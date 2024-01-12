Refactoring Types: ['Extract Superclass']
tflix/discovery/DiscoveryClient.java
/*
 * Copyright 2012 Netflix, Inc.
 *
 *    Licensed under the Apache License, Version 2.0 (the "License");
 *    you may not use this file except in compliance with the License.
 *    You may obtain a copy of the License at
 *
 *        http://www.apache.org/licenses/LICENSE-2.0
 *
 *    Unless required by applicable law or agreed to in writing, software
 *    distributed under the License is distributed on an "AS IS" BASIS,
 *    WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 *    See the License for the specific language governing permissions and
 *    limitations under the License.
 */

package com.netflix.discovery;

import javax.annotation.Nullable;
import javax.annotation.PreDestroy;
import javax.ws.rs.core.MediaType;
import javax.ws.rs.core.Response.Status;
import javax.ws.rs.core.UriBuilder;
import java.io.IOException;
import java.net.URI;
import java.util.ArrayList;
import java.util.Arrays;
import java.util.Collections;
import java.util.HashSet;
import java.util.List;
import java.util.Locale;
import java.util.Map;
import java.util.Set;
import java.util.TimerTask;
import java.util.TreeMap;
import java.util.TreeSet;
import java.util.concurrent.ConcurrentHashMap;
import java.util.concurrent.Executors;
import java.util.concurrent.ScheduledExecutorService;
import java.util.concurrent.SynchronousQueue;
import java.util.concurrent.ThreadPoolExecutor;
import java.util.concurrent.TimeUnit;
import java.util.concurrent.atomic.AtomicInteger;
import java.util.concurrent.atomic.AtomicLong;
import java.util.concurrent.atomic.AtomicReference;
import java.util.concurrent.locks.Lock;
import java.util.concurrent.locks.ReentrantLock;
import java.util.regex.Matcher;
import java.util.regex.Pattern;

import com.google.common.annotations.VisibleForTesting;
import com.google.common.base.Strings;
import com.google.common.util.concurrent.ThreadFactoryBuilder;
import com.google.inject.Inject;
import com.google.inject.Provider;
import com.netflix.appinfo.ApplicationInfoManager;
import com.netflix.appinfo.EurekaClientIdentity;
import com.netflix.appinfo.HealthCheckCallback;
import com.netflix.appinfo.HealthCheckCallbackToHandlerBridge;
import com.netflix.appinfo.HealthCheckHandler;
import com.netflix.appinfo.InstanceInfo;
import com.netflix.appinfo.InstanceInfo.ActionType;
import com.netflix.appinfo.InstanceInfo.InstanceStatus;
import com.netflix.config.DynamicPropertyFactory;
import com.netflix.discovery.shared.Application;
import com.netflix.discovery.shared.Applications;
import com.netflix.discovery.shared.EurekaJerseyClient;
import com.netflix.discovery.shared.EurekaJerseyClient.JerseyClient;
import com.netflix.eventbus.spi.EventBus;
import com.netflix.governator.guice.lazy.FineGrainedLazySingleton;
import com.netflix.servo.monitor.Counter;
import com.netflix.servo.monitor.Monitors;
import com.netflix.servo.monitor.Stopwatch;
import com.sun.jersey.api.client.ClientResponse;
import com.sun.jersey.api.client.WebResource;
import com.sun.jersey.api.client.filter.GZIPContentEncodingFilter;
import com.sun.jersey.client.apache4.ApacheHttpClient4;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

/**
 * The class that is instrumental for interactions with <tt>Eureka Server</tt>.
 *
 * <p>
 * <tt>Eureka Client</tt> is responsible for a) <em>Registering</em> the
 * instance with <tt>Eureka Server</tt> b) <em>Renewal</em>of the lease with
 * <tt>Eureka Server</tt> c) <em>Cancellation</em> of the lease from
 * <tt>Eureka Server</tt> during shutdown
 * <p>
 * d) <em>Querying</em> the list of services/instances registered with
 * <tt>Eureka Server</tt>
 * <p>
 *
 * <p>
 * <tt>Eureka Client</tt> needs a configured list of <tt>Eureka Server</tt>
 * {@link java.net.URL}s to talk to.These {@link java.net.URL}s are typically amazon elastic eips
 * which do not change. All of the functions defined above fail-over to other
 * {@link java.net.URL}s specified in the list in the case of failure.
 * </p>
 *
 * @author Karthik Ranganathan, Greg Kim
 *
 */
@FineGrainedLazySingleton
public class DiscoveryClient implements EurekaClient {
    private static final Logger logger = LoggerFactory.getLogger(DiscoveryClient.class);
    private static final DynamicPropertyFactory configInstance = DynamicPropertyFactory.getInstance();

    // Constants
    public static final int MAX_FOLLOWED_REDIRECTS = 10;
    public static final String HTTP_X_DISCOVERY_ALLOW_REDIRECT = "X-Discovery-AllowRedirect";

    private static final String VALUE_DELIMITER = ",";
    private static final String COMMA_STRING = VALUE_DELIMITER;
    private static final String DISCOVERY_APPID = "DISCOVERY";
    private static final String UNKNOWN = "UNKNOWN";

    private static final Pattern REDIRECT_PATH_REGEX = Pattern.compile("(.*/v2/)apps(/.*)?$");

    // Timers
    private static final String PREFIX = "DiscoveryClient_";
    private final com.netflix.servo.monitor.Timer GET_SERVICE_URLS_DNS_TIMER = Monitors
            .newTimer(PREFIX + "GetServiceUrlsFromDNS");
    private final com.netflix.servo.monitor.Timer REGISTER_TIMER = Monitors
            .newTimer(PREFIX + "Register");
    private final com.netflix.servo.monitor.Timer REFRESH_TIMER = Monitors
            .newTimer(PREFIX + "Refresh");
    private final com.netflix.servo.monitor.Timer REFRESH_DELTA_TIMER = Monitors
            .newTimer(PREFIX + "RefreshDelta");
    private final com.netflix.servo.monitor.Timer RENEW_TIMER = Monitors
            .newTimer(PREFIX + "Renew");
    private final com.netflix.servo.monitor.Timer CANCEL_TIMER = Monitors
            .newTimer(PREFIX + "Cancel");
    private final com.netflix.servo.monitor.Timer FETCH_REGISTRY_TIMER = Monitors
            .newTimer(PREFIX + "FetchRegistry");
    private final Counter SERVER_RETRY_COUNTER = Monitors.newCounter(PREFIX
            + "Retry");
    private final Counter ALL_SERVER_FAILURE_COUNT = Monitors.newCounter(PREFIX
            + "Failed");
    private final Counter REREGISTER_COUNTER = Monitors.newCounter(PREFIX
            + "Reregister");

    private final Provider<BackupRegistry> backupRegistryProvider;

    // instance variables
    private volatile HealthCheckHandler healthCheckHandler;
    private final Provider<HealthCheckHandler> healthCheckHandlerProvider;
    private final Provider<HealthCheckCallback> healthCheckCallbackProvider;
    private final AtomicReference<List<String>> eurekaServiceUrls = new AtomicReference<List<String>>();
    private final AtomicReference<Applications> localRegionApps = new AtomicReference<Applications>();
    private volatile Map<String, Applications> remoteRegionVsApps = new ConcurrentHashMap<String, Applications>();
    private final Lock fetchRegistryUpdateLock = new ReentrantLock();
    // monotonically increasing generation counter to ensure stale threads do not reset registry to an older version
    private final AtomicLong fetchRegistryGeneration;

    private final InstanceInfo instanceInfo;
    private String appPathIdentifier;
    private boolean isRegisteredWithDiscovery = false;
    private JerseyClient discoveryJerseyClient;
    private AtomicReference<String> lastQueryRedirect = new AtomicReference<String>();
    private AtomicReference<String> lastRegisterRedirect = new AtomicReference<String>();
    private ApacheHttpClient4 discoveryApacheClient;
    protected static EurekaClientConfig clientConfig;
    private final AtomicReference<String> remoteRegionsToFetch;
    private final InstanceRegionChecker instanceRegionChecker;
    private volatile InstanceInfo.InstanceStatus lastRemoteInstanceStatus = InstanceInfo.InstanceStatus.UNKNOWN;

    private ApplicationInfoManager.StatusChangeListener statusChangeListener;

    private enum Action {
        Register, Cancel, Renew, Refresh, Refresh_Delta
    }

    /**
     * A scheduler to be used for the following 3 tasks:
     * - updating service urls
     * - scheduling a TimedSuperVisorTask
     */
    private final ScheduledExecutorService scheduler;

    private InstanceInfoReplicator instanceInfoReplicator;

    // additional executors for executing hearbeat and cacheRefresh tasks
    private final ThreadPoolExecutor heartbeatExecutor;
    private final ThreadPoolExecutor cacheRefreshExecutor;

    private final EventBus eventBus;

    public static class DiscoveryClientOptionalArgs {
        @Inject(optional = true)
        private EventBus eventBus;

        @Inject(optional = true)
        private Provider<HealthCheckCallback> healthCheckCallbackProvider;

        @Inject(optional = true)
        private Provider<HealthCheckHandler> healthCheckHandlerProvider;
    }

    public DiscoveryClient(InstanceInfo myInfo, EurekaClientConfig config) {
        this(myInfo, config, null);
    }

    public DiscoveryClient(InstanceInfo myInfo, EurekaClientConfig config, DiscoveryClientOptionalArgs args) {
        this(myInfo, config, args, new Provider<BackupRegistry>() {
            @Override
            public BackupRegistry get() {
                String backupRegistryClassName = clientConfig.getBackupRegistryImpl();
                if (null != backupRegistryClassName) {
                    try {
                        return (BackupRegistry) Class.forName(backupRegistryClassName).newInstance();
                    } catch (InstantiationException e) {
                        logger.error("Error instantiating BackupRegistry.", e);
                    } catch (IllegalAccessException e) {
                        logger.error("Error instantiating BackupRegistry.", e);
                    } catch (ClassNotFoundException e) {
                        logger.error("Error instantiating BackupRegistry.", e);
                    }
                }

                logger.warn("Using default backup registry implementation which does not do anything.");
                return new NotImplementedRegistryImpl();
            }
        });
    }

    @Inject
    DiscoveryClient(InstanceInfo myInfo, EurekaClientConfig config, DiscoveryClientOptionalArgs args,
                    Provider<BackupRegistry> backupRegistryProvider) {
        if (args != null) {
            healthCheckHandlerProvider = args.healthCheckHandlerProvider;
            healthCheckCallbackProvider = args.healthCheckCallbackProvider;
            eventBus = args.eventBus;
        } else {
            healthCheckCallbackProvider = null;
            healthCheckHandlerProvider = null;
            eventBus = null;
        }

        this.backupRegistryProvider = backupRegistryProvider;

        try {
            scheduler = Executors.newScheduledThreadPool(3,
                    new ThreadFactoryBuilder()
                            .setNameFormat("DiscoveryClient-%d")
                            .setDaemon(true)
                            .build());
            clientConfig = config;
            final String zone = getZone(myInfo);
            eurekaServiceUrls.set(getDiscoveryServiceUrls(zone));
            scheduler.scheduleWithFixedDelay(getServiceUrlUpdateTask(zone),
                    clientConfig.getEurekaServiceUrlPollIntervalSeconds(),
                    clientConfig.getEurekaServiceUrlPollIntervalSeconds(), TimeUnit.SECONDS);
            localRegionApps.set(new Applications());

            heartbeatExecutor = new ThreadPoolExecutor(
                    1, clientConfig.getHeartbeatExecutorThreadPoolSize(), 0, TimeUnit.SECONDS,
                    new SynchronousQueue<Runnable>());  // use direct handoff

            cacheRefreshExecutor = new ThreadPoolExecutor(
                    1, clientConfig.getCacheRefreshExecutorThreadPoolSize(), 0, TimeUnit.SECONDS,
                    new SynchronousQueue<Runnable>());  // use direct handoff

            fetchRegistryGeneration = new AtomicLong(0);

            instanceInfo = myInfo;
            if (myInfo != null) {
                appPathIdentifier = instanceInfo.getAppName() + "/"
                        + instanceInfo.getId();
            } else {
                logger.warn("Setting instanceInfo to a passed in null value");
            }

            if (eurekaServiceUrls.get().get(0).startsWith("https://") &&
                    "true".equals(System.getProperty("com.netflix.eureka.shouldSSLConnectionsUseSystemSocketFactory"))) {
                discoveryJerseyClient = EurekaJerseyClient.createSystemSSLJerseyClient("DiscoveryClient-HTTPClient-System",
                        clientConfig.getEurekaServerConnectTimeoutSeconds() * 1000,
                        clientConfig.getEurekaServerReadTimeoutSeconds() * 1000,
                        clientConfig.getEurekaServerTotalConnectionsPerHost(),
                        clientConfig.getEurekaServerTotalConnections(),
                        clientConfig.getEurekaConnectionIdleTimeoutSeconds());
            } else if (clientConfig.getProxyHost() != null && clientConfig.getProxyPort() != null) {
                discoveryJerseyClient = EurekaJerseyClient.createProxyJerseyClient("Proxy-DiscoveryClient-HTTPClient",
                        clientConfig.getEurekaServerConnectTimeoutSeconds() * 1000,
                        clientConfig.getEurekaServerReadTimeoutSeconds() * 1000,
                        clientConfig.getEurekaServerTotalConnectionsPerHost(),
                        clientConfig.getEurekaServerTotalConnections(),
                        clientConfig.getEurekaConnectionIdleTimeoutSeconds(),
                        clientConfig.getProxyHost(), clientConfig.getProxyPort(),
                        clientConfig.getProxyUserName(), clientConfig.getProxyPassword());
            } else {
                discoveryJerseyClient = EurekaJerseyClient.createJerseyClient("DiscoveryClient-HTTPClient",
                        clientConfig.getEurekaServerConnectTimeoutSeconds() * 1000,
                        clientConfig.getEurekaServerReadTimeoutSeconds() * 1000,
                        clientConfig.getEurekaServerTotalConnectionsPerHost(),
                        clientConfig.getEurekaServerTotalConnections(),
                        clientConfig.getEurekaConnectionIdleTimeoutSeconds());
            }
            discoveryApacheClient = discoveryJerseyClient.getClient();
            remoteRegionsToFetch = new AtomicReference<String>(clientConfig.fetchRegistryForRemoteRegions());
            AzToRegionMapper azToRegionMapper;
            if (clientConfig.shouldUseDnsForFetchingServiceUrls()) {
                azToRegionMapper = new DNSBasedAzToRegionMapper();
            } else {
                azToRegionMapper = new PropertyBasedAzToRegionMapper(clientConfig);
            }
            if (null != remoteRegionsToFetch.get()) {
                azToRegionMapper.setRegionsToFetch(remoteRegionsToFetch.get().split(","));
            }
            instanceRegionChecker = new InstanceRegionChecker(azToRegionMapper, clientConfig.getRegion());
            boolean enableGZIPContentEncodingFilter = config.shouldGZipContent();
            // should we enable GZip decoding of responses based on Response
            // Headers?
            if (enableGZIPContentEncodingFilter) {
                // compressed only if there exists a 'Content-Encoding' header
                // whose value is "gzip"
                discoveryApacheClient.addFilter(new GZIPContentEncodingFilter(
                        false));
            }

            // always enable client identity headers
            String ip = instanceInfo == null ? null : instanceInfo.getIPAddr();
            EurekaClientIdentity identity = new EurekaClientIdentity(ip);
            discoveryApacheClient.addFilter(new EurekaIdentityHeaderFilter(identity));

        } catch (Throwable e) {
            throw new RuntimeException("Failed to initialize DiscoveryClient!", e);
        }
        if (clientConfig.shouldFetchRegistry() && !fetchRegistry(false)) {
            fetchRegistryFromBackup();
        }

        initScheduledTasks();
        try {
            Monitors.registerObject(this);
        } catch (Throwable e) {
            logger.warn("Cannot register timers", e);
        }

        // This is a bit of hack to allow for existing code using DiscoveryManager.getInstance()
        // to work with DI'd DiscoveryClient
        DiscoveryManager.getInstance().setDiscoveryClient(this);
        DiscoveryManager.getInstance().setEurekaClientConfig(config);
    }

    /*
     * (non-Javadoc)
     * @see com.netflix.discovery.shared.LookupService#getApplication(java.lang.String)
     */
    @Override
    public Application getApplication(String appName) {
        return getApplications().getRegisteredApplications(appName);
    }

