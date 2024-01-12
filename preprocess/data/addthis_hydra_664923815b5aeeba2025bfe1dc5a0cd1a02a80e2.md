Refactoring Types: ['Extract Method']
ddthis/hydra/data/tree/DataTreeNode.java
/*
 * Licensed under the Apache License, Version 2.0 (the "License");
 * you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at
 *
 * http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 */
package com.addthis.hydra.data.tree;

import java.util.Map;

import com.addthis.basis.util.ClosableIterator;

import com.fasterxml.jackson.annotation.JsonAutoDetect;


@JsonAutoDetect(getterVisibility = JsonAutoDetect.Visibility.NONE,
                isGetterVisibility = JsonAutoDetect.Visibility.NONE,
                setterVisibility = JsonAutoDetect.Visibility.NONE)
public interface DataTreeNode extends Iterable<DataTreeNode> {

    /** Returns the name of this node. This node can be found by querying for this against its parent node. */
    public String getName();

    /** Returns the tree that this node belongs to. */
    public DataTree getTreeRoot();

    /** Returns the number of child nodes. */
    public int getNodeCount();

    /** Returns the number of "hits". "Hits" are increments to the node's intrinsic counter. */
    public long getCounter();

    /** Returns data attachment (if any) with the given name. */
    public DataTreeNodeActor getData(String key);

    /** Return node if it exists. Does not create otherwise. returned node is read only -- do not call release(). */
    public DataTreeNode getNode(String name);

    /** Returns the map of data attachments. */
    public Map<String, TreeNodeData> getDataMap();

    /** Returns an iterator of all child nodes. */
    public ClosableIterator<DataTreeNode> getIterator();

    /** Returns an iterator over the set of child nodes with the matching prefix. */
    public ClosableIterator<DataTreeNode> getIterator(String prefix);

    /** Returns an iterator over child nodes whose names are in the range [from, to).
     * The 'from' is inclusive and the 'to' is exclusive. */
    public ClosableIterator<DataTreeNode> getIterator(String from, String to);

    // Mutation Methods

    /** atomically increment intrinsic counter */
    public default void incrementCounter() {
        throw new UnsupportedOperationException("incrementCounter");
    }

    /** atomically increment intrinsic counter and return new value */
    public default long incrementCounter(long val) {
        throw new UnsupportedOperationException("incrementCounter");
    }

    /** set value of intrinsic counter */
    public default void setCounter(long val) {
        throw new UnsupportedOperationException("setCounter");
    }

    /**
     * TODO for immediate compatibility -- rethink this
     */
    public default void updateChildData(DataTreeNodeUpdater state, TreeDataParent path) {
        throw new UnsupportedOperationException("updateChildData");
    }

    /**
     * TODO for immediate compatibility -- rethink this
     */
    public default void updateParentData(DataTreeNodeUpdater state, DataTreeNode child, boolean isnew) {
        throw new UnsupportedOperationException("updateParentData");
    }

    /** Make this node an alias (link) to another node. This can succeed only if this node currently has no children. */
    public default boolean aliasTo(DataTreeNode target) {
        throw new UnsupportedOperationException("aliasTo");
    }

    /** Attempts to delete named child node. Returns true if node existed and was successfully deleted. */
    public default boolean deleteNode(String node) {
        throw new UnsupportedOperationException("deleteNode");
    }

    // Leasing / Locking methods

    /**
     * return node if it exists, create and return new otherwise.
     * returned node is read/write.  MUST call release() when complete to commit changes OR discard.
     */
    public default DataTreeNode getOrCreateNode(String name, DataTreeNodeInitializer init) {
        throw new UnsupportedOperationException("getOrCreateNode");
    }

    /**
     * return node if it exists, do not create otherwise.
     * returned node is mutable.  MUST call release().
     */
    public default DataTreeNode getLeasedNode(String name) {
        throw new UnsupportedOperationException("getLeasedNode");
    }

    /** TODO temporary workaround.  MUST call ONLY for nodes retrieved via getOrCreateNode(). */
    public default void release() {
        throw new UnsupportedOperationException("release");
    }

    public default void writeLock() {
        throw new UnsupportedOperationException("writeLock");
    }

    public default void writeUnlock() {
        throw new UnsupportedOperationException("writeUnlock");
    }
}


File: hydra-data/src/main/java/com/addthis/hydra/data/tree/concurrent/ConcurrentTree.java
/*
 * Licensed under the Apache License, Version 2.0 (the "License");
 * you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at
 *
 * http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 */
package com.addthis.hydra.data.tree.concurrent;

import javax.annotation.concurrent.GuardedBy;

import java.io.File;
import java.io.IOException;
import java.io.UnsupportedEncodingException;

import java.util.Arrays;
import java.util.Iterator;
import java.util.Map;
import java.util.concurrent.ConcurrentMap;
import java.util.concurrent.Executors;
import java.util.concurrent.ScheduledExecutorService;
import java.util.concurrent.TimeUnit;
import java.util.concurrent.atomic.AtomicBoolean;
import java.util.concurrent.atomic.AtomicInteger;
import java.util.concurrent.atomic.AtomicLong;
import java.util.function.BooleanSupplier;

import com.addthis.basis.concurrentlinkedhashmap.MediatedEvictionConcurrentHashMap;
import com.addthis.basis.util.LessBytes;
import com.addthis.basis.util.ClosableIterator;
import com.addthis.basis.util.LessFiles;
import com.addthis.basis.util.Meter;
import com.addthis.basis.util.Parameter;

import com.addthis.hydra.common.Configuration;
import com.addthis.hydra.data.tree.DataTree;
import com.addthis.hydra.data.tree.DataTreeNode;
import com.addthis.hydra.data.tree.DataTreeNodeActor;
import com.addthis.hydra.data.tree.DataTreeNodeInitializer;
import com.addthis.hydra.data.tree.DataTreeNodeUpdater;
import com.addthis.hydra.data.tree.TreeDataParent;
import com.addthis.hydra.data.tree.TreeNodeData;
import com.addthis.hydra.store.db.CloseOperation;
import com.addthis.hydra.store.db.DBKey;
import com.addthis.hydra.store.db.IPageDB;
import com.addthis.hydra.store.db.PageDB;
import com.addthis.hydra.store.kv.PagedKeyValueStore;
import com.addthis.hydra.store.skiplist.Page;
import com.addthis.hydra.store.skiplist.PageFactory;
import com.addthis.hydra.store.skiplist.SkipListCache;
import com.addthis.hydra.store.util.MeterFileLogger;
import com.addthis.hydra.store.util.MeterFileLogger.MeterDataSource;
import com.addthis.hydra.store.util.NamedThreadFactory;
import com.addthis.hydra.store.util.Raw;

import com.google.common.annotations.VisibleForTesting;
import com.google.common.util.concurrent.AtomicDouble;

import com.yammer.metrics.Metrics;
import com.yammer.metrics.core.Gauge;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

/**
 * @user-reference
 */
public final class ConcurrentTree implements DataTree, MeterDataSource {
    static final Logger log = LoggerFactory.getLogger(ConcurrentTree.class);

    // number of background deletion threads
    @Configuration.Parameter
    static final int defaultNumDeletionThreads = Parameter.intValue("hydra.tree.clean.threads", 1);

    // sleep interval of deletion threads in between polls of deletion queue
    @Configuration.Parameter
    static final int deletionThreadSleepMillis = Parameter.intValue("hydra.tree.clean.interval", 10);

    // number of nodes in between trash removal logging messages
    @Configuration.Parameter
    static final int deletionLogInterval = Parameter.intValue("hydra.tree.clean.logging", 100000);

    private static final AtomicInteger scopeGenerator = new AtomicInteger();

    private final String scope = "ConcurrentTree" + Integer.toString(scopeGenerator.getAndIncrement());

    public static enum METERTREE {
        CACHE_HIT, CACHE_MISS, NODE_PUT, NODE_CREATE, NODE_DELETE, SOURCE_MISS
    }

    static final String keyCacheGet = METERTREE.CACHE_HIT.toString();
    static final String keyCacheMiss = METERTREE.CACHE_MISS.toString();

    private final File root;
    private final File idFile;
    final IPageDB<DBKey, ConcurrentTreeNode> source;
    private final ConcurrentTreeNode treeRootNode;
    final ConcurrentTreeNode treeTrashNode;
    private final AtomicLong nextDBID;
    final AtomicBoolean closed = new AtomicBoolean(false);
    private final Meter<METERTREE> meter;
    private final MeterFileLogger logger;
    private final AtomicDouble cacheHitRate = new AtomicDouble(0.0);
    private final MediatedEvictionConcurrentHashMap<CacheKey, ConcurrentTreeNode> cache;
    private final ScheduledExecutorService deletionThreadPool;

    @GuardedBy("treeTrashNode")
    private IPageDB.Range<DBKey, ConcurrentTreeNode> trashIterator;

    @SuppressWarnings("unused")
    final Gauge<Integer> treeTrashNodeCount = Metrics.newGauge(SkipListCache.class,
            "treeTrashNodeCount", scope,
            new Gauge<Integer>() {
                @Override
                public Integer value() {
                    return treeTrashNode == null ? -1 : treeTrashNode.getNodeCount();
                }
            });

    @SuppressWarnings("unused")
    final Gauge<Long> treeTrashHitsCount = Metrics.newGauge(SkipListCache.class,
            "treeTrashHitsCount", scope,
            new Gauge<Long>() {
                @Override
                public Long value() {
                    return treeTrashNode == null ? -1 : treeTrashNode.getCounter();
                }
            });

    ConcurrentTree(File root, int numDeletionThreads, int cleanQSize, int maxCacheSize,
                   int maxPageSize, PageFactory factory) throws Exception {
        LessFiles.initDirectory(root);
        this.root = root;
        long start = System.currentTimeMillis();

        // setup metering
        meter = new Meter<>(METERTREE.values());
        for (METERTREE m : METERTREE.values()) {
            meter.addCountMetric(m, m.toString());
        }

        // create meter logging thread
        if (TreeCommonParameters.meterLogging > 0) {
            logger = new MeterFileLogger(this, root, "tree-metrics",
                                         TreeCommonParameters.meterLogging, TreeCommonParameters.meterLogLines);
        } else {
            logger = null;
        }
        source = new PageDB.Builder<>(root, ConcurrentTreeNode.class, maxPageSize, maxCacheSize)
                .pageFactory(factory).build();
        source.setCacheMem(TreeCommonParameters.maxCacheMem);
        source.setPageMem(TreeCommonParameters.maxPageMem);
        source.setMemSampleInterval(TreeCommonParameters.memSample);
        // create cache
        cache = new MediatedEvictionConcurrentHashMap.
                Builder<CacheKey, ConcurrentTreeNode>().
                mediator(new CacheMediator(source)).
                maximumWeightedCapacity(cleanQSize).build();

        // get stored next db id
        idFile = new File(root, "nextID");
        if (idFile.exists() && idFile.isFile() && idFile.length() > 0) {
            nextDBID = new AtomicLong(Long.parseLong(LessBytes.toString(LessFiles.read(idFile))));
        } else {
            nextDBID = new AtomicLong(1);
        }

        // get tree root
        ConcurrentTreeNode dummyRoot = ConcurrentTreeNode.getTreeRoot(this);
        treeRootNode = (ConcurrentTreeNode) dummyRoot.getOrCreateEditableNode("root");
        treeTrashNode = (ConcurrentTreeNode) dummyRoot.getOrCreateEditableNode("trash");
        treeTrashNode.requireNodeDB();
        deletionThreadPool = Executors.newScheduledThreadPool(numDeletionThreads,
                new NamedThreadFactory(scope + "-deletion-", true));

        for (int i = 0; i < numDeletionThreads; i++) {
            deletionThreadPool.scheduleAtFixedRate(
                    new ConcurrentTreeDeletionTask(this, closed::get, LoggerFactory.getLogger(
                            ConcurrentTreeDeletionTask.class.getName() + ".Background")),
                    i, deletionThreadSleepMillis, TimeUnit.MILLISECONDS);
        }

        long openTime = System.currentTimeMillis() - start;
        log.info("dir={} root={} trash={} cache={} nextdb={} openms={}",
                 root, treeRootNode, treeTrashNode, TreeCommonParameters.cleanQMax, nextDBID, openTime);
    }

    public ConcurrentTree(File root) throws Exception {
        this(root, defaultNumDeletionThreads, TreeCommonParameters.cleanQMax,
             TreeCommonParameters.maxCacheSize, TreeCommonParameters.maxPageSize,
             Page.DefaultPageFactory.singleton);
    }

    public void meter(METERTREE meterval) {
        meter.inc(meterval);
    }

    /**
     * This method is only for testing purposes.
     * It has a built in safeguard but nonetheless
     * it should not be invoked for other purposes.
     */
    @VisibleForTesting
    boolean setNextNodeDB(long id) {
        while (true) {
            long current = nextDBID.get();
            if (current > id) {
                return false;
            } else if (nextDBID.compareAndSet(current, id)) {
                return true;
            }
        }
    }

    long getNextNodeDB() {
        long nextValue = nextDBID.incrementAndGet();
        return nextValue;
    }

    private static boolean setLease(final ConcurrentTreeNode node, final boolean lease) {
        return (!lease || node.tryLease());
    }

    public ConcurrentTreeNode getNode(final ConcurrentTreeNode parent, final String child, final boolean lease) {
        long nodedb = parent.nodeDB();
        if (nodedb <= 0) {
            log.trace("[node.get] {} --> {} NOMAP --> null", parent, child);
            return null;
        }
        CacheKey key = new CacheKey(nodedb, child);

        /**
         * (1) First check the cache for the (key, value) pair. If the value
         * is found and the value is successfully leased then return it.
         * (2) Otherwise the value is not found in the cache. Check the backing store
         * for the value. If the value is not found in the backing store then (3) return
         * null. Otherwise (4) if the value is found in the backing store and
         * successfully inserted into the cache and the value is leased then
         * return the value. If all of these steps are unsuccessful then repeat.
         */

        while (true) {
            ConcurrentTreeNode node = cache.get(key);
            if (node != null) {
                if (node.isDeleted()) {
                    cache.remove(key, node);
                } else if (setLease(node, lease)) {
                    reportCacheHit();
                    return node; // (1)
                }
            } else {// (2)
                DBKey dbkey = key.dbkey();
                reportCacheMiss();
                node = source.get(dbkey);

                if (node == null) {
                    meter.inc(METERTREE.SOURCE_MISS);
                    return null; // (3)
                }

                if (node.isDeleted()) {
                    source.remove(dbkey);
                } else {
                    node.initIfDecoded(this, dbkey, key.name);

                    ConcurrentTreeNode prev = cache.putIfAbsent(key, node);
                    if (prev == null) {
                        node.reactivate();
                        if (setLease(node, lease)) {
                            return node; // (4)
                        }
                    }
                }
            }
        }
    }

