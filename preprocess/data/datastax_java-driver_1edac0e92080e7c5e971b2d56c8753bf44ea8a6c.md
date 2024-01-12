Refactoring Types: ['Extract Method']
datastax/driver/core/DynamicConnectionPool.java
/*
 *      Copyright (C) 2012-2015 DataStax Inc.
 *
 *   Licensed under the Apache License, Version 2.0 (the "License");
 *   you may not use this file except in compliance with the License.
 *   You may obtain a copy of the License at
 *
 *      http://www.apache.org/licenses/LICENSE-2.0
 *
 *   Unless required by applicable law or agreed to in writing, software
 *   distributed under the License is distributed on an "AS IS" BASIS,
 *   WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 *   See the License for the specific language governing permissions and
 *   limitations under the License.
 */
package com.datastax.driver.core;


import java.util.*;
import java.util.concurrent.*;
import java.util.concurrent.atomic.AtomicInteger;
import java.util.concurrent.locks.*;

import com.google.common.annotations.VisibleForTesting;
import com.google.common.collect.Lists;
import com.google.common.util.concurrent.*;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import com.datastax.driver.core.exceptions.AuthenticationException;
import com.datastax.driver.core.utils.MoreFutures;

import static com.datastax.driver.core.Connection.State.*;

/**
 * A connection pool with a varying number of connections.
 *
 * This is used with {@link ProtocolVersion#V2} and lower.
 */
class DynamicConnectionPool extends HostConnectionPool {

    private static final Logger logger = LoggerFactory.getLogger(DynamicConnectionPool.class);

    private static final int MAX_SIMULTANEOUS_CREATION = 1;

    // When a request timeout, we may never release its stream ID. So over time, a given connection
    // may get less an less available streams. When the number of available ones go below the
    // following threshold, we just replace the connection by a new one.
    private static final int MIN_AVAILABLE_STREAMS = 96;

    final List<Connection> connections;
    private final AtomicInteger open;
    /** The total number of in-flight requests on all connections of this pool. */
    final AtomicInteger totalInFlight = new AtomicInteger();
    /** The maximum value of {@link #totalInFlight} since the last call to {@link #cleanupIdleConnections(long)}*/
    private final AtomicInteger maxTotalInFlight = new AtomicInteger();

    @VisibleForTesting
    final Set<Connection> trash = new CopyOnWriteArraySet<Connection>();

    private volatile int waiter = 0;
    private final Lock waitLock = new ReentrantLock(true);
    private final Condition hasAvailableConnection = waitLock.newCondition();

    private final Runnable newConnectionTask;

    private final AtomicInteger scheduledForCreation = new AtomicInteger();

    public DynamicConnectionPool(Host host, HostDistance hostDistance, SessionManager manager) {
        super(host, hostDistance, manager);

        this.newConnectionTask = new Runnable() {
            @Override
            public void run() {
                addConnectionIfUnderMaximum();
                scheduledForCreation.decrementAndGet();
            }
        };

        this.connections = new CopyOnWriteArrayList<Connection>();
        this.open = new AtomicInteger();
    }

    @Override
    ListenableFuture<Void> initAsync(Connection reusedConnection) {
        // Create initial core connections
        int capacity = options().getCoreConnectionsPerHost(hostDistance);
        final List<Connection> connections = Lists.newArrayListWithCapacity(capacity);
        final List<ListenableFuture<Void>> connectionFutures = Lists.newArrayListWithCapacity(capacity);
        for (int i = 0; i < capacity; i++) {
            Connection connection;
            ListenableFuture<Void> connectionFuture;
            // reuse the existing connection only once
            if (reusedConnection != null && reusedConnection.setPool(this)) {
                connection = reusedConnection;
                connectionFuture = MoreFutures.VOID_SUCCESS;
            } else {
                connection = manager.connectionFactory().newConnection(this);
                connectionFuture = connection.initAsync();
            }
            reusedConnection = null;
            connections.add(connection);
            connectionFutures.add(connectionFuture);
        }

        Executor initExecutor = manager.cluster.manager.configuration.getPoolingOptions().getInitializationExecutor();

        ListenableFuture<List<Void>> allConnectionsFuture = Futures.allAsList(connectionFutures);

        final SettableFuture<Void> initFuture = SettableFuture.create();
        Futures.addCallback(allConnectionsFuture, new FutureCallback<List<Void>>() {
            @Override
            public void onSuccess(List<Void> l) {
                DynamicConnectionPool.this.connections.addAll(connections);
                open.set(l.size());
                if (isClosed()) {
                    initFuture.setException(new ConnectionException(host.getSocketAddress(), "Pool was closed during initialization"));
                    // we're not sure if closeAsync() saw the connections, so ensure they get closed
                    forceClose(connections);
                } else {
                    logger.trace("Created connection pool to host {}", host);
                    phase.compareAndSet(Phase.INITIALIZING, Phase.READY);
                    initFuture.set(null);
                }
            }

            @Override
            public void onFailure(Throwable t) {
                phase.compareAndSet(Phase.INITIALIZING, Phase.INIT_FAILED);
                forceClose(connections);
                initFuture.setException(t);
            }
        }, initExecutor);
        return initFuture;
    }

    // Clean up if we got an error at construction time but still created part of the core connections
    private void forceClose(List<Connection> connections) {
        for (Connection connection : connections) {
            connection.closeAsync().force();
        }
    }

    private PoolingOptions options() {
        return manager.configuration().getPoolingOptions();
    }

    @Override
    public Connection borrowConnection(long timeout, TimeUnit unit) throws ConnectionException, TimeoutException {
        Phase phase = this.phase.get();
        if (phase != Phase.READY)
            // Note: throwing a ConnectionException is probably fine in practice as it will trigger the creation of a new host.
            // That being said, maybe having a specific exception could be cleaner.
            throw new ConnectionException(host.getSocketAddress(), "Pool is " + phase);

        if (connections.isEmpty()) {
            for (int i = 0; i < options().getCoreConnectionsPerHost(hostDistance); i++) {
                // We don't respect MAX_SIMULTANEOUS_CREATION here because it's  only to
                // protect against creating connection in excess of core too quickly
                scheduledForCreation.incrementAndGet();
                manager.blockingExecutor().submit(newConnectionTask);
            }
            Connection c = waitForConnection(timeout, unit);
            totalInFlight.incrementAndGet();
            c.setKeyspace(manager.poolsState.keyspace);
            return c;
        }

        int minInFlight = Integer.MAX_VALUE;
        Connection leastBusy = null;
        for (Connection connection : connections) {
            int inFlight = connection.inFlight.get();
            if (inFlight < minInFlight) {
                minInFlight = inFlight;
                leastBusy = connection;
            }
        }

        if (leastBusy == null) {
            // We could have raced with a shutdown since the last check
            if (isClosed())
                throw new ConnectionException(host.getSocketAddress(), "Pool is shutdown");
            // This might maybe happen if the number of core connections per host is 0 and a connection was trashed between
            // the previous check to connections and now. But in that case, the line above will have trigger the creation of
            // a new connection, so just wait that connection and move on
            leastBusy = waitForConnection(timeout, unit);
        } else {
            while (true) {
                int inFlight = leastBusy.inFlight.get();

                if (inFlight >= leastBusy.maxAvailableStreams()) {
                    leastBusy = waitForConnection(timeout, unit);
                    break;
                }

                if (leastBusy.inFlight.compareAndSet(inFlight, inFlight + 1))
                    break;
            }
        }

        int totalInFlightCount = totalInFlight.incrementAndGet();
        // update max atomically:
        while (true) {
            int oldMax = maxTotalInFlight.get();
            if (totalInFlightCount <= oldMax || maxTotalInFlight.compareAndSet(oldMax, totalInFlightCount))
                break;
        }

        int connectionCount = open.get() + scheduledForCreation.get();
        if (connectionCount < options().getMaxConnectionsPerHost(hostDistance)) {
            // Add a connection if we fill the first n-1 connections and almost fill the last one
            int currentCapacity = (connectionCount - 1) * StreamIdGenerator.MAX_STREAM_PER_CONNECTION_V2
                + options().getMaxSimultaneousRequestsPerConnectionThreshold(hostDistance);
            if (totalInFlightCount > currentCapacity)
                maybeSpawnNewConnection();
        }

        leastBusy.setKeyspace(manager.poolsState.keyspace);
        return leastBusy;
    }