    /*
     * (non-Javadoc)
     *
     * @see com.netflix.discovery.shared.LookupService#getApplications()
     */
    @Override
    public Applications getApplications() {
        return localRegionApps.get();
    }

    @Override
    public Applications getApplicationsForARegion(@Nullable String region) {
        if (instanceRegionChecker.isLocalRegion(region)) {
            return localRegionApps.get();
        } else {
            return remoteRegionVsApps.get(region);
        }
    }

    public Set<String> getAllKnownRegions() {
        String localRegion = instanceRegionChecker.getLocalRegion();
        if (!remoteRegionVsApps.isEmpty()) {
            Set<String> regions = remoteRegionVsApps.keySet();
            Set<String> toReturn = new HashSet<String>(regions);
            toReturn.add(localRegion);
            return toReturn;
        } else {
            return Collections.singleton(localRegion);
        }
    }

    /*
     * (non-Javadoc)
     * @see com.netflix.discovery.shared.LookupService#getInstancesById(java.lang.String)
     */
    @Override
    public List<InstanceInfo> getInstancesById(String id) {
        List<InstanceInfo> instancesList = new ArrayList<InstanceInfo>();
        for (Application app : this.getApplications()
                .getRegisteredApplications()) {
            InstanceInfo instanceInfo = app.getByInstanceId(id);
            if (instanceInfo != null) {
                instancesList.add(instanceInfo);
            }
        }
        return instancesList;
    }

    /**
     * Register {@link HealthCheckCallback} with the eureka client.
     *
     * Once registered, the eureka client will invoke the
     * {@link HealthCheckCallback} in intervals specified by
     * {@link EurekaClientConfig#getInstanceInfoReplicationIntervalSeconds()}.
     *
     * @param callback app specific healthcheck.
     *
     * @deprecated Use
     */
    @Deprecated
    @Override
    public void registerHealthCheckCallback(HealthCheckCallback callback) {
        if (instanceInfo == null) {
            logger.error("Cannot register a listener for instance info since it is null!");
        }
        if (callback != null) {
            healthCheckHandler = new HealthCheckCallbackToHandlerBridge(callback);
        }
    }

    @Override
    public void registerHealthCheck(HealthCheckHandler healthCheckHandler) {
        if (instanceInfo == null) {
            logger.error("Cannot register a healthcheck handler when instance info is null!");
        }
        if (healthCheckHandler != null) {
            this.healthCheckHandler = healthCheckHandler;
        }
    }

    /**
     * Gets the list of instances matching the given VIP Address.
     *
     * @param vipAddress
     *            - The VIP address to match the instances for.
     * @param secure
     *            - true if it is a secure vip address, false otherwise
     * @return - The list of {@link InstanceInfo} objects matching the criteria
     */
    @Override
    public List<InstanceInfo> getInstancesByVipAddress(String vipAddress, boolean secure) {
        return getInstancesByVipAddress(vipAddress, secure, instanceRegionChecker.getLocalRegion());
    }

    /**
     * Gets the list of instances matching the given VIP Address in the passed region.
     *
     * @param vipAddress - The VIP address to match the instances for.
     * @param secure - true if it is a secure vip address, false otherwise
     * @param region - region from which the instances are to be fetched. If <code>null</code> then local region is
     *               assumed.
     *
     * @return - The list of {@link InstanceInfo} objects matching the criteria, empty list if not instances found.
     */
    @Override
    public List<InstanceInfo> getInstancesByVipAddress(String vipAddress, boolean secure,
                                                       @Nullable String region) {
        if (vipAddress == null) {
            throw new IllegalArgumentException(
                    "Supplied VIP Address cannot be null");
        }
        Applications applications;
        if (instanceRegionChecker.isLocalRegion(region)) {
            applications = this.localRegionApps.get();
        } else {
            applications = remoteRegionVsApps.get(region);
            if (null == applications) {
                logger.debug("No applications are defined for region {}, so returning an empty instance list for vip "
                        + "address {}.", region, vipAddress);
                return Collections.emptyList();
            }
        }

        if (!secure) {
            return applications.getInstancesByVirtualHostName(vipAddress);
        } else {
            return applications.getInstancesBySecureVirtualHostName(vipAddress);

        }

    }

    /**
     * Gets the list of instances matching the given VIP Address and the given
     * application name if both of them are not null. If one of them is null,
     * then that criterion is completely ignored for matching instances.
     *
     * @param vipAddress
     *            - The VIP address to match the instances for.
     * @param appName
     *            - The applicationName to match the instances for.
     * @param secure
     *            - true if it is a secure vip address, false otherwise.
     * @return - The list of {@link InstanceInfo} objects matching the criteria.
     */
    @Override
    public List<InstanceInfo> getInstancesByVipAddressAndAppName(
            String vipAddress, String appName, boolean secure) {

        List<InstanceInfo> result = new ArrayList<InstanceInfo>();
        if (vipAddress == null && appName == null) {
            throw new IllegalArgumentException(
                    "Supplied VIP Address and application name cannot both be null");
        } else if (vipAddress != null && appName == null) {
            return getInstancesByVipAddress(vipAddress, secure);
        } else if (vipAddress == null && appName != null) {
            Application application = getApplication(appName);
            if (application != null) {
                result = application.getInstances();
            }
            return result;
        }

        String instanceVipAddress;
        for (Application app : getApplications().getRegisteredApplications()) {
            for (InstanceInfo instance : app.getInstances()) {
                if (secure) {
                    instanceVipAddress = instance.getSecureVipAddress();
                } else {
                    instanceVipAddress = instance.getVIPAddress();
                }
                if (instanceVipAddress == null) {
                    continue;
                }
                String[] instanceVipAddresses = instanceVipAddress
                        .split(COMMA_STRING);

                // If the VIP Address is delimited by a comma, then consider to
                // be a list of VIP Addresses.
                // Try to match at least one in the list, if it matches then
                // return the instance info for the same
                for (String vipAddressFromList : instanceVipAddresses) {
                    if (vipAddress.equalsIgnoreCase(vipAddressFromList.trim())
                            && appName.equalsIgnoreCase(instance.getAppName())) {
                        result.add(instance);
                        break;
                    }
                }
            }
        }
        return result;
    }

    /*
     * (non-Javadoc)
     *
     * @see
     * com.netflix.discovery.shared.LookupService#getNextServerFromEureka(java
     * .lang.String, boolean)
     */
    @Override
    public InstanceInfo getNextServerFromEureka(String virtualHostname, boolean secure) {
        List<InstanceInfo> instanceInfoList = this.getInstancesByVipAddress(
                virtualHostname, secure);
        if (instanceInfoList == null || instanceInfoList.isEmpty()) {
            throw new RuntimeException("No matches for the virtual host name :"
                    + virtualHostname);
        }
        Applications apps = this.localRegionApps.get();
        int index = (int) (apps.getNextIndex(virtualHostname.toUpperCase(Locale.ROOT),
                secure).incrementAndGet() % instanceInfoList.size());
        return instanceInfoList.get(index);
    }

    /**
     * Get all applications registered with a specific eureka service.
     *
     * @param serviceUrl
     *            - The string representation of the service url.
     * @return - The registry information containing all applications.
     */
    @Override
    public Applications getApplications(String serviceUrl) {
        ClientResponse response = null;
        Applications apps = null;
        try {
            response = makeRemoteCall(Action.Refresh);
            apps = response.getEntity(Applications.class);
            logger.debug(PREFIX + appPathIdentifier + " -  refresh status: "
                    + response.getStatus());
            return apps;
        } catch (Throwable th) {
            logger.error(
                    PREFIX + appPathIdentifier
                            + " - was unable to refresh its cache! status = "
                            + th.getMessage(), th);

        } finally {
            if (response != null) {
                response.close();
            }
        }
        return apps;
    }

    /**
     * Checks to see if the eureka client registration is enabled.
     *
     * @param myInfo
     *            - The instance info object
     * @return - true, if the instance should be registered with eureka, false
     *         otherwise
     */
    private boolean shouldRegister(InstanceInfo myInfo) {
        if (!clientConfig.shouldRegisterWithEureka()) {
            return false;
        }

        return true;
    }

    /**
     * Register with the eureka service by making the appropriate REST call.
     */
    void register() throws Throwable {
        logger.info(PREFIX + appPathIdentifier + ": registering service...");
        ClientResponse response = null;
        try {
            response = makeRemoteCall(Action.Register);
            isRegisteredWithDiscovery = true;
            logger.info("{} - registration status: {}", PREFIX + appPathIdentifier,
                    (response != null ? response.getStatus() : "not sent"));
        } catch (Throwable e) {
            logger.warn("{} - registration failed {}", PREFIX + appPathIdentifier, e.getMessage(), e);
            throw e;
        } finally {
            if (response != null) {
                response.close();
            }
        }
    }

    /**
     * Renew with the eureka service by making the appropriate REST call
     */
    void renew() {
        ClientResponse response = null;
        try {
            response = makeRemoteCall(Action.Renew);
            logger.debug("{} - Heartbeat status: {}", PREFIX + appPathIdentifier,
                    (response != null ? response.getStatus() : "not sent"));
            if (response == null) {
                return;
            }
            if (response.getStatus() == 404) {
                REREGISTER_COUNTER.increment();
                logger.info("{} - Re-registering apps/{}", PREFIX + appPathIdentifier, instanceInfo.getAppName());
                register();
            }
        } catch (Throwable e) {
            logger.error("{} - was unable to send heartbeat!", PREFIX + appPathIdentifier, e);
        } finally {
            if (response != null) {
                response.close();
            }
        }

    }

    /**
     * Get the list of all eureka service urls from properties file for the eureka client to talk to.
     *
     * @param instanceZone The zone in which the client resides
     * @param preferSameZone true if we have to prefer the same zone as the client, false otherwise
     * @return The list of all eureka service urls for the eureka client to talk to
     */
    @Override
    public List<String> getServiceUrlsFromConfig(String instanceZone, boolean preferSameZone) {
        List<String> orderedUrls = new ArrayList<String>();
        String region = getRegion();
        String[] availZones = clientConfig.getAvailabilityZones(clientConfig.getRegion());
        if (availZones == null || availZones.length == 0) {
            availZones = new String[1];
            availZones[0] = "default";
        }
        logger.debug("The availability zone for the given region {} are {}",
                region, Arrays.toString(availZones));
        int myZoneOffset = getZoneOffset(instanceZone, preferSameZone,
                availZones);

        List<String> serviceUrls = clientConfig
                .getEurekaServerServiceUrls(availZones[myZoneOffset]);
        if (serviceUrls != null) {
            orderedUrls.addAll(serviceUrls);
        }
        int currentOffset = myZoneOffset == (availZones.length - 1) ? 0
                : (myZoneOffset + 1);
        while (currentOffset != myZoneOffset) {
            serviceUrls = clientConfig
                    .getEurekaServerServiceUrls(availZones[currentOffset]);
            if (serviceUrls != null) {
                orderedUrls.addAll(serviceUrls);
            }
            if (currentOffset == (availZones.length - 1)) {
                currentOffset = 0;
            } else {
                currentOffset++;
            }
        }

        if (orderedUrls.size() < 1) {
            throw new IllegalArgumentException(
                    "DiscoveryClient: invalid serviceUrl specified!");
        }
        return orderedUrls;
    }

    /**
     * @deprecated use {@link #getServiceUrlsFromConfig(String, boolean)} instead.
     */
    @Deprecated
    public static List<String> getEurekaServiceUrlsFromConfig(String instanceZone, boolean preferSameZone) {
        List<String> orderedUrls = new ArrayList<String>();
        String region = getRegion();
        String[] availZones = clientConfig.getAvailabilityZones(clientConfig.getRegion());
        if (availZones == null || availZones.length == 0) {
            availZones = new String[1];
            availZones[0] = "default";
        }
        logger.debug("The availability zone for the given region {} are {}",
                region, Arrays.toString(availZones));
        int myZoneOffset = getZoneOffset(instanceZone, preferSameZone,
                availZones);

        List<String> serviceUrls = clientConfig
                .getEurekaServerServiceUrls(availZones[myZoneOffset]);
        if (serviceUrls != null) {
            orderedUrls.addAll(serviceUrls);
        }
        int currentOffset = myZoneOffset == (availZones.length - 1) ? 0
                : (myZoneOffset + 1);
        while (currentOffset != myZoneOffset) {
            serviceUrls = clientConfig
                    .getEurekaServerServiceUrls(availZones[currentOffset]);
            if (serviceUrls != null) {
                orderedUrls.addAll(serviceUrls);
            }
            if (currentOffset == (availZones.length - 1)) {
                currentOffset = 0;
            } else {
                currentOffset++;
            }
        }

        if (orderedUrls.size() < 1) {
            throw new IllegalArgumentException(
                    "DiscoveryClient: invalid serviceUrl specified!");
        }
        return orderedUrls;
    }

    /**
     * Shuts down Eureka Client. Also sends a deregistration request to the
     * eureka server.
     */
    @PreDestroy
    @Override
    public void shutdown() {
        if (statusChangeListener != null) {
            ApplicationInfoManager.getInstance().unregisterStatusChangeListener(statusChangeListener.getId());
        }

        cancelScheduledTasks();

        // If APPINFO was registered
        if (instanceInfo != null && shouldRegister(instanceInfo)) {
            instanceInfo.setStatus(InstanceStatus.DOWN);
            unregister();
        }

        if (discoveryJerseyClient != null) {
            discoveryJerseyClient.destroyResources();
        }
    }

    /**
     * unregister w/ the eureka service.
     */
    void unregister() {
        ClientResponse response = null;
        try {
            response = makeRemoteCall(Action.Cancel);

            logger.info(PREFIX
                    + appPathIdentifier
                    + " - deregister  status: "
                    + (response != null ? response.getStatus()
                    : "not registered"));
        } catch (Throwable e) {
            logger.error(PREFIX + appPathIdentifier
                    + " - de-registration failed" + e.getMessage(), e);
        } finally {
            if (response != null) {
                response.close();
            }
        }
    }

    /**
     * Fetches the registry information.
     *
     * <p>
     * This method tries to get only deltas after the first fetch unless there
     * is an issue in reconciling eureka server and client registry information.
     * </p>
     *
     * @param forceFullRegistryFetch Forces a full registry fetch.
     *
     * @return true if the registry was fetched
     */
    private boolean fetchRegistry(boolean forceFullRegistryFetch) {
        ClientResponse response = null;
        Stopwatch tracer = FETCH_REGISTRY_TIMER.start();

        try {
            // If the delta is disabled or if it is the first time, get all
            // applications
            Applications applications = getApplications();

            if (clientConfig.shouldDisableDelta()
                    || (!Strings.isNullOrEmpty(clientConfig.getRegistryRefreshSingleVipAddress()))
                    || forceFullRegistryFetch
                    || (applications == null)
                    || (applications.getRegisteredApplications().size() == 0)
                    || (applications.getVersion() == -1)) //Client application does not have latest library supporting delta
            {
                logger.info("Disable delta property : {}", clientConfig.shouldDisableDelta());
                logger.info("Single vip registry refresh property : {}", clientConfig.getRegistryRefreshSingleVipAddress());
                logger.info("Force full registry fetch : {}", forceFullRegistryFetch);
                logger.info("Application is null : {}", (applications == null));
                logger.info("Registered Applications size is zero : {}",
                        (applications.getRegisteredApplications().size() == 0));
                logger.info("Application version is -1: {}", (applications.getVersion() == -1));
                response = getAndStoreFullRegistry();
            } else {
                response = getAndUpdateDelta(applications);
            }
            applications.setAppsHashCode(applications.getReconcileHashCode());
            logTotalInstances();

            logger.debug(PREFIX + appPathIdentifier + " -  refresh status: "
                    + response.getStatus());
        } catch (Throwable e) {
            logger.error(
                    PREFIX + appPathIdentifier
                            + " - was unable to refresh its cache! status = "
                            + e.getMessage(), e);
            return false;
        } finally {
            if (tracer != null) {
                tracer.stop();
            }
            closeResponse(response);
        }

        // Notify about cache refresh before updating the instance remote status
        onCacheRefreshed();
        
        // Update remote status based on refreshed data held in the cache
        updateInstanceRemoteStatus();

        // registry was fetched successfully, so return true
        return true;
    }

