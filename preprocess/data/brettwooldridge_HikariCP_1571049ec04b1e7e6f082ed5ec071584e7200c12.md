Refactoring Types: ['Move Class']
ikari/pool/HikariPool.java
/*
 * Copyright (C) 2013,2014 Brett Wooldridge
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

package com.zaxxer.hikari.pool;

import static com.zaxxer.hikari.util.IConcurrentBagEntry.STATE_IN_USE;
import static com.zaxxer.hikari.util.IConcurrentBagEntry.STATE_NOT_IN_USE;
import static com.zaxxer.hikari.util.IConcurrentBagEntry.STATE_REMOVED;
import static com.zaxxer.hikari.util.UtilityElf.createThreadPoolExecutor;
import static com.zaxxer.hikari.util.UtilityElf.getTransactionIsolation;
import static com.zaxxer.hikari.util.UtilityElf.quietlySleep;

import java.sql.Connection;
import java.sql.ResultSet;
import java.sql.SQLException;
import java.sql.SQLTimeoutException;
import java.sql.Statement;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Future;
import java.util.concurrent.FutureTask;
import java.util.concurrent.ScheduledThreadPoolExecutor;
import java.util.concurrent.ThreadFactory;
import java.util.concurrent.ThreadPoolExecutor;
import java.util.concurrent.TimeUnit;
import java.util.concurrent.atomic.AtomicInteger;
import java.util.concurrent.atomic.AtomicReference;

import javax.sql.DataSource;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import com.codahale.metrics.MetricRegistry;
import com.codahale.metrics.health.HealthCheckRegistry;
import com.zaxxer.hikari.HikariConfig;
import com.zaxxer.hikari.metrics.CodaHaleMetricsTracker;
import com.zaxxer.hikari.metrics.CodahaleHealthChecker;
import com.zaxxer.hikari.metrics.MetricsTracker;
import com.zaxxer.hikari.metrics.PoolStats;
import com.zaxxer.hikari.metrics.MetricsTracker.MetricsContext;
import com.zaxxer.hikari.proxy.ConnectionProxy;
import com.zaxxer.hikari.proxy.IHikariConnectionProxy;
import com.zaxxer.hikari.proxy.ProxyFactory;
import com.zaxxer.hikari.util.ClockSource;
import com.zaxxer.hikari.util.ConcurrentBag;
import com.zaxxer.hikari.util.DefaultThreadFactory;
import com.zaxxer.hikari.util.IBagStateListener;
import com.zaxxer.hikari.util.PropertyElf;

/**
 * This is the primary connection pool class that provides the basic
 * pooling behavior for HikariCP.
 *
 * @author Brett Wooldridge
 */
public class HikariPool implements HikariPoolMBean, IBagStateListener
{
   private final Logger LOGGER = LoggerFactory.getLogger(getClass());

   private static final ClockSource clockSource = ClockSource.INSTANCE;

   private final long ALIVE_BYPASS_WINDOW_MS = Long.getLong("com.zaxxer.hikari.aliveBypassWindow", TimeUnit.SECONDS.toMillis(1));
   private final long HOUSEKEEPING_PERIOD_MS = Long.getLong("com.zaxxer.hikari.housekeeping.periodMs", TimeUnit.SECONDS.toMillis(30));

   private static final int POOL_NORMAL = 0;
   private static final int POOL_SUSPENDED = 1;
   private static final int POOL_SHUTDOWN = 2;

   public int transactionIsolation;
   public final String catalog;
   public final boolean isReadOnly;
   public final boolean isAutoCommit;
   public final PoolElf poolUtils;

   final HikariConfig config;
   final ConcurrentBag<PoolBagEntry> connectionBag;
   final ScheduledThreadPoolExecutor houseKeepingExecutorService;

   private final AtomicInteger totalConnections;
   private final ThreadPoolExecutor addConnectionExecutor;
   private final ThreadPoolExecutor closeConnectionExecutor;

   private final boolean isUseJdbc4Validation;
   private final boolean isIsolateInternalQueries;

   private volatile int poolState;
   private long connectionTimeout;
   
   private final LeakTask leakTask;
   private final DataSource dataSource;
   private final SuspendResumeLock suspendResumeLock;
   private final AtomicReference<Throwable> lastConnectionFailure;

   private volatile MetricsTracker metricsTracker;
   private boolean isRecordMetrics;