    public ConcurrentTreeNode getOrCreateNode(final ConcurrentTreeNode parent, final String child,
                                              final DataTreeNodeInitializer creator) {
        parent.requireNodeDB();
        CacheKey key = new CacheKey(parent.nodeDB(), child);
        ConcurrentTreeNode newNode = null;

        while (true) {
            ConcurrentTreeNode node = cache.get(key);
            if (node != null) {
                if (node.isDeleted()) {
                    cache.remove(key, node);
                } else if (setLease(node, true)) {
                    reportCacheHit();
                    return node;
                }
            } else {
                DBKey dbkey = key.dbkey();
                reportCacheMiss();
                node = source.get(dbkey);

                if (node != null) {
                    if (node.isDeleted()) {
                        source.remove(dbkey);
                    } else {
                        node.initIfDecoded(this, dbkey, key.name);
                        ConcurrentTreeNode prev = cache.putIfAbsent(key, node);
                        if (prev == null) {
                            node.reactivate();
                            if (setLease(node, true)) {
                                return node;
                            }
                        }
                    }
                } else { // create a new node
                    if (newNode == null) {
                        newNode = new ConcurrentTreeNode();
                        newNode.init(this, dbkey, key.name);
                        newNode.tryLease();
                        newNode.markChanged();
                        if (creator != null) {
                            creator.onNewNode(newNode);
                        }
                    }
                    node = newNode;
                    if (cache.putIfAbsent(key, node) == null) {
                        /**
                         * We must insert the new node into the external storage
                         * because our iterators traverse this data
                         * structure to search for nodes.
                         */
                        source.put(dbkey, node);
                        parent.updateNodeCount(1);
                        return node;
                    }
                }
            }
        }
    }

    boolean deleteNode(final ConcurrentTreeNode parent, final String child) {
        log.trace("[node.delete] {} --> {}", parent, child);
        long nodedb = parent.nodeDB();
        if (nodedb <= 0) {
            log.debug("parent has no children on delete : {} --> {}", parent, child);
            return false;
        }
        CacheKey key = new CacheKey(nodedb, child);
        // lease node to prevent eviction from cache and thereby disrupting our {@code source.remove()}
        ConcurrentTreeNode node = getNode(parent, child, true);
        if (node != null) {
            // first ensure no one can rehydrate into a different instance
            source.remove(key.dbkey());
            // "markDeleted" causes other threads to remove the node at will, so it is semantically the same
            // as removing it from the cache ourselves. Since this is the last and only instance, we can safely
            // coordinate concurrent deletion attempts with the lease count (-2 is used as a special flag) even
            // though most other code stops bothering with things like "thread safety" around this stage.
            if (node.markDeleted()) {
                // node could have already been dropped from the cache, and then re-created (sharing the same cache
                // key equality). That is a fresh node that needs its own deletion, so only try to remove our instance.
                cache.remove(key, node);
                parent.updateNodeCount(-1);
                if (node.hasNodes() && !node.isAlias()) {
                    markForChildDeletion(node);
                }
                return true;
            }
        }
        return false;
    }

    private void markForChildDeletion(final ConcurrentTreeNode node) {
        /*
         * only put nodes in the trash if they have children because they've
         * otherwise already been purged from backing store by release() in the
         * TreeCache.
         */
        assert node.hasNodes();
        assert !node.isAlias();
        long nodeDB = treeTrashNode.nodeDB();
        int next = treeTrashNode.incrementNodeCount();
        DBKey key = new DBKey(nodeDB, Raw.get(LessBytes.toBytes(next)));
        source.put(key, node);
        log.trace("[trash.mark] {} --> {}", next, treeTrashNode);
    }

    @SuppressWarnings("unchecked") IPageDB.Range<DBKey, ConcurrentTreeNode> fetchNodeRange(long db) {
        return source.range(new DBKey(db), new DBKey(db + 1));
    }

    @SuppressWarnings({"unchecked", "unused"}) private IPageDB.Range<DBKey, ConcurrentTreeNode> fetchNodeRange(long db, String from) {
        return source.range(new DBKey(db, Raw.get(from)), new DBKey(db + 1));
    }

    @SuppressWarnings("unchecked") IPageDB.Range<DBKey, ConcurrentTreeNode> fetchNodeRange(long db, String from, String to) {
        return source.range(new DBKey(db, Raw.get(from)),
                to == null ? new DBKey(db+1, (Raw)null) : new DBKey(db, Raw.get(to)));
    }

    @Override public ConcurrentTreeNode getRootNode() {
        return treeRootNode;
    }

    /**
     * Package-level visibility is for testing purposes only.
     */
    @VisibleForTesting
    void waitOnDeletions() {
        shutdownDeletionThreadPool();
        synchronized (treeTrashNode) {
            if (trashIterator != null) {
                trashIterator.close();
                trashIterator = null;
            }
        }
    }

    /**
     * Package-level visibility is for testing purposes only.
     */
    @VisibleForTesting
    ConcurrentMap<CacheKey, ConcurrentTreeNode> getCache() {
        return cache;
    }

    private void shutdownDeletionThreadPool() {
        if (deletionThreadPool == null)
            return;

        deletionThreadPool.shutdown();

        try {
            if (!deletionThreadPool.awaitTermination(10, TimeUnit.SECONDS)) {
                log.warn("Waiting on outstanding node deletions to complete.");
                deletionThreadPool.awaitTermination(Long.MAX_VALUE, TimeUnit.SECONDS);
            }
        } catch (InterruptedException ignored) {
        }
    }


    /**
     * Delete from the backing storage all nodes that have been moved to be
     * children of the trash node where they are waiting deletion. Also delete
     * all subtrees of these nodes. After deleting each subtree then test
     * the provided {@param terminationCondition}. If it returns true then
     * stop deletion.
     *
     * @param terminationCondition invoked between subtree deletions to
     *                             determine whether to return from method.
     */
    @Override
    public void foregroundNodeDeletion(BooleanSupplier terminationCondition) {
        ConcurrentTreeDeletionTask deletionTask = new ConcurrentTreeDeletionTask(this, terminationCondition, log);
        deletionTask.run();
    }

    @Override
    public void sync() throws IOException {
        log.debug("[sync] start");
        for (ConcurrentTreeNode node : cache.values()) {
            if (!node.isDeleted() && node.isChanged()) {
                source.put(node.dbkey, node);
            }
        }
        log.debug("[sync] end nextdb={}", nextDBID);
        LessFiles.write(idFile, LessBytes.toBytes(nextDBID.toString()), false);
    }

    @Override
    public long getDBCount() {
        return nextDBID.get();
    }

    @Override
    public int getCacheSize() {
        return cache.size();
    }

    @Override
    public double getCacheHitRate() {
        if (logger == null) {
            getIntervalData();
        }
        return cacheHitRate.get();
    }

    /**
     * Close the tree.
     *
     * @param cleanLog if true then wait for the BerkeleyDB clean thread to finish.
     * @param operation optionally test or repair the berkeleyDB.
     */
    @Override
    public void close(boolean cleanLog, CloseOperation operation) throws IOException {
        if (!closed.compareAndSet(false, true)) {
            log.trace("already closed");
            return;
        }
        log.debug("closing {}", this);
        waitOnDeletions();
        if (treeRootNode != null) {
            treeRootNode.markChanged();
            treeRootNode.release();
            if (treeRootNode.getLeaseCount() != 0) {
                throw new IllegalStateException("invalid root state on shutdown : " + treeRootNode);
            }
        }
        if (treeTrashNode != null) {
            treeTrashNode.markChanged();
            treeTrashNode.release();
        }
        sync();
        if (source != null) {
            int status = source.close(cleanLog, operation);
            if (status != 0) {
                throw new RuntimeException("page db close returned a non-zero exit code : " + status);
            }
        }
        if (logger != null) {
            logger.terminate();
        }
    }


    @Override
    public void close() throws IOException {
        close(false, CloseOperation.NONE);
    }

    @Override
    public Map<String, Long> getIntervalData() {
        Map<String, Long> mark = meter.mark();
        Long gets = mark.get(keyCacheGet);
        Long miss = mark.get(keyCacheMiss);
        if (gets == null || miss == null || miss == 0) {
            cacheHitRate.set(0);
        } else {
            cacheHitRate.set(1.0d - ((miss * 1.0d) / ((gets + miss) * 1.0d)));
        }
        return mark;
    }

    private void reportCacheHit() {
        meter.inc(METERTREE.CACHE_HIT);
    }

    private void reportCacheMiss() {
        meter.inc(METERTREE.CACHE_MISS);
    }

    @Override
    public String toString() {
        return "Tree@" + root;
    }

    @Override
    public DataTreeNode getLeasedNode(String name) {
        return getRootNode().getLeasedNode(name);
    }

    @Override
    public DataTreeNode getOrCreateNode(String name, DataTreeNodeInitializer init) {
        return getRootNode().getOrCreateNode(name, init);
    }

    @Override
    public boolean deleteNode(String node) {
        return getRootNode().deleteNode(node);
    }

    @Override
    public ClosableIterator<DataTreeNode> getIterator() {
        ConcurrentTreeNode rootNode = getRootNode();
        if (rootNode != null) {
            return getRootNode().getIterator();
        }
        return null;
    }

    @Override
    public ClosableIterator<DataTreeNode> getIterator(String begin) {
        return getRootNode().getIterator(begin);
    }

    @Override
    public ClosableIterator<DataTreeNode> getIterator(String from, String to) {
        return getRootNode().getIterator(from, to);
    }

    @Override
    public Iterator<DataTreeNode> iterator() {
        return getRootNode().iterator();
    }

    @Override
    public String getName() {
        return getRootNode().getName();
    }

    @Override
    public int getNodeCount() {
        return getRootNode().getNodeCount();
    }

    @Override
    public long getCounter() {
        return getRootNode().getCounter();
    }

    @Override
    public void incrementCounter() {
        getRootNode().incrementCounter();
    }

    @Override
    public long incrementCounter(long val) {
        return getRootNode().incrementCounter(val);
    }

    @Override
    public void writeLock() {
        getRootNode().writeLock();
    }

    @Override
    public void writeUnlock() {
        getRootNode().writeUnlock();
    }

    @Override
    public void setCounter(long val) {
        getRootNode().setCounter(val);
    }

    @Override
    public void updateChildData(DataTreeNodeUpdater state, TreeDataParent path) {
        getRootNode().updateChildData(state, path);
    }

    @Override
    public void updateParentData(DataTreeNodeUpdater state, DataTreeNode child, boolean isnew) {
        getRootNode().updateParentData(state, child, isnew);
    }

    @Override
    public boolean aliasTo(DataTreeNode target) {
        throw new RuntimeException("root node cannot be an alias");
    }

    @Override
    public void release() {
        getRootNode().release();
    }

    @Override
    public DataTreeNodeActor getData(String key) {
        return getRootNode().getData(key);
    }

    @Override
    public Map<String, TreeNodeData> getDataMap() {
        return getRootNode().getDataMap();
    }

    private static String keyName(DBKey dbkey) {
        try {
            return new String(dbkey.key(), "UTF-8");
        } catch (UnsupportedEncodingException ex) {
            log.warn("Could not decode the following dbkey bytes into a string: " +
                     Arrays.toString(dbkey.key()));
            return null;
        }
    }

    /**
     * Recursively delete all the children of the input node.
     * Use a non-negative value for the counter parameter to
     * tally the nodes that have been deleted. Use a negative
     * value to disable logging of the number of deleted nodes.
     *
     * @param rootNode root of the subtree to delete
     * @param counter if non-negative then tally the nodes that have been deleted
     */
    long deleteSubTree(ConcurrentTreeNode rootNode,
                       long counter,
                       BooleanSupplier terminationCondition,
                       Logger deletionLogger) {
        long nodeDB = rootNode.nodeDB();
        IPageDB.Range<DBKey, ConcurrentTreeNode> range = fetchNodeRange(nodeDB);
        DBKey endRange;
        boolean reschedule;
        try {
            while (range.hasNext() && !terminationCondition.getAsBoolean()) {
                if ((++counter % deletionLogInterval) == 0) {
                    deletionLogger.info("Deleted {} nodes from the tree.", counter);
                }
                Map.Entry<DBKey, ConcurrentTreeNode> entry = range.next();
                ConcurrentTreeNode next = entry.getValue();

                if (next.hasNodes() && !next.isAlias()) {
                    counter = deleteSubTree(next, counter, terminationCondition, deletionLogger);
                }
                String name = entry.getKey().rawKey().toString();
                CacheKey key = new CacheKey(nodeDB, name);
                ConcurrentTreeNode cacheNode = cache.remove(key);
                /* Mark the node as deleted so that it will not be
                 * pushed to disk when removed from the eviction queue.
                 */
                if (cacheNode != null) {
                    cacheNode.markDeleted();
                }
            }
            if (range.hasNext()) {
                endRange = range.next().getKey();
                reschedule = true;
            } else {
                endRange = new DBKey(nodeDB + 1);
                reschedule = false;
            }
        } finally {
            range.close();
        }
        source.remove(new DBKey(nodeDB), endRange);
        if (reschedule) {
            markForChildDeletion(rootNode);
        }
        return counter;
    }

    Map.Entry<DBKey, ConcurrentTreeNode> nextTrashNode() {
        synchronized (treeTrashNode) {
            if (trashIterator == null) {
                return recreateTrashIterator();
            } else if (trashIterator.hasNext()) {
                return trashIterator.next();
            } else {
                return recreateTrashIterator();
            }
        }
    }

    @GuardedBy("treeTrashNode")
    private Map.Entry<DBKey, ConcurrentTreeNode> recreateTrashIterator() {
        if (trashIterator != null) {
            trashIterator.close();
        }
        trashIterator = fetchNodeRange(treeTrashNode.nodeDB());
        if (trashIterator.hasNext()) {
            return trashIterator.next();
        } else {
            trashIterator.close();
            trashIterator = null;
            return null;
        }
    }

