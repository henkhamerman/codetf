Refactoring Types: ['Move Method']
va/org/graylog2/indexer/ranges/EsIndexRangeService.java
/**
 * This file is part of Graylog.
 *
 * Graylog is free software: you can redistribute it and/or modify
 * it under the terms of the GNU General Public License as published by
 * the Free Software Foundation, either version 3 of the License, or
 * (at your option) any later version.
 *
 * Graylog is distributed in the hope that it will be useful,
 * but WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
 * GNU General Public License for more details.
 *
 * You should have received a copy of the GNU General Public License
 * along with Graylog.  If not, see <http://www.gnu.org/licenses/>.
 */
package org.graylog2.indexer.ranges;

import com.fasterxml.jackson.core.JsonProcessingException;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.google.common.base.Stopwatch;
import com.google.common.base.Throwables;
import com.google.common.collect.ImmutableSortedSet;
import com.google.common.primitives.Ints;
import org.elasticsearch.action.NoShardAvailableActionException;
import org.elasticsearch.action.bulk.BulkRequest;
import org.elasticsearch.action.bulk.BulkRequestBuilder;
import org.elasticsearch.action.bulk.BulkResponse;
import org.elasticsearch.action.delete.DeleteRequest;
import org.elasticsearch.action.delete.DeleteResponse;
import org.elasticsearch.action.get.GetRequest;
import org.elasticsearch.action.get.GetRequestBuilder;
import org.elasticsearch.action.get.GetResponse;
import org.elasticsearch.action.index.IndexRequest;
import org.elasticsearch.action.index.IndexResponse;
import org.elasticsearch.action.search.SearchRequest;
import org.elasticsearch.action.search.SearchResponse;
import org.elasticsearch.action.search.SearchScrollRequest;
import org.elasticsearch.action.search.SearchType;
import org.elasticsearch.client.Client;
import org.elasticsearch.common.unit.TimeValue;
import org.elasticsearch.index.query.BoolQueryBuilder;
import org.elasticsearch.index.query.QueryBuilders;
import org.elasticsearch.index.query.RangeQueryBuilder;
import org.elasticsearch.search.Scroll;
import org.elasticsearch.search.SearchHit;
import org.graylog2.database.NotFoundException;
import org.graylog2.indexer.IndexMapping;
import org.graylog2.indexer.searches.Searches;
import org.graylog2.indexer.searches.TimestampStats;
import org.graylog2.shared.system.activities.Activity;
import org.graylog2.shared.system.activities.ActivityWriter;
import org.joda.time.DateTime;
import org.joda.time.DateTimeZone;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import javax.annotation.Nullable;
import javax.inject.Inject;
import java.util.Map;
import java.util.SortedSet;
import java.util.concurrent.TimeUnit;

import static com.google.common.base.MoreObjects.firstNonNull;

public class EsIndexRangeService implements IndexRangeService {
    private static final Logger LOG = LoggerFactory.getLogger(EsIndexRangeService.class);

    private final Client client;
    private final ActivityWriter activityWriter;
    private final Searches searches;
    private final ObjectMapper objectMapper;

    @Inject
    public EsIndexRangeService(Client client, ActivityWriter activityWriter, Searches searches, ObjectMapper objectMapper) {
        this.client = client;
        this.activityWriter = activityWriter;
        this.searches = searches;
        this.objectMapper = objectMapper;
    }

    @Override
    @Nullable
    public IndexRange get(String index) throws NotFoundException {
        final GetRequest request = new GetRequestBuilder(client, index)
                .setType(IndexMapping.TYPE_META)
                .setId(index)
                .request();

        final GetResponse r;
        try {
            r = client.get(request).actionGet();
        } catch (NoShardAvailableActionException e) {
            throw new NotFoundException(e);
        }

        if (!r.isExists()) {
            throw new NotFoundException("Index [" + index + "] not found.");
        }

        return parseSource(r.getIndex(), r.getSource());
    }

    @Nullable
    private IndexRange parseSource(String index, Map<String, Object> fields) {
        try {
            return IndexRange.create(
                    index,
                    parseFromDateString((String) fields.get("begin")),
                    parseFromDateString((String) fields.get("end")),
                    parseFromDateString((String) fields.get("calculated_at")),
                    (int) fields.get("took_ms")
            );
        } catch (Exception e) {
            return null;
        }
    }

    private DateTime parseFromDateString(String s) {
        return DateTime.parse(s);
    }

    @Override
    public SortedSet<IndexRange> find(DateTime begin, DateTime end) {
        final RangeQueryBuilder beginRangeQuery = QueryBuilders.rangeQuery("begin").gte(begin.getMillis());
        final RangeQueryBuilder endRangeQuery = QueryBuilders.rangeQuery("end").lte(end.getMillis());
        final BoolQueryBuilder completeRangeQuery = QueryBuilders.boolQuery()
                .must(beginRangeQuery)
                .must(endRangeQuery);
        final SearchRequest request = client.prepareSearch()
                .setTypes(IndexMapping.TYPE_META)
                .setQuery(completeRangeQuery)
                .request();

        final SearchResponse response = client.search(request).actionGet();
        final ImmutableSortedSet.Builder<IndexRange> indexRanges = ImmutableSortedSet.orderedBy(IndexRange.COMPARATOR);
        for (SearchHit searchHit : response.getHits()) {
            final IndexRange indexRange = parseSource(searchHit.getIndex(), searchHit.getSource());
            if (indexRange != null) {
                indexRanges.add(indexRange);
            }
        }

        return indexRanges.build();
    }

    @Override
    public SortedSet<IndexRange> findAll() {
        final SearchRequest request = client.prepareSearch()
                .setTypes(IndexMapping.TYPE_META)
                .setQuery(QueryBuilders.matchAllQuery())
                .request();

        final SearchResponse response = client.search(request).actionGet();
        final ImmutableSortedSet.Builder<IndexRange> indexRanges = ImmutableSortedSet.orderedBy(IndexRange.COMPARATOR);
        for (SearchHit searchHit : response.getHits()) {
            final IndexRange indexRange = parseSource(searchHit.getIndex(), searchHit.getSource());
            if (indexRange != null) {
                indexRanges.add(indexRange);
            }
        }

        return indexRanges.build();
    }

    @Override
    public void destroy(String index) {
        final DeleteRequest request = client.prepareDelete()
                .setIndex(index)
                .setId(index)
                .setType(IndexMapping.TYPE_META)
                .setRefresh(true)
                .request();
        final DeleteResponse response = client.delete(request).actionGet();

        if (response.isFound()) {
            String msg = "Removed range meta-information of [" + index + "]";
            LOG.info(msg);
            activityWriter.write(new Activity(msg, IndexRange.class));
        } else {
            LOG.warn("Couldn't find meta-information of index [{}]", index);
        }
    }

    @Override
    public void destroyAll() {
        final Scroll scroll = new Scroll(TimeValue.timeValueMinutes(1L));
        final SearchRequest searchRequest = client.prepareSearch()
                .setTypes(IndexMapping.TYPE_META)
                .setSearchType(SearchType.SCAN)
                .setScroll(scroll)
                .setQuery(QueryBuilders.matchAllQuery())
                .request();
        final SearchResponse searchResponse = client.search(searchRequest).actionGet();

        final SearchScrollRequest scrollRequest = client.prepareSearchScroll(searchResponse.getScrollId())
                .setScroll(scroll)
                .request();
        final SearchResponse scrollResponse = client.searchScroll(scrollRequest).actionGet();

        final BulkRequestBuilder bulkRequestBuilder = client.prepareBulk();
        for (SearchHit hit : scrollResponse.getHits().hits()) {
            final DeleteRequest deleteRequest = client.prepareDelete(hit.index(), hit.type(), hit.id()).request();
            bulkRequestBuilder.add(deleteRequest);
        }

        final BulkRequest bulkRequest = bulkRequestBuilder.request();
        final BulkResponse bulkResponse = client.bulk(bulkRequest).actionGet();

        if (bulkResponse.hasFailures()) {
            LOG.warn("Couldn't remove meta-information of all indices");
            LOG.debug("Bulk delete error details: {}", bulkResponse.buildFailureMessage());
        } else {
            String msg = "Removed range meta-information of all indices";
            LOG.info(msg);
            activityWriter.write(new Activity(msg, IndexRange.class));
        }
    }

    @Override
    public IndexRange calculateRange(String index) {
        final Stopwatch sw = Stopwatch.createStarted();
        final DateTime now = DateTime.now(DateTimeZone.UTC);
        final TimestampStats stats = firstNonNull(
                searches.timestampStatsOfIndex(index),
                TimestampStats.create(new DateTime(0L, DateTimeZone.UTC), now, new DateTime(0L, DateTimeZone.UTC))
        );
        final int duration = Ints.saturatedCast(sw.stop().elapsed(TimeUnit.MILLISECONDS));

        LOG.info("Calculated range of [{}] in [{}ms].", index, duration);
        return IndexRange.create(index, stats.min(), stats.max(), now, duration);
    }