    private void awaitAvailableConnection(long timeout, TimeUnit unit) throws InterruptedException {
        waitLock.lock();
        waiter++;
        try {
            hasAvailableConnection.await(timeout, unit);
        } finally {
            waiter--;
            waitLock.unlock();
        }
    }

    private void signalAvailableConnection() {
        // Quick check if it's worth signaling to avoid locking
        if (waiter == 0)
            return;

        waitLock.lock();
        try {
            hasAvailableConnection.signal();
        } finally {
            waitLock.unlock();
        }
    }

    private void signalAllAvailableConnection() {
        // Quick check if it's worth signaling to avoid locking
        if (waiter == 0)
            return;

        waitLock.lock();
        try {
            hasAvailableConnection.signalAll();
        } finally {
            waitLock.unlock();
        }
    }

    private Connection waitForConnection(long timeout, TimeUnit unit) throws ConnectionException, TimeoutException {
        if (timeout == 0)
            throw new TimeoutException();

        long start = System.nanoTime();
        long remaining = timeout;
        do {
            try {
                awaitAvailableConnection(remaining, unit);
            } catch (InterruptedException e) {
                Thread.currentThread().interrupt();
                // If we're interrupted fine, check if there is a connection available but stop waiting otherwise
                timeout = 0; // this will make us stop the loop if we don't get a connection right away
            }

            if (isClosed())
                throw new ConnectionException(host.getSocketAddress(), "Pool is shutdown");

            int minInFlight = Integer.MAX_VALUE;
            Connection leastBusy = null;
            for (Connection connection : connections) {
                int inFlight = connection.inFlight.get();
                if (inFlight < minInFlight) {
                    minInFlight = inFlight;
                    leastBusy = connection;
                }
            }

            // If we race with shutdown, leastBusy could be null. In that case we just loop and we'll throw on the next
            // iteration anyway
            if (leastBusy != null) {
                while (true) {
                    int inFlight = leastBusy.inFlight.get();

                    if (inFlight >= leastBusy.maxAvailableStreams())
                        break;

                    if (leastBusy.inFlight.compareAndSet(inFlight, inFlight + 1))
                        return leastBusy;
                }
            }

            remaining = timeout - Cluster.timeSince(start, unit);
        } while (remaining > 0);

        throw new TimeoutException();
    }

    @Override
    public void returnConnection(Connection connection) {
        connection.inFlight.decrementAndGet();
        totalInFlight.decrementAndGet();

        if (isClosed()) {
            close(connection);
            return;
        }

        if (connection.isDefunct()) {
            // As part of making it defunct, we have already replaced it or
            // closed the pool.
            return;
        }

        if (connection.state.get() != TRASHED) {
            if (connection.maxAvailableStreams() < MIN_AVAILABLE_STREAMS) {
                replaceConnection(connection);
            } else {
                signalAvailableConnection();
            }
        }
    }

    // Trash the connection and create a new one, but we don't call trashConnection
    // directly because we want to make sure the connection is always trashed.
    private void replaceConnection(Connection connection) {
        if (!connection.state.compareAndSet(OPEN, TRASHED))
            return;
        open.decrementAndGet();
        maybeSpawnNewConnection();
        connection.maxIdleTime = Long.MIN_VALUE;
        doTrashConnection(connection);
    }

    private boolean trashConnection(Connection connection) {
        if (!connection.state.compareAndSet(OPEN, TRASHED))
            return true;

        // First, make sure we don't go below core connections
        for (;;) {
            int opened = open.get();
            if (opened <= options().getCoreConnectionsPerHost(hostDistance)) {
                connection.state.set(OPEN);
                return false;
            }

            if (open.compareAndSet(opened, opened - 1))
                break;
        }
        logger.trace("Trashing {}", connection);
        connection.maxIdleTime = System.currentTimeMillis() + options().getIdleTimeoutSeconds() * 1000;
        doTrashConnection(connection);
        return true;
    }

    private void doTrashConnection(Connection connection) {
        connections.remove(connection);
        trash.add(connection);
    }

    private boolean addConnectionIfUnderMaximum() {

        // First, make sure we don't cross the allowed limit of open connections
        for(;;) {
            int opened = open.get();
            if (opened >= options().getMaxConnectionsPerHost(hostDistance))
                return false;

            if (open.compareAndSet(opened, opened + 1))
                break;
        }

        if (phase.get() != Phase.READY) {
            open.decrementAndGet();
            return false;
        }

        // Now really open the connection
        try {
            Connection newConnection = tryResurrectFromTrash();
            if (newConnection == null) {
                logger.debug("Creating new connection on busy pool to {}", host);
                newConnection = manager.connectionFactory().open(this);
            }
            connections.add(newConnection);

            newConnection.state.compareAndSet(RESURRECTING, OPEN); // no-op if it was already OPEN

            // We might have raced with pool shutdown since the last check; ensure the connection gets closed in case the pool did not do it.
            if (isClosed() && !newConnection.isClosed()) {
                close(newConnection);
                open.decrementAndGet();
                return false;
            }

            signalAvailableConnection();
            return true;
        } catch (InterruptedException e) {
            Thread.currentThread().interrupt();
            // Skip the open but ignore otherwise
            open.decrementAndGet();
            return false;
        } catch (ConnectionException e) {
            open.decrementAndGet();
            logger.debug("Connection error to {} while creating additional connection", host);
            return false;
        } catch (AuthenticationException e) {
            // This shouldn't really happen in theory
            open.decrementAndGet();
            logger.error("Authentication error while creating additional connection (error is: {})", e.getMessage());
            return false;
        } catch (UnsupportedProtocolVersionException e) {
            // This shouldn't happen since we shouldn't have been able to connect in the first place
            open.decrementAndGet();
            logger.error("UnsupportedProtocolVersionException error while creating additional connection (error is: {})", e.getMessage());
            return false;
        } catch (ClusterNameMismatchException e) {
            open.decrementAndGet();
            logger.error("ClusterNameMismatchException error while creating additional connection (error is: {})", e.getMessage());
            return false;
        }
    }

    private Connection tryResurrectFromTrash() {
        long highestMaxIdleTime = System.currentTimeMillis();
        Connection chosen = null;

        while (true) {
            for (Connection connection : trash)
                if (connection.maxIdleTime > highestMaxIdleTime && connection.maxAvailableStreams() > MIN_AVAILABLE_STREAMS) {
                    chosen = connection;
                    highestMaxIdleTime = connection.maxIdleTime;
                }

            if (chosen == null)
                return null;
            else if (chosen.state.compareAndSet(TRASHED, RESURRECTING))
                break;
        }
        logger.trace("Resurrecting {}", chosen);
        trash.remove(chosen);
        return chosen;
    }

    private void maybeSpawnNewConnection() {
        while (true) {
            int inCreation = scheduledForCreation.get();
            if (inCreation >= MAX_SIMULTANEOUS_CREATION)
                return;
            if (scheduledForCreation.compareAndSet(inCreation, inCreation + 1))
                break;
        }

        manager.blockingExecutor().submit(newConnectionTask);
    }

    @Override
    void replaceDefunctConnection(final Connection connection) {
        if (connection.state.compareAndSet(OPEN, GONE))
            open.decrementAndGet();
        if (connections.remove(connection))
            manager.blockingExecutor().submit(new Runnable() {
                @Override
                public void run() {
                    addConnectionIfUnderMaximum();
                }
            });
    }

