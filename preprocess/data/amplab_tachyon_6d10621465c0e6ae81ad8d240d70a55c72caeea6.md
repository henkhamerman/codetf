Refactoring Types: ['Push Down Attribute', 'Push Down Method']
ta.java
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

import tachyon.util.CommonUtils;

/**
 * Represents the metadata of a block in Tachyon managed storage.
 */
public class BlockMeta extends BlockMetaBase {

  public BlockMeta(long blockId, long blockSize, StorageDir dir) {
    super(blockId, blockSize, dir);
  }

  public BlockMeta(TempBlockMeta tempBlock) {
    super(tempBlock.getBlockId(), tempBlock.getBlockSize(), tempBlock.getParentDir();
  }

  @Override
  public String getPath() {
    return CommonUtils.concatPath(mDir.getDirPath(), mBlockId);
  }
}


File: servers/src/main/java/tachyon/worker/block/meta/BlockMetaBase.java
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

import com.google.common.base.Preconditions;
import tachyon.worker.BlockStoreLocation;

/**
 * A base class of the metadata of blocks in Tachyon managed storage.
 */
public abstract class BlockMetaBase {
  protected final long mBlockId;
  protected long mBlockSize;
  protected StorageDir mDir;

  public BlockMetaBase(long blockId, long blockSize, StorageDir dir) {
    mBlockId = blockId;
    mBlockSize = blockSize;
    mDir = Preconditions.checkNotNull(dir);
  }

  public long getBlockId() {
    return mBlockId;
  }

  public long getBlockSize() {
    return mBlockSize;
  }

  /**
   * Get the location of a specific block
   */
  public BlockStoreLocation getBlockLocation() {
    StorageTier tier = mDir.getParentTier();
    return new BlockStoreLocation(tier.getTierId(), mDir.getDirId());
  }

  public StorageDir getParentDir() {
    return mDir;
  }

  public abstract String getPath();
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

import java.util.HashMap;
import java.util.Map;
import java.util.Set;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import com.google.common.base.Optional;
import com.google.common.base.Preconditions;
import com.google.common.collect.Sets;

import tachyon.Constants;

/**
 * Represents a directory in a storage tier. It has a fixed capacity allocated to it on
 * instantiation. It contains the set of blocks currently in the storage directory
 * <p>
 * This class is not thread safety.
 */
public class StorageDir {
  private static final Logger LOG = LoggerFactory.getLogger(Constants.LOGGER_TYPE);

  private Map<Long, BlockMeta> mBlockIdToBlockMap;
  private Map<Long, Set<Long>> mUserIdToBlocksMap;
  private long mCapacityBytes;
  private long mAvailableBytes;
  private String mDirPath;
  private int mDirId;
  private StorageTier mTier;

  public StorageDir(StorageTier tier, int dirId, long capacityBytes, String dirPath) {
    mTier = Preconditions.checkNotNull(tier);
    mDirId = dirId;
    mCapacityBytes = capacityBytes;
    mAvailableBytes = capacityBytes;
    mDirPath = dirPath;
    mBlockIdToBlockMap = new HashMap<Long, BlockMeta>(200);
    mUserIdToBlocksMap = new HashMap<Long, Set<Long>>(20);
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

  public int getDirId() {
    return mDirId;
  }

  /**
   * Check if a specific block is in this storage dir.
   *
   * @param blockId the block ID
   * @return true if the block is in this storage dir, false otherwise
   */
  boolean hasBlockMeta(long blockId) {
    return mBlockIdToBlockMap.containsKey(blockId)
  }

  /**
   * Get the BlockMeta from this storage dir by its block ID.
   *
   * @param blockId the block ID
   * @return the BlockMeta or absent
   */
  Optional<BlockMeta> getBlockMeta(long blockId) {
    if (!hasBlockMeta(blockId)) {
      return Optional.absent();
    }
    return Optional.of(mBlockIdToBlockMap.get(blockId));
  }

  /**
   * Add the metadata of a new block into this storage dir.
   *
   * @param userId the user ID
   * @param blockId the block ID
   * @param blockSize the block size in bytes
   * @return the BlockMeta or absent
   */
  Optional<BlockMeta> addBlockMeta(long userId, long blockId, long blockSize) {
    if (getAvailableBytes() < blockSize) {
      LOG.error("Fail to create blockId {} in dir {}: {} bytes required, but {} bytes available",
          blockId, toString(), blockSize, getAvailableBytes());
      return Optional.absent();
    }
    if (hasBlockMeta(blockId)) {
      LOG.error("Fail to create blockId {} in dir {}: blockId exists", blockId, toString());
      return Optional.absent();
    }
    Set<Long> userBlocks = mUserIdToBlocksMap.get(userId);
    if (null == userBlocks) {
      mUserIdToBlocksMap.put(userId, Sets.newHashSet(blockId));
    } else {
      userBlocks.add(blockId);
    }
    BlockMeta block = new BlockMeta(blockId, blockSize, getDirPath());
    mBlockIdToBlockMap.put(userId, block);
    mCapacityBytes += blockSize;
    mAvailableBytes -= blockSize;
    Preconditions.checkState(mAvailableBytes >= 0, "Available bytes should always be non-negative");
    return Optional.of(block);
  }

  /**
   * Remove a block from this storage dir.
   *
   * @param blockId the block ID
   * @return true if success, false otherwise
   */
  boolean removeBlockMeta(long blockId) {
    if (!hasBlockMeta(blockId)) {
      return false;
    }
    BlockMeta block = mBlockIdToBlockMap.remove(blockId);
    Preconditions.checkNotNull(block);
    for (Map.Entry<Long, Set<Long>> entry : mUserIdToBlocksMap.entrySet()) {
      Long userId = entry.getKey();
      Set<Long> userBlocks = entry.getValue();
      if (userBlocks.contains(blockId)) {
        Preconditions.checkState(userBlocks.remove(blockId));
        if (userBlocks.isEmpty()) {
          mUserIdToBlocksMap.remove(userId);
        }
        mCapacityBytes -= block.getBlockSize();
        mAvailableBytes += block.getBlockSize();
        Preconditions.checkState(mCapacityBytes >= 0, "Capacity bytes should always be "
            + "non-negative");
        return true;
      }
    }
    return false;
  }
}


File: servers/src/main/java/tachyon/worker/block/meta/StorageTier.java
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

import java.util.HashMap;
import java.util.HashSet;
import java.util.Set;

import com.google.common.base.Optional;

import tachyon.Constants;
import tachyon.conf.TachyonConf;
import tachyon.util.CommonUtils;

/**
 * Represents a tier of storage, for example memory or SSD. It serves as a container of
 * {@link StorageDir} which actually contains metadata information about blocks stored and space
 * used/available.
 * <p>
 * This class is not guarantee thread safety.
 */
public class StorageTier {
  private HashMap<Integer, StorageDir> mIdToStorageDirMap;
  private final int mTierId;

