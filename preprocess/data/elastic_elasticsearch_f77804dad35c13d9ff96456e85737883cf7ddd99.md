Refactoring Types: ['Move Class']
sticsearch/index/IndexService.java
/*
 * Licensed to Elasticsearch under one or more contributor
 * license agreements. See the NOTICE file distributed with
 * this work for additional information regarding copyright
 * ownership. Elasticsearch licenses this file to you under
 * the Apache License, Version 2.0 (the "License"); you may
 * not use this file except in compliance with the License.
 * You may obtain a copy of the License at
 *
 *    http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing,
 * software distributed under the License is distributed on an
 * "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY
 * KIND, either express or implied.  See the License for the
 * specific language governing permissions and limitations
 * under the License.
 */

package org.elasticsearch.index;

import com.google.common.base.Function;
import com.google.common.collect.ImmutableMap;
import com.google.common.collect.Iterators;

import org.apache.lucene.util.IOUtils;
import org.elasticsearch.cluster.metadata.IndexMetaData;
import org.elasticsearch.common.Nullable;
import org.elasticsearch.common.Strings;
import org.elasticsearch.common.collect.Tuple;
import org.elasticsearch.common.inject.*;
import org.elasticsearch.common.settings.Settings;
import org.elasticsearch.env.NodeEnvironment;
import org.elasticsearch.env.ShardLock;
import org.elasticsearch.index.aliases.IndexAliasesService;
import org.elasticsearch.index.analysis.AnalysisService;
import org.elasticsearch.index.cache.IndexCache;
import org.elasticsearch.index.cache.bitset.BitsetFilterCache;
import org.elasticsearch.index.cache.filter.ShardFilterCache;
import org.elasticsearch.index.deletionpolicy.DeletionPolicyModule;
import org.elasticsearch.index.fielddata.IndexFieldDataService;
import org.elasticsearch.index.gateway.IndexShardGatewayService;
import org.elasticsearch.index.mapper.MapperService;
import org.elasticsearch.index.merge.policy.MergePolicyModule;
import org.elasticsearch.index.merge.policy.MergePolicyProvider;
import org.elasticsearch.index.merge.scheduler.MergeSchedulerProvider;
import org.elasticsearch.index.percolator.PercolatorQueriesRegistry;
import org.elasticsearch.index.query.IndexQueryParserService;
import org.elasticsearch.index.settings.IndexSettings;
import org.elasticsearch.index.settings.IndexSettingsService;
import org.elasticsearch.index.shard.*;
import org.elasticsearch.index.similarity.SimilarityService;
import org.elasticsearch.index.store.IndexStore;
import org.elasticsearch.index.store.Store;
import org.elasticsearch.index.store.StoreModule;
import org.elasticsearch.index.translog.TranslogService;
import org.elasticsearch.indices.IndicesLifecycle;
import org.elasticsearch.indices.IndicesService;
import org.elasticsearch.indices.InternalIndicesLifecycle;
import org.elasticsearch.indices.cache.filter.IndicesFilterCache;
import org.elasticsearch.plugins.PluginsService;
import org.elasticsearch.plugins.ShardsPluginsModule;

import java.io.Closeable;
import java.io.IOException;
import java.util.HashMap;
import java.util.Iterator;
import java.util.Set;
import java.util.concurrent.TimeUnit;
import java.util.concurrent.atomic.AtomicBoolean;

import static com.google.common.collect.Maps.newHashMap;
import static org.elasticsearch.common.collect.MapBuilder.newMapBuilder;

/**
 *
 */
public class IndexService extends AbstractIndexComponent implements IndexComponent, Iterable<IndexShard> {

    private final Injector injector;

    private final Settings indexSettings;

    private final PluginsService pluginsService;

    private final InternalIndicesLifecycle indicesLifecycle;

    private final AnalysisService analysisService;

    private final MapperService mapperService;

    private final IndexQueryParserService queryParserService;

    private final SimilarityService similarityService;

    private final IndexAliasesService aliasesService;

    private final IndexCache indexCache;

    private final IndexFieldDataService indexFieldData;

    private final BitsetFilterCache bitsetFilterCache;

    private final IndexSettingsService settingsService;

    private final NodeEnvironment nodeEnv;
    private final IndicesService indicesServices;

    private volatile ImmutableMap<Integer, Tuple<IndexShard, Injector>> shards = ImmutableMap.of();

    private final AtomicBoolean closed = new AtomicBoolean(false);
    private final AtomicBoolean deleted = new AtomicBoolean(false);

    @Inject
    public IndexService(Injector injector, Index index, @IndexSettings Settings indexSettings, NodeEnvironment nodeEnv,
                        AnalysisService analysisService, MapperService mapperService, IndexQueryParserService queryParserService,
                        SimilarityService similarityService, IndexAliasesService aliasesService, IndexCache indexCache,
                        IndexSettingsService settingsService,
                        IndexFieldDataService indexFieldData, BitsetFilterCache bitSetFilterCache, IndicesService indicesServices) {
        super(index, indexSettings);
        this.injector = injector;
        this.indexSettings = indexSettings;
        this.analysisService = analysisService;
        this.mapperService = mapperService;
        this.queryParserService = queryParserService;
        this.similarityService = similarityService;
        this.aliasesService = aliasesService;
        this.indexCache = indexCache;
        this.indexFieldData = indexFieldData;
        this.settingsService = settingsService;
        this.bitsetFilterCache = bitSetFilterCache;

        this.pluginsService = injector.getInstance(PluginsService.class);
        this.indicesServices = indicesServices;
        this.indicesLifecycle = (InternalIndicesLifecycle) injector.getInstance(IndicesLifecycle.class);

        // inject workarounds for cyclic dep
        indexFieldData.setIndexService(this);
        bitSetFilterCache.setIndexService(this);
        this.nodeEnv = nodeEnv;
    }

    public int numberOfShards() {
        return shards.size();
    }

    public InternalIndicesLifecycle indicesLifecycle() {
        return this.indicesLifecycle;
    }

    @Override
    public Iterator<IndexShard> iterator() {
        return Iterators.transform(shards.values().iterator(), new Function<Tuple<IndexShard, Injector>, IndexShard>() {
            @Override
            public IndexShard apply(Tuple<IndexShard, Injector> input) {
                return input.v1();
            }
        });
    }

    public boolean hasShard(int shardId) {
        return shards.containsKey(shardId);
    }

    /**
     * Return the shard with the provided id, or null if there is no such shard.
     */
    @Nullable
    public IndexShard shard(int shardId) {
        Tuple<IndexShard, Injector> indexShardInjectorTuple = shards.get(shardId);
        if (indexShardInjectorTuple != null) {
            return indexShardInjectorTuple.v1();
        }
        return null;
    }

    /**
     * Return the shard with the provided id, or throw an exception if it doesn't exist.
     */
    public IndexShard shardSafe(int shardId) throws IndexShardMissingException {
        IndexShard indexShard = shard(shardId);
        if (indexShard == null) {
            throw new IndexShardMissingException(new ShardId(index, shardId));
        }
        return indexShard;
    }

    public Set<Integer> shardIds() {
        return shards.keySet();
    }

    public Injector injector() {
        return injector;
    }

    public IndexSettingsService settingsService() {
        return this.settingsService;
    }

    public IndexCache cache() {
        return indexCache;
    }

    public IndexFieldDataService fieldData() {
        return indexFieldData;
    }

    public BitsetFilterCache bitsetFilterCache() {
        return bitsetFilterCache;
    }

    public AnalysisService analysisService() {
        return this.analysisService;
    }

    public MapperService mapperService() {
        return mapperService;
    }

    public IndexQueryParserService queryParserService() {
        return queryParserService;
    }

    public SimilarityService similarityService() {
        return similarityService;
    }

    public IndexAliasesService aliasesService() {
        return aliasesService;
    }

    public synchronized void close(final String reason, boolean delete) {
        if (closed.compareAndSet(false, true)) {
            deleted.compareAndSet(false, delete);
            final Set<Integer> shardIds = shardIds();
            for (final int shardId : shardIds) {
                try {
                    removeShard(shardId, reason);
                } catch (Throwable t) {
                    logger.warn("failed to close shard", t);
                }
            }
        }
    }

    /**
     * Return the shard injector for the provided id, or throw an exception if there is no such shard.
     */
    public Injector shardInjectorSafe(int shardId) throws IndexShardMissingException {
        Tuple<IndexShard, Injector> tuple = shards.get(shardId);
        if (tuple == null) {
            throw new IndexShardMissingException(new ShardId(index, shardId));
        }
        return tuple.v2();
    }

    public String indexUUID() {
        return indexSettings.get(IndexMetaData.SETTING_UUID, IndexMetaData.INDEX_UUID_NA_VALUE);
    }

    public synchronized IndexShard createShard(int sShardId, boolean primary) {
        /*
         * TODO: we execute this in parallel but it's a synced method. Yet, we might
         * be able to serialize the execution via the cluster state in the future. for now we just
         * keep it synced.
         */
        if (closed.get()) {
            throw new IllegalStateException("Can't create shard [" + index.name() + "][" + sShardId + "], closed");
        }
        final ShardId shardId = new ShardId(index, sShardId);
        ShardLock lock = null;
        boolean success = false;
        Injector shardInjector = null;
        try {

            ShardPath path = ShardPath.loadShardPath(logger, nodeEnv, shardId, indexSettings);
            if (path == null) {
                path = ShardPath.selectNewPathForShard(nodeEnv, shardId, indexSettings);
                logger.debug("{} creating using a new path [{}]", shardId, path);
            } else {
                logger.debug("{} creating using an existing path [{}]", shardId, path);
            }

            lock = nodeEnv.shardLock(shardId, TimeUnit.SECONDS.toMillis(5));
            if (shards.containsKey(shardId.id())) {
                throw new IndexShardAlreadyExistsException(shardId + " already exists");
            }

            indicesLifecycle.beforeIndexShardCreated(shardId, indexSettings);
            logger.debug("creating shard_id {}", shardId);
            // if we are on a shared FS we only own the shard (ie. we can safely delete it) if we are the primary.
            final boolean canDeleteShardContent = IndexMetaData.isOnSharedFilesystem(indexSettings) == false ||
                    (primary && IndexMetaData.isOnSharedFilesystem(indexSettings));
            final ShardFilterCache shardFilterCache = new ShardFilterCache(shardId, injector.getInstance(IndicesFilterCache.class));
            ModulesBuilder modules = new ModulesBuilder();
            modules.add(new ShardsPluginsModule(indexSettings, pluginsService));
            modules.add(new IndexShardModule(shardId, primary, indexSettings, shardFilterCache));
            modules.add(new StoreModule(injector.getInstance(IndexStore.class).shardDirectory(), lock,
                    new StoreCloseListener(shardId, canDeleteShardContent, shardFilterCache), path));
            modules.add(new DeletionPolicyModule(indexSettings));
            modules.add(new MergePolicyModule(indexSettings));
            try {
                shardInjector = modules.createChildInjector(injector);
            } catch (CreationException e) {
                throw new IndexShardCreationException(shardId, Injectors.getFirstErrorFailure(e));
            } catch (Throwable e) {
                throw new IndexShardCreationException(shardId, e);
            }

            IndexShard indexShard = shardInjector.getInstance(IndexShard.class);
            indicesLifecycle.indexShardStateChanged(indexShard, null, "shard created");
            indicesLifecycle.afterIndexShardCreated(indexShard);

            shards = newMapBuilder(shards).put(shardId.id(), new Tuple<>(indexShard, shardInjector)).immutableMap();
            success = true;
            return indexShard;
        } catch (IOException ex) {
            throw new IndexShardCreationException(shardId, ex);
        } finally {
            if (success == false) {
                IOUtils.closeWhileHandlingException(lock);
                if (shardInjector != null) {
                    IndexShard indexShard = shardInjector.getInstance(IndexShard.class);
                    closeShardInjector("initialization failed", shardId, shardInjector, indexShard);
                }
            }
        }
    }

    public synchronized void removeShard(int shardId, String reason) {
        final ShardId sId = new ShardId(index, shardId);
        final Injector shardInjector;
        final IndexShard indexShard;
        if (shards.containsKey(shardId) == false) {
            return;
        }
        logger.debug("[{}] closing... (reason: [{}])", shardId, reason);
        HashMap<Integer, Tuple<IndexShard, Injector>> tmpShardsMap = newHashMap(shards);
        Tuple<IndexShard, Injector> tuple = tmpShardsMap.remove(shardId);
        indexShard = tuple.v1();
        shardInjector = tuple.v2();
        shards = ImmutableMap.copyOf(tmpShardsMap);
        closeShardInjector(reason, sId, shardInjector, indexShard);
        logger.debug("[{}] closed (reason: [{}])", shardId, reason);
    }

    private void closeShardInjector(String reason, ShardId sId, Injector shardInjector, IndexShard indexShard) {
        final int shardId = sId.id();
        try {
            try {
                indicesLifecycle.beforeIndexShardClosed(sId, indexShard, indexSettings);
            } finally {
                // close everything else even if the beforeIndexShardClosed threw an exception
                for (Class<? extends Closeable> closeable : pluginsService.shardServices()) {
                    try {
                        shardInjector.getInstance(closeable).close();
                    } catch (Throwable e) {
                        logger.debug("[{}] failed to clean plugin shard service [{}]", e, shardId, closeable);
                    }
                }
                // now we can close the translog service, we need to close it before the we close the shard
                // note the that the translog service is not there for shadow replicas
                closeInjectorOptionalResource(sId, shardInjector, TranslogService.class);
                // this logic is tricky, we want to close the engine so we rollback the changes done to it
                // and close the shard so no operations are allowed to it
                if (indexShard != null) {
                    try {
                        final boolean flushEngine = deleted.get() == false && closed.get(); // only flush we are we closed (closed index or shutdown) and if we are not deleted
                        indexShard.close(reason, flushEngine);
                    } catch (Throwable e) {
                        logger.debug("[{}] failed to close index shard", e, shardId);
                        // ignore
                    }
                }
                closeInjectorResource(sId, shardInjector,
                        MergeSchedulerProvider.class,
                        MergePolicyProvider.class,
                        IndexShardGatewayService.class,
                        PercolatorQueriesRegistry.class);

                // call this before we close the store, so we can release resources for it
                indicesLifecycle.afterIndexShardClosed(sId, indexShard, indexSettings);
            }
        } finally {
            try {
                shardInjector.getInstance(Store.class).close();
            } catch (Throwable e) {
                logger.warn("[{}] failed to close store on shard removal (reason: [{}])", e, shardId, reason);
            }
        }
    }

    /**
     * This method gets an instance for each of the given classes passed and calls #close() on the returned instance.
     * NOTE: this method swallows all exceptions thrown from the close method of the injector and logs them as debug log
     */
    private void closeInjectorResource(ShardId shardId, Injector shardInjector, Class<? extends Closeable>... toClose) {
        for (Class<? extends Closeable> closeable : toClose) {
            if (closeInjectorOptionalResource(shardId, shardInjector, closeable) == false) {
                logger.warn("[{}] no instance available for [{}], ignoring... ", shardId, closeable.getSimpleName());
            }
        }
    }

    /**
     * Closes an optional resource. Returns true if the resource was found;
     * NOTE: this method swallows all exceptions thrown from the close method of the injector and logs them as debug log
     */
    private boolean closeInjectorOptionalResource(ShardId shardId, Injector shardInjector, Class<? extends Closeable> toClose) {
        try {
            final Closeable instance = shardInjector.getInstance(toClose);
            if (instance == null) {
                return false;
            }
            IOUtils.close(instance);
        } catch (Throwable t) {
            logger.debug("{} failed to close {}", t, shardId, Strings.toUnderscoreCase(toClose.getSimpleName()));
        }
        return true;
    }


    private void onShardClose(ShardLock lock, boolean ownsShard) {
        if (deleted.get()) { // we remove that shards content if this index has been deleted
            try {
                if (ownsShard) {
                    try {
                        indicesLifecycle.beforeIndexShardDeleted(lock.getShardId(), indexSettings);
                    } finally {
                        indicesServices.deleteShardStore("delete index", lock, indexSettings);
                        indicesLifecycle.afterIndexShardDeleted(lock.getShardId(), indexSettings);
                    }
                }
            } catch (IOException e) {
                indicesServices.addPendingDelete(lock.getShardId(), indexSettings);
                logger.debug("[{}] failed to delete shard content - scheduled a retry", e, lock.getShardId().id());
            }
        }
    }

    private class StoreCloseListener implements Store.OnClose {
        private final ShardId shardId;
        private final boolean ownsShard;
        private final Closeable[] toClose;

        public StoreCloseListener(ShardId shardId, boolean ownsShard, Closeable... toClose) {
            this.shardId = shardId;
            this.ownsShard = ownsShard;
            this.toClose = toClose;
        }

        @Override
        public void handle(ShardLock lock) {
            try {
                assert lock.getShardId().equals(shardId) : "shard id mismatch, expected: " + shardId + " but got: " + lock.getShardId();
                onShardClose(lock, ownsShard);
            } finally {
                try {
                    IOUtils.close(toClose);
                } catch (IOException ex) {
                    logger.debug("failed to close resource", ex);
                }
            }

        }
    }

    public Settings getIndexSettings() {
        return indexSettings;
    }
}


File: core/src/main/java/org/elasticsearch/index/engine/EngineConfig.java
/*
 * Licensed to Elasticsearch under one or more contributor
 * license agreements. See the NOTICE file distributed with
 * this work for additional information regarding copyright
 * ownership. Elasticsearch licenses this file to you under
 * the Apache License, Version 2.0 (the "License"); you may
 * not use this file except in compliance with the License.
 * You may obtain a copy of the License at
 *
 *    http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing,
 * software distributed under the License is distributed on an
 * "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY
 * KIND, either express or implied.  See the License for the
 * specific language governing permissions and limitations
 * under the License.
 */
package org.elasticsearch.index.engine;

import org.apache.lucene.analysis.Analyzer;
import org.apache.lucene.codecs.Codec;
import org.apache.lucene.index.IndexWriterConfig;
import org.apache.lucene.search.QueryCache;
import org.apache.lucene.search.QueryCachingPolicy;
import org.apache.lucene.search.similarities.Similarity;
import org.elasticsearch.common.Nullable;
import org.elasticsearch.common.settings.Settings;
import org.elasticsearch.common.unit.ByteSizeUnit;
import org.elasticsearch.common.unit.ByteSizeValue;
import org.elasticsearch.common.unit.TimeValue;
import org.elasticsearch.common.util.concurrent.EsExecutors;
import org.elasticsearch.index.codec.CodecService;
import org.elasticsearch.index.deletionpolicy.SnapshotDeletionPolicy;
import org.elasticsearch.index.indexing.ShardIndexingService;
import org.elasticsearch.index.merge.policy.MergePolicyProvider;
import org.elasticsearch.index.merge.scheduler.MergeSchedulerProvider;
import org.elasticsearch.index.settings.IndexSettingsService;
import org.elasticsearch.index.shard.ShardId;
import org.elasticsearch.index.shard.TranslogRecoveryPerformer;
import org.elasticsearch.index.store.Store;
import org.elasticsearch.index.translog.TranslogConfig;
import org.elasticsearch.indices.IndicesWarmer;
import org.elasticsearch.threadpool.ThreadPool;

import java.util.concurrent.TimeUnit;

/*
 * Holds all the configuration that is used to create an {@link Engine}.
 * Once {@link Engine} has been created with this object, changes to this
 * object will affect the {@link Engine} instance.
 */
public final class EngineConfig {
    private final ShardId shardId;
    private final TranslogRecoveryPerformer translogRecoveryPerformer;
    private volatile ByteSizeValue indexingBufferSize;
    private volatile ByteSizeValue versionMapSize;
    private volatile String versionMapSizeSetting;
    private final int indexConcurrency;
    private volatile boolean compoundOnFlush = true;
    private long gcDeletesInMillis = DEFAULT_GC_DELETES.millis();
    private volatile boolean enableGcDeletes = true;
    private final String codecName;
    private final boolean optimizeAutoGenerateId;
    private final ThreadPool threadPool;
    private final ShardIndexingService indexingService;
    private final IndexSettingsService indexSettingsService;
    @Nullable
    private final IndicesWarmer warmer;
    private final Store store;
    private final SnapshotDeletionPolicy deletionPolicy;
    private final MergePolicyProvider mergePolicyProvider;
    private final MergeSchedulerProvider mergeScheduler;
    private final Analyzer analyzer;
    private final Similarity similarity;
    private final CodecService codecService;
    private final Engine.FailedEngineListener failedEngineListener;
    private final boolean forceNewTranslog;
    private final QueryCache filterCache;
    private final QueryCachingPolicy filterCachingPolicy;

    /**
     * Index setting for index concurrency / number of threadstates in the indexwriter.
     * The default is depending on the number of CPUs in the system. We use a 0.65 the number of CPUs or at least {@value org.apache.lucene.index.IndexWriterConfig#DEFAULT_MAX_THREAD_STATES}
     * This setting is <b>not</b> realtime updateable
     */
    public static final String INDEX_CONCURRENCY_SETTING = "index.index_concurrency";

    /**
     * Index setting for compound file on flush. This setting is realtime updateable.
     */
    public static final String INDEX_COMPOUND_ON_FLUSH = "index.compound_on_flush";

    /**
     * Setting to control auto generated ID optimizations. Default is <code>true</code> if not present.
     * This setting is <b>not</b> realtime updateable.
     */
    public static final String INDEX_OPTIMIZE_AUTOGENERATED_ID_SETTING = "index.optimize_auto_generated_id";

    /**
     * Index setting to enable / disable deletes garbage collection.
     * This setting is realtime updateable
     */
    public static final String INDEX_GC_DELETES_SETTING = "index.gc_deletes";

    /**
     * Index setting to control the initial index buffer size.
     * This setting is <b>not</b> realtime updateable.
     */
    public static final String INDEX_BUFFER_SIZE_SETTING = "index.buffer_size";

    /**
     * Index setting to change the low level lucene codec used for writing new segments.
     * This setting is <b>not</b> realtime updateable.
     */
    public static final String INDEX_CODEC_SETTING = "index.codec";

    /**
     * The maximum size the version map should grow to before issuing a refresh. Can be an absolute value or a percentage of
     * the current index memory buffer (defaults to 25%)
     */
    public static final String INDEX_VERSION_MAP_SIZE = "index.version_map_size";


    /** if set to true the engine will start even if the translog id in the commit point can not be found */
    public static final String INDEX_FORCE_NEW_TRANSLOG = "index.engine.force_new_translog";


    public static final TimeValue DEFAULT_REFRESH_INTERVAL = new TimeValue(1, TimeUnit.SECONDS);
    public static final TimeValue DEFAULT_GC_DELETES = TimeValue.timeValueSeconds(60);
    public static final ByteSizeValue DEFAULT_INDEX_BUFFER_SIZE = new ByteSizeValue(64, ByteSizeUnit.MB);
    public static final ByteSizeValue INACTIVE_SHARD_INDEXING_BUFFER = ByteSizeValue.parseBytesSizeValue("500kb", "INACTIVE_SHARD_INDEXING_BUFFER");

    public static final String DEFAULT_VERSION_MAP_SIZE = "25%";

    private static final String DEFAULT_CODEC_NAME = "default";
    private TranslogConfig translogConfig;


    /**
     * Creates a new {@link org.elasticsearch.index.engine.EngineConfig}
     */
    public EngineConfig(ShardId shardId, ThreadPool threadPool, ShardIndexingService indexingService,
                        IndexSettingsService indexSettingsService, IndicesWarmer warmer, Store store, SnapshotDeletionPolicy deletionPolicy,
                        MergePolicyProvider mergePolicyProvider, MergeSchedulerProvider mergeScheduler, Analyzer analyzer,
                        Similarity similarity, CodecService codecService, Engine.FailedEngineListener failedEngineListener,
                        TranslogRecoveryPerformer translogRecoveryPerformer, QueryCache filterCache, QueryCachingPolicy filterCachingPolicy, TranslogConfig translogConfig) {
        this.shardId = shardId;
        this.threadPool = threadPool;
        this.indexingService = indexingService;
        this.indexSettingsService = indexSettingsService;
        this.warmer = warmer;
        this.store = store;
        this.deletionPolicy = deletionPolicy;
        this.mergePolicyProvider = mergePolicyProvider;
        this.mergeScheduler = mergeScheduler;
        this.analyzer = analyzer;
        this.similarity = similarity;
        this.codecService = codecService;
        this.failedEngineListener = failedEngineListener;
        Settings indexSettings = indexSettingsService.getSettings();
        this.optimizeAutoGenerateId = indexSettings.getAsBoolean(EngineConfig.INDEX_OPTIMIZE_AUTOGENERATED_ID_SETTING, false);
        this.compoundOnFlush = indexSettings.getAsBoolean(EngineConfig.INDEX_COMPOUND_ON_FLUSH, compoundOnFlush);
        this.indexConcurrency = indexSettings.getAsInt(EngineConfig.INDEX_CONCURRENCY_SETTING, Math.max(IndexWriterConfig.DEFAULT_MAX_THREAD_STATES, (int) (EsExecutors.boundedNumberOfProcessors(indexSettings) * 0.65)));
        codecName = indexSettings.get(EngineConfig.INDEX_CODEC_SETTING, EngineConfig.DEFAULT_CODEC_NAME);
        indexingBufferSize = indexSettings.getAsBytesSize(INDEX_BUFFER_SIZE_SETTING, DEFAULT_INDEX_BUFFER_SIZE);
        gcDeletesInMillis = indexSettings.getAsTime(INDEX_GC_DELETES_SETTING, EngineConfig.DEFAULT_GC_DELETES).millis();
        versionMapSizeSetting = indexSettings.get(INDEX_VERSION_MAP_SIZE, DEFAULT_VERSION_MAP_SIZE);
        updateVersionMapSize();
        this.translogRecoveryPerformer = translogRecoveryPerformer;
        this.forceNewTranslog = indexSettings.getAsBoolean(INDEX_FORCE_NEW_TRANSLOG, false);
        this.filterCache = filterCache;
        this.filterCachingPolicy = filterCachingPolicy;
        this.translogConfig = translogConfig;
    }

    /** updates {@link #versionMapSize} based on current setting and {@link #indexingBufferSize} */
    private void updateVersionMapSize() {
        if (versionMapSizeSetting.endsWith("%")) {
            double percent = Double.parseDouble(versionMapSizeSetting.substring(0, versionMapSizeSetting.length() - 1));
            versionMapSize = new ByteSizeValue((long) (((double) indexingBufferSize.bytes() * (percent / 100))));
        } else {
            versionMapSize = ByteSizeValue.parseBytesSizeValue(versionMapSizeSetting, INDEX_VERSION_MAP_SIZE);
        }
    }

    /**
     * Settings the version map size that should trigger a refresh. See {@link #INDEX_VERSION_MAP_SIZE} for details.
     */
    public void setVersionMapSizeSetting(String versionMapSizeSetting) {
        this.versionMapSizeSetting = versionMapSizeSetting;
        updateVersionMapSize();
    }

    /**
     * current setting for the version map size that should trigger a refresh. See {@link #INDEX_VERSION_MAP_SIZE} for details.
     */
    public String getVersionMapSizeSetting() {
        return versionMapSizeSetting;
    }

    /** if true the engine will start even if the translog id in the commit point can not be found */
    public boolean forceNewTranslog() {
        return forceNewTranslog;
    }

    /**
     * returns the size of the version map that should trigger a refresh
     */
    public ByteSizeValue getVersionMapSize() {
        return versionMapSize;
    }

    /**
     * Sets the indexing buffer
     */
    public void setIndexingBufferSize(ByteSizeValue indexingBufferSize) {
        this.indexingBufferSize = indexingBufferSize;
        updateVersionMapSize();
    }

    /**
     * Enables / disables gc deletes
     *
     * @see #isEnableGcDeletes()
     */
    public void setEnableGcDeletes(boolean enableGcDeletes) {
        this.enableGcDeletes = enableGcDeletes;
    }

    /**
     * Returns the initial index buffer size. This setting is only read on startup and otherwise controlled by {@link org.elasticsearch.indices.memory.IndexingMemoryController}
     */
    public ByteSizeValue getIndexingBufferSize() {
        return indexingBufferSize;
    }

    /**
     * Returns the index concurrency that directly translates into the number of thread states used in the engines
     * {@code IndexWriter}.
     *
     * @see org.apache.lucene.index.IndexWriterConfig#getMaxThreadStates()
     */
    public int getIndexConcurrency() {
        return indexConcurrency;
    }

    /**
     * Returns <code>true</code> iff flushed segments should be written as compound file system. Defaults to <code>true</code>
     */
    public boolean isCompoundOnFlush() {
        return compoundOnFlush;
    }

    /**
     * Returns the GC deletes cycle in milliseconds.
     */
    public long getGcDeletesInMillis() {
        return gcDeletesInMillis;
    }

    /**
     * Returns <code>true</code> iff delete garbage collection in the engine should be enabled. This setting is updateable
     * in realtime and forces a volatile read. Consumers can safely read this value directly go fetch it's latest value. The default is <code>true</code>
     * <p>
     *     Engine GC deletion if enabled collects deleted documents from in-memory realtime data structures after a certain amount of
     *     time ({@link #getGcDeletesInMillis()} if enabled. Before deletes are GCed they will cause re-adding the document that was deleted
     *     to fail.
     * </p>
     */
    public boolean isEnableGcDeletes() {
        return enableGcDeletes;
    }

    /**
     * Returns the {@link Codec} used in the engines {@link org.apache.lucene.index.IndexWriter}
     * <p>
     *     Note: this settings is only read on startup.
     * </p>
     */
    public Codec getCodec() {
        return codecService.codec(codecName);
    }

    /**
     * Returns <code>true</code> iff documents with auto-generated IDs are optimized if possible. This mainly means that
     * they are simply appended to the index if no update call is necessary.
     */
    public boolean isOptimizeAutoGenerateId() {
        return optimizeAutoGenerateId;
    }

    /**
     * Returns a thread-pool mainly used to get estimated time stamps from {@link org.elasticsearch.threadpool.ThreadPool#estimatedTimeInMillis()} and to schedule
     * async force merge calls on the {@link org.elasticsearch.threadpool.ThreadPool.Names#OPTIMIZE} thread-pool
     */
    public ThreadPool getThreadPool() {
        return threadPool;
    }

    /**
     * Returns a {@link org.elasticsearch.index.indexing.ShardIndexingService} used inside the engine to inform about
     * pre and post index and create operations. The operations are used for statistic purposes etc.
     *
     * @see org.elasticsearch.index.indexing.ShardIndexingService#postCreate(org.elasticsearch.index.engine.Engine.Create)
     * @see org.elasticsearch.index.indexing.ShardIndexingService#preCreate(org.elasticsearch.index.engine.Engine.Create)
     *
     */
    public ShardIndexingService getIndexingService() {
        return indexingService;
    }

    /**
     * Returns an {@link org.elasticsearch.indices.IndicesWarmer} used to warm new searchers before they are used for searching.
     * Note: This method might retrun <code>null</code>
     */
    @Nullable
    public IndicesWarmer getWarmer() {
        return warmer;
    }

    /**
     * Returns the {@link org.elasticsearch.index.store.Store} instance that provides access to the {@link org.apache.lucene.store.Directory}
     * used for the engines {@link org.apache.lucene.index.IndexWriter} to write it's index files to.
     * <p>
     * Note: In order to use this instance the consumer needs to increment the stores reference before it's used the first time and hold
     * it's reference until it's not needed anymore.
     * </p>
     */
    public Store getStore() {
        return store;
    }

    /**
     * Returns a {@link org.elasticsearch.index.deletionpolicy.SnapshotDeletionPolicy} used in the engines
     * {@link org.apache.lucene.index.IndexWriter}.
     */
    public SnapshotDeletionPolicy getDeletionPolicy() {
        return deletionPolicy;
    }

    /**
     * Returns the {@link org.elasticsearch.index.merge.policy.MergePolicyProvider} used to obtain
     * a {@link org.apache.lucene.index.MergePolicy} for the engines {@link org.apache.lucene.index.IndexWriter}
     */
    public MergePolicyProvider getMergePolicyProvider() {
        return mergePolicyProvider;
    }

    /**
     * Returns the {@link org.elasticsearch.index.merge.scheduler.MergeSchedulerProvider} used to obtain
     * a {@link org.apache.lucene.index.MergeScheduler} for the engines {@link org.apache.lucene.index.IndexWriter}
     */
    public MergeSchedulerProvider getMergeScheduler() {
        return mergeScheduler;
    }

    /**
     * Returns a listener that should be called on engine failure
     */
    public Engine.FailedEngineListener getFailedEngineListener() {
        return failedEngineListener;
    }

    /**
     * Returns the latest index settings directly from the index settings service.
     */
    public Settings getIndexSettings() {
        return indexSettingsService.getSettings();
    }

    /**
     * Returns the engines shard ID
     */
    public ShardId getShardId() { return shardId; }

    /**
     * Returns the analyzer as the default analyzer in the engines {@link org.apache.lucene.index.IndexWriter}
     */
    public Analyzer getAnalyzer() {
        return analyzer;
    }

    /**
     * Returns the {@link org.apache.lucene.search.similarities.Similarity} used for indexing and searching.
     */
    public Similarity getSimilarity() {
        return similarity;
    }

    /**
     * Sets the GC deletes cycle in milliseconds.
     */
    public void setGcDeletesInMillis(long gcDeletesInMillis) {
        this.gcDeletesInMillis = gcDeletesInMillis;
    }

    /**
     * Sets if flushed segments should be written as compound file system. Defaults to <code>true</code>
     */
    public void setCompoundOnFlush(boolean compoundOnFlush) {
        this.compoundOnFlush = compoundOnFlush;
    }

    /**
     * Returns the {@link org.elasticsearch.index.shard.TranslogRecoveryPerformer} for this engine. This class is used
     * to apply transaction log operations to the engine. It encapsulates all the logic to transfer the translog entry into
     * an indexing operation.
     */
    public TranslogRecoveryPerformer getTranslogRecoveryPerformer() {
        return translogRecoveryPerformer;
    }

    /**
     * Return the cache to use for filters.
     */
    public QueryCache getFilterCache() {
        return filterCache;
    }

    /**
     * Return the policy to use when caching filters.
     */
    public QueryCachingPolicy getFilterCachingPolicy() {
        return filterCachingPolicy;
    }

    /**
     * Returns the translog config for this engine
     */
    public TranslogConfig getTranslogConfig() {
        return translogConfig;
    }

    IndexSettingsService getIndexSettingsService() { // for testing
        return indexSettingsService;
    }

}


File: core/src/main/java/org/elasticsearch/index/engine/InternalEngine.java
/*
 * Licensed to Elasticsearch under one or more contributor
 * license agreements. See the NOTICE file distributed with
 * this work for additional information regarding copyright
 * ownership. Elasticsearch licenses this file to you under
 * the Apache License, Version 2.0 (the "License"); you may
 * not use this file except in compliance with the License.
 * You may obtain a copy of the License at
 *
 *    http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing,
 * software distributed under the License is distributed on an
 * "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY
 * KIND, either express or implied.  See the License for the
 * specific language governing permissions and limitations
 * under the License.
 */

package org.elasticsearch.index.engine;

import com.google.common.collect.Lists;
import org.apache.lucene.index.*;
import org.apache.lucene.index.IndexWriter.IndexReaderWarmer;
import org.apache.lucene.search.BooleanClause.Occur;
import org.apache.lucene.search.*;
import org.apache.lucene.store.AlreadyClosedException;
import org.apache.lucene.store.LockObtainFailedException;
import org.apache.lucene.util.BytesRef;
import org.apache.lucene.util.IOUtils;
import org.apache.lucene.util.InfoStream;
import org.elasticsearch.ElasticsearchException;
import org.elasticsearch.cluster.routing.DjbHashFunction;
import org.elasticsearch.common.Nullable;
import org.elasticsearch.common.lease.Releasable;
import org.elasticsearch.common.logging.ESLogger;
import org.elasticsearch.common.lucene.LoggerInfoStream;
import org.elasticsearch.common.lucene.Lucene;
import org.elasticsearch.common.lucene.index.ElasticsearchDirectoryReader;
import org.elasticsearch.common.lucene.uid.Versions;
import org.elasticsearch.common.math.MathUtils;
import org.elasticsearch.common.util.concurrent.EsRejectedExecutionException;
import org.elasticsearch.common.util.concurrent.ReleasableLock;
import org.elasticsearch.index.deletionpolicy.SnapshotIndexCommit;
import org.elasticsearch.index.indexing.ShardIndexingService;
import org.elasticsearch.index.mapper.Uid;
import org.elasticsearch.index.merge.OnGoingMerge;
import org.elasticsearch.index.merge.policy.ElasticsearchMergePolicy;
import org.elasticsearch.index.merge.policy.MergePolicyProvider;
import org.elasticsearch.index.merge.scheduler.MergeSchedulerProvider;
import org.elasticsearch.index.search.nested.IncludeNestedDocsQuery;
import org.elasticsearch.index.shard.ShardId;
import org.elasticsearch.index.shard.TranslogRecoveryPerformer;
import org.elasticsearch.index.translog.Translog;
import org.elasticsearch.index.translog.TranslogConfig;
import org.elasticsearch.index.translog.TranslogCorruptedException;
import org.elasticsearch.indices.IndicesWarmer;
import org.elasticsearch.rest.RestStatus;
import org.elasticsearch.threadpool.ThreadPool;

import java.io.IOException;
import java.util.*;
import java.util.concurrent.atomic.AtomicBoolean;
import java.util.concurrent.atomic.AtomicInteger;
import java.util.concurrent.locks.Lock;
import java.util.concurrent.locks.ReentrantLock;

/**
 *
 */
public class InternalEngine extends Engine {
    private final FailEngineOnMergeFailure mergeSchedulerFailureListener;
    private final MergeSchedulerListener mergeSchedulerListener;

    /**
     * When we last pruned expired tombstones from versionMap.deletes:
     */
    private volatile long lastDeleteVersionPruneTimeMSec;

    private final ShardIndexingService indexingService;
    @Nullable
    private final IndicesWarmer warmer;
    private final Translog translog;
    private final MergePolicyProvider mergePolicyProvider;
    private final MergeSchedulerProvider mergeScheduler;

    private final IndexWriter indexWriter;

    private final SearcherFactory searcherFactory;
    private final SearcherManager searcherManager;

    private final Lock flushLock = new ReentrantLock();
    private final ReentrantLock optimizeLock = new ReentrantLock();

    // A uid (in the form of BytesRef) to the version map
    // we use the hashed variant since we iterate over it and check removal and additions on existing keys
    private final LiveVersionMap versionMap;

    private final Object[] dirtyLocks;

    private final AtomicBoolean versionMapRefreshPending = new AtomicBoolean();

    private volatile SegmentInfos lastCommittedSegmentInfos;

    private final IndexThrottle throttle;

    public InternalEngine(EngineConfig engineConfig, boolean skipInitialTranslogRecovery) throws EngineException {
        super(engineConfig);
        this.versionMap = new LiveVersionMap();
        store.incRef();
        IndexWriter writer = null;
        Translog translog = null;
        SearcherManager manager = null;
        boolean success = false;
        try {
            this.lastDeleteVersionPruneTimeMSec = engineConfig.getThreadPool().estimatedTimeInMillis();
            this.indexingService = engineConfig.getIndexingService();
            this.warmer = engineConfig.getWarmer();
            this.mergePolicyProvider = engineConfig.getMergePolicyProvider();
            this.mergeScheduler = engineConfig.getMergeScheduler();
            this.dirtyLocks = new Object[engineConfig.getIndexConcurrency() * 50]; // we multiply it to have enough...
            for (int i = 0; i < dirtyLocks.length; i++) {
                dirtyLocks[i] = new Object();
            }

            throttle = new IndexThrottle();
            this.searcherFactory = new SearchFactory(logger, isClosed, engineConfig);
            final Translog.TranslogGeneration translogGeneration;
            try {
                // TODO: would be better if ES could tell us "from above" whether this shard was already here, instead of using Lucene's API
                // (which relies on IO ops, directory listing, and has had scary bugs in the past):
                boolean create = !Lucene.indexExists(store.directory());
                writer = createWriter(create);
                indexWriter = writer;
                translog = openTranslog(engineConfig, writer, create || skipInitialTranslogRecovery || engineConfig.forceNewTranslog());
                translogGeneration = translog.getGeneration();
                assert translogGeneration != null;
            } catch (IOException | TranslogCorruptedException e) {
                throw new EngineCreationFailureException(shardId, "failed to create engine", e);
            }
            this.translog = translog;
            manager = createSearcherManager();
            this.searcherManager = manager;
            this.versionMap.setManager(searcherManager);
            this.mergeSchedulerFailureListener = new FailEngineOnMergeFailure();
            this.mergeSchedulerListener = new MergeSchedulerListener();
            this.mergeScheduler.addListener(mergeSchedulerListener);
            this.mergeScheduler.addFailureListener(mergeSchedulerFailureListener);
            try {
                if (skipInitialTranslogRecovery) {
                    // make sure we point at the latest translog from now on..
                    commitIndexWriter(writer, translog, lastCommittedSegmentInfos.getUserData().get(SYNC_COMMIT_ID));
                } else {
                    recoverFromTranslog(engineConfig, translogGeneration);
                }
            } catch (IOException | EngineException ex) {
                throw new EngineCreationFailureException(shardId, "failed to recover from translog", ex);
            }
            success = true;
        } finally {
            if (success == false) {
                IOUtils.closeWhileHandlingException(writer, translog, manager);
                versionMap.clear();
                if (isClosed.get() == false) {
                    // failure we need to dec the store reference
                    store.decRef();
                }
            }
        }
        logger.trace("created new InternalEngine");
    }

    private Translog openTranslog(EngineConfig engineConfig, IndexWriter writer, boolean createNew) throws IOException {
        final Translog.TranslogGeneration generation = loadTranslogIdFromCommit(writer);
        final TranslogConfig translogConfig = engineConfig.getTranslogConfig();

        if (createNew == false) {
            // We expect that this shard already exists, so it must already have an existing translog else something is badly wrong!
            if (generation == null) {
                throw new IllegalStateException("no translog generation present in commit data but translog is expected to exist");
            }
            translogConfig.setTranslogGeneration(generation);
            if (generation != null && generation.translogUUID == null) {
                // only upgrade on pre-2.0 indices...
                Translog.upgradeLegacyTranslog(logger, translogConfig);
            }
        }
        final Translog translog = new Translog(translogConfig);
        if (generation == null) {
            logger.debug("no translog ID present in the current generation - creating one");
            boolean success = false;
            try {
                commitIndexWriter(writer, translog);
                success = true;
            } finally {
                if (success == false) {
                    IOUtils.closeWhileHandlingException(translog);
                }
            }
        }
        return translog;
    }

    @Override
    public Translog getTranslog() {
        ensureOpen();
        return translog;
    }

    protected void recoverFromTranslog(EngineConfig engineConfig, Translog.TranslogGeneration translogGeneration) throws IOException {
        int opsRecovered = 0;
        final TranslogRecoveryPerformer handler = engineConfig.getTranslogRecoveryPerformer();
        try (Translog.Snapshot snapshot = translog.newSnapshot()) {
            Translog.Operation operation;
            while ((operation = snapshot.next()) != null) {
                try {
                    handler.performRecoveryOperation(this, operation, true);
                    opsRecovered++;
                } catch (ElasticsearchException e) {
                    if (e.status() == RestStatus.BAD_REQUEST) {
                        // mainly for MapperParsingException and Failure to detect xcontent
                        logger.info("ignoring recovery of a corrupt translog entry", e);
                    } else {
                        throw e;
                    }
                }
            }
        } catch (Throwable e) {
            throw new EngineException(shardId, "failed to recover from translog", e);
        }

        // flush if we recovered something or if we have references to older translogs
        // note: if opsRecovered == 0 and we have older translogs it means they are corrupted or 0 length.
        if (opsRecovered > 0) {
            logger.trace("flushing post recovery from translog. ops recovered [{}]. committed translog id [{}]. current id [{}]",
                    opsRecovered, translogGeneration == null ? null : translogGeneration.translogFileGeneration, translog.currentFileGeneration());
            flush(true, true);
        } else if (translog.isCurrent(translogGeneration) == false){
            commitIndexWriter(indexWriter, translog, lastCommittedSegmentInfos.getUserData().get(Engine.SYNC_COMMIT_ID));
        }
    }

    /**
     * Reads the current stored translog ID from the IW commit data. If the id is not found, recommits the current
     * translog id into lucene and returns null.
     */
    @Nullable
    private Translog.TranslogGeneration loadTranslogIdFromCommit(IndexWriter writer) throws IOException {
        // commit on a just opened writer will commit even if there are no changes done to it
        // we rely on that for the commit data translog id key
        final Map<String, String> commitUserData = writer.getCommitData();
        if (commitUserData.containsKey("translog_id")) {
            assert commitUserData.containsKey(Translog.TRANSLOG_UUID_KEY) == false : "legacy commit contains translog UUID";
            return new Translog.TranslogGeneration(null, Long.parseLong(commitUserData.get("translog_id")));
        } else if (commitUserData.containsKey(Translog.TRANSLOG_GENERATION_KEY)) {
            if (commitUserData.containsKey(Translog.TRANSLOG_UUID_KEY) == false) {
                throw new IllegalStateException("commit doesn't contain translog UUID");
            }
            final String translogUUID = commitUserData.get(Translog.TRANSLOG_UUID_KEY);
            final long translogGen = Long.parseLong(commitUserData.get(Translog.TRANSLOG_GENERATION_KEY));
            return new Translog.TranslogGeneration(translogUUID, translogGen);
        }
        return null;
    }

    private SearcherManager createSearcherManager() throws EngineException {
        boolean success = false;
        SearcherManager searcherManager = null;
        try {
            try {
                final DirectoryReader directoryReader = ElasticsearchDirectoryReader.wrap(DirectoryReader.open(indexWriter, true), shardId);
                searcherManager = new SearcherManager(directoryReader, searcherFactory);
                lastCommittedSegmentInfos = readLastCommittedSegmentInfos(searcherManager, store);
                success = true;
                return searcherManager;
            } catch (IOException e) {
                maybeFailEngine("start", e);
                try {
                    indexWriter.rollback();
                } catch (IOException e1) { // iw is closed below
                    e.addSuppressed(e1);
                }
                throw new EngineCreationFailureException(shardId, "failed to open reader on writer", e);
            }
        } finally {
            if (success == false) { // release everything we created on a failure
                IOUtils.closeWhileHandlingException(searcherManager, indexWriter);
            }
        }
    }

    private void updateIndexWriterSettings() {
        try {
            final LiveIndexWriterConfig iwc = indexWriter.getConfig();
            iwc.setRAMBufferSizeMB(engineConfig.getIndexingBufferSize().mbFrac());
            iwc.setUseCompoundFile(engineConfig.isCompoundOnFlush());
        } catch (AlreadyClosedException ex) {
            // ignore
        }
    }

    @Override
    public GetResult get(Get get) throws EngineException {
        try (ReleasableLock lock = readLock.acquire()) {
            ensureOpen();
            if (get.realtime()) {
                VersionValue versionValue = versionMap.getUnderLock(get.uid().bytes());
                if (versionValue != null) {
                    if (versionValue.delete()) {
                        return GetResult.NOT_EXISTS;
                    }
                    if (get.versionType().isVersionConflictForReads(versionValue.version(), get.version())) {
                        Uid uid = Uid.createUid(get.uid().text());
                        throw new VersionConflictEngineException(shardId, uid.type(), uid.id(), versionValue.version(), get.version());
                    }
                    if (!get.loadSource()) {
                        return new GetResult(true, versionValue.version(), null);
                    }
                    Translog.Operation op = translog.read(versionValue.translogLocation());
                    if (op != null) {
                        return new GetResult(true, versionValue.version(), op.getSource());
                    }
                }
            }

            // no version, get the version from the index, we know that we refresh on flush
            return getFromSearcher(get);
        }
    }

    @Override
    public void create(Create create) throws EngineException {
        try (ReleasableLock lock = readLock.acquire()) {
            ensureOpen();
            if (create.origin() == Operation.Origin.RECOVERY) {
                // Don't throttle recovery operations
                innerCreate(create);
            } else {
                try (Releasable r = throttle.acquireThrottle()) {
                    innerCreate(create);
                }
            }
        } catch (OutOfMemoryError | IllegalStateException | IOException t) {
            maybeFailEngine("create", t);
            throw new CreateFailedEngineException(shardId, create, t);
        }
        checkVersionMapRefresh();
    }

    private void innerCreate(Create create) throws IOException {
        if (engineConfig.isOptimizeAutoGenerateId() && create.autoGeneratedId() && !create.canHaveDuplicates()) {
            // We don't need to lock because this ID cannot be concurrently updated:
            innerCreateNoLock(create, Versions.NOT_FOUND, null);
        } else {
            synchronized (dirtyLock(create.uid())) {
                final long currentVersion;
                final VersionValue versionValue;
                versionValue = versionMap.getUnderLock(create.uid().bytes());
                if (versionValue == null) {
                    currentVersion = loadCurrentVersionFromIndex(create.uid());
                } else {
                    if (engineConfig.isEnableGcDeletes() && versionValue.delete() && (engineConfig.getThreadPool().estimatedTimeInMillis() - versionValue.time()) > engineConfig.getGcDeletesInMillis()) {
                        currentVersion = Versions.NOT_FOUND; // deleted, and GC
                    } else {
                        currentVersion = versionValue.version();
                    }
                }
                innerCreateNoLock(create, currentVersion, versionValue);
            }
        }
    }

    private void innerCreateNoLock(Create create, long currentVersion, VersionValue versionValue) throws IOException {

        // same logic as index
        long updatedVersion;
        long expectedVersion = create.version();
        if (create.versionType().isVersionConflictForWrites(currentVersion, expectedVersion)) {
            if (create.origin() == Operation.Origin.RECOVERY) {
                return;
            } else {
                throw new VersionConflictEngineException(shardId, create.type(), create.id(), currentVersion, expectedVersion);
            }
        }
        updatedVersion = create.versionType().updateVersion(currentVersion, expectedVersion);

        // if the doc exists
        boolean doUpdate = false;
        if ((versionValue != null && versionValue.delete() == false) || (versionValue == null && currentVersion != Versions.NOT_FOUND)) {
            if (create.origin() == Operation.Origin.RECOVERY) {
                return;
            } else if (create.origin() == Operation.Origin.REPLICA) {
                // #7142: the primary already determined it's OK to index this document, and we confirmed above that the version doesn't
                // conflict, so we must also update here on the replica to remain consistent:
                doUpdate = true;
            } else if (create.origin() == Operation.Origin.PRIMARY && create.autoGeneratedId() && create.canHaveDuplicates() && currentVersion == 1 && create.version() == Versions.MATCH_ANY) {
                /**
                 * If bulk index request fails due to a disconnect, unavailable shard etc. then the request is
                 * retried before it actually fails. However, the documents might already be indexed.
                 * For autogenerated ids this means that a version conflict will be reported in the bulk request
                 * although the document was indexed properly.
                 * To avoid this we have to make sure that the index request is treated as an update and set updatedVersion to 1.
                 * See also discussion on https://github.com/elasticsearch/elasticsearch/pull/9125
                 */
                doUpdate = true;
                updatedVersion = 1;
            } else {
                // On primary, we throw DAEE if the _uid is already in the index with an older version:
                assert create.origin() == Operation.Origin.PRIMARY;
                throw new DocumentAlreadyExistsException(shardId, create.type(), create.id());
            }
        }

        create.updateVersion(updatedVersion);

        if (doUpdate) {
            if (create.docs().size() > 1) {
                indexWriter.updateDocuments(create.uid(), create.docs());
            } else {
                indexWriter.updateDocument(create.uid(), create.docs().get(0));
            }
        } else {
            if (create.docs().size() > 1) {
                indexWriter.addDocuments(create.docs());
            } else {
                indexWriter.addDocument(create.docs().get(0));
            }
        }
        Translog.Location translogLocation = translog.add(new Translog.Create(create));

        versionMap.putUnderLock(create.uid().bytes(), new VersionValue(updatedVersion, translogLocation));
        create.setTranslogLocation(translogLocation);
        indexingService.postCreateUnderLock(create);
    }

    @Override
    public boolean index(Index index) throws EngineException {
        final boolean created;
        try (ReleasableLock lock = readLock.acquire()) {
            ensureOpen();
            if (index.origin() == Operation.Origin.RECOVERY) {
                // Don't throttle recovery operations
                created = innerIndex(index);
            } else {
                try (Releasable r = throttle.acquireThrottle()) {
                    created = innerIndex(index);
                }
            }
        } catch (OutOfMemoryError | IllegalStateException | IOException t) {
            maybeFailEngine("index", t);
            throw new IndexFailedEngineException(shardId, index, t);
        }
        checkVersionMapRefresh();
        return created;
    }

    /**
     * Forces a refresh if the versionMap is using too much RAM
     */
    private void checkVersionMapRefresh() {
        if (versionMap.ramBytesUsedForRefresh() > config().getVersionMapSize().bytes() && versionMapRefreshPending.getAndSet(true) == false) {
            try {
                if (isClosed.get()) {
                    // no point...
                    return;
                }
                // Now refresh to clear versionMap:
                engineConfig.getThreadPool().executor(ThreadPool.Names.REFRESH).execute(new Runnable() {
                    @Override
                    public void run() {
                        try {
                            refresh("version_table_full");
                        } catch (EngineClosedException ex) {
                            // ignore
                        }
                    }
                });
            } catch (EsRejectedExecutionException ex) {
                // that is fine too.. we might be shutting down
            }
        }
    }

    private boolean innerIndex(Index index) throws IOException {
        synchronized (dirtyLock(index.uid())) {
            final long currentVersion;
            VersionValue versionValue = versionMap.getUnderLock(index.uid().bytes());
            if (versionValue == null) {
                currentVersion = loadCurrentVersionFromIndex(index.uid());
            } else {
                if (engineConfig.isEnableGcDeletes() && versionValue.delete() && (engineConfig.getThreadPool().estimatedTimeInMillis() - versionValue.time()) > engineConfig.getGcDeletesInMillis()) {
                    currentVersion = Versions.NOT_FOUND; // deleted, and GC
                } else {
                    currentVersion = versionValue.version();
                }
            }

            long updatedVersion;
            long expectedVersion = index.version();
            if (index.versionType().isVersionConflictForWrites(currentVersion, expectedVersion)) {
                if (index.origin() == Operation.Origin.RECOVERY) {
                    return false;
                } else {
                    throw new VersionConflictEngineException(shardId, index.type(), index.id(), currentVersion, expectedVersion);
                }
            }
            updatedVersion = index.versionType().updateVersion(currentVersion, expectedVersion);

            final boolean created;
            index.updateVersion(updatedVersion);
            if (currentVersion == Versions.NOT_FOUND) {
                // document does not exists, we can optimize for create
                created = true;
                if (index.docs().size() > 1) {
                    indexWriter.addDocuments(index.docs());
                } else {
                    indexWriter.addDocument(index.docs().get(0));
                }
            } else {
                if (versionValue != null) {
                    created = versionValue.delete(); // we have a delete which is not GC'ed...
                } else {
                    created = false;
                }
                if (index.docs().size() > 1) {
                    indexWriter.updateDocuments(index.uid(), index.docs());
                } else {
                    indexWriter.updateDocument(index.uid(), index.docs().get(0));
                }
            }
            Translog.Location translogLocation = translog.add(new Translog.Index(index));

            versionMap.putUnderLock(index.uid().bytes(), new VersionValue(updatedVersion, translogLocation));
            index.setTranslogLocation(translogLocation);
            indexingService.postIndexUnderLock(index);
            return created;
        }
    }

    @Override
    public void delete(Delete delete) throws EngineException {
        try (ReleasableLock lock = readLock.acquire()) {
            ensureOpen();
            // NOTE: we don't throttle this when merges fall behind because delete-by-id does not create new segments:
            innerDelete(delete);
        } catch (OutOfMemoryError | IllegalStateException | IOException t) {
            maybeFailEngine("delete", t);
            throw new DeleteFailedEngineException(shardId, delete, t);
        }

        maybePruneDeletedTombstones();
        checkVersionMapRefresh();
    }

    private void maybePruneDeletedTombstones() {
        // It's expensive to prune because we walk the deletes map acquiring dirtyLock for each uid so we only do it
        // every 1/4 of gcDeletesInMillis:
        if (engineConfig.isEnableGcDeletes() && engineConfig.getThreadPool().estimatedTimeInMillis() - lastDeleteVersionPruneTimeMSec > engineConfig.getGcDeletesInMillis() * 0.25) {
            pruneDeletedTombstones();
        }
    }

    private void innerDelete(Delete delete) throws IOException {
        synchronized (dirtyLock(delete.uid())) {
            final long currentVersion;
            VersionValue versionValue = versionMap.getUnderLock(delete.uid().bytes());
            if (versionValue == null) {
                currentVersion = loadCurrentVersionFromIndex(delete.uid());
            } else {
                if (engineConfig.isEnableGcDeletes() && versionValue.delete() && (engineConfig.getThreadPool().estimatedTimeInMillis() - versionValue.time()) > engineConfig.getGcDeletesInMillis()) {
                    currentVersion = Versions.NOT_FOUND; // deleted, and GC
                } else {
                    currentVersion = versionValue.version();
                }
            }

            long updatedVersion;
            long expectedVersion = delete.version();
            if (delete.versionType().isVersionConflictForWrites(currentVersion, expectedVersion)) {
                if (delete.origin() == Operation.Origin.RECOVERY) {
                    return;
                } else {
                    throw new VersionConflictEngineException(shardId, delete.type(), delete.id(), currentVersion, expectedVersion);
                }
            }
            updatedVersion = delete.versionType().updateVersion(currentVersion, expectedVersion);
            final boolean found;
            if (currentVersion == Versions.NOT_FOUND) {
                // doc does not exist and no prior deletes
                found = false;
            } else if (versionValue != null && versionValue.delete()) {
                // a "delete on delete", in this case, we still increment the version, log it, and return that version
                found = false;
            } else {
                // we deleted a currently existing document
                indexWriter.deleteDocuments(delete.uid());
                found = true;
            }

            delete.updateVersion(updatedVersion, found);
            Translog.Location translogLocation = translog.add(new Translog.Delete(delete));
            versionMap.putUnderLock(delete.uid().bytes(), new DeleteVersionValue(updatedVersion, engineConfig.getThreadPool().estimatedTimeInMillis(), translogLocation));
            delete.setTranslogLocation(translogLocation);
            indexingService.postDeleteUnderLock(delete);
        }
    }

    /** @deprecated This was removed, but we keep this API so translog can replay any DBQs on upgrade. */
    @Deprecated
    @Override
    public void delete(DeleteByQuery delete) throws EngineException {
        try (ReleasableLock lock = readLock.acquire()) {
            ensureOpen();
            if (delete.origin() == Operation.Origin.RECOVERY) {
                // Don't throttle recovery operations
                innerDelete(delete);
            } else {
                try (Releasable r = throttle.acquireThrottle()) {
                    innerDelete(delete);
                }
            }
        }
    }

    private void innerDelete(DeleteByQuery delete) throws EngineException {
        try {
            Query query = delete.query();
            if (delete.aliasFilter() != null) {
                BooleanQuery boolQuery = new BooleanQuery();
                boolQuery.add(query, Occur.MUST);
                boolQuery.add(delete.aliasFilter(), Occur.FILTER);
                query = boolQuery;
            }
            if (delete.nested()) {
                query = new IncludeNestedDocsQuery(query, delete.parentFilter());
            }

            indexWriter.deleteDocuments(query);
            translog.add(new Translog.DeleteByQuery(delete));
        } catch (Throwable t) {
            maybeFailEngine("delete_by_query", t);
            throw new DeleteByQueryFailedEngineException(shardId, delete, t);
        }

        // TODO: This is heavy, since we refresh, but we must do this because we don't know which documents were in fact deleted (i.e., our
        // versionMap isn't updated), so we must force a cutover to a new reader to "see" the deletions:
        refresh("delete_by_query");
    }

    @Override
    public void refresh(String source) throws EngineException {
        // we obtain a read lock here, since we don't want a flush to happen while we are refreshing
        // since it flushes the index as well (though, in terms of concurrency, we are allowed to do it)
        try (ReleasableLock lock = readLock.acquire()) {
            ensureOpen();
            updateIndexWriterSettings();
            searcherManager.maybeRefreshBlocking();
        } catch (AlreadyClosedException e) {
            ensureOpen();
            maybeFailEngine("refresh", e);
        } catch (EngineClosedException e) {
            throw e;
        } catch (Throwable t) {
            failEngine("refresh failed", t);
            throw new RefreshFailedEngineException(shardId, t);
        }

        // TODO: maybe we should just put a scheduled job in threadPool?
        // We check for pruning in each delete request, but we also prune here e.g. in case a delete burst comes in and then no more deletes
        // for a long time:
        maybePruneDeletedTombstones();
        versionMapRefreshPending.set(false);
    }

    @Override
    public SyncedFlushResult syncFlush(String syncId, CommitId expectedCommitId) throws EngineException {
        // best effort attempt before we acquire locks
        ensureOpen();
        if (indexWriter.hasUncommittedChanges()) {
            logger.trace("can't sync commit [{}]. have pending changes", syncId);
            return SyncedFlushResult.PENDING_OPERATIONS;
        }
        if (expectedCommitId.idsEqual(lastCommittedSegmentInfos.getId()) == false) {
            logger.trace("can't sync commit [{}]. current commit id is not equal to expected.", syncId);
            return SyncedFlushResult.COMMIT_MISMATCH;
        }
        try (ReleasableLock lock = writeLock.acquire()) {
            ensureOpen();
            if (indexWriter.hasUncommittedChanges()) {
                logger.trace("can't sync commit [{}]. have pending changes", syncId);
                return SyncedFlushResult.PENDING_OPERATIONS;
            }
            if (expectedCommitId.idsEqual(lastCommittedSegmentInfos.getId()) == false) {
                logger.trace("can't sync commit [{}]. current commit id is not equal to expected.", syncId);
                return SyncedFlushResult.COMMIT_MISMATCH;
            }
            logger.trace("starting sync commit [{}]", syncId);
            commitIndexWriter(indexWriter, translog, syncId);
            logger.debug("successfully sync committed. sync id [{}].", syncId);
            lastCommittedSegmentInfos = store.readLastCommittedSegmentsInfo();
            return SyncedFlushResult.SUCCESS;
        } catch (IOException ex) {
            maybeFailEngine("sync commit", ex);
            throw new EngineException(shardId, "failed to sync commit", ex);
        }
    }

    @Override
    public CommitId flush() throws EngineException {
        return flush(false, false);
    }

    @Override
    public CommitId flush(boolean force, boolean waitIfOngoing) throws EngineException {
        ensureOpen();
        final byte[] newCommitId;
        /*
         * Unfortunately the lock order is important here. We have to acquire the readlock first otherwise
         * if we are flushing at the end of the recovery while holding the write lock we can deadlock if:
         *  Thread 1: flushes via API and gets the flush lock but blocks on the readlock since Thread 2 has the writeLock
         *  Thread 2: flushes at the end of the recovery holding the writeLock and blocks on the flushLock owned by Thread 1
         */
        try (ReleasableLock lock = readLock.acquire()) {
            ensureOpen();
            updateIndexWriterSettings();
            if (flushLock.tryLock() == false) {
                // if we can't get the lock right away we block if needed otherwise barf
                if (waitIfOngoing) {
                    logger.trace("waiting for in-flight flush to finish");
                    flushLock.lock();
                    logger.trace("acquired flush lock after blocking");
                } else {
                    throw new FlushNotAllowedEngineException(shardId, "already flushing...");
                }
            } else {
                logger.trace("acquired flush lock immediately");
            }
            try {
                if (indexWriter.hasUncommittedChanges() || force) {
                    try {
                        translog.prepareCommit();
                        logger.trace("starting commit for flush; commitTranslog=true");
                        commitIndexWriter(indexWriter, translog);
                        logger.trace("finished commit for flush");
                        translog.commit();
                        // we need to refresh in order to clear older version values
                        refresh("version_table_flush");
                    } catch (Throwable e) {
                        throw new FlushFailedEngineException(shardId, e);
                    }
                }
                /*
                 * we have to inc-ref the store here since if the engine is closed by a tragic event
                 * we don't acquire the write lock and wait until we have exclusive access. This might also
                 * dec the store reference which can essentially close the store and unless we can inc the reference
                 * we can't use it.
                 */
                store.incRef();
                try {
                    // reread the last committed segment infos
                    lastCommittedSegmentInfos = store.readLastCommittedSegmentsInfo();
                } catch (Throwable e) {
                    if (isClosed.get() == false) {
                        logger.warn("failed to read latest segment infos on flush", e);
                        if (Lucene.isCorruptionException(e)) {
                            throw new FlushFailedEngineException(shardId, e);
                        }
                    }
                } finally {
                    store.decRef();
                }
                newCommitId = lastCommittedSegmentInfos.getId();
            } catch (FlushFailedEngineException ex) {
                maybeFailEngine("flush", ex);
                throw ex;
            } finally {
                flushLock.unlock();
            }
        }
        // We don't have to do this here; we do it defensively to make sure that even if wall clock time is misbehaving
        // (e.g., moves backwards) we will at least still sometimes prune deleted tombstones:
        if (engineConfig.isEnableGcDeletes()) {
            pruneDeletedTombstones();
        }
        return new CommitId(newCommitId);
    }

    private void pruneDeletedTombstones() {
        long timeMSec = engineConfig.getThreadPool().estimatedTimeInMillis();

        // TODO: not good that we reach into LiveVersionMap here; can we move this inside VersionMap instead?  problem is the dirtyLock...

        // we only need to prune the deletes map; the current/old version maps are cleared on refresh:
        for (Map.Entry<BytesRef, VersionValue> entry : versionMap.getAllTombstones()) {
            BytesRef uid = entry.getKey();
            synchronized (dirtyLock(uid)) { // can we do it without this lock on each value? maybe batch to a set and get the lock once per set?

                // Must re-get it here, vs using entry.getValue(), in case the uid was indexed/deleted since we pulled the iterator:
                VersionValue versionValue = versionMap.getTombstoneUnderLock(uid);
                if (versionValue != null) {
                    if (timeMSec - versionValue.time() > engineConfig.getGcDeletesInMillis()) {
                        versionMap.removeTombstoneUnderLock(uid);
                    }
                }
            }
        }

        lastDeleteVersionPruneTimeMSec = timeMSec;
    }

    @Override
    public void forceMerge(final boolean flush, int maxNumSegments, boolean onlyExpungeDeletes,
                           final boolean upgrade, final boolean upgradeOnlyAncientSegments) throws EngineException {
        /*
         * We do NOT acquire the readlock here since we are waiting on the merges to finish
         * that's fine since the IW.rollback should stop all the threads and trigger an IOException
         * causing us to fail the forceMerge
         *
         * The way we implement upgrades is a bit hackish in the sense that we set an instance
         * variable and that this setting will thus apply to the next forced merge that will be run.
         * This is ok because (1) this is the only place we call forceMerge, (2) we have a single
         * thread for optimize, and the 'optimizeLock' guarding this code, and (3) ConcurrentMergeScheduler
         * syncs calls to findForcedMerges.
         */
        assert indexWriter.getConfig().getMergePolicy() instanceof ElasticsearchMergePolicy : "MergePolicy is " + indexWriter.getConfig().getMergePolicy().getClass().getName();
        ElasticsearchMergePolicy mp = (ElasticsearchMergePolicy) indexWriter.getConfig().getMergePolicy();
        optimizeLock.lock();
        try {
            ensureOpen();
            if (upgrade) {
                logger.info("starting segment upgrade upgradeOnlyAncientSegments={}", upgradeOnlyAncientSegments);
                mp.setUpgradeInProgress(true, upgradeOnlyAncientSegments);
            }
            store.incRef(); // increment the ref just to ensure nobody closes the store while we optimize
            try {
                if (onlyExpungeDeletes) {
                    assert upgrade == false;
                    indexWriter.forceMergeDeletes(true /* blocks and waits for merges*/);
                } else if (maxNumSegments <= 0) {
                    assert upgrade == false;
                    indexWriter.maybeMerge();
                } else {
                    indexWriter.forceMerge(maxNumSegments, true /* blocks and waits for merges*/);
                }
                if (flush) {
                    flush(true, true);
                }
                if (upgrade) {
                    logger.info("finished segment upgrade");
                }
            } finally {
                store.decRef();
            }
        } catch (Throwable t) {
            ForceMergeFailedEngineException ex = new ForceMergeFailedEngineException(shardId, t);
            maybeFailEngine("force merge", ex);
            throw ex;
        } finally {
            try {
                mp.setUpgradeInProgress(false, false); // reset it just to make sure we reset it in a case of an error
            } finally {
                optimizeLock.unlock();
            }
        }
    }

    @Override
    public SnapshotIndexCommit snapshotIndex(final boolean flushFirst) throws EngineException {
        // we have to flush outside of the readlock otherwise we might have a problem upgrading
        // the to a write lock when we fail the engine in this operation
        if (flushFirst) {
            logger.trace("start flush for snapshot");
            flush(false, true);
            logger.trace("finish flush for snapshot");
        }
        try (ReleasableLock lock = readLock.acquire()) {
            ensureOpen();
            logger.trace("pulling snapshot");
            return deletionPolicy.snapshot();
        } catch (IOException e) {
            throw new SnapshotFailedEngineException(shardId, e);
        }
    }

    @Override
    protected boolean maybeFailEngine(String source, Throwable t) {
        boolean shouldFail = super.maybeFailEngine(source, t);
        if (shouldFail) {
            return true;
        }

        // Check for AlreadyClosedException
        if (t instanceof AlreadyClosedException) {
            // if we are already closed due to some tragic exception
            // we need to fail the engine. it might have already been failed before
            // but we are double-checking it's failed and closed
            if (indexWriter.isOpen() == false && indexWriter.getTragicException() != null) {
                failEngine("already closed by tragic event", indexWriter.getTragicException());
            }
            return true;
        } else if (t != null && indexWriter.isOpen() == false && indexWriter.getTragicException() == t) {
            // this spot on - we are handling the tragic event exception here so we have to fail the engine
            // right away
            failEngine(source, t);
            return true;
        }
        return false;
    }

    @Override
    protected SegmentInfos getLastCommittedSegmentInfos() {
        return lastCommittedSegmentInfos;
    }

    @Override
    protected final void writerSegmentStats(SegmentsStats stats) {
        stats.addVersionMapMemoryInBytes(versionMap.ramBytesUsed());
        stats.addIndexWriterMemoryInBytes(indexWriter.ramBytesUsed());
        stats.addIndexWriterMaxMemoryInBytes((long) (indexWriter.getConfig().getRAMBufferSizeMB() * 1024 * 1024));
    }

    @Override
    public List<Segment> segments(boolean verbose) {
        try (ReleasableLock lock = readLock.acquire()) {
            Segment[] segmentsArr = getSegmentInfo(lastCommittedSegmentInfos, verbose);

            // fill in the merges flag
            Set<OnGoingMerge> onGoingMerges = mergeScheduler.onGoingMerges();
            for (OnGoingMerge onGoingMerge : onGoingMerges) {
                for (SegmentCommitInfo segmentInfoPerCommit : onGoingMerge.getMergedSegments()) {
                    for (Segment segment : segmentsArr) {
                        if (segment.getName().equals(segmentInfoPerCommit.info.name)) {
                            segment.mergeId = onGoingMerge.getId();
                            break;
                        }
                    }
                }
            }
            return Arrays.asList(segmentsArr);
        }
    }


    /**
     * Closes the engine without acquiring the write lock. This should only be
     * called while the write lock is hold or in a disaster condition ie. if the engine
     * is failed.
     */
    @Override
    protected final void closeNoLock(String reason) {
        if (isClosed.compareAndSet(false, true)) {
            assert rwl.isWriteLockedByCurrentThread() || failEngineLock.isHeldByCurrentThread() : "Either the write lock must be held or the engine must be currently be failing itself";
            try {
                this.versionMap.clear();
                try {
                    IOUtils.close(searcherManager);
                } catch (Throwable t) {
                    logger.warn("Failed to close SearcherManager", t);
                }
                try {
                    IOUtils.close(translog);
                } catch (Throwable t) {
                    logger.warn("Failed to close translog", t);
                }
                // no need to commit in this case!, we snapshot before we close the shard, so translog and all sync'ed
                logger.trace("rollback indexWriter");
                try {
                    indexWriter.rollback();
                } catch (AlreadyClosedException e) {
                    // ignore
                }
                logger.trace("rollback indexWriter done");
            } catch (Throwable e) {
                logger.warn("failed to rollback writer on close", e);
            } finally {
                store.decRef();
                this.mergeScheduler.removeListener(mergeSchedulerListener);
                this.mergeScheduler.removeFailureListener(mergeSchedulerFailureListener);
                logger.debug("engine closed [{}]", reason);
            }
        }
    }

    @Override
    public boolean hasUncommittedChanges() {
        return indexWriter.hasUncommittedChanges();
    }

    @Override
    protected SearcherManager getSearcherManager() {
        return searcherManager;
    }

    private Object dirtyLock(BytesRef uid) {
        int hash = DjbHashFunction.DJB_HASH(uid.bytes, uid.offset, uid.length);
        return dirtyLocks[MathUtils.mod(hash, dirtyLocks.length)];
    }

    private Object dirtyLock(Term uid) {
        return dirtyLock(uid.bytes());
    }

    private long loadCurrentVersionFromIndex(Term uid) throws IOException {
        try (final Searcher searcher = acquireSearcher("load_version")) {
            return Versions.loadVersion(searcher.reader(), uid);
        }
    }

    private IndexWriter createWriter(boolean create) throws IOException {
        try {
            final IndexWriterConfig iwc = new IndexWriterConfig(engineConfig.getAnalyzer());
            iwc.setCommitOnClose(false); // we by default don't commit on close
            iwc.setOpenMode(create ? IndexWriterConfig.OpenMode.CREATE : IndexWriterConfig.OpenMode.APPEND);
            iwc.setIndexDeletionPolicy(deletionPolicy);
            // with tests.verbose, lucene sets this up: plumb to align with filesystem stream
            boolean verbose = false;
            try {
                verbose = Boolean.parseBoolean(System.getProperty("tests.verbose"));
            } catch (Throwable ignore) {
            }
            iwc.setInfoStream(verbose ? InfoStream.getDefault() : new LoggerInfoStream(logger));
            iwc.setMergeScheduler(mergeScheduler.newMergeScheduler());
            MergePolicy mergePolicy = mergePolicyProvider.getMergePolicy();
            // Give us the opportunity to upgrade old segments while performing
            // background merges
            mergePolicy = new ElasticsearchMergePolicy(mergePolicy);
            iwc.setMergePolicy(mergePolicy);
            iwc.setSimilarity(engineConfig.getSimilarity());
            iwc.setRAMBufferSizeMB(engineConfig.getIndexingBufferSize().mbFrac());
            iwc.setMaxThreadStates(engineConfig.getIndexConcurrency());
            iwc.setCodec(engineConfig.getCodec());
            /* We set this timeout to a highish value to work around
             * the default poll interval in the Lucene lock that is
             * 1000ms by default. We might need to poll multiple times
             * here but with 1s poll this is only executed twice at most
             * in combination with the default writelock timeout*/
            iwc.setWriteLockTimeout(5000);
            iwc.setUseCompoundFile(this.engineConfig.isCompoundOnFlush());
            // Warm-up hook for newly-merged segments. Warming up segments here is better since it will be performed at the end
            // of the merge operation and won't slow down _refresh
            iwc.setMergedSegmentWarmer(new IndexReaderWarmer() {
                @Override
                public void warm(LeafReader reader) throws IOException {
                    try {
                        assert isMergedSegment(reader);
                        if (warmer != null) {
                            final Engine.Searcher searcher = new Searcher("warmer", searcherFactory.newSearcher(reader, null));
                            final IndicesWarmer.WarmerContext context = new IndicesWarmer.WarmerContext(shardId, searcher);
                            warmer.warmNewReaders(context);
                        }
                    } catch (Throwable t) {
                        // Don't fail a merge if the warm-up failed
                        if (isClosed.get() == false) {
                            logger.warn("Warm-up failed", t);
                        }
                        if (t instanceof Error) {
                            // assertion/out-of-memory error, don't ignore those
                            throw (Error) t;
                        }
                    }
                }
            });
            return new IndexWriter(store.directory(), iwc);
        } catch (LockObtainFailedException ex) {
            boolean isLocked = IndexWriter.isLocked(store.directory());
            logger.warn("Could not lock IndexWriter isLocked [{}]", ex, isLocked);
            throw ex;
        }
    }
    /** Extended SearcherFactory that warms the segments if needed when acquiring a new searcher */
    final static class SearchFactory extends EngineSearcherFactory {
        private final IndicesWarmer warmer;
        private final ShardId shardId;
        private final ESLogger logger;
        private final AtomicBoolean isEngineClosed;

        SearchFactory(ESLogger logger, AtomicBoolean isEngineClosed, EngineConfig engineConfig) {
            super(engineConfig);
            warmer = engineConfig.getWarmer();
            shardId = engineConfig.getShardId();
            this.logger = logger;
            this.isEngineClosed = isEngineClosed;
        }

        @Override
        public IndexSearcher newSearcher(IndexReader reader, IndexReader previousReader) throws IOException {
            IndexSearcher searcher = super.newSearcher(reader, previousReader);
            if (warmer != null) {
                // we need to pass a custom searcher that does not release anything on Engine.Search Release,
                // we will release explicitly
                IndexSearcher newSearcher = null;
                boolean closeNewSearcher = false;
                try {
                    if (previousReader == null) {
                        // we are starting up - no writer active so we can't acquire a searcher.
                        newSearcher = searcher;
                    } else {
                        // figure out the newSearcher, with only the new readers that are relevant for us
                        List<IndexReader> readers = Lists.newArrayList();
                        for (LeafReaderContext newReaderContext : reader.leaves()) {
                            if (isMergedSegment(newReaderContext.reader())) {
                                // merged segments are already handled by IndexWriterConfig.setMergedSegmentWarmer
                                continue;
                            }
                            boolean found = false;
                            for (LeafReaderContext currentReaderContext : previousReader.leaves()) {
                                if (currentReaderContext.reader().getCoreCacheKey().equals(newReaderContext.reader().getCoreCacheKey())) {
                                    found = true;
                                    break;
                                }
                            }
                            if (!found) {
                                readers.add(newReaderContext.reader());
                            }
                        }
                        if (!readers.isEmpty()) {
                            // we don't want to close the inner readers, just increase ref on them
                            IndexReader newReader = new MultiReader(readers.toArray(new IndexReader[readers.size()]), false);
                            newSearcher = super.newSearcher(newReader, null);
                            closeNewSearcher = true;
                        }
                    }

                    if (newSearcher != null) {
                        IndicesWarmer.WarmerContext context = new IndicesWarmer.WarmerContext(shardId, new Searcher("warmer", newSearcher));
                        warmer.warmNewReaders(context);
                    }
                    warmer.warmTopReader(new IndicesWarmer.WarmerContext(shardId, new Searcher("warmer", searcher)));
                } catch (Throwable e) {
                    if (isEngineClosed.get() == false) {
                        logger.warn("failed to prepare/warm", e);
                    }
                } finally {
                    // no need to release the fullSearcher, nothing really is done...
                    if (newSearcher != null && closeNewSearcher) {
                        IOUtils.closeWhileHandlingException(newSearcher.getIndexReader()); // ignore
                    }
                }
            }
            return searcher;
        }
    }

    public void activateThrottling() {
        throttle.activate();
    }

    public void deactivateThrottling() {
        throttle.deactivate();
    }

    long getGcDeletesInMillis() {
        return engineConfig.getGcDeletesInMillis();
    }

    LiveIndexWriterConfig getCurrentIndexWriterConfig() {
        return indexWriter.getConfig();
    }


    class FailEngineOnMergeFailure implements MergeSchedulerProvider.FailureListener {
        @Override
        public void onFailedMerge(MergePolicy.MergeException e) {
            if (Lucene.isCorruptionException(e)) {
                failEngine("corrupt file detected source: [merge]", e);
            } else {
                failEngine("merge exception", e);
            }
        }
    }

    class MergeSchedulerListener implements MergeSchedulerProvider.Listener {
        private final AtomicInteger numMergesInFlight = new AtomicInteger(0);
        private final AtomicBoolean isThrottling = new AtomicBoolean();

        @Override
        public synchronized void beforeMerge(OnGoingMerge merge) {
            int maxNumMerges = mergeScheduler.getMaxMerges();
            if (numMergesInFlight.incrementAndGet() > maxNumMerges) {
                if (isThrottling.getAndSet(true) == false) {
                    logger.info("now throttling indexing: numMergesInFlight={}, maxNumMerges={}", numMergesInFlight, maxNumMerges);
                    indexingService.throttlingActivated();
                    activateThrottling();
                }
            }
        }

        @Override
        public synchronized void afterMerge(OnGoingMerge merge) {
            int maxNumMerges = mergeScheduler.getMaxMerges();
            if (numMergesInFlight.decrementAndGet() < maxNumMerges) {
                if (isThrottling.getAndSet(false)) {
                    logger.info("stop throttling indexing: numMergesInFlight={}, maxNumMerges={}", numMergesInFlight, maxNumMerges);
                    indexingService.throttlingDeactivated();
                    deactivateThrottling();
                }
            }
        }
    }

    private void commitIndexWriter(IndexWriter writer, Translog translog, String syncId) throws IOException {
        try {
            Translog.TranslogGeneration translogGeneration = translog.getGeneration();
            logger.trace("committing writer with translog id [{}]  and sync id [{}] ", translogGeneration.translogFileGeneration, syncId);
            Map<String, String> commitData = new HashMap<>(2);
            commitData.put(Translog.TRANSLOG_GENERATION_KEY, Long.toString(translogGeneration.translogFileGeneration));
            commitData.put(Translog.TRANSLOG_UUID_KEY, translogGeneration.translogUUID);
            if (syncId != null) {
                commitData.put(Engine.SYNC_COMMIT_ID, syncId);
            }
            indexWriter.setCommitData(commitData);
            writer.commit();
        } catch (Throwable ex) {
            failEngine("lucene commit failed", ex);
            throw ex;
        }
    }

    private void commitIndexWriter(IndexWriter writer, Translog translog) throws IOException {
        commitIndexWriter(writer, translog, null);
    }

}


File: core/src/main/java/org/elasticsearch/index/merge/policy/AbstractMergePolicyProvider.java
/*
 * Licensed to Elasticsearch under one or more contributor
 * license agreements. See the NOTICE file distributed with
 * this work for additional information regarding copyright
 * ownership. Elasticsearch licenses this file to you under
 * the Apache License, Version 2.0 (the "License"); you may
 * not use this file except in compliance with the License.
 * You may obtain a copy of the License at
 *
 *    http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing,
 * software distributed under the License is distributed on an
 * "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY
 * KIND, either express or implied.  See the License for the
 * specific language governing permissions and limitations
 * under the License.
 */
package org.elasticsearch.index.merge.policy;

import org.apache.lucene.index.MergePolicy;
import org.apache.lucene.index.TieredMergePolicy;
import org.elasticsearch.index.shard.AbstractIndexShardComponent;
import org.elasticsearch.index.store.Store;

public abstract class AbstractMergePolicyProvider<MP extends MergePolicy> extends AbstractIndexShardComponent implements MergePolicyProvider<MP> {
    
    public static final String INDEX_COMPOUND_FORMAT = "index.compound_format";

    protected volatile double noCFSRatio;

    protected AbstractMergePolicyProvider(Store store) {
        super(store.shardId(), store.indexSettings());
        // Default to Lucene's default:
        this.noCFSRatio = parseNoCFSRatio(indexSettings.get(INDEX_COMPOUND_FORMAT, Double.toString(TieredMergePolicy.DEFAULT_NO_CFS_RATIO)));
    }

    public static double parseNoCFSRatio(String noCFSRatio) {
        noCFSRatio = noCFSRatio.trim();
        if (noCFSRatio.equalsIgnoreCase("true")) {
            return 1.0d;
        } else if (noCFSRatio.equalsIgnoreCase("false")) {
            return 0.0;
        } else {
            try {
                double value = Double.parseDouble(noCFSRatio);
                if (value < 0.0 || value > 1.0) {
                    throw new IllegalArgumentException("NoCFSRatio must be in the interval [0..1] but was: [" + value + "]");
                }
                return value;
            } catch (NumberFormatException ex) {
                throw new IllegalArgumentException("Expected a boolean or a value in the interval [0..1] but was: [" + noCFSRatio + "]", ex);
            }
        }
    }

    public static String formatNoCFSRatio(double ratio) {
        if (ratio == 1.0) {
            return Boolean.TRUE.toString();
        } else if (ratio == 0.0) {
            return Boolean.FALSE.toString();
        } else {
            return Double.toString(ratio);
        }
    }

}


File: core/src/main/java/org/elasticsearch/index/merge/policy/LogByteSizeMergePolicyProvider.java
/*
 * Licensed to Elasticsearch under one or more contributor
 * license agreements. See the NOTICE file distributed with
 * this work for additional information regarding copyright
 * ownership. Elasticsearch licenses this file to you under
 * the Apache License, Version 2.0 (the "License"); you may
 * not use this file except in compliance with the License.
 * You may obtain a copy of the License at
 *
 *    http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing,
 * software distributed under the License is distributed on an
 * "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY
 * KIND, either express or implied.  See the License for the
 * specific language governing permissions and limitations
 * under the License.
 */

package org.elasticsearch.index.merge.policy;

import com.google.common.base.Preconditions;
import org.apache.lucene.index.LogByteSizeMergePolicy;
import org.elasticsearch.common.inject.Inject;
import org.elasticsearch.common.settings.Settings;
import org.elasticsearch.common.unit.ByteSizeUnit;
import org.elasticsearch.common.unit.ByteSizeValue;
import org.elasticsearch.index.settings.IndexSettingsService;
import org.elasticsearch.index.store.Store;

/**
 *
 */
public class LogByteSizeMergePolicyProvider extends AbstractMergePolicyProvider<LogByteSizeMergePolicy> {

    private final IndexSettingsService indexSettingsService;
    private final ApplySettings applySettings = new ApplySettings();
    private final LogByteSizeMergePolicy mergePolicy = new LogByteSizeMergePolicy();

    public static final ByteSizeValue DEFAULT_MIN_MERGE_SIZE = new ByteSizeValue((long) (LogByteSizeMergePolicy.DEFAULT_MIN_MERGE_MB * 1024 * 1024), ByteSizeUnit.BYTES);
    public static final ByteSizeValue DEFAULT_MAX_MERGE_SIZE = new ByteSizeValue((long) LogByteSizeMergePolicy.DEFAULT_MAX_MERGE_MB, ByteSizeUnit.MB);

    @Inject
    public LogByteSizeMergePolicyProvider(Store store, IndexSettingsService indexSettingsService) {
        super(store);
        Preconditions.checkNotNull(store, "Store must be provided to merge policy");
        this.indexSettingsService = indexSettingsService;

        ByteSizeValue minMergeSize = indexSettings.getAsBytesSize("index.merge.policy.min_merge_size", DEFAULT_MIN_MERGE_SIZE);
        ByteSizeValue maxMergeSize = indexSettings.getAsBytesSize("index.merge.policy.max_merge_size", DEFAULT_MAX_MERGE_SIZE);
        int mergeFactor = indexSettings.getAsInt("index.merge.policy.merge_factor", LogByteSizeMergePolicy.DEFAULT_MERGE_FACTOR);
        int maxMergeDocs = indexSettings.getAsInt("index.merge.policy.max_merge_docs", LogByteSizeMergePolicy.DEFAULT_MAX_MERGE_DOCS);
        boolean calibrateSizeByDeletes = indexSettings.getAsBoolean("index.merge.policy.calibrate_size_by_deletes", true);

        mergePolicy.setMinMergeMB(minMergeSize.mbFrac());
        mergePolicy.setMaxMergeMB(maxMergeSize.mbFrac());
        mergePolicy.setMergeFactor(mergeFactor);
        mergePolicy.setMaxMergeDocs(maxMergeDocs);
        mergePolicy.setCalibrateSizeByDeletes(calibrateSizeByDeletes);
        mergePolicy.setNoCFSRatio(noCFSRatio);
        logger.debug("using [log_bytes_size] merge policy with merge_factor[{}], min_merge_size[{}], max_merge_size[{}], max_merge_docs[{}], calibrate_size_by_deletes[{}]",
                mergeFactor, minMergeSize, maxMergeSize, maxMergeDocs, calibrateSizeByDeletes);

        indexSettingsService.addListener(applySettings);
    }

    @Override
    public LogByteSizeMergePolicy getMergePolicy() {
        return mergePolicy;
    }

    @Override
    public void close() {
        indexSettingsService.removeListener(applySettings);
    }

    public static final String INDEX_MERGE_POLICY_MIN_MERGE_SIZE = "index.merge.policy.min_merge_size";
    public static final String INDEX_MERGE_POLICY_MAX_MERGE_SIZE = "index.merge.policy.max_merge_size";
    public static final String INDEX_MERGE_POLICY_MAX_MERGE_DOCS = "index.merge.policy.max_merge_docs";
    public static final String INDEX_MERGE_POLICY_MERGE_FACTOR = "index.merge.policy.merge_factor";
    public static final String INDEX_MERGE_POLICY_CALIBRATE_SIZE_BY_DELETES = "index.merge.policy.calibrate_size_by_deletes";

    class ApplySettings implements IndexSettingsService.Listener {
        @Override
        public void onRefreshSettings(Settings settings) {
            double oldMinMergeSizeMB = mergePolicy.getMinMergeMB();
            ByteSizeValue minMergeSize = settings.getAsBytesSize(INDEX_MERGE_POLICY_MIN_MERGE_SIZE, null);
            if (minMergeSize != null && minMergeSize.mbFrac() != oldMinMergeSizeMB) {
                logger.info("updating min_merge_size from [{}mb] to [{}]", oldMinMergeSizeMB, minMergeSize);
                mergePolicy.setMinMergeMB(minMergeSize.mbFrac());
            }

            double oldMaxMergeSizeMB = mergePolicy.getMaxMergeMB();
            ByteSizeValue maxMergeSize = settings.getAsBytesSize(INDEX_MERGE_POLICY_MAX_MERGE_SIZE, null);
            if (maxMergeSize != null && maxMergeSize.mbFrac() != oldMaxMergeSizeMB) {
                logger.info("updating max_merge_size from [{}mb] to [{}]", oldMaxMergeSizeMB, maxMergeSize);
                mergePolicy.setMaxMergeMB(maxMergeSize.mbFrac());
            }

            int oldMaxMergeDocs = mergePolicy.getMaxMergeDocs();
            int maxMergeDocs = settings.getAsInt(INDEX_MERGE_POLICY_MAX_MERGE_DOCS, oldMaxMergeDocs);
            if (maxMergeDocs != oldMaxMergeDocs) {
                logger.info("updating max_merge_docs from [{}] to [{}]", oldMaxMergeDocs, maxMergeDocs);
                mergePolicy.setMaxMergeDocs(maxMergeDocs);
            }

            int oldMergeFactor = mergePolicy.getMergeFactor();
            int mergeFactor = settings.getAsInt(INDEX_MERGE_POLICY_MERGE_FACTOR, oldMergeFactor);
            if (mergeFactor != oldMergeFactor) {
                logger.info("updating merge_factor from [{}] to [{}]", oldMergeFactor, mergeFactor);
                mergePolicy.setMergeFactor(mergeFactor);
            }

            boolean oldCalibrateSizeByDeletes = mergePolicy.getCalibrateSizeByDeletes();
            boolean calibrateSizeByDeletes = settings.getAsBoolean(INDEX_MERGE_POLICY_CALIBRATE_SIZE_BY_DELETES, oldCalibrateSizeByDeletes);
            if (calibrateSizeByDeletes != oldCalibrateSizeByDeletes) {
                logger.info("updating calibrate_size_by_deletes from [{}] to [{}]", oldCalibrateSizeByDeletes, calibrateSizeByDeletes);
                mergePolicy.setCalibrateSizeByDeletes(calibrateSizeByDeletes);
            }
            
            final double noCFSRatio = parseNoCFSRatio(settings.get(INDEX_COMPOUND_FORMAT, Double.toString(LogByteSizeMergePolicyProvider.this.noCFSRatio)));
            if (noCFSRatio != LogByteSizeMergePolicyProvider.this.noCFSRatio) {
                logger.info("updating index.compound_format from [{}] to [{}]", formatNoCFSRatio(LogByteSizeMergePolicyProvider.this.noCFSRatio), formatNoCFSRatio(noCFSRatio));
                LogByteSizeMergePolicyProvider.this.noCFSRatio = noCFSRatio;
                mergePolicy.setNoCFSRatio(noCFSRatio);
            }
        }
    }
}


File: core/src/main/java/org/elasticsearch/index/merge/policy/LogDocMergePolicyProvider.java
/*
 * Licensed to Elasticsearch under one or more contributor
 * license agreements. See the NOTICE file distributed with
 * this work for additional information regarding copyright
 * ownership. Elasticsearch licenses this file to you under
 * the Apache License, Version 2.0 (the "License"); you may
 * not use this file except in compliance with the License.
 * You may obtain a copy of the License at
 *
 *    http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing,
 * software distributed under the License is distributed on an
 * "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY
 * KIND, either express or implied.  See the License for the
 * specific language governing permissions and limitations
 * under the License.
 */

package org.elasticsearch.index.merge.policy;

import com.google.common.base.Preconditions;
import org.apache.lucene.index.LogDocMergePolicy;
import org.elasticsearch.common.inject.Inject;
import org.elasticsearch.common.settings.Settings;
import org.elasticsearch.index.settings.IndexSettingsService;
import org.elasticsearch.index.store.Store;

/**
 *
 */
public class LogDocMergePolicyProvider extends AbstractMergePolicyProvider<LogDocMergePolicy> {

    private final IndexSettingsService indexSettingsService;
    private final ApplySettings applySettings = new ApplySettings();
    private final LogDocMergePolicy mergePolicy = new LogDocMergePolicy();


    public static final String MAX_MERGE_DOCS_KEY = "index.merge.policy.max_merge_docs";
    public static final String MIN_MERGE_DOCS_KEY = "index.merge.policy.min_merge_docs";
    public static final String MERGE_FACTORY_KEY = "index.merge.policy.merge_factor";

    @Inject
    public LogDocMergePolicyProvider(Store store, IndexSettingsService indexSettingsService) {
        super(store);
        Preconditions.checkNotNull(store, "Store must be provided to merge policy");
        this.indexSettingsService = indexSettingsService;

        int minMergeDocs = indexSettings.getAsInt(MIN_MERGE_DOCS_KEY, LogDocMergePolicy.DEFAULT_MIN_MERGE_DOCS);
        int maxMergeDocs = indexSettings.getAsInt(MAX_MERGE_DOCS_KEY, LogDocMergePolicy.DEFAULT_MAX_MERGE_DOCS);
        int mergeFactor = indexSettings.getAsInt(MERGE_FACTORY_KEY, LogDocMergePolicy.DEFAULT_MERGE_FACTOR);
        boolean calibrateSizeByDeletes = indexSettings.getAsBoolean("index.merge.policy.calibrate_size_by_deletes", true);

        mergePolicy.setMinMergeDocs(minMergeDocs);
        mergePolicy.setMaxMergeDocs(maxMergeDocs);
        mergePolicy.setMergeFactor(mergeFactor);
        mergePolicy.setCalibrateSizeByDeletes(calibrateSizeByDeletes);
        mergePolicy.setNoCFSRatio(noCFSRatio);
        logger.debug("using [log_doc] merge policy with merge_factor[{}], min_merge_docs[{}], max_merge_docs[{}], calibrate_size_by_deletes[{}]",
                mergeFactor, minMergeDocs, maxMergeDocs, calibrateSizeByDeletes);

        indexSettingsService.addListener(applySettings);
    }

    @Override
    public void close() {
        indexSettingsService.removeListener(applySettings);
    }

    @Override
    public LogDocMergePolicy getMergePolicy() {
        return mergePolicy;
    }

    public static final String INDEX_MERGE_POLICY_MIN_MERGE_DOCS = "index.merge.policy.min_merge_docs";
    public static final String INDEX_MERGE_POLICY_MAX_MERGE_DOCS = "index.merge.policy.max_merge_docs";
    public static final String INDEX_MERGE_POLICY_MERGE_FACTOR = "index.merge.policy.merge_factor";
    public static final String INDEX_MERGE_POLICY_CALIBRATE_SIZE_BY_DELETES = "index.merge.policy.calibrate_size_by_deletes";

    class ApplySettings implements IndexSettingsService.Listener {
        @Override
        public void onRefreshSettings(Settings settings) {
            int oldMinMergeDocs = mergePolicy.getMinMergeDocs();
            int minMergeDocs = settings.getAsInt(INDEX_MERGE_POLICY_MIN_MERGE_DOCS, oldMinMergeDocs);
            if (minMergeDocs != oldMinMergeDocs) {
                logger.info("updating min_merge_docs from [{}] to [{}]", oldMinMergeDocs, minMergeDocs);
                mergePolicy.setMinMergeDocs(minMergeDocs);
            }

            int oldMaxMergeDocs = mergePolicy.getMaxMergeDocs();
            int maxMergeDocs = settings.getAsInt(INDEX_MERGE_POLICY_MAX_MERGE_DOCS, oldMaxMergeDocs);
            if (maxMergeDocs != oldMaxMergeDocs) {
                logger.info("updating max_merge_docs from [{}] to [{}]", oldMaxMergeDocs, maxMergeDocs);
                mergePolicy.setMaxMergeDocs(maxMergeDocs);
            }

            int oldMergeFactor = mergePolicy.getMergeFactor();
            int mergeFactor = settings.getAsInt(INDEX_MERGE_POLICY_MERGE_FACTOR, oldMergeFactor);
            if (mergeFactor != oldMergeFactor) {
                logger.info("updating merge_factor from [{}] to [{}]", oldMergeFactor, mergeFactor);
                mergePolicy.setMergeFactor(mergeFactor);
            }

            boolean oldCalibrateSizeByDeletes = mergePolicy.getCalibrateSizeByDeletes();
            boolean calibrateSizeByDeletes = settings.getAsBoolean(INDEX_MERGE_POLICY_CALIBRATE_SIZE_BY_DELETES, oldCalibrateSizeByDeletes);
            if (calibrateSizeByDeletes != oldCalibrateSizeByDeletes) {
                logger.info("updating calibrate_size_by_deletes from [{}] to [{}]", oldCalibrateSizeByDeletes, calibrateSizeByDeletes);
                mergePolicy.setCalibrateSizeByDeletes(calibrateSizeByDeletes);
            }

            double noCFSRatio = parseNoCFSRatio(settings.get(INDEX_COMPOUND_FORMAT, Double.toString(LogDocMergePolicyProvider.this.noCFSRatio)));
            if (noCFSRatio != LogDocMergePolicyProvider.this.noCFSRatio) {
                logger.info("updating index.compound_format from [{}] to [{}]", formatNoCFSRatio(LogDocMergePolicyProvider.this.noCFSRatio), formatNoCFSRatio(noCFSRatio));
                LogDocMergePolicyProvider.this.noCFSRatio = noCFSRatio;
                mergePolicy.setNoCFSRatio(noCFSRatio);
            }
        }
    }
}


File: core/src/main/java/org/elasticsearch/index/merge/policy/MergePolicyModule.java
/*
 * Licensed to Elasticsearch under one or more contributor
 * license agreements. See the NOTICE file distributed with
 * this work for additional information regarding copyright
 * ownership. Elasticsearch licenses this file to you under
 * the Apache License, Version 2.0 (the "License"); you may
 * not use this file except in compliance with the License.
 * You may obtain a copy of the License at
 *
 *    http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing,
 * software distributed under the License is distributed on an
 * "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY
 * KIND, either express or implied.  See the License for the
 * specific language governing permissions and limitations
 * under the License.
 */

package org.elasticsearch.index.merge.policy;

import org.elasticsearch.common.inject.AbstractModule;
import org.elasticsearch.common.settings.Settings;

/**
 *
 */
public class MergePolicyModule extends AbstractModule {

    private final Settings settings;
    public static final String MERGE_POLICY_TYPE_KEY = "index.merge.policy.type";

    public MergePolicyModule(Settings settings) {
        this.settings = settings;
    }

    @Override
    protected void configure() {
        bind(MergePolicyProvider.class)
                .to(settings.getAsClass("index.merge.policy.type", TieredMergePolicyProvider.class, "org.elasticsearch.index.merge.policy.", "MergePolicyProvider"))
                .asEagerSingleton();
    }
}


File: core/src/main/java/org/elasticsearch/index/merge/policy/MergePolicyProvider.java
/*
 * Licensed to Elasticsearch under one or more contributor
 * license agreements. See the NOTICE file distributed with
 * this work for additional information regarding copyright
 * ownership. Elasticsearch licenses this file to you under
 * the Apache License, Version 2.0 (the "License"); you may
 * not use this file except in compliance with the License.
 * You may obtain a copy of the License at
 *
 *    http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing,
 * software distributed under the License is distributed on an
 * "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY
 * KIND, either express or implied.  See the License for the
 * specific language governing permissions and limitations
 * under the License.
 */

package org.elasticsearch.index.merge.policy;

import org.apache.lucene.index.MergePolicy;
import org.elasticsearch.index.shard.IndexShardComponent;

import java.io.Closeable;

/**
 *
 */
public interface MergePolicyProvider<T extends MergePolicy> extends IndexShardComponent, Closeable {

    T getMergePolicy();
}


File: core/src/main/java/org/elasticsearch/index/merge/policy/TieredMergePolicyProvider.java
/*
 * Licensed to Elasticsearch under one or more contributor
 * license agreements. See the NOTICE file distributed with
 * this work for additional information regarding copyright
 * ownership. Elasticsearch licenses this file to you under
 * the Apache License, Version 2.0 (the "License"); you may
 * not use this file except in compliance with the License.
 * You may obtain a copy of the License at
 *
 *    http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing,
 * software distributed under the License is distributed on an
 * "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY
 * KIND, either express or implied.  See the License for the
 * specific language governing permissions and limitations
 * under the License.
 */

package org.elasticsearch.index.merge.policy;

import org.apache.lucene.index.TieredMergePolicy;
import org.elasticsearch.common.inject.Inject;
import org.elasticsearch.common.settings.Settings;
import org.elasticsearch.common.unit.ByteSizeUnit;
import org.elasticsearch.common.unit.ByteSizeValue;
import org.elasticsearch.index.settings.IndexSettingsService;
import org.elasticsearch.index.store.Store;

public class TieredMergePolicyProvider extends AbstractMergePolicyProvider<TieredMergePolicy> {

    private final IndexSettingsService indexSettingsService;
    private final ApplySettings applySettings = new ApplySettings();
    private final TieredMergePolicy mergePolicy = new TieredMergePolicy();

    public static final double          DEFAULT_EXPUNGE_DELETES_ALLOWED     = 10d;
    public static final ByteSizeValue   DEFAULT_FLOOR_SEGMENT               = new ByteSizeValue(2, ByteSizeUnit.MB);
    public static final int             DEFAULT_MAX_MERGE_AT_ONCE           = 10;
    public static final int             DEFAULT_MAX_MERGE_AT_ONCE_EXPLICIT  = 30;
    public static final ByteSizeValue   DEFAULT_MAX_MERGED_SEGMENT          = new ByteSizeValue(5, ByteSizeUnit.GB);
    public static final double          DEFAULT_SEGMENTS_PER_TIER           = 10.0d;
    public static final double          DEFAULT_RECLAIM_DELETES_WEIGHT      = 2.0d;

    @Inject
    public TieredMergePolicyProvider(Store store, IndexSettingsService indexSettingsService) {
        super(store);
        this.indexSettingsService = indexSettingsService;

        double forceMergeDeletesPctAllowed = indexSettings.getAsDouble("index.merge.policy.expunge_deletes_allowed", DEFAULT_EXPUNGE_DELETES_ALLOWED); // percentage
        ByteSizeValue floorSegment = indexSettings.getAsBytesSize("index.merge.policy.floor_segment", DEFAULT_FLOOR_SEGMENT);
        int maxMergeAtOnce = indexSettings.getAsInt("index.merge.policy.max_merge_at_once", DEFAULT_MAX_MERGE_AT_ONCE);
        int maxMergeAtOnceExplicit = indexSettings.getAsInt("index.merge.policy.max_merge_at_once_explicit", DEFAULT_MAX_MERGE_AT_ONCE_EXPLICIT);
        // TODO is this really a good default number for max_merge_segment, what happens for large indices, won't they end up with many segments?
        ByteSizeValue maxMergedSegment = indexSettings.getAsBytesSize("index.merge.policy.max_merged_segment", DEFAULT_MAX_MERGED_SEGMENT);
        double segmentsPerTier = indexSettings.getAsDouble("index.merge.policy.segments_per_tier", DEFAULT_SEGMENTS_PER_TIER);
        double reclaimDeletesWeight = indexSettings.getAsDouble("index.merge.policy.reclaim_deletes_weight", DEFAULT_RECLAIM_DELETES_WEIGHT);

        maxMergeAtOnce = adjustMaxMergeAtOnceIfNeeded(maxMergeAtOnce, segmentsPerTier);
        mergePolicy.setNoCFSRatio(noCFSRatio);
        mergePolicy.setForceMergeDeletesPctAllowed(forceMergeDeletesPctAllowed);
        mergePolicy.setFloorSegmentMB(floorSegment.mbFrac());
        mergePolicy.setMaxMergeAtOnce(maxMergeAtOnce);
        mergePolicy.setMaxMergeAtOnceExplicit(maxMergeAtOnceExplicit);
        mergePolicy.setMaxMergedSegmentMB(maxMergedSegment.mbFrac());
        mergePolicy.setSegmentsPerTier(segmentsPerTier);
        mergePolicy.setReclaimDeletesWeight(reclaimDeletesWeight);
        logger.debug("using [tiered] merge mergePolicy with expunge_deletes_allowed[{}], floor_segment[{}], max_merge_at_once[{}], max_merge_at_once_explicit[{}], max_merged_segment[{}], segments_per_tier[{}], reclaim_deletes_weight[{}]",
                forceMergeDeletesPctAllowed, floorSegment, maxMergeAtOnce, maxMergeAtOnceExplicit, maxMergedSegment, segmentsPerTier, reclaimDeletesWeight);

        indexSettingsService.addListener(applySettings);
    }

    private int adjustMaxMergeAtOnceIfNeeded(int maxMergeAtOnce, double segmentsPerTier) {
        // fixing maxMergeAtOnce, see TieredMergePolicy#setMaxMergeAtOnce
        if (!(segmentsPerTier >= maxMergeAtOnce)) {
            int newMaxMergeAtOnce = (int) segmentsPerTier;
            // max merge at once should be at least 2
            if (newMaxMergeAtOnce <= 1) {
                newMaxMergeAtOnce = 2;
            }
            logger.debug("[tiered] merge mergePolicy changing max_merge_at_once from [{}] to [{}] because segments_per_tier [{}] has to be higher or equal to it", maxMergeAtOnce, newMaxMergeAtOnce, segmentsPerTier);
            maxMergeAtOnce = newMaxMergeAtOnce;
        }
        return maxMergeAtOnce;
    }

    @Override
    public TieredMergePolicy getMergePolicy() {
        return mergePolicy;
    }

    @Override
    public void close() {
        indexSettingsService.removeListener(applySettings);
    }

    public static final String INDEX_MERGE_POLICY_EXPUNGE_DELETES_ALLOWED = "index.merge.policy.expunge_deletes_allowed";
    public static final String INDEX_MERGE_POLICY_FLOOR_SEGMENT = "index.merge.policy.floor_segment";
    public static final String INDEX_MERGE_POLICY_MAX_MERGE_AT_ONCE = "index.merge.policy.max_merge_at_once";
    public static final String INDEX_MERGE_POLICY_MAX_MERGE_AT_ONCE_EXPLICIT = "index.merge.policy.max_merge_at_once_explicit";
    public static final String INDEX_MERGE_POLICY_MAX_MERGED_SEGMENT = "index.merge.policy.max_merged_segment";
    public static final String INDEX_MERGE_POLICY_SEGMENTS_PER_TIER = "index.merge.policy.segments_per_tier";
    public static final String INDEX_MERGE_POLICY_RECLAIM_DELETES_WEIGHT = "index.merge.policy.reclaim_deletes_weight";

    class ApplySettings implements IndexSettingsService.Listener {
        @Override
        public void onRefreshSettings(Settings settings) {
            final double oldExpungeDeletesPctAllowed = mergePolicy.getForceMergeDeletesPctAllowed();
            final double expungeDeletesPctAllowed = settings.getAsDouble(INDEX_MERGE_POLICY_EXPUNGE_DELETES_ALLOWED, oldExpungeDeletesPctAllowed);
            if (expungeDeletesPctAllowed != oldExpungeDeletesPctAllowed) {
                logger.info("updating [expunge_deletes_allowed] from [{}] to [{}]", oldExpungeDeletesPctAllowed, expungeDeletesPctAllowed);
                mergePolicy.setForceMergeDeletesPctAllowed(expungeDeletesPctAllowed);
            }

            final double oldFloorSegmentMB = mergePolicy.getFloorSegmentMB();
            final ByteSizeValue floorSegment = settings.getAsBytesSize(INDEX_MERGE_POLICY_FLOOR_SEGMENT, null);
            if (floorSegment != null && floorSegment.mbFrac() != oldFloorSegmentMB) {
                logger.info("updating [floor_segment] from [{}mb] to [{}]", oldFloorSegmentMB, floorSegment);
                mergePolicy.setFloorSegmentMB(floorSegment.mbFrac());
            }

            final double oldSegmentsPerTier = mergePolicy.getSegmentsPerTier();
            final double segmentsPerTier = settings.getAsDouble(INDEX_MERGE_POLICY_SEGMENTS_PER_TIER, oldSegmentsPerTier);
            if (segmentsPerTier != oldSegmentsPerTier) {
                logger.info("updating [segments_per_tier] from [{}] to [{}]", oldSegmentsPerTier, segmentsPerTier);
                mergePolicy.setSegmentsPerTier(segmentsPerTier);
            }

            final int oldMaxMergeAtOnce = mergePolicy.getMaxMergeAtOnce();
            int maxMergeAtOnce = settings.getAsInt(INDEX_MERGE_POLICY_MAX_MERGE_AT_ONCE, oldMaxMergeAtOnce);
            if (maxMergeAtOnce != oldMaxMergeAtOnce) {
                logger.info("updating [max_merge_at_once] from [{}] to [{}]", oldMaxMergeAtOnce, maxMergeAtOnce);
                maxMergeAtOnce = adjustMaxMergeAtOnceIfNeeded(maxMergeAtOnce, segmentsPerTier);
                mergePolicy.setMaxMergeAtOnce(maxMergeAtOnce);
            }

            final int oldMaxMergeAtOnceExplicit = mergePolicy.getMaxMergeAtOnceExplicit();
            final int maxMergeAtOnceExplicit = settings.getAsInt(INDEX_MERGE_POLICY_MAX_MERGE_AT_ONCE_EXPLICIT, oldMaxMergeAtOnceExplicit);
            if (maxMergeAtOnceExplicit != oldMaxMergeAtOnceExplicit) {
                logger.info("updating [max_merge_at_once_explicit] from [{}] to [{}]", oldMaxMergeAtOnceExplicit, maxMergeAtOnceExplicit);
                mergePolicy.setMaxMergeAtOnceExplicit(maxMergeAtOnceExplicit);
            }

            final double oldMaxMergedSegmentMB = mergePolicy.getMaxMergedSegmentMB();
            final ByteSizeValue maxMergedSegment = settings.getAsBytesSize(INDEX_MERGE_POLICY_MAX_MERGED_SEGMENT, null);
            if (maxMergedSegment != null && maxMergedSegment.mbFrac() != oldMaxMergedSegmentMB) {
                logger.info("updating [max_merged_segment] from [{}mb] to [{}]", oldMaxMergedSegmentMB, maxMergedSegment);
                mergePolicy.setMaxMergedSegmentMB(maxMergedSegment.mbFrac());
            }

            final double oldReclaimDeletesWeight = mergePolicy.getReclaimDeletesWeight();
            final double reclaimDeletesWeight = settings.getAsDouble(INDEX_MERGE_POLICY_RECLAIM_DELETES_WEIGHT, oldReclaimDeletesWeight);
            if (reclaimDeletesWeight != oldReclaimDeletesWeight) {
                logger.info("updating [reclaim_deletes_weight] from [{}] to [{}]", oldReclaimDeletesWeight, reclaimDeletesWeight);
                mergePolicy.setReclaimDeletesWeight(reclaimDeletesWeight);
            }

            double noCFSRatio = parseNoCFSRatio(settings.get(INDEX_COMPOUND_FORMAT, Double.toString(TieredMergePolicyProvider.this.noCFSRatio)));
            if (noCFSRatio != TieredMergePolicyProvider.this.noCFSRatio) {
                logger.info("updating index.compound_format from [{}] to [{}]", formatNoCFSRatio(TieredMergePolicyProvider.this.noCFSRatio), formatNoCFSRatio(noCFSRatio));
                mergePolicy.setNoCFSRatio(noCFSRatio);
                TieredMergePolicyProvider.this.noCFSRatio = noCFSRatio;
            }
        }
    }
}

File: core/src/main/java/org/elasticsearch/index/settings/IndexDynamicSettingsModule.java
/*
 * Licensed to Elasticsearch under one or more contributor
 * license agreements. See the NOTICE file distributed with
 * this work for additional information regarding copyright
 * ownership. Elasticsearch licenses this file to you under
 * the Apache License, Version 2.0 (the "License"); you may
 * not use this file except in compliance with the License.
 * You may obtain a copy of the License at
 *
 *    http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing,
 * software distributed under the License is distributed on an
 * "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY
 * KIND, either express or implied.  See the License for the
 * specific language governing permissions and limitations
 * under the License.
 */

package org.elasticsearch.index.settings;

import org.elasticsearch.cluster.metadata.IndexMetaData;
import org.elasticsearch.cluster.routing.allocation.decider.DisableAllocationDecider;
import org.elasticsearch.cluster.routing.allocation.decider.EnableAllocationDecider;
import org.elasticsearch.cluster.routing.allocation.decider.FilterAllocationDecider;
import org.elasticsearch.cluster.routing.allocation.decider.ShardsLimitAllocationDecider;
import org.elasticsearch.cluster.settings.DynamicSettings;
import org.elasticsearch.cluster.settings.Validator;
import org.elasticsearch.common.inject.AbstractModule;
import org.elasticsearch.gateway.GatewayAllocator;
import org.elasticsearch.index.engine.EngineConfig;
import org.elasticsearch.index.indexing.slowlog.ShardSlowLogIndexingService;
import org.elasticsearch.index.merge.policy.LogByteSizeMergePolicyProvider;
import org.elasticsearch.index.merge.policy.LogDocMergePolicyProvider;
import org.elasticsearch.index.merge.policy.TieredMergePolicyProvider;
import org.elasticsearch.index.merge.scheduler.ConcurrentMergeSchedulerProvider;
import org.elasticsearch.index.search.slowlog.ShardSlowLogSearchService;
import org.elasticsearch.index.shard.IndexShard;
import org.elasticsearch.index.store.IndexStore;
import org.elasticsearch.index.translog.TranslogConfig;
import org.elasticsearch.index.translog.TranslogService;
import org.elasticsearch.index.translog.Translog;
import org.elasticsearch.indices.IndicesWarmer;
import org.elasticsearch.indices.cache.query.IndicesQueryCache;
import org.elasticsearch.indices.ttl.IndicesTTLService;

/**
 */
public class IndexDynamicSettingsModule extends AbstractModule {

    private final DynamicSettings indexDynamicSettings;

    public IndexDynamicSettingsModule() {
        indexDynamicSettings = new DynamicSettings();
        indexDynamicSettings.addDynamicSetting(IndexStore.INDEX_STORE_THROTTLE_MAX_BYTES_PER_SEC, Validator.BYTES_SIZE);
        indexDynamicSettings.addDynamicSetting(IndexStore.INDEX_STORE_THROTTLE_TYPE);
        indexDynamicSettings.addDynamicSetting(ConcurrentMergeSchedulerProvider.MAX_THREAD_COUNT);
        indexDynamicSettings.addDynamicSetting(ConcurrentMergeSchedulerProvider.MAX_MERGE_COUNT);
        indexDynamicSettings.addDynamicSetting(ConcurrentMergeSchedulerProvider.AUTO_THROTTLE);
        indexDynamicSettings.addDynamicSetting(FilterAllocationDecider.INDEX_ROUTING_REQUIRE_GROUP + "*");
        indexDynamicSettings.addDynamicSetting(FilterAllocationDecider.INDEX_ROUTING_INCLUDE_GROUP + "*");
        indexDynamicSettings.addDynamicSetting(FilterAllocationDecider.INDEX_ROUTING_EXCLUDE_GROUP + "*");
        indexDynamicSettings.addDynamicSetting(EnableAllocationDecider.INDEX_ROUTING_ALLOCATION_ENABLE);
        indexDynamicSettings.addDynamicSetting(EnableAllocationDecider.INDEX_ROUTING_REBALANCE_ENABLE);
        indexDynamicSettings.addDynamicSetting(DisableAllocationDecider.INDEX_ROUTING_ALLOCATION_DISABLE_ALLOCATION);
        indexDynamicSettings.addDynamicSetting(DisableAllocationDecider.INDEX_ROUTING_ALLOCATION_DISABLE_NEW_ALLOCATION);
        indexDynamicSettings.addDynamicSetting(DisableAllocationDecider.INDEX_ROUTING_ALLOCATION_DISABLE_REPLICA_ALLOCATION);
        indexDynamicSettings.addDynamicSetting(TranslogConfig.INDEX_TRANSLOG_FS_TYPE);
        indexDynamicSettings.addDynamicSetting(IndexMetaData.SETTING_NUMBER_OF_REPLICAS, Validator.NON_NEGATIVE_INTEGER);
        indexDynamicSettings.addDynamicSetting(IndexMetaData.SETTING_AUTO_EXPAND_REPLICAS);
        indexDynamicSettings.addDynamicSetting(IndexMetaData.SETTING_READ_ONLY);
        indexDynamicSettings.addDynamicSetting(IndexMetaData.SETTING_BLOCKS_READ);
        indexDynamicSettings.addDynamicSetting(IndexMetaData.SETTING_BLOCKS_WRITE);
        indexDynamicSettings.addDynamicSetting(IndexMetaData.SETTING_BLOCKS_METADATA);
        indexDynamicSettings.addDynamicSetting(IndexMetaData.SETTING_SHARED_FS_ALLOW_RECOVERY_ON_ANY_NODE);
        indexDynamicSettings.addDynamicSetting(IndicesTTLService.INDEX_TTL_DISABLE_PURGE);
        indexDynamicSettings.addDynamicSetting(IndexShard.INDEX_REFRESH_INTERVAL, Validator.TIME);
        indexDynamicSettings.addDynamicSetting(GatewayAllocator.INDEX_RECOVERY_INITIAL_SHARDS);
        indexDynamicSettings.addDynamicSetting(LogByteSizeMergePolicyProvider.INDEX_MERGE_POLICY_MIN_MERGE_SIZE, Validator.BYTES_SIZE);
        indexDynamicSettings.addDynamicSetting(LogByteSizeMergePolicyProvider.INDEX_MERGE_POLICY_MAX_MERGE_SIZE, Validator.BYTES_SIZE);
        indexDynamicSettings.addDynamicSetting(LogByteSizeMergePolicyProvider.INDEX_MERGE_POLICY_MAX_MERGE_DOCS, Validator.POSITIVE_INTEGER);
        indexDynamicSettings.addDynamicSetting(LogByteSizeMergePolicyProvider.INDEX_MERGE_POLICY_MERGE_FACTOR, Validator.INTEGER_GTE_2);
        indexDynamicSettings.addDynamicSetting(LogByteSizeMergePolicyProvider.INDEX_COMPOUND_FORMAT);
        indexDynamicSettings.addDynamicSetting(LogDocMergePolicyProvider.INDEX_MERGE_POLICY_MIN_MERGE_DOCS, Validator.POSITIVE_INTEGER);
        indexDynamicSettings.addDynamicSetting(LogDocMergePolicyProvider.INDEX_MERGE_POLICY_MAX_MERGE_DOCS, Validator.POSITIVE_INTEGER);
        indexDynamicSettings.addDynamicSetting(LogDocMergePolicyProvider.INDEX_MERGE_POLICY_MERGE_FACTOR, Validator.INTEGER_GTE_2);
        indexDynamicSettings.addDynamicSetting(LogDocMergePolicyProvider.INDEX_COMPOUND_FORMAT);
        indexDynamicSettings.addDynamicSetting(EngineConfig.INDEX_COMPOUND_ON_FLUSH, Validator.BOOLEAN);
        indexDynamicSettings.addDynamicSetting(EngineConfig.INDEX_GC_DELETES_SETTING, Validator.TIME);
        indexDynamicSettings.addDynamicSetting(IndexShard.INDEX_FLUSH_ON_CLOSE, Validator.BOOLEAN);
        indexDynamicSettings.addDynamicSetting(EngineConfig.INDEX_VERSION_MAP_SIZE, Validator.BYTES_SIZE_OR_PERCENTAGE);
        indexDynamicSettings.addDynamicSetting(ShardSlowLogIndexingService.INDEX_INDEXING_SLOWLOG_THRESHOLD_INDEX_WARN, Validator.TIME);
        indexDynamicSettings.addDynamicSetting(ShardSlowLogIndexingService.INDEX_INDEXING_SLOWLOG_THRESHOLD_INDEX_INFO, Validator.TIME);
        indexDynamicSettings.addDynamicSetting(ShardSlowLogIndexingService.INDEX_INDEXING_SLOWLOG_THRESHOLD_INDEX_DEBUG, Validator.TIME);
        indexDynamicSettings.addDynamicSetting(ShardSlowLogIndexingService.INDEX_INDEXING_SLOWLOG_THRESHOLD_INDEX_TRACE, Validator.TIME);
        indexDynamicSettings.addDynamicSetting(ShardSlowLogIndexingService.INDEX_INDEXING_SLOWLOG_REFORMAT);
        indexDynamicSettings.addDynamicSetting(ShardSlowLogIndexingService.INDEX_INDEXING_SLOWLOG_LEVEL);
        indexDynamicSettings.addDynamicSetting(ShardSlowLogSearchService.INDEX_SEARCH_SLOWLOG_THRESHOLD_QUERY_WARN, Validator.TIME);
        indexDynamicSettings.addDynamicSetting(ShardSlowLogSearchService.INDEX_SEARCH_SLOWLOG_THRESHOLD_QUERY_INFO, Validator.TIME);
        indexDynamicSettings.addDynamicSetting(ShardSlowLogSearchService.INDEX_SEARCH_SLOWLOG_THRESHOLD_QUERY_DEBUG, Validator.TIME);
        indexDynamicSettings.addDynamicSetting(ShardSlowLogSearchService.INDEX_SEARCH_SLOWLOG_THRESHOLD_QUERY_TRACE, Validator.TIME);
        indexDynamicSettings.addDynamicSetting(ShardSlowLogSearchService.INDEX_SEARCH_SLOWLOG_THRESHOLD_FETCH_WARN, Validator.TIME);
        indexDynamicSettings.addDynamicSetting(ShardSlowLogSearchService.INDEX_SEARCH_SLOWLOG_THRESHOLD_FETCH_INFO, Validator.TIME);
        indexDynamicSettings.addDynamicSetting(ShardSlowLogSearchService.INDEX_SEARCH_SLOWLOG_THRESHOLD_FETCH_DEBUG, Validator.TIME);
        indexDynamicSettings.addDynamicSetting(ShardSlowLogSearchService.INDEX_SEARCH_SLOWLOG_THRESHOLD_FETCH_TRACE, Validator.TIME);
        indexDynamicSettings.addDynamicSetting(ShardSlowLogSearchService.INDEX_SEARCH_SLOWLOG_REFORMAT);
        indexDynamicSettings.addDynamicSetting(ShardSlowLogSearchService.INDEX_SEARCH_SLOWLOG_LEVEL);
        indexDynamicSettings.addDynamicSetting(ShardsLimitAllocationDecider.INDEX_TOTAL_SHARDS_PER_NODE, Validator.INTEGER);
        indexDynamicSettings.addDynamicSetting(TieredMergePolicyProvider.INDEX_MERGE_POLICY_EXPUNGE_DELETES_ALLOWED, Validator.DOUBLE);
        indexDynamicSettings.addDynamicSetting(TieredMergePolicyProvider.INDEX_MERGE_POLICY_FLOOR_SEGMENT, Validator.BYTES_SIZE);
        indexDynamicSettings.addDynamicSetting(TieredMergePolicyProvider.INDEX_MERGE_POLICY_MAX_MERGE_AT_ONCE, Validator.INTEGER_GTE_2);
        indexDynamicSettings.addDynamicSetting(TieredMergePolicyProvider.INDEX_MERGE_POLICY_MAX_MERGE_AT_ONCE_EXPLICIT, Validator.INTEGER_GTE_2);
        indexDynamicSettings.addDynamicSetting(TieredMergePolicyProvider.INDEX_MERGE_POLICY_MAX_MERGED_SEGMENT, Validator.BYTES_SIZE);
        indexDynamicSettings.addDynamicSetting(TieredMergePolicyProvider.INDEX_MERGE_POLICY_SEGMENTS_PER_TIER, Validator.DOUBLE_GTE_2);
        indexDynamicSettings.addDynamicSetting(TieredMergePolicyProvider.INDEX_MERGE_POLICY_RECLAIM_DELETES_WEIGHT, Validator.NON_NEGATIVE_DOUBLE);
        indexDynamicSettings.addDynamicSetting(TieredMergePolicyProvider.INDEX_COMPOUND_FORMAT);
        indexDynamicSettings.addDynamicSetting(TranslogService.INDEX_TRANSLOG_FLUSH_INTERVAL, Validator.TIME);
        indexDynamicSettings.addDynamicSetting(TranslogService.INDEX_TRANSLOG_FLUSH_THRESHOLD_OPS, Validator.INTEGER);
        indexDynamicSettings.addDynamicSetting(TranslogService.INDEX_TRANSLOG_FLUSH_THRESHOLD_SIZE, Validator.BYTES_SIZE);
        indexDynamicSettings.addDynamicSetting(TranslogService.INDEX_TRANSLOG_FLUSH_THRESHOLD_PERIOD, Validator.TIME);
        indexDynamicSettings.addDynamicSetting(TranslogService.INDEX_TRANSLOG_DISABLE_FLUSH);
        indexDynamicSettings.addDynamicSetting(TranslogConfig.INDEX_TRANSLOG_DURABILITY);
        indexDynamicSettings.addDynamicSetting(IndicesWarmer.INDEX_WARMER_ENABLED);
        indexDynamicSettings.addDynamicSetting(IndicesQueryCache.INDEX_CACHE_QUERY_ENABLED, Validator.BOOLEAN);
    }

    public void addDynamicSettings(String... settings) {
        indexDynamicSettings.addDynamicSettings(settings);
    }

    public void addDynamicSetting(String setting, Validator validator) {
        indexDynamicSettings.addDynamicSetting(setting, validator);
    }

    @Override
    protected void configure() {
        bind(DynamicSettings.class).annotatedWith(IndexDynamicSettings.class).toInstance(indexDynamicSettings);
    }

    /**
     * Returns <code>true</code> iff the given setting is in the dynamic settings map. Otherwise <code>false</code>.
     */
    public boolean containsSetting(String setting) {
        return indexDynamicSettings.hasDynamicSetting(setting);
    }
}


File: core/src/main/java/org/elasticsearch/index/shard/IndexShard.java
/*
 * Licensed to Elasticsearch under one or more contributor
 * license agreements. See the NOTICE file distributed with
 * this work for additional information regarding copyright
 * ownership. Elasticsearch licenses this file to you under
 * the Apache License, Version 2.0 (the "License"); you may
 * not use this file except in compliance with the License.
 * You may obtain a copy of the License at
 *
 *    http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing,
 * software distributed under the License is distributed on an
 * "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY
 * KIND, either express or implied.  See the License for the
 * specific language governing permissions and limitations
 * under the License.
 */

package org.elasticsearch.index.shard;

import com.google.common.base.Charsets;
import com.google.common.base.Preconditions;
import org.apache.lucene.codecs.PostingsFormat;
import org.apache.lucene.index.CheckIndex;
import org.apache.lucene.store.AlreadyClosedException;
import org.apache.lucene.util.IOUtils;
import org.apache.lucene.util.ThreadInterruptedException;
import org.elasticsearch.ElasticsearchException;
import org.elasticsearch.Version;
import org.elasticsearch.action.admin.indices.flush.FlushRequest;
import org.elasticsearch.action.admin.indices.optimize.OptimizeRequest;
import org.elasticsearch.action.admin.indices.upgrade.post.UpgradeRequest;
import org.elasticsearch.cluster.ClusterService;
import org.elasticsearch.cluster.metadata.IndexMetaData;
import org.elasticsearch.cluster.node.DiscoveryNode;
import org.elasticsearch.cluster.routing.RestoreSource;
import org.elasticsearch.cluster.routing.ShardRouting;
import org.elasticsearch.cluster.routing.ShardRoutingState;
import org.elasticsearch.common.Booleans;
import org.elasticsearch.common.Nullable;
import org.elasticsearch.common.collect.Tuple;
import org.elasticsearch.common.inject.Inject;
import org.elasticsearch.common.io.stream.BytesStreamOutput;
import org.elasticsearch.common.logging.ESLogger;
import org.elasticsearch.common.lucene.Lucene;
import org.elasticsearch.common.metrics.MeanMetric;
import org.elasticsearch.common.settings.Settings;
import org.elasticsearch.common.unit.ByteSizeValue;
import org.elasticsearch.common.unit.TimeValue;
import org.elasticsearch.common.util.BigArrays;
import org.elasticsearch.common.util.concurrent.AbstractRefCounted;
import org.elasticsearch.common.util.concurrent.FutureUtils;
import org.elasticsearch.env.NodeEnvironment;
import org.elasticsearch.gateway.MetaDataStateFormat;
import org.elasticsearch.index.IndexService;
import org.elasticsearch.index.VersionType;
import org.elasticsearch.index.aliases.IndexAliasesService;
import org.elasticsearch.index.cache.IndexCache;
import org.elasticsearch.index.cache.bitset.ShardBitsetFilterCache;
import org.elasticsearch.index.cache.filter.FilterCacheStats;
import org.elasticsearch.index.cache.filter.ShardFilterCache;
import org.elasticsearch.index.cache.query.ShardQueryCache;
import org.elasticsearch.index.codec.CodecService;
import org.elasticsearch.index.deletionpolicy.SnapshotDeletionPolicy;
import org.elasticsearch.index.deletionpolicy.SnapshotIndexCommit;
import org.elasticsearch.index.engine.*;
import org.elasticsearch.index.fielddata.FieldDataStats;
import org.elasticsearch.index.fielddata.IndexFieldDataService;
import org.elasticsearch.index.fielddata.ShardFieldData;
import org.elasticsearch.index.flush.FlushStats;
import org.elasticsearch.index.get.GetStats;
import org.elasticsearch.index.get.ShardGetService;
import org.elasticsearch.index.indexing.IndexingStats;
import org.elasticsearch.index.indexing.ShardIndexingService;
import org.elasticsearch.index.mapper.*;
import org.elasticsearch.index.merge.MergeStats;
import org.elasticsearch.index.merge.policy.MergePolicyProvider;
import org.elasticsearch.index.merge.scheduler.MergeSchedulerProvider;
import org.elasticsearch.index.percolator.PercolatorQueriesRegistry;
import org.elasticsearch.index.percolator.stats.ShardPercolateService;
import org.elasticsearch.index.query.IndexQueryParserService;
import org.elasticsearch.index.recovery.RecoveryStats;
import org.elasticsearch.index.refresh.RefreshStats;
import org.elasticsearch.index.search.stats.SearchStats;
import org.elasticsearch.index.search.stats.ShardSearchService;
import org.elasticsearch.index.settings.IndexSettingsService;
import org.elasticsearch.index.similarity.SimilarityService;
import org.elasticsearch.index.store.Store;
import org.elasticsearch.index.store.Store.MetadataSnapshot;
import org.elasticsearch.index.store.StoreFileMetaData;
import org.elasticsearch.index.store.StoreStats;
import org.elasticsearch.index.suggest.stats.ShardSuggestService;
import org.elasticsearch.index.suggest.stats.SuggestStats;
import org.elasticsearch.index.termvectors.ShardTermVectorsService;
import org.elasticsearch.index.translog.Translog;
import org.elasticsearch.index.translog.TranslogConfig;
import org.elasticsearch.index.translog.TranslogStats;
import org.elasticsearch.index.translog.TranslogWriter;
import org.elasticsearch.index.warmer.ShardIndexWarmerService;
import org.elasticsearch.index.warmer.WarmerStats;
import org.elasticsearch.indices.IndicesLifecycle;
import org.elasticsearch.indices.IndicesWarmer;
import org.elasticsearch.indices.InternalIndicesLifecycle;
import org.elasticsearch.indices.recovery.RecoveryState;
import org.elasticsearch.search.suggest.completion.Completion090PostingsFormat;
import org.elasticsearch.search.suggest.completion.CompletionStats;
import org.elasticsearch.threadpool.ThreadPool;

import java.io.IOException;
import java.io.PrintStream;
import java.nio.channels.ClosedByInterruptException;
import java.util.Arrays;
import java.util.Locale;
import java.util.Map;
import java.util.concurrent.CopyOnWriteArrayList;
import java.util.concurrent.ScheduledFuture;
import java.util.concurrent.TimeUnit;
import java.util.concurrent.atomic.AtomicReference;

/**
 *
 */
public class IndexShard extends AbstractIndexShardComponent {

    private final ThreadPool threadPool;
    private final IndexSettingsService indexSettingsService;
    private final MapperService mapperService;
    private final IndexQueryParserService queryParserService;
    private final IndexCache indexCache;
    private final InternalIndicesLifecycle indicesLifecycle;
    private final Store store;
    private final MergeSchedulerProvider mergeScheduler;
    private final IndexAliasesService indexAliasesService;
    private final ShardIndexingService indexingService;
    private final ShardSearchService searchService;
    private final ShardGetService getService;
    private final ShardIndexWarmerService shardWarmerService;
    private final ShardFilterCache shardFilterCache;
    private final ShardQueryCache shardQueryCache;
    private final ShardFieldData shardFieldData;
    private final PercolatorQueriesRegistry percolatorQueriesRegistry;
    private final ShardPercolateService shardPercolateService;
    private final ShardTermVectorsService termVectorsService;
    private final IndexFieldDataService indexFieldDataService;
    private final IndexService indexService;
    private final ShardSuggestService shardSuggestService;
    private final ShardBitsetFilterCache shardBitsetFilterCache;
    private final DiscoveryNode localNode;

    private final Object mutex = new Object();
    private final String checkIndexOnStartup;
    private final NodeEnvironment nodeEnv;
    private final CodecService codecService;
    private final IndicesWarmer warmer;
    private final SnapshotDeletionPolicy deletionPolicy;
    private final SimilarityService similarityService;
    private final MergePolicyProvider mergePolicyProvider;
    private final EngineConfig engineConfig;
    private final TranslogConfig translogConfig;

    private TimeValue refreshInterval;

    private volatile ScheduledFuture refreshScheduledFuture;
    private volatile ScheduledFuture mergeScheduleFuture;
    protected volatile ShardRouting shardRouting;
    protected volatile IndexShardState state;
    protected final AtomicReference<Engine> currentEngineReference = new AtomicReference<>();
    protected final EngineFactory engineFactory;

    @Nullable
    private RecoveryState recoveryState;

    private final RecoveryStats recoveryStats = new RecoveryStats();

    private ApplyRefreshSettings applyRefreshSettings = new ApplyRefreshSettings();

    private final MeanMetric refreshMetric = new MeanMetric();
    private final MeanMetric flushMetric = new MeanMetric();

    private final ShardEngineFailListener failedEngineListener = new ShardEngineFailListener();

    private final MapperAnalyzer mapperAnalyzer;
    private volatile boolean flushOnClose = true;

    /**
     * Index setting to control if a flush is executed before engine is closed
     * This setting is realtime updateable.
     */
    public static final String INDEX_FLUSH_ON_CLOSE = "index.flush_on_close";
    private final ShardPath path;

    private final IndexShardOperationCounter indexShardOperationCounter;

    @Inject
    public IndexShard(ShardId shardId, IndexSettingsService indexSettingsService, IndicesLifecycle indicesLifecycle, Store store, MergeSchedulerProvider mergeScheduler,
                      ThreadPool threadPool, MapperService mapperService, IndexQueryParserService queryParserService, IndexCache indexCache, IndexAliasesService indexAliasesService, ShardIndexingService indexingService, ShardGetService getService, ShardSearchService searchService, ShardIndexWarmerService shardWarmerService,
                      ShardFilterCache shardFilterCache, ShardFieldData shardFieldData, PercolatorQueriesRegistry percolatorQueriesRegistry, ShardPercolateService shardPercolateService, CodecService codecService,
                      ShardTermVectorsService termVectorsService, IndexFieldDataService indexFieldDataService, IndexService indexService, ShardSuggestService shardSuggestService,
                      ShardQueryCache shardQueryCache, ShardBitsetFilterCache shardBitsetFilterCache,
                      @Nullable IndicesWarmer warmer, SnapshotDeletionPolicy deletionPolicy, SimilarityService similarityService, MergePolicyProvider mergePolicyProvider, EngineFactory factory,
                      ClusterService clusterService, NodeEnvironment nodeEnv, ShardPath path, BigArrays bigArrays) {
        super(shardId, indexSettingsService.getSettings());
        this.codecService = codecService;
        this.warmer = warmer;
        this.deletionPolicy = deletionPolicy;
        this.similarityService = similarityService;
        this.mergePolicyProvider = mergePolicyProvider;
        Preconditions.checkNotNull(store, "Store must be provided to the index shard");
        Preconditions.checkNotNull(deletionPolicy, "Snapshot deletion policy must be provided to the index shard");
        this.engineFactory = factory;
        this.indicesLifecycle = (InternalIndicesLifecycle) indicesLifecycle;
        this.indexSettingsService = indexSettingsService;
        this.store = store;
        this.mergeScheduler = mergeScheduler;
        this.threadPool = threadPool;
        this.mapperService = mapperService;
        this.queryParserService = queryParserService;
        this.indexCache = indexCache;
        this.indexAliasesService = indexAliasesService;
        this.indexingService = indexingService;
        this.getService = getService.setIndexShard(this);
        this.termVectorsService = termVectorsService.setIndexShard(this);
        this.searchService = searchService;
        this.shardWarmerService = shardWarmerService;
        this.shardFilterCache = shardFilterCache;
        this.shardQueryCache = shardQueryCache;
        this.shardFieldData = shardFieldData;
        this.percolatorQueriesRegistry = percolatorQueriesRegistry;
        this.shardPercolateService = shardPercolateService;
        this.indexFieldDataService = indexFieldDataService;
        this.indexService = indexService;
        this.shardSuggestService = shardSuggestService;
        this.shardBitsetFilterCache = shardBitsetFilterCache;
        assert clusterService.localNode() != null : "Local node is null lifecycle state is: " + clusterService.lifecycleState();
        this.localNode = clusterService.localNode();
        state = IndexShardState.CREATED;
        this.refreshInterval = indexSettings.getAsTime(INDEX_REFRESH_INTERVAL, EngineConfig.DEFAULT_REFRESH_INTERVAL);
        this.flushOnClose = indexSettings.getAsBoolean(INDEX_FLUSH_ON_CLOSE, true);
        this.nodeEnv = nodeEnv;
        indexSettingsService.addListener(applyRefreshSettings);
        this.mapperAnalyzer = new MapperAnalyzer(mapperService);
        this.path = path;
        /* create engine config */

        logger.debug("state: [CREATED]");

        this.checkIndexOnStartup = indexSettings.get("index.shard.check_on_startup", "false");
        this.translogConfig = new TranslogConfig(shardId, shardPath().resolveTranslog(), indexSettings, getFromSettings(logger, indexSettings, Translog.Durabilty.REQUEST),
                bigArrays, threadPool);
        this.engineConfig = newEngineConfig(translogConfig);

        this.indexShardOperationCounter = new IndexShardOperationCounter(logger, shardId);
    }

    public Store store() {
        return this.store;
    }

    /** returns true if this shard supports indexing (i.e., write) operations. */
    public boolean canIndex() {
        return true;
    }

    public ShardIndexingService indexingService() {
        return this.indexingService;
    }

    public ShardGetService getService() {
        return this.getService;
    }

    public ShardTermVectorsService termVectorsService() {
        return termVectorsService;
    }

    public ShardSuggestService shardSuggestService() {
        return shardSuggestService;
    }

    public ShardBitsetFilterCache shardBitsetFilterCache() {
        return shardBitsetFilterCache;
    }

    public IndexFieldDataService indexFieldDataService() {
        return indexFieldDataService;
    }

    public MapperService mapperService() {
        return mapperService;
    }

    public IndexService indexService() {
        return indexService;
    }

    public ShardSearchService searchService() {
        return this.searchService;
    }

    public ShardIndexWarmerService warmerService() {
        return this.shardWarmerService;
    }

    public ShardFilterCache filterCache() {
        return this.shardFilterCache;
    }

    public ShardQueryCache queryCache() {
        return this.shardQueryCache;
    }

    public ShardFieldData fieldData() {
        return this.shardFieldData;
    }

    /**
     * Returns the latest cluster routing entry received with this shard. Might be null if the
     * shard was just created.
     */
    public ShardRouting routingEntry() {
        return this.shardRouting;
    }

    /**
     * Updates the shards routing entry. This mutate the shards internal state depending
     * on the changes that get introduced by the new routing value. This method will persist shard level metadata
     * unless explicitly disabled.
     */
    public void updateRoutingEntry(final ShardRouting newRouting, final boolean persistState) {
        final ShardRouting currentRouting = this.shardRouting;
        if (!newRouting.shardId().equals(shardId())) {
            throw new IllegalArgumentException("Trying to set a routing entry with shardId [" + newRouting.shardId() + "] on a shard with shardId [" + shardId() + "]");
        }
        try {
            if (currentRouting != null) {
                assert newRouting.version() > currentRouting.version() : "expected: " + newRouting.version() + " > " + currentRouting.version();
                if (!newRouting.primary() && currentRouting.primary()) {
                    logger.warn("suspect illegal state: trying to move shard from primary mode to replica mode");
                }
                // if its the same routing, return
                if (currentRouting.equals(newRouting)) {
                    this.shardRouting = newRouting; // might have a new version
                    return;
                }
            }

            if (state == IndexShardState.POST_RECOVERY) {
                // if the state is started or relocating (cause it might move right away from started to relocating)
                // then move to STARTED
                if (newRouting.state() == ShardRoutingState.STARTED || newRouting.state() == ShardRoutingState.RELOCATING) {
                    // we want to refresh *before* we move to internal STARTED state
                    try {
                        engine().refresh("cluster_state_started");
                    } catch (Throwable t) {
                        logger.debug("failed to refresh due to move to cluster wide started", t);
                    }

                    boolean movedToStarted = false;
                    synchronized (mutex) {
                        // do the check under a mutex, so we make sure to only change to STARTED if in POST_RECOVERY
                        if (state == IndexShardState.POST_RECOVERY) {
                            changeState(IndexShardState.STARTED, "global state is [" + newRouting.state() + "]");
                            movedToStarted = true;
                        } else {
                            logger.debug("state [{}] not changed, not in POST_RECOVERY, global state is [{}]", state, newRouting.state());
                        }
                    }
                    if (movedToStarted) {
                        indicesLifecycle.afterIndexShardStarted(this);
                    }
                }
            }
            this.shardRouting = newRouting;
            indicesLifecycle.shardRoutingChanged(this, currentRouting, newRouting);
        } finally {
            if (persistState) {
                persistMetadata(newRouting, currentRouting);
            }
        }
    }

    /**
     * Marks the shard as recovering based on a remote or local node, fails with exception is recovering is not allowed to be set.
     */
    public IndexShardState recovering(String reason, RecoveryState.Type type, DiscoveryNode sourceNode) throws IndexShardStartedException,
            IndexShardRelocatedException, IndexShardRecoveringException, IndexShardClosedException {
        return recovering(reason, new RecoveryState(shardId, shardRouting.primary(), type, sourceNode, localNode));
    }

    /**
     * Marks the shard as recovering based on a restore, fails with exception is recovering is not allowed to be set.
     */
    public IndexShardState recovering(String reason, RecoveryState.Type type, RestoreSource restoreSource) throws IndexShardStartedException {
        return recovering(reason, new RecoveryState(shardId, shardRouting.primary(), type, restoreSource, localNode));
    }

    private IndexShardState recovering(String reason, RecoveryState recoveryState) throws IndexShardStartedException,
            IndexShardRelocatedException, IndexShardRecoveringException, IndexShardClosedException {
        synchronized (mutex) {
            if (state == IndexShardState.CLOSED) {
                throw new IndexShardClosedException(shardId);
            }
            if (state == IndexShardState.STARTED) {
                throw new IndexShardStartedException(shardId);
            }
            if (state == IndexShardState.RELOCATED) {
                throw new IndexShardRelocatedException(shardId);
            }
            if (state == IndexShardState.RECOVERING) {
                throw new IndexShardRecoveringException(shardId);
            }
            if (state == IndexShardState.POST_RECOVERY) {
                throw new IndexShardRecoveringException(shardId);
            }
            this.recoveryState = recoveryState;
            return changeState(IndexShardState.RECOVERING, reason);
        }
    }

    public IndexShard relocated(String reason) throws IndexShardNotStartedException {
        synchronized (mutex) {
            if (state != IndexShardState.STARTED) {
                throw new IndexShardNotStartedException(shardId, state);
            }
            changeState(IndexShardState.RELOCATED, reason);
        }
        return this;
    }

    public IndexShardState state() {
        return state;
    }

    /**
     * Changes the state of the current shard
     *
     * @param newState the new shard state
     * @param reason   the reason for the state change
     * @return the previous shard state
     */
    private IndexShardState changeState(IndexShardState newState, String reason) {
        logger.debug("state: [{}]->[{}], reason [{}]", state, newState, reason);
        IndexShardState previousState = state;
        state = newState;
        this.indicesLifecycle.indexShardStateChanged(this, previousState, reason);
        return previousState;
    }

    public Engine.Create prepareCreate(SourceToParse source, long version, VersionType versionType, Engine.Operation.Origin origin, boolean canHaveDuplicates, boolean autoGeneratedId) {
        try {
            return prepareCreate(docMapper(source.type()), source, version, versionType, origin, state != IndexShardState.STARTED || canHaveDuplicates, autoGeneratedId);
        } catch (Throwable t) {
            verifyNotClosed(t);
            throw t;
        }
    }

    static Engine.Create prepareCreate(Tuple<DocumentMapper, Mapping> docMapper, SourceToParse source, long version, VersionType versionType, Engine.Operation.Origin origin, boolean canHaveDuplicates, boolean autoGeneratedId) {
        long startTime = System.nanoTime();
        ParsedDocument doc = docMapper.v1().parse(source);
        if (docMapper.v2() != null) {
            doc.addDynamicMappingsUpdate(docMapper.v2());
        }
        return new Engine.Create(docMapper.v1(), docMapper.v1().uidMapper().term(doc.uid().stringValue()), doc, version, versionType, origin, startTime, canHaveDuplicates, autoGeneratedId);
    }

    public void create(Engine.Create create) {
        writeAllowed(create.origin());
        create = indexingService.preCreate(create);
        mapperAnalyzer.setType(create.type());
        try {
            if (logger.isTraceEnabled()) {
                logger.trace("index [{}][{}]{}", create.type(), create.id(), create.docs());
            }
            engine().create(create);
            create.endTime(System.nanoTime());
        } catch (Throwable ex) {
            indexingService.postCreate(create, ex);
            throw ex;
        }
        indexingService.postCreate(create);
    }

    public Engine.Index prepareIndex(SourceToParse source, long version, VersionType versionType, Engine.Operation.Origin origin, boolean canHaveDuplicates) {
        try {
            return prepareIndex(docMapper(source.type()), source, version, versionType, origin, state != IndexShardState.STARTED || canHaveDuplicates);
        } catch (Throwable t) {
            verifyNotClosed(t);
            throw t;
        }
    }

    static Engine.Index prepareIndex(Tuple<DocumentMapper, Mapping> docMapper, SourceToParse source, long version, VersionType versionType, Engine.Operation.Origin origin, boolean canHaveDuplicates) {
        long startTime = System.nanoTime();
        ParsedDocument doc = docMapper.v1().parse(source);
        if (docMapper.v2() != null) {
            doc.addDynamicMappingsUpdate(docMapper.v2());
        }
        return new Engine.Index(docMapper.v1(), docMapper.v1().uidMapper().term(doc.uid().stringValue()), doc, version, versionType, origin, startTime, canHaveDuplicates);
    }

    /**
     * Index a document and return whether it was created, as opposed to just
     * updated.
     */
    public boolean index(Engine.Index index) {
        writeAllowed(index.origin());
        index = indexingService.preIndex(index);
        mapperAnalyzer.setType(index.type());
        final boolean created;
        try {
            if (logger.isTraceEnabled()) {
                logger.trace("index [{}][{}]{}", index.type(), index.id(), index.docs());
            }
            created = engine().index(index);
            index.endTime(System.nanoTime());
        } catch (Throwable ex) {
            indexingService.postIndex(index, ex);
            throw ex;
        }
        indexingService.postIndex(index);
        return created;
    }

    public Engine.Delete prepareDelete(String type, String id, long version, VersionType versionType, Engine.Operation.Origin origin) {
        long startTime = System.nanoTime();
        final DocumentMapper documentMapper = docMapper(type).v1();
        return new Engine.Delete(type, id, documentMapper.uidMapper().term(Uid.createUid(type, id)), version, versionType, origin, startTime, false);
    }

    public void delete(Engine.Delete delete) {
        writeAllowed(delete.origin());
        delete = indexingService.preDelete(delete);
        try {
            if (logger.isTraceEnabled()) {
                logger.trace("delete [{}]", delete.uid().text());
            }
            engine().delete(delete);
            delete.endTime(System.nanoTime());
        } catch (Throwable ex) {
            indexingService.postDelete(delete, ex);
            throw ex;
        }
        indexingService.postDelete(delete);
    }

    public Engine.GetResult get(Engine.Get get) {
        readAllowed();
        return engine().get(get);
    }

    public void refresh(String source) {
        verifyNotClosed();
        if (logger.isTraceEnabled()) {
            logger.trace("refresh with source: {}", source);
        }
        long time = System.nanoTime();
        engine().refresh(source);
        refreshMetric.inc(System.nanoTime() - time);
    }

    public RefreshStats refreshStats() {
        return new RefreshStats(refreshMetric.count(), TimeUnit.NANOSECONDS.toMillis(refreshMetric.sum()));
    }

    public FlushStats flushStats() {
        return new FlushStats(flushMetric.count(), TimeUnit.NANOSECONDS.toMillis(flushMetric.sum()));
    }

    public DocsStats docStats() {
        final Engine.Searcher searcher = acquireSearcher("doc_stats");
        try {
            return new DocsStats(searcher.reader().numDocs(), searcher.reader().numDeletedDocs());
        } finally {
            searcher.close();
        }
    }

    /**
     * @return {@link CommitStats} if engine is open, otherwise null
     */
    @Nullable
    public CommitStats commitStats() {
        Engine engine = engineUnsafe();
        return engine == null ? null : engine.commitStats();
    }

    public IndexingStats indexingStats(String... types) {
        return indexingService.stats(types);
    }

    public SearchStats searchStats(String... groups) {
        return searchService.stats(groups);
    }

    public GetStats getStats() {
        return getService.stats();
    }

    public StoreStats storeStats() {
        try {
            return store.stats();
        } catch (IOException e) {
            throw new ElasticsearchException("io exception while building 'store stats'", e);
        } catch (AlreadyClosedException ex) {
            return null; // already closed
        }
    }

    public MergeStats mergeStats() {
        return mergeScheduler.stats();
    }

    public SegmentsStats segmentStats() {
        SegmentsStats segmentsStats = engine().segmentsStats();
        segmentsStats.addBitsetMemoryInBytes(shardBitsetFilterCache.getMemorySizeInBytes());
        return segmentsStats;
    }

    public WarmerStats warmerStats() {
        return shardWarmerService.stats();
    }

    public FilterCacheStats filterCacheStats() {
        return shardFilterCache.stats();
    }

    public FieldDataStats fieldDataStats(String... fields) {
        return shardFieldData.stats(fields);
    }

    public PercolatorQueriesRegistry percolateRegistry() {
        return percolatorQueriesRegistry;
    }

    public ShardPercolateService shardPercolateService() {
        return shardPercolateService;
    }

    public TranslogStats translogStats() {
        return engine().getTranslog().stats();
    }

    public SuggestStats suggestStats() {
        return shardSuggestService.stats();
    }

    public CompletionStats completionStats(String... fields) {
        CompletionStats completionStats = new CompletionStats();
        final Engine.Searcher currentSearcher = acquireSearcher("completion_stats");
        try {
            PostingsFormat postingsFormat = PostingsFormat.forName(Completion090PostingsFormat.CODEC_NAME);
            if (postingsFormat instanceof Completion090PostingsFormat) {
                Completion090PostingsFormat completionPostingsFormat = (Completion090PostingsFormat) postingsFormat;
                completionStats.add(completionPostingsFormat.completionStats(currentSearcher.reader(), fields));
            }
        } finally {
            currentSearcher.close();
        }
        return completionStats;
    }

    public Engine.SyncedFlushResult syncFlush(String syncId, Engine.CommitId expectedCommitId) {
        verifyStartedOrRecovering();
        logger.trace("trying to sync flush. sync id [{}]. expected commit id [{}]]", syncId, expectedCommitId);
        return engine().syncFlush(syncId, expectedCommitId);
    }

    public Engine.CommitId flush(FlushRequest request) throws ElasticsearchException {
        boolean waitIfOngoing = request.waitIfOngoing();
        boolean force = request.force();
        if (logger.isTraceEnabled()) {
            logger.trace("flush with {}", request);
        }
        // we allows flush while recovering, since we allow for operations to happen
        // while recovering, and we want to keep the translog at bay (up to deletes, which
        // we don't gc).
        verifyStartedOrRecovering();

        long time = System.nanoTime();
        Engine.CommitId commitId = engine().flush(force, waitIfOngoing);
        flushMetric.inc(System.nanoTime() - time);
        return commitId;

    }

    public void optimize(OptimizeRequest optimize) {
        verifyStarted();
        if (logger.isTraceEnabled()) {
            logger.trace("optimize with {}", optimize);
        }
        engine().forceMerge(optimize.flush(), optimize.maxNumSegments(), optimize.onlyExpungeDeletes(), false, false);
    }

    /**
     * Upgrades the shard to the current version of Lucene and returns the minimum segment version
     */
    public org.apache.lucene.util.Version upgrade(UpgradeRequest upgrade) {
        verifyStarted();
        if (logger.isTraceEnabled()) {
            logger.trace("upgrade with {}", upgrade);
        }
        org.apache.lucene.util.Version previousVersion = minimumCompatibleVersion();
        // we just want to upgrade the segments, not actually optimize to a single segment
        engine().forceMerge(true,  // we need to flush at the end to make sure the upgrade is durable
                Integer.MAX_VALUE, // we just want to upgrade the segments, not actually optimize to a single segment
                false, true, upgrade.upgradeOnlyAncientSegments());
        org.apache.lucene.util.Version version = minimumCompatibleVersion();
        if (logger.isTraceEnabled()) {
            logger.trace("upgraded segment {} from version {} to version {}", previousVersion, version);
        }

        return version;
    }

    public org.apache.lucene.util.Version minimumCompatibleVersion() {
        org.apache.lucene.util.Version luceneVersion = null;
        for(Segment segment : engine().segments(false)) {
            if (luceneVersion == null || luceneVersion.onOrAfter(segment.getVersion())) {
                luceneVersion = segment.getVersion();
            }
        }
        return luceneVersion == null ?  Version.indexCreated(indexSettings).luceneVersion : luceneVersion;
    }

    public SnapshotIndexCommit snapshotIndex(boolean flushFirst) throws EngineException {
        IndexShardState state = this.state; // one time volatile read
        // we allow snapshot on closed index shard, since we want to do one after we close the shard and before we close the engine
        if (state == IndexShardState.STARTED || state == IndexShardState.RELOCATED || state == IndexShardState.CLOSED) {
            return engine().snapshotIndex(flushFirst);
        } else {
            throw new IllegalIndexShardStateException(shardId, state, "snapshot is not allowed");
        }
    }

    public void failShard(String reason, Throwable e) {
        // fail the engine. This will cause this shard to also be removed from the node's index service.
        engine().failEngine(reason, e);
    }

    public Engine.Searcher acquireSearcher(String source) {
        return acquireSearcher(source, false);
    }

    public Engine.Searcher acquireSearcher(String source, boolean searcherForWriteOperation) {
        readAllowed(searcherForWriteOperation);
        return engine().acquireSearcher(source);
    }

    public void close(String reason, boolean flushEngine) throws IOException {
        synchronized (mutex) {
            try {
                indexSettingsService.removeListener(applyRefreshSettings);
                if (state != IndexShardState.CLOSED) {
                    FutureUtils.cancel(refreshScheduledFuture);
                    refreshScheduledFuture = null;
                    FutureUtils.cancel(mergeScheduleFuture);
                    mergeScheduleFuture = null;
                }
                changeState(IndexShardState.CLOSED, reason);
                indexShardOperationCounter.decRef();
            } finally {
                final Engine engine = this.currentEngineReference.getAndSet(null);
                try {
                    if (engine != null && flushEngine && this.flushOnClose) {
                        engine.flushAndClose();
                    }
                } finally { // playing safe here and close the engine even if the above succeeds - close can be called multiple times
                    IOUtils.close(engine);
                }
            }
        }
    }

    public IndexShard postRecovery(String reason) throws IndexShardStartedException, IndexShardRelocatedException, IndexShardClosedException {
        synchronized (mutex) {
            if (state == IndexShardState.CLOSED) {
                throw new IndexShardClosedException(shardId);
            }
            if (state == IndexShardState.STARTED) {
                throw new IndexShardStartedException(shardId);
            }
            if (state == IndexShardState.RELOCATED) {
                throw new IndexShardRelocatedException(shardId);
            }
            recoveryState.setStage(RecoveryState.Stage.DONE);
            changeState(IndexShardState.POST_RECOVERY, reason);
        }
        indicesLifecycle.afterIndexShardPostRecovery(this);
        return this;
    }

    /**
     * called before starting to copy index files over
     */
    public void prepareForIndexRecovery() {
        if (state != IndexShardState.RECOVERING) {
            throw new IndexShardNotRecoveringException(shardId, state);
        }
        recoveryState.setStage(RecoveryState.Stage.INDEX);
        assert currentEngineReference.get() == null;
    }

    /**
     * Applies all operations in the iterable to the current engine and returns the number of operations applied.
     * This operation will stop applying operations once an operation failed to apply.
     * Note: This method is typically used in peer recovery to replay remote transaction log entries.
     */
    public int performBatchRecovery(Iterable<Translog.Operation> operations) {
        if (state != IndexShardState.RECOVERING) {
            throw new IndexShardNotRecoveringException(shardId, state);
        }
        return engineConfig.getTranslogRecoveryPerformer().performBatchRecovery(engine(), operations);
    }

    /**
     * After the store has been recovered, we need to start the engine in order to apply operations
     */
    public Map<String, Mapping> performTranslogRecovery() {
        final Map<String, Mapping> recoveredTypes = internalPerformTranslogRecovery(false);
        assert recoveryState.getStage() == RecoveryState.Stage.TRANSLOG : "TRANSLOG stage expected but was: " + recoveryState.getStage();
        return recoveredTypes;

    }

    private Map<String, Mapping> internalPerformTranslogRecovery(boolean skipTranslogRecovery) {
        if (state != IndexShardState.RECOVERING) {
            throw new IndexShardNotRecoveringException(shardId, state);
        }
        recoveryState.setStage(RecoveryState.Stage.VERIFY_INDEX);
        // also check here, before we apply the translog
        if (Booleans.parseBoolean(checkIndexOnStartup, false)) {
            checkIndex();
        }
        recoveryState.setStage(RecoveryState.Stage.TRANSLOG);
        // we disable deletes since we allow for operations to be executed against the shard while recovering
        // but we need to make sure we don't loose deletes until we are done recovering
        engineConfig.setEnableGcDeletes(false);
        createNewEngine(skipTranslogRecovery, engineConfig);
        return engineConfig.getTranslogRecoveryPerformer().getRecoveredTypes();
    }

    /**
     * After the store has been recovered, we need to start the engine. This method starts a new engine but skips
     * the replay of the transaction log which is required in cases where we restore a previous index or recover from
     * a remote peer.
     *
     * @param wipeTranslogs if set to <code>true</code> all skipped / uncommitted translogs are removed.
     */
    public void skipTranslogRecovery(boolean wipeTranslogs) throws IOException {
        assert engineUnsafe() == null : "engine was already created";
        Map<String, Mapping> recoveredTypes = internalPerformTranslogRecovery(true);
        assert recoveredTypes.isEmpty();
        assert recoveryState.getTranslog().recoveredOperations() == 0;
    }

    /**
     * called if recovery has to be restarted after network error / delay **
     */
    public void performRecoveryRestart() throws IOException {
        synchronized (mutex) {
            if (state != IndexShardState.RECOVERING) {
                throw new IndexShardNotRecoveringException(shardId, state);
            }
            final Engine engine = this.currentEngineReference.getAndSet(null);
            IOUtils.close(engine);
            recoveryState().setStage(RecoveryState.Stage.INIT);
        }
    }

    /**
     * returns stats about ongoing recoveries, both source and target
     */
    public RecoveryStats recoveryStats() {
        return recoveryStats;
    }

    /**
     * Returns the current {@link RecoveryState} if this shard is recovering or has been recovering.
     * Returns null if the recovery has not yet started or shard was not recovered (created via an API).
     */
    public RecoveryState recoveryState() {
        return this.recoveryState;
    }

    /**
     * perform the last stages of recovery once all translog operations are done.
     * note that you should still call {@link #postRecovery(String)}.
     */
    public void finalizeRecovery() {
        recoveryState().setStage(RecoveryState.Stage.FINALIZE);
        engine().refresh("recovery_finalization");
        startScheduledTasksIfNeeded();
        engineConfig.setEnableGcDeletes(true);
    }

    /**
     * Returns <tt>true</tt> if this shard can ignore a recovery attempt made to it (since the already doing/done it)
     */
    public boolean ignoreRecoveryAttempt() {
        IndexShardState state = state(); // one time volatile read
        return state == IndexShardState.POST_RECOVERY || state == IndexShardState.RECOVERING || state == IndexShardState.STARTED ||
                state == IndexShardState.RELOCATED || state == IndexShardState.CLOSED;
    }

    public void readAllowed() throws IllegalIndexShardStateException {
        readAllowed(false);
    }


    private void readAllowed(boolean writeOperation) throws IllegalIndexShardStateException {
        IndexShardState state = this.state; // one time volatile read
        if (writeOperation) {
            if (state != IndexShardState.STARTED && state != IndexShardState.RELOCATED && state != IndexShardState.RECOVERING && state != IndexShardState.POST_RECOVERY) {
                throw new IllegalIndexShardStateException(shardId, state, "operations only allowed when started/relocated");
            }
        } else {
            if (state != IndexShardState.STARTED && state != IndexShardState.RELOCATED) {
                throw new IllegalIndexShardStateException(shardId, state, "operations only allowed when started/relocated");
            }
        }
    }

    private void writeAllowed(Engine.Operation.Origin origin) throws IllegalIndexShardStateException {
        IndexShardState state = this.state; // one time volatile read

        if (origin == Engine.Operation.Origin.PRIMARY) {
            // for primaries, we only allow to write when actually started (so the cluster has decided we started)
            // otherwise, we need to retry, we also want to still allow to index if we are relocated in case it fails
            if (state != IndexShardState.STARTED && state != IndexShardState.RELOCATED) {
                throw new IllegalIndexShardStateException(shardId, state, "operation only allowed when started/recovering, origin [" + origin + "]");
            }
        } else {
            // for replicas, we allow to write also while recovering, since we index also during recovery to replicas
            // and rely on version checks to make sure its consistent
            if (state != IndexShardState.STARTED && state != IndexShardState.RELOCATED && state != IndexShardState.RECOVERING && state != IndexShardState.POST_RECOVERY) {
                throw new IllegalIndexShardStateException(shardId, state, "operation only allowed when started/recovering, origin [" + origin + "]");
            }
        }
    }

    protected final void verifyStartedOrRecovering() throws IllegalIndexShardStateException {
        IndexShardState state = this.state; // one time volatile read
        if (state != IndexShardState.STARTED && state != IndexShardState.RECOVERING && state != IndexShardState.POST_RECOVERY) {
            throw new IllegalIndexShardStateException(shardId, state, "operation only allowed when started/recovering");
        }
    }

    private void verifyNotClosed() throws IllegalIndexShardStateException {
        verifyNotClosed(null);
    }

    private void verifyNotClosed(Throwable suppressed) throws IllegalIndexShardStateException {
        IndexShardState state = this.state; // one time volatile read
        if (state == IndexShardState.CLOSED) {
            final IllegalIndexShardStateException exc = new IllegalIndexShardStateException(shardId, state, "operation only allowed when not closed");
            if (suppressed != null) {
                exc.addSuppressed(suppressed);
            }
            throw exc;
        }
    }

    protected final void verifyStarted() throws IllegalIndexShardStateException {
        IndexShardState state = this.state; // one time volatile read
        if (state != IndexShardState.STARTED) {
            throw new IndexShardNotStartedException(shardId, state);
        }
    }

    private void startScheduledTasksIfNeeded() {
        if (refreshInterval.millis() > 0) {
            refreshScheduledFuture = threadPool.schedule(refreshInterval, ThreadPool.Names.SAME, new EngineRefresher());
            logger.debug("scheduling refresher every {}", refreshInterval);
        } else {
            logger.debug("scheduled refresher disabled");
        }
    }

    public static final String INDEX_REFRESH_INTERVAL = "index.refresh_interval";

    public void addFailedEngineListener(Engine.FailedEngineListener failedEngineListener) {
        this.failedEngineListener.delegates.add(failedEngineListener);
    }

    public void updateBufferSize(ByteSizeValue shardIndexingBufferSize, ByteSizeValue shardTranslogBufferSize) {
        final EngineConfig config = engineConfig;
        final ByteSizeValue preValue = config.getIndexingBufferSize();
        config.setIndexingBufferSize(shardIndexingBufferSize);
        // update engine if it is already started.
        if (preValue.bytes() != shardIndexingBufferSize.bytes() && engineUnsafe() != null) {
            // its inactive, make sure we do a refresh / full IW flush in this case, since the memory
            // changes only after a "data" change has happened to the writer
            // the index writer lazily allocates memory and a refresh will clean it all up.
            if (shardIndexingBufferSize == EngineConfig.INACTIVE_SHARD_INDEXING_BUFFER && preValue != EngineConfig.INACTIVE_SHARD_INDEXING_BUFFER) {
                logger.debug("updating index_buffer_size from [{}] to (inactive) [{}]", preValue, shardIndexingBufferSize);
                try {
                    refresh("update index buffer");
                } catch (Throwable e) {
                    logger.warn("failed to refresh after setting shard to inactive", e);
                }
            } else {
                logger.debug("updating index_buffer_size from [{}] to [{}]", preValue, shardIndexingBufferSize);
            }
        }
        Engine engine = engineUnsafe();
        if (engine != null) {
            engine.getTranslog().updateBuffer(shardTranslogBufferSize);
        }
    }

    public void markAsInactive() {
        updateBufferSize(EngineConfig.INACTIVE_SHARD_INDEXING_BUFFER, TranslogConfig.INACTIVE_SHARD_TRANSLOG_BUFFER);
        indicesLifecycle.onShardInactive(this);
    }

    public final boolean isFlushOnClose() {
        return flushOnClose;
    }

    /**
     * Deletes the shards metadata state. This method can only be executed if the shard is not active.
     *
     * @throws IOException if the delete fails
     */
    public void deleteShardState() throws IOException {
        if (this.routingEntry() != null && this.routingEntry().active()) {
            throw new IllegalStateException("Can't delete shard state on an active shard");
        }
        MetaDataStateFormat.deleteMetaState(shardPath().getDataPath());
    }

    public ShardPath shardPath() {
        return path;
    }

    private class ApplyRefreshSettings implements IndexSettingsService.Listener {
        @Override
        public void onRefreshSettings(Settings settings) {
            boolean change = false;
            synchronized (mutex) {
                if (state() == IndexShardState.CLOSED) { // no need to update anything if we are closed
                    return;
                }
                final EngineConfig config = engineConfig;
                final boolean flushOnClose = settings.getAsBoolean(INDEX_FLUSH_ON_CLOSE, IndexShard.this.flushOnClose);
                if (flushOnClose != IndexShard.this.flushOnClose) {
                    logger.info("updating {} from [{}] to [{}]", INDEX_FLUSH_ON_CLOSE, IndexShard.this.flushOnClose, flushOnClose);
                    IndexShard.this.flushOnClose = flushOnClose;
                }

                TranslogWriter.Type type = TranslogWriter.Type.fromString(settings.get(TranslogConfig.INDEX_TRANSLOG_FS_TYPE, translogConfig.getType().name()));
                if (type != translogConfig.getType()) {
                    logger.info("updating type from [{}] to [{}]", translogConfig.getType(), type);
                    translogConfig.setType(type);
                }

                final Translog.Durabilty durabilty = getFromSettings(logger, settings, translogConfig.getDurabilty());
                if (durabilty != translogConfig.getDurabilty()) {
                    logger.info("updating durability from [{}] to [{}]", translogConfig.getDurabilty(), durabilty);
                    translogConfig.setDurabilty(durabilty);
                }

                TimeValue refreshInterval = settings.getAsTime(INDEX_REFRESH_INTERVAL, IndexShard.this.refreshInterval);
                if (!refreshInterval.equals(IndexShard.this.refreshInterval)) {
                    logger.info("updating refresh_interval from [{}] to [{}]", IndexShard.this.refreshInterval, refreshInterval);
                    if (refreshScheduledFuture != null) {
                        // NOTE: we pass false here so we do NOT attempt Thread.interrupt if EngineRefresher.run is currently running.  This is
                        // very important, because doing so can cause files to suddenly be closed if they were doing IO when the interrupt
                        // hit.  See https://issues.apache.org/jira/browse/LUCENE-2239
                        FutureUtils.cancel(refreshScheduledFuture);
                        refreshScheduledFuture = null;
                    }
                    IndexShard.this.refreshInterval = refreshInterval;
                    if (refreshInterval.millis() > 0) {
                        refreshScheduledFuture = threadPool.schedule(refreshInterval, ThreadPool.Names.SAME, new EngineRefresher());
                    }
                }

                long gcDeletesInMillis = settings.getAsTime(EngineConfig.INDEX_GC_DELETES_SETTING, TimeValue.timeValueMillis(config.getGcDeletesInMillis())).millis();
                if (gcDeletesInMillis != config.getGcDeletesInMillis()) {
                    logger.info("updating {} from [{}] to [{}]", EngineConfig.INDEX_GC_DELETES_SETTING, TimeValue.timeValueMillis(config.getGcDeletesInMillis()), TimeValue.timeValueMillis(gcDeletesInMillis));
                    config.setGcDeletesInMillis(gcDeletesInMillis);
                    change = true;
                }

                final boolean compoundOnFlush = settings.getAsBoolean(EngineConfig.INDEX_COMPOUND_ON_FLUSH, config.isCompoundOnFlush());
                if (compoundOnFlush != config.isCompoundOnFlush()) {
                    logger.info("updating {} from [{}] to [{}]", EngineConfig.INDEX_COMPOUND_ON_FLUSH, config.isCompoundOnFlush(), compoundOnFlush);
                    config.setCompoundOnFlush(compoundOnFlush);
                    change = true;
                }
                final String versionMapSize = settings.get(EngineConfig.INDEX_VERSION_MAP_SIZE, config.getVersionMapSizeSetting());
                if (config.getVersionMapSizeSetting().equals(versionMapSize) == false) {
                    config.setVersionMapSizeSetting(versionMapSize);
                }
            }
            if (change) {
                refresh("apply settings");
            }
        }
    }

    class EngineRefresher implements Runnable {
        @Override
        public void run() {
            // we check before if a refresh is needed, if not, we reschedule, otherwise, we fork, refresh, and then reschedule
            if (!engine().refreshNeeded()) {
                reschedule();
                return;
            }
            threadPool.executor(ThreadPool.Names.REFRESH).execute(new Runnable() {
                @Override
                public void run() {
                    try {
                        if (engine().refreshNeeded()) {
                            refresh("schedule");
                        }
                    } catch (EngineClosedException e) {
                        // we are being closed, ignore
                    } catch (RefreshFailedEngineException e) {
                        if (e.getCause() instanceof InterruptedException) {
                            // ignore, we are being shutdown
                        } else if (e.getCause() instanceof ClosedByInterruptException) {
                            // ignore, we are being shutdown
                        } else if (e.getCause() instanceof ThreadInterruptedException) {
                            // ignore, we are being shutdown
                        } else {
                            if (state != IndexShardState.CLOSED) {
                                logger.warn("Failed to perform scheduled engine refresh", e);
                            }
                        }
                    } catch (Exception e) {
                        if (state != IndexShardState.CLOSED) {
                            logger.warn("Failed to perform scheduled engine refresh", e);
                        }
                    }

                    reschedule();
                }
            });
        }

        /**
         * Schedules another (future) refresh, if refresh_interval is still enabled.
         */
        private void reschedule() {
            synchronized (mutex) {
                if (state != IndexShardState.CLOSED && refreshInterval.millis() > 0) {
                    refreshScheduledFuture = threadPool.schedule(refreshInterval, ThreadPool.Names.SAME, this);
                }
            }
        }
    }

    private void checkIndex() throws IndexShardException {
        if (store.tryIncRef()) {
            try {
                doCheckIndex();
            } catch (IOException e) {
                throw new IndexShardException(shardId, "exception during checkindex", e);
            } finally {
                store.decRef();
            }
        }
    }

    private void doCheckIndex() throws IndexShardException, IOException {
        long timeNS = System.nanoTime();
        if (!Lucene.indexExists(store.directory())) {
            return;
        }
        BytesStreamOutput os = new BytesStreamOutput();
        PrintStream out = new PrintStream(os, false, Charsets.UTF_8.name());

        if ("checksum".equalsIgnoreCase(checkIndexOnStartup)) {
            // physical verification only: verify all checksums for the latest commit
            boolean corrupt = false;
            MetadataSnapshot metadata = store.getMetadata();
            for (Map.Entry<String, StoreFileMetaData> entry : metadata.asMap().entrySet()) {
                try {
                    Store.checkIntegrity(entry.getValue(), store.directory());
                    out.println("checksum passed: " + entry.getKey());
                } catch (IOException exc) {
                    out.println("checksum failed: " + entry.getKey());
                    exc.printStackTrace(out);
                    corrupt = true;
                }
            }
            out.flush();
            if (corrupt) {
                logger.warn("check index [failure]\n{}", new String(os.bytes().toBytes(), Charsets.UTF_8));
                throw new IndexShardException(shardId, "index check failure");
            }
        } else {
            // full checkindex
            try (CheckIndex checkIndex = new CheckIndex(store.directory())) {
                checkIndex.setInfoStream(out);
                CheckIndex.Status status = checkIndex.checkIndex();
                out.flush();

                if (!status.clean) {
                    if (state == IndexShardState.CLOSED) {
                        // ignore if closed....
                        return;
                    }
                    logger.warn("check index [failure]\n{}", new String(os.bytes().toBytes(), Charsets.UTF_8));
                    if ("fix".equalsIgnoreCase(checkIndexOnStartup)) {
                        if (logger.isDebugEnabled()) {
                            logger.debug("fixing index, writing new segments file ...");
                        }
                        checkIndex.exorciseIndex(status);
                        if (logger.isDebugEnabled()) {
                            logger.debug("index fixed, wrote new segments file \"{}\"", status.segmentsFileName);
                        }
                    } else {
                        // only throw a failure if we are not going to fix the index
                        throw new IndexShardException(shardId, "index check failure");
                    }
                }
            }
        }

        if (logger.isDebugEnabled()) {
            logger.debug("check index [success]\n{}", new String(os.bytes().toBytes(), Charsets.UTF_8));
        }

        recoveryState.getVerifyIndex().checkIndexTime(Math.max(0, TimeValue.nsecToMSec(System.nanoTime() - timeNS)));
    }

    public Engine engine() {
        Engine engine = engineUnsafe();
        if (engine == null) {
            throw new EngineClosedException(shardId);
        }
        return engine;
    }

    protected Engine engineUnsafe() {
        return this.currentEngineReference.get();
    }

    class ShardEngineFailListener implements Engine.FailedEngineListener {
        private final CopyOnWriteArrayList<Engine.FailedEngineListener> delegates = new CopyOnWriteArrayList<>();

        // called by the current engine
        @Override
        public void onFailedEngine(ShardId shardId, String reason, @Nullable Throwable failure) {
            try {
                // delete the shard state so this folder will not be reused
                MetaDataStateFormat.deleteMetaState(nodeEnv.availableShardPaths(shardId));
            } catch (IOException e) {
                logger.warn("failed to delete shard state", e);
            } finally {
                for (Engine.FailedEngineListener listener : delegates) {
                    try {
                        listener.onFailedEngine(shardId, reason, failure);
                    } catch (Exception e) {
                        logger.warn("exception while notifying engine failure", e);
                    }
                }
            }
        }
    }

    private void createNewEngine(boolean skipTranslogRecovery, EngineConfig config) {
        synchronized (mutex) {
            if (state == IndexShardState.CLOSED) {
                throw new EngineClosedException(shardId);
            }
            assert this.currentEngineReference.get() == null;
            this.currentEngineReference.set(newEngine(skipTranslogRecovery, config));
        }
    }

    protected Engine newEngine(boolean skipTranslogRecovery, EngineConfig config) {
        return engineFactory.newReadWriteEngine(config, skipTranslogRecovery);
    }

    /**
     * Returns <code>true</code> iff this shard allows primary promotion, otherwise <code>false</code>
     */
    public boolean allowsPrimaryPromotion() {
        return true;
    }

    // pkg private for testing
    void persistMetadata(ShardRouting newRouting, ShardRouting currentRouting) {
        assert newRouting != null : "newRouting must not be null";
        if (newRouting.active()) {
            try {
                final String writeReason;
                if (currentRouting == null) {
                    writeReason = "freshly started, version [" + newRouting.version() + "]";
                } else if (currentRouting.version() < newRouting.version()) {
                    writeReason = "version changed from [" + currentRouting.version() + "] to [" + newRouting.version() + "]";
                } else if (currentRouting.equals(newRouting) == false) {
                    writeReason = "routing changed from " + currentRouting + " to " + newRouting;
                } else {
                    logger.trace("skip writing shard state, has been written before; previous version:  [" +
                            currentRouting.version() + "] current version [" + newRouting.version() + "]");
                    assert currentRouting.version() <= newRouting.version() : "version should not go backwards for shardID: " + shardId +
                            " previous version:  [" + currentRouting.version() + "] current version [" + newRouting.version() + "]";
                    return;
                }
                final ShardStateMetaData newShardStateMetadata = new ShardStateMetaData(newRouting.version(), newRouting.primary(), getIndexUUID());
                logger.trace("{} writing shard state, reason [{}]", shardId, writeReason);
                ShardStateMetaData.FORMAT.write(newShardStateMetadata, newShardStateMetadata.version, shardPath().getShardStatePath());
            } catch (IOException e) { // this is how we used to handle it.... :(
                logger.warn("failed to write shard state", e);
                // we failed to write the shard state, we will try and write
                // it next time...
            }
        }
    }

    private String getIndexUUID() {
        assert indexSettings.get(IndexMetaData.SETTING_UUID) != null
                || indexSettings.getAsVersion(IndexMetaData.SETTING_VERSION_CREATED, Version.CURRENT).before(Version.V_0_90_6) :
                "version: " + indexSettings.getAsVersion(IndexMetaData.SETTING_VERSION_CREATED, null) + " uuid: " + indexSettings.get(IndexMetaData.SETTING_UUID);
        return indexSettings.get(IndexMetaData.SETTING_UUID, IndexMetaData.INDEX_UUID_NA_VALUE);
    }

    private Tuple<DocumentMapper, Mapping> docMapper(String type) {
        return mapperService.documentMapperWithAutoCreate(type);
    }

    private final EngineConfig newEngineConfig(TranslogConfig translogConfig) {
        final TranslogRecoveryPerformer translogRecoveryPerformer = new TranslogRecoveryPerformer(shardId, mapperService, mapperAnalyzer, queryParserService, indexAliasesService, indexCache) {
            @Override
            protected void operationProcessed() {
                assert recoveryState != null;
                recoveryState.getTranslog().incrementRecoveredOperations();
            }
        };
        return new EngineConfig(shardId,
                threadPool, indexingService, indexSettingsService, warmer, store, deletionPolicy, mergePolicyProvider, mergeScheduler,
                mapperAnalyzer, similarityService.similarity(), codecService, failedEngineListener, translogRecoveryPerformer, indexCache.filter(), indexCache.filterPolicy(), translogConfig);
    }

    private static class IndexShardOperationCounter extends AbstractRefCounted {
        final private ESLogger logger;
        private final ShardId shardId;

        public IndexShardOperationCounter(ESLogger logger, ShardId shardId) {
            super("index-shard-operations-counter");
            this.logger = logger;
            this.shardId = shardId;
        }

        @Override
        protected void closeInternal() {
            logger.debug("operations counter reached 0, will not accept any further writes");
        }

        @Override
        protected void alreadyClosed() {
            throw new IndexShardClosedException(shardId, "could not increment operation counter. shard is closed.");
        }
    }

    public void incrementOperationCounter() {
        indexShardOperationCounter.incRef();
    }

    public void decrementOperationCounter() {
        indexShardOperationCounter.decRef();
    }

    public int getOperationsCount() {
        return Math.max(0, indexShardOperationCounter.refCount() - 1); // refCount is incremented on creation and decremented on close
    }

    /**
     * Syncs the given location with the underlying storage unless already synced.
     */
    public void sync(Translog.Location location) {
        final Engine engine = engine();
        try {
            engine.getTranslog().ensureSynced(location);
        } catch (IOException ex) { // if this fails we are in deep shit - fail the request
            logger.debug("failed to sync translog", ex);
            throw new ElasticsearchException("failed to sync translog", ex);
        }
    }

    /**
     * Returns the current translog durability mode
     */
    public Translog.Durabilty getTranslogDurability() {
        return translogConfig.getDurabilty();
    }

    private static Translog.Durabilty getFromSettings(ESLogger logger, Settings settings, Translog.Durabilty defaultValue) {
        final String value = settings.get(TranslogConfig.INDEX_TRANSLOG_DURABILITY, defaultValue.name());
        try {
            return Translog.Durabilty.valueOf(value.toUpperCase(Locale.ROOT));
        } catch (IllegalArgumentException ex) {
            logger.warn("Can't apply {} illegal value: {} using {} instead, use one of: {}", TranslogConfig.INDEX_TRANSLOG_DURABILITY, value, defaultValue, Arrays.toString(Translog.Durabilty.values()));
            return defaultValue;
        }
    }

}


File: core/src/main/java/org/elasticsearch/index/shard/ShadowIndexShard.java
/*
 * Licensed to Elasticsearch under one or more contributor
 * license agreements. See the NOTICE file distributed with
 * this work for additional information regarding copyright
 * ownership. Elasticsearch licenses this file to you under
 * the Apache License, Version 2.0 (the "License"); you may
 * not use this file except in compliance with the License.
 * You may obtain a copy of the License at
 *
 *    http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing,
 * software distributed under the License is distributed on an
 * "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY
 * KIND, either express or implied.  See the License for the
 * specific language governing permissions and limitations
 * under the License.
 */
package org.elasticsearch.index.shard;

import org.elasticsearch.cluster.ClusterService;
import org.elasticsearch.cluster.routing.ShardRouting;
import org.elasticsearch.common.Nullable;
import org.elasticsearch.common.inject.Inject;
import org.elasticsearch.common.util.BigArrays;
import org.elasticsearch.env.NodeEnvironment;
import org.elasticsearch.index.IndexService;
import org.elasticsearch.index.aliases.IndexAliasesService;
import org.elasticsearch.index.cache.IndexCache;
import org.elasticsearch.index.cache.bitset.ShardBitsetFilterCache;
import org.elasticsearch.index.cache.filter.ShardFilterCache;
import org.elasticsearch.index.cache.query.ShardQueryCache;
import org.elasticsearch.index.codec.CodecService;
import org.elasticsearch.index.deletionpolicy.SnapshotDeletionPolicy;
import org.elasticsearch.index.engine.Engine;
import org.elasticsearch.index.engine.EngineConfig;
import org.elasticsearch.index.engine.EngineFactory;
import org.elasticsearch.index.fielddata.IndexFieldDataService;
import org.elasticsearch.index.fielddata.ShardFieldData;
import org.elasticsearch.index.get.ShardGetService;
import org.elasticsearch.index.indexing.ShardIndexingService;
import org.elasticsearch.index.mapper.MapperService;
import org.elasticsearch.index.merge.policy.MergePolicyProvider;
import org.elasticsearch.index.merge.scheduler.MergeSchedulerProvider;
import org.elasticsearch.index.percolator.PercolatorQueriesRegistry;
import org.elasticsearch.index.percolator.stats.ShardPercolateService;
import org.elasticsearch.index.query.IndexQueryParserService;
import org.elasticsearch.index.search.stats.ShardSearchService;
import org.elasticsearch.index.settings.IndexSettingsService;
import org.elasticsearch.index.similarity.SimilarityService;
import org.elasticsearch.index.store.Store;
import org.elasticsearch.index.suggest.stats.ShardSuggestService;
import org.elasticsearch.index.termvectors.ShardTermVectorsService;
import org.elasticsearch.index.translog.Translog;
import org.elasticsearch.index.warmer.ShardIndexWarmerService;
import org.elasticsearch.indices.IndicesLifecycle;
import org.elasticsearch.indices.IndicesWarmer;
import org.elasticsearch.threadpool.ThreadPool;

import java.io.IOException;

/**
 * ShadowIndexShard extends {@link IndexShard} to add file synchronization
 * from the primary when a flush happens. It also ensures that a replica being
 * promoted to a primary causes the shard to fail, kicking off a re-allocation
 * of the primary shard.
 */
public final class ShadowIndexShard extends IndexShard {

    @Inject
    public ShadowIndexShard(ShardId shardId, IndexSettingsService indexSettingsService,
                            IndicesLifecycle indicesLifecycle, Store store, MergeSchedulerProvider mergeScheduler,
                            ThreadPool threadPool, MapperService mapperService,
                            IndexQueryParserService queryParserService, IndexCache indexCache,
                            IndexAliasesService indexAliasesService, ShardIndexingService indexingService,
                            ShardGetService getService, ShardSearchService searchService,
                            ShardIndexWarmerService shardWarmerService, ShardFilterCache shardFilterCache,
                            ShardFieldData shardFieldData, PercolatorQueriesRegistry percolatorQueriesRegistry,
                            ShardPercolateService shardPercolateService, CodecService codecService,
                            ShardTermVectorsService termVectorsService, IndexFieldDataService indexFieldDataService,
                            IndexService indexService, ShardSuggestService shardSuggestService, ShardQueryCache shardQueryCache,
                            ShardBitsetFilterCache shardBitsetFilterCache, @Nullable IndicesWarmer warmer,
                            SnapshotDeletionPolicy deletionPolicy, SimilarityService similarityService,
                            MergePolicyProvider mergePolicyProvider, EngineFactory factory, ClusterService clusterService,
                            NodeEnvironment nodeEnv, ShardPath path, BigArrays bigArrays) throws IOException {
        super(shardId, indexSettingsService, indicesLifecycle, store, mergeScheduler,
                threadPool, mapperService, queryParserService, indexCache, indexAliasesService,
                indexingService, getService, searchService, shardWarmerService, shardFilterCache,
                shardFieldData, percolatorQueriesRegistry, shardPercolateService, codecService,
                termVectorsService, indexFieldDataService, indexService, shardSuggestService,
                shardQueryCache, shardBitsetFilterCache, warmer, deletionPolicy, similarityService,
                mergePolicyProvider, factory, clusterService, nodeEnv, path, bigArrays);
    }

    /**
     * In addition to the regular accounting done in
     * {@link IndexShard#updateRoutingEntry(org.elasticsearch.cluster.routing.ShardRouting, boolean)},
     * if this shadow replica needs to be promoted to a primary, the shard is
     * failed in order to allow a new primary to be re-allocated.
     */
    @Override
    public void updateRoutingEntry(ShardRouting newRouting, boolean persistState) {
        if (newRouting.primary() == true) {// becoming a primary
            throw new IllegalStateException("can't promote shard to primary");
        }
        super.updateRoutingEntry(newRouting, persistState);
    }

    @Override
    public boolean canIndex() {
        return false;
    }

    @Override
    protected Engine newEngine(boolean skipInitialTranslogRecovery, EngineConfig config) {
        assert this.shardRouting.primary() == false;
        assert skipInitialTranslogRecovery : "can not recover from gateway";
        return engineFactory.newReadOnlyEngine(config);
    }

    public boolean allowsPrimaryPromotion() {
        return false;
    }
}


File: core/src/test/java/org/elasticsearch/bwcompat/OldIndexBackwardsCompatibilityTests.java
/*
 * Licensed to Elasticsearch under one or more contributor
 * license agreements. See the NOTICE file distributed with
 * this work for additional information regarding copyright
 * ownership. Elasticsearch licenses this file to you under
 * the Apache License, Version 2.0 (the "License"); you may
 * not use this file except in compliance with the License.
 * You may obtain a copy of the License at
 *
 *    http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing,
 * software distributed under the License is distributed on an
 * "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY
 * KIND, either express or implied.  See the License for the
 * specific language governing permissions and limitations
 * under the License.
 */

package org.elasticsearch.bwcompat;

import com.google.common.base.Predicate;
import com.google.common.util.concurrent.ListenableFuture;
import org.apache.lucene.index.IndexWriter;
import org.apache.lucene.util.LuceneTestCase;
import org.apache.lucene.util.TestUtil;
import org.elasticsearch.Version;
import org.elasticsearch.action.admin.indices.get.GetIndexResponse;
import org.elasticsearch.action.get.GetResponse;
import org.elasticsearch.action.search.SearchRequestBuilder;
import org.elasticsearch.action.search.SearchResponse;
import org.elasticsearch.cluster.ClusterState;
import org.elasticsearch.cluster.metadata.IndexMetaData;
import org.elasticsearch.common.io.FileSystemUtils;
import org.elasticsearch.common.logging.ESLogger;
import org.elasticsearch.common.settings.Settings;
import org.elasticsearch.common.unit.TimeValue;
import org.elasticsearch.common.util.MultiDataPathUpgrader;
import org.elasticsearch.common.xcontent.XContentHelper;
import org.elasticsearch.env.NodeEnvironment;
import org.elasticsearch.index.IndexException;
import org.elasticsearch.index.engine.EngineConfig;
import org.elasticsearch.index.merge.policy.MergePolicyModule;
import org.elasticsearch.index.query.QueryBuilders;
import org.elasticsearch.indices.recovery.RecoverySettings;
import org.elasticsearch.node.Node;
import org.elasticsearch.rest.action.admin.indices.upgrade.UpgradeTest;
import org.elasticsearch.search.SearchHit;
import org.elasticsearch.search.aggregations.AggregationBuilders;
import org.elasticsearch.search.aggregations.bucket.histogram.Histogram;
import org.elasticsearch.search.aggregations.bucket.terms.Terms;
import org.elasticsearch.search.sort.SortOrder;
import org.elasticsearch.test.ElasticsearchIntegrationTest;
import org.elasticsearch.test.VersionUtils;
import org.elasticsearch.test.hamcrest.ElasticsearchAssertions;
import org.elasticsearch.test.index.merge.NoMergePolicyProvider;
import org.hamcrest.Matchers;
import org.junit.AfterClass;
import org.junit.Before;
import org.junit.Test;

import java.io.IOException;
import java.io.InputStream;
import java.nio.file.*;
import java.nio.file.attribute.BasicFileAttributes;
import java.util.*;

import static org.elasticsearch.test.hamcrest.ElasticsearchAssertions.assertAcked;
import static org.elasticsearch.test.hamcrest.ElasticsearchAssertions.assertNoFailures;
import static org.hamcrest.CoreMatchers.containsString;
import static org.hamcrest.Matchers.greaterThanOrEqualTo;

// needs at least 2 nodes since it bumps replicas to 1
@ElasticsearchIntegrationTest.ClusterScope(scope = ElasticsearchIntegrationTest.Scope.TEST, numDataNodes = 0)
@LuceneTestCase.SuppressFileSystems("ExtrasFS")
@LuceneTestCase.Slow
public class OldIndexBackwardsCompatibilityTests extends ElasticsearchIntegrationTest {
    // TODO: test for proper exception on unsupported indexes (maybe via separate test?)
    // We have a 0.20.6.zip etc for this.

    List<String> indexes;
    List<String> unsupportedIndexes;
    static Path singleDataPath;
    static Path[] multiDataPath;

    @Before
    public void initIndexesList() throws Exception {
        indexes = loadIndexesList("index");
        unsupportedIndexes = loadIndexesList("unsupported");
    }

    private List<String> loadIndexesList(String prefix) throws IOException {
        List<String> indexes = new ArrayList<>();
        Path dir = getDataPath(".");
        try (DirectoryStream<Path> stream = Files.newDirectoryStream(dir, prefix + "-*.zip")) {
            for (Path path : stream) {
                indexes.add(path.getFileName().toString());
            }
        }
        Collections.sort(indexes);
        return indexes;
    }

    @AfterClass
    public static void tearDownStatics() {
        singleDataPath = null;
        multiDataPath = null;
    }

    @Override
    public Settings nodeSettings(int ord) {
        return Settings.builder()
                .put(MergePolicyModule.MERGE_POLICY_TYPE_KEY, NoMergePolicyProvider.class) // disable merging so no segments will be upgraded
                .put(RecoverySettings.INDICES_RECOVERY_CONCURRENT_SMALL_FILE_STREAMS, 30) // increase recovery speed for small files
                .build();
    }

    void setupCluster() throws Exception {
        ListenableFuture<List<String>> replicas = internalCluster().startNodesAsync(1); // for replicas

        Path baseTempDir = createTempDir();
        // start single data path node
        Settings.Builder nodeSettings = Settings.builder()
            .put("path.data", baseTempDir.resolve("single-path").toAbsolutePath())
            .put("node.master", false); // workaround for dangling index loading issue when node is master
        ListenableFuture<String> singleDataPathNode = internalCluster().startNodeAsync(nodeSettings.build());

        // start multi data path node
        nodeSettings = Settings.builder()
            .put("path.data", baseTempDir.resolve("multi-path1").toAbsolutePath() + "," + baseTempDir.resolve("multi-path2").toAbsolutePath())
            .put("node.master", false); // workaround for dangling index loading issue when node is master
        ListenableFuture<String> multiDataPathNode = internalCluster().startNodeAsync(nodeSettings.build());

        // find single data path dir
        Path[] nodePaths = internalCluster().getInstance(NodeEnvironment.class, singleDataPathNode.get()).nodeDataPaths();
        assertEquals(1, nodePaths.length);
        singleDataPath = nodePaths[0].resolve(NodeEnvironment.INDICES_FOLDER);
        assertFalse(Files.exists(singleDataPath));
        Files.createDirectories(singleDataPath);
        logger.info("--> Single data path: " + singleDataPath.toString());

        // find multi data path dirs
        nodePaths = internalCluster().getInstance(NodeEnvironment.class, multiDataPathNode.get()).nodeDataPaths();
        assertEquals(2, nodePaths.length);
        multiDataPath = new Path[] {nodePaths[0].resolve(NodeEnvironment.INDICES_FOLDER),
                                   nodePaths[1].resolve(NodeEnvironment.INDICES_FOLDER)};
        assertFalse(Files.exists(multiDataPath[0]));
        assertFalse(Files.exists(multiDataPath[1]));
        Files.createDirectories(multiDataPath[0]);
        Files.createDirectories(multiDataPath[1]);
        logger.info("--> Multi data paths: " + multiDataPath[0].toString() + ", " + multiDataPath[1].toString());

        replicas.get(); // wait for replicas
    }

    String loadIndex(String indexFile) throws Exception {
        Path unzipDir = createTempDir();
        Path unzipDataDir = unzipDir.resolve("data");
        String indexName = indexFile.replace(".zip", "").toLowerCase(Locale.ROOT).replace("unsupported-", "index-");

        // decompress the index
        Path backwardsIndex = getDataPath(indexFile);
        try (InputStream stream = Files.newInputStream(backwardsIndex)) {
            TestUtil.unzip(stream, unzipDir);
        }

        // check it is unique
        assertTrue(Files.exists(unzipDataDir));
        Path[] list = FileSystemUtils.files(unzipDataDir);
        if (list.length != 1) {
            throw new IllegalStateException("Backwards index must contain exactly one cluster");
        }

        // the bwc scripts packs the indices under this path
        Path src = list[0].resolve("nodes/0/indices/" + indexName);
        assertTrue("[" + indexFile + "] missing index dir: " + src.toString(), Files.exists(src));

        if (randomBoolean()) {
            logger.info("--> injecting index [{}] into single data path", indexName);
            copyIndex(logger, src, indexName, singleDataPath);
        } else {
            logger.info("--> injecting index [{}] into multi data path", indexName);
            copyIndex(logger, src, indexName, multiDataPath);
        }
        return indexName;
    }

    void importIndex(String indexName) throws IOException {
        final Iterable<NodeEnvironment> instances = internalCluster().getInstances(NodeEnvironment.class);
        for (NodeEnvironment nodeEnv : instances) { // upgrade multidata path
            MultiDataPathUpgrader.upgradeMultiDataPath(nodeEnv, logger);
        }
        // force reloading dangling indices with a cluster state republish
        client().admin().cluster().prepareReroute().get();
        ensureGreen(indexName);
    }

    // randomly distribute the files from src over dests paths
    public static void copyIndex(final ESLogger logger, final Path src, final String indexName, final Path... dests) throws IOException {
        for (Path dest : dests) {
            Path indexDir = dest.resolve(indexName);
            assertFalse(Files.exists(indexDir));
            Files.createDirectories(indexDir);
        }
        Files.walkFileTree(src, new SimpleFileVisitor<Path>() {
            @Override
            public FileVisitResult preVisitDirectory(Path dir, BasicFileAttributes attrs) throws IOException {
                Path relativeDir = src.relativize(dir);
                for (Path dest : dests) {
                    Path destDir = dest.resolve(indexName).resolve(relativeDir);
                    Files.createDirectories(destDir);
                }
                return FileVisitResult.CONTINUE;
            }

            @Override
            public FileVisitResult visitFile(Path file, BasicFileAttributes attrs) throws IOException {
                if (file.getFileName().toString().equals(IndexWriter.WRITE_LOCK_NAME)) {
                    // skip lock file, we don't need it
                    logger.trace("Skipping lock file: " + file.toString());
                    return FileVisitResult.CONTINUE;
                }

                Path relativeFile = src.relativize(file);
                Path destFile = dests[randomInt(dests.length - 1)].resolve(indexName).resolve(relativeFile);
                logger.trace("--> Moving " + relativeFile.toString() + " to " + destFile.toString());
                Files.move(file, destFile);
                assertFalse(Files.exists(file));
                assertTrue(Files.exists(destFile));
                return FileVisitResult.CONTINUE;
            }
        });
    }

    void unloadIndex(String indexName) throws Exception {
        assertAcked(client().admin().indices().prepareDelete(indexName).get());
    }

    public void testAllVersionsTested() throws Exception {
        SortedSet<String> expectedVersions = new TreeSet<>();
        for (Version v : VersionUtils.allVersions()) {
            if (v.snapshot()) continue;  // snapshots are unreleased, so there is no backcompat yet
            if (v.onOrBefore(Version.V_0_20_6)) continue; // we can only test back one major lucene version
            if (v.equals(Version.CURRENT)) continue; // the current version is always compatible with itself
            expectedVersions.add("index-" + v.toString() + ".zip");
        }

        for (String index : indexes) {
            if (expectedVersions.remove(index) == false) {
                logger.warn("Old indexes tests contain extra index: " + index);
            }
        }
        if (expectedVersions.isEmpty() == false) {
            StringBuilder msg = new StringBuilder("Old index tests are missing indexes:");
            for (String expected : expectedVersions) {
                msg.append("\n" + expected);
            }
            fail(msg.toString());
        }
    }

    public void testOldIndexes() throws Exception {
        setupCluster();

        Collections.shuffle(indexes, getRandom());
        for (String index : indexes) {
            long startTime = System.currentTimeMillis();
            logger.info("--> Testing old index " + index);
            assertOldIndexWorks(index);
            logger.info("--> Done testing " + index + ", took " + ((System.currentTimeMillis() - startTime) / 1000.0) + " seconds");
        }
    }

    @Test
    public void testHandlingOfUnsupportedDanglingIndexes() throws Exception {
        setupCluster();
        Collections.shuffle(unsupportedIndexes, getRandom());
        for (String index : unsupportedIndexes) {
            assertUnsupportedIndexHandling(index);
        }
    }

    /**
     * Waits for the index to show up in the cluster state in closed state
     */
    void ensureClosed(final String index) throws InterruptedException {
        assertTrue(awaitBusy(new Predicate<Object>() {
            @Override
            public boolean apply(Object o) {
                ClusterState state = client().admin().cluster().prepareState().get().getState();
                return state.metaData().hasIndex(index) && state.metaData().index(index).getState() == IndexMetaData.State.CLOSE;
            }
        }));
    }

    /**
     * Checks that the given index cannot be opened due to incompatible version
     */
    void assertUnsupportedIndexHandling(String index) throws Exception {
        long startTime = System.currentTimeMillis();
        logger.info("--> Testing old index " + index);
        String indexName = loadIndex(index);
        // force reloading dangling indices with a cluster state republish
        client().admin().cluster().prepareReroute().get();
        ensureClosed(indexName);
        try {
            client().admin().indices().prepareOpen(indexName).get();
            fail("Shouldn't be able to open an old index");
        } catch (IndexException ex) {
            assertThat(ex.getMessage(), containsString("cannot open the index due to upgrade failure"));
        }
        unloadIndex(indexName);
        logger.info("--> Done testing " + index + ", took " + ((System.currentTimeMillis() - startTime) / 1000.0) + " seconds");
    }

    void assertOldIndexWorks(String index) throws Exception {
        Version version = extractVersion(index);
        String indexName = loadIndex(index);
        importIndex(indexName);
        assertIndexSanity(indexName);
        assertBasicSearchWorks(indexName);
        assertBasicAggregationWorks(indexName);
        assertRealtimeGetWorks(indexName);
        assertNewReplicasWork(indexName);
        assertUpgradeWorks(indexName, isLatestLuceneVersion(version));
        assertDeleteByQueryWorked(indexName, version);
        unloadIndex(indexName);
    }

    Version extractVersion(String index) {
        return Version.fromString(index.substring(index.indexOf('-') + 1, index.lastIndexOf('.')));
    }

    boolean isLatestLuceneVersion(Version version) {
        return version.luceneVersion.major == Version.CURRENT.luceneVersion.major &&
                version.luceneVersion.minor == Version.CURRENT.luceneVersion.minor;
    }

    void assertIndexSanity(String indexName) {
        GetIndexResponse getIndexResponse = client().admin().indices().prepareGetIndex().addIndices(indexName).get();
        assertEquals(1, getIndexResponse.indices().length);
        assertEquals(indexName, getIndexResponse.indices()[0]);
        ensureYellow(indexName);
        SearchResponse test = client().prepareSearch(indexName).get();
        assertThat(test.getHits().getTotalHits(), greaterThanOrEqualTo(1l));
    }

    void assertBasicSearchWorks(String indexName) {
        logger.info("--> testing basic search");
        SearchRequestBuilder searchReq = client().prepareSearch(indexName).setQuery(QueryBuilders.matchAllQuery());
        SearchResponse searchRsp = searchReq.get();
        ElasticsearchAssertions.assertNoFailures(searchRsp);
        long numDocs = searchRsp.getHits().getTotalHits();
        logger.info("Found " + numDocs + " in old index");

        logger.info("--> testing basic search with sort");
        searchReq.addSort("long_sort", SortOrder.ASC);
        ElasticsearchAssertions.assertNoFailures(searchReq.get());

        logger.info("--> testing exists filter");
        searchReq = client().prepareSearch(indexName).setQuery(QueryBuilders.existsQuery("string"));
        searchRsp = searchReq.get();
        ElasticsearchAssertions.assertNoFailures(searchRsp);
        assertEquals(numDocs, searchRsp.getHits().getTotalHits());

        logger.info("--> testing missing filter");
        // the field for the missing filter here needs to be different than the exists filter above, to avoid being found in the cache
        searchReq = client().prepareSearch(indexName).setQuery(QueryBuilders.missingQuery("long_sort"));
        searchRsp = searchReq.get();
        ElasticsearchAssertions.assertNoFailures(searchRsp);
        assertEquals(0, searchRsp.getHits().getTotalHits());
    }

    void assertBasicAggregationWorks(String indexName) {
        // histogram on a long
        SearchResponse searchRsp = client().prepareSearch(indexName).addAggregation(AggregationBuilders.histogram("histo").field("long_sort").interval(10)).get();
        ElasticsearchAssertions.assertSearchResponse(searchRsp);
        Histogram histo = searchRsp.getAggregations().get("histo");
        assertNotNull(histo);
        long totalCount = 0;
        for (Histogram.Bucket bucket : histo.getBuckets()) {
            totalCount += bucket.getDocCount();
        }
        assertEquals(totalCount, searchRsp.getHits().getTotalHits());

        // terms on a boolean
        searchRsp = client().prepareSearch(indexName).addAggregation(AggregationBuilders.terms("bool_terms").field("bool")).get();
        Terms terms = searchRsp.getAggregations().get("bool_terms");
        totalCount = 0;
        for (Terms.Bucket bucket : terms.getBuckets()) {
            totalCount += bucket.getDocCount();
        }
        assertEquals(totalCount, searchRsp.getHits().getTotalHits());
    }

    void assertRealtimeGetWorks(String indexName) {
        assertAcked(client().admin().indices().prepareUpdateSettings(indexName).setSettings(Settings.builder()
                .put("refresh_interval", -1)
                .build()));
        SearchRequestBuilder searchReq = client().prepareSearch(indexName).setQuery(QueryBuilders.matchAllQuery());
        SearchHit hit = searchReq.get().getHits().getAt(0);
        String docId = hit.getId();
        // foo is new, it is not a field in the generated index
        client().prepareUpdate(indexName, "doc", docId).setDoc("foo", "bar").get();
        GetResponse getRsp = client().prepareGet(indexName, "doc", docId).get();
        Map<String, Object> source = getRsp.getSourceAsMap();
        assertThat(source, Matchers.hasKey("foo"));

        assertAcked(client().admin().indices().prepareUpdateSettings(indexName).setSettings(Settings.builder()
                .put("refresh_interval", EngineConfig.DEFAULT_REFRESH_INTERVAL)
                .build()));
    }

    void assertNewReplicasWork(String indexName) throws Exception {
        final int numReplicas = 1;
        final long startTime = System.currentTimeMillis();
        logger.debug("--> creating [{}] replicas for index [{}]", numReplicas, indexName);
        assertAcked(client().admin().indices().prepareUpdateSettings(indexName).setSettings(Settings.builder()
                        .put("number_of_replicas", numReplicas)
        ).execute().actionGet());
        ensureGreen(TimeValue.timeValueMinutes(2), indexName);
        logger.debug("--> index [{}] is green, took [{}]", indexName, TimeValue.timeValueMillis(System.currentTimeMillis() - startTime));
        logger.debug("--> recovery status:\n{}", XContentHelper.toString(client().admin().indices().prepareRecoveries(indexName).get()));

        // TODO: do something with the replicas! query? index?
    }

    // #10067: create-bwc-index.py deleted any doc with long_sort:[10-20]
    void assertDeleteByQueryWorked(String indexName, Version version) throws Exception {
        if (version.onOrBefore(Version.V_1_0_0_Beta2)) {
            // TODO: remove this once #10262 is fixed
            return;
        }
        // these documents are supposed to be deleted by a delete by query operation in the translog
        SearchRequestBuilder searchReq = client().prepareSearch(indexName).setQuery(QueryBuilders.queryStringQuery("long_sort:[10 TO 20]"));
        assertEquals(0, searchReq.get().getHits().getTotalHits());
    }

    void assertUpgradeWorks(String indexName, boolean alreadyLatest) throws Exception {
        if (alreadyLatest == false) {
            UpgradeTest.assertNotUpgraded(client(), indexName);
        }
        assertNoFailures(client().admin().indices().prepareUpgrade(indexName).get());
        UpgradeTest.assertUpgraded(client(), indexName);
    }

}


File: core/src/test/java/org/elasticsearch/common/lucene/uid/VersionsTests.java
/*
 * Licensed to Elasticsearch under one or more contributor
 * license agreements. See the NOTICE file distributed with
 * this work for additional information regarding copyright
 * ownership. Elasticsearch licenses this file to you under
 * the Apache License, Version 2.0 (the "License"); you may
 * not use this file except in compliance with the License.
 * You may obtain a copy of the License at
 *
 *    http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing,
 * software distributed under the License is distributed on an
 * "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY
 * KIND, either express or implied.  See the License for the
 * specific language governing permissions and limitations
 * under the License.
 */
package org.elasticsearch.common.lucene.uid;

import com.google.common.collect.ImmutableMap;

import org.apache.lucene.analysis.Analyzer;
import org.apache.lucene.analysis.TokenStream;
import org.apache.lucene.analysis.core.KeywordAnalyzer;
import org.apache.lucene.analysis.tokenattributes.CharTermAttribute;
import org.apache.lucene.analysis.tokenattributes.PayloadAttribute;
import org.apache.lucene.document.*;
import org.apache.lucene.document.Field.Store;
import org.apache.lucene.index.*;
import org.apache.lucene.store.Directory;
import org.apache.lucene.util.BytesRef;
import org.elasticsearch.common.Numbers;
import org.elasticsearch.common.lucene.Lucene;
import org.elasticsearch.index.mapper.internal.UidFieldMapper;
import org.elasticsearch.index.mapper.internal.VersionFieldMapper;
import org.elasticsearch.index.merge.policy.ElasticsearchMergePolicy;
import org.elasticsearch.test.ElasticsearchTestCase;
import org.hamcrest.MatcherAssert;
import org.junit.Test;

import java.io.IOException;
import java.util.ArrayList;
import java.util.List;
import java.util.Map;

import static org.hamcrest.Matchers.*;

public class VersionsTests extends ElasticsearchTestCase {
    
    public static DirectoryReader reopen(DirectoryReader reader) throws IOException {
        return reopen(reader, true);
    }

    public static DirectoryReader reopen(DirectoryReader reader, boolean newReaderExpected) throws IOException {
        DirectoryReader newReader = DirectoryReader.openIfChanged(reader);
        if (newReader != null) {
            reader.close();
        } else {
            assertFalse(newReaderExpected);
        }
        return newReader;
    }
    @Test
    public void testVersions() throws Exception {
        Directory dir = newDirectory();
        IndexWriter writer = new IndexWriter(dir, new IndexWriterConfig(Lucene.STANDARD_ANALYZER));
        DirectoryReader directoryReader = DirectoryReader.open(writer, true);
        MatcherAssert.assertThat(Versions.loadVersion(directoryReader, new Term(UidFieldMapper.NAME, "1")), equalTo(Versions.NOT_FOUND));

        Document doc = new Document();
        doc.add(new Field(UidFieldMapper.NAME, "1", UidFieldMapper.Defaults.FIELD_TYPE));
        writer.addDocument(doc);
        directoryReader = reopen(directoryReader);
        assertThat(Versions.loadVersion(directoryReader, new Term(UidFieldMapper.NAME, "1")), equalTo(Versions.NOT_SET));
        assertThat(Versions.loadDocIdAndVersion(directoryReader, new Term(UidFieldMapper.NAME, "1")).version, equalTo(Versions.NOT_SET));

        doc = new Document();
        doc.add(new Field(UidFieldMapper.NAME, "1", UidFieldMapper.Defaults.FIELD_TYPE));
        doc.add(new NumericDocValuesField(VersionFieldMapper.NAME, 1));
        writer.updateDocument(new Term(UidFieldMapper.NAME, "1"), doc);
        directoryReader = reopen(directoryReader);
        assertThat(Versions.loadVersion(directoryReader, new Term(UidFieldMapper.NAME, "1")), equalTo(1l));
        assertThat(Versions.loadDocIdAndVersion(directoryReader, new Term(UidFieldMapper.NAME, "1")).version, equalTo(1l));

        doc = new Document();
        Field uid = new Field(UidFieldMapper.NAME, "1", UidFieldMapper.Defaults.FIELD_TYPE);
        Field version = new NumericDocValuesField(VersionFieldMapper.NAME, 2);
        doc.add(uid);
        doc.add(version);
        writer.updateDocument(new Term(UidFieldMapper.NAME, "1"), doc);
        directoryReader = reopen(directoryReader);
        assertThat(Versions.loadVersion(directoryReader, new Term(UidFieldMapper.NAME, "1")), equalTo(2l));
        assertThat(Versions.loadDocIdAndVersion(directoryReader, new Term(UidFieldMapper.NAME, "1")).version, equalTo(2l));

        // test reuse of uid field
        doc = new Document();
        version.setLongValue(3);
        doc.add(uid);
        doc.add(version);
        writer.updateDocument(new Term(UidFieldMapper.NAME, "1"), doc);
        
        directoryReader = reopen(directoryReader);
        assertThat(Versions.loadVersion(directoryReader, new Term(UidFieldMapper.NAME, "1")), equalTo(3l));
        assertThat(Versions.loadDocIdAndVersion(directoryReader, new Term(UidFieldMapper.NAME, "1")).version, equalTo(3l));

        writer.deleteDocuments(new Term(UidFieldMapper.NAME, "1"));
        directoryReader = reopen(directoryReader);
        assertThat(Versions.loadVersion(directoryReader, new Term(UidFieldMapper.NAME, "1")), equalTo(Versions.NOT_FOUND));
        assertThat(Versions.loadDocIdAndVersion(directoryReader, new Term(UidFieldMapper.NAME, "1")), nullValue());
        directoryReader.close();
        writer.close();
        dir.close();
    }

    @Test
    public void testNestedDocuments() throws IOException {
        Directory dir = newDirectory();
        IndexWriter writer = new IndexWriter(dir, new IndexWriterConfig(Lucene.STANDARD_ANALYZER));

        List<Document> docs = new ArrayList<>();
        for (int i = 0; i < 4; ++i) {
            // Nested
            Document doc = new Document();
            doc.add(new Field(UidFieldMapper.NAME, "1", UidFieldMapper.Defaults.NESTED_FIELD_TYPE));
            docs.add(doc);
        }
        // Root
        Document doc = new Document();
        doc.add(new Field(UidFieldMapper.NAME, "1", UidFieldMapper.Defaults.FIELD_TYPE));
        NumericDocValuesField version = new NumericDocValuesField(VersionFieldMapper.NAME, 5L);
        doc.add(version);
        docs.add(doc);

        writer.updateDocuments(new Term(UidFieldMapper.NAME, "1"), docs);
        DirectoryReader directoryReader = DirectoryReader.open(writer, true);
        assertThat(Versions.loadVersion(directoryReader, new Term(UidFieldMapper.NAME, "1")), equalTo(5l));
        assertThat(Versions.loadDocIdAndVersion(directoryReader, new Term(UidFieldMapper.NAME, "1")).version, equalTo(5l));

        version.setLongValue(6L);
        writer.updateDocuments(new Term(UidFieldMapper.NAME, "1"), docs);
        version.setLongValue(7L);
        writer.updateDocuments(new Term(UidFieldMapper.NAME, "1"), docs);
        directoryReader = reopen(directoryReader);
        assertThat(Versions.loadVersion(directoryReader, new Term(UidFieldMapper.NAME, "1")), equalTo(7l));
        assertThat(Versions.loadDocIdAndVersion(directoryReader, new Term(UidFieldMapper.NAME, "1")).version, equalTo(7l));

        writer.deleteDocuments(new Term(UidFieldMapper.NAME, "1"));
        directoryReader = reopen(directoryReader);
        assertThat(Versions.loadVersion(directoryReader, new Term(UidFieldMapper.NAME, "1")), equalTo(Versions.NOT_FOUND));
        assertThat(Versions.loadDocIdAndVersion(directoryReader, new Term(UidFieldMapper.NAME, "1")), nullValue());
        directoryReader.close();
        writer.close();
        dir.close();
    }

    @Test
    public void testBackwardCompatibility() throws IOException {
        Directory dir = newDirectory();
        IndexWriter writer = new IndexWriter(dir, new IndexWriterConfig(Lucene.STANDARD_ANALYZER));

        DirectoryReader directoryReader = DirectoryReader.open(writer, true);
        MatcherAssert.assertThat(Versions.loadVersion(directoryReader, new Term(UidFieldMapper.NAME, "1")), equalTo(Versions.NOT_FOUND));

        Document doc = new Document();
        UidField uidAndVersion = new UidField("1", 1L);
        doc.add(uidAndVersion);
        writer.addDocument(doc);

        uidAndVersion.uid = "2";
        uidAndVersion.version = 2;
        writer.addDocument(doc);
        writer.commit();

        directoryReader = reopen(directoryReader);
        assertThat(Versions.loadVersion(directoryReader, new Term(UidFieldMapper.NAME, "1")), equalTo(1l));
        assertThat(Versions.loadVersion(directoryReader, new Term(UidFieldMapper.NAME, "2")), equalTo(2l));
        assertThat(Versions.loadVersion(directoryReader, new Term(UidFieldMapper.NAME, "3")), equalTo(Versions.NOT_FOUND));
        directoryReader.close();
        writer.close();
        dir.close();
    }

    // This is how versions used to be encoded
    private static class UidField extends Field {
        private static final FieldType FIELD_TYPE = new FieldType();
        static {
            FIELD_TYPE.setTokenized(true);
            FIELD_TYPE.setIndexOptions(IndexOptions.DOCS_AND_FREQS_AND_POSITIONS);
            FIELD_TYPE.setStored(true);
            FIELD_TYPE.freeze();
        }
        String uid;
        long version;
        UidField(String uid, long version) {
            super(UidFieldMapper.NAME, uid, FIELD_TYPE);
            this.uid = uid;
            this.version = version;
        }
        @Override
        public TokenStream tokenStream(Analyzer analyzer, TokenStream reuse) throws IOException {
            return new TokenStream() {
                boolean finished = true;
                final CharTermAttribute term = addAttribute(CharTermAttribute.class);
                final PayloadAttribute payload = addAttribute(PayloadAttribute.class);
                @Override
                public boolean incrementToken() throws IOException {
                    if (finished) {
                        return false;
                    }
                    term.setEmpty().append(uid);
                    payload.setPayload(new BytesRef(Numbers.longToBytes(version)));
                    finished = true;
                    return true;
                }
                @Override
                public void reset() throws IOException {
                    finished = false;
                }
            };
        }
    }

    @Test
    public void testMergingOldIndices() throws Exception {
        final IndexWriterConfig iwConf = new IndexWriterConfig(new KeywordAnalyzer());
        iwConf.setMergePolicy(new ElasticsearchMergePolicy(iwConf.getMergePolicy()));
        final Directory dir = newDirectory();
        final IndexWriter iw = new IndexWriter(dir, iwConf);

        // 1st segment, no _version
        Document document = new Document();
        // Add a dummy field (enough to trigger #3237)
        document.add(new StringField("a", "b", Store.NO));
        StringField uid = new StringField(UidFieldMapper.NAME, "1", Store.YES);
        document.add(uid);
        iw.addDocument(document);
        uid.setStringValue("2");
        iw.addDocument(document);
        iw.commit();

        // 2nd segment, old layout
        document = new Document();
        UidField uidAndVersion = new UidField("3", 3L);
        document.add(uidAndVersion);
        iw.addDocument(document);
        uidAndVersion.uid = "4";
        uidAndVersion.version = 4L;
        iw.addDocument(document);
        iw.commit();

        // 3rd segment new layout
        document = new Document();
        uid.setStringValue("5");
        Field version = new NumericDocValuesField(VersionFieldMapper.NAME, 5L);
        document.add(uid);
        document.add(version);
        iw.addDocument(document);
        uid.setStringValue("6");
        version.setLongValue(6L);
        iw.addDocument(document);
        iw.commit();

        final Map<String, Long> expectedVersions = ImmutableMap.<String, Long>builder()
                .put("1", 0L).put("2", 0L).put("3", 0L).put("4", 4L).put("5", 5L).put("6", 6L).build();

        // Force merge and check versions
        iw.forceMerge(1, true);
        final LeafReader ir = SlowCompositeReaderWrapper.wrap(DirectoryReader.open(iw.getDirectory()));
        final NumericDocValues versions = ir.getNumericDocValues(VersionFieldMapper.NAME);
        assertThat(versions, notNullValue());
        for (int i = 0; i < ir.maxDoc(); ++i) {
            final String uidValue = ir.document(i).get(UidFieldMapper.NAME);
            final long expectedVersion = expectedVersions.get(uidValue);
            assertThat(versions.get(i), equalTo(expectedVersion));
        }

        iw.close();
        assertThat(IndexWriter.isLocked(iw.getDirectory()), is(false));
        ir.close();
        dir.close();
    }
}


File: core/src/test/java/org/elasticsearch/index/engine/InternalEngineMergeTests.java
/*
 * Licensed to Elasticsearch under one or more contributor
 * license agreements. See the NOTICE file distributed with
 * this work for additional information regarding copyright
 * ownership. Elasticsearch licenses this file to you under
 * the Apache License, Version 2.0 (the "License"); you may
 * not use this file except in compliance with the License.
 * You may obtain a copy of the License at
 *
 *    http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing,
 * software distributed under the License is distributed on an
 * "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY
 * KIND, either express or implied.  See the License for the
 * specific language governing permissions and limitations
 * under the License.
 */
package org.elasticsearch.index.engine;

import com.google.common.base.Predicate;
import org.apache.lucene.index.LogByteSizeMergePolicy;
import org.elasticsearch.action.admin.indices.stats.IndicesStatsResponse;
import org.elasticsearch.action.bulk.BulkRequestBuilder;
import org.elasticsearch.action.bulk.BulkResponse;
import org.elasticsearch.client.Requests;
import org.elasticsearch.cluster.metadata.IndexMetaData;
import org.elasticsearch.common.settings.Settings;
import org.elasticsearch.index.merge.policy.LogDocMergePolicyProvider;
import org.elasticsearch.test.ElasticsearchIntegrationTest;
import org.hamcrest.Matchers;
import org.junit.Test;

import java.io.IOException;
import java.util.concurrent.ExecutionException;

import static org.elasticsearch.common.xcontent.XContentFactory.jsonBuilder;
import static org.elasticsearch.test.ElasticsearchIntegrationTest.ClusterScope;
import static org.elasticsearch.test.ElasticsearchIntegrationTest.Scope;
import static org.elasticsearch.test.hamcrest.ElasticsearchAssertions.assertAcked;
import static org.elasticsearch.test.hamcrest.ElasticsearchAssertions.assertNoFailures;

/**
 */
@ClusterScope(numDataNodes = 1, scope = Scope.SUITE)
public class InternalEngineMergeTests extends ElasticsearchIntegrationTest {

    @Test
    @Slow
    public void testMergesHappening() throws InterruptedException, IOException, ExecutionException {
        final int numOfShards = randomIntBetween(1,5);
        // some settings to keep num segments low
        assertAcked(prepareCreate("test").setSettings(Settings.builder()
                .put(IndexMetaData.SETTING_NUMBER_OF_SHARDS, numOfShards)
                .put(IndexMetaData.SETTING_NUMBER_OF_REPLICAS, 0)
                .put(LogDocMergePolicyProvider.MIN_MERGE_DOCS_KEY, 10)
                .put(LogDocMergePolicyProvider.MERGE_FACTORY_KEY, 5)
                .put(LogByteSizeMergePolicy.DEFAULT_MIN_MERGE_MB, 0.5)
                .build()));
        long id = 0;
        final int rounds = scaledRandomIntBetween(50, 300);
        logger.info("Starting rounds [{}] ", rounds);
        for (int i = 0; i < rounds; ++i) {
            final int numDocs = scaledRandomIntBetween(100, 1000);
            BulkRequestBuilder request = client().prepareBulk();
            for (int j = 0; j < numDocs; ++j) {
                request.add(Requests.indexRequest("test").type("type1").id(Long.toString(id++)).source(jsonBuilder().startObject().field("l", randomLong()).endObject()));
            }
            BulkResponse response = request.execute().actionGet();
            refresh();
            assertNoFailures(response);
            IndicesStatsResponse stats = client().admin().indices().prepareStats("test").setSegments(true).setMerge(true).get();
            logger.info("index round [{}] - segments {}, total merges {}, current merge {}", i, stats.getPrimaries().getSegments().getCount(), stats.getPrimaries().getMerge().getTotal(), stats.getPrimaries().getMerge().getCurrent());
        }
        final long upperNumberSegments = 2 * numOfShards * 10;
        awaitBusy(new Predicate<Object>() {
            @Override
            public boolean apply(Object input) {
                IndicesStatsResponse stats = client().admin().indices().prepareStats().setSegments(true).setMerge(true).get();
                logger.info("numshards {}, segments {}, total merges {}, current merge {}", numOfShards, stats.getPrimaries().getSegments().getCount(), stats.getPrimaries().getMerge().getTotal(), stats.getPrimaries().getMerge().getCurrent());
                long current = stats.getPrimaries().getMerge().getCurrent();
                long count = stats.getPrimaries().getSegments().getCount();
                return count < upperNumberSegments && current == 0;
            }
        });
        IndicesStatsResponse stats = client().admin().indices().prepareStats().setSegments(true).setMerge(true).get();
        logger.info("numshards {}, segments {}, total merges {}, current merge {}", numOfShards, stats.getPrimaries().getSegments().getCount(), stats.getPrimaries().getMerge().getTotal(), stats.getPrimaries().getMerge().getCurrent());
        long count = stats.getPrimaries().getSegments().getCount();
        assertThat(count, Matchers.lessThanOrEqualTo(upperNumberSegments));
    }

}


File: core/src/test/java/org/elasticsearch/index/engine/InternalEngineTests.java
/*
 * Licensed to Elasticsearch under one or more contributor
 * license agreements. See the NOTICE file distributed with
 * this work for additional information regarding copyright
 * ownership. Elasticsearch licenses this file to you under
 * the Apache License, Version 2.0 (the "License"); you may
 * not use this file except in compliance with the License.
 * You may obtain a copy of the License at
 *
 *    http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing,
 * software distributed under the License is distributed on an
 * "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY
 * KIND, either express or implied.  See the License for the
 * specific language governing permissions and limitations
 * under the License.
 */

package org.elasticsearch.index.engine;

import com.google.common.collect.ImmutableMap;
import org.apache.log4j.AppenderSkeleton;
import org.apache.log4j.Level;
import org.apache.log4j.LogManager;
import org.apache.log4j.Logger;
import org.apache.log4j.spi.LoggingEvent;
import org.apache.lucene.codecs.Codec;
import org.apache.lucene.document.Field;
import org.apache.lucene.document.NumericDocValuesField;
import org.apache.lucene.document.TextField;
import org.apache.lucene.index.*;
import org.apache.lucene.search.IndexSearcher;
import org.apache.lucene.search.MatchAllDocsQuery;
import org.apache.lucene.search.TermQuery;
import org.apache.lucene.search.TopDocs;
import org.apache.lucene.store.AlreadyClosedException;
import org.apache.lucene.store.Directory;
import org.apache.lucene.store.MockDirectoryWrapper;
import org.apache.lucene.util.IOUtils;
import org.elasticsearch.Version;
import org.elasticsearch.cluster.metadata.IndexMetaData;
import org.elasticsearch.common.Base64;
import org.elasticsearch.common.Nullable;
import org.elasticsearch.common.bytes.BytesArray;
import org.elasticsearch.common.bytes.BytesReference;
import org.elasticsearch.common.collect.Tuple;
import org.elasticsearch.common.lucene.Lucene;
import org.elasticsearch.common.lucene.uid.Versions;
import org.elasticsearch.common.settings.Settings;
import org.elasticsearch.common.util.BigArrays;
import org.elasticsearch.index.Index;
import org.elasticsearch.index.VersionType;
import org.elasticsearch.index.analysis.AnalysisService;
import org.elasticsearch.index.codec.CodecService;
import org.elasticsearch.index.deletionpolicy.KeepOnlyLastDeletionPolicy;
import org.elasticsearch.index.deletionpolicy.SnapshotDeletionPolicy;
import org.elasticsearch.index.engine.Engine.Searcher;
import org.elasticsearch.index.indexing.ShardIndexingService;
import org.elasticsearch.index.indexing.slowlog.ShardSlowLogIndexingService;
import org.elasticsearch.index.mapper.*;
import org.elasticsearch.index.mapper.Mapper.BuilderContext;
import org.elasticsearch.index.mapper.ParseContext.Document;
import org.elasticsearch.index.mapper.internal.SourceFieldMapper;
import org.elasticsearch.index.mapper.internal.UidFieldMapper;
import org.elasticsearch.index.mapper.object.RootObjectMapper;
import org.elasticsearch.index.merge.policy.LogByteSizeMergePolicyProvider;
import org.elasticsearch.index.merge.policy.MergePolicyProvider;
import org.elasticsearch.index.merge.scheduler.ConcurrentMergeSchedulerProvider;
import org.elasticsearch.index.merge.scheduler.MergeSchedulerProvider;
import org.elasticsearch.index.settings.IndexDynamicSettingsModule;
import org.elasticsearch.index.settings.IndexSettingsService;
import org.elasticsearch.index.shard.ShardId;
import org.elasticsearch.index.shard.ShardUtils;
import org.elasticsearch.index.shard.TranslogRecoveryPerformer;
import org.elasticsearch.index.similarity.SimilarityLookupService;
import org.elasticsearch.index.store.DirectoryService;
import org.elasticsearch.index.store.DirectoryUtils;
import org.elasticsearch.index.store.Store;
import org.elasticsearch.index.translog.Translog;
import org.elasticsearch.index.translog.TranslogConfig;
import org.elasticsearch.test.DummyShardLock;
import org.elasticsearch.test.ElasticsearchTestCase;
import org.elasticsearch.threadpool.ThreadPool;
import org.hamcrest.MatcherAssert;
import org.junit.After;
import org.junit.Before;
import org.junit.Test;

import java.io.IOException;
import java.nio.charset.Charset;
import java.nio.file.Path;
import java.util.Arrays;
import java.util.List;
import java.util.concurrent.CountDownLatch;
import java.util.concurrent.atomic.AtomicInteger;

import static org.elasticsearch.common.settings.Settings.Builder.EMPTY_SETTINGS;
import static org.elasticsearch.index.engine.Engine.Operation.Origin.PRIMARY;
import static org.elasticsearch.index.engine.Engine.Operation.Origin.REPLICA;
import static org.hamcrest.Matchers.*;

public class InternalEngineTests extends ElasticsearchTestCase {

    protected final ShardId shardId = new ShardId(new Index("index"), 1);

    protected ThreadPool threadPool;

    private Store store;
    private Store storeReplica;

    protected InternalEngine engine;
    protected InternalEngine replicaEngine;

    private Settings defaultSettings;
    private int indexConcurrency;
    private String codecName;
    private Path primaryTranslogDir;
    private Path replicaTranslogDir;

    @Override
    @Before
    public void setUp() throws Exception {
        super.setUp();

        CodecService codecService = new CodecService(shardId.index());
        indexConcurrency = randomIntBetween(1, 20);
        String name = Codec.getDefault().getName();
        if (Arrays.asList(codecService.availableCodecs()).contains(name)) {
            // some codecs are read only so we only take the ones that we have in the service and randomly
            // selected by lucene test case.
            codecName = name;
        } else {
            codecName = "default";
        }
        defaultSettings = Settings.builder()
                .put(EngineConfig.INDEX_COMPOUND_ON_FLUSH, randomBoolean())
                .put(EngineConfig.INDEX_GC_DELETES_SETTING, "1h") // make sure this doesn't kick in on us
                .put(EngineConfig.INDEX_CODEC_SETTING, codecName)
                .put(EngineConfig.INDEX_CONCURRENCY_SETTING, indexConcurrency)
                .build(); // TODO randomize more settings
        threadPool = new ThreadPool(getClass().getName());
        store = createStore();
        storeReplica = createStore();
        Lucene.cleanLuceneIndex(store.directory());
        Lucene.cleanLuceneIndex(storeReplica.directory());
        primaryTranslogDir = createTempDir("translog-primary");
        engine = createEngine(store, primaryTranslogDir);
        LiveIndexWriterConfig currentIndexWriterConfig = engine.getCurrentIndexWriterConfig();

        assertEquals(engine.config().getCodec().getName(), codecService.codec(codecName).getName());
        assertEquals(currentIndexWriterConfig.getCodec().getName(), codecService.codec(codecName).getName());
        if (randomBoolean()) {
            engine.config().setEnableGcDeletes(false);
        }
        replicaTranslogDir = createTempDir("translog-replica");
        replicaEngine = createEngine(storeReplica, replicaTranslogDir);
        currentIndexWriterConfig = replicaEngine.getCurrentIndexWriterConfig();

        assertEquals(replicaEngine.config().getCodec().getName(), codecService.codec(codecName).getName());
        assertEquals(currentIndexWriterConfig.getCodec().getName(), codecService.codec(codecName).getName());
        if (randomBoolean()) {
            engine.config().setEnableGcDeletes(false);
        }
    }

    @Override
    @After
    public void tearDown() throws Exception {
        super.tearDown();
        IOUtils.close(
                replicaEngine, storeReplica,
                engine, store);
        terminate(threadPool);
    }


    private Document testDocumentWithTextField() {
        Document document = testDocument();
        document.add(new TextField("value", "test", Field.Store.YES));
        return document;
    }

    private Document testDocument() {
        return new Document();
    }


    private ParsedDocument testParsedDocument(String uid, String id, String type, String routing, long timestamp, long ttl, Document document, BytesReference source, Mapping mappingUpdate) {
        Field uidField = new Field("_uid", uid, UidFieldMapper.Defaults.FIELD_TYPE);
        Field versionField = new NumericDocValuesField("_version", 0);
        document.add(uidField);
        document.add(versionField);
        return new ParsedDocument(uidField, versionField, id, type, routing, timestamp, ttl, Arrays.asList(document), source, mappingUpdate);
    }

    protected Store createStore() throws IOException {
        return createStore(newDirectory());
    }

    protected Store createStore(final Directory directory) throws IOException {
        final DirectoryService directoryService = new DirectoryService(shardId, EMPTY_SETTINGS) {
            @Override
            public Directory newDirectory() throws IOException {
                return directory;
            }

            @Override
            public long throttleTimeInNanos() {
                return 0;
            }
        };
        return new Store(shardId, EMPTY_SETTINGS, directoryService, new DummyShardLock(shardId));
    }

    protected Translog createTranslog() throws IOException {
        return createTranslog(primaryTranslogDir);
    }

    protected Translog createTranslog(Path translogPath) throws IOException {
        TranslogConfig translogConfig = new TranslogConfig(shardId, translogPath, EMPTY_SETTINGS, Translog.Durabilty.REQUEST, BigArrays.NON_RECYCLING_INSTANCE, threadPool);
        return new Translog(translogConfig);
    }

    protected Translog createTranslogReplica() throws IOException {
        return createTranslog(replicaTranslogDir);
    }

    protected IndexDeletionPolicy createIndexDeletionPolicy() {
        return new KeepOnlyLastDeletionPolicy(shardId, EMPTY_SETTINGS);
    }

    protected SnapshotDeletionPolicy createSnapshotDeletionPolicy() {
        return new SnapshotDeletionPolicy(createIndexDeletionPolicy());
    }

    protected MergePolicyProvider<?> createMergePolicy() {
        return new LogByteSizeMergePolicyProvider(store, new IndexSettingsService(new Index("test"), EMPTY_SETTINGS));
    }

    protected MergeSchedulerProvider createMergeScheduler(IndexSettingsService indexSettingsService) {
        return new ConcurrentMergeSchedulerProvider(shardId, EMPTY_SETTINGS, threadPool, indexSettingsService);
    }

    protected InternalEngine createEngine(Store store, Path translogPath) {
        IndexSettingsService indexSettingsService = new IndexSettingsService(shardId.index(), Settings.builder().put(defaultSettings).put(IndexMetaData.SETTING_VERSION_CREATED, Version.CURRENT).build());
        return createEngine(indexSettingsService, store, translogPath, createMergeScheduler(indexSettingsService));
    }

    protected InternalEngine createEngine(IndexSettingsService indexSettingsService, Store store, Path translogPath, MergeSchedulerProvider mergeSchedulerProvider) {
        return new InternalEngine(config(indexSettingsService, store, translogPath, mergeSchedulerProvider), false);
    }

    public EngineConfig config(IndexSettingsService indexSettingsService, Store store, Path translogPath, MergeSchedulerProvider mergeSchedulerProvider) {
        IndexWriterConfig iwc = newIndexWriterConfig();
        TranslogConfig translogConfig = new TranslogConfig(shardId, translogPath, indexSettingsService.getSettings(), Translog.Durabilty.REQUEST, BigArrays.NON_RECYCLING_INSTANCE, threadPool);

        EngineConfig config = new EngineConfig(shardId, threadPool, new ShardIndexingService(shardId, EMPTY_SETTINGS, new ShardSlowLogIndexingService(shardId, EMPTY_SETTINGS, indexSettingsService)), indexSettingsService
                , null, store, createSnapshotDeletionPolicy(), createMergePolicy(), mergeSchedulerProvider,
                iwc.getAnalyzer(), iwc.getSimilarity(), new CodecService(shardId.index()), new Engine.FailedEngineListener() {
            @Override
            public void onFailedEngine(ShardId shardId, String reason, @Nullable Throwable t) {
                // we don't need to notify anybody in this test
            }
        }, new TranslogHandler(shardId.index().getName()), IndexSearcher.getDefaultQueryCache(), IndexSearcher.getDefaultQueryCachingPolicy(), translogConfig);

        return config;
    }

    protected static final BytesReference B_1 = new BytesArray(new byte[]{1});
    protected static final BytesReference B_2 = new BytesArray(new byte[]{2});
    protected static final BytesReference B_3 = new BytesArray(new byte[]{3});

    @Test
    public void testSegments() throws Exception {
        List<Segment> segments = engine.segments(false);
        assertThat(segments.isEmpty(), equalTo(true));
        assertThat(engine.segmentsStats().getCount(), equalTo(0l));
        assertThat(engine.segmentsStats().getMemoryInBytes(), equalTo(0l));
        final boolean defaultCompound = defaultSettings.getAsBoolean(EngineConfig.INDEX_COMPOUND_ON_FLUSH, true);

        // create a doc and refresh
        ParsedDocument doc = testParsedDocument("1", "1", "test", null, -1, -1, testDocumentWithTextField(), B_1, null);
        engine.create(new Engine.Create(null, newUid("1"), doc));

        ParsedDocument doc2 = testParsedDocument("2", "2", "test", null, -1, -1, testDocumentWithTextField(), B_2, null);
        engine.create(new Engine.Create(null, newUid("2"), doc2));
        engine.refresh("test");

        segments = engine.segments(false);
        assertThat(segments.size(), equalTo(1));
        SegmentsStats stats = engine.segmentsStats();
        assertThat(stats.getCount(), equalTo(1l));
        assertThat(stats.getTermsMemoryInBytes(), greaterThan(0l));
        assertThat(stats.getStoredFieldsMemoryInBytes(), greaterThan(0l));
        assertThat(stats.getTermVectorsMemoryInBytes(), equalTo(0l));
        assertThat(stats.getNormsMemoryInBytes(), greaterThan(0l));
        assertThat(stats.getDocValuesMemoryInBytes(), greaterThan(0l));
        assertThat(segments.get(0).isCommitted(), equalTo(false));
        assertThat(segments.get(0).isSearch(), equalTo(true));
        assertThat(segments.get(0).getNumDocs(), equalTo(2));
        assertThat(segments.get(0).getDeletedDocs(), equalTo(0));
        assertThat(segments.get(0).isCompound(), equalTo(defaultCompound));
        assertThat(segments.get(0).ramTree, nullValue());

        engine.flush();

        segments = engine.segments(false);
        assertThat(segments.size(), equalTo(1));
        assertThat(engine.segmentsStats().getCount(), equalTo(1l));
        assertThat(segments.get(0).isCommitted(), equalTo(true));
        assertThat(segments.get(0).isSearch(), equalTo(true));
        assertThat(segments.get(0).getNumDocs(), equalTo(2));
        assertThat(segments.get(0).getDeletedDocs(), equalTo(0));
        assertThat(segments.get(0).isCompound(), equalTo(defaultCompound));

        engine.config().setCompoundOnFlush(false);

        ParsedDocument doc3 = testParsedDocument("3", "3", "test", null, -1, -1, testDocumentWithTextField(), B_3, null);
        engine.create(new Engine.Create(null, newUid("3"), doc3));
        engine.refresh("test");

        segments = engine.segments(false);
        assertThat(segments.size(), equalTo(2));
        assertThat(engine.segmentsStats().getCount(), equalTo(2l));
        assertThat(engine.segmentsStats().getTermsMemoryInBytes(), greaterThan(stats.getTermsMemoryInBytes()));
        assertThat(engine.segmentsStats().getStoredFieldsMemoryInBytes(), greaterThan(stats.getStoredFieldsMemoryInBytes()));
        assertThat(engine.segmentsStats().getTermVectorsMemoryInBytes(), equalTo(0l));
        assertThat(engine.segmentsStats().getNormsMemoryInBytes(), greaterThan(stats.getNormsMemoryInBytes()));
        assertThat(engine.segmentsStats().getDocValuesMemoryInBytes(), greaterThan(stats.getDocValuesMemoryInBytes()));
        assertThat(segments.get(0).getGeneration() < segments.get(1).getGeneration(), equalTo(true));
        assertThat(segments.get(0).isCommitted(), equalTo(true));
        assertThat(segments.get(0).isSearch(), equalTo(true));
        assertThat(segments.get(0).getNumDocs(), equalTo(2));
        assertThat(segments.get(0).getDeletedDocs(), equalTo(0));
        assertThat(segments.get(0).isCompound(), equalTo(defaultCompound));


        assertThat(segments.get(1).isCommitted(), equalTo(false));
        assertThat(segments.get(1).isSearch(), equalTo(true));
        assertThat(segments.get(1).getNumDocs(), equalTo(1));
        assertThat(segments.get(1).getDeletedDocs(), equalTo(0));
        assertThat(segments.get(1).isCompound(), equalTo(false));


        engine.delete(new Engine.Delete("test", "1", newUid("1")));
        engine.refresh("test");

        segments = engine.segments(false);
        assertThat(segments.size(), equalTo(2));
        assertThat(engine.segmentsStats().getCount(), equalTo(2l));
        assertThat(segments.get(0).getGeneration() < segments.get(1).getGeneration(), equalTo(true));
        assertThat(segments.get(0).isCommitted(), equalTo(true));
        assertThat(segments.get(0).isSearch(), equalTo(true));
        assertThat(segments.get(0).getNumDocs(), equalTo(1));
        assertThat(segments.get(0).getDeletedDocs(), equalTo(1));
        assertThat(segments.get(0).isCompound(), equalTo(defaultCompound));

        assertThat(segments.get(1).isCommitted(), equalTo(false));
        assertThat(segments.get(1).isSearch(), equalTo(true));
        assertThat(segments.get(1).getNumDocs(), equalTo(1));
        assertThat(segments.get(1).getDeletedDocs(), equalTo(0));
        assertThat(segments.get(1).isCompound(), equalTo(false));

        engine.config().setCompoundOnFlush(true);
        ParsedDocument doc4 = testParsedDocument("4", "4", "test", null, -1, -1, testDocumentWithTextField(), B_3, null);
        engine.create(new Engine.Create(null, newUid("4"), doc4));
        engine.refresh("test");

        segments = engine.segments(false);
        assertThat(segments.size(), equalTo(3));
        assertThat(engine.segmentsStats().getCount(), equalTo(3l));
        assertThat(segments.get(0).getGeneration() < segments.get(1).getGeneration(), equalTo(true));
        assertThat(segments.get(0).isCommitted(), equalTo(true));
        assertThat(segments.get(0).isSearch(), equalTo(true));
        assertThat(segments.get(0).getNumDocs(), equalTo(1));
        assertThat(segments.get(0).getDeletedDocs(), equalTo(1));
        assertThat(segments.get(0).isCompound(), equalTo(defaultCompound));

        assertThat(segments.get(1).isCommitted(), equalTo(false));
        assertThat(segments.get(1).isSearch(), equalTo(true));
        assertThat(segments.get(1).getNumDocs(), equalTo(1));
        assertThat(segments.get(1).getDeletedDocs(), equalTo(0));
        assertThat(segments.get(1).isCompound(), equalTo(false));

        assertThat(segments.get(2).isCommitted(), equalTo(false));
        assertThat(segments.get(2).isSearch(), equalTo(true));
        assertThat(segments.get(2).getNumDocs(), equalTo(1));
        assertThat(segments.get(2).getDeletedDocs(), equalTo(0));
        assertThat(segments.get(2).isCompound(), equalTo(true));
    }

    public void testVerboseSegments() throws Exception {
        List<Segment> segments = engine.segments(true);
        assertThat(segments.isEmpty(), equalTo(true));

        ParsedDocument doc = testParsedDocument("1", "1", "test", null, -1, -1, testDocumentWithTextField(), B_1, null);
        engine.create(new Engine.Create(null, newUid("1"), doc));
        engine.refresh("test");

        segments = engine.segments(true);
        assertThat(segments.size(), equalTo(1));
        assertThat(segments.get(0).ramTree, notNullValue());

        ParsedDocument doc2 = testParsedDocument("2", "2", "test", null, -1, -1, testDocumentWithTextField(), B_2, null);
        engine.create(new Engine.Create(null, newUid("2"), doc2));
        engine.refresh("test");
        ParsedDocument doc3 = testParsedDocument("3", "3", "test", null, -1, -1, testDocumentWithTextField(), B_3, null);
        engine.create(new Engine.Create(null, newUid("3"), doc3));
        engine.refresh("test");

        segments = engine.segments(true);
        assertThat(segments.size(), equalTo(3));
        assertThat(segments.get(0).ramTree, notNullValue());
        assertThat(segments.get(1).ramTree, notNullValue());
        assertThat(segments.get(2).ramTree, notNullValue());

    }


    @Test
    public void testSegmentsWithMergeFlag() throws Exception {
        ConcurrentMergeSchedulerProvider mergeSchedulerProvider = new ConcurrentMergeSchedulerProvider(shardId, EMPTY_SETTINGS, threadPool, new IndexSettingsService(shardId.index(), EMPTY_SETTINGS));
        IndexSettingsService indexSettingsService = new IndexSettingsService(shardId.index(), Settings.builder().put(defaultSettings).put(IndexMetaData.SETTING_VERSION_CREATED, Version.CURRENT).build());
        try (Store store = createStore();
             Engine engine = createEngine(indexSettingsService, store, createTempDir(), mergeSchedulerProvider)) {

            ParsedDocument doc = testParsedDocument("1", "1", "test", null, -1, -1, testDocument(), B_1, null);
            Engine.Index index = new Engine.Index(null, newUid("1"), doc);
            engine.index(index);
            engine.flush();
            assertThat(engine.segments(false).size(), equalTo(1));
            index = new Engine.Index(null, newUid("2"), doc);
            engine.index(index);
            engine.flush();
            List<Segment> segments = engine.segments(false);
            assertThat(segments.size(), equalTo(2));
            for (Segment segment : segments) {
                assertThat(segment.getMergeId(), nullValue());
            }
            index = new Engine.Index(null, newUid("3"), doc);
            engine.index(index);
            engine.flush();
            segments = engine.segments(false);
            assertThat(segments.size(), equalTo(3));
            for (Segment segment : segments) {
                assertThat(segment.getMergeId(), nullValue());
            }

            index = new Engine.Index(null, newUid("4"), doc);
            engine.index(index);
            engine.flush();
            final long gen1 = store.readLastCommittedSegmentsInfo().getGeneration();
            // now, optimize and wait for merges, see that we have no merge flag
            engine.forceMerge(true);

            for (Segment segment : engine.segments(false)) {
                assertThat(segment.getMergeId(), nullValue());
            }
            // we could have multiple underlying merges, so the generation may increase more than once
            assertTrue(store.readLastCommittedSegmentsInfo().getGeneration() > gen1);

            final boolean flush = randomBoolean();
            final long gen2 = store.readLastCommittedSegmentsInfo().getGeneration();
            engine.forceMerge(flush);
            for (Segment segment : engine.segments(false)) {
                assertThat(segment.getMergeId(), nullValue());
            }

            if (flush) {
                // we should have had just 1 merge, so last generation should be exact
                assertEquals(gen2 + 1, store.readLastCommittedSegmentsInfo().getLastGeneration());
            }
        }
    }

    public void testCommitStats() {
        Document document = testDocumentWithTextField();
        document.add(new Field(SourceFieldMapper.NAME, B_1.toBytes(), SourceFieldMapper.Defaults.FIELD_TYPE));
        ParsedDocument doc = testParsedDocument("1", "1", "test", null, -1, -1, document, B_1, null);
        engine.create(new Engine.Create(null, newUid("1"), doc));

        CommitStats stats1 = engine.commitStats();
        assertThat(stats1.getGeneration(), greaterThan(0l));
        assertThat(stats1.getId(), notNullValue());
        assertThat(stats1.getUserData(), hasKey(Translog.TRANSLOG_GENERATION_KEY));

        engine.flush(true, true);
        CommitStats stats2 = engine.commitStats();
        assertThat(stats2.getGeneration(), greaterThan(stats1.getGeneration()));
        assertThat(stats2.getId(), notNullValue());
        assertThat(stats2.getId(), not(equalTo(stats1.getId())));
        assertThat(stats2.getUserData(), hasKey(Translog.TRANSLOG_GENERATION_KEY));
        assertThat(stats2.getUserData(), hasKey(Translog.TRANSLOG_UUID_KEY));
        assertThat(stats2.getUserData().get(Translog.TRANSLOG_GENERATION_KEY), not(equalTo(stats1.getUserData().get(Translog.TRANSLOG_GENERATION_KEY))));
        assertThat(stats2.getUserData().get(Translog.TRANSLOG_UUID_KEY), equalTo(stats1.getUserData().get(Translog.TRANSLOG_UUID_KEY)))
        ;
    }

    @Test
    public void testSimpleOperations() throws Exception {
        Engine.Searcher searchResult = engine.acquireSearcher("test");
        MatcherAssert.assertThat(searchResult, EngineSearcherTotalHitsMatcher.engineSearcherTotalHits(0));
        searchResult.close();

        // create a document
        Document document = testDocumentWithTextField();
        document.add(new Field(SourceFieldMapper.NAME, B_1.toBytes(), SourceFieldMapper.Defaults.FIELD_TYPE));
        ParsedDocument doc = testParsedDocument("1", "1", "test", null, -1, -1, document, B_1, null);
        engine.create(new Engine.Create(null, newUid("1"), doc));

        // its not there...
        searchResult = engine.acquireSearcher("test");
        MatcherAssert.assertThat(searchResult, EngineSearcherTotalHitsMatcher.engineSearcherTotalHits(0));
        MatcherAssert.assertThat(searchResult, EngineSearcherTotalHitsMatcher.engineSearcherTotalHits(new TermQuery(new Term("value", "test")), 0));
        searchResult.close();

        // but, we can still get it (in realtime)
        Engine.GetResult getResult = engine.get(new Engine.Get(true, newUid("1")));
        assertThat(getResult.exists(), equalTo(true));
        assertThat(getResult.source().source.toBytesArray(), equalTo(B_1.toBytesArray()));
        assertThat(getResult.docIdAndVersion(), nullValue());
        getResult.release();

        // but, not there non realtime
        getResult = engine.get(new Engine.Get(false, newUid("1")));
        assertThat(getResult.exists(), equalTo(false));
        getResult.release();
        // refresh and it should be there
        engine.refresh("test");

        // now its there...
        searchResult = engine.acquireSearcher("test");
        MatcherAssert.assertThat(searchResult, EngineSearcherTotalHitsMatcher.engineSearcherTotalHits(1));
        MatcherAssert.assertThat(searchResult, EngineSearcherTotalHitsMatcher.engineSearcherTotalHits(new TermQuery(new Term("value", "test")), 1));
        searchResult.close();

        // also in non realtime
        getResult = engine.get(new Engine.Get(false, newUid("1")));
        assertThat(getResult.exists(), equalTo(true));
        assertThat(getResult.docIdAndVersion(), notNullValue());
        getResult.release();

        // now do an update
        document = testDocument();
        document.add(new TextField("value", "test1", Field.Store.YES));
        document.add(new Field(SourceFieldMapper.NAME, B_2.toBytes(), SourceFieldMapper.Defaults.FIELD_TYPE));
        doc = testParsedDocument("1", "1", "test", null, -1, -1, document, B_2, null);
        engine.index(new Engine.Index(null, newUid("1"), doc));

        // its not updated yet...
        searchResult = engine.acquireSearcher("test");
        MatcherAssert.assertThat(searchResult, EngineSearcherTotalHitsMatcher.engineSearcherTotalHits(1));
        MatcherAssert.assertThat(searchResult, EngineSearcherTotalHitsMatcher.engineSearcherTotalHits(new TermQuery(new Term("value", "test")), 1));
        MatcherAssert.assertThat(searchResult, EngineSearcherTotalHitsMatcher.engineSearcherTotalHits(new TermQuery(new Term("value", "test1")), 0));
        searchResult.close();

        // but, we can still get it (in realtime)
        getResult = engine.get(new Engine.Get(true, newUid("1")));
        assertThat(getResult.exists(), equalTo(true));
        assertThat(getResult.source().source.toBytesArray(), equalTo(B_2.toBytesArray()));
        assertThat(getResult.docIdAndVersion(), nullValue());
        getResult.release();

        // refresh and it should be updated
        engine.refresh("test");

        searchResult = engine.acquireSearcher("test");
        MatcherAssert.assertThat(searchResult, EngineSearcherTotalHitsMatcher.engineSearcherTotalHits(1));
        MatcherAssert.assertThat(searchResult, EngineSearcherTotalHitsMatcher.engineSearcherTotalHits(new TermQuery(new Term("value", "test")), 0));
        MatcherAssert.assertThat(searchResult, EngineSearcherTotalHitsMatcher.engineSearcherTotalHits(new TermQuery(new Term("value", "test1")), 1));
        searchResult.close();

        // now delete
        engine.delete(new Engine.Delete("test", "1", newUid("1")));

        // its not deleted yet
        searchResult = engine.acquireSearcher("test");
        MatcherAssert.assertThat(searchResult, EngineSearcherTotalHitsMatcher.engineSearcherTotalHits(1));
        MatcherAssert.assertThat(searchResult, EngineSearcherTotalHitsMatcher.engineSearcherTotalHits(new TermQuery(new Term("value", "test")), 0));
        MatcherAssert.assertThat(searchResult, EngineSearcherTotalHitsMatcher.engineSearcherTotalHits(new TermQuery(new Term("value", "test1")), 1));
        searchResult.close();

        // but, get should not see it (in realtime)
        getResult = engine.get(new Engine.Get(true, newUid("1")));
        assertThat(getResult.exists(), equalTo(false));
        getResult.release();

        // refresh and it should be deleted
        engine.refresh("test");

        searchResult = engine.acquireSearcher("test");
        MatcherAssert.assertThat(searchResult, EngineSearcherTotalHitsMatcher.engineSearcherTotalHits(0));
        MatcherAssert.assertThat(searchResult, EngineSearcherTotalHitsMatcher.engineSearcherTotalHits(new TermQuery(new Term("value", "test")), 0));
        MatcherAssert.assertThat(searchResult, EngineSearcherTotalHitsMatcher.engineSearcherTotalHits(new TermQuery(new Term("value", "test1")), 0));
        searchResult.close();

        // add it back
        document = testDocumentWithTextField();
        document.add(new Field(SourceFieldMapper.NAME, B_1.toBytes(), SourceFieldMapper.Defaults.FIELD_TYPE));
        doc = testParsedDocument("1", "1", "test", null, -1, -1, document, B_1, null);
        engine.create(new Engine.Create(null, newUid("1"), doc));

        // its not there...
        searchResult = engine.acquireSearcher("test");
        MatcherAssert.assertThat(searchResult, EngineSearcherTotalHitsMatcher.engineSearcherTotalHits(0));
        MatcherAssert.assertThat(searchResult, EngineSearcherTotalHitsMatcher.engineSearcherTotalHits(new TermQuery(new Term("value", "test")), 0));
        MatcherAssert.assertThat(searchResult, EngineSearcherTotalHitsMatcher.engineSearcherTotalHits(new TermQuery(new Term("value", "test1")), 0));
        searchResult.close();

        // refresh and it should be there
        engine.refresh("test");

        // now its there...
        searchResult = engine.acquireSearcher("test");
        MatcherAssert.assertThat(searchResult, EngineSearcherTotalHitsMatcher.engineSearcherTotalHits(1));
        MatcherAssert.assertThat(searchResult, EngineSearcherTotalHitsMatcher.engineSearcherTotalHits(new TermQuery(new Term("value", "test")), 1));
        MatcherAssert.assertThat(searchResult, EngineSearcherTotalHitsMatcher.engineSearcherTotalHits(new TermQuery(new Term("value", "test1")), 0));
        searchResult.close();

        // now flush
        engine.flush();

        // and, verify get (in real time)
        getResult = engine.get(new Engine.Get(true, newUid("1")));
        assertThat(getResult.exists(), equalTo(true));
        assertThat(getResult.source(), nullValue());
        assertThat(getResult.docIdAndVersion(), notNullValue());
        getResult.release();

        // make sure we can still work with the engine
        // now do an update
        document = testDocument();
        document.add(new TextField("value", "test1", Field.Store.YES));
        doc = testParsedDocument("1", "1", "test", null, -1, -1, document, B_1, null);
        engine.index(new Engine.Index(null, newUid("1"), doc));

        // its not updated yet...
        searchResult = engine.acquireSearcher("test");
        MatcherAssert.assertThat(searchResult, EngineSearcherTotalHitsMatcher.engineSearcherTotalHits(1));
        MatcherAssert.assertThat(searchResult, EngineSearcherTotalHitsMatcher.engineSearcherTotalHits(new TermQuery(new Term("value", "test")), 1));
        MatcherAssert.assertThat(searchResult, EngineSearcherTotalHitsMatcher.engineSearcherTotalHits(new TermQuery(new Term("value", "test1")), 0));
        searchResult.close();

        // refresh and it should be updated
        engine.refresh("test");

        searchResult = engine.acquireSearcher("test");
        MatcherAssert.assertThat(searchResult, EngineSearcherTotalHitsMatcher.engineSearcherTotalHits(1));
        MatcherAssert.assertThat(searchResult, EngineSearcherTotalHitsMatcher.engineSearcherTotalHits(new TermQuery(new Term("value", "test")), 0));
        MatcherAssert.assertThat(searchResult, EngineSearcherTotalHitsMatcher.engineSearcherTotalHits(new TermQuery(new Term("value", "test1")), 1));
        searchResult.close();
    }

    @Test
    public void testSearchResultRelease() throws Exception {
        Engine.Searcher searchResult = engine.acquireSearcher("test");
        MatcherAssert.assertThat(searchResult, EngineSearcherTotalHitsMatcher.engineSearcherTotalHits(0));
        searchResult.close();

        // create a document
        ParsedDocument doc = testParsedDocument("1", "1", "test", null, -1, -1, testDocumentWithTextField(), B_1, null);
        engine.create(new Engine.Create(null, newUid("1"), doc));

        // its not there...
        searchResult = engine.acquireSearcher("test");
        MatcherAssert.assertThat(searchResult, EngineSearcherTotalHitsMatcher.engineSearcherTotalHits(0));
        MatcherAssert.assertThat(searchResult, EngineSearcherTotalHitsMatcher.engineSearcherTotalHits(new TermQuery(new Term("value", "test")), 0));
        searchResult.close();

        // refresh and it should be there
        engine.refresh("test");

        // now its there...
        searchResult = engine.acquireSearcher("test");
        MatcherAssert.assertThat(searchResult, EngineSearcherTotalHitsMatcher.engineSearcherTotalHits(1));
        MatcherAssert.assertThat(searchResult, EngineSearcherTotalHitsMatcher.engineSearcherTotalHits(new TermQuery(new Term("value", "test")), 1));
        // don't release the search result yet...

        // delete, refresh and do a new search, it should not be there
        engine.delete(new Engine.Delete("test", "1", newUid("1")));
        engine.refresh("test");
        Engine.Searcher updateSearchResult = engine.acquireSearcher("test");
        MatcherAssert.assertThat(updateSearchResult, EngineSearcherTotalHitsMatcher.engineSearcherTotalHits(0));
        updateSearchResult.close();

        // the non release search result should not see the deleted yet...
        MatcherAssert.assertThat(searchResult, EngineSearcherTotalHitsMatcher.engineSearcherTotalHits(1));
        MatcherAssert.assertThat(searchResult, EngineSearcherTotalHitsMatcher.engineSearcherTotalHits(new TermQuery(new Term("value", "test")), 1));
        searchResult.close();
    }

    public void testSyncedFlush() throws IOException {
        final String syncId = randomUnicodeOfCodepointLengthBetween(10, 20);
        ParsedDocument doc = testParsedDocument("1", "1", "test", null, -1, -1, testDocumentWithTextField(), B_1, null);
        engine.create(new Engine.Create(null, newUid("1"), doc));
        Engine.CommitId commitID = engine.flush();
        assertThat(commitID, equalTo(new Engine.CommitId(store.readLastCommittedSegmentsInfo().getId())));
        byte[] wrongBytes = Base64.decode(commitID.toString());
        wrongBytes[0] = (byte) ~wrongBytes[0];
        Engine.CommitId wrongId = new Engine.CommitId(wrongBytes);
        assertEquals("should fail to sync flush with wrong id (but no docs)", engine.syncFlush(syncId + "1", wrongId),
                Engine.SyncedFlushResult.COMMIT_MISMATCH);
        engine.create(new Engine.Create(null, newUid("2"), doc));
        assertEquals("should fail to sync flush with right id but pending doc", engine.syncFlush(syncId + "2", commitID),
                Engine.SyncedFlushResult.PENDING_OPERATIONS);
        commitID = engine.flush();
        assertEquals("should succeed to flush commit with right id and no pending doc", engine.syncFlush(syncId, commitID),
                Engine.SyncedFlushResult.SUCCESS);
        assertEquals(store.readLastCommittedSegmentsInfo().getUserData().get(Engine.SYNC_COMMIT_ID), syncId);
        assertEquals(engine.getLastCommittedSegmentInfos().getUserData().get(Engine.SYNC_COMMIT_ID), syncId);
    }

    public void testSycnedFlushSurvivesEngineRestart() throws IOException {
        final String syncId = randomUnicodeOfCodepointLengthBetween(10, 20);
        ParsedDocument doc = testParsedDocument("1", "1", "test", null, -1, -1, testDocumentWithTextField(), B_1, null);
        engine.create(new Engine.Create(null, newUid("1"), doc));
        final Engine.CommitId commitID = engine.flush();
        assertEquals("should succeed to flush commit with right id and no pending doc", engine.syncFlush(syncId, commitID),
                Engine.SyncedFlushResult.SUCCESS);
        assertEquals(store.readLastCommittedSegmentsInfo().getUserData().get(Engine.SYNC_COMMIT_ID), syncId);
        assertEquals(engine.getLastCommittedSegmentInfos().getUserData().get(Engine.SYNC_COMMIT_ID), syncId);
        EngineConfig config = engine.config();
        if (randomBoolean()) {
            engine.close();
        } else {
            engine.flushAndClose();
        }
        engine = new InternalEngine(config, randomBoolean());
        assertEquals(engine.getLastCommittedSegmentInfos().getUserData().get(Engine.SYNC_COMMIT_ID), syncId);
    }

    public void testSycnedFlushVanishesOnReplay() throws IOException {
        final String syncId = randomUnicodeOfCodepointLengthBetween(10, 20);
        ParsedDocument doc = testParsedDocument("1", "1", "test", null, -1, -1, testDocumentWithTextField(), B_1, null);
        engine.create(new Engine.Create(null, newUid("1"), doc));
        final Engine.CommitId commitID = engine.flush();
        assertEquals("should succeed to flush commit with right id and no pending doc", engine.syncFlush(syncId, commitID),
                Engine.SyncedFlushResult.SUCCESS);
        assertEquals(store.readLastCommittedSegmentsInfo().getUserData().get(Engine.SYNC_COMMIT_ID), syncId);
        assertEquals(engine.getLastCommittedSegmentInfos().getUserData().get(Engine.SYNC_COMMIT_ID), syncId);
        doc = testParsedDocument("2", "2", "test", null, -1, -1, testDocumentWithTextField(), new BytesArray("{}"), null);
        engine.create(new Engine.Create(null, newUid("2"), doc));
        EngineConfig config = engine.config();
        engine.close();
        final MockDirectoryWrapper directory = DirectoryUtils.getLeaf(store.directory(), MockDirectoryWrapper.class);
        if (directory != null) {
            // since we rollback the IW we are writing the same segment files again after starting IW but MDW prevents
            // this so we have to disable the check explicitly
            directory.setPreventDoubleWrite(false);
        }
        engine = new InternalEngine(config, false);
        assertNull("Sync ID must be gone since we have a document to replay", engine.getLastCommittedSegmentInfos().getUserData().get(Engine.SYNC_COMMIT_ID));
    }

    @Test
    public void testVersioningNewCreate() {
        ParsedDocument doc = testParsedDocument("1", "1", "test", null, -1, -1, testDocument(), B_1, null);
        Engine.Create create = new Engine.Create(null, newUid("1"), doc);
        engine.create(create);
        assertThat(create.version(), equalTo(1l));

        create = new Engine.Create(null, newUid("1"), doc, create.version(), create.versionType().versionTypeForReplicationAndRecovery(), REPLICA, 0);
        replicaEngine.create(create);
        assertThat(create.version(), equalTo(1l));
    }

    @Test
    public void testExternalVersioningNewCreate() {
        ParsedDocument doc = testParsedDocument("1", "1", "test", null, -1, -1, testDocument(), B_1, null);
        Engine.Create create = new Engine.Create(null, newUid("1"), doc, 12, VersionType.EXTERNAL, Engine.Operation.Origin.PRIMARY, 0);
        engine.create(create);
        assertThat(create.version(), equalTo(12l));

        create = new Engine.Create(null, newUid("1"), doc, create.version(), create.versionType().versionTypeForReplicationAndRecovery(), REPLICA, 0);
        replicaEngine.create(create);
        assertThat(create.version(), equalTo(12l));
    }

    @Test
    public void testVersioningNewIndex() {
        ParsedDocument doc = testParsedDocument("1", "1", "test", null, -1, -1, testDocument(), B_1, null);
        Engine.Index index = new Engine.Index(null, newUid("1"), doc);
        engine.index(index);
        assertThat(index.version(), equalTo(1l));

        index = new Engine.Index(null, newUid("1"), doc, index.version(), index.versionType().versionTypeForReplicationAndRecovery(), REPLICA, 0);
        replicaEngine.index(index);
        assertThat(index.version(), equalTo(1l));
    }

    @Test
    public void testExternalVersioningNewIndex() {
        ParsedDocument doc = testParsedDocument("1", "1", "test", null, -1, -1, testDocument(), B_1, null);
        Engine.Index index = new Engine.Index(null, newUid("1"), doc, 12, VersionType.EXTERNAL, PRIMARY, 0);
        engine.index(index);
        assertThat(index.version(), equalTo(12l));

        index = new Engine.Index(null, newUid("1"), doc, index.version(), index.versionType().versionTypeForReplicationAndRecovery(), REPLICA, 0);
        replicaEngine.index(index);
        assertThat(index.version(), equalTo(12l));
    }

    @Test
    public void testVersioningIndexConflict() {
        ParsedDocument doc = testParsedDocument("1", "1", "test", null, -1, -1, testDocument(), B_1, null);
        Engine.Index index = new Engine.Index(null, newUid("1"), doc);
        engine.index(index);
        assertThat(index.version(), equalTo(1l));

        index = new Engine.Index(null, newUid("1"), doc);
        engine.index(index);
        assertThat(index.version(), equalTo(2l));

        index = new Engine.Index(null, newUid("1"), doc, 1l, VersionType.INTERNAL, Engine.Operation.Origin.PRIMARY, 0);
        try {
            engine.index(index);
            fail();
        } catch (VersionConflictEngineException e) {
            // all is well
        }

        // future versions should not work as well
        index = new Engine.Index(null, newUid("1"), doc, 3l, VersionType.INTERNAL, PRIMARY, 0);
        try {
            engine.index(index);
            fail();
        } catch (VersionConflictEngineException e) {
            // all is well
        }
    }

    @Test
    public void testExternalVersioningIndexConflict() {
        ParsedDocument doc = testParsedDocument("1", "1", "test", null, -1, -1, testDocument(), B_1, null);
        Engine.Index index = new Engine.Index(null, newUid("1"), doc, 12, VersionType.EXTERNAL, PRIMARY, 0);
        engine.index(index);
        assertThat(index.version(), equalTo(12l));

        index = new Engine.Index(null, newUid("1"), doc, 14, VersionType.EXTERNAL, PRIMARY, 0);
        engine.index(index);
        assertThat(index.version(), equalTo(14l));

        index = new Engine.Index(null, newUid("1"), doc, 13, VersionType.EXTERNAL, PRIMARY, 0);
        try {
            engine.index(index);
            fail();
        } catch (VersionConflictEngineException e) {
            // all is well
        }
    }

    @Test
    public void testVersioningIndexConflictWithFlush() {
        ParsedDocument doc = testParsedDocument("1", "1", "test", null, -1, -1, testDocument(), B_1, null);
        Engine.Index index = new Engine.Index(null, newUid("1"), doc);
        engine.index(index);
        assertThat(index.version(), equalTo(1l));

        index = new Engine.Index(null, newUid("1"), doc);
        engine.index(index);
        assertThat(index.version(), equalTo(2l));

        engine.flush();

        index = new Engine.Index(null, newUid("1"), doc, 1l, VersionType.INTERNAL, PRIMARY, 0);
        try {
            engine.index(index);
            fail();
        } catch (VersionConflictEngineException e) {
            // all is well
        }

        // future versions should not work as well
        index = new Engine.Index(null, newUid("1"), doc, 3l, VersionType.INTERNAL, PRIMARY, 0);
        try {
            engine.index(index);
            fail();
        } catch (VersionConflictEngineException e) {
            // all is well
        }
    }

    @Test
    public void testExternalVersioningIndexConflictWithFlush() {
        ParsedDocument doc = testParsedDocument("1", "1", "test", null, -1, -1, testDocument(), B_1, null);
        Engine.Index index = new Engine.Index(null, newUid("1"), doc, 12, VersionType.EXTERNAL, PRIMARY, 0);
        engine.index(index);
        assertThat(index.version(), equalTo(12l));

        index = new Engine.Index(null, newUid("1"), doc, 14, VersionType.EXTERNAL, PRIMARY, 0);
        engine.index(index);
        assertThat(index.version(), equalTo(14l));

        engine.flush();

        index = new Engine.Index(null, newUid("1"), doc, 13, VersionType.EXTERNAL, PRIMARY, 0);
        try {
            engine.index(index);
            fail();
        } catch (VersionConflictEngineException e) {
            // all is well
        }
    }

    public void testForceMerge() {
        int numDocs = randomIntBetween(10, 100);
        for (int i = 0; i < numDocs; i++) {
            ParsedDocument doc = testParsedDocument(Integer.toString(i), Integer.toString(i), "test", null, -1, -1, testDocument(), B_1, null);
            Engine.Index index = new Engine.Index(null, newUid(Integer.toString(i)), doc);
            engine.index(index);
            engine.refresh("test");
        }
        try (Engine.Searcher test = engine.acquireSearcher("test")) {
            assertEquals(numDocs, test.reader().numDocs());
        }
        engine.forceMerge(true, 1, false, false, false);
        assertEquals(engine.segments(true).size(), 1);

        ParsedDocument doc = testParsedDocument(Integer.toString(0), Integer.toString(0), "test", null, -1, -1, testDocument(), B_1, null);
        Engine.Index index = new Engine.Index(null, newUid(Integer.toString(0)), doc);
        engine.delete(new Engine.Delete(index.type(), index.id(), index.uid()));
        engine.forceMerge(true, 10, true, false, false); //expunge deletes

        assertEquals(engine.segments(true).size(), 1);
        try (Engine.Searcher test = engine.acquireSearcher("test")) {
            assertEquals(numDocs - 1, test.reader().numDocs());
            assertEquals(numDocs - 1, test.reader().maxDoc());
        }

        doc = testParsedDocument(Integer.toString(1), Integer.toString(1), "test", null, -1, -1, testDocument(), B_1, null);
        index = new Engine.Index(null, newUid(Integer.toString(1)), doc);
        engine.delete(new Engine.Delete(index.type(), index.id(), index.uid()));
        engine.forceMerge(true, 10, false, false, false); //expunge deletes

        assertEquals(engine.segments(true).size(), 1);
        try (Engine.Searcher test = engine.acquireSearcher("test")) {
            assertEquals(numDocs - 2, test.reader().numDocs());
            assertEquals(numDocs - 1, test.reader().maxDoc());
        }
    }

    public void testForceMergeAndClose() throws IOException, InterruptedException {
        int numIters = randomIntBetween(2, 10);
        for (int j = 0; j < numIters; j++) {
            try (Store store = createStore()) {
                final InternalEngine engine = createEngine(store, createTempDir());
                final CountDownLatch startGun = new CountDownLatch(1);
                final CountDownLatch indexed = new CountDownLatch(1);

                Thread thread = new Thread() {
                    public void run() {
                        try {
                            try {
                                startGun.await();
                            } catch (InterruptedException e) {
                                throw new RuntimeException(e);
                            }
                            int i = 0;
                            while (true) {
                                int numDocs = randomIntBetween(1, 20);
                                for (int j = 0; j < numDocs; j++) {
                                    i++;
                                    ParsedDocument doc = testParsedDocument(Integer.toString(i), Integer.toString(i), "test", null, -1, -1, testDocument(), B_1, null);
                                    Engine.Index index = new Engine.Index(null, newUid(Integer.toString(i)), doc);
                                    engine.index(index);
                                }
                                engine.refresh("test");
                                indexed.countDown();
                                try {
                                    engine.forceMerge(randomBoolean(), 1, false, randomBoolean(), randomBoolean());
                                } catch (ForceMergeFailedEngineException ex) {
                                    // ok
                                    return;
                                }
                            }
                        } catch (AlreadyClosedException | EngineClosedException ex) {
                            // fine
                        }
                    }
                };

                thread.start();
                startGun.countDown();
                int someIters = randomIntBetween(1, 10);
                for (int i = 0; i < someIters; i++) {
                    engine.forceMerge(randomBoolean(), 1, false, randomBoolean(), randomBoolean());
                }
                indexed.await();
                IOUtils.close(engine);
            }
        }

    }

    @Test
    public void testVersioningDeleteConflict() {
        ParsedDocument doc = testParsedDocument("1", "1", "test", null, -1, -1, testDocument(), B_1, null);
        Engine.Index index = new Engine.Index(null, newUid("1"), doc);
        engine.index(index);
        assertThat(index.version(), equalTo(1l));

        index = new Engine.Index(null, newUid("1"), doc);
        engine.index(index);
        assertThat(index.version(), equalTo(2l));

        Engine.Delete delete = new Engine.Delete("test", "1", newUid("1"), 1l, VersionType.INTERNAL, PRIMARY, 0, false);
        try {
            engine.delete(delete);
            fail();
        } catch (VersionConflictEngineException e) {
            // all is well
        }

        // future versions should not work as well
        delete = new Engine.Delete("test", "1", newUid("1"), 3l, VersionType.INTERNAL, PRIMARY, 0, false);
        try {
            engine.delete(delete);
            fail();
        } catch (VersionConflictEngineException e) {
            // all is well
        }

        // now actually delete
        delete = new Engine.Delete("test", "1", newUid("1"), 2l, VersionType.INTERNAL, PRIMARY, 0, false);
        engine.delete(delete);
        assertThat(delete.version(), equalTo(3l));

        // now check if we can index to a delete doc with version
        index = new Engine.Index(null, newUid("1"), doc, 2l, VersionType.INTERNAL, PRIMARY, 0);
        try {
            engine.index(index);
            fail();
        } catch (VersionConflictEngineException e) {
            // all is well
        }

        // we shouldn't be able to create as well
        Engine.Create create = new Engine.Create(null, newUid("1"), doc, 2l, VersionType.INTERNAL, PRIMARY, 0);
        try {
            engine.create(create);
        } catch (VersionConflictEngineException e) {
            // all is well
        }
    }

    @Test
    public void testVersioningDeleteConflictWithFlush() {
        ParsedDocument doc = testParsedDocument("1", "1", "test", null, -1, -1, testDocument(), B_1, null);
        Engine.Index index = new Engine.Index(null, newUid("1"), doc);
        engine.index(index);
        assertThat(index.version(), equalTo(1l));

        index = new Engine.Index(null, newUid("1"), doc);
        engine.index(index);
        assertThat(index.version(), equalTo(2l));

        engine.flush();

        Engine.Delete delete = new Engine.Delete("test", "1", newUid("1"), 1l, VersionType.INTERNAL, PRIMARY, 0, false);
        try {
            engine.delete(delete);
            fail();
        } catch (VersionConflictEngineException e) {
            // all is well
        }

        // future versions should not work as well
        delete = new Engine.Delete("test", "1", newUid("1"), 3l, VersionType.INTERNAL, PRIMARY, 0, false);
        try {
            engine.delete(delete);
            fail();
        } catch (VersionConflictEngineException e) {
            // all is well
        }

        engine.flush();

        // now actually delete
        delete = new Engine.Delete("test", "1", newUid("1"), 2l, VersionType.INTERNAL, PRIMARY, 0, false);
        engine.delete(delete);
        assertThat(delete.version(), equalTo(3l));

        engine.flush();

        // now check if we can index to a delete doc with version
        index = new Engine.Index(null, newUid("1"), doc, 2l, VersionType.INTERNAL, PRIMARY, 0);
        try {
            engine.index(index);
            fail();
        } catch (VersionConflictEngineException e) {
            // all is well
        }

        // we shouldn't be able to create as well
        Engine.Create create = new Engine.Create(null, newUid("1"), doc, 2l, VersionType.INTERNAL, PRIMARY, 0);
        try {
            engine.create(create);
        } catch (VersionConflictEngineException e) {
            // all is well
        }
    }

    @Test
    public void testVersioningCreateExistsException() {
        ParsedDocument doc = testParsedDocument("1", "1", "test", null, -1, -1, testDocument(), B_1, null);
        Engine.Create create = new Engine.Create(null, newUid("1"), doc, Versions.MATCH_ANY, VersionType.INTERNAL, PRIMARY, 0);
        engine.create(create);
        assertThat(create.version(), equalTo(1l));

        create = new Engine.Create(null, newUid("1"), doc, Versions.MATCH_ANY, VersionType.INTERNAL, PRIMARY, 0);
        try {
            engine.create(create);
            fail();
        } catch (DocumentAlreadyExistsException e) {
            // all is well
        }
    }

    @Test
    public void testVersioningCreateExistsExceptionWithFlush() {
        ParsedDocument doc = testParsedDocument("1", "1", "test", null, -1, -1, testDocument(), B_1, null);
        Engine.Create create = new Engine.Create(null, newUid("1"), doc, Versions.MATCH_ANY, VersionType.INTERNAL, PRIMARY, 0);
        engine.create(create);
        assertThat(create.version(), equalTo(1l));

        engine.flush();

        create = new Engine.Create(null, newUid("1"), doc, Versions.MATCH_ANY, VersionType.INTERNAL, PRIMARY, 0);
        try {
            engine.create(create);
            fail();
        } catch (DocumentAlreadyExistsException e) {
            // all is well
        }
    }

    @Test
    public void testVersioningReplicaConflict1() {
        ParsedDocument doc = testParsedDocument("1", "1", "test", null, -1, -1, testDocument(), B_1, null);
        Engine.Index index = new Engine.Index(null, newUid("1"), doc);
        engine.index(index);
        assertThat(index.version(), equalTo(1l));

        index = new Engine.Index(null, newUid("1"), doc);
        engine.index(index);
        assertThat(index.version(), equalTo(2l));

        // apply the second index to the replica, should work fine
        index = new Engine.Index(null, newUid("1"), doc, index.version(), VersionType.INTERNAL.versionTypeForReplicationAndRecovery(), REPLICA, 0);
        replicaEngine.index(index);
        assertThat(index.version(), equalTo(2l));

        // now, the old one should not work
        index = new Engine.Index(null, newUid("1"), doc, 1l, VersionType.INTERNAL.versionTypeForReplicationAndRecovery(), REPLICA, 0);
        try {
            replicaEngine.index(index);
            fail();
        } catch (VersionConflictEngineException e) {
            // all is well
        }

        // second version on replica should fail as well
        try {
            index = new Engine.Index(null, newUid("1"), doc, 2l
                    , VersionType.INTERNAL.versionTypeForReplicationAndRecovery(), REPLICA, 0);
            replicaEngine.index(index);
            assertThat(index.version(), equalTo(2l));
        } catch (VersionConflictEngineException e) {
            // all is well
        }
    }

    @Test
    public void testVersioningReplicaConflict2() {
        ParsedDocument doc = testParsedDocument("1", "1", "test", null, -1, -1, testDocument(), B_1, null);
        Engine.Index index = new Engine.Index(null, newUid("1"), doc);
        engine.index(index);
        assertThat(index.version(), equalTo(1l));

        // apply the first index to the replica, should work fine
        index = new Engine.Index(null, newUid("1"), doc, 1l
                , VersionType.INTERNAL.versionTypeForReplicationAndRecovery(), REPLICA, 0);
        replicaEngine.index(index);
        assertThat(index.version(), equalTo(1l));

        // index it again
        index = new Engine.Index(null, newUid("1"), doc);
        engine.index(index);
        assertThat(index.version(), equalTo(2l));

        // now delete it
        Engine.Delete delete = new Engine.Delete("test", "1", newUid("1"));
        engine.delete(delete);
        assertThat(delete.version(), equalTo(3l));

        // apply the delete on the replica (skipping the second index)
        delete = new Engine.Delete("test", "1", newUid("1"), 3l
                , VersionType.INTERNAL.versionTypeForReplicationAndRecovery(), REPLICA, 0, false);
        replicaEngine.delete(delete);
        assertThat(delete.version(), equalTo(3l));

        // second time delete with same version should fail
        try {
            delete = new Engine.Delete("test", "1", newUid("1"), 3l
                    , VersionType.INTERNAL.versionTypeForReplicationAndRecovery(), REPLICA, 0, false);
            replicaEngine.delete(delete);
            fail("excepted VersionConflictEngineException to be thrown");
        } catch (VersionConflictEngineException e) {
            // all is well
        }

        // now do the second index on the replica, it should fail
        try {
            index = new Engine.Index(null, newUid("1"), doc, 2l, VersionType.INTERNAL.versionTypeForReplicationAndRecovery(), REPLICA, 0);
            replicaEngine.index(index);
            fail("excepted VersionConflictEngineException to be thrown");
        } catch (VersionConflictEngineException e) {
            // all is well
        }
    }


    @Test
    public void testBasicCreatedFlag() {
        ParsedDocument doc = testParsedDocument("1", "1", "test", null, -1, -1, testDocument(), B_1, null);
        Engine.Index index = new Engine.Index(null, newUid("1"), doc);
        assertTrue(engine.index(index));

        index = new Engine.Index(null, newUid("1"), doc);
        assertFalse(engine.index(index));

        engine.delete(new Engine.Delete(null, "1", newUid("1")));

        index = new Engine.Index(null, newUid("1"), doc);
        assertTrue(engine.index(index));
    }

    @Test
    public void testCreatedFlagAfterFlush() {
        ParsedDocument doc = testParsedDocument("1", "1", "test", null, -1, -1, testDocument(), B_1, null);
        Engine.Index index = new Engine.Index(null, newUid("1"), doc);
        assertTrue(engine.index(index));

        engine.delete(new Engine.Delete(null, "1", newUid("1")));

        engine.flush();

        index = new Engine.Index(null, newUid("1"), doc);
        assertTrue(engine.index(index));
    }

    private static class MockAppender extends AppenderSkeleton {
        public boolean sawIndexWriterMessage;

        public boolean sawIndexWriterIFDMessage;

        @Override
        protected void append(LoggingEvent event) {
            if (event.getLevel() == Level.TRACE && event.getMessage().toString().contains("[index][1] ")) {
                if (event.getLoggerName().endsWith("lucene.iw") &&
                        event.getMessage().toString().contains("IW: apply all deletes during flush")) {
                    sawIndexWriterMessage = true;
                }
                if (event.getLoggerName().endsWith("lucene.iw.ifd")) {
                    sawIndexWriterIFDMessage = true;
                }
            }
        }

        @Override
        public boolean requiresLayout() {
            return false;
        }

        @Override
        public void close() {
        }
    }

    // #5891: make sure IndexWriter's infoStream output is
    // sent to lucene.iw with log level TRACE:

    @Test
    public void testIndexWriterInfoStream() {
        assumeFalse("who tests the tester?", VERBOSE);
        MockAppender mockAppender = new MockAppender();

        Logger rootLogger = Logger.getRootLogger();
        Level savedLevel = rootLogger.getLevel();
        rootLogger.addAppender(mockAppender);
        rootLogger.setLevel(Level.DEBUG);

        try {
            // First, with DEBUG, which should NOT log IndexWriter output:
            ParsedDocument doc = testParsedDocument("1", "1", "test", null, -1, -1, testDocumentWithTextField(), B_1, null);
            engine.create(new Engine.Create(null, newUid("1"), doc));
            engine.flush();
            assertFalse(mockAppender.sawIndexWriterMessage);

            // Again, with TRACE, which should log IndexWriter output:
            rootLogger.setLevel(Level.TRACE);
            engine.create(new Engine.Create(null, newUid("2"), doc));
            engine.flush();
            assertTrue(mockAppender.sawIndexWriterMessage);

        } finally {
            rootLogger.removeAppender(mockAppender);
            rootLogger.setLevel(savedLevel);
        }
    }

    // #8603: make sure we can separately log IFD's messages
    public void testIndexWriterIFDInfoStream() {
        assumeFalse("who tests the tester?", VERBOSE);
        MockAppender mockAppender = new MockAppender();

        // Works when running this test inside Intellij:
        Logger iwIFDLogger = LogManager.exists("org.elasticsearch.index.engine.lucene.iw.ifd");
        if (iwIFDLogger == null) {
            // Works when running this test from command line:
            iwIFDLogger = LogManager.exists("index.engine.lucene.iw.ifd");
            assertNotNull(iwIFDLogger);
        }

        iwIFDLogger.addAppender(mockAppender);
        iwIFDLogger.setLevel(Level.DEBUG);

        try {
            // First, with DEBUG, which should NOT log IndexWriter output:
            ParsedDocument doc = testParsedDocument("1", "1", "test", null, -1, -1, testDocumentWithTextField(), B_1, null);
            engine.create(new Engine.Create(null, newUid("1"), doc));
            engine.flush();
            assertFalse(mockAppender.sawIndexWriterMessage);
            assertFalse(mockAppender.sawIndexWriterIFDMessage);

            // Again, with TRACE, which should only log IndexWriter IFD output:
            iwIFDLogger.setLevel(Level.TRACE);
            engine.create(new Engine.Create(null, newUid("2"), doc));
            engine.flush();
            assertFalse(mockAppender.sawIndexWriterMessage);
            assertTrue(mockAppender.sawIndexWriterIFDMessage);

        } finally {
            iwIFDLogger.removeAppender(mockAppender);
            iwIFDLogger.setLevel(null);
        }
    }

    @Slow
    @Test
    public void testEnableGcDeletes() throws Exception {
        IndexSettingsService indexSettingsService = new IndexSettingsService(shardId.index(), Settings.builder().put(defaultSettings).put(IndexMetaData.SETTING_VERSION_CREATED, Version.CURRENT).build());
        try (Store store = createStore();
             Engine engine = new InternalEngine(config(indexSettingsService, store, createTempDir(), createMergeScheduler(indexSettingsService)), false)) {
            engine.config().setEnableGcDeletes(false);

            // Add document
            Document document = testDocument();
            document.add(new TextField("value", "test1", Field.Store.YES));

            ParsedDocument doc = testParsedDocument("1", "1", "test", null, -1, -1, document, B_2, null);
            engine.index(new Engine.Index(null, newUid("1"), doc, 1, VersionType.EXTERNAL, Engine.Operation.Origin.PRIMARY, System.nanoTime(), false));

            // Delete document we just added:
            engine.delete(new Engine.Delete("test", "1", newUid("1"), 10, VersionType.EXTERNAL, Engine.Operation.Origin.PRIMARY, System.nanoTime(), false));

            // Get should not find the document
            Engine.GetResult getResult = engine.get(new Engine.Get(true, newUid("1")));
            assertThat(getResult.exists(), equalTo(false));

            // Give the gc pruning logic a chance to kick in
            Thread.sleep(1000);

            if (randomBoolean()) {
                engine.refresh("test");
            }

            // Delete non-existent document
            engine.delete(new Engine.Delete("test", "2", newUid("2"), 10, VersionType.EXTERNAL, Engine.Operation.Origin.PRIMARY, System.nanoTime(), false));

            // Get should not find the document (we never indexed uid=2):
            getResult = engine.get(new Engine.Get(true, newUid("2")));
            assertThat(getResult.exists(), equalTo(false));

            // Try to index uid=1 with a too-old version, should fail:
            try {
                engine.index(new Engine.Index(null, newUid("1"), doc, 2, VersionType.EXTERNAL, Engine.Operation.Origin.PRIMARY, System.nanoTime()));
                fail("did not hit expected exception");
            } catch (VersionConflictEngineException vcee) {
                // expected
            }

            // Get should still not find the document
            getResult = engine.get(new Engine.Get(true, newUid("1")));
            assertThat(getResult.exists(), equalTo(false));

            // Try to index uid=2 with a too-old version, should fail:
            try {
                engine.index(new Engine.Index(null, newUid("2"), doc, 2, VersionType.EXTERNAL, Engine.Operation.Origin.PRIMARY, System.nanoTime()));
                fail("did not hit expected exception");
            } catch (VersionConflictEngineException vcee) {
                // expected
            }

            // Get should not find the document
            getResult = engine.get(new Engine.Get(true, newUid("2")));
            assertThat(getResult.exists(), equalTo(false));
        }
    }

    protected Term newUid(String id) {
        return new Term("_uid", id);
    }

    @Test
    public void testExtractShardId() {
        try (Engine.Searcher test = this.engine.acquireSearcher("test")) {
            ShardId shardId = ShardUtils.extractShardId(test.reader());
            assertNotNull(shardId);
            assertEquals(shardId, engine.config().getShardId());
        }
    }

    /**
     * Random test that throws random exception and ensures all references are
     * counted down / released and resources are closed.
     */
    @Test
    public void testFailStart() throws IOException {
        // this test fails if any reader, searcher or directory is not closed - MDW FTW
        final int iters = scaledRandomIntBetween(10, 100);
        for (int i = 0; i < iters; i++) {
            MockDirectoryWrapper wrapper = newMockDirectory();
            wrapper.setFailOnOpenInput(randomBoolean());
            wrapper.setAllowRandomFileNotFoundException(randomBoolean());
            wrapper.setRandomIOExceptionRate(randomDouble());
            wrapper.setRandomIOExceptionRateOnOpen(randomDouble());
            final Path translogPath = createTempDir("testFailStart");
            try (Store store = createStore(wrapper)) {
                int refCount = store.refCount();
                assertTrue("refCount: " + store.refCount(), store.refCount() > 0);
                InternalEngine holder;
                try {
                    holder = createEngine(store, translogPath);
                } catch (EngineCreationFailureException ex) {
                    assertEquals(store.refCount(), refCount);
                    continue;
                }
                assertEquals(store.refCount(), refCount + 1);
                final int numStarts = scaledRandomIntBetween(1, 5);
                for (int j = 0; j < numStarts; j++) {
                    try {
                        assertEquals(store.refCount(), refCount + 1);
                        holder.close();
                        holder = createEngine(store, translogPath);
                        assertEquals(store.refCount(), refCount + 1);
                    } catch (EngineCreationFailureException ex) {
                        // all is fine
                        assertEquals(store.refCount(), refCount);
                        break;
                    }
                }
                holder.close();
                assertEquals(store.refCount(), refCount);
            }
        }
    }

    @Test
    public void testSettings() {
        CodecService codecService = new CodecService(shardId.index());
        LiveIndexWriterConfig currentIndexWriterConfig = engine.getCurrentIndexWriterConfig();

        assertEquals(engine.config().getCodec().getName(), codecService.codec(codecName).getName());
        assertEquals(currentIndexWriterConfig.getCodec().getName(), codecService.codec(codecName).getName());
        assertEquals(engine.config().getIndexConcurrency(), indexConcurrency);
        assertEquals(currentIndexWriterConfig.getMaxThreadStates(), indexConcurrency);


        IndexDynamicSettingsModule settings = new IndexDynamicSettingsModule();
        assertTrue(settings.containsSetting(EngineConfig.INDEX_COMPOUND_ON_FLUSH));
        assertTrue(settings.containsSetting(EngineConfig.INDEX_GC_DELETES_SETTING));
    }

    @Test
    public void testRetryWithAutogeneratedIdWorksAndNoDuplicateDocs() throws IOException {

        ParsedDocument doc = testParsedDocument("1", "1", "test", null, -1, -1, testDocument(), B_1, null);
        boolean canHaveDuplicates = false;
        boolean autoGeneratedId = true;

        Engine.Create index = new Engine.Create(null, newUid("1"), doc, Versions.MATCH_ANY, VersionType.INTERNAL, PRIMARY, System.nanoTime(), canHaveDuplicates, autoGeneratedId);
        engine.create(index);
        assertThat(index.version(), equalTo(1l));

        index = new Engine.Create(null, newUid("1"), doc, index.version(), index.versionType().versionTypeForReplicationAndRecovery(), REPLICA, System.nanoTime(), canHaveDuplicates, autoGeneratedId);
        replicaEngine.create(index);
        assertThat(index.version(), equalTo(1l));

        canHaveDuplicates = true;
        index = new Engine.Create(null, newUid("1"), doc, Versions.MATCH_ANY, VersionType.INTERNAL, PRIMARY, System.nanoTime(), canHaveDuplicates, autoGeneratedId);
        engine.create(index);
        assertThat(index.version(), equalTo(1l));
        engine.refresh("test");
        Engine.Searcher searcher = engine.acquireSearcher("test");
        TopDocs topDocs = searcher.searcher().search(new MatchAllDocsQuery(), 10);
        assertThat(topDocs.totalHits, equalTo(1));

        index = new Engine.Create(null, newUid("1"), doc, index.version(), index.versionType().versionTypeForReplicationAndRecovery(), REPLICA, System.nanoTime(), canHaveDuplicates, autoGeneratedId);
        try {
            replicaEngine.create(index);
            fail();
        } catch (VersionConflictEngineException e) {
            // we ignore version conflicts on replicas, see TransportReplicationAction.ignoreReplicaException
        }
        replicaEngine.refresh("test");
        Engine.Searcher replicaSearcher = replicaEngine.acquireSearcher("test");
        topDocs = replicaSearcher.searcher().search(new MatchAllDocsQuery(), 10);
        assertThat(topDocs.totalHits, equalTo(1));
        searcher.close();
        replicaSearcher.close();
    }

    @Test
    public void testRetryWithAutogeneratedIdsAndWrongOrderWorksAndNoDuplicateDocs() throws IOException {

        ParsedDocument doc = testParsedDocument("1", "1", "test", null, -1, -1, testDocument(), B_1, null);
        boolean canHaveDuplicates = true;
        boolean autoGeneratedId = true;

        Engine.Create firstIndexRequest = new Engine.Create(null, newUid("1"), doc, Versions.MATCH_ANY, VersionType.INTERNAL, PRIMARY, System.nanoTime(), canHaveDuplicates, autoGeneratedId);
        engine.create(firstIndexRequest);
        assertThat(firstIndexRequest.version(), equalTo(1l));

        Engine.Create firstIndexRequestReplica = new Engine.Create(null, newUid("1"), doc, firstIndexRequest.version(), firstIndexRequest.versionType().versionTypeForReplicationAndRecovery(), REPLICA, System.nanoTime(), canHaveDuplicates, autoGeneratedId);
        replicaEngine.create(firstIndexRequestReplica);
        assertThat(firstIndexRequestReplica.version(), equalTo(1l));

        canHaveDuplicates = false;
        Engine.Create secondIndexRequest = new Engine.Create(null, newUid("1"), doc, Versions.MATCH_ANY, VersionType.INTERNAL, PRIMARY, System.nanoTime(), canHaveDuplicates, autoGeneratedId);
        try {
            engine.create(secondIndexRequest);
            fail();
        } catch (DocumentAlreadyExistsException e) {
            // we can ignore the exception. In case this happens because the retry request arrived first then this error will not be sent back anyway.
            // in any other case this is an actual error
        }
        engine.refresh("test");
        Engine.Searcher searcher = engine.acquireSearcher("test");
        TopDocs topDocs = searcher.searcher().search(new MatchAllDocsQuery(), 10);
        assertThat(topDocs.totalHits, equalTo(1));

        Engine.Create secondIndexRequestReplica = new Engine.Create(null, newUid("1"), doc, firstIndexRequest.version(), firstIndexRequest.versionType().versionTypeForReplicationAndRecovery(), REPLICA, System.nanoTime(), canHaveDuplicates, autoGeneratedId);
        try {
            replicaEngine.create(secondIndexRequestReplica);
            fail();
        } catch (VersionConflictEngineException e) {
            // we ignore version conflicts on replicas, see TransportReplicationAction.ignoreReplicaException.
        }
        replicaEngine.refresh("test");
        Engine.Searcher replicaSearcher = replicaEngine.acquireSearcher("test");
        topDocs = replicaSearcher.searcher().search(new MatchAllDocsQuery(), 10);
        assertThat(topDocs.totalHits, equalTo(1));
        searcher.close();
        replicaSearcher.close();
    }

    // #10312
    @Test
    public void testDeletesAloneCanTriggerRefresh() throws Exception {
        // Tiny indexing buffer:
        Settings indexSettings = Settings.builder().put(defaultSettings)
                .put(EngineConfig.INDEX_BUFFER_SIZE_SETTING, "1kb").build();
        IndexSettingsService indexSettingsService = new IndexSettingsService(shardId.index(), indexSettings);
        try (Store store = createStore();
             Engine engine = new InternalEngine(config(indexSettingsService, store, createTempDir(), createMergeScheduler(indexSettingsService)),
                     false)) {
            for (int i = 0; i < 100; i++) {
                String id = Integer.toString(i);
                ParsedDocument doc = testParsedDocument(id, id, "test", null, -1, -1, testDocument(), B_1, null);
                engine.index(new Engine.Index(null, newUid(id), doc, 2, VersionType.EXTERNAL, Engine.Operation.Origin.PRIMARY, System.nanoTime()));
            }

            // Force merge so we know all merges are done before we start deleting:
            engine.forceMerge(true, 1, false, false, false);

            Searcher s = engine.acquireSearcher("test");
            final long version1 = ((DirectoryReader) s.reader()).getVersion();
            s.close();
            for (int i = 0; i < 100; i++) {
                String id = Integer.toString(i);
                engine.delete(new Engine.Delete("test", id, newUid(id), 10, VersionType.EXTERNAL, Engine.Operation.Origin.PRIMARY, System.nanoTime(), false));
            }

            // We must assertBusy because refresh due to version map being full is done in background (REFRESH) thread pool:
            assertBusy(new Runnable() {
                @Override
                public void run() {
                    Searcher s2 = engine.acquireSearcher("test");
                    long version2 = ((DirectoryReader) s2.reader()).getVersion();
                    s2.close();

                    // 100 buffered deletes will easily exceed 25% of our 1 KB indexing buffer so it should have forced a refresh:
                    assertThat(version2, greaterThan(version1));
                }
            });
        }
    }

    public void testMissingTranslog() throws IOException {
        // test that we can force start the engine , even if the translog is missing.
        engine.close();
        // fake a new translog, causing the engine to point to a missing one.
        Translog translog = createTranslog();
        long id = translog.currentFileGeneration();
        translog.close();
        IOUtils.rm(translog.location().resolve(Translog.getFilename(id)));
        try {
            engine = createEngine(store, primaryTranslogDir);
            fail("engine shouldn't start without a valid translog id");
        } catch (EngineCreationFailureException ex) {
            // expected
        }
        // now it should be OK.
        IndexSettingsService indexSettingsService = new IndexSettingsService(shardId.index(), Settings.builder().put(defaultSettings)
                .put(EngineConfig.INDEX_FORCE_NEW_TRANSLOG, true).build());
        engine = createEngine(indexSettingsService, store, primaryTranslogDir, createMergeScheduler(indexSettingsService));
    }

    public void testTranslogReplayWithFailure() throws IOException {
        boolean canHaveDuplicates = true;
        boolean autoGeneratedId = true;
        final int numDocs = randomIntBetween(1, 10);
        for (int i = 0; i < numDocs; i++) {
            ParsedDocument doc = testParsedDocument(Integer.toString(i), Integer.toString(i), "test", null, -1, -1, testDocument(), new BytesArray("{}"), null);
            Engine.Create firstIndexRequest = new Engine.Create(null, newUid(Integer.toString(i)), doc, Versions.MATCH_ANY, VersionType.INTERNAL, PRIMARY, System.nanoTime(), canHaveDuplicates, autoGeneratedId);
            engine.create(firstIndexRequest);
            assertThat(firstIndexRequest.version(), equalTo(1l));
        }
        engine.refresh("test");
        try (Engine.Searcher searcher = engine.acquireSearcher("test")) {
            TopDocs topDocs = searcher.searcher().search(new MatchAllDocsQuery(), randomIntBetween(numDocs, numDocs + 10));
            assertThat(topDocs.totalHits, equalTo(numDocs));
        }
        engine.close();
        boolean recoveredButFailed = false;
        final MockDirectoryWrapper directory = DirectoryUtils.getLeaf(store.directory(), MockDirectoryWrapper.class);
        if (directory != null) {
            // since we rollback the IW we are writing the same segment files again after starting IW but MDW prevents
            // this so we have to disable the check explicitly
            directory.setPreventDoubleWrite(false);
            boolean started = false;
            final int numIters = randomIntBetween(10, 20);
            for (int i = 0; i < numIters; i++) {
                directory.setRandomIOExceptionRateOnOpen(randomDouble());
                directory.setRandomIOExceptionRate(randomDouble());
                directory.setFailOnOpenInput(randomBoolean());
                directory.setAllowRandomFileNotFoundException(randomBoolean());
                try {
                    engine = createEngine(store, primaryTranslogDir);
                    started = true;
                    break;
                } catch (EngineCreationFailureException ex) {
                }
            }

            directory.setRandomIOExceptionRateOnOpen(0.0);
            directory.setRandomIOExceptionRate(0.0);
            directory.setFailOnOpenInput(false);
            directory.setAllowRandomFileNotFoundException(false);
            if (started == false) {
                engine = createEngine(store, primaryTranslogDir);
            }
        } else {
            // no mock directory, no fun.
            engine = createEngine(store, primaryTranslogDir);
        }
        try (Engine.Searcher searcher = engine.acquireSearcher("test")) {
            TopDocs topDocs = searcher.searcher().search(new MatchAllDocsQuery(), randomIntBetween(numDocs, numDocs + 10));
            assertThat(topDocs.totalHits, equalTo(numDocs));
        }
    }

    @Test
    public void testSkipTranslogReplay() throws IOException {
        boolean canHaveDuplicates = true;
        boolean autoGeneratedId = true;
        final int numDocs = randomIntBetween(1, 10);
        for (int i = 0; i < numDocs; i++) {
            ParsedDocument doc = testParsedDocument(Integer.toString(i), Integer.toString(i), "test", null, -1, -1, testDocument(), new BytesArray("{}"), null);
            Engine.Create firstIndexRequest = new Engine.Create(null, newUid(Integer.toString(i)), doc, Versions.MATCH_ANY, VersionType.INTERNAL, PRIMARY, System.nanoTime(), canHaveDuplicates, autoGeneratedId);
            engine.create(firstIndexRequest);
            assertThat(firstIndexRequest.version(), equalTo(1l));
        }
        engine.refresh("test");
        try (Engine.Searcher searcher = engine.acquireSearcher("test")) {
            TopDocs topDocs = searcher.searcher().search(new MatchAllDocsQuery(), randomIntBetween(numDocs, numDocs + 10));
            assertThat(topDocs.totalHits, equalTo(numDocs));
        }
        final MockDirectoryWrapper directory = DirectoryUtils.getLeaf(store.directory(), MockDirectoryWrapper.class);
        if (directory != null) {
            // since we rollback the IW we are writing the same segment files again after starting IW but MDW prevents
            // this so we have to disable the check explicitly
            directory.setPreventDoubleWrite(false);
        }
        engine.close();
        engine = new InternalEngine(engine.config(), true);

        try (Engine.Searcher searcher = engine.acquireSearcher("test")) {
            TopDocs topDocs = searcher.searcher().search(new MatchAllDocsQuery(), randomIntBetween(numDocs, numDocs + 10));
            assertThat(topDocs.totalHits, equalTo(0));
        }

    }

    private Mapping dynamicUpdate() {
        BuilderContext context = new BuilderContext(Settings.EMPTY, new ContentPath());
        final RootObjectMapper root = MapperBuilders.rootObject("some_type").build(context);
        return new Mapping(Version.CURRENT, root, new RootMapper[0], new Mapping.SourceTransform[0], ImmutableMap.<String, Object>of());
    }

    public void testTranslogReplay() throws IOException {
        boolean canHaveDuplicates = true;
        boolean autoGeneratedId = true;
        final int numDocs = randomIntBetween(1, 10);
        for (int i = 0; i < numDocs; i++) {
            ParsedDocument doc = testParsedDocument(Integer.toString(i), Integer.toString(i), "test", null, -1, -1, testDocument(), new BytesArray("{}"), null);
            Engine.Create firstIndexRequest = new Engine.Create(null, newUid(Integer.toString(i)), doc, Versions.MATCH_ANY, VersionType.INTERNAL, PRIMARY, System.nanoTime(), canHaveDuplicates, autoGeneratedId);
            engine.create(firstIndexRequest);
            assertThat(firstIndexRequest.version(), equalTo(1l));
        }
        engine.refresh("test");
        try (Engine.Searcher searcher = engine.acquireSearcher("test")) {
            TopDocs topDocs = searcher.searcher().search(new MatchAllDocsQuery(), randomIntBetween(numDocs, numDocs + 10));
            assertThat(topDocs.totalHits, equalTo(numDocs));
        }
        final MockDirectoryWrapper directory = DirectoryUtils.getLeaf(store.directory(), MockDirectoryWrapper.class);
        if (directory != null) {
            // since we rollback the IW we are writing the same segment files again after starting IW but MDW prevents
            // this so we have to disable the check explicitly
            directory.setPreventDoubleWrite(false);
        }

        TranslogHandler parser = (TranslogHandler) engine.config().getTranslogRecoveryPerformer();
        parser.mappingUpdate = dynamicUpdate();

        engine.close();
        engine = new InternalEngine(engine.config(), false); // we need to reuse the engine config unless the parser.mappingModified won't work

        try (Engine.Searcher searcher = engine.acquireSearcher("test")) {
            TopDocs topDocs = searcher.searcher().search(new MatchAllDocsQuery(), randomIntBetween(numDocs, numDocs + 10));
            assertThat(topDocs.totalHits, equalTo(numDocs));
        }
        parser = (TranslogHandler) engine.config().getTranslogRecoveryPerformer();
        assertEquals(numDocs, parser.recoveredOps.get());
        if (parser.mappingUpdate != null) {
            assertEquals(1, parser.getRecoveredTypes().size());
            assertTrue(parser.getRecoveredTypes().containsKey("test"));
        } else {
            assertEquals(0, parser.getRecoveredTypes().size());
        }

        engine.close();
        engine = createEngine(store, primaryTranslogDir);
        try (Engine.Searcher searcher = engine.acquireSearcher("test")) {
            TopDocs topDocs = searcher.searcher().search(new MatchAllDocsQuery(), randomIntBetween(numDocs, numDocs + 10));
            assertThat(topDocs.totalHits, equalTo(numDocs));
        }
        parser = (TranslogHandler) engine.config().getTranslogRecoveryPerformer();
        assertEquals(0, parser.recoveredOps.get());

        final boolean flush = randomBoolean();
        int randomId = randomIntBetween(numDocs + 1, numDocs + 10);
        String uuidValue = "test#" + Integer.toString(randomId);
        ParsedDocument doc = testParsedDocument(uuidValue, Integer.toString(randomId), "test", null, -1, -1, testDocument(), new BytesArray("{}"), null);
        Engine.Create firstIndexRequest = new Engine.Create(null, newUid(uuidValue), doc, 1, VersionType.EXTERNAL, PRIMARY, System.nanoTime(), canHaveDuplicates, autoGeneratedId);
        engine.create(firstIndexRequest);
        assertThat(firstIndexRequest.version(), equalTo(1l));
        if (flush) {
            engine.flush();
        }

        doc = testParsedDocument(uuidValue, Integer.toString(randomId), "test", null, -1, -1, testDocument(), new BytesArray("{}"), null);
        Engine.Index idxRequest = new Engine.Index(null, newUid(uuidValue), doc, 2, VersionType.EXTERNAL, PRIMARY, System.nanoTime());
        engine.index(idxRequest);
        engine.refresh("test");
        assertThat(idxRequest.version(), equalTo(2l));
        try (Engine.Searcher searcher = engine.acquireSearcher("test")) {
            TopDocs topDocs = searcher.searcher().search(new MatchAllDocsQuery(), numDocs + 1);
            assertThat(topDocs.totalHits, equalTo(numDocs + 1));
        }

        engine.close();
        engine = createEngine(store, primaryTranslogDir);
        try (Engine.Searcher searcher = engine.acquireSearcher("test")) {
            TopDocs topDocs = searcher.searcher().search(new MatchAllDocsQuery(), numDocs + 1);
            assertThat(topDocs.totalHits, equalTo(numDocs + 1));
        }
        parser = (TranslogHandler) engine.config().getTranslogRecoveryPerformer();
        assertEquals(flush ? 1 : 2, parser.recoveredOps.get());
        engine.delete(new Engine.Delete("test", Integer.toString(randomId), newUid(uuidValue)));
        if (randomBoolean()) {
            engine.refresh("test");
        } else {
            engine.close();
            engine = createEngine(store, primaryTranslogDir);
        }
        try (Engine.Searcher searcher = engine.acquireSearcher("test")) {
            TopDocs topDocs = searcher.searcher().search(new MatchAllDocsQuery(), numDocs);
            assertThat(topDocs.totalHits, equalTo(numDocs));
        }
    }

    public static class TranslogHandler extends TranslogRecoveryPerformer {

        private final DocumentMapper docMapper;
        public Mapping mappingUpdate = null;

        public final AtomicInteger recoveredOps = new AtomicInteger(0);

        public TranslogHandler(String indexName) {
            super(new ShardId("test", 0), null, new MapperAnalyzer(null), null, null, null);
            Settings settings = Settings.settingsBuilder().put(IndexMetaData.SETTING_VERSION_CREATED, Version.CURRENT).build();
            RootObjectMapper.Builder rootBuilder = new RootObjectMapper.Builder("test");
            Index index = new Index(indexName);
            AnalysisService analysisService = new AnalysisService(index, settings);
            SimilarityLookupService similarityLookupService = new SimilarityLookupService(index, settings);
            MapperService mapperService = new MapperService(index, settings, analysisService, null, similarityLookupService, null);
            DocumentMapper.Builder b = new DocumentMapper.Builder(indexName, settings, rootBuilder);
            DocumentMapperParser parser = new DocumentMapperParser(index, settings, mapperService, analysisService, similarityLookupService, null);
            this.docMapper = b.build(mapperService, parser);

        }

        @Override
        protected Tuple<DocumentMapper, Mapping> docMapper(String type) {
            return new Tuple<>(docMapper, mappingUpdate);
        }

        @Override
        protected void operationProcessed() {
            recoveredOps.incrementAndGet();
        }
    }

    public void testRecoverFromForeignTranslog() throws IOException {
        boolean canHaveDuplicates = true;
        boolean autoGeneratedId = true;
        final int numDocs = randomIntBetween(1, 10);
        for (int i = 0; i < numDocs; i++) {
            ParsedDocument doc = testParsedDocument(Integer.toString(i), Integer.toString(i), "test", null, -1, -1, testDocument(), new BytesArray("{}"), null);
            Engine.Create firstIndexRequest = new Engine.Create(null, newUid(Integer.toString(i)), doc, Versions.MATCH_ANY, VersionType.INTERNAL, PRIMARY, System.nanoTime(), canHaveDuplicates, autoGeneratedId);
            engine.create(firstIndexRequest);
            assertThat(firstIndexRequest.version(), equalTo(1l));
        }
        engine.refresh("test");
        try (Engine.Searcher searcher = engine.acquireSearcher("test")) {
            TopDocs topDocs = searcher.searcher().search(new MatchAllDocsQuery(), randomIntBetween(numDocs, numDocs + 10));
            assertThat(topDocs.totalHits, equalTo(numDocs));
        }
        final MockDirectoryWrapper directory = DirectoryUtils.getLeaf(store.directory(), MockDirectoryWrapper.class);
        if (directory != null) {
            // since we rollback the IW we are writing the same segment files again after starting IW but MDW prevents
            // this so we have to disable the check explicitly
            directory.setPreventDoubleWrite(false);
        }
        Translog.TranslogGeneration generation = engine.getTranslog().getGeneration();
        engine.close();

        Translog translog = new Translog(new TranslogConfig(shardId, createTempDir(), Settings.EMPTY, Translog.Durabilty.REQUEST, BigArrays.NON_RECYCLING_INSTANCE, threadPool));
        translog.add(new Translog.Create("test", "SomeBogusId", "{}".getBytes(Charset.forName("UTF-8"))));
        assertEquals(generation.translogFileGeneration, translog.currentFileGeneration());
        translog.close();

        EngineConfig config = engine.config();
        /* create a TranslogConfig that has been created with a different UUID */
        TranslogConfig translogConfig = new TranslogConfig(shardId, translog.location(), config.getIndexSettings(), Translog.Durabilty.REQUEST, BigArrays.NON_RECYCLING_INSTANCE, threadPool);

        EngineConfig brokenConfig = new EngineConfig(shardId, threadPool, config.getIndexingService(), config.getIndexSettingsService()
                , null, store, createSnapshotDeletionPolicy(), createMergePolicy(), config.getMergeScheduler(),
                config.getAnalyzer(), config.getSimilarity(), new CodecService(shardId.index()), config.getFailedEngineListener()
        , config.getTranslogRecoveryPerformer(), IndexSearcher.getDefaultQueryCache(), IndexSearcher.getDefaultQueryCachingPolicy(), translogConfig);

        try {
            new InternalEngine(brokenConfig, false);
            fail("translog belongs to a different engine");
        } catch (EngineCreationFailureException ex) {
        }

        engine = createEngine(store, primaryTranslogDir); // and recover again!
        try (Engine.Searcher searcher = engine.acquireSearcher("test")) {
            TopDocs topDocs = searcher.searcher().search(new MatchAllDocsQuery(), randomIntBetween(numDocs, numDocs + 10));
            assertThat(topDocs.totalHits, equalTo(numDocs));
        }
    }
}


File: core/src/test/java/org/elasticsearch/index/engine/ShadowEngineTests.java
/*
 * Licensed to Elasticsearch under one or more contributor
 * license agreements. See the NOTICE file distributed with
 * this work for additional information regarding copyright
 * ownership. Elasticsearch licenses this file to you under
 * the Apache License, Version 2.0 (the "License"); you may
 * not use this file except in compliance with the License.
 * You may obtain a copy of the License at
 *
 *    http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing,
 * software distributed under the License is distributed on an
 * "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY
 * KIND, either express or implied.  See the License for the
 * specific language governing permissions and limitations
 * under the License.
 */

package org.elasticsearch.index.engine;

import org.apache.lucene.codecs.Codec;
import org.apache.lucene.document.Field;
import org.apache.lucene.document.NumericDocValuesField;
import org.apache.lucene.document.TextField;
import org.apache.lucene.index.IndexDeletionPolicy;
import org.apache.lucene.index.IndexWriterConfig;
import org.apache.lucene.index.LiveIndexWriterConfig;
import org.apache.lucene.index.Term;
import org.apache.lucene.search.IndexSearcher;
import org.apache.lucene.search.TermQuery;
import org.apache.lucene.store.Directory;
import org.apache.lucene.store.MockDirectoryWrapper;
import org.apache.lucene.util.IOUtils;
import org.elasticsearch.Version;
import org.elasticsearch.cluster.metadata.IndexMetaData;
import org.elasticsearch.common.Nullable;
import org.elasticsearch.common.bytes.BytesArray;
import org.elasticsearch.common.bytes.BytesReference;
import org.elasticsearch.common.lucene.Lucene;
import org.elasticsearch.common.settings.Settings;
import org.elasticsearch.common.util.BigArrays;
import org.elasticsearch.index.Index;
import org.elasticsearch.index.codec.CodecService;
import org.elasticsearch.index.deletionpolicy.KeepOnlyLastDeletionPolicy;
import org.elasticsearch.index.deletionpolicy.SnapshotDeletionPolicy;
import org.elasticsearch.index.indexing.ShardIndexingService;
import org.elasticsearch.index.indexing.slowlog.ShardSlowLogIndexingService;
import org.elasticsearch.index.mapper.Mapping;
import org.elasticsearch.index.mapper.ParseContext;
import org.elasticsearch.index.mapper.ParsedDocument;
import org.elasticsearch.index.mapper.internal.SourceFieldMapper;
import org.elasticsearch.index.mapper.internal.UidFieldMapper;
import org.elasticsearch.index.merge.policy.LogByteSizeMergePolicyProvider;
import org.elasticsearch.index.merge.policy.MergePolicyProvider;
import org.elasticsearch.index.merge.scheduler.ConcurrentMergeSchedulerProvider;
import org.elasticsearch.index.merge.scheduler.MergeSchedulerProvider;
import org.elasticsearch.index.settings.IndexSettingsService;
import org.elasticsearch.index.shard.ShardId;
import org.elasticsearch.index.shard.ShardUtils;
import org.elasticsearch.index.store.DirectoryService;
import org.elasticsearch.index.store.DirectoryUtils;
import org.elasticsearch.index.store.Store;
import org.elasticsearch.index.translog.Translog;
import org.elasticsearch.index.translog.TranslogConfig;
import org.elasticsearch.test.DummyShardLock;
import org.elasticsearch.test.ElasticsearchTestCase;
import org.elasticsearch.threadpool.ThreadPool;
import org.hamcrest.MatcherAssert;
import org.junit.After;
import org.junit.Before;
import org.junit.Test;

import java.io.IOException;
import java.nio.file.Path;
import java.util.Arrays;
import java.util.List;
import java.util.concurrent.CountDownLatch;
import java.util.concurrent.atomic.AtomicBoolean;

import static org.elasticsearch.common.settings.Settings.Builder.EMPTY_SETTINGS;
import static org.hamcrest.Matchers.*;

/**
 * TODO: document me!
 */
public class ShadowEngineTests extends ElasticsearchTestCase {

    protected final ShardId shardId = new ShardId(new Index("index"), 1);

    protected ThreadPool threadPool;

    private Store store;
    private Store storeReplica;


    protected Engine primaryEngine;
    protected Engine replicaEngine;

    private Settings defaultSettings;
    private int indexConcurrency;
    private String codecName;
    private Path dirPath;

    @Override
    @Before
    public void setUp() throws Exception {
        super.setUp();
        CodecService codecService = new CodecService(shardId.index());
        indexConcurrency = randomIntBetween(1, 20);
        String name = Codec.getDefault().getName();
        if (Arrays.asList(codecService.availableCodecs()).contains(name)) {
            // some codecs are read only so we only take the ones that we have in the service and randomly
            // selected by lucene test case.
            codecName = name;
        } else {
            codecName = "default";
        }
        defaultSettings = Settings.builder()
                .put(EngineConfig.INDEX_COMPOUND_ON_FLUSH, randomBoolean())
                .put(EngineConfig.INDEX_GC_DELETES_SETTING, "1h") // make sure this doesn't kick in on us
                .put(EngineConfig.INDEX_CODEC_SETTING, codecName)
                .put(EngineConfig.INDEX_CONCURRENCY_SETTING, indexConcurrency)
                .build(); // TODO randomize more settings
        threadPool = new ThreadPool(getClass().getName());
        dirPath = createTempDir();
        store = createStore(dirPath);
        storeReplica = createStore(dirPath);
        Lucene.cleanLuceneIndex(store.directory());
        Lucene.cleanLuceneIndex(storeReplica.directory());
        primaryEngine = createInternalEngine(store, createTempDir("translog-primary"));
        LiveIndexWriterConfig currentIndexWriterConfig = ((InternalEngine)primaryEngine).getCurrentIndexWriterConfig();

        assertEquals(primaryEngine.config().getCodec().getName(), codecService.codec(codecName).getName());
        assertEquals(currentIndexWriterConfig.getCodec().getName(), codecService.codec(codecName).getName());
        if (randomBoolean()) {
            primaryEngine.config().setEnableGcDeletes(false);
        }

        replicaEngine = createShadowEngine(storeReplica);

        assertEquals(replicaEngine.config().getCodec().getName(), codecService.codec(codecName).getName());
        if (randomBoolean()) {
            replicaEngine.config().setEnableGcDeletes(false);
        }
    }

    @Override
    @After
    public void tearDown() throws Exception {
        super.tearDown();
        replicaEngine.close();
        storeReplica.close();
        primaryEngine.close();
        store.close();
        terminate(threadPool);
    }

    private ParseContext.Document testDocumentWithTextField() {
        ParseContext.Document document = testDocument();
        document.add(new TextField("value", "test", Field.Store.YES));
        return document;
    }

    private ParseContext.Document testDocument() {
        return new ParseContext.Document();
    }


    private ParsedDocument testParsedDocument(String uid, String id, String type, String routing, long timestamp, long ttl, ParseContext.Document document, BytesReference source, Mapping mappingsUpdate) {
        Field uidField = new Field("_uid", uid, UidFieldMapper.Defaults.FIELD_TYPE);
        Field versionField = new NumericDocValuesField("_version", 0);
        document.add(uidField);
        document.add(versionField);
        return new ParsedDocument(uidField, versionField, id, type, routing, timestamp, ttl, Arrays.asList(document), source, mappingsUpdate);
    }

    protected Store createStore(Path p) throws IOException {
        return createStore(newMockFSDirectory(p));
    }

    protected Store createStore(final Directory directory) throws IOException {
        final DirectoryService directoryService = new DirectoryService(shardId, EMPTY_SETTINGS) {
            @Override
            public Directory newDirectory() throws IOException {
                return directory;
            }

            @Override
            public long throttleTimeInNanos() {
                return 0;
            }
        };
        return new Store(shardId, EMPTY_SETTINGS, directoryService, new DummyShardLock(shardId));
    }

    protected IndexDeletionPolicy createIndexDeletionPolicy() {
        return new KeepOnlyLastDeletionPolicy(shardId, EMPTY_SETTINGS);
    }

    protected SnapshotDeletionPolicy createSnapshotDeletionPolicy() {
        return new SnapshotDeletionPolicy(createIndexDeletionPolicy());
    }

    protected MergePolicyProvider<?> createMergePolicy() {
        return new LogByteSizeMergePolicyProvider(store, new IndexSettingsService(new Index("test"), EMPTY_SETTINGS));
    }

    protected MergeSchedulerProvider createMergeScheduler(IndexSettingsService indexSettingsService) {
        return new ConcurrentMergeSchedulerProvider(shardId, EMPTY_SETTINGS, threadPool, indexSettingsService);
    }

    protected ShadowEngine createShadowEngine(Store store) {
        IndexSettingsService indexSettingsService = new IndexSettingsService(shardId.index(), Settings.builder().put(defaultSettings).put(IndexMetaData.SETTING_VERSION_CREATED, Version.CURRENT).build());
        return createShadowEngine(indexSettingsService, store, createMergeScheduler(indexSettingsService));
    }

    protected InternalEngine createInternalEngine(Store store, Path translogPath) {
        IndexSettingsService indexSettingsService = new IndexSettingsService(shardId.index(), Settings.builder().put(defaultSettings).put(IndexMetaData.SETTING_VERSION_CREATED, Version.CURRENT).build());
        return createInternalEngine(indexSettingsService, store, translogPath, createMergeScheduler(indexSettingsService));
    }

    protected ShadowEngine createShadowEngine(IndexSettingsService indexSettingsService, Store store, MergeSchedulerProvider mergeSchedulerProvider) {
        return new ShadowEngine(config(indexSettingsService, store, null, mergeSchedulerProvider));
    }

    protected InternalEngine createInternalEngine(IndexSettingsService indexSettingsService, Store store, Path translogPath, MergeSchedulerProvider mergeSchedulerProvider) {
        return new InternalEngine(config(indexSettingsService, store, translogPath, mergeSchedulerProvider), true);
    }

    public EngineConfig config(IndexSettingsService indexSettingsService, Store store, Path translogPath, MergeSchedulerProvider mergeSchedulerProvider) {
        IndexWriterConfig iwc = newIndexWriterConfig();
        TranslogConfig translogConfig = new TranslogConfig(shardId, translogPath, indexSettingsService.getSettings(), Translog.Durabilty.REQUEST, BigArrays.NON_RECYCLING_INSTANCE, threadPool);
        EngineConfig config = new EngineConfig(shardId, threadPool, new ShardIndexingService(shardId, EMPTY_SETTINGS, new ShardSlowLogIndexingService(shardId, EMPTY_SETTINGS, indexSettingsService)), indexSettingsService
                , null, store, createSnapshotDeletionPolicy(), createMergePolicy(), mergeSchedulerProvider,
                iwc.getAnalyzer(), iwc.getSimilarity() , new CodecService(shardId.index()), new Engine.FailedEngineListener() {
            @Override
            public void onFailedEngine(ShardId shardId, String reason, @Nullable Throwable t) {
                // we don't need to notify anybody in this test
        }}, null, IndexSearcher.getDefaultQueryCache(), IndexSearcher.getDefaultQueryCachingPolicy(), translogConfig);
        return config;
    }

    protected Term newUid(String id) {
        return new Term("_uid", id);
    }

    protected static final BytesReference B_1 = new BytesArray(new byte[]{1});
    protected static final BytesReference B_2 = new BytesArray(new byte[]{2});
    protected static final BytesReference B_3 = new BytesArray(new byte[]{3});

    public void testCommitStats() {
        // create a doc and refresh
        ParsedDocument doc = testParsedDocument("1", "1", "test", null, -1, -1, testDocumentWithTextField(), B_1, null);
        primaryEngine.create(new Engine.Create(null, newUid("1"), doc));

        CommitStats stats1 = replicaEngine.commitStats();
        assertThat(stats1.getGeneration(), greaterThan(0l));
        assertThat(stats1.getId(), notNullValue());
        assertThat(stats1.getUserData(), hasKey(Translog.TRANSLOG_GENERATION_KEY));

        // flush the primary engine
        primaryEngine.flush();
        // flush on replica to make flush visible
        replicaEngine.flush();

        CommitStats stats2 = replicaEngine.commitStats();
        assertThat(stats2.getGeneration(), greaterThan(stats1.getGeneration()));
        assertThat(stats2.getId(), notNullValue());
        assertThat(stats2.getId(), not(equalTo(stats1.getId())));
        assertThat(stats2.getUserData(), hasKey(Translog.TRANSLOG_GENERATION_KEY));
        assertThat(stats2.getUserData(), hasKey(Translog.TRANSLOG_UUID_KEY));
        assertThat(stats2.getUserData().get(Translog.TRANSLOG_GENERATION_KEY), not(equalTo(stats1.getUserData().get(Translog.TRANSLOG_GENERATION_KEY))));
        assertThat(stats2.getUserData().get(Translog.TRANSLOG_UUID_KEY), equalTo(stats1.getUserData().get(Translog.TRANSLOG_UUID_KEY)));
    }


    @Test
    public void testSegments() throws Exception {
        List<Segment> segments = primaryEngine.segments(false);
        assertThat(segments.isEmpty(), equalTo(true));
        assertThat(primaryEngine.segmentsStats().getCount(), equalTo(0l));
        assertThat(primaryEngine.segmentsStats().getMemoryInBytes(), equalTo(0l));
        final boolean defaultCompound = defaultSettings.getAsBoolean(EngineConfig.INDEX_COMPOUND_ON_FLUSH, true);

        // create a doc and refresh
        ParsedDocument doc = testParsedDocument("1", "1", "test", null, -1, -1, testDocumentWithTextField(), B_1, null);
        primaryEngine.create(new Engine.Create(null, newUid("1"), doc));

        ParsedDocument doc2 = testParsedDocument("2", "2", "test", null, -1, -1, testDocumentWithTextField(), B_2, null);
        primaryEngine.create(new Engine.Create(null, newUid("2"), doc2));
        primaryEngine.refresh("test");

        segments = primaryEngine.segments(false);
        assertThat(segments.size(), equalTo(1));
        SegmentsStats stats = primaryEngine.segmentsStats();
        assertThat(stats.getCount(), equalTo(1l));
        assertThat(stats.getTermsMemoryInBytes(), greaterThan(0l));
        assertThat(stats.getStoredFieldsMemoryInBytes(), greaterThan(0l));
        assertThat(stats.getTermVectorsMemoryInBytes(), equalTo(0l));
        assertThat(stats.getNormsMemoryInBytes(), greaterThan(0l));
        assertThat(stats.getDocValuesMemoryInBytes(), greaterThan(0l));
        assertThat(segments.get(0).isCommitted(), equalTo(false));
        assertThat(segments.get(0).isSearch(), equalTo(true));
        assertThat(segments.get(0).getNumDocs(), equalTo(2));
        assertThat(segments.get(0).getDeletedDocs(), equalTo(0));
        assertThat(segments.get(0).isCompound(), equalTo(defaultCompound));
        assertThat(segments.get(0).ramTree, nullValue());

        // Check that the replica sees nothing
        segments = replicaEngine.segments(false);
        assertThat(segments.size(), equalTo(0));
        stats = replicaEngine.segmentsStats();
        assertThat(stats.getCount(), equalTo(0l));
        assertThat(stats.getTermsMemoryInBytes(), equalTo(0l));
        assertThat(stats.getStoredFieldsMemoryInBytes(), equalTo(0l));
        assertThat(stats.getTermVectorsMemoryInBytes(), equalTo(0l));
        assertThat(stats.getNormsMemoryInBytes(), equalTo(0l));
        assertThat(stats.getDocValuesMemoryInBytes(), equalTo(0l));
        assertThat(segments.size(), equalTo(0));

        // flush the primary engine
        primaryEngine.flush();
        // refresh the replica
        replicaEngine.refresh("tests");

        // Check that the primary AND replica sees segments now
        segments = primaryEngine.segments(false);
        assertThat(segments.size(), equalTo(1));
        assertThat(primaryEngine.segmentsStats().getCount(), equalTo(1l));
        assertThat(segments.get(0).isCommitted(), equalTo(true));
        assertThat(segments.get(0).isSearch(), equalTo(true));
        assertThat(segments.get(0).getNumDocs(), equalTo(2));
        assertThat(segments.get(0).getDeletedDocs(), equalTo(0));
        assertThat(segments.get(0).isCompound(), equalTo(defaultCompound));

        segments = replicaEngine.segments(false);
        assertThat(segments.size(), equalTo(1));
        assertThat(replicaEngine.segmentsStats().getCount(), equalTo(1l));
        assertThat(segments.get(0).isCommitted(), equalTo(true));
        assertThat(segments.get(0).isSearch(), equalTo(true));
        assertThat(segments.get(0).getNumDocs(), equalTo(2));
        assertThat(segments.get(0).getDeletedDocs(), equalTo(0));
        assertThat(segments.get(0).isCompound(), equalTo(defaultCompound));


        primaryEngine.config().setCompoundOnFlush(false);

        ParsedDocument doc3 = testParsedDocument("3", "3", "test", null, -1, -1, testDocumentWithTextField(), B_3, null);
        primaryEngine.create(new Engine.Create(null, newUid("3"), doc3));
        primaryEngine.refresh("test");

        segments = primaryEngine.segments(false);
        assertThat(segments.size(), equalTo(2));
        assertThat(primaryEngine.segmentsStats().getCount(), equalTo(2l));
        assertThat(primaryEngine.segmentsStats().getTermsMemoryInBytes(), greaterThan(stats.getTermsMemoryInBytes()));
        assertThat(primaryEngine.segmentsStats().getStoredFieldsMemoryInBytes(), greaterThan(stats.getStoredFieldsMemoryInBytes()));
        assertThat(primaryEngine.segmentsStats().getTermVectorsMemoryInBytes(), equalTo(0l));
        assertThat(primaryEngine.segmentsStats().getNormsMemoryInBytes(), greaterThan(stats.getNormsMemoryInBytes()));
        assertThat(primaryEngine.segmentsStats().getDocValuesMemoryInBytes(), greaterThan(stats.getDocValuesMemoryInBytes()));
        assertThat(segments.get(0).getGeneration() < segments.get(1).getGeneration(), equalTo(true));
        assertThat(segments.get(0).isCommitted(), equalTo(true));
        assertThat(segments.get(0).isSearch(), equalTo(true));
        assertThat(segments.get(0).getNumDocs(), equalTo(2));
        assertThat(segments.get(0).getDeletedDocs(), equalTo(0));
        assertThat(segments.get(0).isCompound(), equalTo(defaultCompound));
        assertThat(segments.get(1).isCommitted(), equalTo(false));
        assertThat(segments.get(1).isSearch(), equalTo(true));
        assertThat(segments.get(1).getNumDocs(), equalTo(1));
        assertThat(segments.get(1).getDeletedDocs(), equalTo(0));
        assertThat(segments.get(1).isCompound(), equalTo(false));

        // Make visible to shadow replica
        primaryEngine.flush();
        replicaEngine.refresh("test");

        segments = replicaEngine.segments(false);
        assertThat(segments.size(), equalTo(2));
        assertThat(replicaEngine.segmentsStats().getCount(), equalTo(2l));
        assertThat(replicaEngine.segmentsStats().getTermsMemoryInBytes(), greaterThan(stats.getTermsMemoryInBytes()));
        assertThat(replicaEngine.segmentsStats().getStoredFieldsMemoryInBytes(), greaterThan(stats.getStoredFieldsMemoryInBytes()));
        assertThat(replicaEngine.segmentsStats().getTermVectorsMemoryInBytes(), equalTo(0l));
        assertThat(replicaEngine.segmentsStats().getNormsMemoryInBytes(), greaterThan(stats.getNormsMemoryInBytes()));
        assertThat(replicaEngine.segmentsStats().getDocValuesMemoryInBytes(), greaterThan(stats.getDocValuesMemoryInBytes()));
        assertThat(segments.get(0).getGeneration() < segments.get(1).getGeneration(), equalTo(true));
        assertThat(segments.get(0).isCommitted(), equalTo(true));
        assertThat(segments.get(0).isSearch(), equalTo(true));
        assertThat(segments.get(0).getNumDocs(), equalTo(2));
        assertThat(segments.get(0).getDeletedDocs(), equalTo(0));
        assertThat(segments.get(0).isCompound(), equalTo(defaultCompound));
        assertThat(segments.get(1).isCommitted(), equalTo(true));
        assertThat(segments.get(1).isSearch(), equalTo(true));
        assertThat(segments.get(1).getNumDocs(), equalTo(1));
        assertThat(segments.get(1).getDeletedDocs(), equalTo(0));
        assertThat(segments.get(1).isCompound(), equalTo(false));

        primaryEngine.delete(new Engine.Delete("test", "1", newUid("1")));
        primaryEngine.refresh("test");

        segments = primaryEngine.segments(false);
        assertThat(segments.size(), equalTo(2));
        assertThat(primaryEngine.segmentsStats().getCount(), equalTo(2l));
        assertThat(segments.get(0).getGeneration() < segments.get(1).getGeneration(), equalTo(true));
        assertThat(segments.get(0).isCommitted(), equalTo(true));
        assertThat(segments.get(0).isSearch(), equalTo(true));
        assertThat(segments.get(0).getNumDocs(), equalTo(1));
        assertThat(segments.get(0).getDeletedDocs(), equalTo(1));
        assertThat(segments.get(0).isCompound(), equalTo(defaultCompound));
        assertThat(segments.get(1).isCommitted(), equalTo(true));
        assertThat(segments.get(1).isSearch(), equalTo(true));
        assertThat(segments.get(1).getNumDocs(), equalTo(1));
        assertThat(segments.get(1).getDeletedDocs(), equalTo(0));
        assertThat(segments.get(1).isCompound(), equalTo(false));

        // Make visible to shadow replica
        primaryEngine.flush();
        replicaEngine.refresh("test");

        primaryEngine.config().setCompoundOnFlush(true);
        ParsedDocument doc4 = testParsedDocument("4", "4", "test", null, -1, -1, testDocumentWithTextField(), B_3, null);
        primaryEngine.create(new Engine.Create(null, newUid("4"), doc4));
        primaryEngine.refresh("test");

        segments = primaryEngine.segments(false);
        assertThat(segments.size(), equalTo(3));
        assertThat(primaryEngine.segmentsStats().getCount(), equalTo(3l));
        assertThat(segments.get(0).getGeneration() < segments.get(1).getGeneration(), equalTo(true));
        assertThat(segments.get(0).isCommitted(), equalTo(true));
        assertThat(segments.get(0).isSearch(), equalTo(true));
        assertThat(segments.get(0).getNumDocs(), equalTo(1));
        assertThat(segments.get(0).getDeletedDocs(), equalTo(1));
        assertThat(segments.get(0).isCompound(), equalTo(defaultCompound));

        assertThat(segments.get(1).isCommitted(), equalTo(true));
        assertThat(segments.get(1).isSearch(), equalTo(true));
        assertThat(segments.get(1).getNumDocs(), equalTo(1));
        assertThat(segments.get(1).getDeletedDocs(), equalTo(0));
        assertThat(segments.get(1).isCompound(), equalTo(false));

        assertThat(segments.get(2).isCommitted(), equalTo(false));
        assertThat(segments.get(2).isSearch(), equalTo(true));
        assertThat(segments.get(2).getNumDocs(), equalTo(1));
        assertThat(segments.get(2).getDeletedDocs(), equalTo(0));
        assertThat(segments.get(2).isCompound(), equalTo(true));
    }

    @Test
    public void testVerboseSegments() throws Exception {
        List<Segment> segments = primaryEngine.segments(true);
        assertThat(segments.isEmpty(), equalTo(true));

        ParsedDocument doc = testParsedDocument("1", "1", "test", null, -1, -1, testDocumentWithTextField(), B_1, null);
        primaryEngine.create(new Engine.Create(null, newUid("1"), doc));
        primaryEngine.refresh("test");

        segments = primaryEngine.segments(true);
        assertThat(segments.size(), equalTo(1));
        assertThat(segments.get(0).ramTree, notNullValue());

        ParsedDocument doc2 = testParsedDocument("2", "2", "test", null, -1, -1, testDocumentWithTextField(), B_2, null);
        primaryEngine.create(new Engine.Create(null, newUid("2"), doc2));
        primaryEngine.refresh("test");
        ParsedDocument doc3 = testParsedDocument("3", "3", "test", null, -1, -1, testDocumentWithTextField(), B_3, null);
        primaryEngine.create(new Engine.Create(null, newUid("3"), doc3));
        primaryEngine.refresh("test");

        segments = primaryEngine.segments(true);
        assertThat(segments.size(), equalTo(3));
        assertThat(segments.get(0).ramTree, notNullValue());
        assertThat(segments.get(1).ramTree, notNullValue());
        assertThat(segments.get(2).ramTree, notNullValue());

        // Now make the changes visible to the replica
        primaryEngine.flush();
        replicaEngine.refresh("test");

        segments = replicaEngine.segments(true);
        assertThat(segments.size(), equalTo(3));
        assertThat(segments.get(0).ramTree, notNullValue());
        assertThat(segments.get(1).ramTree, notNullValue());
        assertThat(segments.get(2).ramTree, notNullValue());

    }

    @Test
    public void testShadowEngineIgnoresWriteOperations() throws Exception {
        // create a document
        ParseContext.Document document = testDocumentWithTextField();
        document.add(new Field(SourceFieldMapper.NAME, B_1.toBytes(), SourceFieldMapper.Defaults.FIELD_TYPE));
        ParsedDocument doc = testParsedDocument("1", "1", "test", null, -1, -1, document, B_1, null);
        try {
            replicaEngine.create(new Engine.Create(null, newUid("1"), doc));
            fail("should have thrown an exception");
        } catch (UnsupportedOperationException e) {}
        replicaEngine.refresh("test");

        // its not there...
        Engine.Searcher searchResult = replicaEngine.acquireSearcher("test");
        MatcherAssert.assertThat(searchResult, EngineSearcherTotalHitsMatcher.engineSearcherTotalHits(0));
        MatcherAssert.assertThat(searchResult, EngineSearcherTotalHitsMatcher.engineSearcherTotalHits(new TermQuery(new Term("value", "test")), 0));
        searchResult.close();
        Engine.GetResult getResult = replicaEngine.get(new Engine.Get(true, newUid("1")));
        assertThat(getResult.exists(), equalTo(false));
        getResult.release();

        // index a document
        document = testDocument();
        document.add(new TextField("value", "test1", Field.Store.YES));
        doc = testParsedDocument("1", "1", "test", null, -1, -1, document, B_1, null);
        try {
            replicaEngine.index(new Engine.Index(null, newUid("1"), doc));
            fail("should have thrown an exception");
        } catch (UnsupportedOperationException e) {}
        replicaEngine.refresh("test");

        // its still not there...
        searchResult = replicaEngine.acquireSearcher("test");
        MatcherAssert.assertThat(searchResult, EngineSearcherTotalHitsMatcher.engineSearcherTotalHits(0));
        MatcherAssert.assertThat(searchResult, EngineSearcherTotalHitsMatcher.engineSearcherTotalHits(new TermQuery(new Term("value", "test")), 0));
        searchResult.close();
        getResult = replicaEngine.get(new Engine.Get(true, newUid("1")));
        assertThat(getResult.exists(), equalTo(false));
        getResult.release();

        // Now, add a document to the primary so we can test shadow engine deletes
        document = testDocumentWithTextField();
        document.add(new Field(SourceFieldMapper.NAME, B_1.toBytes(), SourceFieldMapper.Defaults.FIELD_TYPE));
        doc = testParsedDocument("1", "1", "test", null, -1, -1, document, B_1, null);
        primaryEngine.create(new Engine.Create(null, newUid("1"), doc));
        primaryEngine.flush();
        replicaEngine.refresh("test");

        // Now the replica can see it
        searchResult = replicaEngine.acquireSearcher("test");
        MatcherAssert.assertThat(searchResult, EngineSearcherTotalHitsMatcher.engineSearcherTotalHits(1));
        MatcherAssert.assertThat(searchResult, EngineSearcherTotalHitsMatcher.engineSearcherTotalHits(new TermQuery(new Term("value", "test")), 1));
        searchResult.close();

        // And the replica can retrieve it
        getResult = replicaEngine.get(new Engine.Get(false, newUid("1")));
        assertThat(getResult.exists(), equalTo(true));
        assertThat(getResult.docIdAndVersion(), notNullValue());
        getResult.release();

        // try to delete it on the replica
        try {
            replicaEngine.delete(new Engine.Delete("test", "1", newUid("1")));
            fail("should have thrown an exception");
        } catch (UnsupportedOperationException e) {}
        replicaEngine.flush();
        replicaEngine.refresh("test");
        primaryEngine.refresh("test");

        // it's still there!
        searchResult = replicaEngine.acquireSearcher("test");
        MatcherAssert.assertThat(searchResult, EngineSearcherTotalHitsMatcher.engineSearcherTotalHits(1));
        MatcherAssert.assertThat(searchResult, EngineSearcherTotalHitsMatcher.engineSearcherTotalHits(new TermQuery(new Term("value", "test")), 1));
        searchResult.close();
        getResult = replicaEngine.get(new Engine.Get(false, newUid("1")));
        assertThat(getResult.exists(), equalTo(true));
        assertThat(getResult.docIdAndVersion(), notNullValue());
        getResult.release();

        // it's still there on the primary also!
        searchResult = primaryEngine.acquireSearcher("test");
        MatcherAssert.assertThat(searchResult, EngineSearcherTotalHitsMatcher.engineSearcherTotalHits(1));
        MatcherAssert.assertThat(searchResult, EngineSearcherTotalHitsMatcher.engineSearcherTotalHits(new TermQuery(new Term("value", "test")), 1));
        searchResult.close();
        getResult = primaryEngine.get(new Engine.Get(false, newUid("1")));
        assertThat(getResult.exists(), equalTo(true));
        assertThat(getResult.docIdAndVersion(), notNullValue());
        getResult.release();
    }

    @Test
    public void testSimpleOperations() throws Exception {
        Engine.Searcher searchResult = primaryEngine.acquireSearcher("test");
        MatcherAssert.assertThat(searchResult, EngineSearcherTotalHitsMatcher.engineSearcherTotalHits(0));
        searchResult.close();

        // create a document
        ParseContext.Document document = testDocumentWithTextField();
        document.add(new Field(SourceFieldMapper.NAME, B_1.toBytes(), SourceFieldMapper.Defaults.FIELD_TYPE));
        ParsedDocument doc = testParsedDocument("1", "1", "test", null, -1, -1, document, B_1, null);
        primaryEngine.create(new Engine.Create(null, newUid("1"), doc));

        // its not there...
        searchResult = primaryEngine.acquireSearcher("test");
        MatcherAssert.assertThat(searchResult, EngineSearcherTotalHitsMatcher.engineSearcherTotalHits(0));
        MatcherAssert.assertThat(searchResult, EngineSearcherTotalHitsMatcher.engineSearcherTotalHits(new TermQuery(new Term("value", "test")), 0));
        searchResult.close();

        // not on the replica either...
        searchResult = replicaEngine.acquireSearcher("test");
        MatcherAssert.assertThat(searchResult, EngineSearcherTotalHitsMatcher.engineSearcherTotalHits(0));
        MatcherAssert.assertThat(searchResult, EngineSearcherTotalHitsMatcher.engineSearcherTotalHits(new TermQuery(new Term("value", "test")), 0));
        searchResult.close();

        // but, we can still get it (in realtime)
        Engine.GetResult getResult = primaryEngine.get(new Engine.Get(true, newUid("1")));
        assertThat(getResult.exists(), equalTo(true));
        assertThat(getResult.source().source.toBytesArray(), equalTo(B_1.toBytesArray()));
        assertThat(getResult.docIdAndVersion(), nullValue());
        getResult.release();

        // can't get it from the replica, because it's not in the translog for a shadow replica
        getResult = replicaEngine.get(new Engine.Get(true, newUid("1")));
        assertThat(getResult.exists(), equalTo(false));
        getResult.release();

        // but, not there non realtime
        getResult = primaryEngine.get(new Engine.Get(false, newUid("1")));
        assertThat(getResult.exists(), equalTo(false));
        getResult.release();
        // refresh and it should be there
        primaryEngine.refresh("test");

        // now its there...
        searchResult = primaryEngine.acquireSearcher("test");
        MatcherAssert.assertThat(searchResult, EngineSearcherTotalHitsMatcher.engineSearcherTotalHits(1));
        MatcherAssert.assertThat(searchResult, EngineSearcherTotalHitsMatcher.engineSearcherTotalHits(new TermQuery(new Term("value", "test")), 1));
        searchResult.close();

        // also in non realtime
        getResult = primaryEngine.get(new Engine.Get(false, newUid("1")));
        assertThat(getResult.exists(), equalTo(true));
        assertThat(getResult.docIdAndVersion(), notNullValue());
        getResult.release();

        // still not in the replica because no flush
        searchResult = replicaEngine.acquireSearcher("test");
        MatcherAssert.assertThat(searchResult, EngineSearcherTotalHitsMatcher.engineSearcherTotalHits(0));
        MatcherAssert.assertThat(searchResult, EngineSearcherTotalHitsMatcher.engineSearcherTotalHits(new TermQuery(new Term("value", "test")), 0));
        searchResult.close();

        // now do an update
        document = testDocument();
        document.add(new TextField("value", "test1", Field.Store.YES));
        document.add(new Field(SourceFieldMapper.NAME, B_2.toBytes(), SourceFieldMapper.Defaults.FIELD_TYPE));
        doc = testParsedDocument("1", "1", "test", null, -1, -1, document, B_2, null);
        primaryEngine.index(new Engine.Index(null, newUid("1"), doc));

        // its not updated yet...
        searchResult = primaryEngine.acquireSearcher("test");
        MatcherAssert.assertThat(searchResult, EngineSearcherTotalHitsMatcher.engineSearcherTotalHits(1));
        MatcherAssert.assertThat(searchResult, EngineSearcherTotalHitsMatcher.engineSearcherTotalHits(new TermQuery(new Term("value", "test")), 1));
        MatcherAssert.assertThat(searchResult, EngineSearcherTotalHitsMatcher.engineSearcherTotalHits(new TermQuery(new Term("value", "test1")), 0));
        searchResult.close();

        // but, we can still get it (in realtime)
        getResult = primaryEngine.get(new Engine.Get(true, newUid("1")));
        assertThat(getResult.exists(), equalTo(true));
        assertThat(getResult.source().source.toBytesArray(), equalTo(B_2.toBytesArray()));
        assertThat(getResult.docIdAndVersion(), nullValue());
        getResult.release();

        // refresh and it should be updated
        primaryEngine.refresh("test");

        searchResult = primaryEngine.acquireSearcher("test");
        MatcherAssert.assertThat(searchResult, EngineSearcherTotalHitsMatcher.engineSearcherTotalHits(1));
        MatcherAssert.assertThat(searchResult, EngineSearcherTotalHitsMatcher.engineSearcherTotalHits(new TermQuery(new Term("value", "test")), 0));
        MatcherAssert.assertThat(searchResult, EngineSearcherTotalHitsMatcher.engineSearcherTotalHits(new TermQuery(new Term("value", "test1")), 1));
        searchResult.close();

        // flush, now shadow replica should have the files
        primaryEngine.flush();

        // still not in the replica because the replica hasn't refreshed
        searchResult = replicaEngine.acquireSearcher("test");
        MatcherAssert.assertThat(searchResult, EngineSearcherTotalHitsMatcher.engineSearcherTotalHits(0));
        MatcherAssert.assertThat(searchResult, EngineSearcherTotalHitsMatcher.engineSearcherTotalHits(new TermQuery(new Term("value", "test")), 0));
        searchResult.close();

        replicaEngine.refresh("test");

        // the replica finally sees it because primary has flushed and replica refreshed
        searchResult = replicaEngine.acquireSearcher("test");
        MatcherAssert.assertThat(searchResult, EngineSearcherTotalHitsMatcher.engineSearcherTotalHits(1));
        MatcherAssert.assertThat(searchResult, EngineSearcherTotalHitsMatcher.engineSearcherTotalHits(new TermQuery(new Term("value", "test")), 0));
        MatcherAssert.assertThat(searchResult, EngineSearcherTotalHitsMatcher.engineSearcherTotalHits(new TermQuery(new Term("value", "test1")), 1));
        searchResult.close();

        // now delete
        primaryEngine.delete(new Engine.Delete("test", "1", newUid("1")));

        // its not deleted yet
        searchResult = primaryEngine.acquireSearcher("test");
        MatcherAssert.assertThat(searchResult, EngineSearcherTotalHitsMatcher.engineSearcherTotalHits(1));
        MatcherAssert.assertThat(searchResult, EngineSearcherTotalHitsMatcher.engineSearcherTotalHits(new TermQuery(new Term("value", "test")), 0));
        MatcherAssert.assertThat(searchResult, EngineSearcherTotalHitsMatcher.engineSearcherTotalHits(new TermQuery(new Term("value", "test1")), 1));
        searchResult.close();

        // but, get should not see it (in realtime)
        getResult = primaryEngine.get(new Engine.Get(true, newUid("1")));
        assertThat(getResult.exists(), equalTo(false));
        getResult.release();

        // refresh and it should be deleted
        primaryEngine.refresh("test");

        searchResult = primaryEngine.acquireSearcher("test");
        MatcherAssert.assertThat(searchResult, EngineSearcherTotalHitsMatcher.engineSearcherTotalHits(0));
        MatcherAssert.assertThat(searchResult, EngineSearcherTotalHitsMatcher.engineSearcherTotalHits(new TermQuery(new Term("value", "test")), 0));
        MatcherAssert.assertThat(searchResult, EngineSearcherTotalHitsMatcher.engineSearcherTotalHits(new TermQuery(new Term("value", "test1")), 0));
        searchResult.close();

        // add it back
        document = testDocumentWithTextField();
        document.add(new Field(SourceFieldMapper.NAME, B_1.toBytes(), SourceFieldMapper.Defaults.FIELD_TYPE));
        doc = testParsedDocument("1", "1", "test", null, -1, -1, document, B_1, null);
        primaryEngine.create(new Engine.Create(null, newUid("1"), doc));

        // its not there...
        searchResult = primaryEngine.acquireSearcher("test");
        MatcherAssert.assertThat(searchResult, EngineSearcherTotalHitsMatcher.engineSearcherTotalHits(0));
        MatcherAssert.assertThat(searchResult, EngineSearcherTotalHitsMatcher.engineSearcherTotalHits(new TermQuery(new Term("value", "test")), 0));
        MatcherAssert.assertThat(searchResult, EngineSearcherTotalHitsMatcher.engineSearcherTotalHits(new TermQuery(new Term("value", "test1")), 0));
        searchResult.close();

        // refresh and it should be there
        primaryEngine.refresh("test");

        // now its there...
        searchResult = primaryEngine.acquireSearcher("test");
        MatcherAssert.assertThat(searchResult, EngineSearcherTotalHitsMatcher.engineSearcherTotalHits(1));
        MatcherAssert.assertThat(searchResult, EngineSearcherTotalHitsMatcher.engineSearcherTotalHits(new TermQuery(new Term("value", "test")), 1));
        MatcherAssert.assertThat(searchResult, EngineSearcherTotalHitsMatcher.engineSearcherTotalHits(new TermQuery(new Term("value", "test1")), 0));
        searchResult.close();

        // now flush
        primaryEngine.flush();

        // and, verify get (in real time)
        getResult = primaryEngine.get(new Engine.Get(true, newUid("1")));
        assertThat(getResult.exists(), equalTo(true));
        assertThat(getResult.source(), nullValue());
        assertThat(getResult.docIdAndVersion(), notNullValue());
        getResult.release();

        // the replica should see it if we refresh too!
        replicaEngine.refresh("test");
        searchResult = replicaEngine.acquireSearcher("test");
        MatcherAssert.assertThat(searchResult, EngineSearcherTotalHitsMatcher.engineSearcherTotalHits(1));
        MatcherAssert.assertThat(searchResult, EngineSearcherTotalHitsMatcher.engineSearcherTotalHits(new TermQuery(new Term("value", "test")), 1));
        MatcherAssert.assertThat(searchResult, EngineSearcherTotalHitsMatcher.engineSearcherTotalHits(new TermQuery(new Term("value", "test1")), 0));
        searchResult.close();
        getResult = replicaEngine.get(new Engine.Get(true, newUid("1")));
        assertThat(getResult.exists(), equalTo(true));
        assertThat(getResult.source(), nullValue());
        assertThat(getResult.docIdAndVersion(), notNullValue());
        getResult.release();

        // make sure we can still work with the engine
        // now do an update
        document = testDocument();
        document.add(new TextField("value", "test1", Field.Store.YES));
        doc = testParsedDocument("1", "1", "test", null, -1, -1, document, B_1, null);
        primaryEngine.index(new Engine.Index(null, newUid("1"), doc));

        // its not updated yet...
        searchResult = primaryEngine.acquireSearcher("test");
        MatcherAssert.assertThat(searchResult, EngineSearcherTotalHitsMatcher.engineSearcherTotalHits(1));
        MatcherAssert.assertThat(searchResult, EngineSearcherTotalHitsMatcher.engineSearcherTotalHits(new TermQuery(new Term("value", "test")), 1));
        MatcherAssert.assertThat(searchResult, EngineSearcherTotalHitsMatcher.engineSearcherTotalHits(new TermQuery(new Term("value", "test1")), 0));
        searchResult.close();

        // refresh and it should be updated
        primaryEngine.refresh("test");

        searchResult = primaryEngine.acquireSearcher("test");
        MatcherAssert.assertThat(searchResult, EngineSearcherTotalHitsMatcher.engineSearcherTotalHits(1));
        MatcherAssert.assertThat(searchResult, EngineSearcherTotalHitsMatcher.engineSearcherTotalHits(new TermQuery(new Term("value", "test")), 0));
        MatcherAssert.assertThat(searchResult, EngineSearcherTotalHitsMatcher.engineSearcherTotalHits(new TermQuery(new Term("value", "test1")), 1));
        searchResult.close();

        // Make visible to shadow replica
        primaryEngine.flush();
        replicaEngine.refresh("test");

        searchResult = replicaEngine.acquireSearcher("test");
        MatcherAssert.assertThat(searchResult, EngineSearcherTotalHitsMatcher.engineSearcherTotalHits(1));
        MatcherAssert.assertThat(searchResult, EngineSearcherTotalHitsMatcher.engineSearcherTotalHits(new TermQuery(new Term("value", "test")), 0));
        MatcherAssert.assertThat(searchResult, EngineSearcherTotalHitsMatcher.engineSearcherTotalHits(new TermQuery(new Term("value", "test1")), 1));
        searchResult.close();
    }

    @Test
    public void testSearchResultRelease() throws Exception {
        Engine.Searcher searchResult = replicaEngine.acquireSearcher("test");
        MatcherAssert.assertThat(searchResult, EngineSearcherTotalHitsMatcher.engineSearcherTotalHits(0));
        searchResult.close();

        // create a document
        ParsedDocument doc = testParsedDocument("1", "1", "test", null, -1, -1, testDocumentWithTextField(), B_1, null);
        primaryEngine.create(new Engine.Create(null, newUid("1"), doc));

        // its not there...
        searchResult = primaryEngine.acquireSearcher("test");
        MatcherAssert.assertThat(searchResult, EngineSearcherTotalHitsMatcher.engineSearcherTotalHits(0));
        MatcherAssert.assertThat(searchResult, EngineSearcherTotalHitsMatcher.engineSearcherTotalHits(new TermQuery(new Term("value", "test")), 0));
        searchResult.close();
        searchResult = replicaEngine.acquireSearcher("test");
        MatcherAssert.assertThat(searchResult, EngineSearcherTotalHitsMatcher.engineSearcherTotalHits(0));
        MatcherAssert.assertThat(searchResult, EngineSearcherTotalHitsMatcher.engineSearcherTotalHits(new TermQuery(new Term("value", "test")), 0));
        searchResult.close();

        // flush & refresh and it should everywhere
        primaryEngine.flush();
        primaryEngine.refresh("test");
        replicaEngine.refresh("test");

        // now its there...
        searchResult = primaryEngine.acquireSearcher("test");
        MatcherAssert.assertThat(searchResult, EngineSearcherTotalHitsMatcher.engineSearcherTotalHits(1));
        MatcherAssert.assertThat(searchResult, EngineSearcherTotalHitsMatcher.engineSearcherTotalHits(new TermQuery(new Term("value", "test")), 1));
        searchResult.close();

        searchResult = replicaEngine.acquireSearcher("test");
        MatcherAssert.assertThat(searchResult, EngineSearcherTotalHitsMatcher.engineSearcherTotalHits(1));
        MatcherAssert.assertThat(searchResult, EngineSearcherTotalHitsMatcher.engineSearcherTotalHits(new TermQuery(new Term("value", "test")), 1));
        // don't release the replica search result yet...

        // delete, refresh and do a new search, it should not be there
        primaryEngine.delete(new Engine.Delete("test", "1", newUid("1")));
        primaryEngine.flush();
        primaryEngine.refresh("test");
        replicaEngine.refresh("test");
        Engine.Searcher updateSearchResult = primaryEngine.acquireSearcher("test");
        MatcherAssert.assertThat(updateSearchResult, EngineSearcherTotalHitsMatcher.engineSearcherTotalHits(0));
        updateSearchResult.close();

        // the non released replica search result should not see the deleted yet...
        MatcherAssert.assertThat(searchResult, EngineSearcherTotalHitsMatcher.engineSearcherTotalHits(1));
        MatcherAssert.assertThat(searchResult, EngineSearcherTotalHitsMatcher.engineSearcherTotalHits(new TermQuery(new Term("value", "test")), 1));
        searchResult.close();
    }

    @Test
    public void testFailEngineOnCorruption() {
        ParsedDocument doc = testParsedDocument("1", "1", "test", null, -1, -1, testDocumentWithTextField(), B_1, null);
        primaryEngine.create(new Engine.Create(null, newUid("1"), doc));
        primaryEngine.flush();
        MockDirectoryWrapper leaf = DirectoryUtils.getLeaf(replicaEngine.config().getStore().directory(), MockDirectoryWrapper.class);
        leaf.setRandomIOExceptionRate(1.0);
        leaf.setRandomIOExceptionRateOnOpen(1.0);
        try {
            replicaEngine.refresh("foo");
            fail("exception expected");
        } catch (Exception ex) {

        }
        try {
            Engine.Searcher searchResult = replicaEngine.acquireSearcher("test");
            MatcherAssert.assertThat(searchResult, EngineSearcherTotalHitsMatcher.engineSearcherTotalHits(1));
            MatcherAssert.assertThat(searchResult, EngineSearcherTotalHitsMatcher.engineSearcherTotalHits(new TermQuery(new Term("value", "test")), 1));
            searchResult.close();
            fail("exception expected");
        } catch (EngineClosedException ex) {
            // all is well
        }
    }

    @Test
    public void testExtractShardId() {
        try (Engine.Searcher test = replicaEngine.acquireSearcher("test")) {
            ShardId shardId = ShardUtils.extractShardId(test.reader());
            assertNotNull(shardId);
            assertEquals(shardId, replicaEngine.config().getShardId());
        }
    }

    /**
     * Random test that throws random exception and ensures all references are
     * counted down / released and resources are closed.
     */
    @Test
    public void testFailStart() throws IOException {
        // Need a commit point for this
        ParsedDocument doc = testParsedDocument("1", "1", "test", null, -1, -1, testDocumentWithTextField(), B_1, null);
        primaryEngine.create(new Engine.Create(null, newUid("1"), doc));
        primaryEngine.flush();

        // this test fails if any reader, searcher or directory is not closed - MDW FTW
        final int iters = scaledRandomIntBetween(10, 100);
        for (int i = 0; i < iters; i++) {
            MockDirectoryWrapper wrapper = newMockFSDirectory(dirPath);
            wrapper.setFailOnOpenInput(randomBoolean());
            wrapper.setAllowRandomFileNotFoundException(randomBoolean());
            wrapper.setRandomIOExceptionRate(randomDouble());
            wrapper.setRandomIOExceptionRateOnOpen(randomDouble());
            try (Store store = createStore(wrapper)) {
                int refCount = store.refCount();
                assertTrue("refCount: "+ store.refCount(), store.refCount() > 0);
                ShadowEngine holder;
                try {
                    holder = createShadowEngine(store);
                } catch (EngineCreationFailureException ex) {
                    assertEquals(store.refCount(), refCount);
                    continue;
                }
                assertEquals(store.refCount(), refCount+1);
                final int numStarts = scaledRandomIntBetween(1, 5);
                for (int j = 0; j < numStarts; j++) {
                    try {
                        assertEquals(store.refCount(), refCount + 1);
                        holder.close();
                        holder = createShadowEngine(store);
                        assertEquals(store.refCount(), refCount + 1);
                    } catch (EngineCreationFailureException ex) {
                        // all is fine
                        assertEquals(store.refCount(), refCount);
                        break;
                    }
                }
                holder.close();
                assertEquals(store.refCount(), refCount);
            }
        }
    }

    @Test
    public void testSettings() {
        CodecService codecService = new CodecService(shardId.index());
        assertEquals(replicaEngine.config().getCodec().getName(), codecService.codec(codecName).getName());
        assertEquals(replicaEngine.config().getIndexConcurrency(), indexConcurrency);
    }

    @Test
    public void testShadowEngineCreationRetry() throws Exception {
        final Path srDir = createTempDir();
        final Store srStore = createStore(srDir);
        Lucene.cleanLuceneIndex(srStore.directory());

        final AtomicBoolean succeeded = new AtomicBoolean(false);
        final CountDownLatch latch = new CountDownLatch(1);

        // Create a shadow Engine, which will freak out because there is no
        // index yet
        Thread t = new Thread(new Runnable() {
            @Override
            public void run() {
                try {
                    latch.await();
                } catch (InterruptedException e) {
                    // ignore interruptions
                }
                try (ShadowEngine srEngine = createShadowEngine(srStore)) {
                    succeeded.set(true);
                } catch (Exception e) {
                    fail("should have been able to create the engine!");
                }
            }
        });
        t.start();

        // count down latch
        // now shadow engine should try to be created
        latch.countDown();

        // Create an InternalEngine, which creates the index so the shadow
        // replica will handle it correctly
        Store pStore = createStore(srDir);
        InternalEngine pEngine = createInternalEngine(pStore, createTempDir("translog-primary"));

        // create a document
        ParseContext.Document document = testDocumentWithTextField();
        document.add(new Field(SourceFieldMapper.NAME, B_1.toBytes(), SourceFieldMapper.Defaults.FIELD_TYPE));
        ParsedDocument doc = testParsedDocument("1", "1", "test", null, -1, -1, document, B_1, null);
        pEngine.create(new Engine.Create(null, newUid("1"), doc));
        pEngine.flush(true, true);

        t.join();
        assertTrue("ShadowEngine should have been able to be created", succeeded.get());
        // (shadow engine is already shut down in the try-with-resources)
        IOUtils.close(srStore, pEngine, pStore);
    }
}


File: core/src/test/java/org/elasticsearch/index/merge/policy/MergePolicySettingsTest.java
/*
 * Licensed to Elasticsearch under one or more contributor
 * license agreements. See the NOTICE file distributed with
 * this work for additional information regarding copyright
 * ownership. Elasticsearch licenses this file to you under
 * the Apache License, Version 2.0 (the "License"); you may
 * not use this file except in compliance with the License.
 * You may obtain a copy of the License at
 *
 *    http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing,
 * software distributed under the License is distributed on an
 * "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY
 * KIND, either express or implied.  See the License for the
 * specific language governing permissions and limitations
 * under the License.
 */
package org.elasticsearch.index.merge.policy;

import org.apache.lucene.index.LogByteSizeMergePolicy;
import org.apache.lucene.index.LogDocMergePolicy;
import org.apache.lucene.store.Directory;
import org.apache.lucene.store.RAMDirectory;
import org.elasticsearch.common.settings.Settings;
import org.elasticsearch.common.unit.ByteSizeUnit;
import org.elasticsearch.common.unit.ByteSizeValue;
import org.elasticsearch.index.Index;
import org.elasticsearch.index.settings.IndexSettingsService;
import org.elasticsearch.index.shard.ShardId;
import org.elasticsearch.index.store.DirectoryService;
import org.elasticsearch.index.store.Store;
import org.elasticsearch.test.DummyShardLock;
import org.elasticsearch.test.ElasticsearchTestCase;
import org.junit.Test;

import java.io.IOException;

import static org.elasticsearch.common.settings.Settings.Builder.EMPTY_SETTINGS;
import static org.hamcrest.Matchers.equalTo;

public class MergePolicySettingsTest extends ElasticsearchTestCase {

    protected final ShardId shardId = new ShardId(new Index("index"), 1);

    @Test
    public void testCompoundFileSettings() throws IOException {
        IndexSettingsService service = new IndexSettingsService(new Index("test"), EMPTY_SETTINGS);

        assertThat(new TieredMergePolicyProvider(createStore(EMPTY_SETTINGS), service).getMergePolicy().getNoCFSRatio(), equalTo(0.1));
        assertThat(new TieredMergePolicyProvider(createStore(build(true)), service).getMergePolicy().getNoCFSRatio(), equalTo(1.0));
        assertThat(new TieredMergePolicyProvider(createStore(build(0.5)), service).getMergePolicy().getNoCFSRatio(), equalTo(0.5));
        assertThat(new TieredMergePolicyProvider(createStore(build(1.0)), service).getMergePolicy().getNoCFSRatio(), equalTo(1.0));
        assertThat(new TieredMergePolicyProvider(createStore(build("true")), service).getMergePolicy().getNoCFSRatio(), equalTo(1.0));
        assertThat(new TieredMergePolicyProvider(createStore(build("True")), service).getMergePolicy().getNoCFSRatio(), equalTo(1.0));
        assertThat(new TieredMergePolicyProvider(createStore(build("False")), service).getMergePolicy().getNoCFSRatio(), equalTo(0.0));
        assertThat(new TieredMergePolicyProvider(createStore(build("false")), service).getMergePolicy().getNoCFSRatio(), equalTo(0.0));
        assertThat(new TieredMergePolicyProvider(createStore(build(false)), service).getMergePolicy().getNoCFSRatio(), equalTo(0.0));
        assertThat(new TieredMergePolicyProvider(createStore(build(0)), service).getMergePolicy().getNoCFSRatio(), equalTo(0.0));
        assertThat(new TieredMergePolicyProvider(createStore(build(0.0)), service).getMergePolicy().getNoCFSRatio(), equalTo(0.0));

        assertThat(new LogByteSizeMergePolicyProvider(createStore(EMPTY_SETTINGS), service).getMergePolicy().getNoCFSRatio(), equalTo(0.1));
        assertThat(new LogByteSizeMergePolicyProvider(createStore(build(true)), service).getMergePolicy().getNoCFSRatio(), equalTo(1.0));
        assertThat(new LogByteSizeMergePolicyProvider(createStore(build(0.5)), service).getMergePolicy().getNoCFSRatio(), equalTo(0.5));
        assertThat(new LogByteSizeMergePolicyProvider(createStore(build(1.0)), service).getMergePolicy().getNoCFSRatio(), equalTo(1.0));
        assertThat(new LogByteSizeMergePolicyProvider(createStore(build("true")), service).getMergePolicy().getNoCFSRatio(), equalTo(1.0));
        assertThat(new LogByteSizeMergePolicyProvider(createStore(build("True")), service).getMergePolicy().getNoCFSRatio(), equalTo(1.0));
        assertThat(new LogByteSizeMergePolicyProvider(createStore(build("False")), service).getMergePolicy().getNoCFSRatio(), equalTo(0.0));
        assertThat(new LogByteSizeMergePolicyProvider(createStore(build("false")), service).getMergePolicy().getNoCFSRatio(), equalTo(0.0));
        assertThat(new LogByteSizeMergePolicyProvider(createStore(build(false)), service).getMergePolicy().getNoCFSRatio(), equalTo(0.0));
        assertThat(new LogByteSizeMergePolicyProvider(createStore(build(0)), service).getMergePolicy().getNoCFSRatio(), equalTo(0.0));
        assertThat(new LogByteSizeMergePolicyProvider(createStore(build(0.0)), service).getMergePolicy().getNoCFSRatio(), equalTo(0.0));

        assertThat(new LogDocMergePolicyProvider(createStore(EMPTY_SETTINGS), service).getMergePolicy().getNoCFSRatio(), equalTo(0.1));
        assertThat(new LogDocMergePolicyProvider(createStore(build(true)), service).getMergePolicy().getNoCFSRatio(), equalTo(1.0));
        assertThat(new LogDocMergePolicyProvider(createStore(build(0.5)), service).getMergePolicy().getNoCFSRatio(), equalTo(0.5));
        assertThat(new LogDocMergePolicyProvider(createStore(build(1.0)), service).getMergePolicy().getNoCFSRatio(), equalTo(1.0));
        assertThat(new LogDocMergePolicyProvider(createStore(build("true")), service).getMergePolicy().getNoCFSRatio(), equalTo(1.0));
        assertThat(new LogDocMergePolicyProvider(createStore(build("True")), service).getMergePolicy().getNoCFSRatio(), equalTo(1.0));
        assertThat(new LogDocMergePolicyProvider(createStore(build("False")), service).getMergePolicy().getNoCFSRatio(), equalTo(0.0));
        assertThat(new LogDocMergePolicyProvider(createStore(build("false")), service).getMergePolicy().getNoCFSRatio(), equalTo(0.0));
        assertThat(new LogDocMergePolicyProvider(createStore(build(false)), service).getMergePolicy().getNoCFSRatio(), equalTo(0.0));
        assertThat(new LogDocMergePolicyProvider(createStore(build(0)), service).getMergePolicy().getNoCFSRatio(), equalTo(0.0));
        assertThat(new LogDocMergePolicyProvider(createStore(build(0.0)), service).getMergePolicy().getNoCFSRatio(), equalTo(0.0));

    }

    @Test
    public void testInvalidValue() throws IOException {
        IndexSettingsService service = new IndexSettingsService(new Index("test"), EMPTY_SETTINGS);
        try {
            new LogDocMergePolicyProvider(createStore(build(-0.1)), service).getMergePolicy().getNoCFSRatio();
            fail("exception expected");
        } catch (IllegalArgumentException ex) {

        }
        try {
            new LogDocMergePolicyProvider(createStore(build(1.1)), service).getMergePolicy().getNoCFSRatio();
            fail("exception expected");
        } catch (IllegalArgumentException ex) {

        }
        try {
            new LogDocMergePolicyProvider(createStore(build("Falsch")), service).getMergePolicy().getNoCFSRatio();
            fail("exception expected");
        } catch (IllegalArgumentException ex) {

        }

    }

    @Test
    public void testUpdateSettings() throws IOException {
        {
            IndexSettingsService service = new IndexSettingsService(new Index("test"), EMPTY_SETTINGS);
            TieredMergePolicyProvider mp = new TieredMergePolicyProvider(createStore(EMPTY_SETTINGS), service);
            assertThat(mp.getMergePolicy().getNoCFSRatio(), equalTo(0.1));

            service.refreshSettings(build(1.0));
            assertThat(mp.getMergePolicy().getNoCFSRatio(), equalTo(1.0));

            service.refreshSettings(build(0.1));
            assertThat(mp.getMergePolicy().getNoCFSRatio(), equalTo(0.1));

            service.refreshSettings(build(0.0));
            assertThat(mp.getMergePolicy().getNoCFSRatio(), equalTo(0.0));
        }

        {
            IndexSettingsService service = new IndexSettingsService(new Index("test"), EMPTY_SETTINGS);
            LogByteSizeMergePolicyProvider mp = new LogByteSizeMergePolicyProvider(createStore(EMPTY_SETTINGS), service);
            assertThat(mp.getMergePolicy().getNoCFSRatio(), equalTo(0.1));

            service.refreshSettings(build(1.0));
            assertThat(mp.getMergePolicy().getNoCFSRatio(), equalTo(1.0));

            service.refreshSettings(build(0.1));
            assertThat(mp.getMergePolicy().getNoCFSRatio(), equalTo(0.1));

            service.refreshSettings(build(0.0));
            assertThat(mp.getMergePolicy().getNoCFSRatio(), equalTo(0.0));
        }

        {
            IndexSettingsService service = new IndexSettingsService(new Index("test"), EMPTY_SETTINGS);
            LogDocMergePolicyProvider mp = new LogDocMergePolicyProvider(createStore(EMPTY_SETTINGS), service);
            assertThat(mp.getMergePolicy().getNoCFSRatio(), equalTo(0.1));

            service.refreshSettings(build(1.0));
            assertThat(mp.getMergePolicy().getNoCFSRatio(), equalTo(1.0));

            service.refreshSettings(build(0.1));
            assertThat(mp.getMergePolicy().getNoCFSRatio(), equalTo(0.1));

            service.refreshSettings(build(0.0));
            assertThat(mp.getMergePolicy().getNoCFSRatio(), equalTo(0.0));
        }
    }

    public void testLogDocSizeMergePolicySettingsUpdate() throws IOException {
        IndexSettingsService service = new IndexSettingsService(new Index("test"), EMPTY_SETTINGS);
        LogDocMergePolicyProvider mp = new LogDocMergePolicyProvider(createStore(EMPTY_SETTINGS), service);

        assertEquals(mp.getMergePolicy().getMaxMergeDocs(), LogDocMergePolicy.DEFAULT_MAX_MERGE_DOCS);
        service.refreshSettings(Settings.builder().put(LogDocMergePolicyProvider.INDEX_MERGE_POLICY_MAX_MERGE_DOCS, LogDocMergePolicy.DEFAULT_MAX_MERGE_DOCS / 2).build());
        assertEquals(mp.getMergePolicy().getMaxMergeDocs(), LogDocMergePolicy.DEFAULT_MAX_MERGE_DOCS / 2);

        assertEquals(mp.getMergePolicy().getMinMergeDocs(), LogDocMergePolicy.DEFAULT_MIN_MERGE_DOCS);
        service.refreshSettings(Settings.builder().put(LogDocMergePolicyProvider.INDEX_MERGE_POLICY_MIN_MERGE_DOCS, LogDocMergePolicy.DEFAULT_MIN_MERGE_DOCS / 2).build());
        assertEquals(mp.getMergePolicy().getMinMergeDocs(), LogDocMergePolicy.DEFAULT_MIN_MERGE_DOCS / 2);

        assertTrue(mp.getMergePolicy().getCalibrateSizeByDeletes());
        service.refreshSettings(Settings.builder().put(LogDocMergePolicyProvider.INDEX_MERGE_POLICY_CALIBRATE_SIZE_BY_DELETES, false).build());
        assertFalse(mp.getMergePolicy().getCalibrateSizeByDeletes());

        assertEquals(mp.getMergePolicy().getMergeFactor(), LogDocMergePolicy.DEFAULT_MERGE_FACTOR);
        service.refreshSettings(Settings.builder().put(LogDocMergePolicyProvider.INDEX_MERGE_POLICY_MERGE_FACTOR, LogDocMergePolicy.DEFAULT_MERGE_FACTOR * 2).build());
        assertEquals(mp.getMergePolicy().getMergeFactor(), LogDocMergePolicy.DEFAULT_MERGE_FACTOR * 2);

        service.refreshSettings(EMPTY_SETTINGS); // update without the settings and see if we stick to the values
        assertEquals(mp.getMergePolicy().getMaxMergeDocs(), LogDocMergePolicy.DEFAULT_MAX_MERGE_DOCS / 2);
        assertEquals(mp.getMergePolicy().getMinMergeDocs(), LogDocMergePolicy.DEFAULT_MIN_MERGE_DOCS / 2);
        assertFalse(mp.getMergePolicy().getCalibrateSizeByDeletes());
        assertEquals(mp.getMergePolicy().getMergeFactor(), LogByteSizeMergePolicy.DEFAULT_MERGE_FACTOR * 2);


        service = new IndexSettingsService(new Index("test"), EMPTY_SETTINGS);
        mp = new LogDocMergePolicyProvider(createStore(Settings.builder()
                .put(LogDocMergePolicyProvider.INDEX_MERGE_POLICY_MAX_MERGE_DOCS, LogByteSizeMergePolicy.DEFAULT_MAX_MERGE_DOCS / 2)
                .put(LogDocMergePolicyProvider.INDEX_MERGE_POLICY_MERGE_FACTOR, LogByteSizeMergePolicy.DEFAULT_MERGE_FACTOR / 2)
                .put(LogDocMergePolicyProvider.INDEX_MERGE_POLICY_CALIBRATE_SIZE_BY_DELETES, false)
                .put(LogDocMergePolicyProvider.INDEX_MERGE_POLICY_MIN_MERGE_DOCS, LogDocMergePolicy.DEFAULT_MIN_MERGE_DOCS - 1)
                .build()), service);


        assertEquals(mp.getMergePolicy().getMinMergeDocs(), LogDocMergePolicy.DEFAULT_MIN_MERGE_DOCS - 1);
        assertFalse(mp.getMergePolicy().getCalibrateSizeByDeletes());
        assertEquals(mp.getMergePolicy().getMergeFactor(), LogByteSizeMergePolicy.DEFAULT_MERGE_FACTOR / 2);
        assertEquals(mp.getMergePolicy().getMaxMergeDocs(), LogByteSizeMergePolicy.DEFAULT_MAX_MERGE_DOCS / 2);
    }

    public void testLogByteSizeMergePolicySettingsUpdate() throws IOException {
        IndexSettingsService service = new IndexSettingsService(new Index("test"), EMPTY_SETTINGS);
        LogByteSizeMergePolicyProvider mp = new LogByteSizeMergePolicyProvider(createStore(EMPTY_SETTINGS), service);

        assertEquals(mp.getMergePolicy().getMaxMergeMB(), LogByteSizeMergePolicyProvider.DEFAULT_MAX_MERGE_SIZE.mbFrac(), 0.0d);
        service.refreshSettings(Settings.builder().put(LogByteSizeMergePolicyProvider.INDEX_MERGE_POLICY_MAX_MERGE_SIZE, new ByteSizeValue(LogByteSizeMergePolicyProvider.DEFAULT_MAX_MERGE_SIZE.mb() / 2, ByteSizeUnit.MB)).build());
        assertEquals(mp.getMergePolicy().getMaxMergeMB(), new ByteSizeValue(LogByteSizeMergePolicyProvider.DEFAULT_MAX_MERGE_SIZE.mb() / 2, ByteSizeUnit.MB).mbFrac(), 0.0d);

        assertEquals(mp.getMergePolicy().getMinMergeMB(), LogByteSizeMergePolicyProvider.DEFAULT_MIN_MERGE_SIZE.mbFrac(), 0.0d);
        service.refreshSettings(Settings.builder().put(LogByteSizeMergePolicyProvider.INDEX_MERGE_POLICY_MIN_MERGE_SIZE, new ByteSizeValue(LogByteSizeMergePolicyProvider.DEFAULT_MIN_MERGE_SIZE.mb() + 1, ByteSizeUnit.MB)).build());
        assertEquals(mp.getMergePolicy().getMinMergeMB(), new ByteSizeValue(LogByteSizeMergePolicyProvider.DEFAULT_MIN_MERGE_SIZE.mb() + 1, ByteSizeUnit.MB).mbFrac(), 0.0d);

        assertTrue(mp.getMergePolicy().getCalibrateSizeByDeletes());
        service.refreshSettings(Settings.builder().put(LogByteSizeMergePolicyProvider.INDEX_MERGE_POLICY_CALIBRATE_SIZE_BY_DELETES, false).build());
        assertFalse(mp.getMergePolicy().getCalibrateSizeByDeletes());

        assertEquals(mp.getMergePolicy().getMergeFactor(), LogByteSizeMergePolicy.DEFAULT_MERGE_FACTOR);
        service.refreshSettings(Settings.builder().put(LogByteSizeMergePolicyProvider.INDEX_MERGE_POLICY_MERGE_FACTOR, LogByteSizeMergePolicy.DEFAULT_MERGE_FACTOR / 2).build());
        assertEquals(mp.getMergePolicy().getMergeFactor(), LogByteSizeMergePolicy.DEFAULT_MERGE_FACTOR / 2);

        assertEquals(mp.getMergePolicy().getMaxMergeDocs(), LogByteSizeMergePolicy.DEFAULT_MAX_MERGE_DOCS);
        service.refreshSettings(Settings.builder().put(LogByteSizeMergePolicyProvider.INDEX_MERGE_POLICY_MAX_MERGE_DOCS, LogByteSizeMergePolicy.DEFAULT_MAX_MERGE_DOCS / 2).build());
        assertEquals(mp.getMergePolicy().getMaxMergeDocs(), LogByteSizeMergePolicy.DEFAULT_MAX_MERGE_DOCS / 2);

        service.refreshSettings(EMPTY_SETTINGS); // update without the settings and see if we stick to the values
        assertEquals(mp.getMergePolicy().getMaxMergeMB(), new ByteSizeValue(LogByteSizeMergePolicyProvider.DEFAULT_MAX_MERGE_SIZE.mb() / 2, ByteSizeUnit.MB).mbFrac(), 0.0d);
        assertEquals(mp.getMergePolicy().getMinMergeMB(), new ByteSizeValue(LogByteSizeMergePolicyProvider.DEFAULT_MIN_MERGE_SIZE.mb() + 1, ByteSizeUnit.MB).mbFrac(), 0.0d);
        assertFalse(mp.getMergePolicy().getCalibrateSizeByDeletes());
        assertEquals(mp.getMergePolicy().getMergeFactor(), LogByteSizeMergePolicy.DEFAULT_MERGE_FACTOR / 2);
        assertEquals(mp.getMergePolicy().getMaxMergeDocs(), LogByteSizeMergePolicy.DEFAULT_MAX_MERGE_DOCS / 2);


        service = new IndexSettingsService(new Index("test"), EMPTY_SETTINGS);
        mp = new LogByteSizeMergePolicyProvider(createStore(Settings.builder()
                .put(LogByteSizeMergePolicyProvider.INDEX_MERGE_POLICY_MAX_MERGE_DOCS, LogByteSizeMergePolicy.DEFAULT_MAX_MERGE_DOCS * 2)
                .put(LogByteSizeMergePolicyProvider.INDEX_MERGE_POLICY_MERGE_FACTOR, LogByteSizeMergePolicy.DEFAULT_MERGE_FACTOR * 2)
                .put(LogByteSizeMergePolicyProvider.INDEX_MERGE_POLICY_MAX_MERGE_SIZE, new ByteSizeValue(LogByteSizeMergePolicyProvider.DEFAULT_MAX_MERGE_SIZE.mb() / 2, ByteSizeUnit.MB))
                .put(LogByteSizeMergePolicyProvider.INDEX_MERGE_POLICY_CALIBRATE_SIZE_BY_DELETES, false)
                .put(LogByteSizeMergePolicyProvider.INDEX_MERGE_POLICY_MIN_MERGE_SIZE, new ByteSizeValue(LogByteSizeMergePolicyProvider.DEFAULT_MIN_MERGE_SIZE.mb() + 1, ByteSizeUnit.MB))
                .build()), service);


        assertEquals(mp.getMergePolicy().getMaxMergeMB(), new ByteSizeValue(LogByteSizeMergePolicyProvider.DEFAULT_MAX_MERGE_SIZE.mb() / 2, ByteSizeUnit.MB).mbFrac(), 0.0d);
        assertEquals(mp.getMergePolicy().getMinMergeMB(), new ByteSizeValue(LogByteSizeMergePolicyProvider.DEFAULT_MIN_MERGE_SIZE.mb() + 1, ByteSizeUnit.MB).mbFrac(), 0.0d);
        assertFalse(mp.getMergePolicy().getCalibrateSizeByDeletes());
        assertEquals(mp.getMergePolicy().getMergeFactor(), LogByteSizeMergePolicy.DEFAULT_MERGE_FACTOR * 2);
        assertEquals(mp.getMergePolicy().getMaxMergeDocs(), LogByteSizeMergePolicy.DEFAULT_MAX_MERGE_DOCS * 2);
    }

    public void testTieredMergePolicySettingsUpdate() throws IOException {
        IndexSettingsService service = new IndexSettingsService(new Index("test"), EMPTY_SETTINGS);
        TieredMergePolicyProvider mp = new TieredMergePolicyProvider(createStore(EMPTY_SETTINGS), service);
        assertThat(mp.getMergePolicy().getNoCFSRatio(), equalTo(0.1));

        assertEquals(mp.getMergePolicy().getForceMergeDeletesPctAllowed(), TieredMergePolicyProvider.DEFAULT_EXPUNGE_DELETES_ALLOWED, 0.0d);
        service.refreshSettings(Settings.builder().put(TieredMergePolicyProvider.INDEX_MERGE_POLICY_EXPUNGE_DELETES_ALLOWED, TieredMergePolicyProvider.DEFAULT_EXPUNGE_DELETES_ALLOWED + 1.0d).build());
        assertEquals(mp.getMergePolicy().getForceMergeDeletesPctAllowed(), TieredMergePolicyProvider.DEFAULT_EXPUNGE_DELETES_ALLOWED + 1.0d, 0.0d);

        assertEquals(mp.getMergePolicy().getFloorSegmentMB(), TieredMergePolicyProvider.DEFAULT_FLOOR_SEGMENT.mbFrac(), 0);
        service.refreshSettings(Settings.builder().put(TieredMergePolicyProvider.INDEX_MERGE_POLICY_FLOOR_SEGMENT, new ByteSizeValue(TieredMergePolicyProvider.DEFAULT_FLOOR_SEGMENT.mb() + 1, ByteSizeUnit.MB)).build());
        assertEquals(mp.getMergePolicy().getFloorSegmentMB(), new ByteSizeValue(TieredMergePolicyProvider.DEFAULT_FLOOR_SEGMENT.mb() + 1, ByteSizeUnit.MB).mbFrac(), 0.001);

        assertEquals(mp.getMergePolicy().getMaxMergeAtOnce(), TieredMergePolicyProvider.DEFAULT_MAX_MERGE_AT_ONCE);
        service.refreshSettings(Settings.builder().put(TieredMergePolicyProvider.INDEX_MERGE_POLICY_MAX_MERGE_AT_ONCE, TieredMergePolicyProvider.DEFAULT_MAX_MERGE_AT_ONCE -1 ).build());
        assertEquals(mp.getMergePolicy().getMaxMergeAtOnce(), TieredMergePolicyProvider.DEFAULT_MAX_MERGE_AT_ONCE-1);

        assertEquals(mp.getMergePolicy().getMaxMergeAtOnceExplicit(), TieredMergePolicyProvider.DEFAULT_MAX_MERGE_AT_ONCE_EXPLICIT);
        service.refreshSettings(Settings.builder().put(TieredMergePolicyProvider.INDEX_MERGE_POLICY_MAX_MERGE_AT_ONCE_EXPLICIT, TieredMergePolicyProvider.DEFAULT_MAX_MERGE_AT_ONCE_EXPLICIT -1 ).build());
        assertEquals(mp.getMergePolicy().getMaxMergeAtOnceExplicit(), TieredMergePolicyProvider.DEFAULT_MAX_MERGE_AT_ONCE_EXPLICIT-1);

        assertEquals(mp.getMergePolicy().getMaxMergedSegmentMB(), TieredMergePolicyProvider.DEFAULT_MAX_MERGED_SEGMENT.mbFrac(), 0.0001);
        service.refreshSettings(Settings.builder().put(TieredMergePolicyProvider.INDEX_MERGE_POLICY_MAX_MERGED_SEGMENT, new ByteSizeValue(TieredMergePolicyProvider.DEFAULT_MAX_MERGED_SEGMENT.bytes() + 1)).build());
        assertEquals(mp.getMergePolicy().getMaxMergedSegmentMB(), new ByteSizeValue(TieredMergePolicyProvider.DEFAULT_MAX_MERGED_SEGMENT.bytes() + 1).mbFrac(), 0.0001);

        assertEquals(mp.getMergePolicy().getReclaimDeletesWeight(), TieredMergePolicyProvider.DEFAULT_RECLAIM_DELETES_WEIGHT, 0);
        service.refreshSettings(Settings.builder().put(TieredMergePolicyProvider.INDEX_MERGE_POLICY_RECLAIM_DELETES_WEIGHT, TieredMergePolicyProvider.DEFAULT_RECLAIM_DELETES_WEIGHT + 1 ).build());
        assertEquals(mp.getMergePolicy().getReclaimDeletesWeight(), TieredMergePolicyProvider.DEFAULT_RECLAIM_DELETES_WEIGHT + 1, 0);

        assertEquals(mp.getMergePolicy().getSegmentsPerTier(), TieredMergePolicyProvider.DEFAULT_SEGMENTS_PER_TIER, 0);
        service.refreshSettings(Settings.builder().put(TieredMergePolicyProvider.INDEX_MERGE_POLICY_SEGMENTS_PER_TIER, TieredMergePolicyProvider.DEFAULT_SEGMENTS_PER_TIER + 1 ).build());
        assertEquals(mp.getMergePolicy().getSegmentsPerTier(), TieredMergePolicyProvider.DEFAULT_SEGMENTS_PER_TIER + 1, 0);

        service.refreshSettings(EMPTY_SETTINGS); // update without the settings and see if we stick to the values

        assertEquals(mp.getMergePolicy().getForceMergeDeletesPctAllowed(), TieredMergePolicyProvider.DEFAULT_EXPUNGE_DELETES_ALLOWED + 1.0d, 0.0d);
        assertEquals(mp.getMergePolicy().getFloorSegmentMB(), new ByteSizeValue(TieredMergePolicyProvider.DEFAULT_FLOOR_SEGMENT.mb() + 1, ByteSizeUnit.MB).mbFrac(), 0.001);
        assertEquals(mp.getMergePolicy().getMaxMergeAtOnce(), TieredMergePolicyProvider.DEFAULT_MAX_MERGE_AT_ONCE-1);
        assertEquals(mp.getMergePolicy().getMaxMergeAtOnceExplicit(), TieredMergePolicyProvider.DEFAULT_MAX_MERGE_AT_ONCE_EXPLICIT-1);
        assertEquals(mp.getMergePolicy().getMaxMergedSegmentMB(), new ByteSizeValue(TieredMergePolicyProvider.DEFAULT_MAX_MERGED_SEGMENT.bytes() + 1).mbFrac(), 0.0001);
        assertEquals(mp.getMergePolicy().getReclaimDeletesWeight(), TieredMergePolicyProvider.DEFAULT_RECLAIM_DELETES_WEIGHT + 1, 0);
        assertEquals(mp.getMergePolicy().getSegmentsPerTier(), TieredMergePolicyProvider.DEFAULT_SEGMENTS_PER_TIER + 1, 0);
    }

    public Settings build(String value) {
        return Settings.builder().put(AbstractMergePolicyProvider.INDEX_COMPOUND_FORMAT, value).build();
    }

    public Settings build(double value) {
        return Settings.builder().put(AbstractMergePolicyProvider.INDEX_COMPOUND_FORMAT, value).build();
    }

    public Settings build(int value) {
        return Settings.builder().put(AbstractMergePolicyProvider.INDEX_COMPOUND_FORMAT, value).build();
    }

    public Settings build(boolean value) {
        return Settings.builder().put(AbstractMergePolicyProvider.INDEX_COMPOUND_FORMAT, value).build();
    }

    protected Store createStore(Settings settings) throws IOException {
        final DirectoryService directoryService = new DirectoryService(shardId, EMPTY_SETTINGS) {
            @Override
            public Directory newDirectory() throws IOException {
                return  new RAMDirectory() ;
            }

            @Override
            public long throttleTimeInNanos() {
                return 0;
            }
        };
        return new Store(shardId, settings, directoryService, new DummyShardLock(shardId));
    }

}


File: core/src/test/java/org/elasticsearch/index/store/CorruptedFileTest.java
/*
 * Licensed to Elasticsearch under one or more contributor
 * license agreements. See the NOTICE file distributed with
 * this work for additional information regarding copyright
 * ownership. Elasticsearch licenses this file to you under
 * the Apache License, Version 2.0 (the "License"); you may
 * not use this file except in compliance with the License.
 * You may obtain a copy of the License at
 *
 *    http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing,
 * software distributed under the License is distributed on an
 * "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY
 * KIND, either express or implied.  See the License for the
 * specific language governing permissions and limitations
 * under the License.
 */
package org.elasticsearch.index.store;

import com.carrotsearch.ant.tasks.junit4.dependencies.com.google.common.collect.Lists;
import com.carrotsearch.randomizedtesting.generators.RandomPicks;
import com.google.common.base.Charsets;
import com.google.common.base.Predicate;
import org.apache.lucene.codecs.CodecUtil;
import org.apache.lucene.index.CheckIndex;
import org.apache.lucene.index.IndexFileNames;
import org.apache.lucene.store.*;
import org.elasticsearch.action.admin.cluster.health.ClusterHealthResponse;
import org.elasticsearch.action.admin.cluster.health.ClusterHealthStatus;
import org.elasticsearch.action.admin.cluster.node.stats.NodeStats;
import org.elasticsearch.action.admin.cluster.node.stats.NodesStatsResponse;
import org.elasticsearch.action.admin.cluster.snapshots.create.CreateSnapshotResponse;
import org.elasticsearch.action.admin.cluster.state.ClusterStateResponse;
import org.elasticsearch.action.count.CountResponse;
import org.elasticsearch.action.index.IndexRequestBuilder;
import org.elasticsearch.action.search.SearchResponse;
import org.elasticsearch.client.Requests;
import org.elasticsearch.cluster.ClusterState;
import org.elasticsearch.cluster.metadata.IndexMetaData;
import org.elasticsearch.cluster.node.DiscoveryNode;
import org.elasticsearch.cluster.routing.*;
import org.elasticsearch.cluster.routing.allocation.decider.EnableAllocationDecider;
import org.elasticsearch.cluster.routing.allocation.decider.ThrottlingAllocationDecider;
import org.elasticsearch.common.Nullable;
import org.elasticsearch.common.bytes.BytesArray;
import org.elasticsearch.common.io.PathUtils;
import org.elasticsearch.common.io.stream.BytesStreamOutput;
import org.elasticsearch.common.lucene.Lucene;
import org.elasticsearch.common.settings.Settings;
import org.elasticsearch.common.unit.ByteSizeUnit;
import org.elasticsearch.discovery.Discovery;
import org.elasticsearch.gateway.GatewayAllocator;
import org.elasticsearch.index.merge.policy.MergePolicyModule;
import org.elasticsearch.index.settings.IndexSettings;
import org.elasticsearch.index.shard.IndexShard;
import org.elasticsearch.index.shard.IndexShardException;
import org.elasticsearch.index.shard.IndexShardState;
import org.elasticsearch.index.shard.ShardId;
import org.elasticsearch.index.translog.TranslogService;
import org.elasticsearch.indices.IndicesLifecycle;
import org.elasticsearch.indices.IndicesService;
import org.elasticsearch.indices.recovery.RecoveryFileChunkRequest;
import org.elasticsearch.indices.recovery.RecoverySettings;
import org.elasticsearch.indices.recovery.RecoveryTarget;
import org.elasticsearch.monitor.fs.FsStats;
import org.elasticsearch.snapshots.SnapshotState;
import org.elasticsearch.test.ElasticsearchIntegrationTest;
import org.elasticsearch.test.InternalTestCluster;
import org.elasticsearch.test.index.merge.NoMergePolicyProvider;
import org.elasticsearch.test.store.MockFSDirectoryService;
import org.elasticsearch.test.transport.MockTransportService;
import org.elasticsearch.transport.*;
import org.junit.Test;

import java.io.IOException;
import java.io.OutputStream;
import java.io.PrintStream;
import java.nio.ByteBuffer;
import java.nio.channels.FileChannel;
import java.nio.file.DirectoryStream;
import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.StandardOpenOption;
import java.util.*;
import java.util.concurrent.CopyOnWriteArrayList;
import java.util.concurrent.CountDownLatch;
import java.util.concurrent.ExecutionException;
import java.util.concurrent.TimeUnit;
import java.util.concurrent.atomic.AtomicBoolean;

import static org.elasticsearch.common.settings.Settings.settingsBuilder;
import static org.elasticsearch.test.hamcrest.ElasticsearchAssertions.*;
import static org.hamcrest.Matchers.*;

@ElasticsearchIntegrationTest.ClusterScope(scope = ElasticsearchIntegrationTest.Scope.SUITE)
public class CorruptedFileTest extends ElasticsearchIntegrationTest {

    @Override
    protected Settings nodeSettings(int nodeOrdinal) {
        return Settings.builder()
                // we really need local GW here since this also checks for corruption etc.
                // and we need to make sure primaries are not just trashed if we don't have replicas
                .put(super.nodeSettings(nodeOrdinal))
                .put(TransportModule.TRANSPORT_SERVICE_TYPE_KEY, MockTransportService.class.getName())
                        // speed up recoveries
                .put(RecoverySettings.INDICES_RECOVERY_CONCURRENT_STREAMS, 10)
                .put(RecoverySettings.INDICES_RECOVERY_CONCURRENT_SMALL_FILE_STREAMS, 10)
                .put(ThrottlingAllocationDecider.CLUSTER_ROUTING_ALLOCATION_NODE_CONCURRENT_RECOVERIES, 5)
                .build();
    }

    /**
     * Tests that we can actually recover from a corruption on the primary given that we have replica shards around.
     */
    @Test
    public void testCorruptFileAndRecover() throws ExecutionException, InterruptedException, IOException {
        int numDocs = scaledRandomIntBetween(100, 1000);
        // have enough space for 3 copies
        internalCluster().ensureAtLeastNumDataNodes(3);
        if (cluster().numDataNodes() == 3) {
            logger.info("--> cluster has [3] data nodes, corrupted primary will be overwritten");
        }

        assertThat(cluster().numDataNodes(), greaterThanOrEqualTo(3));

        assertAcked(prepareCreate("test").setSettings(Settings.builder()
                        .put(IndexMetaData.SETTING_NUMBER_OF_SHARDS, "1")
                        .put(IndexMetaData.SETTING_NUMBER_OF_REPLICAS, "1")
                        .put(MergePolicyModule.MERGE_POLICY_TYPE_KEY, NoMergePolicyProvider.class)
                        .put(MockFSDirectoryService.CHECK_INDEX_ON_CLOSE, false) // no checkindex - we corrupt shards on purpose
                        .put(TranslogService.INDEX_TRANSLOG_DISABLE_FLUSH, true) // no translog based flush - it might change the .liv / segments.N files
                        .put("indices.recovery.concurrent_streams", 10)
        ));
        ensureGreen();
        disableAllocation("test");
        IndexRequestBuilder[] builders = new IndexRequestBuilder[numDocs];
        for (int i = 0; i < builders.length; i++) {
            builders[i] = client().prepareIndex("test", "type").setSource("field", "value");
        }
        indexRandom(true, builders);
        ensureGreen();
        assertAllSuccessful(client().admin().indices().prepareFlush().setForce(true).setWaitIfOngoing(true).execute().actionGet());
        // we have to flush at least once here since we don't corrupt the translog
        CountResponse countResponse = client().prepareCount().get();
        assertHitCount(countResponse, numDocs);

        final int numShards = numShards("test");
        ShardRouting corruptedShardRouting = corruptRandomPrimaryFile();
        logger.info("--> {} corrupted", corruptedShardRouting);
        enableAllocation("test");
         /*
         * we corrupted the primary shard - now lets make sure we never recover from it successfully
         */
        Settings build = Settings.builder().put(IndexMetaData.SETTING_NUMBER_OF_REPLICAS, "2").build();
        client().admin().indices().prepareUpdateSettings("test").setSettings(build).get();
        ClusterHealthResponse health = client().admin().cluster()
                .health(Requests.clusterHealthRequest("test").waitForGreenStatus()
                        .timeout("5m") // sometimes due to cluster rebalacing and random settings default timeout is just not enough.
                        .waitForRelocatingShards(0)).actionGet();
        if (health.isTimedOut()) {
            logger.info("cluster state:\n{}\n{}", client().admin().cluster().prepareState().get().getState().prettyPrint(), client().admin().cluster().preparePendingClusterTasks().get().prettyPrint());
            assertThat("timed out waiting for green state", health.isTimedOut(), equalTo(false));
        }
        assertThat(health.getStatus(), equalTo(ClusterHealthStatus.GREEN));
        final int numIterations = scaledRandomIntBetween(5, 20);
        for (int i = 0; i < numIterations; i++) {
            SearchResponse response = client().prepareSearch().setSize(numDocs).get();
            assertHitCount(response, numDocs);
        }



        /*
         * now hook into the IndicesService and register a close listener to
         * run the checkindex. if the corruption is still there we will catch it.
         */
        final CountDownLatch latch = new CountDownLatch(numShards * 3); // primary + 2 replicas
        final CopyOnWriteArrayList<Throwable> exception = new CopyOnWriteArrayList<>();
        final IndicesLifecycle.Listener listener = new IndicesLifecycle.Listener() {
            @Override
            public void afterIndexShardClosed(ShardId sid, @Nullable IndexShard indexShard, @IndexSettings Settings indexSettings) {
                if (indexShard != null) {
                    Store store = ((IndexShard) indexShard).store();
                    store.incRef();
                    try {
                        if (!Lucene.indexExists(store.directory()) && indexShard.state() == IndexShardState.STARTED) {
                            return;
                        }
                        try (CheckIndex checkIndex = new CheckIndex(store.directory())) {
                            BytesStreamOutput os = new BytesStreamOutput();
                            PrintStream out = new PrintStream(os, false, Charsets.UTF_8.name());
                            checkIndex.setInfoStream(out);
                            out.flush();
                            CheckIndex.Status status = checkIndex.checkIndex();
                            if (!status.clean) {
                                logger.warn("check index [failure]\n{}", new String(os.bytes().toBytes(), Charsets.UTF_8));
                                throw new IndexShardException(sid, "index check failure");
                            }
                        }
                    } catch (Throwable t) {
                        exception.add(t);
                    } finally {
                        store.decRef();
                        latch.countDown();
                    }
                }
            }
        };

        for (IndicesService service : internalCluster().getDataNodeInstances(IndicesService.class)) {
            service.indicesLifecycle().addListener(listener);
        }
        try {
            client().admin().indices().prepareDelete("test").get();
            latch.await();
            assertThat(exception, empty());
        } finally {
            for (IndicesService service : internalCluster().getDataNodeInstances(IndicesService.class)) {
                service.indicesLifecycle().removeListener(listener);
            }
        }
    }

    /**
     * Tests corruption that happens on a single shard when no replicas are present. We make sure that the primary stays unassigned
     * and all other replicas for the healthy shards happens
     */
    @Test
    public void testCorruptPrimaryNoReplica() throws ExecutionException, InterruptedException, IOException {
        int numDocs = scaledRandomIntBetween(100, 1000);
        internalCluster().ensureAtLeastNumDataNodes(2);

        assertAcked(prepareCreate("test").setSettings(Settings.builder()
                        .put(IndexMetaData.SETTING_NUMBER_OF_REPLICAS, "0")
                        .put(MergePolicyModule.MERGE_POLICY_TYPE_KEY, NoMergePolicyProvider.class)
                        .put(MockFSDirectoryService.CHECK_INDEX_ON_CLOSE, false) // no checkindex - we corrupt shards on purpose
                        .put(TranslogService.INDEX_TRANSLOG_DISABLE_FLUSH, true) // no translog based flush - it might change the .liv / segments.N files
                        .put("indices.recovery.concurrent_streams", 10)
        ));
        ensureGreen();
        IndexRequestBuilder[] builders = new IndexRequestBuilder[numDocs];
        for (int i = 0; i < builders.length; i++) {
            builders[i] = client().prepareIndex("test", "type").setSource("field", "value");
        }
        indexRandom(true, builders);
        ensureGreen();
        assertAllSuccessful(client().admin().indices().prepareFlush().setForce(true).setWaitIfOngoing(true).execute().actionGet());
        // we have to flush at least once here since we don't corrupt the translog
        CountResponse countResponse = client().prepareCount().get();
        assertHitCount(countResponse, numDocs);

        ShardRouting shardRouting = corruptRandomPrimaryFile();
        /*
         * we corrupted the primary shard - now lets make sure we never recover from it successfully
         */
        Settings build = Settings.builder().put(IndexMetaData.SETTING_NUMBER_OF_REPLICAS, "1").build();
        client().admin().indices().prepareUpdateSettings("test").setSettings(build).get();
        client().admin().cluster().prepareReroute().get();

        boolean didClusterTurnRed = awaitBusy(new Predicate<Object>() {
            @Override
            public boolean apply(Object input) {
                ClusterHealthStatus test = client().admin().cluster()
                        .health(Requests.clusterHealthRequest("test")).actionGet().getStatus();
                return test == ClusterHealthStatus.RED;
            }
        }, 5, TimeUnit.MINUTES);// sometimes on slow nodes the replication / recovery is just dead slow
        final ClusterHealthResponse response = client().admin().cluster()
                .health(Requests.clusterHealthRequest("test")).get();
        if (response.getStatus() != ClusterHealthStatus.RED) {
            logger.info("Cluster turned red in busy loop: {}", didClusterTurnRed);
            logger.info("cluster state:\n{}\n{}", client().admin().cluster().prepareState().get().getState().prettyPrint(), client().admin().cluster().preparePendingClusterTasks().get().prettyPrint());
        }
        assertThat(response.getStatus(), is(ClusterHealthStatus.RED));
        ClusterState state = client().admin().cluster().prepareState().get().getState();
        GroupShardsIterator shardIterators = state.getRoutingNodes().getRoutingTable().activePrimaryShardsGrouped(new String[]{"test"}, false);
        for (ShardIterator iterator : shardIterators) {
            ShardRouting routing;
            while ((routing = iterator.nextOrNull()) != null) {
                if (routing.getId() == shardRouting.getId()) {
                    assertThat(routing.state(), equalTo(ShardRoutingState.UNASSIGNED));
                } else {
                    assertThat(routing.state(), anyOf(equalTo(ShardRoutingState.RELOCATING), equalTo(ShardRoutingState.STARTED)));
                }
            }
        }
        final List<Path> files = listShardFiles(shardRouting);
        Path corruptedFile = null;
        for (Path file : files) {
            if (file.getFileName().toString().startsWith("corrupted_")) {
                corruptedFile = file;
                break;
            }
        }
        assertThat(corruptedFile, notNullValue());
    }

    /**
     * This test triggers a corrupt index exception during finalization size if an empty commit point is transferred
     * during recovery we don't know the version of the segments_N file because it has no segments we can take it from.
     * This simulates recoveries from old indices or even without checksums and makes sure if we fail during finalization
     * we also check if the primary is ok. Without the relevant checks this test fails with a RED cluster
     */
    public void testCorruptionOnNetworkLayerFinalizingRecovery() throws ExecutionException, InterruptedException, IOException {
        internalCluster().ensureAtLeastNumDataNodes(2);
        NodesStatsResponse nodeStats = client().admin().cluster().prepareNodesStats().get();
        List<NodeStats> dataNodeStats = new ArrayList<>();
        for (NodeStats stat : nodeStats.getNodes()) {
            if (stat.getNode().isDataNode()) {
                dataNodeStats.add(stat);
            }
        }

        assertThat(dataNodeStats.size(), greaterThanOrEqualTo(2));
        Collections.shuffle(dataNodeStats, getRandom());
        NodeStats primariesNode = dataNodeStats.get(0);
        NodeStats unluckyNode = dataNodeStats.get(1);
        assertAcked(prepareCreate("test").setSettings(Settings.builder()
                        .put(IndexMetaData.SETTING_NUMBER_OF_REPLICAS, "0")
                        .put(IndexMetaData.SETTING_NUMBER_OF_SHARDS, 1)
                        .put("index.routing.allocation.include._name", primariesNode.getNode().name())
                        .put(EnableAllocationDecider.INDEX_ROUTING_REBALANCE_ENABLE, EnableAllocationDecider.Rebalance.NONE)

        ));
        ensureGreen(); // allocated with empty commit
        final AtomicBoolean corrupt = new AtomicBoolean(true);
        final CountDownLatch hasCorrupted = new CountDownLatch(1);
        for (NodeStats dataNode : dataNodeStats) {
            MockTransportService mockTransportService = ((MockTransportService) internalCluster().getInstance(TransportService.class, dataNode.getNode().name()));
            mockTransportService.addDelegate(internalCluster().getInstance(Discovery.class, unluckyNode.getNode().name()).localNode(), new MockTransportService.DelegateTransport(mockTransportService.original()) {

                @Override
                public void sendRequest(DiscoveryNode node, long requestId, String action, TransportRequest request, TransportRequestOptions options) throws IOException, TransportException {
                    if (corrupt.get() && action.equals(RecoveryTarget.Actions.FILE_CHUNK)) {
                        RecoveryFileChunkRequest req = (RecoveryFileChunkRequest) request;
                        byte[] array = req.content().array();
                        int i = randomIntBetween(0, req.content().length() - 1);
                        array[i] = (byte) ~array[i]; // flip one byte in the content
                        hasCorrupted.countDown();
                    }
                    super.sendRequest(node, requestId, action, request, options);
                }
            });
        }

        Settings build = Settings.builder()
                .put(IndexMetaData.SETTING_NUMBER_OF_REPLICAS, "1")
                .put("index.routing.allocation.include._name", primariesNode.getNode().name() + "," + unluckyNode.getNode().name()).build();
        client().admin().indices().prepareUpdateSettings("test").setSettings(build).get();
        client().admin().cluster().prepareReroute().get();
        hasCorrupted.await();
        corrupt.set(false);
        ensureGreen();
    }

    /**
     * Tests corruption that happens on the network layer and that the primary does not get affected by corruption that happens on the way
     * to the replica. The file on disk stays uncorrupted
     */
    @Test
    public void testCorruptionOnNetworkLayer() throws ExecutionException, InterruptedException {
        int numDocs = scaledRandomIntBetween(100, 1000);
        internalCluster().ensureAtLeastNumDataNodes(2);
        if (cluster().numDataNodes() < 3) {
            internalCluster().startNode(Settings.builder().put("node.data", true).put("node.client", false).put("node.master", false));
        }
        NodesStatsResponse nodeStats = client().admin().cluster().prepareNodesStats().get();
        List<NodeStats> dataNodeStats = new ArrayList<>();
        for (NodeStats stat : nodeStats.getNodes()) {
            if (stat.getNode().isDataNode()) {
                dataNodeStats.add(stat);
            }
        }

        assertThat(dataNodeStats.size(), greaterThanOrEqualTo(2));
        Collections.shuffle(dataNodeStats, getRandom());
        NodeStats primariesNode = dataNodeStats.get(0);
        NodeStats unluckyNode = dataNodeStats.get(1);


        assertAcked(prepareCreate("test").setSettings(Settings.builder()
                        .put(IndexMetaData.SETTING_NUMBER_OF_REPLICAS, "0")
                        .put(IndexMetaData.SETTING_NUMBER_OF_SHARDS, between(1, 4)) // don't go crazy here it must recovery fast
                                // This does corrupt files on the replica, so we can't check:
                        .put(MockFSDirectoryService.CHECK_INDEX_ON_CLOSE, false)
                        .put("index.routing.allocation.include._name", primariesNode.getNode().name())
                        .put(EnableAllocationDecider.INDEX_ROUTING_REBALANCE_ENABLE, EnableAllocationDecider.Rebalance.NONE)
        ));
        ensureGreen();
        IndexRequestBuilder[] builders = new IndexRequestBuilder[numDocs];
        for (int i = 0; i < builders.length; i++) {
            builders[i] = client().prepareIndex("test", "type").setSource("field", "value");
        }
        indexRandom(true, builders);
        ensureGreen();
        assertAllSuccessful(client().admin().indices().prepareFlush().setForce(true).setWaitIfOngoing(true).execute().actionGet());
        // we have to flush at least once here since we don't corrupt the translog
        CountResponse countResponse = client().prepareCount().get();
        assertHitCount(countResponse, numDocs);
        final boolean truncate = randomBoolean();
        for (NodeStats dataNode : dataNodeStats) {
            MockTransportService mockTransportService = ((MockTransportService) internalCluster().getInstance(TransportService.class, dataNode.getNode().name()));
            mockTransportService.addDelegate(internalCluster().getInstance(Discovery.class, unluckyNode.getNode().name()).localNode(), new MockTransportService.DelegateTransport(mockTransportService.original()) {

                @Override
                public void sendRequest(DiscoveryNode node, long requestId, String action, TransportRequest request, TransportRequestOptions options) throws IOException, TransportException {
                    if (action.equals(RecoveryTarget.Actions.FILE_CHUNK)) {
                        RecoveryFileChunkRequest req = (RecoveryFileChunkRequest) request;
                        if (truncate && req.length() > 1) {
                            BytesArray array = new BytesArray(req.content().array(), req.content().arrayOffset(), (int) req.length() - 1);
                            request = new RecoveryFileChunkRequest(req.recoveryId(), req.shardId(), req.metadata(), req.position(), array, req.lastChunk(), req.totalTranslogOps(), req.sourceThrottleTimeInNanos());
                        } else {
                            byte[] array = req.content().array();
                            int i = randomIntBetween(0, req.content().length() - 1);
                            array[i] = (byte) ~array[i]; // flip one byte in the content
                        }
                    }
                    super.sendRequest(node, requestId, action, request, options);
                }
            });
        }

        Settings build = Settings.builder()
                .put(IndexMetaData.SETTING_NUMBER_OF_REPLICAS, "1")
                .put("index.routing.allocation.include._name", "*").build();
        client().admin().indices().prepareUpdateSettings("test").setSettings(build).get();
        client().admin().cluster().prepareReroute().get();
        ClusterHealthResponse actionGet = client().admin().cluster()
                .health(Requests.clusterHealthRequest("test").waitForGreenStatus()).actionGet();
        if (actionGet.isTimedOut()) {
            logger.info("ensureGreen timed out, cluster state:\n{}\n{}", client().admin().cluster().prepareState().get().getState().prettyPrint(), client().admin().cluster().preparePendingClusterTasks().get().prettyPrint());
            assertThat("timed out waiting for green state", actionGet.isTimedOut(), equalTo(false));
        }
        // we are green so primaries got not corrupted.
        // ensure that no shard is actually allocated on the unlucky node
        ClusterStateResponse clusterStateResponse = client().admin().cluster().prepareState().get();
        for (IndexShardRoutingTable table : clusterStateResponse.getState().routingNodes().getRoutingTable().index("test")) {
            for (ShardRouting routing : table) {
                if (unluckyNode.getNode().getId().equals(routing.currentNodeId())) {
                    assertThat(routing.state(), not(equalTo(ShardRoutingState.STARTED)));
                    assertThat(routing.state(), not(equalTo(ShardRoutingState.RELOCATING)));
                }
            }
        }
        final int numIterations = scaledRandomIntBetween(5, 20);
        for (int i = 0; i < numIterations; i++) {
            SearchResponse response = client().prepareSearch().setSize(numDocs).get();
            assertHitCount(response, numDocs);
        }

    }


    /**
     * Tests that restoring of a corrupted shard fails and we get a partial snapshot.
     * TODO once checksum verification on snapshotting is implemented this test needs to be fixed or split into several
     * parts... We should also corrupt files on the actual snapshot and check that we don't restore the corrupted shard.
     */
    @Test
    public void testCorruptFileThenSnapshotAndRestore() throws ExecutionException, InterruptedException, IOException {
        int numDocs = scaledRandomIntBetween(100, 1000);
        internalCluster().ensureAtLeastNumDataNodes(2);

        assertAcked(prepareCreate("test").setSettings(Settings.builder()
                        .put(IndexMetaData.SETTING_NUMBER_OF_REPLICAS, "0") // no replicas for this test
                        .put(MergePolicyModule.MERGE_POLICY_TYPE_KEY, NoMergePolicyProvider.class)
                        .put(MockFSDirectoryService.CHECK_INDEX_ON_CLOSE, false) // no checkindex - we corrupt shards on purpose
                        .put(TranslogService.INDEX_TRANSLOG_DISABLE_FLUSH, true) // no translog based flush - it might change the .liv / segments.N files
                        .put("indices.recovery.concurrent_streams", 10)
        ));
        ensureGreen();
        IndexRequestBuilder[] builders = new IndexRequestBuilder[numDocs];
        for (int i = 0; i < builders.length; i++) {
            builders[i] = client().prepareIndex("test", "type").setSource("field", "value");
        }
        indexRandom(true, builders);
        ensureGreen();
        assertAllSuccessful(client().admin().indices().prepareFlush().setForce(true).setWaitIfOngoing(true).execute().actionGet());
        // we have to flush at least once here since we don't corrupt the translog
        CountResponse countResponse = client().prepareCount().get();
        assertHitCount(countResponse, numDocs);

        ShardRouting shardRouting = corruptRandomPrimaryFile(false);
        // we don't corrupt segments.gen since S/R doesn't snapshot this file
        // the other problem here why we can't corrupt segments.X files is that the snapshot flushes again before
        // it snapshots and that will write a new segments.X+1 file
        logger.info("-->  creating repository");
        assertAcked(client().admin().cluster().preparePutRepository("test-repo")
                .setType("fs").setSettings(settingsBuilder()
                        .put("location", randomRepoPath().toAbsolutePath())
                        .put("compress", randomBoolean())
                        .put("chunk_size", randomIntBetween(100, 1000), ByteSizeUnit.BYTES)));
        logger.info("--> snapshot");
        CreateSnapshotResponse createSnapshotResponse = client().admin().cluster().prepareCreateSnapshot("test-repo", "test-snap").setWaitForCompletion(true).setIndices("test").get();
        assertThat(createSnapshotResponse.getSnapshotInfo().state(), equalTo(SnapshotState.PARTIAL));
        logger.info("failed during snapshot -- maybe SI file got corrupted");
        final List<Path> files = listShardFiles(shardRouting);
        Path corruptedFile = null;
        for (Path file : files) {
            if (file.getFileName().toString().startsWith("corrupted_")) {
                corruptedFile = file;
                break;
            }
        }
        assertThat(corruptedFile, notNullValue());
    }

    /**
     * This test verifies that if we corrupt a replica, we can still get to green, even though
     * listing its store fails. Note, we need to make sure that replicas are allocated on all data
     * nodes, so that replica won't be sneaky and allocated on a node that doesn't have a corrupted
     * replica.
     */
    @Test
    public void testReplicaCorruption() throws Exception {
        int numDocs = scaledRandomIntBetween(100, 1000);
        internalCluster().ensureAtLeastNumDataNodes(2);

        assertAcked(prepareCreate("test").setSettings(Settings.builder()
                        .put(GatewayAllocator.INDEX_RECOVERY_INITIAL_SHARDS, "one")
                        .put(IndexMetaData.SETTING_NUMBER_OF_REPLICAS, cluster().numDataNodes() - 1)
                        .put(MergePolicyModule.MERGE_POLICY_TYPE_KEY, NoMergePolicyProvider.class)
                        .put(MockFSDirectoryService.CHECK_INDEX_ON_CLOSE, false) // no checkindex - we corrupt shards on purpose
                        .put(TranslogService.INDEX_TRANSLOG_DISABLE_FLUSH, true) // no translog based flush - it might change the .liv / segments.N files
                        .put("indices.recovery.concurrent_streams", 10)
        ));
        ensureGreen();
        IndexRequestBuilder[] builders = new IndexRequestBuilder[numDocs];
        for (int i = 0; i < builders.length; i++) {
            builders[i] = client().prepareIndex("test", "type").setSource("field", "value");
        }
        indexRandom(true, builders);
        ensureGreen();
        assertAllSuccessful(client().admin().indices().prepareFlush().setForce(true).setWaitIfOngoing(true).execute().actionGet());
        // we have to flush at least once here since we don't corrupt the translog
        CountResponse countResponse = client().prepareCount().get();
        assertHitCount(countResponse, numDocs);

        final Map<String, List<Path>> filesToCorrupt = findFilesToCorruptForReplica();
        internalCluster().fullRestart(new InternalTestCluster.RestartCallback() {
            @Override
            public Settings onNodeStopped(String nodeName) throws Exception {
                List<Path> paths = filesToCorrupt.get(nodeName);
                if (paths != null) {
                    for (Path path : paths) {
                        try (OutputStream os = Files.newOutputStream(path)) {
                            os.write(0);
                        }
                        logger.info("corrupting file {} on node {}", path, nodeName);
                    }
                }
                return null;
            }
        });
        ensureGreen();
    }

    private int numShards(String... index) {
        ClusterState state = client().admin().cluster().prepareState().get().getState();
        GroupShardsIterator shardIterators = state.getRoutingNodes().getRoutingTable().activePrimaryShardsGrouped(index, false);
        return shardIterators.size();
    }

    private Map<String, List<Path>> findFilesToCorruptForReplica() throws IOException {
        Map<String, List<Path>> filesToNodes = new HashMap<>();
        ClusterState state = client().admin().cluster().prepareState().get().getState();
        for (ShardRouting shardRouting : state.getRoutingTable().allShards("test")) {
            if (shardRouting.primary() == true) {
                continue;
            }
            assertTrue(shardRouting.assignedToNode());
            NodesStatsResponse nodeStatses = client().admin().cluster().prepareNodesStats(shardRouting.currentNodeId()).setFs(true).get();
            NodeStats nodeStats = nodeStatses.getNodes()[0];
            List<Path> files = new ArrayList<>();
            filesToNodes.put(nodeStats.getNode().getName(), files);
            for (FsStats.Info info : nodeStats.getFs()) {
                String path = info.getPath();
                final String relativeDataLocationPath = "indices/test/" + Integer.toString(shardRouting.getId()) + "/index";
                Path file = PathUtils.get(path).resolve(relativeDataLocationPath);
                if (Files.exists(file)) { // multi data path might only have one path in use
                    try (DirectoryStream<Path> stream = Files.newDirectoryStream(file)) {
                        for (Path item : stream) {
                            if (item.getFileName().toString().startsWith("segments_")) {
                                files.add(item);
                            }
                        }
                    }
                }
            }
        }
        return filesToNodes;
    }

    private ShardRouting corruptRandomPrimaryFile() throws IOException {
        return corruptRandomPrimaryFile(true);
    }

    private ShardRouting corruptRandomPrimaryFile(final boolean includePerCommitFiles) throws IOException {
        ClusterState state = client().admin().cluster().prepareState().get().getState();
        GroupShardsIterator shardIterators = state.getRoutingNodes().getRoutingTable().activePrimaryShardsGrouped(new String[]{"test"}, false);
        List<ShardIterator> iterators = Lists.newArrayList(shardIterators);
        ShardIterator shardIterator = RandomPicks.randomFrom(getRandom(), iterators);
        ShardRouting shardRouting = shardIterator.nextOrNull();
        assertNotNull(shardRouting);
        assertTrue(shardRouting.primary());
        assertTrue(shardRouting.assignedToNode());
        String nodeId = shardRouting.currentNodeId();
        NodesStatsResponse nodeStatses = client().admin().cluster().prepareNodesStats(nodeId).setFs(true).get();
        Set<Path> files = new TreeSet<>(); // treeset makes sure iteration order is deterministic
        for (FsStats.Info info : nodeStatses.getNodes()[0].getFs()) {
            String path = info.getPath();
            final String relativeDataLocationPath = "indices/test/" + Integer.toString(shardRouting.getId()) + "/index";
            Path file = PathUtils.get(path).resolve(relativeDataLocationPath);
            if (Files.exists(file)) { // multi data path might only have one path in use
                try (DirectoryStream<Path> stream = Files.newDirectoryStream(file)) {
                    for (Path item : stream) {
                        if (Files.isRegularFile(item) && "write.lock".equals(item.getFileName().toString()) == false) {
                            if (includePerCommitFiles || isPerSegmentFile(item.getFileName().toString())) {
                                files.add(item);
                            }
                        }
                    }
                }
            }
        }
        pruneOldDeleteGenerations(files);
        Path fileToCorrupt = null;
        if (!files.isEmpty()) {
            fileToCorrupt = RandomPicks.randomFrom(getRandom(), files);
            try (Directory dir = FSDirectory.open(fileToCorrupt.toAbsolutePath().getParent())) {
                long checksumBeforeCorruption;
                try (IndexInput input = dir.openInput(fileToCorrupt.getFileName().toString(), IOContext.DEFAULT)) {
                    checksumBeforeCorruption = CodecUtil.retrieveChecksum(input);
                }
                try (FileChannel raf = FileChannel.open(fileToCorrupt, StandardOpenOption.READ, StandardOpenOption.WRITE)) {
                    // read
                    raf.position(randomIntBetween(0, (int) Math.min(Integer.MAX_VALUE, raf.size() - 1)));
                    long filePointer = raf.position();
                    ByteBuffer bb = ByteBuffer.wrap(new byte[1]);
                    raf.read(bb);
                    bb.flip();

                    // corrupt
                    byte oldValue = bb.get(0);
                    byte newValue = (byte) (oldValue + 1);
                    bb.put(0, newValue);

                    // rewrite
                    raf.position(filePointer);
                    raf.write(bb);
                    logger.info("Corrupting file for shard {} --  flipping at position {} from {} to {} file: {}", shardRouting, filePointer, Integer.toHexString(oldValue), Integer.toHexString(newValue), fileToCorrupt.getFileName());
                }
                long checksumAfterCorruption;
                long actualChecksumAfterCorruption;
                try (ChecksumIndexInput input = dir.openChecksumInput(fileToCorrupt.getFileName().toString(), IOContext.DEFAULT)) {
                    assertThat(input.getFilePointer(), is(0l));
                    input.seek(input.length() - 8); // one long is the checksum... 8 bytes
                    checksumAfterCorruption = input.getChecksum();
                    actualChecksumAfterCorruption = input.readLong();
                }
                // we need to add assumptions here that the checksums actually really don't match there is a small chance to get collisions
                // in the checksum which is ok though....
                StringBuilder msg = new StringBuilder();
                msg.append("Checksum before: [").append(checksumBeforeCorruption).append("]");
                msg.append(" after: [").append(checksumAfterCorruption).append("]");
                msg.append(" checksum value after corruption: ").append(actualChecksumAfterCorruption).append("]");
                msg.append(" file: ").append(fileToCorrupt.getFileName()).append(" length: ").append(dir.fileLength(fileToCorrupt.getFileName().toString()));
                logger.info(msg.toString());
                assumeTrue("Checksum collision - " + msg.toString(),
                        checksumAfterCorruption != checksumBeforeCorruption // collision
                                || actualChecksumAfterCorruption != checksumBeforeCorruption); // checksum corrupted
            }
        }
        assertThat("no file corrupted", fileToCorrupt, notNullValue());
        return shardRouting;
    }

    private static final boolean isPerCommitFile(String fileName) {
        // .liv and segments_N are per commit files and might change after corruption
        return fileName.startsWith("segments") || fileName.endsWith(".liv");
    }

    private static final boolean isPerSegmentFile(String fileName) {
        return isPerCommitFile(fileName) == false;
    }

    /**
     * prunes the list of index files such that only the latest del generation files are contained.
     */
    private void pruneOldDeleteGenerations(Set<Path> files) {
        final TreeSet<Path> delFiles = new TreeSet<>();
        for (Path file : files) {
            if (file.getFileName().toString().endsWith(".liv")) {
                delFiles.add(file);
            }
        }
        Path last = null;
        for (Path current : delFiles) {
            if (last != null) {
                final String newSegmentName = IndexFileNames.parseSegmentName(current.getFileName().toString());
                final String oldSegmentName = IndexFileNames.parseSegmentName(last.getFileName().toString());
                if (newSegmentName.equals(oldSegmentName)) {
                    int oldGen = Integer.parseInt(IndexFileNames.stripExtension(IndexFileNames.stripSegmentName(last.getFileName().toString())).replace("_", ""), Character.MAX_RADIX);
                    int newGen = Integer.parseInt(IndexFileNames.stripExtension(IndexFileNames.stripSegmentName(current.getFileName().toString())).replace("_", ""), Character.MAX_RADIX);
                    if (newGen > oldGen) {
                        files.remove(last);
                    } else {
                        files.remove(current);
                        continue;
                    }
                }
            }
            last = current;
        }
    }

    public List<Path> listShardFiles(ShardRouting routing) throws IOException {
        NodesStatsResponse nodeStatses = client().admin().cluster().prepareNodesStats(routing.currentNodeId()).setFs(true).get();

        assertThat(routing.toString(), nodeStatses.getNodes().length, equalTo(1));
        List<Path> files = new ArrayList<>();
        for (FsStats.Info info : nodeStatses.getNodes()[0].getFs()) {
            String path = info.getPath();
            Path file = PathUtils.get(path).resolve("indices/test/" + Integer.toString(routing.getId()) + "/index");
            if (Files.exists(file)) { // multi data path might only have one path in use
                try (DirectoryStream<Path> stream = Files.newDirectoryStream(file)) {
                    for (Path item : stream) {
                        files.add(item);
                    }
                }
            }
        }
        return files;
    }

    private void disableAllocation(String index) {
        client().admin().indices().prepareUpdateSettings(index).setSettings(Settings.builder().put(
                "index.routing.allocation.enable", "none"
        )).get();
    }

    private void enableAllocation(String index) {
        client().admin().indices().prepareUpdateSettings(index).setSettings(Settings.builder().put(
                "index.routing.allocation.enable", "all"
        )).get();
    }
}


File: core/src/test/java/org/elasticsearch/indices/settings/UpdateSettingsTests.java
/*
 * Licensed to Elasticsearch under one or more contributor
 * license agreements. See the NOTICE file distributed with
 * this work for additional information regarding copyright
 * ownership. Elasticsearch licenses this file to you under
 * the Apache License, Version 2.0 (the "License"); you may
 * not use this file except in compliance with the License.
 * You may obtain a copy of the License at
 *
 *    http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing,
 * software distributed under the License is distributed on an
 * "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY
 * KIND, either express or implied.  See the License for the
 * specific language governing permissions and limitations
 * under the License.
 */

package org.elasticsearch.indices.settings;

import org.apache.log4j.AppenderSkeleton;
import org.apache.log4j.Level;
import org.apache.log4j.Logger;
import org.apache.log4j.spi.LoggingEvent;
import org.elasticsearch.action.admin.cluster.health.ClusterHealthResponse;
import org.elasticsearch.action.admin.cluster.node.stats.NodeStats;
import org.elasticsearch.action.admin.cluster.node.stats.NodesStatsResponse;
import org.elasticsearch.action.admin.indices.settings.get.GetSettingsResponse;
import org.elasticsearch.cluster.metadata.IndexMetaData;
import org.elasticsearch.common.Priority;
import org.elasticsearch.common.settings.Settings;
import org.elasticsearch.index.engine.VersionConflictEngineException;
import org.elasticsearch.index.merge.policy.TieredMergePolicyProvider;
import org.elasticsearch.index.merge.scheduler.ConcurrentMergeSchedulerProvider;
import org.elasticsearch.index.store.IndexStore;
import org.elasticsearch.index.store.Store;
import org.elasticsearch.test.ElasticsearchIntegrationTest;
import org.junit.Test;

import java.util.Arrays;

import static org.elasticsearch.cluster.metadata.IndexMetaData.*;
import static org.elasticsearch.test.hamcrest.ElasticsearchAssertions.*;
import static org.hamcrest.Matchers.equalTo;
import static org.hamcrest.Matchers.nullValue;

public class UpdateSettingsTests extends ElasticsearchIntegrationTest {

    @Test
    public void testOpenCloseUpdateSettings() throws Exception {
        createIndex("test");
        try {
            client().admin().indices().prepareUpdateSettings("test")
                    .setSettings(Settings.settingsBuilder()
                            .put("index.refresh_interval", -1) // this one can change
                            .put("index.cache.filter.type", "none") // this one can't
                    )
                    .execute().actionGet();
            fail();
        } catch (IllegalArgumentException e) {
            // all is well
        }

        IndexMetaData indexMetaData = client().admin().cluster().prepareState().execute().actionGet().getState().metaData().index("test");
        assertThat(indexMetaData.settings().get("index.refresh_interval"), nullValue());
        assertThat(indexMetaData.settings().get("index.cache.filter.type"), nullValue());

        // Now verify via dedicated get settings api:
        GetSettingsResponse getSettingsResponse = client().admin().indices().prepareGetSettings("test").get();
        assertThat(getSettingsResponse.getSetting("test", "index.refresh_interval"), nullValue());
        assertThat(getSettingsResponse.getSetting("test", "index.cache.filter.type"), nullValue());

        client().admin().indices().prepareUpdateSettings("test")
                .setSettings(Settings.settingsBuilder()
                        .put("index.refresh_interval", -1) // this one can change
                )
                .execute().actionGet();

        indexMetaData = client().admin().cluster().prepareState().execute().actionGet().getState().metaData().index("test");
        assertThat(indexMetaData.settings().get("index.refresh_interval"), equalTo("-1"));
        // Now verify via dedicated get settings api:
        getSettingsResponse = client().admin().indices().prepareGetSettings("test").get();
        assertThat(getSettingsResponse.getSetting("test", "index.refresh_interval"), equalTo("-1"));

        // now close the index, change the non dynamic setting, and see that it applies

        // Wait for the index to turn green before attempting to close it
        ClusterHealthResponse health = client().admin().cluster().prepareHealth().setTimeout("30s").setWaitForEvents(Priority.LANGUID).setWaitForGreenStatus().execute().actionGet();
        assertThat(health.isTimedOut(), equalTo(false));

        client().admin().indices().prepareClose("test").execute().actionGet();

        try {
            client().admin().indices().prepareUpdateSettings("test")
                    .setSettings(Settings.settingsBuilder()
                                    .put(IndexMetaData.SETTING_NUMBER_OF_REPLICAS, 1)
                    )
                    .execute().actionGet();
            fail("can't change number of replicas on a closed index");
        } catch (IllegalArgumentException ex) {
            assertEquals(ex.getMessage(), "Can't update [index.number_of_replicas] on closed indices [[test]] - can leave index in an unopenable state");
            // expected
        }
        client().admin().indices().prepareUpdateSettings("test")
                .setSettings(Settings.settingsBuilder()
                        .put("index.refresh_interval", "1s") // this one can change
                        .put("index.cache.filter.type", "none") // this one can't
                )
                .execute().actionGet();

        indexMetaData = client().admin().cluster().prepareState().execute().actionGet().getState().metaData().index("test");
        assertThat(indexMetaData.settings().get("index.refresh_interval"), equalTo("1s"));
        assertThat(indexMetaData.settings().get("index.cache.filter.type"), equalTo("none"));

        // Now verify via dedicated get settings api:
        getSettingsResponse = client().admin().indices().prepareGetSettings("test").get();
        assertThat(getSettingsResponse.getSetting("test", "index.refresh_interval"), equalTo("1s"));
        assertThat(getSettingsResponse.getSetting("test", "index.cache.filter.type"), equalTo("none"));
    }

    @Test
    public void testEngineGCDeletesSetting() throws InterruptedException {
        createIndex("test");
        client().prepareIndex("test", "type", "1").setSource("f", 1).get(); // set version to 1
        client().prepareDelete("test", "type", "1").get(); // sets version to 2
        client().prepareIndex("test", "type", "1").setSource("f", 2).setVersion(2).get(); // delete is still in cache this should work & set version to 3
        client().admin().indices().prepareUpdateSettings("test")
                .setSettings(Settings.settingsBuilder()
                        .put("index.gc_deletes", 0)
                ).get();

        client().prepareDelete("test", "type", "1").get(); // sets version to 4
        Thread.sleep(300); // wait for cache time to change TODO: this needs to be solved better. To be discussed.
        assertThrows(client().prepareIndex("test", "type", "1").setSource("f", 3).setVersion(4), VersionConflictEngineException.class); // delete is should not be in cache

    }

    // #6626: make sure we can update throttle settings and the changes take effect
    @Test
    @Slow
    public void testUpdateThrottleSettings() {

        // No throttling at first, only 1 non-replicated shard, force lots of merging:
        assertAcked(prepareCreate("test")
                    .setSettings(Settings.builder()
                                 .put(IndexStore.INDEX_STORE_THROTTLE_TYPE, "none")
                                 .put(IndexMetaData.SETTING_NUMBER_OF_SHARDS, "1")
                                 .put(IndexMetaData.SETTING_NUMBER_OF_REPLICAS, "0")
                                 .put(TieredMergePolicyProvider.INDEX_MERGE_POLICY_MAX_MERGE_AT_ONCE, "2")
                                 .put(TieredMergePolicyProvider.INDEX_MERGE_POLICY_SEGMENTS_PER_TIER, "2")
                                 .put(ConcurrentMergeSchedulerProvider.MAX_THREAD_COUNT, "1")
                                 .put(ConcurrentMergeSchedulerProvider.MAX_MERGE_COUNT, "2")
                                 .put(Store.INDEX_STORE_STATS_REFRESH_INTERVAL, 0) // get stats all the time - no caching
                                 ));
        ensureGreen();
        long termUpto = 0;
        for(int i=0;i<100;i++) {
            // Provoke slowish merging by making many unique terms:
            StringBuilder sb = new StringBuilder();
            for(int j=0;j<100;j++) {
                sb.append(' ');
                sb.append(termUpto++);
            }
            client().prepareIndex("test", "type", ""+termUpto).setSource("field" + (i%10), sb.toString()).get();
            if (i % 2 == 0) {
                refresh();
            }
        }

        // No merge IO throttling should have happened:
        NodesStatsResponse nodesStats = client().admin().cluster().prepareNodesStats().setIndices(true).get();
        for(NodeStats stats : nodesStats.getNodes()) {
            assertThat(stats.getIndices().getStore().getThrottleTime().getMillis(), equalTo(0l));
        }

        logger.info("test: set low merge throttling");

        // Now updates settings to turn on merge throttling lowish rate
        client()
            .admin()
            .indices()
            .prepareUpdateSettings("test")
            .setSettings(Settings.builder()
                         .put(IndexStore.INDEX_STORE_THROTTLE_TYPE, "merge")
                         .put(IndexStore.INDEX_STORE_THROTTLE_MAX_BYTES_PER_SEC, "1mb"))
            .get();

        // Make sure setting says it is in fact changed:
        GetSettingsResponse getSettingsResponse = client().admin().indices().prepareGetSettings("test").get();
        assertThat(getSettingsResponse.getSetting("test", IndexStore.INDEX_STORE_THROTTLE_TYPE), equalTo("merge"));

        // Also make sure we see throttling kicking in:
        boolean done = false;
        while (done == false) {
            // Provoke slowish merging by making many unique terms:
            for(int i=0;i<5;i++) {
                StringBuilder sb = new StringBuilder();
                for(int j=0;j<100;j++) {
                    sb.append(' ');
                    sb.append(termUpto++);
                    sb.append(" some random text that keeps repeating over and over again hambone");
                }
                client().prepareIndex("test", "type", ""+termUpto).setSource("field" + (i%10), sb.toString()).get();
            }
            refresh();
            nodesStats = client().admin().cluster().prepareNodesStats().setIndices(true).get();
            for(NodeStats stats : nodesStats.getNodes()) {
                long throttleMillis = stats.getIndices().getStore().getThrottleTime().getMillis();
                if (throttleMillis > 0) {
                    done = true;
                    break;
                }
            }
        }

        logger.info("test: disable merge throttling");
        
        // Now updates settings to disable merge throttling
        client()
            .admin()
            .indices()
            .prepareUpdateSettings("test")
            .setSettings(Settings.builder()
                         .put(IndexStore.INDEX_STORE_THROTTLE_TYPE, "none"))
            .get();

        // Optimize does a waitForMerges, which we must do to make sure all in-flight (throttled) merges finish:
        logger.info("test: optimize");
        client().admin().indices().prepareOptimize("test").setMaxNumSegments(1).get();
        logger.info("test: optimize done");

        // Record current throttling so far
        long sumThrottleTime = 0;
        nodesStats = client().admin().cluster().prepareNodesStats().setIndices(true).get();
        for(NodeStats stats : nodesStats.getNodes()) {
            sumThrottleTime += stats.getIndices().getStore().getThrottleTime().getMillis();
        }

        // Make sure no further throttling happens:
        for(int i=0;i<100;i++) {
            // Provoke slowish merging by making many unique terms:
            StringBuilder sb = new StringBuilder();
            for(int j=0;j<100;j++) {
                sb.append(' ');
                sb.append(termUpto++);
            }
            client().prepareIndex("test", "type", ""+termUpto).setSource("field" + (i%10), sb.toString()).get();
            if (i % 2 == 0) {
                refresh();
            }
        }
        logger.info("test: done indexing after disabling throttling");

        long newSumThrottleTime = 0;
        nodesStats = client().admin().cluster().prepareNodesStats().setIndices(true).get();
        for(NodeStats stats : nodesStats.getNodes()) {
            newSumThrottleTime += stats.getIndices().getStore().getThrottleTime().getMillis();
        }

        // No additional merge IO throttling should have happened:
        assertEquals(sumThrottleTime, newSumThrottleTime);

        // Optimize & flush and wait; else we sometimes get a "Delete Index failed - not acked"
        // when ElasticsearchIntegrationTest.after tries to remove indices created by the test:

        // Wait for merges to finish
        client().admin().indices().prepareOptimize("test").get();
        flush();

        logger.info("test: test done");
    }

    private static class MockAppender extends AppenderSkeleton {
        public boolean sawIndexWriterMessage;
        public boolean sawFlushDeletes;
        public boolean sawMergeThreadPaused;
        public boolean sawUpdateMaxThreadCount;
        public boolean sawUpdateAutoThrottle;

        @Override
        protected void append(LoggingEvent event) {
            String message = event.getMessage().toString();
            if (event.getLevel() == Level.TRACE &&
                event.getLoggerName().endsWith("lucene.iw")) {
                sawFlushDeletes |= message.contains("IW: apply all deletes during flush");
                sawMergeThreadPaused |= message.contains("CMS: pause thread");
            }
            if (event.getLevel() == Level.INFO && message.contains("updating [index.merge.scheduler.max_thread_count] from [10000] to [1]")) {
                sawUpdateMaxThreadCount = true;
            }
            if (event.getLevel() == Level.INFO && message.contains("updating [index.merge.scheduler.auto_throttle] from [true] to [false]")) {
                sawUpdateAutoThrottle = true;
            }
        }

        @Override
        public boolean requiresLayout() {
            return false;
        }

        @Override
        public void close() {
        }
    }

    @Test
    public void testUpdateAutoThrottleSettings() {

        MockAppender mockAppender = new MockAppender();
        Logger rootLogger = Logger.getRootLogger();
        Level savedLevel = rootLogger.getLevel();
        rootLogger.addAppender(mockAppender);
        rootLogger.setLevel(Level.TRACE);

        try {
            // No throttling at first, only 1 non-replicated shard, force lots of merging:
            assertAcked(prepareCreate("test")
                        .setSettings(Settings.builder()
                                     .put(IndexMetaData.SETTING_NUMBER_OF_SHARDS, "1")
                                     .put(IndexMetaData.SETTING_NUMBER_OF_REPLICAS, "0")
                                     .put(TieredMergePolicyProvider.INDEX_MERGE_POLICY_MAX_MERGE_AT_ONCE, "2")
                                     .put(TieredMergePolicyProvider.INDEX_MERGE_POLICY_SEGMENTS_PER_TIER, "2")
                                     .put(ConcurrentMergeSchedulerProvider.MAX_THREAD_COUNT, "1")
                                     .put(ConcurrentMergeSchedulerProvider.MAX_MERGE_COUNT, "2")
                                     .put(ConcurrentMergeSchedulerProvider.AUTO_THROTTLE, "true")
                                     ));

            // Disable auto throttle:
            client()
                .admin()
                .indices()
                .prepareUpdateSettings("test")
                .setSettings(Settings.builder()
                             .put(ConcurrentMergeSchedulerProvider.AUTO_THROTTLE, "no"))
                .get();

            // Make sure we log the change:
            assertTrue(mockAppender.sawUpdateAutoThrottle);

            // Make sure setting says it is in fact changed:
            GetSettingsResponse getSettingsResponse = client().admin().indices().prepareGetSettings("test").get();
            assertThat(getSettingsResponse.getSetting("test", ConcurrentMergeSchedulerProvider.AUTO_THROTTLE), equalTo("no"));
        } finally {
            rootLogger.removeAppender(mockAppender);
            rootLogger.setLevel(savedLevel);
        }
    }

    // #6882: make sure we can change index.merge.scheduler.max_thread_count live
    @Test
    public void testUpdateMergeMaxThreadCount() {

        MockAppender mockAppender = new MockAppender();
        Logger rootLogger = Logger.getRootLogger();
        Level savedLevel = rootLogger.getLevel();
        rootLogger.addAppender(mockAppender);
        rootLogger.setLevel(Level.TRACE);

        try {

            assertAcked(prepareCreate("test")
                        .setSettings(Settings.builder()
                                     .put(IndexMetaData.SETTING_NUMBER_OF_SHARDS, "1")
                                     .put(IndexMetaData.SETTING_NUMBER_OF_REPLICAS, "0")
                                     .put(TieredMergePolicyProvider.INDEX_MERGE_POLICY_MAX_MERGE_AT_ONCE, "2")
                                     .put(TieredMergePolicyProvider.INDEX_MERGE_POLICY_SEGMENTS_PER_TIER, "2")
                                     .put(ConcurrentMergeSchedulerProvider.MAX_THREAD_COUNT, "10000")
                                     .put(ConcurrentMergeSchedulerProvider.MAX_MERGE_COUNT, "10000")
                                     ));

            assertFalse(mockAppender.sawUpdateMaxThreadCount);

            // Now make a live change to reduce allowed merge threads:
            client()
                .admin()
                .indices()
                .prepareUpdateSettings("test")
                .setSettings(Settings.builder()
                             .put(ConcurrentMergeSchedulerProvider.MAX_THREAD_COUNT, "1")
                             )
                .get();
            
            // Make sure we log the change:
            assertTrue(mockAppender.sawUpdateMaxThreadCount);

            // Make sure setting says it is in fact changed:
            GetSettingsResponse getSettingsResponse = client().admin().indices().prepareGetSettings("test").get();
            assertThat(getSettingsResponse.getSetting("test", ConcurrentMergeSchedulerProvider.MAX_THREAD_COUNT), equalTo("1"));

        } finally {
            rootLogger.removeAppender(mockAppender);
            rootLogger.setLevel(savedLevel);
        }
    }

    @Test
    public void testUpdateSettingsWithBlocks() {
        createIndex("test");
        ensureGreen("test");

        Settings.Builder builder = Settings.builder().put("index.refresh_interval", -1);

        for (String blockSetting : Arrays.asList(SETTING_BLOCKS_READ, SETTING_BLOCKS_WRITE)) {
            try {
                enableIndexBlock("test", blockSetting);
                assertAcked(client().admin().indices().prepareUpdateSettings("test").setSettings(builder));
            } finally {
                disableIndexBlock("test", blockSetting);
            }
        }

        // Closing an index is blocked
        for (String blockSetting : Arrays.asList(SETTING_READ_ONLY, SETTING_BLOCKS_METADATA)) {
            try {
                enableIndexBlock("test", blockSetting);
                assertBlocked(client().admin().indices().prepareUpdateSettings("test").setSettings(builder));
            } finally {
                disableIndexBlock("test", blockSetting);
            }
        }
    }
}


File: core/src/test/java/org/elasticsearch/indices/stats/IndexStatsTests.java
/*
 * Licensed to Elasticsearch under one or more contributor
 * license agreements. See the NOTICE file distributed with
 * this work for additional information regarding copyright
 * ownership. Elasticsearch licenses this file to you under
 * the Apache License, Version 2.0 (the "License"); you may
 * not use this file except in compliance with the License.
 * You may obtain a copy of the License at
 *
 *    http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing,
 * software distributed under the License is distributed on an
 * "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY
 * KIND, either express or implied.  See the License for the
 * specific language governing permissions and limitations
 * under the License.
 */

package org.elasticsearch.indices.stats;

import org.apache.lucene.util.LuceneTestCase.SuppressCodecs;
import org.apache.lucene.util.Version;
import org.elasticsearch.action.admin.cluster.node.stats.NodesStatsResponse;
import org.elasticsearch.action.admin.indices.stats.CommonStats;
import org.elasticsearch.action.admin.indices.stats.CommonStatsFlags;
import org.elasticsearch.action.admin.indices.stats.CommonStatsFlags.Flag;
import org.elasticsearch.action.admin.indices.stats.IndexStats;
import org.elasticsearch.action.admin.indices.stats.IndicesStatsRequestBuilder;
import org.elasticsearch.action.admin.indices.stats.IndicesStatsResponse;
import org.elasticsearch.action.admin.indices.stats.ShardStats;
import org.elasticsearch.action.get.GetResponse;
import org.elasticsearch.action.index.IndexRequestBuilder;
import org.elasticsearch.action.search.SearchResponse;
import org.elasticsearch.action.search.SearchType;
import org.elasticsearch.cluster.metadata.IndexMetaData;
import org.elasticsearch.common.bytes.BytesReference;
import org.elasticsearch.common.io.stream.StreamInput;
import org.elasticsearch.common.io.stream.BytesStreamOutput;
import org.elasticsearch.common.settings.Settings;
import org.elasticsearch.index.cache.filter.FilterCacheModule;
import org.elasticsearch.index.cache.filter.FilterCacheModule.FilterCacheSettings;
import org.elasticsearch.index.cache.filter.FilterCacheStats;
import org.elasticsearch.index.cache.filter.index.IndexFilterCache;
import org.elasticsearch.index.merge.policy.TieredMergePolicyProvider;
import org.elasticsearch.index.merge.scheduler.ConcurrentMergeSchedulerProvider;
import org.elasticsearch.index.query.QueryBuilders;
import org.elasticsearch.index.store.IndexStore;
import org.elasticsearch.indices.cache.query.IndicesQueryCache;
import org.elasticsearch.search.sort.SortOrder;
import org.elasticsearch.test.ElasticsearchIntegrationTest;
import org.elasticsearch.test.ElasticsearchIntegrationTest.ClusterScope;
import org.elasticsearch.test.ElasticsearchIntegrationTest.Scope;
import org.junit.Test;

import java.io.IOException;
import java.util.EnumSet;
import java.util.Random;

import static org.elasticsearch.cluster.metadata.IndexMetaData.SETTING_NUMBER_OF_REPLICAS;
import static org.elasticsearch.common.settings.Settings.settingsBuilder;
import static org.elasticsearch.common.xcontent.XContentFactory.jsonBuilder;
import static org.elasticsearch.test.hamcrest.ElasticsearchAssertions.assertAcked;
import static org.elasticsearch.test.hamcrest.ElasticsearchAssertions.assertAllSuccessful;
import static org.elasticsearch.test.hamcrest.ElasticsearchAssertions.assertSearchResponse;
import static org.hamcrest.Matchers.equalTo;
import static org.hamcrest.Matchers.greaterThan;
import static org.hamcrest.Matchers.is;
import static org.hamcrest.Matchers.lessThan;
import static org.hamcrest.Matchers.notNullValue;
import static org.hamcrest.Matchers.nullValue;

@ClusterScope(scope = Scope.SUITE, numDataNodes = 2, numClientNodes = 0, randomDynamicTemplates = false)
@SuppressCodecs("*") // requires custom completion format
public class IndexStatsTests extends ElasticsearchIntegrationTest {

    @Override
    protected Settings nodeSettings(int nodeOrdinal) {
        //Filter/Query cache is cleaned periodically, default is 60s, so make sure it runs often. Thread.sleep for 60s is bad
        return Settings.settingsBuilder().put(super.nodeSettings(nodeOrdinal))
                .put(IndicesQueryCache.INDICES_CACHE_QUERY_CLEAN_INTERVAL, "1ms")
                .put(FilterCacheSettings.FILTER_CACHE_EVERYTHING, true)
                .put(FilterCacheModule.FilterCacheSettings.FILTER_CACHE_TYPE, IndexFilterCache.class)
                .build();
    }

    @Test
    public void testFieldDataStats() {
        client().admin().indices().prepareCreate("test").setSettings(Settings.settingsBuilder().put("index.number_of_shards", 2)).execute().actionGet();
        ensureGreen();
        client().prepareIndex("test", "type", "1").setSource("field", "value1", "field2", "value1").execute().actionGet();
        client().prepareIndex("test", "type", "2").setSource("field", "value2", "field2", "value2").execute().actionGet();
        client().admin().indices().prepareRefresh().execute().actionGet();

        NodesStatsResponse nodesStats = client().admin().cluster().prepareNodesStats().setIndices(true).execute().actionGet();
        assertThat(nodesStats.getNodes()[0].getIndices().getFieldData().getMemorySizeInBytes() + nodesStats.getNodes()[1].getIndices().getFieldData().getMemorySizeInBytes(), equalTo(0l));
        IndicesStatsResponse indicesStats = client().admin().indices().prepareStats("test").clear().setFieldData(true).execute().actionGet();
        assertThat(indicesStats.getTotal().getFieldData().getMemorySizeInBytes(), equalTo(0l));

        // sort to load it to field data...
        client().prepareSearch().addSort("field", SortOrder.ASC).execute().actionGet();
        client().prepareSearch().addSort("field", SortOrder.ASC).execute().actionGet();

        nodesStats = client().admin().cluster().prepareNodesStats().setIndices(true).execute().actionGet();
        assertThat(nodesStats.getNodes()[0].getIndices().getFieldData().getMemorySizeInBytes() + nodesStats.getNodes()[1].getIndices().getFieldData().getMemorySizeInBytes(), greaterThan(0l));
        indicesStats = client().admin().indices().prepareStats("test").clear().setFieldData(true).execute().actionGet();
        assertThat(indicesStats.getTotal().getFieldData().getMemorySizeInBytes(), greaterThan(0l));

        // sort to load it to field data...
        client().prepareSearch().addSort("field2", SortOrder.ASC).execute().actionGet();
        client().prepareSearch().addSort("field2", SortOrder.ASC).execute().actionGet();

        // now check the per field stats
        nodesStats = client().admin().cluster().prepareNodesStats().setIndices(new CommonStatsFlags().set(CommonStatsFlags.Flag.FieldData, true).fieldDataFields("*")).execute().actionGet();
        assertThat(nodesStats.getNodes()[0].getIndices().getFieldData().getMemorySizeInBytes() + nodesStats.getNodes()[1].getIndices().getFieldData().getMemorySizeInBytes(), greaterThan(0l));
        assertThat(nodesStats.getNodes()[0].getIndices().getFieldData().getFields().get("field") + nodesStats.getNodes()[1].getIndices().getFieldData().getFields().get("field"), greaterThan(0l));
        assertThat(nodesStats.getNodes()[0].getIndices().getFieldData().getFields().get("field") + nodesStats.getNodes()[1].getIndices().getFieldData().getFields().get("field"), lessThan(nodesStats.getNodes()[0].getIndices().getFieldData().getMemorySizeInBytes() + nodesStats.getNodes()[1].getIndices().getFieldData().getMemorySizeInBytes()));

        indicesStats = client().admin().indices().prepareStats("test").clear().setFieldData(true).setFieldDataFields("*").execute().actionGet();
        assertThat(indicesStats.getTotal().getFieldData().getMemorySizeInBytes(), greaterThan(0l));
        assertThat(indicesStats.getTotal().getFieldData().getFields().get("field"), greaterThan(0l));
        assertThat(indicesStats.getTotal().getFieldData().getFields().get("field"), lessThan(indicesStats.getTotal().getFieldData().getMemorySizeInBytes()));

        client().admin().indices().prepareClearCache().setFieldDataCache(true).execute().actionGet();
        nodesStats = client().admin().cluster().prepareNodesStats().setIndices(true).execute().actionGet();
        assertThat(nodesStats.getNodes()[0].getIndices().getFieldData().getMemorySizeInBytes() + nodesStats.getNodes()[1].getIndices().getFieldData().getMemorySizeInBytes(), equalTo(0l));
        indicesStats = client().admin().indices().prepareStats("test").clear().setFieldData(true).execute().actionGet();
        assertThat(indicesStats.getTotal().getFieldData().getMemorySizeInBytes(), equalTo(0l));

    }

    @Test
    public void testClearAllCaches() throws Exception {
        client().admin().indices().prepareCreate("test")
                .setSettings(Settings.settingsBuilder().put("index.number_of_replicas", 0).put("index.number_of_shards", 2))
                .execute().actionGet();
        ensureGreen();
        client().admin().cluster().prepareHealth().setWaitForGreenStatus().execute().actionGet();
        client().prepareIndex("test", "type", "1").setSource("field", "value1").execute().actionGet();
        client().prepareIndex("test", "type", "2").setSource("field", "value2").execute().actionGet();
        client().admin().indices().prepareRefresh().execute().actionGet();

        NodesStatsResponse nodesStats = client().admin().cluster().prepareNodesStats().setIndices(true)
                .execute().actionGet();
        assertThat(nodesStats.getNodes()[0].getIndices().getFieldData().getMemorySizeInBytes() + nodesStats.getNodes()[1].getIndices().getFieldData().getMemorySizeInBytes(), equalTo(0l));
        assertThat(nodesStats.getNodes()[0].getIndices().getFilterCache().getMemorySizeInBytes() + nodesStats.getNodes()[1].getIndices().getFilterCache().getMemorySizeInBytes(), equalTo(0l));

        IndicesStatsResponse indicesStats = client().admin().indices().prepareStats("test")
                .clear().setFieldData(true).setFilterCache(true)
                .execute().actionGet();
        assertThat(indicesStats.getTotal().getFieldData().getMemorySizeInBytes(), equalTo(0l));
        assertThat(indicesStats.getTotal().getFilterCache().getMemorySizeInBytes(), equalTo(0l));

        // sort to load it to field data and filter to load filter cache
        client().prepareSearch()
                .setPostFilter(QueryBuilders.termQuery("field", "value1"))
                .addSort("field", SortOrder.ASC)
                .execute().actionGet();
        client().prepareSearch()
                .setPostFilter(QueryBuilders.termQuery("field", "value2"))
                .addSort("field", SortOrder.ASC)
                .execute().actionGet();

        nodesStats = client().admin().cluster().prepareNodesStats().setIndices(true)
                .execute().actionGet();
        assertThat(nodesStats.getNodes()[0].getIndices().getFieldData().getMemorySizeInBytes() + nodesStats.getNodes()[1].getIndices().getFieldData().getMemorySizeInBytes(), greaterThan(0l));
        assertThat(nodesStats.getNodes()[0].getIndices().getFilterCache().getMemorySizeInBytes() + nodesStats.getNodes()[1].getIndices().getFilterCache().getMemorySizeInBytes(), greaterThan(0l));

        indicesStats = client().admin().indices().prepareStats("test")
                .clear().setFieldData(true).setFilterCache(true)
                .execute().actionGet();
        assertThat(indicesStats.getTotal().getFieldData().getMemorySizeInBytes(), greaterThan(0l));
        assertThat(indicesStats.getTotal().getFilterCache().getMemorySizeInBytes(), greaterThan(0l));

        client().admin().indices().prepareClearCache().execute().actionGet();
        Thread.sleep(100); // Make sure the filter cache entries have been removed...
        nodesStats = client().admin().cluster().prepareNodesStats().setIndices(true)
                .execute().actionGet();
        assertThat(nodesStats.getNodes()[0].getIndices().getFieldData().getMemorySizeInBytes() + nodesStats.getNodes()[1].getIndices().getFieldData().getMemorySizeInBytes(), equalTo(0l));
        assertThat(nodesStats.getNodes()[0].getIndices().getFilterCache().getMemorySizeInBytes() + nodesStats.getNodes()[1].getIndices().getFilterCache().getMemorySizeInBytes(), equalTo(0l));

        indicesStats = client().admin().indices().prepareStats("test")
                .clear().setFieldData(true).setFilterCache(true)
                .execute().actionGet();
        assertThat(indicesStats.getTotal().getFieldData().getMemorySizeInBytes(), equalTo(0l));
        assertThat(indicesStats.getTotal().getFilterCache().getMemorySizeInBytes(), equalTo(0l));
    }

    @Test
    public void testQueryCache() throws Exception {
        assertAcked(client().admin().indices().prepareCreate("idx").setSettings(IndicesQueryCache.INDEX_CACHE_QUERY_ENABLED, true).get());
        ensureGreen();

        // index docs until we have at least one doc on each shard, otherwise, our tests will not work
        // since refresh will not refresh anything on a shard that has 0 docs and its search response get cached
        int pageDocs = randomIntBetween(2, 100);
        int numDocs = 0;
        int counter = 0;
        while (true) {
            IndexRequestBuilder[] builders = new IndexRequestBuilder[pageDocs];
            for (int i = 0; i < pageDocs; ++i) {
                builders[i] = client().prepareIndex("idx", "type", Integer.toString(counter++)).setSource(jsonBuilder()
                        .startObject()
                        .field("common", "field")
                        .field("str_value", "s" + i)
                        .endObject());
            }
            indexRandom(true, builders);
            numDocs += pageDocs;

            boolean allHaveDocs = true;
            for (ShardStats stats : client().admin().indices().prepareStats("idx").setDocs(true).get().getShards()) {
                if (stats.getStats().getDocs().getCount() == 0) {
                    allHaveDocs = false;
                    break;
                }
            }

            if (allHaveDocs) {
                break;
            }
        }

        assertThat(client().admin().indices().prepareStats("idx").setQueryCache(true).get().getTotal().getQueryCache().getMemorySizeInBytes(), equalTo(0l));
        assertThat(client().admin().indices().prepareStats("idx").setQueryCache(true).get().getTotal().getQueryCache().getHitCount(), equalTo(0l));
        assertThat(client().admin().indices().prepareStats("idx").setQueryCache(true).get().getTotal().getQueryCache().getMissCount(), equalTo(0l));
        for (int i = 0; i < 10; i++) {
            assertThat(client().prepareSearch("idx").setSearchType(SearchType.QUERY_THEN_FETCH).setSize(0).get().getHits().getTotalHits(), equalTo((long) numDocs));
            assertThat(client().admin().indices().prepareStats("idx").setQueryCache(true).get().getTotal().getQueryCache().getMemorySizeInBytes(), greaterThan(0l));
        }
        assertThat(client().admin().indices().prepareStats("idx").setQueryCache(true).get().getTotal().getQueryCache().getHitCount(), greaterThan(0l));
        assertThat(client().admin().indices().prepareStats("idx").setQueryCache(true).get().getTotal().getQueryCache().getMissCount(), greaterThan(0l));

        // index the data again...
        IndexRequestBuilder[] builders = new IndexRequestBuilder[numDocs];
        for (int i = 0; i < numDocs; ++i) {
            builders[i] = client().prepareIndex("idx", "type", Integer.toString(i)).setSource(jsonBuilder()
                    .startObject()
                    .field("common", "field")
                    .field("str_value", "s" + i)
                    .endObject());
        }
        indexRandom(true, builders);
        refresh();
        assertBusy(new Runnable() {
            @Override
            public void run() {
                assertThat(client().admin().indices().prepareStats("idx").setQueryCache(true).get().getTotal().getQueryCache().getMemorySizeInBytes(), equalTo(0l));
            }
        });

        for (int i = 0; i < 10; i++) {
            assertThat(client().prepareSearch("idx").setSearchType(SearchType.QUERY_THEN_FETCH).setSize(0).get().getHits().getTotalHits(), equalTo((long) numDocs));
            assertThat(client().admin().indices().prepareStats("idx").setQueryCache(true).get().getTotal().getQueryCache().getMemorySizeInBytes(), greaterThan(0l));
        }

        client().admin().indices().prepareClearCache().setQueryCache(true).get(); // clean the cache
        assertThat(client().admin().indices().prepareStats("idx").setQueryCache(true).get().getTotal().getQueryCache().getMemorySizeInBytes(), equalTo(0l));

        // test explicit request parameter

        assertThat(client().prepareSearch("idx").setSearchType(SearchType.QUERY_THEN_FETCH).setSize(0).setQueryCache(false).get().getHits().getTotalHits(), equalTo((long) numDocs));
        assertThat(client().admin().indices().prepareStats("idx").setQueryCache(true).get().getTotal().getQueryCache().getMemorySizeInBytes(), equalTo(0l));

        assertThat(client().prepareSearch("idx").setSearchType(SearchType.QUERY_THEN_FETCH).setSize(0).setQueryCache(true).get().getHits().getTotalHits(), equalTo((long) numDocs));
        assertThat(client().admin().indices().prepareStats("idx").setQueryCache(true).get().getTotal().getQueryCache().getMemorySizeInBytes(), greaterThan(0l));

        // set the index level setting to false, and see that the reverse works

        client().admin().indices().prepareClearCache().setQueryCache(true).get(); // clean the cache
        assertAcked(client().admin().indices().prepareUpdateSettings("idx").setSettings(Settings.builder().put(IndicesQueryCache.INDEX_CACHE_QUERY_ENABLED, false)));

        assertThat(client().prepareSearch("idx").setSearchType(SearchType.QUERY_THEN_FETCH).setSize(0).get().getHits().getTotalHits(), equalTo((long) numDocs));
        assertThat(client().admin().indices().prepareStats("idx").setQueryCache(true).get().getTotal().getQueryCache().getMemorySizeInBytes(), equalTo(0l));

        assertThat(client().prepareSearch("idx").setSearchType(SearchType.QUERY_THEN_FETCH).setSize(0).setQueryCache(true).get().getHits().getTotalHits(), equalTo((long) numDocs));
        assertThat(client().admin().indices().prepareStats("idx").setQueryCache(true).get().getTotal().getQueryCache().getMemorySizeInBytes(), greaterThan(0l));
    }


    @Test
    public void nonThrottleStats() throws Exception {
        assertAcked(prepareCreate("test")
                .setSettings(Settings.builder()
                                .put(IndexStore.INDEX_STORE_THROTTLE_TYPE, "merge")
                                .put(IndexMetaData.SETTING_NUMBER_OF_SHARDS, "1")
                                .put(IndexMetaData.SETTING_NUMBER_OF_REPLICAS, "0")
                                .put(TieredMergePolicyProvider.INDEX_MERGE_POLICY_MAX_MERGE_AT_ONCE, "2")
                                .put(TieredMergePolicyProvider.INDEX_MERGE_POLICY_SEGMENTS_PER_TIER, "2")
                                .put(ConcurrentMergeSchedulerProvider.MAX_THREAD_COUNT, "1")
                                .put(ConcurrentMergeSchedulerProvider.MAX_MERGE_COUNT, "10000")
                ));
        ensureGreen();
        long termUpto = 0;
        IndicesStatsResponse stats;
        // Provoke slowish merging by making many unique terms:
        for(int i=0; i<100; i++) {
            StringBuilder sb = new StringBuilder();
            for(int j=0; j<100; j++) {
                sb.append(' ');
                sb.append(termUpto++);
                sb.append(" some random text that keeps repeating over and over again hambone");
            }
            client().prepareIndex("test", "type", ""+termUpto).setSource("field" + (i%10), sb.toString()).get();
        }
        refresh();
        stats = client().admin().indices().prepareStats().execute().actionGet();
        //nodesStats = client().admin().cluster().prepareNodesStats().setIndices(true).get();

        stats = client().admin().indices().prepareStats().execute().actionGet();
        assertThat(stats.getPrimaries().getIndexing().getTotal().getThrottleTimeInMillis(), equalTo(0l));
    }

    @Test
    public void throttleStats() throws Exception {
        assertAcked(prepareCreate("test")
                    .setSettings(Settings.builder()
                                 .put(IndexStore.INDEX_STORE_THROTTLE_TYPE, "merge")
                                 .put(IndexMetaData.SETTING_NUMBER_OF_SHARDS, "1")
                                 .put(IndexMetaData.SETTING_NUMBER_OF_REPLICAS, "0")
                                 .put(TieredMergePolicyProvider.INDEX_MERGE_POLICY_MAX_MERGE_AT_ONCE, "2")
                                 .put(TieredMergePolicyProvider.INDEX_MERGE_POLICY_SEGMENTS_PER_TIER, "2")
                                 .put(ConcurrentMergeSchedulerProvider.MAX_THREAD_COUNT, "1")
                                 .put(ConcurrentMergeSchedulerProvider.MAX_MERGE_COUNT, "1")
                                 .put("index.merge.policy.type", "tiered")

                                 ));
        ensureGreen();
        long termUpto = 0;
        IndicesStatsResponse stats;
        // make sure we see throttling kicking in:
        boolean done = false;
        long start = System.currentTimeMillis();
        while (!done) {
            for(int i=0; i<100; i++) {
                // Provoke slowish merging by making many unique terms:
                StringBuilder sb = new StringBuilder();
                for(int j=0; j<100; j++) {
                    sb.append(' ');
                    sb.append(termUpto++);
                }
                client().prepareIndex("test", "type", ""+termUpto).setSource("field" + (i%10), sb.toString()).get();
                if (i % 2 == 0) {
                    refresh();
                }
            }
            refresh();
            stats = client().admin().indices().prepareStats().execute().actionGet();
            //nodesStats = client().admin().cluster().prepareNodesStats().setIndices(true).get();
            done = stats.getPrimaries().getIndexing().getTotal().getThrottleTimeInMillis() > 0;
            if (System.currentTimeMillis() - start > 300*1000) { //Wait 5 minutes for throttling to kick in
                fail("index throttling didn't kick in after 5 minutes of intense merging");
            }
        }

        // Optimize & flush and wait; else we sometimes get a "Delete Index failed - not acked"
        // when ElasticsearchIntegrationTest.after tries to remove indices created by the test:
        logger.info("test: now optimize");
        client().admin().indices().prepareOptimize("test").get();
        flush();
        logger.info("test: test done");
    }

    @Test
    public void simpleStats() throws Exception {
        createIndex("test1", "test2");
        ensureGreen();

        client().prepareIndex("test1", "type1", Integer.toString(1)).setSource("field", "value").execute().actionGet();
        client().prepareIndex("test1", "type2", Integer.toString(1)).setSource("field", "value").execute().actionGet();
        client().prepareIndex("test2", "type", Integer.toString(1)).setSource("field", "value").execute().actionGet();

        refresh();

        NumShards test1 = getNumShards("test1");
        long test1ExpectedWrites = 2 * test1.dataCopies;
        NumShards test2 = getNumShards("test2");
        long test2ExpectedWrites = test2.dataCopies;
        long totalExpectedWrites = test1ExpectedWrites + test2ExpectedWrites;

        IndicesStatsResponse stats = client().admin().indices().prepareStats().execute().actionGet();
        assertThat(stats.getPrimaries().getDocs().getCount(), equalTo(3l));
        assertThat(stats.getTotal().getDocs().getCount(), equalTo(totalExpectedWrites));
        assertThat(stats.getPrimaries().getIndexing().getTotal().getIndexCount(), equalTo(3l));
        assertThat(stats.getPrimaries().getIndexing().getTotal().isThrottled(), equalTo(false));
        assertThat(stats.getPrimaries().getIndexing().getTotal().getThrottleTimeInMillis(), equalTo(0l));
        assertThat(stats.getTotal().getIndexing().getTotal().getIndexCount(), equalTo(totalExpectedWrites));
        assertThat(stats.getTotal().getStore(), notNullValue());
        assertThat(stats.getTotal().getMerge(), notNullValue());
        assertThat(stats.getTotal().getFlush(), notNullValue());
        assertThat(stats.getTotal().getRefresh(), notNullValue());

        assertThat(stats.getIndex("test1").getPrimaries().getDocs().getCount(), equalTo(2l));
        assertThat(stats.getIndex("test1").getTotal().getDocs().getCount(), equalTo(test1ExpectedWrites));
        assertThat(stats.getIndex("test1").getPrimaries().getStore(), notNullValue());
        assertThat(stats.getIndex("test1").getPrimaries().getMerge(), notNullValue());
        assertThat(stats.getIndex("test1").getPrimaries().getFlush(), notNullValue());
        assertThat(stats.getIndex("test1").getPrimaries().getRefresh(), notNullValue());

        assertThat(stats.getIndex("test2").getPrimaries().getDocs().getCount(), equalTo(1l));
        assertThat(stats.getIndex("test2").getTotal().getDocs().getCount(), equalTo(test2ExpectedWrites));

        // make sure that number of requests in progress is 0
        assertThat(stats.getIndex("test1").getTotal().getIndexing().getTotal().getIndexCurrent(), equalTo(0l));
        assertThat(stats.getIndex("test1").getTotal().getIndexing().getTotal().getDeleteCurrent(), equalTo(0l));
        assertThat(stats.getIndex("test1").getTotal().getSearch().getTotal().getFetchCurrent(), equalTo(0l));
        assertThat(stats.getIndex("test1").getTotal().getSearch().getTotal().getQueryCurrent(), equalTo(0l));

        // check flags
        stats = client().admin().indices().prepareStats().clear()
                .setFlush(true)
                .setRefresh(true)
                .setMerge(true)
                .execute().actionGet();

        assertThat(stats.getTotal().getDocs(), nullValue());
        assertThat(stats.getTotal().getStore(), nullValue());
        assertThat(stats.getTotal().getIndexing(), nullValue());
        assertThat(stats.getTotal().getMerge(), notNullValue());
        assertThat(stats.getTotal().getFlush(), notNullValue());
        assertThat(stats.getTotal().getRefresh(), notNullValue());

        // check types
        stats = client().admin().indices().prepareStats().setTypes("type1", "type").execute().actionGet();
        assertThat(stats.getPrimaries().getIndexing().getTypeStats().get("type1").getIndexCount(), equalTo(1l));
        assertThat(stats.getPrimaries().getIndexing().getTypeStats().get("type").getIndexCount(), equalTo(1l));
        assertThat(stats.getPrimaries().getIndexing().getTypeStats().get("type2"), nullValue());
        assertThat(stats.getPrimaries().getIndexing().getTypeStats().get("type1").getIndexCurrent(), equalTo(0l));
        assertThat(stats.getPrimaries().getIndexing().getTypeStats().get("type1").getDeleteCurrent(), equalTo(0l));

        assertThat(stats.getTotal().getGet().getCount(), equalTo(0l));
        // check get
        GetResponse getResponse = client().prepareGet("test1", "type1", "1").execute().actionGet();
        assertThat(getResponse.isExists(), equalTo(true));

        stats = client().admin().indices().prepareStats().execute().actionGet();
        assertThat(stats.getTotal().getGet().getCount(), equalTo(1l));
        assertThat(stats.getTotal().getGet().getExistsCount(), equalTo(1l));
        assertThat(stats.getTotal().getGet().getMissingCount(), equalTo(0l));

        // missing get
        getResponse = client().prepareGet("test1", "type1", "2").execute().actionGet();
        assertThat(getResponse.isExists(), equalTo(false));

        stats = client().admin().indices().prepareStats().execute().actionGet();
        assertThat(stats.getTotal().getGet().getCount(), equalTo(2l));
        assertThat(stats.getTotal().getGet().getExistsCount(), equalTo(1l));
        assertThat(stats.getTotal().getGet().getMissingCount(), equalTo(1l));

        // clear all
        stats = client().admin().indices().prepareStats()
                .setDocs(false)
                .setStore(false)
                .setIndexing(false)
                .setFlush(true)
                .setRefresh(true)
                .setMerge(true)
                .clear() // reset defaults
                .execute().actionGet();

        assertThat(stats.getTotal().getDocs(), nullValue());
        assertThat(stats.getTotal().getStore(), nullValue());
        assertThat(stats.getTotal().getIndexing(), nullValue());
        assertThat(stats.getTotal().getGet(), nullValue());
        assertThat(stats.getTotal().getSearch(), nullValue());
    }

    @Test
    public void testMergeStats() {
        createIndex("test1");

        ensureGreen();

        // clear all
        IndicesStatsResponse stats = client().admin().indices().prepareStats()
                .setDocs(false)
                .setStore(false)
                .setIndexing(false)
                .setFlush(true)
                .setRefresh(true)
                .setMerge(true)
                .clear() // reset defaults
                .execute().actionGet();

        assertThat(stats.getTotal().getDocs(), nullValue());
        assertThat(stats.getTotal().getStore(), nullValue());
        assertThat(stats.getTotal().getIndexing(), nullValue());
        assertThat(stats.getTotal().getGet(), nullValue());
        assertThat(stats.getTotal().getSearch(), nullValue());

        for (int i = 0; i < 20; i++) {
            client().prepareIndex("test1", "type1", Integer.toString(i)).setSource("field", "value").execute().actionGet();
            client().prepareIndex("test1", "type2", Integer.toString(i)).setSource("field", "value").execute().actionGet();
            client().admin().indices().prepareFlush().execute().actionGet();
        }
        client().admin().indices().prepareOptimize().setMaxNumSegments(1).execute().actionGet();
        stats = client().admin().indices().prepareStats()
                .setMerge(true)
                .execute().actionGet();

        assertThat(stats.getTotal().getMerge(), notNullValue());
        assertThat(stats.getTotal().getMerge().getTotal(), greaterThan(0l));
    }

    @Test
    public void testSegmentsStats() {
        assertAcked(prepareCreate("test1", 2, settingsBuilder().put(SETTING_NUMBER_OF_REPLICAS, between(0, 1))));
        ensureGreen();

        NumShards test1 = getNumShards("test1");

        for (int i = 0; i < 100; i++) {
            index("test1", "type1", Integer.toString(i), "field", "value");
            index("test1", "type2", Integer.toString(i), "field", "value");
        }

        IndicesStatsResponse stats = client().admin().indices().prepareStats().setSegments(true).get();
        assertThat(stats.getTotal().getSegments().getIndexWriterMemoryInBytes(), greaterThan(0l));
        assertThat(stats.getTotal().getSegments().getIndexWriterMaxMemoryInBytes(), greaterThan(0l));
        assertThat(stats.getTotal().getSegments().getVersionMapMemoryInBytes(), greaterThan(0l));

        client().admin().indices().prepareFlush().get();
        client().admin().indices().prepareOptimize().setMaxNumSegments(1).execute().actionGet();
        stats = client().admin().indices().prepareStats().setSegments(true).get();

        assertThat(stats.getTotal().getSegments(), notNullValue());
        assertThat(stats.getTotal().getSegments().getCount(), equalTo((long) test1.totalNumShards));
        assumeTrue("test doesn't work with 4.6.0", org.elasticsearch.Version.CURRENT.luceneVersion != Version.LUCENE_4_6_0);
        assertThat(stats.getTotal().getSegments().getMemoryInBytes(), greaterThan(0l));
    }

    @Test
    public void testAllFlags() throws Exception {
        // rely on 1 replica for this tests
        createIndex("test1");
        createIndex("test2");

        ensureGreen();

        client().prepareIndex("test1", "type1", Integer.toString(1)).setSource("field", "value").execute().actionGet();
        client().prepareIndex("test1", "type2", Integer.toString(1)).setSource("field", "value").execute().actionGet();
        client().prepareIndex("test2", "type", Integer.toString(1)).setSource("field", "value").execute().actionGet();

        client().admin().indices().prepareRefresh().execute().actionGet();
        IndicesStatsRequestBuilder builder = client().admin().indices().prepareStats();
        Flag[] values = CommonStatsFlags.Flag.values();
        for (Flag flag : values) {
            set(flag, builder, false);
        }

        IndicesStatsResponse stats = builder.execute().actionGet();
        for (Flag flag : values) {
            assertThat(isSet(flag, stats.getPrimaries()), equalTo(false));
            assertThat(isSet(flag, stats.getTotal()), equalTo(false));
        }

        for (Flag flag : values) {
            set(flag, builder, true);
        }
        stats = builder.execute().actionGet();
        for (Flag flag : values) {
            assertThat(isSet(flag, stats.getPrimaries()), equalTo(true));
            assertThat(isSet(flag, stats.getTotal()), equalTo(true));
        }
        Random random = getRandom();
        EnumSet<Flag> flags = EnumSet.noneOf(Flag.class);
        for (Flag flag : values) {
            if (random.nextBoolean()) {
                flags.add(flag);
            }
        }


        for (Flag flag : values) {
            set(flag, builder, false); // clear all
        }

        for (Flag flag : flags) { // set the flags
            set(flag, builder, true);
        }
        stats = builder.execute().actionGet();
        for (Flag flag : flags) { // check the flags
            assertThat(isSet(flag, stats.getPrimaries()), equalTo(true));
            assertThat(isSet(flag, stats.getTotal()), equalTo(true));
        }

        for (Flag flag : EnumSet.complementOf(flags)) { // check the complement
            assertThat(isSet(flag, stats.getPrimaries()), equalTo(false));
            assertThat(isSet(flag, stats.getTotal()), equalTo(false));
        }

    }

    @Test
    public void testEncodeDecodeCommonStats() throws IOException {
        CommonStatsFlags flags = new CommonStatsFlags();
        Flag[] values = CommonStatsFlags.Flag.values();
        assertThat(flags.anySet(), equalTo(true));

        for (Flag flag : values) {
            flags.set(flag, false);
        }
        assertThat(flags.anySet(), equalTo(false));
        for (Flag flag : values) {
            flags.set(flag, true);
        }
        assertThat(flags.anySet(), equalTo(true));
        Random random = getRandom();
        flags.set(values[random.nextInt(values.length)], false);
        assertThat(flags.anySet(), equalTo(true));

        {
            BytesStreamOutput out = new BytesStreamOutput();
            flags.writeTo(out);
            out.close();
            BytesReference bytes = out.bytes();
            CommonStatsFlags readStats = CommonStatsFlags.readCommonStatsFlags(StreamInput.wrap(bytes));
            for (Flag flag : values) {
                assertThat(flags.isSet(flag), equalTo(readStats.isSet(flag)));
            }
        }

        {
            for (Flag flag : values) {
                flags.set(flag, random.nextBoolean());
            }
            BytesStreamOutput out = new BytesStreamOutput();
            flags.writeTo(out);
            out.close();
            BytesReference bytes = out.bytes();
            CommonStatsFlags readStats = CommonStatsFlags.readCommonStatsFlags(StreamInput.wrap(bytes));
            for (Flag flag : values) {
                assertThat(flags.isSet(flag), equalTo(readStats.isSet(flag)));
            }
        }
    }

    @Test
    public void testFlagOrdinalOrder() {
        Flag[] flags = new Flag[]{Flag.Store, Flag.Indexing, Flag.Get, Flag.Search, Flag.Merge, Flag.Flush, Flag.Refresh,
                Flag.FilterCache, Flag.FieldData, Flag.Docs, Flag.Warmer, Flag.Percolate, Flag.Completion, Flag.Segments,
                Flag.Translog, Flag.Suggest, Flag.QueryCache, Flag.Recovery};

        assertThat(flags.length, equalTo(Flag.values().length));
        for (int i = 0; i < flags.length; i++) {
            assertThat("ordinal has changed - this breaks the wire protocol. Only append to new values", i, equalTo(flags[i].ordinal()));
        }
    }

    @Test
    public void testMultiIndex() throws Exception {

        createIndex("test1");
        createIndex("test2");

        ensureGreen();

        client().prepareIndex("test1", "type1", Integer.toString(1)).setSource("field", "value").execute().actionGet();
        client().prepareIndex("test1", "type2", Integer.toString(1)).setSource("field", "value").execute().actionGet();
        client().prepareIndex("test2", "type", Integer.toString(1)).setSource("field", "value").execute().actionGet();
        refresh();

        int numShards1 = getNumShards("test1").totalNumShards;
        int numShards2 = getNumShards("test2").totalNumShards;

        IndicesStatsRequestBuilder builder = client().admin().indices().prepareStats();
        IndicesStatsResponse stats = builder.execute().actionGet();

        assertThat(stats.getTotalShards(), equalTo(numShards1 + numShards2));

        stats = builder.setIndices("_all").execute().actionGet();
        assertThat(stats.getTotalShards(), equalTo(numShards1 + numShards2));

        stats = builder.setIndices("_all").execute().actionGet();
        assertThat(stats.getTotalShards(), equalTo(numShards1 + numShards2));

        stats = builder.setIndices("*").execute().actionGet();
        assertThat(stats.getTotalShards(), equalTo(numShards1 + numShards2));

        stats = builder.setIndices("test1").execute().actionGet();
        assertThat(stats.getTotalShards(), equalTo(numShards1));

        stats = builder.setIndices("test1", "test2").execute().actionGet();
        assertThat(stats.getTotalShards(), equalTo(numShards1 + numShards2));

        stats = builder.setIndices("*2").execute().actionGet();
        assertThat(stats.getTotalShards(), equalTo(numShards2));

    }

    @Test
    public void testFieldDataFieldsParam() throws Exception {

        createIndex("test1");

        ensureGreen();

        client().prepareIndex("test1", "bar", Integer.toString(1)).setSource("{\"bar\":\"bar\",\"baz\":\"baz\"}").execute().actionGet();
        client().prepareIndex("test1", "baz", Integer.toString(1)).setSource("{\"bar\":\"bar\",\"baz\":\"baz\"}").execute().actionGet();
        refresh();

        client().prepareSearch("_all").addSort("bar", SortOrder.ASC).addSort("baz", SortOrder.ASC).execute().actionGet();

        IndicesStatsRequestBuilder builder = client().admin().indices().prepareStats();
        IndicesStatsResponse stats = builder.execute().actionGet();

        assertThat(stats.getTotal().fieldData.getMemorySizeInBytes(), greaterThan(0l));
        assertThat(stats.getTotal().fieldData.getFields(), is(nullValue()));

        stats = builder.setFieldDataFields("bar").execute().actionGet();
        assertThat(stats.getTotal().fieldData.getMemorySizeInBytes(), greaterThan(0l));
        assertThat(stats.getTotal().fieldData.getFields().containsKey("bar"), is(true));
        assertThat(stats.getTotal().fieldData.getFields().get("bar"), greaterThan(0l));
        assertThat(stats.getTotal().fieldData.getFields().containsKey("baz"), is(false));

        stats = builder.setFieldDataFields("bar", "baz").execute().actionGet();
        assertThat(stats.getTotal().fieldData.getMemorySizeInBytes(), greaterThan(0l));
        assertThat(stats.getTotal().fieldData.getFields().containsKey("bar"), is(true));
        assertThat(stats.getTotal().fieldData.getFields().get("bar"), greaterThan(0l));
        assertThat(stats.getTotal().fieldData.getFields().containsKey("baz"), is(true));
        assertThat(stats.getTotal().fieldData.getFields().get("baz"), greaterThan(0l));

        stats = builder.setFieldDataFields("*").execute().actionGet();
        assertThat(stats.getTotal().fieldData.getMemorySizeInBytes(), greaterThan(0l));
        assertThat(stats.getTotal().fieldData.getFields().containsKey("bar"), is(true));
        assertThat(stats.getTotal().fieldData.getFields().get("bar"), greaterThan(0l));
        assertThat(stats.getTotal().fieldData.getFields().containsKey("baz"), is(true));
        assertThat(stats.getTotal().fieldData.getFields().get("baz"), greaterThan(0l));

        stats = builder.setFieldDataFields("*r").execute().actionGet();
        assertThat(stats.getTotal().fieldData.getMemorySizeInBytes(), greaterThan(0l));
        assertThat(stats.getTotal().fieldData.getFields().containsKey("bar"), is(true));
        assertThat(stats.getTotal().fieldData.getFields().get("bar"), greaterThan(0l));
        assertThat(stats.getTotal().fieldData.getFields().containsKey("baz"), is(false));

    }

    @Test
    public void testCompletionFieldsParam() throws Exception {

        assertAcked(prepareCreate("test1")
                .addMapping(
                        "bar",
                        "{ \"properties\": { \"bar\": { \"type\": \"string\", \"fields\": { \"completion\": { \"type\": \"completion\" }}},\"baz\": { \"type\": \"string\", \"fields\": { \"completion\": { \"type\": \"completion\" }}}}}"));
        ensureGreen();

        client().prepareIndex("test1", "bar", Integer.toString(1)).setSource("{\"bar\":\"bar\",\"baz\":\"baz\"}").execute().actionGet();
        client().prepareIndex("test1", "baz", Integer.toString(1)).setSource("{\"bar\":\"bar\",\"baz\":\"baz\"}").execute().actionGet();
        refresh();

        IndicesStatsRequestBuilder builder = client().admin().indices().prepareStats();
        IndicesStatsResponse stats = builder.execute().actionGet();

        assertThat(stats.getTotal().completion.getSizeInBytes(), greaterThan(0l));
        assertThat(stats.getTotal().completion.getFields(), is(nullValue()));

        stats = builder.setCompletionFields("bar.completion").execute().actionGet();
        assertThat(stats.getTotal().completion.getSizeInBytes(), greaterThan(0l));
        assertThat(stats.getTotal().completion.getFields().containsKey("bar.completion"), is(true));
        assertThat(stats.getTotal().completion.getFields().get("bar.completion"), greaterThan(0l));
        assertThat(stats.getTotal().completion.getFields().containsKey("baz.completion"), is(false));

        stats = builder.setCompletionFields("bar.completion", "baz.completion").execute().actionGet();
        assertThat(stats.getTotal().completion.getSizeInBytes(), greaterThan(0l));
        assertThat(stats.getTotal().completion.getFields().containsKey("bar.completion"), is(true));
        assertThat(stats.getTotal().completion.getFields().get("bar.completion"), greaterThan(0l));
        assertThat(stats.getTotal().completion.getFields().containsKey("baz.completion"), is(true));
        assertThat(stats.getTotal().completion.getFields().get("baz.completion"), greaterThan(0l));

        stats = builder.setCompletionFields("*").execute().actionGet();
        assertThat(stats.getTotal().completion.getSizeInBytes(), greaterThan(0l));
        assertThat(stats.getTotal().completion.getFields().containsKey("bar.completion"), is(true));
        assertThat(stats.getTotal().completion.getFields().get("bar.completion"), greaterThan(0l));
        assertThat(stats.getTotal().completion.getFields().containsKey("baz.completion"), is(true));
        assertThat(stats.getTotal().completion.getFields().get("baz.completion"), greaterThan(0l));

        stats = builder.setCompletionFields("*r*").execute().actionGet();
        assertThat(stats.getTotal().completion.getSizeInBytes(), greaterThan(0l));
        assertThat(stats.getTotal().completion.getFields().containsKey("bar.completion"), is(true));
        assertThat(stats.getTotal().completion.getFields().get("bar.completion"), greaterThan(0l));
        assertThat(stats.getTotal().completion.getFields().containsKey("baz.completion"), is(false));

    }

    @Test
    public void testGroupsParam() throws Exception {

        createIndex("test1");

        ensureGreen();

        client().prepareIndex("test1", "bar", Integer.toString(1)).setSource("foo", "bar").execute().actionGet();
        refresh();

        client().prepareSearch("_all").setStats("bar", "baz").execute().actionGet();

        IndicesStatsRequestBuilder builder = client().admin().indices().prepareStats();
        IndicesStatsResponse stats = builder.execute().actionGet();

        assertThat(stats.getTotal().search.getTotal().getQueryCount(), greaterThan(0l));
        assertThat(stats.getTotal().search.getGroupStats(), is(nullValue()));

        stats = builder.setGroups("bar").execute().actionGet();
        assertThat(stats.getTotal().search.getGroupStats().get("bar").getQueryCount(), greaterThan(0l));
        assertThat(stats.getTotal().search.getGroupStats().containsKey("baz"), is(false));

        stats = builder.setGroups("bar", "baz").execute().actionGet();
        assertThat(stats.getTotal().search.getGroupStats().get("bar").getQueryCount(), greaterThan(0l));
        assertThat(stats.getTotal().search.getGroupStats().get("baz").getQueryCount(), greaterThan(0l));

        stats = builder.setGroups("*").execute().actionGet();
        assertThat(stats.getTotal().search.getGroupStats().get("bar").getQueryCount(), greaterThan(0l));
        assertThat(stats.getTotal().search.getGroupStats().get("baz").getQueryCount(), greaterThan(0l));

        stats = builder.setGroups("*r").execute().actionGet();
        assertThat(stats.getTotal().search.getGroupStats().get("bar").getQueryCount(), greaterThan(0l));
        assertThat(stats.getTotal().search.getGroupStats().containsKey("baz"), is(false));

    }

    @Test
    public void testTypesParam() throws Exception {

        createIndex("test1");
        createIndex("test2");

        ensureGreen();

        client().prepareIndex("test1", "bar", Integer.toString(1)).setSource("foo", "bar").execute().actionGet();
        client().prepareIndex("test2", "baz", Integer.toString(1)).setSource("foo", "bar").execute().actionGet();
        refresh();

        IndicesStatsRequestBuilder builder = client().admin().indices().prepareStats();
        IndicesStatsResponse stats = builder.execute().actionGet();

        assertThat(stats.getTotal().indexing.getTotal().getIndexCount(), greaterThan(0l));
        assertThat(stats.getTotal().indexing.getTypeStats(), is(nullValue()));

        stats = builder.setTypes("bar").execute().actionGet();
        assertThat(stats.getTotal().indexing.getTypeStats().get("bar").getIndexCount(), greaterThan(0l));
        assertThat(stats.getTotal().indexing.getTypeStats().containsKey("baz"), is(false));

        stats = builder.setTypes("bar", "baz").execute().actionGet();
        assertThat(stats.getTotal().indexing.getTypeStats().get("bar").getIndexCount(), greaterThan(0l));
        assertThat(stats.getTotal().indexing.getTypeStats().get("baz").getIndexCount(), greaterThan(0l));

        stats = builder.setTypes("*").execute().actionGet();
        assertThat(stats.getTotal().indexing.getTypeStats().get("bar").getIndexCount(), greaterThan(0l));
        assertThat(stats.getTotal().indexing.getTypeStats().get("baz").getIndexCount(), greaterThan(0l));

        stats = builder.setTypes("*r").execute().actionGet();
        assertThat(stats.getTotal().indexing.getTypeStats().get("bar").getIndexCount(), greaterThan(0l));
        assertThat(stats.getTotal().indexing.getTypeStats().containsKey("baz"), is(false));

    }

    private static void set(Flag flag, IndicesStatsRequestBuilder builder, boolean set) {
        switch (flag) {
            case Docs:
                builder.setDocs(set);
                break;
            case FieldData:
                builder.setFieldData(set);
                break;
            case FilterCache:
                builder.setFilterCache(set);
                break;
            case Flush:
                builder.setFlush(set);
                break;
            case Get:
                builder.setGet(set);
                break;
            case Indexing:
                builder.setIndexing(set);
                break;
            case Merge:
                builder.setMerge(set);
                break;
            case Refresh:
                builder.setRefresh(set);
                break;
            case Search:
                builder.setSearch(set);
                break;
            case Store:
                builder.setStore(set);
                break;
            case Warmer:
                builder.setWarmer(set);
                break;
            case Percolate:
                builder.setPercolate(set);
                break;
            case Completion:
                builder.setCompletion(set);
                break;
            case Segments:
                builder.setSegments(set);
                break;
            case Translog:
                builder.setTranslog(set);
                break;
            case Suggest:
                builder.setSuggest(set);
                break;
            case QueryCache:
                builder.setQueryCache(set);
                break;
            case Recovery:
                builder.setRecovery(set);
                break;
            default:
                fail("new flag? " + flag);
                break;
        }
    }

    private static boolean isSet(Flag flag, CommonStats response) {
        switch (flag) {
            case Docs:
                return response.getDocs() != null;
            case FieldData:
                return response.getFieldData() != null;
            case FilterCache:
                return response.getFilterCache() != null;
            case Flush:
                return response.getFlush() != null;
            case Get:
                return response.getGet() != null;
            case Indexing:
                return response.getIndexing() != null;
            case Merge:
                return response.getMerge() != null;
            case Refresh:
                return response.getRefresh() != null;
            case Search:
                return response.getSearch() != null;
            case Store:
                return response.getStore() != null;
            case Warmer:
                return response.getWarmer() != null;
            case Percolate:
                return response.getPercolate() != null;
            case Completion:
                return response.getCompletion() != null;
            case Segments:
                return response.getSegments() != null;
            case Translog:
                return response.getTranslog() != null;
            case Suggest:
                return response.getSuggest() != null;
            case QueryCache:
                return response.getQueryCache() != null;
            case Recovery:
                return response.getRecoveryStats() != null;
            default:
                fail("new flag? " + flag);
                return false;
        }
    }

    private void assertEquals(FilterCacheStats stats1, FilterCacheStats stats2) {
        assertEquals(stats1.getCacheCount(), stats2.getCacheCount());
        assertEquals(stats1.getCacheSize(), stats2.getCacheSize());
        assertEquals(stats1.getEvictions(), stats2.getEvictions());
        assertEquals(stats1.getHitCount(), stats2.getHitCount());
        assertEquals(stats2.getMemorySizeInBytes(), stats2.getMemorySizeInBytes());
        assertEquals(stats1.getMissCount(), stats2.getMissCount());
        assertEquals(stats1.getTotalCount(), stats2.getTotalCount());
    }

    private void assertCumulativeFilterCacheStats(IndicesStatsResponse response) {
        assertAllSuccessful(response);
        FilterCacheStats total = response.getTotal().filterCache;
        FilterCacheStats indexTotal = new FilterCacheStats();
        FilterCacheStats shardTotal = new FilterCacheStats();
        for (IndexStats indexStats : response.getIndices().values()) {
            indexTotal.add(indexStats.getTotal().filterCache);
            for (ShardStats shardStats : response.getShards()) {
                shardTotal.add(shardStats.getStats().filterCache);
            }
        }
        assertEquals(total, indexTotal);
        assertEquals(total, shardTotal);
    }

    public void testFilterCacheStats() throws Exception {
        assertAcked(prepareCreate("index").setSettings("number_of_replicas", 0).get());
        indexRandom(true,
                client().prepareIndex("index", "type", "1").setSource("foo", "bar"),
                client().prepareIndex("index", "type", "2").setSource("foo", "baz"));
        ensureGreen();

        IndicesStatsResponse response = client().admin().indices().prepareStats("index").setFilterCache(true).get();
        assertCumulativeFilterCacheStats(response);
        assertEquals(0, response.getTotal().filterCache.getCacheSize());

        SearchResponse r;
        assertSearchResponse(r = client().prepareSearch("index").setQuery(QueryBuilders.constantScoreQuery(QueryBuilders.matchQuery("foo", "baz"))).get());
        response = client().admin().indices().prepareStats("index").setFilterCache(true).get();
        assertCumulativeFilterCacheStats(response);
        assertThat(response.getTotal().filterCache.getHitCount(), equalTo(0L));
        assertThat(response.getTotal().filterCache.getEvictions(), equalTo(0L));
        assertThat(response.getTotal().filterCache.getMissCount(), greaterThan(0L));
        assertThat(response.getTotal().filterCache.getCacheSize(), greaterThan(0L));

        assertSearchResponse(client().prepareSearch("index").setQuery(QueryBuilders.constantScoreQuery(QueryBuilders.matchQuery("foo", "baz"))).get());
        response = client().admin().indices().prepareStats("index").setFilterCache(true).get();
        assertCumulativeFilterCacheStats(response);
        assertThat(response.getTotal().filterCache.getHitCount(), greaterThan(0L));
        assertThat(response.getTotal().filterCache.getEvictions(), equalTo(0L));
        assertThat(response.getTotal().filterCache.getMissCount(), greaterThan(0L));
        assertThat(response.getTotal().filterCache.getCacheSize(), greaterThan(0L));

        assertTrue(client().prepareDelete("index", "type", "1").get().isFound());
        assertTrue(client().prepareDelete("index", "type", "2").get().isFound());
        refresh();
        response = client().admin().indices().prepareStats("index").setFilterCache(true).get();
        assertCumulativeFilterCacheStats(response);
        assertThat(response.getTotal().filterCache.getHitCount(), greaterThan(0L));
        assertThat(response.getTotal().filterCache.getEvictions(), greaterThan(0L));
        assertThat(response.getTotal().filterCache.getCacheSize(), equalTo(0L));
        assertThat(response.getTotal().filterCache.getCacheCount(), greaterThan(0L));

        indexRandom(true,
                client().prepareIndex("index", "type", "1").setSource("foo", "bar"),
                client().prepareIndex("index", "type", "2").setSource("foo", "baz"));
        assertSearchResponse(client().prepareSearch("index").setQuery(QueryBuilders.constantScoreQuery(QueryBuilders.matchQuery("foo", "baz"))).get());

        response = client().admin().indices().prepareStats("index").setFilterCache(true).get();
        assertCumulativeFilterCacheStats(response);
        assertThat(response.getTotal().filterCache.getHitCount(), greaterThan(0L));
        assertThat(response.getTotal().filterCache.getEvictions(), greaterThan(0L));
        assertThat(response.getTotal().filterCache.getMissCount(), greaterThan(0L));
        assertThat(response.getTotal().filterCache.getCacheSize(), greaterThan(0L));
        assertThat(response.getTotal().filterCache.getMemorySizeInBytes(), greaterThan(0L));

        assertAllSuccessful(client().admin().indices().prepareClearCache("index").setFilterCache(true).get());
        response = client().admin().indices().prepareStats("index").setFilterCache(true).get();
        assertCumulativeFilterCacheStats(response);
        assertThat(response.getTotal().filterCache.getHitCount(), greaterThan(0L));
        assertThat(response.getTotal().filterCache.getEvictions(), greaterThan(0L));
        assertThat(response.getTotal().filterCache.getMissCount(), greaterThan(0L));
        assertThat(response.getTotal().filterCache.getCacheSize(), equalTo(0L));
        assertThat(response.getTotal().filterCache.getMemorySizeInBytes(), equalTo(0L));
    }

}


File: core/src/test/java/org/elasticsearch/search/child/ParentFieldLoadingBwcTest.java
/*
 * Licensed to Elasticsearch under one or more contributor
 * license agreements. See the NOTICE file distributed with
 * this work for additional information regarding copyright
 * ownership. Elasticsearch licenses this file to you under
 * the Apache License, Version 2.0 (the "License"); you may
 * not use this file except in compliance with the License.
 * You may obtain a copy of the License at
 *
 *    http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing,
 * software distributed under the License is distributed on an
 * "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY
 * KIND, either express or implied.  See the License for the
 * specific language governing permissions and limitations
 * under the License.
 */

package org.elasticsearch.search.child;

import org.apache.lucene.util.LuceneTestCase;
import org.elasticsearch.Version;
import org.elasticsearch.action.admin.cluster.stats.ClusterStatsResponse;
import org.elasticsearch.action.admin.indices.cache.clear.ClearIndicesCacheResponse;
import org.elasticsearch.action.admin.indices.mapping.put.PutMappingResponse;
import org.elasticsearch.action.admin.indices.stats.IndicesStatsResponse;
import org.elasticsearch.action.search.SearchResponse;
import org.elasticsearch.cluster.ClusterState;
import org.elasticsearch.cluster.metadata.IndexMetaData;
import org.elasticsearch.cluster.routing.ShardRouting;
import org.elasticsearch.common.settings.Settings;
import org.elasticsearch.common.xcontent.XContentBuilder;
import org.elasticsearch.common.xcontent.XContentFactory;
import org.elasticsearch.index.IndexService;
import org.elasticsearch.index.fielddata.FieldDataType;
import org.elasticsearch.index.mapper.DocumentMapper;
import org.elasticsearch.index.mapper.FieldMapper;
import org.elasticsearch.index.mapper.MappedFieldType;
import org.elasticsearch.index.mapper.MapperService;
import org.elasticsearch.index.merge.policy.MergePolicyModule;
import org.elasticsearch.index.shard.IndexShard;
import org.elasticsearch.indices.IndicesService;
import org.elasticsearch.test.ElasticsearchIntegrationTest;
import org.elasticsearch.test.index.merge.NoMergePolicyProvider;
import org.junit.Test;

import java.io.IOException;

import static org.elasticsearch.common.xcontent.XContentFactory.jsonBuilder;
import static org.elasticsearch.index.query.QueryBuilders.constantScoreQuery;
import static org.elasticsearch.index.query.QueryBuilders.termQuery;
import static org.elasticsearch.search.child.ChildQuerySearchTests.hasChildQuery;
import static org.elasticsearch.test.hamcrest.ElasticsearchAssertions.assertAcked;
import static org.elasticsearch.test.hamcrest.ElasticsearchAssertions.assertAllSuccessful;
import static org.elasticsearch.test.hamcrest.ElasticsearchAssertions.assertNoFailures;
import static org.hamcrest.Matchers.equalTo;
import static org.hamcrest.Matchers.greaterThan;

/**
 */
public class ParentFieldLoadingBwcTest extends ElasticsearchIntegrationTest {

    private final Settings indexSettings = Settings.builder()
            .put(IndexMetaData.SETTING_NUMBER_OF_SHARDS, 1)
            .put(IndexMetaData.SETTING_NUMBER_OF_REPLICAS, 0)
            .put(IndexShard.INDEX_REFRESH_INTERVAL, -1)
                    // We never want merges in this test to ensure we have two segments for the last validation
            .put(MergePolicyModule.MERGE_POLICY_TYPE_KEY, NoMergePolicyProvider.class)
            .put(IndexMetaData.SETTING_VERSION_CREATED, Version.V_1_6_0)
            .build();

    @Test
    @LuceneTestCase.AwaitsFix(bugUrl = "https://github.com/elasticsearch/elasticsearch/issues/9270")
    public void testParentFieldDataCacheBug() throws Exception {
        assertAcked(prepareCreate("test")
                .setSettings(Settings.builder().put(indexSettings())
                    .put("index.refresh_interval", -1)) // Disable automatic refresh, so that the _parent doesn't get warmed
                .addMapping("parent", XContentFactory.jsonBuilder().startObject().startObject("parent")
                    .startObject("properties")
                    .startObject("p_field")
                    .field("type", "string")
                    .startObject("fielddata")
                    .field(FieldDataType.FORMAT_KEY, MappedFieldType.Loading.LAZY)
                    .endObject()
                    .endObject()
                    .endObject().endObject().endObject()));

        ensureGreen();

        client().prepareIndex("test", "parent", "p0").setSource("p_field", "p_value0").get();
        client().prepareIndex("test", "parent", "p1").setSource("p_field", "p_value1").get();

        refresh();
        // No _parent field yet, there shouldn't be anything in the field data for _parent field
        IndicesStatsResponse indicesStatsResponse = client().admin().indices()
                .prepareStats("test").setFieldData(true).get();
        assertThat(indicesStatsResponse.getTotal().getFieldData().getMemorySizeInBytes(), equalTo(0l));

        // Now add mapping + children
        client().admin().indices().preparePutMapping("test").setType("child")
                .setSource(XContentFactory.jsonBuilder().startObject().startObject("child")
                        .startObject("_parent")
                        .field("type", "parent")
                        .endObject()
                        .startObject("properties")
                        .startObject("c_field")
                        .field("type", "string")
                        .startObject("fielddata")
                        .field(FieldDataType.FORMAT_KEY, MappedFieldType.Loading.LAZY)
                        .endObject()
                        .endObject()
                        .endObject().endObject().endObject())
                .get();

        // index simple data
        client().prepareIndex("test", "child", "c1").setSource("c_field", "red").setParent("p1").get();
        client().prepareIndex("test", "child", "c2").setSource("c_field", "yellow").setParent("p1").get();
        client().prepareIndex("test", "parent", "p2").setSource("p_field", "p_value2").get();
        client().prepareIndex("test", "child", "c3").setSource("c_field", "blue").setParent("p2").get();
        client().prepareIndex("test", "child", "c4").setSource("c_field", "red").setParent("p2").get();

        refresh();

        indicesStatsResponse = client().admin().indices()
                .prepareStats("test").setFieldData(true).setFieldDataFields("_parent").get();
        assertThat(indicesStatsResponse.getTotal().getFieldData().getMemorySizeInBytes(), greaterThan(0l));
        assertThat(indicesStatsResponse.getTotal().getFieldData().getFields().get("_parent"), greaterThan(0l));

        SearchResponse searchResponse = client().prepareSearch("test")
                .setQuery(constantScoreQuery(hasChildQuery("child", termQuery("c_field", "blue"))))
                .get();
        assertNoFailures(searchResponse);
        assertThat(searchResponse.getHits().totalHits(), equalTo(1l));

        indicesStatsResponse = client().admin().indices()
                .prepareStats("test").setFieldData(true).setFieldDataFields("_parent").get();
        assertThat(indicesStatsResponse.getTotal().getFieldData().getMemorySizeInBytes(), greaterThan(0l));
        assertThat(indicesStatsResponse.getTotal().getFieldData().getFields().get("_parent"), greaterThan(0l));

        ClearIndicesCacheResponse clearCacheResponse = client().admin().indices().prepareClearCache("test").setFieldDataCache(true).get();
        assertNoFailures(clearCacheResponse);
        assertAllSuccessful(clearCacheResponse);
        indicesStatsResponse = client().admin().indices()
                .prepareStats("test").setFieldData(true).setFieldDataFields("_parent").get();
        assertThat(indicesStatsResponse.getTotal().getFieldData().getMemorySizeInBytes(), equalTo(0l));
        assertThat(indicesStatsResponse.getTotal().getFieldData().getFields().get("_parent"), equalTo(0l));
    }

    @Test
    public void testEagerParentFieldLoading() throws Exception {
        logger.info("testing lazy loading...");
        assertAcked(prepareCreate("test")
                .setSettings(indexSettings)
                .addMapping("parent")
                .addMapping("child", childMapping(MappedFieldType.Loading.LAZY)));
        ensureGreen();

        client().prepareIndex("test", "parent", "1").setSource("{}").get();
        client().prepareIndex("test", "child", "1").setParent("1").setSource("{}").get();
        refresh();

        ClusterStatsResponse response = client().admin().cluster().prepareClusterStats().get();
        assertThat(response.getIndicesStats().getFieldData().getMemorySizeInBytes(), equalTo(0l));

        logger.info("testing default loading...");
        assertAcked(client().admin().indices().prepareDelete("test").get());
        assertAcked(prepareCreate("test")
                .setSettings(indexSettings)
                .addMapping("parent")
                .addMapping("child", "_parent", "type=parent"));
        ensureGreen();

        client().prepareIndex("test", "parent", "1").setSource("{}").get();
        client().prepareIndex("test", "child", "1").setParent("1").setSource("{}").get();
        refresh();

        response = client().admin().cluster().prepareClusterStats().get();
        long fielddataSizeDefault = response.getIndicesStats().getFieldData().getMemorySizeInBytes();
        assertThat(fielddataSizeDefault, greaterThan(0l));

        logger.info("testing eager loading...");
        assertAcked(client().admin().indices().prepareDelete("test").get());
        assertAcked(prepareCreate("test")
                .setSettings(indexSettings)
                .addMapping("parent")
                .addMapping("child", childMapping(MappedFieldType.Loading.EAGER)));
        ensureGreen();

        client().prepareIndex("test", "parent", "1").setSource("{}").get();
        client().prepareIndex("test", "child", "1").setParent("1").setSource("{}").get();
        refresh();

        response = client().admin().cluster().prepareClusterStats().get();
        assertThat(response.getIndicesStats().getFieldData().getMemorySizeInBytes(), equalTo(fielddataSizeDefault));

        logger.info("testing eager global ordinals loading...");
        assertAcked(client().admin().indices().prepareDelete("test").get());
        assertAcked(prepareCreate("test")
                .setSettings(indexSettings)
                .addMapping("parent")
                .addMapping("child", childMapping(MappedFieldType.Loading.EAGER_GLOBAL_ORDINALS)));
        ensureGreen();

        // Need to do 2 separate refreshes, otherwise we have 1 segment and then we can't measure if global ordinals
        // is loaded by the size of the field data cache, because global ordinals on 1 segment shards takes no extra memory.
        client().prepareIndex("test", "parent", "1").setSource("{}").get();
        refresh();
        client().prepareIndex("test", "child", "1").setParent("1").setSource("{}").get();
        refresh();

        response = client().admin().cluster().prepareClusterStats().get();
        assertThat(response.getIndicesStats().getFieldData().getMemorySizeInBytes(), greaterThan(fielddataSizeDefault));
    }

    @Test
    public void testChangingEagerParentFieldLoadingAtRuntime() throws Exception {
        assertAcked(prepareCreate("test")
                .setSettings(indexSettings)
                .addMapping("parent")
                .addMapping("child", "_parent", "type=parent"));
        ensureGreen();

        client().prepareIndex("test", "parent", "1").setSource("{}").get();
        client().prepareIndex("test", "child", "1").setParent("1").setSource("{}").get();
        refresh();

        ClusterStatsResponse response = client().admin().cluster().prepareClusterStats().get();
        long fielddataSizeDefault = response.getIndicesStats().getFieldData().getMemorySizeInBytes();
        assertThat(fielddataSizeDefault, greaterThan(0l));

        PutMappingResponse putMappingResponse = client().admin().indices().preparePutMapping("test").setType("child")
                .setSource(childMapping(MappedFieldType.Loading.EAGER_GLOBAL_ORDINALS))
                .get();
        assertAcked(putMappingResponse);
        assertBusy(new Runnable() {
            @Override
            public void run() {
                ClusterState clusterState = internalCluster().clusterService().state();
                ShardRouting shardRouting = clusterState.routingTable().index("test").shard(0).getShards().get(0);
                String nodeName = clusterState.getNodes().get(shardRouting.currentNodeId()).getName();

                boolean verified = false;
                IndicesService indicesService = internalCluster().getInstance(IndicesService.class, nodeName);
                IndexService indexService = indicesService.indexService("test");
                if (indexService != null) {
                    MapperService mapperService = indexService.mapperService();
                    DocumentMapper documentMapper = mapperService.documentMapper("child");
                    if (documentMapper != null) {
                        verified = documentMapper.parentFieldMapper().fieldType().fieldDataType().getLoading() == MappedFieldType.Loading.EAGER_GLOBAL_ORDINALS;
                    }
                }
                assertTrue(verified);
            }
        });

        // Need to add a new doc otherwise the refresh doesn't trigger a new searcher
        // Because it ends up in its own segment, but isn't of type parent or child, this doc doesn't contribute to the size of the fielddata cache
        client().prepareIndex("test", "dummy", "dummy").setSource("{}").get();
        refresh();
        response = client().admin().cluster().prepareClusterStats().get();
        assertThat(response.getIndicesStats().getFieldData().getMemorySizeInBytes(), greaterThan(fielddataSizeDefault));
    }

    private XContentBuilder childMapping(MappedFieldType.Loading loading) throws IOException {
        return jsonBuilder().startObject().startObject("child").startObject("_parent")
                .field("type", "parent")
                .startObject("fielddata").field(MappedFieldType.Loading.KEY, loading).endObject()
                .endObject().endObject().endObject();
    }

}


File: core/src/test/java/org/elasticsearch/search/child/ParentFieldLoadingTest.java
/*
 * Licensed to Elasticsearch under one or more contributor
 * license agreements. See the NOTICE file distributed with
 * this work for additional information regarding copyright
 * ownership. Elasticsearch licenses this file to you under
 * the Apache License, Version 2.0 (the "License"); you may
 * not use this file except in compliance with the License.
 * You may obtain a copy of the License at
 *
 *    http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing,
 * software distributed under the License is distributed on an
 * "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY
 * KIND, either express or implied.  See the License for the
 * specific language governing permissions and limitations
 * under the License.
 */

package org.elasticsearch.search.child;

import org.elasticsearch.action.admin.cluster.stats.ClusterStatsResponse;
import org.elasticsearch.action.admin.indices.mapping.put.PutMappingResponse;
import org.elasticsearch.cluster.ClusterState;
import org.elasticsearch.cluster.metadata.IndexMetaData;
import org.elasticsearch.cluster.routing.ShardRouting;
import org.elasticsearch.common.settings.Settings;
import org.elasticsearch.common.xcontent.XContentBuilder;
import org.elasticsearch.index.IndexService;
import org.elasticsearch.index.mapper.DocumentMapper;
import org.elasticsearch.index.mapper.MappedFieldType;
import org.elasticsearch.index.mapper.MapperService;
import org.elasticsearch.index.merge.policy.MergePolicyModule;
import org.elasticsearch.index.shard.IndexShard;
import org.elasticsearch.indices.IndicesService;
import org.elasticsearch.test.ElasticsearchIntegrationTest;
import org.elasticsearch.test.index.merge.NoMergePolicyProvider;
import org.junit.Test;

import java.io.IOException;

import static org.elasticsearch.common.xcontent.XContentFactory.jsonBuilder;
import static org.elasticsearch.test.hamcrest.ElasticsearchAssertions.assertAcked;
import static org.hamcrest.Matchers.equalTo;
import static org.hamcrest.Matchers.greaterThan;

/**
 */
public class ParentFieldLoadingTest extends ElasticsearchIntegrationTest {

    private final Settings indexSettings = Settings.builder()
            .put(IndexMetaData.SETTING_NUMBER_OF_SHARDS, 1)
            .put(IndexMetaData.SETTING_NUMBER_OF_REPLICAS, 0)
            .put(IndexShard.INDEX_REFRESH_INTERVAL, -1)
                    // We never want merges in this test to ensure we have two segments for the last validation
            .put(MergePolicyModule.MERGE_POLICY_TYPE_KEY, NoMergePolicyProvider.class)
            .build();

    @Test
    public void testEagerParentFieldLoading() throws Exception {
        logger.info("testing lazy loading...");
        assertAcked(prepareCreate("test")
                .setSettings(indexSettings)
                .addMapping("parent")
                .addMapping("child", childMapping(MappedFieldType.Loading.LAZY)));
        ensureGreen();

        client().prepareIndex("test", "parent", "1").setSource("{}").get();
        client().prepareIndex("test", "child", "1").setParent("1").setSource("{}").get();
        refresh();

        ClusterStatsResponse response = client().admin().cluster().prepareClusterStats().get();
        assertThat(response.getIndicesStats().getFieldData().getMemorySizeInBytes(), equalTo(0l));

        logger.info("testing default loading...");
        assertAcked(client().admin().indices().prepareDelete("test").get());
        assertAcked(prepareCreate("test")
                .setSettings(indexSettings)
                .addMapping("parent")
                .addMapping("child", "_parent", "type=parent"));
        ensureGreen();

        client().prepareIndex("test", "parent", "1").setSource("{}").get();
        client().prepareIndex("test", "child", "1").setParent("1").setSource("{}").get();
        refresh();

        response = client().admin().cluster().prepareClusterStats().get();
        assertThat(response.getIndicesStats().getFieldData().getMemorySizeInBytes(), equalTo(0l));

        logger.info("testing eager loading...");
        assertAcked(client().admin().indices().prepareDelete("test").get());
        assertAcked(prepareCreate("test")
                .setSettings(indexSettings)
                .addMapping("parent")
                .addMapping("child", childMapping(MappedFieldType.Loading.EAGER)));
        ensureGreen();

        client().prepareIndex("test", "parent", "1").setSource("{}").get();
        client().prepareIndex("test", "child", "1").setParent("1").setSource("{}").get();
        refresh();

        response = client().admin().cluster().prepareClusterStats().get();
        assertThat(response.getIndicesStats().getFieldData().getMemorySizeInBytes(), equalTo(0l));

        logger.info("testing eager global ordinals loading...");
        assertAcked(client().admin().indices().prepareDelete("test").get());
        assertAcked(prepareCreate("test")
                .setSettings(indexSettings)
                .addMapping("parent")
                .addMapping("child", childMapping(MappedFieldType.Loading.EAGER_GLOBAL_ORDINALS)));
        ensureGreen();

        // Need to do 2 separate refreshes, otherwise we have 1 segment and then we can't measure if global ordinals
        // is loaded by the size of the field data cache, because global ordinals on 1 segment shards takes no extra memory.
        client().prepareIndex("test", "parent", "1").setSource("{}").get();
        refresh();
        client().prepareIndex("test", "child", "1").setParent("1").setSource("{}").get();
        refresh();

        response = client().admin().cluster().prepareClusterStats().get();
        assertThat(response.getIndicesStats().getFieldData().getMemorySizeInBytes(), greaterThan(0l));
    }

    @Test
    public void testChangingEagerParentFieldLoadingAtRuntime() throws Exception {
        assertAcked(prepareCreate("test")
                .setSettings(indexSettings)
                .addMapping("parent")
                .addMapping("child", "_parent", "type=parent"));
        ensureGreen();

        client().prepareIndex("test", "parent", "1").setSource("{}").get();
        client().prepareIndex("test", "child", "1").setParent("1").setSource("{}").get();
        refresh();

        ClusterStatsResponse response = client().admin().cluster().prepareClusterStats().get();
        assertThat(response.getIndicesStats().getFieldData().getMemorySizeInBytes(), equalTo(0l));

        PutMappingResponse putMappingResponse = client().admin().indices().preparePutMapping("test").setType("child")
                .setSource(childMapping(MappedFieldType.Loading.EAGER_GLOBAL_ORDINALS))
                .get();
        assertAcked(putMappingResponse);
        assertBusy(new Runnable() {
            @Override
            public void run() {
                ClusterState clusterState = internalCluster().clusterService().state();
                ShardRouting shardRouting = clusterState.routingTable().index("test").shard(0).getShards().get(0);
                String nodeName = clusterState.getNodes().get(shardRouting.currentNodeId()).getName();

                boolean verified = false;
                IndicesService indicesService = internalCluster().getInstance(IndicesService.class, nodeName);
                IndexService indexService = indicesService.indexService("test");
                if (indexService != null) {
                    MapperService mapperService = indexService.mapperService();
                    DocumentMapper documentMapper = mapperService.documentMapper("child");
                    if (documentMapper != null) {
                        verified = documentMapper.parentFieldMapper().fieldType().fieldDataType().getLoading() == MappedFieldType.Loading.EAGER_GLOBAL_ORDINALS;
                    }
                }
                assertTrue(verified);
            }
        });

        // Need to add a new doc otherwise the refresh doesn't trigger a new searcher
        // Because it ends up in its own segment, but isn't of type parent or child, this doc doesn't contribute to the size of the fielddata cache
        client().prepareIndex("test", "dummy", "dummy").setSource("{}").get();
        refresh();
        response = client().admin().cluster().prepareClusterStats().get();
        assertThat(response.getIndicesStats().getFieldData().getMemorySizeInBytes(), greaterThan(0l));
    }

    private XContentBuilder childMapping(MappedFieldType.Loading loading) throws IOException {
        return jsonBuilder().startObject().startObject("child").startObject("_parent")
                .field("type", "parent")
                .startObject("fielddata").field(MappedFieldType.Loading.KEY, loading).endObject()
                .endObject().endObject().endObject();
    }

}


File: core/src/test/java/org/elasticsearch/test/ElasticsearchIntegrationTest.java
/*
 * Licensed to Elasticsearch under one or more contributor
 * license agreements. See the NOTICE file distributed with
 * this work for additional information regarding copyright
 * ownership. Elasticsearch licenses this file to you under
 * the Apache License, Version 2.0 (the "License"); you may
 * not use this file except in compliance with the License.
 * You may obtain a copy of the License at
 *
 *    http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing,
 * software distributed under the License is distributed on an
 * "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY
 * KIND, either express or implied.  See the License for the
 * specific language governing permissions and limitations
 * under the License.
 */
package org.elasticsearch.test;

import com.carrotsearch.randomizedtesting.RandomizedContext;
import com.carrotsearch.randomizedtesting.RandomizedTest;
import com.carrotsearch.randomizedtesting.Randomness;
import com.carrotsearch.randomizedtesting.annotations.TestGroup;
import com.carrotsearch.randomizedtesting.generators.RandomInts;
import com.carrotsearch.randomizedtesting.generators.RandomPicks;
import com.google.common.base.Joiner;
import com.google.common.base.Predicate;
import com.google.common.collect.Lists;
import org.apache.commons.lang3.StringUtils;
import org.apache.http.impl.client.HttpClients;
import org.apache.lucene.store.StoreRateLimiting;
import org.apache.lucene.util.IOUtils;
import org.apache.lucene.util.LuceneTestCase;
import org.apache.lucene.util.TestUtil;
import org.elasticsearch.ElasticsearchException;
import org.elasticsearch.ExceptionsHelper;
import org.elasticsearch.action.ActionListener;
import org.elasticsearch.action.ShardOperationFailedException;
import org.elasticsearch.action.admin.cluster.health.ClusterHealthRequest;
import org.elasticsearch.action.admin.cluster.health.ClusterHealthResponse;
import org.elasticsearch.action.admin.cluster.health.ClusterHealthStatus;
import org.elasticsearch.action.admin.cluster.node.info.NodeInfo;
import org.elasticsearch.action.admin.cluster.node.info.NodesInfoResponse;
import org.elasticsearch.action.admin.cluster.tasks.PendingClusterTasksResponse;
import org.elasticsearch.action.admin.indices.create.CreateIndexRequestBuilder;
import org.elasticsearch.action.admin.indices.exists.indices.IndicesExistsResponse;
import org.elasticsearch.action.admin.indices.flush.FlushResponse;
import org.elasticsearch.action.admin.indices.mapping.get.GetMappingsResponse;
import org.elasticsearch.action.admin.indices.optimize.OptimizeResponse;
import org.elasticsearch.action.admin.indices.refresh.RefreshResponse;
import org.elasticsearch.action.admin.indices.segments.IndicesSegmentResponse;
import org.elasticsearch.action.admin.indices.template.put.PutIndexTemplateRequestBuilder;
import org.elasticsearch.action.bulk.BulkRequestBuilder;
import org.elasticsearch.action.bulk.BulkResponse;
import org.elasticsearch.action.delete.DeleteResponse;
import org.elasticsearch.action.get.GetResponse;
import org.elasticsearch.action.index.IndexRequestBuilder;
import org.elasticsearch.action.index.IndexResponse;
import org.elasticsearch.action.search.ClearScrollResponse;
import org.elasticsearch.action.support.IndicesOptions;
import org.elasticsearch.client.AdminClient;
import org.elasticsearch.client.Client;
import org.elasticsearch.client.Requests;
import org.elasticsearch.cluster.ClusterService;
import org.elasticsearch.cluster.ClusterState;
import org.elasticsearch.cluster.metadata.IndexMetaData;
import org.elasticsearch.cluster.metadata.MappingMetaData;
import org.elasticsearch.cluster.metadata.MetaData;
import org.elasticsearch.cluster.routing.IndexRoutingTable;
import org.elasticsearch.cluster.routing.IndexShardRoutingTable;
import org.elasticsearch.cluster.routing.ShardRouting;
import org.elasticsearch.cluster.routing.allocation.decider.DiskThresholdDecider;
import org.elasticsearch.common.Nullable;
import org.elasticsearch.common.Priority;
import org.elasticsearch.common.Strings;
import org.elasticsearch.common.collect.ImmutableOpenMap;
import org.elasticsearch.common.collect.Tuple;
import org.elasticsearch.common.io.PathUtils;
import org.elasticsearch.common.regex.Regex;
import org.elasticsearch.common.settings.Settings;
import org.elasticsearch.common.transport.InetSocketTransportAddress;
import org.elasticsearch.common.transport.TransportAddress;
import org.elasticsearch.common.unit.ByteSizeUnit;
import org.elasticsearch.common.unit.ByteSizeValue;
import org.elasticsearch.common.unit.TimeValue;
import org.elasticsearch.common.util.concurrent.EsRejectedExecutionException;
import org.elasticsearch.common.xcontent.ToXContent;
import org.elasticsearch.common.xcontent.XContentBuilder;
import org.elasticsearch.common.xcontent.XContentFactory;
import org.elasticsearch.common.xcontent.XContentHelper;
import org.elasticsearch.common.xcontent.json.JsonXContent;
import org.elasticsearch.common.xcontent.support.XContentMapValues;
import org.elasticsearch.discovery.zen.elect.ElectMasterService;
import org.elasticsearch.env.Environment;
import org.elasticsearch.index.IndexService;
import org.elasticsearch.index.codec.CodecService;
import org.elasticsearch.index.fielddata.FieldDataType;
import org.elasticsearch.index.mapper.DocumentMapper;
import org.elasticsearch.index.mapper.MappedFieldType;
import org.elasticsearch.index.mapper.MappedFieldType.Loading;
import org.elasticsearch.index.mapper.internal.SizeFieldMapper;
import org.elasticsearch.index.mapper.internal.TimestampFieldMapper;
import org.elasticsearch.index.merge.policy.*;
import org.elasticsearch.index.merge.scheduler.ConcurrentMergeSchedulerProvider;
import org.elasticsearch.index.translog.Translog;
import org.elasticsearch.index.translog.TranslogConfig;
import org.elasticsearch.index.translog.TranslogService;
import org.elasticsearch.index.translog.TranslogWriter;
import org.elasticsearch.indices.IndicesService;
import org.elasticsearch.indices.cache.query.IndicesQueryCache;
import org.elasticsearch.indices.fielddata.cache.IndicesFieldDataCache;
import org.elasticsearch.indices.flush.IndicesSyncedFlushResult;
import org.elasticsearch.indices.flush.SyncedFlushService;
import org.elasticsearch.indices.recovery.RecoverySettings;
import org.elasticsearch.indices.store.IndicesStore;
import org.elasticsearch.node.Node;
import org.elasticsearch.rest.RestStatus;
import org.elasticsearch.script.ScriptService;
import org.elasticsearch.search.SearchService;
import org.elasticsearch.test.client.RandomizingClient;
import org.elasticsearch.test.disruption.ServiceDisruptionScheme;
import org.elasticsearch.test.rest.client.http.HttpRequestBuilder;
import org.elasticsearch.transport.netty.NettyTransport;
import org.hamcrest.Matchers;
import org.joda.time.DateTimeZone;
import org.junit.*;

import java.io.IOException;
import java.io.InputStream;
import java.lang.annotation.*;
import java.net.InetSocketAddress;
import java.nio.file.DirectoryStream;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.*;
import java.util.concurrent.*;
import java.util.concurrent.atomic.AtomicInteger;
import java.util.concurrent.atomic.AtomicLong;

import static org.elasticsearch.cluster.metadata.IndexMetaData.SETTING_NUMBER_OF_REPLICAS;
import static org.elasticsearch.cluster.metadata.IndexMetaData.SETTING_NUMBER_OF_SHARDS;
import static org.elasticsearch.common.settings.Settings.settingsBuilder;
import static org.elasticsearch.index.query.QueryBuilders.matchAllQuery;
import static org.elasticsearch.test.XContentTestUtils.convertToMap;
import static org.elasticsearch.test.XContentTestUtils.mapsEqualIgnoringArrayOrder;
import static org.elasticsearch.test.hamcrest.ElasticsearchAssertions.*;
import static org.hamcrest.Matchers.*;

/**
 * {@link ElasticsearchIntegrationTest} is an abstract base class to run integration
 * tests against a JVM private Elasticsearch Cluster. The test class supports 2 different
 * cluster scopes.
 * <ul>
 * <li>{@link Scope#TEST} - uses a new cluster for each individual test method.</li>
 * <li>{@link Scope#SUITE} - uses a cluster shared across all test methods in the same suite</li>
 * </ul>
 * <p/>
 * The most common test scope is {@link Scope#SUITE} which shares a cluster per test suite.
 * <p/>
 * If the test methods need specific node settings or change persistent and/or transient cluster settings {@link Scope#TEST}
 * should be used. To configure a scope for the test cluster the {@link ClusterScope} annotation
 * should be used, here is an example:
 * <pre>
 *
 * @ClusterScope(scope=Scope.TEST) public class SomeIntegrationTest extends ElasticsearchIntegrationTest {
 * @Test public void testMethod() {}
 * }
 * </pre>
 * <p/>
 * If no {@link ClusterScope} annotation is present on an integration test the default scope is {@link Scope#SUITE}
 * <p/>
 * A test cluster creates a set of nodes in the background before the test starts. The number of nodes in the cluster is
 * determined at random and can change across tests. The {@link ClusterScope} allows configuring the initial number of nodes
 * that are created before the tests start.
 * <p/>
 *  <pre>
 * @ClusterScope(scope=Scope.SUITE, numDataNodes=3)
 * public class SomeIntegrationTest extends ElasticsearchIntegrationTest {
 * @Test public void testMethod() {}
 * }
 * </pre>
 * <p/>
 * Note, the {@link ElasticsearchIntegrationTest} uses randomized settings on a cluster and index level. For instance
 * each test might use different directory implementation for each test or will return a random client to one of the
 * nodes in the cluster for each call to {@link #client()}. Test failures might only be reproducible if the correct
 * system properties are passed to the test execution environment.
 * <p/>
 * <p>
 * This class supports the following system properties (passed with -Dkey=value to the application)
 * <ul>
 * <li>-D{@value #TESTS_CLIENT_RATIO} - a double value in the interval [0..1] which defines the ration between node and transport clients used</li>
 * <li>-D{@value InternalTestCluster#TESTS_ENABLE_MOCK_MODULES} - a boolean value to enable or disable mock modules. This is
 * useful to test the system without asserting modules that to make sure they don't hide any bugs in production.</li>
 * <li> - a random seed used to initialize the index random context.
 * </ul>
 * </p>
 */
@Ignore
@ElasticsearchIntegrationTest.Integration
@LuceneTestCase.SuppressFileSystems("ExtrasFS") // doesn't work with potential multi data path from test cluster yet
public abstract class ElasticsearchIntegrationTest extends ElasticsearchTestCase {

    /**
     * Property that allows to control whether the Integration tests are run (default) or not
     */
    public static final String SYSPROP_INTEGRATION = "tests.integration";

    /**
     * Annotation for integration tests
     */
    @Inherited
    @Retention(RetentionPolicy.RUNTIME)
    @Target(ElementType.TYPE)
    @TestGroup(enabled = true, sysProperty = ElasticsearchIntegrationTest.SYSPROP_INTEGRATION)
    public @interface Integration {
    }

    /**
     * Property that controls whether ThirdParty Integration tests are run (not the default).
     */
    public static final String SYSPROP_THIRDPARTY = "tests.thirdparty";

    /**
     * Annotation for third-party integration tests.
     * <p/>
     * These are tests the require a third-party service in order to run. They
     * may require the user to manually configure an external process (such as rabbitmq),
     * or may additionally require some external configuration (e.g. AWS credentials)
     * via the {@code tests.config} system property.
     */
    @Inherited
    @Retention(RetentionPolicy.RUNTIME)
    @Target(ElementType.TYPE)
    @TestGroup(enabled = false, sysProperty = ElasticsearchIntegrationTest.SYSPROP_THIRDPARTY)
    public @interface ThirdParty {
    }

    /** node names of the corresponding clusters will start with these prefixes */
    public static final String SUITE_CLUSTER_NODE_PREFIX = "node_s";
    public static final String TEST_CLUSTER_NODE_PREFIX = "node_t";

    /**
     * Key used to set the transport client ratio via the commandline -D{@value #TESTS_CLIENT_RATIO}
     */
    public static final String TESTS_CLIENT_RATIO = "tests.client.ratio";

    /**
     * Key used to eventually switch to using an external cluster and provide its transport addresses
     */
    public static final String TESTS_CLUSTER = "tests.cluster";

    /**
     * Key used to retrieve the index random seed from the index settings on a running node.
     * The value of this seed can be used to initialize a random context for a specific index.
     * It's set once per test via a generic index template.
     */
    public static final String SETTING_INDEX_SEED = "index.tests.seed";

    /**
     * Threshold at which indexing switches from frequently async to frequently bulk.
     */
    private static final int FREQUENT_BULK_THRESHOLD = 300;

    /**
     * Threshold at which bulk indexing will always be used.
     */
    private static final int ALWAYS_BULK_THRESHOLD = 3000;

    /**
     * Maximum number of async operations that indexRandom will kick off at one time.
     */
    private static final int MAX_IN_FLIGHT_ASYNC_INDEXES = 150;

    /**
     * Maximum number of documents in a single bulk index request.
     */
    private static final int MAX_BULK_INDEX_REQUEST_SIZE = 1000;

    /**
     * Default minimum number of shards for an index
     */
    protected static final int DEFAULT_MIN_NUM_SHARDS = 1;

    /**
     * Default maximum number of shards for an index
     */
    protected static final int DEFAULT_MAX_NUM_SHARDS = 10;

    /**
     * The current cluster depending on the configured {@link Scope}.
     * By default if no {@link ClusterScope} is configured this will hold a reference to the suite cluster.
     */
    private static TestCluster currentCluster;

    private static final double TRANSPORT_CLIENT_RATIO = transportClientRatio();

    private static final Map<Class<?>, TestCluster> clusters = new IdentityHashMap<>();

    private static ElasticsearchIntegrationTest INSTANCE = null; // see @SuiteScope
    private static Long SUITE_SEED = null;

    @BeforeClass
    public static void beforeClass() throws Exception {
        SUITE_SEED = randomLong();
        initializeSuiteScope();
    }

    protected final void beforeInternal() throws Exception {
        assert Thread.getDefaultUncaughtExceptionHandler() instanceof ElasticsearchUncaughtExceptionHandler;
        try {
            final Scope currentClusterScope = getCurrentClusterScope();
            switch (currentClusterScope) {
                case SUITE:
                    assert SUITE_SEED != null : "Suite seed was not initialized";
                    currentCluster = buildAndPutCluster(currentClusterScope, SUITE_SEED);
                    break;
                case TEST:
                    currentCluster = buildAndPutCluster(currentClusterScope, randomLong());
                    break;
                default:
                    fail("Unknown Scope: [" + currentClusterScope + "]");
            }
            cluster().beforeTest(getRandom(), getPerTestTransportClientRatio());
            cluster().wipe();
            randomIndexTemplate();
            printTestMessage("before");
        } catch (OutOfMemoryError e) {
            if (e.getMessage().contains("unable to create new native thread")) {
                ElasticsearchTestCase.printStackDump(logger);
            }
            throw e;
        }
    }

    private void printTestMessage(String message) {
        if (isSuiteScopedTest(getClass())) {
            logger.info("[{}]: {} suite", getTestClass().getSimpleName(), message);
        } else {
            logger.info("[{}#{}]: {} test", getTestClass().getSimpleName(), getTestName(), message);
        }
    }

    private Loading randomLoadingValues() {
        return randomFrom(Loading.values());
    }

    /**
     * Creates a randomized index template. This template is used to pass in randomized settings on a
     * per index basis. Allows to enable/disable the randomization for number of shards and replicas
     */
    public void randomIndexTemplate() throws IOException {

        // TODO move settings for random directory etc here into the index based randomized settings.
        if (cluster().size() > 0) {
            Settings.Builder randomSettingsBuilder =
                    setRandomSettings(getRandom(), Settings.builder())
                            .put(SETTING_INDEX_SEED, getRandom().nextLong());

            randomSettingsBuilder.put(SETTING_NUMBER_OF_SHARDS, numberOfShards())
                    .put(SETTING_NUMBER_OF_REPLICAS, numberOfReplicas());

            // if the test class is annotated with SuppressCodecs("*"), it means don't use lucene's codec randomization
            // otherwise, use it, it has assertions and so on that can find bugs.
            SuppressCodecs annotation = getClass().getAnnotation(SuppressCodecs.class);
            if (annotation != null && annotation.value().length == 1 && "*".equals(annotation.value()[0])) {
                randomSettingsBuilder.put("index.codec", randomFrom(CodecService.DEFAULT_CODEC, CodecService.BEST_COMPRESSION_CODEC));
            } else {
                randomSettingsBuilder.put("index.codec", CodecService.LUCENE_DEFAULT_CODEC);
            }
            XContentBuilder mappings = null;
            if (frequently() && randomDynamicTemplates()) {
                mappings = XContentFactory.jsonBuilder().startObject().startObject("_default_");
                if (randomBoolean()) {
                    boolean timestampEnabled = randomBoolean();
                    mappings.startObject(TimestampFieldMapper.NAME)
                            .field("enabled", timestampEnabled);
                    if (timestampEnabled) {
                        mappings.field("doc_values", randomBoolean());
                    }
                    mappings.endObject();
                }
                if (randomBoolean()) {
                    mappings.startObject(SizeFieldMapper.NAME)
                            .field("enabled", randomBoolean())
                            .endObject();
                }
                mappings.startArray("dynamic_templates")
                        .startObject()
                        .startObject("template-strings")
                        .field("match_mapping_type", "string")
                        .startObject("mapping")
                        .startObject("fielddata")
                        .field(FieldDataType.FORMAT_KEY, randomFrom("paged_bytes", "fst"))
                        .field(Loading.KEY, randomLoadingValues())
                        .endObject()
                        .endObject()
                        .endObject()
                        .endObject()
                        .startObject()
                        .startObject("template-longs")
                        .field("match_mapping_type", "long")
                        .startObject("mapping")
                        .field("doc_values", randomBoolean())
                        .startObject("fielddata")
                        .field(Loading.KEY, randomFrom(Loading.LAZY, Loading.EAGER))
                        .endObject()
                        .endObject()
                        .endObject()
                        .endObject()
                        .startObject()
                        .startObject("template-doubles")
                        .field("match_mapping_type", "double")
                        .startObject("mapping")
                        .field("doc_values", randomBoolean())
                        .startObject("fielddata")
                        .field(Loading.KEY, randomFrom(Loading.LAZY, Loading.EAGER))
                        .endObject()
                        .endObject()
                        .endObject()
                        .endObject()
                        .startObject()
                        .startObject("template-geo_points")
                        .field("match_mapping_type", "geo_point")
                        .startObject("mapping")
                        .field("doc_values", randomBoolean())
                        .startObject("fielddata")
                        .field(Loading.KEY, randomFrom(Loading.LAZY, Loading.EAGER))
                        .endObject()
                        .endObject()
                        .endObject()
                        .endObject()
                        .startObject()
                        .startObject("template-booleans")
                        .field("match_mapping_type", "boolean")
                        .startObject("mapping")
                        .startObject("fielddata")
                        .field(FieldDataType.FORMAT_KEY, randomFrom("array", "doc_values"))
                        .field(Loading.KEY, randomFrom(Loading.LAZY, Loading.EAGER))
                        .endObject()
                        .endObject()
                        .endObject()
                        .endObject()
                        .endArray();
                mappings.endObject().endObject();
            }

            PutIndexTemplateRequestBuilder putTemplate = client().admin().indices()
                    .preparePutTemplate("random_index_template")
                    .setTemplate("*")
                    .setOrder(0)
                    .setSettings(randomSettingsBuilder);
            if (mappings != null) {
                logger.info("test using _default_ mappings: [{}]", mappings.bytesStream().bytes().toUtf8());
                putTemplate.addMapping("_default_", mappings);
            }
            assertAcked(putTemplate.execute().actionGet());
        }
    }

    protected Settings.Builder setRandomSettings(Random random, Settings.Builder builder) {
        setRandomMerge(random, builder);
        setRandomTranslogSettings(random, builder);
        setRandomNormsLoading(random, builder);
        setRandomScriptingSettings(random, builder);
        if (random.nextBoolean()) {
            if (random.nextInt(10) == 0) { // do something crazy slow here
                builder.put(IndicesStore.INDICES_STORE_THROTTLE_MAX_BYTES_PER_SEC, new ByteSizeValue(RandomInts.randomIntBetween(random, 1, 10), ByteSizeUnit.MB));
            } else {
                builder.put(IndicesStore.INDICES_STORE_THROTTLE_MAX_BYTES_PER_SEC, new ByteSizeValue(RandomInts.randomIntBetween(random, 10, 200), ByteSizeUnit.MB));
            }
        }
        if (random.nextBoolean()) {
            builder.put(IndicesStore.INDICES_STORE_THROTTLE_TYPE, RandomPicks.randomFrom(random, StoreRateLimiting.Type.values()));
        }

        if (random.nextBoolean()) {
            builder.put(ConcurrentMergeSchedulerProvider.AUTO_THROTTLE, false);
        }

        if (random.nextBoolean()) {
            if (random.nextInt(10) == 0) { // do something crazy slow here
                builder.put(RecoverySettings.INDICES_RECOVERY_MAX_BYTES_PER_SEC, new ByteSizeValue(RandomInts.randomIntBetween(random, 1, 10), ByteSizeUnit.MB));
            } else {
                builder.put(RecoverySettings.INDICES_RECOVERY_MAX_BYTES_PER_SEC, new ByteSizeValue(RandomInts.randomIntBetween(random, 10, 200), ByteSizeUnit.MB));
            }
        }

        if (random.nextBoolean()) {
            builder.put(RecoverySettings.INDICES_RECOVERY_COMPRESS, random.nextBoolean());
        }

        if (random.nextBoolean()) {
            builder.put(TranslogConfig.INDEX_TRANSLOG_FS_TYPE, RandomPicks.randomFrom(random, TranslogWriter.Type.values()).name());
        }

        if (random.nextBoolean()) {
            builder.put(IndicesQueryCache.INDEX_CACHE_QUERY_ENABLED, random.nextBoolean());
        }

        if (random.nextBoolean()) {
            builder.put("index.shard.check_on_startup", randomFrom(random, "false", "checksum", "true"));
        }

        if (random.nextBoolean()) {
            builder.put(IndicesQueryCache.INDICES_CACHE_QUERY_CONCURRENCY_LEVEL, RandomInts.randomIntBetween(random, 1, 32));
            builder.put(IndicesFieldDataCache.FIELDDATA_CACHE_CONCURRENCY_LEVEL, RandomInts.randomIntBetween(random, 1, 32));
        }
        if (random.nextBoolean()) {
            builder.put(NettyTransport.PING_SCHEDULE, RandomInts.randomIntBetween(random, 100, 2000) + "ms");
        }
        return builder;
    }

    private static Settings.Builder setRandomScriptingSettings(Random random, Settings.Builder builder) {
        if (random.nextBoolean()) {
            builder.put(ScriptService.SCRIPT_CACHE_SIZE_SETTING, RandomInts.randomIntBetween(random, -100, 2000));
        }
        if (random.nextBoolean()) {
            builder.put(ScriptService.SCRIPT_CACHE_EXPIRE_SETTING, TimeValue.timeValueMillis(RandomInts.randomIntBetween(random, 750, 10000000)));
        }
        return builder;
    }

    private static Settings.Builder setRandomMerge(Random random, Settings.Builder builder) {
        if (random.nextBoolean()) {
            builder.put(AbstractMergePolicyProvider.INDEX_COMPOUND_FORMAT,
                    random.nextBoolean() ? random.nextDouble() : random.nextBoolean());
        }
        Class<? extends MergePolicyProvider<?>> mergePolicy = TieredMergePolicyProvider.class;
        switch (random.nextInt(5)) {
            case 4:
                mergePolicy = LogByteSizeMergePolicyProvider.class;
                break;
            case 3:
                mergePolicy = LogDocMergePolicyProvider.class;
                break;
            case 0:
                mergePolicy = null;
        }
        if (mergePolicy != null) {
            builder.put(MergePolicyModule.MERGE_POLICY_TYPE_KEY, mergePolicy.getName());
        }

        switch (random.nextInt(4)) {
            case 3:
                final int maxThreadCount = RandomInts.randomIntBetween(random, 1, 4);
                final int maxMergeCount = RandomInts.randomIntBetween(random, maxThreadCount, maxThreadCount + 4);
                builder.put(ConcurrentMergeSchedulerProvider.MAX_MERGE_COUNT, maxMergeCount);
                builder.put(ConcurrentMergeSchedulerProvider.MAX_THREAD_COUNT, maxThreadCount);
                break;
        }

        return builder;
    }

    private static Settings.Builder setRandomNormsLoading(Random random, Settings.Builder builder) {
        if (random.nextBoolean()) {
            builder.put(SearchService.NORMS_LOADING_KEY, RandomPicks.randomFrom(random, Arrays.asList(MappedFieldType.Loading.EAGER, MappedFieldType.Loading.LAZY)));
        }
        return builder;
    }

    private static Settings.Builder setRandomTranslogSettings(Random random, Settings.Builder builder) {
        if (random.nextBoolean()) {
            builder.put(TranslogService.INDEX_TRANSLOG_FLUSH_THRESHOLD_OPS, RandomInts.randomIntBetween(random, 1, 10000));
        }
        if (random.nextBoolean()) {
            builder.put(TranslogService.INDEX_TRANSLOG_FLUSH_THRESHOLD_SIZE, new ByteSizeValue(RandomInts.randomIntBetween(random, 1, 300), ByteSizeUnit.MB));
        }
        if (random.nextBoolean()) {
            builder.put(TranslogService.INDEX_TRANSLOG_FLUSH_THRESHOLD_PERIOD, TimeValue.timeValueMinutes(RandomInts.randomIntBetween(random, 1, 60)));
        }
        if (random.nextBoolean()) {
            builder.put(TranslogService.INDEX_TRANSLOG_FLUSH_INTERVAL, TimeValue.timeValueMillis(RandomInts.randomIntBetween(random, 1, 10000)));
        }
        if (random.nextBoolean()) {
            builder.put(TranslogService.INDEX_TRANSLOG_DISABLE_FLUSH, random.nextBoolean());
        }
        if (random.nextBoolean()) {
            builder.put(TranslogConfig.INDEX_TRANSLOG_DURABILITY, RandomPicks.randomFrom(random, Translog.Durabilty.values()));
        }
        return builder;
    }

    private TestCluster buildWithPrivateContext(final Scope scope, final long seed) throws Exception {
        return RandomizedContext.current().runWithPrivateRandomness(new Randomness(seed), new Callable<TestCluster>() {
            @Override
            public TestCluster call() throws Exception {
                return buildTestCluster(scope, seed);
            }
        });
    }

    private TestCluster buildAndPutCluster(Scope currentClusterScope, long seed) throws Exception {
        final Class<?> clazz = this.getClass();
        TestCluster testCluster = clusters.remove(clazz); // remove this cluster first
        clearClusters(); // all leftovers are gone by now... this is really just a double safety if we miss something somewhere
        switch (currentClusterScope) {
            case SUITE:
                if (testCluster == null) { // only build if it's not there yet
                    testCluster = buildWithPrivateContext(currentClusterScope, seed);
                }
                break;
            case TEST:
                // close the previous one and create a new one
                IOUtils.closeWhileHandlingException(testCluster);
                testCluster = buildTestCluster(currentClusterScope, seed);
                break;
        }
        clusters.put(clazz, testCluster);
        return testCluster;
    }

    private static void clearClusters() throws IOException {
        if (!clusters.isEmpty()) {
            IOUtils.close(clusters.values());
            clusters.clear();
        }
    }

    protected final void afterInternal(boolean afterClass) throws Exception {
        boolean success = false;
        try {
            final Scope currentClusterScope = getCurrentClusterScope();
            printTestMessage("cleaning up after");
            clearDisruptionScheme();
            try {
                if (cluster() != null) {
                    if (currentClusterScope != Scope.TEST) {
                        MetaData metaData = client().admin().cluster().prepareState().execute().actionGet().getState().getMetaData();
                        assertThat("test leaves persistent cluster metadata behind: " + metaData.persistentSettings().getAsMap(), metaData
                                .persistentSettings().getAsMap().size(), equalTo(0));
                        assertThat("test leaves transient cluster metadata behind: " + metaData.transientSettings().getAsMap(), metaData
                                .transientSettings().getAsMap().size(), equalTo(0));
                    }
                    ensureClusterSizeConsistency();
                    ensureClusterStateConsistency();
                    beforeIndexDeletion();
                    cluster().wipe(); // wipe after to make sure we fail in the test that didn't ack the delete
                    if (afterClass || currentClusterScope == Scope.TEST) {
                        cluster().close();
                    }
                    cluster().assertAfterTest();
                }
            } finally {
                if (currentClusterScope == Scope.TEST) {
                    clearClusters(); // it is ok to leave persistent / transient cluster state behind if scope is TEST
                }
            }
            printTestMessage("cleaned up after");
            success = true;
        } finally {
            if (!success) {
                // if we failed here that means that something broke horribly so we should clear all clusters
                // TODO: just let the exception happen, WTF is all this horseshit
                // afterTestRule.forceFailure();
            }
        }
    }

    protected void beforeIndexDeletion() {
        cluster().beforeIndexDeletion();
    }

    public static TestCluster cluster() {
        return currentCluster;
    }

    public static boolean isInternalCluster() {
        return (currentCluster instanceof InternalTestCluster);
    }

    public static InternalTestCluster internalCluster() {
        if (!isInternalCluster()) {
            throw new UnsupportedOperationException("current test cluster is immutable");
        }
        return (InternalTestCluster) currentCluster;
    }

    public ClusterService clusterService() {
        return internalCluster().clusterService();
    }

    public static Client client() {
        return client(null);
    }

    public static Client client(@Nullable String node) {
        if (node != null) {
            return internalCluster().client(node);
        }
        Client client = cluster().client();
        if (frequently()) {
            client = new RandomizingClient(client, getRandom());
        }
        return client;
    }

    public static Client dataNodeClient() {
        Client client = internalCluster().dataNodeClient();
        if (frequently()) {
            client = new RandomizingClient(client, getRandom());
        }
        return client;
    }

    public static Iterable<Client> clients() {
        return cluster();
    }

    protected int minimumNumberOfShards() {
        return DEFAULT_MIN_NUM_SHARDS;
    }

    protected int maximumNumberOfShards() {
        return DEFAULT_MAX_NUM_SHARDS;
    }

    protected int numberOfShards() {
        return between(minimumNumberOfShards(), maximumNumberOfShards());
    }

    protected int minimumNumberOfReplicas() {
        return 0;
    }

    protected int maximumNumberOfReplicas() {
        //use either 0 or 1 replica, yet a higher amount when possible, but only rarely
        int maxNumReplicas = Math.max(0, cluster().numDataNodes() - 1);
        return frequently() ? Math.min(1, maxNumReplicas) : maxNumReplicas;
    }

    protected int numberOfReplicas() {
        return between(minimumNumberOfReplicas(), maximumNumberOfReplicas());
    }


    public void setDisruptionScheme(ServiceDisruptionScheme scheme) {
        internalCluster().setDisruptionScheme(scheme);
    }

    public void clearDisruptionScheme() {
        if (isInternalCluster()) {
            internalCluster().clearDisruptionScheme();
        }
    }

    /**
     * Returns a settings object used in {@link #createIndex(String...)} and {@link #prepareCreate(String)} and friends.
     * This method can be overwritten by subclasses to set defaults for the indices that are created by the test.
     * By default it returns a settings object that sets a random number of shards. Number of shards and replicas
     * can be controlled through specific methods.
     */
    public Settings indexSettings() {
        Settings.Builder builder = Settings.builder();
        int numberOfShards = numberOfShards();
        if (numberOfShards > 0) {
            builder.put(SETTING_NUMBER_OF_SHARDS, numberOfShards).build();
        }
        int numberOfReplicas = numberOfReplicas();
        if (numberOfReplicas >= 0) {
            builder.put(SETTING_NUMBER_OF_REPLICAS, numberOfReplicas).build();
        }
        // 30% of the time
        if (randomInt(9) < 3) {
            final Path dataPath = createTempDir();
            logger.info("using custom data_path for index: [{}]", dataPath);
            builder.put(IndexMetaData.SETTING_DATA_PATH, dataPath);
        }
        return builder.build();
    }

    /**
     * Creates one or more indices and asserts that the indices are acknowledged. If one of the indices
     * already exists this method will fail and wipe all the indices created so far.
     */
    public final void createIndex(String... names) {

        List<String> created = new ArrayList<>();
        for (String name : names) {
            boolean success = false;
            try {
                assertAcked(prepareCreate(name));
                created.add(name);
                success = true;
            } finally {
                if (!success && !created.isEmpty()) {
                    cluster().wipeIndices(created.toArray(new String[created.size()]));
                }
            }
        }
    }

    /**
     * Creates a new {@link CreateIndexRequestBuilder} with the settings obtained from {@link #indexSettings()}.
     */
    public final CreateIndexRequestBuilder prepareCreate(String index) {
        return client().admin().indices().prepareCreate(index).setSettings(indexSettings());
    }

    /**
     * Creates a new {@link CreateIndexRequestBuilder} with the settings obtained from {@link #indexSettings()}.
     * The index that is created with this builder will only be allowed to allocate on the number of nodes passed to this
     * method.
     * <p>
     * This method uses allocation deciders to filter out certain nodes to allocate the created index on. It defines allocation
     * rules based on <code>index.routing.allocation.exclude._name</code>.
     * </p>
     */
    public final CreateIndexRequestBuilder prepareCreate(String index, int numNodes) {
        return prepareCreate(index, numNodes, Settings.builder());
    }

    /**
     * Creates a new {@link CreateIndexRequestBuilder} with the settings obtained from {@link #indexSettings()}.
     * The index that is created with this builder will only be allowed to allocate on the number of nodes passed to this
     * method.
     * <p>
     * This method uses allocation deciders to filter out certain nodes to allocate the created index on. It defines allocation
     * rules based on <code>index.routing.allocation.exclude._name</code>.
     * </p>
     */
    public CreateIndexRequestBuilder prepareCreate(String index, int numNodes, Settings.Builder settingsBuilder) {
        internalCluster().ensureAtLeastNumDataNodes(numNodes);

        Settings.Builder builder = Settings.builder().put(indexSettings()).put(settingsBuilder.build());

        if (numNodes > 0) {
            getExcludeSettings(index, numNodes, builder);
        }
        return client().admin().indices().prepareCreate(index).setSettings(builder.build());
    }

    private Settings.Builder getExcludeSettings(String index, int num, Settings.Builder builder) {
        String exclude = Joiner.on(',').join(internalCluster().allDataNodesButN(num));
        builder.put("index.routing.allocation.exclude._name", exclude);
        return builder;
    }

    /**
     * Waits until all nodes have no pending tasks.
     */
    public void waitNoPendingTasksOnAll() throws Exception {
        assertNoTimeout(client().admin().cluster().prepareHealth().setWaitForEvents(Priority.LANGUID).get());
        assertBusy(new Runnable() {
            @Override
            public void run() {
                for (Client client : clients()) {
                    ClusterHealthResponse clusterHealth = client.admin().cluster().prepareHealth().setLocal(true).get();
                    assertThat("client " + client + " still has in flight fetch", clusterHealth.getNumberOfInFlightFetch(), equalTo(0));
                    PendingClusterTasksResponse pendingTasks = client.admin().cluster().preparePendingClusterTasks().setLocal(true).get();
                    assertThat("client " + client + " still has pending tasks " + pendingTasks.prettyPrint(), pendingTasks, Matchers.emptyIterable());
                    clusterHealth = client.admin().cluster().prepareHealth().setLocal(true).get();
                    assertThat("client " + client + " still has in flight fetch", clusterHealth.getNumberOfInFlightFetch(), equalTo(0));
                }
            }
        });
        assertNoTimeout(client().admin().cluster().prepareHealth().setWaitForEvents(Priority.LANGUID).get());
    }

    /**
     * Waits till a (pattern) field name mappings concretely exists on all nodes. Note, this waits for the current
     * started shards and checks for concrete mappings.
     */
    public void assertConcreteMappingsOnAll(final String index, final String type, final String... fieldNames) throws Exception {
        Set<String> nodes = internalCluster().nodesInclude(index);
        assertThat(nodes, Matchers.not(Matchers.emptyIterable()));
        for (String node : nodes) {
            IndicesService indicesService = internalCluster().getInstance(IndicesService.class, node);
            IndexService indexService = indicesService.indexService(index);
            assertThat("index service doesn't exists on " + node, indexService, notNullValue());
            DocumentMapper documentMapper = indexService.mapperService().documentMapper(type);
            assertThat("document mapper doesn't exists on " + node, documentMapper, notNullValue());
            for (String fieldName : fieldNames) {
                Collection<String> matches = documentMapper.mappers().simpleMatchToFullName(fieldName);
                assertThat("field " + fieldName + " doesn't exists on " + node, matches, Matchers.not(emptyIterable()));
            }
        }
        assertMappingOnMaster(index, type, fieldNames);
    }

    /**
     * Waits for the given mapping type to exists on the master node.
     */
    public void assertMappingOnMaster(final String index, final String type, final String... fieldNames) throws Exception {
        GetMappingsResponse response = client().admin().indices().prepareGetMappings(index).setTypes(type).get();
        ImmutableOpenMap<String, MappingMetaData> mappings = response.getMappings().get(index);
        assertThat(mappings, notNullValue());
        MappingMetaData mappingMetaData = mappings.get(type);
        assertThat(mappingMetaData, notNullValue());

        Map<String, Object> mappingSource = mappingMetaData.getSourceAsMap();
        assertFalse(mappingSource.isEmpty());
        assertTrue(mappingSource.containsKey("properties"));

        for (String fieldName : fieldNames) {
            Map<String, Object> mappingProperties = (Map<String, Object>) mappingSource.get("properties");
            if (fieldName.indexOf('.') != -1) {
                fieldName = fieldName.replace(".", ".properties.");
            }
            assertThat("field " + fieldName + " doesn't exists in mapping " + mappingMetaData.source().string(), XContentMapValues.extractValue(fieldName, mappingProperties), notNullValue());
        }
    }

    /**
     * Restricts the given index to be allocated on <code>n</code> nodes using the allocation deciders.
     * Yet if the shards can't be allocated on any other node shards for this index will remain allocated on
     * more than <code>n</code> nodes.
     */
    public void allowNodes(String index, int n) {
        assert index != null;
        internalCluster().ensureAtLeastNumDataNodes(n);
        Settings.Builder builder = Settings.builder();
        if (n > 0) {
            getExcludeSettings(index, n, builder);
        }
        Settings build = builder.build();
        if (!build.getAsMap().isEmpty()) {
            logger.debug("allowNodes: updating [{}]'s setting to [{}]", index, build.toDelimitedString(';'));
            client().admin().indices().prepareUpdateSettings(index).setSettings(build).execute().actionGet();
        }
    }

    /**
     * Ensures the cluster has a green state via the cluster health API. This method will also wait for relocations.
     * It is useful to ensure that all action on the cluster have finished and all shards that were currently relocating
     * are now allocated and started.
     */
    public ClusterHealthStatus ensureGreen(String... indices) {
        return ensureGreen(TimeValue.timeValueSeconds(30), indices);
    }

    /**
     * Ensures the cluster has a green state via the cluster health API. This method will also wait for relocations.
     * It is useful to ensure that all action on the cluster have finished and all shards that were currently relocating
     * are now allocated and started.
     *
     * @param timeout time out value to set on {@link org.elasticsearch.action.admin.cluster.health.ClusterHealthRequest}
     */
    public ClusterHealthStatus ensureGreen(TimeValue timeout, String... indices) {
        ClusterHealthResponse actionGet = client().admin().cluster()
                .health(Requests.clusterHealthRequest(indices).timeout(timeout).waitForGreenStatus().waitForEvents(Priority.LANGUID).waitForRelocatingShards(0)).actionGet();
        if (actionGet.isTimedOut()) {
            logger.info("ensureGreen timed out, cluster state:\n{}\n{}", client().admin().cluster().prepareState().get().getState().prettyPrint(), client().admin().cluster().preparePendingClusterTasks().get().prettyPrint());
            fail("timed out waiting for green state");
        }
        assertThat(actionGet.getStatus(), equalTo(ClusterHealthStatus.GREEN));
        logger.debug("indices {} are green", indices.length == 0 ? "[_all]" : indices);
        return actionGet.getStatus();
    }

    /**
     * Waits for all relocating shards to become active using the cluster health API.
     */
    public ClusterHealthStatus waitForRelocation() {
        return waitForRelocation(null);
    }

    /**
     * Waits for all relocating shards to become active and the cluster has reached the given health status
     * using the cluster health API.
     */
    public ClusterHealthStatus waitForRelocation(ClusterHealthStatus status) {
        ClusterHealthRequest request = Requests.clusterHealthRequest().waitForRelocatingShards(0);
        if (status != null) {
            request.waitForStatus(status);
        }
        ClusterHealthResponse actionGet = client().admin().cluster()
                .health(request).actionGet();
        if (actionGet.isTimedOut()) {
            logger.info("waitForRelocation timed out (status={}), cluster state:\n{}\n{}", status, client().admin().cluster().prepareState().get().getState().prettyPrint(), client().admin().cluster().preparePendingClusterTasks().get().prettyPrint());
            assertThat("timed out waiting for relocation", actionGet.isTimedOut(), equalTo(false));
        }
        if (status != null) {
            assertThat(actionGet.getStatus(), equalTo(status));
        }
        return actionGet.getStatus();
    }

    /**
     * Waits until at least a give number of document is visible for searchers
     *
     * @param numDocs number of documents to wait for.
     * @return the actual number of docs seen.
     * @throws InterruptedException
     */
    public long waitForDocs(final long numDocs) throws InterruptedException {
        return waitForDocs(numDocs, null);
    }

    /**
     * Waits until at least a give number of document is visible for searchers
     *
     * @param numDocs number of documents to wait for
     * @param indexer a {@link org.elasticsearch.test.BackgroundIndexer}. If supplied it will be first checked for documents indexed.
     *                This saves on unneeded searches.
     * @return the actual number of docs seen.
     * @throws InterruptedException
     */
    public long waitForDocs(final long numDocs, final @Nullable BackgroundIndexer indexer) throws InterruptedException {
        // indexing threads can wait for up to ~1m before retrying when they first try to index into a shard which is not STARTED.
        return waitForDocs(numDocs, 90, TimeUnit.SECONDS, indexer);
    }

    /**
     * Waits until at least a give number of document is visible for searchers
     *
     * @param numDocs         number of documents to wait for
     * @param maxWaitTime     if not progress have been made during this time, fail the test
     * @param maxWaitTimeUnit the unit in which maxWaitTime is specified
     * @param indexer         a {@link org.elasticsearch.test.BackgroundIndexer}. If supplied it will be first checked for documents indexed.
     *                        This saves on unneeded searches.
     * @return the actual number of docs seen.
     * @throws InterruptedException
     */
    public long waitForDocs(final long numDocs, int maxWaitTime, TimeUnit maxWaitTimeUnit, final @Nullable BackgroundIndexer indexer)
            throws InterruptedException {
        final AtomicLong lastKnownCount = new AtomicLong(-1);
        long lastStartCount = -1;
        Predicate<Object> testDocs = new Predicate<Object>() {
            @Override
            public boolean apply(Object o) {
                if (indexer != null) {
                    lastKnownCount.set(indexer.totalIndexedDocs());
                }
                if (lastKnownCount.get() >= numDocs) {
                    try {
                        long count = client().prepareCount().setQuery(matchAllQuery()).execute().actionGet().getCount();
                        if (count == lastKnownCount.get()) {
                            // no progress - try to refresh for the next time
                            client().admin().indices().prepareRefresh().get();
                        }
                        lastKnownCount.set(count);
                    } catch (Throwable e) { // count now acts like search and barfs if all shards failed...
                        logger.debug("failed to executed count", e);
                        return false;
                    }
                    logger.debug("[{}] docs visible for search. waiting for [{}]", lastKnownCount.get(), numDocs);
                } else {
                    logger.debug("[{}] docs indexed. waiting for [{}]", lastKnownCount.get(), numDocs);
                }
                return lastKnownCount.get() >= numDocs;
            }
        };

        while (!awaitBusy(testDocs, maxWaitTime, maxWaitTimeUnit)) {
            if (lastStartCount == lastKnownCount.get()) {
                // we didn't make any progress
                fail("failed to reach " + numDocs + "docs");
            }
            lastStartCount = lastKnownCount.get();
        }
        return lastKnownCount.get();
    }


    /**
     * Sets the cluster's minimum master node and make sure the response is acknowledge.
     * Note: this doesn't guaranty the new settings is in effect, just that it has been received bu all nodes.
     */
    public void setMinimumMasterNodes(int n) {
        assertTrue(client().admin().cluster().prepareUpdateSettings().setTransientSettings(
                settingsBuilder().put(ElectMasterService.DISCOVERY_ZEN_MINIMUM_MASTER_NODES, n))
                .get().isAcknowledged());
    }

    /**
     * Ensures the cluster has a yellow state via the cluster health API.
     */
    public ClusterHealthStatus ensureYellow(String... indices) {
        ClusterHealthResponse actionGet = client().admin().cluster()
                .health(Requests.clusterHealthRequest(indices).waitForRelocatingShards(0).waitForYellowStatus().waitForEvents(Priority.LANGUID)).actionGet();
        if (actionGet.isTimedOut()) {
            logger.info("ensureYellow timed out, cluster state:\n{}\n{}", client().admin().cluster().prepareState().get().getState().prettyPrint(), client().admin().cluster().preparePendingClusterTasks().get().prettyPrint());
            assertThat("timed out waiting for yellow", actionGet.isTimedOut(), equalTo(false));
        }
        logger.debug("indices {} are yellow", indices.length == 0 ? "[_all]" : indices);
        return actionGet.getStatus();
    }

    /**
     * Prints the current cluster state as debug logging.
     */
    public void logClusterState() {
        logger.debug("cluster state:\n{}\n{}", client().admin().cluster().prepareState().get().getState().prettyPrint(), client().admin().cluster().preparePendingClusterTasks().get().prettyPrint());
    }

    /**
     * Prints the segments info for the given indices as debug logging.
     */
    public void logSegmentsState(String... indices) throws Exception {
        IndicesSegmentResponse segsRsp = client().admin().indices().prepareSegments(indices).get();
        logger.debug("segments {} state: \n{}", indices.length == 0 ? "[_all]" : indices,
                segsRsp.toXContent(JsonXContent.contentBuilder().prettyPrint(), ToXContent.EMPTY_PARAMS).string());
    }

    /**
     * Prints current memory stats as info logging.
     */
    public void logMemoryStats() {
        logger.info("memory: {}", XContentHelper.toString(client().admin().cluster().prepareNodesStats().clear().setJvm(true).get()));
    }

    void ensureClusterSizeConsistency() {
        if (cluster() != null) { // if static init fails the cluster can be null
            logger.trace("Check consistency for [{}] nodes", cluster().size());
            assertNoTimeout(client().admin().cluster().prepareHealth().setWaitForNodes(Integer.toString(cluster().size())).get());
        }
    }

    /**
     * Verifies that all nodes that have the same version of the cluster state as master have same cluster state
     */
    protected void ensureClusterStateConsistency() throws IOException {
        if (cluster() != null) {
            boolean getResolvedAddress = InetSocketTransportAddress.getResolveAddress();
            try {
                InetSocketTransportAddress.setResolveAddress(false);
                ClusterState masterClusterState = client().admin().cluster().prepareState().all().get().getState();
                byte[] masterClusterStateBytes = ClusterState.Builder.toBytes(masterClusterState);
                // remove local node reference
                masterClusterState = ClusterState.Builder.fromBytes(masterClusterStateBytes, null);
                Map<String, Object> masterStateMap = convertToMap(masterClusterState);
                int masterClusterStateSize = masterClusterState.toString().length();
                String masterId = masterClusterState.nodes().masterNodeId();
                for (Client client : cluster()) {
                    ClusterState localClusterState = client.admin().cluster().prepareState().all().setLocal(true).get().getState();
                    byte[] localClusterStateBytes = ClusterState.Builder.toBytes(localClusterState);
                    // remove local node reference
                    localClusterState = ClusterState.Builder.fromBytes(localClusterStateBytes, null);
                    final Map<String, Object> localStateMap = convertToMap(localClusterState);
                    final int localClusterStateSize = localClusterState.toString().length();
                    // Check that the non-master node has the same version of the cluster state as the master and that this node didn't disconnect from the master
                    if (masterClusterState.version() == localClusterState.version() && localClusterState.nodes().nodes().containsKey(masterId)) {
                        try {
                            assertEquals("clusterstate UUID does not match", masterClusterState.uuid(), localClusterState.uuid());
                            // We cannot compare serialization bytes since serialization order of maps is not guaranteed
                            // but we can compare serialization sizes - they should be the same
                            assertEquals("clusterstate size does not match", masterClusterStateSize, localClusterStateSize);
                            // Compare JSON serialization
                            assertTrue("clusterstate JSON serialization does not match", mapsEqualIgnoringArrayOrder(masterStateMap, localStateMap));
                        } catch (AssertionError error) {
                            logger.error("Cluster state from master:\n{}\nLocal cluster state:\n{}", masterClusterState.toString(), localClusterState.toString());
                            throw error;
                        }
                    }
                }
            } finally {
                InetSocketTransportAddress.setResolveAddress(getResolvedAddress);
            }
        }

    }

    /**
     * Ensures the cluster is in a searchable state for the given indices. This means a searchable copy of each
     * shard is available on the cluster.
     */
    protected ClusterHealthStatus ensureSearchable(String... indices) {
        // this is just a temporary thing but it's easier to change if it is encapsulated.
        return ensureGreen(indices);
    }

    /**
     * Syntactic sugar for:
     * <pre>
     *   client().prepareIndex(index, type).setSource(source).execute().actionGet();
     * </pre>
     */
    protected final IndexResponse index(String index, String type, XContentBuilder source) {
        return client().prepareIndex(index, type).setSource(source).execute().actionGet();
    }

    /**
     * Syntactic sugar for:
     * <pre>
     *   client().prepareIndex(index, type).setSource(source).execute().actionGet();
     * </pre>
     */
    protected final IndexResponse index(String index, String type, String id, Map<String, Object> source) {
        return client().prepareIndex(index, type, id).setSource(source).execute().actionGet();
    }

    /**
     * Syntactic sugar for:
     * <pre>
     *   client().prepareGet(index, type, id).execute().actionGet();
     * </pre>
     */
    protected final GetResponse get(String index, String type, String id) {
        return client().prepareGet(index, type, id).execute().actionGet();
    }

    /**
     * Syntactic sugar for:
     * <pre>
     *   return client().prepareIndex(index, type, id).setSource(source).execute().actionGet();
     * </pre>
     */
    protected final IndexResponse index(String index, String type, String id, XContentBuilder source) {
        return client().prepareIndex(index, type, id).setSource(source).execute().actionGet();
    }

    /**
     * Syntactic sugar for:
     * <pre>
     *   return client().prepareIndex(index, type, id).setSource(source).execute().actionGet();
     * </pre>
     */
    protected final IndexResponse index(String index, String type, String id, Object... source) {
        return client().prepareIndex(index, type, id).setSource(source).execute().actionGet();
    }

    /**
     * Syntactic sugar for:
     * <p/>
     * <pre>
     *   return client().prepareIndex(index, type, id).setSource(source).execute().actionGet();
     * </pre>
     * <p/>
     * where source is a String.
     */
    protected final IndexResponse index(String index, String type, String id, String source) {
        return client().prepareIndex(index, type, id).setSource(source).execute().actionGet();
    }

    /**
     * Waits for relocations and refreshes all indices in the cluster.
     *
     * @see #waitForRelocation()
     */
    protected final RefreshResponse refresh() {
        waitForRelocation();
        // TODO RANDOMIZE with flush?
        RefreshResponse actionGet = client().admin().indices().prepareRefresh().execute().actionGet();
        assertNoFailures(actionGet);
        return actionGet;
    }

    /**
     * Flushes and refreshes all indices in the cluster
     */
    protected final void flushAndRefresh(String... indices) {
        flush(indices);
        refresh();
    }

    /**
     * Flush some or all indices in the cluster.
     */
    protected final FlushResponse flush(String... indices) {
        waitForRelocation();
        FlushResponse actionGet = client().admin().indices().prepareFlush(indices).setWaitIfOngoing(true).execute().actionGet();
        for (ShardOperationFailedException failure : actionGet.getShardFailures()) {
            assertThat("unexpected flush failure " + failure.reason(), failure.status(), equalTo(RestStatus.SERVICE_UNAVAILABLE));
        }
        return actionGet;
    }

    /**
     * Waits for all relocations and optimized all indices in the cluster to 1 segment.
     */
    protected OptimizeResponse optimize() {
        waitForRelocation();
        OptimizeResponse actionGet = client().admin().indices().prepareOptimize().setMaxNumSegments(1).execute().actionGet();
        assertNoFailures(actionGet);
        return actionGet;
    }

    /**
     * Returns <code>true</code> iff the given index exists otherwise <code>false</code>
     */
    protected boolean indexExists(String index) {
        IndicesExistsResponse actionGet = client().admin().indices().prepareExists(index).execute().actionGet();
        return actionGet.isExists();
    }

    /**
     * Returns a random admin client. This client can either be a node or a transport client pointing to any of
     * the nodes in the cluster.
     */
    protected AdminClient admin() {
        return client().admin();
    }

    /**
     * Convenience method that forwards to {@link #indexRandom(boolean, List)}.
     */
    public void indexRandom(boolean forceRefresh, IndexRequestBuilder... builders) throws InterruptedException, ExecutionException {
        indexRandom(forceRefresh, Arrays.asList(builders));
    }

    public void indexRandom(boolean forceRefresh, boolean dummyDocuments, IndexRequestBuilder... builders) throws InterruptedException, ExecutionException {
        indexRandom(forceRefresh, dummyDocuments, Arrays.asList(builders));
    }


    private static final String RANDOM_BOGUS_TYPE = "RANDOM_BOGUS_TYPE______";

    /**
     * Indexes the given {@link IndexRequestBuilder} instances randomly. It shuffles the given builders and either
     * indexes them in a blocking or async fashion. This is very useful to catch problems that relate to internal document
     * ids or index segment creations. Some features might have bug when a given document is the first or the last in a
     * segment or if only one document is in a segment etc. This method prevents issues like this by randomizing the index
     * layout.
     *
     * @param forceRefresh if <tt>true</tt> all involved indices are refreshed once the documents are indexed. Additionally if <tt>true</tt>
     *                     some empty dummy documents are may be randomly inserted into the document list and deleted once all documents are indexed.
     *                     This is useful to produce deleted documents on the server side.
     * @param builders     the documents to index.
     * @see #indexRandom(boolean, boolean, java.util.List)
     */
    public void indexRandom(boolean forceRefresh, List<IndexRequestBuilder> builders) throws InterruptedException, ExecutionException {
        indexRandom(forceRefresh, forceRefresh, builders);
    }

    /**
     * Indexes the given {@link IndexRequestBuilder} instances randomly. It shuffles the given builders and either
     * indexes they in a blocking or async fashion. This is very useful to catch problems that relate to internal document
     * ids or index segment creations. Some features might have bug when a given document is the first or the last in a
     * segment or if only one document is in a segment etc. This method prevents issues like this by randomizing the index
     * layout.
     *
     * @param forceRefresh   if <tt>true</tt> all involved indices are refreshed once the documents are indexed.
     * @param dummyDocuments if <tt>true</tt> some empty dummy documents may be randomly inserted into the document list and deleted once
     *                       all documents are indexed. This is useful to produce deleted documents on the server side.
     * @param builders       the documents to index.
     */
    public void indexRandom(boolean forceRefresh, boolean dummyDocuments, List<IndexRequestBuilder> builders) throws InterruptedException, ExecutionException {
        indexRandom(forceRefresh, dummyDocuments, true, builders);
    }

    /**
     * Indexes the given {@link IndexRequestBuilder} instances randomly. It shuffles the given builders and either
     * indexes they in a blocking or async fashion. This is very useful to catch problems that relate to internal document
     * ids or index segment creations. Some features might have bug when a given document is the first or the last in a
     * segment or if only one document is in a segment etc. This method prevents issues like this by randomizing the index
     * layout.
     *
     * @param forceRefresh   if <tt>true</tt> all involved indices are refreshed once the documents are indexed.
     * @param dummyDocuments if <tt>true</tt> some empty dummy documents may be randomly inserted into the document list and deleted once
     *                       all documents are indexed. This is useful to produce deleted documents on the server side.
     * @param maybeFlush     if <tt>true</tt> this method may randomly execute full flushes after index operations.
     * @param builders       the documents to index.
     */
    public void indexRandom(boolean forceRefresh, boolean dummyDocuments, boolean maybeFlush, List<IndexRequestBuilder> builders) throws InterruptedException, ExecutionException {

        Random random = getRandom();
        Set<String> indicesSet = new HashSet<>();
        for (IndexRequestBuilder builder : builders) {
            indicesSet.add(builder.request().index());
        }
        Set<Tuple<String, String>> bogusIds = new HashSet<>();
        if (random.nextBoolean() && !builders.isEmpty() && dummyDocuments) {
            builders = new ArrayList<>(builders);
            final String[] indices = indicesSet.toArray(new String[indicesSet.size()]);
            // inject some bogus docs
            final int numBogusDocs = scaledRandomIntBetween(1, builders.size() * 2);
            final int unicodeLen = between(1, 10);
            for (int i = 0; i < numBogusDocs; i++) {
                String id = randomRealisticUnicodeOfLength(unicodeLen) + Integer.toString(dummmyDocIdGenerator.incrementAndGet());
                String index = RandomPicks.randomFrom(random, indices);
                bogusIds.add(new Tuple<>(index, id));
                builders.add(client().prepareIndex(index, RANDOM_BOGUS_TYPE, id).setSource("{}"));
            }
        }
        final String[] indices = indicesSet.toArray(new String[indicesSet.size()]);
        Collections.shuffle(builders, random);
        final CopyOnWriteArrayList<Tuple<IndexRequestBuilder, Throwable>> errors = new CopyOnWriteArrayList<>();
        List<CountDownLatch> inFlightAsyncOperations = new ArrayList<>();
        // If you are indexing just a few documents then frequently do it one at a time.  If many then frequently in bulk.
        if (builders.size() < FREQUENT_BULK_THRESHOLD ? frequently() : builders.size() < ALWAYS_BULK_THRESHOLD ? rarely() : false) {
            if (frequently()) {
                logger.info("Index [{}] docs async: [{}] bulk: [{}]", builders.size(), true, false);
                for (IndexRequestBuilder indexRequestBuilder : builders) {
                    indexRequestBuilder.execute(new PayloadLatchedActionListener<IndexResponse, IndexRequestBuilder>(indexRequestBuilder, newLatch(inFlightAsyncOperations), errors));
                    postIndexAsyncActions(indices, inFlightAsyncOperations, maybeFlush);
                }
            } else {
                logger.info("Index [{}] docs async: [{}] bulk: [{}]", builders.size(), false, false);
                for (IndexRequestBuilder indexRequestBuilder : builders) {
                    indexRequestBuilder.execute().actionGet();
                    postIndexAsyncActions(indices, inFlightAsyncOperations, maybeFlush);
                }
            }
        } else {
            List<List<IndexRequestBuilder>> partition = Lists.partition(builders, Math.min(MAX_BULK_INDEX_REQUEST_SIZE,
                    Math.max(1, (int) (builders.size() * randomDouble()))));
            logger.info("Index [{}] docs async: [{}] bulk: [{}] partitions [{}]", builders.size(), false, true, partition.size());
            for (List<IndexRequestBuilder> segmented : partition) {
                BulkRequestBuilder bulkBuilder = client().prepareBulk();
                for (IndexRequestBuilder indexRequestBuilder : segmented) {
                    bulkBuilder.add(indexRequestBuilder);
                }
                BulkResponse actionGet = bulkBuilder.execute().actionGet();
                assertThat(actionGet.hasFailures() ? actionGet.buildFailureMessage() : "", actionGet.hasFailures(), equalTo(false));
            }
        }
        for (CountDownLatch operation : inFlightAsyncOperations) {
            operation.await();
        }
        final List<Throwable> actualErrors = new ArrayList<>();
        for (Tuple<IndexRequestBuilder, Throwable> tuple : errors) {
            if (ExceptionsHelper.unwrapCause(tuple.v2()) instanceof EsRejectedExecutionException) {
                tuple.v1().execute().actionGet(); // re-index if rejected
            } else {
                actualErrors.add(tuple.v2());
            }
        }
        assertThat(actualErrors, emptyIterable());
        if (!bogusIds.isEmpty()) {
            // delete the bogus types again - it might trigger merges or at least holes in the segments and enforces deleted docs!
            for (Tuple<String, String> doc : bogusIds) {
                // see https://github.com/elasticsearch/elasticsearch/issues/8706
                final DeleteResponse deleteResponse = client().prepareDelete(doc.v1(), RANDOM_BOGUS_TYPE, doc.v2()).get();
                if (deleteResponse.isFound() == false) {
                    logger.warn("failed to delete a dummy doc [{}][{}]", doc.v1(), doc.v2());
                }
            }
        }
        if (forceRefresh) {
            assertNoFailures(client().admin().indices().prepareRefresh(indices).setIndicesOptions(IndicesOptions.lenientExpandOpen()).execute().get());
        }
    }

    private AtomicInteger dummmyDocIdGenerator = new AtomicInteger();

    /** Disables translog flushing for the specified index */
    public static void disableTranslogFlush(String index) {
        Settings settings = Settings.builder().put(TranslogService.INDEX_TRANSLOG_DISABLE_FLUSH, true).build();
        client().admin().indices().prepareUpdateSettings(index).setSettings(settings).get();
    }

    /** Enables translog flushing for the specified index */
    public static void enableTranslogFlush(String index) {
        Settings settings = Settings.builder().put(TranslogService.INDEX_TRANSLOG_DISABLE_FLUSH, false).build();
        client().admin().indices().prepareUpdateSettings(index).setSettings(settings).get();
    }

    /** Disables an index block for the specified index */
    public static void disableIndexBlock(String index, String block) {
        Settings settings = Settings.builder().put(block, false).build();
        client().admin().indices().prepareUpdateSettings(index).setSettings(settings).get();
    }

    /** Enables an index block for the specified index */
    public static void enableIndexBlock(String index, String block) {
        Settings settings = Settings.builder().put(block, true).build();
        client().admin().indices().prepareUpdateSettings(index).setSettings(settings).get();
    }

    /** Sets or unsets the cluster read_only mode **/
    public static void setClusterReadOnly(boolean value) {
        Settings settings = settingsBuilder().put(MetaData.SETTING_READ_ONLY, value).build();
        assertAcked(client().admin().cluster().prepareUpdateSettings().setTransientSettings(settings).get());
    }

    private static CountDownLatch newLatch(List<CountDownLatch> latches) {
        CountDownLatch l = new CountDownLatch(1);
        latches.add(l);
        return l;
    }

    /**
     * Maybe refresh, optimize, or flush then always make sure there aren't too many in flight async operations.
     */
    private void postIndexAsyncActions(String[] indices, List<CountDownLatch> inFlightAsyncOperations, boolean maybeFlush) throws InterruptedException {
        if (rarely()) {
            if (rarely()) {
                client().admin().indices().prepareRefresh(indices).setIndicesOptions(IndicesOptions.lenientExpandOpen()).execute(
                        new LatchedActionListener<RefreshResponse>(newLatch(inFlightAsyncOperations)));
            } else if (maybeFlush && rarely()) {
                if (randomBoolean()) {
                    client().admin().indices().prepareFlush(indices).setIndicesOptions(IndicesOptions.lenientExpandOpen()).execute(
                            new LatchedActionListener<FlushResponse>(newLatch(inFlightAsyncOperations)));
                } else {
                    internalCluster().getInstance(SyncedFlushService.class).attemptSyncedFlush(indices, IndicesOptions.lenientExpandOpen(),
                            new LatchedActionListener<IndicesSyncedFlushResult>(newLatch(inFlightAsyncOperations)));
                }
            } else if (rarely()) {
                client().admin().indices().prepareOptimize(indices).setIndicesOptions(IndicesOptions.lenientExpandOpen()).setMaxNumSegments(between(1, 10)).setFlush(maybeFlush && randomBoolean()).execute(
                        new LatchedActionListener<OptimizeResponse>(newLatch(inFlightAsyncOperations)));
            }
        }
        while (inFlightAsyncOperations.size() > MAX_IN_FLIGHT_ASYNC_INDEXES) {
            int waitFor = between(0, inFlightAsyncOperations.size() - 1);
            inFlightAsyncOperations.remove(waitFor).await();
        }
    }

    /**
     * The scope of a test cluster used together with
     * {@link org.elasticsearch.test.ElasticsearchIntegrationTest.ClusterScope} annotations on {@link org.elasticsearch.test.ElasticsearchIntegrationTest} subclasses.
     */
    public enum Scope {
        /**
         * A cluster shared across all method in a single test suite
         */
        SUITE,
        /**
         * A test exclusive test cluster
         */
        TEST
    }

    /**
     * Defines a cluster scope for a {@link org.elasticsearch.test.ElasticsearchIntegrationTest} subclass.
     * By default if no {@link ClusterScope} annotation is present {@link org.elasticsearch.test.ElasticsearchIntegrationTest.Scope#SUITE} is used
     * together with randomly chosen settings like number of nodes etc.
     */
    @Retention(RetentionPolicy.RUNTIME)
    @Target({ElementType.TYPE})
    public @interface ClusterScope {
        /**
         * Returns the scope. {@link org.elasticsearch.test.ElasticsearchIntegrationTest.Scope#SUITE} is default.
         */
        Scope scope() default Scope.SUITE;

        /**
         * Returns the number of nodes in the cluster. Default is <tt>-1</tt> which means
         * a random number of nodes is used, where the minimum and maximum number of nodes
         * are either the specified ones or the default ones if not specified.
         */
        int numDataNodes() default -1;

        /**
         * Returns the minimum number of nodes in the cluster. Default is <tt>-1</tt>.
         * Ignored when {@link ClusterScope#numDataNodes()} is set.
         */
        int minNumDataNodes() default -1;

        /**
         * Returns the maximum number of nodes in the cluster.  Default is <tt>-1</tt>.
         * Ignored when {@link ClusterScope#numDataNodes()} is set.
         */
        int maxNumDataNodes() default -1;

        /**
         * Returns the number of client nodes in the cluster. Default is {@link InternalTestCluster#DEFAULT_NUM_CLIENT_NODES}, a
         * negative value means that the number of client nodes will be randomized.
         */
        int numClientNodes() default InternalTestCluster.DEFAULT_NUM_CLIENT_NODES;

        /**
         * Returns the transport client ratio. By default this returns <code>-1</code> which means a random
         * ratio in the interval <code>[0..1]</code> is used.
         */
        double transportClientRatio() default -1;

        /**
         * Return whether or not to enable dynamic templates for the mappings.
         */
        boolean randomDynamicTemplates() default true;
    }

    private class LatchedActionListener<Response> implements ActionListener<Response> {
        private final CountDownLatch latch;

        public LatchedActionListener(CountDownLatch latch) {
            this.latch = latch;
        }

        @Override
        public final void onResponse(Response response) {
            latch.countDown();
        }

        @Override
        public final void onFailure(Throwable t) {
            try {
                logger.info("Action Failed", t);
                addError(t);
            } finally {
                latch.countDown();
            }
        }

        protected void addError(Throwable t) {
        }

    }

    private class PayloadLatchedActionListener<Response, T> extends LatchedActionListener<Response> {
        private final CopyOnWriteArrayList<Tuple<T, Throwable>> errors;
        private final T builder;

        public PayloadLatchedActionListener(T builder, CountDownLatch latch, CopyOnWriteArrayList<Tuple<T, Throwable>> errors) {
            super(latch);
            this.errors = errors;
            this.builder = builder;
        }

        @Override
        protected void addError(Throwable t) {
            errors.add(new Tuple<>(builder, t));
        }

    }

    /**
     * Clears the given scroll Ids
     */
    public void clearScroll(String... scrollIds) {
        ClearScrollResponse clearResponse = client().prepareClearScroll()
                .setScrollIds(Arrays.asList(scrollIds)).get();
        assertThat(clearResponse.isSucceeded(), equalTo(true));
    }

    private static ClusterScope getAnnotation(Class<?> clazz) {
        if (clazz == Object.class || clazz == ElasticsearchIntegrationTest.class) {
            return null;
        }
        ClusterScope annotation = clazz.getAnnotation(ClusterScope.class);
        if (annotation != null) {
            return annotation;
        }
        return getAnnotation(clazz.getSuperclass());
    }

    private Scope getCurrentClusterScope() {
        return getCurrentClusterScope(this.getClass());
    }

    private static Scope getCurrentClusterScope(Class<?> clazz) {
        ClusterScope annotation = getAnnotation(clazz);
        // if we are not annotated assume suite!
        return annotation == null ? Scope.SUITE : annotation.scope();
    }

    private int getNumDataNodes() {
        ClusterScope annotation = getAnnotation(this.getClass());
        return annotation == null ? -1 : annotation.numDataNodes();
    }

    private int getMinNumDataNodes() {
        ClusterScope annotation = getAnnotation(this.getClass());
        return annotation == null || annotation.minNumDataNodes() == -1 ? InternalTestCluster.DEFAULT_MIN_NUM_DATA_NODES : annotation.minNumDataNodes();
    }

    private int getMaxNumDataNodes() {
        ClusterScope annotation = getAnnotation(this.getClass());
        return annotation == null || annotation.maxNumDataNodes() == -1 ? InternalTestCluster.DEFAULT_MAX_NUM_DATA_NODES : annotation.maxNumDataNodes();
    }

    private int getNumClientNodes() {
        ClusterScope annotation = getAnnotation(this.getClass());
        return annotation == null ? InternalTestCluster.DEFAULT_NUM_CLIENT_NODES : annotation.numClientNodes();
    }

    private boolean randomDynamicTemplates() {
        ClusterScope annotation = getAnnotation(this.getClass());
        return annotation == null || annotation.randomDynamicTemplates();
    }

    /**
     * This method is used to obtain settings for the <tt>Nth</tt> node in the cluster.
     * Nodes in this cluster are associated with an ordinal number such that nodes can
     * be started with specific configurations. This method might be called multiple
     * times with the same ordinal and is expected to return the same value for each invocation.
     * In other words subclasses must ensure this method is idempotent.
     */
    protected Settings nodeSettings(int nodeOrdinal) {
        return settingsBuilder()
                // Default the watermarks to absurdly low to prevent the tests
                // from failing on nodes without enough disk space
                .put(DiskThresholdDecider.CLUSTER_ROUTING_ALLOCATION_LOW_DISK_WATERMARK, "1b")
                .put(DiskThresholdDecider.CLUSTER_ROUTING_ALLOCATION_HIGH_DISK_WATERMARK, "1b")
                .put("script.indexed", "on")
                .put("script.inline", "on")
                        // wait short time for other active shards before actually deleting, default 30s not needed in tests
                .put(IndicesStore.INDICES_STORE_DELETE_SHARD_TIMEOUT, new TimeValue(1, TimeUnit.SECONDS))
                .build();
    }

    /**
     * This method is used to obtain additional settings for clients created by the internal cluster.
     * These settings will be applied on the client in addition to some randomized settings defined in
     * the cluster. These setttings will also override any other settings the internal cluster might
     * add by default.
     */
    protected Settings transportClientSettings() {
        return Settings.EMPTY;
    }

    private ExternalTestCluster buildExternalCluster(String clusterAddresses) {
        String[] stringAddresses = clusterAddresses.split(",");
        TransportAddress[] transportAddresses = new TransportAddress[stringAddresses.length];
        int i = 0;
        for (String stringAddress : stringAddresses) {
            String[] split = stringAddress.split(":");
            if (split.length < 2) {
                throw new IllegalArgumentException("address [" + clusterAddresses + "] not valid");
            }
            try {
                transportAddresses[i++] = new InetSocketTransportAddress(split[0], Integer.valueOf(split[1]));
            } catch (NumberFormatException e) {
                throw new IllegalArgumentException("port is not valid, expected number but was [" + split[1] + "]");
            }
        }
        return new ExternalTestCluster(transportAddresses);
    }

    protected TestCluster buildTestCluster(Scope scope, long seed) throws IOException {
        String clusterAddresses = System.getProperty(TESTS_CLUSTER);
        if (Strings.hasLength(clusterAddresses)) {
            if (scope == Scope.TEST) {
                throw new IllegalArgumentException("Cannot run TEST scope test with " + TESTS_CLUSTER);
            }
            return buildExternalCluster(clusterAddresses);
        }

        final String nodePrefix;
        switch (scope) {
            case TEST:
                nodePrefix = TEST_CLUSTER_NODE_PREFIX;
                break;
            case SUITE:
                nodePrefix = SUITE_CLUSTER_NODE_PREFIX;
                break;
            default:
                throw new ElasticsearchException("Scope not supported: " + scope);
        }
        SettingsSource settingsSource = new SettingsSource() {
            @Override
            public Settings node(int nodeOrdinal) {
                return Settings.builder().put(Node.HTTP_ENABLED, false).
                        put(nodeSettings(nodeOrdinal)).build();
            }

            @Override
            public Settings transportClient() {
                return transportClientSettings();
            }
        };

        int numDataNodes = getNumDataNodes();
        int minNumDataNodes;
        int maxNumDataNodes;
        if (numDataNodes >= 0) {
            minNumDataNodes = maxNumDataNodes = numDataNodes;
        } else {
            minNumDataNodes = getMinNumDataNodes();
            maxNumDataNodes = getMaxNumDataNodes();
        }
        return new InternalTestCluster(seed, createTempDir(), minNumDataNodes, maxNumDataNodes,
                InternalTestCluster.clusterName(scope.name(), seed) + "-cluster", settingsSource, getNumClientNodes(),
                InternalTestCluster.DEFAULT_ENABLE_HTTP_PIPELINING, nodePrefix);
    }

    /**
     * Returns the client ratio configured via
     */
    private static double transportClientRatio() {
        String property = System.getProperty(TESTS_CLIENT_RATIO);
        if (property == null || property.isEmpty()) {
            return Double.NaN;
        }
        return Double.parseDouble(property);
    }

    /**
     * Returns the transport client ratio from the class level annotation or via
     * {@link System#getProperty(String)} if available. If both are not available this will
     * return a random ratio in the interval <tt>[0..1]</tt>
     */
    protected double getPerTestTransportClientRatio() {
        final ClusterScope annotation = getAnnotation(this.getClass());
        double perTestRatio = -1;
        if (annotation != null) {
            perTestRatio = annotation.transportClientRatio();
        }
        if (perTestRatio == -1) {
            return Double.isNaN(TRANSPORT_CLIENT_RATIO) ? randomDouble() : TRANSPORT_CLIENT_RATIO;
        }
        assert perTestRatio >= 0.0 && perTestRatio <= 1.0;
        return perTestRatio;
    }

    /**
     * Returns a random numeric field data format from the choices of "array" or "doc_values".
     */
    public static String randomNumericFieldDataFormat() {
        return randomFrom(Arrays.asList("array", "doc_values"));
    }

    /**
     * Returns a random bytes field data format from the choices of
     * "paged_bytes", "fst", or "doc_values".
     */
    public static String randomBytesFieldDataFormat() {
        return randomFrom(Arrays.asList("paged_bytes", "fst"));
    }

    /**
     * Returns a random JODA Time Zone based on Java Time Zones
     */
    public static DateTimeZone randomDateTimeZone() {
        DateTimeZone timeZone;

        // It sounds like some Java Time Zones are unknown by JODA. For example: Asia/Riyadh88
        // We need to fallback in that case to a known time zone
        try {
            timeZone = DateTimeZone.forTimeZone(RandomizedTest.randomTimeZone());
        } catch (IllegalArgumentException e) {
            timeZone = DateTimeZone.forOffsetHours(randomIntBetween(-12, 12));
        }

        return timeZone;
    }

    /**
     * Returns path to a random directory that can be used to create a temporary file system repo
     */
    public Path randomRepoPath() {
        if (currentCluster instanceof InternalTestCluster) {
            return randomRepoPath(((InternalTestCluster) currentCluster).getDefaultSettings());
        } else if (currentCluster instanceof CompositeTestCluster) {
            return randomRepoPath(((CompositeTestCluster) currentCluster).internalCluster().getDefaultSettings());
        }
        throw new UnsupportedOperationException("unsupported cluster type");
    }

    /**
     * Returns path to a random directory that can be used to create a temporary file system repo
     */
    public static Path randomRepoPath(Settings settings) {
        Environment environment = new Environment(settings);
        Path[] repoFiles = environment.repoFiles();
        assert repoFiles.length > 0;
        Path path;
        do {
            path = repoFiles[0].resolve(randomAsciiOfLength(10));
        } while (Files.exists(path));
        return path;
    }

    protected NumShards getNumShards(String index) {
        MetaData metaData = client().admin().cluster().prepareState().get().getState().metaData();
        assertThat(metaData.hasIndex(index), equalTo(true));
        int numShards = Integer.valueOf(metaData.index(index).settings().get(SETTING_NUMBER_OF_SHARDS));
        int numReplicas = Integer.valueOf(metaData.index(index).settings().get(SETTING_NUMBER_OF_REPLICAS));
        return new NumShards(numShards, numReplicas);
    }

    /**
     * Asserts that all shards are allocated on nodes matching the given node pattern.
     */
    public Set<String> assertAllShardsOnNodes(String index, String... pattern) {
        Set<String> nodes = new HashSet<>();
        ClusterState clusterState = client().admin().cluster().prepareState().execute().actionGet().getState();
        for (IndexRoutingTable indexRoutingTable : clusterState.routingTable()) {
            for (IndexShardRoutingTable indexShardRoutingTable : indexRoutingTable) {
                for (ShardRouting shardRouting : indexShardRoutingTable) {
                    if (shardRouting.currentNodeId() != null && index.equals(shardRouting.getIndex())) {
                        String name = clusterState.nodes().get(shardRouting.currentNodeId()).name();
                        nodes.add(name);
                        assertThat("Allocated on new node: " + name, Regex.simpleMatch(pattern, name), is(true));
                    }
                }
            }
        }
        return nodes;
    }

    /**
     * Asserts that there are no files in the specified path
     */
    public void assertPathHasBeenCleared(String path) throws Exception {
        assertPathHasBeenCleared(PathUtils.get(path));
    }

    /**
     * Asserts that there are no files in the specified path
     */
    public void assertPathHasBeenCleared(Path path) throws Exception {
        logger.info("--> checking that [{}] has been cleared", path);
        int count = 0;
        StringBuilder sb = new StringBuilder();
        sb.append("[");
        if (Files.exists(path)) {
            try (DirectoryStream<Path> stream = Files.newDirectoryStream(path)) {
                for (Path file : stream) {
                    logger.info("--> found file: [{}]", file.toAbsolutePath().toString());
                    if (Files.isDirectory(file)) {
                        assertPathHasBeenCleared(file);
                    } else if (Files.isRegularFile(file)) {
                        count++;
                        sb.append(file.toAbsolutePath().toString());
                        sb.append("\n");
                    }
                }
            }
        }
        sb.append("]");
        assertThat(count + " files exist that should have been cleaned:\n" + sb.toString(), count, equalTo(0));
    }

    protected static class NumShards {
        public final int numPrimaries;
        public final int numReplicas;
        public final int totalNumShards;
        public final int dataCopies;

        private NumShards(int numPrimaries, int numReplicas) {
            this.numPrimaries = numPrimaries;
            this.numReplicas = numReplicas;
            this.dataCopies = numReplicas + 1;
            this.totalNumShards = numPrimaries * dataCopies;
        }
    }

    private static boolean runTestScopeLifecycle() {
        return INSTANCE == null;
    }


    @Before
    public final void before() throws Exception {
        if (runTestScopeLifecycle()) {
            beforeInternal();
        }
    }


    @After
    public final void after() throws Exception {
        // Deleting indices is going to clear search contexts implicitely so we
        // need to check that there are no more in-flight search contexts before
        // we remove indices
        super.ensureAllSearchContextsReleased();
        if (runTestScopeLifecycle()) {
            afterInternal(false);
        }
    }

    @AfterClass
    public static void afterClass() throws Exception {
        if (!runTestScopeLifecycle()) {
            try {
                INSTANCE.afterInternal(true);
            } finally {
                INSTANCE = null;
            }
        } else {
            clearClusters();
        }
        SUITE_SEED = null;
        currentCluster = null;
    }

    private static void initializeSuiteScope() throws Exception {
        Class<?> targetClass = getTestClass();
        /**
         * Note we create these test class instance via reflection
         * since JUnit creates a new instance per test and that is also
         * the reason why INSTANCE is static since this entire method
         * must be executed in a static context.
         */
        assert INSTANCE == null;
        if (isSuiteScopedTest(targetClass)) {
            // note we need to do this this way to make sure this is reproducible
            INSTANCE = (ElasticsearchIntegrationTest) targetClass.newInstance();
            boolean success = false;
            try {
                INSTANCE.beforeInternal();
                INSTANCE.setupSuiteScopeCluster();
                success = true;
            } finally {
                if (!success) {
                    afterClass();
                }
            }
        } else {
            INSTANCE = null;
        }
    }

    /**
     * Compute a routing key that will route documents to the <code>shard</code>-th shard
     * of the provided index.
     */
    protected String routingKeyForShard(String index, String type, int shard) {
        return internalCluster().routingKeyForShard(index, type, shard, getRandom());
    }

    /**
     * Return settings that could be used to start a node that has the given zipped home directory.
     */
    protected Settings prepareBackwardsDataDir(Path backwardsIndex, Object... settings) throws IOException {
        Path indexDir = createTempDir();
        Path dataDir = indexDir.resolve("data");
        try (InputStream stream = Files.newInputStream(backwardsIndex)) {
            TestUtil.unzip(stream, indexDir);
        }
        assertTrue(Files.exists(dataDir));

        // list clusters in the datapath, ignoring anything from extrasfs
        final Path[] list;
        try (DirectoryStream<Path> stream = Files.newDirectoryStream(dataDir)) {
            List<Path> dirs = new ArrayList<>();
            for (Path p : stream) {
                if (!p.getFileName().toString().startsWith("extra")) {
                    dirs.add(p);
                }
            }
            list = dirs.toArray(new Path[0]);
        }

        if (list.length != 1) {
            throw new IllegalStateException("Backwards index must contain exactly one cluster\n" + StringUtils.join(list, "\n"));
        }
        Path src = list[0];
        Path dest = dataDir.resolve(internalCluster().getClusterName());
        assertTrue(Files.exists(src));
        Files.move(src, dest);
        assertFalse(Files.exists(src));
        assertTrue(Files.exists(dest));
        Settings.Builder builder = Settings.builder()
                .put(settings)
                .put("path.data", dataDir.toAbsolutePath());

        Path configDir = indexDir.resolve("config");
        if (Files.exists(configDir)) {
            builder.put("path.conf", configDir.toAbsolutePath());
        }
        return builder.build();
    }

    protected HttpRequestBuilder httpClient() {
        final NodesInfoResponse nodeInfos = client().admin().cluster().prepareNodesInfo().get();
        final NodeInfo[] nodes = nodeInfos.getNodes();
        assertTrue(nodes.length > 0);
        TransportAddress publishAddress = randomFrom(nodes).getHttp().address().publishAddress();
        assertEquals(1, publishAddress.uniqueAddressTypeId());
        InetSocketAddress address = ((InetSocketTransportAddress) publishAddress).address();
        return new HttpRequestBuilder(HttpClients.createDefault()).host(address.getHostName()).port(address.getPort());
    }

    /**
     * This method is executed iff the test is annotated with {@link SuiteScopeTest}
     * before the first test of this class is executed.
     *
     * @see SuiteScopeTest
     */
    protected void setupSuiteScopeCluster() throws Exception {
    }

    private static boolean isSuiteScopedTest(Class<?> clazz) {
        return clazz.getAnnotation(SuiteScopeTest.class) != null;
    }

    /**
     * If a test is annotated with {@link org.elasticsearch.test.ElasticsearchIntegrationTest.SuiteScopeTest}
     * the checks and modifications that are applied to the used test cluster are only done after all tests
     * of this class are executed. This also has the side-effect of a suite level setup method {@link #setupSuiteScopeCluster()}
     * that is executed in a separate test instance. Variables that need to be accessible across test instances must be static.
     */
    @Retention(RetentionPolicy.RUNTIME)
    @Inherited
    @Ignore
    public @interface SuiteScopeTest {
    }
}


File: core/src/test/java/org/elasticsearch/test/index/merge/NoMergePolicyProvider.java
/*
 * Licensed to Elasticsearch under one or more contributor
 * license agreements. See the NOTICE file distributed with
 * this work for additional information regarding copyright
 * ownership. Elasticsearch licenses this file to you under
 * the Apache License, Version 2.0 (the "License"); you may
 * not use this file except in compliance with the License.
 * You may obtain a copy of the License at
 *
 *    http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing,
 * software distributed under the License is distributed on an
 * "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY
 * KIND, either express or implied.  See the License for the
 * specific language governing permissions and limitations
 * under the License.
 */
package org.elasticsearch.test.index.merge;

import org.apache.lucene.index.MergePolicy;
import org.apache.lucene.index.NoMergePolicy;
import org.elasticsearch.ElasticsearchException;
import org.elasticsearch.common.inject.Inject;
import org.elasticsearch.index.merge.policy.AbstractMergePolicyProvider;
import org.elasticsearch.index.store.Store;

/**
 * {@link org.elasticsearch.index.merge.policy.MergePolicyProvider} for lucenes {@link org.apache.lucene.index.NoMergePolicy}
 */
public class NoMergePolicyProvider extends AbstractMergePolicyProvider<MergePolicy> {

    @Inject
    public NoMergePolicyProvider(Store store) {
        super(store);
    }

    @Override
    public MergePolicy getMergePolicy() {
        return NoMergePolicy.INSTANCE;
    }

    @Override
    public void close() {}
}



File: core/src/test/java/org/elasticsearch/update/UpdateTests.java
/*
 * Licensed to Elasticsearch under one or more contributor
 * license agreements. See the NOTICE file distributed with
 * this work for additional information regarding copyright
 * ownership. Elasticsearch licenses this file to you under
 * the Apache License, Version 2.0 (the "License"); you may
 * not use this file except in compliance with the License.
 * You may obtain a copy of the License at
 *
 *    http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing,
 * software distributed under the License is distributed on an
 * "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY
 * KIND, either express or implied.  See the License for the
 * specific language governing permissions and limitations
 * under the License.
 */

package org.elasticsearch.update;

import org.elasticsearch.ElasticsearchTimeoutException;
import org.elasticsearch.action.ActionListener;
import org.elasticsearch.action.ActionRequestValidationException;
import org.elasticsearch.action.admin.indices.alias.Alias;
import org.elasticsearch.action.delete.DeleteRequest;
import org.elasticsearch.action.delete.DeleteResponse;
import org.elasticsearch.action.get.GetResponse;
import org.elasticsearch.action.update.UpdateRequest;
import org.elasticsearch.action.update.UpdateRequestBuilder;
import org.elasticsearch.action.update.UpdateResponse;
import org.elasticsearch.client.transport.NoNodeAvailableException;
import org.elasticsearch.common.settings.Settings;
import org.elasticsearch.common.unit.TimeValue;
import org.elasticsearch.common.xcontent.XContentFactory;
import org.elasticsearch.index.VersionType;
import org.elasticsearch.index.engine.DocumentMissingException;
import org.elasticsearch.index.engine.VersionConflictEngineException;
import org.elasticsearch.index.merge.policy.MergePolicyModule;
import org.elasticsearch.script.Script;
import org.elasticsearch.script.ScriptService;
import org.elasticsearch.test.ElasticsearchIntegrationTest;
import org.elasticsearch.test.index.merge.NoMergePolicyProvider;
import org.junit.Test;

import java.util.ArrayList;
import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.concurrent.CopyOnWriteArrayList;
import java.util.concurrent.CountDownLatch;
import java.util.concurrent.Semaphore;
import java.util.concurrent.TimeUnit;

import static org.elasticsearch.common.xcontent.XContentFactory.jsonBuilder;
import static org.elasticsearch.test.hamcrest.ElasticsearchAssertions.assertAcked;
import static org.elasticsearch.test.hamcrest.ElasticsearchAssertions.assertThrows;
import static org.hamcrest.Matchers.containsString;
import static org.hamcrest.Matchers.equalTo;
import static org.hamcrest.Matchers.greaterThan;
import static org.hamcrest.Matchers.lessThanOrEqualTo;
import static org.hamcrest.Matchers.notNullValue;
import static org.hamcrest.Matchers.nullValue;

public class UpdateTests extends ElasticsearchIntegrationTest {

    private void createTestIndex() throws Exception {
        logger.info("--> creating index test");

        assertAcked(prepareCreate("test").addAlias(new Alias("alias"))
                .addMapping("type1", XContentFactory.jsonBuilder()
                        .startObject()
                        .startObject("type1")
                        .startObject("_timestamp").field("enabled", true).field("store", "yes").endObject()
                        .startObject("_ttl").field("enabled", true).endObject()
                        .endObject()
                        .endObject()));
    }

    @Test
    public void testUpsert() throws Exception {
        createTestIndex();
        ensureGreen();

        UpdateResponse updateResponse = client().prepareUpdate(indexOrAlias(), "type1", "1")
                .setUpsert(XContentFactory.jsonBuilder().startObject().field("field", 1).endObject())
                .setScript(new Script("ctx._source.field += 1", ScriptService.ScriptType.INLINE, null, null))
                .execute().actionGet();
        assertTrue(updateResponse.isCreated());
        assertThat(updateResponse.getIndex(), equalTo("test"));

        for (int i = 0; i < 5; i++) {
            GetResponse getResponse = client().prepareGet("test", "type1", "1").execute().actionGet();
            assertThat(getResponse.getSourceAsMap().get("field").toString(), equalTo("1"));
        }

        updateResponse = client().prepareUpdate(indexOrAlias(), "type1", "1")
                .setUpsert(XContentFactory.jsonBuilder().startObject().field("field", 1).endObject())
                .setScript(new Script("ctx._source.field += 1", ScriptService.ScriptType.INLINE, null, null))
                .execute().actionGet();
        assertFalse(updateResponse.isCreated());
        assertThat(updateResponse.getIndex(), equalTo("test"));

        for (int i = 0; i < 5; i++) {
            GetResponse getResponse = client().prepareGet("test", "type1", "1").execute().actionGet();
            assertThat(getResponse.getSourceAsMap().get("field").toString(), equalTo("2"));
        }
    }

    @Test
    public void testScriptedUpsert() throws Exception {
        createTestIndex();
        ensureGreen();
        
        // Script logic is 
        // 1) New accounts take balance from "balance" in upsert doc and first payment is charged at 50%
        // 2) Existing accounts subtract full payment from balance stored in elasticsearch
        
        String script="int oldBalance=ctx._source.balance;"+
                      "int deduction=ctx.op == \"create\" ? (payment/2) :  payment;"+
                      "ctx._source.balance=oldBalance-deduction;";
        int openingBalance=10;

        Map<String, Object> params = new HashMap<>();
        params.put("payment", 2);

        // Pay money from what will be a new account and opening balance comes from upsert doc
        // provided by client
        UpdateResponse updateResponse = client().prepareUpdate(indexOrAlias(), "type1", "1")
                .setUpsert(XContentFactory.jsonBuilder().startObject().field("balance", openingBalance).endObject())
                .setScriptedUpsert(true)
.setScript(new Script(script, ScriptService.ScriptType.INLINE, null, params))
                .execute().actionGet();
        assertTrue(updateResponse.isCreated());
        assertThat(updateResponse.getIndex(), equalTo("test"));

        for (int i = 0; i < 5; i++) {
            GetResponse getResponse = client().prepareGet("test", "type1", "1").execute().actionGet();
            assertThat(getResponse.getSourceAsMap().get("balance").toString(), equalTo("9"));
        }

        // Now pay money for an existing account where balance is stored in es 
        updateResponse = client().prepareUpdate(indexOrAlias(), "type1", "1")
                .setUpsert(XContentFactory.jsonBuilder().startObject().field("balance", openingBalance).endObject())
                .setScriptedUpsert(true)
.setScript(new Script(script, ScriptService.ScriptType.INLINE, null, params))
                .execute().actionGet();
        assertFalse(updateResponse.isCreated());
        assertThat(updateResponse.getIndex(), equalTo("test"));

        for (int i = 0; i < 5; i++) {
            GetResponse getResponse = client().prepareGet("test", "type1", "1").execute().actionGet();
            assertThat(getResponse.getSourceAsMap().get("balance").toString(), equalTo("7"));
        }
    }

    @Test
    public void testUpsertDoc() throws Exception {
        createTestIndex();
        ensureGreen();

        UpdateResponse updateResponse = client().prepareUpdate(indexOrAlias(), "type1", "1")
                .setDoc(XContentFactory.jsonBuilder().startObject().field("bar", "baz").endObject())
                .setDocAsUpsert(true)
                .setFields("_source")
                .execute().actionGet();
        assertThat(updateResponse.getIndex(), equalTo("test"));
        assertThat(updateResponse.getGetResult(), notNullValue());
        assertThat(updateResponse.getGetResult().getIndex(), equalTo("test"));
        assertThat(updateResponse.getGetResult().sourceAsMap().get("bar").toString(), equalTo("baz"));
    }

    @Test
    // See: https://github.com/elasticsearch/elasticsearch/issues/3265
    public void testNotUpsertDoc() throws Exception {
        createTestIndex();
        ensureGreen();

        assertThrows(client().prepareUpdate(indexOrAlias(), "type1", "1")
                .setDoc(XContentFactory.jsonBuilder().startObject().field("bar", "baz").endObject())
                .setDocAsUpsert(false)
                .setFields("_source")
                .execute(), DocumentMissingException.class);
    }

    @Test
    public void testUpsertFields() throws Exception {
        createTestIndex();
        ensureGreen();

        UpdateResponse updateResponse = client().prepareUpdate(indexOrAlias(), "type1", "1")
                .setUpsert(XContentFactory.jsonBuilder().startObject().field("bar", "baz").endObject())
                .setScript(new Script("ctx._source.extra = \"foo\"", ScriptService.ScriptType.INLINE, null, null))
                .setFields("_source")
                .execute().actionGet();

        assertThat(updateResponse.getIndex(), equalTo("test"));
        assertThat(updateResponse.getGetResult(), notNullValue());
        assertThat(updateResponse.getGetResult().getIndex(), equalTo("test"));
        assertThat(updateResponse.getGetResult().sourceAsMap().get("bar").toString(), equalTo("baz"));
        assertThat(updateResponse.getGetResult().sourceAsMap().get("extra"), nullValue());

        updateResponse = client().prepareUpdate(indexOrAlias(), "type1", "1")
                .setUpsert(XContentFactory.jsonBuilder().startObject().field("bar", "baz").endObject())
                .setScript(new Script("ctx._source.extra = \"foo\"", ScriptService.ScriptType.INLINE, null, null))
                .setFields("_source")
                .execute().actionGet();

        assertThat(updateResponse.getIndex(), equalTo("test"));
        assertThat(updateResponse.getGetResult(), notNullValue());
        assertThat(updateResponse.getGetResult().getIndex(), equalTo("test"));
        assertThat(updateResponse.getGetResult().sourceAsMap().get("bar").toString(), equalTo("baz"));
        assertThat(updateResponse.getGetResult().sourceAsMap().get("extra").toString(), equalTo("foo"));
    }

    @Test
    public void testVersionedUpdate() throws Exception {
        assertAcked(prepareCreate("test").addAlias(new Alias("alias")));
        ensureGreen();

        index("test", "type", "1", "text", "value"); // version is now 1

        assertThrows(client().prepareUpdate(indexOrAlias(), "type", "1")
                        .setScript(new Script("ctx._source.text = 'v2'", ScriptService.ScriptType.INLINE, null, null)).setVersion(2)
                        .execute(),
                VersionConflictEngineException.class);

        client().prepareUpdate(indexOrAlias(), "type", "1")
                .setScript(new Script("ctx._source.text = 'v2'", ScriptService.ScriptType.INLINE, null, null)).setVersion(1).get();
        assertThat(client().prepareGet("test", "type", "1").get().getVersion(), equalTo(2l));

        // and again with a higher version..
        client().prepareUpdate(indexOrAlias(), "type", "1")
                .setScript(new Script("ctx._source.text = 'v3'", ScriptService.ScriptType.INLINE, null, null)).setVersion(2).get();

        assertThat(client().prepareGet("test", "type", "1").get().getVersion(), equalTo(3l));

        // after delete
        client().prepareDelete("test", "type", "1").get();
        assertThrows(client().prepareUpdate("test", "type", "1")
                        .setScript(new Script("ctx._source.text = 'v2'", ScriptService.ScriptType.INLINE, null, null)).setVersion(3)
                        .execute(),
                DocumentMissingException.class);

        // external versioning
        client().prepareIndex("test", "type", "2").setSource("text", "value").setVersion(10).setVersionType(VersionType.EXTERNAL).get();

        assertThrows(client().prepareUpdate(indexOrAlias(), "type", "2")
                        .setScript(new Script("ctx._source.text = 'v2'", ScriptService.ScriptType.INLINE, null, null)).setVersion(2)
                        .setVersionType(VersionType.EXTERNAL).execute(),
                ActionRequestValidationException.class);

        // upserts - the combination with versions is a bit weird. Test are here to ensure we do not change our behavior unintentionally

        // With internal versions, tt means "if object is there with version X, update it or explode. If it is not there, index.
        client().prepareUpdate(indexOrAlias(), "type", "3")
                .setScript(new Script("ctx._source.text = 'v2'", ScriptService.ScriptType.INLINE, null, null))
                .setVersion(10).setUpsert("{ \"text\": \"v0\" }").get();
        GetResponse get = get("test", "type", "3");
        assertThat(get.getVersion(), equalTo(1l));
        assertThat((String) get.getSource().get("text"), equalTo("v0"));

        // With force version
        client().prepareUpdate(indexOrAlias(), "type", "4")
                .setScript(new Script("ctx._source.text = 'v2'", ScriptService.ScriptType.INLINE, null, null))
                .setVersion(10).setVersionType(VersionType.FORCE).setUpsert("{ \"text\": \"v0\" }").get();

        get = get("test", "type", "4");
        assertThat(get.getVersion(), equalTo(10l));
        assertThat((String) get.getSource().get("text"), equalTo("v0"));


        // retry on conflict is rejected:
        assertThrows(client().prepareUpdate(indexOrAlias(), "type", "1").setVersion(10).setRetryOnConflict(5), ActionRequestValidationException.class);
    }

    @Test
    public void testIndexAutoCreation() throws Exception {
        UpdateResponse updateResponse = client().prepareUpdate("test", "type1", "1")
                .setUpsert(XContentFactory.jsonBuilder().startObject().field("bar", "baz").endObject())
                .setScript(new Script("ctx._source.extra = \"foo\"", ScriptService.ScriptType.INLINE, null, null))
                .setFields("_source")
                .execute().actionGet();

        assertThat(updateResponse.getIndex(), equalTo("test"));
        assertThat(updateResponse.getGetResult(), notNullValue());
        assertThat(updateResponse.getGetResult().getIndex(), equalTo("test"));
        assertThat(updateResponse.getGetResult().sourceAsMap().get("bar").toString(), equalTo("baz"));
        assertThat(updateResponse.getGetResult().sourceAsMap().get("extra"), nullValue());
    }

    @Test
    public void testUpdate() throws Exception {
        createTestIndex();
        ensureGreen();

        try {
            client().prepareUpdate(indexOrAlias(), "type1", "1")
                    .setScript(new Script("ctx._source.field++", ScriptService.ScriptType.INLINE, null, null)).execute().actionGet();
            fail();
        } catch (DocumentMissingException e) {
            // all is well
        }

        client().prepareIndex("test", "type1", "1").setSource("field", 1).execute().actionGet();

        UpdateResponse updateResponse = client().prepareUpdate(indexOrAlias(), "type1", "1")
                .setScript(new Script("ctx._source.field += 1", ScriptService.ScriptType.INLINE, null, null)).execute().actionGet();
        assertThat(updateResponse.getVersion(), equalTo(2L));
        assertFalse(updateResponse.isCreated());
        assertThat(updateResponse.getIndex(), equalTo("test"));

        for (int i = 0; i < 5; i++) {
            GetResponse getResponse = client().prepareGet("test", "type1", "1").execute().actionGet();
            assertThat(getResponse.getSourceAsMap().get("field").toString(), equalTo("2"));
        }

        Map<String, Object> params = new HashMap<>();
        params.put("count", 3);
        updateResponse = client().prepareUpdate(indexOrAlias(), "type1", "1")
                .setScript(new Script("ctx._source.field += count", ScriptService.ScriptType.INLINE, null, params)).execute().actionGet();
        assertThat(updateResponse.getVersion(), equalTo(3L));
        assertFalse(updateResponse.isCreated());
        assertThat(updateResponse.getIndex(), equalTo("test"));

        for (int i = 0; i < 5; i++) {
            GetResponse getResponse = client().prepareGet("test", "type1", "1").execute().actionGet();
            assertThat(getResponse.getSourceAsMap().get("field").toString(), equalTo("5"));
        }

        // check noop
        updateResponse = client().prepareUpdate(indexOrAlias(), "type1", "1")
                .setScript(new Script("ctx.op = 'none'", ScriptService.ScriptType.INLINE, null, null)).execute().actionGet();
        assertThat(updateResponse.getVersion(), equalTo(3L));
        assertFalse(updateResponse.isCreated());
        assertThat(updateResponse.getIndex(), equalTo("test"));

        for (int i = 0; i < 5; i++) {
            GetResponse getResponse = client().prepareGet("test", "type1", "1").execute().actionGet();
            assertThat(getResponse.getSourceAsMap().get("field").toString(), equalTo("5"));
        }

        // check delete
        updateResponse = client().prepareUpdate(indexOrAlias(), "type1", "1")
                .setScript(new Script("ctx.op = 'delete'", ScriptService.ScriptType.INLINE, null, null)).execute().actionGet();
        assertThat(updateResponse.getVersion(), equalTo(4L));
        assertFalse(updateResponse.isCreated());
        assertThat(updateResponse.getIndex(), equalTo("test"));

        for (int i = 0; i < 5; i++) {
            GetResponse getResponse = client().prepareGet("test", "type1", "1").execute().actionGet();
            assertThat(getResponse.isExists(), equalTo(false));
        }

        // check TTL is kept after an update without TTL
        client().prepareIndex("test", "type1", "2").setSource("field", 1).setTTL(86400000L).setRefresh(true).execute().actionGet();
        GetResponse getResponse = client().prepareGet("test", "type1", "2").setFields("_ttl").execute().actionGet();
        long ttl = ((Number) getResponse.getField("_ttl").getValue()).longValue();
        assertThat(ttl, greaterThan(0L));
        client().prepareUpdate(indexOrAlias(), "type1", "2")
                .setScript(new Script("ctx._source.field += 1", ScriptService.ScriptType.INLINE, null, null)).execute().actionGet();
        getResponse = client().prepareGet("test", "type1", "2").setFields("_ttl").execute().actionGet();
        ttl = ((Number) getResponse.getField("_ttl").getValue()).longValue();
        assertThat(ttl, greaterThan(0L));

        // check TTL update
        client().prepareUpdate(indexOrAlias(), "type1", "2")
                .setScript(new Script("ctx._ttl = 3600000", ScriptService.ScriptType.INLINE, null, null)).execute().actionGet();
        getResponse = client().prepareGet("test", "type1", "2").setFields("_ttl").execute().actionGet();
        ttl = ((Number) getResponse.getField("_ttl").getValue()).longValue();
        assertThat(ttl, greaterThan(0L));
        assertThat(ttl, lessThanOrEqualTo(3600000L));

        // check timestamp update
        client().prepareIndex("test", "type1", "3").setSource("field", 1).setRefresh(true).execute().actionGet();
        client().prepareUpdate(indexOrAlias(), "type1", "3")
                .setScript(new Script("ctx._timestamp = \"2009-11-15T14:12:12\"", ScriptService.ScriptType.INLINE, null, null)).execute()
                .actionGet();
        getResponse = client().prepareGet("test", "type1", "3").setFields("_timestamp").execute().actionGet();
        long timestamp = ((Number) getResponse.getField("_timestamp").getValue()).longValue();
        assertThat(timestamp, equalTo(1258294332000L));

        // check fields parameter
        client().prepareIndex("test", "type1", "1").setSource("field", 1).execute().actionGet();
        updateResponse = client().prepareUpdate(indexOrAlias(), "type1", "1")
                .setScript(new Script("ctx._source.field += 1", ScriptService.ScriptType.INLINE, null, null)).setFields("_source", "field")
                .execute().actionGet();
        assertThat(updateResponse.getIndex(), equalTo("test"));
        assertThat(updateResponse.getGetResult(), notNullValue());
        assertThat(updateResponse.getGetResult().getIndex(), equalTo("test"));
        assertThat(updateResponse.getGetResult().sourceRef(), notNullValue());
        assertThat(updateResponse.getGetResult().field("field").getValue(), notNullValue());

        // check updates without script
        // add new field
        client().prepareIndex("test", "type1", "1").setSource("field", 1).execute().actionGet();
        updateResponse = client().prepareUpdate(indexOrAlias(), "type1", "1").setDoc(XContentFactory.jsonBuilder().startObject().field("field2", 2).endObject()).execute().actionGet();
        for (int i = 0; i < 5; i++) {
            getResponse = client().prepareGet("test", "type1", "1").execute().actionGet();
            assertThat(getResponse.getSourceAsMap().get("field").toString(), equalTo("1"));
            assertThat(getResponse.getSourceAsMap().get("field2").toString(), equalTo("2"));
        }

        // change existing field
        updateResponse = client().prepareUpdate(indexOrAlias(), "type1", "1").setDoc(XContentFactory.jsonBuilder().startObject().field("field", 3).endObject()).execute().actionGet();
        for (int i = 0; i < 5; i++) {
            getResponse = client().prepareGet("test", "type1", "1").execute().actionGet();
            assertThat(getResponse.getSourceAsMap().get("field").toString(), equalTo("3"));
            assertThat(getResponse.getSourceAsMap().get("field2").toString(), equalTo("2"));
        }

        // recursive map
        Map<String, Object> testMap = new HashMap<>();
        Map<String, Object> testMap2 = new HashMap<>();
        Map<String, Object> testMap3 = new HashMap<>();
        testMap3.put("commonkey", testMap);
        testMap3.put("map3", 5);
        testMap2.put("map2", 6);
        testMap.put("commonkey", testMap2);
        testMap.put("map1", 8);

        client().prepareIndex("test", "type1", "1").setSource("map", testMap).execute().actionGet();
        updateResponse = client().prepareUpdate(indexOrAlias(), "type1", "1").setDoc(XContentFactory.jsonBuilder().startObject().field("map", testMap3).endObject()).execute().actionGet();
        for (int i = 0; i < 5; i++) {
            getResponse = client().prepareGet("test", "type1", "1").execute().actionGet();
            Map map1 = (Map) getResponse.getSourceAsMap().get("map");
            assertThat(map1.size(), equalTo(3));
            assertThat(map1.containsKey("map1"), equalTo(true));
            assertThat(map1.containsKey("map3"), equalTo(true));
            assertThat(map1.containsKey("commonkey"), equalTo(true));
            Map map2 = (Map) map1.get("commonkey");
            assertThat(map2.size(), equalTo(3));
            assertThat(map2.containsKey("map1"), equalTo(true));
            assertThat(map2.containsKey("map2"), equalTo(true));
            assertThat(map2.containsKey("commonkey"), equalTo(true));
        }
    }

    @Test
    public void testUpdateRequestWithBothScriptAndDoc() throws Exception {
        createTestIndex();
        ensureGreen();

        try {
            client().prepareUpdate(indexOrAlias(), "type1", "1")
                    .setDoc(XContentFactory.jsonBuilder().startObject().field("field", 1).endObject())
                    .setScript(new Script("ctx._source.field += 1", ScriptService.ScriptType.INLINE, null, null))
                    .execute().actionGet();
            fail("Should have thrown ActionRequestValidationException");
        } catch (ActionRequestValidationException e) {
            assertThat(e.validationErrors().size(), equalTo(1));
            assertThat(e.validationErrors().get(0), containsString("can't provide both script and doc"));
            assertThat(e.getMessage(), containsString("can't provide both script and doc"));
        }
    }

    @Test
    public void testUpdateRequestWithScriptAndShouldUpsertDoc() throws Exception {
        createTestIndex();
        ensureGreen();
        try {
            client().prepareUpdate(indexOrAlias(), "type1", "1")
                    .setScript(new Script("ctx._source.field += 1", ScriptService.ScriptType.INLINE, null, null))
                    .setDocAsUpsert(true)
                    .execute().actionGet();
            fail("Should have thrown ActionRequestValidationException");
        } catch (ActionRequestValidationException e) {
            assertThat(e.validationErrors().size(), equalTo(1));
            assertThat(e.validationErrors().get(0), containsString("doc must be specified if doc_as_upsert is enabled"));
            assertThat(e.getMessage(), containsString("doc must be specified if doc_as_upsert is enabled"));
        }
    }

    @Test
    public void testContextVariables() throws Exception {
        assertAcked(prepareCreate("test").addAlias(new Alias("alias"))
                        .addMapping("type1", XContentFactory.jsonBuilder()
                                .startObject()
                                .startObject("type1")
                                .startObject("_timestamp").field("enabled", true).field("store", "yes").endObject()
                                .startObject("_ttl").field("enabled", true).endObject()
                                .endObject()
                                .endObject())
                        .addMapping("subtype1", XContentFactory.jsonBuilder()
                                .startObject()
                                .startObject("subtype1")
                                .startObject("_parent").field("type", "type1").endObject()
                                .startObject("_timestamp").field("enabled", true).field("store", "yes").endObject()
                                .startObject("_ttl").field("enabled", true).endObject()
                                .endObject()
                                .endObject())
        );
        ensureGreen();

        // Index some documents
        long timestamp = System.currentTimeMillis();
        client().prepareIndex()
                .setIndex("test")
                .setType("type1")
                .setId("parentId1")
                .setTimestamp(String.valueOf(timestamp-1))
                .setSource("field1", 0, "content", "bar")
                .execute().actionGet();

        long ttl = 10000;
        client().prepareIndex()
                .setIndex("test")
                .setType("subtype1")
                .setId("id1")
                .setParent("parentId1")
                .setRouting("routing1")
                .setTimestamp(String.valueOf(timestamp))
                .setTTL(ttl)
                .setSource("field1", 1, "content", "foo")
                .execute().actionGet();

        // Update the first object and note context variables values
        Map<String, Object> scriptParams = new HashMap<>();
        scriptParams.put("delim", "_");
        UpdateResponse updateResponse = client().prepareUpdate("test", "subtype1", "id1")
                .setRouting("routing1")
                .setScript(
                        new Script("assert ctx._index == \"test\" : \"index should be \\\"test\\\"\"\n"
                                +
                                "assert ctx._type == \"subtype1\" : \"type should be \\\"subtype1\\\"\"\n" +
                                "assert ctx._id == \"id1\" : \"id should be \\\"id1\\\"\"\n" +
                                "assert ctx._version == 1 : \"version should be 1\"\n" +
                                "assert ctx._parent == \"parentId1\" : \"parent should be \\\"parentId1\\\"\"\n" +
                                "assert ctx._routing == \"routing1\" : \"routing should be \\\"routing1\\\"\"\n" +
                                "assert ctx._timestamp == " + timestamp + " : \"timestamp should be " + timestamp + "\"\n" +
                                // ttl has a 3-second leeway, because it's always counting down
                                "assert ctx._ttl <= " + ttl + " : \"ttl should be <= " + ttl + " but was \" + ctx._ttl\n" +
                                "assert ctx._ttl >= " + (ttl-3000) + " : \"ttl should be <= " + (ttl-3000) + " but was \" + ctx._ttl\n" +
                                "ctx._source.content = ctx._source.content + delim + ctx._source.content;\n" +
                                "ctx._source.field1 += 1;\n",
 ScriptService.ScriptType.INLINE, null, scriptParams))
                .execute().actionGet();

        assertEquals(2, updateResponse.getVersion());

        GetResponse getResponse = client().prepareGet("test", "subtype1", "id1").setRouting("routing1").execute().actionGet();
        assertEquals(2, getResponse.getSourceAsMap().get("field1"));
        assertEquals("foo_foo", getResponse.getSourceAsMap().get("content"));

        // Idem with the second object
        scriptParams = new HashMap<>();
        scriptParams.put("delim", "_");
        updateResponse = client().prepareUpdate("test", "type1", "parentId1")
                .setScript(
                        new Script(
                        "assert ctx._index == \"test\" : \"index should be \\\"test\\\"\"\n" +
                        "assert ctx._type == \"type1\" : \"type should be \\\"type1\\\"\"\n" +
                        "assert ctx._id == \"parentId1\" : \"id should be \\\"parentId1\\\"\"\n" +
                        "assert ctx._version == 1 : \"version should be 1\"\n" +
                        "assert ctx._parent == null : \"parent should be null\"\n" +
                        "assert ctx._routing == null : \"routing should be null\"\n" +
                        "assert ctx._timestamp == " + (timestamp - 1) + " : \"timestamp should be " + (timestamp - 1) + "\"\n" +
                        "assert ctx._ttl == null : \"ttl should be null\"\n" +
                        "ctx._source.content = ctx._source.content + delim + ctx._source.content;\n" +
                        "ctx._source.field1 += 1;\n",
 ScriptService.ScriptType.INLINE, null, scriptParams))
                .execute().actionGet();

        assertEquals(2, updateResponse.getVersion());

        getResponse = client().prepareGet("test", "type1", "parentId1").execute().actionGet();
        assertEquals(1, getResponse.getSourceAsMap().get("field1"));
        assertEquals("bar_bar", getResponse.getSourceAsMap().get("content"));
    }

    @Test
    @Slow
    public void testConcurrentUpdateWithRetryOnConflict() throws Exception {
        final boolean useBulkApi = randomBoolean();
        createTestIndex();
        ensureGreen();

        int numberOfThreads = scaledRandomIntBetween(2,5);
        final CountDownLatch latch = new CountDownLatch(numberOfThreads);
        final CountDownLatch startLatch = new CountDownLatch(1);
        final int numberOfUpdatesPerThread = scaledRandomIntBetween(100, 10000);
        final List<Throwable> failures = new CopyOnWriteArrayList<>();
        for (int i = 0; i < numberOfThreads; i++) {
            Runnable r = new Runnable() {

                @Override
                public void run() {
                    try {
                        startLatch.await();
                        for (int i = 0; i < numberOfUpdatesPerThread; i++) {
                            if (useBulkApi) {
                                UpdateRequestBuilder updateRequestBuilder = client().prepareUpdate(indexOrAlias(), "type1", Integer.toString(i))
                                        .setScript(new Script("ctx._source.field += 1", ScriptService.ScriptType.INLINE, null, null))
                                        .setRetryOnConflict(Integer.MAX_VALUE)
                                        .setUpsert(jsonBuilder().startObject().field("field", 1).endObject());
                                client().prepareBulk().add(updateRequestBuilder).execute().actionGet();
                            } else {
                                client().prepareUpdate(indexOrAlias(), "type1", Integer.toString(i))
                                        .setScript(new Script("ctx._source.field += 1", ScriptService.ScriptType.INLINE, null, null))
                                        .setRetryOnConflict(Integer.MAX_VALUE)
                                        .setUpsert(jsonBuilder().startObject().field("field", 1).endObject())
                                        .execute().actionGet();
                            }
                        }
                    } catch (Throwable e) {
                        failures.add(e);
                    } finally {
                        latch.countDown();
                    }
                }

            };
            new Thread(r).start();
        }
        startLatch.countDown();
        latch.await();
        for (Throwable throwable : failures) {
            logger.info("Captured failure on concurrent update:", throwable);
        }
        assertThat(failures.size(), equalTo(0));
        for (int i = 0; i < numberOfUpdatesPerThread; i++) {
            GetResponse response = client().prepareGet("test", "type1", Integer.toString(i)).execute().actionGet();
            assertThat(response.getId(), equalTo(Integer.toString(i)));
            assertThat(response.isExists(), equalTo(true));
            assertThat(response.getVersion(), equalTo((long) numberOfThreads));
            assertThat((Integer) response.getSource().get("field"), equalTo(numberOfThreads));
        }
    }

    @Test
    @Slow
    public void stressUpdateDeleteConcurrency() throws Exception {
        //We create an index with merging disabled so that deletes don't get merged away
        assertAcked(prepareCreate("test")
                .addMapping("type1", XContentFactory.jsonBuilder()
                        .startObject()
                        .startObject("type1")
                        .startObject("_timestamp").field("enabled", true).field("store", "yes").endObject()
                        .startObject("_ttl").field("enabled", true).endObject()
                        .endObject()
                        .endObject())
                .setSettings(Settings.builder().put(MergePolicyModule.MERGE_POLICY_TYPE_KEY, NoMergePolicyProvider.class)));
        ensureGreen();

        final int numberOfThreads = scaledRandomIntBetween(3,5);
        final int numberOfIdsPerThread = scaledRandomIntBetween(3,10);
        final int numberOfUpdatesPerId = scaledRandomIntBetween(10,100);
        final int retryOnConflict = randomIntBetween(0,1);
        final CountDownLatch latch = new CountDownLatch(numberOfThreads);
        final CountDownLatch startLatch = new CountDownLatch(1);
        final List<Throwable> failures = new CopyOnWriteArrayList<>();

        final class UpdateThread extends Thread {
            final Map<Integer,Integer> failedMap = new HashMap<>();
            final int numberOfIds;
            final int updatesPerId;
            final int maxUpdateRequests = numberOfIdsPerThread*numberOfUpdatesPerId;
            final int maxDeleteRequests = numberOfIdsPerThread*numberOfUpdatesPerId;
            private final Semaphore updateRequestsOutstanding = new Semaphore(maxUpdateRequests);
            private final Semaphore deleteRequestsOutstanding = new Semaphore(maxDeleteRequests);

            public UpdateThread(int numberOfIds, int updatesPerId) {
                this.numberOfIds = numberOfIds;
                this.updatesPerId = updatesPerId;
            }

            final class UpdateListener implements ActionListener<UpdateResponse> {
                int id;

                public UpdateListener(int id) {
                    this.id = id;
                }

                @Override
                public void onResponse(UpdateResponse updateResponse) {
                    updateRequestsOutstanding.release(1);
                }

                @Override
                public void onFailure(Throwable e) {
                    synchronized (failedMap) {
                        incrementMapValue(id, failedMap);
                    }
                    updateRequestsOutstanding.release(1);
                }

            }

            final class DeleteListener implements ActionListener<DeleteResponse> {
                int id;

                public DeleteListener(int id) {
                    this.id = id;
                }

                @Override
                public void onResponse(DeleteResponse deleteResponse) {
                    deleteRequestsOutstanding.release(1);
                }

                @Override
                public void onFailure(Throwable e) {
                    synchronized (failedMap) {
                        incrementMapValue(id, failedMap);
                    }
                    deleteRequestsOutstanding.release(1);
                }
            }

            @Override
            public void run(){
                try {
                    startLatch.await();
                    boolean hasWaitedForNoNode = false;
                    for (int j = 0; j < numberOfIds; j++) {
                        for (int k = 0; k < numberOfUpdatesPerId; ++k) {
                            updateRequestsOutstanding.acquire();
                            try {
                                UpdateRequest ur = client().prepareUpdate("test", "type1", Integer.toString(j))
                                        .setScript(new Script("ctx._source.field += 1", ScriptService.ScriptType.INLINE, null, null))
                                        .setRetryOnConflict(retryOnConflict)
                                        .setUpsert(jsonBuilder().startObject().field("field", 1).endObject())
                                        .request();
                                client().update(ur, new UpdateListener(j));
                            } catch (NoNodeAvailableException nne) {
                                updateRequestsOutstanding.release();
                                synchronized (failedMap) {
                                    incrementMapValue(j, failedMap);
                                }
                                if (hasWaitedForNoNode) {
                                    throw nne;
                                }
                                logger.warn("Got NoNodeException waiting for 1 second for things to recover.");
                                hasWaitedForNoNode = true;
                                Thread.sleep(1000);
                            }

                            try {
                                deleteRequestsOutstanding.acquire();
                                DeleteRequest dr = client().prepareDelete("test", "type1", Integer.toString(j)).request();
                                client().delete(dr, new DeleteListener(j));
                            } catch (NoNodeAvailableException nne) {
                                deleteRequestsOutstanding.release();
                                synchronized (failedMap) {
                                    incrementMapValue(j, failedMap);
                                }
                                if (hasWaitedForNoNode) {
                                    throw nne;
                                }
                                logger.warn("Got NoNodeException waiting for 1 second for things to recover.");
                                hasWaitedForNoNode = true;
                                Thread.sleep(1000); //Wait for no-node to clear
                            }
                        }
                    }
                } catch (Throwable e) {
                    logger.error("Something went wrong", e);
                    failures.add(e);
                } finally {
                    try {
                        waitForOutstandingRequests(TimeValue.timeValueSeconds(60), updateRequestsOutstanding, maxUpdateRequests, "Update");
                        waitForOutstandingRequests(TimeValue.timeValueSeconds(60), deleteRequestsOutstanding, maxDeleteRequests, "Delete");
                    } catch (ElasticsearchTimeoutException ete) {
                        failures.add(ete);
                    }
                    latch.countDown();
                }
            }

            private void incrementMapValue(int j, Map<Integer,Integer> map) {
                if (!map.containsKey(j)) {
                    map.put(j, 0);
                }
                map.put(j, map.get(j) + 1);
            }

            private void waitForOutstandingRequests(TimeValue timeOut, Semaphore requestsOutstanding, int maxRequests, String name) {
                long start = System.currentTimeMillis();
                do {
                    long msRemaining = timeOut.getMillis() - (System.currentTimeMillis() - start);
                    logger.info("[{}] going to try and acquire [{}] in [{}]ms [{}] available to acquire right now",name, maxRequests,msRemaining, requestsOutstanding.availablePermits());
                    try {
                        requestsOutstanding.tryAcquire(maxRequests, msRemaining, TimeUnit.MILLISECONDS );
                        return;
                    } catch (InterruptedException ie) {
                        //Just keep swimming
                    }
                } while ((System.currentTimeMillis() - start) < timeOut.getMillis());
                throw new ElasticsearchTimeoutException("Requests were still outstanding after the timeout [" + timeOut + "] for type [" + name + "]" );
            }
        }
        final List<UpdateThread> threads = new ArrayList<>();

        for (int i = 0; i < numberOfThreads; i++) {
            UpdateThread ut = new UpdateThread(numberOfIdsPerThread, numberOfUpdatesPerId);
            ut.start();
            threads.add(ut);
        }

        startLatch.countDown();
        latch.await();

        for (UpdateThread ut : threads){
            ut.join(); //Threads should have finished because of the latch.await
        }

        //If are no errors every request received a response otherwise the test would have timedout
        //aquiring the request outstanding semaphores.
        for (Throwable throwable : failures) {
            logger.info("Captured failure on concurrent update:", throwable);
        }

        assertThat(failures.size(), equalTo(0));

        //Upsert all the ids one last time to make sure they are available at get time
        //This means that we add 1 to the expected versions and attempts
        //All the previous operations should be complete or failed at this point
        for (int i = 0; i < numberOfIdsPerThread; ++i) {
            UpdateResponse ur = client().prepareUpdate("test", "type1", Integer.toString(i))
                    .setScript(new Script("ctx._source.field += 1", ScriptService.ScriptType.INLINE, null, null))
                .setRetryOnConflict(Integer.MAX_VALUE)
                .setUpsert(jsonBuilder().startObject().field("field", 1).endObject())
                .execute().actionGet();
        }

        refresh();

        for (int i = 0; i < numberOfIdsPerThread; ++i) {
            int totalFailures = 0;
            GetResponse response = client().prepareGet("test", "type1", Integer.toString(i)).execute().actionGet();
            if (response.isExists()) {
                assertThat(response.getId(), equalTo(Integer.toString(i)));
                int expectedVersion = (numberOfThreads * numberOfUpdatesPerId * 2) + 1;
                for (UpdateThread ut : threads) {
                    if (ut.failedMap.containsKey(i)) {
                        totalFailures += ut.failedMap.get(i);
                    }
                }
                expectedVersion -= totalFailures;
                logger.error("Actual version [{}] Expected version [{}] Total failures [{}]", response.getVersion(), expectedVersion, totalFailures);
                assertThat(response.getVersion(), equalTo((long) expectedVersion));
                assertThat(response.getVersion() + totalFailures,
                        equalTo(
                                (long)((numberOfUpdatesPerId * numberOfThreads * 2) + 1)
                ));
            }
        }
    }

    /*
     * TODO Remove in 2.0
     */
    @Test
    public void testUpsertOldScriptAPI() throws Exception {
        createTestIndex();
        ensureGreen();

        UpdateResponse updateResponse = client().prepareUpdate(indexOrAlias(), "type1", "1")
                .setUpsert(XContentFactory.jsonBuilder().startObject().field("field", 1).endObject())
                .setScript("ctx._source.field += 1", ScriptService.ScriptType.INLINE).execute().actionGet();
        assertTrue(updateResponse.isCreated());
        assertThat(updateResponse.getIndex(), equalTo("test"));

        for (int i = 0; i < 5; i++) {
            GetResponse getResponse = client().prepareGet("test", "type1", "1").execute().actionGet();
            assertThat(getResponse.getSourceAsMap().get("field").toString(), equalTo("1"));
        }

        updateResponse = client().prepareUpdate(indexOrAlias(), "type1", "1")
                .setUpsert(XContentFactory.jsonBuilder().startObject().field("field", 1).endObject())
                .setScript("ctx._source.field += 1", ScriptService.ScriptType.INLINE).execute().actionGet();
        assertFalse(updateResponse.isCreated());
        assertThat(updateResponse.getIndex(), equalTo("test"));

        for (int i = 0; i < 5; i++) {
            GetResponse getResponse = client().prepareGet("test", "type1", "1").execute().actionGet();
            assertThat(getResponse.getSourceAsMap().get("field").toString(), equalTo("2"));
        }
    }

    /*
     * TODO Remove in 2.0
     */
    @Test
    public void testScriptedUpsertOldScriptAPI() throws Exception {
        createTestIndex();
        ensureGreen();

        // Script logic is 
        // 1) New accounts take balance from "balance" in upsert doc and first payment is charged at 50%
        // 2) Existing accounts subtract full payment from balance stored in elasticsearch

        String script = "int oldBalance=ctx._source.balance;" + "int deduction=ctx.op == \"create\" ? (payment/2) :  payment;"
                + "ctx._source.balance=oldBalance-deduction;";
        int openingBalance = 10;

        // Pay money from what will be a new account and opening balance comes from upsert doc
        // provided by client
        UpdateResponse updateResponse = client().prepareUpdate(indexOrAlias(), "type1", "1")
                .setUpsert(XContentFactory.jsonBuilder().startObject().field("balance", openingBalance).endObject())
                .setScriptedUpsert(true).addScriptParam("payment", 2).setScript(script, ScriptService.ScriptType.INLINE).execute()
                .actionGet();
        assertTrue(updateResponse.isCreated());
        assertThat(updateResponse.getIndex(), equalTo("test"));

        for (int i = 0; i < 5; i++) {
            GetResponse getResponse = client().prepareGet("test", "type1", "1").execute().actionGet();
            assertThat(getResponse.getSourceAsMap().get("balance").toString(), equalTo("9"));
        }

        // Now pay money for an existing account where balance is stored in es 
        updateResponse = client().prepareUpdate(indexOrAlias(), "type1", "1")
                .setUpsert(XContentFactory.jsonBuilder().startObject().field("balance", openingBalance).endObject())
                .setScriptedUpsert(true).addScriptParam("payment", 2).setScript(script, ScriptService.ScriptType.INLINE).execute()
                .actionGet();
        assertFalse(updateResponse.isCreated());
        assertThat(updateResponse.getIndex(), equalTo("test"));

        for (int i = 0; i < 5; i++) {
            GetResponse getResponse = client().prepareGet("test", "type1", "1").execute().actionGet();
            assertThat(getResponse.getSourceAsMap().get("balance").toString(), equalTo("7"));
        }
    }

    /*
     * TODO Remove in 2.0
     */
    @Test
    public void testUpsertFieldsOldScriptAPI() throws Exception {
        createTestIndex();
        ensureGreen();

        UpdateResponse updateResponse = client().prepareUpdate(indexOrAlias(), "type1", "1")
                .setUpsert(XContentFactory.jsonBuilder().startObject().field("bar", "baz").endObject())
                .setScript("ctx._source.extra = \"foo\"", ScriptService.ScriptType.INLINE).setFields("_source").execute().actionGet();

        assertThat(updateResponse.getIndex(), equalTo("test"));
        assertThat(updateResponse.getGetResult(), notNullValue());
        assertThat(updateResponse.getGetResult().getIndex(), equalTo("test"));
        assertThat(updateResponse.getGetResult().sourceAsMap().get("bar").toString(), equalTo("baz"));
        assertThat(updateResponse.getGetResult().sourceAsMap().get("extra"), nullValue());

        updateResponse = client().prepareUpdate(indexOrAlias(), "type1", "1")
                .setUpsert(XContentFactory.jsonBuilder().startObject().field("bar", "baz").endObject())
                .setScript("ctx._source.extra = \"foo\"", ScriptService.ScriptType.INLINE).setFields("_source").execute().actionGet();

        assertThat(updateResponse.getIndex(), equalTo("test"));
        assertThat(updateResponse.getGetResult(), notNullValue());
        assertThat(updateResponse.getGetResult().getIndex(), equalTo("test"));
        assertThat(updateResponse.getGetResult().sourceAsMap().get("bar").toString(), equalTo("baz"));
        assertThat(updateResponse.getGetResult().sourceAsMap().get("extra").toString(), equalTo("foo"));
    }

    /*
     * TODO Remove in 2.0
     */
    @Test
    public void testVersionedUpdateOldScriptAPI() throws Exception {
        assertAcked(prepareCreate("test").addAlias(new Alias("alias")));
        ensureGreen();

        index("test", "type", "1", "text", "value"); // version is now 1

        assertThrows(
                client().prepareUpdate(indexOrAlias(), "type", "1").setScript("ctx._source.text = 'v2'", ScriptService.ScriptType.INLINE)
                        .setVersion(2).execute(), VersionConflictEngineException.class);

        client().prepareUpdate(indexOrAlias(), "type", "1").setScript("ctx._source.text = 'v2'", ScriptService.ScriptType.INLINE)
                .setVersion(1).get();
        assertThat(client().prepareGet("test", "type", "1").get().getVersion(), equalTo(2l));

        // and again with a higher version..
        client().prepareUpdate(indexOrAlias(), "type", "1").setScript("ctx._source.text = 'v3'", ScriptService.ScriptType.INLINE)
                .setVersion(2).get();

        assertThat(client().prepareGet("test", "type", "1").get().getVersion(), equalTo(3l));

        // after delete
        client().prepareDelete("test", "type", "1").get();
        assertThrows(client().prepareUpdate("test", "type", "1").setScript("ctx._source.text = 'v2'", ScriptService.ScriptType.INLINE)
                .setVersion(3).execute(), DocumentMissingException.class);

        // external versioning
        client().prepareIndex("test", "type", "2").setSource("text", "value").setVersion(10).setVersionType(VersionType.EXTERNAL).get();

        assertThrows(
                client().prepareUpdate(indexOrAlias(), "type", "2").setScript("ctx._source.text = 'v2'", ScriptService.ScriptType.INLINE)
                        .setVersion(2).setVersionType(VersionType.EXTERNAL).execute(), ActionRequestValidationException.class);

        // upserts - the combination with versions is a bit weird. Test are here to ensure we do not change our behavior unintentionally

        // With internal versions, tt means "if object is there with version X, update it or explode. If it is not there, index.
        client().prepareUpdate(indexOrAlias(), "type", "3").setScript("ctx._source.text = 'v2'", ScriptService.ScriptType.INLINE)
                .setVersion(10).setUpsert("{ \"text\": \"v0\" }").get();
        GetResponse get = get("test", "type", "3");
        assertThat(get.getVersion(), equalTo(1l));
        assertThat((String) get.getSource().get("text"), equalTo("v0"));

        // With force version
        client().prepareUpdate(indexOrAlias(), "type", "4").setScript("ctx._source.text = 'v2'", ScriptService.ScriptType.INLINE)
                .setVersion(10).setVersionType(VersionType.FORCE).setUpsert("{ \"text\": \"v0\" }").get();

        get = get("test", "type", "4");
        assertThat(get.getVersion(), equalTo(10l));
        assertThat((String) get.getSource().get("text"), equalTo("v0"));

        // retry on conflict is rejected:
        assertThrows(client().prepareUpdate(indexOrAlias(), "type", "1").setVersion(10).setRetryOnConflict(5),
                ActionRequestValidationException.class);
    }

    /*
     * TODO Remove in 2.0
     */
    @Test
    public void testIndexAutoCreationOldScriptAPI() throws Exception {
        UpdateResponse updateResponse = client().prepareUpdate("test", "type1", "1")
                .setUpsert(XContentFactory.jsonBuilder().startObject().field("bar", "baz").endObject())
                .setScript("ctx._source.extra = \"foo\"", ScriptService.ScriptType.INLINE).setFields("_source").execute().actionGet();

        assertThat(updateResponse.getIndex(), equalTo("test"));
        assertThat(updateResponse.getGetResult(), notNullValue());
        assertThat(updateResponse.getGetResult().getIndex(), equalTo("test"));
        assertThat(updateResponse.getGetResult().sourceAsMap().get("bar").toString(), equalTo("baz"));
        assertThat(updateResponse.getGetResult().sourceAsMap().get("extra"), nullValue());
    }

    /*
     * TODO Remove in 2.0
     */
    @Test
    public void testUpdateOldScriptAPI() throws Exception {
        createTestIndex();
        ensureGreen();

        try {
            client().prepareUpdate(indexOrAlias(), "type1", "1").setScript("ctx._source.field++", ScriptService.ScriptType.INLINE)
                    .execute().actionGet();
            fail();
        } catch (DocumentMissingException e) {
            // all is well
        }

        client().prepareIndex("test", "type1", "1").setSource("field", 1).execute().actionGet();

        UpdateResponse updateResponse = client().prepareUpdate(indexOrAlias(), "type1", "1")
                .setScript("ctx._source.field += 1", ScriptService.ScriptType.INLINE).execute().actionGet();
        assertThat(updateResponse.getVersion(), equalTo(2L));
        assertFalse(updateResponse.isCreated());
        assertThat(updateResponse.getIndex(), equalTo("test"));

        for (int i = 0; i < 5; i++) {
            GetResponse getResponse = client().prepareGet("test", "type1", "1").execute().actionGet();
            assertThat(getResponse.getSourceAsMap().get("field").toString(), equalTo("2"));
        }

        updateResponse = client().prepareUpdate(indexOrAlias(), "type1", "1")
                .setScript("ctx._source.field += count", ScriptService.ScriptType.INLINE).addScriptParam("count", 3).execute().actionGet();
        assertThat(updateResponse.getVersion(), equalTo(3L));
        assertFalse(updateResponse.isCreated());
        assertThat(updateResponse.getIndex(), equalTo("test"));

        for (int i = 0; i < 5; i++) {
            GetResponse getResponse = client().prepareGet("test", "type1", "1").execute().actionGet();
            assertThat(getResponse.getSourceAsMap().get("field").toString(), equalTo("5"));
        }

        // check noop
        updateResponse = client().prepareUpdate(indexOrAlias(), "type1", "1").setScript("ctx.op = 'none'", ScriptService.ScriptType.INLINE)
                .execute().actionGet();
        assertThat(updateResponse.getVersion(), equalTo(3L));
        assertFalse(updateResponse.isCreated());
        assertThat(updateResponse.getIndex(), equalTo("test"));

        for (int i = 0; i < 5; i++) {
            GetResponse getResponse = client().prepareGet("test", "type1", "1").execute().actionGet();
            assertThat(getResponse.getSourceAsMap().get("field").toString(), equalTo("5"));
        }

        // check delete
        updateResponse = client().prepareUpdate(indexOrAlias(), "type1", "1")
                .setScript("ctx.op = 'delete'", ScriptService.ScriptType.INLINE).execute().actionGet();
        assertThat(updateResponse.getVersion(), equalTo(4L));
        assertFalse(updateResponse.isCreated());
        assertThat(updateResponse.getIndex(), equalTo("test"));

        for (int i = 0; i < 5; i++) {
            GetResponse getResponse = client().prepareGet("test", "type1", "1").execute().actionGet();
            assertThat(getResponse.isExists(), equalTo(false));
        }

        // check TTL is kept after an update without TTL
        client().prepareIndex("test", "type1", "2").setSource("field", 1).setTTL(86400000L).setRefresh(true).execute().actionGet();
        GetResponse getResponse = client().prepareGet("test", "type1", "2").setFields("_ttl").execute().actionGet();
        long ttl = ((Number) getResponse.getField("_ttl").getValue()).longValue();
        assertThat(ttl, greaterThan(0L));
        client().prepareUpdate(indexOrAlias(), "type1", "2").setScript("ctx._source.field += 1", ScriptService.ScriptType.INLINE).execute()
                .actionGet();
        getResponse = client().prepareGet("test", "type1", "2").setFields("_ttl").execute().actionGet();
        ttl = ((Number) getResponse.getField("_ttl").getValue()).longValue();
        assertThat(ttl, greaterThan(0L));

        // check TTL update
        client().prepareUpdate(indexOrAlias(), "type1", "2").setScript("ctx._ttl = 3600000", ScriptService.ScriptType.INLINE).execute()
                .actionGet();
        getResponse = client().prepareGet("test", "type1", "2").setFields("_ttl").execute().actionGet();
        ttl = ((Number) getResponse.getField("_ttl").getValue()).longValue();
        assertThat(ttl, greaterThan(0L));
        assertThat(ttl, lessThanOrEqualTo(3600000L));

        // check timestamp update
        client().prepareIndex("test", "type1", "3").setSource("field", 1).setRefresh(true).execute().actionGet();
        client().prepareUpdate(indexOrAlias(), "type1", "3")
                .setScript("ctx._timestamp = \"2009-11-15T14:12:12\"", ScriptService.ScriptType.INLINE).execute().actionGet();
        getResponse = client().prepareGet("test", "type1", "3").setFields("_timestamp").execute().actionGet();
        long timestamp = ((Number) getResponse.getField("_timestamp").getValue()).longValue();
        assertThat(timestamp, equalTo(1258294332000L));

        // check fields parameter
        client().prepareIndex("test", "type1", "1").setSource("field", 1).execute().actionGet();
        updateResponse = client().prepareUpdate(indexOrAlias(), "type1", "1")
                .setScript("ctx._source.field += 1", ScriptService.ScriptType.INLINE).setFields("_source", "field").execute().actionGet();
        assertThat(updateResponse.getIndex(), equalTo("test"));
        assertThat(updateResponse.getGetResult(), notNullValue());
        assertThat(updateResponse.getGetResult().getIndex(), equalTo("test"));
        assertThat(updateResponse.getGetResult().sourceRef(), notNullValue());
        assertThat(updateResponse.getGetResult().field("field").getValue(), notNullValue());

        // check updates without script
        // add new field
        client().prepareIndex("test", "type1", "1").setSource("field", 1).execute().actionGet();
        updateResponse = client().prepareUpdate(indexOrAlias(), "type1", "1")
                .setDoc(XContentFactory.jsonBuilder().startObject().field("field2", 2).endObject()).execute().actionGet();
        for (int i = 0; i < 5; i++) {
            getResponse = client().prepareGet("test", "type1", "1").execute().actionGet();
            assertThat(getResponse.getSourceAsMap().get("field").toString(), equalTo("1"));
            assertThat(getResponse.getSourceAsMap().get("field2").toString(), equalTo("2"));
        }

        // change existing field
        updateResponse = client().prepareUpdate(indexOrAlias(), "type1", "1")
                .setDoc(XContentFactory.jsonBuilder().startObject().field("field", 3).endObject()).execute().actionGet();
        for (int i = 0; i < 5; i++) {
            getResponse = client().prepareGet("test", "type1", "1").execute().actionGet();
            assertThat(getResponse.getSourceAsMap().get("field").toString(), equalTo("3"));
            assertThat(getResponse.getSourceAsMap().get("field2").toString(), equalTo("2"));
        }

        // recursive map
        Map<String, Object> testMap = new HashMap<>();
        Map<String, Object> testMap2 = new HashMap<>();
        Map<String, Object> testMap3 = new HashMap<>();
        testMap3.put("commonkey", testMap);
        testMap3.put("map3", 5);
        testMap2.put("map2", 6);
        testMap.put("commonkey", testMap2);
        testMap.put("map1", 8);

        client().prepareIndex("test", "type1", "1").setSource("map", testMap).execute().actionGet();
        updateResponse = client().prepareUpdate(indexOrAlias(), "type1", "1")
                .setDoc(XContentFactory.jsonBuilder().startObject().field("map", testMap3).endObject()).execute().actionGet();
        for (int i = 0; i < 5; i++) {
            getResponse = client().prepareGet("test", "type1", "1").execute().actionGet();
            Map map1 = (Map) getResponse.getSourceAsMap().get("map");
            assertThat(map1.size(), equalTo(3));
            assertThat(map1.containsKey("map1"), equalTo(true));
            assertThat(map1.containsKey("map3"), equalTo(true));
            assertThat(map1.containsKey("commonkey"), equalTo(true));
            Map map2 = (Map) map1.get("commonkey");
            assertThat(map2.size(), equalTo(3));
            assertThat(map2.containsKey("map1"), equalTo(true));
            assertThat(map2.containsKey("map2"), equalTo(true));
            assertThat(map2.containsKey("commonkey"), equalTo(true));
        }
    }

    /*
     * TODO Remove in 2.0
     */
    @Test
    public void testUpdateRequestWithBothScriptAndDocOldScriptAPI() throws Exception {
        createTestIndex();
        ensureGreen();

        try {
            client().prepareUpdate(indexOrAlias(), "type1", "1")
                    .setDoc(XContentFactory.jsonBuilder().startObject().field("field", 1).endObject())
                    .setScript("ctx._source.field += 1", ScriptService.ScriptType.INLINE).execute().actionGet();
            fail("Should have thrown ActionRequestValidationException");
        } catch (ActionRequestValidationException e) {
            assertThat(e.validationErrors().size(), equalTo(1));
            assertThat(e.validationErrors().get(0), containsString("can't provide both script and doc"));
            assertThat(e.getMessage(), containsString("can't provide both script and doc"));
        }
    }

    /*
     * TODO Remove in 2.0
     */
    @Test
    public void testUpdateRequestWithScriptAndShouldUpsertDocOldScriptAPI() throws Exception {
        createTestIndex();
        ensureGreen();
        try {
            client().prepareUpdate(indexOrAlias(), "type1", "1")
                    .setScript(new Script("ctx._source.field += 1", ScriptService.ScriptType.INLINE, null, null)).setDocAsUpsert(true)
                    .execute().actionGet();
            fail("Should have thrown ActionRequestValidationException");
        } catch (ActionRequestValidationException e) {
            assertThat(e.validationErrors().size(), equalTo(1));
            assertThat(e.validationErrors().get(0), containsString("doc must be specified if doc_as_upsert is enabled"));
            assertThat(e.getMessage(), containsString("doc must be specified if doc_as_upsert is enabled"));
        }
    }

    /*
     * TODO Remove in 2.0
     */
    @Test
    public void testContextVariablesOldScriptAPI() throws Exception {
        assertAcked(prepareCreate("test").addAlias(new Alias("alias"))
                        .addMapping("type1", XContentFactory.jsonBuilder()
                                .startObject()
                                .startObject("type1")
                                .startObject("_timestamp").field("enabled", true).field("store", "yes").endObject()
                                .startObject("_ttl").field("enabled", true).endObject()
                                .endObject()
                                .endObject())
                        .addMapping("subtype1", XContentFactory.jsonBuilder()
                                .startObject()
                                .startObject("subtype1")
                                .startObject("_parent").field("type", "type1").endObject()
                                .startObject("_timestamp").field("enabled", true).field("store", "yes").endObject()
                                .startObject("_ttl").field("enabled", true).endObject()
                                .endObject()
                                .endObject())
        );
        ensureGreen();

        // Index some documents
        long timestamp = System.currentTimeMillis();
        client().prepareIndex().setIndex("test").setType("type1").setId("parentId1").setTimestamp(String.valueOf(timestamp - 1))
                .setSource("field1", 0, "content", "bar").execute().actionGet();

        long ttl = 10000;
        client().prepareIndex().setIndex("test").setType("subtype1").setId("id1").setParent("parentId1").setRouting("routing1")
                .setTimestamp(String.valueOf(timestamp)).setTTL(ttl).setSource("field1", 1, "content", "foo").execute().actionGet();

        // Update the first object and note context variables values
        Map<String, Object> scriptParams = new HashMap<>();
        scriptParams.put("delim", "_");
        UpdateResponse updateResponse = client()
                .prepareUpdate("test", "subtype1", "id1")
                .setRouting("routing1")
                .setScript(
                        "assert ctx._index == \"test\" : \"index should be \\\"test\\\"\"\n"
                                + "assert ctx._type == \"subtype1\" : \"type should be \\\"subtype1\\\"\"\n"
                                + "assert ctx._id == \"id1\" : \"id should be \\\"id1\\\"\"\n"
                                + "assert ctx._version == 1 : \"version should be 1\"\n"
                                + "assert ctx._parent == \"parentId1\" : \"parent should be \\\"parentId1\\\"\"\n"
                                + "assert ctx._routing == \"routing1\" : \"routing should be \\\"routing1\\\"\"\n"
                                + "assert ctx._timestamp == " + timestamp + " : \"timestamp should be "
                                + timestamp
                                + "\"\n"
                                +
                                // ttl has a 3-second leeway, because it's always counting down
                                "assert ctx._ttl <= " + ttl + " : \"ttl should be <= " + ttl + " but was \" + ctx._ttl\n"
                                + "assert ctx._ttl >= " + (ttl - 3000) + " : \"ttl should be <= " + (ttl - 3000)
                                + " but was \" + ctx._ttl\n" + "ctx._source.content = ctx._source.content + delim + ctx._source.content;\n"
                                + "ctx._source.field1 += 1;\n", ScriptService.ScriptType.INLINE).setScriptParams(scriptParams).execute()
                .actionGet();

        assertEquals(2, updateResponse.getVersion());

        GetResponse getResponse = client().prepareGet("test", "subtype1", "id1").setRouting("routing1").execute().actionGet();
        assertEquals(2, getResponse.getSourceAsMap().get("field1"));
        assertEquals("foo_foo", getResponse.getSourceAsMap().get("content"));

        // Idem with the second object
        scriptParams = new HashMap<>();
        scriptParams.put("delim", "_");
        updateResponse = client()
                .prepareUpdate("test", "type1", "parentId1")
                .setScript(
                        "assert ctx._index == \"test\" : \"index should be \\\"test\\\"\"\n"
                                + "assert ctx._type == \"type1\" : \"type should be \\\"type1\\\"\"\n"
                                + "assert ctx._id == \"parentId1\" : \"id should be \\\"parentId1\\\"\"\n"
                                + "assert ctx._version == 1 : \"version should be 1\"\n"
                                + "assert ctx._parent == null : \"parent should be null\"\n"
                                + "assert ctx._routing == null : \"routing should be null\"\n" + "assert ctx._timestamp == "
                                + (timestamp - 1) + " : \"timestamp should be " + (timestamp - 1) + "\"\n"
                                + "assert ctx._ttl == null : \"ttl should be null\"\n"
                                + "ctx._source.content = ctx._source.content + delim + ctx._source.content;\n"
                                + "ctx._source.field1 += 1;\n", ScriptService.ScriptType.INLINE).setScriptParams(scriptParams).execute()
                .actionGet();

        assertEquals(2, updateResponse.getVersion());

        getResponse = client().prepareGet("test", "type1", "parentId1").execute().actionGet();
        assertEquals(1, getResponse.getSourceAsMap().get("field1"));
        assertEquals("bar_bar", getResponse.getSourceAsMap().get("content"));
    }

    /*
     * TODO Remove in 2.0
     */
    @Test
    @Slow
    public void testConcurrentUpdateWithRetryOnConflictOldScriptAPI() throws Exception {
        final boolean useBulkApi = randomBoolean();
        createTestIndex();
        ensureGreen();

        int numberOfThreads = scaledRandomIntBetween(2, 5);
        final CountDownLatch latch = new CountDownLatch(numberOfThreads);
        final CountDownLatch startLatch = new CountDownLatch(1);
        final int numberOfUpdatesPerThread = scaledRandomIntBetween(100, 10000);
        final List<Throwable> failures = new CopyOnWriteArrayList<>();
        for (int i = 0; i < numberOfThreads; i++) {
            Runnable r = new Runnable() {

                @Override
                public void run() {
                    try {
                        startLatch.await();
                        for (int i = 0; i < numberOfUpdatesPerThread; i++) {
                            if (useBulkApi) {
                                UpdateRequestBuilder updateRequestBuilder = client()
                                        .prepareUpdate(indexOrAlias(), "type1", Integer.toString(i))
                                        .setScript("ctx._source.field += 1", ScriptService.ScriptType.INLINE)
                                        .setRetryOnConflict(Integer.MAX_VALUE)
                                        .setUpsert(jsonBuilder().startObject().field("field", 1).endObject());
                                client().prepareBulk().add(updateRequestBuilder).execute().actionGet();
                            } else {
                                client().prepareUpdate(indexOrAlias(), "type1", Integer.toString(i))
                                        .setScript("ctx._source.field += 1", ScriptService.ScriptType.INLINE)
                                        .setRetryOnConflict(Integer.MAX_VALUE)
                                        .setUpsert(jsonBuilder().startObject().field("field", 1).endObject()).execute().actionGet();
                            }
                        }
                    } catch (Throwable e) {
                        failures.add(e);
                    } finally {
                        latch.countDown();
                    }
                }

            };
            new Thread(r).start();
        }
        startLatch.countDown();
        latch.await();
        for (Throwable throwable : failures) {
            logger.info("Captured failure on concurrent update:", throwable);
        }
        assertThat(failures.size(), equalTo(0));
        for (int i = 0; i < numberOfUpdatesPerThread; i++) {
            GetResponse response = client().prepareGet("test", "type1", Integer.toString(i)).execute().actionGet();
            assertThat(response.getId(), equalTo(Integer.toString(i)));
            assertThat(response.isExists(), equalTo(true));
            assertThat(response.getVersion(), equalTo((long) numberOfThreads));
            assertThat((Integer) response.getSource().get("field"), equalTo(numberOfThreads));
        }
    }

    /*
     * TODO Remove in 2.0
     */
    @Test
    @Slow
    public void stressUpdateDeleteConcurrencyOldScriptAPI() throws Exception {
        //We create an index with merging disabled so that deletes don't get merged away
        assertAcked(prepareCreate("test").addMapping(
                "type1",
                XContentFactory.jsonBuilder().startObject().startObject("type1").startObject("_timestamp").field("enabled", true)
                        .field("store", "yes").endObject().startObject("_ttl").field("enabled", true).endObject().endObject().endObject())
                .setSettings(Settings.builder().put(MergePolicyModule.MERGE_POLICY_TYPE_KEY, NoMergePolicyProvider.class)));
        ensureGreen();

        final int numberOfThreads = scaledRandomIntBetween(3, 5);
        final int numberOfIdsPerThread = scaledRandomIntBetween(3, 10);
        final int numberOfUpdatesPerId = scaledRandomIntBetween(10, 100);
        final int retryOnConflict = randomIntBetween(0, 1);
        final CountDownLatch latch = new CountDownLatch(numberOfThreads);
        final CountDownLatch startLatch = new CountDownLatch(1);
        final List<Throwable> failures = new CopyOnWriteArrayList<>();

        final class UpdateThread extends Thread {
            final Map<Integer, Integer> failedMap = new HashMap<>();
            final int numberOfIds;
            final int updatesPerId;
            final int maxUpdateRequests = numberOfIdsPerThread * numberOfUpdatesPerId;
            final int maxDeleteRequests = numberOfIdsPerThread * numberOfUpdatesPerId;
            private final Semaphore updateRequestsOutstanding = new Semaphore(maxUpdateRequests);
            private final Semaphore deleteRequestsOutstanding = new Semaphore(maxDeleteRequests);

            public UpdateThread(int numberOfIds, int updatesPerId) {
                this.numberOfIds = numberOfIds;
                this.updatesPerId = updatesPerId;
            }

            final class UpdateListener implements ActionListener<UpdateResponse> {
                int id;

                public UpdateListener(int id) {
                    this.id = id;
                }

                @Override
                public void onResponse(UpdateResponse updateResponse) {
                    updateRequestsOutstanding.release(1);
                }

                @Override
                public void onFailure(Throwable e) {
                    synchronized (failedMap) {
                        incrementMapValue(id, failedMap);
                    }
                    updateRequestsOutstanding.release(1);
                }

            }

            final class DeleteListener implements ActionListener<DeleteResponse> {
                int id;

                public DeleteListener(int id) {
                    this.id = id;
                }

                @Override
                public void onResponse(DeleteResponse deleteResponse) {
                    deleteRequestsOutstanding.release(1);
                }

                @Override
                public void onFailure(Throwable e) {
                    synchronized (failedMap) {
                        incrementMapValue(id, failedMap);
                    }
                    deleteRequestsOutstanding.release(1);
                }
            }

            @Override
            public void run() {
                try {
                    startLatch.await();
                    boolean hasWaitedForNoNode = false;
                    for (int j = 0; j < numberOfIds; j++) {
                        for (int k = 0; k < numberOfUpdatesPerId; ++k) {
                            updateRequestsOutstanding.acquire();
                            try {
                                UpdateRequest ur = client().prepareUpdate("test", "type1", Integer.toString(j))
                                        .setScript("ctx._source.field += 1", ScriptService.ScriptType.INLINE)
                                        .setRetryOnConflict(retryOnConflict)
                                        .setUpsert(jsonBuilder().startObject().field("field", 1).endObject()).request();
                                client().update(ur, new UpdateListener(j));
                            } catch (NoNodeAvailableException nne) {
                                updateRequestsOutstanding.release();
                                synchronized (failedMap) {
                                    incrementMapValue(j, failedMap);
                                }
                                if (hasWaitedForNoNode) {
                                    throw nne;
                                }
                                logger.warn("Got NoNodeException waiting for 1 second for things to recover.");
                                hasWaitedForNoNode = true;
                                Thread.sleep(1000);
                            }

                            try {
                                deleteRequestsOutstanding.acquire();
                                DeleteRequest dr = client().prepareDelete("test", "type1", Integer.toString(j)).request();
                                client().delete(dr, new DeleteListener(j));
                            } catch (NoNodeAvailableException nne) {
                                deleteRequestsOutstanding.release();
                                synchronized (failedMap) {
                                    incrementMapValue(j, failedMap);
                                }
                                if (hasWaitedForNoNode) {
                                    throw nne;
                                }
                                logger.warn("Got NoNodeException waiting for 1 second for things to recover.");
                                hasWaitedForNoNode = true;
                                Thread.sleep(1000); //Wait for no-node to clear
                            }
                        }
                    }
                } catch (Throwable e) {
                    logger.error("Something went wrong", e);
                    failures.add(e);
                } finally {
                    try {
                        waitForOutstandingRequests(TimeValue.timeValueSeconds(60), updateRequestsOutstanding, maxUpdateRequests, "Update");
                        waitForOutstandingRequests(TimeValue.timeValueSeconds(60), deleteRequestsOutstanding, maxDeleteRequests, "Delete");
                    } catch (ElasticsearchTimeoutException ete) {
                        failures.add(ete);
                    }
                    latch.countDown();
                }
            }

            private void incrementMapValue(int j, Map<Integer, Integer> map) {
                if (!map.containsKey(j)) {
                    map.put(j, 0);
                }
                map.put(j, map.get(j) + 1);
            }

            private void waitForOutstandingRequests(TimeValue timeOut, Semaphore requestsOutstanding, int maxRequests, String name) {
                long start = System.currentTimeMillis();
                do {
                    long msRemaining = timeOut.getMillis() - (System.currentTimeMillis() - start);
                    logger.info("[{}] going to try and acquire [{}] in [{}]ms [{}] available to acquire right now", name, maxRequests,
                            msRemaining, requestsOutstanding.availablePermits());
                    try {
                        requestsOutstanding.tryAcquire(maxRequests, msRemaining, TimeUnit.MILLISECONDS);
                        return;
                    } catch (InterruptedException ie) {
                        //Just keep swimming
                    }
                } while ((System.currentTimeMillis() - start) < timeOut.getMillis());
                throw new ElasticsearchTimeoutException("Requests were still outstanding after the timeout [" + timeOut + "] for type ["
                        + name + "]");
            }
        }
        final List<UpdateThread> threads = new ArrayList<>();

        for (int i = 0; i < numberOfThreads; i++) {
            UpdateThread ut = new UpdateThread(numberOfIdsPerThread, numberOfUpdatesPerId);
            ut.start();
            threads.add(ut);
        }

        startLatch.countDown();
        latch.await();

        for (UpdateThread ut : threads) {
            ut.join(); //Threads should have finished because of the latch.await
        }

        //If are no errors every request received a response otherwise the test would have timedout
        //aquiring the request outstanding semaphores.
        for (Throwable throwable : failures) {
            logger.info("Captured failure on concurrent update:", throwable);
        }

        assertThat(failures.size(), equalTo(0));

        //Upsert all the ids one last time to make sure they are available at get time
        //This means that we add 1 to the expected versions and attempts
        //All the previous operations should be complete or failed at this point
        for (int i = 0; i < numberOfIdsPerThread; ++i) {
            UpdateResponse ur = client().prepareUpdate("test", "type1", Integer.toString(i))
                    .setScript("ctx._source.field += 1", ScriptService.ScriptType.INLINE).setRetryOnConflict(Integer.MAX_VALUE)
                    .setUpsert(jsonBuilder().startObject().field("field", 1).endObject()).execute().actionGet();
        }

        refresh();

        for (int i = 0; i < numberOfIdsPerThread; ++i) {
            int totalFailures = 0;
            GetResponse response = client().prepareGet("test", "type1", Integer.toString(i)).execute().actionGet();
            if (response.isExists()) {
                assertThat(response.getId(), equalTo(Integer.toString(i)));
                int expectedVersion = (numberOfThreads * numberOfUpdatesPerId * 2) + 1;
                for (UpdateThread ut : threads) {
                    if (ut.failedMap.containsKey(i)) {
                        totalFailures += ut.failedMap.get(i);
                    }
                }
                expectedVersion -= totalFailures;
                logger.error("Actual version [{}] Expected version [{}] Total failures [{}]", response.getVersion(), expectedVersion,
                        totalFailures);
                assertThat(response.getVersion(), equalTo((long) expectedVersion));
                assertThat(response.getVersion() + totalFailures, equalTo((long) ((numberOfUpdatesPerId * numberOfThreads * 2) + 1)));
            }
        }
    }

    private static String indexOrAlias() {
        return randomBoolean() ? "test" : "alias";
    }
}
