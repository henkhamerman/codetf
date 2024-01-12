Refactoring Types: ['Extract Method']
pan/stream/impl/AbstractCacheStream.java
package org.infinispan.stream.impl;

import org.infinispan.Cache;
import org.infinispan.CacheStream;
import org.infinispan.commons.CacheException;
import org.infinispan.container.entries.CacheEntry;
import org.infinispan.distribution.DistributionManager;
import org.infinispan.distribution.ch.ConsistentHash;
import org.infinispan.distribution.ch.impl.ReplicatedConsistentHash;
import org.infinispan.factories.ComponentRegistry;
import org.infinispan.partitionhandling.impl.PartitionHandlingManager;
import org.infinispan.remoting.transport.Address;
import org.infinispan.stream.impl.intops.IntermediateOperation;
import org.infinispan.stream.impl.termop.SegmentRetryingOperation;
import org.infinispan.stream.impl.termop.SingleRunOperation;
import org.infinispan.stream.impl.termop.object.FlatMapIteratorOperation;
import org.infinispan.stream.impl.termop.object.MapIteratorOperation;
import org.infinispan.stream.impl.termop.object.NoMapIteratorOperation;
import org.infinispan.util.concurrent.ConcurrentHashSet;
import org.infinispan.util.concurrent.TimeoutException;
import org.infinispan.util.logging.Log;
import org.infinispan.util.logging.LogFactory;

import java.util.*;
import java.util.concurrent.ConcurrentHashMap;
import java.util.concurrent.Executor;
import java.util.concurrent.TimeUnit;
import java.util.concurrent.atomic.AtomicBoolean;
import java.util.concurrent.atomic.AtomicReferenceArray;
import java.util.function.BinaryOperator;
import java.util.function.Consumer;
import java.util.function.Function;
import java.util.function.Predicate;
import java.util.function.Supplier;
import java.util.stream.BaseStream;
import java.util.stream.Collectors;
import java.util.stream.Stream;
import java.util.stream.StreamSupport;

/**
 * Abstract stream that provides all of the common functionality required for all types of Streams including the various
 * primitive types.
 * @param <T> The type returned by the stream
 * @param <S> The stream interface
 * @param <T_CONS> The consumer for this stream
 */
public abstract class AbstractCacheStream<T, S extends BaseStream<T, S>, T_CONS> implements BaseStream<T, S> {
   protected final Log log = LogFactory.getLog(getClass());

   protected final Queue<IntermediateOperation> intermediateOperations;
   protected Queue<IntermediateOperation> localIntermediateOperations;
   protected final Address localAddress;
   protected final DistributionManager dm;
   protected final Supplier<CacheStream<CacheEntry>> supplier;
   protected final ClusterStreamManager csm;
   protected final boolean includeLoader;
   protected final Executor executor;
   protected final ComponentRegistry registry;
   protected final PartitionHandlingManager partition;

   protected Runnable closeRunnable = null;

   protected boolean parallel;
   protected boolean sorted = false;
   protected boolean distinct = false;

   protected IntermediateType intermediateType = IntermediateType.NONE;

   protected Boolean parallelDistribution;
   protected boolean rehashAware = true;

   protected Set<?> keysToFilter;
   protected Set<Integer> segmentsToFilter;

   protected int distributedBatchSize;

   protected CacheStream.SegmentCompletionListener segmentCompletionListener;

   protected IteratorOperation iteratorOperation = IteratorOperation.NO_MAP;

   protected AbstractCacheStream(Address localAddress, boolean parallel, DistributionManager dm,
           Supplier<CacheStream<CacheEntry>> supplier, ClusterStreamManager<Object> csm,
           boolean includeLoader, int distributedBatchSize, Executor executor, ComponentRegistry registry) {
      this.localAddress = localAddress;
      this.parallel = parallel;
      this.dm = dm;
      this.supplier = supplier;
      this.csm = csm;
      this.includeLoader = includeLoader;
      this.distributedBatchSize = distributedBatchSize;
      this.executor = executor;
      this.registry = registry;
      this.partition = registry.getComponent(PartitionHandlingManager.class);
      intermediateOperations = new ArrayDeque<>();
   }

   protected AbstractCacheStream(AbstractCacheStream<T, S, T_CONS> other) {
      this.intermediateOperations = other.intermediateOperations;
      this.localIntermediateOperations = other.localIntermediateOperations;
      this.localAddress = other.localAddress;
      this.dm = other.dm;
      this.supplier = other.supplier;
      this.csm = other.csm;
      this.includeLoader = other.includeLoader;
      this.executor = other.executor;
      this.registry = other.registry;
      this.partition = other.partition;

      this.closeRunnable = other.closeRunnable;

      this.parallel = other.parallel;
      this.sorted = other.sorted;
      this.distinct = other.distinct;

      this.intermediateType = other.intermediateType;

      this.parallelDistribution = other.parallelDistribution;
      this.rehashAware = other.rehashAware;

      this.keysToFilter = other.keysToFilter;
      this.segmentsToFilter = other.segmentsToFilter;

      this.distributedBatchSize = other.distributedBatchSize;

      this.segmentCompletionListener = other.segmentCompletionListener;

      this.iteratorOperation = other.iteratorOperation;
   }

   protected void markSorted(IntermediateType type) {
      if (intermediateType == IntermediateType.NONE) {
         intermediateType = type;
         if (localIntermediateOperations == null) {
            localIntermediateOperations = new ArrayDeque<>();
         }
      }
      sorted = true;
   }

   protected void markDistinct(IntermediateOperation<T, S, T, S> intermediateOperation, IntermediateType type) {
      intermediateOperation.handleInjection(registry);
      if (intermediateType == IntermediateType.NONE) {
         intermediateType = type;
         if (localIntermediateOperations == null) {
            localIntermediateOperations = new ArrayDeque<>();
            intermediateOperations.add(intermediateOperation);
         }
      }
      distinct = true;
   }

   protected void markSkip(IntermediateType type) {
      if (intermediateType == IntermediateType.NONE) {
         intermediateType = type;
         if (localIntermediateOperations == null) {
            localIntermediateOperations = new ArrayDeque<>();
         }
      }
      distinct = true;
   }

   protected S addIntermediateOperation(IntermediateOperation<T, S, T, S> intermediateOperation) {
      intermediateOperation.handleInjection(registry);
      if (localIntermediateOperations == null) {
         intermediateOperations.add(intermediateOperation);
      } else {
         localIntermediateOperations.add(intermediateOperation);
      }
      return unwrap();
   }

   protected void addIntermediateOperationMap(IntermediateOperation<T, S, ?, ?> intermediateOperation) {
      intermediateOperation.handleInjection(registry);
      if (localIntermediateOperations == null) {
         intermediateOperations.add(intermediateOperation);
      } else {
         localIntermediateOperations.add(intermediateOperation);
      }
   }

   protected <T2, S2 extends BaseStream<T2, S2>, S3 extends S2> S3 addIntermediateOperationMap(
           IntermediateOperation<T, S, T2, S2> intermediateOperation, S3 stream) {
      addIntermediateOperationMap(intermediateOperation);
      return stream;
   }

   protected abstract S unwrap();

   @Override
   public boolean isParallel() {
      return parallel;
   }

   boolean getParallelDistribution() {
      return parallelDistribution == null ? true : parallelDistribution;
   }

   @Override
   public S sequential() {
      parallel = false;
      return unwrap();
   }

   @Override
   public S parallel() {
      parallel = true;
      return unwrap();
   }

   @Override
   public S unordered() {
      sorted = false;
      return unwrap();
   }

   @Override
   public S onClose(Runnable closeHandler) {
      if (this.closeRunnable == null) {
         this.closeRunnable = closeHandler;
      } else {
         this.closeRunnable = composeWithExceptions(this.closeRunnable, closeHandler);
      }
      return unwrap();
   }

   @Override
   public void close() {
      if (closeRunnable != null) {
         closeRunnable.run();
      }
   }

   <R> R performOperation(Function<S, ? extends R> function, boolean retryOnRehash, BinaryOperator<R> accumulator,
                          Predicate<? super R> earlyTerminatePredicate) {
      return performOperation(function, retryOnRehash, accumulator, earlyTerminatePredicate, true);
   }

   <R> R performOperation(Function<S, ? extends R> function, boolean retryOnRehash, BinaryOperator<R> accumulator,
           Predicate<? super R> earlyTerminatePredicate, boolean ignoreSorting) {
      // These operations are not affected by sorting, only by distinct
      if (intermediateType.shouldUseIntermediate(ignoreSorting ? false : sorted, distinct)) {
         return performIntermediateRemoteOperation(function);
      } else {
         ResultsAccumulator<R> remoteResults = new ResultsAccumulator<>(accumulator);
         if (rehashAware) {
            return performOperationRehashAware(function, retryOnRehash, remoteResults, earlyTerminatePredicate);
         } else {
            return performOperation(function, remoteResults, earlyTerminatePredicate);
         }
      }
   }

   <R> R performOperation(Function<S, ? extends R> function, ResultsAccumulator<R> remoteResults,
                          Predicate<? super R> earlyTerminatePredicate) {
      ConsistentHash ch = dm.getConsistentHash();
      TerminalOperation<R> op = new SingleRunOperation<>(intermediateOperations,
              supplierForSegments(ch, segmentsToFilter, null), function);
      UUID id = csm.remoteStreamOperation(getParallelDistribution(), parallel, ch, segmentsToFilter, keysToFilter,
              Collections.emptyMap(), includeLoader, op, remoteResults, earlyTerminatePredicate);
      try {
         R localValue = op.performOperation();
         remoteResults.onCompletion(null, Collections.emptySet(), localValue);
         try {
            if ((earlyTerminatePredicate == null || !earlyTerminatePredicate.test(localValue)) &&
                    !csm.awaitCompletion(id, 30, TimeUnit.SECONDS)) {
               throw new CacheException(new TimeoutException());
            }
         } catch (InterruptedException e) {
            throw new CacheException(e);
         }

         log.tracef("Finished operation for id %s", id);

         return remoteResults.currentValue;
      } finally {
         csm.forgetOperation(id);
      }
   }