    /**
     * For testing purposes only.
     */
    @VisibleForTesting
    ConcurrentTreeNode getTreeTrashNode() {
        return treeTrashNode;
    }

    public void repairIntegrity() {
        PagedKeyValueStore store = source.getEps();
        if (store instanceof SkipListCache) {
            ((SkipListCache) store).testIntegrity(true);
        }
    }

}


File: hydra-data/src/main/java/com/addthis/hydra/data/tree/concurrent/ConcurrentTreeNode.java
/*
 * Licensed under the Apache License, Version 2.0 (the "License");
 * you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at
 *
 * http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 */
package com.addthis.hydra.data.tree.concurrent;

import java.util.ArrayList;
import java.util.Collection;
import java.util.HashMap;
import java.util.Iterator;
import java.util.List;
import java.util.Map;
import java.util.Map.Entry;
import java.util.NoSuchElementException;
import java.util.concurrent.atomic.AtomicBoolean;
import java.util.concurrent.atomic.AtomicInteger;
import java.util.concurrent.locks.ReadWriteLock;
import java.util.concurrent.locks.ReentrantReadWriteLock;

import com.addthis.basis.util.ClosableIterator;
import com.addthis.basis.util.MemoryCounter.Mem;

import com.addthis.hydra.data.tree.AbstractTreeNode;
import com.addthis.hydra.data.tree.DataTreeNode;
import com.addthis.hydra.data.tree.DataTreeNodeActor;
import com.addthis.hydra.data.tree.DataTreeNodeInitializer;
import com.addthis.hydra.data.tree.DataTreeNodeUpdater;
import com.addthis.hydra.data.tree.TreeDataParameters;
import com.addthis.hydra.data.tree.TreeDataParent;
import com.addthis.hydra.data.tree.TreeNodeData;
import com.addthis.hydra.data.tree.TreeNodeDataDeferredOperation;
import com.addthis.hydra.store.db.DBKey;
import com.addthis.hydra.store.db.IPageDB.Range;


/**
 * Each instance has an AtomicInteger 'lease' that records the current
 * activity of a node. Values of lease signify the following behavior:
 *
 * N (for N > 0) : There are N threads that may be modifying the node. The node is active.
 * 0             : The node is idle. It may be evicted.
 * -1            : The node is currently being evicted. This is a transient state.
 * -2            : The node has been deleted.
 * -3            : The node has been evicted.
 *
 * Only an idle node may be evicted. Any node that has 0 or more leases
 * can be deleted (yes it is counterintuitive but for legacy purposes
 * deleting nodes is a higher priority operation that modifying nodes).
 *
 */
public class ConcurrentTreeNode extends AbstractTreeNode {

    public static final int ALIAS = 1 << 1;

    public static ConcurrentTreeNode getTreeRoot(ConcurrentTree tree) {
        ConcurrentTreeNode node = new ConcurrentTreeNode() {
            @Override
            void requireEditable() {

            }
        };
        node.tree = tree;
        node.leases.incrementAndGet();
        node.nodedb = 1L;
        return node;
    }

    /**
     * required for Codable. must be followed by an init() call.
     */
    public ConcurrentTreeNode() {
    }

    protected void initIfDecoded(ConcurrentTree tree, DBKey key, String name) {
        if (decoded.get()) {
            synchronized (initLock) {
                if (initOnce.compareAndSet(false, true)) {
                    this.tree = tree;
                    this.dbkey = key;
                    this.name = name;
                    decoded.set(false);
                }
            }
        }
    }

    protected void init(ConcurrentTree tree, DBKey key, String name) {
        this.tree = tree;
        this.dbkey = key;
        this.name = name;
    }

    @Mem(estimate = false, size = 64)
    private ConcurrentTree tree;
    @Mem(estimate = false, size = 64)
    private AtomicInteger leases = new AtomicInteger(0);
    @Mem(estimate = false, size = 64)
    private AtomicBoolean changed = new AtomicBoolean(false);
    @Mem(estimate = false, size = 64)
    private ReadWriteLock lock = new ReentrantReadWriteLock();

    private AtomicBoolean decoded = new AtomicBoolean(false);
    private AtomicBoolean initOnce = new AtomicBoolean(false);
    private final Object initLock = new Object();

    protected String name;
    protected DBKey dbkey;

    public String toString() {
        return "TN[k=" + dbkey + ",db=" + nodedb + ",n#=" + nodes + ",h#=" + hits +
               ",nm=" + name + ",le=" + leases + ",ch=" + changed + ",bi=" + bits + "]";
    }

    @Override public String getName() {
        return name;
    }

    @Override @SuppressWarnings("unchecked")
    public Map<String, TreeNodeData> getDataMap() {
        return data;
    }

    public int getLeaseCount() {
        return leases.get();
    }

    /**
     * The synchronized methods protecting the {@code nodes} field
     * is a code smell. This should probably be protected by the
     * encoding reader/writer {@code lock} field. There is an invariant
     * for the page storage system that the encoding (write) locks of two nodes
     * cannot be held simultaneously and switching to the encoding lock
     * for these methods may violate the invariant.
     */

    protected synchronized int incrementNodeCount() {
        return nodes++;
    }

    protected synchronized int updateNodeCount(int delta) {
        nodes += delta;
        changed.set(true);
        return nodes;
    }

    void requireEditable() {
        int count = leases.get();
        if (!(count == -2 || count > 0)) {
            throw new RuntimeException("fail editable requirement: lease state is " + count);
        }
    }

    public final boolean isBitSet(int bitcheck) {
        return (bits & bitcheck) == bitcheck;
    }

    public boolean isAlias() {
        return isBitSet(ALIAS);
    }

    public boolean isDeleted() {
        int count = leases.get();
        return count == -2;
    }

    public void markChanged() {
        requireEditable();
        changed.set(true);
    }

    protected boolean markDeleted() {
        return leases.getAndSet(-2) != -2;
    }

    protected void evictionComplete() {
        leases.compareAndSet(-1, -3);
    }

    protected synchronized void markAlias() {
        bitSet(ALIAS);
    }

    protected boolean isChanged() {
        return changed.get();
    }

    private final void bitSet(int set) {
        bits |= set;
    }

    private final void bitUnset(int set) {
        bits &= (~set);
    }

    /**
     * A node is reactivated when it is retrieved from the backing storage
     * and its state transitions from the inactive state to the active state
     * with 0 leases.
     *
     */
    void reactivate() {
        while(true) {
            int count = leases.get();
            if (count == -3 && leases.compareAndSet(-3, 0)) {
                return;
            } else if (count == -1 && leases.compareAndSet(-1, 0)) {
                return;
            } else if (count != -3 && count != -1) {
                return;
            }
        }
    }

    /**
     * Atomically try to acquire a lease. If the node is either
     * in the inactive state or the deleted state then a lease
     * cannot be acquired.
     *
     * @return {@code true} if a lease is acquired
     */
    boolean tryLease() {
        while (true) {
            int count = leases.get();
            if (count < 0) {
                return false;
            }
            if (leases.compareAndSet(count, count + 1)) {
                return true;
            }
        }
    }

    /**
     * The node can be evicted if it has been deleted
     * or it transitions from the active leases with 0 leases
     * to the inactive state. If the node is already in the
     * inactive state then it cannot be evicted.
     *
     * @return true if the node can be evicted
     */
    boolean trySetEviction() {
        while (true) {
            int count = leases.get();
            if (count == -2) {
                return true;
            } else if (count != 0) {
                return false;
            }
            if (leases.compareAndSet(0, -1)) {
                return true;
            }
        }
    }

    /**
     * Atomically decrement the number of active leases.
     */
    @Override
    public void release() {
        while (true) {
            int count = leases.get();
            if (count <= 0) {
                return;
            }
            if (leases.compareAndSet(count, count - 1)) {
                return;
            }
        }
    }

    /**
     * double-checked locking idiom to avoid unnecessary synchronization.
     */
    protected void requireNodeDB() {
        if (!hasNodes()) {
            synchronized (this) {
                if (!hasNodes()) {
                    nodedb = tree.getNextNodeDB();
                }
            }
        }
    }

    protected long nodeDB() {
        return nodedb;
    }

    /**
     * returns an iterator of read-only nodes
     */
    public ClosableIterator<DataTreeNode> getNodeIterator() {
        return !hasNodes() || isDeleted() ? new Iter(null, false) : new Iter(tree.fetchNodeRange(nodedb), true);
    }

    /**
     * returns an iterator of read-only nodes
     */
    public ClosableIterator<DataTreeNode> getNodeIterator(String prefix) {
        if (!isDeleted() && prefix != null && prefix.length() > 0) {
            /**
             * the reason this behaves as a prefix as opposed to a "from" is the way
             * the "to" endpoint is calculated.  the last byte of the prefix is incremented
             * by a value of one and used as "to".  this is the effect of excluding all
             * other potential matches with a lexicographic value greater than prefix.
             */
            StringBuilder sb = new StringBuilder(prefix.substring(0, prefix.length() - 1));
            sb.append((char) (prefix.charAt(prefix.length() - 1) + 1));
            return getNodeIterator(prefix, sb.toString());
        } else {
            return new Iter(null, false);
        }
    }

    /**
     * returns an iterator of read-only nodes
     */
    public ClosableIterator<DataTreeNode> getNodeIterator(String from, String to) {
        if (!hasNodes() || isDeleted()) {
            return new Iter(null, false);
        }
        return new Iter(tree.fetchNodeRange(nodedb, from, to), true);
    }

    @Override public ConcurrentTreeNode getNode(String name) {
        return tree.getNode(this, name, false);
    }

    @Override public ConcurrentTreeNode getLeasedNode(String name) {
        return tree.getNode(this, name, true);
    }

    public DataTreeNode getOrCreateEditableNode(String name) {
        return getOrCreateEditableNode(name, null);
    }

    public DataTreeNode getOrCreateEditableNode(String name, DataTreeNodeInitializer creator) {
        return tree.getOrCreateNode(this, name, creator);
    }

    @Override public boolean deleteNode(String name) {
        return tree.deleteNode(this, name);
    }

    /**
     * link this node (aliasing) to another node in the tree. they will share
     * children, but not meta-data. should only be called from within a
     * TreeNodeInitializer passed to getOrCreateEditableNode.
     */
    @Override
    public boolean aliasTo(DataTreeNode node) {
        if (node.getClass() != ConcurrentTreeNode.class) {
            return false;
        }
        requireEditable();
        if (hasNodes()) {
            return false;
        }
        ((ConcurrentTreeNode) node).requireNodeDB();
        nodedb = ((ConcurrentTreeNode) node).nodedb;
        markAlias();
        return true;
    }

    protected HashMap<String, TreeNodeData> createMap() {
        if (data == null) {
            data = new HashMap<>();
        }
        return data;
    }

    /**
     * TODO: warning. if you annotate a path with data then have another path
     * that intersects that node in the tree with some other data, the first one
     * wins and the new data will not be added. further, every time the
     * annotated node is crossed, the attached data will be updated if that path
     * declares annotated data.
     */
    @Override @SuppressWarnings("unchecked")
    public void updateChildData(DataTreeNodeUpdater state, TreeDataParent path) {
        requireEditable();
        boolean updated = false;
        HashMap<String, TreeDataParameters> dataconf = path.dataConfig();
        lock.writeLock().lock();
        try {
            if (path.assignHits()) {
                hits = state.getAssignmentValue();
                updated = true;
            } else if (path.countHits()) {
                hits += state.getCountValue();
                updated = true;
            }
            if (dataconf != null) {
                if (data == null) {
                    data = new HashMap<>(dataconf.size());
                }
                for (Entry<String, TreeDataParameters> el : dataconf.entrySet()) {
                    TreeNodeData tnd = data.get(el.getKey());
                    if (tnd == null) {
                        tnd = el.getValue().newInstance(this);
                        data.put(el.getKey(), tnd);
                        updated = true;
                    }
                    if (tnd.updateChildData(state, this, el.getValue())) {
                        updated = true;
                    }
                }
            }
        } finally {
            lock.writeLock().unlock();
        }
        if (updated) {
            changed.set(true);
        }
    }

    /**
     * @return true if data was changed
     */
    @Override public void updateParentData(DataTreeNodeUpdater state, DataTreeNode child, boolean isnew) {
        requireEditable();
        List<TreeNodeDataDeferredOperation> deferredOps = null;
        lock.writeLock().lock();
        try {
            if (child != null && data != null) {
                deferredOps = new ArrayList<>(1);
                for (TreeNodeData<?> tnd : data.values()) {
                    if (isnew && tnd.updateParentNewChild(state, this, child, deferredOps)) {
                        changed.set(true);
                    }
                    if (tnd.updateParentData(state, this, child, deferredOps)) {
                        changed.set(true);
                    }
                }
            }
        } finally {
            lock.writeLock().unlock();
        }
        if (deferredOps != null) {
            for (TreeNodeDataDeferredOperation currentOp : deferredOps) {
                currentOp.run();
            }
        }
    }

    // TODO concurrent broken -- data classes should be responsible for their
    // own get/update sync
    @Override public DataTreeNodeActor getData(String key) {
        lock.readLock().lock();
        try {
            return data != null ? data.get(key) : null;
        } finally {
            lock.readLock().unlock();
        }
    }

    // TODO concurrent broken -- data classes should be responsible for their
    // own get/update sync
    public Collection<String> getDataFields() {
        lock.readLock().lock();
        try {
            if (data == null || data.size() == 0) {
                return null;
            }
            return data.keySet();
        } finally {
            lock.readLock().unlock();
        }
    }

    @Override
    public int getNodeCount() {
        return nodes;
    }

    @Override
    public void postDecode() {
        super.postDecode();
        decoded.set(true);
    }

    /**
     * TODO warning: not thread safe. sync around next(), hasNext() when
     * concurrency is required.
     */
    private final class Iter implements ClosableIterator<DataTreeNode> {

        private Range<DBKey, ConcurrentTreeNode> range;
        private ConcurrentTreeNode next;
        private boolean filterDeleted;

        private Iter(Range<DBKey, ConcurrentTreeNode> range, boolean filterDeleted) {
            this.range = range;
            this.filterDeleted = filterDeleted;
            fetchNext();
        }

        public String toString() {
            return "Iter(" + range + "," + next + ")";
        }

