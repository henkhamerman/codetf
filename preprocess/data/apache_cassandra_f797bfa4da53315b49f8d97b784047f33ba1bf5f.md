Refactoring Types: ['Extract Method', 'Move Class']
eDescriptor.java
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
import java.io.FileFilter;
import java.io.IOException;
import java.net.Inet4Address;
import java.net.Inet6Address;
import java.net.InetAddress;
import java.net.NetworkInterface;
import java.net.SocketException;
import java.net.UnknownHostException;
import java.util.ArrayList;
import java.util.Arrays;
import java.util.Collection;
import java.util.Collections;
import java.util.Comparator;
import java.util.Enumeration;
import java.util.List;
import java.util.Map;
import java.util.Set;
import java.util.UUID;

import com.google.common.annotations.VisibleForTesting;
import com.google.common.collect.ImmutableSet;
import com.google.common.primitives.Longs;

import org.apache.cassandra.thrift.ThriftServer;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.apache.cassandra.auth.AllowAllAuthenticator;
import org.apache.cassandra.auth.AllowAllAuthorizer;
import org.apache.cassandra.auth.AllowAllInternodeAuthenticator;
import org.apache.cassandra.auth.IAuthenticator;
import org.apache.cassandra.auth.IAuthorizer;
import org.apache.cassandra.auth.IInternodeAuthenticator;
import org.apache.cassandra.config.Config.RequestSchedulerId;
import org.apache.cassandra.config.EncryptionOptions.ClientEncryptionOptions;
import org.apache.cassandra.config.EncryptionOptions.ServerEncryptionOptions;
import org.apache.cassandra.db.ColumnFamilyStore;
import org.apache.cassandra.db.DefsTables;
import org.apache.cassandra.db.SystemKeyspace;
import org.apache.cassandra.dht.IPartitioner;
import org.apache.cassandra.exceptions.ConfigurationException;
import org.apache.cassandra.io.FSWriteError;
import org.apache.cassandra.io.util.FileUtils;
import org.apache.cassandra.io.util.IAllocator;
import org.apache.cassandra.locator.DynamicEndpointSnitch;
import org.apache.cassandra.locator.EndpointSnitchInfo;
import org.apache.cassandra.locator.IEndpointSnitch;
import org.apache.cassandra.locator.SeedProvider;
import org.apache.cassandra.net.MessagingService;
import org.apache.cassandra.scheduler.IRequestScheduler;
import org.apache.cassandra.scheduler.NoScheduler;
import org.apache.cassandra.service.CacheService;
import org.apache.cassandra.utils.ByteBufferUtil;
import org.apache.cassandra.utils.FBUtilities;
import org.apache.cassandra.utils.JVMStabilityInspector;
import org.apache.cassandra.utils.memory.HeapPool;
import org.apache.cassandra.utils.memory.NativePool;
import org.apache.cassandra.utils.memory.MemtablePool;
import org.apache.cassandra.utils.memory.SlabPool;

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

    private static IAuthenticator authenticator = new AllowAllAuthenticator();
    private static IAuthorizer authorizer = new AllowAllAuthorizer();

    private static IRequestScheduler requestScheduler;
    private static RequestSchedulerId requestSchedulerId;
    private static RequestSchedulerOptions requestSchedulerOptions;

    private static long keyCacheSizeInMB;
    private static long counterCacheSizeInMB;
    private static IAllocator memoryAllocator;
    private static long indexSummaryCapacityInMB;

    private static String localDC;
    private static Comparator<InetAddress> localComparator;

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
                // at least we have to set memoryAllocator to open SSTable in client mode
                memoryAllocator = FBUtilities.newOffHeapAllocator(conf.memory_allocator);
            }
            else
            {
                applyConfig(loadConfig());
            }
        }
        catch (ConfigurationException e)
        {
            logger.error("Fatal configuration error", e);
            System.err.println(e.getMessage() + "\nFatal configuration error; unable to start. See log for stacktrace.");
            System.exit(1);
        }
        catch (Exception e)
        {
            logger.error("Fatal error during configuration loading", e);
            System.err.println(e.getMessage() + "\nFatal error during configuration loading; unable to start. See log for stacktrace.");
            JVMStabilityInspector.inspectThrowable(e);
            System.exit(1);
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
                throw new ConfigurationException("Configured " + configName + " \"" + intf + "\" could not be found");
            Enumeration<InetAddress> addrs = ni.getInetAddresses();
            if (!addrs.hasMoreElements())
                throw new ConfigurationException("Configured " + configName + " \"" + intf + "\" was found, but had no addresses");

            /*
             * Try to return the first address of the preferred type, otherwise return the first address
             */
            InetAddress retval = null;
            while (addrs.hasMoreElements())
            {
                InetAddress temp = addrs.nextElement();
                if (preferIPv6 && temp.getClass() == Inet6Address.class) return temp;
                if (!preferIPv6 && temp.getClass() == Inet4Address.class) return temp;
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
            throw new ConfigurationException("Set listen_address OR listen_interface, not both");
        }
        else if (config.listen_address != null)
        {
            try
            {
                listenAddress = InetAddress.getByName(config.listen_address);
            }
            catch (UnknownHostException e)
            {
                throw new ConfigurationException("Unknown listen_address '" + config.listen_address + "'");
            }

            if (listenAddress.isAnyLocalAddress())
                throw new ConfigurationException("listen_address cannot be a wildcard address (" + config.listen_address + ")!");
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
                throw new ConfigurationException("Unknown broadcast_address '" + config.broadcast_address + "'");
            }

            if (broadcastAddress.isAnyLocalAddress())
                throw new ConfigurationException("broadcast_address cannot be a wildcard address (" + config.broadcast_address + ")!");
        }

        /* Local IP, hostname or interface to bind RPC server to */
        if (config.rpc_address != null && config.rpc_interface != null)
        {
            throw new ConfigurationException("Set rpc_address OR rpc_interface, not both");
        }
        else if (config.rpc_address != null)
        {
            try
            {
                rpcAddress = InetAddress.getByName(config.rpc_address);
            }
            catch (UnknownHostException e)
            {
                throw new ConfigurationException("Unknown host in rpc_address " + config.rpc_address);
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
                throw new ConfigurationException("Unknown broadcast_rpc_address '" + config.broadcast_rpc_address + "'");
            }

            if (broadcastRpcAddress.isAnyLocalAddress())
                throw new ConfigurationException("broadcast_rpc_address cannot be a wildcard address (" + config.broadcast_rpc_address + ")!");
        }
        else
        {
            if (rpcAddress.isAnyLocalAddress())
                throw new ConfigurationException("If rpc_address is set to a wildcard address (" + config.rpc_address + "), then " +
                                                 "you must set broadcast_rpc_address to a value other than " + config.rpc_address);
            broadcastRpcAddress = rpcAddress;
        }
    }

    private static void applyConfig(Config config) throws ConfigurationException
    {
        conf = config;

        if (conf.commitlog_sync == null)
        {
            throw new ConfigurationException("Missing required directive CommitLogSync");
        }

        if (conf.commitlog_sync == Config.CommitLogSync.batch)
        {
            if (conf.commitlog_sync_batch_window_in_ms == null)
            {
                throw new ConfigurationException("Missing value for commitlog_sync_batch_window_in_ms: Double expected.");
            }
            else if (conf.commitlog_sync_period_in_ms != null)
            {
                throw new ConfigurationException("Batch sync specified, but commitlog_sync_period_in_ms found. Only specify commitlog_sync_batch_window_in_ms when using batch sync");
            }
            logger.debug("Syncing log with a batch window of {}", conf.commitlog_sync_batch_window_in_ms);
        }
        else
        {
            if (conf.commitlog_sync_period_in_ms == null)
            {
                throw new ConfigurationException("Missing value for commitlog_sync_period_in_ms: Integer expected");
            }
            else if (conf.commitlog_sync_batch_window_in_ms != null)
            {
                throw new ConfigurationException("commitlog_sync_period_in_ms specified, but commitlog_sync_batch_window_in_ms found.  Only specify commitlog_sync_period_in_ms when using periodic sync.");
            }
            logger.debug("Syncing log with a period of {}", conf.commitlog_sync_period_in_ms);
        }

        if (conf.commitlog_total_space_in_mb == null)
            conf.commitlog_total_space_in_mb = hasLargeAddressSpace() ? 8192 : 32;

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

        /* Authentication and authorization backend, implementing IAuthenticator and IAuthorizer */
        if (conf.authenticator != null)
            authenticator = FBUtilities.newAuthenticator(conf.authenticator);

        if (conf.authorizer != null)
            authorizer = FBUtilities.newAuthorizer(conf.authorizer);

        if (authenticator instanceof AllowAllAuthenticator && !(authorizer instanceof AllowAllAuthorizer))
            throw new ConfigurationException("AllowAllAuthenticator can't be used with " +  conf.authorizer);

        if (conf.internode_authenticator != null)
            internodeAuthenticator = FBUtilities.construct(conf.internode_authenticator, "internode_authenticator");
        else
            internodeAuthenticator = new AllowAllInternodeAuthenticator();

        authenticator.validateConfiguration();
        authorizer.validateConfiguration();
        internodeAuthenticator.validateConfiguration();

        /* Hashing strategy */
        if (conf.partitioner == null)
        {
            throw new ConfigurationException("Missing directive: partitioner");
        }
        try
        {
            partitioner = FBUtilities.newPartitioner(System.getProperty("cassandra.partitioner", conf.partitioner));
        }
        catch (Exception e)
        {
            throw new ConfigurationException("Invalid partitioner class " + conf.partitioner);
        }
        paritionerName = partitioner.getClass().getCanonicalName();

        if (conf.max_hint_window_in_ms == null)
        {
            throw new ConfigurationException("max_hint_window_in_ms cannot be set to null");
        }

        /* phi convict threshold for FailureDetector */
        if (conf.phi_convict_threshold < 5 || conf.phi_convict_threshold > 16)
        {
            throw new ConfigurationException("phi_convict_threshold must be between 5 and 16");
        }

        /* Thread per pool */
        if (conf.concurrent_reads != null && conf.concurrent_reads < 2)
        {
            throw new ConfigurationException("concurrent_reads must be at least 2");
        }

        if (conf.concurrent_writes != null && conf.concurrent_writes < 2)
        {
            throw new ConfigurationException("concurrent_writes must be at least 2");
        }

        if (conf.concurrent_counter_writes != null && conf.concurrent_counter_writes < 2)
            throw new ConfigurationException("concurrent_counter_writes must be at least 2");

        if (conf.concurrent_replicates != null)
            logger.warn("concurrent_replicates has been deprecated and should be removed from cassandra.yaml");

        if (conf.file_cache_size_in_mb == null)
            conf.file_cache_size_in_mb = Math.min(512, (int) (Runtime.getRuntime().maxMemory() / (4 * 1048576)));

        if (conf.memtable_offheap_space_in_mb == null)
            conf.memtable_offheap_space_in_mb = (int) (Runtime.getRuntime().maxMemory() / (4 * 1048576));
        if (conf.memtable_offheap_space_in_mb < 0)
            throw new ConfigurationException("memtable_offheap_space_in_mb must be positive");
        // for the moment, we default to twice as much on-heap space as off-heap, as heap overhead is very large
        if (conf.memtable_heap_space_in_mb == null)
            conf.memtable_heap_space_in_mb = (int) (Runtime.getRuntime().maxMemory() / (4 * 1048576));
        if (conf.memtable_heap_space_in_mb <= 0)
            throw new ConfigurationException("memtable_heap_space_in_mb must be positive");
        logger.info("Global memtable on-heap threshold is enabled at {}MB", conf.memtable_heap_space_in_mb);
        if (conf.memtable_offheap_space_in_mb == 0)
            logger.info("Global memtable off-heap threshold is disabled, HeapAllocator will be used instead");
        else
            logger.info("Global memtable off-heap threshold is enabled at {}MB", conf.memtable_offheap_space_in_mb);

        applyAddressConfig(config);

        if (conf.thrift_framed_transport_size_in_mb <= 0)
            throw new ConfigurationException("thrift_framed_transport_size_in_mb must be positive");

        if (conf.native_transport_max_frame_size_in_mb <= 0)
            throw new ConfigurationException("native_transport_max_frame_size_in_mb must be positive");

        // fail early instead of OOMing (see CASSANDRA-8116)
        if (ThriftServer.HSHA.equals(conf.rpc_server_type) && conf.rpc_max_threads == Integer.MAX_VALUE)
            throw new ConfigurationException("The hsha rpc_server_type is not compatible with an rpc_max_threads " +
                                             "setting of 'unlimited'.  Please see the comments in cassandra.yaml " +
                                             "for rpc_server_type and rpc_max_threads.");
        if (ThriftServer.HSHA.equals(conf.rpc_server_type) && conf.rpc_max_threads > (FBUtilities.getAvailableProcessors() * 2 + 1024))
            logger.warn("rpc_max_threads setting of {} may be too high for the hsha server and cause unnecessary thread contention, reducing performance", conf.rpc_max_threads);

        /* end point snitch */
        if (conf.endpoint_snitch == null)
        {
            throw new ConfigurationException("Missing endpoint_snitch directive");
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
                throw new ConfigurationException("Invalid Request Scheduler class " + conf.request_scheduler);
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
                throw new ConfigurationException("commitlog_directory is missing and -Dcassandra.storagedir is not set");
            conf.commitlog_directory += File.separator + "commitlog";
        }
        if (conf.saved_caches_directory == null)
        {
            conf.saved_caches_directory = System.getProperty("cassandra.storagedir", null);
            if (conf.saved_caches_directory == null)
                throw new ConfigurationException("saved_caches_directory is missing and -Dcassandra.storagedir is not set");
            conf.saved_caches_directory += File.separator + "saved_caches";
        }
        if (conf.data_file_directories == null)
        {
            String defaultDataDir = System.getProperty("cassandra.storagedir", null);
            if (defaultDataDir == null)
                throw new ConfigurationException("data_file_directories is not missing and -Dcassandra.storagedir is not set");
            conf.data_file_directories = new String[]{ defaultDataDir + File.separator + "data" };
        }

        /* data file and commit log directories. they get created later, when they're needed. */
        for (String datadir : conf.data_file_directories)
        {
            if (datadir.equals(conf.commitlog_directory))
                throw new ConfigurationException("commitlog_directory must not be the same as any data_file_directories");
            if (datadir.equals(conf.saved_caches_directory))
                throw new ConfigurationException("saved_caches_directory must not be the same as any data_file_directories");
        }

        if (conf.commitlog_directory.equals(conf.saved_caches_directory))
            throw new ConfigurationException("saved_caches_directory must not be the same as the commitlog_directory");

        if (conf.memtable_flush_writers == null)
            conf.memtable_flush_writers = Math.min(8, Math.max(2, Math.min(FBUtilities.getAvailableProcessors(), conf.data_file_directories.length)));

        if (conf.memtable_flush_writers < 1)
            throw new ConfigurationException("memtable_flush_writers must be at least 1");

        if (conf.memtable_cleanup_threshold == null)
            conf.memtable_cleanup_threshold = (float) (1.0 / (1 + conf.memtable_flush_writers));

        if (conf.memtable_cleanup_threshold < 0.01f)
            throw new ConfigurationException("memtable_cleanup_threshold must be >= 0.01");
        if (conf.memtable_cleanup_threshold > 0.99f)
            throw new ConfigurationException("memtable_cleanup_threshold must be <= 0.99");
        if (conf.memtable_cleanup_threshold < 0.1f)
            logger.warn("memtable_cleanup_threshold is set very low, which may cause performance degradation");

        if (conf.concurrent_compactors == null)
            conf.concurrent_compactors = Math.min(8, Math.max(2, Math.min(FBUtilities.getAvailableProcessors(), conf.data_file_directories.length)));

        if (conf.concurrent_compactors <= 0)
            throw new ConfigurationException("concurrent_compactors should be strictly greater than 0");

        if (conf.initial_token != null)
            for (String token : tokensFromString(conf.initial_token))
                partitioner.getTokenFactory().validate(token);

        if (conf.num_tokens == null)
        	conf.num_tokens = 1;
        else if (conf.num_tokens > MAX_NUM_TOKENS)
            throw new ConfigurationException(String.format("A maximum number of %d tokens per node is supported", MAX_NUM_TOKENS));

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
                    + conf.key_cache_size_in_mb + "', supported values are <integer> >= 0.");
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
                    + conf.counter_cache_size_in_mb + "', supported values are <integer> >= 0.");
        }

        // if set to empty/"auto" then use 5% of Heap size
        indexSummaryCapacityInMB = (conf.index_summary_capacity_in_mb == null)
            ? Math.max(1, (int) (Runtime.getRuntime().totalMemory() * 0.05 / 1024 / 1024))
            : conf.index_summary_capacity_in_mb;

        if (indexSummaryCapacityInMB < 0)
            throw new ConfigurationException("index_summary_capacity_in_mb option was set incorrectly to '"
                    + conf.index_summary_capacity_in_mb + "', it should be a non-negative integer.");

        memoryAllocator = FBUtilities.newOffHeapAllocator(conf.memory_allocator);

        if(conf.encryption_options != null)
        {
            logger.warn("Please rename encryption_options as server_encryption_options in the yaml");
            //operate under the assumption that server_encryption_options is not set in yaml rather than both
            conf.server_encryption_options = conf.encryption_options;
        }

        // Hardcoded system keyspaces
        List<KSMetaData> systemKeyspaces = Arrays.asList(KSMetaData.systemKeyspace());
        assert systemKeyspaces.size() == Schema.systemKeyspaceNames.size();
        for (KSMetaData ksmd : systemKeyspaces)
            Schema.instance.load(ksmd);

        /* Load the seeds for node contact points */
        if (conf.seed_provider == null)
        {
            throw new ConfigurationException("seeds configuration is missing; a minimum of one seed is required.");
        }
        try
        {
            Class<?> seedProviderClass = Class.forName(conf.seed_provider.class_name);
            seedProvider = (SeedProvider)seedProviderClass.getConstructor(Map.class).newInstance(conf.seed_provider.parameters);
        }
        // there are about 5 checked exceptions that could be thrown here.
        catch (Exception e)
        {
            logger.error("Fatal configuration error", e);
            System.err.println(e.getMessage() + "\nFatal configuration error; unable to start server.  See log for stacktrace.");
            System.exit(1);
        }
        if (seedProvider.getSeeds().size() == 0)
            throw new ConfigurationException("The seed provider lists no seeds.");
    }

    private static IEndpointSnitch createEndpointSnitch(String snitchClassName) throws ConfigurationException
    {
        if (!snitchClassName.contains("."))
            snitchClassName = "org.apache.cassandra.locator." + snitchClassName;
        IEndpointSnitch snitch = FBUtilities.construct(snitchClassName, "snitch");
        return conf.dynamic_snitch ? new DynamicEndpointSnitch(snitch) : snitch;
    }

    /**
     * load keyspace (keyspace) definitions, but do not initialize the keyspace instances.
     * Schema version may be updated as the result.
     */
    public static void loadSchemas()
    {
        loadSchemas(true);
    }

    /**
     * Load schema definitions.
     *
     * @param updateVersion true if schema version needs to be updated
     */
    public static void loadSchemas(boolean updateVersion)
    {
        ColumnFamilyStore schemaCFS = SystemKeyspace.schemaCFS(SystemKeyspace.SCHEMA_KEYSPACES_CF);

        // if keyspace with definitions is empty try loading the old way
        if (schemaCFS.estimateKeys() == 0)
        {
            logger.info("Couldn't detect any schema definitions in local storage.");
            // peek around the data directories to see if anything is there.
            if (hasExistingNoSystemTables())
                logger.info("Found keyspace data in data directories. Consider using cqlsh to define your schema.");
            else
                logger.info("To create keyspaces and column families, see 'help create' in cqlsh.");
        }
        else
        {
            Schema.instance.load(DefsTables.loadFromKeyspace());
        }

        if (updateVersion)
            Schema.instance.updateVersion();
    }

    private static boolean hasExistingNoSystemTables()
    {
        for (String dataDir : getAllDataFileLocations())
        {
            File dataPath = new File(dataDir);
            if (dataPath.exists() && dataPath.isDirectory())
            {
                // see if there are other directories present.
                int dirCount = dataPath.listFiles(new FileFilter()
                {
                    public boolean accept(File pathname)
                    {
                        return (pathname.isDirectory() && !Schema.systemKeyspaceNames.contains(pathname.getName()));
                    }
                }).length;

                if (dirCount > 0)
                    return true;
            }
        }

        return false;
    }

    public static IAuthenticator getAuthenticator()
    {
        return authenticator;
    }

    public static IAuthorizer getAuthorizer()
    {
        return authorizer;
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
                throw new ConfigurationException("At least one DataFileDirectory must be specified");

            for (String dataFileDirectory : conf.data_file_directories)
            {
                FileUtils.createDirectory(dataFileDirectory);
            }

            if (conf.commitlog_directory == null)
                throw new ConfigurationException("commitlog_directory must be specified");

            FileUtils.createDirectory(conf.commitlog_directory);

            if (conf.saved_caches_directory == null)
                throw new ConfigurationException("saved_caches_directory must be specified");

            FileUtils.createDirectory(conf.saved_caches_directory);
        }
        catch (ConfigurationException e)
        {
            logger.error("Fatal error: {}", e.getMessage());
            System.err.println("Bad configuration; unable to start server");
            System.exit(1);
        }
        catch (FSWriteError e)
        {
            logger.error("Fatal error: {}", e.getMessage());
            System.err.println(e.getCause().getMessage() + "; unable to start server");
            System.exit(1);
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

    public static int getCommitLogSyncPeriod()
    {
        return conf.commitlog_sync_period_in_ms;
    }

    public static int getCommitLogPeriodicQueueSize()
    {
        return conf.commitlog_periodic_queue_size;
    }

    public static Config.CommitLogSync getCommitLogSync()
    {
        return conf.commitlog_sync;
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

    @Deprecated
    public static Integer getIndexInterval()
    {
        return conf.index_interval;
    }

    public static File getSerializedCachePath(String ksName, String cfName, UUID cfId, CacheService.CacheType cacheType, String version)
    {
        StringBuilder builder = new StringBuilder();
        builder.append(ksName).append('-');
        builder.append(cfName).append('-');
        if (cfId != null)
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

    public static long getTotalCommitlogSpaceInMB()
    {
        return conf.commitlog_total_space_in_mb;
    }

    public static int getSSTablePreempiveOpenIntervalInMB()
    {
        return conf.sstable_preemptive_open_interval_in_mb;
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

    public static IAllocator getoffHeapMemoryAllocator()
    {
        return memoryAllocator;
    }

    public static void setRowCacheKeysToSave(int rowCacheKeysToSave)
    {
        conf.row_cache_keys_to_save = rowCacheKeysToSave;
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
                    logger.error("Could not free direct byte buffer: offheap_buffers is not a safe memtable_allocation_type without this ability, please adjust your config. This feature is only guaranteed to work on an Oracle JVM. Refusing to start.");
                    System.exit(-1);
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

    public static String getOtcCoalescingStrategy()
    {
        return conf.otc_coalescing_strategy;
    }

    public static int getOtcCoalescingWindow()
    {
        return conf.otc_coalescing_window_us;
    }
}


File: src/java/org/apache/cassandra/cql3/ResultSet.java
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

import java.nio.ByteBuffer;
import java.util.*;

import io.netty.buffer.ByteBuf;

import org.apache.cassandra.transport.*;
import org.apache.cassandra.db.marshal.AbstractType;
import org.apache.cassandra.db.marshal.LongType;
import org.apache.cassandra.db.marshal.ReversedType;
import org.apache.cassandra.thrift.Column;
import org.apache.cassandra.thrift.CqlMetadata;
import org.apache.cassandra.thrift.CqlResult;
import org.apache.cassandra.thrift.CqlResultType;
import org.apache.cassandra.thrift.CqlRow;
import org.apache.cassandra.utils.ByteBufferUtil;
import org.apache.cassandra.service.pager.PagingState;

public class ResultSet
{
    public static final Codec codec = new Codec();
    private static final ColumnIdentifier COUNT_COLUMN = new ColumnIdentifier("count", false);

    public final Metadata metadata;
    public final List<List<ByteBuffer>> rows;

    public ResultSet(List<ColumnSpecification> metadata)
    {
        this(new Metadata(metadata), new ArrayList<List<ByteBuffer>>());
    }

    public ResultSet(Metadata metadata, List<List<ByteBuffer>> rows)
    {
        this.metadata = metadata;
        this.rows = rows;
    }

    public int size()
    {
        return rows.size();
    }

    public void addRow(List<ByteBuffer> row)
    {
        assert row.size() == metadata.valueCount();
        rows.add(row);
    }

    public void addColumnValue(ByteBuffer value)
    {
        if (rows.isEmpty() || lastRow().size() == metadata.valueCount())
            rows.add(new ArrayList<ByteBuffer>(metadata.valueCount()));

        lastRow().add(value);
    }

    private List<ByteBuffer> lastRow()
    {
        return rows.get(rows.size() - 1);
    }

    public void reverse()
    {
        Collections.reverse(rows);
    }

    public void trim(int limit)
    {
        int toRemove = rows.size() - limit;
        if (toRemove > 0)
        {
            for (int i = 0; i < toRemove; i++)
                rows.remove(rows.size() - 1);
        }
    }

    public ResultSet makeCountResult(ColumnIdentifier alias)
    {
        assert metadata.names != null;
        String ksName = metadata.names.get(0).ksName;
        String cfName = metadata.names.get(0).cfName;
        long count = rows.size();
        return makeCountResult(ksName, cfName, count, alias);
    }

    public static ResultSet.Metadata makeCountMetadata(String ksName, String cfName, ColumnIdentifier alias)
    {
        ColumnSpecification spec = new ColumnSpecification(ksName, cfName, alias == null ? COUNT_COLUMN : alias, LongType.instance);
        return new Metadata(Collections.singletonList(spec));
    }

    public static ResultSet makeCountResult(String ksName, String cfName, long count, ColumnIdentifier alias)
    {
        List<List<ByteBuffer>> newRows = Collections.singletonList(Collections.singletonList(ByteBufferUtil.bytes(count)));
        return new ResultSet(makeCountMetadata(ksName, cfName, alias), newRows);
    }

    public CqlResult toThriftResult()
    {
        assert metadata.names != null;

        String UTF8 = "UTF8Type";
        CqlMetadata schema = new CqlMetadata(new HashMap<ByteBuffer, String>(),
                new HashMap<ByteBuffer, String>(),
                // The 2 following ones shouldn't be needed in CQL3
                UTF8, UTF8);

        for (int i = 0; i < metadata.columnCount; i++)
        {
            ColumnSpecification spec = metadata.names.get(i);
            ByteBuffer colName = ByteBufferUtil.bytes(spec.name.toString());
            schema.name_types.put(colName, UTF8);
            AbstractType<?> normalizedType = spec.type instanceof ReversedType ? ((ReversedType)spec.type).baseType : spec.type;
            schema.value_types.put(colName, normalizedType.toString());

        }

        List<CqlRow> cqlRows = new ArrayList<CqlRow>(rows.size());
        for (List<ByteBuffer> row : rows)
        {
            List<Column> thriftCols = new ArrayList<Column>(metadata.columnCount);
            for (int i = 0; i < metadata.columnCount; i++)
            {
                Column col = new Column(ByteBufferUtil.bytes(metadata.names.get(i).name.toString()));
                col.setValue(row.get(i));
                thriftCols.add(col);
            }
            // The key of CqlRow shoudn't be needed in CQL3
            cqlRows.add(new CqlRow(ByteBufferUtil.EMPTY_BYTE_BUFFER, thriftCols));
        }
        CqlResult res = new CqlResult(CqlResultType.ROWS);
        res.setRows(cqlRows).setSchema(schema);
        return res;
    }

    @Override
    public String toString()
    {
        try
        {
            StringBuilder sb = new StringBuilder();
            sb.append(metadata).append('\n');
            for (List<ByteBuffer> row : rows)
            {
                for (int i = 0; i < row.size(); i++)
                {
                    ByteBuffer v = row.get(i);
                    if (v == null)
                    {
                        sb.append(" | null");
                    }
                    else
                    {
                        sb.append(" | ");
                        if (metadata.flags.contains(Flag.NO_METADATA))
                            sb.append("0x").append(ByteBufferUtil.bytesToHex(v));
                        else
                            sb.append(metadata.names.get(i).type.getString(v));
                    }
                }
                sb.append('\n');
            }
            sb.append("---");
            return sb.toString();
        }
        catch (Exception e)
        {
            throw new RuntimeException(e);
        }
    }

    public static class Codec implements CBCodec<ResultSet>
    {
        /*
         * Format:
         *   - metadata
         *   - rows count (4 bytes)
         *   - rows
         */
        public ResultSet decode(ByteBuf body, int version)
        {
            Metadata m = Metadata.codec.decode(body, version);
            int rowCount = body.readInt();
            ResultSet rs = new ResultSet(m, new ArrayList<List<ByteBuffer>>(rowCount));

            // rows
            int totalValues = rowCount * m.columnCount;
            for (int i = 0; i < totalValues; i++)
                rs.addColumnValue(CBUtil.readValue(body));

            return rs;
        }

        public void encode(ResultSet rs, ByteBuf dest, int version)
        {
            Metadata.codec.encode(rs.metadata, dest, version);
            dest.writeInt(rs.rows.size());
            for (List<ByteBuffer> row : rs.rows)
            {
                // Note that we do only want to serialize only the first columnCount values, even if the row
                // as more: see comment on Metadata.names field.
                for (int i = 0; i < rs.metadata.columnCount; i++)
                    CBUtil.writeValue(row.get(i), dest);
            }
        }

        public int encodedSize(ResultSet rs, int version)
        {
            int size = Metadata.codec.encodedSize(rs.metadata, version) + 4;
            for (List<ByteBuffer> row : rs.rows)
            {
                for (int i = 0; i < rs.metadata.columnCount; i++)
                    size += CBUtil.sizeOfValue(row.get(i));
            }
            return size;
        }
    }

    public static class Metadata
    {
        public static final CBCodec<Metadata> codec = new Codec();

        public static final Metadata EMPTY = new Metadata(EnumSet.of(Flag.NO_METADATA), null, 0, null);

        private final EnumSet<Flag> flags;
        // Please note that columnCount can actually be smaller than names, even if names is not null. This is
        // used to include columns in the resultSet that we need to do post-query re-orderings
        // (SelectStatement.orderResults) but that shouldn't be sent to the user as they haven't been requested
        // (CASSANDRA-4911). So the serialization code will exclude any columns in name whose index is >= columnCount.
        public final List<ColumnSpecification> names;
        private final int columnCount;
        private PagingState pagingState;

        public Metadata(List<ColumnSpecification> names)
        {
            this(EnumSet.noneOf(Flag.class), names, names.size(), null);
            if (!names.isEmpty() && allInSameCF())
                flags.add(Flag.GLOBAL_TABLES_SPEC);
        }

        private Metadata(EnumSet<Flag> flags, List<ColumnSpecification> names, int columnCount, PagingState pagingState)
        {
            this.flags = flags;
            this.names = names;
            this.columnCount = columnCount;
            this.pagingState = pagingState;
        }

        public Metadata copy()
        {
            return new Metadata(EnumSet.copyOf(flags), names, columnCount, pagingState);
        }

        // The maximum number of values that the ResultSet can hold. This can be bigger than columnCount due to CASSANDRA-4911
        public int valueCount()
        {
            return names == null ? columnCount : names.size();
        }

        public void addNonSerializedColumn(ColumnSpecification name)
        {
            // See comment above. Because columnCount doesn't account the newly added name, it
            // won't be serialized.
            names.add(name);
        }

        private boolean allInSameCF()
        {
            if (names == null)
                return false;

            assert !names.isEmpty();

            Iterator<ColumnSpecification> iter = names.iterator();
            ColumnSpecification first = iter.next();
            while (iter.hasNext())
            {
                ColumnSpecification name = iter.next();
                if (!name.ksName.equals(first.ksName) || !name.cfName.equals(first.cfName))
                    return false;
            }
            return true;
        }

        public void setHasMorePages(PagingState pagingState)
        {
            this.pagingState = pagingState;
            if (pagingState == null)
                flags.remove(Flag.HAS_MORE_PAGES);
            else
                flags.add(Flag.HAS_MORE_PAGES);
        }

        public void setSkipMetadata()
        {
            flags.add(Flag.NO_METADATA);
        }

        @Override
        public String toString()
        {
            StringBuilder sb = new StringBuilder();

            if (names == null)
            {
                sb.append("[").append(columnCount).append(" columns]");
            }
            else
            {
                for (ColumnSpecification name : names)
                {
                    sb.append("[").append(name.name.toString());
                    sb.append("(").append(name.ksName).append(", ").append(name.cfName).append(")");
                    sb.append(", ").append(name.type).append("]");
                }
            }
            if (flags.contains(Flag.HAS_MORE_PAGES))
                sb.append(" (to be continued)");
            return sb.toString();
        }

        private static class Codec implements CBCodec<Metadata>
        {
            public Metadata decode(ByteBuf body, int version)
            {
                // flags & column count
                int iflags = body.readInt();
                int columnCount = body.readInt();

                EnumSet<Flag> flags = Flag.deserialize(iflags);

                PagingState state = null;
                if (flags.contains(Flag.HAS_MORE_PAGES))
                    state = PagingState.deserialize(CBUtil.readValue(body));

                if (flags.contains(Flag.NO_METADATA))
                    return new Metadata(flags, null, columnCount, state);

                boolean globalTablesSpec = flags.contains(Flag.GLOBAL_TABLES_SPEC);

                String globalKsName = null;
                String globalCfName = null;
                if (globalTablesSpec)
                {
                    globalKsName = CBUtil.readString(body);
                    globalCfName = CBUtil.readString(body);
                }

                // metadata (names/types)
                List<ColumnSpecification> names = new ArrayList<ColumnSpecification>(columnCount);
                for (int i = 0; i < columnCount; i++)
                {
                    String ksName = globalTablesSpec ? globalKsName : CBUtil.readString(body);
                    String cfName = globalTablesSpec ? globalCfName : CBUtil.readString(body);
                    ColumnIdentifier colName = new ColumnIdentifier(CBUtil.readString(body), true);
                    AbstractType type = DataType.toType(DataType.codec.decodeOne(body, version));
                    names.add(new ColumnSpecification(ksName, cfName, colName, type));
                }
                return new Metadata(flags, names, names.size(), state);
            }

            public void encode(Metadata m, ByteBuf dest, int version)
            {
                boolean noMetadata = m.flags.contains(Flag.NO_METADATA);
                boolean globalTablesSpec = m.flags.contains(Flag.GLOBAL_TABLES_SPEC);
                boolean hasMorePages = m.flags.contains(Flag.HAS_MORE_PAGES);

                assert version > 1 || (!m.flags.contains(Flag.HAS_MORE_PAGES) && !noMetadata): "version = " + version + ", flags = " + m.flags;

                dest.writeInt(Flag.serialize(m.flags));
                dest.writeInt(m.columnCount);

                if (hasMorePages)
                    CBUtil.writeValue(m.pagingState.serialize(), dest);

                if (!noMetadata)
                {
                    if (globalTablesSpec)
                    {
                        CBUtil.writeString(m.names.get(0).ksName, dest);
                        CBUtil.writeString(m.names.get(0).cfName, dest);
                    }

                    for (int i = 0; i < m.columnCount; i++)
                    {
                        ColumnSpecification name = m.names.get(i);
                        if (!globalTablesSpec)
                        {
                            CBUtil.writeString(name.ksName, dest);
                            CBUtil.writeString(name.cfName, dest);
                        }
                        CBUtil.writeString(name.name.toString(), dest);
                        DataType.codec.writeOne(DataType.fromType(name.type, version), dest, version);
                    }
                }
            }

            public int encodedSize(Metadata m, int version)
            {
                boolean noMetadata = m.flags.contains(Flag.NO_METADATA);
                boolean globalTablesSpec = m.flags.contains(Flag.GLOBAL_TABLES_SPEC);
                boolean hasMorePages = m.flags.contains(Flag.HAS_MORE_PAGES);

                int size = 8;
                if (hasMorePages)
                    size += CBUtil.sizeOfValue(m.pagingState.serialize());

                if (!noMetadata)
                {
                    if (globalTablesSpec)
                    {
                        size += CBUtil.sizeOfString(m.names.get(0).ksName);
                        size += CBUtil.sizeOfString(m.names.get(0).cfName);
                    }

                    for (int i = 0; i < m.columnCount; i++)
                    {
                        ColumnSpecification name = m.names.get(i);
                        if (!globalTablesSpec)
                        {
                            size += CBUtil.sizeOfString(name.ksName);
                            size += CBUtil.sizeOfString(name.cfName);
                        }
                        size += CBUtil.sizeOfString(name.name.toString());
                        size += DataType.codec.oneSerializedSize(DataType.fromType(name.type, version), version);
                    }
                }
                return size;
            }
        }
    }

    public static enum Flag
    {
        // The order of that enum matters!!
        GLOBAL_TABLES_SPEC,
        HAS_MORE_PAGES,
        NO_METADATA;

        public static EnumSet<Flag> deserialize(int flags)
        {
            EnumSet<Flag> set = EnumSet.noneOf(Flag.class);
            Flag[] values = Flag.values();
            for (int n = 0; n < values.length; n++)
            {
                if ((flags & (1 << n)) != 0)
                    set.add(values[n]);
            }
            return set;
        }

        public static int serialize(EnumSet<Flag> flags)
        {
            int i = 0;
            for (Flag flag : flags)
                i |= 1 << flag.ordinal();
            return i;
        }
    }
}


File: src/java/org/apache/cassandra/cql3/UntypedResultSet.java
/*
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
 */
package org.apache.cassandra.cql3;

import java.net.InetAddress;
import java.nio.ByteBuffer;
import java.util.*;

import com.google.common.collect.AbstractIterator;

import org.apache.cassandra.cql3.statements.SelectStatement;
import org.apache.cassandra.db.marshal.*;
import org.apache.cassandra.exceptions.*;
import org.apache.cassandra.service.pager.QueryPager;

/** a utility for doing internal cql-based queries */
public abstract class UntypedResultSet implements Iterable<UntypedResultSet.Row>
{
    public static UntypedResultSet create(ResultSet rs)
    {
        return new FromResultSet(rs);
    }

    public static UntypedResultSet create(List<Map<String, ByteBuffer>> results)
    {
        return new FromResultList(results);
    }

    public static UntypedResultSet create(SelectStatement select, QueryPager pager, int pageSize)
    {
        return new FromPager(select, pager, pageSize);
    }

    public boolean isEmpty()
    {
        return size() == 0;
    }

    public abstract int size();
    public abstract Row one();

    // No implemented by all subclasses, but we use it when we know it's there (for tests)
    public abstract List<ColumnSpecification> metadata();

    private static class FromResultSet extends UntypedResultSet
    {
        private final ResultSet cqlRows;

        private FromResultSet(ResultSet cqlRows)
        {
            this.cqlRows = cqlRows;
        }

        public int size()
        {
            return cqlRows.size();
        }

        public Row one()
        {
            if (cqlRows.rows.size() != 1)
                throw new IllegalStateException("One row required, " + cqlRows.rows.size() + " found");
            return new Row(cqlRows.metadata.names, cqlRows.rows.get(0));
        }

        public Iterator<Row> iterator()
        {
            return new AbstractIterator<Row>()
            {
                Iterator<List<ByteBuffer>> iter = cqlRows.rows.iterator();

                protected Row computeNext()
                {
                    if (!iter.hasNext())
                        return endOfData();
                    return new Row(cqlRows.metadata.names, iter.next());
                }
            };
        }

        public List<ColumnSpecification> metadata()
        {
            return cqlRows.metadata.names;
        }
    }

    private static class FromResultList extends UntypedResultSet
    {
        private final List<Map<String, ByteBuffer>> cqlRows;

        private FromResultList(List<Map<String, ByteBuffer>> cqlRows)
        {
            this.cqlRows = cqlRows;
        }

        public int size()
        {
            return cqlRows.size();
        }

        public Row one()
        {
            if (cqlRows.size() != 1)
                throw new IllegalStateException("One row required, " + cqlRows.size() + " found");
            return new Row(cqlRows.get(0));
        }

        public Iterator<Row> iterator()
        {
            return new AbstractIterator<Row>()
            {
                Iterator<Map<String, ByteBuffer>> iter = cqlRows.iterator();

                protected Row computeNext()
                {
                    if (!iter.hasNext())
                        return endOfData();
                    return new Row(iter.next());
                }
            };
        }

        public List<ColumnSpecification> metadata()
        {
            throw new UnsupportedOperationException();
        }
    }

    private static class FromPager extends UntypedResultSet
    {
        private final SelectStatement select;
        private final QueryPager pager;
        private final int pageSize;
        private final List<ColumnSpecification> metadata;

        private FromPager(SelectStatement select, QueryPager pager, int pageSize)
        {
            this.select = select;
            this.pager = pager;
            this.pageSize = pageSize;
            this.metadata = select.getResultMetadata().names;
        }

        public int size()
        {
            throw new UnsupportedOperationException();
        }

        public Row one()
        {
            throw new UnsupportedOperationException();
        }

        public Iterator<Row> iterator()
        {
            return new AbstractIterator<Row>()
            {
                private Iterator<List<ByteBuffer>> currentPage;

                protected Row computeNext()
                {
                    try {
                        while (currentPage == null || !currentPage.hasNext())
                        {
                            if (pager.isExhausted())
                                return endOfData();
                            currentPage = select.process(pager.fetchPage(pageSize)).rows.iterator();
                        }
                        return new Row(metadata, currentPage.next());
                    } catch (RequestValidationException | RequestExecutionException e) {
                        throw new RuntimeException(e);
                    }
                }
            };
        }

        public List<ColumnSpecification> metadata()
        {
            return metadata;
        }
    }

    public static class Row
    {
        private final Map<String, ByteBuffer> data = new HashMap<>();
        private final List<ColumnSpecification> columns = new ArrayList<>();

        public Row(Map<String, ByteBuffer> data)
        {
            this.data.putAll(data);
        }

        public Row(List<ColumnSpecification> names, List<ByteBuffer> columns)
        {
            this.columns.addAll(names);
            for (int i = 0; i < names.size(); i++)
                data.put(names.get(i).name.toString(), columns.get(i));
        }

        public boolean has(String column)
        {
            // Note that containsKey won't work because we may have null values
            return data.get(column) != null;
        }

        public String getString(String column)
        {
            return UTF8Type.instance.compose(data.get(column));
        }

        public boolean getBoolean(String column)
        {
            return BooleanType.instance.compose(data.get(column));
        }

        public int getInt(String column)
        {
            return Int32Type.instance.compose(data.get(column));
        }

        public double getDouble(String column)
        {
            return DoubleType.instance.compose(data.get(column));
        }

        public ByteBuffer getBytes(String column)
        {
            return data.get(column);
        }

        public InetAddress getInetAddress(String column)
        {
            return InetAddressType.instance.compose(data.get(column));
        }

        public UUID getUUID(String column)
        {
            return UUIDType.instance.compose(data.get(column));
        }

        public Date getTimestamp(String column)
        {
            return TimestampType.instance.compose(data.get(column));
        }

        public long getLong(String column)
        {
            return LongType.instance.compose(data.get(column));
        }

        public <T> Set<T> getSet(String column, AbstractType<T> type)
        {
            ByteBuffer raw = data.get(column);
            return raw == null ? null : SetType.getInstance(type, true).compose(raw);
        }

        public <T> List<T> getList(String column, AbstractType<T> type)
        {
            ByteBuffer raw = data.get(column);
            return raw == null ? null : ListType.getInstance(type, true).compose(raw);
        }

        public <K, V> Map<K, V> getMap(String column, AbstractType<K> keyType, AbstractType<V> valueType)
        {
            ByteBuffer raw = data.get(column);
            return raw == null ? null : MapType.getInstance(keyType, valueType, true).compose(raw);
        }

        public List<ColumnSpecification> getColumns()
        {
            return columns;
        }

        @Override
        public String toString()
        {
            return data.toString();
        }
    }
}


File: src/java/org/apache/cassandra/cql3/statements/BatchStatement.java
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

import java.nio.ByteBuffer;
import java.util.*;
import java.util.concurrent.TimeUnit;

import com.google.common.base.Function;
import com.google.common.collect.*;

import org.apache.cassandra.config.DatabaseDescriptor;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import org.apache.cassandra.config.ColumnDefinition;
import org.apache.cassandra.cql3.*;
import org.apache.cassandra.db.*;
import org.apache.cassandra.db.composites.Composite;
import org.apache.cassandra.exceptions.*;
import org.apache.cassandra.service.ClientState;
import org.apache.cassandra.service.QueryState;
import org.apache.cassandra.service.StorageProxy;
import org.apache.cassandra.transport.messages.ResultMessage;
import org.apache.cassandra.utils.NoSpamLogger;

/**
 * A <code>BATCH</code> statement parsed from a CQL query.
 */
public class BatchStatement implements CQLStatement
{
    public static enum Type
    {
        LOGGED, UNLOGGED, COUNTER
    }

    private final int boundTerms;
    public final Type type;
    private final List<ModificationStatement> statements;
    private final Attributes attrs;
    private final boolean hasConditions;
    private static final Logger logger = LoggerFactory.getLogger(BatchStatement.class);
    private static final String unloggedBatchWarning = "Unlogged batch covering {} partition{} detected against table{} {}. You should use a logged batch for atomicity, or asynchronous writes for performance.";

    /**
     * Creates a new BatchStatement from a list of statements and a
     * Thrift consistency level.
     *
     * @param type       type of the batch
     * @param statements a list of UpdateStatements
     * @param attrs      additional attributes for statement (CL, timestamp, timeToLive)
     */
    public BatchStatement(int boundTerms, Type type, List<ModificationStatement> statements, Attributes attrs)
    {
        boolean hasConditions = false;
        for (ModificationStatement statement : statements)
            hasConditions |= statement.hasConditions();

        this.boundTerms = boundTerms;
        this.type = type;
        this.statements = statements;
        this.attrs = attrs;
        this.hasConditions = hasConditions;
    }

    public int getBoundTerms()
    {
        return boundTerms;
    }

    public void checkAccess(ClientState state) throws InvalidRequestException, UnauthorizedException
    {
        for (ModificationStatement statement : statements)
            statement.checkAccess(state);
    }

    // Validates a prepared batch statement without validating its nested statements.
    public void validate() throws InvalidRequestException
    {
        if (attrs.isTimeToLiveSet())
            throw new InvalidRequestException("Global TTL on the BATCH statement is not supported.");

        boolean timestampSet = attrs.isTimestampSet();
        if (timestampSet)
        {
            if (hasConditions)
                throw new InvalidRequestException("Cannot provide custom timestamp for conditional BATCH");
            if (type == Type.COUNTER)
                throw new InvalidRequestException("Cannot provide custom timestamp for counter BATCH");
        }

        boolean hasCounters = false;
        boolean hasNonCounters = false;

        for (ModificationStatement statement : statements)
        {
            if (timestampSet && statement.isCounter())
                throw new InvalidRequestException("Cannot provide custom timestamp for a BATCH containing counters");

            if (timestampSet && statement.isTimestampSet())
                throw new InvalidRequestException("Timestamp must be set either on BATCH or individual statements");

            if (type == Type.COUNTER && !statement.isCounter())
                throw new InvalidRequestException("Cannot include non-counter statement in a counter batch");

            if (type == Type.LOGGED && statement.isCounter())
                throw new InvalidRequestException("Cannot include a counter statement in a logged batch");

            if (statement.isCounter())
                hasCounters = true;
            else
                hasNonCounters = true;
        }

        if (hasCounters && hasNonCounters)
            throw new InvalidRequestException("Counter and non-counter mutations cannot exist in the same batch");

        if (hasConditions)
        {
            String ksName = null;
            String cfName = null;
            for (ModificationStatement stmt : statements)
            {
                if (ksName != null && (!stmt.keyspace().equals(ksName) || !stmt.columnFamily().equals(cfName)))
                    throw new InvalidRequestException("Batch with conditions cannot span multiple tables");
                ksName = stmt.keyspace();
                cfName = stmt.columnFamily();
            }
        }
    }

    // The batch itself will be validated in either Parsed#prepare() - for regular CQL3 batches,
    //   or in QueryProcessor.processBatch() - for native protocol batches.
    public void validate(ClientState state) throws InvalidRequestException
    {
        for (ModificationStatement statement : statements)
            statement.validate(state);
    }

    public List<ModificationStatement> getStatements()
    {
        return statements;
    }

    private Collection<? extends IMutation> getMutations(BatchQueryOptions options, boolean local, long now)
    throws RequestExecutionException, RequestValidationException
    {
        Map<String, Map<ByteBuffer, IMutation>> mutations = new HashMap<>();
        for (int i = 0; i < statements.size(); i++)
        {
            ModificationStatement statement = statements.get(i);
            QueryOptions statementOptions = options.forStatement(i);
            long timestamp = attrs.getTimestamp(now, statementOptions);
            addStatementMutations(statement, statementOptions, local, timestamp, mutations);
        }
        return unzipMutations(mutations);
    }

    private Collection<? extends IMutation> unzipMutations(Map<String, Map<ByteBuffer, IMutation>> mutations)
    {

        // The case where all statement where on the same keyspace is pretty common
        if (mutations.size() == 1)
            return mutations.values().iterator().next().values();


        List<IMutation> ms = new ArrayList<>();
        for (Map<ByteBuffer, IMutation> ksMap : mutations.values())
            ms.addAll(ksMap.values());

        return ms;
    }

    private void addStatementMutations(ModificationStatement statement,
                                       QueryOptions options,
                                       boolean local,
                                       long now,
                                       Map<String, Map<ByteBuffer, IMutation>> mutations)
    throws RequestExecutionException, RequestValidationException
    {
        String ksName = statement.keyspace();
        Map<ByteBuffer, IMutation> ksMap = mutations.get(ksName);
        if (ksMap == null)
        {
            ksMap = new HashMap<>();
            mutations.put(ksName, ksMap);
        }

        // The following does the same than statement.getMutations(), but we inline it here because
        // we don't want to recreate mutations every time as this is particularly inefficient when applying
        // multiple batch to the same partition (see #6737).
        List<ByteBuffer> keys = statement.buildPartitionKeyNames(options);
        Composite clusteringPrefix = statement.createClusteringPrefix(options);
        UpdateParameters params = statement.makeUpdateParameters(keys, clusteringPrefix, options, local, now);

        for (ByteBuffer key : keys)
        {
            IMutation mutation = ksMap.get(key);
            Mutation mut;
            if (mutation == null)
            {
                mut = new Mutation(ksName, key);
                mutation = statement.cfm.isCounter() ? new CounterMutation(mut, options.getConsistency()) : mut;
                ksMap.put(key, mutation);
            }
            else
            {
                mut = statement.cfm.isCounter() ? ((CounterMutation) mutation).getMutation() : (Mutation) mutation;
            }

            statement.addUpdateForKey(mut.addOrGet(statement.cfm), key, clusteringPrefix, params);
        }
    }

    /**
     * Checks batch size to ensure threshold is met. If not, a warning is logged.
     *
     * @param cfs ColumnFamilies that will store the batch's mutations.
     */
    public static void verifyBatchSize(Iterable<ColumnFamily> cfs)
    {
        long size = 0;
        long warnThreshold = DatabaseDescriptor.getBatchSizeWarnThreshold();

        for (ColumnFamily cf : cfs)
            size += cf.dataSize();

        if (size > warnThreshold)
        {
            Set<String> ksCfPairs = new HashSet<>();
            for (ColumnFamily cf : cfs)
                ksCfPairs.add(String.format("%s.%s", cf.metadata().ksName, cf.metadata().cfName));

            String format = "Batch of prepared statements for {} is of size {}, exceeding specified threshold of {} by {}.";
            logger.warn(format, ksCfPairs, size, warnThreshold, size - warnThreshold);
        }
    }

    private void verifyBatchType(Collection<? extends IMutation> mutations)
    {
        if (type != Type.LOGGED && mutations.size() > 1)
        {
            Set<String> ksCfPairs = new HashSet<>();
            Set<ByteBuffer> keySet = new HashSet<>();

            for (IMutation im : mutations)
            {
                keySet.add(im.key());
                for (ColumnFamily cf : im.getColumnFamilies())
                    ksCfPairs.add(String.format("%s.%s", cf.metadata().ksName, cf.metadata().cfName));
            }

            NoSpamLogger.log(logger, NoSpamLogger.Level.WARN, 1, TimeUnit.MINUTES, unloggedBatchWarning,
                             keySet.size(), keySet.size() == 1 ? "" : "s",
                             ksCfPairs.size() == 1 ? "" : "s", ksCfPairs);
        }
    }

    public ResultMessage execute(QueryState queryState, QueryOptions options) throws RequestExecutionException, RequestValidationException
    {
        return execute(queryState, BatchQueryOptions.withoutPerStatementVariables(options));
    }

    public ResultMessage execute(QueryState queryState, BatchQueryOptions options) throws RequestExecutionException, RequestValidationException
    {
        return execute(queryState, options, false, options.getTimestamp(queryState));
    }

    private ResultMessage execute(QueryState queryState, BatchQueryOptions options, boolean local, long now)
    throws RequestExecutionException, RequestValidationException
    {
        if (options.getConsistency() == null)
            throw new InvalidRequestException("Invalid empty consistency level");
        if (options.getSerialConsistency() == null)
            throw new InvalidRequestException("Invalid empty serial consistency level");

        if (hasConditions)
            return executeWithConditions(options, queryState);

        executeWithoutConditions(getMutations(options, local, now), options.getConsistency());
        return new ResultMessage.Void();
    }

    private void executeWithoutConditions(Collection<? extends IMutation> mutations, ConsistencyLevel cl) throws RequestExecutionException, RequestValidationException
    {
        // Extract each collection of cfs from it's IMutation and then lazily concatenate all of them into a single Iterable.
        Iterable<ColumnFamily> cfs = Iterables.concat(Iterables.transform(mutations, new Function<IMutation, Collection<ColumnFamily>>()
        {
            public Collection<ColumnFamily> apply(IMutation im)
            {
                return im.getColumnFamilies();
            }
        }));

        verifyBatchSize(cfs);
        verifyBatchType(mutations);

        boolean mutateAtomic = (type == Type.LOGGED && mutations.size() > 1);
        StorageProxy.mutateWithTriggers(mutations, cl, mutateAtomic);
    }

    private ResultMessage executeWithConditions(BatchQueryOptions options, QueryState state)
    throws RequestExecutionException, RequestValidationException
    {
        long now = state.getTimestamp();
        ByteBuffer key = null;
        String ksName = null;
        String cfName = null;
        CQL3CasRequest casRequest = null;
        Set<ColumnDefinition> columnsWithConditions = new LinkedHashSet<>();

        for (int i = 0; i < statements.size(); i++)
        {
            ModificationStatement statement = statements.get(i);
            QueryOptions statementOptions = options.forStatement(i);
            long timestamp = attrs.getTimestamp(now, statementOptions);
            List<ByteBuffer> pks = statement.buildPartitionKeyNames(statementOptions);
            if (pks.size() > 1)
                throw new IllegalArgumentException("Batch with conditions cannot span multiple partitions (you cannot use IN on the partition key)");
            if (key == null)
            {
                key = pks.get(0);
                ksName = statement.cfm.ksName;
                cfName = statement.cfm.cfName;
                casRequest = new CQL3CasRequest(statement.cfm, key, true);
            }
            else if (!key.equals(pks.get(0)))
            {
                throw new InvalidRequestException("Batch with conditions cannot span multiple partitions");
            }

            Composite clusteringPrefix = statement.createClusteringPrefix(statementOptions);
            if (statement.hasConditions())
            {
                statement.addConditions(clusteringPrefix, casRequest, statementOptions);
                // As soon as we have a ifNotExists, we set columnsWithConditions to null so that everything is in the resultSet
                if (statement.hasIfNotExistCondition() || statement.hasIfExistCondition())
                    columnsWithConditions = null;
                else if (columnsWithConditions != null)
                    Iterables.addAll(columnsWithConditions, statement.getColumnsWithConditions());
            }
            casRequest.addRowUpdate(clusteringPrefix, statement, statementOptions, timestamp);
        }

        ColumnFamily result = StorageProxy.cas(ksName, cfName, key, casRequest, options.getSerialConsistency(), options.getConsistency(), state.getClientState());

        return new ResultMessage.Rows(ModificationStatement.buildCasResultSet(ksName, key, cfName, result, columnsWithConditions, true, options.forStatement(0)));
    }

    public ResultMessage executeInternal(QueryState queryState, QueryOptions options) throws RequestValidationException, RequestExecutionException
    {
        assert !hasConditions;
        for (IMutation mutation : getMutations(BatchQueryOptions.withoutPerStatementVariables(options), true, queryState.getTimestamp()))
        {
            // We don't use counters internally.
            assert mutation instanceof Mutation;
            ((Mutation) mutation).apply();
        }
        return null;
    }

    public interface BatchVariables
    {
        public List<ByteBuffer> getVariablesForStatement(int statementInBatch);
    }

    public String toString()
    {
        return String.format("BatchStatement(type=%s, statements=%s)", type, statements);
    }

    public static class Parsed extends CFStatement
    {
        private final Type type;
        private final Attributes.Raw attrs;
        private final List<ModificationStatement.Parsed> parsedStatements;

        public Parsed(Type type, Attributes.Raw attrs, List<ModificationStatement.Parsed> parsedStatements)
        {
            super(null);
            this.type = type;
            this.attrs = attrs;
            this.parsedStatements = parsedStatements;
        }

        @Override
        public void prepareKeyspace(ClientState state) throws InvalidRequestException
        {
            for (ModificationStatement.Parsed statement : parsedStatements)
                statement.prepareKeyspace(state);
        }

        public ParsedStatement.Prepared prepare() throws InvalidRequestException
        {
            VariableSpecifications boundNames = getBoundVariables();

            List<ModificationStatement> statements = new ArrayList<>(parsedStatements.size());
            for (ModificationStatement.Parsed parsed : parsedStatements)
                statements.add(parsed.prepare(boundNames));

            Attributes prepAttrs = attrs.prepare("[batch]", "[batch]");
            prepAttrs.collectMarkerSpecification(boundNames);

            BatchStatement batchStatement = new BatchStatement(boundNames.size(), type, statements, prepAttrs);
            batchStatement.validate();

            return new ParsedStatement.Prepared(batchStatement, boundNames);
        }
    }
}


File: src/java/org/apache/cassandra/cql3/statements/CQL3CasRequest.java
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

import java.nio.ByteBuffer;
import java.util.*;

import com.google.common.collect.HashMultimap;
import com.google.common.collect.Multimap;
import org.apache.cassandra.cql3.*;
import org.apache.cassandra.config.CFMetaData;
import org.apache.cassandra.db.*;
import org.apache.cassandra.db.composites.Composite;
import org.apache.cassandra.db.filter.*;
import org.apache.cassandra.db.marshal.CompositeType;
import org.apache.cassandra.exceptions.InvalidRequestException;
import org.apache.cassandra.service.CASRequest;
import org.apache.cassandra.utils.Pair;

/**
 * Processed CAS conditions and update on potentially multiple rows of the same partition.
 */
public class CQL3CasRequest implements CASRequest
{
    private final CFMetaData cfm;
    private final ByteBuffer key;
    private final long now;
    private final boolean isBatch;

    // We index RowCondition by the prefix of the row they applied to for 2 reasons:
    //   1) this allows to keep things sorted to build the ColumnSlice array below
    //   2) this allows to detect when contradictory conditions are set (not exists with some other conditions on the same row)
    private final SortedMap<Composite, RowCondition> conditions;

    private final List<RowUpdate> updates = new ArrayList<>();

    public CQL3CasRequest(CFMetaData cfm, ByteBuffer key, boolean isBatch)
    {
        this.cfm = cfm;
        // When checking if conditions apply, we want to use a fixed reference time for a whole request to check
        // for expired cells. Note that this is unrelated to the cell timestamp.
        this.now = System.currentTimeMillis();
        this.key = key;
        this.conditions = new TreeMap<>(cfm.comparator);
        this.isBatch = isBatch;
    }

    public void addRowUpdate(Composite prefix, ModificationStatement stmt, QueryOptions options, long timestamp)
    {
        updates.add(new RowUpdate(prefix, stmt, options, timestamp));
    }

    public void addNotExist(Composite prefix) throws InvalidRequestException
    {
        RowCondition previous = conditions.put(prefix, new NotExistCondition(prefix, now));
        if (previous != null && !(previous instanceof NotExistCondition))
        {
            // these should be prevented by the parser, but it doesn't hurt to check
            if (previous instanceof ExistCondition)
                throw new InvalidRequestException("Cannot mix IF EXISTS and IF NOT EXISTS conditions for the same row");
            else
                throw new InvalidRequestException("Cannot mix IF conditions and IF NOT EXISTS for the same row");
        }
    }

    public void addExist(Composite prefix) throws InvalidRequestException
    {
        RowCondition previous = conditions.put(prefix, new ExistCondition(prefix, now));
        // this should be prevented by the parser, but it doesn't hurt to check
        if (previous != null && previous instanceof NotExistCondition)
            throw new InvalidRequestException("Cannot mix IF EXISTS and IF NOT EXISTS conditions for the same row");
    }

    public void addConditions(Composite prefix, Collection<ColumnCondition> conds, QueryOptions options) throws InvalidRequestException
    {
        RowCondition condition = conditions.get(prefix);
        if (condition == null)
        {
            condition = new ColumnsConditions(prefix, now);
            conditions.put(prefix, condition);
        }
        else if (!(condition instanceof ColumnsConditions))
        {
            throw new InvalidRequestException("Cannot mix IF conditions and IF NOT EXISTS for the same row");
        }
        ((ColumnsConditions)condition).addConditions(conds, options);
    }

    public IDiskAtomFilter readFilter()
    {
        assert !conditions.isEmpty();
        ColumnSlice[] slices = new ColumnSlice[conditions.size()];
        int i = 0;
        // We always read CQL rows entirely as on CAS failure we want to be able to distinguish between "row exists
        // but all values for which there were conditions are null" and "row doesn't exists", and we can't rely on the
        // row marker for that (see #6623)
        for (Composite prefix : conditions.keySet())
            slices[i++] = prefix.slice();

        int toGroup = cfm.comparator.isDense() ? -1 : cfm.clusteringColumns().size();
        slices = ColumnSlice.deoverlapSlices(slices, cfm.comparator);
        assert ColumnSlice.validateSlices(slices, cfm.comparator, false);
        return new SliceQueryFilter(slices, false, slices.length, toGroup);
    }

    public boolean appliesTo(ColumnFamily current) throws InvalidRequestException
    {
        for (RowCondition condition : conditions.values())
        {
            if (!condition.appliesTo(current))
                return false;
        }
        return true;
    }

    public ColumnFamily makeUpdates(ColumnFamily current) throws InvalidRequestException
    {
        ColumnFamily cf = ArrayBackedSortedColumns.factory.create(cfm);
        for (RowUpdate upd : updates)
            upd.applyUpdates(current, cf);

        if (isBatch)
            BatchStatement.verifyBatchSize(Collections.singleton(cf));

        return cf;
    }

    /**
     * Due to some operation on lists, we can't generate the update that a given Modification statement does before
     * we get the values read by the initial read of Paxos. A RowUpdate thus just store the relevant information
     * (include the statement iself) to generate those updates. We'll have multiple RowUpdate for a Batch, otherwise
     * we'll have only one.
     */
    private class RowUpdate
    {
        private final Composite rowPrefix;
        private final ModificationStatement stmt;
        private final QueryOptions options;
        private final long timestamp;

        private RowUpdate(Composite rowPrefix, ModificationStatement stmt, QueryOptions options, long timestamp)
        {
            this.rowPrefix = rowPrefix;
            this.stmt = stmt;
            this.options = options;
            this.timestamp = timestamp;
        }

        public void applyUpdates(ColumnFamily current, ColumnFamily updates) throws InvalidRequestException
        {
            Map<ByteBuffer, CQL3Row> map = null;
            if (stmt.requiresRead())
            {
                // Uses the "current" values read by Paxos for lists operation that requires a read
                Iterator<CQL3Row> iter = cfm.comparator.CQL3RowBuilder(cfm, now).group(current.iterator(new ColumnSlice[]{ rowPrefix.slice() }));
                if (iter.hasNext())
                {
                    map = Collections.singletonMap(key, iter.next());
                    assert !iter.hasNext() : "We shoudn't be updating more than one CQL row per-ModificationStatement";
                }
            }

            UpdateParameters params = new UpdateParameters(cfm, options, timestamp, stmt.getTimeToLive(options), map);
            stmt.addUpdateForKey(updates, key, rowPrefix, params);
        }
    }

    private static abstract class RowCondition
    {
        public final Composite rowPrefix;
        protected final long now;

        protected RowCondition(Composite rowPrefix, long now)
        {
            this.rowPrefix = rowPrefix;
            this.now = now;
        }

        public abstract boolean appliesTo(ColumnFamily current) throws InvalidRequestException;
    }

    private static class NotExistCondition extends RowCondition
    {
        private NotExistCondition(Composite rowPrefix, long now)
        {
            super(rowPrefix, now);
        }

        public boolean appliesTo(ColumnFamily current)
        {
            if (current == null)
                return true;

            Iterator<Cell> iter = current.iterator(new ColumnSlice[]{ rowPrefix.slice() });
            while (iter.hasNext())
                if (iter.next().isLive(now))
                    return false;
            return true;
        }
    }

    private static class ExistCondition extends RowCondition
    {
        private ExistCondition(Composite rowPrefix, long now)
        {
            super (rowPrefix, now);
        }

        public boolean appliesTo(ColumnFamily current)
        {
            if (current == null)
                return false;

            Iterator<Cell> iter = current.iterator(new ColumnSlice[]{ rowPrefix.slice() });
            while (iter.hasNext())
                if (iter.next().isLive(now))
                    return true;
            return false;
        }
    }

    private static class ColumnsConditions extends RowCondition
    {
        private final Multimap<Pair<ColumnIdentifier, ByteBuffer>, ColumnCondition.Bound> conditions = HashMultimap.create();

        private ColumnsConditions(Composite rowPrefix, long now)
        {
            super(rowPrefix, now);
        }

        public void addConditions(Collection<ColumnCondition> conds, QueryOptions options) throws InvalidRequestException
        {
            for (ColumnCondition condition : conds)
            {
                ColumnCondition.Bound current = condition.bind(options);
                conditions.put(Pair.create(condition.column.name, current.getCollectionElementValue()), current);
            }
        }

        public boolean appliesTo(ColumnFamily current) throws InvalidRequestException
        {
            if (current == null)
                return conditions.isEmpty();

            for (ColumnCondition.Bound condition : conditions.values())
                if (!condition.appliesTo(rowPrefix, current, now))
                    return false;
            return true;
        }
    }
}


File: src/java/org/apache/cassandra/cql3/statements/ModificationStatement.java
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

import java.nio.ByteBuffer;
import java.util.*;

import com.google.common.base.Function;
import com.google.common.collect.Iterables;

import org.apache.cassandra.auth.Permission;
import org.apache.cassandra.config.CFMetaData;
import org.apache.cassandra.config.ColumnDefinition;
import org.apache.cassandra.cql3.*;
import org.apache.cassandra.db.*;
import org.apache.cassandra.db.composites.CBuilder;
import org.apache.cassandra.db.composites.Composite;
import org.apache.cassandra.db.filter.ColumnSlice;
import org.apache.cassandra.db.filter.SliceQueryFilter;
import org.apache.cassandra.db.marshal.BooleanType;
import org.apache.cassandra.exceptions.*;
import org.apache.cassandra.service.ClientState;
import org.apache.cassandra.service.QueryState;
import org.apache.cassandra.service.StorageProxy;
import org.apache.cassandra.thrift.ThriftValidation;
import org.apache.cassandra.transport.messages.ResultMessage;
import org.apache.cassandra.utils.Pair;

/*
 * Abstract parent class of individual modifications, i.e. INSERT, UPDATE and DELETE.
 */
public abstract class ModificationStatement implements CQLStatement
{
    private static final ColumnIdentifier CAS_RESULT_COLUMN = new ColumnIdentifier("[applied]", false);

    public static enum StatementType { INSERT, UPDATE, DELETE }
    public final StatementType type;

    private final int boundTerms;
    public final CFMetaData cfm;
    public final Attributes attrs;

    protected final Map<ColumnIdentifier, Restriction> processedKeys = new HashMap<>();
    private final List<Operation> columnOperations = new ArrayList<Operation>();

    // Separating normal and static conditions makes things somewhat easier
    private List<ColumnCondition> columnConditions;
    private List<ColumnCondition> staticConditions;
    private boolean ifNotExists;
    private boolean ifExists;

    private boolean hasNoClusteringColumns = true;

    private boolean setsStaticColumns;
    private boolean setsRegularColumns;

    private final Function<ColumnCondition, ColumnDefinition> getColumnForCondition = new Function<ColumnCondition, ColumnDefinition>()
    {
        public ColumnDefinition apply(ColumnCondition cond)
        {
            return cond.column;
        }
    };

    public ModificationStatement(StatementType type, int boundTerms, CFMetaData cfm, Attributes attrs)
    {
        this.type = type;
        this.boundTerms = boundTerms;
        this.cfm = cfm;
        this.attrs = attrs;
    }

    public abstract boolean requireFullClusteringKey();
    public abstract void addUpdateForKey(ColumnFamily updates, ByteBuffer key, Composite prefix, UpdateParameters params) throws InvalidRequestException;

    public int getBoundTerms()
    {
        return boundTerms;
    }

    public String keyspace()
    {
        return cfm.ksName;
    }

    public String columnFamily()
    {
        return cfm.cfName;
    }

    public boolean isCounter()
    {
        return cfm.isCounter();
    }

    public long getTimestamp(long now, QueryOptions options) throws InvalidRequestException
    {
        return attrs.getTimestamp(now, options);
    }

    public boolean isTimestampSet()
    {
        return attrs.isTimestampSet();
    }

    public int getTimeToLive(QueryOptions options) throws InvalidRequestException
    {
        return attrs.getTimeToLive(options);
    }

    public void checkAccess(ClientState state) throws InvalidRequestException, UnauthorizedException
    {
        state.hasColumnFamilyAccess(keyspace(), columnFamily(), Permission.MODIFY);

        // CAS updates can be used to simulate a SELECT query, so should require Permission.SELECT as well.
        if (hasConditions())
            state.hasColumnFamilyAccess(keyspace(), columnFamily(), Permission.SELECT);
    }

    public void validate(ClientState state) throws InvalidRequestException
    {
        if (hasConditions() && attrs.isTimestampSet())
            throw new InvalidRequestException("Cannot provide custom timestamp for conditional updates");

        if (isCounter() && attrs.isTimestampSet())
            throw new InvalidRequestException("Cannot provide custom timestamp for counter updates");

        if (isCounter() && attrs.isTimeToLiveSet())
            throw new InvalidRequestException("Cannot provide custom TTL for counter updates");
    }

    public void addOperation(Operation op)
    {
        if (op.column.isStatic())
            setsStaticColumns = true;
        else
            setsRegularColumns = true;
        columnOperations.add(op);
    }

    public List<Operation> getOperations()
    {
        return columnOperations;
    }

    public Iterable<ColumnDefinition> getColumnsWithConditions()
    {
        if (ifNotExists || ifExists)
            return null;

        return Iterables.concat(columnConditions == null ? Collections.<ColumnDefinition>emptyList() : Iterables.transform(columnConditions, getColumnForCondition),
                                staticConditions == null ? Collections.<ColumnDefinition>emptyList() : Iterables.transform(staticConditions, getColumnForCondition));
    }

    public void addCondition(ColumnCondition cond)
    {
        List<ColumnCondition> conds = null;
        if (cond.column.isStatic())
        {
            setsStaticColumns = true;
            if (staticConditions == null)
                staticConditions = new ArrayList<ColumnCondition>();
            conds = staticConditions;
        }
        else
        {
            setsRegularColumns = true;
            if (columnConditions == null)
                columnConditions = new ArrayList<ColumnCondition>();
            conds = columnConditions;
        }
        conds.add(cond);
    }

    public void setIfNotExistCondition()
    {
        ifNotExists = true;
    }

    public boolean hasIfNotExistCondition()
    {
        return ifNotExists;
    }

    public void setIfExistCondition()
    {
        ifExists = true;
    }

    public boolean hasIfExistCondition()
    {
        return ifExists;
    }

    private void addKeyValues(ColumnDefinition def, Restriction values) throws InvalidRequestException
    {
        if (def.kind == ColumnDefinition.Kind.CLUSTERING_COLUMN)
            hasNoClusteringColumns = false;
        if (processedKeys.put(def.name, values) != null)
            throw new InvalidRequestException(String.format("Multiple definitions found for PRIMARY KEY part %s", def.name));
    }

    public void addKeyValue(ColumnDefinition def, Term value) throws InvalidRequestException
    {
        addKeyValues(def, new SingleColumnRestriction.EQ(value, false));
    }

    public void processWhereClause(List<Relation> whereClause, VariableSpecifications names) throws InvalidRequestException
    {
        for (Relation relation : whereClause)
        {
            if (relation.isMultiColumn())
            {
                throw new InvalidRequestException(
                        String.format("Multi-column relations cannot be used in WHERE clauses for UPDATE and DELETE statements: %s", relation));
            }
            SingleColumnRelation rel = (SingleColumnRelation) relation;

            if (rel.onToken)
                throw new InvalidRequestException(String.format("The token function cannot be used in WHERE clauses for UPDATE and DELETE statements: %s", relation));

            ColumnIdentifier id = rel.getEntity().prepare(cfm);
            ColumnDefinition def = cfm.getColumnDefinition(id);
            if (def == null)
                throw new InvalidRequestException(String.format("Unknown key identifier %s", id));

            switch (def.kind)
            {
                case PARTITION_KEY:
                case CLUSTERING_COLUMN:
                    Restriction restriction;

                    if (rel.operator() == Operator.EQ)
                    {
                        Term t = rel.getValue().prepare(keyspace(), def);
                        t.collectMarkerSpecification(names);
                        restriction = new SingleColumnRestriction.EQ(t, false);
                    }
                    else if (def.kind == ColumnDefinition.Kind.PARTITION_KEY && rel.operator() == Operator.IN)
                    {
                        if (rel.getValue() != null)
                        {
                            Term t = rel.getValue().prepare(keyspace(), def);
                            t.collectMarkerSpecification(names);
                            restriction = new SingleColumnRestriction.InWithMarker((Lists.Marker)t);
                        }
                        else
                        {
                            List<Term> values = new ArrayList<Term>(rel.getInValues().size());
                            for (Term.Raw raw : rel.getInValues())
                            {
                                Term t = raw.prepare(keyspace(), def);
                                t.collectMarkerSpecification(names);
                                values.add(t);
                            }
                            restriction = new SingleColumnRestriction.InWithValues(values);
                        }
                    }
                    else
                    {
                        throw new InvalidRequestException(String.format("Invalid operator %s for PRIMARY KEY part %s", rel.operator(), def.name));
                    }

                    addKeyValues(def, restriction);
                    break;
                default:
                    throw new InvalidRequestException(String.format("Non PRIMARY KEY %s found in where clause", def.name));
            }
        }
    }

    public List<ByteBuffer> buildPartitionKeyNames(QueryOptions options)
    throws InvalidRequestException
    {
        CBuilder keyBuilder = cfm.getKeyValidatorAsCType().builder();
        List<ByteBuffer> keys = new ArrayList<ByteBuffer>();
        for (ColumnDefinition def : cfm.partitionKeyColumns())
        {
            Restriction r = processedKeys.get(def.name);
            if (r == null)
                throw new InvalidRequestException(String.format("Missing mandatory PRIMARY KEY part %s", def.name));

            List<ByteBuffer> values = r.values(options);

            if (keyBuilder.remainingCount() == 1)
            {
                for (ByteBuffer val : values)
                {
                    if (val == null)
                        throw new InvalidRequestException(String.format("Invalid null value for partition key part %s", def.name));
                    ByteBuffer key = keyBuilder.buildWith(val).toByteBuffer();
                    ThriftValidation.validateKey(cfm, key);
                    keys.add(key);
                }
            }
            else
            {
                if (values.size() != 1)
                    throw new InvalidRequestException("IN is only supported on the last column of the partition key");
                ByteBuffer val = values.get(0);
                if (val == null)
                    throw new InvalidRequestException(String.format("Invalid null value for partition key part %s", def.name));
                keyBuilder.add(val);
            }
        }
        return keys;
    }

    public Composite createClusteringPrefix(QueryOptions options)
    throws InvalidRequestException
    {
        // If the only updated/deleted columns are static, then we don't need clustering columns.
        // And in fact, unless it is an INSERT, we reject if clustering colums are provided as that
        // suggest something unintended. For instance, given:
        //   CREATE TABLE t (k int, v int, s int static, PRIMARY KEY (k, v))
        // it can make sense to do:
        //   INSERT INTO t(k, v, s) VALUES (0, 1, 2)
        // but both
        //   UPDATE t SET s = 3 WHERE k = 0 AND v = 1
        //   DELETE v FROM t WHERE k = 0 AND v = 1
        // sounds like you don't really understand what your are doing.
        if (setsStaticColumns && !setsRegularColumns)
        {
            // If we set no non-static columns, then it's fine not to have clustering columns
            if (hasNoClusteringColumns)
                return cfm.comparator.staticPrefix();

            // If we do have clustering columns however, then either it's an INSERT and the query is valid
            // but we still need to build a proper prefix, or it's not an INSERT, and then we want to reject
            // (see above)
            if (type != StatementType.INSERT)
            {
                for (ColumnDefinition def : cfm.clusteringColumns())
                    if (processedKeys.get(def.name) != null)
                        throw new InvalidRequestException(String.format("Invalid restriction on clustering column %s since the %s statement modifies only static columns", def.name, type));
                // we should get there as it contradicts hasNoClusteringColumns == false
                throw new AssertionError();
            }
        }

        return createClusteringPrefixBuilderInternal(options);
    }

    private Composite createClusteringPrefixBuilderInternal(QueryOptions options)
    throws InvalidRequestException
    {
        CBuilder builder = cfm.comparator.prefixBuilder();
        ColumnDefinition firstEmptyKey = null;
        for (ColumnDefinition def : cfm.clusteringColumns())
        {
            Restriction r = processedKeys.get(def.name);
            if (r == null)
            {
                firstEmptyKey = def;
                if (requireFullClusteringKey() && !cfm.comparator.isDense() && cfm.comparator.isCompound())
                    throw new InvalidRequestException(String.format("Missing mandatory PRIMARY KEY part %s", def.name));
            }
            else if (firstEmptyKey != null)
            {
                throw new InvalidRequestException(String.format("Missing PRIMARY KEY part %s since %s is set", firstEmptyKey.name, def.name));
            }
            else
            {
                List<ByteBuffer> values = r.values(options);
                assert values.size() == 1; // We only allow IN for row keys so far
                ByteBuffer val = values.get(0);
                if (val == null)
                    throw new InvalidRequestException(String.format("Invalid null value for clustering key part %s", def.name));
                builder.add(val);
            }
        }
        return builder.build();
    }

    protected ColumnDefinition getFirstEmptyKey()
    {
        for (ColumnDefinition def : cfm.clusteringColumns())
        {
            if (processedKeys.get(def.name) == null)
                return def;
        }
        return null;
    }

    public boolean requiresRead()
    {
        // Lists SET operation incurs a read.
        for (Operation op : columnOperations)
            if (op.requiresRead())
                return true;

        return false;
    }

    protected Map<ByteBuffer, CQL3Row> readRequiredRows(Collection<ByteBuffer> partitionKeys, Composite clusteringPrefix, boolean local, ConsistencyLevel cl)
    throws RequestExecutionException, RequestValidationException
    {
        if (!requiresRead())
            return null;

        try
        {
            cl.validateForRead(keyspace());
        }
        catch (InvalidRequestException e)
        {
            throw new InvalidRequestException(String.format("Write operation require a read but consistency %s is not supported on reads", cl));
        }

        ColumnSlice[] slices = new ColumnSlice[]{ clusteringPrefix.slice() };
        List<ReadCommand> commands = new ArrayList<ReadCommand>(partitionKeys.size());
        long now = System.currentTimeMillis();
        for (ByteBuffer key : partitionKeys)
            commands.add(new SliceFromReadCommand(keyspace(),
                                                  key,
                                                  columnFamily(),
                                                  now,
                                                  new SliceQueryFilter(slices, false, Integer.MAX_VALUE)));

        List<Row> rows = local
                       ? SelectStatement.readLocally(keyspace(), commands)
                       : StorageProxy.read(commands, cl);

        Map<ByteBuffer, CQL3Row> map = new HashMap<ByteBuffer, CQL3Row>();
        for (Row row : rows)
        {
            if (row.cf == null || row.cf.isEmpty())
                continue;

            Iterator<CQL3Row> iter = cfm.comparator.CQL3RowBuilder(cfm, now).group(row.cf.getSortedColumns().iterator());
            if (iter.hasNext())
            {
                map.put(row.key.getKey(), iter.next());
                // We can only update one CQ3Row per partition key at a time (we don't allow IN for clustering key)
                assert !iter.hasNext();
            }
        }
        return map;
    }

    public boolean hasConditions()
    {
        return ifNotExists
            || ifExists
            || (columnConditions != null && !columnConditions.isEmpty())
            || (staticConditions != null && !staticConditions.isEmpty());
    }

    public ResultMessage execute(QueryState queryState, QueryOptions options)
    throws RequestExecutionException, RequestValidationException
    {
        if (options.getConsistency() == null)
            throw new InvalidRequestException("Invalid empty consistency level");

        if (hasConditions() && options.getProtocolVersion() == 1)
            throw new InvalidRequestException("Conditional updates are not supported by the protocol version in use. You need to upgrade to a driver using the native protocol v2.");

        return hasConditions()
             ? executeWithCondition(queryState, options)
             : executeWithoutCondition(queryState, options);
    }

    private ResultMessage executeWithoutCondition(QueryState queryState, QueryOptions options)
    throws RequestExecutionException, RequestValidationException
    {
        ConsistencyLevel cl = options.getConsistency();
        if (isCounter())
            cl.validateCounterForWrite(cfm);
        else
            cl.validateForWrite(cfm.ksName);

        Collection<? extends IMutation> mutations = getMutations(options, false, options.getTimestamp(queryState));
        if (!mutations.isEmpty())
            StorageProxy.mutateWithTriggers(mutations, cl, false);

        return null;
    }

    public ResultMessage executeWithCondition(QueryState queryState, QueryOptions options)
    throws RequestExecutionException, RequestValidationException
    {
        List<ByteBuffer> keys = buildPartitionKeyNames(options);
        // We don't support IN for CAS operation so far
        if (keys.size() > 1)
            throw new InvalidRequestException("IN on the partition key is not supported with conditional updates");

        ByteBuffer key = keys.get(0);
        long now = options.getTimestamp(queryState);
        Composite prefix = createClusteringPrefix(options);

        CQL3CasRequest request = new CQL3CasRequest(cfm, key, false);
        addConditions(prefix, request, options);
        request.addRowUpdate(prefix, this, options, now);

        ColumnFamily result = StorageProxy.cas(keyspace(),
                                               columnFamily(),
                                               key,
                                               request,
                                               options.getSerialConsistency(),
                                               options.getConsistency(),
                                               queryState.getClientState());
        return new ResultMessage.Rows(buildCasResultSet(key, result, options));
    }

    public void addConditions(Composite clusteringPrefix, CQL3CasRequest request, QueryOptions options) throws InvalidRequestException
    {
        if (ifNotExists)
        {
            // If we use ifNotExists, if the statement applies to any non static columns, then the condition is on the row of the non-static
            // columns and the prefix should be the clusteringPrefix. But if only static columns are set, then the ifNotExists apply to the existence
            // of any static columns and we should use the prefix for the "static part" of the partition.
            request.addNotExist(clusteringPrefix);
        }
        else if (ifExists)
        {
            request.addExist(clusteringPrefix);
        }
        else
        {
            if (columnConditions != null)
                request.addConditions(clusteringPrefix, columnConditions, options);
            if (staticConditions != null)
                request.addConditions(cfm.comparator.staticPrefix(), staticConditions, options);
        }
    }

    private ResultSet buildCasResultSet(ByteBuffer key, ColumnFamily cf, QueryOptions options) throws InvalidRequestException
    {
        return buildCasResultSet(keyspace(), key, columnFamily(), cf, getColumnsWithConditions(), false, options);
    }

    public static ResultSet buildCasResultSet(String ksName, ByteBuffer key, String cfName, ColumnFamily cf, Iterable<ColumnDefinition> columnsWithConditions, boolean isBatch, QueryOptions options)
    throws InvalidRequestException
    {
        boolean success = cf == null;

        ColumnSpecification spec = new ColumnSpecification(ksName, cfName, CAS_RESULT_COLUMN, BooleanType.instance);
        ResultSet.Metadata metadata = new ResultSet.Metadata(Collections.singletonList(spec));
        List<List<ByteBuffer>> rows = Collections.singletonList(Collections.singletonList(BooleanType.instance.decompose(success)));

        ResultSet rs = new ResultSet(metadata, rows);
        return success ? rs : merge(rs, buildCasFailureResultSet(key, cf, columnsWithConditions, isBatch, options));
    }

    private static ResultSet merge(ResultSet left, ResultSet right)
    {
        if (left.size() == 0)
            return right;
        else if (right.size() == 0)
            return left;

        assert left.size() == 1;
        int size = left.metadata.names.size() + right.metadata.names.size();
        List<ColumnSpecification> specs = new ArrayList<ColumnSpecification>(size);
        specs.addAll(left.metadata.names);
        specs.addAll(right.metadata.names);
        List<List<ByteBuffer>> rows = new ArrayList<>(right.size());
        for (int i = 0; i < right.size(); i++)
        {
            List<ByteBuffer> row = new ArrayList<ByteBuffer>(size);
            row.addAll(left.rows.get(0));
            row.addAll(right.rows.get(i));
            rows.add(row);
        }
        return new ResultSet(new ResultSet.Metadata(specs), rows);
    }

    private static ResultSet buildCasFailureResultSet(ByteBuffer key, ColumnFamily cf, Iterable<ColumnDefinition> columnsWithConditions, boolean isBatch, QueryOptions options)
    throws InvalidRequestException
    {
        CFMetaData cfm = cf.metadata();
        Selection selection;
        if (columnsWithConditions == null)
        {
            selection = Selection.wildcard(cfm);
        }
        else
        {
            // We can have multiple conditions on the same columns (for collections) so use a set
            // to avoid duplicate, but preserve the order just to it follows the order of IF in the query in general
            Set<ColumnDefinition> defs = new LinkedHashSet<>();
            // Adding the partition key for batches to disambiguate if the conditions span multipe rows (we don't add them outside
            // of batches for compatibility sakes).
            if (isBatch)
            {
                defs.addAll(cfm.partitionKeyColumns());
                defs.addAll(cfm.clusteringColumns());
            }
            for (ColumnDefinition def : columnsWithConditions)
                defs.add(def);
            selection = Selection.forColumns(new ArrayList<>(defs));
        }

        long now = System.currentTimeMillis();
        Selection.ResultSetBuilder builder = selection.resultSetBuilder(now);
        SelectStatement.forSelection(cfm, selection).processColumnFamily(key, cf, options, now, builder);

        return builder.build();
    }

    public ResultMessage executeInternal(QueryState queryState, QueryOptions options) throws RequestValidationException, RequestExecutionException
    {
        if (hasConditions())
            throw new UnsupportedOperationException();

        for (IMutation mutation : getMutations(options, true, queryState.getTimestamp()))
        {
            // We don't use counters internally.
            assert mutation instanceof Mutation;

            ((Mutation) mutation).apply();
        }
        return null;
    }

    /**
     * Convert statement into a list of mutations to apply on the server
     *
     * @param options value for prepared statement markers
     * @param local if true, any requests (for collections) performed by getMutation should be done locally only.
     * @param now the current timestamp in microseconds to use if no timestamp is user provided.
     *
     * @return list of the mutations
     * @throws InvalidRequestException on invalid requests
     */
    private Collection<? extends IMutation> getMutations(QueryOptions options, boolean local, long now)
    throws RequestExecutionException, RequestValidationException
    {
        List<ByteBuffer> keys = buildPartitionKeyNames(options);
        Composite clusteringPrefix = createClusteringPrefix(options);

        UpdateParameters params = makeUpdateParameters(keys, clusteringPrefix, options, local, now);

        Collection<IMutation> mutations = new ArrayList<IMutation>(keys.size());
        for (ByteBuffer key: keys)
        {
            ThriftValidation.validateKey(cfm, key);
            ColumnFamily cf = ArrayBackedSortedColumns.factory.create(cfm);
            addUpdateForKey(cf, key, clusteringPrefix, params);
            Mutation mut = new Mutation(cfm.ksName, key, cf);

            mutations.add(isCounter() ? new CounterMutation(mut, options.getConsistency()) : mut);
        }
        return mutations;
    }

    public UpdateParameters makeUpdateParameters(Collection<ByteBuffer> keys,
                                                 Composite prefix,
                                                 QueryOptions options,
                                                 boolean local,
                                                 long now)
    throws RequestExecutionException, RequestValidationException
    {
        // Some lists operation requires reading
        Map<ByteBuffer, CQL3Row> rows = readRequiredRows(keys, prefix, local, options.getConsistency());
        return new UpdateParameters(cfm, options, getTimestamp(now, options), getTimeToLive(options), rows);
    }

    /**
     * If there are conditions on the statement, this is called after the where clause and conditions have been
     * processed to check that they are compatible.
     * @throws InvalidRequestException
     */
    protected void validateWhereClauseForConditions() throws InvalidRequestException
    {
        //  no-op by default
    }

    public static abstract class Parsed extends CFStatement
    {
        protected final Attributes.Raw attrs;
        protected final List<Pair<ColumnIdentifier.Raw, ColumnCondition.Raw>> conditions;
        private final boolean ifNotExists;
        private final boolean ifExists;

        protected Parsed(CFName name, Attributes.Raw attrs, List<Pair<ColumnIdentifier.Raw, ColumnCondition.Raw>> conditions, boolean ifNotExists, boolean ifExists)
        {
            super(name);
            this.attrs = attrs;
            this.conditions = conditions == null ? Collections.<Pair<ColumnIdentifier.Raw, ColumnCondition.Raw>>emptyList() : conditions;
            this.ifNotExists = ifNotExists;
            this.ifExists = ifExists;
        }

        public ParsedStatement.Prepared prepare() throws InvalidRequestException
        {
            VariableSpecifications boundNames = getBoundVariables();
            ModificationStatement statement = prepare(boundNames);
            return new ParsedStatement.Prepared(statement, boundNames);
        }

        public ModificationStatement prepare(VariableSpecifications boundNames) throws InvalidRequestException
        {
            CFMetaData metadata = ThriftValidation.validateColumnFamily(keyspace(), columnFamily());

            Attributes preparedAttributes = attrs.prepare(keyspace(), columnFamily());
            preparedAttributes.collectMarkerSpecification(boundNames);

            ModificationStatement stmt = prepareInternal(metadata, boundNames, preparedAttributes);

            if (ifNotExists || ifExists || !conditions.isEmpty())
            {
                if (stmt.isCounter())
                    throw new InvalidRequestException("Conditional updates are not supported on counter tables");

                if (attrs.timestamp != null)
                    throw new InvalidRequestException("Cannot provide custom timestamp for conditional updates");

                if (ifNotExists)
                {
                    // To have both 'IF NOT EXISTS' and some other conditions doesn't make sense.
                    // So far this is enforced by the parser, but let's assert it for sanity if ever the parse changes.
                    assert conditions.isEmpty();
                    assert !ifExists;
                    stmt.setIfNotExistCondition();
                }
                else if (ifExists)
                {
                    assert conditions.isEmpty();
                    assert !ifNotExists;
                    stmt.setIfExistCondition();
                }
                else
                {
                    for (Pair<ColumnIdentifier.Raw, ColumnCondition.Raw> entry : conditions)
                    {
                        ColumnIdentifier id = entry.left.prepare(metadata);
                        ColumnDefinition def = metadata.getColumnDefinition(id);
                        if (def == null)
                            throw new InvalidRequestException(String.format("Unknown identifier %s", id));

                        ColumnCondition condition = entry.right.prepare(keyspace(), def);
                        condition.collectMarkerSpecification(boundNames);

                        switch (def.kind)
                        {
                            case PARTITION_KEY:
                            case CLUSTERING_COLUMN:
                                throw new InvalidRequestException(String.format("PRIMARY KEY column '%s' cannot have IF conditions", id));
                            default:
                                stmt.addCondition(condition);
                                break;
                        }
                    }
                }

                stmt.validateWhereClauseForConditions();
            }
            return stmt;
        }

        protected abstract ModificationStatement prepareInternal(CFMetaData cfm, VariableSpecifications boundNames, Attributes attrs) throws InvalidRequestException;
    }
}


File: src/java/org/apache/cassandra/cql3/statements/SelectStatement.java
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

import java.nio.ByteBuffer;
import java.util.*;

import com.google.common.annotations.VisibleForTesting;
import com.google.common.base.Joiner;
import com.google.common.base.Objects;
import com.google.common.base.Predicate;
import com.google.common.collect.AbstractIterator;
import com.google.common.collect.Iterables;
import com.google.common.collect.Iterators;

import org.apache.cassandra.auth.Permission;
import org.apache.cassandra.cql3.*;
import org.apache.cassandra.cql3.statements.SingleColumnRestriction.Contains;
import org.apache.cassandra.db.composites.*;
import org.apache.cassandra.transport.messages.ResultMessage;
import org.apache.cassandra.config.CFMetaData;
import org.apache.cassandra.config.ColumnDefinition;
import org.apache.cassandra.db.*;
import org.apache.cassandra.db.filter.*;
import org.apache.cassandra.db.index.SecondaryIndex;
import org.apache.cassandra.db.index.SecondaryIndexManager;
import org.apache.cassandra.db.marshal.*;
import org.apache.cassandra.dht.*;
import org.apache.cassandra.exceptions.*;
import org.apache.cassandra.service.ClientState;
import org.apache.cassandra.service.QueryState;
import org.apache.cassandra.service.StorageProxy;
import org.apache.cassandra.service.StorageService;
import org.apache.cassandra.service.pager.*;
import org.apache.cassandra.db.ConsistencyLevel;
import org.apache.cassandra.thrift.ThriftValidation;
import org.apache.cassandra.serializers.MarshalException;
import org.apache.cassandra.utils.ByteBufferUtil;
import org.apache.cassandra.utils.FBUtilities;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

/**
 * Encapsulates a completely parsed SELECT query, including the target
 * column family, expression, result count, and ordering clause.
 *
 * A number of public methods here are only used internally. However,
 * many of these are made accessible for the benefit of custom
 * QueryHandler implementations, so before reducing their accessibility
 * due consideration should be given.
 */
public class SelectStatement implements CQLStatement
{
    private static final Logger logger = LoggerFactory.getLogger(SelectStatement.class);

    private static final int DEFAULT_COUNT_PAGE_SIZE = 10000;

    /**
     * In the current version a query containing duplicate values in an IN restriction on the partition key will
     * cause the same record to be returned multiple time. This behavior will be changed in 3.0 but until then
     * we will log a warning the first time this problem occurs.
     */
    private static volatile boolean HAS_LOGGED_WARNING_FOR_IN_RESTRICTION_WITH_DUPLICATES;

    private final int boundTerms;
    public final CFMetaData cfm;
    public final Parameters parameters;
    private final Selection selection;
    private final Term limit;

    /** Restrictions on partitioning columns */
    private final Restriction[] keyRestrictions;

    /** Restrictions on clustering columns */
    private final Restriction[] columnRestrictions;

    /** Restrictions on non-primary key columns (i.e. secondary index restrictions) */
    private final Map<ColumnIdentifier, Restriction> metadataRestrictions = new HashMap<ColumnIdentifier, Restriction>();

    // The map keys are the name of the columns that must be converted into IndexExpressions if a secondary index need
    // to be used. The value specify if the column has an index that can be used to for the relation in which the column
    // is specified.
    private final Map<ColumnDefinition, Boolean> restrictedColumns = new HashMap<ColumnDefinition, Boolean>();
    private Restriction.Slice sliceRestriction;

    private boolean isReversed;
    private boolean onToken;
    private boolean isKeyRange;
    private boolean keyIsInRelation;
    private boolean usesSecondaryIndexing;

    private Map<ColumnIdentifier, Integer> orderingIndexes;

    private boolean selectsStaticColumns;
    private boolean selectsOnlyStaticColumns;

    // Used by forSelection below
    private static final Parameters defaultParameters = new Parameters(Collections.<ColumnIdentifier.Raw, Boolean>emptyMap(), false, false, null, false);

    private static final Predicate<ColumnDefinition> isStaticFilter = new Predicate<ColumnDefinition>()
    {
        public boolean apply(ColumnDefinition def)
        {
            return def.isStatic();
        }
    };

    public SelectStatement(CFMetaData cfm, int boundTerms, Parameters parameters, Selection selection, Term limit)
    {
        this.cfm = cfm;
        this.boundTerms = boundTerms;
        this.selection = selection;
        this.keyRestrictions = new Restriction[cfm.partitionKeyColumns().size()];
        this.columnRestrictions = new Restriction[cfm.clusteringColumns().size()];
        this.parameters = parameters;
        this.limit = limit;

        // Now gather a few info on whether we should bother with static columns or not for this statement
        initStaticColumnsInfo();
    }

    private void initStaticColumnsInfo()
    {
        if (!cfm.hasStaticColumns())
            return;

        // If it's a wildcard, we do select static but not only them
        if (selection.isWildcard())
        {
            selectsStaticColumns = true;
            return;
        }

        // Otherwise, check the selected columns
        selectsStaticColumns = !Iterables.isEmpty(Iterables.filter(selection.getColumns(), isStaticFilter));
        selectsOnlyStaticColumns = true;
        for (ColumnDefinition def : selection.getColumns())
        {
            if (def.kind != ColumnDefinition.Kind.PARTITION_KEY && def.kind != ColumnDefinition.Kind.STATIC)
            {
                selectsOnlyStaticColumns = false;
                break;
            }
        }
    }

    // Creates a simple select based on the given selection.
    // Note that the results select statement should not be used for actual queries, but only for processing already
    // queried data through processColumnFamily.
    static SelectStatement forSelection(CFMetaData cfm, Selection selection)
    {
        return new SelectStatement(cfm, 0, defaultParameters, selection, null);
    }

    public ResultSet.Metadata getResultMetadata()
    {
        return parameters.isCount
             ? ResultSet.makeCountMetadata(keyspace(), columnFamily(), parameters.countAlias)
             : selection.getResultMetadata();
    }

    /**
     * May be used by custom QueryHandler implementations
     */
    public int getBoundTerms()
    {
        return boundTerms;
    }

    /**
     * May be used by custom QueryHandler implementations
     */
    public Selection getSelection()
    {
        return selection;
    }

    public void checkAccess(ClientState state) throws InvalidRequestException, UnauthorizedException
    {
        state.hasColumnFamilyAccess(keyspace(), columnFamily(), Permission.SELECT);
    }

    public void validate(ClientState state) throws InvalidRequestException
    {
        // Nothing to do, all validation has been done by RawStatement.prepare()
    }

    public ResultMessage.Rows execute(QueryState state, QueryOptions options) throws RequestExecutionException, RequestValidationException
    {
        ConsistencyLevel cl = options.getConsistency();
        if (cl == null)
            throw new InvalidRequestException("Invalid empty consistency level");

        cl.validateForRead(keyspace());

        int limit = getLimit(options);
        long now = System.currentTimeMillis();
        Pageable command = getPageableCommand(options, limit, now);

        int pageSize = options.getPageSize();
        // A count query will never be paged for the user, but we always page it internally to avoid OOM.
        // If we user provided a pageSize we'll use that to page internally (because why not), otherwise we use our default
        // Note that if there are some nodes in the cluster with a version less than 2.0, we can't use paging (CASSANDRA-6707).
        if (parameters.isCount && pageSize <= 0)
            pageSize = DEFAULT_COUNT_PAGE_SIZE;

        if (pageSize <= 0 || command == null || !QueryPagers.mayNeedPaging(command, pageSize))
        {
            return execute(command, options, limit, now, state);
        }
        else
        {
            QueryPager pager = QueryPagers.pager(command, cl, state.getClientState(), options.getPagingState());
            if (parameters.isCount)
                return pageCountQuery(pager, options, pageSize, now, limit);

            // We can't properly do post-query ordering if we page (see #6722)
            if (needsPostQueryOrdering())
                throw new InvalidRequestException("Cannot page queries with both ORDER BY and a IN restriction on the partition key; you must either remove the "
                                                + "ORDER BY or the IN and sort client side, or disable paging for this query");

            List<Row> page = pager.fetchPage(pageSize);
            ResultMessage.Rows msg = processResults(page, options, limit, now);

            if (!pager.isExhausted())
                msg.result.metadata.setHasMorePages(pager.state());

            return msg;
        }
    }

    private Pageable getPageableCommand(QueryOptions options, int limit, long now) throws RequestValidationException
    {
        int limitForQuery = updateLimitForQuery(limit);
        if (isKeyRange || usesSecondaryIndexing)
            return getRangeCommand(options, limitForQuery, now);

        List<ReadCommand> commands = getSliceCommands(options, limitForQuery, now);
        return commands == null ? null : new Pageable.ReadCommands(commands, limitForQuery);
    }

    public Pageable getPageableCommand(QueryOptions options) throws RequestValidationException
    {
        return getPageableCommand(options, getLimit(options), System.currentTimeMillis());
    }

    private ResultMessage.Rows execute(Pageable command, QueryOptions options, int limit, long now, QueryState state) throws RequestValidationException, RequestExecutionException
    {
        List<Row> rows;
        if (command == null)
        {
            rows = Collections.<Row>emptyList();
        }
        else
        {
            rows = command instanceof Pageable.ReadCommands
                 ? StorageProxy.read(((Pageable.ReadCommands)command).commands, options.getConsistency(), state.getClientState())
                 : StorageProxy.getRangeSlice((RangeSliceCommand)command, options.getConsistency());
        }

        return processResults(rows, options, limit, now);
    }

    private ResultMessage.Rows pageCountQuery(QueryPager pager, QueryOptions options, int pageSize, long now, int limit) throws RequestValidationException, RequestExecutionException
    {
        int count = 0;
        while (!pager.isExhausted())
        {
            int maxLimit = pager.maxRemaining();
            logger.debug("New maxLimit for paged count query is {}", maxLimit);
            ResultSet rset = process(pager.fetchPage(pageSize), options, maxLimit, now);
            count += rset.rows.size();
        }

        // We sometimes query one more result than the user limit asks to handle exclusive bounds with compact tables (see updateLimitForQuery).
        // So do make sure the count is not greater than what the user asked for.
        ResultSet result = ResultSet.makeCountResult(keyspace(), columnFamily(), Math.min(count, limit), parameters.countAlias);
        return new ResultMessage.Rows(result);
    }

    public ResultMessage.Rows processResults(List<Row> rows, QueryOptions options, int limit, long now) throws RequestValidationException
    {
        // Even for count, we need to process the result as it'll group some column together in sparse column families
        ResultSet rset = process(rows, options, limit, now);
        rset = parameters.isCount ? rset.makeCountResult(parameters.countAlias) : rset;
        return new ResultMessage.Rows(rset);
    }

    static List<Row> readLocally(String keyspaceName, List<ReadCommand> cmds)
    {
        Keyspace keyspace = Keyspace.open(keyspaceName);
        List<Row> rows = new ArrayList<Row>(cmds.size());
        for (ReadCommand cmd : cmds)
            rows.add(cmd.getRow(keyspace));
        return rows;
    }

    public ResultMessage.Rows executeInternal(QueryState state, QueryOptions options) throws RequestExecutionException, RequestValidationException
    {
        int limit = getLimit(options);
        long now = System.currentTimeMillis();
        Pageable command = getPageableCommand(options, limit, now);
        List<Row> rows = command == null
                       ? Collections.<Row>emptyList()
                       : (command instanceof Pageable.ReadCommands
                          ? readLocally(keyspace(), ((Pageable.ReadCommands)command).commands)
                          : ((RangeSliceCommand)command).executeLocally());

        return processResults(rows, options, limit, now);
    }

    public ResultSet process(List<Row> rows) throws InvalidRequestException
    {
        assert !parameters.isCount; // not yet needed
        QueryOptions options = QueryOptions.DEFAULT;
        return process(rows, options, getLimit(options), System.currentTimeMillis());
    }

    public String keyspace()
    {
        return cfm.ksName;
    }

    public String columnFamily()
    {
        return cfm.cfName;
    }

    private List<ReadCommand> getSliceCommands(QueryOptions options, int limit, long now) throws RequestValidationException
    {
        Collection<ByteBuffer> keys = getKeys(options);
        if (keys.isEmpty()) // in case of IN () for (the last column of) the partition key.
            return null;

        List<ReadCommand> commands = new ArrayList<>(keys.size());

        IDiskAtomFilter filter = makeFilter(options, limit);
        if (filter == null)
            return null;

        // Note that we use the total limit for every key, which is potentially inefficient.
        // However, IN + LIMIT is not a very sensible choice.
        for (ByteBuffer key : keys)
        {
            QueryProcessor.validateKey(key);
            // We should not share the slice filter amongst the commands (hence the cloneShallow), due to
            // SliceQueryFilter not being immutable due to its columnCounter used by the lastCounted() method
            // (this is fairly ugly and we should change that but that's probably not a tiny refactor to do that cleanly)
            commands.add(ReadCommand.create(keyspace(), ByteBufferUtil.clone(key), columnFamily(), now, filter.cloneShallow()));
        }

        return commands;
    }

    private RangeSliceCommand getRangeCommand(QueryOptions options, int limit, long now) throws RequestValidationException
    {
        IDiskAtomFilter filter = makeFilter(options, limit);
        if (filter == null)
            return null;

        List<IndexExpression> expressions = getValidatedIndexExpressions(options);
        // The LIMIT provided by the user is the number of CQL row he wants returned.
        // We want to have getRangeSlice to count the number of columns, not the number of keys.
        AbstractBounds<RowPosition> keyBounds = getKeyBounds(options);
        return keyBounds == null
             ? null
             : new RangeSliceCommand(keyspace(), columnFamily(), now,  filter, keyBounds, expressions, limit, !parameters.isDistinct, false);
    }

    /**
     * May be used by custom QueryHandler implementations
     */
    public AbstractBounds<RowPosition> getKeyBounds(QueryOptions options) throws InvalidRequestException
    {
        IPartitioner p = StorageService.getPartitioner();

        if (onToken)
        {
            Token startToken = getTokenBound(Bound.START, options, p);
            Token endToken = getTokenBound(Bound.END, options, p);

            boolean includeStart = includeKeyBound(Bound.START);
            boolean includeEnd = includeKeyBound(Bound.END);

            /*
             * If we ask SP.getRangeSlice() for (token(200), token(200)], it will happily return the whole ring.
             * However, wrapping range doesn't really make sense for CQL, and we want to return an empty result
             * in that case (CASSANDRA-5573). So special case to create a range that is guaranteed to be empty.
             *
             * In practice, we want to return an empty result set if either startToken > endToken, or both are
             * equal but one of the bound is excluded (since [a, a] can contains something, but not (a, a], [a, a)
             * or (a, a)). Note though that in the case where startToken or endToken is the minimum token, then
             * this special case rule should not apply.
             */
            int cmp = startToken.compareTo(endToken);
            if (!startToken.isMinimum() && !endToken.isMinimum() && (cmp > 0 || (cmp == 0 && (!includeStart || !includeEnd))))
                return null;

            RowPosition start = includeStart ? startToken.minKeyBound() : startToken.maxKeyBound();
            RowPosition end = includeEnd ? endToken.maxKeyBound() : endToken.minKeyBound();

            return new Range<RowPosition>(start, end);
        }
        else
        {
            ByteBuffer startKeyBytes = getKeyBound(Bound.START, options);
            ByteBuffer finishKeyBytes = getKeyBound(Bound.END, options);

            RowPosition startKey = RowPosition.ForKey.get(startKeyBytes, p);
            RowPosition finishKey = RowPosition.ForKey.get(finishKeyBytes, p);

            if (startKey.compareTo(finishKey) > 0 && !finishKey.isMinimum(p))
                return null;

            if (includeKeyBound(Bound.START))
            {
                return includeKeyBound(Bound.END)
                     ? new Bounds<RowPosition>(startKey, finishKey)
                     : new IncludingExcludingBounds<RowPosition>(startKey, finishKey);
            }
            else
            {
                return includeKeyBound(Bound.END)
                     ? new Range<RowPosition>(startKey, finishKey)
                     : new ExcludingBounds<RowPosition>(startKey, finishKey);
            }
        }
    }

    private ColumnSlice makeStaticSlice()
    {
        // Note: we could use staticPrefix.start() for the start bound, but EMPTY gives us the
        // same effect while saving a few CPU cycles.
        return isReversed
             ? new ColumnSlice(cfm.comparator.staticPrefix().end(), Composites.EMPTY)
             : new ColumnSlice(Composites.EMPTY, cfm.comparator.staticPrefix().end());
    }

    private IDiskAtomFilter makeFilter(QueryOptions options, int limit)
    throws InvalidRequestException
    {
        int toGroup = cfm.comparator.isDense() ? -1 : cfm.clusteringColumns().size();
        if (parameters.isDistinct)
        {
            // For distinct, we only care about fetching the beginning of each partition. If we don't have
            // static columns, we in fact only care about the first cell, so we query only that (we don't "group").
            // If we do have static columns, we do need to fetch the first full group (to have the static columns values).

            // See the comments on IGNORE_TOMBSTONED_PARTITIONS and CASSANDRA-8490 for why we use a special value for
            // DISTINCT queries on the partition key only.
            toGroup = selectsStaticColumns ? toGroup : SliceQueryFilter.IGNORE_TOMBSTONED_PARTITIONS;
            return new SliceQueryFilter(ColumnSlice.ALL_COLUMNS_ARRAY, false, 1, toGroup);
        }
        else if (isColumnRange())
        {
            List<Composite> startBounds = getRequestedBound(Bound.START, options);
            List<Composite> endBounds = getRequestedBound(Bound.END, options);
            assert startBounds.size() == endBounds.size();

            // Handles fetching static columns. Note that for 2i, the filter is just used to restrict
            // the part of the index to query so adding the static slice would be useless and confusing.
            // For 2i, static columns are retrieve in CompositesSearcher with each index hit.
            ColumnSlice staticSlice = selectsStaticColumns && !usesSecondaryIndexing
                                    ? makeStaticSlice()
                                    : null;

            // The case where startBounds == 1 is common enough that it's worth optimizing
            if (startBounds.size() == 1)
            {
                ColumnSlice slice = new ColumnSlice(startBounds.get(0), endBounds.get(0));
                if (slice.isAlwaysEmpty(cfm.comparator, isReversed))
                    return staticSlice == null ? null : sliceFilter(staticSlice, limit, toGroup);

                if (staticSlice == null)
                    return sliceFilter(slice, limit, toGroup);

                if (isReversed)
                    return slice.includes(cfm.comparator.reverseComparator(), staticSlice.start)
                            ? sliceFilter(new ColumnSlice(slice.start, staticSlice.finish), limit, toGroup)
                            : sliceFilter(new ColumnSlice[]{ slice, staticSlice }, limit, toGroup);
                else
                    return slice.includes(cfm.comparator, staticSlice.finish)
                            ? sliceFilter(new ColumnSlice(staticSlice.start, slice.finish), limit, toGroup)
                            : sliceFilter(new ColumnSlice[]{ staticSlice, slice }, limit, toGroup);
            }

            List<ColumnSlice> l = new ArrayList<ColumnSlice>(startBounds.size());
            for (int i = 0; i < startBounds.size(); i++)
            {
                ColumnSlice slice = new ColumnSlice(startBounds.get(i), endBounds.get(i));
                if (!slice.isAlwaysEmpty(cfm.comparator, isReversed))
                    l.add(slice);
            }

            if (l.isEmpty())
                return staticSlice == null ? null : sliceFilter(staticSlice, limit, toGroup);
            if (staticSlice == null)
                return sliceFilter(l.toArray(new ColumnSlice[l.size()]), limit, toGroup);

            // The slices should not overlap. We know the slices built from startBounds/endBounds don't, but if there is
            // a static slice, it could overlap with the 2nd slice. Check for it and correct if that's the case
            ColumnSlice[] slices;
            if (isReversed)
            {
                if (l.get(l.size() - 1).includes(cfm.comparator.reverseComparator(), staticSlice.start))
                {
                    slices = l.toArray(new ColumnSlice[l.size()]);
                    slices[slices.length-1] = new ColumnSlice(slices[slices.length-1].start, Composites.EMPTY);
                }
                else
                {
                    slices = l.toArray(new ColumnSlice[l.size()+1]);
                    slices[slices.length-1] = staticSlice;
                }
            }
            else
            {
                if (l.get(0).includes(cfm.comparator, staticSlice.finish))
                {
                    slices = new ColumnSlice[l.size()];
                    slices[0] = new ColumnSlice(Composites.EMPTY, l.get(0).finish);
                    for (int i = 1; i < l.size(); i++)
                        slices[i] = l.get(i);
                }
                else
                {
                    slices = new ColumnSlice[l.size()+1];
                    slices[0] = staticSlice;
                    for (int i = 0; i < l.size(); i++)
                        slices[i+1] = l.get(i);
                }
            }
            return sliceFilter(slices, limit, toGroup);
        }
        else
        {
            SortedSet<CellName> cellNames = getRequestedColumns(options);
            if (cellNames == null) // in case of IN () for the last column of the key
                return null;
            QueryProcessor.validateCellNames(cellNames, cfm.comparator);
            return new NamesQueryFilter(cellNames, true);
        }
    }

    private SliceQueryFilter sliceFilter(ColumnSlice slice, int limit, int toGroup)
    {
        return sliceFilter(new ColumnSlice[]{ slice }, limit, toGroup);
    }

    private SliceQueryFilter sliceFilter(ColumnSlice[] slices, int limit, int toGroup)
    {
        assert ColumnSlice.validateSlices(slices, cfm.comparator, isReversed) : String.format("Invalid slices: " + Arrays.toString(slices) + (isReversed ? " (reversed)" : ""));
        return new SliceQueryFilter(slices, isReversed, limit, toGroup);
    }

    /**
     * May be used by custom QueryHandler implementations
     */
    public int getLimit(QueryOptions options) throws InvalidRequestException
    {
        int l = Integer.MAX_VALUE;
        if (limit != null)
        {
            ByteBuffer b = limit.bindAndGet(options);
            if (b == null)
                throw new InvalidRequestException("Invalid null value of limit");

            try
            {
                Int32Type.instance.validate(b);
                l = Int32Type.instance.compose(b);
            }
            catch (MarshalException e)
            {
                throw new InvalidRequestException("Invalid limit value");
            }
        }

        if (l <= 0)
            throw new InvalidRequestException("LIMIT must be strictly positive");

        return l;
    }

    private int updateLimitForQuery(int limit)
    {
        // Internally, we don't support exclusive bounds for slices. Instead, we query one more element if necessary
        // and exclude it later (in processColumnFamily)
        return sliceRestriction != null && (!sliceRestriction.isInclusive(Bound.START) || !sliceRestriction.isInclusive(Bound.END)) && limit != Integer.MAX_VALUE
             ? limit + 1
             : limit;
    }

    private Collection<ByteBuffer> getKeys(final QueryOptions options) throws InvalidRequestException
    {
        List<ByteBuffer> keys = new ArrayList<ByteBuffer>();
        CBuilder builder = cfm.getKeyValidatorAsCType().builder();
        for (ColumnDefinition def : cfm.partitionKeyColumns())
        {
            Restriction r = keyRestrictions[def.position()];
            assert r != null && !r.isSlice();

            List<ByteBuffer> values = r.values(options);

            if (builder.remainingCount() == 1)
            {
                if (values.size() > 1 && !HAS_LOGGED_WARNING_FOR_IN_RESTRICTION_WITH_DUPLICATES  && containsDuplicates(values))
                {
                    // This approach does not fully prevent race conditions but it is not a big deal.
                    HAS_LOGGED_WARNING_FOR_IN_RESTRICTION_WITH_DUPLICATES = true;
                    logger.warn("SELECT queries with IN restrictions on the partition key containing duplicate values will return duplicate rows.");
                }

                for (ByteBuffer val : values)
                {
                    if (val == null)
                        throw new InvalidRequestException(String.format("Invalid null value for partition key part %s", def.name));
                    keys.add(builder.buildWith(val).toByteBuffer());
                }
            }
            else
            {
                // Note: for backward compatibility reasons, we let INs with 1 value slide
                if (values.size() != 1)
                    throw new InvalidRequestException("IN is only supported on the last column of the partition key");
                ByteBuffer val = values.get(0);
                if (val == null)
                    throw new InvalidRequestException(String.format("Invalid null value for partition key part %s", def.name));
                builder.add(val);
            }
        }
        return keys;
    }

    /**
     * Checks if the specified list contains duplicate values.
     *
     * @param values the values to check
     * @return <code>true</code> if the specified list contains duplicate values, <code>false</code> otherwise.
     */
    private static boolean containsDuplicates(List<ByteBuffer> values)
    {
        return new HashSet<>(values).size() < values.size();
    }

    private ByteBuffer getKeyBound(Bound b, QueryOptions options) throws InvalidRequestException
    {
        // Deal with unrestricted partition key components (special-casing is required to deal with 2i queries on the first
        // component of a composite partition key).
        for (int i = 0; i < keyRestrictions.length; i++)
            if (keyRestrictions[i] == null)
                return ByteBufferUtil.EMPTY_BYTE_BUFFER;

        // We deal with IN queries for keys in other places, so we know buildBound will return only one result
        return buildBound(b, cfm.partitionKeyColumns(), keyRestrictions, false, cfm.getKeyValidatorAsCType(), options).get(0).toByteBuffer();
    }

    private Token getTokenBound(Bound b, QueryOptions options, IPartitioner p) throws InvalidRequestException
    {
        assert onToken;

        Restriction restriction = keyRestrictions[0];

        assert !restriction.isMultiColumn() : "Unexpectedly got a multi-column restriction on a partition key for a range query";
        SingleColumnRestriction keyRestriction = (SingleColumnRestriction)restriction;

        ByteBuffer value;
        if (keyRestriction.isEQ())
        {
            value = keyRestriction.values(options).get(0);
        }
        else
        {
            SingleColumnRestriction.Slice slice = (SingleColumnRestriction.Slice)keyRestriction;
            if (!slice.hasBound(b))
                return p.getMinimumToken();

            value = slice.bound(b, options);
        }

        if (value == null)
            throw new InvalidRequestException("Invalid null token value");
        return p.getTokenFactory().fromByteArray(value);
    }

    private boolean includeKeyBound(Bound b)
    {
        for (Restriction r : keyRestrictions)
        {
            if (r == null)
                return true;
            else if (r.isSlice())
            {
                assert !r.isMultiColumn() : "Unexpectedly got multi-column restriction on partition key";
                return ((SingleColumnRestriction.Slice)r).isInclusive(b);
            }
        }
        // All equality
        return true;
    }

    private boolean isColumnRange()
    {
        // Due to CASSANDRA-5762, we always do a slice for CQL3 tables (not dense, composite).
        // Static CF (non dense but non composite) never entails a column slice however
        if (!cfm.comparator.isDense())
            return cfm.comparator.isCompound();

        // Otherwise (i.e. for compact table where we don't have a row marker anyway and thus don't care about CASSANDRA-5762),
        // it is a range query if it has at least one the column alias for which no relation is defined or is not EQ.
        for (Restriction r : columnRestrictions)
        {
            if (r == null || r.isSlice())
                return true;
        }
        return false;
    }

    private SortedSet<CellName> getRequestedColumns(QueryOptions options) throws InvalidRequestException
    {
        // Note: getRequestedColumns don't handle static columns, but due to CASSANDRA-5762
        // we always do a slice for CQL3 tables, so it's ok to ignore them here
        assert !isColumnRange();

        CBuilder builder = cfm.comparator.prefixBuilder();

        Iterator<ColumnDefinition> columnIter = cfm.clusteringColumns().iterator();
        while (columnIter.hasNext())
        {
            ColumnDefinition def = columnIter.next();
            Restriction r = columnRestrictions[def.position()];
            assert r != null && !r.isSlice();

            if (r.isEQ())
            {
                List<ByteBuffer> values = r.values(options);
                if (r.isMultiColumn())
                {
                    for (int i = 0, m = values.size(); i < m; i++)
                    {
                        ByteBuffer val = values.get(i);

                        if (i != 0)
                            columnIter.next();

                        if (val == null)
                            throw new InvalidRequestException(String.format("Invalid null value for clustering key part %s", def.name));
                        builder.add(val);
                    }
                }
                else
                {
                    ByteBuffer val = r.values(options).get(0);
                    if (val == null)
                        throw new InvalidRequestException(String.format("Invalid null value for clustering key part %s", def.name));
                    builder.add(val);
                }
            }
            else
            {
                if (!r.isMultiColumn())
                {
                    List<ByteBuffer> values = r.values(options);
                    // We have a IN, which we only support for the last column.
                    // If compact, just add all values and we're done. Otherwise,
                    // for each value of the IN, creates all the columns corresponding to the selection.
                    if (values.isEmpty())
                        return null;
                    SortedSet<CellName> columns = new TreeSet<CellName>(cfm.comparator);
                    Iterator<ByteBuffer> iter = values.iterator();
                    while (iter.hasNext())
                    {
                        ByteBuffer val = iter.next();
                        if (val == null)
                            throw new InvalidRequestException(String.format("Invalid null value for clustering key part %s", def.name));

                        Composite prefix = builder.buildWith(val);
                        columns.addAll(addSelectedColumns(prefix));
                    }
                    return columns;
                }

                // we have a multi-column IN restriction
                List<List<ByteBuffer>> values = ((MultiColumnRestriction.IN) r).splitValues(options);
                TreeSet<CellName> inValues = new TreeSet<>(cfm.comparator);
                for (List<ByteBuffer> components : values)
                {
                    for (int i = 0; i < components.size(); i++)
                        if (components.get(i) == null)
                            throw new InvalidRequestException("Invalid null value in condition for column "
                                    + cfm.clusteringColumns().get(i + def.position()).name);

                    Composite prefix = builder.buildWith(components);
                    inValues.addAll(addSelectedColumns(prefix));
                }
                return inValues;
            }
        }

        return addSelectedColumns(builder.build());
    }

    private SortedSet<CellName> addSelectedColumns(Composite prefix)
    {
        if (cfm.comparator.isDense())
        {
            return FBUtilities.singleton(cfm.comparator.create(prefix, null), cfm.comparator);
        }
        else
        {
            // Collections require doing a slice query because a given collection is a
            // non-know set of columns, so we shouldn't get there
            assert !selectACollection();

            SortedSet<CellName> columns = new TreeSet<CellName>(cfm.comparator);

            // We need to query the selected column as well as the marker
            // column (for the case where the row exists but has no columns outside the PK)
            // Two exceptions are "static CF" (non-composite non-compact CF) and "super CF"
            // that don't have marker and for which we must query all columns instead
            if (cfm.comparator.isCompound() && !cfm.isSuper())
            {
                // marker
                columns.add(cfm.comparator.rowMarker(prefix));

                // selected columns
                for (ColumnDefinition def : selection.getColumns())
                    if (def.kind == ColumnDefinition.Kind.REGULAR || def.kind == ColumnDefinition.Kind.STATIC)
                        columns.add(cfm.comparator.create(prefix, def));
            }
            else
            {
                // We now that we're not composite so we can ignore static columns
                for (ColumnDefinition def : cfm.regularColumns())
                    columns.add(cfm.comparator.create(prefix, def));
            }
            return columns;
        }
    }

    /** Returns true if a non-frozen collection is selected, false otherwise. */
    private boolean selectACollection()
    {
        if (!cfm.comparator.hasCollections())
            return false;

        for (ColumnDefinition def : selection.getColumns())
        {
            if (def.type.isCollection() && def.type.isMultiCell())
                return true;
        }

        return false;
    }

    @VisibleForTesting
    static List<Composite> buildBound(Bound bound,
                                      List<ColumnDefinition> defs,
                                      Restriction[] restrictions,
                                      boolean isReversed,
                                      CType type,
                                      QueryOptions options) throws InvalidRequestException
    {
        CBuilder builder = type.builder();

        // The end-of-component of composite doesn't depend on whether the
        // component type is reversed or not (i.e. the ReversedType is applied
        // to the component comparator but not to the end-of-component itself),
        // it only depends on whether the slice is reversed
        Bound eocBound = isReversed ? Bound.reverse(bound) : bound;
        for (int i = 0, m = defs.size(); i < m; i++)
        {
            ColumnDefinition def = defs.get(i);

            // In a restriction, we always have Bound.START < Bound.END for the "base" comparator.
            // So if we're doing a reverse slice, we must inverse the bounds when giving them as start and end of the slice filter.
            // But if the actual comparator itself is reversed, we must inversed the bounds too.
            Bound b = isReversed == isReversedType(def) ? bound : Bound.reverse(bound);
            Restriction r = restrictions[def.position()];
            if (isNullRestriction(r, b) || !r.canEvaluateWithSlices())
            {
                // There wasn't any non EQ relation on that key, we select all records having the preceding component as prefix.
                // For composites, if there was preceding component and we're computing the end, we must change the last component
                // End-Of-Component, otherwise we would be selecting only one record.
                Composite prefix = builder.build();
                return Collections.singletonList(eocBound == Bound.END ? prefix.end() : prefix.start());
            }
            if (r.isSlice())
            {
                if (r.isMultiColumn())
                {
                    MultiColumnRestriction.Slice slice = (MultiColumnRestriction.Slice) r;

                    if (!slice.hasBound(b))
                    {
                        Composite prefix = builder.build();
                        return Collections.singletonList(builder.remainingCount() > 0 && eocBound == Bound.END
                                ? prefix.end()
                                : prefix);
                    }

                    List<ByteBuffer> vals = slice.componentBounds(b, options);

                    for (int j = 0, n = vals.size(); j < n; j++)
                        addValue(builder, defs.get(i + j), vals.get(j)) ;
                }
                else
                {
                    builder.add(getSliceValue(r, b, options));
                }
                Operator relType = ((Restriction.Slice)r).getRelation(eocBound, b);
                return Collections.singletonList(builder.build().withEOC(eocForRelation(relType)));
            }

            if (r.isIN())
            {
                // The IN query might not have listed the values in comparator order, so we need to re-sort
                // the bounds lists to make sure the slices works correctly (also, to avoid duplicates).
                TreeSet<Composite> inValues = new TreeSet<>(isReversed ? type.reverseComparator() : type);

                if (r.isMultiColumn())
                {
                    List<List<ByteBuffer>> splitInValues = ((MultiColumnRestriction.IN) r).splitValues(options);

                    for (List<ByteBuffer> components : splitInValues)
                    {
                        for (int j = 0; j < components.size(); j++)
                            if (components.get(j) == null)
                                throw new InvalidRequestException("Invalid null value in condition for column " + defs.get(i + j).name);

                        Composite prefix = builder.buildWith(components);
                        inValues.add(builder.remainingCount() == 0 ? prefix : addEOC(prefix, eocBound));
                    }
                    return new ArrayList<>(inValues);
                }

                List<ByteBuffer> values = r.values(options);
                if (values.size() != 1)
                {
                    // IN query, we only support it on the clustering columns
                    assert def.position() == defs.size() - 1;
                    for (ByteBuffer val : values)
                    {
                        if (val == null)
                            throw new InvalidRequestException(String.format("Invalid null value in condition for column %s",
                                                                            def.name));
                        Composite prefix = builder.buildWith(val);
                        // See below for why this
                        inValues.add(builder.remainingCount() == 0 ? prefix : addEOC(prefix, eocBound));
                    }
                    return new ArrayList<>(inValues);
                }
            }

            List<ByteBuffer> values = r.values(options);

            if (r.isMultiColumn())
            {
                for (int j = 0; j < values.size(); j++)
                    addValue(builder, defs.get(i + j), values.get(j));
                i += values.size() - 1; // skips the processed columns
            }
            else
            {
                addValue(builder, def, values.get(0));
            }
        }
        // Means no relation at all or everything was an equal
        // Note: if the builder is "full", there is no need to use the end-of-component bit. For columns selection,
        // it would be harmless to do it. However, we use this method got the partition key too. And when a query
        // with 2ndary index is done, and with the the partition provided with an EQ, we'll end up here, and in that
        // case using the eoc would be bad, since for the random partitioner we have no guarantee that
        // prefix.end() will sort after prefix (see #5240).
        Composite prefix = builder.build();
        return Collections.singletonList(builder.remainingCount() == 0 ? prefix : addEOC(prefix, eocBound));
    }

    /**
     * Adds an EOC to the specified Composite.
     *
     * @param composite the composite
     * @param eocBound the EOC bound
     * @return a new <code>Composite</code> with the EOC corresponding to the eocBound
     */
    private static Composite addEOC(Composite composite, Bound eocBound)
    {
        return eocBound == Bound.END ? composite.end() : composite.start();
    }

    /**
     * Adds the specified value to the specified builder
     *
     * @param builder the CBuilder to which the value must be added
     * @param def the column associated to the value
     * @param value the value to add
     * @throws InvalidRequestException if the value is null
     */
    private static void addValue(CBuilder builder, ColumnDefinition def, ByteBuffer value) throws InvalidRequestException
    {
        if (value == null)
            throw new InvalidRequestException(String.format("Invalid null value in condition for column %s", def.name));
        builder.add(value);
    }

    private static Composite.EOC eocForRelation(Operator op)
    {
        switch (op)
        {
            case LT:
                // < X => using startOf(X) as finish bound
                return Composite.EOC.START;
            case GT:
            case LTE:
                // > X => using endOf(X) as start bound
                // <= X => using endOf(X) as finish bound
                return Composite.EOC.END;
            default:
                // >= X => using X as start bound (could use START_OF too)
                // = X => using X
                return Composite.EOC.NONE;
        }
    }

    private static boolean isNullRestriction(Restriction r, Bound b)
    {
        return r == null || (r.isSlice() && !((Restriction.Slice)r).hasBound(b));
    }

    private static ByteBuffer getSliceValue(Restriction r, Bound b, QueryOptions options) throws InvalidRequestException
    {
        Restriction.Slice slice = (Restriction.Slice)r;
        assert slice.hasBound(b);
        ByteBuffer val = slice.bound(b, options);
        if (val == null)
            throw new InvalidRequestException(String.format("Invalid null clustering key part %s", r));
        return val;
    }

    private List<Composite> getRequestedBound(Bound b, QueryOptions options) throws InvalidRequestException
    {
        assert isColumnRange();
        return buildBound(b, cfm.clusteringColumns(), columnRestrictions, isReversed, cfm.comparator, options);
    }

    /**
     * May be used by custom QueryHandler implementations
     */
    public List<IndexExpression> getValidatedIndexExpressions(QueryOptions options) throws InvalidRequestException
    {
        if (!usesSecondaryIndexing || restrictedColumns.isEmpty())
            return Collections.emptyList();

        List<IndexExpression> expressions = new ArrayList<IndexExpression>();
        for (ColumnDefinition def : restrictedColumns.keySet())
        {
            Restriction restriction;
            switch (def.kind)
            {
                case PARTITION_KEY:
                    restriction = keyRestrictions[def.position()];
                    break;
                case CLUSTERING_COLUMN:
                    restriction = columnRestrictions[def.position()];
                    break;
                case REGULAR:
                case STATIC:
                    restriction = metadataRestrictions.get(def.name);
                    break;
                default:
                    // We don't allow restricting a COMPACT_VALUE for now in prepare.
                    throw new AssertionError();
            }

            if (restriction.isSlice())
            {
                Restriction.Slice slice = (Restriction.Slice)restriction;
                for (Bound b : Bound.values())
                {
                    if (slice.hasBound(b))
                    {
                        ByteBuffer value = validateIndexedValue(def, slice.bound(b, options));
                        Operator op = slice.getIndexOperator(b);
                        // If the underlying comparator for name is reversed, we need to reverse the IndexOperator: user operation
                        // always refer to the "forward" sorting even if the clustering order is reversed, but the 2ndary code does
                        // use the underlying comparator as is.
                        if (def.type instanceof ReversedType)
                            op = reverse(op);
                        expressions.add(new IndexExpression(def.name.bytes, op, value));
                    }
                }
            }
            else if (restriction.isContains())
            {
                SingleColumnRestriction.Contains contains = (SingleColumnRestriction.Contains)restriction;
                for (ByteBuffer value : contains.values(options))
                {
                    validateIndexedValue(def, value);
                    expressions.add(new IndexExpression(def.name.bytes, Operator.CONTAINS, value));
                }
                for (ByteBuffer key : contains.keys(options))
                {
                    validateIndexedValue(def, key);
                    expressions.add(new IndexExpression(def.name.bytes, Operator.CONTAINS_KEY, key));
                }
            }
            else
            {
                ByteBuffer value;
                if (restriction.isMultiColumn())
                {
                    List<ByteBuffer> values = restriction.values(options);
                    value = values.get(def.position());
                }
                else
                {
                    List<ByteBuffer> values = restriction.values(options);
                    if (values.size() != 1)
                        throw new InvalidRequestException("IN restrictions are not supported on indexed columns");

                    value = values.get(0);
                }

                validateIndexedValue(def, value);
                expressions.add(new IndexExpression(def.name.bytes, Operator.EQ, value));
            }
        }

        if (usesSecondaryIndexing)
        {
            ColumnFamilyStore cfs = Keyspace.open(keyspace()).getColumnFamilyStore(columnFamily());
            SecondaryIndexManager secondaryIndexManager = cfs.indexManager;
            secondaryIndexManager.validateIndexSearchersForQuery(expressions);
        }
        
        return expressions;
    }

    private static ByteBuffer validateIndexedValue(ColumnDefinition def, ByteBuffer value) throws InvalidRequestException
    {
        if (value == null)
            throw new InvalidRequestException(String.format("Unsupported null value for indexed column %s", def.name));
        if (value.remaining() > 0xFFFF)
            throw new InvalidRequestException("Index expression values may not be larger than 64K");
        return value;
    }

    private CellName makeExclusiveSliceBound(Bound bound, CellNameType type, QueryOptions options) throws InvalidRequestException
    {
        if (sliceRestriction.isInclusive(bound))
            return null;

        if (sliceRestriction.isMultiColumn())
            return type.makeCellName(((MultiColumnRestriction.Slice) sliceRestriction).componentBounds(bound, options).toArray());
        else
            return type.makeCellName(sliceRestriction.bound(bound, options));
    }

    private Iterator<Cell> applySliceRestriction(final Iterator<Cell> cells, final QueryOptions options) throws InvalidRequestException
    {
        assert sliceRestriction != null;

        final CellNameType type = cfm.comparator;
        final CellName excludedStart = makeExclusiveSliceBound(Bound.START, type, options);
        final CellName excludedEnd = makeExclusiveSliceBound(Bound.END, type, options);

        return new AbstractIterator<Cell>()
        {
            protected Cell computeNext()
            {
                while (cells.hasNext())
                {
                    Cell c = cells.next();

                    // For dynamic CF, the column could be out of the requested bounds (because we don't support strict bounds internally (unless
                    // the comparator is composite that is)), filter here
                    if ( (excludedStart != null && type.compare(c.name(), excludedStart) == 0)
                      || (excludedEnd != null && type.compare(c.name(), excludedEnd) == 0) )
                        continue;

                    return c;
                }
                return endOfData();
            }
        };
    }

    private static Operator reverse(Operator op)
    {
        switch (op)
        {
            case LT:  return Operator.GT;
            case LTE: return Operator.GTE;
            case GT:  return Operator.LT;
            case GTE: return Operator.LTE;
            default: return op;
        }
    }

    private ResultSet process(List<Row> rows, QueryOptions options, int limit, long now) throws InvalidRequestException
    {
        Selection.ResultSetBuilder result = selection.resultSetBuilder(now);
        for (org.apache.cassandra.db.Row row : rows)
        {
            // Not columns match the query, skip
            if (row.cf == null)
                continue;

            processColumnFamily(row.key.getKey(), row.cf, options, now, result);
        }

        ResultSet cqlRows = result.build();

        orderResults(cqlRows);

        // Internal calls always return columns in the comparator order, even when reverse was set
        if (isReversed)
            cqlRows.reverse();

        // Trim result if needed to respect the user limit
        cqlRows.trim(limit);
        return cqlRows;
    }

    // Used by ModificationStatement for CAS operations
    void processColumnFamily(ByteBuffer key, ColumnFamily cf, QueryOptions options, long now, Selection.ResultSetBuilder result)
    throws InvalidRequestException
    {
        CFMetaData cfm = cf.metadata();
        ByteBuffer[] keyComponents = null;
        if (cfm.getKeyValidator() instanceof CompositeType)
        {
            keyComponents = ((CompositeType)cfm.getKeyValidator()).split(key);
        }
        else
        {
            keyComponents = new ByteBuffer[]{ key };
        }

        Iterator<Cell> cells = cf.getSortedColumns().iterator();
        if (sliceRestriction != null)
            cells = applySliceRestriction(cells, options);

        CQL3Row.RowIterator iter = cfm.comparator.CQL3RowBuilder(cfm, now).group(cells);

        // If there is static columns but there is no non-static row, then provided the select was a full
        // partition selection (i.e. not a 2ndary index search and there was no condition on clustering columns)
        // then we want to include the static columns in the result set (and we're done).
        CQL3Row staticRow = iter.getStaticRow();
        if (staticRow != null && !iter.hasNext() && !usesSecondaryIndexing && hasNoClusteringColumnsRestriction())
        {
            result.newRow();
            for (ColumnDefinition def : selection.getColumns())
            {
                switch (def.kind)
                {
                    case PARTITION_KEY:
                        result.add(keyComponents[def.position()]);
                        break;
                    case STATIC:
                        addValue(result, def, staticRow, options);
                        break;
                    default:
                        result.add((ByteBuffer)null);
                }
            }
            return;
        }

        while (iter.hasNext())
        {
            CQL3Row cql3Row = iter.next();

            // Respect requested order
            result.newRow();
            // Respect selection order
            for (ColumnDefinition def : selection.getColumns())
            {
                switch (def.kind)
                {
                    case PARTITION_KEY:
                        result.add(keyComponents[def.position()]);
                        break;
                    case CLUSTERING_COLUMN:
                        result.add(cql3Row.getClusteringColumn(def.position()));
                        break;
                    case COMPACT_VALUE:
                        result.add(cql3Row.getColumn(null));
                        break;
                    case REGULAR:
                        addValue(result, def, cql3Row, options);
                        break;
                    case STATIC:
                        addValue(result, def, staticRow, options);
                        break;
                }
            }
        }
    }

    private static void addValue(Selection.ResultSetBuilder result, ColumnDefinition def, CQL3Row row, QueryOptions options)
    {
        if (row == null)
        {
            result.add((ByteBuffer)null);
            return;
        }

        if (def.type.isMultiCell())
        {
            List<Cell> cells = row.getMultiCellColumn(def.name);
            ByteBuffer buffer = cells == null
                             ? null
                             : ((CollectionType)def.type).serializeForNativeProtocol(def, cells, options.getProtocolVersion());
            result.add(buffer);
            return;
        }

        result.add(row.getColumn(def.name));
    }

    private boolean hasNoClusteringColumnsRestriction()
    {
        for (int i = 0; i < columnRestrictions.length; i++)
            if (columnRestrictions[i] != null)
                return false;
        return true;
    }

    private boolean needsPostQueryOrdering()
    {
        // We need post-query ordering only for queries with IN on the partition key and an ORDER BY.
        return keyIsInRelation && !parameters.orderings.isEmpty();
    }

    /**
     * Orders results when multiple keys are selected (using IN)
     */
    private void orderResults(ResultSet cqlRows) throws InvalidRequestException
    {
        if (cqlRows.size() == 0 || !needsPostQueryOrdering())
            return;

        assert orderingIndexes != null;

        List<Integer> idToSort = new ArrayList<Integer>();
        List<Comparator<ByteBuffer>> sorters = new ArrayList<Comparator<ByteBuffer>>();

        for (ColumnIdentifier.Raw identifier : parameters.orderings.keySet())
        {
            ColumnDefinition orderingColumn = cfm.getColumnDefinition(identifier.prepare(cfm));
            idToSort.add(orderingIndexes.get(orderingColumn.name));
            sorters.add(orderingColumn.type);
        }

        Comparator<List<ByteBuffer>> comparator = idToSort.size() == 1
                                                ? new SingleColumnComparator(idToSort.get(0), sorters.get(0))
                                                : new CompositeComparator(sorters, idToSort);
        Collections.sort(cqlRows.rows, comparator);
    }

    private static boolean isReversedType(ColumnDefinition def)
    {
        return def.type instanceof ReversedType;
    }

    private boolean columnFilterIsIdentity()
    {
        for (Restriction r : columnRestrictions)
        {
            if (r != null)
                return false;
        }
        return true;
    }

    /**
     * May be used by custom QueryHandler implementations
     */
    public boolean hasClusteringColumnsRestriction()
    {
        for (int i = 0; i < columnRestrictions.length; i++)
            if (columnRestrictions[i] != null)
                return true;
        return false;
    }

    /**
     * May be used by custom QueryHandler implementations
     */
    public boolean hasPartitionKeyRestriction()
    {
        for (int i = 0; i < keyRestrictions.length; i++)
            if (keyRestrictions[i] != null)
                return true;
        return false;
    }

    private void validateDistinctSelection()
    throws InvalidRequestException
    {
        Collection<ColumnDefinition> requestedColumns = selection.getColumns();
        for (ColumnDefinition def : requestedColumns)
            if (def.kind != ColumnDefinition.Kind.PARTITION_KEY && def.kind != ColumnDefinition.Kind.STATIC)
                throw new InvalidRequestException(String.format("SELECT DISTINCT queries must only request partition key columns and/or static columns (not %s)", def.name));

        // If it's a key range, we require that all partition key columns are selected so we don't have to bother with post-query grouping.
        if (!isKeyRange)
            return;

        for (ColumnDefinition def : cfm.partitionKeyColumns())
            if (!requestedColumns.contains(def))
                throw new InvalidRequestException(String.format("SELECT DISTINCT queries must request all the partition key columns (missing %s)", def.name));
    }

    /**
     * Checks if the specified column is restricted by multiple contains or contains key.
     *
     * @param columnDef the definition of the column to check
     * @return <code>true</code> the specified column is restricted by multiple contains or contains key,
     * <code>false</code> otherwise
     */
    private boolean isRestrictedByMultipleContains(ColumnDefinition columnDef)
    {
        if (!columnDef.type.isCollection())
            return false;

        Restriction restriction = metadataRestrictions.get(columnDef.name);

        if (!(restriction instanceof Contains))
            return false;

        Contains contains = (Contains) restriction;
        return (contains.numberOfValues() + contains.numberOfKeys()) > 1;
    }

    public static class RawStatement extends CFStatement
    {
        /**
         * Checks to ensure that the warning for missing allow filtering is only logged once.
         */
        private static volatile boolean hasLoggedMissingAllowFilteringWarning = false;

        private final Parameters parameters;
        private final List<RawSelector> selectClause;
        private final List<Relation> whereClause;
        private final Term.Raw limit;

        public RawStatement(CFName cfName, Parameters parameters, List<RawSelector> selectClause, List<Relation> whereClause, Term.Raw limit)
        {
            super(cfName);
            this.parameters = parameters;
            this.selectClause = selectClause;
            this.whereClause = whereClause == null ? Collections.<Relation>emptyList() : whereClause;
            this.limit = limit;
        }

        public ParsedStatement.Prepared prepare() throws InvalidRequestException
        {
            CFMetaData cfm = ThriftValidation.validateColumnFamily(keyspace(), columnFamily());
            VariableSpecifications boundNames = getBoundVariables();

            // Select clause
            if (parameters.isCount && !selectClause.isEmpty())
                throw new InvalidRequestException("Only COUNT(*) and COUNT(1) operations are currently supported.");

            Selection selection = selectClause.isEmpty()
                                ? Selection.wildcard(cfm)
                                : Selection.fromSelectors(cfm, selectClause);

            SelectStatement stmt = new SelectStatement(cfm, boundNames.size(), parameters, selection, prepareLimit(boundNames));

            /*
             * WHERE clause. For a given entity, rules are:
             *   - EQ relation conflicts with anything else (including a 2nd EQ)
             *   - Can't have more than one LT(E) relation (resp. GT(E) relation)
             *   - IN relation are restricted to row keys (for now) and conflicts with anything else
             *     (we could allow two IN for the same entity but that doesn't seem very useful)
             *   - The value_alias cannot be restricted in any way (we don't support wide rows with indexed value in CQL so far)
             */
            boolean hasQueriableIndex = false;
            boolean hasQueriableClusteringColumnIndex = false;

            ColumnFamilyStore cfs = Keyspace.open(keyspace()).getColumnFamilyStore(columnFamily());
            SecondaryIndexManager indexManager = cfs.indexManager;

            for (Relation relation : whereClause)
            {
                if (relation.isMultiColumn())
                {
                    MultiColumnRelation rel = (MultiColumnRelation) relation;
                    List<ColumnDefinition> names = new ArrayList<>(rel.getEntities().size());
                    for (ColumnIdentifier.Raw rawEntity : rel.getEntities())
                    {
                        ColumnIdentifier entity = rawEntity.prepare(cfm);
                        ColumnDefinition def = cfm.getColumnDefinition(entity);
                        boolean[] queriable = processRelationEntity(stmt, indexManager, relation, entity, def);
                        hasQueriableIndex |= queriable[0];
                        hasQueriableClusteringColumnIndex |= queriable[1];
                        names.add(def);
                    }
                    updateRestrictionsForRelation(stmt, names, rel, boundNames);
                }
                else
                {
                    SingleColumnRelation rel = (SingleColumnRelation) relation;
                    ColumnIdentifier entity = rel.getEntity().prepare(cfm);
                    ColumnDefinition def = cfm.getColumnDefinition(entity);
                    boolean[] queriable = processRelationEntity(stmt, indexManager, relation, entity, def);
                    hasQueriableIndex |= queriable[0];
                    hasQueriableClusteringColumnIndex |= queriable[1];
                    updateRestrictionsForRelation(stmt, def, rel, boundNames);
                }
            }

             // At this point, the select statement if fully constructed, but we still have a few things to validate
            processPartitionKeyRestrictions(stmt, hasQueriableIndex, cfm);

            // All (or none) of the partition key columns have been specified;
            // hence there is no need to turn these restrictions into index expressions.
            if (!stmt.usesSecondaryIndexing)
                stmt.restrictedColumns.keySet().removeAll(cfm.partitionKeyColumns());

            if (stmt.selectsOnlyStaticColumns && stmt.hasClusteringColumnsRestriction())
                throw new InvalidRequestException("Cannot restrict clustering columns when selecting only static columns");

            processColumnRestrictions(stmt, hasQueriableIndex, cfm);

            // Covers indexes on the first clustering column (among others).
            if (stmt.isKeyRange && hasQueriableClusteringColumnIndex)
                stmt.usesSecondaryIndexing = true;

            int numberOfRestrictionsEvaluatedWithSlices = 0;

            for (ColumnDefinition def : cfm.clusteringColumns())
            {
                // Remove clustering column restrictions that can be handled by slices; the remainder will be
                // handled by filters (which may require a secondary index).
                Boolean indexed = stmt.restrictedColumns.get(def);
                if (indexed == null)
                    break;
                if (!indexed && stmt.columnRestrictions[def.position()].canEvaluateWithSlices())
                {
                    stmt.restrictedColumns.remove(def);
                    numberOfRestrictionsEvaluatedWithSlices++;
                }
            }

            // Even if usesSecondaryIndexing is false at this point, we'll still have to use one if
            // there are restrictions not covered by the PK.
            if (!stmt.metadataRestrictions.isEmpty())
                stmt.usesSecondaryIndexing = true;

            if (stmt.usesSecondaryIndexing)
                validateSecondaryIndexSelections(stmt);

            if (!stmt.parameters.orderings.isEmpty())
                processOrderingClause(stmt, cfm);

            checkNeedsFiltering(stmt, numberOfRestrictionsEvaluatedWithSlices);

            if (parameters.isDistinct)
                stmt.validateDistinctSelection();

            return new ParsedStatement.Prepared(stmt, boundNames);
        }

        /** Returns a pair of (hasQueriableIndex, hasQueriableClusteringColumnIndex) */
        private boolean[] processRelationEntity(SelectStatement stmt,
                                                SecondaryIndexManager indexManager,
                                                Relation relation,
                                                ColumnIdentifier entity,
                                                ColumnDefinition def) throws InvalidRequestException
        {
            if (def == null)
                handleUnrecognizedEntity(entity, relation);

            SecondaryIndex index = indexManager.getIndexForColumn(def.name.bytes);
            if (index != null && index.supportsOperator(relation.operator()))
            {
                stmt.restrictedColumns.put(def, Boolean.TRUE);
                return new boolean[]{true, def.kind == ColumnDefinition.Kind.CLUSTERING_COLUMN};
            }

            stmt.restrictedColumns.put(def, Boolean.FALSE);
            return new boolean[]{false, false};
        }

        /** Throws an InvalidRequestException for an unrecognized identifier in the WHERE clause */
        private void handleUnrecognizedEntity(ColumnIdentifier entity, Relation relation) throws InvalidRequestException
        {
            if (containsAlias(entity))
                throw new InvalidRequestException(String.format("Aliases aren't allowed in the where clause ('%s')", relation));
            else
                throw new InvalidRequestException(String.format("Undefined name %s in where clause ('%s')", entity, relation));
        }

        /** Returns a Term for the limit or null if no limit is set */
        private Term prepareLimit(VariableSpecifications boundNames) throws InvalidRequestException
        {
            if (limit == null)
                return null;

            Term prepLimit = limit.prepare(keyspace(), limitReceiver());
            prepLimit.collectMarkerSpecification(boundNames);
            return prepLimit;
        }

        private void updateRestrictionsForRelation(SelectStatement stmt, List<ColumnDefinition> defs, MultiColumnRelation relation, VariableSpecifications boundNames) throws InvalidRequestException
        {
            List<ColumnDefinition> restrictedColumns = new ArrayList<>();
            Set<ColumnDefinition> seen = new HashSet<>();
            Restriction existing = null;

            int previousPosition = defs.get(0).position() - 1;
            for (int i = 0, m = defs.size(); i < m; i++)
            {
                ColumnDefinition def = defs.get(i);

                // ensure multi-column restriction only applies to clustering columns
                if (def.kind != ColumnDefinition.Kind.CLUSTERING_COLUMN)
                    throw new InvalidRequestException(String.format("Multi-column relations can only be applied to clustering columns: %s", def.name));

                if (seen.contains(def))
                    throw new InvalidRequestException(String.format("Column \"%s\" appeared twice in a relation: %s", def.name, relation));
                seen.add(def);

                // check that no clustering columns were skipped
                if (def.position() != previousPosition + 1)
                {
                    if (previousPosition == -1)
                        throw new InvalidRequestException(String.format(
                                "Clustering columns may not be skipped in multi-column relations. " +
                                "They should appear in the PRIMARY KEY order. Got %s", relation));

                    throw new InvalidRequestException(String.format(
                                "Clustering columns must appear in the PRIMARY KEY order in multi-column relations: %s",
                                 relation));
                }
                previousPosition++;

                Restriction previous = existing;
                existing = getExistingRestriction(stmt, def);
                Operator operator = relation.operator();
                if (existing != null)
                {
                    if (operator == Operator.EQ || operator == Operator.IN)
                    {
                        throw new InvalidRequestException(String.format(
                                "Column \"%s\" cannot be restricted by more than one relation if it is in an %s relation",
                                def.name, operator));
                    }
                    else if (!existing.isSlice())
                    {
                        throw new InvalidRequestException(String.format(
                                "Column \"%s\" cannot be restricted by an equality relation and an inequality relation",
                                def.name));
                    }
                    else
                    {
                        if (!existing.isMultiColumn())
                        {
                            throw new InvalidRequestException(String.format(
                                    "Column \"%s\" cannot have both tuple-notation inequalities and single-column inequalities: %s",
                                    def.name, relation));
                        }

                        boolean existingRestrictionStartBefore =
                            (i == 0 && def.position() != 0 && stmt.columnRestrictions[def.position() - 1] == existing);

                        boolean existingRestrictionStartAfter = (i != 0 && previous != existing);

                        if (existingRestrictionStartBefore || existingRestrictionStartAfter)
                        {
                            throw new InvalidRequestException(String.format(
                                    "Column \"%s\" cannot be restricted by two tuple-notation inequalities not starting with the same column: %s",
                                    def.name, relation));
                        }

                        checkBound(existing, def, operator);
                    }
                }
                restrictedColumns.add(def);
            }

            switch (relation.operator())
            {
                case EQ:
                {
                    Term t = relation.getValue().prepare(keyspace(), defs);
                    t.collectMarkerSpecification(boundNames);
                    Restriction restriction = new MultiColumnRestriction.EQ(t, false);
                    for (ColumnDefinition def : restrictedColumns)
                        stmt.columnRestrictions[def.position()] = restriction;
                    break;
                }
                case IN:
                {
                    Restriction restriction;
                    List<? extends Term.MultiColumnRaw> inValues = relation.getInValues();
                    if (inValues != null)
                    {
                        // we have something like "(a, b, c) IN ((1, 2, 3), (4, 5, 6), ...) or
                        // "(a, b, c) IN (?, ?, ?)
                        List<Term> terms = new ArrayList<>(inValues.size());
                        for (Term.MultiColumnRaw tuple : inValues)
                        {
                            Term t = tuple.prepare(keyspace(), defs);
                            t.collectMarkerSpecification(boundNames);
                            terms.add(t);
                        }
                         restriction = new MultiColumnRestriction.InWithValues(terms);
                    }
                    else
                    {
                        Tuples.INRaw rawMarker = relation.getInMarker();
                        AbstractMarker t = rawMarker.prepare(keyspace(), defs);
                        t.collectMarkerSpecification(boundNames);
                        restriction = new MultiColumnRestriction.InWithMarker(t);
                    }
                    for (ColumnDefinition def : restrictedColumns)
                        stmt.columnRestrictions[def.position()] = restriction;

                    break;
                }
                case LT:
                case LTE:
                case GT:
                case GTE:
                {
                    Term t = relation.getValue().prepare(keyspace(), defs);
                    t.collectMarkerSpecification(boundNames);
                    Restriction.Slice restriction = (Restriction.Slice)getExistingRestriction(stmt, defs.get(0));
                    if (restriction == null)
                        restriction = new MultiColumnRestriction.Slice(false);
                    restriction.setBound(relation.operator(), t);

                    for (ColumnDefinition def : defs)
                    {
                        stmt.columnRestrictions[def.position()] = restriction;
                    }
                    break;
                }
                case NEQ:
                    throw new InvalidRequestException(String.format("Unsupported \"!=\" relation: %s", relation));
            }
        }

        /**
         * Checks that the operator for the specified column is compatible with the bounds of the existing restriction.
         *
         * @param existing the existing restriction
         * @param def the column definition
         * @param operator the operator
         * @throws InvalidRequestException if the operator is not compatible with the bounds of the existing restriction
         */
        private static void checkBound(Restriction existing, ColumnDefinition def, Operator operator) throws InvalidRequestException
        {
            Restriction.Slice existingSlice = (Restriction.Slice) existing;

            if (existingSlice.hasBound(Bound.START) && (operator == Operator.GT || operator == Operator.GTE))
                throw new InvalidRequestException(String.format(
                            "More than one restriction was found for the start bound on %s", def.name));

            if (existingSlice.hasBound(Bound.END) && (operator == Operator.LT || operator == Operator.LTE))
                throw new InvalidRequestException(String.format(
                            "More than one restriction was found for the end bound on %s", def.name));
        }

        private static Restriction getExistingRestriction(SelectStatement stmt, ColumnDefinition def)
        {
            switch (def.kind)
            {
                case PARTITION_KEY:
                    return stmt.keyRestrictions[def.position()];
                case CLUSTERING_COLUMN:
                    return stmt.columnRestrictions[def.position()];
                case REGULAR:
                case STATIC:
                    return stmt.metadataRestrictions.get(def.name);
                default:
                    throw new AssertionError();
            }
        }

        private void updateRestrictionsForRelation(SelectStatement stmt, ColumnDefinition def, SingleColumnRelation relation, VariableSpecifications names) throws InvalidRequestException
        {
            switch (def.kind)
            {
                case PARTITION_KEY:
                    stmt.keyRestrictions[def.position()] = updateSingleColumnRestriction(def, stmt.keyRestrictions[def.position()], relation, names);
                    break;
                case CLUSTERING_COLUMN:
                    stmt.columnRestrictions[def.position()] = updateSingleColumnRestriction(def, stmt.columnRestrictions[def.position()], relation, names);
                    break;
                case COMPACT_VALUE:
                    throw new InvalidRequestException(String.format("Predicates on the non-primary-key column (%s) of a COMPACT table are not yet supported", def.name));
                case REGULAR:
                case STATIC:
                    // We only all IN on the row key and last clustering key so far, never on non-PK columns, and this even if there's an index
                    Restriction r = updateSingleColumnRestriction(def, stmt.metadataRestrictions.get(def.name), relation, names);
                    if (r.isIN() && !((Restriction.IN)r).canHaveOnlyOneValue())
                        // Note: for backward compatibility reason, we conside a IN of 1 value the same as a EQ, so we let that slide.
                        throw new InvalidRequestException(String.format("IN predicates on non-primary-key columns (%s) is not yet supported", def.name));
                    stmt.metadataRestrictions.put(def.name, r);
                    break;
            }
        }

        Restriction updateSingleColumnRestriction(ColumnDefinition def, Restriction existingRestriction, SingleColumnRelation newRel, VariableSpecifications boundNames) throws InvalidRequestException
        {
            ColumnSpecification receiver = def;
            if (newRel.onToken)
            {
                if (def.kind != ColumnDefinition.Kind.PARTITION_KEY)
                    throw new InvalidRequestException(String.format("The token() function is only supported on the partition key, found on %s", def.name));

                receiver = new ColumnSpecification(def.ksName,
                                                   def.cfName,
                                                   new ColumnIdentifier("partition key token", true),
                                                   StorageService.getPartitioner().getTokenValidator());
            }

            // We don't support relations against entire collections (unless they're frozen), like "numbers = {1, 2, 3}"
            if (receiver.type.isCollection() && receiver.type.isMultiCell() && !(newRel.operator() == Operator.CONTAINS_KEY || newRel.operator() == Operator.CONTAINS))
            {
                throw new InvalidRequestException(String.format("Collection column '%s' (%s) cannot be restricted by a '%s' relation",
                                                                def.name, receiver.type.asCQL3Type(), newRel.operator()));
            }

            switch (newRel.operator())
            {
                case EQ:
                {
                    if (existingRestriction != null)
                        throw new InvalidRequestException(String.format("%s cannot be restricted by more than one relation if it includes an Equal", def.name));
                    Term t = newRel.getValue().prepare(keyspace(), receiver);
                    t.collectMarkerSpecification(boundNames);
                    existingRestriction = new SingleColumnRestriction.EQ(t, newRel.onToken);
                }
                break;
                case IN:
                    if (existingRestriction != null)
                        throw new InvalidRequestException(String.format("%s cannot be restricted by more than one relation if it includes a IN", def.name));

                    if (newRel.getInValues() == null)
                    {
                        // Means we have a "SELECT ... IN ?"
                        assert newRel.getValue() != null;
                        Term t = newRel.getValue().prepare(keyspace(), receiver);
                        t.collectMarkerSpecification(boundNames);
                        existingRestriction = new SingleColumnRestriction.InWithMarker((Lists.Marker)t);
                    }
                    else
                    {
                        List<Term> inValues = new ArrayList<>(newRel.getInValues().size());
                        for (Term.Raw raw : newRel.getInValues())
                        {
                            Term t = raw.prepare(keyspace(), receiver);
                            t.collectMarkerSpecification(boundNames);
                            inValues.add(t);
                        }
                        existingRestriction = new SingleColumnRestriction.InWithValues(inValues);
                    }
                    break;
                case NEQ:
                    throw new InvalidRequestException(String.format("Unsupported \"!=\" relation on column \"%s\"", def.name));
                case GT:
                case GTE:
                case LT:
                case LTE:
                    {
                        if (existingRestriction == null)
                            existingRestriction = new SingleColumnRestriction.Slice(newRel.onToken);
                        else if (!existingRestriction.isSlice())
                            throw new InvalidRequestException(String.format("Column \"%s\" cannot be restricted by both an equality and an inequality relation", def.name));
                        else if (existingRestriction.isMultiColumn())
                            throw new InvalidRequestException(String.format("Column \"%s\" cannot be restricted by both a tuple notation inequality and a single column inequality (%s)", def.name, newRel));
                        else if (existingRestriction.isOnToken() != newRel.onToken)
                            // For partition keys, we shouldn't have slice restrictions without token(). And while this is rejected later by
                            // processPartitionKeysRestrictions, we shouldn't update the existing restriction by the new one if the old one was using token()
                            // and the new one isn't since that would bypass that later test.
                            throw new InvalidRequestException("Only EQ and IN relation are supported on the partition key (unless you use the token() function)");

                        checkBound(existingRestriction, def, newRel.operator());

                        Term t = newRel.getValue().prepare(keyspace(), receiver);
                        t.collectMarkerSpecification(boundNames);
                        ((SingleColumnRestriction.Slice)existingRestriction).setBound(newRel.operator(), t);
                    }
                    break;
                case CONTAINS_KEY:
                    if (!(receiver.type instanceof MapType))
                        throw new InvalidRequestException(String.format("Cannot use CONTAINS KEY on non-map column %s", def.name));
                    // Fallthrough on purpose
                case CONTAINS:
                {
                    if (!receiver.type.isCollection())
                        throw new InvalidRequestException(String.format("Cannot use %s relation on non collection column %s", newRel.operator(), def.name));

                    if (existingRestriction == null)
                        existingRestriction = new SingleColumnRestriction.Contains();
                    else if (!existingRestriction.isContains())
                        throw new InvalidRequestException(String.format("Collection column %s can only be restricted by CONTAINS or CONTAINS KEY", def.name));

                    boolean isKey = newRel.operator() == Operator.CONTAINS_KEY;
                    receiver = makeCollectionReceiver(receiver, isKey);
                    Term t = newRel.getValue().prepare(keyspace(), receiver);
                    t.collectMarkerSpecification(boundNames);
                    ((SingleColumnRestriction.Contains)existingRestriction).add(t, isKey);
                    break;
                }
            }
            return existingRestriction;
        }

        private void processPartitionKeyRestrictions(SelectStatement stmt, boolean hasQueriableIndex, CFMetaData cfm) throws InvalidRequestException
        {
            // If there is a queriable index, no special condition are required on the other restrictions.
            // But we still need to know 2 things:
            //   - If we don't have a queriable index, is the query ok
            //   - Is it queriable without 2ndary index, which is always more efficient
            // If a component of the partition key is restricted by a relation, all preceding
            // components must have a EQ. Only the last partition key component can be in IN relation.
            boolean canRestrictFurtherComponents = true;
            ColumnDefinition previous = null;
            stmt.keyIsInRelation = false;
            Iterator<ColumnDefinition> iter = cfm.partitionKeyColumns().iterator();
            for (int i = 0; i < stmt.keyRestrictions.length; i++)
            {
                ColumnDefinition cdef = iter.next();
                Restriction restriction = stmt.keyRestrictions[i];

                if (restriction == null)
                {
                    if (stmt.onToken)
                        throw new InvalidRequestException("The token() function must be applied to all partition key components or none of them");

                    // The only time not restricting a key part is allowed is if none are restricted or an index is used.
                    if (i > 0 && stmt.keyRestrictions[i - 1] != null)
                    {
                        if (hasQueriableIndex)
                        {
                            stmt.usesSecondaryIndexing = true;
                            stmt.isKeyRange = true;
                            break;
                        }
                        throw new InvalidRequestException(String.format("Partition key part %s must be restricted since preceding part is", cdef.name));
                    }

                    stmt.isKeyRange = true;
                    canRestrictFurtherComponents = false;
                }
                else if (!canRestrictFurtherComponents)
                {
                    if (hasQueriableIndex)
                    {
                        stmt.usesSecondaryIndexing = true;
                        break;
                    }
                    throw new InvalidRequestException(String.format(
                            "Partitioning column \"%s\" cannot be restricted because the preceding column (\"%s\") is " +
                            "either not restricted or is restricted by a non-EQ relation", cdef.name, previous));
                }
                else if (restriction.isOnToken())
                {
                    // If this is a query on tokens, it's necessarily a range query (there can be more than one key per token).
                    stmt.isKeyRange = true;
                    stmt.onToken = true;
                }
                else if (stmt.onToken)
                {
                    throw new InvalidRequestException(String.format("The token() function must be applied to all partition key components or none of them"));
                }
                else if (!restriction.isSlice())
                {
                    if (restriction.isIN())
                    {
                        // We only support IN for the last name so far
                        if (i != stmt.keyRestrictions.length - 1)
                            throw new InvalidRequestException(String.format("Partition KEY part %s cannot be restricted by IN relation (only the last part of the partition key can)", cdef.name));
                        stmt.keyIsInRelation = true;
                    }
                }
                else
                {
                    // Non EQ relation is not supported without token(), even if we have a 2ndary index (since even those are ordered by partitioner).
                    // Note: In theory we could allow it for 2ndary index queries with ALLOW FILTERING, but that would probably require some special casing
                    // Note bis: This is also why we don't bother handling the 'tuple' notation of #4851 for keys. If we lift the limitation for 2ndary
                    // index with filtering, we'll need to handle it though.
                    throw new InvalidRequestException("Only EQ and IN relation are supported on the partition key (unless you use the token() function)");
                }
                previous = cdef;
            }

            if (stmt.onToken)
                checkTokenFunctionArgumentsOrder(cfm);
        }

        /**
         * Checks that the column identifiers used as argument for the token function have been specified in the
         * partition key order.
         * @param cfm the Column Family MetaData
         * @throws InvalidRequestException if the arguments have not been provided in the proper order.
         */
        private void checkTokenFunctionArgumentsOrder(CFMetaData cfm) throws InvalidRequestException
        {
            Iterator<ColumnDefinition> iter = Iterators.cycle(cfm.partitionKeyColumns());
            for (Relation relation : whereClause)
            {
                if (!relation.isOnToken())
                    continue;

                assert !relation.isMultiColumn() : "Unexpectedly got multi-column token relation";
                SingleColumnRelation singleColumnRelation = (SingleColumnRelation) relation;
                if (!cfm.getColumnDefinition(singleColumnRelation.getEntity().prepare(cfm)).equals(iter.next()))
                    throw new InvalidRequestException(String.format("The token function arguments must be in the partition key order: %s",
                                                                    Joiner.on(',').join(cfm.partitionKeyColumns())));
            }
        }

        private void processColumnRestrictions(SelectStatement stmt, boolean hasQueriableIndex, CFMetaData cfm) throws InvalidRequestException
        {
            // If a clustering key column is restricted by a non-EQ relation, all preceding
            // columns must have a EQ, and all following must have no restriction. Unless
            // the column is indexed that is.
            boolean canRestrictFurtherComponents = true;
            ColumnDefinition previous = null;
            Restriction previousRestriction = null;
            Iterator<ColumnDefinition> iter = cfm.clusteringColumns().iterator();
            for (int i = 0; i < stmt.columnRestrictions.length; i++)
            {
                ColumnDefinition cdef = iter.next();
                Restriction restriction = stmt.columnRestrictions[i];

                if (restriction == null)
                {
                    canRestrictFurtherComponents = false;
                }
                else if (!canRestrictFurtherComponents)
                {
                    // We're here if the previous clustering column was either not restricted, was a slice or an IN tulpe-notation.

                    // we can continue if we are in the special case of a slice 'tuple' notation from #4851
                    if (restriction != previousRestriction)
                    {
                        // if we have a 2ndary index, we need to use it
                        if (hasQueriableIndex)
                        {
                            stmt.usesSecondaryIndexing = true;
                            break;
                        }

                        if (previousRestriction == null)
                            throw new InvalidRequestException(String.format(
                                "PRIMARY KEY column \"%s\" cannot be restricted (preceding column \"%s\" is not restricted)", cdef.name, previous.name));

                        if (previousRestriction.isMultiColumn() && previousRestriction.isIN())
                            throw new InvalidRequestException(String.format(
                                     "PRIMARY KEY column \"%s\" cannot be restricted (preceding column \"%s\" is restricted by an IN tuple notation)", cdef.name, previous.name));

                        throw new InvalidRequestException(String.format(
                                "PRIMARY KEY column \"%s\" cannot be restricted (preceding column \"%s\" is restricted by a non-EQ relation)", cdef.name, previous.name));
                    }
                }
                else if (restriction.isSlice())
                {
                    canRestrictFurtherComponents = false;
                    Restriction.Slice slice = (Restriction.Slice)restriction;
                    // For non-composite slices, we don't support internally the difference between exclusive and
                    // inclusive bounds, so we deal with it manually.
                    if (!cfm.comparator.isCompound() && (!slice.isInclusive(Bound.START) || !slice.isInclusive(Bound.END)))
                        stmt.sliceRestriction = slice;
                }
                else if (restriction.isIN())
                {
                    if (!restriction.isMultiColumn() && i != stmt.columnRestrictions.length - 1)
                        throw new InvalidRequestException(String.format("Clustering column \"%s\" cannot be restricted by an IN relation", cdef.name));

                    if (stmt.selectACollection())
                        throw new InvalidRequestException(String.format("Cannot restrict column \"%s\" by IN relation as a collection is selected by the query", cdef.name));

                    if (restriction.isMultiColumn())
                        canRestrictFurtherComponents = false;
                }
                else if (restriction.isContains())
                {
                    if (!hasQueriableIndex)
                        throw new InvalidRequestException(String.format("Cannot restrict column \"%s\" by a CONTAINS relation without a secondary index", cdef.name));
                    stmt.usesSecondaryIndexing = true;
                }

                previous = cdef;
                previousRestriction = restriction;
            }
        }

        private void validateSecondaryIndexSelections(SelectStatement stmt) throws InvalidRequestException
        {
            if (stmt.keyIsInRelation)
                throw new InvalidRequestException("Select on indexed columns and with IN clause for the PRIMARY KEY are not supported");
            // When the user only select static columns, the intent is that we don't query the whole partition but just
            // the static parts. But 1) we don't have an easy way to do that with 2i and 2) since we don't support index on static columns
            // so far, 2i means that you've restricted a non static column, so the query is somewhat non-sensical.
            if (stmt.selectsOnlyStaticColumns)
                throw new InvalidRequestException("Queries using 2ndary indexes don't support selecting only static columns");            
        }

        private void verifyOrderingIsAllowed(SelectStatement stmt) throws InvalidRequestException
        {
            if (stmt.usesSecondaryIndexing)
                throw new InvalidRequestException("ORDER BY with 2ndary indexes is not supported.");

            if (stmt.isKeyRange)
                throw new InvalidRequestException("ORDER BY is only supported when the partition key is restricted by an EQ or an IN.");
        }

        private void handleUnrecognizedOrderingColumn(ColumnIdentifier column) throws InvalidRequestException
        {
            if (containsAlias(column))
                throw new InvalidRequestException(String.format("Aliases are not allowed in order by clause ('%s')", column));
            else
                throw new InvalidRequestException(String.format("Order by on unknown column %s", column));
        }

        private void processOrderingClause(SelectStatement stmt, CFMetaData cfm) throws InvalidRequestException
        {
            verifyOrderingIsAllowed(stmt);

            // If we order post-query (see orderResults), the sorted column needs to be in the ResultSet for sorting, even if we don't
            // ultimately ship them to the client (CASSANDRA-4911).
            if (stmt.keyIsInRelation)
            {
                stmt.orderingIndexes = new HashMap<>();
                for (ColumnIdentifier.Raw rawColumn : stmt.parameters.orderings.keySet())
                {
                    ColumnIdentifier column = rawColumn.prepare(cfm);
                    final ColumnDefinition def = cfm.getColumnDefinition(column);
                    if (def == null)
                        handleUnrecognizedOrderingColumn(column);

                    int index = indexOf(def, stmt.selection);
                    if (index < 0)
                        index = stmt.selection.addColumnForOrdering(def);
                    stmt.orderingIndexes.put(def.name, index);
                }
            }
            stmt.isReversed = isReversed(stmt, cfm);
        }

        private boolean isReversed(SelectStatement stmt, CFMetaData cfm) throws InvalidRequestException
        {
            Boolean[] reversedMap = new Boolean[cfm.clusteringColumns().size()];
            int i = 0;
            for (Map.Entry<ColumnIdentifier.Raw, Boolean> entry : stmt.parameters.orderings.entrySet())
            {
                ColumnIdentifier column = entry.getKey().prepare(cfm);
                boolean reversed = entry.getValue();

                ColumnDefinition def = cfm.getColumnDefinition(column);
                if (def == null)
                    handleUnrecognizedOrderingColumn(column);

                if (def.kind != ColumnDefinition.Kind.CLUSTERING_COLUMN)
                    throw new InvalidRequestException(String.format("Order by is currently only supported on the clustered columns of the PRIMARY KEY, got %s", column));

                if (i++ != def.position())
                    throw new InvalidRequestException(String.format("Order by currently only support the ordering of columns following their declared order in the PRIMARY KEY"));

                reversedMap[def.position()] = (reversed != isReversedType(def));
            }

            // Check that all boolean in reversedMap, if set, agrees
            Boolean isReversed = null;
            for (Boolean b : reversedMap)
            {
                // Column on which order is specified can be in any order
                if (b == null)
                    continue;

                if (isReversed == null)
                {
                    isReversed = b;
                    continue;
                }
                if (!isReversed.equals(b))
                    throw new InvalidRequestException(String.format("Unsupported order by relation"));
            }
            assert isReversed != null;
            return isReversed;
        }

        /** If ALLOW FILTERING was not specified, this verifies that it is not needed */
        private void checkNeedsFiltering(SelectStatement stmt, int numberOfRestrictionsEvaluatedWithSlices) throws InvalidRequestException
        {
            // non-key-range non-indexed queries cannot involve filtering underneath
            if (!parameters.allowFiltering && (stmt.isKeyRange || stmt.usesSecondaryIndexing))
            {
                // We will potentially filter data if either:
                //  - Have more than one IndexExpression
                //  - Have no index expression and the column filter is not the identity
                if (needFiltering(stmt, numberOfRestrictionsEvaluatedWithSlices))
                    throw new InvalidRequestException("Cannot execute this query as it might involve data filtering and " +
                                                      "thus may have unpredictable performance. If you want to execute " +
                                                      "this query despite the performance unpredictability, use ALLOW FILTERING");
            }

            // We don't internally support exclusive slice bounds on non-composite tables. To deal with it we do an
            // inclusive slice and remove post-query the value that shouldn't be returned. One problem however is that
            // if there is a user limit, that limit may make the query return before the end of the slice is reached,
            // in which case, once we'll have removed bound post-query, we might end up with less results than
            // requested which would be incorrect. For single-partition query, this is not a problem, we just ask for
            // one more result (see updateLimitForQuery()) since that's enough to compensate for that problem. For key
            // range however, each returned row may include one result that will have to be trimmed, so we would have
            // to bump the query limit by N where N is the number of rows we will return, but we don't know that in
            // advance. So, since we currently don't have a good way to handle such query, we refuse it (#7059) rather
            // than answering with something that is wrong.
            if (stmt.sliceRestriction != null && stmt.isKeyRange && limit != null)
            {
                SingleColumnRelation rel = findInclusiveClusteringRelationForCompact(stmt.cfm);
                throw new InvalidRequestException(String.format("The query requests a restriction of rows with a strict bound (%s) over a range of partitions. "
                                                              + "This is not supported by the underlying storage engine for COMPACT tables if a LIMIT is provided. "
                                                              + "Please either make the condition non strict (%s) or remove the user LIMIT", rel, rel.withNonStrictOperator()));
            }
        }

        /**
         * Checks if the specified statement will need to filter the data.
         *
         * @param stmt the statement to test.
         * @param numberOfRestrictionsEvaluatedWithSlices the number of restrictions that can be evaluated with slices
         * @return <code>true</code> if the specified statement will need to filter the data, <code>false</code>
         * otherwise.
         */
        private static boolean needFiltering(SelectStatement stmt, int numberOfRestrictionsEvaluatedWithSlices)
        {
            boolean needFiltering = stmt.restrictedColumns.size() > 1
                    || (stmt.restrictedColumns.isEmpty() && !stmt.columnFilterIsIdentity())
                    || (!stmt.restrictedColumns.isEmpty()
                            && stmt.isRestrictedByMultipleContains(Iterables.getOnlyElement(stmt.restrictedColumns.keySet())));

            // For some secondary index queries, that were having some restrictions on non-indexed clustering columns,
            // were not requiring ALLOW FILTERING as we should. The first time such a query is executed we will log a
            // warning to notify the user (CASSANDRA-8418)
            if (!needFiltering
                    && !hasLoggedMissingAllowFilteringWarning
                    && (stmt.restrictedColumns.size() + numberOfRestrictionsEvaluatedWithSlices) > 1)
            {
                hasLoggedMissingAllowFilteringWarning = true;

                String msg = "Some secondary index queries with restrictions on non-indexed clustering columns "
                           + "were executed without ALLOW FILTERING. In Cassandra 3.0, these queries will require "
                           + "ALLOW FILTERING (see CASSANDRA-8418 for details).";

                logger.warn(msg);
            }

            return needFiltering;
        }

        private int indexOf(ColumnDefinition def, Selection selection)
        {
            return indexOf(def, selection.getColumns().iterator());
        }

        private int indexOf(final ColumnDefinition def, Iterator<ColumnDefinition> defs)
        {
            return Iterators.indexOf(defs, new Predicate<ColumnDefinition>()
                                           {
                                               public boolean apply(ColumnDefinition n)
                                               {
                                                   return def.name.equals(n.name);
                                               }
                                           });
        }

        private SingleColumnRelation findInclusiveClusteringRelationForCompact(CFMetaData cfm)
        {
            for (Relation r : whereClause)
            {
                // We only call this when sliceRestriction != null, i.e. for compact table with non composite comparator,
                // so it can't be a MultiColumnRelation.
                SingleColumnRelation rel = (SingleColumnRelation)r;
                if (cfm.getColumnDefinition(rel.getEntity().prepare(cfm)).kind == ColumnDefinition.Kind.CLUSTERING_COLUMN
                    && (rel.operator() == Operator.GT || rel.operator() == Operator.LT))
                    return rel;
            }

            // We're not supposed to call this method unless we know this can't happen
            throw new AssertionError();
        }

        private boolean containsAlias(final ColumnIdentifier name)
        {
            return Iterables.any(selectClause, new Predicate<RawSelector>()
                                               {
                                                   public boolean apply(RawSelector raw)
                                                   {
                                                       return name.equals(raw.alias);
                                                   }
                                               });
        }

        private ColumnSpecification limitReceiver()
        {
            return new ColumnSpecification(keyspace(), columnFamily(), new ColumnIdentifier("[limit]", true), Int32Type.instance);
        }

        private static ColumnSpecification makeCollectionReceiver(ColumnSpecification collection, boolean isKey)
        {
            assert collection.type.isCollection();
            switch (((CollectionType)collection.type).kind)
            {
                case LIST:
                    assert !isKey;
                    return Lists.valueSpecOf(collection);
                case SET:
                    assert !isKey;
                    return Sets.valueSpecOf(collection);
                case MAP:
                    return isKey ? Maps.keySpecOf(collection) : Maps.valueSpecOf(collection);
            }
            throw new AssertionError();
        }

        @Override
        public String toString()
        {
            return Objects.toStringHelper(this)
                          .add("name", cfName)
                          .add("selectClause", selectClause)
                          .add("whereClause", whereClause)
                          .add("isDistinct", parameters.isDistinct)
                          .add("isCount", parameters.isCount)
                          .toString();
        }
    }

    public static class Parameters
    {
        private final Map<ColumnIdentifier.Raw, Boolean> orderings;
        private final boolean isDistinct;
        private final boolean isCount;
        private final ColumnIdentifier countAlias;
        private final boolean allowFiltering;

        public Parameters(Map<ColumnIdentifier.Raw, Boolean> orderings,
                          boolean isDistinct,
                          boolean isCount,
                          ColumnIdentifier countAlias,
                          boolean allowFiltering)
        {
            this.orderings = orderings;
            this.isDistinct = isDistinct;
            this.isCount = isCount;
            this.countAlias = countAlias;
            this.allowFiltering = allowFiltering;
        }
    }

    /**
     * Used in orderResults(...) method when single 'ORDER BY' condition where given
     */
    private static class SingleColumnComparator implements Comparator<List<ByteBuffer>>
    {
        private final int index;
        private final Comparator<ByteBuffer> comparator;

        public SingleColumnComparator(int columnIndex, Comparator<ByteBuffer> orderer)
        {
            index = columnIndex;
            comparator = orderer;
        }

        public int compare(List<ByteBuffer> a, List<ByteBuffer> b)
        {
            return comparator.compare(a.get(index), b.get(index));
        }
    }

    /**
     * Used in orderResults(...) method when multiple 'ORDER BY' conditions where given
     */
    private static class CompositeComparator implements Comparator<List<ByteBuffer>>
    {
        private final List<Comparator<ByteBuffer>> orderTypes;
        private final List<Integer> positions;

        private CompositeComparator(List<Comparator<ByteBuffer>> orderTypes, List<Integer> positions)
        {
            this.orderTypes = orderTypes;
            this.positions = positions;
        }

        public int compare(List<ByteBuffer> a, List<ByteBuffer> b)
        {
            for (int i = 0; i < positions.size(); i++)
            {
                Comparator<ByteBuffer> type = orderTypes.get(i);
                int columnPos = positions.get(i);

                ByteBuffer aValue = a.get(columnPos);
                ByteBuffer bValue = b.get(columnPos);

                int comparison = type.compare(aValue, bValue);

                if (comparison != 0)
                    return comparison;
            }

            return 0;
        }
    }
}


File: src/java/org/apache/cassandra/cql3/statements/TruncateStatement.java
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

import java.io.IOException;
import java.util.concurrent.TimeoutException;

import org.apache.cassandra.auth.Permission;
import org.apache.cassandra.cql3.*;
import org.apache.cassandra.exceptions.*;
import org.apache.cassandra.transport.messages.ResultMessage;
import org.apache.cassandra.service.ClientState;
import org.apache.cassandra.service.QueryState;
import org.apache.cassandra.service.StorageProxy;
import org.apache.cassandra.thrift.ThriftValidation;

public class TruncateStatement extends CFStatement implements CQLStatement
{
    public TruncateStatement(CFName name)
    {
        super(name);
    }

    public int getBoundTerms()
    {
        return 0;
    }

    public Prepared prepare() throws InvalidRequestException
    {
        return new Prepared(this);
    }

    public void checkAccess(ClientState state) throws InvalidRequestException, UnauthorizedException
    {
        state.hasColumnFamilyAccess(keyspace(), columnFamily(), Permission.MODIFY);
    }

    public void validate(ClientState state) throws InvalidRequestException
    {
        ThriftValidation.validateColumnFamily(keyspace(), columnFamily());
    }

    public ResultMessage execute(QueryState state, QueryOptions options) throws InvalidRequestException, TruncateException
    {
        try
        {
            StorageProxy.truncateBlocking(keyspace(), columnFamily());
        }
        catch (UnavailableException e)
        {
            throw new TruncateException(e);
        }
        catch (TimeoutException e)
        {
            throw new TruncateException(e);
        }
        catch (IOException e)
        {
            throw new TruncateException(e);
        }
        return null;
    }

    public ResultMessage executeInternal(QueryState state, QueryOptions options)
    {
        throw new UnsupportedOperationException();
    }
}


File: src/java/org/apache/cassandra/db/ColumnFamilyStore.java
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
package org.apache.cassandra.db;

import java.io.*;
import java.lang.management.ManagementFactory;
import java.nio.ByteBuffer;
import java.util.*;
import java.util.concurrent.*;
import java.util.concurrent.atomic.AtomicInteger;
import java.util.concurrent.atomic.AtomicReference;
import java.util.regex.Pattern;
import javax.management.*;
import javax.management.openmbean.*;

import com.google.common.annotations.VisibleForTesting;
import com.google.common.base.*;
import com.google.common.base.Throwables;
import com.google.common.collect.*;
import com.google.common.util.concurrent.*;

import org.apache.cassandra.io.FSWriteError;
import org.json.simple.*;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import org.apache.cassandra.cache.*;
import org.apache.cassandra.concurrent.*;
import org.apache.cassandra.config.*;
import org.apache.cassandra.config.CFMetaData.SpeculativeRetry;
import org.apache.cassandra.db.commitlog.CommitLog;
import org.apache.cassandra.db.commitlog.ReplayPosition;
import org.apache.cassandra.db.compaction.*;
import org.apache.cassandra.db.composites.CellName;
import org.apache.cassandra.db.composites.CellNameType;
import org.apache.cassandra.db.composites.Composite;
import org.apache.cassandra.db.filter.ColumnSlice;
import org.apache.cassandra.db.filter.ExtendedFilter;
import org.apache.cassandra.db.filter.IDiskAtomFilter;
import org.apache.cassandra.db.filter.QueryFilter;
import org.apache.cassandra.db.filter.SliceQueryFilter;
import org.apache.cassandra.db.index.SecondaryIndex;
import org.apache.cassandra.db.index.SecondaryIndexManager;
import org.apache.cassandra.dht.*;
import org.apache.cassandra.dht.Range;
import org.apache.cassandra.exceptions.ConfigurationException;
import org.apache.cassandra.io.FSReadError;
import org.apache.cassandra.io.compress.CompressionParameters;
import org.apache.cassandra.io.sstable.*;
import org.apache.cassandra.io.sstable.Descriptor;
import org.apache.cassandra.io.sstable.metadata.CompactionMetadata;
import org.apache.cassandra.io.sstable.metadata.MetadataType;
import org.apache.cassandra.io.util.FileUtils;
import org.apache.cassandra.metrics.ColumnFamilyMetrics;
import org.apache.cassandra.metrics.ColumnFamilyMetrics.Sampler;
import org.apache.cassandra.service.CacheService;
import org.apache.cassandra.service.StorageService;
import org.apache.cassandra.streaming.StreamLockfile;
import org.apache.cassandra.tracing.Tracing;
import org.apache.cassandra.utils.*;
import org.apache.cassandra.utils.concurrent.*;
import org.apache.cassandra.utils.TopKSampler.SamplerResult;
import org.apache.cassandra.utils.memory.MemtableAllocator;

import com.clearspring.analytics.stream.Counter;

public class ColumnFamilyStore implements ColumnFamilyStoreMBean
{
    private static final Logger logger = LoggerFactory.getLogger(ColumnFamilyStore.class);

    private static final ExecutorService flushExecutor = new JMXEnabledThreadPoolExecutor(DatabaseDescriptor.getFlushWriters(),
                                                                                          StageManager.KEEPALIVE,
                                                                                          TimeUnit.SECONDS,
                                                                                          new LinkedBlockingQueue<Runnable>(),
                                                                                          new NamedThreadFactory("MemtableFlushWriter"),
                                                                                          "internal");

    // post-flush executor is single threaded to provide guarantee that any flush Future on a CF will never return until prior flushes have completed
    private static final ExecutorService postFlushExecutor = new JMXEnabledThreadPoolExecutor(1,
                                                                                              StageManager.KEEPALIVE,
                                                                                              TimeUnit.SECONDS,
                                                                                              new LinkedBlockingQueue<Runnable>(),
                                                                                              new NamedThreadFactory("MemtablePostFlush"),
                                                                                              "internal");

    private static final ExecutorService reclaimExecutor = new JMXEnabledThreadPoolExecutor(1,
                                                                                            StageManager.KEEPALIVE,
                                                                                            TimeUnit.SECONDS,
                                                                                            new LinkedBlockingQueue<Runnable>(),
                                                                                            new NamedThreadFactory("MemtableReclaimMemory"),
                                                                                            "internal");

    private static final String[] COUNTER_NAMES = new String[]{"raw", "count", "error", "string"};
    private static final String[] COUNTER_DESCS = new String[]
    { "partition key in raw hex bytes",
      "value of this partition for given sampler",
      "value is within the error bounds plus or minus of this",
      "the partition key turned into a human readable format" };
    private static final CompositeType COUNTER_COMPOSITE_TYPE;
    private static final TabularType COUNTER_TYPE;

    private static final String[] SAMPLER_NAMES = new String[]{"cardinality", "partitions"};
    private static final String[] SAMPLER_DESCS = new String[]
    { "cardinality of partitions",
      "list of counter results" };

    private static final String SAMPLING_RESULTS_NAME = "SAMPLING_RESULTS";
    private static final CompositeType SAMPLING_RESULT;

    static
    {
        try
        {
            OpenType<?>[] counterTypes = new OpenType[] { SimpleType.STRING, SimpleType.LONG, SimpleType.LONG, SimpleType.STRING };
            COUNTER_COMPOSITE_TYPE = new CompositeType(SAMPLING_RESULTS_NAME, SAMPLING_RESULTS_NAME, COUNTER_NAMES, COUNTER_DESCS, counterTypes);
            COUNTER_TYPE = new TabularType(SAMPLING_RESULTS_NAME, SAMPLING_RESULTS_NAME, COUNTER_COMPOSITE_TYPE, COUNTER_NAMES);

            OpenType<?>[] samplerTypes = new OpenType[] { SimpleType.LONG, COUNTER_TYPE };
            SAMPLING_RESULT = new CompositeType(SAMPLING_RESULTS_NAME, SAMPLING_RESULTS_NAME, SAMPLER_NAMES, SAMPLER_DESCS, samplerTypes);
        } catch (OpenDataException e)
        {
            throw Throwables.propagate(e);
        }
    }

    public final Keyspace keyspace;
    public final String name;
    public final CFMetaData metadata;
    public final IPartitioner partitioner;
    private final String mbeanName;
    private volatile boolean valid = true;

    /**
     * Memtables and SSTables on disk for this column family.
     *
     * We synchronize on the DataTracker to ensure isolation when we want to make sure
     * that the memtable we're acting on doesn't change out from under us.  I.e., flush
     * syncronizes on it to make sure it can submit on both executors atomically,
     * so anyone else who wants to make sure flush doesn't interfere should as well.
     */
    private final DataTracker data;

    /* The read order, used to track accesses to off-heap memtable storage */
    public final OpOrder readOrdering = new OpOrder();

    /* This is used to generate the next index for a SSTable */
    private final AtomicInteger fileIndexGenerator = new AtomicInteger(0);

    public final SecondaryIndexManager indexManager;

    /* These are locally held copies to be changed from the config during runtime */
    private volatile DefaultInteger minCompactionThreshold;
    private volatile DefaultInteger maxCompactionThreshold;
    private final WrappingCompactionStrategy compactionStrategyWrapper;

    public final Directories directories;

    public final ColumnFamilyMetrics metric;
    public volatile long sampleLatencyNanos;
    private final ScheduledFuture<?> latencyCalculator;

    public static void shutdownPostFlushExecutor() throws InterruptedException
    {
        postFlushExecutor.shutdown();
        postFlushExecutor.awaitTermination(60, TimeUnit.SECONDS);
    }

    public void reload()
    {
        // metadata object has been mutated directly. make all the members jibe with new settings.

        // only update these runtime-modifiable settings if they have not been modified.
        if (!minCompactionThreshold.isModified())
            for (ColumnFamilyStore cfs : concatWithIndexes())
                cfs.minCompactionThreshold = new DefaultInteger(metadata.getMinCompactionThreshold());
        if (!maxCompactionThreshold.isModified())
            for (ColumnFamilyStore cfs : concatWithIndexes())
                cfs.maxCompactionThreshold = new DefaultInteger(metadata.getMaxCompactionThreshold());

        compactionStrategyWrapper.maybeReloadCompactionStrategy(metadata);

        scheduleFlush();

        indexManager.reload();

        // If the CF comparator has changed, we need to change the memtable,
        // because the old one still aliases the previous comparator.
        if (data.getView().getCurrentMemtable().initialComparator != metadata.comparator)
            switchMemtable();
    }

    void scheduleFlush()
    {
        int period = metadata.getMemtableFlushPeriod();
        if (period > 0)
        {
            logger.debug("scheduling flush in {} ms", period);
            WrappedRunnable runnable = new WrappedRunnable()
            {
                protected void runMayThrow() throws Exception
                {
                    synchronized (data)
                    {
                        Memtable current = data.getView().getCurrentMemtable();
                        // if we're not expired, we've been hit by a scheduled flush for an already flushed memtable, so ignore
                        if (current.isExpired())
                        {
                            if (current.isClean())
                            {
                                // if we're still clean, instead of swapping just reschedule a flush for later
                                scheduleFlush();
                            }
                            else
                            {
                                // we'll be rescheduled by the constructor of the Memtable.
                                forceFlush();
                            }
                        }
                    }
                }
            };
            ScheduledExecutors.scheduledTasks.schedule(runnable, period, TimeUnit.MILLISECONDS);
        }
    }

    public static Runnable getBackgroundCompactionTaskSubmitter()
    {
        return new Runnable()
        {
            public void run()
            {
                List<ColumnFamilyStore> submitted = new ArrayList<>();
                for (Keyspace keyspace : Keyspace.all())
                    for (ColumnFamilyStore cfs : keyspace.getColumnFamilyStores())
                        if (!CompactionManager.instance.submitBackground(cfs, false).isEmpty())
                            submitted.add(cfs);

                while (!submitted.isEmpty() && CompactionManager.instance.getActiveCompactions() < CompactionManager.instance.getMaximumCompactorThreads())
                {
                    List<ColumnFamilyStore> submitMore = ImmutableList.copyOf(submitted);
                    submitted.clear();
                    for (ColumnFamilyStore cfs : submitMore)
                        if (!CompactionManager.instance.submitBackground(cfs, false).isEmpty())
                            submitted.add(cfs);
                }
            }
        };
    }

    public void setCompactionStrategyClass(String compactionStrategyClass)
    {
        try
        {
            metadata.compactionStrategyClass = CFMetaData.createCompactionStrategy(compactionStrategyClass);
            compactionStrategyWrapper.maybeReloadCompactionStrategy(metadata);
        }
        catch (ConfigurationException e)
        {
            throw new IllegalArgumentException(e.getMessage());
        }
    }

    public String getCompactionStrategyClass()
    {
        return metadata.compactionStrategyClass.getName();
    }

    public Map<String,String> getCompressionParameters()
    {
        return metadata.compressionParameters().asThriftOptions();
    }

    public void setCompressionParameters(Map<String,String> opts)
    {
        try
        {
            metadata.compressionParameters = CompressionParameters.create(opts);
        }
        catch (ConfigurationException e)
        {
            throw new IllegalArgumentException(e.getMessage());
        }
    }

    public void setCrcCheckChance(double crcCheckChance)
    {
        try
        {
            for (SSTableReader sstable : keyspace.getAllSSTables())
                if (sstable.compression)
                    sstable.getCompressionMetadata().parameters.setCrcCheckChance(crcCheckChance);
        }
        catch (ConfigurationException e)
        {
            throw new IllegalArgumentException(e.getMessage());
        }
    }

    private ColumnFamilyStore(Keyspace keyspace,
                              String columnFamilyName,
                              IPartitioner partitioner,
                              int generation,
                              CFMetaData metadata,
                              Directories directories,
                              boolean loadSSTables)
    {
        assert metadata != null : "null metadata for " + keyspace + ":" + columnFamilyName;

        this.keyspace = keyspace;
        name = columnFamilyName;
        this.metadata = metadata;
        this.minCompactionThreshold = new DefaultInteger(metadata.getMinCompactionThreshold());
        this.maxCompactionThreshold = new DefaultInteger(metadata.getMaxCompactionThreshold());
        this.partitioner = partitioner;
        this.directories = directories;
        this.indexManager = new SecondaryIndexManager(this);
        this.metric = new ColumnFamilyMetrics(this);
        fileIndexGenerator.set(generation);
        sampleLatencyNanos = DatabaseDescriptor.getReadRpcTimeout() / 2;

        CachingOptions caching = metadata.getCaching();

        logger.info("Initializing {}.{}", keyspace.getName(), name);

        // scan for sstables corresponding to this cf and load them
        data = new DataTracker(this);

        if (loadSSTables)
        {
            Directories.SSTableLister sstableFiles = directories.sstableLister().skipTemporary(true);
            Collection<SSTableReader> sstables = SSTableReader.openAll(sstableFiles.list().entrySet(), metadata, this.partitioner);
            data.addInitialSSTables(sstables);
        }

        if (caching.keyCache.isEnabled())
            CacheService.instance.keyCache.loadSaved(this);

        // compaction strategy should be created after the CFS has been prepared
        this.compactionStrategyWrapper = new WrappingCompactionStrategy(this);

        if (maxCompactionThreshold.value() <= 0 || minCompactionThreshold.value() <=0)
        {
            logger.warn("Disabling compaction strategy by setting compaction thresholds to 0 is deprecated, set the compaction option 'enabled' to 'false' instead.");
            this.compactionStrategyWrapper.disable();
        }

        // create the private ColumnFamilyStores for the secondary column indexes
        for (ColumnDefinition info : metadata.allColumns())
        {
            if (info.getIndexType() != null)
                indexManager.addIndexedColumn(info);
        }

        // register the mbean
        String type = this.partitioner instanceof LocalPartitioner ? "IndexColumnFamilies" : "ColumnFamilies";
        mbeanName = "org.apache.cassandra.db:type=" + type + ",keyspace=" + this.keyspace.getName() + ",columnfamily=" + name;
        try
        {
            MBeanServer mbs = ManagementFactory.getPlatformMBeanServer();
            ObjectName nameObj = new ObjectName(mbeanName);
            mbs.registerMBean(this, nameObj);
        }
        catch (Exception e)
        {
            throw new RuntimeException(e);
        }
        logger.debug("retryPolicy for {} is {}", name, this.metadata.getSpeculativeRetry());
        latencyCalculator = ScheduledExecutors.optionalTasks.scheduleWithFixedDelay(new Runnable()
        {
            public void run()
            {
                SpeculativeRetry retryPolicy = ColumnFamilyStore.this.metadata.getSpeculativeRetry();
                switch (retryPolicy.type)
                {
                    case PERCENTILE:
                        // get percentile in nanos
                        assert metric.coordinatorReadLatency.durationUnit() == TimeUnit.MICROSECONDS;
                        sampleLatencyNanos = (long) (metric.coordinatorReadLatency.getSnapshot().getValue(retryPolicy.value) * 1000d);
                        break;
                    case CUSTOM:
                        // convert to nanos, since configuration is in millisecond
                        sampleLatencyNanos = (long) (retryPolicy.value * 1000d * 1000d);
                        break;
                    default:
                        sampleLatencyNanos = Long.MAX_VALUE;
                        break;
                }
            }
        }, DatabaseDescriptor.getReadRpcTimeout(), DatabaseDescriptor.getReadRpcTimeout(), TimeUnit.MILLISECONDS);
    }

    /** call when dropping or renaming a CF. Performs mbean housekeeping and invalidates CFS to other operations */
    public void invalidate()
    {
        // disable and cancel in-progress compactions before invalidating
        valid = false;

        try
        {
            unregisterMBean();
        }
        catch (Exception e)
        {
            JVMStabilityInspector.inspectThrowable(e);
            // this shouldn't block anything.
            logger.warn("Failed unregistering mbean: {}", mbeanName, e);
        }

        latencyCalculator.cancel(false);
        SystemKeyspace.removeTruncationRecord(metadata.cfId);
        data.unreferenceSSTables();
        indexManager.invalidate();

        invalidateCaches();
    }

    /**
     * Removes every SSTable in the directory from the DataTracker's view.
     * @param directory the unreadable directory, possibly with SSTables in it, but not necessarily.
     */
    void maybeRemoveUnreadableSSTables(File directory)
    {
        data.removeUnreadableSSTables(directory);
    }

    void unregisterMBean() throws MalformedObjectNameException, InstanceNotFoundException, MBeanRegistrationException
    {
        MBeanServer mbs = ManagementFactory.getPlatformMBeanServer();
        ObjectName nameObj = new ObjectName(mbeanName);
        if (mbs.isRegistered(nameObj))
            mbs.unregisterMBean(nameObj);

        // unregister metrics
        metric.release();
    }

    public long getMinRowSize()
    {
        return metric.minRowSize.value();
    }

    public long getMaxRowSize()
    {
        return metric.maxRowSize.value();
    }

    public long getMeanRowSize()
    {
        return metric.meanRowSize.value();
    }

    public int getMeanColumns()
    {
        return data.getMeanColumns();
    }

    public static ColumnFamilyStore createColumnFamilyStore(Keyspace keyspace, String columnFamily, boolean loadSSTables)
    {
        return createColumnFamilyStore(keyspace, columnFamily, StorageService.getPartitioner(), Schema.instance.getCFMetaData(keyspace.getName(), columnFamily), loadSSTables);
    }

    public static ColumnFamilyStore createColumnFamilyStore(Keyspace keyspace, String columnFamily, IPartitioner partitioner, CFMetaData metadata)
    {
        return createColumnFamilyStore(keyspace, columnFamily, partitioner, metadata, true);
    }

    private static synchronized ColumnFamilyStore createColumnFamilyStore(Keyspace keyspace,
                                                                         String columnFamily,
                                                                         IPartitioner partitioner,
                                                                         CFMetaData metadata,
                                                                         boolean loadSSTables)
    {
        // get the max generation number, to prevent generation conflicts
        Directories directories = new Directories(metadata);
        Directories.SSTableLister lister = directories.sstableLister().includeBackups(true);
        List<Integer> generations = new ArrayList<Integer>();
        for (Map.Entry<Descriptor, Set<Component>> entry : lister.list().entrySet())
        {
            Descriptor desc = entry.getKey();
            generations.add(desc.generation);
            if (!desc.isCompatible())
                throw new RuntimeException(String.format("Incompatible SSTable found. Current version %s is unable to read file: %s. Please run upgradesstables.",
                                                          Descriptor.Version.CURRENT, desc));
        }
        Collections.sort(generations);
        int value = (generations.size() > 0) ? (generations.get(generations.size() - 1)) : 0;

        return new ColumnFamilyStore(keyspace, columnFamily, partitioner, value, metadata, directories, loadSSTables);
    }

    /**
     * Removes unnecessary files from the cf directory at startup: these include temp files, orphans, zero-length files
     * and compacted sstables. Files that cannot be recognized will be ignored.
     */
    public static void scrubDataDirectories(CFMetaData metadata)
    {
        Directories directories = new Directories(metadata);

        // remove any left-behind SSTables from failed/stalled streaming
        FileFilter filter = new FileFilter()
        {
            public boolean accept(File pathname)
            {
                return pathname.toString().endsWith(StreamLockfile.FILE_EXT);
            }
        };
        for (File dir : directories.getCFDirectories())
        {
            File[] lockfiles = dir.listFiles(filter);
            // lock files can be null if I/O error happens
            if (lockfiles == null || lockfiles.length == 0)
                continue;
            logger.info("Removing SSTables from failed streaming session. Found {} files to cleanup.", lockfiles.length);

            for (File lockfile : lockfiles)
            {
                StreamLockfile streamLockfile = new StreamLockfile(lockfile);
                streamLockfile.cleanup();
                streamLockfile.delete();
            }
        }

        logger.debug("Removing compacted SSTable files from {} (see http://wiki.apache.org/cassandra/MemtableSSTable)", metadata.cfName);

        for (Map.Entry<Descriptor,Set<Component>> sstableFiles : directories.sstableLister().list().entrySet())
        {
            Descriptor desc = sstableFiles.getKey();
            Set<Component> components = sstableFiles.getValue();

            if (desc.type.isTemporary)
            {
                SSTable.delete(desc, components);
                continue;
            }

            File dataFile = new File(desc.filenameFor(Component.DATA));
            if (components.contains(Component.DATA) && dataFile.length() > 0)
                // everything appears to be in order... moving on.
                continue;

            // missing the DATA file! all components are orphaned
            logger.warn("Removing orphans for {}: {}", desc, components);
            for (Component component : components)
            {
                FileUtils.deleteWithConfirm(desc.filenameFor(component));
            }
        }

        // cleanup incomplete saved caches
        Pattern tmpCacheFilePattern = Pattern.compile(metadata.ksName + "-" + metadata.cfName + "-(Key|Row)Cache.*\\.tmp$");
        File dir = new File(DatabaseDescriptor.getSavedCachesLocation());

        if (dir.exists())
        {
            assert dir.isDirectory();
            for (File file : dir.listFiles())
                if (tmpCacheFilePattern.matcher(file.getName()).matches())
                    if (!file.delete())
                        logger.warn("could not delete {}", file.getAbsolutePath());
        }

        // also clean out any index leftovers.
        for (ColumnDefinition def : metadata.allColumns())
        {
            if (def.isIndexed())
            {
                CellNameType indexComparator = SecondaryIndex.getIndexComparator(metadata, def);
                if (indexComparator != null)
                {
                    CFMetaData indexMetadata = CFMetaData.newIndexMetadata(metadata, def, indexComparator);
                    scrubDataDirectories(indexMetadata);
                }
            }
        }
    }

    /**
     * Replacing compacted sstables is atomic as far as observers of DataTracker are concerned, but not on the
     * filesystem: first the new sstables are renamed to "live" status (i.e., the tmp marker is removed), then
     * their ancestors are removed.
     *
     * If an unclean shutdown happens at the right time, we can thus end up with both the new ones and their
     * ancestors "live" in the system.  This is harmless for normal data, but for counters it can cause overcounts.
     *
     * To prevent this, we record sstables being compacted in the system keyspace.  If we find unfinished
     * compactions, we remove the new ones (since those may be incomplete -- under LCS, we may create multiple
     * sstables from any given ancestor).
     */
    public static void removeUnfinishedCompactionLeftovers(CFMetaData metadata, Map<Integer, UUID> unfinishedCompactions)
    {
        Directories directories = new Directories(metadata);

        Set<Integer> allGenerations = new HashSet<>();
        for (Descriptor desc : directories.sstableLister().list().keySet())
            allGenerations.add(desc.generation);

        // sanity-check unfinishedCompactions
        Set<Integer> unfinishedGenerations = unfinishedCompactions.keySet();
        if (!allGenerations.containsAll(unfinishedGenerations))
        {
            HashSet<Integer> missingGenerations = new HashSet<>(unfinishedGenerations);
            missingGenerations.removeAll(allGenerations);
            logger.debug("Unfinished compactions of {}.{} reference missing sstables of generations {}",
                         metadata.ksName, metadata.cfName, missingGenerations);
        }

        // remove new sstables from compactions that didn't complete, and compute
        // set of ancestors that shouldn't exist anymore
        Set<Integer> completedAncestors = new HashSet<>();
        for (Map.Entry<Descriptor, Set<Component>> sstableFiles : directories.sstableLister().skipTemporary(true).list().entrySet())
        {
            Descriptor desc = sstableFiles.getKey();

            Set<Integer> ancestors;
            try
            {
                CompactionMetadata compactionMetadata = (CompactionMetadata) desc.getMetadataSerializer().deserialize(desc, MetadataType.COMPACTION);
                ancestors = compactionMetadata.ancestors;
            }
            catch (IOException e)
            {
                throw new FSReadError(e, desc.filenameFor(Component.STATS));
            }
            catch (NullPointerException e)
            {
                throw new FSReadError(e, "Failed to remove unfinished compaction leftovers (file: " + desc.filenameFor(Component.STATS) + ").  See log for details.");
            }

            if (!ancestors.isEmpty()
                && unfinishedGenerations.containsAll(ancestors)
                && allGenerations.containsAll(ancestors))
            {
                // any of the ancestors would work, so we'll just lookup the compaction task ID with the first one
                UUID compactionTaskID = unfinishedCompactions.get(ancestors.iterator().next());
                assert compactionTaskID != null;
                logger.debug("Going to delete unfinished compaction product {}", desc);
                SSTable.delete(desc, sstableFiles.getValue());
                SystemKeyspace.finishCompaction(compactionTaskID);
            }
            else
            {
                completedAncestors.addAll(ancestors);
            }
        }

        // remove old sstables from compactions that did complete
        for (Map.Entry<Descriptor, Set<Component>> sstableFiles : directories.sstableLister().list().entrySet())
        {
            Descriptor desc = sstableFiles.getKey();
            if (completedAncestors.contains(desc.generation))
            {
                // if any of the ancestors were participating in a compaction, finish that compaction
                logger.debug("Going to delete leftover compaction ancestor {}", desc);
                SSTable.delete(desc, sstableFiles.getValue());
                UUID compactionTaskID = unfinishedCompactions.get(desc.generation);
                if (compactionTaskID != null)
                    SystemKeyspace.finishCompaction(unfinishedCompactions.get(desc.generation));
            }
        }
    }

    // must be called after all sstables are loaded since row cache merges all row versions
    public void initRowCache()
    {
        if (!isRowCacheEnabled())
            return;

        long start = System.nanoTime();

        int cachedRowsRead = CacheService.instance.rowCache.loadSaved(this);
        if (cachedRowsRead > 0)
            logger.info("Completed loading ({} ms; {} keys) row cache for {}.{}",
                        TimeUnit.NANOSECONDS.toMillis(System.nanoTime() - start),
                        cachedRowsRead,
                        keyspace.getName(),
                        name);
    }

    public void initCounterCache()
    {
        if (!metadata.isCounter() || CacheService.instance.counterCache.getCapacity() == 0)
            return;

        long start = System.nanoTime();

        int cachedShardsRead = CacheService.instance.counterCache.loadSaved(this);
        if (cachedShardsRead > 0)
            logger.info("Completed loading ({} ms; {} shards) counter cache for {}.{}",
                        TimeUnit.NANOSECONDS.toMillis(System.nanoTime() - start),
                        cachedShardsRead,
                        keyspace.getName(),
                        name);
    }

    /**
     * See #{@code StorageService.loadNewSSTables(String, String)} for more info
     *
     * @param ksName The keyspace name
     * @param cfName The columnFamily name
     */
    public static synchronized void loadNewSSTables(String ksName, String cfName)
    {
        /** ks/cf existence checks will be done by open and getCFS methods for us */
        Keyspace keyspace = Keyspace.open(ksName);
        keyspace.getColumnFamilyStore(cfName).loadNewSSTables();
    }

    /**
     * #{@inheritDoc}
     */
    public synchronized void loadNewSSTables()
    {
        logger.info("Loading new SSTables for {}/{}...", keyspace.getName(), name);

        Set<Descriptor> currentDescriptors = new HashSet<Descriptor>();
        for (SSTableReader sstable : data.getView().sstables)
            currentDescriptors.add(sstable.descriptor);
        Set<SSTableReader> newSSTables = new HashSet<SSTableReader>();

        Directories.SSTableLister lister = directories.sstableLister().skipTemporary(true);
        for (Map.Entry<Descriptor, Set<Component>> entry : lister.list().entrySet())
        {
            Descriptor descriptor = entry.getKey();

            if (currentDescriptors.contains(descriptor))
                continue; // old (initialized) SSTable found, skipping
            if (descriptor.type.isTemporary) // in the process of being written
                continue;

            if (!descriptor.isCompatible())
                throw new RuntimeException(String.format("Can't open incompatible SSTable! Current version %s, found file: %s",
                                                         Descriptor.Version.CURRENT,
                                                         descriptor));

            // force foreign sstables to level 0
            try
            {
                if (new File(descriptor.filenameFor(Component.STATS)).exists())
                    descriptor.getMetadataSerializer().mutateLevel(descriptor, 0);
            }
            catch (IOException e)
            {
                SSTableReader.logOpenException(entry.getKey(), e);
                continue;
            }

            // Increment the generation until we find a filename that doesn't exist. This is needed because the new
            // SSTables that are being loaded might already use these generation numbers.
            Descriptor newDescriptor;
            do
            {
                newDescriptor = new Descriptor(descriptor.version,
                                               descriptor.directory,
                                               descriptor.ksname,
                                               descriptor.cfname,
                                               fileIndexGenerator.incrementAndGet(),
                                               Descriptor.Type.FINAL);
            }
            while (new File(newDescriptor.filenameFor(Component.DATA)).exists());

            logger.info("Renaming new SSTable {} to {}", descriptor, newDescriptor);
            SSTableWriter.rename(descriptor, newDescriptor, entry.getValue());

            SSTableReader reader;
            try
            {
                reader = SSTableReader.open(newDescriptor, entry.getValue(), metadata, partitioner);
            }
            catch (IOException e)
            {
                SSTableReader.logOpenException(entry.getKey(), e);
                continue;
            }
            newSSTables.add(reader);
        }

        if (newSSTables.isEmpty())
        {
            logger.info("No new SSTables were found for {}/{}", keyspace.getName(), name);
            return;
        }

        logger.info("Loading new SSTables and building secondary indexes for {}/{}: {}", keyspace.getName(), name, newSSTables);

        try (Refs<SSTableReader> refs = Refs.ref(newSSTables))
        {
            data.addSSTables(newSSTables);
            indexManager.maybeBuildSecondaryIndexes(newSSTables, indexManager.allIndexesNames());
        }

        logger.info("Done loading load new SSTables for {}/{}", keyspace.getName(), name);
    }

    public static void rebuildSecondaryIndex(String ksName, String cfName, String... idxNames)
    {
        ColumnFamilyStore cfs = Keyspace.open(ksName).getColumnFamilyStore(cfName);

        Set<String> indexes = new HashSet<String>(Arrays.asList(idxNames));

        Collection<SSTableReader> sstables = cfs.getSSTables();

        try (Refs<SSTableReader> refs = Refs.ref(sstables))
        {
            cfs.indexManager.setIndexRemoved(indexes);
            logger.info(String.format("User Requested secondary index re-build for %s/%s indexes", ksName, cfName));
            cfs.indexManager.maybeBuildSecondaryIndexes(sstables, indexes);
            cfs.indexManager.setIndexBuilt(indexes);
        }
    }

    public String getColumnFamilyName()
    {
        return name;
    }

    public String getTempSSTablePath(File directory)
    {
        return getTempSSTablePath(directory, Descriptor.Version.CURRENT);
    }

    private String getTempSSTablePath(File directory, Descriptor.Version version)
    {
        Descriptor desc = new Descriptor(version,
                                         directory,
                                         keyspace.getName(),
                                         name,
                                         fileIndexGenerator.incrementAndGet(),
                                         Descriptor.Type.TEMP);
        return desc.filenameFor(Component.DATA);
    }

    /**
     * Switches the memtable iff the live memtable is the one provided
     *
     * @param memtable
     */
    public Future<?> switchMemtableIfCurrent(Memtable memtable)
    {
        synchronized (data)
        {
            if (data.getView().getCurrentMemtable() == memtable)
                return switchMemtable();
        }
        return Futures.immediateFuture(null);
    }

    /*
     * switchMemtable puts Memtable.getSortedContents on the writer executor.  When the write is complete,
     * we turn the writer into an SSTableReader and add it to ssTables where it is available for reads.
     * This method does not block except for synchronizing on DataTracker, but the Future it returns will
     * not complete until the Memtable (and all prior Memtables) have been successfully flushed, and the CL
     * marked clean up to the position owned by the Memtable.
     */
    public ListenableFuture<?> switchMemtable()
    {
        synchronized (data)
        {
            logFlush();
            Flush flush = new Flush(false);
            flushExecutor.execute(flush);
            ListenableFutureTask<?> task = ListenableFutureTask.create(flush.postFlush, null);
            postFlushExecutor.submit(task);
            return task;
        }
    }

    // print out size of all memtables we're enqueuing
    private void logFlush()
    {
        // reclaiming includes that which we are GC-ing;
        float onHeapRatio = 0, offHeapRatio = 0;
        long onHeapTotal = 0, offHeapTotal = 0;
        Memtable memtable = getDataTracker().getView().getCurrentMemtable();
        onHeapRatio +=  memtable.getAllocator().onHeap().ownershipRatio();
        offHeapRatio += memtable.getAllocator().offHeap().ownershipRatio();
        onHeapTotal += memtable.getAllocator().onHeap().owns();
        offHeapTotal += memtable.getAllocator().offHeap().owns();

        for (SecondaryIndex index : indexManager.getIndexes())
        {
            if (index.getIndexCfs() != null)
            {
                MemtableAllocator allocator = index.getIndexCfs().getDataTracker().getView().getCurrentMemtable().getAllocator();
                onHeapRatio += allocator.onHeap().ownershipRatio();
                offHeapRatio += allocator.offHeap().ownershipRatio();
                onHeapTotal += allocator.onHeap().owns();
                offHeapTotal += allocator.offHeap().owns();
            }
        }

        logger.info("Enqueuing flush of {}: {}", name, String.format("%d (%.0f%%) on-heap, %d (%.0f%%) off-heap",
                                                                     onHeapTotal, onHeapRatio * 100, offHeapTotal, offHeapRatio * 100));
    }


    public ListenableFuture<?> forceFlush()
    {
        return forceFlush(null);
    }

    /**
     * Flush if there is unflushed data that was written to the CommitLog before @param flushIfDirtyBefore
     * (inclusive).  If @param flushIfDirtyBefore is null, flush if there is any unflushed data.
     *
     * @return a Future such that when the future completes, all data inserted before forceFlush was called,
     * will be flushed.
     */
    public ListenableFuture<?> forceFlush(ReplayPosition flushIfDirtyBefore)
    {
        // we synchronize on the data tracker to ensure we don't race against other calls to switchMemtable(),
        // unnecessarily queueing memtables that are about to be made clean
        synchronized (data)
        {
            // during index build, 2ary index memtables can be dirty even if parent is not.  if so,
            // we want to flush the 2ary index ones too.
            boolean clean = true;
            for (ColumnFamilyStore cfs : concatWithIndexes())
                clean &= cfs.data.getView().getCurrentMemtable().isCleanAfter(flushIfDirtyBefore);

            if (clean)
            {
                // We could have a memtable for this column family that is being
                // flushed. Make sure the future returned wait for that so callers can
                // assume that any data inserted prior to the call are fully flushed
                // when the future returns (see #5241).
                ListenableFutureTask<?> task = ListenableFutureTask.create(new Runnable()
                {
                    public void run()
                    {
                        logger.debug("forceFlush requested but everything is clean in {}", name);
                    }
                }, null);
                postFlushExecutor.execute(task);
                return task;
            }

            return switchMemtable();
        }
    }

    public void forceBlockingFlush()
    {
        FBUtilities.waitOnFuture(forceFlush());
    }

    /**
     * Both synchronises custom secondary indexes and provides ordering guarantees for futures on switchMemtable/flush
     * etc, which expect to be able to wait until the flush (and all prior flushes) requested have completed.
     */
    private final class PostFlush implements Runnable
    {
        final boolean flushSecondaryIndexes;
        final OpOrder.Barrier writeBarrier;
        final CountDownLatch latch = new CountDownLatch(1);
        final ReplayPosition lastReplayPosition;

        private PostFlush(boolean flushSecondaryIndexes, OpOrder.Barrier writeBarrier, ReplayPosition lastReplayPosition)
        {
            this.writeBarrier = writeBarrier;
            this.flushSecondaryIndexes = flushSecondaryIndexes;
            this.lastReplayPosition = lastReplayPosition;
        }

        public void run()
        {
            writeBarrier.await();

            /**
             * we can flush 2is as soon as the barrier completes, as they will be consistent with (or ahead of) the
             * flushed memtables and CL position, which is as good as we can guarantee.
             * TODO: SecondaryIndex should support setBarrier(), so custom implementations can co-ordinate exactly
             * with CL as we do with memtables/CFS-backed SecondaryIndexes.
             */

            if (flushSecondaryIndexes)
            {
                for (SecondaryIndex index : indexManager.getIndexesNotBackedByCfs())
                {
                    // flush any non-cfs backed indexes
                    logger.info("Flushing SecondaryIndex {}", index);
                    index.forceBlockingFlush();
                }
            }

            try
            {
                // we wait on the latch for the lastReplayPosition to be set, and so that waiters
                // on this task can rely on all prior flushes being complete
                latch.await();
            }
            catch (InterruptedException e)
            {
                throw new IllegalStateException();
            }

            // must check lastReplayPosition != null because Flush may find that all memtables are clean
            // and so not set a lastReplayPosition
            if (lastReplayPosition != null)
            {
                CommitLog.instance.discardCompletedSegments(metadata.cfId, lastReplayPosition);
            }

            metric.pendingFlushes.dec();
        }
    }

    /**
     * Should only be constructed/used from switchMemtable() or truncate(), with ownership of the DataTracker monitor.
     * In the constructor the current memtable(s) are swapped, and a barrier on outstanding writes is issued;
     * when run by the flushWriter the barrier is waited on to ensure all outstanding writes have completed
     * before all memtables are immediately written, and the CL is either immediately marked clean or, if
     * there are custom secondary indexes, the post flush clean up is left to update those indexes and mark
     * the CL clean
     */
    private final class Flush implements Runnable
    {
        final OpOrder.Barrier writeBarrier;
        final List<Memtable> memtables;
        final PostFlush postFlush;
        final boolean truncate;

        private Flush(boolean truncate)
        {
            // if true, we won't flush, we'll just wait for any outstanding writes, switch the memtable, and discard
            this.truncate = truncate;

            metric.pendingFlushes.inc();
            /**
             * To ensure correctness of switch without blocking writes, run() needs to wait for all write operations
             * started prior to the switch to complete. We do this by creating a Barrier on the writeOrdering
             * that all write operations register themselves with, and assigning this barrier to the memtables,
             * after which we *.issue()* the barrier. This barrier is used to direct write operations started prior
             * to the barrier.issue() into the memtable we have switched out, and any started after to its replacement.
             * In doing so it also tells the write operations to update the lastReplayPosition of the memtable, so
             * that we know the CL position we are dirty to, which can be marked clean when we complete.
             */
            writeBarrier = keyspace.writeOrder.newBarrier();
            memtables = new ArrayList<>();

            // submit flushes for the memtable for any indexed sub-cfses, and our own
            AtomicReference<ReplayPosition> lastReplayPositionHolder = new AtomicReference<>();
            for (ColumnFamilyStore cfs : concatWithIndexes())
            {
                // switch all memtables, regardless of their dirty status, setting the barrier
                // so that we can reach a coordinated decision about cleanliness once they
                // are no longer possible to be modified
                Memtable mt = cfs.data.switchMemtable(truncate);
                mt.setDiscarding(writeBarrier, lastReplayPositionHolder);
                memtables.add(mt);
            }

            // we now attempt to define the lastReplayPosition; we do this by grabbing the current limit from the CL
            // and attempting to set the holder to this value. at the same time all writes to the memtables are
            // also maintaining this value, so if somebody sneaks ahead of us somehow (should be rare) we simply retry,
            // so that we know all operations prior to the position have not reached it yet
            ReplayPosition lastReplayPosition;
            while (true)
            {
                lastReplayPosition = new Memtable.LastReplayPosition(CommitLog.instance.getContext());
                ReplayPosition currentLast = lastReplayPositionHolder.get();
                if ((currentLast == null || currentLast.compareTo(lastReplayPosition) <= 0)
                    && lastReplayPositionHolder.compareAndSet(currentLast, lastReplayPosition))
                    break;
            }

            // we then issue the barrier; this lets us wait for all operations started prior to the barrier to complete;
            // since this happens after wiring up the lastReplayPosition, we also know all operations with earlier
            // replay positions have also completed, i.e. the memtables are done and ready to flush
            writeBarrier.issue();
            postFlush = new PostFlush(!truncate, writeBarrier, lastReplayPosition);
        }

        public void run()
        {
            // mark writes older than the barrier as blocking progress, permitting them to exceed our memory limit
            // if they are stuck waiting on it, then wait for them all to complete
            writeBarrier.markBlocking();
            writeBarrier.await();

            // mark all memtables as flushing, removing them from the live memtable list, and
            // remove any memtables that are already clean from the set we need to flush
            Iterator<Memtable> iter = memtables.iterator();
            while (iter.hasNext())
            {
                Memtable memtable = iter.next();
                memtable.cfs.data.markFlushing(memtable);
                if (memtable.isClean() || truncate)
                {
                    memtable.cfs.replaceFlushed(memtable, null);
                    reclaim(memtable);
                    iter.remove();
                }
            }

            if (memtables.isEmpty())
            {
                postFlush.latch.countDown();
                return;
            }

            metric.memtableSwitchCount.inc();

            for (Memtable memtable : memtables)
            {
                // flush the memtable
                MoreExecutors.sameThreadExecutor().execute(memtable.flushRunnable());
                reclaim(memtable);
            }

            // signal the post-flush we've done our work
            postFlush.latch.countDown();
        }

        private void reclaim(final Memtable memtable)
        {
            // issue a read barrier for reclaiming the memory, and offload the wait to another thread
            final OpOrder.Barrier readBarrier = readOrdering.newBarrier();
            readBarrier.issue();
            reclaimExecutor.execute(new WrappedRunnable()
            {
                public void runMayThrow() throws InterruptedException, ExecutionException
                {
                    readBarrier.await();
                    memtable.setDiscarded();
                }
            });
        }
    }

    /**
     * Finds the largest memtable, as a percentage of *either* on- or off-heap memory limits, and immediately
     * queues it for flushing. If the memtable selected is flushed before this completes, no work is done.
     */
    public static class FlushLargestColumnFamily implements Runnable
    {
        public void run()
        {
            float largestRatio = 0f;
            Memtable largest = null;
            for (ColumnFamilyStore cfs : ColumnFamilyStore.all())
            {
                // we take a reference to the current main memtable for the CF prior to snapping its ownership ratios
                // to ensure we have some ordering guarantee for performing the switchMemtableIf(), i.e. we will only
                // swap if the memtables we are measuring here haven't already been swapped by the time we try to swap them
                Memtable current = cfs.getDataTracker().getView().getCurrentMemtable();

                // find the total ownership ratio for the memtable and all SecondaryIndexes owned by this CF,
                // both on- and off-heap, and select the largest of the two ratios to weight this CF
                float onHeap = 0f, offHeap = 0f;
                onHeap += current.getAllocator().onHeap().ownershipRatio();
                offHeap += current.getAllocator().offHeap().ownershipRatio();

                for (SecondaryIndex index : cfs.indexManager.getIndexes())
                {
                    if (index.getIndexCfs() != null)
                    {
                        MemtableAllocator allocator = index.getIndexCfs().getDataTracker().getView().getCurrentMemtable().getAllocator();
                        onHeap += allocator.onHeap().ownershipRatio();
                        offHeap += allocator.offHeap().ownershipRatio();
                    }
                }

                float ratio = Math.max(onHeap, offHeap);

                if (ratio > largestRatio)
                {
                    largest = current;
                    largestRatio = ratio;
                }
            }

            if (largest != null)
                largest.cfs.switchMemtableIfCurrent(largest);
        }
    }

    public void maybeUpdateRowCache(DecoratedKey key)
    {
        if (!isRowCacheEnabled())
            return;

        RowCacheKey cacheKey = new RowCacheKey(metadata.cfId, key);
        invalidateCachedRow(cacheKey);
    }

    /**
     * Insert/Update the column family for this key.
     * Caller is responsible for acquiring Keyspace.switchLock
     * param @ lock - lock that needs to be used.
     * param @ key - key for update/insert
     * param @ columnFamily - columnFamily changes
     */
    public void apply(DecoratedKey key, ColumnFamily columnFamily, SecondaryIndexManager.Updater indexer, OpOrder.Group opGroup, ReplayPosition replayPosition)
    {
        long start = System.nanoTime();
        Memtable mt = data.getMemtableFor(opGroup, replayPosition);
        final long timeDelta = mt.put(key, columnFamily, indexer, opGroup);
        maybeUpdateRowCache(key);
        metric.samplers.get(Sampler.WRITES).addSample(key.getKey(), key.hashCode(), 1);
        metric.writeLatency.addNano(System.nanoTime() - start);
        if(timeDelta < Long.MAX_VALUE)
            metric.colUpdateTimeDeltaHistogram.update(timeDelta);
    }

    /**
     * Purges gc-able top-level and range tombstones, returning `cf` if there are any columns or tombstones left,
     * null otherwise.
     * @param gcBefore a timestamp (in seconds); tombstones with a localDeletionTime before this will be purged
     */
    public static ColumnFamily removeDeletedCF(ColumnFamily cf, int gcBefore)
    {
        // purge old top-level and range tombstones
        cf.purgeTombstones(gcBefore);

        // if there are no columns or tombstones left, return null
        return !cf.hasColumns() && !cf.isMarkedForDelete() ? null : cf;
    }

    /**
     * Removes deleted columns and purges gc-able tombstones.
     * @return an updated `cf` if any columns or tombstones remain, null otherwise
     */
    public static ColumnFamily removeDeleted(ColumnFamily cf, int gcBefore)
    {
        return removeDeleted(cf, gcBefore, SecondaryIndexManager.nullUpdater);
    }

    /*
     This is complicated because we need to preserve deleted columns and columnfamilies
     until they have been deleted for at least GC_GRACE_IN_SECONDS.  But, we do not need to preserve
     their contents; just the object itself as a "tombstone" that can be used to repair other
     replicas that do not know about the deletion.
     */
    public static ColumnFamily removeDeleted(ColumnFamily cf, int gcBefore, SecondaryIndexManager.Updater indexer)
    {
        if (cf == null)
        {
            return null;
        }

        return removeDeletedCF(removeDeletedColumnsOnly(cf, gcBefore, indexer), gcBefore);
    }

    /**
     * Removes only per-cell tombstones, cells that are shadowed by a row-level or range tombstone, or
     * columns that have been dropped from the schema (for CQL3 tables only).
     * @return the updated ColumnFamily
     */
    public static ColumnFamily removeDeletedColumnsOnly(ColumnFamily cf, int gcBefore, SecondaryIndexManager.Updater indexer)
    {
        BatchRemoveIterator<Cell> iter = cf.batchRemoveIterator();
        DeletionInfo.InOrderTester tester = cf.inOrderDeletionTester();
        boolean hasDroppedColumns = !cf.metadata.getDroppedColumns().isEmpty();
        while (iter.hasNext())
        {
            Cell c = iter.next();
            // remove columns if
            // (a) the column itself is gcable or
            // (b) the column is shadowed by a CF tombstone
            // (c) the column has been dropped from the CF schema (CQL3 tables only)
            if (c.getLocalDeletionTime() < gcBefore || tester.isDeleted(c) || (hasDroppedColumns && isDroppedColumn(c, cf.metadata())))
            {
                iter.remove();
                indexer.remove(c);
            }
        }
        iter.commit();
        return cf;
    }

    // returns true if
    // 1. this column has been dropped from schema and
    // 2. if it has been re-added since then, this particular column was inserted before the last drop
    private static boolean isDroppedColumn(Cell c, CFMetaData meta)
    {
        Long droppedAt = meta.getDroppedColumns().get(c.name().cql3ColumnName(meta));
        return droppedAt != null && c.timestamp() <= droppedAt;
    }

    private void removeDroppedColumns(ColumnFamily cf)
    {
        if (cf == null || cf.metadata.getDroppedColumns().isEmpty())
            return;

        BatchRemoveIterator<Cell> iter = cf.batchRemoveIterator();
        while (iter.hasNext())
            if (isDroppedColumn(iter.next(), metadata))
                iter.remove();
        iter.commit();
    }

    /**
     * @param sstables
     * @return sstables whose key range overlaps with that of the given sstables, not including itself.
     * (The given sstables may or may not overlap with each other.)
     */
    public Collection<SSTableReader> getOverlappingSSTables(Iterable<SSTableReader> sstables)
    {
        logger.debug("Checking for sstables overlapping {}", sstables);

        // a normal compaction won't ever have an empty sstables list, but we create a skeleton
        // compaction controller for streaming, and that passes an empty list.
        if (!sstables.iterator().hasNext())
            return ImmutableSet.of();

        DataTracker.SSTableIntervalTree tree = data.getView().intervalTree;

        Set<SSTableReader> results = null;
        for (SSTableReader sstable : sstables)
        {
            Set<SSTableReader> overlaps = ImmutableSet.copyOf(tree.search(Interval.<RowPosition, SSTableReader>create(sstable.first, sstable.last)));
            results = results == null ? overlaps : Sets.union(results, overlaps).immutableCopy();
        }
        results = Sets.difference(results, ImmutableSet.copyOf(sstables));

        return results;
    }

    /**
     * like getOverlappingSSTables, but acquires references before returning
     */
    public Refs<SSTableReader> getAndReferenceOverlappingSSTables(Iterable<SSTableReader> sstables)
    {
        while (true)
        {
            Iterable<SSTableReader> overlapped = getOverlappingSSTables(sstables);
            Refs<SSTableReader> refs = Refs.tryRef(overlapped);
            if (refs != null)
                return refs;
        }
    }

    /*
     * Called after a BinaryMemtable flushes its in-memory data, or we add a file
     * via bootstrap. This information is cached in the ColumnFamilyStore.
     * This is useful for reads because the ColumnFamilyStore first looks in
     * the in-memory store and the into the disk to find the key. If invoked
     * during recoveryMode the onMemtableFlush() need not be invoked.
     *
     * param @ filename - filename just flushed to disk
     */
    public void addSSTable(SSTableReader sstable)
    {
        assert sstable.getColumnFamilyName().equals(name);
        addSSTables(Arrays.asList(sstable));
    }

    public void addSSTables(Collection<SSTableReader> sstables)
    {
        data.addSSTables(sstables);
        CompactionManager.instance.submitBackground(this);
    }

    /**
     * Calculate expected file size of SSTable after compaction.
     *
     * If operation type is {@code CLEANUP} and we're not dealing with an index sstable,
     * then we calculate expected file size with checking token range to be eliminated.
     *
     * Otherwise, we just add up all the files' size, which is the worst case file
     * size for compaction of all the list of files given.
     *
     * @param sstables SSTables to calculate expected compacted file size
     * @param operation Operation type
     * @return Expected file size of SSTable after compaction
     */
    public long getExpectedCompactedFileSize(Iterable<SSTableReader> sstables, OperationType operation)
    {
        if (operation != OperationType.CLEANUP || isIndex())
        {
            return SSTableReader.getTotalBytes(sstables);
        }

        // cleanup size estimation only counts bytes for keys local to this node
        long expectedFileSize = 0;
        Collection<Range<Token>> ranges = StorageService.instance.getLocalRanges(keyspace.getName());
        for (SSTableReader sstable : sstables)
        {
            List<Pair<Long, Long>> positions = sstable.getPositionsForRanges(ranges);
            for (Pair<Long, Long> position : positions)
                expectedFileSize += position.right - position.left;
        }

        double compressionRatio = getCompressionRatio();
        if (compressionRatio > 0d)
            expectedFileSize *= compressionRatio;

        return expectedFileSize;
    }

    /*
     *  Find the maximum size file in the list .
     */
    public SSTableReader getMaxSizeFile(Iterable<SSTableReader> sstables)
    {
        long maxSize = 0L;
        SSTableReader maxFile = null;
        for (SSTableReader sstable : sstables)
        {
            if (sstable.onDiskLength() > maxSize)
            {
                maxSize = sstable.onDiskLength();
                maxFile = sstable;
            }
        }
        return maxFile;
    }

    public CompactionManager.AllSSTableOpStatus forceCleanup() throws ExecutionException, InterruptedException
    {
        return CompactionManager.instance.performCleanup(ColumnFamilyStore.this);
    }

    public CompactionManager.AllSSTableOpStatus scrub(boolean disableSnapshot, boolean skipCorrupted, boolean checkData) throws ExecutionException, InterruptedException
    {
        // skip snapshot creation during scrub, SEE JIRA 5891
        if(!disableSnapshot)
            snapshotWithoutFlush("pre-scrub-" + System.currentTimeMillis());
        return CompactionManager.instance.performScrub(ColumnFamilyStore.this, skipCorrupted, checkData);
    }

    public CompactionManager.AllSSTableOpStatus sstablesRewrite(boolean excludeCurrentVersion) throws ExecutionException, InterruptedException
    {
        return CompactionManager.instance.performSSTableRewrite(ColumnFamilyStore.this, excludeCurrentVersion);
    }

    public void markObsolete(Collection<SSTableReader> sstables, OperationType compactionType)
    {
        assert !sstables.isEmpty();
        data.markObsolete(sstables, compactionType);
    }

    void replaceFlushed(Memtable memtable, SSTableReader sstable)
    {
        compactionStrategyWrapper.replaceFlushed(memtable, sstable);
    }

    public boolean isValid()
    {
        return valid;
    }

    public long getMemtableColumnsCount()
    {
        return metric.memtableColumnsCount.value();
    }

    public long getMemtableDataSize()
    {
        return metric.memtableOnHeapSize.value();
    }

    public int getMemtableSwitchCount()
    {
        return (int) metric.memtableSwitchCount.count();
    }

    /**
     * Package protected for access from the CompactionManager.
     */
    public DataTracker getDataTracker()
    {
        return data;
    }

    public Collection<SSTableReader> getSSTables()
    {
        return data.getSSTables();
    }

    public Set<SSTableReader> getUncompactingSSTables()
    {
        return data.getUncompactingSSTables();
    }

    public long[] getRecentSSTablesPerReadHistogram()
    {
        return metric.recentSSTablesPerRead.getBuckets(true);
    }

    public long[] getSSTablesPerReadHistogram()
    {
        return metric.sstablesPerRead.getBuckets(false);
    }

    public long getReadCount()
    {
        return metric.readLatency.latency.count();
    }

    public double getRecentReadLatencyMicros()
    {
        return metric.readLatency.getRecentLatency();
    }

    public long[] getLifetimeReadLatencyHistogramMicros()
    {
        return metric.readLatency.totalLatencyHistogram.getBuckets(false);
    }

    public long[] getRecentReadLatencyHistogramMicros()
    {
        return metric.readLatency.recentLatencyHistogram.getBuckets(true);
    }

    public long getTotalReadLatencyMicros()
    {
        return metric.readLatency.totalLatency.count();
    }

    public int getPendingTasks()
    {
        return (int) metric.pendingFlushes.count();
    }

    public long getWriteCount()
    {
        return metric.writeLatency.latency.count();
    }

    public long getTotalWriteLatencyMicros()
    {
        return metric.writeLatency.totalLatency.count();
    }

    public double getRecentWriteLatencyMicros()
    {
        return metric.writeLatency.getRecentLatency();
    }

    public long[] getLifetimeWriteLatencyHistogramMicros()
    {
        return metric.writeLatency.totalLatencyHistogram.getBuckets(false);
    }

    public long[] getRecentWriteLatencyHistogramMicros()
    {
        return metric.writeLatency.recentLatencyHistogram.getBuckets(true);
    }

    public long getRangeCount()
    {
        return metric.rangeLatency.latency.count();
    }

    public double getRecentRangeLatencyMicros()
    {
        return metric.rangeLatency.getRecentLatency();
    }

    public long[] getLifetimeRangeLatencyHistogramMicros()
    {
        return metric.rangeLatency.totalLatencyHistogram.getBuckets(false);
    }

    public long[] getRecentRangeLatencyHistogramMicros()
    {
        return metric.rangeLatency.recentLatencyHistogram.getBuckets(true);
    }

    public long getTotalRangeLatencyMicros()
    {
        return metric.rangeLatency.totalLatency.count();
    }

    public ColumnFamily getColumnFamily(DecoratedKey key,
                                        Composite start,
                                        Composite finish,
                                        boolean reversed,
                                        int limit,
                                        long timestamp)
    {
        return getColumnFamily(QueryFilter.getSliceFilter(key, name, start, finish, reversed, limit, timestamp));
    }

    /**
     * Fetch the row and columns given by filter.key if it is in the cache; if not, read it from disk and cache it
     *
     * If row is cached, and the filter given is within its bounds, we return from cache, otherwise from disk
     *
     * If row is not cached, we figure out what filter is "biggest", read that from disk, then
     * filter the result and either cache that or return it.
     *
     * @param cfId the column family to read the row from
     * @param filter the columns being queried.
     * @return the requested data for the filter provided
     */
    private ColumnFamily getThroughCache(UUID cfId, QueryFilter filter)
    {
        assert isRowCacheEnabled()
               : String.format("Row cache is not enabled on column family [" + name + "]");

        RowCacheKey key = new RowCacheKey(cfId, filter.key);

        // attempt a sentinel-read-cache sequence.  if a write invalidates our sentinel, we'll return our
        // (now potentially obsolete) data, but won't cache it. see CASSANDRA-3862
        // TODO: don't evict entire rows on writes (#2864)
        IRowCacheEntry cached = CacheService.instance.rowCache.get(key);
        if (cached != null)
        {
            if (cached instanceof RowCacheSentinel)
            {
                // Some other read is trying to cache the value, just do a normal non-caching read
                Tracing.trace("Row cache miss (race)");
                metric.rowCacheMiss.inc();
                return getTopLevelColumns(filter, Integer.MIN_VALUE);
            }

            ColumnFamily cachedCf = (ColumnFamily)cached;
            if (isFilterFullyCoveredBy(filter.filter, cachedCf, filter.timestamp))
            {
                metric.rowCacheHit.inc();
                Tracing.trace("Row cache hit");
                return filterColumnFamily(cachedCf, filter);
            }

            metric.rowCacheHitOutOfRange.inc();
            Tracing.trace("Ignoring row cache as cached value could not satisfy query");
            return getTopLevelColumns(filter, Integer.MIN_VALUE);
        }

        metric.rowCacheMiss.inc();
        Tracing.trace("Row cache miss");
        RowCacheSentinel sentinel = new RowCacheSentinel();
        boolean sentinelSuccess = CacheService.instance.rowCache.putIfAbsent(key, sentinel);
        ColumnFamily data = null;
        ColumnFamily toCache = null;
        try
        {
            // If we are explicitely asked to fill the cache with full partitions, we go ahead and query the whole thing
            if (metadata.getCaching().rowCache.cacheFullPartitions())
            {
                data = getTopLevelColumns(QueryFilter.getIdentityFilter(filter.key, name, filter.timestamp), Integer.MIN_VALUE);
                toCache = data;
                Tracing.trace("Populating row cache with the whole partition");
                if (sentinelSuccess && toCache != null)
                    CacheService.instance.rowCache.replace(key, sentinel, toCache);
                return filterColumnFamily(data, filter);
            }

            // Otherwise, if we want to cache the result of the query we're about to do, we must make sure this query
            // covers what needs to be cached. And if the user filter does not satisfy that, we sometimes extend said
            // filter so we can populate the cache but only if:
            //   1) we can guarantee it is a strict extension, i.e. that we will still fetch the data asked by the user.
            //   2) the extension does not make us query more than getRowsPerPartitionToCache() (as a mean to limit the
            //      amount of extra work we'll do on a user query for the purpose of populating the cache).
            //
            // In practice, we can only guarantee those 2 points if the filter is one that queries the head of the
            // partition (and if that filter actually counts CQL3 rows since that's what we cache and it would be
            // bogus to compare the filter count to the 'rows to cache' otherwise).
            if (filter.filter.isHeadFilter() && filter.filter.countCQL3Rows(metadata.comparator))
            {
                SliceQueryFilter sliceFilter = (SliceQueryFilter)filter.filter;
                int rowsToCache = metadata.getCaching().rowCache.rowsToCache;

                SliceQueryFilter cacheSlice = readFilterForCache();
                QueryFilter cacheFilter = new QueryFilter(filter.key, name, cacheSlice, filter.timestamp);

                // If the filter count is less than the number of rows cached, we simply extend it to make sure we do cover the
                // number of rows to cache, and if that count is greater than the number of rows to cache, we simply filter what
                // needs to be cached afterwards.
                if (sliceFilter.count < rowsToCache)
                {
                    toCache = getTopLevelColumns(cacheFilter, Integer.MIN_VALUE);
                    if (toCache != null)
                    {
                        Tracing.trace("Populating row cache ({} rows cached)", cacheSlice.lastCounted());
                        data = filterColumnFamily(toCache, filter);
                    }
                }
                else
                {
                    data = getTopLevelColumns(filter, Integer.MIN_VALUE);
                    if (data != null)
                    {
                        // The filter limit was greater than the number of rows to cache. But, if the filter had a non-empty
                        // finish bound, we may have gotten less than what needs to be cached, in which case we shouldn't cache it
                        // (otherwise a cache hit would assume the whole partition is cached which is not the case).
                        if (sliceFilter.finish().isEmpty() || sliceFilter.lastCounted() >= rowsToCache)
                        {
                            toCache = filterColumnFamily(data, cacheFilter);
                            Tracing.trace("Caching {} rows (out of {} requested)", cacheSlice.lastCounted(), sliceFilter.count);
                        }
                        else
                        {
                            Tracing.trace("Not populating row cache, not enough rows fetched ({} fetched but {} required for the cache)", sliceFilter.lastCounted(), rowsToCache);
                        }
                    }
                }

                if (sentinelSuccess && toCache != null)
                    CacheService.instance.rowCache.replace(key, sentinel, toCache);
                return data;
            }
            else
            {
                Tracing.trace("Fetching data but not populating cache as query does not query from the start of the partition");
                return getTopLevelColumns(filter, Integer.MIN_VALUE);
            }
        }
        finally
        {
            if (sentinelSuccess && toCache == null)
                invalidateCachedRow(key);
        }
    }

    public SliceQueryFilter readFilterForCache()
    {
        // We create a new filter everytime before for now SliceQueryFilter is unfortunatly mutable.
        return new SliceQueryFilter(ColumnSlice.ALL_COLUMNS_ARRAY, false, metadata.getCaching().rowCache.rowsToCache, metadata.clusteringColumns().size());
    }

    public boolean isFilterFullyCoveredBy(IDiskAtomFilter filter, ColumnFamily cachedCf, long now)
    {
        // We can use the cached value only if we know that no data it doesn't contain could be covered
        // by the query filter, that is if:
        //   1) either the whole partition is cached
        //   2) or we can ensure than any data the filter selects are in the cached partition

        // When counting rows to decide if the whole row is cached, we should be careful with expiring
        // columns: if we use a timestamp newer than the one that was used when populating the cache, we might
        // end up deciding the whole partition is cached when it's really not (just some rows expired since the
        // cf was cached). This is the reason for Integer.MIN_VALUE below.
        boolean wholePartitionCached = cachedCf.liveCQL3RowCount(Integer.MIN_VALUE) < metadata.getCaching().rowCache.rowsToCache;

        // Contrarily to the "wholePartitionCached" check above, we do want isFullyCoveredBy to take the
        // timestamp of the query into account when dealing with expired columns. Otherwise, we could think
        // the cached partition has enough live rows to satisfy the filter when it doesn't because some
        // are now expired.
        return wholePartitionCached || filter.isFullyCoveredBy(cachedCf, now);
    }

    public int gcBefore(long now)
    {
        return (int) (now / 1000) - metadata.getGcGraceSeconds();
    }

    /**
     * get a list of columns starting from a given column, in a specified order.
     * only the latest version of a column is returned.
     * @return null if there is no data and no tombstones; otherwise a ColumnFamily
     */
    public ColumnFamily getColumnFamily(QueryFilter filter)
    {
        assert name.equals(filter.getColumnFamilyName()) : filter.getColumnFamilyName();

        ColumnFamily result = null;

        long start = System.nanoTime();
        try
        {
            int gcBefore = gcBefore(filter.timestamp);
            if (isRowCacheEnabled())
            {
                assert !isIndex(); // CASSANDRA-5732
                UUID cfId = metadata.cfId;

                ColumnFamily cached = getThroughCache(cfId, filter);
                if (cached == null)
                {
                    logger.trace("cached row is empty");
                    return null;
                }

                result = cached;
            }
            else
            {
                ColumnFamily cf = getTopLevelColumns(filter, gcBefore);

                if (cf == null)
                    return null;

                result = removeDeletedCF(cf, gcBefore);
            }

            removeDroppedColumns(result);

            if (filter.filter instanceof SliceQueryFilter)
            {
                // Log the number of tombstones scanned on single key queries
                metric.tombstoneScannedHistogram.update(((SliceQueryFilter) filter.filter).lastTombstones());
                metric.liveScannedHistogram.update(((SliceQueryFilter) filter.filter).lastLive());
            }
        }
        finally
        {
            metric.readLatency.addNano(System.nanoTime() - start);
        }

        return result;
    }

    /**
     *  Filter a cached row, which will not be modified by the filter, but may be modified by throwing out
     *  tombstones that are no longer relevant.
     *  The returned column family won't be thread safe.
     */
    ColumnFamily filterColumnFamily(ColumnFamily cached, QueryFilter filter)
    {
        if (cached == null)
            return null;

        ColumnFamily cf = cached.cloneMeShallow(ArrayBackedSortedColumns.factory, filter.filter.isReversed());
        int gcBefore = gcBefore(filter.timestamp);
        filter.collateOnDiskAtom(cf, filter.getIterator(cached), gcBefore);
        return removeDeletedCF(cf, gcBefore);
    }

    public Set<SSTableReader> getUnrepairedSSTables()
    {
        Set<SSTableReader> unRepairedSSTables = new HashSet<>(getSSTables());
        Iterator<SSTableReader> sstableIterator = unRepairedSSTables.iterator();
        while(sstableIterator.hasNext())
        {
            SSTableReader sstable = sstableIterator.next();
            if (sstable.isRepaired())
                sstableIterator.remove();
        }
        return unRepairedSSTables;
    }

    public Set<SSTableReader> getRepairedSSTables()
    {
        Set<SSTableReader> repairedSSTables = new HashSet<>(getSSTables());
        Iterator<SSTableReader> sstableIterator = repairedSSTables.iterator();
        while(sstableIterator.hasNext())
        {
            SSTableReader sstable = sstableIterator.next();
            if (!sstable.isRepaired())
                sstableIterator.remove();
        }
        return repairedSSTables;
    }

    public RefViewFragment selectAndReference(Function<DataTracker.View, List<SSTableReader>> filter)
    {
        long failingSince = -1L;
        while (true)
        {
            ViewFragment view = select(filter);
            Refs<SSTableReader> refs = Refs.tryRef(view.sstables);
            if (refs != null)
                return new RefViewFragment(view.sstables, view.memtables, refs);
            if (failingSince <= 0)
            {
                failingSince = System.nanoTime();
            }
            else if (TimeUnit.MILLISECONDS.toNanos(100) > System.nanoTime() - failingSince)
            {
                List<SSTableReader> released = new ArrayList<>();
                for (SSTableReader reader : view.sstables)
                    if (reader.selfRef().globalCount() == 0)
                        released.add(reader);
                logger.info("Spinning trying to capture released readers {}", released);
                logger.info("Spinning trying to capture all readers {}", view.sstables);
                failingSince = System.nanoTime();
            }
        }
    }

    public ViewFragment select(Function<DataTracker.View, List<SSTableReader>> filter)
    {
        DataTracker.View view = data.getView();
        List<SSTableReader> sstables = view.intervalTree.isEmpty()
                                       ? Collections.<SSTableReader>emptyList()
                                       : filter.apply(view);
        return new ViewFragment(sstables, view.getAllMemtables());
    }


    /**
     * @return a ViewFragment containing the sstables and memtables that may need to be merged
     * for the given @param key, according to the interval tree
     */
    public Function<DataTracker.View, List<SSTableReader>> viewFilter(final DecoratedKey key)
    {
        assert !key.isMinimum(partitioner);
        return new Function<DataTracker.View, List<SSTableReader>>()
        {
            public List<SSTableReader> apply(DataTracker.View view)
            {
                return compactionStrategyWrapper.filterSSTablesForReads(view.intervalTree.search(key));
            }
        };
    }

    /**
     * @return a ViewFragment containing the sstables and memtables that may need to be merged
     * for rows within @param rowBounds, inclusive, according to the interval tree.
     */
    public Function<DataTracker.View, List<SSTableReader>> viewFilter(final AbstractBounds<RowPosition> rowBounds)
    {
        return new Function<DataTracker.View, List<SSTableReader>>()
        {
            public List<SSTableReader> apply(DataTracker.View view)
            {
                return compactionStrategyWrapper.filterSSTablesForReads(view.sstablesInBounds(rowBounds));
            }
        };
    }

    public List<String> getSSTablesForKey(String key)
    {
        DecoratedKey dk = partitioner.decorateKey(metadata.getKeyValidator().fromString(key));
        try (OpOrder.Group op = readOrdering.start())
        {
            List<String> files = new ArrayList<>();
            for (SSTableReader sstr : select(viewFilter(dk)).sstables)
            {
                // check if the key actually exists in this sstable, without updating cache and stats
                if (sstr.getPosition(dk, SSTableReader.Operator.EQ, false) != null)
                    files.add(sstr.getFilename());
            }
            return files;
        }
    }

    public ColumnFamily getTopLevelColumns(QueryFilter filter, int gcBefore)
    {
        Tracing.trace("Executing single-partition query on {}", name);
        CollationController controller = new CollationController(this, filter, gcBefore);
        ColumnFamily columns;
        try (OpOrder.Group op = readOrdering.start())
        {
            columns = controller.getTopLevelColumns(Memtable.MEMORY_POOL.needToCopyOnHeap());
        }
        if (columns != null)
            metric.samplers.get(Sampler.READS).addSample(filter.key.getKey(), filter.key.hashCode(), 1);
        metric.updateSSTableIterated(controller.getSstablesIterated());
        return columns;
    }

    public void beginLocalSampling(String sampler, int capacity)
    {
        metric.samplers.get(Sampler.valueOf(sampler)).beginSampling(capacity);
    }

    public CompositeData finishLocalSampling(String sampler, int count) throws OpenDataException
    {
        SamplerResult<ByteBuffer> samplerResults = metric.samplers.get(Sampler.valueOf(sampler))
                .finishSampling(count);
        TabularDataSupport result = new TabularDataSupport(COUNTER_TYPE);
        for (Counter<ByteBuffer> counter : samplerResults.topK)
        {
            byte[] key = counter.getItem().array();
            result.put(new CompositeDataSupport(COUNTER_COMPOSITE_TYPE, COUNTER_NAMES, new Object[] {
                    Hex.bytesToHex(key), // raw
                    counter.getCount(),  // count
                    counter.getError(),  // error
                    metadata.getKeyValidator().getString(ByteBuffer.wrap(key)) })); // string
        }
        return new CompositeDataSupport(SAMPLING_RESULT, SAMPLER_NAMES, new Object[]{
                samplerResults.cardinality, result});
    }

    public void cleanupCache()
    {
        Collection<Range<Token>> ranges = StorageService.instance.getLocalRanges(keyspace.getName());

        for (RowCacheKey key : CacheService.instance.rowCache.getKeySet())
        {
            DecoratedKey dk = partitioner.decorateKey(ByteBuffer.wrap(key.key));
            if (key.cfId == metadata.cfId && !Range.isInRanges(dk.getToken(), ranges))
                invalidateCachedRow(dk);
        }

        if (metadata.isCounter())
        {
            for (CounterCacheKey key : CacheService.instance.counterCache.getKeySet())
            {
                DecoratedKey dk = partitioner.decorateKey(ByteBuffer.wrap(key.partitionKey));
                if (key.cfId == metadata.cfId && !Range.isInRanges(dk.getToken(), ranges))
                    CacheService.instance.counterCache.remove(key);
            }
        }
    }

    public static abstract class AbstractScanIterator extends AbstractIterator<Row> implements CloseableIterator<Row>
    {
        public boolean needsFiltering()
        {
            return true;
        }
    }

    /**
      * Iterate over a range of rows and columns from memtables/sstables.
      *
      * @param range The range of keys and columns within those keys to fetch
     */
    private AbstractScanIterator getSequentialIterator(final DataRange range, long now)
    {
        assert !(range.keyRange() instanceof Range) || !((Range)range.keyRange()).isWrapAround() || range.keyRange().right.isMinimum(partitioner) : range.keyRange();

        final ViewFragment view = select(viewFilter(range.keyRange()));
        Tracing.trace("Executing seq scan across {} sstables for {}", view.sstables.size(), range.keyRange().getString(metadata.getKeyValidator()));

        final CloseableIterator<Row> iterator = RowIteratorFactory.getIterator(view.memtables, view.sstables, range, this, now);

        // todo this could be pushed into SSTableScanner
        return new AbstractScanIterator()
        {
            protected Row computeNext()
            {
                // pull a row out of the iterator
                if (!iterator.hasNext())
                    return endOfData();

                Row current = iterator.next();
                DecoratedKey key = current.key;

                if (!range.stopKey().isMinimum(partitioner) && range.stopKey().compareTo(key) < 0)
                    return endOfData();

                // skipping outside of assigned range
                if (!range.contains(key))
                    return computeNext();

                if (logger.isTraceEnabled())
                    logger.trace("scanned {}", metadata.getKeyValidator().getString(key.getKey()));

                return current;
            }

            public void close() throws IOException
            {
                iterator.close();
            }
        };
    }

    @VisibleForTesting
    public List<Row> getRangeSlice(final AbstractBounds<RowPosition> range,
                                   List<IndexExpression> rowFilter,
                                   IDiskAtomFilter columnFilter,
                                   int maxResults)
    {
        return getRangeSlice(range, rowFilter, columnFilter, maxResults, System.currentTimeMillis());
    }

    public List<Row> getRangeSlice(final AbstractBounds<RowPosition> range,
                                   List<IndexExpression> rowFilter,
                                   IDiskAtomFilter columnFilter,
                                   int maxResults,
                                   long now)
    {
        return getRangeSlice(makeExtendedFilter(range, columnFilter, rowFilter, maxResults, false, false, now));
    }

    /**
     * Allows generic range paging with the slice column filter.
     * Typically, suppose we have rows A, B, C ... Z having each some columns in [1, 100].
     * And suppose we want to page through the query that for all rows returns the columns
     * within [25, 75]. For that, we need to be able to do a range slice starting at (row r, column c)
     * and ending at (row Z, column 75), *but* that only return columns in [25, 75].
     * That is what this method allows. The columnRange is the "window" of  columns we are interested
     * in each row, and columnStart (resp. columnEnd) is the start (resp. end) for the first
     * (resp. last) requested row.
     */
    public ExtendedFilter makeExtendedFilter(AbstractBounds<RowPosition> keyRange,
                                             SliceQueryFilter columnRange,
                                             Composite columnStart,
                                             Composite columnStop,
                                             List<IndexExpression> rowFilter,
                                             int maxResults,
                                             boolean countCQL3Rows,
                                             long now)
    {
        DataRange dataRange = new DataRange.Paging(keyRange, columnRange, columnStart, columnStop, metadata);
        return ExtendedFilter.create(this, dataRange, rowFilter, maxResults, countCQL3Rows, now);
    }

    public List<Row> getRangeSlice(AbstractBounds<RowPosition> range,
                                   List<IndexExpression> rowFilter,
                                   IDiskAtomFilter columnFilter,
                                   int maxResults,
                                   long now,
                                   boolean countCQL3Rows,
                                   boolean isPaging)
    {
        return getRangeSlice(makeExtendedFilter(range, columnFilter, rowFilter, maxResults, countCQL3Rows, isPaging, now));
    }

    public ExtendedFilter makeExtendedFilter(AbstractBounds<RowPosition> range,
                                             IDiskAtomFilter columnFilter,
                                             List<IndexExpression> rowFilter,
                                             int maxResults,
                                             boolean countCQL3Rows,
                                             boolean isPaging,
                                             long timestamp)
    {
        DataRange dataRange;
        if (isPaging)
        {
            assert columnFilter instanceof SliceQueryFilter;
            SliceQueryFilter sfilter = (SliceQueryFilter)columnFilter;
            assert sfilter.slices.length == 1;
            // create a new SliceQueryFilter that selects all cells, but pass the original slice start and finish
            // through to DataRange.Paging to be used on the first and last partitions
            SliceQueryFilter newFilter = new SliceQueryFilter(ColumnSlice.ALL_COLUMNS_ARRAY, sfilter.isReversed(), sfilter.count);
            dataRange = new DataRange.Paging(range, newFilter, sfilter.start(), sfilter.finish(), metadata);
        }
        else
        {
            dataRange = new DataRange(range, columnFilter);
        }
        return ExtendedFilter.create(this, dataRange, rowFilter, maxResults, countCQL3Rows, timestamp);
    }

    public List<Row> getRangeSlice(ExtendedFilter filter)
    {
        long start = System.nanoTime();
        try (OpOrder.Group op = readOrdering.start())
        {
            return filter(getSequentialIterator(filter.dataRange, filter.timestamp), filter);
        }
        finally
        {
            metric.rangeLatency.addNano(System.nanoTime() - start);
        }
    }

    @VisibleForTesting
    public List<Row> search(AbstractBounds<RowPosition> range,
                            List<IndexExpression> clause,
                            IDiskAtomFilter dataFilter,
                            int maxResults)
    {
        return search(range, clause, dataFilter, maxResults, System.currentTimeMillis());
    }

    public List<Row> search(AbstractBounds<RowPosition> range,
                            List<IndexExpression> clause,
                            IDiskAtomFilter dataFilter,
                            int maxResults,
                            long now)
    {
        return search(makeExtendedFilter(range, dataFilter, clause, maxResults, false, false, now));
    }

    public List<Row> search(ExtendedFilter filter)
    {
        Tracing.trace("Executing indexed scan for {}", filter.dataRange.keyRange().getString(metadata.getKeyValidator()));
        return indexManager.search(filter);
    }

    public List<Row> filter(AbstractScanIterator rowIterator, ExtendedFilter filter)
    {
        logger.trace("Filtering {} for rows matching {}", rowIterator, filter);
        List<Row> rows = new ArrayList<Row>();
        int columnsCount = 0;
        int total = 0, matched = 0;
        boolean ignoreTombstonedPartitions = filter.ignoreTombstonedPartitions();

        try
        {
            while (rowIterator.hasNext() && matched < filter.maxRows() && columnsCount < filter.maxColumns())
            {
                // get the raw columns requested, and additional columns for the expressions if necessary
                Row rawRow = rowIterator.next();
                total++;
                ColumnFamily data = rawRow.cf;

                if (rowIterator.needsFiltering())
                {
                    IDiskAtomFilter extraFilter = filter.getExtraFilter(rawRow.key, data);
                    if (extraFilter != null)
                    {
                        ColumnFamily cf = filter.cfs.getColumnFamily(new QueryFilter(rawRow.key, name, extraFilter, filter.timestamp));
                        if (cf != null)
                            data.addAll(cf);
                    }

                    removeDroppedColumns(data);

                    if (!filter.isSatisfiedBy(rawRow.key, data, null, null))
                        continue;

                    logger.trace("{} satisfies all filter expressions", data);
                    // cut the resultset back to what was requested, if necessary
                    data = filter.prune(rawRow.key, data);
                }
                else
                {
                    removeDroppedColumns(data);
                }

                rows.add(new Row(rawRow.key, data));
                if (!ignoreTombstonedPartitions || !data.hasOnlyTombstones(filter.timestamp))
                    matched++;

                if (data != null)
                    columnsCount += filter.lastCounted(data);
                // Update the underlying filter to avoid querying more columns per slice than necessary and to handle paging
                filter.updateFilter(columnsCount);
            }

            return rows;
        }
        finally
        {
            try
            {
                rowIterator.close();
                Tracing.trace("Scanned {} rows and matched {}", total, matched);
            }
            catch (IOException e)
            {
                throw new RuntimeException(e);
            }
        }
    }

    public CellNameType getComparator()
    {
        return metadata.comparator;
    }

    public void snapshotWithoutFlush(String snapshotName)
    {
        snapshotWithoutFlush(snapshotName, null);
    }

    public void snapshotWithoutFlush(String snapshotName, Predicate<SSTableReader> predicate)
    {
        for (ColumnFamilyStore cfs : concatWithIndexes())
        {
            final JSONArray filesJSONArr = new JSONArray();
            try (RefViewFragment currentView = cfs.selectAndReference(CANONICAL_SSTABLES))
            {
                for (SSTableReader ssTable : currentView.sstables)
                {
                    if (predicate != null && !predicate.apply(ssTable))
                        continue;

                    File snapshotDirectory = Directories.getSnapshotDirectory(ssTable.descriptor, snapshotName);
                    ssTable.createLinks(snapshotDirectory.getPath()); // hard links
                    filesJSONArr.add(ssTable.descriptor.relativeFilenameFor(Component.DATA));
                    if (logger.isDebugEnabled())
                        logger.debug("Snapshot for {} keyspace data file {} created in {}", keyspace, ssTable.getFilename(), snapshotDirectory);
                }

                writeSnapshotManifest(filesJSONArr, snapshotName);
            }
        }
    }

    private void writeSnapshotManifest(final JSONArray filesJSONArr, final String snapshotName)
    {
        final File manifestFile = directories.getSnapshotManifestFile(snapshotName);
        final JSONObject manifestJSON = new JSONObject();
        manifestJSON.put("files", filesJSONArr);

        try
        {
            if (!manifestFile.getParentFile().exists())
                manifestFile.getParentFile().mkdirs();
            PrintStream out = new PrintStream(manifestFile);
            out.println(manifestJSON.toJSONString());
            out.close();
        }
        catch (IOException e)
        {
            throw new FSWriteError(e, manifestFile);
        }
    }

    public Refs<SSTableReader> getSnapshotSSTableReader(String tag) throws IOException
    {
        Map<Integer, SSTableReader> active = new HashMap<>();
        for (SSTableReader sstable : data.getView().sstables)
            active.put(sstable.descriptor.generation, sstable);
        Map<Descriptor, Set<Component>> snapshots = directories.sstableLister().snapshots(tag).list();
        Refs<SSTableReader> refs = new Refs<>();
        try
        {
            for (Map.Entry<Descriptor, Set<Component>> entries : snapshots.entrySet())
            {
                // Try acquire reference to an active sstable instead of snapshot if it exists,
                // to avoid opening new sstables. If it fails, use the snapshot reference instead.
                SSTableReader sstable = active.get(entries.getKey().generation);
                if (sstable == null || !refs.tryRef(sstable))
                {
                    if (logger.isDebugEnabled())
                        logger.debug("using snapshot sstable {}", entries.getKey());
                    sstable = SSTableReader.open(entries.getKey(), entries.getValue(), metadata, partitioner);
                    // This is technically not necessary since it's a snapshot but makes things easier
                    refs.tryRef(sstable);
                }
                else if (logger.isDebugEnabled())
                {
                    logger.debug("using active sstable {}", entries.getKey());
                }
            }
        }
        catch (IOException | RuntimeException e)
        {
            // In case one of the snapshot sstables fails to open,
            // we must release the references to the ones we opened so far
            refs.release();
            throw e;
        }
        return refs;
    }

    /**
     * Take a snap shot of this columnfamily store.
     *
     * @param snapshotName the name of the associated with the snapshot
     */
    public void snapshot(String snapshotName)
    {
        snapshot(snapshotName, null);
    }

    public void snapshot(String snapshotName, Predicate<SSTableReader> predicate)
    {
        forceBlockingFlush();
        snapshotWithoutFlush(snapshotName, predicate);
    }

    public boolean snapshotExists(String snapshotName)
    {
        return directories.snapshotExists(snapshotName);
    }

    public long getSnapshotCreationTime(String snapshotName)
    {
        return directories.snapshotCreationTime(snapshotName);
    }

    /**
     * Clear all the snapshots for a given column family.
     *
     * @param snapshotName the user supplied snapshot name. If left empty,
     *                     all the snapshots will be cleaned.
     */
    public void clearSnapshot(String snapshotName)
    {
        List<File> snapshotDirs = directories.getCFDirectories();
        Directories.clearSnapshot(snapshotName, snapshotDirs);
    }
    /**
     *
     * @return  Return a map of all snapshots to space being used
     * The pair for a snapshot has true size and size on disk.
     */
    public Map<String, Pair<Long,Long>> getSnapshotDetails()
    {
        return directories.getSnapshotDetails();
    }

    public long getTotalDiskSpaceUsed()
    {
        return metric.totalDiskSpaceUsed.count();
    }

    public long getLiveDiskSpaceUsed()
    {
        return metric.liveDiskSpaceUsed.count();
    }

    public int getLiveSSTableCount()
    {
        return metric.liveSSTableCount.value();
    }

    /**
     * @return the cached row for @param key if it is already present in the cache.
     * That is, unlike getThroughCache, it will not readAndCache the row if it is not present, nor
     * are these calls counted in cache statistics.
     *
     * Note that this WILL cause deserialization of a SerializingCache row, so if all you
     * need to know is whether a row is present or not, use containsCachedRow instead.
     */
    public ColumnFamily getRawCachedRow(DecoratedKey key)
    {
        if (!isRowCacheEnabled())
            return null;

        IRowCacheEntry cached = CacheService.instance.rowCache.getInternal(new RowCacheKey(metadata.cfId, key));
        return cached == null || cached instanceof RowCacheSentinel ? null : (ColumnFamily)cached;
    }

    private void invalidateCaches()
    {
        CacheService.instance.invalidateKeyCacheForCf(metadata.cfId);
        CacheService.instance.invalidateRowCacheForCf(metadata.cfId);
        if (metadata.isCounter())
            CacheService.instance.invalidateCounterCacheForCf(metadata.cfId);
    }

    /**
     * @return true if @param key is contained in the row cache
     */
    public boolean containsCachedRow(DecoratedKey key)
    {
        return CacheService.instance.rowCache.getCapacity() != 0 && CacheService.instance.rowCache.containsKey(new RowCacheKey(metadata.cfId, key));
    }

    public void invalidateCachedRow(RowCacheKey key)
    {
        CacheService.instance.rowCache.remove(key);
    }

    public void invalidateCachedRow(DecoratedKey key)
    {
        UUID cfId = Schema.instance.getId(keyspace.getName(), this.name);
        if (cfId == null)
            return; // secondary index

        invalidateCachedRow(new RowCacheKey(cfId, key));
    }

    public ClockAndCount getCachedCounter(ByteBuffer partitionKey, CellName cellName)
    {
        if (CacheService.instance.counterCache.getCapacity() == 0L) // counter cache disabled.
            return null;
        return CacheService.instance.counterCache.get(CounterCacheKey.create(metadata.cfId, partitionKey, cellName));
    }

    public void putCachedCounter(ByteBuffer partitionKey, CellName cellName, ClockAndCount clockAndCount)
    {
        if (CacheService.instance.counterCache.getCapacity() == 0L) // counter cache disabled.
            return;
        CacheService.instance.counterCache.put(CounterCacheKey.create(metadata.cfId, partitionKey, cellName), clockAndCount);
    }

    public void forceMajorCompaction() throws InterruptedException, ExecutionException
    {
        CompactionManager.instance.performMaximal(this);
    }

    public static Iterable<ColumnFamilyStore> all()
    {
        List<Iterable<ColumnFamilyStore>> stores = new ArrayList<Iterable<ColumnFamilyStore>>(Schema.instance.getKeyspaces().size());
        for (Keyspace keyspace : Keyspace.all())
        {
            stores.add(keyspace.getColumnFamilyStores());
        }
        return Iterables.concat(stores);
    }

    public Iterable<DecoratedKey> keySamples(Range<Token> range)
    {
        try (RefViewFragment view = selectAndReference(CANONICAL_SSTABLES))
        {
            Iterable<DecoratedKey>[] samples = new Iterable[view.sstables.size()];
            int i = 0;
            for (SSTableReader sstable: view.sstables)
            {
                samples[i++] = sstable.getKeySamples(range);
            }
            return Iterables.concat(samples);
        }
    }

    public long estimatedKeysForRange(Range<Token> range)
    {
        try (RefViewFragment view = selectAndReference(CANONICAL_SSTABLES))
        {
            long count = 0;
            for (SSTableReader sstable : view.sstables)
                count += sstable.estimatedKeysForRanges(Collections.singleton(range));
            return count;
        }
    }

    /**
     * For testing.  No effort is made to clear historical or even the current memtables, nor for
     * thread safety.  All we do is wipe the sstable containers clean, while leaving the actual
     * data files present on disk.  (This allows tests to easily call loadNewSSTables on them.)
     */
    public void clearUnsafe()
    {
        for (final ColumnFamilyStore cfs : concatWithIndexes())
        {
            cfs.runWithCompactionsDisabled(new Callable<Void>()
            {
                public Void call()
                {
                    cfs.data.init();
                    return null;
                }
            }, true);
        }
    }

    /**
     * Truncate deletes the entire column family's data with no expensive tombstone creation
     */
    public void truncateBlocking()
    {
        // We have two goals here:
        // - truncate should delete everything written before truncate was invoked
        // - but not delete anything that isn't part of the snapshot we create.
        // We accomplish this by first flushing manually, then snapshotting, and
        // recording the timestamp IN BETWEEN those actions. Any sstables created
        // with this timestamp or greater time, will not be marked for delete.
        //
        // Bonus complication: since we store replay position in sstable metadata,
        // truncating those sstables means we will replay any CL segments from the
        // beginning if we restart before they [the CL segments] are discarded for
        // normal reasons post-truncate.  To prevent this, we store truncation
        // position in the System keyspace.
        logger.debug("truncating {}", name);

        if (keyspace.metadata.durableWrites || DatabaseDescriptor.isAutoSnapshot())
        {
            // flush the CF being truncated before forcing the new segment
            forceBlockingFlush();

            // sleep a little to make sure that our truncatedAt comes after any sstable
            // that was part of the flushed we forced; otherwise on a tie, it won't get deleted.
            Uninterruptibles.sleepUninterruptibly(1, TimeUnit.MILLISECONDS);
        }
        else
        {
            // just nuke the memtable data w/o writing to disk first
            synchronized (data)
            {
                final Flush flush = new Flush(true);
                flushExecutor.execute(flush);
                postFlushExecutor.submit(flush.postFlush);
            }
        }

        Runnable truncateRunnable = new Runnable()
        {
            public void run()
            {
                logger.debug("Discarding sstable data for truncated CF + indexes");

                final long truncatedAt = System.currentTimeMillis();
                data.notifyTruncated(truncatedAt);

                if (DatabaseDescriptor.isAutoSnapshot())
                    snapshot(Keyspace.getTimestampedSnapshotName(name));

                ReplayPosition replayAfter = discardSSTables(truncatedAt);

                for (SecondaryIndex index : indexManager.getIndexes())
                    index.truncateBlocking(truncatedAt);

                SystemKeyspace.saveTruncationRecord(ColumnFamilyStore.this, truncatedAt, replayAfter);
                logger.debug("cleaning out row cache");
                invalidateCaches();
            }
        };

        runWithCompactionsDisabled(Executors.callable(truncateRunnable), true);
        logger.debug("truncate complete");
    }

    public <V> V runWithCompactionsDisabled(Callable<V> callable, boolean interruptValidation)
    {
        // synchronize so that concurrent invocations don't re-enable compactions partway through unexpectedly,
        // and so we only run one major compaction at a time
        synchronized (this)
        {
            logger.debug("Cancelling in-progress compactions for {}", metadata.cfName);

            Iterable<ColumnFamilyStore> selfWithIndexes = concatWithIndexes();
            for (ColumnFamilyStore cfs : selfWithIndexes)
                cfs.getCompactionStrategy().pause();
            try
            {
                // interrupt in-progress compactions
                CompactionManager.instance.interruptCompactionForCFs(selfWithIndexes, interruptValidation);
                CompactionManager.instance.waitForCessation(selfWithIndexes);

                // doublecheck that we finished, instead of timing out
                for (ColumnFamilyStore cfs : selfWithIndexes)
                {
                    if (!cfs.getDataTracker().getCompacting().isEmpty())
                    {
                        logger.warn("Unable to cancel in-progress compactions for {}.  Perhaps there is an unusually large row in progress somewhere, or the system is simply overloaded.", metadata.cfName);
                        return null;
                    }
                }
                logger.debug("Compactions successfully cancelled");

                // run our task
                try
                {
                    return callable.call();
                }
                catch (Exception e)
                {
                    throw new RuntimeException(e);
                }
            }
            finally
            {
                for (ColumnFamilyStore cfs : selfWithIndexes)
                    cfs.getCompactionStrategy().resume();
            }
        }
    }

    public Iterable<SSTableReader> markAllCompacting()
    {
        Callable<Iterable<SSTableReader>> callable = new Callable<Iterable<SSTableReader>>()
        {
            public Iterable<SSTableReader> call() throws Exception
            {
                assert data.getCompacting().isEmpty() : data.getCompacting();
                Collection<SSTableReader> sstables = Lists.newArrayList(AbstractCompactionStrategy.filterSuspectSSTables(getSSTables()));
                if (Iterables.isEmpty(sstables))
                    return Collections.emptyList();
                boolean success = data.markCompacting(sstables);
                assert success : "something marked things compacting while compactions are disabled";
                return sstables;
            }
        };

        return runWithCompactionsDisabled(callable, false);
    }

    public long getBloomFilterFalsePositives()
    {
        return metric.bloomFilterFalsePositives.value();
    }

    public long getRecentBloomFilterFalsePositives()
    {
        return metric.recentBloomFilterFalsePositives.value();
    }

    public double getBloomFilterFalseRatio()
    {
        return metric.bloomFilterFalseRatio.value();
    }

    public double getRecentBloomFilterFalseRatio()
    {
        return metric.recentBloomFilterFalseRatio.value();
    }

    public long getBloomFilterDiskSpaceUsed()
    {
        return metric.bloomFilterDiskSpaceUsed.value();
    }

    public long getBloomFilterOffHeapMemoryUsed()
    {
        return metric.bloomFilterOffHeapMemoryUsed.value();
    }

    public long getIndexSummaryOffHeapMemoryUsed()
    {
        return metric.indexSummaryOffHeapMemoryUsed.value();
    }

    public long getCompressionMetadataOffHeapMemoryUsed()
    {
        return metric.compressionMetadataOffHeapMemoryUsed.value();
    }

    @Override
    public String toString()
    {
        return "CFS(" +
               "Keyspace='" + keyspace.getName() + '\'' +
               ", ColumnFamily='" + name + '\'' +
               ')';
    }

    public void disableAutoCompaction()
    {
        // we don't use CompactionStrategy.pause since we don't want users flipping that on and off
        // during runWithCompactionsDisabled
        this.compactionStrategyWrapper.disable();
    }

    public void enableAutoCompaction()
    {
        enableAutoCompaction(false);
    }

    /**
     * used for tests - to be able to check things after a minor compaction
     * @param waitForFutures if we should block until autocompaction is done
     */
    @VisibleForTesting
    public void enableAutoCompaction(boolean waitForFutures)
    {
        this.compactionStrategyWrapper.enable();
        List<Future<?>> futures = CompactionManager.instance.submitBackground(this);
        if (waitForFutures)
            FBUtilities.waitOnFutures(futures);
    }

    public boolean isAutoCompactionDisabled()
    {
        return !this.compactionStrategyWrapper.isEnabled();
    }

    /*
     JMX getters and setters for the Default<T>s.
       - get/set minCompactionThreshold
       - get/set maxCompactionThreshold
       - get     memsize
       - get     memops
       - get/set memtime
     */

    public AbstractCompactionStrategy getCompactionStrategy()
    {
        return compactionStrategyWrapper;
    }

    public void setCompactionThresholds(int minThreshold, int maxThreshold)
    {
        validateCompactionThresholds(minThreshold, maxThreshold);

        minCompactionThreshold.set(minThreshold);
        maxCompactionThreshold.set(maxThreshold);
        CompactionManager.instance.submitBackground(this);
    }

    public int getMinimumCompactionThreshold()
    {
        return minCompactionThreshold.value();
    }

    public void setMinimumCompactionThreshold(int minCompactionThreshold)
    {
        validateCompactionThresholds(minCompactionThreshold, maxCompactionThreshold.value());
        this.minCompactionThreshold.set(minCompactionThreshold);
    }

    public int getMaximumCompactionThreshold()
    {
        return maxCompactionThreshold.value();
    }

    public void setMaximumCompactionThreshold(int maxCompactionThreshold)
    {
        validateCompactionThresholds(minCompactionThreshold.value(), maxCompactionThreshold);
        this.maxCompactionThreshold.set(maxCompactionThreshold);
    }

    private void validateCompactionThresholds(int minThreshold, int maxThreshold)
    {
        if (minThreshold > maxThreshold)
            throw new RuntimeException(String.format("The min_compaction_threshold cannot be larger than the max_compaction_threshold. " +
                                                     "Min is '%d', Max is '%d'.", minThreshold, maxThreshold));

        if (maxThreshold == 0 || minThreshold == 0)
            throw new RuntimeException("Disabling compaction by setting min_compaction_threshold or max_compaction_threshold to 0 " +
                    "is deprecated, set the compaction strategy option 'enabled' to 'false' instead or use the nodetool command 'disableautocompaction'.");
    }

    public double getTombstonesPerSlice()
    {
        return metric.tombstoneScannedHistogram.cf.getSnapshot().getMedian();
    }

    public double getLiveCellsPerSlice()
    {
        return metric.liveScannedHistogram.cf.getSnapshot().getMedian();
    }

    // End JMX get/set.

    public long estimateKeys()
    {
        return data.estimatedKeys();
    }

    public long[] getEstimatedRowSizeHistogram()
    {
        return metric.estimatedRowSizeHistogram.value();
    }

    public long[] getEstimatedColumnCountHistogram()
    {
        return metric.estimatedColumnCountHistogram.value();
    }

    public double getCompressionRatio()
    {
        return metric.compressionRatio.value();
    }

    /** true if this CFS contains secondary index data */
    public boolean isIndex()
    {
        return partitioner instanceof LocalPartitioner;
    }

    public Iterable<ColumnFamilyStore> concatWithIndexes()
    {
        // we return the main CFS first, which we rely on for simplicity in switchMemtable(), for getting the
        // latest replay position
        return Iterables.concat(Collections.singleton(this), indexManager.getIndexesBackedByCfs());
    }

    public List<String> getBuiltIndexes()
    {
       return indexManager.getBuiltIndexes();
    }

    public int getUnleveledSSTables()
    {
        return this.compactionStrategyWrapper.getUnleveledSSTables();
    }

    public int[] getSSTableCountPerLevel()
    {
        return compactionStrategyWrapper.getSSTableCountPerLevel();
    }

    public static class ViewFragment
    {
        public final List<SSTableReader> sstables;
        public final Iterable<Memtable> memtables;

        public ViewFragment(List<SSTableReader> sstables, Iterable<Memtable> memtables)
        {
            this.sstables = sstables;
            this.memtables = memtables;
        }
    }

    public static class RefViewFragment extends ViewFragment implements AutoCloseable
    {
        public final Refs<SSTableReader> refs;

        public RefViewFragment(List<SSTableReader> sstables, Iterable<Memtable> memtables, Refs<SSTableReader> refs)
        {
            super(sstables, memtables);
            this.refs = refs;
        }

        public void release()
        {
            refs.release();
        }

        public void close()
        {
            refs.release();
        }
    }

    /**
     * Returns the creation time of the oldest memtable not fully flushed yet.
     */
    public long oldestUnflushedMemtable()
    {
        return data.getView().getOldestMemtable().creationTime();
    }

    public boolean isEmpty()
    {
        DataTracker.View view = data.getView();
        return view.sstables.isEmpty() && view.getCurrentMemtable().getOperations() == 0 && view.getCurrentMemtable() == view.getOldestMemtable();
    }

    private boolean isRowCacheEnabled()
    {
        return metadata.getCaching().rowCache.isEnabled() && CacheService.instance.rowCache.getCapacity() > 0;
    }

    /**
     * Discard all SSTables that were created before given timestamp.
     *
     * Caller should first ensure that comapctions have quiesced.
     *
     * @param truncatedAt The timestamp of the truncation
     *                    (all SSTables before that timestamp are going be marked as compacted)
     *
     * @return the most recent replay position of the truncated data
     */
    public ReplayPosition discardSSTables(long truncatedAt)
    {
        assert data.getCompacting().isEmpty() : data.getCompacting();

        List<SSTableReader> truncatedSSTables = new ArrayList<SSTableReader>();

        for (SSTableReader sstable : getSSTables())
        {
            if (!sstable.newSince(truncatedAt))
                truncatedSSTables.add(sstable);
        }

        if (truncatedSSTables.isEmpty())
            return ReplayPosition.NONE;

        markObsolete(truncatedSSTables, OperationType.UNKNOWN);
        return ReplayPosition.getReplayPosition(truncatedSSTables);
    }

    public double getDroppableTombstoneRatio()
    {
        return getDataTracker().getDroppableTombstoneRatio();
    }

    public long trueSnapshotsSize()
    {
        return directories.trueSnapshotsSize();
    }

    @VisibleForTesting
    void resetFileIndexGenerator()
    {
        fileIndexGenerator.set(0);
    }

    // returns the "canonical" version of any current sstable, i.e. if an sstable is being replaced and is only partially
    // visible to reads, this sstable will be returned as its original entirety, and its replacement will not be returned
    // (even if it completely replaces it)
    public static final Function<DataTracker.View, List<SSTableReader>> CANONICAL_SSTABLES = new Function<DataTracker.View, List<SSTableReader>>()
    {
        public List<SSTableReader> apply(DataTracker.View view)
        {
            List<SSTableReader> sstables = new ArrayList<>();
            for (SSTableReader sstable : view.compacting)
                if (sstable.openReason != SSTableReader.OpenReason.EARLY)
                    sstables.add(sstable);
            for (SSTableReader sstable : view.sstables)
                if (!view.compacting.contains(sstable) && sstable.openReason != SSTableReader.OpenReason.EARLY)
                    sstables.add(sstable);
            return sstables;
        }
    };

    public static final Function<DataTracker.View, List<SSTableReader>> UNREPAIRED_SSTABLES = new Function<DataTracker.View, List<SSTableReader>>()
    {
        public List<SSTableReader> apply(DataTracker.View view)
        {
            List<SSTableReader> sstables = new ArrayList<>();
            for (SSTableReader sstable : CANONICAL_SSTABLES.apply(view))
            {
                if (!sstable.isRepaired())
                    sstables.add(sstable);
            }
            return sstables;
        }
    };
}


File: src/java/org/apache/cassandra/service/StorageProxy.java
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

import java.io.IOException;
import java.lang.management.ManagementFactory;
import java.net.InetAddress;
import java.nio.ByteBuffer;
import java.util.*;
import java.util.concurrent.*;
import java.util.concurrent.atomic.AtomicInteger;
import javax.management.MBeanServer;
import javax.management.ObjectName;

import com.google.common.base.Predicate;
import com.google.common.cache.CacheLoader;
import com.google.common.collect.*;
import com.google.common.util.concurrent.Uninterruptibles;
import org.apache.cassandra.metrics.*;
import org.apache.commons.lang3.StringUtils;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import org.apache.cassandra.concurrent.Stage;
import org.apache.cassandra.concurrent.StageManager;
import org.apache.cassandra.config.CFMetaData;
import org.apache.cassandra.config.DatabaseDescriptor;
import org.apache.cassandra.config.Schema;
import org.apache.cassandra.db.*;
import org.apache.cassandra.db.Keyspace;
import org.apache.cassandra.db.index.SecondaryIndex;
import org.apache.cassandra.db.index.SecondaryIndexSearcher;
import org.apache.cassandra.db.marshal.UUIDType;
import org.apache.cassandra.dht.AbstractBounds;
import org.apache.cassandra.dht.Bounds;
import org.apache.cassandra.dht.RingPosition;
import org.apache.cassandra.dht.Token;
import org.apache.cassandra.exceptions.*;
import org.apache.cassandra.gms.FailureDetector;
import org.apache.cassandra.gms.Gossiper;
import org.apache.cassandra.io.util.DataOutputBuffer;
import org.apache.cassandra.locator.AbstractReplicationStrategy;
import org.apache.cassandra.locator.IEndpointSnitch;
import org.apache.cassandra.locator.LocalStrategy;
import org.apache.cassandra.locator.TokenMetadata;
import org.apache.cassandra.net.*;
import org.apache.cassandra.service.paxos.*;
import org.apache.cassandra.sink.SinkManager;
import org.apache.cassandra.tracing.Tracing;
import org.apache.cassandra.triggers.TriggerExecutor;
import org.apache.cassandra.utils.*;

public class StorageProxy implements StorageProxyMBean
{
    public static final String MBEAN_NAME = "org.apache.cassandra.db:type=StorageProxy";
    private static final Logger logger = LoggerFactory.getLogger(StorageProxy.class);
    static final boolean OPTIMIZE_LOCAL_REQUESTS = true; // set to false to test messagingservice path on single node

    public static final String UNREACHABLE = "UNREACHABLE";

    private static final WritePerformer standardWritePerformer;
    private static final WritePerformer counterWritePerformer;
    private static final WritePerformer counterWriteOnCoordinatorPerformer;

    public static final StorageProxy instance = new StorageProxy();

    private static volatile int maxHintsInProgress = 128 * FBUtilities.getAvailableProcessors();
    private static final CacheLoader<InetAddress, AtomicInteger> hintsInProgress = new CacheLoader<InetAddress, AtomicInteger>()
    {
        public AtomicInteger load(InetAddress inetAddress)
        {
            return new AtomicInteger(0);
        }
    };
    private static final ClientRequestMetrics readMetrics = new ClientRequestMetrics("Read");
    private static final ClientRequestMetrics rangeMetrics = new ClientRequestMetrics("RangeSlice");
    private static final ClientRequestMetrics writeMetrics = new ClientRequestMetrics("Write");
    private static final CASClientRequestMetrics casWriteMetrics = new CASClientRequestMetrics("CASWrite");
    private static final CASClientRequestMetrics casReadMetrics = new CASClientRequestMetrics("CASRead");

    private static final double CONCURRENT_SUBREQUESTS_MARGIN = 0.10;

    private StorageProxy() {}

    static
    {
        MBeanServer mbs = ManagementFactory.getPlatformMBeanServer();
        try
        {
            mbs.registerMBean(instance, new ObjectName(MBEAN_NAME));
        }
        catch (Exception e)
        {
            throw new RuntimeException(e);
        }

        standardWritePerformer = new WritePerformer()
        {
            public void apply(IMutation mutation,
                              Iterable<InetAddress> targets,
                              AbstractWriteResponseHandler responseHandler,
                              String localDataCenter,
                              ConsistencyLevel consistency_level)
            throws OverloadedException
            {
                assert mutation instanceof Mutation;
                sendToHintedEndpoints((Mutation) mutation, targets, responseHandler, localDataCenter);
            }
        };

        /*
         * We execute counter writes in 2 places: either directly in the coordinator node if it is a replica, or
         * in CounterMutationVerbHandler on a replica othewise. The write must be executed on the COUNTER_MUTATION stage
         * but on the latter case, the verb handler already run on the COUNTER_MUTATION stage, so we must not execute the
         * underlying on the stage otherwise we risk a deadlock. Hence two different performer.
         */
        counterWritePerformer = new WritePerformer()
        {
            public void apply(IMutation mutation,
                              Iterable<InetAddress> targets,
                              AbstractWriteResponseHandler responseHandler,
                              String localDataCenter,
                              ConsistencyLevel consistencyLevel)
            {
                counterWriteTask(mutation, targets, responseHandler, localDataCenter).run();
            }
        };

        counterWriteOnCoordinatorPerformer = new WritePerformer()
        {
            public void apply(IMutation mutation,
                              Iterable<InetAddress> targets,
                              AbstractWriteResponseHandler responseHandler,
                              String localDataCenter,
                              ConsistencyLevel consistencyLevel)
            {
                StageManager.getStage(Stage.COUNTER_MUTATION)
                            .execute(counterWriteTask(mutation, targets, responseHandler, localDataCenter));
            }
        };
    }

    /**
     * Apply @param updates if and only if the current values in the row for @param key
     * match the provided @param conditions.  The algorithm is "raw" Paxos: that is, Paxos
     * minus leader election -- any node in the cluster may propose changes for any row,
     * which (that is, the row) is the unit of values being proposed, not single columns.
     *
     * The Paxos cohort is only the replicas for the given key, not the entire cluster.
     * So we expect performance to be reasonable, but CAS is still intended to be used
     * "when you really need it," not for all your updates.
     *
     * There are three phases to Paxos:
     *  1. Prepare: the coordinator generates a ballot (timeUUID in our case) and asks replicas to (a) promise
     *     not to accept updates from older ballots and (b) tell us about the most recent update it has already
     *     accepted.
     *  2. Accept: if a majority of replicas reply, the coordinator asks replicas to accept the value of the
     *     highest proposal ballot it heard about, or a new value if no in-progress proposals were reported.
     *  3. Commit (Learn): if a majority of replicas acknowledge the accept request, we can commit the new
     *     value.
     *
     *  Commit procedure is not covered in "Paxos Made Simple," and only briefly mentioned in "Paxos Made Live,"
     *  so here is our approach:
     *   3a. The coordinator sends a commit message to all replicas with the ballot and value.
     *   3b. Because of 1-2, this will be the highest-seen commit ballot.  The replicas will note that,
     *       and send it with subsequent promise replies.  This allows us to discard acceptance records
     *       for successfully committed replicas, without allowing incomplete proposals to commit erroneously
     *       later on.
     *
     *  Note that since we are performing a CAS rather than a simple update, we perform a read (of committed
     *  values) between the prepare and accept phases.  This gives us a slightly longer window for another
     *  coordinator to come along and trump our own promise with a newer one but is otherwise safe.
     *
     * @param keyspaceName the keyspace for the CAS
     * @param cfName the column family for the CAS
     * @param key the row key for the row to CAS
     * @param request the conditions for the CAS to apply as well as the update to perform if the conditions hold.
     * @param consistencyForPaxos the consistency for the paxos prepare and propose round. This can only be either SERIAL or LOCAL_SERIAL.
     * @param consistencyForCommit the consistency for write done during the commit phase. This can be anything, except SERIAL or LOCAL_SERIAL.
     *
     * @return null if the operation succeeds in updating the row, or the current values corresponding to conditions.
     * (since, if the CAS doesn't succeed, it means the current value do not match the conditions).
     */
    public static ColumnFamily cas(String keyspaceName,
                                   String cfName,
                                   ByteBuffer key,
                                   CASRequest request,
                                   ConsistencyLevel consistencyForPaxos,
                                   ConsistencyLevel consistencyForCommit,
                                   ClientState state)
    throws UnavailableException, IsBootstrappingException, ReadTimeoutException, WriteTimeoutException, InvalidRequestException
    {
        final long start = System.nanoTime();
        int contentions = 0;
        try
        {
            consistencyForPaxos.validateForCas();
            consistencyForCommit.validateForCasCommit(keyspaceName);

            CFMetaData metadata = Schema.instance.getCFMetaData(keyspaceName, cfName);

            long timeout = TimeUnit.MILLISECONDS.toNanos(DatabaseDescriptor.getCasContentionTimeout());
            while (System.nanoTime() - start < timeout)
            {
                // for simplicity, we'll do a single liveness check at the start of each attempt
                Pair<List<InetAddress>, Integer> p = getPaxosParticipants(keyspaceName, key, consistencyForPaxos);
                List<InetAddress> liveEndpoints = p.left;
                int requiredParticipants = p.right;

                final Pair<UUID, Integer> pair = beginAndRepairPaxos(start, key, metadata, liveEndpoints, requiredParticipants, consistencyForPaxos, consistencyForCommit, true, state);
                final UUID ballot = pair.left;
                contentions += pair.right;
                // read the current values and check they validate the conditions
                Tracing.trace("Reading existing values for CAS precondition");
                long timestamp = System.currentTimeMillis();
                ReadCommand readCommand = ReadCommand.create(keyspaceName, key, cfName, timestamp, request.readFilter());
                List<Row> rows = read(Arrays.asList(readCommand), consistencyForPaxos == ConsistencyLevel.LOCAL_SERIAL ? ConsistencyLevel.LOCAL_QUORUM : ConsistencyLevel.QUORUM);
                ColumnFamily current = rows.get(0).cf;
                if (!request.appliesTo(current))
                {
                    Tracing.trace("CAS precondition does not match current values {}", current);
                    // We should not return null as this means success
                    casWriteMetrics.conditionNotMet.inc();
                    return current == null ? ArrayBackedSortedColumns.factory.create(metadata) : current;
                }

                // finish the paxos round w/ the desired updates
                // TODO turn null updates into delete?
                ColumnFamily updates = request.makeUpdates(current);

                // Apply triggers to cas updates. A consideration here is that
                // triggers emit Mutations, and so a given trigger implementation
                // may generate mutations for partitions other than the one this
                // paxos round is scoped for. In this case, TriggerExecutor will
                // validate that the generated mutations are targetted at the same
                // partition as the initial updates and reject (via an
                // InvalidRequestException) any which aren't.
                updates = TriggerExecutor.instance.execute(key, updates);

                Commit proposal = Commit.newProposal(key, ballot, updates);
                Tracing.trace("CAS precondition is met; proposing client-requested updates for {}", ballot);
                if (proposePaxos(proposal, liveEndpoints, requiredParticipants, true, consistencyForPaxos))
                {
                    commitPaxos(proposal, consistencyForCommit);
                    Tracing.trace("CAS successful");
                    return null;
                }

                Tracing.trace("Paxos proposal not accepted (pre-empted by a higher ballot)");
                contentions++;
                Uninterruptibles.sleepUninterruptibly(ThreadLocalRandom.current().nextInt(100), TimeUnit.MILLISECONDS);
                // continue to retry
            }

            throw new WriteTimeoutException(WriteType.CAS, consistencyForPaxos, 0, consistencyForPaxos.blockFor(Keyspace.open(keyspaceName)));
        }
        catch (WriteTimeoutException|ReadTimeoutException e)
        {
            casWriteMetrics.timeouts.mark();
            throw e;
        }
        catch(UnavailableException e)
        {
            casWriteMetrics.unavailables.mark();
            throw e;
        }
        finally
        {
            if(contentions > 0)
                casWriteMetrics.contention.update(contentions);
            casWriteMetrics.addNano(System.nanoTime() - start);
        }
    }

    private static Predicate<InetAddress> sameDCPredicateFor(final String dc)
    {
        final IEndpointSnitch snitch = DatabaseDescriptor.getEndpointSnitch();
        return new Predicate<InetAddress>()
        {
            public boolean apply(InetAddress host)
            {
                return dc.equals(snitch.getDatacenter(host));
            }
        };
    }

    private static Pair<List<InetAddress>, Integer> getPaxosParticipants(String keyspaceName, ByteBuffer key, ConsistencyLevel consistencyForPaxos) throws UnavailableException
    {
        Token tk = StorageService.getPartitioner().getToken(key);
        List<InetAddress> naturalEndpoints = StorageService.instance.getNaturalEndpoints(keyspaceName, tk);
        Collection<InetAddress> pendingEndpoints = StorageService.instance.getTokenMetadata().pendingEndpointsFor(tk, keyspaceName);

        if (consistencyForPaxos == ConsistencyLevel.LOCAL_SERIAL)
        {
            // Restrict naturalEndpoints and pendingEndpoints to node in the local DC only
            String localDc = DatabaseDescriptor.getEndpointSnitch().getDatacenter(FBUtilities.getBroadcastAddress());
            Predicate<InetAddress> isLocalDc = sameDCPredicateFor(localDc);
            naturalEndpoints = ImmutableList.copyOf(Iterables.filter(naturalEndpoints, isLocalDc));
            pendingEndpoints = ImmutableList.copyOf(Iterables.filter(pendingEndpoints, isLocalDc));
        }
        int participants = pendingEndpoints.size() + naturalEndpoints.size();
        int requiredParticipants = participants / 2 + 1; // See CASSANDRA-8346, CASSANDRA-833
        List<InetAddress> liveEndpoints = ImmutableList.copyOf(Iterables.filter(Iterables.concat(naturalEndpoints, pendingEndpoints), IAsyncCallback.isAlive));
        if (liveEndpoints.size() < requiredParticipants)
            throw new UnavailableException(consistencyForPaxos, requiredParticipants, liveEndpoints.size());

        // We cannot allow CAS operations with 2 or more pending endpoints, see #8346.
        // Note that we fake an impossible number of required nodes in the unavailable exception
        // to nail home the point that it's an impossible operation no matter how many nodes are live.
        if (pendingEndpoints.size() > 1)
            throw new UnavailableException(String.format("Cannot perform LWT operation as there is more than one (%d) pending range movement", pendingEndpoints.size()),
                                           consistencyForPaxos,
                                           participants + 1,
                                           liveEndpoints.size());

        return Pair.create(liveEndpoints, requiredParticipants);
    }

    /**
     * begin a Paxos session by sending a prepare request and completing any in-progress requests seen in the replies
     *
     * @return the Paxos ballot promised by the replicas if no in-progress requests were seen and a quorum of
     * nodes have seen the mostRecentCommit.  Otherwise, return null.
     */
    private static Pair<UUID, Integer> beginAndRepairPaxos(long start,
                                                           ByteBuffer key,
                                                           CFMetaData metadata,
                                                           List<InetAddress> liveEndpoints,
                                                           int requiredParticipants,
                                                           ConsistencyLevel consistencyForPaxos,
                                                           ConsistencyLevel consistencyForCommit,
                                                           final boolean isWrite,
                                                           ClientState state)
    throws WriteTimeoutException
    {
        long timeout = TimeUnit.MILLISECONDS.toNanos(DatabaseDescriptor.getCasContentionTimeout());

        PrepareCallback summary = null;
        int contentions = 0;
        while (System.nanoTime() - start < timeout)
        {
            // We don't want to use a timestamp that is older than the last one assigned by the ClientState or operations
            // may appear out-of-order (#7801). But note that state.getTimestamp() is in microseconds while the ballot
            // timestamp is only in milliseconds
            long currentTime = (state.getTimestamp() / 1000) + 1;
            long ballotMillis = summary == null
                              ? currentTime
                              : Math.max(currentTime, 1 + UUIDGen.unixTimestamp(summary.mostRecentInProgressCommit.ballot));
            UUID ballot = UUIDGen.getTimeUUID(ballotMillis);

            // prepare
            Tracing.trace("Preparing {}", ballot);
            Commit toPrepare = Commit.newPrepare(key, metadata, ballot);
            summary = preparePaxos(toPrepare, liveEndpoints, requiredParticipants, consistencyForPaxos);
            if (!summary.promised)
            {
                Tracing.trace("Some replicas have already promised a higher ballot than ours; aborting");
                contentions++;
                // sleep a random amount to give the other proposer a chance to finish
                Uninterruptibles.sleepUninterruptibly(ThreadLocalRandom.current().nextInt(100), TimeUnit.MILLISECONDS);
                continue;
            }

            Commit inProgress = summary.mostRecentInProgressCommitWithUpdate;
            Commit mostRecent = summary.mostRecentCommit;

            // If we have an in-progress ballot greater than the MRC we know, then it's an in-progress round that
            // needs to be completed, so do it.
            if (!inProgress.update.isEmpty() && inProgress.isAfter(mostRecent))
            {
                Tracing.trace("Finishing incomplete paxos round {}", inProgress);
                if(isWrite)
                    casWriteMetrics.unfinishedCommit.inc();
                else
                    casReadMetrics.unfinishedCommit.inc();
                Commit refreshedInProgress = Commit.newProposal(inProgress.key, ballot, inProgress.update);
                if (proposePaxos(refreshedInProgress, liveEndpoints, requiredParticipants, false, consistencyForPaxos))
                {
                    try
                    {
                        commitPaxos(refreshedInProgress, consistencyForCommit);
                    }
                    catch (WriteTimeoutException e)
                    {
                        // We're still doing preparation for the paxos rounds, so we want to use the CAS (see CASSANDRA-8672)
                        throw new WriteTimeoutException(WriteType.CAS, e.consistency, e.received, e.blockFor);
                    }
                }
                else
                {
                    Tracing.trace("Some replicas have already promised a higher ballot than ours; aborting");
                    // sleep a random amount to give the other proposer a chance to finish
                    contentions++;
                    Uninterruptibles.sleepUninterruptibly(ThreadLocalRandom.current().nextInt(100), TimeUnit.MILLISECONDS);
                }
                continue;
            }

            // To be able to propose our value on a new round, we need a quorum of replica to have learn the previous one. Why is explained at:
            // https://issues.apache.org/jira/browse/CASSANDRA-5062?focusedCommentId=13619810&page=com.atlassian.jira.plugin.system.issuetabpanels:comment-tabpanel#comment-13619810)
            // Since we waited for quorum nodes, if some of them haven't seen the last commit (which may just be a timing issue, but may also
            // mean we lost messages), we pro-actively "repair" those nodes, and retry.
            Iterable<InetAddress> missingMRC = summary.replicasMissingMostRecentCommit();
            if (Iterables.size(missingMRC) > 0)
            {
                Tracing.trace("Repairing replicas that missed the most recent commit");
                sendCommit(mostRecent, missingMRC);
                // TODO: provided commits don't invalid the prepare we just did above (which they don't), we could just wait
                // for all the missingMRC to acknowledge this commit and then move on with proposing our value. But that means
                // adding the ability to have commitPaxos block, which is exactly CASSANDRA-5442 will do. So once we have that
                // latter ticket, we can pass CL.ALL to the commit above and remove the 'continue'.
                continue;
            }

            // We might commit this ballot and we want to ensure operations starting after this CAS succeed will be assigned
            // a timestamp greater that the one of this ballot, so operation order is preserved (#7801)
            state.updateLastTimestamp(ballotMillis * 1000);

            return Pair.create(ballot, contentions);
        }

        throw new WriteTimeoutException(WriteType.CAS, consistencyForPaxos, 0, consistencyForPaxos.blockFor(Keyspace.open(metadata.ksName)));
    }

    /**
     * Unlike commitPaxos, this does not wait for replies
     */
    private static void sendCommit(Commit commit, Iterable<InetAddress> replicas)
    {
        MessageOut<Commit> message = new MessageOut<Commit>(MessagingService.Verb.PAXOS_COMMIT, commit, Commit.serializer);
        for (InetAddress target : replicas)
            MessagingService.instance().sendOneWay(message, target);
    }

    private static PrepareCallback preparePaxos(Commit toPrepare, List<InetAddress> endpoints, int requiredParticipants, ConsistencyLevel consistencyForPaxos)
    throws WriteTimeoutException
    {
        PrepareCallback callback = new PrepareCallback(toPrepare.key, toPrepare.update.metadata(), requiredParticipants, consistencyForPaxos);
        MessageOut<Commit> message = new MessageOut<Commit>(MessagingService.Verb.PAXOS_PREPARE, toPrepare, Commit.serializer);
        for (InetAddress target : endpoints)
            MessagingService.instance().sendRR(message, target, callback);
        callback.await();
        return callback;
    }

    private static boolean proposePaxos(Commit proposal, List<InetAddress> endpoints, int requiredParticipants, boolean timeoutIfPartial, ConsistencyLevel consistencyLevel)
    throws WriteTimeoutException
    {
        ProposeCallback callback = new ProposeCallback(endpoints.size(), requiredParticipants, !timeoutIfPartial, consistencyLevel);
        MessageOut<Commit> message = new MessageOut<Commit>(MessagingService.Verb.PAXOS_PROPOSE, proposal, Commit.serializer);
        for (InetAddress target : endpoints)
            MessagingService.instance().sendRR(message, target, callback);

        callback.await();

        if (callback.isSuccessful())
            return true;

        if (timeoutIfPartial && !callback.isFullyRefused())
            throw new WriteTimeoutException(WriteType.CAS, consistencyLevel, callback.getAcceptCount(), requiredParticipants);

        return false;
    }

    private static void commitPaxos(Commit proposal, ConsistencyLevel consistencyLevel) throws WriteTimeoutException
    {
        boolean shouldBlock = consistencyLevel != ConsistencyLevel.ANY;
        Keyspace keyspace = Keyspace.open(proposal.update.metadata().ksName);

        Token tk = StorageService.getPartitioner().getToken(proposal.key);
        List<InetAddress> naturalEndpoints = StorageService.instance.getNaturalEndpoints(keyspace.getName(), tk);
        Collection<InetAddress> pendingEndpoints = StorageService.instance.getTokenMetadata().pendingEndpointsFor(tk, keyspace.getName());

        AbstractWriteResponseHandler responseHandler = null;
        if (shouldBlock)
        {
            AbstractReplicationStrategy rs = keyspace.getReplicationStrategy();
            responseHandler = rs.getWriteResponseHandler(naturalEndpoints, pendingEndpoints, consistencyLevel, null, WriteType.SIMPLE);
        }

        MessageOut<Commit> message = new MessageOut<Commit>(MessagingService.Verb.PAXOS_COMMIT, proposal, Commit.serializer);
        for (InetAddress destination : Iterables.concat(naturalEndpoints, pendingEndpoints))
        {
            if (FailureDetector.instance.isAlive(destination))
            {
                if (shouldBlock)
                    MessagingService.instance().sendRR(message, destination, responseHandler);
                else
                    MessagingService.instance().sendOneWay(message, destination);
            }
        }

        if (shouldBlock)
            responseHandler.get();
    }

    /**
     * Use this method to have these Mutations applied
     * across all replicas. This method will take care
     * of the possibility of a replica being down and hint
     * the data across to some other replica.
     *
     * @param mutations the mutations to be applied across the replicas
     * @param consistency_level the consistency level for the operation
     */
    public static void mutate(Collection<? extends IMutation> mutations, ConsistencyLevel consistency_level)
    throws UnavailableException, OverloadedException, WriteTimeoutException
    {
        Tracing.trace("Determining replicas for mutation");
        final String localDataCenter = DatabaseDescriptor.getEndpointSnitch().getDatacenter(FBUtilities.getBroadcastAddress());

        long startTime = System.nanoTime();
        List<AbstractWriteResponseHandler> responseHandlers = new ArrayList<>(mutations.size());

        try
        {
            for (IMutation mutation : mutations)
            {
                if (mutation instanceof CounterMutation)
                {
                    responseHandlers.add(mutateCounter((CounterMutation)mutation, localDataCenter));
                }
                else
                {
                    WriteType wt = mutations.size() <= 1 ? WriteType.SIMPLE : WriteType.UNLOGGED_BATCH;
                    responseHandlers.add(performWrite(mutation, consistency_level, localDataCenter, standardWritePerformer, null, wt));
                }
            }

            // wait for writes.  throws TimeoutException if necessary
            for (AbstractWriteResponseHandler responseHandler : responseHandlers)
            {
                responseHandler.get();
            }
        }
        catch (WriteTimeoutException ex)
        {
            if (consistency_level == ConsistencyLevel.ANY)
            {
                // hint all the mutations (except counters, which can't be safely retried).  This means
                // we'll re-hint any successful ones; doesn't seem worth it to track individual success
                // just for this unusual case.
                for (IMutation mutation : mutations)
                {
                    if (mutation instanceof CounterMutation)
                        continue;

                    Token tk = StorageService.getPartitioner().getToken(mutation.key());
                    List<InetAddress> naturalEndpoints = StorageService.instance.getNaturalEndpoints(mutation.getKeyspaceName(), tk);
                    Collection<InetAddress> pendingEndpoints = StorageService.instance.getTokenMetadata().pendingEndpointsFor(tk, mutation.getKeyspaceName());
                    for (InetAddress target : Iterables.concat(naturalEndpoints, pendingEndpoints))
                    {
                        // local writes can timeout, but cannot be dropped (see LocalMutationRunnable and
                        // CASSANDRA-6510), so there is no need to hint or retry
                        if (!target.equals(FBUtilities.getBroadcastAddress()) && shouldHint(target))
                            submitHint((Mutation) mutation, target, null);
                    }
                }
                Tracing.trace("Wrote hint to satisfy CL.ANY after no replicas acknowledged the write");
            }
            else
            {
                writeMetrics.timeouts.mark();
                ClientRequestMetrics.writeTimeouts.inc();
                Tracing.trace("Write timeout; received {} of {} required replies", ex.received, ex.blockFor);
                throw ex;
            }
        }
        catch (UnavailableException e)
        {
            writeMetrics.unavailables.mark();
            ClientRequestMetrics.writeUnavailables.inc();
            Tracing.trace("Unavailable");
            throw e;
        }
        catch (OverloadedException e)
        {
            ClientRequestMetrics.writeUnavailables.inc();
            Tracing.trace("Overloaded");
            throw e;
        }
        finally
        {
            writeMetrics.addNano(System.nanoTime() - startTime);
        }
    }

    @SuppressWarnings("unchecked")
    public static void mutateWithTriggers(Collection<? extends IMutation> mutations,
                                          ConsistencyLevel consistencyLevel,
                                          boolean mutateAtomically)
    throws WriteTimeoutException, UnavailableException, OverloadedException, InvalidRequestException
    {
        Collection<Mutation> augmented = TriggerExecutor.instance.execute(mutations);

        if (augmented != null)
            mutateAtomically(augmented, consistencyLevel);
        else if (mutateAtomically)
            mutateAtomically((Collection<Mutation>) mutations, consistencyLevel);
        else
            mutate(mutations, consistencyLevel);
    }

    /**
     * See mutate. Adds additional steps before and after writing a batch.
     * Before writing the batch (but after doing availability check against the FD for the row replicas):
     *      write the entire batch to a batchlog elsewhere in the cluster.
     * After: remove the batchlog entry (after writing hints for the batch rows, if necessary).
     *
     * @param mutations the Mutations to be applied across the replicas
     * @param consistency_level the consistency level for the operation
     */
    public static void mutateAtomically(Collection<Mutation> mutations, ConsistencyLevel consistency_level)
    throws UnavailableException, OverloadedException, WriteTimeoutException
    {
        Tracing.trace("Determining replicas for atomic batch");
        long startTime = System.nanoTime();

        List<WriteResponseHandlerWrapper> wrappers = new ArrayList<WriteResponseHandlerWrapper>(mutations.size());
        String localDataCenter = DatabaseDescriptor.getEndpointSnitch().getDatacenter(FBUtilities.getBroadcastAddress());

        try
        {
            // add a handler for each mutation - includes checking availability, but doesn't initiate any writes, yet
            for (Mutation mutation : mutations)
            {
                WriteResponseHandlerWrapper wrapper = wrapResponseHandler(mutation, consistency_level, WriteType.BATCH);
                // exit early if we can't fulfill the CL at this time.
                wrapper.handler.assureSufficientLiveNodes();
                wrappers.add(wrapper);
            }

            // write to the batchlog
            Collection<InetAddress> batchlogEndpoints = getBatchlogEndpoints(localDataCenter, consistency_level);
            UUID batchUUID = UUIDGen.getTimeUUID();
            syncWriteToBatchlog(mutations, batchlogEndpoints, batchUUID);

            // now actually perform the writes and wait for them to complete
            syncWriteBatchedMutations(wrappers, localDataCenter);

            // remove the batchlog entries asynchronously
            asyncRemoveFromBatchlog(batchlogEndpoints, batchUUID);
        }
        catch (UnavailableException e)
        {
            writeMetrics.unavailables.mark();
            ClientRequestMetrics.writeUnavailables.inc();
            Tracing.trace("Unavailable");
            throw e;
        }
        catch (WriteTimeoutException e)
        {
            writeMetrics.timeouts.mark();
            ClientRequestMetrics.writeTimeouts.inc();
            Tracing.trace("Write timeout; received {} of {} required replies", e.received, e.blockFor);
            throw e;
        }
        finally
        {
            writeMetrics.addNano(System.nanoTime() - startTime);
        }
    }

    private static void syncWriteToBatchlog(Collection<Mutation> mutations, Collection<InetAddress> endpoints, UUID uuid)
    throws WriteTimeoutException
    {
        AbstractWriteResponseHandler handler = new WriteResponseHandler(endpoints,
                                                                        Collections.<InetAddress>emptyList(),
                                                                        ConsistencyLevel.ONE,
                                                                        Keyspace.open(Keyspace.SYSTEM_KS),
                                                                        null,
                                                                        WriteType.BATCH_LOG);

        MessageOut<Mutation> message = BatchlogManager.getBatchlogMutationFor(mutations, uuid, MessagingService.current_version)
                                                      .createMessage();
        for (InetAddress target : endpoints)
        {
            int targetVersion = MessagingService.instance().getVersion(target);
            if (target.equals(FBUtilities.getBroadcastAddress()) && OPTIMIZE_LOCAL_REQUESTS)
            {
                insertLocal(message.payload, handler);
            }
            else if (targetVersion == MessagingService.current_version)
            {
                MessagingService.instance().sendRR(message, target, handler, false);
            }
            else
            {
                MessagingService.instance().sendRR(BatchlogManager.getBatchlogMutationFor(mutations, uuid, targetVersion)
                                                                  .createMessage(),
                                                   target,
                                                   handler,
                                                   false);
            }
        }

        handler.get();
    }

    private static void asyncRemoveFromBatchlog(Collection<InetAddress> endpoints, UUID uuid)
    {
        AbstractWriteResponseHandler handler = new WriteResponseHandler(endpoints,
                                                                        Collections.<InetAddress>emptyList(),
                                                                        ConsistencyLevel.ANY,
                                                                        Keyspace.open(Keyspace.SYSTEM_KS),
                                                                        null,
                                                                        WriteType.SIMPLE);
        Mutation mutation = new Mutation(Keyspace.SYSTEM_KS, UUIDType.instance.decompose(uuid));
        mutation.delete(SystemKeyspace.BATCHLOG_CF, FBUtilities.timestampMicros());
        MessageOut<Mutation> message = mutation.createMessage();
        for (InetAddress target : endpoints)
        {
            if (target.equals(FBUtilities.getBroadcastAddress()) && OPTIMIZE_LOCAL_REQUESTS)
                insertLocal(message.payload, handler);
            else
                MessagingService.instance().sendRR(message, target, handler, false);
        }
    }

    private static void syncWriteBatchedMutations(List<WriteResponseHandlerWrapper> wrappers, String localDataCenter)
    throws WriteTimeoutException, OverloadedException
    {
        for (WriteResponseHandlerWrapper wrapper : wrappers)
        {
            Iterable<InetAddress> endpoints = Iterables.concat(wrapper.handler.naturalEndpoints, wrapper.handler.pendingEndpoints);
            sendToHintedEndpoints(wrapper.mutation, endpoints, wrapper.handler, localDataCenter);
        }

        for (WriteResponseHandlerWrapper wrapper : wrappers)
            wrapper.handler.get();
    }

    /**
     * Perform the write of a mutation given a WritePerformer.
     * Gather the list of write endpoints, apply locally and/or forward the mutation to
     * said write endpoint (deletaged to the actual WritePerformer) and wait for the
     * responses based on consistency level.
     *
     * @param mutation the mutation to be applied
     * @param consistency_level the consistency level for the write operation
     * @param performer the WritePerformer in charge of appliying the mutation
     * given the list of write endpoints (either standardWritePerformer for
     * standard writes or counterWritePerformer for counter writes).
     * @param callback an optional callback to be run if and when the write is
     * successful.
     */
    public static AbstractWriteResponseHandler performWrite(IMutation mutation,
                                                            ConsistencyLevel consistency_level,
                                                            String localDataCenter,
                                                            WritePerformer performer,
                                                            Runnable callback,
                                                            WriteType writeType)
    throws UnavailableException, OverloadedException
    {
        String keyspaceName = mutation.getKeyspaceName();
        AbstractReplicationStrategy rs = Keyspace.open(keyspaceName).getReplicationStrategy();

        Token tk = StorageService.getPartitioner().getToken(mutation.key());
        List<InetAddress> naturalEndpoints = StorageService.instance.getNaturalEndpoints(keyspaceName, tk);
        Collection<InetAddress> pendingEndpoints = StorageService.instance.getTokenMetadata().pendingEndpointsFor(tk, keyspaceName);

        AbstractWriteResponseHandler responseHandler = rs.getWriteResponseHandler(naturalEndpoints, pendingEndpoints, consistency_level, callback, writeType);

        // exit early if we can't fulfill the CL at this time
        responseHandler.assureSufficientLiveNodes();

        performer.apply(mutation, Iterables.concat(naturalEndpoints, pendingEndpoints), responseHandler, localDataCenter, consistency_level);
        return responseHandler;
    }

    // same as above except does not initiate writes (but does perform availability checks).
    private static WriteResponseHandlerWrapper wrapResponseHandler(Mutation mutation, ConsistencyLevel consistency_level, WriteType writeType)
    {
        AbstractReplicationStrategy rs = Keyspace.open(mutation.getKeyspaceName()).getReplicationStrategy();
        String keyspaceName = mutation.getKeyspaceName();
        Token tk = StorageService.getPartitioner().getToken(mutation.key());
        List<InetAddress> naturalEndpoints = StorageService.instance.getNaturalEndpoints(keyspaceName, tk);
        Collection<InetAddress> pendingEndpoints = StorageService.instance.getTokenMetadata().pendingEndpointsFor(tk, keyspaceName);
        AbstractWriteResponseHandler responseHandler = rs.getWriteResponseHandler(naturalEndpoints, pendingEndpoints, consistency_level, null, writeType);
        return new WriteResponseHandlerWrapper(responseHandler, mutation);
    }

    // used by atomic_batch_mutate to decouple availability check from the write itself, caches consistency level and endpoints.
    private static class WriteResponseHandlerWrapper
    {
        final AbstractWriteResponseHandler handler;
        final Mutation mutation;

        WriteResponseHandlerWrapper(AbstractWriteResponseHandler handler, Mutation mutation)
        {
            this.handler = handler;
            this.mutation = mutation;
        }
    }

    /*
     * Replicas are picked manually:
     * - replicas should be alive according to the failure detector
     * - replicas should be in the local datacenter
     * - choose min(2, number of qualifying candiates above)
     * - allow the local node to be the only replica only if it's a single-node DC
     */
    private static Collection<InetAddress> getBatchlogEndpoints(String localDataCenter, ConsistencyLevel consistencyLevel)
    throws UnavailableException
    {
        TokenMetadata.Topology topology = StorageService.instance.getTokenMetadata().cachedOnlyTokenMap().getTopology();
        Multimap<String, InetAddress> localEndpoints = HashMultimap.create(topology.getDatacenterRacks().get(localDataCenter));
        String localRack = DatabaseDescriptor.getEndpointSnitch().getRack(FBUtilities.getBroadcastAddress());

        Collection<InetAddress> chosenEndpoints = new BatchlogManager.EndpointFilter(localRack, localEndpoints).filter();
        if (chosenEndpoints.isEmpty())
        {
            if (consistencyLevel == ConsistencyLevel.ANY)
                return Collections.singleton(FBUtilities.getBroadcastAddress());

            throw new UnavailableException(ConsistencyLevel.ONE, 1, 0);
        }

        return chosenEndpoints;
    }

    /**
     * Send the mutations to the right targets, write it locally if it corresponds or writes a hint when the node
     * is not available.
     *
     * Note about hints:
     *
     * | Hinted Handoff | Consist. Level |
     * | on             |       >=1      | --> wait for hints. We DO NOT notify the handler with handler.response() for hints;
     * | on             |       ANY      | --> wait for hints. Responses count towards consistency.
     * | off            |       >=1      | --> DO NOT fire hints. And DO NOT wait for them to complete.
     * | off            |       ANY      | --> DO NOT fire hints. And DO NOT wait for them to complete.
     *
     * @throws OverloadedException if the hints cannot be written/enqueued
     */
    public static void sendToHintedEndpoints(final Mutation mutation,
                                             Iterable<InetAddress> targets,
                                             AbstractWriteResponseHandler responseHandler,
                                             String localDataCenter)
    throws OverloadedException
    {
        // extra-datacenter replicas, grouped by dc
        Map<String, Collection<InetAddress>> dcGroups = null;
        // only need to create a Message for non-local writes
        MessageOut<Mutation> message = null;

        boolean insertLocal = false;


        for (InetAddress destination : targets)
        {
            // avoid OOMing due to excess hints.  we need to do this check even for "live" nodes, since we can
            // still generate hints for those if it's overloaded or simply dead but not yet known-to-be-dead.
            // The idea is that if we have over maxHintsInProgress hints in flight, this is probably due to
            // a small number of nodes causing problems, so we should avoid shutting down writes completely to
            // healthy nodes.  Any node with no hintsInProgress is considered healthy.
            if (StorageMetrics.totalHintsInProgress.count() > maxHintsInProgress
                    && (getHintsInProgressFor(destination).get() > 0 && shouldHint(destination)))
            {
                throw new OverloadedException("Too many in flight hints: " + StorageMetrics.totalHintsInProgress.count());
            }

            if (FailureDetector.instance.isAlive(destination))
            {
                if (destination.equals(FBUtilities.getBroadcastAddress()) && OPTIMIZE_LOCAL_REQUESTS)
                {
                    insertLocal = true;
                } else
                {
                    // belongs on a different server
                    if (message == null)
                        message = mutation.createMessage();
                    String dc = DatabaseDescriptor.getEndpointSnitch().getDatacenter(destination);
                    // direct writes to local DC or old Cassandra versions
                    // (1.1 knows how to forward old-style String message IDs; updated to int in 2.0)
                    if (localDataCenter.equals(dc))
                    {
                        MessagingService.instance().sendRR(message, destination, responseHandler, true);
                    } else
                    {
                        Collection<InetAddress> messages = (dcGroups != null) ? dcGroups.get(dc) : null;
                        if (messages == null)
                        {
                            messages = new ArrayList<InetAddress>(3); // most DCs will have <= 3 replicas
                            if (dcGroups == null)
                                dcGroups = new HashMap<String, Collection<InetAddress>>();
                            dcGroups.put(dc, messages);
                        }
                        messages.add(destination);
                    }
                }
            } else
            {
                if (!shouldHint(destination))
                    continue;

                // Schedule a local hint
                submitHint(mutation, destination, responseHandler);
            }
        }

        if (insertLocal)
            insertLocal(mutation, responseHandler);

        if (dcGroups != null)
        {
            // for each datacenter, send the message to one node to relay the write to other replicas
            if (message == null)
                message = mutation.createMessage();

            for (Collection<InetAddress> dcTargets : dcGroups.values())
                sendMessagesToNonlocalDC(message, dcTargets, responseHandler);
        }
    }

    private static AtomicInteger getHintsInProgressFor(InetAddress destination)
    {
        try
        {
            return hintsInProgress.load(destination);
        }
        catch (Exception e)
        {
            throw new AssertionError(e);
        }
    }

    public static Future<Void> submitHint(final Mutation mutation,
                                          final InetAddress target,
                                          final AbstractWriteResponseHandler responseHandler)
    {
        // local write that time out should be handled by LocalMutationRunnable
        assert !target.equals(FBUtilities.getBroadcastAddress()) : target;

        HintRunnable runnable = new HintRunnable(target)
        {
            public void runMayThrow()
            {
                int ttl = HintedHandOffManager.calculateHintTTL(mutation);
                if (ttl > 0)
                {
                    logger.debug("Adding hint for {}", target);
                    writeHintForMutation(mutation, System.currentTimeMillis(), ttl, target);
                    // Notify the handler only for CL == ANY
                    if (responseHandler != null && responseHandler.consistencyLevel == ConsistencyLevel.ANY)
                        responseHandler.response(null);
                } else
                {
                    logger.debug("Skipped writing hint for {} (ttl {})", target, ttl);
                }
            }
        };

        return submitHint(runnable);
    }

    private static Future<Void> submitHint(HintRunnable runnable)
    {
        StorageMetrics.totalHintsInProgress.inc();
        getHintsInProgressFor(runnable.target).incrementAndGet();
        return (Future<Void>) StageManager.getStage(Stage.MUTATION).submit(runnable);
    }

    /**
     * @param now current time in milliseconds - relevant for hint replay handling of truncated CFs
     */
    public static void writeHintForMutation(Mutation mutation, long now, int ttl, InetAddress target)
    {
        assert ttl > 0;
        UUID hostId = StorageService.instance.getTokenMetadata().getHostId(target);
        assert hostId != null : "Missing host ID for " + target.getHostAddress();
        HintedHandOffManager.instance.hintFor(mutation, now, ttl, hostId).apply();
        StorageMetrics.totalHints.inc();
    }

    private static void sendMessagesToNonlocalDC(MessageOut<? extends IMutation> message, Collection<InetAddress> targets, AbstractWriteResponseHandler handler)
    {
        Iterator<InetAddress> iter = targets.iterator();
        InetAddress target = iter.next();

        // Add the other destinations of the same message as a FORWARD_HEADER entry
        DataOutputBuffer out = new DataOutputBuffer();
        try
        {
            out.writeInt(targets.size() - 1);
            while (iter.hasNext())
            {
                InetAddress destination = iter.next();
                CompactEndpointSerializationHelper.serialize(destination, out);
                int id = MessagingService.instance().addCallback(handler,
                                                                 message,
                                                                 destination,
                                                                 message.getTimeout(),
                                                                 handler.consistencyLevel,
                                                                 true);
                out.writeInt(id);
                logger.trace("Adding FWD message to {}@{}", id, destination);
            }
            message = message.withParameter(Mutation.FORWARD_TO, out.getData());
            // send the combined message + forward headers
            int id = MessagingService.instance().sendRR(message, target, handler, true);
            logger.trace("Sending message to {}@{}", id, target);
        }
        catch (IOException e)
        {
            // DataOutputBuffer is in-memory, doesn't throw IOException
            throw new AssertionError(e);
        }
    }

    private static void insertLocal(final Mutation mutation, final AbstractWriteResponseHandler responseHandler)
    {

        StageManager.getStage(Stage.MUTATION).maybeExecuteImmediately(new LocalMutationRunnable()
        {
            public void runMayThrow()
            {
                IMutation processed = SinkManager.processWriteRequest(mutation);
                if (processed != null)
                {
                    ((Mutation) processed).apply();
                    responseHandler.response(null);
                }
            }
        });
    }

    /**
     * Handle counter mutation on the coordinator host.
     *
     * A counter mutation needs to first be applied to a replica (that we'll call the leader for the mutation) before being
     * replicated to the other endpoint. To achieve so, there is two case:
     *   1) the coordinator host is a replica: we proceed to applying the update locally and replicate throug
     *   applyCounterMutationOnCoordinator
     *   2) the coordinator is not a replica: we forward the (counter)mutation to a chosen replica (that will proceed through
     *   applyCounterMutationOnLeader upon receive) and wait for its acknowledgment.
     *
     * Implementation note: We check if we can fulfill the CL on the coordinator host even if he is not a replica to allow
     * quicker response and because the WriteResponseHandlers don't make it easy to send back an error. We also always gather
     * the write latencies at the coordinator node to make gathering point similar to the case of standard writes.
     */
    public static AbstractWriteResponseHandler mutateCounter(CounterMutation cm, String localDataCenter) throws UnavailableException, OverloadedException
    {
        InetAddress endpoint = findSuitableEndpoint(cm.getKeyspaceName(), cm.key(), localDataCenter, cm.consistency());

        if (endpoint.equals(FBUtilities.getBroadcastAddress()))
        {
            return applyCounterMutationOnCoordinator(cm, localDataCenter);
        }
        else
        {
            // Exit now if we can't fulfill the CL here instead of forwarding to the leader replica
            String keyspaceName = cm.getKeyspaceName();
            AbstractReplicationStrategy rs = Keyspace.open(keyspaceName).getReplicationStrategy();
            Token tk = StorageService.getPartitioner().getToken(cm.key());
            List<InetAddress> naturalEndpoints = StorageService.instance.getNaturalEndpoints(keyspaceName, tk);
            Collection<InetAddress> pendingEndpoints = StorageService.instance.getTokenMetadata().pendingEndpointsFor(tk, keyspaceName);

            rs.getWriteResponseHandler(naturalEndpoints, pendingEndpoints, cm.consistency(), null, WriteType.COUNTER).assureSufficientLiveNodes();

            // Forward the actual update to the chosen leader replica
            AbstractWriteResponseHandler responseHandler = new WriteResponseHandler(endpoint, WriteType.COUNTER);

            Tracing.trace("Enqueuing counter update to {}", endpoint);
            MessagingService.instance().sendRR(cm.makeMutationMessage(), endpoint, responseHandler, false);
            return responseHandler;
        }
    }

    /**
     * Find a suitable replica as leader for counter update.
     * For now, we pick a random replica in the local DC (or ask the snitch if
     * there is no replica alive in the local DC).
     * TODO: if we track the latency of the counter writes (which makes sense
     * contrarily to standard writes since there is a read involved), we could
     * trust the dynamic snitch entirely, which may be a better solution. It
     * is unclear we want to mix those latencies with read latencies, so this
     * may be a bit involved.
     */
    private static InetAddress findSuitableEndpoint(String keyspaceName, ByteBuffer key, String localDataCenter, ConsistencyLevel cl) throws UnavailableException
    {
        Keyspace keyspace = Keyspace.open(keyspaceName);
        IEndpointSnitch snitch = DatabaseDescriptor.getEndpointSnitch();
        List<InetAddress> endpoints = StorageService.instance.getLiveNaturalEndpoints(keyspace, key);
        if (endpoints.isEmpty())
            // TODO have a way to compute the consistency level
            throw new UnavailableException(cl, cl.blockFor(keyspace), 0);

        List<InetAddress> localEndpoints = new ArrayList<InetAddress>();
        for (InetAddress endpoint : endpoints)
        {
            if (snitch.getDatacenter(endpoint).equals(localDataCenter))
                localEndpoints.add(endpoint);
        }
        if (localEndpoints.isEmpty())
        {
            // No endpoint in local DC, pick the closest endpoint according to the snitch
            snitch.sortByProximity(FBUtilities.getBroadcastAddress(), endpoints);
            return endpoints.get(0);
        }
        else
        {
            return localEndpoints.get(ThreadLocalRandom.current().nextInt(localEndpoints.size()));
        }
    }

    // Must be called on a replica of the mutation. This replica becomes the
    // leader of this mutation.
    public static AbstractWriteResponseHandler applyCounterMutationOnLeader(CounterMutation cm, String localDataCenter, Runnable callback)
    throws UnavailableException, OverloadedException
    {
        return performWrite(cm, cm.consistency(), localDataCenter, counterWritePerformer, callback, WriteType.COUNTER);
    }

    // Same as applyCounterMutationOnLeader but must with the difference that it use the MUTATION stage to execute the write (while
    // applyCounterMutationOnLeader assumes it is on the MUTATION stage already)
    public static AbstractWriteResponseHandler applyCounterMutationOnCoordinator(CounterMutation cm, String localDataCenter)
    throws UnavailableException, OverloadedException
    {
        return performWrite(cm, cm.consistency(), localDataCenter, counterWriteOnCoordinatorPerformer, null, WriteType.COUNTER);
    }

    private static Runnable counterWriteTask(final IMutation mutation,
                                             final Iterable<InetAddress> targets,
                                             final AbstractWriteResponseHandler responseHandler,
                                             final String localDataCenter)
    {
        return new DroppableRunnable(MessagingService.Verb.COUNTER_MUTATION)
        {
            @Override
            public void runMayThrow() throws OverloadedException, WriteTimeoutException
            {
                IMutation processed = SinkManager.processWriteRequest(mutation);
                if (processed == null)
                    return;

                assert processed instanceof CounterMutation;
                CounterMutation cm = (CounterMutation) processed;

                Mutation result = cm.apply();
                responseHandler.response(null);

                Set<InetAddress> remotes = Sets.difference(ImmutableSet.copyOf(targets),
                            ImmutableSet.of(FBUtilities.getBroadcastAddress()));
                if (!remotes.isEmpty())
                    sendToHintedEndpoints(result, remotes, responseHandler, localDataCenter);
            }
        };
    }

    private static boolean systemKeyspaceQuery(List<ReadCommand> cmds)
    {
        for (ReadCommand cmd : cmds)
            if (!cmd.ksName.equals(Keyspace.SYSTEM_KS))
                return false;
        return true;
    }

    public static List<Row> read(List<ReadCommand> commands, ConsistencyLevel consistencyLevel)
    throws UnavailableException, IsBootstrappingException, ReadTimeoutException, InvalidRequestException
    {
        // When using serial CL, the ClientState should be provided
        assert !consistencyLevel.isSerialConsistency();
        return read(commands, consistencyLevel, null);
    }

    /**
     * Performs the actual reading of a row out of the StorageService, fetching
     * a specific set of column names from a given column family.
     */
    public static List<Row> read(List<ReadCommand> commands, ConsistencyLevel consistencyLevel, ClientState state)
    throws UnavailableException, IsBootstrappingException, ReadTimeoutException, InvalidRequestException
    {
        if (StorageService.instance.isBootstrapMode() && !systemKeyspaceQuery(commands))
        {
            readMetrics.unavailables.mark();
            ClientRequestMetrics.readUnavailables.inc();
            throw new IsBootstrappingException();
        }

        return consistencyLevel.isSerialConsistency()
             ? readWithPaxos(commands, consistencyLevel, state)
             : readRegular(commands, consistencyLevel);
    }

    private static List<Row> readWithPaxos(List<ReadCommand> commands, ConsistencyLevel consistencyLevel, ClientState state)
    throws InvalidRequestException, UnavailableException, ReadTimeoutException
    {
        assert state != null;

        long start = System.nanoTime();
        List<Row> rows = null;

        try
        {
            // make sure any in-progress paxos writes are done (i.e., committed to a majority of replicas), before performing a quorum read
            if (commands.size() > 1)
                throw new InvalidRequestException("SERIAL/LOCAL_SERIAL consistency may only be requested for one row at a time");
            ReadCommand command = commands.get(0);

            CFMetaData metadata = Schema.instance.getCFMetaData(command.ksName, command.cfName);
            Pair<List<InetAddress>, Integer> p = getPaxosParticipants(command.ksName, command.key, consistencyLevel);
            List<InetAddress> liveEndpoints = p.left;
            int requiredParticipants = p.right;

            // does the work of applying in-progress writes; throws UAE or timeout if it can't
            final ConsistencyLevel consistencyForCommitOrFetch = consistencyLevel == ConsistencyLevel.LOCAL_SERIAL
                                                                                   ? ConsistencyLevel.LOCAL_QUORUM
                                                                                   : ConsistencyLevel.QUORUM;
            try
            {
                final Pair<UUID, Integer> pair = beginAndRepairPaxos(start, command.key, metadata, liveEndpoints, requiredParticipants, consistencyLevel, consistencyForCommitOrFetch, false, state);
                if (pair.right > 0)
                    casReadMetrics.contention.update(pair.right);
            }
            catch (WriteTimeoutException e)
            {
                throw new ReadTimeoutException(consistencyLevel, 0, consistencyLevel.blockFor(Keyspace.open(command.ksName)), false);
            }

            rows = fetchRows(commands, consistencyForCommitOrFetch);
        }
        catch (UnavailableException e)
        {
            readMetrics.unavailables.mark();
            ClientRequestMetrics.readUnavailables.inc();
            casReadMetrics.unavailables.mark();
            throw e;
        }
        catch (ReadTimeoutException e)
        {
            readMetrics.timeouts.mark();
            ClientRequestMetrics.readTimeouts.inc();
            casReadMetrics.timeouts.mark();
            throw e;
        }
        finally
        {
            long latency = System.nanoTime() - start;
            readMetrics.addNano(latency);
            casReadMetrics.addNano(latency);
            // TODO avoid giving every command the same latency number.  Can fix this in CASSADRA-5329
            for (ReadCommand command : commands)
                Keyspace.open(command.ksName).getColumnFamilyStore(command.cfName).metric.coordinatorReadLatency.update(latency, TimeUnit.NANOSECONDS);
        }

        return rows;
    }

    private static List<Row> readRegular(List<ReadCommand> commands, ConsistencyLevel consistencyLevel)
    throws UnavailableException, ReadTimeoutException
    {
        long start = System.nanoTime();
        List<Row> rows = null;

        try
        {
            rows = fetchRows(commands, consistencyLevel);
        }
        catch (UnavailableException e)
        {
            readMetrics.unavailables.mark();
            ClientRequestMetrics.readUnavailables.inc();
            throw e;
        }
        catch (ReadTimeoutException e)
        {
            readMetrics.timeouts.mark();
            ClientRequestMetrics.readTimeouts.inc();
            throw e;
        }
        finally
        {
            long latency = System.nanoTime() - start;
            readMetrics.addNano(latency);
            // TODO avoid giving every command the same latency number.  Can fix this in CASSADRA-5329
            for (ReadCommand command : commands)
                Keyspace.open(command.ksName).getColumnFamilyStore(command.cfName).metric.coordinatorReadLatency.update(latency, TimeUnit.NANOSECONDS);
        }

        return rows;
    }

    /**
     * This function executes local and remote reads, and blocks for the results:
     *
     * 1. Get the replica locations, sorted by response time according to the snitch
     * 2. Send a data request to the closest replica, and digest requests to either
     *    a) all the replicas, if read repair is enabled
     *    b) the closest R-1 replicas, where R is the number required to satisfy the ConsistencyLevel
     * 3. Wait for a response from R replicas
     * 4. If the digests (if any) match the data return the data
     * 5. else carry out read repair by getting data from all the nodes.
     */
    private static List<Row> fetchRows(List<ReadCommand> initialCommands, ConsistencyLevel consistencyLevel)
    throws UnavailableException, ReadTimeoutException
    {
        List<Row> rows = new ArrayList<>(initialCommands.size());
        // (avoid allocating a new list in the common case of nothing-to-retry)
        List<ReadCommand> commandsToRetry = Collections.emptyList();

        do
        {
            List<ReadCommand> commands = commandsToRetry.isEmpty() ? initialCommands : commandsToRetry;
            AbstractReadExecutor[] readExecutors = new AbstractReadExecutor[commands.size()];

            if (!commandsToRetry.isEmpty())
                Tracing.trace("Retrying {} commands", commandsToRetry.size());

            // send out read requests
            for (int i = 0; i < commands.size(); i++)
            {
                ReadCommand command = commands.get(i);
                assert !command.isDigestQuery();

                AbstractReadExecutor exec = AbstractReadExecutor.getReadExecutor(command, consistencyLevel);
                exec.executeAsync();
                readExecutors[i] = exec;
            }

            for (AbstractReadExecutor exec : readExecutors)
                exec.maybeTryAdditionalReplicas();

            // read results and make a second pass for any digest mismatches
            List<ReadCommand> repairCommands = null;
            List<ReadCallback<ReadResponse, Row>> repairResponseHandlers = null;
            for (AbstractReadExecutor exec: readExecutors)
            {
                try
                {
                    Row row = exec.get();
                    if (row != null)
                    {
                        exec.command.maybeTrim(row);
                        rows.add(row);
                    }

                    if (logger.isDebugEnabled())
                        logger.debug("Read: {} ms.", TimeUnit.NANOSECONDS.toMillis(System.nanoTime() - exec.handler.start));
                }
                catch (ReadTimeoutException ex)
                {
                    int blockFor = consistencyLevel.blockFor(Keyspace.open(exec.command.getKeyspace()));
                    int responseCount = exec.handler.getReceivedCount();
                    String gotData = responseCount > 0
                                   ? exec.resolver.isDataPresent() ? " (including data)" : " (only digests)"
                                   : "";

                    if (Tracing.isTracing())
                    {
                        Tracing.trace("Timed out; received {} of {} responses{}",
                                      new Object[]{ responseCount, blockFor, gotData });
                    }
                    else if (logger.isDebugEnabled())
                    {
                        logger.debug("Read timeout; received {} of {} responses{}", responseCount, blockFor, gotData);
                    }
                    throw ex;
                }
                catch (DigestMismatchException ex)
                {
                    Tracing.trace("Digest mismatch: {}", ex);

                    ReadRepairMetrics.repairedBlocking.mark();

                    // Do a full data read to resolve the correct response (and repair node that need be)
                    RowDataResolver resolver = new RowDataResolver(exec.command.ksName, exec.command.key, exec.command.filter(), exec.command.timestamp);
                    ReadCallback<ReadResponse, Row> repairHandler = new ReadCallback<>(resolver,
                                                                                       ConsistencyLevel.ALL,
                                                                                       exec.getContactedReplicas().size(),
                                                                                       exec.command,
                                                                                       Keyspace.open(exec.command.getKeyspace()),
                                                                                       exec.handler.endpoints);

                    if (repairCommands == null)
                    {
                        repairCommands = new ArrayList<>();
                        repairResponseHandlers = new ArrayList<>();
                    }
                    repairCommands.add(exec.command);
                    repairResponseHandlers.add(repairHandler);

                    MessageOut<ReadCommand> message = exec.command.createMessage();
                    for (InetAddress endpoint : exec.getContactedReplicas())
                    {
                        Tracing.trace("Enqueuing full data read to {}", endpoint);
                        MessagingService.instance().sendRR(message, endpoint, repairHandler);
                    }
                }
            }

            commandsToRetry.clear();

            // read the results for the digest mismatch retries
            if (repairResponseHandlers != null)
            {
                for (int i = 0; i < repairCommands.size(); i++)
                {
                    ReadCommand command = repairCommands.get(i);
                    ReadCallback<ReadResponse, Row> handler = repairResponseHandlers.get(i);

                    Row row;
                    try
                    {
                        row = handler.get();
                    }
                    catch (DigestMismatchException e)
                    {
                        throw new AssertionError(e); // full data requested from each node here, no digests should be sent
                    }
                    catch (ReadTimeoutException e)
                    {
                        if (Tracing.isTracing())
                            Tracing.trace("Timed out waiting on digest mismatch repair requests");
                        else
                            logger.debug("Timed out waiting on digest mismatch repair requests");
                        // the caught exception here will have CL.ALL from the repair command,
                        // not whatever CL the initial command was at (CASSANDRA-7947)
                        int blockFor = consistencyLevel.blockFor(Keyspace.open(command.getKeyspace()));
                        throw new ReadTimeoutException(consistencyLevel, blockFor-1, blockFor, true);
                    }

                    RowDataResolver resolver = (RowDataResolver)handler.resolver;
                    try
                    {
                        // wait for the repair writes to be acknowledged, to minimize impact on any replica that's
                        // behind on writes in case the out-of-sync row is read multiple times in quick succession
                        FBUtilities.waitOnFutures(resolver.repairResults, DatabaseDescriptor.getWriteRpcTimeout());
                    }
                    catch (TimeoutException e)
                    {
                        if (Tracing.isTracing())
                            Tracing.trace("Timed out waiting on digest mismatch repair acknowledgements");
                        else
                            logger.debug("Timed out waiting on digest mismatch repair acknowledgements");
                        int blockFor = consistencyLevel.blockFor(Keyspace.open(command.getKeyspace()));
                        throw new ReadTimeoutException(consistencyLevel, blockFor-1, blockFor, true);
                    }

                    // retry any potential short reads
                    ReadCommand retryCommand = command.maybeGenerateRetryCommand(resolver, row);
                    if (retryCommand != null)
                    {
                        Tracing.trace("Issuing retry for read command");
                        if (commandsToRetry == Collections.EMPTY_LIST)
                            commandsToRetry = new ArrayList<>();
                        commandsToRetry.add(retryCommand);
                        continue;
                    }

                    if (row != null)
                    {
                        command.maybeTrim(row);
                        rows.add(row);
                    }
                }
            }
        } while (!commandsToRetry.isEmpty());

        return rows;
    }

    static class LocalReadRunnable extends DroppableRunnable
    {
        private final ReadCommand command;
        private final ReadCallback<ReadResponse, Row> handler;
        private final long start = System.nanoTime();

        LocalReadRunnable(ReadCommand command, ReadCallback<ReadResponse, Row> handler)
        {
            super(MessagingService.Verb.READ);
            this.command = command;
            this.handler = handler;
        }

        protected void runMayThrow()
        {
            Keyspace keyspace = Keyspace.open(command.ksName);
            Row r = command.getRow(keyspace);
            ReadResponse result = ReadVerbHandler.getResponse(command, r);
            MessagingService.instance().addLatency(FBUtilities.getBroadcastAddress(), TimeUnit.NANOSECONDS.toMillis(System.nanoTime() - start));
            handler.response(result);
        }
    }

    static class LocalRangeSliceRunnable extends DroppableRunnable
    {
        private final AbstractRangeCommand command;
        private final ReadCallback<RangeSliceReply, Iterable<Row>> handler;
        private final long start = System.nanoTime();

        LocalRangeSliceRunnable(AbstractRangeCommand command, ReadCallback<RangeSliceReply, Iterable<Row>> handler)
        {
            super(MessagingService.Verb.RANGE_SLICE);
            this.command = command;
            this.handler = handler;
        }

        protected void runMayThrow()
        {
            RangeSliceReply result = new RangeSliceReply(command.executeLocally());
            MessagingService.instance().addLatency(FBUtilities.getBroadcastAddress(), TimeUnit.NANOSECONDS.toMillis(System.nanoTime() - start));
            handler.response(result);
        }
    }

    public static List<InetAddress> getLiveSortedEndpoints(Keyspace keyspace, ByteBuffer key)
    {
        return getLiveSortedEndpoints(keyspace, StorageService.getPartitioner().decorateKey(key));
    }

    private static List<InetAddress> getLiveSortedEndpoints(Keyspace keyspace, RingPosition pos)
    {
        List<InetAddress> liveEndpoints = StorageService.instance.getLiveNaturalEndpoints(keyspace, pos);
        DatabaseDescriptor.getEndpointSnitch().sortByProximity(FBUtilities.getBroadcastAddress(), liveEndpoints);
        return liveEndpoints;
    }

    private static List<InetAddress> intersection(List<InetAddress> l1, List<InetAddress> l2)
    {
        // Note: we don't use Guava Sets.intersection() for 3 reasons:
        //   1) retainAll would be inefficient if l1 and l2 are large but in practice both are the replicas for a range and
        //   so will be very small (< RF). In that case, retainAll is in fact more efficient.
        //   2) we do ultimately need a list so converting everything to sets don't make sense
        //   3) l1 and l2 are sorted by proximity. The use of retainAll  maintain that sorting in the result, while using sets wouldn't.
        List<InetAddress> inter = new ArrayList<InetAddress>(l1);
        inter.retainAll(l2);
        return inter;
    }

    /**
     * Estimate the number of result rows (either cql3 rows or storage rows, as called for by the command) per
     * range in the ring based on our local data.  This assumes that ranges are uniformly distributed across the cluster
     * and that the queried data is also uniformly distributed.
     */
    private static float estimateResultRowsPerRange(AbstractRangeCommand command, Keyspace keyspace)
    {
        ColumnFamilyStore cfs = keyspace.getColumnFamilyStore(command.columnFamily);
        float resultRowsPerRange = Float.POSITIVE_INFINITY;
        if (command.rowFilter != null && !command.rowFilter.isEmpty())
        {
            List<SecondaryIndexSearcher> searchers = cfs.indexManager.getIndexSearchersForQuery(command.rowFilter);
            if (searchers.isEmpty())
            {
                resultRowsPerRange = calculateResultRowsUsingEstimatedKeys(cfs);
            }
            else
            {
                // Secondary index query (cql3 or otherwise).  Estimate result rows based on most selective 2ary index.
                for (SecondaryIndexSearcher searcher : searchers)
                {
                    // use our own mean column count as our estimate for how many matching rows each node will have
                    SecondaryIndex highestSelectivityIndex = searcher.highestSelectivityIndex(command.rowFilter);
                    resultRowsPerRange = Math.min(resultRowsPerRange, highestSelectivityIndex.estimateResultRows());
                }
            }
        }
        else if (!command.countCQL3Rows())
        {
            // non-cql3 query
            resultRowsPerRange = cfs.estimateKeys();
        }
        else
        {
            resultRowsPerRange = calculateResultRowsUsingEstimatedKeys(cfs);
        }

        // adjust resultRowsPerRange by the number of tokens this node has and the replication factor for this ks
        return (resultRowsPerRange / DatabaseDescriptor.getNumTokens()) / keyspace.getReplicationStrategy().getReplicationFactor();
    }

    private static float calculateResultRowsUsingEstimatedKeys(ColumnFamilyStore cfs)
    {
        if (cfs.metadata.comparator.isDense())
        {
            // one storage row per result row, so use key estimate directly
            return cfs.estimateKeys();
        }
        else
        {
            float resultRowsPerStorageRow = ((float) cfs.getMeanColumns()) / cfs.metadata.regularColumns().size();
            return resultRowsPerStorageRow * (cfs.estimateKeys());
        }
    }

    public static List<Row> getRangeSlice(AbstractRangeCommand command, ConsistencyLevel consistency_level)
    throws UnavailableException, ReadTimeoutException
    {
        Tracing.trace("Computing ranges to query");
        long startTime = System.nanoTime();

        Keyspace keyspace = Keyspace.open(command.keyspace);
        List<Row> rows;
        // now scan until we have enough results
        try
        {
            int liveRowCount = 0;
            boolean countLiveRows = command.countCQL3Rows() || command.ignoredTombstonedPartitions();
            rows = new ArrayList<>();

            // when dealing with LocalStrategy keyspaces, we can skip the range splitting and merging (which can be
            // expensive in clusters with vnodes)
            List<? extends AbstractBounds<RowPosition>> ranges;
            if (keyspace.getReplicationStrategy() instanceof LocalStrategy)
                ranges = command.keyRange.unwrap();
            else
                ranges = getRestrictedRanges(command.keyRange);

            // determine the number of rows to be fetched and the concurrency factor
            int rowsToBeFetched = command.limit();
            int concurrencyFactor;
            if (command.requiresScanningAllRanges())
            {
                // all nodes must be queried
                rowsToBeFetched *= ranges.size();
                concurrencyFactor = ranges.size();
                logger.debug("Requested rows: {}, ranges.size(): {}; concurrent range requests: {}",
                             command.limit(),
                             ranges.size(),
                             concurrencyFactor);
                Tracing.trace("Submitting range requests on {} ranges with a concurrency of {}",
                              new Object[]{ ranges.size(), concurrencyFactor});
            }
            else
            {
                // our estimate of how many result rows there will be per-range
                float resultRowsPerRange = estimateResultRowsPerRange(command, keyspace);
                // underestimate how many rows we will get per-range in order to increase the likelihood that we'll
                // fetch enough rows in the first round
                resultRowsPerRange -= resultRowsPerRange * CONCURRENT_SUBREQUESTS_MARGIN;
                concurrencyFactor = resultRowsPerRange == 0.0
                                  ? 1
                                  : Math.max(1, Math.min(ranges.size(), (int) Math.ceil(command.limit() / resultRowsPerRange)));
                logger.debug("Estimated result rows per range: {}; requested rows: {}, ranges.size(): {}; concurrent range requests: {}",
                             resultRowsPerRange,
                             command.limit(),
                             ranges.size(),
                             concurrencyFactor);
                Tracing.trace("Submitting range requests on {} ranges with a concurrency of {} ({} rows per range expected)",
                              new Object[]{ ranges.size(), concurrencyFactor, resultRowsPerRange});
            }

            boolean haveSufficientRows = false;
            int i = 0;
            AbstractBounds<RowPosition> nextRange = null;
            List<InetAddress> nextEndpoints = null;
            List<InetAddress> nextFilteredEndpoints = null;
            while (i < ranges.size())
            {
                List<Pair<AbstractRangeCommand, ReadCallback<RangeSliceReply, Iterable<Row>>>> scanHandlers = new ArrayList<>(concurrencyFactor);
                int concurrentFetchStartingIndex = i;
                int concurrentRequests = 0;
                while ((i - concurrentFetchStartingIndex) < concurrencyFactor)
                {
                    AbstractBounds<RowPosition> range = nextRange == null
                                                      ? ranges.get(i)
                                                      : nextRange;
                    List<InetAddress> liveEndpoints = nextEndpoints == null
                                                    ? getLiveSortedEndpoints(keyspace, range.right)
                                                    : nextEndpoints;
                    List<InetAddress> filteredEndpoints = nextFilteredEndpoints == null
                                                        ? consistency_level.filterForQuery(keyspace, liveEndpoints)
                                                        : nextFilteredEndpoints;
                    ++i;
                    ++concurrentRequests;

                    // getRestrictedRange has broken the queried range into per-[vnode] token ranges, but this doesn't take
                    // the replication factor into account. If the intersection of live endpoints for 2 consecutive ranges
                    // still meets the CL requirements, then we can merge both ranges into the same RangeSliceCommand.
                    while (i < ranges.size())
                    {
                        nextRange = ranges.get(i);
                        nextEndpoints = getLiveSortedEndpoints(keyspace, nextRange.right);
                        nextFilteredEndpoints = consistency_level.filterForQuery(keyspace, nextEndpoints);

                        // If the current range right is the min token, we should stop merging because CFS.getRangeSlice
                        // don't know how to deal with a wrapping range.
                        // Note: it would be slightly more efficient to have CFS.getRangeSlice on the destination nodes unwraps
                        // the range if necessary and deal with it. However, we can't start sending wrapped range without breaking
                        // wire compatibility, so It's likely easier not to bother;
                        if (range.right.isMinimum())
                            break;

                        List<InetAddress> merged = intersection(liveEndpoints, nextEndpoints);

                        // Check if there is enough endpoint for the merge to be possible.
                        if (!consistency_level.isSufficientLiveNodes(keyspace, merged))
                            break;

                        List<InetAddress> filteredMerged = consistency_level.filterForQuery(keyspace, merged);

                        // Estimate whether merging will be a win or not
                        if (!DatabaseDescriptor.getEndpointSnitch().isWorthMergingForRangeQuery(filteredMerged, filteredEndpoints, nextFilteredEndpoints))
                            break;

                        // If we get there, merge this range and the next one
                        range = range.withNewRight(nextRange.right);
                        liveEndpoints = merged;
                        filteredEndpoints = filteredMerged;
                        ++i;
                    }

                    AbstractRangeCommand nodeCmd = command.forSubRange(range);

                    // collect replies and resolve according to consistency level
                    RangeSliceResponseResolver resolver = new RangeSliceResponseResolver(nodeCmd.keyspace, command.timestamp);
                    List<InetAddress> minimalEndpoints = filteredEndpoints.subList(0, Math.min(filteredEndpoints.size(), consistency_level.blockFor(keyspace)));
                    ReadCallback<RangeSliceReply, Iterable<Row>> handler = new ReadCallback<>(resolver, consistency_level, nodeCmd, minimalEndpoints);
                    handler.assureSufficientLiveNodes();
                    resolver.setSources(filteredEndpoints);
                    if (filteredEndpoints.size() == 1
                        && filteredEndpoints.get(0).equals(FBUtilities.getBroadcastAddress())
                        && OPTIMIZE_LOCAL_REQUESTS)
                    {
                        StageManager.getStage(Stage.READ).execute(new LocalRangeSliceRunnable(nodeCmd, handler), Tracing.instance.get());
                    }
                    else
                    {
                        MessageOut<? extends AbstractRangeCommand> message = nodeCmd.createMessage();
                        for (InetAddress endpoint : filteredEndpoints)
                        {
                            Tracing.trace("Enqueuing request to {}", endpoint);
                            MessagingService.instance().sendRR(message, endpoint, handler);
                        }
                    }
                    scanHandlers.add(Pair.create(nodeCmd, handler));
                }
                Tracing.trace("Submitted {} concurrent range requests covering {} ranges", concurrentRequests, i - concurrentFetchStartingIndex);

                List<AsyncOneResponse> repairResponses = new ArrayList<>();
                for (Pair<AbstractRangeCommand, ReadCallback<RangeSliceReply, Iterable<Row>>> cmdPairHandler : scanHandlers)
                {
                    ReadCallback<RangeSliceReply, Iterable<Row>> handler = cmdPairHandler.right;
                    RangeSliceResponseResolver resolver = (RangeSliceResponseResolver)handler.resolver;

                    try
                    {
                        for (Row row : handler.get())
                        {
                            rows.add(row);
                            if (countLiveRows)
                                liveRowCount += row.getLiveCount(command.predicate, command.timestamp);
                        }
                        repairResponses.addAll(resolver.repairResults);
                    }
                    catch (ReadTimeoutException ex)
                    {
                        // we timed out waiting for responses
                        int blockFor = consistency_level.blockFor(keyspace);
                        int responseCount = resolver.responses.size();
                        String gotData = responseCount > 0
                                         ? resolver.isDataPresent() ? " (including data)" : " (only digests)"
                                         : "";

                        if (Tracing.isTracing())
                        {
                            Tracing.trace("Timed out; received {} of {} responses{} for range {} of {}",
                                          new Object[]{ responseCount, blockFor, gotData, i, ranges.size() });
                        }
                        else if (logger.isDebugEnabled())
                        {
                            logger.debug("Range slice timeout; received {} of {} responses{} for range {} of {}",
                                         responseCount, blockFor, gotData, i, ranges.size());
                        }
                        throw ex;
                    }
                    catch (DigestMismatchException e)
                    {
                        throw new AssertionError(e); // no digests in range slices yet
                    }

                    // if we're done, great, otherwise, move to the next range
                    int count = countLiveRows ? liveRowCount : rows.size();
                    if (count >= rowsToBeFetched)
                    {
                        haveSufficientRows = true;
                        break;
                    }
                }

                try
                {
                    FBUtilities.waitOnFutures(repairResponses, DatabaseDescriptor.getWriteRpcTimeout());
                }
                catch (TimeoutException ex)
                {
                    // We got all responses, but timed out while repairing
                    int blockFor = consistency_level.blockFor(keyspace);
                    if (Tracing.isTracing())
                        Tracing.trace("Timed out while read-repairing after receiving all {} data and digest responses", blockFor);
                    else
                        logger.debug("Range slice timeout while read-repairing after receiving all {} data and digest responses", blockFor);
                    throw new ReadTimeoutException(consistency_level, blockFor-1, blockFor, true);
                }

                if (haveSufficientRows)
                    return command.postReconciliationProcessing(rows);

                // we didn't get enough rows in our concurrent fetch; recalculate our concurrency factor
                // based on the results we've seen so far (as long as we still have ranges left to query)
                if (i < ranges.size())
                {
                    float fetchedRows = countLiveRows ? liveRowCount : rows.size();
                    float remainingRows = rowsToBeFetched - fetchedRows;
                    float actualRowsPerRange;
                    if (fetchedRows == 0.0)
                    {
                        // we haven't actually gotten any results, so query all remaining ranges at once
                        actualRowsPerRange = 0.0f;
                        concurrencyFactor = ranges.size() - i;
                    }
                    else
                    {
                        actualRowsPerRange = fetchedRows / i;
                        concurrencyFactor = Math.max(1, Math.min(ranges.size() - i, Math.round(remainingRows / actualRowsPerRange)));
                    }
                    logger.debug("Didn't get enough response rows; actual rows per range: {}; remaining rows: {}, new concurrent requests: {}",
                                 actualRowsPerRange, (int) remainingRows, concurrencyFactor);
                }
            }
        }
        finally
        {
            long latency = System.nanoTime() - startTime;
            rangeMetrics.addNano(latency);
            Keyspace.open(command.keyspace).getColumnFamilyStore(command.columnFamily).metric.coordinatorScanLatency.update(latency, TimeUnit.NANOSECONDS);
        }
        return command.postReconciliationProcessing(rows);
    }

    public Map<String, List<String>> getSchemaVersions()
    {
        return describeSchemaVersions();
    }

    /**
     * initiate a request/response session with each live node to check whether or not everybody is using the same
     * migration id. This is useful for determining if a schema change has propagated through the cluster. Disagreement
     * is assumed if any node fails to respond.
     */
    public static Map<String, List<String>> describeSchemaVersions()
    {
        final String myVersion = Schema.instance.getVersion().toString();
        final Map<InetAddress, UUID> versions = new ConcurrentHashMap<InetAddress, UUID>();
        final Set<InetAddress> liveHosts = Gossiper.instance.getLiveMembers();
        final CountDownLatch latch = new CountDownLatch(liveHosts.size());

        IAsyncCallback<UUID> cb = new IAsyncCallback<UUID>()
        {
            public void response(MessageIn<UUID> message)
            {
                // record the response from the remote node.
                versions.put(message.from, message.payload);
                latch.countDown();
            }

            public boolean isLatencyForSnitch()
            {
                return false;
            }
        };
        // an empty message acts as a request to the SchemaCheckVerbHandler.
        MessageOut message = new MessageOut(MessagingService.Verb.SCHEMA_CHECK);
        for (InetAddress endpoint : liveHosts)
            MessagingService.instance().sendRR(message, endpoint, cb);

        try
        {
            // wait for as long as possible. timeout-1s if possible.
            latch.await(DatabaseDescriptor.getRpcTimeout(), TimeUnit.MILLISECONDS);
        }
        catch (InterruptedException ex)
        {
            throw new AssertionError("This latch shouldn't have been interrupted.");
        }

        // maps versions to hosts that are on that version.
        Map<String, List<String>> results = new HashMap<String, List<String>>();
        Iterable<InetAddress> allHosts = Iterables.concat(Gossiper.instance.getLiveMembers(), Gossiper.instance.getUnreachableMembers());
        for (InetAddress host : allHosts)
        {
            UUID version = versions.get(host);
            String stringVersion = version == null ? UNREACHABLE : version.toString();
            List<String> hosts = results.get(stringVersion);
            if (hosts == null)
            {
                hosts = new ArrayList<String>();
                results.put(stringVersion, hosts);
            }
            hosts.add(host.getHostAddress());
        }

        // we're done: the results map is ready to return to the client.  the rest is just debug logging:
        if (results.get(UNREACHABLE) != null)
            logger.debug("Hosts not in agreement. Didn't get a response from everybody: {}", StringUtils.join(results.get(UNREACHABLE), ","));
        for (Map.Entry<String, List<String>> entry : results.entrySet())
        {
            // check for version disagreement. log the hosts that don't agree.
            if (entry.getKey().equals(UNREACHABLE) || entry.getKey().equals(myVersion))
                continue;
            for (String host : entry.getValue())
                logger.debug("{} disagrees ({})", host, entry.getKey());
        }
        if (results.size() == 1)
            logger.debug("Schemas are in agreement.");

        return results;
    }

    /**
     * Compute all ranges we're going to query, in sorted order. Nodes can be replica destinations for many ranges,
     * so we need to restrict each scan to the specific range we want, or else we'd get duplicate results.
     */
    static <T extends RingPosition<T>> List<AbstractBounds<T>> getRestrictedRanges(final AbstractBounds<T> queryRange)
    {
        // special case for bounds containing exactly 1 (non-minimum) token
        if (queryRange instanceof Bounds && queryRange.left.equals(queryRange.right) && !queryRange.left.isMinimum(StorageService.getPartitioner()))
        {
            return Collections.singletonList(queryRange);
        }

        TokenMetadata tokenMetadata = StorageService.instance.getTokenMetadata();

        List<AbstractBounds<T>> ranges = new ArrayList<AbstractBounds<T>>();
        // divide the queryRange into pieces delimited by the ring and minimum tokens
        Iterator<Token> ringIter = TokenMetadata.ringIterator(tokenMetadata.sortedTokens(), queryRange.left.getToken(), true);
        AbstractBounds<T> remainder = queryRange;
        while (ringIter.hasNext())
        {
            /*
             * remainder can be a range/bounds of token _or_ keys and we want to split it with a token:
             *   - if remainder is tokens, then we'll just split using the provided token.
             *   - if remainder is keys, we want to split using token.upperBoundKey. For instance, if remainder
             *     is [DK(10, 'foo'), DK(20, 'bar')], and we have 3 nodes with tokens 0, 15, 30. We want to
             *     split remainder to A=[DK(10, 'foo'), 15] and B=(15, DK(20, 'bar')]. But since we can't mix
             *     tokens and keys at the same time in a range, we uses 15.upperBoundKey() to have A include all
             *     keys having 15 as token and B include none of those (since that is what our node owns).
             * asSplitValue() abstracts that choice.
             */
            Token upperBoundToken = ringIter.next();
            T upperBound = (T)upperBoundToken.upperBound(queryRange.left.getClass());
            if (!remainder.left.equals(upperBound) && !remainder.contains(upperBound))
                // no more splits
                break;
            Pair<AbstractBounds<T>,AbstractBounds<T>> splits = remainder.split(upperBound);
            if (splits == null)
                continue;

            ranges.add(splits.left);
            remainder = splits.right;
        }
        ranges.add(remainder);

        return ranges;
    }

    public long getReadOperations()
    {
        return readMetrics.latency.count();
    }

    public long getTotalReadLatencyMicros()
    {
        return readMetrics.totalLatency.count();
    }

    public double getRecentReadLatencyMicros()
    {
        return readMetrics.getRecentLatency();
    }

    public long[] getTotalReadLatencyHistogramMicros()
    {
        return readMetrics.totalLatencyHistogram.getBuckets(false);
    }

    public long[] getRecentReadLatencyHistogramMicros()
    {
        return readMetrics.recentLatencyHistogram.getBuckets(true);
    }

    public long getRangeOperations()
    {
        return rangeMetrics.latency.count();
    }

    public long getTotalRangeLatencyMicros()
    {
        return rangeMetrics.totalLatency.count();
    }

    public double getRecentRangeLatencyMicros()
    {
        return rangeMetrics.getRecentLatency();
    }

    public long[] getTotalRangeLatencyHistogramMicros()
    {
        return rangeMetrics.totalLatencyHistogram.getBuckets(false);
    }

    public long[] getRecentRangeLatencyHistogramMicros()
    {
        return rangeMetrics.recentLatencyHistogram.getBuckets(true);
    }

    public long getWriteOperations()
    {
        return writeMetrics.latency.count();
    }

    public long getTotalWriteLatencyMicros()
    {
        return writeMetrics.totalLatency.count();
    }

    public double getRecentWriteLatencyMicros()
    {
        return writeMetrics.getRecentLatency();
    }

    public long[] getTotalWriteLatencyHistogramMicros()
    {
        return writeMetrics.totalLatencyHistogram.getBuckets(false);
    }

    public long[] getRecentWriteLatencyHistogramMicros()
    {
        return writeMetrics.recentLatencyHistogram.getBuckets(true);
    }

    public boolean getHintedHandoffEnabled()
    {
        return DatabaseDescriptor.hintedHandoffEnabled();
    }

    public Set<String> getHintedHandoffEnabledByDC()
    {
        return DatabaseDescriptor.hintedHandoffEnabledByDC();
    }

    public void setHintedHandoffEnabled(boolean b)
    {
        DatabaseDescriptor.setHintedHandoffEnabled(b);
    }

    public void setHintedHandoffEnabledByDCList(String dcNames)
    {
        DatabaseDescriptor.setHintedHandoffEnabled(dcNames);
    }

    public int getMaxHintWindow()
    {
        return DatabaseDescriptor.getMaxHintWindow();
    }

    public void setMaxHintWindow(int ms)
    {
        DatabaseDescriptor.setMaxHintWindow(ms);
    }

    public static boolean shouldHint(InetAddress ep)
    {
        if (DatabaseDescriptor.shouldHintByDC())
        {
            final String dc = DatabaseDescriptor.getEndpointSnitch().getDatacenter(ep);
            //Disable DC specific hints
            if(!DatabaseDescriptor.hintedHandoffEnabled(dc))
            {
                HintedHandOffManager.instance.metrics.incrPastWindow(ep);
                return false;
            }
        }
        else if (!DatabaseDescriptor.hintedHandoffEnabled())
        {
            HintedHandOffManager.instance.metrics.incrPastWindow(ep);
            return false;
        }

        boolean hintWindowExpired = Gossiper.instance.getEndpointDowntime(ep) > DatabaseDescriptor.getMaxHintWindow();
        if (hintWindowExpired)
        {
            HintedHandOffManager.instance.metrics.incrPastWindow(ep);
            Tracing.trace("Not hinting {} which has been down {}ms", ep, Gossiper.instance.getEndpointDowntime(ep));
        }
        return !hintWindowExpired;
    }

    /**
     * Performs the truncate operatoin, which effectively deletes all data from
     * the column family cfname
     * @param keyspace
     * @param cfname
     * @throws UnavailableException If some of the hosts in the ring are down.
     * @throws TimeoutException
     * @throws IOException
     */
    public static void truncateBlocking(String keyspace, String cfname) throws UnavailableException, TimeoutException, IOException
    {
        logger.debug("Starting a blocking truncate operation on keyspace {}, CF {}", keyspace, cfname);
        if (isAnyStorageHostDown())
        {
            logger.info("Cannot perform truncate, some hosts are down");
            // Since the truncate operation is so aggressive and is typically only
            // invoked by an admin, for simplicity we require that all nodes are up
            // to perform the operation.
            int liveMembers = Gossiper.instance.getLiveMembers().size();
            throw new UnavailableException(ConsistencyLevel.ALL, liveMembers + Gossiper.instance.getUnreachableMembers().size(), liveMembers);
        }

        Set<InetAddress> allEndpoints = Gossiper.instance.getLiveTokenOwners();
        
        int blockFor = allEndpoints.size();
        final TruncateResponseHandler responseHandler = new TruncateResponseHandler(blockFor);

        // Send out the truncate calls and track the responses with the callbacks.
        Tracing.trace("Enqueuing truncate messages to hosts {}", allEndpoints);
        final Truncation truncation = new Truncation(keyspace, cfname);
        MessageOut<Truncation> message = truncation.createMessage();
        for (InetAddress endpoint : allEndpoints)
            MessagingService.instance().sendRR(message, endpoint, responseHandler);

        // Wait for all
        try
        {
            responseHandler.get();
        }
        catch (TimeoutException e)
        {
            Tracing.trace("Timed out");
            throw e;
        }
    }

    /**
     * Asks the gossiper if there are any nodes that are currently down.
     * @return true if the gossiper thinks all nodes are up.
     */
    private static boolean isAnyStorageHostDown()
    {
        return !Gossiper.instance.getUnreachableTokenOwners().isEmpty();
    }
    
    public interface WritePerformer
    {
        public void apply(IMutation mutation,
                          Iterable<InetAddress> targets,
                          AbstractWriteResponseHandler responseHandler,
                          String localDataCenter,
                          ConsistencyLevel consistencyLevel) throws OverloadedException;
    }

    /**
     * A Runnable that aborts if it doesn't start running before it times out
     */
    private static abstract class DroppableRunnable implements Runnable
    {
        private final long constructionTime = System.nanoTime();
        private final MessagingService.Verb verb;

        public DroppableRunnable(MessagingService.Verb verb)
        {
            this.verb = verb;
        }

        public final void run()
        {

            if (TimeUnit.NANOSECONDS.toMillis(System.nanoTime() - constructionTime) > DatabaseDescriptor.getTimeout(verb))
            {
                MessagingService.instance().incrementDroppedMessages(verb);
                return;
            }
            try
            {
                runMayThrow();
            } catch (Exception e)
            {
                throw new RuntimeException(e);
            }
        }

        abstract protected void runMayThrow() throws Exception;
    }

    /**
     * Like DroppableRunnable, but if it aborts, it will rerun (on the mutation stage) after
     * marking itself as a hint in progress so that the hint backpressure mechanism can function.
     */
    private static abstract class LocalMutationRunnable implements Runnable
    {
        private final long constructionTime = System.currentTimeMillis();

        public final void run()
        {
            if (System.currentTimeMillis() > constructionTime + DatabaseDescriptor.getTimeout(MessagingService.Verb.MUTATION))
            {
                MessagingService.instance().incrementDroppedMessages(MessagingService.Verb.MUTATION);
                HintRunnable runnable = new HintRunnable(FBUtilities.getBroadcastAddress())
                {
                    protected void runMayThrow() throws Exception
                    {
                        LocalMutationRunnable.this.runMayThrow();
                    }
                };
                submitHint(runnable);
                return;
            }

            try
            {
                runMayThrow();
            }
            catch (Exception e)
            {
                throw new RuntimeException(e);
            }
        }

        abstract protected void runMayThrow() throws Exception;
    }

    /**
     * HintRunnable will decrease totalHintsInProgress and targetHints when finished.
     * It is the caller's responsibility to increment them initially.
     */
    private abstract static class HintRunnable implements Runnable
    {
        public final InetAddress target;

        protected HintRunnable(InetAddress target)
        {
            this.target = target;
        }

        public void run()
        {
            try
            {
                runMayThrow();
            }
            catch (Exception e)
            {
                throw new RuntimeException(e);
            }
            finally
            {
                StorageMetrics.totalHintsInProgress.dec();
                getHintsInProgressFor(target).decrementAndGet();
            }
        }

        abstract protected void runMayThrow() throws Exception;
    }

    public long getTotalHints()
    {
        return StorageMetrics.totalHints.count();
    }

    public int getMaxHintsInProgress()
    {
        return maxHintsInProgress;
    }

    public void setMaxHintsInProgress(int qs)
    {
        maxHintsInProgress = qs;
    }

    public int getHintsInProgress()
    {
        return (int) StorageMetrics.totalHintsInProgress.count();
    }

    public void verifyNoHintsInProgress()
    {
        if (getHintsInProgress() > 0)
            logger.warn("Some hints were not written before shutdown.  This is not supposed to happen.  You should (a) run repair, and (b) file a bug report");
    }

    public Long getRpcTimeout() { return DatabaseDescriptor.getRpcTimeout(); }
    public void setRpcTimeout(Long timeoutInMillis) { DatabaseDescriptor.setRpcTimeout(timeoutInMillis); }

    public Long getReadRpcTimeout() { return DatabaseDescriptor.getReadRpcTimeout(); }
    public void setReadRpcTimeout(Long timeoutInMillis) { DatabaseDescriptor.setReadRpcTimeout(timeoutInMillis); }

    public Long getWriteRpcTimeout() { return DatabaseDescriptor.getWriteRpcTimeout(); }
    public void setWriteRpcTimeout(Long timeoutInMillis) { DatabaseDescriptor.setWriteRpcTimeout(timeoutInMillis); }

    public Long getCounterWriteRpcTimeout() { return DatabaseDescriptor.getCounterWriteRpcTimeout(); }
    public void setCounterWriteRpcTimeout(Long timeoutInMillis) { DatabaseDescriptor.setCounterWriteRpcTimeout(timeoutInMillis); }

    public Long getCasContentionTimeout() { return DatabaseDescriptor.getCasContentionTimeout(); }
    public void setCasContentionTimeout(Long timeoutInMillis) { DatabaseDescriptor.setCasContentionTimeout(timeoutInMillis); }

    public Long getRangeRpcTimeout() { return DatabaseDescriptor.getRangeRpcTimeout(); }
    public void setRangeRpcTimeout(Long timeoutInMillis) { DatabaseDescriptor.setRangeRpcTimeout(timeoutInMillis); }

    public Long getTruncateRpcTimeout() { return DatabaseDescriptor.getTruncateRpcTimeout(); }
    public void setTruncateRpcTimeout(Long timeoutInMillis) { DatabaseDescriptor.setTruncateRpcTimeout(timeoutInMillis); }

    public Long getNativeTransportMaxConcurrentConnections() { return DatabaseDescriptor.getNativeTransportMaxConcurrentConnections(); }
    public void setNativeTransportMaxConcurrentConnections(Long nativeTransportMaxConcurrentConnections) { DatabaseDescriptor.setNativeTransportMaxConcurrentConnections(nativeTransportMaxConcurrentConnections); }

    public Long getNativeTransportMaxConcurrentConnectionsPerIp() { return DatabaseDescriptor.getNativeTransportMaxConcurrentConnectionsPerIp(); }
    public void setNativeTransportMaxConcurrentConnectionsPerIp(Long nativeTransportMaxConcurrentConnections) { DatabaseDescriptor.setNativeTransportMaxConcurrentConnectionsPerIp(nativeTransportMaxConcurrentConnections); }

    public void reloadTriggerClasses() { TriggerExecutor.instance.reloadClasses(); }

    public long getReadRepairAttempted() {
        return ReadRepairMetrics.attempted.count();
    }
    
    public long getReadRepairRepairedBlocking() {
        return ReadRepairMetrics.repairedBlocking.count();
    }
    
    public long getReadRepairRepairedBackground() {
        return ReadRepairMetrics.repairedBackground.count();
    }
}


File: src/java/org/apache/cassandra/utils/UUIDGen.java
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

import java.net.InetAddress;
import java.nio.ByteBuffer;
import java.security.MessageDigest;
import java.security.NoSuchAlgorithmException;
import java.util.Collection;
import java.util.Random;
import java.util.UUID;

import com.google.common.annotations.VisibleForTesting;


/**
 * The goods are here: www.ietf.org/rfc/rfc4122.txt.
 */
public class UUIDGen
{
    // A grand day! millis at 00:00:00.000 15 Oct 1582.
    private static final long START_EPOCH = -12219292800000L;
    private static final long clockSeqAndNode = makeClockSeqAndNode();

    /*
     * The min and max possible lsb for a UUID.
     * Note that his is not 0 and all 1's because Cassandra TimeUUIDType
     * compares the lsb parts as a signed byte array comparison. So the min
     * value is 8 times -128 and the max is 8 times +127.
     *
     * Note that we ignore the uuid variant (namely, MIN_CLOCK_SEQ_AND_NODE
     * have variant 2 as it should, but MAX_CLOCK_SEQ_AND_NODE have variant 0).
     * I don't think that has any practical consequence and is more robust in
     * case someone provides a UUID with a broken variant.
     */
    private static final long MIN_CLOCK_SEQ_AND_NODE = 0x8080808080808080L;
    private static final long MAX_CLOCK_SEQ_AND_NODE = 0x7f7f7f7f7f7f7f7fL;

    // placement of this singleton is important.  It needs to be instantiated *AFTER* the other statics.
    private static final UUIDGen instance = new UUIDGen();

    private long lastNanos;

    private UUIDGen()
    {
        // make sure someone didn't whack the clockSeqAndNode by changing the order of instantiation.
        if (clockSeqAndNode == 0) throw new RuntimeException("singleton instantiation is misplaced.");
    }

    /**
     * Creates a type 1 UUID (time-based UUID).
     *
     * @return a UUID instance
     */
    public static UUID getTimeUUID()
    {
        return new UUID(instance.createTimeSafe(), clockSeqAndNode);
    }

    /**
     * Creates a type 1 UUID (time-based UUID) with the timestamp of @param when, in milliseconds.
     *
     * @return a UUID instance
     */
    public static UUID getTimeUUID(long when)
    {
        return new UUID(createTime(fromUnixTimestamp(when)), clockSeqAndNode);
    }

    @VisibleForTesting
    public static UUID getTimeUUID(long when, long clockSeqAndNode)
    {
        return new UUID(createTime(fromUnixTimestamp(when)), clockSeqAndNode);
    }

    /** creates a type 1 uuid from raw bytes. */
    public static UUID getUUID(ByteBuffer raw)
    {
        return new UUID(raw.getLong(raw.position()), raw.getLong(raw.position() + 8));
    }

    /** decomposes a uuid into raw bytes. */
    public static byte[] decompose(UUID uuid)
    {
        long most = uuid.getMostSignificantBits();
        long least = uuid.getLeastSignificantBits();
        byte[] b = new byte[16];
        for (int i = 0; i < 8; i++)
        {
            b[i] = (byte)(most >>> ((7-i) * 8));
            b[8+i] = (byte)(least >>> ((7-i) * 8));
        }
        return b;
    }

    /**
     * Returns a 16 byte representation of a type 1 UUID (a time-based UUID),
     * based on the current system time.
     *
     * @return a type 1 UUID represented as a byte[]
     */
    public static byte[] getTimeUUIDBytes()
    {
        return createTimeUUIDBytes(instance.createTimeSafe());
    }

    /**
     * Returns the smaller possible type 1 UUID having the provided timestamp.
     *
     * <b>Warning:</b> this method should only be used for querying as this
     * doesn't at all guarantee the uniqueness of the resulting UUID.
     */
    public static UUID minTimeUUID(long timestamp)
    {
        return new UUID(createTime(fromUnixTimestamp(timestamp)), MIN_CLOCK_SEQ_AND_NODE);
    }

    /**
     * Returns the biggest possible type 1 UUID having the provided timestamp.
     *
     * <b>Warning:</b> this method should only be used for querying as this
     * doesn't at all guarantee the uniqueness of the resulting UUID.
     */
    public static UUID maxTimeUUID(long timestamp)
    {
        // unix timestamp are milliseconds precision, uuid timestamp are 100's
        // nanoseconds precision. If we ask for the biggest uuid have unix
        // timestamp 1ms, then we should not extend 100's nanoseconds
        // precision by taking 10000, but rather 19999.
        long uuidTstamp = fromUnixTimestamp(timestamp + 1) - 1;
        return new UUID(createTime(uuidTstamp), MAX_CLOCK_SEQ_AND_NODE);
    }

    /**
     * @param uuid
     * @return milliseconds since Unix epoch
     */
    public static long unixTimestamp(UUID uuid)
    {
        return (uuid.timestamp() / 10000) + START_EPOCH;
    }

    /**
     * @param uuid
     * @return microseconds since Unix epoch
     */
    public static long microsTimestamp(UUID uuid)
    {
        return (uuid.timestamp() / 10) + START_EPOCH * 1000;
    }

    /**
     * @param timestamp milliseconds since Unix epoch
     * @return
     */
    private static long fromUnixTimestamp(long timestamp) {
        return (timestamp - START_EPOCH) * 10000;
    }

    /**
     * Converts a milliseconds-since-epoch timestamp into the 16 byte representation
     * of a type 1 UUID (a time-based UUID).
     *
     * <p><i><b>Deprecated:</b> This method goes again the principle of a time
     * UUID and should not be used. For queries based on timestamp, minTimeUUID() and
     * maxTimeUUID() can be used but this method has questionable usefulness. This is
     * only kept because CQL2 uses it (see TimeUUID.fromStringCQL2) and we
     * don't want to break compatibility.</i></p>
     *
     * <p><i><b>Warning:</b> This method is not guaranteed to return unique UUIDs; Multiple
     * invocations using identical timestamps will result in identical UUIDs.</i></p>
     *
     * @param timeMillis
     * @return a type 1 UUID represented as a byte[]
     */
    public static byte[] getTimeUUIDBytes(long timeMillis)
    {
        return createTimeUUIDBytes(instance.createTimeUnsafe(timeMillis));
    }

    /**
     * Converts a 100-nanoseconds precision timestamp into the 16 byte representation
     * of a type 1 UUID (a time-based UUID).
     *
     * To specify a 100-nanoseconds precision timestamp, one should provide a milliseconds timestamp and
     * a number 0 <= n < 10000 such that n*100 is the number of nanoseconds within that millisecond.
     *
     * <p><i><b>Warning:</b> This method is not guaranteed to return unique UUIDs; Multiple
     * invocations using identical timestamps will result in identical UUIDs.</i></p>
     *
     * @return a type 1 UUID represented as a byte[]
     */
    public static byte[] getTimeUUIDBytes(long timeMillis, int nanos)
    {
        if (nanos >= 10000)
            throw new IllegalArgumentException();
        return createTimeUUIDBytes(instance.createTimeUnsafe(timeMillis, nanos));
    }

    private static byte[] createTimeUUIDBytes(long msb)
    {
        long lsb = clockSeqAndNode;
        byte[] uuidBytes = new byte[16];

        for (int i = 0; i < 8; i++)
            uuidBytes[i] = (byte) (msb >>> 8 * (7 - i));

        for (int i = 8; i < 16; i++)
            uuidBytes[i] = (byte) (lsb >>> 8 * (7 - i));

        return uuidBytes;
    }

    /**
     * Returns a milliseconds-since-epoch value for a type-1 UUID.
     *
     * @param uuid a type-1 (time-based) UUID
     * @return the number of milliseconds since the unix epoch
     * @throws IllegalArgumentException if the UUID is not version 1
     */
    public static long getAdjustedTimestamp(UUID uuid)
    {
        if (uuid.version() != 1)
            throw new IllegalArgumentException("incompatible with uuid version: "+uuid.version());
        return (uuid.timestamp() / 10000) + START_EPOCH;
    }

    private static long makeClockSeqAndNode()
    {
        long clock = new Random(System.currentTimeMillis()).nextLong();

        long lsb = 0;
        lsb |= 0x8000000000000000L;                 // variant (2 bits)
        lsb |= (clock & 0x0000000000003FFFL) << 48; // clock sequence (14 bits)
        lsb |= makeNode();                          // 6 bytes
        return lsb;
    }

    // needs to return two different values for the same when.
    // we can generate at most 10k UUIDs per ms.
    private synchronized long createTimeSafe()
    {
        long nanosSince = (System.currentTimeMillis() - START_EPOCH) * 10000;
        if (nanosSince > lastNanos)
            lastNanos = nanosSince;
        else
            nanosSince = ++lastNanos;

        return createTime(nanosSince);
    }

    /** @param when time in milliseconds */
    private long createTimeUnsafe(long when)
    {
        return createTimeUnsafe(when, 0);
    }

    private long createTimeUnsafe(long when, int nanos)
    {
        long nanosSince = ((when - START_EPOCH) * 10000) + nanos;
        return createTime(nanosSince);
    }

    private static long createTime(long nanosSince)
    {
        long msb = 0L;
        msb |= (0x00000000ffffffffL & nanosSince) << 32;
        msb |= (0x0000ffff00000000L & nanosSince) >>> 16;
        msb |= (0xffff000000000000L & nanosSince) >>> 48;
        msb |= 0x0000000000001000L; // sets the version to 1.
        return msb;
    }

    private static long makeNode()
    {
       /*
        * We don't have access to the MAC address but need to generate a node part
        * that identify this host as uniquely as possible.
        * The spec says that one option is to take as many source that identify
        * this node as possible and hash them together. That's what we do here by
        * gathering all the ip of this host.
        * Note that FBUtilities.getBroadcastAddress() should be enough to uniquely
        * identify the node *in the cluster* but it triggers DatabaseDescriptor
        * instanciation and the UUID generator is used in Stress for instance,
        * where we don't want to require the yaml.
        */
        Collection<InetAddress> localAddresses = FBUtilities.getAllLocalAddresses();
        if (localAddresses.isEmpty())
            throw new RuntimeException("Cannot generate the node component of the UUID because cannot retrieve any IP addresses.");

        // ideally, we'd use the MAC address, but java doesn't expose that.
        byte[] hash = hash(localAddresses);
        long node = 0;
        for (int i = 0; i < Math.min(6, hash.length); i++)
            node |= (0x00000000000000ff & (long)hash[i]) << (5-i)*8;
        assert (0xff00000000000000L & node) == 0;

        // Since we don't use the mac address, the spec says that multicast
        // bit (least significant bit of the first octet of the node ID) must be 1.
        return node | 0x0000010000000000L;
    }

    private static byte[] hash(Collection<InetAddress> data)
    {
        try
        {
            MessageDigest messageDigest = MessageDigest.getInstance("MD5");
            for(InetAddress addr : data)
                messageDigest.update(addr.getAddress());

            return messageDigest.digest();
        }
        catch (NoSuchAlgorithmException nsae)
        {
            throw new RuntimeException("MD5 digest algorithm is not available", nsae);
        }
    }
}

// for the curious, here is how I generated START_EPOCH
//        Calendar c = Calendar.getInstance(TimeZone.getTimeZone("GMT-0"));
//        c.set(Calendar.YEAR, 1582);
//        c.set(Calendar.MONTH, Calendar.OCTOBER);
//        c.set(Calendar.DAY_OF_MONTH, 15);
//        c.set(Calendar.HOUR_OF_DAY, 0);
//        c.set(Calendar.MINUTE, 0);
//        c.set(Calendar.SECOND, 0);
//        c.set(Calendar.MILLISECOND, 0);
//        long START_EPOCH = c.getTimeInMillis();


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
import java.nio.ByteBuffer;
import java.util.*;
import java.util.concurrent.CountDownLatch;
import java.util.concurrent.ExecutionException;
import java.util.concurrent.TimeUnit;
import java.util.concurrent.atomic.AtomicInteger;

import com.google.common.base.Objects;
import com.google.common.collect.ImmutableSet;
import org.junit.AfterClass;
import org.junit.After;
import org.junit.Assert;
import org.junit.BeforeClass;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import org.apache.cassandra.SchemaLoader;
import org.apache.cassandra.concurrent.ScheduledExecutors;
import org.apache.cassandra.config.CFMetaData;
import org.apache.cassandra.config.Schema;
import org.apache.cassandra.db.Directories;
import org.apache.cassandra.db.Keyspace;
import org.apache.cassandra.db.marshal.*;
import org.apache.cassandra.exceptions.*;
import org.apache.cassandra.io.util.FileUtils;
import org.apache.cassandra.serializers.TypeSerializer;

/**
 * Base class for CQL tests.
 */
public abstract class CQLTester
{
    protected static final Logger logger = LoggerFactory.getLogger(CQLTester.class);

    public static final String KEYSPACE = "cql_test_keyspace";
    private static final boolean USE_PREPARED_VALUES = Boolean.valueOf(System.getProperty("cassandra.test.use_prepared", "true"));
    private static final AtomicInteger seqNumber = new AtomicInteger();

    static
    {
        // Once per-JVM is enough
        SchemaLoader.prepareServer();
    }

    private List<String> tables = new ArrayList<>();
    private List<String> types = new ArrayList<>();

    @BeforeClass
    public static void setUpClass() throws Throwable
    {
        schemaChange(String.format("CREATE KEYSPACE IF NOT EXISTS %s WITH replication = {'class': 'SimpleStrategy', 'replication_factor': '1'}", KEYSPACE));
    }

    @AfterClass
    public static void tearDownClass()
    {
    }

    @After
    public void afterTest() throws Throwable
    {
        final List<String> tablesToDrop = copy(tables);
        final List<String> typesToDrop = copy(types);
        tables = null;
        types = null;

        // We want to clean up after the test, but dropping a table is rather long so just do that asynchronously
        ScheduledExecutors.optionalTasks.execute(new Runnable()
        {
            public void run()
            {
                try
                {
                    for (int i = tablesToDrop.size() - 1; i >=0; i--)
                        schemaChange(String.format("DROP TABLE IF EXISTS %s.%s", KEYSPACE, tablesToDrop.get(i)));

                    for (int i = typesToDrop.size() - 1; i >=0; i--)
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

    /**
     * Returns a copy of the specified list.
     * @return a copy of the specified list.
     */
    private static List<String> copy(List<String> list)
    {
        return list.isEmpty() ? Collections.<String>emptyList() : new ArrayList<>(list);
    }

    public void flush()
    {
        try
        {
            String currentTable = currentTable();
            if (currentTable != null)
                Keyspace.open(KEYSPACE).getColumnFamilyStore(currentTable).forceFlush().get();
        }
        catch (InterruptedException e)
        {
            throw new RuntimeException(e);
        }
        catch (ExecutionException e)
        {
            throw new RuntimeException(e);
        }
    }

    public boolean usePrepared()
    {
        return USE_PREPARED_VALUES;
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
            if (filename.contains(tables.get(i)))
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

    protected String createType(String query)
    {
        String typeName = "type_" + seqNumber.getAndIncrement();
        String fullQuery = String.format(query, KEYSPACE + "." + typeName);
        types.add(typeName);
        logger.info(fullQuery);
        schemaChange(fullQuery);
        return typeName;
    }

    protected String createTable(String query)
    {
        String currentTable = "table_" + seqNumber.getAndIncrement();
        tables.add(currentTable);
        String fullQuery = String.format(query, KEYSPACE + "." + currentTable);
        logger.info(fullQuery);
        schemaChange(fullQuery);
        return currentTable;
    }

    protected void createTableMayThrow(String query) throws Throwable
    {
        String currentTable = "table_" + seqNumber.getAndIncrement();
        tables.add(currentTable);
        String fullQuery = String.format(query, KEYSPACE + "." + currentTable);
        logger.info(fullQuery);
        try
        {
            QueryProcessor.executeOnceInternal(fullQuery);
        }
        catch (RuntimeException ex)
        {
            throw ex.getCause();
        }
    }

    protected void alterTable(String query)
    {
        String fullQuery = String.format(query, KEYSPACE + "." + currentTable());
        logger.info(fullQuery);
        schemaChange(fullQuery);
    }

    protected void alterTableMayThrow(String query) throws Throwable
    {
        String fullQuery = String.format(query, KEYSPACE + "." + currentTable());
        logger.info(fullQuery);
        try
        {
            QueryProcessor.executeOnceInternal(fullQuery);
        }
        catch (RuntimeException ex)
        {
            throw ex.getCause();
        }
    }

    protected void dropTable(String query)
    {
        String fullQuery = String.format(query, KEYSPACE + "." + currentTable());
        logger.info(fullQuery);
        schemaChange(fullQuery);
    }

    protected void createIndex(String query)
    {
        String fullQuery = String.format(query, KEYSPACE + "." + currentTable());
        logger.info(fullQuery);
        schemaChange(fullQuery);
    }

    protected void createIndexMayThrow(String query) throws Throwable
    {
        String fullQuery = String.format(query, KEYSPACE + "." + currentTable());
        logger.info(fullQuery);
        try
        {
            QueryProcessor.executeOnceInternal(fullQuery);
        }
        catch (RuntimeException ex)
        {
            throw ex.getCause();
        }
    }

    protected void dropIndex(String query) throws Throwable
    {
        String fullQuery = String.format(query, KEYSPACE);
        logger.info(fullQuery);
        schemaChange(fullQuery);
    }

    private static void schemaChange(String query)
    {
        try
        {
            // executeOnceInternal don't work for schema changes
            QueryProcessor.executeOnceInternal(query);
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

    protected UntypedResultSet execute(String query, Object... values) throws Throwable
    {
        try
        {
            query = currentTable() == null ? query : String.format(query, KEYSPACE + "." + currentTable());

            UntypedResultSet rs;
            if (USE_PREPARED_VALUES)
            {
                logger.info("Executing: {} with values {}", query, formatAllValues(values));
                rs = QueryProcessor.executeOnceInternal(query, transformValues(values));
            }
            else
            {
                query = replaceValues(query, values);
                logger.info("Executing: {}", query);
                rs = QueryProcessor.executeOnceInternal(query);
            }
            if (rs != null)
                logger.info("Got {} rows", rs.size());
            return rs;
        }
        catch (RuntimeException e)
        {
            Throwable cause = e.getCause() != null ? e.getCause() : e;
            logger.info("Got error: {}", cause.getMessage() == null ? cause.toString() : cause.getMessage());
            throw cause;
        }
    }

    protected void assertRows(UntypedResultSet result, Object[]... rows)
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

            Assert.assertEquals(String.format("Invalid number of (expected) values provided for row %d", i), meta.size(), expected.length);

            for (int j = 0; j < meta.size(); j++)
            {
                ColumnSpecification column = meta.get(j);
                Object expectedValue = expected[j];
                ByteBuffer expectedByteValue = makeByteBuffer(expected[j], (AbstractType)column.type);
                ByteBuffer actualValue = actual.getBytes(column.name.toString());

                if (!Objects.equal(expectedByteValue, actualValue))
                    Assert.fail(String.format("Invalid value for row %d column %d (%s of type %s), expected <%s> but got <%s>",
                                              i, j, column.name, column.type.asCQL3Type(), formatValue(expectedByteValue, column.type), formatValue(actualValue, column.type)));
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
            Assert.fail(String.format("Got less rows than expected. Expected %d but got %d.", rows.length, i));
        }

        Assert.assertTrue(String.format("Got more rows than expected. Expected %d but got %d", rows.length, i), i == rows.length);
    }

    protected void assertAllRows(Object[]... rows) throws Throwable
    {
        assertRows(execute("SELECT * FROM %s"), rows);
    }

    protected Object[] row(Object... expected)
    {
        return expected;
    }

    protected void assertEmpty(UntypedResultSet result) throws Throwable
    {
        if (result != null && result.size() != 0)
            throw new InvalidRequestException(String.format("Expected empty result but got %d rows", result.size()));
    }

    protected void assertInvalid(String query, Object... values) throws Throwable
    {
        assertInvalidMessage(null, query, values);
    }

    protected void assertInvalidMessage(String errorMessage, String query, Object... values) throws Throwable
    {
        try
        {
            execute(query, values);
            String q = USE_PREPARED_VALUES
                     ? query + " (values: " + formatAllValues(values) + ")"
                     : replaceValues(query, values);
            Assert.fail("Query should be invalid but no error was thrown. Query is: " + q);
        }
        catch (InvalidRequestException e)
        {
            if (errorMessage != null)
            {
                assertMessageContains(errorMessage, e);
            }
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
            String q = USE_PREPARED_VALUES
                     ? query + " (values: " + formatAllValues(values) + ")"
                     : replaceValues(query, values);
            Assert.fail("Query should have invalid syntax but no error was thrown. Query is: " + q);
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

        if (type instanceof UTF8Type)
            return String.format("'%s'", s.replaceAll("'", "''"));

        if (type instanceof BytesType)
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

        if (value instanceof Integer)
            return Int32Type.instance;

        if (value instanceof Long)
            return LongType.instance;

        if (value instanceof Float)
            return FloatType.instance;

        if (value instanceof Double)
            return DoubleType.instance;

        if (value instanceof String)
            return UTF8Type.instance;

        if (value instanceof Boolean)
            return BooleanType.instance;

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


File: test/unit/org/apache/cassandra/cql3/CollectionsTest.java
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

import org.junit.Test;

public class CollectionsTest extends CQLTester
{
    @Test
    public void testMapBulkRemoval() throws Throwable
    {
        createTable("CREATE TABLE %s (k int PRIMARY KEY, m map<text, text>)");

        execute("INSERT INTO %s(k, m) VALUES (?, ?)", 0, map("k1", "v1", "k2", "v2", "k3", "v3"));

        assertRows(execute("SELECT * FROM %s"),
            row(0, map("k1", "v1", "k2", "v2", "k3", "v3"))
        );

        execute("UPDATE %s SET m = m - ? WHERE k = ?", set("k2"), 0);

        assertRows(execute("SELECT * FROM %s"),
            row(0, map("k1", "v1", "k3", "v3"))
        );

        execute("UPDATE %s SET m = m + ?, m = m - ? WHERE k = ?", map("k4", "v4"), set("k3"), 0);

        assertRows(execute("SELECT * FROM %s"),
            row(0, map("k1", "v1", "k4", "v4"))
        );
    }

    @Test
    public void testInvalidCollectionsMix() throws Throwable
    {
        createTable("CREATE TABLE %s (k int PRIMARY KEY, l list<text>, s set<text>, m map<text, text>)");

        // Note: we force the non-prepared form for some of those tests because a list and a set
        // have the same serialized format in practice and CQLTester don't validate that the type
        // of what's passed as a value in the prepared case, so the queries would work (which is ok,
        // CQLTester is just a "dumb" client).

        assertInvalid("UPDATE %s SET l = l + { 'a', 'b' } WHERE k = 0");
        assertInvalid("UPDATE %s SET l = l - { 'a', 'b' } WHERE k = 0");
        assertInvalid("UPDATE %s SET l = l + ? WHERE k = 0", map("a", "b", "c", "d"));
        assertInvalid("UPDATE %s SET l = l - ? WHERE k = 0", map("a", "b", "c", "d"));

        assertInvalid("UPDATE %s SET s = s + [ 'a', 'b' ] WHERE k = 0");
        assertInvalid("UPDATE %s SET s = s - [ 'a', 'b' ] WHERE k = 0");
        assertInvalid("UPDATE %s SET s = s + ? WHERE k = 0", map("a", "b", "c", "d"));
        assertInvalid("UPDATE %s SET s = s - ? WHERE k = 0", map("a", "b", "c", "d"));

        assertInvalid("UPDATE %s SET m = m + ? WHERE k = 0", list("a", "b"));
        assertInvalid("UPDATE %s SET m = m - [ 'a', 'b' ] WHERE k = 0");
        assertInvalid("UPDATE %s SET m = m + ? WHERE k = 0", set("a", "b"));
        assertInvalid("UPDATE %s SET m = m - ? WHERE k = 0", map("a", "b", "c", "d"));
    }

    @Test
    public void testSets() throws Throwable
    {
        createTable("CREATE TABLE %s (k int PRIMARY KEY, s set<text>)");

        execute("INSERT INTO %s(k, s) VALUES (0, ?)", set("v1", "v2", "v3", "v4"));

        assertRows(execute("SELECT s FROM %s WHERE k = 0"),
            row(set("v1", "v2", "v3", "v4"))
        );

        execute("DELETE s[?] FROM %s WHERE k = 0", "v1");

        assertRows(execute("SELECT s FROM %s WHERE k = 0"),
            row(set("v2", "v3", "v4"))
        );

        // Full overwrite
        execute("UPDATE %s SET s = ? WHERE k = 0", set("v6", "v5"));

        assertRows(execute("SELECT s FROM %s WHERE k = 0"),
            row(set("v5", "v6"))
        );

        execute("UPDATE %s SET s = s + ? WHERE k = 0", set("v7"));

        assertRows(execute("SELECT s FROM %s WHERE k = 0"),
            row(set("v5", "v6", "v7"))
        );

        execute("UPDATE %s SET s = s - ? WHERE k = 0", set("v6", "v5"));

        assertRows(execute("SELECT s FROM %s WHERE k = 0"),
            row(set("v7"))
        );

        execute("DELETE s[?] FROM %s WHERE k = 0", set("v7"));

        // Deleting an element that does not exist will succeed
        execute("DELETE s[?] FROM %s WHERE k = 0", set("v7"));

        execute("DELETE s FROM %s WHERE k = 0");

        assertRows(execute("SELECT s FROM %s WHERE k = 0"),
            row((Object)null)
        );
    }

    @Test
    public void testMaps() throws Throwable
    {
        createTable("CREATE TABLE %s (k int PRIMARY KEY, m map<text, int>)");

        execute("INSERT INTO %s(k, m) VALUES (0, ?)", map("v1", 1, "v2", 2));

        assertRows(execute("SELECT m FROM %s WHERE k = 0"),
            row(map("v1", 1, "v2", 2))
        );

        execute("UPDATE %s SET m[?] = ?, m[?] = ? WHERE k = 0", "v3", 3, "v4", 4);

        assertRows(execute("SELECT m FROM %s WHERE k = 0"),
            row(map("v1", 1, "v2", 2, "v3", 3, "v4", 4))
        );

        execute("DELETE m[?] FROM %s WHERE k = 0", "v1");

        assertRows(execute("SELECT m FROM %s WHERE k = 0"),
            row(map("v2", 2, "v3", 3, "v4", 4))
        );

        // Full overwrite
        execute("UPDATE %s SET m = ? WHERE k = 0", map("v6", 6, "v5", 5));

        assertRows(execute("SELECT m FROM %s WHERE k = 0"),
            row(map("v5", 5, "v6", 6))
        );

        execute("UPDATE %s SET m = m + ? WHERE k = 0", map("v7", 7));

        assertRows(execute("SELECT m FROM %s WHERE k = 0"),
            row(map("v5", 5, "v6", 6, "v7", 7))
        );

        execute("DELETE m[?] FROM %s WHERE k = 0", "v7");

        assertRows(execute("SELECT m FROM %s WHERE k = 0"),
            row(map("v5", 5, "v6", 6))
        );

        execute("DELETE m[?] FROM %s WHERE k = 0", "v6");

        assertRows(execute("SELECT m FROM %s WHERE k = 0"),
            row(map("v5", 5))
        );

        execute("DELETE m[?] FROM %s WHERE k = 0", "v5");

        assertRows(execute("SELECT m FROM %s WHERE k = 0"),
            row((Object)null)
        );

        // Deleting a non-existing key should succeed
        execute("DELETE m[?] FROM %s WHERE k = 0", "v5");

        assertRows(execute("SELECT m FROM %s WHERE k = 0"),
            row((Object) null)
        );

        // The empty map is parsed as an empty set (because we don't have enough info at parsing
        // time when we see a {}) and special cased later. This test checks this work properly
        execute("UPDATE %s SET m = {} WHERE k = 0");

        assertRows(execute("SELECT m FROM %s WHERE k = 0"),
            row((Object)null)
        );
    }

    @Test
    public void testLists() throws Throwable
    {
        createTable("CREATE TABLE %s (k int PRIMARY KEY, l list<text>)");

        execute("INSERT INTO %s(k, l) VALUES (0, ?)", list("v1", "v2", "v3"));

        assertRows(execute("SELECT l FROM %s WHERE k = 0"), row(list("v1", "v2", "v3")));

        execute("DELETE l[?] FROM %s WHERE k = 0", 1);

        assertRows(execute("SELECT l FROM %s WHERE k = 0"), row(list("v1", "v3")));

        execute("UPDATE %s SET l[?] = ? WHERE k = 0", 1, "v4");

        assertRows(execute("SELECT l FROM %s WHERE k = 0"), row(list("v1", "v4")));

        // Full overwrite
        execute("UPDATE %s SET l = ? WHERE k = 0", list("v6", "v5"));

        assertRows(execute("SELECT l FROM %s WHERE k = 0"), row(list("v6", "v5")));

        execute("UPDATE %s SET l = l + ? WHERE k = 0", list("v7", "v8"));

        assertRows(execute("SELECT l FROM %s WHERE k = 0"), row(list("v6", "v5", "v7", "v8")));

        execute("UPDATE %s SET l = ? + l WHERE k = 0", list("v9"));

        assertRows(execute("SELECT l FROM %s WHERE k = 0"), row(list("v9", "v6", "v5", "v7", "v8")));

        execute("UPDATE %s SET l = l - ? WHERE k = 0", list("v5", "v8"));

        assertRows(execute("SELECT l FROM %s WHERE k = 0"), row(list("v9", "v6", "v7")));

        execute("DELETE l FROM %s WHERE k = 0");

        assertRows(execute("SELECT l FROM %s WHERE k = 0"), row((Object) null));

        assertInvalidMessage("Attempted to delete an element from a list which is null",
                             "DELETE l[0] FROM %s WHERE k=0 ");

        assertInvalidMessage("Attempted to set an element on a list which is null",
                             "UPDATE %s SET l[0] = ? WHERE k=0", list("v10"));

        execute("UPDATE %s SET l = l - ? WHERE k=0 ", list("v11"));

        assertRows(execute("SELECT l FROM %s WHERE k = 0"), row((Object) null));
    }
}


File: test/unit/org/apache/cassandra/cql3/ContainsRelationTest.java
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

import org.junit.Test;

public class ContainsRelationTest extends CQLTester
{
    @Test
    public void testSetContains() throws Throwable
    {
        createTable("CREATE TABLE %s (account text, id int, categories set<text>, PRIMARY KEY (account, id))");
        createIndex("CREATE INDEX ON %s(categories)");

        execute("INSERT INTO %s (account, id , categories) VALUES (?, ?, ?)", "test", 5, set("lmn"));

        assertEmpty(execute("SELECT * FROM %s WHERE account = ? AND categories CONTAINS ?", "xyz", "lmn"));

        assertRows(execute("SELECT * FROM %s WHERE categories CONTAINS ?", "lmn"),
            row("test", 5, set("lmn"))
        );

        assertRows(execute("SELECT * FROM %s WHERE account = ? AND categories CONTAINS ?", "test", "lmn"),
            row("test", 5, set("lmn"))
        );

        assertRows(execute("SELECT * FROM %s WHERE account = ? AND id = ? AND categories CONTAINS ?", "test", 5, "lmn"),
                   row("test", 5, set("lmn"))
        );

        assertInvalid("SELECT * FROM %s WHERE account = ? AND categories CONTAINS ? AND categories CONTAINS ?", "xyz", "lmn", "notPresent");
        assertEmpty(execute("SELECT * FROM %s WHERE account = ? AND categories CONTAINS ? AND categories CONTAINS ? ALLOW FILTERING", "xyz", "lmn", "notPresent"));
    }

    @Test
    public void testListContains() throws Throwable
    {
        createTable("CREATE TABLE %s (account text, id int, categories list<text>, PRIMARY KEY (account, id))");
        createIndex("CREATE INDEX ON %s(categories)");

        execute("INSERT INTO %s (account, id , categories) VALUES (?, ?, ?)", "test", 5, list("lmn"));

        assertEmpty(execute("SELECT * FROM %s WHERE account = ? AND categories CONTAINS ?", "xyz", "lmn"));

        assertRows(execute("SELECT * FROM %s WHERE account = ? AND categories CONTAINS ?;", "test", "lmn"),
            row("test", 5, list("lmn"))
        );

        assertRows(execute("SELECT * FROM %s WHERE categories CONTAINS ?", "lmn"),
            row("test", 5, list("lmn"))
        );

        assertRows(execute("SELECT * FROM %s WHERE account = ? AND id = ? AND categories CONTAINS ?;", "test", 5, "lmn"),
                   row("test", 5, list("lmn"))
        );

        assertInvalid("SELECT * FROM %s WHERE account = ? AND id = ? AND categories CONTAINS ? AND categories CONTAINS ?",
                      "test", 5, "lmn", "notPresent");
        assertEmpty(execute("SELECT * FROM %s WHERE account = ? AND id = ? AND categories CONTAINS ? AND categories CONTAINS ? ALLOW FILTERING",
                            "test", 5, "lmn", "notPresent"));
    }

    @Test
    public void testListContainsWithFiltering() throws Throwable
    {
        createTable("CREATE TABLE %s (e int PRIMARY KEY, f list<text>, s int)");
        createIndex("CREATE INDEX ON %s(f)");
        for(int i = 0; i < 3; i++)
        {
            execute("INSERT INTO %s (e, f, s) VALUES (?, ?, ?)", i, list("Dubai"), 4);
        }
        for(int i = 3; i < 5; i++)
        {
            execute("INSERT INTO %s (e, f, s) VALUES (?, ?, ?)", i, list("Dubai"), 3);
        }
        assertRows(execute("SELECT * FROM %s WHERE f CONTAINS ? AND s=? allow filtering", "Dubai", 3),
                   row(3, list("Dubai"), 3),
                   row(4, list("Dubai"), 3));
    }

    @Test
    public void testMapKeyContains() throws Throwable
    {
        createTable("CREATE TABLE %s (account text, id int, categories map<text,text>, PRIMARY KEY (account, id))");
        createIndex("CREATE INDEX ON %s(keys(categories))");

        execute("INSERT INTO %s (account, id , categories) VALUES (?, ?, ?)", "test", 5, map("lmn", "foo"));

        assertEmpty(execute("SELECT * FROM %s WHERE account = ? AND categories CONTAINS KEY ?", "xyz", "lmn"));

        assertRows(execute("SELECT * FROM %s WHERE account = ? AND categories CONTAINS KEY ?", "test", "lmn"),
            row("test", 5, map("lmn", "foo"))
        );
        assertRows(execute("SELECT * FROM %s WHERE categories CONTAINS KEY ?", "lmn"),
            row("test", 5, map("lmn", "foo"))
        );

        assertRows(execute("SELECT * FROM %s WHERE account = ? AND id = ? AND categories CONTAINS KEY ?", "test", 5, "lmn"),
                   row("test", 5, map("lmn", "foo"))
        );

        assertInvalid("SELECT * FROM %s WHERE account = ? AND id = ? AND categories CONTAINS KEY ? AND categories CONTAINS KEY ?",
                      "test", 5, "lmn", "notPresent");
        assertEmpty(execute("SELECT * FROM %s WHERE account = ? AND id = ? AND categories CONTAINS KEY ? AND categories CONTAINS KEY ? ALLOW FILTERING",
                            "test", 5, "lmn", "notPresent"));

        assertInvalid("SELECT * FROM %s WHERE account = ? AND id = ? AND categories CONTAINS KEY ? AND categories CONTAINS ?",
                      "test", 5, "lmn", "foo");
    }

    @Test
    public void testMapValueContains() throws Throwable
    {
        createTable("CREATE TABLE %s (account text, id int, categories map<text,text>, PRIMARY KEY (account, id))");
        createIndex("CREATE INDEX ON %s(categories)");

        execute("INSERT INTO %s (account, id , categories) VALUES (?, ?, ?)", "test", 5, map("lmn", "foo"));

        assertEmpty(execute("SELECT * FROM %s WHERE account = ? AND categories CONTAINS ?", "xyz", "foo"));

        assertRows(execute("SELECT * FROM %s WHERE account = ? AND categories CONTAINS ?", "test", "foo"),
            row("test", 5, map("lmn", "foo"))
        );

        assertRows(execute("SELECT * FROM %s WHERE categories CONTAINS ?", "foo"),
            row("test", 5, map("lmn", "foo"))
        );

        assertRows(execute("SELECT * FROM %s WHERE account = ? AND id = ? AND categories CONTAINS ?", "test", 5, "foo"),
                   row("test", 5, map("lmn", "foo"))
        );

        assertInvalid("SELECT * FROM %s WHERE account = ? AND id = ? AND categories CONTAINS ? AND categories CONTAINS ?"
                           , "test", 5, "foo", "notPresent");

        assertEmpty(execute("SELECT * FROM %s WHERE account = ? AND id = ? AND categories CONTAINS ? AND categories CONTAINS ? ALLOW FILTERING"
                           , "test", 5, "foo", "notPresent"));
    }

    // See CASSANDRA-7525
    @Test
    public void testQueryMultipleIndexTypes() throws Throwable
    {
        createTable("CREATE TABLE %s (account text, id int, categories map<text,text>, PRIMARY KEY (account, id))");

        // create an index on
        createIndex("CREATE INDEX id_index ON %s(id)");
        createIndex("CREATE INDEX categories_values_index ON %s(categories)");

        execute("INSERT INTO %s (account, id , categories) VALUES (?, ?, ?)", "test", 5, map("lmn", "foo"));

        assertRows(execute("SELECT * FROM %s WHERE categories CONTAINS ? AND id = ? ALLOW FILTERING", "foo", 5),
                row("test", 5, map("lmn", "foo"))
        );

        assertRows(
            execute("SELECT * FROM %s WHERE account = ? AND categories CONTAINS ? AND id = ? ALLOW FILTERING", "test", "foo", 5),
            row("test", 5, map("lmn", "foo"))
        );
    }

    // See CASSANDRA-8033
    @Test
    public void testFilterForContains() throws Throwable
    {
        createTable("CREATE TABLE %s (k1 int, k2 int, v set<int>, PRIMARY KEY ((k1, k2)))");
        createIndex("CREATE INDEX ON %s(k2)");

        execute("INSERT INTO %s (k1, k2, v) VALUES (?, ?, ?)", 0, 0, set(1, 2, 3));
        execute("INSERT INTO %s (k1, k2, v) VALUES (?, ?, ?)", 0, 1, set(2, 3, 4));
        execute("INSERT INTO %s (k1, k2, v) VALUES (?, ?, ?)", 1, 0, set(3, 4, 5));
        execute("INSERT INTO %s (k1, k2, v) VALUES (?, ?, ?)", 1, 1, set(4, 5, 6));

        assertRows(execute("SELECT * FROM %s WHERE k2 = ?", 1),
            row(0, 1, set(2, 3, 4)),
            row(1, 1, set(4, 5, 6))
        );

        assertRows(execute("SELECT * FROM %s WHERE k2 = ? AND v CONTAINS ? ALLOW FILTERING", 1, 6),
            row(1, 1, set(4, 5, 6))
        );

        assertEmpty(execute("SELECT * FROM %s WHERE k2 = ? AND v CONTAINS ? ALLOW FILTERING", 1, 7));
    }

    // See CASSANDRA-8073
    @Test
    public void testIndexLookupWithClusteringPrefix() throws Throwable
    {
        createTable("CREATE TABLE %s (a int, b int, c int, d set<int>, PRIMARY KEY (a, b, c))");
        createIndex("CREATE INDEX ON %s(d)");
        execute("INSERT INTO %s (a, b, c, d) VALUES (?, ?, ?, ?)", 0, 0, 0, set(1, 2, 3));
        execute("INSERT INTO %s (a, b, c, d) VALUES (?, ?, ?, ?)", 0, 0, 1, set(3, 4, 5));
        execute("INSERT INTO %s (a, b, c, d) VALUES (?, ?, ?, ?)", 0, 1, 0, set(1, 2, 3));
        execute("INSERT INTO %s (a, b, c, d) VALUES (?, ?, ?, ?)", 0, 1, 1, set(3, 4, 5));

        assertRows(execute("SELECT * FROM %s WHERE a=? AND b=? AND d CONTAINS ?", 0, 1, 3),
            row(0, 1, 0, set(1, 2, 3)),
            row(0, 1, 1, set(3, 4, 5))
        );

        assertRows(execute("SELECT * FROM %s WHERE a=? AND b=? AND d CONTAINS ?", 0, 1, 2),
            row(0, 1, 0, set(1, 2, 3))
        );

        assertRows(execute("SELECT * FROM %s WHERE a=? AND b=? AND d CONTAINS ?", 0, 1, 5),
            row(0, 1, 1, set(3, 4, 5))
        );
    }

    @Test
    public void testContainsKeyAndContainsWithIndexOnMapKey() throws Throwable
    {
        createTable("CREATE TABLE %s (account text, id int, categories map<text,text>, PRIMARY KEY (account, id))");
        createIndex("CREATE INDEX ON %s(keys(categories))");

        execute("INSERT INTO %s (account, id , categories) VALUES (?, ?, ?)", "test", 5, map("lmn", "foo"));
        execute("INSERT INTO %s (account, id , categories) VALUES (?, ?, ?)", "test", 6, map("lmn", "foo2"));

        assertInvalid("SELECT * FROM %s WHERE account = ? AND categories CONTAINS ?", "test", "foo");

        assertRows(execute("SELECT * FROM %s WHERE account = ? AND categories CONTAINS KEY ?", "test", "lmn"),
                   row("test", 5, map("lmn", "foo")),
                   row("test", 6, map("lmn", "foo2")));
        assertRows(execute("SELECT * FROM %s WHERE account = ? AND categories CONTAINS KEY ? AND categories CONTAINS ? ALLOW FILTERING",
                           "test", "lmn", "foo"),
                   row("test", 5, map("lmn", "foo")));
        assertRows(execute("SELECT * FROM %s WHERE account = ? AND categories CONTAINS ? AND categories CONTAINS KEY ? ALLOW FILTERING",
                           "test", "foo", "lmn"),
                   row("test", 5, map("lmn", "foo")));
    }

    @Test
    public void testContainsKeyAndContainsWithIndexOnMapValue() throws Throwable
    {
        createTable("CREATE TABLE %s (account text, id int, categories map<text,text>, PRIMARY KEY (account, id))");
        createIndex("CREATE INDEX ON %s(categories)");

        execute("INSERT INTO %s (account, id , categories) VALUES (?, ?, ?)", "test", 5, map("lmn", "foo"));
        execute("INSERT INTO %s (account, id , categories) VALUES (?, ?, ?)", "test", 6, map("lmn2", "foo"));

        assertInvalid("SELECT * FROM %s WHERE account = ? AND categories CONTAINS KEY ?", "test", "lmn");

        assertRows(execute("SELECT * FROM %s WHERE account = ? AND categories CONTAINS ?", "test", "foo"),
                   row("test", 5, map("lmn", "foo")),
                   row("test", 6, map("lmn2", "foo")));
        assertRows(execute("SELECT * FROM %s WHERE account = ? AND categories CONTAINS KEY ? AND categories CONTAINS ? ALLOW FILTERING",
                           "test", "lmn", "foo"),
                   row("test", 5, map("lmn", "foo")));
        assertRows(execute("SELECT * FROM %s WHERE account = ? AND categories CONTAINS ? AND categories CONTAINS KEY ? ALLOW FILTERING",
                           "test", "foo", "lmn"),
                   row("test", 5, map("lmn", "foo")));
    }
}


File: test/unit/org/apache/cassandra/cql3/CreateAndAlterKeyspaceTest.java
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

import org.junit.Test;

public class CreateAndAlterKeyspaceTest extends CQLTester
{
    @Test
    // tests CASSANDRA-9565
    public void testCreateAndAlterWithDoubleWith() throws Throwable
    {
        String[] stmts = new String[] {"ALTER KEYSPACE WITH WITH DURABLE_WRITES = true",
                                       "ALTER KEYSPACE ks WITH WITH DURABLE_WRITES = true",
                                       "CREATE KEYSPACE WITH WITH DURABLE_WRITES = true",
                                       "CREATE KEYSPACE ks WITH WITH DURABLE_WRITES = true"};

        for (String stmt : stmts) {
            assertInvalidSyntaxMessage("no viable alternative at input 'WITH'", stmt);
        }
    }
}


File: test/unit/org/apache/cassandra/cql3/CreateIndexStatementTest.java
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

import java.util.Locale;

import org.apache.commons.lang.StringUtils;

import org.junit.Test;

public class CreateIndexStatementTest extends CQLTester
{
    @Test
    public void testCreateAndDropIndex() throws Throwable
    {
        testCreateAndDropIndex("test", false);
        testCreateAndDropIndex("test2", true);
    }

    @Test
    public void testCreateAndDropIndexWithQuotedIdentifier() throws Throwable
    {
        testCreateAndDropIndex("\"quoted_ident\"", false);
        testCreateAndDropIndex("\"quoted_ident2\"", true);
    }

    @Test
    public void testCreateAndDropIndexWithCamelCaseIdentifier() throws Throwable
    {
        testCreateAndDropIndex("CamelCase", false);
        testCreateAndDropIndex("CamelCase2", true);
    }

    /**
     * Test creating and dropping an index with the specified name.
     *
     * @param indexName the index name
     * @param addKeyspaceOnDrop add the keyspace name in the drop statement
     * @throws Throwable if an error occurs
     */
    private void testCreateAndDropIndex(String indexName, boolean addKeyspaceOnDrop) throws Throwable
    {
        execute("USE system");
        assertInvalidMessage("Index '" + removeQuotes(indexName.toLowerCase(Locale.US)) + "' could not be found", "DROP INDEX " + indexName + ";");

        createTable("CREATE TABLE %s (a int primary key, b int);");
        createIndex("CREATE INDEX " + indexName + " ON %s(b);");
        createIndex("CREATE INDEX IF NOT EXISTS " + indexName + " ON %s(b);");

        assertInvalidMessage("Index already exists", "CREATE INDEX " + indexName + " ON %s(b)");

        execute("INSERT INTO %s (a, b) values (?, ?);", 0, 0);
        execute("INSERT INTO %s (a, b) values (?, ?);", 1, 1);
        execute("INSERT INTO %s (a, b) values (?, ?);", 2, 2);
        execute("INSERT INTO %s (a, b) values (?, ?);", 3, 1);

        assertRows(execute("SELECT * FROM %s where b = ?", 1), row(1, 1), row(3, 1));
        assertInvalidMessage("Index '" + removeQuotes(indexName.toLowerCase(Locale.US)) + "' could not be found in any of the tables of keyspace 'system'", "DROP INDEX " + indexName);

        if (addKeyspaceOnDrop)
        {
            dropIndex("DROP INDEX " + KEYSPACE + "." + indexName);
        }
        else
        {
            execute("USE " + KEYSPACE);
            dropIndex("DROP INDEX " + indexName);
        }

        assertInvalidMessage("No secondary indexes on the restricted columns support the provided operators",
                             "SELECT * FROM %s where b = ?", 1);
        dropIndex("DROP INDEX IF EXISTS " + indexName);
        assertInvalidMessage("Index '" + removeQuotes(indexName.toLowerCase(Locale.US)) + "' could not be found", "DROP INDEX " + indexName);
    }

    /**
     * Removes the quotes from the specified index name.
     *
     * @param indexName the index name from which the quotes must be removed.
     * @return the unquoted index name.
     */
    private static String removeQuotes(String indexName)
    {
        return StringUtils.remove(indexName, '\"');
    }
}


File: test/unit/org/apache/cassandra/cql3/CreateTableTest.java
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

import org.junit.Test;

import static junit.framework.Assert.assertFalse;

public class CreateTableTest extends CQLTester
{
    @Test
    public void testCQL3PartitionKeyOnlyTable()
    {
        createTable("CREATE TABLE %s (id text PRIMARY KEY);");
        assertFalse(currentTableMetadata().isThriftCompatible());
    }
}


File: test/unit/org/apache/cassandra/cql3/CreateTriggerStatementTest.java
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

import java.nio.ByteBuffer;
import java.util.Collection;
import java.util.Collections;

import org.apache.cassandra.config.CFMetaData;
import org.apache.cassandra.config.Schema;
import org.apache.cassandra.config.TriggerDefinition;
import org.apache.cassandra.db.ColumnFamily;
import org.apache.cassandra.db.Mutation;
import org.apache.cassandra.triggers.ITrigger;
import org.junit.Test;

import static org.junit.Assert.assertFalse;
import static org.junit.Assert.assertTrue;

public class CreateTriggerStatementTest extends CQLTester
{
    @Test
    public void testCreateTrigger() throws Throwable
    {
        createTable("CREATE TABLE %s (a int, b int, c int, PRIMARY KEY (a))");
        execute("CREATE TRIGGER trigger_1 ON %s USING '" + TestTrigger.class.getName() + "'");
        assertTriggerExists("trigger_1", TestTrigger.class);
        execute("CREATE TRIGGER trigger_2 ON %s USING '" + TestTrigger.class.getName() + "'");
        assertTriggerExists("trigger_2", TestTrigger.class);
        assertInvalid("CREATE TRIGGER trigger_1 ON %s USING '" + TestTrigger.class.getName() + "'");
        execute("CREATE TRIGGER \"Trigger 3\" ON %s USING '" + TestTrigger.class.getName() + "'");
        assertTriggerExists("Trigger 3", TestTrigger.class);
    }

    @Test
    public void testCreateTriggerIfNotExists() throws Throwable
    {
        createTable("CREATE TABLE %s (a int, b int, c int, PRIMARY KEY (a, b))");

        execute("CREATE TRIGGER IF NOT EXISTS trigger_1 ON %s USING '" + TestTrigger.class.getName() + "'");
        assertTriggerExists("trigger_1", TestTrigger.class);

        execute("CREATE TRIGGER IF NOT EXISTS trigger_1 ON %s USING '" + TestTrigger.class.getName() + "'");
        assertTriggerExists("trigger_1", TestTrigger.class);
    }

    @Test
    public void testDropTrigger() throws Throwable
    {
        createTable("CREATE TABLE %s (a int, b int, c int, PRIMARY KEY (a))");

        execute("CREATE TRIGGER trigger_1 ON %s USING '" + TestTrigger.class.getName() + "'");
        assertTriggerExists("trigger_1", TestTrigger.class);

        execute("DROP TRIGGER trigger_1 ON %s");
        assertTriggerDoesNotExists("trigger_1", TestTrigger.class);

        execute("CREATE TRIGGER trigger_1 ON %s USING '" + TestTrigger.class.getName() + "'");
        assertTriggerExists("trigger_1", TestTrigger.class);

        assertInvalid("DROP TRIGGER trigger_2 ON %s");
        
        execute("CREATE TRIGGER \"Trigger 3\" ON %s USING '" + TestTrigger.class.getName() + "'");
        assertTriggerExists("Trigger 3", TestTrigger.class);

        execute("DROP TRIGGER \"Trigger 3\" ON %s");
        assertTriggerDoesNotExists("Trigger 3", TestTrigger.class);
    }

    @Test
    public void testDropTriggerIfExists() throws Throwable
    {
        createTable("CREATE TABLE %s (a int, b int, c int, PRIMARY KEY (a))");

        execute("DROP TRIGGER IF EXISTS trigger_1 ON %s");
        assertTriggerDoesNotExists("trigger_1", TestTrigger.class);

        execute("CREATE TRIGGER trigger_1 ON %s USING '" + TestTrigger.class.getName() + "'");
        assertTriggerExists("trigger_1", TestTrigger.class);

        execute("DROP TRIGGER IF EXISTS trigger_1 ON %s");
        assertTriggerDoesNotExists("trigger_1", TestTrigger.class);
    }

    private void assertTriggerExists(String name, Class<?> clazz)
    {
        CFMetaData cfm = Schema.instance.getCFMetaData(keyspace(), currentTable()).copy();
        assertTrue("the trigger does not exist", cfm.containsTriggerDefinition(TriggerDefinition.create(name,
                clazz.getName())));
    }

    private void assertTriggerDoesNotExists(String name, Class<?> clazz)
    {
        CFMetaData cfm = Schema.instance.getCFMetaData(keyspace(), currentTable()).copy();
        assertFalse("the trigger exists", cfm.containsTriggerDefinition(TriggerDefinition.create(name,
                clazz.getName())));
    }

    public static class TestTrigger implements ITrigger
    {
        public Collection<Mutation> augment(ByteBuffer key, ColumnFamily update)
        {
            return Collections.emptyList();
        }
    }
}


File: test/unit/org/apache/cassandra/cql3/IndexedValuesValidationTest.java
/*
 *
 *  * Licensed to the Apache Software Foundation (ASF) under one
 *  * or more contributor license agreements.  See the NOTICE file
 *  * distributed with this work for additional information
 *  * regarding copyright ownership.  The ASF licenses this file
 *  * to you under the Apache License, Version 2.0 (the
 *  * "License"); you may not use this file except in compliance
 *  * with the License.  You may obtain a copy of the License at
 *  *
 *  *     http://www.apache.org/licenses/LICENSE-2.0
 *  *
 *  * Unless required by applicable law or agreed to in writing, software
 *  * distributed under the License is distributed on an "AS IS" BASIS,
 *  * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 *  * See the License for the specific language governing permissions and
 *  * limitations under the License.
 *
 */

package org.apache.cassandra.cql3;

import java.nio.ByteBuffer;
import java.util.HashMap;
import java.util.Map;

import org.junit.Test;

import org.apache.cassandra.utils.FBUtilities;

import static org.junit.Assert.fail;

public class IndexedValuesValidationTest extends CQLTester
{
    private static final int TOO_BIG = 1024 * 65;
    // CASSANDRA-8280/8081
    // reject updates with indexed values where value > 64k
    @Test
    public void testIndexOnCompositeValueOver64k() throws Throwable
    {
        createTable("CREATE TABLE %s(a int, b int, c blob, PRIMARY KEY (a))");
        createIndex("CREATE INDEX ON %s(c)");
        failInsert("INSERT INTO %s (a, b, c) VALUES (0, 0, ?)", ByteBuffer.allocate(TOO_BIG));
    }

    @Test
    public void testIndexOnClusteringColumnInsertPartitionKeyAndClusteringsOver64k() throws Throwable
    {
        createTable("CREATE TABLE %s(a blob, b blob, c blob, d int, PRIMARY KEY (a, b, c))");
        createIndex("CREATE INDEX ON %s(b)");

        // CompositeIndexOnClusteringKey creates index entries composed of the
        // PK plus all of the non-indexed clustering columns from the primary row
        // so we should reject where len(a) + len(c) > 65560 as this will form the
        // total clustering in the index table
        ByteBuffer a = ByteBuffer.allocate(100);
        ByteBuffer b = ByteBuffer.allocate(10);
        ByteBuffer c = ByteBuffer.allocate(FBUtilities.MAX_UNSIGNED_SHORT - 99);

        failInsert("INSERT INTO %s (a, b, c, d) VALUES (?, ?, ?, 0)", a, b, c);
    }

    @Test
    public void testCompactTableWithValueOver64k() throws Throwable
    {
        createTable("CREATE TABLE %s(a int, b blob, PRIMARY KEY (a)) WITH COMPACT STORAGE");
        createIndex("CREATE INDEX ON %s(b)");
        failInsert("INSERT INTO %s (a, b) VALUES (0, ?)", ByteBuffer.allocate(TOO_BIG));
    }

    @Test
    public void testIndexOnCollectionValueInsertPartitionKeyAndCollectionKeyOver64k() throws Throwable
    {
        createTable("CREATE TABLE %s(a blob , b map<blob, int>, PRIMARY KEY (a))");
        createIndex("CREATE INDEX ON %s(b)");

        // A collection key > 64k by itself will be rejected from
        // the primary table.
        // To test index validation we need to ensure that
        // len(b) < 64k, but len(a) + len(b) > 64k as that will
        // form the clustering in the index table
        ByteBuffer a = ByteBuffer.allocate(100);
        ByteBuffer b = ByteBuffer.allocate(FBUtilities.MAX_UNSIGNED_SHORT - 100);

        failInsert("UPDATE %s SET b[?] = 0 WHERE a = ?", b, a);
    }

    @Test
    public void testIndexOnCollectionKeyInsertPartitionKeyAndClusteringOver64k() throws Throwable
    {
        createTable("CREATE TABLE %s(a blob, b blob, c map<blob, int>, PRIMARY KEY (a, b))");
        createIndex("CREATE INDEX ON %s(KEYS(c))");

        // Basically the same as the case with non-collection clustering
        // CompositeIndexOnCollectionKeyy creates index entries composed of the
        // PK plus all of the clustering columns from the primary row, except the
        // collection element - which becomes the partition key in the index table
        ByteBuffer a = ByteBuffer.allocate(100);
        ByteBuffer b = ByteBuffer.allocate(FBUtilities.MAX_UNSIGNED_SHORT - 100);
        ByteBuffer c = ByteBuffer.allocate(10);

        failInsert("UPDATE %s SET c[?] = 0 WHERE a = ? and b = ?", c, a, b);
    }

    @Test
    public void testIndexOnPartitionKeyInsertValueOver64k() throws Throwable
    {
        createTable("CREATE TABLE %s(a int, b int, c blob, PRIMARY KEY ((a, b)))");
        createIndex("CREATE INDEX ON %s(a)");
        succeedInsert("INSERT INTO %s (a, b, c) VALUES (0, 0, ?)", ByteBuffer.allocate(TOO_BIG));
    }

    @Test
    public void testIndexOnClusteringColumnInsertValueOver64k() throws Throwable
    {
        createTable("CREATE TABLE %s(a int, b int, c blob, PRIMARY KEY (a, b))");
        createIndex("CREATE INDEX ON %s(b)");
        succeedInsert("INSERT INTO %s (a, b, c) VALUES (0, 0, ?)", ByteBuffer.allocate(TOO_BIG));
    }

    @Test
    public void testIndexOnFullCollectionEntryInsertCollectionValueOver64k() throws Throwable
    {
        createTable("CREATE TABLE %s(a int, b frozen<map<int, blob>>, PRIMARY KEY (a))");
        createIndex("CREATE INDEX ON %s(full(b))");
        Map<Integer, ByteBuffer> map = new HashMap();
        map.put(0, ByteBuffer.allocate(1024 * 65));
        failInsert("INSERT INTO %s (a, b) VALUES (0, ?)", map);
    }

    public void failInsert(String insertCQL, Object...args) throws Throwable
    {
        try
        {
            execute(insertCQL, args);
            fail("Expected statement to fail validation");
        }
        catch (Exception e)
        {
            // as expected
        }
    }

    public void succeedInsert(String insertCQL, Object...args) throws Throwable
    {
        execute(insertCQL, args);
        flush();
    }
}


File: test/unit/org/apache/cassandra/cql3/RangeDeletionTest.java
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

import org.junit.Test;

public class RangeDeletionTest extends CQLTester
{
    @Test
    public void testCassandra8558() throws Throwable
    {
        createTable("CREATE TABLE %s (a int, b int, c int, d int, PRIMARY KEY (a, b, c))");

        execute("INSERT INTO %s (a, b, c, d) VALUES (?, ?, ?, ?)", 1, 1, 1, 1);
        flush();
        execute("DELETE FROM %s WHERE a=? AND b=?", 1, 1);
        flush();
        assertEmpty(execute("SELECT * FROM %s WHERE a=? AND b=? AND c=?", 1, 1, 1));
    }
}


File: test/unit/org/apache/cassandra/cql3/SelectWithTokenFunctionTest.java
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

import org.junit.Test;

public class SelectWithTokenFunctionTest extends CQLTester
{
    @Test
    public void testTokenFunctionWithSingleColumnPartitionKey() throws Throwable
    {
        createTable("CREATE TABLE IF NOT EXISTS %s (a int PRIMARY KEY, b text)");
        execute("INSERT INTO %s (a, b) VALUES (0, 'a')");

        assertRows(execute("SELECT * FROM %s WHERE token(a) >= token(?)", 0), row(0, "a"));
        assertRows(execute("SELECT * FROM %s WHERE token(a) >= token(?) and token(a) < token(?)", 0, 1), row(0, "a"));
        assertInvalid("SELECT * FROM %s WHERE token(a) > token(?)", "a");
        assertInvalid("SELECT * FROM %s WHERE token(a, b) >= token(?, ?)", "b", 0);
        assertInvalid("SELECT * FROM %s WHERE token(a) >= token(?) and token(a) >= token(?)", 0, 1);
        assertInvalid("SELECT * FROM %s WHERE token(a) >= token(?) and token(a) = token(?)", 0, 1);
        assertInvalidSyntax("SELECT * FROM %s WHERE token(a) = token(?) and token(a) IN (token(?))", 0, 1);
    }

    @Test
    public void testTokenFunctionWithPartitionKeyAndClusteringKeyArguments() throws Throwable
    {
        createTable("CREATE TABLE IF NOT EXISTS %s (a int, b text, PRIMARY KEY (a, b))");
        assertInvalid("SELECT * FROM %s WHERE token(a, b) > token(0, 'c')");
    }

    @Test
    public void testTokenFunctionWithMultiColumnPartitionKey() throws Throwable
    {
        createTable("CREATE TABLE IF NOT EXISTS %s (a int, b text, PRIMARY KEY ((a, b)))");
        execute("INSERT INTO %s (a, b) VALUES (0, 'a')");
        execute("INSERT INTO %s (a, b) VALUES (0, 'b')");
        execute("INSERT INTO %s (a, b) VALUES (0, 'c')");

        assertRows(execute("SELECT * FROM %s WHERE token(a, b) > token(?, ?)", 0, "a"),
                   row(0, "b"),
                   row(0, "c"));
        assertRows(execute("SELECT * FROM %s WHERE token(a, b) > token(?, ?) and token(a, b) < token(?, ?)",
                           0, "a",
                           0, "d"),
                   row(0, "b"),
                   row(0, "c"));
        assertInvalid("SELECT * FROM %s WHERE token(a) > token(?) and token(b) > token(?)", 0, "a");
        assertInvalid("SELECT * FROM %s WHERE token(a) > token(?, ?) and token(a) < token(?, ?) and token(b) > token(?, ?) ", 0, "a", 0, "d", 0, "a");
        assertInvalid("SELECT * FROM %s WHERE token(b, a) > token(0, 'c')");
    }

    @Test
    public void testTokenFunctionWithCompoundPartitionAndClusteringCols() throws Throwable
    {
        createTable("CREATE TABLE IF NOT EXISTS %s (a int, b int, c int, d int, PRIMARY KEY ((a, b), c, d))");
        // just test that the queries don't error
        execute("SELECT * FROM %s WHERE token(a, b) > token(0, 0) AND c > 10 ALLOW FILTERING;");
        execute("SELECT * FROM %s WHERE c > 10 AND token(a, b) > token(0, 0) ALLOW FILTERING;");
        execute("SELECT * FROM %s WHERE token(a, b) > token(0, 0) AND (c, d) > (0, 0) ALLOW FILTERING;");
        execute("SELECT * FROM %s WHERE (c, d) > (0, 0) AND token(a, b) > token(0, 0) ALLOW FILTERING;");
    }
}


File: test/unit/org/apache/cassandra/cql3/SelectionOrderingTest.java
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

import org.junit.Test;

public class SelectionOrderingTest extends CQLTester
{

    @Test
    public void testNormalSelectionOrderSingleClustering() throws Throwable
    {
        for (String descOption : new String[]{"", " WITH CLUSTERING ORDER BY (b DESC)"})
        {
            createTable("CREATE TABLE %s (a int, b int, c int, PRIMARY KEY (a, b))" + descOption);
            execute("INSERT INTO %s (a, b, c) VALUES (?, ?, ?)", 0, 0, 0);
            execute("INSERT INTO %s (a, b, c) VALUES (?, ?, ?)", 0, 1, 1);
            execute("INSERT INTO %s (a, b, c) VALUES (?, ?, ?)", 0, 2, 2);

            assertRows(execute("SELECT * FROM %s WHERE a=? ORDER BY b ASC", 0),
                    row(0, 0, 0),
                    row(0, 1, 1),
                    row(0, 2, 2)
            );

            assertRows(execute("SELECT * FROM %s WHERE a=? ORDER BY b DESC", 0),
                    row(0, 2, 2),
                    row(0, 1, 1),
                    row(0, 0, 0)
            );

            // order by the only column in the selection
            assertRows(execute("SELECT b FROM %s WHERE a=? ORDER BY b ASC", 0),
                    row(0), row(1), row(2));

            assertRows(execute("SELECT b FROM %s WHERE a=? ORDER BY b DESC", 0),
                    row(2), row(1), row(0));

            // order by a column not in the selection
            assertRows(execute("SELECT c FROM %s WHERE a=? ORDER BY b ASC", 0),
                    row(0), row(1), row(2));

            assertRows(execute("SELECT c FROM %s WHERE a=? ORDER BY b DESC", 0),
                    row(2), row(1), row(0));
        }
    }

    @Test
    public void testFunctionSelectionOrderSingleClustering() throws Throwable
    {
        for (String descOption : new String[]{"", " WITH CLUSTERING ORDER BY (b DESC)"})
        {
            createTable("CREATE TABLE %s (a int, b int, c int, PRIMARY KEY (a, b))" + descOption);
            execute("INSERT INTO %s (a, b, c) VALUES (?, ?, ?)", 0, 0, 0);
            execute("INSERT INTO %s (a, b, c) VALUES (?, ?, ?)", 0, 1, 1);
            execute("INSERT INTO %s (a, b, c) VALUES (?, ?, ?)", 0, 2, 2);

            // order by the only column in the selection
            assertRows(execute("SELECT blobAsInt(intAsBlob(b)) FROM %s WHERE a=? ORDER BY b ASC", 0),
                    row(0), row(1), row(2));

            assertRows(execute("SELECT blobAsInt(intAsBlob(b)) FROM %s WHERE a=? ORDER BY b DESC", 0),
                    row(2), row(1), row(0));

            // order by a column not in the selection
            assertRows(execute("SELECT blobAsInt(intAsBlob(c)) FROM %s WHERE a=? ORDER BY b ASC", 0),
                    row(0), row(1), row(2));

            assertRows(execute("SELECT blobAsInt(intAsBlob(c)) FROM %s WHERE a=? ORDER BY b DESC", 0),
                    row(2), row(1), row(0));

            assertInvalid("SELECT * FROM %s WHERE a=? ORDER BY c ASC", 0);
            assertInvalid("SELECT * FROM %s WHERE a=? ORDER BY c DESC", 0);
        }
    }

    @Test
    public void testFieldSelectionOrderSingleClustering() throws Throwable
    {
        String type = createType("CREATE TYPE %s (a int)");

        for (String descOption : new String[]{"", " WITH CLUSTERING ORDER BY (b DESC)"})
        {
            createTable("CREATE TABLE %s (a int, b int, c frozen<" + type + "   >, PRIMARY KEY (a, b))" + descOption);
            execute("INSERT INTO %s (a, b, c) VALUES (?, ?, {a: ?})", 0, 0, 0);
            execute("INSERT INTO %s (a, b, c) VALUES (?, ?, {a: ?})", 0, 1, 1);
            execute("INSERT INTO %s (a, b, c) VALUES (?, ?, {a: ?})", 0, 2, 2);

            // order by a column not in the selection
            assertRows(execute("SELECT c.a FROM %s WHERE a=? ORDER BY b ASC", 0),
                    row(0), row(1), row(2));

            assertRows(execute("SELECT c.a FROM %s WHERE a=? ORDER BY b DESC", 0),
                    row(2), row(1), row(0));

            assertRows(execute("SELECT blobAsInt(intAsBlob(c.a)) FROM %s WHERE a=? ORDER BY b DESC", 0),
                    row(2), row(1), row(0));
            dropTable("DROP TABLE %s");
        }
    }

    @Test
    public void testNormalSelectionOrderMultipleClustering() throws Throwable
    {
        createTable("CREATE TABLE %s (a int, b int, c int, d int, PRIMARY KEY (a, b, c))");
        execute("INSERT INTO %s (a, b, c, d) VALUES (?, ?, ?, ?)", 0, 0, 0, 0);
        execute("INSERT INTO %s (a, b, c, d) VALUES (?, ?, ?, ?)", 0, 0, 1, 1);
        execute("INSERT INTO %s (a, b, c, d) VALUES (?, ?, ?, ?)", 0, 0, 2, 2);
        execute("INSERT INTO %s (a, b, c, d) VALUES (?, ?, ?, ?)", 0, 1, 0, 3);
        execute("INSERT INTO %s (a, b, c, d) VALUES (?, ?, ?, ?)", 0, 1, 1, 4);
        execute("INSERT INTO %s (a, b, c, d) VALUES (?, ?, ?, ?)", 0, 1, 2, 5);

        assertRows(execute("SELECT * FROM %s WHERE a=? ORDER BY b ASC", 0),
                row(0, 0, 0, 0),
                row(0, 0, 1, 1),
                row(0, 0, 2, 2),
                row(0, 1, 0, 3),
                row(0, 1, 1, 4),
                row(0, 1, 2, 5)
        );

        assertRows(execute("SELECT * FROM %s WHERE a=? ORDER BY b DESC", 0),
                row(0, 1, 2, 5),
                row(0, 1, 1, 4),
                row(0, 1, 0, 3),
                row(0, 0, 2, 2),
                row(0, 0, 1, 1),
                row(0, 0, 0, 0)
        );

        assertRows(execute("SELECT * FROM %s WHERE a=? ORDER BY b DESC, c DESC", 0),
                row(0, 1, 2, 5),
                row(0, 1, 1, 4),
                row(0, 1, 0, 3),
                row(0, 0, 2, 2),
                row(0, 0, 1, 1),
                row(0, 0, 0, 0)
        );

        assertInvalid("SELECT * FROM %s WHERE a=? ORDER BY c ASC", 0);
        assertInvalid("SELECT * FROM %s WHERE a=? ORDER BY c DESC", 0);
        assertInvalid("SELECT * FROM %s WHERE a=? ORDER BY b ASC, c DESC", 0);
        assertInvalid("SELECT * FROM %s WHERE a=? ORDER BY b DESC, c ASC", 0);
        assertInvalid("SELECT * FROM %s WHERE a=? ORDER BY d ASC", 0);

        // select and order by b
        assertRows(execute("SELECT b FROM %s WHERE a=? ORDER BY b ASC", 0),
                row(0), row(0), row(0), row(1), row(1), row(1));
        assertRows(execute("SELECT b FROM %s WHERE a=? ORDER BY b DESC", 0),
                row(1), row(1), row(1), row(0), row(0), row(0));

        // select c, order by b
        assertRows(execute("SELECT c FROM %s WHERE a=? ORDER BY b ASC", 0),
                row(0), row(1), row(2), row(0), row(1), row(2));
        assertRows(execute("SELECT c FROM %s WHERE a=? ORDER BY b DESC", 0),
                row(2), row(1), row(0), row(2), row(1), row(0));

        // select c, order by b, c
        assertRows(execute("SELECT c FROM %s WHERE a=? ORDER BY b ASC, c ASC", 0),
                row(0), row(1), row(2), row(0), row(1), row(2));
        assertRows(execute("SELECT c FROM %s WHERE a=? ORDER BY b DESC, c DESC", 0),
                row(2), row(1), row(0), row(2), row(1), row(0));

        // select d, order by b, c
        assertRows(execute("SELECT d FROM %s WHERE a=? ORDER BY b ASC, c ASC", 0),
                row(0), row(1), row(2), row(3), row(4), row(5));
        assertRows(execute("SELECT d FROM %s WHERE a=? ORDER BY b DESC, c DESC", 0),
                row(5), row(4), row(3), row(2), row(1), row(0));
    }

    @Test
    public void testFunctionSelectionOrderMultipleClustering() throws Throwable
    {
        createTable("CREATE TABLE %s (a int, b int, c int, d int, PRIMARY KEY (a, b, c))");
        execute("INSERT INTO %s (a, b, c, d) VALUES (?, ?, ?, ?)", 0, 0, 0, 0);
        execute("INSERT INTO %s (a, b, c, d) VALUES (?, ?, ?, ?)", 0, 0, 1, 1);
        execute("INSERT INTO %s (a, b, c, d) VALUES (?, ?, ?, ?)", 0, 0, 2, 2);
        execute("INSERT INTO %s (a, b, c, d) VALUES (?, ?, ?, ?)", 0, 1, 0, 3);
        execute("INSERT INTO %s (a, b, c, d) VALUES (?, ?, ?, ?)", 0, 1, 1, 4);
        execute("INSERT INTO %s (a, b, c, d) VALUES (?, ?, ?, ?)", 0, 1, 2, 5);

        assertInvalid("SELECT blobAsInt(intAsBlob(b)) FROM %s WHERE a=? ORDER BY c ASC", 0);
        assertInvalid("SELECT blobAsInt(intAsBlob(b)) FROM %s WHERE a=? ORDER BY c DESC", 0);
        assertInvalid("SELECT blobAsInt(intAsBlob(b)) FROM %s WHERE a=? ORDER BY b ASC, c DESC", 0);
        assertInvalid("SELECT blobAsInt(intAsBlob(b)) FROM %s WHERE a=? ORDER BY b DESC, c ASC", 0);
        assertInvalid("SELECT blobAsInt(intAsBlob(b)) FROM %s WHERE a=? ORDER BY d ASC", 0);

        // select and order by b
        assertRows(execute("SELECT blobAsInt(intAsBlob(b)) FROM %s WHERE a=? ORDER BY b ASC", 0),
                row(0), row(0), row(0), row(1), row(1), row(1));
        assertRows(execute("SELECT blobAsInt(intAsBlob(b)) FROM %s WHERE a=? ORDER BY b DESC", 0),
                row(1), row(1), row(1), row(0), row(0), row(0));

        assertRows(execute("SELECT b, blobAsInt(intAsBlob(b)) FROM %s WHERE a=? ORDER BY b ASC", 0),
                row(0, 0), row(0, 0), row(0, 0), row(1, 1), row(1, 1), row(1, 1));
        assertRows(execute("SELECT b, blobAsInt(intAsBlob(b)) FROM %s WHERE a=? ORDER BY b DESC", 0),
                row(1, 1), row(1, 1), row(1, 1), row(0, 0), row(0, 0), row(0, 0));

        // select c, order by b
        assertRows(execute("SELECT blobAsInt(intAsBlob(c)) FROM %s WHERE a=? ORDER BY b ASC", 0),
                row(0), row(1), row(2), row(0), row(1), row(2));
        assertRows(execute("SELECT blobAsInt(intAsBlob(c)) FROM %s WHERE a=? ORDER BY b DESC", 0),
                row(2), row(1), row(0), row(2), row(1), row(0));

        // select c, order by b, c
        assertRows(execute("SELECT blobAsInt(intAsBlob(c)) FROM %s WHERE a=? ORDER BY b ASC, c ASC", 0),
                row(0), row(1), row(2), row(0), row(1), row(2));
        assertRows(execute("SELECT blobAsInt(intAsBlob(c)) FROM %s WHERE a=? ORDER BY b DESC, c DESC", 0),
                row(2), row(1), row(0), row(2), row(1), row(0));

        // select d, order by b, c
        assertRows(execute("SELECT blobAsInt(intAsBlob(d)) FROM %s WHERE a=? ORDER BY b ASC, c ASC", 0),
                row(0), row(1), row(2), row(3), row(4), row(5));
        assertRows(execute("SELECT blobAsInt(intAsBlob(d)) FROM %s WHERE a=? ORDER BY b DESC, c DESC", 0),
                row(5), row(4), row(3), row(2), row(1), row(0));

    }
}


File: test/unit/org/apache/cassandra/cql3/StaticColumnsQueryTest.java
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

import org.junit.Test;

/**
 * Test column ranges and ordering with static column in table
 */
public class StaticColumnsQueryTest extends CQLTester
{
    @Test
    public void testSingleClustering() throws Throwable
    {
        createTable("CREATE TABLE %s (p text, c text, v text, s text static, PRIMARY KEY (p, c))");

        execute("INSERT INTO %s(p, c, v, s) values (?, ?, ?, ?)", "p1", "k1", "v1", "sv1");
        execute("INSERT INTO %s(p, c, v) values (?, ?, ?)", "p1", "k2", "v2");
        execute("INSERT INTO %s(p, s) values (?, ?)", "p2", "sv2");

        assertRows(execute("SELECT * FROM %s WHERE p=?", "p1"),
            row("p1", "k1", "sv1", "v1"),
            row("p1", "k2", "sv1", "v2")
        );

        assertRows(execute("SELECT * FROM %s WHERE p=?", "p2"),
            row("p2", null, "sv2", null)
        );

        // Ascending order

        assertRows(execute("SELECT * FROM %s WHERE p=? ORDER BY c ASC", "p1"),
            row("p1", "k1", "sv1", "v1"),
            row("p1", "k2", "sv1", "v2")
        );

        assertRows(execute("SELECT * FROM %s WHERE p=? ORDER BY c ASC", "p2"),
            row("p2", null, "sv2", null)
        );

        // Descending order

        assertRows(execute("SELECT * FROM %s WHERE p=? ORDER BY c DESC", "p1"),
            row("p1", "k2", "sv1", "v2"),
            row("p1", "k1", "sv1", "v1")
        );

        assertRows(execute("SELECT * FROM %s WHERE p=? ORDER BY c DESC", "p2"),
            row("p2", null, "sv2", null)
        );

        // No order with one relation

        assertRows(execute("SELECT * FROM %s WHERE p=? AND c>=?", "p1", "k1"),
            row("p1", "k1", "sv1", "v1"),
            row("p1", "k2", "sv1", "v2")
        );

        assertRows(execute("SELECT * FROM %s WHERE p=? AND c>=?", "p1", "k2"),
            row("p1", "k2", "sv1", "v2")
        );

        assertEmpty(execute("SELECT * FROM %s WHERE p=? AND c>=?", "p1", "k3"));

        assertRows(execute("SELECT * FROM %s WHERE p=? AND c =?", "p1", "k1"),
            row("p1", "k1", "sv1", "v1")
        );

        assertRows(execute("SELECT * FROM %s WHERE p=? AND c<=?", "p1", "k1"),
            row("p1", "k1", "sv1", "v1")
        );

        assertEmpty(execute("SELECT * FROM %s WHERE p=? AND c<=?", "p1", "k0"));

        // Ascending with one relation

        assertRows(execute("SELECT * FROM %s WHERE p=? AND c>=? ORDER BY c ASC", "p1", "k1"),
            row("p1", "k1", "sv1", "v1"),
            row("p1", "k2", "sv1", "v2")
        );

        assertRows(execute("SELECT * FROM %s WHERE p=? AND c>=? ORDER BY c ASC", "p1", "k2"),
            row("p1", "k2", "sv1", "v2")
        );

        assertEmpty(execute("SELECT * FROM %s WHERE p=? AND c>=? ORDER BY c ASC", "p1", "k3"));

        assertRows(execute("SELECT * FROM %s WHERE p=? AND c =? ORDER BY c ASC", "p1", "k1"),
            row("p1", "k1", "sv1", "v1")
        );

        assertRows(execute("SELECT * FROM %s WHERE p=? AND c<=? ORDER BY c ASC", "p1", "k1"),
            row("p1", "k1", "sv1", "v1")
        );

        assertEmpty(execute("SELECT * FROM %s WHERE p=? AND c<=? ORDER BY c ASC", "p1", "k0"));

        // Descending with one relation

        assertRows(execute("SELECT * FROM %s WHERE p=? AND c>=? ORDER BY c DESC", "p1", "k1"),
            row("p1", "k2", "sv1", "v2"),
            row("p1", "k1", "sv1", "v1")
        );

        assertRows(execute("SELECT * FROM %s WHERE p=? AND c>=? ORDER BY c DESC", "p1", "k2"),
            row("p1", "k2", "sv1", "v2")
        );

        assertEmpty(execute("SELECT * FROM %s WHERE p=? AND c>=? ORDER BY c DESC", "p1", "k3"));

        assertRows(execute("SELECT * FROM %s WHERE p=? AND c =? ORDER BY c DESC", "p1", "k1"),
            row("p1", "k1", "sv1", "v1")
        );

        assertRows(execute("SELECT * FROM %s WHERE p=? AND c<=? ORDER BY c DESC", "p1", "k1"),
            row("p1", "k1", "sv1", "v1")
        );

        assertEmpty(execute("SELECT * FROM %s WHERE p=? AND c<=? ORDER BY c DESC", "p1", "k0"));

        // IN

        assertRows(execute("SELECT * FROM %s WHERE p=? AND c IN (?, ?)", "p1", "k1", "k2"),
            row("p1", "k1", "sv1", "v1"),
            row("p1", "k2", "sv1", "v2")
        );

        assertRows(execute("SELECT * FROM %s WHERE p=? AND c IN (?, ?) ORDER BY c ASC", "p1", "k1", "k2"),
            row("p1", "k1", "sv1", "v1"),
            row("p1", "k2", "sv1", "v2")
        );

        assertRows(execute("SELECT * FROM %s WHERE p=? AND c IN (?, ?) ORDER BY c DESC", "p1", "k1", "k2"),
            row("p1", "k2", "sv1", "v2"),
            row("p1", "k1", "sv1", "v1")
        );
    }

    @Test
    public void testSingleClusteringReversed() throws Throwable
    {
        createTable("CREATE TABLE %s (p text, c text, v text, s text static, PRIMARY KEY (p, c)) WITH CLUSTERING ORDER BY (c DESC)");

        execute("INSERT INTO %s(p, c, v, s) values (?, ?, ?, ?)", "p1", "k1", "v1", "sv1");
        execute("INSERT INTO %s(p, c, v) values (?, ?, ?)", "p1", "k2", "v2");
        execute("INSERT INTO %s(p, s) values (?, ?)", "p2", "sv2");

        assertRows(execute("SELECT * FROM %s WHERE p=?", "p1"),
            row("p1", "k2", "sv1", "v2"),
            row("p1", "k1", "sv1", "v1")
        );

        assertRows(execute("SELECT * FROM %s WHERE p=?", "p2"),
            row("p2", null, "sv2", null)
        );

        // Ascending order

        assertRows(execute("SELECT * FROM %s WHERE p=? ORDER BY c ASC", "p1"),
            row("p1", "k1", "sv1", "v1"),
            row("p1", "k2", "sv1", "v2")
        );

        assertRows(execute("SELECT * FROM %s WHERE p=? ORDER BY c ASC", "p2"),
            row("p2", null, "sv2", null)
        );

        // Descending order

        assertRows(execute("SELECT * FROM %s WHERE p=? ORDER BY c DESC", "p1"),
            row("p1", "k2", "sv1", "v2"),
            row("p1", "k1", "sv1", "v1")
        );

        assertRows(execute("SELECT * FROM %s WHERE p=? ORDER BY c DESC", "p2"),
            row("p2", null, "sv2", null)
        );

        // No order with one relation

        assertRows(execute("SELECT * FROM %s WHERE p=? AND c>=?", "p1", "k1"),
            row("p1", "k2", "sv1", "v2"),
            row("p1", "k1", "sv1", "v1")
        );

        assertRows(execute("SELECT * FROM %s WHERE p=? AND c>=?", "p1", "k2"),
            row("p1", "k2", "sv1", "v2")
        );

        assertEmpty(execute("SELECT * FROM %s WHERE p=? AND c>=?", "p1", "k3"));

        assertRows(execute("SELECT * FROM %s WHERE p=? AND c=?", "p1", "k1"),
            row("p1", "k1", "sv1", "v1")
        );

        assertRows(execute("SELECT * FROM %s WHERE p=? AND c<=?", "p1", "k1"),
            row("p1", "k1", "sv1", "v1")
        );

        assertEmpty(execute("SELECT * FROM %s WHERE p=? AND c<=?", "p1", "k0"));

        // Ascending with one relation

        assertRows(execute("SELECT * FROM %s WHERE p=? AND c>=? ORDER BY c ASC", "p1", "k1"),
            row("p1", "k1", "sv1", "v1"),
            row("p1", "k2", "sv1", "v2")
        );

        assertRows(execute("SELECT * FROM %s WHERE p=? AND c>=? ORDER BY c ASC", "p1", "k2"),
            row("p1", "k2", "sv1", "v2")
        );

        assertEmpty(execute("SELECT * FROM %s WHERE p=? AND c>=? ORDER BY c ASC", "p1", "k3"));

        assertRows(execute("SELECT * FROM %s WHERE p=? AND c=? ORDER BY c ASC", "p1", "k1"),
            row("p1", "k1", "sv1", "v1")
        );

        assertRows(execute("SELECT * FROM %s WHERE p=? AND c<=? ORDER BY c ASC", "p1", "k1"),
            row("p1", "k1", "sv1", "v1")
        );

        assertEmpty(execute("SELECT * FROM %s WHERE p=? AND c<=? ORDER BY c ASC", "p1", "k0"));

        // Descending with one relation

        assertRows(execute("SELECT * FROM %s WHERE p=? AND c>=? ORDER BY c DESC", "p1", "k1"),
            row("p1", "k2", "sv1", "v2"),
            row("p1", "k1", "sv1", "v1")
        );

        assertRows(execute("SELECT * FROM %s WHERE p=? AND c>=? ORDER BY c DESC", "p1", "k2"),
            row("p1", "k2", "sv1", "v2")
        );

        assertEmpty(execute("SELECT * FROM %s WHERE p=? AND c>=? ORDER BY c DESC", "p1", "k3"));

        assertRows(execute("SELECT * FROM %s WHERE p=? AND c=? ORDER BY c DESC", "p1", "k1"),
            row("p1", "k1", "sv1", "v1")
        );

        assertRows(execute("SELECT * FROM %s WHERE p=? AND c<=? ORDER BY c DESC", "p1", "k1"),
            row("p1", "k1", "sv1", "v1")
        );

        assertEmpty(execute("SELECT * FROM %s WHERE p=? AND c<=? ORDER BY c DESC", "p1", "k0"));

        // IN

        assertRows(execute("SELECT * FROM %s WHERE p=? AND c IN (?, ?)", "p1", "k1", "k2"),
            row("p1", "k2", "sv1", "v2"),
            row("p1", "k1", "sv1", "v1")
        );

        assertRows(execute("SELECT * FROM %s WHERE p=? AND c IN (?, ?) ORDER BY c ASC", "p1", "k1", "k2"),
            row("p1", "k1", "sv1", "v1"),
            row("p1", "k2", "sv1", "v2")
        );

        assertRows(execute("SELECT * FROM %s WHERE p=? AND c IN (?, ?) ORDER BY c DESC", "p1", "k1", "k2"),
            row("p1", "k2", "sv1", "v2"),
            row("p1", "k1", "sv1", "v1")
        );
    }
}


File: test/unit/org/apache/cassandra/cql3/ThriftCompatibilityTest.java
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

import org.apache.cassandra.utils.ByteBufferUtil;
import org.junit.Test;

import org.apache.cassandra.SchemaLoader;

import static org.junit.Assert.assertEquals;

public class ThriftCompatibilityTest extends SchemaLoader
{
    private static UntypedResultSet execute(String query) throws Throwable
    {
        try
        {
            return QueryProcessor.executeInternal(String.format(query));
        }
        catch (RuntimeException exc)
        {
            if (exc.getCause() != null)
                throw exc.getCause();
            throw exc;
        }
    }

    /** Test For CASSANDRA-8178 */
    @Test
    public void testNonTextComparator() throws Throwable
    {
        // the comparator is IntegerType, and there is a column named 42 with a UTF8Type validation type
        execute("INSERT INTO \"Keyspace1\".\"JdbcInteger\" (key, \"42\") VALUES (0x00000001, 'abc')");
        execute("UPDATE \"Keyspace1\".\"JdbcInteger\" SET \"42\" = 'abc' WHERE key = 0x00000001");
        execute("DELETE \"42\" FROM \"Keyspace1\".\"JdbcInteger\" WHERE key = 0x00000000");
        UntypedResultSet results = execute("SELECT key, \"42\" FROM \"Keyspace1\".\"JdbcInteger\"");
        assertEquals(1, results.size());
        UntypedResultSet.Row row = results.iterator().next();
        assertEquals(ByteBufferUtil.bytes(1), row.getBytes("key"));
        assertEquals("abc", row.getString("42"));
    }
}


File: test/unit/org/apache/cassandra/cql3/statements/SelectionColumnMappingTest.java
package org.apache.cassandra.cql3.statements;

import java.util.ArrayList;
import java.util.List;

import org.junit.Test;

import org.apache.cassandra.config.ColumnDefinition;
import org.apache.cassandra.config.Schema;
import org.apache.cassandra.cql3.*;
import org.apache.cassandra.db.marshal.*;
import org.apache.cassandra.exceptions.RequestValidationException;
import org.apache.cassandra.service.ClientState;

import static org.junit.Assert.assertEquals;
import static org.junit.Assert.assertTrue;

public class SelectionColumnMappingTest extends CQLTester
{
    String tableName;
    String typeName;

    @Test
    public void testSelectionColumnMapping() throws Throwable
    {
        // Organised as a single test to avoid the overhead of
        // table creation for each variant

        typeName = createType("CREATE TYPE %s (f1 int, f2 text)");
        tableName = createTable("CREATE TABLE %s (" +
                                    " k int PRIMARY KEY," +
                                    " v1 int," +
                                    " v2 ascii," +
                                    " v3 frozen<" + typeName + ">)");
        testSimpleTypes();
        testWildcard();
        testSimpleTypesWithAliases();
        testUserTypes();
        testUserTypesWithAliases();
        testWritetimeAndTTL();
        testWritetimeAndTTLWithAliases();
        testFunction();
        testFunctionWithAlias();
        testMultipleAliasesOnSameColumn();
        testMixedColumnTypes();
    }

    @Test
    public void testMultipleArgumentFunction() throws Throwable
    {
        // token() is currently the only function which accepts multiple arguments
        tableName = createTable("CREATE TABLE %s (a int, b text, PRIMARY KEY ((a, b)))");
        ColumnSpecification tokenSpec = columnSpecification("token(a, b)", BytesType.instance);
        SelectionColumnMapping expected = SelectionColumnMapping.newMapping()
                                                                .addMapping(tokenSpec, columnDefinitions("a", "b"));

        assertEquals(expected, extractColumnMappingFromSelect("SELECT token(a,b) FROM %s"));
    }

    private void testSimpleTypes() throws Throwable
    {
        // simple column identifiers without aliases are represented in
        // ResultSet.Metadata by the underlying ColumnDefinition
        ColumnDefinition kDef = columnDefinition("k");
        ColumnDefinition v1Def = columnDefinition("v1");
        ColumnDefinition v2Def = columnDefinition("v2");
        SelectionColumnMapping expected = SelectionColumnMapping.newMapping()
                                                                .addMapping(kDef, columnDefinition("k"))
                                                                .addMapping(v1Def, columnDefinition("v1"))
                                                                .addMapping(v2Def, columnDefinition("v2"));

        assertEquals(expected, extractColumnMappingFromSelect("SELECT k, v1, v2 FROM %s"));
    }

    private void testWildcard() throws Throwable
    {
        // Wildcard select should behave just as though we had
        // explicitly selected each column
        ColumnDefinition kDef = columnDefinition("k");
        ColumnDefinition v1Def = columnDefinition("v1");
        ColumnDefinition v2Def = columnDefinition("v2");
        ColumnDefinition v3Def = columnDefinition("v3");
        SelectionColumnMapping expected = SelectionColumnMapping.newMapping()
                                                                .addMapping(kDef, columnDefinition("k"))
                                                                .addMapping(v1Def, columnDefinition("v1"))
                                                                .addMapping(v2Def, columnDefinition("v2"))
                                                                .addMapping(v3Def, columnDefinition("v3"));

        assertEquals(expected, extractColumnMappingFromSelect("SELECT * FROM %s"));
    }

    private void testSimpleTypesWithAliases() throws Throwable
    {
        // simple column identifiers with aliases are represented in ResultSet.Metadata
        // by a ColumnSpecification based on the underlying ColumnDefinition
        ColumnSpecification kSpec = columnSpecification("k_alias", Int32Type.instance);
        ColumnSpecification v1Spec = columnSpecification("v1_alias", Int32Type.instance);
        ColumnSpecification v2Spec = columnSpecification("v2_alias", AsciiType.instance);
        SelectionColumnMapping expected = SelectionColumnMapping.newMapping()
                                                                .addMapping(kSpec, columnDefinition("k"))
                                                                .addMapping(v1Spec, columnDefinition("v1"))
                                                                .addMapping(v2Spec, columnDefinition("v2"));

        assertEquals(expected, extractColumnMappingFromSelect("SELECT k AS k_alias, v1 AS v1_alias, v2 AS v2_alias FROM %s"));
    }

    private void testUserTypes() throws Throwable
    {
        // User type fields are represented in ResultSet.Metadata by a
        // ColumnSpecification denoting the name and type of the particular field
        ColumnSpecification f1Spec = columnSpecification("v3.f1", Int32Type.instance);
        ColumnSpecification f2Spec = columnSpecification("v3.f2", UTF8Type.instance);
        SelectionColumnMapping expected = SelectionColumnMapping.newMapping()
                                                                .addMapping(f1Spec, columnDefinition("v3"))
                                                                .addMapping(f2Spec, columnDefinition("v3"));

        assertEquals(expected, extractColumnMappingFromSelect("SELECT v3.f1, v3.f2 FROM %s"));
    }

    private void testUserTypesWithAliases() throws Throwable
    {
        // User type fields with aliases are represented in ResultSet.Metadata
        // by a ColumnSpecification with the alias name and the type of the actual field
        ColumnSpecification f1Spec = columnSpecification("f1_alias", Int32Type.instance);
        ColumnSpecification f2Spec = columnSpecification("f2_alias", UTF8Type.instance);
        SelectionColumnMapping expected = SelectionColumnMapping.newMapping()
                                                                .addMapping(f1Spec, columnDefinition("v3"))
                                                                .addMapping(f2Spec, columnDefinition("v3"));

        assertEquals(expected, extractColumnMappingFromSelect("SELECT v3.f1 AS f1_alias, v3.f2 AS f2_alias FROM %s"));
    }

    private void testWritetimeAndTTL() throws Throwable
    {
        // writetime and ttl are represented in ResultSet.Metadata by a ColumnSpecification
        // with the function name plus argument and a long or int type respectively
        ColumnSpecification wtSpec = columnSpecification("writetime(v1)", LongType.instance);
        ColumnSpecification ttlSpec = columnSpecification("ttl(v2)", Int32Type.instance);
        SelectionColumnMapping expected = SelectionColumnMapping.newMapping()
                                                                .addMapping(wtSpec, columnDefinition("v1"))
                                                                .addMapping(ttlSpec, columnDefinition("v2"));

        assertEquals(expected, extractColumnMappingFromSelect("SELECT writetime(v1), ttl(v2) FROM %s"));
    }

    private void testWritetimeAndTTLWithAliases() throws Throwable
    {
        // writetime and ttl with aliases are represented in ResultSet.Metadata
        // by a ColumnSpecification with the alias name and the appropriate numeric type
        ColumnSpecification wtSpec = columnSpecification("wt_alias", LongType.instance);
        ColumnSpecification ttlSpec = columnSpecification("ttl_alias", Int32Type.instance);
        SelectionColumnMapping expected = SelectionColumnMapping.newMapping()
                                                                .addMapping(wtSpec, columnDefinition("v1"))
                                                                .addMapping(ttlSpec, columnDefinition("v2"));

        assertEquals(expected, extractColumnMappingFromSelect("SELECT writetime(v1) AS wt_alias, ttl(v2) AS ttl_alias FROM %s"));
    }

    private void testFunction() throws Throwable
    {
        // a function such as intasblob(<col>) is represented in ResultSet.Metadata
        // by a ColumnSpecification with the function name plus args and the type set
        // to the function's return type
        ColumnSpecification fnSpec = columnSpecification("intasblob(v1)", BytesType.instance);
        SelectionColumnMapping expected = SelectionColumnMapping.newMapping()
                                                                .addMapping(fnSpec, columnDefinition("v1"));

        assertEquals(expected, extractColumnMappingFromSelect("SELECT intasblob(v1) FROM %s"));
    }

    private void testFunctionWithAlias() throws Throwable
    {
        // a function with an alias is represented in ResultSet.Metadata by a
        // ColumnSpecification with the alias and the type set to the function's
        // return type
        ColumnSpecification fnSpec = columnSpecification("fn_alias", BytesType.instance);
        SelectionColumnMapping expected = SelectionColumnMapping.newMapping()
                                                                .addMapping(fnSpec, columnDefinition("v1"));

        assertEquals(expected, extractColumnMappingFromSelect("SELECT intasblob(v1) AS fn_alias FROM %s"));
    }

    private void testMultipleAliasesOnSameColumn() throws Throwable
    {
        // Multiple result columns derived from the same underlying column are
        // represented by ColumnSpecifications
        ColumnSpecification alias1 = columnSpecification("alias_1", Int32Type.instance);
        ColumnSpecification alias2 = columnSpecification("alias_2", Int32Type.instance);
        SelectionColumnMapping expected = SelectionColumnMapping.newMapping()
                                                                .addMapping(alias1, columnDefinition("v1"))
                                                                .addMapping(alias2, columnDefinition("v1"));

        assertEquals(expected, extractColumnMappingFromSelect("SELECT v1 AS alias_1, v1 AS alias_2 FROM %s"));
    }

    private void testMixedColumnTypes() throws Throwable
    {
        ColumnSpecification kSpec = columnSpecification("k_alias", Int32Type.instance);
        ColumnSpecification v1Spec = columnSpecification("writetime(v1)", LongType.instance);
        ColumnSpecification v2Spec = columnSpecification("ttl_alias", Int32Type.instance);
        ColumnSpecification f1Spec = columnSpecification("v3.f1", Int32Type.instance);
        ColumnSpecification f2Spec = columnSpecification("f2_alias", UTF8Type.instance);

        SelectionColumnMapping expected = SelectionColumnMapping.newMapping()
                                                                .addMapping(kSpec, columnDefinition("k"))
                                                                .addMapping(v1Spec, columnDefinition("v1"))
                                                                .addMapping(v2Spec, columnDefinition("v2"))
                                                                .addMapping(f1Spec, columnDefinition("v3"))
                                                                .addMapping(f2Spec, columnDefinition("v3"))
                                                                .addMapping(columnDefinition("v3"), columnDefinition(
                                                                                                                    "v3"));

        assertEquals(expected, extractColumnMappingFromSelect("SELECT k AS k_alias," +
                                                              "       writetime(v1)," +
                                                              "       ttl(v2) as ttl_alias," +
                                                              "       v3.f1," +
                                                              "       v3.f2 AS f2_alias," +
                                                              "       v3" +
                                                              " FROM %s"));
    }

    private SelectionColumns extractColumnMappingFromSelect(String query) throws RequestValidationException
    {
        CQLStatement statement = QueryProcessor.getStatement(String.format(query, KEYSPACE + "." + tableName),
                                                             ClientState.forInternalCalls()).statement;
        assertTrue(statement instanceof SelectStatement);
        return ((SelectStatement)statement).getSelection().getColumnMapping();
    }

    private ColumnDefinition columnDefinition(String name)
    {
        return Schema.instance.getCFMetaData(KEYSPACE, tableName)
                              .getColumnDefinition(new ColumnIdentifier(name, true));

    }

    private Iterable<ColumnDefinition> columnDefinitions(String...name)
    {
        List<ColumnDefinition> list = new ArrayList<>();
        for (String n : name)
            list.add(columnDefinition(n));
        return list;
    }

    private ColumnSpecification columnSpecification(String name, AbstractType<?> type)
    {
        return new ColumnSpecification(KEYSPACE,
                                       tableName,
                                       new ColumnIdentifier(name, true),
                                       type);
    }
}


File: tools/stress/src/org/apache/cassandra/stress/generate/values/TimeUUIDs.java
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
package org.apache.cassandra.stress.generate.values;


import java.util.UUID;

import org.apache.cassandra.db.marshal.TimeUUIDType;
import org.apache.cassandra.utils.UUIDGen;

public class TimeUUIDs extends Generator<UUID>
{
    final Dates dateGen;
    final long clockSeqAndNode;

    public TimeUUIDs(String name, GeneratorConfig config)
    {
        super(TimeUUIDType.instance, config, name, UUID.class);
        dateGen = new Dates(name, config);
        clockSeqAndNode = config.salt;
    }

    public void setSeed(long seed)
    {
        dateGen.setSeed(seed);
    }

    @Override
    public UUID generate()
    {
        return UUIDGen.getTimeUUID(dateGen.generate().getTime(), clockSeqAndNode);
    }
}
