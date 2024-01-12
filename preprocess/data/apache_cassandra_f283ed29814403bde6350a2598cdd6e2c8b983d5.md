Refactoring Types: ['Inline Method']
/db/ColumnFamilyStore.java
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

import java.io.File;
import java.io.FileFilter;
import java.io.IOException;
import java.lang.management.ManagementFactory;
import java.nio.ByteBuffer;
import java.util.*;
import java.util.concurrent.*;
import java.util.concurrent.atomic.AtomicInteger;
import java.util.regex.Pattern;
import javax.management.*;

import com.google.common.annotations.VisibleForTesting;
import com.google.common.base.Function;
import com.google.common.collect.*;
import com.google.common.util.concurrent.Futures;
import com.google.common.util.concurrent.Uninterruptibles;
import org.cliffc.high_scale_lib.NonBlockingHashMap;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import org.apache.cassandra.cache.KeyCacheKey;
import org.apache.cassandra.cache.IRowCacheEntry;
import org.apache.cassandra.cache.RowCacheKey;
import org.apache.cassandra.cache.RowCacheSentinel;
import org.apache.cassandra.concurrent.JMXEnabledThreadPoolExecutor;
import org.apache.cassandra.config.CFMetaData;
import org.apache.cassandra.config.CFMetaData.SpeculativeRetry;
import org.apache.cassandra.config.ColumnDefinition;
import org.apache.cassandra.config.DatabaseDescriptor;
import org.apache.cassandra.config.Schema;
import org.apache.cassandra.db.columniterator.OnDiskAtomIterator;
import org.apache.cassandra.db.commitlog.CommitLog;
import org.apache.cassandra.db.commitlog.ReplayPosition;
import org.apache.cassandra.db.compaction.*;
import org.apache.cassandra.db.filter.*;
import org.apache.cassandra.db.index.SecondaryIndex;
import org.apache.cassandra.db.index.SecondaryIndexManager;
import org.apache.cassandra.db.marshal.AbstractType;
import org.apache.cassandra.db.marshal.CompositeType;
import org.apache.cassandra.dht.*;
import org.apache.cassandra.dht.Range;
import org.apache.cassandra.exceptions.ConfigurationException;
import org.apache.cassandra.io.FSReadError;
import org.apache.cassandra.io.compress.CompressionParameters;
import org.apache.cassandra.io.sstable.*;
import org.apache.cassandra.io.sstable.Descriptor;
import org.apache.cassandra.io.util.FileUtils;
import org.apache.cassandra.metrics.ColumnFamilyMetrics;
import org.apache.cassandra.service.CacheService;
import org.apache.cassandra.service.StorageService;
import org.apache.cassandra.streaming.StreamLockfile;
import org.apache.cassandra.thrift.IndexExpression;
import org.apache.cassandra.tracing.Tracing;
import org.apache.cassandra.utils.*;

import static org.apache.cassandra.config.CFMetaData.Caching;

public class ColumnFamilyStore implements ColumnFamilyStoreMBean
{
    private static final Logger logger = LoggerFactory.getLogger(ColumnFamilyStore.class);

    public static final ExecutorService postFlushExecutor = new JMXEnabledThreadPoolExecutor("MemtablePostFlusher");

    public final Keyspace keyspace;
    public final String name;
    public final CFMetaData metadata;
    public final IPartitioner partitioner;
    private final String mbeanName;
    private volatile boolean valid = true;

    /* Memtables and SSTables on disk for this column family */
    private final DataTracker data;

    /* This is used to generate the next index for a SSTable */
    private final AtomicInteger fileIndexGenerator = new AtomicInteger(0);

    public final SecondaryIndexManager indexManager;

    private static final int INTERN_CUTOFF = 256;
    public final ConcurrentMap<ByteBuffer, ByteBuffer> internedNames = new NonBlockingHashMap<ByteBuffer, ByteBuffer>();

    /* These are locally held copies to be changed from the config during runtime */
    private volatile DefaultInteger minCompactionThreshold;
    private volatile DefaultInteger maxCompactionThreshold;
    private volatile AbstractCompactionStrategy compactionStrategy;

    public final Directories directories;

    public final ColumnFamilyMetrics metric;
    public volatile long sampleLatencyNanos;
    private final ScheduledFuture<?> latencyCalculator;

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

        maybeReloadCompactionStrategy();

        scheduleFlush();

        indexManager.reload();

