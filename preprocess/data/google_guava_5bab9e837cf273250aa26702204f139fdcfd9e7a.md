Refactoring Types: ['Inline Method']
ommon/collect/HashBiMapTest.java
/*
 * Copyright (C) 2007 The Guava Authors
 *
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

package com.google.common.collect;

import com.google.common.annotations.GwtCompatible;
import com.google.common.annotations.GwtIncompatible;
import com.google.common.collect.testing.features.CollectionFeature;
import com.google.common.collect.testing.features.CollectionSize;
import com.google.common.collect.testing.features.MapFeature;
import com.google.common.collect.testing.google.BiMapTestSuiteBuilder;
import com.google.common.collect.testing.google.TestStringBiMapGenerator;

import junit.framework.Test;
import junit.framework.TestCase;
import junit.framework.TestSuite;

import java.util.Iterator;
import java.util.Map;
import java.util.Map.Entry;
import java.util.Set;

/**
 * Tests for {@link HashBiMap}.
 *
 * @author Mike Bostock
 */
@GwtCompatible(emulated = true)
public class HashBiMapTest extends TestCase {

  public static final class HashBiMapGenerator extends TestStringBiMapGenerator {
    @Override
    protected BiMap<String, String> create(Entry<String, String>[] entries) {
      BiMap<String, String> result = HashBiMap.create();
      for (Entry<String, String> entry : entries) {
        result.put(entry.getKey(), entry.getValue());
      }
      return result;
    }
  }

  @GwtIncompatible("suite")
  public static Test suite() {
    TestSuite suite = new TestSuite();
    suite.addTest(BiMapTestSuiteBuilder.using(new HashBiMapGenerator())
      .named("HashBiMap")
      .withFeatures(CollectionSize.ANY,
          CollectionFeature.SERIALIZABLE,
          CollectionFeature.SUPPORTS_ITERATOR_REMOVE,
          MapFeature.ALLOWS_NULL_KEYS,
          MapFeature.ALLOWS_NULL_VALUES,
          MapFeature.ALLOWS_ANY_NULL_QUERIES,
          MapFeature.GENERAL_PURPOSE)
      .createTestSuite());
    suite.addTestSuite(HashBiMapTest.class);
    return suite;
  }

  public void testMapConstructor() {
    /* Test with non-empty Map. */
    Map<String, String> map = ImmutableMap.of(
        "canada", "dollar",
        "chile", "peso",
        "switzerland", "franc");
    HashBiMap<String, String> bimap = HashBiMap.create(map);
    assertEquals("dollar", bimap.get("canada"));
    assertEquals("canada", bimap.inverse().get("dollar"));
  }

  private static final int N = 1000;

  public void testBashIt() throws Exception {
    BiMap<Integer, Integer> bimap = HashBiMap.create(N);
    BiMap<Integer, Integer> inverse = bimap.inverse();

    for (int i = 0; i < N; i++) {
      assertNull(bimap.put(2 * i, 2 * i + 1));
    }
    for (int i = 0; i < N; i++) {
      assertEquals(2 * i + 1, (int) bimap.get(2 * i));
    }
    for (int i = 0; i < N; i++) {
      assertEquals(2 * i, (int) inverse.get(2 * i + 1));
    }
    for (int i = 0; i < N; i++) {
      int oldValue = bimap.get(2 * i);
      assertEquals(2 * i + 1, (int) bimap.put(2 * i, oldValue - 2));
    }
    for (int i = 0; i < N; i++) {
      assertEquals(2 * i - 1, (int) bimap.get(2 * i));
    }
    for (int i = 0; i < N; i++) {
      assertEquals(2 * i, (int) inverse.get(2 * i - 1));
    }
    Set<Entry<Integer, Integer>> entries = bimap.entrySet();
    for (Entry<Integer, Integer> entry : entries) {
      entry.setValue(entry.getValue() + 2 * N);
    }
    for (int i = 0; i < N; i++) {
      assertEquals(2 * N + 2 * i - 1, (int) bimap.get(2 * i));
    }
  }