   /**
    * Construct a HikariPool with the specified configuration.
    *
    * @param config a HikariConfig instance
    */
   public HikariPool(HikariConfig config)
    {
      this.config = config;

      this.poolUtils = new PoolElf(config);
      this.dataSource = poolUtils.initializeDataSource();

      this.connectionBag = new ConcurrentBag<>(this);
      this.totalConnections = new AtomicInteger();
      this.connectionTimeout = config.getConnectionTimeout();
      this.lastConnectionFailure = new AtomicReference<>();

      this.catalog = config.getCatalog();
      this.isReadOnly = config.isReadOnly();
      this.isAutoCommit = config.isAutoCommit();
      this.isUseJdbc4Validation = config.getConnectionTestQuery() == null;
      this.isIsolateInternalQueries = config.isIsolateInternalQueries();
      this.transactionIsolation = getTransactionIsolation(config.getTransactionIsolation());

      this.suspendResumeLock = config.isAllowPoolSuspension() ? new SuspendResumeLock(true) : SuspendResumeLock.FAUX_LOCK;

      setMetricRegistry(config.getMetricRegistry());
      setHealthCheckRegistry(config.getHealthCheckRegistry());

      this.addConnectionExecutor = createThreadPoolExecutor(config.getMaximumPoolSize(), "Hikari connection filler (pool " + config.getPoolName() + ")", config.getThreadFactory(), new ThreadPoolExecutor.DiscardPolicy());
      this.closeConnectionExecutor = createThreadPoolExecutor(4, "Hikari connection closer (pool " + config.getPoolName() + ")", config.getThreadFactory(), new ThreadPoolExecutor.CallerRunsPolicy());

      if (config.getScheduledExecutorService() == null) {
         ThreadFactory threadFactory = config.getThreadFactory() != null ? config.getThreadFactory() : new DefaultThreadFactory("Hikari housekeeper (pool " + config.getPoolName() + ")", true);
         this.houseKeepingExecutorService = new ScheduledThreadPoolExecutor(1, threadFactory, new ThreadPoolExecutor.DiscardPolicy());
         this.houseKeepingExecutorService.scheduleAtFixedRate(new HouseKeeper(), HOUSEKEEPING_PERIOD_MS, HOUSEKEEPING_PERIOD_MS, TimeUnit.MILLISECONDS);
         this.houseKeepingExecutorService.setExecuteExistingDelayedTasksAfterShutdownPolicy(false);
         this.houseKeepingExecutorService.setRemoveOnCancelPolicy(true);
      }
      else {
         this.houseKeepingExecutorService = config.getScheduledExecutorService();
      }
      this.leakTask = (config.getLeakDetectionThreshold() == 0) ? LeakTask.NO_LEAK : new LeakTask(config.getLeakDetectionThreshold(), houseKeepingExecutorService);

      poolUtils.registerMBeans(this);

      PropertyElf.flushCaches();  // prevent classloader leak

      initializeConnections();
   }

   /**
    * Get a connection from the pool, or timeout after connectionTimeout milliseconds.
    *
    * @return a java.sql.Connection instance
    * @throws SQLException thrown if a timeout occurs trying to obtain a connection
    */
   public final Connection getConnection() throws SQLException
   {
      return getConnection(connectionTimeout);
   }

   /**
    * Get a connection from the pool, or timeout after the specified number of milliseconds.
    *
    * @param hardTimeout the maximum time to wait for a connection from the pool
    * @return a java.sql.Connection instance
    * @throws SQLException thrown if a timeout occurs trying to obtain a connection
    */
   public final Connection getConnection(final long hardTimeout) throws SQLException
   {
      suspendResumeLock.acquire();
      final long startTime = clockSource.currentTime();

      try {
         long timeout = hardTimeout;
         final MetricsContext metricsContext = (isRecordMetrics ? metricsTracker.recordConnectionRequest() : MetricsTracker.NO_CONTEXT);
         do {
            final PoolBagEntry bagEntry = connectionBag.borrow(timeout, TimeUnit.MILLISECONDS);
            if (bagEntry == null) {
               break; // We timed out... break and throw exception
            }

            final long now = clockSource.currentTime();
            if (bagEntry.evicted || (clockSource.elapsedMillis(bagEntry.lastAccess, now) > ALIVE_BYPASS_WINDOW_MS && !isConnectionAlive(bagEntry.connection))) {
               closeConnection(bagEntry, "(connection evicted or dead)"); // Throw away the dead connection and try again
               timeout = hardTimeout - clockSource.elapsedMillis(startTime, now);
            }
            else {
               metricsContext.setConnectionLastOpen(bagEntry, now);
               metricsContext.stop();
               return ProxyFactory.getProxyConnection(bagEntry, leakTask.start(bagEntry), now);
            }
         }
         while (timeout > 0L);
      }
      catch (InterruptedException e) {
         throw new SQLException("Interrupted during connection acquisition", e);
      }
      finally {
         suspendResumeLock.release();
      }

      logPoolState("Timeout failure ");
      throw new SQLTimeoutException(String.format("Timeout after %dms of waiting for a connection.", clockSource.elapsedMillis(startTime), lastConnectionFailure.getAndSet(null)));
   }

   /**
    * Release a connection back to the pool, or permanently close it if it is broken.
    *
    * @param bagEntry the PoolBagEntry to release back to the pool
    */
   public final void releaseConnection(final PoolBagEntry bagEntry)
   {
      metricsTracker.recordConnectionUsage(bagEntry);

      if (bagEntry.evicted) {
         closeConnection(bagEntry, "(connection broken or evicted)");
      }
      else {
         connectionBag.requite(bagEntry);
      }
   }

   /**
    * Shutdown the pool, closing all idle connections and aborting or closing
    * active connections.
    *
    * @throws InterruptedException thrown if the thread is interrupted during shutdown
    */
   public final synchronized void shutdown() throws InterruptedException
   {
      try {
         poolState = POOL_SHUTDOWN;

         LOGGER.info("Hikari pool {} is shutting down.", config.getPoolName());

         logPoolState("Before shutdown ");
         connectionBag.close();
         softEvictConnections();
         houseKeepingExecutorService.shutdown();
         addConnectionExecutor.shutdownNow();
         houseKeepingExecutorService.awaitTermination(5L, TimeUnit.SECONDS);
         addConnectionExecutor.awaitTermination(5L, TimeUnit.SECONDS);

         final ExecutorService assassinExecutor = createThreadPoolExecutor(config.getMaximumPoolSize(), "Hikari connection assassin",
                                                                           config.getThreadFactory(), new ThreadPoolExecutor.CallerRunsPolicy());
         try {
            final long start = clockSource.currentTime();
            do {
               softEvictConnections();
               abortActiveConnections(assassinExecutor);
            }
            while (getTotalConnections() > 0 && clockSource.elapsedMillis(start) < TimeUnit.SECONDS.toMillis(5));
         } finally {
            assassinExecutor.shutdown();
            assassinExecutor.awaitTermination(5L, TimeUnit.SECONDS);
         }

         closeConnectionExecutor.shutdown();
         closeConnectionExecutor.awaitTermination(5L, TimeUnit.SECONDS);
      }
      finally {
         logPoolState("After shutdown ");

         poolUtils.unregisterMBeans();
         metricsTracker.close();
      }
   }