    private synchronized void updateInstanceRemoteStatus() {
        // Determine this instance's status for this app and set to UNKNOWN if not found
        InstanceInfo.InstanceStatus currentRemoteInstanceStatus = null;
        if (instanceInfo.getAppName() != null) {
            Application app = getApplication(instanceInfo.getAppName());
            if (app != null) {
                InstanceInfo remoteInstanceInfo = app.getByInstanceId(instanceInfo.getId());
                if (remoteInstanceInfo != null) {
                    currentRemoteInstanceStatus = remoteInstanceInfo.getStatus();
                }
            }
        }
        if (currentRemoteInstanceStatus == null) {
            currentRemoteInstanceStatus = InstanceInfo.InstanceStatus.UNKNOWN;
        }

        // Notify if status changed
        if (lastRemoteInstanceStatus != currentRemoteInstanceStatus) {
        	onRemoteStatusChanged(lastRemoteInstanceStatus, currentRemoteInstanceStatus);
        	lastRemoteInstanceStatus = currentRemoteInstanceStatus;
        }
    }

    /**
     * @return Return he current instance status as seen on the Eureka server.
     */
    @Override
    public InstanceInfo.InstanceStatus getInstanceRemoteStatus() {
        return lastRemoteInstanceStatus;
    }

    private String getReconcileHashCode(Applications applications) {
        TreeMap<String, AtomicInteger> instanceCountMap = new TreeMap<String, AtomicInteger>();
        if (isFetchingRemoteRegionRegistries()) {
            for (Applications remoteApp : remoteRegionVsApps.values()) {
                remoteApp.populateInstanceCountMap(instanceCountMap);
            }
        }
        applications.populateInstanceCountMap(instanceCountMap);
        return Applications.getReconcileHashCode(instanceCountMap);
    }

    /**
     * Gets the full registry information from the eureka server and stores it locally.
     * When applying the full registry, the following flow is observed:
     *
     * if (update generation have not advanced (due to another thread))
     *   atomically set the registry to the new registry
     * fi
     *
     * @return the full registry information.
     * @throws Throwable
     *             on error.
     */
    private ClientResponse getAndStoreFullRegistry() throws Throwable {
        long currentUpdateGeneration = fetchRegistryGeneration.get();
        ClientResponse response = makeRemoteCall(Action.Refresh);
        logger.info("Getting all instance registry info from the eureka server");

        Applications apps = null;
        if (response.getStatus() == Status.OK.getStatusCode()) {
            apps = response.getEntity(Applications.class);
        }

        if (apps == null) {
            logger.error("The application is null for some reason. Not storing this information");
        } else if (fetchRegistryGeneration.compareAndSet(currentUpdateGeneration, currentUpdateGeneration + 1)) {
            localRegionApps.set(this.filterAndShuffle(apps));
        } else {
            logger.warn("Not updating applications as another thread is updating it already");
        }
        logger.info("The response status is {}", response.getStatus());
        return response;
    }

    /**
     * Get the delta registry information from the eureka server and update it locally.
     * When applying the delta, the following flow is observed:
     *
     * if (update generation have not advanced (due to another thread))
     *   atomically try to: update application with the delta and get reconcileHashCode
     *   abort entire processing otherwise
     *   do reconciliation if reconcileHashCode clash
     * fi
     *
     * @return the client response
     * @throws Throwable on error
     */
    private ClientResponse getAndUpdateDelta(Applications applications) throws Throwable {
        long currentUpdateGeneration = fetchRegistryGeneration.get();
        ClientResponse response = makeRemoteCall(Action.Refresh_Delta);

        Applications delta = null;
        if (response.getStatus() == Status.OK.getStatusCode()) {
            delta = response.getEntity(Applications.class);
        }
        if (delta == null) {
            logger.warn("The server does not allow the delta revision to be applied because it is not safe. "
                    + "Hence got the full registry.");
            this.closeResponse(response);
            response = getAndStoreFullRegistry();
        } else if (fetchRegistryGeneration.compareAndSet(currentUpdateGeneration, currentUpdateGeneration + 1)) {
            String reconcileHashCode = "";
            if (fetchRegistryUpdateLock.tryLock()) {
                try {
                    updateDelta(delta);
                    reconcileHashCode = getReconcileHashCode(applications);
                } finally {
                    fetchRegistryUpdateLock.unlock();
                }
            } else {
                logger.warn("Cannot acquire update lock, aborting getAndUpdateDelta");
                return response;
            }
            // There is a diff in number of instances for some reason
            if ((!reconcileHashCode.equals(delta.getAppsHashCode()))
                    || clientConfig.shouldLogDeltaDiff()) {
                response = reconcileAndLogDifference(response, delta, reconcileHashCode);  // this makes a remoteCall
            }
        } else {
            logger.warn("Not updating application delta as another thread is updating it already");
        }

        return response;
    }

    /**
     * Logs the total number of non-filtered instances stored locally.
     */
    private void logTotalInstances() {
        int totInstances = 0;
        for (Application application : getApplications().getRegisteredApplications()) {
            totInstances += application.getInstancesAsIsFromEureka().size();
        }
        logger.debug("The total number of all instances in the client now is {}", totInstances);
    }

    /**
     * Reconcile the eureka server and client registry information and logs the differences if any.
     * When reconciling, the following flow is observed:
     *
     * make a remote call to the server for the full registry
     * calculate and log differences
     * if (update generation have not advanced (due to another thread))
     *   atomically set the registry to the new registry
     * fi
     *
     * @param response
     *            the HTTP response after getting the full registry.
     * @param delta
     *            the last delta registry information received from the eureka
     *            server.
     * @param reconcileHashCode
     *            the hashcode generated by the server for reconciliation.
     * @return ClientResponse the HTTP response object.
     * @throws Throwable
     *             on any error.
     */
    private ClientResponse reconcileAndLogDifference(ClientResponse response,
                                                     Applications delta, String reconcileHashCode) throws Throwable {
        logger.warn(
                "The Reconcile hashcodes do not match, client : {}, server : {}. Getting the full registry",
                reconcileHashCode, delta.getAppsHashCode());

        this.closeResponse(response);

        long currentUpdateGeneration = fetchRegistryGeneration.get();
        response = makeRemoteCall(Action.Refresh);
        Applications serverApps = response.getEntity(Applications.class);

        try {
            Map<String, List<String>> reconcileDiffMap = getApplications().getReconcileMapDiff(serverApps);
            String reconcileString = "";
            for (Map.Entry<String, List<String>> mapEntry : reconcileDiffMap.entrySet()) {
                reconcileString = reconcileString + mapEntry.getKey() + ": ";
                for (String displayString : mapEntry.getValue()) {
                    reconcileString = reconcileString + displayString;
                }
                reconcileString = reconcileString + "\n";
            }
            logger.warn("The reconcile string is {}", reconcileString);
        } catch (Throwable e) {
            logger.error("Could not calculate reconcile string ", e);
        }

        if (fetchRegistryGeneration.compareAndSet(currentUpdateGeneration, currentUpdateGeneration + 1)) {
            localRegionApps.set(this.filterAndShuffle(serverApps));
            getApplications().setVersion(delta.getVersion());
            logger.warn(
                    "The Reconcile hashcodes after complete sync up, client : {}, server : {}.",
                    getApplications().getReconcileHashCode(),
                    delta.getAppsHashCode());
        } else {
            logger.warn("Not setting the applications map as another thread has advanced the update generation");
        }

        return response;
    }

    /**
     * Updates the delta information fetches from the eureka server into the
     * local cache.
     *
     * @param delta
     *            the delta information received from eureka server in the last
     *            poll cycle.
     */
    private void updateDelta(Applications delta) {
        int deltaCount = 0;
        for (Application app : delta.getRegisteredApplications()) {
            for (InstanceInfo instance : app.getInstances()) {
                Applications applications = getApplications();
                String instanceRegion = instanceRegionChecker.getInstanceRegion(instance);
                if (!instanceRegionChecker.isLocalRegion(instanceRegion)) {
                    Applications remoteApps = remoteRegionVsApps.get(instanceRegion);
                    if (null == remoteApps) {
                        remoteApps = new Applications();
                        remoteRegionVsApps.put(instanceRegion, remoteApps);
                    }
                    applications = remoteApps;
                }

                ++deltaCount;
                if (ActionType.ADDED.equals(instance.getActionType())) {
                    Application existingApp = applications
                            .getRegisteredApplications(instance.getAppName());
                    if (existingApp == null) {
                        applications.addApplication(app);
                    }
                    logger.debug("Added instance {} to the existing apps in region {}",
                            instance.getId(), instanceRegion);
                    applications.getRegisteredApplications(
                            instance.getAppName()).addInstance(instance);
                } else if (ActionType.MODIFIED.equals(instance.getActionType())) {
                    Application existingApp = applications
                            .getRegisteredApplications(instance.getAppName());
                    if (existingApp == null) {
                        applications.addApplication(app);
                    }
                    logger.debug("Modified instance {} to the existing apps ",
                            instance.getId());

                    applications.getRegisteredApplications(
                            instance.getAppName()).addInstance(instance);

                } else if (ActionType.DELETED.equals(instance.getActionType())) {
                    Application existingApp = applications
                            .getRegisteredApplications(instance.getAppName());
                    if (existingApp == null) {
                        applications.addApplication(app);
                    }
                    logger.debug("Deleted instance {} to the existing apps ",
                            instance.getId());
                    applications.getRegisteredApplications(
                            instance.getAppName()).removeInstance(instance);
                }
            }
        }
        logger.debug(
                "The total number of instances fetched by the delta processor : {}",
                deltaCount);

        getApplications().setVersion(delta.getVersion());
        getApplications().shuffleInstances(clientConfig.shouldFilterOnlyUpInstances());

        for (Applications applications : remoteRegionVsApps.values()) {
            applications.setVersion(delta.getVersion());
            applications.shuffleInstances(clientConfig.shouldFilterOnlyUpInstances());
        }
    }

    /**
     * Makes remote calls with the corresponding action(register,renew etc).
     *
     * @param action
     *            the action to be performed on eureka server.
     * @return ClientResponse the HTTP response object.
     * @throws Throwable
     *             on any error.
     */
    private ClientResponse makeRemoteCall(Action action) throws Throwable {
        ClientResponse response;
        if (isQueryAction(action)) {
            response = makeRemoteCallToRedirectedServer(lastQueryRedirect, action);
        } else {
            response = makeRemoteCallToRedirectedServer(lastRegisterRedirect, action);
        }
        if (response == null) {
            response = makeRemoteCall(action, 0);
        }
        return response;
    }

    private ClientResponse makeRemoteCallToRedirectedServer(AtomicReference<String> lastRedirect, Action action) {
        String lastRedirectUrl = lastRedirect.get();
        if (lastRedirectUrl != null) {
            try {
                ClientResponse clientResponse = makeRemoteCall(action, lastRedirectUrl);
                int status = clientResponse.getStatus();
                if (status >= 200 && status < 300) {
                    return clientResponse;
                }
                SERVER_RETRY_COUNTER.increment();
                lastRedirect.compareAndSet(lastRedirectUrl, null);
            } catch (Throwable ignored) {
                logger.warn("Remote call to last redirect address failed; retrying from configured service URL list");
                SERVER_RETRY_COUNTER.increment();
                lastRedirect.compareAndSet(lastRedirectUrl, null);
            }
        }
        return null;
    }

    private static boolean isQueryAction(Action action) {
        return action == Action.Refresh || action == Action.Refresh_Delta;
    }

    /**
     * Makes remote calls with the corresponding action(register,renew etc).
     *
     * @param action
     *            the action to be performed on eureka server.
     *
     *            Try the fallback servers in case of problems communicating to
     *            the primary one.
     *
     * @return ClientResponse the HTTP response object.
     * @throws Throwable
     *             on any error.
     */
    private ClientResponse makeRemoteCall(Action action, int serviceUrlIndex) throws Throwable {
        String serviceUrl;
        try {
            serviceUrl = eurekaServiceUrls.get().get(serviceUrlIndex);
            return makeRemoteCallWithFollowRedirect(action, serviceUrl);
        } catch (Throwable t) {
            if (eurekaServiceUrls.get().size() > ++serviceUrlIndex) {
                logger.warn("Trying backup: " + eurekaServiceUrls.get().get(serviceUrlIndex));
                SERVER_RETRY_COUNTER.increment();
                return makeRemoteCall(action, serviceUrlIndex);
            } else {
                ALL_SERVER_FAILURE_COUNT.increment();
                logger.error("Can't contact any eureka nodes - possibly a security group issue?", t);
                throw t;
            }
        }
    }

    private ClientResponse makeRemoteCallWithFollowRedirect(Action action, String serviceUrl) throws Throwable {
        URI targetUrl = new URI(serviceUrl);
        for (int followRedirectCount = 0; followRedirectCount < MAX_FOLLOWED_REDIRECTS; followRedirectCount++) {
            ClientResponse clientResponse = makeRemoteCall(action, targetUrl.toString());
            if (clientResponse.getStatus() != 302) {
                if (followRedirectCount > 0) {
                    if (isQueryAction(action)) {
                        lastQueryRedirect.set(targetUrl.toString());
                    } else {
                        lastRegisterRedirect.set(targetUrl.toString());
                    }
                }
                return clientResponse;
            }
            targetUrl = getRedirectBaseUri(clientResponse.getLocation());
            if (targetUrl == null) {
                throw new IOException("Invalid redirect URL " + clientResponse.getLocation());
            }
        }
        String message = "Follow redirect limit crossed for URI " + serviceUrl;
        logger.warn(message);
        throw new IOException(message);
    }

    private static URI getRedirectBaseUri(URI targetUrl) {
        Matcher pathMatcher = REDIRECT_PATH_REGEX.matcher(targetUrl.getPath());
        if (pathMatcher.matches()) {
            return UriBuilder.fromUri(targetUrl)
                    .host(DnsResolver.resolve(targetUrl.getHost()))
                    .replacePath(pathMatcher.group(1))
                    .replaceQuery(null)
                    .build();
        }
        logger.warn("Invalid redirect URL {}", targetUrl);
        return null;
    }

    /**
     * Makes remote calls with the corresponding action(register,renew etc).
     *
     * @param action
     *            the action to be performed on eureka server.
     *
     * @return ClientResponse the HTTP response object.
     * @throws Throwable
     *             on any error.
     */
    private ClientResponse makeRemoteCall(Action action, String serviceUrl) throws Throwable {
        String urlPath = null;
        Stopwatch tracer = null;
        ClientResponse response = null;
        logger.debug("Discovery Client talking to the server {}", serviceUrl);
        try {
            // If the application is unknown do not register/renew/cancel but
            // refresh
            if ((UNKNOWN.equals(instanceInfo.getAppName())
                    && (!Action.Refresh.equals(action)) && (!Action.Refresh_Delta
                    .equals(action)))) {
                return null;
            }
            WebResource r = discoveryApacheClient.resource(serviceUrl);
            if (clientConfig.allowRedirects()) {
                r.header(HTTP_X_DISCOVERY_ALLOW_REDIRECT, "true");
            }
            String remoteRegionsToFetchStr;
            switch (action) {
                case Renew:
                    tracer = RENEW_TIMER.start();
                    urlPath = "apps/" + appPathIdentifier;
                    response = r
                            .path(urlPath)
                            .queryParam("status",
                                    instanceInfo.getStatus().toString())
                            .queryParam("lastDirtyTimestamp",
                                    instanceInfo.getLastDirtyTimestamp().toString())
                            .put(ClientResponse.class);
                    break;
                case Refresh:
                    tracer = REFRESH_TIMER.start();
                    final String vipAddress = clientConfig.getRegistryRefreshSingleVipAddress();
                    urlPath = vipAddress == null ? "apps/" : "vips/" + vipAddress;
                    remoteRegionsToFetchStr = remoteRegionsToFetch.get();
                    if (!Strings.isNullOrEmpty(remoteRegionsToFetchStr)) {
                        urlPath += "?regions=" + remoteRegionsToFetchStr;
                    }
                    response = getUrl(serviceUrl + urlPath);
                    break;
                case Refresh_Delta:
                    tracer = REFRESH_DELTA_TIMER.start();
                    urlPath = "apps/delta";
                    remoteRegionsToFetchStr = remoteRegionsToFetch.get();
                    if (!Strings.isNullOrEmpty(remoteRegionsToFetchStr)) {
                        urlPath += "?regions=" + remoteRegionsToFetchStr;
                    }
                    response = getUrl(serviceUrl + urlPath);
                    break;
                case Register:
                    tracer = REGISTER_TIMER.start();
                    urlPath = "apps/" + instanceInfo.getAppName();
                    response = r.path(urlPath)
                            .type(MediaType.APPLICATION_JSON_TYPE)
                            .post(ClientResponse.class, instanceInfo);
                    break;
                case Cancel:
                    tracer = CANCEL_TIMER.start();
                    urlPath = "apps/" + appPathIdentifier;
                    response = r.path(urlPath).delete(ClientResponse.class);
                    // Return without during de-registration if it is not registered
                    // already and if we get a 404
                    if ((!isRegisteredWithDiscovery)
                            && (response.getStatus() == Status.NOT_FOUND
                            .getStatusCode())) {
                        return response;
                    }
                    break;
            }

            if (logger.isDebugEnabled()) {
                logger.debug("Finished a call to service url {} and url path {} with status code {}.",
                        new String[]{serviceUrl, urlPath, String.valueOf(response.getStatus())});
            }
            if (isOk(action, response.getStatus())) {
                return response;
            } else {
                logger.warn("Action: " + action + "  => returned status of "
                        + response.getStatus() + " from " + serviceUrl
                        + urlPath);
                throw new RuntimeException("Bad status: "
                        + response.getStatus());
            }
        } catch (Throwable t) {
            closeResponse(response);
            logger.warn("Can't get a response from " + serviceUrl + urlPath, t);
            throw t;
        } finally {
            if (tracer != null) {
                tracer.stop();
            }
        }
    }