   <R> R performOperationRehashAware(Function<S, ? extends R> function, boolean retryOnRehash,
                                     ResultsAccumulator<R> remoteResults, Predicate<? super R> earlyTerminatePredicate) {
      Set<Integer> segmentsToProcess = segmentsToFilter;
      TerminalOperation<R> op;
      do {
         remoteResults.lostSegments.clear();
         ConsistentHash ch = dm.getReadConsistentHash();
         if (retryOnRehash) {
            op = new SegmentRetryingOperation<>(intermediateOperations, supplierForSegments(ch, segmentsToProcess,
                    null), function);
         } else {
            op = new SingleRunOperation<>(intermediateOperations, supplierForSegments(ch, segmentsToProcess, null),
                    function);
         }
         UUID id = csm.remoteStreamOperationRehashAware(getParallelDistribution(), parallel, ch, segmentsToProcess,
                 keysToFilter, Collections.emptyMap(), includeLoader, op, remoteResults, earlyTerminatePredicate);
         try {
            R localValue;
            boolean localRun = ch.getMembers().contains(localAddress);
            if (localRun) {
               localValue = op.performOperation();
               // TODO: we can do this more efficiently
               if (dm.getReadConsistentHash().equals(ch)) {
                  remoteResults.onCompletion(null, ch.getPrimarySegmentsForOwner(localAddress), localValue);
               } else {
                  if (segmentsToProcess != null) {
                     Set<Integer> ourSegments = ch.getPrimarySegmentsForOwner(localAddress);
                     ourSegments.retainAll(segmentsToProcess);
                     remoteResults.onSegmentsLost(ourSegments);
                  } else {
                     remoteResults.onSegmentsLost(ch.getPrimarySegmentsForOwner(localAddress));
                  }
               }
            } else {
               // This isn't actually used because localRun short circuits first
               localValue = null;
            }
            try {
               if ((!localRun || earlyTerminatePredicate == null || !earlyTerminatePredicate.test(localValue)) &&
                       !csm.awaitCompletion(id, 30, TimeUnit.SECONDS)) {
                  throw new CacheException(new TimeoutException());
               }
            } catch (InterruptedException e) {
               throw new CacheException(e);
            }

            segmentsToProcess = new HashSet<>(remoteResults.lostSegments);
            if (!segmentsToProcess.isEmpty()) {
               log.tracef("Found %s lost segments for identifier %s", segmentsToProcess, id);
            } else {
               log.tracef("Finished rehash aware operation for id %s", id);
            }
         } finally {
            csm.forgetOperation(id);
         }
      } while (!remoteResults.lostSegments.isEmpty());

      return remoteResults.currentValue;
   }

   abstract KeyTrackingTerminalOperation<Object, T, Object> getForEach(T_CONS consumer,
           Supplier<Stream<CacheEntry>> supplier);

   void performRehashForEach(T_CONS consumer) {
      final AtomicBoolean complete = new AtomicBoolean();

      ConsistentHash segmentInfoCH = dm.getReadConsistentHash();
      KeyTrackingConsumer<Object, Object> results = new KeyTrackingConsumer<>(segmentInfoCH, (c) -> {},
              c -> c, null);
      Set<Integer> segmentsToProcess = segmentsToFilter == null ?
              new ReplicatedConsistentHash.RangeSet(segmentInfoCH.getNumSegments()) : segmentsToFilter;
      do {
         ConsistentHash ch = dm.getReadConsistentHash();
         boolean localRun = ch.getMembers().contains(localAddress);
         Set<Integer> segments;
         Set<Object> excludedKeys;
         if (localRun) {
            segments = ch.getPrimarySegmentsForOwner(localAddress);
            segments.retainAll(segmentsToProcess);

            excludedKeys = segments.stream().flatMap(s -> results.referenceArray.get(s).stream()).collect(
                    Collectors.toSet());
         } else {
            // This null is okay as it is only referenced if it was a localRun
            segments = null;
            excludedKeys = Collections.emptySet();
         }
         KeyTrackingTerminalOperation<Object, T, Object> op = getForEach(consumer, supplierForSegments(ch,
                 segmentsToProcess, excludedKeys));
         UUID id = csm.remoteStreamOperationRehashAware(getParallelDistribution(), parallel, ch, segmentsToProcess,
                 keysToFilter, new AtomicReferenceArrayToMap<>(results.referenceArray), includeLoader, op,
                 results);
         try {
            if (localRun) {
               Collection<CacheEntry<Object, Object>> localValue = op.performOperationRehashAware(results);
               // TODO: we can do this more efficiently - this hampers performance during rehash
               if (dm.getReadConsistentHash().equals(ch)) {
                  log.tracef("Found local values %s for id %s", localValue.size(), id);
                  results.onCompletion(null, segments, localValue);
               } else {
                  Set<Integer> ourSegments = ch.getPrimarySegmentsForOwner(localAddress);
                  ourSegments.retainAll(segmentsToProcess);
                  log.tracef("CH changed - making %s segments suspect for identifier %s", ourSegments, id);
                  results.onSegmentsLost(ourSegments);
                  // We keep track of those keys so we don't fire them again
                  results.onIntermediateResult(null, localValue);
               }
            }
            try {
               if (!csm.awaitCompletion(id, 30, TimeUnit.SECONDS)) {
                  throw new CacheException(new TimeoutException());
               }
            } catch (InterruptedException e) {
               throw new CacheException(e);
            }
            if (!results.lostSegments.isEmpty()) {
               segmentsToProcess = new HashSet<>(results.lostSegments);
               results.lostSegments.clear();
               log.tracef("Found %s lost segments for identifier %s", segmentsToProcess, id);
            } else {
               log.tracef("Finished rehash aware operation for id %s", id);
               complete.set(true);
            }
         } finally {
            csm.forgetOperation(id);
         }
      } while (!complete.get());
   }

   static class AtomicReferenceArrayToMap<R> extends AbstractMap<Integer, R> {
      final AtomicReferenceArray<R> array;

      AtomicReferenceArrayToMap(AtomicReferenceArray<R> array) {
         this.array = array;
      }

      @Override
      public boolean containsKey(Object o) {
         if (!(o instanceof Integer))
            return false;
         int i = (int) o;
         return 0 <= i && i < array.length();
      }

      @Override
      public R get(Object key) {
         if (!(key instanceof Integer))
            return null;
         int i = (int) key;
         if (0 <= i && i < array.length()) {
            return array.get(i);
         }
         return null;
      }

      @Override
      public int size() {
         return array.length();
      }

      @Override
      public boolean remove(Object key, Object value) {
         throw new UnsupportedOperationException();
      }

      @Override
      public void clear() {
         throw new UnsupportedOperationException();
      }

      @Override
      public Set<Entry<Integer, R>> entrySet() {
         // Do we want to implement this later?
         throw new UnsupportedOperationException();
      }
   }

   class KeyTrackingConsumer<K, V> implements ClusterStreamManager.ResultsCallback<Collection<CacheEntry<K, Object>>>,
           KeyTrackingTerminalOperation.IntermediateCollector<Collection<CacheEntry<K, Object>>> {
      final ConsistentHash ch;
      final Consumer<V> consumer;
      final Set<Integer> lostSegments = new ConcurrentHashSet<>();
      final Function<CacheEntry<K, Object>, V> valueFunction;

      final AtomicReferenceArray<Set<K>> referenceArray;

      final DistributedCacheStream.SegmentListenerNotifier listenerNotifier;

      KeyTrackingConsumer(ConsistentHash ch, Consumer<V> consumer, Function<CacheEntry<K, Object>, V> valueFunction,
              DistributedCacheStream.SegmentListenerNotifier completedSegments) {
         this.ch = ch;
         this.consumer = consumer;
         this.valueFunction = valueFunction;

         this.listenerNotifier = completedSegments;

         this.referenceArray = new AtomicReferenceArray<>(ch.getNumSegments());
         for (int i = 0; i < referenceArray.length(); ++i) {
            // We only allow 1 request per id
            referenceArray.set(i, new HashSet<>());
         }
      }

      @Override
      public Set<Integer> onIntermediateResult(Address address, Collection<CacheEntry<K, Object>> results) {
         if (results != null) {
            log.tracef("Response from %s with results %s", address, results.size());
            Set<Integer> segmentsCompleted;
            CacheEntry<K, Object>[] lastCompleted = new CacheEntry[1];
            if (listenerNotifier != null) {
               segmentsCompleted = new HashSet<>();
            } else {
               segmentsCompleted = null;
            }
            results.forEach(e -> {
               K key = e.getKey();
               int segment = ch.getSegment(key);
               Set<K> keys = referenceArray.get(segment);
               // On completion we null this out first - thus we don't need to add
               if (keys != null) {
                  keys.add(key);
               } else if (segmentsCompleted != null) {
                  segmentsCompleted.add(segment);
                  lastCompleted[0] = e;
               }
               consumer.accept(valueFunction.apply(e));
            });
            if (lastCompleted[0] != null) {
               listenerNotifier.addSegmentsForObject(lastCompleted[0], segmentsCompleted);
               return segmentsCompleted;
            }
         }
         return null;
      }

      @Override
      public void onCompletion(Address address, Set<Integer> completedSegments, Collection<CacheEntry<K, Object>> results) {
         if (!completedSegments.isEmpty()) {
            log.tracef("Completing segments %s", completedSegments);
            // We null this out first so intermediate results don't add for no reason
            completedSegments.forEach(s -> referenceArray.set(s, null));
         } else {
            log.tracef("No segments to complete from %s", address);
         }
         Set<Integer> valueSegments = onIntermediateResult(address, results);
         if (valueSegments != null) {
            completedSegments.removeAll(valueSegments);
            listenerNotifier.completeSegmentsNoResults(completedSegments);
         }
      }

      @Override
      public void onSegmentsLost(Set<Integer> segments) {
         // Have to use for loop since ConcurrentHashSet doesn't support addAll
         for (Integer segment : segments) {
            lostSegments.add(segment);
         }
      }

      @Override
      public void sendDataResonse(Collection<CacheEntry<K, Object>> response) {
         onIntermediateResult(null, response);
      }
   }

   static class ResultsAccumulator<R> implements ClusterStreamManager.ResultsCallback<R> {
      private final BinaryOperator<R> binaryOperator;
      private final Set<Integer> lostSegments = new ConcurrentHashSet<>();
      R currentValue;

      ResultsAccumulator(BinaryOperator<R> binaryOperator) {
         this.binaryOperator = binaryOperator;
      }

      @Override
      public synchronized Set<Integer> onIntermediateResult(Address address, R results) {
         if (results != null) {
            if (currentValue != null) {
               currentValue = binaryOperator.apply(currentValue, results);
            } else {
               currentValue = results;
            }
         }
         return null;
      }

      @Override
      public void onCompletion(Address address, Set<Integer> completedSegments, R results) {
         if (results != null) {
            onIntermediateResult(address, results);
         }
      }

      @Override
      public void onSegmentsLost(Set<Integer> segments) {
         // Have to use for loop since ConcurrentHashSet doesn't support addAll
         for (Integer segment : segments) {
            lostSegments.add(segment);
         }
      }
   }

   static class CollectionConsumer<R> implements ClusterStreamManager.ResultsCallback<Collection<R>>,
           KeyTrackingTerminalOperation.IntermediateCollector<Collection<R>> {
      private final Consumer<R> consumer;
      private final Set<Integer> lostSegments = new ConcurrentHashSet<>();

      CollectionConsumer(Consumer<R> consumer) {
         this.consumer = consumer;
      }

      @Override
      public Set<Integer> onIntermediateResult(Address address, Collection<R> results) {
         if (results != null) {
            results.forEach(consumer);
         }
         return null;
      }

      @Override
      public void onCompletion(Address address, Set<Integer> completedSegments, Collection<R> results) {
         onIntermediateResult(address, results);
      }

      @Override
      public void onSegmentsLost(Set<Integer> segments) {
         // Have to use for loop since ConcurrentHashSet doesn't support addAll
         for (Integer segment : segments) {
            lostSegments.add(segment);
         }
      }

      @Override
      public void sendDataResonse(Collection<R> response) {
         onIntermediateResult(null, response);
      }
   }