  public StorageTier(TachyonConf tachyonConf, int tier) {
    mTierId = tier;
    String tierDirPathConf =
        String.format(Constants.WORKER_TIERED_STORAGE_LEVEL_DIRS_PATH_FORMAT, tier);
    String[] dirPaths = tachyonConf.get(tierDirPathConf, "/mnt/ramdisk").split(",");

    String tierDirCapacityConf =
        String.format(Constants.WORKER_TIERED_STORAGE_LEVEL_DIRS_QUOTA_FORMAT, tier);
    String[] dirQuotas = tachyonConf.get(tierDirCapacityConf, "0").split(",");

    mIdToStorageDirMap = new HashMap<Integer, StorageDir>(dirPaths.length);

    for (int i = 0; i < dirPaths.length; i ++) {
      int index = i >= dirQuotas.length ? dirQuotas.length - 1 : i;
      long capacity = CommonUtils.parseSpaceSize(dirQuotas[index]);
      mIdToStorageDirMap.put(i, new StorageDir(i, capacity, dirPaths[i]));
    }
  }

  public int getTierId() {
    return mTierId;
  }

  public long getCapacityBytes() {
    long capacityBytes = 0;
    for (StorageDir dir : mIdToStorageDirMap.values()) {
      capacityBytes += dir.getCapacityBytes();
    }
    return capacityBytes;
  }

  public long getAvailableBytes() {
    long availableBytes = 0;
    for (StorageDir dir : mIdToStorageDirMap.values()) {
      availableBytes += dir.getAvailableBytes();
    }
    return availableBytes;
  }

  public Set<StorageDir> getStorageDirs() {
    return new HashSet<StorageDir>(mIdToStorageDirMap.values());
  }

  public Optional<BlockMeta> getBlockMeta(long blockId) {
    for (StorageDir dir : mIdToStorageDirMap.values()) {
      Optional<BlockMeta> optionalBlock = dir.getBlockMeta(blockId);
      if (optionalBlock.isPresent()) {
        return optionalBlock;
      }
    }
    return Optional.absent();
  }

  public Optional<BlockMeta> addBlockMeta(long userId, long blockId, long blockSize) {
    for (StorageDir dir : mIdToStorageDirMap.values()) {
      Optional<BlockMeta> optionalBlock = dir.addBlockMeta(userId, blockId, blockSize);
      if (optionalBlock.isPresent()) {
        return optionalBlock;
      }
    }
    return Optional.absent();
  }

  public boolean removeBlockMeta(long blockId) {
    for (StorageDir dir : mIdToStorageDirMap.values()) {
      if (dir.hasBlockMeta(blockId)) {
        return dir.removeBlockMeta(blockId);
      }
    }
    return false;
  }

}


File: servers/src/main/java/tachyon/worker/block/meta/TempBlockMeta.java
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

import tachyon.util.CommonUtils;

/**
 * Represents the metadata of an uncommited block in Tachyon managed storage.
 */
public class TempBlockMeta extends BlockMetaBase {
  private final long mUserId;

  public TempBlockMeta(long userId, long blockId, long blockSize, StorageDir dir) {
    super(blockId, blockSize, dir);
    mUserId = userId;
  }

  @Override
  public String getPath() {
    return CommonUtils.concatPath(mDir.getDirPath(), mUserId, mBlockId);
  }

  public String getCommitPath() {
    return CommonUtils.concatPath(mDir.getDirPath(), mBlockId);
  }

  public void setBlockSize(long newSize) {
    mBlockSize = newSize;
  }
}
