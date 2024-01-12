Refactoring Types: ['Extract Method']
worker/block/BlockMetadataManager.java
/*
 * Licensed to the University of California, Berkeley under one or more contributor license
 * agreements. See the NOTICE file distributed with this work for additional information regarding
 * copyright ownership. The ASF licenses this file to You under the Apache License, Version 2.0 (the
 * "License"); you may not use this file except in compliance with the License. You may obtain a
 * copy of the License at
 *
 * http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software distributed under the License
 * is distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express
 * or implied. See the License for the specific language governing permissions and limitations under
 * the License.
 */

package tachyon.worker.block;

import java.util.ArrayList;
import java.util.HashMap;
import java.util.List;
import java.util.Map;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import com.google.common.base.Optional;

import tachyon.Constants;
import tachyon.conf.TachyonConf;
import tachyon.worker.BlockStoreLocation;
import tachyon.worker.block.meta.BlockMeta;
import tachyon.worker.block.meta.StorageDir;
import tachyon.worker.block.meta.StorageTier;
import tachyon.worker.block.meta.TempBlockMeta;

/**
 * Manages the metadata of all blocks in managed space. This information is used by the
 * TieredBlockStore, Allocator and Evictor.
 * <p>
 * This class is thread-safe and all operations on block metadata such as StorageTier, StorageDir
 * should go through this class.
 */
public class BlockMetadataManager {
  private static final Logger LOG = LoggerFactory.getLogger(Constants.LOGGER_TYPE);

  /** A list of managed StorageTier */
  private Map<Integer, StorageTier> mTiers;

  public BlockMetadataManager(TachyonConf tachyonConf) {
    // Initialize storage tiers
    int totalTiers = tachyonConf.getInt(Constants.WORKER_MAX_TIERED_STORAGE_LEVEL, 1);
    mTiers = new HashMap<Integer, StorageTier>(totalTiers);
    for (int i = 0; i < totalTiers; i ++) {
      int tierAlias = i + 1;
      mTiers.put(tierAlias, new StorageTier(tachyonConf, tierAlias));
    }
  }

  /**
   * Gets the StorageTier given its tierAlias.
   *
   * @param tierAlias the alias of this tier
   * @return the StorageTier object associated with the alias
   */
  public synchronized StorageTier getTier(int tierAlias) {
    return mTiers.get(tierAlias);
  }

  /**
   * Gets the list of StorageTier managed.
   *
   * @return the list of StorageTiers
   */
  public synchronized List<StorageTier> getTiers() {
    return new ArrayList<StorageTier>(mTiers.values());
  }

  /**
   * Gets the amount of available space in given location in bytes.
   *
   * @param location location the check available bytes
   * @return available bytes
   */
  public synchronized long getAvailableBytes(BlockStoreLocation location) {
    long spaceAvailable = 0;

    if (location.equals(BlockStoreLocation.anyTier())) {
      for (StorageTier tier : getTiers()) {
        spaceAvailable += tier.getAvailableBytes();
      }
      return spaceAvailable;
    }

    int tierAlias = location.tierAlias();
    StorageTier tier = getTier(tierAlias);
    if (location.equals(BlockStoreLocation.anyDirInTier(tierAlias))) {
      return tier.getAvailableBytes();
    }

    int dirIndex = location.dir();
    StorageDir dir = tier.getDir(dirIndex);
    return dir.getAvailableBytes();
  }

  /**
   * Checks if the storage has a given block.
   *
   * @param blockId the block ID
   * @return true if the block is contained, false otherwise
   */
  public synchronized boolean hasBlockMeta(long blockId) {
    for (StorageTier tier : mTiers.values()) {
      for (StorageDir dir : tier.getStorageDirs()) {
        if (dir.hasBlockMeta(blockId)) {
          return true;
        }
      }
    }
    return false;
  }