   protected Supplier<Stream<CacheEntry>> supplierForSegments(ConsistentHash ch, Set<Integer> targetSegments,
           Set<Object> excludedKeys) {
      if (!ch.getMembers().contains(localAddress)) {
         return () -> Stream.empty();
      }
      Set<Integer> segments = ch.getPrimarySegmentsForOwner(localAddress);
      if (targetSegments != null) {
         segments.retainAll(targetSegments);
      }

      return () -> {
         if (segments.isEmpty()) {
            return Stream.empty();
         }

         CacheStream<CacheEntry> stream = supplier.get().filterKeySegments(segments);
         if (keysToFilter != null) {
            stream = stream.filterKeys(keysToFilter);
         }
         if (excludedKeys != null) {
            return stream.filter(e -> !excludedKeys.contains(e.getKey()));
         }
         return stream;
      };
   }

   /**
    * Given two Runnables, return a Runnable that executes both in sequence,
    * even if the first throws an exception, and if both throw exceptions, add
    * any exceptions thrown by the second as suppressed exceptions of the first.
    */
   static Runnable composeWithExceptions(Runnable a, Runnable b) {
      return () -> {
         try {
            a.run();
         }
         catch (Throwable e1) {
            try {
               b.run();
            }
            catch (Throwable e2) {
               try {
                  e1.addSuppressed(e2);
               } catch (Throwable ignore) {}
            }
            throw e1;
         }
         b.run();
      };
   }

   enum IteratorOperation {
      NO_MAP {
         @Override
         public KeyTrackingTerminalOperation getOperation(Iterable<IntermediateOperation> intermediateOperations,
                                                          Supplier<Stream<CacheEntry>> supplier, int batchSize) {
            return new NoMapIteratorOperation<>(intermediateOperations, supplier, batchSize);
         }

         @Override
         public <K, V, R> Function<CacheEntry<K, V>, R> getFunction() {
            return e -> (R) e;
         }
      },
      MAP {
         @Override
         public KeyTrackingTerminalOperation getOperation(Iterable<IntermediateOperation> intermediateOperations,
                                                          Supplier<Stream<CacheEntry>> supplier, int batchSize) {
            return new MapIteratorOperation<>(intermediateOperations, supplier, batchSize);
         }
      },
      FLAT_MAP {
         @Override
         public KeyTrackingTerminalOperation getOperation(Iterable<IntermediateOperation> intermediateOperations,
                                                          Supplier<Stream<CacheEntry>> supplier, int batchSize) {
            return new FlatMapIteratorOperation<>(intermediateOperations, supplier, batchSize);
         }

         @Override
         public <V, V2> Consumer<V2> wrapConsumer(Consumer<V> consumer) {
            return new CollectionDecomposerConsumer(consumer);
         }
      };

      public abstract KeyTrackingTerminalOperation getOperation(Iterable<IntermediateOperation> intermediateOperations,
                                                       Supplier<Stream<CacheEntry>> supplier, int batchSize);

      public <K, V, R> Function<CacheEntry<K, V>, R> getFunction() {
         return e -> (R) e.getValue();
      }

      public <V, V2> Consumer<V2> wrapConsumer(Consumer<V> consumer) { return (Consumer<V2>) consumer; }
   }

   static class CollectionDecomposerConsumer<E> implements Consumer<Iterable<E>> {
      private final Consumer<E> consumer;

      CollectionDecomposerConsumer(Consumer<E> consumer) {
         this.consumer = consumer;
      }

      @Override
      public void accept(Iterable<E> es) {
         es.forEach(consumer);
      }
   }

   enum IntermediateType {
      OBJ,
      INT,
      DOUBLE,
      LONG,
      NONE {
         @Override
         public boolean shouldUseIntermediate(boolean sorted, boolean distinct) {
            return false;
         }
      };

      public boolean shouldUseIntermediate(boolean sorted, boolean distinct) {
         return sorted || distinct;
      }
   }

   <R> R performIntermediateRemoteOperation(Function<S, ? extends R> function) {
      switch (intermediateType) {
         case OBJ:
            return performObjIntermediateRemoteOperation(function);
         case INT:
            return performIntegerIntermediateRemoteOperation(function);
         case DOUBLE:
            return performDoubleIntermediateRemoteOperation(function);
         case LONG:
            return performLongIntermediateRemoteOperation(function);
         default:
            throw new IllegalStateException("No intermediate state set");
      }
   }

   <R> R performIntegerIntermediateRemoteOperation(Function<S, ? extends R> function) {
      // TODO: once we don't have to box for primitive iterators we can remove this copy
      Queue<IntermediateOperation> copyOperations = new ArrayDeque<>(localIntermediateOperations);
      PrimitiveIterator.OfInt iterator = new DistributedIntCacheStream(this).remoteIterator();
      SingleRunOperation<R, T, S> op = new SingleRunOperation<>(copyOperations,
              () -> StreamSupport.intStream(Spliterators.spliteratorUnknownSize(
                      iterator, Spliterator.CONCURRENT), parallel), function);
      return op.performOperation();
   }

   <R> R performDoubleIntermediateRemoteOperation(Function<S, ? extends R> function) {
      // TODO: once we don't have to box for primitive iterators we can remove this copy
      Queue<IntermediateOperation> copyOperations = new ArrayDeque<>(localIntermediateOperations);
      PrimitiveIterator.OfDouble iterator = new DistributedDoubleCacheStream(this).remoteIterator();
      SingleRunOperation<R, T, S> op = new SingleRunOperation<>(copyOperations,
              () -> StreamSupport.doubleStream(Spliterators.spliteratorUnknownSize(
                      iterator, Spliterator.CONCURRENT), parallel), function);
      return op.performOperation();
   }

   <R> R performLongIntermediateRemoteOperation(Function<S, ? extends R> function) {
      // TODO: once we don't have to box for primitive iterators we can remove this copy
      Queue<IntermediateOperation> copyOperations = new ArrayDeque<>(localIntermediateOperations);
      PrimitiveIterator.OfLong iterator = new DistributedLongCacheStream(this).remoteIterator();
      SingleRunOperation<R, T, S> op = new SingleRunOperation<>(copyOperations,
              () -> StreamSupport.longStream(Spliterators.spliteratorUnknownSize(
                      iterator, Spliterator.CONCURRENT), parallel), function);
      return op.performOperation();
   }

   <R> R performObjIntermediateRemoteOperation(Function<S, ? extends R> function) {
      Iterator<Object> iterator = new DistributedCacheStream<>(this).remoteIterator();
      SingleRunOperation<R, T, S> op = new SingleRunOperation<>(localIntermediateOperations,
              () -> StreamSupport.stream(Spliterators.spliteratorUnknownSize(
                      iterator, Spliterator.CONCURRENT), parallel), function);
      return op.performOperation();
   }
}


File: core/src/main/java/org/infinispan/stream/impl/DistributedCacheStream.java
package org.infinispan.stream.impl;

import org.infinispan.CacheStream;
import org.infinispan.commons.CacheException;
import org.infinispan.commons.marshall.Externalizer;
import org.infinispan.commons.marshall.SerializeWith;
import org.infinispan.commons.util.CloseableIterator;
import org.infinispan.container.entries.CacheEntry;
import org.infinispan.distribution.DistributionManager;
import org.infinispan.distribution.ch.ConsistentHash;
import org.infinispan.distribution.ch.impl.ReplicatedConsistentHash;
import org.infinispan.factories.ComponentRegistry;
import org.infinispan.remoting.transport.Address;
import org.infinispan.stream.impl.intops.object.*;
import org.infinispan.stream.impl.termop.SingleRunOperation;
import org.infinispan.stream.impl.termop.object.ForEachOperation;
import org.infinispan.stream.impl.termop.object.NoMapIteratorOperation;
import org.infinispan.util.CloseableSuppliedIterator;
import org.infinispan.util.CloseableSupplier;
import org.infinispan.util.concurrent.TimeoutException;

import java.io.IOException;
import java.io.ObjectInput;
import java.io.ObjectOutput;
import java.io.Serializable;
import java.util.*;
import java.util.concurrent.ArrayBlockingQueue;
import java.util.concurrent.BlockingQueue;
import java.util.concurrent.Executor;
import java.util.concurrent.TimeUnit;
import java.util.concurrent.atomic.AtomicBoolean;
import java.util.concurrent.locks.Condition;
import java.util.concurrent.locks.Lock;
import java.util.concurrent.locks.ReentrantLock;
import java.util.function.*;
import java.util.stream.Collector;
import java.util.stream.Collectors;
import java.util.stream.DoubleStream;
import java.util.stream.IntStream;
import java.util.stream.LongStream;
import java.util.stream.Stream;
import java.util.stream.StreamSupport;

/**
 * Implementation of {@link CacheStream} that provides support for lazily distributing stream methods to appropriate
 * nodes
 * @param <R> The type of the stream
 */
