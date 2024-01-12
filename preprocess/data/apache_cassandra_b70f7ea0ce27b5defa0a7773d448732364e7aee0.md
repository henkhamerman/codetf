Refactoring Types: ['Extract Method']
db/ColumnFamilyStore.java
/*
 * Licensed to the Apache Software Foundation (ASF) under one
 * or more contributor license agreements.  See the NOTICE file
 * distributed with this work for additional information
 * regarding copyright ownership.  The ASF licenses this file
 * to you under the Apache License, Version 2.0 (the
 * "License"); you may not use this file except in compliance
 * with the License.  You may obtain a copy of the License at
 *
 *     http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 */
package org.apache.cassandra.db;

import java.io.*;
import java.lang.management.ManagementFactory;
import java.nio.ByteBuffer;
import java.util.*;
import java.util.concurrent.*;
import java.util.concurrent.atomic.AtomicInteger;
import java.util.concurrent.atomic.AtomicReference;
import java.util.regex.Pattern;
import javax.management.*;
import javax.management.openmbean.*;

import com.google.common.annotations.VisibleForTesting;
import com.google.common.base.*;
import com.google.common.base.Throwables;
import com.google.common.collect.*;
import com.google.common.util.concurrent.*;

import org.apache.cassandra.io.FSWriteError;
import org.apache.cassandra.utils.memory.MemtablePool;
import org.json.simple.*;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import org.apache.cassandra.cache.*;
import org.apache.cassandra.concurrent.*;
import org.apache.cassandra.config.*;
import org.apache.cassandra.config.CFMetaData.SpeculativeRetry;
import org.apache.cassandra.db.commitlog.CommitLog;
import org.apache.cassandra.db.commitlog.ReplayPosition;
import org.apache.cassandra.db.compaction.*;
import org.apache.cassandra.db.composites.CellName;
import org.apache.cassandra.db.composites.CellNameType;
import org.apache.cassandra.db.composites.Composite;
import org.apache.cassandra.db.filter.ColumnSlice;
import org.apache.cassandra.db.filter.ExtendedFilter;
import org.apache.cassandra.db.filter.IDiskAtomFilter;
import org.apache.cassandra.db.filter.QueryFilter;
import org.apache.cassandra.db.filter.SliceQueryFilter;
import org.apache.cassandra.db.index.SecondaryIndex;
import org.apache.cassandra.db.index.SecondaryIndexManager;
import org.apache.cassandra.dht.*;
import org.apache.cassandra.dht.Range;
import org.apache.cassandra.exceptions.ConfigurationException;
import org.apache.cassandra.io.FSReadError;
import org.apache.cassandra.io.compress.CompressionParameters;
import org.apache.cassandra.io.sstable.*;
import org.apache.cassandra.io.sstable.Descriptor;
import org.apache.cassandra.io.sstable.metadata.CompactionMetadata;
import org.apache.cassandra.io.sstable.metadata.MetadataType;
import org.apache.cassandra.io.util.FileUtils;
import org.apache.cassandra.metrics.ColumnFamilyMetrics;
import org.apache.cassandra.metrics.ColumnFamilyMetrics.Sampler;
import org.apache.cassandra.service.CacheService;
import org.apache.cassandra.service.StorageService;
import org.apache.cassandra.streaming.StreamLockfile;
import org.apache.cassandra.tracing.Tracing;
import org.apache.cassandra.utils.*;
import org.apache.cassandra.utils.concurrent.*;
import org.apache.cassandra.utils.TopKSampler.SamplerResult;
import org.apache.cassandra.utils.memory.MemtableAllocator;

import com.clearspring.analytics.stream.Counter;

public class ColumnFamilyStore implements ColumnFamilyStoreMBean
{
    private static final Logger logger = LoggerFactory.getLogger(ColumnFamilyStore.class);

    private static final ExecutorService flushExecutor = new JMXEnabledThreadPoolExecutor(DatabaseDescriptor.getFlushWriters(),
                                                                                          StageManager.KEEPALIVE,
                                                                                          TimeUnit.SECONDS,
                                                                                          new LinkedBlockingQueue<Runnable>(),
                                                                                          new NamedThreadFactory("MemtableFlushWriter"),
                                                                                          "internal");

    // post-flush executor is single threaded to provide guarantee that any flush Future on a CF will never return until prior flushes have completed
    private static final ExecutorService postFlushExecutor = new JMXEnabledThreadPoolExecutor(1,
                                                                                              StageManager.KEEPALIVE,
                                                                                              TimeUnit.SECONDS,
                                                                                              new LinkedBlockingQueue<Runnable>(),
                                                                                              new NamedThreadFactory("MemtablePostFlush"),
                                                                                              "internal");

    private static final ExecutorService reclaimExecutor = new JMXEnabledThreadPoolExecutor(1,
                                                                                            StageManager.KEEPALIVE,
                                                                                            TimeUnit.SECONDS,
                                                                                            new LinkedBlockingQueue<Runnable>(),
                                                                                            new NamedThreadFactory("MemtableReclaimMemory"),
                                                                                            "internal");

    private static final String[] COUNTER_NAMES = new String[]{"raw", "count", "error", "string"};
    private static final String[] COUNTER_DESCS = new String[]
    { "partition key in raw hex bytes",
      "value of this partition for given sampler",
      "value is within the error bounds plus or minus of this",
      "the partition key turned into a human readable format" };
    private static final CompositeType COUNTER_COMPOSITE_TYPE;
    private static final TabularType COUNTER_TYPE;

    private static final String[] SAMPLER_NAMES = new String[]{"cardinality", "partitions"};
    private static final String[] SAMPLER_DESCS = new String[]
    { "cardinality of partitions",
      "list of counter results" };

    private static final String SAMPLING_RESULTS_NAME = "SAMPLING_RESULTS";
    private static final CompositeType SAMPLING_RESULT;

    static
    {
        try
        {
            OpenType<?>[] counterTypes = new OpenType[] { SimpleType.STRING, SimpleType.LONG, SimpleType.LONG, SimpleType.STRING };
            COUNTER_COMPOSITE_TYPE = new CompositeType(SAMPLING_RESULTS_NAME, SAMPLING_RESULTS_NAME, COUNTER_NAMES, COUNTER_DESCS, counterTypes);
            COUNTER_TYPE = new TabularType(SAMPLING_RESULTS_NAME, SAMPLING_RESULTS_NAME, COUNTER_COMPOSITE_TYPE, COUNTER_NAMES);

            OpenType<?>[] samplerTypes = new OpenType[] { SimpleType.LONG, COUNTER_TYPE };
            SAMPLING_RESULT = new CompositeType(SAMPLING_RESULTS_NAME, SAMPLING_RESULTS_NAME, SAMPLER_NAMES, SAMPLER_DESCS, samplerTypes);
        } catch (OpenDataException e)
        {
            throw Throwables.propagate(e);
        }
    }

    public final Keyspace keyspace;
    public final String name;
    public final CFMetaData metadata;
    public final IPartitioner partitioner;
    private final String mbeanName;
    private volatile boolean valid = true;

    /**
     * Memtables and SSTables on disk for this column family.
     *
     * We synchronize on the DataTracker to ensure isolation when we want to make sure
     * that the memtable we're acting on doesn't change out from under us.  I.e., flush
     * syncronizes on it to make sure it can submit on both executors atomically,
     * so anyone else who wants to make sure flush doesn't interfere should as well.
     */
    private final DataTracker data;

    /* The read order, used to track accesses to off-heap memtable storage */
    public final OpOrder readOrdering = new OpOrder();

    /* This is used to generate the next index for a SSTable */
    private final AtomicInteger fileIndexGenerator = new AtomicInteger(0);

    public final SecondaryIndexManager indexManager;

    /* These are locally held copies to be changed from the config during runtime */
    private volatile DefaultInteger minCompactionThreshold;
    private volatile DefaultInteger maxCompactionThreshold;
    private final WrappingCompactionStrategy compactionStrategyWrapper;

    public final Directories directories;

    public final ColumnFamilyMetrics metric;
    public volatile long sampleLatencyNanos;
    private final ScheduledFuture<?> latencyCalculator;

    public static void shutdownPostFlushExecutor() throws InterruptedException
    {
        postFlushExecutor.shutdown();
        postFlushExecutor.awaitTermination(60, TimeUnit.SECONDS);
    }

    public void reload()
    {
        // metadata object has been mutated directly. make all the members jibe with new settings.

        // only update these runtime-modifiable settings if they have not been modified.
        if (!minCompactionThreshold.isModified())
            for (ColumnFamilyStore cfs : concatWithIndexes())
                cfs.minCompactionThreshold = new DefaultInteger(metadata.getMinCompactionThreshold());
        if (!maxCompactionThreshold.isModified())
            for (ColumnFamilyStore cfs : concatWithIndexes())
                cfs.maxCompactionThreshold = new DefaultInteger(metadata.getMaxCompactionThreshold());

        compactionStrategyWrapper.maybeReloadCompactionStrategy(metadata);

        scheduleFlush();

        indexManager.reload();

        // If the CF comparator has changed, we need to change the memtable,
        // because the old one still aliases the previous comparator.
        if (data.getView().getCurrentMemtable().initialComparator != metadata.comparator)
            switchMemtable();
    }

    void scheduleFlush()
    {
        int period = metadata.getMemtableFlushPeriod();
        if (period > 0)
        {
            logger.debug("scheduling flush in {} ms", period);
            WrappedRunnable runnable = new WrappedRunnable()
            {
                protected void runMayThrow() throws Exception
                {
                    synchronized (data)
                    {
                        Memtable current = data.getView().getCurrentMemtable();
                        // if we're not expired, we've been hit by a scheduled flush for an already flushed memtable, so ignore
                        if (current.isExpired())
                        {
                            if (current.isClean())
                            {
                                // if we're still clean, instead of swapping just reschedule a flush for later
                                scheduleFlush();
                            }
                            else
                            {
                                // we'll be rescheduled by the constructor of the Memtable.
                                forceFlush();
                            }
                        }
                    }
                }
            };
            ScheduledExecutors.scheduledTasks.schedule(runnable, period, TimeUnit.MILLISECONDS);
        }
    }

    public static Runnable getBackgroundCompactionTaskSubmitter()
    {
        return new Runnable()
        {
            public void run()
            {
                for (Keyspace keyspace : Keyspace.all())
                    for (ColumnFamilyStore cfs : keyspace.getColumnFamilyStores())
                        CompactionManager.instance.submitBackground(cfs);
            }
        };
    }

    public void setCompactionStrategyClass(String compactionStrategyClass)
    {
        try
        {
            metadata.compactionStrategyClass = CFMetaData.createCompactionStrategy(compactionStrategyClass);
            compactionStrategyWrapper.maybeReloadCompactionStrategy(metadata);
        }
        catch (ConfigurationException e)
        {
            throw new IllegalArgumentException(e.getMessage());
        }
    }

    public String getCompactionStrategyClass()
    {
        return metadata.compactionStrategyClass.getName();
    }

    public Map<String,String> getCompressionParameters()
    {
        return metadata.compressionParameters().asThriftOptions();
    }

    public void setCompressionParameters(Map<String,String> opts)
    {
        try
        {
            metadata.compressionParameters = CompressionParameters.create(opts);
        }
        catch (ConfigurationException e)
        {
            throw new IllegalArgumentException(e.getMessage());
        }
    }

    public void setCrcCheckChance(double crcCheckChance)
    {
        try
        {
            for (SSTableReader sstable : keyspace.getAllSSTables())
                if (sstable.compression)
                    sstable.getCompressionMetadata().parameters.setCrcCheckChance(crcCheckChance);
        }
        catch (ConfigurationException e)
        {
            throw new IllegalArgumentException(e.getMessage());
        }
    }

    private ColumnFamilyStore(Keyspace keyspace,
                              String columnFamilyName,
                              IPartitioner partitioner,
                              int generation,
                              CFMetaData metadata,
                              Directories directories,
                              boolean loadSSTables)
    {
        assert metadata != null : "null metadata for " + keyspace + ":" + columnFamilyName;

        this.keyspace = keyspace;
        name = columnFamilyName;
        this.metadata = metadata;
        this.minCompactionThreshold = new DefaultInteger(metadata.getMinCompactionThreshold());
        this.maxCompactionThreshold = new DefaultInteger(metadata.getMaxCompactionThreshold());
        this.partitioner = partitioner;
        this.directories = directories;
        this.indexManager = new SecondaryIndexManager(this);
        this.metric = new ColumnFamilyMetrics(this);
        fileIndexGenerator.set(generation);
        sampleLatencyNanos = DatabaseDescriptor.getReadRpcTimeout() / 2;

        CachingOptions caching = metadata.getCaching();

        logger.info("Initializing {}.{}", keyspace.getName(), name);

        // scan for sstables corresponding to this cf and load them
        data = new DataTracker(this);

        if (loadSSTables)
        {
            Directories.SSTableLister sstableFiles = directories.sstableLister().skipTemporary(true);
            Collection<SSTableReader> sstables = SSTableReader.openAll(sstableFiles.list().entrySet(), metadata, this.partitioner);
            data.addInitialSSTables(sstables);
        }

        if (caching.keyCache.isEnabled())
            CacheService.instance.keyCache.loadSaved(this);

        // compaction strategy should be created after the CFS has been prepared
        this.compactionStrategyWrapper = new WrappingCompactionStrategy(this);

        if (maxCompactionThreshold.value() <= 0 || minCompactionThreshold.value() <=0)
        {
            logger.warn("Disabling compaction strategy by setting compaction thresholds to 0 is deprecated, set the compaction option 'enabled' to 'false' instead.");
            this.compactionStrategyWrapper.disable();
        }

        // create the private ColumnFamilyStores for the secondary column indexes
        for (ColumnDefinition info : metadata.allColumns())
        {
            if (info.getIndexType() != null)
                indexManager.addIndexedColumn(info);
        }

        // register the mbean
        String type = this.partitioner instanceof LocalPartitioner ? "IndexColumnFamilies" : "ColumnFamilies";
        mbeanName = "org.apache.cassandra.db:type=" + type + ",keyspace=" + this.keyspace.getName() + ",columnfamily=" + name;
        try
        {
            MBeanServer mbs = ManagementFactory.getPlatformMBeanServer();
            ObjectName nameObj = new ObjectName(mbeanName);
            mbs.registerMBean(this, nameObj);
        }
        catch (Exception e)
        {
            throw new RuntimeException(e);
        }
        logger.debug("retryPolicy for {} is {}", name, this.metadata.getSpeculativeRetry());
        latencyCalculator = ScheduledExecutors.optionalTasks.scheduleWithFixedDelay(new Runnable()
        {
            public void run()
            {
                SpeculativeRetry retryPolicy = ColumnFamilyStore.this.metadata.getSpeculativeRetry();
                switch (retryPolicy.type)
                {
                    case PERCENTILE:
                        // get percentile in nanos
                        assert metric.coordinatorReadLatency.durationUnit() == TimeUnit.MICROSECONDS;
                        sampleLatencyNanos = (long) (metric.coordinatorReadLatency.getSnapshot().getValue(retryPolicy.value) * 1000d);
                        break;
                    case CUSTOM:
                        // convert to nanos, since configuration is in millisecond
                        sampleLatencyNanos = (long) (retryPolicy.value * 1000d * 1000d);
                        break;
                    default:
                        sampleLatencyNanos = Long.MAX_VALUE;
                        break;
                }
            }
        }, DatabaseDescriptor.getReadRpcTimeout(), DatabaseDescriptor.getReadRpcTimeout(), TimeUnit.MILLISECONDS);
    }

    /** call when dropping or renaming a CF. Performs mbean housekeeping and invalidates CFS to other operations */
    public void invalidate()
    {
        // disable and cancel in-progress compactions before invalidating
        valid = false;

        try
        {
            unregisterMBean();
        }
        catch (Exception e)
        {
            JVMStabilityInspector.inspectThrowable(e);
            // this shouldn't block anything.
            logger.warn("Failed unregistering mbean: {}", mbeanName, e);
        }

        latencyCalculator.cancel(false);
        SystemKeyspace.removeTruncationRecord(metadata.cfId);
        data.unreferenceSSTables();
        indexManager.invalidate();

        invalidateCaches();
    }

    /**
     * Removes every SSTable in the directory from the DataTracker's view.
     * @param directory the unreadable directory, possibly with SSTables in it, but not necessarily.
     */
    void maybeRemoveUnreadableSSTables(File directory)
    {
        data.removeUnreadableSSTables(directory);
    }

    void unregisterMBean() throws MalformedObjectNameException, InstanceNotFoundException, MBeanRegistrationException
    {
        MBeanServer mbs = ManagementFactory.getPlatformMBeanServer();
        ObjectName nameObj = new ObjectName(mbeanName);
        if (mbs.isRegistered(nameObj))
            mbs.unregisterMBean(nameObj);

        // unregister metrics
        metric.release();
    }

    public long getMinRowSize()
    {
        return metric.minRowSize.value();
    }

    public long getMaxRowSize()
    {
        return metric.maxRowSize.value();
    }

    public long getMeanRowSize()
    {
        return metric.meanRowSize.value();
    }

    public int getMeanColumns()
    {
        return data.getMeanColumns();
    }

    public static ColumnFamilyStore createColumnFamilyStore(Keyspace keyspace, String columnFamily, boolean loadSSTables)
    {
        return createColumnFamilyStore(keyspace, columnFamily, StorageService.getPartitioner(), Schema.instance.getCFMetaData(keyspace.getName(), columnFamily), loadSSTables);
    }

    public static ColumnFamilyStore createColumnFamilyStore(Keyspace keyspace, String columnFamily, IPartitioner partitioner, CFMetaData metadata)
    {
        return createColumnFamilyStore(keyspace, columnFamily, partitioner, metadata, true);
    }

    private static synchronized ColumnFamilyStore createColumnFamilyStore(Keyspace keyspace,
                                                                         String columnFamily,
                                                                         IPartitioner partitioner,
                                                                         CFMetaData metadata,
                                                                         boolean loadSSTables)
    {
        // get the max generation number, to prevent generation conflicts
        Directories directories = new Directories(metadata);
        Directories.SSTableLister lister = directories.sstableLister().includeBackups(true);
        List<Integer> generations = new ArrayList<Integer>();
        for (Map.Entry<Descriptor, Set<Component>> entry : lister.list().entrySet())
        {
            Descriptor desc = entry.getKey();
            generations.add(desc.generation);
            if (!desc.isCompatible())
                throw new RuntimeException(String.format("Incompatible SSTable found. Current version %s is unable to read file: %s. Please run upgradesstables.",
                                                          Descriptor.Version.CURRENT, desc));
        }
        Collections.sort(generations);
        int value = (generations.size() > 0) ? (generations.get(generations.size() - 1)) : 0;

        return new ColumnFamilyStore(keyspace, columnFamily, partitioner, value, metadata, directories, loadSSTables);
    }

    /**
     * Removes unnecessary files from the cf directory at startup: these include temp files, orphans, zero-length files
     * and compacted sstables. Files that cannot be recognized will be ignored.
     */
    public static void scrubDataDirectories(CFMetaData metadata)
    {
        Directories directories = new Directories(metadata);

        // remove any left-behind SSTables from failed/stalled streaming
        FileFilter filter = new FileFilter()
        {
            public boolean accept(File pathname)
            {
                return pathname.toString().endsWith(StreamLockfile.FILE_EXT);
            }
        };
        for (File dir : directories.getCFDirectories())
        {
            File[] lockfiles = dir.listFiles(filter);
            // lock files can be null if I/O error happens
            if (lockfiles == null || lockfiles.length == 0)
                continue;
            logger.info("Removing SSTables from failed streaming session. Found {} files to cleanup.", lockfiles.length);

            for (File lockfile : lockfiles)
            {
                StreamLockfile streamLockfile = new StreamLockfile(lockfile);
                streamLockfile.cleanup();
                streamLockfile.delete();
            }
        }

        logger.debug("Removing compacted SSTable files from {} (see http://wiki.apache.org/cassandra/MemtableSSTable)", metadata.cfName);

        for (Map.Entry<Descriptor,Set<Component>> sstableFiles : directories.sstableLister().list().entrySet())
        {
            Descriptor desc = sstableFiles.getKey();
            Set<Component> components = sstableFiles.getValue();

            if (desc.type.isTemporary)
            {
                SSTable.delete(desc, components);
                continue;
            }

            File dataFile = new File(desc.filenameFor(Component.DATA));
            if (components.contains(Component.DATA) && dataFile.length() > 0)
                // everything appears to be in order... moving on.
                continue;

            // missing the DATA file! all components are orphaned
            logger.warn("Removing orphans for {}: {}", desc, components);
            for (Component component : components)
            {
                FileUtils.deleteWithConfirm(desc.filenameFor(component));
            }
        }

        // cleanup incomplete saved caches
        Pattern tmpCacheFilePattern = Pattern.compile(metadata.ksName + "-" + metadata.cfName + "-(Key|Row)Cache.*\\.tmp$");
        File dir = new File(DatabaseDescriptor.getSavedCachesLocation());

        if (dir.exists())
        {
            assert dir.isDirectory();
            for (File file : dir.listFiles())
                if (tmpCacheFilePattern.matcher(file.getName()).matches())
                    if (!file.delete())
                        logger.warn("could not delete {}", file.getAbsolutePath());
        }

        // also clean out any index leftovers.
        for (ColumnDefinition def : metadata.allColumns())
        {
            if (def.isIndexed())
            {
                CellNameType indexComparator = SecondaryIndex.getIndexComparator(metadata, def);
                if (indexComparator != null)
                {
                    CFMetaData indexMetadata = CFMetaData.newIndexMetadata(metadata, def, indexComparator);
                    scrubDataDirectories(indexMetadata);
                }
            }
        }
    }

    /**
     * Replacing compacted sstables is atomic as far as observers of DataTracker are concerned, but not on the
     * filesystem: first the new sstables are renamed to "live" status (i.e., the tmp marker is removed), then
     * their ancestors are removed.
     *
     * If an unclean shutdown happens at the right time, we can thus end up with both the new ones and their
     * ancestors "live" in the system.  This is harmless for normal data, but for counters it can cause overcounts.
     *
     * To prevent this, we record sstables being compacted in the system keyspace.  If we find unfinished
     * compactions, we remove the new ones (since those may be incomplete -- under LCS, we may create multiple
     * sstables from any given ancestor).
     */
    public static void removeUnfinishedCompactionLeftovers(CFMetaData metadata, Map<Integer, UUID> unfinishedCompactions)
    {
        Directories directories = new Directories(metadata);

        Set<Integer> allGenerations = new HashSet<>();
        for (Descriptor desc : directories.sstableLister().list().keySet())
            allGenerations.add(desc.generation);

        // sanity-check unfinishedCompactions
        Set<Integer> unfinishedGenerations = unfinishedCompactions.keySet();
        if (!allGenerations.containsAll(unfinishedGenerations))
        {
            HashSet<Integer> missingGenerations = new HashSet<>(unfinishedGenerations);
            missingGenerations.removeAll(allGenerations);
            logger.debug("Unfinished compactions of {}.{} reference missing sstables of generations {}",
                         metadata.ksName, metadata.cfName, missingGenerations);
        }

        // remove new sstables from compactions that didn't complete, and compute
        // set of ancestors that shouldn't exist anymore
        Set<Integer> completedAncestors = new HashSet<>();
        for (Map.Entry<Descriptor, Set<Component>> sstableFiles : directories.sstableLister().skipTemporary(true).list().entrySet())
        {
            Descriptor desc = sstableFiles.getKey();

            Set<Integer> ancestors;
            try
            {
                CompactionMetadata compactionMetadata = (CompactionMetadata) desc.getMetadataSerializer().deserialize(desc, MetadataType.COMPACTION);
                ancestors = compactionMetadata.ancestors;
            }
            catch (IOException e)
            {
                throw new FSReadError(e, desc.filenameFor(Component.STATS));
            }
            catch (NullPointerException e)
            {
                throw new FSReadError(e, "Failed to remove unfinished compaction leftovers (file: " + desc.filenameFor(Component.STATS) + ").  See log for details.");
            }

            if (!ancestors.isEmpty()
                && unfinishedGenerations.containsAll(ancestors)
                && allGenerations.containsAll(ancestors))
            {
                // any of the ancestors would work, so we'll just lookup the compaction task ID with the first one
                UUID compactionTaskID = unfinishedCompactions.get(ancestors.iterator().next());
                assert compactionTaskID != null;
                logger.debug("Going to delete unfinished compaction product {}", desc);
                SSTable.delete(desc, sstableFiles.getValue());
                SystemKeyspace.finishCompaction(compactionTaskID);
            }
            else
            {
                completedAncestors.addAll(ancestors);
            }
        }

        // remove old sstables from compactions that did complete
        for (Map.Entry<Descriptor, Set<Component>> sstableFiles : directories.sstableLister().list().entrySet())
        {
            Descriptor desc = sstableFiles.getKey();
            if (completedAncestors.contains(desc.generation))
            {
                // if any of the ancestors were participating in a compaction, finish that compaction
                logger.debug("Going to delete leftover compaction ancestor {}", desc);
                SSTable.delete(desc, sstableFiles.getValue());
                UUID compactionTaskID = unfinishedCompactions.get(desc.generation);
                if (compactionTaskID != null)
                    SystemKeyspace.finishCompaction(unfinishedCompactions.get(desc.generation));
            }
        }
    }

    // must be called after all sstables are loaded since row cache merges all row versions
    public void initRowCache()
    {
        if (!isRowCacheEnabled())
            return;

        long start = System.nanoTime();

        int cachedRowsRead = CacheService.instance.rowCache.loadSaved(this);
        if (cachedRowsRead > 0)
            logger.info("Completed loading ({} ms; {} keys) row cache for {}.{}",
                        TimeUnit.NANOSECONDS.toMillis(System.nanoTime() - start),
                        cachedRowsRead,
                        keyspace.getName(),
                        name);
    }

    public void initCounterCache()
    {
        if (!metadata.isCounter() || CacheService.instance.counterCache.getCapacity() == 0)
            return;

        long start = System.nanoTime();

        int cachedShardsRead = CacheService.instance.counterCache.loadSaved(this);
        if (cachedShardsRead > 0)
            logger.info("Completed loading ({} ms; {} shards) counter cache for {}.{}",
                        TimeUnit.NANOSECONDS.toMillis(System.nanoTime() - start),
                        cachedShardsRead,
                        keyspace.getName(),
                        name);
    }

    /**
     * See #{@code StorageService.loadNewSSTables(String, String)} for more info
     *
     * @param ksName The keyspace name
     * @param cfName The columnFamily name
     */
    public static synchronized void loadNewSSTables(String ksName, String cfName)
    {
        /** ks/cf existence checks will be done by open and getCFS methods for us */
        Keyspace keyspace = Keyspace.open(ksName);
        keyspace.getColumnFamilyStore(cfName).loadNewSSTables();
    }

    /**
     * #{@inheritDoc}
     */
    public synchronized void loadNewSSTables()
    {
        logger.info("Loading new SSTables for {}/{}...", keyspace.getName(), name);

        Set<Descriptor> currentDescriptors = new HashSet<Descriptor>();
        for (SSTableReader sstable : data.getView().sstables)
            currentDescriptors.add(sstable.descriptor);
        Set<SSTableReader> newSSTables = new HashSet<SSTableReader>();

        Directories.SSTableLister lister = directories.sstableLister().skipTemporary(true);
        for (Map.Entry<Descriptor, Set<Component>> entry : lister.list().entrySet())
        {
            Descriptor descriptor = entry.getKey();

            if (currentDescriptors.contains(descriptor))
                continue; // old (initialized) SSTable found, skipping
            if (descriptor.type.isTemporary) // in the process of being written
                continue;

            if (!descriptor.isCompatible())
                throw new RuntimeException(String.format("Can't open incompatible SSTable! Current version %s, found file: %s",
                                                         Descriptor.Version.CURRENT,
                                                         descriptor));

            // force foreign sstables to level 0
            try
            {
                if (new File(descriptor.filenameFor(Component.STATS)).exists())
                    descriptor.getMetadataSerializer().mutateLevel(descriptor, 0);
            }
            catch (IOException e)
            {
                SSTableReader.logOpenException(entry.getKey(), e);
                continue;
            }

            // Increment the generation until we find a filename that doesn't exist. This is needed because the new
            // SSTables that are being loaded might already use these generation numbers.
            Descriptor newDescriptor;
            do
            {
                newDescriptor = new Descriptor(descriptor.version,
                                               descriptor.directory,
                                               descriptor.ksname,
                                               descriptor.cfname,
                                               fileIndexGenerator.incrementAndGet(),
                                               Descriptor.Type.FINAL);
            }
            while (new File(newDescriptor.filenameFor(Component.DATA)).exists());

            logger.info("Renaming new SSTable {} to {}", descriptor, newDescriptor);
            SSTableWriter.rename(descriptor, newDescriptor, entry.getValue());

            SSTableReader reader;
            try
            {
                reader = SSTableReader.open(newDescriptor, entry.getValue(), metadata, partitioner);
            }
            catch (IOException e)
            {
                SSTableReader.logOpenException(entry.getKey(), e);
                continue;
            }
            newSSTables.add(reader);
        }

        if (newSSTables.isEmpty())
        {
            logger.info("No new SSTables were found for {}/{}", keyspace.getName(), name);
            return;
        }

        logger.info("Loading new SSTables and building secondary indexes for {}/{}: {}", keyspace.getName(), name, newSSTables);

        try (Refs<SSTableReader> refs = Refs.ref(newSSTables))
        {
            data.addSSTables(newSSTables);
            indexManager.maybeBuildSecondaryIndexes(newSSTables, indexManager.allIndexesNames());
        }

        logger.info("Done loading load new SSTables for {}/{}", keyspace.getName(), name);
    }

    public void rebuildSecondaryIndex(String idxName)
    {
        rebuildSecondaryIndex(keyspace.getName(), metadata.cfName, idxName);
    }

    public static void rebuildSecondaryIndex(String ksName, String cfName, String... idxNames)
    {
        ColumnFamilyStore cfs = Keyspace.open(ksName).getColumnFamilyStore(cfName);

        Set<String> indexes = new HashSet<String>(Arrays.asList(idxNames));

        Collection<SSTableReader> sstables = cfs.getSSTables();

        try (Refs<SSTableReader> refs = Refs.ref(sstables))
        {
            cfs.indexManager.setIndexRemoved(indexes);
            logger.info(String.format("User Requested secondary index re-build for %s/%s indexes", ksName, cfName));
            cfs.indexManager.maybeBuildSecondaryIndexes(sstables, indexes);
            cfs.indexManager.setIndexBuilt(indexes);
        }
    }

    public String getColumnFamilyName()
    {
        return name;
    }

    public String getTempSSTablePath(File directory)
    {
        return getTempSSTablePath(directory, Descriptor.Version.CURRENT);
    }

    private String getTempSSTablePath(File directory, Descriptor.Version version)
    {
        Descriptor desc = new Descriptor(version,
                                         directory,
                                         keyspace.getName(),
                                         name,
                                         fileIndexGenerator.incrementAndGet(),
                                         Descriptor.Type.TEMP);
        return desc.filenameFor(Component.DATA);
    }

    /**
     * Switches the memtable iff the live memtable is the one provided
     *
     * @param memtable
     */
    public Future<?> switchMemtableIfCurrent(Memtable memtable)
    {
        synchronized (data)
        {
            if (data.getView().getCurrentMemtable() == memtable)
                return switchMemtable();
        }
        return Futures.immediateFuture(null);
    }

    /*
     * switchMemtable puts Memtable.getSortedContents on the writer executor.  When the write is complete,
     * we turn the writer into an SSTableReader and add it to ssTables where it is available for reads.
     * This method does not block except for synchronizing on DataTracker, but the Future it returns will
     * not complete until the Memtable (and all prior Memtables) have been successfully flushed, and the CL
     * marked clean up to the position owned by the Memtable.
     */
    public ListenableFuture<?> switchMemtable()
    {
        synchronized (data)
        {
            logFlush();
            Flush flush = new Flush(false);
            flushExecutor.execute(flush);
            ListenableFutureTask<?> task = ListenableFutureTask.create(flush.postFlush, null);
            postFlushExecutor.submit(task);
            return task;
        }
    }

    // print out size of all memtables we're enqueuing
    private void logFlush()
    {
        // reclaiming includes that which we are GC-ing;
        float onHeapRatio = 0, offHeapRatio = 0;
        long onHeapTotal = 0, offHeapTotal = 0;
        Memtable memtable = getDataTracker().getView().getCurrentMemtable();
        onHeapRatio +=  memtable.getAllocator().onHeap().ownershipRatio();
        offHeapRatio += memtable.getAllocator().offHeap().ownershipRatio();
        onHeapTotal += memtable.getAllocator().onHeap().owns();
        offHeapTotal += memtable.getAllocator().offHeap().owns();

        for (SecondaryIndex index : indexManager.getIndexes())
        {
            if (index.getIndexCfs() != null)
            {
                MemtableAllocator allocator = index.getIndexCfs().getDataTracker().getView().getCurrentMemtable().getAllocator();
                onHeapRatio += allocator.onHeap().ownershipRatio();
                offHeapRatio += allocator.offHeap().ownershipRatio();
                onHeapTotal += allocator.onHeap().owns();
                offHeapTotal += allocator.offHeap().owns();
            }
        }

        logger.info("Enqueuing flush of {}: {}", name, String.format("%d (%.0f%%) on-heap, %d (%.0f%%) off-heap",
                                                                     onHeapTotal, onHeapRatio * 100, offHeapTotal, offHeapRatio * 100));
    }


