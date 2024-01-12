Refactoring Types: ['Extract Method']
concurrent/AbstractTracingAwareExecutorService.java
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
package org.apache.cassandra.concurrent;

import java.util.Collection;
import java.util.List;
import java.util.concurrent.Callable;
import java.util.concurrent.ExecutionException;
import java.util.concurrent.Executors;
import java.util.concurrent.Future;
import java.util.concurrent.TimeUnit;
import java.util.concurrent.TimeoutException;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import org.apache.cassandra.tracing.TraceState;
import org.apache.cassandra.tracing.Tracing;
import org.apache.cassandra.utils.concurrent.SimpleCondition;
import org.apache.cassandra.utils.JVMStabilityInspector;

import static org.apache.cassandra.tracing.Tracing.isTracing;

public abstract class AbstractTracingAwareExecutorService implements TracingAwareExecutorService
{
    private static final Logger logger = LoggerFactory.getLogger(AbstractTracingAwareExecutorService.class);

    protected abstract void addTask(FutureTask<?> futureTask);
    protected abstract void onCompletion();

    /** Task Submission / Creation / Objects **/

    public <T> FutureTask<T> submit(Callable<T> task)
    {
        return submit(newTaskFor(task));
    }

    public FutureTask<?> submit(Runnable task)
    {
        return submit(newTaskFor(task, null));
    }

    public <T> FutureTask<T> submit(Runnable task, T result)
    {
        return submit(newTaskFor(task, result));
    }

    public <T> List<Future<T>> invokeAll(Collection<? extends Callable<T>> tasks)
    {
        throw new UnsupportedOperationException();
    }

    public <T> List<Future<T>> invokeAll(Collection<? extends Callable<T>> tasks, long timeout, TimeUnit unit) throws InterruptedException
    {
        throw new UnsupportedOperationException();
    }

    public <T> T invokeAny(Collection<? extends Callable<T>> tasks) throws InterruptedException, ExecutionException
    {
        throw new UnsupportedOperationException();
    }

    public <T> T invokeAny(Collection<? extends Callable<T>> tasks, long timeout, TimeUnit unit) throws InterruptedException, ExecutionException, TimeoutException
    {
        throw new UnsupportedOperationException();
    }

    protected <T> FutureTask<T> newTaskFor(Runnable runnable, T result)
    {
        return newTaskFor(runnable, result, Tracing.instance.get());
    }

    protected <T> FutureTask<T> newTaskFor(Runnable runnable, T result, TraceState traceState)
    {
        if (traceState != null)
        {
            if (runnable instanceof TraceSessionFutureTask)
                return (TraceSessionFutureTask<T>) runnable;
            return new TraceSessionFutureTask<T>(runnable, result, traceState);
        }
        if (runnable instanceof FutureTask)
            return (FutureTask<T>) runnable;
        return new FutureTask<>(runnable, result);
    }

    protected <T> FutureTask<T> newTaskFor(Callable<T> callable)
    {
        if (isTracing())
        {
            if (callable instanceof TraceSessionFutureTask)
                return (TraceSessionFutureTask<T>) callable;
            return new TraceSessionFutureTask<T>(callable, Tracing.instance.get());
        }
        if (callable instanceof FutureTask)
            return (FutureTask<T>) callable;
        return new FutureTask<>(callable);
    }

    private class TraceSessionFutureTask<T> extends FutureTask<T>
    {
        private final TraceState state;

        public TraceSessionFutureTask(Callable<T> callable, TraceState state)
        {
            super(callable);
            this.state = state;
        }

        public TraceSessionFutureTask(Runnable runnable, T result, TraceState state)
        {
            super(runnable, result);
            this.state = state;
        }

        public void run()
        {
            TraceState oldState = Tracing.instance.get();
            Tracing.instance.set(state);
            try
            {
                super.run();
            }
            finally
            {
                Tracing.instance.set(oldState);
            }
        }
    }

    class FutureTask<T> extends SimpleCondition implements Future<T>, Runnable
    {
        private boolean failure;
        private Object result = this;
        private final Callable<T> callable;

        public FutureTask(Callable<T> callable)
        {
            this.callable = callable;
        }
        public FutureTask(Runnable runnable, T result)
        {
            this(Executors.callable(runnable, result));
        }

        public void run()
        {
            try
            {
                result = callable.call();
            }
            catch (Throwable t)
            {
                JVMStabilityInspector.inspectThrowable(t);
                logger.warn("Uncaught exception on thread {}: {}", Thread.currentThread(), t);
                result = t;
                failure = true;
            }
            finally
            {
                signalAll();
                onCompletion();
            }
        }

        public boolean cancel(boolean mayInterruptIfRunning)
        {
            return false;
        }

        public boolean isCancelled()
        {
            return false;
        }

        public boolean isDone()
        {
            return isSignaled();
        }

        public T get() throws InterruptedException, ExecutionException
        {
            await();
            Object result = this.result;
            if (failure)
                throw new ExecutionException((Throwable) result);
            return (T) result;
        }

        public T get(long timeout, TimeUnit unit) throws InterruptedException, ExecutionException, TimeoutException
        {
            await(timeout, unit);
            Object result = this.result;
            if (failure)
                throw new ExecutionException((Throwable) result);
            return (T) result;
        }
    }

    private <T> FutureTask<T> submit(FutureTask<T> task)
    {
        addTask(task);
        return task;
    }

    public void execute(Runnable command)
    {
        addTask(newTaskFor(command, null));
    }

    public void execute(Runnable command, TraceState state)
    {
        addTask(newTaskFor(command, null, state));
    }
}


File: src/java/org/apache/cassandra/concurrent/NamedThreadFactory.java
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
package org.apache.cassandra.concurrent;

import java.util.concurrent.ThreadFactory;
import java.util.concurrent.atomic.AtomicInteger;

/**
 * This class is an implementation of the <i>ThreadFactory</i> interface. This
 * is useful to give Java threads meaningful names which is useful when using
 * a tool like JConsole.
 */

public class NamedThreadFactory implements ThreadFactory
{
    protected final String id;
    private final int priority;
    protected final AtomicInteger n = new AtomicInteger(1);

    public NamedThreadFactory(String id)
    {
        this(id, Thread.NORM_PRIORITY);
    }

    public NamedThreadFactory(String id, int priority)
    {

        this.id = id;
        this.priority = priority;
    }

    public Thread newThread(Runnable runnable)
    {
        String name = id + ":" + n.getAndIncrement();
        Thread thread = new Thread(runnable, name);
        thread.setPriority(priority);
        thread.setDaemon(true);
        return thread;
    }
}


File: src/java/org/apache/cassandra/config/Config.java
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
package org.apache.cassandra.config;

import java.util.Set;
import java.util.concurrent.TimeUnit;

import com.google.common.collect.Sets;

import org.apache.cassandra.config.EncryptionOptions.ClientEncryptionOptions;
import org.apache.cassandra.config.EncryptionOptions.ServerEncryptionOptions;

/**
 * A class that contains configuration properties for the cassandra node it runs within.
 *
 * Properties declared as volatile can be mutated via JMX.
 */
public class Config
{
    /*
     * Prefix for Java properties for internal Cassandra configuration options
     */
    public static final String PROPERTY_PREFIX = "cassandra.";


    public String cluster_name = "Test Cluster";
    public String authenticator;
    public String authorizer;
    public String role_manager;
    public volatile int permissions_validity_in_ms = 2000;
    public int permissions_cache_max_entries = 1000;
    public volatile int permissions_update_interval_in_ms = -1;
    public volatile int roles_validity_in_ms = 2000;
    public int roles_cache_max_entries = 1000;
    public volatile int roles_update_interval_in_ms = -1;

    /* Hashing strategy Random or OPHF */
    public String partitioner;

    public Boolean auto_bootstrap = true;
    public volatile boolean hinted_handoff_enabled = true;
    public Set<String> hinted_handoff_disabled_datacenters = Sets.newConcurrentHashSet();
    public volatile Integer max_hint_window_in_ms = 3 * 3600 * 1000; // three hours

    public ParameterizedClass seed_provider;
    public DiskAccessMode disk_access_mode = DiskAccessMode.auto;

    public DiskFailurePolicy disk_failure_policy = DiskFailurePolicy.ignore;
    public CommitFailurePolicy commit_failure_policy = CommitFailurePolicy.stop;

    /* initial token in the ring */
    public String initial_token;
    public Integer num_tokens = 1;
    /** Triggers automatic allocation of tokens if set, using the replication strategy of the referenced keyspace */
    public String allocate_tokens_for_keyspace = null;

    public volatile Long request_timeout_in_ms = 10000L;

    public volatile Long read_request_timeout_in_ms = 5000L;

    public volatile Long range_request_timeout_in_ms = 10000L;

    public volatile Long write_request_timeout_in_ms = 2000L;

    public volatile Long counter_write_request_timeout_in_ms = 5000L;

    public volatile Long cas_contention_timeout_in_ms = 1000L;

    public volatile Long truncate_request_timeout_in_ms = 60000L;

    public Integer streaming_socket_timeout_in_ms = 0;

    public boolean cross_node_timeout = false;

    public volatile Double phi_convict_threshold = 8.0;

    public Integer concurrent_reads = 32;
    public Integer concurrent_writes = 32;
    public Integer concurrent_counter_writes = 32;

    @Deprecated
    public Integer concurrent_replicates = null;

    public Integer memtable_flush_writers = null;
    public Integer memtable_heap_space_in_mb;
    public Integer memtable_offheap_space_in_mb;
    public Float memtable_cleanup_threshold = null;

    public Integer storage_port = 7000;
    public Integer ssl_storage_port = 7001;
    public String listen_address;
    public String listen_interface;
    public Boolean listen_interface_prefer_ipv6 = false;
    public String broadcast_address;
    public String internode_authenticator;

    /* intentionally left set to true, despite being set to false in stock 2.2 cassandra.yaml
       we don't want to surprise Thrift users who have the setting blank in the yaml during 2.1->2.2 upgrade */
    public Boolean start_rpc = true;
    public String rpc_address;
    public String rpc_interface;
    public Boolean rpc_interface_prefer_ipv6 = false;
    public String broadcast_rpc_address;
    public Integer rpc_port = 9160;
    public Integer rpc_listen_backlog = 50;
    public String rpc_server_type = "sync";
    public Boolean rpc_keepalive = true;
    public Integer rpc_min_threads = 16;
    public Integer rpc_max_threads = Integer.MAX_VALUE;
    public Integer rpc_send_buff_size_in_bytes;
    public Integer rpc_recv_buff_size_in_bytes;
    public Integer internode_send_buff_size_in_bytes;
    public Integer internode_recv_buff_size_in_bytes;

    public Boolean start_native_transport = false;
    public Integer native_transport_port = 9042;
    public Integer native_transport_max_threads = 128;
    public Integer native_transport_max_frame_size_in_mb = 256;
    public volatile Long native_transport_max_concurrent_connections = -1L;
    public volatile Long native_transport_max_concurrent_connections_per_ip = -1L;

    @Deprecated
    public Integer thrift_max_message_length_in_mb = 16;

    public Integer thrift_framed_transport_size_in_mb = 15;
    public Boolean snapshot_before_compaction = false;
    public Boolean auto_snapshot = true;

    /* if the size of columns or super-columns are more than this, indexing will kick in */
    public Integer column_index_size_in_kb = 64;
    public volatile int batch_size_warn_threshold_in_kb = 5;
    public volatile int batch_size_fail_threshold_in_kb = 50;
    public Integer concurrent_compactors;
    public volatile Integer compaction_throughput_mb_per_sec = 16;
    public volatile Integer compaction_large_partition_warning_threshold_mb = 100;

    public Integer max_streaming_retries = 3;

    public volatile Integer stream_throughput_outbound_megabits_per_sec = 200;
    public volatile Integer inter_dc_stream_throughput_outbound_megabits_per_sec = 0;

    public String[] data_file_directories;

    public String saved_caches_directory;

    // Commit Log
    public String commitlog_directory;
    public Integer commitlog_total_space_in_mb;
    public CommitLogSync commitlog_sync;
    public Double commitlog_sync_batch_window_in_ms;
    public Integer commitlog_sync_period_in_ms;
    public int commitlog_segment_size_in_mb = 32;
    public ParameterizedClass commitlog_compression;
    public int commitlog_max_compression_buffers_in_pool = 3;
 
    @Deprecated
    public int commitlog_periodic_queue_size = -1;

    public String endpoint_snitch;
    public Boolean dynamic_snitch = true;
    public Integer dynamic_snitch_update_interval_in_ms = 100;
    public Integer dynamic_snitch_reset_interval_in_ms = 600000;
    public Double dynamic_snitch_badness_threshold = 0.1;

    public String request_scheduler;
    public RequestSchedulerId request_scheduler_id;
    public RequestSchedulerOptions request_scheduler_options;

    public ServerEncryptionOptions server_encryption_options = new ServerEncryptionOptions();
    public ClientEncryptionOptions client_encryption_options = new ClientEncryptionOptions();
    // this encOptions is for backward compatibility (a warning is logged by DatabaseDescriptor)
    public ServerEncryptionOptions encryption_options;

    public InternodeCompression internode_compression = InternodeCompression.none;

    @Deprecated
    public Integer index_interval = null;

    public int hinted_handoff_throttle_in_kb = 1024;
    public int batchlog_replay_throttle_in_kb = 1024;
    public int max_hints_delivery_threads = 1;
    public int sstable_preemptive_open_interval_in_mb = 50;

    public volatile boolean incremental_backups = false;
    public boolean trickle_fsync = false;
    public int trickle_fsync_interval_in_kb = 10240;

    public Long key_cache_size_in_mb = null;
    public volatile int key_cache_save_period = 14400;
    public volatile int key_cache_keys_to_save = Integer.MAX_VALUE;

    public String row_cache_class_name = "org.apache.cassandra.cache.OHCProvider";
    public long row_cache_size_in_mb = 0;
    public volatile int row_cache_save_period = 0;
    public volatile int row_cache_keys_to_save = Integer.MAX_VALUE;

    public Long counter_cache_size_in_mb = null;
    public volatile int counter_cache_save_period = 7200;
    public volatile int counter_cache_keys_to_save = Integer.MAX_VALUE;

    @Deprecated
    public String memory_allocator;

    private static boolean isClientMode = false;

    public Integer file_cache_size_in_mb = 512;

    public boolean buffer_pool_use_heap_if_exhausted = true;

    public boolean inter_dc_tcp_nodelay = true;

    public MemtableAllocationType memtable_allocation_type = MemtableAllocationType.heap_buffers;

    private static boolean outboundBindAny = false;

    public volatile int tombstone_warn_threshold = 1000;
    public volatile int tombstone_failure_threshold = 100000;

    public volatile Long index_summary_capacity_in_mb;
    public volatile int index_summary_resize_interval_in_minutes = 60;

    // TTL for different types of trace events.
    public int tracetype_query_ttl = (int) TimeUnit.DAYS.toSeconds(1);
    public int tracetype_repair_ttl = (int) TimeUnit.DAYS.toSeconds(7);

    /*
     * Strategy to use for coalescing messages in OutboundTcpConnection.
     * Can be fixed, movingaverage, timehorizon, disabled. Setting is case and leading/trailing
     * whitespace insensitive. You can also specify a subclass of CoalescingStrategies.CoalescingStrategy by name.
     */
    public String otc_coalescing_strategy = "TIMEHORIZON";

    /*
     * How many microseconds to wait for coalescing. For fixed strategy this is the amount of time after the first
     * messgae is received before it will be sent with any accompanying messages. For moving average this is the
     * maximum amount of time that will be waited as well as the interval at which messages must arrive on average
     * for coalescing to be enabled.
     */
    public static final int otc_coalescing_window_us_default = 200;
    public int otc_coalescing_window_us = otc_coalescing_window_us_default;

    public int windows_timer_interval = 0;

    public boolean enable_user_defined_functions = false;

    public static boolean getOutboundBindAny()
    {
        return outboundBindAny;
    }

    public static void setOutboundBindAny(boolean value)
    {
        outboundBindAny = value;
    }

    public static boolean isClientMode()
    {
        return isClientMode;
    }

    public static void setClientMode(boolean clientMode)
    {
        isClientMode = clientMode;
    }

    public static enum CommitLogSync
    {
        periodic,
        batch
    }
    public static enum InternodeCompression
    {
        all, none, dc
    }

    public static enum DiskAccessMode
    {
        auto,
        mmap,
        mmap_index_only,
        standard,
    }

    public static enum MemtableAllocationType
    {
        unslabbed_heap_buffers,
        heap_buffers,
        offheap_buffers,
        offheap_objects
    }

    public static enum DiskFailurePolicy
    {
        best_effort,
        stop,
        ignore,
        stop_paranoid,
        die
    }

    public static enum CommitFailurePolicy
    {
        stop,
        stop_commit,
        ignore,
        die,
    }

    public static enum RequestSchedulerId
    {
        keyspace
    }
}


File: src/java/org/apache/cassandra/config/DatabaseDescriptor.java
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
package org.apache.cassandra.config;

import java.io.File;
import java.io.IOException;
import java.net.*;
import java.util.*;

import com.google.common.annotations.VisibleForTesting;
import com.google.common.collect.ImmutableSet;
import com.google.common.primitives.Longs;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import org.apache.cassandra.auth.*;
import org.apache.cassandra.config.Config.CommitLogSync;
import org.apache.cassandra.config.Config.RequestSchedulerId;
import org.apache.cassandra.config.EncryptionOptions.ClientEncryptionOptions;
import org.apache.cassandra.config.EncryptionOptions.ServerEncryptionOptions;
import org.apache.cassandra.db.ColumnFamilyStore;
import org.apache.cassandra.db.SystemKeyspace;
import org.apache.cassandra.dht.IPartitioner;
import org.apache.cassandra.exceptions.ConfigurationException;
import org.apache.cassandra.io.FSWriteError;
import org.apache.cassandra.io.sstable.format.SSTableFormat;
import org.apache.cassandra.io.util.FileUtils;
import org.apache.cassandra.locator.*;
import org.apache.cassandra.net.MessagingService;
import org.apache.cassandra.scheduler.IRequestScheduler;
import org.apache.cassandra.scheduler.NoScheduler;
import org.apache.cassandra.service.CacheService;
import org.apache.cassandra.thrift.ThriftServer;
import org.apache.cassandra.utils.ByteBufferUtil;
import org.apache.cassandra.utils.FBUtilities;
import org.apache.cassandra.utils.memory.*;

public class DatabaseDescriptor
{
    private static final Logger logger = LoggerFactory.getLogger(DatabaseDescriptor.class);

    /**
     * Tokens are serialized in a Gossip VersionedValue String.  VV are restricted to 64KB
     * when we send them over the wire, which works out to about 1700 tokens.
     */
    private static final int MAX_NUM_TOKENS = 1536;

    private static IEndpointSnitch snitch;
    private static InetAddress listenAddress; // leave null so we can fall through to getLocalHost
    private static InetAddress broadcastAddress;
    private static InetAddress rpcAddress;
    private static InetAddress broadcastRpcAddress;
    private static SeedProvider seedProvider;
    private static IInternodeAuthenticator internodeAuthenticator;

    /* Hashing strategy Random or OPHF */
    private static IPartitioner partitioner;
    private static String paritionerName;

    private static Config.DiskAccessMode indexAccessMode;

    private static Config conf;

    private static SSTableFormat.Type sstable_format = SSTableFormat.Type.BIG;

    private static IAuthenticator authenticator = new AllowAllAuthenticator();
    private static IAuthorizer authorizer = new AllowAllAuthorizer();
    private static IRoleManager roleManager = new CassandraRoleManager();

    private static IRequestScheduler requestScheduler;
    private static RequestSchedulerId requestSchedulerId;
    private static RequestSchedulerOptions requestSchedulerOptions;

    private static long keyCacheSizeInMB;
    private static long counterCacheSizeInMB;
    private static long indexSummaryCapacityInMB;

    private static String localDC;
    private static Comparator<InetAddress> localComparator;

    public static void forceStaticInitialization() {}
    static
    {
        // In client mode, we use a default configuration. Note that the fields of this class will be
        // left unconfigured however (the partitioner or localDC will be null for instance) so this
        // should be used with care.
        try
        {
            if (Config.isClientMode())
            {
                conf = new Config();
            }
            else
            {
                applyConfig(loadConfig());
            }
        }
        catch (Exception e)
        {
            throw new ExceptionInInitializerError(e);
        }
    }

    @VisibleForTesting
    public static Config loadConfig() throws ConfigurationException
    {
        String loaderClass = System.getProperty("cassandra.config.loader");
        ConfigurationLoader loader = loaderClass == null
                                   ? new YamlConfigurationLoader()
                                   : FBUtilities.<ConfigurationLoader>construct(loaderClass, "configuration loading");
        return loader.loadConfig();
    }

    private static InetAddress getNetworkInterfaceAddress(String intf, String configName, boolean preferIPv6) throws ConfigurationException
    {
        try
        {
            NetworkInterface ni = NetworkInterface.getByName(intf);
            if (ni == null)
                throw new ConfigurationException("Configured " + configName + " \"" + intf + "\" could not be found", false);
            Enumeration<InetAddress> addrs = ni.getInetAddresses();
            if (!addrs.hasMoreElements())
                throw new ConfigurationException("Configured " + configName + " \"" + intf + "\" was found, but had no addresses", false);

            /*
             * Try to return the first address of the preferred type, otherwise return the first address
             */
            InetAddress retval = null;
            while (addrs.hasMoreElements())
            {
                InetAddress temp = addrs.nextElement();
                if (preferIPv6 && temp instanceof Inet6Address) return temp;
                if (!preferIPv6 && temp instanceof Inet4Address) return temp;
                if (retval == null) retval = temp;
            }
            return retval;
        }
        catch (SocketException e)
        {
            throw new ConfigurationException("Configured " + configName + " \"" + intf + "\" caused an exception", e);
        }
    }

    @VisibleForTesting
    static void applyAddressConfig(Config config) throws ConfigurationException
    {
        listenAddress = null;
        rpcAddress = null;
        broadcastAddress = null;
        broadcastRpcAddress = null;

        /* Local IP, hostname or interface to bind services to */
        if (config.listen_address != null && config.listen_interface != null)
        {
            throw new ConfigurationException("Set listen_address OR listen_interface, not both", false);
        }
        else if (config.listen_address != null)
        {
            try
            {
                listenAddress = InetAddress.getByName(config.listen_address);
            }
            catch (UnknownHostException e)
            {
                throw new ConfigurationException("Unknown listen_address '" + config.listen_address + "'", false);
            }

            if (listenAddress.isAnyLocalAddress())
                throw new ConfigurationException("listen_address cannot be a wildcard address (" + config.listen_address + ")!", false);
        }
        else if (config.listen_interface != null)
        {
            listenAddress = getNetworkInterfaceAddress(config.listen_interface, "listen_interface", config.listen_interface_prefer_ipv6);
        }

        /* Gossip Address to broadcast */
        if (config.broadcast_address != null)
        {
            try
            {
                broadcastAddress = InetAddress.getByName(config.broadcast_address);
            }
            catch (UnknownHostException e)
            {
                throw new ConfigurationException("Unknown broadcast_address '" + config.broadcast_address + "'", false);
            }

            if (broadcastAddress.isAnyLocalAddress())
                throw new ConfigurationException("broadcast_address cannot be a wildcard address (" + config.broadcast_address + ")!", false);
        }

        /* Local IP, hostname or interface to bind RPC server to */
        if (config.rpc_address != null && config.rpc_interface != null)
        {
            throw new ConfigurationException("Set rpc_address OR rpc_interface, not both", false);
        }
        else if (config.rpc_address != null)
        {
            try
            {
                rpcAddress = InetAddress.getByName(config.rpc_address);
            }
            catch (UnknownHostException e)
            {
                throw new ConfigurationException("Unknown host in rpc_address " + config.rpc_address, false);
            }
        }
        else if (config.rpc_interface != null)
        {
            rpcAddress = getNetworkInterfaceAddress(config.rpc_interface, "rpc_interface", config.rpc_interface_prefer_ipv6);
        }
        else
        {
            rpcAddress = FBUtilities.getLocalAddress();
        }

        /* RPC address to broadcast */
        if (config.broadcast_rpc_address != null)
        {
            try
            {
                broadcastRpcAddress = InetAddress.getByName(config.broadcast_rpc_address);
            }
            catch (UnknownHostException e)
            {
                throw new ConfigurationException("Unknown broadcast_rpc_address '" + config.broadcast_rpc_address + "'", false);
            }

            if (broadcastRpcAddress.isAnyLocalAddress())
                throw new ConfigurationException("broadcast_rpc_address cannot be a wildcard address (" + config.broadcast_rpc_address + ")!", false);
        }
        else
        {
            if (rpcAddress.isAnyLocalAddress())
                throw new ConfigurationException("If rpc_address is set to a wildcard address (" + config.rpc_address + "), then " +
                                                 "you must set broadcast_rpc_address to a value other than " + config.rpc_address, false);
            broadcastRpcAddress = rpcAddress;
        }
    }

    public static void applyConfig(Config config) throws ConfigurationException
    {
        conf = config;

        if (conf.commitlog_sync == null)
        {
            throw new ConfigurationException("Missing required directive CommitLogSync", false);
        }

        if (conf.commitlog_sync == Config.CommitLogSync.batch)
        {
            if (conf.commitlog_sync_batch_window_in_ms == null)
            {
                throw new ConfigurationException("Missing value for commitlog_sync_batch_window_in_ms: Double expected.", false);
            }
            else if (conf.commitlog_sync_period_in_ms != null)
            {
                throw new ConfigurationException("Batch sync specified, but commitlog_sync_period_in_ms found. Only specify commitlog_sync_batch_window_in_ms when using batch sync", false);
            }
            logger.debug("Syncing log with a batch window of {}", conf.commitlog_sync_batch_window_in_ms);
        }
        else
        {
            if (conf.commitlog_sync_period_in_ms == null)
            {
                throw new ConfigurationException("Missing value for commitlog_sync_period_in_ms: Integer expected", false);
            }
            else if (conf.commitlog_sync_batch_window_in_ms != null)
            {
                throw new ConfigurationException("commitlog_sync_period_in_ms specified, but commitlog_sync_batch_window_in_ms found.  Only specify commitlog_sync_period_in_ms when using periodic sync.", false);
            }
            logger.debug("Syncing log with a period of {}", conf.commitlog_sync_period_in_ms);
        }

        if (conf.commitlog_total_space_in_mb == null)
            conf.commitlog_total_space_in_mb = 8192;

        /* evaluate the DiskAccessMode Config directive, which also affects indexAccessMode selection */
        if (conf.disk_access_mode == Config.DiskAccessMode.auto)
        {
            conf.disk_access_mode = hasLargeAddressSpace() ? Config.DiskAccessMode.mmap : Config.DiskAccessMode.standard;
            indexAccessMode = conf.disk_access_mode;
            logger.info("DiskAccessMode 'auto' determined to be {}, indexAccessMode is {}", conf.disk_access_mode, indexAccessMode);
        }
        else if (conf.disk_access_mode == Config.DiskAccessMode.mmap_index_only)
        {
            conf.disk_access_mode = Config.DiskAccessMode.standard;
            indexAccessMode = Config.DiskAccessMode.mmap;
            logger.info("DiskAccessMode is {}, indexAccessMode is {}", conf.disk_access_mode, indexAccessMode);
        }
        else
        {
            indexAccessMode = conf.disk_access_mode;
            logger.info("DiskAccessMode is {}, indexAccessMode is {}", conf.disk_access_mode, indexAccessMode);
        }

        /* Authentication, authorization and role management backend, implementing IAuthenticator, IAuthorizer & IRoleMapper*/
        if (conf.authenticator != null)
            authenticator = FBUtilities.newAuthenticator(conf.authenticator);

        if (conf.authorizer != null)
            authorizer = FBUtilities.newAuthorizer(conf.authorizer);

        if (authenticator instanceof AllowAllAuthenticator && !(authorizer instanceof AllowAllAuthorizer))
            throw new ConfigurationException("AllowAllAuthenticator can't be used with " +  conf.authorizer, false);

        if (conf.role_manager != null)
            roleManager = FBUtilities.newRoleManager(conf.role_manager);

        if (authenticator instanceof PasswordAuthenticator && !(roleManager instanceof CassandraRoleManager))
            throw new ConfigurationException("CassandraRoleManager must be used with PasswordAuthenticator", false);

        if (conf.internode_authenticator != null)
            internodeAuthenticator = FBUtilities.construct(conf.internode_authenticator, "internode_authenticator");
        else
            internodeAuthenticator = new AllowAllInternodeAuthenticator();

        authenticator.validateConfiguration();
        authorizer.validateConfiguration();
        roleManager.validateConfiguration();
        internodeAuthenticator.validateConfiguration();

        /* Hashing strategy */
        if (conf.partitioner == null)
        {
            throw new ConfigurationException("Missing directive: partitioner", false);
        }
        try
        {
            partitioner = FBUtilities.newPartitioner(System.getProperty("cassandra.partitioner", conf.partitioner));
        }
        catch (Exception e)
        {
            throw new ConfigurationException("Invalid partitioner class " + conf.partitioner, false);
        }
        paritionerName = partitioner.getClass().getCanonicalName();

        if (conf.max_hint_window_in_ms == null)
        {
            throw new ConfigurationException("max_hint_window_in_ms cannot be set to null", false);
        }

        /* phi convict threshold for FailureDetector */
        if (conf.phi_convict_threshold < 5 || conf.phi_convict_threshold > 16)
        {
            throw new ConfigurationException("phi_convict_threshold must be between 5 and 16, but was " + conf.phi_convict_threshold, false);
        }

        /* Thread per pool */
        if (conf.concurrent_reads != null && conf.concurrent_reads < 2)
        {
            throw new ConfigurationException("concurrent_reads must be at least 2, but was " + conf.concurrent_reads, false);
        }

        if (conf.concurrent_writes != null && conf.concurrent_writes < 2)
        {
            throw new ConfigurationException("concurrent_writes must be at least 2, but was " + conf.concurrent_writes, false);
        }

        if (conf.concurrent_counter_writes != null && conf.concurrent_counter_writes < 2)
            throw new ConfigurationException("concurrent_counter_writes must be at least 2, but was " + conf.concurrent_counter_writes, false);

        if (conf.concurrent_replicates != null)
            logger.warn("concurrent_replicates has been deprecated and should be removed from cassandra.yaml");

        if (conf.file_cache_size_in_mb == null)
            conf.file_cache_size_in_mb = Math.min(512, (int) (Runtime.getRuntime().maxMemory() / (4 * 1048576)));

        if (conf.memtable_offheap_space_in_mb == null)
            conf.memtable_offheap_space_in_mb = (int) (Runtime.getRuntime().maxMemory() / (4 * 1048576));
        if (conf.memtable_offheap_space_in_mb < 0)
            throw new ConfigurationException("memtable_offheap_space_in_mb must be positive, but was " + conf.memtable_offheap_space_in_mb, false);
        // for the moment, we default to twice as much on-heap space as off-heap, as heap overhead is very large
        if (conf.memtable_heap_space_in_mb == null)
            conf.memtable_heap_space_in_mb = (int) (Runtime.getRuntime().maxMemory() / (4 * 1048576));
        if (conf.memtable_heap_space_in_mb <= 0)
            throw new ConfigurationException("memtable_heap_space_in_mb must be positive, but was " + conf.memtable_heap_space_in_mb, false);
        logger.info("Global memtable on-heap threshold is enabled at {}MB", conf.memtable_heap_space_in_mb);
        if (conf.memtable_offheap_space_in_mb == 0)
            logger.info("Global memtable off-heap threshold is disabled, HeapAllocator will be used instead");
        else
            logger.info("Global memtable off-heap threshold is enabled at {}MB", conf.memtable_offheap_space_in_mb);

        applyAddressConfig(config);

        if (conf.thrift_framed_transport_size_in_mb <= 0)
            throw new ConfigurationException("thrift_framed_transport_size_in_mb must be positive, but was " + conf.thrift_framed_transport_size_in_mb, false);

        if (conf.native_transport_max_frame_size_in_mb <= 0)
            throw new ConfigurationException("native_transport_max_frame_size_in_mb must be positive, but was " + conf.native_transport_max_frame_size_in_mb, false);

        // fail early instead of OOMing (see CASSANDRA-8116)
        if (ThriftServer.HSHA.equals(conf.rpc_server_type) && conf.rpc_max_threads == Integer.MAX_VALUE)
            throw new ConfigurationException("The hsha rpc_server_type is not compatible with an rpc_max_threads " +
                                             "setting of 'unlimited'.  Please see the comments in cassandra.yaml " +
                                             "for rpc_server_type and rpc_max_threads.",
                                             false);
        if (ThriftServer.HSHA.equals(conf.rpc_server_type) && conf.rpc_max_threads > (FBUtilities.getAvailableProcessors() * 2 + 1024))
            logger.warn("rpc_max_threads setting of {} may be too high for the hsha server and cause unnecessary thread contention, reducing performance", conf.rpc_max_threads);

        /* end point snitch */
        if (conf.endpoint_snitch == null)
        {
            throw new ConfigurationException("Missing endpoint_snitch directive", false);
        }
        snitch = createEndpointSnitch(conf.endpoint_snitch);
        EndpointSnitchInfo.create();

        localDC = snitch.getDatacenter(FBUtilities.getBroadcastAddress());
        localComparator = new Comparator<InetAddress>()
        {
            public int compare(InetAddress endpoint1, InetAddress endpoint2)
            {
                boolean local1 = localDC.equals(snitch.getDatacenter(endpoint1));
                boolean local2 = localDC.equals(snitch.getDatacenter(endpoint2));
                if (local1 && !local2)
                    return -1;
                if (local2 && !local1)
                    return 1;
                return 0;
            }
        };

        /* Request Scheduler setup */
        requestSchedulerOptions = conf.request_scheduler_options;
        if (conf.request_scheduler != null)
        {
            try
            {
                if (requestSchedulerOptions == null)
                {
                    requestSchedulerOptions = new RequestSchedulerOptions();
                }
                Class<?> cls = Class.forName(conf.request_scheduler);
                requestScheduler = (IRequestScheduler) cls.getConstructor(RequestSchedulerOptions.class).newInstance(requestSchedulerOptions);
            }
            catch (ClassNotFoundException e)
            {
                throw new ConfigurationException("Invalid Request Scheduler class " + conf.request_scheduler, false);
            }
            catch (Exception e)
            {
                throw new ConfigurationException("Unable to instantiate request scheduler", e);
            }
        }
        else
        {
            requestScheduler = new NoScheduler();
        }

        if (conf.request_scheduler_id == RequestSchedulerId.keyspace)
        {
            requestSchedulerId = conf.request_scheduler_id;
        }
        else
        {
            // Default to Keyspace
            requestSchedulerId = RequestSchedulerId.keyspace;
        }

        // if data dirs, commitlog dir, or saved caches dir are set in cassandra.yaml, use that.  Otherwise,
        // use -Dcassandra.storagedir (set in cassandra-env.sh) as the parent dir for data/, commitlog/, and saved_caches/
        if (conf.commitlog_directory == null)
        {
            conf.commitlog_directory = System.getProperty("cassandra.storagedir", null);
            if (conf.commitlog_directory == null)
                throw new ConfigurationException("commitlog_directory is missing and -Dcassandra.storagedir is not set", false);
            conf.commitlog_directory += File.separator + "commitlog";
        }
        if (conf.saved_caches_directory == null)
        {
            conf.saved_caches_directory = System.getProperty("cassandra.storagedir", null);
            if (conf.saved_caches_directory == null)
                throw new ConfigurationException("saved_caches_directory is missing and -Dcassandra.storagedir is not set", false);
            conf.saved_caches_directory += File.separator + "saved_caches";
        }
        if (conf.data_file_directories == null)
        {
            String defaultDataDir = System.getProperty("cassandra.storagedir", null);
            if (defaultDataDir == null)
                throw new ConfigurationException("data_file_directories is not missing and -Dcassandra.storagedir is not set", false);
            conf.data_file_directories = new String[]{ defaultDataDir + File.separator + "data" };
        }

        /* data file and commit log directories. they get created later, when they're needed. */
        for (String datadir : conf.data_file_directories)
        {
            if (datadir.equals(conf.commitlog_directory))
                throw new ConfigurationException("commitlog_directory must not be the same as any data_file_directories", false);
            if (datadir.equals(conf.saved_caches_directory))
                throw new ConfigurationException("saved_caches_directory must not be the same as any data_file_directories", false);
        }

        if (conf.commitlog_directory.equals(conf.saved_caches_directory))
            throw new ConfigurationException("saved_caches_directory must not be the same as the commitlog_directory", false);

        if (conf.memtable_flush_writers == null)
            conf.memtable_flush_writers = Math.min(8, Math.max(2, Math.min(FBUtilities.getAvailableProcessors(), conf.data_file_directories.length)));

        if (conf.memtable_flush_writers < 1)
            throw new ConfigurationException("memtable_flush_writers must be at least 1, but was " + conf.memtable_flush_writers, false);

        if (conf.memtable_cleanup_threshold == null)
            conf.memtable_cleanup_threshold = (float) (1.0 / (1 + conf.memtable_flush_writers));

        if (conf.memtable_cleanup_threshold < 0.01f)
            throw new ConfigurationException("memtable_cleanup_threshold must be >= 0.01, but was " + conf.memtable_cleanup_threshold, false);
        if (conf.memtable_cleanup_threshold > 0.99f)
            throw new ConfigurationException("memtable_cleanup_threshold must be <= 0.99, but was " + conf.memtable_cleanup_threshold, false);
        if (conf.memtable_cleanup_threshold < 0.1f)
            logger.warn("memtable_cleanup_threshold is set very low [{}], which may cause performance degradation", conf.memtable_cleanup_threshold);

        if (conf.concurrent_compactors == null)
            conf.concurrent_compactors = Math.min(8, Math.max(2, Math.min(FBUtilities.getAvailableProcessors(), conf.data_file_directories.length)));

        if (conf.concurrent_compactors <= 0)
            throw new ConfigurationException("concurrent_compactors should be strictly greater than 0, but was " + conf.concurrent_compactors, false);

        if (conf.initial_token != null)
            for (String token : tokensFromString(conf.initial_token))
                partitioner.getTokenFactory().validate(token);

        if (conf.num_tokens == null)
        	conf.num_tokens = 1;
        else if (conf.num_tokens > MAX_NUM_TOKENS)
            throw new ConfigurationException(String.format("A maximum number of %d tokens per node is supported", MAX_NUM_TOKENS), false);

        try
        {
            // if key_cache_size_in_mb option was set to "auto" then size of the cache should be "min(5% of Heap (in MB), 100MB)
            keyCacheSizeInMB = (conf.key_cache_size_in_mb == null)
                ? Math.min(Math.max(1, (int) (Runtime.getRuntime().totalMemory() * 0.05 / 1024 / 1024)), 100)
                : conf.key_cache_size_in_mb;

            if (keyCacheSizeInMB < 0)
                throw new NumberFormatException(); // to escape duplicating error message
        }
        catch (NumberFormatException e)
        {
            throw new ConfigurationException("key_cache_size_in_mb option was set incorrectly to '"
                    + conf.key_cache_size_in_mb + "', supported values are <integer> >= 0.", false);
        }

        try
        {
            // if counter_cache_size_in_mb option was set to "auto" then size of the cache should be "min(2.5% of Heap (in MB), 50MB)
            counterCacheSizeInMB = (conf.counter_cache_size_in_mb == null)
                    ? Math.min(Math.max(1, (int) (Runtime.getRuntime().totalMemory() * 0.025 / 1024 / 1024)), 50)
                    : conf.counter_cache_size_in_mb;

            if (counterCacheSizeInMB < 0)
                throw new NumberFormatException(); // to escape duplicating error message
        }
        catch (NumberFormatException e)
        {
            throw new ConfigurationException("counter_cache_size_in_mb option was set incorrectly to '"
                    + conf.counter_cache_size_in_mb + "', supported values are <integer> >= 0.", false);
        }

        // if set to empty/"auto" then use 5% of Heap size
        indexSummaryCapacityInMB = (conf.index_summary_capacity_in_mb == null)
            ? Math.max(1, (int) (Runtime.getRuntime().totalMemory() * 0.05 / 1024 / 1024))
            : conf.index_summary_capacity_in_mb;

        if (indexSummaryCapacityInMB < 0)
            throw new ConfigurationException("index_summary_capacity_in_mb option was set incorrectly to '"
                    + conf.index_summary_capacity_in_mb + "', it should be a non-negative integer.", false);

        if(conf.encryption_options != null)
        {
            logger.warn("Please rename encryption_options as server_encryption_options in the yaml");
            //operate under the assumption that server_encryption_options is not set in yaml rather than both
            conf.server_encryption_options = conf.encryption_options;
        }

        // load the seeds for node contact points
        if (conf.seed_provider == null)
        {
            throw new ConfigurationException("seeds configuration is missing; a minimum of one seed is required.", false);
        }
        try
        {
            Class<?> seedProviderClass = Class.forName(conf.seed_provider.class_name);
            seedProvider = (SeedProvider)seedProviderClass.getConstructor(Map.class).newInstance(conf.seed_provider.parameters);
        }
        // there are about 5 checked exceptions that could be thrown here.
        catch (Exception e)
        {
            throw new ConfigurationException(e.getMessage() + "\nFatal configuration error; unable to start server.  See log for stacktrace.", false);
        }
        if (seedProvider.getSeeds().size() == 0)
            throw new ConfigurationException("The seed provider lists no seeds.", false);
    }