public class DistributedCacheStream<R> extends AbstractCacheStream<R, Stream<R>, Consumer<? super R>>
        implements CacheStream<R> {

   // This is a hack to allow for cast to work properly, since Java doesn't work as well with nested generics
   protected static Supplier<CacheStream<CacheEntry>> supplierStreamCast(Supplier supplier) {
      return supplier;
   }

   /**
    * Standard constructor requiring all pertinent information to properly utilize a distributed cache stream
    * @param localAddress the local address for this node
    * @param parallel whether or not this stream is parallel
    * @param dm the distribution manager to find out what keys map where
    * @param supplier a supplier of local cache stream instances.
    * @param csm manager that handles sending out messages to other nodes
    * @param includeLoader whether or not a cache loader should be utilized for these operations
    * @param distributedBatchSize default size of distributed batches
    * @param executor executor to be used for certain operations that require async processing (ie. iterator)
    */
   public <K, V> DistributedCacheStream(Address localAddress, boolean parallel, DistributionManager dm,
           Supplier<CacheStream<CacheEntry<K, V>>> supplier, ClusterStreamManager csm, boolean includeLoader,
           int distributedBatchSize, Executor executor, ComponentRegistry registry) {
      super(localAddress, parallel, dm, supplierStreamCast(supplier), csm, includeLoader, distributedBatchSize,
              executor, registry);
   }

   /**
    * Constructor that also allows a simple map method to be inserted first to change to another type.  This is
    * important because the {@link CacheStream#map(Function)} currently doesn't return a {@link CacheStream}.  If this
    * is changed we can remove this constructor and update references accordingly.
    * @param localAddress the local address for this node
    * @param parallel whether or not this stream is parallel
    * @param dm the distribution manager to find out what keys map where
    * @param supplier a supplier of local cache stream instances.
    * @param csm manager that handles sending out messages to other nodes
    * @param includeLoader whether or not a cache loader should be utilized for these operations
    * @param distributedBatchSize default size of distributed batches
    * @param executor executor to be used for certain operations that require async processing (ie. iterator)
    * @param function initial function to apply to the stream to change the type
    */
   public <K, V> DistributedCacheStream(Address localAddress, boolean parallel, DistributionManager dm,
           Supplier<CacheStream<CacheEntry<K, V>>> supplier, ClusterStreamManager csm, boolean includeLoader,
           int distributedBatchSize, Executor executor, ComponentRegistry registry,
           Function<? super CacheEntry<K, V>, R> function) {
      super(localAddress, parallel, dm, supplierStreamCast(supplier), csm, includeLoader, distributedBatchSize, executor,
              registry);
      intermediateOperations.add(new MapOperation(function));
      iteratorOperation = IteratorOperation.MAP;
   }

   /**
    * This constructor is to be used only when a user calls a map or flat map method changing back to a regular
    * Stream from an IntStream, DoubleStream etc.
    * @param other other instance of {@link AbstractCacheStream} to copy details from
    */
   protected DistributedCacheStream(AbstractCacheStream other) {
      super(other);
   }

   @Override
   protected Stream<R> unwrap() {
      return this;
   }

   // Intermediate operations that are stored for lazy evalulation

   @Override
   public Stream<R> filter(Predicate<? super R> predicate) {
      return addIntermediateOperation(new FilterOperation<>(predicate));
   }

   @Override
   public <R1> Stream<R1> map(Function<? super R, ? extends R1> mapper) {
      if (iteratorOperation != IteratorOperation.FLAT_MAP) {
         iteratorOperation = IteratorOperation.MAP;
      }
      return addIntermediateOperationMap(new MapOperation<>(mapper), (Stream<R1>) this);
   }

   @Override
   public IntStream mapToInt(ToIntFunction<? super R> mapper) {
      if (iteratorOperation != IteratorOperation.FLAT_MAP) {
         iteratorOperation = IteratorOperation.MAP;
      }
      return addIntermediateOperationMap(new MapToIntOperation<>(mapper), intCacheStream());
   }

   @Override
   public LongStream mapToLong(ToLongFunction<? super R> mapper) {
      if (iteratorOperation != IteratorOperation.FLAT_MAP) {
         iteratorOperation = IteratorOperation.MAP;
      }
      return addIntermediateOperationMap(new MapToLongOperation<>(mapper), longCacheStream());
   }

   @Override
   public DoubleStream mapToDouble(ToDoubleFunction<? super R> mapper) {
      if (iteratorOperation != IteratorOperation.FLAT_MAP) {
         iteratorOperation = IteratorOperation.MAP;
      }
      return addIntermediateOperationMap(new MapToDoubleOperation<>(mapper), doubleCacheStream());
   }

   @Override
   public <R1> Stream<R1> flatMap(Function<? super R, ? extends Stream<? extends R1>> mapper) {
      iteratorOperation = IteratorOperation.FLAT_MAP;
      return addIntermediateOperationMap(new FlatMapOperation<>(mapper), (Stream<R1>) this);
   }

   @Override
   public IntStream flatMapToInt(Function<? super R, ? extends IntStream> mapper) {
      iteratorOperation = IteratorOperation.FLAT_MAP;
      return addIntermediateOperationMap(new FlatMapToIntOperation<>(mapper), intCacheStream());
   }

   @Override
   public LongStream flatMapToLong(Function<? super R, ? extends LongStream> mapper) {
      iteratorOperation = IteratorOperation.FLAT_MAP;
      return addIntermediateOperationMap(new FlatMapToLongOperation<>(mapper), longCacheStream());
   }

   @Override
   public DoubleStream flatMapToDouble(Function<? super R, ? extends DoubleStream> mapper) {
      iteratorOperation = IteratorOperation.FLAT_MAP;
      return addIntermediateOperationMap(new FlatMapToDoubleOperation<>(mapper), doubleCacheStream());
   }

   @Override
   public Stream<R> distinct() {
      DistinctOperation op = DistinctOperation.getInstance();
      markDistinct(op, IntermediateType.OBJ);
      return addIntermediateOperation(op);
   }

   @Override
   public Stream<R> sorted() {
      markSorted(IntermediateType.OBJ);
      return addIntermediateOperation(SortedOperation.getInstance());
   }

   @Override
   public Stream<R> sorted(Comparator<? super R> comparator) {
      markSorted(IntermediateType.OBJ);
      return addIntermediateOperation(new SortedComparatorOperation<>(comparator));
   }

   @Override
   public Stream<R> peek(Consumer<? super R> action) {
      return addIntermediateOperation(new PeekOperation<>(action));
   }

   @Override
   public Stream<R> limit(long maxSize) {
      LimitOperation op = new LimitOperation<>(maxSize);
      markDistinct(op, IntermediateType.OBJ);
      return addIntermediateOperation(op);
   }

   @Override
   public Stream<R> skip(long n) {
      SkipOperation op = new SkipOperation<>(n);
      markSkip(IntermediateType.OBJ);
      return addIntermediateOperation(op);
   }

   // Now we have terminal operators

   @Override
   public R reduce(R identity, BinaryOperator<R> accumulator) {
      return performOperation(TerminalFunctions.reduceFunction(identity, accumulator), true, accumulator, null);
   }

   @Override
   public Optional<R> reduce(BinaryOperator<R> accumulator) {
      R value = performOperation(TerminalFunctions.reduceFunction(accumulator), true,
              (e1, e2) -> {
                 if (e1 != null) {
                    if (e2 != null) {
                       return accumulator.apply(e1, e2);
                    }
                    return e1;
                 }
                 return e2;
              }, null);
      return Optional.ofNullable(value);
   }

   @Override
   public <U> U reduce(U identity, BiFunction<U, ? super R, U> accumulator, BinaryOperator<U> combiner) {
      return performOperation(TerminalFunctions.reduceFunction(identity, accumulator, combiner), true, combiner, null);
   }

   /**
    * {@inheritDoc}
    * Note: this method doesn't pay attention to ordering constraints and any sorting performed on the stream will
    * be ignored by this terminal operator.  If you wish to have an ordered collector use the
    * {@link DistributedCacheStream#collect(Collector)} method making sure the
    * {@link java.util.stream.Collector.Characteristics#UNORDERED} property is not set.
    * @param supplier
    * @param accumulator
    * @param combiner
    * @param <R1>
    * @return
    */
   @Override
   public <R1> R1 collect(Supplier<R1> supplier, BiConsumer<R1, ? super R> accumulator, BiConsumer<R1, R1> combiner) {
      return performOperation(TerminalFunctions.collectFunction(supplier, accumulator, combiner), true,
              (e1, e2) -> {
                 combiner.accept(e1, e2);
                 return e1;
              }, null);
   }

   @SerializeWith(value = IdentifyFinishCollector.IdentityFinishCollectorExternalizer.class)
   private static final class IdentifyFinishCollector<T, A> implements Collector<T, A, A> {
      private final Collector<T, A, ?> realCollector;

      IdentifyFinishCollector(Collector<T, A, ?> realCollector) {
         this.realCollector = realCollector;
      }

      @Override
      public Supplier<A> supplier() {
         return realCollector.supplier();
      }

      @Override
      public BiConsumer<A, T> accumulator() {
         return realCollector.accumulator();
      }

      @Override
      public BinaryOperator<A> combiner() {
         return realCollector.combiner();
      }

      @Override
      public Function<A, A> finisher() {
         return null;
      }

      @Override
      public Set<Characteristics> characteristics() {
         Set<Characteristics> characteristics = realCollector.characteristics();
         if (characteristics.size() == 0) {
            return EnumSet.of(Characteristics.IDENTITY_FINISH);
         } else {
            Set<Characteristics> tweaked = EnumSet.copyOf(characteristics);
            tweaked.add(Characteristics.IDENTITY_FINISH);
            return tweaked;
         }
      }

      public static final class IdentityFinishCollectorExternalizer implements Externalizer<IdentifyFinishCollector> {
         @Override
         public void writeObject(ObjectOutput output, IdentifyFinishCollector object) throws IOException {
            output.writeObject(object.realCollector);
         }

         @Override
         public IdentifyFinishCollector readObject(ObjectInput input) throws IOException, ClassNotFoundException {
            return new IdentifyFinishCollector((Collector) input.readObject());
         }
      }
   }

   @Override
   public <R1, A> R1 collect(Collector<? super R, A, R1> collector) {
      if (sorted) {
         // If we have a sorted map then we only have to worry about it being sorted if the collector is not
         // unordered
         sorted = !collector.characteristics().contains(Collector.Characteristics.UNORDERED);
      }
      // If it is not an identify finish we have to prevent the remote finisher, and apply locally only after
      // everything is combined.
      if (collector.characteristics().contains(Collector.Characteristics.IDENTITY_FINISH)) {
         return performOperation(TerminalFunctions.collectorFunction(collector), true,
                 (BinaryOperator<R1>) collector.combiner(), null, false);
      } else {
         // Need to wrap collector to force identity finish
         A intermediateResult = performOperation(TerminalFunctions.collectorFunction(
                 new IdentifyFinishCollector<>(collector)), true, collector.combiner(), null, false);
         return collector.finisher().apply(intermediateResult);
      }
   }

   @Override
   public Optional<R> min(Comparator<? super R> comparator) {
      R value = performOperation(TerminalFunctions.minFunction(comparator), false,
              (e1, e2) -> {
                 if (e1 != null) {
                    if (e2 != null) {
                       return comparator.compare(e1, e2) > 0 ? e2 : e1;
                    } else {
                       return e1;
                    }
                 }
                 return e2;
              }, null);
      return Optional.ofNullable(value);
   }

   @Override
   public Optional<R> max(Comparator<? super R> comparator) {
      R value = performOperation(TerminalFunctions.maxFunction(comparator), false,
              (e1, e2) -> {
                 if (e1 != null) {
                    if (e2 != null) {
                       return comparator.compare(e1, e2) > 0 ? e1 : e2;
                    } else {
                       return e1;
                    }
                 }
                 return e2;
              }, null);
      return Optional.ofNullable(value);
   }

   @Override
   public boolean anyMatch(Predicate<? super R> predicate) {
      return performOperation(TerminalFunctions.anyMatchFunction(predicate), false, Boolean::logicalOr, b -> b);
   }

   @Override
   public boolean allMatch(Predicate<? super R> predicate) {
      return performOperation(TerminalFunctions.allMatchFunction(predicate), false, Boolean::logicalAnd, b -> !b);
   }

   @Override
   public boolean noneMatch(Predicate<? super R> predicate) {
      return performOperation(TerminalFunctions.noneMatchFunction(predicate), false, Boolean::logicalAnd, b -> !b);
   }

   @Override
   public Optional<R> findFirst() {
      if (intermediateType.shouldUseIntermediate(sorted, distinct)) {
         Iterator<R> iterator = iterator();
         SingleRunOperation<Optional<R>, R, Stream<R>> op = new SingleRunOperation<>(localIntermediateOperations,
                 () -> StreamSupport.stream(Spliterators.spliteratorUnknownSize(
                         iterator, Spliterator.CONCURRENT | Spliterator.NONNULL), parallel), s -> s.findFirst());
         return op.performOperation();
      } else {
         return findAny();
      }
   }

   @Override
   public Optional<R> findAny() {
      R value = performOperation(TerminalFunctions.findAnyFunction(), false, (r1, r2) -> r1 == null ? r2 : r1,
              a -> a != null);
      return Optional.ofNullable(value);
   }

   @Override
   public long count() {
      return performOperation(TerminalFunctions.countFunction(), true, (l1, l2) -> l1 + l2, null);
   }


   // The next ones are key tracking terminal operators

   @Override
   public Iterator<R> iterator() {
      if (intermediateType.shouldUseIntermediate(sorted, distinct)) {
         return performIntermediateRemoteOperation(s -> s.iterator());
      } else {
         return remoteIterator();
      }
   }

   Iterator<R> remoteIterator() {
      BlockingQueue<R> queue = new ArrayBlockingQueue<>(distributedBatchSize);

      final AtomicBoolean complete = new AtomicBoolean();

      Lock nextLock = new ReentrantLock();
      Condition nextCondition = nextLock.newCondition();

      Consumer<R> consumer = new HandOffConsumer(queue, complete, nextLock, nextCondition);

      IteratorSupplier<R> supplier = new IteratorSupplier(queue, complete, nextLock, nextCondition, csm);

      boolean iteratorParallelDistribute = parallelDistribution == null ? false : parallelDistribution;

      if (rehashAware) {
         ConsistentHash segmentInfoCH = dm.getReadConsistentHash();
         SegmentListenerNotifier<R> listenerNotifier;
         if (segmentCompletionListener != null) {
             listenerNotifier = new SegmentListenerNotifier<>(
                    segmentCompletionListener);
            supplier.setConsumer(listenerNotifier);
         } else {
            listenerNotifier = null;
         }
         KeyTrackingConsumer<Object, R> results = new KeyTrackingConsumer<>(segmentInfoCH,
                 iteratorOperation.wrapConsumer(consumer), iteratorOperation.getFunction(),
                 listenerNotifier);
         Thread thread = Thread.currentThread();
         executor.execute(() -> {
            try {
               log.tracef("Thread %s submitted iterator request for stream", thread);
               Set<Integer> segmentsToProcess = segmentsToFilter == null ?
                       new ReplicatedConsistentHash.RangeSet(segmentInfoCH.getNumSegments()) : segmentsToFilter;
               do {
                  ConsistentHash ch = dm.getReadConsistentHash();
                  boolean runLocal = ch.getMembers().contains(localAddress);
                  Set<Integer> segments;
                  Set<Object> excludedKeys;
                  if (runLocal) {
                     segments = ch.getPrimarySegmentsForOwner(localAddress);
                     segments.retainAll(segmentsToProcess);

                     excludedKeys = segments.stream().flatMap(s -> results.referenceArray.get(s).stream())
                             .collect(Collectors.toSet());
                  } else {
                     segments = null;
                     excludedKeys = Collections.emptySet();
                  }
                  KeyTrackingTerminalOperation<Object, R, Object> op = iteratorOperation.getOperation(
                          intermediateOperations, supplierForSegments(ch, segmentsToProcess, excludedKeys),
                          distributedBatchSize);
                  UUID id = csm.remoteStreamOperationRehashAware(iteratorParallelDistribute, parallel, ch,
                          segmentsToProcess, keysToFilter, new AtomicReferenceArrayToMap<>(results.referenceArray),
                          includeLoader, op, results);
                  supplier.pending = id;
                  try {
                     if (runLocal) {
                        Collection<CacheEntry<Object, Object>> localValue = op.performOperationRehashAware(results);
                        // TODO: we can do this more efficiently - this hampers performance during rehash
                        if (dm.getReadConsistentHash().equals(ch)) {
                           log.tracef("Found local values %s for id %s", localValue.size(), id);
                           results.onCompletion(null, segments, localValue);
                        } else {
                           Set<Integer> ourSegments = ch.getPrimarySegmentsForOwner(localAddress);
                           ourSegments.retainAll(segmentsToProcess);
                           log.tracef("CH changed - making %s segments suspect for identifier %s", ourSegments, id);
                           results.onSegmentsLost(ourSegments);
                        }
                     }
                     try {
                        if (!csm.awaitCompletion(id, 30, TimeUnit.SECONDS)) {
                           throw new TimeoutException();
                        }
                     } catch (InterruptedException e) {
                        throw new CacheException(e);
                     }
                     if (!results.lostSegments.isEmpty()) {
                        segmentsToProcess = new HashSet<>(results.lostSegments);
                        results.lostSegments.clear();
                        log.tracef("Found %s lost segments for identifier %s", segmentsToProcess, id);
                     } else {
                        supplier.close();
                        log.tracef("Finished rehash aware operation for id %s", id);
                     }
                  } finally {
                     csm.forgetOperation(id);
                  }
               } while (!complete.get());
            } catch (CacheException e) {
               log.trace("Encountered local cache exception for stream", e);
               supplier.close(e);
            } catch (Throwable t) {
               log.trace("Encountered local throwable for stream", t);
               supplier.close(new CacheException(t));
            }
         });
      } else {
         CollectionConsumer<R> remoteResults = new CollectionConsumer<>(consumer);
         ConsistentHash ch = dm.getConsistentHash();
         NoMapIteratorOperation<?, R> op = new NoMapIteratorOperation<>(intermediateOperations, supplierForSegments(ch,
                 segmentsToFilter, null), distributedBatchSize);


         Thread thread = Thread.currentThread();
         executor.execute(() -> {
            try {
               log.tracef("Thread %s submitted iterator request for stream", thread);
               UUID id = csm.remoteStreamOperation(iteratorParallelDistribute, parallel, ch, segmentsToFilter,
                       keysToFilter, Collections.emptyMap(), includeLoader, op, remoteResults);
               supplier.pending = id;
               try {
                  Collection<R> localValue = op.performOperation(remoteResults);
                  remoteResults.onCompletion(null, Collections.emptySet(), localValue);
                  try {
                     if (!csm.awaitCompletion(id, 30, TimeUnit.SECONDS)) {
                        throw new TimeoutException();
                     }
                  } catch (InterruptedException e) {
                     throw new CacheException(e);
                  }

                  supplier.close();
               } finally {
                  csm.forgetOperation(id);
               }
            } catch (CacheException e) {
               log.trace("Encountered local cache exception for stream", e);
               supplier.close(e);
            } catch (Throwable t) {
               log.trace("Encountered local throwable for stream", t);
               supplier.close(new CacheException(t));
            }
         });
      }

      CloseableIterator<R> closeableIterator = new CloseableSuppliedIterator<>(supplier);
      onClose(() -> supplier.close());
      return closeableIterator;
   }

   static class HandOffConsumer<R> implements Consumer<R> {
      private final BlockingQueue<R> queue;
      private final AtomicBoolean completed;
      private final Lock nextLock;
      private final Condition nextCondition;

      HandOffConsumer(BlockingQueue<R> queue, AtomicBoolean completed, Lock nextLock, Condition nextCondition) {
         this.queue = queue;
         this.completed = completed;
         this.nextLock = nextLock;
         this.nextCondition = nextCondition;
      }

      @Override
      public void accept(R rs) {
         // TODO: we don't awake people if they are waiting until we fill up the queue or process retrieves all values
         // is this the reason for slowdown?
         if (!queue.offer(rs)) {
            if (!completed.get()) {
               // Signal anyone waiting for values to consume from the queue
               nextLock.lock();
               try {
                  nextCondition.signalAll();
               } finally {
                  nextLock.unlock();
               }
               while (!completed.get()) {
                  // We keep trying to offer the value until it takes it.  In this case we check the completed after
                  // each time to make sure the iterator wasn't closed early
                  try {
                     if (queue.offer(rs, 100, TimeUnit.MILLISECONDS)) {
                        break;
                     }
                  } catch (InterruptedException e) {
                     throw new CacheException(e);
                  }
               }
            }
         }
      }
   }

   static class SegmentListenerNotifier<T> implements Consumer<T> {
      private final SegmentCompletionListener listener;
      // we know the objects will always be ==
      private final Map<T, Set<Integer>> segmentsByObject = new IdentityHashMap<>();

      SegmentListenerNotifier(SegmentCompletionListener listener) {
         this.listener = listener;
      }

      @Override
      public void accept(T t) {
         Set<Integer> segments = segmentsByObject.remove(t);
         if (segments != null) {
            listener.segmentCompleted(segments);
         }
      }

      public void addSegmentsForObject(T object, Set<Integer> segments) {
         segmentsByObject.put(object, segments);
      }

      public void completeSegmentsNoResults(Set<Integer> segments) {
         listener.segmentCompleted(segments);
      }
   }

   static class IteratorSupplier<R> implements CloseableSupplier<R> {
      private final BlockingQueue<R> queue;
      private final AtomicBoolean completed;
      private final Lock nextLock;
      private final Condition nextCondition;
      private final ClusterStreamManager<?> clusterStreamManager;

      CacheException exception;
      volatile UUID pending;

      private Consumer<R> consumer;

      IteratorSupplier(BlockingQueue<R> queue, AtomicBoolean completed, Lock nextLock, Condition nextCondition,
              ClusterStreamManager<?> clusterStreamManager) {
         this.queue = queue;
         this.completed = completed;
         this.nextLock = nextLock;
         this.nextCondition = nextCondition;
         this.clusterStreamManager = clusterStreamManager;
      }

      @Override
      public void close() {
         close(null);
      }

      public void close(CacheException e) {
         nextLock.lock();
         try {
            if (!completed.getAndSet(true)) {
               if (e != null) {
                  exception = e;
               }
            }
            if (pending != null) {
               clusterStreamManager.forgetOperation(pending);
               pending = null;
            }
            nextCondition.signalAll();
         } finally {
            nextLock.unlock();
         }
      }

      @Override
      public R get() {
         R entry = queue.poll();
         if (entry == null) {
            if (completed.get()) {
               if (exception != null) {
                  throw exception;
               }
               return null;
            }
            nextLock.lock();
            try {
               boolean interrupted = false;
               while ((entry = queue.poll()) == null && !completed.get()) {
                  try {
                     nextCondition.await(100, TimeUnit.MILLISECONDS);
                  } catch (InterruptedException e) {
                     // If interrupted, we just loop back around
                     interrupted = true;
                  }
               }
               if (entry == null) {
                  if (exception != null) {
                     throw exception;
                  }
                  return null;
               } else if (interrupted) {
                  // Now reset the interrupt state before returning
                  Thread.currentThread().interrupt();
               }
            } finally {
               nextLock.unlock();
            }
         }
         if (consumer != null && entry != null) {
            consumer.accept(entry);
         }
         return entry;
      }

      public void setConsumer(Consumer<R> consumer) {
         this.consumer = consumer;
      }
   }

   @Override
   public Spliterator<R> spliterator() {
      return Spliterators.spliterator(iterator(), Long.MAX_VALUE, Spliterator.CONCURRENT);
   }

   @Override
   public void forEach(Consumer<? super R> action) {
      if (!rehashAware) {
         performOperation(TerminalFunctions.forEachFunction(action), false, (v1, v2) -> null, null);
      } else {
         performRehashForEach(action);
      }
   }

   @Override
   KeyTrackingTerminalOperation getForEach(Consumer<? super R> consumer, Supplier<Stream<CacheEntry>> supplier) {
      return new ForEachOperation<>(intermediateOperations, supplier, distributedBatchSize, consumer);
   }

   @Override
   public void forEachOrdered(Consumer<? super R> action) {
      if (sorted) {
         Iterator<R> iterator = iterator();
         SingleRunOperation<Void, R,Stream<R>> op = new SingleRunOperation<>(localIntermediateOperations,
                 () -> StreamSupport.stream(Spliterators.spliteratorUnknownSize(
                         iterator, Spliterator.CONCURRENT | Spliterator.NONNULL), parallel), s -> {
            s.forEachOrdered(action);
            return null;
         });
         op.performOperation();
      } else {
         forEach(action);
      }
   }

   @Override
   public Object[] toArray() {
      return performOperation(TerminalFunctions.toArrayFunction(), false,
              (v1, v2) -> {
                 Object[] array = Arrays.copyOf(v1, v1.length + v2.length);
                 System.arraycopy(v2, 0, array, v1.length, v2.length);
                 return array;
              }, null, false);
   }

   @Override
   public <A> A[] toArray(IntFunction<A[]> generator) {
      return performOperation(TerminalFunctions.toArrayFunction(generator), false,
              (v1, v2) -> {
                 A[] array = generator.apply(v1.length + v2.length);
                 System.arraycopy(v1, 0, array, 0, v1.length);
                 System.arraycopy(v2, 0, array, v1.length, v2.length);
                 return array;
              }, null, false);
   }

   // These are the custom added methods for cache streams

   @Override
   public CacheStream<R> sequentialDistribution() {
      parallelDistribution = false;
      return this;
   }

   @Override
   public CacheStream<R> parallelDistribution() {
      parallelDistribution = true;
      return this;
   }

   @Override
   public CacheStream<R>
   filterKeySegments(Set<Integer> segments) {
      segmentsToFilter = segments;
      return this;
   }

   @Override
   public CacheStream<R> filterKeys(Set<?> keys) {
      keysToFilter = keys;
      return this;
   }

   @Override
   public CacheStream<R> distributedBatchSize(int batchSize) {
      distributedBatchSize = batchSize;
      return this;
   }

   @Override
   public CacheStream<R> segmentCompletionListener(SegmentCompletionListener listener) {
      if (segmentCompletionListener == null) {
         segmentCompletionListener = listener;
      } else {
         segmentCompletionListener = composeWithExceptions(segmentCompletionListener, listener);
      }
      return this;
   }

   @Override
   public CacheStream<R> disableRehashAware() {
      rehashAware = false;
      return this;
   }

   protected DistributedIntCacheStream intCacheStream() {
      return new DistributedIntCacheStream(this);
   }

   protected DistributedDoubleCacheStream doubleCacheStream() {
      return new DistributedDoubleCacheStream(this);
   }

   protected DistributedLongCacheStream longCacheStream() {
      return new DistributedLongCacheStream(this);
   }

   /**
    * Given two SegmentCompletionListener, return a SegmentCompletionListener that
    * executes both in sequence, even if the first throws an exception, and if both
    * throw exceptions, add any exceptions thrown by the second as suppressed
    * exceptions of the first.
    */
   protected static CacheStream.SegmentCompletionListener composeWithExceptions(CacheStream.SegmentCompletionListener a,
                                                                                CacheStream.SegmentCompletionListener b) {
      return (segments) -> {
         try {
            a.segmentCompleted(segments);
         }
         catch (Throwable e1) {
            try {
               b.segmentCompleted(segments);
            }
            catch (Throwable e2) {
               try {
                  e1.addSuppressed(e2);
               } catch (Throwable ignore) {}
            }
            throw e1;
         }
         b.segmentCompleted(segments);
      };
   }
}