    public ListenableFuture<?> forceFlush()
    {
        return forceFlush(null);
    }

    /**
     * Flush if there is unflushed data that was written to the CommitLog before @param flushIfDirtyBefore
     * (inclusive).  If @param flushIfDirtyBefore is null, flush if there is any unflushed data.
     *
     * @return a Future such that when the future completes, all data inserted before forceFlush was called,
     * will be flushed.
     */
    public ListenableFuture<?> forceFlush(ReplayPosition flushIfDirtyBefore)
    {
        // we synchronize on the data tracker to ensure we don't race against other calls to switchMemtable(),
        // unnecessarily queueing memtables that are about to be made clean
        synchronized (data)
        {
            // during index build, 2ary index memtables can be dirty even if parent is not.  if so,
            // we want to flush the 2ary index ones too.
            boolean clean = true;
            for (ColumnFamilyStore cfs : concatWithIndexes())
                clean &= cfs.data.getView().getCurrentMemtable().isCleanAfter(flushIfDirtyBefore);

            if (clean)
            {
                // We could have a memtable for this column family that is being
                // flushed. Make sure the future returned wait for that so callers can
                // assume that any data inserted prior to the call are fully flushed
                // when the future returns (see #5241).
                ListenableFutureTask<?> task = ListenableFutureTask.create(new Runnable()
                {
                    public void run()
                    {
                        logger.debug("forceFlush requested but everything is clean in {}", name);
                    }
                }, null);
                postFlushExecutor.execute(task);
                return task;
            }

            return switchMemtable();
        }
    }

    public void forceBlockingFlush()
    {
        FBUtilities.waitOnFuture(forceFlush());
    }

    /**
     * Both synchronises custom secondary indexes and provides ordering guarantees for futures on switchMemtable/flush
     * etc, which expect to be able to wait until the flush (and all prior flushes) requested have completed.
     */
    private final class PostFlush implements Runnable
    {
        final boolean flushSecondaryIndexes;
        final OpOrder.Barrier writeBarrier;
        final CountDownLatch latch = new CountDownLatch(1);
        final ReplayPosition lastReplayPosition;

        private PostFlush(boolean flushSecondaryIndexes, OpOrder.Barrier writeBarrier, ReplayPosition lastReplayPosition)
        {
            this.writeBarrier = writeBarrier;
            this.flushSecondaryIndexes = flushSecondaryIndexes;
            this.lastReplayPosition = lastReplayPosition;
        }

        public void run()
        {
            writeBarrier.await();

            /**
             * we can flush 2is as soon as the barrier completes, as they will be consistent with (or ahead of) the
             * flushed memtables and CL position, which is as good as we can guarantee.
             * TODO: SecondaryIndex should support setBarrier(), so custom implementations can co-ordinate exactly
             * with CL as we do with memtables/CFS-backed SecondaryIndexes.
             */

            if (flushSecondaryIndexes)
            {
                for (SecondaryIndex index : indexManager.getIndexesNotBackedByCfs())
                {
                    // flush any non-cfs backed indexes
                    logger.info("Flushing SecondaryIndex {}", index);
                    index.forceBlockingFlush();
                }
            }

            try
            {
                // we wait on the latch for the lastReplayPosition to be set, and so that waiters
                // on this task can rely on all prior flushes being complete
                latch.await();
            }
            catch (InterruptedException e)
            {
                throw new IllegalStateException();
            }

            // must check lastReplayPosition != null because Flush may find that all memtables are clean
            // and so not set a lastReplayPosition
            if (lastReplayPosition != null)
            {
                CommitLog.instance.discardCompletedSegments(metadata.cfId, lastReplayPosition);
            }

            metric.pendingFlushes.dec();
        }
    }

    /**
     * Should only be constructed/used from switchMemtable() or truncate(), with ownership of the DataTracker monitor.
     * In the constructor the current memtable(s) are swapped, and a barrier on outstanding writes is issued;
     * when run by the flushWriter the barrier is waited on to ensure all outstanding writes have completed
     * before all memtables are immediately written, and the CL is either immediately marked clean or, if
     * there are custom secondary indexes, the post flush clean up is left to update those indexes and mark
     * the CL clean
     */
    private final class Flush implements Runnable
    {
        final OpOrder.Barrier writeBarrier;
        final List<Memtable> memtables;
        final PostFlush postFlush;
        final boolean truncate;

        private Flush(boolean truncate)
        {
            // if true, we won't flush, we'll just wait for any outstanding writes, switch the memtable, and discard
            this.truncate = truncate;

            metric.pendingFlushes.inc();
            /**
             * To ensure correctness of switch without blocking writes, run() needs to wait for all write operations
             * started prior to the switch to complete. We do this by creating a Barrier on the writeOrdering
             * that all write operations register themselves with, and assigning this barrier to the memtables,
             * after which we *.issue()* the barrier. This barrier is used to direct write operations started prior
             * to the barrier.issue() into the memtable we have switched out, and any started after to its replacement.
             * In doing so it also tells the write operations to update the lastReplayPosition of the memtable, so
             * that we know the CL position we are dirty to, which can be marked clean when we complete.
             */
            writeBarrier = keyspace.writeOrder.newBarrier();
            memtables = new ArrayList<>();

            // submit flushes for the memtable for any indexed sub-cfses, and our own
            AtomicReference<ReplayPosition> lastReplayPositionHolder = new AtomicReference<>();
            for (ColumnFamilyStore cfs : concatWithIndexes())
            {
                // switch all memtables, regardless of their dirty status, setting the barrier
                // so that we can reach a coordinated decision about cleanliness once they
                // are no longer possible to be modified
                Memtable mt = cfs.data.switchMemtable(truncate);
                mt.setDiscarding(writeBarrier, lastReplayPositionHolder);
                memtables.add(mt);
            }

            // we now attempt to define the lastReplayPosition; we do this by grabbing the current limit from the CL
            // and attempting to set the holder to this value. at the same time all writes to the memtables are
            // also maintaining this value, so if somebody sneaks ahead of us somehow (should be rare) we simply retry,
            // so that we know all operations prior to the position have not reached it yet
            ReplayPosition lastReplayPosition;
            while (true)
            {
                lastReplayPosition = new Memtable.LastReplayPosition(CommitLog.instance.getContext());
                ReplayPosition currentLast = lastReplayPositionHolder.get();
                if ((currentLast == null || currentLast.compareTo(lastReplayPosition) <= 0)
                    && lastReplayPositionHolder.compareAndSet(currentLast, lastReplayPosition))
                    break;
            }

            // we then issue the barrier; this lets us wait for all operations started prior to the barrier to complete;
            // since this happens after wiring up the lastReplayPosition, we also know all operations with earlier
            // replay positions have also completed, i.e. the memtables are done and ready to flush
            writeBarrier.issue();
            postFlush = new PostFlush(!truncate, writeBarrier, lastReplayPosition);
        }

        public void run()
        {
            // mark writes older than the barrier as blocking progress, permitting them to exceed our memory limit
            // if they are stuck waiting on it, then wait for them all to complete
            writeBarrier.markBlocking();
            writeBarrier.await();

            // mark all memtables as flushing, removing them from the live memtable list, and
            // remove any memtables that are already clean from the set we need to flush
            Iterator<Memtable> iter = memtables.iterator();
            while (iter.hasNext())
            {
                Memtable memtable = iter.next();
                memtable.cfs.data.markFlushing(memtable);
                if (memtable.isClean() || truncate)
                {
                    memtable.cfs.replaceFlushed(memtable, null);
                    reclaim(memtable);
                    iter.remove();
                }
            }

            if (memtables.isEmpty())
            {
                postFlush.latch.countDown();
                return;
            }

            metric.memtableSwitchCount.inc();

            for (Memtable memtable : memtables)
            {
                // flush the memtable
                MoreExecutors.sameThreadExecutor().execute(memtable.flushRunnable());
                reclaim(memtable);
            }

            // signal the post-flush we've done our work
            postFlush.latch.countDown();
        }

        private void reclaim(final Memtable memtable)
        {
            // issue a read barrier for reclaiming the memory, and offload the wait to another thread
            final OpOrder.Barrier readBarrier = readOrdering.newBarrier();
            readBarrier.issue();
            reclaimExecutor.execute(new WrappedRunnable()
            {
                public void runMayThrow() throws InterruptedException, ExecutionException
                {
                    readBarrier.await();
                    memtable.setDiscarded();
                }
            });
        }
    }

    /**
     * Finds the largest memtable, as a percentage of *either* on- or off-heap memory limits, and immediately
     * queues it for flushing. If the memtable selected is flushed before this completes, no work is done.
     */
    public static class FlushLargestColumnFamily implements Runnable
    {
        public void run()
        {
            float largestRatio = 0f;
            Memtable largest = null;
            float liveOnHeap = 0, liveOffHeap = 0;
            for (ColumnFamilyStore cfs : ColumnFamilyStore.all())
            {
                // we take a reference to the current main memtable for the CF prior to snapping its ownership ratios
                // to ensure we have some ordering guarantee for performing the switchMemtableIf(), i.e. we will only
                // swap if the memtables we are measuring here haven't already been swapped by the time we try to swap them
                Memtable current = cfs.getDataTracker().getView().getCurrentMemtable();

                // find the total ownership ratio for the memtable and all SecondaryIndexes owned by this CF,
                // both on- and off-heap, and select the largest of the two ratios to weight this CF
                float onHeap = 0f, offHeap = 0f;
                onHeap += current.getAllocator().onHeap().ownershipRatio();
                offHeap += current.getAllocator().offHeap().ownershipRatio();

                for (SecondaryIndex index : cfs.indexManager.getIndexes())
                {
                    if (index.getIndexCfs() != null)
                    {
                        MemtableAllocator allocator = index.getIndexCfs().getDataTracker().getView().getCurrentMemtable().getAllocator();
                        onHeap += allocator.onHeap().ownershipRatio();
                        offHeap += allocator.offHeap().ownershipRatio();
                    }
                }

                float ratio = Math.max(onHeap, offHeap);
                if (ratio > largestRatio)
                {
                    largest = current;
                    largestRatio = ratio;
                }

                liveOnHeap += onHeap;
                liveOffHeap += offHeap;
            }

            if (largest != null)
            {
                float usedOnHeap = Memtable.MEMORY_POOL.onHeap.usedRatio();
                float usedOffHeap = Memtable.MEMORY_POOL.offHeap.usedRatio();
                float flushingOnHeap = Memtable.MEMORY_POOL.onHeap.reclaimingRatio();
                float flushingOffHeap = Memtable.MEMORY_POOL.offHeap.reclaimingRatio();
                float thisOnHeap = largest.getAllocator().onHeap().ownershipRatio();
                float thisOffHeap = largest.getAllocator().onHeap().ownershipRatio();
                logger.info("Flushing largest {} to free up room. Used total: {}, live: {}, flushing: {}, this: {}",
                            largest.cfs, ratio(usedOnHeap, usedOffHeap), ratio(liveOnHeap, liveOffHeap),
                            ratio(flushingOnHeap, flushingOffHeap), ratio(thisOnHeap, thisOffHeap));
                largest.cfs.switchMemtableIfCurrent(largest);
            }
        }
    }

    private static String ratio(float onHeap, float offHeap)
    {
        return String.format("%.2f/%.2f", onHeap, offHeap);
    }

    public void maybeUpdateRowCache(DecoratedKey key)
    {
        if (!isRowCacheEnabled())
            return;

        RowCacheKey cacheKey = new RowCacheKey(metadata.cfId, key);
        invalidateCachedRow(cacheKey);
    }

    /**
     * Insert/Update the column family for this key.
     * Caller is responsible for acquiring Keyspace.switchLock
     * param @ lock - lock that needs to be used.
     * param @ key - key for update/insert
     * param @ columnFamily - columnFamily changes
     */
    public void apply(DecoratedKey key, ColumnFamily columnFamily, SecondaryIndexManager.Updater indexer, OpOrder.Group opGroup, ReplayPosition replayPosition)
    {
        long start = System.nanoTime();
        Memtable mt = data.getMemtableFor(opGroup, replayPosition);
        final long timeDelta = mt.put(key, columnFamily, indexer, opGroup);
        maybeUpdateRowCache(key);
        metric.samplers.get(Sampler.WRITES).addSample(key.getKey(), key.hashCode(), 1);
        metric.writeLatency.addNano(System.nanoTime() - start);
        if(timeDelta < Long.MAX_VALUE)
            metric.colUpdateTimeDeltaHistogram.update(timeDelta);
    }

    /**
     * Purges gc-able top-level and range tombstones, returning `cf` if there are any columns or tombstones left,
     * null otherwise.
     * @param gcBefore a timestamp (in seconds); tombstones with a localDeletionTime before this will be purged
     */
    public static ColumnFamily removeDeletedCF(ColumnFamily cf, int gcBefore)
    {
        // purge old top-level and range tombstones
        cf.purgeTombstones(gcBefore);

        // if there are no columns or tombstones left, return null
        return !cf.hasColumns() && !cf.isMarkedForDelete() ? null : cf;
    }

    /**
     * Removes deleted columns and purges gc-able tombstones.
     * @return an updated `cf` if any columns or tombstones remain, null otherwise
     */
    public static ColumnFamily removeDeleted(ColumnFamily cf, int gcBefore)
    {
        return removeDeleted(cf, gcBefore, SecondaryIndexManager.nullUpdater);
    }

    /*
     This is complicated because we need to preserve deleted columns and columnfamilies
     until they have been deleted for at least GC_GRACE_IN_SECONDS.  But, we do not need to preserve
     their contents; just the object itself as a "tombstone" that can be used to repair other
     replicas that do not know about the deletion.
     */
    public static ColumnFamily removeDeleted(ColumnFamily cf, int gcBefore, SecondaryIndexManager.Updater indexer)
    {
        if (cf == null)
        {
            return null;
        }

        return removeDeletedCF(removeDeletedColumnsOnly(cf, gcBefore, indexer), gcBefore);
    }

    /**
     * Removes only per-cell tombstones, cells that are shadowed by a row-level or range tombstone, or
     * columns that have been dropped from the schema (for CQL3 tables only).
     * @return the updated ColumnFamily
     */
    public static ColumnFamily removeDeletedColumnsOnly(ColumnFamily cf, int gcBefore, SecondaryIndexManager.Updater indexer)
    {
        BatchRemoveIterator<Cell> iter = cf.batchRemoveIterator();
        DeletionInfo.InOrderTester tester = cf.inOrderDeletionTester();
        boolean hasDroppedColumns = !cf.metadata.getDroppedColumns().isEmpty();
        while (iter.hasNext())
        {
            Cell c = iter.next();
            // remove columns if
            // (a) the column itself is gcable or
            // (b) the column is shadowed by a CF tombstone
            // (c) the column has been dropped from the CF schema (CQL3 tables only)
            if (c.getLocalDeletionTime() < gcBefore || tester.isDeleted(c) || (hasDroppedColumns && isDroppedColumn(c, cf.metadata())))
            {
                iter.remove();
                indexer.remove(c);
            }
        }
        iter.commit();
        return cf;
    }

    // returns true if
    // 1. this column has been dropped from schema and
    // 2. if it has been re-added since then, this particular column was inserted before the last drop
    private static boolean isDroppedColumn(Cell c, CFMetaData meta)
    {
        Long droppedAt = meta.getDroppedColumns().get(c.name().cql3ColumnName(meta));
        return droppedAt != null && c.timestamp() <= droppedAt;
    }

    private void removeDroppedColumns(ColumnFamily cf)
    {
        if (cf == null || cf.metadata.getDroppedColumns().isEmpty())
            return;

        BatchRemoveIterator<Cell> iter = cf.batchRemoveIterator();
        while (iter.hasNext())
            if (isDroppedColumn(iter.next(), metadata))
                iter.remove();
        iter.commit();
    }

    /**
     * @param sstables
     * @return sstables whose key range overlaps with that of the given sstables, not including itself.
     * (The given sstables may or may not overlap with each other.)
     */
    public Collection<SSTableReader> getOverlappingSSTables(Iterable<SSTableReader> sstables)
    {
        logger.debug("Checking for sstables overlapping {}", sstables);

        // a normal compaction won't ever have an empty sstables list, but we create a skeleton
        // compaction controller for streaming, and that passes an empty list.
        if (!sstables.iterator().hasNext())
            return ImmutableSet.of();

        DataTracker.SSTableIntervalTree tree = data.getView().intervalTree;

        Set<SSTableReader> results = null;
        for (SSTableReader sstable : sstables)
        {
            Set<SSTableReader> overlaps = ImmutableSet.copyOf(tree.search(Interval.<RowPosition, SSTableReader>create(sstable.first, sstable.last)));
            results = results == null ? overlaps : Sets.union(results, overlaps).immutableCopy();
        }
        results = Sets.difference(results, ImmutableSet.copyOf(sstables));

        return results;
    }

    /**
     * like getOverlappingSSTables, but acquires references before returning
     */
    public Refs<SSTableReader> getAndReferenceOverlappingSSTables(Iterable<SSTableReader> sstables)
    {
        while (true)
        {
            Iterable<SSTableReader> overlapped = getOverlappingSSTables(sstables);
            Refs<SSTableReader> refs = Refs.tryRef(overlapped);
            if (refs != null)
                return refs;
        }
    }

    /*
     * Called after a BinaryMemtable flushes its in-memory data, or we add a file
     * via bootstrap. This information is cached in the ColumnFamilyStore.
     * This is useful for reads because the ColumnFamilyStore first looks in
     * the in-memory store and the into the disk to find the key. If invoked
     * during recoveryMode the onMemtableFlush() need not be invoked.
     *
     * param @ filename - filename just flushed to disk
     */
    public void addSSTable(SSTableReader sstable)
    {
        assert sstable.getColumnFamilyName().equals(name);
        addSSTables(Arrays.asList(sstable));
    }

    public void addSSTables(Collection<SSTableReader> sstables)
    {
        data.addSSTables(sstables);
        CompactionManager.instance.submitBackground(this);
    }

    /**
     * Calculate expected file size of SSTable after compaction.
     *
     * If operation type is {@code CLEANUP} and we're not dealing with an index sstable,
     * then we calculate expected file size with checking token range to be eliminated.
     *
     * Otherwise, we just add up all the files' size, which is the worst case file
     * size for compaction of all the list of files given.
     *
     * @param sstables SSTables to calculate expected compacted file size
     * @param operation Operation type
     * @return Expected file size of SSTable after compaction
     */
    public long getExpectedCompactedFileSize(Iterable<SSTableReader> sstables, OperationType operation)
    {
        if (operation != OperationType.CLEANUP || isIndex())
        {
            return SSTableReader.getTotalBytes(sstables);
        }

        // cleanup size estimation only counts bytes for keys local to this node
        long expectedFileSize = 0;
        Collection<Range<Token>> ranges = StorageService.instance.getLocalRanges(keyspace.getName());
        for (SSTableReader sstable : sstables)
        {
            List<Pair<Long, Long>> positions = sstable.getPositionsForRanges(ranges);
            for (Pair<Long, Long> position : positions)
                expectedFileSize += position.right - position.left;
        }

        double compressionRatio = getCompressionRatio();
        if (compressionRatio > 0d)
            expectedFileSize *= compressionRatio;

        return expectedFileSize;
    }

    /*
     *  Find the maximum size file in the list .
     */
    public SSTableReader getMaxSizeFile(Iterable<SSTableReader> sstables)
    {
        long maxSize = 0L;
        SSTableReader maxFile = null;
        for (SSTableReader sstable : sstables)
        {
            if (sstable.onDiskLength() > maxSize)
            {
                maxSize = sstable.onDiskLength();
                maxFile = sstable;
            }
        }
        return maxFile;
    }

    public CompactionManager.AllSSTableOpStatus forceCleanup() throws ExecutionException, InterruptedException
    {
        return CompactionManager.instance.performCleanup(ColumnFamilyStore.this);
    }

    public CompactionManager.AllSSTableOpStatus scrub(boolean disableSnapshot, boolean skipCorrupted, boolean checkData) throws ExecutionException, InterruptedException
    {
        // skip snapshot creation during scrub, SEE JIRA 5891
        if(!disableSnapshot)
            snapshotWithoutFlush("pre-scrub-" + System.currentTimeMillis());
        return CompactionManager.instance.performScrub(ColumnFamilyStore.this, skipCorrupted, checkData);
    }

    public CompactionManager.AllSSTableOpStatus sstablesRewrite(boolean excludeCurrentVersion) throws ExecutionException, InterruptedException
    {
        return CompactionManager.instance.performSSTableRewrite(ColumnFamilyStore.this, excludeCurrentVersion);
    }

    public void markObsolete(Collection<SSTableReader> sstables, OperationType compactionType)
    {
        assert !sstables.isEmpty();
        data.markObsolete(sstables, compactionType);
    }

    void replaceFlushed(Memtable memtable, SSTableReader sstable)
    {
        compactionStrategyWrapper.replaceFlushed(memtable, sstable);
    }

    public boolean isValid()
    {
        return valid;
    }

    public long getMemtableColumnsCount()
    {
        return metric.memtableColumnsCount.value();
    }

    public long getMemtableDataSize()
    {
        return metric.memtableOnHeapSize.value();
    }

    public int getMemtableSwitchCount()
    {
        return (int) metric.memtableSwitchCount.count();
    }

    /**
     * Package protected for access from the CompactionManager.
     */
    public DataTracker getDataTracker()
    {
        return data;
    }

    public Collection<SSTableReader> getSSTables()
    {
        return data.getSSTables();
    }

    public Set<SSTableReader> getUncompactingSSTables()
    {
        return data.getUncompactingSSTables();
    }

    public long[] getRecentSSTablesPerReadHistogram()
    {
        return metric.recentSSTablesPerRead.getBuckets(true);
    }

    public long[] getSSTablesPerReadHistogram()
    {
        return metric.sstablesPerRead.getBuckets(false);
    }

    public long getReadCount()
    {
        return metric.readLatency.latency.count();
    }

    public double getRecentReadLatencyMicros()
    {
        return metric.readLatency.getRecentLatency();
    }

    public long[] getLifetimeReadLatencyHistogramMicros()
    {
        return metric.readLatency.totalLatencyHistogram.getBuckets(false);
    }

    public long[] getRecentReadLatencyHistogramMicros()
    {
        return metric.readLatency.recentLatencyHistogram.getBuckets(true);
    }

    public long getTotalReadLatencyMicros()
    {
        return metric.readLatency.totalLatency.count();
    }

    public int getPendingTasks()
    {
        return (int) metric.pendingFlushes.count();
    }

    public long getWriteCount()
    {
        return metric.writeLatency.latency.count();
    }

    public long getTotalWriteLatencyMicros()
    {
        return metric.writeLatency.totalLatency.count();
    }

    public double getRecentWriteLatencyMicros()
    {
        return metric.writeLatency.getRecentLatency();
    }

    public long[] getLifetimeWriteLatencyHistogramMicros()
    {
        return metric.writeLatency.totalLatencyHistogram.getBuckets(false);
    }

    public long[] getRecentWriteLatencyHistogramMicros()
    {
        return metric.writeLatency.recentLatencyHistogram.getBuckets(true);
    }

    public long getRangeCount()
    {
        return metric.rangeLatency.latency.count();
    }

    public double getRecentRangeLatencyMicros()
    {
        return metric.rangeLatency.getRecentLatency();
    }

    public long[] getLifetimeRangeLatencyHistogramMicros()
    {
        return metric.rangeLatency.totalLatencyHistogram.getBuckets(false);
    }

    public long[] getRecentRangeLatencyHistogramMicros()
    {
        return metric.rangeLatency.recentLatencyHistogram.getBuckets(true);
    }

    public long getTotalRangeLatencyMicros()
    {
        return metric.rangeLatency.totalLatency.count();
    }

    public ColumnFamily getColumnFamily(DecoratedKey key,
                                        Composite start,
                                        Composite finish,
                                        boolean reversed,
                                        int limit,
                                        long timestamp)
    {
        return getColumnFamily(QueryFilter.getSliceFilter(key, name, start, finish, reversed, limit, timestamp));
    }

    /**
     * Fetch the row and columns given by filter.key if it is in the cache; if not, read it from disk and cache it
     *
     * If row is cached, and the filter given is within its bounds, we return from cache, otherwise from disk
     *
     * If row is not cached, we figure out what filter is "biggest", read that from disk, then
     * filter the result and either cache that or return it.
     *
     * @param cfId the column family to read the row from
     * @param filter the columns being queried.
     * @return the requested data for the filter provided
     */
    private ColumnFamily getThroughCache(UUID cfId, QueryFilter filter)
    {
        assert isRowCacheEnabled()
               : String.format("Row cache is not enabled on column family [" + name + "]");

        RowCacheKey key = new RowCacheKey(cfId, filter.key);

        // attempt a sentinel-read-cache sequence.  if a write invalidates our sentinel, we'll return our
        // (now potentially obsolete) data, but won't cache it. see CASSANDRA-3862
        // TODO: don't evict entire rows on writes (#2864)
        IRowCacheEntry cached = CacheService.instance.rowCache.get(key);
        if (cached != null)
        {
            if (cached instanceof RowCacheSentinel)
            {
                // Some other read is trying to cache the value, just do a normal non-caching read
                Tracing.trace("Row cache miss (race)");
                metric.rowCacheMiss.inc();
                return getTopLevelColumns(filter, Integer.MIN_VALUE);
            }

            ColumnFamily cachedCf = (ColumnFamily)cached;
            if (isFilterFullyCoveredBy(filter.filter, cachedCf, filter.timestamp))
            {
                metric.rowCacheHit.inc();
                Tracing.trace("Row cache hit");
                return filterColumnFamily(cachedCf, filter);
            }

            metric.rowCacheHitOutOfRange.inc();
            Tracing.trace("Ignoring row cache as cached value could not satisfy query");
            return getTopLevelColumns(filter, Integer.MIN_VALUE);
        }

        metric.rowCacheMiss.inc();
        Tracing.trace("Row cache miss");
        RowCacheSentinel sentinel = new RowCacheSentinel();
        boolean sentinelSuccess = CacheService.instance.rowCache.putIfAbsent(key, sentinel);
        ColumnFamily data = null;
        ColumnFamily toCache = null;
        try
        {
            // If we are explicitely asked to fill the cache with full partitions, we go ahead and query the whole thing
            if (metadata.getCaching().rowCache.cacheFullPartitions())
            {
                data = getTopLevelColumns(QueryFilter.getIdentityFilter(filter.key, name, filter.timestamp), Integer.MIN_VALUE);
                toCache = data;
                Tracing.trace("Populating row cache with the whole partition");
                if (sentinelSuccess && toCache != null)
                    CacheService.instance.rowCache.replace(key, sentinel, toCache);
                return filterColumnFamily(data, filter);
            }

            // Otherwise, if we want to cache the result of the query we're about to do, we must make sure this query
            // covers what needs to be cached. And if the user filter does not satisfy that, we sometimes extend said
            // filter so we can populate the cache but only if:
            //   1) we can guarantee it is a strict extension, i.e. that we will still fetch the data asked by the user.
            //   2) the extension does not make us query more than getRowsPerPartitionToCache() (as a mean to limit the
            //      amount of extra work we'll do on a user query for the purpose of populating the cache).
            //
            // In practice, we can only guarantee those 2 points if the filter is one that queries the head of the
            // partition (and if that filter actually counts CQL3 rows since that's what we cache and it would be
            // bogus to compare the filter count to the 'rows to cache' otherwise).
            if (filter.filter.isHeadFilter() && filter.filter.countCQL3Rows(metadata.comparator))
            {
                SliceQueryFilter sliceFilter = (SliceQueryFilter)filter.filter;
                int rowsToCache = metadata.getCaching().rowCache.rowsToCache;

                SliceQueryFilter cacheSlice = readFilterForCache();
                QueryFilter cacheFilter = new QueryFilter(filter.key, name, cacheSlice, filter.timestamp);

                // If the filter count is less than the number of rows cached, we simply extend it to make sure we do cover the
                // number of rows to cache, and if that count is greater than the number of rows to cache, we simply filter what
                // needs to be cached afterwards.
                if (sliceFilter.count < rowsToCache)
                {
                    toCache = getTopLevelColumns(cacheFilter, Integer.MIN_VALUE);
                    if (toCache != null)
                    {
                        Tracing.trace("Populating row cache ({} rows cached)", cacheSlice.lastCounted());
                        data = filterColumnFamily(toCache, filter);
                    }
                }
                else
                {
                    data = getTopLevelColumns(filter, Integer.MIN_VALUE);
                    if (data != null)
                    {
                        // The filter limit was greater than the number of rows to cache. But, if the filter had a non-empty
                        // finish bound, we may have gotten less than what needs to be cached, in which case we shouldn't cache it
                        // (otherwise a cache hit would assume the whole partition is cached which is not the case).
                        if (sliceFilter.finish().isEmpty() || sliceFilter.lastCounted() >= rowsToCache)
                        {
                            toCache = filterColumnFamily(data, cacheFilter);
                            Tracing.trace("Caching {} rows (out of {} requested)", cacheSlice.lastCounted(), sliceFilter.count);
                        }
                        else
                        {
                            Tracing.trace("Not populating row cache, not enough rows fetched ({} fetched but {} required for the cache)", sliceFilter.lastCounted(), rowsToCache);
                        }
                    }
                }

                if (sentinelSuccess && toCache != null)
                    CacheService.instance.rowCache.replace(key, sentinel, toCache);
                return data;
            }
            else
            {
                Tracing.trace("Fetching data but not populating cache as query does not query from the start of the partition");
                return getTopLevelColumns(filter, Integer.MIN_VALUE);
            }
        }
        finally
        {
            if (sentinelSuccess && toCache == null)
                invalidateCachedRow(key);
        }
    }

    public SliceQueryFilter readFilterForCache()
    {
        // We create a new filter everytime before for now SliceQueryFilter is unfortunatly mutable.
        return new SliceQueryFilter(ColumnSlice.ALL_COLUMNS_ARRAY, false, metadata.getCaching().rowCache.rowsToCache, metadata.clusteringColumns().size());
    }

    public boolean isFilterFullyCoveredBy(IDiskAtomFilter filter, ColumnFamily cachedCf, long now)
    {
        // We can use the cached value only if we know that no data it doesn't contain could be covered
        // by the query filter, that is if:
        //   1) either the whole partition is cached
        //   2) or we can ensure than any data the filter selects are in the cached partition

        // When counting rows to decide if the whole row is cached, we should be careful with expiring
        // columns: if we use a timestamp newer than the one that was used when populating the cache, we might
        // end up deciding the whole partition is cached when it's really not (just some rows expired since the
        // cf was cached). This is the reason for Integer.MIN_VALUE below.
        boolean wholePartitionCached = cachedCf.liveCQL3RowCount(Integer.MIN_VALUE) < metadata.getCaching().rowCache.rowsToCache;

        // Contrarily to the "wholePartitionCached" check above, we do want isFullyCoveredBy to take the
        // timestamp of the query into account when dealing with expired columns. Otherwise, we could think
        // the cached partition has enough live rows to satisfy the filter when it doesn't because some
        // are now expired.
        return wholePartitionCached || filter.isFullyCoveredBy(cachedCf, now);
    }

    public int gcBefore(long now)
    {
        return (int) (now / 1000) - metadata.getGcGraceSeconds();
    }

    /**
     * get a list of columns starting from a given column, in a specified order.
     * only the latest version of a column is returned.
     * @return null if there is no data and no tombstones; otherwise a ColumnFamily
     */
    public ColumnFamily getColumnFamily(QueryFilter filter)
    {
        assert name.equals(filter.getColumnFamilyName()) : filter.getColumnFamilyName();

        ColumnFamily result = null;

        long start = System.nanoTime();
        try
        {
            int gcBefore = gcBefore(filter.timestamp);
            if (isRowCacheEnabled())
            {
                assert !isIndex(); // CASSANDRA-5732
                UUID cfId = metadata.cfId;

                ColumnFamily cached = getThroughCache(cfId, filter);
                if (cached == null)
                {
                    logger.trace("cached row is empty");
                    return null;
                }

                result = cached;
            }
            else
            {
                ColumnFamily cf = getTopLevelColumns(filter, gcBefore);

                if (cf == null)
                    return null;

                result = removeDeletedCF(cf, gcBefore);
            }

            removeDroppedColumns(result);

            if (filter.filter instanceof SliceQueryFilter)
            {
                // Log the number of tombstones scanned on single key queries
                metric.tombstoneScannedHistogram.update(((SliceQueryFilter) filter.filter).lastTombstones());
                metric.liveScannedHistogram.update(((SliceQueryFilter) filter.filter).lastLive());
            }
        }
        finally
        {
            metric.readLatency.addNano(System.nanoTime() - start);
        }

        return result;
    }