  /**
   * Gets the metadata of a block given its blockId.
   *
   * @param blockId the block ID
   * @return metadata of the block or absent
   */
  public synchronized Optional<BlockMeta> getBlockMeta(long blockId) {
    for (StorageTier tier : mTiers.values()) {
      for (StorageDir dir : tier.getStorageDirs()) {
        if (dir.hasBlockMeta(blockId)) {
          return tier.getBlockMeta(blockId);
        }
      }
    }
    return Optional.absent();
  }

  /**
   * Moves the metadata of an existing block to another location.
   *
   * @param blockId the block ID
   * @return the new block metadata if success, absent otherwise
   */
  public synchronized Optional<BlockMeta> moveBlockMeta(long userId, long blockId,
      BlockStoreLocation newLocation) {
    // Check if the blockId is valid.
    BlockMeta block = getBlockMeta(blockId).orNull();
    if (block == null) {
      LOG.error("No block found for block ID {}", blockId);
      return Optional.absent();
    }

    // If move target can be any tier, then simply return the current block meta.
    if (newLocation.equals(BlockStoreLocation.anyTier())) {
      return Optional.of(block);
    }

    int newTierAlias = newLocation.tierAlias();
    StorageTier newTier = getTier(newTierAlias);
    StorageDir newDir = null;
    if (newLocation.equals(BlockStoreLocation.anyDirInTier(newTierAlias))) {
      for (StorageDir dir : newTier.getStorageDirs()) {
        if (dir.getAvailableBytes() > block.getBlockSize()) {
          newDir = dir;
        }
      }
    } else {
      newDir = newTier.getDir(newLocation.dir());
    }

    if (newDir == null) {
      return Optional.absent();
    }
    StorageDir oldDir = block.getParentDir();
    if (!oldDir.removeBlockMeta(block)) {
      return Optional.absent();
    }
    return newDir.addBlockMeta(block);
  }

  /**
   * Remove the metadata of a specific block.
   *
   * @param block the meta data of the block to remove
   * @return true if success, false otherwise
   */
  public synchronized boolean removeBlockMeta(BlockMeta block) {
    StorageDir dir = block.getParentDir();
    return dir.removeBlockMeta(block);
  }

  /**
   * Gets the metadata of a temp block.
   *
   * @param blockId the ID of the temp block
   * @return metadata of the block or absent
   */
  public synchronized Optional<TempBlockMeta> getTempBlockMeta(long blockId) {
    for (StorageTier tier : mTiers.values()) {
      for (StorageDir dir : tier.getStorageDirs()) {
        if (dir.hasTempBlockMeta(blockId)) {
          return dir.getTempBlockMeta(blockId);
        }
      }
    }
    return Optional.absent();
  }

  /**
   * Adds a temp block.
   *
   * @param tempBlockMeta the meta data of the temp block to add
   * @return true if success, false otherwise
   */
  public synchronized boolean addTempBlockMeta(TempBlockMeta tempBlockMeta) {
    StorageDir dir = tempBlockMeta.getParentDir();
    return dir.addTempBlockMeta(tempBlockMeta);
  }

  /**
   * Commits a temp block.
   *
   * @param tempBlockMeta the meta data of the temp block to commit
   * @return true if success, false otherwise
   */
  public synchronized boolean commitTempBlockMeta(TempBlockMeta tempBlockMeta) {
    BlockMeta block = new BlockMeta(tempBlockMeta);
    StorageDir dir = tempBlockMeta.getParentDir();
    return dir.removeTempBlockMeta(tempBlockMeta) && dir.addBlockMeta(block).isPresent();

  }

  /**
   * Aborts a temp block.
   *
   * @param tempBlockMeta the meta data of the temp block to add
   * @return true if success, false otherwise
   */
  public synchronized boolean abortTempBlockMeta(TempBlockMeta tempBlockMeta) {
    StorageDir dir = tempBlockMeta.getParentDir();
    return dir.removeTempBlockMeta(tempBlockMeta);
  }

  /**
   * Cleans up the temp blocks meta data created by the given user.
   *
   * @param userId the ID of the user
   */
  public synchronized void cleanupUser(long userId) {
    for (StorageTier tier : mTiers.values()) {
      for (StorageDir dir : tier.getStorageDirs()) {
        dir.cleanupUser(userId);
      }
    }
  }