    private static IEndpointSnitch createEndpointSnitch(String snitchClassName) throws ConfigurationException
    {
        if (!snitchClassName.contains("."))
            snitchClassName = "org.apache.cassandra.locator." + snitchClassName;
        IEndpointSnitch snitch = FBUtilities.construct(snitchClassName, "snitch");
        return conf.dynamic_snitch ? new DynamicEndpointSnitch(snitch) : snitch;
    }

    public static IAuthenticator getAuthenticator()
    {
        return authenticator;
    }

    public static IAuthorizer getAuthorizer()
    {
        return authorizer;
    }

    public static IRoleManager getRoleManager()
    {
        return roleManager;
    }

    public static int getPermissionsValidity()
    {
        return conf.permissions_validity_in_ms;
    }

    public static void setPermissionsValidity(int timeout)
    {
        conf.permissions_validity_in_ms = timeout;
    }

    public static int getPermissionsCacheMaxEntries()
    {
        return conf.permissions_cache_max_entries;
    }

    public static int getPermissionsUpdateInterval()
    {
        return conf.permissions_update_interval_in_ms == -1
             ? conf.permissions_validity_in_ms
             : conf.permissions_update_interval_in_ms;
    }

    public static int getRolesValidity()
    {
        return conf.roles_validity_in_ms;
    }

    public static void setRolesValidity(int validity)
    {
        conf.roles_validity_in_ms = validity;
    }

    public static int getRolesCacheMaxEntries()
    {
        return conf.roles_cache_max_entries;
    }

    public static int getRolesUpdateInterval()
    {
        return conf.roles_update_interval_in_ms == -1
             ? conf.roles_validity_in_ms
             : conf.roles_update_interval_in_ms;
    }

    public static void setRolesUpdateInterval(int interval)
    {
        conf.roles_update_interval_in_ms = interval;
    }

    public static void setPermissionsUpdateInterval(int updateInterval)
    {
        conf.permissions_update_interval_in_ms = updateInterval;
    }

    public static int getThriftFramedTransportSize()
    {
        return conf.thrift_framed_transport_size_in_mb * 1024 * 1024;
    }

    /**
     * Creates all storage-related directories.
     */
    public static void createAllDirectories()
    {
        try
        {
            if (conf.data_file_directories.length == 0)
                throw new ConfigurationException("At least one DataFileDirectory must be specified", false);

            for (String dataFileDirectory : conf.data_file_directories)
            {
                FileUtils.createDirectory(dataFileDirectory);
            }

            if (conf.commitlog_directory == null)
                throw new ConfigurationException("commitlog_directory must be specified", false);

            FileUtils.createDirectory(conf.commitlog_directory);

            if (conf.saved_caches_directory == null)
                throw new ConfigurationException("saved_caches_directory must be specified", false);

            FileUtils.createDirectory(conf.saved_caches_directory);
        }
        catch (ConfigurationException e)
        {
            throw new IllegalArgumentException("Bad configuration; unable to start server: "+e.getMessage());
        }
        catch (FSWriteError e)
        {
            throw new IllegalStateException(e.getCause().getMessage() + "; unable to start server");
        }
    }

    public static IPartitioner getPartitioner()
    {
        return partitioner;
    }

    public static String getPartitionerName()
    {
        return paritionerName;
    }

    /* For tests ONLY, don't use otherwise or all hell will break loose */
    public static void setPartitioner(IPartitioner newPartitioner)
    {
        partitioner = newPartitioner;
    }

    public static IEndpointSnitch getEndpointSnitch()
    {
        return snitch;
    }
    public static void setEndpointSnitch(IEndpointSnitch eps)
    {
        snitch = eps;
    }

    public static IRequestScheduler getRequestScheduler()
    {
        return requestScheduler;
    }

    public static RequestSchedulerOptions getRequestSchedulerOptions()
    {
        return requestSchedulerOptions;
    }

    public static RequestSchedulerId getRequestSchedulerId()
    {
        return requestSchedulerId;
    }

    public static int getColumnIndexSize()
    {
        return conf.column_index_size_in_kb * 1024;
    }

    public static int getBatchSizeWarnThreshold()
    {
        return conf.batch_size_warn_threshold_in_kb * 1024;
    }

    public static long getBatchSizeFailThreshold()
    {
        return conf.batch_size_fail_threshold_in_kb * 1024L;
    }

    public static int getBatchSizeFailThresholdInKB()
    {
        return conf.batch_size_fail_threshold_in_kb;
    }

    public static void setBatchSizeWarnThresholdInKB(int threshold)
    {
        conf.batch_size_warn_threshold_in_kb = threshold;
    }

    public static void setBatchSizeFailThresholdInKB(int threshold)
    {
        conf.batch_size_fail_threshold_in_kb = threshold;
    }

    public static Collection<String> getInitialTokens()
    {
        return tokensFromString(System.getProperty("cassandra.initial_token", conf.initial_token));
    }

    public static String getAllocateTokensKeyspace()
    {
        return System.getProperty("cassandra.allocate_tokens_keyspace", conf.allocate_tokens_for_keyspace);
    }

    public static Collection<String> tokensFromString(String tokenString)
    {
        List<String> tokens = new ArrayList<String>();
        if (tokenString != null)
            for (String token : tokenString.split(","))
                tokens.add(token.replaceAll("^\\s+", "").replaceAll("\\s+$", ""));
        return tokens;
    }

    public static Integer getNumTokens()
    {
        return conf.num_tokens;
    }

    public static InetAddress getReplaceAddress()
    {
        try
        {
            if (System.getProperty("cassandra.replace_address", null) != null)
                return InetAddress.getByName(System.getProperty("cassandra.replace_address", null));
            else if (System.getProperty("cassandra.replace_address_first_boot", null) != null)
                return InetAddress.getByName(System.getProperty("cassandra.replace_address_first_boot", null));
            return null;
        }
        catch (UnknownHostException e)
        {
            return null;
        }
    }

    public static Collection<String> getReplaceTokens()
    {
        return tokensFromString(System.getProperty("cassandra.replace_token", null));
    }

    public static UUID getReplaceNode()
    {
        try
        {
            return UUID.fromString(System.getProperty("cassandra.replace_node", null));
        } catch (NullPointerException e)
        {
            return null;
        }
    }

    public static boolean isReplacing()
    {
        if (System.getProperty("cassandra.replace_address_first_boot", null) != null && SystemKeyspace.bootstrapComplete())
        {
            logger.info("Replace address on first boot requested; this node is already bootstrapped");
            return false;
        }
        return getReplaceAddress() != null;
    }

    public static String getClusterName()
    {
        return conf.cluster_name;
    }

    public static int getMaxStreamingRetries()
    {
        return conf.max_streaming_retries;
    }

    public static int getStoragePort()
    {
        return Integer.parseInt(System.getProperty("cassandra.storage_port", conf.storage_port.toString()));
    }

    public static int getSSLStoragePort()
    {
        return Integer.parseInt(System.getProperty("cassandra.ssl_storage_port", conf.ssl_storage_port.toString()));
    }

    public static int getRpcPort()
    {
        return Integer.parseInt(System.getProperty("cassandra.rpc_port", conf.rpc_port.toString()));
    }

    public static int getRpcListenBacklog()
    {
        return conf.rpc_listen_backlog;
    }

    public static long getRpcTimeout()
    {
        return conf.request_timeout_in_ms;
    }

    public static void setRpcTimeout(Long timeOutInMillis)
    {
        conf.request_timeout_in_ms = timeOutInMillis;
    }

    public static long getReadRpcTimeout()
    {
        return conf.read_request_timeout_in_ms;
    }

    public static void setReadRpcTimeout(Long timeOutInMillis)
    {
        conf.read_request_timeout_in_ms = timeOutInMillis;
    }

    public static long getRangeRpcTimeout()
    {
        return conf.range_request_timeout_in_ms;
    }

    public static void setRangeRpcTimeout(Long timeOutInMillis)
    {
        conf.range_request_timeout_in_ms = timeOutInMillis;
    }

    public static long getWriteRpcTimeout()
    {
        return conf.write_request_timeout_in_ms;
    }

    public static void setWriteRpcTimeout(Long timeOutInMillis)
    {
        conf.write_request_timeout_in_ms = timeOutInMillis;
    }

    public static long getCounterWriteRpcTimeout()
    {
        return conf.counter_write_request_timeout_in_ms;
    }

    public static void setCounterWriteRpcTimeout(Long timeOutInMillis)
    {
        conf.counter_write_request_timeout_in_ms = timeOutInMillis;
    }

    public static long getCasContentionTimeout()
    {
        return conf.cas_contention_timeout_in_ms;
    }

    public static void setCasContentionTimeout(Long timeOutInMillis)
    {
        conf.cas_contention_timeout_in_ms = timeOutInMillis;
    }

    public static long getTruncateRpcTimeout()
    {
        return conf.truncate_request_timeout_in_ms;
    }

    public static void setTruncateRpcTimeout(Long timeOutInMillis)
    {
        conf.truncate_request_timeout_in_ms = timeOutInMillis;
    }

    public static boolean hasCrossNodeTimeout()
    {
        return conf.cross_node_timeout;
    }

    // not part of the Verb enum so we can change timeouts easily via JMX
    public static long getTimeout(MessagingService.Verb verb)
    {
        switch (verb)
        {
            case READ:
                return getReadRpcTimeout();
            case RANGE_SLICE:
                return getRangeRpcTimeout();
            case TRUNCATE:
                return getTruncateRpcTimeout();
            case READ_REPAIR:
            case MUTATION:
            case PAXOS_COMMIT:
            case PAXOS_PREPARE:
            case PAXOS_PROPOSE:
                return getWriteRpcTimeout();
            case COUNTER_MUTATION:
                return getCounterWriteRpcTimeout();
            default:
                return getRpcTimeout();
        }
    }

    /**
     * @return the minimum configured {read, write, range, truncate, misc} timeout
     */
    public static long getMinRpcTimeout()
    {
        return Longs.min(getRpcTimeout(),
                         getReadRpcTimeout(),
                         getRangeRpcTimeout(),
                         getWriteRpcTimeout(),
                         getCounterWriteRpcTimeout(),
                         getTruncateRpcTimeout());
    }

    public static double getPhiConvictThreshold()
    {
        return conf.phi_convict_threshold;
    }

    public static void setPhiConvictThreshold(double phiConvictThreshold)
    {
        conf.phi_convict_threshold = phiConvictThreshold;
    }

    public static int getConcurrentReaders()
    {
        return conf.concurrent_reads;
    }

    public static int getConcurrentWriters()
    {
        return conf.concurrent_writes;
    }

    public static int getConcurrentCounterWriters()
    {
        return conf.concurrent_counter_writes;
    }

    public static int getFlushWriters()
    {
            return conf.memtable_flush_writers;
    }

    public static int getConcurrentCompactors()
    {
        return conf.concurrent_compactors;
    }

    public static int getCompactionThroughputMbPerSec()
    {
        return conf.compaction_throughput_mb_per_sec;
    }

    public static void setCompactionThroughputMbPerSec(int value)
    {
        conf.compaction_throughput_mb_per_sec = value;
    }

    public static int getCompactionLargePartitionWarningThreshold() { return conf.compaction_large_partition_warning_threshold_mb * 1024 * 1024; }

    public static boolean getDisableSTCSInL0()
    {
        return Boolean.getBoolean("cassandra.disable_stcs_in_l0");
    }

    public static int getStreamThroughputOutboundMegabitsPerSec()
    {
        return conf.stream_throughput_outbound_megabits_per_sec;
    }

    public static void setStreamThroughputOutboundMegabitsPerSec(int value)
    {
        conf.stream_throughput_outbound_megabits_per_sec = value;
    }

    public static int getInterDCStreamThroughputOutboundMegabitsPerSec()
    {
        return conf.inter_dc_stream_throughput_outbound_megabits_per_sec;
    }

    public static void setInterDCStreamThroughputOutboundMegabitsPerSec(int value)
    {
        conf.inter_dc_stream_throughput_outbound_megabits_per_sec = value;
    }

    public static String[] getAllDataFileLocations()
    {
        return conf.data_file_directories;
    }

    public static String getCommitLogLocation()
    {
        return conf.commitlog_directory;
    }

    public static ParameterizedClass getCommitLogCompression()
    {
        return conf.commitlog_compression;
    }

    public static void setCommitLogCompression(ParameterizedClass compressor)
    {
        conf.commitlog_compression = compressor;
    }

    public static int getCommitLogMaxCompressionBuffersInPool()
    {
        return conf.commitlog_max_compression_buffers_in_pool;
    }

    public static int getTombstoneWarnThreshold()
    {
        return conf.tombstone_warn_threshold;
    }

    public static void setTombstoneWarnThreshold(int threshold)
    {
        conf.tombstone_warn_threshold = threshold;
    }

    public static int getTombstoneFailureThreshold()
    {
        return conf.tombstone_failure_threshold;
    }

    public static void setTombstoneFailureThreshold(int threshold)
    {
        conf.tombstone_failure_threshold = threshold;
    }

    /**
     * size of commitlog segments to allocate
     */
    public static int getCommitLogSegmentSize()
    {
        return conf.commitlog_segment_size_in_mb * 1024 * 1024;
    }
    
    public static void setCommitLogSegmentSize(int sizeMegabytes)
    {
        conf.commitlog_segment_size_in_mb = sizeMegabytes;
    }

    public static String getSavedCachesLocation()
    {
        return conf.saved_caches_directory;
    }

    public static Set<InetAddress> getSeeds()
    {
        return ImmutableSet.<InetAddress>builder().addAll(seedProvider.getSeeds()).build();
    }

    public static InetAddress getListenAddress()
    {
        return listenAddress;
    }

    public static InetAddress getBroadcastAddress()
    {
        return broadcastAddress;
    }

    public static IInternodeAuthenticator getInternodeAuthenticator()
    {
        return internodeAuthenticator;
    }

    public static void setBroadcastAddress(InetAddress broadcastAdd)
    {
        broadcastAddress = broadcastAdd;
    }

    public static boolean startRpc()
    {
        return conf.start_rpc;
    }

    public static InetAddress getRpcAddress()
    {
        return rpcAddress;
    }

    public static void setBroadcastRpcAddress(InetAddress broadcastRPCAddr)
    {
        broadcastRpcAddress = broadcastRPCAddr;
    }

    public static InetAddress getBroadcastRpcAddress()
    {
        return broadcastRpcAddress;
    }

    public static String getRpcServerType()
    {
        return conf.rpc_server_type;
    }

    public static boolean getRpcKeepAlive()
    {
        return conf.rpc_keepalive;
    }

    public static Integer getRpcMinThreads()
    {
        return conf.rpc_min_threads;
    }

    public static Integer getRpcMaxThreads()
    {
        return conf.rpc_max_threads;
    }

    public static Integer getRpcSendBufferSize()
    {
        return conf.rpc_send_buff_size_in_bytes;
    }

    public static Integer getRpcRecvBufferSize()
    {
        return conf.rpc_recv_buff_size_in_bytes;
    }

    public static Integer getInternodeSendBufferSize()
    {
        return conf.internode_send_buff_size_in_bytes;
    }

    public static Integer getInternodeRecvBufferSize()
    {
        return conf.internode_recv_buff_size_in_bytes;
    }

    public static boolean startNativeTransport()
    {
        return conf.start_native_transport;
    }

    public static int getNativeTransportPort()
    {
        return Integer.parseInt(System.getProperty("cassandra.native_transport_port", conf.native_transport_port.toString()));
    }

    public static Integer getNativeTransportMaxThreads()
    {
        return conf.native_transport_max_threads;
    }

    public static int getNativeTransportMaxFrameSize()
    {
        return conf.native_transport_max_frame_size_in_mb * 1024 * 1024;
    }

    public static Long getNativeTransportMaxConcurrentConnections()
    {
        return conf.native_transport_max_concurrent_connections;
    }

    public static void setNativeTransportMaxConcurrentConnections(long nativeTransportMaxConcurrentConnections)
    {
        conf.native_transport_max_concurrent_connections = nativeTransportMaxConcurrentConnections;
    }

    public static Long getNativeTransportMaxConcurrentConnectionsPerIp() {
        return conf.native_transport_max_concurrent_connections_per_ip;
    }

    public static void setNativeTransportMaxConcurrentConnectionsPerIp(long native_transport_max_concurrent_connections_per_ip)
    {
        conf.native_transport_max_concurrent_connections_per_ip = native_transport_max_concurrent_connections_per_ip;
    }

    public static double getCommitLogSyncBatchWindow()
    {
        return conf.commitlog_sync_batch_window_in_ms;
    }

    public static void setCommitLogSyncBatchWindow(double windowMillis)
    {
        conf.commitlog_sync_batch_window_in_ms = windowMillis;
    }

    public static int getCommitLogSyncPeriod()
    {
        return conf.commitlog_sync_period_in_ms;
    }
    
    public static void setCommitLogSyncPeriod(int periodMillis)
    {
        conf.commitlog_sync_period_in_ms = periodMillis;
    }

    public static Config.CommitLogSync getCommitLogSync()
    {
        return conf.commitlog_sync;
    }

    public static void setCommitLogSync(CommitLogSync sync)
    {
        conf.commitlog_sync = sync;
    }

    public static Config.DiskAccessMode getDiskAccessMode()
    {
        return conf.disk_access_mode;
    }

    // Do not use outside unit tests.
    @VisibleForTesting
    public static void setDiskAccessMode(Config.DiskAccessMode mode)
    {
        conf.disk_access_mode = mode;
    }

    public static Config.DiskAccessMode getIndexAccessMode()
    {
        return indexAccessMode;
    }

    // Do not use outside unit tests.
    @VisibleForTesting
    public static void setIndexAccessMode(Config.DiskAccessMode mode)
    {
        indexAccessMode = mode;
    }

    public static void setDiskFailurePolicy(Config.DiskFailurePolicy policy)
    {
        conf.disk_failure_policy = policy;
    }

    public static Config.DiskFailurePolicy getDiskFailurePolicy()
    {
        return conf.disk_failure_policy;
    }

    public static void setCommitFailurePolicy(Config.CommitFailurePolicy policy)
    {
        conf.commit_failure_policy = policy;
    }

    public static Config.CommitFailurePolicy getCommitFailurePolicy()
    {
        return conf.commit_failure_policy;
    }

    public static boolean isSnapshotBeforeCompaction()
    {
        return conf.snapshot_before_compaction;
    }

    public static boolean isAutoSnapshot() {
        return conf.auto_snapshot;
    }

    @VisibleForTesting
    public static void setAutoSnapshot(boolean autoSnapshot)
    {
        conf.auto_snapshot = autoSnapshot;
    }
    @VisibleForTesting
    public static boolean getAutoSnapshot()
    {
        return conf.auto_snapshot;
    }

    public static boolean isAutoBootstrap()
    {
        return Boolean.parseBoolean(System.getProperty("cassandra.auto_bootstrap", conf.auto_bootstrap.toString()));
    }

    public static void setHintedHandoffEnabled(boolean hintedHandoffEnabled)
    {
        conf.hinted_handoff_enabled = hintedHandoffEnabled;
    }

    public static boolean hintedHandoffEnabled()
    {
        return conf.hinted_handoff_enabled;
    }

    public static Set<String> hintedHandoffDisabledDCs()
    {
        return conf.hinted_handoff_disabled_datacenters;
    }

    public static void enableHintsForDC(String dc)
    {
        conf.hinted_handoff_disabled_datacenters.remove(dc);
    }

    public static void disableHintsForDC(String dc)
    {
        conf.hinted_handoff_disabled_datacenters.add(dc);
    }

    public static void setMaxHintWindow(int ms)
    {
        conf.max_hint_window_in_ms = ms;
    }

    public static int getMaxHintWindow()
    {
        return conf.max_hint_window_in_ms;
    }

    public static File getSerializedCachePath(String ksName, String cfName, UUID cfId, CacheService.CacheType cacheType, String version)
    {
        StringBuilder builder = new StringBuilder();
        builder.append(ksName).append('-');
        builder.append(cfName).append('-');
        builder.append(ByteBufferUtil.bytesToHex(ByteBufferUtil.bytes(cfId))).append('-');
        builder.append(cacheType);
        builder.append((version == null ? "" : "-" + version + ".db"));
        return new File(conf.saved_caches_directory, builder.toString());
    }

    public static int getDynamicUpdateInterval()
    {
        return conf.dynamic_snitch_update_interval_in_ms;
    }
    public static void setDynamicUpdateInterval(Integer dynamicUpdateInterval)
    {
        conf.dynamic_snitch_update_interval_in_ms = dynamicUpdateInterval;
    }

    public static int getDynamicResetInterval()
    {
        return conf.dynamic_snitch_reset_interval_in_ms;
    }
    public static void setDynamicResetInterval(Integer dynamicResetInterval)
    {
        conf.dynamic_snitch_reset_interval_in_ms = dynamicResetInterval;
    }

    public static double getDynamicBadnessThreshold()
    {
        return conf.dynamic_snitch_badness_threshold;
    }

    public static void setDynamicBadnessThreshold(Double dynamicBadnessThreshold)
    {
        conf.dynamic_snitch_badness_threshold = dynamicBadnessThreshold;
    }

    public static ServerEncryptionOptions getServerEncryptionOptions()
    {
        return conf.server_encryption_options;
    }

    public static ClientEncryptionOptions getClientEncryptionOptions()
    {
        return conf.client_encryption_options;
    }

    public static int getHintedHandoffThrottleInKB()
    {
        return conf.hinted_handoff_throttle_in_kb;
    }

    public static int getBatchlogReplayThrottleInKB()
    {
        return conf.batchlog_replay_throttle_in_kb;
    }

    public static void setHintedHandoffThrottleInKB(Integer throttleInKB)
    {
        conf.hinted_handoff_throttle_in_kb = throttleInKB;
    }

    public static int getMaxHintsThread()
    {
        return conf.max_hints_delivery_threads;
    }

    public static boolean isIncrementalBackupsEnabled()
    {
        return conf.incremental_backups;
    }

    public static void setIncrementalBackupsEnabled(boolean value)
    {
        conf.incremental_backups = value;
    }

    public static int getFileCacheSizeInMB()
    {
        return conf.file_cache_size_in_mb;
    }

    public static boolean getBufferPoolUseHeapIfExhausted()
    {
        return conf.buffer_pool_use_heap_if_exhausted;
    }

    public static long getTotalCommitlogSpaceInMB()
    {
        return conf.commitlog_total_space_in_mb;
    }

    public static int getSSTablePreempiveOpenIntervalInMB()
    {
        return FBUtilities.isWindows() ? -1 : conf.sstable_preemptive_open_interval_in_mb;
    }

    public static boolean getTrickleFsync()
    {
        return conf.trickle_fsync;
    }

    public static int getTrickleFsyncIntervalInKb()
    {
        return conf.trickle_fsync_interval_in_kb;
    }

    public static long getKeyCacheSizeInMB()
    {
        return keyCacheSizeInMB;
    }

    public static long getIndexSummaryCapacityInMB()
    {
        return indexSummaryCapacityInMB;
    }

    public static int getKeyCacheSavePeriod()
    {
        return conf.key_cache_save_period;
    }

    public static void setKeyCacheSavePeriod(int keyCacheSavePeriod)
    {
        conf.key_cache_save_period = keyCacheSavePeriod;
    }

    public static int getKeyCacheKeysToSave()
    {
        return conf.key_cache_keys_to_save;
    }

    public static void setKeyCacheKeysToSave(int keyCacheKeysToSave)
    {
        conf.key_cache_keys_to_save = keyCacheKeysToSave;
    }

    public static String getRowCacheClassName()
    {
        return conf.row_cache_class_name;
    }

    public static long getRowCacheSizeInMB()
    {
        return conf.row_cache_size_in_mb;
    }

    @VisibleForTesting
    public static void setRowCacheSizeInMB(long val)
    {
        conf.row_cache_size_in_mb = val;
    }

    public static int getRowCacheSavePeriod()
    {
        return conf.row_cache_save_period;
    }

    public static void setRowCacheSavePeriod(int rowCacheSavePeriod)
    {
        conf.row_cache_save_period = rowCacheSavePeriod;
    }

    public static int getRowCacheKeysToSave()
    {
        return conf.row_cache_keys_to_save;
    }

    public static long getCounterCacheSizeInMB()
    {
        return counterCacheSizeInMB;
    }

    public static void setRowCacheKeysToSave(int rowCacheKeysToSave)
    {
        conf.row_cache_keys_to_save = rowCacheKeysToSave;
    }

    public static int getCounterCacheSavePeriod()
    {
        return conf.counter_cache_save_period;
    }

    public static void setCounterCacheSavePeriod(int counterCacheSavePeriod)
    {
        conf.counter_cache_save_period = counterCacheSavePeriod;
    }

    public static int getCounterCacheKeysToSave()
    {
        return conf.counter_cache_keys_to_save;
    }

    public static void setCounterCacheKeysToSave(int counterCacheKeysToSave)
    {
        conf.counter_cache_keys_to_save = counterCacheKeysToSave;
    }

    public static int getStreamingSocketTimeout()
    {
        return conf.streaming_socket_timeout_in_ms;
    }

    public static String getLocalDataCenter()
    {
        return localDC;
    }

    public static Comparator<InetAddress> getLocalComparator()
    {
        return localComparator;
    }

    public static Config.InternodeCompression internodeCompression()
    {
        return conf.internode_compression;
    }

    public static boolean getInterDCTcpNoDelay()
    {
        return conf.inter_dc_tcp_nodelay;
    }


    public static SSTableFormat.Type getSSTableFormat()
    {
        return sstable_format;
    }

    public static MemtablePool getMemtableAllocatorPool()
    {
        long heapLimit = ((long) conf.memtable_heap_space_in_mb) << 20;
        long offHeapLimit = ((long) conf.memtable_offheap_space_in_mb) << 20;
        switch (conf.memtable_allocation_type)
        {
            case unslabbed_heap_buffers:
                return new HeapPool(heapLimit, conf.memtable_cleanup_threshold, new ColumnFamilyStore.FlushLargestColumnFamily());
            case heap_buffers:
                return new SlabPool(heapLimit, 0, conf.memtable_cleanup_threshold, new ColumnFamilyStore.FlushLargestColumnFamily());
            case offheap_buffers:
                if (!FileUtils.isCleanerAvailable())
                {
                    throw new IllegalStateException("Could not free direct byte buffer: offheap_buffers is not a safe memtable_allocation_type without this ability, please adjust your config. This feature is only guaranteed to work on an Oracle JVM. Refusing to start.");
                }
                return new SlabPool(heapLimit, offHeapLimit, conf.memtable_cleanup_threshold, new ColumnFamilyStore.FlushLargestColumnFamily());
            case offheap_objects:
                return new NativePool(heapLimit, offHeapLimit, conf.memtable_cleanup_threshold, new ColumnFamilyStore.FlushLargestColumnFamily());
            default:
                throw new AssertionError();
        }
    }

    public static int getIndexSummaryResizeIntervalInMinutes()
    {
        return conf.index_summary_resize_interval_in_minutes;
    }

    public static boolean hasLargeAddressSpace()
    {
        // currently we just check if it's a 64bit arch, but any we only really care if the address space is large
        String datamodel = System.getProperty("sun.arch.data.model");
        if (datamodel != null)
        {
            switch (datamodel)
            {
                case "64": return true;
                case "32": return false;
            }
        }
        String arch = System.getProperty("os.arch");
        return arch.contains("64") || arch.contains("sparcv9");
    }

    public static int getTracetypeRepairTTL()
    {
        return conf.tracetype_repair_ttl;
    }

    public static int getTracetypeQueryTTL()
    {
        return conf.tracetype_query_ttl;
    }

    public static String getOtcCoalescingStrategy()
    {
        return conf.otc_coalescing_strategy;
    }

    public static int getOtcCoalescingWindow()
    {
        return conf.otc_coalescing_window_us;
    }

    public static boolean enableUserDefinedFunctions()
    {
        return conf.enable_user_defined_functions;
    }

    public static int getWindowsTimerInterval()
    {
        return conf.windows_timer_interval;
    }
}


File: src/java/org/apache/cassandra/cql3/functions/ScriptBasedUDF.java
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
package org.apache.cassandra.cql3.functions;

import java.math.BigDecimal;
import java.math.BigInteger;
import java.nio.ByteBuffer;
import java.util.HashMap;
import java.util.List;
import java.util.Map;

import javax.script.Bindings;
import javax.script.Compilable;
import javax.script.CompiledScript;
import javax.script.ScriptEngine;
import javax.script.ScriptEngineFactory;
import javax.script.ScriptEngineManager;
import javax.script.ScriptException;
import javax.script.SimpleBindings;

import org.apache.cassandra.cql3.ColumnIdentifier;
import org.apache.cassandra.db.marshal.AbstractType;
import org.apache.cassandra.exceptions.FunctionExecutionException;
import org.apache.cassandra.exceptions.InvalidRequestException;

public class ScriptBasedUDF extends UDFunction
{
    static final Map<String, Compilable> scriptEngines = new HashMap<>();

    static {
        ScriptEngineManager scriptEngineManager = new ScriptEngineManager();
        for (ScriptEngineFactory scriptEngineFactory : scriptEngineManager.getEngineFactories())
        {
            ScriptEngine scriptEngine = scriptEngineFactory.getScriptEngine();
            boolean compilable = scriptEngine instanceof Compilable;
            if (compilable)
            {
                logger.info("Found scripting engine {} {} - {} {} - language names: {}",
                            scriptEngineFactory.getEngineName(), scriptEngineFactory.getEngineVersion(),
                            scriptEngineFactory.getLanguageName(), scriptEngineFactory.getLanguageVersion(),
                            scriptEngineFactory.getNames());
                for (String name : scriptEngineFactory.getNames())
                    scriptEngines.put(name, (Compilable) scriptEngine);
            }
        }
    }

    private final CompiledScript script;

