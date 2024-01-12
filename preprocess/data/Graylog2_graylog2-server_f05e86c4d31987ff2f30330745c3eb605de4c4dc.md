Refactoring Types: ['Move Attribute']
org/graylog2/indexer/IndexHelper.java
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
package org.graylog2.indexer;

import com.google.common.collect.Lists;
import com.google.common.collect.Sets;
import org.elasticsearch.index.query.FilterBuilder;
import org.elasticsearch.index.query.FilterBuilders;
import org.graylog2.database.NotFoundException;
import org.graylog2.indexer.ranges.IndexRange;
import org.graylog2.indexer.ranges.IndexRangeService;
import org.graylog2.indexer.searches.timeranges.RelativeRange;
import org.graylog2.indexer.searches.timeranges.TimeRange;
import org.graylog2.plugin.Tools;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.util.Comparator;
import java.util.List;
import java.util.Set;

public class IndexHelper {
    private static final Logger LOG = LoggerFactory.getLogger(IndexHelper.class);

    public static Set<String> getOldestIndices(Set<String> indexNames, int count) {
        Set<String> r = Sets.newHashSet();

        if (count < 0 || indexNames.size() <= count) {
            return r;
        }

        Set<Integer> numbers = Sets.newHashSet();

        for (String indexName : indexNames) {
            numbers.add(Deflector.extractIndexNumber(indexName));
        }

        List<String> sorted = prependPrefixes(getPrefix(indexNames), Tools.asSortedList(numbers));

        // Add last x entries to return set.
        r.addAll(sorted.subList(0, count));

        return r;
    }

    public static FilterBuilder getTimestampRangeFilter(TimeRange range) throws InvalidRangeFormatException {
        if (range == null) {
            return null;
        }

        return FilterBuilders.rangeFilter("timestamp")
                .gte(Tools.buildElasticSearchTimeFormat(range.getFrom()))
                .lte(Tools.buildElasticSearchTimeFormat(range.getTo()));
    }

    private static String getPrefix(Set<String> names) {
        if (names.isEmpty()) {
            return "";
        }

        String name = (String) names.toArray()[0];
        return name.substring(0, name.lastIndexOf("_"));
    }

    private static List<String> prependPrefixes(String prefix, List<Integer> numbers) {
        List<String> r = Lists.newArrayList();

        for (int number : numbers) {
            r.add(prefix + "_" + number);
        }

        return r;
    }

    public static Set<String> determineAffectedIndices(IndexRangeService indexRangeService,
                                                       Deflector deflector,
                                                       TimeRange range) {
        Set<String> indices = Sets.newHashSet();

        for (IndexRange indexRange : indexRangeService.getFrom((int) (range.getFrom().getMillis() / 1000))) {
            indices.add(indexRange.getIndexName());
        }

        // Always include the most recent index in some cases.
        final String targetIndex = deflector.getCurrentActualTargetIndex();
        if (targetIndex != null && (indices.isEmpty() || range instanceof RelativeRange)) {
            indices.add(targetIndex);
        }

        return indices;
    }

    public static Set<IndexRange> determineAffectedIndicesWithRanges(IndexRangeService indexRangeService,
                                                                     Deflector deflector,
                                                                     TimeRange range) {
        Set<IndexRange> indices = Sets.newTreeSet(new Comparator<IndexRange>() {
            @Override
            public int compare(IndexRange o1, IndexRange o2) {
                return o2.getStart().compareTo(o1.getStart());
            }
        });

        for (IndexRange indexRange : indexRangeService.getFrom((int) (range.getFrom().getMillis() / 1000))) {
            indices.add(indexRange);
        }

        // Always include the most recent index in some cases.
        final String targetIndex = deflector.getCurrentActualTargetIndex();
        if (targetIndex != null && (indices.isEmpty() || range instanceof RelativeRange)) {
            try {
                final IndexRange deflectorIndexRange = indexRangeService.get(targetIndex);
                indices.add(deflectorIndexRange);
            } catch (NotFoundException e) {
                LOG.warn("Couldn't find latest deflector target index", e);
            }
        }

        return indices;
    }

}


File: graylog2-server/src/main/java/org/graylog2/indexer/ranges/IndexRange.java
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

import org.graylog2.plugin.database.Persisted;
import org.joda.time.DateTime;

/**
 * @author Dennis Oelkers <dennis@torch.sh>
 */