    /**
     * Close HTTP response object and its respective resources.
     *
     * @param response
     *            the HttpResponse object.
     */
    private void closeResponse(ClientResponse response) {
        if (response != null) {
            try {
                response.close();
            } catch (Throwable th) {
                logger.error("Cannot release response resource :", th);
            }
        }
    }

    /**
     * Initializes all scheduled tasks.
     */
    private void initScheduledTasks() {
        if (clientConfig.shouldFetchRegistry()) {
            // registry cache refresh timer
            int registryFetchIntervalSeconds = clientConfig.getRegistryFetchIntervalSeconds();
            int expBackOffBound = clientConfig.getCacheRefreshExecutorExponentialBackOffBound();
            scheduler.schedule(
                    new TimedSupervisorTask(
                            "cacheRefresh",
                            scheduler,
                            cacheRefreshExecutor,
                            registryFetchIntervalSeconds,
                            TimeUnit.SECONDS,
                            expBackOffBound,
                            new CacheRefreshThread()
                    ),
                    registryFetchIntervalSeconds, TimeUnit.SECONDS);
        }

        if (shouldRegister(instanceInfo)) {
            int renewalIntervalInSecs = instanceInfo.getLeaseInfo().getRenewalIntervalInSecs();
            int expBackOffBound = clientConfig.getHeartbeatExecutorExponentialBackOffBound();
            logger.info("Starting heartbeat executor: " + "renew interval is: " + renewalIntervalInSecs);

            // Heartbeat timer
            scheduler.schedule(
                    new TimedSupervisorTask(
                            "heartbeat",
                            scheduler,
                            heartbeatExecutor,
                            renewalIntervalInSecs,
                            TimeUnit.SECONDS,
                            expBackOffBound,
                            new HeartbeatThread()
                    ),
                    renewalIntervalInSecs, TimeUnit.SECONDS);

            // InstanceInfo replicator
            instanceInfoReplicator = new InstanceInfoReplicator(
                    this,
                    instanceInfo,
                    clientConfig.getInstanceInfoReplicationIntervalSeconds(),
                    2); // burstSize

            statusChangeListener = new ApplicationInfoManager.StatusChangeListener() {
                @Override
                public String getId() {
                    return "statusChangeListener";
                }

                @Override
                public void notify(StatusChangeEvent statusChangeEvent) {
                    logger.info("Saw local status change event {}", statusChangeEvent);
                    instanceInfoReplicator.onDemandUpdate();
                }
            };

            if (clientConfig.shouldOnDemandUpdateStatusChange()) {
                ApplicationInfoManager.getInstance().registerStatusChangeListener(statusChangeListener);
            }

            instanceInfoReplicator.start(clientConfig.getInitialInstanceInfoReplicationIntervalSeconds());
        } else {
            logger.info("Not registering with Eureka server per configuration");
        }
    }

    private void cancelScheduledTasks() {
        if (instanceInfoReplicator != null) {
            instanceInfoReplicator.stop();
        }
        heartbeatExecutor.shutdownNow();
        cacheRefreshExecutor.shutdownNow();
        scheduler.shutdownNow();
    }

    /**
     * Get the list of all eureka service urls from DNS for the eureka client to
     * talk to. The client picks up the service url from its zone and then fails over to
     * other zones randomly. If there are multiple servers in the same zone, the client once
     * again picks one randomly. This way the traffic will be distributed in the case of failures.
     *
     * @param instanceZone The zone in which the client resides.
     * @param preferSameZone true if we have to prefer the same zone as the client, false otherwise.
     * @return The list of all eureka service urls for the eureka client to talk to.
     */
    @Override
    public List<String> getServiceUrlsFromDNS(String instanceZone, boolean preferSameZone) {
        Stopwatch t = GET_SERVICE_URLS_DNS_TIMER.start();
        String region = getRegion();
        // Get zone-specific DNS names for the given region so that we can get a
        // list of available zones
        Map<String, List<String>> zoneDnsNamesMap = getZoneBasedDiscoveryUrlsFromRegion(region);
        Set<String> availableZones = zoneDnsNamesMap.keySet();
        List<String> zones = new ArrayList<String>(availableZones);
        if (zones.isEmpty()) {
            throw new RuntimeException("No available zones configured for the instanceZone " + instanceZone);
        }
        int zoneIndex = 0;
        boolean zoneFound = false;
        for (String zone : zones) {
            logger.debug(
                    "Checking if the instance zone {} is the same as the zone from DNS {}",
                    instanceZone, zone);
            if (preferSameZone) {
                if (instanceZone.equalsIgnoreCase(zone)) {
                    zoneFound = true;
                }
            } else {
                if (!instanceZone.equalsIgnoreCase(zone)) {
                    zoneFound = true;
                }
            }
            if (zoneFound) {
                Object[] args = {zones, instanceZone, zoneIndex};
                logger.debug(
                        "The zone index from the list {} that matches the instance zone {} is {}",
                        args);
                break;
            }
            zoneIndex++;
        }
        if (zoneIndex >= zones.size()) {
            logger.warn(
                    "No match for the zone {} in the list of available zones {}",
                    instanceZone, Arrays.toString(zones.toArray()));
        } else {
            // Rearrange the zones with the instance zone first
            for (int i = 0; i < zoneIndex; i++) {
                String zone = zones.remove(0);
                zones.add(zone);
            }
        }

        // Now get the eureka urls for all the zones in the order and return it
        List<String> serviceUrls = new ArrayList<String>();
        for (String zone : zones) {
            for (String zoneCname : zoneDnsNamesMap.get(zone)) {
                List<String> ec2Urls = new ArrayList<String>(
                        getEC2DiscoveryUrlsFromZone(zoneCname,
                                DiscoveryUrlType.CNAME));
                // Rearrange the list to distribute the load in case of
                // multiple servers
                if (ec2Urls.size() > 1) {
                    this.arrangeListBasedonHostname(ec2Urls);
                }
                for (String ec2Url : ec2Urls) {
                    String serviceUrl = "http://" + ec2Url + ":"
                            + clientConfig.getEurekaServerPort()

                            + "/" + clientConfig.getEurekaServerURLContext()
                            + "/";
                    logger.debug("The EC2 url is {}", serviceUrl);
                    serviceUrls.add(serviceUrl);
                }
            }
        }
        // Rearrange the fail over server list to distribute the load
        String primaryServiceUrl = serviceUrls.remove(0);
        arrangeListBasedonHostname(serviceUrls);
        serviceUrls.add(0, primaryServiceUrl);

        logger.debug(
                "This client will talk to the following serviceUrls in order : {} ",
                Arrays.toString(serviceUrls.toArray()));
        t.stop();
        return serviceUrls;
    }

    @Override
    public List<String> getDiscoveryServiceUrls(String zone) {
        boolean shouldUseDns = clientConfig.shouldUseDnsForFetchingServiceUrls();
        if (shouldUseDns) {
            return getServiceUrlsFromDNS(zone, clientConfig.shouldPreferSameZoneEureka());
        }
        return getServiceUrlsFromConfig(zone, clientConfig.shouldPreferSameZoneEureka());
    }

    public enum DiscoveryUrlType {
        CNAME, A
    }

    /**
     * @deprecated see {@link com.netflix.appinfo.InstanceInfo#getZone(String[], com.netflix.appinfo.InstanceInfo)}
     *
     * Get the zone that a particular instance is in.
     *
     * @param myInfo
     *            - The InstanceInfo object of the instance.
     * @return - The zone in which the particular instance belongs to.
     */
    @Deprecated
    public static String getZone(InstanceInfo myInfo) {
        String[] availZones = clientConfig.getAvailabilityZones(clientConfig.getRegion());
        return InstanceInfo.getZone(availZones, myInfo);
    }

    /**
     * Get the region that this particular instance is in.
     *
     * @return - The region in which the particular instance belongs to.
     */
    public static String getRegion() {
        String region = clientConfig.getRegion();
        if (region == null) {
            region = "default";
        }
        region = region.trim().toLowerCase();
        return region;
    }

    /**
     * Get the zone based CNAMES that are bound to a region.
     *
     * @param region
     *            - The region for which the zone names need to be retrieved
     * @return - The list of CNAMES from which the zone-related information can
     *         be retrieved
     */
    static Map<String, List<String>> getZoneBasedDiscoveryUrlsFromRegion(
            String region) {
        String discoveryDnsName = null;
        try {
            discoveryDnsName = "txt." + region + "."
                    + clientConfig.getEurekaServerDNSName();

            logger.debug("The region url to be looked up is {} :",
                    discoveryDnsName);
            Set<String> zoneCnamesForRegion = new TreeSet<String>(
                    DnsResolver.getCNamesFromTxtRecord(discoveryDnsName));
            Map<String, List<String>> zoneCnameMapForRegion = new TreeMap<String, List<String>>();
            for (String zoneCname : zoneCnamesForRegion) {
                String zone = null;
                if (isEC2Url(zoneCname)) {
                    throw new RuntimeException(
                            "Cannot find the right DNS entry for "
                                    + discoveryDnsName
                                    + ". "
                                    + "Expected mapping of the format <aws_zone>.<domain_name>");
                } else {
                    String[] cnameTokens = zoneCname.split("\\.");
                    zone = cnameTokens[0];
                    logger.debug("The zoneName mapped to region {} is {}",
                            region, zone);
                }
                List<String> zoneCnamesSet = zoneCnameMapForRegion.get(zone);
                if (zoneCnamesSet == null) {
                    zoneCnamesSet = new ArrayList<String>();
                    zoneCnameMapForRegion.put(zone, zoneCnamesSet);
                }
                zoneCnamesSet.add(zoneCname);
            }
            return zoneCnameMapForRegion;
        } catch (Throwable e) {
            throw new RuntimeException("Cannot get cnames bound to the region:"
                    + discoveryDnsName, e);
        }
    }

    private static boolean isEC2Url(String zoneCname) {
        return zoneCname.startsWith("ec2");
    }

    /**
     * Get the list of EC2 URLs given the zone name.
     *
     * @param dnsName
     *            - The dns name of the zone-specific CNAME
     * @param type
     *            - CNAME or EIP that needs to be retrieved
     * @return - The list of EC2 URLs associated with the dns name
     */
    public static Set<String> getEC2DiscoveryUrlsFromZone(String dnsName,
                                                          DiscoveryUrlType type) {
        Set<String> eipsForZone = null;
        try {
            dnsName = "txt." + dnsName;
            logger.debug("The zone url to be looked up is {} :", dnsName);
            Set<String> ec2UrlsForZone = DnsResolver.getCNamesFromTxtRecord(dnsName);
            for (String ec2Url : ec2UrlsForZone) {
                logger.debug("The eureka url for the dns name {} is {}",
                        dnsName, ec2Url);
                ec2UrlsForZone.add(ec2Url);
            }
            if (DiscoveryUrlType.CNAME.equals(type)) {
                return ec2UrlsForZone;
            }
            eipsForZone = new TreeSet<String>();
            for (String cname : ec2UrlsForZone) {
                String[] tokens = cname.split("\\.");
                String ec2HostName = tokens[0];
                String[] ips = ec2HostName.split("-");
                StringBuffer eipBuffer = new StringBuffer();
                for (int ipCtr = 1; ipCtr < 5; ipCtr++) {
                    eipBuffer.append(ips[ipCtr]);
                    if (ipCtr < 4) {
                        eipBuffer.append(".");
                    }
                }
                eipsForZone.add(eipBuffer.toString());
            }
            logger.debug("The EIPS for {} is {} :", dnsName, eipsForZone);
        } catch (Throwable e) {
            throw new RuntimeException("Cannot get cnames bound to the region:"
                    + dnsName, e);
        }
        return eipsForZone;
    }

    /**
     * Gets the zone to pick up for this instance.
     *
     */
    private static int getZoneOffset(String myZone, boolean preferSameZone,
                                     String[] availZones) {
        for (int i = 0; i < availZones.length; i++) {
            if (myZone != null
                    && (availZones[i].equalsIgnoreCase(myZone.trim()) == preferSameZone)) {
                return i;
            }
        }
        logger.warn(
                "DISCOVERY: Could not pick a zone based on preferred zone settings. My zone - {}, preferSameZone- {}. "
                        + "Defaulting to " + availZones[0], myZone, preferSameZone);
        return 0;
    }

    /**
     * Check if the http status code is a success for the given action.
     *
     */
    private boolean isOk(Action action, int httpStatus) {
        if (httpStatus >= 200 && httpStatus < 300 || httpStatus == 302) {
            return true;
        } else if (Action.Renew == action && httpStatus == 404) {
            return true;
        } else if (Action.Refresh_Delta == action
                && (httpStatus == 403 || httpStatus == 404)) {
            return true;
        } else {
            return false;
        }
    }

    /**
     * Returns the eureka server which this eureka client communicates with.
     *
     * @return - The instance information that describes the eureka server.
     */
    private InstanceInfo getCoordinatingServer() {
        Application app = getApplication(DISCOVERY_APPID);
        List<InstanceInfo> discoveryInstances = null;
        InstanceInfo instanceToReturn = null;

        if (app != null) {
            discoveryInstances = app.getInstances();
        }

        if (discoveryInstances != null) {
            for (InstanceInfo instance : discoveryInstances) {
                if ((instance != null)
                        && (instance.isCoordinatingDiscoveryServer())) {
                    instanceToReturn = instance;
                    break;
                }
            }
        }
        return instanceToReturn;
    }

    private ClientResponse getUrl(String fullServiceUrl) {
        ClientResponse cr = discoveryApacheClient.resource(fullServiceUrl)
                .accept(MediaType.APPLICATION_JSON_TYPE)
                .get(ClientResponse.class);

        return cr;
    }

    /**
     * Refresh the current local instanceInfo. Note that after a valid refresh where changes are observed, the
     * isDirty flag on the instanceInfo is set to true
     */
    void refreshInstanceInfo() {
        ApplicationInfoManager.getInstance().refreshDataCenterInfoIfRequired();

        InstanceStatus status;
        try {
            status = getHealthCheckHandler().getStatus(instanceInfo.getStatus());
        } catch (Exception e) {
            logger.warn("Exception from healthcheckHandler.getStatus, setting status to DOWN", e);
            status = InstanceStatus.DOWN;
        }

        if (null != status) {
            instanceInfo.setStatus(status);
        }
    }

    /**
     * The heartbeat task that renews the lease in the given intervals.
`     */
    private class HeartbeatThread implements Runnable {

        public void run() {
            renew();
        }
    }

    @VisibleForTesting
    InstanceInfoReplicator getInstanceInfoReplicator() {
        return instanceInfoReplicator;
    }

    @VisibleForTesting
    InstanceInfo getInstanceInfo() {
        return instanceInfo;
    }

    @Override
    public HealthCheckHandler getHealthCheckHandler() {
        if (healthCheckHandler == null) {
            if (null != healthCheckHandlerProvider) {
                healthCheckHandler = healthCheckHandlerProvider.get();
            } else if (null != healthCheckCallbackProvider) {
                healthCheckHandler = new HealthCheckCallbackToHandlerBridge(healthCheckCallbackProvider.get());
            }

            if (null == healthCheckHandler) {
                healthCheckHandler = new HealthCheckCallbackToHandlerBridge(null);
            }
        }

        return healthCheckHandler;
    }

