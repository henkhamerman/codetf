Refactoring Types: ['Move Attribute']
pan/persistence/async/AdvancedAsyncCacheWriter.java
package org.infinispan.persistence.async;

import org.infinispan.persistence.spi.AdvancedCacheWriter;
import org.infinispan.persistence.spi.CacheWriter;

import java.util.concurrent.Executor;

/**
 * @author Mircea Markus
 * @since 6.0
 */
public class AdvancedAsyncCacheWriter extends AsyncCacheWriter implements AdvancedCacheWriter {

   public AdvancedAsyncCacheWriter(CacheWriter delegate) {
      super(delegate);
   }

   @Override
   public void purge(Executor threadPool, PurgeListener task) {
      advancedWriter().purge(threadPool, task);
   }

   @Override
   public void clear() {
      stateLock.writeLock(1);
      try {
         state.set(newState(true, state.get().next));
      } finally {
         stateLock.reset(1);
         stateLock.writeUnlock();
      }
   }

   @Override
   protected void clearStore() {
      advancedWriter().clear();
   }

   private AdvancedCacheWriter advancedWriter() {
      return (AdvancedCacheWriter) actual;
   }
}


File: core/src/main/java/org/infinispan/persistence/async/AsyncCacheWriter.java
package org.infinispan.persistence.async;

import net.jcip.annotations.GuardedBy;

import org.infinispan.Cache;
import org.infinispan.configuration.cache.AsyncStoreConfiguration;
import org.infinispan.configuration.cache.Configuration;
import org.infinispan.persistence.spi.PersistenceException;
import org.infinispan.persistence.modifications.Modification;
import org.infinispan.persistence.modifications.Remove;
import org.infinispan.persistence.modifications.Store;
import org.infinispan.commons.util.CollectionFactory;
import org.infinispan.persistence.spi.CacheWriter;
import org.infinispan.persistence.spi.InitializationContext;
import org.infinispan.marshall.core.MarshalledEntry;
import org.infinispan.persistence.support.DelegatingCacheWriter;
import org.infinispan.util.logging.Log;
import org.infinispan.util.logging.LogFactory;

import java.util.ArrayList;
import java.util.List;
import java.util.Map;
import java.util.concurrent.ConcurrentMap;
import java.util.concurrent.CountDownLatch;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.LinkedBlockingQueue;
import java.util.concurrent.ThreadFactory;
import java.util.concurrent.ThreadPoolExecutor;
import java.util.concurrent.TimeUnit;
import java.util.concurrent.atomic.AtomicInteger;
import java.util.concurrent.atomic.AtomicReference;

/**
 * The AsyncCacheWriter is a delegating CacheStore that buffers changes and writes them asynchronously to
 * the underlying CacheStore.
 * <p/>
 * Read operations are done synchronously, taking into account the current state of buffered changes.
 * <p/>
 * There is no provision for exception handling for problems encountered with the underlying store
 * during a write operation, and the exception is just logged.
 * <p/>
 * When configuring the loader, use the following element:
 * <p/>
 * <code> &lt;async enabled="true" /&gt; </code>
 * <p/>
 * to define whether cache loader operations are to be asynchronous. If not specified, a cache loader operation is
 * assumed synchronous and this decorator is not applied.
 * <p/>
 * Write operations affecting same key are now coalesced so that only the final state is actually stored.
 * <p/>
 *
 * @author Manik Surtani
 * @author Galder Zamarreño
 * @author Sanne Grinovero
 * @author Karsten Blees
 * @author Mircea Markus
 * @since 4.0
 */
public class AsyncCacheWriter extends DelegatingCacheWriter {
   private static final Log log = LogFactory.getLog(AsyncCacheWriter.class);
   private static final boolean trace = log.isTraceEnabled();
   private static final AtomicInteger threadId = new AtomicInteger(0);

   private ExecutorService executor;
   private Thread coordinator;
   private int concurrencyLevel;
   private String cacheName;

   protected BufferLock stateLock;
   @GuardedBy("stateLock")
   protected final AtomicReference<State> state = new AtomicReference<State>();

   protected AsyncStoreConfiguration asyncConfiguration;

   public AsyncCacheWriter(CacheWriter delegate) {
      super(delegate);
   }

   @Override
   public void init(InitializationContext ctx) {
      super.init(ctx);
      this.asyncConfiguration = ctx.getConfiguration().async();

      Cache cache = ctx.getCache();
      Configuration cacheCfg = cache != null ? cache.getCacheConfiguration() : null;
      concurrencyLevel = cacheCfg != null ? cacheCfg.locking().concurrencyLevel() : 16;
      cacheName = cache != null ? cache.getName() : null;
   }