        void fetchNext() {
            if (range != null) {
                next = null;
                while (range.hasNext()) {
                    Entry<DBKey, ConcurrentTreeNode> tne = range.next();
                    next = tree.getNode(ConcurrentTreeNode.this, tne.getKey().rawKey().toString(), false);
                    if (next != null) {
                        if (filterDeleted && next.isDeleted()) {
                            next = null;
                            continue;
                        }
                        break;
                    }
                }
            }
        }

        @Override
        public boolean hasNext() {
            return next != null;
        }

        @Override
        public ConcurrentTreeNode next() {
            if (!hasNext()) {
                throw new NoSuchElementException();
            }
            ConcurrentTreeNode ret = next;
            fetchNext();
            return ret;
        }

        @Override
        public void remove() {
            throw new UnsupportedOperationException();
        }

        @Override
        public void close() {
            if (range != null) {
                range.close();
                range = null;
            }
        }
    }

    @Override
    public void encodeLock() {
        lock.readLock().lock();
    }

    @Override
    public void encodeUnlock() {
        lock.readLock().unlock();
    }


    @Override
    public void writeLock() {
        lock.writeLock().lock();
    }

    @Override
    public void writeUnlock() {
        lock.writeLock().unlock();
    }

    @Override
    public Iterator<DataTreeNode> iterator() {
        return getNodeIterator();
    }

    @Override
    public ClosableIterator<DataTreeNode> getIterator() {
        return getNodeIterator();
    }

    @Override
    public ConcurrentTree getTreeRoot() {
        return tree;
    }

    @Override
    public ClosableIterator<DataTreeNode> getIterator(String begin) {
        return getNodeIterator(begin);
    }

    @Override
    public ClosableIterator<DataTreeNode> getIterator(String from, String to) {
        return getNodeIterator(from, to);
    }

    @Override
    public DataTreeNode getOrCreateNode(String name, DataTreeNodeInitializer init) {
        return getOrCreateEditableNode(name, init);
    }

    /**
     * The synchronized methods protecting the {@code counter} field
     * is a code smell. This should probably be protected by the
     * encoding reader/writer {@code lock} field. There is an invariant
     * for the page storage system that the encoding (write) locks of two nodes
     * cannot be held simultaneously and switching to the encoding lock
     * for these methods may violate the invariant.
     */

    @Override
    public synchronized long getCounter() {
        return hits;
    }

    @Override
    public synchronized void incrementCounter() {
        hits++;
    }

    @Override
    public synchronized long incrementCounter(long val) {
        hits += val;
        return hits;
    }

    @Override
    public synchronized void setCounter(long val) {
        hits = val;
    }
}


File: hydra-data/src/main/java/com/addthis/hydra/data/tree/prop/DataKeyTop.java
/*
 * Licensed under the Apache License, Version 2.0 (the "License");
 * you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at
 *
 * http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 */
package com.addthis.hydra.data.tree.prop;

import java.util.ArrayList;
import java.util.Arrays;
import java.util.List;
import java.util.Map;
import java.util.Map.Entry;

import com.addthis.basis.util.LessStrings;
import com.addthis.basis.util.Varint;

import com.addthis.bundle.util.AutoField;
import com.addthis.bundle.value.ValueFactory;
import com.addthis.bundle.value.ValueObject;
import com.addthis.codec.annotations.FieldConfig;
import com.addthis.codec.codables.Codable;
import com.addthis.hydra.data.filter.value.ValueFilter;
import com.addthis.hydra.data.tree.DataTreeNode;
import com.addthis.hydra.data.tree.DataTreeNodeUpdater;
import com.addthis.hydra.data.tree.ReadTreeNode;
import com.addthis.hydra.data.tree.TreeDataParameters;
import com.addthis.hydra.data.tree.TreeNodeData;
import com.addthis.hydra.data.util.KeyTopper;

import io.netty.buffer.ByteBuf;
import io.netty.buffer.PooledByteBufAllocator;
import io.netty.buffer.Unpooled;

public class DataKeyTop extends TreeNodeData<DataKeyTop.Config> implements Codable {

    /**
     * This data attachment <span class="hydra-summary">keeps a record of the top N values
     * and the number of times they're encountered</span>.
     * <p/>
     * <p>Job Configuration Example:</p>
     * <pre>
     * {const:"shard-counter"}
     * {field:"DATE_YMD", data.top_ips.key-top {size:500, key:"IP"}}
     * </pre>
     *
     * <p><b>Query Path Directives</b>
     *
     * <p>"$" operations support the following commands in the format
     * $+{attachment}={command} :
     * <table>
     * <tr>
     * <td width="20%">size</td>
     * <td>number of entries in the data attachment</td></tr>
     * <tr>
     * <td>g[name]</td>
     * <td>value associated with the key "name"</td>
     * </tr>
     * <tr>
     * <td>k[number]</td>
     * <td>key associated with the i^th element. Counting is assumed to begin at 1</td>
     * </tr>
     * <tr>
     * <td>v[number]</td>
     * <td>value associated with the i^th element. Counting is assumed to begin at 1</td>
     * </tr>
     * <tr>
     * <td>e[number]</td>
     * <td>error associated with the i^th element. Counting is assumed to begin at 1</td>
     * </tr>
     * </table>
     *
     * <p>"%" operations support the following commands in the format /+%{attachment}={command}.
     * Two consecutive equals characters ("==") are necessary to use the "hit", "node",
     * "phit", or "vhit" operations.
     *
     * <table>
     * <tr>
     * <td width="25%">"=hit" or "=node"</td>
     * <td>retrieve the child nodes that are identified by the keys stored in the data attachment</td></tr>
     * <tr>
     * <td>"=vhit"</td>
     * <td>create virtual nodes using the keys stored in the data attachment</td>
     * </tr>
     * <tr>
     * <td>"=phit"</td>
     * <td>retrieve a cloned copy of the child nodes that are identified by the keys stored in the data attachment</td>
     * </tr>
     * <tr>
     * <td>"=guaranteed"</td>
     * <td>if error tracking has been enabled then only return the guaranteed top-k elements</td>
     * </tr>
     * <tr>
     * <td>"name1:name2:name3"</td>
     * <td>create virtual nodes using the keys specified in the command</td>
     * </tr>
     * </table>
     *
     * <p>Using "%" without any arguments creates virtual nodes using the keys
     * stored in the data attachment. If error estimation is enabled then the
     * errors appear in the 'stats' data attachment that is a {@link DataMap}
     * retrieved using the key 'error'.
     *
     * <p>Query Path Examples:</p>
     * <pre>
     *     /shard-counter/+130101$+top_ips=k1,k2,k3,k4,k5
     *     /shard-counter/+130101/+%top_ips==hit
     * </pre>
     *
     * @user-reference
     */
    public static final class Config extends TreeDataParameters<DataKeyTop> {

        /**
         * Bundle field name from which to draw values.
         * This field is required.
         */
        @FieldConfig(codable = true, required = true)
        private AutoField key;

        /**
         * Optionally specify a bundle field name for
         * which to weight the insertions into the
         * data attachment. If weight is specified
         * then the weight field must have a valid
         * integer whenever the key field is non-null
         * or the job will error. Default is null.
         */
        @FieldConfig(codable = true)
        private AutoField weight;

        /**
         * Maximum capacity of the key topper.
         * This field is required.
         */
        @FieldConfig(codable = true, required = true)
        private int size;

        /**
         * Optionally track an error estimate associated with
         * each key/value pair. Default is false.
         */
        @FieldConfig(codable = true)
        private boolean errors;

        /**
         * Optionally split the input with this regular expression
         * before recording the data. Default is null.
         */
        @FieldConfig(codable = true)
        private String splitRegex;

        /**
         * Optionally apply a filter before recording the data.
         * Default is null.
         */
        @FieldConfig(codable = true)
        private ValueFilter filter;

        @Override
        public DataKeyTop newInstance() {
            DataKeyTop dataKeyTop = new DataKeyTop();
            dataKeyTop.size = size;
            dataKeyTop.top = new KeyTopper().init().setLossy(true).enableErrors(errors);
            dataKeyTop.filter = filter;
            return dataKeyTop;
        }
    }

    @FieldConfig(codable = true, required = true)
    private KeyTopper top;
    @FieldConfig(codable = true, required = true)
    private int size;

    private ValueFilter filter;
    private AutoField keyAccess;
    private AutoField weightAccess;

    @Override
    public boolean updateChildData(DataTreeNodeUpdater state, DataTreeNode childNode, DataKeyTop.Config conf) {
        if (keyAccess == null) {
            keyAccess = conf.key;
            weightAccess = conf.weight;
            filter = conf.filter;
        }
        ValueObject val = keyAccess.getValue(state.getBundle());
        if (val != null) {
            if (filter != null) {
                val = filter.filter(val, state.getBundle());
                if (val == null) {
                    return false;
                }
            }
            int weight = 1;
            if (weightAccess != null) {
                weight = weightAccess.getValue(state.getBundle()).asLong().asNative().intValue();
            }
            if (conf.splitRegex != null) {
                String[] split = val.toString().split(conf.splitRegex);
                for (int i = 0; i < split.length; i++) {
                    top.increment(split[i], weight, size);
                }
            } else {
                if (val.getObjectType() == ValueObject.TYPE.ARRAY) {
                    for (ValueObject obj : val.asArray()) {
                        top.increment(obj.toString(), weight, size);
                    }
                } else {
                    top.increment(val.toString(), weight, size);
                }
            }
            return true;
        } else {
            return false;
        }
    }

    @Override
    public ValueObject getValue(String key) {
        if (key != null && key.length() > 0) {
            if (key.equals("size")) {
                return ValueFactory.create(top.size());
            }
            try {
                if (key.charAt(0) == 'g') {
                    String topKey = key.substring(1);
                    Long val = top.get(topKey);
                    return ValueFactory.create(val != null ? val : 0);
                }
                if (key.charAt(0) == 'v') {
                    int pos = Integer.parseInt(key.substring(1));
                    return pos <= top.size() ? ValueFactory.create(top.getSortedEntries()[pos - 1].getValue()) : null;
                }
                if (key.charAt(0) == 'e') {
                    if (top.hasErrors()) {
                        int pos = Integer.parseInt(key.substring(1));
                        if (pos <= top.size()) {
                            String element = top.getSortedEntries()[pos - 1].getKey();
                            Long error = top.getError(element);
                            return ValueFactory.create(error);
                        }
                    }
                    return null;
                }
                if (key.charAt(0) == 'k') {
                    key = key.substring(1);
                }
                int pos = Integer.parseInt(key);
                return pos <= top.size() ? ValueFactory.create(top.getSortedEntries()[pos - 1].getKey()) : null;
            } catch (Exception e) {
                return ValueFactory.create(e.toString());
            }
        }
        return ValueFactory.create(top.toString());
    }

    /**
     * return types of synthetic nodes returned
     */
    @Override public List<String> getNodeTypes() {
        return Arrays.asList(new String[]{"#"});
    }

    @Override
    public List<DataTreeNode> getNodes(DataTreeNode parent, String key) {
        if (key != null && key.startsWith("=")) {
            key = key.substring(1);
            if (key.equals("hit") || key.equals("node")) {
                Entry<String, Long>[] list = top.getSortedEntries();
                ArrayList<DataTreeNode> ret = new ArrayList<>(list.length);
                for (Entry<String, Long> e : list) {
                    DataTreeNode node = parent.getNode(e.getKey());
                    if (node != null) {
                        ret.add(node);
                    }
                }
                return ret;
            } else if (key.equals("vhit")) {
                Entry<String, Long>[] list = top.getSortedEntries();
                ArrayList<DataTreeNode> ret = new ArrayList<>(list.length);
                for (Entry<String, Long> e : list) {
                    ret.add(new VirtualTreeNode(e.getKey(), e.getValue()));
                }
                return ret;
            } else if (key.equals("phit")) {
                Entry<String, Long>[] list = top.getSortedEntries();
                ArrayList<DataTreeNode> ret = new ArrayList<>(list.length);
                for (Entry<String, Long> e : list) {
                    DataTreeNode node = parent.getNode(e.getKey());
                    if (node != null) {
                        node = ((ReadTreeNode) node).getCloneWithCount(e.getValue());
                        ret.add(node);
                    }
                }
                return ret;
            } else if (key.equals("guaranteed")) {
                return generateVirtualNodes(true);
            }
        } else if (key != null) {
            String[] keys = LessStrings.splitArray(key, ":");
            ArrayList<DataTreeNode> list = new ArrayList<>(keys.length);
            for (String k : keys) {
                Long v = top.get(k);
                if (v != null) {
                    list.add(new VirtualTreeNode(k, v));
                }
            }
            return list.size() > 0 ? list : null;
        }
        return generateVirtualNodes(false);
    }

    /**
     * Generate a list of virtual nodes and include error estimates
     * if they are available.
     *
     * @param onlyGuaranteed if true then only return guaranteed top-K
     *                       (requires error estimates)
     * @return list of virtual nodes
     */
    private List<DataTreeNode> generateVirtualNodes(boolean onlyGuaranteed) {
        ArrayList<DataTreeNode> list = new ArrayList<>(top.size());
        Entry<String, Long>[] entries = top.getSortedEntries();
        for (int i = 0; i < entries.length; i++) {
            Entry<String,Long> entry = entries[i];
            String name = entry.getKey();
            Long value = entry.getValue();
            VirtualTreeNode node = new VirtualTreeNode(name, value);
            if (top.hasErrors()) {
                Long error = top.getError(name);
                if (onlyGuaranteed && ((i + 1) < entries.length) &&
                    ((value - error) < entries[i + 1].getValue())) {
                    break;
                }
                Map<String, TreeNodeData> data = node.createMap();
                DataMap dataMap = new DataMap(1);
                dataMap.put("error", ValueFactory.create(error));
                data.put("stats", dataMap);
            }
            list.add(node);
        }
        return list;
    }

    @Override
    public byte[] bytesEncode(long version) {
        byte[] bytes = null;
        ByteBuf buf = PooledByteBufAllocator.DEFAULT.buffer();
        try {
            byte[] topBytes = top.bytesEncode(version);
            Varint.writeUnsignedVarInt(topBytes.length, buf);
            buf.writeBytes(topBytes);
            Varint.writeUnsignedVarInt(size, buf);
            bytes = new byte[buf.readableBytes()];
            buf.readBytes(bytes);
        } finally {
            buf.release();
        }
        return bytes;
    }

