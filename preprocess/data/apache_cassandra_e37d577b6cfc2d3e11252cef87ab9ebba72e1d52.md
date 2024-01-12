Refactoring Types: ['Extract Method']
config/Config.java
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
    public Integer concurrent_batchlog_writes = 32;
    public Integer concurrent_materialized_view_writes = 32;

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

    public String[] data_file_directories = new String[0];

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
    public TransparentDataEncryptionOptions transparent_data_encryption_options = new TransparentDataEncryptionOptions();

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

    public DiskOptimizationStrategy disk_optimization_strategy = DiskOptimizationStrategy.ssd;

    public double disk_optimization_estimate_percentile = 0.95;

    public double disk_optimization_page_cross_chance = 0.1;

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
    /**
     * Optionally disable asynchronous UDF execution.
     * Disabling asynchronous UDF execution also implicitly disables the security-manager!
     * By default, async UDF execution is enabled to be able to detect UDFs that run too long / forever and be
     * able to fail fast - i.e. stop the Cassandra daemon, which is currently the only appropriate approach to
     * "tell" a user that there's something really wrong with the UDF.
     * When you disable async UDF execution, users MUST pay attention to read-timeouts since these may indicate
     * UDFs that run too long or forever - and this can destabilize the cluster.
     */
    public boolean enable_user_defined_functions_threads = true;
    /**
     * Time in milliseconds after a warning will be emitted to the log and to the client that a UDF runs too long.
     * (Only valid, if enable_user_defined_functions_threads==true)
     */
    public long user_defined_function_warn_timeout = 500;
    /**
     * Time in milliseconds after a fatal UDF run-time situation is detected and action according to
     * user_function_timeout_policy will take place.
     * (Only valid, if enable_user_defined_functions_threads==true)
     */
    public long user_defined_function_fail_timeout = 1500;
    /**
     * Defines what to do when a UDF ran longer than user_defined_function_fail_timeout.
     * Possible options are:
     * - 'die' - i.e. it is able to emit a warning to the client before the Cassandra Daemon will shut down.
     * - 'die_immediate' - shut down C* daemon immediately (effectively prevent the chance that the client will receive a warning).
     * - 'ignore' - just log - the most dangerous option.
     * (Only valid, if enable_user_defined_functions_threads==true)
     */
    public UserFunctionTimeoutPolicy user_function_timeout_policy = UserFunctionTimeoutPolicy.die;

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

    public enum CommitLogSync
    {
        periodic,
        batch
    }
    public enum InternodeCompression
    {
        all, none, dc
    }

    public enum DiskAccessMode
    {
        auto,
        mmap,
        mmap_index_only,
        standard,
    }

    public enum MemtableAllocationType
    {
        unslabbed_heap_buffers,
        heap_buffers,
        offheap_buffers,
        offheap_objects
    }

    public enum DiskFailurePolicy
    {
        best_effort,
        stop,
        ignore,
        stop_paranoid,
        die
    }

    public enum CommitFailurePolicy
    {
        stop,
        stop_commit,
        ignore,
        die,
    }

    public enum UserFunctionTimeoutPolicy
    {
        ignore,
        die,
        die_immediate
    }

    public enum RequestSchedulerId
    {
        keyspace
    }

    public enum DiskOptimizationStrategy
    {
        ssd,
        spinning
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
import org.apache.cassandra.security.EncryptionContext;
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
    private static EncryptionContext encryptionContext;

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
        if (conf.data_file_directories == null || conf.data_file_directories.length == 0)
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

        if (conf.user_defined_function_fail_timeout < 0)
            throw new ConfigurationException("user_defined_function_fail_timeout must not be negative", false);
        if (conf.user_defined_function_warn_timeout < 0)
            throw new ConfigurationException("user_defined_function_warn_timeout must not be negative", false);

        if (conf.user_defined_function_fail_timeout < conf.user_defined_function_warn_timeout)
            throw new ConfigurationException("user_defined_function_warn_timeout must less than user_defined_function_fail_timeout", false);

        // always attempt to load the cipher factory, as we could be in the situation where the user has disabled encryption,
        // but has existing commitlogs and sstables on disk that are still encrypted (and still need to be read)
        encryptionContext = new EncryptionContext(config.transparent_data_encryption_options);
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

    /* For tests ONLY, don't use otherwise or all hell will break loose. Tests should restore value at the end. */
    public static IPartitioner setPartitionerUnsafe(IPartitioner newPartitioner)
    {
        IPartitioner old = partitioner;
        partitioner = newPartitioner;
        return old;
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
            case BATCHLOG_MUTATION:
            case MATERIALIZED_VIEW_MUTATION:
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

    public static int getConcurrentBatchlogWriters()
    {
        return conf.concurrent_batchlog_writes;
    }
    public static int getConcurrentMaterializedViewWriters()
    {
        return conf.concurrent_materialized_view_writes;
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

    public static Config.DiskOptimizationStrategy getDiskOptimizationStrategy()
    {
        return conf.disk_optimization_strategy;
    }

    @VisibleForTesting
    public static void setDiskOptimizationStrategy(Config.DiskOptimizationStrategy strategy)
    {
        conf.disk_optimization_strategy = strategy;
    }

    public static double getDiskOptimizationEstimatePercentile()
    {
        return conf.disk_optimization_estimate_percentile;
    }

    public static double getDiskOptimizationPageCrossChance()
    {
        return conf.disk_optimization_page_cross_chance;
    }

    @VisibleForTesting
    public static void setDiskOptimizationPageCrossChance(double chance)
    {
        conf.disk_optimization_page_cross_chance = chance;
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

    public static int getWindowsTimerInterval()
    {
        return conf.windows_timer_interval;
    }

    public static boolean enableUserDefinedFunctions()
    {
        return conf.enable_user_defined_functions;
    }

    public static boolean enableUserDefinedFunctionsThreads()
    {
        return conf.enable_user_defined_functions_threads;
    }

    public static long getUserDefinedFunctionWarnTimeout()
    {
        return conf.user_defined_function_warn_timeout;
    }

    public static void setUserDefinedFunctionWarnTimeout(long userDefinedFunctionWarnTimeout)
    {
        conf.user_defined_function_warn_timeout = userDefinedFunctionWarnTimeout;
    }

    public static long getUserDefinedFunctionFailTimeout()
    {
        return conf.user_defined_function_fail_timeout;
    }

    public static void setUserDefinedFunctionFailTimeout(long userDefinedFunctionFailTimeout)
    {
        conf.user_defined_function_fail_timeout = userDefinedFunctionFailTimeout;
    }

    public static Config.UserFunctionTimeoutPolicy getUserFunctionTimeoutPolicy()
    {
        return conf.user_function_timeout_policy;
    }

    public static void setUserFunctionTimeoutPolicy(Config.UserFunctionTimeoutPolicy userFunctionTimeoutPolicy)
    {
        conf.user_function_timeout_policy = userFunctionTimeoutPolicy;
    }

    public static EncryptionContext getEncryptionContext()
    {
        return encryptionContext;
    }

    @VisibleForTesting
    public static void setEncryptionContext(EncryptionContext ec)
    {
        encryptionContext = ec;
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

import java.lang.management.ManagementFactory;
import java.lang.management.ThreadMXBean;
import java.net.InetAddress;
import java.net.URL;
import java.nio.ByteBuffer;
import java.util.ArrayList;
import java.util.Collections;
import java.util.Enumeration;
import java.util.HashSet;
import java.util.List;
import java.util.concurrent.ExecutionException;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;
import java.util.concurrent.Future;
import java.util.concurrent.TimeUnit;
import java.util.concurrent.TimeoutException;

import com.google.common.base.Objects;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import com.datastax.driver.core.DataType;
import com.datastax.driver.core.ProtocolVersion;
import com.datastax.driver.core.UserType;
import org.apache.cassandra.config.Config;
import org.apache.cassandra.config.DatabaseDescriptor;
import org.apache.cassandra.config.Schema;
import org.apache.cassandra.cql3.ColumnIdentifier;
import org.apache.cassandra.db.marshal.AbstractType;
import org.apache.cassandra.exceptions.FunctionExecutionException;
import org.apache.cassandra.exceptions.InvalidRequestException;
import org.apache.cassandra.schema.Functions;
import org.apache.cassandra.schema.KeyspaceMetadata;
import org.apache.cassandra.service.ClientWarn;
import org.apache.cassandra.service.MigrationManager;
import org.apache.cassandra.tracing.Tracing;
import org.apache.cassandra.utils.ByteBufferUtil;
import org.apache.cassandra.utils.JVMStabilityInspector;

/**
 * Base class for User Defined Functions.
 */
public abstract class UDFunction extends AbstractFunction implements ScalarFunction
{
    protected static final Logger logger = LoggerFactory.getLogger(UDFunction.class);

    static final ThreadMXBean threadMXBean = ManagementFactory.getThreadMXBean();

    protected final List<ColumnIdentifier> argNames;

    protected final String language;
    protected final String body;

    protected final DataType[] argDataTypes;
    protected final DataType returnDataType;
    protected final boolean calledOnNullInput;

    //
    // Access to classes is controlled via a whitelist and a blacklist.
    //
    // When a class is requested (both during compilation and runtime),
    // the whitelistedPatterns array is searched first, whether the
    // requested name matches one of the patterns. If not, nothing is
    // returned from the class-loader - meaning ClassNotFoundException
    // during runtime and "type could not resolved" during compilation.
    //
    // If a whitelisted pattern has been found, the blacklistedPatterns
    // array is searched for a match. If a match is found, class-loader
    // rejects access. Otherwise the class/resource can be loaded.
    //
    private static final String[] whitelistedPatterns =
    {
    "com/datastax/driver/core/",
    "com/google/common/reflect/TypeToken",
    "java/io/IOException.class",
    "java/io/Serializable.class",
    "java/lang/",
    "java/math/",
    "java/nio/Buffer.class",
    "java/nio/ByteBuffer.class",
    "java/text/",
    "java/time/",
    "java/util/",
    "org/apache/cassandra/cql3/functions/JavaUDF.class",
    "org/apache/cassandra/exceptions/",
    };
    // Only need to blacklist a pattern, if it would otherwise be allowed via whitelistedPatterns
    private static final String[] blacklistedPatterns =
    {
    "com/datastax/driver/core/Cluster.class",
    "com/datastax/driver/core/Metrics.class",
    "com/datastax/driver/core/NettyOptions.class",
    "com/datastax/driver/core/Session.class",
    "com/datastax/driver/core/Statement.class",
    "com/datastax/driver/core/TimestampGenerator.class", // indirectly covers ServerSideTimestampGenerator + ThreadLocalMonotonicTimestampGenerator
    "java/lang/Compiler.class",
    "java/lang/InheritableThreadLocal.class",
    "java/lang/Package.class",
    "java/lang/Process.class",
    "java/lang/ProcessBuilder.class",
    "java/lang/ProcessEnvironment.class",
    "java/lang/ProcessImpl.class",
    "java/lang/Runnable.class",
    "java/lang/Runtime.class",
    "java/lang/Shutdown.class",
    "java/lang/Thread.class",
    "java/lang/ThreadGroup.class",
    "java/lang/ThreadLocal.class",
    "java/lang/instrument/",
    "java/lang/invoke/",
    "java/lang/management/",
    "java/lang/ref/",
    "java/lang/reflect/",
    "java/util/ServiceLoader.class",
    "java/util/Timer.class",
    "java/util/concurrent/",
    "java/util/function/",
    "java/util/jar/",
    "java/util/logging/",
    "java/util/prefs/",
    "java/util/spi/",
    "java/util/stream/",
    "java/util/zip/",
    };

    static boolean secureResource(String resource)
    {
        while (resource.startsWith("/"))
            resource = resource.substring(1);

        for (String white : whitelistedPatterns)
            if (resource.startsWith(white))
            {

                // resource is in whitelistedPatterns, let's see if it is not explicityl blacklisted
                for (String black : blacklistedPatterns)
                    if (resource.startsWith(black))
                    {
                        logger.trace("access denied: resource {}", resource);
                        return false;
                    }

                return true;
            }

        logger.trace("access denied: resource {}", resource);
        return false;
    }

    // setup the UDF class loader with no parent class loader so that we have full control about what class/resource UDF uses
    static final ClassLoader udfClassLoader = new UDFClassLoader();

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
    {
        if (!DatabaseDescriptor.enableUserDefinedFunctions())
            throw new InvalidRequestException("User-defined functions are disabled in cassandra.yaml - set enable_user_defined_functions=true to enable if you are aware of the security risks");

        switch (language)
        {
            case "java":
                return new JavaBasedUDFunction(name, argNames, argTypes, returnType, calledOnNullInput, body);
            default:
                return new ScriptBasedUDFunction(name, argNames, argTypes, returnType, calledOnNullInput, language, body);
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
                                                  InvalidRequestException reason)
    {
        return new UDFunction(name, argNames, argTypes, returnType, calledOnNullInput, language, body)
        {
            protected ExecutorService executor()
            {
                return Executors.newSingleThreadExecutor();
            }

            public ByteBuffer executeUserDefined(int protocolVersion, List<ByteBuffer> parameters)
            {
                throw new InvalidRequestException(String.format("Function '%s' exists but hasn't been loaded successfully "
                                                                + "for the following reason: %s. Please see the server log for details",
                                                                this,
                                                                reason.getMessage()));
            }
        };
    }

    public final ByteBuffer execute(int protocolVersion, List<ByteBuffer> parameters)
    {
        if (!DatabaseDescriptor.enableUserDefinedFunctions())
            throw new InvalidRequestException("User-defined-functions are disabled in cassandra.yaml - set enable_user_defined_functions=true to enable if you are aware of the security risks");

        if (!isCallableWrtNullable(parameters))
            return null;

        long tStart = System.nanoTime();
        parameters = makeEmptyParametersNull(parameters);

        try
        {
            // Using async UDF execution is expensive (adds about 100us overhead per invocation on a Core-i7 MBPr).
            ByteBuffer result = DatabaseDescriptor.enableUserDefinedFunctionsThreads()
                                ? executeAsync(protocolVersion, parameters)
                                : executeUserDefined(protocolVersion, parameters);
            Tracing.trace("Executed UDF {} in {}\u03bcs", name(), (System.nanoTime() - tStart) / 1000);
            return result;
        }
        catch (InvalidRequestException e)
        {
            throw e;
        }
        catch (Throwable t)
        {
            logger.debug("Invocation of user-defined function '{}' failed", this, t);
            if (t instanceof VirtualMachineError)
                throw (VirtualMachineError) t;
            throw FunctionExecutionException.create(this, t);
        }
    }

    private static final class ThreadIdAndCpuTime
    {
        long threadId;
        long cpuTime;

        ThreadIdAndCpuTime()
        {
            // Looks weird?
            // This call "just" links this class to java.lang.management - otherwise UDFs (script UDFs) might fail due to
            //      java.security.AccessControlException: access denied: ("java.lang.RuntimePermission" "accessClassInPackage.java.lang.management")
            // because class loading would be deferred until setup() is executed - but setup() is called with
            // limited privileges.
            threadMXBean.getCurrentThreadCpuTime();
            //
            // Get the TypeCodec stuff in Java Driver initialized.
            DataType.inet().format(InetAddress.getLoopbackAddress());
            DataType.list(DataType.ascii()).format(Collections.emptyList());
        }

        void setup()
        {
            this.threadId = Thread.currentThread().getId();
            this.cpuTime = threadMXBean.getCurrentThreadCpuTime();
        }
    }

    private ByteBuffer executeAsync(int protocolVersion, List<ByteBuffer> parameters)
    {
        ThreadIdAndCpuTime threadIdAndCpuTime = new ThreadIdAndCpuTime();

        Future<ByteBuffer> future = executor().submit(() -> {
            threadIdAndCpuTime.setup();
            return executeUserDefined(protocolVersion, parameters);
        });

        try
        {
            if (DatabaseDescriptor.getUserDefinedFunctionWarnTimeout() > 0)
                try
                {
                    return future.get(DatabaseDescriptor.getUserDefinedFunctionWarnTimeout(), TimeUnit.MILLISECONDS);
                }
                catch (TimeoutException e)
                {

                    // log and emit a warning that UDF execution took long
                    String warn = String.format("User defined function %s ran longer than %dms", this, DatabaseDescriptor.getUserDefinedFunctionWarnTimeout());
                    logger.warn(warn);
                    ClientWarn.warn(warn);
                }

            // retry with difference of warn-timeout to fail-timeout
            return future.get(DatabaseDescriptor.getUserDefinedFunctionFailTimeout() - DatabaseDescriptor.getUserDefinedFunctionWarnTimeout(), TimeUnit.MILLISECONDS);
        }
        catch (InterruptedException e)
        {
            Thread.currentThread().interrupt();
            throw new RuntimeException(e);
        }
        catch (ExecutionException e)
        {
            Throwable c = e.getCause();
            if (c instanceof RuntimeException)
                throw (RuntimeException) c;
            throw new RuntimeException(c);
        }
        catch (TimeoutException e)
        {
            // retry a last time with the difference of UDF-fail-timeout to consumed CPU time (just in case execution hit a badly timed GC)
            try
            {
                long cpuTimeMillis = threadMXBean.getThreadCpuTime(threadIdAndCpuTime.threadId) - threadIdAndCpuTime.cpuTime;
                cpuTimeMillis /= 1000000L;

                return future.get(Math.max(DatabaseDescriptor.getUserDefinedFunctionFailTimeout() - cpuTimeMillis, 0L),
                                  TimeUnit.MILLISECONDS);
            }
            catch (InterruptedException e1)
            {
                Thread.currentThread().interrupt();
                throw new RuntimeException(e);
            }
            catch (ExecutionException e1)
            {
                Throwable c = e.getCause();
                if (c instanceof RuntimeException)
                    throw (RuntimeException) c;
                throw new RuntimeException(c);
            }
            catch (TimeoutException e1)
            {
                TimeoutException cause = new TimeoutException(String.format("User defined function %s ran longer than %dms%s",
                                                                            this,
                                                                            DatabaseDescriptor.getUserDefinedFunctionFailTimeout(),
                                                                            DatabaseDescriptor.getUserFunctionTimeoutPolicy() == Config.UserFunctionTimeoutPolicy.ignore
                                                                            ? "" : " - will stop Cassandra VM"));
                FunctionExecutionException fe = FunctionExecutionException.create(this, cause);
                JVMStabilityInspector.userFunctionTimeout(cause);
                throw fe;
            }
        }
    }

    private List<ByteBuffer> makeEmptyParametersNull(List<ByteBuffer> parameters)
    {
        List<ByteBuffer> r = new ArrayList<>(parameters.size());
        for (int i = 0; i < parameters.size(); i++)
        {
            ByteBuffer param = parameters.get(i);
            r.add(UDHelper.isNullOrEmpty(argTypes.get(i), param)
                  ? null : param);
        }
        return r;
    }

    protected abstract ExecutorService executor();

    public boolean isCallableWrtNullable(List<ByteBuffer> parameters)
    {
        if (!calledOnNullInput)
            for (int i = 0; i < parameters.size(); i++)
                if (UDHelper.isNullOrEmpty(argTypes.get(i), parameters.get(i)))
                    return false;
        return true;
    }

    protected abstract ByteBuffer executeUserDefined(int protocolVersion, List<ByteBuffer> parameters);

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
     * Used by UDF implementations (both Java code generated by {@link JavaBasedUDFunction}
     * and script executor {@link ScriptBasedUDFunction}) to convert the C*
     * serialized representation to the Java object representation.
     *
     * @param protocolVersion the native protocol version used for serialization
     * @param argIndex        index of the UDF input argument
     */
    protected Object compose(int protocolVersion, int argIndex, ByteBuffer value)
    {
        return compose(argDataTypes, protocolVersion, argIndex, value);
    }

    protected static Object compose(DataType[] argDataTypes, int protocolVersion, int argIndex, ByteBuffer value)
    {
        return value == null ? null : argDataTypes[argIndex].deserialize(value, ProtocolVersion.fromInt(protocolVersion));
    }

    /**
     * Used by UDF implementations (both Java code generated by {@link JavaBasedUDFunction}
     * and script executor {@link ScriptBasedUDFunction}) to convert the Java
     * object representation for the return value to the C* serialized representation.
     *
     * @param protocolVersion the native protocol version used for serialization
     */
    protected ByteBuffer decompose(int protocolVersion, Object value)
    {
        return decompose(returnDataType, protocolVersion, value);
    }

    protected static ByteBuffer decompose(DataType dataType, int protocolVersion, Object value)
    {
        return value == null ? null : dataType.serialize(value, ProtocolVersion.fromInt(protocolVersion));
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

    private static class UDFClassLoader extends ClassLoader
    {
        // insecureClassLoader is the C* class loader
        static final ClassLoader insecureClassLoader = Thread.currentThread().getContextClassLoader();

        public URL getResource(String name)
        {
            if (!secureResource(name))
                return null;
            return insecureClassLoader.getResource(name);
        }

        protected URL findResource(String name)
        {
            return getResource(name);
        }

        public Enumeration<URL> getResources(String name)
        {
            return Collections.emptyEnumeration();
        }

        protected Class<?> findClass(String name) throws ClassNotFoundException
        {
            if (!secureResource(name.replace('.', '/') + ".class"))
                throw new ClassNotFoundException(name);
            return insecureClassLoader.loadClass(name);
        }

        public Class<?> loadClass(String name) throws ClassNotFoundException
        {
            if (!secureResource(name.replace('.', '/') + ".class"))
                throw new ClassNotFoundException(name);
            return super.loadClass(name);
        }
    }
}


File: src/java/org/apache/cassandra/cql3/statements/CreateFunctionStatement.java
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
package org.apache.cassandra.cql3.statements;

import java.util.ArrayList;
import java.util.HashSet;
import java.util.List;

import org.apache.cassandra.auth.*;
import org.apache.cassandra.config.DatabaseDescriptor;
import org.apache.cassandra.config.Schema;
import org.apache.cassandra.cql3.CQL3Type;
import org.apache.cassandra.cql3.ColumnIdentifier;
import org.apache.cassandra.cql3.functions.*;
import org.apache.cassandra.db.marshal.AbstractType;
import org.apache.cassandra.exceptions.*;
import org.apache.cassandra.schema.Functions;
import org.apache.cassandra.service.ClientState;
import org.apache.cassandra.service.MigrationManager;
import org.apache.cassandra.service.QueryState;
import org.apache.cassandra.thrift.ThriftValidation;
import org.apache.cassandra.transport.Event;

/**
 * A {@code CREATE FUNCTION} statement parsed from a CQL query.
 */
public final class CreateFunctionStatement extends SchemaAlteringStatement
{
    private final boolean orReplace;
    private final boolean ifNotExists;
    private FunctionName functionName;
    private final String language;
    private final String body;

    private final List<ColumnIdentifier> argNames;
    private final List<CQL3Type.Raw> argRawTypes;
    private final CQL3Type.Raw rawReturnType;
    private final boolean calledOnNullInput;

    private List<AbstractType<?>> argTypes;
    private AbstractType<?> returnType;
    private UDFunction udFunction;
    private boolean replaced;

    public CreateFunctionStatement(FunctionName functionName,
                                   String language,
                                   String body,
                                   List<ColumnIdentifier> argNames,
                                   List<CQL3Type.Raw> argRawTypes,
                                   CQL3Type.Raw rawReturnType,
                                   boolean calledOnNullInput,
                                   boolean orReplace,
                                   boolean ifNotExists)
    {
        this.functionName = functionName;
        this.language = language;
        this.body = body;
        this.argNames = argNames;
        this.argRawTypes = argRawTypes;
        this.rawReturnType = rawReturnType;
        this.calledOnNullInput = calledOnNullInput;
        this.orReplace = orReplace;
        this.ifNotExists = ifNotExists;
    }

    public Prepared prepare() throws InvalidRequestException
    {
        if (new HashSet<>(argNames).size() != argNames.size())
            throw new InvalidRequestException(String.format("duplicate argument names for given function %s with argument names %s",
                                                            functionName, argNames));

        argTypes = new ArrayList<>(argRawTypes.size());
        for (CQL3Type.Raw rawType : argRawTypes)
            argTypes.add(prepareType("arguments", rawType));

        returnType = prepareType("return type", rawReturnType);
        return super.prepare();
    }

    public void prepareKeyspace(ClientState state) throws InvalidRequestException
    {
        if (!functionName.hasKeyspace() && state.getRawKeyspace() != null)
            functionName = new FunctionName(state.getRawKeyspace(), functionName.name);

        if (!functionName.hasKeyspace())
            throw new InvalidRequestException("Functions must be fully qualified with a keyspace name if a keyspace is not set for the session");

        ThriftValidation.validateKeyspaceNotSystem(functionName.keyspace);
    }

    protected void grantPermissionsToCreator(QueryState state)
    {
        try
        {
            IResource resource = FunctionResource.function(functionName.keyspace, functionName.name, argTypes);
            DatabaseDescriptor.getAuthorizer().grant(AuthenticatedUser.SYSTEM_USER,
                                                     resource.applicablePermissions(),
                                                     resource,
                                                     RoleResource.role(state.getClientState().getUser().getName()));
        }
        catch (RequestExecutionException e)
        {
            throw new RuntimeException(e);
        }
    }

    public void checkAccess(ClientState state) throws UnauthorizedException, InvalidRequestException
    {
        if (Schema.instance.findFunction(functionName, argTypes).isPresent() && orReplace)
            state.ensureHasPermission(Permission.ALTER, FunctionResource.function(functionName.keyspace,
                                                                                  functionName.name,
                                                                                  argTypes));
        else
            state.ensureHasPermission(Permission.CREATE, FunctionResource.keyspace(functionName.keyspace));
    }

    public void validate(ClientState state) throws InvalidRequestException
    {
        if (!DatabaseDescriptor.enableUserDefinedFunctions())
            throw new InvalidRequestException("User-defined-functions are disabled in cassandra.yaml - set enable_user_defined_functions=true to enable if you are aware of the security risks");

        if (ifNotExists && orReplace)
            throw new InvalidRequestException("Cannot use both 'OR REPLACE' and 'IF NOT EXISTS' directives");

        if (Schema.instance.getKSMetaData(functionName.keyspace) == null)
            throw new InvalidRequestException(String.format("Cannot add function '%s' to non existing keyspace '%s'.", functionName.name, functionName.keyspace));
    }

    public Event.SchemaChange changeEvent()
    {
        return new Event.SchemaChange(replaced ? Event.SchemaChange.Change.UPDATED : Event.SchemaChange.Change.CREATED,
                                      Event.SchemaChange.Target.FUNCTION,
                                      udFunction.name().keyspace, udFunction.name().name, AbstractType.asCQLTypeStringList(udFunction.argTypes()));
    }

    public boolean announceMigration(boolean isLocalOnly) throws RequestValidationException
    {
        Function old = Schema.instance.findFunction(functionName, argTypes).orElse(null);
        if (old != null)
        {
            if (ifNotExists)
                return false;
            if (!orReplace)
                throw new InvalidRequestException(String.format("Function %s already exists", old));
            if (!(old instanceof ScalarFunction))
                throw new InvalidRequestException(String.format("Function %s can only replace a function", old));
            if (calledOnNullInput != ((ScalarFunction) old).isCalledOnNullInput())
                throw new InvalidRequestException(String.format("Function %s can only be replaced with %s", old,
                                                                calledOnNullInput ? "CALLED ON NULL INPUT" : "RETURNS NULL ON NULL INPUT"));

            if (!Functions.typesMatch(old.returnType(), returnType))
                throw new InvalidRequestException(String.format("Cannot replace function %s, the new return type %s is not compatible with the return type %s of existing function",
                                                                functionName, returnType.asCQL3Type(), old.returnType().asCQL3Type()));
        }

        this.udFunction = UDFunction.create(functionName, argNames, argTypes, returnType, calledOnNullInput, language, body);
        this.replaced = old != null;

        MigrationManager.announceNewFunction(udFunction, isLocalOnly);

        return true;
    }

    private AbstractType<?> prepareType(String typeName, CQL3Type.Raw rawType)
    {
        if (rawType.isFrozen())
            throw new InvalidRequestException(String.format("The function %s should not be frozen; remove the frozen<> modifier", typeName));

        // UDT are not supported non frozen but we do not allow the frozen keyword for argument. So for the moment we
        // freeze them here
        if (!rawType.canBeNonFrozen())
            rawType.freeze();

        AbstractType<?> type = rawType.prepare(functionName.keyspace).getType();
        return type;
    }
}


File: test/unit/org/apache/cassandra/cql3/validation/entities/UFPureScriptTest.java
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
import java.util.Arrays;
import java.util.Date;
import java.util.List;
import java.util.Map;
import java.util.Set;
import java.util.TreeMap;
import java.util.TreeSet;
import java.util.UUID;

import org.junit.Assert;
import org.junit.Test;

import com.datastax.driver.core.DataType;
import com.datastax.driver.core.TupleType;
import com.datastax.driver.core.TupleValue;
import org.apache.cassandra.cql3.CQLTester;
import org.apache.cassandra.cql3.UntypedResultSet;
import org.apache.cassandra.cql3.functions.FunctionName;
import org.apache.cassandra.exceptions.FunctionExecutionException;
import org.apache.cassandra.transport.Server;
import org.apache.cassandra.utils.UUIDGen;

public class UFPureScriptTest extends CQLTester
{
    // Just JavaScript UDFs to check how UDF - especially security/class-loading/sandboxing stuff -
    // behaves, if no Java UDF has been executed before.

    // Do not add any other test here - especially none using Java UDFs

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
                                      "       tup.getList(1, java.lang.Double.class);$$;");
        String fTup4 = createFunction(KEYSPACE_PER_TEST, tupleTypeDef,
                                      "CREATE FUNCTION %s( tup " + tupleTypeDef + " ) " +
                                      "RETURNS NULL ON NULL INPUT " +
                                      "RETURNS set<text> " +
                                      "LANGUAGE javascript\n" +
                                      "AS $$" +
                                      "       tup.getSet(2, java.lang.String.class);$$;");
        String fTup5 = createFunction(KEYSPACE_PER_TEST, tupleTypeDef,
                                      "CREATE FUNCTION %s( tup " + tupleTypeDef + " ) " +
                                      "RETURNS NULL ON NULL INPUT " +
                                      "RETURNS map<int, boolean> " +
                                      "LANGUAGE javascript\n" +
                                      "AS $$" +
                                      "       tup.getMap(3, java.lang.Integer.class, java.lang.Boolean.class);$$;");

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
                                      "RETURNS " + type + ' ' +
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
}