    /**
     *  Filter a cached row, which will not be modified by the filter, but may be modified by throwing out
     *  tombstones that are no longer relevant.
     *  The returned column family won't be thread safe.
     */
    ColumnFamily filterColumnFamily(ColumnFamily cached, QueryFilter filter)
    {
        if (cached == null)
            return null;

        ColumnFamily cf = cached.cloneMeShallow(ArrayBackedSortedColumns.factory, filter.filter.isReversed());
        int gcBefore = gcBefore(filter.timestamp);
        filter.collateOnDiskAtom(cf, filter.getIterator(cached), gcBefore);
        return removeDeletedCF(cf, gcBefore);
    }

    public Set<SSTableReader> getUnrepairedSSTables()
    {
        Set<SSTableReader> unRepairedSSTables = new HashSet<>(getSSTables());
        Iterator<SSTableReader> sstableIterator = unRepairedSSTables.iterator();
        while(sstableIterator.hasNext())
        {
            SSTableReader sstable = sstableIterator.next();
            if (sstable.isRepaired())
                sstableIterator.remove();
        }
        return unRepairedSSTables;
    }

    public Set<SSTableReader> getRepairedSSTables()
    {
        Set<SSTableReader> repairedSSTables = new HashSet<>(getSSTables());
        Iterator<SSTableReader> sstableIterator = repairedSSTables.iterator();
        while(sstableIterator.hasNext())
        {
            SSTableReader sstable = sstableIterator.next();
            if (!sstable.isRepaired())
                sstableIterator.remove();
        }
        return repairedSSTables;
    }

    public RefViewFragment selectAndReference(Function<DataTracker.View, List<SSTableReader>> filter)
    {
        long failingSince = -1L;
        while (true)
        {
            ViewFragment view = select(filter);
            Refs<SSTableReader> refs = Refs.tryRef(view.sstables);
            if (refs != null)
                return new RefViewFragment(view.sstables, view.memtables, refs);
            if (failingSince <= 0)
            {
                failingSince = System.nanoTime();
            }
            else if (TimeUnit.MILLISECONDS.toNanos(100) > System.nanoTime() - failingSince)
            {
                List<SSTableReader> released = new ArrayList<>();
                for (SSTableReader reader : view.sstables)
                    if (reader.selfRef().globalCount() == 0)
                        released.add(reader);
                logger.info("Spinning trying to capture released readers {}", released);
                logger.info("Spinning trying to capture all readers {}", view.sstables);
                failingSince = System.nanoTime();
            }
        }
    }

    public ViewFragment select(Function<DataTracker.View, List<SSTableReader>> filter)
    {
        DataTracker.View view = data.getView();
        List<SSTableReader> sstables = view.intervalTree.isEmpty()
                                       ? Collections.<SSTableReader>emptyList()
                                       : filter.apply(view);
        return new ViewFragment(sstables, view.getAllMemtables());
    }


    /**
     * @return a ViewFragment containing the sstables and memtables that may need to be merged
     * for the given @param key, according to the interval tree
     */
    public Function<DataTracker.View, List<SSTableReader>> viewFilter(final DecoratedKey key)
    {
        assert !key.isMinimum(partitioner);
        return new Function<DataTracker.View, List<SSTableReader>>()
        {
            public List<SSTableReader> apply(DataTracker.View view)
            {
                return compactionStrategyWrapper.filterSSTablesForReads(view.intervalTree.search(key));
            }
        };
    }

    /**
     * @return a ViewFragment containing the sstables and memtables that may need to be merged
     * for rows within @param rowBounds, inclusive, according to the interval tree.
     */
    public Function<DataTracker.View, List<SSTableReader>> viewFilter(final AbstractBounds<RowPosition> rowBounds)
    {
        return new Function<DataTracker.View, List<SSTableReader>>()
        {
            public List<SSTableReader> apply(DataTracker.View view)
            {
                return compactionStrategyWrapper.filterSSTablesForReads(view.sstablesInBounds(rowBounds));
            }
        };
    }

    public List<String> getSSTablesForKey(String key)
    {
        DecoratedKey dk = partitioner.decorateKey(metadata.getKeyValidator().fromString(key));
        try (OpOrder.Group op = readOrdering.start())
        {
            List<String> files = new ArrayList<>();
            for (SSTableReader sstr : select(viewFilter(dk)).sstables)
            {
                // check if the key actually exists in this sstable, without updating cache and stats
                if (sstr.getPosition(dk, SSTableReader.Operator.EQ, false) != null)
                    files.add(sstr.getFilename());
            }
            return files;
        }
    }

    public ColumnFamily getTopLevelColumns(QueryFilter filter, int gcBefore)
    {
        Tracing.trace("Executing single-partition query on {}", name);
        CollationController controller = new CollationController(this, filter, gcBefore);
        ColumnFamily columns;
        try (OpOrder.Group op = readOrdering.start())
        {
            columns = controller.getTopLevelColumns(Memtable.MEMORY_POOL.needToCopyOnHeap());
        }
        if (columns != null)
            metric.samplers.get(Sampler.READS).addSample(filter.key.getKey(), filter.key.hashCode(), 1);
        metric.updateSSTableIterated(controller.getSstablesIterated());
        return columns;
    }

    public void beginLocalSampling(String sampler, int capacity)
    {
        metric.samplers.get(Sampler.valueOf(sampler)).beginSampling(capacity);
    }

    public CompositeData finishLocalSampling(String sampler, int count) throws OpenDataException
    {
        SamplerResult<ByteBuffer> samplerResults = metric.samplers.get(Sampler.valueOf(sampler))
                .finishSampling(count);
        TabularDataSupport result = new TabularDataSupport(COUNTER_TYPE);
        for (Counter<ByteBuffer> counter : samplerResults.topK)
        {
            byte[] key = counter.getItem().array();
            result.put(new CompositeDataSupport(COUNTER_COMPOSITE_TYPE, COUNTER_NAMES, new Object[] {
                    Hex.bytesToHex(key), // raw
                    counter.getCount(),  // count
                    counter.getError(),  // error
                    metadata.getKeyValidator().getString(ByteBuffer.wrap(key)) })); // string
        }
        return new CompositeDataSupport(SAMPLING_RESULT, SAMPLER_NAMES, new Object[]{
                samplerResults.cardinality, result});
    }

    public void cleanupCache()
    {
        Collection<Range<Token>> ranges = StorageService.instance.getLocalRanges(keyspace.getName());

        for (RowCacheKey key : CacheService.instance.rowCache.getKeySet())
        {
            DecoratedKey dk = partitioner.decorateKey(ByteBuffer.wrap(key.key));
            if (key.cfId == metadata.cfId && !Range.isInRanges(dk.getToken(), ranges))
                invalidateCachedRow(dk);
        }

        if (metadata.isCounter())
        {
            for (CounterCacheKey key : CacheService.instance.counterCache.getKeySet())
            {
                DecoratedKey dk = partitioner.decorateKey(ByteBuffer.wrap(key.partitionKey));
                if (key.cfId == metadata.cfId && !Range.isInRanges(dk.getToken(), ranges))
                    CacheService.instance.counterCache.remove(key);
            }
        }
    }

    public static abstract class AbstractScanIterator extends AbstractIterator<Row> implements CloseableIterator<Row>
    {
        public boolean needsFiltering()
        {
            return true;
        }
    }

    /**
      * Iterate over a range of rows and columns from memtables/sstables.
      *
      * @param range The range of keys and columns within those keys to fetch
     */
    private AbstractScanIterator getSequentialIterator(final DataRange range, long now)
    {
        assert !(range.keyRange() instanceof Range) || !((Range)range.keyRange()).isWrapAround() || range.keyRange().right.isMinimum(partitioner) : range.keyRange();

        final ViewFragment view = select(viewFilter(range.keyRange()));
        Tracing.trace("Executing seq scan across {} sstables for {}", view.sstables.size(), range.keyRange().getString(metadata.getKeyValidator()));

        final CloseableIterator<Row> iterator = RowIteratorFactory.getIterator(view.memtables, view.sstables, range, this, now);

        // todo this could be pushed into SSTableScanner
        return new AbstractScanIterator()
        {
            protected Row computeNext()
            {
                // pull a row out of the iterator
                if (!iterator.hasNext())
                    return endOfData();

                Row current = iterator.next();
                DecoratedKey key = current.key;

                if (!range.stopKey().isMinimum(partitioner) && range.stopKey().compareTo(key) < 0)
                    return endOfData();

                // skipping outside of assigned range
                if (!range.contains(key))
                    return computeNext();

                if (logger.isTraceEnabled())
                    logger.trace("scanned {}", metadata.getKeyValidator().getString(key.getKey()));

                return current;
            }

            public void close() throws IOException
            {
                iterator.close();
            }
        };
    }

    @VisibleForTesting
    public List<Row> getRangeSlice(final AbstractBounds<RowPosition> range,
                                   List<IndexExpression> rowFilter,
                                   IDiskAtomFilter columnFilter,
                                   int maxResults)
    {
        return getRangeSlice(range, rowFilter, columnFilter, maxResults, System.currentTimeMillis());
    }

    public List<Row> getRangeSlice(final AbstractBounds<RowPosition> range,
                                   List<IndexExpression> rowFilter,
                                   IDiskAtomFilter columnFilter,
                                   int maxResults,
                                   long now)
    {
        return getRangeSlice(makeExtendedFilter(range, columnFilter, rowFilter, maxResults, false, false, now));
    }

    /**
     * Allows generic range paging with the slice column filter.
     * Typically, suppose we have rows A, B, C ... Z having each some columns in [1, 100].
     * And suppose we want to page through the query that for all rows returns the columns
     * within [25, 75]. For that, we need to be able to do a range slice starting at (row r, column c)
     * and ending at (row Z, column 75), *but* that only return columns in [25, 75].
     * That is what this method allows. The columnRange is the "window" of  columns we are interested
     * in each row, and columnStart (resp. columnEnd) is the start (resp. end) for the first
     * (resp. last) requested row.
     */
    public ExtendedFilter makeExtendedFilter(AbstractBounds<RowPosition> keyRange,
                                             SliceQueryFilter columnRange,
                                             Composite columnStart,
                                             Composite columnStop,
                                             List<IndexExpression> rowFilter,
                                             int maxResults,
                                             boolean countCQL3Rows,
                                             long now)
    {
        DataRange dataRange = new DataRange.Paging(keyRange, columnRange, columnStart, columnStop, metadata);
        return ExtendedFilter.create(this, dataRange, rowFilter, maxResults, countCQL3Rows, now);
    }

    public List<Row> getRangeSlice(AbstractBounds<RowPosition> range,
                                   List<IndexExpression> rowFilter,
                                   IDiskAtomFilter columnFilter,
                                   int maxResults,
                                   long now,
                                   boolean countCQL3Rows,
                                   boolean isPaging)
    {
        return getRangeSlice(makeExtendedFilter(range, columnFilter, rowFilter, maxResults, countCQL3Rows, isPaging, now));
    }

    public ExtendedFilter makeExtendedFilter(AbstractBounds<RowPosition> range,
                                             IDiskAtomFilter columnFilter,
                                             List<IndexExpression> rowFilter,
                                             int maxResults,
                                             boolean countCQL3Rows,
                                             boolean isPaging,
                                             long timestamp)
    {
        DataRange dataRange;
        if (isPaging)
        {
            assert columnFilter instanceof SliceQueryFilter;
            SliceQueryFilter sfilter = (SliceQueryFilter)columnFilter;
            assert sfilter.slices.length == 1;
            // create a new SliceQueryFilter that selects all cells, but pass the original slice start and finish
            // through to DataRange.Paging to be used on the first and last partitions
            SliceQueryFilter newFilter = new SliceQueryFilter(ColumnSlice.ALL_COLUMNS_ARRAY, sfilter.isReversed(), sfilter.count);
            dataRange = new DataRange.Paging(range, newFilter, sfilter.start(), sfilter.finish(), metadata);
        }
        else
        {
            dataRange = new DataRange(range, columnFilter);
        }
        return ExtendedFilter.create(this, dataRange, rowFilter, maxResults, countCQL3Rows, timestamp);
    }

    public List<Row> getRangeSlice(ExtendedFilter filter)
    {
        long start = System.nanoTime();
        try (OpOrder.Group op = readOrdering.start())
        {
            return filter(getSequentialIterator(filter.dataRange, filter.timestamp), filter);
        }
        finally
        {
            metric.rangeLatency.addNano(System.nanoTime() - start);
        }
    }

    @VisibleForTesting
    public List<Row> search(AbstractBounds<RowPosition> range,
                            List<IndexExpression> clause,
                            IDiskAtomFilter dataFilter,
                            int maxResults)
    {
        return search(range, clause, dataFilter, maxResults, System.currentTimeMillis());
    }

    public List<Row> search(AbstractBounds<RowPosition> range,
                            List<IndexExpression> clause,
                            IDiskAtomFilter dataFilter,
                            int maxResults,
                            long now)
    {
        return search(makeExtendedFilter(range, dataFilter, clause, maxResults, false, false, now));
    }

    public List<Row> search(ExtendedFilter filter)
    {
        Tracing.trace("Executing indexed scan for {}", filter.dataRange.keyRange().getString(metadata.getKeyValidator()));
        return indexManager.search(filter);
    }

    public List<Row> filter(AbstractScanIterator rowIterator, ExtendedFilter filter)
    {
        logger.trace("Filtering {} for rows matching {}", rowIterator, filter);
        List<Row> rows = new ArrayList<Row>();
        int columnsCount = 0;
        int total = 0, matched = 0;
        boolean ignoreTombstonedPartitions = filter.ignoreTombstonedPartitions();

        try
        {
            while (rowIterator.hasNext() && matched < filter.maxRows() && columnsCount < filter.maxColumns())
            {
                // get the raw columns requested, and additional columns for the expressions if necessary
                Row rawRow = rowIterator.next();
                total++;
                ColumnFamily data = rawRow.cf;

                if (rowIterator.needsFiltering())
                {
                    IDiskAtomFilter extraFilter = filter.getExtraFilter(rawRow.key, data);
                    if (extraFilter != null)
                    {
                        ColumnFamily cf = filter.cfs.getColumnFamily(new QueryFilter(rawRow.key, name, extraFilter, filter.timestamp));
                        if (cf != null)
                            data.addAll(cf);
                    }

                    removeDroppedColumns(data);

                    if (!filter.isSatisfiedBy(rawRow.key, data, null, null))
                        continue;

                    logger.trace("{} satisfies all filter expressions", data);
                    // cut the resultset back to what was requested, if necessary
                    data = filter.prune(rawRow.key, data);
                }
                else
                {
                    removeDroppedColumns(data);
                }

                rows.add(new Row(rawRow.key, data));
                if (!ignoreTombstonedPartitions || !data.hasOnlyTombstones(filter.timestamp))
                    matched++;

                if (data != null)
                    columnsCount += filter.lastCounted(data);
                // Update the underlying filter to avoid querying more columns per slice than necessary and to handle paging
                filter.updateFilter(columnsCount);
            }

            return rows;
        }
        finally
        {
            try
            {
                rowIterator.close();
                Tracing.trace("Scanned {} rows and matched {}", total, matched);
            }
            catch (IOException e)
            {
                throw new RuntimeException(e);
            }
        }
    }

    public CellNameType getComparator()
    {
        return metadata.comparator;
    }

    public void snapshotWithoutFlush(String snapshotName)
    {
        snapshotWithoutFlush(snapshotName, null);
    }

    public void snapshotWithoutFlush(String snapshotName, Predicate<SSTableReader> predicate)
    {
        for (ColumnFamilyStore cfs : concatWithIndexes())
        {
            final JSONArray filesJSONArr = new JSONArray();
            try (RefViewFragment currentView = cfs.selectAndReference(CANONICAL_SSTABLES))
            {
                for (SSTableReader ssTable : currentView.sstables)
                {
                    if (predicate != null && !predicate.apply(ssTable))
                        continue;

                    File snapshotDirectory = Directories.getSnapshotDirectory(ssTable.descriptor, snapshotName);
                    ssTable.createLinks(snapshotDirectory.getPath()); // hard links
                    filesJSONArr.add(ssTable.descriptor.relativeFilenameFor(Component.DATA));
                    if (logger.isDebugEnabled())
                        logger.debug("Snapshot for {} keyspace data file {} created in {}", keyspace, ssTable.getFilename(), snapshotDirectory);
                }

                writeSnapshotManifest(filesJSONArr, snapshotName);
            }
        }
    }

    private void writeSnapshotManifest(final JSONArray filesJSONArr, final String snapshotName)
    {
        final File manifestFile = directories.getSnapshotManifestFile(snapshotName);
        final JSONObject manifestJSON = new JSONObject();
        manifestJSON.put("files", filesJSONArr);

        try
        {
            if (!manifestFile.getParentFile().exists())
                manifestFile.getParentFile().mkdirs();
            PrintStream out = new PrintStream(manifestFile);
            out.println(manifestJSON.toJSONString());
            out.close();
        }
        catch (IOException e)
        {
            throw new FSWriteError(e, manifestFile);
        }
    }

    public Refs<SSTableReader> getSnapshotSSTableReader(String tag) throws IOException
    {
        Map<Integer, SSTableReader> active = new HashMap<>();
        for (SSTableReader sstable : data.getView().sstables)
            active.put(sstable.descriptor.generation, sstable);
        Map<Descriptor, Set<Component>> snapshots = directories.sstableLister().snapshots(tag).list();
        Refs<SSTableReader> refs = new Refs<>();
        try
        {
            for (Map.Entry<Descriptor, Set<Component>> entries : snapshots.entrySet())
            {
                // Try acquire reference to an active sstable instead of snapshot if it exists,
                // to avoid opening new sstables. If it fails, use the snapshot reference instead.
                SSTableReader sstable = active.get(entries.getKey().generation);
                if (sstable == null || !refs.tryRef(sstable))
                {
                    if (logger.isDebugEnabled())
                        logger.debug("using snapshot sstable {}", entries.getKey());
                    sstable = SSTableReader.open(entries.getKey(), entries.getValue(), metadata, partitioner);
                    // This is technically not necessary since it's a snapshot but makes things easier
                    refs.tryRef(sstable);
                }
                else if (logger.isDebugEnabled())
                {
                    logger.debug("using active sstable {}", entries.getKey());
                }
            }
        }
        catch (IOException | RuntimeException e)
        {
            // In case one of the snapshot sstables fails to open,
            // we must release the references to the ones we opened so far
            refs.release();
            throw e;
        }
        return refs;
    }

    /**
     * Take a snap shot of this columnfamily store.
     *
     * @param snapshotName the name of the associated with the snapshot
     */
    public void snapshot(String snapshotName)
    {
        snapshot(snapshotName, null);
    }

    public void snapshot(String snapshotName, Predicate<SSTableReader> predicate)
    {
        forceBlockingFlush();
        snapshotWithoutFlush(snapshotName, predicate);
    }

    public boolean snapshotExists(String snapshotName)
    {
        return directories.snapshotExists(snapshotName);
    }

    public long getSnapshotCreationTime(String snapshotName)
    {
        return directories.snapshotCreationTime(snapshotName);
    }

    /**
     * Clear all the snapshots for a given column family.
     *
     * @param snapshotName the user supplied snapshot name. If left empty,
     *                     all the snapshots will be cleaned.
     */
    public void clearSnapshot(String snapshotName)
    {
        List<File> snapshotDirs = directories.getCFDirectories();
        Directories.clearSnapshot(snapshotName, snapshotDirs);
    }
    /**
     *
     * @return  Return a map of all snapshots to space being used
     * The pair for a snapshot has true size and size on disk.
     */
    public Map<String, Pair<Long,Long>> getSnapshotDetails()
    {
        return directories.getSnapshotDetails();
    }

    public long getTotalDiskSpaceUsed()
    {
        return metric.totalDiskSpaceUsed.count();
    }

    public long getLiveDiskSpaceUsed()
    {
        return metric.liveDiskSpaceUsed.count();
    }

    public int getLiveSSTableCount()
    {
        return metric.liveSSTableCount.value();
    }

    /**
     * @return the cached row for @param key if it is already present in the cache.
     * That is, unlike getThroughCache, it will not readAndCache the row if it is not present, nor
     * are these calls counted in cache statistics.
     *
     * Note that this WILL cause deserialization of a SerializingCache row, so if all you
     * need to know is whether a row is present or not, use containsCachedRow instead.
     */
    public ColumnFamily getRawCachedRow(DecoratedKey key)
    {
        if (!isRowCacheEnabled())
            return null;

        IRowCacheEntry cached = CacheService.instance.rowCache.getInternal(new RowCacheKey(metadata.cfId, key));
        return cached == null || cached instanceof RowCacheSentinel ? null : (ColumnFamily)cached;
    }

    private void invalidateCaches()
    {
        CacheService.instance.invalidateKeyCacheForCf(metadata.cfId);
        CacheService.instance.invalidateRowCacheForCf(metadata.cfId);
        if (metadata.isCounter())
            CacheService.instance.invalidateCounterCacheForCf(metadata.cfId);
    }

    /**
     * @return true if @param key is contained in the row cache
     */
    public boolean containsCachedRow(DecoratedKey key)
    {
        return CacheService.instance.rowCache.getCapacity() != 0 && CacheService.instance.rowCache.containsKey(new RowCacheKey(metadata.cfId, key));
    }

    public void invalidateCachedRow(RowCacheKey key)
    {
        CacheService.instance.rowCache.remove(key);
    }

    public void invalidateCachedRow(DecoratedKey key)
    {
        UUID cfId = Schema.instance.getId(keyspace.getName(), this.name);
        if (cfId == null)
            return; // secondary index

        invalidateCachedRow(new RowCacheKey(cfId, key));
    }

    public ClockAndCount getCachedCounter(ByteBuffer partitionKey, CellName cellName)
    {
        if (CacheService.instance.counterCache.getCapacity() == 0L) // counter cache disabled.
            return null;
        return CacheService.instance.counterCache.get(CounterCacheKey.create(metadata.cfId, partitionKey, cellName));
    }

    public void putCachedCounter(ByteBuffer partitionKey, CellName cellName, ClockAndCount clockAndCount)
    {
        if (CacheService.instance.counterCache.getCapacity() == 0L) // counter cache disabled.
            return;
        CacheService.instance.counterCache.put(CounterCacheKey.create(metadata.cfId, partitionKey, cellName), clockAndCount);
    }

    public void forceMajorCompaction() throws InterruptedException, ExecutionException
    {
        CompactionManager.instance.performMaximal(this);
    }

    public static Iterable<ColumnFamilyStore> all()
    {
        List<Iterable<ColumnFamilyStore>> stores = new ArrayList<Iterable<ColumnFamilyStore>>(Schema.instance.getKeyspaces().size());
        for (Keyspace keyspace : Keyspace.all())
        {
            stores.add(keyspace.getColumnFamilyStores());
        }
        return Iterables.concat(stores);
    }

    public Iterable<DecoratedKey> keySamples(Range<Token> range)
    {
        try (RefViewFragment view = selectAndReference(CANONICAL_SSTABLES))
        {
            Iterable<DecoratedKey>[] samples = new Iterable[view.sstables.size()];
            int i = 0;
            for (SSTableReader sstable: view.sstables)
            {
                samples[i++] = sstable.getKeySamples(range);
            }
            return Iterables.concat(samples);
        }
    }

    public long estimatedKeysForRange(Range<Token> range)
    {
        try (RefViewFragment view = selectAndReference(CANONICAL_SSTABLES))
        {
            long count = 0;
            for (SSTableReader sstable : view.sstables)
                count += sstable.estimatedKeysForRanges(Collections.singleton(range));
            return count;
        }
    }

    /**
     * For testing.  No effort is made to clear historical or even the current memtables, nor for
     * thread safety.  All we do is wipe the sstable containers clean, while leaving the actual
     * data files present on disk.  (This allows tests to easily call loadNewSSTables on them.)
     */
    public void clearUnsafe()
    {
        for (final ColumnFamilyStore cfs : concatWithIndexes())
        {
            cfs.runWithCompactionsDisabled(new Callable<Void>()
            {
                public Void call()
                {
                    cfs.data.init();
                    return null;
                }
            }, true);
        }
    }

    /**
     * Truncate deletes the entire column family's data with no expensive tombstone creation
     */
    public void truncateBlocking()
    {
        // We have two goals here:
        // - truncate should delete everything written before truncate was invoked
        // - but not delete anything that isn't part of the snapshot we create.
        // We accomplish this by first flushing manually, then snapshotting, and
        // recording the timestamp IN BETWEEN those actions. Any sstables created
        // with this timestamp or greater time, will not be marked for delete.
        //
        // Bonus complication: since we store replay position in sstable metadata,
        // truncating those sstables means we will replay any CL segments from the
        // beginning if we restart before they [the CL segments] are discarded for
        // normal reasons post-truncate.  To prevent this, we store truncation
        // position in the System keyspace.
        logger.debug("truncating {}", name);

        if (keyspace.getMetadata().durableWrites || DatabaseDescriptor.isAutoSnapshot())
        {
            // flush the CF being truncated before forcing the new segment
            forceBlockingFlush();

            // sleep a little to make sure that our truncatedAt comes after any sstable
            // that was part of the flushed we forced; otherwise on a tie, it won't get deleted.
            Uninterruptibles.sleepUninterruptibly(1, TimeUnit.MILLISECONDS);
        }
        else
        {
            // just nuke the memtable data w/o writing to disk first
            synchronized (data)
            {
                final Flush flush = new Flush(true);
                flushExecutor.execute(flush);
                postFlushExecutor.submit(flush.postFlush);
            }
        }

        Runnable truncateRunnable = new Runnable()
        {
            public void run()
            {
                logger.debug("Discarding sstable data for truncated CF + indexes");

                final long truncatedAt = System.currentTimeMillis();
                data.notifyTruncated(truncatedAt);

                if (DatabaseDescriptor.isAutoSnapshot())
                    snapshot(Keyspace.getTimestampedSnapshotName(name));

                ReplayPosition replayAfter = discardSSTables(truncatedAt);

                for (SecondaryIndex index : indexManager.getIndexes())
                    index.truncateBlocking(truncatedAt);

                SystemKeyspace.saveTruncationRecord(ColumnFamilyStore.this, truncatedAt, replayAfter);
                logger.debug("cleaning out row cache");
                invalidateCaches();
            }
        };

        runWithCompactionsDisabled(Executors.callable(truncateRunnable), true);
        logger.debug("truncate complete");
    }

    public <V> V runWithCompactionsDisabled(Callable<V> callable, boolean interruptValidation)
    {
        // synchronize so that concurrent invocations don't re-enable compactions partway through unexpectedly,
        // and so we only run one major compaction at a time
        synchronized (this)
        {
            logger.debug("Cancelling in-progress compactions for {}", metadata.cfName);

            Iterable<ColumnFamilyStore> selfWithIndexes = concatWithIndexes();
            for (ColumnFamilyStore cfs : selfWithIndexes)
                cfs.getCompactionStrategy().pause();
            try
            {
                // interrupt in-progress compactions
                CompactionManager.instance.interruptCompactionForCFs(selfWithIndexes, interruptValidation);
                CompactionManager.instance.waitForCessation(selfWithIndexes);

                // doublecheck that we finished, instead of timing out
                for (ColumnFamilyStore cfs : selfWithIndexes)
                {
                    if (!cfs.getDataTracker().getCompacting().isEmpty())
                    {
                        logger.warn("Unable to cancel in-progress compactions for {}.  Perhaps there is an unusually large row in progress somewhere, or the system is simply overloaded.", metadata.cfName);
                        return null;
                    }
                }
                logger.debug("Compactions successfully cancelled");

                // run our task
                try
                {
                    return callable.call();
                }
                catch (Exception e)
                {
                    throw new RuntimeException(e);
                }
            }
            finally
            {
                for (ColumnFamilyStore cfs : selfWithIndexes)
                    cfs.getCompactionStrategy().resume();
            }
        }
    }

    public Iterable<SSTableReader> markAllCompacting()
    {
        Callable<Iterable<SSTableReader>> callable = new Callable<Iterable<SSTableReader>>()
        {
            public Iterable<SSTableReader> call() throws Exception
            {
                assert data.getCompacting().isEmpty() : data.getCompacting();
                Collection<SSTableReader> sstables = Lists.newArrayList(AbstractCompactionStrategy.filterSuspectSSTables(getSSTables()));
                if (Iterables.isEmpty(sstables))
                    return Collections.emptyList();
                boolean success = data.markCompacting(sstables);
                assert success : "something marked things compacting while compactions are disabled";
                return sstables;
            }
        };

        return runWithCompactionsDisabled(callable, false);
    }

    public long getBloomFilterFalsePositives()
    {
        return metric.bloomFilterFalsePositives.value();
    }

    public long getRecentBloomFilterFalsePositives()
    {
        return metric.recentBloomFilterFalsePositives.value();
    }

    public double getBloomFilterFalseRatio()
    {
        return metric.bloomFilterFalseRatio.value();
    }

    public double getRecentBloomFilterFalseRatio()
    {
        return metric.recentBloomFilterFalseRatio.value();
    }

    public long getBloomFilterDiskSpaceUsed()
    {
        return metric.bloomFilterDiskSpaceUsed.value();
    }

    public long getBloomFilterOffHeapMemoryUsed()
    {
        return metric.bloomFilterOffHeapMemoryUsed.value();
    }

    public long getIndexSummaryOffHeapMemoryUsed()
    {
        return metric.indexSummaryOffHeapMemoryUsed.value();
    }

    public long getCompressionMetadataOffHeapMemoryUsed()
    {
        return metric.compressionMetadataOffHeapMemoryUsed.value();
    }

    @Override
    public String toString()
    {
        return "CFS(" +
               "Keyspace='" + keyspace.getName() + '\'' +
               ", ColumnFamily='" + name + '\'' +
               ')';
    }

    public void disableAutoCompaction()
    {
        // we don't use CompactionStrategy.pause since we don't want users flipping that on and off
        // during runWithCompactionsDisabled
        this.compactionStrategyWrapper.disable();
    }

    public void enableAutoCompaction()
    {
        enableAutoCompaction(false);
    }

    /**
     * used for tests - to be able to check things after a minor compaction
     * @param waitForFutures if we should block until autocompaction is done
     */
    @VisibleForTesting
    public void enableAutoCompaction(boolean waitForFutures)
    {
        this.compactionStrategyWrapper.enable();
        List<Future<?>> futures = CompactionManager.instance.submitBackground(this);
        if (waitForFutures)
            FBUtilities.waitOnFutures(futures);
    }

    public boolean isAutoCompactionDisabled()
    {
        return !this.compactionStrategyWrapper.isEnabled();
    }

    /*
     JMX getters and setters for the Default<T>s.
       - get/set minCompactionThreshold
       - get/set maxCompactionThreshold
       - get     memsize
       - get     memops
       - get/set memtime
     */

    public AbstractCompactionStrategy getCompactionStrategy()
    {
        return compactionStrategyWrapper;
    }

    public void setCompactionThresholds(int minThreshold, int maxThreshold)
    {
        validateCompactionThresholds(minThreshold, maxThreshold);

        minCompactionThreshold.set(minThreshold);
        maxCompactionThreshold.set(maxThreshold);
        CompactionManager.instance.submitBackground(this);
    }

    public int getMinimumCompactionThreshold()
    {
        return minCompactionThreshold.value();
    }

    public void setMinimumCompactionThreshold(int minCompactionThreshold)
    {
        validateCompactionThresholds(minCompactionThreshold, maxCompactionThreshold.value());
        this.minCompactionThreshold.set(minCompactionThreshold);
    }

    public int getMaximumCompactionThreshold()
    {
        return maxCompactionThreshold.value();
    }

    public void setMaximumCompactionThreshold(int maxCompactionThreshold)
    {
        validateCompactionThresholds(minCompactionThreshold.value(), maxCompactionThreshold);
        this.maxCompactionThreshold.set(maxCompactionThreshold);
    }

    private void validateCompactionThresholds(int minThreshold, int maxThreshold)
    {
        if (minThreshold > maxThreshold)
            throw new RuntimeException(String.format("The min_compaction_threshold cannot be larger than the max_compaction_threshold. " +
                                                     "Min is '%d', Max is '%d'.", minThreshold, maxThreshold));

        if (maxThreshold == 0 || minThreshold == 0)
            throw new RuntimeException("Disabling compaction by setting min_compaction_threshold or max_compaction_threshold to 0 " +
                    "is deprecated, set the compaction strategy option 'enabled' to 'false' instead or use the nodetool command 'disableautocompaction'.");
    }

    public double getTombstonesPerSlice()
    {
        return metric.tombstoneScannedHistogram.cf.getSnapshot().getMedian();
    }