    @Override
    void cleanupIdleConnections(long now) {
        if (isClosed())
            return;

        shrinkIfBelowCapacity();
        cleanupTrash(now);
    }

    /** If we have more active connections than needed, trash some of them */
    private void shrinkIfBelowCapacity() {
        int currentLoad = maxTotalInFlight.getAndSet(totalInFlight.get());

        int needed = currentLoad / StreamIdGenerator.MAX_STREAM_PER_CONNECTION_V2 + 1;
        if (currentLoad % StreamIdGenerator.MAX_STREAM_PER_CONNECTION_V2 > options().getMaxSimultaneousRequestsPerConnectionThreshold(hostDistance))
            needed += 1;
        needed = Math.max(needed, options().getCoreConnectionsPerHost(hostDistance));
        int actual = open.get();
        int toTrash = Math.max(0, actual - needed);

        logger.trace("Current inFlight = {}, {} connections needed, {} connections available, trashing {}",
            currentLoad, needed, actual, toTrash);

        if (toTrash <= 0)
            return;

        for (Connection connection : connections)
            if (trashConnection(connection)) {
                toTrash -= 1;
                if (toTrash == 0)
                    return;
            }
    }

    /** Close connections that have been sitting in the trash for too long */
    private void cleanupTrash(long now) {
        for (Connection connection : trash) {
            if (connection.maxIdleTime < now && connection.state.compareAndSet(TRASHED, GONE)) {
                if (connection.inFlight.get() == 0) {
                    logger.trace("Cleaning up {}", connection);
                    trash.remove(connection);
                    close(connection);
                } else {
                    // Given that idleTimeout >> request timeout, all outstanding requests should
                    // have finished by now, so we should not get here.
                    // Restore the status so that it's retried on the next cleanup.
                    connection.state.set(TRASHED);
                }
            }
        }
    }

    private void close(final Connection connection) {
        connection.closeAsync();
    }

    protected CloseFuture makeCloseFuture() {
        // Wake up all threads that wait
        signalAllAvailableConnection();

        return new CloseFuture.Forwarding(discardAvailableConnections());
    }

    private List<CloseFuture> discardAvailableConnections() {
        // Note: if this gets called before initialization has completed, both connections and trash will be empty,
        // so this will return an empty list

        List<CloseFuture> futures = new ArrayList<CloseFuture>(connections.size() + trash.size());

        for (final Connection connection : connections) {
            CloseFuture future = connection.closeAsync();
            future.addListener(new Runnable() {
                public void run() {
                    if (connection.state.compareAndSet(OPEN, GONE))
                        open.decrementAndGet();
                }
            }, MoreExecutors.sameThreadExecutor());
            futures.add(future);
        }

        // Some connections in the trash might still be open if they hadn't reached their idle timeout
        for (Connection connection : trash)
            futures.add(connection.closeAsync());

        return futures;
    }

    // This creates connections if we have less than core connections (if we
    // have more than core, connection will just get trash when we can).
    @Override
    public void ensureCoreConnections() {
        if (isClosed())
            return;

        // Note: this process is a bit racy, but it doesn't matter since we're still guaranteed to not create
        // more connection than maximum (and if we create more than core connection due to a race but this isn't
        // justified by the load, the connection in excess will be quickly trashed anyway)
        int opened = open.get();
        for (int i = opened; i < options().getCoreConnectionsPerHost(hostDistance); i++) {
            // We don't respect MAX_SIMULTANEOUS_CREATION here because it's only to
            // protect against creating connection in excess of core too quickly
            scheduledForCreation.incrementAndGet();
            manager.blockingExecutor().submit(newConnectionTask);
        }
    }

    @Override
    public int opened() {
        return open.get();
    }

    @Override
    int trashed() {
        return trash.size();
    }

    @Override
    public int inFlightQueriesCount() {
        int count = 0;
        for (Connection connection : connections) {
            count += connection.inFlight.get();
        }
        return count;
    }
}


File: driver-core/src/main/java/com/datastax/driver/core/PoolingOptions.java
/*
 *      Copyright (C) 2012-2015 DataStax Inc.
 *
 *   Licensed under the Apache License, Version 2.0 (the "License");
 *   you may not use this file except in compliance with the License.
 *   You may obtain a copy of the License at
 *
 *      http://www.apache.org/licenses/LICENSE-2.0
 *
 *   Unless required by applicable law or agreed to in writing, software
 *   distributed under the License is distributed on an "AS IS" BASIS,
 *   WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 *   See the License for the specific language governing permissions and
 *   limitations under the License.
 */
package com.datastax.driver.core;

import java.util.concurrent.Executor;

import com.google.common.base.Preconditions;
import com.google.common.util.concurrent.MoreExecutors;

/**
 * Options related to connection pooling.
 * <p>
 * The driver uses connections in an asynchronous manner. Meaning that
 * multiple requests can be submitted on the same connection at the same
 * time. This means that the driver only needs to maintain a relatively
 * small number of connections to each Cassandra host. These options allow
 * the driver to control how many connections are kept exactly.
 * <p>
 * <b>With {@code ProtocolVersion#V2} or below:</b>
 * for each host, the driver keeps a core pool of connections open at all
 * times determined by calling ({@link #getCoreConnectionsPerHost}).
 * If the use of those connections reaches a configurable threshold
 * ({@link #getMaxSimultaneousRequestsPerConnectionThreshold}),
 * more connections are created up to the configurable maximum number of
 * connections ({@link #getMaxConnectionsPerHost}). When the pool exceeds
 * the maximum number of connections, connections in excess are
 * reclaimed.
 * <p>
 * <b>With {@code ProtocolVersion#V3} or above:</b>
 * the driver uses a single connection for each {@code LOCAL} or {@code REMOTE}
 * host. This connection can handle a larger amount of simultaneous requests,
 * limited by {@link #getMaxSimultaneousRequestsPerHostThreshold(HostDistance)}.
 * <p>
 * Each of these parameters can be separately set for {@code LOCAL} and
 * {@code REMOTE} hosts ({@link HostDistance}). For {@code IGNORED} hosts,
 * the default for all those settings is 0 and cannot be changed.
 */
public class PoolingOptions {

    private static final int DEFAULT_MAX_REQUESTS_PER_CONNECTION = 100;

    private static final int DEFAULT_CORE_POOL_LOCAL = 2;
    private static final int DEFAULT_CORE_POOL_REMOTE = 1;

    private static final int DEFAULT_MAX_POOL_LOCAL = 8;
    private static final int DEFAULT_MAX_POOL_REMOTE = 2;

    private static final int DEFAULT_MAX_REQUESTS_PER_HOST_LOCAL = 1024;
    private static final int DEFAULT_MAX_REQUESTS_PER_HOST_REMOTE = 256;

    private static final int DEFAULT_IDLE_TIMEOUT_SECONDS = 120;
    private static final int DEFAULT_POOL_TIMEOUT_MILLIS = 5000;
    private static final int DEFAULT_HEARTBEAT_INTERVAL_SECONDS = 30;

    private static final Executor DEFAULT_INITIALIZATION_EXECUTOR = MoreExecutors.sameThreadExecutor();

    private volatile Cluster.Manager manager;

    private final int[] maxSimultaneousRequestsPerConnection = new int[]{ DEFAULT_MAX_REQUESTS_PER_CONNECTION, DEFAULT_MAX_REQUESTS_PER_CONNECTION, 0 };

    private final int[] coreConnections = new int[] { DEFAULT_CORE_POOL_LOCAL, DEFAULT_CORE_POOL_REMOTE, 0 };
    private final int[] maxConnections = new int[] { DEFAULT_MAX_POOL_LOCAL , DEFAULT_MAX_POOL_REMOTE, 0 };

    private volatile int maxSimultaneousRequestsPerHostLocal = DEFAULT_MAX_REQUESTS_PER_HOST_LOCAL;
    private volatile int maxSimultaneousRequestsPerHostRemote = DEFAULT_MAX_REQUESTS_PER_HOST_REMOTE;
    