    @Override
    public void save(IndexRange indexRange) {
        final byte[] source;
        try {
            source = objectMapper.writeValueAsBytes(indexRange);
        } catch (JsonProcessingException e) {
            throw Throwables.propagate(e);
        }

        final IndexRequest request = client.prepareIndex()
                .setIndex(indexRange.indexName())
                .setType(IndexMapping.TYPE_META)
                .setId(indexRange.indexName())
                .setRefresh(true)
                .setSource(source)
                .request();
        final IndexResponse response = client.index(request).actionGet();
        if (response.isCreated()) {
            LOG.debug("Successfully saved index range {}", indexRange);
        } else {
            LOG.warn("Couldn't safe index range for index [{}]: {}", indexRange.indexName(), indexRange);
        }
    }
}

File: graylog2-server/src/main/java/org/graylog2/indexer/searches/Searches.java
/**
 * This file is part of Graylog.
 *
 * Graylog is free software: you can redistribute it and/or modify
 * it under the terms of the GNU General Public License as published by
 * the Free Software Foundation, either version 3 of the License, or
 * (at your option) any later version.
 *
 * Graylog is distributed in the hope that it will be useful,
 * but WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
 * GNU General Public License for more details.
 *
 * You should have received a copy of the GNU General Public License
 * along with Graylog.  If not, see <http://www.gnu.org/licenses/>.
 */
package org.graylog2.indexer.searches;

import com.codahale.metrics.Histogram;
import com.codahale.metrics.MetricRegistry;
import com.codahale.metrics.Timer;
import com.google.common.collect.Sets;
import org.elasticsearch.ElasticsearchException;
import org.elasticsearch.action.search.SearchRequest;
import org.elasticsearch.action.search.SearchRequestBuilder;
import org.elasticsearch.action.search.SearchResponse;
import org.elasticsearch.action.search.SearchType;
import org.elasticsearch.client.Client;
import org.elasticsearch.common.unit.TimeValue;
import org.elasticsearch.common.xcontent.XContentHelper;
import org.elasticsearch.index.query.BoolFilterBuilder;
import org.elasticsearch.index.query.FilterBuilders;
import org.elasticsearch.index.query.QueryBuilder;
import org.elasticsearch.index.query.QueryBuilders;
import org.elasticsearch.index.query.QueryStringQueryBuilder;
import org.elasticsearch.indices.IndexMissingException;
import org.elasticsearch.search.SearchHit;
import org.elasticsearch.search.aggregations.AggregationBuilders;
import org.elasticsearch.search.aggregations.bucket.filter.Filter;
import org.elasticsearch.search.aggregations.bucket.filter.FilterAggregationBuilder;
import org.elasticsearch.search.aggregations.bucket.histogram.DateHistogram;
import org.elasticsearch.search.aggregations.bucket.missing.Missing;
import org.elasticsearch.search.aggregations.bucket.terms.Terms;
import org.elasticsearch.search.aggregations.metrics.max.Max;
import org.elasticsearch.search.aggregations.metrics.min.Min;
import org.elasticsearch.search.aggregations.metrics.stats.Stats;
import org.elasticsearch.search.aggregations.metrics.stats.extended.ExtendedStats;
import org.elasticsearch.search.sort.SortOrder;
import org.graylog2.Configuration;
import org.graylog2.indexer.Deflector;
import org.graylog2.indexer.IndexHelper;
import org.graylog2.indexer.ranges.IndexRange;
import org.graylog2.indexer.ranges.IndexRangeService;
import org.graylog2.indexer.results.CountResult;
import org.graylog2.indexer.results.DateHistogramResult;
import org.graylog2.indexer.results.FieldHistogramResult;
import org.graylog2.indexer.results.FieldStatsResult;
import org.graylog2.indexer.results.HistogramResult;
import org.graylog2.indexer.results.ScrollResult;
import org.graylog2.indexer.results.SearchResult;
import org.graylog2.indexer.results.TermsResult;
import org.graylog2.indexer.results.TermsStatsResult;
import org.graylog2.indexer.searches.timeranges.TimeRange;
import org.graylog2.indexer.searches.timeranges.TimeRanges;
import org.graylog2.plugin.Tools;
import org.joda.time.DateTime;
import org.joda.time.Period;
import org.joda.time.format.DateTimeFormat;
import org.joda.time.format.DateTimeFormatter;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import javax.inject.Inject;
import javax.inject.Singleton;
import java.io.IOException;
import java.util.List;
import java.util.Set;
import java.util.concurrent.TimeUnit;

import static com.codahale.metrics.MetricRegistry.name;
import static com.google.common.base.Preconditions.checkNotNull;
import static org.elasticsearch.index.query.QueryBuilders.matchAllQuery;
import static org.elasticsearch.index.query.QueryBuilders.queryStringQuery;

@Singleton
public class Searches {
    private static final Logger LOG = LoggerFactory.getLogger(Searches.class);

    public final static String AGG_TERMS = "gl2_terms";
    public final static String AGG_STATS = "gl2_stats";
    public final static String AGG_TERMS_STATS = "gl2_termsstats";
    public static final String AGG_FILTER = "gl2_filter";
    public static final String AGG_HISTOGRAM = "gl2_histogram";
    public static final String AGG_EXTENDED_STATS = "gl2_extended_stats";

    public enum TermsStatsOrder {
        TERM,
        REVERSE_TERM,
        COUNT,
        REVERSE_COUNT,
        TOTAL,
        REVERSE_TOTAL,
        MIN,
        REVERSE_MIN,
        MAX,
        REVERSE_MAX,
        MEAN,
        REVERSE_MEAN
    }

    public enum DateHistogramInterval {
        YEAR(Period.years(1)),
        QUARTER(Period.months(3)),
        MONTH(Period.months(1)),
        WEEK(Period.weeks(1)),
        DAY(Period.days(1)),
        HOUR(Period.hours(1)),
        MINUTE(Period.minutes(1));

        private final Period period;

        DateHistogramInterval(Period period) {
            this.period = period;
        }

        public Period getPeriod() {
            return period;
        }

        public DateHistogram.Interval toESInterval() {
            switch (this.name()) {
                case "MINUTE":
                    return DateHistogram.Interval.MINUTE;
                case "HOUR":
                    return DateHistogram.Interval.HOUR;
                case "DAY":
                    return DateHistogram.Interval.DAY;
                case "WEEK":
                    return DateHistogram.Interval.WEEK;
                case "MONTH":
                    return DateHistogram.Interval.MONTH;
                case "QUARTER":
                    return DateHistogram.Interval.QUARTER;
                default:
                    return DateHistogram.Interval.YEAR;
            }
        }
    }


    private final Configuration configuration;
    private final Deflector deflector;
    private final IndexRangeService indexRangeService;
    private final Client c;
    private final MetricRegistry metricRegistry;
    private final Timer esRequestTimer;
    private final Histogram esTimeRangeHistogram;

    @Inject
    public Searches(Configuration configuration,
                    Deflector deflector,
                    IndexRangeService indexRangeService,
                    Client client,
                    MetricRegistry metricRegistry) {
        this.configuration = checkNotNull(configuration);
        this.deflector = checkNotNull(deflector);
        this.indexRangeService = checkNotNull(indexRangeService);
        this.c = checkNotNull(client);
        this.metricRegistry = checkNotNull(metricRegistry);

        this.esRequestTimer = metricRegistry.timer(name(Searches.class, "elasticsearch", "requests"));
        this.esTimeRangeHistogram = metricRegistry.histogram(name(Searches.class, "elasticsearch", "ranges"));
    }

    public CountResult count(String query, TimeRange range) {
        return count(query, range, null);
    }

    public CountResult count(String query, TimeRange range, String filter) {
        Set<String> indices = IndexHelper.determineAffectedIndices(indexRangeService, deflector, range);

        SearchRequest request;
        if (filter == null) {
            request = standardSearchRequest(query, indices, range).request();
        } else {
            request = filteredSearchRequest(query, filter, indices, range).request();
        }
        request.searchType(SearchType.COUNT);

        SearchResponse r = c.search(request).actionGet();
        esRequestTimer.update(r.getTookInMillis(), TimeUnit.MILLISECONDS);
        return new CountResult(r.getHits().getTotalHits(), r.getTookInMillis(), r.getHits());
    }