    public double getLiveCellsPerSlice()
    {
        return metric.liveScannedHistogram.cf.getSnapshot().getMedian();
    }

    // End JMX get/set.

    public long estimateKeys()
    {
        return data.estimatedKeys();
    }

    public long[] getEstimatedRowSizeHistogram()
    {
        return metric.estimatedRowSizeHistogram.value();
    }

    public long[] getEstimatedColumnCountHistogram()
    {
        return metric.estimatedColumnCountHistogram.value();
    }

    public double getCompressionRatio()
    {
        return metric.compressionRatio.value();
    }

    /** true if this CFS contains secondary index data */
    public boolean isIndex()
    {
        return partitioner instanceof LocalPartitioner;
    }

    public Iterable<ColumnFamilyStore> concatWithIndexes()
    {
        // we return the main CFS first, which we rely on for simplicity in switchMemtable(), for getting the
        // latest replay position
        return Iterables.concat(Collections.singleton(this), indexManager.getIndexesBackedByCfs());
    }

    public List<String> getBuiltIndexes()
    {
       return indexManager.getBuiltIndexes();
    }

    public int getUnleveledSSTables()
    {
        return this.compactionStrategyWrapper.getUnleveledSSTables();
    }

    public int[] getSSTableCountPerLevel()
    {
        return compactionStrategyWrapper.getSSTableCountPerLevel();
    }

    public static class ViewFragment
    {
        public final List<SSTableReader> sstables;
        public final Iterable<Memtable> memtables;

        public ViewFragment(List<SSTableReader> sstables, Iterable<Memtable> memtables)
        {
            this.sstables = sstables;
            this.memtables = memtables;
        }
    }

    public static class RefViewFragment extends ViewFragment implements AutoCloseable
    {
        public final Refs<SSTableReader> refs;

        public RefViewFragment(List<SSTableReader> sstables, Iterable<Memtable> memtables, Refs<SSTableReader> refs)
        {
            super(sstables, memtables);
            this.refs = refs;
        }

        public void release()
        {
            refs.release();
        }

        public void close()
        {
            refs.release();
        }
    }

    /**
     * Returns the creation time of the oldest memtable not fully flushed yet.
     */
    public long oldestUnflushedMemtable()
    {
        return data.getView().getOldestMemtable().creationTime();
    }

    public boolean isEmpty()
    {
        DataTracker.View view = data.getView();
        return view.sstables.isEmpty() && view.getCurrentMemtable().getOperations() == 0 && view.getCurrentMemtable() == view.getOldestMemtable();
    }

    private boolean isRowCacheEnabled()
    {
        return metadata.getCaching().rowCache.isEnabled() && CacheService.instance.rowCache.getCapacity() > 0;
    }

    /**
     * Discard all SSTables that were created before given timestamp.
     *
     * Caller should first ensure that comapctions have quiesced.
     *
     * @param truncatedAt The timestamp of the truncation
     *                    (all SSTables before that timestamp are going be marked as compacted)
     *
     * @return the most recent replay position of the truncated data
     */
    public ReplayPosition discardSSTables(long truncatedAt)
    {
        assert data.getCompacting().isEmpty() : data.getCompacting();

        List<SSTableReader> truncatedSSTables = new ArrayList<SSTableReader>();

        for (SSTableReader sstable : getSSTables())
        {
            if (!sstable.newSince(truncatedAt))
                truncatedSSTables.add(sstable);
        }

        if (truncatedSSTables.isEmpty())
            return ReplayPosition.NONE;

        markObsolete(truncatedSSTables, OperationType.UNKNOWN);
        return ReplayPosition.getReplayPosition(truncatedSSTables);
    }

    public double getDroppableTombstoneRatio()
    {
        return getDataTracker().getDroppableTombstoneRatio();
    }

    public long trueSnapshotsSize()
    {
        return directories.trueSnapshotsSize();
    }

    @VisibleForTesting
    void resetFileIndexGenerator()
    {
        fileIndexGenerator.set(0);
    }

    // returns the "canonical" version of any current sstable, i.e. if an sstable is being replaced and is only partially
    // visible to reads, this sstable will be returned as its original entirety, and its replacement will not be returned
    // (even if it completely replaces it)
    public static final Function<DataTracker.View, List<SSTableReader>> CANONICAL_SSTABLES = new Function<DataTracker.View, List<SSTableReader>>()
    {
        public List<SSTableReader> apply(DataTracker.View view)
        {
            List<SSTableReader> sstables = new ArrayList<>();
            for (SSTableReader sstable : view.compacting)
                if (sstable.openReason != SSTableReader.OpenReason.EARLY)
                    sstables.add(sstable);
            for (SSTableReader sstable : view.sstables)
                if (!view.compacting.contains(sstable) && sstable.openReason != SSTableReader.OpenReason.EARLY)
                    sstables.add(sstable);
            return sstables;
        }
    };

    public static final Function<DataTracker.View, List<SSTableReader>> UNREPAIRED_SSTABLES = new Function<DataTracker.View, List<SSTableReader>>()
    {
        public List<SSTableReader> apply(DataTracker.View view)
        {
            List<SSTableReader> sstables = new ArrayList<>();
            for (SSTableReader sstable : CANONICAL_SSTABLES.apply(view))
            {
                if (!sstable.isRepaired())
                    sstables.add(sstable);
            }
            return sstables;
        }
    };
}


File: src/java/org/apache/cassandra/db/Directories.java
/*
 * Licensed to the Apache Software Foundation (ASF) under one
 * or more contributor license agreements.  See the NOTICE file
 * distributed with this work for additional information
 * regarding copyright ownership.  The ASF licenses this file
 * to you under the Apache License, Version 2.0 (the
 * "License"); you may not use this file except in compliance
 * with the License.  You may obtain a copy of the License at
 *
 *     http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 */
package org.apache.cassandra.db;

import static com.google.common.collect.Sets.newHashSet;

import java.io.File;
import java.io.FileFilter;
import java.io.IOError;
import java.io.IOException;
import java.nio.file.FileVisitResult;
import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.SimpleFileVisitor;
import java.nio.file.attribute.BasicFileAttributes;
import java.util.*;
import java.util.concurrent.ThreadLocalRandom;
import java.util.concurrent.atomic.AtomicLong;

import com.google.common.annotations.VisibleForTesting;
import com.google.common.base.Predicate;
import com.google.common.collect.ImmutableMap;
import com.google.common.collect.ImmutableSet;
import com.google.common.collect.ImmutableSet.Builder;
import com.google.common.collect.Iterables;

import org.apache.commons.lang3.StringUtils;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import org.apache.cassandra.config.*;
import org.apache.cassandra.io.FSError;
import org.apache.cassandra.io.FSWriteError;
import org.apache.cassandra.io.util.FileUtils;
import org.apache.cassandra.io.sstable.*;
import org.apache.cassandra.service.StorageService;
import org.apache.cassandra.utils.ByteBufferUtil;
import org.apache.cassandra.utils.Pair;

/**
 * Encapsulate handling of paths to the data files.
 *
 * Since v2.1, the directory layout is the following:
 *   /<path_to_data_dir>/ks/cf1-cfId/ks-cf1-ka-1-Data.db
 *                         /cf2-cfId/ks-cf2-ka-1-Data.db
 *                         ...
 *
 * cfId is an hex encoded CFID.
 *
 * For backward compatibility, Directories uses older directory layout if exists.
 *
 * In addition, more that one 'root' data directory can be specified so that
 * <path_to_data_dir> potentially represents multiple locations.
 * Note that in the case of multiple locations, the manifest for the leveled
 * compaction is only in one of the location.
 *
 * Snapshots (resp. backups) are always created along the sstables thare are
 * snapshoted (resp. backuped) but inside a subdirectory named 'snapshots'
 * (resp. backups) (and snapshots are furter inside a subdirectory of the name
 * of the snapshot).
 *
 * This class abstracts all those details from the rest of the code.
 */
public class Directories
{
    private static final Logger logger = LoggerFactory.getLogger(Directories.class);

    public static final String BACKUPS_SUBDIR = "backups";
    public static final String SNAPSHOT_SUBDIR = "snapshots";
    public static final String SECONDARY_INDEX_NAME_SEPARATOR = ".";

    public static final DataDirectory[] dataDirectories;
    static
    {
        String[] locations = DatabaseDescriptor.getAllDataFileLocations();
        dataDirectories = new DataDirectory[locations.length];
        for (int i = 0; i < locations.length; ++i)
            dataDirectories[i] = new DataDirectory(new File(locations[i]));
    }

    /**
     * Checks whether Cassandra has RWX permissions to the specified directory.  Logs an error with
     * the details if it does not.
     *
     * @param dir File object of the directory.
     * @param dataDir String representation of the directory's location
     * @return status representing Cassandra's RWX permissions to the supplied folder location.
     */
    public static boolean verifyFullPermissions(File dir, String dataDir)
    {
        if (!dir.isDirectory())
        {
            logger.error("Not a directory {}", dataDir);
            return false;
        }
        else if (!FileAction.hasPrivilege(dir, FileAction.X))
        {
            logger.error("Doesn't have execute permissions for {} directory", dataDir);
            return false;
        }
        else if (!FileAction.hasPrivilege(dir, FileAction.R))
        {
            logger.error("Doesn't have read permissions for {} directory", dataDir);
            return false;
        }
        else if (dir.exists() && !FileAction.hasPrivilege(dir, FileAction.W))
        {
            logger.error("Doesn't have write permissions for {} directory", dataDir);
            return false;
        }

        return true;
    }

    public enum FileAction
    {
        X, W, XW, R, XR, RW, XRW;

        private FileAction()
        {
        }

        public static boolean hasPrivilege(File file, FileAction action)
        {
            boolean privilege = false;

            switch (action) {
                case X:
                    privilege = file.canExecute();
                    break;
                case W:
                    privilege = file.canWrite();
                    break;
                case XW:
                    privilege = file.canExecute() && file.canWrite();
                    break;
                case R:
                    privilege = file.canRead();
                    break;
                case XR:
                    privilege = file.canExecute() && file.canRead();
                    break;
                case RW:
                    privilege = file.canRead() && file.canWrite();
                    break;
                case XRW:
                    privilege = file.canExecute() && file.canRead() && file.canWrite();
                    break;
            }
            return privilege;
        }
    }

    private final CFMetaData metadata;
    private final File[] dataPaths;

    /**
     * Create Directories of given ColumnFamily.
     * SSTable directories are created under data_directories defined in cassandra.yaml if not exist at this time.
     *
     * @param metadata metadata of ColumnFamily
     */
    public Directories(CFMetaData metadata)
    {
        this.metadata = metadata;
        if (StorageService.instance.isClientMode())
        {
            dataPaths = null;
            return;
        }

        String cfId = ByteBufferUtil.bytesToHex(ByteBufferUtil.bytes(metadata.cfId));
        int idx = metadata.cfName.indexOf(SECONDARY_INDEX_NAME_SEPARATOR);
        // secondary indicies go in the same directory as the base cf
        String directoryName = idx > 0 ? metadata.cfName.substring(0, idx) + "-" + cfId : metadata.cfName + "-" + cfId;

        this.dataPaths = new File[dataDirectories.length];
        // If upgraded from version less than 2.1, use existing directories
        for (int i = 0; i < dataDirectories.length; ++i)
        {
            // check if old SSTable directory exists
            dataPaths[i] = new File(dataDirectories[i].location,
                                    join(metadata.ksName,
                                         idx > 0 ? metadata.cfName.substring(0, idx) : metadata.cfName));
        }
        boolean olderDirectoryExists = Iterables.any(Arrays.asList(dataPaths), new Predicate<File>()
        {
            public boolean apply(File file)
            {
                return file.exists();
            }
        });
        if (!olderDirectoryExists)
        {
            // use 2.1-style path names
            for (int i = 0; i < dataDirectories.length; ++i)
                dataPaths[i] = new File(dataDirectories[i].location, join(metadata.ksName, directoryName));
        }

        for (File dir : dataPaths)
        {
            try
            {
                FileUtils.createDirectory(dir);
            }
            catch (FSError e)
            {
                // don't just let the default exception handler do this, we need the create loop to continue
                logger.error("Failed to create {} directory", dir);
                FileUtils.handleFSError(e);
            }
        }
    }

    /**
     * Returns SSTable location which is inside given data directory.
     *
     * @param dataDirectory
     * @return SSTable location
     */
    public File getLocationForDisk(DataDirectory dataDirectory)
    {
        if (dataDirectory != null)
            for (File dir : dataPaths)
                if (dir.getAbsolutePath().startsWith(dataDirectory.location.getAbsolutePath()))
                    return dir;
        return null;
    }

    public Descriptor find(String filename)
    {
        for (File dir : dataPaths)
        {
            if (new File(dir, filename).exists())
                return Descriptor.fromFilename(dir, filename).left;
        }
        return null;
    }

    /**
     * Basically the same as calling {@link #getWriteableLocationAsFile(long)} with an unknown size ({@code -1L}),
     * which may return any non-blacklisted directory - even a data directory that has no usable space.
     * Do not use this method in production code.
     *
     * @throws IOError if all directories are blacklisted.
     */
    public File getDirectoryForNewSSTables()
    {
        return getWriteableLocationAsFile(-1L);
    }

    /**
     * Returns a non-blacklisted data directory that _currently_ has {@code writeSize} bytes as usable space.
     *
     * @throws IOError if all directories are blacklisted.
     */
    public File getWriteableLocationAsFile(long writeSize)
    {
        return getLocationForDisk(getWriteableLocation(writeSize));
    }

    /**
     * Returns a non-blacklisted data directory that _currently_ has {@code writeSize} bytes as usable space.
     *
     * @throws IOError if all directories are blacklisted.
     */
    public DataDirectory getWriteableLocation(long writeSize)
    {
        List<DataDirectoryCandidate> candidates = new ArrayList<>();

        long totalAvailable = 0L;

        // pick directories with enough space and so that resulting sstable dirs aren't blacklisted for writes.
        boolean tooBig = false;
        for (DataDirectory dataDir : dataDirectories)
        {
            if (BlacklistedDirectories.isUnwritable(getLocationForDisk(dataDir)))
            {
                logger.debug("removing blacklisted candidate {}", dataDir.location);
                continue;
            }
            DataDirectoryCandidate candidate = new DataDirectoryCandidate(dataDir);
            // exclude directory if its total writeSize does not fit to data directory
            if (candidate.availableSpace < writeSize)
            {
                logger.debug("removing candidate {}, usable={}, requested={}", candidate.dataDirectory.location, candidate.availableSpace, writeSize);
                tooBig = true;
                continue;
            }
            candidates.add(candidate);
            totalAvailable += candidate.availableSpace;
        }

        if (candidates.isEmpty())
            if (tooBig)
                return null;
            else
                throw new IOError(new IOException("All configured data directories have been blacklisted as unwritable for erroring out"));

        // shortcut for single data directory systems
        if (candidates.size() == 1)
            return candidates.get(0).dataDirectory;

        sortWriteableCandidates(candidates, totalAvailable);

        return pickWriteableDirectory(candidates);
    }

    // separated for unit testing
    static DataDirectory pickWriteableDirectory(List<DataDirectoryCandidate> candidates)
    {
        // weighted random
        double rnd = ThreadLocalRandom.current().nextDouble();
        for (DataDirectoryCandidate candidate : candidates)
        {
            rnd -= candidate.perc;
            if (rnd <= 0)
                return candidate.dataDirectory;
        }

        // last resort
        return candidates.get(0).dataDirectory;
    }

    // separated for unit testing
    static void sortWriteableCandidates(List<DataDirectoryCandidate> candidates, long totalAvailable)
    {
        // calculate free-space-percentage
        for (DataDirectoryCandidate candidate : candidates)
            candidate.calcFreePerc(totalAvailable);

        // sort directories by perc
        Collections.sort(candidates);
    }

    public boolean hasAvailableDiskSpace(long estimatedSSTables, long expectedTotalWriteSize)
    {
        long writeSize = expectedTotalWriteSize / estimatedSSTables;
        long totalAvailable = 0L;

        for (DataDirectory dataDir : dataDirectories)
        {
            if (BlacklistedDirectories.isUnwritable(getLocationForDisk(dataDir)))
                  continue;
            DataDirectoryCandidate candidate = new DataDirectoryCandidate(dataDir);
            // exclude directory if its total writeSize does not fit to data directory
            if (candidate.availableSpace < writeSize)
                continue;
            totalAvailable += candidate.availableSpace;
        }
        return totalAvailable > expectedTotalWriteSize;
    }

    public static File getSnapshotDirectory(Descriptor desc, String snapshotName)
    {
        return getOrCreate(desc.directory, SNAPSHOT_SUBDIR, snapshotName);
    }

    public File getSnapshotManifestFile(String snapshotName)
    {
         return new File(getDirectoryForNewSSTables(), join(SNAPSHOT_SUBDIR, snapshotName, "manifest.json"));
    }

    public static File getBackupsDirectory(Descriptor desc)
    {
        return getOrCreate(desc.directory, BACKUPS_SUBDIR);
    }

    public SSTableLister sstableLister()
    {
        return new SSTableLister();
    }

    public static class DataDirectory
    {
        public final File location;

        public DataDirectory(File location)
        {
            this.location = location;
        }

        public long getAvailableSpace()
        {
            return location.getUsableSpace();
        }
    }

    static final class DataDirectoryCandidate implements Comparable<DataDirectoryCandidate>
    {
        final DataDirectory dataDirectory;
        final long availableSpace;
        double perc;

        public DataDirectoryCandidate(DataDirectory dataDirectory)
        {
            this.dataDirectory = dataDirectory;
            this.availableSpace = dataDirectory.getAvailableSpace();
        }

        void calcFreePerc(long totalAvailableSpace)
        {
            double w = availableSpace;
            w /= totalAvailableSpace;
            perc = w;
        }

        public int compareTo(DataDirectoryCandidate o)
        {
            if (this == o)
                return 0;

            int r = Double.compare(perc, o.perc);
            if (r != 0)
                return -r;
            // last resort
            return System.identityHashCode(this) - System.identityHashCode(o);
        }
    }

    public class SSTableLister
    {
        private boolean skipTemporary;
        private boolean includeBackups;
        private boolean onlyBackups;
        private int nbFiles;
        private final Map<Descriptor, Set<Component>> components = new HashMap<>();
        private boolean filtered;
        private String snapshotName;

        public SSTableLister skipTemporary(boolean b)
        {
            if (filtered)
                throw new IllegalStateException("list() has already been called");
            skipTemporary = b;
            return this;
        }

        public SSTableLister includeBackups(boolean b)
        {
            if (filtered)
                throw new IllegalStateException("list() has already been called");
            includeBackups = b;
            return this;
        }

        public SSTableLister onlyBackups(boolean b)
        {
            if (filtered)
                throw new IllegalStateException("list() has already been called");
            onlyBackups = b;
            includeBackups = b;
            return this;
        }

        public SSTableLister snapshots(String sn)
        {
            if (filtered)
                throw new IllegalStateException("list() has already been called");
            snapshotName = sn;
            return this;
        }

        public Map<Descriptor, Set<Component>> list()
        {
            filter();
            return ImmutableMap.copyOf(components);
        }

        public List<File> listFiles()
        {
            filter();
            List<File> l = new ArrayList<>(nbFiles);
            for (Map.Entry<Descriptor, Set<Component>> entry : components.entrySet())
            {
                for (Component c : entry.getValue())
                {
                    l.add(new File(entry.getKey().filenameFor(c)));
                }
            }
            return l;
        }

        private void filter()
        {
            if (filtered)
                return;

            for (File location : dataPaths)
            {
                if (BlacklistedDirectories.isUnreadable(location))
                    continue;

                if (snapshotName != null)
                {
                    new File(location, join(SNAPSHOT_SUBDIR, snapshotName)).listFiles(getFilter());
                    continue;
                }

                if (!onlyBackups)
                    location.listFiles(getFilter());

                if (includeBackups)
                    new File(location, BACKUPS_SUBDIR).listFiles(getFilter());
            }
            filtered = true;
        }

        private FileFilter getFilter()
        {
            // Note: the prefix needs to include cfname + separator to distinguish between a cfs and it's secondary indexes
            final String sstablePrefix = getSSTablePrefix();
            return new FileFilter()
            {
                // This function always return false since accepts adds to the components map
                public boolean accept(File file)
                {
                    // we are only interested in the SSTable files that belong to the specific ColumnFamily
                    if (file.isDirectory() || !file.getName().startsWith(sstablePrefix))
                        return false;

                    Pair<Descriptor, Component> pair = SSTable.tryComponentFromFilename(file.getParentFile(), file.getName());
                    if (pair == null)
                        return false;

                    if (skipTemporary && pair.left.type.isTemporary)
                        return false;

                    Set<Component> previous = components.get(pair.left);
                    if (previous == null)
                    {
                        previous = new HashSet<>();
                        components.put(pair.left, previous);
                    }
                    previous.add(pair.right);
                    nbFiles++;
                    return false;
                }
            };
        }
    }

    /**
     *
     * @return  Return a map of all snapshots to space being used
     * The pair for a snapshot has size on disk and true size.
     */
    public Map<String, Pair<Long, Long>> getSnapshotDetails()
    {
        final Map<String, Pair<Long, Long>> snapshotSpaceMap = new HashMap<>();
        for (final File dir : dataPaths)
        {
            final File snapshotDir = new File(dir,SNAPSHOT_SUBDIR);
            if (snapshotDir.exists() && snapshotDir.isDirectory())
            {
                final File[] snapshots  = snapshotDir.listFiles();
                if (snapshots != null)
                {
                    for (final File snapshot : snapshots)
                    {
                        if (snapshot.isDirectory())
                        {
                            final long sizeOnDisk = FileUtils.folderSize(snapshot);
                            final long trueSize = getTrueAllocatedSizeIn(snapshot);
                            Pair<Long,Long> spaceUsed = snapshotSpaceMap.get(snapshot.getName());
                            if (spaceUsed == null)
                                spaceUsed =  Pair.create(sizeOnDisk,trueSize);
                            else
                                spaceUsed = Pair.create(spaceUsed.left + sizeOnDisk, spaceUsed.right + trueSize);
                            snapshotSpaceMap.put(snapshot.getName(), spaceUsed);
                        }
                    }
                }
            }
        }

        return snapshotSpaceMap;
    }
    public boolean snapshotExists(String snapshotName)
    {
        for (File dir : dataPaths)
        {
            File snapshotDir = new File(dir, join(SNAPSHOT_SUBDIR, snapshotName));
            if (snapshotDir.exists())
                return true;
        }
        return false;
    }

    public static void clearSnapshot(String snapshotName, List<File> snapshotDirectories)
    {
        // If snapshotName is empty or null, we will delete the entire snapshot directory
        String tag = snapshotName == null ? "" : snapshotName;
        for (File dir : snapshotDirectories)
        {
            File snapshotDir = new File(dir, join(SNAPSHOT_SUBDIR, tag));
            if (snapshotDir.exists())
            {
                if (logger.isDebugEnabled())
                    logger.debug("Removing snapshot directory {}", snapshotDir);
                FileUtils.deleteRecursive(snapshotDir);
            }
        }
    }

    // The snapshot must exist
    public long snapshotCreationTime(String snapshotName)
    {
        for (File dir : dataPaths)
        {
            File snapshotDir = new File(dir, join(SNAPSHOT_SUBDIR, snapshotName));
            if (snapshotDir.exists())
                return snapshotDir.lastModified();
        }
        throw new RuntimeException("Snapshot " + snapshotName + " doesn't exist");
    }
    
    public long trueSnapshotsSize()
    {
        long result = 0L;
        for (File dir : dataPaths)
            result += getTrueAllocatedSizeIn(new File(dir, join(SNAPSHOT_SUBDIR)));
        return result;
    }

    private String getSSTablePrefix()
    {
        return metadata.ksName + Component.separator + metadata.cfName + Component.separator;
    }

    public long getTrueAllocatedSizeIn(File input)
    {
        if (!input.isDirectory())
            return 0;
        
        TrueFilesSizeVisitor visitor = new TrueFilesSizeVisitor();
        try
        {
            Files.walkFileTree(input.toPath(), visitor);
        }
        catch (IOException e)
        {
            logger.error("Could not calculate the size of {}. {}", input, e);
        }
    
        return visitor.getAllocatedSize();
    }

    // Recursively finds all the sub directories in the KS directory.
    public static List<File> getKSChildDirectories(String ksName)
    {
        List<File> result = new ArrayList<>();
        for (DataDirectory dataDirectory : dataDirectories)
        {
            File ksDir = new File(dataDirectory.location, ksName);
            File[] cfDirs = ksDir.listFiles();
            if (cfDirs == null)
                continue;
            for (File cfDir : cfDirs)
            {
                if (cfDir.isDirectory())
                    result.add(cfDir);
            }
        }
        return result;
    }

    public List<File> getCFDirectories()
    {
        List<File> result = new ArrayList<>();
        for (File dataDirectory : dataPaths)
        {
            if (dataDirectory.isDirectory())
                result.add(dataDirectory);
        }
        return result;
    }

    private static File getOrCreate(File base, String... subdirs)
    {
        File dir = subdirs == null || subdirs.length == 0 ? base : new File(base, join(subdirs));
        if (dir.exists())
        {
            if (!dir.isDirectory())
                throw new AssertionError(String.format("Invalid directory path %s: path exists but is not a directory", dir));
        }
        else if (!dir.mkdirs() && !(dir.exists() && dir.isDirectory()))
        {
            throw new FSWriteError(new IOException("Unable to create directory " + dir), dir);
        }
        return dir;
    }

    private static String join(String... s)
    {
        return StringUtils.join(s, File.separator);
    }

    @VisibleForTesting
    static void overrideDataDirectoriesForTest(String loc)
    {
        for (int i = 0; i < dataDirectories.length; ++i)
            dataDirectories[i] = new DataDirectory(new File(loc));
    }

    @VisibleForTesting
    static void resetDataDirectoriesAfterTest()
    {
        String[] locations = DatabaseDescriptor.getAllDataFileLocations();
        for (int i = 0; i < locations.length; ++i)
            dataDirectories[i] = new DataDirectory(new File(locations[i]));
    }
    
    private class TrueFilesSizeVisitor extends SimpleFileVisitor<Path>
    {
        private final AtomicLong size = new AtomicLong(0);
        private final Set<String> visited = newHashSet(); //count each file only once
        private final Set<String> alive;
        private final String prefix = getSSTablePrefix();

        public TrueFilesSizeVisitor()
        {
            super();
            Builder<String> builder = ImmutableSet.builder();
            for (File file: sstableLister().listFiles())
                builder.add(file.getName());
            alive = builder.build();
        }

        private boolean isAcceptable(Path file)
        {
            String fileName = file.toFile().getName(); 
            return fileName.startsWith(prefix)
                    && !visited.contains(fileName)
                    && !alive.contains(fileName);
        }

        @Override
        public FileVisitResult visitFile(Path file, BasicFileAttributes attrs) throws IOException
        {
            if (isAcceptable(file))
            {
                size.addAndGet(attrs.size());
                visited.add(file.toFile().getName());
            }
            return FileVisitResult.CONTINUE;
        }

        @Override
        public FileVisitResult visitFileFailed(Path file, IOException exc) throws IOException 
        {
            return FileVisitResult.CONTINUE;
        }
        
        public long getAllocatedSize()
        {
            return size.get();
        }
    }
}


File: src/java/org/apache/cassandra/repair/RepairMessageVerbHandler.java
/*
 * Licensed to the Apache Software Foundation (ASF) under one
 * or more contributor license agreements.  See the NOTICE file
 * distributed with this work for additional information
 * regarding copyright ownership.  The ASF licenses this file
 * to you under the Apache License, Version 2.0 (the
 * "License"); you may not use this file except in compliance
 * with the License.  You may obtain a copy of the License at
 *
 *     http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 */
package org.apache.cassandra.repair;

import java.util.ArrayList;
import java.util.Collections;
import java.util.List;
import java.util.UUID;

import com.google.common.base.Predicate;
import com.google.common.util.concurrent.ListenableFuture;
import com.google.common.util.concurrent.MoreExecutors;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import org.apache.cassandra.config.Schema;
import org.apache.cassandra.db.ColumnFamilyStore;
import org.apache.cassandra.db.Keyspace;
import org.apache.cassandra.db.compaction.CompactionManager;
import org.apache.cassandra.dht.Bounds;
import org.apache.cassandra.dht.LocalPartitioner;
import org.apache.cassandra.dht.Range;
import org.apache.cassandra.dht.Token;
import org.apache.cassandra.io.sstable.SSTableReader;
import org.apache.cassandra.net.IVerbHandler;
import org.apache.cassandra.net.MessageIn;
import org.apache.cassandra.net.MessageOut;
import org.apache.cassandra.net.MessagingService;
import org.apache.cassandra.repair.messages.*;
import org.apache.cassandra.service.ActiveRepairService;
import org.apache.cassandra.utils.Pair;

/**
 * Handles all repair related message.
 *
 * @since 2.0
 */
public class RepairMessageVerbHandler implements IVerbHandler<RepairMessage>
{
    private static final Logger logger = LoggerFactory.getLogger(RepairMessageVerbHandler.class);
    public void doVerb(final MessageIn<RepairMessage> message, final int id)
    {
        // TODO add cancel/interrupt message
        RepairJobDesc desc = message.payload.desc;
        try
        {
            switch (message.payload.messageType)
            {
                case PREPARE_MESSAGE:
                    PrepareMessage prepareMessage = (PrepareMessage) message.payload;
                    List<ColumnFamilyStore> columnFamilyStores = new ArrayList<>(prepareMessage.cfIds.size());
                    for (UUID cfId : prepareMessage.cfIds)
                    {
                        Pair<String, String> kscf = Schema.instance.getCF(cfId);
                        ColumnFamilyStore columnFamilyStore = Keyspace.open(kscf.left).getColumnFamilyStore(kscf.right);
                        columnFamilyStores.add(columnFamilyStore);
                    }
                    ActiveRepairService.instance.registerParentRepairSession(prepareMessage.parentRepairSession,
                            columnFamilyStores,
                            prepareMessage.ranges);
                    MessagingService.instance().sendReply(new MessageOut(MessagingService.Verb.INTERNAL_RESPONSE), id, message.from);
                    break;

                case SNAPSHOT:
                    ColumnFamilyStore cfs = Keyspace.open(desc.keyspace).getColumnFamilyStore(desc.columnFamily);
                    final Range<Token> repairingRange = desc.range;
                    cfs.snapshot(desc.sessionId.toString(), new Predicate<SSTableReader>()
                    {
                        public boolean apply(SSTableReader sstable)
                        {
                            return sstable != null &&
                                    !(sstable.partitioner instanceof LocalPartitioner) && // exclude SSTables from 2i
                                    new Bounds<>(sstable.first.getToken(), sstable.last.getToken()).intersects(Collections.singleton(repairingRange));
                        }
                    });

                    logger.debug("Enqueuing response to snapshot request {} to {}", desc.sessionId, message.from);
                    MessagingService.instance().sendReply(new MessageOut(MessagingService.Verb.INTERNAL_RESPONSE), id, message.from);
                    break;

                case VALIDATION_REQUEST:
                    ValidationRequest validationRequest = (ValidationRequest) message.payload;
                    // trigger read-only compaction
                    ColumnFamilyStore store = Keyspace.open(desc.keyspace).getColumnFamilyStore(desc.columnFamily);

                    Validator validator = new Validator(desc, message.from, validationRequest.gcBefore);
                    CompactionManager.instance.submitValidation(store, validator);
                    break;

                case SYNC_REQUEST:
                    // forwarded sync request
                    SyncRequest request = (SyncRequest) message.payload;
                    StreamingRepairTask task = new StreamingRepairTask(desc, request);
                    task.run();
                    break;

                case ANTICOMPACTION_REQUEST:
                    logger.debug("Got anticompaction request");
                    AnticompactionRequest anticompactionRequest = (AnticompactionRequest) message.payload;
                    ListenableFuture<?> compactionDone = ActiveRepairService.instance.doAntiCompaction(anticompactionRequest.parentRepairSession);
                    compactionDone.addListener(new Runnable()
                    {
                        @Override
                        public void run()
                        {
                            MessagingService.instance().sendReply(new MessageOut(MessagingService.Verb.INTERNAL_RESPONSE), id, message.from);
                        }
                    }, MoreExecutors.sameThreadExecutor());
                    break;

                case CLEANUP:
                    logger.debug("cleaning up repair");
                    CleanupMessage cleanup = (CleanupMessage) message.payload;
                    ActiveRepairService.instance.removeParentRepairSession(cleanup.parentRepairSession);
                    MessagingService.instance().sendReply(new MessageOut(MessagingService.Verb.INTERNAL_RESPONSE), id, message.from);
                    break;

                default:
                    ActiveRepairService.instance.handleMessage(message.from, message.payload);
                    break;
            }
        }
        catch (Exception e)
        {
            logger.error("Got error, removing parent repair session");
            if (desc!=null && desc.parentSessionId != null)
                ActiveRepairService.instance.removeParentRepairSession(desc.parentSessionId);
            throw new RuntimeException(e);
        }
    }
}