   /**
    * Evict a connection from the pool.
    *
    * @param proxyConnection the connection to evict
    */
   public final void evictConnection(IHikariConnectionProxy proxyConnection)
   {
      closeConnection(proxyConnection.getPoolBagEntry(), "(connection evicted by user)");
   }

   /**
    * Get the wrapped DataSource.
    *
    * @return the wrapped DataSource
    */
   public final DataSource getDataSource()
   {
      return dataSource;
   }

   public void setMetricRegistry(Object metricRegistry)
   {
      this.isRecordMetrics = metricRegistry != null;
      if (isRecordMetrics) {
         this.metricsTracker = new CodaHaleMetricsTracker(config.getPoolName(), getPoolStats(), (MetricRegistry) metricRegistry);
      }
      else {
         this.metricsTracker = new MetricsTracker();
      }
   }

   public void setHealthCheckRegistry(Object healthCheckRegistry)
   {
      if (healthCheckRegistry != null) {
         CodahaleHealthChecker.registerHealthChecks(this, config, (HealthCheckRegistry) healthCheckRegistry);
      }
   }

   /**
    * Log the current pool state at debug level.
    *
    * @param prefix an optional prefix to prepend the log message 
    */
   public final void logPoolState(String... prefix)
   {
      if (LOGGER.isDebugEnabled()) {
         LOGGER.debug("{}pool {} stats (total={}, active={}, idle={}, waiting={})",
                      (prefix.length > 0 ? prefix[0] : ""), config.getPoolName(),
                      getTotalConnections(), getActiveConnections(), getIdleConnections(), getThreadsAwaitingConnection());
      }
   }

   /** {@inheritDoc} */
   @Override
   public String toString()
   {
      return config.getPoolName();
   }

   // ***********************************************************************
   //                        IBagStateListener callback
   // ***********************************************************************

   /** {@inheritDoc} */
   @Override
   public Future<Boolean> addBagItem()
   {
      FutureTask<Boolean> future = new FutureTask<>(new Runnable() {
         @Override
         public void run()
         {
            long sleepBackoff = 200L;
            final int minimumIdle = config.getMinimumIdle();
            final int maxPoolSize = config.getMaximumPoolSize();
            while (poolState == POOL_NORMAL && totalConnections.get() < maxPoolSize && getIdleConnections() <= minimumIdle && !addConnection()) {
               // If we got into the loop, addConnection() failed, so we sleep and retry
               quietlySleep(sleepBackoff);
               sleepBackoff = Math.min(connectionTimeout / 2, (long) ((double) sleepBackoff * 1.5));
            }
         }
      }, true);

      addConnectionExecutor.execute(future);
      return future;
   }

   // ***********************************************************************
   //                        HikariPoolMBean methods
   // ***********************************************************************

   /** {@inheritDoc} */
   @Override
   public final int getActiveConnections()
   {
      return connectionBag.getCount(STATE_IN_USE);
   }

   /** {@inheritDoc} */
   @Override
   public final int getIdleConnections()
   {
      return connectionBag.getCount(STATE_NOT_IN_USE);
   }

   /** {@inheritDoc} */
   @Override
   public final int getTotalConnections()
   {
      return connectionBag.size() - connectionBag.getCount(STATE_REMOVED);
   }

   /** {@inheritDoc} */
   @Override
   public final int getThreadsAwaitingConnection()
   {
      return connectionBag.getPendingQueue();
   }

   /** {@inheritDoc} */
   @Override
   public void softEvictConnections()
   {
      for (PoolBagEntry bagEntry : connectionBag.values()) {
         bagEntry.evicted = true;
      }

      for (PoolBagEntry bagEntry : connectionBag.values(STATE_NOT_IN_USE)) {
         if (connectionBag.reserve(bagEntry)) {
            closeConnection(bagEntry, "(connection evicted by user)");
         }
      }
   }

   /** {@inheritDoc} */
   @Override
   public final synchronized void suspendPool()
   {
      if (suspendResumeLock == SuspendResumeLock.FAUX_LOCK) {
         throw new IllegalStateException("Pool " + config.getPoolName() + " is not suspendable");
      }
      else if (poolState != POOL_SUSPENDED) {
         suspendResumeLock.suspend();
         poolState = POOL_SUSPENDED;
      }
   }

   /** {@inheritDoc} */
   @Override
   public final synchronized void resumePool()
   {
      if (poolState == POOL_SUSPENDED) {
         poolState = POOL_NORMAL;
         fillPool();
         suspendResumeLock.resume();
      }
   }

   // ***********************************************************************
   //                           Package methods
   // ***********************************************************************