    /**
     * The task that fetches the registry information at specified intervals.
     *
     */
    class CacheRefreshThread implements Runnable {
        public void run() {
            try {
                boolean isFetchingRemoteRegionRegistries = isFetchingRemoteRegionRegistries();

                boolean remoteRegionsModified = false;
                // This makes sure that a dynamic change to remote regions to fetch is honored.
                String latestRemoteRegions = clientConfig.fetchRegistryForRemoteRegions();
                if (null != latestRemoteRegions) {
                    String currentRemoteRegions = remoteRegionsToFetch.get();
                    if (!latestRemoteRegions.equals(currentRemoteRegions)) {
                        // Both remoteRegionsToFetch and AzToRegionMapper.regionsToFetch need to be in sync
                        synchronized (instanceRegionChecker.getAzToRegionMapper()) {
                            if (remoteRegionsToFetch.compareAndSet(currentRemoteRegions, latestRemoteRegions)) {
                                String[] remoteRegions = latestRemoteRegions.split(",");
                                instanceRegionChecker.getAzToRegionMapper().setRegionsToFetch(remoteRegions);
                                remoteRegionsModified = true;
                            } else {
                                logger.info("Remote regions to fetch modified concurrently," +
                                        " ignoring change from {} to {}", currentRemoteRegions, latestRemoteRegions);
                            }
                        }
                    } else {
                        // Just refresh mapping to reflect any DNS/Property change
                        instanceRegionChecker.getAzToRegionMapper().refreshMapping();
                    }
                }

                fetchRegistry(remoteRegionsModified);

                if (logger.isDebugEnabled()) {
                    StringBuilder allAppsHashCodes = new StringBuilder();
                    allAppsHashCodes.append("Local region apps hashcode: ");
                    allAppsHashCodes.append(localRegionApps.get().getAppsHashCode());
                    allAppsHashCodes.append(", is fetching remote regions? ");
                    allAppsHashCodes.append(isFetchingRemoteRegionRegistries);
                    for (Map.Entry<String, Applications> entry : remoteRegionVsApps.entrySet()) {
                        allAppsHashCodes.append(", Remote region: ");
                        allAppsHashCodes.append(entry.getKey());
                        allAppsHashCodes.append(" , apps hashcode: ");
                        allAppsHashCodes.append(entry.getValue().getAppsHashCode());
                    }
                    logger.debug("Completed cache refresh task for discovery. All Apps hash code is {} ",
                            allAppsHashCodes.toString());
                }
            } catch (Throwable th) {
                logger.error("Cannot fetch registry from server", th);
            }
        }
    }

    /**
     * Fetch the registry information from back up registry if all eureka server
     * urls are unreachable.
     */
    private void fetchRegistryFromBackup() {
        try {
            @SuppressWarnings("deprecation")
            BackupRegistry backupRegistryInstance = newBackupRegistryInstance();
            if (null == backupRegistryInstance) { // backward compatibility with the old protected method, in case it is being used.
                backupRegistryInstance = backupRegistryProvider.get();
            }

            if (null != backupRegistryInstance) {
                Applications apps = null;
                if (isFetchingRemoteRegionRegistries()) {
                    String remoteRegionsStr = remoteRegionsToFetch.get();
                    if (null != remoteRegionsStr) {
                        apps = backupRegistryInstance.fetchRegistry(remoteRegionsStr.split(","));
                    }
                } else {
                    apps = backupRegistryInstance.fetchRegistry();
                }
                if (apps != null) {
                    final Applications applications = this.filterAndShuffle(apps);
                    applications.setAppsHashCode(applications.getReconcileHashCode());
                    localRegionApps.set(applications);
                    logTotalInstances();
                    logger.info("Fetched registry successfully from the backup");
                }
            } else {
                logger.warn("No backup registry instance defined & unable to find any discovery servers.");
            }
        } catch (Throwable e) {
            logger.warn("Cannot fetch applications from apps although backup registry was specified", e);
        }
    }

    /**
     * @deprecated Use injection to provide {@link BackupRegistry} implementation.
     */
    @Deprecated
    @Nullable
    protected BackupRegistry newBackupRegistryInstance()
            throws ClassNotFoundException, IllegalAccessException, InstantiationException {
        return null;
    }

    /**
     * Gets the task that is responsible for fetching the eureka service Urls.
     *
     * @param zone
     *            the zone in which the instance resides.
     * @return TimerTask the task which executes periodically.
     */
    private TimerTask getServiceUrlUpdateTask(final String zone) {
        return new TimerTask() {
            @Override
            public void run() {
                try {
                    List<String> serviceUrlList = getDiscoveryServiceUrls(zone);
                    if (serviceUrlList.isEmpty()) {
                        logger.warn("The service url list is empty");
                        return;
                    }
                    if (!serviceUrlList.equals(eurekaServiceUrls.get())) {
                        logger.info(
                                "Updating the serviceUrls as they seem to have changed from {} to {} ",
                                Arrays.toString(eurekaServiceUrls.get()
                                        .toArray()), Arrays
                                        .toString(serviceUrlList.toArray()));

                        eurekaServiceUrls.set(serviceUrlList);
                    }
                } catch (Throwable e) {
                    logger.error("Cannot get the eureka service urls :", e);
                }

            }
        };
    }

    /**
     * Gets the <em>applications</em> after filtering the applications for
     * instances with only UP states and shuffling them.
     *
     * <p>
     * The filtering depends on the option specified by the configuration
     * {@link EurekaClientConfig#shouldFilterOnlyUpInstances()}. Shuffling helps
     * in randomizing the applications list there by avoiding the same instances
     * receiving traffic during start ups.
     * </p>
     *
     * @param apps
     *            The applications that needs to be filtered and shuffled.
     * @return The applications after the filter and the shuffle.
     */
    private Applications filterAndShuffle(Applications apps) {
        if (apps != null) {
            if (isFetchingRemoteRegionRegistries()) {
                Map<String, Applications> remoteRegionVsApps = new ConcurrentHashMap<String, Applications>();
                apps.shuffleAndIndexInstances(remoteRegionVsApps, clientConfig, instanceRegionChecker);
                for (Applications applications : remoteRegionVsApps.values()) {
                    applications.shuffleInstances(clientConfig.shouldFilterOnlyUpInstances());
                }
                this.remoteRegionVsApps = remoteRegionVsApps;
            } else {
                apps.shuffleInstances(clientConfig.shouldFilterOnlyUpInstances());
            }
        }
        return apps;
    }

    private boolean isFetchingRemoteRegionRegistries() {
        return null != remoteRegionsToFetch.get();
    }


    private void arrangeListBasedonHostname(List<String> list) {
        int listSize = 0;
        if (list != null) {
            listSize = list.size();
        }
        if ((this.instanceInfo == null) || (listSize == 0)) {
            return;
        }
        // Find the hashcode of the instance hostname and use it to find an entry
        // and then arrange the rest of the entries after this entry.
        int instanceHashcode = this.instanceInfo.getHostName().hashCode();
        if (instanceHashcode < 0) {
            instanceHashcode = instanceHashcode * -1;
        }
        int backupInstance = instanceHashcode % listSize;
        for (int i = 0; i < backupInstance; i++) {
            String zone = list.remove(0);
            list.add(zone);
        }
    }

    
    /**
     * Invoked when the remote status of this client has changed.
     * Subclasses may override this method to implement custom behavior if needed.
     * 
     * @param oldStatus the previous remote {@link InstanceStatus}
     * @param newStatus the new remote {@link InstanceStatus} 
     */
    protected void onRemoteStatusChanged(InstanceInfo.InstanceStatus oldStatus, InstanceInfo.InstanceStatus newStatus) {
    	fireEvent(new StatusChangeEvent(oldStatus, newStatus));
    }
    
    /**
     * Invoked every time the local registry cache is refreshed (whether changes have 
     * been detected or not).
     * 
     * Subclasses may override this method to implement custom behavior if needed.
     */
    protected void onCacheRefreshed() {
    	fireEvent(new CacheRefreshedEvent());
    }


    /**
     * Send the given event on the EventBus if one is available
     * 
     * @param event the event to send on the eventBus
     */
    protected void fireEvent(DiscoveryEvent event) {
    	// Publish event if an EventBus is available
        if (eventBus != null) {
            eventBus.publish(event);
        }
    }
}


File: eureka-client/src/main/java/com/netflix/discovery/StatusChangeEvent.java
package com.netflix.discovery;

import com.netflix.appinfo.InstanceInfo;

/**
 * Event containing the latest instance status information.  This event
 * is sent to the {@link com.netflix.eventbus.spi.EventBus} by {@link EurekaClient) whenever
 * a status change is identified from the remote Eureka server response.
 *
 * @author elandau
 *
 */
public class StatusChangeEvent extends DiscoveryEvent {
    private final InstanceInfo.InstanceStatus current;
    private final InstanceInfo.InstanceStatus previous;

    public StatusChangeEvent(InstanceInfo.InstanceStatus previous, InstanceInfo.InstanceStatus current) {
        this.current = current;
        this.previous = previous;
    }

    /**
     * Return the up current when the event was generated.
     * @return true if current is up or false for ALL other current values
     */
    public boolean isUp() {
        return this.current.equals(InstanceInfo.InstanceStatus.UP);
    }

    /**
     * @return The current at the time the event is generated.
     */
    public InstanceInfo.InstanceStatus getStatus() {
        return current;
    }

    /**
     * @return Return the client status immediately before the change
     */
    public InstanceInfo.InstanceStatus getPreviousStatus() {
        return previous;
    }

    @Override
    public String toString() {
        return "StatusChangeEvent [current=" + current + ", previous="
                + previous + "]";
    }

}


File: eureka-client/src/test/java/com/netflix/discovery/AbstractDiscoveryClientTester.java
package com.netflix.discovery;

import javax.annotation.Nullable;
import java.util.Arrays;
import java.util.List;

import com.netflix.appinfo.AmazonInfo;
import com.netflix.appinfo.InstanceInfo;
import com.netflix.appinfo.LeaseInfo;
import com.netflix.discovery.shared.Application;
import org.junit.After;
import org.junit.Before;
import org.junit.Rule;

/**
 * @author Nitesh Kant
 */
public class AbstractDiscoveryClientTester {

    public static final String REMOTE_REGION = "myregion";
    public static final String REMOTE_ZONE = "myzone";
    public static final int CLIENT_REFRESH_RATE = 10;

    public static final String ALL_REGIONS_VIP1_ADDR = "myvip1";
    public static final String REMOTE_REGION_APP1_INSTANCE1_HOSTNAME = "blah1-1";
    public static final String REMOTE_REGION_APP1_INSTANCE2_HOSTNAME = "blah1-2";
    public static final String LOCAL_REGION_APP1_NAME = "MYAPP1_LOC";
    public static final String LOCAL_REGION_APP1_INSTANCE1_HOSTNAME = "blahloc1-1";
    public static final String LOCAL_REGION_APP1_INSTANCE2_HOSTNAME = "blahloc1-2";
    public static final String REMOTE_REGION_APP1_NAME = "MYAPP1";

    public static final String ALL_REGIONS_VIP2_ADDR = "myvip2";
    public static final String REMOTE_REGION_APP2_INSTANCE1_HOSTNAME = "blah2-1";
    public static final String REMOTE_REGION_APP2_INSTANCE2_HOSTNAME = "blah2-2";
    public static final String LOCAL_REGION_APP2_NAME = "MYAPP2_LOC";
    public static final String LOCAL_REGION_APP2_INSTANCE1_HOSTNAME = "blahloc2-1";
    public static final String LOCAL_REGION_APP2_INSTANCE2_HOSTNAME = "blahloc2-2";
    public static final String REMOTE_REGION_APP2_NAME = "MYAPP2";

    public static final String ALL_REGIONS_VIP3_ADDR = "myvip3";
    public static final String LOCAL_REGION_APP3_NAME = "MYAPP3_LOC";
    public static final String LOCAL_REGION_APP3_INSTANCE1_HOSTNAME = "blahloc3-1";

    @Rule
    public MockRemoteEurekaServer mockLocalEurekaServer = new MockRemoteEurekaServer();
    protected EurekaClient client;

    @Before
    public void setUp() throws Exception {

        setupProperties();

        populateLocalRegistryAtStartup();
        populateRemoteRegistryAtStartup();

        setupDiscoveryClient();
    }

    protected void setupProperties() {
        DiscoveryClientRule.setupDiscoveryClientConfig(mockLocalEurekaServer.getPort(),
                MockRemoteEurekaServer.EUREKA_API_BASE_PATH);
    }

    protected void setupDiscoveryClient() {
        setupDiscoveryClient(30);
    }

    protected void setupDiscoveryClient(int renewalIntervalInSecs) {
        InstanceInfo instanceInfo = newInstanceInfoBuilder(renewalIntervalInSecs).build();
        client = DiscoveryClientRule.setupDiscoveryClient(instanceInfo);
    }

    protected InstanceInfo.Builder newInstanceInfoBuilder(int renewalIntervalInSecs) {
        return DiscoveryClientRule.newInstanceInfoBuilder(renewalIntervalInSecs);
    }

    protected void shutdownDiscoveryClient() {
        if (client != null) {
            client.shutdown();
        }
    }

    @After
    public void tearDown() throws Exception {
        shutdownDiscoveryClient();
        DiscoveryClientRule.clearDiscoveryClientConfig();
    }

    protected void addLocalAppDelta() {
        Application myappDelta = new Application(LOCAL_REGION_APP3_NAME);
        InstanceInfo instanceInfo = createInstance(LOCAL_REGION_APP3_NAME, ALL_REGIONS_VIP3_ADDR,
                LOCAL_REGION_APP3_INSTANCE1_HOSTNAME, null);
        instanceInfo.setActionType(InstanceInfo.ActionType.ADDED);
        myappDelta.addInstance(instanceInfo);
        mockLocalEurekaServer.addLocalRegionAppsDelta(LOCAL_REGION_APP3_NAME, myappDelta);
    }

    private void populateLocalRegistryAtStartup() {
        for (Application app : createLocalApps()) {
            mockLocalEurekaServer.addLocalRegionApps(app.getName(), app);
        }

        for (Application appDelta : createLocalAppsDelta()) {
            mockLocalEurekaServer.addLocalRegionAppsDelta(appDelta.getName(), appDelta);
        }
    }

    private void populateRemoteRegistryAtStartup() {
        for (Application app : createRemoteApps()) {
            mockLocalEurekaServer.addRemoteRegionApps(app.getName(), app);
        }

        for (Application appDelta : createRemoteAppsDelta()) {
            mockLocalEurekaServer.addRemoteRegionAppsDelta(appDelta.getName(), appDelta);
        }
    }

    private static List<Application> createRemoteApps() {
        Application myapp1 = new Application(REMOTE_REGION_APP1_NAME);
        InstanceInfo instanceInfo1 = createInstance(REMOTE_REGION_APP1_NAME, ALL_REGIONS_VIP1_ADDR,
                REMOTE_REGION_APP1_INSTANCE1_HOSTNAME, REMOTE_ZONE);
        myapp1.addInstance(instanceInfo1);

        Application myapp2 = new Application(REMOTE_REGION_APP2_NAME);
        InstanceInfo instanceInfo2 = createInstance(REMOTE_REGION_APP2_NAME, ALL_REGIONS_VIP2_ADDR,
                REMOTE_REGION_APP2_INSTANCE1_HOSTNAME, REMOTE_ZONE);
        myapp2.addInstance(instanceInfo2);

        return Arrays.asList(myapp1, myapp2);
    }

    private static List<Application> createRemoteAppsDelta() {
        Application myapp1 = new Application(REMOTE_REGION_APP1_NAME);
        InstanceInfo instanceInfo1 = createInstance(REMOTE_REGION_APP1_NAME, ALL_REGIONS_VIP1_ADDR,
                REMOTE_REGION_APP1_INSTANCE2_HOSTNAME, REMOTE_ZONE);
        instanceInfo1.setActionType(InstanceInfo.ActionType.ADDED);
        myapp1.addInstance(instanceInfo1);

        Application myapp2 = new Application(REMOTE_REGION_APP2_NAME);
        InstanceInfo instanceInfo2 = createInstance(REMOTE_REGION_APP2_NAME, ALL_REGIONS_VIP2_ADDR,
                REMOTE_REGION_APP2_INSTANCE2_HOSTNAME, REMOTE_ZONE);
        instanceInfo2.setActionType(InstanceInfo.ActionType.ADDED);
        myapp2.addInstance(instanceInfo2);

        return Arrays.asList(myapp1, myapp2);
    }