    public ScrollResult scroll(String query, TimeRange range, int limit, int offset, List<String> fields, String filter) {
        final Set<String> indices = IndexHelper.determineAffectedIndices(indexRangeService, deflector, range);
        final SearchRequestBuilder srb = standardSearchRequest(query, indices, limit, offset, range, null, false);
        if (range != null && filter != null) {
            srb.setPostFilter(standardFilters(range, filter));
        }

        // only request the fields we asked for otherwise we can't figure out which fields will be in the result set
        // until we've scrolled through the entire set.
        // TODO: Check if we can get away without loading the _source field.
        // http://www.elasticsearch.org/guide/en/elasticsearch/reference/current/search-request-fields.html#search-request-fields
        // "For backwards compatibility, if the fields parameter specifies fields which are not stored , it will
        // load the _source and extract it from it. This functionality has been replaced by the source filtering
        // parameter." -- So we should look at the source filtering parameter once we switched to ES 1.x.
        srb.addFields(fields.toArray(new String[fields.size()]));
        srb.addField("_source"); // always request the _source field because otherwise we can't access non-stored values

        final SearchRequest request = srb.setSearchType(SearchType.SCAN)
                .setScroll(new TimeValue(1, TimeUnit.MINUTES))
                .setSize(500).request(); // TODO magic numbers
        if (LOG.isDebugEnabled()) {
            try {
                LOG.debug("ElasticSearch scroll query: {}", XContentHelper.convertToJson(request.source(), false));
            } catch (IOException ignored) {
            }
        }
        final SearchResponse r = c.search(request).actionGet();
        esRequestTimer.update(r.getTookInMillis(), TimeUnit.MILLISECONDS);

        return new ScrollResult(c, query, request.source(), r, fields);
    }

    public SearchResult search(String query, TimeRange range, int limit, int offset, Sorting sorting) {
        return search(query, null, range, limit, offset, sorting);
    }

    public SearchResult search(String query, String filter, TimeRange range, int limit, int offset, Sorting sorting) {
        final SearchesConfig searchesConfig = SearchesConfigBuilder.newConfig()
                .setQuery(query)
                .setFilter(filter)
                .setRange(range)
                .setLimit(limit)
                .setOffset(offset)
                .setSorting(sorting)
                .build();

        return search(searchesConfig);
    }

    public SearchResult search(SearchesConfig config) {
        Set<IndexRange> indices = IndexHelper.determineAffectedIndicesWithRanges(indexRangeService, deflector, config.range());

        Set<String> indexNames = Sets.newHashSet();
        for (IndexRange index : indices) {
            indexNames.add(index.indexName());
        }

        SearchRequest request = searchRequest(config, indexNames).request();

        SearchResponse r = c.search(request).actionGet();
        esRequestTimer.update(r.getTookInMillis(), TimeUnit.MILLISECONDS);

        return new SearchResult(r.getHits(), indices, config.query(), request.source(), r.getTook());
    }

    public TermsResult terms(String field, int size, String query, String filter, TimeRange range) {
        if (size == 0) {
            size = 50;
        }

        SearchRequestBuilder srb;
        if (filter == null) {
            srb = standardSearchRequest(query, IndexHelper.determineAffectedIndices(indexRangeService, deflector, range), range);
        } else {
            srb = filteredSearchRequest(query, filter, IndexHelper.determineAffectedIndices(indexRangeService, deflector, range), range);
        }

        FilterAggregationBuilder builder = AggregationBuilders.filter(AGG_FILTER)
                .subAggregation(
                        AggregationBuilders.terms(AGG_TERMS)
                                .field(field)
                                .size(size))
                .subAggregation(
                        AggregationBuilders.missing("missing")
                                .field(field))
                .filter(standardFilters(range, filter));

        srb.addAggregation(builder);

        final SearchRequest request = srb.request();
        SearchResponse r = c.search(request).actionGet();
        esRequestTimer.update(r.getTookInMillis(), TimeUnit.MILLISECONDS);

        final Filter f = r.getAggregations().get(AGG_FILTER);
        return new TermsResult(
                (Terms) f.getAggregations().get(AGG_TERMS),
                (Missing) f.getAggregations().get("missing"),
                f.getDocCount(),
                query,
                request.source(),
                r.getTook()
        );
    }

    public TermsResult terms(String field, int size, String query, TimeRange range) {
        return terms(field, size, query, null, range);
    }

    public TermsStatsResult termsStats(String keyField, String valueField, TermsStatsOrder order, int size, String query, String filter, TimeRange range) {
        if (size == 0) {
            size = 50;
        }

        SearchRequestBuilder srb;
        if (filter == null) {
            srb = standardSearchRequest(query, IndexHelper.determineAffectedIndices(indexRangeService, deflector, range), range);
        } else {
            srb = filteredSearchRequest(query, filter, IndexHelper.determineAffectedIndices(indexRangeService, deflector, range), range);
        }


        Terms.Order termsOrder;
        switch (order) {
            case COUNT:
                termsOrder = Terms.Order.count(true);
                break;
            case REVERSE_COUNT:
                termsOrder = Terms.Order.count(false);
                break;
            case TERM:
                termsOrder = Terms.Order.term(true);
                break;
            case REVERSE_TERM:
                termsOrder = Terms.Order.term(false);
                break;
            case MIN:
                termsOrder = Terms.Order.aggregation(AGG_STATS, "min", true);
                break;
            case REVERSE_MIN:
                termsOrder = Terms.Order.aggregation(AGG_STATS, "min", false);
                break;
            case MAX:
                termsOrder = Terms.Order.aggregation(AGG_STATS, "max", true);
                break;
            case REVERSE_MAX:
                termsOrder = Terms.Order.aggregation(AGG_STATS, "max", false);
                break;
            case MEAN:
                termsOrder = Terms.Order.aggregation(AGG_STATS, "avg", true);
                break;
            case REVERSE_MEAN:
                termsOrder = Terms.Order.aggregation(AGG_STATS, "avg", false);
                break;
            case TOTAL:
                termsOrder = Terms.Order.aggregation(AGG_STATS, "sum", true);
                break;
            case REVERSE_TOTAL:
                termsOrder = Terms.Order.aggregation(AGG_STATS, "sum", false);
                break;
            default:
                termsOrder = Terms.Order.count(true);
        }

        FilterAggregationBuilder builder = AggregationBuilders.filter(AGG_FILTER)
                .subAggregation(
                        AggregationBuilders.terms(AGG_TERMS_STATS)
                                .field(keyField)
                                .subAggregation(AggregationBuilders.stats(AGG_STATS).field(valueField))
                                .order(termsOrder)
                                .size(size))
                .filter(standardFilters(range, filter));

        srb.addAggregation(builder);

        final SearchRequest request = srb.request();
        SearchResponse r = c.search(request).actionGet();
        esRequestTimer.update(r.getTookInMillis(), TimeUnit.MILLISECONDS);

        final Filter f = r.getAggregations().get(AGG_FILTER);
        return new TermsStatsResult(
                (Terms) f.getAggregations().get(AGG_TERMS_STATS),
                query,
                request.source(),
                r.getTook()
        );
    }

    public TermsStatsResult termsStats(String keyField, String valueField, TermsStatsOrder order, int size, String query, TimeRange range) {
        return termsStats(keyField, valueField, order, size, query, null, range);
    }

    public FieldStatsResult fieldStats(String field, String query, TimeRange range) throws FieldTypeException {
        return fieldStats(field, query, null, range);
    }

    public FieldStatsResult fieldStats(String field, String query, String filter, TimeRange range) throws FieldTypeException {
        SearchRequestBuilder srb;

        if (filter == null) {
            srb = standardSearchRequest(query, IndexHelper.determineAffectedIndices(indexRangeService, deflector, range), range);
        } else {
            srb = filteredSearchRequest(query, filter, IndexHelper.determineAffectedIndices(indexRangeService, deflector, range), range);
        }

        FilterAggregationBuilder builder = AggregationBuilders.filter(AGG_FILTER)
                .filter(standardFilters(range, filter))
                .subAggregation(AggregationBuilders.extendedStats(AGG_EXTENDED_STATS).field(field));

        srb.addAggregation(builder);

        SearchResponse r;
        final SearchRequest request;
        try {
            request = srb.request();
            r = c.search(request).actionGet();
        } catch (org.elasticsearch.action.search.SearchPhaseExecutionException e) {
            throw new FieldTypeException(e);
        }
        esRequestTimer.update(r.getTookInMillis(), TimeUnit.MILLISECONDS);

        final Filter f = r.getAggregations().get(AGG_FILTER);
        return new FieldStatsResult(
                (ExtendedStats) f.getAggregations().get(AGG_EXTENDED_STATS),
                r.getHits(),
                query,
                request.source(),
                r.getTook()
        );
    }

    public HistogramResult histogram(String query, DateHistogramInterval interval, TimeRange range) {
        return histogram(query, interval, null, range);
    }