    private volatile int idleTimeoutSeconds = DEFAULT_IDLE_TIMEOUT_SECONDS;
    private volatile int poolTimeoutMillis = DEFAULT_POOL_TIMEOUT_MILLIS;
    private volatile int heartbeatIntervalSeconds = DEFAULT_HEARTBEAT_INTERVAL_SECONDS;

    private volatile Executor initializationExecutor = DEFAULT_INITIALIZATION_EXECUTOR;

    public PoolingOptions() {}

    void register(Cluster.Manager manager) {
        this.manager = manager;
    }

    /**
     * Returns the number of simultaneous requests on a connection below which
     * connections in excess are reclaimed.
     * <p>
     * This option is only used with {@code ProtocolVersion#V2} or below.
     * <p>
     * If an opened connection to an host at distance {@code distance}
     * handles less than this number of simultaneous requests and there is
     * more than {@link #getCoreConnectionsPerHost} connections open to this
     * host, the connection is closed.
     * <p>
     * The default value for this option is 25 for {@code LOCAL} and
     * {@code REMOTE} hosts.
     *
     * @param distance the {@code HostDistance} for which to return this threshold.
     * @return the configured threshold, or the default one if none have been set.
     *
     * @deprecated this option isn't used anymore with the current pool resizing algorithm.
     */
    @Deprecated
    public int getMinSimultaneousRequestsPerConnectionThreshold(HostDistance distance) {
        return 0;
    }

    /**
     * Sets the number of simultaneous requests on a connection below which
     * connections in excess are reclaimed.
     * <p>
     * This option is only used with {@code ProtocolVersion#V2} or below.
     *
     * @param distance the {@code HostDistance} for which to configure this threshold.
     * @param newMinSimultaneousRequests the value to set (between 0 and 128).
     * @return this {@code PoolingOptions}.
     *
     * @throws IllegalArgumentException if {@code distance == HostDistance.IGNORED}, or if {@code minSimultaneousRequests}
     * is not in range, or if {@code newMinSimultaneousRequests} is greater than the maximum value for this distance.
     *
     * @deprecated this option isn't used anymore with the current pool resizing algorithm.
     */
    @Deprecated
    public synchronized PoolingOptions setMinSimultaneousRequestsPerConnectionThreshold(HostDistance distance, int newMinSimultaneousRequests) {
        return this;
    }

    /**
     * Returns the number of simultaneous requests on all connections to an host after
     * which more connections are created.
     * <p>
     * This option is only used with {@code ProtocolVersion#V2} or below.
     * <p>
     * If all the connections opened to an host at distance {@code
     * distance} connection are handling more than this number of
     * simultaneous requests and there is less than
     * {@link #getMaxConnectionsPerHost} connections open to this host, a
     * new connection is open.
     * <p>
     * Note that a given connection cannot handle more than 128
     * simultaneous requests (protocol limitation).
     * <p>
     * The default value for this option is 100 for {@code LOCAL} and
     * {@code REMOTE} hosts.
     *
     * @param distance the {@code HostDistance} for which to return this threshold.
     * @return the configured threshold, or the default one if none have been set.
     */
    public int getMaxSimultaneousRequestsPerConnectionThreshold(HostDistance distance) {
        return maxSimultaneousRequestsPerConnection[distance.ordinal()];
    }

    /**
     * Sets number of simultaneous requests on all connections to an host after
     * which more connections are created.
     * <p>
     * This option is only used with {@code ProtocolVersion#V2} or below.
     *
     * @param distance the {@code HostDistance} for which to configure this threshold.
     * @param newMaxSimultaneousRequests the value to set (between 0 and 128).
     * @return this {@code PoolingOptions}.
     *
     * @throws IllegalArgumentException if {@code distance == HostDistance.IGNORED}, or if {@code maxSimultaneousRequests}
     * is not in range, or if {@code newMaxSimultaneousRequests} is less than the minimum value for this distance.
     */
    public synchronized PoolingOptions setMaxSimultaneousRequestsPerConnectionThreshold(HostDistance distance, int newMaxSimultaneousRequests) {
        if (distance == HostDistance.IGNORED)
            throw new IllegalArgumentException("Cannot set max simultaneous requests per connection threshold for " + distance + " hosts");

        checkRequestsPerConnectionRange(newMaxSimultaneousRequests, "Max simultaneous requests per connection", distance);
        maxSimultaneousRequestsPerConnection[distance.ordinal()] = newMaxSimultaneousRequests;
        return this;
    }

    /**
     * Returns the core number of connections per host.
     * <p>
     * This option is only used with {@code ProtocolVersion#V2} or below.
     * <p>
     * For the provided {@code distance}, this correspond to the number of
     * connections initially created and kept open to each host of that
     * distance.
     *
     * @param distance the {@code HostDistance} for which to return this threshold.
     * @return the core number of connections per host at distance {@code distance}.
     */
    public int getCoreConnectionsPerHost(HostDistance distance) {
        return coreConnections[distance.ordinal()];
    }

    /**
     * Sets the core number of connections per host.
     * <p>
     * This option is only used with {@code ProtocolVersion#V2} or below.
     *
     * @param distance the {@code HostDistance} for which to set this threshold.
     * @param newCoreConnections the value to set
     * @return this {@code PoolingOptions}.
     *
     * @throws IllegalArgumentException if {@code distance == HostDistance.IGNORED},
     * or if {@code newCoreConnections} is greater than the maximum value for this distance.
     */
    public synchronized PoolingOptions setCoreConnectionsPerHost(HostDistance distance, int newCoreConnections) {
        if (distance == HostDistance.IGNORED)
                throw new IllegalArgumentException("Cannot set core connections per host for " + distance + " hosts");

        checkConnectionsPerHostOrder(newCoreConnections, maxConnections[distance.ordinal()], distance);
        int oldCore = coreConnections[distance.ordinal()];
        coreConnections[distance.ordinal()] = newCoreConnections;
        if (oldCore < newCoreConnections && manager != null)
            manager.ensurePoolsSizing();
        return this;
    }

    /**
     * Returns the maximum number of connections per host.
     * <p>
     * This option is only used with {@code ProtocolVersion#V2} or below.
     * <p>
     * For the provided {@code distance}, this correspond to the maximum
     * number of connections that can be created per host at that distance.
     *
     * @param distance the {@code HostDistance} for which to return this threshold.
     * @return the maximum number of connections per host at distance {@code distance}.
     */
    public int getMaxConnectionsPerHost(HostDistance distance) {
        return maxConnections[distance.ordinal()];
    }

    /**
     * Sets the maximum number of connections per host.
     * <p>
     * This option is only used with {@code ProtocolVersion#V2} or below.
     *
     * @param distance the {@code HostDistance} for which to set this threshold.
     * @param newMaxConnections the value to set
     * @return this {@code PoolingOptions}.
     *
     * @throws IllegalArgumentException if {@code distance == HostDistance.IGNORED},
     * or if {@code newMaxConnections} is less than the core value for this distance.
     */
    public synchronized PoolingOptions setMaxConnectionsPerHost(HostDistance distance, int newMaxConnections) {
        if (distance == HostDistance.IGNORED)
            throw new IllegalArgumentException("Cannot set max connections per host for " + distance + " hosts");

        checkConnectionsPerHostOrder(coreConnections[distance.ordinal()], newMaxConnections, distance);
        maxConnections[distance.ordinal()] = newMaxConnections;
        return this;
    }

    /**
     * Returns the timeout before an idle connection is removed.
     *
     * @return the timeout.
     */
    public int getIdleTimeoutSeconds() {
        return idleTimeoutSeconds;
    }