  public void testBiMapEntrySetIteratorRemove() {
    BiMap<Integer, String> map = HashBiMap.create();
    map.put(1, "one");
    Set<Map.Entry<Integer, String>> entries = map.entrySet();
    Iterator<Map.Entry<Integer, String>> iterator = entries.iterator();
    Map.Entry<Integer, String> entry = iterator.next();
    entry.setValue("two"); // changes the iterator's current entry value
    assertEquals("two", map.get(1));
    assertEquals(Integer.valueOf(1), map.inverse().get("two"));
    iterator.remove(); // removes the updated entry
    assertTrue(map.isEmpty());
  }

  public void testInverseEntrySetValue() {
    BiMap<Integer, String> map = HashBiMap.create();
    map.put(1, "one");
    Entry<String, Integer> inverseEntry = Iterables.getOnlyElement(map.inverse().entrySet());
    inverseEntry.setValue(2);
    assertEquals(Integer.valueOf(2), inverseEntry.getValue());
  }
}


File: guava/src/com/google/common/collect/HashBiMap.java
/*
 * Copyright (C) 2007 The Guava Authors
 *
 * Licensed under the Apache License, Version 2.0 (the "License"); you may not use this file except
 * in compliance with the License. You may obtain a copy of the License at
 *
 * http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software distributed under the License
 * is distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express
 * or implied. See the License for the specific language governing permissions and limitations under
 * the License.
 */

package com.google.common.collect;

import static com.google.common.base.Preconditions.checkArgument;
import static com.google.common.collect.CollectPreconditions.checkNonnegative;
import static com.google.common.collect.CollectPreconditions.checkRemove;
import static com.google.common.collect.Hashing.smearedHash;

import com.google.common.annotations.GwtCompatible;
import com.google.common.annotations.GwtIncompatible;
import com.google.common.base.Objects;
import com.google.common.collect.Maps.IteratorBasedAbstractMap;
import com.google.j2objc.annotations.WeakOuter;

import java.io.IOException;
import java.io.ObjectInputStream;
import java.io.ObjectOutputStream;
import java.io.Serializable;
import java.util.AbstractMap;
import java.util.Arrays;
import java.util.ConcurrentModificationException;
import java.util.Iterator;
import java.util.Map;
import java.util.NoSuchElementException;
import java.util.Set;

import javax.annotation.Nullable;

/**
 * A {@link BiMap} backed by two hash tables. This implementation allows null keys and values. A
 * {@code HashBiMap} and its inverse are both serializable.
 *
 * <p>See the Guava User Guide article on <a href=
 * "https://github.com/google/guava/wiki/NewCollectionTypesExplained#bimap"> {@code BiMap}
 * </a>.
 *
 * @author Louis Wasserman
 * @author Mike Bostock
 * @since 2.0
 */