    public HistogramResult histogram(String query, DateHistogramInterval interval, String filter, TimeRange range) {
        FilterAggregationBuilder builder = AggregationBuilders.filter(AGG_FILTER)
                .subAggregation(
                        AggregationBuilders.dateHistogram(AGG_HISTOGRAM)
                                .field("timestamp")
                                .interval(interval.toESInterval()))
                .filter(standardFilters(range, filter));

        QueryStringQueryBuilder qs = queryStringQuery(query);
        qs.allowLeadingWildcard(configuration.isAllowLeadingWildcardSearches());

        SearchRequestBuilder srb = c.prepareSearch();
        final Set<String> affectedIndices = IndexHelper.determineAffectedIndices(indexRangeService, deflector, range);
        srb.setIndices(affectedIndices.toArray(new String[affectedIndices.size()]));
        srb.setQuery(qs);
        srb.addAggregation(builder);

        final SearchRequest request = srb.request();
        SearchResponse r = c.search(request).actionGet();
        esRequestTimer.update(r.getTookInMillis(), TimeUnit.MILLISECONDS);

        final Filter f = r.getAggregations().get(AGG_FILTER);
        return new DateHistogramResult(
                (DateHistogram) f.getAggregations().get(AGG_HISTOGRAM),
                query,
                request.source(),
                interval,
                r.getTook());
    }

    public HistogramResult fieldHistogram(String query, String field, DateHistogramInterval interval, String filter, TimeRange range) throws FieldTypeException {
        FilterAggregationBuilder builder = AggregationBuilders.filter(AGG_FILTER)
                .subAggregation(
                        AggregationBuilders.dateHistogram(AGG_HISTOGRAM)
                                .field("timestamp")
                                .subAggregation(AggregationBuilders.stats(AGG_STATS).field(field))
                                .interval(interval.toESInterval())
                )
                .filter(standardFilters(range, filter));

        QueryStringQueryBuilder qs = queryStringQuery(query);
        qs.allowLeadingWildcard(configuration.isAllowLeadingWildcardSearches());

        SearchRequestBuilder srb = c.prepareSearch();
        final Set<String> affectedIndices = IndexHelper.determineAffectedIndices(indexRangeService, deflector, range);
        srb.setIndices(affectedIndices.toArray(new String[affectedIndices.size()]));
        srb.setQuery(qs);
        srb.addAggregation(builder);

        SearchResponse r;
        final SearchRequest request = srb.request();
        try {
            r = c.search(request).actionGet();
        } catch (org.elasticsearch.action.search.SearchPhaseExecutionException e) {
            throw new FieldTypeException(e);
        }
        esRequestTimer.update(r.getTookInMillis(), TimeUnit.MILLISECONDS);

        final Filter f = r.getAggregations().get(AGG_FILTER);
        return new FieldHistogramResult(
                (DateHistogram) f.getAggregations().get(AGG_HISTOGRAM),
                query,
                request.source(),
                interval,
                r.getTook());
    }

    /**
     * <em>WARNING:</em> The name of that method is wrong and it returns the <em>newest</em> message of an index!
     */
    public SearchHit firstOfIndex(String index) {
        return oneOfIndex(index, matchAllQuery(), SortOrder.DESC);
    }

    /**
     * Find the oldest message timestamp in the given index.
     *
     * @param index Name of the index to query.
     * @return the oldest message timestamp in the given index, or {@code null} if it couldn't be found.
     */
    public DateTime findOldestMessageTimestampOfIndex(String index) {
        final FilterAggregationBuilder builder = AggregationBuilders.filter("agg")
                .filter(FilterBuilders.existsFilter("timestamp"))
                .subAggregation(AggregationBuilders.min("ts_min").field("timestamp"));
        final SearchRequestBuilder srb = c.prepareSearch()
                .setIndices(index)
                .setSearchType(SearchType.COUNT)
                .addAggregation(builder);

        final SearchResponse response;
        try {
            response = c.search(srb.request()).actionGet();
        } catch (IndexMissingException e) {
            throw e;
        } catch (ElasticsearchException e) {
            LOG.error("Error while calculating oldest timestamp in index <" + index + ">", e);
            return null;
        }
        esRequestTimer.update(response.getTookInMillis(), TimeUnit.MILLISECONDS);

        final Filter f = response.getAggregations().get("agg");
        if (f.getDocCount() == 0L) {
            LOG.debug("No documents with attribute \"timestamp\" found in index <{}>", index);
            return null;
        }

        final Min min = f.getAggregations().get("ts_min");
        final String minTimeStamp = min.getValueAsString();
        final DateTimeFormatter formatter = DateTimeFormat.forPattern(Tools.ES_DATE_FORMAT).withZoneUTC();

        return formatter.parseDateTime(minTimeStamp);
    }

    /**
     * Calculate stats (min, max, avg) about the message timestamps in the given index.
     *
     * @param index Name of the index to query.
     * @return the timestamp stats in the given index, or {@code null} if they couldn't be calculated.
     * @see org.elasticsearch.search.aggregations.metrics.stats.Stats
     */
    public TimestampStats timestampStatsOfIndex(String index) {
        final FilterAggregationBuilder builder = AggregationBuilders.filter("agg")
                .filter(FilterBuilders.existsFilter("timestamp"))
                .subAggregation(AggregationBuilders.stats("ts_stats").field("timestamp"));
        final SearchRequestBuilder srb = c.prepareSearch()
                .setIndices(index)
                .setSearchType(SearchType.COUNT)
                .addAggregation(builder);

        final SearchResponse response;
        try {
            response = c.search(srb.request()).actionGet();
        } catch (IndexMissingException e) {
            throw e;
        } catch (ElasticsearchException e) {
            LOG.error("Error while calculating timestamp stats in index <" + index + ">", e);
            return null;
        }
        esRequestTimer.update(response.getTookInMillis(), TimeUnit.MILLISECONDS);

        final Filter f = response.getAggregations().get("agg");
        if (f.getDocCount() == 0L) {
            LOG.debug("No documents with attribute \"timestamp\" found in index <{}>", index);
            return null;
        }

        final Stats stats = f.getAggregations().get("ts_stats");
        final DateTimeFormatter formatter = DateTimeFormat.forPattern(Tools.ES_DATE_FORMAT).withZoneUTC();
        final DateTime min = formatter.parseDateTime(stats.getMinAsString());
        final DateTime max = formatter.parseDateTime(stats.getMaxAsString());
        final DateTime avg = formatter.parseDateTime(stats.getAvgAsString());

        return TimestampStats.create(min, max, avg);
    }

    /**
     * <em>WARNING:</em> The name of that method is wrong and it returns the <em>oldest</em> message of an index!
     */
    public SearchHit lastOfIndex(String index) {
        return oneOfIndex(index, matchAllQuery(), SortOrder.ASC);
    }

    /**
     * Find the newest message timestamp in the given index.
     *
     * @param index Name of the index to query.
     * @return the youngest message timestamp in the given index, or {@code null} if it couldn't be found.
     */
    public DateTime findNewestMessageTimestampOfIndex(String index) {
        final FilterAggregationBuilder builder = AggregationBuilders.filter("agg")
                .filter(FilterBuilders.existsFilter("timestamp"))
                .subAggregation(AggregationBuilders.max("ts_max").field("timestamp"));
        final SearchRequestBuilder srb = c.prepareSearch()
                .setIndices(index)
                .setSearchType(SearchType.COUNT)
                .addAggregation(builder);

        final SearchResponse response;
        try {
            response = c.search(srb.request()).actionGet();
        } catch (IndexMissingException e) {
            throw e;
        } catch (ElasticsearchException e) {
            LOG.error("Error while calculating newest timestamp in index <" + index + ">", e);
            return null;
        }
        esRequestTimer.update(response.getTookInMillis(), TimeUnit.MILLISECONDS);

        final Filter f = response.getAggregations().get("agg");
        if (f.getDocCount() == 0L) {
            LOG.debug("No documents with attribute \"timestamp\" found in index <{}>", index);
            return null;
        }

        final Max max = f.getAggregations().get("ts_max");
        final String maxTimeStamp = max.getValueAsString();
        final DateTimeFormatter formatter = DateTimeFormat.forPattern(Tools.ES_DATE_FORMAT).withZoneUTC();

        return formatter.parseDateTime(maxTimeStamp);
    }

    private SearchRequestBuilder searchRequest(SearchesConfig config, Set<String> indices) {
        final SearchRequestBuilder request;

        if (config.filter() == null) {
            request = standardSearchRequest(config.query(), indices, config.limit(), config.offset(), config.range(), config.sorting());
        } else {
            request = filteredSearchRequest(config.query(), config.filter(), indices, config.limit(), config.offset(), config.range(), config.sorting());
        }

        if (config.fields() != null) {
            // http://www.elasticsearch.org/guide/en/elasticsearch/reference/current/search-request-fields.html#search-request-fields
            // "For backwards compatibility, if the fields parameter specifies fields which are not stored , it will
            // load the _source and extract it from it. This functionality has been replaced by the source filtering
            // parameter."
            // TODO: Look at the source filtering parameter once we switched to ES 1.x.
            request.addFields(config.fields().toArray(new String[config.fields().size()]));
        }

        return request;
    }