   /**
    * Permanently close the real (underlying) connection (eat any exception).
    *
    * @param bagEntry the connection to actually close
    */
   void closeConnection(final PoolBagEntry bagEntry, final String closureReason)
   {
      final Connection connection = bagEntry.connection;
      bagEntry.connection = null;
      bagEntry.cancelMaxLifeTermination();
      if (connectionBag.remove(bagEntry)) {
         final int tc = totalConnections.decrementAndGet();
         if (tc < 0) {
            LOGGER.warn("Internal accounting inconsistency, totalConnections={}", tc, new Exception());
         }
         
         closeConnectionExecutor.execute(new Runnable() {
            @Override
            public void run() {
               poolUtils.quietlyCloseConnection(connection, closureReason);
            }
         });
      }
   }

   // ***********************************************************************
   //                           Private methods
   // ***********************************************************************

   /**
    * Create and add a single connection to the pool.
    */
   private boolean addConnection()
   {
      // Speculative increment of totalConnections with expectation of success
      if (totalConnections.incrementAndGet() > config.getMaximumPoolSize()) {
         totalConnections.decrementAndGet(); // Pool is maxed out, so undo speculative increment of totalConnections
         lastConnectionFailure.set(new SQLException("Hikari pool " + config.getPoolName() +" is at maximum capacity"));
         return true;
      }

      Connection connection = null;
      try {
         String username = config.getUsername();
         String password = config.getPassword();

         connection = (username == null && password == null) ? dataSource.getConnection() : dataSource.getConnection(username, password);
         
         if (isUseJdbc4Validation && !poolUtils.isJdbc4ValidationSupported(connection)) {
            throw new SQLException("JDBC4 Connection.isValid() method not supported, connection test query must be configured");
         }

         final int originalTimeout = poolUtils.getAndSetNetworkTimeout(connection, connectionTimeout);

         transactionIsolation = (transactionIsolation < 0 ? connection.getTransactionIsolation() : transactionIsolation);
         poolUtils.setupConnection(connection, config.getConnectionInitSql(), isAutoCommit, isReadOnly, transactionIsolation, catalog);

         poolUtils.setNetworkTimeout(connection, originalTimeout);
         
         connectionBag.add(new PoolBagEntry(connection, originalTimeout, this));
         lastConnectionFailure.set(null);
         LOGGER.debug("Connection {} added to pool {} ", connection, config.getPoolName());
         return true;
      }
      catch (Exception e) {
         totalConnections.decrementAndGet(); // We failed, so undo speculative increment of totalConnections
         lastConnectionFailure.set(e);
         if (poolState == POOL_NORMAL) {
            LOGGER.debug("Connection attempt to database in pool {} failed: {}", config.getPoolName(), e.getMessage(), e);
         }
         poolUtils.quietlyCloseConnection(connection, "(exception during connection creation)");
         return false;
      }
   }

   /**
    * Fill pool up from current idle connections (as they are perceived at the point of execution) to minimumIdle connections.
    */
   private void fillPool()
   {
      final int connectionsToAdd = Math.min(config.getMaximumPoolSize() - totalConnections.get(), config.getMinimumIdle() - getIdleConnections());
      for (int i = 0; i < connectionsToAdd; i++) {
         addBagItem();
      }

      if (connectionsToAdd > 0 && LOGGER.isDebugEnabled()) {
         addConnectionExecutor.execute(new Runnable() {
            @Override
            public void run() {
               logPoolState("After fill ");
            }
         });
      }
   }

   /**
    * Check whether the connection is alive or not.
    *
    * @param connection the connection to test
    * @return true if the connection is alive, false if it is not alive or we timed out
    */
   private boolean isConnectionAlive(final Connection connection)
   {
      try {
         int timeoutSec = (int) TimeUnit.MILLISECONDS.toSeconds(config.getValidationTimeout());

         if (isUseJdbc4Validation) {
            return connection.isValid(timeoutSec);
         }

         final int originalTimeout = poolUtils.getAndSetNetworkTimeout(connection, config.getValidationTimeout());

         try (Statement statement = connection.createStatement()) {
            poolUtils.setQueryTimeout(statement, timeoutSec);
            try (ResultSet rs = statement.executeQuery(config.getConnectionTestQuery())) { 
               /* auto close */
            }
         }

         if (isIsolateInternalQueries && !isAutoCommit) {
            connection.rollback();
         }

         poolUtils.setNetworkTimeout(connection, originalTimeout);

         return true;
      }
      catch (SQLException e) {
         LOGGER.warn("Exception during alive check, Connection ({}) declared dead.", connection, e);
         return false;
      }
   }

   /**
    * Attempt to abort() active connections, or close() them.
    */
   private void abortActiveConnections(final ExecutorService assassinExecutor)
   {
      for (PoolBagEntry bagEntry : connectionBag.values(STATE_IN_USE)) {
         try {
            bagEntry.aborted = bagEntry.evicted = true;
            bagEntry.connection.abort(assassinExecutor);
         }
         catch (Throwable e) {
            poolUtils.quietlyCloseConnection(bagEntry.connection, "(connection aborted during shutdown)");
         }
         finally {
            bagEntry.connection = null;
            if (connectionBag.remove(bagEntry)) {
               totalConnections.decrementAndGet();
            }
         }
      }
   }
   
   /**
    * Fill the pool up to the minimum size.
    */
   private void initializeConnections()
   {
      if (config.isInitializationFailFast()) {
         try {
            if (!addConnection()) {
               throw lastConnectionFailure.getAndSet(null);
            }

            ConnectionProxy connection = (ConnectionProxy) getConnection();
            connection.getPoolBagEntry().evicted = (config.getMinimumIdle() == 0);
            connection.close();
         }
         catch (Throwable e) {
            try {
               shutdown();
            }
            catch (Throwable ex) {
               e.addSuppressed(ex);
            }

            throw new PoolInitializationException(e);
         }
      }

      fillPool();
   }