  /**
   * Gets a summary of the meta data.
   *
   * @return the metadata of this block store
   */
  public synchronized BlockStoreMeta getBlockStoreMeta() {
    return new BlockStoreMeta(this);
  }
}


File: servers/src/main/java/tachyon/worker/block/TieredBlockStore.java
/*
 * Licensed to the University of California, Berkeley under one or more contributor license
 * agreements. See the NOTICE file distributed with this work for additional information regarding
 * copyright ownership. The ASF licenses this file to You under the Apache License, Version 2.0 (the
 * "License"); you may not use this file except in compliance with the License. You may obtain a
 * copy of the License at
 *
 * http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software distributed under the License
 * is distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express
 * or implied. See the License for the specific language governing permissions and limitations under
 * the License.
 */

package tachyon.worker.block;

import java.io.File;
import java.io.IOException;
import java.util.ArrayList;
import java.util.List;
import java.util.concurrent.locks.ReentrantReadWriteLock;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import com.google.common.base.Optional;
import com.google.common.base.Preconditions;

import tachyon.Constants;
import tachyon.Pair;
import tachyon.conf.TachyonConf;
import tachyon.worker.BlockStoreLocation;
import tachyon.worker.block.allocator.Allocator;
import tachyon.worker.block.allocator.NaiveAllocator;
import tachyon.worker.block.evictor.EvictionPlan;
import tachyon.worker.block.evictor.Evictor;
import tachyon.worker.block.evictor.NaiveEvictor;
import tachyon.worker.block.io.BlockReader;
import tachyon.worker.block.io.BlockWriter;
import tachyon.worker.block.io.LocalFileBlockReader;
import tachyon.worker.block.io.LocalFileBlockWriter;
import tachyon.worker.block.meta.BlockMeta;
import tachyon.worker.block.meta.TempBlockMeta;

/**
 * This class represents an object store that manages all the blocks in the local tiered storage.
 * This store exposes simple public APIs to operate blocks. Inside this store, it creates an
 * Allocator to decide where to put a new block, an Evictor to decide where to evict a stale block,
 * a BlockMetadataManager to maintain the status of the tiered storage, and a LockManager to
 * coordinate read/write on the same block.
 * <p>
 * This class is thread-safe.
 */
public class TieredBlockStore implements BlockStore {
  private static final Logger LOG = LoggerFactory.getLogger(Constants.LOGGER_TYPE);

  private final TachyonConf mTachyonConf;
  private final BlockMetadataManager mMetaManager;
  private final BlockLockManager mLockManager;
  private final Allocator mAllocator;
  private final Evictor mEvictor;

  private List<BlockAccessEventListener> mAccessEventListeners = new
      ArrayList<BlockAccessEventListener>();
  private List<BlockMetaEventListener> mMetaEventListeners = new
      ArrayList<BlockMetaEventListener>();

  /** A readwrite lock for meta data **/
  private final ReentrantReadWriteLock mEvictionLock = new ReentrantReadWriteLock();

  public TieredBlockStore(TachyonConf tachyonConf) {
    mTachyonConf = Preconditions.checkNotNull(tachyonConf);
    mMetaManager = new BlockMetadataManager(mTachyonConf);
    mLockManager = new BlockLockManager(mMetaManager);

    // TODO: create Allocator according to tachyonConf.
    mAllocator = new NaiveAllocator(mMetaManager);
    // TODO: create Evictor according to tachyonConf
    mEvictor = new NaiveEvictor(mMetaManager);
  }

  @Override
  public Optional<Long> lockBlock(long userId, long blockId) {
    return mLockManager.lockBlock(userId, blockId, BlockLockType.READ);
  }

  @Override
  public boolean unlockBlock(long lockId) {
    return mLockManager.unlockBlock(lockId);
  }