    /**
     * Sets the timeout before an idle connection is removed.
     * <p>
     * The order of magnitude should be a few minutes (the default is 120 seconds). The
     * timeout that triggers the removal has a granularity of 10 seconds.
     *
     * @param idleTimeoutSeconds the new timeout in seconds.
     * @return this {@code PoolingOptions}.
     *
     * @throws IllegalArgumentException if the timeout is negative.
     */
    public PoolingOptions setIdleTimeoutSeconds(int idleTimeoutSeconds) {
        if (idleTimeoutSeconds < 0)
            throw new IllegalArgumentException("Idle timeout must be positive");
        this.idleTimeoutSeconds = idleTimeoutSeconds;
        return this;
    }

    /**
     * Returns the timeout when trying to acquire a connection from a host's pool.
     *
     * @return the timeout.
     */
    public int getPoolTimeoutMillis() {
        return poolTimeoutMillis;
    }

    /**
     * Sets the timeout when trying to acquire a connection from a host's pool.
     * <p>
     * If no connection is available within that time, the driver will try the
     * next host from the query plan.
     * <p>
     * If this option is set to zero, the driver won't wait at all.
     *
     * @param poolTimeoutMillis the new value in milliseconds.
     * @return this {@code PoolingOptions}
     *
     * @throws IllegalArgumentException if the timeout is negative.
     */
    public PoolingOptions setPoolTimeoutMillis(int poolTimeoutMillis) {
        if (poolTimeoutMillis < 0)
            throw new IllegalArgumentException("Pool timeout must be positive");
        this.poolTimeoutMillis = poolTimeoutMillis;
        return this;
    }

    /**
     * Returns the heart beat interval, after which a message is sent on an idle connection to make sure it's still alive.
     * @return the interval.
     */
    public int getHeartbeatIntervalSeconds() {
        return heartbeatIntervalSeconds;
    }

    /**
     * Sets the heart beat interval, after which a message is sent on an idle connection to make sure it's still alive.
     * <p>
     * This is an application-level keep-alive, provided for convenience since adjusting the TCP keep-alive might not be
     * practical in all environments.
     * <p>
     * This option should be set higher than {@link SocketOptions#getReadTimeoutMillis()}.
     * <p>
     * The default value for this option is 30 seconds.
     *
     * @param heartbeatIntervalSeconds the new value in seconds. If set to 0, it will disable the feature.
     * @return this {@code PoolingOptions}
     *
     * @throws IllegalArgumentException if the interval is negative.
     */
    public PoolingOptions setHeartbeatIntervalSeconds(int heartbeatIntervalSeconds) {
        if (heartbeatIntervalSeconds < 0)
            throw new IllegalArgumentException("Heartbeat interval must be positive");

        this.heartbeatIntervalSeconds = heartbeatIntervalSeconds;
        return this;
    }

    /**
     * Returns the maximum number of requests per host.
     * <p>
     * This option is only used with {@code ProtocolVersion#V3} or above.
     * <p>
     * The default value for this option is 1024 for {@code LOCAL} and 256 for
     * {@code REMOTE} hosts.
     *
     * @param distance the {@code HostDistance} for which to return this threshold.
     * @return the maximum number of requests per host at distance {@code distance}.
     */
    public int getMaxSimultaneousRequestsPerHostThreshold(HostDistance distance) {
        switch (distance) {
            case LOCAL:
                return maxSimultaneousRequestsPerHostLocal;
            case REMOTE:
                return maxSimultaneousRequestsPerHostRemote;
            default:
                return 0;
        }
    }

    /**
     * Sets the maximum number of requests per host.
     * <p>
     * This option is only used with {@code ProtocolVersion#V3} or above.
     *
     * @param distance the {@code HostDistance} for which to set this threshold.
     * @param newMaxRequests the value to set (between 1 and 32768).
     * @return this {@code PoolingOptions}.
     *
     * @throws IllegalArgumentException if {@code distance == HostDistance.IGNORED},
     * or if {@code newMaxConnections} is not within the allowed range.
     */
    public PoolingOptions setMaxSimultaneousRequestsPerHostThreshold(HostDistance distance, int newMaxRequests) {
        if (newMaxRequests <= 0 || newMaxRequests > StreamIdGenerator.MAX_STREAM_PER_CONNECTION_V3)
            throw new IllegalArgumentException(String.format("Max requests must be in the range (1, %d)",
                                               StreamIdGenerator.MAX_STREAM_PER_CONNECTION_V3));

        switch (distance) {
            case LOCAL:
                maxSimultaneousRequestsPerHostLocal = newMaxRequests;
                break;
            case REMOTE:
                maxSimultaneousRequestsPerHostRemote = newMaxRequests;
                break;
            default:
                throw new IllegalArgumentException("Cannot set max requests per host for " + distance + " hosts");
        }
        return this;
    }

    /**
     * Returns the executor to use for connection initialization.
     *
     * @return the executor.
     * @see #setInitializationExecutor(java.util.concurrent.Executor)
     */
    public Executor getInitializationExecutor() {
        return initializationExecutor;
    }

    /**
     * Sets the executor to use for connection initialization.
     * <p>
     * Connections are open in a completely asynchronous manner. Since initializing the transport
     * requires separate CQL queries, the futures representing the completion of these queries are
     * transformed and chained. This executor is where these transformations happen.
     * <p>
     * <b>This is an advanced option, which should be rarely needed in practice.</b> It defaults to
     * Guava's {@code MoreExecutors.sameThreadExecutor()}, which results in running the transformations
     * on the network I/O threads; this is fine if the transformations are fast and not I/O bound
     * (which is the case by default).
     * One reason why you might want to provide a custom executor is if you use authentication with
     * a custom {@link com.datastax.driver.core.Authenticator} implementation that performs blocking
     * calls.
     *
     * @param initializationExecutor the executor to use
     * @return this {@code PoolingOptions}
     *
     * @throws java.lang.NullPointerException if the executor is null
     */
    public PoolingOptions setInitializationExecutor(Executor initializationExecutor) {
        Preconditions.checkNotNull(initializationExecutor);
        this.initializationExecutor = initializationExecutor;
        return this;
    }

    /**
     * Requests the driver to re-evaluate the {@link HostDistance} (through the configured
     * {@link com.datastax.driver.core.policies.LoadBalancingPolicy#distance}) for every known
     * hosts and to drop/add connections to each hosts according to the computed distance.
     */
    public void refreshConnectedHosts() {
        manager.refreshConnectedHosts();
    }

    /**
     * Requests the driver to re-evaluate the {@link HostDistance} for a given node.
     *
     * @param host the host to refresh.
     *
     * @see #refreshConnectedHosts()
     */
    public void refreshConnectedHost(Host host) {
        manager.refreshConnectedHost(host);
    }

    private static void checkRequestsPerConnectionRange(int value, String description, HostDistance distance) {
        if (value < 0 || value > StreamIdGenerator.MAX_STREAM_PER_CONNECTION_V2)
            throw new IllegalArgumentException(String.format("%s for %s hosts must be in the range (0, %d)",
                                                             description, distance,
                                                             StreamIdGenerator.MAX_STREAM_PER_CONNECTION_V2));
    }

    private static void checkConnectionsPerHostOrder(int core, int max, HostDistance distance) {
        if (core > max)
            throw new IllegalArgumentException(String.format("Core connections for %s hosts must be less than max (%d > %d)",
                                                             distance, core, max));
    }
}


File: driver-core/src/main/java/com/datastax/driver/core/SingleConnectionPool.java
/*
 *      Copyright (C) 2012-2015 DataStax Inc.
 *
 *   Licensed under the Apache License, Version 2.0 (the "License");
 *   you may not use this file except in compliance with the License.
 *   You may obtain a copy of the License at
 *
 *      http://www.apache.org/licenses/LICENSE-2.0
 *
 *   Unless required by applicable law or agreed to in writing, software
 *   distributed under the License is distributed on an "AS IS" BASIS,
 *   WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 *   See the License for the specific language governing permissions and
 *   limitations under the License.
 */
package com.datastax.driver.core;