        // If the CF comparator has changed, we need to change the memtable,
        // because the old one still aliases the previous comparator.
        if (getMemtableThreadSafe().initialComparator != metadata.comparator)
            switchMemtable(true, true);
    }

    private void maybeReloadCompactionStrategy()
    {
        // Check if there is a need for reloading
        if (metadata.compactionStrategyClass.equals(compactionStrategy.getClass()) && metadata.compactionStrategyOptions.equals(compactionStrategy.options))
            return;

        // synchronize vs runWithCompactionsDisabled calling pause/resume.  otherwise, letting old compactions
        // finish should be harmless and possibly useful.
        synchronized (this)
        {
            compactionStrategy.shutdown();
            compactionStrategy = metadata.createCompactionStrategyInstance(this);
            compactionStrategy.startup();
        }
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
                    if (getMemtableThreadSafe().isExpired())
                    {
                        // if memtable is already expired but didn't flush because it's empty,
                        // then schedule another flush.
                        if (isClean())
                            scheduleFlush();
                        else
                            forceFlush(); // scheduleFlush() will be called by the constructor of the new memtable.
                    }
                }
            };
            StorageService.scheduledTasks.schedule(runnable, period, TimeUnit.MILLISECONDS);
        }
    }

    public static Runnable getBackgroundCompactionTaskSubmitter()
    {
        return new Runnable()
        {
            public void run()
            {
                List<ColumnFamilyStore> submitted = new ArrayList<>();
                for (Keyspace keyspace : Keyspace.all())
                    for (ColumnFamilyStore cfs : keyspace.getColumnFamilyStores())
                        if (!CompactionManager.instance.submitBackground(cfs, false).isEmpty())
                            submitted.add(cfs);

                while (!submitted.isEmpty() && CompactionManager.instance.getActiveCompactions() < CompactionManager.instance.getMaximumCompactorThreads())
                {
                    List<ColumnFamilyStore> submitMore = ImmutableList.copyOf(submitted);
                    submitted.clear();
                    for (ColumnFamilyStore cfs : submitMore)
                        if (!CompactionManager.instance.submitBackground(cfs, false).isEmpty())
                            submitted.add(cfs);
                }
            }
        };
    }

    public void setCompactionStrategyClass(String compactionStrategyClass)
    {
        try
        {
            metadata.compactionStrategyClass = CFMetaData.createCompactionStrategy(compactionStrategyClass);
            maybeReloadCompactionStrategy();
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

        Caching caching = metadata.getCaching();

        logger.info("Initializing {}.{}", keyspace.getName(), name);

        // scan for sstables corresponding to this cf and load them
        data = new DataTracker(this);

        if (loadSSTables)
        {
            Directories.SSTableLister sstableFiles = directories.sstableLister().skipTemporary(true);
            Collection<SSTableReader> sstables = SSTableReader.openAll(sstableFiles.list().entrySet(), metadata, this.partitioner);
            data.addInitialSSTables(sstables);
        }

        if (caching == Caching.ALL || caching == Caching.KEYS_ONLY)
            CacheService.instance.keyCache.loadSaved(this);

        // compaction strategy should be created after the CFS has been prepared
        this.compactionStrategy = metadata.createCompactionStrategyInstance(this);
        this.compactionStrategy.startup();

        if (maxCompactionThreshold.value() <= 0 || minCompactionThreshold.value() <=0)
        {
            logger.warn("Disabling compaction strategy by setting compaction thresholds to 0 is deprecated, set the compaction option 'enabled' to 'false' instead.");
            this.compactionStrategy.disable();
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
        latencyCalculator = StorageService.optionalTasks.scheduleWithFixedDelay(new Runnable()
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
        valid = false;

        try
        {
            unregisterMBean();
        }
        catch (Exception e)
        {
            // this shouldn't block anything.
            logger.warn("Failed unregistering mbean: " + mbeanName, e);
        }

        latencyCalculator.cancel(false);
        compactionStrategy.shutdown();
        SystemKeyspace.removeTruncationRecord(metadata.cfId);
        data.unreferenceSSTables();
        indexManager.invalidate();

        for (RowCacheKey key : CacheService.instance.rowCache.getKeySet())
            if (key.cfId == metadata.cfId)
                invalidateCachedRow(key);

        String ksname = keyspace.getName();
        for (KeyCacheKey key : CacheService.instance.keyCache.getKeySet())
            if (key.getPathInfo().left.equals(ksname) && key.getPathInfo().right.equals(name))
                CacheService.instance.keyCache.remove(key);
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
        Directories directories = Directories.create(keyspace.getName(), columnFamily);
        Directories.SSTableLister lister = directories.sstableLister().includeBackups(true);
        List<Integer> generations = new ArrayList<Integer>();
        for (Map.Entry<Descriptor, Set<Component>> entry : lister.list().entrySet())
        {
            Descriptor desc = entry.getKey();
            generations.add(desc.generation);
            if (!desc.isCompatible())
                throw new RuntimeException(String.format("Incompatible SSTable found.  Current version %s is unable to read file: %s.  Please run upgradesstables.",
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
    public static void scrubDataDirectories(String keyspaceName, String columnFamily)
    {
        Directories directories = Directories.create(keyspaceName, columnFamily);

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

        logger.debug("Removing compacted SSTable files from {} (see http://wiki.apache.org/cassandra/MemtableSSTable)", columnFamily);

        for (Map.Entry<Descriptor,Set<Component>> sstableFiles : directories.sstableLister().list().entrySet())
        {
            Descriptor desc = sstableFiles.getKey();
            Set<Component> components = sstableFiles.getValue();

            if (components.contains(Component.COMPACTED_MARKER) || desc.temporary)
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
        Pattern tmpCacheFilePattern = Pattern.compile(keyspaceName + "-" + columnFamily + "-(Key|Row)Cache.*\\.tmp$");
        File dir = new File(DatabaseDescriptor.getSavedCachesLocation());

        if (dir.exists())
        {
            assert dir.isDirectory();
            for (File file : dir.listFiles())
                if (tmpCacheFilePattern.matcher(file.getName()).matches())
                    if (!file.delete())
                        logger.warn("could not delete " + file.getAbsolutePath());
        }

        // also clean out any index leftovers.
        CFMetaData cfm = Schema.instance.getCFMetaData(keyspaceName, columnFamily);
        if (cfm != null) // secondary indexes aren't stored in DD.
        {
            for (ColumnDefinition def : cfm.allColumns())
                scrubDataDirectories(keyspaceName, cfm.indexColumnFamilyName(def));
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
    public static void removeUnfinishedCompactionLeftovers(String keyspace, String columnfamily, Map<Integer, UUID> unfinishedCompactions)
    {
        Directories directories = Directories.create(keyspace, columnfamily);

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
                         keyspace, columnfamily, missingGenerations);
        }

        // remove new sstables from compactions that didn't complete, and compute
        // set of ancestors that shouldn't exist anymore
        Set<Integer> completedAncestors = new HashSet<>();
        for (Map.Entry<Descriptor, Set<Component>> sstableFiles : directories.sstableLister().list().entrySet())
        {
            Descriptor desc = sstableFiles.getKey();

            Set<Integer> ancestors;
            try
            {
                ancestors = SSTableMetadata.serializer.deserialize(desc).right;
            }
            catch (IOException e)
            {
                throw new FSReadError(e, desc.filenameFor(Component.STATS));
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
            logger.info("completed loading ({} ms; {} keys) row cache for {}.{}",
                        TimeUnit.NANOSECONDS.toMillis(System.nanoTime() - start),
                        cachedRowsRead,
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
        logger.info("Loading new SSTables for " + keyspace.getName() + "/" + name + "...");

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
            if (descriptor.temporary) // in the process of being written
                continue;

            if (!descriptor.isCompatible())
                throw new RuntimeException(String.format("Can't open incompatible SSTable! Current version %s, found file: %s",
                                                         Descriptor.Version.CURRENT,
                                                         descriptor));

            // force foreign sstables to level 0
            try
            {
                if (new File(descriptor.filenameFor(Component.STATS)).exists())
                {
                    Pair<SSTableMetadata, Set<Integer>> oldMetadata = SSTableMetadata.serializer.deserialize(descriptor);
                    LeveledManifest.mutateLevel(oldMetadata, descriptor, descriptor.filenameFor(Component.STATS), 0);
                }
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
                                               false);
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
            logger.info("No new SSTables were found for " + keyspace.getName() + "/" + name);
            return;
        }

        logger.info("Loading new SSTables and building secondary indexes for " + keyspace.getName() + "/" + name + ": " + newSSTables);
        SSTableReader.acquireReferences(newSSTables);
        data.addSSTables(newSSTables);
        try
        {
            indexManager.maybeBuildSecondaryIndexes(newSSTables, indexManager.allIndexesNames());
        }
        finally
        {
            SSTableReader.releaseReferences(newSSTables);
        }

        logger.info("Done loading load new SSTables for " + keyspace.getName() + "/" + name);
    }

    public static void rebuildSecondaryIndex(String ksName, String cfName, String... idxNames)
    {
        ColumnFamilyStore cfs = Keyspace.open(ksName).getColumnFamilyStore(cfName);

        Set<String> indexes = new HashSet<String>(Arrays.asList(idxNames));

        Collection<SSTableReader> sstables = cfs.getSSTables();
        try
        {
            cfs.indexManager.setIndexRemoved(indexes);
            SSTableReader.acquireReferences(sstables);
            logger.info(String.format("User Requested secondary index re-build for %s/%s indexes", ksName, cfName));
            cfs.indexManager.maybeBuildSecondaryIndexes(sstables, indexes);
            cfs.indexManager.setIndexBuilt(indexes);
        }
        finally
        {
            SSTableReader.releaseReferences(sstables);
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
                                         true);
        return desc.filenameFor(Component.DATA);
    }

    /**
     * Switch and flush the current memtable, if it was dirty. The forceSwitch
     * flag allow to force switching the memtable even if it is clean (though
     * in that case we don't flush, as there is no point).
     */
    public Future<?> switchMemtable(final boolean writeCommitLog, boolean forceSwitch)
    {
        /*
         * If we can get the writelock, that means no new updates can come in and
         * all ongoing updates to memtables have completed. We can get the tail
         * of the log and use it as the starting position for log replay on recovery.
         *
         * This is why we Keyspace.switchLock needs to be global instead of per-Keyspace:
         * we need to schedule discardCompletedSegments calls in the same order as their
         * contexts (commitlog position) were read, even though the flush executor
         * is multithreaded.
         */
        Keyspace.switchLock.writeLock().lock();
        try
        {
            final Future<ReplayPosition> ctx = writeCommitLog ? CommitLog.instance.getContext() : Futures.immediateFuture(ReplayPosition.NONE);

            // submit the memtable for any indexed sub-cfses, and our own.
            final List<ColumnFamilyStore> icc = new ArrayList<ColumnFamilyStore>();
            // don't assume that this.memtable is dirty; forceFlush can bring us here during index build even if it is not
            for (ColumnFamilyStore cfs : concatWithIndexes())
            {
                if (forceSwitch || !cfs.getMemtableThreadSafe().isClean())
                    icc.add(cfs);
            }

            final CountDownLatch latch = new CountDownLatch(icc.size());
            for (ColumnFamilyStore cfs : icc)
            {
                Memtable memtable = cfs.data.switchMemtable();
                // With forceSwitch it's possible to get a clean memtable here.
                // In that case, since we've switched it already, just remove
                // it from the memtable pending flush right away.
                if (memtable.isClean())
                {
                    cfs.replaceFlushed(memtable, null);
                    latch.countDown();
                }
                else
                {
                    logger.info("Enqueuing flush of {}", memtable);
                    memtable.flushAndSignal(latch, ctx);
                }
            }

            if (metric.memtableSwitchCount.count() == Long.MAX_VALUE)
                metric.memtableSwitchCount.clear();
            metric.memtableSwitchCount.inc();

            // when all the memtables have been written, including for indexes, mark the flush in the commitlog header.
            // a second executor makes sure the onMemtableFlushes get called in the right order,
            // while keeping the wait-for-flush (future.get) out of anything latency-sensitive.
            return postFlushExecutor.submit(new WrappedRunnable()
            {
                public void runMayThrow() throws InterruptedException, ExecutionException
                {
                    latch.await();

                    if (!icc.isEmpty())
                    {
                        //only valid when memtables exist

                        for (SecondaryIndex index : indexManager.getIndexesNotBackedByCfs())
                        {
                            // flush any non-cfs backed indexes
                            logger.info("Flushing SecondaryIndex {}", index);
                            index.forceBlockingFlush();
                        }
                    }

                    if (writeCommitLog)
                    {
                        // if we're not writing to the commit log, we are replaying the log, so marking
                        // the log header with "you can discard anything written before the context" is not valid
                        CommitLog.instance.discardCompletedSegments(metadata.cfId, ctx.get());
                    }
                }
            });
        }
        finally
        {
            Keyspace.switchLock.writeLock().unlock();
        }
    }

    private boolean isClean()
    {
        // during index build, 2ary index memtables can be dirty even if parent is not.  if so,
        // we want flushLargestMemtables to flush the 2ary index ones too.
        for (ColumnFamilyStore cfs : concatWithIndexes())
            if (!cfs.getMemtableThreadSafe().isClean())
                return false;

        return true;
    }

    /**
     * @return a future, with a guarantee that any data inserted prior to the forceFlush() call is fully flushed
     *         by the time future.get() returns. Never returns null.
     */
    public Future<?> forceFlush()
    {
        if (isClean())
        {
            // We could have a memtable for this column family that is being
            // flushed. Make sure the future returned wait for that so callers can
            // assume that any data inserted prior to the call are fully flushed
            // when the future returns (see #5241).
            return postFlushExecutor.submit(new Runnable()
            {
                public void run()
                {
                    logger.debug("forceFlush requested but everything is clean in {}", name);
                }
            });
        }

        return switchMemtable(true, false);
    }

    public void forceBlockingFlush()
    {
        FBUtilities.waitOnFuture(forceFlush());
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
    public void apply(DecoratedKey key, ColumnFamily columnFamily, SecondaryIndexManager.Updater indexer)
    {
        long start = System.nanoTime();

        Memtable mt = getMemtableThreadSafe();
        final long timeDelta = mt.put(key, columnFamily, indexer);
        maybeUpdateRowCache(key);
        metric.writeLatency.addNano(System.nanoTime() - start);
        if(timeDelta < Long.MAX_VALUE)
            metric.colUpdateTimeDeltaHistogram.update(timeDelta);
        mt.maybeUpdateLiveRatio();
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
        return cf.getColumnCount() == 0 && !cf.isMarkedForDelete() ? null : cf;
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
     This is complicated because we need to preserve deleted columns, supercolumns, and columnfamilies
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

        removeDeletedColumnsOnly(cf, gcBefore, indexer);
        return removeDeletedCF(cf, gcBefore);
    }

    /**
     * Removes only per-cell tombstones, cells that are shadowed by a row-level or range tombstone, or
     * columns that have been dropped from the schema (for CQL3 tables only).
     * @return the updated ColumnFamily
     */
    public static long removeDeletedColumnsOnly(ColumnFamily cf, int gcBefore, SecondaryIndexManager.Updater indexer)
    {
        BatchRemoveIterator<Column> iter = cf.batchRemoveIterator();
        DeletionInfo.InOrderTester tester = cf.inOrderDeletionTester();
        boolean hasDroppedColumns = !cf.metadata.getDroppedColumns().isEmpty();
        long removedBytes = 0;
        while (iter.hasNext())
        {
            Column c = iter.next();
            // remove columns if
            // (a) the column itself is gcable or
            // (b) the column is shadowed by a CF tombstone
            // (c) the column has been dropped from the CF schema (CQL3 tables only)
            if (c.getLocalDeletionTime() < gcBefore || tester.isDeleted(c) || (hasDroppedColumns && isDroppedColumn(c, cf.metadata())))
            {
                iter.remove();
                indexer.remove(c);
                removedBytes += c.dataSize();
            }
        }
        iter.commit();
        return removedBytes;
    }

    public static long removeDeletedColumnsOnly(ColumnFamily cf, int gcBefore)
    {
        return removeDeletedColumnsOnly(cf, gcBefore, SecondaryIndexManager.nullUpdater);
    }

    // returns true if
    // 1. this column has been dropped from schema and
    // 2. if it has been re-added since then, this particular column was inserted before the last drop
    private static boolean isDroppedColumn(Column c, CFMetaData meta)
    {
        Long droppedAt = meta.getDroppedColumns().get(((CompositeType) meta.comparator).extractLastComponent(c.name()));
        return droppedAt != null && c.timestamp() <= droppedAt;
    }

    private void removeDroppedColumns(ColumnFamily cf)
    {
        if (cf == null || cf.metadata.getDroppedColumns().isEmpty())
            return;

        BatchRemoveIterator<Column> iter = cf.batchRemoveIterator();
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
    public Set<SSTableReader> getOverlappingSSTables(Collection<SSTableReader> sstables)
    {
        logger.debug("Checking for sstables overlapping {}", sstables);

        // a normal compaction won't ever have an empty sstables list, but we create a skeleton
        // compaction controller for streaming, and that passes an empty list.
        if (sstables.isEmpty())
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
    public Set<SSTableReader> getAndReferenceOverlappingSSTables(Collection<SSTableReader> sstables)
    {
        while (true)
        {
            Set<SSTableReader> overlapped = getOverlappingSSTables(sstables);
            if (SSTableReader.acquireReferences(overlapped))
                return overlapped;
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
            return SSTable.getTotalBytes(sstables);
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

    public void forceCleanup(CounterId.OneShotRenewer renewer) throws ExecutionException, InterruptedException
    {
        CompactionManager.instance.performCleanup(ColumnFamilyStore.this, renewer);
    }

    public void scrub(boolean disableSnapshot, boolean skipCorrupted, boolean checkData) throws ExecutionException, InterruptedException
    {
        // skip snapshot creation during scrub, SEE JIRA 5891
        if(!disableSnapshot)
            snapshotWithoutFlush("pre-scrub-" + System.currentTimeMillis());
        CompactionManager.instance.performScrub(ColumnFamilyStore.this, skipCorrupted, checkData);
    }

    public void sstablesRewrite(boolean excludeCurrentVersion) throws ExecutionException, InterruptedException
    {
        CompactionManager.instance.performSSTableRewrite(ColumnFamilyStore.this, excludeCurrentVersion);
    }

    public void markObsolete(Collection<SSTableReader> sstables, OperationType compactionType)
    {
        assert !sstables.isEmpty();
        data.markObsolete(sstables, compactionType);
    }

    public void replaceCompactedSSTables(Collection<SSTableReader> sstables, Collection<SSTableReader> replacements, OperationType compactionType)
    {
        data.replaceCompactedSSTables(sstables, replacements, compactionType);
    }

    void replaceFlushed(Memtable memtable, SSTableReader sstable)
    {
        compactionStrategy.replaceFlushed(memtable, sstable);
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
        return metric.memtableDataSize.value();
    }

    public long getTotalMemtableLiveSize()
    {
        return getMemtableDataSize() + indexManager.getTotalLiveSize();
    }

    /**
     * @return the live size of all the memtables (the current active one and pending flush).
     */
    public long getAllMemtablesLiveSize()
    {
        long size = 0;
        for (Memtable mt : getDataTracker().getAllMemtables())
            size += mt.getLiveSize();
        return size;
    }

    /**
     * @return the size of all the memtables, including the pending flush ones and 2i memtables, if any.
     */
    public long getTotalAllMemtablesLiveSize()
    {
        long size = getAllMemtablesLiveSize();
        if (indexManager.hasIndexes())
            for (ColumnFamilyStore index : indexManager.getIndexesBackedByCfs())
                size += index.getAllMemtablesLiveSize();
        return size;
    }

    public int getMemtableSwitchCount()
    {
        return (int) metric.memtableSwitchCount.count();
    }

    Memtable getMemtableThreadSafe()
    {
        return data.getMemtable();
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
        return metric.pendingTasks.value();
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

    public ColumnFamily getColumnFamily(DecoratedKey key,
                                        ByteBuffer start,
                                        ByteBuffer finish,
                                        boolean reversed,
                                        int limit,
                                        long timestamp)
    {
        return getColumnFamily(QueryFilter.getSliceFilter(key, name, start, finish, reversed, limit, timestamp));
    }

    /**
     * fetch the row given by filter.key if it is in the cache; if not, read it from disk and cache it
     * @param cfId the column family to read the row from
     * @param filter the columns being queried.  Note that we still cache entire rows, but if a row is uncached
     *               and we race to cache it, only the winner will read the entire row
     * @return the entire row for filter.key, if present in the cache (or we can cache it), or just the column
     *         specified by filter otherwise
     */
    private ColumnFamily getThroughCache(UUID cfId, QueryFilter filter)
    {
        assert isRowCacheEnabled()
               : String.format("Row cache is not enabled on column family [" + name + "]");

        RowCacheKey key = new RowCacheKey(cfId, filter.key);

        // attempt a sentinel-read-cache sequence.  if a write invalidates our sentinel, we'll return our
        // (now potentially obsolete) data, but won't cache it. see CASSANDRA-3862
        IRowCacheEntry cached = CacheService.instance.rowCache.get(key);
        if (cached != null)
        {
            if (cached instanceof RowCacheSentinel)
            {
                // Some other read is trying to cache the value, just do a normal non-caching read
                Tracing.trace("Row cache miss (race)");
                return getTopLevelColumns(filter, Integer.MIN_VALUE);
            }
            Tracing.trace("Row cache hit");
            return (ColumnFamily) cached;
        }

        Tracing.trace("Row cache miss");
        RowCacheSentinel sentinel = new RowCacheSentinel();
        boolean sentinelSuccess = CacheService.instance.rowCache.putIfAbsent(key, sentinel);

        try
        {
            ColumnFamily data = getTopLevelColumns(QueryFilter.getIdentityFilter(filter.key, name, filter.timestamp),
                                                   Integer.MIN_VALUE);
            if (sentinelSuccess && data != null)
                CacheService.instance.rowCache.replace(key, sentinel, data);

            return data;
        }
        finally
        {
            if (sentinelSuccess && data == null)
                invalidateCachedRow(key);
        }
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

                result = filterColumnFamily(cached, filter);
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
        ColumnFamily cf = cached.cloneMeShallow(ArrayBackedSortedColumns.factory, filter.filter.isReversed());
        OnDiskAtomIterator ci = filter.getColumnFamilyIterator(cached);

        int gcBefore = gcBefore(filter.timestamp);
        filter.collateOnDiskAtom(cf, ci, gcBefore);
        return removeDeletedCF(cf, gcBefore);
    }

    /**
     * Get the current view and acquires references on all its sstables.
     * This is a bit tricky because we must ensure that between the time we
     * get the current view and the time we acquire the references the set of
     * sstables hasn't changed. Otherwise we could get a view for which an
     * sstable have been deleted in the meantime.
     *
     * At the end of this method, a reference on all the sstables of the
     * returned view will have been acquired and must thus be released when
     * appropriate.
     */
    private DataTracker.View markCurrentViewReferenced()
    {
        while (true)
        {
            DataTracker.View currentView = data.getView();
            if (SSTableReader.acquireReferences(currentView.sstables))
                return currentView;
        }
    }

    /**
     * Get the current sstables, acquiring references on all of them.
     * The caller is in charge of releasing the references on the sstables.
     *
     * See markCurrentViewReferenced() above.
     */
    public Collection<SSTableReader> markCurrentSSTablesReferenced()
    {
        return markCurrentViewReferenced().sstables;
    }

    private ViewFragment markReferenced(Function<DataTracker.View, List<SSTableReader>> filter)
    {
        List<SSTableReader> sstables = null;
        List<SSTableReader> prevSstables = null;
        DataTracker.View view;

        while (true)
        {
            view = data.getView();

            if (view.intervalTree.isEmpty())
            {
                sstables = Collections.emptyList();
                break;
            }

            sstables = filter.apply(view);

            if (null != prevSstables)
            {
                // we're trying again so verify we're acquiring something different
                assert (!new HashSet<>(sstables).containsAll(prevSstables)) : "Next attempt at acquiring " +
                        "references is trying the same files. There is probably a reference counting bug somewhere.";
            }

            if (SSTableReader.acquireReferences(sstables))
                break;
            // retry w/ new view
            prevSstables = sstables;
        }

        return new ViewFragment(sstables, Iterables.concat(Collections.singleton(view.memtable), view.memtablesPendingFlush));
    }

    /**
     * @return a ViewFragment containing the sstables and memtables that may need to be merged
     * for the given @param key, according to the interval tree
     */
    public ViewFragment markReferenced(final DecoratedKey key)
    {
        assert !key.isMinimum(partitioner);
        return markReferenced(new Function<DataTracker.View, List<SSTableReader>>()
        {
            public List<SSTableReader> apply(DataTracker.View view)
            {
                return compactionStrategy.filterSSTablesForReads(view.intervalTree.search(key));
            }
        });
    }

    /**
     * @return a ViewFragment containing the sstables and memtables that may need to be merged
     * for rows within @param rowBounds, inclusive, according to the interval tree.
     */
    public ViewFragment markReferenced(final AbstractBounds<RowPosition> rowBounds)
    {
        return markReferenced(new Function<DataTracker.View, List<SSTableReader>>()
        {
            public List<SSTableReader> apply(DataTracker.View view)
            {
                return compactionStrategy.filterSSTablesForReads(view.sstablesInBounds(rowBounds));
            }
        });
    }

    /**
     * @return a ViewFragment containing the sstables and memtables that may need to be merged
     * for rows for all of @param rowBoundsCollection, inclusive, according to the interval tree.
     */
    public ViewFragment markReferenced(final Collection<AbstractBounds<RowPosition>> rowBoundsCollection)
    {
        return markReferenced(new Function<DataTracker.View, List<SSTableReader>>()
        {
            public List<SSTableReader> apply(DataTracker.View view)
            {
                Set<SSTableReader> sstables = Sets.newHashSet();
                for (AbstractBounds<RowPosition> rowBounds : rowBoundsCollection)
                    sstables.addAll(view.sstablesInBounds(rowBounds));

                return ImmutableList.copyOf(sstables);
            }
        });
    }

    public List<String> getSSTablesForKey(String key)
    {
        DecoratedKey dk = partitioner.decorateKey(metadata.getKeyValidator().fromString(key));
        ViewFragment view = markReferenced(dk);
        try
        {
            List<String> files = new ArrayList<String>();
            for (SSTableReader sstr : view.sstables)
            {
                // check if the key actually exists in this sstable, without updating cache and stats
                if (sstr.getPosition(dk, SSTableReader.Operator.EQ, false) != null)
                    files.add(sstr.getFilename());
            }
            return files;
        }
        finally
        {
            SSTableReader.releaseReferences(view.sstables);
        }
    }

    public ColumnFamily getTopLevelColumns(QueryFilter filter, int gcBefore)
    {
        Tracing.trace("Executing single-partition query on {}", name);
        CollationController controller = new CollationController(this, filter, gcBefore);
        ColumnFamily columns = controller.getTopLevelColumns();
        metric.updateSSTableIterated(controller.getSstablesIterated());
        return columns;
    }

    public void cleanupCache()
    {
        Collection<Range<Token>> ranges = StorageService.instance.getLocalRanges(keyspace.getName());

        for (RowCacheKey key : CacheService.instance.rowCache.getKeySet())
        {
            DecoratedKey dk = partitioner.decorateKey(ByteBuffer.wrap(key.key));
            if (key.cfId == metadata.cfId && !Range.isInRanges(dk.token, ranges))
                invalidateCachedRow(dk);
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

        final ViewFragment view = markReferenced(range.keyRange());
        Tracing.trace("Executing seq scan across {} sstables for {}", view.sstables.size(), range.keyRange().getString(metadata.getKeyValidator()));

        try
        {
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
                        logger.trace("scanned {}", metadata.getKeyValidator().getString(key.key));

                    return current;
                }

                public void close() throws IOException
                {
                    SSTableReader.releaseReferences(view.sstables);
                    iterator.close();
                }
            };
        }
        catch (RuntimeException e)
        {
            // In case getIterator() throws, otherwise the iteror close method releases the references.
            SSTableReader.releaseReferences(view.sstables);
            throw e;
        }
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
                                             ByteBuffer columnStart,
                                             ByteBuffer columnStop,
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
        try
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
                            data.addAll(cf, HeapAllocator.instance);
                    }

                    removeDroppedColumns(data);

                    if (!filter.isSatisfiedBy(rawRow.key, data, null))
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

    public AbstractType<?> getComparator()
    {
        return metadata.comparator;
    }

    public void snapshotWithoutFlush(String snapshotName)
    {
        for (ColumnFamilyStore cfs : concatWithIndexes())
        {
            DataTracker.View currentView = cfs.markCurrentViewReferenced();

            try
            {
                for (SSTableReader ssTable : currentView.sstables)
                {
                    File snapshotDirectory = Directories.getSnapshotDirectory(ssTable.descriptor, snapshotName);
                    ssTable.createLinks(snapshotDirectory.getPath()); // hard links
                    if (logger.isDebugEnabled())
                        logger.debug("Snapshot for " + keyspace + " keyspace data file " + ssTable.getFilename() +
                                     " created in " + snapshotDirectory);
                }

                if (cfs.compactionStrategy instanceof LeveledCompactionStrategy)
                    cfs.directories.snapshotLeveledManifest(snapshotName);
            }
            finally
            {
                SSTableReader.releaseReferences(currentView.sstables);
            }
        }
    }

    public List<SSTableReader> getSnapshotSSTableReader(String tag) throws IOException
    {
        Map<Integer, SSTableReader> active = new HashMap<>();
        for (SSTableReader sstable : data.getView().sstables)
            active.put(sstable.descriptor.generation, sstable);
        Map<Descriptor, Set<Component>> snapshots = directories.sstableLister().snapshots(tag).list();
        List<SSTableReader> readers = new ArrayList<>(snapshots.size());
        try
        {
            for (Map.Entry<Descriptor, Set<Component>> entries : snapshots.entrySet())
            {
                // Try acquire reference to an active sstable instead of snapshot if it exists,
                // to avoid opening new sstables. If it fails, use the snapshot reference instead.
                SSTableReader sstable = active.get(entries.getKey().generation);
                if (sstable == null || !sstable.acquireReference())
                {
                    if (logger.isDebugEnabled())
                        logger.debug("using snapshot sstable {}", entries.getKey());
                    sstable = SSTableReader.open(entries.getKey(), entries.getValue(), metadata, partitioner);
                    // This is technically not necessary since it's a snapshot but makes things easier
                    sstable.acquireReference();
                }
                else if (logger.isDebugEnabled())
                {
                    logger.debug("using active sstable {}", entries.getKey());
                }
                readers.add(sstable);
            }
        }
        catch (IOException | RuntimeException e)
        {
            // In case one of the snapshot sstables fails to open,
            // we must release the references to the ones we opened so far
            SSTableReader.releaseReferences(readers);
            throw e;
        }
        return readers;
    }

    /**
     * Take a snap shot of this columnfamily store.
     *
     * @param snapshotName the name of the associated with the snapshot
     */
    public void snapshot(String snapshotName)
    {
        forceBlockingFlush();
        snapshotWithoutFlush(snapshotName);
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
        return cached == null || cached instanceof RowCacheSentinel ? null : (ColumnFamily) cached;
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
        Collection<SSTableReader> sstables = getSSTables();
        Iterable<DecoratedKey>[] samples = new Iterable[sstables.size()];
        int i = 0;
        for (SSTableReader sstable: sstables)
        {
            samples[i++] = sstable.getKeySamples(range);
        }
        return Iterables.concat(samples);
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
            Keyspace.switchLock.writeLock().lock();
            try
            {
                for (ColumnFamilyStore cfs : concatWithIndexes())
                {
                    Memtable mt = cfs.getMemtableThreadSafe();
                    if (!mt.isClean())
                        mt.cfs.data.renewMemtable();
                }
            } finally
            {
                Keyspace.switchLock.writeLock().unlock();
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
                for (RowCacheKey key : CacheService.instance.rowCache.getKeySet())
                {
                    if (key.cfId == metadata.cfId)
                        invalidateCachedRow(key);
                }
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
                Function<ColumnFamilyStore, CFMetaData> f = new Function<ColumnFamilyStore, CFMetaData>()
                {
                    public CFMetaData apply(ColumnFamilyStore cfs)
                    {
                        return cfs.metadata;
                    }
                };
                Iterable<CFMetaData> allMetadata = Iterables.transform(selfWithIndexes, f);
                CompactionManager.instance.interruptCompactionFor(allMetadata, interruptValidation);

                // wait for the interruption to be recognized
                long start = System.nanoTime();
                long delay = TimeUnit.MINUTES.toNanos(1);
                while (System.nanoTime() - start < delay)
                {
                    if (CompactionManager.instance.isCompacting(selfWithIndexes))
                        Uninterruptibles.sleepUninterruptibly(100, TimeUnit.MILLISECONDS);
                    else
                        break;
                }

                // doublecheck that we finished, instead of timing out
                for (ColumnFamilyStore cfs : selfWithIndexes)
                {
                    if (!cfs.getDataTracker().getCompacting().isEmpty())
                    {
                        logger.warn("Unable to cancel in-progress compactions for {}.  Probably there is an unusually large row in progress somewhere.  It is also possible that buggy code left some sstables compacting after it was done with them", metadata.cfName);
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
                Iterable<SSTableReader> sstables = Lists.newArrayList(AbstractCompactionStrategy.filterSuspectSSTables(getSSTables()));
                if (Iterables.isEmpty(sstables))
                    return null;
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
        this.compactionStrategy.disable();
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
        this.compactionStrategy.enable();
        List<Future<?>> futures = CompactionManager.instance.submitBackground(this);
        if (waitForFutures)
            FBUtilities.waitOnFutures(futures);
    }

    public boolean isAutoCompactionDisabled()
    {
        return !this.compactionStrategy.isEnabled();
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
        assert compactionStrategy != null : "No compaction strategy set yet";
        return compactionStrategy;
    }

    public void setCompactionThresholds(int minThreshold, int maxThreshold)
    {
        validateCompactionThresholds(minThreshold, maxThreshold);

        minCompactionThreshold.set(minThreshold);
        maxCompactionThreshold.set(maxThreshold);

        // this is called as part of CompactionStrategy constructor; avoid circular dependency by checking for null
        if (compactionStrategy != null)
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

    private ByteBuffer intern(ByteBuffer name)
    {
        ByteBuffer internedName = internedNames.get(name);
        if (internedName == null)
        {
            internedName = ByteBufferUtil.clone(name);
            ByteBuffer concurrentName = internedNames.putIfAbsent(internedName, internedName);
            if (concurrentName != null)
                internedName = concurrentName;
        }
        return internedName;
    }

    public ByteBuffer internOrCopy(ByteBuffer name, Allocator allocator)
    {
        if (internedNames.size() >= INTERN_CUTOFF)
            return allocator.clone(name);

        return intern(name);
    }

    public ByteBuffer maybeIntern(ByteBuffer name)
    {
        if (internedNames.size() >= INTERN_CUTOFF)
            return null;

        return intern(name);
    }

    public Iterable<ColumnFamilyStore> concatWithIndexes()
    {
        return Iterables.concat(indexManager.getIndexesBackedByCfs(), Collections.singleton(this));
    }

    public Set<Memtable> getMemtablesPendingFlush()
    {
        return data.getMemtablesPendingFlush();
    }

    public List<String> getBuiltIndexes()
    {
       return indexManager.getBuiltIndexes();
    }

    public int getUnleveledSSTables()
    {
        return this.compactionStrategy instanceof LeveledCompactionStrategy
               ? ((LeveledCompactionStrategy) this.compactionStrategy).getLevelSize(0)
               : 0;
    }

    public int[] getSSTableCountPerLevel()
    {
        return compactionStrategy instanceof LeveledCompactionStrategy
               ? ((LeveledCompactionStrategy) compactionStrategy).getAllLevelSize()
               : null;
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

    /**
     * Returns the creation time of the oldest memtable not fully flushed yet.
     */
    public long oldestUnflushedMemtable()
    {
        DataTracker.View view = data.getView();
        long oldest = view.memtable.creationTime();
        for (Memtable memtable : view.memtablesPendingFlush)
            oldest = Math.min(oldest, memtable.creationTime());
        return oldest;
    }

    public boolean isEmpty()
    {
        DataTracker.View view = data.getView();
        return view.sstables.isEmpty() && view.memtable.getOperations() == 0 && view.memtablesPendingFlush.isEmpty();
    }

    private boolean isRowCacheEnabled()
    {
        return !(metadata.getCaching() == Caching.NONE
              || metadata.getCaching() == Caching.KEYS_ONLY
              || CacheService.instance.rowCache.getCapacity() == 0);
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

    @VisibleForTesting
    void resetFileIndexGenerator()
    {
        fileIndexGenerator.set(0);
    }
}


File: src/java/org/apache/cassandra/db/compaction/CompactionManager.java
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
package org.apache.cassandra.db.compaction;

import java.io.File;
import java.io.IOException;
import java.lang.management.ManagementFactory;
import java.util.*;
import java.util.concurrent.*;
import javax.management.MBeanServer;
import javax.management.ObjectName;
import javax.management.openmbean.OpenDataException;
import javax.management.openmbean.TabularData;

import com.google.common.base.Throwables;
import com.google.common.collect.*;
import com.google.common.util.concurrent.RateLimiter;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import org.apache.cassandra.cache.AutoSavingCache;
import org.apache.cassandra.concurrent.DebuggableThreadPoolExecutor;
import org.apache.cassandra.concurrent.JMXEnabledThreadPoolExecutor;
import org.apache.cassandra.concurrent.NamedThreadFactory;
import org.apache.cassandra.config.CFMetaData;
import org.apache.cassandra.config.DatabaseDescriptor;
import org.apache.cassandra.config.Schema;
import org.apache.cassandra.db.*;
import org.apache.cassandra.db.compaction.CompactionInfo.Holder;
import org.apache.cassandra.db.index.SecondaryIndexBuilder;
import org.apache.cassandra.dht.Bounds;
import org.apache.cassandra.dht.Range;
import org.apache.cassandra.dht.Token;
import org.apache.cassandra.io.sstable.*;
import org.apache.cassandra.io.util.FileUtils;
import org.apache.cassandra.metrics.CompactionMetrics;
import org.apache.cassandra.repair.Validator;
import org.apache.cassandra.service.StorageService;
import org.apache.cassandra.utils.*;

/**
 * A singleton which manages a private executor of ongoing compactions.
 * <p/>
 * Scheduling for compaction is accomplished by swapping sstables to be compacted into
 * a set via DataTracker. New scheduling attempts will ignore currently compacting
 * sstables.
 */
public class CompactionManager implements CompactionManagerMBean
{
    public static final String MBEAN_OBJECT_NAME = "org.apache.cassandra.db:type=CompactionManager";
    private static final Logger logger = LoggerFactory.getLogger(CompactionManager.class);
    public static final CompactionManager instance;

    public static final int NO_GC = Integer.MIN_VALUE;
    public static final int GC_ALL = Integer.MAX_VALUE;

    // A thread local that tells us if the current thread is owned by the compaction manager. Used
    // by CounterContext to figure out if it should log a warning for invalid counter shards.
    public static final ThreadLocal<Boolean> isCompactionManager = new ThreadLocal<Boolean>()
    {
        @Override
        protected Boolean initialValue()
        {
            return false;
        }
    };

    static
    {
        instance = new CompactionManager();
        MBeanServer mbs = ManagementFactory.getPlatformMBeanServer();
        try
        {
            mbs.registerMBean(instance, new ObjectName(MBEAN_OBJECT_NAME));
        }
        catch (Exception e)
        {
            throw new RuntimeException(e);
        }
    }

    private final CompactionExecutor executor = new CompactionExecutor();
    private final CompactionExecutor validationExecutor = new ValidationExecutor();
    private final static CompactionExecutor cacheCleanupExecutor = new CacheCleanupExecutor();

    private final CompactionMetrics metrics = new CompactionMetrics(executor, validationExecutor);
    private final Multiset<ColumnFamilyStore> compactingCF = ConcurrentHashMultiset.create();

    private final RateLimiter compactionRateLimiter = RateLimiter.create(Double.MAX_VALUE);

    /**
     * Gets compaction rate limiter. When compaction_throughput_mb_per_sec is 0 or node is bootstrapping,
     * this returns rate limiter with the rate of Double.MAX_VALUE bytes per second.
     * Rate unit is bytes per sec.
     *
     * @return RateLimiter with rate limit set
     */
    public RateLimiter getRateLimiter()
    {
        double currentThroughput = DatabaseDescriptor.getCompactionThroughputMbPerSec() * 1024.0 * 1024.0;
        // if throughput is set to 0, throttling is disabled
        if (currentThroughput == 0 || StorageService.instance.isBootstrapMode())
            currentThroughput = Double.MAX_VALUE;
        if (compactionRateLimiter.getRate() != currentThroughput)
            compactionRateLimiter.setRate(currentThroughput);
        return compactionRateLimiter;
    }

    /**
     * Call this whenever a compaction might be needed on the given columnfamily.
     * It's okay to over-call (within reason) if a call is unnecessary, it will
     * turn into a no-op in the bucketing/candidate-scan phase.
     */
    public List<Future<?>> submitBackground(final ColumnFamilyStore cfs)
    {
        return submitBackground(cfs, true);
    }

    public List<Future<?>> submitBackground(final ColumnFamilyStore cfs, boolean autoFill)
    {
        if (cfs.isAutoCompactionDisabled())
        {
            logger.debug("Autocompaction is disabled");
            return Collections.emptyList();
        }

        int count = compactingCF.count(cfs);
        if (count > 0 && executor.getActiveCount() >= executor.getMaximumPoolSize())
        {
            logger.debug("Background compaction is still running for {}.{} ({} remaining). Skipping",
                         cfs.keyspace.getName(), cfs.name, count);
            return Collections.emptyList();
        }

        logger.debug("Scheduling a background task check for {}.{} with {}",
                     cfs.keyspace.getName(),
                     cfs.name,
                     cfs.getCompactionStrategy().getClass().getSimpleName());
        List<Future<?>> futures = new ArrayList<Future<?>>();

        // we must schedule it at least once, otherwise compaction will stop for a CF until next flush
        do {
            compactingCF.add(cfs);
            futures.add(executor.submit(new BackgroundCompactionTask(cfs)));
            // if we have room for more compactions, then fill up executor
        } while (autoFill && executor.getActiveCount() + futures.size() < executor.getMaximumPoolSize());

        return futures;
    }

    public boolean isCompacting(Iterable<ColumnFamilyStore> cfses)
    {
        for (ColumnFamilyStore cfs : cfses)
            if (!cfs.getDataTracker().getCompacting().isEmpty())
                return true;
        return false;
    }

    // the actual sstables to compact are not determined until we run the BCT; that way, if new sstables
    // are created between task submission and execution, we execute against the most up-to-date information
    class BackgroundCompactionTask implements Runnable
    {
        private final ColumnFamilyStore cfs;

        BackgroundCompactionTask(ColumnFamilyStore cfs)
        {
            this.cfs = cfs;
        }

        public void run()
        {
            try
            {
                logger.debug("Checking {}.{}", cfs.keyspace.getName(), cfs.name);
                if (!cfs.isValid())
                {
                    logger.debug("Aborting compaction for dropped CF");
                    return;
                }

                AbstractCompactionStrategy strategy = cfs.getCompactionStrategy();
                AbstractCompactionTask task = strategy.getNextBackgroundTask(getDefaultGcBefore(cfs));
                if (task == null)
                {
                    logger.debug("No tasks available");
                    return;
                }
                task.execute(metrics);
            }
            finally
            {
                compactingCF.remove(cfs);
            }
            submitBackground(cfs);
        }
    }

    private static interface AllSSTablesOperation
    {
        public void perform(ColumnFamilyStore store, Iterable<SSTableReader> sstables) throws IOException;
    }

    private void performAllSSTableOperation(final ColumnFamilyStore cfs, final AllSSTablesOperation operation) throws InterruptedException, ExecutionException
    {
        final Iterable<SSTableReader> sstables = cfs.markAllCompacting();
        if (sstables == null)
            return;

        Callable<Object> runnable = new Callable<Object>()
        {
            public Object call() throws IOException
            {
                try
                {
                    operation.perform(cfs, sstables);
                }
                finally
                {
                    cfs.getDataTracker().unmarkCompacting(sstables);
                }
                return this;
            }
        };
        executor.submit(runnable).get();
    }

    public void performScrub(ColumnFamilyStore cfStore, final boolean skipCorrupted, final boolean checkData) throws InterruptedException, ExecutionException
    {
        performAllSSTableOperation(cfStore, new AllSSTablesOperation()
        {
            public void perform(ColumnFamilyStore store, Iterable<SSTableReader> sstables) throws IOException
            {
                doScrub(store, sstables, skipCorrupted, checkData);
            }
        });
    }

    public void performSSTableRewrite(ColumnFamilyStore cfStore, final boolean excludeCurrentVersion) throws InterruptedException, ExecutionException
    {
        performAllSSTableOperation(cfStore, new AllSSTablesOperation()
        {
            public void perform(ColumnFamilyStore cfs, Iterable<SSTableReader> sstables)
            {
                for (final SSTableReader sstable : sstables)
                {
                    if (excludeCurrentVersion && sstable.descriptor.version.equals(Descriptor.Version.CURRENT))
                        continue;

                    // SSTables are marked by the caller
                    // NOTE: it is important that the task create one and only one sstable, even for Leveled compaction (see LeveledManifest.replace())
                    AbstractCompactionTask task = cfs.getCompactionStrategy().getCompactionTask(Collections.singleton(sstable), NO_GC, Long.MAX_VALUE);
                    task.setUserDefined(true);
                    task.setCompactionType(OperationType.UPGRADE_SSTABLES);
                    task.execute(metrics);
                }
            }
        });
    }

    public void performCleanup(ColumnFamilyStore cfStore, final CounterId.OneShotRenewer renewer) throws InterruptedException, ExecutionException
    {
        performAllSSTableOperation(cfStore, new AllSSTablesOperation()
        {
            public void perform(ColumnFamilyStore store, Iterable<SSTableReader> sstables) throws IOException
            {
                // Sort the column families in order of SSTable size, so cleanup of smaller CFs
                // can free up space for larger ones
                List<SSTableReader> sortedSSTables = Lists.newArrayList(sstables);
                Collections.sort(sortedSSTables, new SSTableReader.SizeComparator());

                doCleanupCompaction(store, sortedSSTables, renewer);
            }
        });
    }

    public void performMaximal(final ColumnFamilyStore cfStore) throws InterruptedException, ExecutionException
    {
        submitMaximal(cfStore, getDefaultGcBefore(cfStore)).get();
    }

    public Future<?> submitMaximal(final ColumnFamilyStore cfStore, final int gcBefore)
    {
        // here we compute the task off the compaction executor, so having that present doesn't
        // confuse runWithCompactionsDisabled -- i.e., we don't want to deadlock ourselves, waiting
        // for ourselves to finish/acknowledge cancellation before continuing.
        final AbstractCompactionTask task = cfStore.getCompactionStrategy().getMaximalTask(gcBefore);
        Runnable runnable = new WrappedRunnable()
        {
            protected void runMayThrow() throws IOException
            {
                if (task == null)
                    return;
                task.execute(metrics);
            }
        };
        return executor.submit(runnable);
    }

    public void forceUserDefinedCompaction(String dataFiles)
    {
        String[] filenames = dataFiles.split(",");
        Multimap<Pair<String, String>, Descriptor> descriptors = ArrayListMultimap.create();

        for (String filename : filenames)
        {
            // extract keyspace and columnfamily name from filename
            Descriptor desc = Descriptor.fromFilename(filename.trim());
            if (Schema.instance.getCFMetaData(desc) == null)
            {
                logger.warn("Schema does not exist for file {}. Skipping.", filename);
                continue;
            }
            File directory = new File(desc.ksname + File.separator + desc.cfname);
            // group by keyspace/columnfamily
            Pair<Descriptor, String> p = Descriptor.fromFilename(directory, filename.trim());
            Pair<String, String> key = Pair.create(p.left.ksname, p.left.cfname);
            descriptors.put(key, p.left);
        }

        List<Future<?>> futures = new ArrayList<>();
        for (Pair<String, String> key : descriptors.keySet())
        {
            ColumnFamilyStore cfs = Keyspace.open(key.left).getColumnFamilyStore(key.right);
            futures.add(submitUserDefined(cfs, descriptors.get(key), getDefaultGcBefore(cfs)));
        }
        FBUtilities.waitOnFutures(futures);
    }

    public Future<?> submitUserDefined(final ColumnFamilyStore cfs, final Collection<Descriptor> dataFiles, final int gcBefore)
    {
        Runnable runnable = new WrappedRunnable()
        {
            protected void runMayThrow() throws IOException
            {
                // look up the sstables now that we're on the compaction executor, so we don't try to re-compact
                // something that was already being compacted earlier.
                Collection<SSTableReader> sstables = new ArrayList<SSTableReader>(dataFiles.size());
                for (Descriptor desc : dataFiles)
                {
                    // inefficient but not in a performance sensitive path
                    SSTableReader sstable = lookupSSTable(cfs, desc);
                    if (sstable == null)
                    {
                        logger.info("Will not compact {}: it is not an active sstable", desc);
                    }
                    else
                    {
                        sstables.add(sstable);
                    }
                }

                if (sstables.isEmpty())
                {
                    logger.info("No files to compact for user defined compaction");
                }
                else
                {
                    AbstractCompactionTask task = cfs.getCompactionStrategy().getUserDefinedTask(sstables, gcBefore);
                    if (task != null)
                        task.execute(metrics);
                }
            }
        };
        return executor.submit(runnable);
    }

    // This acquire a reference on the sstable
    // This is not efficent, do not use in any critical path
    private SSTableReader lookupSSTable(final ColumnFamilyStore cfs, Descriptor descriptor)
    {
        for (SSTableReader sstable : cfs.getSSTables())
        {
            // .equals() with no other changes won't work because in sstable.descriptor, the directory is an absolute path.
            // We could construct descriptor with an absolute path too but I haven't found any satisfying way to do that
            // (DB.getDataFileLocationForTable() may not return the right path if you have multiple volumes). Hence the
            // endsWith.
            if (sstable.descriptor.toString().endsWith(descriptor.toString()))
                return sstable;
        }
        return null;
    }

    /**
     * Does not mutate data, so is not scheduled.
     */
    public Future<Object> submitValidation(final ColumnFamilyStore cfStore, final Validator validator)
    {
        Callable<Object> callable = new Callable<Object>()
        {
            public Object call() throws IOException
            {
                try
                {
                    doValidationCompaction(cfStore, validator);
                }
                catch (Throwable e)
                {
                    // we need to inform the remote end of our failure, otherwise it will hang on repair forever
                    validator.fail();
                    throw e;
                }
                return this;
            }
        };
        return validationExecutor.submit(callable);
    }

    /* Used in tests. */
    public void disableAutoCompaction()
    {
        for (String ksname : Schema.instance.getNonSystemKeyspaces())
        {
            for (ColumnFamilyStore cfs : Keyspace.open(ksname).getColumnFamilyStores())
                cfs.disableAutoCompaction();
        }
    }

    /**
     * Deserialize everything in the CFS and re-serialize w/ the newest version.  Also attempts to recover
     * from bogus row keys / sizes using data from the index, and skips rows with garbage columns that resulted
     * from early ByteBuffer bugs.
     *
     * @throws IOException
     */
    private void doScrub(ColumnFamilyStore cfs, Iterable<SSTableReader> sstables, boolean skipCorrupted, boolean checkData) throws IOException
    {
        assert !cfs.isIndex();
        for (final SSTableReader sstable : sstables)
            scrubOne(cfs, sstable, skipCorrupted, checkData);
    }

    private void scrubOne(ColumnFamilyStore cfs, SSTableReader sstable, boolean skipCorrupted, boolean checkData) throws IOException
    {
        Scrubber scrubber = new Scrubber(cfs, sstable, skipCorrupted, checkData);

        CompactionInfo.Holder scrubInfo = scrubber.getScrubInfo();
        metrics.beginCompaction(scrubInfo);
        try
        {
            scrubber.scrub();
        }
        finally
        {
            scrubber.close();
            metrics.finishCompaction(scrubInfo);
        }

        if (scrubber.getNewInOrderSSTable() != null)
            cfs.addSSTable(scrubber.getNewInOrderSSTable());

        if (scrubber.getNewSSTable() == null)
            cfs.markObsolete(Collections.singletonList(sstable), OperationType.SCRUB);
        else
            cfs.replaceCompactedSSTables(Collections.singletonList(sstable), Collections.singletonList(scrubber.getNewSSTable()), OperationType.SCRUB);
    }

    /**
     * Determines if a cleanup would actually remove any data in this SSTable based
     * on a set of owned ranges.
     */
    static boolean needsCleanup(SSTableReader sstable, Collection<Range<Token>> ownedRanges)
    {
        assert !ownedRanges.isEmpty(); // cleanup checks for this

        // unwrap and sort the ranges by LHS token
        List<Range<Token>> sortedRanges = Range.normalize(ownedRanges);

        // see if there are any keys LTE the token for the start of the first range
        // (token range ownership is exclusive on the LHS.)
        Range<Token> firstRange = sortedRanges.get(0);
        if (sstable.first.token.compareTo(firstRange.left) <= 0)
            return true;

        // then, iterate over all owned ranges and see if the next key beyond the end of the owned
        // range falls before the start of the next range
        for (int i = 0; i < sortedRanges.size(); i++)
        {
            Range<Token> range = sortedRanges.get(i);
            if (range.right.isMinimum())
            {
                // we split a wrapping range and this is the second half.
                // there can't be any keys beyond this (and this is the last range)
                return false;
            }

            DecoratedKey firstBeyondRange = sstable.firstKeyBeyond(range.right.maxKeyBound());
            if (firstBeyondRange == null)
            {
                // we ran off the end of the sstable looking for the next key; we don't need to check any more ranges
                return false;
            }

            if (i == (sortedRanges.size() - 1))
            {
                // we're at the last range and we found a key beyond the end of the range
                return true;
            }

            Range<Token> nextRange = sortedRanges.get(i + 1);
            if (!nextRange.contains(firstBeyondRange.token))
            {
                // we found a key in between the owned ranges
                return true;
            }
        }

        return false;
    }

    /**
     * This function goes over each file and removes the keys that the node is not responsible for
     * and only keeps keys that this node is responsible for.
     *
     * @throws IOException
     */
    private void doCleanupCompaction(final ColumnFamilyStore cfs, Collection<SSTableReader> sstables, CounterId.OneShotRenewer renewer) throws IOException
    {
        assert !cfs.isIndex();
        Keyspace keyspace = cfs.keyspace;
        Collection<Range<Token>> ranges = StorageService.instance.getLocalRanges(keyspace.getName());
        if (ranges.isEmpty())
        {
            logger.info("Cleanup cannot run before a node has joined the ring");
            return;
        }

        boolean hasIndexes = cfs.indexManager.hasIndexes();
        CleanupStrategy cleanupStrategy = CleanupStrategy.get(cfs, ranges, renewer);

        for (SSTableReader sstable : sstables)
        {
            Set<SSTableReader> sstableAsSet = Collections.singleton(sstable);
            if (!hasIndexes && !new Bounds<Token>(sstable.first.token, sstable.last.token).intersects(ranges))
            {
                cfs.replaceCompactedSSTables(sstableAsSet, Collections.<SSTableReader>emptyList(), OperationType.CLEANUP);
                continue;
            }
            if (!needsCleanup(sstable, ranges))
            {
                logger.debug("Skipping {} for cleanup; all rows should be kept", sstable);
                continue;
            }

            CompactionController controller = new CompactionController(cfs, sstableAsSet, getDefaultGcBefore(cfs));
            long start = System.nanoTime();

            long totalkeysWritten = 0;

            int expectedBloomFilterSize = Math.max(cfs.metadata.getIndexInterval(),
                                                   (int) (SSTableReader.getApproximateKeyCount(sstableAsSet, cfs.metadata)));
            if (logger.isDebugEnabled())
                logger.debug("Expected bloom filter size : " + expectedBloomFilterSize);

            logger.info("Cleaning up " + sstable);
            File compactionFileLocation = cfs.directories.getWriteableLocationAsFile(cfs.getExpectedCompactedFileSize(sstableAsSet, OperationType.CLEANUP));
            if (compactionFileLocation == null)
                throw new IOException("disk full");

            ICompactionScanner scanner = cleanupStrategy.getScanner(sstable, getRateLimiter());
            CleanupInfo ci = new CleanupInfo(sstable, scanner);

            metrics.beginCompaction(ci);
            SSTableWriter writer = createWriter(cfs,
                                                compactionFileLocation,
                                                expectedBloomFilterSize,
                                                sstable);
            SSTableReader newSstable = null;
            try
            {
                while (scanner.hasNext())
                {
                    if (ci.isStopRequested())
                        throw new CompactionInterruptedException(ci.getCompactionInfo());
                    SSTableIdentityIterator row = (SSTableIdentityIterator) scanner.next();

                    row = cleanupStrategy.cleanup(row);
                    if (row == null)
                        continue;
                    AbstractCompactedRow compactedRow = controller.getCompactedRow(row);
                    if (writer.append(compactedRow) != null)
                        totalkeysWritten++;
                }
                if (totalkeysWritten > 0)
                    newSstable = writer.closeAndOpenReader(sstable.maxDataAge);
                else
                    writer.abort();
            }
            catch (Throwable e)
            {
                writer.abort();
                throw Throwables.propagate(e);
            }
            finally
            {
                controller.close();
                scanner.close();
                metrics.finishCompaction(ci);
            }

            List<SSTableReader> results = new ArrayList<SSTableReader>(1);
            if (newSstable != null)
            {
                results.add(newSstable);

                String format = "Cleaned up to %s.  %,d to %,d (~%d%% of original) bytes for %,d keys.  Time: %,dms.";
                long dTime = TimeUnit.NANOSECONDS.toMillis(System.nanoTime() - start);
                long startsize = sstable.onDiskLength();
                long endsize = newSstable.onDiskLength();
                double ratio = (double) endsize / (double) startsize;
                logger.info(String.format(format, writer.getFilename(), startsize, endsize, (int) (ratio * 100), totalkeysWritten, dTime));
            }

            // flush to ensure we don't lose the tombstones on a restart, since they are not commitlog'd
            cfs.indexManager.flushIndexesBlocking();

            cfs.replaceCompactedSSTables(Arrays.asList(sstable), results, OperationType.CLEANUP);
        }
    }

    private static abstract class CleanupStrategy
    {
        public static CleanupStrategy get(ColumnFamilyStore cfs, Collection<Range<Token>> ranges, CounterId.OneShotRenewer renewer)
        {
            if (cfs.indexManager.hasIndexes() || cfs.metadata.getDefaultValidator().isCommutative())
                return new Full(cfs, ranges, renewer);

            return new Bounded(cfs, ranges);
        }

        public abstract ICompactionScanner getScanner(SSTableReader sstable, RateLimiter limiter);
        public abstract SSTableIdentityIterator cleanup(SSTableIdentityIterator row);

        private static final class Bounded extends CleanupStrategy
        {
            private final Collection<Range<Token>> ranges;

            public Bounded(final ColumnFamilyStore cfs, Collection<Range<Token>> ranges)
            {
                this.ranges = ranges;
                cacheCleanupExecutor.submit(new Runnable()
                {
                    @Override
                    public void run()
                    {
                        cfs.cleanupCache();
                    }
                });

            }
            @Override
            public ICompactionScanner getScanner(SSTableReader sstable, RateLimiter limiter)
            {
                return sstable.getScanner(ranges, limiter);
            }

            @Override
            public SSTableIdentityIterator cleanup(SSTableIdentityIterator row)
            {
                return row;
            }
        }

        private static final class Full extends CleanupStrategy
        {
            private final Collection<Range<Token>> ranges;
            private final ColumnFamilyStore cfs;
            private List<Column> indexedColumnsInRow;
            private final CounterId.OneShotRenewer renewer;

            public Full(ColumnFamilyStore cfs, Collection<Range<Token>> ranges, CounterId.OneShotRenewer renewer)
            {
                this.cfs = cfs;
                this.ranges = ranges;
                this.indexedColumnsInRow = null;
                this.renewer = renewer;
            }

            @Override
            public ICompactionScanner getScanner(SSTableReader sstable, RateLimiter limiter)
            {
                return sstable.getScanner(limiter);
            }

            @Override
            public SSTableIdentityIterator cleanup(SSTableIdentityIterator row)
            {
                if (Range.isInRanges(row.getKey().token, ranges))
                    return row;

                cfs.invalidateCachedRow(row.getKey());

                if (indexedColumnsInRow != null)
                    indexedColumnsInRow.clear();

                while (row.hasNext())
                {
                    OnDiskAtom column = row.next();
                    if (column instanceof CounterColumn)
                        renewer.maybeRenew((CounterColumn) column);

                    if (column instanceof Column && cfs.indexManager.indexes((Column) column))
                    {
                        if (indexedColumnsInRow == null)
                            indexedColumnsInRow = new ArrayList<>();

                        indexedColumnsInRow.add((Column) column);
                    }
                }

                if (indexedColumnsInRow != null && !indexedColumnsInRow.isEmpty())
                {
                    // acquire memtable lock here because secondary index deletion may cause a race. See CASSANDRA-3712
                    Keyspace.switchLock.readLock().lock();
                    try
                    {
                        cfs.indexManager.deleteFromIndexes(row.getKey(), indexedColumnsInRow);
                    }
                    finally
                    {
                        Keyspace.switchLock.readLock().unlock();
                    }
                }
                return null;
            }
        }
    }

    public static SSTableWriter createWriter(ColumnFamilyStore cfs,
                                             File compactionFileLocation,
                                             int expectedBloomFilterSize,
                                             SSTableReader sstable)
    {
        FileUtils.createDirectory(compactionFileLocation);
        return new SSTableWriter(cfs.getTempSSTablePath(compactionFileLocation),
                                 expectedBloomFilterSize,
                                 cfs.metadata,
                                 cfs.partitioner,
                                 SSTableMetadata.createCollector(Collections.singleton(sstable), cfs.metadata.comparator, sstable.getSSTableLevel()));
    }

    /**
     * Performs a readonly "compaction" of all sstables in order to validate complete rows,
     * but without writing the merge result
     */
    private void doValidationCompaction(ColumnFamilyStore cfs, Validator validator) throws IOException
    {
        // this isn't meant to be race-proof, because it's not -- it won't cause bugs for a CFS to be dropped
        // mid-validation, or to attempt to validate a droped CFS.  this is just a best effort to avoid useless work,
        // particularly in the scenario where a validation is submitted before the drop, and there are compactions
        // started prior to the drop keeping some sstables alive.  Since validationCompaction can run
        // concurrently with other compactions, it would otherwise go ahead and scan those again.
        if (!cfs.isValid())
            return;

        Collection<SSTableReader> sstables;
        String snapshotName = validator.desc.sessionId.toString();
        int gcBefore;
        boolean isSnapshotValidation = cfs.snapshotExists(snapshotName);
        if (isSnapshotValidation)
        {
            // If there is a snapshot created for the session then read from there.
            sstables = cfs.getSnapshotSSTableReader(snapshotName);

            // Computing gcbefore based on the current time wouldn't be very good because we know each replica will execute
            // this at a different time (that's the whole purpose of repair with snapshot). So instead we take the creation
            // time of the snapshot, which should give us roughly the same time on each replica (roughly being in that case
            // 'as good as in the non-snapshot' case)
            gcBefore = cfs.gcBefore(cfs.getSnapshotCreationTime(snapshotName));
        }
        else
        {
            // flush first so everyone is validating data that is as similar as possible
            StorageService.instance.forceKeyspaceFlush(cfs.keyspace.getName(), cfs.name);

            // we don't mark validating sstables as compacting in DataTracker, so we have to mark them referenced
            // instead so they won't be cleaned up if they do get compacted during the validation
            sstables = cfs.markCurrentSSTablesReferenced();
            if (validator.gcBefore > 0)
                gcBefore = validator.gcBefore;
            else
                gcBefore = getDefaultGcBefore(cfs);
        }

        CompactionIterable ci = new ValidationCompactionIterable(cfs, sstables, validator.desc.range, gcBefore);
        CloseableIterator<AbstractCompactedRow> iter = ci.iterator();
        metrics.beginCompaction(ci);
        try
        {
            // validate the CF as we iterate over it
            validator.prepare(cfs);
            while (iter.hasNext())
            {
                if (ci.isStopRequested())
                    throw new CompactionInterruptedException(ci.getCompactionInfo());
                AbstractCompactedRow row = iter.next();
                validator.add(row);
            }
            validator.complete();
        }
        finally
        {
            iter.close();
            SSTableReader.releaseReferences(sstables);
            if (isSnapshotValidation)
            {
                cfs.clearSnapshot(snapshotName);
            }

            metrics.finishCompaction(ci);
        }
    }

    /**
     * Is not scheduled, because it is performing disjoint work from sstable compaction.
     */
    public Future<?> submitIndexBuild(final SecondaryIndexBuilder builder)
    {
        Runnable runnable = new Runnable()
        {
            public void run()
            {
                metrics.beginCompaction(builder);
                try
                {
                    builder.build();
                }
                finally
                {
                    metrics.finishCompaction(builder);
                }
            }
        };

        return executor.submit(runnable);
    }

    public Future<?> submitCacheWrite(final AutoSavingCache.Writer writer)
    {
        Runnable runnable = new Runnable()
        {
            public void run()
            {
                if (!AutoSavingCache.flushInProgress.add(writer.cacheType()))
                {
                    logger.debug("Cache flushing was already in progress: skipping {}", writer.getCompactionInfo());
                    return;
                }
                try
                {
                    metrics.beginCompaction(writer);
                    try
                    {
                        writer.saveCache();
                    }
                    finally
                    {
                        metrics.finishCompaction(writer);
                    }
                }
                finally
                {
                    AutoSavingCache.flushInProgress.remove(writer.cacheType());
                }
            }
        };
        return executor.submit(runnable);
    }

    static int getDefaultGcBefore(ColumnFamilyStore cfs)
    {
        // 2ndary indexes have ExpiringColumns too, so we need to purge tombstones deleted before now. We do not need to
        // add any GcGrace however since 2ndary indexes are local to a node.
        return cfs.isIndex() ? (int) (System.currentTimeMillis() / 1000) : cfs.gcBefore(System.currentTimeMillis());
    }

    private static class ValidationCompactionIterable extends CompactionIterable
    {
        public ValidationCompactionIterable(ColumnFamilyStore cfs, Collection<SSTableReader> sstables, Range<Token> range, int gcBefore)
        {
            super(OperationType.VALIDATION,
                  cfs.getCompactionStrategy().getScanners(sstables, range),
                  new ValidationCompactionController(cfs, gcBefore));
        }
    }

    /*
     * Controller for validation compaction that always purges.
     * Note that we should not call cfs.getOverlappingSSTables on the provided
     * sstables because those sstables are not guaranteed to be active sstables
     * (since we can run repair on a snapshot).
     */
    private static class ValidationCompactionController extends CompactionController
    {
        public ValidationCompactionController(ColumnFamilyStore cfs, int gcBefore)
        {
            super(cfs, gcBefore);
        }

        @Override
        public boolean shouldPurge(DecoratedKey key, long delTimestamp)
        {
            /*
             * The main reason we always purge is that including gcable tombstone would mean that the
             * repair digest will depends on the scheduling of compaction on the different nodes. This
             * is still not perfect because gcbefore is currently dependend on the current time at which
             * the validation compaction start, which while not too bad for normal repair is broken for
             * repair on snapshots. A better solution would be to agree on a gcbefore that all node would
             * use, and we'll do that with CASSANDRA-4932.
             * Note validation compaction includes all sstables, so we don't have the problem of purging
             * a tombstone that could shadow a column in another sstable, but this is doubly not a concern
             * since validation compaction is read-only.
             */
            return true;
        }
    }

    public int getActiveCompactions()
    {
        return CompactionMetrics.getCompactions().size();
    }

    private static class CompactionExecutor extends JMXEnabledThreadPoolExecutor
    {
        protected CompactionExecutor(int minThreads, int maxThreads, String name, BlockingQueue<Runnable> queue)
        {
            super(minThreads, maxThreads, 60, TimeUnit.SECONDS, queue, new NamedThreadFactory(name, Thread.MIN_PRIORITY), "internal");
        }

        private CompactionExecutor(int threadCount, String name)
        {
            this(threadCount, threadCount, name, new LinkedBlockingQueue<Runnable>());
        }

        public CompactionExecutor()
        {
            this(Math.max(1, DatabaseDescriptor.getConcurrentCompactors()), "CompactionExecutor");
        }

        protected void beforeExecute(Thread t, Runnable r)
        {
            // can't set this in Thread factory, so we do it redundantly here
            isCompactionManager.set(true);
            super.beforeExecute(t, r);
        }

        // modified from DebuggableThreadPoolExecutor so that CompactionInterruptedExceptions are not logged
        @Override
        public void afterExecute(Runnable r, Throwable t)
        {
            DebuggableThreadPoolExecutor.maybeResetTraceSessionWrapper(r);

            if (t == null)
                t = DebuggableThreadPoolExecutor.extractThrowable(r);

            if (t != null)
            {
                if (t instanceof CompactionInterruptedException)
                {
                    logger.info(t.getMessage());
                    logger.debug("Full interruption stack trace:", t);
                }
                else
                {
                    DebuggableThreadPoolExecutor.handleOrLog(t);
                }
            }
        }
    }

    private static class ValidationExecutor extends CompactionExecutor
    {
        public ValidationExecutor()
        {
            super(1, Integer.MAX_VALUE, "ValidationExecutor", new SynchronousQueue<Runnable>());
        }
    }

    private static class CacheCleanupExecutor extends CompactionExecutor
    {
        public CacheCleanupExecutor()
        {
            super(1, "CacheCleanupExecutor");
        }
    }

    public interface CompactionExecutorStatsCollector
    {
        void beginCompaction(CompactionInfo.Holder ci);

        void finishCompaction(CompactionInfo.Holder ci);
    }

    public List<Map<String, String>> getCompactions()
    {
        List<Holder> compactionHolders = CompactionMetrics.getCompactions();
        List<Map<String, String>> out = new ArrayList<Map<String, String>>(compactionHolders.size());
        for (CompactionInfo.Holder ci : compactionHolders)
            out.add(ci.getCompactionInfo().asMap());
        return out;
    }

    public List<String> getCompactionSummary()
    {
        List<Holder> compactionHolders = CompactionMetrics.getCompactions();
        List<String> out = new ArrayList<String>(compactionHolders.size());
        for (CompactionInfo.Holder ci : compactionHolders)
            out.add(ci.getCompactionInfo().toString());
        return out;
    }

    public TabularData getCompactionHistory()
    {
        try
        {
            return SystemKeyspace.getCompactionHistory();
        }
        catch (OpenDataException e)
        {
            throw new RuntimeException(e);
        }
    }

    public long getTotalBytesCompacted()
    {
        return metrics.bytesCompacted.count();
    }

    public long getTotalCompactionsCompleted()
    {
        return metrics.totalCompactionsCompleted.count();
    }

    public int getPendingTasks()
    {
        return metrics.pendingTasks.value();
    }

    public long getCompletedTasks()
    {
        return metrics.completedTasks.value();
    }

    private static class CleanupInfo extends CompactionInfo.Holder
    {
        private final SSTableReader sstable;
        private final ICompactionScanner scanner;

        public CleanupInfo(SSTableReader sstable, ICompactionScanner scanner)
        {
            this.sstable = sstable;
            this.scanner = scanner;
        }

        public CompactionInfo getCompactionInfo()
        {
            try
            {
                return new CompactionInfo(sstable.metadata,
                                          OperationType.CLEANUP,
                                          scanner.getCurrentPosition(),
                                          scanner.getLengthInBytes());
            }
            catch (Exception e)
            {
                throw new RuntimeException();
            }
        }
    }

    public void stopCompaction(String type)
    {
        OperationType operation = OperationType.valueOf(type);
        for (Holder holder : CompactionMetrics.getCompactions())
        {
            if (holder.getCompactionInfo().getTaskType() == operation)
                holder.stop();
        }
    }

    public int getCoreCompactorThreads()
    {
        return executor.getCorePoolSize();
    }

    public void setCoreCompactorThreads(int number)
    {
        executor.setCorePoolSize(number);
    }

    public int getMaximumCompactorThreads()
    {
        return executor.getMaximumPoolSize();
    }

    public void setMaximumCompactorThreads(int number)
    {
        executor.setMaximumPoolSize(number);
    }

    public int getCoreValidationThreads()
    {
        return validationExecutor.getCorePoolSize();
    }

    public void setCoreValidationThreads(int number)
    {
        validationExecutor.setCorePoolSize(number);
    }

    public int getMaximumValidatorThreads()
    {
        return validationExecutor.getMaximumPoolSize();
    }

    public void setMaximumValidatorThreads(int number)
    {
        validationExecutor.setMaximumPoolSize(number);
    }

    /**
     * Try to stop all of the compactions for given ColumnFamilies.
     *
     * Note that this method does not wait for all compactions to finish; you'll need to loop against
     * isCompacting if you want that behavior.
     *
     * @param columnFamilies The ColumnFamilies to try to stop compaction upon.
     * @param interruptValidation true if validation operations for repair should also be interrupted
     *
     */
    public void interruptCompactionFor(Iterable<CFMetaData> columnFamilies, boolean interruptValidation)
    {
        assert columnFamilies != null;

        // interrupt in-progress compactions
        for (Holder compactionHolder : CompactionMetrics.getCompactions())
        {
            CompactionInfo info = compactionHolder.getCompactionInfo();
            if ((info.getTaskType() == OperationType.VALIDATION) && !interruptValidation)
                continue;

            if (Iterables.contains(columnFamilies, info.getCFMetaData()))
                compactionHolder.stop(); // signal compaction to stop
        }
    }
}


File: src/java/org/apache/cassandra/metrics/CompactionMetrics.java
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
package org.apache.cassandra.metrics;

import java.util.*;
import java.util.concurrent.ThreadPoolExecutor;
import java.util.concurrent.TimeUnit;

import com.yammer.metrics.Metrics;
import com.yammer.metrics.core.Counter;
import com.yammer.metrics.core.Gauge;
import com.yammer.metrics.core.Meter;

import org.apache.cassandra.config.Schema;
import org.apache.cassandra.db.ColumnFamilyStore;
import org.apache.cassandra.db.Keyspace;
import org.apache.cassandra.db.compaction.CompactionInfo;
import org.apache.cassandra.db.compaction.CompactionManager;

/**
 * Metrics for compaction.
 */
public class CompactionMetrics implements CompactionManager.CompactionExecutorStatsCollector
{
    public static final MetricNameFactory factory = new DefaultNameFactory("Compaction");

    // a synchronized identity set of running tasks to their compaction info
    private static final Set<CompactionInfo.Holder> compactions = Collections.synchronizedSet(Collections.newSetFromMap(new IdentityHashMap<CompactionInfo.Holder, Boolean>()));

    /** Estimated number of compactions remaining to perform */
    public final Gauge<Integer> pendingTasks;
    /** Number of completed compactions since server [re]start */
    public final Gauge<Long> completedTasks;
    /** Total number of compactions since server [re]start */
    public final Meter totalCompactionsCompleted;
    /** Total number of bytes compacted since server [re]start */
    public final Counter bytesCompacted;

    public CompactionMetrics(final ThreadPoolExecutor... collectors)
    {
        pendingTasks = Metrics.newGauge(factory.createMetricName("PendingTasks"), new Gauge<Integer>()
        {
            public Integer value()
            {
                int n = 0;
                for (String keyspaceName : Schema.instance.getKeyspaces())
                {
                    for (ColumnFamilyStore cfs : Keyspace.open(keyspaceName).getColumnFamilyStores())
                        n += cfs.getCompactionStrategy().getEstimatedRemainingTasks();
                }
                for (ThreadPoolExecutor collector : collectors)
                    n += collector.getTaskCount() - collector.getCompletedTaskCount();
                return n;
            }
        });
        completedTasks = Metrics.newGauge(factory.createMetricName("CompletedTasks"), new Gauge<Long>()
        {
            public Long value()
            {
                long completedTasks = 0;
                for (ThreadPoolExecutor collector : collectors)
                    completedTasks += collector.getCompletedTaskCount();
                return completedTasks;
            }
        });
        totalCompactionsCompleted = Metrics.newMeter(factory.createMetricName("TotalCompactionsCompleted"), "compaction completed", TimeUnit.SECONDS);
        bytesCompacted = Metrics.newCounter(factory.createMetricName("BytesCompacted"));
    }

    public void beginCompaction(CompactionInfo.Holder ci)
    {
        // notify
        ci.started();
        compactions.add(ci);
    }

    public void finishCompaction(CompactionInfo.Holder ci)
    {
        // notify
        ci.finished();
        compactions.remove(ci);
        bytesCompacted.inc(ci.getCompactionInfo().getTotal());
        totalCompactionsCompleted.mark();
    }

    public static List<CompactionInfo.Holder> getCompactions()
    {
        return new ArrayList<CompactionInfo.Holder>(compactions);
    }
}


File: test/unit/org/apache/cassandra/db/compaction/CompactionsTest.java
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
package org.apache.cassandra.db.compaction;

import java.io.*;
import java.nio.ByteBuffer;
import java.util.*;
import java.util.concurrent.ExecutionException;
import java.util.concurrent.TimeUnit;

import com.google.common.base.Function;
import com.google.common.collect.Iterables;
import com.google.common.collect.Sets;

import org.junit.Test;
import org.junit.runner.RunWith;
import org.apache.cassandra.OrderedJUnit4ClassRunner;
import org.apache.cassandra.SchemaLoader;
import org.apache.cassandra.Util;
import org.apache.cassandra.config.CFMetaData;
import org.apache.cassandra.config.DatabaseDescriptor;
import org.apache.cassandra.db.*;
import org.apache.cassandra.db.columniterator.OnDiskAtomIterator;
import org.apache.cassandra.db.filter.QueryFilter;
import org.apache.cassandra.db.marshal.CompositeType;
import org.apache.cassandra.dht.BytesToken;
import org.apache.cassandra.dht.Range;
import org.apache.cassandra.dht.Token;
import org.apache.cassandra.io.sstable.Component;
import org.apache.cassandra.io.sstable.SSTableMetadata;
import org.apache.cassandra.io.sstable.SSTableReader;
import org.apache.cassandra.io.sstable.SSTableScanner;
import org.apache.cassandra.io.sstable.SSTableWriter;
import org.apache.cassandra.service.StorageService;
import org.apache.cassandra.utils.ByteBufferUtil;
import org.apache.cassandra.utils.FBUtilities;
import org.apache.cassandra.utils.Pair;

import static org.junit.Assert.*;

@RunWith(OrderedJUnit4ClassRunner.class)
public class CompactionsTest extends SchemaLoader
{
    private static final String STANDARD1 = "Standard1";
    public static final String KEYSPACE1 = "Keyspace1";

    public ColumnFamilyStore testSingleSSTableCompaction(String strategyClassName) throws Exception
    {
        Keyspace keyspace = Keyspace.open(KEYSPACE1);
        ColumnFamilyStore store = keyspace.getColumnFamilyStore(STANDARD1);
        store.clearUnsafe();
        store.metadata.gcGraceSeconds(1);
        store.setCompactionStrategyClass(strategyClassName);

        // disable compaction while flushing
        store.disableAutoCompaction();

        long timestamp = populate(KEYSPACE1, STANDARD1, 0, 9, 3); //ttl=3s
        store.forceBlockingFlush();
        assertEquals(1, store.getSSTables().size());
        long originalSize = store.getSSTables().iterator().next().uncompressedLength();

        // wait enough to force single compaction
        TimeUnit.SECONDS.sleep(5);

        // enable compaction, submit background and wait for it to complete
        store.enableAutoCompaction();
        FBUtilities.waitOnFutures(CompactionManager.instance.submitBackground(store));
        while (CompactionManager.instance.getPendingTasks() > 0 || CompactionManager.instance.getActiveCompactions() > 0)
            TimeUnit.SECONDS.sleep(1);

        // and sstable with ttl should be compacted
        assertEquals(1, store.getSSTables().size());
        long size = store.getSSTables().iterator().next().uncompressedLength();
        assertTrue("should be less than " + originalSize + ", but was " + size, size < originalSize);

        // make sure max timestamp of compacted sstables is recorded properly after compaction.
        assertMaxTimestamp(store, timestamp);

        return store;
    }

    private long populate(String ks, String cf, int startRowKey, int endRowKey, int ttl) {
        long timestamp = System.currentTimeMillis();
        for (int i = startRowKey; i <= endRowKey; i++)
        {
            DecoratedKey key = Util.dk(Integer.toString(i));
            RowMutation rm = new RowMutation(ks, key.key);
            for (int j = 0; j < 10; j++)
                rm.add(cf, ByteBufferUtil.bytes(Integer.toString(j)),
                       ByteBufferUtil.EMPTY_BYTE_BUFFER,
                       timestamp,
                       j > 0 ? ttl : 0); // let first column never expire, since deleting all columns does not produce sstable
            rm.apply();
        }
        return timestamp;
    }

    /**
     * Test to see if sstable has enough expired columns, it is compacted itself.
     */
    @Test
    public void testSingleSSTableCompactionWithSizeTieredCompaction() throws Exception
    {
        testSingleSSTableCompaction(SizeTieredCompactionStrategy.class.getCanonicalName());
    }

    @Test
    public void testSingleSSTableCompactionWithLeveledCompaction() throws Exception
    {
        ColumnFamilyStore store = testSingleSSTableCompaction(LeveledCompactionStrategy.class.getCanonicalName());
        LeveledCompactionStrategy strategy = (LeveledCompactionStrategy) store.getCompactionStrategy();
        // tombstone removal compaction should not promote level
        assert strategy.getLevelSize(0) == 1;
    }

    @Test
    public void testSuperColumnTombstones() throws IOException, ExecutionException, InterruptedException
    {
        Keyspace keyspace = Keyspace.open(KEYSPACE1);
        ColumnFamilyStore cfs = keyspace.getColumnFamilyStore("Super1");
        cfs.disableAutoCompaction();

        DecoratedKey key = Util.dk("tskey");
        ByteBuffer scName = ByteBufferUtil.bytes("TestSuperColumn");

        // a subcolumn
        RowMutation rm = new RowMutation(KEYSPACE1, key.key);
        rm.add("Super1", CompositeType.build(scName, ByteBufferUtil.bytes(0)),
               ByteBufferUtil.EMPTY_BYTE_BUFFER,
               FBUtilities.timestampMicros());
        rm.apply();
        cfs.forceBlockingFlush();

        // shadow the subcolumn with a supercolumn tombstone
        rm = new RowMutation(KEYSPACE1, key.key);
        rm.deleteRange("Super1", SuperColumns.startOf(scName), SuperColumns.endOf(scName), FBUtilities.timestampMicros());
        rm.apply();
        cfs.forceBlockingFlush();

        CompactionManager.instance.performMaximal(cfs);
        assertEquals(1, cfs.getSSTables().size());

        // check that the shadowed column is gone
        SSTableReader sstable = cfs.getSSTables().iterator().next();
        Range keyRange = new Range<RowPosition>(key, sstable.partitioner.getMinimumToken().maxKeyBound());
        SSTableScanner scanner = sstable.getScanner(DataRange.forKeyRange(keyRange));
        OnDiskAtomIterator iter = scanner.next();
        assertEquals(key, iter.getKey());
        assert iter.next() instanceof RangeTombstone;
        assert !iter.hasNext();
    }

    @Test
    public void testUncheckedTombstoneSizeTieredCompaction() throws Exception
    {
        Keyspace keyspace = Keyspace.open(KEYSPACE1);
        ColumnFamilyStore store = keyspace.getColumnFamilyStore(STANDARD1);
        store.clearUnsafe();
        store.metadata.gcGraceSeconds(1);
        store.metadata.compactionStrategyOptions.put("tombstone_compaction_interval", "1");
        store.metadata.compactionStrategyOptions.put("unchecked_tombstone_compaction", "false");
        store.reload();
        store.setCompactionStrategyClass(SizeTieredCompactionStrategy.class.getName());

        // disable compaction while flushing
        store.disableAutoCompaction();

        //Populate sstable1 with with keys [0..9]
        populate(KEYSPACE1, STANDARD1, 0, 9, 3); //ttl=3s
        store.forceBlockingFlush();

        //Populate sstable2 with with keys [10..19] (keys do not overlap with SSTable1)
        long timestamp2 = populate(KEYSPACE1, STANDARD1, 10, 19, 3); //ttl=3s
        store.forceBlockingFlush();

        assertEquals(2, store.getSSTables().size());

        Iterator<SSTableReader> it = store.getSSTables().iterator();
        long originalSize1 = it.next().uncompressedLength();
        long originalSize2 = it.next().uncompressedLength();

        // wait enough to force single compaction
        TimeUnit.SECONDS.sleep(5);

        // enable compaction, submit background and wait for it to complete
        store.enableAutoCompaction();
        FBUtilities.waitOnFutures(CompactionManager.instance.submitBackground(store));
        while (CompactionManager.instance.getPendingTasks() > 0 || CompactionManager.instance.getActiveCompactions() > 0)
            TimeUnit.SECONDS.sleep(1);

        // even though both sstables were candidate for tombstone compaction
        // it was not executed because they have an overlapping token range
        assertEquals(2, store.getSSTables().size());
        it = store.getSSTables().iterator();
        long newSize1 = it.next().uncompressedLength();
        long newSize2 = it.next().uncompressedLength();
        assertEquals("candidate sstable should not be tombstone-compacted because its key range overlap with other sstable",
                      originalSize1, newSize1);
        assertEquals("candidate sstable should not be tombstone-compacted because its key range overlap with other sstable",
                      originalSize2, newSize2);

        // now let's enable the magic property
        store.metadata.compactionStrategyOptions.put("unchecked_tombstone_compaction", "true");
        store.reload();

        //submit background task again and wait for it to complete
        FBUtilities.waitOnFutures(CompactionManager.instance.submitBackground(store));
        while (CompactionManager.instance.getPendingTasks() > 0 || CompactionManager.instance.getActiveCompactions() > 0)
            TimeUnit.SECONDS.sleep(1);

        //we still have 2 sstables, since they were not compacted against each other
        assertEquals(2, store.getSSTables().size());
        it = store.getSSTables().iterator();
        newSize1 = it.next().uncompressedLength();
        newSize2 = it.next().uncompressedLength();
        assertTrue("should be less than " + originalSize1 + ", but was " + newSize1, newSize1 < originalSize1);
        assertTrue("should be less than " + originalSize2 + ", but was " + newSize2, newSize2 < originalSize2);

        // make sure max timestamp of compacted sstables is recorded properly after compaction.
        assertMaxTimestamp(store, timestamp2);
    }

    public static void assertMaxTimestamp(ColumnFamilyStore cfs, long maxTimestampExpected)
    {
        long maxTimestampObserved = Long.MIN_VALUE;
        for (SSTableReader sstable : cfs.getSSTables())
            maxTimestampObserved = Math.max(sstable.getMaxTimestamp(), maxTimestampObserved);
        assertEquals(maxTimestampExpected, maxTimestampObserved);
    }

    @Test
    public void testEchoedRow() throws IOException, ExecutionException, InterruptedException
    {
        // This test check that EchoedRow doesn't skipp rows: see CASSANDRA-2653

        Keyspace keyspace = Keyspace.open(KEYSPACE1);
        ColumnFamilyStore cfs = keyspace.getColumnFamilyStore("Standard2");

        // disable compaction while flushing
        cfs.disableAutoCompaction();

        // Insert 4 keys in two sstables. We need the sstables to have 2 rows
        // at least to trigger what was causing CASSANDRA-2653
        for (int i=1; i < 5; i++)
        {
            DecoratedKey key = Util.dk(String.valueOf(i));
            RowMutation rm = new RowMutation(KEYSPACE1, key.key);
            rm.add("Standard2", ByteBufferUtil.bytes(String.valueOf(i)), ByteBufferUtil.EMPTY_BYTE_BUFFER, i);
            rm.apply();

            if (i % 2 == 0)
                cfs.forceBlockingFlush();
        }
        Collection<SSTableReader> toCompact = cfs.getSSTables();
        assert toCompact.size() == 2;

        // Reinserting the same keys. We will compact only the previous sstable, but we need those new ones
        // to make sure we use EchoedRow, otherwise it won't be used because purge can be done.
        for (int i=1; i < 5; i++)
        {
            DecoratedKey key = Util.dk(String.valueOf(i));
            RowMutation rm = new RowMutation(KEYSPACE1, key.key);
            rm.add("Standard2", ByteBufferUtil.bytes(String.valueOf(i)), ByteBufferUtil.EMPTY_BYTE_BUFFER, i);
            rm.apply();
        }
        cfs.forceBlockingFlush();
        SSTableReader tmpSSTable = null;
        for (SSTableReader sstable : cfs.getSSTables())
            if (!toCompact.contains(sstable))
                tmpSSTable = sstable;
        assert tmpSSTable != null;

        // Force compaction on first sstables. Since each row is in only one sstable, we will be using EchoedRow.
        Util.compact(cfs, toCompact);
        assertEquals(2, cfs.getSSTables().size());

        // Now, we remove the sstable that was just created to force the use of EchoedRow (so that it doesn't hide the problem)
        cfs.markObsolete(Collections.singleton(tmpSSTable), OperationType.UNKNOWN);
        assertEquals(1, cfs.getSSTables().size());

        // Now assert we do have the 4 keys
        assertEquals(4, Util.getRangeSlice(cfs).size());
    }

    @Test
    public void testDontPurgeAccidentaly() throws IOException, ExecutionException, InterruptedException
    {
        testDontPurgeAccidentaly("test1", "Super5");

        // Use CF with gc_grace=0, see last bug of CASSANDRA-2786
        testDontPurgeAccidentaly("test1", "SuperDirectGC");
    }

    @Test
    public void testUserDefinedCompaction() throws Exception
    {
        Keyspace keyspace = Keyspace.open(KEYSPACE1);
        final String cfname = "Standard3"; // use clean(no sstable) CF
        ColumnFamilyStore cfs = keyspace.getColumnFamilyStore(cfname);

        // disable compaction while flushing
        cfs.disableAutoCompaction();

        final int ROWS_PER_SSTABLE = 10;
        for (int i = 0; i < ROWS_PER_SSTABLE; i++) {
            DecoratedKey key = Util.dk(String.valueOf(i));
            RowMutation rm = new RowMutation(KEYSPACE1, key.key);
            rm.add(cfname, ByteBufferUtil.bytes("col"),
                   ByteBufferUtil.EMPTY_BYTE_BUFFER,
                   System.currentTimeMillis());
            rm.apply();
        }
        cfs.forceBlockingFlush();
        Collection<SSTableReader> sstables = cfs.getSSTables();

        assert sstables.size() == 1;
        SSTableReader sstable = sstables.iterator().next();

        int prevGeneration = sstable.descriptor.generation;
        String file = new File(sstable.descriptor.filenameFor(Component.DATA)).getName();
        // submit user defined compaction on flushed sstable
        CompactionManager.instance.forceUserDefinedCompaction(file);
        // wait until user defined compaction finishes
        do
        {
            Thread.sleep(100);
        } while (CompactionManager.instance.getPendingTasks() > 0 || CompactionManager.instance.getActiveCompactions() > 0);
        // CF should have only one sstable with generation number advanced
        sstables = cfs.getSSTables();
        assert sstables.size() == 1;
        assert sstables.iterator().next().descriptor.generation == prevGeneration + 1;
    }

    @Test
    public void testRangeTombstones() throws IOException, ExecutionException, InterruptedException
    {
        boolean lazy = false;

        do
        {
            Keyspace keyspace = Keyspace.open(KEYSPACE1);
            ColumnFamilyStore cfs = keyspace.getColumnFamilyStore("Standard2");
            cfs.clearUnsafe();

            // disable compaction while flushing
            cfs.disableAutoCompaction();

            final CFMetaData cfmeta = cfs.metadata;
            Directories dir = Directories.create(cfmeta.ksName, cfmeta.cfName);

            ArrayList<DecoratedKey> keys = new ArrayList<DecoratedKey>();

            for (int i=0; i < 4; i++)
            {
                keys.add(Util.dk(""+i));
            }

            ArrayBackedSortedColumns cf = ArrayBackedSortedColumns.factory.create(cfmeta);
            cf.addColumn(Util.column("01", "a", 1)); // this must not resurrect
            cf.addColumn(Util.column("a", "a", 3));
            cf.deletionInfo().add(new RangeTombstone(ByteBufferUtil.bytes("0"), ByteBufferUtil.bytes("b"), 2, (int) (System.currentTimeMillis()/1000)),cfmeta.comparator);

            SSTableWriter writer = new SSTableWriter(cfs.getTempSSTablePath(dir.getDirectoryForNewSSTables()),
                                                     0,
                                                     cfs.metadata,
                                                     StorageService.getPartitioner(),
                                                     SSTableMetadata.createCollector(cfs.metadata.comparator));


            writer.append(Util.dk("0"), cf);
            writer.append(Util.dk("1"), cf);
            writer.append(Util.dk("3"), cf);

            cfs.addSSTable(writer.closeAndOpenReader());
            writer = new SSTableWriter(cfs.getTempSSTablePath(dir.getDirectoryForNewSSTables()),
                                       0,
                                       cfs.metadata,
                                       StorageService.getPartitioner(),
                                       SSTableMetadata.createCollector(cfs.metadata.comparator));

            writer.append(Util.dk("0"), cf);
            writer.append(Util.dk("1"), cf);
            writer.append(Util.dk("2"), cf);
            writer.append(Util.dk("3"), cf);
            cfs.addSSTable(writer.closeAndOpenReader());

            Collection<SSTableReader> toCompact = cfs.getSSTables();
            assert toCompact.size() == 2;

            // forcing lazy comapction
            if (lazy)
                DatabaseDescriptor.setInMemoryCompactionLimit(0);

            // Force compaction on first sstables. Since each row is in only one sstable, we will be using EchoedRow.
            Util.compact(cfs, toCompact);
            assertEquals(1, cfs.getSSTables().size());

            // Now assert we do have the 4 keys
            assertEquals(4, Util.getRangeSlice(cfs).size());

            ArrayList<DecoratedKey> k = new ArrayList<DecoratedKey>();
            for (Row r : Util.getRangeSlice(cfs))
            {
                k.add(r.key);
                assertEquals(ByteBufferUtil.bytes("a"),r.cf.getColumn(ByteBufferUtil.bytes("a")).value());
                assertNull(r.cf.getColumn(ByteBufferUtil.bytes("01")));
                assertEquals(3,r.cf.getColumn(ByteBufferUtil.bytes("a")).timestamp());
            }

            for (SSTableReader sstable : cfs.getSSTables())
            {
                SSTableMetadata stats = sstable.getSSTableMetadata();
                assertEquals(ByteBufferUtil.bytes("0"), stats.minColumnNames.get(0));
                assertEquals(ByteBufferUtil.bytes("b"), stats.maxColumnNames.get(0));
            }

            assertEquals(keys, k);

            lazy=!lazy;
        }
        while (lazy);
    }

    @Test
    public void testCompactionLog() throws Exception
    {
        SystemKeyspace.discardCompactionsInProgress();

        String cf = "Standard4";
        ColumnFamilyStore cfs = Keyspace.open(KEYSPACE1).getColumnFamilyStore(cf);
        insertData(KEYSPACE1, cf, 0, 1);
        cfs.forceBlockingFlush();

        Collection<SSTableReader> sstables = cfs.getSSTables();
        assert !sstables.isEmpty();
        Set<Integer> generations = Sets.newHashSet(Iterables.transform(sstables, new Function<SSTableReader, Integer>()
        {
            public Integer apply(SSTableReader sstable)
            {
                return sstable.descriptor.generation;
            }
        }));
        UUID taskId = SystemKeyspace.startCompaction(cfs, sstables);
        Map<Pair<String, String>, Map<Integer, UUID>> compactionLogs = SystemKeyspace.getUnfinishedCompactions();
        Set<Integer> unfinishedCompactions = compactionLogs.get(Pair.create(KEYSPACE1, cf)).keySet();
        assert unfinishedCompactions.containsAll(generations);

        SystemKeyspace.finishCompaction(taskId);
        compactionLogs = SystemKeyspace.getUnfinishedCompactions();
        assert !compactionLogs.containsKey(Pair.create(KEYSPACE1, cf));
    }

    private void testDontPurgeAccidentaly(String k, String cfname) throws IOException, ExecutionException, InterruptedException
    {
        // This test catches the regression of CASSANDRA-2786
        Keyspace keyspace = Keyspace.open(KEYSPACE1);
        ColumnFamilyStore cfs = keyspace.getColumnFamilyStore(cfname);

        // disable compaction while flushing
        cfs.clearUnsafe();
        cfs.disableAutoCompaction();

        // Add test row
        DecoratedKey key = Util.dk(k);
        RowMutation rm = new RowMutation(KEYSPACE1, key.key);
        rm.add(cfname, CompositeType.build(ByteBufferUtil.bytes("sc"), ByteBufferUtil.bytes("c")), ByteBufferUtil.EMPTY_BYTE_BUFFER, 0);
        rm.apply();

        cfs.forceBlockingFlush();

        Collection<SSTableReader> sstablesBefore = cfs.getSSTables();

        QueryFilter filter = QueryFilter.getIdentityFilter(key, cfname, System.currentTimeMillis());
        assert !(cfs.getColumnFamily(filter).getColumnCount() == 0);

        // Remove key
        rm = new RowMutation(KEYSPACE1, key.key);
        rm.delete(cfname, 2);
        rm.apply();

        ColumnFamily cf = cfs.getColumnFamily(filter);
        assert cf == null || cf.getColumnCount() == 0 : "should be empty: " + cf;

        // Sleep one second so that the removal is indeed purgeable even with gcgrace == 0
        Thread.sleep(1000);

        cfs.forceBlockingFlush();

        Collection<SSTableReader> sstablesAfter = cfs.getSSTables();
        Collection<SSTableReader> toCompact = new ArrayList<SSTableReader>();
        for (SSTableReader sstable : sstablesAfter)
            if (!sstablesBefore.contains(sstable))
                toCompact.add(sstable);

        Util.compact(cfs, toCompact);

        cf = cfs.getColumnFamily(filter);
        assert cf == null || cf.getColumnCount() == 0 : "should be empty: " + cf;
    }

    private static Range<Token> rangeFor(int start, int end)
    {
        return new Range<Token>(new BytesToken(String.format("%03d", start).getBytes()),
                                new BytesToken(String.format("%03d", end).getBytes()));
    }

    private static Collection<Range<Token>> makeRanges(int ... keys)
    {
        Collection<Range<Token>> ranges = new ArrayList<Range<Token>>(keys.length / 2);
        for (int i = 0; i < keys.length; i += 2)
            ranges.add(rangeFor(keys[i], keys[i + 1]));
        return ranges;
    }

    private static void insertRowWithKey(int key)
    {
        long timestamp = System.currentTimeMillis();
        DecoratedKey decoratedKey = Util.dk(String.format("%03d", key));
        RowMutation rm = new RowMutation(KEYSPACE1, decoratedKey.key);
        rm.add("Standard1", ByteBufferUtil.bytes("col"), ByteBufferUtil.EMPTY_BYTE_BUFFER, timestamp, 1000);
        rm.apply();
    }

    @Test
    public void testNeedsCleanup() throws IOException
    {
        Keyspace keyspace = Keyspace.open(KEYSPACE1);
        ColumnFamilyStore store = keyspace.getColumnFamilyStore("Standard1");
        store.clearUnsafe();

        // disable compaction while flushing
        store.disableAutoCompaction();

        // write three groups of 9 keys: 001, 002, ... 008, 009
        //                               101, 102, ... 108, 109
        //                               201, 202, ... 208, 209
        for (int i = 1; i < 10; i++)
        {
            insertRowWithKey(i);
            insertRowWithKey(i + 100);
            insertRowWithKey(i + 200);
        }
        store.forceBlockingFlush();

        assertEquals(1, store.getSSTables().size());
        SSTableReader sstable = store.getSSTables().iterator().next();


        // contiguous range spans all data
        assertFalse(CompactionManager.needsCleanup(sstable, makeRanges(0, 209)));
        assertFalse(CompactionManager.needsCleanup(sstable, makeRanges(0, 210)));

        // separate ranges span all data
        assertFalse(CompactionManager.needsCleanup(sstable, makeRanges(0, 9,
                                                                       100, 109,
                                                                       200, 209)));
        assertFalse(CompactionManager.needsCleanup(sstable, makeRanges(0, 109,
                                                                       200, 210)));
        assertFalse(CompactionManager.needsCleanup(sstable, makeRanges(0, 9,
                                                                       100, 210)));

        // one range is missing completely
        assertTrue(CompactionManager.needsCleanup(sstable, makeRanges(100, 109,
                                                                      200, 209)));
        assertTrue(CompactionManager.needsCleanup(sstable, makeRanges(0, 9,
                                                                      200, 209)));
        assertTrue(CompactionManager.needsCleanup(sstable, makeRanges(0, 9,
                                                                      100, 109)));


        // the beginning of one range is missing
        assertTrue(CompactionManager.needsCleanup(sstable, makeRanges(1, 9,
                                                                      100, 109,
                                                                      200, 209)));
        assertTrue(CompactionManager.needsCleanup(sstable, makeRanges(0, 9,
                                                                      101, 109,
                                                                      200, 209)));
        assertTrue(CompactionManager.needsCleanup(sstable, makeRanges(0, 9,
                                                                      100, 109,
                                                                      201, 209)));

        // the end of one range is missing
        assertTrue(CompactionManager.needsCleanup(sstable, makeRanges(0, 8,
                                                                      100, 109,
                                                                      200, 209)));
        assertTrue(CompactionManager.needsCleanup(sstable, makeRanges(0, 9,
                                                                      100, 108,
                                                                      200, 209)));
        assertTrue(CompactionManager.needsCleanup(sstable, makeRanges(0, 9,
                                                                      100, 109,
                                                                      200, 208)));

        // some ranges don't contain any data
        assertFalse(CompactionManager.needsCleanup(sstable, makeRanges(0, 0,
                                                                       0, 9,
                                                                       50, 51,
                                                                       100, 109,
                                                                       150, 199,
                                                                       200, 209,
                                                                       300, 301)));
        // same case, but with a middle range not covering some of the existing data
        assertFalse(CompactionManager.needsCleanup(sstable, makeRanges(0, 0,
                                                                       0, 9,
                                                                       50, 51,
                                                                       100, 103,
                                                                       150, 199,
                                                                       200, 209,
                                                                       300, 301)));
    }
}