File: core/src/main/java/org/infinispan/stream/impl/tx/TxDistributedCacheStream.java
package org.infinispan.stream.impl.tx;

import org.infinispan.CacheStream;
import org.infinispan.container.entries.CacheEntry;
import org.infinispan.context.impl.LocalTxInvocationContext;
import org.infinispan.distribution.DistributionManager;
import org.infinispan.distribution.ch.ConsistentHash;
import org.infinispan.factories.ComponentRegistry;
import org.infinispan.remoting.transport.Address;
import org.infinispan.stream.impl.AbstractCacheStream;
import org.infinispan.stream.impl.DistributedCacheStream;
import org.infinispan.stream.impl.DistributedDoubleCacheStream;
import org.infinispan.stream.impl.DistributedIntCacheStream;
import org.infinispan.stream.impl.DistributedLongCacheStream;

import java.util.Set;
import java.util.concurrent.Executor;
import java.util.function.Function;
import java.util.function.Supplier;
import java.util.stream.Collectors;
import java.util.stream.Stream;

/**
 * A distributed cache stream that also utilizes transactional awareness.  Basically this adds functionality to
 * take items from the local tx context and add them to the local stream that is produced to enable our stream to
 * operate upon entries in the context that don't map to our segments that are normally ignored in a distributed
 * stream.
 * @param <R> the type of stream
 */