    private SearchRequestBuilder standardSearchRequest(String query, Set<String> indices) {
        return standardSearchRequest(query, indices, 0, 0, null, null);
    }

    private SearchRequestBuilder standardSearchRequest(String query, Set<String> indices, TimeRange range) {
        return standardSearchRequest(query, indices, 0, 0, range, null);
    }

    private SearchRequestBuilder standardSearchRequest(String query,
                                                       Set<String> indices,
                                                       int limit,
                                                       int offset,
                                                       TimeRange range,
                                                       Sorting sort) {
        return standardSearchRequest(query, indices, limit, offset, range, sort, true);
    }

    private SearchRequestBuilder standardSearchRequest(
            String query,
            Set<String> indices,
            int limit,
            int offset,
            TimeRange range,
            Sorting sort,
            boolean highlight) {
        if (query == null || query.trim().isEmpty()) {
            query = "*";
        }

        SearchRequestBuilder srb = c.prepareSearch();
        srb.setIndices(indices.toArray(new String[indices.size()]));

        if (query.trim().equals("*")) {
            srb.setQuery(matchAllQuery());
        } else {
            QueryStringQueryBuilder qs = queryStringQuery(query);
            qs.allowLeadingWildcard(configuration.isAllowLeadingWildcardSearches());
            srb.setQuery(qs);
        }

        srb.setFrom(offset);

        if (limit > 0) {
            srb.setSize(limit);
        }

        if (range != null) {
            srb.setPostFilter(IndexHelper.getTimestampRangeFilter(range));
        }

        if (sort != null) {
            srb.addSort(sort.getField(), sort.asElastic());
        }

        if (highlight && configuration.isAllowHighlighting()) {
            srb.setHighlighterRequireFieldMatch(false);
            srb.addHighlightedField("*", 0, 0);
        }

        return srb;
    }

    private SearchRequestBuilder filteredSearchRequest(String query, String filter, Set<String> indices) {
        return filteredSearchRequest(query, filter, indices, 0, 0, null, null);
    }

    private SearchRequestBuilder filteredSearchRequest(String query, String filter, Set<String> indices, TimeRange range) {
        return filteredSearchRequest(query, filter, indices, 0, 0, range, null);
    }

    private SearchRequestBuilder filteredSearchRequest(String query, String filter, Set<String> indices, int limit, int offset, TimeRange range, Sorting sort) {
        SearchRequestBuilder srb = standardSearchRequest(query, indices, limit, offset, range, sort);

        if (range != null && filter != null) {
            srb.setPostFilter(standardFilters(range, filter));
        }

        return srb;
    }

    private SearchHit oneOfIndex(String index, QueryBuilder q, SortOrder sort) {
        SearchRequestBuilder srb = c.prepareSearch();
        srb.setIndices(index);
        srb.setQuery(q);
        srb.setSize(1);
        srb.addSort("timestamp", sort);

        SearchResponse r = c.search(srb.request()).actionGet();
        esRequestTimer.update(r.getTookInMillis(), TimeUnit.MILLISECONDS);

        if (r.getHits() != null && r.getHits().totalHits() > 0) {
            return r.getHits().getAt(0);
        } else {
            return null;
        }
    }

    private BoolFilterBuilder standardFilters(TimeRange range, String filter) {
        BoolFilterBuilder bfb = FilterBuilders.boolFilter();

        boolean set = false;

        if (range != null) {
            bfb.must(IndexHelper.getTimestampRangeFilter(range));
            set = true;
            esTimeRangeHistogram.update(TimeRanges.toSeconds(range));
        }

        if (filter != null && !filter.isEmpty() && !filter.equals("*")) {
            bfb.must(FilterBuilders.queryFilter(QueryBuilders.queryStringQuery(filter)));
            set = true;
        }

        if (!set) {
            throw new RuntimeException("Either range or filter must be set.");
        }

        return bfb;
    }

    public static class FieldTypeException extends Exception {
        public FieldTypeException(Throwable e) {
            super(e);
        }
    }
}


File: graylog2-server/src/test/java/org/graylog2/indexer/ranges/EsIndexRangeServiceTest.java
/**
 * This file is part of Graylog.
 *
 * Graylog is free software: you can redistribute it and/or modify
 * it under the terms of the GNU General Public License as published by
 * the Free Software Foundation, either version 3 of the License, or
 * (at your option) any later version.
 *
 * Graylog is distributed in the hope that it will be useful,
 * but WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
 * GNU General Public License for more details.
 *
 * You should have received a copy of the GNU General Public License
 * along with Graylog.  If not, see <http://www.gnu.org/licenses/>.
 */
package org.graylog2.indexer.ranges;

import com.google.common.collect.ImmutableSet;
import com.lordofthejars.nosqlunit.annotation.UsingDataSet;
import com.lordofthejars.nosqlunit.core.LoadStrategyEnum;
import com.lordofthejars.nosqlunit.elasticsearch.ElasticsearchRule;
import com.lordofthejars.nosqlunit.elasticsearch.EmbeddedElasticsearch;
import org.assertj.jodatime.api.Assertions;
import org.elasticsearch.action.admin.indices.refresh.RefreshRequest;
import org.elasticsearch.action.admin.indices.refresh.RefreshResponse;
import org.elasticsearch.client.Client;
import org.elasticsearch.indices.IndexMissingException;
import org.graylog2.database.NotFoundException;
import org.graylog2.indexer.nosqlunit.IndexCreatingLoadStrategyFactory;
import org.graylog2.indexer.searches.Searches;
import org.graylog2.indexer.searches.TimestampStats;
import org.graylog2.shared.bindings.providers.ObjectMapperProvider;
import org.graylog2.shared.system.activities.NullActivityWriter;
import org.joda.time.DateTime;
import org.joda.time.DateTimeZone;
import org.junit.Before;
import org.junit.ClassRule;
import org.junit.Rule;
import org.junit.Test;
import org.junit.runner.RunWith;
import org.mockito.Mock;
import org.mockito.runners.MockitoJUnitRunner;

import javax.inject.Inject;
import java.util.Set;

import static com.lordofthejars.nosqlunit.elasticsearch.ElasticsearchRule.ElasticsearchRuleBuilder.newElasticsearchRule;
import static com.lordofthejars.nosqlunit.elasticsearch.EmbeddedElasticsearch.EmbeddedElasticsearchRuleBuilder.newEmbeddedElasticsearchRule;
import static org.assertj.core.api.Assertions.assertThat;
import static org.junit.Assume.assumeTrue;
import static org.mockito.Matchers.anyString;
import static org.mockito.Mockito.doThrow;
import static org.mockito.Mockito.when;

@RunWith(MockitoJUnitRunner.class)
public class EsIndexRangeServiceTest {
    @ClassRule
    public static final EmbeddedElasticsearch EMBEDDED_ELASTICSEARCH = newEmbeddedElasticsearchRule().build();
    private static final String INDEX_NAME = "graylog";
    private static final ImmutableSet<String> INDEX_NAMES = ImmutableSet.of("graylog", "graylog_1", "graylog_2");

    @Rule
    public ElasticsearchRule elasticsearchRule;

    @Inject
    private Client client;

    @Mock
    private Searches searches;
    private IndexRangeService indexRangeService;

    public EsIndexRangeServiceTest() {
        this.elasticsearchRule = newElasticsearchRule().defaultEmbeddedElasticsearch();
        this.elasticsearchRule.setLoadStrategyFactory(new IndexCreatingLoadStrategyFactory(INDEX_NAMES));
    }

    @Before
    public void setUp() throws Exception {
        indexRangeService = new EsIndexRangeService(client, new NullActivityWriter(), searches, new ObjectMapperProvider().get());
    }

    @Test
    @UsingDataSet(locations = "EsIndexRangeServiceTest.json", loadStrategy = LoadStrategyEnum.CLEAN_INSERT)
    public void getReturnsExistingIndexRange() throws Exception {
        IndexRange indexRange = indexRangeService.get("graylog_1");

        assertThat(indexRange.indexName()).isEqualTo("graylog_1");
        assertThat(indexRange.begin()).isEqualTo(new DateTime(2015, 1, 1, 0, 0, DateTimeZone.UTC));
        assertThat(indexRange.end()).isEqualTo(new DateTime(2015, 1, 2, 0, 0, DateTimeZone.UTC));
        assertThat(indexRange.calculatedAt()).isEqualTo(new DateTime(2015, 1, 1, 0, 0, DateTimeZone.UTC));
        assertThat(indexRange.calculationDuration()).isEqualTo(23);
    }

    @Test(expected = NotFoundException.class)
    public void getThrowsNotFoundException() throws Exception {
        indexRangeService.get("does-not-exist");
    }