   @Override
   public void start() {
      log.debugf("Async cache loader starting %s", this);
      state.set(newState(false, null));
      stateLock = new BufferLock(asyncConfiguration.modificationQueueSize());

      // Create a thread pool with unbounded work queue, so that all work is accepted and eventually
      // executed. A bounded queue could throw RejectedExecutionException and thus lose data.
      int poolSize = asyncConfiguration.threadPoolSize();
      executor = new ThreadPoolExecutor(poolSize, poolSize, 120L, TimeUnit.SECONDS, new LinkedBlockingQueue<Runnable>(),
                                        new ThreadFactory() {
                                           @Override
                                           public Thread newThread(Runnable r) {
                                              Thread t = new Thread(r, "AsyncStoreProcessor-" + cacheName + "-" + threadId.getAndIncrement());
                                              t.setDaemon(true);
                                              return t;
                                           }
                                        });
      ((ThreadPoolExecutor) executor).allowCoreThreadTimeOut(true);
      coordinator = new Thread(new AsyncStoreCoordinator(), "AsyncStoreCoordinator-" + cacheName);
      coordinator.setDaemon(true);
      coordinator.start();
   }

   @Override
   public void stop() {
      if (trace) log.tracef("Stop async store %s", this);
      stateLock.writeLock(1);
      state.get().stopped = true;
      stateLock.writeUnlock();
      try {
         // It is safe to wait without timeout because the thread pool uses an unbounded work queue (i.e.
         // all work handed to the pool will be accepted and eventually executed) and AsyncStoreProcessors
         // decrement the workerThreads latch in a finally block (i.e. even if the back-end store throws
         // java.lang.Error). The coordinator thread can only block forever if the back-end's write() /
         // remove() methods block, but this is no different from PassivationManager.stop() being blocked
         // in a synchronous call to write() / remove().
         coordinator.join();
         // The coordinator thread waits for AsyncStoreProcessor threads to count down their latch (nearly
         // at the end). Thus the threads should have terminated or terminate instantly.
         executor.shutdown();
         if (!executor.awaitTermination(1, TimeUnit.SECONDS))
            log.errorAsyncStoreNotStopped();
      } catch (InterruptedException e) {
         log.interruptedWaitingAsyncStorePush(e);
         Thread.currentThread().interrupt();
      }
   }

   @Override
   public void write(MarshalledEntry entry) {
      put(new Store(entry.getKey(), entry), 1);
   }

   @Override
   public boolean delete(Object key) {
      put(new Remove(key), 1);
      return true;
   }

   protected void applyModificationsSync(List<Modification> mods) throws PersistenceException {
      for (Modification m : mods) {
         switch (m.getType()) {
            case STORE:
               actual.write(((Store) m).getStoredValue());
               break;
            case REMOVE:
               actual.delete(((Remove) m).getKey());
               break;
            default:
               throw new IllegalArgumentException("Unknown modification type " + m.getType());
         }
      }
   }


   State newState(boolean clear, State next) {
      ConcurrentMap<Object, Modification> map = CollectionFactory.makeConcurrentMap(64, concurrencyLevel);
      return new State(clear, map, next);
   }

   private void put(Modification mod, int count) {
      stateLock.writeLock(count);
      try {
         if (log.isTraceEnabled())
            log.tracef("Queue modification: %s", mod);

         state.get().put(mod);
      } finally {
         stateLock.writeUnlock();
      }
   }

   public AtomicReference<State> getState() {
      return state;
   }

   protected void clearStore() {
      // No-op, not supported for async
   }

   private class AsyncStoreCoordinator implements Runnable {

      @Override
      public void run() {
         LogFactory.pushNDC(cacheName, trace);
         try {
            for (;;) {
               final State s, head, tail;
               stateLock.readLock();
               try {
                  s = state.get();
                  tail = s.next;
                  assert tail == null || tail.next == null : "State chain longer than 3 entries!";
                  head = newState(false, s);
                  state.set(head);
               } finally {
                  stateLock.reset(0);
                  stateLock.readUnlock();
               }

               try {
                  if (s.clear) {
                     // clear() must be called synchronously, wait until background threads are done
                     if (tail != null)
                        tail.workerThreads.await();

                     clearStore();
                  }

                  List<Modification> mods;
                  if (tail != null) {
                     // if there's work in progress, push-back keys that are still in use to the head state
                     mods = new ArrayList<Modification>();
                     for (Map.Entry<Object, Modification> e : s.modifications.entrySet()) {
                        if (!tail.modifications.containsKey(e.getKey()))
                           mods.add(e.getValue());
                        else {
                           if (!head.clear && head.modifications.putIfAbsent(e.getKey(), e.getValue()) == null)
                              stateLock.add(1);
                           s.modifications.remove(e.getKey());
                        }
                     }
                  } else {
                     mods = new ArrayList<Modification>(s.modifications.values());
                  }

                  // distribute modifications evenly across worker threads
                  int threads = Math.min(mods.size(), asyncConfiguration.threadPoolSize());
                  s.workerThreads = new CountDownLatch(threads);
                  if (threads > 0) {
                     // schedule background threads
                     int start = 0;
                     int quotient = mods.size() / threads;
                     int remainder = mods.size() % threads;
                     for (int i = 0; i < threads; i++) {
                        int end = start + quotient + (i < remainder ? 1 : 0);
                        executor.execute(new AsyncStoreProcessor(mods.subList(start, end), s));
                        start = end;
                     }
                     assert start == mods.size() : "Thread distribution is broken!";
                  }

                  // wait until background threads of previous round are done
                  if (tail != null) {
                     tail.workerThreads.await();
                     s.next = null;
                  }

                  // if this is the last state to process, wait for background threads, then quit
                  if (s.stopped && head.modifications.isEmpty()) {
                     s.workerThreads.await();
                     return;
                  }
               } catch (Exception e) {
                  log.unexpectedErrorInAsyncStoreCoordinator(e);
               }
            }
         } finally {
            LogFactory.popNDC(trace);
         }
      }
   }