public interface IndexRange extends Persisted {
    String getIndexName();

    DateTime getCalculatedAt();

    DateTime getStart();

    int getCalculationTookMs();
}


File: graylog2-server/src/main/java/org/graylog2/indexer/ranges/MongoIndexRangeService.java
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

import com.google.common.base.Stopwatch;
import com.google.common.collect.ImmutableMap;
import com.google.common.collect.ImmutableSortedSet;
import com.google.common.primitives.Ints;
import com.mongodb.BasicDBObject;
import com.mongodb.DBObject;
import org.bson.types.ObjectId;
import org.graylog2.database.MongoConnection;
import org.graylog2.database.NotFoundException;
import org.graylog2.database.PersistedServiceImpl;
import org.graylog2.indexer.searches.Searches;
import org.graylog2.plugin.Tools;
import org.graylog2.plugin.database.ValidationException;
import org.graylog2.shared.system.activities.Activity;
import org.graylog2.shared.system.activities.ActivityWriter;
import org.joda.time.DateTime;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import javax.inject.Inject;
import java.util.Comparator;
import java.util.Map;
import java.util.SortedSet;
import java.util.concurrent.TimeUnit;

import static com.google.common.base.MoreObjects.firstNonNull;

public class MongoIndexRangeService extends PersistedServiceImpl implements IndexRangeService {
    private static final Logger LOG = LoggerFactory.getLogger(MongoIndexRangeService.class);
    private static final Comparator<IndexRange> COMPARATOR = new IndexRangeComparator();

    private final Searches searches;
    private final ActivityWriter activityWriter;

    @Inject
    public MongoIndexRangeService(MongoConnection mongoConnection, ActivityWriter activityWriter, Searches searches) {
        super(mongoConnection);
        this.activityWriter = activityWriter;
        this.searches = searches;
    }

    @Override
    public IndexRange get(String index) throws NotFoundException {
        DBObject dbo = findOne(MongoIndexRange.class, new BasicDBObject("index", index));

        if (dbo == null)
            throw new NotFoundException("Index " + index + " not found.");

        return new MongoIndexRange((ObjectId) dbo.get("_id"), dbo.toMap());
    }

    @Override
    public SortedSet<IndexRange> getFrom(int timestamp) {
        final ImmutableSortedSet.Builder<IndexRange> ranges = ImmutableSortedSet.orderedBy(COMPARATOR);
        final BasicDBObject query = new BasicDBObject("start", new BasicDBObject("$gte", timestamp));
        for (DBObject dbo : query(MongoIndexRange.class, query)) {
            ranges.add(new MongoIndexRange((ObjectId) dbo.get("_id"), dbo.toMap()));
        }

        return ranges.build();
    }

    @Override
    public SortedSet<IndexRange> getFrom(DateTime dateTime) {
        return getFrom(Ints.saturatedCast(dateTime.getMillis() / 1000L));
    }

    @Override
    public void destroy(String index) {
        try {
            final IndexRange range = get(index);
            destroy(range);
        } catch (NotFoundException e) {
            return;
        }

        String x = "Removed range meta-information of [" + index + "]";
        LOG.info(x);
        activityWriter.write(new Activity(x, MongoIndexRange.class));
    }

    @Override
    public IndexRange create(Map<String, Object> range) {
        return new MongoIndexRange(range);
    }

    @Override
    public void destroyAll() {
        destroyAll(MongoIndexRange.class);
    }

    @Override
    public IndexRange calculateRange(String index) {
        final Stopwatch x = Stopwatch.createStarted();
        final DateTime timestamp = firstNonNull(searches.findNewestMessageTimestampOfIndex(index), Tools.iso8601());
        final int rangeEnd = Ints.saturatedCast(timestamp.getMillis() / 1000L);
        final int took = Ints.saturatedCast(x.stop().elapsed(TimeUnit.MILLISECONDS));

        LOG.info("Calculated range of [{}] in [{}ms].", index, took);

        return create(ImmutableMap.<String, Object>of(
                "index", index,
                "start", rangeEnd, // FIXME The name of the attribute is massively misleading and should be rectified some time
                "calculated_at", Tools.getUTCTimestamp(),
                "took_ms", took));
    }

    @Override
    public void save(IndexRange indexRange) throws ValidationException {
        super.save(indexRange);
    }
}