    @Test
    @UsingDataSet(locations = "EsIndexRangeServiceTest.json", loadStrategy = LoadStrategyEnum.CLEAN_INSERT)
    public void findReturnsIndexRangesWithinGivenRange() throws Exception {
        final DateTime begin = new DateTime(2015, 1, 1, 0, 0, DateTimeZone.UTC);
        final DateTime end = new DateTime(2015, 1, 2, 0, 0, DateTimeZone.UTC);
        Set<IndexRange> indexRanges = indexRangeService.find(begin, end);

        assertThat(indexRanges).hasSize(1);
    }

    @Test
    @UsingDataSet(locations = "EsIndexRangeServiceTest.json", loadStrategy = LoadStrategyEnum.CLEAN_INSERT)
    public void findReturnsNothingBeforeBegin() throws Exception {
        final DateTime begin = new DateTime(2016, 1, 1, 0, 0, DateTimeZone.UTC);
        final DateTime end = new DateTime(2016, 1, 2, 0, 0, DateTimeZone.UTC);
        Set<IndexRange> indexRanges = indexRangeService.find(begin, end);

        assertThat(indexRanges).isEmpty();
    }

    @Test
    @UsingDataSet(locations = "EsIndexRangeServiceTest.json", loadStrategy = LoadStrategyEnum.CLEAN_INSERT)
    public void findAllReturnsAllIndexRanges() throws Exception {
        assertThat(indexRangeService.findAll()).hasSize(2);
    }

    @Test
    @UsingDataSet(locations = "EsIndexRangeServiceTest.json", loadStrategy = LoadStrategyEnum.CLEAN_INSERT)
    public void destroyRemovesIndexRange() throws Exception {
        indexRangeService.destroy("graylog_1");

        Set<IndexRange> indexRanges = indexRangeService.findAll();

        assertThat(indexRanges).hasSize(1);
        assertThat(indexRanges.iterator().next().indexName()).isEqualTo("graylog_2");
    }

    @Test
    @UsingDataSet(locations = "EsIndexRangeServiceTest.json", loadStrategy = LoadStrategyEnum.CLEAN_INSERT)
    public void destroyRemovesIgnoresNonExistingIndexRange() throws Exception {
        indexRangeService.destroy("does-not-exist");

        assertThat(indexRangeService.findAll()).hasSize(2);
    }

    @Test
    public void calculateRangeReturnsIndexRange() throws Exception {
        final String index = "graylog_test";
        final DateTime min = new DateTime(2015, 1, 1, 0, 0, DateTimeZone.UTC);
        final DateTime max = new DateTime(2015, 1, 3, 0, 0, DateTimeZone.UTC);
        final DateTime avg = new DateTime(2015, 1, 2, 0, 0, DateTimeZone.UTC);
        final TimestampStats stats = TimestampStats.create(min, max, avg);

        when(searches.timestampStatsOfIndex(index)).thenReturn(stats);

        final IndexRange indexRange = indexRangeService.calculateRange(index);

        assertThat(indexRange.indexName()).isEqualTo(index);
        assertThat(indexRange.begin()).isEqualTo(min);
        assertThat(indexRange.end()).isEqualTo(max);
        Assertions.assertThat(indexRange.calculatedAt()).isEqualToIgnoringHours(DateTime.now(DateTimeZone.UTC));
    }

    @Test
    public void testCalculateRangeWithEmptyIndex() throws Exception {
        final String index = "graylog_test";
        when(searches.findNewestMessageTimestampOfIndex(index)).thenReturn(null);
        final IndexRange range = indexRangeService.calculateRange(index);

        assertThat(range).isNotNull();
        assertThat(range.indexName()).isEqualTo(index);
        Assertions.assertThat(range.end()).isEqualToIgnoringHours(DateTime.now(DateTimeZone.UTC));
    }

    @Test(expected = IndexMissingException.class)
    public void testCalculateRangeWithNonExistingIndex() throws Exception {
        doThrow(IndexMissingException.class).when(searches).timestampStatsOfIndex(anyString());
        indexRangeService.calculateRange("does-not-exist");
    }

    @Test
    @UsingDataSet(locations = "EsIndexRangeServiceTest.json", loadStrategy = LoadStrategyEnum.CLEAN_INSERT)
    public void destroyAllKillsAllIndexRanges() throws Exception {
        indexRangeService.destroyAll();
        // Refresh indices
        final RefreshRequest refreshRequest = client.admin().indices().prepareRefresh().request();
        final RefreshResponse refreshResponse = client.admin().indices().refresh(refreshRequest).actionGet();
        assumeTrue(refreshResponse.getFailedShards() == 0);

        assertThat(indexRangeService.findAll()).isEmpty();
    }

    @Test
    @UsingDataSet(loadStrategy = LoadStrategyEnum.DELETE_ALL)
    public void savePersistsIndexRange() throws Exception {
        final String indexName = "graylog";
        final DateTime begin = new DateTime(2015, 1, 1, 0, 0, DateTimeZone.UTC);
        final DateTime end = new DateTime(2015, 1, 2, 0, 0, DateTimeZone.UTC);
        final DateTime now = DateTime.now(DateTimeZone.UTC);
        final IndexRange indexRange = IndexRange.create(indexName, begin, end, now, 42);

        indexRangeService.save(indexRange);

        final IndexRange result = indexRangeService.get(indexName);
        assertThat(result.indexName()).isEqualTo(indexName);
        assertThat(result.begin()).isEqualTo(begin);
        assertThat(result.end()).isEqualTo(end);
        assertThat(result.calculatedAt()).isEqualTo(now);
        assertThat(result.calculationDuration()).isEqualTo(42);
    }

    @Test
    @UsingDataSet(loadStrategy = LoadStrategyEnum.DELETE_ALL)
    public void saveOverwritesExistingIndexRange() throws Exception {
        final String indexName = "graylog";
        final DateTime begin = new DateTime(2015, 1, 1, 0, 0, DateTimeZone.UTC);
        final DateTime end = new DateTime(2015, 1, 2, 0, 0, DateTimeZone.UTC);
        final DateTime now = DateTime.now(DateTimeZone.UTC);
        final IndexRange indexRangeBefore = IndexRange.create(indexName, begin, end, now, 1);
        final IndexRange indexRangeAfter = IndexRange.create(indexName, begin, end, now, 2);

        indexRangeService.save(indexRangeBefore);

        final IndexRange before = indexRangeService.get(indexName);
        assertThat(before.calculationDuration()).isEqualTo(1);

        indexRangeService.save(indexRangeAfter);

        final IndexRange after = indexRangeService.get(indexName);
        assertThat(after.calculationDuration()).isEqualTo(2);
    }
}

File: graylog2-server/src/test/java/org/graylog2/indexer/searches/SearchesTest.java
/**
 * This file is part of Graylog.
 *
 * Graylog is free software: you can redistribute it and/or modify
 * it under the terms of the GNU General Public License as published by
 * the Free Software Foundation, either version 3 of the License, or
 * (at your option) any later version.
 *
 * Graylog is distributed in the hope that it will be useful,
 * but WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
 * GNU General Public License for more details.
 *
 * You should have received a copy of the GNU General Public License
 * along with Graylog.  If not, see <http://www.gnu.org/licenses/>.
 */
package org.graylog2.indexer.searches;

import com.codahale.metrics.Histogram;
import com.codahale.metrics.MetricRegistry;
import com.codahale.metrics.Timer;
import com.google.common.collect.ImmutableSortedSet;
import com.lordofthejars.nosqlunit.annotation.UsingDataSet;
import com.lordofthejars.nosqlunit.core.LoadStrategyEnum;
import com.lordofthejars.nosqlunit.elasticsearch.ElasticsearchRule;
import com.lordofthejars.nosqlunit.elasticsearch.EmbeddedElasticsearch;
import org.elasticsearch.client.Client;
import org.elasticsearch.indices.IndexMissingException;
import org.elasticsearch.search.SearchHit;
import org.graylog2.Configuration;
import org.graylog2.indexer.Deflector;
import org.graylog2.indexer.nosqlunit.IndexCreatingLoadStrategyFactory;
import org.graylog2.indexer.ranges.IndexRange;
import org.graylog2.indexer.ranges.IndexRangeComparator;
import org.graylog2.indexer.ranges.IndexRangeService;
import org.graylog2.indexer.results.CountResult;
import org.graylog2.indexer.results.FieldStatsResult;
import org.graylog2.indexer.results.HistogramResult;
import org.graylog2.indexer.results.TermsResult;
import org.graylog2.indexer.results.TermsStatsResult;
import org.graylog2.indexer.searches.timeranges.AbsoluteRange;
import org.joda.time.DateTime;
import org.joda.time.DateTimeZone;
import org.junit.Before;
import org.junit.ClassRule;
import org.junit.Rule;
import org.junit.Test;
import org.junit.runner.RunWith;
import org.mockito.Mock;
import org.mockito.runners.MockitoJUnitRunner;

import javax.inject.Inject;
import java.util.Collections;
import java.util.Map;
import java.util.SortedSet;