  @Override
  public boolean unlockBlock(long userId, long blockId) {
    return mLockManager.unlockBlock(userId, blockId);
  }

  @Override
  public Optional<BlockWriter> getBlockWriter(long userId, long blockId) throws IOException {
    Optional<TempBlockMeta> optBlock = mMetaManager.getTempBlockMeta(blockId);
    if (!optBlock.isPresent()) {
      return Optional.absent();
    }
    BlockWriter writer = new LocalFileBlockWriter(optBlock.get());
    return Optional.of(writer);
  }

  @Override
  public Optional<BlockReader> getBlockReader(long userId, long blockId, long lockId)
      throws IOException {
    Preconditions.checkState(mLockManager.validateLockId(userId, blockId, lockId));

    Optional<BlockMeta> optBlock = mMetaManager.getBlockMeta(blockId);
    if (!optBlock.isPresent()) {
      return Optional.absent();
    }
    BlockReader reader = new LocalFileBlockReader(optBlock.get());
    return Optional.of(reader);
  }

  @Override
  public Optional<TempBlockMeta> createBlockMeta(long userId, long blockId,
      BlockStoreLocation location, long initialBlockSize) throws IOException {
    mEvictionLock.readLock().lock();
    Optional<TempBlockMeta> optTempBlock =
        createBlockMetaNoLock(userId, blockId, location, initialBlockSize);
    mEvictionLock.readLock().unlock();
    return optTempBlock;
  }

  @Override
  public Optional<BlockMeta> getBlockMeta(long userId, long blockId, long lockId) {
    Preconditions.checkState(mLockManager.validateLockId(userId, blockId, lockId));
    return mMetaManager.getBlockMeta(blockId);
  }

  @Override
  public boolean commitBlock(long userId, long blockId) {
    TempBlockMeta tempBlock = mMetaManager.getTempBlockMeta(blockId).orNull();
    for (BlockMetaEventListener listener: mMetaEventListeners) {
      listener.preCommitBlock(userId, blockId, tempBlock.getBlockLocation());
    }

    mEvictionLock.readLock().lock();
    boolean result = commitBlockNoLock(userId, blockId);
    mEvictionLock.readLock().unlock();

    if (result) {
      for (BlockMetaEventListener listener : mMetaEventListeners) {
        listener.postCommitBlock(userId, blockId, tempBlock.getBlockLocation());
      }
    }
    return true;
  }

  @Override
  public boolean abortBlock(long userId, long blockId) {
    mEvictionLock.readLock().lock();
    boolean result = abortBlockNoLock(userId, blockId);
    mEvictionLock.readLock().unlock();
    return result;
  }

  @Override
  public boolean requestSpace(long userId, long blockId, long moreBytes) throws IOException {
    mEvictionLock.writeLock().lock();
    boolean result = requestSpaceNoLock(userId, blockId, moreBytes);
    mEvictionLock.writeLock().unlock();
    return result;
  }

  @Override
  public boolean moveBlock(long userId, long blockId, BlockStoreLocation newLocation)
      throws IOException {
    for (BlockMetaEventListener listener: mMetaEventListeners) {
      listener.preMoveBlock(userId, blockId, newLocation);
    }

    mEvictionLock.readLock().lock();
    // TODO: Handle absent
    long lockId = mLockManager.lockBlock(userId, blockId, BlockLockType.WRITE).get();
    boolean result = moveBlockNoLock(userId, blockId, newLocation);
    mLockManager.unlockBlock(lockId);
    mEvictionLock.readLock().unlock();

    if (result) {
      for (BlockMetaEventListener listener: mMetaEventListeners) {
        listener.postMoveBlock(userId, blockId, newLocation);
      }
    }
    return result;
  }