   private PoolStats getPoolStats()
   {
      return new PoolStats(TimeUnit.SECONDS.toMillis(1)) {
         @Override
         protected void update() {
            this.pendingThreads = HikariPool.this.getThreadsAwaitingConnection();
            this.idleConnections = HikariPool.this.getIdleConnections();
            this.totalConnections = HikariPool.this.getTotalConnections();
            this.activeConnections = HikariPool.this.getActiveConnections();
         }
      };
   }

   // ***********************************************************************
   //                      Non-anonymous Inner-classes
   // ***********************************************************************

   /**
    * The house keeping task to retire idle connections.
    */
   private class HouseKeeper implements Runnable
   {
      private volatile long previous = clockSource.currentTime();

      @Override
      public void run()
      {
         connectionTimeout = config.getConnectionTimeout(); // refresh member in case it changed

         final long now = clockSource.currentTime();
         final long idleTimeout = config.getIdleTimeout();

         // Detect retrograde time as well as forward leaps of unacceptable duration
         if (now < previous || now > clockSource.plusMillis(previous, (2 * HOUSEKEEPING_PERIOD_MS))) {
            LOGGER.warn("Unusual system clock change detected, soft-evicting connections from pool.");
            softEvictConnections();
            fillPool();
            return;
         }

         previous = now;

         logPoolState("Before cleanup ");
         for (PoolBagEntry bagEntry : connectionBag.values(STATE_NOT_IN_USE)) {
            if (connectionBag.reserve(bagEntry)) {
               if (bagEntry.evicted) {
                  closeConnection(bagEntry, "(connection evicted)");
               }
               else if (idleTimeout > 0L && clockSource.elapsedMillis(bagEntry.lastAccess, now) > idleTimeout) {
                  closeConnection(bagEntry, "(connection passed idleTimeout)");
               }
               else {
                  connectionBag.unreserve(bagEntry);
               }
            }
         }
         
         logPoolState("After cleanup ");

         fillPool(); // Try to maintain minimum connections
      }
   }
}


File: src/main/java/com/zaxxer/hikari/pool/PoolBagEntry.java
/*
 * Copyright (C) 2014 Brett Wooldridge
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
package com.zaxxer.hikari.pool;

import java.sql.Connection;
import java.sql.Statement;
import java.util.concurrent.ScheduledFuture;
import java.util.concurrent.ThreadLocalRandom;
import java.util.concurrent.TimeUnit;
import java.util.concurrent.atomic.AtomicInteger;

import com.zaxxer.hikari.util.ClockSource;
import com.zaxxer.hikari.util.FastList;
import com.zaxxer.hikari.util.IConcurrentBagEntry;

/**
 * Entry used in the ConcurrentBag to track Connection instances.
 *
 * @author Brett Wooldridge
 */
public final class PoolBagEntry implements IConcurrentBagEntry
{
   public final AtomicInteger state = new AtomicInteger();
   public final FastList<Statement> openStatements;
   public final HikariPool parentPool;

   public Connection connection;
   public int networkTimeout;
   public long lastAccess;
   public volatile long lastOpenTime;
   public volatile boolean evicted;
   public volatile boolean aborted;

   private volatile ScheduledFuture<?> endOfLife;

   public PoolBagEntry(final Connection connection, final int networkTimeout, final HikariPool pool) {
      this.connection = connection;
      this.networkTimeout = networkTimeout;
      this.parentPool = pool;
      this.lastAccess = ClockSource.INSTANCE.currentTime();
      this.openStatements = new FastList<>(Statement.class, 16);

      final long variance = pool.config.getMaxLifetime() > 60_000 ? ThreadLocalRandom.current().nextLong(10_000) : 0;
      final long maxLifetime = pool.config.getMaxLifetime() - variance;
      if (maxLifetime > 0) {
         endOfLife = pool.houseKeepingExecutorService.schedule(new Runnable() {
            @Override
            public void run()
            {
               // If we can reserve it, close it
               if (pool.connectionBag.reserve(PoolBagEntry.this)) {
                  pool.closeConnection(PoolBagEntry.this, "(connection reached maxLifetime)");
               }
               else {
                  // else the connection is "in-use" and we mark it for eviction by pool.releaseConnection() or the housekeeper
                  PoolBagEntry.this.evicted = true;
               }
            }
         }, maxLifetime, TimeUnit.MILLISECONDS);
      }
   }

   void cancelMaxLifeTermination()
   {
      if (endOfLife != null) {
         endOfLife.cancel(false);
      }
   }


   /** {@inheritDoc} */
   @Override
   public AtomicInteger state()
   {
      return state;
   }

   @Override
   public String toString()
   {
      return "Connection......" + connection + "\n"
           + "  Last  access.." + lastAccess + "\n"
           + "  Last open....." + lastOpenTime + "\n"
           + "  State........." + stateToString();
   }

   private String stateToString()
   {
      switch (state.get()) {
      case STATE_IN_USE:
         return "IN_USE";
      case STATE_NOT_IN_USE:
         return "NOT_IN_USE";
      case STATE_REMOVED:
         return "REMOVED";
      case STATE_RESERVED:
         return "RESERVED";
      default:
         return "Invalid";
      }
   }
}