public class TxDistributedCacheStream<R> extends DistributedCacheStream<R> {
   private final Address localAddress;
   private final LocalTxInvocationContext ctx;
   private final ConsistentHash hash;

   public <K, V> TxDistributedCacheStream(Address localAddress, boolean parallel, DistributionManager dm,
           Supplier<CacheStream<CacheEntry<K, V>>> supplier, TxClusterStreamManager<?> csm, boolean includeLoader,
           int distributedBatchSize, Executor executor, ComponentRegistry registry, LocalTxInvocationContext ctx) {
      super(localAddress, parallel, dm, supplier, csm, includeLoader, distributedBatchSize, executor, registry);
      this.localAddress = localAddress;
      this.hash = dm.getConsistentHash();
      this.ctx = ctx;
   }

   public <K, V> TxDistributedCacheStream(Address localAddress, boolean parallel, DistributionManager dm,
           Supplier<CacheStream<CacheEntry<K, V>>> supplier, TxClusterStreamManager<?> csm, boolean includeLoader,
           int distributedBatchSize, Executor executor, ComponentRegistry registry,
           Function<? super CacheEntry<K, V>, R> function, LocalTxInvocationContext ctx) {
      super(localAddress, parallel, dm, supplier, csm, includeLoader, distributedBatchSize, executor, registry, function);
      this.localAddress = localAddress;
      this.hash = dm.getConsistentHash();
      this.ctx = ctx;
   }

   TxDistributedCacheStream(AbstractCacheStream other, Address localAddress, ConsistentHash hash,
           LocalTxInvocationContext ctx) {
      super(other);
      this.localAddress = localAddress;
      this.hash = hash;
      this.ctx = ctx;
   }

   @Override
   protected Supplier<Stream<CacheEntry>> supplierForSegments(ConsistentHash ch, Set<Integer> targetSegments,
           Set<Object> excludedKeys) {
      return () -> {
         Supplier<Stream<CacheEntry>> supplier = super.supplierForSegments(ch, targetSegments, excludedKeys);
         // Now we have to add entries that aren't mapped to our local segments since we are excluding those
         // remotely via {@link TxClusterStreamManager} using the same hash
         Set<CacheEntry> set = ctx.getLookedUpEntries().values().stream().filter(
                 e -> !localAddress.equals(ch.locatePrimaryOwner(e.getKey()))).collect(Collectors.toSet());
         Stream<CacheEntry> suppliedStream = supplier.get();
         if (!set.isEmpty()) {
            return Stream.concat(set.stream(), suppliedStream);
         }
         return suppliedStream;
      };
   }

   @Override
   protected DistributedDoubleCacheStream doubleCacheStream() {
      return new TxDistributedDoubleCacheStream(this, localAddress, hash, ctx);
   }

   @Override
   protected DistributedLongCacheStream longCacheStream() {
      return new TxDistributedLongCacheStream(this, localAddress, hash, ctx);
   }

   @Override
   protected DistributedIntCacheStream intCacheStream() {
      return new TxDistributedIntCacheStream(this, localAddress, hash, ctx);
   }
}


File: core/src/main/java/org/infinispan/stream/impl/tx/TxDistributedDoubleCacheStream.java
package org.infinispan.stream.impl.tx;

import org.infinispan.container.entries.CacheEntry;
import org.infinispan.context.impl.LocalTxInvocationContext;
import org.infinispan.distribution.ch.ConsistentHash;
import org.infinispan.remoting.transport.Address;
import org.infinispan.stream.impl.AbstractCacheStream;
import org.infinispan.stream.impl.DistributedCacheStream;
import org.infinispan.stream.impl.DistributedDoubleCacheStream;
import org.infinispan.stream.impl.DistributedIntCacheStream;
import org.infinispan.stream.impl.DistributedLongCacheStream;

import java.util.Set;
import java.util.function.Supplier;
import java.util.stream.Collectors;
import java.util.stream.Stream;

/**
 * Double variant of tx cache stream
 * @see TxDistributedCacheStream
 */
public class TxDistributedDoubleCacheStream extends DistributedDoubleCacheStream {
   private final Address localAddress;
   private final LocalTxInvocationContext ctx;
   private final ConsistentHash hash;

   TxDistributedDoubleCacheStream(AbstractCacheStream stream, Address localAddress, ConsistentHash hash,
           LocalTxInvocationContext ctx) {
      super(stream);
      this.localAddress = localAddress;
      this.hash = hash;
      this.ctx = ctx;
   }

   @Override
   protected Supplier<Stream<CacheEntry>> supplierForSegments(ConsistentHash ch, Set<Integer> targetSegments,
           Set<Object> excludedKeys) {
      return () -> {
         Supplier<Stream<CacheEntry>> supplier = super.supplierForSegments(ch, targetSegments, excludedKeys);
         Set<CacheEntry> set = ctx.getLookedUpEntries().values().stream().filter(
                 e -> !localAddress.equals(ch.locatePrimaryOwner(e.getKey()))).collect(Collectors.toSet());
         Stream<CacheEntry> suppliedStream = supplier.get();
         if (!set.isEmpty()) {
            return Stream.concat(set.stream(), suppliedStream);
         }
         return suppliedStream;
      };
   }

   @Override
   protected <R> DistributedCacheStream<R> cacheStream() {
      return new TxDistributedCacheStream<>(this, localAddress, hash, ctx);
   }

   @Override
   protected DistributedIntCacheStream intCacheStream() {
      return new TxDistributedIntCacheStream(this, localAddress, hash, ctx);
   }