  @Override
  public boolean removeBlock(long userId, long blockId) throws IOException {
    for (BlockMetaEventListener listener: mMetaEventListeners) {
      listener.preRemoveBlock(userId, blockId);
    }

    mEvictionLock.readLock().lock();
    // TODO: Handle absent
    long lockId = mLockManager.lockBlock(userId, blockId, BlockLockType.WRITE).get();
    boolean result = removeBlockNoLock(userId, blockId);
    mLockManager.unlockBlock(lockId);
    mEvictionLock.readLock().unlock();

    if (result) {
      for (BlockMetaEventListener listener: mMetaEventListeners) {
        listener.postRemoveBlock(userId, blockId);
      }
    }
    return result;
  }

  @Override
  public void accessBlock(long userId, long blockId) {
    for (BlockAccessEventListener listener: mAccessEventListeners) {
      listener.onAccessBlock(userId, blockId);
    }
  }

  @Override
  public boolean freeSpace(long userId, long availableBytes, BlockStoreLocation location)
      throws IOException {
    mEvictionLock.writeLock().lock();
    boolean result = freeSpaceNoEvictionLock(userId, availableBytes, location);
    mEvictionLock.writeLock().unlock();
    return result;
  }

  @Override
  public boolean cleanupUser(long userId) {
    mEvictionLock.readLock().lock();
    mMetaManager.cleanupUser(userId);
    mLockManager.cleanupUser(userId);
    mEvictionLock.readLock().unlock();
    return true;
  }

  @Override
  public BlockStoreMeta getBlockStoreMeta() {
    return mMetaManager.getBlockStoreMeta();
  }

  @Override
  public void registerMetaListener(BlockMetaEventListener listener) {
    mMetaEventListeners.add(listener);
  }

  @Override
  public void registerAccessListener(BlockAccessEventListener listener) {
    mAccessEventListeners.add(listener);
  }

  private Optional<TempBlockMeta> createBlockMetaNoLock(long userId, long blockId,
      BlockStoreLocation location, long initialBlockSize) throws IOException {
    Optional<TempBlockMeta> optTempBlock =
        mAllocator.allocateBlock(userId, blockId, initialBlockSize, location);
    if (!optTempBlock.isPresent()) {
      // Failed to allocate a temp block, let Evictor kick in to ensure sufficient space available.

      // Upgrade to write lock to guard evictor.
      mEvictionLock.readLock().unlock();
      mEvictionLock.writeLock().lock();

      boolean result = freeSpaceNoEvictionLock(userId, initialBlockSize, location);

      // Downgrade to read lock again after eviction
      mEvictionLock.readLock().lock();
      mEvictionLock.writeLock().unlock();

      // Not enough space in this block store, let's try to free some space.
      if (!result) {
        LOG.error("Cannot free {} bytes space in {}", initialBlockSize, location);
        return Optional.absent();
      }
      optTempBlock = mAllocator.allocateBlock(userId, blockId, initialBlockSize, location);
      Preconditions.checkState(optTempBlock.isPresent(), "Cannot allocate block {}:", blockId);
    }
    // Add allocated temp block to metadata manager
    mMetaManager.addTempBlockMeta(optTempBlock.get());
    return optTempBlock;
  }

  private boolean commitBlockNoLock(long userId, long blockId) {
    Optional<TempBlockMeta> optTempBlock = mMetaManager.getTempBlockMeta(blockId);
    if (!optTempBlock.isPresent()) {
      return false;
    }
    TempBlockMeta tempBlock = optTempBlock.get();
    // Check the userId is the owner of this temp block
    if (tempBlock.getUserId() != userId) {
      return false;
    }
    String sourcePath = tempBlock.getPath();
    String destPath = tempBlock.getCommitPath();
    boolean renamed = new File(sourcePath).renameTo(new File(destPath));
    if (!renamed) {
      return false;
    }
    return mMetaManager.commitTempBlockMeta(tempBlock);
  }

  private boolean abortBlockNoLock(long userId, long blockId) {
    Optional<TempBlockMeta> optTempBlock = mMetaManager.getTempBlockMeta(blockId);
    if (!optTempBlock.isPresent()) {
      return false;
    }
    TempBlockMeta tempBlock = optTempBlock.get();
    // Check the userId is the owner of this temp block
    if (tempBlock.getUserId() != userId) {
      return false;
    }
    String path = tempBlock.getPath();
    boolean deleted = new File(path).delete();
    if (!deleted) {
      return false;
    }
    return mMetaManager.abortTempBlockMeta(tempBlock);
  }