File: src/main/java/com/zaxxer/hikari/util/ConcurrentBag.java
/*
 * Copyright (C) 2013, 2014 Brett Wooldridge
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
package com.zaxxer.hikari.util;

import static com.zaxxer.hikari.util.IConcurrentBagEntry.STATE_IN_USE;
import static com.zaxxer.hikari.util.IConcurrentBagEntry.STATE_NOT_IN_USE;
import static com.zaxxer.hikari.util.IConcurrentBagEntry.STATE_REMOVED;
import static com.zaxxer.hikari.util.IConcurrentBagEntry.STATE_RESERVED;

import java.lang.ref.WeakReference;
import java.util.ArrayList;
import java.util.List;
import java.util.concurrent.CopyOnWriteArrayList;
import java.util.concurrent.Future;
import java.util.concurrent.TimeUnit;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

/**
 * This is a specialized concurrent bag that achieves superior performance
 * to LinkedBlockingQueue and LinkedTransferQueue for the purposes of a
 * connection pool.  It uses ThreadLocal storage when possible to avoid
 * locks, but resorts to scanning a common collection if there are no
 * available items in the ThreadLocal list.  Not-in-use items in the
 * ThreadLocal lists can be "stolen" when the borrowing thread has none
 * of its own.  It is a "lock-less" implementation using a specialized
 * AbstractQueuedLongSynchronizer to manage cross-thread signaling.
 *
 * Note that items that are "borrowed" from the bag are not actually
 * removed from any collection, so garbage collection will not occur
 * even if the reference is abandoned.  Thus care must be taken to
 * "requite" borrowed objects otherwise a memory leak will result.  Only
 * the "remove" method can completely remove an object from the bag.
 *
 * @author Brett Wooldridge
 *
 * @param <T> the templated type to store in the bag
 */
@SuppressWarnings("rawtypes")
public class ConcurrentBag<T extends IConcurrentBagEntry> implements AutoCloseable
{
   private static final Logger LOGGER = LoggerFactory.getLogger(ConcurrentBag.class);

   private final QueuedSequenceSynchronizer synchronizer;
   private final CopyOnWriteArrayList<T> sharedList;
   private final boolean weakThreadLocals;

   private final ThreadLocal<List> threadList;
   private final IBagStateListener listener;
   private volatile boolean closed;


   /**
    * Construct a ConcurrentBag with the specified listener.
    *
    * @param listener the IBagStateListener to attach to this bag
    */
   public ConcurrentBag(IBagStateListener listener)
   {
      this.listener = listener;
      this.weakThreadLocals = useWeakThreadLocals();

      this.sharedList = new CopyOnWriteArrayList<>();
      this.synchronizer = new QueuedSequenceSynchronizer();
      if (weakThreadLocals) {
         this.threadList = new ThreadLocal<>(); 
      }
      else {
         this.threadList = new ThreadLocal<List>() {
            @Override
            protected List initialValue()
            {
               return new FastList<>(IConcurrentBagEntry.class, 16);
            }
         };
      }
   }

   /**
    * The method will borrow a BagEntry from the bag, blocking for the
    * specified timeout if none are available.
    * 
    * @param timeout how long to wait before giving up, in units of unit
    * @param timeUnit a <code>TimeUnit</code> determining how to interpret the timeout parameter
    * @return a borrowed instance from the bag or null if a timeout occurs
    * @throws InterruptedException if interrupted while waiting
    */
   @SuppressWarnings("unchecked")
   public T borrow(long timeout, final TimeUnit timeUnit) throws InterruptedException
   {
      // Try the thread-local list first, if there are no blocked threads waiting already
      if (!synchronizer.hasQueuedThreads()) {
         List<?> list = threadList.get();
         if (weakThreadLocals && list == null) {
            list = new ArrayList<>(16);
            threadList.set(list);
         }

         for (int i = list.size() - 1; i >= 0; i--) {
            final T bagEntry = (T) (weakThreadLocals ? ((WeakReference) list.remove(i)).get() : list.remove(i));
            if (bagEntry != null && bagEntry.state().compareAndSet(STATE_NOT_IN_USE, STATE_IN_USE)) {
               return bagEntry;
            }
         }
      }

      // Otherwise, scan the shared list ... for maximum of timeout
      timeout = timeUnit.toNanos(timeout);
      Future<Boolean> addItemFuture = null;
      final long startScan = System.nanoTime();
      final long originTimeout = timeout;
      long startSeq;
      do {
         do {
            startSeq = synchronizer.currentSequence();
            for (final T bagEntry : sharedList) {
               if (bagEntry.state().compareAndSet(STATE_NOT_IN_USE, STATE_IN_USE)) {
                  return bagEntry;
               }
            }
         } while (startSeq < synchronizer.currentSequence());

         if (addItemFuture == null || addItemFuture.isDone()) {
            addItemFuture = listener.addBagItem();
         }

         timeout = originTimeout - (System.nanoTime() - startScan);
      } while (timeout > 1000L && synchronizer.waitUntilSequenceExceeded(startSeq, timeout));

      return null;
   }