    private static List<Application> createLocalApps() {
        Application myapp1 = new Application(LOCAL_REGION_APP1_NAME);
        InstanceInfo instanceInfo1 = createInstance(LOCAL_REGION_APP1_NAME, ALL_REGIONS_VIP1_ADDR,
                LOCAL_REGION_APP1_INSTANCE1_HOSTNAME, null);
        myapp1.addInstance(instanceInfo1);

        Application myapp2 = new Application(LOCAL_REGION_APP2_NAME);
        InstanceInfo instanceInfo2 = createInstance(LOCAL_REGION_APP2_NAME, ALL_REGIONS_VIP2_ADDR,
                LOCAL_REGION_APP2_INSTANCE1_HOSTNAME, null);
        myapp2.addInstance(instanceInfo2);

        return Arrays.asList(myapp1, myapp2);
    }

    private static List<Application> createLocalAppsDelta() {
        Application myapp1 = new Application(LOCAL_REGION_APP1_NAME);
        InstanceInfo instanceInfo1 = createInstance(LOCAL_REGION_APP1_NAME, ALL_REGIONS_VIP1_ADDR,
                LOCAL_REGION_APP1_INSTANCE2_HOSTNAME, null);
        instanceInfo1.setActionType(InstanceInfo.ActionType.ADDED);
        myapp1.addInstance(instanceInfo1);

        Application myapp2 = new Application(LOCAL_REGION_APP2_NAME);
        InstanceInfo instanceInfo2 = createInstance(LOCAL_REGION_APP2_NAME, ALL_REGIONS_VIP2_ADDR,
                LOCAL_REGION_APP2_INSTANCE2_HOSTNAME, null);
        instanceInfo2.setActionType(InstanceInfo.ActionType.ADDED);
        myapp2.addInstance(instanceInfo2);

        return Arrays.asList(myapp1, myapp2);
    }

    private static InstanceInfo createInstance(String appName, String vipAddress, String instanceHostName, String zone) {
        InstanceInfo.Builder instanceBuilder = InstanceInfo.Builder.newBuilder();
        instanceBuilder.setAppName(appName);
        instanceBuilder.setVIPAddress(vipAddress);
        instanceBuilder.setHostName(instanceHostName);
        instanceBuilder.setIPAddr("10.10.101.1");
        AmazonInfo amazonInfo = getAmazonInfo(zone, instanceHostName);
        instanceBuilder.setDataCenterInfo(amazonInfo);
        instanceBuilder.setMetadata(amazonInfo.getMetadata());
        instanceBuilder.setLeaseInfo(LeaseInfo.Builder.newBuilder().build());
        return instanceBuilder.build();
    }

    private static AmazonInfo getAmazonInfo(@Nullable String availabilityZone, String instanceHostName) {
        AmazonInfo.Builder azBuilder = AmazonInfo.Builder.newBuilder();
        azBuilder.addMetadata(AmazonInfo.MetaDataKey.availabilityZone, null == availabilityZone ? "us-east-1a" : availabilityZone);
        azBuilder.addMetadata(AmazonInfo.MetaDataKey.instanceId, instanceHostName);
        azBuilder.addMetadata(AmazonInfo.MetaDataKey.amiId, "XXX");
        azBuilder.addMetadata(AmazonInfo.MetaDataKey.instanceType, "XXX");
        azBuilder.addMetadata(AmazonInfo.MetaDataKey.localIpv4, "XXX");
        azBuilder.addMetadata(AmazonInfo.MetaDataKey.publicIpv4, "XXX");
        azBuilder.addMetadata(AmazonInfo.MetaDataKey.publicHostname, instanceHostName);
        return azBuilder.build();
    }
}


File: eureka-client/src/test/java/com/netflix/discovery/BackUpRegistryTest.java
package com.netflix.discovery;

import javax.annotation.Nullable;
import java.util.List;
import java.util.UUID;

import com.google.inject.Provider;
import com.netflix.appinfo.AmazonInfo;
import com.netflix.appinfo.DataCenterInfo;
import com.netflix.appinfo.InstanceInfo;
import com.netflix.config.ConfigurationManager;
import com.netflix.discovery.shared.Application;
import com.netflix.discovery.shared.Applications;
import org.junit.After;
import org.junit.Assert;
import org.junit.Test;

/**
 * @author Nitesh Kant
 */
public class BackUpRegistryTest {


    public static final String ALL_REGIONS_VIP_ADDR = "myvip";
    public static final String REMOTE_REGION_INSTANCE_1_HOSTNAME = "blah";
    public static final String REMOTE_REGION_INSTANCE_2_HOSTNAME = "blah2";

    public static final String LOCAL_REGION_APP_NAME = "MYAPP_LOC";
    public static final String LOCAL_REGION_INSTANCE_1_HOSTNAME = "blahloc";
    public static final String LOCAL_REGION_INSTANCE_2_HOSTNAME = "blahloc2";

    public static final String REMOTE_REGION_APP_NAME = "MYAPP";
    public static final String REMOTE_REGION = "myregion";
    public static final String REMOTE_ZONE = "myzone";
    public static final int CLIENT_REFRESH_RATE = 10;
    public static final int NOT_AVAILABLE_EUREKA_PORT = 756473;

    private EurekaClient client;
    private MockBackupRegistry backupRegistry;

    public void setUp(boolean enableRemote) throws Exception {
        ConfigurationManager.getConfigInstance().setProperty("eureka.client.refresh.interval", CLIENT_REFRESH_RATE);
        ConfigurationManager.getConfigInstance().setProperty("eureka.registration.enabled", "false");
        if (enableRemote) {
            ConfigurationManager.getConfigInstance().setProperty("eureka.fetchRemoteRegionsRegistry", REMOTE_REGION);
        }
        ConfigurationManager.getConfigInstance().setProperty("eureka.myregion.availabilityZones", REMOTE_ZONE);
        ConfigurationManager.getConfigInstance().setProperty("eureka.backupregistry", MockBackupRegistry.class.getName());
        ConfigurationManager.getConfigInstance().setProperty("eureka.serviceUrl.default",
                "http://localhost:" + NOT_AVAILABLE_EUREKA_PORT /*Should always be unavailable*/
                        +
                        MockRemoteEurekaServer.EUREKA_API_BASE_PATH);

        InstanceInfo.Builder builder = InstanceInfo.Builder.newBuilder();
        builder.setIPAddr("10.10.101.00");
        builder.setHostName("Hosttt");
        builder.setAppName("EurekaTestApp-" + UUID.randomUUID());
        builder.setDataCenterInfo(new DataCenterInfo() {
            @Override
            public Name getName() {
                return Name.MyOwn;
            }
        });

        backupRegistry = new MockBackupRegistry();
        setupBackupMock();
        client = new DiscoveryClient(builder.build(), new DefaultEurekaClientConfig(), null,
                new Provider<BackupRegistry>() {
                    @Override
                    public BackupRegistry get() {
                        return backupRegistry;
                    }
                });
    }

    @After
    public void tearDown() throws Exception {
        client.shutdown();
        ConfigurationManager.getConfigInstance().clear();
    }

    @Test
    public void testLocalOnly() throws Exception {
        setUp(false);
        Applications applications = client.getApplications();
        List<Application> registeredApplications = applications.getRegisteredApplications();
        System.out.println("***" + registeredApplications);
        Assert.assertNotNull("Local region apps not found.", registeredApplications);
        Assert.assertEquals("Local apps size not as expected.", 1, registeredApplications.size());
        Assert.assertEquals("Local region apps not present.", LOCAL_REGION_APP_NAME, registeredApplications.get(0).getName());
    }

    @Test
    public void testRemoteEnabledButLocalOnlyQuried() throws Exception {
        setUp(true);
        Applications applications = client.getApplications();
        List<Application> registeredApplications = applications.getRegisteredApplications();
        Assert.assertNotNull("Local region apps not found.", registeredApplications);
        Assert.assertEquals("Local apps size not as expected.", 2, registeredApplications.size()); // Remote region comes with no instances.
        Application localRegionApp = null;
        Application remoteRegionApp = null;
        for (Application registeredApplication : registeredApplications) {
            if (registeredApplication.getName().equals(LOCAL_REGION_APP_NAME)) {
                localRegionApp = registeredApplication;
            } else if (registeredApplication.getName().equals(REMOTE_REGION_APP_NAME)) {
                remoteRegionApp = registeredApplication;
            }
        }
        Assert.assertNotNull("Local region apps not present.", localRegionApp);
        Assert.assertTrue("Remote region instances returned for local query.", null == remoteRegionApp || remoteRegionApp.getInstances().isEmpty());
    }

    @Test
    public void testRemoteEnabledAndQuried() throws Exception {
        setUp(true);
        Applications applications = client.getApplicationsForARegion(REMOTE_REGION);
        List<Application> registeredApplications = applications.getRegisteredApplications();
        Assert.assertNotNull("Remote region apps not found.", registeredApplications);
        Assert.assertEquals("Remote apps size not as expected.", 1, registeredApplications.size());
        Assert.assertEquals("Remote region apps not present.", REMOTE_REGION_APP_NAME, registeredApplications.get(0).getName());
    }

    @Test
    public void testAppsHashCode() throws Exception {
        setUp(true);
        Applications applications = client.getApplications();

        Assert.assertEquals("UP_1_", applications.getAppsHashCode());
    }

    private void setupBackupMock() {
        Application localApp = createLocalApps();
        Applications localApps = new Applications();
        localApps.addApplication(localApp);
        backupRegistry.setLocalRegionApps(localApps);
        Application remoteApp = createRemoteApps();
        Applications remoteApps = new Applications();
        remoteApps.addApplication(remoteApp);
        backupRegistry.getRemoteRegionVsApps().put(REMOTE_REGION, remoteApps);
    }

    private Application createLocalApps() {
        Application myapp = new Application(LOCAL_REGION_APP_NAME);
        InstanceInfo instanceInfo = createLocalInstance(LOCAL_REGION_INSTANCE_1_HOSTNAME);
        myapp.addInstance(instanceInfo);
        return myapp;
    }


    private Application createRemoteApps() {
        Application myapp = new Application(REMOTE_REGION_APP_NAME);
        InstanceInfo instanceInfo = createRemoteInstance(REMOTE_REGION_INSTANCE_1_HOSTNAME);
        myapp.addInstance(instanceInfo);
        return myapp;
    }

    private InstanceInfo createRemoteInstance(String instanceHostName) {
        InstanceInfo.Builder instanceBuilder = InstanceInfo.Builder.newBuilder();
        instanceBuilder.setAppName(REMOTE_REGION_APP_NAME);
        instanceBuilder.setVIPAddress(ALL_REGIONS_VIP_ADDR);
        instanceBuilder.setHostName(instanceHostName);
        instanceBuilder.setIPAddr("10.10.101.1");
        AmazonInfo amazonInfo = getAmazonInfo(REMOTE_ZONE, instanceHostName);
        instanceBuilder.setDataCenterInfo(amazonInfo);
        instanceBuilder.setMetadata(amazonInfo.getMetadata());
        return instanceBuilder.build();
    }

    private InstanceInfo createLocalInstance(String instanceHostName) {
        InstanceInfo.Builder instanceBuilder = InstanceInfo.Builder.newBuilder();
        instanceBuilder.setAppName(LOCAL_REGION_APP_NAME);
        instanceBuilder.setVIPAddress(ALL_REGIONS_VIP_ADDR);
        instanceBuilder.setHostName(instanceHostName);
        instanceBuilder.setIPAddr("10.10.101.1");
        AmazonInfo amazonInfo = getAmazonInfo(null, instanceHostName);
        instanceBuilder.setDataCenterInfo(amazonInfo);
        instanceBuilder.setMetadata(amazonInfo.getMetadata());
        return instanceBuilder.build();
    }

    private AmazonInfo getAmazonInfo(@Nullable String availabilityZone, String instanceHostName) {
        AmazonInfo.Builder azBuilder = AmazonInfo.Builder.newBuilder();
        azBuilder.addMetadata(AmazonInfo.MetaDataKey.availabilityZone, (null == availabilityZone) ? "us-east-1a" : availabilityZone);
        azBuilder.addMetadata(AmazonInfo.MetaDataKey.instanceId, instanceHostName);
        azBuilder.addMetadata(AmazonInfo.MetaDataKey.amiId, "XXX");
        azBuilder.addMetadata(AmazonInfo.MetaDataKey.instanceType, "XXX");
        azBuilder.addMetadata(AmazonInfo.MetaDataKey.localIpv4, "XXX");
        azBuilder.addMetadata(AmazonInfo.MetaDataKey.publicIpv4, "XXX");
        azBuilder.addMetadata(AmazonInfo.MetaDataKey.publicHostname, instanceHostName);
        return azBuilder.build();
    }
}


File: eureka-client/src/test/java/com/netflix/discovery/DiscoveryClientRegisterUpdateTest.java
package com.netflix.discovery;

import com.netflix.appinfo.ApplicationInfoManager;
import com.netflix.appinfo.InstanceInfo;
import com.netflix.appinfo.MyDataCenterInstanceConfig;
import com.netflix.config.ConfigurationManager;
import org.junit.After;
import org.junit.Assert;
import org.junit.Before;
import org.junit.Test;

import java.util.Arrays;
import java.util.Map;
import java.util.UUID;

/**
 * @author David Liu
 */
public class DiscoveryClientRegisterUpdateTest {

    private TestApplicationInfoManager applicationInfoManager;
    private MockRemoteEurekaServer mockLocalEurekaServer;
    private EurekaClient client;

    @Before
    public void setUp() throws Exception {
        mockLocalEurekaServer = new MockRemoteEurekaServer();
        mockLocalEurekaServer.start();

        ConfigurationManager.getConfigInstance().setProperty("eureka.name", "EurekaTestApp-" + UUID.randomUUID());
        ConfigurationManager.getConfigInstance().setProperty("eureka.registration.enabled", "true");
        ConfigurationManager.getConfigInstance().setProperty("eureka.appinfo.replicate.interval", 2);
        ConfigurationManager.getConfigInstance().setProperty("eureka.shouldFetchRegistry", "false");
        ConfigurationManager.getConfigInstance().setProperty("eureka.serviceUrl.default",
                "http://localhost:" + mockLocalEurekaServer.getPort() +
                        MockRemoteEurekaServer.EUREKA_API_BASE_PATH);

        applicationInfoManager = new TestApplicationInfoManager();
        applicationInfoManager.initComponent(new MyDataCenterInstanceConfig());
        client = new DiscoveryClient(applicationInfoManager.getInfo(), new DefaultEurekaClientConfig());
    }

    @After
    public void tearDown() throws Exception {
        client.shutdown();
        mockLocalEurekaServer.stop();
        ConfigurationManager.getConfigInstance().clear();
    }

    @Test
    public void registerUpdateLifecycleTest() throws Exception {
        applicationInfoManager.setInstanceStatus(InstanceInfo.InstanceStatus.UP);
        Thread.sleep(400);  // give some execution time
        applicationInfoManager.setInstanceStatus(InstanceInfo.InstanceStatus.UNKNOWN);
        Thread.sleep(400);  // give some execution time
        applicationInfoManager.setInstanceStatus(InstanceInfo.InstanceStatus.DOWN);

        Thread.sleep(2400);

        Assert.assertEquals(Arrays.asList("UP", "UNKNOWN", "DOWN"), mockLocalEurekaServer.registrationStatuses);
        Assert.assertEquals(3, mockLocalEurekaServer.registerCount.get());
    }

    /**
     * This test is similar to the normal lifecycle test, but don't sleep between calls of setInstanceStatus
     */
    @Test
    public void registerUpdateQuickLifecycleTest() throws Exception {
        applicationInfoManager.setInstanceStatus(InstanceInfo.InstanceStatus.UP);
        applicationInfoManager.setInstanceStatus(InstanceInfo.InstanceStatus.UNKNOWN);
        applicationInfoManager.setInstanceStatus(InstanceInfo.InstanceStatus.DOWN);
        Thread.sleep(400);
        // this call will be rate limited, but will be transmitted by the automatic update after 10s
        applicationInfoManager.setInstanceStatus(InstanceInfo.InstanceStatus.UP);
        Thread.sleep(2400);

        Assert.assertEquals(Arrays.asList("DOWN", "UP"), mockLocalEurekaServer.registrationStatuses);
        Assert.assertEquals(2, mockLocalEurekaServer.registerCount.get());
    }