  private boolean requestSpaceNoLock(long userId, long blockId, long moreBytes) throws IOException {
    Optional<TempBlockMeta> optTempBlock = mMetaManager.getTempBlockMeta(blockId);
    if (!optTempBlock.isPresent()) {
      return false;
    }
    TempBlockMeta tempBlock = optTempBlock.get();
    BlockStoreLocation location = tempBlock.getBlockLocation();
    if (!freeSpaceNoEvictionLock(userId, moreBytes, location)) {
      return false;
    }

    // Increase the size of this temp block
    tempBlock.setBlockSize(tempBlock.getBlockSize() + moreBytes);
    return true;
  }

  private boolean moveBlockNoLock(long userId, long blockId, BlockStoreLocation newLocation)
      throws IOException {
    Optional<BlockMeta> optSrcBlock = mMetaManager.getBlockMeta(blockId);
    if (!optSrcBlock.isPresent()) {
      return false;
    }
    String srcPath = optSrcBlock.get().getPath();
    Optional<BlockMeta> optDestBlock = mMetaManager.moveBlockMeta(userId, blockId, newLocation);
    if (!optDestBlock.isPresent()) {
      return false;
    }
    String destPath = optDestBlock.get().getPath();

    return new File(srcPath).renameTo(new File(destPath));
  }

  private boolean removeBlockNoLock(long userId, long blockId) throws IOException {
    Optional<BlockMeta> optBlock = mMetaManager.getBlockMeta(blockId);
    if (!optBlock.isPresent()) {
      LOG.error("Block is not present");
      return false;
    }
    BlockMeta block = optBlock.get();
    // Delete metadata of the block
    if (!mMetaManager.removeBlockMeta(block)) {
      LOG.error("Unable to remove metadata");
      return false;
    }
    // Delete the data file of the block
    return new File(block.getPath()).delete();
  }

  private boolean freeSpaceNoEvictionLock(long userId, long availableBytes,
      BlockStoreLocation location) throws IOException {
    Optional<EvictionPlan> optPlan = mEvictor.freeSpace(availableBytes, location);
    // Absent plan means failed to evict enough space.
    if (!optPlan.isPresent()) {
      LOG.error("Failed to free space: no eviction plan by evictor");
      return false;
    }
    EvictionPlan plan = optPlan.get();
    // Step1: remove blocks to make room.
    for (long blockId : plan.toEvict()) {
      // TODO: Handle absent
      long lockId = mLockManager.lockBlock(userId, blockId, BlockLockType.WRITE).get();
      boolean result = removeBlockNoLock(userId, blockId);
      mLockManager.unlockBlock(lockId);
      if (!result) {
        LOG.error("Failed to free space: cannot evict block {}", blockId);
        return false;
      }
    }
    // Step2: transfer blocks among tiers.
    for (Pair<Long, BlockStoreLocation> entry : plan.toMove()) {
      long blockId = entry.getFirst();
      BlockStoreLocation newLocation = entry.getSecond();
      // TODO: Handle absent
      long lockId = mLockManager.lockBlock(userId, blockId, BlockLockType.WRITE).get();
      boolean result = moveBlockNoLock(userId, blockId, newLocation);
      mLockManager.unlockBlock(lockId);
      if (!result) {
        LOG.error("Failed to free space: cannot move block {} to {}", blockId, newLocation);
        return false;
      }
    }
    return true;
  }

}


File: servers/src/main/java/tachyon/worker/block/meta/StorageDir.java
/*
 * Licensed to the University of California, Berkeley under one or more contributor license
 * agreements. See the NOTICE file distributed with this work for additional information regarding
 * copyright ownership. The ASF licenses this file to You under the Apache License, Version 2.0 (the
 * "License"); you may not use this file except in compliance with the License. You may obtain a
 * copy of the License at
 *
 * http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software distributed under the License
 * is distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express
 * or implied. See the License for the specific language governing permissions and limitations under
 * the License.
 */