import static com.lordofthejars.nosqlunit.elasticsearch.ElasticsearchRule.ElasticsearchRuleBuilder.newElasticsearchRule;
import static com.lordofthejars.nosqlunit.elasticsearch.EmbeddedElasticsearch.EmbeddedElasticsearchRuleBuilder.newEmbeddedElasticsearchRule;
import static org.assertj.core.api.Assertions.assertThat;
import static org.mockito.Matchers.any;
import static org.mockito.Mockito.when;

@RunWith(MockitoJUnitRunner.class)
public class SearchesTest {
    @ClassRule
    public static final EmbeddedElasticsearch EMBEDDED_ELASTICSEARCH = newEmbeddedElasticsearchRule().build();
    private static final String REQUEST_TIMER_NAME = "org.graylog2.indexer.searches.Searches.elasticsearch.requests";
    private static final String RANGES_HISTOGRAM_NAME = "org.graylog2.indexer.searches.Searches.elasticsearch.ranges";

    @Rule
    public ElasticsearchRule elasticsearchRule;

    private static final String INDEX_NAME = "graylog";
    private static final SortedSet<IndexRange> INDEX_RANGES = ImmutableSortedSet
            .orderedBy(new IndexRangeComparator())
            .add(new IndexRange() {
                @Override
                public String indexName() {
                    return INDEX_NAME;
                }

                @Override
                public DateTime calculatedAt() {
                    return DateTime.now();
                }

                @Override
                public DateTime end() {
                    return new DateTime(2015, 1, 1, 0, 0, DateTimeZone.UTC);
                }

                @Override
                public int calculationDuration() {
                    return 0;
                }

                @Override
                public DateTime begin() {
                    return new DateTime(0L, DateTimeZone.UTC);
                }
            }).build();

    @Mock
    private Deflector deflector;
    @Mock
    private IndexRangeService indexRangeService;

    private MetricRegistry metricRegistry;
    private Searches searches;

    @Inject
    private Client client;

    public SearchesTest() {
        this.elasticsearchRule = newElasticsearchRule().defaultEmbeddedElasticsearch();
        this.elasticsearchRule.setLoadStrategyFactory(new IndexCreatingLoadStrategyFactory(Collections.singleton(INDEX_NAME)));
    }

    @Before
    public void setUp() throws Exception {
        when(indexRangeService.find(any(DateTime.class), any(DateTime.class))).thenReturn(INDEX_RANGES);
        metricRegistry = new MetricRegistry();
        searches = new Searches(new Configuration(), deflector, indexRangeService, client, metricRegistry);
    }

    @Test
    @UsingDataSet(loadStrategy = LoadStrategyEnum.CLEAN_INSERT)
    public void testCount() throws Exception {
        CountResult result = searches.count("*", new AbsoluteRange(
                new DateTime(2015, 1, 1, 0, 0),
                new DateTime(2015, 1, 2, 0, 0)));

        assertThat(result.getCount()).isEqualTo(10L);
    }

    @Test
    @UsingDataSet(loadStrategy = LoadStrategyEnum.CLEAN_INSERT)
    public void countRecordsMetrics() throws Exception {
        CountResult result = searches.count("*", new AbsoluteRange(
                new DateTime(2015, 1, 1, 0, 0),
                new DateTime(2015, 1, 2, 0, 0)));

        assertThat(metricRegistry.getTimers()).containsKey(REQUEST_TIMER_NAME);
        assertThat(metricRegistry.getHistograms()).containsKey(RANGES_HISTOGRAM_NAME);

        Timer timer = metricRegistry.timer(REQUEST_TIMER_NAME);
        assertThat(timer.getCount()).isEqualTo(1L);
    }

    @Test
    @UsingDataSet(loadStrategy = LoadStrategyEnum.CLEAN_INSERT)
    public void testTerms() throws Exception {
        TermsResult result = searches.terms("n", 25, "*", new AbsoluteRange(
                new DateTime(2015, 1, 1, 0, 0),
                new DateTime(2015, 1, 2, 0, 0)));

        assertThat(result.getTotal()).isEqualTo(10L);
        assertThat(result.getMissing()).isEqualTo(2L);
        assertThat(result.getTerms())
                .hasSize(4)
                .containsEntry("1", 2L)
                .containsEntry("2", 2L)
                .containsEntry("3", 3L)
                .containsEntry("4", 1L);
    }

    @Test
    @UsingDataSet(loadStrategy = LoadStrategyEnum.CLEAN_INSERT)
    public void termsRecordsMetrics() throws Exception {
        TermsResult result = searches.terms("n", 25, "*", new AbsoluteRange(
                new DateTime(2015, 1, 1, 0, 0),
                new DateTime(2015, 1, 2, 0, 0)));

        assertThat(metricRegistry.getTimers()).containsKey(REQUEST_TIMER_NAME);
        assertThat(metricRegistry.getHistograms()).containsKey(RANGES_HISTOGRAM_NAME);

        Timer timer = metricRegistry.timer(REQUEST_TIMER_NAME);
        assertThat(timer.getCount()).isEqualTo(1L);

        Histogram histogram = metricRegistry.histogram(RANGES_HISTOGRAM_NAME);
        assertThat(histogram.getCount()).isEqualTo(1L);
        assertThat(histogram.getSnapshot().getValues()).containsExactly(86400L);
    }

    @Test
    @UsingDataSet(loadStrategy = LoadStrategyEnum.CLEAN_INSERT)
    public void testTermsStats() throws Exception {
        TermsStatsResult r = searches.termsStats("message", "n", Searches.TermsStatsOrder.COUNT, 25, "*",
                new AbsoluteRange(
                        new DateTime(2015, 1, 1, 0, 0),
                        new DateTime(2015, 1, 2, 0, 0))
        );

        assertThat(r.getResults()).hasSize(2);
        assertThat((Map<String, Object>) r.getResults().get(0))
                .hasSize(7)
                .containsEntry("key_field", "ho");
    }

    @Test
    @UsingDataSet(loadStrategy = LoadStrategyEnum.CLEAN_INSERT)
    public void termsStatsRecordsMetrics() throws Exception {
        TermsStatsResult r = searches.termsStats("message", "n", Searches.TermsStatsOrder.COUNT, 25, "*",
                new AbsoluteRange(
                        new DateTime(2015, 1, 1, 0, 0),
                        new DateTime(2015, 1, 2, 0, 0))
        );

        assertThat(metricRegistry.getTimers()).containsKey(REQUEST_TIMER_NAME);
        assertThat(metricRegistry.getHistograms()).containsKey(RANGES_HISTOGRAM_NAME);

        Timer timer = metricRegistry.timer(REQUEST_TIMER_NAME);
        assertThat(timer.getCount()).isEqualTo(1L);

        Histogram histogram = metricRegistry.histogram(RANGES_HISTOGRAM_NAME);
        assertThat(histogram.getCount()).isEqualTo(1L);
        assertThat(histogram.getSnapshot().getValues()).containsExactly(86400L);
    }

    @Test
    @UsingDataSet(loadStrategy = LoadStrategyEnum.CLEAN_INSERT)
    public void testFieldStats() throws Exception {
        FieldStatsResult result = searches.fieldStats("n", "*", new AbsoluteRange(
                new DateTime(2015, 1, 1, 0, 0),
                new DateTime(2015, 1, 2, 0, 0)));

        assertThat(result.getSearchHits()).hasSize(10);
        assertThat(result.getCount()).isEqualTo(8);
        assertThat(result.getMin()).isEqualTo(1.0);
        assertThat(result.getMax()).isEqualTo(4.0);
        assertThat(result.getMean()).isEqualTo(2.375);
        assertThat(result.getSum()).isEqualTo(19.0);
        assertThat(result.getSumOfSquares()).isEqualTo(53.0);
        assertThat(result.getVariance()).isEqualTo(0.984375);
        assertThat(result.getStdDeviation()).isEqualTo(0.9921567416492215);
    }

    @Test
    @UsingDataSet(loadStrategy = LoadStrategyEnum.CLEAN_INSERT)
    public void fieldStatsRecordsMetrics() throws Exception {
        FieldStatsResult result = searches.fieldStats("n", "*", new AbsoluteRange(
                new DateTime(2015, 1, 1, 0, 0),
                new DateTime(2015, 1, 2, 0, 0)));

        assertThat(metricRegistry.getTimers()).containsKey(REQUEST_TIMER_NAME);
        assertThat(metricRegistry.getHistograms()).containsKey(RANGES_HISTOGRAM_NAME);

        Timer timer = metricRegistry.timer(REQUEST_TIMER_NAME);
        assertThat(timer.getCount()).isEqualTo(1L);

        Histogram histogram = metricRegistry.histogram(RANGES_HISTOGRAM_NAME);
        assertThat(histogram.getCount()).isEqualTo(1L);
        assertThat(histogram.getSnapshot().getValues()).containsExactly(86400L);
    }