    @Test
    public void registerUpdateShutdownTest() throws Exception {
        Assert.assertEquals(1, applicationInfoManager.getStatusChangeListeners().size());
        client.shutdown();
        Assert.assertEquals(0, applicationInfoManager.getStatusChangeListeners().size());
    }

    @Test
    public void testRegistrationDisabled() throws Exception {
        client.shutdown();  // shutdown the default @Before client first

        ConfigurationManager.getConfigInstance().setProperty("eureka.registration.enabled", "false");
        client = new DiscoveryClient(applicationInfoManager.getInfo(), new DefaultEurekaClientConfig());
        Assert.assertEquals(0, applicationInfoManager.getStatusChangeListeners().size());
        applicationInfoManager.setInstanceStatus(InstanceInfo.InstanceStatus.DOWN);
        applicationInfoManager.setInstanceStatus(InstanceInfo.InstanceStatus.UP);
        Thread.sleep(400);
        client.shutdown();
        Assert.assertEquals(0, applicationInfoManager.getStatusChangeListeners().size());
    }

    public class TestApplicationInfoManager extends ApplicationInfoManager {
        TestApplicationInfoManager() {
            super(null, null);
        }

        public Map<String, StatusChangeListener> getStatusChangeListeners() {
            return this.listeners;
        }
    }
}


File: eureka-client/src/test/java/com/netflix/discovery/DiscoveryClientRule.java
package com.netflix.discovery;

import java.util.UUID;
import java.util.concurrent.Callable;

import com.netflix.appinfo.ApplicationInfoManager;
import com.netflix.appinfo.DataCenterInfo;
import com.netflix.appinfo.InstanceInfo;
import com.netflix.appinfo.LeaseInfo;
import com.netflix.appinfo.MyDataCenterInstanceConfig;
import com.netflix.config.ConfigurationManager;
import org.junit.rules.ExternalResource;

/**
 * JUnit rule for discovery client + collection of static methods for setting it up.
 */
public class DiscoveryClientRule extends ExternalResource {

    public static final String REMOTE_REGION = "myregion";
    public static final String REMOTE_ZONE = "myzone";
    public static final int CLIENT_REFRESH_RATE = 10;

    private final boolean registrationEnabled;
    private final boolean registryFetchEnabled;
    private final Callable<Integer> portResolverCallable;
    private final InstanceInfo instance;

    private EurekaClient client;

    DiscoveryClientRule(DiscoveryClientRuleBuilder builder) {
        this.registrationEnabled = builder.registrationEnabled;
        this.registryFetchEnabled = builder.registryFetchEnabled;
        this.portResolverCallable = builder.portResolverCallable;
        this.instance = builder.instance;
    }

    public EurekaClient getClient() {
        if (client == null) {
            int port;
            try {
                port = portResolverCallable.call();
            } catch (Exception e) {
                throw new RuntimeException("Cannot resolve discovery server port number", e);
            }
            setupDiscoveryClientConfig(port, "/eureka/v2/");

            ConfigurationManager.getConfigInstance().setProperty("eureka.registration.enabled", Boolean.valueOf(registrationEnabled));
            ConfigurationManager.getConfigInstance().setProperty("eureka.shouldFetchRegistry", Boolean.valueOf(registryFetchEnabled));

            InstanceInfo clientInstanceInfo = instance == null ? newInstanceInfoBuilder(30).build() : instance;
            client = setupDiscoveryClient(clientInstanceInfo);
        }
        return client;
    }

    @Override
    protected void after() {
        if (client != null) {
            client.shutdown();
        }
        clearDiscoveryClientConfig();
    }

    public static DiscoveryClientRuleBuilder newBuilder() {
        return new DiscoveryClientRuleBuilder();
    }

    public static void setupDiscoveryClientConfig(int serverPort, String path) {
        ConfigurationManager.getConfigInstance().setProperty("eureka.shouldFetchRegistry", "true");
        ConfigurationManager.getConfigInstance().setProperty("eureka.responseCacheAutoExpirationInSeconds", "10");
        ConfigurationManager.getConfigInstance().setProperty("eureka.client.refresh.interval", CLIENT_REFRESH_RATE);
        ConfigurationManager.getConfigInstance().setProperty("eureka.registration.enabled", "false");
        ConfigurationManager.getConfigInstance().setProperty("eureka.fetchRemoteRegionsRegistry", REMOTE_REGION);
        ConfigurationManager.getConfigInstance().setProperty("eureka.myregion.availabilityZones", REMOTE_ZONE);
        ConfigurationManager.getConfigInstance().setProperty("eureka.serviceUrl.default",
                "http://localhost:" + serverPort + path);
    }

    public static void clearDiscoveryClientConfig() {
        ConfigurationManager.getConfigInstance().clearProperty("eureka.client.refresh.interval");
        ConfigurationManager.getConfigInstance().clearProperty("eureka.registration.enabled");
        ConfigurationManager.getConfigInstance().clearProperty("eureka.fetchRemoteRegionsRegistry");
        ConfigurationManager.getConfigInstance().clearProperty("eureka.myregion.availabilityZones");
        ConfigurationManager.getConfigInstance().clearProperty("eureka.serviceUrl.default");
    }

    public static EurekaClient setupDiscoveryClient(InstanceInfo clientInstanceInfo) {
        DefaultEurekaClientConfig config = new DefaultEurekaClientConfig();
        // setup config in advance, used in initialize converter
        DiscoveryManager.getInstance().setEurekaClientConfig(config);
        EurekaClient client = new DiscoveryClient(clientInstanceInfo, config);
        ApplicationInfoManager.getInstance().initComponent(new MyDataCenterInstanceConfig());
        return client;
    }

    public static InstanceInfo.Builder newInstanceInfoBuilder(int renewalIntervalInSecs) {
        InstanceInfo.Builder builder = InstanceInfo.Builder.newBuilder();
        builder.setIPAddr("10.10.101.00");
        builder.setHostName("Hosttt");
        builder.setAppName("EurekaTestApp-" + UUID.randomUUID());
        builder.setDataCenterInfo(new DataCenterInfo() {
            @Override
            public Name getName() {
                return Name.MyOwn;
            }
        });
        builder.setLeaseInfo(LeaseInfo.Builder.newBuilder().setRenewalIntervalInSecs(renewalIntervalInSecs).build());
        return builder;
    }

    public static class DiscoveryClientRuleBuilder {
        private boolean registrationEnabled;
        private boolean registryFetchEnabled;
        private Callable<Integer> portResolverCallable;
        private InstanceInfo instance;

        public DiscoveryClientRuleBuilder registration(boolean enabled) {
            this.registrationEnabled = enabled;
            return this;
        }

        public DiscoveryClientRuleBuilder registryFetch(boolean enabled) {
            this.registryFetchEnabled = enabled;
            return this;
        }

        public DiscoveryClientRuleBuilder portResolver(Callable<Integer> portResolverCallable) {
            this.portResolverCallable = portResolverCallable;
            return this;
        }

        public DiscoveryClientRuleBuilder instanceInfo(InstanceInfo instance) {
            this.instance = instance;
            return this;
        }

        public DiscoveryClientRule build() {
            return new DiscoveryClientRule(this);
        }
    }
}


File: eureka-client/src/test/java/com/netflix/discovery/MockRemoteEurekaServer.java
package com.netflix.discovery;

import javax.servlet.ServletException;
import javax.servlet.http.HttpServletRequest;
import javax.servlet.http.HttpServletResponse;
import java.io.BufferedReader;
import java.io.IOException;
import java.util.ArrayList;
import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.concurrent.atomic.AtomicBoolean;
import java.util.concurrent.atomic.AtomicLong;
import java.util.regex.Matcher;
import java.util.regex.Pattern;

import com.netflix.appinfo.AbstractEurekaIdentity;
import com.netflix.appinfo.EurekaClientIdentity;
import com.netflix.appinfo.InstanceInfo;
import com.netflix.discovery.converters.XmlXStream;
import com.netflix.discovery.shared.Application;
import com.netflix.discovery.shared.Applications;
import org.junit.Assert;
import org.junit.rules.ExternalResource;
import org.mortbay.jetty.Request;
import org.mortbay.jetty.Server;
import org.mortbay.jetty.handler.AbstractHandler;

/**
 * @author Nitesh Kant
 */
public class MockRemoteEurekaServer extends ExternalResource {

    public static final String EUREKA_API_BASE_PATH = "/eureka/v2/";

    private static Pattern STATUS_PATTERN = Pattern.compile("\"status\"\\s?:\\s?\\\"([A-Z_]*)\\\"");

    private int port;
    private final Map<String, Application> applicationMap = new HashMap<String, Application>();
    private final Map<String, Application> remoteRegionApps = new HashMap<String, Application>();
    private final Map<String, Application> remoteRegionAppsDelta = new HashMap<String, Application>();
    private final Map<String, Application> applicationDeltaMap = new HashMap<String, Application>();
    private Server server;
    private final AtomicBoolean sentDelta = new AtomicBoolean();
    private final AtomicBoolean sentRegistry = new AtomicBoolean();

    public final List<String> registrationStatuses = new ArrayList<String>();

    public final AtomicLong registerCount = new AtomicLong(0);
    public final AtomicLong heartbeatCount = new AtomicLong(0);
    public final AtomicLong getFullRegistryCount = new AtomicLong(0);
    public final AtomicLong getSingleVipCount = new AtomicLong(0);
    public final AtomicLong getDeltaCount = new AtomicLong(0);

    @Override
    protected void before() throws Throwable {
        start();
    }

    @Override
    protected void after() {
        try {
            stop();
        } catch (Exception e) {
            Assert.fail(e.getMessage());
        }
    }

    public void start() throws Exception {
        server = new Server(port);
        server.setHandler(new AppsResourceHandler());
        server.start();
        port = server.getConnectors()[0].getLocalPort();
    }

    public int getPort() {
        return port;
    }

    public void stop() throws Exception {
        server.stop();
        server = null;
        port = 0;

        registrationStatuses.clear();

        applicationMap.clear();
        remoteRegionApps.clear();
        remoteRegionAppsDelta.clear();
        applicationDeltaMap.clear();
    }

    public boolean isSentDelta() {
        return sentDelta.get();
    }

    public boolean isSentRegistry() {
        return sentRegistry.get();
    }

    public void addRemoteRegionApps(String appName, Application app) {
        remoteRegionApps.put(appName, app);
    }

    public void addRemoteRegionAppsDelta(String appName, Application app) {
        remoteRegionAppsDelta.put(appName, app);
    }

    public void addLocalRegionApps(String appName, Application app) {
        applicationMap.put(appName, app);
    }

    public void addLocalRegionAppsDelta(String appName, Application app) {
        applicationDeltaMap.put(appName, app);
    }

    public void waitForDeltaToBeRetrieved(int refreshRate) throws InterruptedException {
        int count = 0;
        while (count++ < 3 && !isSentDelta()) {
            System.out.println("Sleeping for " + refreshRate + " seconds to let the remote registry fetch delta. Attempt: " + count);
            Thread.sleep(3 * refreshRate * 1000);
            System.out.println("Done sleeping for 10 seconds to let the remote registry fetch delta. Delta fetched: " + isSentDelta());
        }

        System.out.println("Sleeping for extra " + refreshRate + " seconds for the client to update delta in memory.");
    }

    //
    // A base default resource handler for the mock server
    //
    private class AppsResourceHandler extends AbstractHandler {

        @Override
        public void handle(String target, HttpServletRequest request, HttpServletResponse response, int dispatch)
                throws IOException, ServletException {
            String authName = request.getHeader(AbstractEurekaIdentity.AUTH_NAME_HEADER_KEY);
            String authVersion = request.getHeader(AbstractEurekaIdentity.AUTH_VERSION_HEADER_KEY);
            String authId = request.getHeader(AbstractEurekaIdentity.AUTH_ID_HEADER_KEY);

            Assert.assertEquals(EurekaClientIdentity.DEFAULT_CLIENT_NAME, authName);
            Assert.assertNotNull(authVersion);
            Assert.assertNotNull(authId);

            String pathInfo = request.getPathInfo();
            System.out.println("Eureka port: " + port + ". " + System.currentTimeMillis() +
                    ". Eureka resource mock, received request on path: " + pathInfo + ". HTTP method: |"
                    + request.getMethod() + '|' + ", query string: " + request.getQueryString());
            boolean handled = false;
            if (null != pathInfo && pathInfo.startsWith("")) {
                pathInfo = pathInfo.substring(EUREKA_API_BASE_PATH.length());
                boolean includeRemote = isRemoteRequest(request);

                if (pathInfo.startsWith("apps/delta")) {
                    getDeltaCount.getAndIncrement();

                    Applications apps = new Applications();
                    apps.setVersion(100L);
                    if (sentDelta.compareAndSet(false, true)) {
                        addDeltaApps(includeRemote, apps);
                    } else {
                        System.out.println("Eureka port: " + port + ". " + System.currentTimeMillis() + ". Not including delta as it has already been sent.");
                    }
                    apps.setAppsHashCode(getDeltaAppsHashCode(includeRemote));
                    sendOkResponseWithContent((Request) request, response, apps);
                    handled = true;
                } else if (pathInfo.equals("apps/")) {
                    getFullRegistryCount.getAndIncrement();

                    Applications apps = new Applications();
                    apps.setVersion(100L);
                    for (Application application : applicationMap.values()) {
                        apps.addApplication(application);
                    }
                    if (includeRemote) {
                        for (Application application : remoteRegionApps.values()) {
                            apps.addApplication(application);
                        }
                    }

                    if (sentDelta.get()) {
                        addDeltaApps(includeRemote, apps);
                    } else {
                        System.out.println("Eureka port: " + port + ". " + System.currentTimeMillis() + ". Not including delta apps in /apps response, as delta has not been sent.");
                    }
                    apps.setAppsHashCode(apps.getReconcileHashCode());
                    sendOkResponseWithContent((Request) request, response, apps);
                    sentRegistry.set(true);
                    handled = true;
                } else if (pathInfo.startsWith("vips/")) {
                    getSingleVipCount.getAndIncrement();

                    String vipAddress = pathInfo.substring("vips/".length());
                    Applications apps = new Applications();
                    apps.setVersion(-1l);
                    for (Application application : applicationMap.values()) {
                        Application retApp = new Application(application.getName());
                        for (InstanceInfo instance : application.getInstances()) {
                            if (vipAddress.equals(instance.getVIPAddress())) {
                                retApp.addInstance(instance);
                            }
                        }

                        if (retApp.getInstances().size() > 0) {
                            apps.addApplication(retApp);
                        }
                    }

                    apps.setAppsHashCode(apps.getReconcileHashCode());
                    sendOkResponseWithContent((Request) request, response, apps);
                    handled = true;
                } else if (pathInfo.startsWith("apps")) {  // assume this is the renewal heartbeat
                    if (request.getMethod().equals("PUT")) {  // this is the renewal heartbeat
                        heartbeatCount.getAndIncrement();
                    } else if (request.getMethod().equals("POST")) {  // this is a register request
                        registerCount.getAndIncrement();
                        String result = null;
                        String line;
                        BufferedReader reader = request.getReader();
                        while ((line = reader.readLine()) != null) {
                            Matcher matcher = STATUS_PATTERN.matcher(line);
                            if (result == null && matcher.find()) {
                                result = matcher.group(1);
                                // don't break here as we want to read the full buffer for a clean connection close
                            }
                        }
                        System.out.println("Matched status to: " + result);
                        registrationStatuses.add(result);
                    }
                    Applications apps = new Applications();
                    apps.setAppsHashCode("");
                    sendOkResponseWithContent((Request) request, response, apps);
                    handled = true;
                } else {
                    System.out.println("Not handling request: " + pathInfo);
                }
            }

            if (!handled) {
                response.sendError(HttpServletResponse.SC_NOT_FOUND,
                        "Request path: " + pathInfo + " not supported by eureka resource mock.");
            }
        }

        protected void addDeltaApps(boolean includeRemote, Applications apps) {
            for (Application application : applicationDeltaMap.values()) {
                apps.addApplication(application);
            }
            if (includeRemote) {
                for (Application application : remoteRegionAppsDelta.values()) {
                    apps.addApplication(application);
                }
            }
        }