    @Override
    public void bytesDecode(byte[] b, long version) {
        top = new KeyTopper();
        ByteBuf buf = Unpooled.wrappedBuffer(b);
        try {
            int topBytesLength = Varint.readUnsignedVarInt(buf);
            if (topBytesLength > 0) {
                byte[] topBytes = new byte[topBytesLength];
                buf.readBytes(topBytes);
                top.bytesDecode(topBytes, version);
            } else {
                top.init().setLossy(true);
            }
            size = Varint.readUnsignedVarInt(buf);
        } finally {
            buf.release();
        }
    }
}


File: hydra-data/src/main/java/com/addthis/hydra/data/tree/prop/DataLimitRecent.java
/*
 * Licensed under the Apache License, Version 2.0 (the "License");
 * you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at
 *
 * http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 */
package com.addthis.hydra.data.tree.prop;

import java.util.Collections;
import java.util.Comparator;
import java.util.LinkedList;
import java.util.List;

import com.addthis.bundle.core.Bundle;
import com.addthis.bundle.core.BundleField;
import com.addthis.bundle.util.ValueUtil;
import com.addthis.bundle.value.ValueFactory;
import com.addthis.bundle.value.ValueObject;
import com.addthis.codec.annotations.FieldConfig;
import com.addthis.codec.codables.Codable;
import com.addthis.hydra.data.tree.DataTreeNode;
import com.addthis.hydra.data.tree.DataTreeNodeUpdater;
import com.addthis.hydra.data.tree.TreeDataParameters;
import com.addthis.hydra.data.tree.TreeNodeData;
import com.addthis.hydra.data.tree.TreeNodeDataDeferredOperation;


public class DataLimitRecent extends TreeNodeData<DataLimitRecent.Config> {

    /**
     * This data attachment <span class="hydra-summary">limits child nodes to recent values</span>.
     *
     * @user-reference
     */
    public static final class Config extends TreeDataParameters<DataLimitRecent> {

        /**
         * If non-zero then remove values that are older than the oldest bundle by this amount.
         * Either this field or {@link #size} must be nonzero.
         */
        @FieldConfig(codable = true)
        private long age;

        /**
         * If non-zero then accept at most N bundles.
         * Either this field or {@link #age} must be nonzero.
         */
        @FieldConfig(codable = true)
        private int size;

        /**
         * Bundle field name from which to draw time values.
         * If null then the system time is used while processing each bundle.
         */
        @FieldConfig(codable = true)
        private String timeKey;

        /**
         * If true then use the time value to sort the observed values.
         * The sorting is inefficient and should be
         * reimplemented. Default is false.
         */
        @FieldConfig(codable = true)
        private boolean sortQueue;

        @Override
        public DataLimitRecent newInstance() {
            DataLimitRecent dc = new DataLimitRecent();
            dc.size = size;
            dc.age = age;
            dc.timeKey = timeKey;
            dc.sortQueue = sortQueue;
            dc.queue = new LinkedList<>();
            return dc;
        }
    }

    /** */
    public static final class KeyTime implements Codable {

        @FieldConfig(codable = true)
        private String key;
        @FieldConfig(codable = true)
        private long time;
    }

    @FieldConfig(codable = true)
    private int size;
    @FieldConfig(codable = true)
    private long age;
    @FieldConfig(codable = true)
    private long deleted;
    @FieldConfig(codable = true)
    private LinkedList<KeyTime> queue;
    @FieldConfig(codable = true)
    private String timeKey;
    @FieldConfig(codable = true)
    private boolean sortQueue;

    private BundleField keyAccess;

    @Override
    public boolean updateChildData(DataTreeNodeUpdater state, DataTreeNode tn, Config conf) {
        return false;
    }

    public static class DataLimitRecentDeferredOperation extends TreeNodeDataDeferredOperation {

        final DataTreeNode parentNode;
        final KeyTime e;

        DataLimitRecentDeferredOperation(DataTreeNode parentNode, KeyTime e) {
            this.parentNode = parentNode;
            this.e = e;
        }

        @Override
        public void run() {
            DataTreeNode check = parentNode.getOrCreateNode(e.key, null);
            if (check != null) {
                // TODO need 'count' field from current PathElement to be
                // strict instead of using 1
                // TODO requires update to TreeNodeUpdater to keep ptr to
                // PathElement being processed

                /**
                 * The following try/finally block locks 'parentNode'
                 * when it should be locking 'check' instead. This is
                 * to maintain the original behavior of the updateParentData()
                 * method before the introduction of DataLimitRecentDeferredOperation.
                 *
                 * Prior to the introduction of deferred operations this
                 * code was executed holding the parentNode lock.
                 * Therefore we will continue to mimic this behavior
                 * until the TreeNode class is properly refactored with
                 * a policy for maintaining consistent state during
                 * concurrent operations.
                 */
                parentNode.writeLock();
                long counterVal;
                try {
                    counterVal = check.incrementCounter(-1);
                } finally {
                    parentNode.writeUnlock();
                }
                if (counterVal <= 0) {
                    if (!parentNode.deleteNode(e.key)) {
                        // TODO booo hiss
                    }
                }
//                  check.release();
            }
        }
    }


    @Override
    public boolean updateParentData(DataTreeNodeUpdater state, DataTreeNode parentNode,
            DataTreeNode childNode,
            List<TreeNodeDataDeferredOperation> deferredOps) {
        try {
            KeyTime e = new KeyTime();
            e.key = childNode.getName();
            if (timeKey != null) {
                Bundle p = state.getBundle();
                if (keyAccess == null) {
                    keyAccess = p.getFormat().getField(timeKey);
                }
                e.time = ValueUtil.asNumber(p.getValue(keyAccess)).asLong().getLong();
            } else {
                e.time = System.currentTimeMillis();
            }
            queue.addFirst(e);
            if ((size > 0 && queue.size() > size) || (age > 0 && e.time - queue.peekLast().time > age)) {
                if (sortQueue) {
                    Collections.sort(queue, new Comparator<KeyTime>() {
                        @Override
                        public int compare(KeyTime o, KeyTime o1) {
                            if (o.time > o1.time) {
                                return -1;
                            } else if (o.time < o1.time) {
                                return 1;
                            } else {
                                return 0;
                            }
                        }
                    });
                }
                e = queue.removeLast();
                deferredOps.add(new DataLimitRecentDeferredOperation(parentNode, e));
            }
        } catch (Exception e) {
            throw new RuntimeException(e);
        }
        return false;
    }

    @Override
    public ValueObject getValue(String key) {
        return ValueFactory.create(deleted);
    }
}


File: hydra-data/src/main/java/com/addthis/hydra/data/tree/prop/VirtualTreeNode.java
/*
 * Licensed under the Apache License, Version 2.0 (the "License");
 * you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at
 *
 * http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 */
package com.addthis.hydra.data.tree.prop;

import java.util.HashMap;
import java.util.NoSuchElementException;

import com.addthis.basis.util.ClosableIterator;

import com.addthis.hydra.data.tree.TreeNodeData;
import com.addthis.hydra.data.tree.concurrent.ConcurrentTreeNode;
import com.addthis.hydra.data.tree.DataTreeNode;

/**
 * phantom node created for reporting
 */
public final class VirtualTreeNode extends ConcurrentTreeNode {

    public VirtualTreeNode(final String name, final long hits) {
        this(name, hits, null);
    }

    public VirtualTreeNode(final String name, final long hits, final VirtualTreeNode[] children) {
        this.name = name;
        this.hits = hits;
        this.nodes = children != null ? children.length : 0;
        this.children = children;
    }

    private final VirtualTreeNode[] children;

    @Override
    public ClosableIterator<DataTreeNode> getNodeIterator() {
        return new VirtualTreeNodeIterator();
    }

    @Override
    public ClosableIterator<DataTreeNode> getNodeIterator(String prefix) {
        VirtualTreeNodeIterator iter = new VirtualTreeNodeIterator();
        while (true) {
            VirtualTreeNode peek = iter.peek();
            if ((peek == null) || peek.name.startsWith(prefix)) {
                break;
            }
            iter.next();
        }
        return iter;
    }

    @Override
    public ClosableIterator<DataTreeNode> getNodeIterator(String from, String to) {
        VirtualTreeNodeIterator iter = new VirtualTreeNodeIterator();
        iter.end = to;
        while (true) {
            VirtualTreeNode peek = iter.peek();
            if (peek == null || (peek.name.compareTo(from) >= 0) && (to == null || peek.name.compareTo(to) <= 0)) {
                break;
            }
            iter.next();
        }
        return iter;
    }

    @Override
    public ConcurrentTreeNode getNode(String name) {
        if (children == null || children.length == 0) {
            return null;
        }
        for (VirtualTreeNode vtn : children) {
            if (vtn.name.equals(name)) {
                return vtn;
            }
        }
        return null;
    }

    /**
     * Upgrade access modifier of this operation for VirtualTreeNodes.
     */
    @Override
    public HashMap<String, TreeNodeData> createMap() {
        return super.createMap();
    }

    private class VirtualTreeNodeIterator implements ClosableIterator<DataTreeNode> {

        int pos;
        String end;

        VirtualTreeNode peek() {
            return children != null && pos < children.length ? children[pos] : null;
        }

        @Override
        public void close() {
        }

        @Override
        public boolean hasNext() {
            if (children != null && pos < children.length) {
                if (end != null) {
                    return children[pos].name.compareTo(end) < 0;
                }
                return true;
            }
            return false;
        }

        @Override
        public VirtualTreeNode next() {
            if (!hasNext()) {
                throw new NoSuchElementException();
            }
            return children[pos++];
        }

        @Override
        public void remove() {
            throw new UnsupportedOperationException();
        }
    }
}


File: hydra-data/src/test/java/com/addthis/hydra/data/tree/concurrent/ConcurrentTreeConverter.java
/*
 * Licensed under the Apache License, Version 2.0 (the "License");
 * you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at
 *
 * http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 */
package com.addthis.hydra.data.tree.concurrent;

import java.io.File;

import java.util.Iterator;
import java.util.Map;

import com.addthis.basis.util.ClosableIterator;

import com.addthis.hydra.data.tree.DataTreeNode;
import com.addthis.hydra.data.tree.ReadTree;
import com.addthis.hydra.data.tree.ReadTreeNode;
import com.addthis.hydra.data.tree.TreeNodeData;
import com.addthis.hydra.store.db.CloseOperation;

public class ConcurrentTreeConverter {

    public static void main(String[] args) throws Exception {
        int maxNodes = (args.length >= 3) ? Integer.parseInt(args[2]) : -1;
        new ConcurrentTreeConverter(new File(args[0]), new File(args[1]), maxNodes);
    }

    public ConcurrentTreeConverter(File readRoot, File writeRoot, int maxNodes) throws Exception {
        long mark = System.currentTimeMillis();
        ReadTree readTree = new ReadTree(readRoot);
        ConcurrentTree writeTree = new ConcurrentTree(writeRoot);
        long openTime = System.currentTimeMillis() - mark;
        long testTime = 0;
        try {
            mark += openTime;
            ReadTreeNode readNode = readTree.getRootNode();
            ConcurrentTreeNode writeNode = writeTree.getRootNode();
            explore(writeTree, writeNode, readNode, 0, maxNodes);
            testTime = System.currentTimeMillis() - mark;
        } catch (Exception ex) {
            ex.printStackTrace();
            throw ex;
        } finally {
            readTree.close();
            writeTree.close(true, CloseOperation.NONE);
        }
        System.out.println("nodeCount=" + nodeCount + " hasNodes=" + hasNodes + " maxLeafs=" +
                           maxLeafs + " maxDepth=" + maxDepth + " openTime=" + openTime + " testTime=" + testTime);
    }

    private int nodeCount;
    private int maxLeafs;
    private int hasNodes;
    private int maxDepth;

    private void generateNode(ConcurrentTree writeTree,
            ConcurrentTreeNode writeParent,
            ReadTreeNode readChild) {
        ConcurrentTreeNode writeNode = writeTree.getOrCreateNode(writeParent, readChild.getName(), null);
        writeNode.writeLock();
        if (readChild.hasNodes()) {
            writeNode.requireNodeDB();
        }
        writeNode.setCounter(readChild.getCounter());
        Map<String, TreeNodeData> readMap = readChild.getDataMap();
        if (readMap != null) {
            Map<String, TreeNodeData> writeMap = writeNode.createMap();
            for (Map.Entry<String, TreeNodeData> entry : readMap.entrySet()) {
                writeMap.put(entry.getKey(), entry.getValue());
            }
        }
        writeNode.markChanged();
        writeNode.writeUnlock();
        writeNode.release();
    }

    private void explore(ConcurrentTree writeTree,
            ConcurrentTreeNode writeNode,
            ReadTreeNode readNode, int depth,
            int maxNodes) throws Exception {
        int count = 0;
        if (maxNodes > 0 && nodeCount >= maxNodes) {
            return;
        }
        Iterator<DataTreeNode> iter = readNode.iterator();
        if (iter != null) {
            if (iter.hasNext()) {
                hasNodes++;
            }
            try {
                while (iter.hasNext()) {
                    count++;
                    ReadTreeNode readChild = (ReadTreeNode) iter.next();
                    generateNode(writeTree, writeNode, readChild);
                }
            } finally {
                if (iter instanceof ClosableIterator) {
                    ((ClosableIterator<DataTreeNode>) iter).close();
                }
            }
            iter = readNode.iterator();
            try {
                while (iter.hasNext()) {
                    ReadTreeNode readChild = (ReadTreeNode) iter.next();
                    ConcurrentTreeNode writeChild = writeTree.getNode(writeNode, readChild.getName(), false);
                    explore(writeTree, writeChild, readChild, depth + 1, maxNodes);
                }
            } finally {
                if (iter instanceof ClosableIterator) {
                    ((ClosableIterator<DataTreeNode>) iter).close();
                }
            }
        }
        maxLeafs = Math.max(count, maxLeafs);
        maxDepth = Math.max(depth, maxDepth);
        nodeCount++;
        if (nodeCount % 10000000 == 0) {
            System.out.println(".. nodeCount=" + nodeCount + " hasNodes=" + hasNodes + " maxLeafs=" + maxLeafs + " maxDepth=" + maxDepth);
        }
    }
}