    @Test
    @UsingDataSet(loadStrategy = LoadStrategyEnum.CLEAN_INSERT)
    @SuppressWarnings("unchecked")
    public void testHistogram() throws Exception {
        final AbsoluteRange range = new AbsoluteRange(new DateTime(2015, 1, 1, 0, 0), new DateTime(2015, 1, 2, 0, 0));
        HistogramResult h = searches.histogram("*", Searches.DateHistogramInterval.MINUTE, range);

        assertThat(h.getInterval()).isEqualTo(Searches.DateHistogramInterval.MINUTE);
        assertThat(h.getHistogramBoundaries()).isEqualTo(range);
        assertThat(h.getResults())
                .hasSize(5)
                .containsEntry(new DateTime(2015, 1, 1, 1, 0, DateTimeZone.UTC).getMillis() / 1000L, 2L)
                .containsEntry(new DateTime(2015, 1, 1, 2, 0, DateTimeZone.UTC).getMillis() / 1000L, 2L)
                .containsEntry(new DateTime(2015, 1, 1, 3, 0, DateTimeZone.UTC).getMillis() / 1000L, 2L)
                .containsEntry(new DateTime(2015, 1, 1, 4, 0, DateTimeZone.UTC).getMillis() / 1000L, 2L)
                .containsEntry(new DateTime(2015, 1, 1, 5, 0, DateTimeZone.UTC).getMillis() / 1000L, 2L);
    }

    @Test
    @UsingDataSet(loadStrategy = LoadStrategyEnum.CLEAN_INSERT)
    @SuppressWarnings("unchecked")
    public void histogramRecordsMetrics() throws Exception {
        final AbsoluteRange range = new AbsoluteRange(new DateTime(2015, 1, 1, 0, 0), new DateTime(2015, 1, 2, 0, 0));
        HistogramResult h = searches.histogram("*", Searches.DateHistogramInterval.MINUTE, range);

        assertThat(metricRegistry.getTimers()).containsKey(REQUEST_TIMER_NAME);
        assertThat(metricRegistry.getHistograms()).containsKey(RANGES_HISTOGRAM_NAME);

        Timer timer = metricRegistry.timer(REQUEST_TIMER_NAME);
        assertThat(timer.getCount()).isEqualTo(1L);

        Histogram histogram = metricRegistry.histogram(RANGES_HISTOGRAM_NAME);
        assertThat(histogram.getCount()).isEqualTo(1L);
        assertThat(histogram.getSnapshot().getValues()).containsExactly(86400L);
    }

    @Test
    @UsingDataSet(loadStrategy = LoadStrategyEnum.CLEAN_INSERT)
    @SuppressWarnings("unchecked")
    public void testFieldHistogram() throws Exception {
        final AbsoluteRange range = new AbsoluteRange(new DateTime(2015, 1, 1, 0, 0), new DateTime(2015, 1, 2, 0, 0));
        HistogramResult h = searches.fieldHistogram("*", "n", Searches.DateHistogramInterval.MINUTE, null, range);

        assertThat(h.getInterval()).isEqualTo(Searches.DateHistogramInterval.MINUTE);
        assertThat(h.getHistogramBoundaries()).isEqualTo(range);
        assertThat(h.getResults()).hasSize(5);
        assertThat((Map<String, Number>) h.getResults().get(new DateTime(2015, 1, 1, 1, 0, DateTimeZone.UTC).getMillis() / 1000L))
                .containsEntry("total_count", 2L)
                .containsEntry("total", 0.0);
        assertThat((Map<String, Number>) h.getResults().get(new DateTime(2015, 1, 1, 2, 0, DateTimeZone.UTC).getMillis() / 1000L))
                .containsEntry("total_count", 2L)
                .containsEntry("total", 4.0)
                .containsEntry("mean", 2.0);
    }

    @Test
    @UsingDataSet(loadStrategy = LoadStrategyEnum.CLEAN_INSERT)
    @SuppressWarnings("unchecked")
    public void fieldHistogramRecordsMetrics() throws Exception {
        final AbsoluteRange range = new AbsoluteRange(new DateTime(2015, 1, 1, 0, 0), new DateTime(2015, 1, 2, 0, 0));
        HistogramResult h = searches.fieldHistogram("*", "n", Searches.DateHistogramInterval.MINUTE, null, range);

        assertThat(metricRegistry.getTimers()).containsKey(REQUEST_TIMER_NAME);
        assertThat(metricRegistry.getHistograms()).containsKey(RANGES_HISTOGRAM_NAME);

        Timer timer = metricRegistry.timer(REQUEST_TIMER_NAME);
        assertThat(timer.getCount()).isEqualTo(1L);

        Histogram histogram = metricRegistry.histogram(RANGES_HISTOGRAM_NAME);
        assertThat(histogram.getCount()).isEqualTo(1L);
        assertThat(histogram.getSnapshot().getValues()).containsExactly(86400L);
    }

    @Test
    @UsingDataSet(loadStrategy = LoadStrategyEnum.CLEAN_INSERT)
    public void testFirstOfIndex() throws Exception {
        SearchHit searchHit = searches.firstOfIndex("graylog");

        assertThat(searchHit.getSource()).containsKey("timestamp");
        assertThat(searchHit.getSource().get("timestamp")).isEqualTo("2015-01-01 05:00:00.000");
    }

    @Test
    @UsingDataSet(loadStrategy = LoadStrategyEnum.CLEAN_INSERT)
    public void testLastOfIndex() throws Exception {
        SearchHit searchHit = searches.lastOfIndex("graylog");

        assertThat(searchHit.getSource()).containsKey("timestamp");
        assertThat(searchHit.getSource().get("timestamp")).isEqualTo("2015-01-01 01:00:00.000");
    }

    @Test
    @UsingDataSet(loadStrategy = LoadStrategyEnum.CLEAN_INSERT)
    public void testFindNewestMessageTimestampOfIndex() throws Exception {
        DateTime dateTime = searches.findNewestMessageTimestampOfIndex("graylog");

        assertThat(dateTime).isEqualTo(new DateTime(2015, 1, 1, 5, 0, DateTimeZone.UTC));
    }

    @Test
    @UsingDataSet(locations = "SearchesTest-EmptyIndex.json", loadStrategy = LoadStrategyEnum.CLEAN_INSERT)
    public void testFindNewestMessageTimestampOfIndexWithEmptyIndex() throws Exception {
        DateTime dateTime = searches.findNewestMessageTimestampOfIndex("graylog");

        assertThat(dateTime).isNull();
    }

    @Test(expected = IndexMissingException.class)
    public void testFindNewestMessageTimestampOfIndexWithNonExistingIndex() throws Exception {
        searches.findNewestMessageTimestampOfIndex("does-not-exist");
    }

    @Test
    @UsingDataSet(loadStrategy = LoadStrategyEnum.CLEAN_INSERT)
    public void testFindOldestMessageTimestampOfIndex() throws Exception {
        DateTime dateTime = searches.findOldestMessageTimestampOfIndex("graylog");

        assertThat(dateTime).isEqualTo(new DateTime(2015, 1, 1, 1, 0, DateTimeZone.UTC));
    }

    @Test
    @UsingDataSet(locations = "SearchesTest-EmptyIndex.json", loadStrategy = LoadStrategyEnum.CLEAN_INSERT)
    public void testFindOldestMessageTimestampOfIndexWithEmptyIndex() throws Exception {
        DateTime dateTime = searches.findOldestMessageTimestampOfIndex("graylog");

        assertThat(dateTime).isNull();
    }

    @Test(expected = IndexMissingException.class)
    public void testFindOldestMessageTimestampOfIndexWithNonExistingIndex() throws Exception {
        searches.findOldestMessageTimestampOfIndex("does-not-exist");
    }

    @Test
    @UsingDataSet(loadStrategy = LoadStrategyEnum.CLEAN_INSERT)
    public void testTimestampStatsOfIndex() throws Exception {
        TimestampStats stats = searches.timestampStatsOfIndex("graylog");

        assertThat(stats.min()).isEqualTo(new DateTime(2015, 1, 1, 1, 0, DateTimeZone.UTC));
        assertThat(stats.max()).isEqualTo(new DateTime(2015, 1, 1, 5, 0, DateTimeZone.UTC));
        assertThat(stats.avg()).isEqualTo(new DateTime(2015, 1, 1, 3, 0, DateTimeZone.UTC));
    }

    @Test
    @UsingDataSet(locations = "SearchesTest-EmptyIndex.json", loadStrategy = LoadStrategyEnum.CLEAN_INSERT)
    public void testTimestampStatsOfIndexWithEmptyIndex() throws Exception {
        TimestampStats stats = searches.timestampStatsOfIndex("graylog");

        assertThat(stats).isNull();
    }

    @Test(expected = IndexMissingException.class)
    public void testTimestampStatsOfIndexWithNonExistingIndex() throws Exception {
        searches.timestampStatsOfIndex("does-not-exist");
    }

}