    ScriptBasedUDF(FunctionName name,
                   List<ColumnIdentifier> argNames,
                   List<AbstractType<?>> argTypes,
                   AbstractType<?> returnType,
                   boolean calledOnNullInput,
                   String language,
                   String body)
    throws InvalidRequestException
    {
        super(name, argNames, argTypes, returnType, calledOnNullInput, language, body);

        Compilable scriptEngine = scriptEngines.get(language);
        if (scriptEngine == null)
            throw new InvalidRequestException(String.format("Invalid language '%s' for function '%s'", language, name));

        try
        {
            this.script = scriptEngine.compile(body);
        }
        catch (RuntimeException | ScriptException e)
        {
            logger.info("Failed to compile function '{}' for language {}: ", name, language, e);
            throw new InvalidRequestException(
                    String.format("Failed to compile function '%s' for language %s: %s", name, language, e));
        }
    }

    public ByteBuffer executeUserDefined(int protocolVersion, List<ByteBuffer> parameters) throws InvalidRequestException
    {
        Object[] params = new Object[argTypes.size()];
        for (int i = 0; i < params.length; i++)
            params[i] = compose(protocolVersion, i, parameters.get(i));

        try
        {
            Bindings bindings = new SimpleBindings();
            for (int i = 0; i < params.length; i++)
                bindings.put(argNames.get(i).toString(), params[i]);

            Object result = script.eval(bindings);
            if (result == null)
                return null;

            Class<?> javaReturnType = returnDataType.asJavaClass();
            Class<?> resultType = result.getClass();
            if (!javaReturnType.isAssignableFrom(resultType))
            {
                if (result instanceof Number)
                {
                    Number rNumber = (Number) result;
                    if (javaReturnType == Integer.class)
                        result = rNumber.intValue();
                    else if (javaReturnType == Short.class)
                        result = rNumber.shortValue();
                    else if (javaReturnType == Byte.class)
                        result = rNumber.byteValue();
                    else if (javaReturnType == Long.class)
                        result = rNumber.longValue();
                    else if (javaReturnType == Float.class)
                        result = rNumber.floatValue();
                    else if (javaReturnType == Double.class)
                        result = rNumber.doubleValue();
                    else if (javaReturnType == BigInteger.class)
                    {
                        if (rNumber instanceof BigDecimal)
                            result = ((BigDecimal)rNumber).toBigInteger();
                        else if (rNumber instanceof Double || rNumber instanceof Float)
                            result = new BigDecimal(rNumber.toString()).toBigInteger();
                        else
                            result = BigInteger.valueOf(rNumber.longValue());
                    }
                    else if (javaReturnType == BigDecimal.class)
                        // String c'tor of BigDecimal is more accurate than valueOf(double)
                        result = new BigDecimal(rNumber.toString());
                }
            }

            return decompose(protocolVersion, result);
        }
        catch (RuntimeException | ScriptException e)
        {
            logger.debug("Execution of UDF '{}' failed", name, e);
            throw FunctionExecutionException.create(this, e);
        }
    }
}


File: src/java/org/apache/cassandra/cql3/functions/UDAggregate.java
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
package org.apache.cassandra.cql3.functions;

import java.nio.ByteBuffer;
import java.util.*;

import com.google.common.base.Objects;
import com.google.common.collect.ImmutableSet;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import org.apache.cassandra.config.Schema;
import org.apache.cassandra.db.marshal.AbstractType;
import org.apache.cassandra.exceptions.InvalidRequestException;
import org.apache.cassandra.schema.Functions;
import org.apache.cassandra.tracing.Tracing;

/**
 * Base class for user-defined-aggregates.
 */
public class UDAggregate extends AbstractFunction implements AggregateFunction
{
    protected static final Logger logger = LoggerFactory.getLogger(UDAggregate.class);

    protected final AbstractType<?> stateType;
    protected final ByteBuffer initcond;
    private final ScalarFunction stateFunction;
    private final ScalarFunction finalFunction;

    public UDAggregate(FunctionName name,
                       List<AbstractType<?>> argTypes,
                       AbstractType<?> returnType,
                       ScalarFunction stateFunc,
                       ScalarFunction finalFunc,
                       ByteBuffer initcond)
    {
        super(name, argTypes, returnType);
        this.stateFunction = stateFunc;
        this.finalFunction = finalFunc;
        this.stateType = stateFunc != null ? stateFunc.returnType() : null;
        this.initcond = initcond;
    }

    public static UDAggregate create(FunctionName name,
                                     List<AbstractType<?>> argTypes,
                                     AbstractType<?> returnType,
                                     FunctionName stateFunc,
                                     FunctionName finalFunc,
                                     AbstractType<?> stateType,
                                     ByteBuffer initcond)
    throws InvalidRequestException
    {
        List<AbstractType<?>> stateTypes = new ArrayList<>(argTypes.size() + 1);
        stateTypes.add(stateType);
        stateTypes.addAll(argTypes);
        List<AbstractType<?>> finalTypes = Collections.<AbstractType<?>>singletonList(stateType);
        return new UDAggregate(name,
                               argTypes,
                               returnType,
                               resolveScalar(name, stateFunc, stateTypes),
                               finalFunc != null ? resolveScalar(name, finalFunc, finalTypes) : null,
                               initcond);
    }

    public static UDAggregate createBroken(FunctionName name,
                                           List<AbstractType<?>> argTypes,
                                           AbstractType<?> returnType,
                                           ByteBuffer initcond,
                                           final InvalidRequestException reason)
    {
        return new UDAggregate(name, argTypes, returnType, null, null, initcond)
        {
            public Aggregate newAggregate() throws InvalidRequestException
            {
                throw new InvalidRequestException(String.format("Aggregate '%s' exists but hasn't been loaded successfully for the following reason: %s. "
                                                                + "Please see the server log for more details",
                                                                this,
                                                                reason.getMessage()));
            }
        };
    }

    public boolean hasReferenceTo(Function function)
    {
        return stateFunction == function || finalFunction == function;
    }

    public Iterable<Function> getFunctions()
    {
        if (stateFunction == null)
            return Collections.emptySet();
        if (finalFunction != null)
            return ImmutableSet.of(this, stateFunction, finalFunction);
        else
            return ImmutableSet.of(this, stateFunction);
    }

    public boolean isAggregate()
    {
        return true;
    }

    public boolean isNative()
    {
        return false;
    }

    public ScalarFunction stateFunction()
    {
        return stateFunction;
    }

    public ScalarFunction finalFunction()
    {
        return finalFunction;
    }

    public ByteBuffer initialCondition()
    {
        return initcond;
    }

    public AbstractType<?> stateType()
    {
        return stateType;
    }

    public Aggregate newAggregate() throws InvalidRequestException
    {
        return new Aggregate()
        {
            private long stateFunctionCount;
            private long stateFunctionDuration;

            private ByteBuffer state;
            {
                reset();
            }

            public void addInput(int protocolVersion, List<ByteBuffer> values) throws InvalidRequestException
            {
                long startTime = System.nanoTime();
                stateFunctionCount++;
                List<ByteBuffer> fArgs = new ArrayList<>(values.size() + 1);
                fArgs.add(state);
                fArgs.addAll(values);
                if (stateFunction instanceof UDFunction)
                {
                    UDFunction udf = (UDFunction)stateFunction;
                    if (udf.isCallableWrtNullable(fArgs))
                        state = udf.executeUserDefined(protocolVersion, fArgs);
                }
                else
                {
                    state = stateFunction.execute(protocolVersion, fArgs);
                }
                stateFunctionDuration += (System.nanoTime() - startTime) / 1000;
            }

            public ByteBuffer compute(int protocolVersion) throws InvalidRequestException
            {
                // final function is traced in UDFunction
                Tracing.trace("Executed UDA {}: {} call(s) to state function {} in {}\u03bcs", name(), stateFunctionCount, stateFunction.name(), stateFunctionDuration);
                if (finalFunction == null)
                    return state;

                List<ByteBuffer> fArgs = Collections.singletonList(state);
                ByteBuffer result = finalFunction.execute(protocolVersion, fArgs);
                return result;
            }

            public void reset()
            {
                state = initcond != null ? initcond.duplicate() : null;
                stateFunctionDuration = 0;
                stateFunctionCount = 0;
            }
        };
    }

    private static ScalarFunction resolveScalar(FunctionName aName, FunctionName fName, List<AbstractType<?>> argTypes) throws InvalidRequestException
    {
        Optional<Function> fun = Schema.instance.findFunction(fName, argTypes);
        if (!fun.isPresent())
            throw new InvalidRequestException(String.format("Referenced state function '%s %s' for aggregate '%s' does not exist",
                                                            fName,
                                                            Arrays.toString(UDHelper.driverTypes(argTypes)),
                                                            aName));

        if (!(fun.get() instanceof ScalarFunction))
            throw new InvalidRequestException(String.format("Referenced state function '%s %s' for aggregate '%s' is not a scalar function",
                                                            fName,
                                                            Arrays.toString(UDHelper.driverTypes(argTypes)),
                                                            aName));
        return (ScalarFunction) fun.get();
    }

    @Override
    public boolean equals(Object o)
    {
        if (!(o instanceof UDAggregate))
            return false;

        UDAggregate that = (UDAggregate) o;
        return Objects.equal(name, that.name)
            && Functions.typesMatch(argTypes, that.argTypes)
            && Functions.typesMatch(returnType, that.returnType)
            && Objects.equal(stateFunction, that.stateFunction)
            && Objects.equal(finalFunction, that.finalFunction)
            && Objects.equal(stateType, that.stateType)
            && Objects.equal(initcond, that.initcond);
    }

    @Override
    public int hashCode()
    {
        return Objects.hashCode(name, Functions.typeHashCode(argTypes), Functions.typeHashCode(returnType), stateFunction, finalFunction, stateType, initcond);
    }
}


File: src/java/org/apache/cassandra/cql3/functions/UDFunction.java
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
package org.apache.cassandra.cql3.functions;

import java.nio.ByteBuffer;
import java.util.*;

import com.google.common.base.Objects;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import com.datastax.driver.core.DataType;
import com.datastax.driver.core.ProtocolVersion;
import com.datastax.driver.core.UserType;
import org.apache.cassandra.config.DatabaseDescriptor;
import org.apache.cassandra.config.Schema;
import org.apache.cassandra.cql3.*;
import org.apache.cassandra.db.marshal.AbstractType;
import org.apache.cassandra.exceptions.*;
import org.apache.cassandra.schema.Functions;
import org.apache.cassandra.schema.KeyspaceMetadata;
import org.apache.cassandra.service.MigrationManager;
import org.apache.cassandra.tracing.Tracing;
import org.apache.cassandra.utils.ByteBufferUtil;

/**
 * Base class for User Defined Functions.
 */
public abstract class UDFunction extends AbstractFunction implements ScalarFunction
{
    protected static final Logger logger = LoggerFactory.getLogger(UDFunction.class);

    protected final List<ColumnIdentifier> argNames;

    protected final String language;
    protected final String body;

    protected final DataType[] argDataTypes;
    protected final DataType returnDataType;
    protected final boolean calledOnNullInput;

    protected UDFunction(FunctionName name,
                         List<ColumnIdentifier> argNames,
                         List<AbstractType<?>> argTypes,
                         AbstractType<?> returnType,
                         boolean calledOnNullInput,
                         String language,
                         String body)
    {
        this(name, argNames, argTypes, UDHelper.driverTypes(argTypes), returnType,
             UDHelper.driverType(returnType), calledOnNullInput, language, body);
    }

    protected UDFunction(FunctionName name,
                         List<ColumnIdentifier> argNames,
                         List<AbstractType<?>> argTypes,
                         DataType[] argDataTypes,
                         AbstractType<?> returnType,
                         DataType returnDataType,
                         boolean calledOnNullInput,
                         String language,
                         String body)
    {
        super(name, argTypes, returnType);
        assert new HashSet<>(argNames).size() == argNames.size() : "duplicate argument names";
        this.argNames = argNames;
        this.language = language;
        this.body = body;
        this.argDataTypes = argDataTypes;
        this.returnDataType = returnDataType;
        this.calledOnNullInput = calledOnNullInput;
    }

    public static UDFunction create(FunctionName name,
                                    List<ColumnIdentifier> argNames,
                                    List<AbstractType<?>> argTypes,
                                    AbstractType<?> returnType,
                                    boolean calledOnNullInput,
                                    String language,
                                    String body)
    throws InvalidRequestException
    {
        if (!DatabaseDescriptor.enableUserDefinedFunctions())
            throw new InvalidRequestException("User-defined-functions are disabled in cassandra.yaml - set enable_user_defined_functions=true to enable if you are aware of the security risks");

        switch (language)
        {
            case "java": return JavaSourceUDFFactory.buildUDF(name, argNames, argTypes, returnType, calledOnNullInput, body);
            default: return new ScriptBasedUDF(name, argNames, argTypes, returnType, calledOnNullInput, language, body);
        }
    }

    /**
     * It can happen that a function has been declared (is listed in the scheam) but cannot
     * be loaded (maybe only on some nodes). This is the case for instance if the class defining
     * the class is not on the classpath for some of the node, or after a restart. In that case,
     * we create a "fake" function so that:
     *  1) the broken function can be dropped easily if that is what people want to do.
     *  2) we return a meaningful error message if the function is executed (something more precise
     *     than saying that the function doesn't exist)
     */
    public static UDFunction createBrokenFunction(FunctionName name,
                                                  List<ColumnIdentifier> argNames,
                                                  List<AbstractType<?>> argTypes,
                                                  AbstractType<?> returnType,
                                                  boolean calledOnNullInput,
                                                  String language,
                                                  String body,
                                                  final InvalidRequestException reason)
    {
        return new UDFunction(name, argNames, argTypes, returnType, calledOnNullInput, language, body)
        {
            public ByteBuffer executeUserDefined(int protocolVersion, List<ByteBuffer> parameters) throws InvalidRequestException
            {
                throw new InvalidRequestException(String.format("Function '%s' exists but hasn't been loaded successfully "
                                                                + "for the following reason: %s. Please see the server log for details",
                                                                this,
                                                                reason.getMessage()));
            }
        };
    }

    public final ByteBuffer execute(int protocolVersion, List<ByteBuffer> parameters) throws InvalidRequestException
    {
        if (!DatabaseDescriptor.enableUserDefinedFunctions())
            throw new InvalidRequestException("User-defined-functions are disabled in cassandra.yaml - set enable_user_defined_functions=true to enable if you are aware of the security risks");

        if (!isCallableWrtNullable(parameters))
            return null;

        long tStart = System.nanoTime();
        ByteBuffer result = executeUserDefined(protocolVersion, parameters);
        Tracing.trace("Executed UDF {} in {}\u03bcs", name(), (System.nanoTime() - tStart) / 1000);
        return result;
    }

    public boolean isCallableWrtNullable(List<ByteBuffer> parameters)
    {
        if (!calledOnNullInput)
            for (int i = 0; i < parameters.size(); i++)
                if (UDHelper.isNullOrEmpty(argTypes.get(i), parameters.get(i)))
                    return false;
        return true;
    }

    protected abstract ByteBuffer executeUserDefined(int protocolVersion, List<ByteBuffer> parameters) throws InvalidRequestException;

    public boolean isAggregate()
    {
        return false;
    }

    public boolean isNative()
    {
        return false;
    }

    public boolean isCalledOnNullInput()
    {
        return calledOnNullInput;
    }

    public List<ColumnIdentifier> argNames()
    {
        return argNames;
    }

    public String body()
    {
        return body;
    }

    public String language()
    {
        return language;
    }

    /**
     * Used by UDF implementations (both Java code generated by {@link org.apache.cassandra.cql3.functions.JavaSourceUDFFactory}
     * and script executor {@link org.apache.cassandra.cql3.functions.ScriptBasedUDF}) to convert the C*
     * serialized representation to the Java object representation.
     *
     * @param protocolVersion the native protocol version used for serialization
     * @param argIndex index of the UDF input argument
     */
    protected Object compose(int protocolVersion, int argIndex, ByteBuffer value)
    {
        return UDHelper.isNullOrEmpty(argTypes.get(argIndex), value) ? null : argDataTypes[argIndex].deserialize(value, ProtocolVersion.fromInt(protocolVersion));
    }

    // do not remove - used by generated Java UDFs
    protected float compose_float(int protocolVersion, int argIndex, ByteBuffer value)
    {
        assert value != null && value.remaining() > 0;
        return (float)DataType.cfloat().deserialize(value, ProtocolVersion.fromInt(protocolVersion));
    }

    // do not remove - used by generated Java UDFs
    protected double compose_double(int protocolVersion, int argIndex, ByteBuffer value)
    {
        assert value != null && value.remaining() > 0;
        return (double)DataType.cdouble().deserialize(value, ProtocolVersion.fromInt(protocolVersion));
    }

    // do not remove - used by generated Java UDFs
    protected byte compose_byte(int protocolVersion, int argIndex, ByteBuffer value)
    {
        assert value != null && value.remaining() > 0;
        return (byte)DataType.tinyint().deserialize(value, ProtocolVersion.fromInt(protocolVersion));
    }

    // do not remove - used by generated Java UDFs
    protected short compose_short(int protocolVersion, int argIndex, ByteBuffer value)
    {
        assert value != null && value.remaining() > 0;
        return (short)DataType.smallint().deserialize(value, ProtocolVersion.fromInt(protocolVersion));
    }

    // do not remove - used by generated Java UDFs
    protected int compose_int(int protocolVersion, int argIndex, ByteBuffer value)
    {
        assert value != null && value.remaining() > 0;
        return (int)DataType.cint().deserialize(value, ProtocolVersion.fromInt(protocolVersion));
    }

    // do not remove - used by generated Java UDFs
    protected long compose_long(int protocolVersion, int argIndex, ByteBuffer value)
    {
        assert value != null && value.remaining() > 0;
        return (long)DataType.bigint().deserialize(value, ProtocolVersion.fromInt(protocolVersion));
    }

    // do not remove - used by generated Java UDFs
    protected boolean compose_boolean(int protocolVersion, int argIndex, ByteBuffer value)
    {
        assert value != null && value.remaining() > 0;
        return (boolean) DataType.cboolean().deserialize(value, ProtocolVersion.fromInt(protocolVersion));
    }

    /**
     * Used by UDF implementations (both Java code generated by {@link org.apache.cassandra.cql3.functions.JavaSourceUDFFactory}
     * and script executor {@link org.apache.cassandra.cql3.functions.ScriptBasedUDF}) to convert the Java
     * object representation for the return value to the C* serialized representation.
     *
     * @param protocolVersion the native protocol version used for serialization
     */
    protected ByteBuffer decompose(int protocolVersion, Object value)
    {
        return value == null ? null : returnDataType.serialize(value, ProtocolVersion.fromInt(protocolVersion));
    }

    @Override
    public boolean equals(Object o)
    {
        if (!(o instanceof UDFunction))
            return false;

        UDFunction that = (UDFunction)o;
        return Objects.equal(name, that.name)
            && Objects.equal(argNames, that.argNames)
            && Functions.typesMatch(argTypes, that.argTypes)
            && Functions.typesMatch(returnType, that.returnType)
            && Objects.equal(language, that.language)
            && Objects.equal(body, that.body);
    }

    @Override
    public int hashCode()
    {
        return Objects.hashCode(name, Functions.typeHashCode(argTypes), Functions.typeHashCode(returnType), returnType, language, body);
    }