import java.util.ArrayList;
import java.util.List;
import java.util.Set;
import java.util.concurrent.CopyOnWriteArraySet;
import java.util.concurrent.Executor;
import java.util.concurrent.TimeUnit;
import java.util.concurrent.TimeoutException;
import java.util.concurrent.atomic.AtomicBoolean;
import java.util.concurrent.atomic.AtomicReference;
import java.util.concurrent.locks.Condition;
import java.util.concurrent.locks.Lock;
import java.util.concurrent.locks.ReentrantLock;

import com.google.common.util.concurrent.*;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import com.datastax.driver.core.exceptions.AuthenticationException;
import com.datastax.driver.core.utils.MoreFutures;

import static com.datastax.driver.core.Connection.State.GONE;
import static com.datastax.driver.core.Connection.State.OPEN;
import static com.datastax.driver.core.Connection.State.TRASHED;

/**
 * A connection pool with a a single connection.
 *
 * This is used with {@link ProtocolVersion#V3} and higher.
 */
class SingleConnectionPool extends HostConnectionPool {

    private static final Logger logger = LoggerFactory.getLogger(SingleConnectionPool.class);

    // When a request timeout, we may never release its stream ID. So over time, a given connection
    // may get less an less available streams. When the number of available ones go below the
    // following threshold, we just replace the connection by a new one.
    private static final int MIN_AVAILABLE_STREAMS = 32768 * 3 / 4;

    volatile AtomicReference<Connection> connectionRef = new AtomicReference<Connection>();
    private final AtomicBoolean open = new AtomicBoolean();
    private final Set<Connection> trash = new CopyOnWriteArraySet<Connection>();

    private volatile int waiter = 0;
    private final Lock waitLock = new ReentrantLock(true);
    private final Condition hasAvailableConnection = waitLock.newCondition();

    private final Runnable newConnectionTask;

    private final AtomicBoolean scheduledForCreation = new AtomicBoolean();

    public SingleConnectionPool(Host host, HostDistance hostDistance, SessionManager manager) {
        super(host, hostDistance, manager);

        this.newConnectionTask = new Runnable() {
            @Override
            public void run() {
                addConnectionIfNeeded();
                scheduledForCreation.set(false);
            }
        };
    }

    @Override
    ListenableFuture<Void> initAsync(Connection reusedConnection) {
        final Connection connection;
        ListenableFuture<Void> connectionFuture;
        if (reusedConnection != null && reusedConnection.setPool(this)) {
            connection = reusedConnection;
            connectionFuture = MoreFutures.VOID_SUCCESS;
        } else {
            connection = manager.connectionFactory().newConnection(this);
            connectionFuture = connection.initAsync();
        }

        Executor initExecutor = manager.cluster.manager.configuration.getPoolingOptions().getInitializationExecutor();

        final SettableFuture<Void> initFuture = SettableFuture.create();
        Futures.addCallback(connectionFuture, new FutureCallback<Void>() {
            @Override
            public void onSuccess(Void result) {
                connectionRef.set(connection);
                open.set(true);
                if (isClosed()) {
                    initFuture.setException(new ConnectionException(host.getSocketAddress(), "Pool was closed during initialization"));
                    // we're not sure if closeAsync() saw the connection, so ensure it gets closed
                    connection.closeAsync().force();
                } else {
                    logger.trace("Created connection pool to host {}", host);
                    phase.compareAndSet(Phase.INITIALIZING, Phase.READY);
                    initFuture.set(null);
                }
            }

            @Override
            public void onFailure(Throwable t) {
                phase.compareAndSet(Phase.INITIALIZING, Phase.INIT_FAILED);
                initFuture.setException(t);
            }
        }, initExecutor);

        return initFuture;
    }

    private PoolingOptions options() {
        return manager.configuration().getPoolingOptions();
    }

    @Override
    public Connection borrowConnection(long timeout, TimeUnit unit) throws ConnectionException, TimeoutException {
        Phase phase = this.phase.get();
        if (phase != Phase.READY)
            // Note: throwing a ConnectionException is probably fine in practice as it will trigger the creation of a new host.
            // That being said, maybe having a specific exception could be cleaner.
            throw new ConnectionException(host.getSocketAddress(), "Pool is " + phase);

        Connection connection = connectionRef.get();
        if (connection == null) {
            if (scheduledForCreation.compareAndSet(false, true))
                manager.blockingExecutor().submit(newConnectionTask);
            connection = waitForConnection(timeout, unit);
        } else {
            while (true) {
                int inFlight = connection.inFlight.get();

                if (inFlight >= Math.min(connection.maxAvailableStreams(),
                                         options().getMaxSimultaneousRequestsPerHostThreshold(hostDistance))) {
                    connection = waitForConnection(timeout, unit);
                    break;
                }

                if (connection.inFlight.compareAndSet(inFlight, inFlight + 1))
                    break;
            }
        }
        connection.setKeyspace(manager.poolsState.keyspace);
        return connection;
    }

    private void awaitAvailableConnection(long timeout, TimeUnit unit) throws InterruptedException {
        waitLock.lock();
        waiter++;
        try {
            hasAvailableConnection.await(timeout, unit);
        } finally {
            waiter--;
            waitLock.unlock();
        }
    }

    private void signalAvailableConnection() {
        // Quick check if it's worth signaling to avoid locking
        if (waiter == 0)
            return;

        waitLock.lock();
        try {
            hasAvailableConnection.signal();
        } finally {
            waitLock.unlock();
        }
    }

    private void signalAllAvailableConnection() {
        // Quick check if it's worth signaling to avoid locking
        if (waiter == 0)
            return;

        waitLock.lock();
        try {
            hasAvailableConnection.signalAll();
        } finally {
            waitLock.unlock();
        }
    }

    private Connection waitForConnection(long timeout, TimeUnit unit) throws ConnectionException, TimeoutException {
        if (timeout == 0)
            throw new TimeoutException();

        long start = System.nanoTime();
        long remaining = timeout;
        do {
            try {
                awaitAvailableConnection(remaining, unit);
            } catch (InterruptedException e) {
                Thread.currentThread().interrupt();
                // If we're interrupted fine, check if there is a connection available but stop waiting otherwise
                timeout = 0; // this will make us stop the loop if we don't get a connection right away
            }

            if (isClosed())
                throw new ConnectionException(host.getSocketAddress(), "Pool is shutdown");

            Connection connection = connectionRef.get();
            // If we race with shutdown, connection could be null. In that case we just loop and we'll throw on the next
            // iteration anyway
            if (connection != null) {
                while (true) {
                    int inFlight = connection.inFlight.get();

                    if (inFlight >= Math.min(connection.maxAvailableStreams(),
                                             options().getMaxSimultaneousRequestsPerHostThreshold(hostDistance)))
                        break;

                    if (connection.inFlight.compareAndSet(inFlight, inFlight + 1))
                        return connection;
                }
            }

            remaining = timeout - Cluster.timeSince(start, unit);
        } while (remaining > 0);

        throw new TimeoutException();
    }

    @Override
    public void returnConnection(Connection connection) {
        int inFlight = connection.inFlight.decrementAndGet();

        if (isClosed()) {
            close(connection);
            return;
        }

        if (connection.isDefunct()) {
            // As part of making it defunct, we have already replaced it or
            // closed the pool.
            return;
        }

        if (trash.contains(connection)) {
            if (inFlight == 0 && trash.remove(connection))
                close(connection);
        } else {
            if (connection.maxAvailableStreams() < MIN_AVAILABLE_STREAMS) {
                replaceConnection(connection);
            } else {
                signalAvailableConnection();
            }
        }
    }

    // Trash the connection and create a new one, but we don't call trashConnection
    // directly because we want to make sure the connection is always trashed.
    private void replaceConnection(Connection connection) {
        if (!connection.state.compareAndSet(OPEN, TRASHED))
            return;
        open.set(false);
        maybeSpawnNewConnection();
        doTrashConnection(connection);
    }

    private void doTrashConnection(Connection connection) {
        connectionRef.compareAndSet(connection, null);
        trash.add(connection);

        if (connection.inFlight.get() == 0 && trash.remove(connection))
            close(connection);
    }