File: hydra-data/src/test/java/com/addthis/hydra/data/tree/concurrent/TestConcurrentTree.java
/*
 * Licensed under the Apache License, Version 2.0 (the "License");
 * you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at
 *
 * http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 */
package com.addthis.hydra.data.tree.concurrent;

import java.io.File;
import java.io.IOException;

import java.util.ArrayList;
import java.util.Collections;
import java.util.List;
import java.util.Random;
import java.util.concurrent.CyclicBarrier;

import com.addthis.basis.test.SlowTest;
import com.addthis.basis.util.ClosableIterator;
import com.addthis.basis.util.LessFiles;

import com.addthis.hydra.data.tree.DataTreeNode;
import com.addthis.hydra.store.db.CloseOperation;

import org.junit.Test;
import org.junit.experimental.categories.Category;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import static org.junit.Assert.assertEquals;
import static org.junit.Assert.assertNotNull;
import static org.junit.Assert.assertNull;
import static org.junit.Assert.assertTrue;
import static org.junit.Assert.fail;

public class TestConcurrentTree {

    private static final Logger log = LoggerFactory.getLogger(TestConcurrentTree.class);

    private static final CloseOperation close = CloseOperation.TEST;

    static final int fastNumElements = 10000;
    static final int fastNumThreads = 8;

    static final int slowNumElements = 100000;
    static final int slowNumThreads = 8;

    private File makeTemporaryDirectory() throws IOException {
        final File temp;

        temp = File.createTempFile("temp", Long.toString(System.nanoTime()));

        if (!(temp.delete())) {
            throw new IOException("Could not delete temp file: " + temp.getAbsolutePath());
        }

        if (!(temp.mkdir())) {
            throw new IOException("Could not create temp directory: " + temp.getAbsolutePath());
        }

        return temp;
    }

    static final class InsertionThread extends Thread {

        final CyclicBarrier barrier;
        final List<Integer> values;
        final List<Integer> threadId;
        final int myId;
        final ConcurrentTree cache;
        final ConcurrentTreeNode parent;
        int counter;

        public InsertionThread(CyclicBarrier barrier, List<Integer> values,
                List<Integer> threadId, int id, ConcurrentTree cache,
                ConcurrentTreeNode parent) {
            super("InsertionThread" + id);
            this.barrier = barrier;
            this.values = values;
            this.threadId = threadId;
            this.myId = id;
            this.cache = cache;
            this.counter = 0;
            this.parent = parent;
        }

        @Override
        public void run() {
            try {
                barrier.await();
                int len = threadId.size();
                for (int i = 0; i < len; i++) {
                    if (threadId.get(i) == myId) {
                        Integer val = values.get(i);
                        ConcurrentTreeNode node = cache.getOrCreateNode(parent,
                                Integer.toString(val), null);
                        node.release();
                        counter++;
                    }
                }
            } catch (Exception e) {
                e.printStackTrace();
                fail();
            }
        }

    }

    static final class DeletionThread extends Thread {

        final CyclicBarrier barrier;
        final List<Integer> values;
        final List<Integer> threadId;
        final int myId;
        final ConcurrentTree cache;
        final ConcurrentTreeNode parent;
        int counter;

        public DeletionThread(CyclicBarrier barrier, List<Integer> values,
                List<Integer> threadId, int id, ConcurrentTree cache,
                ConcurrentTreeNode parent) {
            super("DeletionThread" + id);
            this.barrier = barrier;
            this.values = values;
            this.threadId = threadId;
            this.myId = id;
            this.cache = cache;
            this.counter = 0;
            this.parent = parent;
        }

        @Override
        public void run() {
            try {
                barrier.await();
                int len = threadId.size();
                for (int i = 0; i < len; i++) {
                    if (threadId.get(i) == myId) {
                        Integer val = values.get(i);
                        cache.deleteNode(parent, Integer.toString(val));
                        counter++;
                    }
                }
            } catch (Exception e) {
                e.printStackTrace();
                fail();
            }
        }
    }

    @Test
    @Category(SlowTest.class)
    public void getOrCreateOneThreadIterations() throws Exception {
        for(int i = 0; i < 100; i++) {
            getOrCreateOneThread();
        }
    }

    @Test
    public void getOrCreateOneThread() throws Exception {
        log.info("getOrCreateOneThread");
        File dir = makeTemporaryDirectory();
        try {
            ConcurrentTree tree = new Builder(dir).build();
            ConcurrentTreeNode root = tree.getRootNode();
            for (int i = 0; i < 1000; i++) {
                ConcurrentTreeNode node = tree.getOrCreateNode(root, Integer.toString(i), null);
                assertNotNull(node);
                assertEquals(Integer.toString(i), node.getName());
                node.release();
            }
            for (int i = 0; i < 1000; i++) {
                ConcurrentTreeNode node = tree.getNode(root, Integer.toString(i), true);
                assertNotNull(node);
                assertEquals(1, node.getLeaseCount());
                assertEquals(Integer.toString(i), node.getName());
                node.release();
            }
            tree.close(false, close);
        } finally {
            if (dir != null) {
                LessFiles.deleteDir(dir);
            }
        }
    }

    @Test
    public void recursiveDeleteOneThread() throws Exception {
        log.info("recursiveDeleteOneThread");
        File dir = makeTemporaryDirectory();
        try {
            ConcurrentTree tree = new Builder(dir).build();
            ConcurrentTreeNode root = tree.getRootNode();
            ConcurrentTreeNode parent = tree.getOrCreateNode(root, "hello", null);
            for (int i = 0; i < (TreeCommonParameters.cleanQMax << 1); i++) {
                ConcurrentTreeNode child = tree.getOrCreateNode(parent, Integer.toString(i), null);
                assertNotNull(child);
                assertEquals(Integer.toString(i), child.getName());
                parent.release();
                parent = child;
            }
            parent.release();

            assertEquals(1, root.getNodeCount());
            assertEquals(TreeCommonParameters.cleanQMax, tree.getCache().size());

            tree.deleteNode(root, "hello");
            tree = waitForDeletion(tree, dir);
            assertEquals(2, tree.getCache().size());
            assertEquals(0, root.getNodeCount());
            assertTrue(tree.getTreeTrashNode().getCounter() >= 1);
            assertEquals(tree.getTreeTrashNode().getCounter(), tree.getTreeTrashNode().getNodeCount());
            tree.close(false, close);
        } finally {
            if (dir != null) {
                LessFiles.deleteDir(dir);
            }
        }
    }

    @Test
    public void recursiveDeleteMultiThreads() throws Exception {
        log.info("recursiveDeleteMultiThreads");
        File dir = makeTemporaryDirectory();
        try {
            ConcurrentTree tree = new Builder(dir).
                    numDeletionThreads(8).build();
            ConcurrentTreeNode root = tree.getRootNode();
            for (int i = 0; i < fastNumThreads; i++) {
                ConcurrentTreeNode parent = tree.getOrCreateNode(root, Integer.toString(i), null);
                for (int j = 0; j < TreeCommonParameters.cleanQMax; j++) {
                    ConcurrentTreeNode child = tree.getOrCreateNode(parent, Integer.toString(j), null);
                    assertNotNull(child);
                    assertEquals(Integer.toString(j), child.getName());
                    parent.release();
                    parent = child;
                }
                parent.release();
            }

            assertEquals(TreeCommonParameters.cleanQMax, tree.getCache().size());

            assertEquals(fastNumThreads, root.getNodeCount());

            for (int i = 0; i < fastNumThreads; i++) {
                tree.deleteNode(root, Integer.toString(i));
            }

            tree = waitForDeletion(tree, dir);
            assertEquals(2, tree.getCache().size());
            assertEquals(0, root.getNodeCount());

            tree.close(false, close);
        } finally {
            if (dir != null) {
                LessFiles.deleteDir(dir);
            }
        }
    }

    @Test
    public void getOrCreateFast() throws Exception {
        getOrCreateMultiThread(fastNumElements, fastNumThreads);
    }

    @Test
    @Category(SlowTest.class)
    public void getOrCreateSlow() throws Exception {
        getOrCreateMultiThread(slowNumElements, slowNumThreads);
    }

    private void getOrCreateMultiThread(int numElements, int numThreads) throws Exception {
        log.info("getOrCreateMultiThread");
        File dir = makeTemporaryDirectory();
        try {
            ArrayList<Integer> values = new ArrayList<>(numElements);
            final CyclicBarrier barrier = new CyclicBarrier(numThreads);
            ArrayList<Integer> threadId = new ArrayList<>(numElements);
            InsertionThread[] threads = new InsertionThread[numThreads];
            ConcurrentTree tree = new Builder(dir).build();
            ConcurrentTreeNode root = tree.getRootNode();

            for (int i = 0; i < numElements; i++) {
                values.add(i);
                threadId.add(i % numThreads);
            }

            for (int i = 0; i < numThreads; i++) {
                threads[i] = new InsertionThread(barrier, values, threadId, i, tree, root);
            }

            Collections.shuffle(values);

            for (int i = 0; i < numThreads; i++) {
                threads[i].start();
            }

            for (int i = 0; i < numThreads; i++) {
                threads[i].join();
            }

            for (int i = 0; i < numThreads; i++) {
                assertEquals(numElements / numThreads, threads[i].counter);
            }

            for (int i = 0; i < numElements; i++) {
                ConcurrentTreeNode node = tree.getNode(root, Integer.toString(i), true);
                assertNotNull(node);
                assertEquals(1, node.getLeaseCount());
                assertEquals(Integer.toString(i), node.getName());
                node.release();
            }
            tree.close(false, close);
        } finally {
            if (dir != null) {
                LessFiles.deleteDir(dir);
            }
        }
    }

    @Test
    public void deleteOneThreadForeground() throws Exception {
        log.info("deleteOneThreadForeground");
        deleteOneThread(0);
    }

    @Test
    public void deleteOneThreadBackground() throws Exception {
        log.info("deleteOneThreadBackground");
        deleteOneThread(fastNumThreads);
    }

    private void deleteOneThread(int numDeletionThreads) throws Exception {
        File dir = makeTemporaryDirectory();
        try {
            ConcurrentTree tree = new Builder(dir)
                    .numDeletionThreads(numDeletionThreads).build();
            ConcurrentTreeNode root = tree.getRootNode();
            for (int i = 0; i < 1000; i++) {
                ConcurrentTreeNode node = tree.getOrCreateNode(root, Integer.toString(i), null);
                assertNotNull(node);
                assertEquals(1, node.getLeaseCount());
                assertEquals(Integer.toString(i), node.getName());
                ConcurrentTreeNode child = tree.getOrCreateNode(node, Integer.toString(i), null);
                child.release();
                node.release();
            }
            for (int i = 0; i < 1000; i++) {
                tree.deleteNode(root, Integer.toString(i));
            }
            for (int i = 0; i < 1000; i++) {
                ConcurrentTreeNode node = tree.getNode(root, Integer.toString(i), false);
                assertNull(node);
            }
            tree = waitForDeletion(tree, dir);
            assertTrue(tree.getTreeTrashNode().getCounter() >= 1000);
            assertEquals(tree.getTreeTrashNode().getCounter(), tree.getTreeTrashNode().getNodeCount());
            tree.close(false, close);
        } finally {
            if (dir != null) {
                LessFiles.deleteDir(dir);
            }
        }
    }

    /**
     * Test the foreground deletion by closing the existing tree, reopening
     * the tree with 0 deletion threads, and the performing deletion
     * in the foreground.
     *
     * @param tree input tree
     * @param dir  directory containing database of the input tree
     * @return reopened copy of the input tree
     * @throws Exception
     */
    private ConcurrentTree waitForDeletion(ConcurrentTree tree, File dir) throws Exception {
        tree.close();
        tree = new Builder(dir).numDeletionThreads(0).build();
        tree.foregroundNodeDeletion(() -> false);
        return tree;
    }

    @Test
    public void deleteFast() throws Exception {
        deleteMultiThread(fastNumElements, fastNumThreads, fastNumThreads);
        deleteMultiThread(fastNumElements, fastNumThreads, 0);
    }

    @Test
    @Category(SlowTest.class)
    public void deleteSlow1() throws Exception {
        deleteMultiThread(slowNumElements, slowNumThreads, slowNumThreads);
        deleteMultiThread(slowNumElements, slowNumThreads, 0);
    }

    @Test
    @Category(SlowTest.class)
    public void deleteSlow2() throws Exception {
        for(int i = 0 ; i < 100; i++) {
            deleteMultiThread(fastNumElements, fastNumThreads, fastNumThreads);
            deleteMultiThread(fastNumElements, fastNumThreads, 0);
        }
    }

    @Test
    @Category(SlowTest.class)
    public void iterateAndDeleteSlow() throws Exception {
        for(int i = 0; i < 100; i++) {
            iterateAndDelete(fastNumThreads, 1000);
        }
    }

    @Test
    public void iterateAndDeleteFast() throws Exception {
        iterateAndDelete(fastNumThreads, 1000);
    }

    private void iterateAndDelete(int numThreads, int numElements) throws Exception {
        log.info("iterateAndDelete {} {}", numThreads, numElements);
        File dir = makeTemporaryDirectory();
        try {
            ConcurrentTree tree = new Builder(dir).numDeletionThreads(numThreads).
                    maxPageSize(5).maxCacheSize(500).build();
            ConcurrentTreeNode root = tree.getRootNode();

            for (int i = 0; i < numElements; i++) {
                ConcurrentTreeNode node = tree.getOrCreateNode(root, Integer.toString(i), null);
                assertNotNull(node);
                assertEquals(Integer.toString(i), node.getName());
                ConcurrentTreeNode child = tree.getOrCreateNode(node, Integer.toString(i), null);
                child.release();
                node.release();
            }

            Random rng = new Random();

            ClosableIterator<DataTreeNode> iterator = tree.getIterator();
            try {
                int counter = 0;
                while(iterator.hasNext()) {
                    DataTreeNode node = iterator.next();
                    if (rng.nextFloat() < 0.8) {
                        String name = node.getName();
                        tree.deleteNode(root, name);
                        counter++;
                    }
                }
                log.info("Deleted " + (((float) counter) / numElements * 100.0) + " % of nodes");
            } finally {
                iterator.close();
            }

            tree.close(false, close);

        } finally {
            if (dir != null) {
                LessFiles.deleteDir(dir);
            }
        }

    }