File: src/java/org/apache/cassandra/service/CassandraDaemon.java
/*
 * Licensed to the Apache Software Foundation (ASF) under one
 * or more contributor license agreements.  See the NOTICE file
 * distributed with this work for additional information
 * regarding copyright ownership.  The ASF licenses this file
 * to you under the Apache License, Version 2.0 (the
 * "License"); you may not use this file except in compliance
 * with the License.  You may obtain a copy of the License at
 *
 *     http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 */
package org.apache.cassandra.service;

import java.io.File;
import java.io.IOException;
import java.lang.management.ManagementFactory;
import java.lang.management.MemoryPoolMXBean;
import java.net.InetAddress;
import java.net.UnknownHostException;
import java.rmi.registry.LocateRegistry;
import java.rmi.server.RMIServerSocketFactory;
import java.util.*;
import java.util.concurrent.TimeUnit;
import javax.management.MBeanServer;
import javax.management.ObjectName;
import javax.management.StandardMBean;
import javax.management.remote.JMXConnectorServer;
import javax.management.remote.JMXServiceURL;
import javax.management.remote.rmi.RMIConnectorServer;

import com.google.common.collect.Iterables;
import com.google.common.util.concurrent.Uninterruptibles;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import com.addthis.metrics.reporter.config.ReporterConfig;
import org.apache.cassandra.concurrent.JMXEnabledThreadPoolExecutor;
import org.apache.cassandra.concurrent.ScheduledExecutors;
import org.apache.cassandra.concurrent.Stage;
import org.apache.cassandra.concurrent.StageManager;
import org.apache.cassandra.config.CFMetaData;
import org.apache.cassandra.config.DatabaseDescriptor;
import org.apache.cassandra.config.Schema;
import org.apache.cassandra.db.*;
import org.apache.cassandra.db.commitlog.CommitLog;
import org.apache.cassandra.db.compaction.CompactionManager;
import org.apache.cassandra.exceptions.ConfigurationException;
import org.apache.cassandra.io.FSError;
import org.apache.cassandra.io.sstable.CorruptSSTableException;
import org.apache.cassandra.io.util.FileUtils;
import org.apache.cassandra.metrics.StorageMetrics;
import org.apache.cassandra.thrift.ThriftServer;
import org.apache.cassandra.tracing.Tracing;
import org.apache.cassandra.utils.*;

/**
 * The <code>CassandraDaemon</code> is an abstraction for a Cassandra daemon
 * service, which defines not only a way to activate and deactivate it, but also
 * hooks into its lifecycle methods (see {@link #setup()}, {@link #start()},
 * {@link #stop()} and {@link #setup()}).
 */
public class CassandraDaemon
{
    public static final String MBEAN_NAME = "org.apache.cassandra.db:type=NativeAccess";
    public static JMXConnectorServer jmxServer = null;

    private static final Logger logger = LoggerFactory.getLogger(CassandraDaemon.class);

    private static void maybeInitJmx()
    {
        String jmxPort = System.getProperty("com.sun.management.jmxremote.port");

        if (jmxPort == null)
        {
            logger.warn("JMX is not enabled to receive remote connections. Please see cassandra-env.sh for more info.");

            jmxPort = System.getProperty("cassandra.jmx.local.port");

            if (jmxPort == null)
            {
                logger.error("cassandra.jmx.local.port missing from cassandra-env.sh, unable to start local JMX service." + jmxPort);
            }
            else
            {
                System.setProperty("java.rmi.server.hostname", InetAddress.getLoopbackAddress().getHostAddress());

                try
                {
                    RMIServerSocketFactory serverFactory = new RMIServerSocketFactoryImpl();
                    LocateRegistry.createRegistry(Integer.valueOf(jmxPort), null, serverFactory);

                    StringBuffer url = new StringBuffer();
                    url.append("service:jmx:");
                    url.append("rmi://localhost/jndi/");
                    url.append("rmi://localhost:").append(jmxPort).append("/jmxrmi");
                    
                    Map env = new HashMap();
                    env.put(RMIConnectorServer.RMI_SERVER_SOCKET_FACTORY_ATTRIBUTE, serverFactory);

                    jmxServer = new RMIConnectorServer(
                            new JMXServiceURL(url.toString()),
                            env,
                            ManagementFactory.getPlatformMBeanServer()
                    );

                    jmxServer.start();
                }
                catch (IOException e)
                {
                    logger.error("Error starting local jmx server: ", e);
                }
            }
        }
        else
        {
            logger.info("JMX is enabled to receive remote connections on port: " + jmxPort);
        }
    }

    private static final CassandraDaemon instance = new CassandraDaemon();

    /**
     * The earliest legit timestamp a casandra instance could have ever launched.
     * Date roughly taken from http://perspectives.mvdirona.com/2008/07/12/FacebookReleasesCassandraAsOpenSource.aspx
     * We use this to ensure the system clock is at least somewhat correct at startup.
     */
    private static final long EARLIEST_LAUNCH_DATE = 1215820800000L;

    public Server thriftServer;
    public Server nativeServer;
    private boolean setupCompleted = false;
    /**
     * This is a hook for concrete daemons to initialize themselves suitably.
     *
     * Subclasses should override this to finish the job (listening on ports, etc.)
     *
     * @throws IOException
     */
    protected void setup()
    {
        try 
        {
            logger.info("Hostname: {}", InetAddress.getLocalHost().getHostName());
        }
        catch (UnknownHostException e1)
        {
            logger.info("Could not resolve local host");
        }

        long now = System.currentTimeMillis();
        if (now < EARLIEST_LAUNCH_DATE)
        {
            logger.error("current machine time is {}, but that is seemingly incorrect. exiting now.", new Date(now));
            System.exit(3);
        }

        // log warnings for different kinds of sub-optimal JVMs.  tldr use 64-bit Oracle >= 1.6u32
        if (!DatabaseDescriptor.hasLargeAddressSpace())
            logger.info("32bit JVM detected.  It is recommended to run Cassandra on a 64bit JVM for better performance.");
        String javaVersion = System.getProperty("java.version");
        String javaVmName = System.getProperty("java.vm.name");
        logger.info("JVM vendor/version: {}/{}", javaVmName, javaVersion);
        if (javaVmName.contains("OpenJDK"))
        {
            // There is essentially no QA done on OpenJDK builds, and
            // clusters running OpenJDK have seen many heap and load issues.
            logger.warn("OpenJDK is not recommended. Please upgrade to the newest Oracle Java release");
        }
        else if (!javaVmName.contains("HotSpot"))
        {
            logger.warn("Non-Oracle JVM detected.  Some features, such as immediate unmap of compacted SSTables, may not work as intended");
        }
     /*   else
        {
            String[] java_version = javaVersion.split("_");
            String java_major = java_version[0];
            int java_minor;
            try
            {
                java_minor = (java_version.length > 1) ? Integer.parseInt(java_version[1]) : 0;
            }
            catch (NumberFormatException e)
            {
                // have only seen this with java7 so far but no doubt there are other ways to break this
                logger.info("Unable to parse java version {}", Arrays.toString(java_version));
                java_minor = 32;
            }
        }
     */
        logger.info("Heap size: {}/{}", Runtime.getRuntime().totalMemory(), Runtime.getRuntime().maxMemory());
        for(MemoryPoolMXBean pool: ManagementFactory.getMemoryPoolMXBeans())
            logger.info("{} {}: {}", pool.getName(), pool.getType(), pool.getPeakUsage());
        logger.info("Classpath: {}", System.getProperty("java.class.path"));

        // Fail-fast if JNA is not available or failing to initialize properly
        // except with -Dcassandra.boot_without_jna=true. See CASSANDRA-6575.
        if (!CLibrary.jnaAvailable())
        {
            boolean jnaRequired = !Boolean.getBoolean("cassandra.boot_without_jna");

            if (jnaRequired)
            {
                logger.error("JNA failing to initialize properly. Use -Dcassandra.boot_without_jna=true to bootstrap even so.");
                System.exit(3);
            }
        }

        CLibrary.tryMlockall();

        maybeInitJmx();

        Thread.setDefaultUncaughtExceptionHandler(new Thread.UncaughtExceptionHandler()
        {
            public void uncaughtException(Thread t, Throwable e)
            {
                StorageMetrics.exceptions.inc();
                logger.error("Exception in thread {}", t, e);
                Tracing.trace("Exception in thread {}", t, e);
                for (Throwable e2 = e; e2 != null; e2 = e2.getCause())
                {
                    JVMStabilityInspector.inspectThrowable(e2);

                    if (e2 instanceof FSError)
                    {
                        if (e2 != e) // make sure FSError gets logged exactly once.
                            logger.error("Exception in thread {}", t, e2);
                        FileUtils.handleFSError((FSError) e2);
                    }

                    if (e2 instanceof CorruptSSTableException)
                    {
                        if (e2 != e)
                            logger.error("Exception in thread " + t, e2);
                        FileUtils.handleCorruptSSTable((CorruptSSTableException) e2);
                    }
                }
            }
        });

        // check all directories(data, commitlog, saved cache) for existence and permission
        Iterable<String> dirs = Iterables.concat(Arrays.asList(DatabaseDescriptor.getAllDataFileLocations()),
                                                 Arrays.asList(DatabaseDescriptor.getCommitLogLocation(),
                                                               DatabaseDescriptor.getSavedCachesLocation()));
        for (String dataDir : dirs)
        {
            logger.debug("Checking directory {}", dataDir);
            File dir = new File(dataDir);

            // check that directories exist.
            if (!dir.exists())
            {
                logger.error("Directory {} doesn't exist", dataDir);
                // if they don't, failing their creation, stop cassandra.
                if (!dir.mkdirs())
                {
                    logger.error("Has no permission to create {} directory", dataDir);
                    System.exit(3);
                }
            }
            // if directories exist verify their permissions
            if (!Directories.verifyFullPermissions(dir, dataDir))
            {
                // if permissions aren't sufficient, stop cassandra.
                System.exit(3);
            }
        }

        if (CacheService.instance == null) // should never happen
            throw new RuntimeException("Failed to initialize Cache Service.");

        // check the system keyspace to keep user from shooting self in foot by changing partitioner, cluster name, etc.
        // we do a one-off scrub of the system keyspace first; we can't load the list of the rest of the keyspaces,
        // until system keyspace is opened.
        for (CFMetaData cfm : Schema.instance.getKeyspaceMetaData(Keyspace.SYSTEM_KS).values())
            ColumnFamilyStore.scrubDataDirectories(cfm);
        try
        {
            SystemKeyspace.checkHealth();
        }
        catch (ConfigurationException e)
        {
            logger.error("Fatal exception during initialization", e);
            System.exit(100);
        }

        // load keyspace descriptions.
        DatabaseDescriptor.loadSchemas();

        // clean up compaction leftovers
        Map<Pair<String, String>, Map<Integer, UUID>> unfinishedCompactions = SystemKeyspace.getUnfinishedCompactions();
        for (Pair<String, String> kscf : unfinishedCompactions.keySet())
        {
            CFMetaData cfm = Schema.instance.getCFMetaData(kscf.left, kscf.right);
            // CFMetaData can be null if CF is already dropped
            if (cfm != null)
                ColumnFamilyStore.removeUnfinishedCompactionLeftovers(cfm, unfinishedCompactions.get(kscf));
        }
        SystemKeyspace.discardCompactionsInProgress();

        // clean up debris in the rest of the keyspaces
        for (String keyspaceName : Schema.instance.getKeyspaces())
        {
            // Skip system as we've already cleaned it
            if (keyspaceName.equals(Keyspace.SYSTEM_KS))
                continue;

            for (CFMetaData cfm : Schema.instance.getKeyspaceMetaData(keyspaceName).values())
                ColumnFamilyStore.scrubDataDirectories(cfm);
        }

        Keyspace.setInitialized();
        // initialize keyspaces
        for (String keyspaceName : Schema.instance.getKeyspaces())
        {
            if (logger.isDebugEnabled())
                logger.debug("opening keyspace {}", keyspaceName);
            // disable auto compaction until commit log replay ends
            for (ColumnFamilyStore cfs : Keyspace.open(keyspaceName).getColumnFamilyStores())
            {
                for (ColumnFamilyStore store : cfs.concatWithIndexes())
                {
                    store.disableAutoCompaction();
                }
            }
        }

        if (CacheService.instance.keyCache.size() > 0)
            logger.info("completed pre-loading ({} keys) key cache.", CacheService.instance.keyCache.size());

        if (CacheService.instance.rowCache.size() > 0)
            logger.info("completed pre-loading ({} keys) row cache.", CacheService.instance.rowCache.size());

        try
        {
            GCInspector.register();
        }
        catch (Throwable t)
        {
            JVMStabilityInspector.inspectThrowable(t);
            logger.warn("Unable to start GCInspector (currently only supported on the Sun JVM)");
        }

        // replay the log if necessary
        try
        {
            CommitLog.instance.recover();
        }
        catch (IOException e)
        {
            throw new RuntimeException(e);
        }

        // enable auto compaction
        for (Keyspace keyspace : Keyspace.all())
        {
            for (ColumnFamilyStore cfs : keyspace.getColumnFamilyStores())
            {
                for (final ColumnFamilyStore store : cfs.concatWithIndexes())
                {
                    if (store.getCompactionStrategy().shouldBeEnabled())
                        store.enableAutoCompaction();
                }
            }
        }

        SystemKeyspace.finishStartup();

        // start server internals
        StorageService.instance.registerDaemon(this);
        try
        {
            StorageService.instance.initServer();
        }
        catch (ConfigurationException e)
        {
            logger.error("Fatal configuration error", e);
            System.err.println(e.getMessage() + "\nFatal configuration error; unable to start server.  See log for stacktrace.");
            System.exit(1);
        }

        Mx4jTool.maybeLoad();

        // Metrics
        String metricsReporterConfigFile = System.getProperty("cassandra.metricsReporterConfigFile");
        if (metricsReporterConfigFile != null)
        {
            logger.info("Trying to load metrics-reporter-config from file: {}", metricsReporterConfigFile);
            try
            {
                String reportFileLocation = CassandraDaemon.class.getClassLoader().getResource(metricsReporterConfigFile).getFile();
                ReporterConfig.loadFromFile(reportFileLocation).enableAll();
            }
            catch (Exception e)
            {
                logger.warn("Failed to load metrics-reporter-config, metric sinks will not be activated", e);
            }
        }

        if (!FBUtilities.getBroadcastAddress().equals(InetAddress.getLoopbackAddress()))
            waitForGossipToSettle();

        // schedule periodic background compaction task submission. this is simply a backstop against compactions stalling
        // due to scheduling errors or race conditions
        ScheduledExecutors.optionalTasks.scheduleWithFixedDelay(ColumnFamilyStore.getBackgroundCompactionTaskSubmitter(), 5, 1, TimeUnit.MINUTES);

        // schedule periodic dumps of table size estimates into SystemKeyspace.SIZE_ESTIMATES_CF
        // set cassandra.size_recorder_interval to 0 to disable
        int sizeRecorderInterval = Integer.getInteger("cassandra.size_recorder_interval", 5 * 60);
        if (sizeRecorderInterval > 0)
            ScheduledExecutors.optionalTasks.scheduleWithFixedDelay(SizeEstimatesRecorder.instance, 30, sizeRecorderInterval, TimeUnit.SECONDS);

        // Thrift
        InetAddress rpcAddr = DatabaseDescriptor.getRpcAddress();
        int rpcPort = DatabaseDescriptor.getRpcPort();
        int listenBacklog = DatabaseDescriptor.getRpcListenBacklog();
        thriftServer = new ThriftServer(rpcAddr, rpcPort, listenBacklog);

        // Native transport
        InetAddress nativeAddr = DatabaseDescriptor.getRpcAddress();
        int nativePort = DatabaseDescriptor.getNativeTransportPort();
        nativeServer = new org.apache.cassandra.transport.Server(nativeAddr, nativePort);

        setupCompleted = true;
    }

    public boolean setupCompleted()
    {
        return setupCompleted;
    }

    /**
     * Initialize the Cassandra Daemon based on the given <a
     * href="http://commons.apache.org/daemon/jsvc.html">Commons
     * Daemon</a>-specific arguments. To clarify, this is a hook for JSVC.
     *
     * @param arguments
     *            the arguments passed in from JSVC
     * @throws IOException
     */
    public void init(String[] arguments) throws IOException
    {
        setup();
    }

    /**
     * Start the Cassandra Daemon, assuming that it has already been
     * initialized via {@link #init(String[])}
     *
     * Hook for JSVC
     */
    public void start()
    {
        String nativeFlag = System.getProperty("cassandra.start_native_transport");
        if ((nativeFlag != null && Boolean.parseBoolean(nativeFlag)) || (nativeFlag == null && DatabaseDescriptor.startNativeTransport()))
            nativeServer.start();
        else
            logger.info("Not starting native transport as requested. Use JMX (StorageService->startNativeTransport()) or nodetool (enablebinary) to start it");

        String rpcFlag = System.getProperty("cassandra.start_rpc");
        if ((rpcFlag != null && Boolean.parseBoolean(rpcFlag)) || (rpcFlag == null && DatabaseDescriptor.startRpc()))
            thriftServer.start();
        else
            logger.info("Not starting RPC server as requested. Use JMX (StorageService->startRPCServer()) or nodetool (enablethrift) to start it");
    }

    /**
     * Stop the daemon, ideally in an idempotent manner.
     *
     * Hook for JSVC / Procrun
     */
    public void stop()
    {
        // On linux, this doesn't entirely shut down Cassandra, just the RPC server.
        // jsvc takes care of taking the rest down
        logger.info("Cassandra shutting down...");
        thriftServer.stop();
        nativeServer.stop();

        // On windows, we need to stop the entire system as prunsrv doesn't have the jsvc hooks
        // We rely on the shutdown hook to drain the node
        if (FBUtilities.isWindows())
            System.exit(0);

        if (jmxServer != null)
        {
            try
            {
                jmxServer.stop();
            }
            catch (IOException e)
            {
                logger.error("Error shutting down local JMX server: ", e);
            }
        }
    }


    /**
     * Clean up all resources obtained during the lifetime of the daemon. This
     * is a hook for JSVC.
     */
    public void destroy()
    {}

    /**
     * A convenience method to initialize and start the daemon in one shot.
     */
    public void activate()
    {
        String pidFile = System.getProperty("cassandra-pidfile");

        try
        {
            try
            {
                MBeanServer mbs = ManagementFactory.getPlatformMBeanServer();
                mbs.registerMBean(new StandardMBean(new NativeAccess(), NativeAccessMBean.class), new ObjectName(MBEAN_NAME));
            }
            catch (Exception e)
            {
                logger.error("error registering MBean {}", MBEAN_NAME, e);
                //Allow the server to start even if the bean can't be registered
            }
            
            setup();

            if (pidFile != null)
            {
                new File(pidFile).deleteOnExit();
            }

            if (System.getProperty("cassandra-foreground") == null)
            {
                System.out.close();
                System.err.close();
            }

            start();
        }
        catch (Throwable e)
        {
            logger.error("Exception encountered during startup", e);

            // try to warn user on stdout too, if we haven't already detached
            e.printStackTrace();
            System.out.println("Exception encountered during startup: " + e.getMessage());

            System.exit(3);
        }
    }

    /**
     * A convenience method to stop and destroy the daemon in one shot.
     */
    public void deactivate()
    {
        stop();
        destroy();
    }

    private void waitForGossipToSettle()
    {
        int forceAfter = Integer.getInteger("cassandra.skip_wait_for_gossip_to_settle", -1);
        if (forceAfter == 0)
        {
            return;
        }
        final int GOSSIP_SETTLE_MIN_WAIT_MS = 5000;
        final int GOSSIP_SETTLE_POLL_INTERVAL_MS = 1000;
        final int GOSSIP_SETTLE_POLL_SUCCESSES_REQUIRED = 3;

        logger.info("Waiting for gossip to settle before accepting client requests...");
        Uninterruptibles.sleepUninterruptibly(GOSSIP_SETTLE_MIN_WAIT_MS, TimeUnit.MILLISECONDS);
        int totalPolls = 0;
        int numOkay = 0;
        JMXEnabledThreadPoolExecutor gossipStage = (JMXEnabledThreadPoolExecutor)StageManager.getStage(Stage.GOSSIP);
        while (numOkay < GOSSIP_SETTLE_POLL_SUCCESSES_REQUIRED)
        {
            Uninterruptibles.sleepUninterruptibly(GOSSIP_SETTLE_POLL_INTERVAL_MS, TimeUnit.MILLISECONDS);
            long completed = gossipStage.getCompletedTasks();
            long active = gossipStage.getActiveCount();
            long pending = gossipStage.getPendingTasks();
            totalPolls++;
            if (active == 0 && pending == 0)
            {
                logger.debug("Gossip looks settled. CompletedTasks: {}", completed);
                numOkay++;
            }
            else
            {
                logger.info("Gossip not settled after {} polls. Gossip Stage active/pending/completed: {}/{}/{}", totalPolls, active, pending, completed);
                numOkay = 0;
            }
            if (forceAfter > 0 && totalPolls > forceAfter)
            {
                logger.warn("Gossip not settled but startup forced by cassandra.skip_wait_for_gossip_to_settle. Gossip Stage total/active/pending/completed: {}/{}/{}/{}",
                            totalPolls, active, pending, completed);
                break;
            }
        }
        if (totalPolls > GOSSIP_SETTLE_POLL_SUCCESSES_REQUIRED)
            logger.info("Gossip settled after {} extra polls; proceeding", totalPolls - GOSSIP_SETTLE_POLL_SUCCESSES_REQUIRED);
        else
            logger.info("No gossip backlog; proceeding");
    }

    public static void stop(String[] args)
    {
        instance.deactivate();
    }

    public static void main(String[] args)
    {
        instance.activate();
    }
    
    static class NativeAccess implements NativeAccessMBean
    {
        public boolean isAvailable()
        {
            return CLibrary.jnaAvailable();
        }
        
        public boolean isMemoryLockable() 
        {
            return CLibrary.jnaMemoryLockable();
        }
    }

    public interface Server
    {
        /**
         * Start the server.
         * This method shoud be able to restart a server stopped through stop().
         * Should throw a RuntimeException if the server cannot be started
         */
        public void start();

        /**
         * Stop the server.
         * This method should be able to stop server started through start().
         * Should throw a RuntimeException if the server cannot be stopped
         */
        public void stop();

        /**
         * Returns whether the server is currently running.
         */
        public boolean isRunning();
    }
}