    private boolean addConnectionIfNeeded() {
        if (!open.compareAndSet(false, true))
            return false;

        if (phase.get() != Phase.READY) {
            open.set(false);
            return false;
        }

        // Now really open the connection
        try {
            logger.debug("Creating new connection on busy pool to {}", host);
            Connection newConnection = manager.connectionFactory().open(this);
            connectionRef.set(newConnection);

            // We might have raced with pool shutdown since the last check; ensure the connection gets closed in case the pool did not do it.
            if (isClosed() && !newConnection.isClosed()) {
                close(newConnection);
                this.open.set(false);
                return false;
            }

            signalAvailableConnection();
            return true;
        } catch (InterruptedException e) {
            Thread.currentThread().interrupt();
            // Skip the open but ignore otherwise
            open.set(false);
            return false;
        } catch (ConnectionException e) {
            open.set(false);
            logger.debug("Connection error to {} while creating additional connection", host);
            return false;
        } catch (AuthenticationException e) {
            // This shouldn't really happen in theory
            open.set(false);
            logger.error("Authentication error while creating additional connection (error is: {})", e.getMessage());
            return false;
        } catch (UnsupportedProtocolVersionException e) {
            // This shouldn't happen since we shouldn't have been able to connect in the first place
            open.set(false);
            logger.error("UnsupportedProtocolVersionException error while creating additional connection (error is: {})", e.getMessage());
            return false;
        } catch (ClusterNameMismatchException e) {
            open.set(false);
            logger.error("ClusterNameMismatchException error while creating additional connection (error is: {})", e.getMessage());
            return false;
        }
    }

    private void maybeSpawnNewConnection() {
        if (!scheduledForCreation.compareAndSet(false, true))
            return;

        manager.blockingExecutor().submit(newConnectionTask);
    }

    @Override
    public void replaceDefunctConnection(final Connection connection) {
        if (connection.state.compareAndSet(OPEN, GONE))
            open.set(false);
        if (connectionRef.compareAndSet(connection, null))
            manager.blockingExecutor().submit(new Runnable() {
                @Override
                public void run() {
                    addConnectionIfNeeded();
                }
            });
    }

    @Override
    void cleanupIdleConnections(long now) {
    }

    private void close(final Connection connection) {
        connection.closeAsync();
    }

    protected CloseFuture makeCloseFuture() {
        // Wake up all threads that wait
        signalAllAvailableConnection();

        return new CloseFuture.Forwarding(discardConnection());
    }

    private List<CloseFuture> discardConnection() {

        List<CloseFuture> futures = new ArrayList<CloseFuture>();

        final Connection connection = connectionRef.get();
        if (connection != null) {
            CloseFuture future = connection.closeAsync();
            future.addListener(new Runnable() {
                public void run() {
                    if (connection.state.compareAndSet(OPEN, GONE))
                        open.set(false);
                }
            }, MoreExecutors.sameThreadExecutor());
            futures.add(future);
        }
        return futures;
    }

    @Override
    public void ensureCoreConnections() {
        if (isClosed())
            return;

        if (!open.get() && scheduledForCreation.compareAndSet(false, true)) {
            manager.blockingExecutor().submit(newConnectionTask);
        }
    }

    @Override
    public int opened() {
        return open.get() ? 1 : 0;
    }

    @Override
    int trashed() {
        return trash.size();
    }

    @Override
    public int inFlightQueriesCount() {
        Connection connection = connectionRef.get();
        return connection == null ? 0 : connection.inFlight.get();
    }
}


File: driver-core/src/test/java/com/datastax/driver/core/SingleConnectionPoolTest.java
/*
 *      Copyright (C) 2012-2015 DataStax Inc.
 *
 *   Licensed under the Apache License, Version 2.0 (the "License");
 *   you may not use this file except in compliance with the License.
 *   You may obtain a copy of the License at
 *
 *      http://www.apache.org/licenses/LICENSE-2.0
 *
 *   Unless required by applicable law or agreed to in writing, software
 *   distributed under the License is distributed on an "AS IS" BASIS,
 *   WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 *   See the License for the specific language governing permissions and
 *   limitations under the License.
 */
package com.datastax.driver.core;

import java.net.InetSocketAddress;
import java.util.Collection;
import java.util.concurrent.Executors;
import java.util.concurrent.ScheduledExecutorService;
import java.util.concurrent.TimeUnit;
import java.util.concurrent.atomic.AtomicBoolean;

import org.testng.annotations.Test;
import org.testng.collections.Lists;

import static org.testng.Assert.fail;

import com.datastax.driver.core.utils.CassandraVersion;

@CassandraVersion(major=2.1)
public class SingleConnectionPoolTest extends CCMBridge.PerClassSingleNodeCluster {
    @Override
    protected Collection<String> getTableDefinitions() {
        return Lists.newArrayList();
    }

    @Test(groups = "short")
    public void should_throttle_requests() {
        // Throttle to a very low value. Even a single thread can generate a higher throughput.
        final int maxRequests = 10;
        cluster.getConfiguration().getPoolingOptions()
               .setMaxSimultaneousRequestsPerHostThreshold(HostDistance.LOCAL, maxRequests);

        // Track in flight requests in a dedicated thread every second
        final AtomicBoolean excessInflightQueriesSpotted = new AtomicBoolean(false);
        final Host host = cluster.getMetadata().getHost(new InetSocketAddress(CCMBridge.IP_PREFIX + "1", 9042));
        ScheduledExecutorService openConnectionsWatcherExecutor = Executors.newScheduledThreadPool(1);
        final Runnable openConnectionsWatcher = new Runnable() {
            @Override
            public void run() {
                int inFlight = session.getState().getInFlightQueries(host);
                if (inFlight > maxRequests)
                    excessInflightQueriesSpotted.set(true);
            }
        };
        openConnectionsWatcherExecutor.scheduleAtFixedRate(openConnectionsWatcher, 200, 200, TimeUnit.MILLISECONDS);

        // Generate the load
        for (int i = 0; i < 10000; i++)
            session.executeAsync("SELECT release_version FROM system.local");

        openConnectionsWatcherExecutor.shutdownNow();
        if (excessInflightQueriesSpotted.get()) {
            fail("Inflight queries exceeded the limit");
        }
    }
}


File: driver-examples/stress/src/main/java/com/datastax/driver/stress/Stress.java
/*
 *      Copyright (C) 2012-2015 DataStax Inc.
 *
 *   Licensed under the Apache License, Version 2.0 (the "License");
 *   you may not use this file except in compliance with the License.
 *   You may obtain a copy of the License at
 *
 *      http://www.apache.org/licenses/LICENSE-2.0
 *
 *   Unless required by applicable law or agreed to in writing, software
 *   distributed under the License is distributed on an "AS IS" BASIS,
 *   WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 *   See the License for the specific language governing permissions and
 *   limitations under the License.
 */
package com.datastax.driver.stress;

import java.io.IOException;
import java.util.*;

import com.datastax.driver.core.*;
import com.datastax.driver.core.exceptions.*;

import org.apache.log4j.PropertyConfigurator;

import joptsimple.*;

/**
 * A simple stress tool to demonstrate the use of the driver.
 *
 * Sample usage:
 *   stress insert -n 100000
 *   stress read -n 10000
 */
public class Stress {

    private static final Map<String, QueryGenerator.Builder> generators = new HashMap<String, QueryGenerator.Builder>();
    static {
        PropertyConfigurator.configure(System.getProperty("log4j.configuration", "./conf/log4j.properties"));

        QueryGenerator.Builder[] gs = new QueryGenerator.Builder[] {
            Generators.INSERTER,
            Generators.READER
        };

        for (QueryGenerator.Builder b : gs)
            register(b.name(), b);
    }