    private void deleteMultiThread(int numElements, int numThreads, int numDeletionThreads) throws Exception {
        log.info("deleteMultiThread {} {} {}", numElements, numThreads, numDeletionThreads);
        File dir = makeTemporaryDirectory();
        try {
            ArrayList<Integer> values = new ArrayList<>(numElements);
            final CyclicBarrier barrier = new CyclicBarrier(numThreads);
            ArrayList<Integer> threadId = new ArrayList<>(numElements);
            DeletionThread[] threads = new DeletionThread[numThreads];
            ConcurrentTree tree = new Builder(dir)
                    .numDeletionThreads(numDeletionThreads).build();
            ConcurrentTreeNode root = tree.getRootNode();

            for (int i = 0; i < numElements; i++) {
                values.add(i);
                threadId.add(i % numThreads);
                ConcurrentTreeNode node = tree.getOrCreateNode(root, Integer.toString(i), null);
                assertNotNull(node);
                assertEquals(Integer.toString(i), node.getName());
                ConcurrentTreeNode child = tree.getOrCreateNode(node, Integer.toString(i), null);
                child.release();
                node.release();
            }

            for (int i = 0; i < numThreads; i++) {
                threads[i] = new DeletionThread(barrier, values, threadId, i, tree, root);
            }

            Collections.shuffle(values);

            for (int i = 0; i < numThreads; i++) {
                threads[i].start();
            }

            for (int i = 0; i < numThreads; i++) {
                threads[i].join();
            }

            for (int i = 0; i < numThreads; i++) {
                assertEquals(numElements / numThreads, threads[i].counter);
            }

            for (int i = 0; i < numElements; i++) {
                ConcurrentTreeNode node = tree.getNode(root, Integer.toString(i), true);
                assertNull(node);
            }
            tree = waitForDeletion(tree, dir);
            assertTrue(tree.getTreeTrashNode().getCounter() >= numElements);
            assertEquals(tree.getTreeTrashNode().getCounter(), tree.getTreeTrashNode().getNodeCount());
            tree.close(false, close);
        } finally {
            if (dir != null) {
                LessFiles.deleteDir(dir);
            }
        }
    }

    @Test
    public void maximumNodeIdentifier() throws Exception {
        File dir = makeTemporaryDirectory();
        try {
            ConcurrentTree tree = new Builder(dir).build();
            ConcurrentTreeNode root = tree.getRootNode();
            for (int i = 0; i < 1000; i++) {
                ConcurrentTreeNode node = tree.getOrCreateNode(root, Integer.toString(i), null);
                assertNotNull(node);
                assertEquals(1, node.getLeaseCount());
                assertEquals(Integer.toString(i), node.getName());
                ConcurrentTreeNode child = tree.getOrCreateNode(node, Integer.toString(i), null);
                child.release();
                node.release();
            }
            assertTrue(tree.setNextNodeDB(Integer.MAX_VALUE));
            for (int i = 1000; i < 2000; i++) {
                ConcurrentTreeNode node = tree.getOrCreateNode(root, Integer.toString(i), null);
                assertNotNull(node);
                assertEquals(1, node.getLeaseCount());
                assertEquals(Integer.toString(i), node.getName());
                ConcurrentTreeNode child = tree.getOrCreateNode(node, Integer.toString(i), null);
                child.release();
                node.release();
            }
            tree.close(false, close);
        } finally {
            if (dir != null) {
                LessFiles.deleteDir(dir);
            }
        }
    }

}


File: hydra-data/src/test/java/com/addthis/hydra/data/tree/concurrent/TestTreeSerializationVersions.java
/*
 * Licensed under the Apache License, Version 2.0 (the "License");
 * you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at
 *
 * http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 */
package com.addthis.hydra.data.tree.concurrent;

import java.io.File;
import java.io.IOException;

import java.util.Map;

import com.addthis.basis.util.LessFiles;

import com.addthis.hydra.data.tree.TreeNodeData;
import com.addthis.hydra.data.tree.prop.DataTime;
import com.addthis.hydra.store.db.CloseOperation;
import com.addthis.hydra.store.skiplist.LegacyPage;
import com.addthis.hydra.store.skiplist.Page;

import org.junit.Test;

import static org.junit.Assert.assertEquals;
import static org.junit.Assert.assertNotNull;
import static org.junit.Assert.assertTrue;

public class TestTreeSerializationVersions {

    private static final CloseOperation close = CloseOperation.TEST;

    private File makeTemporaryDirectory() throws IOException {
        final File temp;

        temp = File.createTempFile("temp", Long.toString(System.nanoTime()));

        if (!(temp.delete())) {
            throw new IOException("Could not delete temp file: " + temp.getAbsolutePath());
        }

        if (!(temp.mkdir())) {
            throw new IOException("Could not create temp directory: " + temp.getAbsolutePath());
        }

        return temp;
    }

    @Test
    public void legacyToSparseUpgradePath() throws Exception {
        File dir = makeTemporaryDirectory();
        try {
            int count = 1000;
            ConcurrentTree tree = new Builder(dir).
                    pageFactory(LegacyPage.LegacyPageFactory.singleton).build();
            ConcurrentTreeNode root = tree.getRootNode();
            /**
             * write count nodes that have a time data attachment. Use the legacy page encoding.
             */
            for (int i = 0; i < count; i++) {
                ConcurrentTreeNode node = tree.getOrCreateNode(root, Integer.toString(i), null);
                assertNotNull(node);
                assertEquals(Integer.toString(i), node.getName());
                DataTime attachment = new DataTime();
                attachment.setFirst(i);
                attachment.setLast(i + count);
                node.createMap().put("time", attachment);
                node.markChanged();
                node.release();
            }
            tree.close(false, close);
            tree = new Builder(dir).
                    pageFactory(Page.DefaultPageFactory.singleton).build();
            /**
             * Sanity check. Read the count notes and look for the data attachment.
             */
            for (int i = 0; i < count; i++) {
                ConcurrentTreeNode node = tree.getNode(root, Integer.toString(i), true);
                assertNotNull(node);
                assertEquals(1, node.getLeaseCount());
                assertEquals(Integer.toString(i), node.getName());
                Map<String, TreeNodeData> attachments = node.getDataMap();
                assertNotNull(attachments);
                assertTrue(attachments.containsKey("time"));
                DataTime attachment = (DataTime) attachments.get("time");
                assertEquals(i, attachment.first());
                assertEquals(i + count, attachment.last());
                node.release();
            }
            tree.close(false, close);
            tree = new Builder(dir).
                    pageFactory(Page.DefaultPageFactory.singleton).build();
            /**
             * Only on even nodes update the data attachment.
             * Use the new page encoding.
             */
            for (int i = 0; i < count; i += 2) {
                ConcurrentTreeNode node = tree.getNode(root, Integer.toString(i), true);
                assertNotNull("i = " + i, node);
                assertEquals(Integer.toString(i), node.getName());
                node.setCounter(1);
                DataTime attachment = new DataTime();
                attachment.setFirst(2 * i);
                attachment.setLast(2 * i + count);
                node.createMap().put("time", attachment);
                node.markChanged();
                node.release();
            }
            tree.close(false, close);
            tree = new Builder(dir).
                    pageFactory(Page.DefaultPageFactory.singleton).build();
            /**
             * Read all the nodes and verify that the data attachments are correct.
             */
            for (int i = 0; i < count; i++) {
                ConcurrentTreeNode node = tree.getNode(root, Integer.toString(i), true);
                assertNotNull(node);
                assertEquals(1, node.getLeaseCount());
                assertEquals(Integer.toString(i), node.getName());
                Map<String, TreeNodeData> attachments = node.getDataMap();
                assertNotNull(attachments);
                assertTrue(attachments.containsKey("time"));
                DataTime attachment = (DataTime) attachments.get("time");
                if (i % 2 == 0) {
                    assertEquals(2 * i, attachment.first());
                    assertEquals(2 * i + count, attachment.last());
                } else {
                    assertEquals(i, attachment.first());
                    assertEquals(i + count, attachment.last());
                }
                node.release();
            }
        } finally {
            if (dir != null) {
                LessFiles.deleteDir(dir);
            }
        }
    }


}


File: hydra-task/src/main/java/com/addthis/hydra/task/output/tree/PathAlias.java
/*
 * Licensed under the Apache License, Version 2.0 (the "License");
 * you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at
 *
 * http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 */
package com.addthis.hydra.task.output.tree;

import com.addthis.basis.util.LessStrings;

import com.addthis.bundle.util.ValueUtil;
import com.addthis.codec.annotations.FieldConfig;
import com.addthis.hydra.data.tree.DataTreeNode;
import com.addthis.hydra.data.tree.DataTreeNodeInitializer;
import com.addthis.hydra.data.tree.DataTreeUtil;

/**
 * This {@link PathElement PathElement} <span class="hydra-summary">creates a reference to another existing node in the tree</span>.
 * <p/>
 * <p>The location of the target node is specified as a path
 * to the target node using the 'path' parameter. By default the traversal
 * to the target node begins at the root of the tree. If the 'peer' parameter
 * is set then the tree traversal begins at the current location. If the 'relativeUp'
 * parameter is a positive integer then the tree traversal begins with
 * an ancestor of the current location. The 'peer' and the 'relativeUp' parameters
 * are incompatible with each other: if 'peer' is set to true then the 'relativeUp'
 * parameter is ignored.</p>
 * <p>Compare this path element to the '{@link PathCall call}' path element.
 * 'call' does not create a reference to an existing path element but instead
 * creates a copy of a path element.</p>
 * </p>
 * <p>Example:</p>
 * <pre>
 *  {alias {
 *      key:"DATE_YMD"
 *      data.uid.count {ver:"hll", rsd:0.05, key:"UID"}
 *      relativeUp:1
 *      path:[
 *          {const:"ymd"}
 *          {field:"DATE_YMD"}
 *      ]
 *  }}
 * </pre>
 *
 * @user-reference
 */
public class PathAlias extends PathKeyValue {

    /**
     * Path traversal to the target node. This field is required.
     */
    @FieldConfig(codable = true, required = true)
    protected PathValue[] path;

    /**
     * When traversing the tree in search of the target node,
     * if this parameter is a positive integer then begin
     * the traversal this many levels higher than the
     * current location. If {@linkplain #peer} is true
     * then this parameter is ignored. Default is zero.
     */
    @FieldConfig(codable = true)
    protected int relativeUp;

    /**
     * When traversing the tree in search of the target node,
     * if this flag is true then begin the traversal at
     * current location. Default is false.
     */
    @FieldConfig(codable = true)
    protected boolean peer;

    /**
     * When true the alias acts like a filesystem hard link.
     * The target of the link is identified the first time
     * the alias is accessed. On subsequent access the target node
     * is retrieved immediately without traversing through the tree.
     * When this parameter is false the alias will re-traverse through
     * the tree to find the target of the link upon every access.
     * If you know the target node will never be deleted then you
     * should set this parameter to true for improved performance.
     * Default is false.
     */
    @FieldConfig(codable = true)
    protected boolean hard;

    /**
     * Default is false.
     */
    @FieldConfig(codable = true)
    protected int debug;

    /**
     * Default is null.
     */
    @FieldConfig(codable = true)
    private String debugKey;

    private int match;
    private int miss;

    public PathAlias() {
    }

    public PathAlias(PathValue[] path) {
        this.path = path;
    }

    @Override
    public void resolve(TreeMapper mapper) {
        super.resolve(mapper);
        for (PathValue pv : path) {
            pv.resolve(mapper);
        }
    }

    @Override
    public DataTreeNode getOrCreateNode(final TreeMapState state, final String name) {
        if (hard) {
            DataTreeNode node = state.getLeasedNode(name);
            if (node != null) {
                return node;
            }
        }
        String[] p = new String[path.length];
        for (int i = 0; i < p.length; i++) {
            p[i] = ValueUtil.asNativeString(path[i].getFilteredValue(state));
        }
        DataTreeNode alias = null;
        if (peer) {
            alias = DataTreeUtil.pathLocateFrom(state.current(), p);
        } else if (relativeUp > 0) {
            alias = DataTreeUtil.pathLocateFrom(state.peek(relativeUp), p);
        } else {
            alias = DataTreeUtil.pathLocateFrom(state.current().getTreeRoot(), p);
        }
        if (alias != null) {
            final DataTreeNode finalAlias = alias;
            DataTreeNodeInitializer init = new DataTreeNodeInitializer() {
                @Override
                public void onNewNode(DataTreeNode child) {
                    child.aliasTo(finalAlias);
                    state.onNewNode(child);
                }
            };
            if (debug > 0) {
                debug(true);
            }
            return state.getOrCreateNode(name, init);
        } else {
            if (debug > 0) {
                debug(false);
            }
            if (log.isDebugEnabled() || debug == 1) {
                log.warn("alias fail, missing " + LessStrings.join(p, " / "));
            }
            return null;
        }
    }

    protected synchronized void debug(boolean hit) {
        if (hit) {
            match++;
        } else {
            miss++;
        }
        if (match + miss >= debug) {
            log.warn("query[" + debugKey + "]: match=" + match + " miss=" + miss);
            match = 0;
            miss = 0;
        }
    }
}


File: hydra-task/src/main/java/com/addthis/hydra/task/output/tree/PathValue.java
/*
 * Licensed under the Apache License, Version 2.0 (the "License");
 * you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at
 *
 * http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 */
package com.addthis.hydra.task.output.tree;

import java.util.ArrayList;
import java.util.List;

import com.addthis.bundle.core.BundleField;
import com.addthis.bundle.util.ValueUtil;
import com.addthis.bundle.value.ValueFactory;
import com.addthis.bundle.value.ValueMap;
import com.addthis.bundle.value.ValueMapEntry;
import com.addthis.bundle.value.ValueObject;
import com.addthis.bundle.value.ValueString;
import com.addthis.codec.annotations.FieldConfig;
import com.addthis.hydra.data.filter.value.ValueFilter;
import com.addthis.hydra.data.tree.DataTreeNode;

/**
 * This {@link PathElement PathElement} <span class="hydra-summary">creates a single node with a specified value</span>.
 * <p/>
 * <p>Compare this path element to the "{@link PathKeyValue value}" path element. "value" creates one
 * or more nodes with a specified key.</p>
 * <p/>
 * <p>Example:</p>
 * <pre>paths : {
 *   "ROOT" : [
 *     {type:"const", value:"date"},
 *     {type:"value", key:"DATE_YMD"},
 *     {type:"value", key:"DATE_HH"},
 *   ],
 * },</pre>
 *
 * @user-reference
 */