   @Override
   protected DistributedLongCacheStream longCacheStream() {
      return new TxDistributedLongCacheStream(this, localAddress, hash, ctx);
   }
}


File: core/src/main/java/org/infinispan/stream/impl/tx/TxDistributedIntCacheStream.java
package org.infinispan.stream.impl.tx;

import org.infinispan.container.entries.CacheEntry;
import org.infinispan.context.impl.LocalTxInvocationContext;
import org.infinispan.distribution.ch.ConsistentHash;
import org.infinispan.remoting.transport.Address;
import org.infinispan.stream.impl.AbstractCacheStream;
import org.infinispan.stream.impl.DistributedCacheStream;
import org.infinispan.stream.impl.DistributedDoubleCacheStream;
import org.infinispan.stream.impl.DistributedIntCacheStream;
import org.infinispan.stream.impl.DistributedLongCacheStream;

import java.util.Set;
import java.util.function.Supplier;
import java.util.stream.Collectors;
import java.util.stream.Stream;

/**
 * Int variant of tx cache stream
 * @see TxDistributedCacheStream
 */
public class TxDistributedIntCacheStream extends DistributedIntCacheStream {
   private final Address localAddress;
   private final LocalTxInvocationContext ctx;
   private final ConsistentHash hash;

   TxDistributedIntCacheStream(AbstractCacheStream stream, Address localAddress, ConsistentHash hash,
           LocalTxInvocationContext ctx) {
      super(stream);
      this.localAddress = localAddress;
      this.ctx = ctx;
      this.hash = hash;
   }

   @Override
   protected Supplier<Stream<CacheEntry>> supplierForSegments(ConsistentHash ch, Set<Integer> targetSegments,
           Set<Object> excludedKeys) {
      return () -> {
         Supplier<Stream<CacheEntry>> supplier = super.supplierForSegments(ch, targetSegments, excludedKeys);
         Set<CacheEntry> set = ctx.getLookedUpEntries().values().stream().filter(
                 e -> !localAddress.equals(ch.locatePrimaryOwner(e.getKey()))).collect(Collectors.toSet());
         Stream<CacheEntry> suppliedStream = supplier.get();
         if (!set.isEmpty()) {
            return Stream.concat(set.stream(), suppliedStream);
         }
         return suppliedStream;
      };
   }

   @Override
   protected <R> DistributedCacheStream<R> cacheStream() {
      return new TxDistributedCacheStream<>(this, localAddress, hash, ctx);
   }

   @Override
   protected DistributedLongCacheStream longCacheStream() {
      return new TxDistributedLongCacheStream(this, localAddress, hash, ctx);
   }

   @Override
   protected DistributedDoubleCacheStream doubleCacheStream() {
      return new TxDistributedDoubleCacheStream(this, localAddress, hash, ctx);
   }
}


File: core/src/main/java/org/infinispan/stream/impl/tx/TxDistributedLongCacheStream.java
package org.infinispan.stream.impl.tx;

import org.infinispan.container.entries.CacheEntry;
import org.infinispan.context.impl.LocalTxInvocationContext;
import org.infinispan.distribution.ch.ConsistentHash;
import org.infinispan.remoting.transport.Address;
import org.infinispan.stream.impl.AbstractCacheStream;
import org.infinispan.stream.impl.DistributedCacheStream;
import org.infinispan.stream.impl.DistributedDoubleCacheStream;
import org.infinispan.stream.impl.DistributedIntCacheStream;
import org.infinispan.stream.impl.DistributedLongCacheStream;

import java.util.Set;
import java.util.function.Supplier;
import java.util.stream.Collectors;
import java.util.stream.Stream;

/**
 * Long variant of tx cache stream
 * @see TxDistributedCacheStream
 */
public class TxDistributedLongCacheStream extends DistributedLongCacheStream {
   private final Address localAddress;
   private final LocalTxInvocationContext ctx;
   private final ConsistentHash hash;

   TxDistributedLongCacheStream(AbstractCacheStream stream, Address localAddress, ConsistentHash hash,
           LocalTxInvocationContext ctx) {
      super(stream);
      this.localAddress = localAddress;
      this.ctx = ctx;
      this.hash = hash;
   }

   @Override
   protected Supplier<Stream<CacheEntry>> supplierForSegments(ConsistentHash ch, Set<Integer> targetSegments,
           Set<Object> excludedKeys) {
      return () -> {
         Supplier<Stream<CacheEntry>> supplier = super.supplierForSegments(ch, targetSegments, excludedKeys);
         Set<CacheEntry> set = ctx.getLookedUpEntries().values().stream().filter(
                 e -> !localAddress.equals(ch.locatePrimaryOwner(e.getKey()))).collect(Collectors.toSet());
         Stream<CacheEntry> suppliedStream = supplier.get();
         if (!set.isEmpty()) {
            return Stream.concat(set.stream(), suppliedStream);
         }
         return suppliedStream;
      };
   }

   @Override
   protected <R> DistributedCacheStream<R> cacheStream() {
      return new TxDistributedCacheStream<R>(this, localAddress, hash, ctx);
   }

   @Override
   protected DistributedIntCacheStream intCacheStream() {
      return new TxDistributedIntCacheStream(this, localAddress, hash, ctx);
   }

   @Override
   protected DistributedDoubleCacheStream doubleCacheStream() {
      return new TxDistributedDoubleCacheStream(this, localAddress, hash, ctx);
   }
}


File: core/src/test/java/org/infinispan/stream/DistributedStreamIteratorTest.java
package org.infinispan.stream;

import org.infinispan.Cache;
import org.infinispan.configuration.cache.CacheMode;
import org.infinispan.container.DataContainer;
import org.infinispan.container.entries.CacheEntry;
import org.infinispan.container.entries.ImmortalCacheEntry;
import org.infinispan.context.Flag;
import org.infinispan.distribution.DistributionManager;
import org.infinispan.distribution.MagicKey;
import org.infinispan.distribution.ch.ConsistentHash;
import org.infinispan.filter.CacheFilters;
import org.infinispan.remoting.rpc.RpcManager;
import org.infinispan.remoting.rpc.RpcOptions;
import org.infinispan.remoting.transport.Address;
import org.infinispan.stream.impl.ClusterStreamManager;
import org.infinispan.stream.impl.StreamResponseCommand;
import org.infinispan.test.TestingUtil;
import org.infinispan.test.fwk.CheckPoint;
import org.mockito.AdditionalAnswers;
import org.mockito.stubbing.Answer;
import org.testng.annotations.Test;

import java.util.HashMap;
import java.util.HashSet;
import java.util.Iterator;
import java.util.Map;
import java.util.Set;
import java.util.UUID;
import java.util.concurrent.ArrayBlockingQueue;
import java.util.concurrent.BlockingQueue;
import java.util.concurrent.ExecutionException;
import java.util.concurrent.Future;
import java.util.concurrent.LinkedBlockingQueue;
import java.util.concurrent.TimeUnit;
import java.util.concurrent.TimeoutException;
import java.util.concurrent.atomic.AtomicInteger;

import static org.mockito.Matchers.any;
import static org.mockito.Matchers.anyCollectionOf;
import static org.mockito.Matchers.anySetOf;
import static org.mockito.Mockito.anyBoolean;
import static org.mockito.Mockito.*;
import static org.testng.AssertJUnit.*;

/**
 * Test to verify distributed stream iterator
 *
 * @author wburns
 * @since 8.0
 */
@Test(groups = {"functional", "smoke"}, testName = "iteration.DistributedStreamIteratorTest")
public class DistributedStreamIteratorTest extends BaseClusteredStreamIteratorTest {
   public DistributedStreamIteratorTest() {
      this(false);
   }

   public DistributedStreamIteratorTest(boolean tx) {
      super(tx, CacheMode.DIST_SYNC);
      // This is needed since we kill nodes
      cleanup = CleanupPhase.AFTER_METHOD;
   }

   protected Object getKeyTiedToCache(Cache<?, ?> cache) {
      return new MagicKey(cache);
   }

   @Test
   public void verifyNodeLeavesBeforeGettingData() throws TimeoutException, InterruptedException, ExecutionException {
      Map<Object, String> values = putValueInEachCache(3);

      Cache<Object, String> cache0 = cache(0, CACHE_NAME);
      Cache<Object, String> cache1 = cache(1, CACHE_NAME);

      CheckPoint checkPoint = new CheckPoint();
      checkPoint.triggerForever("post_send_response_released");
      waitUntilSendingResponse(cache1, checkPoint);

      final BlockingQueue<Map.Entry<Object, String>> returnQueue = new ArrayBlockingQueue<>(10);
      Future<Void> future = fork(() -> {
         Iterator<Map.Entry<Object, String>> iter = cache0.entrySet().stream().iterator();
         while (iter.hasNext()) {
            Map.Entry<Object, String> entry = iter.next();
            returnQueue.add(entry);
         }
         return null;
      });

      // Make sure the thread is waiting for the response
      checkPoint.awaitStrict("pre_send_response_invoked", 10, TimeUnit.SECONDS);

      // Now kill the cache - we should recover
      killMember(1, CACHE_NAME);

      checkPoint.trigger("pre_send_response_released");

      future.get(10, TimeUnit.SECONDS);

      for (Map.Entry<Object, String> entry : values.entrySet()) {
         assertTrue("Entry wasn't found:" + entry, returnQueue.contains(entry));
      }
   }

   /**
    * This test is to verify proper behavior when a node dies after sending a batch to the requestor
    */
   @Test
   public void verifyNodeLeavesAfterSendingBackSomeData() throws TimeoutException, InterruptedException, ExecutionException {
      Cache<Object, String> cache0 = cache(0, CACHE_NAME);
      Cache<Object, String> cache1 = cache(1, CACHE_NAME);

      Map<Object, String> values = new HashMap<>();
      int chunkSize = cache0.getCacheConfiguration().clustering().stateTransfer().chunkSize();
      // Now insert 10 more values than the chunk size into the node we will kill
      for (int i = 0; i < chunkSize + 10; ++i) {
         MagicKey key = new MagicKey(cache1);
         cache1.put(key, key.toString());
         values.put(key, key.toString());
      }

      CheckPoint checkPoint = new CheckPoint();
      // Let the first request come through fine
      checkPoint.trigger("pre_send_response_released");
      waitUntilSendingResponse(cache1, checkPoint);

      final BlockingQueue<Map.Entry<Object, String>> returnQueue = new LinkedBlockingQueue<>();
      Future<Void> future = fork(() -> {
         Iterator<Map.Entry<Object, String>> iter = cache0.entrySet().stream().iterator();
         while (iter.hasNext()) {
            Map.Entry<Object, String> entry = iter.next();
            returnQueue.add(entry);
         }
         return null;
      });

      // Now wait for them to send back first results
      checkPoint.awaitStrict("post_send_response_invoked", 10, TimeUnit.SECONDS);

      // We should get a value now, note all values are currently residing on cache1 as primary
      Map.Entry<Object, String> value = returnQueue.poll(10, TimeUnit.SECONDS);

      // Now kill the cache - we should recover
      killMember(1, CACHE_NAME);

      future.get(10, TimeUnit.SECONDS);

      for (Map.Entry<Object, String> entry : values.entrySet()) {
         assertTrue("Entry wasn't found:" + entry, returnQueue.contains(entry) || entry.equals(value));
      }
   }