   /**
    * This method will return a borrowed object to the bag.  Objects
    * that are borrowed from the bag but never "requited" will result
    * in a memory leak.
    *
    * @param bagEntry the value to return to the bag
    * @throws NullPointerException if value is null
    * @throws IllegalStateException if the requited value was not borrowed from the bag
    */
   @SuppressWarnings("unchecked")
   public void requite(final T bagEntry)
   {
      if (bagEntry.state().compareAndSet(STATE_IN_USE, STATE_NOT_IN_USE)) {
         final List threadLocalList = threadList.get();
         if (threadLocalList != null) {
            threadLocalList.add((weakThreadLocals ? new WeakReference<>(bagEntry) : bagEntry));
         }

         synchronizer.signal();
      }
      else {
         LOGGER.warn("Attempt to remove an object from the bag that does not exist: {}", bagEntry);
      }
   }

   /**
    * Add a new object to the bag for others to borrow.
    *
    * @param bagEntry an object to add to the bag
    */
   public void add(final T bagEntry)
   {
      if (closed) {
         LOGGER.info("ConcurrentBag has been closed, ignoring add()");
         throw new IllegalStateException("ConcurrentBag has been closed, ignoring add()");
      }

      sharedList.add(bagEntry);
      synchronizer.signal();
   }

   /**
    * Remove a value from the bag.  This method should only be called
    * with objects obtained by <code>borrow(long, TimeUnit)</code> or <code>reserve(T)</code>
    *
    * @param bagEntry the value to remove
    * @return true if the entry was removed, false otherwise
    * @throws IllegalStateException if an attempt is made to remove an object
    *         from the bag that was not borrowed or reserved first
    */
   public boolean remove(final T bagEntry)
   {
      if (!bagEntry.state().compareAndSet(STATE_IN_USE, STATE_REMOVED) && !bagEntry.state().compareAndSet(STATE_RESERVED, STATE_REMOVED) && !closed) {
         LOGGER.warn("Attempt to remove an object from the bag that was not borrowed or reserved: {}", bagEntry);
         return false;
      }

      final boolean removed = sharedList.remove(bagEntry);
      if (!removed && !closed) {
         LOGGER.warn("Attempt to remove an object from the bag that does not exist: {}", bagEntry);
      }
      return removed;
   }

   /**
    * Close the bag to further adds.
    */
   @Override
   public void close()
   {
      closed = true;
   }

   /**
    * This method provides a "snapshot" in time of the BagEntry
    * items in the bag in the specified state.  It does not "lock"
    * or reserve items in any way.  Call <code>reserve(T)</code>
    * on items in list before performing any action on them.
    *
    * @param state one of the {@link IConcurrentBagEntry} states
    * @return a possibly empty list of objects having the state specified
    */
   public List<T> values(final int state)
   {
      final ArrayList<T> list = new ArrayList<>(sharedList.size());
      for (final T reference : sharedList) {
         if (reference.state().get() == state) {
            list.add(reference);
         }
      }

      return list;
   }

   /**
    * This method provides a "snapshot" in time of the bag items.  It
    * does not "lock" or reserve items in any way.  Call <code>reserve(T)</code>
    * on items in the list, or understand the concurrency implications of
    * modifying items, before performing any action on them.
    *
    * @return a possibly empty list of (all) bag items
    */
   @SuppressWarnings("unchecked")
   public List<T> values()
   {
      return (List<T>) sharedList.clone();
   }

   /**
    * The method is used to make an item in the bag "unavailable" for
    * borrowing.  It is primarily used when wanting to operate on items
    * returned by the <code>values(int)</code> method.  Items that are
    * reserved can be removed from the bag via <code>remove(T)</code>
    * without the need to unreserve them.  Items that are not removed
    * from the bag can be make available for borrowing again by calling
    * the <code>unreserve(T)</code> method.
    *
    * @param bagEntry the item to reserve
    * @return true if the item was able to be reserved, false otherwise
    */
   public boolean reserve(final T bagEntry)
   {
      return bagEntry.state().compareAndSet(STATE_NOT_IN_USE, STATE_RESERVED);
   }

   /**
    * This method is used to make an item reserved via <code>reserve(T)</code>
    * available again for borrowing.
    *
    * @param bagEntry the item to unreserve
    */
   public void unreserve(final T bagEntry)
   {
      if (bagEntry.state().compareAndSet(STATE_RESERVED, STATE_NOT_IN_USE)) {
         synchronizer.signal();
      }
      else {
         LOGGER.warn("Attempt to relinquish an object to the bag that was not reserved: {}", bagEntry);
      }
   }

   /**
    * Get the number of threads pending (waiting) for an item from the
    * bag to become available.
    *
    * @return the number of threads waiting for items from the bag
    */
   public int getPendingQueue()
   {
      return synchronizer.getQueueLength();
   }

   /**
    * Get a count of the number of items in the specified state at the time of this call.
    *
    * @param state the state of the items to count
    * @return a count of how many items in the bag are in the specified state
    */
   public int getCount(final int state)
   {
      int count = 0;
      for (final T reference : sharedList) {
         if (reference.state().get() == state) {
            count++;
         }
      }
      return count;
   }

   /**
    * Get the total number of items in the bag.
    *
    * @return the number of items in the bag 
    */
   public int size()
   {
      return sharedList.size();
   }

   public void dumpState()
   {
      for (T bagEntry : sharedList) {
         LOGGER.info(bagEntry.toString());
      }
   }

   /**
    * Determine whether to use WeakReferences based on whether there is a
    * custom ClassLoader implementation sitting between this class and the
    * System ClassLoader.
    *
    * @return true if we should use WeakReferences in our ThreadLocals, false otherwise
    */
   private boolean useWeakThreadLocals()
   {
      try {
         if (System.getProperty("com.zaxxer.hikari.useWeakReferences") != null) {   // undocumented manual override of WeakReference behavior
            return Boolean.getBoolean("com.zaxxer.hikari.useWeakReferences");
         }

         return getClass().getClassLoader() != ClassLoader.getSystemClassLoader();
      }
      catch (SecurityException se) {
         return true;
      }
   }
}