public class PathValue extends PathElement {

    public PathValue() {
    }

    public PathValue(String value) {
        this.value = value;
    }

    public PathValue(String value, boolean count) {
        this.value = value;
        this.count = count;
    }

    /**
     * Value to be stored in the constructed node.
     */
    @FieldConfig(codable = true)
    protected String value;

    @FieldConfig(codable = true)
    protected String set;

    @FieldConfig(codable = true)
    protected ValueFilter vfilter;

    @FieldConfig(codable = true)
    protected boolean sync;

    @FieldConfig(codable = true)
    protected boolean create = true;

    @FieldConfig(codable = true)
    protected boolean once;

    @FieldConfig(codable = true)
    protected String mapTo;

    /** Deletes a node before attempting to (re)create or update it. Pure deletion requires {@code create: false}. */
    @FieldConfig protected boolean delete;

    @FieldConfig(codable = true)
    protected boolean push;

    @FieldConfig(codable = true)
    protected PathElement each;

    /**
     * If positive then limit the number of nodes that can be created.
     * Multiple threads may be writing to the tree concurrently.
     * Therefore this limit is a best-effort limit it is not a strict
     * guarantee. Default is zero.
     **/
    @FieldConfig(codable = true)
    protected int maxNodes = 0;

    private ValueString valueString;
    private BundleField setField;
    private BundleField mapField;

    public final ValueObject value() {
        if (valueString == null) {
            valueString = ValueFactory.create(value);
        }
        return valueString;
    }

    /**
     * override in subclasses
     */
    public ValueObject getPathValue(final TreeMapState state) {
        return value();
    }

    public final ValueObject getFilteredValue(final TreeMapState state) {
        ValueObject value = getPathValue(state);
        if (vfilter != null) {
            value = vfilter.filter(value, state.getBundle());
        }
        return value;
    }

    @Override
    public void resolve(final TreeMapper mapper) {
        super.resolve(mapper);
        if (set != null) {
            setField = mapper.bindField(set);
        }
        if (mapTo != null) {
            mapField = mapper.bindField(mapTo);
        }
        if (each != null) {
            each.resolve(mapper);
        }
    }

    @Override
    public String toString() {
        return "PathValue[" + value + "]";
    }

    /**
     * prevent subclasses from overriding as this is not used from here on
     */
    @Override
    public final List<DataTreeNode> getNextNodeList(final TreeMapState state) {
        ValueObject value = getFilteredValue(state);
        if (setField != null) {
            state.getBundle().setValue(setField, value);
        }
        if (ValueUtil.isEmpty(value)) {
            return op ? TreeMapState.empty() : null;
        }
        if (op) {
            return TreeMapState.empty();
        }
        List<DataTreeNode> list;
        if (sync) {
            synchronized (this) {
                list = processNodeUpdates(state, value);
            }
        } else {
            list = processNodeUpdates(state, value);
        }
        if (term) {
            if (list != null) {
                list.forEach(DataTreeNode::release);
            }
            return null;
        } else {
            return list;
        }
    }

    /**
     * Either get an existing node or optionally create a new node
     * if one does not exist. The {@link #create} field determines
     * whether or not to create a new node. If {@link #maxNodes}
     * is a positive integer then test the current node count
     * to determine whether to create a new node.
     *
     * @param state   current state
     * @param name    name of target node
     * @return existing node or newly created node
     */
    public DataTreeNode getOrCreateNode(TreeMapState state, String name) {
        if (create && ((maxNodes == 0) || (state.getNodeCount() < maxNodes))) {
            return state.getOrCreateNode(name, state);
        } else {
            return state.getLeasedNode(name);
        }
    }

    /**
     * override this in subclasses. the rules for this path element are to be
     * applied to the child (next node) of the parent (current node).
     */
    public List<DataTreeNode> processNodeUpdates(TreeMapState state, ValueObject name) {
        List<DataTreeNode> list = new ArrayList<>(1);
        int pushed = 0;
        if (name.getObjectType() == ValueObject.TYPE.ARRAY) {
            for (ValueObject o : name.asArray()) {
                if (o != null) {
                    pushed += processNodeByValue(list, state, o);
                }
            }
        } else if (name.getObjectType() == ValueObject.TYPE.MAP) {
            ValueMap nameAsMap = name.asMap();
            for (ValueMapEntry e : nameAsMap) {
                String key = e.getKey();
                if (mapTo != null) {
                    state.getBundle().setValue(mapField, e.getValue());
                    pushed += processNodeByValue(list, state, ValueFactory.create(key));
                } else {
                    PathValue mapValue = new PathValue(key, count);
                    List<DataTreeNode> tnl = mapValue.processNode(state);
                    if (tnl != null) {
                        state.push(tnl);
                        List<DataTreeNode> children = processNodeUpdates(state, e.getValue());
                        if (children != null) {
                            list.addAll(children);
                        }
                        state.pop().release();
                    }
                }
            }
        } else {
            pushed += processNodeByValue(list, state, name);
        }
        while (pushed-- > 0) {
            state.pop().release();
        }
        if (!list.isEmpty()) {
            return list;
        } else {
            return null;
        }
    }

    /**
     * can be called by subclasses to create/update nodes
     */
    public final int processNodeByValue(List<DataTreeNode> list, TreeMapState state, ValueObject name) {
        if (each != null) {
            List<DataTreeNode> next = state.processPathElement(each);
            if (push) {
                if (next.size() > 1) {
                    throw new RuntimeException("push and each are incompatible for > 1 return nodes");
                }
                if (next.size() == 1) {
                    state.push(next.get(0));
                    return 1;
                }
            } else if (next != null) {
                list.addAll(next);
            }
            return 0;
        }
        DataTreeNode parent = state.current();
        String sv = ValueUtil.asNativeString(name);
        if (delete) {
            parent.deleteNode(sv);
        }
        /** get db for parent node once we're past it (since it has children) */
        DataTreeNode child = getOrCreateNode(state, sv);
        boolean isnew = state.getAndClearLastWasNew();
        /** can be null if parent is deleted by another thread or if create == false */
        if (child == null) {
            return 0;
        }
        /* bail if only new nodes are required */
        if (once && !isnew) {
            child.release();
            return 0;
        }
        try {
            /** child node accounting and custom data updates */
            if (assignHits()) {
                state.setAssignmentValue(hitsField.getLong(state.getBundle()).orElse(0l));
            }
            child.updateChildData(state, this);
            /** update node data accounting */
            parent.updateParentData(state, child, isnew);
            if (push) {
                state.push(child);
                return 1;
            } else {
                list.add(child);
                return 0;
            }
        } catch (Throwable t) {
            child.release();
            throw t;
        }
    }
}


File: hydra-task/src/main/java/com/addthis/hydra/task/output/tree/TreeMapState.java
/*
 * Licensed under the Apache License, Version 2.0 (the "License");
 * you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at
 *
 * http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 */
package com.addthis.hydra.task.output.tree;

import javax.annotation.Nullable;

import java.util.ArrayList;
import java.util.Collections;
import java.util.LinkedList;
import java.util.List;

import com.addthis.basis.util.LessStrings;

import com.addthis.bundle.core.Bundle;
import com.addthis.bundle.core.BundleFactory;
import com.addthis.bundle.core.BundleFormat;
import com.addthis.bundle.core.BundleFormatted;
import com.addthis.hydra.data.tree.DataTreeNode;
import com.addthis.hydra.data.tree.DataTreeNodeInitializer;
import com.addthis.hydra.data.tree.DataTreeNodeUpdater;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
@SuppressWarnings("serial")
public final class TreeMapState implements DataTreeNodeUpdater, DataTreeNodeInitializer, BundleFactory, BundleFormatted {

    private static final Logger log = LoggerFactory.getLogger(TreeMapState.class);
    private static final int debug = Integer.parseInt(System.getProperty("hydra.process.debug", "0"));
    private static final boolean debugthread = System.getProperty("hydra.process.debugthread", "0").equals("1");
    // TODO: remove any uses of reference equality to this value and redefine as a proper empty list
    private static final List<DataTreeNode> empty = Collections.unmodifiableList(new ArrayList<>());

    static {
        if (debugthread) {
            log.warn("ENABLED debugthread");
        }
    }

    /**
     * test harness constructor
     */
    public TreeMapState(Bundle p) {
        this.bundle = p;
        this.path = null;
        this.processor = null;
        this.stack = null;
        this.thread = null;
        this.profiling = false;
    }

    /** */
    public TreeMapState(TreeMapper processor, DataTreeNode rootNode, PathElement[] path, Bundle bundle) {
        this.path = path;
        this.bundle = bundle;
        this.processor = processor;
        this.countValue = 1;
        this.stack = new LinkedList<>();
        this.thread = Thread.currentThread();
        this.profiling = processor != null ? processor.isProfiling() : false;
        push(rootNode);
    }

    private final LinkedList<DataTreeNode> stack;
    private final TreeMapper processor;
    private final PathElement[] path;
    private final Bundle bundle;
    private final Thread thread;
    private final boolean profiling;

    private boolean lastWasNew;
    private int touched;
    private int countValue;
    private long assignmentValue;

    private void checkThread() {
        if (Thread.currentThread() != thread) {
            throw new RuntimeException("invalid accessing thread " + Thread.currentThread() + " != " + thread);
        }
    }

    public static List<DataTreeNode> empty() {
        return empty;
    }

    @Override
    public int getCountValue() {
        return countValue;
    }

    public void setCountValue(int v) {
        countValue = v;
    }

    @Override
    public long getAssignmentValue() {
        return assignmentValue;
    }

    public TreeMapState setAssignmentValue(long assignmentValue) {
        this.assignmentValue = assignmentValue;
        return this;
    }

    public boolean getAndClearLastWasNew() {
        boolean ret = lastWasNew;
        lastWasNew = false;
        return ret;
    }

    public DataTreeNode getLeasedNode(String key) {
        DataTreeNode tn = current().getLeasedNode(key);
        return tn;
    }

    public DataTreeNode getOrCreateNode(String key, DataTreeNodeInitializer init) {
        DataTreeNode tn = current().getOrCreateNode(key, init);
        return tn;
    }

    public DataTreeNode pop() {
        if (debugthread) {
            checkThread();
        }
        return stack.pop();
    }

    public int getNodeCount() {
        return current().getNodeCount();
    }

    public void push(List<DataTreeNode> tnl) {
        if (tnl.size() == 1) {
            push(tnl.get(0));
        } else {
            throw new RuntimeException("unexpected response: " + tnl.size() + " -> " + tnl);
        }
    }

    public void push(DataTreeNode tn) {
        if (debugthread) {
            checkThread();
        }
        stack.push(tn);
    }

    /** */
    public long getBundleTime() {
        throw new RuntimeException("fix me");
    }

    public void setBundleTime(long time) {
        throw new RuntimeException("fix me");
    }

    /** */
    public DataTreeNode peek(int back) {
        return (stack.size() > back) ? stack.get(back) : null;
    }

    /** */
    public DataTreeNode current() {
        return stack.peek();
    }

    @Override
    public Bundle getBundle() {
        return bundle;
    }

    /** */
    public int touched() {
        return touched;
    }

    /**
     * used by path elements to schedule delivering the current bundle to a new
     * rule, usually as part of conditional processing. currently called from
     * PathCall and PathEachChild
     */
    public void dispatchRule(TreeMapperPathReference t) {
        if ((t != null) && (bundle != null) && (processor != null)) {
            processor.processBundle(bundle, t);
        } else if (debug > 0) {
            log.warn("Proc Rule Dispatch DROP {} b/c p={} rp={}", t, bundle, processor);
        }
    }

    public void process() {
        List<DataTreeNode> list = processPath(path, 0);
        if ((debug > 0) && ((list == null) || list.isEmpty())) {
            log.warn("proc FAIL {}", list);
            log.warn(".... PATH {}", LessStrings.join(path, " // "));
            log.warn(".... PACK {}", bundle);
        }
        if (list != null) {
            list.forEach(DataTreeNode::release);
        }
    }

    /**
     * called from PathCall.processNode(), PathCombo.processNode() and
     * PathEach.processNode()
     */
    public List<DataTreeNode> processPath(PathElement[] path) {
        return processPath(path, 0);
    }

    /** */
    @Nullable private List<DataTreeNode> processPath(PathElement[] path, int index) {
        if ((path == null) || (path.length <= index)) {
            return null;
        }
        List<DataTreeNode> nodes = processPathElement(path[index]);
        if ((nodes != null) && nodes.isEmpty()) {
            // we get here from op elements, each elements, etc
            if ((index + 1) < path.length) {
                return processPath(path, index + 1);
            }
            return null;
        } else if (nodes == null) {
            return null;
        } else if ((index + 1) < path.length) {
            List<DataTreeNode> childNodes = null;
            for (DataTreeNode tn : nodes) {
                push(tn);
                List<DataTreeNode> childNodesPartition = processPath(path, index + 1);
                if (childNodesPartition != null) {
                    if ((childNodes == null) || (childNodes == empty)) {
                        childNodes = childNodesPartition;
                    } else {
                        childNodes.addAll(childNodesPartition);
                    }
                }
                pop().release();
            }
            return childNodes;
        } else {
            return nodes;
        }
    }

    /**
     * called from this.processPath(), PathEach.processNode() and
     * PathSplit.processNode()
     */
    public List<DataTreeNode> processPathElement(PathElement pe) {
        if (profiling) {
            long mark = System.nanoTime();
            List<DataTreeNode> list = processPathElementProfiled(pe);
            processor.updateProfile(pe, System.nanoTime() - mark);
            return list;
        } else {
            return processPathElementProfiled(pe);
        }
    }

    private List<DataTreeNode> processPathElementProfiled(PathElement pe) {
        if (pe.disabled()) {
            return empty();
        }
        if (debugthread) {
            checkThread();
        }
        List<DataTreeNode> list = pe.processNode(this);
        if (list != null) {
            touched += list.size();
        }
        return list;
    }

    @Override
    public void onNewNode(DataTreeNode child) {
        lastWasNew = true;
    }

    @Override
    public Bundle createBundle() {
        return processor.createBundle();
    }

    @Override
    public BundleFormat getFormat() {
        return processor.getFormat();
    }

    public boolean processorClosing() { return processor.isClosing(); }
}
