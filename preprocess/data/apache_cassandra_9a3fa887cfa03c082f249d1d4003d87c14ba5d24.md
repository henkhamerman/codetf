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

import java.io.IOException;
import java.io.StringReader;
import java.util.List;
import java.util.Set;
import java.util.concurrent.TimeUnit;

import com.google.common.collect.Sets;

import org.apache.cassandra.config.EncryptionOptions.ClientEncryptionOptions;
import org.apache.cassandra.config.EncryptionOptions.ServerEncryptionOptions;
import org.apache.cassandra.exceptions.ConfigurationException;
import org.supercsv.io.CsvListReader;
import org.supercsv.prefs.CsvPreference;

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
    public volatile boolean hinted_handoff_enabled_global = true;
    public String hinted_handoff_enabled;
    public Set<String> hinted_handoff_enabled_by_dc = Sets.newConcurrentHashSet();
    public volatile Integer max_hint_window_in_ms = 3 * 3600 * 1000; // three hours

    public ParameterizedClass seed_provider;
    public DiskAccessMode disk_access_mode = DiskAccessMode.auto;

    public DiskFailurePolicy disk_failure_policy = DiskFailurePolicy.ignore;
    public CommitFailurePolicy commit_failure_policy = CommitFailurePolicy.stop;

    /* initial token in the ring */
    public String initial_token;
    public Integer num_tokens = 1;

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

    private static final CsvPreference STANDARD_SURROUNDING_SPACES_NEED_QUOTES = new CsvPreference.Builder(CsvPreference.STANDARD_PREFERENCE)
                                                                                                  .surroundingSpacesNeedQuotes(true).build();

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

    public void configHintedHandoff() throws ConfigurationException
    {
        if (hinted_handoff_enabled != null && !hinted_handoff_enabled.isEmpty())
        {
            if (hinted_handoff_enabled.equalsIgnoreCase("true"))
            {
                hinted_handoff_enabled_global = true;
            }
            else if (hinted_handoff_enabled.equalsIgnoreCase("false"))
            {
                hinted_handoff_enabled_global = false;
            }
            else
            {
                try
                {
                    hinted_handoff_enabled_by_dc.addAll(parseHintedHandoffEnabledDCs(hinted_handoff_enabled));
                }
                catch (IOException e)
                {
                    throw new ConfigurationException("Invalid hinted_handoff_enabled parameter " + hinted_handoff_enabled, e);
                }
            }
        }
    }

    public static List<String> parseHintedHandoffEnabledDCs(final String dcNames) throws IOException
    {
        try (final CsvListReader csvListReader = new CsvListReader(new StringReader(dcNames), STANDARD_SURROUNDING_SPACES_NEED_QUOTES))
        {
        	return csvListReader.read();
        }
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

        // Always force standard mode access on Windows - CASSANDRA-6993. Windows won't allow deletion of hard-links to files that
        // are memory-mapped which causes trouble with snapshots.
        if (FBUtilities.isWindows())
        {
            conf.disk_access_mode = Config.DiskAccessMode.standard;
            indexAccessMode = conf.disk_access_mode;
            logger.info("Windows environment detected.  DiskAccessMode set to {}, indexAccessMode {}", conf.disk_access_mode, indexAccessMode);
        }
        else
        {
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

    public static Config.DiskAccessMode getIndexAccessMode()
    {
        return indexAccessMode;
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
    public static void setAutoSnapshot(boolean autoSnapshot) {
        conf.auto_snapshot = autoSnapshot;
    }

    public static boolean isAutoBootstrap()
    {
        return Boolean.parseBoolean(System.getProperty("cassandra.auto_bootstrap", conf.auto_bootstrap.toString()));
    }

    public static void setHintedHandoffEnabled(boolean hintedHandoffEnabled)
    {
        conf.hinted_handoff_enabled_global = hintedHandoffEnabled;
        conf.hinted_handoff_enabled_by_dc.clear();
    }

    public static void setHintedHandoffEnabled(final String dcNames)
    {
        List<String> dcNameList;
        try
        {
            dcNameList = Config.parseHintedHandoffEnabledDCs(dcNames);
        }
        catch (IOException e)
        {
            throw new IllegalArgumentException("Could not read csv of dcs for hinted handoff enable. " + dcNames, e);
        }

        if (dcNameList.isEmpty())
            throw new IllegalArgumentException("Empty list of Dcs for hinted handoff enable");

        conf.hinted_handoff_enabled_by_dc.clear();
        conf.hinted_handoff_enabled_by_dc.addAll(dcNameList);
    }

    public static boolean hintedHandoffEnabled()
    {
        return conf.hinted_handoff_enabled_global;
    }

    public static Set<String> hintedHandoffEnabledByDC()
    {
        return Collections.unmodifiableSet(conf.hinted_handoff_enabled_by_dc);
    }

    public static boolean shouldHintByDC()
    {
        return !conf.hinted_handoff_enabled_by_dc.isEmpty();
    }

    public static boolean hintedHandoffEnabled(final String dcName)
    {
        return conf.hinted_handoff_enabled_by_dc.contains(dcName);
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


File: src/java/org/apache/cassandra/db/commitlog/CommitLog.java
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
package org.apache.cassandra.db.commitlog;

import java.io.*;
import java.lang.management.ManagementFactory;
import java.nio.ByteBuffer;
import java.util.*;

import javax.management.MBeanServer;
import javax.management.ObjectName;

import com.google.common.annotations.VisibleForTesting;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import org.apache.commons.lang3.StringUtils;

import com.github.tjake.ICRC32;

import org.apache.cassandra.config.Config;
import org.apache.cassandra.config.DatabaseDescriptor;
import org.apache.cassandra.config.ParameterizedClass;
import org.apache.cassandra.db.*;
import org.apache.cassandra.io.FSWriteError;
import org.apache.cassandra.io.compress.CompressionParameters;
import org.apache.cassandra.io.compress.ICompressor;
import org.apache.cassandra.io.util.BufferedDataOutputStreamPlus;
import org.apache.cassandra.io.util.DataOutputBufferFixed;
import org.apache.cassandra.metrics.CommitLogMetrics;
import org.apache.cassandra.net.MessagingService;
import org.apache.cassandra.service.StorageService;
import org.apache.cassandra.utils.CRC32Factory;
import org.apache.cassandra.utils.JVMStabilityInspector;

import static org.apache.cassandra.db.commitlog.CommitLogSegment.*;

/*
 * Commit Log tracks every write operation into the system. The aim of the commit log is to be able to
 * successfully recover data that was not stored to disk via the Memtable.
 */
public class CommitLog implements CommitLogMBean
{
    private static final Logger logger = LoggerFactory.getLogger(CommitLog.class);

    public static final CommitLog instance = CommitLog.construct();

    // we only permit records HALF the size of a commit log, to ensure we don't spin allocating many mostly
    // empty segments when writing large records
    private final long MAX_MUTATION_SIZE = DatabaseDescriptor.getCommitLogSegmentSize() >> 1;

    public final CommitLogSegmentManager allocator;
    public final CommitLogArchiver archiver;
    final CommitLogMetrics metrics;
    final AbstractCommitLogService executor;

    final ICompressor compressor;
    public ParameterizedClass compressorClass;
    final public String location;

    static private CommitLog construct()
    {
        CommitLog log = new CommitLog(DatabaseDescriptor.getCommitLogLocation(), new CommitLogArchiver());

        MBeanServer mbs = ManagementFactory.getPlatformMBeanServer();
        try
        {
            mbs.registerMBean(log, new ObjectName("org.apache.cassandra.db:type=Commitlog"));
        }
        catch (Exception e)
        {
            throw new RuntimeException(e);
        }
        return log;
    }

    @VisibleForTesting
    CommitLog(String location, CommitLogArchiver archiver)
    {
        compressorClass = DatabaseDescriptor.getCommitLogCompression();
        this.location = location;
        ICompressor compressor = compressorClass != null ? CompressionParameters.createCompressor(compressorClass) : null;
        DatabaseDescriptor.createAllDirectories();

        this.compressor = compressor;
        this.archiver = archiver;
        metrics = new CommitLogMetrics();

        executor = DatabaseDescriptor.getCommitLogSync() == Config.CommitLogSync.batch
                ? new BatchCommitLogService(this)
                : new PeriodicCommitLogService(this);

        allocator = new CommitLogSegmentManager(this);
        executor.start();

        // register metrics
        metrics.attach(executor, allocator);
    }

    /**
     * Perform recovery on commit logs located in the directory specified by the config file.
     *
     * @return the number of mutations replayed
     */
    public int recover() throws IOException
    {
        // If createReserveSegments is already flipped, the CLSM is running and recovery has already taken place.
        if (allocator.createReserveSegments)
            return 0;

        // Allocator could be in the process of initial startup with 0 active and available segments. We need to wait for
        // the allocation manager to finish allocation and add it to available segments so we don't get an invalid response
        // on allocator.manages(...) below by grabbing a file off the filesystem before it's added to the CLQ.
        allocator.allocatingFrom();

        FilenameFilter unmanagedFilesFilter = new FilenameFilter()
        {
            public boolean accept(File dir, String name)
            {
                // we used to try to avoid instantiating commitlog (thus creating an empty segment ready for writes)
                // until after recover was finished.  this turns out to be fragile; it is less error-prone to go
                // ahead and allow writes before recover(), and just skip active segments when we do.
                return CommitLogDescriptor.isValid(name) && !allocator.manages(name);
            }
        };

        // submit all existing files in the commit log dir for archiving prior to recovery - CASSANDRA-6904
        for (File file : new File(DatabaseDescriptor.getCommitLogLocation()).listFiles(unmanagedFilesFilter))
        {
            archiver.maybeArchive(file.getPath(), file.getName());
            archiver.maybeWaitForArchiving(file.getName());
        }

        assert archiver.archivePending.isEmpty() : "Not all commit log archive tasks were completed before restore";
        archiver.maybeRestoreArchive();

        File[] files = new File(DatabaseDescriptor.getCommitLogLocation()).listFiles(unmanagedFilesFilter);
        int replayed = 0;
        if (files.length == 0)
        {
            logger.info("No commitlog files found; skipping replay");
        }
        else
        {
            Arrays.sort(files, new CommitLogSegmentFileComparator());
            logger.info("Replaying {}", StringUtils.join(files, ", "));
            replayed = recover(files);
            logger.info("Log replay complete, {} replayed mutations", replayed);

            for (File f : files)
                allocator.recycleSegment(f);
        }

        allocator.enableReserveSegmentCreation();
        return replayed;
    }

    /**
     * Perform recovery on a list of commit log files.
     *
     * @param clogs   the list of commit log files to replay
     * @return the number of mutations replayed
     */
    public int recover(File... clogs) throws IOException
    {
        CommitLogReplayer recovery = CommitLogReplayer.create();
        recovery.recover(clogs);
        return recovery.blockForWrites();
    }

    /**
     * Perform recovery on a single commit log.
     */
    public void recover(String path) throws IOException
    {
        recover(new File(path));
    }

    /**
     * @return a ReplayPosition which, if >= one returned from add(), implies add() was started
     * (but not necessarily finished) prior to this call
     */
    public ReplayPosition getContext()
    {
        return allocator.allocatingFrom().getContext();
    }

    /**
     * Flushes all dirty CFs, waiting for them to free and recycle any segments they were retaining
     */
    public void forceRecycleAllSegments(Iterable<UUID> droppedCfs)
    {
        allocator.forceRecycleAll(droppedCfs);
    }

    /**
     * Flushes all dirty CFs, waiting for them to free and recycle any segments they were retaining
     */
    public void forceRecycleAllSegments()
    {
        allocator.forceRecycleAll(Collections.<UUID>emptyList());
    }

    /**
     * Forces a disk flush on the commit log files that need it.  Blocking.
     */
    public void sync(boolean syncAllSegments)
    {
        CommitLogSegment current = allocator.allocatingFrom();
        for (CommitLogSegment segment : allocator.getActiveSegments())
        {
            if (!syncAllSegments && segment.id > current.id)
                return;
            segment.sync();
        }
    }

    /**
     * Preempts the CLExecutor, telling to to sync immediately
     */
    public void requestExtraSync()
    {
        executor.requestExtraSync();
    }

    /**
     * Add a Mutation to the commit log.
     *
     * @param mutation the Mutation to add to the log
     */
    public ReplayPosition add(Mutation mutation)
    {
        assert mutation != null;

        long size = Mutation.serializer.serializedSize(mutation, MessagingService.current_version);

        long totalSize = size + ENTRY_OVERHEAD_SIZE;
        if (totalSize > MAX_MUTATION_SIZE)
        {
            throw new IllegalArgumentException(String.format("Mutation of %s bytes is too large for the maxiumum size of %s",
                                                             totalSize, MAX_MUTATION_SIZE));
        }

        Allocation alloc = allocator.allocate(mutation, (int) totalSize);
        ICRC32 checksum = CRC32Factory.instance.create();
        final ByteBuffer buffer = alloc.getBuffer();
        try (BufferedDataOutputStreamPlus dos = new DataOutputBufferFixed(buffer))
        {
            // checksummed length
            dos.writeInt((int) size);
            checksum.update(buffer, buffer.position() - 4, 4);
            buffer.putInt(checksum.getCrc());

            int start = buffer.position();
            // checksummed mutation
            Mutation.serializer.serialize(mutation, dos, MessagingService.current_version);
            checksum.update(buffer, start, (int) size);
            buffer.putInt(checksum.getCrc());
        }
        catch (IOException e)
        {
            throw new FSWriteError(e, alloc.getSegment().getPath());
        }
        finally
        {
            alloc.markWritten();
        }

        executor.finishWriteFor(alloc);
        return alloc.getReplayPosition();
    }

    /**
     * Modifies the per-CF dirty cursors of any commit log segments for the column family according to the position
     * given. Discards any commit log segments that are no longer used.
     *
     * @param cfId    the column family ID that was flushed
     * @param context the replay position of the flush
     */
    public void discardCompletedSegments(final UUID cfId, final ReplayPosition context)
    {
        logger.debug("discard completed log segments for {}, table {}", context, cfId);

        // Go thru the active segment files, which are ordered oldest to newest, marking the
        // flushed CF as clean, until we reach the segment file containing the ReplayPosition passed
        // in the arguments. Any segments that become unused after they are marked clean will be
        // recycled or discarded.
        for (Iterator<CommitLogSegment> iter = allocator.getActiveSegments().iterator(); iter.hasNext();)
        {
            CommitLogSegment segment = iter.next();
            segment.markClean(cfId, context);

            if (segment.isUnused())
            {
                logger.debug("Commit log segment {} is unused", segment);
                allocator.recycleSegment(segment);
            }
            else
            {
                logger.debug("Not safe to delete{} commit log segment {}; dirty is {}",
                        (iter.hasNext() ? "" : " active"), segment, segment.dirtyString());
            }

            // Don't mark or try to delete any newer segments once we've reached the one containing the
            // position of the flush.
            if (segment.contains(context))
                break;
        }
    }

    @Override
    public String getArchiveCommand()
    {
        return archiver.archiveCommand;
    }

    @Override
    public String getRestoreCommand()
    {
        return archiver.restoreCommand;
    }

    @Override
    public String getRestoreDirectories()
    {
        return archiver.restoreDirectories;
    }

    @Override
    public long getRestorePointInTime()
    {
        return archiver.restorePointInTime;
    }

    @Override
    public String getRestorePrecision()
    {
        return archiver.precision.toString();
    }

    public List<String> getActiveSegmentNames()
    {
        List<String> segmentNames = new ArrayList<>();
        for (CommitLogSegment segment : allocator.getActiveSegments())
            segmentNames.add(segment.getName());
        return segmentNames;
    }

    public List<String> getArchivingSegmentNames()
    {
        return new ArrayList<>(archiver.archivePending.keySet());
    }

    @Override
    public long getActiveContentSize()
    {
        long size = 0;
        for (CommitLogSegment segment : allocator.getActiveSegments())
            size += segment.contentSize();
        return size;
    }

    @Override
    public long getActiveOnDiskSize()
    {
        return allocator.onDiskSize();
    }

    @Override
    public Map<String, Double> getActiveSegmentCompressionRatios()
    {
        Map<String, Double> segmentRatios = new TreeMap<>();
        for (CommitLogSegment segment : allocator.getActiveSegments())
            segmentRatios.put(segment.getName(), 1.0 * segment.onDiskSize() / segment.contentSize());
        return segmentRatios;
    }

    /**
     * Shuts down the threads used by the commit log, blocking until completion.
     */
    public void shutdownBlocking() throws InterruptedException
    {
        executor.shutdown();
        executor.awaitTermination();
        allocator.shutdown();
        allocator.awaitTermination();
    }

    /**
     * FOR TESTING PURPOSES. See CommitLogAllocator.
     * @return the number of files recovered
     */
    public int resetUnsafe(boolean deleteSegments) throws IOException
    {
        stopUnsafe(deleteSegments);
        return startUnsafe();
    }

    /**
     * FOR TESTING PURPOSES. See CommitLogAllocator.
     */
    public void stopUnsafe(boolean deleteSegments)
    {
        executor.shutdown();
        try
        {
            executor.awaitTermination();
        }
        catch (InterruptedException e)
        {
            throw new RuntimeException(e);
        }
        allocator.stopUnsafe(deleteSegments);
    }

    /**
     * FOR TESTING PURPOSES.  See CommitLogAllocator
     */
    public int startUnsafe() throws IOException
    {
        allocator.startUnsafe();
        executor.startUnsafe();
        return recover();
    }

    /**
     * Used by tests.
     *
     * @return the number of active segments (segments with unflushed data in them)
     */
    public int activeSegments()
    {
        return allocator.getActiveSegments().size();
    }

    @VisibleForTesting
    public static boolean handleCommitError(String message, Throwable t)
    {
        JVMStabilityInspector.inspectCommitLogThrowable(t);
        switch (DatabaseDescriptor.getCommitFailurePolicy())
        {
            // Needed here for unit tests to not fail on default assertion
            case die:
            case stop:
                StorageService.instance.stopTransports();
                //$FALL-THROUGH$
            case stop_commit:
                logger.error(String.format("%s. Commit disk failure policy is %s; terminating thread", message, DatabaseDescriptor.getCommitFailurePolicy()), t);
                return false;
            case ignore:
                logger.error(message, t);
                return true;
            default:
                throw new AssertionError(DatabaseDescriptor.getCommitFailurePolicy());
        }
    }
}


File: src/java/org/apache/cassandra/db/commitlog/CompressedSegment.java
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
package org.apache.cassandra.db.commitlog;

import java.io.IOException;
import java.nio.ByteBuffer;
import java.util.Queue;
import java.util.concurrent.ConcurrentLinkedQueue;

import org.apache.cassandra.config.DatabaseDescriptor;
import org.apache.cassandra.io.FSWriteError;
import org.apache.cassandra.io.compress.BufferType;
import org.apache.cassandra.io.compress.ICompressor;
import org.apache.cassandra.io.util.FileUtils;
import org.apache.cassandra.utils.SyncUtil;

/*
 * Compressed commit log segment. Provides an in-memory buffer for the mutation threads. On sync compresses the written
 * section of the buffer and writes it to the destination channel.
 */
public class CompressedSegment extends CommitLogSegment
{
    static private final ThreadLocal<ByteBuffer> compressedBufferHolder = new ThreadLocal<ByteBuffer>() {
        protected ByteBuffer initialValue()
        {
            return ByteBuffer.allocate(0);
        }
    };
    static Queue<ByteBuffer> bufferPool = new ConcurrentLinkedQueue<>();

    /**
     * Maximum number of buffers in the compression pool. The default value is 3, it should not be set lower than that
     * (one segment in compression, one written to, one in reserve); delays in compression may cause the log to use
     * more, depending on how soon the sync policy stops all writing threads.
     */
    static final int MAX_BUFFERPOOL_SIZE = DatabaseDescriptor.getCommitLogMaxCompressionBuffersInPool();

    static final int COMPRESSED_MARKER_SIZE = SYNC_MARKER_SIZE + 4;
    final ICompressor compressor;

    volatile long lastWrittenPos = 0;

    /**
     * Constructs a new segment file.
     */
    CompressedSegment(CommitLog commitLog)
    {
        super(commitLog);
        this.compressor = commitLog.compressor;
        try
        {
            channel.write((ByteBuffer) buffer.duplicate().flip());
            commitLog.allocator.addSize(lastWrittenPos = buffer.position());
        }
        catch (IOException e)
        {
            throw new FSWriteError(e, getPath());
        }
    }

    ByteBuffer allocate(int size)
    {
        return compressor.preferredBufferType().allocate(size);
    }

    ByteBuffer createBuffer(CommitLog commitLog)
    {
        ByteBuffer buf = bufferPool.poll();
        if (buf == null)
        {
            // this.compressor is not yet set, so we must use the commitLog's one.
            buf = commitLog.compressor.preferredBufferType().allocate(DatabaseDescriptor.getCommitLogSegmentSize());
        } else
            buf.clear();
        return buf;
    }

    static long startMillis = System.currentTimeMillis();

    @Override
    void write(int startMarker, int nextMarker)
    {
        int contentStart = startMarker + SYNC_MARKER_SIZE;
        int length = nextMarker - contentStart;
        // The length may be 0 when the segment is being closed.
        assert length > 0 || length == 0 && !isStillAllocating();

        try
        {
            int neededBufferSize = compressor.initialCompressedBufferLength(length) + COMPRESSED_MARKER_SIZE;
            ByteBuffer compressedBuffer = compressedBufferHolder.get();
            if (compressor.preferredBufferType() != BufferType.typeOf(compressedBuffer) ||
                compressedBuffer.capacity() < neededBufferSize)
            {
                FileUtils.clean(compressedBuffer);
                compressedBuffer = allocate(neededBufferSize);
                compressedBufferHolder.set(compressedBuffer);
            }

            ByteBuffer inputBuffer = buffer.duplicate();
            inputBuffer.limit(contentStart + length).position(contentStart);
            compressedBuffer.limit(compressedBuffer.capacity()).position(COMPRESSED_MARKER_SIZE);
            compressor.compress(inputBuffer, compressedBuffer);

            compressedBuffer.flip();
            compressedBuffer.putInt(SYNC_MARKER_SIZE, length);

            // Only one thread can be here at a given time.
            // Protected by synchronization on CommitLogSegment.sync().
            writeSyncMarker(compressedBuffer, 0, (int) channel.position(), (int) channel.position() + compressedBuffer.remaining());
            commitLog.allocator.addSize(compressedBuffer.limit());
            channel.write(compressedBuffer);
            assert channel.position() - lastWrittenPos == compressedBuffer.limit();
            lastWrittenPos = channel.position();
            SyncUtil.force(channel, true);
        }
        catch (Exception e)
        {
            throw new FSWriteError(e, getPath());
        }
    }

    @Override
    protected void internalClose()
    {
        if (bufferPool.size() < MAX_BUFFERPOOL_SIZE)
            bufferPool.add(buffer);
        else
            FileUtils.clean(buffer);

        super.internalClose();
    }

    static void shutdown()
    {
        bufferPool.clear();
    }

    @Override
    public long onDiskSize()
    {
        return lastWrittenPos;
    }
}


File: src/java/org/apache/cassandra/dht/BootStrapper.java
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
package org.apache.cassandra.dht;

import java.io.DataInput;
import java.io.IOException;
import java.net.InetAddress;
import java.util.*;
import java.util.concurrent.atomic.AtomicInteger;

import com.google.common.util.concurrent.ListenableFuture;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import org.apache.cassandra.config.DatabaseDescriptor;
import org.apache.cassandra.config.Schema;
import org.apache.cassandra.db.Keyspace;
import org.apache.cassandra.db.TypeSizes;
import org.apache.cassandra.exceptions.ConfigurationException;
import org.apache.cassandra.gms.FailureDetector;
import org.apache.cassandra.io.IVersionedSerializer;
import org.apache.cassandra.io.util.DataOutputPlus;
import org.apache.cassandra.locator.AbstractReplicationStrategy;
import org.apache.cassandra.locator.TokenMetadata;
import org.apache.cassandra.service.StorageService;
import org.apache.cassandra.streaming.*;
import org.apache.cassandra.utils.progress.ProgressEvent;
import org.apache.cassandra.utils.progress.ProgressEventNotifierSupport;
import org.apache.cassandra.utils.progress.ProgressEventType;

public class BootStrapper extends ProgressEventNotifierSupport
{
    private static final Logger logger = LoggerFactory.getLogger(BootStrapper.class);

    /* endpoint that needs to be bootstrapped */
    protected final InetAddress address;
    /* token of the node being bootstrapped. */
    protected final Collection<Token> tokens;
    protected final TokenMetadata tokenMetadata;

    public BootStrapper(InetAddress address, Collection<Token> tokens, TokenMetadata tmd)
    {
        assert address != null;
        assert tokens != null && !tokens.isEmpty();

        this.address = address;
        this.tokens = tokens;
        this.tokenMetadata = tmd;
    }

    public ListenableFuture<StreamState> bootstrap(StreamStateStore stateStore, boolean useStrictConsistency)
    {
        logger.debug("Beginning bootstrap process");

        RangeStreamer streamer = new RangeStreamer(tokenMetadata,
                                                   tokens,
                                                   address,
                                                   "Bootstrap",
                                                   useStrictConsistency,
                                                   DatabaseDescriptor.getEndpointSnitch(),
                                                   stateStore);
        streamer.addSourceFilter(new RangeStreamer.FailureDetectorSourceFilter(FailureDetector.instance));

        for (String keyspaceName : Schema.instance.getNonSystemKeyspaces())
        {
            AbstractReplicationStrategy strategy = Keyspace.open(keyspaceName).getReplicationStrategy();
            streamer.addRanges(keyspaceName, strategy.getPendingAddressRanges(tokenMetadata, tokens, address));
        }

        StreamResultFuture bootstrapStreamResult = streamer.fetchAsync();
        bootstrapStreamResult.addEventListener(new StreamEventHandler()
        {
            private final AtomicInteger receivedFiles = new AtomicInteger();
            private final AtomicInteger totalFilesToReceive = new AtomicInteger();

            @Override
            public void handleStreamEvent(StreamEvent event)
            {
                switch (event.eventType)
                {
                    case STREAM_PREPARED:
                        StreamEvent.SessionPreparedEvent prepared = (StreamEvent.SessionPreparedEvent) event;
                        int currentTotal = totalFilesToReceive.addAndGet((int) prepared.session.getTotalFilesToReceive());
                        ProgressEvent prepareProgress = new ProgressEvent(ProgressEventType.PROGRESS, receivedFiles.get(), currentTotal, "prepare with " + prepared.session.peer + " complete");
                        fireProgressEvent("bootstrap", prepareProgress);
                        break;

                    case FILE_PROGRESS:
                        StreamEvent.ProgressEvent progress = (StreamEvent.ProgressEvent) event;
                        if (progress.progress.isCompleted())
                        {
                            int received = receivedFiles.incrementAndGet();
                            ProgressEvent currentProgress = new ProgressEvent(ProgressEventType.PROGRESS, received, totalFilesToReceive.get(), "received file " + progress.progress.fileName);
                            fireProgressEvent("bootstrap", currentProgress);
                        }
                        break;

                    case STREAM_COMPLETE:
                        StreamEvent.SessionCompleteEvent completeEvent = (StreamEvent.SessionCompleteEvent) event;
                        ProgressEvent completeProgress = new ProgressEvent(ProgressEventType.PROGRESS, receivedFiles.get(), totalFilesToReceive.get(), "session with " + completeEvent.peer + " complete");
                        fireProgressEvent("bootstrap", completeProgress);
                        break;
                }
            }

            @Override
            public void onSuccess(StreamState streamState)
            {
                ProgressEventType type;
                String message;

                if (streamState.hasFailedSession())
                {
                    type = ProgressEventType.ERROR;
                    message = "Some bootstrap stream failed";
                }
                else
                {
                    type = ProgressEventType.SUCCESS;
                    message = "Bootstrap streaming success";
                }
                ProgressEvent currentProgress = new ProgressEvent(type, receivedFiles.get(), totalFilesToReceive.get(), message);
                fireProgressEvent("bootstrap", currentProgress);
            }

            @Override
            public void onFailure(Throwable throwable)
            {
                ProgressEvent currentProgress = new ProgressEvent(ProgressEventType.ERROR, receivedFiles.get(), totalFilesToReceive.get(), throwable.getMessage());
                fireProgressEvent("bootstrap", currentProgress);
            }
        });
        return bootstrapStreamResult;
    }

    /**
     * if initialtoken was specified, use that (split on comma).
     * otherwise, if num_tokens == 1, pick a token to assume half the load of the most-loaded node.
     * else choose num_tokens tokens at random
     */
    public static Collection<Token> getBootstrapTokens(final TokenMetadata metadata) throws ConfigurationException
    {
        Collection<String> initialTokens = DatabaseDescriptor.getInitialTokens();
        // if user specified tokens, use those
        if (initialTokens.size() > 0)
        {
            logger.debug("tokens manually specified as {}",  initialTokens);
            List<Token> tokens = new ArrayList<>(initialTokens.size());
            for (String tokenString : initialTokens)
            {
                Token token = StorageService.getPartitioner().getTokenFactory().fromString(tokenString);
                if (metadata.getEndpoint(token) != null)
                    throw new ConfigurationException("Bootstrapping to existing token " + tokenString + " is not allowed (decommission/removenode the old node first).");
                tokens.add(token);
            }
            return tokens;
        }

        int numTokens = DatabaseDescriptor.getNumTokens();
        if (numTokens < 1)
            throw new ConfigurationException("num_tokens must be >= 1");

        if (numTokens == 1)
            logger.warn("Picking random token for a single vnode.  You should probably add more vnodes; failing that, you should probably specify the token manually");

        return getRandomTokens(metadata, numTokens);
    }

    public static Collection<Token> getRandomTokens(TokenMetadata metadata, int numTokens)
    {
        Set<Token> tokens = new HashSet<>(numTokens);
        while (tokens.size() < numTokens)
        {
            Token token = StorageService.getPartitioner().getRandomToken();
            if (metadata.getEndpoint(token) == null)
                tokens.add(token);
        }
        return tokens;
    }

    public static class StringSerializer implements IVersionedSerializer<String>
    {
        public static final StringSerializer instance = new StringSerializer();

        public void serialize(String s, DataOutputPlus out, int version) throws IOException
        {
            out.writeUTF(s);
        }

        public String deserialize(DataInput in, int version) throws IOException
        {
            return in.readUTF();
        }

        public long serializedSize(String s, int version)
        {
            return TypeSizes.NATIVE.sizeof(s);
        }
    }
}


File: src/java/org/apache/cassandra/dht/ByteOrderedPartitioner.java
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
package org.apache.cassandra.dht;

import org.apache.cassandra.config.CFMetaData;
import org.apache.cassandra.config.Schema;
import org.apache.cassandra.db.BufferDecoratedKey;
import org.apache.cassandra.db.DecoratedKey;
import org.apache.cassandra.db.marshal.AbstractType;
import org.apache.cassandra.db.marshal.BytesType;
import org.apache.cassandra.exceptions.ConfigurationException;
import org.apache.cassandra.service.StorageService;
import org.apache.cassandra.utils.ByteBufferUtil;
import org.apache.cassandra.utils.FBUtilities;
import org.apache.cassandra.utils.Hex;
import org.apache.cassandra.utils.ObjectSizes;
import org.apache.cassandra.utils.Pair;

import org.apache.commons.lang3.ArrayUtils;

import java.math.BigInteger;
import java.nio.ByteBuffer;
import java.util.ArrayList;
import java.util.Arrays;
import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.Random;

public class ByteOrderedPartitioner implements IPartitioner
{
    public static final BytesToken MINIMUM = new BytesToken(ArrayUtils.EMPTY_BYTE_ARRAY);

    public static final BigInteger BYTE_MASK = new BigInteger("255");

    private static final long EMPTY_SIZE = ObjectSizes.measure(MINIMUM);

    public static final ByteOrderedPartitioner instance = new ByteOrderedPartitioner();

    public static class BytesToken extends Token
    {
        static final long serialVersionUID = -2630749093733680626L;

        final byte[] token;

        public BytesToken(ByteBuffer token)
        {
            this(ByteBufferUtil.getArray(token));
        }

        public BytesToken(byte[] token)
        {
            this.token = token;
        }

        @Override
        public String toString()
        {
            return Hex.bytesToHex(token);
        }

        public int compareTo(Token other)
        {
            BytesToken o = (BytesToken) other;
            return FBUtilities.compareUnsigned(token, o.token, 0, 0, token.length, o.token.length);
        }

        @Override
        public int hashCode()
        {
            final int prime = 31;
            return prime + Arrays.hashCode(token);
        }

        @Override
        public boolean equals(Object obj)
        {
            if (this == obj)
                return true;
            if (!(obj instanceof BytesToken))
                return false;
            BytesToken other = (BytesToken) obj;

            return Arrays.equals(token, other.token);
        }

        @Override
        public IPartitioner getPartitioner()
        {
            return instance;
        }

        @Override
        public long getHeapSize()
        {
            return EMPTY_SIZE + ObjectSizes.sizeOfArray(token);
        }

        @Override
        public Object getTokenValue()
        {
            return token;
        }
    }

    public BytesToken getToken(ByteBuffer key)
    {
        if (key.remaining() == 0)
            return MINIMUM;
        return new BytesToken(key);
    }

    public DecoratedKey decorateKey(ByteBuffer key)
    {
        return new BufferDecoratedKey(getToken(key), key);
    }

    public BytesToken midpoint(Token lt, Token rt)
    {
        BytesToken ltoken = (BytesToken) lt;
        BytesToken rtoken = (BytesToken) rt;

        int sigbytes = Math.max(ltoken.token.length, rtoken.token.length);
        BigInteger left = bigForBytes(ltoken.token, sigbytes);
        BigInteger right = bigForBytes(rtoken.token, sigbytes);

        Pair<BigInteger,Boolean> midpair = FBUtilities.midpoint(left, right, 8*sigbytes);
        return new BytesToken(bytesForBig(midpair.left, sigbytes, midpair.right));
    }

    /**
     * Convert a byte array containing the most significant of 'sigbytes' bytes
     * representing a big-endian magnitude into a BigInteger.
     */
    private BigInteger bigForBytes(byte[] bytes, int sigbytes)
    {
        byte[] b;
        if (sigbytes != bytes.length)
        {
            b = new byte[sigbytes];
            System.arraycopy(bytes, 0, b, 0, bytes.length);
        } else
            b = bytes;
        return new BigInteger(1, b);
    }

    /**
     * Convert a (positive) BigInteger into a byte array representing its magnitude.
     * If remainder is true, an additional byte with the high order bit enabled
     * will be added to the end of the array
     */
    private byte[] bytesForBig(BigInteger big, int sigbytes, boolean remainder)
    {
        byte[] bytes = new byte[sigbytes + (remainder ? 1 : 0)];
        if (remainder)
        {
            // remaining bit is the most significant in the last byte
            bytes[sigbytes] |= 0x80;
        }
        // bitmask for a single byte
        for (int i = 0; i < sigbytes; i++)
        {
            int maskpos = 8 * (sigbytes - (i + 1));
            // apply bitmask and get byte value
            bytes[i] = (byte)(big.and(BYTE_MASK.shiftLeft(maskpos)).shiftRight(maskpos).intValue() & 0xFF);
        }
        return bytes;
    }

    public BytesToken getMinimumToken()
    {
        return MINIMUM;
    }

    public BytesToken getRandomToken()
    {
        Random r = new Random();
        byte[] buffer = new byte[16];
        r.nextBytes(buffer);
        return new BytesToken(buffer);
    }

    private final Token.TokenFactory tokenFactory = new Token.TokenFactory() {
        public ByteBuffer toByteArray(Token token)
        {
            BytesToken bytesToken = (BytesToken) token;
            return ByteBuffer.wrap(bytesToken.token);
        }

        public Token fromByteArray(ByteBuffer bytes)
        {
            return new BytesToken(bytes);
        }

        public String toString(Token token)
        {
            BytesToken bytesToken = (BytesToken) token;
            return Hex.bytesToHex(bytesToken.token);
        }

        public void validate(String token) throws ConfigurationException
        {
            try
            {
                if (token.length() % 2 == 1)
                    token = "0" + token;
                Hex.hexToBytes(token);
            }
            catch (NumberFormatException e)
            {
                throw new ConfigurationException("Token " + token + " contains non-hex digits");
            }
        }

        public Token fromString(String string)
        {
            if (string.length() % 2 == 1)
                string = "0" + string;
            return new BytesToken(Hex.hexToBytes(string));
        }
    };

    public Token.TokenFactory getTokenFactory()
    {
        return tokenFactory;
    }

    public boolean preservesOrder()
    {
        return true;
    }

    public Map<Token, Float> describeOwnership(List<Token> sortedTokens)
    {
        // allTokens will contain the count and be returned, sorted_ranges is shorthand for token<->token math.
        Map<Token, Float> allTokens = new HashMap<Token, Float>();
        List<Range<Token>> sortedRanges = new ArrayList<Range<Token>>(sortedTokens.size());

        // this initializes the counts to 0 and calcs the ranges in order.
        Token lastToken = sortedTokens.get(sortedTokens.size() - 1);
        for (Token node : sortedTokens)
        {
            allTokens.put(node, new Float(0.0));
            sortedRanges.add(new Range<Token>(lastToken, node));
            lastToken = node;
        }

        for (String ks : Schema.instance.getKeyspaces())
        {
            for (CFMetaData cfmd : Schema.instance.getKSMetaData(ks).cfMetaData().values())
            {
                for (Range<Token> r : sortedRanges)
                {
                    // Looping over every KS:CF:Range, get the splits size and add it to the count
                    allTokens.put(r.right, allTokens.get(r.right) + StorageService.instance.getSplits(ks, cfmd.cfName, r, 1).size());
                }
            }
        }

        // Sum every count up and divide count/total for the fractional ownership.
        Float total = new Float(0.0);
        for (Float f : allTokens.values())
            total += f;
        for (Map.Entry<Token, Float> row : allTokens.entrySet())
            allTokens.put(row.getKey(), row.getValue() / total);

        return allTokens;
    }

    public AbstractType<?> getTokenValidator()
    {
        return BytesType.instance;
    }
}


File: src/java/org/apache/cassandra/dht/ComparableObjectToken.java
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
package org.apache.cassandra.dht;

abstract class ComparableObjectToken<C extends Comparable<C>> extends Token
{
    private static final long serialVersionUID = 1L;

    final C token;   // Package-private to allow access from subtypes, which should all reside in the dht package.

    protected ComparableObjectToken(C token)
    {
        this.token = token;
    }

    @Override
    public C getTokenValue()
    {
        return token;
    }

    @Override
    public String toString()
    {
        return token.toString();
    }

    @Override
    public boolean equals(Object obj)
    {
        if (this == obj)
            return true;
        if (obj == null || this.getClass() != obj.getClass())
            return false;

        return token.equals(((ComparableObjectToken<?>)obj).token);
    }

    @Override
    public int hashCode()
    {
        return token.hashCode();
    }

    @Override
    @SuppressWarnings("unchecked")
    public int compareTo(Token o)
    {
        if (o.getClass() != getClass())
            throw new IllegalArgumentException("Invalid type of Token.compareTo() argument.");

        return token.compareTo(((ComparableObjectToken<C>) o).token);
    }
}


File: src/java/org/apache/cassandra/dht/Murmur3Partitioner.java
/**
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
package org.apache.cassandra.dht;

import java.math.BigDecimal;
import java.math.BigInteger;
import java.nio.ByteBuffer;
import java.util.HashMap;
import java.util.Iterator;
import java.util.List;
import java.util.Map;
import java.util.concurrent.ThreadLocalRandom;

import org.apache.cassandra.db.DecoratedKey;
import org.apache.cassandra.db.PreHashedDecoratedKey;
import org.apache.cassandra.db.marshal.AbstractType;
import org.apache.cassandra.db.marshal.LongType;
import org.apache.cassandra.exceptions.ConfigurationException;
import org.apache.cassandra.utils.ByteBufferUtil;
import org.apache.cassandra.utils.MurmurHash;
import org.apache.cassandra.utils.ObjectSizes;

import com.google.common.primitives.Longs;

/**
 * This class generates a BigIntegerToken using a Murmur3 hash.
 */
public class Murmur3Partitioner implements IPartitioner
{
    public static final LongToken MINIMUM = new LongToken(Long.MIN_VALUE);
    public static final long MAXIMUM = Long.MAX_VALUE;

    private static final int HEAP_SIZE = (int) ObjectSizes.measureDeep(MINIMUM);

    public static final Murmur3Partitioner instance = new Murmur3Partitioner();

    public DecoratedKey decorateKey(ByteBuffer key)
    {
        long[] hash = getHash(key);
        return new PreHashedDecoratedKey(getToken(key, hash), key, hash[0], hash[1]);
    }

    public Token midpoint(Token lToken, Token rToken)
    {
        // using BigInteger to avoid long overflow in intermediate operations
        BigInteger l = BigInteger.valueOf(((LongToken) lToken).token),
                   r = BigInteger.valueOf(((LongToken) rToken).token),
                   midpoint;

        if (l.compareTo(r) < 0)
        {
            BigInteger sum = l.add(r);
            midpoint = sum.shiftRight(1);
        }
        else // wrapping case
        {
            BigInteger max = BigInteger.valueOf(MAXIMUM);
            BigInteger min = BigInteger.valueOf(MINIMUM.token);
            // length of range we're bisecting is (R - min) + (max - L)
            // so we add that to L giving
            // L + ((R - min) + (max - L) / 2) = (L + R + max - min) / 2
            midpoint = (max.subtract(min).add(l).add(r)).shiftRight(1);
            if (midpoint.compareTo(max) > 0)
                midpoint = min.add(midpoint.subtract(max));
        }

        return new LongToken(midpoint.longValue());
    }

    public LongToken getMinimumToken()
    {
        return MINIMUM;
    }

    public static class LongToken extends Token
    {
        static final long serialVersionUID = -5833580143318243006L;

        final long token;

        public LongToken(long token)
        {
            this.token = token;
        }

        public String toString()
        {
            return Long.toString(token);
        }

        public boolean equals(Object obj)
        {
            if (this == obj)
                return true;
            if (obj == null || this.getClass() != obj.getClass())
                return false;

            return token == (((LongToken)obj).token);
        }

        public int hashCode()
        {
            return Longs.hashCode(token);
        }

        public int compareTo(Token o)
        {
            return Long.compare(token, ((LongToken) o).token);
        }

        @Override
        public IPartitioner getPartitioner()
        {
            return instance;
        }

        @Override
        public long getHeapSize()
        {
            return HEAP_SIZE;
        }

        @Override
        public Object getTokenValue()
        {
            return token;
        }
    }

    /**
     * Generate the token of a key.
     * Note that we need to ensure all generated token are strictly bigger than MINIMUM.
     * In particular we don't want MINIMUM to correspond to any key because the range (MINIMUM, X] doesn't
     * include MINIMUM but we use such range to select all data whose token is smaller than X.
     */
    public LongToken getToken(ByteBuffer key)
    {
        return getToken(key, getHash(key));
    }

    private LongToken getToken(ByteBuffer key, long[] hash)
    {
        if (key.remaining() == 0)
            return MINIMUM;

        return new LongToken(normalize(hash[0]));
    }

    private long[] getHash(ByteBuffer key)
    {
        long[] hash = new long[2];
        MurmurHash.hash3_x64_128(key, key.position(), key.remaining(), 0, hash);
        return hash;
    }

    public LongToken getRandomToken()
    {
        return new LongToken(normalize(ThreadLocalRandom.current().nextLong()));
    }

    private long normalize(long v)
    {
        // We exclude the MINIMUM value; see getToken()
        return v == Long.MIN_VALUE ? Long.MAX_VALUE : v;
    }

    public boolean preservesOrder()
    {
        return false;
    }

    public Map<Token, Float> describeOwnership(List<Token> sortedTokens)
    {
        Map<Token, Float> ownerships = new HashMap<Token, Float>();
        Iterator<Token> i = sortedTokens.iterator();

        // 0-case
        if (!i.hasNext())
            throw new RuntimeException("No nodes present in the cluster. Has this node finished starting up?");
        // 1-case
        if (sortedTokens.size() == 1)
            ownerships.put(i.next(), new Float(1.0));
        // n-case
        else
        {
            final BigInteger ri = BigInteger.valueOf(MAXIMUM).subtract(BigInteger.valueOf(MINIMUM.token + 1));  //  (used for addition later)
            final BigDecimal r  = new BigDecimal(ri);
            Token start = i.next();BigInteger ti = BigInteger.valueOf(((LongToken)start).token);  // The first token and its value
            Token t; BigInteger tim1 = ti;                                                                // The last token and its value (after loop)

            while (i.hasNext())
            {
                t = i.next(); ti = BigInteger.valueOf(((LongToken) t).token); // The next token and its value
                float age = new BigDecimal(ti.subtract(tim1).add(ri).mod(ri)).divide(r, 6, BigDecimal.ROUND_HALF_EVEN).floatValue(); // %age = ((T(i) - T(i-1) + R) % R) / R
                ownerships.put(t, age);                           // save (T(i) -> %age)
                tim1 = ti;                                        // -> advance loop
            }

            // The start token's range extends backward to the last token, which is why both were saved above.
            float x = new BigDecimal(BigInteger.valueOf(((LongToken)start).token).subtract(ti).add(ri).mod(ri)).divide(r, 6, BigDecimal.ROUND_HALF_EVEN).floatValue();
            ownerships.put(start, x);
        }

        return ownerships;
    }

    public Token.TokenFactory getTokenFactory()
    {
        return tokenFactory;
    }

    private final Token.TokenFactory tokenFactory = new Token.TokenFactory()
    {
        public ByteBuffer toByteArray(Token token)
        {
            LongToken longToken = (LongToken) token;
            return ByteBufferUtil.bytes(longToken.token);
        }

        public Token fromByteArray(ByteBuffer bytes)
        {
            return new LongToken(ByteBufferUtil.toLong(bytes));
        }

        public String toString(Token token)
        {
            return token.toString();
        }

        public void validate(String token) throws ConfigurationException
        {
            try
            {
                Long.valueOf(token);
            }
            catch (NumberFormatException e)
            {
                throw new ConfigurationException(e.getMessage());
            }
        }

        public Token fromString(String string)
        {
            try
            {
                return new LongToken(Long.parseLong(string));
            }
            catch (NumberFormatException e)
            {
                throw new IllegalArgumentException(String.format("Invalid token for Murmur3Partitioner. Got %s but expected a long value (unsigned 8 bytes integer).", string));
            }
        }
    };

    public AbstractType<?> getTokenValidator()
    {
        return LongType.instance;
    }
}


File: src/java/org/apache/cassandra/dht/Token.java
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
package org.apache.cassandra.dht;

import java.io.DataInput;
import java.io.IOException;
import java.io.Serializable;
import java.nio.ByteBuffer;

import org.apache.cassandra.db.RowPosition;
import org.apache.cassandra.db.TypeSizes;
import org.apache.cassandra.exceptions.ConfigurationException;
import org.apache.cassandra.io.util.DataOutputPlus;
import org.apache.cassandra.utils.ByteBufferUtil;

public abstract class Token implements RingPosition<Token>, Serializable
{
    private static final long serialVersionUID = 1L;

    public static final TokenSerializer serializer = new TokenSerializer();

    public static abstract class TokenFactory
    {
        public abstract ByteBuffer toByteArray(Token token);
        public abstract Token fromByteArray(ByteBuffer bytes);
        public abstract String toString(Token token); // serialize as string, not necessarily human-readable
        public abstract Token fromString(String string); // deserialize

        public abstract void validate(String token) throws ConfigurationException;
    }

    public static class TokenSerializer implements IPartitionerDependentSerializer<Token>
    {
        public void serialize(Token token, DataOutputPlus out, int version) throws IOException
        {
            IPartitioner p = token.getPartitioner();
            ByteBuffer b = p.getTokenFactory().toByteArray(token);
            ByteBufferUtil.writeWithLength(b, out);
        }

        public Token deserialize(DataInput in, IPartitioner p, int version) throws IOException
        {
            int size = in.readInt();
            byte[] bytes = new byte[size];
            in.readFully(bytes);
            return p.getTokenFactory().fromByteArray(ByteBuffer.wrap(bytes));
        }

        public long serializedSize(Token object, int version)
        {
            IPartitioner p = object.getPartitioner();
            ByteBuffer b = p.getTokenFactory().toByteArray(object);
            return TypeSizes.NATIVE.sizeof(b.remaining()) + b.remaining();
        }
    }

    abstract public IPartitioner getPartitioner();
    abstract public long getHeapSize();
    abstract public Object getTokenValue();

    public Token getToken()
    {
        return this;
    }

    public Token minValue()
    {
        return getPartitioner().getMinimumToken();
    }

    public boolean isMinimum()
    {
        return this.equals(minValue());
    }

    /*
     * A token corresponds to the range of all the keys having this token.
     * A token is thus no comparable directly to a key. But to be able to select
     * keys given tokens, we introduce two "fake" keys for each token T:
     *   - lowerBoundKey: a "fake" key representing the lower bound T represents.
     *                    In other words, lowerBoundKey is the smallest key that
     *                    have token T.
     *   - upperBoundKey: a "fake" key representing the upper bound T represents.
     *                    In other words, upperBoundKey is the largest key that
     *                    have token T.
     *
     * Note that those are "fake" keys and should only be used for comparison
     * of other keys, for selection of keys when only a token is known.
     */
    public KeyBound minKeyBound()
    {
        return new KeyBound(this, true);
    }

    public KeyBound maxKeyBound()
    {
        /*
         * For each token, we needs both minKeyBound and maxKeyBound
         * because a token corresponds to a range of keys. But the minimun
         * token corresponds to no key, so it is valid and actually much
         * simpler to associate the same value for minKeyBound and
         * maxKeyBound for the minimun token.
         */
        if (isMinimum())
            return minKeyBound();
        return new KeyBound(this, false);
    }

    @SuppressWarnings("unchecked")
    public <R extends RingPosition<R>> R upperBound(Class<R> klass)
    {
        if (klass.equals(getClass()))
            return (R)this;
        else
            return (R)maxKeyBound();
    }

    public static class KeyBound implements RowPosition
    {
        private final Token token;
        public final boolean isMinimumBound;

        private KeyBound(Token t, boolean isMinimumBound)
        {
            this.token = t;
            this.isMinimumBound = isMinimumBound;
        }

        public Token getToken()
        {
            return token;
        }

        public int compareTo(RowPosition pos)
        {
            if (this == pos)
                return 0;

            int cmp = getToken().compareTo(pos.getToken());
            if (cmp != 0)
                return cmp;

            if (isMinimumBound)
                return ((pos instanceof KeyBound) && ((KeyBound)pos).isMinimumBound) ? 0 : -1;
            else
                return ((pos instanceof KeyBound) && !((KeyBound)pos).isMinimumBound) ? 0 : 1;
        }

        public IPartitioner getPartitioner()
        {
            return getToken().getPartitioner();
        }

        public KeyBound minValue()
        {
            return getPartitioner().getMinimumToken().minKeyBound();
        }

        public boolean isMinimum()
        {
            return getToken().isMinimum();
        }

        public RowPosition.Kind kind()
        {
            return isMinimumBound ? RowPosition.Kind.MIN_BOUND : RowPosition.Kind.MAX_BOUND;
        }

        @Override
        public boolean equals(Object obj)
        {
            if (this == obj)
                return true;
            if (obj == null || this.getClass() != obj.getClass())
                return false;

            KeyBound other = (KeyBound)obj;
            return token.equals(other.token) && isMinimumBound == other.isMinimumBound;
        }

        @Override
        public int hashCode()
        {
            return getToken().hashCode() + (isMinimumBound ? 0 : 1);
        }

        @Override
        public String toString()
        {
            return String.format("%s(%s)", isMinimumBound ? "min" : "max", getToken().toString());
        }
    }
}


File: src/java/org/apache/cassandra/locator/TokenMetadata.java
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
package org.apache.cassandra.locator;

import java.net.InetAddress;
import java.nio.ByteBuffer;
import java.util.*;
import java.util.concurrent.ConcurrentHashMap;
import java.util.concurrent.ConcurrentMap;
import java.util.concurrent.atomic.AtomicReference;
import java.util.concurrent.locks.ReadWriteLock;
import java.util.concurrent.locks.ReentrantReadWriteLock;

import com.google.common.collect.*;
import org.apache.commons.lang3.StringUtils;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import org.apache.cassandra.config.DatabaseDescriptor;
import org.apache.cassandra.dht.Range;
import org.apache.cassandra.dht.Token;
import org.apache.cassandra.gms.FailureDetector;
import org.apache.cassandra.service.StorageService;
import org.apache.cassandra.utils.BiMultiValMap;
import org.apache.cassandra.utils.Pair;
import org.apache.cassandra.utils.SortedBiMultiValMap;

public class TokenMetadata
{
    private static final Logger logger = LoggerFactory.getLogger(TokenMetadata.class);

    /**
     * Maintains token to endpoint map of every node in the cluster.
     * Each Token is associated with exactly one Address, but each Address may have
     * multiple tokens.  Hence, the BiMultiValMap collection.
     */
    private final BiMultiValMap<Token, InetAddress> tokenToEndpointMap;

    /** Maintains endpoint to host ID map of every node in the cluster */
    private final BiMap<InetAddress, UUID> endpointToHostIdMap;

    // Prior to CASSANDRA-603, we just had <tt>Map<Range, InetAddress> pendingRanges<tt>,
    // which was added to when a node began bootstrap and removed from when it finished.
    //
    // This is inadequate when multiple changes are allowed simultaneously.  For example,
    // suppose that there is a ring of nodes A, C and E, with replication factor 3.
    // Node D bootstraps between C and E, so its pending ranges will be E-A, A-C and C-D.
    // Now suppose node B bootstraps between A and C at the same time. Its pending ranges
    // would be C-E, E-A and A-B. Now both nodes need to be assigned pending range E-A,
    // which we would be unable to represent with the old Map.  The same thing happens
    // even more obviously for any nodes that boot simultaneously between same two nodes.
    //
    // So, we made two changes:
    //
    // First, we changed pendingRanges to a <tt>Multimap<Range, InetAddress></tt> (now
    // <tt>Map<String, Multimap<Range, InetAddress>></tt>, because replication strategy
    // and options are per-KeySpace).
    //
    // Second, we added the bootstrapTokens and leavingEndpoints collections, so we can
    // rebuild pendingRanges from the complete information of what is going on, when
    // additional changes are made mid-operation.
    //
    // Finally, note that recording the tokens of joining nodes in bootstrapTokens also
    // means we can detect and reject the addition of multiple nodes at the same token
    // before one becomes part of the ring.
    private final BiMultiValMap<Token, InetAddress> bootstrapTokens = new BiMultiValMap<Token, InetAddress>();
    // (don't need to record Token here since it's still part of tokenToEndpointMap until it's done leaving)
    private final Set<InetAddress> leavingEndpoints = new HashSet<InetAddress>();
    // this is a cache of the calculation from {tokenToEndpointMap, bootstrapTokens, leavingEndpoints}
    private final ConcurrentMap<String, Multimap<Range<Token>, InetAddress>> pendingRanges = new ConcurrentHashMap<String, Multimap<Range<Token>, InetAddress>>();

    // nodes which are migrating to the new tokens in the ring
    private final Set<Pair<Token, InetAddress>> movingEndpoints = new HashSet<Pair<Token, InetAddress>>();

    /* Use this lock for manipulating the token map */
    private final ReadWriteLock lock = new ReentrantReadWriteLock(true);
    private volatile ArrayList<Token> sortedTokens;

    private final Topology topology;

    private static final Comparator<InetAddress> inetaddressCmp = new Comparator<InetAddress>()
    {
        public int compare(InetAddress o1, InetAddress o2)
        {
            return ByteBuffer.wrap(o1.getAddress()).compareTo(ByteBuffer.wrap(o2.getAddress()));
        }
    };

    // signals replication strategies that nodes have joined or left the ring and they need to recompute ownership
    private volatile long ringVersion = 0;

    public TokenMetadata()
    {
        this(SortedBiMultiValMap.<Token, InetAddress>create(null, inetaddressCmp),
             HashBiMap.<InetAddress, UUID>create(),
             new Topology());
    }

    private TokenMetadata(BiMultiValMap<Token, InetAddress> tokenToEndpointMap, BiMap<InetAddress, UUID> endpointsMap, Topology topology)
    {
        this.tokenToEndpointMap = tokenToEndpointMap;
        this.topology = topology;
        endpointToHostIdMap = endpointsMap;
        sortedTokens = sortTokens();
    }

    private ArrayList<Token> sortTokens()
    {
        return new ArrayList<Token>(tokenToEndpointMap.keySet());
    }

    /** @return the number of nodes bootstrapping into source's primary range */
    public int pendingRangeChanges(InetAddress source)
    {
        int n = 0;
        Collection<Range<Token>> sourceRanges = getPrimaryRangesFor(getTokens(source));
        lock.readLock().lock();
        try
        {
            for (Token token : bootstrapTokens.keySet())
                for (Range<Token> range : sourceRanges)
                    if (range.contains(token))
                        n++;
        }
        finally
        {
            lock.readLock().unlock();
        }
        return n;
    }

    /**
     * Update token map with a single token/endpoint pair in normal state.
     */
    public void updateNormalToken(Token token, InetAddress endpoint)
    {
        updateNormalTokens(Collections.singleton(token), endpoint);
    }

    public void updateNormalTokens(Collection<Token> tokens, InetAddress endpoint)
    {
        Multimap<InetAddress, Token> endpointTokens = HashMultimap.create();
        for (Token token : tokens)
            endpointTokens.put(endpoint, token);
        updateNormalTokens(endpointTokens);
    }

    /**
     * Update token map with a set of token/endpoint pairs in normal state.
     *
     * Prefer this whenever there are multiple pairs to update, as each update (whether a single or multiple)
     * is expensive (CASSANDRA-3831).
     *
     * @param endpointTokens
     */
    public void updateNormalTokens(Multimap<InetAddress, Token> endpointTokens)
    {
        if (endpointTokens.isEmpty())
            return;

        lock.writeLock().lock();
        try
        {
            boolean shouldSortTokens = false;
            for (InetAddress endpoint : endpointTokens.keySet())
            {
                Collection<Token> tokens = endpointTokens.get(endpoint);

                assert tokens != null && !tokens.isEmpty();

                bootstrapTokens.removeValue(endpoint);
                tokenToEndpointMap.removeValue(endpoint);
                topology.addEndpoint(endpoint);
                leavingEndpoints.remove(endpoint);
                removeFromMoving(endpoint); // also removing this endpoint from moving

                for (Token token : tokens)
                {
                    InetAddress prev = tokenToEndpointMap.put(token, endpoint);
                    if (!endpoint.equals(prev))
                    {
                        if (prev != null)
                            logger.warn("Token {} changing ownership from {} to {}", token, prev, endpoint);
                        shouldSortTokens = true;
                    }
                }
            }

            if (shouldSortTokens)
                sortedTokens = sortTokens();
        }
        finally
        {
            lock.writeLock().unlock();
        }
    }

    /**
     * Store an end-point to host ID mapping.  Each ID must be unique, and
     * cannot be changed after the fact.
     *
     * @param hostId
     * @param endpoint
     */
    public void updateHostId(UUID hostId, InetAddress endpoint)
    {
        assert hostId != null;
        assert endpoint != null;

        lock.writeLock().lock();
        try
        {
            InetAddress storedEp = endpointToHostIdMap.inverse().get(hostId);
            if (storedEp != null)
            {
                if (!storedEp.equals(endpoint) && (FailureDetector.instance.isAlive(storedEp)))
                {
                    throw new RuntimeException(String.format("Host ID collision between active endpoint %s and %s (id=%s)",
                                                             storedEp,
                                                             endpoint,
                                                             hostId));
                }
            }

            UUID storedId = endpointToHostIdMap.get(endpoint);
            if ((storedId != null) && (!storedId.equals(hostId)))
                logger.warn("Changing {}'s host ID from {} to {}", endpoint, storedId, hostId);
    
            endpointToHostIdMap.forcePut(endpoint, hostId);
        }
        finally
        {
            lock.writeLock().unlock();
        }

    }

    /** Return the unique host ID for an end-point. */
    public UUID getHostId(InetAddress endpoint)
    {
        lock.readLock().lock();
        try
        {
            return endpointToHostIdMap.get(endpoint);
        }
        finally
        {
            lock.readLock().unlock();
        }
    }

    /** Return the end-point for a unique host ID */
    public InetAddress getEndpointForHostId(UUID hostId)
    {
        lock.readLock().lock();
        try
        {
            return endpointToHostIdMap.inverse().get(hostId);
        }
        finally
        {
            lock.readLock().unlock();
        }
    }

    /** @return a copy of the endpoint-to-id map for read-only operations */
    public Map<InetAddress, UUID> getEndpointToHostIdMapForReading()
    {
        lock.readLock().lock();
        try
        {
            Map<InetAddress, UUID> readMap = new HashMap<InetAddress, UUID>();
            readMap.putAll(endpointToHostIdMap);
            return readMap;
        }
        finally
        {
            lock.readLock().unlock();
        }
    }

    @Deprecated
    public void addBootstrapToken(Token token, InetAddress endpoint)
    {
        addBootstrapTokens(Collections.singleton(token), endpoint);
    }

    public void addBootstrapTokens(Collection<Token> tokens, InetAddress endpoint)
    {
        assert tokens != null && !tokens.isEmpty();
        assert endpoint != null;

        lock.writeLock().lock();
        try
        {

            InetAddress oldEndpoint;

            for (Token token : tokens)
            {
                oldEndpoint = bootstrapTokens.get(token);
                if (oldEndpoint != null && !oldEndpoint.equals(endpoint))
                    throw new RuntimeException("Bootstrap Token collision between " + oldEndpoint + " and " + endpoint + " (token " + token);

                oldEndpoint = tokenToEndpointMap.get(token);
                if (oldEndpoint != null && !oldEndpoint.equals(endpoint))
                    throw new RuntimeException("Bootstrap Token collision between " + oldEndpoint + " and " + endpoint + " (token " + token);
            }

            bootstrapTokens.removeValue(endpoint);

            for (Token token : tokens)
                bootstrapTokens.put(token, endpoint);
        }
        finally
        {
            lock.writeLock().unlock();
        }
    }

    public void removeBootstrapTokens(Collection<Token> tokens)
    {
        assert tokens != null && !tokens.isEmpty();

        lock.writeLock().lock();
        try
        {
            for (Token token : tokens)
                bootstrapTokens.remove(token);
        }
        finally
        {
            lock.writeLock().unlock();
        }
    }

    public void addLeavingEndpoint(InetAddress endpoint)
    {
        assert endpoint != null;

        lock.writeLock().lock();
        try
        {
            leavingEndpoints.add(endpoint);
        }
        finally
        {
            lock.writeLock().unlock();
        }
    }

    /**
     * Add a new moving endpoint
     * @param token token which is node moving to
     * @param endpoint address of the moving node
     */
    public void addMovingEndpoint(Token token, InetAddress endpoint)
    {
        assert endpoint != null;

        lock.writeLock().lock();

        try
        {
            movingEndpoints.add(Pair.create(token, endpoint));
        }
        finally
        {
            lock.writeLock().unlock();
        }
    }

    public void removeEndpoint(InetAddress endpoint)
    {
        assert endpoint != null;

        lock.writeLock().lock();
        try
        {
            bootstrapTokens.removeValue(endpoint);
            tokenToEndpointMap.removeValue(endpoint);
            topology.removeEndpoint(endpoint);
            leavingEndpoints.remove(endpoint);
            endpointToHostIdMap.remove(endpoint);
            sortedTokens = sortTokens();
            invalidateCachedRings();
        }
        finally
        {
            lock.writeLock().unlock();
        }
    }

    /**
     * Remove pair of token/address from moving endpoints
     * @param endpoint address of the moving node
     */
    public void removeFromMoving(InetAddress endpoint)
    {
        assert endpoint != null;

        lock.writeLock().lock();
        try
        {
            for (Pair<Token, InetAddress> pair : movingEndpoints)
            {
                if (pair.right.equals(endpoint))
                {
                    movingEndpoints.remove(pair);
                    break;
                }
            }

            invalidateCachedRings();
        }
        finally
        {
            lock.writeLock().unlock();
        }
    }

    public Collection<Token> getTokens(InetAddress endpoint)
    {
        assert endpoint != null;
        assert isMember(endpoint); // don't want to return nulls

        lock.readLock().lock();
        try
        {
            return new ArrayList<Token>(tokenToEndpointMap.inverse().get(endpoint));
        }
        finally
        {
            lock.readLock().unlock();
        }
    }

    @Deprecated
    public Token getToken(InetAddress endpoint)
    {
        return getTokens(endpoint).iterator().next();
    }

    public boolean isMember(InetAddress endpoint)
    {
        assert endpoint != null;

        lock.readLock().lock();
        try
        {
            return tokenToEndpointMap.inverse().containsKey(endpoint);
        }
        finally
        {
            lock.readLock().unlock();
        }
    }

    public boolean isLeaving(InetAddress endpoint)
    {
        assert endpoint != null;

        lock.readLock().lock();
        try
        {
            return leavingEndpoints.contains(endpoint);
        }
        finally
        {
            lock.readLock().unlock();
        }
    }

    public boolean isMoving(InetAddress endpoint)
    {
        assert endpoint != null;

        lock.readLock().lock();

        try
        {
            for (Pair<Token, InetAddress> pair : movingEndpoints)
            {
                if (pair.right.equals(endpoint))
                    return true;
            }

            return false;
        }
        finally
        {
            lock.readLock().unlock();
        }
    }

    private final AtomicReference<TokenMetadata> cachedTokenMap = new AtomicReference<TokenMetadata>();

    /**
     * Create a copy of TokenMetadata with only tokenToEndpointMap. That is, pending ranges,
     * bootstrap tokens and leaving endpoints are not included in the copy.
     */
    public TokenMetadata cloneOnlyTokenMap()
    {
        lock.readLock().lock();
        try
        {
            return new TokenMetadata(SortedBiMultiValMap.<Token, InetAddress>create(tokenToEndpointMap, null, inetaddressCmp),
                                     HashBiMap.create(endpointToHostIdMap),
                                     new Topology(topology));
        }
        finally
        {
            lock.readLock().unlock();
        }
    }

    /**
     * Return a cached TokenMetadata with only tokenToEndpointMap, i.e., the same as cloneOnlyTokenMap but
     * uses a cached copy that is invalided when the ring changes, so in the common case
     * no extra locking is required.
     *
     * Callers must *NOT* mutate the returned metadata object.
     */
    public TokenMetadata cachedOnlyTokenMap()
    {
        TokenMetadata tm = cachedTokenMap.get();
        if (tm != null)
            return tm;

        // synchronize to prevent thundering herd (CASSANDRA-6345)
        synchronized (this)
        {
            if ((tm = cachedTokenMap.get()) != null)
                return tm;

            tm = cloneOnlyTokenMap();
            cachedTokenMap.set(tm);
            return tm;
        }
    }

    /**
     * Create a copy of TokenMetadata with tokenToEndpointMap reflecting situation after all
     * current leave operations have finished.
     *
     * @return new token metadata
     */
    public TokenMetadata cloneAfterAllLeft()
    {
        lock.readLock().lock();
        try
        {
            TokenMetadata allLeftMetadata = cloneOnlyTokenMap();

            for (InetAddress endpoint : leavingEndpoints)
                allLeftMetadata.removeEndpoint(endpoint);

            return allLeftMetadata;
        }
        finally
        {
            lock.readLock().unlock();
        }
    }

    /**
     * Create a copy of TokenMetadata with tokenToEndpointMap reflecting situation after all
     * current leave, and move operations have finished.
     *
     * @return new token metadata
     */
    public TokenMetadata cloneAfterAllSettled()
    {
        lock.readLock().lock();

        try
        {
            TokenMetadata metadata = cloneOnlyTokenMap();

            for (InetAddress endpoint : leavingEndpoints)
                metadata.removeEndpoint(endpoint);


            for (Pair<Token, InetAddress> pair : movingEndpoints)
                metadata.updateNormalToken(pair.left, pair.right);

            return metadata;
        }
        finally
        {
            lock.readLock().unlock();
        }
    }

    public InetAddress getEndpoint(Token token)
    {
        lock.readLock().lock();
        try
        {
            return tokenToEndpointMap.get(token);
        }
        finally
        {
            lock.readLock().unlock();
        }
    }

    public Collection<Range<Token>> getPrimaryRangesFor(Collection<Token> tokens)
    {
        Collection<Range<Token>> ranges = new ArrayList<Range<Token>>(tokens.size());
        for (Token right : tokens)
            ranges.add(new Range<Token>(getPredecessor(right), right));
        return ranges;
    }

    @Deprecated
    public Range<Token> getPrimaryRangeFor(Token right)
    {
        return getPrimaryRangesFor(Arrays.asList(right)).iterator().next();
    }

    public ArrayList<Token> sortedTokens()
    {
        return sortedTokens;
    }

    private Multimap<Range<Token>, InetAddress> getPendingRangesMM(String keyspaceName)
    {
        Multimap<Range<Token>, InetAddress> map = pendingRanges.get(keyspaceName);
        if (map == null)
        {
            map = HashMultimap.create();
            Multimap<Range<Token>, InetAddress> priorMap = pendingRanges.putIfAbsent(keyspaceName, map);
            if (priorMap != null)
                map = priorMap;
        }
        return map;
    }

    /** a mutable map may be returned but caller should not modify it */
    public Map<Range<Token>, Collection<InetAddress>> getPendingRanges(String keyspaceName)
    {
        return getPendingRangesMM(keyspaceName).asMap();
    }

    public List<Range<Token>> getPendingRanges(String keyspaceName, InetAddress endpoint)
    {
        List<Range<Token>> ranges = new ArrayList<Range<Token>>();
        for (Map.Entry<Range<Token>, InetAddress> entry : getPendingRangesMM(keyspaceName).entries())
        {
            if (entry.getValue().equals(endpoint))
            {
                ranges.add(entry.getKey());
            }
        }
        return ranges;
    }

     /**
     * Calculate pending ranges according to bootsrapping and leaving nodes. Reasoning is:
     *
     * (1) When in doubt, it is better to write too much to a node than too little. That is, if
     * there are multiple nodes moving, calculate the biggest ranges a node could have. Cleaning
     * up unneeded data afterwards is better than missing writes during movement.
     * (2) When a node leaves, ranges for other nodes can only grow (a node might get additional
     * ranges, but it will not lose any of its current ranges as a result of a leave). Therefore
     * we will first remove _all_ leaving tokens for the sake of calculation and then check what
     * ranges would go where if all nodes are to leave. This way we get the biggest possible
     * ranges with regard current leave operations, covering all subsets of possible final range
     * values.
     * (3) When a node bootstraps, ranges of other nodes can only get smaller. Without doing
     * complex calculations to see if multiple bootstraps overlap, we simply base calculations
     * on the same token ring used before (reflecting situation after all leave operations have
     * completed). Bootstrapping nodes will be added and removed one by one to that metadata and
     * checked what their ranges would be. This will give us the biggest possible ranges the
     * node could have. It might be that other bootstraps make our actual final ranges smaller,
     * but it does not matter as we can clean up the data afterwards.
     *
     * NOTE: This is heavy and ineffective operation. This will be done only once when a node
     * changes state in the cluster, so it should be manageable.
     */
    public void calculatePendingRanges(AbstractReplicationStrategy strategy, String keyspaceName)
    {
        lock.readLock().lock();
        try
        {
            Multimap<Range<Token>, InetAddress> newPendingRanges = HashMultimap.create();

            if (bootstrapTokens.isEmpty() && leavingEndpoints.isEmpty() && movingEndpoints.isEmpty())
            {
                if (logger.isDebugEnabled())
                    logger.debug("No bootstrapping, leaving or moving nodes -> empty pending ranges for {}", keyspaceName);

                pendingRanges.put(keyspaceName, newPendingRanges);
                return;
            }

            Multimap<InetAddress, Range<Token>> addressRanges = strategy.getAddressRanges();

            // Copy of metadata reflecting the situation after all leave operations are finished.
            TokenMetadata allLeftMetadata = cloneAfterAllLeft();

            // get all ranges that will be affected by leaving nodes
            Set<Range<Token>> affectedRanges = new HashSet<Range<Token>>();
            for (InetAddress endpoint : leavingEndpoints)
                affectedRanges.addAll(addressRanges.get(endpoint));

            // for each of those ranges, find what new nodes will be responsible for the range when
            // all leaving nodes are gone.
            TokenMetadata metadata = cloneOnlyTokenMap(); // don't do this in the loop! #7758
            for (Range<Token> range : affectedRanges)
            {
                Set<InetAddress> currentEndpoints = ImmutableSet.copyOf(strategy.calculateNaturalEndpoints(range.right, metadata));
                Set<InetAddress> newEndpoints = ImmutableSet.copyOf(strategy.calculateNaturalEndpoints(range.right, allLeftMetadata));
                newPendingRanges.putAll(range, Sets.difference(newEndpoints, currentEndpoints));
            }

            // At this stage newPendingRanges has been updated according to leave operations. We can
            // now continue the calculation by checking bootstrapping nodes.

            // For each of the bootstrapping nodes, simply add and remove them one by one to
            // allLeftMetadata and check in between what their ranges would be.
            Multimap<InetAddress, Token> bootstrapAddresses = bootstrapTokens.inverse();
            for (InetAddress endpoint : bootstrapAddresses.keySet())
            {
                Collection<Token> tokens = bootstrapAddresses.get(endpoint);

                allLeftMetadata.updateNormalTokens(tokens, endpoint);
                for (Range<Token> range : strategy.getAddressRanges(allLeftMetadata).get(endpoint))
                    newPendingRanges.put(range, endpoint);
                allLeftMetadata.removeEndpoint(endpoint);
            }

            // At this stage newPendingRanges has been updated according to leaving and bootstrapping nodes.
            // We can now finish the calculation by checking moving nodes.

            // For each of the moving nodes, we do the same thing we did for bootstrapping:
            // simply add and remove them one by one to allLeftMetadata and check in between what their ranges would be.
            for (Pair<Token, InetAddress> moving : movingEndpoints)
            {
                InetAddress endpoint = moving.right; // address of the moving node

                //  moving.left is a new token of the endpoint
                allLeftMetadata.updateNormalToken(moving.left, endpoint);

                for (Range<Token> range : strategy.getAddressRanges(allLeftMetadata).get(endpoint))
                {
                    newPendingRanges.put(range, endpoint);
                }

                allLeftMetadata.removeEndpoint(endpoint);
            }

            pendingRanges.put(keyspaceName, newPendingRanges);

            if (logger.isDebugEnabled())
                logger.debug("Pending ranges:\n{}", (pendingRanges.isEmpty() ? "<empty>" : printPendingRanges()));
        }
        finally
        {
            lock.readLock().unlock();
        }
    }

    public Token getPredecessor(Token token)
    {
        List tokens = sortedTokens();
        int index = Collections.binarySearch(tokens, token);
        assert index >= 0 : token + " not found in " + StringUtils.join(tokenToEndpointMap.keySet(), ", ");
        return (Token) (index == 0 ? tokens.get(tokens.size() - 1) : tokens.get(index - 1));
    }

    public Token getSuccessor(Token token)
    {
        List tokens = sortedTokens();
        int index = Collections.binarySearch(tokens, token);
        assert index >= 0 : token + " not found in " + StringUtils.join(tokenToEndpointMap.keySet(), ", ");
        return (Token) ((index == (tokens.size() - 1)) ? tokens.get(0) : tokens.get(index + 1));
    }

    /** @return a copy of the bootstrapping tokens map */
    public BiMultiValMap<Token, InetAddress> getBootstrapTokens()
    {
        lock.readLock().lock();
        try
        {
            return new BiMultiValMap<Token, InetAddress>(bootstrapTokens);
        }
        finally
        {
            lock.readLock().unlock();
        }
    }

    public Set<InetAddress> getAllEndpoints()
    {
        lock.readLock().lock();
        try
        {
            return ImmutableSet.copyOf(endpointToHostIdMap.keySet());
        }
        finally
        {
            lock.readLock().unlock();
        }
    }

    /** caller should not modify leavingEndpoints */
    public Set<InetAddress> getLeavingEndpoints()
    {
        lock.readLock().lock();
        try
        {
            return ImmutableSet.copyOf(leavingEndpoints);
        }
        finally
        {
            lock.readLock().unlock();
        }
    }

    /**
     * Endpoints which are migrating to the new tokens
     * @return set of addresses of moving endpoints
     */
    public Set<Pair<Token, InetAddress>> getMovingEndpoints()
    {
        lock.readLock().lock();
        try
        {
            return ImmutableSet.copyOf(movingEndpoints);
        }
        finally
        {
            lock.readLock().unlock();
        }
    }

    public static int firstTokenIndex(final ArrayList ring, Token start, boolean insertMin)
    {
        assert ring.size() > 0;
        // insert the minimum token (at index == -1) if we were asked to include it and it isn't a member of the ring
        int i = Collections.binarySearch(ring, start);
        if (i < 0)
        {
            i = (i + 1) * (-1);
            if (i >= ring.size())
                i = insertMin ? -1 : 0;
        }
        return i;
    }

    public static Token firstToken(final ArrayList<Token> ring, Token start)
    {
        return ring.get(firstTokenIndex(ring, start, false));
    }

    /**
     * iterator over the Tokens in the given ring, starting with the token for the node owning start
     * (which does not have to be a Token in the ring)
     * @param includeMin True if the minimum token should be returned in the ring even if it has no owner.
     */
    public static Iterator<Token> ringIterator(final ArrayList<Token> ring, Token start, boolean includeMin)
    {
        if (ring.isEmpty())
            return includeMin ? Iterators.singletonIterator(StorageService.getPartitioner().getMinimumToken())
                              : Iterators.<Token>emptyIterator();

        final boolean insertMin = includeMin && !ring.get(0).isMinimum();
        final int startIndex = firstTokenIndex(ring, start, insertMin);
        return new AbstractIterator<Token>()
        {
            int j = startIndex;
            protected Token computeNext()
            {
                if (j < -1)
                    return endOfData();
                try
                {
                    // return minimum for index == -1
                    if (j == -1)
                        return StorageService.getPartitioner().getMinimumToken();
                    // return ring token for other indexes
                    return ring.get(j);
                }
                finally
                {
                    j++;
                    if (j == ring.size())
                        j = insertMin ? -1 : 0;
                    if (j == startIndex)
                        // end iteration
                        j = -2;
                }
            }
        };
    }

    /** used by tests */
    public void clearUnsafe()
    {
        lock.writeLock().lock();
        try
        {
            tokenToEndpointMap.clear();
            endpointToHostIdMap.clear();
            bootstrapTokens.clear();
            leavingEndpoints.clear();
            pendingRanges.clear();
            movingEndpoints.clear();
            sortedTokens.clear();
            topology.clear();
            invalidateCachedRings();
        }
        finally
        {
            lock.writeLock().unlock();
        }
    }

    public String toString()
    {
        StringBuilder sb = new StringBuilder();
        lock.readLock().lock();
        try
        {
            Set<InetAddress> eps = tokenToEndpointMap.inverse().keySet();

            if (!eps.isEmpty())
            {
                sb.append("Normal Tokens:");
                sb.append(System.getProperty("line.separator"));
                for (InetAddress ep : eps)
                {
                    sb.append(ep);
                    sb.append(":");
                    sb.append(tokenToEndpointMap.inverse().get(ep));
                    sb.append(System.getProperty("line.separator"));
                }
            }

            if (!bootstrapTokens.isEmpty())
            {
                sb.append("Bootstrapping Tokens:" );
                sb.append(System.getProperty("line.separator"));
                for (Map.Entry<Token, InetAddress> entry : bootstrapTokens.entrySet())
                {
                    sb.append(entry.getValue()).append(":").append(entry.getKey());
                    sb.append(System.getProperty("line.separator"));
                }
            }

            if (!leavingEndpoints.isEmpty())
            {
                sb.append("Leaving Endpoints:");
                sb.append(System.getProperty("line.separator"));
                for (InetAddress ep : leavingEndpoints)
                {
                    sb.append(ep);
                    sb.append(System.getProperty("line.separator"));
                }
            }

            if (!pendingRanges.isEmpty())
            {
                sb.append("Pending Ranges:");
                sb.append(System.getProperty("line.separator"));
                sb.append(printPendingRanges());
            }
        }
        finally
        {
            lock.readLock().unlock();
        }

        return sb.toString();
    }

    private String printPendingRanges()
    {
        StringBuilder sb = new StringBuilder();

        for (Map.Entry<String, Multimap<Range<Token>, InetAddress>> entry : pendingRanges.entrySet())
        {
            for (Map.Entry<Range<Token>, InetAddress> rmap : entry.getValue().entries())
            {
                sb.append(rmap.getValue()).append(":").append(rmap.getKey());
                sb.append(System.getProperty("line.separator"));
            }
        }

        return sb.toString();
    }

    public Collection<InetAddress> pendingEndpointsFor(Token token, String keyspaceName)
    {
        Map<Range<Token>, Collection<InetAddress>> ranges = getPendingRanges(keyspaceName);
        if (ranges.isEmpty())
            return Collections.emptyList();

        Set<InetAddress> endpoints = new HashSet<InetAddress>();
        for (Map.Entry<Range<Token>, Collection<InetAddress>> entry : ranges.entrySet())
        {
            if (entry.getKey().contains(token))
                endpoints.addAll(entry.getValue());
        }

        return endpoints;
    }

    /**
     * @deprecated retained for benefit of old tests
     */
    public Collection<InetAddress> getWriteEndpoints(Token token, String keyspaceName, Collection<InetAddress> naturalEndpoints)
    {
        return ImmutableList.copyOf(Iterables.concat(naturalEndpoints, pendingEndpointsFor(token, keyspaceName)));
    }

    /** @return an endpoint to token multimap representation of tokenToEndpointMap (a copy) */
    public Multimap<InetAddress, Token> getEndpointToTokenMapForReading()
    {
        lock.readLock().lock();
        try
        {
            Multimap<InetAddress, Token> cloned = HashMultimap.create();
            for (Map.Entry<Token, InetAddress> entry : tokenToEndpointMap.entrySet())
                cloned.put(entry.getValue(), entry.getKey());
            return cloned;
        }
        finally
        {
            lock.readLock().unlock();
        }
    }

    /**
     * @return a (stable copy, won't be modified) Token to Endpoint map for all the normal and bootstrapping nodes
     *         in the cluster.
     */
    public Map<Token, InetAddress> getNormalAndBootstrappingTokenToEndpointMap()
    {
        lock.readLock().lock();
        try
        {
            Map<Token, InetAddress> map = new HashMap<Token, InetAddress>(tokenToEndpointMap.size() + bootstrapTokens.size());
            map.putAll(tokenToEndpointMap);
            map.putAll(bootstrapTokens);
            return map;
        }
        finally
        {
            lock.readLock().unlock();
        }
    }

    /**
     * @return the Topology map of nodes to DCs + Racks
     *
     * This is only allowed when a copy has been made of TokenMetadata, to avoid concurrent modifications
     * when Topology methods are subsequently used by the caller.
     */
    public Topology getTopology()
    {
        assert this != StorageService.instance.getTokenMetadata();
        return topology;
    }

    public long getRingVersion()
    {
        return ringVersion;
    }

    public void invalidateCachedRings()
    {
        ringVersion++;
        cachedTokenMap.set(null);
    }

    /**
     * Tracks the assignment of racks and endpoints in each datacenter for all the "normal" endpoints
     * in this TokenMetadata. This allows faster calculation of endpoints in NetworkTopologyStrategy.
     */
    public static class Topology
    {
        /** multi-map of DC to endpoints in that DC */
        private final Multimap<String, InetAddress> dcEndpoints;
        /** map of DC to multi-map of rack to endpoints in that rack */
        private final Map<String, Multimap<String, InetAddress>> dcRacks;
        /** reverse-lookup map for endpoint to current known dc/rack assignment */
        private final Map<InetAddress, Pair<String, String>> currentLocations;

        protected Topology()
        {
            dcEndpoints = HashMultimap.create();
            dcRacks = new HashMap<String, Multimap<String, InetAddress>>();
            currentLocations = new HashMap<InetAddress, Pair<String, String>>();
        }

        protected void clear()
        {
            dcEndpoints.clear();
            dcRacks.clear();
            currentLocations.clear();
        }

        /**
         * construct deep-copy of other
         */
        protected Topology(Topology other)
        {
            dcEndpoints = HashMultimap.create(other.dcEndpoints);
            dcRacks = new HashMap<String, Multimap<String, InetAddress>>();
            for (String dc : other.dcRacks.keySet())
                dcRacks.put(dc, HashMultimap.create(other.dcRacks.get(dc)));
            currentLocations = new HashMap<InetAddress, Pair<String, String>>(other.currentLocations);
        }

        /**
         * Stores current DC/rack assignment for ep
         */
        protected void addEndpoint(InetAddress ep)
        {
            IEndpointSnitch snitch = DatabaseDescriptor.getEndpointSnitch();
            String dc = snitch.getDatacenter(ep);
            String rack = snitch.getRack(ep);
            Pair<String, String> current = currentLocations.get(ep);
            if (current != null)
            {
                if (current.left.equals(dc) && current.right.equals(rack))
                    return;
                dcRacks.get(current.left).remove(current.right, ep);
                dcEndpoints.remove(current.left, ep);
            }

            dcEndpoints.put(dc, ep);

            if (!dcRacks.containsKey(dc))
                dcRacks.put(dc, HashMultimap.<String, InetAddress>create());
            dcRacks.get(dc).put(rack, ep);

            currentLocations.put(ep, Pair.create(dc, rack));
        }

        /**
         * Removes current DC/rack assignment for ep
         */
        protected void removeEndpoint(InetAddress ep)
        {
            if (!currentLocations.containsKey(ep))
                return;
            Pair<String, String> current = currentLocations.remove(ep);
            dcEndpoints.remove(current.left, ep);
            dcRacks.get(current.left).remove(current.right, ep);
        }

        /**
         * @return multi-map of DC to endpoints in that DC
         */
        public Multimap<String, InetAddress> getDatacenterEndpoints()
        {
            return dcEndpoints;
        }

        /**
         * @return map of DC to multi-map of rack to endpoints in that rack
         */
        public Map<String, Multimap<String, InetAddress>> getDatacenterRacks()
        {
            return dcRacks;
        }
    }
}


File: src/java/org/apache/cassandra/service/StorageService.java
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

import static java.nio.charset.StandardCharsets.ISO_8859_1;

import java.io.ByteArrayInputStream;
import java.io.DataInputStream;
import java.io.File;
import java.io.IOError;
import java.io.IOException;
import java.lang.management.ManagementFactory;
import java.net.InetAddress;
import java.net.UnknownHostException;
import java.nio.ByteBuffer;
import java.util.ArrayList;
import java.util.Arrays;
import java.util.Collection;
import java.util.Collections;
import java.util.HashMap;
import java.util.HashSet;
import java.util.Iterator;
import java.util.LinkedHashMap;
import java.util.LinkedList;
import java.util.List;
import java.util.Map;
import java.util.Map.Entry;
import java.util.Set;
import java.util.SortedMap;
import java.util.TreeMap;
import java.util.UUID;
import java.util.concurrent.CopyOnWriteArrayList;
import java.util.concurrent.ExecutionException;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Future;
import java.util.concurrent.FutureTask;
import java.util.concurrent.TimeUnit;
import java.util.concurrent.TimeoutException;
import java.util.concurrent.atomic.AtomicBoolean;
import java.util.concurrent.atomic.AtomicInteger;

import javax.management.JMX;
import javax.management.MBeanServer;
import javax.management.NotificationBroadcasterSupport;
import javax.management.ObjectName;
import javax.management.openmbean.TabularData;
import javax.management.openmbean.TabularDataSupport;

import org.apache.cassandra.auth.AuthKeyspace;
import org.apache.cassandra.auth.AuthMigrationListener;
import org.apache.cassandra.concurrent.ScheduledExecutors;
import org.apache.cassandra.concurrent.Stage;
import org.apache.cassandra.concurrent.StageManager;
import org.apache.cassandra.config.*;
import org.apache.cassandra.db.BatchlogManager;
import org.apache.cassandra.db.ColumnFamilyStore;
import org.apache.cassandra.db.CounterMutationVerbHandler;
import org.apache.cassandra.db.DecoratedKey;
import org.apache.cassandra.db.DefinitionsUpdateVerbHandler;
import org.apache.cassandra.db.HintedHandOffManager;
import org.apache.cassandra.db.Keyspace;
import org.apache.cassandra.db.MigrationRequestVerbHandler;
import org.apache.cassandra.db.MutationVerbHandler;
import org.apache.cassandra.db.ReadRepairVerbHandler;
import org.apache.cassandra.db.ReadVerbHandler;
import org.apache.cassandra.db.SchemaCheckVerbHandler;
import org.apache.cassandra.db.SnapshotDetailsTabularData;
import org.apache.cassandra.db.SystemKeyspace;
import org.apache.cassandra.db.TruncateVerbHandler;
import org.apache.cassandra.db.commitlog.CommitLog;
import org.apache.cassandra.db.compaction.CompactionManager;
import org.apache.cassandra.dht.BootStrapper;
import org.apache.cassandra.dht.IPartitioner;
import org.apache.cassandra.dht.Range;
import org.apache.cassandra.dht.RangeStreamer;
import org.apache.cassandra.dht.RingPosition;
import org.apache.cassandra.dht.StreamStateStore;
import org.apache.cassandra.dht.Token;
import org.apache.cassandra.exceptions.AlreadyExistsException;
import org.apache.cassandra.exceptions.ConfigurationException;
import org.apache.cassandra.exceptions.InvalidRequestException;
import org.apache.cassandra.exceptions.UnavailableException;
import org.apache.cassandra.gms.ApplicationState;
import org.apache.cassandra.gms.EndpointState;
import org.apache.cassandra.gms.FailureDetector;
import org.apache.cassandra.gms.GossipDigestAck2VerbHandler;
import org.apache.cassandra.gms.GossipDigestAckVerbHandler;
import org.apache.cassandra.gms.GossipDigestSynVerbHandler;
import org.apache.cassandra.gms.GossipShutdownVerbHandler;
import org.apache.cassandra.gms.Gossiper;
import org.apache.cassandra.gms.IEndpointStateChangeSubscriber;
import org.apache.cassandra.gms.IFailureDetector;
import org.apache.cassandra.gms.TokenSerializer;
import org.apache.cassandra.gms.VersionedValue;
import org.apache.cassandra.io.sstable.SSTableDeletingTask;
import org.apache.cassandra.io.sstable.SSTableLoader;
import org.apache.cassandra.io.util.FileUtils;
import org.apache.cassandra.locator.AbstractReplicationStrategy;
import org.apache.cassandra.locator.DynamicEndpointSnitch;
import org.apache.cassandra.locator.IEndpointSnitch;
import org.apache.cassandra.locator.LocalStrategy;
import org.apache.cassandra.locator.TokenMetadata;
import org.apache.cassandra.metrics.StorageMetrics;
import org.apache.cassandra.net.AsyncOneResponse;
import org.apache.cassandra.net.MessageOut;
import org.apache.cassandra.net.MessagingService;
import org.apache.cassandra.net.ResponseVerbHandler;
import org.apache.cassandra.repair.RepairMessageVerbHandler;
import org.apache.cassandra.repair.RepairParallelism;
import org.apache.cassandra.repair.RepairRunnable;
import org.apache.cassandra.repair.SystemDistributedKeyspace;
import org.apache.cassandra.repair.messages.RepairOption;
import org.apache.cassandra.service.paxos.CommitVerbHandler;
import org.apache.cassandra.service.paxos.PrepareVerbHandler;
import org.apache.cassandra.service.paxos.ProposeVerbHandler;
import org.apache.cassandra.streaming.ReplicationFinishedVerbHandler;
import org.apache.cassandra.streaming.StreamManager;
import org.apache.cassandra.streaming.StreamPlan;
import org.apache.cassandra.streaming.StreamResultFuture;
import org.apache.cassandra.streaming.StreamState;
import org.apache.cassandra.thrift.EndpointDetails;
import org.apache.cassandra.thrift.TokenRange;
import org.apache.cassandra.thrift.cassandraConstants;
import org.apache.cassandra.tracing.TraceKeyspace;
import org.apache.cassandra.utils.BackgroundActivityMonitor;
import org.apache.cassandra.utils.FBUtilities;
import org.apache.cassandra.utils.JVMStabilityInspector;
import org.apache.cassandra.utils.OutputHandler;
import org.apache.cassandra.utils.Pair;
import org.apache.cassandra.utils.WindowsTimer;
import org.apache.cassandra.utils.WrappedRunnable;
import org.apache.cassandra.utils.progress.ProgressEvent;
import org.apache.cassandra.utils.progress.ProgressEventType;
import org.apache.cassandra.utils.progress.jmx.JMXProgressSupport;
import org.apache.commons.lang3.StringUtils;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import ch.qos.logback.classic.LoggerContext;
import ch.qos.logback.classic.jmx.JMXConfiguratorMBean;
import ch.qos.logback.classic.spi.ILoggingEvent;
import ch.qos.logback.core.Appender;

import com.google.common.annotations.VisibleForTesting;
import com.google.common.base.Predicate;
import com.google.common.collect.ArrayListMultimap;
import com.google.common.collect.Collections2;
import com.google.common.collect.HashMultimap;
import com.google.common.collect.ImmutableSet;
import com.google.common.collect.Iterables;
import com.google.common.collect.Lists;
import com.google.common.collect.Maps;
import com.google.common.collect.Multimap;
import com.google.common.collect.Sets;
import com.google.common.util.concurrent.FutureCallback;
import com.google.common.util.concurrent.Futures;
import com.google.common.util.concurrent.ListenableFuture;
import com.google.common.util.concurrent.Uninterruptibles;

/**
 * This abstraction contains the token/identifier of this node
 * on the identifier space. This token gets gossiped around.
 * This class will also maintain histograms of the load information
 * of other nodes in the cluster.
 */
public class StorageService extends NotificationBroadcasterSupport implements IEndpointStateChangeSubscriber, StorageServiceMBean
{
    private static final Logger logger = LoggerFactory.getLogger(StorageService.class);

    public static final int RING_DELAY = getRingDelay(); // delay after which we assume ring has stablized

    private final JMXProgressSupport progressSupport = new JMXProgressSupport(this);

    private static int getRingDelay()
    {
        String newdelay = System.getProperty("cassandra.ring_delay_ms");
        if (newdelay != null)
        {
            logger.info("Overriding RING_DELAY to {}ms", newdelay);
            return Integer.parseInt(newdelay);
        }
        else
            return 30 * 1000;
    }

    /* This abstraction maintains the token/endpoint metadata information */
    private TokenMetadata tokenMetadata = new TokenMetadata();

    public volatile VersionedValue.VersionedValueFactory valueFactory = new VersionedValue.VersionedValueFactory(getPartitioner());

    private Thread drainOnShutdown = null;
    private boolean inShutdownHook = false;

    public static final StorageService instance = new StorageService();

    public boolean isInShutdownHook()
    {
        return inShutdownHook;
    }

    public static IPartitioner getPartitioner()
    {
        return DatabaseDescriptor.getPartitioner();
    }

    public Collection<Range<Token>> getLocalRanges(String keyspaceName)
    {
        return getRangesForEndpoint(keyspaceName, FBUtilities.getBroadcastAddress());
    }

    public Collection<Range<Token>> getPrimaryRanges(String keyspace)
    {
        return getPrimaryRangesForEndpoint(keyspace, FBUtilities.getBroadcastAddress());
    }

    public Collection<Range<Token>> getPrimaryRangesWithinDC(String keyspace)
    {
        return getPrimaryRangeForEndpointWithinDC(keyspace, FBUtilities.getBroadcastAddress());
    }

    private final Set<InetAddress> replicatingNodes = Collections.synchronizedSet(new HashSet<InetAddress>());
    private CassandraDaemon daemon;

    private InetAddress removingNode;

    /* Are we starting this node in bootstrap mode? */
    private volatile boolean isBootstrapMode;

    /* we bootstrap but do NOT join the ring unless told to do so */
    private boolean isSurveyMode = Boolean.parseBoolean(System.getProperty("cassandra.write_survey", "false"));
    /* true if node is rebuilding and receiving data */
    private final AtomicBoolean isRebuilding = new AtomicBoolean();

    private boolean initialized;
    private volatile boolean joined = false;

    /* the probability for tracing any particular request, 0 disables tracing and 1 enables for all */
    private double traceProbability = 0.0;

    private static enum Mode { STARTING, NORMAL, JOINING, LEAVING, DECOMMISSIONED, MOVING, DRAINING, DRAINED }
    private Mode operationMode = Mode.STARTING;

    /* Used for tracking drain progress */
    private volatile int totalCFs, remainingCFs;

    private static final AtomicInteger nextRepairCommand = new AtomicInteger();

    private final List<IEndpointLifecycleSubscriber> lifecycleSubscribers = new CopyOnWriteArrayList<>();

    private static final BackgroundActivityMonitor bgMonitor = new BackgroundActivityMonitor();

    private final ObjectName jmxObjectName;

    private Collection<Token> bootstrapTokens = null;

    // true when keeping strict consistency while bootstrapping
    private boolean useStrictConsistency = Boolean.parseBoolean(System.getProperty("cassandra.consistent.rangemovement", "true"));
    private boolean replacing;

    private final StreamStateStore streamStateStore = new StreamStateStore();

    /** This method updates the local token on disk  */
    public void setTokens(Collection<Token> tokens)
    {
        if (logger.isDebugEnabled())
            logger.debug("Setting tokens to {}", tokens);
        SystemKeyspace.updateTokens(tokens);
        tokenMetadata.updateNormalTokens(tokens, FBUtilities.getBroadcastAddress());
        Collection<Token> localTokens = getLocalTokens();
        setGossipTokens(localTokens);
        setMode(Mode.NORMAL, false);
    }

    public void setGossipTokens(Collection<Token> tokens)
    {
        List<Pair<ApplicationState, VersionedValue>> states = new ArrayList<Pair<ApplicationState, VersionedValue>>();
        states.add(Pair.create(ApplicationState.TOKENS, valueFactory.tokens(tokens)));
        states.add(Pair.create(ApplicationState.STATUS, valueFactory.normal(tokens)));
        Gossiper.instance.addLocalApplicationStates(states);
    }

    public StorageService()
    {
        MBeanServer mbs = ManagementFactory.getPlatformMBeanServer();
        try
        {
            jmxObjectName = new ObjectName("org.apache.cassandra.db:type=StorageService");
            mbs.registerMBean(this, jmxObjectName);
            mbs.registerMBean(StreamManager.instance, new ObjectName(StreamManager.OBJECT_NAME));
        }
        catch (Exception e)
        {
            throw new RuntimeException(e);
        }

        /* register the verb handlers */
        MessagingService.instance().registerVerbHandlers(MessagingService.Verb.MUTATION, new MutationVerbHandler());
        MessagingService.instance().registerVerbHandlers(MessagingService.Verb.READ_REPAIR, new ReadRepairVerbHandler());
        MessagingService.instance().registerVerbHandlers(MessagingService.Verb.READ, new ReadVerbHandler());
        MessagingService.instance().registerVerbHandlers(MessagingService.Verb.RANGE_SLICE, new RangeSliceVerbHandler());
        MessagingService.instance().registerVerbHandlers(MessagingService.Verb.PAGED_RANGE, new RangeSliceVerbHandler());
        MessagingService.instance().registerVerbHandlers(MessagingService.Verb.COUNTER_MUTATION, new CounterMutationVerbHandler());
        MessagingService.instance().registerVerbHandlers(MessagingService.Verb.TRUNCATE, new TruncateVerbHandler());
        MessagingService.instance().registerVerbHandlers(MessagingService.Verb.PAXOS_PREPARE, new PrepareVerbHandler());
        MessagingService.instance().registerVerbHandlers(MessagingService.Verb.PAXOS_PROPOSE, new ProposeVerbHandler());
        MessagingService.instance().registerVerbHandlers(MessagingService.Verb.PAXOS_COMMIT, new CommitVerbHandler());

        // see BootStrapper for a summary of how the bootstrap verbs interact
        MessagingService.instance().registerVerbHandlers(MessagingService.Verb.REPLICATION_FINISHED, new ReplicationFinishedVerbHandler());
        MessagingService.instance().registerVerbHandlers(MessagingService.Verb.REQUEST_RESPONSE, new ResponseVerbHandler());
        MessagingService.instance().registerVerbHandlers(MessagingService.Verb.INTERNAL_RESPONSE, new ResponseVerbHandler());
        MessagingService.instance().registerVerbHandlers(MessagingService.Verb.REPAIR_MESSAGE, new RepairMessageVerbHandler());
        MessagingService.instance().registerVerbHandlers(MessagingService.Verb.GOSSIP_SHUTDOWN, new GossipShutdownVerbHandler());

        MessagingService.instance().registerVerbHandlers(MessagingService.Verb.GOSSIP_DIGEST_SYN, new GossipDigestSynVerbHandler());
        MessagingService.instance().registerVerbHandlers(MessagingService.Verb.GOSSIP_DIGEST_ACK, new GossipDigestAckVerbHandler());
        MessagingService.instance().registerVerbHandlers(MessagingService.Verb.GOSSIP_DIGEST_ACK2, new GossipDigestAck2VerbHandler());

        MessagingService.instance().registerVerbHandlers(MessagingService.Verb.DEFINITIONS_UPDATE, new DefinitionsUpdateVerbHandler());
        MessagingService.instance().registerVerbHandlers(MessagingService.Verb.SCHEMA_CHECK, new SchemaCheckVerbHandler());
        MessagingService.instance().registerVerbHandlers(MessagingService.Verb.MIGRATION_REQUEST, new MigrationRequestVerbHandler());

        MessagingService.instance().registerVerbHandlers(MessagingService.Verb.SNAPSHOT, new SnapshotVerbHandler());
        MessagingService.instance().registerVerbHandlers(MessagingService.Verb.ECHO, new EchoVerbHandler());
    }

    public void registerDaemon(CassandraDaemon daemon)
    {
        this.daemon = daemon;
    }

    public void register(IEndpointLifecycleSubscriber subscriber)
    {
        lifecycleSubscribers.add(subscriber);
    }

    public void unregister(IEndpointLifecycleSubscriber subscriber)
    {
        lifecycleSubscribers.remove(subscriber);
    }

    // should only be called via JMX
    public void stopGossiping()
    {
        if (initialized)
        {
            logger.warn("Stopping gossip by operator request");
            Gossiper.instance.stop();
            initialized = false;
        }
    }

    // should only be called via JMX
    public void startGossiping()
    {
        if (!initialized)
        {
            logger.warn("Starting gossip by operator request");
            setGossipTokens(getLocalTokens());
            Gossiper.instance.forceNewerGeneration();
            Gossiper.instance.start((int) (System.currentTimeMillis() / 1000));
            initialized = true;
        }
    }

    // should only be called via JMX
    public boolean isGossipRunning()
    {
        return Gossiper.instance.isEnabled();
    }

    // should only be called via JMX
    public void startRPCServer()
    {
        if (daemon == null)
        {
            throw new IllegalStateException("No configured daemon");
        }
        daemon.thriftServer.start();
    }

    public void stopRPCServer()
    {
        if (daemon == null)
        {
            throw new IllegalStateException("No configured daemon");
        }
        if (daemon.thriftServer != null)
            daemon.thriftServer.stop();
    }

    public boolean isRPCServerRunning()
    {
        if ((daemon == null) || (daemon.thriftServer == null))
        {
            return false;
        }
        return daemon.thriftServer.isRunning();
    }

    public void startNativeTransport()
    {
        if (daemon == null)
        {
            throw new IllegalStateException("No configured daemon");
        }

        try
        {
            daemon.nativeServer.start();
        }
        catch (Exception e)
        {
            throw new RuntimeException("Error starting native transport: " + e.getMessage());
        }
    }

    public void stopNativeTransport()
    {
        if (daemon == null)
        {
            throw new IllegalStateException("No configured daemon");
        }
        if (daemon.nativeServer != null)
            daemon.nativeServer.stop();
    }

    public boolean isNativeTransportRunning()
    {
        if ((daemon == null) || (daemon.nativeServer == null))
        {
            return false;
        }
        return daemon.nativeServer.isRunning();
    }

    public void stopTransports()
    {
        if (isInitialized())
        {
            logger.error("Stopping gossiper");
            stopGossiping();
        }
        if (isRPCServerRunning())
        {
            logger.error("Stopping RPC server");
            stopRPCServer();
        }
        if (isNativeTransportRunning())
        {
            logger.error("Stopping native transport");
            stopNativeTransport();
        }
    }

    private void shutdownClientServers()
    {
        stopRPCServer();
        stopNativeTransport();
    }

    public void stopClient()
    {
        Gossiper.instance.unregister(this);
        Gossiper.instance.stop();
        MessagingService.instance().shutdown();
        // give it a second so that task accepted before the MessagingService shutdown gets submitted to the stage (to avoid RejectedExecutionException)
        Uninterruptibles.sleepUninterruptibly(1, TimeUnit.SECONDS);
        StageManager.shutdownNow();
    }

    public boolean isInitialized()
    {
        return initialized;
    }

    public void stopDaemon()
    {
        if (daemon == null)
            throw new IllegalStateException("No configured daemon");
        daemon.deactivate();
    }

    public synchronized Collection<Token> prepareReplacementInfo() throws ConfigurationException
    {
        logger.info("Gathering node replacement information for {}", DatabaseDescriptor.getReplaceAddress());
        if (!MessagingService.instance().isListening())
            MessagingService.instance().listen(FBUtilities.getLocalAddress());

        // make magic happen
        Gossiper.instance.doShadowRound();

        UUID hostId = null;
        // now that we've gossiped at least once, we should be able to find the node we're replacing
        if (Gossiper.instance.getEndpointStateForEndpoint(DatabaseDescriptor.getReplaceAddress())== null)
            throw new RuntimeException("Cannot replace_address " + DatabaseDescriptor.getReplaceAddress() + " because it doesn't exist in gossip");
        hostId = Gossiper.instance.getHostId(DatabaseDescriptor.getReplaceAddress());
        try
        {
            if (Gossiper.instance.getEndpointStateForEndpoint(DatabaseDescriptor.getReplaceAddress()).getApplicationState(ApplicationState.TOKENS) == null)
                throw new RuntimeException("Could not find tokens for " + DatabaseDescriptor.getReplaceAddress() + " to replace");
            Collection<Token> tokens = TokenSerializer.deserialize(getPartitioner(), new DataInputStream(new ByteArrayInputStream(getApplicationStateValue(DatabaseDescriptor.getReplaceAddress(), ApplicationState.TOKENS))));

            SystemKeyspace.setLocalHostId(hostId); // use the replacee's host Id as our own so we receive hints, etc
            Gossiper.instance.resetEndpointStateMap(); // clean up since we have what we need
            return tokens;
        }
        catch (IOException e)
        {
            throw new RuntimeException(e);
        }
    }

    public synchronized void checkForEndpointCollision() throws ConfigurationException
    {
        logger.debug("Starting shadow gossip round to check for endpoint collision");
        if (!MessagingService.instance().isListening())
            MessagingService.instance().listen(FBUtilities.getLocalAddress());
        Gossiper.instance.doShadowRound();
        EndpointState epState = Gossiper.instance.getEndpointStateForEndpoint(FBUtilities.getBroadcastAddress());
        if (epState != null && !Gossiper.instance.isDeadState(epState) && !Gossiper.instance.isGossipOnlyMember(FBUtilities.getBroadcastAddress()))
        {
            throw new RuntimeException(String.format("A node with address %s already exists, cancelling join. " +
                                                     "Use cassandra.replace_address if you want to replace this node.",
                                                     FBUtilities.getBroadcastAddress()));
        }
        if (useStrictConsistency)
        {
            for (Map.Entry<InetAddress, EndpointState> entry : Gossiper.instance.getEndpointStates())
            {
                // ignore local node or empty status
                if (entry.getKey().equals(FBUtilities.getBroadcastAddress()) || entry.getValue().getApplicationState(ApplicationState.STATUS) == null)
                    continue;
                String[] pieces = entry.getValue().getApplicationState(ApplicationState.STATUS).value.split(VersionedValue.DELIMITER_STR, -1);
                assert (pieces.length > 0);
                String state = pieces[0];
                if (state.equals(VersionedValue.STATUS_BOOTSTRAPPING) || state.equals(VersionedValue.STATUS_LEAVING) || state.equals(VersionedValue.STATUS_MOVING))
                    throw new UnsupportedOperationException("Other bootstrapping/leaving/moving nodes detected, cannot bootstrap while cassandra.consistent.rangemovement is true");
            }
        }
        Gossiper.instance.resetEndpointStateMap();
    }

    // for testing only
    public void unsafeInitialize() throws ConfigurationException
    {
        initialized = true;
        Gossiper.instance.register(this);
        Gossiper.instance.start((int) (System.currentTimeMillis() / 1000)); // needed for node-ring gathering.
        Gossiper.instance.addLocalApplicationState(ApplicationState.NET_VERSION, valueFactory.networkVersion());
        if (!MessagingService.instance().isListening())
            MessagingService.instance().listen(FBUtilities.getLocalAddress());
    }

    public void populateTokenMetadata()
    {
        if (Boolean.parseBoolean(System.getProperty("cassandra.load_ring_state", "true")))
        {
            logger.info("Populating token metadata from system tables");
            Multimap<InetAddress, Token> loadedTokens = SystemKeyspace.loadTokens();
            if (!shouldBootstrap()) // if we have not completed bootstrapping, we should not add ourselves as a normal token
                loadedTokens.putAll(FBUtilities.getBroadcastAddress(), SystemKeyspace.getSavedTokens());
            for (InetAddress ep : loadedTokens.keySet())
                tokenMetadata.updateNormalTokens(loadedTokens.get(ep), ep);

            logger.info("Token metadata: {}", tokenMetadata);
        }
    }

    public synchronized void initServer() throws ConfigurationException
    {
        initServer(RING_DELAY);
    }

    public synchronized void initServer(int delay) throws ConfigurationException
    {
        logger.info("Cassandra version: {}", FBUtilities.getReleaseVersionString());
        logger.info("Thrift API version: {}", cassandraConstants.VERSION);
        logger.info("CQL supported versions: {} (default: {})",
                    StringUtils.join(ClientState.getCQLSupportedVersion(), ","), ClientState.DEFAULT_CQL_VERSION);

        initialized = true;

        try
        {
            // Ensure StorageProxy is initialized on start-up; see CASSANDRA-3797.
            Class.forName("org.apache.cassandra.service.StorageProxy");
            // also IndexSummaryManager, which is otherwise unreferenced
            Class.forName("org.apache.cassandra.io.sstable.IndexSummaryManager");
        }
        catch (ClassNotFoundException e)
        {
            throw new AssertionError(e);
        }

        if (Boolean.parseBoolean(System.getProperty("cassandra.load_ring_state", "true")))
        {
            logger.info("Loading persisted ring state");
            Multimap<InetAddress, Token> loadedTokens = SystemKeyspace.loadTokens();
            Map<InetAddress, UUID> loadedHostIds = SystemKeyspace.loadHostIds();
            for (InetAddress ep : loadedTokens.keySet())
            {
                if (ep.equals(FBUtilities.getBroadcastAddress()))
                {
                    // entry has been mistakenly added, delete it
                    SystemKeyspace.removeEndpoint(ep);
                }
                else
                {
                    if (loadedHostIds.containsKey(ep))
                        tokenMetadata.updateHostId(loadedHostIds.get(ep), ep);
                    Gossiper.instance.addSavedEndpoint(ep);
                }
            }
        }

        // daemon threads, like our executors', continue to run while shutdown hooks are invoked
        drainOnShutdown = new Thread(new WrappedRunnable()
        {
            @Override
            public void runMayThrow() throws InterruptedException
            {
                inShutdownHook = true;
                ExecutorService counterMutationStage = StageManager.getStage(Stage.COUNTER_MUTATION);
                ExecutorService mutationStage = StageManager.getStage(Stage.MUTATION);
                if (mutationStage.isShutdown() && counterMutationStage.isShutdown())
                    return; // drained already

                if (daemon != null)
                	shutdownClientServers();
                ScheduledExecutors.optionalTasks.shutdown();
                Gossiper.instance.stop();

                // In-progress writes originating here could generate hints to be written, so shut down MessagingService
                // before mutation stage, so we can get all the hints saved before shutting down
                MessagingService.instance().shutdown();
                counterMutationStage.shutdown();
                mutationStage.shutdown();
                counterMutationStage.awaitTermination(3600, TimeUnit.SECONDS);
                mutationStage.awaitTermination(3600, TimeUnit.SECONDS);
                StorageProxy.instance.verifyNoHintsInProgress();

                List<Future<?>> flushes = new ArrayList<>();
                for (Keyspace keyspace : Keyspace.all())
                {
                    KSMetaData ksm = Schema.instance.getKSMetaData(keyspace.getName());
                    if (!ksm.durableWrites)
                    {
                        for (ColumnFamilyStore cfs : keyspace.getColumnFamilyStores())
                            flushes.add(cfs.forceFlush());
                    }
                }
                try
                {
                    FBUtilities.waitOnFutures(flushes);
                }
                catch (Throwable t)
                {
                    JVMStabilityInspector.inspectThrowable(t);
                    // don't let this stop us from shutting down the commitlog and other thread pools
                    logger.warn("Caught exception while waiting for memtable flushes during shutdown hook", t);
                }

                CommitLog.instance.shutdownBlocking();

                if (FBUtilities.isWindows())
                    WindowsTimer.endTimerPeriod(DatabaseDescriptor.getWindowsTimerInterval());

                // wait for miscellaneous tasks like sstable and commitlog segment deletion
                ScheduledExecutors.nonPeriodicTasks.shutdown();
                if (!ScheduledExecutors.nonPeriodicTasks.awaitTermination(1, TimeUnit.MINUTES))
                    logger.warn("Miscellaneous task executor still busy after one minute; proceeding with shutdown");
            }
        }, "StorageServiceShutdownHook");
        Runtime.getRuntime().addShutdownHook(drainOnShutdown);

        replacing = DatabaseDescriptor.isReplacing();

        prepareToJoin();

        // Has to be called after the host id has potentially changed in prepareToJoin().
        for (ColumnFamilyStore cfs : ColumnFamilyStore.all())
            if (cfs.metadata.isCounter())
                cfs.initCounterCache();

        if (Boolean.parseBoolean(System.getProperty("cassandra.join_ring", "true")))
        {
            joinTokenRing(delay);
        }
        else
        {
            Collection<Token> tokens = SystemKeyspace.getSavedTokens();
            if (!tokens.isEmpty())
            {
                tokenMetadata.updateNormalTokens(tokens, FBUtilities.getBroadcastAddress());
                // order is important here, the gossiper can fire in between adding these two states.  It's ok to send TOKENS without STATUS, but *not* vice versa.
                List<Pair<ApplicationState, VersionedValue>> states = new ArrayList<Pair<ApplicationState, VersionedValue>>();
                states.add(Pair.create(ApplicationState.TOKENS, valueFactory.tokens(tokens)));
                states.add(Pair.create(ApplicationState.STATUS, valueFactory.hibernate(true)));
                Gossiper.instance.addLocalApplicationStates(states);
            }
            logger.info("Not joining ring as requested. Use JMX (StorageService->joinRing()) to initiate ring joining");
        }
    }

    /**
     * In the event of forceful termination we need to remove the shutdown hook to prevent hanging (OOM for instance)
     */
    public void removeShutdownHook()
    {
        if (drainOnShutdown != null)
            Runtime.getRuntime().removeShutdownHook(drainOnShutdown);

        if (FBUtilities.isWindows())
            WindowsTimer.endTimerPeriod(DatabaseDescriptor.getWindowsTimerInterval());
    }

    private boolean shouldBootstrap()
    {
        return DatabaseDescriptor.isAutoBootstrap() && !SystemKeyspace.bootstrapComplete() && !DatabaseDescriptor.getSeeds().contains(FBUtilities.getBroadcastAddress());
    }

    private void prepareToJoin() throws ConfigurationException
    {
        if (!joined)
        {
            Map<ApplicationState, VersionedValue> appStates = new HashMap<>();

            if (SystemKeyspace.wasDecommissioned())
            {
                if (Boolean.getBoolean("cassandra.override_decommission"))
                {
                    logger.warn("This node was decommissioned, but overriding by operator request.");
                    SystemKeyspace.setBootstrapState(SystemKeyspace.BootstrapState.COMPLETED);
                }
                else
                    throw new ConfigurationException("This node was decommissioned and will not rejoin the ring unless cassandra.override_decommission=true has been set, or all existing data is removed and the node is bootstrapped again");
            }
            if (replacing && !(Boolean.parseBoolean(System.getProperty("cassandra.join_ring", "true"))))
                throw new ConfigurationException("Cannot set both join_ring=false and attempt to replace a node");
            if (DatabaseDescriptor.getReplaceTokens().size() > 0 || DatabaseDescriptor.getReplaceNode() != null)
                throw new RuntimeException("Replace method removed; use cassandra.replace_address instead");
            if (replacing)
            {
                if (SystemKeyspace.bootstrapComplete())
                    throw new RuntimeException("Cannot replace address with a node that is already bootstrapped");
                if (!DatabaseDescriptor.isAutoBootstrap())
                    throw new RuntimeException("Trying to replace_address with auto_bootstrap disabled will not work, check your configuration");
                bootstrapTokens = prepareReplacementInfo();
                appStates.put(ApplicationState.TOKENS, valueFactory.tokens(bootstrapTokens));
                appStates.put(ApplicationState.STATUS, valueFactory.hibernate(true));
            }
            else if (shouldBootstrap())
            {
                checkForEndpointCollision();
            }

            // have to start the gossip service before we can see any info on other nodes.  this is necessary
            // for bootstrap to get the load info it needs.
            // (we won't be part of the storage ring though until we add a counterId to our state, below.)
            // Seed the host ID-to-endpoint map with our own ID.
            UUID localHostId = SystemKeyspace.getLocalHostId();
            getTokenMetadata().updateHostId(localHostId, FBUtilities.getBroadcastAddress());
            appStates.put(ApplicationState.NET_VERSION, valueFactory.networkVersion());
            appStates.put(ApplicationState.HOST_ID, valueFactory.hostId(localHostId));
            appStates.put(ApplicationState.RPC_ADDRESS, valueFactory.rpcaddress(DatabaseDescriptor.getBroadcastRpcAddress()));
            appStates.put(ApplicationState.RELEASE_VERSION, valueFactory.releaseVersion());
            logger.info("Starting up server gossip");
            Gossiper.instance.register(this);
            Gossiper.instance.start(SystemKeyspace.incrementAndGetGeneration(), appStates); // needed for node-ring gathering.
            // gossip snitch infos (local DC and rack)
            gossipSnitchInfo();
            // gossip Schema.emptyVersion forcing immediate check for schema updates (see MigrationManager#maybeScheduleSchemaPull)
            Schema.instance.updateVersionAndAnnounce(); // Ensure we know our own actual Schema UUID in preparation for updates

            if (!MessagingService.instance().isListening())
                MessagingService.instance().listen(FBUtilities.getLocalAddress());
            LoadBroadcaster.instance.startBroadcasting();

            HintedHandOffManager.instance.start();
            BatchlogManager.instance.start();
        }
    }

    private void joinTokenRing(int delay) throws ConfigurationException
    {
        joined = true;

        // We bootstrap if we haven't successfully bootstrapped before, as long as we are not a seed.
        // If we are a seed, or if the user manually sets auto_bootstrap to false,
        // we'll skip streaming data from other nodes and jump directly into the ring.
        //
        // The seed check allows us to skip the RING_DELAY sleep for the single-node cluster case,
        // which is useful for both new users and testing.
        //
        // We attempted to replace this with a schema-presence check, but you need a meaningful sleep
        // to get schema info from gossip which defeats the purpose.  See CASSANDRA-4427 for the gory details.
        Set<InetAddress> current = new HashSet<>();
        if (logger.isDebugEnabled())
        {
            logger.debug("Bootstrap variables: {} {} {} {}",
                         DatabaseDescriptor.isAutoBootstrap(),
                         SystemKeyspace.bootstrapInProgress(),
                         SystemKeyspace.bootstrapComplete(),
                         DatabaseDescriptor.getSeeds().contains(FBUtilities.getBroadcastAddress()));
        }
        if (DatabaseDescriptor.isAutoBootstrap() && !SystemKeyspace.bootstrapComplete() && DatabaseDescriptor.getSeeds().contains(FBUtilities.getBroadcastAddress()))
        {
            logger.info("This node will not auto bootstrap because it is configured to be a seed node.");
        }

        boolean dataAvailable = true; // make this to false when bootstrap streaming failed
        if (shouldBootstrap())
        {
            if (SystemKeyspace.bootstrapInProgress())
                logger.warn("Detected previous bootstrap failure; retrying");
            else
                SystemKeyspace.setBootstrapState(SystemKeyspace.BootstrapState.IN_PROGRESS);
            setMode(Mode.JOINING, "waiting for ring information", true);
            // first sleep the delay to make sure we see all our peers
            for (int i = 0; i < delay; i += 1000)
            {
                // if we see schema, we can proceed to the next check directly
                if (!Schema.instance.getVersion().equals(Schema.emptyVersion))
                {
                    logger.debug("got schema: {}", Schema.instance.getVersion());
                    break;
                }
                Uninterruptibles.sleepUninterruptibly(1, TimeUnit.SECONDS);
            }
            // if our schema hasn't matched yet, keep sleeping until it does
            // (post CASSANDRA-1391 we don't expect this to be necessary very often, but it doesn't hurt to be careful)
            while (!MigrationManager.isReadyForBootstrap())
            {
                setMode(Mode.JOINING, "waiting for schema information to complete", true);
                Uninterruptibles.sleepUninterruptibly(1, TimeUnit.SECONDS);
            }
            setMode(Mode.JOINING, "schema complete, ready to bootstrap", true);
            setMode(Mode.JOINING, "waiting for pending range calculation", true);
            PendingRangeCalculatorService.instance.blockUntilFinished();
            setMode(Mode.JOINING, "calculation complete, ready to bootstrap", true);

            logger.debug("... got ring + schema info");

            if (useStrictConsistency &&
                    (
                        tokenMetadata.getBootstrapTokens().valueSet().size() > 0 ||
                        tokenMetadata.getLeavingEndpoints().size() > 0 ||
                        tokenMetadata.getMovingEndpoints().size() > 0
                    ))
            {
                throw new UnsupportedOperationException("Other bootstrapping/leaving/moving nodes detected, cannot bootstrap while cassandra.consistent.rangemovement is true");
            }

            // get bootstrap tokens
            if (!replacing)
            {
                if (tokenMetadata.isMember(FBUtilities.getBroadcastAddress()))
                {
                    String s = "This node is already a member of the token ring; bootstrap aborted. (If replacing a dead node, remove the old one from the ring first.)";
                    throw new UnsupportedOperationException(s);
                }
                setMode(Mode.JOINING, "getting bootstrap token", true);
                bootstrapTokens = BootStrapper.getBootstrapTokens(tokenMetadata);
            }
            else
            {
                if (!DatabaseDescriptor.getReplaceAddress().equals(FBUtilities.getBroadcastAddress()))
                {
                    try
                    {
                        // Sleep additionally to make sure that the server actually is not alive
                        // and giving it more time to gossip if alive.
                        Thread.sleep(LoadBroadcaster.BROADCAST_INTERVAL);
                    }
                    catch (InterruptedException e)
                    {
                        throw new AssertionError(e);
                    }

                    // check for operator errors...
                    for (Token token : bootstrapTokens)
                    {
                        InetAddress existing = tokenMetadata.getEndpoint(token);
                        if (existing != null)
                        {
                            long nanoDelay = delay * 1000000L;
                            if (Gossiper.instance.getEndpointStateForEndpoint(existing).getUpdateTimestamp() > (System.nanoTime() - nanoDelay))
                                throw new UnsupportedOperationException("Cannot replace a live node... ");
                            current.add(existing);
                        }
                        else
                        {
                            throw new UnsupportedOperationException("Cannot replace token " + token + " which does not exist!");
                        }
                    }
                }
                else
                {
                    try
                    {
                        Thread.sleep(RING_DELAY);
                    }
                    catch (InterruptedException e)
                    {
                        throw new AssertionError(e);
                    }

                }
                setMode(Mode.JOINING, "Replacing a node with token(s): " + bootstrapTokens, true);
            }

            dataAvailable = bootstrap(bootstrapTokens);
        }
        else
        {
            bootstrapTokens = SystemKeyspace.getSavedTokens();
            if (bootstrapTokens.isEmpty())
            {
                Collection<String> initialTokens = DatabaseDescriptor.getInitialTokens();
                if (initialTokens.size() < 1)
                {
                    bootstrapTokens = BootStrapper.getRandomTokens(tokenMetadata, DatabaseDescriptor.getNumTokens());
                    if (DatabaseDescriptor.getNumTokens() == 1)
                        logger.warn("Generated random token {}. Random tokens will result in an unbalanced ring; see http://wiki.apache.org/cassandra/Operations", bootstrapTokens);
                    else
                        logger.info("Generated random tokens. tokens are {}", bootstrapTokens);
                }
                else
                {
                    bootstrapTokens = new ArrayList<>(initialTokens.size());
                    for (String token : initialTokens)
                        bootstrapTokens.add(getPartitioner().getTokenFactory().fromString(token));
                    logger.info("Saved tokens not found. Using configuration value: {}", bootstrapTokens);
                }
            }
            else
            {
                if (bootstrapTokens.size() != DatabaseDescriptor.getNumTokens())
                    throw new ConfigurationException("Cannot change the number of tokens from " + bootstrapTokens.size() + " to " + DatabaseDescriptor.getNumTokens());
                else
                    logger.info("Using saved tokens {}", bootstrapTokens);
            }
        }

        // if we don't have system_traces keyspace at this point, then create it manually
        if (Schema.instance.getKSMetaData(TraceKeyspace.NAME) == null)
            maybeAddKeyspace(TraceKeyspace.definition());

        if (Schema.instance.getKSMetaData(SystemDistributedKeyspace.NAME) == null)
            MigrationManager.announceNewKeyspace(SystemDistributedKeyspace.definition(), 0, false);

        if (!isSurveyMode)
        {
            if (dataAvailable)
            {
                // start participating in the ring.
                SystemKeyspace.setBootstrapState(SystemKeyspace.BootstrapState.COMPLETED);
                setTokens(bootstrapTokens);
                // remove the existing info about the replaced node.
                if (!current.isEmpty())
                {
                    for (InetAddress existing : current)
                        Gossiper.instance.replacedEndpoint(existing);
                }
                assert tokenMetadata.sortedTokens().size() > 0;
                doAuthSetup();
            }
            else
            {
                logger.warn("Some data streaming failed. Use nodetool to check bootstrap state and resume. For more, see `nodetool help bootstrap`. {}", SystemKeyspace.getBootstrapState());
            }
        }
        else
        {
            logger.info("Startup complete, but write survey mode is active, not becoming an active ring member. Use JMX (StorageService->joinRing()) to finalize ring joining.");
        }
    }

    public void gossipSnitchInfo()
    {
        IEndpointSnitch snitch = DatabaseDescriptor.getEndpointSnitch();
        String dc = snitch.getDatacenter(FBUtilities.getBroadcastAddress());
        String rack = snitch.getRack(FBUtilities.getBroadcastAddress());
        Gossiper.instance.addLocalApplicationState(ApplicationState.DC, StorageService.instance.valueFactory.datacenter(dc));
        Gossiper.instance.addLocalApplicationState(ApplicationState.RACK, StorageService.instance.valueFactory.rack(rack));
    }

    public synchronized void joinRing() throws IOException
    {
        if (!joined)
        {
            logger.info("Joining ring by operator request");
            try
            {
                joinTokenRing(0);
            }
            catch (ConfigurationException e)
            {
                throw new IOException(e.getMessage());
            }
        }
        else if (isSurveyMode)
        {
            setTokens(SystemKeyspace.getSavedTokens());
            SystemKeyspace.setBootstrapState(SystemKeyspace.BootstrapState.COMPLETED);
            isSurveyMode = false;
            logger.info("Leaving write survey mode and joining ring at operator request");
            assert tokenMetadata.sortedTokens().size() > 0;

            doAuthSetup();
        }
    }

    private void doAuthSetup()
    {
        try
        {
            // if we don't have system_auth keyspace at this point, then create it
            if (Schema.instance.getKSMetaData(AuthKeyspace.NAME) == null)
                maybeAddKeyspace(AuthKeyspace.definition());
        }
        catch (Exception e)
        {
            throw new AssertionError(e); // shouldn't ever happen.
        }

        // create any necessary tables as we may be upgrading in which case
        // the ks exists with the only the legacy tables defined.
        // Also, the addKeyspace above can be racy if multiple nodes are started
        // concurrently - see CASSANDRA-9201
        for (Map.Entry<String, CFMetaData> table : AuthKeyspace.definition().cfMetaData().entrySet())
            if (Schema.instance.getCFMetaData(AuthKeyspace.NAME, table.getKey()) == null)
                maybeAddTable(table.getValue());

        DatabaseDescriptor.getRoleManager().setup();
        DatabaseDescriptor.getAuthenticator().setup();
        DatabaseDescriptor.getAuthorizer().setup();
        MigrationManager.instance.register(new AuthMigrationListener());
    }

    private void maybeAddTable(CFMetaData cfm)
    {
        try
        {
            MigrationManager.announceNewColumnFamily(cfm);
        }
        catch (AlreadyExistsException e)
        {
            logger.debug("Attempted to create new table {}, but it already exists", cfm.cfName);
        }
    }

    private void maybeAddKeyspace(KSMetaData ksm)
    {
        try
        {
            MigrationManager.announceNewKeyspace(ksm, 0, false);
        }
        catch (AlreadyExistsException e)
        {
            logger.debug("Attempted to create new keyspace {}, but it already exists", ksm.name);
        }
    }

    public boolean isJoined()
    {
        return joined;
    }

    public void rebuild(String sourceDc)
    {
        // check on going rebuild
        if (!isRebuilding.compareAndSet(false, true))
        {
            throw new IllegalStateException("Node is still rebuilding. Check nodetool netstats.");
        }

        logger.info("rebuild from dc: {}", sourceDc == null ? "(any dc)" : sourceDc);

        try
        {
            RangeStreamer streamer = new RangeStreamer(tokenMetadata,
                                                       null,
                                                       FBUtilities.getBroadcastAddress(),
                                                       "Rebuild",
                                                       !replacing && useStrictConsistency,
                                                       DatabaseDescriptor.getEndpointSnitch(),
                                                       streamStateStore);
            streamer.addSourceFilter(new RangeStreamer.FailureDetectorSourceFilter(FailureDetector.instance));
            if (sourceDc != null)
                streamer.addSourceFilter(new RangeStreamer.SingleDatacenterFilter(DatabaseDescriptor.getEndpointSnitch(), sourceDc));

            for (String keyspaceName : Schema.instance.getNonSystemKeyspaces())
                streamer.addRanges(keyspaceName, getLocalRanges(keyspaceName));

            StreamResultFuture resultFuture = streamer.fetchAsync();
            // wait for result
            resultFuture.get();
        }
        catch (InterruptedException e)
        {
            throw new RuntimeException("Interrupted while waiting on rebuild streaming");
        }
        catch (ExecutionException e)
        {
            // This is used exclusively through JMX, so log the full trace but only throw a simple RTE
            logger.error("Error while rebuilding node", e.getCause());
            throw new RuntimeException("Error while rebuilding node: " + e.getCause().getMessage());
        }
        finally
        {
            // rebuild is done (successfully or not)
            isRebuilding.set(false);
        }
    }

    public void setStreamThroughputMbPerSec(int value)
    {
        DatabaseDescriptor.setStreamThroughputOutboundMegabitsPerSec(value);
        logger.info("setstreamthroughput: throttle set to {}", value);
    }

    public int getStreamThroughputMbPerSec()
    {
        return DatabaseDescriptor.getStreamThroughputOutboundMegabitsPerSec();
    }

    public int getCompactionThroughputMbPerSec()
    {
        return DatabaseDescriptor.getCompactionThroughputMbPerSec();
    }

    public void setCompactionThroughputMbPerSec(int value)
    {
        DatabaseDescriptor.setCompactionThroughputMbPerSec(value);
    }

    public boolean isIncrementalBackupsEnabled()
    {
        return DatabaseDescriptor.isIncrementalBackupsEnabled();
    }

    public void setIncrementalBackupsEnabled(boolean value)
    {
        DatabaseDescriptor.setIncrementalBackupsEnabled(value);
    }

    private void setMode(Mode m, boolean log)
    {
        setMode(m, null, log);
    }

    private void setMode(Mode m, String msg, boolean log)
    {
        operationMode = m;
        String logMsg = msg == null ? m.toString() : String.format("%s: %s", m, msg);
        if (log)
            logger.info(logMsg);
        else
            logger.debug(logMsg);
    }

    /**
     * Bootstrap node by fetching data from other nodes.
     * If node is bootstrapping as a new node, then this also announces bootstrapping to the cluster.
     *
     * This blocks until streaming is done.
     *
     * @param tokens bootstrapping tokens
     * @return true if bootstrap succeeds.
     */
    private boolean bootstrap(final Collection<Token> tokens)
    {
        isBootstrapMode = true;
        SystemKeyspace.updateTokens(tokens); // DON'T use setToken, that makes us part of the ring locally which is incorrect until we are done bootstrapping
        if (!replacing)
        {
            // if not an existing token then bootstrap
            List<Pair<ApplicationState, VersionedValue>> states = new ArrayList<>();
            states.add(Pair.create(ApplicationState.TOKENS, valueFactory.tokens(tokens)));
            states.add(Pair.create(ApplicationState.STATUS, valueFactory.bootstrapping(tokens)));
            Gossiper.instance.addLocalApplicationStates(states);
            setMode(Mode.JOINING, "sleeping " + RING_DELAY + " ms for pending range setup", true);
            Uninterruptibles.sleepUninterruptibly(RING_DELAY, TimeUnit.MILLISECONDS);
        }
        else
        {
            // Dont set any state for the node which is bootstrapping the existing token...
            tokenMetadata.updateNormalTokens(tokens, FBUtilities.getBroadcastAddress());
            SystemKeyspace.removeEndpoint(DatabaseDescriptor.getReplaceAddress());
        }
        if (!Gossiper.instance.seenAnySeed())
            throw new IllegalStateException("Unable to contact any seeds!");

        if (Boolean.getBoolean("cassandra.reset_bootstrap_progress"))
        {
            logger.info("Resetting bootstrap progress to start fresh");
            SystemKeyspace.resetAvailableRanges();
        }

        setMode(Mode.JOINING, "Starting to bootstrap...", true);
        BootStrapper bootstrapper = new BootStrapper(FBUtilities.getBroadcastAddress(), tokens, tokenMetadata);
        bootstrapper.addProgressListener(progressSupport);
        ListenableFuture<StreamState> bootstrapStream = bootstrapper.bootstrap(streamStateStore, !replacing && useStrictConsistency); // handles token update
        Futures.addCallback(bootstrapStream, new FutureCallback<StreamState>()
        {
            @Override
            public void onSuccess(StreamState streamState)
            {
                isBootstrapMode = false;
                logger.info("Bootstrap completed! for the tokens {}", tokens);
            }

            @Override
            public void onFailure(Throwable e)
            {
                logger.warn("Error during bootstrap: " + e.getCause().getMessage(), e.getCause());
            }
        });
        try
        {
            bootstrapStream.get();
            return true;
        }
        catch (Throwable e)
        {
            logger.error("Error while waiting on bootstrap to complete. Bootstrap will have to be restarted.", e);
            return false;
        }
    }

    public boolean resumeBootstrap()
    {
        if (isBootstrapMode && SystemKeyspace.bootstrapInProgress())
        {
            logger.info("Resuming bootstrap...");

            // get bootstrap tokens saved in system keyspace
            final Collection<Token> tokens = SystemKeyspace.getSavedTokens();
            // already bootstrapped ranges are filtered during bootstrap
            BootStrapper bootstrapper = new BootStrapper(FBUtilities.getBroadcastAddress(), tokens, tokenMetadata);
            bootstrapper.addProgressListener(progressSupport);
            ListenableFuture<StreamState> bootstrapStream = bootstrapper.bootstrap(streamStateStore, !replacing && useStrictConsistency); // handles token update
            Futures.addCallback(bootstrapStream, new FutureCallback<StreamState>()
            {
                @Override
                public void onSuccess(StreamState streamState)
                {
                    isBootstrapMode = false;
                    // start participating in the ring.
                    // pretend we are in survey mode so we can use joinRing() here
                    isSurveyMode = true;
                    try
                    {
                        progressSupport.progress("bootstrap", ProgressEvent.createNotification("Joining ring..."));
                        joinRing();
                    }
                    catch (IOException ignore)
                    {
                        // joinRing with survey mode does not throw IOException
                    }
                    progressSupport.progress("bootstrap", new ProgressEvent(ProgressEventType.COMPLETE, 1, 1, "Resume bootstrap complete"));
                    logger.info("Resume complete");
                }

                @Override
                public void onFailure(Throwable e)
                {
                    String message = "Error during bootstrap: " + e.getCause().getMessage();
                    logger.error(message, e.getCause());
                    progressSupport.progress("bootstrap", new ProgressEvent(ProgressEventType.ERROR, 1, 1, message));
                    progressSupport.progress("bootstrap", new ProgressEvent(ProgressEventType.COMPLETE, 1, 1, "Resume bootstrap complete"));
                }
            });
            return true;
        }
        else
        {
            logger.info("Resuming bootstrap is requested, but the node is already bootstrapped.");
            return false;
        }
    }

    public boolean isBootstrapMode()
    {
        return isBootstrapMode;
    }

    public TokenMetadata getTokenMetadata()
    {
        return tokenMetadata;
    }

    /**
     * Increment about the known Compaction severity of the events in this node
     */
    public void reportSeverity(double incr)
    {
        bgMonitor.incrCompactionSeverity(incr);
    }

    public void reportManualSeverity(double incr)
    {
        bgMonitor.incrManualSeverity(incr);
    }

    public double getSeverity(InetAddress endpoint)
    {
        return bgMonitor.getSeverity(endpoint);
    }

    /**
     * for a keyspace, return the ranges and corresponding listen addresses.
     * @param keyspace
     * @return the endpoint map
     */
    public Map<List<String>, List<String>> getRangeToEndpointMap(String keyspace)
    {
        /* All the ranges for the tokens */
        Map<List<String>, List<String>> map = new HashMap<>();
        for (Map.Entry<Range<Token>,List<InetAddress>> entry : getRangeToAddressMap(keyspace).entrySet())
        {
            map.put(entry.getKey().asList(), stringify(entry.getValue()));
        }
        return map;
    }

    /**
     * Return the rpc address associated with an endpoint as a string.
     * @param endpoint The endpoint to get rpc address for
     * @return the rpc address
     */
    public String getRpcaddress(InetAddress endpoint)
    {
        if (endpoint.equals(FBUtilities.getBroadcastAddress()))
            return DatabaseDescriptor.getBroadcastRpcAddress().getHostAddress();
        else if (Gossiper.instance.getEndpointStateForEndpoint(endpoint).getApplicationState(ApplicationState.RPC_ADDRESS) == null)
            return endpoint.getHostAddress();
        else
            return Gossiper.instance.getEndpointStateForEndpoint(endpoint).getApplicationState(ApplicationState.RPC_ADDRESS).value;
    }

    /**
     * for a keyspace, return the ranges and corresponding RPC addresses for a given keyspace.
     * @param keyspace
     * @return the endpoint map
     */
    public Map<List<String>, List<String>> getRangeToRpcaddressMap(String keyspace)
    {
        /* All the ranges for the tokens */
        Map<List<String>, List<String>> map = new HashMap<>();
        for (Map.Entry<Range<Token>, List<InetAddress>> entry : getRangeToAddressMap(keyspace).entrySet())
        {
            List<String> rpcaddrs = new ArrayList<>(entry.getValue().size());
            for (InetAddress endpoint: entry.getValue())
            {
                rpcaddrs.add(getRpcaddress(endpoint));
            }
            map.put(entry.getKey().asList(), rpcaddrs);
        }
        return map;
    }

    public Map<List<String>, List<String>> getPendingRangeToEndpointMap(String keyspace)
    {
        // some people just want to get a visual representation of things. Allow null and set it to the first
        // non-system keyspace.
        if (keyspace == null)
            keyspace = Schema.instance.getNonSystemKeyspaces().get(0);

        Map<List<String>, List<String>> map = new HashMap<>();
        for (Map.Entry<Range<Token>, Collection<InetAddress>> entry : tokenMetadata.getPendingRanges(keyspace).entrySet())
        {
            List<InetAddress> l = new ArrayList<>(entry.getValue());
            map.put(entry.getKey().asList(), stringify(l));
        }
        return map;
    }

    public Map<Range<Token>, List<InetAddress>> getRangeToAddressMap(String keyspace)
    {
        return getRangeToAddressMap(keyspace, tokenMetadata.sortedTokens());
    }

    public Map<Range<Token>, List<InetAddress>> getRangeToAddressMapInLocalDC(String keyspace)
    {
        Predicate<InetAddress> isLocalDC = new Predicate<InetAddress>()
        {
            public boolean apply(InetAddress address)
            {
                return isLocalDC(address);
            }
        };

        Map<Range<Token>, List<InetAddress>> origMap = getRangeToAddressMap(keyspace, getTokensInLocalDC());
        Map<Range<Token>, List<InetAddress>> filteredMap = Maps.newHashMap();
        for (Map.Entry<Range<Token>, List<InetAddress>> entry : origMap.entrySet())
        {
            List<InetAddress> endpointsInLocalDC = Lists.newArrayList(Collections2.filter(entry.getValue(), isLocalDC));
            filteredMap.put(entry.getKey(), endpointsInLocalDC);
        }

        return filteredMap;
    }

    private List<Token> getTokensInLocalDC()
    {
        List<Token> filteredTokens = Lists.newArrayList();
        for (Token token : tokenMetadata.sortedTokens())
        {
            InetAddress endpoint = tokenMetadata.getEndpoint(token);
            if (isLocalDC(endpoint))
                filteredTokens.add(token);
        }
        return filteredTokens;
    }

    private boolean isLocalDC(InetAddress targetHost)
    {
        String remoteDC = DatabaseDescriptor.getEndpointSnitch().getDatacenter(targetHost);
        String localDC = DatabaseDescriptor.getEndpointSnitch().getDatacenter(FBUtilities.getBroadcastAddress());
        return remoteDC.equals(localDC);
    }

    private Map<Range<Token>, List<InetAddress>> getRangeToAddressMap(String keyspace, List<Token> sortedTokens)
    {
        // some people just want to get a visual representation of things. Allow null and set it to the first
        // non-system keyspace.
        if (keyspace == null)
            keyspace = Schema.instance.getNonSystemKeyspaces().get(0);

        List<Range<Token>> ranges = getAllRanges(sortedTokens);
        return constructRangeToEndpointMap(keyspace, ranges);
    }


    /**
     * The same as {@code describeRing(String)} but converts TokenRange to the String for JMX compatibility
     *
     * @param keyspace The keyspace to fetch information about
     *
     * @return a List of TokenRange(s) converted to String for the given keyspace
     */
    public List<String> describeRingJMX(String keyspace) throws IOException
    {
        List<TokenRange> tokenRanges;
        try
        {
            tokenRanges = describeRing(keyspace);
        }
        catch (InvalidRequestException e)
        {
            throw new IOException(e.getMessage());
        }
        List<String> result = new ArrayList<>(tokenRanges.size());

        for (TokenRange tokenRange : tokenRanges)
            result.add(tokenRange.toString());

        return result;
    }

    /**
     * The TokenRange for a given keyspace.
     *
     * @param keyspace The keyspace to fetch information about
     *
     * @return a List of TokenRange(s) for the given keyspace
     *
     * @throws InvalidRequestException if there is no ring information available about keyspace
     */
    public List<TokenRange> describeRing(String keyspace) throws InvalidRequestException
    {
        return describeRing(keyspace, false);
    }

    /**
     * The same as {@code describeRing(String)} but considers only the part of the ring formed by nodes in the local DC.
     */
    public List<TokenRange> describeLocalRing(String keyspace) throws InvalidRequestException
    {
        return describeRing(keyspace, true);
    }

    private List<TokenRange> describeRing(String keyspace, boolean includeOnlyLocalDC) throws InvalidRequestException
    {
        if (!Schema.instance.getKeyspaces().contains(keyspace))
            throw new InvalidRequestException("No such keyspace: " + keyspace);

        if (keyspace == null || Keyspace.open(keyspace).getReplicationStrategy() instanceof LocalStrategy)
            throw new InvalidRequestException("There is no ring for the keyspace: " + keyspace);

        List<TokenRange> ranges = new ArrayList<>();
        Token.TokenFactory tf = getPartitioner().getTokenFactory();

        Map<Range<Token>, List<InetAddress>> rangeToAddressMap =
                includeOnlyLocalDC
                        ? getRangeToAddressMapInLocalDC(keyspace)
                        : getRangeToAddressMap(keyspace);

        for (Map.Entry<Range<Token>, List<InetAddress>> entry : rangeToAddressMap.entrySet())
        {
            Range<Token> range = entry.getKey();
            List<InetAddress> addresses = entry.getValue();
            List<String> endpoints = new ArrayList<>(addresses.size());
            List<String> rpc_endpoints = new ArrayList<>(addresses.size());
            List<EndpointDetails> epDetails = new ArrayList<>(addresses.size());

            for (InetAddress endpoint : addresses)
            {
                EndpointDetails details = new EndpointDetails();
                details.host = endpoint.getHostAddress();
                details.datacenter = DatabaseDescriptor.getEndpointSnitch().getDatacenter(endpoint);
                details.rack = DatabaseDescriptor.getEndpointSnitch().getRack(endpoint);

                endpoints.add(details.host);
                rpc_endpoints.add(getRpcaddress(endpoint));

                epDetails.add(details);
            }

            TokenRange tr = new TokenRange(tf.toString(range.left.getToken()), tf.toString(range.right.getToken()), endpoints)
                                    .setEndpoint_details(epDetails)
                                    .setRpc_endpoints(rpc_endpoints);

            ranges.add(tr);
        }

        return ranges;
    }

    public Map<String, String> getTokenToEndpointMap()
    {
        Map<Token, InetAddress> mapInetAddress = tokenMetadata.getNormalAndBootstrappingTokenToEndpointMap();
        // in order to preserve tokens in ascending order, we use LinkedHashMap here
        Map<String, String> mapString = new LinkedHashMap<>(mapInetAddress.size());
        List<Token> tokens = new ArrayList<>(mapInetAddress.keySet());
        Collections.sort(tokens);
        for (Token token : tokens)
        {
            mapString.put(token.toString(), mapInetAddress.get(token).getHostAddress());
        }
        return mapString;
    }

    public String getLocalHostId()
    {
        return getTokenMetadata().getHostId(FBUtilities.getBroadcastAddress()).toString();
    }

    public Map<String, String> getHostIdMap()
    {
        Map<String, String> mapOut = new HashMap<>();
        for (Map.Entry<InetAddress, UUID> entry : getTokenMetadata().getEndpointToHostIdMapForReading().entrySet())
            mapOut.put(entry.getKey().getHostAddress(), entry.getValue().toString());
        return mapOut;
    }

    /**
     * Construct the range to endpoint mapping based on the true view
     * of the world.
     * @param ranges
     * @return mapping of ranges to the replicas responsible for them.
    */
    private Map<Range<Token>, List<InetAddress>> constructRangeToEndpointMap(String keyspace, List<Range<Token>> ranges)
    {
        Map<Range<Token>, List<InetAddress>> rangeToEndpointMap = new HashMap<>(ranges.size());
        for (Range<Token> range : ranges)
        {
            rangeToEndpointMap.put(range, Keyspace.open(keyspace).getReplicationStrategy().getNaturalEndpoints(range.right));
        }
        return rangeToEndpointMap;
    }

    public void beforeChange(InetAddress endpoint, EndpointState currentState, ApplicationState newStateKey, VersionedValue newValue)
    {
        // no-op
    }

    /*
     * Handle the reception of a new particular ApplicationState for a particular endpoint. Note that the value of the
     * ApplicationState has not necessarily "changed" since the last known value, if we already received the same update
     * from somewhere else.
     *
     * onChange only ever sees one ApplicationState piece change at a time (even if many ApplicationState updates were
     * received at the same time), so we perform a kind of state machine here. We are concerned with two events: knowing
     * the token associated with an endpoint, and knowing its operation mode. Nodes can start in either bootstrap or
     * normal mode, and from bootstrap mode can change mode to normal. A node in bootstrap mode needs to have
     * pendingranges set in TokenMetadata; a node in normal mode should instead be part of the token ring.
     *
     * Normal progression of ApplicationState.STATUS values for a node should be like this:
     * STATUS_BOOTSTRAPPING,token
     *   if bootstrapping. stays this way until all files are received.
     * STATUS_NORMAL,token
     *   ready to serve reads and writes.
     * STATUS_LEAVING,token
     *   get ready to leave the cluster as part of a decommission
     * STATUS_LEFT,token
     *   set after decommission is completed.
     *
     * Other STATUS values that may be seen (possibly anywhere in the normal progression):
     * STATUS_MOVING,newtoken
     *   set if node is currently moving to a new token in the ring
     * REMOVING_TOKEN,deadtoken
     *   set if the node is dead and is being removed by its REMOVAL_COORDINATOR
     * REMOVED_TOKEN,deadtoken
     *   set if the node is dead and has been removed by its REMOVAL_COORDINATOR
     *
     * Note: Any time a node state changes from STATUS_NORMAL, it will not be visible to new nodes. So it follows that
     * you should never bootstrap a new node during a removenode, decommission or move.
     */
    public void onChange(InetAddress endpoint, ApplicationState state, VersionedValue value)
    {
        if (state == ApplicationState.STATUS)
        {
            String apStateValue = value.value;
            String[] pieces = apStateValue.split(VersionedValue.DELIMITER_STR, -1);
            assert (pieces.length > 0);

            String moveName = pieces[0];

            switch (moveName)
            {
                case VersionedValue.STATUS_BOOTSTRAPPING:
                    handleStateBootstrap(endpoint);
                    break;
                case VersionedValue.STATUS_NORMAL:
                    handleStateNormal(endpoint);
                    break;
                case VersionedValue.REMOVING_TOKEN:
                case VersionedValue.REMOVED_TOKEN:
                    handleStateRemoving(endpoint, pieces);
                    break;
                case VersionedValue.STATUS_LEAVING:
                    handleStateLeaving(endpoint);
                    break;
                case VersionedValue.STATUS_LEFT:
                    handleStateLeft(endpoint, pieces);
                    break;
                case VersionedValue.STATUS_MOVING:
                    handleStateMoving(endpoint, pieces);
                    break;
            }
        }
        else
        {
            EndpointState epState = Gossiper.instance.getEndpointStateForEndpoint(endpoint);
            if (epState == null || Gossiper.instance.isDeadState(epState))
            {
                logger.debug("Ignoring state change for dead or unknown endpoint: {}", endpoint);
                return;
            }

            if (getTokenMetadata().isMember(endpoint))
            {
                switch (state)
                {
                    case RELEASE_VERSION:
                        SystemKeyspace.updatePeerInfo(endpoint, "release_version", value.value);
                        break;
                    case DC:
                        SystemKeyspace.updatePeerInfo(endpoint, "data_center", value.value);
                        break;
                    case RACK:
                        SystemKeyspace.updatePeerInfo(endpoint, "rack", value.value);
                        break;
                    case RPC_ADDRESS:
                        try
                        {
                            SystemKeyspace.updatePeerInfo(endpoint, "rpc_address", InetAddress.getByName(value.value));
                        }
                        catch (UnknownHostException e)
                        {
                            throw new RuntimeException(e);
                        }
                        break;
                    case SCHEMA:
                        SystemKeyspace.updatePeerInfo(endpoint, "schema_version", UUID.fromString(value.value));
                        MigrationManager.instance.scheduleSchemaPull(endpoint, epState);
                        break;
                    case HOST_ID:
                        SystemKeyspace.updatePeerInfo(endpoint, "host_id", UUID.fromString(value.value));
                        break;
                    case RPC_READY:
                        notifyRpcChange(endpoint, epState.isRpcReady());
                        break;
                }
            }
        }
    }

    private void updatePeerInfo(InetAddress endpoint)
    {
        EndpointState epState = Gossiper.instance.getEndpointStateForEndpoint(endpoint);
        for (Map.Entry<ApplicationState, VersionedValue> entry : epState.getApplicationStateMap().entrySet())
        {
            switch (entry.getKey())
            {
                case RELEASE_VERSION:
                    SystemKeyspace.updatePeerInfo(endpoint, "release_version", entry.getValue().value);
                    break;
                case DC:
                    SystemKeyspace.updatePeerInfo(endpoint, "data_center", entry.getValue().value);
                    break;
                case RACK:
                    SystemKeyspace.updatePeerInfo(endpoint, "rack", entry.getValue().value);
                    break;
                case RPC_ADDRESS:
                    try
                    {
                        SystemKeyspace.updatePeerInfo(endpoint, "rpc_address", InetAddress.getByName(entry.getValue().value));
                    }
                    catch (UnknownHostException e)
                    {
                        throw new RuntimeException(e);
                    }
                    break;
                case SCHEMA:
                    SystemKeyspace.updatePeerInfo(endpoint, "schema_version", UUID.fromString(entry.getValue().value));
                    break;
                case HOST_ID:
                    SystemKeyspace.updatePeerInfo(endpoint, "host_id", UUID.fromString(entry.getValue().value));
                    break;
            }
        }
    }

    private byte[] getApplicationStateValue(InetAddress endpoint, ApplicationState appstate)
    {
        String vvalue = Gossiper.instance.getEndpointStateForEndpoint(endpoint).getApplicationState(appstate).value;
        return vvalue.getBytes(ISO_8859_1);
    }

    private void notifyRpcChange(InetAddress endpoint, boolean ready)
    {
        if (ready)
        {
            notifyUp(endpoint);
            notifyJoined(endpoint);
        }
        else
        {
            notifyDown(endpoint);
        }
    }

    private void notifyUp(InetAddress endpoint)
    {
        if (!isRpcReady(endpoint) || !Gossiper.instance.isAlive(endpoint))
            return;

        for (IEndpointLifecycleSubscriber subscriber : lifecycleSubscribers)
            subscriber.onUp(endpoint);
    }

    private void notifyDown(InetAddress endpoint)
    {
        for (IEndpointLifecycleSubscriber subscriber : lifecycleSubscribers)
            subscriber.onDown(endpoint);
    }

    private void notifyJoined(InetAddress endpoint)
    {
        if (!isRpcReady(endpoint) || !isStatus(endpoint, VersionedValue.STATUS_NORMAL))
            return;

        for (IEndpointLifecycleSubscriber subscriber : lifecycleSubscribers)
            subscriber.onJoinCluster(endpoint);
    }

    private void notifyMoved(InetAddress endpoint)
    {
        for (IEndpointLifecycleSubscriber subscriber : lifecycleSubscribers)
            subscriber.onMove(endpoint);
    }

    private void notifyLeft(InetAddress endpoint)
    {
        for (IEndpointLifecycleSubscriber subscriber : lifecycleSubscribers)
            subscriber.onLeaveCluster(endpoint);
    }

    private boolean isStatus(InetAddress endpoint, String status)
    {
        return Gossiper.instance.getEndpointStateForEndpoint(endpoint).getStatus().equals(status);
    }

    private boolean isRpcReady(InetAddress endpoint)
    {
        return MessagingService.instance().getVersion(endpoint) < MessagingService.VERSION_22 ||
                Gossiper.instance.getEndpointStateForEndpoint(endpoint).isRpcReady();
    }

    public void setRpcReady(boolean value)
    {
        Gossiper.instance.addLocalApplicationState(ApplicationState.RPC_READY, valueFactory.rpcReady(value));
    }

    private Collection<Token> getTokensFor(InetAddress endpoint)
    {
        try
        {
            return TokenSerializer.deserialize(getPartitioner(), new DataInputStream(new ByteArrayInputStream(getApplicationStateValue(endpoint, ApplicationState.TOKENS))));
        }
        catch (IOException e)
        {
            throw new RuntimeException(e);
        }
    }

    /**
     * Handle node bootstrap
     *
     * @param endpoint bootstrapping node
     */
    private void handleStateBootstrap(InetAddress endpoint)
    {
        Collection<Token> tokens;
        // explicitly check for TOKENS, because a bootstrapping node might be bootstrapping in legacy mode; that is, not using vnodes and no token specified
        tokens = getTokensFor(endpoint);

        if (logger.isDebugEnabled())
            logger.debug("Node {} state bootstrapping, token {}", endpoint, tokens);

        // if this node is present in token metadata, either we have missed intermediate states
        // or the node had crashed. Print warning if needed, clear obsolete stuff and
        // continue.
        if (tokenMetadata.isMember(endpoint))
        {
            // If isLeaving is false, we have missed both LEAVING and LEFT. However, if
            // isLeaving is true, we have only missed LEFT. Waiting time between completing
            // leave operation and rebootstrapping is relatively short, so the latter is quite
            // common (not enough time for gossip to spread). Therefore we report only the
            // former in the log.
            if (!tokenMetadata.isLeaving(endpoint))
                logger.info("Node {} state jump to bootstrap", endpoint);
            tokenMetadata.removeEndpoint(endpoint);
        }

        tokenMetadata.addBootstrapTokens(tokens, endpoint);
        PendingRangeCalculatorService.instance.update();

        tokenMetadata.updateHostId(Gossiper.instance.getHostId(endpoint), endpoint);
    }

    /**
     * Handle node move to normal state. That is, node is entering token ring and participating
     * in reads.
     *
     * @param endpoint node
     */
    private void handleStateNormal(final InetAddress endpoint)
    {
        Collection<Token> tokens;

        tokens = getTokensFor(endpoint);

        Set<Token> tokensToUpdateInMetadata = new HashSet<>();
        Set<Token> tokensToUpdateInSystemKeyspace = new HashSet<>();
        Set<Token> localTokensToRemove = new HashSet<>();
        Set<InetAddress> endpointsToRemove = new HashSet<>();


        if (logger.isDebugEnabled())
            logger.debug("Node {} state normal, token {}", endpoint, tokens);

        if (tokenMetadata.isMember(endpoint))
            logger.info("Node {} state jump to normal", endpoint);

        updatePeerInfo(endpoint);
        // Order Matters, TM.updateHostID() should be called before TM.updateNormalToken(), (see CASSANDRA-4300).
        UUID hostId = Gossiper.instance.getHostId(endpoint);
        InetAddress existing = tokenMetadata.getEndpointForHostId(hostId);
        if (replacing && Gossiper.instance.getEndpointStateForEndpoint(DatabaseDescriptor.getReplaceAddress()) != null && (hostId.equals(Gossiper.instance.getHostId(DatabaseDescriptor.getReplaceAddress()))))
            logger.warn("Not updating token metadata for {} because I am replacing it", endpoint);
        else
        {
            if (existing != null && !existing.equals(endpoint))
            {
                if (existing.equals(FBUtilities.getBroadcastAddress()))
                {
                    logger.warn("Not updating host ID {} for {} because it's mine", hostId, endpoint);
                    tokenMetadata.removeEndpoint(endpoint);
                    endpointsToRemove.add(endpoint);
                }
                else if (Gossiper.instance.compareEndpointStartup(endpoint, existing) > 0)
                {
                    logger.warn("Host ID collision for {} between {} and {}; {} is the new owner", hostId, existing, endpoint, endpoint);
                    tokenMetadata.removeEndpoint(existing);
                    endpointsToRemove.add(existing);
                    tokenMetadata.updateHostId(hostId, endpoint);
                }
                else
                {
                    logger.warn("Host ID collision for {} between {} and {}; ignored {}", hostId, existing, endpoint, endpoint);
                    tokenMetadata.removeEndpoint(endpoint);
                    endpointsToRemove.add(endpoint);
                }
            }
            else
                tokenMetadata.updateHostId(hostId, endpoint);
        }

        for (final Token token : tokens)
        {
            // we don't want to update if this node is responsible for the token and it has a later startup time than endpoint.
            InetAddress currentOwner = tokenMetadata.getEndpoint(token);
            if (currentOwner == null)
            {
                logger.debug("New node {} at token {}", endpoint, token);
                tokensToUpdateInMetadata.add(token);
                tokensToUpdateInSystemKeyspace.add(token);
            }
            else if (endpoint.equals(currentOwner))
            {
                // set state back to normal, since the node may have tried to leave, but failed and is now back up
                tokensToUpdateInMetadata.add(token);
                tokensToUpdateInSystemKeyspace.add(token);
            }
            else if (Gossiper.instance.compareEndpointStartup(endpoint, currentOwner) > 0)
            {
                tokensToUpdateInMetadata.add(token);
                tokensToUpdateInSystemKeyspace.add(token);

                // currentOwner is no longer current, endpoint is.  Keep track of these moves, because when
                // a host no longer has any tokens, we'll want to remove it.
                Multimap<InetAddress, Token> epToTokenCopy = getTokenMetadata().getEndpointToTokenMapForReading();
                epToTokenCopy.get(currentOwner).remove(token);
                if (epToTokenCopy.get(currentOwner).size() < 1)
                    endpointsToRemove.add(currentOwner);

                logger.info(String.format("Nodes %s and %s have the same token %s.  %s is the new owner",
                                          endpoint,
                                          currentOwner,
                                          token,
                                          endpoint));
            }
            else
            {
                logger.info(String.format("Nodes %s and %s have the same token %s.  Ignoring %s",
                                           endpoint,
                                           currentOwner,
                                           token,
                                           endpoint));
            }
        }

        boolean isMoving = tokenMetadata.isMoving(endpoint); // capture because updateNormalTokens clears moving status
        tokenMetadata.updateNormalTokens(tokensToUpdateInMetadata, endpoint);
        for (InetAddress ep : endpointsToRemove)
        {
            removeEndpoint(ep);
            if (replacing && DatabaseDescriptor.getReplaceAddress().equals(ep))
                Gossiper.instance.replacementQuarantine(ep); // quarantine locally longer than normally; see CASSANDRA-8260
        }
        if (!tokensToUpdateInSystemKeyspace.isEmpty())
            SystemKeyspace.updateTokens(endpoint, tokensToUpdateInSystemKeyspace);
        if (!localTokensToRemove.isEmpty())
            SystemKeyspace.updateLocalTokens(Collections.<Token>emptyList(), localTokensToRemove);

        if (isMoving || operationMode == Mode.MOVING)
        {
            tokenMetadata.removeFromMoving(endpoint);
            notifyMoved(endpoint);
        }
        else
        {
            notifyJoined(endpoint);
        }

        PendingRangeCalculatorService.instance.update();
    }

    /**
     * Handle node preparing to leave the ring
     *
     * @param endpoint node
     */
    private void handleStateLeaving(InetAddress endpoint)
    {
        Collection<Token> tokens;
        tokens = getTokensFor(endpoint);

        if (logger.isDebugEnabled())
            logger.debug("Node {} state leaving, tokens {}", endpoint, tokens);

        // If the node is previously unknown or tokens do not match, update tokenmetadata to
        // have this node as 'normal' (it must have been using this token before the
        // leave). This way we'll get pending ranges right.
        if (!tokenMetadata.isMember(endpoint))
        {
            logger.info("Node {} state jump to leaving", endpoint);
            tokenMetadata.updateNormalTokens(tokens, endpoint);
        }
        else if (!tokenMetadata.getTokens(endpoint).containsAll(tokens))
        {
            logger.warn("Node {} 'leaving' token mismatch. Long network partition?", endpoint);
            tokenMetadata.updateNormalTokens(tokens, endpoint);
        }

        // at this point the endpoint is certainly a member with this token, so let's proceed
        // normally
        tokenMetadata.addLeavingEndpoint(endpoint);
        PendingRangeCalculatorService.instance.update();
    }

    /**
     * Handle node leaving the ring. This will happen when a node is decommissioned
     *
     * @param endpoint If reason for leaving is decommission, endpoint is the leaving node.
     * @param pieces STATE_LEFT,token
     */
    private void handleStateLeft(InetAddress endpoint, String[] pieces)
    {
        assert pieces.length >= 2;
        Collection<Token> tokens;
        tokens = getTokensFor(endpoint);

        if (logger.isDebugEnabled())
            logger.debug("Node {} state left, tokens {}", endpoint, tokens);

        excise(tokens, endpoint, extractExpireTime(pieces));
    }

    /**
     * Handle node moving inside the ring.
     *
     * @param endpoint moving endpoint address
     * @param pieces STATE_MOVING, token
     */
    private void handleStateMoving(InetAddress endpoint, String[] pieces)
    {
        assert pieces.length >= 2;
        Token token = getPartitioner().getTokenFactory().fromString(pieces[1]);

        if (logger.isDebugEnabled())
            logger.debug("Node {} state moving, new token {}", endpoint, token);

        tokenMetadata.addMovingEndpoint(token, endpoint);

        PendingRangeCalculatorService.instance.update();
    }

    /**
     * Handle notification that a node being actively removed from the ring via 'removenode'
     *
     * @param endpoint node
     * @param pieces either REMOVED_TOKEN (node is gone) or REMOVING_TOKEN (replicas need to be restored)
     */
    private void handleStateRemoving(InetAddress endpoint, String[] pieces)
    {
        assert (pieces.length > 0);

        if (endpoint.equals(FBUtilities.getBroadcastAddress()))
        {
            logger.info("Received removenode gossip about myself. Is this node rejoining after an explicit removenode?");
            try
            {
                drain();
            }
            catch (Exception e)
            {
                throw new RuntimeException(e);
            }
            return;
        }
        if (tokenMetadata.isMember(endpoint))
        {
            String state = pieces[0];
            Collection<Token> removeTokens = tokenMetadata.getTokens(endpoint);

            if (VersionedValue.REMOVED_TOKEN.equals(state))
            {
                excise(removeTokens, endpoint, extractExpireTime(pieces));
            }
            else if (VersionedValue.REMOVING_TOKEN.equals(state))
            {
                if (logger.isDebugEnabled())
                    logger.debug("Tokens {} removed manually (endpoint was {})", removeTokens, endpoint);

                // Note that the endpoint is being removed
                tokenMetadata.addLeavingEndpoint(endpoint);
                PendingRangeCalculatorService.instance.update();

                // find the endpoint coordinating this removal that we need to notify when we're done
                String[] coordinator = Gossiper.instance.getEndpointStateForEndpoint(endpoint).getApplicationState(ApplicationState.REMOVAL_COORDINATOR).value.split(VersionedValue.DELIMITER_STR, -1);
                UUID hostId = UUID.fromString(coordinator[1]);
                // grab any data we are now responsible for and notify responsible node
                restoreReplicaCount(endpoint, tokenMetadata.getEndpointForHostId(hostId));
            }
        }
        else // now that the gossiper has told us about this nonexistent member, notify the gossiper to remove it
        {
            if (VersionedValue.REMOVED_TOKEN.equals(pieces[0]))
                addExpireTimeIfFound(endpoint, extractExpireTime(pieces));
            removeEndpoint(endpoint);
        }
    }

    private void excise(Collection<Token> tokens, InetAddress endpoint)
    {
        logger.info("Removing tokens {} for {}", tokens, endpoint);
        HintedHandOffManager.instance.deleteHintsForEndpoint(endpoint);
        removeEndpoint(endpoint);
        tokenMetadata.removeEndpoint(endpoint);
        tokenMetadata.removeBootstrapTokens(tokens);

        notifyLeft(endpoint);
        PendingRangeCalculatorService.instance.update();
    }

    private void excise(Collection<Token> tokens, InetAddress endpoint, long expireTime)
    {
        addExpireTimeIfFound(endpoint, expireTime);
        excise(tokens, endpoint);
    }

    /** unlike excise we just need this endpoint gone without going through any notifications **/
    private void removeEndpoint(InetAddress endpoint)
    {
        Gossiper.instance.removeEndpoint(endpoint);
        SystemKeyspace.removeEndpoint(endpoint);
    }

    protected void addExpireTimeIfFound(InetAddress endpoint, long expireTime)
    {
        if (expireTime != 0L)
        {
            Gossiper.instance.addExpireTimeForEndpoint(endpoint, expireTime);
        }
    }

    protected long extractExpireTime(String[] pieces)
    {
        return Long.parseLong(pieces[2]);
    }

    /**
     * Finds living endpoints responsible for the given ranges
     *
     * @param keyspaceName the keyspace ranges belong to
     * @param ranges the ranges to find sources for
     * @return multimap of addresses to ranges the address is responsible for
     */
    private Multimap<InetAddress, Range<Token>> getNewSourceRanges(String keyspaceName, Set<Range<Token>> ranges)
    {
        InetAddress myAddress = FBUtilities.getBroadcastAddress();
        Multimap<Range<Token>, InetAddress> rangeAddresses = Keyspace.open(keyspaceName).getReplicationStrategy().getRangeAddresses(tokenMetadata.cloneOnlyTokenMap());
        Multimap<InetAddress, Range<Token>> sourceRanges = HashMultimap.create();
        IFailureDetector failureDetector = FailureDetector.instance;

        // find alive sources for our new ranges
        for (Range<Token> range : ranges)
        {
            Collection<InetAddress> possibleRanges = rangeAddresses.get(range);
            IEndpointSnitch snitch = DatabaseDescriptor.getEndpointSnitch();
            List<InetAddress> sources = snitch.getSortedListByProximity(myAddress, possibleRanges);

            assert (!sources.contains(myAddress));

            for (InetAddress source : sources)
            {
                if (failureDetector.isAlive(source))
                {
                    sourceRanges.put(source, range);
                    break;
                }
            }
        }
        return sourceRanges;
    }

    /**
     * Sends a notification to a node indicating we have finished replicating data.
     *
     * @param remote node to send notification to
     */
    private void sendReplicationNotification(InetAddress remote)
    {
        // notify the remote token
        MessageOut msg = new MessageOut(MessagingService.Verb.REPLICATION_FINISHED);
        IFailureDetector failureDetector = FailureDetector.instance;
        if (logger.isDebugEnabled())
            logger.debug("Notifying {} of replication completion\n", remote);
        while (failureDetector.isAlive(remote))
        {
            AsyncOneResponse iar = MessagingService.instance().sendRR(msg, remote);
            try
            {
                iar.get(DatabaseDescriptor.getRpcTimeout(), TimeUnit.MILLISECONDS);
                return; // done
            }
            catch(TimeoutException e)
            {
                // try again
            }
        }
    }

    /**
     * Called when an endpoint is removed from the ring. This function checks
     * whether this node becomes responsible for new ranges as a
     * consequence and streams data if needed.
     *
     * This is rather ineffective, but it does not matter so much
     * since this is called very seldom
     *
     * @param endpoint the node that left
     */
    private void restoreReplicaCount(InetAddress endpoint, final InetAddress notifyEndpoint)
    {
        Multimap<String, Map.Entry<InetAddress, Collection<Range<Token>>>> rangesToFetch = HashMultimap.create();

        InetAddress myAddress = FBUtilities.getBroadcastAddress();

        for (String keyspaceName : Schema.instance.getNonSystemKeyspaces())
        {
            Multimap<Range<Token>, InetAddress> changedRanges = getChangedRangesForLeaving(keyspaceName, endpoint);
            Set<Range<Token>> myNewRanges = new HashSet<>();
            for (Map.Entry<Range<Token>, InetAddress> entry : changedRanges.entries())
            {
                if (entry.getValue().equals(myAddress))
                    myNewRanges.add(entry.getKey());
            }
            Multimap<InetAddress, Range<Token>> sourceRanges = getNewSourceRanges(keyspaceName, myNewRanges);
            for (Map.Entry<InetAddress, Collection<Range<Token>>> entry : sourceRanges.asMap().entrySet())
            {
                rangesToFetch.put(keyspaceName, entry);
            }
        }

        StreamPlan stream = new StreamPlan("Restore replica count");
        for (String keyspaceName : rangesToFetch.keySet())
        {
            for (Map.Entry<InetAddress, Collection<Range<Token>>> entry : rangesToFetch.get(keyspaceName))
            {
                InetAddress source = entry.getKey();
                InetAddress preferred = SystemKeyspace.getPreferredIP(source);
                Collection<Range<Token>> ranges = entry.getValue();
                if (logger.isDebugEnabled())
                    logger.debug("Requesting from {} ranges {}", source, StringUtils.join(ranges, ", "));
                stream.requestRanges(source, preferred, keyspaceName, ranges);
            }
        }
        StreamResultFuture future = stream.execute();
        Futures.addCallback(future, new FutureCallback<StreamState>()
        {
            public void onSuccess(StreamState finalState)
            {
                sendReplicationNotification(notifyEndpoint);
            }

            public void onFailure(Throwable t)
            {
                logger.warn("Streaming to restore replica count failed", t);
                // We still want to send the notification
                sendReplicationNotification(notifyEndpoint);
            }
        });
    }

    // needs to be modified to accept either a keyspace or ARS.
    private Multimap<Range<Token>, InetAddress> getChangedRangesForLeaving(String keyspaceName, InetAddress endpoint)
    {
        // First get all ranges the leaving endpoint is responsible for
        Collection<Range<Token>> ranges = getRangesForEndpoint(keyspaceName, endpoint);

        if (logger.isDebugEnabled())
            logger.debug("Node {} ranges [{}]", endpoint, StringUtils.join(ranges, ", "));

        Map<Range<Token>, List<InetAddress>> currentReplicaEndpoints = new HashMap<>(ranges.size());

        // Find (for each range) all nodes that store replicas for these ranges as well
        TokenMetadata metadata = tokenMetadata.cloneOnlyTokenMap(); // don't do this in the loop! #7758
        for (Range<Token> range : ranges)
            currentReplicaEndpoints.put(range, Keyspace.open(keyspaceName).getReplicationStrategy().calculateNaturalEndpoints(range.right, metadata));

        TokenMetadata temp = tokenMetadata.cloneAfterAllLeft();

        // endpoint might or might not be 'leaving'. If it was not leaving (that is, removenode
        // command was used), it is still present in temp and must be removed.
        if (temp.isMember(endpoint))
            temp.removeEndpoint(endpoint);

        Multimap<Range<Token>, InetAddress> changedRanges = HashMultimap.create();

        // Go through the ranges and for each range check who will be
        // storing replicas for these ranges when the leaving endpoint
        // is gone. Whoever is present in newReplicaEndpoints list, but
        // not in the currentReplicaEndpoints list, will be needing the
        // range.
        for (Range<Token> range : ranges)
        {
            Collection<InetAddress> newReplicaEndpoints = Keyspace.open(keyspaceName).getReplicationStrategy().calculateNaturalEndpoints(range.right, temp);
            newReplicaEndpoints.removeAll(currentReplicaEndpoints.get(range));
            if (logger.isDebugEnabled())
                if (newReplicaEndpoints.isEmpty())
                    logger.debug("Range {} already in all replicas", range);
                else
                    logger.debug("Range {} will be responsibility of {}", range, StringUtils.join(newReplicaEndpoints, ", "));
            changedRanges.putAll(range, newReplicaEndpoints);
        }

        return changedRanges;
    }

    public void onJoin(InetAddress endpoint, EndpointState epState)
    {
        for (Map.Entry<ApplicationState, VersionedValue> entry : epState.getApplicationStateMap().entrySet())
        {
            onChange(endpoint, entry.getKey(), entry.getValue());
        }
        MigrationManager.instance.scheduleSchemaPull(endpoint, epState);
    }

    public void onAlive(InetAddress endpoint, EndpointState state)
    {
        MigrationManager.instance.scheduleSchemaPull(endpoint, state);

        if (tokenMetadata.isMember(endpoint))
        {
            HintedHandOffManager.instance.scheduleHintDelivery(endpoint, true);
            notifyUp(endpoint);
        }
    }

    public void onRemove(InetAddress endpoint)
    {
        tokenMetadata.removeEndpoint(endpoint);
        PendingRangeCalculatorService.instance.update();
    }

    public void onDead(InetAddress endpoint, EndpointState state)
    {
        MessagingService.instance().convict(endpoint);
        notifyDown(endpoint);
    }

    public void onRestart(InetAddress endpoint, EndpointState state)
    {
        // If we have restarted before the node was even marked down, we need to reset the connection pool
        if (state.isAlive())
            onDead(endpoint, state);
    }


    public String getLoadString()
    {
        return FileUtils.stringifyFileSize(StorageMetrics.load.getCount());
    }

    public Map<String, String> getLoadMap()
    {
        Map<String, String> map = new HashMap<>();
        for (Map.Entry<InetAddress,Double> entry : LoadBroadcaster.instance.getLoadInfo().entrySet())
        {
            map.put(entry.getKey().getHostAddress(), FileUtils.stringifyFileSize(entry.getValue()));
        }
        // gossiper doesn't see its own updates, so we need to special-case the local node
        map.put(FBUtilities.getBroadcastAddress().getHostAddress(), getLoadString());
        return map;
    }

    public final void deliverHints(String host) throws UnknownHostException
    {
        HintedHandOffManager.instance.scheduleHintDelivery(host);
    }

    public Collection<Token> getLocalTokens()
    {
        Collection<Token> tokens = SystemKeyspace.getSavedTokens();
        assert tokens != null && !tokens.isEmpty(); // should not be called before initServer sets this
        return tokens;
    }

    /* These methods belong to the MBean interface */

    public List<String> getTokens()
    {
        return getTokens(FBUtilities.getBroadcastAddress());
    }

    public List<String> getTokens(String endpoint) throws UnknownHostException
    {
        return getTokens(InetAddress.getByName(endpoint));
    }

    private List<String> getTokens(InetAddress endpoint)
    {
        List<String> strTokens = new ArrayList<>();
        for (Token tok : getTokenMetadata().getTokens(endpoint))
            strTokens.add(tok.toString());
        return strTokens;
    }

    public String getReleaseVersion()
    {
        return FBUtilities.getReleaseVersionString();
    }

    public String getSchemaVersion()
    {
        return Schema.instance.getVersion().toString();
    }

    public List<String> getLeavingNodes()
    {
        return stringify(tokenMetadata.getLeavingEndpoints());
    }

    public List<String> getMovingNodes()
    {
        List<String> endpoints = new ArrayList<>();

        for (Pair<Token, InetAddress> node : tokenMetadata.getMovingEndpoints())
        {
            endpoints.add(node.right.getHostAddress());
        }

        return endpoints;
    }

    public List<String> getJoiningNodes()
    {
        return stringify(tokenMetadata.getBootstrapTokens().valueSet());
    }

    public List<String> getLiveNodes()
    {
        return stringify(Gossiper.instance.getLiveMembers());
    }

    public List<String> getUnreachableNodes()
    {
        return stringify(Gossiper.instance.getUnreachableMembers());
    }

    public String[] getAllDataFileLocations()
    {
        String[] locations = DatabaseDescriptor.getAllDataFileLocations();
        for (int i = 0; i < locations.length; i++)
            locations[i] = FileUtils.getCanonicalPath(locations[i]);
        return locations;
    }

    public String getCommitLogLocation()
    {
        return FileUtils.getCanonicalPath(DatabaseDescriptor.getCommitLogLocation());
    }

    public String getSavedCachesLocation()
    {
        return FileUtils.getCanonicalPath(DatabaseDescriptor.getSavedCachesLocation());
    }

    private List<String> stringify(Iterable<InetAddress> endpoints)
    {
        List<String> stringEndpoints = new ArrayList<>();
        for (InetAddress ep : endpoints)
        {
            stringEndpoints.add(ep.getHostAddress());
        }
        return stringEndpoints;
    }

    public int getCurrentGenerationNumber()
    {
        return Gossiper.instance.getCurrentGenerationNumber(FBUtilities.getBroadcastAddress());
    }

    public int forceKeyspaceCleanup(String keyspaceName, String... columnFamilies) throws IOException, ExecutionException, InterruptedException
    {
        if (keyspaceName.equals(SystemKeyspace.NAME))
            throw new RuntimeException("Cleanup of the system keyspace is neither necessary nor wise");

        CompactionManager.AllSSTableOpStatus status = CompactionManager.AllSSTableOpStatus.SUCCESSFUL;
        for (ColumnFamilyStore cfStore : getValidColumnFamilies(false, false, keyspaceName, columnFamilies))
        {
            CompactionManager.AllSSTableOpStatus oneStatus = cfStore.forceCleanup();
            if (oneStatus != CompactionManager.AllSSTableOpStatus.SUCCESSFUL)
                status = oneStatus;
        }
        return status.statusCode;
    }

    public int scrub(boolean disableSnapshot, boolean skipCorrupted, String keyspaceName, String... columnFamilies) throws IOException, ExecutionException, InterruptedException
    {
        return scrub(disableSnapshot, skipCorrupted, true, keyspaceName, columnFamilies);
    }

    public int scrub(boolean disableSnapshot, boolean skipCorrupted, boolean checkData, String keyspaceName, String... columnFamilies) throws IOException, ExecutionException, InterruptedException
    {
        CompactionManager.AllSSTableOpStatus status = CompactionManager.AllSSTableOpStatus.SUCCESSFUL;
        for (ColumnFamilyStore cfStore : getValidColumnFamilies(true, false, keyspaceName, columnFamilies))
        {
            CompactionManager.AllSSTableOpStatus oneStatus = cfStore.scrub(disableSnapshot, skipCorrupted, checkData);
            if (oneStatus != CompactionManager.AllSSTableOpStatus.SUCCESSFUL)
                status = oneStatus;
        }
        return status.statusCode;
    }

    public int verify(boolean extendedVerify, String keyspaceName, String... columnFamilies) throws IOException, ExecutionException, InterruptedException
    {
        CompactionManager.AllSSTableOpStatus status = CompactionManager.AllSSTableOpStatus.SUCCESSFUL;
        for (ColumnFamilyStore cfStore : getValidColumnFamilies(false, false, keyspaceName, columnFamilies))
        {
            CompactionManager.AllSSTableOpStatus oneStatus = cfStore.verify(extendedVerify);
            if (oneStatus != CompactionManager.AllSSTableOpStatus.SUCCESSFUL)
                status = oneStatus;
        }
        return status.statusCode;
    }

    public int upgradeSSTables(String keyspaceName, boolean excludeCurrentVersion, String... columnFamilies) throws IOException, ExecutionException, InterruptedException
    {
        CompactionManager.AllSSTableOpStatus status = CompactionManager.AllSSTableOpStatus.SUCCESSFUL;
        for (ColumnFamilyStore cfStore : getValidColumnFamilies(true, true, keyspaceName, columnFamilies))
        {
            CompactionManager.AllSSTableOpStatus oneStatus = cfStore.sstablesRewrite(excludeCurrentVersion);
            if (oneStatus != CompactionManager.AllSSTableOpStatus.SUCCESSFUL)
                status = oneStatus;
        }
        return status.statusCode;
    }

    public void forceKeyspaceCompaction(boolean splitOutput, String keyspaceName, String... columnFamilies) throws IOException, ExecutionException, InterruptedException
    {
        for (ColumnFamilyStore cfStore : getValidColumnFamilies(true, false, keyspaceName, columnFamilies))
        {
            cfStore.forceMajorCompaction(splitOutput);
        }
    }

    /**
     * Takes the snapshot for the given keyspaces. A snapshot name must be specified.
     *
     * @param tag the tag given to the snapshot; may not be null or empty
     * @param keyspaceNames the names of the keyspaces to snapshot; empty means "all."
     */
    public void takeSnapshot(String tag, String... keyspaceNames) throws IOException
    {
        if (operationMode == Mode.JOINING)
            throw new IOException("Cannot snapshot until bootstrap completes");
        if (tag == null || tag.equals(""))
            throw new IOException("You must supply a snapshot name.");

        Iterable<Keyspace> keyspaces;
        if (keyspaceNames.length == 0)
        {
            keyspaces = Keyspace.all();
        }
        else
        {
            ArrayList<Keyspace> t = new ArrayList<>(keyspaceNames.length);
            for (String keyspaceName : keyspaceNames)
                t.add(getValidKeyspace(keyspaceName));
            keyspaces = t;
        }

        // Do a check to see if this snapshot exists before we actually snapshot
        for (Keyspace keyspace : keyspaces)
            if (keyspace.snapshotExists(tag))
                throw new IOException("Snapshot " + tag + " already exists.");


        for (Keyspace keyspace : keyspaces)
            keyspace.snapshot(tag, null);
    }

    /**
     * Takes the snapshot of a specific column family. A snapshot name must be specified.
     *
     * @param keyspaceName the keyspace which holds the specified column family
     * @param columnFamilyName the column family to snapshot
     * @param tag the tag given to the snapshot; may not be null or empty
     */
    public void takeColumnFamilySnapshot(String keyspaceName, String columnFamilyName, String tag) throws IOException
    {
        if (keyspaceName == null)
            throw new IOException("You must supply a keyspace name");
        if (operationMode == Mode.JOINING)
            throw new IOException("Cannot snapshot until bootstrap completes");

        if (columnFamilyName == null)
            throw new IOException("You must supply a table name");
        if (columnFamilyName.contains("."))
            throw new IllegalArgumentException("Cannot take a snapshot of a secondary index by itself. Run snapshot on the table that owns the index.");

        if (tag == null || tag.equals(""))
            throw new IOException("You must supply a snapshot name.");

        Keyspace keyspace = getValidKeyspace(keyspaceName);
        ColumnFamilyStore columnFamilyStore = keyspace.getColumnFamilyStore(columnFamilyName);
        if (columnFamilyStore.snapshotExists(tag))
            throw new IOException("Snapshot " + tag + " already exists.");

        columnFamilyStore.snapshot(tag);
    }

    /**
     * Takes the snapshot of a multiple column family from different keyspaces. A snapshot name must be specified.
     * 
     * 
     * @param tag
     *            the tag given to the snapshot; may not be null or empty
     * @param columnFamilyList
     *            list of columnfamily from different keyspace in the form of ks1.cf1 ks2.cf2
     */
    @Override
    public void takeMultipleColumnFamilySnapshot(String tag, String... columnFamilyList)
            throws IOException
    {
        Map<Keyspace, List<String>> keyspaceColumnfamily = new HashMap<Keyspace, List<String>>();
        for (String columnFamily : columnFamilyList)
        {
            String splittedString[] = columnFamily.split("\\.");
            if (splittedString.length == 2)
            {
                String keyspaceName = splittedString[0];
                String columnFamilyName = splittedString[1];

                if (keyspaceName == null)
                    throw new IOException("You must supply a keyspace name");
                if (operationMode.equals(Mode.JOINING))
                    throw new IOException("Cannot snapshot until bootstrap completes");

                if (columnFamilyName == null)
                    throw new IOException("You must supply a column family name");
                if (tag == null || tag.equals(""))
                    throw new IOException("You must supply a snapshot name.");

                Keyspace keyspace = getValidKeyspace(keyspaceName);
                ColumnFamilyStore columnFamilyStore = keyspace.getColumnFamilyStore(columnFamilyName);
                // As there can be multiple column family from same keyspace check if snapshot exist for that specific
                // columnfamily and not for whole keyspace

                if (columnFamilyStore.snapshotExists(tag))
                    throw new IOException("Snapshot " + tag + " already exists.");
                if (!keyspaceColumnfamily.containsKey(keyspace))
                {
                    keyspaceColumnfamily.put(keyspace, new ArrayList<String>());
                }

                // Add Keyspace columnfamily to map in order to support atomicity for snapshot process.
                // So no snapshot should happen if any one of the above conditions fail for any keyspace or columnfamily
                keyspaceColumnfamily.get(keyspace).add(columnFamilyName);

            }
            else
            {
                throw new IllegalArgumentException(
                        "Cannot take a snapshot on secondary index or invalid column family name. You must supply a column family name in the form of keyspace.columnfamily");
            }
        }

        for (Entry<Keyspace, List<String>> entry : keyspaceColumnfamily.entrySet())
        {
            for (String columnFamily : entry.getValue())
                entry.getKey().snapshot(tag, columnFamily);
        }

    }

    private Keyspace getValidKeyspace(String keyspaceName) throws IOException
    {
        if (!Schema.instance.getKeyspaces().contains(keyspaceName))
        {
            throw new IOException("Keyspace " + keyspaceName + " does not exist");
        }
        return Keyspace.open(keyspaceName);
    }

    /**
     * Remove the snapshot with the given name from the given keyspaces.
     * If no tag is specified we will remove all snapshots.
     */
    public void clearSnapshot(String tag, String... keyspaceNames) throws IOException
    {
        if(tag == null)
            tag = "";

        Set<String> keyspaces = new HashSet<>();
        for (String dataDir : DatabaseDescriptor.getAllDataFileLocations())
        {
            for(String keyspaceDir : new File(dataDir).list())
            {
                // Only add a ks if it has been specified as a param, assuming params were actually provided.
                if (keyspaceNames.length > 0 && !Arrays.asList(keyspaceNames).contains(keyspaceDir))
                    continue;
                keyspaces.add(keyspaceDir);
            }
        }

        for (String keyspace : keyspaces)
            Keyspace.clearSnapshot(tag, keyspace);

        if (logger.isDebugEnabled())
            logger.debug("Cleared out snapshot directories");
    }

    public Map<String, TabularData> getSnapshotDetails()
    {
        Map<String, TabularData> snapshotMap = new HashMap<>();
        for (Keyspace keyspace : Keyspace.all())
        {
            if (SystemKeyspace.NAME.equals(keyspace.getName()))
                continue;

            for (ColumnFamilyStore cfStore : keyspace.getColumnFamilyStores())
            {
                for (Map.Entry<String, Pair<Long,Long>> snapshotDetail : cfStore.getSnapshotDetails().entrySet())
                {
                    TabularDataSupport data = (TabularDataSupport)snapshotMap.get(snapshotDetail.getKey());
                    if (data == null)
                    {
                        data = new TabularDataSupport(SnapshotDetailsTabularData.TABULAR_TYPE);
                        snapshotMap.put(snapshotDetail.getKey(), data);
                    }

                    SnapshotDetailsTabularData.from(snapshotDetail.getKey(), keyspace.getName(), cfStore.getColumnFamilyName(), snapshotDetail, data);
                }
            }
        }
        return snapshotMap;
    }

    public long trueSnapshotsSize()
    {
        long total = 0;
        for (Keyspace keyspace : Keyspace.all())
        {
            if (SystemKeyspace.NAME.equals(keyspace.getName()))
                continue;

            for (ColumnFamilyStore cfStore : keyspace.getColumnFamilyStores())
            {
                total += cfStore.trueSnapshotsSize();
            }
        }

        return total;
    }

    /**
     * @param allowIndexes Allow index CF names to be passed in
     * @param autoAddIndexes Automatically add secondary indexes if a CF has them
     * @param keyspaceName keyspace
     * @param cfNames CFs
     * @throws java.lang.IllegalArgumentException when given CF name does not exist
     */
    public Iterable<ColumnFamilyStore> getValidColumnFamilies(boolean allowIndexes, boolean autoAddIndexes, String keyspaceName, String... cfNames) throws IOException
    {
        Keyspace keyspace = getValidKeyspace(keyspaceName);
        return keyspace.getValidColumnFamilies(allowIndexes, autoAddIndexes, cfNames);
    }

    /**
     * Flush all memtables for a keyspace and column families.
     * @param keyspaceName
     * @param columnFamilies
     * @throws IOException
     */
    public void forceKeyspaceFlush(String keyspaceName, String... columnFamilies) throws IOException
    {
        for (ColumnFamilyStore cfStore : getValidColumnFamilies(true, false, keyspaceName, columnFamilies))
        {
            logger.debug("Forcing flush on keyspace {}, CF {}", keyspaceName, cfStore.name);
            cfStore.forceBlockingFlush();
        }
    }

    public int repairAsync(String keyspace, Map<String, String> repairSpec)
    {
        RepairOption option = RepairOption.parse(repairSpec, getPartitioner());
        // if ranges are not specified
        if (option.getRanges().isEmpty())
        {
            if (option.isPrimaryRange())
            {
                // when repairing only primary range, neither dataCenters nor hosts can be set
                if (option.getDataCenters().isEmpty() && option.getHosts().isEmpty())
                    option.getRanges().addAll(getPrimaryRanges(keyspace));
                    // except dataCenters only contain local DC (i.e. -local)
                else if (option.getDataCenters().size() == 1 && option.getDataCenters().contains(DatabaseDescriptor.getLocalDataCenter()))
                    option.getRanges().addAll(getPrimaryRangesWithinDC(keyspace));
                else
                    throw new IllegalArgumentException("You need to run primary range repair on all nodes in the cluster.");
            }
            else
            {
                option.getRanges().addAll(getLocalRanges(keyspace));
            }
        }
        return forceRepairAsync(keyspace, option);
    }

    @Deprecated
    public int forceRepairAsync(String keyspace,
                                boolean isSequential,
                                Collection<String> dataCenters,
                                Collection<String> hosts,
                                boolean primaryRange,
                                boolean fullRepair,
                                String... columnFamilies)
    {
        return forceRepairAsync(keyspace, isSequential ? RepairParallelism.SEQUENTIAL.ordinal() : RepairParallelism.PARALLEL.ordinal(), dataCenters, hosts, primaryRange, fullRepair, columnFamilies);
    }

    @Deprecated
    public int forceRepairAsync(String keyspace,
                                int parallelismDegree,
                                Collection<String> dataCenters,
                                Collection<String> hosts,
                                boolean primaryRange,
                                boolean fullRepair,
                                String... columnFamilies)
    {
        if (parallelismDegree < 0 || parallelismDegree > RepairParallelism.values().length - 1)
        {
            throw new IllegalArgumentException("Invalid parallelism degree specified: " + parallelismDegree);
        }
        RepairParallelism parallelism = RepairParallelism.values()[parallelismDegree];
        if (FBUtilities.isWindows() && parallelism != RepairParallelism.PARALLEL)
        {
            logger.warn("Snapshot-based repair is not yet supported on Windows.  Reverting to parallel repair.");
            parallelism = RepairParallelism.PARALLEL;
        }

        RepairOption options = new RepairOption(parallelism, primaryRange, !fullRepair, false, 1, Collections.<Range<Token>>emptyList());
        if (dataCenters != null)
        {
            options.getDataCenters().addAll(dataCenters);
        }
        if (hosts != null)
        {
            options.getHosts().addAll(hosts);
        }
        if (primaryRange)
        {
            // when repairing only primary range, neither dataCenters nor hosts can be set
            if (options.getDataCenters().isEmpty() && options.getHosts().isEmpty())
                options.getRanges().addAll(getPrimaryRanges(keyspace));
                // except dataCenters only contain local DC (i.e. -local)
            else if (options.getDataCenters().size() == 1 && options.getDataCenters().contains(DatabaseDescriptor.getLocalDataCenter()))
                options.getRanges().addAll(getPrimaryRangesWithinDC(keyspace));
            else
                throw new IllegalArgumentException("You need to run primary range repair on all nodes in the cluster.");
        }
        else
        {
            options.getRanges().addAll(getLocalRanges(keyspace));
        }
        if (columnFamilies != null)
        {
            for (String columnFamily : columnFamilies)
            {
                options.getColumnFamilies().add(columnFamily);
            }
        }
        return forceRepairAsync(keyspace, options);
    }

    public int forceRepairAsync(String keyspace,
                                boolean isSequential,
                                boolean isLocal,
                                boolean primaryRange,
                                boolean fullRepair,
                                String... columnFamilies)
    {
        Set<String> dataCenters = null;
        if (isLocal)
        {
            dataCenters = Sets.newHashSet(DatabaseDescriptor.getLocalDataCenter());
        }
        return forceRepairAsync(keyspace, isSequential, dataCenters, null, primaryRange, fullRepair, columnFamilies);
    }

    public int forceRepairRangeAsync(String beginToken,
                                     String endToken,
                                     String keyspaceName,
                                     boolean isSequential,
                                     Collection<String> dataCenters,
                                     Collection<String> hosts,
                                     boolean fullRepair,
                                     String... columnFamilies)
    {
        return forceRepairRangeAsync(beginToken, endToken, keyspaceName,
                                     isSequential ? RepairParallelism.SEQUENTIAL.ordinal() : RepairParallelism.PARALLEL.ordinal(),
                                     dataCenters, hosts, fullRepair, columnFamilies);
    }

    public int forceRepairRangeAsync(String beginToken,
                                     String endToken,
                                     String keyspaceName,
                                     int parallelismDegree,
                                     Collection<String> dataCenters,
                                     Collection<String> hosts,
                                     boolean fullRepair,
                                     String... columnFamilies)
    {
        if (parallelismDegree < 0 || parallelismDegree > RepairParallelism.values().length - 1)
        {
            throw new IllegalArgumentException("Invalid parallelism degree specified: " + parallelismDegree);
        }
        RepairParallelism parallelism = RepairParallelism.values()[parallelismDegree];
        if (FBUtilities.isWindows() && parallelism != RepairParallelism.PARALLEL)
        {
            logger.warn("Snapshot-based repair is not yet supported on Windows.  Reverting to parallel repair.");
            parallelism = RepairParallelism.PARALLEL;
        }
        Collection<Range<Token>> repairingRange = createRepairRangeFrom(beginToken, endToken);

        RepairOption options = new RepairOption(parallelism, false, !fullRepair, false, 1, repairingRange);
        options.getDataCenters().addAll(dataCenters);
        if (hosts != null)
        {
            options.getHosts().addAll(hosts);
        }
        if (columnFamilies != null)
        {
            for (String columnFamily : columnFamilies)
            {
                options.getColumnFamilies().add(columnFamily);
            }
        }

        logger.info("starting user-requested repair of range {} for keyspace {} and column families {}",
                    repairingRange, keyspaceName, columnFamilies);
        return forceRepairAsync(keyspaceName, options);
    }

    public int forceRepairRangeAsync(String beginToken,
                                     String endToken,
                                     String keyspaceName,
                                     boolean isSequential,
                                     boolean isLocal,
                                     boolean fullRepair,
                                     String... columnFamilies)
    {
        Set<String> dataCenters = null;
        if (isLocal)
        {
            dataCenters = Sets.newHashSet(DatabaseDescriptor.getLocalDataCenter());
        }
        return forceRepairRangeAsync(beginToken, endToken, keyspaceName, isSequential, dataCenters, null, fullRepair, columnFamilies);
    }

    /**
     * Create collection of ranges that match ring layout from given tokens.
     *
     * @param beginToken beginning token of the range
     * @param endToken end token of the range
     * @return collection of ranges that match ring layout in TokenMetadata
     */
    @VisibleForTesting
    Collection<Range<Token>> createRepairRangeFrom(String beginToken, String endToken)
    {
        Token parsedBeginToken = getPartitioner().getTokenFactory().fromString(beginToken);
        Token parsedEndToken = getPartitioner().getTokenFactory().fromString(endToken);

        // Break up given range to match ring layout in TokenMetadata
        ArrayList<Range<Token>> repairingRange = new ArrayList<>();

        ArrayList<Token> tokens = new ArrayList<>(tokenMetadata.sortedTokens());
        if (!tokens.contains(parsedBeginToken))
        {
            tokens.add(parsedBeginToken);
        }
        if (!tokens.contains(parsedEndToken))
        {
            tokens.add(parsedEndToken);
        }
        // tokens now contain all tokens including our endpoints
        Collections.sort(tokens);

        int start = tokens.indexOf(parsedBeginToken), end = tokens.indexOf(parsedEndToken);
        for (int i = start; i != end; i = (i+1) % tokens.size())
        {
            Range<Token> range = new Range<>(tokens.get(i), tokens.get((i+1) % tokens.size()));
            repairingRange.add(range);
        }

        return repairingRange;
    }

    public int forceRepairAsync(String keyspace, RepairOption options)
    {
        if (options.getRanges().isEmpty() || Keyspace.open(keyspace).getReplicationStrategy().getReplicationFactor() < 2)
            return 0;

        int cmd = nextRepairCommand.incrementAndGet();
        new Thread(createRepairTask(cmd, keyspace, options)).start();
        return cmd;
    }

    private FutureTask<Object> createRepairTask(final int cmd, final String keyspace, final RepairOption options)
    {
        if (!options.getDataCenters().isEmpty() && !options.getDataCenters().contains(DatabaseDescriptor.getLocalDataCenter()))
        {
            throw new IllegalArgumentException("the local data center must be part of the repair");
        }

        RepairRunnable task = new RepairRunnable(this, cmd, options, keyspace);
        task.addProgressListener(progressSupport);
        return new FutureTask<>(task, null);
    }

    public void forceTerminateAllRepairSessions() {
        ActiveRepairService.instance.terminateSessions();
    }

    /* End of MBean interface methods */

    /**
     * Get the "primary ranges" for the specified keyspace and endpoint.
     * "Primary ranges" are the ranges that the node is responsible for storing replica primarily.
     * The node that stores replica primarily is defined as the first node returned
     * by {@link AbstractReplicationStrategy#calculateNaturalEndpoints}.
     *
     * @param keyspace Keyspace name to check primary ranges
     * @param ep endpoint we are interested in.
     * @return primary ranges for the specified endpoint.
     */
    public Collection<Range<Token>> getPrimaryRangesForEndpoint(String keyspace, InetAddress ep)
    {
        AbstractReplicationStrategy strategy = Keyspace.open(keyspace).getReplicationStrategy();
        Collection<Range<Token>> primaryRanges = new HashSet<>();
        TokenMetadata metadata = tokenMetadata.cloneOnlyTokenMap();
        for (Token token : metadata.sortedTokens())
        {
            List<InetAddress> endpoints = strategy.calculateNaturalEndpoints(token, metadata);
            if (endpoints.size() > 0 && endpoints.get(0).equals(ep))
                primaryRanges.add(new Range<>(metadata.getPredecessor(token), token));
        }
        return primaryRanges;
    }

    /**
     * Get the "primary ranges" within local DC for the specified keyspace and endpoint.
     *
     * @see #getPrimaryRangesForEndpoint(String, java.net.InetAddress)
     * @param keyspace Keyspace name to check primary ranges
     * @param referenceEndpoint endpoint we are interested in.
     * @return primary ranges within local DC for the specified endpoint.
     */
    public Collection<Range<Token>> getPrimaryRangeForEndpointWithinDC(String keyspace, InetAddress referenceEndpoint)
    {
        TokenMetadata metadata = tokenMetadata.cloneOnlyTokenMap();
        String localDC = DatabaseDescriptor.getEndpointSnitch().getDatacenter(referenceEndpoint);
        Collection<InetAddress> localDcNodes = metadata.getTopology().getDatacenterEndpoints().get(localDC);
        AbstractReplicationStrategy strategy = Keyspace.open(keyspace).getReplicationStrategy();

        Collection<Range<Token>> localDCPrimaryRanges = new HashSet<>();
        for (Token token : metadata.sortedTokens())
        {
            List<InetAddress> endpoints = strategy.calculateNaturalEndpoints(token, metadata);
            for (InetAddress endpoint : endpoints)
            {
                if (localDcNodes.contains(endpoint))
                {
                    if (endpoint.equals(referenceEndpoint))
                    {
                        localDCPrimaryRanges.add(new Range<>(metadata.getPredecessor(token), token));
                    }
                    break;
                }
            }
        }

        return localDCPrimaryRanges;
    }

    /**
     * Get all ranges an endpoint is responsible for (by keyspace)
     * @param ep endpoint we are interested in.
     * @return ranges for the specified endpoint.
     */
    Collection<Range<Token>> getRangesForEndpoint(String keyspaceName, InetAddress ep)
    {
        return Keyspace.open(keyspaceName).getReplicationStrategy().getAddressRanges().get(ep);
    }

    /**
     * Get all ranges that span the ring given a set
     * of tokens. All ranges are in sorted order of
     * ranges.
     * @return ranges in sorted order
    */
    public List<Range<Token>> getAllRanges(List<Token> sortedTokens)
    {
        if (logger.isDebugEnabled())
            logger.debug("computing ranges for {}", StringUtils.join(sortedTokens, ", "));

        if (sortedTokens.isEmpty())
            return Collections.emptyList();
        int size = sortedTokens.size();
        List<Range<Token>> ranges = new ArrayList<>(size + 1);
        for (int i = 1; i < size; ++i)
        {
            Range<Token> range = new Range<>(sortedTokens.get(i - 1), sortedTokens.get(i));
            ranges.add(range);
        }
        Range<Token> range = new Range<>(sortedTokens.get(size - 1), sortedTokens.get(0));
        ranges.add(range);

        return ranges;
    }

    /**
     * This method returns the N endpoints that are responsible for storing the
     * specified key i.e for replication.
     *
     * @param keyspaceName keyspace name also known as keyspace
     * @param cf Column family name
     * @param key key for which we need to find the endpoint
     * @return the endpoint responsible for this key
     */
    public List<InetAddress> getNaturalEndpoints(String keyspaceName, String cf, String key)
    {
        KSMetaData ksMetaData = Schema.instance.getKSMetaData(keyspaceName);
        if (ksMetaData == null)
            throw new IllegalArgumentException("Unknown keyspace '" + keyspaceName + "'");

        CFMetaData cfMetaData = ksMetaData.cfMetaData().get(cf);
        if (cfMetaData == null)
            throw new IllegalArgumentException("Unknown table '" + cf + "' in keyspace '" + keyspaceName + "'");

        return getNaturalEndpoints(keyspaceName, getPartitioner().getToken(cfMetaData.getKeyValidator().fromString(key)));
    }

    public List<InetAddress> getNaturalEndpoints(String keyspaceName, ByteBuffer key)
    {
        return getNaturalEndpoints(keyspaceName, getPartitioner().getToken(key));
    }

    /**
     * This method returns the N endpoints that are responsible for storing the
     * specified key i.e for replication.
     *
     * @param keyspaceName keyspace name also known as keyspace
     * @param pos position for which we need to find the endpoint
     * @return the endpoint responsible for this token
     */
    public List<InetAddress> getNaturalEndpoints(String keyspaceName, RingPosition pos)
    {
        return Keyspace.open(keyspaceName).getReplicationStrategy().getNaturalEndpoints(pos);
    }

    /**
     * This method attempts to return N endpoints that are responsible for storing the
     * specified key i.e for replication.
     *
     * @param keyspace keyspace name also known as keyspace
     * @param key key for which we need to find the endpoint
     * @return the endpoint responsible for this key
     */
    public List<InetAddress> getLiveNaturalEndpoints(Keyspace keyspace, ByteBuffer key)
    {
        return getLiveNaturalEndpoints(keyspace, getPartitioner().decorateKey(key));
    }

    public List<InetAddress> getLiveNaturalEndpoints(Keyspace keyspace, RingPosition pos)
    {
        List<InetAddress> endpoints = keyspace.getReplicationStrategy().getNaturalEndpoints(pos);
        List<InetAddress> liveEps = new ArrayList<>(endpoints.size());

        for (InetAddress endpoint : endpoints)
        {
            if (FailureDetector.instance.isAlive(endpoint))
                liveEps.add(endpoint);
        }

        return liveEps;
    }

    public void setLoggingLevel(String classQualifier, String rawLevel) throws Exception
    {
        ch.qos.logback.classic.Logger logBackLogger = (ch.qos.logback.classic.Logger) LoggerFactory.getLogger(classQualifier);

        // if both classQualifer and rawLevel are empty, reload from configuration
        if (StringUtils.isBlank(classQualifier) && StringUtils.isBlank(rawLevel) )
        {
            JMXConfiguratorMBean jmxConfiguratorMBean = JMX.newMBeanProxy(ManagementFactory.getPlatformMBeanServer(),
                    new ObjectName("ch.qos.logback.classic:Name=default,Type=ch.qos.logback.classic.jmx.JMXConfigurator"),
                    JMXConfiguratorMBean.class);
            jmxConfiguratorMBean.reloadDefaultConfiguration();
            return;
        }
        // classQualifer is set, but blank level given
        else if (StringUtils.isNotBlank(classQualifier) && StringUtils.isBlank(rawLevel) )
        {
            if (logBackLogger.getLevel() != null || hasAppenders(logBackLogger))
                logBackLogger.setLevel(null);
            return;
        }

        ch.qos.logback.classic.Level level = ch.qos.logback.classic.Level.toLevel(rawLevel);
        logBackLogger.setLevel(level);
        logger.info("set log level to {} for classes under '{}' (if the level doesn't look like '{}' then the logger couldn't parse '{}')", level, classQualifier, rawLevel, rawLevel);
    }

    /**
     * @return the runtime logging levels for all the configured loggers
     */
    @Override
    public Map<String,String>getLoggingLevels() {
        Map<String, String> logLevelMaps = Maps.newLinkedHashMap();
        LoggerContext lc = (LoggerContext) LoggerFactory.getILoggerFactory();
        for (ch.qos.logback.classic.Logger logger : lc.getLoggerList())
        {
            if(logger.getLevel() != null || hasAppenders(logger))
                logLevelMaps.put(logger.getName(), logger.getLevel().toString());
        }
        return logLevelMaps;
    }

    private boolean hasAppenders(ch.qos.logback.classic.Logger logger) {
        Iterator<Appender<ILoggingEvent>> it = logger.iteratorForAppenders();
        return it.hasNext();
    }

    /**
     * @return list of Token ranges (_not_ keys!) together with estimated key count,
     *      breaking up the data this node is responsible for into pieces of roughly keysPerSplit
     */
    public List<Pair<Range<Token>, Long>> getSplits(String keyspaceName, String cfName, Range<Token> range, int keysPerSplit)
    {
        Keyspace t = Keyspace.open(keyspaceName);
        ColumnFamilyStore cfs = t.getColumnFamilyStore(cfName);
        List<DecoratedKey> keys = keySamples(Collections.singleton(cfs), range);

        long totalRowCountEstimate = cfs.estimatedKeysForRange(range);

        // splitCount should be much smaller than number of key samples, to avoid huge sampling error
        int minSamplesPerSplit = 4;
        int maxSplitCount = keys.size() / minSamplesPerSplit + 1;
        int splitCount = Math.max(1, Math.min(maxSplitCount, (int)(totalRowCountEstimate / keysPerSplit)));

        List<Token> tokens = keysToTokens(range, keys);
        return getSplits(tokens, splitCount, cfs);
    }

    private List<Pair<Range<Token>, Long>> getSplits(List<Token> tokens, int splitCount, ColumnFamilyStore cfs)
    {
        double step = (double) (tokens.size() - 1) / splitCount;
        Token prevToken = tokens.get(0);
        List<Pair<Range<Token>, Long>> splits = Lists.newArrayListWithExpectedSize(splitCount);
        for (int i = 1; i <= splitCount; i++)
        {
            int index = (int) Math.round(i * step);
            Token token = tokens.get(index);
            Range<Token> range = new Range<>(prevToken, token);
            // always return an estimate > 0 (see CASSANDRA-7322)
            splits.add(Pair.create(range, Math.max(cfs.metadata.getMinIndexInterval(), cfs.estimatedKeysForRange(range))));
            prevToken = token;
        }
        return splits;
    }

    private List<Token> keysToTokens(Range<Token> range, List<DecoratedKey> keys)
    {
        List<Token> tokens = Lists.newArrayListWithExpectedSize(keys.size() + 2);
        tokens.add(range.left);
        for (DecoratedKey key : keys)
            tokens.add(key.getToken());
        tokens.add(range.right);
        return tokens;
    }

    private List<DecoratedKey> keySamples(Iterable<ColumnFamilyStore> cfses, Range<Token> range)
    {
        List<DecoratedKey> keys = new ArrayList<>();
        for (ColumnFamilyStore cfs : cfses)
            Iterables.addAll(keys, cfs.keySamples(range));
        FBUtilities.sortSampledKeys(keys, range);
        return keys;
    }

    /**
     * Broadcast leaving status and update local tokenMetadata accordingly
     */
    private void startLeaving()
    {
        Gossiper.instance.addLocalApplicationState(ApplicationState.STATUS, valueFactory.leaving(getLocalTokens()));
        tokenMetadata.addLeavingEndpoint(FBUtilities.getBroadcastAddress());
        PendingRangeCalculatorService.instance.update();
    }

    public void decommission() throws InterruptedException
    {
        if (!tokenMetadata.isMember(FBUtilities.getBroadcastAddress()))
            throw new UnsupportedOperationException("local node is not a member of the token ring yet");
        if (tokenMetadata.cloneAfterAllLeft().sortedTokens().size() < 2)
            throw new UnsupportedOperationException("no other normal nodes in the ring; decommission would be pointless");

        PendingRangeCalculatorService.instance.blockUntilFinished();
        for (String keyspaceName : Schema.instance.getNonSystemKeyspaces())
        {
            if (tokenMetadata.getPendingRanges(keyspaceName, FBUtilities.getBroadcastAddress()).size() > 0)
                throw new UnsupportedOperationException("data is currently moving to this node; unable to leave the ring");
        }

        if (logger.isDebugEnabled())
            logger.debug("DECOMMISSIONING");
        startLeaving();
        long timeout = Math.max(RING_DELAY, BatchlogManager.instance.getBatchlogTimeout());
        setMode(Mode.LEAVING, "sleeping " + timeout + " ms for batch processing and pending range setup", true);
        Thread.sleep(timeout);

        Runnable finishLeaving = new Runnable()
        {
            public void run()
            {
                shutdownClientServers();
                Gossiper.instance.stop();
                try {
                    MessagingService.instance().shutdown();
                } catch (IOError ioe) {
                    logger.info("failed to shutdown message service: {}", ioe);
                }
                StageManager.shutdownNow();
                SystemKeyspace.setBootstrapState(SystemKeyspace.BootstrapState.DECOMMISSIONED);
                setMode(Mode.DECOMMISSIONED, true);
                // let op be responsible for killing the process
            }
        };
        unbootstrap(finishLeaving);
    }

    private void leaveRing()
    {
        SystemKeyspace.setBootstrapState(SystemKeyspace.BootstrapState.NEEDS_BOOTSTRAP);
        tokenMetadata.removeEndpoint(FBUtilities.getBroadcastAddress());
        PendingRangeCalculatorService.instance.update();

        Gossiper.instance.addLocalApplicationState(ApplicationState.STATUS, valueFactory.left(getLocalTokens(),Gossiper.computeExpireTime()));
        int delay = Math.max(RING_DELAY, Gossiper.intervalInMillis * 2);
        logger.info("Announcing that I have left the ring for {}ms", delay);
        Uninterruptibles.sleepUninterruptibly(delay, TimeUnit.MILLISECONDS);
    }

    private void unbootstrap(Runnable onFinish)
    {
        Map<String, Multimap<Range<Token>, InetAddress>> rangesToStream = new HashMap<>();

        for (String keyspaceName : Schema.instance.getNonSystemKeyspaces())
        {
            Multimap<Range<Token>, InetAddress> rangesMM = getChangedRangesForLeaving(keyspaceName, FBUtilities.getBroadcastAddress());

            if (logger.isDebugEnabled())
                logger.debug("Ranges needing transfer are [{}]", StringUtils.join(rangesMM.keySet(), ","));

            rangesToStream.put(keyspaceName, rangesMM);
        }

        setMode(Mode.LEAVING, "replaying batch log and streaming data to other nodes", true);

        // Start with BatchLog replay, which may create hints but no writes since this is no longer a valid endpoint.
        Future<?> batchlogReplay = BatchlogManager.instance.startBatchlogReplay();
        Future<StreamState> streamSuccess = streamRanges(rangesToStream);

        // Wait for batch log to complete before streaming hints.
        logger.debug("waiting for batch log processing.");
        try
        {
            batchlogReplay.get();
        }
        catch (ExecutionException | InterruptedException e)
        {
            throw new RuntimeException(e);
        }

        setMode(Mode.LEAVING, "streaming hints to other nodes", true);

        Future<StreamState> hintsSuccess = streamHints();

        // wait for the transfer runnables to signal the latch.
        logger.debug("waiting for stream acks.");
        try
        {
            streamSuccess.get();
            hintsSuccess.get();
        }
        catch (ExecutionException | InterruptedException e)
        {
            throw new RuntimeException(e);
        }
        logger.debug("stream acks all received.");
        leaveRing();
        onFinish.run();
    }

    private Future<StreamState> streamHints()
    {
        // StreamPlan will not fail if there are zero files to transfer, so flush anyway (need to get any in-memory hints, as well)
        ColumnFamilyStore hintsCF = Keyspace.open(SystemKeyspace.NAME).getColumnFamilyStore(SystemKeyspace.HINTS);
        FBUtilities.waitOnFuture(hintsCF.forceFlush());

        // gather all live nodes in the cluster that aren't also leaving
        List<InetAddress> candidates = new ArrayList<>(StorageService.instance.getTokenMetadata().cloneAfterAllLeft().getAllEndpoints());
        candidates.remove(FBUtilities.getBroadcastAddress());
        for (Iterator<InetAddress> iter = candidates.iterator(); iter.hasNext(); )
        {
            InetAddress address = iter.next();
            if (!FailureDetector.instance.isAlive(address))
                iter.remove();
        }

        if (candidates.isEmpty())
        {
            logger.warn("Unable to stream hints since no live endpoints seen");
            return Futures.immediateFuture(null);
        }
        else
        {
            // stream to the closest peer as chosen by the snitch
            DatabaseDescriptor.getEndpointSnitch().sortByProximity(FBUtilities.getBroadcastAddress(), candidates);
            InetAddress hintsDestinationHost = candidates.get(0);
            InetAddress preferred = SystemKeyspace.getPreferredIP(hintsDestinationHost);

            // stream all hints -- range list will be a singleton of "the entire ring"
            Token token = StorageService.getPartitioner().getMinimumToken();
            List<Range<Token>> ranges = Collections.singletonList(new Range<>(token, token));

            return new StreamPlan("Hints").transferRanges(hintsDestinationHost,
                                                          preferred,
                                                          SystemKeyspace.NAME,
                                                          ranges,
                                                          SystemKeyspace.HINTS)
                                          .execute();
        }
    }

    public void move(String newToken) throws IOException
    {
        try
        {
            getPartitioner().getTokenFactory().validate(newToken);
        }
        catch (ConfigurationException e)
        {
            throw new IOException(e.getMessage());
        }
        move(getPartitioner().getTokenFactory().fromString(newToken));
    }

    /**
     * move the node to new token or find a new token to boot to according to load
     *
     * @param newToken new token to boot to, or if null, find balanced token to boot to
     *
     * @throws IOException on any I/O operation error
     */
    private void move(Token newToken) throws IOException
    {
        if (newToken == null)
            throw new IOException("Can't move to the undefined (null) token.");

        if (tokenMetadata.sortedTokens().contains(newToken))
            throw new IOException("target token " + newToken + " is already owned by another node.");

        // address of the current node
        InetAddress localAddress = FBUtilities.getBroadcastAddress();

        // This doesn't make any sense in a vnodes environment.
        if (getTokenMetadata().getTokens(localAddress).size() > 1)
        {
            logger.error("Invalid request to move(Token); This node has more than one token and cannot be moved thusly.");
            throw new UnsupportedOperationException("This node has more than one token and cannot be moved thusly.");
        }

        List<String> keyspacesToProcess = Schema.instance.getNonSystemKeyspaces();

        PendingRangeCalculatorService.instance.blockUntilFinished();
        // checking if data is moving to this node
        for (String keyspaceName : keyspacesToProcess)
        {
            if (tokenMetadata.getPendingRanges(keyspaceName, localAddress).size() > 0)
                throw new UnsupportedOperationException("data is currently moving to this node; unable to leave the ring");
        }

        Gossiper.instance.addLocalApplicationState(ApplicationState.STATUS, valueFactory.moving(newToken));
        setMode(Mode.MOVING, String.format("Moving %s from %s to %s.", localAddress, getLocalTokens().iterator().next(), newToken), true);

        setMode(Mode.MOVING, String.format("Sleeping %s ms before start streaming/fetching ranges", RING_DELAY), true);
        Uninterruptibles.sleepUninterruptibly(RING_DELAY, TimeUnit.MILLISECONDS);

        RangeRelocator relocator = new RangeRelocator(Collections.singleton(newToken), keyspacesToProcess);

        if (relocator.streamsNeeded())
        {
            setMode(Mode.MOVING, "fetching new ranges and streaming old ranges", true);
            try
            {
                relocator.stream().get();
            }
            catch (ExecutionException | InterruptedException e)
            {
                throw new RuntimeException("Interrupted while waiting for stream/fetch ranges to finish: " + e.getMessage());
            }
        }
        else
        {
            setMode(Mode.MOVING, "No ranges to fetch/stream", true);
        }

        setTokens(Collections.singleton(newToken)); // setting new token as we have everything settled

        if (logger.isDebugEnabled())
            logger.debug("Successfully moved to new token {}", getLocalTokens().iterator().next());
    }

    private class RangeRelocator
    {
        private final StreamPlan streamPlan = new StreamPlan("Relocation");

        private RangeRelocator(Collection<Token> tokens, List<String> keyspaceNames)
        {
            calculateToFromStreams(tokens, keyspaceNames);
        }

        private void calculateToFromStreams(Collection<Token> newTokens, List<String> keyspaceNames)
        {
            InetAddress localAddress = FBUtilities.getBroadcastAddress();
            IEndpointSnitch snitch = DatabaseDescriptor.getEndpointSnitch();
            TokenMetadata tokenMetaCloneAllSettled = tokenMetadata.cloneAfterAllSettled();
            // clone to avoid concurrent modification in calculateNaturalEndpoints
            TokenMetadata tokenMetaClone = tokenMetadata.cloneOnlyTokenMap();

            for (String keyspace : keyspaceNames)
            {
                logger.debug("Calculating ranges to stream and request for keyspace {}", keyspace);
                for (Token newToken : newTokens)
                {
                    // replication strategy of the current keyspace (aka table)
                    AbstractReplicationStrategy strategy = Keyspace.open(keyspace).getReplicationStrategy();

                    // getting collection of the currently used ranges by this keyspace
                    Collection<Range<Token>> currentRanges = getRangesForEndpoint(keyspace, localAddress);
                    // collection of ranges which this node will serve after move to the new token
                    Collection<Range<Token>> updatedRanges = strategy.getPendingAddressRanges(tokenMetaClone, newToken, localAddress);

                    // ring ranges and endpoints associated with them
                    // this used to determine what nodes should we ping about range data
                    Multimap<Range<Token>, InetAddress> rangeAddresses = strategy.getRangeAddresses(tokenMetaClone);

                    // calculated parts of the ranges to request/stream from/to nodes in the ring
                    Pair<Set<Range<Token>>, Set<Range<Token>>> rangesPerKeyspace = calculateStreamAndFetchRanges(currentRanges, updatedRanges);

                    /**
                     * In this loop we are going through all ranges "to fetch" and determining
                     * nodes in the ring responsible for data we are interested in
                     */
                    Multimap<Range<Token>, InetAddress> rangesToFetchWithPreferredEndpoints = ArrayListMultimap.create();
                    for (Range<Token> toFetch : rangesPerKeyspace.right)
                    {
                        for (Range<Token> range : rangeAddresses.keySet())
                        {
                            if (range.contains(toFetch))
                            {
                                List<InetAddress> endpoints = null;

                                if (useStrictConsistency)
                                {
                                    Set<InetAddress> oldEndpoints = Sets.newHashSet(rangeAddresses.get(range));
                                    Set<InetAddress> newEndpoints = Sets.newHashSet(strategy.calculateNaturalEndpoints(toFetch.right, tokenMetaCloneAllSettled));

                                    //Due to CASSANDRA-5953 we can have a higher RF then we have endpoints.
                                    //So we need to be careful to only be strict when endpoints == RF
                                    if (oldEndpoints.size() == strategy.getReplicationFactor())
                                    {
                                        oldEndpoints.removeAll(newEndpoints);

                                        //No relocation required
                                        if (oldEndpoints.isEmpty())
                                            continue;

                                        assert oldEndpoints.size() == 1 : "Expected 1 endpoint but found " + oldEndpoints.size();
                                    }

                                    endpoints = Lists.newArrayList(oldEndpoints.iterator().next());
                                }
                                else
                                {
                                    endpoints = snitch.getSortedListByProximity(localAddress, rangeAddresses.get(range));
                                }

                                // storing range and preferred endpoint set
                                rangesToFetchWithPreferredEndpoints.putAll(toFetch, endpoints);
                            }
                        }

                        Collection<InetAddress> addressList = rangesToFetchWithPreferredEndpoints.get(toFetch);
                        if (addressList == null || addressList.isEmpty())
                            continue;

                        if (useStrictConsistency)
                        {
                            if (addressList.size() > 1)
                                throw new IllegalStateException("Multiple strict sources found for " + toFetch);

                            InetAddress sourceIp = addressList.iterator().next();
                            if (Gossiper.instance.isEnabled() && !Gossiper.instance.getEndpointStateForEndpoint(sourceIp).isAlive())
                                throw new RuntimeException("A node required to move the data consistently is down ("+sourceIp+").  If you wish to move the data from a potentially inconsistent replica, restart the node with -Dcassandra.consistent.rangemovement=false");
                        }
                    }

                    // calculating endpoints to stream current ranges to if needed
                    // in some situations node will handle current ranges as part of the new ranges
                    Multimap<InetAddress, Range<Token>> endpointRanges = HashMultimap.create();
                    for (Range<Token> toStream : rangesPerKeyspace.left)
                    {
                        Set<InetAddress> currentEndpoints = ImmutableSet.copyOf(strategy.calculateNaturalEndpoints(toStream.right, tokenMetaClone));
                        Set<InetAddress> newEndpoints = ImmutableSet.copyOf(strategy.calculateNaturalEndpoints(toStream.right, tokenMetaCloneAllSettled));
                        logger.debug("Range: {} Current endpoints: {} New endpoints: {}", toStream, currentEndpoints, newEndpoints);
                        for (InetAddress address : Sets.difference(newEndpoints, currentEndpoints))
                        {
                            logger.debug("Range {} has new owner {}", toStream, address);
                            endpointRanges.put(address, toStream);
                        }
                    }

                    // stream ranges
                    for (InetAddress address : endpointRanges.keySet())
                    {
                        logger.debug("Will stream range {} of keyspace {} to endpoint {}", endpointRanges.get(address), keyspace, address);
                        InetAddress preferred = SystemKeyspace.getPreferredIP(address);
                        streamPlan.transferRanges(address, preferred, keyspace, endpointRanges.get(address));
                    }

                    // stream requests
                    Multimap<InetAddress, Range<Token>> workMap = RangeStreamer.getWorkMap(rangesToFetchWithPreferredEndpoints, keyspace, FailureDetector.instance);
                    for (InetAddress address : workMap.keySet())
                    {
                        logger.debug("Will request range {} of keyspace {} from endpoint {}", workMap.get(address), keyspace, address);
                        InetAddress preferred = SystemKeyspace.getPreferredIP(address);
                        streamPlan.requestRanges(address, preferred, keyspace, workMap.get(address));
                    }

                    logger.debug("Keyspace {}: work map {}.", keyspace, workMap);
                }
            }
        }

        public Future<StreamState> stream()
        {
            return streamPlan.execute();
        }

        public boolean streamsNeeded()
        {
            return !streamPlan.isEmpty();
        }
    }

    /**
     * Get the status of a token removal.
     */
    public String getRemovalStatus()
    {
        if (removingNode == null) {
            return "No token removals in process.";
        }
        return String.format("Removing token (%s). Waiting for replication confirmation from [%s].",
                             tokenMetadata.getToken(removingNode),
                             StringUtils.join(replicatingNodes, ","));
    }

    /**
     * Force a remove operation to complete. This may be necessary if a remove operation
     * blocks forever due to node/stream failure. removeToken() must be called
     * first, this is a last resort measure.  No further attempt will be made to restore replicas.
     */
    public void forceRemoveCompletion()
    {
        if (!replicatingNodes.isEmpty()  || !tokenMetadata.getLeavingEndpoints().isEmpty())
        {
            logger.warn("Removal not confirmed for for {}", StringUtils.join(this.replicatingNodes, ","));
            for (InetAddress endpoint : tokenMetadata.getLeavingEndpoints())
            {
                UUID hostId = tokenMetadata.getHostId(endpoint);
                Gossiper.instance.advertiseTokenRemoved(endpoint, hostId);
                excise(tokenMetadata.getTokens(endpoint), endpoint);
            }
            replicatingNodes.clear();
            removingNode = null;
        }
        else
        {
            logger.warn("No tokens to force removal on, call 'removenode' first");
        }
    }

    /**
     * Remove a node that has died, attempting to restore the replica count.
     * If the node is alive, decommission should be attempted.  If decommission
     * fails, then removeToken should be called.  If we fail while trying to
     * restore the replica count, finally forceRemoveCompleteion should be
     * called to forcibly remove the node without regard to replica count.
     *
     * @param hostIdString token for the node
     */
    public void removeNode(String hostIdString)
    {
        InetAddress myAddress = FBUtilities.getBroadcastAddress();
        UUID localHostId = tokenMetadata.getHostId(myAddress);
        UUID hostId = UUID.fromString(hostIdString);
        InetAddress endpoint = tokenMetadata.getEndpointForHostId(hostId);

        if (endpoint == null)
            throw new UnsupportedOperationException("Host ID not found.");

        Collection<Token> tokens = tokenMetadata.getTokens(endpoint);

        if (endpoint.equals(myAddress))
             throw new UnsupportedOperationException("Cannot remove self");

        if (Gossiper.instance.getLiveMembers().contains(endpoint))
            throw new UnsupportedOperationException("Node " + endpoint + " is alive and owns this ID. Use decommission command to remove it from the ring");

        // A leaving endpoint that is dead is already being removed.
        if (tokenMetadata.isLeaving(endpoint))
            logger.warn("Node {} is already being removed, continuing removal anyway", endpoint);

        if (!replicatingNodes.isEmpty())
            throw new UnsupportedOperationException("This node is already processing a removal. Wait for it to complete, or use 'removenode force' if this has failed.");

        // Find the endpoints that are going to become responsible for data
        for (String keyspaceName : Schema.instance.getNonSystemKeyspaces())
        {
            // if the replication factor is 1 the data is lost so we shouldn't wait for confirmation
            if (Keyspace.open(keyspaceName).getReplicationStrategy().getReplicationFactor() == 1)
                continue;

            // get all ranges that change ownership (that is, a node needs
            // to take responsibility for new range)
            Multimap<Range<Token>, InetAddress> changedRanges = getChangedRangesForLeaving(keyspaceName, endpoint);
            IFailureDetector failureDetector = FailureDetector.instance;
            for (InetAddress ep : changedRanges.values())
            {
                if (failureDetector.isAlive(ep))
                    replicatingNodes.add(ep);
                else
                    logger.warn("Endpoint {} is down and will not receive data for re-replication of {}", ep, endpoint);
            }
        }
        removingNode = endpoint;

        tokenMetadata.addLeavingEndpoint(endpoint);
        PendingRangeCalculatorService.instance.update();

        // the gossiper will handle spoofing this node's state to REMOVING_TOKEN for us
        // we add our own token so other nodes to let us know when they're done
        Gossiper.instance.advertiseRemoving(endpoint, hostId, localHostId);

        // kick off streaming commands
        restoreReplicaCount(endpoint, myAddress);

        // wait for ReplicationFinishedVerbHandler to signal we're done
        while (!replicatingNodes.isEmpty())
        {
            Uninterruptibles.sleepUninterruptibly(100, TimeUnit.MILLISECONDS);
        }

        excise(tokens, endpoint);

        // gossiper will indicate the token has left
        Gossiper.instance.advertiseTokenRemoved(endpoint, hostId);

        replicatingNodes.clear();
        removingNode = null;
    }

    public void confirmReplication(InetAddress node)
    {
        // replicatingNodes can be empty in the case where this node used to be a removal coordinator,
        // but restarted before all 'replication finished' messages arrived. In that case, we'll
        // still go ahead and acknowledge it.
        if (!replicatingNodes.isEmpty())
        {
            replicatingNodes.remove(node);
        }
        else
        {
            logger.info("Received unexpected REPLICATION_FINISHED message from {}. Was this node recently a removal coordinator?", node);
        }
    }

    public String getOperationMode()
    {
        return operationMode.toString();
    }

    public boolean isStarting()
    {
        return operationMode == Mode.STARTING;
    }

    public String getDrainProgress()
    {
        return String.format("Drained %s/%s ColumnFamilies", remainingCFs, totalCFs);
    }

    /**
     * Shuts node off to writes, empties memtables and the commit log.
     * There are two differences between drain and the normal shutdown hook:
     * - Drain waits for in-progress streaming to complete
     * - Drain flushes *all* columnfamilies (shutdown hook only flushes non-durable CFs)
     */
    public synchronized void drain() throws IOException, InterruptedException, ExecutionException
    {
        inShutdownHook = true;
        
        ExecutorService counterMutationStage = StageManager.getStage(Stage.COUNTER_MUTATION);
        ExecutorService mutationStage = StageManager.getStage(Stage.MUTATION);
        if (mutationStage.isTerminated() && counterMutationStage.isTerminated())
        {
            logger.warn("Cannot drain node (did it already happen?)");
            return;
        }
        setMode(Mode.DRAINING, "starting drain process", true);
        shutdownClientServers();
        ScheduledExecutors.optionalTasks.shutdown();
        Gossiper.instance.stop();

        setMode(Mode.DRAINING, "shutting down MessageService", false);
        MessagingService.instance().shutdown();

        setMode(Mode.DRAINING, "clearing mutation stage", false);
        counterMutationStage.shutdown();
        mutationStage.shutdown();
        counterMutationStage.awaitTermination(3600, TimeUnit.SECONDS);
        mutationStage.awaitTermination(3600, TimeUnit.SECONDS);

        StorageProxy.instance.verifyNoHintsInProgress();

        setMode(Mode.DRAINING, "flushing column families", false);
        // count CFs first, since forceFlush could block for the flushWriter to get a queue slot empty
        totalCFs = 0;
        for (Keyspace keyspace : Keyspace.nonSystem())
            totalCFs += keyspace.getColumnFamilyStores().size();
        remainingCFs = totalCFs;
        // flush
        List<Future<?>> flushes = new ArrayList<>();
        for (Keyspace keyspace : Keyspace.nonSystem())
        {
            for (ColumnFamilyStore cfs : keyspace.getColumnFamilyStores())
                flushes.add(cfs.forceFlush());
        }
        // wait for the flushes.
        // TODO this is a godawful way to track progress, since they flush in parallel.  a long one could
        // thus make several short ones "instant" if we wait for them later.
        for (Future f : flushes)
        {
            FBUtilities.waitOnFuture(f);
            remainingCFs--;
        }
        // flush the system ones after all the rest are done, just in case flushing modifies any system state
        // like CASSANDRA-5151. don't bother with progress tracking since system data is tiny.
        flushes.clear();
        for (Keyspace keyspace : Keyspace.system())
        {
            for (ColumnFamilyStore cfs : keyspace.getColumnFamilyStores())
                flushes.add(cfs.forceFlush());
        }
        FBUtilities.waitOnFutures(flushes);

        BatchlogManager.shutdown();

        // whilst we've flushed all the CFs, which will have recycled all completed segments, we want to ensure
        // there are no segments to replay, so we force the recycling of any remaining (should be at most one)
        CommitLog.instance.forceRecycleAllSegments();

        ColumnFamilyStore.shutdownPostFlushExecutor();

        CommitLog.instance.shutdownBlocking();

        // wait for miscellaneous tasks like sstable and commitlog segment deletion
        ScheduledExecutors.nonPeriodicTasks.shutdown();
        if (!ScheduledExecutors.nonPeriodicTasks.awaitTermination(1, TimeUnit.MINUTES))
            logger.warn("Miscellaneous task executor still busy after one minute; proceeding with shutdown");

        setMode(Mode.DRAINED, true);
    }

    // Never ever do this at home. Used by tests.
    IPartitioner setPartitionerUnsafe(IPartitioner newPartitioner)
    {
        IPartitioner oldPartitioner = DatabaseDescriptor.getPartitioner();
        DatabaseDescriptor.setPartitioner(newPartitioner);
        valueFactory = new VersionedValue.VersionedValueFactory(getPartitioner());
        return oldPartitioner;
    }

    TokenMetadata setTokenMetadataUnsafe(TokenMetadata tmd)
    {
        TokenMetadata old = tokenMetadata;
        tokenMetadata = tmd;
        return old;
    }

    public void truncate(String keyspace, String columnFamily) throws TimeoutException, IOException
    {
        try
        {
            StorageProxy.truncateBlocking(keyspace, columnFamily);
        }
        catch (UnavailableException e)
        {
            throw new IOException(e.getMessage());
        }
    }

    public Map<InetAddress, Float> getOwnership()
    {
        List<Token> sortedTokens = tokenMetadata.sortedTokens();
        // describeOwnership returns tokens in an unspecified order, let's re-order them
        Map<Token, Float> tokenMap = new TreeMap<Token, Float>(getPartitioner().describeOwnership(sortedTokens));
        Map<InetAddress, Float> nodeMap = new LinkedHashMap<>();
        for (Map.Entry<Token, Float> entry : tokenMap.entrySet())
        {
            InetAddress endpoint = tokenMetadata.getEndpoint(entry.getKey());
            Float tokenOwnership = entry.getValue();
            if (nodeMap.containsKey(endpoint))
                nodeMap.put(endpoint, nodeMap.get(endpoint) + tokenOwnership);
            else
                nodeMap.put(endpoint, tokenOwnership);
        }
        return nodeMap;
    }

    /**
     * Calculates ownership. If there are multiple DC's and the replication strategy is DC aware then ownership will be
     * calculated per dc, i.e. each DC will have total ring ownership divided amongst its nodes. Without replication
     * total ownership will be a multiple of the number of DC's and this value will then go up within each DC depending
     * on the number of replicas within itself. For DC unaware replication strategies, ownership without replication
     * will be 100%.
     *
     * @throws IllegalStateException when node is not configured properly.
     */
    public LinkedHashMap<InetAddress, Float> effectiveOwnership(String keyspace) throws IllegalStateException
    {
    	
    	if (keyspace != null)
    	{
    		Keyspace keyspaceInstance = Schema.instance.getKeyspaceInstance(keyspace);
			if(keyspaceInstance == null)
				throw new IllegalArgumentException("The keyspace " + keyspace + ", does not exist");
    		
    		if(keyspaceInstance.getReplicationStrategy() instanceof LocalStrategy)
				throw new IllegalStateException("Ownership values for keyspaces with LocalStrategy are meaningless");
    	}
    	else
    	{
        	List<String> nonSystemKeyspaces = Schema.instance.getNonSystemKeyspaces();
        	
        	//system_traces is a non-system keyspace however it needs to be counted as one for this process
        	int specialTableCount = 0;
        	if (nonSystemKeyspaces.contains("system_traces"))
			{
        		specialTableCount += 1;
			}
        	if (nonSystemKeyspaces.size() > specialTableCount) 	   		
        		throw new IllegalStateException("Non-system keyspaces don't have the same replication settings, effective ownership information is meaningless");
        	
        	keyspace = "system_traces";
    	}
    	
        TokenMetadata metadata = tokenMetadata.cloneOnlyTokenMap();

        Collection<Collection<InetAddress>> endpointsGroupedByDc = new ArrayList<>();
        // mapping of dc's to nodes, use sorted map so that we get dcs sorted
        SortedMap<String, Collection<InetAddress>> sortedDcsToEndpoints = new TreeMap<>();
        sortedDcsToEndpoints.putAll(metadata.getTopology().getDatacenterEndpoints().asMap());
        for (Collection<InetAddress> endpoints : sortedDcsToEndpoints.values())
            endpointsGroupedByDc.add(endpoints);

        Map<Token, Float> tokenOwnership = getPartitioner().describeOwnership(tokenMetadata.sortedTokens());
        LinkedHashMap<InetAddress, Float> finalOwnership = Maps.newLinkedHashMap();

        // calculate ownership per dc
        for (Collection<InetAddress> endpoints : endpointsGroupedByDc)
        {
            // calculate the ownership with replication and add the endpoint to the final ownership map
            for (InetAddress endpoint : endpoints)
            {
                float ownership = 0.0f;
                for (Range<Token> range : getRangesForEndpoint(keyspace, endpoint))
                {
                    if (tokenOwnership.containsKey(range.right))
                        ownership += tokenOwnership.get(range.right);
                }
                finalOwnership.put(endpoint, ownership);
            }
        }
        return finalOwnership;
    }

    public List<String> getKeyspaces()
    {
        List<String> keyspaceNamesList = new ArrayList<>(Schema.instance.getKeyspaces());
        return Collections.unmodifiableList(keyspaceNamesList);
    }

    public List<String> getNonSystemKeyspaces()
    {
        List<String> keyspaceNamesList = new ArrayList<>(Schema.instance.getNonSystemKeyspaces());
        return Collections.unmodifiableList(keyspaceNamesList);
    }

    public void updateSnitch(String epSnitchClassName, Boolean dynamic, Integer dynamicUpdateInterval, Integer dynamicResetInterval, Double dynamicBadnessThreshold) throws ClassNotFoundException
    {
        IEndpointSnitch oldSnitch = DatabaseDescriptor.getEndpointSnitch();

        // new snitch registers mbean during construction
        IEndpointSnitch newSnitch;
        try
        {
            newSnitch = FBUtilities.construct(epSnitchClassName, "snitch");
        }
        catch (ConfigurationException e)
        {
            throw new ClassNotFoundException(e.getMessage());
        }
        if (dynamic)
        {
            DatabaseDescriptor.setDynamicUpdateInterval(dynamicUpdateInterval);
            DatabaseDescriptor.setDynamicResetInterval(dynamicResetInterval);
            DatabaseDescriptor.setDynamicBadnessThreshold(dynamicBadnessThreshold);
            newSnitch = new DynamicEndpointSnitch(newSnitch);
        }

        // point snitch references to the new instance
        DatabaseDescriptor.setEndpointSnitch(newSnitch);
        for (String ks : Schema.instance.getKeyspaces())
        {
            Keyspace.open(ks).getReplicationStrategy().snitch = newSnitch;
        }

        if (oldSnitch instanceof DynamicEndpointSnitch)
            ((DynamicEndpointSnitch)oldSnitch).unregisterMBean();
    }

    /**
     * Seed data to the endpoints that will be responsible for it at the future
     *
     * @param rangesToStreamByKeyspace keyspaces and data ranges with endpoints included for each
     * @return async Future for whether stream was success
     */
    private Future<StreamState> streamRanges(Map<String, Multimap<Range<Token>, InetAddress>> rangesToStreamByKeyspace)
    {
        // First, we build a list of ranges to stream to each host, per table
        Map<String, Map<InetAddress, List<Range<Token>>>> sessionsToStreamByKeyspace = new HashMap<>();
        for (Map.Entry<String, Multimap<Range<Token>, InetAddress>> entry : rangesToStreamByKeyspace.entrySet())
        {
            String keyspace = entry.getKey();
            Multimap<Range<Token>, InetAddress> rangesWithEndpoints = entry.getValue();

            if (rangesWithEndpoints.isEmpty())
                continue;

            Map<InetAddress, List<Range<Token>>> rangesPerEndpoint = new HashMap<>();
            for (Map.Entry<Range<Token>, InetAddress> endPointEntry : rangesWithEndpoints.entries())
            {
                Range<Token> range = endPointEntry.getKey();
                InetAddress endpoint = endPointEntry.getValue();

                List<Range<Token>> curRanges = rangesPerEndpoint.get(endpoint);
                if (curRanges == null)
                {
                    curRanges = new LinkedList<>();
                    rangesPerEndpoint.put(endpoint, curRanges);
                }
                curRanges.add(range);
            }

            sessionsToStreamByKeyspace.put(keyspace, rangesPerEndpoint);
        }

        StreamPlan streamPlan = new StreamPlan("Unbootstrap");
        for (Map.Entry<String, Map<InetAddress, List<Range<Token>>>> entry : sessionsToStreamByKeyspace.entrySet())
        {
            String keyspaceName = entry.getKey();
            Map<InetAddress, List<Range<Token>>> rangesPerEndpoint = entry.getValue();

            for (Map.Entry<InetAddress, List<Range<Token>>> rangesEntry : rangesPerEndpoint.entrySet())
            {
                List<Range<Token>> ranges = rangesEntry.getValue();
                InetAddress newEndpoint = rangesEntry.getKey();
                InetAddress preferred = SystemKeyspace.getPreferredIP(newEndpoint);

                // TODO each call to transferRanges re-flushes, this is potentially a lot of waste
                streamPlan.transferRanges(newEndpoint, preferred, keyspaceName, ranges);
            }
        }
        return streamPlan.execute();
    }

    /**
     * Calculate pair of ranges to stream/fetch for given two range collections
     * (current ranges for keyspace and ranges after move to new token)
     *
     * @param current collection of the ranges by current token
     * @param updated collection of the ranges after token is changed
     * @return pair of ranges to stream/fetch for given current and updated range collections
     */
    public Pair<Set<Range<Token>>, Set<Range<Token>>> calculateStreamAndFetchRanges(Collection<Range<Token>> current, Collection<Range<Token>> updated)
    {
        Set<Range<Token>> toStream = new HashSet<>();
        Set<Range<Token>> toFetch  = new HashSet<>();


        for (Range<Token> r1 : current)
        {
            boolean intersect = false;
            for (Range<Token> r2 : updated)
            {
                if (r1.intersects(r2))
                {
                    // adding difference ranges to fetch from a ring
                    toStream.addAll(r1.subtract(r2));
                    intersect = true;
                }
            }
            if (!intersect)
            {
                toStream.add(r1); // should seed whole old range
            }
        }

        for (Range<Token> r2 : updated)
        {
            boolean intersect = false;
            for (Range<Token> r1 : current)
            {
                if (r2.intersects(r1))
                {
                    // adding difference ranges to fetch from a ring
                    toFetch.addAll(r2.subtract(r1));
                    intersect = true;
                }
            }
            if (!intersect)
            {
                toFetch.add(r2); // should fetch whole old range
            }
        }

        return Pair.create(toStream, toFetch);
    }

    public void bulkLoad(String directory)
    {
        try
        {
            bulkLoadInternal(directory).get();
        }
        catch (Exception e)
        {
            throw new RuntimeException(e);
        }
    }

    public String bulkLoadAsync(String directory)
    {
        return bulkLoadInternal(directory).planId.toString();
    }

    private StreamResultFuture bulkLoadInternal(String directory)
    {
        File dir = new File(directory);

        if (!dir.exists() || !dir.isDirectory())
            throw new IllegalArgumentException("Invalid directory " + directory);

        SSTableLoader.Client client = new SSTableLoader.Client()
        {
            private String keyspace;

            public void init(String keyspace)
            {
                this.keyspace = keyspace;
                try
                {
                    setPartitioner(DatabaseDescriptor.getPartitioner());
                    for (Map.Entry<Range<Token>, List<InetAddress>> entry : StorageService.instance.getRangeToAddressMap(keyspace).entrySet())
                    {
                        Range<Token> range = entry.getKey();
                        for (InetAddress endpoint : entry.getValue())
                            addRangeForEndpoint(range, endpoint);
                    }
                }
                catch (Exception e)
                {
                    throw new RuntimeException(e);
                }
            }

            public CFMetaData getTableMetadata(String tableName)
            {
                return Schema.instance.getCFMetaData(keyspace, tableName);
            }
        };

        return new SSTableLoader(dir, client, new OutputHandler.LogOutput()).stream();
    }

    public void rescheduleFailedDeletions()
    {
        SSTableDeletingTask.rescheduleFailedTasks();
    }

    /**
     * #{@inheritDoc}
     */
    public void loadNewSSTables(String ksName, String cfName)
    {
        ColumnFamilyStore.loadNewSSTables(ksName, cfName);
    }

    /**
     * #{@inheritDoc}
     */
    public List<String> sampleKeyRange() // do not rename to getter - see CASSANDRA-4452 for details
    {
        List<DecoratedKey> keys = new ArrayList<>();
        for (Keyspace keyspace : Keyspace.nonSystem())
        {
            for (Range<Token> range : getPrimaryRangesForEndpoint(keyspace.getName(), FBUtilities.getBroadcastAddress()))
                keys.addAll(keySamples(keyspace.getColumnFamilyStores(), range));
        }

        List<String> sampledKeys = new ArrayList<>(keys.size());
        for (DecoratedKey key : keys)
            sampledKeys.add(key.getToken().toString());
        return sampledKeys;
    }

    public void rebuildSecondaryIndex(String ksName, String cfName, String... idxNames)
    {
        ColumnFamilyStore.rebuildSecondaryIndex(ksName, cfName, idxNames);
    }

    public void resetLocalSchema() throws IOException
    {
        MigrationManager.resetLocalSchema();
    }

    public void setTraceProbability(double probability)
    {
        this.traceProbability = probability;
    }

    public double getTraceProbability()
    {
        return traceProbability;
    }

    public void disableAutoCompaction(String ks, String... columnFamilies) throws IOException
    {
        for (ColumnFamilyStore cfs : getValidColumnFamilies(true, true, ks, columnFamilies))
        {
            cfs.disableAutoCompaction();
        }
    }

    public void enableAutoCompaction(String ks, String... columnFamilies) throws IOException
    {
        for (ColumnFamilyStore cfs : getValidColumnFamilies(true, true, ks, columnFamilies))
        {
            cfs.enableAutoCompaction();
        }
    }

    /** Returns the name of the cluster */
    public String getClusterName()
    {
        return DatabaseDescriptor.getClusterName();
    }

    /** Returns the cluster partitioner */
    public String getPartitionerName()
    {
        return DatabaseDescriptor.getPartitionerName();
    }

    public int getTombstoneWarnThreshold()
    {
        return DatabaseDescriptor.getTombstoneWarnThreshold();
    }

    public void setTombstoneWarnThreshold(int threshold)
    {
        DatabaseDescriptor.setTombstoneWarnThreshold(threshold);
    }

    public int getTombstoneFailureThreshold()
    {
        return DatabaseDescriptor.getTombstoneFailureThreshold();
    }

    public void setTombstoneFailureThreshold(int threshold)
    {
        DatabaseDescriptor.setTombstoneFailureThreshold(threshold);
    }

    public int getBatchSizeFailureThreshold()
    {
        return DatabaseDescriptor.getBatchSizeFailThresholdInKB();
    }

    public void setBatchSizeFailureThreshold(int threshold)
    {
        DatabaseDescriptor.setBatchSizeFailThresholdInKB(threshold);
    }

    public void setHintedHandoffThrottleInKB(int throttleInKB)
    {
        DatabaseDescriptor.setHintedHandoffThrottleInKB(throttleInKB);
        logger.info(String.format("Updated hinted_handoff_throttle_in_kb to %d", throttleInKB));
    }

}


File: test/long/org/apache/cassandra/db/commitlog/CommitLogStressTest.java
package org.apache.cassandra.db.commitlog;
/*
 *
 * Licensed to the Apache Software Foundation (ASF) under one
 * or more contributor license agreements.  See the NOTICE file
 * distributed with this work for additional information
 * regarding copyright ownership.  The ASF licenses this file
 * to you under the Apache License, Version 2.0 (the
 * "License"); you may not use this file except in compliance
 * with the License.  You may obtain a copy of the License at
 *
 *   http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing,
 * software distributed under the License is distributed on an
 * "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY
 * KIND, either express or implied.  See the License for the
 * specific language governing permissions and limitations
 * under the License.
 *
 */


import java.io.DataInputStream;
import java.io.File;
import java.io.FileInputStream;
import java.io.FileNotFoundException;
import java.io.IOException;
import java.nio.ByteBuffer;
import java.nio.charset.StandardCharsets;
import java.util.ArrayList;
import java.util.Collection;
import java.util.List;
import java.util.Map;
import java.util.Random;
import java.util.concurrent.Executors;
import java.util.concurrent.ScheduledExecutorService;
import java.util.concurrent.ThreadLocalRandom;
import java.util.concurrent.TimeUnit;
import java.util.concurrent.atomic.AtomicLong;

import junit.framework.Assert;

import com.google.common.util.concurrent.RateLimiter;

import org.junit.Before;
import org.junit.BeforeClass;
import org.junit.Test;
import org.apache.cassandra.SchemaLoader;
import org.apache.cassandra.Util;
import org.apache.cassandra.config.Config.CommitLogSync;
import org.apache.cassandra.config.DatabaseDescriptor;
import org.apache.cassandra.config.ParameterizedClass;
import org.apache.cassandra.config.Schema;
import org.apache.cassandra.db.Cell;
import org.apache.cassandra.db.ColumnFamily;
import org.apache.cassandra.db.ColumnSerializer;
import org.apache.cassandra.db.Mutation;
import org.apache.cassandra.io.util.FastByteArrayInputStream;

public class CommitLogStressTest
{

    public static ByteBuffer dataSource;
    
    public static int NUM_THREADS = 4 * Runtime.getRuntime().availableProcessors() - 1;

    public static int numCells = 1;

    public static int cellSize = 1024;
    
    public static int rateLimit = 0;
    
    public static int runTimeMs = 10000;
    
    public static String location = DatabaseDescriptor.getCommitLogLocation() + "/stress";
    
    public static int hash(int hash, ByteBuffer bytes)
    {
        int shift = 0;
        for (int i=0; i<bytes.limit(); i++) {
            hash += (bytes.get(i) & 0xFF) << shift;
            shift = (shift + 8) & 0x1F;
        }
        return hash;
    }
    
    public static void main(String[] args) throws Exception {
        try {
            if (args.length >= 1) {
                NUM_THREADS = Integer.parseInt(args[0]);
                System.out.println("Setting num threads to: " + NUM_THREADS);
            }
    
            if (args.length >= 2) {
                numCells = Integer.parseInt(args[1]);
                System.out.println("Setting num cells to: " + numCells);
            }
    
            if (args.length >= 3) {
                cellSize = Integer.parseInt(args[1]);
                System.out.println("Setting cell size to: " + cellSize + " be aware the source corpus may be small");
            }
    
            if (args.length >= 4) {
                rateLimit = Integer.parseInt(args[1]);
                System.out.println("Setting per thread rate limit to: " + rateLimit);
            }
            initialize();
            
            CommitLogStressTest tester = new CommitLogStressTest();
            tester.testFixedSize();
        }
        catch (Throwable e)
        {
            e.printStackTrace(System.err);
        }
        finally {
            System.exit(0);
        }
    }
    
    boolean failed = false;
    volatile boolean stop = false;
    boolean randomSize = false;
    boolean discardedRun = false;
    ReplayPosition discardedPos;
    
    @BeforeClass
    static public void initialize() throws FileNotFoundException, IOException, InterruptedException
    {
        try (FileInputStream fis = new FileInputStream("CHANGES.txt"))
        {
            dataSource = ByteBuffer.allocateDirect((int)fis.getChannel().size());
            while (dataSource.hasRemaining()) {
                fis.getChannel().read(dataSource);
            }
            dataSource.flip();
        }

        SchemaLoader.loadSchema();
        SchemaLoader.schemaDefinition(""); // leave def. blank to maintain old behaviour
    }
    
    @Before
    public void cleanDir()
    {
        File dir = new File(location);
        if (dir.isDirectory())
        {
            File[] files = dir.listFiles();
    
            for (File f : files)
                if (!f.delete())
                    Assert.fail("Failed to delete " + f);
        } else {
            dir.mkdir();
        }
    }

    @Test
    public void testRandomSize() throws Exception
    {
        randomSize = true;
        discardedRun = false;
        testAllLogConfigs();
    }

    @Test
    public void testFixedSize() throws Exception
    {
        randomSize = false;
        discardedRun = false;

        testAllLogConfigs();
    }

    @Test
    public void testDiscardedRun() throws Exception
    {
        discardedRun = true;
        randomSize = true;

        testAllLogConfigs();
    }

    public void testAllLogConfigs() throws IOException, InterruptedException
    {
        failed = false;
        DatabaseDescriptor.setCommitLogSyncBatchWindow(1);
        DatabaseDescriptor.setCommitLogSyncPeriod(30);
        DatabaseDescriptor.setCommitLogSegmentSize(32);
        for (ParameterizedClass compressor : new ParameterizedClass[] {
                null,
                new ParameterizedClass("LZ4Compressor", null),
                new ParameterizedClass("SnappyCompressor", null),
                new ParameterizedClass("DeflateCompressor", null)}) {
            DatabaseDescriptor.setCommitLogCompression(compressor);
            for (CommitLogSync sync : CommitLogSync.values())
            {
                DatabaseDescriptor.setCommitLogSync(sync);
                CommitLog commitLog = new CommitLog(location, CommitLog.instance.archiver);
                testLog(commitLog);
            }
        }
        assert !failed;
    }

    public void testLog(CommitLog commitLog) throws IOException, InterruptedException {
        System.out.format("\nTesting commit log size %.0fmb, compressor %s, sync %s%s%s\n",
                           mb(DatabaseDescriptor.getCommitLogSegmentSize()),
                           commitLog.compressor != null ? commitLog.compressor.getClass().getSimpleName() : "none",
                           commitLog.executor.getClass().getSimpleName(),
                           randomSize ? " random size" : "",
                           discardedRun ? " with discarded run" : "");
        commitLog.allocator.enableReserveSegmentCreation();
        
        final List<CommitlogExecutor> threads = new ArrayList<>();
        ScheduledExecutorService scheduled = startThreads(commitLog, threads);

        discardedPos = ReplayPosition.NONE;
        if (discardedRun) {
            // Makes sure post-break data is not deleted, and that replayer correctly rejects earlier mutations.
            Thread.sleep(runTimeMs / 3);
            stop = true;
            scheduled.shutdown();
            scheduled.awaitTermination(2, TimeUnit.SECONDS);

            for (CommitlogExecutor t: threads)
            {
                t.join();
                if (t.rp.compareTo(discardedPos) > 0)
                    discardedPos = t.rp;
            }
            verifySizes(commitLog);

            commitLog.discardCompletedSegments(Schema.instance.getCFMetaData("Keyspace1", "Standard1").cfId, discardedPos);
            threads.clear();
            System.out.format("Discarded at %s\n", discardedPos);
            verifySizes(commitLog);
            
            scheduled = startThreads(commitLog, threads);
        }

        
        Thread.sleep(runTimeMs);
        stop = true;
        scheduled.shutdown();
        scheduled.awaitTermination(2, TimeUnit.SECONDS);

        int hash = 0;
        int cells = 0;
        for (CommitlogExecutor t: threads) {
            t.join();
            hash += t.hash;
            cells += t.cells;
        }
        verifySizes(commitLog);
        
        commitLog.shutdownBlocking();

        System.out.print("Stopped. Replaying... "); System.out.flush();
        Replayer repl = new Replayer();
        File[] files = new File(location).listFiles();
        repl.recover(files);

        for (File f : files)
            if (!f.delete())
                Assert.fail("Failed to delete " + f);
        
        if (hash == repl.hash && cells == repl.cells)
            System.out.println("Test success.");
        else
        {
            System.out.format("Test failed. Cells %d expected %d, hash %d expected %d.\n", repl.cells, cells, repl.hash, hash);
            failed = true;
        }
    }

    private void verifySizes(CommitLog commitLog)
    {
        // Complete anything that's still left to write.
        commitLog.executor.requestExtraSync().awaitUninterruptibly();
        // One await() does not suffice as we may be signalled when an ongoing sync finished. Request another
        // (which shouldn't write anything) to make sure the first we triggered completes.
        // FIXME: The executor should give us a chance to await completion of the sync we requested.
        commitLog.executor.requestExtraSync().awaitUninterruptibly();
        // Wait for any pending deletes or segment allocations to complete.
        commitLog.allocator.awaitManagementTasksCompletion();
        
        long combinedSize = 0;
        for (File f : new File(commitLog.location).listFiles())
            combinedSize += f.length();
        Assert.assertEquals(combinedSize, commitLog.getActiveOnDiskSize());

        List<String> logFileNames = commitLog.getActiveSegmentNames();
        Map<String, Double> ratios = commitLog.getActiveSegmentCompressionRatios();
        Collection<CommitLogSegment> segments = commitLog.allocator.getActiveSegments();

        for (CommitLogSegment segment: segments)
        {
            Assert.assertTrue(logFileNames.remove(segment.getName()));
            Double ratio = ratios.remove(segment.getName());
            
            Assert.assertEquals(segment.logFile.length(), segment.onDiskSize());
            Assert.assertEquals(segment.onDiskSize() * 1.0 / segment.contentSize(), ratio, 0.01);
        }
        Assert.assertTrue(logFileNames.isEmpty());
        Assert.assertTrue(ratios.isEmpty());
    }

    public ScheduledExecutorService startThreads(final CommitLog commitLog, final List<CommitlogExecutor> threads)
    {
        stop = false;
        for (int ii = 0; ii < NUM_THREADS; ii++) {
            final CommitlogExecutor t = new CommitlogExecutor(commitLog, new Random(ii));
            threads.add(t);
            t.start();
        }

        final long start = System.currentTimeMillis();
        Runnable printRunnable = new Runnable() {
            long lastUpdate = 0;

            public void run() {
              Runtime runtime = Runtime.getRuntime();
              long maxMemory = runtime.maxMemory();
              long allocatedMemory = runtime.totalMemory();
              long freeMemory = runtime.freeMemory();
              long temp = 0;
              long sz = 0;
              for (CommitlogExecutor cle : threads) {
                  temp += cle.counter.get();
                  sz += cle.dataSize;
              }
              double time = (System.currentTimeMillis() - start) / 1000.0;
              double avg = (temp / time);
              System.out.println(
                      String.format("second %d mem max %.0fmb allocated %.0fmb free %.0fmb mutations %d since start %d avg %.3f content %.1fmb ondisk %.1fmb transfer %.3fmb",
                      ((System.currentTimeMillis() - start) / 1000),
                      mb(maxMemory), mb(allocatedMemory), mb(freeMemory), (temp - lastUpdate), lastUpdate, avg,
                      mb(commitLog.getActiveContentSize()), mb(commitLog.getActiveOnDiskSize()), mb(sz / time)));
              lastUpdate = temp;
            }
        };
        ScheduledExecutorService scheduled = Executors.newScheduledThreadPool(1);
        scheduled.scheduleAtFixedRate(printRunnable, 1, 1, TimeUnit.SECONDS);
        return scheduled;
    }

    private static double mb(long maxMemory) {
        return maxMemory / (1024.0 * 1024);
    }

    private static double mb(double maxMemory) {
        return maxMemory / (1024 * 1024);
    }

    public static ByteBuffer randomBytes(int quantity, Random tlr) {
        ByteBuffer slice = ByteBuffer.allocate(quantity);
        ByteBuffer source = dataSource.duplicate();
        source.position(tlr.nextInt(source.capacity() - quantity));
        source.limit(source.position() + quantity);
        slice.put(source);
        slice.flip();
        return slice;
    }

    public class CommitlogExecutor extends Thread {
        final AtomicLong counter = new AtomicLong();
        int hash = 0;
        int cells = 0;
        int dataSize = 0;
        final CommitLog commitLog;
        final Random random;

        volatile ReplayPosition rp;

        public CommitlogExecutor(CommitLog commitLog, Random rand)
        {
            this.commitLog = commitLog;
            this.random = rand;
        }

        public void run() {
            RateLimiter rl = rateLimit != 0 ? RateLimiter.create(rateLimit) : null;
            final Random rand = random != null ? random : ThreadLocalRandom.current();
            while (!stop) {
                if (rl != null)
                    rl.acquire();
                String ks = "Keyspace1";
                ByteBuffer key = randomBytes(16, rand);
                Mutation mutation = new Mutation(ks, key);

                for (int ii = 0; ii < numCells; ii++) {
                    int sz = randomSize ? rand.nextInt(cellSize) : cellSize;
                    ByteBuffer bytes = randomBytes(sz, rand);
                    mutation.add("Standard1", Util.cellname("name" + ii), bytes,
                            System.currentTimeMillis());
                    hash = hash(hash, bytes);
                    ++cells;
                    dataSize += sz;
                }
                rp = commitLog.add(mutation);
                counter.incrementAndGet();
            }
        }
    }
    
    class Replayer extends CommitLogReplayer
    {
        Replayer()
        {
            super(discardedPos, null, ReplayFilter.create());
        }

        int hash = 0;
        int cells = 0;

        @Override
        void replayMutation(byte[] inputBuffer, int size, final long entryLocation, final CommitLogDescriptor desc)
        {
            if (desc.id < discardedPos.segment) {
                System.out.format("Mutation from discarded segment, segment %d pos %d\n", desc.id, entryLocation);
                return;
            } else if (desc.id == discardedPos.segment && entryLocation <= discardedPos.position)
                // Skip over this mutation.
                return;
                
            FastByteArrayInputStream bufIn = new FastByteArrayInputStream(inputBuffer, 0, size);
            Mutation mutation;
            try
            {
                mutation = Mutation.serializer.deserialize(new DataInputStream(bufIn),
                                                               desc.getMessagingVersion(),
                                                               ColumnSerializer.Flag.LOCAL);
            }
            catch (IOException e)
            {
                // Test fails.
                throw new AssertionError(e);
            }

            for (ColumnFamily cf : mutation.getColumnFamilies()) {
                for (Cell c : cf.getSortedColumns()) {
                    if (new String(c.name().toByteBuffer().array(), StandardCharsets.UTF_8).startsWith("name"))
                    {
                        hash = hash(hash, c.value());
                        ++cells;
                    }
                }
            }
        }
        
    }
}


File: test/long/org/apache/cassandra/io/compress/CompressorPerformance.java
package org.apache.cassandra.io.compress;

import java.io.FileInputStream;
import java.io.IOException;
import java.nio.ByteBuffer;
import java.util.concurrent.ThreadLocalRandom;

public class CompressorPerformance
{

    static public void testPerformances() throws IOException
    {
        for (ICompressor compressor: new ICompressor[] {
                SnappyCompressor.instance,  // warm up
                DeflateCompressor.instance,
                LZ4Compressor.instance,
                SnappyCompressor.instance
        })
        {
            for (BufferType in: BufferType.values())
            {
                if (compressor.supports(in))
                {
                    for (BufferType out: BufferType.values())
                    {
                        if (compressor.supports(out))
                        {
                            for (int i=0; i<10; ++i)
                                testPerformance(compressor, in, out);
                            System.out.println();
                        }
                    }
                }
            }
        }
    }

    static ByteBuffer dataSource;
    static int bufLen;

    static private void testPerformance(ICompressor compressor, BufferType in, BufferType out) throws IOException
    {
        int len = dataSource.capacity();
        int bufLen = compressor.initialCompressedBufferLength(len);
        ByteBuffer input = in.allocate(bufLen);
        ByteBuffer output = out.allocate(bufLen);

        int checksum = 0;
        int count = 100;

        long time = System.nanoTime();
        for (int i=0; i<count; ++i)
        {
            output.clear();
            compressor.compress(dataSource, output);
            // Make sure not optimized away.
            checksum += output.get(ThreadLocalRandom.current().nextInt(output.position()));
            dataSource.rewind();
        }
        long timec = System.nanoTime() - time;
        output.flip();
        input.put(output);
        input.flip();

        time = System.nanoTime();
        for (int i=0; i<count; ++i)
        {
            output.clear();
            compressor.uncompress(input, output);
            // Make sure not optimized away.
            checksum += output.get(ThreadLocalRandom.current().nextInt(output.position()));
            input.rewind();
        }
        long timed = System.nanoTime() - time;
        System.out.format("Compressor %s %s->%s compress %.3f ns/b %.3f mb/s uncompress %.3f ns/b %.3f mb/s.%s\n",
                          compressor.getClass().getSimpleName(),
                          in,
                          out,
                          1.0 * timec / (count * len),
                          Math.scalb(1.0e9, -20) * count * len / timec,
                          1.0 * timed / (count * len),
                          Math.scalb(1.0e9, -20) * count * len / timed,
                          checksum == 0 ? " " : "");
    }

    public static void main(String[] args) throws IOException
    {
        try (FileInputStream fis = new FileInputStream("CHANGES.txt"))
        {
            int len = (int)fis.getChannel().size();
            dataSource = ByteBuffer.allocateDirect(len);
            while (dataSource.hasRemaining()) {
                fis.getChannel().read(dataSource);
            }
            dataSource.flip();
        }
        testPerformances();
    }
}


File: test/unit/org/apache/cassandra/db/commitlog/CommitLogTestReplayer.java
/*
* Licensed to the Apache Software Foundation (ASF) under one
* or more contributor license agreements.  See the NOTICE file
* distributed with this work for additional information
* regarding copyright ownership.  The ASF licenses this file
* to you under the Apache License, Version 2.0 (the
* "License"); you may not use this file except in compliance
* with the License.  You may obtain a copy of the License at
*
*    http://www.apache.org/licenses/LICENSE-2.0
*
* Unless required by applicable law or agreed to in writing,
* software distributed under the License is distributed on an
* "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY
* KIND, either express or implied.  See the License for the
* specific language governing permissions and limitations
* under the License.
*/
package org.apache.cassandra.db.commitlog;

import java.io.DataInputStream;
import java.io.File;
import java.io.IOException;

import com.google.common.base.Predicate;

import org.junit.Assert;

import org.apache.cassandra.config.DatabaseDescriptor;
import org.apache.cassandra.db.ColumnSerializer;
import org.apache.cassandra.db.Mutation;
import org.apache.cassandra.io.util.FastByteArrayInputStream;

/**
 * Utility class for tests needing to examine the commitlog contents.
 */
public class CommitLogTestReplayer extends CommitLogReplayer
{
    static public void examineCommitLog(Predicate<Mutation> processor) throws IOException
    {
        CommitLog.instance.sync(true);

        CommitLogTestReplayer replayer = new CommitLogTestReplayer(processor);
        File commitLogDir = new File(DatabaseDescriptor.getCommitLogLocation());
        replayer.recover(commitLogDir.listFiles());
    }

    final private Predicate<Mutation> processor;

    public CommitLogTestReplayer(Predicate<Mutation> processor)
    {
        this(ReplayPosition.NONE, processor);
    }

    public CommitLogTestReplayer(ReplayPosition discardedPos, Predicate<Mutation> processor)
    {
        super(discardedPos, null, ReplayFilter.create());
        this.processor = processor;
    }

    @Override
    void replayMutation(byte[] inputBuffer, int size, final long entryLocation, final CommitLogDescriptor desc)
    {
        FastByteArrayInputStream bufIn = new FastByteArrayInputStream(inputBuffer, 0, size);
        Mutation mutation;
        try
        {
            mutation = Mutation.serializer.deserialize(new DataInputStream(bufIn),
                                                           desc.getMessagingVersion(),
                                                           ColumnSerializer.Flag.LOCAL);
            Assert.assertTrue(processor.apply(mutation));
        }
        catch (IOException e)
        {
            // Test fails.
            throw new AssertionError(e);
        }
    }
}


File: test/unit/org/apache/cassandra/dht/BootStrapperTest.java
/*
* Licensed to the Apache Software Foundation (ASF) under one
* or more contributor license agreements.  See the NOTICE file
* distributed with this work for additional information
* regarding copyright ownership.  The ASF licenses this file
* to you under the Apache License, Version 2.0 (the
* "License"); you may not use this file except in compliance
* with the License.  You may obtain a copy of the License at
*
*    http://www.apache.org/licenses/LICENSE-2.0
*
* Unless required by applicable law or agreed to in writing,
* software distributed under the License is distributed on an
* "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY
* KIND, either express or implied.  See the License for the
* specific language governing permissions and limitations
* under the License.
*/
package org.apache.cassandra.dht;

import java.net.InetAddress;
import java.net.UnknownHostException;
import java.util.Collection;
import java.util.HashSet;
import java.util.Set;
import java.util.Map;

import org.junit.BeforeClass;
import org.junit.Test;
import org.junit.runner.RunWith;

import org.apache.cassandra.OrderedJUnit4ClassRunner;
import org.apache.cassandra.SchemaLoader;
import org.apache.cassandra.config.DatabaseDescriptor;
import org.apache.cassandra.config.Schema;
import org.apache.cassandra.db.Keyspace;
import org.apache.cassandra.exceptions.ConfigurationException;
import org.apache.cassandra.gms.IFailureDetectionEventListener;
import org.apache.cassandra.gms.IFailureDetector;
import org.apache.cassandra.locator.TokenMetadata;
import org.apache.cassandra.service.StorageService;

import static org.junit.Assert.*;

@RunWith(OrderedJUnit4ClassRunner.class)
public class BootStrapperTest
{
    @BeforeClass
    public static void setup() throws ConfigurationException
    {
        SchemaLoader.startGossiper();
        SchemaLoader.prepareServer();
        SchemaLoader.schemaDefinition("BootStrapperTest");
    }

    @Test
    public void testSourceTargetComputation() throws UnknownHostException
    {
        final int[] clusterSizes = new int[] { 1, 3, 5, 10, 100};
        for (String keyspaceName : Schema.instance.getNonSystemKeyspaces())
        {
            int replicationFactor = Keyspace.open(keyspaceName).getReplicationStrategy().getReplicationFactor();
            for (int clusterSize : clusterSizes)
                if (clusterSize >= replicationFactor)
                    testSourceTargetComputation(keyspaceName, clusterSize, replicationFactor);
        }
    }

    private RangeStreamer testSourceTargetComputation(String keyspaceName, int numOldNodes, int replicationFactor) throws UnknownHostException
    {
        StorageService ss = StorageService.instance;

        generateFakeEndpoints(numOldNodes);
        Token myToken = StorageService.getPartitioner().getRandomToken();
        InetAddress myEndpoint = InetAddress.getByName("127.0.0.1");

        TokenMetadata tmd = ss.getTokenMetadata();
        assertEquals(numOldNodes, tmd.sortedTokens().size());
        RangeStreamer s = new RangeStreamer(tmd, null, myEndpoint, "Bootstrap", true, DatabaseDescriptor.getEndpointSnitch(), new StreamStateStore());
        IFailureDetector mockFailureDetector = new IFailureDetector()
        {
            public boolean isAlive(InetAddress ep)
            {
                return true;
            }

            public void interpret(InetAddress ep) { throw new UnsupportedOperationException(); }
            public void report(InetAddress ep) { throw new UnsupportedOperationException(); }
            public void registerFailureDetectionEventListener(IFailureDetectionEventListener listener) { throw new UnsupportedOperationException(); }
            public void unregisterFailureDetectionEventListener(IFailureDetectionEventListener listener) { throw new UnsupportedOperationException(); }
            public void remove(InetAddress ep) { throw new UnsupportedOperationException(); }
            public void forceConviction(InetAddress ep) { throw new UnsupportedOperationException(); }
        };
        s.addSourceFilter(new RangeStreamer.FailureDetectorSourceFilter(mockFailureDetector));
        s.addRanges(keyspaceName, Keyspace.open(keyspaceName).getReplicationStrategy().getPendingAddressRanges(tmd, myToken, myEndpoint));

        Collection<Map.Entry<InetAddress, Collection<Range<Token>>>> toFetch = s.toFetch().get(keyspaceName);

        // Check we get get RF new ranges in total
        Set<Range<Token>> ranges = new HashSet<>();
        for (Map.Entry<InetAddress, Collection<Range<Token>>> e : toFetch)
            ranges.addAll(e.getValue());

        assertEquals(replicationFactor, ranges.size());

        // there isn't any point in testing the size of these collections for any specific size.  When a random partitioner
        // is used, they will vary.
        assert toFetch.iterator().next().getValue().size() > 0;
        assert !toFetch.iterator().next().getKey().equals(myEndpoint);
        return s;
    }

    private void generateFakeEndpoints(int numOldNodes) throws UnknownHostException
    {
        TokenMetadata tmd = StorageService.instance.getTokenMetadata();
        tmd.clearUnsafe();
        IPartitioner p = StorageService.getPartitioner();

        for (int i = 1; i <= numOldNodes; i++)
        {
            // leave .1 for myEndpoint
            tmd.updateNormalToken(p.getRandomToken(), InetAddress.getByName("127.0.0." + (i + 1)));
        }
    }
}