   private class AsyncStoreProcessor implements Runnable {
      private final List<Modification> modifications;
      private final State myState;

      AsyncStoreProcessor(List<Modification> modifications, State myState) {
         this.modifications = modifications;
         this.myState = myState;
      }

      @Override
      public void run() {
         try {
            // try 3 times to store the modifications
            retryWork(3);

         } finally {
            // decrement active worker threads and disconnect myState if this was the last one
            myState.workerThreads.countDown();
            if (myState.workerThreads.getCount() == 0 && myState.next == null)
               for (State s = state.get(); s != null; s = s.next)
                  if (s.next == myState)
                     s.next = null;
         }
      }

      private void retryWork(int maxRetries) {
         for (int attempt = 0; attempt < maxRetries; attempt++) {
            if (attempt > 0 && log.isDebugEnabled())
               log.debugf("Retrying due to previous failure. %s attempts left.", maxRetries - attempt);

            try {
               AsyncCacheWriter.this.applyModificationsSync(modifications);
               return;
            } catch (Exception e) {
               if (log.isDebugEnabled())
                  log.debug("Failed to process async modifications", e);
            }
         }
         log.unableToProcessAsyncModifications(maxRetries);
      }
   }
}


File: core/src/main/java/org/infinispan/persistence/async/State.java
package org.infinispan.persistence.async;

import org.infinispan.commons.CacheException;
import org.infinispan.persistence.modifications.Clear;
import org.infinispan.persistence.modifications.Modification;
import org.infinispan.persistence.modifications.ModificationsList;
import org.infinispan.persistence.modifications.Remove;
import org.infinispan.persistence.modifications.Store;

import java.util.HashSet;
import java.util.Set;
import java.util.concurrent.ConcurrentMap;
import java.util.concurrent.CountDownLatch;

/**
* @author Karsten Blees
* @since 6.0
*/
public class State {

   final static Clear CLEAR = new Clear();

   /**
    * True if the state has been cleared before making modifications.
    */
   final boolean clear;

   /**
    * Modifications to apply to the back-end CacheStore.
    */
   final ConcurrentMap<Object, Modification> modifications;

   /**
    * Next state in the chain, initialized in constructor, may be set to <code>null</code>
    * asynchronously at any time.
    */
   volatile State next;

   /**
    * True if the CacheStore has been stopped (i.e. this is the last state to process).
    */
   volatile boolean stopped = false;

   /**
    * Number of worker threads that currently work with this instance.
    */
   CountDownLatch workerThreads;

   State(boolean clear, ConcurrentMap<Object, Modification> modMap, State next) {
      this.clear = clear;
      this.modifications = modMap;
      this.next = next;
      if (next != null)
         stopped = next.stopped;
   }

   /**
    * Gets the Modification for the specified key from this State object or chained (
    * <code>next</code>) State objects.
    *
    * @param key
    *           the key to look up
    * @return the Modification for the specified key, or <code>CLEAR</code> if the state was
    *         cleared, or <code>null</code> if the key is not in the state map
    */
   Modification get(Object key) {
      for (State state = this; state != null; state = state.next) {
         Modification mod = state.modifications.get(key);
         if (mod != null)
            return mod;
         else if (state.clear)
            return CLEAR;
      }
      return null;
   }

   /**
    * Adds the Modification(s) to the state map.
    *
    * @param mod
    *           the Modification to add, supports modification types STORE, REMOVE and LIST
    */
   void put(Modification mod) {
      if (stopped)
         throw new CacheException("AsyncCacheWriter stopped; no longer accepting more entries.");
      switch (mod.getType()) {
         case STORE:
            modifications.put(((Store) mod).getKey(), mod);
            break;
         case REMOVE:
            modifications.put(((Remove) mod).getKey(), mod);
            break;
         case LIST:
            for (Modification m : ((ModificationsList) mod).getList())
               put(m);
            break;
         default:
            throw new IllegalArgumentException("Unknown modification type " + mod.getType());
      }
   }


   public Set getKeysInTransit() {
      Set result = new HashSet();
      _loadKeys(this, result);
      return result;
   }

   private void _loadKeys(State s, Set result) {
      // if not cleared, get keys from next State or the back-end store
      if (!s.clear) {
         State next = s.next;
         if (next != null)
            _loadKeys(next, result);
      }

      // merge keys of the current State
      for (Modification mod : s.modifications.values()) {
         switch (mod.getType()) {
            case STORE:
               Object key = ((Store) mod).getKey();
                  result.add(key);
               break;
            case REMOVE:
               result.remove(((Remove) mod).getKey());
               break;
         }
      }
   }

}