File: test/unit/org/apache/cassandra/db/ColumnFamilyStoreTest.java
/*
* Licensed to the Apache Software Foundation (ASF) under one
* or more contributor license agreements.  See the NOTICE file
* distributed with this work for additional information
* regarding copyright ownership.  The ASF licenses this file
* to you under the Apache License, Version 2.0 (the
* "License"); you may not use this file except in compliance
* with the License.  You may obtain a copy of the License at
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
package org.apache.cassandra.db;

import java.io.File;
import java.io.IOException;
import java.nio.ByteBuffer;
import java.nio.charset.CharacterCodingException;
import java.util.*;
import java.util.concurrent.ExecutionException;
import java.util.concurrent.Future;
import java.util.concurrent.TimeUnit;

import com.google.common.base.Function;
import com.google.common.collect.Iterables;
import com.google.common.collect.Sets;
import org.apache.commons.lang3.ArrayUtils;
import org.apache.commons.lang3.StringUtils;
import org.junit.Test;
import org.junit.runner.RunWith;

import org.apache.cassandra.OrderedJUnit4ClassRunner;
import org.apache.cassandra.SchemaLoader;
import org.apache.cassandra.Util;
import org.apache.cassandra.config.*;
import org.apache.cassandra.cql3.Operator;
import org.apache.cassandra.db.columniterator.IdentityQueryFilter;
import org.apache.cassandra.db.composites.*;
import org.apache.cassandra.db.filter.*;
import org.apache.cassandra.db.index.PerRowSecondaryIndexTest;
import org.apache.cassandra.db.index.SecondaryIndex;
import org.apache.cassandra.db.marshal.LexicalUUIDType;
import org.apache.cassandra.db.marshal.LongType;
import org.apache.cassandra.dht.*;
import org.apache.cassandra.io.sstable.*;
import org.apache.cassandra.io.sstable.metadata.MetadataCollector;
import org.apache.cassandra.io.util.FileUtils;
import org.apache.cassandra.service.ActiveRepairService;
import org.apache.cassandra.service.StorageService;
import org.apache.cassandra.thrift.SlicePredicate;
import org.apache.cassandra.thrift.SliceRange;
import org.apache.cassandra.thrift.ThriftValidation;
import org.apache.cassandra.utils.*;

import static org.apache.cassandra.Util.cellname;
import static org.apache.cassandra.Util.column;
import static org.apache.cassandra.Util.dk;
import static org.apache.cassandra.Util.rp;
import static org.apache.cassandra.utils.ByteBufferUtil.bytes;
import static org.junit.Assert.assertEquals;
import static org.junit.Assert.assertFalse;
import static org.junit.Assert.assertNull;
import static org.junit.Assert.assertSame;
import static org.junit.Assert.assertTrue;

@RunWith(OrderedJUnit4ClassRunner.class)
public class ColumnFamilyStoreTest extends SchemaLoader
{
    static byte[] bytes1, bytes2;

    static
    {
        Random random = new Random();
        bytes1 = new byte[1024];
        bytes2 = new byte[128];
        random.nextBytes(bytes1);
        random.nextBytes(bytes2);
    }

    @Test
    // create two sstables, and verify that we only deserialize data from the most recent one
    public void testTimeSortedQuery()
    {
        Keyspace keyspace = Keyspace.open("Keyspace1");
        ColumnFamilyStore cfs = keyspace.getColumnFamilyStore("Standard1");
        cfs.truncateBlocking();

        Mutation rm;
        rm = new Mutation("Keyspace1", ByteBufferUtil.bytes("key1"));
        rm.add("Standard1", cellname("Column1"), ByteBufferUtil.bytes("asdf"), 0);
        rm.apply();
        cfs.forceBlockingFlush();

        rm = new Mutation("Keyspace1", ByteBufferUtil.bytes("key1"));
        rm.add("Standard1", cellname("Column1"), ByteBufferUtil.bytes("asdf"), 1);
        rm.apply();
        cfs.forceBlockingFlush();

        cfs.getRecentSSTablesPerReadHistogram(); // resets counts
        cfs.getColumnFamily(Util.namesQueryFilter(cfs, Util.dk("key1"), "Column1"));
        assertEquals(1, cfs.getRecentSSTablesPerReadHistogram()[0]);
    }

    @Test
    public void testGetColumnWithWrongBF()
    {
        Keyspace keyspace = Keyspace.open("Keyspace1");
        ColumnFamilyStore cfs = keyspace.getColumnFamilyStore("Standard1");
        cfs.truncateBlocking();

        List<Mutation> rms = new LinkedList<>();
        Mutation rm = new Mutation("Keyspace1", ByteBufferUtil.bytes("key1"));
        rm.add("Standard1", cellname("Column1"), ByteBufferUtil.bytes("asdf"), 0);
        rm.add("Standard1", cellname("Column2"), ByteBufferUtil.bytes("asdf"), 0);
        rms.add(rm);
        Util.writeColumnFamily(rms);

        List<SSTableReader> ssTables = keyspace.getAllSSTables();
        assertEquals(1, ssTables.size());
        ssTables.get(0).forceFilterFailures();
        ColumnFamily cf = cfs.getColumnFamily(QueryFilter.getIdentityFilter(Util.dk("key2"), "Standard1", System.currentTimeMillis()));
        assertNull(cf);
    }

    @Test
    public void testEmptyRow() throws Exception
    {
        Keyspace keyspace = Keyspace.open("Keyspace1");
        final ColumnFamilyStore store = keyspace.getColumnFamilyStore("Standard2");
        Mutation rm;

        rm = new Mutation("Keyspace1", ByteBufferUtil.bytes("key1"));
        rm.delete("Standard2", System.currentTimeMillis());
        rm.apply();

        Runnable r = new WrappedRunnable()
        {
            public void runMayThrow() throws IOException
            {
                QueryFilter sliceFilter = QueryFilter.getSliceFilter(Util.dk("key1"), "Standard2", Composites.EMPTY, Composites.EMPTY, false, 1, System.currentTimeMillis());
                ColumnFamily cf = store.getColumnFamily(sliceFilter);
                assertTrue(cf.isMarkedForDelete());
                assertFalse(cf.hasColumns());

                QueryFilter namesFilter = Util.namesQueryFilter(store, Util.dk("key1"), "a");
                cf = store.getColumnFamily(namesFilter);
                assertTrue(cf.isMarkedForDelete());
                assertFalse(cf.hasColumns());
            }
        };

        KeyspaceTest.reTest(store, r);
    }

    @Test
    public void testSkipStartKey()
    {
        ColumnFamilyStore cfs = insertKey1Key2();

        IPartitioner p = StorageService.getPartitioner();
        List<Row> result = cfs.getRangeSlice(Util.range(p, "key1", "key2"),
                                             null,
                                             Util.namesFilter(cfs, "asdf"),
                                             10);
        assertEquals(1, result.size());
        assert result.get(0).key.getKey().equals(ByteBufferUtil.bytes("key2"));
    }

    @Test
    public void testIndexScan()
    {
        ColumnFamilyStore cfs = Keyspace.open("Keyspace1").getColumnFamilyStore("Indexed1");
        Mutation rm;
        CellName nobirthdate = cellname("notbirthdate");
        CellName birthdate = cellname("birthdate");

        rm = new Mutation("Keyspace1", ByteBufferUtil.bytes("k1"));
        rm.add("Indexed1", nobirthdate, ByteBufferUtil.bytes(1L), 0);
        rm.add("Indexed1", birthdate, ByteBufferUtil.bytes(1L), 0);
        rm.apply();

        rm = new Mutation("Keyspace1", ByteBufferUtil.bytes("k2"));
        rm.add("Indexed1", nobirthdate, ByteBufferUtil.bytes(2L), 0);
        rm.add("Indexed1", birthdate, ByteBufferUtil.bytes(2L), 0);
        rm.apply();

        rm = new Mutation("Keyspace1", ByteBufferUtil.bytes("k3"));
        rm.add("Indexed1", nobirthdate, ByteBufferUtil.bytes(2L), 0);
        rm.add("Indexed1", birthdate, ByteBufferUtil.bytes(1L), 0);
        rm.apply();

        rm = new Mutation("Keyspace1", ByteBufferUtil.bytes("k4aaaa"));
        rm.add("Indexed1", nobirthdate, ByteBufferUtil.bytes(2L), 0);
        rm.add("Indexed1", birthdate, ByteBufferUtil.bytes(3L), 0);
        rm.apply();

        // basic single-expression query
        IndexExpression expr = new IndexExpression(ByteBufferUtil.bytes("birthdate"), Operator.EQ, ByteBufferUtil.bytes(1L));
        List<IndexExpression> clause = Arrays.asList(expr);
        IDiskAtomFilter filter = new IdentityQueryFilter();
        Range<RowPosition> range = Util.range("", "");
        List<Row> rows = cfs.search(range, clause, filter, 100);

        assert rows != null;
        assert rows.size() == 2 : StringUtils.join(rows, ",");

        String key = new String(rows.get(0).key.getKey().array(), rows.get(0).key.getKey().position(), rows.get(0).key.getKey().remaining());
        assert "k1".equals( key ) : key;

        key = new String(rows.get(1).key.getKey().array(), rows.get(1).key.getKey().position(), rows.get(1).key.getKey().remaining());
        assert "k3".equals(key) : key;

        assert ByteBufferUtil.bytes(1L).equals( rows.get(0).cf.getColumn(birthdate).value());
        assert ByteBufferUtil.bytes(1L).equals( rows.get(1).cf.getColumn(birthdate).value());

        // add a second expression
        IndexExpression expr2 = new IndexExpression(ByteBufferUtil.bytes("notbirthdate"), Operator.GTE, ByteBufferUtil.bytes(2L));
        clause = Arrays.asList(expr, expr2);
        rows = cfs.search(range, clause, filter, 100);

        assert rows.size() == 1 : StringUtils.join(rows, ",");
        key = new String(rows.get(0).key.getKey().array(), rows.get(0).key.getKey().position(), rows.get(0).key.getKey().remaining());
        assert "k3".equals( key );

        // same query again, but with resultset not including the subordinate expression
        rows = cfs.search(range, clause, Util.namesFilter(cfs, "birthdate"), 100);

        assert rows.size() == 1 : StringUtils.join(rows, ",");
        key = new String(rows.get(0).key.getKey().array(), rows.get(0).key.getKey().position(), rows.get(0).key.getKey().remaining());
        assert "k3".equals( key );

        assert rows.get(0).cf.getColumnCount() == 1 : rows.get(0).cf;

        // once more, this time with a slice rowset that needs to be expanded
        SliceQueryFilter emptyFilter = new SliceQueryFilter(Composites.EMPTY, Composites.EMPTY, false, 0);
        rows = cfs.search(range, clause, emptyFilter, 100);

        assert rows.size() == 1 : StringUtils.join(rows, ",");
        key = new String(rows.get(0).key.getKey().array(), rows.get(0).key.getKey().position(), rows.get(0).key.getKey().remaining());
        assert "k3".equals( key );

        assertFalse(rows.get(0).cf.hasColumns());

        // query with index hit but rejected by secondary clause, with a small enough count that just checking count
        // doesn't tell the scan loop that it's done
        IndexExpression expr3 = new IndexExpression(ByteBufferUtil.bytes("notbirthdate"), Operator.EQ, ByteBufferUtil.bytes(-1L));
        clause = Arrays.asList(expr, expr3);
        rows = cfs.search(range, clause, filter, 100);

        assert rows.isEmpty();
    }

    @Test
    public void testLargeScan()
    {
        Mutation rm;
        ColumnFamilyStore cfs = Keyspace.open("Keyspace1").getColumnFamilyStore("Indexed1");
        for (int i = 0; i < 100; i++)
        {
            rm = new Mutation("Keyspace1", ByteBufferUtil.bytes("key" + i));
            rm.add("Indexed1", cellname("birthdate"), ByteBufferUtil.bytes(34L), 0);
            rm.add("Indexed1", cellname("notbirthdate"), ByteBufferUtil.bytes((long) (i % 2)), 0);
            rm.applyUnsafe();
        }

        IndexExpression expr = new IndexExpression(ByteBufferUtil.bytes("birthdate"), Operator.EQ, ByteBufferUtil.bytes(34L));
        IndexExpression expr2 = new IndexExpression(ByteBufferUtil.bytes("notbirthdate"), Operator.EQ, ByteBufferUtil.bytes(1L));
        List<IndexExpression> clause = Arrays.asList(expr, expr2);
        IDiskAtomFilter filter = new IdentityQueryFilter();
        Range<RowPosition> range = Util.range("", "");
        List<Row> rows = cfs.search(range, clause, filter, 100);

        assert rows != null;
        assert rows.size() == 50 : rows.size();
        Set<DecoratedKey> keys = new HashSet<DecoratedKey>();
        // extra check that there are no duplicate results -- see https://issues.apache.org/jira/browse/CASSANDRA-2406
        for (Row row : rows)
            keys.add(row.key);
        assert rows.size() == keys.size();
    }

    @Test
    public void testIndexDeletions() throws IOException
    {
        ColumnFamilyStore cfs = Keyspace.open("Keyspace3").getColumnFamilyStore("Indexed1");
        Mutation rm;

        rm = new Mutation("Keyspace3", ByteBufferUtil.bytes("k1"));
        rm.add("Indexed1", cellname("birthdate"), ByteBufferUtil.bytes(1L), 0);
        rm.apply();

        IndexExpression expr = new IndexExpression(ByteBufferUtil.bytes("birthdate"), Operator.EQ, ByteBufferUtil.bytes(1L));
        List<IndexExpression> clause = Arrays.asList(expr);
        IDiskAtomFilter filter = new IdentityQueryFilter();
        Range<RowPosition> range = Util.range("", "");
        List<Row> rows = cfs.search(range, clause, filter, 100);
        assert rows.size() == 1 : StringUtils.join(rows, ",");
        String key = ByteBufferUtil.string(rows.get(0).key.getKey());
        assert "k1".equals( key );

        // delete the column directly
        rm = new Mutation("Keyspace3", ByteBufferUtil.bytes("k1"));
        rm.delete("Indexed1", cellname("birthdate"), 1);
        rm.apply();
        rows = cfs.search(range, clause, filter, 100);
        assert rows.isEmpty();

        // verify that it's not being indexed under the deletion column value either
        Cell deletion = rm.getColumnFamilies().iterator().next().iterator().next();
        ByteBuffer deletionLong = ByteBufferUtil.bytes((long) ByteBufferUtil.toInt(deletion.value()));
        IndexExpression expr0 = new IndexExpression(ByteBufferUtil.bytes("birthdate"), Operator.EQ, deletionLong);
        List<IndexExpression> clause0 = Arrays.asList(expr0);
        rows = cfs.search(range, clause0, filter, 100);
        assert rows.isEmpty();

        // resurrect w/ a newer timestamp
        rm = new Mutation("Keyspace3", ByteBufferUtil.bytes("k1"));
        rm.add("Indexed1", cellname("birthdate"), ByteBufferUtil.bytes(1L), 2);
        rm.apply();
        rows = cfs.search(range, clause, filter, 100);
        assert rows.size() == 1 : StringUtils.join(rows, ",");
        key = ByteBufferUtil.string(rows.get(0).key.getKey());
        assert "k1".equals( key );

        // verify that row and delete w/ older timestamp does nothing
        rm = new Mutation("Keyspace3", ByteBufferUtil.bytes("k1"));
        rm.delete("Indexed1", 1);
        rm.apply();
        rows = cfs.search(range, clause, filter, 100);
        assert rows.size() == 1 : StringUtils.join(rows, ",");
        key = ByteBufferUtil.string(rows.get(0).key.getKey());
        assert "k1".equals( key );

        // similarly, column delete w/ older timestamp should do nothing
        rm = new Mutation("Keyspace3", ByteBufferUtil.bytes("k1"));
        rm.delete("Indexed1", cellname("birthdate"), 1);
        rm.apply();
        rows = cfs.search(range, clause, filter, 100);
        assert rows.size() == 1 : StringUtils.join(rows, ",");
        key = ByteBufferUtil.string(rows.get(0).key.getKey());
        assert "k1".equals( key );

        // delete the entire row (w/ newer timestamp this time)
        rm = new Mutation("Keyspace3", ByteBufferUtil.bytes("k1"));
        rm.delete("Indexed1", 3);
        rm.apply();
        rows = cfs.search(range, clause, filter, 100);
        assert rows.isEmpty() : StringUtils.join(rows, ",");

        // make sure obsolete mutations don't generate an index entry
        rm = new Mutation("Keyspace3", ByteBufferUtil.bytes("k1"));
        rm.add("Indexed1", cellname("birthdate"), ByteBufferUtil.bytes(1L), 3);
        rm.apply();
        rows = cfs.search(range, clause, filter, 100);
        assert rows.isEmpty() : StringUtils.join(rows, ",");

        // try insert followed by row delete in the same mutation
        rm = new Mutation("Keyspace3", ByteBufferUtil.bytes("k1"));
        rm.add("Indexed1", cellname("birthdate"), ByteBufferUtil.bytes(1L), 1);
        rm.delete("Indexed1", 2);
        rm.apply();
        rows = cfs.search(range, clause, filter, 100);
        assert rows.isEmpty() : StringUtils.join(rows, ",");

        // try row delete followed by insert in the same mutation
        rm = new Mutation("Keyspace3", ByteBufferUtil.bytes("k1"));
        rm.delete("Indexed1", 3);
        rm.add("Indexed1", cellname("birthdate"), ByteBufferUtil.bytes(1L), 4);
        rm.apply();
        rows = cfs.search(range, clause, filter, 100);
        assert rows.size() == 1 : StringUtils.join(rows, ",");
        key = ByteBufferUtil.string(rows.get(0).key.getKey());
        assert "k1".equals( key );
    }

    @Test
    public void testIndexUpdate() throws IOException
    {
        Keyspace keyspace = Keyspace.open("Keyspace2");
        ColumnFamilyStore cfs = keyspace.getColumnFamilyStore("Indexed1");
        CellName birthdate = cellname("birthdate");

        // create a row and update the birthdate value, test that the index query fetches the new version
        Mutation rm;
        rm = new Mutation("Keyspace2", ByteBufferUtil.bytes("k1"));
        rm.add("Indexed1", birthdate, ByteBufferUtil.bytes(1L), 1);
        rm.apply();
        rm = new Mutation("Keyspace2", ByteBufferUtil.bytes("k1"));
        rm.add("Indexed1", birthdate, ByteBufferUtil.bytes(2L), 2);
        rm.apply();

        IndexExpression expr = new IndexExpression(ByteBufferUtil.bytes("birthdate"), Operator.EQ, ByteBufferUtil.bytes(1L));
        List<IndexExpression> clause = Arrays.asList(expr);
        IDiskAtomFilter filter = new IdentityQueryFilter();
        Range<RowPosition> range = Util.range("", "");
        List<Row> rows = cfs.search(range, clause, filter, 100);
        assert rows.size() == 0;

        expr = new IndexExpression(ByteBufferUtil.bytes("birthdate"), Operator.EQ, ByteBufferUtil.bytes(2L));
        clause = Arrays.asList(expr);
        rows = keyspace.getColumnFamilyStore("Indexed1").search(range, clause, filter, 100);
        String key = ByteBufferUtil.string(rows.get(0).key.getKey());
        assert "k1".equals( key );

        // update the birthdate value with an OLDER timestamp, and test that the index ignores this
        rm = new Mutation("Keyspace2", ByteBufferUtil.bytes("k1"));
        rm.add("Indexed1", birthdate, ByteBufferUtil.bytes(3L), 0);
        rm.apply();

        rows = keyspace.getColumnFamilyStore("Indexed1").search(range, clause, filter, 100);
        key = ByteBufferUtil.string(rows.get(0).key.getKey());
        assert "k1".equals( key );

    }

    @Test
    public void testIndexUpdateOverwritingExpiringColumns() throws Exception
    {
        // see CASSANDRA-7268
        Keyspace keyspace = Keyspace.open("Keyspace2");

        // create a row and update the birthdate value with an expiring column
        Mutation rm;
        rm = new Mutation("Keyspace2", ByteBufferUtil.bytes("k100"));
        rm.add("Indexed1", cellname("birthdate"), ByteBufferUtil.bytes(100L), 1, 1000);
        rm.apply();

        IndexExpression expr = new IndexExpression(ByteBufferUtil.bytes("birthdate"), Operator.EQ, ByteBufferUtil.bytes(100L));
        List<IndexExpression> clause = Arrays.asList(expr);
        IDiskAtomFilter filter = new IdentityQueryFilter();
        Range<RowPosition> range = Util.range("", "");
        List<Row> rows = keyspace.getColumnFamilyStore("Indexed1").search(range, clause, filter, 100);
        assertEquals(1, rows.size());

        // requires a 1s sleep because we calculate local expiry time as (now() / 1000) + ttl
        TimeUnit.SECONDS.sleep(1);

        // now overwrite with the same name/value/ttl, but the local expiry time will be different
        rm = new Mutation("Keyspace2", ByteBufferUtil.bytes("k100"));
        rm.add("Indexed1", cellname("birthdate"), ByteBufferUtil.bytes(100L), 1, 1000);
        rm.apply();

        rows = keyspace.getColumnFamilyStore("Indexed1").search(range, clause, filter, 100);
        assertEquals(1, rows.size());

        // check that modifying the indexed value using the same timestamp behaves as expected
        rm = new Mutation("Keyspace2", ByteBufferUtil.bytes("k101"));
        rm.add("Indexed1", cellname("birthdate"), ByteBufferUtil.bytes(101L), 1, 1000);
        rm.apply();

        expr = new IndexExpression(ByteBufferUtil.bytes("birthdate"), Operator.EQ, ByteBufferUtil.bytes(101L));
        clause = Arrays.asList(expr);
        rows = keyspace.getColumnFamilyStore("Indexed1").search(range, clause, filter, 100);
        assertEquals(1, rows.size());

        TimeUnit.SECONDS.sleep(1);
        rm = new Mutation("Keyspace2", ByteBufferUtil.bytes("k101"));
        rm.add("Indexed1", cellname("birthdate"), ByteBufferUtil.bytes(102L), 1, 1000);
        rm.apply();
        // search for the old value
        rows = keyspace.getColumnFamilyStore("Indexed1").search(range, clause, filter, 100);
        assertEquals(0, rows.size());
        // and for the new
        expr = new IndexExpression(ByteBufferUtil.bytes("birthdate"), Operator.EQ, ByteBufferUtil.bytes(102L));
        clause = Arrays.asList(expr);
        rows = keyspace.getColumnFamilyStore("Indexed1").search(range, clause, filter, 100);
        assertEquals(1, rows.size());
    }

    @Test
    public void testDeleteOfInconsistentValuesInKeysIndex() throws Exception
    {
        String keySpace = "Keyspace2";
        String cfName = "Indexed1";

        Keyspace keyspace = Keyspace.open(keySpace);
        ColumnFamilyStore cfs = keyspace.getColumnFamilyStore(cfName);
        cfs.truncateBlocking();

        ByteBuffer rowKey = ByteBufferUtil.bytes("k1");
        CellName colName = cellname("birthdate"); 
        ByteBuffer val1 = ByteBufferUtil.bytes(1L);
        ByteBuffer val2 = ByteBufferUtil.bytes(2L);

        // create a row and update the "birthdate" value, test that the index query fetches this version
        Mutation rm;
        rm = new Mutation(keySpace, rowKey);
        rm.add(cfName, colName, val1, 0);
        rm.apply();
        IndexExpression expr = new IndexExpression(ByteBufferUtil.bytes("birthdate"), Operator.EQ, val1);
        List<IndexExpression> clause = Arrays.asList(expr);
        IDiskAtomFilter filter = new IdentityQueryFilter();
        Range<RowPosition> range = Util.range("", "");
        List<Row> rows = keyspace.getColumnFamilyStore(cfName).search(range, clause, filter, 100);
        assertEquals(1, rows.size());

        // force a flush, so our index isn't being read from a memtable
        keyspace.getColumnFamilyStore(cfName).forceBlockingFlush();

        // now apply another update, but force the index update to be skipped
        rm = new Mutation(keySpace, rowKey);
        rm.add(cfName, colName, val2, 1);
        keyspace.apply(rm, true, false);

        // Now searching the index for either the old or new value should return 0 rows
        // because the new value was not indexed and the old value should be ignored
        // (and in fact purged from the index cf).
        // first check for the old value
        rows = keyspace.getColumnFamilyStore(cfName).search(range, clause, filter, 100);
        assertEquals(0, rows.size());
        // now check for the updated value
        expr = new IndexExpression(ByteBufferUtil.bytes("birthdate"), Operator.EQ, val2);
        clause = Arrays.asList(expr);
        filter = new IdentityQueryFilter();
        range = Util.range("", "");
        rows = keyspace.getColumnFamilyStore(cfName).search(range, clause, filter, 100);
        assertEquals(0, rows.size());

        // now, reset back to the original value, still skipping the index update, to
        // make sure the value was expunged from the index when it was discovered to be inconsistent
        rm = new Mutation(keySpace, rowKey);
        rm.add(cfName, colName, ByteBufferUtil.bytes(1L), 3);
        keyspace.apply(rm, true, false);

        expr = new IndexExpression(ByteBufferUtil.bytes("birthdate"), Operator.EQ, ByteBufferUtil.bytes(1L));
        clause = Arrays.asList(expr);
        filter = new IdentityQueryFilter();
        range = Util.range("", "");
        rows = keyspace.getColumnFamilyStore(cfName).search(range, clause, filter, 100);
        assertEquals(0, rows.size());
    }

    @Test
    public void testDeleteOfInconsistentValuesFromCompositeIndex() throws Exception
    {
        String keySpace = "Keyspace2";
        String cfName = "Indexed2";

        Keyspace keyspace = Keyspace.open(keySpace);
        ColumnFamilyStore cfs = keyspace.getColumnFamilyStore(cfName);
        cfs.truncateBlocking();

        ByteBuffer rowKey = ByteBufferUtil.bytes("k1");
        ByteBuffer clusterKey = ByteBufferUtil.bytes("ck1");
        ByteBuffer colName = ByteBufferUtil.bytes("col1"); 

        CellNameType baseComparator = cfs.getComparator();
        CellName compositeName = baseComparator.makeCellName(clusterKey, colName);

        ByteBuffer val1 = ByteBufferUtil.bytes("v1");
        ByteBuffer val2 = ByteBufferUtil.bytes("v2");

        // create a row and update the author value
        Mutation rm;
        rm = new Mutation(keySpace, rowKey);
        rm.add(cfName, compositeName, val1, 0);
        rm.apply();

        // test that the index query fetches this version
        IndexExpression expr = new IndexExpression(colName, Operator.EQ, val1);
        List<IndexExpression> clause = Arrays.asList(expr);
        IDiskAtomFilter filter = new IdentityQueryFilter();
        Range<RowPosition> range = Util.range("", "");
        List<Row> rows = keyspace.getColumnFamilyStore(cfName).search(range, clause, filter, 100);
        assertEquals(1, rows.size());

        // force a flush and retry the query, so our index isn't being read from a memtable
        keyspace.getColumnFamilyStore(cfName).forceBlockingFlush();
        rows = keyspace.getColumnFamilyStore(cfName).search(range, clause, filter, 100);
        assertEquals(1, rows.size());

        // now apply another update, but force the index update to be skipped
        rm = new Mutation(keySpace, rowKey);
        rm.add(cfName, compositeName, val2, 1);
        keyspace.apply(rm, true, false);

        // Now searching the index for either the old or new value should return 0 rows
        // because the new value was not indexed and the old value should be ignored
        // (and in fact purged from the index cf).
        // first check for the old value
        rows = keyspace.getColumnFamilyStore(cfName).search(range, clause, filter, 100);
        assertEquals(0, rows.size());
        // now check for the updated value
        expr = new IndexExpression(colName, Operator.EQ, val2);
        clause = Arrays.asList(expr);
        filter = new IdentityQueryFilter();
        range = Util.range("", "");
        rows = keyspace.getColumnFamilyStore(cfName).search(range, clause, filter, 100);
        assertEquals(0, rows.size());

        // now, reset back to the original value, still skipping the index update, to
        // make sure the value was expunged from the index when it was discovered to be inconsistent
        rm = new Mutation(keySpace, rowKey);
        rm.add(cfName, compositeName, val1, 2);
        keyspace.apply(rm, true, false);

        expr = new IndexExpression(colName, Operator.EQ, val1);
        clause = Arrays.asList(expr);
        filter = new IdentityQueryFilter();
        range = Util.range("", "");
        rows = keyspace.getColumnFamilyStore(cfName).search(range, clause, filter, 100);
        assertEquals(0, rows.size());
    }

    // See CASSANDRA-6098
    @Test
    public void testDeleteCompositeIndex() throws Exception
    {
        String keySpace = "Keyspace2";
        String cfName = "Indexed3"; // has gcGrace 0

        Keyspace keyspace = Keyspace.open(keySpace);
        ColumnFamilyStore cfs = keyspace.getColumnFamilyStore(cfName);
        cfs.truncateBlocking();

        ByteBuffer rowKey = ByteBufferUtil.bytes("k1");
        ByteBuffer clusterKey = ByteBufferUtil.bytes("ck1");
        ByteBuffer colName = ByteBufferUtil.bytes("col1");

        CellNameType baseComparator = cfs.getComparator();
        CellName compositeName = baseComparator.makeCellName(clusterKey, colName);

        ByteBuffer val1 = ByteBufferUtil.bytes("v2");

        // Insert indexed value.
        Mutation rm;
        rm = new Mutation(keySpace, rowKey);
        rm.add(cfName, compositeName, val1, 0);
        rm.apply();

        // Now delete the value and flush too.
        rm = new Mutation(keySpace, rowKey);
        rm.delete(cfName, 1);
        rm.apply();

        // We want the data to be gcable, but even if gcGrace == 0, we still need to wait 1 second
        // since we won't gc on a tie.
        try { Thread.sleep(1000); } catch (Exception e) {}

        // Read the index and we check we do get no value (and no NPE)
        // Note: the index will return the entry because it hasn't been deleted (we
        // haven't read yet nor compacted) but the data read itself will return null
        IndexExpression expr = new IndexExpression(colName, Operator.EQ, val1);
        List<IndexExpression> clause = Arrays.asList(expr);
        IDiskAtomFilter filter = new IdentityQueryFilter();
        Range<RowPosition> range = Util.range("", "");
        List<Row> rows = keyspace.getColumnFamilyStore(cfName).search(range, clause, filter, 100);
        assertEquals(0, rows.size());
    }

    // See CASSANDRA-2628
    @Test
    public void testIndexScanWithLimitOne()
    {
        ColumnFamilyStore cfs = Keyspace.open("Keyspace1").getColumnFamilyStore("Indexed1");
        Mutation rm;

        CellName nobirthdate = cellname("notbirthdate");
        CellName birthdate = cellname("birthdate");

        rm = new Mutation("Keyspace1", ByteBufferUtil.bytes("kk1"));
        rm.add("Indexed1", nobirthdate, ByteBufferUtil.bytes(1L), 0);
        rm.add("Indexed1", birthdate, ByteBufferUtil.bytes(1L), 0);
        rm.apply();

        rm = new Mutation("Keyspace1", ByteBufferUtil.bytes("kk2"));
        rm.add("Indexed1", nobirthdate, ByteBufferUtil.bytes(2L), 0);
        rm.add("Indexed1", birthdate, ByteBufferUtil.bytes(1L), 0);
        rm.apply();

        rm = new Mutation("Keyspace1", ByteBufferUtil.bytes("kk3"));
        rm.add("Indexed1", nobirthdate, ByteBufferUtil.bytes(2L), 0);
        rm.add("Indexed1", birthdate, ByteBufferUtil.bytes(1L), 0);
        rm.apply();

        rm = new Mutation("Keyspace1", ByteBufferUtil.bytes("kk4"));
        rm.add("Indexed1", nobirthdate, ByteBufferUtil.bytes(2L), 0);
        rm.add("Indexed1", birthdate, ByteBufferUtil.bytes(1L), 0);
        rm.apply();

        // basic single-expression query
        IndexExpression expr1 = new IndexExpression(ByteBufferUtil.bytes("birthdate"), Operator.EQ, ByteBufferUtil.bytes(1L));
        IndexExpression expr2 = new IndexExpression(ByteBufferUtil.bytes("notbirthdate"), Operator.GT, ByteBufferUtil.bytes(1L));
        List<IndexExpression> clause = Arrays.asList(expr1, expr2);
        IDiskAtomFilter filter = new IdentityQueryFilter();
        Range<RowPosition> range = Util.range("", "");
        List<Row> rows = cfs.search(range, clause, filter, 1);

        assert rows != null;
        assert rows.size() == 1 : StringUtils.join(rows, ",");
    }

    @Test
    public void testIndexCreate() throws IOException, InterruptedException, ExecutionException
    {
        Keyspace keyspace = Keyspace.open("Keyspace1");
        ColumnFamilyStore cfs = keyspace.getColumnFamilyStore("Indexed2");

        // create a row and update the birthdate value, test that the index query fetches the new version
        Mutation rm;
        rm = new Mutation("Keyspace1", ByteBufferUtil.bytes("k1"));
        rm.add("Indexed2", cellname("birthdate"), ByteBufferUtil.bytes(1L), 1);
        rm.apply();

        ColumnDefinition old = cfs.metadata.getColumnDefinition(ByteBufferUtil.bytes("birthdate"));
        ColumnDefinition cd = ColumnDefinition.regularDef(cfs.metadata, old.name.bytes, old.type, null).setIndex("birthdate_index", IndexType.KEYS, null);
        Future<?> future = cfs.indexManager.addIndexedColumn(cd);
        future.get();
        // we had a bug (CASSANDRA-2244) where index would get created but not flushed -- check for that
        assert cfs.indexManager.getIndexForColumn(cd.name.bytes).getIndexCfs().getSSTables().size() > 0;

        queryBirthdate(keyspace);

        // validate that drop clears it out & rebuild works (CASSANDRA-2320)
        SecondaryIndex indexedCfs = cfs.indexManager.getIndexForColumn(ByteBufferUtil.bytes("birthdate"));
        cfs.indexManager.removeIndexedColumn(ByteBufferUtil.bytes("birthdate"));
        assert !indexedCfs.isIndexBuilt(ByteBufferUtil.bytes("birthdate"));

        // rebuild & re-query
        future = cfs.indexManager.addIndexedColumn(cd);
        future.get();
        queryBirthdate(keyspace);
    }

    private void queryBirthdate(Keyspace keyspace) throws CharacterCodingException
    {
        IndexExpression expr = new IndexExpression(ByteBufferUtil.bytes("birthdate"), Operator.EQ, ByteBufferUtil.bytes(1L));
        List<IndexExpression> clause = Arrays.asList(expr);
        IDiskAtomFilter filter = new IdentityQueryFilter();
        List<Row> rows = keyspace.getColumnFamilyStore("Indexed2").search(Util.range("", ""), clause, filter, 100);
        assert rows.size() == 1 : StringUtils.join(rows, ",");
        assertEquals("k1", ByteBufferUtil.string(rows.get(0).key.getKey()));
    }

    @Test
    public void testCassandra6778() throws CharacterCodingException
    {
        String cfname = "StandardInteger1";
        Keyspace keyspace = Keyspace.open("Keyspace1");
        ColumnFamilyStore cfs = keyspace.getColumnFamilyStore(cfname);

        // insert two columns that represent the same integer but have different binary forms (the
        // second one is padded with extra zeros)
        Mutation rm = new Mutation("Keyspace1", ByteBufferUtil.bytes("k1"));
        CellName column1 = cellname(ByteBuffer.wrap(new byte[]{1}));
        rm.add(cfname, column1, ByteBufferUtil.bytes("data1"), 1);
        rm.apply();
        cfs.forceBlockingFlush();

        rm = new Mutation("Keyspace1", ByteBufferUtil.bytes("k1"));
        CellName column2 = cellname(ByteBuffer.wrap(new byte[]{0, 0, 1}));
        rm.add(cfname, column2, ByteBufferUtil.bytes("data2"), 2);
        rm.apply();
        cfs.forceBlockingFlush();

        // fetch by the first column name; we should get the second version of the column value
        SliceByNamesReadCommand cmd = new SliceByNamesReadCommand(
            "Keyspace1", ByteBufferUtil.bytes("k1"), cfname, System.currentTimeMillis(),
            new NamesQueryFilter(FBUtilities.singleton(column1, cfs.getComparator())));

        ColumnFamily cf = cmd.getRow(keyspace).cf;
        assertEquals(1, cf.getColumnCount());
        Cell cell = cf.getColumn(column1);
        assertEquals("data2", ByteBufferUtil.string(cell.value()));
        assertEquals(column2, cell.name());

        // fetch by the second column name; we should get the second version of the column value
        cmd = new SliceByNamesReadCommand(
            "Keyspace1", ByteBufferUtil.bytes("k1"), cfname, System.currentTimeMillis(),
            new NamesQueryFilter(FBUtilities.singleton(column2, cfs.getComparator())));

        cf = cmd.getRow(keyspace).cf;
        assertEquals(1, cf.getColumnCount());
        cell = cf.getColumn(column2);
        assertEquals("data2", ByteBufferUtil.string(cell.value()));
        assertEquals(column2, cell.name());
    }

    @Test
    public void testInclusiveBounds()
    {
        ColumnFamilyStore cfs = insertKey1Key2();

        List<Row> result = cfs.getRangeSlice(Util.bounds("key1", "key2"),
                                             null,
                                             Util.namesFilter(cfs, "asdf"),
                                             10);
        assertEquals(2, result.size());
        assert result.get(0).key.getKey().equals(ByteBufferUtil.bytes("key1"));
    }

    @Test
    public void testDeleteSuperRowSticksAfterFlush() throws Throwable
    {
        String keyspaceName = "Keyspace1";
        String cfName= "Super1";
        ByteBuffer scfName = ByteBufferUtil.bytes("SuperDuper");
        Keyspace keyspace = Keyspace.open(keyspaceName);
        ColumnFamilyStore cfs = keyspace.getColumnFamilyStore(cfName);
        DecoratedKey key = Util.dk("flush-resurrection");

        // create an isolated sstable.
        putColsSuper(cfs, key, scfName,
                new BufferCell(cellname(1L), ByteBufferUtil.bytes("val1"), 1),
                new BufferCell(cellname(2L), ByteBufferUtil.bytes("val2"), 1),
                new BufferCell(cellname(3L), ByteBufferUtil.bytes("val3"), 1));
        cfs.forceBlockingFlush();

        // insert, don't flush.
        putColsSuper(cfs, key, scfName,
                new BufferCell(cellname(4L), ByteBufferUtil.bytes("val4"), 1),
                new BufferCell(cellname(5L), ByteBufferUtil.bytes("val5"), 1),
                new BufferCell(cellname(6L), ByteBufferUtil.bytes("val6"), 1));

        // verify insert.
        final SlicePredicate sp = new SlicePredicate();
        sp.setSlice_range(new SliceRange());
        sp.getSlice_range().setCount(100);
        sp.getSlice_range().setStart(ArrayUtils.EMPTY_BYTE_ARRAY);
        sp.getSlice_range().setFinish(ArrayUtils.EMPTY_BYTE_ARRAY);

        assertRowAndColCount(1, 6, false, cfs.getRangeSlice(Util.range("f", "g"), null, ThriftValidation.asIFilter(sp, cfs.metadata, scfName), 100));

        // delete
        Mutation rm = new Mutation(keyspace.getName(), key.getKey());
        rm.deleteRange(cfName, SuperColumns.startOf(scfName), SuperColumns.endOf(scfName), 2);
        rm.apply();

        // verify delete.
        assertRowAndColCount(1, 0, false, cfs.getRangeSlice(Util.range("f", "g"), null, ThriftValidation.asIFilter(sp, cfs.metadata, scfName), 100));

        // flush
        cfs.forceBlockingFlush();

        // re-verify delete.
        assertRowAndColCount(1, 0, false, cfs.getRangeSlice(Util.range("f", "g"), null, ThriftValidation.asIFilter(sp, cfs.metadata, scfName), 100));

        // late insert.
        putColsSuper(cfs, key, scfName,
                new BufferCell(cellname(4L), ByteBufferUtil.bytes("val4"), 1L),
                new BufferCell(cellname(7L), ByteBufferUtil.bytes("val7"), 1L));

        // re-verify delete.
        assertRowAndColCount(1, 0, false, cfs.getRangeSlice(Util.range("f", "g"), null, ThriftValidation.asIFilter(sp, cfs.metadata, scfName), 100));

        // make sure new writes are recognized.
        putColsSuper(cfs, key, scfName,
                new BufferCell(cellname(3L), ByteBufferUtil.bytes("val3"), 3),
                new BufferCell(cellname(8L), ByteBufferUtil.bytes("val8"), 3),
                new BufferCell(cellname(9L), ByteBufferUtil.bytes("val9"), 3));
        assertRowAndColCount(1, 3, false, cfs.getRangeSlice(Util.range("f", "g"), null, ThriftValidation.asIFilter(sp, cfs.metadata, scfName), 100));
    }

    private static void assertRowAndColCount(int rowCount, int colCount, boolean isDeleted, Collection<Row> rows) throws CharacterCodingException
    {
        assert rows.size() == rowCount : "rowcount " + rows.size();
        for (Row row : rows)
        {
            assert row.cf != null : "cf was null";
            assert row.cf.getColumnCount() == colCount : "colcount " + row.cf.getColumnCount() + "|" + str(row.cf);
            if (isDeleted)
                assert row.cf.isMarkedForDelete() : "cf not marked for delete";
        }
    }

    private static String str(ColumnFamily cf) throws CharacterCodingException
    {
        StringBuilder sb = new StringBuilder();
        for (Cell col : cf.getSortedColumns())
            sb.append(String.format("(%s,%s,%d),", ByteBufferUtil.string(col.name().toByteBuffer()), ByteBufferUtil.string(col.value()), col.timestamp()));
        return sb.toString();
    }

    private static void putColsSuper(ColumnFamilyStore cfs, DecoratedKey key, ByteBuffer scfName, Cell... cols) throws Throwable
    {
        ColumnFamily cf = ArrayBackedSortedColumns.factory.create(cfs.keyspace.getName(), cfs.name);
        for (Cell col : cols)
            cf.addColumn(col.withUpdatedName(CellNames.compositeDense(scfName, col.name().toByteBuffer())));
        Mutation rm = new Mutation(cfs.keyspace.getName(), key.getKey(), cf);
        rm.apply();
    }

    private static void putColsStandard(ColumnFamilyStore cfs, DecoratedKey key, Cell... cols) throws Throwable
    {
        ColumnFamily cf = ArrayBackedSortedColumns.factory.create(cfs.keyspace.getName(), cfs.name);
        for (Cell col : cols)
            cf.addColumn(col);
        Mutation rm = new Mutation(cfs.keyspace.getName(), key.getKey(), cf);
        rm.apply();
    }

    @Test
    public void testDeleteStandardRowSticksAfterFlush() throws Throwable
    {
        // test to make sure flushing after a delete doesn't resurrect delted cols.
        String keyspaceName = "Keyspace1";
        String cfName = "Standard1";
        Keyspace keyspace = Keyspace.open(keyspaceName);
        ColumnFamilyStore cfs = keyspace.getColumnFamilyStore(cfName);
        DecoratedKey key = Util.dk("f-flush-resurrection");

        SlicePredicate sp = new SlicePredicate();
        sp.setSlice_range(new SliceRange());
        sp.getSlice_range().setCount(100);
        sp.getSlice_range().setStart(ArrayUtils.EMPTY_BYTE_ARRAY);
        sp.getSlice_range().setFinish(ArrayUtils.EMPTY_BYTE_ARRAY);

        // insert
        putColsStandard(cfs, key, column("col1", "val1", 1), column("col2", "val2", 1));
        assertRowAndColCount(1, 2, false, cfs.getRangeSlice(Util.range("f", "g"), null, ThriftValidation.asIFilter(sp, cfs.metadata, null), 100));

        // flush.
        cfs.forceBlockingFlush();

        // insert, don't flush
        putColsStandard(cfs, key, column("col3", "val3", 1), column("col4", "val4", 1));
        assertRowAndColCount(1, 4, false, cfs.getRangeSlice(Util.range("f", "g"), null, ThriftValidation.asIFilter(sp, cfs.metadata, null), 100));

        // delete (from sstable and memtable)
        Mutation rm = new Mutation(keyspace.getName(), key.getKey());
        rm.delete(cfs.name, 2);
        rm.apply();

        // verify delete
        assertRowAndColCount(1, 0, true, cfs.getRangeSlice(Util.range("f", "g"), null, ThriftValidation.asIFilter(sp, cfs.metadata, null), 100));

        // flush
        cfs.forceBlockingFlush();

        // re-verify delete. // first breakage is right here because of CASSANDRA-1837.
        assertRowAndColCount(1, 0, true, cfs.getRangeSlice(Util.range("f", "g"), null, ThriftValidation.asIFilter(sp, cfs.metadata, null), 100));

        // simulate a 'late' insertion that gets put in after the deletion. should get inserted, but fail on read.
        putColsStandard(cfs, key, column("col5", "val5", 1), column("col2", "val2", 1));

        // should still be nothing there because we deleted this row. 2nd breakage, but was undetected because of 1837.
        assertRowAndColCount(1, 0, true, cfs.getRangeSlice(Util.range("f", "g"), null, ThriftValidation.asIFilter(sp, cfs.metadata, null), 100));

        // make sure that new writes are recognized.
        putColsStandard(cfs, key, column("col6", "val6", 3), column("col7", "val7", 3));
        assertRowAndColCount(1, 2, true, cfs.getRangeSlice(Util.range("f", "g"), null, ThriftValidation.asIFilter(sp, cfs.metadata, null), 100));

        // and it remains so after flush. (this wasn't failing before, but it's good to check.)
        cfs.forceBlockingFlush();
        assertRowAndColCount(1, 2, true, cfs.getRangeSlice(Util.range("f", "g"), null, ThriftValidation.asIFilter(sp, cfs.metadata, null), 100));
    }


    private ColumnFamilyStore insertKey1Key2()
    {
        ColumnFamilyStore cfs = Keyspace.open("Keyspace2").getColumnFamilyStore("Standard1");
        List<Mutation> rms = new LinkedList<>();
        Mutation rm;
        rm = new Mutation("Keyspace2", ByteBufferUtil.bytes("key1"));
        rm.add("Standard1", cellname("Column1"), ByteBufferUtil.bytes("asdf"), 0);
        rms.add(rm);
        Util.writeColumnFamily(rms);

        rm = new Mutation("Keyspace2", ByteBufferUtil.bytes("key2"));
        rm.add("Standard1", cellname("Column1"), ByteBufferUtil.bytes("asdf"), 0);
        rms.add(rm);
        return Util.writeColumnFamily(rms);
    }

    @Test
    public void testBackupAfterFlush() throws Throwable
    {
        ColumnFamilyStore cfs = insertKey1Key2();

        for (int version = 1; version <= 2; ++version)
        {
            Descriptor existing = new Descriptor(cfs.directories.getDirectoryForNewSSTables(), "Keyspace2", "Standard1", version, Descriptor.Type.FINAL);
            Descriptor desc = new Descriptor(Directories.getBackupsDirectory(existing), "Keyspace2", "Standard1", version, Descriptor.Type.FINAL);
            for (Component c : new Component[]{ Component.DATA, Component.PRIMARY_INDEX, Component.FILTER, Component.STATS })
                assertTrue("can not find backedup file:" + desc.filenameFor(c), new File(desc.filenameFor(c)).exists());
        }
    }

    // CASSANDRA-3467.  the key here is that supercolumn and subcolumn comparators are different
    @Test
    public void testSliceByNamesCommandOnUUIDTypeSCF() throws Throwable
    {
        String keyspaceName = "Keyspace1";
        String cfName = "Super6";
        ByteBuffer superColName = LexicalUUIDType.instance.fromString("a4ed3562-0e8e-4b41-bdfd-c45a2774682d");
        Keyspace keyspace = Keyspace.open(keyspaceName);
        ColumnFamilyStore cfs = keyspace.getColumnFamilyStore(cfName);
        DecoratedKey key = Util.dk("slice-get-uuid-type");

        // Insert a row with one supercolumn and multiple subcolumns
        putColsSuper(cfs, key, superColName, new BufferCell(cellname("a"), ByteBufferUtil.bytes("A"), 1),
                                             new BufferCell(cellname("b"), ByteBufferUtil.bytes("B"), 1));

        // Get the entire supercolumn like normal
        ColumnFamily cfGet = cfs.getColumnFamily(QueryFilter.getIdentityFilter(key, cfName, System.currentTimeMillis()));
        assertEquals(ByteBufferUtil.bytes("A"), cfGet.getColumn(CellNames.compositeDense(superColName, ByteBufferUtil.bytes("a"))).value());
        assertEquals(ByteBufferUtil.bytes("B"), cfGet.getColumn(CellNames.compositeDense(superColName, ByteBufferUtil.bytes("b"))).value());

        // Now do the SliceByNamesCommand on the supercolumn, passing both subcolumns in as columns to get
        SortedSet<CellName> sliceColNames = new TreeSet<CellName>(cfs.metadata.comparator);
        sliceColNames.add(CellNames.compositeDense(superColName, ByteBufferUtil.bytes("a")));
        sliceColNames.add(CellNames.compositeDense(superColName, ByteBufferUtil.bytes("b")));
        SliceByNamesReadCommand cmd = new SliceByNamesReadCommand(keyspaceName, key.getKey(), cfName, System.currentTimeMillis(), new NamesQueryFilter(sliceColNames));
        ColumnFamily cfSliced = cmd.getRow(keyspace).cf;

        // Make sure the slice returns the same as the straight get
        assertEquals(ByteBufferUtil.bytes("A"), cfSliced.getColumn(CellNames.compositeDense(superColName, ByteBufferUtil.bytes("a"))).value());
        assertEquals(ByteBufferUtil.bytes("B"), cfSliced.getColumn(CellNames.compositeDense(superColName, ByteBufferUtil.bytes("b"))).value());
    }

    @Test
    public void testSliceByNamesCommandOldMetadata() throws Throwable
    {
        String keyspaceName = "Keyspace1";
        String cfName= "Standard1";
        DecoratedKey key = Util.dk("slice-name-old-metadata");
        CellName cname = cellname("c1");
        Keyspace keyspace = Keyspace.open(keyspaceName);
        ColumnFamilyStore cfs = keyspace.getColumnFamilyStore(cfName);
        cfs.clearUnsafe();

        // Create a cell a 'high timestamp'
        putColsStandard(cfs, key, new BufferCell(cname, ByteBufferUtil.bytes("a"), 2));
        cfs.forceBlockingFlush();

        // Nuke the metadata and reload that sstable
        Collection<SSTableReader> ssTables = cfs.getSSTables();
        assertEquals(1, ssTables.size());
        cfs.clearUnsafe();
        assertEquals(0, cfs.getSSTables().size());

        new File(ssTables.iterator().next().descriptor.filenameFor(Component.STATS)).delete();
        cfs.loadNewSSTables();

        // Add another cell with a lower timestamp
        putColsStandard(cfs, key, new BufferCell(cname, ByteBufferUtil.bytes("b"), 1));

        // Test fetching the cell by name returns the first cell
        SliceByNamesReadCommand cmd = new SliceByNamesReadCommand(keyspaceName, key.getKey(), cfName, System.currentTimeMillis(), new NamesQueryFilter(FBUtilities.singleton(cname, cfs.getComparator())));
        ColumnFamily cf = cmd.getRow(keyspace).cf;
        Cell cell = cf.getColumn(cname);
        assert cell.value().equals(ByteBufferUtil.bytes("a")) : "expecting a, got " + ByteBufferUtil.string(cell.value());

        Keyspace.clear("Keyspace1"); // CASSANDRA-7195
    }

    private static void assertTotalColCount(Collection<Row> rows, int expectedCount)
    {
        int columns = 0;
        for (Row row : rows)
        {
            columns += row.getLiveCount(new SliceQueryFilter(ColumnSlice.ALL_COLUMNS_ARRAY, false, expectedCount), System.currentTimeMillis());
        }
        assert columns == expectedCount : "Expected " + expectedCount + " live columns but got " + columns + ": " + rows;
    }


    @Test
    public void testRangeSliceColumnsLimit() throws Throwable
    {
        String keyspaceName = "Keyspace1";
        String cfName = "Standard1";
        Keyspace keyspace = Keyspace.open(keyspaceName);
        ColumnFamilyStore cfs = keyspace.getColumnFamilyStore(cfName);
        cfs.clearUnsafe();

        Cell[] cols = new Cell[5];
        for (int i = 0; i < 5; i++)
            cols[i] = column("c" + i, "value", 1);

        putColsStandard(cfs, Util.dk("a"), cols[0], cols[1], cols[2], cols[3], cols[4]);
        putColsStandard(cfs, Util.dk("b"), cols[0], cols[1]);
        putColsStandard(cfs, Util.dk("c"), cols[0], cols[1], cols[2], cols[3]);
        cfs.forceBlockingFlush();

        SlicePredicate sp = new SlicePredicate();
        sp.setSlice_range(new SliceRange());
        sp.getSlice_range().setCount(1);
        sp.getSlice_range().setStart(ArrayUtils.EMPTY_BYTE_ARRAY);
        sp.getSlice_range().setFinish(ArrayUtils.EMPTY_BYTE_ARRAY);

        assertTotalColCount(cfs.getRangeSlice(Util.range("", ""),
                                              null,
                                              ThriftValidation.asIFilter(sp, cfs.metadata, null),
                                              3,
                                              System.currentTimeMillis(),
                                              true,
                                              false),
                            3);
        assertTotalColCount(cfs.getRangeSlice(Util.range("", ""),
                                              null,
                                              ThriftValidation.asIFilter(sp, cfs.metadata, null),
                                              5,
                                              System.currentTimeMillis(),
                                              true,
                                              false),
                            5);
        assertTotalColCount(cfs.getRangeSlice(Util.range("", ""),
                                              null,
                                              ThriftValidation.asIFilter(sp, cfs.metadata, null),
                                              8,
                                              System.currentTimeMillis(),
                                              true,
                                              false),
                            8);
        assertTotalColCount(cfs.getRangeSlice(Util.range("", ""),
                                              null,
                                              ThriftValidation.asIFilter(sp, cfs.metadata, null),
                                              10,
                                              System.currentTimeMillis(),
                                              true,
                                              false),
                            10);
        assertTotalColCount(cfs.getRangeSlice(Util.range("", ""),
                                              null,
                                              ThriftValidation.asIFilter(sp, cfs.metadata, null),
                                              100,
                                              System.currentTimeMillis(),
                                              true,
                                              false),
                            11);

        // Check that when querying by name, we always include all names for a
        // gien row even if it means returning more columns than requested (this is necesseray for CQL)
        sp = new SlicePredicate();
        sp.setColumn_names(Arrays.asList(
            ByteBufferUtil.bytes("c0"),
            ByteBufferUtil.bytes("c1"),
            ByteBufferUtil.bytes("c2")
        ));

        assertTotalColCount(cfs.getRangeSlice(Util.range("", ""),
                                              null,
                                              ThriftValidation.asIFilter(sp, cfs.metadata, null),
                                              1,
                                              System.currentTimeMillis(),
                                              true,
                                              false),
                            3);
        assertTotalColCount(cfs.getRangeSlice(Util.range("", ""),
                                              null,
                                              ThriftValidation.asIFilter(sp, cfs.metadata, null),
                                              4,
                                              System.currentTimeMillis(),
                                              true,
                                              false),
                            5);
        assertTotalColCount(cfs.getRangeSlice(Util.range("", ""),
                                              null,
                                              ThriftValidation.asIFilter(sp, cfs.metadata, null),
                                              5,
                                              System.currentTimeMillis(),
                                              true,
                                              false),
                            5);
        assertTotalColCount(cfs.getRangeSlice(Util.range("", ""),
                                              null,
                                              ThriftValidation.asIFilter(sp, cfs.metadata, null),
                                              6,
                                              System.currentTimeMillis(),
                                              true,
                                              false),
                            8);
        assertTotalColCount(cfs.getRangeSlice(Util.range("", ""),
                                              null,
                                              ThriftValidation.asIFilter(sp, cfs.metadata, null),
                                              100,
                                              System.currentTimeMillis(),
                                              true,
                                              false),
                            8);
    }

    @Test
    public void testRangeSlicePaging() throws Throwable
    {
        String keyspaceName = "Keyspace1";
        String cfName = "Standard1";
        Keyspace keyspace = Keyspace.open(keyspaceName);
        ColumnFamilyStore cfs = keyspace.getColumnFamilyStore(cfName);
        cfs.clearUnsafe();

        Cell[] cols = new Cell[4];
        for (int i = 0; i < 4; i++)
            cols[i] = column("c" + i, "value", 1);

        DecoratedKey ka = Util.dk("a");
        DecoratedKey kb = Util.dk("b");
        DecoratedKey kc = Util.dk("c");

        RowPosition min = Util.rp("");

        putColsStandard(cfs, ka, cols[0], cols[1], cols[2], cols[3]);
        putColsStandard(cfs, kb, cols[0], cols[1], cols[2]);
        putColsStandard(cfs, kc, cols[0], cols[1], cols[2], cols[3]);
        cfs.forceBlockingFlush();

        SlicePredicate sp = new SlicePredicate();
        sp.setSlice_range(new SliceRange());
        sp.getSlice_range().setCount(1);
        sp.getSlice_range().setStart(ArrayUtils.EMPTY_BYTE_ARRAY);
        sp.getSlice_range().setFinish(ArrayUtils.EMPTY_BYTE_ARRAY);

        Collection<Row> rows;
        Row row, row1, row2;
        IDiskAtomFilter filter = ThriftValidation.asIFilter(sp, cfs.metadata, null);

        rows = cfs.getRangeSlice(cfs.makeExtendedFilter(Util.range("", ""), filter, null, 3, true, true, System.currentTimeMillis()));
        assert rows.size() == 1 : "Expected 1 row, got " + toString(rows);
        row = rows.iterator().next();
        assertColumnNames(row, "c0", "c1", "c2");

        sp.getSlice_range().setStart(ByteBufferUtil.getArray(ByteBufferUtil.bytes("c2")));
        filter = ThriftValidation.asIFilter(sp, cfs.metadata, null);
        rows = cfs.getRangeSlice(cfs.makeExtendedFilter(new Bounds<RowPosition>(ka, min), filter, null, 3, true, true, System.currentTimeMillis()));
        assert rows.size() == 2 : "Expected 2 rows, got " + toString(rows);
        Iterator<Row> iter = rows.iterator();
        row1 = iter.next();
        row2 = iter.next();
        assertColumnNames(row1, "c2", "c3");
        assertColumnNames(row2, "c0");

        sp.getSlice_range().setStart(ByteBufferUtil.getArray(ByteBufferUtil.bytes("c0")));
        filter = ThriftValidation.asIFilter(sp, cfs.metadata, null);
        rows = cfs.getRangeSlice(cfs.makeExtendedFilter(new Bounds<RowPosition>(row2.key, min), filter, null, 3, true, true, System.currentTimeMillis()));
        assert rows.size() == 1 : "Expected 1 row, got " + toString(rows);
        row = rows.iterator().next();
        assertColumnNames(row, "c0", "c1", "c2");

        sp.getSlice_range().setStart(ByteBufferUtil.getArray(ByteBufferUtil.bytes("c2")));
        filter = ThriftValidation.asIFilter(sp, cfs.metadata, null);
        rows = cfs.getRangeSlice(cfs.makeExtendedFilter(new Bounds<RowPosition>(row.key, min), filter, null, 3, true, true, System.currentTimeMillis()));
        assert rows.size() == 2 : "Expected 2 rows, got " + toString(rows);
        iter = rows.iterator();
        row1 = iter.next();
        row2 = iter.next();
        assertColumnNames(row1, "c2");
        assertColumnNames(row2, "c0", "c1");

        // Paging within bounds
        SliceQueryFilter sf = new SliceQueryFilter(cellname("c1"),
                                                   cellname("c2"),
                                                   false,
                                                   0);
        rows = cfs.getRangeSlice(cfs.makeExtendedFilter(new Bounds<RowPosition>(ka, kc), sf, cellname("c2"), cellname("c1"), null, 2, true, System.currentTimeMillis()));
        assert rows.size() == 2 : "Expected 2 rows, got " + toString(rows);
        iter = rows.iterator();
        row1 = iter.next();
        row2 = iter.next();
        assertColumnNames(row1, "c2");
        assertColumnNames(row2, "c1");

        rows = cfs.getRangeSlice(cfs.makeExtendedFilter(new Bounds<RowPosition>(kb, kc), sf, cellname("c1"), cellname("c1"), null, 10, true, System.currentTimeMillis()));
        assert rows.size() == 2 : "Expected 2 rows, got " + toString(rows);
        iter = rows.iterator();
        row1 = iter.next();
        row2 = iter.next();
        assertColumnNames(row1, "c1", "c2");
        assertColumnNames(row2, "c1");
    }

    private static String toString(Collection<Row> rows)
    {
        try
        {
            StringBuilder sb = new StringBuilder();
            for (Row row : rows)
            {
                sb.append("{");
                sb.append(ByteBufferUtil.string(row.key.getKey()));
                sb.append(":");
                if (row.cf != null && !row.cf.isEmpty())
                {
                    for (Cell c : row.cf)
                        sb.append(" ").append(row.cf.getComparator().getString(c.name()));
                }
                sb.append("} ");
            }
            return sb.toString();
        }
        catch (Exception e)
        {
            throw new RuntimeException(e);
        }
    }

    private static void assertColumnNames(Row row, String ... columnNames) throws Exception
    {
        if (row == null || row.cf == null)
            throw new AssertionError("The row should not be empty");

        Iterator<Cell> columns = row.cf.getSortedColumns().iterator();
        Iterator<String> names = Arrays.asList(columnNames).iterator();

        while (columns.hasNext())
        {
            Cell c = columns.next();
            assert names.hasNext() : "Got more columns that expected (first unexpected column: " + ByteBufferUtil.string(c.name().toByteBuffer()) + ")";
            String n = names.next();
            assert c.name().toByteBuffer().equals(ByteBufferUtil.bytes(n)) : "Expected " + n + ", got " + ByteBufferUtil.string(c.name().toByteBuffer());
        }
        assert !names.hasNext() : "Missing expected column " + names.next();
    }

    private static DecoratedKey idk(int i)
    {
        return Util.dk(String.valueOf(i));
    }

    @Test
    public void testRangeSliceInclusionExclusion() throws Throwable
    {
        String keyspaceName = "Keyspace1";
        String cfName = "Standard1";
        Keyspace keyspace = Keyspace.open(keyspaceName);
        ColumnFamilyStore cfs = keyspace.getColumnFamilyStore(cfName);
        cfs.clearUnsafe();

        Cell[] cols = new Cell[5];
        for (int i = 0; i < 5; i++)
            cols[i] = column("c" + i, "value", 1);

        for (int i = 0; i <= 9; i++)
        {
            putColsStandard(cfs, idk(i), column("name", "value", 1));
        }
        cfs.forceBlockingFlush();

        SlicePredicate sp = new SlicePredicate();
        sp.setSlice_range(new SliceRange());
        sp.getSlice_range().setCount(1);
        sp.getSlice_range().setStart(ArrayUtils.EMPTY_BYTE_ARRAY);
        sp.getSlice_range().setFinish(ArrayUtils.EMPTY_BYTE_ARRAY);
        IDiskAtomFilter qf = ThriftValidation.asIFilter(sp, cfs.metadata, null);

        List<Row> rows;

        // Start and end inclusive
        rows = cfs.getRangeSlice(new Bounds<RowPosition>(rp("2"), rp("7")), null, qf, 100);
        assert rows.size() == 6;
        assert rows.get(0).key.equals(idk(2));
        assert rows.get(rows.size() - 1).key.equals(idk(7));

        // Start and end excluded
        rows = cfs.getRangeSlice(new ExcludingBounds<RowPosition>(rp("2"), rp("7")), null, qf, 100);
        assert rows.size() == 4;
        assert rows.get(0).key.equals(idk(3));
        assert rows.get(rows.size() - 1).key.equals(idk(6));

        // Start excluded, end included
        rows = cfs.getRangeSlice(new Range<RowPosition>(rp("2"), rp("7")), null, qf, 100);
        assert rows.size() == 5;
        assert rows.get(0).key.equals(idk(3));
        assert rows.get(rows.size() - 1).key.equals(idk(7));

        // Start included, end excluded
        rows = cfs.getRangeSlice(new IncludingExcludingBounds<RowPosition>(rp("2"), rp("7")), null, qf, 100);
        assert rows.size() == 5;
        assert rows.get(0).key.equals(idk(2));
        assert rows.get(rows.size() - 1).key.equals(idk(6));
    }

    @Test
    public void testKeysSearcher() throws Exception
    {
        // Create secondary index and flush to disk
        Keyspace keyspace = Keyspace.open("Keyspace1");
        ColumnFamilyStore store = keyspace.getColumnFamilyStore("Indexed1");

        store.truncateBlocking();

        for (int i = 0; i < 10; i++)
        {
            ByteBuffer key = ByteBufferUtil.bytes(String.valueOf("k" + i));
            Mutation rm = new Mutation("Keyspace1", key);
            rm.add("Indexed1", cellname("birthdate"), LongType.instance.decompose(1L), System.currentTimeMillis());
            rm.apply();
        }

        store.forceBlockingFlush();

        IndexExpression expr = new IndexExpression(ByteBufferUtil.bytes("birthdate"), Operator.EQ, LongType.instance.decompose(1L));
        // explicitly tell to the KeysSearcher to use column limiting for rowsPerQuery to trigger bogus columnsRead--; (CASSANDRA-3996)
        List<Row> rows = store.search(store.makeExtendedFilter(Util.range("", ""), new IdentityQueryFilter(), Arrays.asList(expr), 10, true, false, System.currentTimeMillis()));

        assert rows.size() == 10;
    }

    @SuppressWarnings("unchecked")
    @Test
    public void testMultiRangeSomeEmptyNoIndex() throws Throwable
    {
        // in order not to change thrift interfaces at this stage we build SliceQueryFilter
        // directly instead of using QueryFilter to build it for us
        ColumnSlice[] ranges = new ColumnSlice[] {
                new ColumnSlice(Composites.EMPTY, cellname("colA")),
                new ColumnSlice(cellname("colC"), cellname("colE")),
                new ColumnSlice(cellname("colF"), cellname("colF")),
                new ColumnSlice(cellname("colG"), cellname("colG")),
                new ColumnSlice(cellname("colI"), Composites.EMPTY) };

        ColumnSlice[] rangesReversed = new ColumnSlice[] {
                new ColumnSlice(Composites.EMPTY, cellname("colI")),
                new ColumnSlice(cellname("colG"), cellname("colG")),
                new ColumnSlice(cellname("colF"), cellname("colF")),
                new ColumnSlice(cellname("colE"), cellname("colC")),
                new ColumnSlice(cellname("colA"), Composites.EMPTY) };

        String tableName = "Keyspace1";
        String cfName = "Standard1";
        Keyspace table = Keyspace.open(tableName);
        ColumnFamilyStore cfs = table.getColumnFamilyStore(cfName);
        cfs.clearUnsafe();

        String[] letters = new String[] { "a", "b", "c", "d", "i" };
        Cell[] cols = new Cell[letters.length];
        for (int i = 0; i < cols.length; i++)
        {
            cols[i] = new BufferCell(cellname("col" + letters[i].toUpperCase()),
                    ByteBuffer.wrap(new byte[1]), 1);
        }

        putColsStandard(cfs, dk("a"), cols);

        cfs.forceBlockingFlush();

        SliceQueryFilter multiRangeForward = new SliceQueryFilter(ranges, false, 100);
        SliceQueryFilter multiRangeForwardWithCounting = new SliceQueryFilter(ranges, false, 3);
        SliceQueryFilter multiRangeReverse = new SliceQueryFilter(rangesReversed, true, 100);
        SliceQueryFilter multiRangeReverseWithCounting = new SliceQueryFilter(rangesReversed, true, 3);

        findRowGetSlicesAndAssertColsFound(cfs, multiRangeForward, "a", "colA", "colC", "colD", "colI");
        findRowGetSlicesAndAssertColsFound(cfs, multiRangeForwardWithCounting, "a", "colA", "colC", "colD");
        findRowGetSlicesAndAssertColsFound(cfs, multiRangeReverse, "a", "colI", "colD", "colC", "colA");
        findRowGetSlicesAndAssertColsFound(cfs, multiRangeReverseWithCounting, "a", "colI", "colD", "colC");
    }

    @SuppressWarnings("unchecked")
    @Test
    public void testMultiRangeSomeEmptyIndexed() throws Throwable
    {
        // in order not to change thrift interfaces at this stage we build SliceQueryFilter
        // directly instead of using QueryFilter to build it for us
        ColumnSlice[] ranges = new ColumnSlice[] {
                new ColumnSlice(Composites.EMPTY, cellname("colA")),
                new ColumnSlice(cellname("colC"), cellname("colE")),
                new ColumnSlice(cellname("colF"), cellname("colF")),
                new ColumnSlice(cellname("colG"), cellname("colG")),
                new ColumnSlice(cellname("colI"), Composites.EMPTY) };

        ColumnSlice[] rangesReversed = new ColumnSlice[] {
                new ColumnSlice(Composites.EMPTY,  cellname("colI")),
                new ColumnSlice(cellname("colG"), cellname("colG")),
                new ColumnSlice(cellname("colF"), cellname("colF")),
                new ColumnSlice(cellname("colE"), cellname("colC")),
                new ColumnSlice(cellname("colA"), Composites.EMPTY) };

        String tableName = "Keyspace1";
        String cfName = "Standard1";
        Keyspace table = Keyspace.open(tableName);
        ColumnFamilyStore cfs = table.getColumnFamilyStore(cfName);
        cfs.clearUnsafe();

        String[] letters = new String[] { "a", "b", "c", "d", "i" };
        Cell[] cols = new Cell[letters.length];
        for (int i = 0; i < cols.length; i++)
        {
            cols[i] = new BufferCell(cellname("col" + letters[i].toUpperCase()),
                    ByteBuffer.wrap(new byte[1366]), 1);
        }

        putColsStandard(cfs, dk("a"), cols);

        cfs.forceBlockingFlush();

        SliceQueryFilter multiRangeForward = new SliceQueryFilter(ranges, false, 100);
        SliceQueryFilter multiRangeForwardWithCounting = new SliceQueryFilter(ranges, false, 3);
        SliceQueryFilter multiRangeReverse = new SliceQueryFilter(rangesReversed, true, 100);
        SliceQueryFilter multiRangeReverseWithCounting = new SliceQueryFilter(rangesReversed, true, 3);

        findRowGetSlicesAndAssertColsFound(cfs, multiRangeForward, "a", "colA", "colC", "colD", "colI");
        findRowGetSlicesAndAssertColsFound(cfs, multiRangeForwardWithCounting, "a", "colA", "colC", "colD");
        findRowGetSlicesAndAssertColsFound(cfs, multiRangeReverse, "a", "colI", "colD", "colC", "colA");
        findRowGetSlicesAndAssertColsFound(cfs, multiRangeReverseWithCounting, "a", "colI", "colD", "colC");
    }

    @SuppressWarnings("unchecked")
    @Test
    public void testMultiRangeContiguousNoIndex() throws Throwable
    {
        // in order not to change thrift interfaces at this stage we build SliceQueryFilter
        // directly instead of using QueryFilter to build it for us
        ColumnSlice[] ranges = new ColumnSlice[] {
                new ColumnSlice(Composites.EMPTY, cellname("colA")),
                new ColumnSlice(cellname("colC"), cellname("colE")),
                new ColumnSlice(cellname("colF"), cellname("colF")),
                new ColumnSlice(cellname("colG"), cellname("colG")),
                new ColumnSlice(cellname("colI"), Composites.EMPTY) };

        ColumnSlice[] rangesReversed = new ColumnSlice[] {
                new ColumnSlice(Composites.EMPTY, cellname("colI")),
                new ColumnSlice(cellname("colG"), cellname("colG")),
                new ColumnSlice(cellname("colF"), cellname("colF")),
                new ColumnSlice(cellname("colE"), cellname("colC")),
                new ColumnSlice(cellname("colA"), Composites.EMPTY) };

        String tableName = "Keyspace1";
        String cfName = "Standard1";
        Keyspace table = Keyspace.open(tableName);
        ColumnFamilyStore cfs = table.getColumnFamilyStore(cfName);
        cfs.clearUnsafe();

        String[] letters = new String[] { "a", "b", "c", "d", "e", "f", "g", "h", "i" };
        Cell[] cols = new Cell[letters.length];
        for (int i = 0; i < cols.length; i++)
        {
            cols[i] = new BufferCell(cellname("col" + letters[i].toUpperCase()),
                    ByteBuffer.wrap(new byte[1]), 1);
        }

        putColsStandard(cfs, dk("a"), cols);

        cfs.forceBlockingFlush();

        SliceQueryFilter multiRangeForward = new SliceQueryFilter(ranges, false, 100);
        SliceQueryFilter multiRangeForwardWithCounting = new SliceQueryFilter(ranges, false, 3);
        SliceQueryFilter multiRangeReverse = new SliceQueryFilter(rangesReversed, true, 100);
        SliceQueryFilter multiRangeReverseWithCounting = new SliceQueryFilter(rangesReversed, true, 3);

        findRowGetSlicesAndAssertColsFound(cfs, multiRangeForward, "a", "colA", "colC", "colD", "colE", "colF", "colG", "colI");
        findRowGetSlicesAndAssertColsFound(cfs, multiRangeForwardWithCounting, "a", "colA", "colC", "colD");
        findRowGetSlicesAndAssertColsFound(cfs, multiRangeReverse, "a", "colI", "colG", "colF", "colE", "colD", "colC", "colA");
        findRowGetSlicesAndAssertColsFound(cfs, multiRangeReverseWithCounting, "a", "colI", "colG", "colF");

    }

    @SuppressWarnings("unchecked")
    @Test
    public void testMultiRangeContiguousIndexed() throws Throwable
    {
        // in order not to change thrift interfaces at this stage we build SliceQueryFilter
        // directly instead of using QueryFilter to build it for us
        ColumnSlice[] ranges = new ColumnSlice[] {
                new ColumnSlice(Composites.EMPTY, cellname("colA")),
                new ColumnSlice(cellname("colC"), cellname("colE")),
                new ColumnSlice(cellname("colF"), cellname("colF")),
                new ColumnSlice(cellname("colG"), cellname("colG")),
                new ColumnSlice(cellname("colI"), Composites.EMPTY) };

        ColumnSlice[] rangesReversed = new ColumnSlice[] {
                new ColumnSlice(Composites.EMPTY, cellname("colI")),
                new ColumnSlice(cellname("colG"), cellname("colG")),
                new ColumnSlice(cellname("colF"), cellname("colF")),
                new ColumnSlice(cellname("colE"), cellname("colC")),
                new ColumnSlice(cellname("colA"), Composites.EMPTY) };

        String tableName = "Keyspace1";
        String cfName = "Standard1";
        Keyspace table = Keyspace.open(tableName);
        ColumnFamilyStore cfs = table.getColumnFamilyStore(cfName);
        cfs.clearUnsafe();

        String[] letters = new String[] { "a", "b", "c", "d", "e", "f", "g", "h", "i" };
        Cell[] cols = new Cell[letters.length];
        for (int i = 0; i < cols.length; i++)
        {
            cols[i] = new BufferCell(cellname("col" + letters[i].toUpperCase()),
                    ByteBuffer.wrap(new byte[1366]), 1);
        }

        putColsStandard(cfs, dk("a"), cols);

        cfs.forceBlockingFlush();

        SliceQueryFilter multiRangeForward = new SliceQueryFilter(ranges, false, 100);
        SliceQueryFilter multiRangeForwardWithCounting = new SliceQueryFilter(ranges, false, 3);
        SliceQueryFilter multiRangeReverse = new SliceQueryFilter(rangesReversed, true, 100);
        SliceQueryFilter multiRangeReverseWithCounting = new SliceQueryFilter(rangesReversed, true, 3);

        findRowGetSlicesAndAssertColsFound(cfs, multiRangeForward, "a", "colA", "colC", "colD", "colE", "colF", "colG", "colI");
        findRowGetSlicesAndAssertColsFound(cfs, multiRangeForwardWithCounting, "a", "colA", "colC", "colD");
        findRowGetSlicesAndAssertColsFound(cfs, multiRangeReverse, "a", "colI", "colG", "colF", "colE", "colD", "colC", "colA");
        findRowGetSlicesAndAssertColsFound(cfs, multiRangeReverseWithCounting, "a", "colI", "colG", "colF");

    }

    @SuppressWarnings("unchecked")
    @Test
    public void testMultiRangeIndexed() throws Throwable
    {
        // in order not to change thrift interfaces at this stage we build SliceQueryFilter
        // directly instead of using QueryFilter to build it for us
        ColumnSlice[] ranges = new ColumnSlice[] {
                new ColumnSlice(Composites.EMPTY, cellname("colA")),
                new ColumnSlice(cellname("colC"), cellname("colE")),
                new ColumnSlice(cellname("colG"), cellname("colG")),
                new ColumnSlice(cellname("colI"), Composites.EMPTY) };

        ColumnSlice[] rangesReversed = new ColumnSlice[] {
                new ColumnSlice(Composites.EMPTY, cellname("colI")),
                new ColumnSlice(cellname("colG"), cellname("colG")),
                new ColumnSlice(cellname("colE"), cellname("colC")),
                new ColumnSlice(cellname("colA"), Composites.EMPTY) };

        String keyspaceName = "Keyspace1";
        String cfName = "Standard1";
        Keyspace keyspace = Keyspace.open(keyspaceName);
        ColumnFamilyStore cfs = keyspace.getColumnFamilyStore(cfName);
        cfs.clearUnsafe();

        String[] letters = new String[] { "a", "b", "c", "d", "e", "f", "g", "h", "i" };
        Cell[] cols = new Cell[letters.length];
        for (int i = 0; i < cols.length; i++)
        {
            cols[i] = new BufferCell(cellname("col" + letters[i].toUpperCase()),
                    // use 1366 so that three cols make an index segment
                    ByteBuffer.wrap(new byte[1366]), 1);
        }

        putColsStandard(cfs, dk("a"), cols);

        cfs.forceBlockingFlush();

        // this setup should generate the following row (assuming indexes are of 4Kb each):
        // [colA, colB, colC, colD, colE, colF, colG, colH, colI]
        // indexed as:
        // index0 [colA, colC]
        // index1 [colD, colF]
        // index2 [colG, colI]
        // and we're looking for the ranges:
        // range0 [____, colA]
        // range1 [colC, colE]
        // range2 [colG, ColG]
        // range3 [colI, ____]

        SliceQueryFilter multiRangeForward = new SliceQueryFilter(ranges, false, 100);
        SliceQueryFilter multiRangeForwardWithCounting = new SliceQueryFilter(ranges, false, 3);
        SliceQueryFilter multiRangeReverse = new SliceQueryFilter(rangesReversed, true, 100);
        SliceQueryFilter multiRangeReverseWithCounting = new SliceQueryFilter(rangesReversed, true, 3);

        findRowGetSlicesAndAssertColsFound(cfs, multiRangeForward, "a", "colA", "colC", "colD", "colE", "colG", "colI");
        findRowGetSlicesAndAssertColsFound(cfs, multiRangeForwardWithCounting, "a", "colA", "colC", "colD");
        findRowGetSlicesAndAssertColsFound(cfs, multiRangeReverse, "a", "colI", "colG", "colE", "colD", "colC", "colA");
        findRowGetSlicesAndAssertColsFound(cfs, multiRangeReverseWithCounting, "a", "colI", "colG", "colE");

    }

    @Test
    public void testMultipleRangesSlicesNoIndexedColumns() throws Throwable
    {
        // small values so that cols won't be indexed
        testMultiRangeSlicesBehavior(prepareMultiRangeSlicesTest(10, true));
    }

    @Test
    public void testMultipleRangesSlicesWithIndexedColumns() throws Throwable
    {
        // min val size before cols are indexed is 4kb while testing so lets make sure cols are indexed
        testMultiRangeSlicesBehavior(prepareMultiRangeSlicesTest(1024, true));
    }

    @Test
    public void testMultipleRangesSlicesInMemory() throws Throwable
    {
        // small values so that cols won't be indexed
        testMultiRangeSlicesBehavior(prepareMultiRangeSlicesTest(10, false));
    }

    @Test
    public void testRemoveUnfinishedCompactionLeftovers() throws Throwable
    {
        String ks = "Keyspace1";
        String cf = "Standard3"; // should be empty

        final CFMetaData cfmeta = Schema.instance.getCFMetaData(ks, cf);
        Directories dir = new Directories(cfmeta);
        ByteBuffer key = bytes("key");

        // 1st sstable
        SSTableSimpleWriter writer = new SSTableSimpleWriter(dir.getDirectoryForNewSSTables(), cfmeta, StorageService.getPartitioner());
        writer.newRow(key);
        writer.addColumn(bytes("col"), bytes("val"), 1);
        writer.close();

        Map<Descriptor, Set<Component>> sstables = dir.sstableLister().list();
        assertEquals(1, sstables.size());

        Map.Entry<Descriptor, Set<Component>> sstableToOpen = sstables.entrySet().iterator().next();
        final SSTableReader sstable1 = SSTableReader.open(sstableToOpen.getKey());

        // simulate incomplete compaction
        writer = new SSTableSimpleWriter(dir.getDirectoryForNewSSTables(),
                                         cfmeta, StorageService.getPartitioner())
        {
            protected SSTableWriter getWriter()
            {
                MetadataCollector collector = new MetadataCollector(cfmeta.comparator);
                collector.addAncestor(sstable1.descriptor.generation); // add ancestor from previously written sstable
                return new SSTableWriter(makeFilename(directory, metadata.ksName, metadata.cfName),
                                         0,
                                         ActiveRepairService.UNREPAIRED_SSTABLE,
                                         metadata,
                                         StorageService.getPartitioner(),
                                         collector);
            }
        };
        writer.newRow(key);
        writer.addColumn(bytes("col"), bytes("val"), 1);
        writer.close();

        // should have 2 sstables now
        sstables = dir.sstableLister().list();
        assertEquals(2, sstables.size());

        SSTableReader sstable2 = SSTableReader.open(sstable1.descriptor);
        UUID compactionTaskID = SystemKeyspace.startCompaction(
                Keyspace.open(ks).getColumnFamilyStore(cf),
                Collections.singleton(sstable2));

        Map<Integer, UUID> unfinishedCompaction = new HashMap<>();
        unfinishedCompaction.put(sstable1.descriptor.generation, compactionTaskID);
        ColumnFamilyStore.removeUnfinishedCompactionLeftovers(cfmeta, unfinishedCompaction);

        // 2nd sstable should be removed (only 1st sstable exists in set of size 1)
        sstables = dir.sstableLister().list();
        assertEquals(1, sstables.size());
        assertTrue(sstables.containsKey(sstable1.descriptor));

        Map<Pair<String, String>, Map<Integer, UUID>> unfinished = SystemKeyspace.getUnfinishedCompactions();
        assertTrue(unfinished.isEmpty());
        sstable1.selfRef().release();
        sstable2.selfRef().release();
    }

    /**
     * @see <a href="https://issues.apache.org/jira/browse/CASSANDRA-6086">CASSANDRA-6086</a>
     */
    @Test
    public void testFailedToRemoveUnfinishedCompactionLeftovers() throws Throwable
    {
        final String ks = "Keyspace1";
        final String cf = "Standard4"; // should be empty

        final CFMetaData cfmeta = Schema.instance.getCFMetaData(ks, cf);
        Directories dir = new Directories(cfmeta);
        ByteBuffer key = bytes("key");

        // Write SSTable generation 3 that has ancestors 1 and 2
        final Set<Integer> ancestors = Sets.newHashSet(1, 2);
        SSTableSimpleWriter writer = new SSTableSimpleWriter(dir.getDirectoryForNewSSTables(),
                                                cfmeta, StorageService.getPartitioner())
        {
            protected SSTableWriter getWriter()
            {
                MetadataCollector collector = new MetadataCollector(cfmeta.comparator);
                for (int ancestor : ancestors)
                    collector.addAncestor(ancestor);
                String file = new Descriptor(directory, ks, cf, 3, Descriptor.Type.TEMP).filenameFor(Component.DATA);
                return new SSTableWriter(file,
                                         0,
                                         ActiveRepairService.UNREPAIRED_SSTABLE,
                                         metadata,
                                         StorageService.getPartitioner(),
                                         collector);
            }
        };
        writer.newRow(key);
        writer.addColumn(bytes("col"), bytes("val"), 1);
        writer.close();

        Map<Descriptor, Set<Component>> sstables = dir.sstableLister().list();
        assert sstables.size() == 1;

        Map.Entry<Descriptor, Set<Component>> sstableToOpen = sstables.entrySet().iterator().next();
        final SSTableReader sstable1 = SSTableReader.open(sstableToOpen.getKey());

        // simulate we don't have generation in compaction_history
        Map<Integer, UUID> unfinishedCompactions = new HashMap<>();
        UUID compactionTaskID = UUID.randomUUID();
        for (Integer ancestor : ancestors)
            unfinishedCompactions.put(ancestor, compactionTaskID);
        ColumnFamilyStore.removeUnfinishedCompactionLeftovers(cfmeta, unfinishedCompactions);

        // SSTable should not be deleted
        sstables = dir.sstableLister().list();
        assert sstables.size() == 1;
        assert sstables.containsKey(sstable1.descriptor);
    }

    @Test
    public void testLoadNewSSTablesAvoidsOverwrites() throws Throwable
    {
        String ks = "Keyspace1";
        String cf = "Standard1";
        ColumnFamilyStore cfs = Keyspace.open(ks).getColumnFamilyStore(cf);
        cfs.truncateBlocking();
        SSTableDeletingTask.waitForDeletions();

        final CFMetaData cfmeta = Schema.instance.getCFMetaData(ks, cf);
        Directories dir = new Directories(cfs.metadata);

        // clear old SSTables (probably left by CFS.clearUnsafe() calls in other tests)
        for (Map.Entry<Descriptor, Set<Component>> entry : dir.sstableLister().list().entrySet())
        {
            for (Component component : entry.getValue())
            {
                FileUtils.delete(entry.getKey().filenameFor(component));
            }
        }

        // sanity check
        int existingSSTables = dir.sstableLister().list().keySet().size();
        assert existingSSTables == 0 : String.format("%d SSTables unexpectedly exist", existingSSTables);

        ByteBuffer key = bytes("key");

        SSTableSimpleWriter writer = new SSTableSimpleWriter(dir.getDirectoryForNewSSTables(),
                                                             cfmeta, StorageService.getPartitioner())
        {
            @Override
            protected SSTableWriter getWriter()
            {
                // hack for reset generation
                generation.set(0);
                return super.getWriter();
            }
        };
        writer.newRow(key);
        writer.addColumn(bytes("col"), bytes("val"), 1);
        writer.close();

        writer = new SSTableSimpleWriter(dir.getDirectoryForNewSSTables(),
                                         cfmeta, StorageService.getPartitioner());
        writer.newRow(key);
        writer.addColumn(bytes("col"), bytes("val"), 1);
        writer.close();

        Set<Integer> generations = new HashSet<>();
        for (Descriptor descriptor : dir.sstableLister().list().keySet())
            generations.add(descriptor.generation);

        // we should have two generations: [1, 2]
        assertEquals(2, generations.size());
        assertTrue(generations.contains(1));
        assertTrue(generations.contains(2));

        assertEquals(0, cfs.getSSTables().size());

        // start the generation counter at 1 again (other tests have incremented it already)
        cfs.resetFileIndexGenerator();

        boolean incrementalBackupsEnabled = DatabaseDescriptor.isIncrementalBackupsEnabled();
        try
        {
            // avoid duplicate hardlinks to incremental backups
            DatabaseDescriptor.setIncrementalBackupsEnabled(false);
            cfs.loadNewSSTables();
        }
        finally
        {
            DatabaseDescriptor.setIncrementalBackupsEnabled(incrementalBackupsEnabled);
        }

        assertEquals(2, cfs.getSSTables().size());
        generations = new HashSet<>();
        for (Descriptor descriptor : dir.sstableLister().list().keySet())
            generations.add(descriptor.generation);

        // normally they would get renamed to generations 1 and 2, but since those filenames already exist,
        // they get skipped and we end up with generations 3 and 4
        assertEquals(2, generations.size());
        assertTrue(generations.contains(3));
        assertTrue(generations.contains(4));
    }

    private ColumnFamilyStore prepareMultiRangeSlicesTest(int valueSize, boolean flush) throws Throwable
    {
        String keyspaceName = "Keyspace1";
        String cfName = "Standard1";
        Keyspace keyspace = Keyspace.open(keyspaceName);
        ColumnFamilyStore cfs = keyspace.getColumnFamilyStore(cfName);
        cfs.clearUnsafe();

        String[] letters = new String[] { "a", "b", "c", "d", "e", "f", "g", "h", "i", "j", "k", "l" };
        Cell[] cols = new Cell[12];
        for (int i = 0; i < cols.length; i++)
        {
            cols[i] = new BufferCell(cellname("col" + letters[i]), ByteBuffer.wrap(new byte[valueSize]), 1);
        }

        for (int i = 0; i < 12; i++)
        {
            putColsStandard(cfs, dk(letters[i]), Arrays.copyOfRange(cols, 0, i + 1));
        }

        if (flush)
        {
            cfs.forceBlockingFlush();
        }
        else
        {
            // The intent is to validate memtable code, so check we really didn't flush
            assert cfs.getSSTables().isEmpty();
        }

        return cfs;
    }

    private void testMultiRangeSlicesBehavior(ColumnFamilyStore cfs)
    {
        // in order not to change thrift interfaces at this stage we build SliceQueryFilter
        // directly instead of using QueryFilter to build it for us
        ColumnSlice[] startMiddleAndEndRanges = new ColumnSlice[] {
                new ColumnSlice(Composites.EMPTY, cellname("colc")),
                new ColumnSlice(cellname("colf"), cellname("colg")),
                new ColumnSlice(cellname("colj"), Composites.EMPTY) };

        ColumnSlice[] startMiddleAndEndRangesReversed = new ColumnSlice[] {
                new ColumnSlice(Composites.EMPTY, cellname("colj")),
                new ColumnSlice(cellname("colg"), cellname("colf")),
                new ColumnSlice(cellname("colc"), Composites.EMPTY) };

        ColumnSlice[] startOnlyRange =
                new ColumnSlice[] { new ColumnSlice(Composites.EMPTY, cellname("colc")) };

        ColumnSlice[] startOnlyRangeReversed =
                new ColumnSlice[] { new ColumnSlice(cellname("colc"), Composites.EMPTY) };

        ColumnSlice[] middleOnlyRanges =
                new ColumnSlice[] { new ColumnSlice(cellname("colf"), cellname("colg")) };

        ColumnSlice[] middleOnlyRangesReversed =
                new ColumnSlice[] { new ColumnSlice(cellname("colg"), cellname("colf")) };

        ColumnSlice[] endOnlyRanges =
                new ColumnSlice[] { new ColumnSlice(cellname("colj"), Composites.EMPTY) };

        ColumnSlice[] endOnlyRangesReversed =
                new ColumnSlice[] { new ColumnSlice(Composites.EMPTY, cellname("colj")) };

        SliceQueryFilter startOnlyFilter = new SliceQueryFilter(startOnlyRange, false,
                Integer.MAX_VALUE);
        SliceQueryFilter startOnlyFilterReversed = new SliceQueryFilter(startOnlyRangeReversed, true,
                Integer.MAX_VALUE);
        SliceQueryFilter startOnlyFilterWithCounting = new SliceQueryFilter(startOnlyRange, false, 1);
        SliceQueryFilter startOnlyFilterReversedWithCounting = new SliceQueryFilter(startOnlyRangeReversed,
                true, 1);

        SliceQueryFilter middleOnlyFilter = new SliceQueryFilter(middleOnlyRanges,
                false,
                Integer.MAX_VALUE);
        SliceQueryFilter middleOnlyFilterReversed = new SliceQueryFilter(middleOnlyRangesReversed, true,
                Integer.MAX_VALUE);
        SliceQueryFilter middleOnlyFilterWithCounting = new SliceQueryFilter(middleOnlyRanges, false, 1);
        SliceQueryFilter middleOnlyFilterReversedWithCounting = new SliceQueryFilter(middleOnlyRangesReversed,
                true, 1);

        SliceQueryFilter endOnlyFilter = new SliceQueryFilter(endOnlyRanges, false,
                Integer.MAX_VALUE);
        SliceQueryFilter endOnlyReversed = new SliceQueryFilter(endOnlyRangesReversed, true,
                Integer.MAX_VALUE);
        SliceQueryFilter endOnlyWithCounting = new SliceQueryFilter(endOnlyRanges, false, 1);
        SliceQueryFilter endOnlyWithReversedCounting = new SliceQueryFilter(endOnlyRangesReversed,
                true, 1);

        SliceQueryFilter startMiddleAndEndFilter = new SliceQueryFilter(startMiddleAndEndRanges, false,
                Integer.MAX_VALUE);
        SliceQueryFilter startMiddleAndEndFilterReversed = new SliceQueryFilter(startMiddleAndEndRangesReversed, true,
                Integer.MAX_VALUE);
        SliceQueryFilter startMiddleAndEndFilterWithCounting = new SliceQueryFilter(startMiddleAndEndRanges, false,
                1);
        SliceQueryFilter startMiddleAndEndFilterReversedWithCounting = new SliceQueryFilter(
                startMiddleAndEndRangesReversed, true,
                1);

        findRowGetSlicesAndAssertColsFound(cfs, startOnlyFilter, "a", "cola");
        findRowGetSlicesAndAssertColsFound(cfs, startOnlyFilterReversed, "a", "cola");
        findRowGetSlicesAndAssertColsFound(cfs, startOnlyFilterWithCounting, "a", "cola");
        findRowGetSlicesAndAssertColsFound(cfs, startOnlyFilterReversedWithCounting, "a", "cola");

        findRowGetSlicesAndAssertColsFound(cfs, middleOnlyFilter, "a", new String[] {});
        findRowGetSlicesAndAssertColsFound(cfs, middleOnlyFilterReversed, "a", new String[] {});
        findRowGetSlicesAndAssertColsFound(cfs, middleOnlyFilterWithCounting, "a", new String[] {});
        findRowGetSlicesAndAssertColsFound(cfs, middleOnlyFilterReversedWithCounting, "a", new String[] {});

        findRowGetSlicesAndAssertColsFound(cfs, endOnlyFilter, "a", new String[] {});
        findRowGetSlicesAndAssertColsFound(cfs, endOnlyReversed, "a", new String[] {});
        findRowGetSlicesAndAssertColsFound(cfs, endOnlyWithCounting, "a", new String[] {});
        findRowGetSlicesAndAssertColsFound(cfs, endOnlyWithReversedCounting, "a", new String[] {});

        findRowGetSlicesAndAssertColsFound(cfs, startMiddleAndEndFilter, "a", "cola");
        findRowGetSlicesAndAssertColsFound(cfs, startMiddleAndEndFilterReversed, "a", "cola");
        findRowGetSlicesAndAssertColsFound(cfs, startMiddleAndEndFilterWithCounting, "a", "cola");
        findRowGetSlicesAndAssertColsFound(cfs, startMiddleAndEndFilterReversedWithCounting, "a", "cola");

        findRowGetSlicesAndAssertColsFound(cfs, startOnlyFilter, "c", "cola", "colb", "colc");
        findRowGetSlicesAndAssertColsFound(cfs, startOnlyFilterReversed, "c", "colc", "colb", "cola");
        findRowGetSlicesAndAssertColsFound(cfs, startOnlyFilterWithCounting, "c", "cola");
        findRowGetSlicesAndAssertColsFound(cfs, startOnlyFilterReversedWithCounting, "c", "colc");

        findRowGetSlicesAndAssertColsFound(cfs, middleOnlyFilter, "c", new String[] {});
        findRowGetSlicesAndAssertColsFound(cfs, middleOnlyFilterReversed, "c", new String[] {});
        findRowGetSlicesAndAssertColsFound(cfs, middleOnlyFilterWithCounting, "c", new String[] {});
        findRowGetSlicesAndAssertColsFound(cfs, middleOnlyFilterReversedWithCounting, "c", new String[] {});

        findRowGetSlicesAndAssertColsFound(cfs, endOnlyFilter, "c", new String[] {});
        findRowGetSlicesAndAssertColsFound(cfs, endOnlyReversed, "c", new String[] {});
        findRowGetSlicesAndAssertColsFound(cfs, endOnlyWithCounting, "c", new String[] {});
        findRowGetSlicesAndAssertColsFound(cfs, endOnlyWithReversedCounting, "c", new String[] {});

        findRowGetSlicesAndAssertColsFound(cfs, startMiddleAndEndFilter, "c", "cola", "colb", "colc");
        findRowGetSlicesAndAssertColsFound(cfs, startMiddleAndEndFilterReversed, "c", "colc", "colb", "cola");
        findRowGetSlicesAndAssertColsFound(cfs, startMiddleAndEndFilterWithCounting, "c", "cola");
        findRowGetSlicesAndAssertColsFound(cfs, startMiddleAndEndFilterReversedWithCounting, "c", "colc");

        findRowGetSlicesAndAssertColsFound(cfs, startOnlyFilter, "f", "cola", "colb", "colc");
        findRowGetSlicesAndAssertColsFound(cfs, startOnlyFilterReversed, "f", "colc", "colb", "cola");
        findRowGetSlicesAndAssertColsFound(cfs, startOnlyFilterWithCounting, "f", "cola");
        findRowGetSlicesAndAssertColsFound(cfs, startOnlyFilterReversedWithCounting, "f", "colc");

        findRowGetSlicesAndAssertColsFound(cfs, middleOnlyFilter, "f", "colf");

        findRowGetSlicesAndAssertColsFound(cfs, middleOnlyFilterReversed, "f", "colf");
        findRowGetSlicesAndAssertColsFound(cfs, middleOnlyFilterWithCounting, "f", "colf");
        findRowGetSlicesAndAssertColsFound(cfs, middleOnlyFilterReversedWithCounting, "f", "colf");

        findRowGetSlicesAndAssertColsFound(cfs, endOnlyFilter, "f", new String[] {});
        findRowGetSlicesAndAssertColsFound(cfs, endOnlyReversed, "f", new String[] {});
        findRowGetSlicesAndAssertColsFound(cfs, endOnlyWithCounting, "f", new String[] {});
        findRowGetSlicesAndAssertColsFound(cfs, endOnlyWithReversedCounting, "f", new String[] {});

        findRowGetSlicesAndAssertColsFound(cfs, startMiddleAndEndFilter, "f", "cola", "colb", "colc", "colf");

        findRowGetSlicesAndAssertColsFound(cfs, startMiddleAndEndFilterReversed, "f", "colf", "colc", "colb",
                "cola");
        findRowGetSlicesAndAssertColsFound(cfs, startMiddleAndEndFilterWithCounting, "f", "cola");
        findRowGetSlicesAndAssertColsFound(cfs, startMiddleAndEndFilterReversedWithCounting, "f", "colf");

        findRowGetSlicesAndAssertColsFound(cfs, startOnlyFilter, "h", "cola", "colb", "colc");
        findRowGetSlicesAndAssertColsFound(cfs, startOnlyFilterReversed, "h", "colc", "colb", "cola");
        findRowGetSlicesAndAssertColsFound(cfs, startOnlyFilterWithCounting, "h", "cola");
        findRowGetSlicesAndAssertColsFound(cfs, startOnlyFilterReversedWithCounting, "h", "colc");

        findRowGetSlicesAndAssertColsFound(cfs, middleOnlyFilter, "h", "colf", "colg");
        findRowGetSlicesAndAssertColsFound(cfs, middleOnlyFilterReversed, "h", "colg", "colf");
        findRowGetSlicesAndAssertColsFound(cfs, middleOnlyFilterWithCounting, "h", "colf");
        findRowGetSlicesAndAssertColsFound(cfs, middleOnlyFilterReversedWithCounting, "h", "colg");

        findRowGetSlicesAndAssertColsFound(cfs, endOnlyFilter, "h", new String[] {});
        findRowGetSlicesAndAssertColsFound(cfs, endOnlyReversed, "h", new String[] {});
        findRowGetSlicesAndAssertColsFound(cfs, endOnlyWithCounting, "h", new String[] {});
        findRowGetSlicesAndAssertColsFound(cfs, endOnlyWithReversedCounting, "h", new String[] {});

        findRowGetSlicesAndAssertColsFound(cfs, startMiddleAndEndFilter, "h", "cola", "colb", "colc", "colf",
                "colg");
        findRowGetSlicesAndAssertColsFound(cfs, startMiddleAndEndFilterReversed, "h", "colg", "colf", "colc", "colb",
                "cola");
        findRowGetSlicesAndAssertColsFound(cfs, startMiddleAndEndFilterWithCounting, "h", "cola");
        findRowGetSlicesAndAssertColsFound(cfs, startMiddleAndEndFilterReversedWithCounting, "h", "colg");

        findRowGetSlicesAndAssertColsFound(cfs, startOnlyFilter, "j", "cola", "colb", "colc");
        findRowGetSlicesAndAssertColsFound(cfs, startOnlyFilterReversed, "j", "colc", "colb", "cola");
        findRowGetSlicesAndAssertColsFound(cfs, startOnlyFilterWithCounting, "j", "cola");
        findRowGetSlicesAndAssertColsFound(cfs, startOnlyFilterReversedWithCounting, "j", "colc");

        findRowGetSlicesAndAssertColsFound(cfs, middleOnlyFilter, "j", "colf", "colg");
        findRowGetSlicesAndAssertColsFound(cfs, middleOnlyFilterReversed, "j", "colg", "colf");
        findRowGetSlicesAndAssertColsFound(cfs, middleOnlyFilterWithCounting, "j", "colf");
        findRowGetSlicesAndAssertColsFound(cfs, middleOnlyFilterReversedWithCounting, "j", "colg");

        findRowGetSlicesAndAssertColsFound(cfs, endOnlyFilter, "j", "colj");
        findRowGetSlicesAndAssertColsFound(cfs, endOnlyReversed, "j", "colj");
        findRowGetSlicesAndAssertColsFound(cfs, endOnlyWithCounting, "j", "colj");
        findRowGetSlicesAndAssertColsFound(cfs, endOnlyWithReversedCounting, "j", "colj");

        findRowGetSlicesAndAssertColsFound(cfs, startMiddleAndEndFilter, "j", "cola", "colb", "colc", "colf", "colg",
                "colj");
        findRowGetSlicesAndAssertColsFound(cfs, startMiddleAndEndFilterReversed, "j", "colj", "colg", "colf", "colc",
                "colb", "cola");
        findRowGetSlicesAndAssertColsFound(cfs, startMiddleAndEndFilterWithCounting, "j", "cola");
        findRowGetSlicesAndAssertColsFound(cfs, startMiddleAndEndFilterReversedWithCounting, "j", "colj");

        findRowGetSlicesAndAssertColsFound(cfs, startOnlyFilter, "l", "cola", "colb", "colc");
        findRowGetSlicesAndAssertColsFound(cfs, startOnlyFilterReversed, "l", "colc", "colb", "cola");
        findRowGetSlicesAndAssertColsFound(cfs, startOnlyFilterWithCounting, "l", "cola");
        findRowGetSlicesAndAssertColsFound(cfs, startOnlyFilterReversedWithCounting, "l", "colc");

        findRowGetSlicesAndAssertColsFound(cfs, middleOnlyFilter, "l", "colf", "colg");
        findRowGetSlicesAndAssertColsFound(cfs, middleOnlyFilterReversed, "l", "colg", "colf");
        findRowGetSlicesAndAssertColsFound(cfs, middleOnlyFilterWithCounting, "l", "colf");
        findRowGetSlicesAndAssertColsFound(cfs, middleOnlyFilterReversedWithCounting, "l", "colg");

        findRowGetSlicesAndAssertColsFound(cfs, endOnlyFilter, "l", "colj", "colk", "coll");
        findRowGetSlicesAndAssertColsFound(cfs, endOnlyReversed, "l", "coll", "colk", "colj");
        findRowGetSlicesAndAssertColsFound(cfs, endOnlyWithCounting, "l", "colj");
        findRowGetSlicesAndAssertColsFound(cfs, endOnlyWithReversedCounting, "l", "coll");

        findRowGetSlicesAndAssertColsFound(cfs, startMiddleAndEndFilter, "l", "cola", "colb", "colc", "colf", "colg",
                "colj", "colk", "coll");
        findRowGetSlicesAndAssertColsFound(cfs, startMiddleAndEndFilterReversed, "l", "coll", "colk", "colj", "colg",
                "colf", "colc", "colb", "cola");
        findRowGetSlicesAndAssertColsFound(cfs, startMiddleAndEndFilterWithCounting, "l", "cola");
        findRowGetSlicesAndAssertColsFound(cfs, startMiddleAndEndFilterReversedWithCounting, "l", "coll");
    }

    private void findRowGetSlicesAndAssertColsFound(ColumnFamilyStore cfs, SliceQueryFilter filter, String rowKey,
            String... colNames)
    {
        List<Row> rows = cfs.getRangeSlice(new Bounds<RowPosition>(rp(rowKey), rp(rowKey)),
                                           null,
                                           filter,
                                           Integer.MAX_VALUE,
                                           System.currentTimeMillis(),
                                           false,
                                           false);
        assertSame("unexpected number of rows ", 1, rows.size());
        Row row = rows.get(0);
        Collection<Cell> cols = !filter.isReversed() ? row.cf.getSortedColumns() : row.cf.getReverseSortedColumns();
        // printRow(cfs, new String(row.key.key.array()), cols);
        String[] returnedColsNames = Iterables.toArray(Iterables.transform(cols, new Function<Cell, String>()
        {
            public String apply(Cell arg0)
            {
                return Util.string(arg0.name().toByteBuffer());
            }
        }), String.class);

        assertTrue(
                "Columns did not match. Expected: " + Arrays.toString(colNames) + " but got:"
                        + Arrays.toString(returnedColsNames), Arrays.equals(colNames, returnedColsNames));
        int i = 0;
        for (Cell col : cols)
        {
            assertEquals(colNames[i++], Util.string(col.name().toByteBuffer()));
        }
    }

    private void printRow(ColumnFamilyStore cfs, String rowKey, Collection<Cell> cols)
    {
        DecoratedKey ROW = Util.dk(rowKey);
        System.err.println("Original:");
        ColumnFamily cf = cfs.getColumnFamily(QueryFilter.getIdentityFilter(ROW, "Standard1", System.currentTimeMillis()));
        System.err.println("Row key: " + rowKey + " Cols: "
                + Iterables.transform(cf.getSortedColumns(), new Function<Cell, String>()
                {
                    public String apply(Cell arg0)
                    {
                        return Util.string(arg0.name().toByteBuffer());
                    }
                }));
        System.err.println("Filtered:");
        Iterable<String> transformed = Iterables.transform(cols, new Function<Cell, String>()
        {
            public String apply(Cell arg0)
            {
                return Util.string(arg0.name().toByteBuffer());
            }
        });
        System.err.println("Row key: " + rowKey + " Cols: " + transformed);
    }
    
    @Test
    public void testRebuildSecondaryIndex() throws IOException
    {
        CellName indexedCellName = cellname("indexed");
        Mutation rm;

        rm = new Mutation("PerRowSecondaryIndex", ByteBufferUtil.bytes("k1"));
        rm.add("Indexed1", indexedCellName, ByteBufferUtil.bytes("foo"), 1);

        rm.apply();
        assertTrue(Arrays.equals("k1".getBytes(), PerRowSecondaryIndexTest.TestIndex.LAST_INDEXED_KEY.array()));
        
        Keyspace.open("PerRowSecondaryIndex").getColumnFamilyStore("Indexed1").forceBlockingFlush();
        
        PerRowSecondaryIndexTest.TestIndex.reset();
        
        ColumnFamilyStore.rebuildSecondaryIndex("PerRowSecondaryIndex", "Indexed1", PerRowSecondaryIndexTest.TestIndex.class.getSimpleName());
        assertTrue(Arrays.equals("k1".getBytes(), PerRowSecondaryIndexTest.TestIndex.LAST_INDEXED_KEY.array()));
        
        PerRowSecondaryIndexTest.TestIndex.reset();
        PerRowSecondaryIndexTest.TestIndex.ACTIVE = false;
        ColumnFamilyStore.rebuildSecondaryIndex("PerRowSecondaryIndex", "Indexed1", PerRowSecondaryIndexTest.TestIndex.class.getSimpleName());
        assertNull(PerRowSecondaryIndexTest.TestIndex.LAST_INDEXED_KEY);
        
        PerRowSecondaryIndexTest.TestIndex.reset();
    }
}