    public void userTypeUpdated(String ksName, String typeName)
    {
        boolean updated = false;

        for (int i = 0; i < argDataTypes.length; i++)
        {
            DataType dataType = argDataTypes[i];
            if (dataType instanceof UserType)
            {
                UserType userType = (UserType) dataType;
                if (userType.getKeyspace().equals(ksName) && userType.getTypeName().equals(typeName))
                {
                    KeyspaceMetadata ksm = Schema.instance.getKSMetaData(ksName);
                    assert ksm != null;

                    org.apache.cassandra.db.marshal.UserType ut = ksm.types.get(ByteBufferUtil.bytes(typeName)).get();

                    DataType newUserType = UDHelper.driverType(ut);
                    argDataTypes[i] = newUserType;

                    argTypes.set(i, ut);

                    updated = true;
                }
            }
        }

        if (updated)
            MigrationManager.announceNewFunction(this, true);
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
import java.util.Collections;
import java.util.Map;
import java.util.UUID;
import java.util.concurrent.TimeUnit;
import javax.management.MBeanServer;
import javax.management.ObjectName;
import javax.management.StandardMBean;
import javax.management.remote.JMXConnectorServer;
import javax.management.remote.JMXServiceURL;
import javax.management.remote.rmi.RMIConnectorServer;

import com.codahale.metrics.Meter;
import com.codahale.metrics.MetricRegistryListener;
import com.codahale.metrics.SharedMetricRegistries;
import com.google.common.util.concurrent.Uninterruptibles;
import org.apache.cassandra.gms.Gossiper;
import org.apache.cassandra.metrics.DefaultNameFactory;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import com.addthis.metrics3.reporter.config.ReporterConfig;
import org.apache.cassandra.concurrent.*;
import org.apache.cassandra.config.CFMetaData;
import org.apache.cassandra.config.DatabaseDescriptor;
import org.apache.cassandra.config.Schema;
import org.apache.cassandra.db.*;
import org.apache.cassandra.db.commitlog.CommitLog;
import org.apache.cassandra.exceptions.ConfigurationException;
import org.apache.cassandra.exceptions.StartupException;
import org.apache.cassandra.io.FSError;
import org.apache.cassandra.io.sstable.CorruptSSTableException;
import org.apache.cassandra.io.util.FileUtils;
import org.apache.cassandra.metrics.CassandraMetricsRegistry;
import org.apache.cassandra.metrics.StorageMetrics;
import org.apache.cassandra.schema.LegacySchemaMigrator;
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
    private static JMXConnectorServer jmxServer = null;

    private static final Logger logger;
    static {
        // Need to register metrics before instrumented appender is created(first access to LoggerFactory).
        SharedMetricRegistries.getOrCreate("logback-metrics").addListener(new MetricRegistryListener.Base()
        {
            @Override
            public void onMeterAdded(String metricName, Meter meter)
            {
                // Given metricName consists of appender name in logback.xml + "." + metric name.
                // We first separate appender name
                int separator = metricName.lastIndexOf('.');
                String appenderName = metricName.substring(0, separator);
                String metric = metricName.substring(separator + 1); // remove "."
                ObjectName name = DefaultNameFactory.createMetricName(appenderName, metric, null).getMBeanName();
                CassandraMetricsRegistry.Metrics.registerMBean(meter, name);
            }
        });
        logger = LoggerFactory.getLogger(CassandraDaemon.class);
    }

    private static void maybeInitJmx()
    {
        if (System.getProperty("com.sun.management.jmxremote.port") != null)
            return;

        String jmxPort = System.getProperty("cassandra.jmx.local.port");
        if (jmxPort == null)
            return;

        System.setProperty("java.rmi.server.hostname", InetAddress.getLoopbackAddress().getHostAddress());
        RMIServerSocketFactory serverFactory = new RMIServerSocketFactoryImpl();
        Map<String, ?> env = Collections.singletonMap(RMIConnectorServer.RMI_SERVER_SOCKET_FACTORY_ATTRIBUTE, serverFactory);
        try
        {
            LocateRegistry.createRegistry(Integer.valueOf(jmxPort), null, serverFactory);
            JMXServiceURL url = new JMXServiceURL(String.format("service:jmx:rmi://localhost/jndi/rmi://localhost:%s/jmxrmi", jmxPort));
            jmxServer = new RMIConnectorServer(url, env, ManagementFactory.getPlatformMBeanServer());
            jmxServer.start();
        }
        catch (IOException e)
        {
            logger.error("Error starting local jmx server: ", e);
        }
    }

    private static final CassandraDaemon instance = new CassandraDaemon();

    public Server thriftServer;
    public Server nativeServer;

    private final boolean runManaged;
    protected final StartupChecks startupChecks;
    private boolean setupCompleted;

    public CassandraDaemon() {
        this(false);
    }

    public CassandraDaemon(boolean runManaged) {
        this.runManaged = runManaged;
        this.startupChecks = new StartupChecks().withDefaultTests();
        this.setupCompleted = false;
    }

    /**
     * This is a hook for concrete daemons to initialize themselves suitably.
     *
     * Subclasses should override this to finish the job (listening on ports, etc.)
     */
    protected void setup()
    {
        // Delete any failed snapshot deletions on Windows - see CASSANDRA-9658
        if (FBUtilities.isWindows())
            WindowsFailedSnapshotTracker.deleteOldSnapshots();

        logSystemInfo();

        CLibrary.tryMlockall();

        try
        {
            startupChecks.verify();
        }
        catch (StartupException e)
        {
            exitOrFail(e.returnCode, e.getMessage(), e.getCause());
        }

        try
        {
            SystemKeyspace.snapshotOnVersionChange();
        }
        catch (IOException e)
        {
            exitOrFail(3, e.getMessage(), e.getCause());
        }

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

        /*
         * Migrate pre-3.0 keyspaces, tables, types, functions, and aggregates, to their new 3.0 storage.
         * We don't (and can't) wait for commit log replay here, but we don't need to - all schema changes force
         * explicit memtable flushes.
         */
        LegacySchemaMigrator.migrate();

        StorageService.instance.populateTokenMetadata();

        // load schema from disk
        Schema.instance.loadFromDisk();

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
            if (keyspaceName.equals(SystemKeyspace.NAME))
                continue;

            for (CFMetaData cfm : Schema.instance.getTables(keyspaceName))
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
                    if (store.getCompactionStrategyManager().shouldBeEnabled())
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
            System.err.println(e.getMessage() + "\nFatal configuration error; unable to start server.  See log for stacktrace.");
            exitOrFail(1, "Fatal configuration error", e);
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
                ReporterConfig.loadFromFile(reportFileLocation).enableAll(CassandraMetricsRegistry.Metrics);
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

    private void logSystemInfo()
    {
    	if (logger.isInfoEnabled())
    	{
	        try
	        {
	            logger.info("Hostname: {}", InetAddress.getLocalHost().getHostName());
	        }
	        catch (UnknownHostException e1)
	        {
	            logger.info("Could not resolve local host");
	        }
	
	        logger.info("JVM vendor/version: {}/{}", System.getProperty("java.vm.name"), System.getProperty("java.version"));
	        logger.info("Heap size: {}/{}", Runtime.getRuntime().totalMemory(), Runtime.getRuntime().maxMemory());
	
	        for(MemoryPoolMXBean pool: ManagementFactory.getMemoryPoolMXBeans())
	            logger.info("{} {}: {}", pool.getName(), pool.getType(), pool.getPeakUsage());
	
	        logger.info("Classpath: {}", System.getProperty("java.class.path"));
    	}
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
        {
            nativeServer.start();
        }
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

        if (FBUtilities.isWindows())
        {
            // We need to adjust the system timer on windows from the default 15ms down to the minimum of 1ms as this
            // impacts timer intervals, thread scheduling, driver interrupts, etc.
            WindowsTimer.startTimerPeriod(DatabaseDescriptor.getWindowsTimerInterval());
        }

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

            try {
                DatabaseDescriptor.forceStaticInitialization();
            } catch (ExceptionInInitializerError e) {
                throw e.getCause();
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
            boolean logStackTrace =
                    e instanceof ConfigurationException ? ((ConfigurationException)e).logStackTrace : true;

            System.out.println("Exception (" + e.getClass().getName() + ") encountered during startup: " + e.getMessage());

            if (logStackTrace)
            {
                if (runManaged)
                    logger.error("Exception encountered during startup", e);
                // try to warn user on stdout too, if we haven't already detached
                e.printStackTrace();
                exitOrFail(3, "Exception encountered during startup", e);
            }
            else
            {
                if (runManaged)
                    logger.error("Exception encountered during startup: {}", e.getMessage());
                // try to warn user on stdout too, if we haven't already detached
                System.err.println(e.getMessage());
                exitOrFail(3, "Exception encountered during startup: " + e.getMessage());
            }
        }
    }

    /**
     * A convenience method to stop and destroy the daemon in one shot.
     */
    public void deactivate()
    {
        stop();
        destroy();
        // completely shut down cassandra
        if(!runManaged) {
            System.exit(0);
        }
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
        int epSize = Gossiper.instance.getEndpointStates().size();
        while (numOkay < GOSSIP_SETTLE_POLL_SUCCESSES_REQUIRED)
        {
            Uninterruptibles.sleepUninterruptibly(GOSSIP_SETTLE_POLL_INTERVAL_MS, TimeUnit.MILLISECONDS);
            int currentSize = Gossiper.instance.getEndpointStates().size();
            totalPolls++;
            if (currentSize == epSize)
            {
                logger.debug("Gossip looks settled.");
                numOkay++;
            }
            else
            {
                logger.info("Gossip not settled after {} polls.", totalPolls);
                numOkay = 0;
            }
            epSize = currentSize;
            if (forceAfter > 0 && totalPolls > forceAfter)
            {
                logger.warn("Gossip not settled but startup forced by cassandra.skip_wait_for_gossip_to_settle. Gossip total polls: {}",
                            totalPolls);
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

    private void exitOrFail(int code, String message) {
        exitOrFail(code, message, null);
    }

    private void exitOrFail(int code, String message, Throwable cause) {
            if(runManaged) {
                RuntimeException t = cause!=null ? new RuntimeException(message, cause) : new RuntimeException(message);
                throw t;
            }
            else {
                logger.error(message, cause);
                System.exit(code);
            }

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


File: src/java/org/apache/cassandra/utils/JVMStabilityInspector.java
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
package org.apache.cassandra.utils;

import java.io.FileNotFoundException;
import java.net.SocketException;

import com.google.common.annotations.VisibleForTesting;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import org.apache.cassandra.config.Config;
import org.apache.cassandra.config.DatabaseDescriptor;
import org.apache.cassandra.io.FSError;
import org.apache.cassandra.io.sstable.CorruptSSTableException;
import org.apache.cassandra.service.StorageService;

/**
 * Responsible for deciding whether to kill the JVM if it gets in an "unstable" state (think OOM).
 */
public final class JVMStabilityInspector
{
    private static final Logger logger = LoggerFactory.getLogger(JVMStabilityInspector.class);
    private static Killer killer = new Killer();

    private JVMStabilityInspector() {}

    /**
     * Certain Throwables and Exceptions represent "Die" conditions for the server.
     * @param t
     *      The Throwable to check for server-stop conditions
     */
    public static void inspectThrowable(Throwable t)
    {
        boolean isUnstable = false;
        if (t instanceof OutOfMemoryError)
            isUnstable = true;

        if (DatabaseDescriptor.getDiskFailurePolicy() == Config.DiskFailurePolicy.die)
            if (t instanceof FSError || t instanceof CorruptSSTableException)
            isUnstable = true;

        // Check for file handle exhaustion
        if (t instanceof FileNotFoundException || t instanceof SocketException)
            if (t.getMessage().contains("Too many open files"))
                isUnstable = true;

        if (isUnstable)
            killer.killCurrentJVM(t);
    }

    public static void inspectCommitLogThrowable(Throwable t)
    {
        if (DatabaseDescriptor.getCommitFailurePolicy() == Config.CommitFailurePolicy.die)
            killer.killCurrentJVM(t);
        else
            inspectThrowable(t);
    }

    public static void killCurrentJVM(Throwable t, boolean quiet)
    {
        killer.killCurrentJVM(t, quiet);
    }

    @VisibleForTesting
    public static Killer replaceKiller(Killer newKiller) {
        Killer oldKiller = JVMStabilityInspector.killer;
        JVMStabilityInspector.killer = newKiller;
        return oldKiller;
    }

    @VisibleForTesting
    public static class Killer
    {
        /**
        * Certain situations represent "Die" conditions for the server, and if so, the reason is logged and the current JVM is killed.
        *
        * @param t
        *      The Throwable to log before killing the current JVM
        */
        protected void killCurrentJVM(Throwable t)
        {
            killCurrentJVM(t, false);
        }

        protected void killCurrentJVM(Throwable t, boolean quiet)
        {
            if (!quiet)
            {
                t.printStackTrace(System.err);
                logger.error("JVM state determined to be unstable.  Exiting forcefully due to:", t);
            }
            StorageService.instance.removeShutdownHook();
            System.exit(100);
        }
    }
}


File: test/unit/org/apache/cassandra/SchemaLoader.java
/*
 * Licensed to the Apache Software Foundation (ASF) under one
 * or more contributor license agreements.  See the NOTICE file
 * distributed with this work for additional information
 * regarding copyright ownership.  The ASF licenses this file
 * to you under the Apache License, Version 2.0 (the
 * "License"); you may not use this file except in compliance
 * with the License.  You may obtain a copy of the License at
 * <p/>
 * http://www.apache.org/licenses/LICENSE-2.0
 * <p/>
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 */
package org.apache.cassandra;

import java.io.File;
import java.io.IOException;
import java.util.*;

import org.junit.After;
import org.junit.BeforeClass;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import org.apache.cassandra.cache.CachingOptions;
import org.apache.cassandra.config.*;
import org.apache.cassandra.cql3.CQLTester;
import org.apache.cassandra.cql3.ColumnIdentifier;
import org.apache.cassandra.db.*;
import org.apache.cassandra.db.commitlog.CommitLog;
import org.apache.cassandra.db.compaction.LeveledCompactionStrategy;
import org.apache.cassandra.db.index.PerRowSecondaryIndexTest;
import org.apache.cassandra.db.index.SecondaryIndex;
import org.apache.cassandra.db.marshal.*;
import org.apache.cassandra.exceptions.ConfigurationException;
import org.apache.cassandra.gms.Gossiper;
import org.apache.cassandra.io.compress.CompressionParameters;
import org.apache.cassandra.io.compress.SnappyCompressor;
import org.apache.cassandra.io.util.FileUtils;
import org.apache.cassandra.schema.KeyspaceMetadata;
import org.apache.cassandra.schema.KeyspaceParams;
import org.apache.cassandra.schema.Tables;
import org.apache.cassandra.service.MigrationManager;
import org.apache.cassandra.utils.ByteBufferUtil;
import org.apache.cassandra.utils.FBUtilities;

public class SchemaLoader
{
    private static Logger logger = LoggerFactory.getLogger(SchemaLoader.class);

    @BeforeClass
    public static void loadSchema() throws ConfigurationException
    {
        prepareServer();

        // Migrations aren't happy if gossiper is not started.  Even if we don't use migrations though,
        // some tests now expect us to start gossip for them.
        startGossiper();
    }

    @After
    public void leakDetect() throws InterruptedException
    {
        System.gc();
        System.gc();
        System.gc();
        Thread.sleep(10);
    }

    public static void prepareServer()
    {
       CQLTester.prepareServer(false);
    }

    public static void startGossiper()
    {
        if (!Gossiper.instance.isEnabled())
            Gossiper.instance.start((int) (System.currentTimeMillis() / 1000));
    }

    public static void schemaDefinition(String testName) throws ConfigurationException
    {
        List<KeyspaceMetadata> schema = new ArrayList<KeyspaceMetadata>();

        // A whole bucket of shorthand
        String ks1 = testName + "Keyspace1";
        String ks2 = testName + "Keyspace2";
        String ks3 = testName + "Keyspace3";
        String ks4 = testName + "Keyspace4";
        String ks5 = testName + "Keyspace5";
        String ks6 = testName + "Keyspace6";
        String ks_kcs = testName + "KeyCacheSpace";
        String ks_rcs = testName + "RowCacheSpace";
        String ks_ccs = testName + "CounterCacheSpace";
        String ks_nocommit = testName + "NoCommitlogSpace";
        String ks_prsi = testName + "PerRowSecondaryIndex";
        String ks_cql = testName + "cql_keyspace";

        AbstractType bytes = BytesType.instance;

        AbstractType<?> composite = CompositeType.getInstance(Arrays.asList(new AbstractType<?>[]{BytesType.instance, TimeUUIDType.instance, IntegerType.instance}));
        AbstractType<?> compositeMaxMin = CompositeType.getInstance(Arrays.asList(new AbstractType<?>[]{BytesType.instance, IntegerType.instance}));
        Map<Byte, AbstractType<?>> aliases = new HashMap<Byte, AbstractType<?>>();
        aliases.put((byte)'b', BytesType.instance);
        aliases.put((byte)'t', TimeUUIDType.instance);
        aliases.put((byte)'B', ReversedType.getInstance(BytesType.instance));
        aliases.put((byte)'T', ReversedType.getInstance(TimeUUIDType.instance));
        AbstractType<?> dynamicComposite = DynamicCompositeType.getInstance(aliases);

        // Make it easy to test compaction
        Map<String, String> compactionOptions = new HashMap<String, String>();
        compactionOptions.put("tombstone_compaction_interval", "1");
        Map<String, String> leveledOptions = new HashMap<String, String>();
        leveledOptions.put("sstable_size_in_mb", "1");

        // Keyspace 1
        schema.add(KeyspaceMetadata.create(ks1,
                KeyspaceParams.simple(1),
                Tables.of(
                // Column Families
                standardCFMD(ks1, "Standard1").compactionStrategyOptions(compactionOptions),
                standardCFMD(ks1, "Standard2"),
                standardCFMD(ks1, "Standard3"),
                standardCFMD(ks1, "Standard4"),
                standardCFMD(ks1, "StandardGCGS0").gcGraceSeconds(0),
                standardCFMD(ks1, "StandardLong1"),
                standardCFMD(ks1, "StandardLong2"),
                //CFMetaData.Builder.create(ks1, "ValuesWithQuotes").build(),
                superCFMD(ks1, "Super1", LongType.instance),
                superCFMD(ks1, "Super2", LongType.instance),
                superCFMD(ks1, "Super3", LongType.instance),
                superCFMD(ks1, "Super4", UTF8Type.instance),
                superCFMD(ks1, "Super5", bytes),
                superCFMD(ks1, "Super6", LexicalUUIDType.instance, UTF8Type.instance),
                keysIndexCFMD(ks1, "Indexed1", true),
                keysIndexCFMD(ks1, "Indexed2", false),
                //CFMetaData.Builder.create(ks1, "StandardInteger1").withColumnNameComparator(IntegerType.instance).build(),
                //CFMetaData.Builder.create(ks1, "StandardLong3").withColumnNameComparator(IntegerType.instance).build(),
                //CFMetaData.Builder.create(ks1, "Counter1", false, false, true).build(),
                //CFMetaData.Builder.create(ks1, "SuperCounter1", false, false, true, true).build(),
                superCFMD(ks1, "SuperDirectGC", BytesType.instance).gcGraceSeconds(0),
//                jdbcCFMD(ks1, "JdbcInteger", IntegerType.instance).addColumnDefinition(integerColumn(ks1, "JdbcInteger")),
                jdbcCFMD(ks1, "JdbcUtf8", UTF8Type.instance).addColumnDefinition(utf8Column(ks1, "JdbcUtf8")),
                jdbcCFMD(ks1, "JdbcLong", LongType.instance),
                jdbcCFMD(ks1, "JdbcBytes", bytes),
                jdbcCFMD(ks1, "JdbcAscii", AsciiType.instance),
                //CFMetaData.Builder.create(ks1, "StandardComposite", false, true, false).withColumnNameComparator(composite).build(),
                //CFMetaData.Builder.create(ks1, "StandardComposite2", false, true, false).withColumnNameComparator(compositeMaxMin).build(),
                //CFMetaData.Builder.create(ks1, "StandardDynamicComposite", false, true, false).withColumnNameComparator(dynamicComposite).build(),
                standardCFMD(ks1, "StandardLeveled")
                        .compactionStrategyClass(LeveledCompactionStrategy.class)
                        .compactionStrategyOptions(leveledOptions),
                standardCFMD(ks1, "legacyleveled")
                        .compactionStrategyClass(LeveledCompactionStrategy.class)
                        .compactionStrategyOptions(leveledOptions),
                standardCFMD(ks1, "StandardLowIndexInterval").minIndexInterval(8)
                        .maxIndexInterval(256)
                        .caching(CachingOptions.NONE)
                //CFMetaData.Builder.create(ks1, "UUIDKeys").addPartitionKey("key",UUIDType.instance).build(),
                //CFMetaData.Builder.create(ks1, "MixedTypes").withColumnNameComparator(LongType.instance).addPartitionKey("key", UUIDType.instance).build(),
                //CFMetaData.Builder.create(ks1, "MixedTypesComposite", false, true, false).withColumnNameComparator(composite).addPartitionKey("key", composite).build(),
                //CFMetaData.Builder.create(ks1, "AsciiKeys").addPartitionKey("key", AsciiType.instance).build()
        )));

        // Keyspace 2
        schema.add(KeyspaceMetadata.create(ks2,
                KeyspaceParams.simple(1),
                Tables.of(
                // Column Families
                standardCFMD(ks2, "Standard1"),
                standardCFMD(ks2, "Standard3"),
                superCFMD(ks2, "Super3", bytes),
                superCFMD(ks2, "Super4", TimeUUIDType.instance),
                keysIndexCFMD(ks2, "Indexed1", true),
                compositeIndexCFMD(ks2, "Indexed2", true),
                compositeIndexCFMD(ks2, "Indexed3", true).gcGraceSeconds(0))));

        // Keyspace 3
        schema.add(KeyspaceMetadata.create(ks3,
                KeyspaceParams.simple(5),
                Tables.of(
                standardCFMD(ks3, "Standard1"),
                keysIndexCFMD(ks3, "Indexed1", true))));

        // Keyspace 4
        schema.add(KeyspaceMetadata.create(ks4,
                KeyspaceParams.simple(3),
                Tables.of(
                standardCFMD(ks4, "Standard1"),
                standardCFMD(ks4, "Standard3"),
                superCFMD(ks4, "Super3", bytes),
                superCFMD(ks4, "Super4", TimeUUIDType.instance),
                superCFMD(ks4, "Super5", TimeUUIDType.instance, BytesType.instance))));

        // Keyspace 5
        schema.add(KeyspaceMetadata.create(ks5,
                KeyspaceParams.simple(2),
                Tables.of(standardCFMD(ks5, "Standard1"))));
        // Keyspace 6
        schema.add(KeyspaceMetadata.create(ks6,
                KeyspaceParams.simple(1),
                Tables.of(keysIndexCFMD(ks6, "Indexed1", true))));

        // KeyCacheSpace
        schema.add(KeyspaceMetadata.create(ks_kcs,
                KeyspaceParams.simple(1),
                Tables.of(
                standardCFMD(ks_kcs, "Standard1"),
                standardCFMD(ks_kcs, "Standard2"),
                standardCFMD(ks_kcs, "Standard3"))));

        // RowCacheSpace
        schema.add(KeyspaceMetadata.create(ks_rcs,
                KeyspaceParams.simple(1),
                Tables.of(
                standardCFMD(ks_rcs, "CFWithoutCache").caching(CachingOptions.NONE),
                standardCFMD(ks_rcs, "CachedCF").caching(CachingOptions.ALL),
                standardCFMD(ks_rcs, "CachedIntCF").
                        caching(new CachingOptions(new CachingOptions.KeyCache(CachingOptions.KeyCache.Type.ALL),
                                new CachingOptions.RowCache(CachingOptions.RowCache.Type.HEAD, 100))))));

        // CounterCacheSpace
        /*schema.add(KeyspaceMetadata.testMetadata(ks_ccs,
                simple,
                opts_rf1,
                CFMetaData.Builder.create(ks_ccs, "Counter1", false, false, true).build(),
                CFMetaData.Builder.create(ks_ccs, "Counter1", false, false, true).build()));*/

        schema.add(KeyspaceMetadata.create(ks_nocommit, KeyspaceParams.simpleTransient(1), Tables.of(
                standardCFMD(ks_nocommit, "Standard1"))));

        // PerRowSecondaryIndexTest
        schema.add(KeyspaceMetadata.create(ks_prsi, KeyspaceParams.simple(1), Tables.of(
                perRowIndexedCFMD(ks_prsi, "Indexed1"))));

        // CQLKeyspace
        schema.add(KeyspaceMetadata.create(ks_cql, KeyspaceParams.simple(1), Tables.of(

                // Column Families
                CFMetaData.compile("CREATE TABLE table1 ("
                        + "k int PRIMARY KEY,"
                        + "v1 text,"
                        + "v2 int"
                        + ")", ks_cql),

                CFMetaData.compile("CREATE TABLE table2 ("
                        + "k text,"
                        + "c text,"
                        + "v text,"
                        + "PRIMARY KEY (k, c))", ks_cql),
                CFMetaData.compile("CREATE TABLE foo ("
                        + "bar text, "
                        + "baz text, "
                        + "qux text, "
                        + "PRIMARY KEY(bar, baz) ) "
                        + "WITH COMPACT STORAGE", ks_cql),
                CFMetaData.compile("CREATE TABLE foofoo ("
                        + "bar text, "
                        + "baz text, "
                        + "qux text, "
                        + "quz text, "
                        + "foo text, "
                        + "PRIMARY KEY((bar, baz), qux, quz) ) "
                        + "WITH COMPACT STORAGE", ks_cql)
        )));


        if (Boolean.parseBoolean(System.getProperty("cassandra.test.compression", "false")))
            useCompression(schema);

        // if you're messing with low-level sstable stuff, it can be useful to inject the schema directly
        // Schema.instance.load(schemaDefinition());
        for (KeyspaceMetadata ksm : schema)
            MigrationManager.announceNewKeyspace(ksm, false);
    }

    public static void createKeyspace(String name, KeyspaceParams params, CFMetaData... tables)
    {
        MigrationManager.announceNewKeyspace(KeyspaceMetadata.create(name, params, Tables.of(tables)), true);
    }

    public static ColumnDefinition integerColumn(String ksName, String cfName)
    {
        return new ColumnDefinition(ksName,
                                    cfName,
                                    ColumnIdentifier.getInterned(IntegerType.instance.fromString("42"), IntegerType.instance),
                                    UTF8Type.instance,
                                    null,
                                    null,
                                    null,
                                    null,
                                    ColumnDefinition.Kind.REGULAR);
    }

    public static ColumnDefinition utf8Column(String ksName, String cfName)
    {
        return new ColumnDefinition(ksName,
                                    cfName,
                                    ColumnIdentifier.getInterned("fortytwo", true),
                                    UTF8Type.instance,
                                    null,
                                    null,
                                    null,
                                    null,
                                    ColumnDefinition.Kind.REGULAR);
    }

    public static CFMetaData perRowIndexedCFMD(String ksName, String cfName)
    {
        final Map<String, String> indexOptions = Collections.singletonMap(
                                                      SecondaryIndex.CUSTOM_INDEX_OPTION_NAME,
                                                      PerRowSecondaryIndexTest.TestIndex.class.getName());

        CFMetaData cfm =  CFMetaData.Builder.create(ksName, cfName)
                .addPartitionKey("key", AsciiType.instance)
                .build();

        return cfm.addOrReplaceColumnDefinition(ColumnDefinition.regularDef(ksName, cfName, "indexed", AsciiType.instance)
                                                                .setIndex("indexe1", IndexType.CUSTOM, indexOptions));
    }

    private static void useCompression(List<KeyspaceMetadata> schema)
    {
        for (KeyspaceMetadata ksm : schema)
            for (CFMetaData cfm : ksm.tables)
                cfm.compressionParameters(CompressionParameters.snappy());
    }

    public static CFMetaData counterCFMD(String ksName, String cfName)
    {
        return CFMetaData.Builder.create(ksName, cfName, false, true, true)
                .addPartitionKey("key", AsciiType.instance)
                .addClusteringColumn("name", AsciiType.instance)
                .addRegularColumn("val", CounterColumnType.instance)
                .addRegularColumn("val2", CounterColumnType.instance)
                .build()
                .compressionParameters(getCompressionParameters());
    }

    public static CFMetaData standardCFMD(String ksName, String cfName)
    {
        return standardCFMD(ksName, cfName, 1, AsciiType.instance);
    }

    public static CFMetaData standardCFMD(String ksName, String cfName, int columnCount, AbstractType<?> keyType)
    {
        return standardCFMD(ksName, cfName, columnCount, keyType, AsciiType.instance);
    }

    public static CFMetaData standardCFMD(String ksName, String cfName, int columnCount, AbstractType<?> keyType, AbstractType<?> valType)
    {
        return standardCFMD(ksName, cfName, columnCount, keyType, valType, AsciiType.instance);
    }

    public static CFMetaData standardCFMD(String ksName, String cfName, int columnCount, AbstractType<?> keyType, AbstractType<?> valType, AbstractType<?> clusteringType)
    {
        CFMetaData.Builder builder = CFMetaData.Builder.create(ksName, cfName)
                .addPartitionKey("key", keyType)
                .addClusteringColumn("name", clusteringType)
                .addRegularColumn("val", valType);

        for (int i = 0; i < columnCount; i++)
            builder.addRegularColumn("val" + i, AsciiType.instance);

        return builder.build()
               .compressionParameters(getCompressionParameters());
    }

    public static CFMetaData denseCFMD(String ksName, String cfName)
    {
        return denseCFMD(ksName, cfName, AsciiType.instance);
    }
    public static CFMetaData denseCFMD(String ksName, String cfName, AbstractType cc)
    {
        return denseCFMD(ksName, cfName, cc, null);
    }
    public static CFMetaData denseCFMD(String ksName, String cfName, AbstractType cc, AbstractType subcc)
    {
        AbstractType comp = cc;
        if (subcc != null)
            comp = CompositeType.getInstance(Arrays.asList(new AbstractType<?>[]{cc, subcc}));

        return CFMetaData.Builder.createDense(ksName, cfName, subcc != null, false)
            .addPartitionKey("key", AsciiType.instance)
            .addClusteringColumn("cols", comp)
            .addRegularColumn("val", AsciiType.instance)
            .build()
            .compressionParameters(getCompressionParameters());
    }

    // TODO: Fix superCFMD failing on legacy table creation. Seems to be applying composite comparator to partition key
    public static CFMetaData superCFMD(String ksName, String cfName, AbstractType subcc)
    {
        return superCFMD(ksName, cfName, BytesType.instance, subcc);
    }
    public static CFMetaData superCFMD(String ksName, String cfName, AbstractType cc, AbstractType subcc)
    {
        return superCFMD(ksName, cfName, "cols", cc, subcc);
    }
    public static CFMetaData superCFMD(String ksName, String cfName, String ccName, AbstractType cc, AbstractType subcc)
    {
        //This is busted
//        return CFMetaData.Builder.createSuper(ksName, cfName, false)
//            .addPartitionKey("0", BytesType.instance)
//            .addClusteringColumn("1", cc)
//            .addClusteringColumn("2", subcc)
//            .addRegularColumn("3", AsciiType.instance)
//            .build();
        return standardCFMD(ksName, cfName);

    }
    public static CFMetaData compositeIndexCFMD(String ksName, String cfName, boolean withIndex) throws ConfigurationException
    {
        // the withIndex flag exists to allow tests index creation
        // on existing columns
        CFMetaData cfm = CFMetaData.Builder.create(ksName, cfName)
                .addPartitionKey("key", AsciiType.instance)
                .addClusteringColumn("c1", AsciiType.instance)
                .addRegularColumn("birthdate", LongType.instance)
                .addRegularColumn("notbirthdate", LongType.instance)
                .build();

        if (withIndex)
            cfm.getColumnDefinition(new ColumnIdentifier("birthdate", true))
               .setIndex("birthdate_key_index", IndexType.COMPOSITES, Collections.EMPTY_MAP);

        return cfm.compressionParameters(getCompressionParameters());
    }
    public static CFMetaData keysIndexCFMD(String ksName, String cfName, boolean withIndex) throws ConfigurationException
    {
        CFMetaData cfm = CFMetaData.Builder.createDense(ksName, cfName, false, false)
                                           .addPartitionKey("key", AsciiType.instance)
                                           .addClusteringColumn("c1", AsciiType.instance)
                                           .addStaticColumn("birthdate", LongType.instance)
                                           .addStaticColumn("notbirthdate", LongType.instance)
                                           .addRegularColumn("value", LongType.instance)
                                           .build();

        if (withIndex)
            cfm.getColumnDefinition(new ColumnIdentifier("birthdate", true))
               .setIndex("birthdate_composite_index", IndexType.KEYS, Collections.EMPTY_MAP);

        return cfm.compressionParameters(getCompressionParameters());
    }
    
    public static CFMetaData jdbcCFMD(String ksName, String cfName, AbstractType comp)
    {
        return CFMetaData.Builder.create(ksName, cfName).addPartitionKey("key", BytesType.instance)
                                                        .build()
                                                        .compressionParameters(getCompressionParameters());
    }

    public static CompressionParameters getCompressionParameters()
    {
        return getCompressionParameters(null);
    }

    public static CompressionParameters getCompressionParameters(Integer chunkSize)
    {
        if (Boolean.parseBoolean(System.getProperty("cassandra.test.compression", "false")))
            return CompressionParameters.snappy(chunkSize);

        return CompressionParameters.noCompression();
    }

    public static void cleanupAndLeaveDirs() throws IOException
    {
        // We need to stop and unmap all CLS instances prior to cleanup() or we'll get failures on Windows.
        CommitLog.instance.stopUnsafe(true);
        mkdirs();
        cleanup();
        mkdirs();
        CommitLog.instance.startUnsafe();
    }

    public static void cleanup()
    {
        // clean up commitlog
        String[] directoryNames = { DatabaseDescriptor.getCommitLogLocation(), };
        for (String dirName : directoryNames)
        {
            File dir = new File(dirName);
            if (!dir.exists())
                throw new RuntimeException("No such directory: " + dir.getAbsolutePath());

            // Leave the folder around as Windows will complain about directory deletion w/handles open to children files
            String[] children = dir.list();
            for (String child : children)
                FileUtils.deleteRecursive(new File(dir, child));
        }

        cleanupSavedCaches();

        // clean up data directory which are stored as data directory/keyspace/data files
        for (String dirName : DatabaseDescriptor.getAllDataFileLocations())
        {
            File dir = new File(dirName);
            if (!dir.exists())
                throw new RuntimeException("No such directory: " + dir.getAbsolutePath());
            String[] children = dir.list();
            for (String child : children)
                FileUtils.deleteRecursive(new File(dir, child));
        }
    }

    public static void mkdirs()
    {
        DatabaseDescriptor.createAllDirectories();
    }

    public static void insertData(String keyspace, String columnFamily, int offset, int numberOfRows)
    {
        CFMetaData cfm = Schema.instance.getCFMetaData(keyspace, columnFamily);

        for (int i = offset; i < offset + numberOfRows; i++)
        {
            RowUpdateBuilder builder = new RowUpdateBuilder(cfm, FBUtilities.timestampMicros(), ByteBufferUtil.bytes("key"+i));
            builder.clustering(ByteBufferUtil.bytes("col"+ i)).add("val", ByteBufferUtil.bytes("val" + i));
            builder.build().apply();
        }
    }

    public static void cleanupSavedCaches()
    {
        File cachesDir = new File(DatabaseDescriptor.getSavedCachesLocation());

        if (!cachesDir.exists() || !cachesDir.isDirectory())
            return;

        FileUtils.delete(cachesDir.listFiles());
    }
}


File: test/unit/org/apache/cassandra/cql3/CQLTester.java
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
package org.apache.cassandra.cql3;

import java.io.File;
import java.io.IOException;
import java.math.BigDecimal;
import java.math.BigInteger;
import java.net.InetAddress;
import java.net.ServerSocket;
import java.nio.ByteBuffer;
import java.util.*;
import java.util.concurrent.CountDownLatch;
import java.util.concurrent.ExecutionException;
import java.util.concurrent.TimeUnit;
import java.util.concurrent.atomic.AtomicInteger;

import com.datastax.driver.core.*;
import com.datastax.driver.core.ResultSet;
import com.google.common.base.Objects;
import com.google.common.collect.ImmutableSet;
import org.junit.*;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import org.apache.cassandra.SchemaLoader;
import org.apache.cassandra.concurrent.ScheduledExecutors;
import org.apache.cassandra.config.CFMetaData;
import org.apache.cassandra.config.DatabaseDescriptor;
import org.apache.cassandra.config.Schema;
import org.apache.cassandra.cql3.functions.FunctionName;
import org.apache.cassandra.cql3.statements.ParsedStatement;
import org.apache.cassandra.db.*;
import org.apache.cassandra.db.commitlog.CommitLog;
import org.apache.cassandra.db.marshal.*;
import org.apache.cassandra.db.marshal.TupleType;
import org.apache.cassandra.dht.Murmur3Partitioner;
import org.apache.cassandra.exceptions.*;
import org.apache.cassandra.gms.Gossiper;
import org.apache.cassandra.io.util.FileUtils;
import org.apache.cassandra.serializers.TypeSerializer;
import org.apache.cassandra.service.ClientState;
import org.apache.cassandra.service.QueryState;
import org.apache.cassandra.service.StorageService;
import org.apache.cassandra.transport.Event;
import org.apache.cassandra.transport.Server;
import org.apache.cassandra.transport.messages.ResultMessage;
import org.apache.cassandra.utils.ByteBufferUtil;

import static junit.framework.Assert.assertNotNull;

/**
 * Base class for CQL tests.
 */
public abstract class CQLTester
{
    protected static final Logger logger = LoggerFactory.getLogger(CQLTester.class);

    public static final String KEYSPACE = "cql_test_keyspace";
    public static final String KEYSPACE_PER_TEST = "cql_test_keyspace_alt";
    protected static final boolean USE_PREPARED_VALUES = Boolean.valueOf(System.getProperty("cassandra.test.use_prepared", "true"));
    protected static final long ROW_CACHE_SIZE_IN_MB = Integer.valueOf(System.getProperty("cassandra.test.row_cache_size_in_mb", "0"));
    private static final AtomicInteger seqNumber = new AtomicInteger();

    private static org.apache.cassandra.transport.Server server;
    protected static final int nativePort;
    protected static final InetAddress nativeAddr;
    private static final Cluster[] cluster;
    private static final Session[] session;

    private static boolean isServerPrepared = false;

    public static int maxProtocolVersion;
    static
    {
        int version;
        for (version = 1; version <= Server.CURRENT_VERSION; )
        {
            try
            {
                ProtocolVersion.fromInt(++version);
            }
            catch (IllegalArgumentException e)
            {
                version--;
                break;
            }
        }
        maxProtocolVersion = version;
        cluster = new Cluster[maxProtocolVersion];
        session = new Session[maxProtocolVersion];

        // Once per-JVM is enough
        prepareServer(true);

        nativeAddr = InetAddress.getLoopbackAddress();

        try
        {
            try (ServerSocket serverSocket = new ServerSocket(0))
            {
                nativePort = serverSocket.getLocalPort();
            }
            Thread.sleep(250);
        }
        catch (Exception e)
        {
            throw new RuntimeException(e);
        }
    }

    public static ResultMessage lastSchemaChangeResult;

    private List<String> tables = new ArrayList<>();
    private List<String> types = new ArrayList<>();
    private List<String> functions = new ArrayList<>();
    private List<String> aggregates = new ArrayList<>();

    // We don't use USE_PREPARED_VALUES in the code below so some test can foce value preparation (if the result
    // is not expected to be the same without preparation)
    private boolean usePrepared = USE_PREPARED_VALUES;

    public static void prepareServer(boolean checkInit)
    {
        if (checkInit && isServerPrepared)
            return;

        // Cleanup first
        try
        {
            cleanupAndLeaveDirs();
        }
        catch (IOException e)
        {
            logger.error("Failed to cleanup and recreate directories.");
            throw new RuntimeException(e);
        }

        Thread.setDefaultUncaughtExceptionHandler(new Thread.UncaughtExceptionHandler()
        {
            public void uncaughtException(Thread t, Throwable e)
            {
                logger.error("Fatal exception in thread " + t, e);
            }
        });

        Keyspace.setInitialized();
        isServerPrepared = true;
    }

    public static void cleanupAndLeaveDirs() throws IOException
    {
        // We need to stop and unmap all CLS instances prior to cleanup() or we'll get failures on Windows.
        CommitLog.instance.stopUnsafe(true);
        mkdirs();
        cleanup();
        mkdirs();
        CommitLog.instance.startUnsafe();
    }

    public static void cleanup()
    {
        // clean up commitlog
        String[] directoryNames = { DatabaseDescriptor.getCommitLogLocation(), };
        for (String dirName : directoryNames)
        {
            File dir = new File(dirName);
            if (!dir.exists())
                throw new RuntimeException("No such directory: " + dir.getAbsolutePath());
            FileUtils.deleteRecursive(dir);
        }

        cleanupSavedCaches();

        // clean up data directory which are stored as data directory/keyspace/data files
        for (String dirName : DatabaseDescriptor.getAllDataFileLocations())
        {
            File dir = new File(dirName);
            if (!dir.exists())
                throw new RuntimeException("No such directory: " + dir.getAbsolutePath());
            FileUtils.deleteRecursive(dir);
        }
    }

    public static void mkdirs()
    {
        DatabaseDescriptor.createAllDirectories();
    }

    public static void cleanupSavedCaches()
    {
        File cachesDir = new File(DatabaseDescriptor.getSavedCachesLocation());

        if (!cachesDir.exists() || !cachesDir.isDirectory())
            return;

        FileUtils.delete(cachesDir.listFiles());
    }

    @BeforeClass
    public static void setUpClass()
    {
        if (ROW_CACHE_SIZE_IN_MB > 0)
            DatabaseDescriptor.setRowCacheSizeInMB(ROW_CACHE_SIZE_IN_MB);

        StorageService.instance.setPartitionerUnsafe(Murmur3Partitioner.instance);
    }

    @AfterClass
    public static void tearDownClass()
    {
        for (Session sess : session)
            if (sess != null)
                sess.close();
        for (Cluster cl : cluster)
            if (cl != null)
                cl.close();

        if (server != null)
            server.stop();
    }

    @Before
    public void beforeTest() throws Throwable
    {
        schemaChange(String.format("CREATE KEYSPACE IF NOT EXISTS %s WITH replication = {'class': 'SimpleStrategy', 'replication_factor': '1'}", KEYSPACE));
        schemaChange(String.format("CREATE KEYSPACE IF NOT EXISTS %s WITH replication = {'class': 'SimpleStrategy', 'replication_factor': '1'}", KEYSPACE_PER_TEST));
    }

    @After
    public void afterTest() throws Throwable
    {
        dropPerTestKeyspace();

        // Restore standard behavior in case it was changed
        usePrepared = USE_PREPARED_VALUES;

        final List<String> tablesToDrop = copy(tables);
        final List<String> typesToDrop = copy(types);
        final List<String> functionsToDrop = copy(functions);
        final List<String> aggregatesToDrop = copy(aggregates);
        tables = null;
        types = null;
        functions = null;
        aggregates = null;

        // We want to clean up after the test, but dropping a table is rather long so just do that asynchronously
        ScheduledExecutors.optionalTasks.execute(new Runnable()
        {
            public void run()
            {
                try
                {
                    for (int i = tablesToDrop.size() - 1; i >= 0; i--)
                        schemaChange(String.format("DROP TABLE IF EXISTS %s.%s", KEYSPACE, tablesToDrop.get(i)));

                    for (int i = aggregatesToDrop.size() - 1; i >= 0; i--)
                        schemaChange(String.format("DROP AGGREGATE IF EXISTS %s", aggregatesToDrop.get(i)));

                    for (int i = functionsToDrop.size() - 1; i >= 0; i--)
                        schemaChange(String.format("DROP FUNCTION IF EXISTS %s", functionsToDrop.get(i)));

                    for (int i = typesToDrop.size() - 1; i >= 0; i--)
                        schemaChange(String.format("DROP TYPE IF EXISTS %s.%s", KEYSPACE, typesToDrop.get(i)));

                    // Dropping doesn't delete the sstables. It's not a huge deal but it's cleaner to cleanup after us
                    // Thas said, we shouldn't delete blindly before the SSTableDeletingTask for the table we drop
                    // have run or they will be unhappy. Since those taks are scheduled on StorageService.tasks and that's
                    // mono-threaded, just push a task on the queue to find when it's empty. No perfect but good enough.

                    final CountDownLatch latch = new CountDownLatch(1);
                    ScheduledExecutors.nonPeriodicTasks.execute(new Runnable()
                    {
                        public void run()
                        {
                            latch.countDown();
                        }
                    });
                    latch.await(2, TimeUnit.SECONDS);

                    removeAllSSTables(KEYSPACE, tablesToDrop);
                }
                catch (Exception e)
                {
                    throw new RuntimeException(e);
                }
            }
        });
    }

    // lazy initialization for all tests that require Java Driver
    protected static void requireNetwork() throws ConfigurationException
    {
        if (server != null)
            return;

        SystemKeyspace.finishStartup();
        StorageService.instance.initServer();
        SchemaLoader.startGossiper();

        server = new org.apache.cassandra.transport.Server(nativeAddr, nativePort);
        server.start();

        for (int version = 1; version <= maxProtocolVersion; version++)
        {
            if (cluster[version-1] != null)
                continue;

            cluster[version-1] = Cluster.builder().addContactPoints(nativeAddr)
                                  .withClusterName("Test Cluster")
                                  .withPort(nativePort)
                                  .withProtocolVersion(ProtocolVersion.fromInt(version))
                                  .build();
            session[version-1] = cluster[version-1].connect();

            logger.info("Started Java Driver instance for protocol version {}", version);
        }
    }

    protected void dropPerTestKeyspace() throws Throwable
    {
        execute(String.format("DROP KEYSPACE IF EXISTS %s", KEYSPACE_PER_TEST));
    }

    /**
     * Returns a copy of the specified list.
     * @return a copy of the specified list.
     */
    private static List<String> copy(List<String> list)
    {
        return list.isEmpty() ? Collections.<String>emptyList() : new ArrayList<>(list);
    }

    public ColumnFamilyStore getCurrentColumnFamilyStore()
    {
        String currentTable = currentTable();
        return currentTable == null
             ? null
             : Keyspace.open(KEYSPACE).getColumnFamilyStore(currentTable);
    }

    public void flush()
    {
        try
        {
            ColumnFamilyStore store = getCurrentColumnFamilyStore();
            if (store != null)
                store.forceFlush().get();
        }
        catch (InterruptedException | ExecutionException e)
        {
            throw new RuntimeException(e);
        }
    }

    public void compact()
    {
        try
        {
            String currentTable = currentTable();
            if (currentTable != null)
                Keyspace.open(KEYSPACE).getColumnFamilyStore(currentTable).forceMajorCompaction();
        }
        catch (InterruptedException | ExecutionException e)
        {
            throw new RuntimeException(e);
        }
    }

    public void cleanupCache()
    {
        String currentTable = currentTable();
        if (currentTable != null)
            Keyspace.open(KEYSPACE).getColumnFamilyStore(currentTable).cleanupCache();
    }

    public static FunctionName parseFunctionName(String qualifiedName)
    {
        int i = qualifiedName.indexOf('.');
        return i == -1
               ? FunctionName.nativeFunction(qualifiedName)
               : new FunctionName(qualifiedName.substring(0, i).trim(), qualifiedName.substring(i+1).trim());
    }

    public static String shortFunctionName(String f)
    {
        return parseFunctionName(f).name;
    }

    private static void removeAllSSTables(String ks, List<String> tables)
    {
        // clean up data directory which are stored as data directory/keyspace/data files
        for (File d : Directories.getKSChildDirectories(ks))
        {
            if (d.exists() && containsAny(d.getName(), tables))
                FileUtils.deleteRecursive(d);
        }
    }

    private static boolean containsAny(String filename, List<String> tables)
    {
        for (int i = 0, m = tables.size(); i < m; i++)
            // don't accidentally delete in-use directories with the
            // same prefix as a table to delete, i.e. table_1 & table_11
            if (filename.contains(tables.get(i) + "-"))
                return true;
        return false;
    }

    protected String keyspace()
    {
        return KEYSPACE;
    }

    protected String currentTable()
    {
        if (tables.isEmpty())
            return null;
        return tables.get(tables.size() - 1);
    }

    protected ByteBuffer unset()
    {
        return ByteBufferUtil.UNSET_BYTE_BUFFER;
    }

    protected void forcePreparedValues()
    {
        this.usePrepared = true;
    }

    protected void stopForcingPreparedValues()
    {
        this.usePrepared = USE_PREPARED_VALUES;
    }

    protected String createType(String query)
    {
        String typeName = "type_" + seqNumber.getAndIncrement();
        String fullQuery = String.format(query, KEYSPACE + "." + typeName);
        types.add(typeName);
        logger.info(fullQuery);
        schemaChange(fullQuery);
        return typeName;
    }

    protected String createFunction(String keyspace, String argTypes, String query) throws Throwable
    {
        String functionName = keyspace + ".function_" + seqNumber.getAndIncrement();
        createFunctionOverload(functionName, argTypes, query);
        return functionName;
    }

    protected void createFunctionOverload(String functionName, String argTypes, String query) throws Throwable
    {
        String fullQuery = String.format(query, functionName);
        functions.add(functionName + '(' + argTypes + ')');
        logger.info(fullQuery);
        schemaChange(fullQuery);
    }

    protected String createAggregate(String keyspace, String argTypes, String query) throws Throwable
    {
        String aggregateName = keyspace + "." + "aggregate_" + seqNumber.getAndIncrement();
        createAggregateOverload(aggregateName, argTypes, query);
        return aggregateName;
    }

    protected void createAggregateOverload(String aggregateName, String argTypes, String query) throws Throwable
    {
        String fullQuery = String.format(query, aggregateName);
        aggregates.add(aggregateName + '(' + argTypes + ')');
        logger.info(fullQuery);
        schemaChange(fullQuery);
    }

    protected String createTable(String query)
    {
        String currentTable = createTableName();
        String fullQuery = formatQuery(query);
        logger.info(fullQuery);
        schemaChange(fullQuery);
        return currentTable;
    }

    protected String createTableName()
    {
        String currentTable = "table_" + seqNumber.getAndIncrement();
        tables.add(currentTable);
        return currentTable;
    }

    protected void createTableMayThrow(String query) throws Throwable
    {
        String currentTable = "table_" + seqNumber.getAndIncrement();
        tables.add(currentTable);
        String fullQuery = formatQuery(query);
        logger.info(fullQuery);
        QueryProcessor.executeOnceInternal(fullQuery);
    }

    protected void alterTable(String query)
    {
        String fullQuery = formatQuery(query);
        logger.info(fullQuery);
        schemaChange(fullQuery);
    }

    protected void alterTableMayThrow(String query) throws Throwable
    {
        String fullQuery = formatQuery(query);
        logger.info(fullQuery);
        QueryProcessor.executeOnceInternal(fullQuery);
    }

    protected void dropTable(String query)
    {
        String fullQuery = String.format(query, KEYSPACE + "." + currentTable());
        logger.info(fullQuery);
        schemaChange(fullQuery);
    }

    protected void createIndex(String query)
    {
        String fullQuery = formatQuery(query);
        logger.info(fullQuery);
        schemaChange(fullQuery);
    }

    /**
     * Index creation is asynchronous, this method searches in the system table IndexInfo
     * for the specified index and returns true if it finds it, which indicates the
     * index was built. If we haven't found it after 5 seconds we give-up.
     */
    protected boolean waitForIndex(String keyspace, String table, String index) throws Throwable
    {
        long start = System.currentTimeMillis();
        boolean indexCreated = false;
        String indedName = String.format("%s.%s", table, index);
        while (!indexCreated)
        {
            Object[][] results = getRows(execute("select index_name from system.\"IndexInfo\" where table_name = ?", keyspace));
            for(int i = 0; i < results.length; i++)
            {
                if (indedName.equals(results[i][0]))
                {
                    indexCreated = true;
                    break;
                }
            }

            if (System.currentTimeMillis() - start > 5000)
                break;

            Thread.sleep(10);
        }

        return indexCreated;
    }

    protected void createIndexMayThrow(String query) throws Throwable
    {
        String fullQuery = formatQuery(query);
        logger.info(fullQuery);
        QueryProcessor.executeOnceInternal(fullQuery);
    }

    protected void dropIndex(String query) throws Throwable
    {
        String fullQuery = String.format(query, KEYSPACE);
        logger.info(fullQuery);
        schemaChange(fullQuery);
    }

    protected void assertLastSchemaChange(Event.SchemaChange.Change change, Event.SchemaChange.Target target,
                                          String keyspace, String name,
                                          String... argTypes)
    {
        Assert.assertTrue(lastSchemaChangeResult instanceof ResultMessage.SchemaChange);
        ResultMessage.SchemaChange schemaChange = (ResultMessage.SchemaChange) lastSchemaChangeResult;
        Assert.assertSame(change, schemaChange.change.change);
        Assert.assertSame(target, schemaChange.change.target);
        Assert.assertEquals(keyspace, schemaChange.change.keyspace);
        Assert.assertEquals(name, schemaChange.change.name);
        Assert.assertEquals(argTypes != null ? Arrays.asList(argTypes) : null, schemaChange.change.argTypes);
    }

    protected static void schemaChange(String query)
    {
        try
        {
            ClientState state = ClientState.forInternalCalls();
            state.setKeyspace(SystemKeyspace.NAME);
            QueryState queryState = new QueryState(state);

            ParsedStatement.Prepared prepared = QueryProcessor.parseStatement(query, queryState);
            prepared.statement.validate(state);

            QueryOptions options = QueryOptions.forInternalCalls(Collections.<ByteBuffer>emptyList());

            lastSchemaChangeResult = prepared.statement.executeInternal(queryState, options);
        }
        catch (Exception e)
        {
            throw new RuntimeException("Error setting schema for test (query was: " + query + ")", e);
        }
    }

    protected CFMetaData currentTableMetadata()
    {
        return Schema.instance.getCFMetaData(KEYSPACE, currentTable());
    }

    protected com.datastax.driver.core.ResultSet executeNet(int protocolVersion, String query, Object... values) throws Throwable
    {
        requireNetwork();

        return session[protocolVersion-1].execute(formatQuery(query), values);
    }

    protected Session sessionNet(int protocolVersion)
    {
        requireNetwork();

        return session[protocolVersion-1];
    }

    private String formatQuery(String query)
    {
        String currentTable = currentTable();
        return currentTable == null ? query : String.format(query, KEYSPACE + "." + currentTable);
    }

    protected UntypedResultSet execute(String query, Object... values) throws Throwable
    {
        query = formatQuery(query);

        UntypedResultSet rs;
        if (usePrepared)
        {
            if (logger.isDebugEnabled())
                logger.debug("Executing: {} with values {}", query, formatAllValues(values));
            rs = QueryProcessor.executeOnceInternal(query, transformValues(values));
        }
        else
        {
            query = replaceValues(query, values);
            if (logger.isDebugEnabled())
                logger.debug("Executing: {}", query);
            rs = QueryProcessor.executeOnceInternal(query);
        }
        if (rs != null)
        {
            if (logger.isDebugEnabled())
                logger.debug("Got {} rows", rs.size());
        }
        return rs;
    }

    protected void assertRowsNet(int protocolVersion, ResultSet result, Object[]... rows)
    {
        if (result == null)
        {
            if (rows.length > 0)
                Assert.fail(String.format("No rows returned by query but %d expected", rows.length));
            return;
        }

        ColumnDefinitions meta = result.getColumnDefinitions();
        Iterator<Row> iter = result.iterator();
        int i = 0;
        while (iter.hasNext() && i < rows.length)
        {
            Object[] expected = rows[i];
            Row actual = iter.next();

            Assert.assertEquals(String.format("Invalid number of (expected) values provided for row %d (using protocol version %d)",
                                              i, protocolVersion),
                                meta.size(), expected.length);

            for (int j = 0; j < meta.size(); j++)
            {
                DataType type = meta.getType(j);
                ByteBuffer expectedByteValue = type.serialize(expected[j], ProtocolVersion.fromInt(protocolVersion));
                int expectedBytes = expectedByteValue.remaining();
                ByteBuffer actualValue = actual.getBytesUnsafe(meta.getName(j));
                int actualBytes = actualValue.remaining();

                if (!Objects.equal(expectedByteValue, actualValue))
                    Assert.fail(String.format("Invalid value for row %d column %d (%s of type %s), " +
                                              "expected <%s> (%d bytes) but got <%s> (%d bytes) " +
                                              "(using protocol version %d)",
                                              i, j, meta.getName(j), type,
                                              type.format(expected[j]),
                                              expectedBytes,
                                              type.format(type.deserialize(actualValue, ProtocolVersion.fromInt(protocolVersion))),
                                              actualBytes,
                                              protocolVersion));
            }
            i++;
        }

        if (iter.hasNext())
        {
            while (iter.hasNext())
            {
                iter.next();
                i++;
            }
            Assert.fail(String.format("Got less rows than expected. Expected %d but got %d (using protocol version %d).",
                                      rows.length, i, protocolVersion));
        }

        Assert.assertTrue(String.format("Got %s rows than expected. Expected %d but got %d (using protocol version %d)",
                                        rows.length>i ? "less" : "more", rows.length, i, protocolVersion), i == rows.length);
    }

    public static void assertRows(UntypedResultSet result, Object[]... rows)
    {
        if (result == null)
        {
            if (rows.length > 0)
                Assert.fail(String.format("No rows returned by query but %d expected", rows.length));
            return;
        }

        List<ColumnSpecification> meta = result.metadata();
        Iterator<UntypedResultSet.Row> iter = result.iterator();
        int i = 0;
        while (iter.hasNext() && i < rows.length)
        {
            Object[] expected = rows[i];
            UntypedResultSet.Row actual = iter.next();

            Assert.assertEquals(String.format("Invalid number of (expected) values provided for row %d", i), expected.length, meta.size());

            for (int j = 0; j < meta.size(); j++)
            {
                ColumnSpecification column = meta.get(j);
                ByteBuffer expectedByteValue = makeByteBuffer(expected[j], column.type);
                ByteBuffer actualValue = actual.getBytes(column.name.toString());

                if (!Objects.equal(expectedByteValue, actualValue))
                {
                    Object actualValueDecoded = column.type.getSerializer().deserialize(actualValue);
                    if (!actualValueDecoded.equals(expected[j]))
                        Assert.fail(String.format("Invalid value for row %d column %d (%s of type %s), expected <%s> but got <%s>",
                                                  i,
                                                  j,
                                                  column.name,
                                                  column.type.asCQL3Type(),
                                                  formatValue(expectedByteValue, column.type),
                                                  formatValue(actualValue, column.type)));
                }
            }
            i++;
        }

        if (iter.hasNext())
        {
            while (iter.hasNext())
            {
                iter.next();
                i++;
            }
            Assert.fail(String.format("Got more rows than expected. Expected %d but got %d.", rows.length, i));
        }

        Assert.assertTrue(String.format("Got %s rows than expected. Expected %d but got %d", rows.length>i ? "less" : "more", rows.length, i), i == rows.length);
    }

    protected void assertRowCount(UntypedResultSet result, int numExpectedRows)
    {
        if (result == null)
        {
            if (numExpectedRows > 0)
                Assert.fail(String.format("No rows returned by query but %d expected", numExpectedRows));
            return;
        }

        List<ColumnSpecification> meta = result.metadata();
        Iterator<UntypedResultSet.Row> iter = result.iterator();
        int i = 0;
        while (iter.hasNext() && i < numExpectedRows)
        {
            UntypedResultSet.Row actual = iter.next();
            assertNotNull(actual);
            i++;
        }

        if (iter.hasNext())
        {
            while (iter.hasNext())
            {
                iter.next();
                i++;
            }
            Assert.fail(String.format("Got less rows than expected. Expected %d but got %d.", numExpectedRows, i));
        }

        Assert.assertTrue(String.format("Got %s rows than expected. Expected %d but got %d", numExpectedRows>i ? "less" : "more", numExpectedRows, i), i == numExpectedRows);
    }

    protected Object[][] getRows(UntypedResultSet result)
    {
        if (result == null)
            return new Object[0][];

        List<Object[]> ret = new ArrayList<>();
        List<ColumnSpecification> meta = result.metadata();

        Iterator<UntypedResultSet.Row> iter = result.iterator();
        while (iter.hasNext())
        {
            UntypedResultSet.Row rowVal = iter.next();
            Object[] row = new Object[meta.size()];
            for (int j = 0; j < meta.size(); j++)
            {
                ColumnSpecification column = meta.get(j);
                ByteBuffer val = rowVal.getBytes(column.name.toString());
                row[j] = val == null ? null : column.type.getSerializer().deserialize(val);
            }

            ret.add(row);
        }

        Object[][] a = new Object[ret.size()][];
        return ret.toArray(a);
    }

    protected void assertColumnNames(UntypedResultSet result, String... expectedColumnNames)
    {
        if (result == null)
        {
            Assert.fail("No rows returned by query.");
            return;
        }

        List<ColumnSpecification> metadata = result.metadata();
        Assert.assertEquals("Got less columns than expected.", expectedColumnNames.length, metadata.size());

        for (int i = 0, m = metadata.size(); i < m; i++)
        {
            ColumnSpecification columnSpec = metadata.get(i);
            Assert.assertEquals(expectedColumnNames[i], columnSpec.name.toString());
        }
    }

    protected void assertAllRows(Object[]... rows) throws Throwable
    {
        assertRows(execute("SELECT * FROM %s"), rows);
    }

    public static Object[] row(Object... expected)
    {
        return expected;
    }

    protected void assertEmpty(UntypedResultSet result) throws Throwable
    {
        if (result != null && !result.isEmpty())
            throw new AssertionError(String.format("Expected empty result but got %d rows", result.size()));
    }

    protected void assertInvalid(String query, Object... values) throws Throwable
    {
        assertInvalidMessage(null, query, values);
    }

    protected void assertInvalidMessage(String errorMessage, String query, Object... values) throws Throwable
    {
        assertInvalidThrowMessage(errorMessage, null, query, values);
    }

    protected void assertInvalidThrow(Class<? extends Throwable> exception, String query, Object... values) throws Throwable
    {
        assertInvalidThrowMessage(null, exception, query, values);
    }

    protected void assertInvalidThrowMessage(String errorMessage, Class<? extends Throwable> exception, String query, Object... values) throws Throwable
    {
        try
        {
            execute(query, values);
            String q = USE_PREPARED_VALUES
                       ? query + " (values: " + formatAllValues(values) + ")"
                       : replaceValues(query, values);
            Assert.fail("Query should be invalid but no error was thrown. Query is: " + q);
        }
        catch (CassandraException e)
        {
            if (exception != null && !exception.isAssignableFrom(e.getClass()))
            {
                Assert.fail("Query should be invalid but wrong error was thrown. " +
                            "Expected: " + exception.getName() + ", got: " + e.getClass().getName() + ". " +
                            "Query is: " + queryInfo(query, values));
            }
            if (errorMessage != null)
            {
                assertMessageContains(errorMessage, e);
            }
        }
    }

    private static String queryInfo(String query, Object[] values)
    {
        return USE_PREPARED_VALUES
               ? query + " (values: " + formatAllValues(values) + ")"
               : replaceValues(query, values);
    }

    protected void assertValidSyntax(String query) throws Throwable
    {
        try
        {
            QueryProcessor.parseStatement(query);
        }
        catch(SyntaxException e)
        {
            Assert.fail(String.format("Expected query syntax to be valid but was invalid. Query is: %s; Error is %s",
                                      query, e.getMessage()));
        }
    }

    protected void assertInvalidSyntax(String query, Object... values) throws Throwable
    {
        assertInvalidSyntaxMessage(null, query, values);
    }

    protected void assertInvalidSyntaxMessage(String errorMessage, String query, Object... values) throws Throwable
    {
        try
        {
            execute(query, values);
            Assert.fail("Query should have invalid syntax but no error was thrown. Query is: " + queryInfo(query, values));
        }
        catch (SyntaxException e)
        {
            if (errorMessage != null)
            {
                assertMessageContains(errorMessage, e);
            }
        }
    }

    /**
     * Asserts that the message of the specified exception contains the specified text.
     *
     * @param text the text that the exception message must contains
     * @param e the exception to check
     */
    private static void assertMessageContains(String text, Exception e)
    {
        Assert.assertTrue("Expected error message to contain '" + text + "', but got '" + e.getMessage() + "'",
                e.getMessage().contains(text));
    }

    private static String replaceValues(String query, Object[] values)
    {
        StringBuilder sb = new StringBuilder();
        int last = 0;
        int i = 0;
        int idx;
        while ((idx = query.indexOf('?', last)) > 0)
        {
            if (i >= values.length)
                throw new IllegalArgumentException(String.format("Not enough values provided. The query has at least %d variables but only %d values provided", i, values.length));

            sb.append(query.substring(last, idx));

            Object value = values[i++];

            // When we have a .. IN ? .., we use a list for the value because that's what's expected when the value is serialized.
            // When we format as string however, we need to special case to use parenthesis. Hackish but convenient.
            if (idx >= 3 && value instanceof List && query.substring(idx - 3, idx).equalsIgnoreCase("IN "))
            {
                List l = (List)value;
                sb.append("(");
                for (int j = 0; j < l.size(); j++)
                {
                    if (j > 0)
                        sb.append(", ");
                    sb.append(formatForCQL(l.get(j)));
                }
                sb.append(")");
            }
            else
            {
                sb.append(formatForCQL(value));
            }
            last = idx + 1;
        }
        sb.append(query.substring(last));
        return sb.toString();
    }

    // We're rellly only returning ByteBuffers but this make the type system happy
    private static Object[] transformValues(Object[] values)
    {
        // We could partly rely on QueryProcessor.executeOnceInternal doing type conversion for us, but
        // it would complain with ClassCastException if we pass say a string where an int is excepted (since
        // it bases conversion on what the value should be, not what it is). For testing, we sometimes
        // want to pass value of the wrong type and assert that this properly raise an InvalidRequestException
        // and executeOnceInternal goes into way. So instead, we pre-convert everything to bytes here based
        // on the value.
        // Besides, we need to handle things like TupleValue that executeOnceInternal don't know about.

        Object[] buffers = new ByteBuffer[values.length];
        for (int i = 0; i < values.length; i++)
        {
            Object value = values[i];
            if (value == null)
            {
                buffers[i] = null;
                continue;
            }
            else if (value == ByteBufferUtil.UNSET_BYTE_BUFFER)
            {
                buffers[i] = ByteBufferUtil.UNSET_BYTE_BUFFER;
                continue;
            }

            try
            {
                buffers[i] = typeFor(value).decompose(serializeTuples(value));
            }
            catch (Exception ex)
            {
                logger.info("Error serializing query parameter {}:", value, ex);
                throw ex;
            }
        }
        return buffers;
    }

    private static Object serializeTuples(Object value)
    {
        if (value instanceof TupleValue)
        {
            return ((TupleValue)value).toByteBuffer();
        }

        // We need to reach inside collections for TupleValue and transform them to ByteBuffer
        // since otherwise the decompose method of the collection AbstractType won't know what
        // to do with them
        if (value instanceof List)
        {
            List l = (List)value;
            List n = new ArrayList(l.size());
            for (Object o : l)
                n.add(serializeTuples(o));
            return n;
        }

        if (value instanceof Set)
        {
            Set s = (Set)value;
            Set n = new LinkedHashSet(s.size());
            for (Object o : s)
                n.add(serializeTuples(o));
            return n;
        }

        if (value instanceof Map)
        {
            Map m = (Map)value;
            Map n = new LinkedHashMap(m.size());
            for (Object entry : m.entrySet())
                n.put(serializeTuples(((Map.Entry)entry).getKey()), serializeTuples(((Map.Entry)entry).getValue()));
            return n;
        }
        return value;
    }

    private static String formatAllValues(Object[] values)
    {
        StringBuilder sb = new StringBuilder();
        sb.append("[");
        for (int i = 0; i < values.length; i++)
        {
            if (i > 0)
                sb.append(", ");
            sb.append(formatForCQL(values[i]));
        }
        sb.append("]");
        return sb.toString();
    }

    private static String formatForCQL(Object value)
    {
        if (value == null)
            return "null";

        if (value instanceof TupleValue)
            return ((TupleValue)value).toCQLString();

        // We need to reach inside collections for TupleValue. Besides, for some reason the format
        // of collection that CollectionType.getString gives us is not at all 'CQL compatible'
        if (value instanceof Collection || value instanceof Map)
        {
            StringBuilder sb = new StringBuilder();
            if (value instanceof List)
            {
                List l = (List)value;
                sb.append("[");
                for (int i = 0; i < l.size(); i++)
                {
                    if (i > 0)
                        sb.append(", ");
                    sb.append(formatForCQL(l.get(i)));
                }
                sb.append("]");
            }
            else if (value instanceof Set)
            {
                Set s = (Set)value;
                sb.append("{");
                Iterator iter = s.iterator();
                while (iter.hasNext())
                {
                    sb.append(formatForCQL(iter.next()));
                    if (iter.hasNext())
                        sb.append(", ");
                }
                sb.append("}");
            }
            else
            {
                Map m = (Map)value;
                sb.append("{");
                Iterator iter = m.entrySet().iterator();
                while (iter.hasNext())
                {
                    Map.Entry entry = (Map.Entry)iter.next();
                    sb.append(formatForCQL(entry.getKey())).append(": ").append(formatForCQL(entry.getValue()));
                    if (iter.hasNext())
                        sb.append(", ");
                }
                sb.append("}");
            }
            return sb.toString();
        }

        AbstractType type = typeFor(value);
        String s = type.getString(type.decompose(value));

        if (type instanceof InetAddressType || type instanceof TimestampType)
            return String.format("'%s'", s);
        else if (type instanceof UTF8Type)
            return String.format("'%s'", s.replaceAll("'", "''"));
        else if (type instanceof BytesType)
            return "0x" + s;

        return s;
    }

    private static ByteBuffer makeByteBuffer(Object value, AbstractType type)
    {
        if (value == null)
            return null;

        if (value instanceof TupleValue)
            return ((TupleValue)value).toByteBuffer();

        if (value instanceof ByteBuffer)
            return (ByteBuffer)value;

        return type.decompose(value);
    }

    private static String formatValue(ByteBuffer bb, AbstractType<?> type)
    {
        if (bb == null)
            return "null";

        if (type instanceof CollectionType)
        {
            // CollectionType override getString() to use hexToBytes. We can't change that
            // without breaking SSTable2json, but the serializer for collection have the
            // right getString so using it directly instead.
            TypeSerializer ser = type.getSerializer();
            return ser.toString(ser.deserialize(bb));
        }

        return type.getString(bb);
    }

    protected Object tuple(Object...values)
    {
        return new TupleValue(values);
    }

    protected Object userType(Object... values)
    {
        return new TupleValue(values).toByteBuffer();
    }

    protected Object list(Object...values)
    {
        return Arrays.asList(values);
    }

    protected Object set(Object...values)
    {
        return ImmutableSet.copyOf(values);
    }

    protected Object map(Object...values)
    {
        if (values.length % 2 != 0)
            throw new IllegalArgumentException();

        int size = values.length / 2;
        Map m = new LinkedHashMap(size);
        for (int i = 0; i < size; i++)
            m.put(values[2 * i], values[(2 * i) + 1]);
        return m;
    }

    // Attempt to find an AbstracType from a value (for serialization/printing sake).
    // Will work as long as we use types we know of, which is good enough for testing
    private static AbstractType typeFor(Object value)
    {
        if (value instanceof ByteBuffer || value instanceof TupleValue || value == null)
            return BytesType.instance;

        if (value instanceof Byte)
            return ByteType.instance;

        if (value instanceof Short)
            return ShortType.instance;

        if (value instanceof Integer)
            return Int32Type.instance;

        if (value instanceof Long)
            return LongType.instance;

        if (value instanceof Float)
            return FloatType.instance;

        if (value instanceof Double)
            return DoubleType.instance;

        if (value instanceof BigInteger)
            return IntegerType.instance;

        if (value instanceof BigDecimal)
            return DecimalType.instance;

        if (value instanceof String)
            return UTF8Type.instance;

        if (value instanceof Boolean)
            return BooleanType.instance;

        if (value instanceof InetAddress)
            return InetAddressType.instance;

        if (value instanceof Date)
            return TimestampType.instance;

        if (value instanceof UUID)
            return UUIDType.instance;

        if (value instanceof List)
        {
            List l = (List)value;
            AbstractType elt = l.isEmpty() ? BytesType.instance : typeFor(l.get(0));
            return ListType.getInstance(elt, true);
        }

        if (value instanceof Set)
        {
            Set s = (Set)value;
            AbstractType elt = s.isEmpty() ? BytesType.instance : typeFor(s.iterator().next());
            return SetType.getInstance(elt, true);
        }

        if (value instanceof Map)
        {
            Map m = (Map)value;
            AbstractType keys, values;
            if (m.isEmpty())
            {
                keys = BytesType.instance;
                values = BytesType.instance;
            }
            else
            {
                Map.Entry entry = (Map.Entry)m.entrySet().iterator().next();
                keys = typeFor(entry.getKey());
                values = typeFor(entry.getValue());
            }
            return MapType.getInstance(keys, values, true);
        }

        throw new IllegalArgumentException("Unsupported value type (value is " + value + ")");
    }

    private static class TupleValue
    {
        private final Object[] values;

        TupleValue(Object[] values)
        {
            this.values = values;
        }

        public ByteBuffer toByteBuffer()
        {
            ByteBuffer[] bbs = new ByteBuffer[values.length];
            for (int i = 0; i < values.length; i++)
                bbs[i] = makeByteBuffer(values[i], typeFor(values[i]));
            return TupleType.buildValue(bbs);
        }

        public String toCQLString()
        {
            StringBuilder sb = new StringBuilder();
            sb.append("(");
            for (int i = 0; i < values.length; i++)
            {
                if (i > 0)
                    sb.append(", ");
                sb.append(formatForCQL(values[i]));
            }
            sb.append(")");
            return sb.toString();
        }

        public String toString()
        {
            return "TupleValue" + toCQLString();
        }
    }
}


File: test/unit/org/apache/cassandra/cql3/validation/entities/UFTest.java
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
package org.apache.cassandra.cql3.validation.entities;

import java.math.BigDecimal;
import java.math.BigInteger;
import java.nio.ByteBuffer;
import java.util.ArrayList;
import java.util.Arrays;
import java.util.Date;
import java.util.List;
import java.util.Map;
import java.util.Set;
import java.util.TreeMap;
import java.util.TreeSet;
import java.util.UUID;

import org.junit.Assert;
import org.junit.BeforeClass;
import org.junit.Test;

import com.datastax.driver.core.*;
import com.datastax.driver.core.exceptions.InvalidQueryException;
import org.apache.cassandra.config.Schema;
import org.apache.cassandra.cql3.QueryProcessor;
import org.apache.cassandra.cql3.UntypedResultSet;
import org.apache.cassandra.cql3.functions.FunctionName;
import org.apache.cassandra.cql3.functions.UDFunction;
import org.apache.cassandra.cql3.CQLTester;
import org.apache.cassandra.db.marshal.CollectionType;
import org.apache.cassandra.dht.ByteOrderedPartitioner;
import org.apache.cassandra.exceptions.FunctionExecutionException;
import org.apache.cassandra.exceptions.InvalidRequestException;
import org.apache.cassandra.schema.KeyspaceMetadata;
import org.apache.cassandra.service.ClientState;
import org.apache.cassandra.service.StorageService;
import org.apache.cassandra.transport.Event;
import org.apache.cassandra.transport.Server;
import org.apache.cassandra.transport.messages.ResultMessage;
import org.apache.cassandra.utils.ByteBufferUtil;
import org.apache.cassandra.utils.UUIDGen;

public class UFTest extends CQLTester
{
    @Test
    public void testSchemaChange() throws Throwable
    {
        String f = createFunction(KEYSPACE,
                                  "double, double",
                                  "CREATE OR REPLACE FUNCTION %s(state double, val double) " +
                                  "RETURNS NULL ON NULL INPUT " +
                                  "RETURNS double " +
                                  "LANGUAGE javascript " +
                                  "AS '\"string\";';");

        assertLastSchemaChange(Event.SchemaChange.Change.CREATED, Event.SchemaChange.Target.FUNCTION,
                               KEYSPACE, parseFunctionName(f).name,
                               "double", "double");

        createFunctionOverload(f,
                               "double, double",
                               "CREATE OR REPLACE FUNCTION %s(state int, val int) " +
                               "RETURNS NULL ON NULL INPUT " +
                               "RETURNS int " +
                               "LANGUAGE javascript " +
                               "AS '\"string\";';");

        assertLastSchemaChange(Event.SchemaChange.Change.CREATED, Event.SchemaChange.Target.FUNCTION,
                               KEYSPACE, parseFunctionName(f).name,
                               "int", "int");

        schemaChange("CREATE OR REPLACE FUNCTION " + f + "(state int, val int) " +
                     "RETURNS NULL ON NULL INPUT " +
                     "RETURNS int " +
                     "LANGUAGE javascript " +
                     "AS '\"string\";';");

        assertLastSchemaChange(Event.SchemaChange.Change.UPDATED, Event.SchemaChange.Target.FUNCTION,
                               KEYSPACE, parseFunctionName(f).name,
                               "int", "int");

        schemaChange("DROP FUNCTION " + f + "(double, double)");

        assertLastSchemaChange(Event.SchemaChange.Change.DROPPED, Event.SchemaChange.Target.FUNCTION,
                               KEYSPACE, parseFunctionName(f).name,
                               "double", "double");
    }

    @Test
    public void testFunctionDropOnKeyspaceDrop() throws Throwable
    {
        String fSin = createFunction(KEYSPACE_PER_TEST, "double",
                                     "CREATE FUNCTION %s ( input double ) " +
                                     "CALLED ON NULL INPUT " +
                                     "RETURNS double " +
                                     "LANGUAGE java " +
                                     "AS 'return Double.valueOf(Math.sin(input.doubleValue()));'");

        FunctionName fSinName = parseFunctionName(fSin);

        Assert.assertEquals(1, Schema.instance.getFunctions(parseFunctionName(fSin)).size());

        assertRows(execute("SELECT function_name, language FROM system_schema.functions WHERE keyspace_name=?", KEYSPACE_PER_TEST),
                   row(fSinName.name, "java"));

        dropPerTestKeyspace();

        assertRows(execute("SELECT function_name, language FROM system_schema.functions WHERE keyspace_name=?", KEYSPACE_PER_TEST));

        Assert.assertEquals(0, Schema.instance.getFunctions(fSinName).size());
    }

    @Test
    public void testFunctionDropPreparedStatement() throws Throwable
    {
        createTable("CREATE TABLE %s (key int PRIMARY KEY, d double)");

        String fSin = createFunction(KEYSPACE_PER_TEST, "double",
                                     "CREATE FUNCTION %s ( input double ) " +
                                     "CALLED ON NULL INPUT " +
                                     "RETURNS double " +
                                     "LANGUAGE java " +
                                     "AS 'return Double.valueOf(Math.sin(input.doubleValue()));'");

        FunctionName fSinName = parseFunctionName(fSin);

        Assert.assertEquals(1, Schema.instance.getFunctions(parseFunctionName(fSin)).size());

        // create a pairs of Select and Inserts. One statement in each pair uses the function so when we
        // drop it those statements should be removed from the cache in QueryProcessor. The other statements
        // should be unaffected.

        ResultMessage.Prepared preparedSelect1 = QueryProcessor.prepare(
                                                                       String.format("SELECT key, %s(d) FROM %s.%s", fSin, KEYSPACE, currentTable()),
                                                                       ClientState.forInternalCalls(), false);
        ResultMessage.Prepared preparedSelect2 = QueryProcessor.prepare(
                                                    String.format("SELECT key FROM %s.%s", KEYSPACE, currentTable()),
                                                    ClientState.forInternalCalls(), false);
        ResultMessage.Prepared preparedInsert1 = QueryProcessor.prepare(
                                                      String.format("INSERT INTO %s.%s (key, d) VALUES (?, %s(?))", KEYSPACE, currentTable(), fSin),
                                                      ClientState.forInternalCalls(), false);
        ResultMessage.Prepared preparedInsert2 = QueryProcessor.prepare(
                                                      String.format("INSERT INTO %s.%s (key, d) VALUES (?, ?)", KEYSPACE, currentTable()),
                                                      ClientState.forInternalCalls(), false);

        Assert.assertNotNull(QueryProcessor.instance.getPrepared(preparedSelect1.statementId));
        Assert.assertNotNull(QueryProcessor.instance.getPrepared(preparedSelect2.statementId));
        Assert.assertNotNull(QueryProcessor.instance.getPrepared(preparedInsert1.statementId));
        Assert.assertNotNull(QueryProcessor.instance.getPrepared(preparedInsert2.statementId));

        execute("DROP FUNCTION " + fSin + "(double);");

        // the statements which use the dropped function should be removed from cache, with the others remaining
        Assert.assertNull(QueryProcessor.instance.getPrepared(preparedSelect1.statementId));
        Assert.assertNotNull(QueryProcessor.instance.getPrepared(preparedSelect2.statementId));
        Assert.assertNull(QueryProcessor.instance.getPrepared(preparedInsert1.statementId));
        Assert.assertNotNull(QueryProcessor.instance.getPrepared(preparedInsert2.statementId));

        execute("CREATE FUNCTION " + fSin + " ( input double ) " +
                "RETURNS NULL ON NULL INPUT " +
                "RETURNS double " +
                "LANGUAGE java " +
                "AS 'return Double.valueOf(Math.sin(input));'");

        Assert.assertEquals(1, Schema.instance.getFunctions(fSinName).size());

        preparedSelect1= QueryProcessor.prepare(
                                         String.format("SELECT key, %s(d) FROM %s.%s", fSin, KEYSPACE, currentTable()),
                                         ClientState.forInternalCalls(), false);
        preparedInsert1 = QueryProcessor.prepare(
                                         String.format("INSERT INTO %s.%s (key, d) VALUES (?, %s(?))", KEYSPACE, currentTable(), fSin),
                                         ClientState.forInternalCalls(), false);
        Assert.assertNotNull(QueryProcessor.instance.getPrepared(preparedSelect1.statementId));
        Assert.assertNotNull(QueryProcessor.instance.getPrepared(preparedInsert1.statementId));

        dropPerTestKeyspace();

        // again, only the 2 statements referencing the function should be removed from cache
        // this time because the statements select from tables in KEYSPACE, only the function
        // is scoped to KEYSPACE_PER_TEST
        Assert.assertNull(QueryProcessor.instance.getPrepared(preparedSelect1.statementId));
        Assert.assertNotNull(QueryProcessor.instance.getPrepared(preparedSelect2.statementId));
        Assert.assertNull(QueryProcessor.instance.getPrepared(preparedInsert1.statementId));
        Assert.assertNotNull(QueryProcessor.instance.getPrepared(preparedInsert2.statementId));
    }

    @Test
    public void testDropFunctionDropsPreparedStatementsWithDelayedValues() throws Throwable
    {
        // test that dropping a function removes stmts which use
        // it to provide a DelayedValue collection from the
        // cache in QueryProcessor
        checkDelayedValuesCorrectlyIdentifyFunctionsInUse(false);
    }

    @Test
    public void testDropKeyspaceContainingFunctionDropsPreparedStatementsWithDelayedValues() throws Throwable
    {
        // test that dropping a function removes stmts which use
        // it to provide a DelayedValue collection from the
        // cache in QueryProcessor
        checkDelayedValuesCorrectlyIdentifyFunctionsInUse(true);
    }

    private ResultMessage.Prepared prepareStatementWithDelayedValue(CollectionType.Kind kind, String function)
    {
        String collectionType;
        String literalArgs;
        switch (kind)
        {
            case LIST:
                collectionType = "list<double>";
                literalArgs = String.format("[%s(0.0)]", function);
                break;
            case SET:
                collectionType = "set<double>";
                literalArgs = String.format("{%s(0.0)}", function);
                break;
            case MAP:
                collectionType = "map<double, double>";
                literalArgs = String.format("{%s(0.0):0.0}", function);
                break;
            default:
                Assert.fail("Unsupported collection type " + kind);
                collectionType = null;
                literalArgs = null;
        }

        createTable("CREATE TABLE %s (" +
                    " key int PRIMARY KEY," +
                    " val " + collectionType + ')');

        ResultMessage.Prepared prepared = QueryProcessor.prepare(
                                                                String.format("INSERT INTO %s.%s (key, val) VALUES (?, %s)",
                                                                             KEYSPACE,
                                                                             currentTable(),
                                                                             literalArgs),
                                                                ClientState.forInternalCalls(), false);
        Assert.assertNotNull(QueryProcessor.instance.getPrepared(prepared.statementId));
        return prepared;
    }

    private ResultMessage.Prepared prepareStatementWithDelayedValueTuple(String function)
    {
        createTable("CREATE TABLE %s (" +
                    " key int PRIMARY KEY," +
                    " val tuple<double> )");

        ResultMessage.Prepared prepared = QueryProcessor.prepare(
                                                                String.format("INSERT INTO %s.%s (key, val) VALUES (?, (%s(0.0)))",
                                                                             KEYSPACE,
                                                                             currentTable(),
                                                                             function),
                                                                ClientState.forInternalCalls(), false);
        Assert.assertNotNull(QueryProcessor.instance.getPrepared(prepared.statementId));
        return prepared;
    }

    public void checkDelayedValuesCorrectlyIdentifyFunctionsInUse(boolean dropKeyspace) throws Throwable
    {
        // prepare a statement which doesn't use any function for a control
        createTable("CREATE TABLE %s (" +
                    " key int PRIMARY KEY," +
                    " val double)");
        ResultMessage.Prepared control = QueryProcessor.prepare(
                                                               String.format("INSERT INTO %s.%s (key, val) VALUES (?, ?)",
                                                                            KEYSPACE,
                                                                            currentTable()),
                                                               ClientState.forInternalCalls(), false);
        Assert.assertNotNull(QueryProcessor.instance.getPrepared(control.statementId));

        // a function that we'll drop and verify that statements which use it to
        // provide a DelayedValue are removed from the cache in QueryProcessor
        String function = createFunction(KEYSPACE_PER_TEST, "double",
                                        "CREATE FUNCTION %s ( input double ) " +
                                        "CALLED ON NULL INPUT " +
                                        "RETURNS double " +
                                        "LANGUAGE javascript " +
                                        "AS 'input'");
        Assert.assertEquals(1, Schema.instance.getFunctions(parseFunctionName(function)).size());

        List<ResultMessage.Prepared> prepared = new ArrayList<>();
        // prepare statements which use the function to provide a DelayedValue
        prepared.add(prepareStatementWithDelayedValue(CollectionType.Kind.LIST, function));
        prepared.add(prepareStatementWithDelayedValue(CollectionType.Kind.SET, function));
        prepared.add(prepareStatementWithDelayedValue(CollectionType.Kind.MAP, function));
        prepared.add(prepareStatementWithDelayedValueTuple(function));

        // what to drop - the function is scoped to the per-test keyspace, but the prepared statements
        // select from the per-fixture keyspace. So if we drop the per-test keyspace, the function
        // should be removed along with the statements that reference it. The control statement should
        // remain present in the cache. Likewise, if we actually drop the function itself the control
        // statement should not be removed, but the others should be
        if (dropKeyspace)
            dropPerTestKeyspace();
        else
            execute("DROP FUNCTION " + function);

        Assert.assertNotNull(QueryProcessor.instance.getPrepared(control.statementId));
        for (ResultMessage.Prepared removed : prepared)
            Assert.assertNull(QueryProcessor.instance.getPrepared(removed.statementId));
    }

    @Test
    public void testFunctionCreationAndDrop() throws Throwable
    {
        createTable("CREATE TABLE %s (key int PRIMARY KEY, d double)");

        execute("INSERT INTO %s(key, d) VALUES (?, ?)", 1, 1d);
        execute("INSERT INTO %s(key, d) VALUES (?, ?)", 2, 2d);
        execute("INSERT INTO %s(key, d) VALUES (?, ?)", 3, 3d);

        // simple creation
        String fSin = createFunction(KEYSPACE_PER_TEST, "double",
                                     "CREATE FUNCTION %s ( input double ) " +
                                     "CALLED ON NULL INPUT " +
                                     "RETURNS double " +
                                     "LANGUAGE java " +
                                     "AS 'return Math.sin(input);'");
        // check we can't recreate the same function
        assertInvalidMessage("already exists",
                             "CREATE FUNCTION " + fSin + " ( input double ) " +
                             "CALLED ON NULL INPUT " +
                             "RETURNS double " +
                             "LANGUAGE java AS 'return Double.valueOf(Math.sin(input.doubleValue()));'");

        // but that it doesn't comply with "IF NOT EXISTS"
        execute("CREATE FUNCTION IF NOT EXISTS " + fSin + " ( input double ) " +
                "CALLED ON NULL INPUT " +
                "RETURNS double " +
                "LANGUAGE java AS 'return Double.valueOf(Math.sin(input.doubleValue()));'");

        // Validate that it works as expected
        assertRows(execute("SELECT key, " + fSin + "(d) FROM %s"),
            row(1, Math.sin(1d)),
            row(2, Math.sin(2d)),
            row(3, Math.sin(3d))
        );

        // Replace the method with incompatible return type
        assertInvalidMessage("the new return type text is not compatible with the return type double of existing function",
                             "CREATE OR REPLACE FUNCTION " + fSin + " ( input double ) " +
                             "CALLED ON NULL INPUT " +
                             "RETURNS text " +
                             "LANGUAGE java AS 'return Double.valueOf(42d);'");

        // proper replacement
        execute("CREATE OR REPLACE FUNCTION " + fSin + " ( input double ) " +
                "CALLED ON NULL INPUT " +
                "RETURNS double " +
                "LANGUAGE java AS 'return Double.valueOf(42d);'");

        // Validate the method as been replaced
        assertRows(execute("SELECT key, " + fSin + "(d) FROM %s"),
            row(1, 42.0),
            row(2, 42.0),
            row(3, 42.0)
        );

        // same function but other keyspace
        String fSin2 = createFunction(KEYSPACE, "double",
                                      "CREATE FUNCTION %s ( input double ) " +
                                      "RETURNS NULL ON NULL INPUT " +
                                      "RETURNS double " +
                                      "LANGUAGE java " +
                                      "AS 'return Math.sin(input);'");
        assertRows(execute("SELECT key, " + fSin2 + "(d) FROM %s"),
            row(1, Math.sin(1d)),
            row(2, Math.sin(2d)),
            row(3, Math.sin(3d))
        );

        // Drop
        execute("DROP FUNCTION " + fSin);
        execute("DROP FUNCTION " + fSin2);

        // Drop unexisting function
        assertInvalidMessage("Cannot drop non existing function", "DROP FUNCTION " + fSin);
        // but don't complain with "IF EXISTS"
        execute("DROP FUNCTION IF EXISTS " + fSin);

        // can't drop native functions
        assertInvalidMessage("system keyspace is not user-modifiable", "DROP FUNCTION totimestamp");
        assertInvalidMessage("system keyspace is not user-modifiable", "DROP FUNCTION uuid");

        // sin() no longer exists
        assertInvalidMessage("Unknown function", "SELECT key, sin(d) FROM %s");
    }

    @Test
    public void testFunctionExecution() throws Throwable
    {
        createTable("CREATE TABLE %s (v text PRIMARY KEY)");

        execute("INSERT INTO %s(v) VALUES (?)", "aaa");

        String fRepeat = createFunction(KEYSPACE_PER_TEST, "text,int",
                                        "CREATE FUNCTION %s(v text, n int) " +
                                        "RETURNS NULL ON NULL INPUT " +
                                        "RETURNS text " +
                                        "LANGUAGE java " +
                                        "AS 'StringBuilder sb = new StringBuilder();\n" +
                                        "    for (int i = 0; i < n; i++)\n" +
                                        "        sb.append(v);\n" +
                                        "    return sb.toString();'");

        assertRows(execute("SELECT v FROM %s WHERE v=" + fRepeat + "(?, ?)", "a", 3), row("aaa"));
        assertEmpty(execute("SELECT v FROM %s WHERE v=" + fRepeat + "(?, ?)", "a", 2));
    }

    @Test
    public void testFunctionOverloading() throws Throwable
    {
        createTable("CREATE TABLE %s (k text PRIMARY KEY, v int)");

        execute("INSERT INTO %s(k, v) VALUES (?, ?)", "f2", 1);

        String fOverload = createFunction(KEYSPACE_PER_TEST, "varchar",
                                          "CREATE FUNCTION %s ( input varchar ) " +
                                          "RETURNS NULL ON NULL INPUT " +
                                          "RETURNS text " +
                                          "LANGUAGE java " +
                                          "AS 'return \"f1\";'");
        createFunctionOverload(fOverload,
                               "int",
                               "CREATE OR REPLACE FUNCTION %s(i int) " +
                               "RETURNS NULL ON NULL INPUT " +
                               "RETURNS text " +
                               "LANGUAGE java " +
                               "AS 'return \"f2\";'");
        createFunctionOverload(fOverload,
                               "text,text",
                               "CREATE OR REPLACE FUNCTION %s(v1 text, v2 text) " +
                               "RETURNS NULL ON NULL INPUT " +
                               "RETURNS text " +
                               "LANGUAGE java " +
                               "AS 'return \"f3\";'");
        createFunctionOverload(fOverload,
                               "ascii",
                               "CREATE OR REPLACE FUNCTION %s(v ascii) " +
                               "RETURNS NULL ON NULL INPUT " +
                               "RETURNS text " +
                               "LANGUAGE java " +
                               "AS 'return \"f1\";'");

        // text == varchar, so this should be considered as a duplicate
        assertInvalidMessage("already exists",
                             "CREATE FUNCTION " + fOverload + "(v varchar) " +
                             "RETURNS NULL ON NULL INPUT " +
                             "RETURNS text " +
                             "LANGUAGE java AS 'return \"f1\";'");

        assertRows(execute("SELECT " + fOverload + "(k), " + fOverload + "(v), " + fOverload + "(k, k) FROM %s"),
            row("f1", "f2", "f3")
        );

        forcePreparedValues();
        // This shouldn't work if we use preparation since there no way to know which overload to use
        assertInvalidMessage("Ambiguous call to function", "SELECT v FROM %s WHERE k = " + fOverload + "(?)", "foo");
        stopForcingPreparedValues();

        // but those should since we specifically cast
        assertEmpty(execute("SELECT v FROM %s WHERE k = " + fOverload + "((text)?)", "foo"));
        assertRows(execute("SELECT v FROM %s WHERE k = " + fOverload + "((int)?)", 3), row(1));
        assertEmpty(execute("SELECT v FROM %s WHERE k = " + fOverload + "((ascii)?)", "foo"));
        // And since varchar == text, this should work too
        assertEmpty(execute("SELECT v FROM %s WHERE k = " + fOverload + "((varchar)?)", "foo"));

        // no such functions exist...
        assertInvalidMessage("non existing function", "DROP FUNCTION " + fOverload + "(boolean)");
        assertInvalidMessage("non existing function", "DROP FUNCTION " + fOverload + "(bigint)");

        // 'overloaded' has multiple overloads - so it has to fail (CASSANDRA-7812)
        assertInvalidMessage("matches multiple function definitions", "DROP FUNCTION " + fOverload);
        execute("DROP FUNCTION " + fOverload + "(varchar)");
        assertInvalidMessage("none of its type signatures match", "SELECT v FROM %s WHERE k = " + fOverload + "((text)?)", "foo");
        execute("DROP FUNCTION " + fOverload + "(text, text)");
        assertInvalidMessage("none of its type signatures match", "SELECT v FROM %s WHERE k = " + fOverload + "((text)?,(text)?)", "foo", "bar");
        execute("DROP FUNCTION " + fOverload + "(ascii)");
        assertInvalidMessage("cannot be passed as argument 0 of function", "SELECT v FROM %s WHERE k = " + fOverload + "((ascii)?)", "foo");
        // single-int-overload must still work
        assertRows(execute("SELECT v FROM %s WHERE k = " + fOverload + "((int)?)", 3), row(1));
        // overloaded has just one overload now - so the following DROP FUNCTION is not ambigious (CASSANDRA-7812)
        execute("DROP FUNCTION " + fOverload);
    }

    @Test
    public void testCreateOrReplaceJavaFunction() throws Throwable
    {
        createTable("CREATE TABLE %s (key int primary key, val double)");
        execute("INSERT INTO %s (key, val) VALUES (?, ?)", 1, 1d);
        execute("INSERT INTO %s (key, val) VALUES (?, ?)", 2, 2d);
        execute("INSERT INTO %s (key, val) VALUES (?, ?)", 3, 3d);

        String fName = createFunction(KEYSPACE_PER_TEST, "double",
                "CREATE FUNCTION %s( input double ) " +
                "CALLED ON NULL INPUT " +
                "RETURNS double " +
                "LANGUAGE java " +
                "AS '\n" +
                "  // parameter val is of type java.lang.Double\n" +
                "  /* return type is of type java.lang.Double */\n" +
                "  if (input == null) {\n" +
                "    return null;\n" +
                "  }\n" +
                "  return Math.sin( input );\n" +
                "';");

        // just check created function
        assertRows(execute("SELECT key, val, " + fName + "(val) FROM %s"),
                   row(1, 1d, Math.sin(1d)),
                   row(2, 2d, Math.sin(2d)),
                   row(3, 3d, Math.sin(3d))
        );

        execute("CREATE OR REPLACE FUNCTION " + fName + "( input double ) " +
                "CALLED ON NULL INPUT " +
                "RETURNS double " +
                "LANGUAGE java\n" +
                "AS '\n" +
                "  return input;\n" +
                "';");

        // check if replaced function returns correct result
        assertRows(execute("SELECT key, val, " + fName + "(val) FROM %s"),
                   row(1, 1d, 1d),
                   row(2, 2d, 2d),
                   row(3, 3d, 3d)
        );
    }

    @Test
    public void testJavaFunctionNoParameters() throws Throwable
    {
        createTable("CREATE TABLE %s (key int primary key, val double)");

        String functionBody = "\n  return 1L;\n";

        String fName = createFunction(KEYSPACE, "",
                                      "CREATE OR REPLACE FUNCTION %s() " +
                                      "RETURNS NULL ON NULL INPUT " +
                                      "RETURNS bigint " +
                                      "LANGUAGE JAVA\n" +
                                      "AS '" +functionBody + "';");

        assertRows(execute("SELECT language, body FROM system_schema.functions WHERE keyspace_name=? AND function_name=?",
                           KEYSPACE, parseFunctionName(fName).name),
                   row("java", functionBody));

        execute("INSERT INTO %s (key, val) VALUES (?, ?)", 1, 1d);
        execute("INSERT INTO %s (key, val) VALUES (?, ?)", 2, 2d);
        execute("INSERT INTO %s (key, val) VALUES (?, ?)", 3, 3d);
        assertRows(execute("SELECT key, val, " + fName + "() FROM %s"),
                   row(1, 1d, 1L),
                   row(2, 2d, 1L),
                   row(3, 3d, 1L)
        );
    }

    @Test
    public void testJavaFunctionInvalidBodies() throws Throwable
    {
        try
        {
            execute("CREATE OR REPLACE FUNCTION " + KEYSPACE + ".jfinv() " +
                    "RETURNS NULL ON NULL INPUT " +
                    "RETURNS bigint " +
                    "LANGUAGE JAVA\n" +
                    "AS '\n" +
                    "foobarbaz" +
                    "\n';");
            Assert.fail();
        }
        catch (InvalidRequestException e)
        {
            Assert.assertTrue(e.getMessage(), e.getMessage().contains("Java source compilation failed"));
            Assert.assertTrue(e.getMessage(), e.getMessage().contains("insert \";\" to complete BlockStatements"));
        }

        try
        {
            execute("CREATE OR REPLACE FUNCTION " + KEYSPACE + ".jfinv() " +
                    "RETURNS NULL ON NULL INPUT " +
                    "RETURNS bigint " +
                    "LANGUAGE JAVA\n" +
                    "AS '\n" +
                    "foobarbaz;" +
                    "\n';");
            Assert.fail();
        }
        catch (InvalidRequestException e)
        {
            Assert.assertTrue(e.getMessage(), e.getMessage().contains("Java source compilation failed"));
            Assert.assertTrue(e.getMessage(), e.getMessage().contains("foobarbaz cannot be resolved to a type"));
        }
    }

    @Test
    public void testJavaFunctionInvalidReturn() throws Throwable
    {
        assertInvalidMessage("system keyspace is not user-modifiable",
                             "CREATE OR REPLACE FUNCTION jfir(val double) " +
                             "RETURNS NULL ON NULL INPUT " +
                             "RETURNS double " +
                             "LANGUAGE JAVA\n" +
                             "AS 'return 1L;';");
    }

    @Test
    public void testJavaFunctionArgumentTypeMismatch() throws Throwable
    {
        createTable("CREATE TABLE %s (key int primary key, val bigint)");

        String fName = createFunction(KEYSPACE, "double",
                                      "CREATE OR REPLACE FUNCTION %s(val double)" +
                                      "RETURNS NULL ON NULL INPUT " +
                                      "RETURNS double " +
                                      "LANGUAGE JAVA " +
                                      "AS 'return Double.valueOf(val);';");

        execute("INSERT INTO %s (key, val) VALUES (?, ?)", 1, 1L);
        execute("INSERT INTO %s (key, val) VALUES (?, ?)", 2, 2L);
        execute("INSERT INTO %s (key, val) VALUES (?, ?)", 3, 3L);
        assertInvalidMessage("val cannot be passed as argument 0 of function",
                             "SELECT key, val, " + fName + "(val) FROM %s");
    }

    @Test
    public void testJavaFunction() throws Throwable
    {
        createTable("CREATE TABLE %s (key int primary key, val double)");

        String functionBody = '\n' +
                              "  // parameter val is of type java.lang.Double\n" +
                              "  /* return type is of type java.lang.Double */\n" +
                              "  if (val == null) {\n" +
                              "    return null;\n" +
                              "  }\n" +
                              "  return Math.sin(val);\n";

        String fName = createFunction(KEYSPACE, "double",
                                      "CREATE OR REPLACE FUNCTION %s(val double) " +
                                      "CALLED ON NULL INPUT " +
                                      "RETURNS double " +
                                      "LANGUAGE JAVA " +
                                      "AS '" + functionBody + "';");

        FunctionName fNameName = parseFunctionName(fName);

        assertRows(execute("SELECT language, body FROM system_schema.functions WHERE keyspace_name=? AND function_name=?",
                           fNameName.keyspace, fNameName.name),
                   row("java", functionBody));

        execute("INSERT INTO %s (key, val) VALUES (?, ?)", 1, 1d);
        execute("INSERT INTO %s (key, val) VALUES (?, ?)", 2, 2d);
        execute("INSERT INTO %s (key, val) VALUES (?, ?)", 3, 3d);
        assertRows(execute("SELECT key, val, " + fName + "(val) FROM %s"),
                   row(1, 1d, Math.sin(1d)),
                   row(2, 2d, Math.sin(2d)),
                   row(3, 3d, Math.sin(3d))
        );
    }

    @Test
    public void testFunctionInTargetKeyspace() throws Throwable
    {
        createTable("CREATE TABLE %s (key int primary key, val double)");

        execute("CREATE TABLE " + KEYSPACE_PER_TEST + ".second_tab (key int primary key, val double)");

        String fName = createFunction(KEYSPACE_PER_TEST, "double",
                                      "CREATE OR REPLACE FUNCTION %s(val double) " +
                                      "RETURNS NULL ON NULL INPUT " +
                                      "RETURNS double " +
                                      "LANGUAGE JAVA " +
                                      "AS 'return Double.valueOf(val);';");

        execute("INSERT INTO %s (key, val) VALUES (?, ?)", 1, 1d);
        execute("INSERT INTO %s (key, val) VALUES (?, ?)", 2, 2d);
        execute("INSERT INTO %s (key, val) VALUES (?, ?)", 3, 3d);
        assertInvalidMessage("Unknown function",
                             "SELECT key, val, " + parseFunctionName(fName).name + "(val) FROM %s");

        execute("INSERT INTO " + KEYSPACE_PER_TEST + ".second_tab (key, val) VALUES (?, ?)", 1, 1d);
        execute("INSERT INTO " + KEYSPACE_PER_TEST + ".second_tab (key, val) VALUES (?, ?)", 2, 2d);
        execute("INSERT INTO " + KEYSPACE_PER_TEST + ".second_tab (key, val) VALUES (?, ?)", 3, 3d);
        assertRows(execute("SELECT key, val, " + fName + "(val) FROM " + KEYSPACE_PER_TEST + ".second_tab"),
                   row(1, 1d, 1d),
                   row(2, 2d, 2d),
                   row(3, 3d, 3d)
        );
    }

    @Test
    public void testFunctionWithReservedName() throws Throwable
    {
        execute("CREATE TABLE " + KEYSPACE_PER_TEST + ".second_tab (key int primary key, val double)");

        String fName = createFunction(KEYSPACE_PER_TEST, "",
                                      "CREATE OR REPLACE FUNCTION %s() " +
                                      "RETURNS NULL ON NULL INPUT " +
                                      "RETURNS timestamp " +
                                      "LANGUAGE JAVA " +
                                      "AS 'return null;';");

        execute("INSERT INTO " + KEYSPACE_PER_TEST + ".second_tab (key, val) VALUES (?, ?)", 1, 1d);
        execute("INSERT INTO " + KEYSPACE_PER_TEST + ".second_tab (key, val) VALUES (?, ?)", 2, 2d);
        execute("INSERT INTO " + KEYSPACE_PER_TEST + ".second_tab (key, val) VALUES (?, ?)", 3, 3d);

        // ensure that system now() is executed
        UntypedResultSet rows = execute("SELECT key, val, now() FROM " + KEYSPACE_PER_TEST + ".second_tab");
        Assert.assertEquals(3, rows.size());
        UntypedResultSet.Row row = rows.iterator().next();
        Date ts = row.getTimestamp(row.getColumns().get(2).name.toString());
        Assert.assertNotNull(ts);

        // ensure that KEYSPACE_PER_TEST's now() is executed
        rows = execute("SELECT key, val, " + fName + "() FROM " + KEYSPACE_PER_TEST + ".second_tab");
        Assert.assertEquals(3, rows.size());
        row = rows.iterator().next();
        Assert.assertFalse(row.has(row.getColumns().get(2).name.toString()));
    }

    @Test
    public void testFunctionInSystemKS() throws Throwable
    {
        execute("CREATE OR REPLACE FUNCTION " + KEYSPACE + ".totimestamp(val timeuuid) " +
                "RETURNS NULL ON NULL INPUT " +
                "RETURNS timestamp " +
                "LANGUAGE JAVA\n" +

                "AS 'return null;';");

        assertInvalidMessage("system keyspace is not user-modifiable",
                             "CREATE OR REPLACE FUNCTION system.jnft(val double) " +
                             "RETURNS NULL ON NULL INPUT " +
                             "RETURNS double " +
                             "LANGUAGE JAVA\n" +
                             "AS 'return null;';");
        assertInvalidMessage("system keyspace is not user-modifiable",
                             "CREATE OR REPLACE FUNCTION system.totimestamp(val timeuuid) " +
                             "RETURNS NULL ON NULL INPUT " +
                             "RETURNS timestamp " +
                             "LANGUAGE JAVA\n" +

                             "AS 'return null;';");
        assertInvalidMessage("system keyspace is not user-modifiable",
                             "DROP FUNCTION system.now");

        // KS for executeInternal() is system
        assertInvalidMessage("system keyspace is not user-modifiable",
                             "CREATE OR REPLACE FUNCTION jnft(val double) " +
                             "RETURNS NULL ON NULL INPUT " +
                             "RETURNS double " +
                             "LANGUAGE JAVA\n" +
                             "AS 'return null;';");
        assertInvalidMessage("system keyspace is not user-modifiable",
                             "CREATE OR REPLACE FUNCTION totimestamp(val timeuuid) " +
                             "RETURNS NULL ON NULL INPUT " +
                             "RETURNS timestamp " +
                             "LANGUAGE JAVA\n" +
                             "AS 'return null;';");
        assertInvalidMessage("system keyspace is not user-modifiable",
                             "DROP FUNCTION now");
    }

    @Test
    public void testFunctionNonExistingKeyspace() throws Throwable
    {
        assertInvalidMessage("to non existing keyspace",
                             "CREATE OR REPLACE FUNCTION this_ks_does_not_exist.jnft(val double) " +
                             "RETURNS NULL ON NULL INPUT " +
                             "RETURNS double " +
                             "LANGUAGE JAVA\n" +
                             "AS 'return null;';");
    }

    @Test
    public void testFunctionAfterOnDropKeyspace() throws Throwable
    {
        dropPerTestKeyspace();

        assertInvalidMessage("to non existing keyspace",
                             "CREATE OR REPLACE FUNCTION " + KEYSPACE_PER_TEST + ".jnft(val double) " +
                             "RETURNS NULL ON NULL INPUT " +
                             "RETURNS double " +
                             "LANGUAGE JAVA\n" +
                             "AS 'return null;';");
    }

    @Test
    public void testJavaKeyspaceFunction() throws Throwable
    {
        createTable("CREATE TABLE %s (key int primary key, val double)");

        String functionBody = '\n' +
                              "  // parameter val is of type java.lang.Double\n" +
                              "  /* return type is of type java.lang.Double */\n" +
                              "  if (val == null) {\n" +
                              "    return null;\n" +
                              "  }\n" +
                              "  return Math.sin( val );\n";

        String fName = createFunction(KEYSPACE_PER_TEST, "double",
                                     "CREATE OR REPLACE FUNCTION %s(val double) " +
                                     "CALLED ON NULL INPUT " +
                                     "RETURNS double " +
                                     "LANGUAGE JAVA " +
                                     "AS '" + functionBody + "';");

        FunctionName fNameName = parseFunctionName(fName);

        assertRows(execute("SELECT language, body FROM system_schema.functions WHERE keyspace_name=? AND function_name=?",
                           fNameName.keyspace, fNameName.name),
                   row("java", functionBody));

        execute("INSERT INTO %s (key, val) VALUES (?, ?)", 1, 1d);
        execute("INSERT INTO %s (key, val) VALUES (?, ?)", 2, 2d);
        execute("INSERT INTO %s (key, val) VALUES (?, ?)", 3, 3d);
        assertRows(execute("SELECT key, val, " + fName + "(val) FROM %s"),
                   row(1, 1d, Math.sin(1d)),
                   row(2, 2d, Math.sin(2d)),
                   row(3, 3d, Math.sin(3d))
        );
    }

    @Test
    public void testJavaRuntimeException() throws Throwable
    {
        createTable("CREATE TABLE %s (key int primary key, val double)");

        String functionBody = '\n' +
                              "  throw new RuntimeException(\"oh no!\");\n";

        String fName = createFunction(KEYSPACE_PER_TEST, "double",
                                      "CREATE OR REPLACE FUNCTION %s(val double) " +
                                      "RETURNS NULL ON NULL INPUT " +
                                      "RETURNS double " +
                                      "LANGUAGE JAVA\n" +
                                      "AS '" + functionBody + "';");

        FunctionName fNameName = parseFunctionName(fName);

        assertRows(execute("SELECT language, body FROM system_schema.functions WHERE keyspace_name=? AND function_name=?",
                           fNameName.keyspace, fNameName.name),
                   row("java", functionBody));

        execute("INSERT INTO %s (key, val) VALUES (?, ?)", 1, 1d);
        execute("INSERT INTO %s (key, val) VALUES (?, ?)", 2, 2d);
        execute("INSERT INTO %s (key, val) VALUES (?, ?)", 3, 3d);

        // function throws a RuntimeException which is wrapped by FunctionExecutionException
        assertInvalidThrowMessage("java.lang.RuntimeException: oh no", FunctionExecutionException.class,
                                  "SELECT key, val, " + fName + "(val) FROM %s");
    }

    @Test
    public void testJavaDollarQuotedFunction() throws Throwable
    {
        String functionBody = '\n' +
                              "  // parameter val is of type java.lang.Double\n" +
                              "  /* return type is of type java.lang.Double */\n" +
                              "  if (input == null) {\n" +
                              "    return null;\n" +
                              "  }\n" +
                              "  return \"'\"+Math.sin(input)+'\\\'';\n";

        String fName = createFunction(KEYSPACE_PER_TEST, "double",
                                      "CREATE FUNCTION %s( input double ) " +
                                      "CALLED ON NULL INPUT " +
                                      "RETURNS text " +
                                      "LANGUAGE java\n" +
                                      "AS $$" + functionBody + "$$;");

        FunctionName fNameName = parseFunctionName(fName);

        assertRows(execute("SELECT language, body FROM system_schema.functions WHERE keyspace_name=? AND function_name=?",
                           fNameName.keyspace, fNameName.name),
                   row("java", functionBody));
    }

    @Test
    public void testJavaSimpleCollections() throws Throwable
    {
        createTable("CREATE TABLE %s (key int primary key, lst list<double>, st set<text>, mp map<int, boolean>)");

        String fList = createFunction(KEYSPACE_PER_TEST, "list<double>",
                                     "CREATE FUNCTION %s( lst list<double> ) " +
                                     "RETURNS NULL ON NULL INPUT " +
                                     "RETURNS list<double> " +
                                     "LANGUAGE java\n" +
                                     "AS $$return lst;$$;");
        String fSet = createFunction(KEYSPACE_PER_TEST, "set<text>",
                                     "CREATE FUNCTION %s( st set<text> ) " +
                                     "RETURNS NULL ON NULL INPUT " +
                                     "RETURNS set<text> " +
                                     "LANGUAGE java\n" +
                                     "AS $$return st;$$;");
        String fMap = createFunction(KEYSPACE_PER_TEST, "map<int, boolean>",
                                     "CREATE FUNCTION %s( mp map<int, boolean> ) " +
                                     "RETURNS NULL ON NULL INPUT " +
                                     "RETURNS map<int, boolean> " +
                                     "LANGUAGE java\n" +
                                     "AS $$return mp;$$;");

        List<Double> list = Arrays.asList(1d, 2d, 3d);
        Set<String> set = new TreeSet<>(Arrays.asList("one", "three", "two"));
        Map<Integer, Boolean> map = new TreeMap<>();
        map.put(1, true);
        map.put(2, false);
        map.put(3, true);

        execute("INSERT INTO %s (key, lst, st, mp) VALUES (1, ?, ?, ?)", list, set, map);

        assertRows(execute("SELECT " + fList + "(lst), " + fSet + "(st), " + fMap + "(mp) FROM %s WHERE key = 1"),
                   row(list, set, map));

        // same test - but via native protocol
        for (int version = Server.VERSION_2; version <= maxProtocolVersion; version++)
            assertRowsNet(version,
                          executeNet(version, "SELECT " + fList + "(lst), " + fSet + "(st), " + fMap + "(mp) FROM %s WHERE key = 1"),
                          row(list, set, map));
    }

    @Test
    public void testWrongKeyspace() throws Throwable
    {
        String typeName = createType("CREATE TYPE %s (txt text, i int)");
        String type = KEYSPACE + '.' + typeName;

        assertInvalidMessage(String.format("Statement on keyspace %s cannot refer to a user type in keyspace %s; user types can only be used in the keyspace they are defined in",
                                           KEYSPACE_PER_TEST, KEYSPACE),
                             "CREATE FUNCTION " + KEYSPACE_PER_TEST + ".test_wrong_ks( val int ) " +
                             "CALLED ON NULL INPUT " +
                             "RETURNS " + type + " " +
                             "LANGUAGE java\n" +
                             "AS $$return val;$$;");

        assertInvalidMessage(String.format("Statement on keyspace %s cannot refer to a user type in keyspace %s; user types can only be used in the keyspace they are defined in",
                                           KEYSPACE_PER_TEST, KEYSPACE),
                             "CREATE FUNCTION " + KEYSPACE_PER_TEST + ".test_wrong_ks( val " + type + " ) " +
                             "CALLED ON NULL INPUT " +
                             "RETURNS int " +
                             "LANGUAGE java\n" +
                             "AS $$return val;$$;");
    }

    @Test
    public void testComplexNullValues() throws Throwable
    {
        String type = KEYSPACE + '.' + createType("CREATE TYPE %s (txt text, i int)");

        createTable("CREATE TABLE %s (key int primary key, lst list<double>, st set<text>, mp map<int, boolean>," +
                    "tup frozen<tuple<double, text, int, boolean>>, udt frozen<" + type + ">)");

        String fList = createFunction(KEYSPACE, "list<double>",
                                      "CREATE FUNCTION %s( coll list<double> ) " +
                                      "CALLED ON NULL INPUT " +
                                      "RETURNS list<double> " +
                                      "LANGUAGE java\n" +
                                      "AS $$return coll;$$;");
        String fSet = createFunction(KEYSPACE, "set<text>",
                                     "CREATE FUNCTION %s( coll set<text> ) " +
                                     "CALLED ON NULL INPUT " +
                                     "RETURNS set<text> " +
                                     "LANGUAGE java\n" +
                                     "AS $$return coll;$$;");
        String fMap = createFunction(KEYSPACE, "map<int, boolean>",
                                     "CREATE FUNCTION %s( coll map<int, boolean> ) " +
                                     "CALLED ON NULL INPUT " +
                                     "RETURNS map<int, boolean> " +
                                     "LANGUAGE java\n" +
                                     "AS $$return coll;$$;");
        String fTup = createFunction(KEYSPACE, "tuple<double, text, int, boolean>",
                                     "CREATE FUNCTION %s( val tuple<double, text, int, boolean> ) " +
                                     "CALLED ON NULL INPUT " +
                                     "RETURNS tuple<double, text, int, boolean> " +
                                     "LANGUAGE java\n" +
                                     "AS $$return val;$$;");
        String fUdt = createFunction(KEYSPACE, type,
                                     "CREATE FUNCTION %s( val " + type + " ) " +
                                     "CALLED ON NULL INPUT " +
                                     "RETURNS " + type + " " +
                                     "LANGUAGE java\n" +
                                     "AS $$return val;$$;");
        List<Double> list = Arrays.asList(1d, 2d, 3d);
        Set<String> set = new TreeSet<>(Arrays.asList("one", "three", "two"));
        Map<Integer, Boolean> map = new TreeMap<>();
        map.put(1, true);
        map.put(2, false);
        map.put(3, true);
        Object t = tuple(1d, "one", 42, false);

        execute("INSERT INTO %s (key, lst, st, mp, tup, udt) VALUES (1, ?, ?, ?, ?, {txt: 'one', i:1})", list, set, map, t);
        execute("INSERT INTO %s (key, lst, st, mp, tup, udt) VALUES (2, ?, ?, ?, ?, null)", null, null, null, null);

        execute("SELECT " +
                fList + "(lst), " +
                fSet + "(st), " +
                fMap + "(mp), " +
                fTup + "(tup), " +
                fUdt + "(udt) FROM %s WHERE key = 1");
        UntypedResultSet.Row row = execute("SELECT " +
                                           fList + "(lst) as l, " +
                                           fSet + "(st) as s, " +
                                           fMap + "(mp) as m, " +
                                           fTup + "(tup) as t, " +
                                           fUdt + "(udt) as u " +
                                           "FROM %s WHERE key = 1").one();
        Assert.assertNotNull(row.getBytes("l"));
        Assert.assertNotNull(row.getBytes("s"));
        Assert.assertNotNull(row.getBytes("m"));
        Assert.assertNotNull(row.getBytes("t"));
        Assert.assertNotNull(row.getBytes("u"));
        row = execute("SELECT " +
                      fList + "(lst) as l, " +
                      fSet + "(st) as s, " +
                      fMap + "(mp) as m, " +
                      fTup + "(tup) as t, " +
                      fUdt + "(udt) as u " +
                      "FROM %s WHERE key = 2").one();
        Assert.assertNull(row.getBytes("l"));
        Assert.assertNull(row.getBytes("s"));
        Assert.assertNull(row.getBytes("m"));
        Assert.assertNull(row.getBytes("t"));
        Assert.assertNull(row.getBytes("u"));

        for (int version = Server.VERSION_2; version <= maxProtocolVersion; version++)
        {
            Row r = executeNet(version, "SELECT " +
                                        fList + "(lst) as l, " +
                                        fSet + "(st) as s, " +
                                        fMap + "(mp) as m, " +
                                        fTup + "(tup) as t, " +
                                        fUdt + "(udt) as u " +
                                        "FROM %s WHERE key = 1").one();
            Assert.assertNotNull(r.getBytesUnsafe("l"));
            Assert.assertNotNull(r.getBytesUnsafe("s"));
            Assert.assertNotNull(r.getBytesUnsafe("m"));
            Assert.assertNotNull(r.getBytesUnsafe("t"));
            Assert.assertNotNull(r.getBytesUnsafe("u"));
            r = executeNet(version, "SELECT " +
                                    fList + "(lst) as l, " +
                                    fSet + "(st) as s, " +
                                    fMap + "(mp) as m, " +
                                    fTup + "(tup) as t, " +
                                    fUdt + "(udt) as u " +
                                    "FROM %s WHERE key = 2").one();
            Assert.assertNull(r.getBytesUnsafe("l"));
            Assert.assertNull(r.getBytesUnsafe("s"));
            Assert.assertNull(r.getBytesUnsafe("m"));
            Assert.assertNull(r.getBytesUnsafe("t"));
            Assert.assertNull(r.getBytesUnsafe("u"));
        }
    }

    @Test
    public void testJavaTupleType() throws Throwable
    {
        createTable("CREATE TABLE %s (key int primary key, tup frozen<tuple<double, text, int, boolean>>)");

        String fName = createFunction(KEYSPACE, "tuple<double, text, int, boolean>",
                                     "CREATE FUNCTION %s( tup tuple<double, text, int, boolean> ) " +
                                     "RETURNS NULL ON NULL INPUT " +
                                     "RETURNS tuple<double, text, int, boolean> " +
                                     "LANGUAGE java\n" +
                                     "AS $$return tup;$$;");

        Object t = tuple(1d, "foo", 2, true);

        execute("INSERT INTO %s (key, tup) VALUES (1, ?)", t);

        assertRows(execute("SELECT tup FROM %s WHERE key = 1"),
                   row(t));

        assertRows(execute("SELECT " + fName + "(tup) FROM %s WHERE key = 1"),
                   row(t));
    }

    @Test
    public void testJavaTupleTypeCollection() throws Throwable
    {
        String tupleTypeDef = "tuple<double, list<double>, set<text>, map<int, boolean>>";

        createTable("CREATE TABLE %s (key int primary key, tup frozen<" + tupleTypeDef + ">)");

        String fTup0 = createFunction(KEYSPACE_PER_TEST, tupleTypeDef,
                "CREATE FUNCTION %s( tup " + tupleTypeDef + " ) " +
                "CALLED ON NULL INPUT " +
                "RETURNS " + tupleTypeDef + ' ' +
                "LANGUAGE java\n" +
                "AS $$return " +
                "       tup;$$;");
        String fTup1 = createFunction(KEYSPACE_PER_TEST, tupleTypeDef,
                "CREATE FUNCTION %s( tup " + tupleTypeDef + " ) " +
                "CALLED ON NULL INPUT " +
                "RETURNS double " +
                "LANGUAGE java\n" +
                "AS $$return " +
                "       Double.valueOf(tup.getDouble(0));$$;");
        String fTup2 = createFunction(KEYSPACE_PER_TEST, tupleTypeDef,
                                      "CREATE FUNCTION %s( tup " + tupleTypeDef + " ) " +
                                      "RETURNS NULL ON NULL INPUT " +
                                      "RETURNS list<double> " +
                                      "LANGUAGE java\n" +
                                      "AS $$return " +
                                      "       tup.getList(1, Double.class);$$;");
        String fTup3 = createFunction(KEYSPACE_PER_TEST, tupleTypeDef,
                "CREATE FUNCTION %s( tup " + tupleTypeDef + " ) " +
                "RETURNS NULL ON NULL INPUT " +
                "RETURNS set<text> " +
                "LANGUAGE java\n" +
                "AS $$return " +
                "       tup.getSet(2, String.class);$$;");
        String fTup4 = createFunction(KEYSPACE_PER_TEST, tupleTypeDef,
                "CREATE FUNCTION %s( tup " + tupleTypeDef + " ) " +
                "RETURNS NULL ON NULL INPUT " +
                "RETURNS map<int, boolean> " +
                "LANGUAGE java\n" +
                "AS $$return " +
                "       tup.getMap(3, Integer.class, Boolean.class);$$;");

        List<Double> list = Arrays.asList(1d, 2d, 3d);
        Set<String> set = new TreeSet<>(Arrays.asList("one", "three", "two"));
        Map<Integer, Boolean> map = new TreeMap<>();
        map.put(1, true);
        map.put(2, false);
        map.put(3, true);

        Object t = tuple(1d, list, set, map);

        execute("INSERT INTO %s (key, tup) VALUES (1, ?)", t);

        assertRows(execute("SELECT " + fTup0 + "(tup) FROM %s WHERE key = 1"),
                   row(t));
        assertRows(execute("SELECT " + fTup1 + "(tup) FROM %s WHERE key = 1"),
                   row(1d));
        assertRows(execute("SELECT " + fTup2 + "(tup) FROM %s WHERE key = 1"),
                   row(list));
        assertRows(execute("SELECT " + fTup3 + "(tup) FROM %s WHERE key = 1"),
                   row(set));
        assertRows(execute("SELECT " + fTup4 + "(tup) FROM %s WHERE key = 1"),
                   row(map));

        TupleType tType = TupleType.of(DataType.cdouble(),
                                       DataType.list(DataType.cdouble()),
                                       DataType.set(DataType.text()),
                                       DataType.map(DataType.cint(), DataType.cboolean()));
        TupleValue tup = tType.newValue(1d, list, set, map);
        for (int version = Server.VERSION_2; version <= maxProtocolVersion; version++)
        {
            assertRowsNet(version,
                          executeNet(version, "SELECT " + fTup0 + "(tup) FROM %s WHERE key = 1"),
                          row(tup));
            assertRowsNet(version,
                          executeNet(version, "SELECT " + fTup1 + "(tup) FROM %s WHERE key = 1"),
                          row(1d));
            assertRowsNet(version,
                          executeNet(version, "SELECT " + fTup2 + "(tup) FROM %s WHERE key = 1"),
                          row(list));
            assertRowsNet(version,
                          executeNet(version, "SELECT " + fTup3 + "(tup) FROM %s WHERE key = 1"),
                          row(set));
            assertRowsNet(version,
                          executeNet(version, "SELECT " + fTup4 + "(tup) FROM %s WHERE key = 1"),
                          row(map));
        }
    }

    @Test
    public void testJavaUserTypeWithUse() throws Throwable
    {
        String type = createType("CREATE TYPE %s (txt text, i int)");
        createTable("CREATE TABLE %s (key int primary key, udt frozen<" + KEYSPACE + '.' + type + ">)");
        execute("INSERT INTO %s (key, udt) VALUES (1, {txt: 'one', i:1})");

        for (int version = Server.VERSION_2; version <= maxProtocolVersion; version++)
        {
            executeNet(version, "USE " + KEYSPACE);

            executeNet(version,
                       "CREATE FUNCTION f_use1( udt " + type + " ) " +
                       "RETURNS NULL ON NULL INPUT " +
                       "RETURNS " + type + " " +
                       "LANGUAGE java " +
                       "AS $$return " +
                       "     udt;$$;");
            try
            {
                List<Row> rowsNet = executeNet(version, "SELECT f_use1(udt) FROM %s WHERE key = 1").all();
                Assert.assertEquals(1, rowsNet.size());
                UDTValue udtVal = rowsNet.get(0).getUDTValue(0);
                Assert.assertEquals("one", udtVal.getString("txt"));
                Assert.assertEquals(1, udtVal.getInt("i"));
            }
            finally
            {
                executeNet(version, "DROP FUNCTION f_use1");
            }
        }
    }

    @Test
    public void testJavaUserType() throws Throwable
    {
        String type = KEYSPACE + '.' + createType("CREATE TYPE %s (txt text, i int)");

        createTable("CREATE TABLE %s (key int primary key, udt frozen<" + type + ">)");

        String fUdt0 = createFunction(KEYSPACE, type,
                                      "CREATE FUNCTION %s( udt " + type + " ) " +
                                      "RETURNS NULL ON NULL INPUT " +
                                      "RETURNS " + type + " " +
                                      "LANGUAGE java " +
                                      "AS $$return " +
                                      "     udt;$$;");
        String fUdt1 = createFunction(KEYSPACE, type,
                                      "CREATE FUNCTION %s( udt " + type + ") " +
                                      "RETURNS NULL ON NULL INPUT " +
                                      "RETURNS text " +
                                      "LANGUAGE java " +
                                      "AS $$return " +
                                      "     udt.getString(\"txt\");$$;");
        String fUdt2 = createFunction(KEYSPACE, type,
                                      "CREATE FUNCTION %s( udt " + type + ") " +
                                      "CALLED ON NULL INPUT " +
                                      "RETURNS int " +
                                      "LANGUAGE java " +
                                      "AS $$return " +
                                      "     Integer.valueOf(udt.getInt(\"i\"));$$;");

        execute("INSERT INTO %s (key, udt) VALUES (1, {txt: 'one', i:1})");

        UntypedResultSet rows = execute("SELECT " + fUdt0 + "(udt) FROM %s WHERE key = 1");
        Assert.assertEquals(1, rows.size());
        assertRows(execute("SELECT " + fUdt1 + "(udt) FROM %s WHERE key = 1"),
                   row("one"));
        assertRows(execute("SELECT " + fUdt2 + "(udt) FROM %s WHERE key = 1"),
                   row(1));

        for (int version = Server.VERSION_2; version <= maxProtocolVersion; version++)
        {
            List<Row> rowsNet = executeNet(version, "SELECT " + fUdt0 + "(udt) FROM %s WHERE key = 1").all();
            Assert.assertEquals(1, rowsNet.size());
            UDTValue udtVal = rowsNet.get(0).getUDTValue(0);
            Assert.assertEquals("one", udtVal.getString("txt"));
            Assert.assertEquals(1, udtVal.getInt("i"));
            assertRowsNet(version,
                          executeNet(version, "SELECT " + fUdt1 + "(udt) FROM %s WHERE key = 1"),
                          row("one"));
            assertRowsNet(version,
                          executeNet(version, "SELECT " + fUdt2 + "(udt) FROM %s WHERE key = 1"),
                          row(1));
        }
    }

    @Test
    public void testUserTypeDrop() throws Throwable
    {
        String type = KEYSPACE + '.' + createType("CREATE TYPE %s (txt text, i int)");

        createTable("CREATE TABLE %s (key int primary key, udt frozen<" + type + ">)");

        String fName = createFunction(KEYSPACE, type,
                                      "CREATE FUNCTION %s( udt " + type + " ) " +
                                      "CALLED ON NULL INPUT " +
                                      "RETURNS int " +
                                      "LANGUAGE java " +
                                      "AS $$return " +
                                      "     Integer.valueOf(udt.getInt(\"i\"));$$;");

        FunctionName fNameName = parseFunctionName(fName);

        Assert.assertEquals(1, Schema.instance.getFunctions(fNameName).size());

        ResultMessage.Prepared prepared = QueryProcessor.prepare(String.format("SELECT key, %s(udt) FROM %s.%s", fName, KEYSPACE, currentTable()),
                                                                 ClientState.forInternalCalls(), false);
        Assert.assertNotNull(QueryProcessor.instance.getPrepared(prepared.statementId));

        // UT still referenced by table
        assertInvalidMessage("Cannot drop user type", "DROP TYPE " + type);

        execute("DROP TABLE %s");

        // UT still referenced by UDF
        assertInvalidMessage("as it is still used by function", "DROP TYPE " + type);

        Assert.assertNull(QueryProcessor.instance.getPrepared(prepared.statementId));

        // function stays
        Assert.assertEquals(1, Schema.instance.getFunctions(fNameName).size());
    }

    @Test
    public void testJavaUserTypeRenameField() throws Throwable
    {
        String type = KEYSPACE + '.' + createType("CREATE TYPE %s (txt text, i int)");

        createTable("CREATE TABLE %s (key int primary key, udt frozen<" + type + ">)");

        String fName = createFunction(KEYSPACE, type,
                                      "CREATE FUNCTION %s( udt " + type + " ) " +
                                      "RETURNS NULL ON NULL INPUT " +
                                      "RETURNS text " +
                                      "LANGUAGE java\n" +
                                      "AS $$return udt.getString(\"txt\");$$;");

        execute("INSERT INTO %s (key, udt) VALUES (1, {txt: 'one', i:1})");

        assertRows(execute("SELECT " + fName + "(udt) FROM %s WHERE key = 1"),
                   row("one"));

        execute("ALTER TYPE " + type + " RENAME txt TO str");

        assertInvalidMessage("txt is not a field defined in this UDT",
                             "SELECT " + fName + "(udt) FROM %s WHERE key = 1");

        execute("ALTER TYPE " + type + " RENAME str TO txt");

        assertRows(execute("SELECT " + fName + "(udt) FROM %s WHERE key = 1"),
                   row("one"));
    }

    @Test
    public void testJavaUserTypeAddFieldWithReplace() throws Throwable
    {
        String type = KEYSPACE + '.' + createType("CREATE TYPE %s (txt text, i int)");

        createTable("CREATE TABLE %s (key int primary key, udt frozen<" + type + ">)");

        String fName1replace = createFunction(KEYSPACE, type,
                                              "CREATE FUNCTION %s( udt " + type + ") " +
                                              "RETURNS NULL ON NULL INPUT " +
                                              "RETURNS text " +
                                              "LANGUAGE java\n" +
                                              "AS $$return udt.getString(\"txt\");$$;");
        String fName2replace = createFunction(KEYSPACE, type,
                                              "CREATE FUNCTION %s( udt " + type + " ) " +
                                              "CALLED ON NULL INPUT " +
                                              "RETURNS int " +
                                              "LANGUAGE java\n" +
                                              "AS $$return Integer.valueOf(udt.getInt(\"i\"));$$;");
        String fName3replace = createFunction(KEYSPACE, type,
                                              "CREATE FUNCTION %s( udt " + type + " ) " +
                                              "CALLED ON NULL INPUT " +
                                              "RETURNS double " +
                                              "LANGUAGE java\n" +
                                              "AS $$return Double.valueOf(udt.getDouble(\"added\"));$$;");
        String fName4replace = createFunction(KEYSPACE, type,
                                              "CREATE FUNCTION %s( udt " + type + " ) " +
                                              "RETURNS NULL ON NULL INPUT " +
                                              "RETURNS " + type + " " +
                                              "LANGUAGE java\n" +
                                              "AS $$return udt;$$;");

        String fName1noReplace = createFunction(KEYSPACE, type,
                                              "CREATE FUNCTION %s( udt " + type + " ) " +
                                              "RETURNS NULL ON NULL INPUT " +
                                              "RETURNS text " +
                                              "LANGUAGE java\n" +
                                              "AS $$return udt.getString(\"txt\");$$;");
        String fName2noReplace = createFunction(KEYSPACE, type,
                                              "CREATE FUNCTION %s( udt " + type + " ) " +
                                              "CALLED ON NULL INPUT " +
                                              "RETURNS int " +
                                              "LANGUAGE java\n" +
                                              "AS $$return Integer.valueOf(udt.getInt(\"i\"));$$;");
        String fName3noReplace = createFunction(KEYSPACE, type,
                                                "CREATE FUNCTION %s( udt " + type + " ) " +
                                                "CALLED ON NULL INPUT " +
                                                "RETURNS double " +
                                                "LANGUAGE java\n" +
                                                "AS $$return Double.valueOf(udt.getDouble(\"added\"));$$;");
        String fName4noReplace = createFunction(KEYSPACE, type,
                                                "CREATE FUNCTION %s( udt " + type + " ) " +
                                                "RETURNS NULL ON NULL INPUT " +
                                                "RETURNS " + type + " " +
                                                "LANGUAGE java\n" +
                                                "AS $$return udt;$$;");

        execute("INSERT INTO %s (key, udt) VALUES (1, {txt: 'one', i:1})");

        assertRows(execute("SELECT " + fName1replace + "(udt) FROM %s WHERE key = 1"),
                   row("one"));
        assertRows(execute("SELECT " + fName2replace + "(udt) FROM %s WHERE key = 1"),
                   row(1));

        // add field

        execute("ALTER TYPE " + type + " ADD added double");

        execute("INSERT INTO %s (key, udt) VALUES (2, {txt: 'two', i:2, added: 2})");

        // note: type references of functions remain at the state _before_ the type mutation
        // means we need to recreate the functions

        execute(String.format("CREATE OR REPLACE FUNCTION %s( udt %s ) " +
                              "RETURNS NULL ON NULL INPUT " +
                              "RETURNS text " +
                              "LANGUAGE java\n" +
                              "AS $$return " +
                              "     udt.getString(\"txt\");$$;",
                              fName1replace, type));
        Assert.assertEquals(1, Schema.instance.getFunctions(parseFunctionName(fName1replace)).size());
        execute(String.format("CREATE OR REPLACE FUNCTION %s( udt %s ) " +
                              "CALLED ON NULL INPUT " +
                              "RETURNS int " +
                              "LANGUAGE java\n" +
                              "AS $$return " +
                              "     Integer.valueOf(udt.getInt(\"i\"));$$;",
                              fName2replace, type));
        Assert.assertEquals(1, Schema.instance.getFunctions(parseFunctionName(fName2replace)).size());
        execute(String.format("CREATE OR REPLACE FUNCTION %s( udt %s ) " +
                              "CALLED ON NULL INPUT " +
                              "RETURNS double " +
                              "LANGUAGE java\n" +
                              "AS $$return " +
                              "     Double.valueOf(udt.getDouble(\"added\"));$$;",
                              fName3replace, type));
        Assert.assertEquals(1, Schema.instance.getFunctions(parseFunctionName(fName3replace)).size());
        execute(String.format("CREATE OR REPLACE FUNCTION %s( udt %s ) " +
                              "RETURNS NULL ON NULL INPUT " +
                              "RETURNS %s " +
                              "LANGUAGE java\n" +
                              "AS $$return " +
                              "     udt;$$;",
                              fName4replace, type, type));
        Assert.assertEquals(1, Schema.instance.getFunctions(parseFunctionName(fName4replace)).size());

        assertRows(execute("SELECT " + fName1replace + "(udt) FROM %s WHERE key = 2"),
                   row("two"));
        assertRows(execute("SELECT " + fName2replace + "(udt) FROM %s WHERE key = 2"),
                   row(2));
        assertRows(execute("SELECT " + fName3replace + "(udt) FROM %s WHERE key = 2"),
                   row(2d));
        assertRows(execute("SELECT " + fName3replace + "(udt) FROM %s WHERE key = 1"),
                   row(0d));

        // un-replaced functions will work since the user type has changed
        // and the UDF has exchanged the user type reference

        assertRows(execute("SELECT " + fName1noReplace + "(udt) FROM %s WHERE key = 2"),
                   row("two"));
        assertRows(execute("SELECT " + fName2noReplace + "(udt) FROM %s WHERE key = 2"),
                   row(2));
        assertRows(execute("SELECT " + fName3noReplace + "(udt) FROM %s WHERE key = 2"),
                   row(2d));
        assertRows(execute("SELECT " + fName3noReplace + "(udt) FROM %s WHERE key = 1"),
                   row(0d));

        execute("DROP FUNCTION " + fName1replace);
        execute("DROP FUNCTION " + fName2replace);
        execute("DROP FUNCTION " + fName3replace);
        execute("DROP FUNCTION " + fName4replace);
        execute("DROP FUNCTION " + fName1noReplace);
        execute("DROP FUNCTION " + fName2noReplace);
        execute("DROP FUNCTION " + fName3noReplace);
        execute("DROP FUNCTION " + fName4noReplace);
    }

    @Test
    public void testJavaUTCollections() throws Throwable
    {
        String type = KEYSPACE + '.' + createType("CREATE TYPE %s (txt text, i int)");

        createTable(String.format("CREATE TABLE %%s " +
                                  "(key int primary key, lst list<frozen<%s>>, st set<frozen<%s>>, mp map<int, frozen<%s>>)",
                                  type, type, type));

        String fName1 = createFunction(KEYSPACE, "list<frozen<" + type + ">>",
                              "CREATE FUNCTION %s( lst list<frozen<" + type + ">> ) " +
                              "RETURNS NULL ON NULL INPUT " +
                              "RETURNS text " +
                              "LANGUAGE java\n" +
                              "AS $$" +
                              "     com.datastax.driver.core.UDTValue udtVal = (com.datastax.driver.core.UDTValue)lst.get(1);" +
                              "     return udtVal.getString(\"txt\");$$;");
        String fName2 = createFunction(KEYSPACE, "set<frozen<" + type + ">>",
                                       "CREATE FUNCTION %s( st set<frozen<" + type + ">> ) " +
                                       "RETURNS NULL ON NULL INPUT " +
                                       "RETURNS text " +
                                       "LANGUAGE java\n" +
                                       "AS $$" +
                                       "     com.datastax.driver.core.UDTValue udtVal = (com.datastax.driver.core.UDTValue)st.iterator().next();" +
                                       "     return udtVal.getString(\"txt\");$$;");
        String fName3 = createFunction(KEYSPACE, "map<int, frozen<" + type + ">>",
                              "CREATE FUNCTION %s( mp map<int, frozen<" + type + ">> ) " +
                              "RETURNS NULL ON NULL INPUT " +
                              "RETURNS text " +
                              "LANGUAGE java\n" +
                              "AS $$" +
                              "     com.datastax.driver.core.UDTValue udtVal = (com.datastax.driver.core.UDTValue)mp.get(Integer.valueOf(3));" +
                              "     return udtVal.getString(\"txt\");$$;");

        execute("INSERT INTO %s (key, lst, st, mp) values (1, " +
                "[ {txt: 'one', i:1}, {txt: 'three', i:1}, {txt: 'one', i:1} ] , " +
                "{ {txt: 'one', i:1}, {txt: 'three', i:3}, {txt: 'two', i:2} }, " +
                "{ 1: {txt: 'one', i:1}, 2: {txt: 'one', i:3}, 3: {txt: 'two', i:2} })");

        assertRows(execute("SELECT " + fName1 + "(lst), " + fName2 + "(st), " + fName3 + "(mp) FROM %s WHERE key = 1"),
                   row("three", "one", "two"));

        for (int version = Server.VERSION_2; version <= maxProtocolVersion; version++)
            assertRowsNet(version,
                          executeNet(version, "SELECT " + fName1 + "(lst), " + fName2 + "(st), " + fName3 + "(mp) FROM %s WHERE key = 1"),
                          row("three", "one", "two"));
    }

    @Test
    public void testJavascriptSimpleCollections() throws Throwable
    {
        createTable("CREATE TABLE %s (key int primary key, lst list<double>, st set<text>, mp map<int, boolean>)");

        String fName1 = createFunction(KEYSPACE_PER_TEST, "list<double>",
                "CREATE FUNCTION %s( lst list<double> ) " +
                "RETURNS NULL ON NULL INPUT " +
                "RETURNS list<double> " +
                "LANGUAGE javascript\n" +
                "AS 'lst;';");
        String fName2 = createFunction(KEYSPACE_PER_TEST, "set<text>",
                "CREATE FUNCTION %s( st set<text> ) " +
                "RETURNS NULL ON NULL INPUT " +
                "RETURNS set<text> " +
                "LANGUAGE javascript\n" +
                "AS 'st;';");
        String fName3 = createFunction(KEYSPACE_PER_TEST, "map<int, boolean>",
                "CREATE FUNCTION %s( mp map<int, boolean> ) " +
                "RETURNS NULL ON NULL INPUT " +
                "RETURNS map<int, boolean> " +
                "LANGUAGE javascript\n" +
                "AS 'mp;';");

        List<Double> list = Arrays.asList(1d, 2d, 3d);
        Set<String> set = new TreeSet<>(Arrays.asList("one", "three", "two"));
        Map<Integer, Boolean> map = new TreeMap<>();
        map.put(1, true);
        map.put(2, false);
        map.put(3, true);

        execute("INSERT INTO %s (key, lst, st, mp) VALUES (1, ?, ?, ?)", list, set, map);

        assertRows(execute("SELECT lst, st, mp FROM %s WHERE key = 1"),
                   row(list, set, map));

        assertRows(execute("SELECT " + fName1 + "(lst), " + fName2 + "(st), " + fName3 + "(mp) FROM %s WHERE key = 1"),
                   row(list, set, map));

        for (int version = Server.VERSION_2; version <= maxProtocolVersion; version++)
            assertRowsNet(version,
                          executeNet(version, "SELECT " + fName1 + "(lst), " + fName2 + "(st), " + fName3 + "(mp) FROM %s WHERE key = 1"),
                          row(list, set, map));
    }

    @Test
    public void testJavascriptTupleType() throws Throwable
    {
        createTable("CREATE TABLE %s (key int primary key, tup frozen<tuple<double, text, int, boolean>>)");

        String fName = createFunction(KEYSPACE_PER_TEST, "tuple<double, text, int, boolean>",
                "CREATE FUNCTION %s( tup tuple<double, text, int, boolean> ) " +
                "RETURNS NULL ON NULL INPUT " +
                "RETURNS tuple<double, text, int, boolean> " +
                "LANGUAGE javascript\n" +
                "AS $$tup;$$;");

        Object t = tuple(1d, "foo", 2, true);

        execute("INSERT INTO %s (key, tup) VALUES (1, ?)", t);

        assertRows(execute("SELECT tup FROM %s WHERE key = 1"),
                   row(t));

        assertRows(execute("SELECT " + fName + "(tup) FROM %s WHERE key = 1"),
                   row(t));
    }

    @Test
    public void testJavascriptTupleTypeCollection() throws Throwable
    {
        String tupleTypeDef = "tuple<double, list<double>, set<text>, map<int, boolean>>";
        createTable("CREATE TABLE %s (key int primary key, tup frozen<" + tupleTypeDef + ">)");

        String fTup1 = createFunction(KEYSPACE_PER_TEST, tupleTypeDef,
                "CREATE FUNCTION %s( tup " + tupleTypeDef + " ) " +
                "RETURNS NULL ON NULL INPUT " +
                "RETURNS tuple<double, list<double>, set<text>, map<int, boolean>> " +
                "LANGUAGE javascript\n" +
                "AS $$" +
                "       tup;$$;");
        String fTup2 = createFunction(KEYSPACE_PER_TEST, tupleTypeDef,
                "CREATE FUNCTION %s( tup " + tupleTypeDef + " ) " +
                "RETURNS NULL ON NULL INPUT " +
                "RETURNS double " +
                "LANGUAGE javascript\n" +
                "AS $$" +
                "       tup.getDouble(0);$$;");
        String fTup3 = createFunction(KEYSPACE_PER_TEST, tupleTypeDef,
                "CREATE FUNCTION %s( tup " + tupleTypeDef + " ) " +
                "RETURNS NULL ON NULL INPUT " +
                "RETURNS list<double> " +
                "LANGUAGE javascript\n" +
                "AS $$" +
                "       tup.getList(1, java.lang.Class.forName(\"java.lang.Double\"));$$;");
        String fTup4 = createFunction(KEYSPACE_PER_TEST, tupleTypeDef,
                "CREATE FUNCTION %s( tup " + tupleTypeDef + " ) " +
                "RETURNS NULL ON NULL INPUT " +
                "RETURNS set<text> " +
                "LANGUAGE javascript\n" +
                "AS $$" +
                "       tup.getSet(2, java.lang.Class.forName(\"java.lang.String\"));$$;");
        String fTup5 = createFunction(KEYSPACE_PER_TEST, tupleTypeDef,
                "CREATE FUNCTION %s( tup " + tupleTypeDef + " ) " +
                "RETURNS NULL ON NULL INPUT " +
                "RETURNS map<int, boolean> " +
                "LANGUAGE javascript\n" +
                "AS $$" +
                "       tup.getMap(3, java.lang.Class.forName(\"java.lang.Integer\"), java.lang.Class.forName(\"java.lang.Boolean\"));$$;");

        List<Double> list = Arrays.asList(1d, 2d, 3d);
        Set<String> set = new TreeSet<>(Arrays.asList("one", "three", "two"));
        Map<Integer, Boolean> map = new TreeMap<>();
        map.put(1, true);
        map.put(2, false);
        map.put(3, true);

        Object t = tuple(1d, list, set, map);

        execute("INSERT INTO %s (key, tup) VALUES (1, ?)", t);

        assertRows(execute("SELECT " + fTup1 + "(tup) FROM %s WHERE key = 1"),
                   row(t));
        assertRows(execute("SELECT " + fTup2 + "(tup) FROM %s WHERE key = 1"),
                   row(1d));
        assertRows(execute("SELECT " + fTup3 + "(tup) FROM %s WHERE key = 1"),
                   row(list));
        assertRows(execute("SELECT " + fTup4 + "(tup) FROM %s WHERE key = 1"),
                   row(set));
        assertRows(execute("SELECT " + fTup5 + "(tup) FROM %s WHERE key = 1"),
                   row(map));

        // same test - but via native protocol
        TupleType tType = TupleType.of(DataType.cdouble(),
                                       DataType.list(DataType.cdouble()),
                                       DataType.set(DataType.text()),
                                       DataType.map(DataType.cint(), DataType.cboolean()));
        TupleValue tup = tType.newValue(1d, list, set, map);
        for (int version = Server.VERSION_2; version <= maxProtocolVersion; version++)
        {
            assertRowsNet(version,
                          executeNet(version, "SELECT " + fTup1 + "(tup) FROM %s WHERE key = 1"),
                          row(tup));
            assertRowsNet(version,
                          executeNet(version, "SELECT " + fTup2 + "(tup) FROM %s WHERE key = 1"),
                          row(1d));
            assertRowsNet(version,
                          executeNet(version, "SELECT " + fTup3 + "(tup) FROM %s WHERE key = 1"),
                          row(list));
            assertRowsNet(version,
                          executeNet(version, "SELECT " + fTup4 + "(tup) FROM %s WHERE key = 1"),
                          row(set));
            assertRowsNet(version,
                          executeNet(version, "SELECT " + fTup5 + "(tup) FROM %s WHERE key = 1"),
                          row(map));
        }
    }

    @Test
    public void testJavascriptUserType() throws Throwable
    {
        String type = createType("CREATE TYPE %s (txt text, i int)");

        createTable("CREATE TABLE %s (key int primary key, udt frozen<" + type + ">)");

        String fUdt1 = createFunction(KEYSPACE, type,
                              "CREATE FUNCTION %s( udt " + type + " ) " +
                              "RETURNS NULL ON NULL INPUT " +
                              "RETURNS " + type + " " +
                              "LANGUAGE javascript\n" +
                              "AS $$" +
                              "     udt;$$;");
        String fUdt2 = createFunction(KEYSPACE, type,
                              "CREATE FUNCTION %s( udt " + type + " ) " +
                              "RETURNS NULL ON NULL INPUT " +
                              "RETURNS text " +
                              "LANGUAGE javascript\n" +
                              "AS $$" +
                              "     udt.getString(\"txt\");$$;");
        String fUdt3 = createFunction(KEYSPACE, type,
                                      "CREATE FUNCTION %s( udt " + type + " ) " +
                                      "RETURNS NULL ON NULL INPUT " +
                                      "RETURNS int " +
                                      "LANGUAGE javascript\n" +
                                      "AS $$" +
                                      "     udt.getInt(\"i\");$$;");

        execute("INSERT INTO %s (key, udt) VALUES (1, {txt: 'one', i:1})");

        UntypedResultSet rows = execute("SELECT " + fUdt1 + "(udt) FROM %s WHERE key = 1");
        Assert.assertEquals(1, rows.size());
        assertRows(execute("SELECT " + fUdt2 + "(udt) FROM %s WHERE key = 1"),
                   row("one"));
        assertRows(execute("SELECT " + fUdt3 + "(udt) FROM %s WHERE key = 1"),
                   row(1));
    }

    @Test
    public void testJavascriptUTCollections() throws Throwable
    {
        String type = createType("CREATE TYPE %s (txt text, i int)");

        createTable(String.format("CREATE TABLE %%s " +
                                  "(key int primary key, lst list<frozen<%s>>, st set<frozen<%s>>, mp map<int, frozen<%s>>)",
                                  type, type, type));

        String fName = createFunction(KEYSPACE, "list<frozen<" + type + ">>",
                                      "CREATE FUNCTION %s( lst list<frozen<" + type + ">> ) " +
                                      "RETURNS NULL ON NULL INPUT " +
                                      "RETURNS text " +
                                      "LANGUAGE javascript\n" +
                                      "AS $$" +
                                      "        lst.get(1).getString(\"txt\");$$;");
        createFunctionOverload(fName, "set<frozen<" + type + ">>",
                               "CREATE FUNCTION %s( st set<frozen<" + type + ">> ) " +
                               "RETURNS NULL ON NULL INPUT " +
                               "RETURNS text " +
                               "LANGUAGE javascript\n" +
                               "AS $$" +
                               "        st.iterator().next().getString(\"txt\");$$;");
        createFunctionOverload(fName, "map<int, frozen<" + type + ">>",
                               "CREATE FUNCTION %s( mp map<int, frozen<" + type + ">> ) " +
                               "RETURNS NULL ON NULL INPUT " +
                               "RETURNS text " +
                               "LANGUAGE javascript\n" +
                               "AS $$" +
                               "        mp.get(java.lang.Integer.valueOf(3)).getString(\"txt\");$$;");

        execute("INSERT INTO %s (key, lst, st, mp) values (1, " +
                // list<frozen<UDT>>
                "[ {txt: 'one', i:1}, {txt: 'three', i:1}, {txt: 'one', i:1} ] , " +
                // set<frozen<UDT>>
                "{ {txt: 'one', i:1}, {txt: 'three', i:3}, {txt: 'two', i:2} }, " +
                // map<int, frozen<UDT>>
                "{ 1: {txt: 'one', i:1}, 2: {txt: 'one', i:3}, 3: {txt: 'two', i:2} })");

        assertRows(execute("SELECT " + fName + "(lst) FROM %s WHERE key = 1"),
                   row("three"));
        assertRows(execute("SELECT " + fName + "(st) FROM %s WHERE key = 1"),
                   row("one"));
        assertRows(execute("SELECT " + fName + "(mp) FROM %s WHERE key = 1"),
                   row("two"));

        String cqlSelect = "SELECT " + fName + "(lst), " + fName + "(st), " + fName + "(mp) FROM %s WHERE key = 1";
        assertRows(execute(cqlSelect),
                   row("three", "one", "two"));

        // same test - but via native protocol
        for (int version = Server.VERSION_2; version <= maxProtocolVersion; version++)
            assertRowsNet(version,
                          executeNet(version, cqlSelect),
                          row("three", "one", "two"));
    }

    @Test
    public void testJavascriptFunction() throws Throwable
    {
        createTable("CREATE TABLE %s (key int primary key, val double)");

        String functionBody = '\n' +
                              "  Math.sin(val);\n";

        String fName = createFunction(KEYSPACE, "double",
                                      "CREATE OR REPLACE FUNCTION %s(val double) " +
                                      "RETURNS NULL ON NULL INPUT " +
                                      "RETURNS double " +
                                      "LANGUAGE javascript\n" +
                                      "AS '" + functionBody + "';");

        FunctionName fNameName = parseFunctionName(fName);

        assertRows(execute("SELECT language, body FROM system_schema.functions WHERE keyspace_name=? AND function_name=?",
                           fNameName.keyspace, fNameName.name),
                   row("javascript", functionBody));

        execute("INSERT INTO %s (key, val) VALUES (?, ?)", 1, 1d);
        execute("INSERT INTO %s (key, val) VALUES (?, ?)", 2, 2d);
        execute("INSERT INTO %s (key, val) VALUES (?, ?)", 3, 3d);
        assertRows(execute("SELECT key, val, " + fName + "(val) FROM %s"),
                   row(1, 1d, Math.sin(1d)),
                   row(2, 2d, Math.sin(2d)),
                   row(3, 3d, Math.sin(3d))
        );
    }

    @Test
    public void testJavascriptBadReturnType() throws Throwable
    {
        createTable("CREATE TABLE %s (key int primary key, val double)");

        String fName = createFunction(KEYSPACE, "double",
                                      "CREATE OR REPLACE FUNCTION %s(val double) " +
                                      "RETURNS NULL ON NULL INPUT " +
                                      "RETURNS double " +
                                      "LANGUAGE javascript\n" +
                                      "AS '\"string\";';");

        execute("INSERT INTO %s (key, val) VALUES (?, ?)", 1, 1d);
        // throws IRE with ClassCastException
        assertInvalidMessage("Invalid value for CQL type double", "SELECT key, val, " + fName + "(val) FROM %s");
    }

    @Test
    public void testJavascriptThrow() throws Throwable
    {
        createTable("CREATE TABLE %s (key int primary key, val double)");

        String fName = createFunction(KEYSPACE, "double",
                       "CREATE OR REPLACE FUNCTION %s(val double) " +
                       "RETURNS NULL ON NULL INPUT " +
                       "RETURNS double " +
                       "LANGUAGE javascript\n" +
                       "AS 'throw \"fool\";';");

        execute("INSERT INTO %s (key, val) VALUES (?, ?)", 1, 1d);
        // throws IRE with ScriptException
        assertInvalidThrowMessage("fool", FunctionExecutionException.class,
                                  "SELECT key, val, " + fName + "(val) FROM %s");
    }

    @Test
    public void testDuplicateArgNames() throws Throwable
    {
        assertInvalidMessage("duplicate argument names for given function",
                             "CREATE OR REPLACE FUNCTION " + KEYSPACE + ".scrinv(val double, val text) " +
                             "RETURNS NULL ON NULL INPUT " +
                             "RETURNS text " +
                             "LANGUAGE javascript\n" +
                             "AS '\"foo bar\";';");
    }

    @Test
    public void testJavascriptCompileFailure() throws Throwable
    {
        assertInvalidMessage("Failed to compile function 'cql_test_keyspace.scrinv'",
                             "CREATE OR REPLACE FUNCTION " + KEYSPACE + ".scrinv(val double) " +
                             "RETURNS NULL ON NULL INPUT " +
                             "RETURNS double " +
                             "LANGUAGE javascript\n" +
                             "AS 'foo bar';");
    }

    @Test
    public void testScriptInvalidLanguage() throws Throwable
    {
        assertInvalidMessage("Invalid language 'artificial_intelligence' for function 'cql_test_keyspace.scrinv'",
                             "CREATE OR REPLACE FUNCTION " + KEYSPACE + ".scrinv(val double) " +
                             "RETURNS NULL ON NULL INPUT " +
                             "RETURNS double " +
                             "LANGUAGE artificial_intelligence\n" +
                             "AS 'question for 42?';");
    }

    @Test
    public void testScriptReturnTypeCasting() throws Throwable
    {
        createTable("CREATE TABLE %s (key int primary key, val double)");
        execute("INSERT INTO %s (key, val) VALUES (?, ?)", 1, 1d);

        Object[][] variations = {
                                new Object[]    {   "true",     "boolean",  true    },
                                new Object[]    {   "false",    "boolean",  false   },
                                new Object[]    {   "100",      "tinyint",  (byte)100 },
                                new Object[]    {   "100.",     "tinyint",  (byte)100 },
                                new Object[]    {   "100",      "smallint", (short)100 },
                                new Object[]    {   "100.",     "smallint", (short)100 },
                                new Object[]    {   "100",      "int",      100     },
                                new Object[]    {   "100.",     "int",      100     },
                                new Object[]    {   "100",      "double",   100d    },
                                new Object[]    {   "100.",     "double",   100d    },
                                new Object[]    {   "100",      "bigint",   100L    },
                                new Object[]    {   "100.",     "bigint",   100L    },
                                new Object[]    {   "100",      "varint",   BigInteger.valueOf(100L)    },
                                new Object[]    {   "100.",     "varint",   BigInteger.valueOf(100L)    },
                                new Object[]    {   "parseInt(\"100\");", "decimal",  BigDecimal.valueOf(100d)    },
                                new Object[]    {   "100.",     "decimal",  BigDecimal.valueOf(100d)    },
                                };

        for (Object[] variation : variations)
        {
            Object functionBody = variation[0];
            Object returnType = variation[1];
            Object expectedResult = variation[2];

            String fName = createFunction(KEYSPACE, "double",
                                          "CREATE OR REPLACE FUNCTION %s(val double) " +
                                          "RETURNS NULL ON NULL INPUT " +
                                          "RETURNS " +returnType + ' ' +
                                          "LANGUAGE javascript " +
                                          "AS '" + functionBody + ";';");
            assertRows(execute("SELECT key, val, " + fName + "(val) FROM %s"),
                       row(1, 1d, expectedResult));
        }
    }

    @Test
    public void testScriptParamReturnTypes() throws Throwable
    {
        UUID ruuid = UUID.randomUUID();
        UUID tuuid = UUIDGen.getTimeUUID();

        createTable("CREATE TABLE %s (key int primary key, " +
                    "tival tinyint, sival smallint, ival int, lval bigint, fval float, dval double, vval varint, ddval decimal, " +
                    "timval time, dtval date, tsval timestamp, uval uuid, tuval timeuuid)");
        execute("INSERT INTO %s (key, tival, sival, ival, lval, fval, dval, vval, ddval, timval, dtval, tsval, uval, tuval) VALUES " +
                "(?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)", 1,
                (byte)1, (short)1, 1, 1L, 1f, 1d, BigInteger.valueOf(1L), BigDecimal.valueOf(1d), 1L, Integer.MAX_VALUE, new Date(1), ruuid, tuuid);

        Object[][] variations = {
                                new Object[] {  "tinyint",  "tival",    (byte)1,                (byte)2  },
                                new Object[] {  "smallint", "sival",    (short)1,               (short)2  },
                                new Object[] {  "int",      "ival",     1,                      2  },
                                new Object[] {  "bigint",   "lval",     1L,                     2L  },
                                new Object[] {  "float",    "fval",     1f,                     2f  },
                                new Object[] {  "double",   "dval",     1d,                     2d  },
                                new Object[] {  "varint",   "vval",     BigInteger.valueOf(1L), BigInteger.valueOf(2L)  },
                                new Object[] {  "decimal",  "ddval",    BigDecimal.valueOf(1d), BigDecimal.valueOf(2d)  },
                                new Object[] {  "time",     "timval",   1L,                     2L  },
                                };

        for (Object[] variation : variations)
        {
            Object type = variation[0];
            Object col = variation[1];
            Object expected1 = variation[2];
            Object expected2 = variation[3];
            String fName = createFunction(KEYSPACE, type.toString(),
                           "CREATE OR REPLACE FUNCTION %s(val " + type + ") " +
                           "RETURNS NULL ON NULL INPUT " +
                           "RETURNS " + type + ' ' +
                           "LANGUAGE javascript " +
                           "AS 'val+1;';");
            assertRows(execute("SELECT key, " + col + ", " + fName + '(' + col + ") FROM %s"),
                       row(1, expected1, expected2));
        }

        variations = new Object[][] {
                     new Object[] {  "timestamp","tsval",    new Date(1),            new Date(1)  },
                     new Object[] {  "uuid",     "uval",     ruuid,                  ruuid  },
                     new Object[] {  "timeuuid", "tuval",    tuuid,                  tuuid  },
                     new Object[] {  "date",     "dtval",    Integer.MAX_VALUE,      Integer.MAX_VALUE },
        };

        for (Object[] variation : variations)
        {
            Object type = variation[0];
            Object col = variation[1];
            Object expected1 = variation[2];
            Object expected2 = variation[3];
            String fName = createFunction(KEYSPACE, type.toString(),
                                          "CREATE OR REPLACE FUNCTION %s(val " + type + ") " +
                                          "RETURNS NULL ON NULL INPUT " +
                                          "RETURNS " + type + ' ' +
                                          "LANGUAGE javascript " +
                                          "AS 'val;';");
            assertRows(execute("SELECT key, " + col + ", " + fName + '(' + col + ") FROM %s"),
                       row(1, expected1, expected2));
        }
    }

    static class TypesTestDef
    {
        final String udfType;
        final String tableType;
        final String columnName;
        final Object referenceValue;

        String fCheckArgAndReturn;

        String fCalledOnNull;
        String fReturnsNullOnNull;

        TypesTestDef(String udfType, String tableType, String columnName, Object referenceValue)
        {
            this.udfType = udfType;
            this.tableType = tableType;
            this.columnName = columnName;
            this.referenceValue = referenceValue;
        }
    }

    @Test
    public void testTypesWithAndWithoutNulls() throws Throwable
    {
        // test various combinations of types against UDFs with CALLED ON NULL or RETURNS NULL ON NULL

        String type = createType("CREATE TYPE %s (txt text, i int)");

        TypesTestDef[] typeDefs =
        {
        //                udf type,            table type,                 column, reference value
        new TypesTestDef("timestamp", "timestamp", "ts", new Date()),
        new TypesTestDef("date", "date", "dt", 12345),
        new TypesTestDef("time", "time", "tim", 12345L),
        new TypesTestDef("uuid", "uuid", "uu", UUID.randomUUID()),
        new TypesTestDef("timeuuid", "timeuuid", "tu", UUIDGen.getTimeUUID()),
        new TypesTestDef("tinyint", "tinyint", "ti", (byte) 42),
        new TypesTestDef("smallint", "smallint", "si", (short) 43),
        new TypesTestDef("int", "int", "i", 44),
        new TypesTestDef("bigint", "bigint", "b", 45L),
        new TypesTestDef("float", "float", "f", 46f),
        new TypesTestDef("double", "double", "d", 47d),
        new TypesTestDef("boolean", "boolean", "x", true),
        new TypesTestDef("ascii", "ascii", "a", "tqbfjutld"),
        new TypesTestDef("text", "text", "t", "k\u00f6lsche jung"),
        //new TypesTestDef(type,                 "frozen<" + type + '>',     "u",    null),
        new TypesTestDef("tuple<int, text>", "frozen<tuple<int, text>>", "tup", tuple(1, "foo"))
        };

        String createTableDDL = "CREATE TABLE %s (key int PRIMARY KEY";
        String insertDML = "INSERT INTO %s (key";
        List<Object> values = new ArrayList<>();
        for (TypesTestDef typeDef : typeDefs)
        {
            createTableDDL += ", " + typeDef.columnName + ' ' + typeDef.tableType;
            insertDML += ", " + typeDef.columnName;
            String typeName = typeDef.udfType;
            typeDef.fCheckArgAndReturn = createFunction(KEYSPACE,
                                                        typeName,
                                                        "CREATE OR REPLACE FUNCTION %s(val " + typeName + ") " +
                                                        "CALLED ON NULL INPUT " +
                                                        "RETURNS " + typeName + ' ' +
                                                        "LANGUAGE java\n" +
                                                        "AS 'return val;';");
            typeDef.fCalledOnNull = createFunction(KEYSPACE,
                                                   typeName,
                                                   "CREATE OR REPLACE FUNCTION %s(val " + typeName + ") " +
                                                   "CALLED ON NULL INPUT " +
                                                   "RETURNS text " +
                                                   "LANGUAGE java\n" +
                                                   "AS 'return \"called\";';");
            typeDef.fReturnsNullOnNull = createFunction(KEYSPACE,
                                                        typeName,
                                                        "CREATE OR REPLACE FUNCTION %s(val " + typeName + ") " +
                                                        "RETURNS NULL ON NULL INPUT " +
                                                        "RETURNS text " +
                                                        "LANGUAGE java\n" +
                                                        "AS 'return \"called\";';");
            values.add(typeDef.referenceValue);
        }

        createTableDDL += ')';
        createTable(createTableDDL);

        insertDML += ") VALUES (1";
        for (TypesTestDef ignored : typeDefs)
            insertDML += ", ?";
        insertDML += ')';

        execute(insertDML, values.toArray());

        // second row with null values
        for (int i = 0; i < values.size(); i++)
            values.set(i, null);
        execute(insertDML.replace('1', '2'), values.toArray());

        // check argument input + return
        for (TypesTestDef typeDef : typeDefs)
        {
            assertRows(execute("SELECT " + typeDef.fCheckArgAndReturn + '(' + typeDef.columnName + ") FROM %s WHERE key = 1"),
                       row(new Object[]{ typeDef.referenceValue }));
        }

        // check for CALLED ON NULL INPUT with non-null arguments
        for (TypesTestDef typeDef : typeDefs)
        {
            assertRows(execute("SELECT " + typeDef.fCalledOnNull + '(' + typeDef.columnName + ") FROM %s WHERE key = 1"),
                       row(new Object[]{ "called" }));
        }

        // check for CALLED ON NULL INPUT with null arguments
        for (TypesTestDef typeDef : typeDefs)
        {
            assertRows(execute("SELECT " + typeDef.fCalledOnNull + '(' + typeDef.columnName + ") FROM %s WHERE key = 2"),
                       row(new Object[]{ "called" }));
        }

        // check for RETURNS NULL ON NULL INPUT with non-null arguments
        for (TypesTestDef typeDef : typeDefs)
        {
            assertRows(execute("SELECT " + typeDef.fReturnsNullOnNull + '(' + typeDef.columnName + ") FROM %s WHERE key = 1"),
                       row(new Object[]{ "called" }));
        }

        // check for RETURNS NULL ON NULL INPUT with null arguments
        for (TypesTestDef typeDef : typeDefs)
        {
            assertRows(execute("SELECT " + typeDef.fReturnsNullOnNull + '(' + typeDef.columnName + ") FROM %s WHERE key = 2"),
                       row(new Object[]{ null }));
        }

    }

    @Test
    public void testReplaceAllowNulls() throws Throwable
    {
        String fNulls = createFunction(KEYSPACE,
                                       "int",
                                       "CREATE OR REPLACE FUNCTION %s(val int) " +
                                       "CALLED ON NULL INPUT " +
                                       "RETURNS text " +
                                       "LANGUAGE java\n" +
                                       "AS 'return \"foo bar\";';");
        String fNoNulls = createFunction(KEYSPACE,
                                         "int",
                                         "CREATE OR REPLACE FUNCTION %s(val int) " +
                                         "RETURNS NULL ON NULL INPUT " +
                                         "RETURNS text " +
                                         "LANGUAGE java\n" +
                                         "AS 'return \"foo bar\";';");

        assertInvalid("CREATE OR REPLACE FUNCTION " + fNulls + "(val int) " +
                      "RETURNS NULL ON NULL INPUT " +
                      "RETURNS text " +
                      "LANGUAGE java\n" +
                      "AS 'return \"foo bar\";';");
        assertInvalid("CREATE OR REPLACE FUNCTION " + fNoNulls + "(val int) " +
                      "CALLED ON NULL INPUT " +
                      "RETURNS text " +
                      "LANGUAGE java\n" +
                      "AS 'return \"foo bar\";';");

        execute("CREATE OR REPLACE FUNCTION " + fNulls + "(val int) " +
                "CALLED ON NULL INPUT " +
                "RETURNS text " +
                "LANGUAGE java\n" +
                "AS 'return \"foo bar\";';");
        execute("CREATE OR REPLACE FUNCTION " + fNoNulls + "(val int) " +
                "RETURNS NULL ON NULL INPUT " +
                "RETURNS text " +
                "LANGUAGE java\n" +
                "AS 'return \"foo bar\";';");
    }

    @Test
    public void testBrokenFunction() throws Throwable
    {
        createTable("CREATE TABLE %s (key int primary key, dval double)");
        execute("INSERT INTO %s (key, dval) VALUES (?, ?)", 1, 1d);

        String fName = createFunction(KEYSPACE_PER_TEST, "double",
                                      "CREATE OR REPLACE FUNCTION %s(val double) " +
                                      "RETURNS NULL ON NULL INPUT " +
                                      "RETURNS double " +
                                      "LANGUAGE JAVA\n" +
                                      "AS 'throw new RuntimeException();';");

        KeyspaceMetadata ksm = Schema.instance.getKSMetaData(KEYSPACE_PER_TEST);
        UDFunction f = (UDFunction) ksm.functions.get(parseFunctionName(fName)).iterator().next();

        UDFunction broken = UDFunction.createBrokenFunction(f.name(),
                                                            f.argNames(),
                                                            f.argTypes(),
                                                            f.returnType(),
                                                            true,
                                                            "java",
                                                            f.body(),
                                                            new InvalidRequestException("foo bar is broken"));
        Schema.instance.setKeyspaceMetadata(ksm.withSwapped(ksm.functions.without(f.name(), f.argTypes()).with(broken)));

        assertInvalidThrowMessage("foo bar is broken", InvalidRequestException.class,
                                  "SELECT key, " + fName + "(dval) FROM %s");
    }

    @Test
    public void testFunctionExecutionExceptionNet() throws Throwable
    {
        createTable("CREATE TABLE %s (key int primary key, dval double)");
        execute("INSERT INTO %s (key, dval) VALUES (?, ?)", 1, 1d);

        String fName = createFunction(KEYSPACE_PER_TEST, "double",
                                      "CREATE OR REPLACE FUNCTION %s(val double) " +
                                      "RETURNS NULL ON NULL INPUT " +
                                      "RETURNS double " +
                                      "LANGUAGE JAVA\n" +
                                      "AS 'throw new RuntimeException();'");

        for (int version = Server.VERSION_2; version <= maxProtocolVersion; version++)
        {
            try
            {
                assertRowsNet(version,
                              executeNet(version, "SELECT " + fName + "(dval) FROM %s WHERE key = 1"));
                Assert.fail();
            }
            catch (com.datastax.driver.core.exceptions.FunctionExecutionException fee)
            {
                // Java driver neither throws FunctionExecutionException nor does it set the exception code correctly
                Assert.assertTrue(version >= Server.VERSION_4);
            }
            catch (InvalidQueryException e)
            {
                Assert.assertTrue(version < Server.VERSION_4);
            }
        }
    }

    @Test
    public void testFunctionWithFrozenSetType() throws Throwable
    {
        createTable("CREATE TABLE %s (a int PRIMARY KEY, b frozen<set<int>>)");
        createIndex("CREATE INDEX ON %s (FULL(b))");

        execute("INSERT INTO %s (a, b) VALUES (?, ?)", 0, set());
        execute("INSERT INTO %s (a, b) VALUES (?, ?)", 1, set(1, 2, 3));
        execute("INSERT INTO %s (a, b) VALUES (?, ?)", 2, set(4, 5, 6));
        execute("INSERT INTO %s (a, b) VALUES (?, ?)", 3, set(7, 8, 9));

        assertInvalidMessage("The function arguments should not be frozen",
                             "CREATE OR REPLACE FUNCTION " + KEYSPACE + ".frozenSetArg(values frozen<set<int>>) " +
                             "CALLED ON NULL INPUT " +
                             "RETURNS int " +
                             "LANGUAGE java\n" +
                             "AS 'int sum = 0; for (Object value : values) {sum += value;} return sum;';");

        assertInvalidMessage("The function return type should not be frozen",
                             "CREATE OR REPLACE FUNCTION " + KEYSPACE + ".frozenReturnType(values set<int>) " +
                             "CALLED ON NULL INPUT " +
                             "RETURNS frozen<set<int>> " +
                             "LANGUAGE java\n" +
                             "AS 'return values;';");

        String functionName = createFunction(KEYSPACE,
                                             "set<int>",
                                             "CREATE FUNCTION %s (values set<int>) " +
                                             "CALLED ON NULL INPUT " +
                                             "RETURNS int " +
                                             "LANGUAGE java\n" +
                                             "AS 'int sum = 0; for (Object value : values) {sum += ((Integer) value);} return sum;';");

        assertRows(execute("SELECT a, " + functionName + "(b) FROM %s WHERE a = 0"), row(0, 0));
        assertRows(execute("SELECT a, " + functionName + "(b) FROM %s WHERE a = 1"), row(1, 6));
        assertRows(execute("SELECT a, " + functionName + "(b) FROM %s WHERE a = 2"), row(2, 15));
        assertRows(execute("SELECT a, " + functionName + "(b) FROM %s WHERE a = 3"), row(3, 24));

        functionName = createFunction(KEYSPACE,
                                      "set<int>",
                                             "CREATE FUNCTION %s (values set<int>) " +
                                             "CALLED ON NULL INPUT " +
                                             "RETURNS set<int> " +
                                             "LANGUAGE java\n" +
                                             "AS 'return values;';");

        assertRows(execute("SELECT a FROM %s WHERE b = " + functionName + "(?)", set(1, 2, 3)),
                   row(1));

        assertInvalidMessage("The function arguments should not be frozen",
                             "DROP FUNCTION " + functionName + "(frozen<set<int>>);");
    }

    @Test
    public void testFunctionWithFrozenListType() throws Throwable
    {
        createTable("CREATE TABLE %s (a int PRIMARY KEY, b frozen<list<int>>)");
        createIndex("CREATE INDEX ON %s (FULL(b))");

        execute("INSERT INTO %s (a, b) VALUES (?, ?)", 0, list());
        execute("INSERT INTO %s (a, b) VALUES (?, ?)", 1, list(1, 2, 3));
        execute("INSERT INTO %s (a, b) VALUES (?, ?)", 2, list(4, 5, 6));
        execute("INSERT INTO %s (a, b) VALUES (?, ?)", 3, list(7, 8, 9));

        assertInvalidMessage("The function arguments should not be frozen",
                             "CREATE OR REPLACE FUNCTION " + KEYSPACE + ".withFrozenArg(values frozen<list<int>>) " +
                             "CALLED ON NULL INPUT " +
                             "RETURNS int " +
                             "LANGUAGE java\n" +
                             "AS 'int sum = 0; for (Object value : values) {sum += value;} return sum;';");

        assertInvalidMessage("The function return type should not be frozen",
                             "CREATE OR REPLACE FUNCTION " + KEYSPACE + ".frozenReturnType(values list<int>) " +
                             "CALLED ON NULL INPUT " +
                             "RETURNS frozen<list<int>> " +
                             "LANGUAGE java\n" +
                             "AS 'return values;';");

        String functionName = createFunction(KEYSPACE,
                                             "list<int>",
                                             "CREATE FUNCTION %s (values list<int>) " +
                                             "CALLED ON NULL INPUT " +
                                             "RETURNS int " +
                                             "LANGUAGE java\n" +
                                             "AS 'int sum = 0; for (Object value : values) {sum += ((Integer) value);} return sum;';");

        assertRows(execute("SELECT a, " + functionName + "(b) FROM %s WHERE a = 0"), row(0, 0));
        assertRows(execute("SELECT a, " + functionName + "(b) FROM %s WHERE a = 1"), row(1, 6));
        assertRows(execute("SELECT a, " + functionName + "(b) FROM %s WHERE a = 2"), row(2, 15));
        assertRows(execute("SELECT a, " + functionName + "(b) FROM %s WHERE a = 3"), row(3, 24));

        functionName = createFunction(KEYSPACE,
                                      "list<int>",
                                      "CREATE FUNCTION %s (values list<int>) " +
                                      "CALLED ON NULL INPUT " +
                                      "RETURNS list<int> " +
                                      "LANGUAGE java\n" +
                                      "AS 'return values;';");

        assertRows(execute("SELECT a FROM %s WHERE b = " + functionName + "(?)", set(1, 2, 3)),
                   row(1));

        assertInvalidMessage("The function arguments should not be frozen",
                             "DROP FUNCTION " + functionName + "(frozen<list<int>>);");
    }

    @Test
    public void testFunctionWithFrozenMapType() throws Throwable
    {
        createTable("CREATE TABLE %s (a int PRIMARY KEY, b frozen<map<int, int>>)");
        createIndex("CREATE INDEX ON %s (FULL(b))");

        execute("INSERT INTO %s (a, b) VALUES (?, ?)", 0, map());
        execute("INSERT INTO %s (a, b) VALUES (?, ?)", 1, map(1, 1, 2, 2, 3, 3));
        execute("INSERT INTO %s (a, b) VALUES (?, ?)", 2, map(4, 4, 5, 5, 6, 6));
        execute("INSERT INTO %s (a, b) VALUES (?, ?)", 3, map(7, 7, 8, 8, 9, 9));

        assertInvalidMessage("The function arguments should not be frozen",
                             "CREATE OR REPLACE FUNCTION " + KEYSPACE + ".withFrozenArg(values frozen<map<int, int>>) " +
                             "CALLED ON NULL INPUT " +
                             "RETURNS int " +
                             "LANGUAGE java\n" +
                             "AS 'int sum = 0; for (Object value : values.values()) {sum += value;} return sum;';");

        assertInvalidMessage("The function return type should not be frozen",
                             "CREATE OR REPLACE FUNCTION " + KEYSPACE + ".frozenReturnType(values map<int, int>) " +
                             "CALLED ON NULL INPUT " +
                             "RETURNS frozen<map<int, int>> " +
                             "LANGUAGE java\n" +
                             "AS 'return values;';");

        String functionName = createFunction(KEYSPACE,
                                             "map<int, int>",
                                             "CREATE FUNCTION %s (values map<int, int>) " +
                                             "CALLED ON NULL INPUT " +
                                             "RETURNS int " +
                                             "LANGUAGE java\n" +
                                             "AS 'int sum = 0; for (Object value : values.values()) {sum += ((Integer) value);} return sum;';");

        assertRows(execute("SELECT a, " + functionName + "(b) FROM %s WHERE a = 0"), row(0, 0));
        assertRows(execute("SELECT a, " + functionName + "(b) FROM %s WHERE a = 1"), row(1, 6));
        assertRows(execute("SELECT a, " + functionName + "(b) FROM %s WHERE a = 2"), row(2, 15));
        assertRows(execute("SELECT a, " + functionName + "(b) FROM %s WHERE a = 3"), row(3, 24));

        functionName = createFunction(KEYSPACE,
                                      "map<int, int>",
                                      "CREATE FUNCTION %s (values map<int, int>) " +
                                      "CALLED ON NULL INPUT " +
                                      "RETURNS map<int, int> " +
                                      "LANGUAGE java\n" +
                                      "AS 'return values;';");

        assertRows(execute("SELECT a FROM %s WHERE b = " + functionName + "(?)", map(1, 1, 2, 2, 3, 3)),
                   row(1));

        assertInvalidMessage("The function arguments should not be frozen",
                             "DROP FUNCTION " + functionName + "(frozen<map<int, int>>);");
    }

    @Test
    public void testFunctionWithFrozenTupleType() throws Throwable
    {
        createTable("CREATE TABLE %s (a int PRIMARY KEY, b frozen<tuple<int, int>>)");
        createIndex("CREATE INDEX ON %s (b)");

        execute("INSERT INTO %s (a, b) VALUES (?, ?)", 0, tuple());
        execute("INSERT INTO %s (a, b) VALUES (?, ?)", 1, tuple(1, 2));
        execute("INSERT INTO %s (a, b) VALUES (?, ?)", 2, tuple(4, 5));
        execute("INSERT INTO %s (a, b) VALUES (?, ?)", 3, tuple(7, 8));

        assertInvalidMessage("The function arguments should not be frozen",
                             "CREATE OR REPLACE FUNCTION " + KEYSPACE + ".withFrozenArg(values frozen<tuple<int, int>>) " +
                             "CALLED ON NULL INPUT " +
                             "RETURNS text " +
                             "LANGUAGE java\n" +
                             "AS 'return values.toString();';");

        assertInvalidMessage("The function return type should not be frozen",
                             "CREATE OR REPLACE FUNCTION " + KEYSPACE + ".frozenReturnType(values tuple<int, int>) " +
                             "CALLED ON NULL INPUT " +
                             "RETURNS frozen<tuple<int, int>> " +
                             "LANGUAGE java\n" +
                             "AS 'return values;';");

        String functionName = createFunction(KEYSPACE,
                                             "tuple<int, int>",
                                             "CREATE FUNCTION %s (values tuple<int, int>) " +
                                             "CALLED ON NULL INPUT " +
                                             "RETURNS text " +
                                             "LANGUAGE java\n" +
                                             "AS 'return values.toString();';");

        assertRows(execute("SELECT a, " + functionName + "(b) FROM %s WHERE a = 0"), row(0, "(null, null)"));
        assertRows(execute("SELECT a, " + functionName + "(b) FROM %s WHERE a = 1"), row(1, "(1, 2)"));
        assertRows(execute("SELECT a, " + functionName + "(b) FROM %s WHERE a = 2"), row(2, "(4, 5)"));
        assertRows(execute("SELECT a, " + functionName + "(b) FROM %s WHERE a = 3"), row(3, "(7, 8)"));

        functionName = createFunction(KEYSPACE,
                                      "tuple<int, int>",
                                      "CREATE FUNCTION %s (values tuple<int, int>) " +
                                      "CALLED ON NULL INPUT " +
                                      "RETURNS tuple<int, int> " +
                                      "LANGUAGE java\n" +
                                      "AS 'return values;';");

        assertRows(execute("SELECT a FROM %s WHERE b = " + functionName + "(?)", tuple(1, 2)),
                   row(1));

        assertInvalidMessage("The function arguments should not be frozen",
                             "DROP FUNCTION " + functionName + "(frozen<tuple<int, int>>);");
    }

    @Test
    public void testFunctionWithFrozenUDType() throws Throwable
    {
        String myType = createType("CREATE TYPE %s (f int)");
        createTable("CREATE TABLE %s (a int PRIMARY KEY, b frozen<" + myType + ">)");
        createIndex("CREATE INDEX ON %s (b)");

        execute("INSERT INTO %s (a, b) VALUES (?, {f : ?})", 0, 0);
        execute("INSERT INTO %s (a, b) VALUES (?, {f : ?})", 1, 1);
        execute("INSERT INTO %s (a, b) VALUES (?, {f : ?})", 2, 4);
        execute("INSERT INTO %s (a, b) VALUES (?, {f : ?})", 3, 7);

        assertInvalidMessage("The function arguments should not be frozen",
                             "CREATE OR REPLACE FUNCTION " + KEYSPACE + ".withFrozenArg(values frozen<" + myType + ">) " +
                             "CALLED ON NULL INPUT " +
                             "RETURNS text " +
                             "LANGUAGE java\n" +
                             "AS 'return values.toString();';");

        assertInvalidMessage("The function return type should not be frozen",
                             "CREATE OR REPLACE FUNCTION " + KEYSPACE + ".frozenReturnType(values " + myType + ") " +
                             "CALLED ON NULL INPUT " +
                             "RETURNS frozen<" + myType + "> " +
                             "LANGUAGE java\n" +
                             "AS 'return values;';");

        String functionName = createFunction(KEYSPACE,
                                             myType,
                                             "CREATE FUNCTION %s (values " + myType + ") " +
                                             "CALLED ON NULL INPUT " +
                                             "RETURNS text " +
                                             "LANGUAGE java\n" +
                                             "AS 'return values.toString();';");

        assertRows(execute("SELECT a, " + functionName + "(b) FROM %s WHERE a = 0"), row(0, "{f:0}"));
        assertRows(execute("SELECT a, " + functionName + "(b) FROM %s WHERE a = 1"), row(1, "{f:1}"));
        assertRows(execute("SELECT a, " + functionName + "(b) FROM %s WHERE a = 2"), row(2, "{f:4}"));
        assertRows(execute("SELECT a, " + functionName + "(b) FROM %s WHERE a = 3"), row(3, "{f:7}"));

        functionName = createFunction(KEYSPACE,
                                      myType,
                                      "CREATE FUNCTION %s (values " + myType + ") " +
                                      "CALLED ON NULL INPUT " +
                                      "RETURNS " + myType + " " +
                                      "LANGUAGE java\n" +
                                      "AS 'return values;';");

        assertRows(execute("SELECT a FROM %s WHERE b = " + functionName + "({f: ?})", 1),
                   row(1));

        assertInvalidMessage("The function arguments should not be frozen",
                             "DROP FUNCTION " + functionName + "(frozen<" + myType + ">);");
    }

    @Test
    public void testEmptyString() throws Throwable
    {
        createTable("CREATE TABLE %s (key int primary key, sval text, aval ascii, bval blob, empty_int int)");
        execute("INSERT INTO %s (key, sval, aval, bval, empty_int) VALUES (?, ?, ?, ?, blobAsInt(0x))", 1, "", "", ByteBuffer.allocate(0));

        String fNameSRC = createFunction(KEYSPACE_PER_TEST, "text",
                                         "CREATE OR REPLACE FUNCTION %s(val text) " +
                                         "CALLED ON NULL INPUT " +
                                         "RETURNS text " +
                                         "LANGUAGE JAVA\n" +
                                         "AS 'return val;'");

        String fNameSCC = createFunction(KEYSPACE_PER_TEST, "text",
                                         "CREATE OR REPLACE FUNCTION %s(val text) " +
                                         "CALLED ON NULL INPUT " +
                                         "RETURNS text " +
                                         "LANGUAGE JAVA\n" +
                                         "AS 'return \"\";'");

        String fNameSRN = createFunction(KEYSPACE_PER_TEST, "text",
                                         "CREATE OR REPLACE FUNCTION %s(val text) " +
                                         "RETURNS NULL ON NULL INPUT " +
                                         "RETURNS text " +
                                         "LANGUAGE JAVA\n" +
                                         "AS 'return val;'");

        String fNameSCN = createFunction(KEYSPACE_PER_TEST, "text",
                                         "CREATE OR REPLACE FUNCTION %s(val text) " +
                                         "RETURNS NULL ON NULL INPUT " +
                                         "RETURNS text " +
                                         "LANGUAGE JAVA\n" +
                                         "AS 'return \"\";'");

        String fNameBRC = createFunction(KEYSPACE_PER_TEST, "blob",
                                         "CREATE OR REPLACE FUNCTION %s(val blob) " +
                                         "CALLED ON NULL INPUT " +
                                         "RETURNS blob " +
                                         "LANGUAGE JAVA\n" +
                                         "AS 'return val;'");

        String fNameBCC = createFunction(KEYSPACE_PER_TEST, "blob",
                                         "CREATE OR REPLACE FUNCTION %s(val blob) " +
                                         "CALLED ON NULL INPUT " +
                                         "RETURNS blob " +
                                         "LANGUAGE JAVA\n" +
                                         "AS 'return ByteBuffer.allocate(0);'");

        String fNameBRN = createFunction(KEYSPACE_PER_TEST, "blob",
                                         "CREATE OR REPLACE FUNCTION %s(val blob) " +
                                         "RETURNS NULL ON NULL INPUT " +
                                         "RETURNS blob " +
                                         "LANGUAGE JAVA\n" +
                                         "AS 'return val;'");

        String fNameBCN = createFunction(KEYSPACE_PER_TEST, "blob",
                                         "CREATE OR REPLACE FUNCTION %s(val blob) " +
                                         "RETURNS NULL ON NULL INPUT " +
                                         "RETURNS blob " +
                                         "LANGUAGE JAVA\n" +
                                         "AS 'return ByteBuffer.allocate(0);'");

        String fNameIRC = createFunction(KEYSPACE_PER_TEST, "int",
                                         "CREATE OR REPLACE FUNCTION %s(val int) " +
                                         "CALLED ON NULL INPUT " +
                                         "RETURNS int " +
                                         "LANGUAGE JAVA\n" +
                                         "AS 'return val;'");

        String fNameICC = createFunction(KEYSPACE_PER_TEST, "int",
                                         "CREATE OR REPLACE FUNCTION %s(val int) " +
                                         "CALLED ON NULL INPUT " +
                                         "RETURNS int " +
                                         "LANGUAGE JAVA\n" +
                                         "AS 'return 0;'");

        String fNameIRN = createFunction(KEYSPACE_PER_TEST, "int",
                                         "CREATE OR REPLACE FUNCTION %s(val int) " +
                                         "RETURNS NULL ON NULL INPUT " +
                                         "RETURNS int " +
                                         "LANGUAGE JAVA\n" +
                                         "AS 'return val;'");

        String fNameICN = createFunction(KEYSPACE_PER_TEST, "blob",
                                         "CREATE OR REPLACE FUNCTION %s(val int) " +
                                         "RETURNS NULL ON NULL INPUT " +
                                         "RETURNS int " +
                                         "LANGUAGE JAVA\n" +
                                         "AS 'return 0;'");

        assertRows(execute("SELECT " + fNameSRC + "(sval) FROM %s"), row(""));
        assertRows(execute("SELECT " + fNameSRN + "(sval) FROM %s"), row(""));
        assertRows(execute("SELECT " + fNameSCC + "(sval) FROM %s"), row(""));
        assertRows(execute("SELECT " + fNameSCN + "(sval) FROM %s"), row(""));
        assertRows(execute("SELECT " + fNameSRC + "(aval) FROM %s"), row(""));
        assertRows(execute("SELECT " + fNameSRN + "(aval) FROM %s"), row(""));
        assertRows(execute("SELECT " + fNameSCC + "(aval) FROM %s"), row(""));
        assertRows(execute("SELECT " + fNameSCN + "(aval) FROM %s"), row(""));
        assertRows(execute("SELECT " + fNameBRC + "(bval) FROM %s"), row(ByteBufferUtil.EMPTY_BYTE_BUFFER));
        assertRows(execute("SELECT " + fNameBRN + "(bval) FROM %s"), row(ByteBufferUtil.EMPTY_BYTE_BUFFER));
        assertRows(execute("SELECT " + fNameBCC + "(bval) FROM %s"), row(ByteBufferUtil.EMPTY_BYTE_BUFFER));
        assertRows(execute("SELECT " + fNameBCN + "(bval) FROM %s"), row(ByteBufferUtil.EMPTY_BYTE_BUFFER));
        assertRows(execute("SELECT " + fNameIRC + "(empty_int) FROM %s"), row(new Object[]{null}));
        assertRows(execute("SELECT " + fNameIRN + "(empty_int) FROM %s"), row(new Object[]{null}));
        assertRows(execute("SELECT " + fNameICC + "(empty_int) FROM %s"), row(0));
        assertRows(execute("SELECT " + fNameICN + "(empty_int) FROM %s"), row(new Object[]{null}));
    }
}