        protected String getDeltaAppsHashCode(boolean includeRemote) {
            Applications allApps = new Applications();
            for (Application application : applicationMap.values()) {
                allApps.addApplication(application);
            }

            if (includeRemote) {
                for (Application application : remoteRegionApps.values()) {
                    allApps.addApplication(application);
                }
            }
            addDeltaApps(includeRemote, allApps);
            return allApps.getReconcileHashCode();
        }

        protected boolean isRemoteRequest(HttpServletRequest request) {
            String queryString = request.getQueryString();
            if (queryString == null) {
                return false;
            }
            return queryString.contains("regions=");
        }

        protected void sendOkResponseWithContent(Request request, HttpServletResponse response, Applications apps)
                throws IOException {
            String content = XmlXStream.getInstance().toXML(apps);
            response.setContentType("application/xml");
            response.setStatus(HttpServletResponse.SC_OK);
            response.getWriter().println(content);
            response.getWriter().flush();
            request.setHandled(true);
            System.out.println("Eureka port: " + port + ". " + System.currentTimeMillis() +
                    ". Eureka resource mock, sent response for request path: " + request.getPathInfo() +
                    ", apps count: " + apps.getRegisteredApplications().size());
        }

        protected void sleep(int seconds) {
            try {
                Thread.sleep(seconds);
            } catch (InterruptedException e) {
                System.out.println("Interrupted: " + e);
            }
        }
    }
}

File: eureka-client/src/test/java/com/netflix/discovery/guice/EurekaModuleTest.java
package com.netflix.discovery.guice;

import com.google.inject.AbstractModule;
import com.google.inject.Injector;
import com.google.inject.Module;
import com.google.inject.Scopes;
import com.google.inject.util.Modules;
import com.netflix.appinfo.ApplicationInfoManager;
import com.netflix.appinfo.EurekaInstanceConfig;
import com.netflix.appinfo.InstanceInfo;
import com.netflix.appinfo.providers.MyDataCenterInstanceConfigProvider;
import com.netflix.config.ConfigurationManager;
import com.netflix.discovery.DiscoveryClient;
import com.netflix.discovery.DiscoveryManager;
import com.netflix.discovery.EurekaClient;
import com.netflix.discovery.EurekaClientConfig;
import com.netflix.governator.guice.LifecycleInjector;
import com.netflix.governator.guice.LifecycleInjectorBuilder;
import com.netflix.governator.lifecycle.LifecycleManager;
import org.junit.After;
import org.junit.Assert;
import org.junit.Before;
import org.junit.Test;

/**
 * @author David Liu
 */
public class EurekaModuleTest {

    private Injector injector;
    private LifecycleManager lifecycleManager;

    @Before
    public void setUp() throws Exception {
        ConfigurationManager.getConfigInstance().setProperty("eureka.region", "default");
        ConfigurationManager.getConfigInstance().setProperty("eureka.shouldFetchRegistry", "false");
        ConfigurationManager.getConfigInstance().setProperty("eureka.registration.enabled", "false");
        ConfigurationManager.getConfigInstance().setProperty("eureka.serviceUrl.default", "http://localhost:8080/eureka/v2");

        LifecycleInjectorBuilder builder = LifecycleInjector.builder();

        Module testModule = Modules.override(new EurekaModule()).with(new AbstractModule() {
            @Override
            protected void configure() {
                // the default impl of EurekaInstanceConfig is CloudInstanceConfig, which we only want in an AWS
                // environment. Here we override that by binding MyDataCenterInstanceConfig to EurekaInstanceConfig.
                bind(EurekaInstanceConfig.class).toProvider(MyDataCenterInstanceConfigProvider.class).in(Scopes.SINGLETON);
            }
        });

        builder.withModules(testModule);

        injector = builder.build().createInjector();
        lifecycleManager = injector.getInstance(LifecycleManager.class);
        lifecycleManager.start();
    }

    @After
    public void tearDown() {
        if (lifecycleManager != null) {
            lifecycleManager.close();
        }

        ConfigurationManager.getConfigInstance().clear();
    }

    @SuppressWarnings("deprecation")
    @Test
    public void testDI() {
        InstanceInfo instanceInfo = injector.getInstance(InstanceInfo.class);
        Assert.assertEquals(ApplicationInfoManager.getInstance().getInfo(), instanceInfo);

        EurekaClient eurekaClient = injector.getInstance(EurekaClient.class);
        DiscoveryClient discoveryClient = injector.getInstance(DiscoveryClient.class);

        Assert.assertEquals(DiscoveryManager.getInstance().getEurekaClient(), eurekaClient);
        Assert.assertEquals(DiscoveryManager.getInstance().getDiscoveryClient(), discoveryClient);
        Assert.assertEquals(eurekaClient, discoveryClient);

        EurekaClientConfig eurekaClientConfig = injector.getInstance(EurekaClientConfig.class);
        Assert.assertEquals(DiscoveryManager.getInstance().getEurekaClientConfig(), eurekaClientConfig);

        EurekaInstanceConfig eurekaInstanceConfig = injector.getInstance(EurekaInstanceConfig.class);
        Assert.assertEquals(DiscoveryManager.getInstance().getEurekaInstanceConfig(), eurekaInstanceConfig);
    }
}


File: eureka-core/src/test/java/com/netflix/eureka/AbstractTester.java
package com.netflix.eureka;

import javax.annotation.Nullable;
import java.util.ArrayList;
import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.UUID;

import com.netflix.appinfo.AmazonInfo;
import com.netflix.appinfo.ApplicationInfoManager;
import com.netflix.appinfo.DataCenterInfo;
import com.netflix.appinfo.InstanceInfo;
import com.netflix.appinfo.LeaseInfo;
import com.netflix.appinfo.MyDataCenterInstanceConfig;
import com.netflix.blitz4j.LoggingConfiguration;
import com.netflix.config.ConfigurationManager;
import com.netflix.discovery.DefaultEurekaClientConfig;
import com.netflix.discovery.DiscoveryClient;
import com.netflix.discovery.DiscoveryManager;
import com.netflix.discovery.EurekaClient;
import com.netflix.discovery.shared.Application;
import com.netflix.discovery.shared.Pair;
import com.netflix.eureka.mock.MockRemoteEurekaServer;
import org.junit.After;
import org.junit.Before;

/**
 * @author Nitesh Kant
 */
public class AbstractTester {

    static {
        LoggingConfiguration.getInstance().configure();
    }

    public static final String REMOTE_REGION_NAME = "us-east-1";
    public static final String REMOTE_REGION_APP_NAME = "MYAPP";
    public static final String REMOTE_REGION_INSTANCE_1_HOSTNAME = "blah";
    public static final String REMOTE_REGION_INSTANCE_2_HOSTNAME = "blah2";
    public static final String LOCAL_REGION_APP_NAME = "MYLOCAPP";
    public static final String LOCAL_REGION_INSTANCE_1_HOSTNAME = "blahloc";
    public static final String LOCAL_REGION_INSTANCE_2_HOSTNAME = "blahloc2";
    protected final List<Pair<String, String>> registeredApps = new ArrayList<Pair<String, String>>();
    protected final Map<String, Application> remoteRegionApps = new HashMap<String, Application>();
    protected final Map<String, Application> remoteRegionAppsDelta = new HashMap<String, Application>();
    protected MockRemoteEurekaServer mockRemoteEurekaServer;
    protected PeerAwareInstanceRegistry registry;
    protected EurekaClient client;
    public static final String REMOTE_ZONE = "us-east-1c";

    @Before
    public void setUp() throws Exception {
        ConfigurationManager.getConfigInstance().clearProperty("eureka.remoteRegion.global.appWhiteList");
        ConfigurationManager.getConfigInstance().setProperty("eureka.responseCacheAutoExpirationInSeconds", "10");
        ConfigurationManager.getConfigInstance().clearProperty("eureka.remoteRegion." + REMOTE_REGION_NAME + ".appWhiteList");
        ConfigurationManager.getConfigInstance().setProperty("eureka.deltaRetentionTimerIntervalInMs", "600000");
        ConfigurationManager.getConfigInstance().setProperty("eureka.remoteRegion.registryFetchIntervalInSeconds", "5");
        populateRemoteRegistryAtStartup();
        mockRemoteEurekaServer = newMockRemoteServer();
        mockRemoteEurekaServer.start();

        ConfigurationManager.getConfigInstance().setProperty("eureka.remoteRegionUrlsWithName",
                REMOTE_REGION_NAME + ";http://localhost:" + mockRemoteEurekaServer.getPort() + MockRemoteEurekaServer.EUREKA_API_BASE_PATH);

        EurekaServerConfig serverConfig = new DefaultEurekaServerConfig();
        EurekaServerConfigurationManager.getInstance().setConfiguration(serverConfig);
        InstanceInfo.Builder builder = InstanceInfo.Builder.newBuilder();
        builder.setIPAddr("10.10.101.00");
        builder.setHostName("Hosttt");
        builder.setAppName("EurekaTestApp-" + UUID.randomUUID());
        builder.setLeaseInfo(LeaseInfo.Builder.newBuilder().build());
        builder.setDataCenterInfo(new DataCenterInfo() {
            @Override
            public Name getName() {
                return Name.MyOwn;
            }
        });

        ConfigurationManager.getConfigInstance().setProperty("eureka.serviceUrl.default",
                "http://localhost:" + mockRemoteEurekaServer.getPort() +
                        MockRemoteEurekaServer.EUREKA_API_BASE_PATH);

        DefaultEurekaClientConfig config = new DefaultEurekaClientConfig();
        // setup config in advance, used in initialize converter
        DiscoveryManager.getInstance().setEurekaClientConfig(config);
        client = new DiscoveryClient(builder.build(), config);
        ApplicationInfoManager.getInstance().initComponent(new MyDataCenterInstanceConfig());
        registry = new TestPeerAwareInstanceRegistry();
        registry.initRemoteRegionRegistry();
    }

    protected MockRemoteEurekaServer newMockRemoteServer() {
        return new MockRemoteEurekaServer(0 /* use ephemeral */, remoteRegionApps, remoteRegionAppsDelta);
    }

    @After
    public void tearDown() throws Exception {
        for (Pair<String, String> registeredApp : registeredApps) {
            System.out.println("Canceling application: " + registeredApp.first() + " from local registry.");
            registry.cancel(registeredApp.first(), registeredApp.second(), false);
        }
        registry.shutdown();
        mockRemoteEurekaServer.stop();
        remoteRegionApps.clear();
        remoteRegionAppsDelta.clear();
        ConfigurationManager.getConfigInstance().clearProperty("eureka.remoteRegionUrls");
        ConfigurationManager.getConfigInstance().clearProperty("eureka.deltaRetentionTimerIntervalInMs");
    }

    private static Application createRemoteApps() {
        Application myapp = new Application(REMOTE_REGION_APP_NAME);
        InstanceInfo instanceInfo = createRemoteInstance(REMOTE_REGION_INSTANCE_1_HOSTNAME);
        //instanceInfo.setActionType(InstanceInfo.ActionType.MODIFIED);
        myapp.addInstance(instanceInfo);
        return myapp;
    }

    private static Application createRemoteAppsDelta() {
        Application myapp = new Application(REMOTE_REGION_APP_NAME);
        InstanceInfo instanceInfo = createRemoteInstance(REMOTE_REGION_INSTANCE_1_HOSTNAME);
        myapp.addInstance(instanceInfo);
        return myapp;
    }

    protected static InstanceInfo createRemoteInstance(String instanceHostName) {
        InstanceInfo.Builder instanceBuilder = InstanceInfo.Builder.newBuilder();
        instanceBuilder.setAppName(REMOTE_REGION_APP_NAME);
        instanceBuilder.setHostName(instanceHostName);
        instanceBuilder.setIPAddr("10.10.101.1");
        instanceBuilder.setDataCenterInfo(getAmazonInfo(REMOTE_ZONE, instanceHostName));
        instanceBuilder.setLeaseInfo(LeaseInfo.Builder.newBuilder().build());
        return instanceBuilder.build();
    }

    protected static InstanceInfo createLocalInstance(String hostname) {
        InstanceInfo.Builder instanceBuilder = InstanceInfo.Builder.newBuilder();
        instanceBuilder.setAppName(LOCAL_REGION_APP_NAME);
        instanceBuilder.setHostName(hostname);
        instanceBuilder.setIPAddr("10.10.101.1");
        instanceBuilder.setDataCenterInfo(getAmazonInfo(null, hostname));
        instanceBuilder.setLeaseInfo(LeaseInfo.Builder.newBuilder().build());
        return instanceBuilder.build();
    }

    private static AmazonInfo getAmazonInfo(@Nullable String availabilityZone, String instanceHostName) {
        AmazonInfo.Builder azBuilder = AmazonInfo.Builder.newBuilder();
        azBuilder.addMetadata(AmazonInfo.MetaDataKey.availabilityZone, null == availabilityZone ? "us-east-1a" : availabilityZone);
        azBuilder.addMetadata(AmazonInfo.MetaDataKey.instanceId, instanceHostName);
        azBuilder.addMetadata(AmazonInfo.MetaDataKey.amiId, "XXX");
        azBuilder.addMetadata(AmazonInfo.MetaDataKey.instanceType, "XXX");
        azBuilder.addMetadata(AmazonInfo.MetaDataKey.localIpv4, "XXX");
        azBuilder.addMetadata(AmazonInfo.MetaDataKey.publicIpv4, "XXX");
        azBuilder.addMetadata(AmazonInfo.MetaDataKey.publicHostname, instanceHostName);
        return azBuilder.build();
    }

    private void populateRemoteRegistryAtStartup() {
        Application myapp = createRemoteApps();
        Application myappDelta = createRemoteAppsDelta();
        remoteRegionApps.put(REMOTE_REGION_APP_NAME, myapp);
        remoteRegionAppsDelta.put(REMOTE_REGION_APP_NAME, myappDelta);
    }

    private static class TestPeerAwareInstanceRegistry extends PeerAwareInstanceRegistry {

        @Override
        public boolean isLeaseExpirationEnabled() {
            return false;
        }

        @Override
        public InstanceInfo getNextServerFromEureka(String virtualHostname, boolean secure) {
            return null;
        }
    }
}


File: eureka-examples/src/main/java/com/netflix/eureka/ExampleEurekaGovernatedService.java
package com.netflix.eureka;

import com.google.inject.AbstractModule;
import com.google.inject.Injector;
import com.netflix.appinfo.EurekaInstanceConfig;
import com.netflix.appinfo.MyDataCenterInstanceConfig;
import com.netflix.config.DynamicPropertyFactory;
import com.netflix.discovery.guice.EurekaModule;
import com.netflix.governator.guice.LifecycleInjector;
import com.netflix.governator.guice.LifecycleInjectorBuilder;
import com.netflix.governator.lifecycle.LifecycleManager;

/**
 * Sample Eureka service that registers with Eureka to receive and process requests, using EurekaModule.
 *
 * @author David Liu
 */
public class ExampleEurekaGovernatedService {

    static class ExampleServiceModule extends AbstractModule {
        @Override
        protected void configure() {
            bind(ExampleServiceBase.class).asEagerSingleton();
        }
    }

    private static ExampleServiceBase init() throws Exception {
        System.out.println("Creating injector for Example Service");
        LifecycleInjectorBuilder builder = LifecycleInjector.builder();
        builder.withModules(
                new AbstractModule() {
                    @Override
                    protected void configure() {
                        DynamicPropertyFactory configInstance = com.netflix.config.DynamicPropertyFactory.getInstance();
                        bind(DynamicPropertyFactory.class).toInstance(configInstance);
                        // the default impl of EurekaInstanceConfig is CloudInstanceConfig, which we only want in an AWS
                        // environment. Here we override that by binding MyDataCenterInstanceConfig to EurekaInstanceConfig.
                        bind(EurekaInstanceConfig.class).to(MyDataCenterInstanceConfig.class);
                    }
                },
                new EurekaModule(),
                new ExampleServiceModule());

        Injector injector = builder.build().createInjector();
        LifecycleManager lifecycleManager = injector.getInstance(LifecycleManager.class);
        lifecycleManager.start();

        System.out.println("Done creating the injector");
        return injector.getInstance(ExampleServiceBase.class);
    }

    public static void main(String[] args) throws Exception {
        ExampleServiceBase exampleServiceBase = null;
        try {
            exampleServiceBase = init();
            exampleServiceBase.start();
        } catch (Exception e) {
            System.out.println("Error starting the sample service: " + e);
            e.printStackTrace();
        } finally {
            if (exampleServiceBase != null) {
                exampleServiceBase.stop();
            }
        }
    }

}