package tachyon.worker.block.meta;

import java.util.ArrayList;
import java.util.Collection;
import java.util.List;
import java.util.HashMap;
import java.util.Map;
import java.util.Set;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import com.google.common.base.Optional;
import com.google.common.base.Preconditions;
import com.google.common.collect.Sets;

import tachyon.Constants;
import tachyon.StorageDirId;

/**
 * Represents a directory in a storage tier. It has a fixed capacity allocated to it on
 * instantiation. It contains the set of blocks currently in the storage directory
 * <p>
 * This class does not guarantee thread safety.
 */
public class StorageDir {
  private static final Logger LOG = LoggerFactory.getLogger(Constants.LOGGER_TYPE);

  /** A map from block ID to block meta data */
  private Map<Long, BlockMeta> mBlockIdToBlockMap;
  /** A map from block ID to temp block meta data */
  private Map<Long, TempBlockMeta> mBlockIdToTempBlockMap;
  /** A map from user ID to the set of temp blocks created by this user */
  private Map<Long, Set<Long>> mUserIdToTempBlockIdsMap;

  private final long mCapacityBytes;
  private long mAvailableBytes;
  private String mDirPath;
  private int mDirIndex;
  private StorageTier mTier;

  public StorageDir(StorageTier tier, int dirIndex, long capacityBytes, String dirPath) {
    mTier = Preconditions.checkNotNull(tier);
    mDirIndex = dirIndex;
    mCapacityBytes = capacityBytes;
    mAvailableBytes = capacityBytes;
    mDirPath = dirPath;
    mBlockIdToBlockMap = new HashMap<Long, BlockMeta>(200);
    mBlockIdToTempBlockMap = new HashMap<Long, TempBlockMeta>(200);
    mUserIdToTempBlockIdsMap = new HashMap<Long, Set<Long>>(200);
  }

  public long getCapacityBytes() {
    return mCapacityBytes;
  }

  public long getAvailableBytes() {
    return mAvailableBytes;
  }

  public String getDirPath() {
    return mDirPath;
  }

  public StorageTier getParentTier() {
    return mTier;
  }

  public int getDirIndex() {
    return mDirIndex;
  }

  // TODO: deprecate this method.
  public long getStorageDirId() {
    int level = mTier.getTierAlias() - 1;
    int storageLevelAliasValue = mTier.getTierAlias();
    return StorageDirId.getStorageDirId(level, storageLevelAliasValue, mDirIndex);
  }

  /**
   * Returns a list of non-temporary block IDs in this dir.
   */
  public List<Long> getBlockIds() {
    return new ArrayList<Long>(mBlockIdToBlockMap.keySet());
  }

  public Collection<BlockMeta> getBlocks() {
    return mBlockIdToBlockMap.values();
  }

  /**
   * Check if a specific block is in this storage dir.
   *
   * @param blockId the block ID
   * @return true if the block is in this storage dir, false otherwise
   */
  public boolean hasBlockMeta(long blockId) {
    return mBlockIdToBlockMap.containsKey(blockId);
  }

  /**
   * Check if a temp block is in this storage dir.
   *
   * @param blockId the block ID
   * @return true if the block is in this storage dir, false otherwise
   */
  public boolean hasTempBlockMeta(long blockId) {
    return mBlockIdToTempBlockMap.containsKey(blockId);
  }

  /**
   * Get the BlockMeta from this storage dir by its block ID.
   *
   * @param blockId the block ID
   * @return the BlockMeta or absent
   */
  public Optional<BlockMeta> getBlockMeta(long blockId) {
    return Optional.fromNullable(mBlockIdToBlockMap.get(blockId));
  }

  /**
   * Get the BlockMeta from this storage dir by its block ID.
   *
   * @param blockId the block ID
   * @return the BlockMeta or absent
   */
  public Optional<TempBlockMeta> getTempBlockMeta(long blockId) {
    return Optional.fromNullable(mBlockIdToTempBlockMap.get(blockId));
  }