    private static OptionParser defaultParser() {
        OptionParser parser = new OptionParser() {{
            accepts("h", "Show this help message");
            accepts("n", "Number of requests to perform (default: unlimited)").withRequiredArg().ofType(Integer.class);
            accepts("t", "Level of concurrency to use").withRequiredArg().ofType(Integer.class).defaultsTo(50);
            accepts("async", "Make asynchronous requests instead of blocking ones");
            accepts("ip", "The hosts ip to connect to").withRequiredArg().ofType(String.class).defaultsTo("127.0.0.1");
            accepts("report-file", "The name of csv file to use for reporting results").withRequiredArg().ofType(String.class).defaultsTo("last.csv");
            accepts("print-delay", "The delay in seconds at which to report on the console").withRequiredArg().ofType(Integer.class).defaultsTo(5);
            accepts("compression", "Use compression (SNAPPY)");
            accepts("connections-per-host", "The number of connections per hosts (default: based on the number of threads)").withRequiredArg().ofType(Integer.class);
        }};
        String msg = "Where <generator> can be one of " + generators.keySet() + '\n'
                   + "You can get more help on a particular generator with: stress <generator> -h";
        parser.formatHelpWith(Help.formatFor("<generator>", msg));
        return parser;
    }

    public static void register(String name, QueryGenerator.Builder generator) {
        if (generators.containsKey(name))
            throw new IllegalStateException("There is already a generator registered with the name " + name);

        generators.put(name, generator);
    }

    private static class Stresser {
        private final QueryGenerator.Builder genBuilder;
        private final OptionParser parser;
        private final OptionSet options;

        private Stresser(QueryGenerator.Builder genBuilder, OptionParser parser, OptionSet options) {
            this.genBuilder = genBuilder;
            this.parser = parser;
            this.options = options;
        }

        public static Stresser forCommandLineArguments(String[] args) {
            OptionParser parser = defaultParser();

            String generatorName = findPotentialGenerator(args);
            if (generatorName == null) {
                // Still parse the options to handle -h
                OptionSet options = parseOptions(parser, args);
                System.err.println("Missing generator, you need to provide a generator.");
                printHelp(parser);
                System.exit(1);
            }

            if (!generators.containsKey(generatorName)) {
                System.err.println(String.format("Unknown generator '%s'", generatorName));
                printHelp(parser);
                System.exit(1);
            }

            QueryGenerator.Builder genBuilder = generators.get(generatorName);
            parser = genBuilder.addOptions(parser);
            OptionSet options = parseOptions(parser, args);

            List<?> nonOpts = options.nonOptionArguments();
            if (nonOpts.size() > 1) {
                System.err.println("Too many generators provided. Got " + nonOpts + " but only one generator supported.");
                printHelp(parser);
                System.exit(1);
            }

            return new Stresser(genBuilder, parser, options);
        }

        private static String findPotentialGenerator(String[] args) {
            for (String arg : args)
                if (!arg.startsWith("-"))
                    return arg;

            return null;
        }

        private static OptionSet parseOptions(OptionParser parser, String[] args) {
            try {
                OptionSet options = parser.parse(args);
                if (options.has("h")) {
                    printHelp(parser);
                    System.exit(0);
                }
                return options;
            } catch (Exception e) {
                System.err.println("Error parsing options: " + e.getMessage());
                printHelp(parser);
                System.exit(1);
                throw new AssertionError();
            }
        }

        private static void printHelp(OptionParser parser) {
            try {
                parser.printHelpOn(System.out);
            } catch (IOException e) {
                throw new AssertionError(e);
            }
        }

        public OptionSet getOptions() {
            return options;
        }

        public void prepare(Session session) {
            genBuilder.prepare(options, session);
        }

        public QueryGenerator newGenerator(int id, Session session, int iterations) {
            return genBuilder.create(id, iterations, options, session);
        }
    }

    public static class Help implements HelpFormatter {

        private final HelpFormatter defaultFormatter;
        private final String generator;
        private final String header;

        private Help(HelpFormatter defaultFormatter, String generator, String header) {
            this.defaultFormatter = defaultFormatter;
            this.generator = generator;
            this.header = header;
        }

        public static Help formatFor(String generator, String header) {
            // It's a pain in the ass to get the real console width in JAVA so hardcode it. But it's the 21th
            // century, we're not stuck at 80 characters anymore.
            int width = 120; 
            return new Help(new BuiltinHelpFormatter(width, 4), generator, header);
        }

        @Override
        public String format(Map<String, ? extends OptionDescriptor> options) {
            StringBuilder sb = new StringBuilder();

            sb.append("Usage: stress ").append(generator).append(" [<option>]*").append("\n\n");
            sb.append(header).append("\n\n");
            sb.append(defaultFormatter.format(options));
            return sb.toString();
        }
    }

    public static void main(String[] args) throws Exception {

        Stresser stresser = Stresser.forCommandLineArguments(args);
        OptionSet options = stresser.getOptions();

        int requests = options.has("n") ? (Integer)options.valueOf("n") : -1;
        int concurrency = (Integer)options.valueOf("t");

        String reportFileName = (String)options.valueOf("report-file");

        boolean async = options.has("async");

        int iterations = (requests  == -1 ? -1 : requests / concurrency);

        final int maxRequestsPerConnection = 128;
        int maxConnections = options.has("connections-per-host")
                           ? (Integer)options.valueOf("connections-per-host")
                           : concurrency / maxRequestsPerConnection + 1;

        PoolingOptions pools = new PoolingOptions();
        pools.setMaxSimultaneousRequestsPerConnectionThreshold(HostDistance.LOCAL, concurrency);
        pools.setCoreConnectionsPerHost(HostDistance.LOCAL, maxConnections);
        pools.setMaxConnectionsPerHost(HostDistance.LOCAL, maxConnections);
        pools.setCoreConnectionsPerHost(HostDistance.REMOTE, maxConnections);
        pools.setMaxConnectionsPerHost(HostDistance.REMOTE, maxConnections);

        System.out.println("Initializing stress test:");
        System.out.println("  request count:        " + (requests == -1 ? "unlimited" : requests));
        System.out.println("  concurrency:          " + concurrency + " (" + iterations + " requests/thread)");
        System.out.println("  mode:                 " + (async ? "asynchronous" : "blocking"));
        System.out.println("  per-host connections: " + maxConnections);
        System.out.println("  compression:          " + options.has("compression"));

        try {
            // Create session to hosts
            Cluster cluster = new Cluster.Builder()
                                         .addContactPoints(String.valueOf(options.valueOf("ip")))
                                         .withPoolingOptions(pools)
                                         .withSocketOptions(new SocketOptions().setTcpNoDelay(true))
                                         .build();

            if (options.has("compression"))
                cluster.getConfiguration().getProtocolOptions().setCompression(ProtocolOptions.Compression.SNAPPY);

            Session session = cluster.connect();

            Metadata metadata = cluster.getMetadata();
            System.out.println(String.format("Connected to cluster '%s' on %s.", metadata.getClusterName(), metadata.getAllHosts()));

            System.out.println("Preparing test...");
            stresser.prepare(session);

            Reporter reporter = new Reporter((Integer)options.valueOf("print-delay"), reportFileName, args, requests);

            Consumer[] consumers = new Consumer[concurrency];
            for (int i = 0; i < concurrency; i++) {
                QueryGenerator generator = stresser.newGenerator(i, session, iterations);
                consumers[i] = async ? new AsynchronousConsumer(session, generator, reporter) :
                                       new BlockingConsumer(session, generator, reporter);
            }

            System.out.println("Starting to stress test...");
            System.out.println();

            reporter.start();

            for (Consumer consumer : consumers)
                consumer.start();

            for (Consumer consumer : consumers)
                consumer.join();

            reporter.stop();

            System.out.println("Stress test successful.");
            System.exit(0);

        } catch (NoHostAvailableException e) {
            System.err.println("No alive hosts to use: " + e.getMessage());
            System.exit(1);
        } catch (Exception e) {
            System.err.println("Unexpected error: " + e.getMessage());
            e.printStackTrace();
            System.exit(1);
        }
    }
}