   @Test
   public void waitUntilProcessingResults() throws TimeoutException, InterruptedException, ExecutionException {
      Cache<Object, String> cache0 = cache(0, CACHE_NAME);
      Cache<Object, String> cache1 = cache(1, CACHE_NAME);

      Map<Object, String> values = new HashMap<>();
      for (int i = 0; i < 501; ++i) {
         MagicKey key = new MagicKey(cache1);
         cache1.put(key, key.toString());
         values.put(key, key.toString());
      }

      CheckPoint checkPoint = new CheckPoint();
      checkPoint.triggerForever("post_receive_response_released");
      waitUntilStartOfProcessingResult(cache0, checkPoint);

      final BlockingQueue<Map.Entry<Object, String>> returnQueue = new LinkedBlockingQueue<>();
      Future<Void> future = fork(() -> {
            Iterator<Map.Entry<Object, String>> iter = cache0.entrySet().stream().iterator();
            while (iter.hasNext()) {
               Map.Entry<Object, String> entry = iter.next();
               returnQueue.add(entry);
            }
            return null;
      });

      // Now wait for them to send back first results but don't let them process
      checkPoint.awaitStrict("pre_receive_response_invoked", 10, TimeUnit.SECONDS);

      // Now let them process the results
      checkPoint.triggerForever("pre_receive_response_released");

      // Now kill the cache - we should recover and get appropriate values
      killMember(1, CACHE_NAME);

      future.get(10, TimeUnit.SECONDS);


      ConsistentHash hash = cache0.getAdvancedCache().getComponentRegistry().getComponent(DistributionManager.class).getReadConsistentHash();
      Map<Integer, Set<Map.Entry<Object, String>>> expected = generateEntriesPerSegment(hash, values.entrySet());
      Map<Integer, Set<Map.Entry<Object, String>>> answer = generateEntriesPerSegment(hash, returnQueue);

      for (Map.Entry<Integer, Set<Map.Entry<Object, String>>> entry : expected.entrySet()) {
         assertEquals("Segment " + entry.getKey() + " had a mismatch", answer.get(entry.getKey()), entry.getValue());
      }
   }

   @Test
   public void testNodeLeavesWhileIteratingOverContainerCausingRehashToLoseValues() throws TimeoutException,
                                                                                           InterruptedException,
                                                                                           ExecutionException {
      Cache<Object, String> cache0 = cache(0, CACHE_NAME);
      Cache<Object, String> cache1 = cache(1, CACHE_NAME);
      Cache<Object, String> cache2 = cache(2, CACHE_NAME);

      // Add an extra so that when we remove 1 it means not all the values will be on 1 node
      addClusterEnabledCacheManager(builderUsed);

      // put a lot of entries in cache0, so that when a node goes down it will lose some
      Map<Object, String> values = new HashMap<>();
      for (int i = 0; i < 501; ++i) {
         MagicKey key = new MagicKey(cache0);
         cache1.put(key, key.toString());
         values.put(key, key.toString());
      }

      CheckPoint checkPoint = new CheckPoint();
      checkPoint.triggerForever("post_iterator_released");
      waitUntilDataContainerWillBeIteratedOn(cache0, checkPoint);

      final BlockingQueue<Map.Entry<Object, String>> returnQueue = new LinkedBlockingQueue<>();
      Future<Void> future = fork(() -> {
         Iterator<Map.Entry<Object, String>> iter = cache2.entrySet().stream().iterator();
         while (iter.hasNext()) {
            Map.Entry<Object, String> entry = iter.next();
            returnQueue.add(entry);
         }
         return null;
      });

      // Now wait for them to send back first results but don't let them process
      checkPoint.awaitStrict("pre_iterator_invoked", 10, TimeUnit.SECONDS);

      // Now kill the cache - we should recover and get appropriate values
      killMember(1, CACHE_NAME);

      // Now let them process the results
      checkPoint.triggerForever("pre_iterator_released");

      future.get(10, TimeUnit.SECONDS);


      ConsistentHash hash = cache0.getAdvancedCache().getComponentRegistry().getComponent(DistributionManager.class).getReadConsistentHash();
      Map<Integer, Set<Map.Entry<Object, String>>> expected = generateEntriesPerSegment(hash, values.entrySet());
      Map<Integer, Set<Map.Entry<Object, String>>> answer = generateEntriesPerSegment(hash, returnQueue);

      for (Map.Entry<Integer, Set<Map.Entry<Object, String>>> entry : expected.entrySet()) {
         assertEquals("Segment " + entry.getKey() + " had a mismatch", answer.get(entry.getKey()), entry.getValue());
      }
   }

   @Test
   public void testLocallyForcedStream() {
      Cache<Object, String> cache0 = cache(0, CACHE_NAME);
      Cache<Object, String> cache1 = cache(1, CACHE_NAME);
      Cache<Object, String> cache2 = cache(2, CACHE_NAME);

      Map<Object, String> values = new HashMap<>();
      for (int i = 0; i < 501; ++i) {
         switch (i % 3) {
            case 0:
               MagicKey key = new MagicKey(cache0);
               cache0.put(key, key.toString());
               values.put(key, key.toString());
               break;
            case 1:
               // Force it so only cache0 has it's primary owned keys
               key = new MagicKey(cache1, cache2);
               cache1.put(key, key.toString());
               break;
            case 2:
               // Force it so only cache0 has it's primary owned keys
               key = new MagicKey(cache2, cache1);
               cache2.put(key, key.toString());
               break;
            default:
               fail("Unexpected switch case!");
         }
      }

      int count = 0;
      Iterator<Map.Entry<Object, String>> iter = cache0.getAdvancedCache().withFlags(Flag.CACHE_MODE_LOCAL).entrySet().
              stream().iterator();
      while (iter.hasNext()) {
         Map.Entry<Object, String> entry = iter.next();
         String cacheValue = cache0.get(entry.getKey());
         assertNotNull(cacheValue);
         assertEquals(cacheValue, entry.getValue());
         count++;
      }

      assertEquals(values.size(), count);
   }

   private Map<Integer, Set<Map.Entry<Object, String>>> generateEntriesPerSegment(ConsistentHash hash, Iterable<Map.Entry<Object, String>> entries) {
      Map<Integer, Set<Map.Entry<Object, String>>> returnMap = new HashMap<>();

      for (Map.Entry<Object, String> value : entries) {
         int segment = hash.getSegment(value.getKey());
         Set<Map.Entry<Object, String>> set = returnMap.get(segment);
         if (set == null) {
            set = new HashSet<>();
            returnMap.put(segment, set);
         }
         set.add(new ImmortalCacheEntry(value.getKey(), value.getValue()));
      }
      return returnMap;
   }

   protected RpcManager waitUntilSendingResponse(final Cache<?, ?> cache, final CheckPoint checkPoint) {
      RpcManager rpc = TestingUtil.extractComponent(cache, RpcManager.class);
      final Answer<Object> forwardedAnswer = AdditionalAnswers.delegatesTo(rpc);
      RpcManager mockManager = mock(RpcManager.class, withSettings().defaultAnswer(forwardedAnswer));
      doAnswer(invocation -> {
         // Wait for main thread to sync up
         checkPoint.trigger("pre_send_response_invoked");
         // Now wait until main thread lets us through
         checkPoint.awaitStrict("pre_send_response_released", 10, TimeUnit.SECONDS);

         try {
            return forwardedAnswer.answer(invocation);
         } finally {
            // Wait for main thread to sync up
            checkPoint.trigger("post_send_response_invoked");
            // Now wait until main thread lets us through
            checkPoint.awaitStrict("post_send_response_released", 10, TimeUnit.SECONDS);
         }
      }).when(mockManager).invokeRemotely(anyCollectionOf(Address.class), any(StreamResponseCommand.class),
                                          any(RpcOptions.class));
      TestingUtil.replaceComponent(cache, RpcManager.class, mockManager, true);
      return rpc;
   }

   protected ClusterStreamManager waitUntilStartOfProcessingResult(final Cache<?, ?> cache, final CheckPoint checkPoint) {
      ClusterStreamManager rpc = TestingUtil.extractComponent(cache, ClusterStreamManager.class);
      final Answer<Object> forwardedAnswer = AdditionalAnswers.delegatesTo(rpc);
      ClusterStreamManager mockRetriever = mock(ClusterStreamManager.class, withSettings().defaultAnswer(forwardedAnswer));
      doAnswer(invocation -> {
         // Wait for main thread to sync up
         checkPoint.trigger("pre_receive_response_invoked");
         // Now wait until main thread lets us through
         checkPoint.awaitStrict("pre_receive_response_released", 10, TimeUnit.SECONDS);

         try {
            return forwardedAnswer.answer(invocation);
         } finally {
            // Wait for main thread to sync up
            checkPoint.trigger("post_receive_response_invoked");
            // Now wait until main thread lets us through
            checkPoint.awaitStrict("post_receive_response_released", 10, TimeUnit.SECONDS);
         }
      }).when(mockRetriever).receiveResponse(any(UUID.class), any(Address.class), anyBoolean(), anySetOf(Integer.class),
              any());
      TestingUtil.replaceComponent(cache, ClusterStreamManager.class, mockRetriever, true);
      return rpc;
   }

   protected DataContainer waitUntilDataContainerWillBeIteratedOn(final Cache<?, ?> cache, final CheckPoint checkPoint) {
      DataContainer rpc = TestingUtil.extractComponent(cache, DataContainer.class);
      final Answer<Object> forwardedAnswer = AdditionalAnswers.delegatesTo(rpc);
      DataContainer mocaContainer = mock(DataContainer.class, withSettings().defaultAnswer(forwardedAnswer));
      final AtomicInteger invocationCount = new AtomicInteger();
      doAnswer(invocation -> {
         boolean waiting = false;
         if (invocationCount.getAndIncrement() == 0) {
            waiting = true;
            // Wait for main thread to sync up
            checkPoint.trigger("pre_iterator_invoked");
            // Now wait until main thread lets us through
            checkPoint.awaitStrict("pre_iterator_released", 10, TimeUnit.SECONDS);
         }

         try {
            return forwardedAnswer.answer(invocation);
         } finally {
            invocationCount.getAndDecrement();
            if (waiting) {
               // Wait for main thread to sync up
               checkPoint.trigger("post_iterator_invoked");
               // Now wait until main thread lets us through
               checkPoint.awaitStrict("post_iterator_released", 10, TimeUnit.SECONDS);
            }
         }
      }).when(mocaContainer).iterator();
      TestingUtil.replaceComponent(cache, DataContainer.class, mocaContainer, true);
      return rpc;
   }
}