  /**
   * Add the metadata of a new block into this storage dir.
   *
   * @param block the meta data of the block
   * @return the BlockMeta or absent
   */
  public Optional<BlockMeta> addBlockMeta(BlockMeta block) {
    long blockId = block.getBlockId();
    long blockSize = block.getBlockSize();

    if (getAvailableBytes() < blockSize) {
      LOG.error("Fail to create blockId {} in dir {}: {} bytes required, but {} bytes available",
          blockId, toString(), blockSize, getAvailableBytes());
      return Optional.absent();
    }
    if (hasBlockMeta(blockId)) {
      LOG.error("Fail to create blockId {} in dir {}: blockId exists", blockId, toString());
      return Optional.absent();
    }
    mBlockIdToBlockMap.put(blockId, block);
    mAvailableBytes -= blockSize;
    Preconditions.checkState(mAvailableBytes >= 0, "Available bytes should always be non-negative");
    return Optional.of(block);
  }


  /**
   * Add the metadata of a new block into this storage dir.
   *
   * @param tempBlockMeta the meta data of a temp block to add
   * @return the BlockMeta or absent
   */
  public boolean addTempBlockMeta(TempBlockMeta tempBlockMeta) {
    long userId = tempBlockMeta.getUserId();
    long blockId = tempBlockMeta.getBlockId();
    long blockSize = tempBlockMeta.getBlockSize();
    mBlockIdToTempBlockMap.put(blockId, tempBlockMeta);
    Set<Long> userTempBlocks = mUserIdToTempBlockIdsMap.get(userId);
    if (null == userTempBlocks) {
      mUserIdToTempBlockIdsMap.put(userId, Sets.newHashSet(blockId));
    } else {
      userTempBlocks.add(blockId);
    }
    mAvailableBytes -= blockSize;
    return true;
  }

  /**
   * Remove a block from this storage dir.
   *
   * @param block the meta data of the block
   * @return true if success, false otherwise
   */
  public boolean removeBlockMeta(BlockMeta block) {
    Preconditions.checkNotNull(block);
    mBlockIdToBlockMap.remove(block.getBlockId());
    mAvailableBytes += block.getBlockSize();
    return true;
  }

  /**
   * Remove a block from this storage dir.
   *
   * @param tempBlockMeta the meta data of the temp block to remove
   * @return true if success, false otherwise
   */
  public boolean removeTempBlockMeta(TempBlockMeta tempBlockMeta) {
    Preconditions.checkNotNull(tempBlockMeta);
    long blockId = tempBlockMeta.getBlockId();
    mBlockIdToTempBlockMap.remove(blockId);
    Preconditions.checkNotNull(tempBlockMeta);
    for (Map.Entry<Long, Set<Long>> entry : mUserIdToTempBlockIdsMap.entrySet()) {
      Long userId = entry.getKey();
      Set<Long> userBlocks = entry.getValue();
      if (userBlocks.contains(blockId)) {
        Preconditions.checkState(userBlocks.remove(blockId));
        if (userBlocks.isEmpty()) {
          mUserIdToTempBlockIdsMap.remove(userId);
        }
        mAvailableBytes += tempBlockMeta.getBlockSize();
        Preconditions.checkState(mCapacityBytes >= mAvailableBytes,
            "Available bytes should always be less than total capacity bytes");
        return true;
      }
    }
    return false;
  }

  /**
   * Cleans up the temp block meta data of a specific user
   *
   * @param userId the ID of the user to cleanup
   */
  public void cleanupUser(long userId) {
    Set<Long> userTempBlocks = mUserIdToTempBlockIdsMap.get(userId);
    if (null == userTempBlocks) {
      return;
    }
    for (long blockId : userTempBlocks) {
      mBlockIdToTempBlockMap.remove(blockId);
    }
    mUserIdToTempBlockIdsMap.remove(userId);
  }
}