File: src/main/java/com/zaxxer/hikari/util/IBagStateListener.java
/*
 * Copyright (C) 2013, 2014 Brett Wooldridge
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
package com.zaxxer.hikari.util;

import java.util.concurrent.Future;

/**
 * This interface is implemented by a listener to the ConcurrentBag.  The
 * listener will be informed of when the bag has become empty.  The usual
 * course of action by the listener in this case is to attempt to add an
 * item to the bag.
 *
 * @author Brett Wooldridge
 */
public interface IBagStateListener
{
   Future<Boolean> addBagItem();
}


File: src/main/java/com/zaxxer/hikari/util/IConcurrentBagEntry.java
/*
 * Copyright (C) 2014 Brett Wooldridge
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
package com.zaxxer.hikari.util;

import java.util.concurrent.atomic.AtomicInteger;

/**
 * @author Brett Wooldridge
 */
public interface IConcurrentBagEntry
{
   int STATE_NOT_IN_USE = 0;
   int STATE_IN_USE = 1;
   int STATE_REMOVED = -1;
   int STATE_RESERVED = -2;

   AtomicInteger state();
}


File: src/test/java/com/zaxxer/hikari/TestConcurrentBag.java
/*
 * Copyright (C) 2013 Brett Wooldridge
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

package com.zaxxer.hikari;

import java.io.ByteArrayOutputStream;
import java.io.PrintStream;
import java.util.concurrent.ExecutionException;
import java.util.concurrent.Future;
import java.util.concurrent.TimeUnit;
import java.util.concurrent.TimeoutException;

import org.junit.AfterClass;
import org.junit.Assert;
import org.junit.BeforeClass;
import org.junit.Test;

import com.zaxxer.hikari.pool.HikariPool;
import com.zaxxer.hikari.pool.PoolBagEntry;
import com.zaxxer.hikari.util.ConcurrentBag;
import com.zaxxer.hikari.util.IBagStateListener;

/**
 *
 * @author Brett Wooldridge
 */
public class TestConcurrentBag
{
   private static HikariDataSource ds;

   @BeforeClass
   public static void setup()
   {
      HikariConfig config = new HikariConfig();
      config.setMinimumIdle(1);
      config.setMaximumPoolSize(2);
      config.setInitializationFailFast(true);
      config.setConnectionTestQuery("VALUES 1");
      config.setDataSourceClassName("com.zaxxer.hikari.mocks.StubDataSource");

      ds = new HikariDataSource(config);      
   }

   @AfterClass
   public static void teardown()
   {
      ds.close();
   }

   @Test
   public void testConcurrentBag() throws InterruptedException
   {
      ConcurrentBag<PoolBagEntry> bag = new ConcurrentBag<PoolBagEntry>(new IBagStateListener() {
         @Override
         public Future<Boolean> addBagItem()
         {
            return new Future<Boolean>() {
               @Override
               public boolean isDone()
               {
                  return true;
               }
               
               @Override
               public boolean isCancelled()
               {
                  return false;
               }
               
               @Override
               public Boolean get(long timeout, TimeUnit unit) throws InterruptedException, ExecutionException, TimeoutException
               {
                  return null;
               }
               
               @Override
               public Boolean get() throws InterruptedException, ExecutionException
               {
                  return true;
               }
               
               @Override
               public boolean cancel(boolean mayInterruptIfRunning)
               {
                  return false;
               }
            };
         }
      });
      Assert.assertEquals(0, bag.values(8).size());

      HikariPool pool = TestElf.getPool(ds);
      PoolBagEntry reserved = new PoolBagEntry(null, 0, TestElf.getPool(ds));
      bag.add(reserved);
      bag.reserve(reserved);      // reserved

      PoolBagEntry inuse = new PoolBagEntry(null, 0, pool);
      bag.add(inuse);
      bag.borrow(2, TimeUnit.MILLISECONDS); // in use
      
      PoolBagEntry notinuse = new PoolBagEntry(null, 0, pool);
      bag.add(notinuse); // not in use

      bag.dumpState();

      ByteArrayOutputStream baos = new ByteArrayOutputStream();
      PrintStream ps = new PrintStream(baos, true);
      TestElf.setSlf4jTargetStream(ConcurrentBag.class, ps);
      
      bag.requite(reserved);
      Assert.assertTrue(new String(baos.toByteArray()).contains("does not exist"));

      bag.remove(notinuse);
      Assert.assertTrue(new String(baos.toByteArray()).contains("not borrowed or reserved"));

      bag.unreserve(notinuse);
      Assert.assertTrue(new String(baos.toByteArray()).contains("was not reserved"));

      bag.remove(inuse);
      bag.remove(inuse);
      Assert.assertTrue(new String(baos.toByteArray()).contains("not borrowed or reserved"));

      bag.close();
      try {
         PoolBagEntry bagEntry = new PoolBagEntry(null, 0, pool);
         bag.add(bagEntry);
         Assert.assertNotEquals(bagEntry, bag.borrow(100, TimeUnit.MILLISECONDS));
      }
      catch (IllegalStateException e) {
         Assert.assertTrue(new String(baos.toByteArray()).contains("ignoring add()"));
      }

      Assert.assertNotNull(notinuse.toString());
   }
}