@GwtCompatible(emulated = true)
public final class HashBiMap<K, V> extends IteratorBasedAbstractMap<K, V>
    implements BiMap<K, V>, Serializable {

  /**
   * Returns a new, empty {@code HashBiMap} with the default initial capacity (16).
   */
  public static <K, V> HashBiMap<K, V> create() {
    return create(16);
  }

  /**
   * Constructs a new, empty bimap with the specified expected size.
   *
   * @param expectedSize the expected number of entries
   * @throws IllegalArgumentException if the specified expected size is negative
   */
  public static <K, V> HashBiMap<K, V> create(int expectedSize) {
    return new HashBiMap<K, V>(expectedSize);
  }

  /**
   * Constructs a new bimap containing initial values from {@code map}. The bimap is created with an
   * initial capacity sufficient to hold the mappings in the specified map.
   */
  public static <K, V> HashBiMap<K, V> create(Map<? extends K, ? extends V> map) {
    HashBiMap<K, V> bimap = create(map.size());
    bimap.putAll(map);
    return bimap;
  }

  private static final class BiEntry<K, V> extends ImmutableEntry<K, V> {
    final int keyHash;
    final int valueHash;
    @Nullable BiEntry<K, V> nextInKToVBucket;
    @Nullable BiEntry<K, V> nextInVToKBucket;

    BiEntry(K key, int keyHash, V value, int valueHash) {
      super(key, value);
      this.keyHash = keyHash;
      this.valueHash = valueHash;
    }
  }

  private static final double LOAD_FACTOR = 1.0;

  private transient BiEntry<K, V>[] hashTableKToV;
  private transient BiEntry<K, V>[] hashTableVToK;
  private transient int size;
  private transient int mask;
  private transient int modCount;

  private HashBiMap(int expectedSize) {
    init(expectedSize);
  }

  private void init(int expectedSize) {
    checkNonnegative(expectedSize, "expectedSize");
    int tableSize = Hashing.closedTableSize(expectedSize, LOAD_FACTOR);
    this.hashTableKToV = createTable(tableSize);
    this.hashTableVToK = createTable(tableSize);
    this.mask = tableSize - 1;
    this.modCount = 0;
    this.size = 0;
  }

  /**
   * Finds and removes {@code entry} from the bucket linked lists in both the
   * key-to-value direction and the value-to-key direction.
   */
  private void delete(BiEntry<K, V> entry) {
    int keyBucket = entry.keyHash & mask;
    BiEntry<K, V> prevBucketEntry = null;
    for (BiEntry<K, V> bucketEntry = hashTableKToV[keyBucket];
        true;
        bucketEntry = bucketEntry.nextInKToVBucket) {
      if (bucketEntry == entry) {
        if (prevBucketEntry == null) {
          hashTableKToV[keyBucket] = entry.nextInKToVBucket;
        } else {
          prevBucketEntry.nextInKToVBucket = entry.nextInKToVBucket;
        }
        break;
      }
      prevBucketEntry = bucketEntry;
    }

    int valueBucket = entry.valueHash & mask;
    prevBucketEntry = null;
    for (BiEntry<K, V> bucketEntry = hashTableVToK[valueBucket];
        true;
        bucketEntry = bucketEntry.nextInVToKBucket) {
      if (bucketEntry == entry) {
        if (prevBucketEntry == null) {
          hashTableVToK[valueBucket] = entry.nextInVToKBucket;
        } else {
          prevBucketEntry.nextInVToKBucket = entry.nextInVToKBucket;
        }
        break;
      }
      prevBucketEntry = bucketEntry;
    }

    size--;
    modCount++;
  }

  private void insert(BiEntry<K, V> entry) {
    int keyBucket = entry.keyHash & mask;
    entry.nextInKToVBucket = hashTableKToV[keyBucket];
    hashTableKToV[keyBucket] = entry;

    int valueBucket = entry.valueHash & mask;
    entry.nextInVToKBucket = hashTableVToK[valueBucket];
    hashTableVToK[valueBucket] = entry;

    size++;
    modCount++;
  }

  private BiEntry<K, V> seekByKey(@Nullable Object key, int keyHash) {
    for (BiEntry<K, V> entry = hashTableKToV[keyHash & mask];
        entry != null;
        entry = entry.nextInKToVBucket) {
      if (keyHash == entry.keyHash && Objects.equal(key, entry.key)) {
        return entry;
      }
    }
    return null;
  }

  private BiEntry<K, V> seekByValue(@Nullable Object value, int valueHash) {
    for (BiEntry<K, V> entry = hashTableVToK[valueHash & mask];
        entry != null;
        entry = entry.nextInVToKBucket) {
      if (valueHash == entry.valueHash && Objects.equal(value, entry.value)) {
        return entry;
      }
    }
    return null;
  }

  @Override
  public boolean containsKey(@Nullable Object key) {
    return seekByKey(key, smearedHash(key)) != null;
  }

  @Override
  public boolean containsValue(@Nullable Object value) {
    return seekByValue(value, smearedHash(value)) != null;
  }

  @Nullable
  @Override
  public V get(@Nullable Object key) {
    return Maps.valueOrNull(seekByKey(key, smearedHash(key)));
  }

  @Override
  public V put(@Nullable K key, @Nullable V value) {
    return put(key, value, false);
  }

  @Override
  public V forcePut(@Nullable K key, @Nullable V value) {
    return put(key, value, true);
  }

  private V put(@Nullable K key, @Nullable V value, boolean force) {
    int keyHash = smearedHash(key);
    int valueHash = smearedHash(value);

    BiEntry<K, V> oldEntryForKey = seekByKey(key, keyHash);
    if (oldEntryForKey != null
        && valueHash == oldEntryForKey.valueHash
        && Objects.equal(value, oldEntryForKey.value)) {
      return value;
    }

    BiEntry<K, V> oldEntryForValue = seekByValue(value, valueHash);
    if (oldEntryForValue != null) {
      if (force) {
        delete(oldEntryForValue);
      } else {
        throw new IllegalArgumentException("value already present: " + value);
      }
    }

    if (oldEntryForKey != null) {
      delete(oldEntryForKey);
    }
    BiEntry<K, V> newEntry = new BiEntry<K, V>(key, keyHash, value, valueHash);
    insert(newEntry);
    rehashIfNecessary();
    return Maps.valueOrNull(oldEntryForKey);
  }

  @Nullable
  private K putInverse(@Nullable V value, @Nullable K key, boolean force) {
    int valueHash = smearedHash(value);
    int keyHash = smearedHash(key);

    BiEntry<K, V> oldEntryForValue = seekByValue(value, valueHash);
    if (oldEntryForValue != null
        && keyHash == oldEntryForValue.keyHash
        && Objects.equal(key, oldEntryForValue.key)) {
      return key;
    }

    BiEntry<K, V> oldEntryForKey = seekByKey(key, keyHash);
    if (oldEntryForKey != null) {
      if (force) {
        delete(oldEntryForKey);
      } else {
        throw new IllegalArgumentException("value already present: " + key);
      }
    }

    if (oldEntryForValue != null) {
      delete(oldEntryForValue);
    }
    BiEntry<K, V> newEntry = new BiEntry<K, V>(key, keyHash, value, valueHash);
    insert(newEntry);
    rehashIfNecessary();
    return Maps.keyOrNull(oldEntryForValue);
  }

  private void rehashIfNecessary() {
    BiEntry<K, V>[] oldKToV = hashTableKToV;
    if (Hashing.needsResizing(size, oldKToV.length, LOAD_FACTOR)) {
      int newTableSize = oldKToV.length * 2;

      this.hashTableKToV = createTable(newTableSize);
      this.hashTableVToK = createTable(newTableSize);
      this.mask = newTableSize - 1;
      this.size = 0;

      for (int bucket = 0; bucket < oldKToV.length; bucket++) {
        BiEntry<K, V> entry = oldKToV[bucket];
        while (entry != null) {
          BiEntry<K, V> nextEntry = entry.nextInKToVBucket;
          insert(entry);
          entry = nextEntry;
        }
      }
      this.modCount++;
    }
  }

  @SuppressWarnings("unchecked")
  private BiEntry<K, V>[] createTable(int length) {
    return new BiEntry[length];
  }

  @Override
  public V remove(@Nullable Object key) {
    BiEntry<K, V> entry = seekByKey(key, smearedHash(key));
    if (entry == null) {
      return null;
    } else {
      delete(entry);
      return entry.value;
    }
  }

  @Override
  public void clear() {
    size = 0;
    Arrays.fill(hashTableKToV, null);
    Arrays.fill(hashTableVToK, null);
    modCount++;
  }

  @Override
  public int size() {
    return size;
  }

  abstract class Itr<T> implements Iterator<T> {
    int nextBucket = 0;
    BiEntry<K, V> next = null;
    BiEntry<K, V> toRemove = null;
    int expectedModCount = modCount;

    private void checkForConcurrentModification() {
      if (modCount != expectedModCount) {
        throw new ConcurrentModificationException();
      }
    }

    @Override
    public boolean hasNext() {
      checkForConcurrentModification();
      if (next != null) {
        return true;
      }
      while (nextBucket < hashTableKToV.length) {
        if (hashTableKToV[nextBucket] != null) {
          next = hashTableKToV[nextBucket++];
          return true;
        }
        nextBucket++;
      }
      return false;
    }

    @Override
    public T next() {
      checkForConcurrentModification();
      if (!hasNext()) {
        throw new NoSuchElementException();
      }

      BiEntry<K, V> entry = next;
      next = entry.nextInKToVBucket;
      toRemove = entry;
      return output(entry);
    }

    @Override
    public void remove() {
      checkForConcurrentModification();
      checkRemove(toRemove != null);
      delete(toRemove);
      expectedModCount = modCount;
      toRemove = null;
    }

    abstract T output(BiEntry<K, V> entry);
  }

  @Override
  public Set<K> keySet() {
    return new KeySet();
  }

  @WeakOuter
  private final class KeySet extends Maps.KeySet<K, V> {
    KeySet() {
      super(HashBiMap.this);
    }

    @Override
    public Iterator<K> iterator() {
      return new Itr<K>() {
        @Override
        K output(BiEntry<K, V> entry) {
          return entry.key;
        }
      };
    }

    @Override
    public boolean remove(@Nullable Object o) {
      BiEntry<K, V> entry = seekByKey(o, smearedHash(o));
      if (entry == null) {
        return false;
      } else {
        delete(entry);
        return true;
      }
    }
  }

  @Override
  public Set<V> values() {
    return inverse().keySet();
  }

  @Override
  Iterator<Entry<K, V>> entryIterator() {
    return new Itr<Entry<K, V>>() {
      @Override
      Entry<K, V> output(BiEntry<K, V> entry) {
        return new MapEntry(entry);
      }

      class MapEntry extends AbstractMapEntry<K, V> {
        BiEntry<K, V> delegate;

        MapEntry(BiEntry<K, V> entry) {
          this.delegate = entry;
        }

        @Override
        public K getKey() {
          return delegate.key;
        }

        @Override
        public V getValue() {
          return delegate.value;
        }

        @Override
        public V setValue(V value) {
          V oldValue = delegate.value;
          int valueHash = smearedHash(value);
          if (valueHash == delegate.valueHash && Objects.equal(value, oldValue)) {
            return value;
          }
          checkArgument(seekByValue(value, valueHash) == null, "value already present: %s", value);
          delete(delegate);
          BiEntry<K, V> newEntry =
              new BiEntry<K, V>(delegate.key, delegate.keyHash, value, valueHash);
          insert(newEntry);
          expectedModCount = modCount;
          if (toRemove == delegate) {
            toRemove = newEntry;
          }
          delegate = newEntry;
          return oldValue;
        }
      }
    };
  }

  private transient BiMap<V, K> inverse;

  @Override
  public BiMap<V, K> inverse() {
    return (inverse == null) ? inverse = new Inverse() : inverse;
  }

  private final class Inverse extends AbstractMap<V, K> implements BiMap<V, K>, Serializable {
    BiMap<K, V> forward() {
      return HashBiMap.this;
    }

    @Override
    public int size() {
      return size;
    }

    @Override
    public void clear() {
      forward().clear();
    }

    @Override
    public boolean containsKey(@Nullable Object value) {
      return forward().containsValue(value);
    }

    @Override
    public K get(@Nullable Object value) {
      return Maps.keyOrNull(seekByValue(value, smearedHash(value)));
    }

    @Override
    public K put(@Nullable V value, @Nullable K key) {
      return putInverse(value, key, false);
    }

    @Override
    public K forcePut(@Nullable V value, @Nullable K key) {
      return putInverse(value, key, true);
    }

    @Override
    public K remove(@Nullable Object value) {
      BiEntry<K, V> entry = seekByValue(value, smearedHash(value));
      if (entry == null) {
        return null;
      } else {
        delete(entry);
        return entry.key;
      }
    }

    @Override
    public BiMap<K, V> inverse() {
      return forward();
    }

    @Override
    public Set<V> keySet() {
      return new InverseKeySet();
    }

    @WeakOuter
    private final class InverseKeySet extends Maps.KeySet<V, K> {
      InverseKeySet() {
        super(Inverse.this);
      }

      @Override
      public boolean remove(@Nullable Object o) {
        BiEntry<K, V> entry = seekByValue(o, smearedHash(o));
        if (entry == null) {
          return false;
        } else {
          delete(entry);
          return true;
        }
      }

      @Override
      public Iterator<V> iterator() {
        return new Itr<V>() {
          @Override
          V output(BiEntry<K, V> entry) {
            return entry.value;
          }
        };
      }
    }

    @Override
    public Set<K> values() {
      return forward().keySet();
    }

    @Override
    public Set<Entry<V, K>> entrySet() {
      return new Maps.EntrySet<V, K>() {

        @Override
        Map<V, K> map() {
          return Inverse.this;
        }

        @Override
        public Iterator<Entry<V, K>> iterator() {
          return new Itr<Entry<V, K>>() {
            @Override
            Entry<V, K> output(BiEntry<K, V> entry) {
              return new InverseEntry(entry);
            }

            class InverseEntry extends AbstractMapEntry<V, K> {
              BiEntry<K, V> delegate;

              InverseEntry(BiEntry<K, V> entry) {
                this.delegate = entry;
              }

              @Override
              public V getKey() {
                return delegate.value;
              }

              @Override
              public K getValue() {
                return delegate.key;
              }

              @Override
              public K setValue(K key) {
                K oldKey = delegate.key;
                int keyHash = smearedHash(key);
                if (keyHash == delegate.keyHash && Objects.equal(key, oldKey)) {
                  return key;
                }
                checkArgument(seekByKey(key, keyHash) == null, "value already present: %s", key);
                delete(delegate);
                BiEntry<K, V> newEntry =
                    new BiEntry<K, V>(key, keyHash, delegate.value, delegate.valueHash);
                delegate = newEntry;
                insert(newEntry);
                expectedModCount = modCount;
                // This is safe because entries can only get bumped up to earlier in the iteration,
                // so they can't get revisited.
                return oldKey;
              }
            }
          };
        }
      };
    }

    Object writeReplace() {
      return new InverseSerializedForm<K, V>(HashBiMap.this);
    }
  }

  private static final class InverseSerializedForm<K, V> implements Serializable {
    private final HashBiMap<K, V> bimap;

    InverseSerializedForm(HashBiMap<K, V> bimap) {
      this.bimap = bimap;
    }

    Object readResolve() {
      return bimap.inverse();
    }
  }

  /**
   * @serialData the number of entries, first key, first value, second key, second value, and so on.
   */
  @GwtIncompatible("java.io.ObjectOutputStream")
  private void writeObject(ObjectOutputStream stream) throws IOException {
    stream.defaultWriteObject();
    Serialization.writeMap(this, stream);
  }

  @GwtIncompatible("java.io.ObjectInputStream")
  private void readObject(ObjectInputStream stream) throws IOException, ClassNotFoundException {
    stream.defaultReadObject();
    init(16);
    int size = Serialization.readCount(stream);
    Serialization.populateMap(this, stream, size);
  }

  @GwtIncompatible("Not needed in emulated source")
  private static final long serialVersionUID = 0;
}
