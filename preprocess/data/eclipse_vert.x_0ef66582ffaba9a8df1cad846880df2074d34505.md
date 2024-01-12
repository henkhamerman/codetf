Refactoring Types: ['Extract Method']
ploymentOptions.java
/*
 * Copyright (c) 2011-2014 The original author or authors
 * ------------------------------------------------------
 * All rights reserved. This program and the accompanying materials
 * are made available under the terms of the Eclipse Public License v1.0
 * and Apache License v2.0 which accompanies this distribution.
 *
 *     The Eclipse Public License is available at
 *     http://www.eclipse.org/legal/epl-v10.html
 *
 *     The Apache License v2.0 is available at
 *     http://www.opensource.org/licenses/apache2.0.php
 *
 * You may elect to redistribute this code under either of these licenses.
 */

package io.vertx.core;

import io.vertx.codegen.annotations.DataObject;
import io.vertx.core.json.JsonArray;
import io.vertx.core.json.JsonObject;

import java.util.ArrayList;
import java.util.List;

/**
 * Options for configuring a verticle deployment.
 * <p>
 *
 *
 * @author <a href="http://tfox.org">Tim Fox</a>
 */
@DataObject
public class DeploymentOptions {

  public static final boolean DEFAULT_WORKER = false;
  public static final boolean DEFAULT_MULTI_THREADED = false;
  public static final String DEFAULT_ISOLATION_GROUP = null;
  public static final boolean DEFAULT_HA = false;
  public static final int DEFAULT_INSTANCES = 1;

  private JsonObject config;
  private boolean worker;
  private boolean multiThreaded;
  private String isolationGroup;
  private boolean ha;
  private List<String> extraClasspath;
  private int instances;
  private List<String> isolatedClasses;

  /**
   * Default constructor
   */
  public DeploymentOptions() {
    this.worker = DEFAULT_WORKER;
    this.config = null;
    this.multiThreaded = DEFAULT_MULTI_THREADED;
    this.isolationGroup = DEFAULT_ISOLATION_GROUP;
    this.ha = DEFAULT_HA;
    this.instances = DEFAULT_INSTANCES;
  }

  /**
   * Copy constructor
   *
   * @param other the instance to copy
   */
  public DeploymentOptions(DeploymentOptions other) {
    this.config = other.getConfig() == null ? null : other.getConfig().copy();
    this.worker = other.isWorker();
    this.multiThreaded = other.isMultiThreaded();
    this.isolationGroup = other.getIsolationGroup();
    this.ha = other.isHa();
    this.extraClasspath = other.getExtraClasspath() == null ? null : new ArrayList<>(other.getExtraClasspath());
    this.instances = other.instances;
    this.isolatedClasses = other.getIsolatedClasses() == null ? null : new ArrayList<>(other.getIsolatedClasses());
  }

  /**
   * Constructor for creating a instance from JSON
   *
   * @param json  the JSON
   */
  public DeploymentOptions(JsonObject json) {
    fromJson(json);
  }

  /**
   * Initialise the fields of this instance from the specified JSON
   *
   * @param json  the JSON
   */
  public void fromJson(JsonObject json) {
    this.config = json.getJsonObject("config");
    this.worker = json.getBoolean("worker", DEFAULT_WORKER);
    this.multiThreaded = json.getBoolean("multiThreaded", DEFAULT_MULTI_THREADED);
    this.isolationGroup = json.getString("isolationGroup", DEFAULT_ISOLATION_GROUP);
    this.ha = json.getBoolean("ha", DEFAULT_HA);
    JsonArray arr = json.getJsonArray("extraClasspath", null);
    if (arr != null) {
      this.extraClasspath = arr.getList();
    }
    this.instances = json.getInteger("instances", DEFAULT_INSTANCES);
    JsonArray arrIsolated = json.getJsonArray("isolatedClasses", null);
    if (arrIsolated != null) {
      this.isolatedClasses = arrIsolated.getList();
    }
  }

  /**
   * Get the JSON configuration that will be passed to the verticle(s) when deployed.
   *
   * @return  the JSON config
   */
  public JsonObject getConfig() {
    return config;
  }

  /**
   * Set the JSON configuration that will be passed to the verticle(s) when it's deployed
   *
   * @param config  the JSON config
   * @return a reference to this, so the API can be used fluently
   */
  public DeploymentOptions setConfig(JsonObject config) {
    this.config = config;
    return this;
  }

  /**
   * Should the verticle(s) be deployed as a worker verticle?
   *
   * @return true if will be deployed as worker, false otherwise
   */
  public boolean isWorker() {
    return worker;
  }

  /**
   * Set whether the verticle(s) should be deployed as a worker verticle
   *
   * @param worker true for worker, false otherwise
   * @return a reference to this, so the API can be used fluently
   */
  public DeploymentOptions setWorker(boolean worker) {
    this.worker = worker;
    return this;
  }

  /**
   * Should the verticle(s) be deployed as a multi-threaded worker verticle?
   * <p>
   * Ignored if {@link #isWorker} is not true.
   *
   * @return true if will be deployed as multi-threaded worker, false otherwise
   */
  public boolean isMultiThreaded() {
    return multiThreaded;
  }

  /**
   * Set whether the verticle(s) should be deployed as a multi-threaded worker verticle
   *
   * @param multiThreaded true for multi-threaded worker, false otherwise
   * @return a reference to this, so the API can be used fluently
   */
  public DeploymentOptions setMultiThreaded(boolean multiThreaded) {
    this.multiThreaded = multiThreaded;
    return this;
  }

  /**
   * Get the isolation group that will be used when deploying the verticle(s)
   *
   * @return the isolation group
   */
  public String getIsolationGroup() {
    return isolationGroup;
  }

  /**
   * Set the isolation group that will be used when deploying the verticle(s)
   *
   * @param isolationGroup - the isolation group
   * @return a reference to this, so the API can be used fluently
   */
  public DeploymentOptions setIsolationGroup(String isolationGroup) {
    this.isolationGroup = isolationGroup;
    return this;
  }

  /**
   * Will the verticle(s) be deployed as HA (highly available) ?
   *
   * @return true if HA, false otherwise
   */
  public boolean isHa() {
    return ha;
  }

  /**
   * Set whether the verticle(s) will be deployed as HA.
   *
   * @param ha  true if to be deployed as HA, false otherwise
   * @return a reference to this, so the API can be used fluently
   */
  public DeploymentOptions setHa(boolean ha) {
    this.ha = ha;
    return this;
  }

  /**
   * Get any extra classpath to be used when deploying the verticle.
   * <p>
   * Ignored if no isolation group is set.
   *
   * @return  any extra classpath
   */
  public List<String> getExtraClasspath() {
    return extraClasspath;
  }

  /**
   * Set any extra classpath to be used when deploying the verticle.
   * <p>
   * Ignored if no isolation group is set.
   *
   * @return a reference to this, so the API can be used fluently
   */
  public DeploymentOptions setExtraClasspath(List<String> extraClasspath) {
    this.extraClasspath = extraClasspath;
    return this;
  }

  /**
   * Get the number of instances that should be deployed.
   *
   * @return  the number of instances
   */
  public int getInstances() {
    return instances;
  }

  /**
   * Set the number of instances that should be deployed.
   *
   * @param instances  the number of instances
   * @return a reference to this, so the API can be used fluently
   */
  public DeploymentOptions setInstances(int instances) {
    this.instances = instances;
    return this;
  }

  /**
   * Get the list of isolated class names, the names can be a Java class fully qualified name such as
   * 'com.mycompany.myproject.engine.MyClass' or a wildcard matching such as `com.mycompany.myproject.*`.
   *
   * @return the list of isolated classes
   */
  public List<String> getIsolatedClasses() {
    return isolatedClasses;
  }

  /**
   * Set the isolated class names.
   *
   * @param isolatedClasses the list of isolated class names
   * @return a reference to this, so the API can be used fluently
   */
  public DeploymentOptions setIsolatedClasses(List<String> isolatedClasses) {
    this.isolatedClasses = isolatedClasses;
    return this;
  }

  /**
   * Convert this to JSON
   *
   * @return  the JSON
   */
  public JsonObject toJson() {
    JsonObject json = new JsonObject();
    if (worker) json.put("worker", true);
    if (multiThreaded) json.put("multiThreaded", true);
    if (isolationGroup != null) json.put("isolationGroup", isolationGroup);
    if (ha) json.put("ha", true);
    if (config != null) json.put("config", config);
    if (extraClasspath != null) json.put("extraClasspath", new JsonArray(extraClasspath));
    if (instances != DEFAULT_INSTANCES) {
      json.put("instances", instances);
    }
    if (isolatedClasses != null) json.put("isolatedClasses", new JsonArray(isolatedClasses));
    return json;
  }

  @Override
  public boolean equals(Object o) {
    if (this == o) return true;
    if (o == null || getClass() != o.getClass()) return false;

    DeploymentOptions that = (DeploymentOptions) o;

    if (worker != that.worker) return false;
    if (multiThreaded != that.multiThreaded) return false;
    if (ha != that.ha) return false;
    if (instances != that.instances) return false;
    if (config != null ? !config.equals(that.config) : that.config != null) return false;
    if (isolationGroup != null ? !isolationGroup.equals(that.isolationGroup) : that.isolationGroup != null)
      return false;
    if (extraClasspath != null ? !extraClasspath.equals(that.extraClasspath) : that.extraClasspath != null)
      return false;
    return !(isolatedClasses != null ? !isolatedClasses.equals(that.isolatedClasses) : that.isolatedClasses != null);

  }

  @Override
  public int hashCode() {
    int result = config != null ? config.hashCode() : 0;
    result = 31 * result + (worker ? 1 : 0);
    result = 31 * result + (multiThreaded ? 1 : 0);
    result = 31 * result + (isolationGroup != null ? isolationGroup.hashCode() : 0);
    result = 31 * result + (ha ? 1 : 0);
    result = 31 * result + (extraClasspath != null ? extraClasspath.hashCode() : 0);
    result = 31 * result + instances;
    result = 31 * result + (isolatedClasses != null ? isolatedClasses.hashCode() : 0);
    return result;
  }
}


File: src/main/java/io/vertx/core/VertxOptions.java
/*
 * Copyright (c) 2011-2014 The original author or authors
 * ------------------------------------------------------
 * All rights reserved. This program and the accompanying materials
 * are made available under the terms of the Eclipse Public License v1.0
 * and Apache License v2.0 which accompanies this distribution.
 *
 *     The Eclipse Public License is available at
 *     http://www.eclipse.org/legal/epl-v10.html
 *
 *     The Apache License v2.0 is available at
 *     http://www.opensource.org/licenses/apache2.0.php
 *
 * You may elect to redistribute this code under either of these licenses.
 */

package io.vertx.core;

import io.vertx.codegen.annotations.DataObject;
import io.vertx.core.json.JsonObject;
import io.vertx.core.metrics.MetricsOptions;
import io.vertx.core.spi.cluster.ClusterManager;

import java.util.Objects;

/**
 * Instances of this class are used to configure {@link io.vertx.core.Vertx} instances.
 * 
 * @author <a href="http://tfox.org">Tim Fox</a>
 */
@DataObject
public class VertxOptions {

  /**
   * The default number of event loop threads to be used  = 2 * number of cores on the machine
   */
  public static final int DEFAULT_EVENT_LOOP_POOL_SIZE = 2 * Runtime.getRuntime().availableProcessors();

  /**
   * The default number of threads in the worker pool = 20
   */
  public static final int DEFAULT_WORKER_POOL_SIZE = 20;

  /**
   * The default number of threads in the internal blocking  pool (used by some internal operations) = 20
   */
  public static final int DEFAULT_INTERNAL_BLOCKING_POOL_SIZE = 20;

  /**
   * The default value of whether Vert.x is clustered = false.
   */
  public static final boolean DEFAULT_CLUSTERED = false;

  /**
   * The default hostname to use when clustering = "localhost"
   */
  public static final String DEFAULT_CLUSTER_HOST = "localhost";

  /**
   * The default port to use when clustering = 0 (meaning assign a random port)
   */
  public static final int DEFAULT_CLUSTER_PORT = 0;

  /**
   * The default value of cluster ping interval = 20000 ms.
   */
  public static final long DEFAULT_CLUSTER_PING_INTERVAL = 20000;

  /**
   * The default value of cluster ping reply interval = 20000 ms.
   */
  public static final long DEFAULT_CLUSTER_PING_REPLY_INTERVAL = 20000;

  /**
   * The default value of blocked thread check interval = 1000 ms.
   */
  public static final long DEFAULT_BLOCKED_THREAD_CHECK_INTERVAL = 1000;

  /**
   * The default value of max event loop execute time = 2000000000 ns (2 seconds)
   */
  public static final long DEFAULT_MAX_EVENT_LOOP_EXECUTE_TIME = 2l * 1000 * 1000000;

  /**
   * The default value of max worker execute time = 60000000000 ns (60 seconds)
   */
  public static final long DEFAULT_MAX_WORKER_EXECUTE_TIME = 60l * 1000 * 1000000;

  /**
   * The default value of quorum size = 1
   */
  public static final int DEFAULT_QUORUM_SIZE = 1;

  /**
   * The default value of Ha group is "__DEFAULT__"
   */
  public static final String DEFAULT_HA_GROUP = "__DEFAULT__";

  /**
   * The default value of HA enabled = false
   */
  public static final boolean DEFAULT_HA_ENABLED = false;

  /**
   * The default value of metrics enabled false
   */
  public static final boolean DEFAULT_METRICS_ENABLED = false;

  /**
   * The default value of warning exception time 5000000000 ns (5 seconds)
   * If a thread is blocked longer than this threshold, the warning log
   * contains a stack trace
   */
  private static final long DEFAULT_WARNING_EXECPTION_TIME = 5l * 1000 * 1000000;

  private int eventLoopPoolSize = DEFAULT_EVENT_LOOP_POOL_SIZE;
  private int workerPoolSize = DEFAULT_WORKER_POOL_SIZE;
  private int internalBlockingPoolSize = DEFAULT_INTERNAL_BLOCKING_POOL_SIZE;
  private boolean clustered = DEFAULT_CLUSTERED;
  private String clusterHost = DEFAULT_CLUSTER_HOST;
  private int clusterPort = DEFAULT_CLUSTER_PORT;
  private long clusterPingInterval = DEFAULT_CLUSTER_PING_INTERVAL;
  private long clusterPingReplyInterval = DEFAULT_CLUSTER_PING_REPLY_INTERVAL;
  private long blockedThreadCheckInterval = DEFAULT_BLOCKED_THREAD_CHECK_INTERVAL;
  private long maxEventLoopExecuteTime = DEFAULT_MAX_EVENT_LOOP_EXECUTE_TIME;
  private long maxWorkerExecuteTime = DEFAULT_MAX_WORKER_EXECUTE_TIME;
  private ClusterManager clusterManager;
  private boolean haEnabled = DEFAULT_HA_ENABLED;
  private int quorumSize = DEFAULT_QUORUM_SIZE;
  private String haGroup = DEFAULT_HA_GROUP;
  private MetricsOptions metrics;

  private long warningExceptionTime = DEFAULT_WARNING_EXECPTION_TIME;

  /**
   * Default constructor
   */
  public VertxOptions() {
  }

  /**
   * Copy constructor
   * 
   * @param other The other {@code VertxOptions} to copy when creating this
   */
  public VertxOptions(VertxOptions other) {
    this.eventLoopPoolSize = other.getEventLoopPoolSize();
    this.workerPoolSize = other.getWorkerPoolSize();
    this.clustered = other.isClustered();
    this.clusterHost = other.getClusterHost();
    this.clusterPort = other.getClusterPort();
    this.clusterPingInterval = other.getClusterPingInterval();
    this.clusterPingReplyInterval = other.getClusterPingReplyInterval();
    this.blockedThreadCheckInterval = other.getBlockedThreadCheckInterval();
    this.maxEventLoopExecuteTime = other.getMaxEventLoopExecuteTime();
    this.maxWorkerExecuteTime = other.getMaxWorkerExecuteTime();
    this.internalBlockingPoolSize = other.getInternalBlockingPoolSize();
    this.clusterManager = other.getClusterManager();
    this.haEnabled = other.isHAEnabled();
    this.quorumSize = other.getQuorumSize();
    this.haGroup = other.getHAGroup();
    this.metrics = other.getMetricsOptions() != null ? new MetricsOptions(other.getMetricsOptions()) : null;
    this.warningExceptionTime = other.warningExceptionTime;
  }

  /**
   * Create an instance from a {@link io.vertx.core.json.JsonObject}
   * 
   * @param json the JsonObject to create it from
   */
  public VertxOptions(JsonObject json) {
    this.eventLoopPoolSize = json.getInteger("eventLoopPoolSize", DEFAULT_EVENT_LOOP_POOL_SIZE);
    this.workerPoolSize = json.getInteger("workerPoolSize", DEFAULT_WORKER_POOL_SIZE);
    this.clustered = json.getBoolean("clustered", DEFAULT_CLUSTERED);
    this.clusterHost = json.getString("clusterHost", DEFAULT_CLUSTER_HOST);
    this.clusterPort = json.getInteger("clusterPort", DEFAULT_CLUSTER_PORT);
    this.clusterPingInterval = json.getLong("clusterPingInterval", DEFAULT_CLUSTER_PING_INTERVAL);
    this.clusterPingReplyInterval = json.getLong("clusterPingReplyInterval", DEFAULT_CLUSTER_PING_REPLY_INTERVAL);
    this.internalBlockingPoolSize = json.getInteger("internalBlockingPoolSize", DEFAULT_INTERNAL_BLOCKING_POOL_SIZE);
    this.blockedThreadCheckInterval = json.getLong("blockedThreadCheckInterval", DEFAULT_BLOCKED_THREAD_CHECK_INTERVAL);
    this.maxEventLoopExecuteTime = json.getLong("maxEventLoopExecuteTime", DEFAULT_MAX_EVENT_LOOP_EXECUTE_TIME);
    this.maxWorkerExecuteTime = json.getLong("maxWorkerExecuteTime", DEFAULT_MAX_WORKER_EXECUTE_TIME);
    this.haEnabled = json.getBoolean("haEnabled", false);
    this.quorumSize = json.getInteger("quorumSize", DEFAULT_QUORUM_SIZE);
    this.haGroup = json.getString("haGroup", DEFAULT_HA_GROUP);
    JsonObject metricsJson = json.getJsonObject("metricsOptions");
    this.metrics = metricsJson != null ? new MetricsOptions(metricsJson) : null;
    this.warningExceptionTime = json.getLong("warningExceptionTime", DEFAULT_WARNING_EXECPTION_TIME);
  }

  /**
   * Get the number of event loop threads to be used by the Vert.x instance.
   * 
   * @return the number of threads
   */
  public int getEventLoopPoolSize() {
    return eventLoopPoolSize;
  }

  /**
   * Set the number of event loop threads to be used by the Vert.x instance.
   * 
   * @param eventLoopPoolSize  the number of threads
   * @return a reference to this, so the API can be used fluently
   */
  public VertxOptions setEventLoopPoolSize(int eventLoopPoolSize) {
    if (eventLoopPoolSize < 1) {
      throw new IllegalArgumentException("eventLoopPoolSize must be > 0");
    }
    this.eventLoopPoolSize = eventLoopPoolSize;
    return this;
  }

  /**
   * Get the maximum number of worker threads to be used by the Vert.x instance.
   * <p>
   * Worker threads are used for running blocking code and worker verticles.
   *
   * @return the maximum number of worker threads
   */
  public int getWorkerPoolSize() {
    return workerPoolSize;
  }

  /**
   * Set the maximum number of worker threads to be used by the Vert.x instance.
   *
   * @param workerPoolSize  the number of threads
   * @return a reference to this, so the API can be used fluently
   */
  public VertxOptions setWorkerPoolSize(int workerPoolSize) {
    if (workerPoolSize < 1) {
      throw new IllegalArgumentException("workerPoolSize must be > 0");
    }
    this.workerPoolSize = workerPoolSize;
    return this;
  }

  /**
   * Is the Vert.x instance clustered?
   * @return true if clustered, false if not
   */
  public boolean isClustered() {
    return clustered;
  }

  /**
   * Set whether or not the Vert.x instance will be clustered.
   * @param clustered  if true, the Vert.x instance will be clustered, otherwise not
   * @return a reference to this, so the API can be used fluently
   */
  public VertxOptions setClustered(boolean clustered) {
    this.clustered = clustered;
    return this;
  }

  /**
   * Get the host name to be used for clustering.
   *
   * @return The host name
   */
  public String getClusterHost() {
    return clusterHost;
  }

  /**
   * Set the hostname to be used for clustering.
   *
   * @param clusterHost  the host name to use
   * @return a reference to this, so the API can be used fluently
   */
  public VertxOptions setClusterHost(String clusterHost) {
    this.clusterHost = clusterHost;
    return this;
  }

  /**
   * Get the port to be used for clustering
   *
   * @return the port
   */
  public int getClusterPort() {
    return clusterPort;
  }

  /**
   * Set the port to be used for clustering.
   *
   * @param clusterPort  the port
   * @return a reference to this, so the API can be used fluently
   */
  public VertxOptions setClusterPort(int clusterPort) {
    if (clusterPort < 0 || clusterPort > 65535) {
      throw new IllegalArgumentException("clusterPort p must be in range 0 <= p <= 65535");
    }
    this.clusterPort = clusterPort;
    return this;
  }

  /**
   * Get the value of cluster ping interval, in ms.
   * <p>
   * Nodes in the cluster ping each other at this interval to determine whether they are still running.
   *
   * @return The value of cluster ping interval
   */
  public long getClusterPingInterval() {
    return clusterPingInterval;
  }

  /**
   * Set the value of cluster ping interval, in ms.
   *
   * @param clusterPingInterval The value of cluster ping interval, in ms.
   * @return a reference to this, so the API can be used fluently
   */
  public VertxOptions setClusterPingInterval(long clusterPingInterval) {
    if (clusterPingInterval < 1) {
      throw new IllegalArgumentException("clusterPingInterval must be greater than 0");
    }
    this.clusterPingInterval = clusterPingInterval;
    return this;
  }

  /**
   * Get the value of cluster ping reply interval, in ms.
   * <p>
   * After sending a ping, if a pong is not received in this time, the node will be considered dead.
   *
   * @return the value of cluster ping reply interval
   */
  public long getClusterPingReplyInterval() {
    return clusterPingReplyInterval;
  }

  /**
   * Set the value of cluster ping reply interval, in ms.
   *
   * @param clusterPingReplyInterval The value of cluster ping reply interval, in ms.
   * @return a reference to this, so the API can be used fluently
   */
  public VertxOptions setClusterPingReplyInterval(long clusterPingReplyInterval) {
    if (clusterPingReplyInterval < 1) {
      throw new IllegalArgumentException("clusterPingReplyInterval must be greater than 0");
    }
    this.clusterPingReplyInterval = clusterPingReplyInterval;
    return this;
  }

  /**
   * Get the value of blocked thread check period, in ms.
   * <p>
   * This setting determines how often Vert.x will check whether event loop threads are executing for too long.
   *
   * @return the value of blocked thread check period, in ms.
   */
  public long getBlockedThreadCheckInterval() {
    return blockedThreadCheckInterval;
  }

  /**
   * Sets the value of blocked thread check period, in ms.
   *
   * @param blockedThreadCheckInterval  the value of blocked thread check period, in ms.
   * @return a reference to this, so the API can be used fluently
   */
  public VertxOptions setBlockedThreadCheckInterval(long blockedThreadCheckInterval) {
    if (blockedThreadCheckInterval < 1) {
      throw new IllegalArgumentException("blockedThreadCheckInterval must be > 0");
    }
    this.blockedThreadCheckInterval = blockedThreadCheckInterval;
    return this;
  }

  /**
   * Get the value of max event loop execute time, in ns.
   * <p>
   * Vert.x will automatically log a warning if it detects that event loop threads haven't returned within this time.
   * <p>
   * This can be used to detect where the user is blocking an event loop thread, contrary to the Golden Rule of the
   * holy Event Loop.
   *
   * @return the value of max event loop execute time, in ms.
   */
  public long getMaxEventLoopExecuteTime() {
    return maxEventLoopExecuteTime;
  }

  /**
   * Sets the value of max event loop execute time, in ns.
   *
   * @param maxEventLoopExecuteTime  the value of max event loop execute time, in ms.
   * @return a reference to this, so the API can be used fluently
   */
  public VertxOptions setMaxEventLoopExecuteTime(long maxEventLoopExecuteTime) {
    if (maxEventLoopExecuteTime < 1) {
      throw new IllegalArgumentException("maxEventLoopExecuteTime must be > 0");
    }
    this.maxEventLoopExecuteTime = maxEventLoopExecuteTime;
    return this;
  }

  /**
   * Get the value of max worker execute time, in ns.
   * <p>
   * Vert.x will automatically log a warning if it detects that worker threads haven't returned within this time.
   * <p>
   * This can be used to detect where the user is blocking a worker thread for too long. Although worker threads
   * can be blocked longer than event loop threads, they shouldn't be blocked for long periods of time.
   *
   * @return The value of max worker execute time, in ms.
   */
  public long getMaxWorkerExecuteTime() {
    return maxWorkerExecuteTime;
  }

  /**
   * Sets the value of max worker execute time, in ns.
   *
   * @param maxWorkerExecuteTime  the value of max worker execute time, in ms.
   * @return a reference to this, so the API can be used fluently
   */
  public VertxOptions setMaxWorkerExecuteTime(long maxWorkerExecuteTime) {
    if (maxWorkerExecuteTime < 1) {
      throw new IllegalArgumentException("maxWorkerpExecuteTime must be > 0");
    }
    this.maxWorkerExecuteTime = maxWorkerExecuteTime;
    return this;
  }

  /**
   * Get the cluster manager to be used when clustering.
   * <p>
   * If the cluster manager has been programmatically set here, then that will be used when clustering.
   * <p>
   * Otherwise Vert.x attempts to locate a cluster manager on the classpath.
   *
   * @return  the cluster manager.
   */
  public ClusterManager getClusterManager() {
    return clusterManager;
  }

  /**
   * Programmatically set the cluster manager to be used when clustering.
   * <p>
   * Only valid if clustered = true.
   * <p>
   * Normally Vert.x will look on the classpath for a cluster manager, but if you want to set one
   * programmatically you can use this method.
   *
   * @param clusterManager  the cluster manager
   * @return a reference to this, so the API can be used fluently
   */
  public VertxOptions setClusterManager(ClusterManager clusterManager) {
    this.clusterManager = clusterManager;
    return this;
  }

  /**
   * Get the value of internal blocking pool size.
   * <p>
   * Vert.x maintains a pool for internal blocking operations
   *
   * @return the value of internal blocking pool size
   */
  public int getInternalBlockingPoolSize() {
    return internalBlockingPoolSize;
  }

  /**
   * Set the value of internal blocking pool size
   *
   * @param internalBlockingPoolSize the maximumn number of threads in the internal blocking pool
   * @return a reference to this, so the API can be used fluently
   */
  public VertxOptions setInternalBlockingPoolSize(int internalBlockingPoolSize) {
    if (internalBlockingPoolSize < 1) {
      throw new IllegalArgumentException("internalBlockingPoolSize must be > 0");
    }
    this.internalBlockingPoolSize = internalBlockingPoolSize;
    return this;
  }

  /**
   * Will HA be enabled on the Vert.x instance?
   *
   * @return true if HA enabled, false otherwise
   */
  public boolean isHAEnabled() {
    return haEnabled;
  }

  /**
   * Set whether HA will be enabled on the Vert.x instance.
   *
   * @param haEnabled  true if enabled, false if not.
   * @return a reference to this, so the API can be used fluently
   */
  public VertxOptions setHAEnabled(boolean haEnabled) {
    this.haEnabled = haEnabled;
    return this;
  }

  /**
   * Get the quorum size to be used when HA is enabled.
   *
   * @return  the quorum size
   */
  public int getQuorumSize() {
    return quorumSize;
  }

  /**
   * Set the quorum size to be used when HA is enabled.
   *
   * @param quorumSize  the quorum size
   * @return a reference to this, so the API can be used fluently
   */
  public VertxOptions setQuorumSize(int quorumSize) {
    if (quorumSize < 1) {
      throw new IllegalArgumentException("quorumSize should be >= 1");
    }
    this.quorumSize = quorumSize;
    return this;
  }

  /**
   * Get the HA group to be used when HA is enabled.
   *
   * @return the HA group
   */
  public String getHAGroup() {
    return haGroup;
  }

  /**
   * Set the HA group to be used when HA is enabled.
   *
   * @param haGroup the HA group to use
   * @return a reference to this, so the API can be used fluently
   */
  public VertxOptions setHAGroup(String haGroup) {
    Objects.requireNonNull(haGroup, "ha group cannot be null");
    this.haGroup = haGroup;
    return this;
  }

  /**
   * @return the metrics options
   */
  public MetricsOptions getMetricsOptions() {
    return metrics;
  }

  /**
   * Set the metrics options
   *
   * @param metrics the options
   * @return a reference to this, so the API can be used fluently
   */
  public VertxOptions setMetricsOptions(MetricsOptions metrics) {
    this.metrics = metrics;
    return this;
  }

  /**
   * Get the threshold value above this, the blocked warning contains a stack trace.
   *
   * @return the warning exception time threshold
   */
  public long getWarningExceptionTime() {
    return warningExceptionTime;
  }

  /**
   * Set the threshold value above this, the blocked warning contains a stack trace.
   *
   * @param warningExceptionTime
   * @return a reference to this, so the API can be used fluently
   */
  public VertxOptions setWarningExceptionTime(long warningExceptionTime) {
    if (warningExceptionTime < 1) {
      throw new IllegalArgumentException("warningExceptionTime must be > 0");
    }
    this.warningExceptionTime = warningExceptionTime;
    return this;
  }

  @Override
  public boolean equals(Object o) {
    if (this == o) return true;
    if (o == null || getClass() != o.getClass()) return false;

    VertxOptions that = (VertxOptions) o;

    if (blockedThreadCheckInterval != that.blockedThreadCheckInterval) return false;
    if (clusterPort != that.clusterPort) return false;
    if (clustered != that.clustered) return false;
    if (eventLoopPoolSize != that.eventLoopPoolSize) return false;
    if (haEnabled != that.haEnabled) return false;
    if (internalBlockingPoolSize != that.internalBlockingPoolSize) return false;
    if (maxEventLoopExecuteTime != that.maxEventLoopExecuteTime) return false;
    if (maxWorkerExecuteTime != that.maxWorkerExecuteTime) return false;
    if (quorumSize != that.quorumSize) return false;
    if (workerPoolSize != that.workerPoolSize) return false;
    if (clusterHost != null ? !clusterHost.equals(that.clusterHost) : that.clusterHost != null) return false;
    if (clusterManager != null ? !clusterManager.equals(that.clusterManager) : that.clusterManager != null)
      return false;
    if (haGroup != null ? !haGroup.equals(that.haGroup) : that.haGroup != null) return false;
    if (warningExceptionTime != that.warningExceptionTime) return false;

    return true;
  }

  @Override
  public int hashCode() {
    int result = eventLoopPoolSize;
    result = 31 * result + workerPoolSize;
    result = 31 * result + internalBlockingPoolSize;
    result = 31 * result + (clustered ? 1 : 0);
    result = 31 * result + (clusterHost != null ? clusterHost.hashCode() : 0);
    result = 31 * result + clusterPort;
    result = 31 * result + (int) (blockedThreadCheckInterval ^ (blockedThreadCheckInterval >>> 32));
    result = 31 * result + (int) (maxEventLoopExecuteTime ^ (maxEventLoopExecuteTime >>> 32));
    result = 31 * result + (int) (maxWorkerExecuteTime ^ (maxWorkerExecuteTime >>> 32));
    result = 31 * result + (clusterManager != null ? clusterManager.hashCode() : 0);
    result = 31 * result + (haEnabled ? 1 : 0);
    result = 31 * result + quorumSize;
    result = 31 * result + (haGroup != null ? haGroup.hashCode() : 0);
    result = 31 * result + (int) (warningExceptionTime ^ (warningExceptionTime >>> 32));
    return result;
  }
}


File: src/main/java/io/vertx/core/datagram/DatagramSocketOptions.java
/*
 * Copyright (c) 2011-2014 The original author or authors
 * ------------------------------------------------------
 * All rights reserved. This program and the accompanying materials
 * are made available under the terms of the Eclipse Public License v1.0
 * and Apache License v2.0 which accompanies this distribution.
 *
 *     The Eclipse Public License is available at
 *     http://www.eclipse.org/legal/epl-v10.html
 *
 *     The Apache License v2.0 is available at
 *     http://www.opensource.org/licenses/apache2.0.php
 *
 * You may elect to redistribute this code under either of these licenses.
 */

package io.vertx.core.datagram;

import io.vertx.codegen.annotations.DataObject;
import io.vertx.core.impl.Arguments;
import io.vertx.core.json.JsonObject;
import io.vertx.core.net.NetworkOptions;

/**
 * Options used to configure a datagram socket.
 *
 * @author <a href="http://tfox.org">Tim Fox</a>
 */
@DataObject
public class DatagramSocketOptions extends NetworkOptions {

  /**
   * The default value of broadcast for the socket = false
   */
  public static final boolean DEFAULT_BROADCAST = false;

  /**
   * The default value of loopback disabled = true
   */
  public static final boolean DEFAULT_LOOPBACK_MODE_DISABLED = true;

  /**
   * The default value of multicast disabled = -1
   */
  public static final int DEFAULT_MULTICAST_TIME_TO_LIVE = -1;

  /**
   * The default value of multicast network interface = null
   */
  public static final String DEFAULT_MULTICAST_NETWORK_INTERFACE = null;

  /**
   * The default value of reuse address = false
   */
  public static final boolean DEFAULT_REUSE_ADDRESS = false; // Override this

  /**
   * The default value of use IP v6 = false
   */
  public static final boolean DEFAULT_IPV6 = false;

  private boolean broadcast;
  private boolean loopbackModeDisabled;
  private int multicastTimeToLive;
  private String multicastNetworkInterface;
  private boolean ipV6;

  /**
   * Default constructor
   */
  public DatagramSocketOptions() {
    super();
    setReuseAddress(DEFAULT_REUSE_ADDRESS); // default is different for DatagramSocket
    broadcast = DEFAULT_BROADCAST;
    loopbackModeDisabled = DEFAULT_LOOPBACK_MODE_DISABLED;
    multicastTimeToLive = DEFAULT_MULTICAST_TIME_TO_LIVE;
    multicastNetworkInterface = DEFAULT_MULTICAST_NETWORK_INTERFACE;
    ipV6 = DEFAULT_IPV6;
  }

  /**
   * Copy constructor
   *
   * @param other  the options to copy
   */
  public DatagramSocketOptions(DatagramSocketOptions other) {
    super(other);
    this.broadcast = other.isBroadcast();
    this.loopbackModeDisabled = other.isLoopbackModeDisabled();
    this.multicastTimeToLive = other.getMulticastTimeToLive();
    this.multicastNetworkInterface = other.getMulticastNetworkInterface();
    this.ipV6 = other.isIpV6();
  }

  /**
   * Constructor to create options from JSON
   *
   * @param json  the JSON
   */
  public DatagramSocketOptions(JsonObject json) {
    super(json);
    this.broadcast = json.getBoolean("broadcast", DEFAULT_BROADCAST);
    this.loopbackModeDisabled = json.getBoolean("loopbackModeDisabled", DEFAULT_LOOPBACK_MODE_DISABLED);
    this.multicastTimeToLive = json.getInteger("multicastTimeToLive", DEFAULT_MULTICAST_TIME_TO_LIVE);
    this.multicastNetworkInterface = json.getString("multicastNetworkInterface", DEFAULT_MULTICAST_NETWORK_INTERFACE);
    this.ipV6 = json.getBoolean("ipV6", DEFAULT_IPV6);
    setReuseAddress(json.getBoolean("reuseAddress", DEFAULT_REUSE_ADDRESS));
  }

  @Override
  public int getSendBufferSize() {
    return super.getSendBufferSize();
  }

  @Override
  public DatagramSocketOptions setSendBufferSize(int sendBufferSize) {
    super.setSendBufferSize(sendBufferSize);
    return this;
  }

  @Override
  public int getReceiveBufferSize() {
    return super.getReceiveBufferSize();
  }

  @Override
  public DatagramSocketOptions setReceiveBufferSize(int receiveBufferSize) {
    super.setReceiveBufferSize(receiveBufferSize);
    return this;
  }

  @Override
  public DatagramSocketOptions setReuseAddress(boolean reuseAddress) {
    super.setReuseAddress(reuseAddress);
    return this;
  }

  @Override
  public int getTrafficClass() {
    return super.getTrafficClass();
  }

  @Override
  public DatagramSocketOptions setTrafficClass(int trafficClass) {
    super.setTrafficClass(trafficClass);
    return this;
  }

  /**
   * @return true if the socket receive broadcast packets?
   */
  public boolean isBroadcast() {
    return broadcast;
  }

  /**
   * Set if the socket can receive broadcast packets
   *
   * @param broadcast  true if the socket can receive broadcast packets
   * @return a reference to this, so the API can be used fluently
   */
  public DatagramSocketOptions setBroadcast(boolean broadcast) {
    this.broadcast = broadcast;
    return this;
  }

  /**
   * @return true if loopback mode is disabled
   *
   */
  public boolean isLoopbackModeDisabled() {
    return loopbackModeDisabled;
  }

  /**
   * Set if loopback mode is disabled
   *
   * @param loopbackModeDisabled  true if loopback mode is disabled
   * @return a reference to this, so the API can be used fluently
   */
  public DatagramSocketOptions setLoopbackModeDisabled(boolean loopbackModeDisabled) {
    this.loopbackModeDisabled = loopbackModeDisabled;
    return this;
  }

  /**
   * @return the multicast ttl value
   */
  public int getMulticastTimeToLive() {
    return multicastTimeToLive;
  }

  /**
   * Set the multicast ttl value
   *
   * @param multicastTimeToLive  the multicast ttl value
   * @return a reference to this, so the API can be used fluently
   */
  public DatagramSocketOptions setMulticastTimeToLive(int multicastTimeToLive) {
    Arguments.require(multicastTimeToLive >= 0, "multicastTimeToLive must be >= 0");
    this.multicastTimeToLive = multicastTimeToLive;
    return this;
  }

  /**
   * Get the multicast network interface address
   *
   * @return  the interface address
   */
  public String getMulticastNetworkInterface() {
    return multicastNetworkInterface;
  }

  /**
   * Set the multicast network interface address
   *
   * @param multicastNetworkInterface  the address
   * @return a reference to this, so the API can be used fluently
   */
  public DatagramSocketOptions setMulticastNetworkInterface(String multicastNetworkInterface) {
    this.multicastNetworkInterface = multicastNetworkInterface;
    return this;
  }

  /**
   * @return  true if IP v6 be used?
   */
  public boolean isIpV6() {
    return ipV6;
  }

  /**
   * Set if IP v6 should be used
   *
   * @param ipV6  true if IP v6 should be used
   * @return a reference to this, so the API can be used fluently
   */
  public DatagramSocketOptions setIpV6(boolean ipV6) {
    this.ipV6 = ipV6;
    return this;
  }

  @Override
  public boolean equals(Object o) {
    if (this == o) return true;
    if (!(o instanceof DatagramSocketOptions)) return false;
    if (!super.equals(o)) return false;

    DatagramSocketOptions that = (DatagramSocketOptions) o;

    if (broadcast != that.broadcast) return false;
    if (ipV6 != that.ipV6) return false;
    if (loopbackModeDisabled != that.loopbackModeDisabled) return false;
    if (multicastTimeToLive != that.multicastTimeToLive) return false;
    if (multicastNetworkInterface != null ? !multicastNetworkInterface.equals(that.multicastNetworkInterface) : that.multicastNetworkInterface != null)
      return false;

    return true;
  }

  @Override
  public int hashCode() {
    int result = super.hashCode();
    result = 31 * result + (broadcast ? 1 : 0);
    result = 31 * result + (loopbackModeDisabled ? 1 : 0);
    result = 31 * result + multicastTimeToLive;
    result = 31 * result + (multicastNetworkInterface != null ? multicastNetworkInterface.hashCode() : 0);
    result = 31 * result + (ipV6 ? 1 : 0);
    return result;
  }
}


File: src/main/java/io/vertx/core/file/OpenOptions.java
/*
 * Copyright (c) 2011-2014 The original author or authors
 * ------------------------------------------------------
 * All rights reserved. This program and the accompanying materials
 * are made available under the terms of the Eclipse Public License v1.0
 * and Apache License v2.0 which accompanies this distribution.
 *
 *     The Eclipse Public License is available at
 *     http://www.eclipse.org/legal/epl-v10.html
 *
 *     The Apache License v2.0 is available at
 *     http://www.opensource.org/licenses/apache2.0.php
 *
 * You may elect to redistribute this code under either of these licenses.
 */

package io.vertx.core.file;

import io.vertx.codegen.annotations.DataObject;
import io.vertx.core.json.JsonObject;

/**
 * Describes how an {@link io.vertx.core.file.AsyncFile} should be opened.
 * 
 * @author <a href="http://tfox.org">Tim Fox</a>
 */
@DataObject
public class OpenOptions {

  public static final String DEFAULT_PERMS = null;
  public static final boolean DEFAULT_READ = true;
  public static final boolean DEFAULT_WRITE = true;
  public static final boolean DEFAULT_CREATE = true;
  public static final boolean DEFAULT_CREATENEW = false;
  public static final boolean DEFAULT_DSYNC = false;
  public static final boolean DEFAULT_SYNC = false;
  public static final boolean DEFAULT_DELETEONCLOSE = false;
  public static final boolean DEFAULT_TRUNCATEEXISTING = false;
  public static final boolean DEFAULT_SPARSE = false;

  private String perms = DEFAULT_PERMS;
  private boolean read = DEFAULT_READ;
  private boolean write = DEFAULT_WRITE;
  private boolean create = DEFAULT_CREATE;
  private boolean createNew = DEFAULT_CREATENEW;
  private boolean dsync = DEFAULT_DSYNC;
  private boolean sync = DEFAULT_SYNC;
  private boolean deleteOnClose = DEFAULT_DELETEONCLOSE;
  private boolean truncateExisting = DEFAULT_TRUNCATEEXISTING;
  private boolean sparse = DEFAULT_SPARSE;

  /**
   * Default constructor
   */
  public OpenOptions() {
    super();
  }

  /**
   * Copy constructor
   *
   * @param other  the options to copy
   */
  public OpenOptions(OpenOptions other) {
    this.perms = other.perms;
    this.read = other.read;
    this.write = other.write;
    this.create = other.create;
    this.createNew = other.createNew;
    this.dsync = other.dsync;
    this.sync = other.sync;
    this.deleteOnClose = other.deleteOnClose;
    this.truncateExisting = other.truncateExisting;
    this.sparse = other.sparse;
  }

  /**
   * Constructor to create options from JSON
   *
   * @param json  the JSON
   */
  public OpenOptions(JsonObject json) {
    this.perms = json.getString("perms", DEFAULT_PERMS);
    this.read = json.getBoolean("read", DEFAULT_READ);
    this.write = json.getBoolean("write", DEFAULT_WRITE);
    this.create = json.getBoolean("create", DEFAULT_CREATE);
    this.createNew = json.getBoolean("createNew", DEFAULT_CREATENEW);
    this.dsync = json.getBoolean("dsync", DEFAULT_DSYNC);
    this.sync = json.getBoolean("sync", DEFAULT_SYNC);
    this.deleteOnClose = json.getBoolean("deleteOnClose", DEFAULT_DELETEONCLOSE);
    this.truncateExisting = json.getBoolean("truncateExisting", DEFAULT_TRUNCATEEXISTING);
    this.sparse = json.getBoolean("sparse", DEFAULT_SPARSE);
  }

  /**
   * Get the permissions string to be used if creating a file
   *
   * @return  the permissions string
   */
  public String getPerms() {
    return perms;
  }

  /**
   * Set the permissions string
   *
   * @param perms  the permissions string
   * @return a reference to this, so the API can be used fluently
   */
  public OpenOptions setPerms(String perms) {
    this.perms = perms;
    return this;
  }

  /**
   * Is the file to opened for reading?
   *
   * @return true if to be opened for reading
   */
  public boolean isRead() {
    return read;
  }

  /**
   * Set whether the file is to be opened for reading
   *
   * @param read  true if the file is to be opened for reading
   * @return a reference to this, so the API can be used fluently
   */
  public OpenOptions setRead(boolean read) {
    this.read = read;
    return this;
  }

  /**
   * Is the file to opened for writing?
   *
   * @return true if to be opened for writing
   */
  public boolean isWrite() {
    return write;
  }

  /**
   * Set whether the file is to be opened for writing
   *
   * @param write  true if the file is to be opened for writing
   * @return a reference to this, so the API can be used fluently
   */
  public OpenOptions setWrite(boolean write) {
    this.write = write;
    return this;
  }

  /**
   * Should the file be created if it does not already exist?
   *
   * @return true if the file should be created if it does not already exist
   */
  public boolean isCreate() {
    return create;
  }

  /**
   * Set whether the file should be created if it does not already exist.
   *
   * @param create  true if the file should be created if it does not already exist
   * @return a reference to this, so the API can be used fluently
   */
  public OpenOptions setCreate(boolean create) {
    this.create = create;
    return this;
  }

  /**
   * Should the file be created if and the open fail if it already exists?
   *
   * @return true if the file should be created if and the open fail if it already exists.
   */
  public boolean isCreateNew() {
    return createNew;
  }

  /**
   * Set whether the file should be created and fail if it does exist already.
   *
   * @param createNew  true if the file should be created or fail if it exists already
   * @return a reference to this, so the API can be used fluently
   */
  public OpenOptions setCreateNew(boolean createNew) {
    this.createNew = createNew;
    return this;
  }

  /**
   * Should the file be deleted when it's closed, or the JVM is shutdown.
   *
   * @return  true if the file should be deleted when it's closed or the JVM shutdown
   */
  public boolean isDeleteOnClose() {
    return deleteOnClose;
  }

  /**
   * Set whether the file should be deleted when it's closed, or the JVM is shutdown.
   *
   * @param deleteOnClose whether the file should be deleted when it's closed, or the JVM is shutdown.
   * @return  a reference to this, so the API can be used fluently
   */
  public OpenOptions setDeleteOnClose(boolean deleteOnClose) {
    this.deleteOnClose = deleteOnClose;
    return this;
  }

  /**
   * If the file exists and is opened for writing should the file be truncated to zero length on open?
   *
   * @return true  if the file exists and is opened for writing and the file be truncated to zero length on open
   */
  public boolean isTruncateExisting() {
    return truncateExisting;
  }

  /**
   * Set whether the file should be truncated to zero length on opening if it exists and is opened for write
   *
   * @param truncateExisting  true if the file should be truncated to zero length on opening if it exists and is opened for write
   * @return a reference to this, so the API can be used fluently
   */
  public OpenOptions setTruncateExisting(boolean truncateExisting) {
    this.truncateExisting = truncateExisting;
    return this;
  }

  /**
   * Set whether a hint should be provided that the file to created is sparse
   *
   * @return true if a hint should be provided that the file to created is sparse
   */
  public boolean isSparse() {
    return sparse;
  }

  /**
   * Set whether a hint should be provided that the file to created is sparse
   * @param sparse true if a hint should be provided that the file to created is sparse
   * @return a reference to this, so the API can be used fluently
   */
  public OpenOptions setSparse(boolean sparse) {
    this.sparse = sparse;
    return this;
  }

  /**
   * If true then every write to the file's content and metadata will be written synchronously to the underlying hardware.
   *
   * @return true if sync
   */
  public boolean isSync() {
    return sync;
  }

  /**
   * Set whether every write to the file's content and meta-data will be written synchronously to the underlying hardware.
   * @param sync  true if sync
   * @return a reference to this, so the API can be used fluently
   */
  public OpenOptions setSync(boolean sync) {
    this.sync = sync;
    return this;
  }

  /**
   * If true then every write to the file's content will be written synchronously to the underlying hardware.
   *
   * @return true if sync
   */
  public boolean isDSync() {
    return dsync;
  }

  /**
   * Set whether every write to the file's content  ill be written synchronously to the underlying hardware.
   * @param dsync  true if sync
   * @return a reference to this, so the API can be used fluently
   */
  public OpenOptions setDSync(boolean dsync) {
    this.dsync = dsync;
    return this;
  }
}


File: src/main/java/io/vertx/core/file/impl/AsyncFileImpl.java
/*
 * Copyright (c) 2011-2013 The original author or authors
 * ------------------------------------------------------
 * All rights reserved. This program and the accompanying materials
 * are made available under the terms of the Eclipse Public License v1.0
 * and Apache License v2.0 which accompanies this distribution.
 *
 *     The Eclipse Public License is available at
 *     http://www.eclipse.org/legal/epl-v10.html
 *
 *     The Apache License v2.0 is available at
 *     http://www.opensource.org/licenses/apache2.0.php
 *
 * You may elect to redistribute this code under either of these licenses.
 */

package io.vertx.core.file.impl;

import io.netty.buffer.ByteBuf;
import io.vertx.core.AsyncResult;
import io.vertx.core.Future;
import io.vertx.core.Handler;
import io.vertx.core.buffer.Buffer;
import io.vertx.core.file.AsyncFile;
import io.vertx.core.file.FileSystemException;
import io.vertx.core.file.OpenOptions;
import io.vertx.core.impl.Arguments;
import io.vertx.core.impl.ContextImpl;
import io.vertx.core.impl.VertxInternal;
import io.vertx.core.logging.Logger;
import io.vertx.core.logging.LoggerFactory;

import java.io.IOException;
import java.nio.ByteBuffer;
import java.nio.channels.AsynchronousFileChannel;
import java.nio.file.OpenOption;
import java.nio.file.Path;
import java.nio.file.Paths;
import java.nio.file.StandardOpenOption;
import java.nio.file.attribute.FileAttribute;
import java.nio.file.attribute.PosixFilePermissions;
import java.util.HashSet;
import java.util.Objects;
import java.util.concurrent.atomic.AtomicBoolean;
import java.util.concurrent.atomic.AtomicInteger;

/**
 *
 * This class is optimised for performance when used on the same event loop that is was passed to the handler with.
 * However it can be used safely from other threads.
 *
 * The internal state is protected using the synchronized keyword. If always used on the same event loop, then
 * we benefit from biased locking which makes the overhead of synchronized near zero.
 *
 * @author <a href="http://tfox.org">Tim Fox</a>
 */
public class AsyncFileImpl implements AsyncFile {

  private static final Logger log = LoggerFactory.getLogger(AsyncFile.class);

  public static final int BUFFER_SIZE = 8192;

  private final VertxInternal vertx;
  private final AsynchronousFileChannel ch;
  private final ContextImpl context;
  private boolean closed;
  private Runnable closedDeferred;
  private long writesOutstanding;
  private Handler<Throwable> exceptionHandler;
  private Handler<Void> drainHandler;
  private long writePos;
  private int maxWrites = 128 * 1024;    // TODO - we should tune this for best performance
  private int lwm = maxWrites / 2;
  private boolean paused;
  private Handler<Buffer> dataHandler;
  private Handler<Void> endHandler;
  private long readPos;
  private boolean readInProgress;

  AsyncFileImpl(VertxInternal vertx, String path, OpenOptions options, ContextImpl context) {
    if (!options.isRead() && !options.isWrite()) {
      throw new FileSystemException("Cannot open file for neither reading nor writing");
    }
    this.vertx = vertx;
    Path file = Paths.get(path);
    HashSet<OpenOption> opts = new HashSet<>();
    if (options.isRead()) opts.add(StandardOpenOption.READ);
    if (options.isWrite()) opts.add(StandardOpenOption.WRITE);
    if (options.isCreate()) opts.add(StandardOpenOption.CREATE);
    if (options.isCreateNew()) opts.add(StandardOpenOption.CREATE_NEW);
    if (options.isSync()) opts.add(StandardOpenOption.SYNC);
    if (options.isDSync()) opts.add(StandardOpenOption.DSYNC);
    if (options.isDeleteOnClose()) opts.add(StandardOpenOption.DELETE_ON_CLOSE);
    if (options.isSparse()) opts.add(StandardOpenOption.SPARSE);
    if (options.isTruncateExisting()) opts.add(StandardOpenOption.TRUNCATE_EXISTING);
    try {
      if (options.getPerms() != null) {
        FileAttribute<?> attrs = PosixFilePermissions.asFileAttribute(PosixFilePermissions.fromString(options.getPerms()));
        ch = AsynchronousFileChannel.open(file, opts, vertx.getWorkerPool(), attrs);
      } else {
        ch = AsynchronousFileChannel.open(file, opts, vertx.getWorkerPool());
      }
    } catch (IOException e) {
      throw new FileSystemException(e);
    }
    this.context = context;
  }

  @Override
  public void close() {
    closeInternal(null);
  }

  @Override
  public void close(Handler<AsyncResult<Void>> handler) {
    closeInternal(handler);
  }


  @Override
  public synchronized AsyncFile read(Buffer buffer, int offset, long position, int length, Handler<AsyncResult<Buffer>> handler) {
    Objects.requireNonNull(buffer, "buffer");
    Objects.requireNonNull(handler, "handler");
    Arguments.require(offset >= 0, "offset must be >= 0");
    Arguments.require(position >= 0, "position must be >= 0");
    Arguments.require(length >= 0, "length must be >= 0");
    check();
    ByteBuffer bb = ByteBuffer.allocate(length);
    doRead(buffer, offset, bb, position, handler);
    return this;
  }

  @Override
  public AsyncFile write(Buffer buffer, long position, Handler<AsyncResult<Void>> handler) {
    Objects.requireNonNull(handler, "handler");
    return doWrite(buffer, position, handler);
  }

  private synchronized AsyncFile doWrite(Buffer buffer, long position, Handler<AsyncResult<Void>> handler) {
    Objects.requireNonNull(buffer, "buffer");
    Arguments.require(position >= 0, "position must be >= 0");
    check();
    Handler<AsyncResult<Void>> wrapped = ar -> {
      if (ar.succeeded()) {
        checkContext();
        checkDrained();
        if (writesOutstanding == 0 && closedDeferred != null) {
          closedDeferred.run();
        }
        if (handler != null) {
          handler.handle(ar);
        }
      } else {
        if (handler != null) {
          handler.handle(ar);
        } else {
          handleException(ar.cause());
        }
      }
    };
    ByteBuf buf = buffer.getByteBuf();
    if (buf.nioBufferCount() > 1) {
      doWrite(buf.nioBuffers(), position, wrapped);
    } else {
      ByteBuffer bb = buf.nioBuffer();
      doWrite(bb, position, bb.limit(),  wrapped);
    }
    return this;
  }

  @Override
  public AsyncFile write(Buffer buffer) {
    int length = buffer.length();
    doWrite(buffer, writePos, null);
    writePos += length;
    return this;
  }

  @Override
  public synchronized AsyncFile setWriteQueueMaxSize(int maxSize) {
    Arguments.require(maxSize >= 2, "maxSize must be >= 2");
    check();
    this.maxWrites = maxSize;
    this.lwm = maxWrites / 2;
    return this;
  }

  @Override
  public synchronized boolean writeQueueFull() {
    check();
    return writesOutstanding >= maxWrites;
  }

  @Override
  public synchronized AsyncFile drainHandler(Handler<Void> handler) {
    check();
    this.drainHandler = handler;
    checkDrained();
    return this;
  }

  @Override
  public synchronized AsyncFile exceptionHandler(Handler<Throwable> handler) {
    check();
    this.exceptionHandler = handler;
    return this;
  }

  @Override
  public synchronized AsyncFile handler(Handler<Buffer> handler) {
    check();
    this.dataHandler = handler;
    if (dataHandler != null && !paused && !closed) {
      doRead();
    }
    return this;
  }

  @Override
  public synchronized AsyncFile endHandler(Handler<Void> handler) {
    check();
    this.endHandler = handler;
    return this;
  }

  @Override
  public synchronized AsyncFile pause() {
    check();
    paused = true;
    return this;
  }

  @Override
  public synchronized AsyncFile resume() {
    check();
    if (paused && !closed) {
      paused = false;
      if (dataHandler != null) {
        doRead();
      }
    }
    return this;
  }


  @Override
  public AsyncFile flush() {
    doFlush(null);
    return this;
  }

  @Override
  public AsyncFile flush(Handler<AsyncResult<Void>> handler) {
    doFlush(handler);
    return this;
  }

  @Override
  public synchronized AsyncFile setReadPos(long readPos) {
    this.readPos = readPos;
    return this;
  }

  @Override
  public synchronized AsyncFile setWritePos(long writePos) {
    this.writePos = writePos;
    return this;
  }

  private synchronized void checkDrained() {
    if (drainHandler != null && writesOutstanding <= lwm) {
      Handler<Void> handler = drainHandler;
      drainHandler = null;
      handler.handle(null);
    }
  }

  private void handleException(Throwable t) {
    if (exceptionHandler != null && t instanceof Exception) {
      exceptionHandler.handle(t);
    } else {
      log.error("Unhandled exception", t);

    }
  }

  private synchronized void doWrite(ByteBuffer[] buffers, long position, Handler<AsyncResult<Void>> handler) {
    AtomicInteger cnt = new AtomicInteger();
    AtomicBoolean sentFailure = new AtomicBoolean();
    for (ByteBuffer b: buffers) {
      int limit = b.limit();
      doWrite(b, position, limit, ar -> {
        if (ar.succeeded()) {
          if (cnt.incrementAndGet() == buffers.length) {
            handler.handle(ar);
          }
        } else {
          if (sentFailure.compareAndSet(false, true)) {
            handler.handle(ar);
          }
        }
      });
      position += limit;
    }
  }

  private synchronized void doRead() {
    if (!readInProgress) {
      readInProgress = true;
      Buffer buff = Buffer.buffer(BUFFER_SIZE);
      read(buff, 0, readPos, BUFFER_SIZE, ar -> {
        if (ar.succeeded()) {
          readInProgress = false;
          Buffer buffer = ar.result();
          if (buffer.length() == 0) {
            // Empty buffer represents end of file
            handleEnd();
          } else {
            readPos += buffer.length();
            handleData(buffer);
            if (!paused && dataHandler != null) {
              doRead();
            }
          }
        } else {
          handleException(ar.cause());
        }
      });
    }
  }

  private synchronized void handleData(Buffer buffer) {
    if (dataHandler != null) {
      checkContext();
      dataHandler.handle(buffer);
    }
  }

  private synchronized void handleEnd() {
    if (endHandler != null) {
      checkContext();
      endHandler.handle(null);
    }
  }

  private synchronized void doFlush(Handler<AsyncResult<Void>> handler) {
    checkClosed();
    context.executeBlocking(() -> {
      try {
        ch.force(false);
        return null;
      } catch (IOException e) {
        throw new FileSystemException(e);
      }
    }, handler);
  }

  private void doWrite(ByteBuffer buff, long position, long toWrite, Handler<AsyncResult<Void>> handler) {
    if (toWrite == 0) {
      throw new IllegalStateException("Cannot save zero bytes");
    }
    writesOutstanding += toWrite;
    writeInternal(buff, position, handler);
  }

  private void writeInternal(ByteBuffer buff, long position, Handler<AsyncResult<Void>> handler) {

    ch.write(buff, position, null, new java.nio.channels.CompletionHandler<Integer, Object>() {

      public void completed(Integer bytesWritten, Object attachment) {

        long pos = position;

        if (buff.hasRemaining()) {
          // partial write
          pos += bytesWritten;
          // resubmit
          writeInternal(buff, pos, handler);
        } else {
          // It's been fully written
          context.runOnContext((v) -> {
            writesOutstanding -= buff.limit();
            handler.handle(Future.succeededFuture());
          });
        }
      }

      public void failed(Throwable exc, Object attachment) {
        if (exc instanceof Exception) {
          context.runOnContext((v) -> handler.handle(Future.succeededFuture()));
        } else {
          log.error("Error occurred", exc);
        }
      }
    });
  }

  private void doRead(Buffer writeBuff, int offset, ByteBuffer buff, long position, Handler<AsyncResult<Buffer>> handler) {

    ch.read(buff, position, null, new java.nio.channels.CompletionHandler<Integer, Object>() {

      long pos = position;

      private void done() {
        context.runOnContext((v) -> {
          buff.flip();
          writeBuff.setBytes(offset, buff);
          handler.handle(Future.succeededFuture(writeBuff));
        });
      }

      public void completed(Integer bytesRead, Object attachment) {
        if (bytesRead == -1) {
          //End of file
          done();
        } else if (buff.hasRemaining()) {
          // partial read
          pos += bytesRead;
          // resubmit
          doRead(writeBuff, offset, buff, pos, handler);
        } else {
          // It's been fully written
          done();
        }
      }

      public void failed(Throwable t, Object attachment) {
        context.runOnContext((v) -> handler.handle(Future.failedFuture(t)));
      }
    });
  }

  private void check() {
    checkClosed();
  }

  private void checkClosed() {
    if (closed) {
      throw new IllegalStateException("File handle is closed");
    }
  }

  private void checkContext() {
    if (!vertx.getContext().equals(context)) {
      throw new IllegalStateException("AsyncFile must only be used in the context that created it, expected: "
          + context + " actual " + vertx.getContext());
    }
  }

  private void doClose(Handler<AsyncResult<Void>> handler) {
    Future<Void> res = Future.future();
    try {
      ch.close();
      res.complete(null);
    } catch (IOException e) {
      res.fail(e);
    }
    if (handler != null) {
      vertx.runOnContext(v -> handler.handle(res));
    }
  }

  private synchronized void closeInternal(Handler<AsyncResult<Void>> handler) {
    check();

    closed = true;

    if (writesOutstanding == 0) {
      doClose(handler);
    } else {
      closedDeferred = () -> doClose(handler);
    }
  }

}


File: src/main/java/io/vertx/core/file/package-info.java
/*
 * Copyright 2014 Red Hat, Inc.
 *
 *  All rights reserved. This program and the accompanying materials
 *  are made available under the terms of the Eclipse Public License v1.0
 *  and Apache License v2.0 which accompanies this distribution.
 *
 *  The Eclipse Public License is available at
 *  http://www.eclipse.org/legal/epl-v10.html
 *
 *  The Apache License v2.0 is available at
 *  http://www.opensource.org/licenses/apache2.0.php
 *
 *  You may elect to redistribute this code under either of these licenses.
 */

/**
 * == Using the file system with Vert.x
 *
 * The Vert.x {@link io.vertx.core.file.FileSystem} object provides many operations for manipulating the file system.
 *
 * There is one file system object per Vert.x instance, and you obtain it with  {@link io.vertx.core.Vertx#fileSystem()}.
 *
 * A blocking and a non blocking version of each operation is provided. The non blocking versions take a handler
 * which is called when the operation completes or an error occurs.
 *
 * Here's an example of an asynchronous copy of a file:
 *
 * [source,$lang]
 * ----
 * {@link examples.FileSystemExamples#example1}
 * ----
 * The blocking versions are named `xxxBlocking` and return the results or throw exceptions directly. In many
 * cases, depending on the operating system and file system, some of the potentially blocking operations can return
 * quickly, which is why we provide them, but it's highly recommended that you test how long they take to return in your
 * particular application before using them from an event loop, so as not to break the Golden Rule.
 *
 * Here's the copy using the blocking API:
 *
 * [source,$lang]
 * ----
 * {@link examples.FileSystemExamples#example2}
 * ----
 *
 * Many operations exist to copy, move, truncate, chmod and many other file operations. We won't list them all here,
 * please consult the {@link io.vertx.core.file.FileSystem API docs} for the full list.
 *
 * Let's see a couple of examples using asynchronous methods:
 *
 * [source,$lang]
 * ----
 * {@link examples.FileSystemExamples#asyncAPIExamples}
 * ----
 *
 * === Asynchronous files
 *
 * Vert.x provides an asynchronous file abstraction that allows you to manipulate a file on the file system.
 *
 * You open an {@link io.vertx.core.file.AsyncFile AsyncFile} as follows:
 *
 * [source,$lang]
 * ----
 * {@link examples.FileSystemExamples#example3}
 * ----
 *
 * `AsyncFile` implements `ReadStream` and `WriteStream` so you can _pump_
 * files to and from other stream objects such as net sockets, http requests and responses, and WebSockets.
 *
 * They also allow you to read and write directly to them.
 *
 * ==== Random access writes
 *
 * To use an `AsyncFile` for random access writing you use the
 * {@link io.vertx.core.file.AsyncFile#write(io.vertx.core.buffer.Buffer, long, io.vertx.core.Handler) write} method.
 *
 * The parameters to the method are:
 *
 * * `buffer`: the buffer to write.
 * * `position`: an integer position in the file where to write the buffer. If the position is greater or equal to the size
 *  of the file, the file will be enlarged to accommodate the offset.
 * * `handler`: the result handler
 *
 * Here is an example of random access writes:
 *
 * [source,$lang]
 * ----
 * {@link examples.FileSystemExamples#asyncFileWrite()}
 * ----
 *
 * ==== Random access reads
 *
 * To use an `AsyncFile` for random access reads you use the
 * {@link io.vertx.core.file.AsyncFile#read(io.vertx.core.buffer.Buffer, int, long, int, io.vertx.core.Handler) read}
 * method.
 *
 * The parameters to the method are:
 *
 * * `buffer`: the buffer into which the data will be read.
 * * `offset`: an integer offset into the buffer where the read data will be placed.
 * * `position`: the position in the file where to read data from.
 * * `length`: the number of bytes of data to read
 * * `handler`: the result handler
 *
 * Here's an example of random access reads:
 *
 * [source,$lang]
 * ----
 * {@link examples.FileSystemExamples#asyncFileRead()}
 * ----
 *
 * ==== Opening Options
 *
 * When opening an `AsyncFile`, you pass an {@link io.vertx.core.file.OpenOptions OpenOptions} instance.
 * These options describe the behavior of the file access. For instance, you can configure the file permissions with the
 * {@link io.vertx.core.file.OpenOptions#setRead(boolean)}, {@link io.vertx.core.file.OpenOptions#setWrite(boolean)}
 * and {@link io.vertx.core.file.OpenOptions#setPerms(java.lang.String)} methods.
 *
 * You can also configure the behavior if the open file already exists with
 * {@link io.vertx.core.file.OpenOptions#setCreateNew(boolean)} and
 * {@link io.vertx.core.file.OpenOptions#setTruncateExisting(boolean)}.
 *
 * You can also mark the file to be deleted on
 * close or when the JVM is shutdown with {@link io.vertx.core.file.OpenOptions#setDeleteOnClose(boolean)}.
 *
 * ==== Flushing data to underlying storage.
 *
 * In the `OpenOptions`, you can enable/disable the automatic synchronisation of the content on every write using
 * {@link io.vertx.core.file.OpenOptions#setDSync(boolean)}. In that case, you can manually flush any writes from the OS
 * cache by calling the {@link io.vertx.core.file.AsyncFile#flush()} method.
 *
 * This method can also be called with an handler which will be called when the flush is complete.
 *
 * ==== Using AsyncFile as ReadStream and WriteStream
 *
 * `AsyncFile` implements `ReadStream` and `WriteStream`. You can then
 * use them with a _pump_ to pump data to and from other read and write streams. For example, this would
 * copy the content to another `AsyncFile`:
 *
 * [source,$lang]
 * ----
 * {@link examples.FileSystemExamples#asyncFilePump()}
 * ----
 *
 * You can also use the _pump_ to write file content into HTTP responses, or more generally in any
 * `WriteStream`.
 *
 * ==== Closing an AsyncFile
 *
 * To close an `AsyncFile` call the {@link io.vertx.core.file.AsyncFile#close()} method. Closing is asynchronous and
 * if you want to be notified when the close has been completed you can specify a handler function as an argument.
 *
 */
@Document(fileName = "filesystem.adoc")
package io.vertx.core.file;

import io.vertx.docgen.Document;



File: src/main/java/io/vertx/core/http/HttpClientOptions.java
/*
 * Copyright (c) 2011-2014 The original author or authors
 * ------------------------------------------------------
 * All rights reserved. This program and the accompanying materials
 * are made available under the terms of the Eclipse Public License v1.0
 * and Apache License v2.0 which accompanies this distribution.
 *
 *     The Eclipse Public License is available at
 *     http://www.eclipse.org/legal/epl-v10.html
 *
 *     The Apache License v2.0 is available at
 *     http://www.opensource.org/licenses/apache2.0.php
 *
 * You may elect to redistribute this code under either of these licenses.
 */

package io.vertx.core.http;

import io.vertx.codegen.annotations.DataObject;
import io.vertx.core.buffer.Buffer;
import io.vertx.core.json.JsonObject;
import io.vertx.core.net.ClientOptionsBase;
import io.vertx.core.net.JksOptions;
import io.vertx.core.net.PemTrustOptions;
import io.vertx.core.net.PemKeyCertOptions;
import io.vertx.core.net.PfxOptions;
import io.vertx.core.net.TCPSSLOptions;

/**
 * Options describing how an {@link HttpClient} will make connections.
 *
 * @author <a href="http://tfox.org">Tim Fox</a>
 */
@DataObject
public class HttpClientOptions extends ClientOptionsBase {

  /**
   * The default maximum number of connections a client will pool = 5
   */
  public static final int DEFAULT_MAX_POOL_SIZE = 5;

  /**
   * Default value of whether keep-alive is enabled = true
   */
  public static final boolean DEFAULT_KEEP_ALIVE = true;

  /**
   * Default value of whether pipe-lining is enabled = false
   */
  public static final boolean DEFAULT_PIPELINING = false;

  /**
   * Default value of whether the client will attempt to use compression = false
   */
  public static final boolean DEFAULT_TRY_USE_COMPRESSION = false;

  /**
   * Default value of whether hostname verification (for SSL/TLS) is enabled = true
   */
  public static final boolean DEFAULT_VERIFY_HOST = true;

  /**
   * The default value for maximum websocket frame size = 65536 bytes
   */
  public static final int DEFAULT_MAX_WEBSOCKET_FRAME_SIZE = 65536;

  /**
   * The default value for host name = "localhost"
   */
  public static final String DEFAULT_DEFAULT_HOST = "localhost";

  /**
   * The default value for port = 80
   */
  public static final int DEFAULT_DEFAULT_PORT = 80;

  private boolean verifyHost = true;
  private int maxPoolSize;
  private boolean keepAlive;
  private boolean pipelining;
  private boolean tryUseCompression;
  private int maxWebsocketFrameSize;
  private String defaultHost;
  private int defaultPort;

  /**
   * Default constructor
   */
  public HttpClientOptions() {
    super();
    verifyHost = DEFAULT_VERIFY_HOST;
    maxPoolSize = DEFAULT_MAX_POOL_SIZE;
    keepAlive = DEFAULT_KEEP_ALIVE;
    pipelining = DEFAULT_PIPELINING;
    tryUseCompression = DEFAULT_TRY_USE_COMPRESSION;
    maxWebsocketFrameSize = DEFAULT_MAX_WEBSOCKET_FRAME_SIZE;
    defaultHost = DEFAULT_DEFAULT_HOST;
    defaultPort = DEFAULT_DEFAULT_PORT;
  }

  /**
   * Copy constructor
   *
   * @param other  the options to copy
   */
  public HttpClientOptions(HttpClientOptions other) {
    super(other);
    this.verifyHost = other.isVerifyHost();
    this.maxPoolSize = other.getMaxPoolSize();
    this.keepAlive = other.isKeepAlive();
    this.pipelining = other.isPipelining();
    this.tryUseCompression = other.isTryUseCompression();
    this.maxWebsocketFrameSize = other.maxWebsocketFrameSize;
    this.defaultHost = other.defaultHost;
    this.defaultPort = other.defaultPort;
  }

  /**
   * Constructor to create an options from JSON
   *
   * @param json  the JSON
   */
  public HttpClientOptions(JsonObject json) {
    super(json);
    this.verifyHost = json.getBoolean("verifyHost", DEFAULT_VERIFY_HOST);
    this.maxPoolSize = json.getInteger("maxPoolSize", DEFAULT_MAX_POOL_SIZE);
    this.keepAlive = json.getBoolean("keepAlive", DEFAULT_KEEP_ALIVE);
    this.pipelining = json.getBoolean("pipelining", DEFAULT_PIPELINING);
    this.tryUseCompression = json.getBoolean("tryUseCompression", DEFAULT_TRY_USE_COMPRESSION);
    this.maxWebsocketFrameSize = json.getInteger("maxWebsocketFrameSize", DEFAULT_MAX_WEBSOCKET_FRAME_SIZE);
    this.defaultHost = json.getString("defaultHost", DEFAULT_DEFAULT_HOST);
    this.defaultPort = json.getInteger("defaultPort", DEFAULT_DEFAULT_PORT);
  }

  @Override
  public HttpClientOptions setSendBufferSize(int sendBufferSize) {
    super.setSendBufferSize(sendBufferSize);
    return this;
  }

  @Override
  public HttpClientOptions setReceiveBufferSize(int receiveBufferSize) {
    super.setReceiveBufferSize(receiveBufferSize);
    return this;
  }

  @Override
  public HttpClientOptions setReuseAddress(boolean reuseAddress) {
    super.setReuseAddress(reuseAddress);
    return this;
  }

  @Override
  public HttpClientOptions setTrafficClass(int trafficClass) {
    super.setTrafficClass(trafficClass);
    return this;
  }

  @Override
  public HttpClientOptions setTcpNoDelay(boolean tcpNoDelay) {
    super.setTcpNoDelay(tcpNoDelay);
    return this;
  }

  @Override
  public HttpClientOptions setTcpKeepAlive(boolean tcpKeepAlive) {
    super.setTcpKeepAlive(tcpKeepAlive);
    return this;
  }

  @Override
  public HttpClientOptions setSoLinger(int soLinger) {
    super.setSoLinger(soLinger);
    return this;
  }

  @Override
  public HttpClientOptions setUsePooledBuffers(boolean usePooledBuffers) {
    super.setUsePooledBuffers(usePooledBuffers);
    return this;
  }

  @Override
  public HttpClientOptions setIdleTimeout(int idleTimeout) {
    super.setIdleTimeout(idleTimeout);
    return this;
  }

  @Override
  public HttpClientOptions setSsl(boolean ssl) {
    super.setSsl(ssl);
    return this;
  }

  @Override
  public HttpClientOptions setKeyStoreOptions(JksOptions options) {
    super.setKeyStoreOptions(options);
    return this;
  }

  @Override
  public HttpClientOptions setPfxKeyCertOptions(PfxOptions options) {
    return (HttpClientOptions) super.setPfxKeyCertOptions(options);
  }

  @Override
  public HttpClientOptions setPemKeyCertOptions(PemKeyCertOptions options) {
    return (HttpClientOptions) super.setPemKeyCertOptions(options);
  }

  @Override
  public HttpClientOptions setTrustStoreOptions(JksOptions options) {
    super.setTrustStoreOptions(options);
    return this;
  }

  @Override
  public HttpClientOptions setPfxTrustOptions(PfxOptions options) {
    return (HttpClientOptions) super.setPfxTrustOptions(options);
  }

  @Override
  public HttpClientOptions setPemTrustOptions(PemTrustOptions options) {
    return (HttpClientOptions) super.setPemTrustOptions(options);
  }

  @Override
  public HttpClientOptions addEnabledCipherSuite(String suite) {
    super.addEnabledCipherSuite(suite);
    return this;
  }

  @Override
  public HttpClientOptions addCrlPath(String crlPath) throws NullPointerException {
    return (HttpClientOptions) super.addCrlPath(crlPath);
  }

  @Override
  public HttpClientOptions addCrlValue(Buffer crlValue) throws NullPointerException {
    return (HttpClientOptions) super.addCrlValue(crlValue);
  }

  @Override
  public HttpClientOptions setConnectTimeout(int connectTimeout) {
    super.setConnectTimeout(connectTimeout);
    return this;
  }

  @Override
  public HttpClientOptions setTrustAll(boolean trustAll) {
    super.setTrustAll(trustAll);
    return this;
  }

  /**
   * Get the maximum pool size for connections
   *
   * @return  the maximum pool size
   */
  public int getMaxPoolSize() {
    return maxPoolSize;
  }

  /**
   * Set the maximum pool size for connections
   *
   * @param maxPoolSize  the maximum pool size
   * @return a reference to this, so the API can be used fluently
   */
  public HttpClientOptions setMaxPoolSize(int maxPoolSize) {
    if (maxPoolSize < 1) {
      throw new IllegalArgumentException("maxPoolSize must be > 0");
    }
    this.maxPoolSize = maxPoolSize;
    return this;
  }

  /**
   * Is keep alive enabled on the client?
   *
   * @return true if enabled
   */
  public boolean isKeepAlive() {
    return keepAlive;
  }

  /**
   * Set whether keep alive is enabled on the client
   *
   * @param keepAlive  true if enabled
   * @return a reference to this, so the API can be used fluently
   */
  public HttpClientOptions setKeepAlive(boolean keepAlive) {
    this.keepAlive = keepAlive;
    return this;
  }

  /**
   * Is pipe-lining enabled on the client
   *
   * @return  true if pipe-lining is enabled
   */
  public boolean isPipelining() {
    return pipelining;
  }

  /**
   * Set whether pipe-lining is enabled on the client
   *
   * @param pipelining  true if enabled
   * @return a reference to this, so the API can be used fluently
   */
  public HttpClientOptions setPipelining(boolean pipelining) {
    this.pipelining = pipelining;
    return this;
  }

  /**
   * Is hostname verification (for SSL/TLS) enabled?
   *
   * @return  true if enabled
   */
  public boolean isVerifyHost() {
    return verifyHost;
  }

  /**
   * Set whether hostname verification is enabled
   *
   * @param verifyHost  true if enabled
   * @return a reference to this, so the API can be used fluently
   */
  public HttpClientOptions setVerifyHost(boolean verifyHost) {
    this.verifyHost = verifyHost;
    return this;
  }

  /**
   * Is compression enabled on the client?
   *
   * @return  true if enabled
   */
  public boolean isTryUseCompression() {
    return tryUseCompression;
  }

  /**
   * Set whether compression is enabled
   *
   * @param tryUseCompression  true if enabled
   * @return a reference to this, so the API can be used fluently
   */
  public HttpClientOptions setTryUseCompression(boolean tryUseCompression) {
    this.tryUseCompression = tryUseCompression;
    return this;
  }

  /**
   * Get the maximum websocket framesize to use
   *
   * @return  the max websocket framesize
   */
  public int getMaxWebsocketFrameSize() {
    return maxWebsocketFrameSize;
  }

  /**
   * Set the max websocket frame size
   *
   * @param maxWebsocketFrameSize  the max frame size, in bytes
   * @return a reference to this, so the API can be used fluently
   */
  public HttpClientOptions setMaxWebsocketFrameSize(int maxWebsocketFrameSize) {
    this.maxWebsocketFrameSize = maxWebsocketFrameSize;
    return this;
  }

  /**
   * Get the default host name to be used by this client in requests if none is provided when making the request.
   *
   * @return  the default host name
   */
  public String getDefaultHost() {
    return defaultHost;
  }

  /**
   * Set the default host name to be used by this client in requests if none is provided when making the request.
   *
   * @return a reference to this, so the API can be used fluently
   */
  public HttpClientOptions setDefaultHost(String defaultHost) {
    this.defaultHost = defaultHost;
    return this;
  }

  /**
   * Get the default port to be used by this client in requests if none is provided when making the request.
   *
   * @return  the default port
   */
  public int getDefaultPort() {
    return defaultPort;
  }

  /**
   * Set the default port to be used by this client in requests if none is provided when making the request.
   *
   * @return a reference to this, so the API can be used fluently
   */
  public HttpClientOptions setDefaultPort(int defaultPort) {
    this.defaultPort = defaultPort;
    return this;
  }

  @Override
  public boolean equals(Object o) {
    if (this == o) return true;
    if (!(o instanceof HttpClientOptions)) return false;
    if (!super.equals(o)) return false;

    HttpClientOptions that = (HttpClientOptions) o;

    if (defaultPort != that.defaultPort) return false;
    if (keepAlive != that.keepAlive) return false;
    if (maxPoolSize != that.maxPoolSize) return false;
    if (maxWebsocketFrameSize != that.maxWebsocketFrameSize) return false;
    if (pipelining != that.pipelining) return false;
    if (tryUseCompression != that.tryUseCompression) return false;
    if (verifyHost != that.verifyHost) return false;
    if (!defaultHost.equals(that.defaultHost)) return false;

    return true;
  }

  @Override
  public int hashCode() {
    int result = super.hashCode();
    result = 31 * result + (verifyHost ? 1 : 0);
    result = 31 * result + maxPoolSize;
    result = 31 * result + (keepAlive ? 1 : 0);
    result = 31 * result + (pipelining ? 1 : 0);
    result = 31 * result + (tryUseCompression ? 1 : 0);
    result = 31 * result + maxWebsocketFrameSize;
    result = 31 * result + defaultHost.hashCode();
    result = 31 * result + defaultPort;
    return result;
  }
}




File: src/main/java/io/vertx/core/http/HttpServerOptions.java
/*
 * Copyright (c) 2011-2014 The original author or authors
 * ------------------------------------------------------
 * All rights reserved. This program and the accompanying materials
 * are made available under the terms of the Eclipse Public License v1.0
 * and Apache License v2.0 which accompanies this distribution.
 *
 *     The Eclipse Public License is available at
 *     http://www.eclipse.org/legal/epl-v10.html
 *
 *     The Apache License v2.0 is available at
 *     http://www.opensource.org/licenses/apache2.0.php
 *
 * You may elect to redistribute this code under either of these licenses.
 */

package io.vertx.core.http;

import io.vertx.codegen.annotations.DataObject;
import io.vertx.core.buffer.Buffer;
import io.vertx.core.json.JsonObject;
import io.vertx.core.net.*;

/**
 * Represents options used by an {@link io.vertx.core.http.HttpServer} instance
 *
 * @author <a href="http://tfox.org">Tim Fox</a>
 */
@DataObject
public class HttpServerOptions extends NetServerOptions {

  /**
   * Default port the server will listen on = 80
   */
  public static final int DEFAULT_PORT = 80;  // Default port is 80 for HTTP not 0 from HttpServerOptions

  /**
   * Default value of whether compression is supported = false
   */
  public static final boolean DEFAULT_COMPRESSION_SUPPORTED = false;

  /**
   * Default max websocket framesize = 65536
   */
  public static final int DEFAULT_MAX_WEBSOCKET_FRAME_SIZE = 65536;

  /**
   * Default value of whether 100-Continue should be handled automatically
   */
  public static final boolean DEFAULT_HANDLE_100_CONTINE_AUTOMATICALLY = false;

  private boolean compressionSupported;
  private int maxWebsocketFrameSize;
  private String websocketSubProtocols;
  private boolean handle100ContinueAutomatically;

  /**
   * Default constructor
   */
  public HttpServerOptions() {
    super();
    setPort(DEFAULT_PORT); // We override the default for port
    compressionSupported = DEFAULT_COMPRESSION_SUPPORTED;
    maxWebsocketFrameSize = DEFAULT_MAX_WEBSOCKET_FRAME_SIZE;
    handle100ContinueAutomatically = DEFAULT_HANDLE_100_CONTINE_AUTOMATICALLY;
  }

  /**
   * Copy constructor
   *
   * @param other  the options to copy
   */
  public HttpServerOptions(HttpServerOptions other) {
    super(other);
    this.compressionSupported = other.isCompressionSupported();
    this.maxWebsocketFrameSize = other.getMaxWebsocketFrameSize();
    this.websocketSubProtocols = other.getWebsocketSubProtocols();
    this.handle100ContinueAutomatically = other.handle100ContinueAutomatically;
  }

  /**
   * Create an options from JSON
   *
   * @param json  the JSON
   */
  public HttpServerOptions(JsonObject json) {
    super(json);
    this.compressionSupported = json.getBoolean("compressionSupported", DEFAULT_COMPRESSION_SUPPORTED);
    this.maxWebsocketFrameSize = json.getInteger("maxWebsocketFrameSize", DEFAULT_MAX_WEBSOCKET_FRAME_SIZE);
    this.websocketSubProtocols = json.getString("websocketSubProtocols", null);
    this.handle100ContinueAutomatically = json.getBoolean("handle100ContinueAutomatically",
      DEFAULT_HANDLE_100_CONTINE_AUTOMATICALLY);
    setPort(json.getInteger("port", DEFAULT_PORT));
  }

  @Override
  public HttpServerOptions setSendBufferSize(int sendBufferSize) {
    super.setSendBufferSize(sendBufferSize);
    return this;
  }

  @Override
  public HttpServerOptions setReceiveBufferSize(int receiveBufferSize) {
    super.setReceiveBufferSize(receiveBufferSize);
    return this;
  }

  @Override
  public HttpServerOptions setReuseAddress(boolean reuseAddress) {
    super.setReuseAddress(reuseAddress);
    return this;
  }

  @Override
  public HttpServerOptions setTrafficClass(int trafficClass) {
    super.setTrafficClass(trafficClass);
    return this;
  }

  @Override
  public HttpServerOptions setTcpNoDelay(boolean tcpNoDelay) {
    super.setTcpNoDelay(tcpNoDelay);
    return this;
  }

  @Override
  public HttpServerOptions setTcpKeepAlive(boolean tcpKeepAlive) {
    super.setTcpKeepAlive(tcpKeepAlive);
    return this;
  }

  @Override
  public HttpServerOptions setSoLinger(int soLinger) {
    super.setSoLinger(soLinger);
    return this;
  }

  @Override
  public HttpServerOptions setUsePooledBuffers(boolean usePooledBuffers) {
    super.setUsePooledBuffers(usePooledBuffers);
    return this;
  }

  @Override
  public HttpServerOptions setIdleTimeout(int idleTimeout) {
    super.setIdleTimeout(idleTimeout);
    return this;
  }

  @Override
  public HttpServerOptions setSsl(boolean ssl) {
    super.setSsl(ssl);
    return this;
  }

  @Override
  public HttpServerOptions setKeyStoreOptions(JksOptions options) {
    super.setKeyStoreOptions(options);
    return this;
  }

  @Override
  public HttpServerOptions setPfxKeyCertOptions(PfxOptions options) {
    return (HttpServerOptions) super.setPfxKeyCertOptions(options);
  }

  @Override
  public HttpServerOptions setPemKeyCertOptions(PemKeyCertOptions options) {
    return (HttpServerOptions) super.setPemKeyCertOptions(options);
  }

  @Override
  public HttpServerOptions setTrustStoreOptions(JksOptions options) {
    super.setTrustStoreOptions(options);
    return this;
  }

  @Override
  public HttpServerOptions setPemTrustOptions(PemTrustOptions options) {
    return (HttpServerOptions) super.setPemTrustOptions(options);
  }

  @Override
  public HttpServerOptions setPfxTrustOptions(PfxOptions options) {
    return (HttpServerOptions) super.setPfxTrustOptions(options);
  }

  @Override
  public HttpServerOptions addEnabledCipherSuite(String suite) {
    super.addEnabledCipherSuite(suite);
    return this;
  }

  @Override
  public HttpServerOptions addCrlPath(String crlPath) throws NullPointerException {
    return (HttpServerOptions) super.addCrlPath(crlPath);
  }

  @Override
  public HttpServerOptions addCrlValue(Buffer crlValue) throws NullPointerException {
    return (HttpServerOptions) super.addCrlValue(crlValue);
  }

  @Override
  public HttpServerOptions setAcceptBacklog(int acceptBacklog) {
    super.setAcceptBacklog(acceptBacklog);
    return this;
  }

  public HttpServerOptions setPort(int port) {
    super.setPort(port);
    return this;
  }

  @Override
  public HttpServerOptions setHost(String host) {
    super.setHost(host);
    return this;
  }

  /**
   * @return true if the server supports compression
   */
  public boolean isCompressionSupported() {
    return compressionSupported;
  }

  /**
   * Set whether the server supports compression
   *
   * @param compressionSupported true if compression supported
   * @return a reference to this, so the API can be used fluently
   */
  public HttpServerOptions setCompressionSupported(boolean compressionSupported) {
    this.compressionSupported = compressionSupported;
    return this;
  }

  /**
   * @return  the maximum websocket framesize
   */
  public int getMaxWebsocketFrameSize() {
    return maxWebsocketFrameSize;
  }

  /**
   * Set the maximum websocket frames size
   *
   * @param maxWebsocketFrameSize  the maximum frame size in bytes.
   * @return a reference to this, so the API can be used fluently
   */
  public HttpServerOptions setMaxWebsocketFrameSize(int maxWebsocketFrameSize) {
    this.maxWebsocketFrameSize = maxWebsocketFrameSize;
    return this;
  }

  /**
   * Set the websocket subprotocols supported by the server.
   *
   * @param subProtocols  comma separated list of subprotocols
   * @return a reference to this, so the API can be used fluently
   */
  public HttpServerOptions setWebsocketSubProtocol(String subProtocols) {
    websocketSubProtocols = subProtocols;
    return this;
  }

  /**
   * @return Get the websocket subprotocols
   */
  public String getWebsocketSubProtocols() {
    return websocketSubProtocols;
  }
  
  @Override
  public HttpServerOptions setClientAuthRequired(boolean clientAuthRequired) {
    super.setClientAuthRequired(clientAuthRequired);
    return this;
  }

  /**
   * @return whether 100 Continue should be handled automatically
   */
  public boolean isHandle100ContinueAutomatically() {
    return handle100ContinueAutomatically;
  }

  /**
   * Set whether 100 Continue should be handled automatically
   * @param handle100ContinueAutomatically true if it should be handled automatically
   * @return a reference to this, so the API can be used fluently
   */
  public HttpServerOptions setHandle100ContinueAutomatically(boolean handle100ContinueAutomatically) {
    this.handle100ContinueAutomatically = handle100ContinueAutomatically;
    return this;
  }

  @Override
  public boolean equals(Object o) {
    if (this == o) return true;
    if (o == null || getClass() != o.getClass()) return false;
    if (!super.equals(o)) return false;

    HttpServerOptions that = (HttpServerOptions) o;

    if (compressionSupported != that.compressionSupported) return false;
    if (maxWebsocketFrameSize != that.maxWebsocketFrameSize) return false;
    if (handle100ContinueAutomatically != that.handle100ContinueAutomatically) return false;
    return !(websocketSubProtocols != null ? !websocketSubProtocols.equals(that.websocketSubProtocols) : that.websocketSubProtocols != null);

  }

  @Override
  public int hashCode() {
    int result = super.hashCode();
    result = 31 * result + (compressionSupported ? 1 : 0);
    result = 31 * result + maxWebsocketFrameSize;
    result = 31 * result + (websocketSubProtocols != null ? websocketSubProtocols.hashCode() : 0);
    result = 31 * result + (handle100ContinueAutomatically ? 1 : 0);
    return result;
  }
}


File: src/main/java/io/vertx/core/json/Json.java
/*
 * Copyright (c) 2011-2014 The original author or authors
 * ------------------------------------------------------
 * All rights reserved. This program and the accompanying materials
 * are made available under the terms of the Eclipse Public License v1.0
 * and Apache License v2.0 which accompanies this distribution.
 *
 *     The Eclipse Public License is available at
 *     http://www.eclipse.org/legal/epl-v10.html
 *
 *     The Apache License v2.0 is available at
 *     http://www.opensource.org/licenses/apache2.0.php
 *
 * You may elect to redistribute this code under either of these licenses.
 */

package io.vertx.core.json;

import com.fasterxml.jackson.core.JsonGenerator;
import com.fasterxml.jackson.core.JsonParser;
import com.fasterxml.jackson.databind.JsonSerializer;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.fasterxml.jackson.databind.SerializationFeature;
import com.fasterxml.jackson.databind.SerializerProvider;
import com.fasterxml.jackson.databind.module.SimpleModule;

import java.io.IOException;
import java.math.BigDecimal;
import java.util.Base64;
import java.util.List;
import java.util.Map;

/**
 * @author <a href="http://tfox.org">Tim Fox</a>
 */
public class Json {

  public static ObjectMapper mapper = new ObjectMapper();
  public static ObjectMapper prettyMapper = new ObjectMapper();

  static {
    // Non-standard JSON but we allow C style comments in our JSON
    mapper.configure(JsonParser.Feature.ALLOW_COMMENTS, true);

    prettyMapper.configure(JsonParser.Feature.ALLOW_COMMENTS, true);
    prettyMapper.configure(SerializationFeature.INDENT_OUTPUT, true);

    SimpleModule module = new SimpleModule();
    module.addSerializer(JsonObject.class, new JsonObjectSerializer());
    module.addSerializer(JsonArray.class, new JsonArraySerializer());
    mapper.registerModule(module);
    prettyMapper.registerModule(module);
  }

  public static String encode(Object obj) throws EncodeException {
    try {
      return mapper.writeValueAsString(obj);
    } catch (Exception e) {
      throw new EncodeException("Failed to encode as JSON: " + e.getMessage());
    }
  }

  public static String encodePrettily(Object obj) throws EncodeException {
    try {
      return prettyMapper.writeValueAsString(obj);
    } catch (Exception e) {
      throw new EncodeException("Failed to encode as JSON: " + e.getMessage());
    }
  }

  public static <T> T decodeValue(String str, Class<T> clazz) throws DecodeException {
    try {
      return mapper.readValue(str, clazz);
    }
    catch (Exception e) {
      throw new DecodeException("Failed to decode:" + e.getMessage());
    }
  }

  @SuppressWarnings("unchecked")
  static Object checkAndCopy(Object val, boolean copy) {
    if (val == null) {
      // OK
    } else if (val instanceof Number && !(val instanceof BigDecimal)) {
      // OK
    } else if (val instanceof Boolean) {
      // OK
    } else if (val instanceof String) {
      // OK
    } else if (val instanceof CharSequence) {
      val = val.toString();
    } else if (val instanceof JsonObject) {
      if (copy) {
        val = ((JsonObject) val).copy();
      }
    } else if (val instanceof JsonArray) {
      if (copy) {
        val = ((JsonArray) val).copy();
      }
    } else if (val instanceof Map) {
      if (copy) {
        val = (new JsonObject((Map)val)).copy();
      } else {
        val = new JsonObject((Map)val);
      }
    } else if (val instanceof List) {
      if (copy) {
        val = (new JsonArray((List)val)).copy();
      } else {
        val = new JsonArray((List)val);
      }
    } else if (val instanceof byte[]) {
      val = Base64.getEncoder().encodeToString((byte[])val);
    } else {
      throw new IllegalStateException("Illegal type in JsonObject: " + val.getClass());
    }
    return val;
  }

  private static class JsonObjectSerializer extends JsonSerializer<JsonObject> {
    @Override
    public void serialize(JsonObject value, JsonGenerator jgen, SerializerProvider provider) throws IOException {
      jgen.writeObject(value.getMap());
    }
  }

  private static class JsonArraySerializer extends JsonSerializer<JsonArray> {
    @Override
    public void serialize(JsonArray value, JsonGenerator jgen, SerializerProvider provider) throws IOException {
      jgen.writeObject(value.getList());
    }
  }
}


File: src/main/java/io/vertx/core/metrics/MetricsOptions.java
/*
 * Copyright (c) 2011-2013 The original author or authors
 *  ------------------------------------------------------
 *  All rights reserved. This program and the accompanying materials
 *  are made available under the terms of the Eclipse Public License v1.0
 *  and Apache License v2.0 which accompanies this distribution.
 *
 *      The Eclipse Public License is available at
 *      http://www.eclipse.org/legal/epl-v10.html
 *
 *      The Apache License v2.0 is available at
 *      http://www.opensource.org/licenses/apache2.0.php
 *
 *  You may elect to redistribute this code under either of these licenses.
 */

package io.vertx.core.metrics;

import io.vertx.codegen.annotations.DataObject;
import io.vertx.core.json.JsonObject;

/**
 * Vert.x metrics base configuration, this class can be extended by provider implementations to configure
 * those specific implementations.
 *
 * @author <a href="mailto:julien@julienviet.com">Julien Viet</a>
 */
@DataObject
public class MetricsOptions {

  /**
   * The default value of metrics enabled false
   */
  public static final boolean DEFAULT_METRICS_ENABLED = false;

  private boolean enabled;
  private JsonObject json; // Keep a copy of the original json, so we don't lose info when building options subclasses

  /**
   * Default constructor
   */
  public MetricsOptions() {
    enabled = DEFAULT_METRICS_ENABLED;
  }

  /**
   * Copy constructor
   *
   * @param other The other {@link MetricsOptions} to copy when creating this
   */
  public MetricsOptions(MetricsOptions other) {
    enabled = other.isEnabled();
  }

  /**
   * Create an instance from a {@link io.vertx.core.json.JsonObject}
   *
   * @param json the JsonObject to create it from
   */
  public MetricsOptions(JsonObject json) {
    this.enabled = json.getBoolean("enabled", DEFAULT_METRICS_ENABLED);
    this.json = json.copy();
  }

  /**
   * Will metrics be enabled on the Vert.x instance?
   *
   * @return true if enabled, false if not.
   */
  public boolean isEnabled() {
    return enabled;
  }

  /**
   * Set whether metrics will be enabled on the Vert.x instance.
   *
   * @param enable true if metrics enabled, or false if not.
   * @return a reference to this, so the API can be used fluently
   */
  public MetricsOptions setEnabled(boolean enable) {
    this.enabled = enable;
    return this;
  }

  public JsonObject toJson() {
    return json != null ? json.copy() : new JsonObject();
  }
}


File: src/main/java/io/vertx/core/net/ClientOptionsBase.java
/*
 * Copyright (c) 2011-2014 The original author or authors
 * ------------------------------------------------------
 * All rights reserved. This program and the accompanying materials
 * are made available under the terms of the Eclipse Public License v1.0
 * and Apache License v2.0 which accompanies this distribution.
 *
 *     The Eclipse Public License is available at
 *     http://www.eclipse.org/legal/epl-v10.html
 *
 *     The Apache License v2.0 is available at
 *     http://www.opensource.org/licenses/apache2.0.php
 *
 * You may elect to redistribute this code under either of these licenses.
 */

package io.vertx.core.net;

import io.vertx.core.json.JsonObject;

/**
 * Base class for Client options
 *
 * @author <a href="http://tfox.org">Tim Fox</a>
 */
public abstract class ClientOptionsBase extends TCPSSLOptions {

  /**
   * The default value of connect timeout = 60000 ms
   */
  public static final int DEFAULT_CONNECT_TIMEOUT = 60000;

  /**
   * The default value of whether all servers (SSL/TLS) should be trusted = false
   */
  public static final boolean DEFAULT_TRUST_ALL = false;

  private int connectTimeout;
  private boolean trustAll;

  /**
   * Default constructor
   */
  public ClientOptionsBase() {
    super();
    this.connectTimeout = DEFAULT_CONNECT_TIMEOUT;
    this.trustAll = DEFAULT_TRUST_ALL;
  }

  /**
   * Copy constructor
   *
   * @param other  the options to copy
   */
  public ClientOptionsBase(ClientOptionsBase other) {
    super(other);
    this.connectTimeout = other.getConnectTimeout();
    this.trustAll = other.isTrustAll();
  }

  /**
   * Create options from some JSON
   *
   * @param json  the JSON
   */
  public ClientOptionsBase(JsonObject json) {
    super(json);
    this.connectTimeout = json.getInteger("connectTimeout", DEFAULT_CONNECT_TIMEOUT);
    this.trustAll = json.getBoolean("trustAll", DEFAULT_TRUST_ALL);
  }

  /**
   *
   * @return true if all server certificates should be trusted
   */
  public boolean isTrustAll() {
    return trustAll;
  }

  /**
   * Set whether all server certificates should be trusted
   *
   * @param trustAll true if all should be trusted
   * @return a reference to this, so the API can be used fluently
   */
  public ClientOptionsBase setTrustAll(boolean trustAll) {
    this.trustAll = trustAll;
    return this;
  }

  /**
   * @return the value of connect timeout
   */
  public int getConnectTimeout() {
    return connectTimeout;
  }

  /**
   * Set the connect timeout
   *
   * @param connectTimeout  connect timeout, in ms
   * @return a reference to this, so the API can be used fluently
   */
  public ClientOptionsBase setConnectTimeout(int connectTimeout) {
    if (connectTimeout < 0) {
      throw new IllegalArgumentException("connectTimeout must be >= 0");
    }
    this.connectTimeout = connectTimeout;
    return this;
  }

  @Override
  public boolean equals(Object o) {
    if (this == o) return true;
    if (!(o instanceof ClientOptionsBase)) return false;
    if (!super.equals(o)) return false;

    ClientOptionsBase that = (ClientOptionsBase) o;

    if (connectTimeout != that.connectTimeout) return false;
    if (trustAll != that.trustAll) return false;

    return true;
  }

  @Override
  public int hashCode() {
    int result = super.hashCode();
    result = 31 * result + connectTimeout;
    result = 31 * result + (trustAll ? 1 : 0);
    return result;
  }
}


File: src/main/java/io/vertx/core/net/JksOptions.java
/*
 * Copyright (c) 2011-2014 The original author or authors
 * ------------------------------------------------------
 * All rights reserved. This program and the accompanying materials
 * are made available under the terms of the Eclipse Public License v1.0
 * and Apache License v2.0 which accompanies this distribution.
 *
 *     The Eclipse Public License is available at
 *     http://www.eclipse.org/legal/epl-v10.html
 *
 *     The Apache License v2.0 is available at
 *     http://www.opensource.org/licenses/apache2.0.php
 *
 * You may elect to redistribute this code under either of these licenses.
 */

package io.vertx.core.net;

import io.vertx.codegen.annotations.DataObject;
import io.vertx.core.buffer.Buffer;
import io.vertx.core.json.JsonObject;

/**
 * Key or trust store options configuring private key and/or certificates based on Java Keystore files.
 * <p>
 * When used as a key store, it should point to a store containing a private key and its certificate.
 * When used as a trust store, it should point to a store containing a list of trusted certificates.
 * <p>
 * The store can either be loaded by Vert.x from the filesystem:
 * <p>
 * <pre>
 * HttpServerOptions options = HttpServerOptions.httpServerOptions();
 * options.setKeyStore(JKSOptions.options().setPath("/mykeystore.jks").setPassword("foo"));
 * </pre>
 *
 * Or directly provided as a buffer:
 * <p>
 *
 * <pre>
 * Buffer store = vertx.fileSystem().readFileSync("/mykeystore.jks");
 * options.setKeyStore(JKSOptions.options().setValue(store).setPassword("foo"));
 * </pre>
 *
 * @author <a href="mailto:julien@julienviet.com">Julien Viet</a>
 * @author <a href="http://tfox.org">Tim Fox</a>
 */
@DataObject
public class JksOptions implements KeyCertOptions, TrustOptions, Cloneable {

  private String password;
  private String path;
  private Buffer value;

  /**
   * Default constructor
   */
  public JksOptions() {
    super();
  }

  /**
   * Copy constructor
   *
   * @param other  the options to copy
   */
  public JksOptions(JksOptions other) {
    super();
    this.password = other.getPassword();
    this.path = other.getPath();
    this.value = other.getValue();
  }

  /**
   * Create options from JSON
   *
   * @param json  the JSON
   */
  public JksOptions(JsonObject json) {
    super();
    this.password = json.getString("password");
    this.path = json.getString("path");
    byte[] value = json.getBinary("value");
    this.value = value != null ? Buffer.buffer(value) : null;
  }

  /**
   * @return the password for the key store
   */
  public String getPassword() {
    return password;
  }

  /**
   * Set the password for the key store
   *
   * @param password  the password
   * @return a reference to this, so the API can be used fluently
   */
  public JksOptions setPassword(String password) {
    this.password = password;
    return this;
  }

  /**
   * Get the path to the ksy store
   *
   * @return the path
   */
  public String getPath() {
    return path;
  }

  /**
   * Set the path to the key store
   *
   * @param path  the path
   * @return a reference to this, so the API can be used fluently
   */
  public JksOptions setPath(String path) {
    this.path = path;
    return this;
  }

  /**
   * Get the key store as a buffer
   *
   * @return  the key store as a buffer
   */
  public Buffer getValue() {
    return value;
  }

  /**
   * Set the key store as a buffer
   *
   * @param value  the key store as a buffer
   * @return a reference to this, so the API can be used fluently
   */
  public JksOptions setValue(Buffer value) {
    this.value = value;
    return this;
  }

  @Override
  public boolean equals(Object o) {
    if (this == o) {
      return true;
    }
    if (!(o instanceof JksOptions)) {
      return false;
    }

    JksOptions that = (JksOptions) o;

    if (password != null ? !password.equals(that.password) : that.password != null) {
      return false;
    }
    if (path != null ? !path.equals(that.path) : that.path != null) {
      return false;
    }
    if (value != null ? !value.equals(that.value) : that.value != null) {
      return false;
    }

    return true;
  }

  @Override
  public int hashCode() {
    int result = 1;
    result += 31 * result + (password != null ? password.hashCode() : 0);
    result += 31 * result + (path != null ? path.hashCode() : 0);
    result += 31 * result + (value != null ? value.hashCode() : 0);

    return result;
  }

  @Override
  public JksOptions clone() {
    return new JksOptions(this);
  }
}


File: src/main/java/io/vertx/core/net/NetClientOptions.java
/*
 * Copyright (c) 2011-2014 The original author or authors
 * ------------------------------------------------------
 * All rights reserved. This program and the accompanying materials
 * are made available under the terms of the Eclipse Public License v1.0
 * and Apache License v2.0 which accompanies this distribution.
 *
 *     The Eclipse Public License is available at
 *     http://www.eclipse.org/legal/epl-v10.html
 *
 *     The Apache License v2.0 is available at
 *     http://www.opensource.org/licenses/apache2.0.php
 *
 * You may elect to redistribute this code under either of these licenses.
 */

package io.vertx.core.net;

import io.vertx.codegen.annotations.DataObject;
import io.vertx.core.buffer.Buffer;
import io.vertx.core.json.JsonObject;

/**
 * Options for configuring a {@link io.vertx.core.net.NetClient}.
 *
 * @author <a href="http://tfox.org">Tim Fox</a>
 */
@DataObject
public class NetClientOptions extends ClientOptionsBase {

  /**
   * The default value for reconnect attempts = 0
   */
  public static final int DEFAULT_RECONNECT_ATTEMPTS = 0;

  /**
   * The default value for reconnect interval = 1000 ms
   */
  public static final long DEFAULT_RECONNECT_INTERVAL = 1000;

  private int reconnectAttempts;
  private long reconnectInterval;

  /**
   * The default constructor
   */
  public NetClientOptions() {
    super();
    this.reconnectAttempts = DEFAULT_RECONNECT_ATTEMPTS;
    this.reconnectInterval = DEFAULT_RECONNECT_INTERVAL;
  }

  /**
   * Copy constructor
   *
   * @param other  the options to copy
   */
  public NetClientOptions(NetClientOptions other) {
    super(other);
    this.reconnectAttempts = other.getReconnectAttempts();
    this.reconnectInterval = other.getReconnectInterval();
  }

  /**
   * Create options from JSON
   *
   * @param json  the JSON
   */
  public NetClientOptions(JsonObject json) {
    super(json);
    this.reconnectAttempts = json.getInteger("reconnectAttempts", DEFAULT_RECONNECT_ATTEMPTS);
    this.reconnectInterval = json.getLong("reconnectInterval", DEFAULT_RECONNECT_INTERVAL);
  }

  @Override
  public NetClientOptions setSendBufferSize(int sendBufferSize) {
    super.setSendBufferSize(sendBufferSize);
    return this;
  }

  @Override
  public NetClientOptions setReceiveBufferSize(int receiveBufferSize) {
    super.setReceiveBufferSize(receiveBufferSize);
    return this;
  }

  @Override
  public NetClientOptions setReuseAddress(boolean reuseAddress) {
    super.setReuseAddress(reuseAddress);
    return this;
  }

  @Override
  public NetClientOptions setTrafficClass(int trafficClass) {
    super.setTrafficClass(trafficClass);
    return this;
  }

  @Override
  public NetClientOptions setTcpNoDelay(boolean tcpNoDelay) {
    super.setTcpNoDelay(tcpNoDelay);
    return this;
  }

  @Override
  public NetClientOptions setTcpKeepAlive(boolean tcpKeepAlive) {
    super.setTcpKeepAlive(tcpKeepAlive);
    return this;
  }

  @Override
  public NetClientOptions setSoLinger(int soLinger) {
    super.setSoLinger(soLinger);
    return this;
  }

  @Override
  public NetClientOptions setUsePooledBuffers(boolean usePooledBuffers) {
    super.setUsePooledBuffers(usePooledBuffers);
    return this;
  }

  @Override
  public NetClientOptions setIdleTimeout(int idleTimeout) {
    super.setIdleTimeout(idleTimeout);
    return this;
  }

  @Override
  public NetClientOptions setSsl(boolean ssl) {
    super.setSsl(ssl);
    return this;
  }

  @Override
  public NetClientOptions setKeyStoreOptions(JksOptions options) {
    super.setKeyStoreOptions(options);
    return this;
  }

  @Override
  public NetClientOptions setPfxKeyCertOptions(PfxOptions options) {
    return (NetClientOptions) super.setPfxKeyCertOptions(options);
  }

  @Override
  public NetClientOptions setPemKeyCertOptions(PemKeyCertOptions options) {
    return (NetClientOptions) super.setPemKeyCertOptions(options);
  }

  @Override
  public NetClientOptions setTrustStoreOptions(JksOptions options) {
    super.setTrustStoreOptions(options);
    return this;
  }

  @Override
  public NetClientOptions setPemTrustOptions(PemTrustOptions options) {
    return (NetClientOptions) super.setPemTrustOptions(options);
  }

  @Override
  public NetClientOptions setPfxTrustOptions(PfxOptions options) {
    return (NetClientOptions) super.setPfxTrustOptions(options);
  }

  @Override
  public NetClientOptions addEnabledCipherSuite(String suite) {
    super.addEnabledCipherSuite(suite);
    return this;
  }

  @Override
  public NetClientOptions addCrlPath(String crlPath) throws NullPointerException {
    return (NetClientOptions) super.addCrlPath(crlPath);
  }

  @Override
  public NetClientOptions addCrlValue(Buffer crlValue) throws NullPointerException {
    return (NetClientOptions) super.addCrlValue(crlValue);
  }

  @Override
  public NetClientOptions setTrustAll(boolean trustAll) {
    super.setTrustAll(trustAll);
    return this;
  }

  @Override
  public NetClientOptions setConnectTimeout(int connectTimeout) {
    super.setConnectTimeout(connectTimeout);
    return this;
  }

  /**
   * Set the value of reconnect attempts
   *
   * @param attempts  the maximum number of reconnect attempts
   * @return a reference to this, so the API can be used fluently
   */
  public NetClientOptions setReconnectAttempts(int attempts) {
    if (attempts < -1) {
      throw new IllegalArgumentException("reconnect attempts must be >= -1");
    }
    this.reconnectAttempts = attempts;
    return this;
  }

  /**
   * @return  the value of reconnect attempts
   */
  public int getReconnectAttempts() {
    return reconnectAttempts;
  }

  /**
   * Set the reconnect interval
   *
   * @param interval  the reconnect interval in ms
   * @return a reference to this, so the API can be used fluently
   */
  public NetClientOptions setReconnectInterval(long interval) {
    if (interval < 1) {
      throw new IllegalArgumentException("reconnect interval nust be >= 1");
    }
    this.reconnectInterval = interval;
    return this;
  }

  /**
   * @return  the value of reconnect interval
   */
  public long getReconnectInterval() {
    return reconnectInterval;
  }

  @Override
  public boolean equals(Object o) {
    if (this == o) return true;
    if (!(o instanceof NetClientOptions)) return false;
    if (!super.equals(o)) return false;

    NetClientOptions that = (NetClientOptions) o;

    if (reconnectAttempts != that.reconnectAttempts) return false;
    if (reconnectInterval != that.reconnectInterval) return false;

    return true;
  }

  @Override
  public int hashCode() {
    int result = super.hashCode();
    result = 31 * result + reconnectAttempts;
    result = 31 * result + (int) (reconnectInterval ^ (reconnectInterval >>> 32));
    return result;
  }
}


File: src/main/java/io/vertx/core/net/NetServerOptions.java
/*
 * Copyright (c) 2011-2014 The original author or authors
 * ------------------------------------------------------
 * All rights reserved. This program and the accompanying materials
 * are made available under the terms of the Eclipse Public License v1.0
 * and Apache License v2.0 which accompanies this distribution.
 *
 *     The Eclipse Public License is available at
 *     http://www.eclipse.org/legal/epl-v10.html
 *
 *     The Apache License v2.0 is available at
 *     http://www.opensource.org/licenses/apache2.0.php
 *
 * You may elect to redistribute this code under either of these licenses.
 */

package io.vertx.core.net;

import io.vertx.codegen.annotations.DataObject;
import io.vertx.core.buffer.Buffer;
import io.vertx.core.json.JsonObject;

/**
 * Options for configuring a {@link io.vertx.core.net.NetServer}.
 *
 * @author <a href="http://tfox.org">Tim Fox</a>
 */
@DataObject
public class NetServerOptions extends TCPSSLOptions {

  // Server specific HTTP stuff

  /**
   * The default port to listen on = 0 (meaning a random ephemeral free port will be chosen)
   */
  public static final int DEFAULT_PORT = 0;

  /**
   * The default host to listen on = "0.0.0.0" (meaning listen on all available interfaces).
   */
  public static final String DEFAULT_HOST = "0.0.0.0";

  /**
   * The default accept backlog = 1024
   */
  public static final int DEFAULT_ACCEPT_BACKLOG = 1024;

  /**
   * Default value of whether client auth is required (SSL/TLS) = false
   */
  public static final boolean DEFAULT_CLIENT_AUTH_REQUIRED = false;

  private int port;
  private String host;
  private int acceptBacklog;
  private boolean clientAuthRequired;

  /**
   * Default constructor
   */
  public NetServerOptions() {
    super();
    this.port = DEFAULT_PORT;
    this.host = DEFAULT_HOST;
    this.acceptBacklog = DEFAULT_ACCEPT_BACKLOG;
    this.clientAuthRequired = DEFAULT_CLIENT_AUTH_REQUIRED;
  }

  /**
   * Copy constructor
   *
   * @param other  the options to copy
   */
  public NetServerOptions(NetServerOptions other) {
    super(other);
    this.port = other.getPort();
    this.host = other.getHost();
    this.acceptBacklog = other.getAcceptBacklog();
    this.clientAuthRequired = other.isClientAuthRequired();
  }

  /**
   * Create some options from JSON
   *
   * @param json  the JSON
   */
  public NetServerOptions(JsonObject json) {
    super(json);
    this.port = json.getInteger("port", DEFAULT_PORT);
    this.host = json.getString("host", DEFAULT_HOST);
    this.acceptBacklog = json.getInteger("acceptBacklog", DEFAULT_ACCEPT_BACKLOG);
    this.clientAuthRequired = json.getBoolean("clientAuthRequired", DEFAULT_CLIENT_AUTH_REQUIRED);
  }

  @Override
  public NetServerOptions setSendBufferSize(int sendBufferSize) {
    super.setSendBufferSize(sendBufferSize);
    return this;
  }

  @Override
  public NetServerOptions setReceiveBufferSize(int receiveBufferSize) {
    super.setReceiveBufferSize(receiveBufferSize);
    return this;
  }

  @Override
  public NetServerOptions setReuseAddress(boolean reuseAddress) {
    super.setReuseAddress(reuseAddress);
    return this;
  }

  @Override
  public NetServerOptions setTrafficClass(int trafficClass) {
    super.setTrafficClass(trafficClass);
    return this;
  }

  @Override
  public NetServerOptions setTcpNoDelay(boolean tcpNoDelay) {
    super.setTcpNoDelay(tcpNoDelay);
    return this;
  }

  @Override
  public NetServerOptions setTcpKeepAlive(boolean tcpKeepAlive) {
    super.setTcpKeepAlive(tcpKeepAlive);
    return this;
  }

  @Override
  public NetServerOptions setSoLinger(int soLinger) {
    super.setSoLinger(soLinger);
    return this;
  }

  @Override
  public NetServerOptions setUsePooledBuffers(boolean usePooledBuffers) {
    super.setUsePooledBuffers(usePooledBuffers);
    return this;
  }

  @Override
  public NetServerOptions setIdleTimeout(int idleTimeout) {
    super.setIdleTimeout(idleTimeout);
    return this;
  }

  @Override
  public NetServerOptions setSsl(boolean ssl) {
    super.setSsl(ssl);
    return this;
  }

  @Override
  public NetServerOptions setKeyStoreOptions(JksOptions options) {
    super.setKeyStoreOptions(options);
    return this;
  }

  @Override
  public NetServerOptions setPfxKeyCertOptions(PfxOptions options) {
    return (NetServerOptions) super.setPfxKeyCertOptions(options);
  }

  @Override
  public NetServerOptions setPemKeyCertOptions(PemKeyCertOptions options) {
    return (NetServerOptions) super.setPemKeyCertOptions(options);
  }

  @Override
  public NetServerOptions setTrustStoreOptions(JksOptions options) {
    super.setTrustStoreOptions(options);
    return this;
  }

  @Override
  public NetServerOptions setPfxTrustOptions(PfxOptions options) {
    return (NetServerOptions) super.setPfxTrustOptions(options);
  }

  @Override
  public NetServerOptions setPemTrustOptions(PemTrustOptions options) {
    return (NetServerOptions) super.setPemTrustOptions(options);
  }

  @Override
  public NetServerOptions addEnabledCipherSuite(String suite) {
    super.addEnabledCipherSuite(suite);
    return this;
  }

  @Override
  public NetServerOptions addCrlPath(String crlPath) throws NullPointerException {
    return (NetServerOptions) super.addCrlPath(crlPath);
  }

  @Override
  public NetServerOptions addCrlValue(Buffer crlValue) throws NullPointerException {
    return (NetServerOptions) super.addCrlValue(crlValue);
  }

  /**
   * @return the value of accept backlog
   */
  public int getAcceptBacklog() {
    return acceptBacklog;
  }

  /**
   * Set the accept back log
   *
   * @param acceptBacklog accept backlog
   * @return a reference to this, so the API can be used fluently
   */
  public NetServerOptions setAcceptBacklog(int acceptBacklog) {
    this.acceptBacklog = acceptBacklog;
    return this;
  }

  /**
   *
   * @return the port
   */
  public int getPort() {
    return port;
  }

  /**
   * Set the port
   *
   * @param port  the port
   * @return a reference to this, so the API can be used fluently
   */
  public NetServerOptions setPort(int port) {
    if (port < 0 || port > 65535) {
      throw new IllegalArgumentException("port p must be in range 0 <= p <= 65535");
    }
    this.port = port;
    return this;
  }

  /**
   *
   * @return the host
   */
  public String getHost() {
    return host;
  }

  /**
   * Set the host
   * @param host  the host
   * @return a reference to this, so the API can be used fluently
   */
  public NetServerOptions setHost(String host) {
    this.host = host;
    return this;
  }

  /**
   *
   * @return true if client auth is required
   */
  public boolean isClientAuthRequired() {
    return clientAuthRequired;
  }

  /**
   * Set whether client auth is required
   *
   * @param clientAuthRequired  true if client auth is required
   * @return a reference to this, so the API can be used fluently
   */
  public NetServerOptions setClientAuthRequired(boolean clientAuthRequired) {
    this.clientAuthRequired = clientAuthRequired;
    return this;
  }

  @Override
  public boolean equals(Object o) {
    if (this == o) return true;
    if (!(o instanceof NetServerOptions)) return false;
    if (!super.equals(o)) return false;

    NetServerOptions that = (NetServerOptions) o;

    if (acceptBacklog != that.acceptBacklog) return false;
    if (clientAuthRequired != that.clientAuthRequired) return false;
    if (port != that.port) return false;
    if (host != null ? !host.equals(that.host) : that.host != null) return false;

    return true;
  }

  @Override
  public int hashCode() {
    int result = super.hashCode();
    result = 31 * result + port;
    result = 31 * result + (host != null ? host.hashCode() : 0);
    result = 31 * result + acceptBacklog;
    result = 31 * result + (clientAuthRequired ? 1 : 0);
    return result;
  }
}


File: src/main/java/io/vertx/core/net/NetworkOptions.java
/*
 * Copyright (c) 2011-2014 The original author or authors
 * ------------------------------------------------------
 * All rights reserved. This program and the accompanying materials
 * are made available under the terms of the Eclipse Public License v1.0
 * and Apache License v2.0 which accompanies this distribution.
 *
 *     The Eclipse Public License is available at
 *     http://www.eclipse.org/legal/epl-v10.html
 *
 *     The Apache License v2.0 is available at
 *     http://www.opensource.org/licenses/apache2.0.php
 *
 * You may elect to redistribute this code under either of these licenses.
 */

package io.vertx.core.net;

import io.vertx.core.impl.Arguments;
import io.vertx.core.json.JsonObject;
import io.vertx.core.net.impl.SocketDefaults;


/**
 * @author <a href="http://tfox.org">Tim Fox</a>
 */
public abstract class NetworkOptions {

  /**
   * The default value of TCP send buffer size
   */
  public static final int DEFAULT_SEND_BUFFER_SIZE = SocketDefaults.instance.getTcpSendBufferSize();

  /**
   * The default value of TCP receive buffer size
   */
  public static final int DEFAULT_RECEIVE_BUFFER_SIZE = SocketDefaults.instance.getTcpReceiveBufferSize();

  /**
   * The default value of traffic class
   */
  public static final int DEFAULT_TRAFFIC_CLASS = SocketDefaults.instance.getTrafficClass();

  /**
   * The default value of reuse address
   */
  public static final boolean DEFAULT_REUSE_ADDRESS = true;

  private int sendBufferSize;
  private int receiveBufferSize;
  private int trafficClass;
  private boolean reuseAddress;

  /**
   * Default constructor
   */
  public NetworkOptions() {
    sendBufferSize = DEFAULT_SEND_BUFFER_SIZE;
    receiveBufferSize = DEFAULT_RECEIVE_BUFFER_SIZE;
    reuseAddress = DEFAULT_REUSE_ADDRESS;
    trafficClass = DEFAULT_TRAFFIC_CLASS;
  }

  /**
   * Copy constructor
   *
   * @param other  the options to copy
   */
  public NetworkOptions(NetworkOptions other) {
    this.sendBufferSize = other.getSendBufferSize();
    this.receiveBufferSize = other.getReceiveBufferSize();
    this.reuseAddress = other.isReuseAddress();
    this.trafficClass = other.getTrafficClass();
  }

  /**
   * Constructor from JSON
   *
   * @param json  the JSON
   */
  public NetworkOptions(JsonObject json) {
    this.sendBufferSize = json.getInteger("sendBufferSize", DEFAULT_SEND_BUFFER_SIZE);
    this.receiveBufferSize = json.getInteger("receiveBufferSize", DEFAULT_RECEIVE_BUFFER_SIZE);
    this.reuseAddress = json.getBoolean("reuseAddress", DEFAULT_REUSE_ADDRESS);
    this.trafficClass = json.getInteger("trafficClass", DEFAULT_TRAFFIC_CLASS);
  }

  /**
   * Return the TCP send buffer size, in bytes.
   *
   * @return the send buffer size
   */
  public int getSendBufferSize() {
    return sendBufferSize;
  }

  /**
   * Set the TCP send buffer size
   *
   * @param sendBufferSize  the buffers size, in bytes
   * @return a reference to this, so the API can be used fluently
   */
  public NetworkOptions setSendBufferSize(int sendBufferSize) {
    Arguments.require(sendBufferSize > 0, "sendBufferSize must be > 0");
    this.sendBufferSize = sendBufferSize;
    return this;
  }

  /**
   * Return the TCP receive buffer size, in bytes
   *
   * @return the receive buffer size
   */
  public int getReceiveBufferSize() {
    return receiveBufferSize;
  }

  /**
   * Set the TCP receive buffer size
   *
   * @param receiveBufferSize  the buffers size, in bytes
   * @return a reference to this, so the API can be used fluently
   */
  public NetworkOptions setReceiveBufferSize(int receiveBufferSize) {
    Arguments.require(receiveBufferSize > 0, "receiveBufferSize must be > 0");
    this.receiveBufferSize = receiveBufferSize;
    return this;
  }

  /**
   * @return  the value of reuse address
   */
  public boolean isReuseAddress() {
    return reuseAddress;
  }

  /**
   * Set the value of reuse address
   * @param reuseAddress  the value of reuse address
   * @return a reference to this, so the API can be used fluently
   */
  public NetworkOptions setReuseAddress(boolean reuseAddress) {
    this.reuseAddress = reuseAddress;
    return this;
  }

  /**
   * @return  the value of traffic class
   */
  public int getTrafficClass() {
    return trafficClass;
  }

  /**
   * Set the value of traffic class
   *
   * @param trafficClass  the value of traffic class
   * @return a reference to this, so the API can be used fluently
   */
  public NetworkOptions setTrafficClass(int trafficClass) {
    Arguments.requireInRange(trafficClass, 0, 255, "trafficClass tc must be 0 <= tc <= 255");
    this.trafficClass = trafficClass;
    return this;
  }

  @Override
  public boolean equals(Object o) {
    if (this == o) return true;
    if (!(o instanceof NetworkOptions)) return false;

    NetworkOptions that = (NetworkOptions) o;

    if (receiveBufferSize != that.receiveBufferSize) return false;
    if (reuseAddress != that.reuseAddress) return false;
    if (sendBufferSize != that.sendBufferSize) return false;
    if (trafficClass != that.trafficClass) return false;

    return true;
  }

  @Override
  public int hashCode() {
    int result = sendBufferSize;
    result = 31 * result + receiveBufferSize;
    result = 31 * result + trafficClass;
    result = 31 * result + (reuseAddress ? 1 : 0);
    return result;
  }
}


File: src/main/java/io/vertx/core/net/PemKeyCertOptions.java
/*
 * Copyright (c) 2011-2014 The original author or authors
 * ------------------------------------------------------
 * All rights reserved. This program and the accompanying materials
 * are made available under the terms of the Eclipse Public License v1.0
 * and Apache License v2.0 which accompanies this distribution.
 *
 *     The Eclipse Public License is available at
 *     http://www.eclipse.org/legal/epl-v10.html
 *
 *     The Apache License v2.0 is available at
 *     http://www.opensource.org/licenses/apache2.0.php
 *
 * You may elect to redistribute this code under either of these licenses.
 */

package io.vertx.core.net;

import io.vertx.codegen.annotations.DataObject;
import io.vertx.core.buffer.Buffer;
import io.vertx.core.json.JsonObject;

/**
 * Key store options configuring a private key and its certificate based on
 * <i>Privacy-enhanced Electronic Email</i> (PEM) files.
 * <p>
 *
 * The key file must contain a <b>non encrypted</b> private key in <b>PKCS8</b> format wrapped in a PEM
 * block, for example:
 * <p>
 *
 * <pre>
 * -----BEGIN PRIVATE KEY-----
 * MIIEvgIBADANBgkqhkiG9w0BAQEFAASCBKgwggSkAgEAAoIBAQDV6zPk5WqLwS0a
 * ...
 * K5xBhtm1AhdnZjx5KfW3BecE
 * -----END PRIVATE KEY-----
 * </pre><p>
 *
 * The certificate file must contain an X.509 certificate wrapped in a PEM block, for example:
 * <p>
 *
 * <pre>
 * -----BEGIN CERTIFICATE-----
 * MIIDezCCAmOgAwIBAgIEZOI/3TANBgkqhkiG9w0BAQsFADBuMRAwDgYDVQQGEwdV
 * ...
 * +tmLSvYS39O2nqIzzAUfztkYnUlZmB0l/mKkVqbGJA==
 * -----END CERTIFICATE-----
 * </pre>
 *
 * The key and certificate can either be loaded by Vert.x from the filesystem:
 * <p>
 * <pre>
 * HttpServerOptions options = new HttpServerOptions();
 * options.setPemKeyCertOptions(new PemKeyCertOptions().setKeyPath("/mykey.pem").setCertPath("/mycert.pem"));
 * </pre>
 *
 * Or directly provided as a buffer:<p>
 *
 * <pre>
 * Buffer key = vertx.fileSystem().readFileSync("/mykey.pem");
 * Buffer cert = vertx.fileSystem().readFileSync("/mycert.pem");
 * options.setPemKeyCertOptions(new PemKeyCertOptions().setKeyValue(key).setCertValue(cert));
 * </pre>
 *
 * @author <a href="mailto:julien@julienviet.com">Julien Viet</a>
 * @author <a href="http://tfox.org">Tim Fox</a>
 */
@DataObject
public class PemKeyCertOptions implements KeyCertOptions, Cloneable {

  private String keyPath;
  private Buffer keyValue;
  private String certPath;
  private Buffer certValue;

  /**
   * Default constructor
   */
  public PemKeyCertOptions() {
    super();
  }

  /**
   * Copy constructor
   *
   * @param other  the options to copy
   */
  public PemKeyCertOptions(PemKeyCertOptions other) {
    super();
    this.keyPath = other.getKeyPath();
    this.keyValue = other.getKeyValue();
    this.certPath = other.getCertPath();
    this.certValue = other.getCertValue();
  }

  /**
   * Create options from JSON
   *
   * @param json  the JSON
   */
  public PemKeyCertOptions(JsonObject json) {
    super();
    keyPath = json.getString("keyPath");
    byte[] keyValue = json.getBinary("keyValue");
    this.keyValue = keyValue != null ? Buffer.buffer(keyValue) : null;
    certPath = json.getString("certPath");
    byte[] certValue = json.getBinary("certValue");
    this.certValue = certValue != null ? Buffer.buffer(certValue) : null;
  }

  /**
   * Get the path to the key file
   *
   * @return the path to the key file
   */
  public String getKeyPath() {
    return keyPath;
  }

  /**
   * Set the path to the key file
   *
   * @param keyPath  the path to the key file
   * @return a reference to this, so the API can be used fluently
   */
  public PemKeyCertOptions setKeyPath(String keyPath) {
    this.keyPath = keyPath;
    return this;
  }

  /**
   * Get the path to the certificate file
   *
   * @return  the path to the certificate file
   */
  public String getCertPath() {
    return certPath;
  }

  /**
   * Get the key as a buffer
   *
   * @return  key as a buffer
   */
  public Buffer getKeyValue() {
    return keyValue;
  }

  /**
   * Set the key a a buffer
   *
   * @param keyValue  key as a buffer
   * @return a reference to this, so the API can be used fluently
   */
  public PemKeyCertOptions setKeyValue(Buffer keyValue) {
    this.keyValue = keyValue;
    return this;
  }

  /**
   * Set the path to the certificate
   *
   * @param certPath  the path to the certificate
   * @return a reference to this, so the API can be used fluently
   */
  public PemKeyCertOptions setCertPath(String certPath) {
    this.certPath = certPath;
    return this;
  }

  /**
   * Get the certificate as a buffer
   *
   * @return  the certificate as a buffer
   */
  public Buffer getCertValue() {
    return certValue;
  }

  /**
   * Set the certificate as a buffer
   *
   * @param certValue  the certificate as a buffer
   * @return a reference to this, so the API can be used fluently
   */
  public PemKeyCertOptions setCertValue(Buffer certValue) {
    this.certValue = certValue;
    return this;
  }

  @Override
  public boolean equals(Object o) {
    if (this == o) {
      return true;
    }
    if (!(o instanceof PemKeyCertOptions)) {
      return false;
    }

    PemKeyCertOptions that = (PemKeyCertOptions) o;
    if (keyPath != null ? !keyPath.equals(that.keyPath) : that.keyPath != null) {
      return false;
    }
    if (keyValue != null ? !keyValue.equals(that.keyValue) : that.keyValue != null) {
      return false;
    }
    if (certPath != null ? !certPath.equals(that.certPath) : that.certPath != null) {
      return false;
    }
    if (certValue != null ? !certValue.equals(that.certValue) : that.certValue != null) {
      return false;
    }

    return true;
  }

  @Override
  public int hashCode() {
    int result = 1;
    result += 31 * result + (keyPath != null ? keyPath.hashCode() : 0);
    result += 31 * result + (keyValue != null ? keyValue.hashCode() : 0);
    result += 31 * result + (certPath != null ? certPath.hashCode() : 0);
    result += 31 * result + (certValue != null ? certValue.hashCode() : 0);

    return result;
  }

  @Override
  public PemKeyCertOptions clone() {
    return new PemKeyCertOptions(this);
  }
}


File: src/main/java/io/vertx/core/net/PemTrustOptions.java
/*
 * Copyright (c) 2011-2014 The original author or authors
 * ------------------------------------------------------
 * All rights reserved. This program and the accompanying materials
 * are made available under the terms of the Eclipse Public License v1.0
 * and Apache License v2.0 which accompanies this distribution.
 *
 *     The Eclipse Public License is available at
 *     http://www.eclipse.org/legal/epl-v10.html
 *
 *     The Apache License v2.0 is available at
 *     http://www.opensource.org/licenses/apache2.0.php
 *
 * You may elect to redistribute this code under either of these licenses.
 */

package io.vertx.core.net;

import io.vertx.codegen.annotations.DataObject;
import io.vertx.core.buffer.Buffer;
import io.vertx.core.impl.Arguments;
import io.vertx.core.json.JsonArray;
import io.vertx.core.json.JsonObject;

import java.util.ArrayList;
import java.util.Base64;
import java.util.List;
import java.util.Objects;

/**
 * Certificate Authority options configuring certificates based on
 * <i>Privacy-enhanced Electronic Email</i> (PEM) files. The options is configured with a list of
 * validating certificates.
 * <p>
 * Validating certificates must contain X.509 certificates wrapped in a PEM block:<p>
 *
 * <pre>
 * -----BEGIN CERTIFICATE-----
 * MIIDezCCAmOgAwIBAgIEVmLkwTANBgkqhkiG9w0BAQsFADBuMRAwDgYDVQQGEwdV
 * ...
 * z5+DuODBJUQst141Jmgq8bS543IU/5apcKQeGNxEyQ==
 * -----END CERTIFICATE-----
 * </pre>
 *
 * The certificates can either be loaded by Vert.x from the filesystem:
 * <p>
 * <pre>
 * HttpServerOptions options = new HttpServerOptions();
 * options.setPemTrustOptions(new PemTrustOptions().addCertPath("/cert.pem"));
 * </pre>
 *
 * Or directly provided as a buffer:
 * <p>
 *
 * <pre>
 * Buffer cert = vertx.fileSystem().readFileSync("/cert.pem");
 * HttpServerOptions options = new HttpServerOptions();
 * options.setPemTrustOptions(new PemTrustOptions().addCertValue(cert));
 * </pre>
 *
 * @author <a href="mailto:julien@julienviet.com">Julien Viet</a>
 * @author <a href="http://tfox.org">Tim Fox</a>
 */
@DataObject
public class PemTrustOptions implements TrustOptions, Cloneable {

  private ArrayList<String> certPaths;
  private ArrayList<Buffer> certValues;

  /**
   * Default constructor
   */
  public PemTrustOptions() {
    super();
    this.certPaths = new ArrayList<>();
    this.certValues = new ArrayList<>();
  }

  /**
   * Copy constructor
   *
   * @param other  the options to copy
   */
  public PemTrustOptions(PemTrustOptions other) {
    super();
    this.certPaths = new ArrayList<>(other.getCertPaths());
    this.certValues = new ArrayList<>(other.getCertValues());
  }

  /**
   * Create options from JSON
   *
   * @param json  the JSON
   */
  public PemTrustOptions(JsonObject json) {
    super();
    this.certPaths = new ArrayList<>();
    this.certValues = new ArrayList<>();
    for (Object certPath : json.getJsonArray("certPaths", new JsonArray())) {
      certPaths.add((String) certPath);
    }
    for (Object certValue : json.getJsonArray("certValues", new JsonArray())) {
      certValues.add(Buffer.buffer(Base64.getDecoder().decode((String) certValue)));
    }
  }

  /**
   * @return  the certificate paths used to locate certificates
   */
  public List<String> getCertPaths() {
    return certPaths;
  }

  /**
   * Add a certificate path
   *
   * @param certPath  the path to add
   * @return a reference to this, so the API can be used fluently
   * @throws NullPointerException
   */
  public PemTrustOptions addCertPath(String certPath) throws NullPointerException {
    Objects.requireNonNull(certPath, "No null certificate accepted");
    Arguments.require(!certPath.isEmpty(), "No empty certificate path accepted");
    certPaths.add(certPath);
    return this;
  }

  /**
   *
   * @return the certificate values
   */
  public List<Buffer> getCertValues() {
    return certValues;
  }

  /**
   * Add a certificate value
   *
   * @param certValue  the value to add
   * @return a reference to this, so the API can be used fluently
   * @throws NullPointerException
   */
  public PemTrustOptions addCertValue(Buffer certValue) throws NullPointerException {
    Objects.requireNonNull(certValue, "No null certificate accepted");
    certValues.add(certValue);
    return this;
  }

  @Override
  public PemTrustOptions clone() {
    return new PemTrustOptions(this);
  }

}


File: src/main/java/io/vertx/core/net/PfxOptions.java
/*
 * Copyright (c) 2011-2014 The original author or authors
 * ------------------------------------------------------
 * All rights reserved. This program and the accompanying materials
 * are made available under the terms of the Eclipse Public License v1.0
 * and Apache License v2.0 which accompanies this distribution.
 *
 *     The Eclipse Public License is available at
 *     http://www.eclipse.org/legal/epl-v10.html
 *
 *     The Apache License v2.0 is available at
 *     http://www.opensource.org/licenses/apache2.0.php
 *
 * You may elect to redistribute this code under either of these licenses.
 */

package io.vertx.core.net;

import io.vertx.codegen.annotations.DataObject;
import io.vertx.core.buffer.Buffer;
import io.vertx.core.json.JsonObject;

/**
 * Key or trust store options configuring private key and/or certificates based on PKCS#12 files.
 * <p>
 * When used as a key store, it should point to a store containing a private key and its certificate.
 * When used as a trust store, it should point to a store containing a list of accepted certificates.
 * <p>
 *
 * The store can either be loaded by Vert.x from the filesystem:
 * <p>
 * <pre>
 * HttpServerOptions options = new HttpServerOptions();
 * options.setPfxKeyCertOptions(new PfxOptions().setPath("/mykeystore.p12").setPassword("foo"));
 * </pre>
 *
 * Or directly provided as a buffer:<p>
 *
 * <pre>
 * Buffer store = vertx.fileSystem().readFileSync("/mykeystore.p12");
 * options.setPfxKeyCertOptions(new PfxOptions().setValue(store).setPassword("foo"));
 * </pre>
 *
 * @author <a href="mailto:julien@julienviet.com">Julien Viet</a>
 * @author <a href="http://tfox.org">Tim Fox</a>
 */
@DataObject
public class PfxOptions implements KeyCertOptions, TrustOptions, Cloneable {

  private String password;
  private String path;
  private Buffer value;

  /**
   * Default constructor
   */
  public PfxOptions() {
    super();
  }

  /**
   * Copy constructor
   *
   * @param other  the options to copy
   */
  public PfxOptions(PfxOptions other) {
    super();
    this.password = other.getPassword();
    this.path = other.getPath();
    this.value = other.getValue();
  }

  /**
   * Create options from JSON
   *
   * @param json  the JSON
   */
  public PfxOptions(JsonObject json) {
    super();
    this.password = json.getString("password");
    this.path = json.getString("path");
    byte[] value = json.getBinary("value");
    this.value = value != null ? Buffer.buffer(value) : null;
  }

  /**
   * Get the password
   *
   * @return  the password
   */
  public String getPassword() {
    return password;
  }

  /**
   * Set the password
   *
   * @param password  the password
   * @return a reference to this, so the API can be used fluently
   */
  public PfxOptions setPassword(String password) {
    this.password = password;
    return this;
  }

  /**
   * Get the path
   *
   * @return the path
   */
  public String getPath() {
    return path;
  }

  /**
   * Set the path
   *
   * @param path  the path
   * @return a reference to this, so the API can be used fluently
   */
  public PfxOptions setPath(String path) {
    this.path = path;
    return this;
  }

  /**
   * Get the store as a buffer
   *
   * @return store as buffer
   */
  public Buffer getValue() {
    return value;
  }

  /**
   * Set the store as a buffer
   *
   * @param value  the store as a buffer
   * @return a reference to this, so the API can be used fluently
   */
  public PfxOptions setValue(Buffer value) {
    this.value = value;
    return this;
  }

  @Override
  public boolean equals(Object o) {
    if (this == o) {
      return true;
    }
    if (!(o instanceof PfxOptions)) {
      return false;
    }

    PfxOptions that = (PfxOptions) o;
    if (password != null ? !password.equals(that.password) : that.password != null) {
      return false;
    }
    if (path != null ? !path.equals(that.path) : that.path != null) {
      return false;
    }
    if (value != null ? !value.equals(that.value) : that.value != null) {
      return false;
    }

    return true;
  }

  @Override
  public int hashCode() {
    int result = 1;
    result += 31 * result + (password != null ? password.hashCode() : 0);
    result += 31 * result + (path != null ? path.hashCode() : 0);
    result += 31 * result + (value != null ? value.hashCode() : 0);
    return result;
  }

  @Override
  public PfxOptions clone() {
    return new PfxOptions(this);
  }
}


File: src/main/java/io/vertx/core/net/TCPSSLOptions.java
/*
 * Copyright (c) 2011-2014 The original author or authors
 * ------------------------------------------------------
 * All rights reserved. This program and the accompanying materials
 * are made available under the terms of the Eclipse Public License v1.0
 * and Apache License v2.0 which accompanies this distribution.
 *
 *     The Eclipse Public License is available at
 *     http://www.eclipse.org/legal/epl-v10.html
 *
 *     The Apache License v2.0 is available at
 *     http://www.opensource.org/licenses/apache2.0.php
 *
 * You may elect to redistribute this code under either of these licenses.
 */

package io.vertx.core.net;

import io.vertx.core.buffer.Buffer;
import io.vertx.core.json.JsonArray;
import io.vertx.core.json.JsonObject;
import io.vertx.core.net.impl.SocketDefaults;

import java.util.ArrayList;
import java.util.HashSet;
import java.util.List;
import java.util.Objects;
import java.util.Set;

/**
 * Base class. TCP and SSL related options
 *
 * @author <a href="http://tfox.org">Tim Fox</a>
 */
public abstract class TCPSSLOptions extends NetworkOptions {

  /**
   * The default value of TCP-no-delay = true (Nagle disabled)
   */
  public static final boolean DEFAULT_TCP_NO_DELAY = true;

  /**
   * The default value of TCP keep alive
   */
  public static final boolean DEFAULT_TCP_KEEP_ALIVE = SocketDefaults.instance.isTcpKeepAlive();

  /**
   * The default value of SO_linger
   */
  public static final int DEFAULT_SO_LINGER = SocketDefaults.instance.getSoLinger();

  /**
   * The default value of Netty use pooled buffers = false
   */
  public static final boolean DEFAULT_USE_POOLED_BUFFERS = false;

  /**
   * SSL enable by default = false
   */
  public static final boolean DEFAULT_SSL = false;

  /**
   * Default idle timeout = 0
   */
  public static final int DEFAULT_IDLE_TIMEOUT = 0;

  private boolean tcpNoDelay;
  private boolean tcpKeepAlive;
  private int soLinger;
  private boolean usePooledBuffers;
  private int idleTimeout;
  private boolean ssl;
  private KeyCertOptions keyCertOptions;
  private TrustOptions trustOptions;
  private Set<String> enabledCipherSuites = new HashSet<>();
  private ArrayList<String> crlPaths;
  private ArrayList<Buffer> crlValues;

  /**
   * Default constructor
   */
  public TCPSSLOptions() {
    super();
    tcpNoDelay = DEFAULT_TCP_NO_DELAY;
    tcpKeepAlive = DEFAULT_TCP_KEEP_ALIVE;
    soLinger = DEFAULT_SO_LINGER;
    usePooledBuffers = DEFAULT_USE_POOLED_BUFFERS;
    idleTimeout = DEFAULT_IDLE_TIMEOUT;
    ssl = DEFAULT_SSL;
    crlPaths = new ArrayList<>();
    crlValues = new ArrayList<>();
  }

  /**
   * Copy constructor
   *
   * @param other  the options to copy
   */
  public TCPSSLOptions(TCPSSLOptions other) {
    super(other);
    this.tcpNoDelay = other.isTcpNoDelay();
    this.tcpKeepAlive = other.isTcpKeepAlive();
    this.soLinger = other.getSoLinger();
    this.usePooledBuffers = other.isUsePooledBuffers();
    this.idleTimeout = other.getIdleTimeout();
    this.ssl = other.isSsl();
    this.keyCertOptions = other.getKeyCertOptions() != null ? other.getKeyCertOptions().clone() : null;
    this.trustOptions = other.getTrustOptions() != null ? other.getTrustOptions().clone() : null;
    this.enabledCipherSuites = other.getEnabledCipherSuites() == null ? new HashSet<>() : new HashSet<>(other.getEnabledCipherSuites());
    this.crlPaths = new ArrayList<>(other.getCrlPaths());
    this.crlValues = new ArrayList<>(other.getCrlValues());
  }

  /**
   * Create options from JSON
   *
   * @param json the JSON
   */
  public TCPSSLOptions(JsonObject json) {
    super(json);
    this.tcpNoDelay = json.getBoolean("tcpNoDelay", DEFAULT_TCP_NO_DELAY);
    this.tcpKeepAlive = json.getBoolean("tcpKeepAlive", DEFAULT_TCP_KEEP_ALIVE);
    this.soLinger = json.getInteger("soLinger", DEFAULT_SO_LINGER);
    this.usePooledBuffers = json.getBoolean("usePooledBuffers", false);
    this.idleTimeout = json.getInteger("idleTimeout", 0);
    this.ssl = json.getBoolean("ssl", false);
    JsonObject keyCertJson = json.getJsonObject("keyStoreOptions");
    if (keyCertJson != null) {
      keyCertOptions = new JksOptions(keyCertJson);
    }
    keyCertJson = json.getJsonObject("pfxKeyCertOptions");
    if (keyCertJson != null) {
      keyCertOptions = new PfxOptions(keyCertJson);
    }
    keyCertJson = json.getJsonObject("pemKeyCertOptions");
    if (keyCertJson != null) {
      keyCertOptions = new PemKeyCertOptions(keyCertJson);
    }
    JsonObject trustOptions = json.getJsonObject("trustStoreOptions");
    if (trustOptions != null) {
      this.trustOptions = new JksOptions(trustOptions);
    }
    trustOptions = json.getJsonObject("pfxTrustOptions");
    if (trustOptions != null) {
      this.trustOptions = new PfxOptions(trustOptions);
    }
    trustOptions = json.getJsonObject("pemTrustOptions");
    if (trustOptions != null) {
      this.trustOptions = new PemTrustOptions(trustOptions);
    }
    JsonArray arr = json.getJsonArray("enabledCipherSuites");
    this.enabledCipherSuites = arr == null ? new HashSet<>() : new HashSet<>(arr.getList());
    arr = json.getJsonArray("crlPaths");
    this.crlPaths = arr == null ? new ArrayList<>() : new ArrayList<>(arr.getList());
    this.crlValues = new ArrayList<>();
    arr = json.getJsonArray("crlValues");
    if (arr != null) {
      ((List<byte[]>) arr.getList()).stream().map(Buffer::buffer).forEach(crlValues::add);
    }
  }

  /**
   * @return TCP no delay enabled ?
   */
  public boolean isTcpNoDelay() {
    return tcpNoDelay;
  }

  /**
   * Set whether TCP no delay is enabled
   *
   * @param tcpNoDelay true if TCP no delay is enabled (Nagle disabled)
   * @return a reference to this, so the API can be used fluently
   */
  public TCPSSLOptions setTcpNoDelay(boolean tcpNoDelay) {
    this.tcpNoDelay = tcpNoDelay;
    return this;
  }

  /**
   * @return is TCP keep alive enabled?
   */
  public boolean isTcpKeepAlive() {
    return tcpKeepAlive;
  }

  /**
   * Set whether TCP keep alive is enabled
   *
   * @param tcpKeepAlive true if TCP keep alive is enabled
   * @return a reference to this, so the API can be used fluently
   */
  public TCPSSLOptions setTcpKeepAlive(boolean tcpKeepAlive) {
    this.tcpKeepAlive = tcpKeepAlive;
    return this;
  }

  /**
   *
   * @return is SO_linger enabled
   */
  public int getSoLinger() {
    return soLinger;
  }

  /**
   * Set whether SO_linger keep alive is enabled
   *
   * @param soLinger true if SO_linger is enabled
   * @return a reference to this, so the API can be used fluently
   */
  public TCPSSLOptions setSoLinger(int soLinger) {
    if (soLinger < 0) {
      throw new IllegalArgumentException("soLinger must be >= 0");
    }
    this.soLinger = soLinger;
    return this;
  }

  /**
   * @return are Netty pooled buffers enabled?
   *
   */
  public boolean isUsePooledBuffers() {
    return usePooledBuffers;
  }

  /**
   * Set whether Netty pooled buffers are enabled
   *
   * @param usePooledBuffers true if pooled buffers enabled
   * @return a reference to this, so the API can be used fluently
   */
  public TCPSSLOptions setUsePooledBuffers(boolean usePooledBuffers) {
    this.usePooledBuffers = usePooledBuffers;
    return this;
  }

  /**
   * Set the idle timeout, in seconds. zero means don't timeout.
   * This determines if a connection will timeout and be closed if no data is received within the timeout.
   *
   * @param idleTimeout  the timeout, in seconds
   * @return a reference to this, so the API can be used fluently
   */
  public TCPSSLOptions setIdleTimeout(int idleTimeout) {
    if (idleTimeout < 0) {
      throw new IllegalArgumentException("idleTimeout must be >= 0");
    }
    this.idleTimeout = idleTimeout;
    return this;
  }

  /**
   * @return  the idle timeout, in seconds
   */
  public int getIdleTimeout() {
    return idleTimeout;
  }

  /**
   *
   * @return is SSL/TLS enabled?
   */
  public boolean isSsl() {
    return ssl;
  }

  /**
   * Set whether SSL/TLS is enabled
   *
   * @param ssl  true if enabled
   * @return a reference to this, so the API can be used fluently
   */
  public TCPSSLOptions setSsl(boolean ssl) {
    this.ssl = ssl;
    return this;
  }

  /**
   * @return the key cert options
   */
  public KeyCertOptions getKeyCertOptions() {
    return keyCertOptions;
  }

  /**
   * Set the key/cert options in jks format, aka Java keystore.
   * @param options the key store in jks format
   * @return a reference to this, so the API can be used fluently
   */
  public TCPSSLOptions setKeyStoreOptions(JksOptions options) {
    this.keyCertOptions = options;
    return this;
  }

  /**
   * Set the key/cert options in pfx format.
   * @param options the key cert options in pfx format
   * @return a reference to this, so the API can be used fluently
   */
  public TCPSSLOptions setPfxKeyCertOptions(PfxOptions options) {
    this.keyCertOptions = options;
    return this;
  }

  /**
   * Set the key/cert store options in pem format.
   * @param options the options in pem format
   * @return a reference to this, so the API can be used fluently
   */
  public TCPSSLOptions setPemKeyCertOptions(PemKeyCertOptions options) {
    this.keyCertOptions = options;
    return this;
  }

  /**
   * @return the trust options
   */
  public TrustOptions getTrustOptions() {
    return trustOptions;
  }

  /**
   * Set the trust options in jks format, aka Java trustore
   * @param options the options in jks format
   * @return a reference to this, so the API can be used fluently
   */
  public TCPSSLOptions setTrustStoreOptions(JksOptions options) {
    this.trustOptions = options;
    return this;
  }

  /**
   * Set the trust options in pfx format
   * @param options the options in pfx format
   * @return a reference to this, so the API can be used fluently
   */
  public TCPSSLOptions setPfxTrustOptions(PfxOptions options) {
    this.trustOptions = options;
    return this;
  }

  /**
   * Set the trust options in pem format
   * @param options the options in pem format
   * @return a reference to this, so the API can be used fluently
   */
  public TCPSSLOptions setPemTrustOptions(PemTrustOptions options) {
    this.trustOptions = options;
    return this;
  }

  /**
   * Add an enabled cipher suite
   *
   * @param suite  the suite
   * @return a reference to this, so the API can be used fluently
   */
  public TCPSSLOptions addEnabledCipherSuite(String suite) {
    enabledCipherSuites.add(suite);
    return this;
  }

  /**
   *
   * @return the enabled cipher suites
   */
  public Set<String> getEnabledCipherSuites() {
    return enabledCipherSuites;
  }

  /**
   *
   * @return the CRL (Certificate revocation list) paths
   */
  public List<String> getCrlPaths() {
    return crlPaths;
  }

  /**
   * Add a CRL path
   * @param crlPath  the path
   * @return a reference to this, so the API can be used fluently
   * @throws NullPointerException
   */
  public TCPSSLOptions addCrlPath(String crlPath) throws NullPointerException {
    Objects.requireNonNull(crlPath, "No null crl accepted");
    crlPaths.add(crlPath);
    return this;
  }

  /**
   * Get the CRL values
   *
   * @return the list of values
   */
  public List<Buffer> getCrlValues() {
    return crlValues;
  }

  /**
   * Add a CRL value
   *
   * @param crlValue  the value
   * @return a reference to this, so the API can be used fluently
   * @throws NullPointerException
   */
  public TCPSSLOptions addCrlValue(Buffer crlValue) throws NullPointerException {
    Objects.requireNonNull(crlValue, "No null crl accepted");
    crlValues.add(crlValue);
    return this;
  }

  @Override
  public boolean equals(Object o) {
    if (this == o) return true;
    if (!(o instanceof TCPSSLOptions)) return false;
    if (!super.equals(o)) return false;

    TCPSSLOptions that = (TCPSSLOptions) o;

    if (idleTimeout != that.idleTimeout) return false;
    if (soLinger != that.soLinger) return false;
    if (ssl != that.ssl) return false;
    if (tcpKeepAlive != that.tcpKeepAlive) return false;
    if (tcpNoDelay != that.tcpNoDelay) return false;
    if (usePooledBuffers != that.usePooledBuffers) return false;
    if (crlPaths != null ? !crlPaths.equals(that.crlPaths) : that.crlPaths != null) return false;
    if (crlValues != null ? !crlValues.equals(that.crlValues) : that.crlValues != null) return false;
    if (enabledCipherSuites != null ? !enabledCipherSuites.equals(that.enabledCipherSuites) : that.enabledCipherSuites != null)
      return false;
    if (keyCertOptions != null ? !keyCertOptions.equals(that.keyCertOptions) : that.keyCertOptions != null) return false;
    if (trustOptions != null ? !trustOptions.equals(that.trustOptions) : that.trustOptions != null) return false;

    return true;
  }

  @Override
  public int hashCode() {
    int result = super.hashCode();
    result = 31 * result + (tcpNoDelay ? 1 : 0);
    result = 31 * result + (tcpKeepAlive ? 1 : 0);
    result = 31 * result + soLinger;
    result = 31 * result + (usePooledBuffers ? 1 : 0);
    result = 31 * result + idleTimeout;
    result = 31 * result + (ssl ? 1 : 0);
    result = 31 * result + (keyCertOptions != null ? keyCertOptions.hashCode() : 0);
    result = 31 * result + (trustOptions != null ? trustOptions.hashCode() : 0);
    result = 31 * result + (enabledCipherSuites != null ? enabledCipherSuites.hashCode() : 0);
    result = 31 * result + (crlPaths != null ? crlPaths.hashCode() : 0);
    result = 31 * result + (crlValues != null ? crlValues.hashCode() : 0);
    return result;
  }
}


File: src/test/java/io/vertx/test/core/FileSystemTest.java
/*
 * Copyright 2014 Red Hat, Inc.
 *
 * All rights reserved. This program and the accompanying materials
 * are made available under the terms of the Eclipse Public License v1.0
 * and Apache License v2.0 which accompanies this distribution.
 *
 * The Eclipse Public License is available at
 * http://www.eclipse.org/legal/epl-v10.html
 *
 * The Apache License v2.0 is available at
 * http://www.opensource.org/licenses/apache2.0.php
 *
 * You may elect to redistribute this code under either of these licenses.
 */

package io.vertx.test.core;

import io.netty.buffer.ByteBuf;
import io.netty.buffer.Unpooled;
import io.vertx.core.AsyncResultHandler;
import io.vertx.core.Handler;
import io.vertx.core.Vertx;
import io.vertx.core.buffer.Buffer;
import io.vertx.core.file.AsyncFile;
import io.vertx.core.file.FileProps;
import io.vertx.core.file.FileSystemException;
import io.vertx.core.file.FileSystemProps;
import io.vertx.core.file.OpenOptions;
import io.vertx.core.file.impl.AsyncFileImpl;
import io.vertx.core.impl.Utils;
import io.vertx.core.json.JsonObject;
import io.vertx.core.streams.Pump;
import io.vertx.core.streams.ReadStream;
import io.vertx.core.streams.WriteStream;
import org.junit.Assume;
import org.junit.Rule;
import org.junit.Test;
import org.junit.rules.TemporaryFolder;

import java.io.File;
import java.io.IOException;
import java.nio.file.FileSystems;
import java.nio.file.Files;
import java.nio.file.LinkOption;
import java.nio.file.Path;
import java.nio.file.Paths;
import java.nio.file.attribute.GroupPrincipal;
import java.nio.file.attribute.PosixFileAttributes;
import java.nio.file.attribute.PosixFilePermission;
import java.nio.file.attribute.PosixFilePermissions;
import java.nio.file.attribute.UserPrincipal;
import java.util.HashSet;
import java.util.List;
import java.util.Set;
import java.util.concurrent.atomic.AtomicInteger;

import static io.vertx.test.core.TestUtils.*;

/**
 * @author <a href="http://tfox.org">Tim Fox</a>
 */
public class FileSystemTest extends VertxTestBase {

  private static final String DEFAULT_DIR_PERMS = "rwxr-xr-x";
  private static final String DEFAULT_FILE_PERMS = "rw-r--r--";

  private String pathSep;
  private String testDir;

  @Rule
  public TemporaryFolder testFolder = new TemporaryFolder();

  public void setUp() throws Exception {
    super.setUp();
    java.nio.file.FileSystem fs = FileSystems.getDefault();
    pathSep = fs.getSeparator();
    File ftestDir = testFolder.newFolder();
    testDir = ftestDir.toString();
  }

  @Test
  public void testIllegalArguments() throws Exception {
    assertNullPointerException(() -> vertx.fileSystem().copy(null, "ignored", h -> {}));
    assertNullPointerException(() -> vertx.fileSystem().copy("ignored", null, h -> {}));
    assertNullPointerException(() -> vertx.fileSystem().copyBlocking(null, "ignored"));
    assertNullPointerException(() -> vertx.fileSystem().copyBlocking("ignored", null));
    assertNullPointerException(() -> vertx.fileSystem().copyRecursive(null, "ignored", true, h -> {}));
    assertNullPointerException(() -> vertx.fileSystem().copyRecursive("ignored", null, true, h -> {}));
    assertNullPointerException(() -> vertx.fileSystem().copyRecursiveBlocking(null, "ignored", true));
    assertNullPointerException(() -> vertx.fileSystem().copyRecursiveBlocking("ignored", null, true));
    assertNullPointerException(() -> vertx.fileSystem().move(null, "ignored", h -> {}));
    assertNullPointerException(() -> vertx.fileSystem().move("ignored", null, h -> {}));
    assertNullPointerException(() -> vertx.fileSystem().moveBlocking(null, "ignored"));
    assertNullPointerException(() -> vertx.fileSystem().moveBlocking("ignored", null));
    assertNullPointerException(() -> vertx.fileSystem().truncate(null, 0, h -> {}));
    assertNullPointerException(() -> vertx.fileSystem().truncateBlocking(null, 0));
    assertNullPointerException(() -> vertx.fileSystem().chmod(null, "ignored", h -> {}));
    assertNullPointerException(() -> vertx.fileSystem().chmod("ignored", null, h -> {}));
    assertNullPointerException(() -> vertx.fileSystem().chmodBlocking(null, "ignored"));
    assertNullPointerException(() -> vertx.fileSystem().chmodBlocking("ignored", null));
    assertNullPointerException(() -> vertx.fileSystem().chmodRecursive(null, "ignored", "ignored", h -> {}));
    assertNullPointerException(() -> vertx.fileSystem().chmodRecursive("ignored", null, "ignored", h -> {}));
    assertNullPointerException(() -> vertx.fileSystem().chmodRecursiveBlocking(null, "ignored", "ignored"));
    assertNullPointerException(() -> vertx.fileSystem().chmodRecursiveBlocking("ignored", null, "ignored"));
    assertNullPointerException(() -> vertx.fileSystem().chown(null, "ignored", "ignored", h -> {}));
    assertNullPointerException(() -> vertx.fileSystem().chownBlocking(null, "ignored", "ignored"));
    assertNullPointerException(() -> vertx.fileSystem().props(null, h -> {}));
    assertNullPointerException(() -> vertx.fileSystem().propsBlocking(null));
    assertNullPointerException(() -> vertx.fileSystem().lprops(null, h -> {}));
    assertNullPointerException(() -> vertx.fileSystem().lpropsBlocking(null));
    assertNullPointerException(() -> vertx.fileSystem().link(null, "ignored", h -> {}));
    assertNullPointerException(() -> vertx.fileSystem().link("ignored", null, h -> {}));
    assertNullPointerException(() -> vertx.fileSystem().linkBlocking(null, "ignored"));
    assertNullPointerException(() -> vertx.fileSystem().linkBlocking("ignored", null));
    assertNullPointerException(() -> vertx.fileSystem().symlink(null, "ignored", h -> {}));
    assertNullPointerException(() -> vertx.fileSystem().symlink("ignored", null, h -> {}));
    assertNullPointerException(() -> vertx.fileSystem().symlinkBlocking(null, "ignored"));
    assertNullPointerException(() -> vertx.fileSystem().symlinkBlocking("ignored", null));
    assertNullPointerException(() -> vertx.fileSystem().unlink(null, h -> {}));
    assertNullPointerException(() -> vertx.fileSystem().unlinkBlocking(null));
    assertNullPointerException(() -> vertx.fileSystem().readSymlink(null, h -> {}));
    assertNullPointerException(() -> vertx.fileSystem().readSymlinkBlocking(null));
    assertNullPointerException(() -> vertx.fileSystem().delete(null, h -> {}));
    assertNullPointerException(() -> vertx.fileSystem().deleteBlocking(null));
    assertNullPointerException(() -> vertx.fileSystem().deleteRecursive(null, true, h -> {}));
    assertNullPointerException(() -> vertx.fileSystem().deleteRecursiveBlocking(null, true));
    assertNullPointerException(() -> vertx.fileSystem().mkdir(null, h -> {}));
    assertNullPointerException(() -> vertx.fileSystem().mkdirBlocking(null));
    assertNullPointerException(() -> vertx.fileSystem().mkdir(null, "ignored", h -> {}));
    assertNullPointerException(() -> vertx.fileSystem().mkdirBlocking(null, "ignored"));
    assertNullPointerException(() -> vertx.fileSystem().mkdirs(null, h -> {}));
    assertNullPointerException(() -> vertx.fileSystem().mkdirsBlocking(null));
    assertNullPointerException(() -> vertx.fileSystem().mkdirs(null, "ignored", h -> {}));
    assertNullPointerException(() -> vertx.fileSystem().mkdirsBlocking(null, "ignored"));
    assertNullPointerException(() -> vertx.fileSystem().readDir(null, h -> {}));
    assertNullPointerException(() -> vertx.fileSystem().readDirBlocking(null));
    assertNullPointerException(() -> vertx.fileSystem().readDir(null, "ignored", h -> {}));
    assertNullPointerException(() -> vertx.fileSystem().readDirBlocking(null, "ignored"));
    assertNullPointerException(() -> vertx.fileSystem().readFile(null, h -> {}));
    assertNullPointerException(() -> vertx.fileSystem().readFileBlocking(null));
    assertNullPointerException(() -> vertx.fileSystem().writeFile(null, Buffer.buffer(), h -> {}));
    assertNullPointerException(() -> vertx.fileSystem().writeFile("ignored", null, h -> {}));
    assertNullPointerException(() -> vertx.fileSystem().writeFileBlocking(null, Buffer.buffer()));
    assertNullPointerException(() -> vertx.fileSystem().writeFileBlocking("ignored", null));
    assertNullPointerException(() -> vertx.fileSystem().open(null, new OpenOptions(), h -> {}));
    assertNullPointerException(() -> vertx.fileSystem().open("ignored", null, h -> {}));
    assertNullPointerException(() -> vertx.fileSystem().openBlocking(null, new OpenOptions()));
    assertNullPointerException(() -> vertx.fileSystem().openBlocking("ignored", null));
    assertNullPointerException(() -> vertx.fileSystem().createFile(null, h -> {}));
    assertNullPointerException(() -> vertx.fileSystem().createFileBlocking(null));
    assertNullPointerException(() -> vertx.fileSystem().createFile(null, "ignored", h -> {}));
    assertNullPointerException(() -> vertx.fileSystem().createFileBlocking(null, "ignored"));
    assertNullPointerException(() -> vertx.fileSystem().exists(null, h -> {}));
    assertNullPointerException(() -> vertx.fileSystem().existsBlocking(null));
    assertNullPointerException(() -> vertx.fileSystem().fsProps(null, h -> {}));
    assertNullPointerException(() -> vertx.fileSystem().fsPropsBlocking(null));

    String fileName = "some-file.dat";
    AsyncFile asyncFile = vertx.fileSystem().openBlocking(testDir + pathSep + fileName, new OpenOptions());

    assertNullPointerException(() -> asyncFile.write(null));
    assertIllegalArgumentException(() -> asyncFile.setWriteQueueMaxSize(1));
    assertIllegalArgumentException(() -> asyncFile.setWriteQueueMaxSize(0));
    assertIllegalArgumentException(() -> asyncFile.setWriteQueueMaxSize(-1));
    assertNullPointerException(() -> asyncFile.write(null, 0, h -> {}));
    assertNullPointerException(() -> asyncFile.write(Buffer.buffer(), 0, null));
    assertIllegalArgumentException(() -> asyncFile.write(Buffer.buffer(), -1, h -> {}));

    assertNullPointerException(() -> asyncFile.read(null, 0, 0, 0, h -> {}));
    assertNullPointerException(() -> asyncFile.read(Buffer.buffer(), 0, 0, 0, null));

    assertIllegalArgumentException(() -> asyncFile.read(Buffer.buffer(), -1, 0, 0, h -> {}));
    assertIllegalArgumentException(() -> asyncFile.read(Buffer.buffer(), 0, -1, 0, h -> {}));
    assertIllegalArgumentException(() -> asyncFile.read(Buffer.buffer(), 0, 0, -1, h -> {}));
  }

  @Test
  public void testSimpleCopy() throws Exception {
    String source = "foo.txt";
    String target = "bar.txt";
    createFileWithJunk(source, 100);
    testCopy(source, target, false, true, v-> {
      assertTrue(fileExists(source));
      assertTrue(fileExists(target));
    });
    await();
  }

  @Test
  public void testSimpleCopyFileAlreadyExists() throws Exception {
    String source = "foo.txt";
    String target = "bar.txt";
    createFileWithJunk(source, 100);
    createFileWithJunk(target, 100);
    testCopy(source, target, false, false, v -> {
      assertTrue(fileExists(source));
      assertTrue(fileExists(target));
    });
    await();
  }

  @Test
  public void testCopyIntoDir() throws Exception {
    String source = "foo.txt";
    String dir = "some-dir";
    String target = dir + pathSep + "bar.txt";
    mkDir(dir);
    createFileWithJunk(source, 100);
    testCopy(source, target, false, true, v -> {
      assertTrue(fileExists(source));
      assertTrue(fileExists(target));
    });
    await();
  }

  @Test
  public void testCopyEmptyDir() throws Exception {
    String source = "some-dir";
    String target = "some-other-dir";
    mkDir(source);
    testCopy(source, target, false, true, v -> {
     assertTrue(fileExists(source));
     assertTrue(fileExists(target));
    });
    await();
  }

  @Test
  public void testCopyNonEmptyDir() throws Exception {
    String source = "some-dir";
    String target = "some-other-dir";
    String file1 = pathSep + "somefile.bar";
    mkDir(source);
    createFileWithJunk(source + file1, 100);
    testCopy(source, target, false, true, v -> {
      assertTrue(fileExists(source));
      assertTrue(fileExists(target));
      assertFalse(fileExists(target + file1));
    });
    await();
  }

  @Test
  public void testFailCopyDirAlreadyExists() throws Exception {
    String source = "some-dir";
    String target = "some-other-dir";
    mkDir(source);
    mkDir(target);
    testCopy(source, target, false, false, v -> {
      assertTrue(fileExists(source));
      assertTrue(fileExists(target));
    });
    await();
  }

  @Test
  public void testRecursiveCopy() throws Exception {
    String dir = "some-dir";
    String file1 = pathSep + "file1.dat";
    String file2 = pathSep + "index.html";
    String dir2 = "next-dir";
    String file3 = pathSep + "blah.java";
    mkDir(dir);
    createFileWithJunk(dir + file1, 100);
    createFileWithJunk(dir + file2, 100);
    mkDir(dir + pathSep + dir2);
    createFileWithJunk(dir + pathSep + dir2 + file3, 100);
    String target = "some-other-dir";
    testCopy(dir, target, true, true, v -> {
      assertTrue(fileExists(dir));
      assertTrue(fileExists(target));
      assertTrue(fileExists(target + file1));
      assertTrue(fileExists(target + file2));
      assertTrue(fileExists(target + pathSep + dir2 + file3));
    });
    await();
  }

  private void testCopy(String source, String target, boolean recursive,
                        boolean shouldPass, Handler<Void> afterOK) {
    if (recursive) {
      vertx.fileSystem().copyRecursive(testDir + pathSep + source, testDir + pathSep + target, true, createHandler(shouldPass, afterOK));
    } else {
      vertx.fileSystem().copy(testDir + pathSep + source, testDir + pathSep + target, createHandler(shouldPass, afterOK));
    }
  }

  @Test
  public void testSimpleMove() throws Exception {
    String source = "foo.txt";
    String target = "bar.txt";
    createFileWithJunk(source, 100);
    testMove(source, target, true, v -> {
      assertFalse(fileExists(source));
      assertTrue(fileExists(target));
    });
    await();
  }

  @Test
  public void testSimpleMoveFileAlreadyExists() throws Exception {
    String source = "foo.txt";
    String target = "bar.txt";
    createFileWithJunk(source, 100);
    createFileWithJunk(target, 100);
    testMove(source, target, false, v -> {
      assertTrue(fileExists(source));
      assertTrue(fileExists(target));
    });
    await();
  }

  @Test
  public void testMoveEmptyDir() throws Exception {
    String source = "some-dir";
    String target = "some-other-dir";
    mkDir(source);
    testMove(source, target, true, v -> {
      assertFalse(fileExists(source));
      assertTrue(fileExists(target));
    });
    await();
  }

  @Test
  public void testMoveEmptyDirTargetExists() throws Exception {
    String source = "some-dir";
    String target = "some-other-dir";
    mkDir(source);
    mkDir(target);
    testMove(source, target, false, v -> {
      assertTrue(fileExists(source));
      assertTrue(fileExists(target));
    });
    await();
  }

  @Test
  public void testMoveNonEmptyDir() throws Exception {
    String dir = "some-dir";
    String file1 = pathSep + "file1.dat";
    String file2 = pathSep + "index.html";
    String dir2 = "next-dir";
    String file3 = pathSep + "blah.java";
    mkDir(dir);
    createFileWithJunk(dir + file1, 100);
    createFileWithJunk(dir + file2, 100);
    mkDir(dir + pathSep + dir2);
    createFileWithJunk(dir + pathSep + dir2 + file3, 100);
    String target = "some-other-dir";
    testMove(dir, target, true, v -> {
      assertFalse(fileExists(dir));
      assertTrue(fileExists(target));
      assertTrue(fileExists(target + file1));
      assertTrue(fileExists(target + file2));
      assertTrue(fileExists(target + pathSep + dir2 + file3));
    });
    await();
  }

  private void testMove(String source, String target, boolean shouldPass, Handler<Void> afterOK) throws Exception {
    vertx.fileSystem().move(testDir + pathSep + source, testDir + pathSep + target, createHandler(shouldPass, afterOK));
  }

  @Test
  public void testTruncate() throws Exception {
    String file1 = "some-file.dat";
    long initialLen = 1000;
    long truncatedLen = 534;
    createFileWithJunk(file1, initialLen);
    assertEquals(initialLen, fileLength(file1));
    testTruncate(file1, truncatedLen, true, v -> {
      assertEquals(truncatedLen, fileLength(file1));
    });
    await();
  }

  @Test
  public void testTruncateExtendsFile() throws Exception {
    String file1 = "some-file.dat";
    long initialLen = 500;
    long truncatedLen = 1000;
    createFileWithJunk(file1, initialLen);
    assertEquals(initialLen, fileLength(file1));
    testTruncate(file1, truncatedLen, true, v -> {
      assertEquals(truncatedLen, fileLength(file1));
    });
    await();
  }

  @Test
  public void testTruncateFileDoesNotExist() throws Exception {
    String file1 = "some-file.dat";
    long truncatedLen = 534;
    testTruncate(file1, truncatedLen, false, null);
    await();
  }

  private void testTruncate(String file, long truncatedLen, boolean shouldPass,
                            Handler<Void> afterOK) throws Exception {
    vertx.fileSystem().truncate(testDir + pathSep + file, truncatedLen, createHandler(shouldPass, afterOK));
  }

  @Test
  public void testChmodNonRecursive1() throws Exception {
    testChmodNonRecursive("rw-------");
  }

  @Test
  public void testChmodNonRecursive2() throws Exception {
    testChmodNonRecursive("rwx------");
  }

  @Test
  public void testChmodNonRecursive3() throws Exception {
    testChmodNonRecursive( "rw-rw-rw-");
  }

  @Test
  public void testChmodNonRecursive4() throws Exception {
    testChmodNonRecursive("rw-r--r--");
  }

  @Test
  public void testChmodNonRecursive5() throws Exception {
    testChmodNonRecursive("rw--w--w-");
  }

  @Test
  public void testChmodNonRecursive6() throws Exception {
    testChmodNonRecursive("rw-rw-rw-");
  }

  private void testChmodNonRecursive(String perms) throws Exception {
    String file1 = "some-file.dat";
    createFileWithJunk(file1, 100);
    testChmod(file1, perms, null, true, v -> {
      azzertPerms(perms, file1);
      deleteFile(file1);
    });
    await();
  }

  private void azzertPerms(String perms, String file1) {
    if (!Utils.isWindows()) {
      assertEquals(perms, getPerms(file1));
    }
  }

  @Test
  public void testChmodRecursive1() throws Exception {
    testChmodRecursive("rw-------",  "rwx------");
  }

  @Test
  public void testChmodRecursive2() throws Exception {
    testChmodRecursive("rwx------", "rwx------");
  }

  @Test
  public void testChmodRecursive3() throws Exception {
    testChmodRecursive("rw-rw-rw-", "rwxrw-rw-");
  }

  @Test
  public void testChmodRecursive4() throws Exception {
    testChmodRecursive("rw-r--r--", "rwxr--r--");
  }

  @Test
  public void testChmodRecursive5() throws Exception {
    testChmodRecursive("rw--w--w-", "rwx-w--w-");
  }

  @Test
  public void testChmodRecursive6() throws Exception {
    testChmodRecursive("rw-rw-rw-", "rwxrw-rw-");
  }

  private void testChmodRecursive(String perms, String dirPerms) throws Exception {
    String dir = "some-dir";
    String file1 = pathSep + "file1.dat";
    String file2 = pathSep + "index.html";
    String dir2 = "next-dir";
    String file3 = pathSep + "blah.java";
    mkDir(dir);
    createFileWithJunk(dir + file1, 100);
    createFileWithJunk(dir + file2, 100);
    mkDir(dir + pathSep + dir2);
    createFileWithJunk(dir + pathSep + dir2 + file3, 100);
    testChmod(dir, perms, dirPerms, true, v -> {
      azzertPerms(dirPerms, dir);
      azzertPerms(perms, dir + file1);
      azzertPerms(perms, dir + file2);
      azzertPerms(dirPerms, dir + pathSep + dir2);
      azzertPerms(perms, dir + pathSep + dir2 + file3);
      deleteDir(dir);
    });
    await();
  }

  @Test
  public void testChownToRootFails() throws Exception {
    testChownFails("root");
  }

  @Test
  public void testChownToNotExistingUserFails() throws Exception {
    testChownFails("jfhfhjejweg");
  }

  private void testChownFails(String user) throws Exception {
    String file1 = "some-file.dat";
    createFileWithJunk(file1, 100);
    vertx.fileSystem().chown(testDir + pathSep + file1, user, null, ar -> {
      deleteFile(file1);
      assertTrue(ar.failed());
      testComplete();
    });
    await();
  }

  @Test
  public void testChownToOwnUser() throws Exception {
    String file1 = "some-file.dat";
    createFileWithJunk(file1, 100);
    String fullPath = testDir + pathSep + file1;
    Path path = Paths.get(fullPath);
    UserPrincipal owner = Files.getOwner(path);
    String user = owner.getName();
    vertx.fileSystem().chown(fullPath, user, null, ar -> {
      deleteFile(file1);
      assertTrue(ar.succeeded());
      testComplete();
    });
    await();
  }

  @Test
  public void testChownToOwnGroup() throws Exception {
    // Not supported in WindowsFileSystemProvider
    Assume.assumeFalse(Utils.isWindows());
    String file1 = "some-file.dat";
    createFileWithJunk(file1, 100);
    String fullPath = testDir + pathSep + file1;
    Path path = Paths.get(fullPath);
    GroupPrincipal group = Files.readAttributes(path, PosixFileAttributes.class, LinkOption.NOFOLLOW_LINKS).group();
    vertx.fileSystem().chown(fullPath, null, group.getName(), ar -> {
      deleteFile(file1);
      assertTrue(ar.succeeded());
      testComplete();
    });
    await();
  }

  private void testChmod(String file, String perms, String dirPerms,
                         boolean shouldPass, Handler<Void> afterOK) throws Exception {
    if (Files.isDirectory(Paths.get(testDir + pathSep + file))) {
      azzertPerms(DEFAULT_DIR_PERMS, file);
    } else {
      azzertPerms(DEFAULT_FILE_PERMS, file);
    }
    if (dirPerms != null) {
      vertx.fileSystem().chmodRecursive(testDir + pathSep + file, perms, dirPerms, createHandler(shouldPass, afterOK));
    } else {
      vertx.fileSystem().chmod(testDir + pathSep + file, perms, createHandler(shouldPass, afterOK));
    }
  }

  @Test
  public void testProps() throws Exception {
    String fileName = "some-file.txt";
    long fileSize = 1234;

    // The times are quite inaccurate so we give 1 second leeway
    long start = 1000 * (System.currentTimeMillis() / 1000 - 1);
    createFileWithJunk(fileName, fileSize);

    testProps(fileName, false, true, st -> {
      assertNotNull(st);
      assertEquals(fileSize, st.size());
      assertTrue(st.creationTime() >= start);
      assertTrue(st.lastAccessTime() >= start);
      assertTrue(st.lastModifiedTime() >= start);
      assertFalse(st.isDirectory());
      assertTrue(st.isRegularFile());
      assertFalse(st.isSymbolicLink());
    });
    await();
  }

  @Test
  public void testPropsFileDoesNotExist() throws Exception {
    String fileName = "some-file.txt";
    testProps(fileName, false, false, null);
    await();
  }

  @Test
  public void testPropsFollowLink() throws Exception {
    // Symlinks require a modified security policy in Windows. -- See http://stackoverflow.com/questions/23217460/how-to-create-soft-symbolic-link-using-java-nio-files
    Assume.assumeFalse(Utils.isWindows());
    String fileName = "some-file.txt";
    long fileSize = 1234;

    // The times are quite inaccurate so we give 1 second leeway
    long start = 1000 * (System.currentTimeMillis() / 1000 - 1);
    createFileWithJunk(fileName, fileSize);
    long end = 1000 * (System.currentTimeMillis() / 1000 + 1);

    String linkName = "some-link.txt";
    Files.createSymbolicLink(Paths.get(testDir + pathSep + linkName), Paths.get(fileName));

    testProps(linkName, false, true, st -> {
      assertNotNull(st);
      assertEquals(fileSize, st.size());
      assertTrue(st.creationTime() >= start);
      assertTrue(st.creationTime() <= end);
      assertTrue(st.lastAccessTime() >= start);
      assertTrue(st.lastAccessTime() <= end);
      assertTrue(st.lastModifiedTime() >= start);
      assertTrue(st.lastModifiedTime() <= end);
      assertFalse(st.isDirectory());
      assertFalse(st.isOther());
      assertTrue(st.isRegularFile());
      assertFalse(st.isSymbolicLink());
    });
    await();
  }

  @Test
  public void testPropsDontFollowLink() throws Exception {
    // Symlinks require a modified security policy in Windows. -- See http://stackoverflow.com/questions/23217460/how-to-create-soft-symbolic-link-using-java-nio-files
    Assume.assumeFalse(Utils.isWindows());
    String fileName = "some-file.txt";
    long fileSize = 1234;
    createFileWithJunk(fileName, fileSize);
    String linkName = "some-link.txt";
    Files.createSymbolicLink(Paths.get(testDir + pathSep + linkName), Paths.get(fileName));
    testProps(linkName, true, true, st -> {
      assertNotNull(st != null);
      assertTrue(st.isSymbolicLink());
    });
    await();
  }

  private void testProps(String fileName, boolean link, boolean shouldPass,
                         Handler<FileProps> afterOK) throws Exception {
    AsyncResultHandler<FileProps> handler = ar -> {
      if (ar.failed()) {
        if (shouldPass) {
          fail(ar.cause().getMessage());
        } else {
          assertTrue(ar.cause() instanceof io.vertx.core.file.FileSystemException);
          if (afterOK != null) {
            afterOK.handle(ar.result());
          }
          testComplete();
        }
      } else {
        if (shouldPass) {
          if (afterOK != null) {
            afterOK.handle(ar.result());
          }
          testComplete();
        } else {
          fail("stat should fail");
        }
      }
    };
    if (link) {
      vertx.fileSystem().lprops(testDir + pathSep + fileName, handler);
    } else {
      vertx.fileSystem().props(testDir + pathSep + fileName, handler);
    }
  }

  @Test
  public void testLink() throws Exception {
    String fileName = "some-file.txt";
    long fileSize = 1234;
    createFileWithJunk(fileName, fileSize);
    String linkName = "some-link.txt";
    testLink(linkName, fileName, false, true, v -> {
      assertEquals(fileSize, fileLength(linkName));
      assertFalse(Files.isSymbolicLink(Paths.get(testDir + pathSep + linkName)));
    });
    await();
  }

  @Test
  public void testSymLink() throws Exception {
    // Symlinks require a modified security policy in Windows. -- See http://stackoverflow.com/questions/23217460/how-to-create-soft-symbolic-link-using-java-nio-files
    Assume.assumeFalse(Utils.isWindows());
    String fileName = "some-file.txt";
    long fileSize = 1234;
    createFileWithJunk(fileName, fileSize);
    String symlinkName = "some-sym-link.txt";
    testLink(symlinkName, fileName, true, true, v -> {
      assertEquals(fileSize, fileLength(symlinkName));
      assertTrue(Files.isSymbolicLink(Paths.get(testDir + pathSep + symlinkName)));
      // Now try reading it
      String read = vertx.fileSystem().readSymlinkBlocking(testDir + pathSep + symlinkName);
      assertEquals(fileName, read);
    });
    await();
  }

  private void testLink(String from, String to, boolean symbolic,
                        boolean shouldPass, Handler<Void> afterOK) throws Exception {
    if (symbolic) {
      // Symlink is relative
      vertx.fileSystem().symlink(testDir + pathSep + from, to, createHandler(shouldPass, afterOK));
    } else {
      vertx.fileSystem().link(testDir + pathSep + from, testDir + pathSep + to, createHandler(shouldPass, afterOK));
    }
  }

  @Test
  public void testUnlink() throws Exception {
    String fileName = "some-file.txt";
    long fileSize = 1234;
    createFileWithJunk(fileName, fileSize);
    String linkName = "some-link.txt";
    Files.createLink(Paths.get(testDir + pathSep + linkName), Paths.get(testDir + pathSep + fileName));
    assertEquals(fileSize, fileLength(linkName));
    vertx.fileSystem().unlink(testDir + pathSep + linkName, createHandler(true, v -> assertFalse(fileExists(linkName))));
    await();
  }

  @Test
  public void testReadSymLink() throws Exception {
    // Symlinks require a modified security policy in Windows. -- See http://stackoverflow.com/questions/23217460/how-to-create-soft-symbolic-link-using-java-nio-files
    Assume.assumeFalse(Utils.isWindows());
    String fileName = "some-file.txt";
    long fileSize = 1234;
    createFileWithJunk(fileName, fileSize);
    String linkName = "some-link.txt";
    Files.createSymbolicLink(Paths.get(testDir + pathSep + linkName), Paths.get(fileName));
    vertx.fileSystem().readSymlink(testDir + pathSep + linkName, ar -> {
      if (ar.failed()) {
        fail(ar.cause().getMessage());
      } else {
        assertEquals(fileName, ar.result());
        testComplete();
      }
    });
    await();
  }

  @Test
  public void testSimpleDelete() throws Exception {
    String fileName = "some-file.txt";
    createFileWithJunk(fileName, 100);
    assertTrue(fileExists(fileName));
    testDelete(fileName, false, true, v -> {
      assertFalse(fileExists(fileName));
    });
    await();
  }

  @Test
  public void testDeleteEmptyDir() throws Exception {
    String dirName = "some-dir";
    mkDir(dirName);
    assertTrue(fileExists(dirName));
    testDelete(dirName, false, true, v -> {
      assertFalse(fileExists(dirName));
    });
    await();
  }

  @Test
  public void testDeleteNonExistent() throws Exception {
    String dirName = "some-dir";
    assertFalse(fileExists(dirName));
    testDelete(dirName, false, false, null);
    await();
  }

  @Test
  public void testDeleteNonEmptyFails() throws Exception {
    String dirName = "some-dir";
    mkDir(dirName);
    String file1 = "some-file.txt";
    createFileWithJunk(dirName + pathSep + file1, 100);
    testDelete(dirName, false, false, null);
    await();
  }

  @Test
  public void testDeleteRecursive() throws Exception {
    String dir = "some-dir";
    String file1 = pathSep + "file1.dat";
    String file2 = pathSep + "index.html";
    String dir2 = "next-dir";
    String file3 = pathSep + "blah.java";
    mkDir(dir);
    createFileWithJunk(dir + file1, 100);
    createFileWithJunk(dir + file2, 100);
    mkDir(dir + pathSep + dir2);
    createFileWithJunk(dir + pathSep + dir2 + file3, 100);
    testDelete(dir, true, true, v -> {
      assertFalse(fileExists(dir));
    });
    await();
  }

  private void testDelete(String fileName, boolean recursive, boolean shouldPass,
                          Handler<Void> afterOK) throws Exception {
    if (recursive) {
      vertx.fileSystem().deleteRecursive(testDir + pathSep + fileName, recursive, createHandler(shouldPass, afterOK));
    } else {
      vertx.fileSystem().delete(testDir + pathSep + fileName, createHandler(shouldPass, afterOK));
    }
  }

  @Test
  public void testMkdirSimple() throws Exception {
    String dirName = "some-dir";
    testMkdir(dirName, null, false, true, v -> {
      assertTrue(fileExists(dirName));
      assertTrue(Files.isDirectory(Paths.get(testDir + pathSep + dirName)));
    });
    await();
  }

  @Test
  public void testMkdirWithParentsFails() throws Exception {
    String dirName = "top-dir" + pathSep + "some-dir";
    testMkdir(dirName, null, false, false, null);
    await();
  }

  @Test
  public void testMkdirWithPerms() throws Exception {
    String dirName = "some-dir";
    String perms = "rwx--x--x";
    testMkdir(dirName, perms, false, true, v -> {
      assertTrue(fileExists(dirName));
      assertTrue(Files.isDirectory(Paths.get(testDir + pathSep + dirName)));
      azzertPerms(perms, dirName);
    });
    await();
  }

  @Test
  public void testMkdirCreateParents() throws Exception {
    String dirName = "top-dir" + pathSep + "/some-dir";
    testMkdir(dirName, null, true, true, v -> {
      assertTrue(fileExists(dirName));
      assertTrue(Files.isDirectory(Paths.get(testDir + pathSep + dirName)));
    });
    await();
  }

  @Test
  public void testMkdirCreateParentsWithPerms() throws Exception {
    String dirName = "top-dir" + pathSep + "/some-dir";
    String perms = "rwx--x--x";
    testMkdir(dirName, perms, true, true, v -> {
      assertTrue(fileExists(dirName));
      assertTrue(Files.isDirectory(Paths.get(testDir + pathSep + dirName)));
      azzertPerms(perms, dirName);
    });
    await();
  }

  private void testMkdir(String dirName, String perms, boolean createParents,
                         boolean shouldPass, Handler<Void> afterOK) throws Exception {
    AsyncResultHandler<Void> handler = createHandler(shouldPass, afterOK);
    if (createParents) {
      if (perms != null) {
        vertx.fileSystem().mkdirs(testDir + pathSep + dirName, perms, handler);
      } else {
        vertx.fileSystem().mkdirs(testDir + pathSep + dirName, handler);
      }
    } else {
      if (perms != null) {
        vertx.fileSystem().mkdir(testDir + pathSep + dirName, perms, handler);
      } else {
        vertx.fileSystem().mkdir(testDir + pathSep + dirName, handler);
      }
    }
  }

  @Test
  public void testReadDirSimple() throws Exception {
    String dirName = "some-dir";
    mkDir(dirName);
    int numFiles = 10;
    for (int i = 0; i < numFiles; i++) {
      createFileWithJunk(dirName + pathSep + "file-" + i + ".dat", 100);
    }
    testReadDir(dirName, null, true, fileNames -> {
      assertEquals(numFiles, fileNames.size());
      Set<String> fset = new HashSet<String>();
      for (String fileName: fileNames) {
        fset.add(fileName);
      }
      File dir = new File(testDir + pathSep + dirName);
      String root;
      try {
        root = dir.getCanonicalPath();
      } catch (IOException e) {
        fail(e.getMessage());
        return;
      }
      for (int i = 0; i < numFiles; i++) {
        assertTrue(fset.contains(root + pathSep + "file-" + i + ".dat"));
      }
    });
    await();
  }

  @Test
  public void testReadDirWithFilter() throws Exception {
    String dirName = "some-dir";
    mkDir(dirName);
    int numFiles = 10;
    for (int i = 0; i < numFiles; i++) {
      createFileWithJunk(dirName + pathSep + "foo-" + i + ".txt", 100);
    }
    for (int i = 0; i < numFiles; i++) {
      createFileWithJunk(dirName + pathSep + "bar-" + i + ".txt", 100);
    }
    testReadDir(dirName, "foo.+", true, fileNames -> {
      assertEquals(numFiles, fileNames.size());
      Set<String> fset = new HashSet<>();
      for (String fileName: fileNames) {
        fset.add(fileName);
      }
      File dir = new File(testDir + pathSep + dirName);
      String root;
      try {
        root = dir.getCanonicalPath();
      } catch (IOException e) {
        fail(e.getMessage());
        return;
      }
      for (int i = 0; i < numFiles; i++) {
        assertTrue(fset.contains(root + pathSep + "foo-" + i + ".txt"));
      }
    });
    await();
  }

  private void testReadDir(String dirName, String filter, boolean shouldPass,
                           Handler<List<String>> afterOK) throws Exception {
    AsyncResultHandler<List<String>> handler = ar -> {
      if (ar.failed()) {
        if (shouldPass) {
          fail(ar.cause().getMessage());
        } else {
          assertTrue(ar.cause() instanceof FileSystemException);
          if (afterOK != null) {
            afterOK.handle(null);
          }
          testComplete();
        }
      } else {
        if (shouldPass) {
          if (afterOK != null) {
            afterOK.handle(ar.result());
          }
          testComplete();
        } else {
          fail("read should fail");
        }
      }
    };
    if (filter == null) {
      vertx.fileSystem().readDir(testDir + pathSep + dirName, handler);
    } else {
      vertx.fileSystem().readDir(testDir + pathSep + dirName, filter, handler);
    }
  }

  @Test
  public void testReadFile() throws Exception {
    byte[] content = TestUtils.randomByteArray(1000);
    String fileName = "some-file.dat";
    createFile(fileName, content);

    vertx.fileSystem().readFile(testDir + pathSep + fileName, ar -> {
      if (ar.failed()) {
        fail(ar.cause().getMessage());
      } else {
        assertEquals(Buffer.buffer(content), ar.result());
        testComplete();
      }
    });
    await();
  }

  @Test
  public void testWriteFile() throws Exception {
    byte[] content = TestUtils.randomByteArray(1000);
    Buffer buff = Buffer.buffer(content);
    String fileName = "some-file.dat";
    vertx.fileSystem().writeFile(testDir + pathSep + fileName, buff, ar -> {
      if (ar.failed()) {
        fail(ar.cause().getMessage());
      } else {
        assertTrue(fileExists(fileName));
        assertEquals(content.length, fileLength(fileName));
        byte[] readBytes;
        try {
          readBytes = Files.readAllBytes(Paths.get(testDir + pathSep + fileName));
        } catch (IOException e) {
          fail(e.getMessage());
          return;
        }
        assertEquals(buff, Buffer.buffer(readBytes));
        testComplete();
      }
    });
    await();
  }

  @Test
  public void testWriteAsync() throws Exception {
    String fileName = "some-file.dat";
    int chunkSize = 1000;
    int chunks = 10;
    byte[] content = TestUtils.randomByteArray(chunkSize * chunks);
    Buffer buff = Buffer.buffer(content);
    AtomicInteger count = new AtomicInteger();
    vertx.fileSystem().open(testDir + pathSep + fileName, new OpenOptions(), arr -> {
      if (arr.succeeded()) {
        for (int i = 0; i < chunks; i++) {
          Buffer chunk = buff.getBuffer(i * chunkSize, (i + 1) * chunkSize);
          assertEquals(chunkSize, chunk.length());
          arr.result().write(chunk, i * chunkSize, ar -> {
            if (ar.succeeded()) {
              if (count.incrementAndGet() == chunks) {
                arr.result().close(ar2 -> {
                  if (ar2.failed()) {
                    fail(ar2.cause().getMessage());
                  } else {
                    assertTrue(fileExists(fileName));
                    byte[] readBytes;
                    try {
                      readBytes = Files.readAllBytes(Paths.get(testDir + pathSep + fileName));
                    } catch (IOException e) {
                      fail(e.getMessage());
                      return;
                    }
                    Buffer read = Buffer.buffer(readBytes);
                    assertEquals(buff, read);
                    testComplete();
                  }
                });
              }
            } else {
              fail(ar.cause().getMessage());
            }
          });
        }
      } else {
        fail(arr.cause().getMessage());
      }
    });
    await();
  }

  @Test
  public void testReadAsync() throws Exception {
    String fileName = "some-file.dat";
    int chunkSize = 1000;
    int chunks = 10;
    byte[] content = TestUtils.randomByteArray(chunkSize * chunks);
    Buffer expected = Buffer.buffer(content);
    createFile(fileName, content);
    AtomicInteger reads = new AtomicInteger();
    vertx.fileSystem().open(testDir + pathSep + fileName, new OpenOptions(), arr -> {
      if (arr.succeeded()) {
        Buffer buff = Buffer.buffer(chunks * chunkSize);
        for (int i = 0; i < chunks; i++) {
          arr.result().read(buff, i * chunkSize, i * chunkSize, chunkSize, arb -> {
            if (arb.succeeded()) {
              if (reads.incrementAndGet() == chunks) {
                arr.result().close(ar -> {
                  if (ar.failed()) {
                    fail(ar.cause().getMessage());
                  } else {
                    assertEquals(expected, buff);
                    assertEquals(buff, arb.result());
                    testComplete();
                  }
                });
              }
            } else {
              fail(arb.cause().getMessage());
            }
          });
        }
      } else {
        fail(arr.cause().getMessage());
      }
    });
    await();
  }

  @Test
  public void testWriteStream() throws Exception {
    String fileName = "some-file.dat";
    int chunkSize = 1000;
    int chunks = 10;
    byte[] content = TestUtils.randomByteArray(chunkSize * chunks);
    Buffer buff = Buffer.buffer(content);
    vertx.fileSystem().open(testDir + pathSep + fileName, new OpenOptions(), ar -> {
      if (ar.succeeded()) {
        WriteStream<Buffer> ws = ar.result();
        ws.exceptionHandler(t -> fail(t.getMessage()));
        for (int i = 0; i < chunks; i++) {
          Buffer chunk = buff.getBuffer(i * chunkSize, (i + 1) * chunkSize);
          assertEquals(chunkSize, chunk.length());
          ws.write(chunk);
        }
        ar.result().close(ar2 -> {
          if (ar2.failed()) {
            fail(ar2.cause().getMessage());
          } else {
            assertTrue(fileExists(fileName));
            byte[] readBytes;
            try {
              readBytes = Files.readAllBytes(Paths.get(testDir + pathSep + fileName));
            } catch (IOException e) {
              fail(e.getMessage());
              return;
            }
            assertEquals(buff, Buffer.buffer(readBytes));
            testComplete();
          }
        });
      } else {
        fail(ar.cause().getMessage());
      }
    });
    await();
  }

  @Test
  public void testWriteStreamAppend() throws Exception {
    String fileName = "some-file.dat";
    int chunkSize = 1000;
    int chunks = 10;
    byte[] existing = TestUtils.randomByteArray(1000);
    createFile(fileName, existing);
    byte[] content = TestUtils.randomByteArray(chunkSize * chunks);
    Buffer buff = Buffer.buffer(content);
    vertx.fileSystem().open(testDir + pathSep + fileName, new OpenOptions(), ar -> {
      if (ar.succeeded()) {
        AsyncFile ws = ar.result();
        long size = vertx.fileSystem().propsBlocking(testDir + pathSep + fileName).size();
        ws.setWritePos(size);
        ws.exceptionHandler(t -> fail(t.getMessage()));
        for (int i = 0; i < chunks; i++) {
          Buffer chunk = buff.getBuffer(i * chunkSize, (i + 1) * chunkSize);
          assertEquals(chunkSize, chunk.length());
          ws.write(chunk);
        }
        ar.result().close(ar2 -> {
          if (ar2.failed()) {
            fail(ar2.cause().getMessage());
          } else {
            assertTrue(fileExists(fileName));
            byte[] readBytes;
            try {
              readBytes = Files.readAllBytes(Paths.get(testDir + pathSep + fileName));
            } catch (IOException e) {
              fail(e.getMessage());
              return;
            }
            assertEquals(Buffer.buffer(existing).appendBuffer(buff), Buffer.buffer(readBytes));
            testComplete();
          }
        });
      } else {
        fail(ar.cause().getMessage());
      }
    });
    await();
  }

  @Test
  public void testWriteStreamWithCompositeBuffer() throws Exception {
    String fileName = "some-file.dat";
    int chunkSize = 1000;
    int chunks = 10;
    byte[] content1 = TestUtils.randomByteArray(chunkSize * (chunks / 2));
    byte[] content2 = TestUtils.randomByteArray(chunkSize * (chunks / 2));
    ByteBuf byteBuf = Unpooled.wrappedBuffer(content1, content2);
    Buffer buff = Buffer.buffer(byteBuf);
    vertx.fileSystem().open(testDir + pathSep + fileName, new OpenOptions(), ar -> {
      if (ar.succeeded()) {
        WriteStream<Buffer> ws = ar.result();
        ws.exceptionHandler(t -> fail(t.getMessage()));
        ws.write(buff);
        ar.result().close(ar2 -> {
          if (ar2.failed()) {
            fail(ar2.cause().getMessage());
          } else {
            assertTrue(fileExists(fileName));
            byte[] readBytes;
            try {
              readBytes = Files.readAllBytes(Paths.get(testDir + pathSep + fileName));
            } catch (IOException e) {
              fail(e.getMessage());
              return;
            }
            assertEquals(buff, Buffer.buffer(readBytes));
            byteBuf.release();
            testComplete();
          }
        });
      } else {
        fail(ar.cause().getMessage());
      }
    });
    await();
  }

  @Test
  public void testReadStream() throws Exception {
    String fileName = "some-file.dat";
    int chunkSize = 1000;
    int chunks = 10;
    byte[] content = TestUtils.randomByteArray(chunkSize * chunks);
    createFile(fileName, content);
    vertx.fileSystem().open(testDir + pathSep + fileName, new OpenOptions(), ar -> {
      if (ar.succeeded()) {
        ReadStream<Buffer> rs = ar.result();
        Buffer buff = Buffer.buffer();
        rs.handler(buff::appendBuffer);
        rs.exceptionHandler(t -> fail(t.getMessage()));
        rs.endHandler(v -> {
          ar.result().close(ar2 -> {
            if (ar2.failed()) {
              fail(ar2.cause().getMessage());
            } else {
              assertEquals(Buffer.buffer(content), buff);
              testComplete();
            }
          });
        });
      } else {
        fail(ar.cause().getMessage());
      }
    });
    await();
  }

  @Test
  public void testReadStreamSetReadPos() throws Exception {
    String fileName = "some-file.dat";
    int chunkSize = 1000;
    int chunks = 10;
    byte[] content = TestUtils.randomByteArray(chunkSize * chunks);
    createFile(fileName, content);
    vertx.fileSystem().open(testDir + pathSep + fileName, new OpenOptions(), ar -> {
      if (ar.succeeded()) {
        AsyncFile rs = ar.result();
        rs.setReadPos(chunkSize * chunks / 2);
        Buffer buff = Buffer.buffer();
        rs.handler(buff::appendBuffer);
        rs.exceptionHandler(t -> fail(t.getMessage()));
        rs.endHandler(v -> {
          ar.result().close(ar2 -> {
            if (ar2.failed()) {
              fail(ar2.cause().getMessage());
            } else {
              assertEquals(chunkSize * chunks / 2, buff.length());
              byte[] lastHalf = new byte[chunkSize * chunks / 2];
              System.arraycopy(content, chunkSize * chunks / 2, lastHalf, 0, chunkSize * chunks / 2);
              assertEquals(Buffer.buffer(lastHalf), buff);
              testComplete();
            }
          });
        });
      } else {
        fail(ar.cause().getMessage());
      }
    });
    await();
  }

  @Test
  @SuppressWarnings("unchecked")
  public void testPumpFileStreams() throws Exception {
    String fileName1 = "some-file.dat";
    String fileName2 = "some-other-file.dat";

    //Non integer multiple of buffer size
    int fileSize = (int) (AsyncFileImpl.BUFFER_SIZE * 1000.3);
    byte[] content = TestUtils.randomByteArray(fileSize);
    createFile(fileName1, content);

    vertx.fileSystem().open(testDir + pathSep + fileName1, new OpenOptions(), arr -> {
      if (arr.succeeded()) {
        ReadStream rs = arr.result();
        //Open file for writing
        vertx.fileSystem().open(testDir + pathSep + fileName2, new OpenOptions(), ar -> {
          if (ar.succeeded()) {
            WriteStream ws = ar.result();
            Pump p = Pump.pump(rs, ws);
            p.start();
            rs.endHandler(v -> {
              arr.result().close(car -> {
                if (car.failed()) {
                  fail(ar.cause().getMessage());
                } else {
                  ar.result().close(ar2 -> {
                    if (ar2.failed()) {
                      fail(ar2.cause().getMessage());
                    } else {
                      assertTrue(fileExists(fileName2));
                      byte[] readBytes;
                      try {
                        readBytes = Files.readAllBytes(Paths.get(testDir + pathSep + fileName2));
                      } catch (IOException e) {
                        fail(e.getMessage());
                        return;
                      }
                      assertEquals(Buffer.buffer(content), Buffer.buffer(readBytes));
                      testComplete();
                    }
                  });
                }
              });
            });
          } else {
            fail(ar.cause().getMessage());
          }
        });
      } else {
        fail(arr.cause().getMessage());
      }
    });
    await();
  }

  @Test
  public void testCreateFileNoPerms() throws Exception {
    testCreateFile(null, true);
  }

  @Test
  public void testCreateFileWithPerms() throws Exception {
    testCreateFile("rwx------", true);
  }

  @Test
  public void testCreateFileAlreadyExists() throws Exception {
    createFileWithJunk("some-file.dat", 100);
    testCreateFile(null, false);
  }

  private void testCreateFile(String perms, boolean shouldPass) throws Exception {
    String fileName = "some-file.dat";
    AsyncResultHandler<Void> handler = ar -> {
      if (ar.failed()) {
        if (shouldPass) {
          fail(ar.cause().getMessage());
        } else {
          assertTrue(ar.cause() instanceof FileSystemException);
          testComplete();
        }
      } else {
        if (shouldPass) {
          assertTrue(fileExists(fileName));
          assertEquals(0, fileLength(fileName));
          if (perms != null) {
            azzertPerms(perms, fileName);
          }
          testComplete();
        } else {
          fail("test should fail");
        }
      }
    };
    if (perms != null) {
      vertx.fileSystem().createFile(testDir + pathSep + fileName, perms, handler);
    } else {
      vertx.fileSystem().createFile(testDir + pathSep + fileName, handler);
    }
    await();
  }

  @Test
  public void testExists() throws Exception {
    testExists(true);
  }

  @Test
  public void testNotExists() throws Exception {
    testExists(false);
  }

  private void testExists(boolean exists) throws Exception {
    String fileName = "some-file.dat";
    if (exists) {
      createFileWithJunk(fileName, 100);
    }
    vertx.fileSystem().exists(testDir + pathSep + fileName, ar -> {
      if (ar.succeeded()) {
        if (exists) {
          assertTrue(ar.result());
        } else {
          assertFalse(ar.result());
        }
        testComplete();
      } else {
        fail(ar.cause().getMessage());
      }
    });
    await();
  }

  @Test
  public void testFSProps() throws Exception {
    String fileName = "some-file.txt";
    createFileWithJunk(fileName, 1234);
    testFSProps(fileName, props -> {
      assertTrue(props.totalSpace() > 0);
      assertTrue(props.unallocatedSpace() > 0);
      assertTrue(props.usableSpace() > 0);
    });
    await();
  }

  private void testFSProps(String fileName,
                           Handler<FileSystemProps> afterOK) throws Exception {
    vertx.fileSystem().fsProps(testDir + pathSep + fileName, ar -> {
      if (ar.failed()) {
        fail(ar.cause().getMessage());
      } else {
        afterOK.handle(ar.result());
        testComplete();
      }
    });
  }

  @Test
  public void testOpenOptions() {
    OpenOptions opts = new OpenOptions();
    assertNull(opts.getPerms());
    String perms = "rwxrwxrwx";
    assertEquals(opts, opts.setPerms(perms));
    assertEquals(perms, opts.getPerms());
    assertTrue(opts.isCreate());
    assertEquals(opts, opts.setCreate(false));
    assertFalse(opts.isCreate());
    assertFalse(opts.isCreateNew());
    assertEquals(opts, opts.setCreateNew(true));
    assertTrue(opts.isCreateNew());
    assertTrue(opts.isRead());
    assertEquals(opts, opts.setRead(false));
    assertFalse(opts.isRead());
    assertTrue(opts.isWrite());
    assertEquals(opts, opts.setWrite(false));
    assertFalse(opts.isWrite());
    assertFalse(opts.isDSync());
    assertEquals(opts, opts.setDSync(true));
    assertTrue(opts.isDSync());
    assertFalse(opts.isSync());
    assertEquals(opts, opts.setSync(true));
    assertTrue(opts.isSync());
    assertFalse(opts.isDeleteOnClose());
    assertEquals(opts, opts.setDeleteOnClose(true));
    assertTrue(opts.isDeleteOnClose());
    assertFalse(opts.isTruncateExisting());
    assertEquals(opts, opts.setTruncateExisting(true));
    assertTrue(opts.isTruncateExisting());
    assertFalse(opts.isSparse());
    assertEquals(opts, opts.setSparse(true));
    assertTrue(opts.isSparse());
  }

  @Test
  public void testDefaultOptionOptions() {
    OpenOptions def = new OpenOptions();
    OpenOptions json = new OpenOptions(new JsonObject());
    assertEquals(def.getPerms(), json.getPerms());
    assertEquals(def.isRead(), json.isRead());
    assertEquals(def.isWrite(), json.isWrite());
    assertEquals(def.isCreate(), json.isCreate());
    assertEquals(def.isCreateNew(), json.isCreateNew());
    assertEquals(def.isDeleteOnClose(), json.isDeleteOnClose());
    assertEquals(def.isTruncateExisting(), json.isTruncateExisting());
    assertEquals(def.isSparse(), json.isSparse());
    assertEquals(def.isSync(), json.isSync());
    assertEquals(def.isDSync(), json.isDSync());
  }

  @Test
  public void testAsyncFileCloseHandlerIsAsync() throws Exception {
    String fileName = "some-file.dat";
    createFileWithJunk(fileName, 100);
    AsyncFile file = vertx.fileSystem().openBlocking(testDir + pathSep + fileName, new OpenOptions());
    ThreadLocal stack = new ThreadLocal();
    stack.set(true);
    file.close(ar -> {
      assertNull(stack.get());
      assertTrue(Vertx.currentContext().isEventLoopContext());
      testComplete();
    });
    await();
  }

  private AsyncResultHandler<Void> createHandler(boolean shouldPass, Handler<Void> afterOK) {
    return ar -> {
      if (ar.failed()) {
        if (shouldPass) {
          fail(ar.cause().getMessage());
        } else {
          assertTrue(ar.cause() instanceof FileSystemException);
          if (afterOK != null) {
            afterOK.handle(null);
          }
          testComplete();
        }
      } else {
        if (shouldPass) {
          if (afterOK != null) {
            afterOK.handle(null);
          }
          testComplete();
        } else {
          fail("operation should fail");
        }
      }
    };
  }

  // Helper methods

  private boolean fileExists(String fileName) {
    File file = new File(testDir, fileName);
    return file.exists();
  }

  private void createFileWithJunk(String fileName, long length) throws Exception {
    createFile(fileName, TestUtils.randomByteArray((int) length));
  }

  private void createFile(String fileName, byte[] bytes) throws Exception {
    File file = new File(testDir, fileName);
    Path path = Paths.get(file.getCanonicalPath());
    Files.write(path, bytes);

    setPerms( path, DEFAULT_FILE_PERMS );
  }

  private void deleteDir(File dir) {
    File[] files = dir.listFiles();
    for (int i = 0; i < files.length; i++) {
      if (files[i].isDirectory()) {
        deleteDir(files[i]);
      } else {
        files[i].delete();
      }
    }
    dir.delete();
  }

  private void deleteDir(String dir) {
    deleteDir(new File(testDir + pathSep + dir));
  }

  private void mkDir(String dirName) throws Exception {
    File dir = new File(testDir + pathSep + dirName);
    dir.mkdir();

    setPerms( Paths.get( dir.getCanonicalPath() ), DEFAULT_DIR_PERMS );
  }

  private long fileLength(String fileName) {
    File file = new File(testDir, fileName);
    return file.length();
  }

  private void setPerms(Path path, String perms) {
    if (Utils.isWindows() == false) {
      try {
        Files.setPosixFilePermissions( path, PosixFilePermissions.fromString(perms) );
      }
      catch(IOException e) {
        throw new RuntimeException(e.getMessage());
      }
    }
  }

  private String getPerms(String fileName) {
    try {
      Set<PosixFilePermission> perms = Files.getPosixFilePermissions(Paths.get(testDir + pathSep + fileName));
      return PosixFilePermissions.toString(perms);
    } catch (Exception e) {
      throw new RuntimeException(e.getMessage());
    }
  }

  private void deleteFile(String fileName) {
    File file = new File(testDir + pathSep + fileName);
    file.delete();
  }
}


File: src/test/java/io/vertx/test/core/HttpTest.java
/*
 * Copyright (c) 2011-2013 The original author or authors
 * ------------------------------------------------------
 * All rights reserved. This program and the accompanying materials
 * are made available under the terms of the Eclipse Public License v1.0
 * and Apache License v2.0 which accompanies this distribution.
 *
 *     The Eclipse Public License is available at
 *     http://www.eclipse.org/legal/epl-v10.html
 *
 *     The Apache License v2.0 is available at
 *     http://www.opensource.org/licenses/apache2.0.php
 *
 * You may elect to redistribute this code under either of these licenses.
 */

package io.vertx.test.core;

import io.netty.handler.codec.http.DefaultHttpHeaders;
import io.netty.handler.codec.http.HttpResponseStatus;
import io.vertx.core.*;
import io.vertx.core.buffer.Buffer;
import io.vertx.core.eventbus.Message;
import io.vertx.core.eventbus.MessageConsumer;
import io.vertx.core.http.*;
import io.vertx.core.http.impl.HeadersAdaptor;
import io.vertx.core.impl.*;
import io.vertx.core.json.JsonArray;
import io.vertx.core.json.JsonObject;
import io.vertx.core.net.*;
import io.vertx.core.net.impl.SocketDefaults;
import io.vertx.core.streams.Pump;
import org.junit.Assume;
import org.junit.Rule;
import org.junit.Test;
import org.junit.rules.TemporaryFolder;

import java.io.*;
import java.net.URLEncoder;
import java.nio.file.Files;
import java.nio.file.NoSuchFileException;
import java.nio.file.Path;
import java.util.*;
import java.util.concurrent.ConcurrentHashMap;
import java.util.concurrent.CountDownLatch;
import java.util.concurrent.TimeUnit;
import java.util.concurrent.TimeoutException;
import java.util.concurrent.atomic.AtomicBoolean;
import java.util.concurrent.atomic.AtomicInteger;
import java.util.concurrent.atomic.AtomicReference;
import java.util.function.Consumer;

import static io.vertx.test.core.TestUtils.*;

/**
 *
 * @author <a href="http://tfox.org">Tim Fox</a>
 * @author <a href="mailto:nscavell@redhat.com">Nick Scavelli</a>
 */
public class HttpTest extends HttpTestBase {

  @Rule
  public TemporaryFolder testFolder = new TemporaryFolder();

  private File testDir;

  @Override
  public void setUp() throws Exception {
    super.setUp();
    testDir = testFolder.newFolder();
    server = vertx.createHttpServer(new HttpServerOptions().setPort(DEFAULT_HTTP_PORT).setHost(DEFAULT_HTTP_HOST)
                                        .setHandle100ContinueAutomatically(true));
    client = vertx.createHttpClient(new HttpClientOptions());
  }

  @Test
  public void testClientOptions() {
    HttpClientOptions options = new HttpClientOptions();

    assertEquals(NetworkOptions.DEFAULT_SEND_BUFFER_SIZE, options.getSendBufferSize());
    int rand = TestUtils.randomPositiveInt();
    assertEquals(options, options.setSendBufferSize(rand));
    assertEquals(rand, options.getSendBufferSize());
    assertIllegalArgumentException(() -> options.setSendBufferSize(0));
    assertIllegalArgumentException(() -> options.setSendBufferSize(-123));

    assertEquals(NetworkOptions.DEFAULT_RECEIVE_BUFFER_SIZE, options.getReceiveBufferSize());
    rand = TestUtils.randomPositiveInt();
    assertEquals(options, options.setReceiveBufferSize(rand));
    assertEquals(rand, options.getReceiveBufferSize());
    assertIllegalArgumentException(() -> options.setReceiveBufferSize(0));
    assertIllegalArgumentException(() -> options.setReceiveBufferSize(-123));

    assertTrue(options.isReuseAddress());
    assertEquals(options, options.setReuseAddress(false));
    assertFalse(options.isReuseAddress());

    assertEquals(NetworkOptions.DEFAULT_TRAFFIC_CLASS, options.getTrafficClass());
    rand = 23;
    assertEquals(options, options.setTrafficClass(rand));
    assertEquals(rand, options.getTrafficClass());
    assertIllegalArgumentException(() -> options.setTrafficClass(-1));
    assertIllegalArgumentException(() -> options.setTrafficClass(256));

    assertTrue(options.isTcpNoDelay());
    assertEquals(options, options.setTcpNoDelay(false));
    assertFalse(options.isTcpNoDelay());

    boolean tcpKeepAlive = SocketDefaults.instance.isTcpKeepAlive();
    assertEquals(tcpKeepAlive, options.isTcpKeepAlive());
    assertEquals(options, options.setTcpKeepAlive(!tcpKeepAlive));
    assertEquals(!tcpKeepAlive, options.isTcpKeepAlive());

    int soLinger = SocketDefaults.instance.getSoLinger();
    assertEquals(soLinger, options.getSoLinger());
    rand = TestUtils.randomPositiveInt();
    assertEquals(options, options.setSoLinger(rand));
    assertEquals(rand, options.getSoLinger());
    assertIllegalArgumentException(() -> options.setSoLinger(-1));

    assertFalse(options.isUsePooledBuffers());
    assertEquals(options, options.setUsePooledBuffers(true));
    assertTrue(options.isUsePooledBuffers());

    assertEquals(0, options.getIdleTimeout());
    assertEquals(options, options.setIdleTimeout(10));
    assertEquals(10, options.getIdleTimeout());
    assertIllegalArgumentException(() -> options.setIdleTimeout(-1));

    assertFalse(options.isSsl());
    assertEquals(options, options.setSsl(true));
    assertTrue(options.isSsl());

    assertNull(options.getKeyCertOptions());
    JksOptions keyStoreOptions = new JksOptions().setPath(TestUtils.randomAlphaString(100)).setPassword(TestUtils.randomAlphaString(100));
    assertEquals(options, options.setKeyStoreOptions(keyStoreOptions));
    assertEquals(keyStoreOptions, options.getKeyCertOptions());

    assertNull(options.getTrustOptions());
    JksOptions trustStoreOptions = new JksOptions().setPath(TestUtils.randomAlphaString(100)).setPassword(TestUtils.randomAlphaString(100));
    assertEquals(options, options.setTrustStoreOptions(trustStoreOptions));
    assertEquals(trustStoreOptions, options.getTrustOptions());

    assertFalse(options.isTrustAll());
    assertEquals(options, options.setTrustAll(true));
    assertTrue(options.isTrustAll());

    assertTrue(options.isVerifyHost());
    assertEquals(options, options.setVerifyHost(false));
    assertFalse(options.isVerifyHost());

    assertEquals(5, options.getMaxPoolSize());
    rand = TestUtils.randomPositiveInt();
    assertEquals(options, options.setMaxPoolSize(rand));
    assertEquals(rand, options.getMaxPoolSize());
    assertIllegalArgumentException(() -> options.setMaxPoolSize(0));
    assertIllegalArgumentException(() -> options.setMaxPoolSize(-1));

    assertTrue(options.isKeepAlive());
    assertEquals(options, options.setKeepAlive(false));
    assertFalse(options.isKeepAlive());

    assertFalse(options.isPipelining());
    assertEquals(options, options.setPipelining(true));
    assertTrue(options.isPipelining());

    assertEquals(60000, options.getConnectTimeout());
    rand = TestUtils.randomPositiveInt();
    assertEquals(options, options.setConnectTimeout(rand));
    assertEquals(rand, options.getConnectTimeout());
    assertIllegalArgumentException(() -> options.setConnectTimeout(-2));

    assertFalse(options.isTryUseCompression());
    assertEquals(options, options.setTryUseCompression(true));
    assertEquals(true, options.isTryUseCompression());

    assertTrue(options.getEnabledCipherSuites().isEmpty());
    assertEquals(options, options.addEnabledCipherSuite("foo"));
    assertEquals(options, options.addEnabledCipherSuite("bar"));
    assertNotNull(options.getEnabledCipherSuites());
    assertTrue(options.getEnabledCipherSuites().contains("foo"));
    assertTrue(options.getEnabledCipherSuites().contains("bar"));

    testComplete();
  }


  @Test
  public void testServerOptions() {
    HttpServerOptions options = new HttpServerOptions();

    assertEquals(NetworkOptions.DEFAULT_SEND_BUFFER_SIZE, options.getSendBufferSize());
    int rand = TestUtils.randomPositiveInt();
    assertEquals(options, options.setSendBufferSize(rand));
    assertEquals(rand, options.getSendBufferSize());
    assertIllegalArgumentException(() -> options.setSendBufferSize(0));
    assertIllegalArgumentException(() -> options.setSendBufferSize(-123));

    assertEquals(NetworkOptions.DEFAULT_RECEIVE_BUFFER_SIZE, options.getReceiveBufferSize());
    rand = TestUtils.randomPositiveInt();
    assertEquals(options, options.setReceiveBufferSize(rand));
    assertEquals(rand, options.getReceiveBufferSize());
    assertIllegalArgumentException(() -> options.setReceiveBufferSize(0));
    assertIllegalArgumentException(() -> options.setReceiveBufferSize(-123));

    assertTrue(options.isReuseAddress());
    assertEquals(options, options.setReuseAddress(false));
    assertFalse(options.isReuseAddress());

    assertEquals(NetworkOptions.DEFAULT_TRAFFIC_CLASS, options.getTrafficClass());
    rand = 23;
    assertEquals(options, options.setTrafficClass(rand));
    assertEquals(rand, options.getTrafficClass());
    assertIllegalArgumentException(() -> options.setTrafficClass(-1));
    assertIllegalArgumentException(() -> options.setTrafficClass(256));

    assertTrue(options.isTcpNoDelay());
    assertEquals(options, options.setTcpNoDelay(false));
    assertFalse(options.isTcpNoDelay());

    boolean tcpKeepAlive = SocketDefaults.instance.isTcpKeepAlive();
    assertEquals(tcpKeepAlive, options.isTcpKeepAlive());
    assertEquals(options, options.setTcpKeepAlive(!tcpKeepAlive));
    assertEquals(!tcpKeepAlive, options.isTcpKeepAlive());

    int soLinger = SocketDefaults.instance.getSoLinger();
    assertEquals(soLinger, options.getSoLinger());
    rand = TestUtils.randomPositiveInt();
    assertEquals(options, options.setSoLinger(rand));
    assertEquals(rand, options.getSoLinger());
    assertIllegalArgumentException(() -> options.setSoLinger(-1));

    assertFalse(options.isUsePooledBuffers());
    assertEquals(options, options.setUsePooledBuffers(true));
    assertTrue(options.isUsePooledBuffers());

    assertEquals(0, options.getIdleTimeout());
    assertEquals(options, options.setIdleTimeout(10));
    assertEquals(10, options.getIdleTimeout());
    assertIllegalArgumentException(() -> options.setIdleTimeout(-1));

    assertFalse(options.isSsl());
    assertEquals(options, options.setSsl(true));
    assertTrue(options.isSsl());

    assertNull(options.getKeyCertOptions());
    JksOptions keyStoreOptions = new JksOptions().setPath(TestUtils.randomAlphaString(100)).setPassword(TestUtils.randomAlphaString(100));
    assertEquals(options, options.setKeyStoreOptions(keyStoreOptions));
    assertEquals(keyStoreOptions, options.getKeyCertOptions());

    assertNull(options.getTrustOptions());
    JksOptions trustStoreOptions = new JksOptions().setPath(TestUtils.randomAlphaString(100)).setPassword(TestUtils.randomAlphaString(100));
    assertEquals(options, options.setTrustStoreOptions(trustStoreOptions));
    assertEquals(trustStoreOptions, options.getTrustOptions());

    assertEquals(1024, options.getAcceptBacklog());
    rand = TestUtils.randomPositiveInt();
    assertEquals(options, options.setAcceptBacklog(rand));
    assertEquals(rand, options.getAcceptBacklog());

    assertFalse(options.isCompressionSupported());
    assertEquals(options, options.setCompressionSupported(true));
    assertTrue(options.isCompressionSupported());

    assertEquals(65536, options.getMaxWebsocketFrameSize());
    rand = TestUtils.randomPositiveInt();
    assertEquals(options, options.setMaxWebsocketFrameSize(rand));
    assertEquals(rand, options.getMaxWebsocketFrameSize());

    assertEquals(80, options.getPort());
    assertEquals(options, options.setPort(1234));
    assertEquals(1234, options.getPort());
    assertIllegalArgumentException(() -> options.setPort(-1));
    assertIllegalArgumentException(() -> options.setPort(65536));

    assertEquals("0.0.0.0", options.getHost());
    String randString = TestUtils.randomUnicodeString(100);
    assertEquals(options, options.setHost(randString));
    assertEquals(randString, options.getHost());

    assertNull(options.getWebsocketSubProtocols());
    assertEquals(options, options.setWebsocketSubProtocol("foo"));
    assertEquals("foo", options.getWebsocketSubProtocols());

    HttpServerOptions optionsCopy = new HttpServerOptions(options);
    assertEquals(options, optionsCopy.setWebsocketSubProtocol(new String(options.getWebsocketSubProtocols())));

    assertTrue(options.getEnabledCipherSuites().isEmpty());
    assertEquals(options, options.addEnabledCipherSuite("foo"));
    assertEquals(options, options.addEnabledCipherSuite("bar"));
    assertNotNull(options.getEnabledCipherSuites());
    assertTrue(options.getEnabledCipherSuites().contains("foo"));
    assertTrue(options.getEnabledCipherSuites().contains("bar"));

    assertFalse(options.isHandle100ContinueAutomatically());
    assertEquals(options, options.setHandle100ContinueAutomatically(true));
    assertTrue(options.isHandle100ContinueAutomatically());

    testComplete();
  }

  @Test
  public void testCopyClientOptions() {
    HttpClientOptions options = new HttpClientOptions();
    int sendBufferSize = TestUtils.randomPositiveInt();
    int receiverBufferSize = TestUtils.randomPortInt();
    Random rand = new Random();
    boolean reuseAddress = rand.nextBoolean();
    int trafficClass = TestUtils.randomByte() + 128;
    boolean tcpNoDelay = rand.nextBoolean();
    boolean tcpKeepAlive = rand.nextBoolean();
    int soLinger = TestUtils.randomPositiveInt();
    boolean usePooledBuffers = rand.nextBoolean();
    int idleTimeout = TestUtils.randomPositiveInt();
    boolean ssl = rand.nextBoolean();
    JksOptions keyStoreOptions = new JksOptions();
    String ksPassword = TestUtils.randomAlphaString(100);
    keyStoreOptions.setPassword(ksPassword);
    JksOptions trustStoreOptions = new JksOptions();
    String tsPassword = TestUtils.randomAlphaString(100);
    trustStoreOptions.setPassword(tsPassword);
    String enabledCipher = TestUtils.randomAlphaString(100);
    int connectTimeout = TestUtils.randomPositiveInt();
    boolean trustAll = rand.nextBoolean();
    String crlPath = TestUtils.randomUnicodeString(100);
    Buffer crlValue = TestUtils.randomBuffer(100);

    boolean verifyHost = rand.nextBoolean();
    int maxPoolSize = TestUtils.randomPositiveInt();
    boolean keepAlive = rand.nextBoolean();
    boolean pipelining = rand.nextBoolean();
    boolean tryUseCompression = rand.nextBoolean();

    options.setSendBufferSize(sendBufferSize);
    options.setReceiveBufferSize(receiverBufferSize);
    options.setReuseAddress(reuseAddress);
    options.setTrafficClass(trafficClass);
    options.setSsl(ssl);
    options.setTcpNoDelay(tcpNoDelay);
    options.setTcpKeepAlive(tcpKeepAlive);
    options.setSoLinger(soLinger);
    options.setUsePooledBuffers(usePooledBuffers);
    options.setIdleTimeout(idleTimeout);
    options.setKeyStoreOptions(keyStoreOptions);
    options.setTrustStoreOptions(trustStoreOptions);
    options.addEnabledCipherSuite(enabledCipher);
    options.setConnectTimeout(connectTimeout);
    options.setTrustAll(trustAll);
    options.addCrlPath(crlPath);
    options.addCrlValue(crlValue);
    options.setVerifyHost(verifyHost);
    options.setMaxPoolSize(maxPoolSize);
    options.setKeepAlive(keepAlive);
    options.setPipelining(pipelining);
    options.setTryUseCompression(tryUseCompression);
    HttpClientOptions copy = new HttpClientOptions(options);
    assertEquals(sendBufferSize, copy.getSendBufferSize());
    assertEquals(receiverBufferSize, copy.getReceiveBufferSize());
    assertEquals(reuseAddress, copy.isReuseAddress());
    assertEquals(trafficClass, copy.getTrafficClass());
    assertEquals(tcpNoDelay, copy.isTcpNoDelay());
    assertEquals(tcpKeepAlive, copy.isTcpKeepAlive());
    assertEquals(soLinger, copy.getSoLinger());
    assertEquals(usePooledBuffers, copy.isUsePooledBuffers());
    assertEquals(idleTimeout, copy.getIdleTimeout());
    assertEquals(ssl, copy.isSsl());
    assertNotSame(keyStoreOptions, copy.getKeyCertOptions());
    assertEquals(ksPassword, ((JksOptions) copy.getKeyCertOptions()).getPassword());
    assertNotSame(trustStoreOptions, copy.getTrustOptions());
    assertEquals(tsPassword, ((JksOptions)copy.getTrustOptions()).getPassword());
    assertEquals(1, copy.getEnabledCipherSuites().size());
    assertTrue(copy.getEnabledCipherSuites().contains(enabledCipher));
    assertEquals(connectTimeout, copy.getConnectTimeout());
    assertEquals(trustAll, copy.isTrustAll());
    assertEquals(1, copy.getCrlPaths().size());
    assertEquals(crlPath, copy.getCrlPaths().get(0));
    assertEquals(1, copy.getCrlValues().size());
    assertEquals(crlValue, copy.getCrlValues().get(0));
    assertEquals(verifyHost, copy.isVerifyHost());
    assertEquals(maxPoolSize, copy.getMaxPoolSize());
    assertEquals(keepAlive, copy.isKeepAlive());
    assertEquals(pipelining, copy.isPipelining());
    assertEquals(tryUseCompression, copy.isTryUseCompression());
  }

  @Test
  public void testDefaultClientOptionsJson() {
    HttpClientOptions def = new HttpClientOptions();
    HttpClientOptions json = new HttpClientOptions(new JsonObject());
    assertEquals(def.getMaxPoolSize(), json.getMaxPoolSize());
    assertEquals(def.isKeepAlive(), json.isKeepAlive());
    assertEquals(def.isPipelining(), json.isPipelining());
    assertEquals(def.isVerifyHost(), json.isVerifyHost());
    assertEquals(def.isTryUseCompression(), json.isTryUseCompression());
    assertEquals(def.isTrustAll(), json.isTrustAll());
    assertEquals(def.getCrlPaths(), json.getCrlPaths());
    assertEquals(def.getCrlValues(), json.getCrlValues());
    assertEquals(def.getConnectTimeout(), json.getConnectTimeout());
    assertEquals(def.isTcpNoDelay(), json.isTcpNoDelay());
    assertEquals(def.isTcpKeepAlive(), json.isTcpKeepAlive());
    assertEquals(def.getSoLinger(), json.getSoLinger());
    assertEquals(def.isUsePooledBuffers(), json.isUsePooledBuffers());
    assertEquals(def.isSsl(), json.isSsl());
  }

  @Test
  public void testClientOptionsJson() {
    int sendBufferSize = TestUtils.randomPositiveInt();
    int receiverBufferSize = TestUtils.randomPortInt();
    Random rand = new Random();
    boolean reuseAddress = rand.nextBoolean();
    int trafficClass = TestUtils.randomByte() + 127;
    boolean tcpNoDelay = rand.nextBoolean();
    boolean tcpKeepAlive = rand.nextBoolean();
    int soLinger = TestUtils.randomPositiveInt();
    boolean usePooledBuffers = rand.nextBoolean();
    int idleTimeout = TestUtils.randomPositiveInt();
    boolean ssl = rand.nextBoolean();
    JksOptions keyStoreOptions = new JksOptions();
    String ksPassword = TestUtils.randomAlphaString(100);
    keyStoreOptions.setPassword(ksPassword);
    String ksPath = TestUtils.randomAlphaString(100);
    keyStoreOptions.setPath(ksPath);
    JksOptions trustStoreOptions = new JksOptions();
    String tsPassword = TestUtils.randomAlphaString(100);
    trustStoreOptions.setPassword(tsPassword);
    String tsPath = TestUtils.randomAlphaString(100);
    trustStoreOptions.setPath(tsPath);
    String enabledCipher = TestUtils.randomAlphaString(100);
    int connectTimeout = TestUtils.randomPositiveInt();
    boolean trustAll = rand.nextBoolean();
    String crlPath = TestUtils.randomUnicodeString(100);
    boolean verifyHost = rand.nextBoolean();
    int maxPoolSize = TestUtils.randomPositiveInt();
    boolean keepAlive = rand.nextBoolean();
    boolean pipelining = rand.nextBoolean();
    boolean tryUseCompression = rand.nextBoolean();

    JsonObject json = new JsonObject();
    json.put("sendBufferSize", sendBufferSize)
      .put("receiveBufferSize", receiverBufferSize)
      .put("reuseAddress", reuseAddress)
      .put("trafficClass", trafficClass)
      .put("tcpNoDelay", tcpNoDelay)
      .put("tcpKeepAlive", tcpKeepAlive)
      .put("soLinger", soLinger)
      .put("usePooledBuffers", usePooledBuffers)
      .put("idleTimeout", idleTimeout)
      .put("ssl", ssl)
      .put("enabledCipherSuites", new JsonArray().add(enabledCipher))
      .put("connectTimeout", connectTimeout)
      .put("trustAll", trustAll)
      .put("crlPaths", new JsonArray().add(crlPath))
      .put("keyStoreOptions", new JsonObject().put("type", "jks").put("password", ksPassword).put("path", ksPath))
      .put("trustStoreOptions", new JsonObject().put("type", "jks").put("password", tsPassword).put("path", tsPath))
      .put("verifyHost", verifyHost)
      .put("maxPoolSize", maxPoolSize)
      .put("keepAlive", keepAlive)
      .put("pipelining", pipelining)
      .put("tryUseCompression", tryUseCompression);

    HttpClientOptions options = new HttpClientOptions(json);
    assertEquals(sendBufferSize, options.getSendBufferSize());
    assertEquals(receiverBufferSize, options.getReceiveBufferSize());
    assertEquals(reuseAddress, options.isReuseAddress());
    assertEquals(trafficClass, options.getTrafficClass());
    assertEquals(tcpKeepAlive, options.isTcpKeepAlive());
    assertEquals(tcpNoDelay, options.isTcpNoDelay());
    assertEquals(soLinger, options.getSoLinger());
    assertEquals(usePooledBuffers, options.isUsePooledBuffers());
    assertEquals(idleTimeout, options.getIdleTimeout());
    assertEquals(ssl, options.isSsl());
    assertNotSame(keyStoreOptions, options.getKeyCertOptions());
    assertEquals(ksPassword, ((JksOptions) options.getKeyCertOptions()).getPassword());
    assertEquals(ksPath, ((JksOptions) options.getKeyCertOptions()).getPath());
    assertNotSame(trustStoreOptions, options.getTrustOptions());
    assertEquals(tsPassword, ((JksOptions) options.getTrustOptions()).getPassword());
    assertEquals(tsPath, ((JksOptions) options.getTrustOptions()).getPath());
    assertEquals(1, options.getEnabledCipherSuites().size());
    assertTrue(options.getEnabledCipherSuites().contains(enabledCipher));
    assertEquals(connectTimeout, options.getConnectTimeout());
    assertEquals(trustAll, options.isTrustAll());
    assertEquals(1, options.getCrlPaths().size());
    assertEquals(crlPath, options.getCrlPaths().get(0));
    assertEquals(verifyHost, options.isVerifyHost());
    assertEquals(maxPoolSize, options.getMaxPoolSize());
    assertEquals(keepAlive, options.isKeepAlive());
    assertEquals(pipelining, options.isPipelining());
    assertEquals(tryUseCompression, options.isTryUseCompression());

    // Test other keystore/truststore types
    json.put("pfxKeyCertOptions", new JsonObject().put("password", ksPassword))
      .put("pfxTrustOptions", new JsonObject().put("password", tsPassword));
    options = new HttpClientOptions(json);
    assertTrue(options.getTrustOptions() instanceof PfxOptions);
    assertTrue(options.getKeyCertOptions() instanceof PfxOptions);

    json.put("pemKeyCertOptions", new JsonObject())
      .put("pemTrustOptions", new JsonObject());
    options = new HttpClientOptions(json);
    assertTrue(options.getTrustOptions() instanceof PemTrustOptions);
    assertTrue(options.getKeyCertOptions() instanceof PemKeyCertOptions);
  }

  @Test
  public void testCopyServerOptions() {
    HttpServerOptions options = new HttpServerOptions();
    int sendBufferSize = TestUtils.randomPositiveInt();
    int receiverBufferSize = TestUtils.randomPortInt();
    Random rand = new Random();
    boolean reuseAddress = rand.nextBoolean();
    int trafficClass = TestUtils.randomByte() + 128;
    boolean tcpNoDelay = rand.nextBoolean();
    boolean tcpKeepAlive = rand.nextBoolean();
    int soLinger = TestUtils.randomPositiveInt();
    boolean usePooledBuffers = rand.nextBoolean();
    int idleTimeout = TestUtils.randomPositiveInt();
    boolean ssl = rand.nextBoolean();
    JksOptions keyStoreOptions = new JksOptions();
    String ksPassword = TestUtils.randomAlphaString(100);
    keyStoreOptions.setPassword(ksPassword);
    JksOptions trustStoreOptions = new JksOptions();
    String tsPassword = TestUtils.randomAlphaString(100);
    trustStoreOptions.setPassword(tsPassword);
    String enabledCipher = TestUtils.randomAlphaString(100);
    String crlPath = TestUtils.randomUnicodeString(100);
    Buffer crlValue = TestUtils.randomBuffer(100);
    int port = 1234;
    String host = TestUtils.randomAlphaString(100);
    int acceptBacklog = TestUtils.randomPortInt();
    boolean compressionSupported = rand.nextBoolean();
    int maxWebsocketFrameSize = TestUtils.randomPositiveInt();
    String wsSubProtocol = TestUtils.randomAlphaString(10);
    boolean is100ContinueHandledAutomatically = rand.nextBoolean();
    options.setSendBufferSize(sendBufferSize);
    options.setReceiveBufferSize(receiverBufferSize);
    options.setReuseAddress(reuseAddress);
    options.setTrafficClass(trafficClass);
    options.setTcpNoDelay(tcpNoDelay);
    options.setTcpKeepAlive(tcpKeepAlive);
    options.setSoLinger(soLinger);
    options.setUsePooledBuffers(usePooledBuffers);
    options.setIdleTimeout(idleTimeout);
    options.setSsl(ssl);
    options.setKeyStoreOptions(keyStoreOptions);
    options.setTrustStoreOptions(trustStoreOptions);
    options.addEnabledCipherSuite(enabledCipher);
    options.addCrlPath(crlPath);
    options.addCrlValue(crlValue);
    options.setPort(port);
    options.setHost(host);
    options.setAcceptBacklog(acceptBacklog);
    options.setCompressionSupported(compressionSupported);
    options.setMaxWebsocketFrameSize(maxWebsocketFrameSize);
    options.setWebsocketSubProtocol(wsSubProtocol);
    options.setHandle100ContinueAutomatically(is100ContinueHandledAutomatically);
    HttpServerOptions copy = new HttpServerOptions(options);
    assertEquals(sendBufferSize, copy.getSendBufferSize());
    assertEquals(receiverBufferSize, copy.getReceiveBufferSize());
    assertEquals(reuseAddress, copy.isReuseAddress());
    assertEquals(trafficClass, copy.getTrafficClass());
    assertEquals(tcpNoDelay, copy.isTcpNoDelay());
    assertEquals(tcpKeepAlive, copy.isTcpKeepAlive());
    assertEquals(soLinger, copy.getSoLinger());
    assertEquals(usePooledBuffers, copy.isUsePooledBuffers());
    assertEquals(idleTimeout, copy.getIdleTimeout());
    assertEquals(ssl, copy.isSsl());
    assertNotSame(keyStoreOptions, copy.getKeyCertOptions());
    assertEquals(ksPassword, ((JksOptions) copy.getKeyCertOptions()).getPassword());
    assertNotSame(trustStoreOptions, copy.getTrustOptions());
    assertEquals(tsPassword, ((JksOptions)copy.getTrustOptions()).getPassword());
    assertEquals(1, copy.getEnabledCipherSuites().size());
    assertTrue(copy.getEnabledCipherSuites().contains(enabledCipher));
    assertEquals(1, copy.getCrlPaths().size());
    assertEquals(crlPath, copy.getCrlPaths().get(0));
    assertEquals(1, copy.getCrlValues().size());
    assertEquals(crlValue, copy.getCrlValues().get(0));
    assertEquals(port, copy.getPort());
    assertEquals(host, copy.getHost());
    assertEquals(acceptBacklog, copy.getAcceptBacklog());
    assertEquals(compressionSupported, copy.isCompressionSupported());
    assertEquals(maxWebsocketFrameSize, copy.getMaxWebsocketFrameSize());
    assertEquals(wsSubProtocol, copy.getWebsocketSubProtocols());
    assertEquals(is100ContinueHandledAutomatically, copy.isHandle100ContinueAutomatically());
  }

  @Test
  public void testDefaultServerOptionsJson() {
    HttpServerOptions def = new HttpServerOptions();
    HttpServerOptions json = new HttpServerOptions(new JsonObject());
    assertEquals(def.getMaxWebsocketFrameSize(), json.getMaxWebsocketFrameSize());
    assertEquals(def.getWebsocketSubProtocols(), json.getWebsocketSubProtocols());
    assertEquals(def.isCompressionSupported(), json.isCompressionSupported());
    assertEquals(def.isClientAuthRequired(), json.isClientAuthRequired());
    assertEquals(def.getCrlPaths(), json.getCrlPaths());
    assertEquals(def.getCrlValues(), json.getCrlValues());
    assertEquals(def.getAcceptBacklog(), json.getAcceptBacklog());
    assertEquals(def.getPort(), json.getPort());
    assertEquals(def.getHost(), json.getHost());
    assertEquals(def.isTcpNoDelay(), json.isTcpNoDelay());
    assertEquals(def.isTcpKeepAlive(), json.isTcpKeepAlive());
    assertEquals(def.getSoLinger(), json.getSoLinger());
    assertEquals(def.isUsePooledBuffers(), json.isUsePooledBuffers());
    assertEquals(def.isSsl(), json.isSsl());
    assertEquals(def.isHandle100ContinueAutomatically(), json.isHandle100ContinueAutomatically());
  }

  @Test
  public void testServerOptionsJson() {
    int sendBufferSize = TestUtils.randomPositiveInt();
    int receiverBufferSize = TestUtils.randomPortInt();
    Random rand = new Random();
    boolean reuseAddress = rand.nextBoolean();
    int trafficClass = TestUtils.randomByte() + 127;
    boolean tcpNoDelay = rand.nextBoolean();
    boolean tcpKeepAlive = rand.nextBoolean();
    int soLinger = TestUtils.randomPositiveInt();
    boolean usePooledBuffers = rand.nextBoolean();
    int idleTimeout = TestUtils.randomPositiveInt();
    boolean ssl = rand.nextBoolean();
    JksOptions keyStoreOptions = new JksOptions();
    String ksPassword = TestUtils.randomAlphaString(100);
    keyStoreOptions.setPassword(ksPassword);
    String ksPath = TestUtils.randomAlphaString(100);
    keyStoreOptions.setPath(ksPath);
    JksOptions trustStoreOptions = new JksOptions();
    String tsPassword = TestUtils.randomAlphaString(100);
    trustStoreOptions.setPassword(tsPassword);
    String tsPath = TestUtils.randomAlphaString(100);
    trustStoreOptions.setPath(tsPath);
    String enabledCipher = TestUtils.randomAlphaString(100);
    String crlPath = TestUtils.randomUnicodeString(100);
    int port = 1234;
    String host = TestUtils.randomAlphaString(100);
    int acceptBacklog = TestUtils.randomPortInt();
    boolean compressionSupported = rand.nextBoolean();
    int maxWebsocketFrameSize = TestUtils.randomPositiveInt();
    String wsSubProtocol = TestUtils.randomAlphaString(10);
    boolean is100ContinueHandledAutomatically = rand.nextBoolean();

    JsonObject json = new JsonObject();
    json.put("sendBufferSize", sendBufferSize)
      .put("receiveBufferSize", receiverBufferSize)
      .put("reuseAddress", reuseAddress)
      .put("trafficClass", trafficClass)
      .put("tcpNoDelay", tcpNoDelay)
      .put("tcpKeepAlive", tcpKeepAlive)
      .put("soLinger", soLinger)
      .put("usePooledBuffers", usePooledBuffers)
      .put("idleTimeout", idleTimeout)
      .put("ssl", ssl)
      .put("enabledCipherSuites", new JsonArray().add(enabledCipher))
      .put("crlPaths", new JsonArray().add(crlPath))
      .put("keyStoreOptions", new JsonObject().put("type", "jks").put("password", ksPassword).put("path", ksPath))
      .put("trustStoreOptions", new JsonObject().put("type", "jks").put("password", tsPassword).put("path", tsPath))
      .put("port", port)
      .put("host", host)
      .put("acceptBacklog", acceptBacklog)
      .put("compressionSupported", compressionSupported)
      .put("maxWebsocketFrameSize", maxWebsocketFrameSize)
      .put("websocketSubProtocols", wsSubProtocol)
      .put("handle100ContinueAutomatically", is100ContinueHandledAutomatically);

    HttpServerOptions options = new HttpServerOptions(json);
    assertEquals(sendBufferSize, options.getSendBufferSize());
    assertEquals(receiverBufferSize, options.getReceiveBufferSize());
    assertEquals(reuseAddress, options.isReuseAddress());
    assertEquals(trafficClass, options.getTrafficClass());
    assertEquals(tcpKeepAlive, options.isTcpKeepAlive());
    assertEquals(tcpNoDelay, options.isTcpNoDelay());
    assertEquals(soLinger, options.getSoLinger());
    assertEquals(usePooledBuffers, options.isUsePooledBuffers());
    assertEquals(idleTimeout, options.getIdleTimeout());
    assertEquals(ssl, options.isSsl());
    assertNotSame(keyStoreOptions, options.getKeyCertOptions());
    assertEquals(ksPassword, ((JksOptions) options.getKeyCertOptions()).getPassword());
    assertEquals(ksPath, ((JksOptions) options.getKeyCertOptions()).getPath());
    assertNotSame(trustStoreOptions, options.getTrustOptions());
    assertEquals(tsPassword, ((JksOptions) options.getTrustOptions()).getPassword());
    assertEquals(tsPath, ((JksOptions) options.getTrustOptions()).getPath());
    assertEquals(1, options.getEnabledCipherSuites().size());
    assertTrue(options.getEnabledCipherSuites().contains(enabledCipher));
    assertEquals(1, options.getCrlPaths().size());
    assertEquals(crlPath, options.getCrlPaths().get(0));
    assertEquals(port, options.getPort());
    assertEquals(host, options.getHost());
    assertEquals(acceptBacklog, options.getAcceptBacklog());
    assertEquals(compressionSupported, options.isCompressionSupported());
    assertEquals(maxWebsocketFrameSize, options.getMaxWebsocketFrameSize());
    assertEquals(wsSubProtocol, options.getWebsocketSubProtocols());
    assertEquals(is100ContinueHandledAutomatically, options.isHandle100ContinueAutomatically());

    // Test other keystore/truststore types
    json.put("pfxKeyCertOptions", new JsonObject().put("password", ksPassword))
      .put("pfxTrustOptions", new JsonObject().put("password", tsPassword));
    options = new HttpServerOptions(json);
    assertTrue(options.getTrustOptions() instanceof PfxOptions);
    assertTrue(options.getKeyCertOptions() instanceof PfxOptions);

    json.put("pemKeyCertOptions", new JsonObject())
      .put("pemTrustOptions", new JsonObject());
    options = new HttpServerOptions(json);
    assertTrue(options.getTrustOptions() instanceof PemTrustOptions);
    assertTrue(options.getKeyCertOptions() instanceof PemKeyCertOptions);
  }

  @Test
  public void testServerChaining() {
    server.requestHandler(req -> {
      assertTrue(req.response().setChunked(true) == req.response());
      assertTrue(req.response().write("foo", "UTF-8") == req.response());
      assertTrue(req.response().write("foo") == req.response());
      testComplete();
    });

    server.listen(onSuccess(server -> {
      client.request(HttpMethod.PUT, DEFAULT_HTTP_PORT, DEFAULT_HTTP_HOST, DEFAULT_TEST_URI, noOpHandler()).end();
    }));

    await();
  }

  @Test
  public void testServerChainingSendFile() throws Exception {
    File file = setupFile("test-server-chaining.dat", "blah");
    server.requestHandler(req -> {
      assertTrue(req.response().sendFile(file.getAbsolutePath()) == req.response());
      assertTrue(req.response().ended());
      file.delete();
      testComplete();
    });

    server.listen(onSuccess(server -> {
      client.request(HttpMethod.PUT, DEFAULT_HTTP_PORT, DEFAULT_HTTP_HOST, DEFAULT_TEST_URI, noOpHandler()).end();
    }));

    await();
  }

  @Test
  public void testClientRequestArguments() throws Exception {
    HttpClientRequest req = client.request(HttpMethod.PUT, DEFAULT_HTTP_PORT, DEFAULT_HTTP_HOST, DEFAULT_TEST_URI, noOpHandler());
    assertNullPointerException(() -> req.putHeader((String) null, "someValue"));
    assertNullPointerException(() -> req.putHeader((CharSequence) null, "someValue"));
    assertNullPointerException(() -> req.putHeader("someKey", (Iterable<String>) null));
    assertNullPointerException(() -> req.write((Buffer) null));
    assertNullPointerException(() -> req.write((String) null));
    assertNullPointerException(() -> req.write(null, "UTF-8"));
    assertNullPointerException(() -> req.write("someString", null));
    assertNullPointerException(() -> req.end((Buffer) null));
    assertNullPointerException(() -> req.end((String) null));
    assertNullPointerException(() -> req.end(null, "UTF-8"));
    assertNullPointerException(() -> req.end("someString", null));
    assertIllegalArgumentException(() -> req.setTimeout(0));
  }

  @Test
  public void testClientChaining() {
    server.requestHandler(noOpHandler());

    server.listen(onSuccess(server -> {
      HttpClientRequest req = client.request(HttpMethod.PUT, DEFAULT_HTTP_PORT, DEFAULT_HTTP_HOST, DEFAULT_TEST_URI, noOpHandler());
      assertTrue(req.setChunked(true) == req);
      assertTrue(req.sendHead() == req);
      assertTrue(req.write("foo", "UTF-8") == req);
      assertTrue(req.write("foo") == req);
      assertTrue(req.write(Buffer.buffer("foo")) == req);
      testComplete();
    }));

    await();
  }

  @Test
  public void testLowerCaseHeaders() {
    server.requestHandler(req -> {
      assertEquals("foo", req.headers().get("Foo"));
      assertEquals("foo", req.headers().get("foo"));
      assertEquals("foo", req.headers().get("fOO"));
      assertTrue(req.headers().contains("Foo"));
      assertTrue(req.headers().contains("foo"));
      assertTrue(req.headers().contains("fOO"));

      req.response().putHeader("Quux", "quux");

      assertEquals("quux", req.response().headers().get("Quux"));
      assertEquals("quux", req.response().headers().get("quux"));
      assertEquals("quux", req.response().headers().get("qUUX"));
      assertTrue(req.response().headers().contains("Quux"));
      assertTrue(req.response().headers().contains("quux"));
      assertTrue(req.response().headers().contains("qUUX"));

      req.response().end();
    });

    server.listen(onSuccess(server -> {
      HttpClientRequest req = client.request(HttpMethod.GET, DEFAULT_HTTP_PORT, DEFAULT_HTTP_HOST, DEFAULT_TEST_URI, resp -> {
        assertEquals("quux", resp.headers().get("Quux"));
        assertEquals("quux", resp.headers().get("quux"));
        assertEquals("quux", resp.headers().get("qUUX"));
        assertTrue(resp.headers().contains("Quux"));
        assertTrue(resp.headers().contains("quux"));
        assertTrue(resp.headers().contains("qUUX"));
        testComplete();
      });

      req.putHeader("Foo", "foo");
      assertEquals("foo", req.headers().get("Foo"));
      assertEquals("foo", req.headers().get("foo"));
      assertEquals("foo", req.headers().get("fOO"));
      assertTrue(req.headers().contains("Foo"));
      assertTrue(req.headers().contains("foo"));
      assertTrue(req.headers().contains("fOO"));

      req.end();
    }));

    await();
  }


  @Test
  public void testPutHeadersOnRequest() {
    server.requestHandler(req -> {
      assertEquals("bar", req.headers().get("foo"));
      assertEquals("bar", req.getHeader("foo"));
      req.response().end();
    });
    server.listen(onSuccess(server -> {
      client.request(HttpMethod.GET, DEFAULT_HTTP_PORT, DEFAULT_HTTP_HOST, DEFAULT_TEST_URI, resp -> {
        assertEquals(200, resp.statusCode());
        testComplete();
      }).putHeader("foo", "bar").end();
    }));
    await();
  }

  @Test
  public void testRequestNPE() {
    String uri = "/some-uri?foo=bar";
    TestUtils.assertNullPointerException(() -> client.request(HttpMethod.GET, DEFAULT_HTTP_PORT, DEFAULT_HTTP_HOST, uri, null));
    TestUtils.assertNullPointerException(() -> client.request((HttpMethod)null, DEFAULT_HTTP_PORT, DEFAULT_HTTP_HOST, uri, resp -> {}));
    TestUtils.assertNullPointerException(() -> client.requestAbs((HttpMethod) null, "http://someuri", resp -> {
    }));
    TestUtils.assertNullPointerException(() -> client.request(HttpMethod.GET, 8080, "localhost", "/somepath", null));
    TestUtils.assertNullPointerException(() -> client.request((HttpMethod)null, 8080, "localhost", "/somepath", resp -> {}));
    TestUtils.assertNullPointerException(() -> client.request(HttpMethod.GET, 8080, null, "/somepath", resp -> {}));
    TestUtils.assertNullPointerException(() -> client.request(HttpMethod.GET, 8080, "localhost", null, resp -> {}));
  }

  @Test
  public void testInvalidAbsoluteURI() {
    try {
      client.requestAbs(HttpMethod.GET, "ijdijwidjqwoijd192d192192ej12d", resp -> {
      }).end();
      fail("Should throw exception");
    } catch (VertxException e) {
      //OK
    }
  }

  @Test
  public void testSimpleGET() {
    String uri = "/some-uri?foo=bar";
    testSimpleRequest(uri, HttpMethod.GET, resp -> testComplete());
  }

  @Test
  public void testSimplePUT() {
    String uri = "/some-uri?foo=bar";
    testSimpleRequest(uri, HttpMethod.PUT, resp -> testComplete());
  }

  @Test
  public void testSimplePOST() {
    String uri = "/some-uri?foo=bar";
    testSimpleRequest(uri, HttpMethod.POST, resp -> testComplete());
  }

  @Test
  public void testSimpleDELETE() {
    String uri = "/some-uri?foo=bar";
    testSimpleRequest(uri, HttpMethod.DELETE, resp -> testComplete());
  }

  @Test
  public void testSimpleHEAD() {
    String uri = "/some-uri?foo=bar";
    testSimpleRequest(uri, HttpMethod.HEAD, resp -> testComplete());
  }

  @Test
  public void testSimpleTRACE() {
    String uri = "/some-uri?foo=bar";
    testSimpleRequest(uri, HttpMethod.TRACE, resp -> testComplete());
  }

  @Test
  public void testSimpleCONNECT() {
    String uri = "/some-uri?foo=bar";
    testSimpleRequest(uri, HttpMethod.CONNECT, resp -> testComplete());
  }

  @Test
  public void testSimpleOPTIONS() {
    String uri = "/some-uri?foo=bar";
    testSimpleRequest(uri, HttpMethod.OPTIONS, resp -> testComplete());
  }

  @Test
  public void testSimplePATCH() {
    String uri = "/some-uri?foo=bar";
    testSimpleRequest(uri, HttpMethod.PATCH, resp -> testComplete());
  }

  @Test
  public void testSimpleGETAbsolute() {
    String uri = "/some-uri?foo=bar";
    testSimpleRequest(uri, HttpMethod.GET, true, resp -> testComplete());
  }

  @Test
  public void testSimplePUTAbsolute() {
    String uri = "/some-uri?foo=bar";
    testSimpleRequest(uri, HttpMethod.PUT, true, resp -> testComplete());
  }

  @Test
  public void testSimplePOSTAbsolute() {
    String uri = "/some-uri?foo=bar";
    testSimpleRequest(uri, HttpMethod.POST, true, resp -> testComplete());
  }

  @Test
  public void testSimpleDELETEAbsolute() {
    String uri = "/some-uri?foo=bar";
    testSimpleRequest(uri, HttpMethod.DELETE, true, resp -> testComplete());
  }

  @Test
  public void testSimpleHEADAbsolute() {
    String uri = "/some-uri?foo=bar";
    testSimpleRequest(uri, HttpMethod.HEAD, true, resp -> testComplete());
  }

  @Test
  public void testSimpleTRACEAbsolute() {
    String uri = "/some-uri?foo=bar";
    testSimpleRequest(uri, HttpMethod.TRACE, true, resp -> testComplete());
  }

  @Test
  public void testSimpleCONNECTAbsolute() {
    String uri = "/some-uri?foo=bar";
    testSimpleRequest(uri, HttpMethod.CONNECT, true, resp -> testComplete());
  }

  @Test
  public void testSimpleOPTIONSAbsolute() {
    String uri = "/some-uri?foo=bar";
    testSimpleRequest(uri, HttpMethod.OPTIONS, true, resp -> testComplete());
  }

  @Test
  public void testSimplePATCHAbsolute() {
    String uri = "/some-uri?foo=bar";
    testSimpleRequest(uri, HttpMethod.PATCH, true, resp -> testComplete());
  }

  private void testSimpleRequest(String uri, HttpMethod method, Handler<HttpClientResponse> handler) {
    testSimpleRequest(uri, method, false, handler);
  }

  private void testSimpleRequest(String uri, HttpMethod method, boolean absolute, Handler<HttpClientResponse> handler) {
    HttpClientRequest req;
    if (absolute) {
      req = client.requestAbs(method, "http://" + DEFAULT_HTTP_HOST + ":" + DEFAULT_HTTP_PORT + uri, handler);
    } else {
      req = client.request(method, DEFAULT_HTTP_PORT, DEFAULT_HTTP_HOST, uri, handler);
    }
    testSimpleRequest(uri, method, req);
  }

  private void testSimpleRequest(String uri, HttpMethod method, HttpClientRequest request) {
    int index = uri.indexOf('?');
    String path = index == -1 ? uri : uri.substring(0, index);
    String query = index == -1 ? null : uri.substring(index + 1);
    server.requestHandler(req -> {
      assertEquals(path, req.path());
      assertEquals(method, req.method());
      assertEquals(query, req.query());
      req.response().end();
    });

    server.listen(onSuccess(server -> request.end()));

    await();
  }

  @Test
  public void testResponseEndHandlers1() {
    waitFor(2);
    AtomicInteger cnt = new AtomicInteger();
    server.requestHandler(req -> {
      req.response().headersEndHandler(fut -> {
        // Insert another header
        req.response().putHeader("extraheader", "wibble");
        assertEquals(0, cnt.getAndIncrement());
        fut.complete();
      });
      req.response().bodyEndHandler(v -> {
        assertEquals(1, cnt.getAndIncrement());
        complete();
      });
      req.response().end();
    }).listen(onSuccess(server -> {
      client.request(HttpMethod.GET, DEFAULT_HTTP_PORT, DEFAULT_HTTP_HOST, "/", res -> {
        assertEquals(200, res.statusCode());
        assertEquals("wibble", res.headers().get("extraheader"));
        complete();
      }).end();
    }));
    await();
  }

  @Test
  public void testResponseEndHandlers2() {
    waitFor(2);
    AtomicInteger cnt = new AtomicInteger();
    server.requestHandler(req -> {
      req.response().headersEndHandler(fut -> {
        // Insert another header
        req.response().putHeader("extraheader", "wibble");
        assertEquals(0, cnt.getAndIncrement());
        fut.complete();
      });
      req.response().bodyEndHandler(v -> {
        assertEquals(1, cnt.getAndIncrement());
        complete();
      });
      req.response().end("blah");
    }).listen(onSuccess(server -> {
      client.request(HttpMethod.GET, DEFAULT_HTTP_PORT, DEFAULT_HTTP_HOST, "/", res -> {
        assertEquals(200, res.statusCode());
        assertEquals("wibble", res.headers().get("extraheader"));
        res.bodyHandler(buff -> {
          assertEquals(Buffer.buffer("blah"), buff);
          complete();
        });
      }).end();
    }));
    await();
  }

  @Test
  public void testResponseEndHandlersSendFile() throws Exception {
    waitFor(2);
    AtomicInteger cnt = new AtomicInteger();
    String content = "iqdioqwdqwiojqwijdwqd";
    File toSend = setupFile("somefile.txt", content);
    server.requestHandler(req -> {
      req.response().headersEndHandler(fut -> {
        // Insert another header
        req.response().putHeader("extraheader", "wibble");
        assertEquals(0, cnt.getAndIncrement());
        fut.complete();
      });
      req.response().bodyEndHandler(v -> {
        assertEquals(1, cnt.getAndIncrement());
        complete();
      });
      req.response().sendFile(toSend.getAbsolutePath());
    }).listen(onSuccess(server -> {
      client.request(HttpMethod.GET, DEFAULT_HTTP_PORT, DEFAULT_HTTP_HOST, "/", res -> {
        assertEquals(200, res.statusCode());
        assertEquals("wibble", res.headers().get("extraheader"));
        res.bodyHandler(buff -> {
          assertEquals(Buffer.buffer(content), buff);
          complete();
        });
      }).end();
    }));
    await();
  }

  @Test
  public void testAbsoluteURI() {
    testURIAndPath("http://localhost:" + DEFAULT_HTTP_PORT + "/this/is/a/path/foo.html", "/this/is/a/path/foo.html");
  }

  @Test
  public void testRelativeURI() {
    testURIAndPath("/this/is/a/path/foo.html", "/this/is/a/path/foo.html");
  }

  @Test
  public void testAbsoluteURIWithHttpSchemaInQuery() {
    testURIAndPath("http://localhost:" + DEFAULT_HTTP_PORT + "/correct/path?url=http://localhost:8008/wrong/path", "/correct/path");
  }

  @Test
  public void testRelativeURIWithHttpSchemaInQuery() {
    testURIAndPath("/correct/path?url=http://localhost:8008/wrong/path", "/correct/path");
  }

  @Test
  public void testAbsoluteURIEmptyPath() {
    testURIAndPath("http://localhost:" + DEFAULT_HTTP_PORT + "/", "/");
  }

  private void testURIAndPath(String uri, String path) {
    server.requestHandler(req -> {
      assertEquals(uri, req.uri());
      assertEquals(path, req.path());
      req.response().end();
    });

    server.listen(onSuccess(server -> {
      client.request(HttpMethod.GET, DEFAULT_HTTP_PORT, DEFAULT_HTTP_HOST, uri, resp -> testComplete()).end();
    }));

    await();
  }

  @Test
  public void testParamUmlauteDecoding() throws UnsupportedEncodingException {
    testParamDecoding("äüö");
  } 
  
  @Test
  public void testParamPlusDecoding() throws UnsupportedEncodingException {
    testParamDecoding("+");
  } 

  @Test
  public void testParamPercentDecoding() throws UnsupportedEncodingException {
    testParamDecoding("%");
  }

  @Test
  public void testParamSpaceDecoding() throws UnsupportedEncodingException {
    testParamDecoding(" ");
  }

  @Test
  public void testParamNormalDecoding() throws UnsupportedEncodingException {
    testParamDecoding("hello");
  }

  @Test
  public void testParamAltogetherDecoding() throws UnsupportedEncodingException {
    testParamDecoding("äüö+% hello");
  }

  private void testParamDecoding(String value) throws UnsupportedEncodingException {
    
    server.requestHandler(req -> {
      req.setExpectMultipart(true);
      req.endHandler(v -> {
        MultiMap formAttributes = req.formAttributes();
        assertEquals(value, formAttributes.get("param"));
      });
      req.response().end();
    });
    String postData = "param=" + URLEncoder.encode(value,"UTF-8");
    server.listen(onSuccess(server -> {
      client.post(DEFAULT_HTTP_PORT, DEFAULT_HTTP_HOST, "/")
        .putHeader(HttpHeaders.CONTENT_TYPE, HttpHeaders.APPLICATION_X_WWW_FORM_URLENCODED)
        .putHeader(HttpHeaders.CONTENT_LENGTH, String.valueOf(postData.length()))
        .handler(resp -> {
          testComplete();
        })
    .write(postData).end();
    }));

    await();
  }

  @Test
  public void testParamsAmpersand() {
    testParams('&');
  }

  @Test
  public void testParamsSemiColon() {
    testParams(';');
  }

  private void testParams(char delim) {
    Map<String, String> params = genMap(10);
    String query = generateQueryString(params, delim);

    server.requestHandler(req -> {
      assertEquals(query, req.query());
      assertEquals(params.size(), req.params().size());
      for (Map.Entry<String, String> entry : req.params()) {
        assertEquals(entry.getValue(), params.get(entry.getKey()));
      }
      req.response().end();
    });

    server.listen(onSuccess(server -> {
      client.request(HttpMethod.GET, DEFAULT_HTTP_PORT, DEFAULT_HTTP_HOST, "some-uri/?" + query, resp -> testComplete()).end();
    }));

    await();
  }

  @Test
  public void testNoParams() {
    server.requestHandler(req -> {
      assertNull(req.query());
      assertTrue(req.params().isEmpty());
      req.response().end();
    });

    server.listen(onSuccess(server -> {
      client.request(HttpMethod.GET, DEFAULT_HTTP_PORT, DEFAULT_HTTP_HOST, DEFAULT_TEST_URI, resp -> testComplete()).end();
    }));

    await();
  }

  @Test
  public void testDefaultRequestHeaders() {
    server.requestHandler(req -> {
      assertEquals(1, req.headers().size());
      assertEquals("localhost:" + DEFAULT_HTTP_PORT, req.headers().get("host"));
      req.response().end();
    });

    server.listen(onSuccess(server -> {
      client.request(HttpMethod.GET, DEFAULT_HTTP_PORT, DEFAULT_HTTP_HOST, DEFAULT_TEST_URI, resp -> testComplete()).end();
    }));

    await();
  }

  @Test
  public void testRequestHeadersPutAll() {
    testRequestHeaders(false);
  }

  @Test
  public void testRequestHeadersIndividually() {
    testRequestHeaders(true);
  }

  private void testRequestHeaders(boolean individually) {
    MultiMap headers = getHeaders(10);

    server.requestHandler(req -> {
      assertEquals(headers.size() + 1, req.headers().size());
      for (Map.Entry<String, String> entry : headers) {
        assertEquals(entry.getValue(), req.headers().get(entry.getKey()));
        assertEquals(entry.getValue(), req.getHeader(entry.getKey()));
      }
      req.response().end();
    });

    server.listen(onSuccess(server -> {
      HttpClientRequest req = client.request(HttpMethod.GET, DEFAULT_HTTP_PORT, DEFAULT_HTTP_HOST, DEFAULT_TEST_URI, resp -> testComplete());
      if (individually) {
        for (Map.Entry<String, String> header : headers) {
          req.headers().add(header.getKey(), header.getValue());
        }
      } else {
        req.headers().setAll(headers);
      }
      req.end();
    }));

    await();
  }

  @Test
  public void testResponseHeadersPutAll() {
    testResponseHeaders(false);
  }

  @Test
  public void testResponseHeadersIndividually() {
    testResponseHeaders(true);
  }

  private void testResponseHeaders(boolean individually) {
    MultiMap headers = getHeaders(10);

    server.requestHandler(req -> {
      if (individually) {
        for (Map.Entry<String, String> header : headers) {
          req.response().headers().add(header.getKey(), header.getValue());
        }
      } else {
        req.response().headers().setAll(headers);
      }
      req.response().end();
    });

    server.listen(onSuccess(server -> {
      client.request(HttpMethod.GET, DEFAULT_HTTP_PORT, DEFAULT_HTTP_HOST, DEFAULT_TEST_URI, resp -> {
        assertEquals(headers.size() + 1, resp.headers().size());
        for (Map.Entry<String, String> entry : headers) {
          assertEquals(entry.getValue(), resp.headers().get(entry.getKey()));
          assertEquals(entry.getValue(), resp.getHeader(entry.getKey()));
        }
        testComplete();
      }).end();
    }));

    await();
  }

  @Test
  public void testResponseMultipleSetCookieInHeader() {
    testResponseMultipleSetCookie(true, false);
  }

  @Test
  public void testResponseMultipleSetCookieInTrailer() {
    testResponseMultipleSetCookie(false, true);
  }

  @Test
  public void testResponseMultipleSetCookieInHeaderAndTrailer() {
    testResponseMultipleSetCookie(true, true);
  }

  private void testResponseMultipleSetCookie(boolean inHeader, boolean inTrailer) {
    List<String> cookies = new ArrayList<>();

    server.requestHandler(req -> {
      if (inHeader) {
        List<String> headers = new ArrayList<>();
        headers.add("h1=h1v1");
        headers.add("h2=h2v2; Expires=Wed, 09-Jun-2021 10:18:14 GMT");
        cookies.addAll(headers);
        req.response().headers().set("Set-Cookie", headers);
      }
      if (inTrailer) {
        req.response().setChunked(true);
        List<String> trailers = new ArrayList<>();
        trailers.add("t1=t1v1");
        trailers.add("t2=t2v2; Expires=Wed, 09-Jun-2021 10:18:14 GMT");
        cookies.addAll(trailers);
        req.response().trailers().set("Set-Cookie", trailers);
      }
      req.response().end();
    });

    server.listen(onSuccess(server -> {
      client.request(HttpMethod.GET, DEFAULT_HTTP_PORT, DEFAULT_HTTP_HOST, DEFAULT_TEST_URI, resp -> {
        resp.endHandler(v -> {
          assertEquals(cookies.size(), resp.cookies().size());
          for (int i = 0; i < cookies.size(); ++i) {
            assertEquals(cookies.get(i), resp.cookies().get(i));
          }
          testComplete();
        });
      }).end();
    }));

    await();
  }

  @Test
  public void testUseRequestAfterComplete() {
    server.requestHandler(noOpHandler());

    server.listen(onSuccess(server -> {
      HttpClientRequest req = client.request(HttpMethod.POST, DEFAULT_HTTP_PORT, DEFAULT_HTTP_HOST, DEFAULT_TEST_URI, noOpHandler());
      req.end();

      Buffer buff = Buffer.buffer();
      assertIllegalStateException(() -> req.end());
      assertIllegalStateException(() -> req.continueHandler(noOpHandler()));
      assertIllegalStateException(() -> req.drainHandler(noOpHandler()));
      assertIllegalStateException(() -> req.end("foo"));
      assertIllegalStateException(() -> req.end(buff));
      assertIllegalStateException(() -> req.end("foo", "UTF-8"));
      assertIllegalStateException(() -> req.sendHead());
      assertIllegalStateException(() -> req.setChunked(false));
      assertIllegalStateException(() -> req.setWriteQueueMaxSize(123));
      assertIllegalStateException(() -> req.write(buff));
      assertIllegalStateException(() -> req.write("foo"));
      assertIllegalStateException(() -> req.write("foo", "UTF-8"));
      assertIllegalStateException(() -> req.write(buff));
      assertIllegalStateException(() -> req.writeQueueFull());

      testComplete();
    }));

    await();
  }

  @Test
  public void testRequestBodyBufferAtEnd() {
    Buffer body = TestUtils.randomBuffer(1000);
    server.requestHandler(req -> req.bodyHandler(buffer -> {
      assertEquals(body, buffer);
      req.response().end();
    }));

    server.listen(onSuccess(server -> {
      client.request(HttpMethod.POST, DEFAULT_HTTP_PORT, DEFAULT_HTTP_HOST, DEFAULT_TEST_URI, resp -> testComplete()).end(body);
    }));

    await();
  }

  @Test
  public void testRequestBodyStringDefaultEncodingAtEnd() {
    testRequestBodyStringAtEnd(null);
  }

  @Test
  public void testRequestBodyStringUTF8AtEnd() {
    testRequestBodyStringAtEnd("UTF-8");
  }

  @Test
  public void testRequestBodyStringUTF16AtEnd() {
    testRequestBodyStringAtEnd("UTF-16");
  }

  private void testRequestBodyStringAtEnd(String encoding) {
    String body = TestUtils.randomUnicodeString(1000);
    Buffer bodyBuff;

    if (encoding == null) {
      bodyBuff = Buffer.buffer(body);
    } else {
      bodyBuff = Buffer.buffer(body, encoding);
    }

    server.requestHandler(req -> {
      req.bodyHandler(buffer -> {
        assertEquals(bodyBuff, buffer);
        testComplete();
      });
    });

    server.listen(onSuccess(server -> {
      HttpClientRequest req = client.request(HttpMethod.POST, DEFAULT_HTTP_PORT, DEFAULT_HTTP_HOST, DEFAULT_TEST_URI, noOpHandler());
      if (encoding == null) {
        req.end(body);
      } else {
        req.end(body, encoding);
      }
    }));

    await();
  }

  @Test
  public void testRequestBodyWriteChunked() {
    testRequestBodyWrite(true);
  }

  @Test
  public void testRequestBodyWriteNonChunked() {
    testRequestBodyWrite(false);
  }

  private void testRequestBodyWrite(boolean chunked) {
    Buffer body = Buffer.buffer();

    server.requestHandler(req -> {
      req.bodyHandler(buffer -> {
        assertEquals(body, buffer);
        req.response().end();
      });
    });

    server.listen(onSuccess(server -> {
      HttpClientRequest req = client.request(HttpMethod.POST, DEFAULT_HTTP_PORT, DEFAULT_HTTP_HOST, DEFAULT_TEST_URI, resp -> testComplete());
      int numWrites = 10;
      int chunkSize = 100;

      if (chunked) {
        req.setChunked(true);
      } else {
        req.headers().set("Content-Length", String.valueOf(numWrites * chunkSize));
      }
      for (int i = 0; i < numWrites; i++) {
        Buffer b = TestUtils.randomBuffer(chunkSize);
        body.appendBuffer(b);
        req.write(b);
      }
      req.end();
    }));

    await();
  }

  @Test
  public void testRequestBodyWriteStringChunkedDefaultEncoding() {
    testRequestBodyWriteString(true, null);
  }

  @Test
  public void testRequestBodyWriteStringChunkedUTF8() {
    testRequestBodyWriteString(true, "UTF-8");
  }

  @Test
  public void testRequestBodyWriteStringChunkedUTF16() {
    testRequestBodyWriteString(true, "UTF-16");
  }

  @Test
  public void testRequestBodyWriteStringNonChunkedDefaultEncoding() {
    testRequestBodyWriteString(false, null);
  }

  @Test
  public void testRequestBodyWriteStringNonChunkedUTF8() {
    testRequestBodyWriteString(false, "UTF-8");
  }

  @Test
  public void testRequestBodyWriteStringNonChunkedUTF16() {
    testRequestBodyWriteString(false, "UTF-16");
  }

  private void testRequestBodyWriteString(boolean chunked, String encoding) {
    String body = TestUtils.randomUnicodeString(1000);
    Buffer bodyBuff;

    if (encoding == null) {
      bodyBuff = Buffer.buffer(body);
    } else {
      bodyBuff = Buffer.buffer(body, encoding);
    }

    server.requestHandler(req -> {
      req.bodyHandler(buff -> {
        assertEquals(bodyBuff, buff);
        testComplete();
      });
    });

    server.listen(onSuccess(server -> {
      HttpClientRequest req = client.request(HttpMethod.POST, DEFAULT_HTTP_PORT, DEFAULT_HTTP_HOST, DEFAULT_TEST_URI, noOpHandler());

      if (chunked) {
        req.setChunked(true);
      } else {
        req.headers().set("Content-Length", String.valueOf(bodyBuff.length()));
      }

      if (encoding == null) {
        req.write(body);
      } else {
        req.write(body, encoding);
      }
      req.end();
    }));

    await();
  }

  @Test
  public void testRequestWrite() {
    Buffer body = TestUtils.randomBuffer(1000);

    server.requestHandler(req -> {
      req.bodyHandler(buff -> {
        assertEquals(body, buff);
        testComplete();
      });
    });

    server.listen(onSuccess(s -> {
      HttpClientRequest req = client.request(HttpMethod.POST, DEFAULT_HTTP_PORT, DEFAULT_HTTP_HOST, DEFAULT_TEST_URI, noOpHandler());
      req.setChunked(true);
      req.write(body);
      req.end();
    }));

    await();
  }

  @Test
  public void testConnectWithoutResponseHandler() throws Exception {
    try {
      client.request(HttpMethod.GET, DEFAULT_HTTP_PORT, DEFAULT_HTTP_HOST, DEFAULT_TEST_URI).end();
      fail();
    } catch (IllegalStateException expected) {
    }
    try {
      client.request(HttpMethod.GET, DEFAULT_HTTP_PORT, DEFAULT_HTTP_HOST, DEFAULT_TEST_URI).end("whatever");
      fail();
    } catch (IllegalStateException expected) {
    }
    try {
      client.request(HttpMethod.GET, DEFAULT_HTTP_PORT, DEFAULT_HTTP_HOST, DEFAULT_TEST_URI).end("whatever", "UTF-8");
      fail();
    } catch (IllegalStateException expected) {
    }
    try {
      client.request(HttpMethod.GET, DEFAULT_HTTP_PORT, DEFAULT_HTTP_HOST, DEFAULT_TEST_URI).end(Buffer.buffer("whatever"));
      fail();
    } catch (IllegalStateException expected) {
    }
    try {
      client.request(HttpMethod.GET, DEFAULT_HTTP_PORT, DEFAULT_HTTP_HOST, DEFAULT_TEST_URI).sendHead();
      fail();
    } catch (IllegalStateException expected) {
    }
    try {
      client.request(HttpMethod.GET, DEFAULT_HTTP_PORT, DEFAULT_HTTP_HOST, DEFAULT_TEST_URI).write(Buffer.buffer("whatever"));
      fail();
    } catch (IllegalStateException expected) {
    }
    try {
      client.request(HttpMethod.GET, DEFAULT_HTTP_PORT, DEFAULT_HTTP_HOST, DEFAULT_TEST_URI).write("whatever");
      fail();
    } catch (IllegalStateException expected) {
    }
    try {
      client.request(HttpMethod.GET, DEFAULT_HTTP_PORT, DEFAULT_HTTP_HOST, DEFAULT_TEST_URI).write("whatever", "UTF-8");
      fail();
    } catch (IllegalStateException expected) {
    }
  }

  @Test
  public void testClientExceptionHandlerCalledWhenFailingToConnect() throws Exception {
    client.request(HttpMethod.GET, 9998, "255.255.255.255", DEFAULT_TEST_URI, resp -> fail("Connect should not be called")).
        exceptionHandler(error -> testComplete()).
        endHandler(done -> fail()).
        end();
    await();
  }

  @Test
  public void testClientExceptionHandlerCalledWhenServerTerminatesConnection() throws Exception {
    int numReqs = 10;
    CountDownLatch latch = new CountDownLatch(numReqs);
    server.requestHandler(request -> {
      request.response().close();
    }).listen(DEFAULT_HTTP_PORT, onSuccess(s -> {
      // Exception handler should be called for any requests in the pipeline if connection is closed
      for (int i = 0; i < numReqs; i++) {
        client.request(HttpMethod.GET, DEFAULT_HTTP_PORT, DEFAULT_HTTP_HOST, DEFAULT_TEST_URI, resp -> fail("Connect should not be called")).
          exceptionHandler(error -> latch.countDown()).endHandler(done -> fail()).end();
      }
    }));
    awaitLatch(latch);
  }

  @Test
  public void testClientExceptionHandlerCalledWhenServerTerminatesConnectionAfterPartialResponse() throws Exception {
    server.requestHandler(request -> {
      //Write partial response then close connection before completing it
      request.response().setChunked(true).write("foo").close();
    }).listen(DEFAULT_HTTP_PORT, onSuccess(s -> {
      // Exception handler should be called for any requests in the pipeline if connection is closed
      client.request(HttpMethod.GET, DEFAULT_HTTP_PORT, DEFAULT_HTTP_HOST, DEFAULT_TEST_URI, resp ->
        resp.exceptionHandler(t -> testComplete())).exceptionHandler(error -> fail()).end();
    }));
    await();
  }

  @Test
  public void testNoExceptionHandlerCalledWhenResponseReceivedOK() throws Exception {
    server.requestHandler(request -> {
      request.response().end();
    }).listen(DEFAULT_HTTP_PORT, onSuccess(s -> {
      client.get(DEFAULT_HTTP_PORT, DEFAULT_HTTP_HOST, DEFAULT_TEST_URI, resp -> {
        resp.endHandler(v -> {
          vertx.setTimer(100, tid -> testComplete());
        });
        resp.exceptionHandler(t -> {
          fail("Should not be called");
        });
      }).exceptionHandler(t -> {
        fail("Should not be called");
      }).end();
    }));
    await();
  }

  @Test
  public void testDefaultStatus() {
    testStatusCode(-1, null);
  }

  @Test
  public void testDefaultOther() {
    // Doesn't really matter which one we choose
    testStatusCode(405, null);
  }

  @Test
  public void testOverrideStatusMessage() {
    testStatusCode(404, "some message");
  }

  @Test
  public void testOverrideDefaultStatusMessage() {
    testStatusCode(-1, "some other message");
  }

  private void testStatusCode(int code, String statusMessage) {
    server.requestHandler(req -> {
      if (code != -1) {
        req.response().setStatusCode(code);
      }
      if (statusMessage != null) {
        req.response().setStatusMessage(statusMessage);
      }
      req.response().end();
    });

    server.listen(onSuccess(s -> {
      client.request(HttpMethod.GET, DEFAULT_HTTP_PORT, DEFAULT_HTTP_HOST, DEFAULT_TEST_URI, resp -> {
        int theCode;
        if (code == -1) {
          // Default code - 200
          assertEquals(200, resp.statusCode());
          theCode = 200;
        } else {
          theCode = code;
        }
        if (statusMessage != null) {
          assertEquals(statusMessage, resp.statusMessage());
        } else {
          assertEquals(HttpResponseStatus.valueOf(theCode).reasonPhrase(), resp.statusMessage());
        }
        testComplete();
      }).end();
    }));

    await();
  }

  @Test
  public void testResponseTrailersPutAll() {
    testResponseTrailers(false);
  }

  @Test
  public void testResponseTrailersPutIndividually() {
    testResponseTrailers(true);
  }

  private void testResponseTrailers(boolean individually) {
    MultiMap trailers = getHeaders(10);

    server.requestHandler(req -> {
      req.response().setChunked(true);
      if (individually) {
        for (Map.Entry<String, String> header : trailers) {
          req.response().trailers().add(header.getKey(), header.getValue());
        }
      } else {
        req.response().trailers().setAll(trailers);
      }
      req.response().end();
    });

    server.listen(onSuccess(s -> {
      client.request(HttpMethod.GET, DEFAULT_HTTP_PORT, DEFAULT_HTTP_HOST, DEFAULT_TEST_URI, resp -> {
        resp.endHandler(v -> {
          assertEquals(trailers.size(), resp.trailers().size());
          for (Map.Entry<String, String> entry : trailers) {
            assertEquals(entry.getValue(), resp.trailers().get(entry.getKey()));
            assertEquals(entry.getValue(), resp.getTrailer(entry.getKey()));
          }
          testComplete();
        });
      }).end();
    }));

    await();
  }

  @Test
  public void testResponseNoTrailers() {
    server.requestHandler(req -> {
      req.response().setChunked(true);
      req.response().end();
    });

    server.listen(onSuccess(s -> {
      client.request(HttpMethod.GET, DEFAULT_HTTP_PORT, DEFAULT_HTTP_HOST, DEFAULT_TEST_URI, resp -> {
        resp.endHandler(v -> {
          assertTrue(resp.trailers().isEmpty());
          testComplete();
        });
      }).end();
    }));

    await();
  }

  @Test
  public void testUseResponseAfterComplete() {
    server.requestHandler(req -> {
      Buffer buff = Buffer.buffer();
      HttpServerResponse resp = req.response();

      assertFalse(resp.ended());
      resp.end();
      assertTrue(resp.ended());

      assertIllegalStateException(() -> resp.drainHandler(noOpHandler()));
      assertIllegalStateException(() -> resp.end());
      assertIllegalStateException(() -> resp.end("foo"));
      assertIllegalStateException(() -> resp.end(buff));
      assertIllegalStateException(() -> resp.end("foo", "UTF-8"));
      assertIllegalStateException(() -> resp.exceptionHandler(noOpHandler()));
      assertIllegalStateException(() -> resp.setChunked(false));
      assertIllegalStateException(() -> resp.setWriteQueueMaxSize(123));
      assertIllegalStateException(() -> resp.write(buff));
      assertIllegalStateException(() -> resp.write("foo"));
      assertIllegalStateException(() -> resp.write("foo", "UTF-8"));
      assertIllegalStateException(() -> resp.write(buff));
      assertIllegalStateException(() -> resp.writeQueueFull());
      assertIllegalStateException(() -> resp.sendFile("asokdasokd"));

      testComplete();
    });

    server.listen(onSuccess(s -> {
      client.request(HttpMethod.GET, DEFAULT_HTTP_PORT, DEFAULT_HTTP_HOST, DEFAULT_TEST_URI, noOpHandler()).end();
    }));

    await();
  }

  @Test
  public void testResponseBodyBufferAtEnd() {
    Buffer body = TestUtils.randomBuffer(1000);

    server.requestHandler(req -> {
      req.response().end(body);
    });

    server.listen(onSuccess(s -> {
      client.request(HttpMethod.GET, DEFAULT_HTTP_PORT, DEFAULT_HTTP_HOST, DEFAULT_TEST_URI, resp -> {
        resp.bodyHandler(buff -> {
          assertEquals(body, buff);
          testComplete();
        });
      }).end();
    }));

    await();
  }

  @Test
  public void testResponseBodyStringDefaultEncodingAtEnd() {
    testResponseBodyStringAtEnd(null);
  }

  @Test
  public void testResponseBodyStringUTF8AtEnd() {
    testResponseBodyStringAtEnd("UTF-8");
  }

  @Test
  public void testResponseBodyStringUTF16AtEnd() {
    testResponseBodyStringAtEnd("UTF-16");
  }

  private void testResponseBodyStringAtEnd(String encoding) {
    String body = TestUtils.randomUnicodeString(1000);
    Buffer bodyBuff;

    if (encoding == null) {
      bodyBuff = Buffer.buffer(body);
    } else {
      bodyBuff = Buffer.buffer(body, encoding);
    }

    server.requestHandler(req -> {
      if (encoding == null) {
        req.response().end(body);
      } else {
        req.response().end(body, encoding);
      }
    });

    server.listen(onSuccess(s -> {
      client.request(HttpMethod.GET, DEFAULT_HTTP_PORT, DEFAULT_HTTP_HOST, DEFAULT_TEST_URI, resp -> {
        resp.bodyHandler(buff -> {
          assertEquals(bodyBuff, buff);
          testComplete();
        });
      }).end();
    }));

    await();
  }

  @Test
  public void testResponseBodyWriteStringNonChunked() {
    server.requestHandler(req -> {
      assertIllegalStateException(() -> req.response().write("foo"));
      testComplete();
    });

    server.listen(onSuccess(s -> {
      client.request(HttpMethod.POST, DEFAULT_HTTP_PORT, DEFAULT_HTTP_HOST, DEFAULT_TEST_URI, noOpHandler()).end();
    }));

    await();
  }

  @Test
  public void testResponseBodyWriteChunked() {
    testResponseBodyWrite(true);
  }

  @Test
  public void testResponseBodyWriteNonChunked() {
    testResponseBodyWrite(false);
  }

  private void testResponseBodyWrite(boolean chunked) {
    Buffer body = Buffer.buffer();

    int numWrites = 10;
    int chunkSize = 100;

    server.requestHandler(req -> {
      assertFalse(req.response().headWritten());
      if (chunked) {
        req.response().setChunked(true);
      } else {
        req.response().headers().set("Content-Length", String.valueOf(numWrites * chunkSize));
      }
      assertFalse(req.response().headWritten());
      for (int i = 0; i < numWrites; i++) {
        Buffer b = TestUtils.randomBuffer(chunkSize);
        body.appendBuffer(b);
        req.response().write(b);
        assertTrue(req.response().headWritten());
      }
      req.response().end();
      assertTrue(req.response().headWritten());
    });

    server.listen(onSuccess(s -> {
      client.request(HttpMethod.GET, DEFAULT_HTTP_PORT, DEFAULT_HTTP_HOST, DEFAULT_TEST_URI, resp -> {
        resp.bodyHandler(buff -> {
          assertEquals(body, buff);
          testComplete();
        });
      }).end();
    }));

    await();
  }

  @Test
  public void testResponseBodyWriteStringChunkedDefaultEncoding() {
    testResponseBodyWriteString(true, null);
  }

  @Test
  public void testResponseBodyWriteStringChunkedUTF8() {
    testResponseBodyWriteString(true, "UTF-8");
  }

  @Test
  public void testResponseBodyWriteStringChunkedUTF16() {
    testResponseBodyWriteString(true, "UTF-16");
  }

  @Test
  public void testResponseBodyWriteStringNonChunkedDefaultEncoding() {
    testResponseBodyWriteString(false, null);
  }

  @Test
  public void testResponseBodyWriteStringNonChunkedUTF8() {
    testResponseBodyWriteString(false, "UTF-8");
  }

  @Test
  public void testResponseBodyWriteStringNonChunkedUTF16() {
    testResponseBodyWriteString(false, "UTF-16");
  }

  private void testResponseBodyWriteString(boolean chunked, String encoding) {
    String body = TestUtils.randomUnicodeString(1000);
    Buffer bodyBuff;

    if (encoding == null) {
      bodyBuff = Buffer.buffer(body);
    } else {
      bodyBuff = Buffer.buffer(body, encoding);
    }

    server.requestHandler(req -> {
      if (chunked) {
        req.response().setChunked(true);
      } else {
        req.response().headers().set("Content-Length", String.valueOf(bodyBuff.length()));
      }
      if (encoding == null) {
        req.response().write(body);
      } else {
        req.response().write(body, encoding);
      }
      req.response().end();
    });

    server.listen(onSuccess(s -> {
      client.request(HttpMethod.GET, DEFAULT_HTTP_PORT, DEFAULT_HTTP_HOST, DEFAULT_TEST_URI, resp -> {
        resp.bodyHandler(buff -> {
          assertEquals(bodyBuff, buff);
          testComplete();
        });
      }).end();
    }));

    await();
  }

  @Test
  public void testResponseWrite() {
    Buffer body = TestUtils.randomBuffer(1000);

    server.requestHandler(req -> {
      req.response().setChunked(true);
      req.response().write(body);
      req.response().end();
    });

    server.listen(onSuccess(s -> {
      client.request(HttpMethod.POST, DEFAULT_HTTP_PORT, DEFAULT_HTTP_HOST, DEFAULT_TEST_URI, resp -> {
        resp.bodyHandler(buff -> {
          assertEquals(body, buff);
          testComplete();
        });
      }).end();
    }));

    await();
  }

  @Test
  public void testPipeliningOrder() throws Exception {
    client.close();
    client = vertx.createHttpClient(new HttpClientOptions().setKeepAlive(true).setPipelining(true).setMaxPoolSize(1));
    int requests = 100;

    AtomicInteger reqCount = new AtomicInteger(0);
    server.requestHandler(req -> {
      int theCount = reqCount.get();
      assertEquals(theCount, Integer.parseInt(req.headers().get("count")));
      reqCount.incrementAndGet();
      req.response().setChunked(true);
      req.bodyHandler(buff -> {
        assertEquals("This is content " + theCount, buff.toString());
        // We write the response back after a random time to increase the chances of responses written in the
        // wrong order if we didn't implement pipelining correctly
        vertx.setTimer(1 + (long) (10 * Math.random()), id -> {
          req.response().headers().set("count", String.valueOf(theCount));
          req.response().write(buff);
          req.response().end();
        });
      });
    });


    CountDownLatch latch = new CountDownLatch(requests);

    server.listen(onSuccess(s -> {
      vertx.setTimer(500, id -> {
        for (int count = 0; count < requests; count++) {
          int theCount = count;
          HttpClientRequest req = client.request(HttpMethod.POST, DEFAULT_HTTP_PORT, DEFAULT_HTTP_HOST, DEFAULT_TEST_URI, resp -> {
            assertEquals(theCount, Integer.parseInt(resp.headers().get("count")));
            resp.bodyHandler(buff -> {
              assertEquals("This is content " + theCount, buff.toString());
              latch.countDown();
            });
          });
          req.setChunked(true);
          req.headers().set("count", String.valueOf(count));
          req.write("This is content " + count);
          req.end();
        }
      });

    }));

    awaitLatch(latch);

  }

  @Test
  public void testKeepAlive() throws Exception {
    testKeepAlive(true, 5, 10, 5);
  }

  @Test
  public void testNoKeepAlive() throws Exception {
    testKeepAlive(false, 5, 10, 10);
  }

  private void testKeepAlive(boolean keepAlive, int poolSize, int numServers, int expectedConnectedServers) throws Exception {
    client.close();
    CountDownLatch firstCloseLatch = new CountDownLatch(1);
    server.close(onSuccess(v -> firstCloseLatch.countDown()));
    // Make sure server is closed before continuing
    awaitLatch(firstCloseLatch);

    client = vertx.createHttpClient(new HttpClientOptions().setKeepAlive(keepAlive).setPipelining(false).setMaxPoolSize(poolSize));
    int requests = 100;

    // Start the servers
    HttpServer[] servers = new HttpServer[numServers];
    CountDownLatch startServerLatch = new CountDownLatch(numServers);
    Set<HttpServer> connectedServers = new ConcurrentHashSet<>();
    for (int i = 0; i < numServers; i++) {
      HttpServer server = vertx.createHttpServer(new HttpServerOptions().setHost(DEFAULT_HTTP_HOST).setPort(DEFAULT_HTTP_PORT));
      server.requestHandler(req -> {
        connectedServers.add(server);
        req.response().end();
      });
      server.listen(ar -> {
        assertTrue(ar.succeeded());
        startServerLatch.countDown();
      });
      servers[i] = server;
    }

    awaitLatch(startServerLatch);

    CountDownLatch reqLatch = new CountDownLatch(requests);

    // We make sure we execute all the requests on the same context otherwise some responses can come beack when there
    // are no waiters resulting in it being closed so a a new connection is made for the next request resulting in the
    // number of total connections being > pool size (which is correct)
    vertx.runOnContext(v -> {
      for (int count = 0; count < requests; count++) {
        client.request(HttpMethod.GET, DEFAULT_HTTP_PORT, DEFAULT_HTTP_HOST, DEFAULT_TEST_URI, resp -> {
          assertEquals(200, resp.statusCode());
          reqLatch.countDown();
        }).end();
      }
    });

    awaitLatch(reqLatch);

    //client.dispConnCount();
    assertEquals(expectedConnectedServers, connectedServers.size());

    CountDownLatch serverCloseLatch = new CountDownLatch(numServers);
    for (HttpServer server: servers) {
      server.close(ar -> {
        assertTrue(ar.succeeded());
        serverCloseLatch.countDown();
      });
    }

    awaitLatch(serverCloseLatch);
  }

  @Test
  public void testSendFile() throws Exception {
    String content = TestUtils.randomUnicodeString(10000);
    sendFile("test-send-file.html", content, false);
  }

  @Test
  public void testSendFileWithHandler() throws Exception {
    String content = TestUtils.randomUnicodeString(10000);
    sendFile("test-send-file.html", content, true);
  }

  private void sendFile(String fileName, String contentExpected, boolean handler) throws Exception {
    File fileToSend = setupFile(fileName, contentExpected);

    CountDownLatch latch;
    if (handler) {
      latch = new CountDownLatch(2);
    } else {
      latch = new CountDownLatch(1);
    }

    server.requestHandler(req -> {
      if (handler) {
        Handler<AsyncResult<Void>> completionHandler = onSuccess(v -> latch.countDown());
        req.response().sendFile(fileToSend.getAbsolutePath(), completionHandler);
      } else {
        req.response().sendFile(fileToSend.getAbsolutePath());
      }
    });

    server.listen(onSuccess(s -> {
      client.request(HttpMethod.GET, DEFAULT_HTTP_PORT, DEFAULT_HTTP_HOST, DEFAULT_TEST_URI, resp -> {
        assertEquals(200, resp.statusCode());

        assertEquals("text/html", resp.headers().get("Content-Type"));
        resp.bodyHandler(buff -> {
          assertEquals(contentExpected, buff.toString());
          assertEquals(fileToSend.length(), Long.parseLong(resp.headers().get("content-length")));
          latch.countDown();
        });
      }).end();
    }));

    assertTrue("Timed out waiting for test to complete.", latch.await(10, TimeUnit.SECONDS));

    testComplete();
  }

  @Test
  public void testSendFileOverrideHeaders() throws Exception {
    String content = TestUtils.randomUnicodeString(10000);
    File file = setupFile("test-send-file.html", content);

    server.requestHandler(req -> {
      req.response().putHeader("Content-Type", "wibble");
      req.response().sendFile(file.getAbsolutePath());
    });

    server.listen(onSuccess(s -> {
      client.request(HttpMethod.GET, DEFAULT_HTTP_PORT, DEFAULT_HTTP_HOST, DEFAULT_TEST_URI, resp -> {
        assertEquals(file.length(), Long.parseLong(resp.headers().get("content-length")));
        assertEquals("wibble", resp.headers().get("content-type"));
        resp.bodyHandler(buff -> {
          assertEquals(content, buff.toString());
          file.delete();
          testComplete();
        });
      }).end();
    }));

    await();
  }

  @Test
  public void testSendFileNotFound() throws Exception {

    server.requestHandler(req -> {
      req.response().putHeader("Content-Type", "wibble");
      req.response().sendFile("nosuchfile.html");
    });

    server.listen(onSuccess(s -> {
      client.request(HttpMethod.GET, DEFAULT_HTTP_PORT, DEFAULT_HTTP_HOST, DEFAULT_TEST_URI, resp -> {
        fail("Should not receive response");
      }).end();
      vertx.setTimer(100, tid -> testComplete());
    }));

    await();
  }

  @Test
  public void testSendFileNotFoundWithHandler() throws Exception {

    server.requestHandler(req -> {
      req.response().putHeader("Content-Type", "wibble");
      req.response().sendFile("nosuchfile.html", onFailure(t -> {
        assertTrue(t instanceof FileNotFoundException);
        testComplete();
      }));
    });

    server.listen(onSuccess(s -> {
      client.request(HttpMethod.GET, DEFAULT_HTTP_PORT, DEFAULT_HTTP_HOST, DEFAULT_TEST_URI, resp -> {
        fail("Should not receive response");
      }).end();
    }));

    await();
  }

  @Test
  public void testSendFileDirectoryWithHandler() throws Exception {

    File dir = testFolder.newFolder();

    server.requestHandler(req -> {
      req.response().putHeader("Content-Type", "wibble");
      req.response().sendFile(dir.getAbsolutePath(), onFailure(t -> {
        assertTrue(t instanceof FileNotFoundException);
        testComplete();
      }));
    });

    server.listen(onSuccess(s -> {
      client.request(HttpMethod.GET, DEFAULT_HTTP_PORT, DEFAULT_HTTP_HOST, DEFAULT_TEST_URI, resp -> {
        fail("Should not receive response");
      }).end();
    }));

    await();
  }

  @Test
  public void test100ContinueHandledAutomatically() throws Exception {
    Buffer toSend = TestUtils.randomBuffer(1000);

    server.requestHandler(req -> {
      req.bodyHandler(data -> {
        assertEquals(toSend, data);
        req.response().end();
      });
    });

    server.listen(onSuccess(s -> {
      HttpClientRequest req = client.request(HttpMethod.PUT, DEFAULT_HTTP_PORT, DEFAULT_HTTP_HOST, DEFAULT_TEST_URI, resp -> {
        resp.endHandler(v -> testComplete());
      });
      req.headers().set("Expect", "100-continue");
      req.setChunked(true);
      req.continueHandler(v -> {
        req.write(toSend);
        req.end();
      });
      req.sendHead();
    }));

    await();
  }

  @Test
  public void test100ContinueHandledManually() throws Exception {

    server.close();
    server = vertx.createHttpServer(new HttpServerOptions().setPort(DEFAULT_HTTP_PORT).setHost(DEFAULT_HTTP_HOST));

    Buffer toSend = TestUtils.randomBuffer(1000);
    server.requestHandler(req -> {
      assertEquals("100-continue", req.getHeader("expect"));
      req.response().writeContinue();
      req.bodyHandler(data -> {
        assertEquals(toSend, data);
        req.response().end();
      });
    });

    server.listen(onSuccess(s -> {
      HttpClientRequest req = client.request(HttpMethod.PUT, DEFAULT_HTTP_PORT, DEFAULT_HTTP_HOST, DEFAULT_TEST_URI, resp -> {
        resp.endHandler(v -> testComplete());
      });
      req.headers().set("Expect", "100-continue");
      req.setChunked(true);
      req.continueHandler(v -> {
        req.write(toSend);
        req.end();
      });
      req.sendHead();
    }));

    await();
  }

  @Test
  public void test100ContinueRejectedManually() throws Exception {

    server.close();
    server = vertx.createHttpServer(new HttpServerOptions().setPort(DEFAULT_HTTP_PORT).setHost(DEFAULT_HTTP_HOST));

    server.requestHandler(req -> {
      req.response().setStatusCode(405).end();
      req.bodyHandler(data -> {
        fail("body should not be received");
      });
    });

    server.listen(onSuccess(s -> {
      HttpClientRequest req = client.request(HttpMethod.PUT, DEFAULT_HTTP_PORT, DEFAULT_HTTP_HOST, DEFAULT_TEST_URI, resp -> {
        assertEquals(405, resp.statusCode());
        testComplete();
      });
      req.headers().set("Expect", "100-continue");
      req.setChunked(true);
      req.continueHandler(v -> {
        fail("should not be called");
      });
      req.sendHead();
    }));

    await();
  }

  @Test
  public void testClientDrainHandler() {
    pausingServer(s -> {
      HttpClientRequest req = client.request(HttpMethod.GET, DEFAULT_HTTP_PORT, DEFAULT_HTTP_HOST, DEFAULT_TEST_URI, noOpHandler());
      req.setChunked(true);
      assertFalse(req.writeQueueFull());
      req.setWriteQueueMaxSize(1000);
      Buffer buff = TestUtils.randomBuffer(10000);
      vertx.setPeriodic(1, id -> {
        req.write(buff);
        if (req.writeQueueFull()) {
          vertx.cancelTimer(id);
          req.drainHandler(v -> {
            assertFalse(req.writeQueueFull());
            testComplete();
          });

          // Tell the server to resume
          vertx.eventBus().send("server_resume", "");
        }
      });
    });

    await();
  }

  @Test
  public void testServerDrainHandler() {
    drainingServer(s -> {
      client.request(HttpMethod.GET, DEFAULT_HTTP_PORT, DEFAULT_HTTP_HOST, DEFAULT_TEST_URI, resp -> {
        resp.pause();
        Handler<Message<Buffer>> resumeHandler = msg -> resp.resume();
        MessageConsumer reg = vertx.eventBus().<Buffer>consumer("client_resume").handler(resumeHandler);
        resp.endHandler(v -> reg.unregister());
      }).end();
    });

    await();
  }

  @Test
  public void testPoolingKeepAliveAndPipelining() {
    testPooling(true, true);
  }

  @Test
  public void testPoolingKeepAliveNoPipelining() {
    testPooling(true, false);
  }

  @Test
  public void testPoolingNoKeepAliveNoPipelining() {
    testPooling(false, false);
  }

  @Test
  public void testPoolingNoKeepAliveAndPipelining() {
    testPooling(false, true);
  }

  private void testPooling(boolean keepAlive, boolean pipelining) {
    String path = "foo.txt";
    int numGets = 100;
    int maxPoolSize = 10;
    client.close();
    client = vertx.createHttpClient(new HttpClientOptions().setKeepAlive(keepAlive).setPipelining(pipelining).setMaxPoolSize(maxPoolSize));

    server.requestHandler(req -> {
      String cnt = req.headers().get("count");
      req.response().headers().set("count", cnt);
      req.response().end();
    });

    AtomicBoolean completeAlready = new AtomicBoolean();

    server.listen(onSuccess(s -> {

      AtomicInteger cnt = new AtomicInteger(0);
      for (int i = 0; i < numGets; i++) {
        int theCount = i;
        HttpClientRequest req = client.request(HttpMethod.GET, DEFAULT_HTTP_PORT, DEFAULT_HTTP_HOST, path, resp -> {
          assertEquals(200, resp.statusCode());
          assertEquals(theCount, Integer.parseInt(resp.headers().get("count")));
          if (cnt.incrementAndGet() == numGets) {
            testComplete();
          }
        });
        req.exceptionHandler(t -> {
          if (pipelining && !keepAlive) {
            // Illegal combination - should get exception
            assertTrue(t instanceof IllegalStateException);
            if (completeAlready.compareAndSet(false, true)) {
              testComplete();
            }
          } else {
            fail("Should not throw exception: " + t.getMessage());
          }
        });
        req.headers().set("count", String.valueOf(i));
        req.end();
      }
    }));

    await();
  }

  @Test
  public void testConnectionErrorsGetReportedToRequest() throws InterruptedException {
    AtomicInteger req1Exceptions = new AtomicInteger();
    AtomicInteger req2Exceptions = new AtomicInteger();
    AtomicInteger req3Exceptions = new AtomicInteger();

    CountDownLatch latch = new CountDownLatch(3);

    // This one should cause an error in the Client Exception handler, because it has no exception handler set specifically.
    HttpClientRequest req1 = client.request(HttpMethod.GET, 9998, DEFAULT_HTTP_HOST, "someurl1", resp -> {
      fail("Should never get a response on a bad port, if you see this message than you are running an http server on port 9998");
    });

    req1.exceptionHandler(t -> {
      assertEquals("More than one call to req1 exception handler was not expected", 1, req1Exceptions.incrementAndGet());
      latch.countDown();
    });

    HttpClientRequest req2 = client.request(HttpMethod.GET, 9998, DEFAULT_HTTP_HOST, "someurl2", resp -> {
      fail("Should never get a response on a bad port, if you see this message than you are running an http server on port 9998");
    });

    req2.exceptionHandler(t -> {
      assertEquals("More than one call to req2 exception handler was not expected", 1, req2Exceptions.incrementAndGet());
      latch.countDown();
    });

    HttpClientRequest req3 = client.request(HttpMethod.GET, 9998, DEFAULT_HTTP_HOST, "someurl2", resp -> {
      fail("Should never get a response on a bad port, if you see this message than you are running an http server on port 9998");
    });

    req3.exceptionHandler(t -> {
      assertEquals("More than one call to req2 exception handler was not expected", 1, req3Exceptions.incrementAndGet());
      latch.countDown();
    });

    req1.end();
    req2.end();
    req3.end();

    awaitLatch(latch);
    testComplete();
  }

  @Test
  public void testRequestTimesoutWhenIndicatedPeriodExpiresWithoutAResponseFromRemoteServer() {
    server.requestHandler(noOpHandler()); // No response handler so timeout triggers

    server.listen(onSuccess(s -> {
      HttpClientRequest req = client.request(HttpMethod.GET, DEFAULT_HTTP_PORT, DEFAULT_HTTP_HOST, DEFAULT_TEST_URI, resp -> {
        fail("End should not be called because the request should timeout");
      });
      req.exceptionHandler(t -> {
        assertTrue("Expected to end with timeout exception but ended with other exception: " + t, t instanceof TimeoutException);
        testComplete();
      });
      req.setTimeout(1000);
      req.end();
    }));

    await();
  }

  @Test
  public void testRequestTimeoutExtendedWhenResponseChunksReceived() {
    long timeout = 2000;
    int numChunks = 100;
    AtomicInteger count = new AtomicInteger(0);
    long interval = timeout * 2 / numChunks;

    server.requestHandler(req -> {
      req.response().setChunked(true);
      vertx.setPeriodic(interval, timerID -> {
        req.response().write("foo");
        if (count.incrementAndGet() == numChunks) {
          req.response().end();
          vertx.cancelTimer(timerID);
        }
      });
    });

    server.listen(onSuccess(s -> {
      HttpClientRequest req = client.request(HttpMethod.GET, DEFAULT_HTTP_PORT, DEFAULT_HTTP_HOST, DEFAULT_TEST_URI, resp -> {
        assertEquals(200, resp.statusCode());
        resp.endHandler(v -> testComplete());
      });
      req.exceptionHandler(t -> fail("Should not be called"));
      req.setTimeout(timeout);
      req.end();
    }));

    await();
  }

  @Test
  public void testRequestTimeoutCanceledWhenRequestHasAnOtherError() {
    AtomicReference<Throwable> exception = new AtomicReference<>();
    // There is no server running, should fail to connect
    HttpClientRequest req = client.request(HttpMethod.GET, DEFAULT_HTTP_PORT, DEFAULT_HTTP_HOST, DEFAULT_TEST_URI, resp -> {
      fail("End should not be called because the request should fail to connect");
    });
    req.exceptionHandler(exception::set);
    req.setTimeout(800);
    req.end();

    vertx.setTimer(1500, id -> {
      assertNotNull("Expected an exception to be set", exception.get());
      assertFalse("Expected to not end with timeout exception, but did: " + exception.get(), exception.get() instanceof TimeoutException);
      testComplete();
    });

    await();
  }

  @Test
  public void testRequestTimeoutCanceledWhenRequestEndsNormally() {
    server.requestHandler(req -> req.response().end());

    server.listen(onSuccess(s -> {
      AtomicReference<Throwable> exception = new AtomicReference<>();

      // There is no server running, should fail to connect
      HttpClientRequest req = client.request(HttpMethod.GET, DEFAULT_HTTP_PORT, DEFAULT_HTTP_HOST, DEFAULT_TEST_URI, noOpHandler());
      req.exceptionHandler(exception::set);
      req.setTimeout(500);
      req.end();

      vertx.setTimer(1000, id -> {
        assertNull("Did not expect any exception", exception.get());
        testComplete();
      });
    }));

    await();
  }

  @Test
  public void testRequestNotReceivedIfTimedout() {
    server.requestHandler(req -> {
      vertx.setTimer(500, id -> {
        req.response().setStatusCode(200);
        req.response().end("OK");
      });
    });

    server.listen(onSuccess(s -> {
      HttpClientRequest req = client.request(HttpMethod.GET, DEFAULT_HTTP_PORT, DEFAULT_HTTP_HOST, DEFAULT_TEST_URI, resp -> fail("Response should not be handled"));
      req.exceptionHandler(t -> {
        assertTrue("Expected to end with timeout exception but ended with other exception: " + t, t instanceof TimeoutException);
        //Delay a bit to let any response come back
        vertx.setTimer(500, id -> testComplete());
      });
      req.setTimeout(100);
      req.end();
    }));

    await();
  }

  @Test
  public void testServerWebsocketIdleTimeout() {
    server.close();
    server = vertx.createHttpServer(new HttpServerOptions().setIdleTimeout(1).setPort(DEFAULT_HTTP_PORT).setHost(DEFAULT_HTTP_HOST));
    server.websocketHandler(ws -> {}).listen(ar -> {
      assertTrue(ar.succeeded());
      client.websocket(DEFAULT_HTTP_PORT, DEFAULT_HTTP_HOST, "/", ws -> {
        ws.closeHandler(v -> testComplete());
      });
    });

    await();
  }


  @Test
  public void testClientWebsocketIdleTimeout() {
    client.close();
    client = vertx.createHttpClient(new HttpClientOptions().setIdleTimeout(1));
    server.websocketHandler(ws -> {}).listen(ar -> {
      client.websocket(DEFAULT_HTTP_PORT, DEFAULT_HTTP_HOST, "/", ws -> {
        ws.closeHandler(v -> testComplete());
      });

    });

    await();
  }

  @Test
  // Client trusts all server certs
  public void testTLSClientTrustAll() throws Exception {
    testTLS(KeyCert.NONE, Trust.NONE, KeyCert.JKS, Trust.NONE, false, false, true, false, true);
  }

  @Test
  // Server specifies cert that the client trusts (not trust all)
  public void testTLSClientTrustServerCert() throws Exception {
    testTLS(KeyCert.NONE, Trust.JKS, KeyCert.JKS, Trust.NONE, false, false, false, false, true);
  }

  @Test
  // Server specifies cert that the client trusts (not trust all)
  public void testTLSClientTrustServerCertPKCS12() throws Exception {
    testTLS(KeyCert.NONE, Trust.JKS, KeyCert.PKCS12, Trust.NONE, false, false, false, false, true);
  }

  @Test
  // Server specifies cert that the client trusts (not trust all)
  public void testTLSClientTrustServerCertPEM() throws Exception {
    testTLS(KeyCert.NONE, Trust.JKS, KeyCert.PEM, Trust.NONE, false, false, false, false, true);
  }

  @Test
  // Server specifies cert that the client trusts via a CA (not trust all)
  public void testTLSClientTrustServerCertJKS_CAWithJKS_CA() throws Exception {
    testTLS(KeyCert.NONE, Trust.JKS_CA, KeyCert.JKS_CA, Trust.NONE, false, false, false, false, true);
  }

  @Test
  // Server specifies cert that the client trusts via a CA (not trust all)
  public void testTLSClientTrustServerCertJKS_CAWithPKCS12_CA() throws Exception {
    testTLS(KeyCert.NONE, Trust.PKCS12_CA, KeyCert.JKS_CA, Trust.NONE, false, false, false, false, true);
  }

  @Test
  // Server specifies cert that the client trusts via a CA (not trust all)
  public void testTLSClientTrustServerCertJKS_CAWithPEM_CA() throws Exception {
    testTLS(KeyCert.NONE, Trust.PEM_CA, KeyCert.JKS_CA, Trust.NONE, false, false, false, false, true);
  }

  @Test
  // Server specifies cert that the client trusts via a CA (not trust all)
  public void testTLSClientTrustServerCertPKCS12_CAWithJKS_CA() throws Exception {
    testTLS(KeyCert.NONE, Trust.JKS_CA, KeyCert.PKCS12_CA, Trust.NONE, false, false, false, false, true);
  }

  @Test
  // Server specifies cert that the client trusts via a CA (not trust all)
  public void testTLSClientTrustServerCertPKCS12_CAWithPKCS12_CA() throws Exception {
    testTLS(KeyCert.NONE, Trust.PKCS12_CA, KeyCert.PKCS12_CA, Trust.NONE, false, false, false, false, true);
  }

  @Test
  // Server specifies cert that the client trusts via a CA (not trust all)
  public void testTLSClientTrustServerCertPKCS12_CAWithPEM_CA() throws Exception {
    testTLS(KeyCert.NONE, Trust.PEM_CA, KeyCert.PKCS12_CA, Trust.NONE, false, false, false, false, true);
  }

  @Test
  // Server specifies cert that the client trusts via a CA (not trust all)
  public void testTLSClientTrustServerCertPEM_CAWithJKS_CA() throws Exception {
    testTLS(KeyCert.NONE, Trust.JKS_CA, KeyCert.PEM_CA, Trust.NONE, false, false, false, false, true);
  }

  @Test
  // Server specifies cert that the client trusts via a CA (not trust all)
  public void testTLSClientTrustServerCertPEM_CAWithPKCS12_CA() throws Exception {
    testTLS(KeyCert.NONE, Trust.PKCS12_CA, KeyCert.PEM_CA, Trust.NONE, false, false, false, false, true);
  }

  @Test
  // Server specifies cert that the client trusts via a CA (not trust all)
  public void testTLSClientTrustServerCertPEM_CAWithPEM_CA() throws Exception {
    testTLS(KeyCert.NONE, Trust.PEM_CA, KeyCert.PEM_CA, Trust.NONE, false, false, false, false, true);
  }

  @Test
  // Server specifies cert that the client trusts (not trust all)
  public void testTLSClientTrustPKCS12ServerCert() throws Exception {
    testTLS(KeyCert.NONE, Trust.PKCS12, KeyCert.JKS, Trust.NONE, false, false, false, false, true);
  }

  @Test
  // Server specifies cert that the client trusts (not trust all)
  public void testTLSClientTrustPEMServerCert() throws Exception {
    testTLS(KeyCert.NONE, Trust.PEM, KeyCert.JKS, Trust.NONE, false, false, false, false, true);
  }

  @Test
  // Server specifies cert that the client doesn't trust
  public void testTLSClientUntrustedServer() throws Exception {
    testTLS(KeyCert.NONE, Trust.NONE, KeyCert.JKS, Trust.NONE, false, false, false, false, false);
  }

  @Test
  // Server specifies cert that the client doesn't trust
  public void testTLSClientUntrustedServerPEM() throws Exception {
    testTLS(KeyCert.NONE, Trust.NONE, KeyCert.PEM, Trust.NONE, false, false, false, false, false);
  }

  @Test
  //Client specifies cert even though it's not required
  public void testTLSClientCertNotRequired() throws Exception {
    testTLS(KeyCert.JKS, Trust.JKS, KeyCert.JKS, Trust.JKS, false, false, false, false, true);
  }

  @Test
  //Client specifies cert even though it's not required
  public void testTLSClientCertNotRequiredPEM() throws Exception {
    testTLS(KeyCert.JKS, Trust.JKS, KeyCert.PEM, Trust.JKS, false, false, false, false, true);
  }

  @Test
  //Client specifies cert and it is required
  public void testTLSClientCertRequired() throws Exception {
    testTLS(KeyCert.JKS, Trust.JKS, KeyCert.JKS, Trust.JKS, true, false, false, false, true);
  }

  @Test
  //Client specifies cert and it is required
  public void testTLSClientCertRequiredPKCS12() throws Exception {
    testTLS(KeyCert.JKS, Trust.JKS, KeyCert.JKS, Trust.PKCS12, true, false, false, false, true);
  }

  @Test
  //Client specifies cert and it is required
  public void testTLSClientCertRequiredPEM() throws Exception {
    testTLS(KeyCert.JKS, Trust.JKS, KeyCert.JKS, Trust.PEM, true, false, false, false, true);
  }

  @Test
  //Client specifies cert and it is required
  public void testTLSClientCertPKCS12Required() throws Exception {
    testTLS(KeyCert.PKCS12, Trust.JKS, KeyCert.JKS, Trust.JKS, true, false, false, false, true);
  }

  @Test
  //Client specifies cert and it is required
  public void testTLSClientCertPEMRequired() throws Exception {
    testTLS(KeyCert.PEM, Trust.JKS, KeyCert.JKS, Trust.JKS, true, false, false, false, true);
  }

  @Test
  //Client specifies cert by CA and it is required
  public void testTLSClientCertPEM_CARequired() throws Exception {
    testTLS(KeyCert.PEM_CA, Trust.JKS, KeyCert.JKS, Trust.PEM_CA, true, false, false, false, true);
  }

  @Test
  //Client doesn't specify cert but it's required
  public void testTLSClientCertRequiredNoClientCert() throws Exception {
    testTLS(KeyCert.NONE, Trust.JKS, KeyCert.JKS, Trust.JKS, true, false, false, false, false);
  }

  @Test
  //Client specifies cert but it's not trusted
  public void testTLSClientCertClientNotTrusted() throws Exception {
    testTLS(KeyCert.JKS, Trust.JKS, KeyCert.JKS, Trust.NONE, true, false, false, false, false);
  }

  @Test
  // Server specifies cert that the client does not trust via a revoked certificate of the CA
  public void testTLSClientRevokedServerCert() throws Exception {
    testTLS(KeyCert.NONE, Trust.PEM_CA, KeyCert.PEM_CA, Trust.NONE, false, false, false, true, false);
  }

  @Test
  //Client specifies cert that the server does not trust via a revoked certificate of the CA
  public void testTLSRevokedClientCertServer() throws Exception {
    testTLS(KeyCert.PEM_CA, Trust.JKS, KeyCert.JKS, Trust.PEM_CA, true, true, false, false, false);
  }

  @Test
  // Specify some cipher suites
  public void testTLSCipherSuites() throws Exception {
    testTLS(KeyCert.NONE, Trust.NONE, KeyCert.JKS, Trust.NONE, false, false, true, false, true, ENABLED_CIPHER_SUITES);
  }

  private void testTLS(KeyCert clientCert, Trust clientTrust,
                       KeyCert serverCert, Trust serverTrust,
                       boolean requireClientAuth, boolean serverUsesCrl, boolean clientTrustAll,
                       boolean clientUsesCrl, boolean shouldPass,
                       String... enabledCipherSuites) throws Exception {
    client.close();
    server.close();
    HttpClientOptions options = new HttpClientOptions();
    options.setSsl(true);
    if (clientTrustAll) {
      options.setTrustAll(true);
    }
    if (clientUsesCrl) {
      options.addCrlPath(findFileOnClasspath("tls/ca/crl.pem"));
    }
    setOptions(options, getClientTrustOptions(clientTrust));
    setOptions(options, getClientCertOptions(clientCert));
    for (String suite: enabledCipherSuites) {
      options.addEnabledCipherSuite(suite);
    }
    client = vertx.createHttpClient(options);
    HttpServerOptions serverOptions = new HttpServerOptions();
    serverOptions.setSsl(true);
    setOptions(serverOptions, getServerTrustOptions(serverTrust));
    setOptions(serverOptions, getServerCertOptions(serverCert));
    if (requireClientAuth) {
      serverOptions.setClientAuthRequired(true);
    }
    if (serverUsesCrl) {
      serverOptions.addCrlPath(findFileOnClasspath("tls/ca/crl.pem"));
    }
    for (String suite: enabledCipherSuites) {
      serverOptions.addEnabledCipherSuite(suite);
    }
    server = vertx.createHttpServer(serverOptions.setPort(4043));
    server.requestHandler(req -> {
      req.bodyHandler(buffer -> {
        assertEquals("foo", buffer.toString());
        req.response().end("bar");
      });
    });
    server.listen(ar -> {
      assertTrue(ar.succeeded());

      HttpClientRequest req = client.request(HttpMethod.GET, 4043, DEFAULT_HTTP_HOST, DEFAULT_TEST_URI, response -> {
        response.bodyHandler(data -> assertEquals("bar", data.toString()));
        testComplete();
      });
      req.exceptionHandler(t -> {
        if (shouldPass) {
          t.printStackTrace();
          fail("Should not throw exception");
        } else {
          testComplete();
        }
      });
      req.end("foo");
    });
    await();
  }

  @Test
  public void testJKSInvalidPath() {
    testInvalidKeyStore(((JksOptions) getServerCertOptions(KeyCert.JKS)).setPath("/invalid.jks"), "java.nio.file.NoSuchFileException: ", "invalid.jks");
  }

  @Test
  public void testJKSMissingPassword() {
    testInvalidKeyStore(((JksOptions) getServerCertOptions(KeyCert.JKS)).setPassword(null), "Password must not be null", null);
  }

  @Test
  public void testJKSInvalidPassword() {
    testInvalidKeyStore(((JksOptions) getServerCertOptions(KeyCert.JKS)).setPassword("wrongpassword"), "Keystore was tampered with, or password was incorrect", null);
  }

  @Test
  public void testPKCS12InvalidPath() {
    testInvalidKeyStore(((PfxOptions) getServerCertOptions(KeyCert.PKCS12)).setPath("/invalid.p12"), "java.nio.file.NoSuchFileException: ", "invalid.p12");
  }

  @Test
  public void testPKCS12MissingPassword() {
    testInvalidKeyStore(((PfxOptions) getServerCertOptions(KeyCert.PKCS12)).setPassword(null), "Get Key failed: null", null);
  }

  @Test
  public void testPKCS12InvalidPassword() {
    testInvalidKeyStore(((PfxOptions) getServerCertOptions(KeyCert.PKCS12)).setPassword("wrongpassword"), "failed to decrypt safe contents entry: javax.crypto.BadPaddingException: Given final block not properly padded", null);
  }

  @Test
  public void testKeyCertMissingKeyPath() {
    testInvalidKeyStore(((PemKeyCertOptions) getServerCertOptions(KeyCert.PEM)).setKeyPath(null), "Missing private key", null);
  }

  @Test
  public void testKeyCertInvalidKeyPath() {
    testInvalidKeyStore(((PemKeyCertOptions) getServerCertOptions(KeyCert.PEM)).setKeyPath("/invalid.pem"), "java.nio.file.NoSuchFileException: ", "invalid.pem");
  }

  @Test
  public void testKeyCertMissingCertPath() {
    testInvalidKeyStore(((PemKeyCertOptions) getServerCertOptions(KeyCert.PEM)).setCertPath(null), "Missing X.509 certificate", null);
  }

  @Test
  public void testKeyCertInvalidCertPath() {
    testInvalidKeyStore(((PemKeyCertOptions) getServerCertOptions(KeyCert.PEM)).setCertPath("/invalid.pem"), "java.nio.file.NoSuchFileException: ", "invalid.pem");
  }

  @Test
  public void testKeyCertInvalidPem() throws IOException {
    String[] contents = {
        "",
        "-----BEGIN PRIVATE KEY-----",
        "-----BEGIN PRIVATE KEY-----\n-----END PRIVATE KEY-----",
        "-----BEGIN PRIVATE KEY-----\n*\n-----END PRIVATE KEY-----"
    };
    String[] messages = {
        "Missing -----BEGIN PRIVATE KEY----- delimiter",
        "Missing -----END PRIVATE KEY----- delimiter",
        "Empty pem file",
        "Input byte[] should at least have 2 bytes for base64 bytes"
    };
    for (int i = 0;i < contents.length;i++) {
      Path file = testFolder.newFile("vertx" + UUID.randomUUID().toString() + ".pem").toPath();
      Files.write(file, Collections.singleton(contents[i]));
      String expectedMessage = messages[i];
      testInvalidKeyStore(((PemKeyCertOptions) getServerCertOptions(KeyCert.PEM)).setKeyPath(file.toString()), expectedMessage, null);
    }
  }

  @Test
  public void testCaInvalidPath() {
    testInvalidTrustStore(new PemTrustOptions().addCertPath("/invalid.pem"), "java.nio.file.NoSuchFileException: ", "invalid.pem");
  }

  @Test
  public void testCaInvalidPem() throws IOException {
    String[] contents = {
        "",
        "-----BEGIN CERTIFICATE-----",
        "-----BEGIN CERTIFICATE-----\n-----END CERTIFICATE-----",
        "-----BEGIN CERTIFICATE-----\n*\n-----END CERTIFICATE-----"
    };
    String[] messages = {
        "Missing -----BEGIN CERTIFICATE----- delimiter",
        "Missing -----END CERTIFICATE----- delimiter",
        "Empty pem file",
        "Input byte[] should at least have 2 bytes for base64 bytes"
    };
    for (int i = 0;i < contents.length;i++) {
      Path file = testFolder.newFile("vertx" + UUID.randomUUID().toString() + ".pem").toPath();
      Files.write(file, Collections.singleton(contents[i]));
      String expectedMessage = messages[i];
      testInvalidTrustStore(new PemTrustOptions().addCertPath(file.toString()), expectedMessage, null);
    }
  }

  private void testInvalidKeyStore(KeyCertOptions options, String expectedPrefix, String expectedSuffix) {
    HttpServerOptions serverOptions = new HttpServerOptions();
    setOptions(serverOptions, options);
    serverOptions.setSsl(true);
    serverOptions.setPort(4043);
    testStore(serverOptions, expectedPrefix, expectedSuffix);
  }

  private void testInvalidTrustStore(TrustOptions options, String expectedPrefix, String expectedSuffix) {
    HttpServerOptions serverOptions = new HttpServerOptions();
    setOptions(serverOptions, options);
    serverOptions.setSsl(true);
    serverOptions.setPort(4043);
    testStore(serverOptions, expectedPrefix, expectedSuffix);
  }

  private void testStore(HttpServerOptions serverOptions, String expectedPrefix, String expectedSuffix) {
    HttpServer server = vertx.createHttpServer(serverOptions);
    server.requestHandler(req -> {
    });
    try {
      server.listen();
      fail("Was expecting a failure");
    } catch (VertxException e) {
      assertNotNull(e.getCause());
      if(expectedSuffix == null)
        assertEquals(expectedPrefix, e.getCause().getMessage());
      else {
        assertTrue(e.getCause().getMessage().startsWith(expectedPrefix));
        assertTrue(e.getCause().getMessage().endsWith(expectedSuffix));
      }
    }
  }

  @Test
  public void testCrlInvalidPath() throws Exception {
    HttpClientOptions clientOptions = new HttpClientOptions();
    setOptions(clientOptions, getClientTrustOptions(Trust.PEM_CA));
    clientOptions.setSsl(true);
    clientOptions.addCrlPath("/invalid.pem");
    HttpClient client = vertx.createHttpClient(clientOptions);
    HttpClientRequest req = client.request(HttpMethod.CONNECT, DEFAULT_HTTP_PORT, DEFAULT_HTTP_HOST, "/", (handler) -> {});
    try {
      req.end();
      fail("Was expecting a failure");
    } catch (VertxException e) {
      assertNotNull(e.getCause());
      assertEquals(NoSuchFileException.class, e.getCause().getCause().getClass());
    }
  }

  @Test
  public void testConnectInvalidPort() {
    client.request(HttpMethod.GET, 9998, DEFAULT_HTTP_HOST, DEFAULT_TEST_URI, resp -> fail("Connect should not be called")).
        exceptionHandler(t -> testComplete()).
        end();

    await();
  }

  @Test
  public void testConnectInvalidHost() {
    client.request(HttpMethod.GET, 9998, "255.255.255.255", DEFAULT_TEST_URI, resp -> fail("Connect should not be called")).
        exceptionHandler(t -> testComplete()).
        end();

    await();
  }

  @Test
  public void testSetHandlersAfterListening() throws Exception {
    server.requestHandler(noOpHandler());

    server.listen(onSuccess(s -> {
      assertIllegalStateException(() -> server.requestHandler(noOpHandler()));
      assertIllegalStateException(() -> server.websocketHandler(noOpHandler()));
      testComplete();
    }));

    await();
  }

  @Test
  public void testSetHandlersAfterListening2() throws Exception {
    server.requestHandler(noOpHandler());

    server.listen();
    assertIllegalStateException(() -> server.requestHandler(noOpHandler()));
    assertIllegalStateException(() -> server.websocketHandler(noOpHandler()));
  }

  @Test
  public void testListenNoHandlers() throws Exception {
    assertIllegalStateException(() -> server.listen(ar -> {}));
  }

  @Test
  public void testListenNoHandlers2() throws Exception {
    assertIllegalStateException(() -> server.listen());
  }

  @Test
  public void testListenTwice() throws Exception {
    server.requestHandler(noOpHandler());
    server.listen();
    assertIllegalStateException(() -> server.listen());
  }

  @Test
  public void testListenTwice2() throws Exception {
    server.requestHandler(noOpHandler());
    server.listen(ar -> {
      assertTrue(ar.succeeded());
      assertIllegalStateException(() -> server.listen());
      testComplete();
    });
    await();
  }

  @Test
  public void testSharedServersRoundRobin() throws Exception {
    client.close();
    server.close();
    client = vertx.createHttpClient(new HttpClientOptions().setKeepAlive(false));
    int numServers = 5;
    int numRequests = numServers * 100;

    List<HttpServer> servers = new ArrayList<>();
    Set<HttpServer> connectedServers = Collections.newSetFromMap(new ConcurrentHashMap<>());
    Map<HttpServer, Integer> requestCount = new ConcurrentHashMap<>();

    CountDownLatch latchListen = new CountDownLatch(numServers);
    CountDownLatch latchConns = new CountDownLatch(numRequests);
    Set<Context> contexts = new ConcurrentHashSet<>();
    for (int i = 0; i < numServers; i++) {
      HttpServer theServer = vertx.createHttpServer(new HttpServerOptions().setPort(DEFAULT_HTTP_PORT));
      servers.add(theServer);
      final AtomicReference<Context> context = new AtomicReference<>();
      theServer.requestHandler(req -> {
        Context ctx = Vertx.currentContext();
        if (context.get() != null) {
          assertSame(ctx, context.get());
        } else {
          context.set(ctx);
          contexts.add(ctx);
        }
        connectedServers.add(theServer);
        Integer cnt = requestCount.get(theServer);
        int icnt = cnt == null ? 0 : cnt;
        icnt++;
        requestCount.put(theServer, icnt);
        latchConns.countDown();
        req.response().end();
      }).listen(onSuccess(s -> latchListen.countDown()));
    }
    assertTrue(latchListen.await(10, TimeUnit.SECONDS));


    // Create a bunch of connections
    CountDownLatch latchClient = new CountDownLatch(numRequests);
    for (int i = 0; i < numRequests; i++) {
      client.request(HttpMethod.GET, DEFAULT_HTTP_PORT, DEFAULT_HTTP_HOST, DEFAULT_TEST_URI, res -> latchClient.countDown()).end();
    }

    assertTrue(latchClient.await(10, TimeUnit.SECONDS));
    assertTrue(latchConns.await(10, TimeUnit.SECONDS));

    assertEquals(numServers, connectedServers.size());
    for (HttpServer server : servers) {
      assertTrue(connectedServers.contains(server));
    }
    assertEquals(numServers, requestCount.size());
    for (int cnt : requestCount.values()) {
      assertEquals(numRequests / numServers, cnt);
    }
    assertEquals(numServers, contexts.size());

    CountDownLatch closeLatch = new CountDownLatch(numServers);

    for (HttpServer server : servers) {
      server.close(ar -> {
        assertTrue(ar.succeeded());
        closeLatch.countDown();
      });
    }

    assertTrue(closeLatch.await(10, TimeUnit.SECONDS));

    testComplete();
  }

  @Test
  public void testSharedServersRoundRobinWithOtherServerRunningOnDifferentPort() throws Exception {
    // Have a server running on a different port to make sure it doesn't interact
    CountDownLatch latch = new CountDownLatch(1);
    HttpServer theServer = vertx.createHttpServer(new HttpServerOptions().setPort(8081));
    theServer.requestHandler(req -> {
      fail("Should not process request");
    }).listen(onSuccess(s -> latch.countDown()));
    awaitLatch(latch);

    testSharedServersRoundRobin();
  }

  @Test
  public void testSharedServersRoundRobinButFirstStartAndStopServer() throws Exception {
    // Start and stop a server on the same port/host before hand to make sure it doesn't interact
    CountDownLatch latch = new CountDownLatch(1);
    HttpServer theServer = vertx.createHttpServer(new HttpServerOptions().setPort(DEFAULT_HTTP_PORT));
    theServer.requestHandler(req -> {
      fail("Should not process request");
    }).listen(onSuccess(s -> latch.countDown()));
    awaitLatch(latch);

    CountDownLatch closeLatch = new CountDownLatch(1);
    theServer.close(ar -> {
      assertTrue(ar.succeeded());
      closeLatch.countDown();
    });
    assertTrue(closeLatch.await(10, TimeUnit.SECONDS));

    testSharedServersRoundRobin();
  }

  @Test
  public void testHeadNoBody() {
    server.requestHandler(req -> {
      assertEquals(HttpMethod.HEAD, req.method());
      // Head never contains a body but it can contain a Content-Length header
      // Since headers from HEAD must correspond EXACTLY with corresponding headers for GET
      req.response().headers().set("Content-Length", String.valueOf(41));
      req.response().end();
    });

    server.listen(onSuccess(s -> {
      client.request(HttpMethod.HEAD, DEFAULT_HTTP_PORT, DEFAULT_HTTP_HOST, DEFAULT_TEST_URI, resp -> {
        assertEquals(41, Integer.parseInt(resp.headers().get("Content-Length")));
        resp.endHandler(v -> testComplete());
      }).end();
    }));

    await();
  }

  @Test
  public void testRemoteAddress() {
    server.requestHandler(req -> {
      assertEquals("127.0.0.1", req.remoteAddress().host());
      req.response().end();
    });

    server.listen(onSuccess(s -> {
      client.request(HttpMethod.GET, DEFAULT_HTTP_PORT, DEFAULT_HTTP_HOST, DEFAULT_TEST_URI, resp -> resp.endHandler(v -> testComplete())).end();
    }));

    await();
  }

  @Test
  public void testGetAbsoluteURI() {
    server.requestHandler(req -> {
      assertEquals("http://localhost:" + DEFAULT_HTTP_PORT + "/foo/bar", req.absoluteURI().toString());
      req.response().end();
    });

    server.listen(onSuccess(s -> {
      client.request(HttpMethod.GET, DEFAULT_HTTP_PORT, DEFAULT_HTTP_HOST, "/foo/bar", resp -> resp.endHandler(v -> testComplete())).end();
    }));

    await();
  }

  @Test
  public void testListenInvalidPort() throws Exception {
    /* Port 7 is free for use by any application in Windows, so this test fails. */
    Assume.assumeFalse(System.getProperty("os.name").startsWith("Windows"));
    server.close();
    server = vertx.createHttpServer(new HttpServerOptions().setPort(7));
    server.requestHandler(noOpHandler()).listen(onFailure(server -> testComplete()));
    await();
  }

  @Test
  public void testListenInvalidHost() {
    server.close();
    server = vertx.createHttpServer(new HttpServerOptions().setPort(DEFAULT_HTTP_PORT).setHost("iqwjdoqiwjdoiqwdiojwd"));
    server.requestHandler(noOpHandler());
    server.listen(onFailure(s -> testComplete()));
  }

  @Test
  public void testPauseClientResponse() {
    int numWrites = 10;
    int numBytes = 100;
    server.requestHandler(req -> {
      req.response().setChunked(true);
      // Send back a big response in several chunks
      for (int i = 0; i < numWrites; i++) {
        req.response().write(TestUtils.randomBuffer(numBytes));
      }
      req.response().end();
    });

    AtomicBoolean paused = new AtomicBoolean();
    Buffer totBuff = Buffer.buffer();
    HttpClientRequest clientRequest = client.request(HttpMethod.GET, DEFAULT_HTTP_PORT, DEFAULT_HTTP_HOST, DEFAULT_TEST_URI, resp -> {
      resp.pause();
      paused.set(true);
      resp.handler(chunk -> {
        if (paused.get()) {
          fail("Shouldn't receive chunks when paused");
        } else {
          totBuff.appendBuffer(chunk);
        }
      });
      resp.endHandler(v -> {
        if (paused.get()) {
          fail("Shouldn't receive chunks when paused");
        } else {
          assertEquals(numWrites * numBytes, totBuff.length());
          testComplete();
        }
      });
      vertx.setTimer(500, id -> {
        paused.set(false);
        resp.resume();
      });
    });

    server.listen(onSuccess(s -> clientRequest.end()));

    await();
  }

  @Test
  public void testHttpVersion() {
    server.requestHandler(req -> {
      assertEquals(HttpVersion.HTTP_1_1, req.version());
      req.response().end();
    });

    server.listen(onSuccess(s -> {
      client.request(HttpMethod.GET, DEFAULT_HTTP_PORT, DEFAULT_HTTP_HOST, DEFAULT_TEST_URI, resp -> resp.endHandler(v -> testComplete())).end();
    }));

    await();
  }

  @Test
  public void testFormUploadSmallFile() throws Exception {
    testFormUploadFile(TestUtils.randomAlphaString(100), false);
  }

  @Test
  public void testFormUploadLargerFile() throws Exception {
    testFormUploadFile(TestUtils.randomAlphaString(20000), false);
  }

  @Test
  public void testFormUploadSmallFileStreamToDisk() throws Exception {
    testFormUploadFile(TestUtils.randomAlphaString(100), true);
  }

  @Test
  public void testFormUploadLargerFileStreamToDisk() throws Exception {
    testFormUploadFile(TestUtils.randomAlphaString(20000), true);
  }

  private void testFormUploadFile(String contentStr, boolean streamToDisk) throws Exception {

    Buffer content = Buffer.buffer(contentStr);

    AtomicInteger attributeCount = new AtomicInteger();

    server.requestHandler(req -> {
      if (req.method() == HttpMethod.POST) {
        assertEquals(req.path(), "/form");
        req.response().setChunked(true);
        req.setExpectMultipart(true);
        assertTrue(req.isExpectMultipart());

        // Now try setting again, it shouldn't have an effect
        req.setExpectMultipart(true);
        assertTrue(req.isExpectMultipart());

        req.uploadHandler(upload -> {
          Buffer tot = Buffer.buffer();
          assertEquals("file", upload.name());
          assertEquals("tmp-0.txt", upload.filename());
          assertEquals("image/gif", upload.contentType());
          String uploadedFileName;
          if (!streamToDisk) {
            upload.handler(buffer -> tot.appendBuffer(buffer));
            uploadedFileName = null;
          } else {
            uploadedFileName = new File(testDir, UUID.randomUUID().toString()).getPath();
            upload.streamToFileSystem(uploadedFileName);
          }
          upload.endHandler(v -> {
            if (streamToDisk) {
              Buffer uploaded = vertx.fileSystem().readFileBlocking(uploadedFileName);
              assertEquals(content, uploaded);
            } else {
              assertEquals(content, tot);
            }
            assertTrue(upload.isSizeAvailable());
            assertEquals(content.length(), upload.size());
          });
        });
        req.endHandler(v -> {
          MultiMap attrs = req.formAttributes();
          attributeCount.set(attrs.size());
          req.response().end();
        });
      }
    });

    server.listen(onSuccess(s -> {
      HttpClientRequest req = client.request(HttpMethod.POST, DEFAULT_HTTP_PORT, DEFAULT_HTTP_HOST, "/form", resp -> {
        // assert the response
        assertEquals(200, resp.statusCode());
        resp.bodyHandler(body -> {
          assertEquals(0, body.length());
        });
        assertEquals(0, attributeCount.get());
        testComplete();
      });

      String boundary = "dLV9Wyq26L_-JQxk6ferf-RT153LhOO";
      Buffer buffer = Buffer.buffer();
      String body =
        "--" + boundary + "\r\n" +
          "Content-Disposition: form-data; name=\"file\"; filename=\"tmp-0.txt\"\r\n" +
          "Content-Type: image/gif\r\n" +
          "\r\n" +
          contentStr + "\r\n" +
          "--" + boundary + "--\r\n";

      buffer.appendString(body);
      req.headers().set("content-length", String.valueOf(buffer.length()));
      req.headers().set("content-type", "multipart/form-data; boundary=" + boundary);
      req.write(buffer).end();
    }));

    await();
  }

  @Test
  public void testFormUploadAttributes() throws Exception {
    AtomicInteger attributeCount = new AtomicInteger();
    server.requestHandler(req -> {
      if (req.method() == HttpMethod.POST) {
        assertEquals(req.path(), "/form");
        req.response().setChunked(true);
        req.setExpectMultipart(true);
        req.uploadHandler(upload -> upload.handler(buffer -> {
          fail("Should get here");
        }));
        req.endHandler(v -> {
          MultiMap attrs = req.formAttributes();
          attributeCount.set(attrs.size());
          assertEquals("vert x", attrs.get("framework"));
          assertEquals("vert x", req.getFormAttribute("framework"));
          assertEquals("jvm", attrs.get("runson"));
          assertEquals("jvm", req.getFormAttribute("runson"));
          req.response().end();
        });
      }
    });

    server.listen(onSuccess(s -> {
      HttpClientRequest req = client.request(HttpMethod.POST, DEFAULT_HTTP_PORT, DEFAULT_HTTP_HOST, "/form", resp -> {
        // assert the response
        assertEquals(200, resp.statusCode());
        resp.bodyHandler(body -> {
          assertEquals(0, body.length());
        });
        assertEquals(2, attributeCount.get());
        testComplete();
      });
      try {
        Buffer buffer = Buffer.buffer();
        // Make sure we have one param that needs url encoding
        buffer.appendString("framework=" + URLEncoder.encode("vert x", "UTF-8") + "&runson=jvm", "UTF-8");
        req.headers().set("content-length", String.valueOf(buffer.length()));
        req.headers().set("content-type", "application/x-www-form-urlencoded");
        req.write(buffer).end();
      } catch (UnsupportedEncodingException e) {
        fail(e.getMessage());
      }
    }));

    await();
  }

  @Test
  public void testFormUploadAttributes2() throws Exception {
    AtomicInteger attributeCount = new AtomicInteger();
    server.requestHandler(req -> {
      if (req.method() == HttpMethod.POST) {
        assertEquals(req.path(), "/form");
        req.setExpectMultipart(true);
        req.uploadHandler(event -> event.handler(buffer -> {
          fail("Should not get here");
        }));
        req.endHandler(v -> {
          MultiMap attrs = req.formAttributes();
          attributeCount.set(attrs.size());
          assertEquals("junit-testUserAlias", attrs.get("origin"));
          assertEquals("admin@foo.bar", attrs.get("login"));
          assertEquals("admin", attrs.get("pass word"));
          req.response().end();
        });
      }
    });

    server.listen(onSuccess(s -> {
      HttpClientRequest req = client.request(HttpMethod.POST, DEFAULT_HTTP_PORT, DEFAULT_HTTP_HOST, "/form", resp -> {
        // assert the response
        assertEquals(200, resp.statusCode());
        resp.bodyHandler(body -> {
          assertEquals(0, body.length());
        });
        assertEquals(3, attributeCount.get());
        testComplete();
      });
      Buffer buffer = Buffer.buffer();
      buffer.appendString("origin=junit-testUserAlias&login=admin%40foo.bar&pass+word=admin");
      req.headers().set("content-length", String.valueOf(buffer.length()));
      req.headers().set("content-type", "application/x-www-form-urlencoded");
      req.write(buffer).end();
    }));

    await();
  }

  @Test
  public void testAccessNetSocket() throws Exception {
    Buffer toSend = TestUtils.randomBuffer(1000);

    server.requestHandler(req -> {
      req.response().headers().set("HTTP/1.1", "101 Upgrade");
      req.bodyHandler(data -> {
        assertEquals(toSend, data);
        req.response().end();
      });
    });

    server.listen(onSuccess(s -> {
      HttpClientRequest req = client.request(HttpMethod.GET, DEFAULT_HTTP_PORT, DEFAULT_HTTP_HOST, DEFAULT_TEST_URI, resp -> {
        resp.endHandler(v -> {
          assertNotNull(resp.netSocket());
          testComplete();
        });
      });
      req.headers().set("content-length", String.valueOf(toSend.length()));
      req.write(toSend);
    }));

    await();
  }

  @Test
  public void testHostHeaderOverridePossible() {
    server.requestHandler(req -> {
      assertEquals("localhost:4444", req.headers().get("Host"));
      req.response().end();
    });

    server.listen(onSuccess(s -> {
      HttpClientRequest req = client.request(HttpMethod.GET, DEFAULT_HTTP_PORT, DEFAULT_HTTP_HOST, DEFAULT_TEST_URI, resp -> testComplete());
      req.putHeader("Host", "localhost:4444");
      req.end();
    }));

    await();
  }

  @Test
  public void testResponseBodyWriteFixedString() {
    String body = "Lorem ipsum dolor sit amet, consectetur adipisicing elit, sed do eiusmod tempor incididunt ut labore et dolore magna aliqua. Ut enim ad minim veniam, quis nostrud exercitation ullamco laboris nisi ut aliquip ex ea commodo consequat. Duis aute irure dolor in reprehenderit in voluptate velit esse cillum dolore eu fugiat nulla pariatur. Excepteur sint occaecat cupidatat non proident, sunt in culpa qui officia deserunt mollit anim id est laborum.";
    Buffer bodyBuff = Buffer.buffer(body);

    server.requestHandler(req -> {
      req.response().setChunked(true);
      req.response().write(body);
      req.response().end();
    });

    server.listen(onSuccess(s -> {
      client.request(HttpMethod.GET, DEFAULT_HTTP_PORT, DEFAULT_HTTP_HOST, DEFAULT_TEST_URI, resp -> {
        resp.bodyHandler(buff -> {
          assertEquals(bodyBuff, buff);
          testComplete();
        });
      }).end();
    }));

    await();
  }

  @Test
  public void testHttpConnect() {
    Buffer buffer = TestUtils.randomBuffer(128);
    Buffer received = Buffer.buffer();
    vertx.createNetServer(new NetServerOptions().setPort(1235)).connectHandler(socket -> {
      socket.handler(socket::write);
    }).listen(onSuccess(netServer -> {
      server.requestHandler(req -> {
        vertx.createNetClient(new NetClientOptions()).connect(netServer.actualPort(), "localhost", onSuccess(socket -> {
          req.response().setStatusCode(200);
          req.response().setStatusMessage("Connection established");
          req.response().end();

          // Create pumps which echo stuff
          Pump.pump(req.netSocket(), socket).start();
          Pump.pump(socket, req.netSocket()).start();
          req.netSocket().closeHandler(v -> socket.close());
        }));
      });
      server.listen(onSuccess(s -> {
        client.request(HttpMethod.CONNECT, DEFAULT_HTTP_PORT, DEFAULT_HTTP_HOST, DEFAULT_TEST_URI, resp -> {
          assertEquals(200, resp.statusCode());
          NetSocket socket = resp.netSocket();
          socket.handler(buff -> {
            received.appendBuffer(buff);
            if (received.length() == buffer.length()) {
              netServer.close();
              assertEquals(buffer, received);
              testComplete();
            }
          });
          socket.write(buffer);
        }).end();
      }));
    }));

    await();
  }

  @Test
  public void testRequestsTimeoutInQueue() {

    server.requestHandler(req -> {
      vertx.setTimer(1000, id -> {
        req.response().end();
      });
    });

    client.close();
    client = vertx.createHttpClient(new HttpClientOptions().setKeepAlive(false).setMaxPoolSize(1));

    server.listen(onSuccess(s -> {
      // Add a few requests that should all timeout
      for (int i = 0; i < 5; i++) {
        HttpClientRequest req = client.request(HttpMethod.GET, DEFAULT_HTTP_PORT, DEFAULT_HTTP_HOST, DEFAULT_TEST_URI, resp -> {
          fail("Should not be called");
        });
        req.exceptionHandler(t -> assertTrue(t instanceof TimeoutException));
        req.setTimeout(500);
        req.end();
      }
      // Now another request that should not timeout
      HttpClientRequest req = client.request(HttpMethod.GET, DEFAULT_HTTP_PORT, DEFAULT_HTTP_HOST, DEFAULT_TEST_URI, resp -> {
        assertEquals(200, resp.statusCode());
        testComplete();
      });
      req.exceptionHandler(t -> fail("Should not throw exception"));
      req.setTimeout(3000);
      req.end();
    }));

    await();
  }

  @Test
  public void testServerOptionsCopiedBeforeUse() {
    server.close();
    HttpServerOptions options = new HttpServerOptions().setHost(DEFAULT_HTTP_HOST).setPort(DEFAULT_HTTP_PORT);
    HttpServer server = vertx.createHttpServer(options);
    // Now change something - but server should still listen at previous port
    options.setPort(DEFAULT_HTTP_PORT + 1);
    server.requestHandler(req -> {
      req.response().end();
    });
    server.listen(ar -> {
      assertTrue(ar.succeeded());
      client.request(HttpMethod.GET, DEFAULT_HTTP_PORT, DEFAULT_HTTP_HOST, "/uri", res -> {
        assertEquals(200, res.statusCode());
        testComplete();
      }).end();
    });
    await();
  }

  @Test
  public void testClientOptionsCopiedBeforeUse() {
    client.close();
    server.requestHandler(req -> {
      req.response().end();
    });
    server.listen(ar -> {
      assertTrue(ar.succeeded());
      HttpClientOptions options = new HttpClientOptions();
      client = vertx.createHttpClient(options);
      // Now change something - but server should ignore this
      options.setSsl(true);
      client.request(HttpMethod.GET, DEFAULT_HTTP_PORT, DEFAULT_HTTP_HOST, "/uri", res -> {
        assertEquals(200, res.statusCode());
        testComplete();
      }).end();
    });
    await();
  }

  @Test
  public void testClientMultiThreaded() throws Exception {
    int numThreads = 10;
    Thread[] threads = new Thread[numThreads];
    CountDownLatch latch = new CountDownLatch(numThreads);
    server.requestHandler(req -> {
      req.response().putHeader("count", req.headers().get("count"));
      req.response().end();
    }).listen(ar -> {
      assertTrue(ar.succeeded());
      for (int i = 0; i < numThreads; i++) {
        int index = i;
        threads[i] = new Thread() {
          public void run() {
            client.request(HttpMethod.GET, DEFAULT_HTTP_PORT, DEFAULT_HTTP_HOST, "/", res -> {
              assertEquals(200, res.statusCode());
              assertEquals(String.valueOf(index), res.headers().get("count"));
              latch.countDown();
            }).putHeader("count", String.valueOf(index)).end();
          }
        };
        threads[i].start();
      }
    });
    awaitLatch(latch);
    for (int i = 0; i < numThreads; i++) {
      threads[i].join();
    }
  }

  @Test
  public void testInVerticle() throws Exception {
    testInVerticle(false);
  }

  private void testInVerticle(boolean worker) throws Exception {
    client.close();
    server.close();
    class MyVerticle extends AbstractVerticle {
      Context ctx;
      @Override
      public void start() {
        ctx = Vertx.currentContext();
        if (worker) {
          assertTrue(ctx instanceof WorkerContext);
        } else {
          assertTrue(ctx instanceof EventLoopContext);
        }
        Thread thr = Thread.currentThread();
        server = vertx.createHttpServer(new HttpServerOptions().setPort(DEFAULT_HTTP_PORT));
        server.requestHandler(req -> {
          req.response().end();
          assertSame(ctx, Vertx.currentContext());
          if (!worker) {
            assertSame(thr, Thread.currentThread());
          }
        });
        server.listen(ar -> {
          assertTrue(ar.succeeded());
          assertSame(ctx, Vertx.currentContext());
          if (!worker) {
            assertSame(thr, Thread.currentThread());
          }
          client = vertx.createHttpClient(new HttpClientOptions());
          client.request(HttpMethod.GET, DEFAULT_HTTP_PORT, DEFAULT_HTTP_HOST, "/", res -> {
            assertSame(ctx, Vertx.currentContext());
            if (!worker) {
              assertSame(thr, Thread.currentThread());
            }
            assertEquals(200, res.statusCode());
            testComplete();
          }).end();
        });
      }
    }
    MyVerticle verticle = new MyVerticle();
    vertx.deployVerticle(verticle, new DeploymentOptions().setWorker(worker));
    await();
  }

  @Test
  public void testUseInMultithreadedWorker() throws Exception {
    class MyVerticle extends AbstractVerticle {
      @Override
      public void start() {
        assertIllegalStateException(() -> server = vertx.createHttpServer(new HttpServerOptions()));
        assertIllegalStateException(() -> client = vertx.createHttpClient(new HttpClientOptions()));
        testComplete();
      }
    }
    MyVerticle verticle = new MyVerticle();
    vertx.deployVerticle(verticle, new DeploymentOptions().setWorker(true).setMultiThreaded(true));
    await();
  }

  @Test
  public void testContexts() throws Exception {
    Set<ContextImpl> contexts = new ConcurrentHashSet<>();
    AtomicInteger cnt = new AtomicInteger();
    AtomicReference<ContextImpl> serverRequestContext = new AtomicReference<>();
    // Server connect handler should always be called with same context
    server.requestHandler(req -> {
      ContextImpl serverContext = ((VertxInternal) vertx).getContext();
      if (serverRequestContext.get() != null) {
        assertSame(serverRequestContext.get(), serverContext);
      } else {
        serverRequestContext.set(serverContext);
      }
      req.response().end();
    });
    CountDownLatch latch = new CountDownLatch(1);
    AtomicReference<ContextImpl> listenContext = new AtomicReference<>();
    server.listen(ar -> {
      assertTrue(ar.succeeded());
      listenContext.set(((VertxInternal) vertx).getContext());
      latch.countDown();
    });
    awaitLatch(latch);
    CountDownLatch latch2 = new CountDownLatch(1);
    int numReqs = 16;
    int numConns = 8;
    // There should be a context per *connection*
    client.close();
    client = vertx.createHttpClient(new HttpClientOptions().setMaxPoolSize(numConns));
    for (int i = 0; i < numReqs; i++) {
      client.request(HttpMethod.GET, DEFAULT_HTTP_PORT, DEFAULT_HTTP_HOST, "/", resp -> {
        assertEquals(200, resp.statusCode());
        contexts.add(((VertxInternal) vertx).getContext());
        if (cnt.incrementAndGet() == numReqs) {
          // Some connections might get closed if response comes back quick enough hence the >=
          assertTrue(contexts.size() >= numConns);
          latch2.countDown();
        }
      }).end();
    }
    awaitLatch(latch2);
    // Close should be in own context
    server.close(ar -> {
      assertTrue(ar.succeeded());
      ContextImpl closeContext = ((VertxInternal) vertx).getContext();
      assertFalse(contexts.contains(closeContext));
      assertNotSame(serverRequestContext.get(), closeContext);
      assertFalse(contexts.contains(listenContext.get()));
      assertSame(serverRequestContext.get(), listenContext.get());
      testComplete();
    });

    server = null;
    await();
  }

  @Test
  public void testRequestHandlerNotCalledInvalidRequest() {
    server.requestHandler(req -> {
      fail();
    });
    server.listen(onSuccess(s -> {
      vertx.createNetClient(new NetClientOptions()).connect(8080, "127.0.0.1", result -> {
        NetSocket socket = result.result();
        socket.closeHandler(r -> {
          testComplete();
        });
        socket.write("GET HTTP1/1\r\n");

        // trigger another write to be sure we detect that the other peer has closed the connection.
        socket.write("X-Header: test\r\n");
      });
    }));
    await();
  }

  @Test
  public void testTwoServersSameAddressDifferentContext() throws Exception {
    vertx.deployVerticle(SimpleServer.class.getName(), new DeploymentOptions().setInstances(2), onSuccess(id -> {
      testComplete();
    }));
    await();
  }

  @Test
  public void testMultipleServerClose() {
    this.server = vertx.createHttpServer(new HttpServerOptions().setPort(DEFAULT_HTTP_PORT));
    AtomicInteger times = new AtomicInteger();
    // We assume the endHandler and the close completion handler are invoked in the same context task
    ThreadLocal stack = new ThreadLocal();
    stack.set(true);
    server.requestStream().endHandler(v -> {
      assertNull(stack.get());
      assertTrue(Vertx.currentContext().isEventLoopContext());
      times.incrementAndGet();
    });
    server.close(ar1 -> {
      assertNull(stack.get());
      assertTrue(Vertx.currentContext().isEventLoopContext());
      server.close(ar2 -> {
        server.close(ar3 -> {
          assertEquals(1, times.get());
          testComplete();
        });
      });
    });
    await();
  }

  @Test
  public void testClearHandlersOnEnd() {
    String path = "/some/path";
    server = vertx.createHttpServer(new HttpServerOptions().setPort(HttpTestBase.DEFAULT_HTTP_PORT));
    server.requestHandler(req -> req.response().setStatusCode(200).end());
    server.listen(ar -> {
      assertTrue(ar.succeeded());
      HttpClientRequest req = client.request(HttpMethod.GET, HttpTestBase.DEFAULT_HTTP_PORT, HttpTestBase.DEFAULT_HTTP_HOST, path);
      AtomicInteger count = new AtomicInteger();
      req.handler(resp -> {
        resp.endHandler(v -> {
          try {
            resp.endHandler(null);
            resp.exceptionHandler(null);
            resp.handler(null);
          } catch (Exception e) {
            fail("Was expecting to set to null the handlers when the response is completed");
            return;
          }
          if (count.incrementAndGet() == 2) {
            testComplete();
          }
        });
      });
      req.endHandler(done -> {
        try {
          req.handler(null);
          req.exceptionHandler(null);
          req.endHandler(null);
        } catch (Exception e) {
          e.printStackTrace();
          fail("Was expecting to set to null the handlers when the response is completed");
          return;
        }
        if (count.incrementAndGet() == 2) {
          testComplete();
        }
      });
      req.end();

    });
    await();
  }

  @Test
  public void testSetHandlersOnEnd() {
    String path = "/some/path";
    server = vertx.createHttpServer(new HttpServerOptions().setPort(HttpTestBase.DEFAULT_HTTP_PORT));
    server.requestHandler(req -> req.response().setStatusCode(200).end());
    server.listen(ar -> {
      assertTrue(ar.succeeded());
      HttpClientRequest req = client.request(HttpMethod.GET, HttpTestBase.DEFAULT_HTTP_PORT, HttpTestBase.DEFAULT_HTTP_HOST, path);
      req.handler(resp -> {});
      req.endHandler(done -> {
        try {
          req.handler(arg -> {});
          fail();
        } catch (Exception ignore) {
        }
        try {
          req.exceptionHandler(arg -> {
          });
          fail();
        } catch (Exception ignore) {
        }
        try {
          req.endHandler(arg -> {
          });
          fail();
        } catch (Exception ignore) {
        }
        testComplete();
      });
      req.end();

    });
    await();
  }

  @Test
  public void testRequestEnded() {
    server = vertx.createHttpServer(new HttpServerOptions().setPort(HttpTestBase.DEFAULT_HTTP_PORT));
    server.requestHandler(req -> {
      assertFalse(req.isEnded());
      req.endHandler(v -> {
        assertTrue(req.isEnded());
        try  {
          req.endHandler(v2 -> {});
          fail("Shouldn't be able to set end handler");
        } catch (IllegalStateException e) {
          // OK
        }
        try  {
          req.setExpectMultipart(true);
          fail("Shouldn't be able to set expect multipart");
        } catch (IllegalStateException e) {
          // OK
        }
        try  {
          req.bodyHandler(v2 -> {
          });
          fail("Shouldn't be able to set body handler");
        } catch (IllegalStateException e) {
          // OK
        }
        try  {
          req.handler(v2 -> {
          });
          fail("Shouldn't be able to set handler");
        } catch (IllegalStateException e) {
          // OK
        }

        req.response().setStatusCode(200).end();
      });
    });
    server.listen(ar -> {
      assertTrue(ar.succeeded());
      client.getNow(HttpTestBase.DEFAULT_HTTP_PORT, HttpTestBase.DEFAULT_HTTP_HOST, "/blah", resp -> {
        assertEquals(200, resp.statusCode());
        testComplete();
      });
    });
    await();
  }

  @Test
  public void testRequestEndedNoEndHandler() {
    server = vertx.createHttpServer(new HttpServerOptions().setPort(HttpTestBase.DEFAULT_HTTP_PORT));
    server.requestHandler(req -> {
      assertFalse(req.isEnded());
      req.response().setStatusCode(200).end();
      vertx.setTimer(500, v -> {
        assertTrue(req.isEnded());
        try {
          req.endHandler(v2 -> {
          });
          fail("Shouldn't be able to set end handler");
        } catch (IllegalStateException e) {
          // OK
        }
        try {
          req.setExpectMultipart(true);
          fail("Shouldn't be able to set expect multipart");
        } catch (IllegalStateException e) {
          // OK
        }
        try {
          req.bodyHandler(v2 -> {
          });
          fail("Shouldn't be able to set body handler");
        } catch (IllegalStateException e) {
          // OK
        }
        try {
          req.handler(v2 -> {
          });
          fail("Shouldn't be able to set handler");
        } catch (IllegalStateException e) {
          // OK
        }
        testComplete();
      });
    });
    server.listen(ar -> {
      assertTrue(ar.succeeded());
      client.getNow(HttpTestBase.DEFAULT_HTTP_PORT, HttpTestBase.DEFAULT_HTTP_HOST, "/blah", resp -> {
        assertEquals(200, resp.statusCode());
      });
    });
    await();
  }

  @Test
  public void testInWorker() throws Exception {
    vertx.deployVerticle(new AbstractVerticle() {
      @Override
      public void start() throws Exception {
        assertTrue(Vertx.currentContext().isWorkerContext());
        assertTrue(Context.isOnWorkerThread());
        HttpServer server1 = vertx.createHttpServer(new HttpServerOptions()
          .setHost(HttpTestBase.DEFAULT_HTTP_HOST).setPort(HttpTestBase.DEFAULT_HTTP_PORT));
        server1.requestHandler(req -> {
          assertTrue(Vertx.currentContext().isWorkerContext());
          assertTrue(Context.isOnWorkerThread());
          Buffer buf = Buffer.buffer();
          req.handler(buf::appendBuffer);
          req.endHandler(v -> {
            assertEquals("hello", buf.toString());
            req.response().end("bye");
          });
        }).listen(onSuccess(s -> {
          assertTrue(Vertx.currentContext().isWorkerContext());
          assertTrue(Context.isOnWorkerThread());
          HttpClient client = vertx.createHttpClient();
          client.put(HttpTestBase.DEFAULT_HTTP_PORT, HttpTestBase.DEFAULT_HTTP_HOST, "/blah", resp -> {
            assertEquals(200, resp.statusCode());
            assertTrue(Vertx.currentContext().isWorkerContext());
            assertTrue(Context.isOnWorkerThread());
            resp.handler(buf -> {
              assertEquals("bye", buf.toString());
              resp.endHandler(v -> {
                testComplete();
              });
            });
          }).setChunked(true).write(Buffer.buffer("hello")).end();
        }));
      }
    }, new DeploymentOptions().setWorker(true));
    await();
  }

  @Test
  public void testInMultithreadedWorker() throws Exception {
    vertx.deployVerticle(new AbstractVerticle() {
      @Override
      public void start() throws Exception {
        assertTrue(Vertx.currentContext().isWorkerContext());
        assertTrue(Vertx.currentContext().isMultiThreadedWorkerContext());
        assertTrue(Context.isOnWorkerThread());
        try {
          vertx.createHttpServer();
          fail("Should throw exception");
        } catch (IllegalStateException e) {
          // OK
        }
        try {
          vertx.createHttpClient();
          fail("Should throw exception");
        } catch (IllegalStateException e) {
          // OK
        }
        testComplete();
      }
    }, new DeploymentOptions().setWorker(true).setMultiThreaded(true));
    await();
  }

  @Test
  public void testAbsoluteURIServer() {
    server.close();
    // Listen on all addresses 
    server = vertx.createHttpServer(new HttpServerOptions().setPort(DEFAULT_HTTP_PORT).setHost("0.0.0.0"));
    server.requestHandler(req -> {
      String absURI = req.absoluteURI();
      assertEquals("http://localhost:8080/path", absURI);
      req.response().end();
    });
    server.listen(onSuccess(s -> {
      String host = "localhost";
      String path = "/path";
      int port = 8080;
      client.getNow(port, host, path, resp -> {
        assertEquals(200, resp.statusCode());
        testComplete();
      });
    }));

    await();
  }

  private void pausingServer(Consumer<HttpServer> consumer) {
    server.requestHandler(req -> {
      req.response().setChunked(true);
      req.pause();
      Handler<Message<Buffer>> resumeHandler = msg -> req.resume();
      MessageConsumer reg = vertx.eventBus().<Buffer>consumer("server_resume").handler(resumeHandler);
      req.endHandler(v -> reg.unregister());

      req.handler(buff -> {
        req.response().write(buff);
      });
    });

    server.listen(onSuccess(consumer));
  }

  private void drainingServer(Consumer<HttpServer> consumer) {
    server.requestHandler(req -> {
      req.response().setChunked(true);
      assertFalse(req.response().writeQueueFull());
      req.response().setWriteQueueMaxSize(1000);

      Buffer buff = TestUtils.randomBuffer(10000);
      //Send data until the buffer is full
      vertx.setPeriodic(1, id -> {
        req.response().write(buff);
        if (req.response().writeQueueFull()) {
          vertx.cancelTimer(id);
          req.response().drainHandler(v -> {
            assertFalse(req.response().writeQueueFull());
            testComplete();
          });

          // Tell the client to resume
          vertx.eventBus().send("client_resume", "");
        }
      });
    });

    server.listen(onSuccess(consumer));
  }

  private static MultiMap getHeaders(int num) {
    Map<String, String> map = genMap(num);
    MultiMap headers = new HeadersAdaptor(new DefaultHttpHeaders());
    for (Map.Entry<String, String> entry : map.entrySet()) {
      headers.add(entry.getKey(), entry.getValue());
    }
    return headers;
  }

  private static Map<String, String> genMap(int num) {
    Map<String, String> map = new HashMap<>();
    for (int i = 0; i < num; i++) {
      String key;
      do {
        key = TestUtils.randomAlphaString(1 + (int) ((19) * Math.random())).toLowerCase();
      } while (map.containsKey(key));
      map.put(key, TestUtils.randomAlphaString(1 + (int) ((19) * Math.random())));
    }
    return map;
  }

  private static String generateQueryString(Map<String, String> params, char delim) {
    StringBuilder sb = new StringBuilder();
    int count = 0;
    for (Map.Entry<String, String> param : params.entrySet()) {
      sb.append(param.getKey()).append("=").append(param.getValue());
      if (++count != params.size()) {
        sb.append(delim);
      }
    }
    return sb.toString();
  }

  private File setupFile(String fileName, String content) throws Exception {
    File file = new File(testDir, fileName);
    if (file.exists()) {
      file.delete();
    }
    BufferedWriter out = new BufferedWriter(new OutputStreamWriter(new FileOutputStream(file), "UTF-8"));
    out.write(content);
    out.close();
    return file;
  }
}


File: src/test/java/io/vertx/test/core/NetTest.java
/*
 * Copyright 2014 Red Hat, Inc.
 *
 * All rights reserved. This program and the accompanying materials
 * are made available under the terms of the Eclipse Public License v1.0
 * and Apache License v2.0 which accompanies this distribution.
 *
 * The Eclipse Public License is available at
 * http://www.eclipse.org/legal/epl-v10.html
 *
 * The Apache License v2.0 is available at
 * http://www.opensource.org/licenses/apache2.0.php
 *
 * You may elect to redistribute this code under either of these licenses.
 */

package io.vertx.test.core;

import io.vertx.core.*;
import io.vertx.core.buffer.Buffer;
import io.vertx.core.eventbus.Message;
import io.vertx.core.eventbus.MessageConsumer;
import io.vertx.core.impl.*;
import io.vertx.core.json.JsonArray;
import io.vertx.core.json.JsonObject;
import io.vertx.core.net.*;
import io.vertx.core.net.impl.SocketAddressImpl;
import io.vertx.core.net.impl.SocketDefaults;
import org.junit.Assume;
import org.junit.Rule;
import org.junit.Test;
import org.junit.rules.TemporaryFolder;

import javax.net.ssl.SSLPeerUnverifiedException;
import javax.security.cert.X509Certificate;
import java.io.BufferedWriter;
import java.io.File;
import java.io.FileOutputStream;
import java.io.OutputStreamWriter;
import java.util.*;
import java.util.concurrent.ConcurrentHashMap;
import java.util.concurrent.CountDownLatch;
import java.util.concurrent.TimeUnit;
import java.util.concurrent.atomic.AtomicBoolean;
import java.util.concurrent.atomic.AtomicInteger;
import java.util.concurrent.atomic.AtomicReference;
import java.util.function.Consumer;

import static io.vertx.test.core.TestUtils.assertIllegalArgumentException;
import static io.vertx.test.core.TestUtils.assertNullPointerException;

/**
 * @author <a href="http://tfox.org">Tim Fox</a>
 */
public class NetTest extends VertxTestBase {

  private NetServer server;
  private NetClient client;

  @Rule
  public TemporaryFolder testFolder = new TemporaryFolder();

  public void setUp() throws Exception {
    super.setUp();
    client = vertx.createNetClient(new NetClientOptions().setConnectTimeout(1000));
    server = vertx.createNetServer(new NetServerOptions().setPort(1234).setHost("localhost"));
  }

  protected void awaitClose(NetServer server) throws InterruptedException {
    CountDownLatch latch = new CountDownLatch(1);
    server.close((asyncResult) -> {
      latch.countDown();
    });
    awaitLatch(latch);
  }

  protected void tearDown() throws Exception {
    if (client != null) {
      client.close();
    }
    if (server != null) {
      awaitClose(server);
    }
    super.tearDown();
  }

  @Test
  public void testClientOptions() {
    NetClientOptions options = new NetClientOptions();

    assertEquals(NetworkOptions.DEFAULT_SEND_BUFFER_SIZE, options.getSendBufferSize());
    int rand = TestUtils.randomPositiveInt();
    assertEquals(options, options.setSendBufferSize(rand));
    assertEquals(rand, options.getSendBufferSize());
    assertIllegalArgumentException(() -> options.setSendBufferSize(0));
    assertIllegalArgumentException(() -> options.setSendBufferSize(-123));

    assertEquals(NetworkOptions.DEFAULT_RECEIVE_BUFFER_SIZE, options.getReceiveBufferSize());
    rand = TestUtils.randomPositiveInt();
    assertEquals(options, options.setReceiveBufferSize(rand));
    assertEquals(rand, options.getReceiveBufferSize());
    assertIllegalArgumentException(() -> options.setReceiveBufferSize(0));
    assertIllegalArgumentException(() -> options.setReceiveBufferSize(-123));

    assertTrue(options.isReuseAddress());
    assertEquals(options, options.setReuseAddress(false));
    assertFalse(options.isReuseAddress());

    assertEquals(NetworkOptions.DEFAULT_TRAFFIC_CLASS, options.getTrafficClass());
    rand = 23;
    assertEquals(options, options.setTrafficClass(rand));
    assertEquals(rand, options.getTrafficClass());
    assertIllegalArgumentException(() -> options.setTrafficClass(-1));
    assertIllegalArgumentException(() -> options.setTrafficClass(256));

    assertTrue(options.isTcpNoDelay());
    assertEquals(options, options.setTcpNoDelay(false));
    assertFalse(options.isTcpNoDelay());

    boolean tcpKeepAlive = SocketDefaults.instance.isTcpKeepAlive();
    assertEquals(tcpKeepAlive, options.isTcpKeepAlive());
    assertEquals(options, options.setTcpKeepAlive(!tcpKeepAlive));
    assertEquals(!tcpKeepAlive, options.isTcpKeepAlive());

    int soLinger = SocketDefaults.instance.getSoLinger();
    assertEquals(soLinger, options.getSoLinger());
    rand = TestUtils.randomPositiveInt();
    assertEquals(options, options.setSoLinger(rand));
    assertEquals(rand, options.getSoLinger());
    assertIllegalArgumentException(() -> options.setSoLinger(-1));

    assertFalse(options.isUsePooledBuffers());
    assertEquals(options, options.setUsePooledBuffers(true));
    assertTrue(options.isUsePooledBuffers());

    rand = TestUtils.randomPositiveInt();
    assertEquals(0, options.getIdleTimeout());
    assertEquals(options, options.setIdleTimeout(rand));
    assertEquals(rand, options.getIdleTimeout());

    assertFalse(options.isSsl());
    assertEquals(options, options.setSsl(true));
    assertTrue(options.isSsl());

    assertNull(options.getKeyCertOptions());
    JksOptions keyStoreOptions = new JksOptions().setPath(TestUtils.randomAlphaString(100)).setPassword(TestUtils.randomAlphaString(100));
    assertEquals(options, options.setKeyStoreOptions(keyStoreOptions));
    assertEquals(keyStoreOptions, options.getKeyCertOptions());

    assertNull(options.getTrustOptions());
    JksOptions trustStoreOptions = new JksOptions().setPath(TestUtils.randomAlphaString(100)).setPassword(TestUtils.randomAlphaString(100));
    assertEquals(options, options.setTrustStoreOptions(trustStoreOptions));
    assertEquals(trustStoreOptions, options.getTrustOptions());

    assertFalse(options.isTrustAll());
    assertEquals(options, options.setTrustAll(true));
    assertTrue(options.isTrustAll());

    assertEquals(0, options.getReconnectAttempts());
    assertIllegalArgumentException(() -> options.setReconnectAttempts(-2));
    rand = TestUtils.randomPositiveInt();
    assertEquals(options, options.setReconnectAttempts(rand));
    assertEquals(rand, options.getReconnectAttempts());

    assertEquals(1000, options.getReconnectInterval());
    assertIllegalArgumentException(() -> options.setReconnectInterval(0));
    rand = TestUtils.randomPositiveInt();
    assertEquals(options, options.setReconnectInterval(rand));
    assertEquals(rand, options.getReconnectInterval());

    assertTrue(options.getEnabledCipherSuites().isEmpty());
    assertEquals(options, options.addEnabledCipherSuite("foo"));
    assertEquals(options, options.addEnabledCipherSuite("bar"));
    assertNotNull(options.getEnabledCipherSuites());
    assertTrue(options.getEnabledCipherSuites().contains("foo"));
    assertTrue(options.getEnabledCipherSuites().contains("bar"));

    testComplete();
  }

  @Test
  public void testServerOptions() {
    NetServerOptions options = new NetServerOptions();

    assertEquals(NetworkOptions.DEFAULT_SEND_BUFFER_SIZE, options.getSendBufferSize());
    int rand = TestUtils.randomPositiveInt();
    assertEquals(options, options.setSendBufferSize(rand));
    assertEquals(rand, options.getSendBufferSize());
    assertIllegalArgumentException(() -> options.setSendBufferSize(0));
    assertIllegalArgumentException(() -> options.setSendBufferSize(-123));

    assertEquals(NetworkOptions.DEFAULT_RECEIVE_BUFFER_SIZE, options.getReceiveBufferSize());
    rand = TestUtils.randomPositiveInt();
    assertEquals(options, options.setReceiveBufferSize(rand));
    assertEquals(rand, options.getReceiveBufferSize());
    assertIllegalArgumentException(() -> options.setReceiveBufferSize(0));
    assertIllegalArgumentException(() -> options.setReceiveBufferSize(-123));

    assertTrue(options.isReuseAddress());
    assertEquals(options, options.setReuseAddress(false));
    assertFalse(options.isReuseAddress());

    assertEquals(NetworkOptions.DEFAULT_TRAFFIC_CLASS, options.getTrafficClass());
    rand = 23;
    assertEquals(options, options.setTrafficClass(rand));
    assertEquals(rand, options.getTrafficClass());
    assertIllegalArgumentException(() -> options.setTrafficClass(-1));
    assertIllegalArgumentException(() -> options.setTrafficClass(256));

    assertTrue(options.isTcpNoDelay());
    assertEquals(options, options.setTcpNoDelay(false));
    assertFalse(options.isTcpNoDelay());

    boolean tcpKeepAlive = SocketDefaults.instance.isTcpKeepAlive();
    assertEquals(tcpKeepAlive, options.isTcpKeepAlive());
    assertEquals(options, options.setTcpKeepAlive(!tcpKeepAlive));
    assertEquals(!tcpKeepAlive, options.isTcpKeepAlive());

    int soLinger = SocketDefaults.instance.getSoLinger();
    assertEquals(soLinger, options.getSoLinger());
    rand = TestUtils.randomPositiveInt();
    assertEquals(options, options.setSoLinger(rand));
    assertEquals(rand, options.getSoLinger());
    assertIllegalArgumentException(() -> options.setSoLinger(-1));

    assertFalse(options.isUsePooledBuffers());
    assertEquals(options, options.setUsePooledBuffers(true));
    assertTrue(options.isUsePooledBuffers());

    rand = TestUtils.randomPositiveInt();
    assertEquals(0, options.getIdleTimeout());
    assertEquals(options, options.setIdleTimeout(rand));
    assertEquals(rand, options.getIdleTimeout());
    assertIllegalArgumentException(() -> options.setIdleTimeout(-1));

    assertFalse(options.isSsl());
    assertEquals(options, options.setSsl(true));
    assertTrue(options.isSsl());

    assertNull(options.getKeyCertOptions());
    JksOptions keyStoreOptions = new JksOptions().setPath(TestUtils.randomAlphaString(100)).setPassword(TestUtils.randomAlphaString(100));
    assertEquals(options, options.setKeyStoreOptions(keyStoreOptions));
    assertEquals(keyStoreOptions, options.getKeyCertOptions());

    assertNull(options.getTrustOptions());
    JksOptions trustStoreOptions = new JksOptions().setPath(TestUtils.randomAlphaString(100)).setPassword(TestUtils.randomAlphaString(100));
    assertEquals(options, options.setTrustStoreOptions(trustStoreOptions));
    assertEquals(trustStoreOptions, options.getTrustOptions());

    assertEquals(1024, options.getAcceptBacklog());
    rand = TestUtils.randomPositiveInt();
    assertEquals(options, options.setAcceptBacklog(rand));
    assertEquals(rand, options.getAcceptBacklog());

    assertEquals(0, options.getPort());
    assertEquals(options, options.setPort(1234));
    assertEquals(1234, options.getPort());
    assertIllegalArgumentException(() -> options.setPort(-1));
    assertIllegalArgumentException(() -> options.setPort(65536));

    assertEquals("0.0.0.0", options.getHost());
    String randString = TestUtils.randomUnicodeString(100);
    assertEquals(options, options.setHost(randString));
    assertEquals(randString, options.getHost());

    assertTrue(options.getEnabledCipherSuites().isEmpty());
    assertEquals(options, options.addEnabledCipherSuite("foo"));
    assertEquals(options, options.addEnabledCipherSuite("bar"));
    assertNotNull(options.getEnabledCipherSuites());
    assertTrue(options.getEnabledCipherSuites().contains("foo"));
    assertTrue(options.getEnabledCipherSuites().contains("bar"));

    testComplete();
  }

  @Test
  public void testCopyClientOptions() {
    NetClientOptions options = new NetClientOptions();
    int sendBufferSize = TestUtils.randomPositiveInt();
    int receiverBufferSize = TestUtils.randomPortInt();
    Random rand = new Random();
    boolean reuseAddress = rand.nextBoolean();
    int trafficClass = TestUtils.randomByte() + 127;
    boolean tcpNoDelay = rand.nextBoolean();
    boolean tcpKeepAlive = rand.nextBoolean();
    int soLinger = TestUtils.randomPositiveInt();
    boolean usePooledBuffers = rand.nextBoolean();
    int idleTimeout = TestUtils.randomPositiveInt();
    boolean ssl = rand.nextBoolean();
    JksOptions keyStoreOptions = new JksOptions();
    String ksPassword = TestUtils.randomAlphaString(100);
    keyStoreOptions.setPassword(ksPassword);
    JksOptions trustStoreOptions = new JksOptions();
    String tsPassword = TestUtils.randomAlphaString(100);
    trustStoreOptions.setPassword(tsPassword);
    String enabledCipher = TestUtils.randomAlphaString(100);
    int connectTimeout = TestUtils.randomPositiveInt();
    boolean trustAll = rand.nextBoolean();
    String crlPath = TestUtils.randomUnicodeString(100);
    Buffer crlValue = TestUtils.randomBuffer(100);
    int reconnectAttempts = TestUtils.randomPositiveInt();
    long reconnectInterval = TestUtils.randomPositiveInt();
    options.setSendBufferSize(sendBufferSize);
    options.setReceiveBufferSize(receiverBufferSize);
    options.setReuseAddress(reuseAddress);
    options.setTrafficClass(trafficClass);
    options.setSsl(ssl);
    options.setTcpNoDelay(tcpNoDelay);
    options.setTcpKeepAlive(tcpKeepAlive);
    options.setSoLinger(soLinger);
    options.setUsePooledBuffers(usePooledBuffers);
    options.setIdleTimeout(idleTimeout);
    options.setKeyStoreOptions(keyStoreOptions);
    options.setTrustStoreOptions(trustStoreOptions);
    options.addEnabledCipherSuite(enabledCipher);
    options.setConnectTimeout(connectTimeout);
    options.setTrustAll(trustAll);
    options.addCrlPath(crlPath);
    options.addCrlValue(crlValue);
    options.setReconnectAttempts(reconnectAttempts);
    options.setReconnectInterval(reconnectInterval);
    NetClientOptions copy = new NetClientOptions(options);
    assertEquals(sendBufferSize, copy.getSendBufferSize());
    assertEquals(receiverBufferSize, copy.getReceiveBufferSize());
    assertEquals(reuseAddress, copy.isReuseAddress());
    assertEquals(trafficClass, copy.getTrafficClass());
    assertEquals(tcpNoDelay, copy.isTcpNoDelay());
    assertEquals(tcpKeepAlive, copy.isTcpKeepAlive());
    assertEquals(soLinger, copy.getSoLinger());
    assertEquals(usePooledBuffers, copy.isUsePooledBuffers());
    assertEquals(idleTimeout, copy.getIdleTimeout());
    assertEquals(ssl, copy.isSsl());
    assertNotSame(keyStoreOptions, copy.getKeyCertOptions());
    assertEquals(ksPassword, ((JksOptions) copy.getKeyCertOptions()).getPassword());
    assertNotSame(trustStoreOptions, copy.getTrustOptions());
    assertEquals(tsPassword, ((JksOptions)copy.getTrustOptions()).getPassword());
    assertEquals(1, copy.getEnabledCipherSuites().size());
    assertTrue(copy.getEnabledCipherSuites().contains(enabledCipher));
    assertEquals(connectTimeout, copy.getConnectTimeout());
    assertEquals(trustAll, copy.isTrustAll());
    assertEquals(1, copy.getCrlPaths().size());
    assertEquals(crlPath, copy.getCrlPaths().get(0));
    assertEquals(1, copy.getCrlValues().size());
    assertEquals(crlValue, copy.getCrlValues().get(0));
    assertEquals(reconnectAttempts, copy.getReconnectAttempts());
    assertEquals(reconnectInterval, copy.getReconnectInterval());
  }

  @Test
  public void testDefaultClientOptionsJson() {
    NetClientOptions def = new NetClientOptions();
    NetClientOptions json = new NetClientOptions(new JsonObject());
    assertEquals(def.getReconnectAttempts(), json.getReconnectAttempts());
    assertEquals(def.getReconnectInterval(), json.getReconnectInterval());
    assertEquals(def.isTrustAll(), json.isTrustAll());
    assertEquals(def.getCrlPaths(), json.getCrlPaths());
    assertEquals(def.getCrlValues(), json.getCrlValues());
    assertEquals(def.getConnectTimeout(), json.getConnectTimeout());
    assertEquals(def.isTcpNoDelay(), json.isTcpNoDelay());
    assertEquals(def.isTcpKeepAlive(), json.isTcpKeepAlive());
    assertEquals(def.getSoLinger(), json.getSoLinger());
    assertEquals(def.isUsePooledBuffers(), json.isUsePooledBuffers());
    assertEquals(def.isSsl(), json.isSsl());
  }

  @Test
  public void testClientOptionsJson() {
    int sendBufferSize = TestUtils.randomPositiveInt();
    int receiverBufferSize = TestUtils.randomPortInt();
    Random rand = new Random();
    boolean reuseAddress = rand.nextBoolean();
    int trafficClass = TestUtils.randomByte() + 127;
    boolean tcpNoDelay = rand.nextBoolean();
    boolean tcpKeepAlive = rand.nextBoolean();
    int soLinger = TestUtils.randomPositiveInt();
    boolean usePooledBuffers = rand.nextBoolean();
    int idleTimeout = TestUtils.randomPositiveInt();
    boolean ssl = rand.nextBoolean();
    JksOptions keyStoreOptions = new JksOptions();
    String ksPassword = TestUtils.randomAlphaString(100);
    keyStoreOptions.setPassword(ksPassword);
    String ksPath = TestUtils.randomAlphaString(100);
    keyStoreOptions.setPath(ksPath);
    JksOptions trustStoreOptions = new JksOptions();
    String tsPassword = TestUtils.randomAlphaString(100);
    trustStoreOptions.setPassword(tsPassword);
    String tsPath = TestUtils.randomAlphaString(100);
    trustStoreOptions.setPath(tsPath);
    String enabledCipher = TestUtils.randomAlphaString(100);
    int connectTimeout = TestUtils.randomPositiveInt();
    boolean trustAll = rand.nextBoolean();
    String crlPath = TestUtils.randomUnicodeString(100);
    int reconnectAttempts = TestUtils.randomPositiveInt();
    long reconnectInterval = TestUtils.randomPositiveInt();

    JsonObject json = new JsonObject();
    json.put("sendBufferSize", sendBufferSize)
        .put("receiveBufferSize", receiverBufferSize)
        .put("reuseAddress", reuseAddress)
        .put("trafficClass", trafficClass)
        .put("tcpNoDelay", tcpNoDelay)
        .put("tcpKeepAlive", tcpKeepAlive)
        .put("soLinger", soLinger)
        .put("usePooledBuffers", usePooledBuffers)
        .put("idleTimeout", idleTimeout)
        .put("ssl", ssl)
        .put("enabledCipherSuites", new JsonArray().add(enabledCipher))
        .put("connectTimeout", connectTimeout)
        .put("trustAll", trustAll)
        .put("crlPaths", new JsonArray().add(crlPath))
        .put("keyStoreOptions", new JsonObject().put("type", "jks").put("password", ksPassword).put("path", ksPath))
        .put("trustStoreOptions", new JsonObject().put("type", "jks").put("password", tsPassword).put("path", tsPath))
        .put("reconnectAttempts", reconnectAttempts)
        .put("reconnectInterval", reconnectInterval);

    NetClientOptions options = new NetClientOptions(json);
    assertEquals(sendBufferSize, options.getSendBufferSize());
    assertEquals(receiverBufferSize, options.getReceiveBufferSize());
    assertEquals(reuseAddress, options.isReuseAddress());
    assertEquals(trafficClass, options.getTrafficClass());
    assertEquals(tcpKeepAlive, options.isTcpKeepAlive());
    assertEquals(tcpNoDelay, options.isTcpNoDelay());
    assertEquals(soLinger, options.getSoLinger());
    assertEquals(usePooledBuffers, options.isUsePooledBuffers());
    assertEquals(idleTimeout, options.getIdleTimeout());
    assertEquals(ssl, options.isSsl());
    assertNotSame(keyStoreOptions, options.getKeyCertOptions());
    assertEquals(ksPassword, ((JksOptions) options.getKeyCertOptions()).getPassword());
    assertEquals(ksPath, ((JksOptions) options.getKeyCertOptions()).getPath());
    assertNotSame(trustStoreOptions, options.getTrustOptions());
    assertEquals(tsPassword, ((JksOptions) options.getTrustOptions()).getPassword());
    assertEquals(tsPath, ((JksOptions) options.getTrustOptions()).getPath());
    assertEquals(1, options.getEnabledCipherSuites().size());
    assertTrue(options.getEnabledCipherSuites().contains(enabledCipher));
    assertEquals(connectTimeout, options.getConnectTimeout());
    assertEquals(trustAll, options.isTrustAll());
    assertEquals(1, options.getCrlPaths().size());
    assertEquals(crlPath, options.getCrlPaths().get(0));
    assertEquals(reconnectAttempts, options.getReconnectAttempts());
    assertEquals(reconnectInterval, options.getReconnectInterval());

    // Test other keystore/truststore types
    json.remove("keyStoreOptions");
    json.remove("trustStoreOptions");
    json.put("pfxKeyCertOptions", new JsonObject().put("password", ksPassword))
      .put("pfxTrustOptions", new JsonObject().put("password", tsPassword));
    options = new NetClientOptions(json);
    assertTrue(options.getTrustOptions() instanceof PfxOptions);
    assertTrue(options.getKeyCertOptions() instanceof PfxOptions);

    json.remove("pfxKeyCertOptions");
    json.remove("pfxTrustOptions");
    json.put("pemKeyCertOptions", new JsonObject())
      .put("pemTrustOptions", new JsonObject());
    options = new NetClientOptions(json);
    assertTrue(options.getTrustOptions() instanceof PemTrustOptions);
    assertTrue(options.getKeyCertOptions() instanceof PemKeyCertOptions);
  }

  @Test
  public void testCopyServerOptions() {
    NetServerOptions options = new NetServerOptions();
    int sendBufferSize = TestUtils.randomPositiveInt();
    int receiverBufferSize = TestUtils.randomPortInt();
    Random rand = new Random();
    boolean reuseAddress = rand.nextBoolean();
    int trafficClass = TestUtils.randomByte() + 128;
    boolean tcpNoDelay = rand.nextBoolean();
    boolean tcpKeepAlive = rand.nextBoolean();
    int soLinger = TestUtils.randomPositiveInt();
    boolean usePooledBuffers = rand.nextBoolean();
    int idleTimeout = TestUtils.randomPositiveInt();
    boolean ssl = rand.nextBoolean();
    JksOptions keyStoreOptions = new JksOptions();
    String ksPassword = TestUtils.randomAlphaString(100);
    keyStoreOptions.setPassword(ksPassword);
    JksOptions trustStoreOptions = new JksOptions();
    String tsPassword = TestUtils.randomAlphaString(100);
    trustStoreOptions.setPassword(tsPassword);
    String enabledCipher = TestUtils.randomAlphaString(100);
    String crlPath = TestUtils.randomUnicodeString(100);
    Buffer crlValue = TestUtils.randomBuffer(100);
    int port = 1234;
    String host = TestUtils.randomAlphaString(100);
    int acceptBacklog = TestUtils.randomPortInt();
    options.setSendBufferSize(sendBufferSize);
    options.setReceiveBufferSize(receiverBufferSize);
    options.setReuseAddress(reuseAddress);
    options.setTrafficClass(trafficClass);
    options.setTcpNoDelay(tcpNoDelay);
    options.setTcpKeepAlive(tcpKeepAlive);
    options.setSoLinger(soLinger);
    options.setUsePooledBuffers(usePooledBuffers);
    options.setIdleTimeout(idleTimeout);
    options.setSsl(ssl);
    options.setKeyStoreOptions(keyStoreOptions);
    options.setTrustStoreOptions(trustStoreOptions);
    options.addEnabledCipherSuite(enabledCipher);
    options.addCrlPath(crlPath);
    options.addCrlValue(crlValue);
    options.setPort(port);
    options.setHost(host);
    options.setAcceptBacklog(acceptBacklog);
    NetServerOptions copy = new NetServerOptions(options);
    assertEquals(sendBufferSize, copy.getSendBufferSize());
    assertEquals(receiverBufferSize, copy.getReceiveBufferSize());
    assertEquals(reuseAddress, copy.isReuseAddress());
    assertEquals(trafficClass, copy.getTrafficClass());
    assertEquals(tcpNoDelay, copy.isTcpNoDelay());
    assertEquals(tcpKeepAlive, copy.isTcpKeepAlive());
    assertEquals(soLinger, copy.getSoLinger());
    assertEquals(usePooledBuffers, copy.isUsePooledBuffers());
    assertEquals(idleTimeout, copy.getIdleTimeout());
    assertEquals(ssl, copy.isSsl());
    assertNotSame(keyStoreOptions, copy.getKeyCertOptions());
    assertEquals(ksPassword, ((JksOptions) copy.getKeyCertOptions()).getPassword());
    assertNotSame(trustStoreOptions, copy.getTrustOptions());
    assertEquals(tsPassword, ((JksOptions)copy.getTrustOptions()).getPassword());
    assertEquals(1, copy.getEnabledCipherSuites().size());
    assertTrue(copy.getEnabledCipherSuites().contains(enabledCipher));
    assertEquals(1, copy.getCrlPaths().size());
    assertEquals(crlPath, copy.getCrlPaths().get(0));
    assertEquals(1, copy.getCrlValues().size());
    assertEquals(crlValue, copy.getCrlValues().get(0));
    assertEquals(port, copy.getPort());
    assertEquals(host, copy.getHost());
    assertEquals(acceptBacklog, copy.getAcceptBacklog());
  }

  @Test
  public void testDefaultServerOptionsJson() {
    NetServerOptions def = new NetServerOptions();
    NetServerOptions json = new NetServerOptions(new JsonObject());
    assertEquals(def.isClientAuthRequired(), json.isClientAuthRequired());
    assertEquals(def.getCrlPaths(), json.getCrlPaths());
    assertEquals(def.getCrlValues(), json.getCrlValues());
    assertEquals(def.getAcceptBacklog(), json.getAcceptBacklog());
    assertEquals(def.getPort(), json.getPort());
    assertEquals(def.getHost(), json.getHost());
    assertEquals(def.isClientAuthRequired(), json.isClientAuthRequired());
    assertEquals(def.getCrlPaths(), json.getCrlPaths());
    assertEquals(def.getCrlValues(), json.getCrlValues());
    assertEquals(def.getAcceptBacklog(), json.getAcceptBacklog());
    assertEquals(def.getPort(), json.getPort());
    assertEquals(def.getHost(), json.getHost());
    assertEquals(def.isTcpNoDelay(), json.isTcpNoDelay());
    assertEquals(def.isTcpKeepAlive(), json.isTcpKeepAlive());
    assertEquals(def.getSoLinger(), json.getSoLinger());
    assertEquals(def.isUsePooledBuffers(), json.isUsePooledBuffers());
    assertEquals(def.isSsl(), json.isSsl());
  }

  @Test
  public void testServerOptionsJson() {
    int sendBufferSize = TestUtils.randomPositiveInt();
    int receiverBufferSize = TestUtils.randomPortInt();
    Random rand = new Random();
    boolean reuseAddress = rand.nextBoolean();
    int trafficClass = TestUtils.randomByte() + 127;
    boolean tcpNoDelay = rand.nextBoolean();
    boolean tcpKeepAlive = rand.nextBoolean();
    int soLinger = TestUtils.randomPositiveInt();
    boolean usePooledBuffers = rand.nextBoolean();
    int idleTimeout = TestUtils.randomInt();
    boolean ssl = rand.nextBoolean();
    JksOptions keyStoreOptions = new JksOptions();
    String ksPassword = TestUtils.randomAlphaString(100);
    keyStoreOptions.setPassword(ksPassword);
    String ksPath = TestUtils.randomAlphaString(100);
    keyStoreOptions.setPath(ksPath);
    JksOptions trustStoreOptions = new JksOptions();
    String tsPassword = TestUtils.randomAlphaString(100);
    trustStoreOptions.setPassword(tsPassword);
    String tsPath = TestUtils.randomAlphaString(100);
    trustStoreOptions.setPath(tsPath);
    String enabledCipher = TestUtils.randomAlphaString(100);
    String crlPath = TestUtils.randomUnicodeString(100);
    int port = 1234;
    String host = TestUtils.randomAlphaString(100);
    int acceptBacklog = TestUtils.randomPortInt();

    JsonObject json = new JsonObject();
    json.put("sendBufferSize", sendBufferSize)
      .put("receiveBufferSize", receiverBufferSize)
      .put("reuseAddress", reuseAddress)
      .put("trafficClass", trafficClass)
      .put("tcpNoDelay", tcpNoDelay)
      .put("tcpKeepAlive", tcpKeepAlive)
      .put("soLinger", soLinger)
      .put("usePooledBuffers", usePooledBuffers)
      .put("idleTimeout", idleTimeout)
      .put("ssl", ssl)
      .put("enabledCipherSuites", new JsonArray().add(enabledCipher))
      .put("crlPaths", new JsonArray().add(crlPath))
      .put("keyStoreOptions", new JsonObject().put("password", ksPassword).put("path", ksPath))
      .put("trustStoreOptions", new JsonObject().put("password", tsPassword).put("path", tsPath))
      .put("port", port)
      .put("host", host)
      .put("acceptBacklog", acceptBacklog);

    NetServerOptions options = new NetServerOptions(json);
    assertEquals(sendBufferSize, options.getSendBufferSize());
    assertEquals(receiverBufferSize, options.getReceiveBufferSize());
    assertEquals(reuseAddress, options.isReuseAddress());
    assertEquals(trafficClass, options.getTrafficClass());
    assertEquals(tcpKeepAlive, options.isTcpKeepAlive());
    assertEquals(tcpNoDelay, options.isTcpNoDelay());
    assertEquals(soLinger, options.getSoLinger());
    assertEquals(usePooledBuffers, options.isUsePooledBuffers());
    assertEquals(idleTimeout, options.getIdleTimeout());
    assertEquals(ssl, options.isSsl());
    assertNotSame(keyStoreOptions, options.getKeyCertOptions());
    assertEquals(ksPassword, ((JksOptions) options.getKeyCertOptions()).getPassword());
    assertEquals(ksPath, ((JksOptions) options.getKeyCertOptions()).getPath());
    assertNotSame(trustStoreOptions, options.getTrustOptions());
    assertEquals(tsPassword, ((JksOptions) options.getTrustOptions()).getPassword());
    assertEquals(tsPath, ((JksOptions) options.getTrustOptions()).getPath());
    assertEquals(1, options.getEnabledCipherSuites().size());
    assertTrue(options.getEnabledCipherSuites().contains(enabledCipher));
    assertEquals(1, options.getCrlPaths().size());
    assertEquals(crlPath, options.getCrlPaths().get(0));
    assertEquals(port, options.getPort());
    assertEquals(host, options.getHost());
    assertEquals(acceptBacklog, options.getAcceptBacklog());

    // Test other keystore/truststore types
    json.remove("keyStoreOptions");
    json.remove("trustStoreOptions");
    json.put("pfxKeyCertOptions", new JsonObject().put("password", ksPassword))
      .put("pfxTrustOptions", new JsonObject().put("password", tsPassword));
    options = new NetServerOptions(json);
    assertTrue(options.getTrustOptions() instanceof PfxOptions);
    assertTrue(options.getKeyCertOptions() instanceof PfxOptions);

    json.remove("pfxKeyCertOptions");
    json.remove("pfxTrustOptions");
    json.put("pemKeyCertOptions", new JsonObject())
      .put("pemTrustOptions", new JsonObject());
    options = new NetServerOptions(json);
    assertTrue(options.getTrustOptions() instanceof PemTrustOptions);
    assertTrue(options.getKeyCertOptions() instanceof PemKeyCertOptions);
  }

  @Test
  public void testSocketAddress() throws Exception {
    assertNullPointerException(() -> new SocketAddressImpl(0, null));
    assertIllegalArgumentException(() -> new SocketAddressImpl(0, ""));
    assertIllegalArgumentException(() -> new SocketAddressImpl(-1, "someHost"));
    assertIllegalArgumentException(() -> new SocketAddressImpl(65536, "someHost"));
  }

  @Test
  public void testEchoBytes() {
    Buffer sent = TestUtils.randomBuffer(100);
    testEcho(sock -> sock.write(sent), buff -> assertEquals(sent, buff), sent.length());
  }

  @Test
  public void testEchoString() {
    String sent = TestUtils.randomUnicodeString(100);
    Buffer buffSent = Buffer.buffer(sent);
    testEcho(sock -> sock.write(sent), buff -> assertEquals(buffSent, buff), buffSent.length());
  }

  @Test
  public void testEchoStringUTF8() {
    testEchoStringWithEncoding("UTF-8");
  }

  @Test
  public void testEchoStringUTF16() {
    testEchoStringWithEncoding("UTF-16");
  }

  void testEchoStringWithEncoding(String encoding) {
    String sent = TestUtils.randomUnicodeString(100);
    Buffer buffSent = Buffer.buffer(sent, encoding);
    testEcho(sock -> sock.write(sent, encoding), buff -> assertEquals(buffSent, buff), buffSent.length());
  }

  void testEcho(Consumer<NetSocket> writer, Consumer<Buffer> dataChecker, int length) {
    Handler<AsyncResult<NetSocket>> clientHandler = (asyncResult) -> {
      if (asyncResult.succeeded()) {
        NetSocket sock = asyncResult.result();
        Buffer buff = Buffer.buffer();
        sock.handler((buffer) -> {
          buff.appendBuffer(buffer);
          if (buff.length() == length) {
            dataChecker.accept(buff);
            testComplete();
          }
          if (buff.length() > length) {
            fail("Too many bytes received");
          }
        });
        writer.accept(sock);
      } else {
        fail("failed to connect");
      }
    };
    startEchoServer(s -> client.connect(1234, "localhost", clientHandler));
    await();
  }

  void startEchoServer(Handler<AsyncResult<NetServer>> listenHandler) {
    Handler<NetSocket> serverHandler = socket -> socket.handler(socket::write);
    server.connectHandler(serverHandler).listen(listenHandler);
  }

  @Test
  public void testConnectLocalHost() {
    connect(1234, "localhost");
  }

  void connect(int port, String host) {
    startEchoServer(s -> {
      final int numConnections = 100;
      final AtomicInteger connCount = new AtomicInteger(0);
      for (int i = 0; i < numConnections; i++) {
        AsyncResultHandler<NetSocket> handler = res -> {
          if (res.succeeded()) {
            res.result().close();
            if (connCount.incrementAndGet() == numConnections) {
              testComplete();
            }
          }
        };
        client.connect(port, host, handler);
      }
    });
    await();
  }

  @Test
  public void testConnectInvalidPort() {
    assertIllegalArgumentException(() -> client.connect(-1, "localhost", res -> {}));
    assertIllegalArgumentException(() -> client.connect(65536, "localhost", res -> {}));
    client.connect(9998, "localhost", res -> {
      assertTrue(res.failed());
      assertFalse(res.succeeded());
      assertNotNull(res.cause());
      testComplete();
    });
    await();
  }

  @Test
  public void testConnectInvalidHost() {
    assertNullPointerException(() -> client.connect(80, null, res -> {}));
    client.connect(1234, "127.0.0.2", res -> {
      assertTrue(res.failed());
      assertFalse(res.succeeded());
      assertNotNull(res.cause());
      testComplete();
    });
    await();
  }

  @Test
  public void testConnectInvalidConnectHandler() throws Exception {
    assertNullPointerException(() -> client.connect(80, "localhost", null));
  }

  @Test
  public void testListenInvalidPort() {
    /* Port 80 is free to use by any application on Windows, so this test fails. */
    Assume.assumeFalse(System.getProperty("os.name").startsWith("Windows"));
    server.close();
    server = vertx.createNetServer(new NetServerOptions().setPort(80));
    server.connectHandler((netSocket) -> {
    }).listen(ar -> {
      assertTrue(ar.failed());
      assertFalse(ar.succeeded());
      assertNotNull(ar.cause());
      testComplete();
    });
    await();
  }

  @Test
  public void testListenInvalidHost() {
    server.close();
    server = vertx.createNetServer(new NetServerOptions().setPort(1234).setHost("uhqwduhqwudhqwuidhqwiudhqwudqwiuhd"));
    server.connectHandler(netSocket -> {
    }).listen(ar -> {
      assertTrue(ar.failed());
      assertFalse(ar.succeeded());
      assertNotNull(ar.cause());
      testComplete();
    });
    await();
  }

  @Test
  public void testListenOnWildcardPort() {
    server.close();
    server = vertx.createNetServer(new NetServerOptions().setPort(0));
    server.connectHandler((netSocket) -> {
    }).listen(ar -> {
      assertFalse(ar.failed());
      assertTrue(ar.succeeded());
      assertNull(ar.cause());
      assertTrue(server.actualPort() > 1024);
      assertEquals(server, ar.result());
      testComplete();
    });
    await();
  }

  @Test
  public void testClientCloseHandlersCloseFromClient() {
    startEchoServer(s -> clientCloseHandlers(true));
    await();
  }

  @Test
  public void testClientCloseHandlersCloseFromServer() {
    server.connectHandler((netSocket) -> netSocket.close()).listen((s) -> clientCloseHandlers(false));
    await();
  }

  void clientCloseHandlers(boolean closeFromClient) {
    client.connect(1234, "localhost", ar -> {
      AtomicInteger counter = new AtomicInteger(0);
      ar.result().endHandler(v -> assertEquals(1, counter.incrementAndGet()));
      ar.result().closeHandler(v -> {
        assertEquals(2, counter.incrementAndGet());
        testComplete();
      });
      if (closeFromClient) {
        ar.result().close();
      }
    });
  }

  @Test
  public void testServerCloseHandlersCloseFromClient() {
    serverCloseHandlers(false, s -> client.connect(1234, "localhost", ar -> ar.result().close()));
    await();
  }

  @Test
  public void testServerCloseHandlersCloseFromServer() {
    serverCloseHandlers(true, s -> client.connect(1234, "localhost", ar -> {
    }));
    await();
  }

  void serverCloseHandlers(boolean closeFromServer, Handler<AsyncResult<NetServer>> listenHandler) {
    server.connectHandler((sock) -> {
      AtomicInteger counter = new AtomicInteger(0);
      sock.endHandler(v -> assertEquals(1, counter.incrementAndGet()));
      sock.closeHandler(v -> {
        assertEquals(2, counter.incrementAndGet());
        testComplete();
      });
      if (closeFromServer) {
        sock.close();
      }
    }).listen(listenHandler);
  }

  @Test
  public void testClientDrainHandler() {
    pausingServer((s) -> {
      client.connect(1234, "localhost", ar -> {
        NetSocket sock = ar.result();
        assertFalse(sock.writeQueueFull());
        sock.setWriteQueueMaxSize(1000);
        Buffer buff = TestUtils.randomBuffer(10000);
        vertx.setPeriodic(1, id -> {
          sock.write(buff.copy());
          if (sock.writeQueueFull()) {
            vertx.cancelTimer(id);
            sock.drainHandler(v -> {
              assertFalse(sock.writeQueueFull());
              testComplete();
            });
            // Tell the server to resume
            vertx.eventBus().send("server_resume", "");
          }
        });
      });
    });
    await();
  }

  void pausingServer(Handler<AsyncResult<NetServer>> listenHandler) {
    server.connectHandler(sock -> {
      sock.pause();
      Handler<Message<Buffer>> resumeHandler = (m) -> sock.resume();
      MessageConsumer reg = vertx.eventBus().<Buffer>consumer("server_resume").handler(resumeHandler);
      sock.closeHandler(v -> reg.unregister());
    }).listen(listenHandler);
  }

  @Test
  public void testServerDrainHandler() {
    drainingServer(s -> {
      client.connect(1234, "localhost", ar -> {
        NetSocket sock = ar.result();
        sock.pause();
        setHandlers(sock);
        sock.handler(buf -> {
        });
      });
    });
    await();
  }

  void setHandlers(NetSocket sock) {
    Handler<Message<Buffer>> resumeHandler = m -> sock.resume();
    MessageConsumer reg = vertx.eventBus().<Buffer>consumer("client_resume").handler(resumeHandler);
    sock.closeHandler(v -> reg.unregister());
  }

  void drainingServer(Handler<AsyncResult<NetServer>> listenHandler) {
    server.connectHandler(sock -> {
      assertFalse(sock.writeQueueFull());
      sock.setWriteQueueMaxSize(1000);

      Buffer buff = TestUtils.randomBuffer(10000);
      //Send data until the buffer is full
      vertx.setPeriodic(1, id -> {
        sock.write(buff.copy());
        if (sock.writeQueueFull()) {
          vertx.cancelTimer(id);
          sock.drainHandler(v -> {
            assertFalse(sock.writeQueueFull());
            // End test after a short delay to give the client some time to read the data
            vertx.setTimer(100, id2 -> testComplete());
          });

          // Tell the client to resume
          vertx.eventBus().send("client_resume", "");
        }
      });
    }).listen(listenHandler);
  }

  @Test
  public void testReconnectAttemptsInfinite() {
    reconnectAttempts(-1);
  }

  @Test
  public void testReconnectAttemptsMany() {
    reconnectAttempts(100000);
  }

  void reconnectAttempts(int attempts) {
    client.close();
    client = vertx.createNetClient(new NetClientOptions().setReconnectAttempts(attempts).setReconnectInterval(10));

    //The server delays starting for a a few seconds, but it should still connect
    client.connect(1234, "localhost", (res) -> {
      assertTrue(res.succeeded());
      assertFalse(res.failed());
      testComplete();
    });

    // Start the server after a delay
    vertx.setTimer(2000, id -> startEchoServer(s -> {
    }));

    await();
  }

  @Test
  public void testReconnectAttemptsNotEnough() {
    client.close();
    client = vertx.createNetClient(new NetClientOptions().setReconnectAttempts(100).setReconnectInterval(10));

    client.connect(1234, "localhost", (res) -> {
      assertFalse(res.succeeded());
      assertTrue(res.failed());
      testComplete();
    });

    await();
  }

  @Test
  public void testServerIdleTimeout() {
    server.close();
    server = vertx.createNetServer(new NetServerOptions().setPort(1234).setHost("localhost").setIdleTimeout(1));
    server.connectHandler(s -> {}).listen(ar -> {
      assertTrue(ar.succeeded());
      client.connect(1234, "localhost", res -> {
        assertTrue(res.succeeded());
        NetSocket socket = res.result();
        socket.closeHandler(v -> testComplete());
      });
    });
    await();
  }

  @Test
  public void testClientIdleTimeout() {
    client.close();
    client = vertx.createNetClient(new NetClientOptions().setIdleTimeout(1));

    server.connectHandler(s -> {
    }).listen(ar -> {
      assertTrue(ar.succeeded());
      client.connect(1234, "localhost", res -> {
        assertTrue(res.succeeded());
        NetSocket socket = res.result();
        socket.closeHandler(v -> testComplete());
      });
    });


    await();
  }

  @Test
  // StartTLS
  public void testStartTLSClientTrustAll() throws Exception {
    testTLS(false, false, true, false, false, true, true, true);
  }

  @Test
  // Client trusts all server certs
  public void testTLSClientTrustAll() throws Exception {
    testTLS(false, false, true, false, false, true, true, false);
  }

  @Test
  // Server specifies cert that the client trusts (not trust all)
  public void testTLSClientTrustServerCert() throws Exception {
    testTLS(false, true, true, false, false, false, true, false);
  }

  @Test
  // Server specifies cert that the client doesn't trust
  public void testTLSClientUntrustedServer() throws Exception {
    testTLS(false, false, true, false, false, false, false, false);
  }

  @Test
  //Client specifies cert even though it's not required
  public void testTLSClientCertNotRequired() throws Exception {
    testTLS(true, true, true, true, false, false, true, false);
  }

  @Test
  //Client specifies cert and it's not required
  public void testTLSClientCertRequired() throws Exception {
    testTLS(true, true, true, true, true, false, true, false);
  }

  @Test
  //Client doesn't specify cert but it's required
  public void testTLSClientCertRequiredNoClientCert() throws Exception {
    testTLS(false, true, true, true, true, false, false, false);
  }

  @Test
  //Client specifies cert but it's not trusted
  public void testTLSClientCertClientNotTrusted() throws Exception {
    testTLS(true, true, true, false, true, false, false, false);
  }

  @Test
  // Specify some cipher suites
  public void testTLSCipherSuites() throws Exception {
    testTLS(false, false, true, false, false, true, true, false, ENABLED_CIPHER_SUITES);
  }

  void testTLS(boolean clientCert, boolean clientTrust,
               boolean serverCert, boolean serverTrust,
               boolean requireClientAuth, boolean clientTrustAll,
               boolean shouldPass, boolean startTLS,
               String... enabledCipherSuites) throws Exception {
    server.close();
    NetServerOptions options = new NetServerOptions();
    if (!startTLS) {
      options.setSsl(true);
    }
    if (serverTrust) {
      options.setTrustStoreOptions(new JksOptions().setPath(findFileOnClasspath("tls/server-truststore.jks")).setPassword("wibble"));
    }
    if (serverCert) {
      options.setKeyStoreOptions(new JksOptions().setPath(findFileOnClasspath("tls/server-keystore.jks")).setPassword("wibble"));
    }
    if (requireClientAuth) {
      options.setClientAuthRequired(true);
    }
    for (String suite: enabledCipherSuites) {
      options.addEnabledCipherSuite(suite);
    }

    options.setPort(4043);
    server = vertx.createNetServer(options);
    Handler<NetSocket> serverHandler = socket -> {
      try {
        X509Certificate[] certs = socket.peerCertificateChain();
        if (clientCert) {
          assertNotNull(certs);
          assertEquals(1, certs.length);
        } else {
          assertNull(certs);
        }
      } catch (SSLPeerUnverifiedException e) {
        assertTrue(clientTrust || clientTrustAll);
      }

      AtomicBoolean upgradedServer = new AtomicBoolean();
      socket.handler(buff -> {
        socket.write(buff); // echo the data
        if (startTLS && !upgradedServer.get()) {
          assertFalse(socket.isSsl());
          socket.upgradeToSsl(v -> assertTrue(socket.isSsl()));
          upgradedServer.set(true);
        } else {
          assertTrue(socket.isSsl());
        }
      });
    };
    server.connectHandler(serverHandler).listen(ar -> {
      client.close();
      NetClientOptions clientOptions = new NetClientOptions();
      if (!startTLS) {
        clientOptions.setSsl(true);
        if (clientTrustAll) {
          clientOptions.setTrustAll(true);
        }
        if (clientTrust) {
          clientOptions.setTrustStoreOptions(new JksOptions().setPath(findFileOnClasspath("tls/client-truststore.jks")).setPassword("wibble"));
        }
        if (clientCert) {
          clientOptions.setKeyStoreOptions(new JksOptions().setPath(findFileOnClasspath("tls/client-keystore.jks")).setPassword("wibble"));
        }
        for (String suite: enabledCipherSuites) {
          clientOptions.addEnabledCipherSuite(suite);
        }
      }
      client = vertx.createNetClient(clientOptions);
      client.connect(4043, "localhost", ar2 -> {
        if (ar2.succeeded()) {
          if (!shouldPass) {
            fail("Should not connect");
            return;
          }
          final int numChunks = 100;
          final int chunkSize = 100;
          final Buffer received = Buffer.buffer();
          final Buffer sent = Buffer.buffer();
          final NetSocket socket = ar2.result();

          final AtomicBoolean upgradedClient = new AtomicBoolean();
          socket.handler(buffer -> {
            received.appendBuffer(buffer);
            if (received.length() == sent.length()) {
              assertEquals(sent, received);
              testComplete();
            }
            if (startTLS && !upgradedClient.get()) {
              assertFalse(socket.isSsl());
              socket.upgradeToSsl(v -> {
                assertTrue(socket.isSsl());
                // Now send the rest
                for (int i = 1; i < numChunks; i++) {
                  sendBuffer(socket, sent, chunkSize);
                }
              });
            } else {
              assertTrue(socket.isSsl());
            }
          });

          //Now send some data
          int numToSend = startTLS ? 1 : numChunks;
          for (int i = 0; i < numToSend; i++) {
            sendBuffer(socket, sent, chunkSize);
          }
        } else {
          if (shouldPass) {
            fail("Should not fail to connect");
          } else {
            testComplete();
          }
        }
      });
    });
    await();
  }

  void sendBuffer(NetSocket socket, Buffer sent, int chunkSize) {
    Buffer buff = TestUtils.randomBuffer(chunkSize);
    sent.appendBuffer(buff);
    socket.write(buff);
  }

  @Test
  // Need to:
  // sudo sysctl -w net.core.somaxconn=10000
  // sudo sysctl -w net.ipv4.tcp_max_syn_backlog=10000
  // To get this to reliably pass with a lot of connections.
  public void testSharedServersRoundRobin() throws Exception {

    int numServers = 5;
    int numConnections = numServers * 20;

    List<NetServer> servers = new ArrayList<>();
    Set<NetServer> connectedServers = new ConcurrentHashSet<>();
    Map<NetServer, Integer> connectCount = new ConcurrentHashMap<>();

    CountDownLatch latchListen = new CountDownLatch(numServers);
    CountDownLatch latchConns = new CountDownLatch(numConnections);
    for (int i = 0; i < numServers; i++) {
      NetServer theServer = vertx.createNetServer(new NetServerOptions().setHost("localhost").setPort(1234));
      servers.add(theServer);
      theServer.connectHandler(sock -> {
        connectedServers.add(theServer);
        Integer cnt = connectCount.get(theServer);
        int icnt = cnt == null ? 0 : cnt;
        icnt++;
        connectCount.put(theServer, icnt);
        latchConns.countDown();
      }).listen(ar -> {
        if (ar.succeeded()) {
          latchListen.countDown();
        } else {
          fail("Failed to bind server");
        }
      });
    }
    assertTrue(latchListen.await(10, TimeUnit.SECONDS));

    // Create a bunch of connections
    client.close();
    client = vertx.createNetClient(new NetClientOptions());
    CountDownLatch latchClient = new CountDownLatch(numConnections);
    for (int i = 0; i < numConnections; i++) {
      client.connect(1234, "localhost", res -> {
        if (res.succeeded()) {
          latchClient.countDown();
        } else {
          res.cause().printStackTrace();
          fail("Failed to connect");
        }
      });
    }

    assertTrue(latchClient.await(10, TimeUnit.SECONDS));
    assertTrue(latchConns.await(10, TimeUnit.SECONDS));

    assertEquals(numServers, connectedServers.size());
    for (NetServer server : servers) {
      assertTrue(connectedServers.contains(server));
    }
    assertEquals(numServers, connectCount.size());
    for (int cnt : connectCount.values()) {
      assertEquals(numConnections / numServers, cnt);
    }

    CountDownLatch closeLatch = new CountDownLatch(numServers);

    for (NetServer server : servers) {
      server.close(ar -> {
        assertTrue(ar.succeeded());
        closeLatch.countDown();
      });
    }

    assertTrue(closeLatch.await(10, TimeUnit.SECONDS));

    testComplete();
  }

  @Test
  public void testSharedServersRoundRobinWithOtherServerRunningOnDifferentPort() throws Exception {
    CountDownLatch latch = new CountDownLatch(1);
    // Have a server running on a different port to make sure it doesn't interact
    server.close();
    server = vertx.createNetServer(new NetServerOptions().setPort(4321));
    server.connectHandler(sock -> {
      fail("Should not connect");
    }).listen(ar2 -> {
      if (ar2.succeeded()) {
        latch.countDown();
      } else {
        fail("Failed to bind server");
      }
    });
    awaitLatch(latch);
    testSharedServersRoundRobin();
  }

  @Test
  public void testSharedServersRoundRobinButFirstStartAndStopServer() throws Exception {
    // Start and stop a server on the same port/host before hand to make sure it doesn't interact
    server.close();
    CountDownLatch latch = new CountDownLatch(1);
    server = vertx.createNetServer(new NetServerOptions().setPort(1234));
    server.connectHandler(sock -> {
      fail("Should not connect");
    }).listen(ar -> {
      if (ar.succeeded()) {
        latch.countDown();
      } else {
        fail("Failed to bind server");
      }
    });
    awaitLatch(latch);
    CountDownLatch closeLatch = new CountDownLatch(1);
    server.close(ar -> {
      assertTrue(ar.succeeded());
      closeLatch.countDown();
    });
    assertTrue(closeLatch.await(10, TimeUnit.SECONDS));
    testSharedServersRoundRobin();
  }

  @Test
  // This tests using NetSocket.writeHandlerID (on the server side)
  // Send some data and make sure it is fanned out to all connections
  public void testFanout() throws Exception {

    CountDownLatch latch = new CountDownLatch(1);
    Set<String> connections = new ConcurrentHashSet<>();
    server.connectHandler(socket -> {
      connections.add(socket.writeHandlerID());
      socket.handler(buffer -> {
        for (String actorID : connections) {
          vertx.eventBus().publish(actorID, buffer);
        }
      });
      socket.closeHandler(v -> {
        connections.remove(socket.writeHandlerID());
      });
    });
    server.listen(ar -> {
      assertTrue(ar.succeeded());
      latch.countDown();
    });
    awaitLatch(latch);

    int numConnections = 10;
    CountDownLatch connectLatch = new CountDownLatch(numConnections);
    CountDownLatch receivedLatch = new CountDownLatch(numConnections);
    for (int i = 0; i < numConnections; i++) {
      client.connect(1234, "localhost", res -> {
        connectLatch.countDown();
        res.result().handler(data -> {
          receivedLatch.countDown();
        });
      });
    }
    assertTrue(connectLatch.await(10, TimeUnit.SECONDS));

    // Send some data
    client.connect(1234, "localhost", res -> {
      res.result().write("foo");
    });
    assertTrue(receivedLatch.await(10, TimeUnit.SECONDS));

    testComplete();
  }

  @Test
  public void testRemoteAddress() throws Exception {
    server.connectHandler(socket -> {
      SocketAddress addr = socket.remoteAddress();
      assertEquals("127.0.0.1", addr.host());
    }).listen(ar -> {
      assertTrue(ar.succeeded());
      vertx.createNetClient(new NetClientOptions()).connect(1234, "localhost", result -> {
        NetSocket socket = result.result();
        SocketAddress addr = socket.remoteAddress();
        assertEquals("127.0.0.1", addr.host());
        assertEquals(addr.port(), 1234);
        testComplete();
      });
    });
    await();
  }

  @Test
  public void testWriteSameBufferMoreThanOnce() throws Exception {
    server.connectHandler(socket -> {
      Buffer received = Buffer.buffer();
      socket.handler(buff -> {
        received.appendBuffer(buff);
        if (received.toString().equals("foofoo")) {
          testComplete();
        }
      });
    }).listen(ar -> {
      assertTrue(ar.succeeded());
      client.connect(1234, "localhost", result -> {
        NetSocket socket = result.result();
        Buffer buff = Buffer.buffer("foo");
        socket.write(buff);
        socket.write(buff);
      });
    });
    await();
  }

  @Test
  public void sendFileClientToServer() throws Exception {
    File fDir = testFolder.newFolder();
    String content = TestUtils.randomUnicodeString(10000);
    File file = setupFile(fDir.toString(), "some-file.txt", content);
    Buffer expected = Buffer.buffer(content);
    Buffer received = Buffer.buffer();
    server.connectHandler(sock -> {
      sock.handler(buff -> {
        received.appendBuffer(buff);
        if (received.length() == expected.length()) {
          assertEquals(expected, received);
          testComplete();
        }
      });
      // Send some data to the client to trigger the sendfile
      sock.write("foo");
    });
    server.listen(ar -> {
      assertTrue(ar.succeeded());
      client.connect(1234, "localhost", ar2 -> {
        assertTrue(ar2.succeeded());
        NetSocket sock = ar2.result();
        sock.handler(buf -> {
          sock.sendFile(file.getAbsolutePath());
        });
      });
    });

    await();
  }

  @Test
  public void sendFileServerToClient() throws Exception {
    File fDir = testFolder.newFolder();
    String content = TestUtils.randomUnicodeString(10000);
    File file = setupFile(fDir.toString(), "some-file.txt", content);
    Buffer expected = Buffer.buffer(content);
    Buffer received = Buffer.buffer();
    server.connectHandler(sock -> {
      sock.handler(buf -> {
        sock.sendFile(file.getAbsolutePath());
      });
    });
    server.listen(ar -> {
      assertTrue(ar.succeeded());
      client.connect(1234, "localhost", ar2 -> {
        assertTrue(ar2.succeeded());
        NetSocket sock = ar2.result();
        sock.handler(buff -> {
          received.appendBuffer(buff);
          if (received.length() == expected.length()) {
            assertEquals(expected, received);
            testComplete();
          }
        });
        sock.write("foo");
      });
    });

    await();
  }

  @Test
  public void testSendFileDirectory() throws Exception {
    File fDir = testFolder.newFolder();
    server.connectHandler(socket -> {
      SocketAddress addr = socket.remoteAddress();
      assertEquals("127.0.0.1", addr.host());
    }).listen(ar -> {
      assertTrue(ar.succeeded());
      client.connect(1234, "localhost", result -> {
        assertTrue(result.succeeded());
        NetSocket socket = result.result();
        try {
          socket.sendFile(fDir.getAbsolutePath().toString());
          // should throw exception and never hit the assert
          fail("Should throw exception");
        } catch (IllegalArgumentException e) {
          testComplete();
        }
      });
    });
    await();
  }

  @Test
  public void testServerOptionsCopiedBeforeUse() {
    server.close();
    NetServerOptions options = new NetServerOptions().setPort(1234);
    NetServer server = vertx.createNetServer(options);
    // Now change something - but server should still listen at previous port
    options.setPort(1235);
    server.connectHandler(sock -> {
      testComplete();
    });
    server.listen(ar -> {
      assertTrue(ar.succeeded());
      client.connect(1234, "localhost", ar2 -> {
        assertTrue(ar2.succeeded());
      });
    });
    await();
  }

  @Test
  public void testClientOptionsCopiedBeforeUse() {
    client.close();
    NetClientOptions options = new NetClientOptions();
    client = vertx.createNetClient(options);
    options.setSsl(true);
    // Now change something - but server should ignore this
    server.connectHandler(sock -> {
      testComplete();
    });
    server.listen(ar -> {
      assertTrue(ar.succeeded());
      client.connect(1234, "localhost", ar2 -> {
        assertTrue(ar2.succeeded());
      });
    });
    await();
  }

  @Test
  public void testListenWithNoHandler() {
    try {
      server.listen();
      fail("Should throw exception");
    } catch (IllegalStateException e) {
      // OK
    }
  }

  @Test
  public void testListenWithNoHandler2() {
    try {
      server.listen(ar -> {
        assertFalse(ar.succeeded());
      });
      fail("Should throw exception");
    } catch (IllegalStateException e) {
      // OK
    }
  }

  @Test
  public void testSetHandlerAfterListen() {
    server.connectHandler(sock -> {
    });
    server.listen();
    try {
      server.connectHandler(sock -> {
      });
      fail("Should throw exception");
    } catch (IllegalStateException e) {
      // OK
    }
  }

  @Test
  public void testSetHandlerAfterListen2() {
    server.connectHandler(sock -> {
    });
    server.listen(ar -> {
      assertTrue(ar.succeeded());
      try {
        server.connectHandler(sock -> {
        });
        fail("Should throw exception");
      } catch (IllegalStateException e) {
        // OK
      }
      testComplete();
    });
    await();
  }

  @Test
  public void testListenTwice() {
    server.connectHandler(sock -> {
    });
    server.listen(onSuccess(s -> {
      try {
        server.listen(res -> {});
        fail("Should throw exception");
      } catch (IllegalStateException e) {
        // OK
        testComplete();
      } catch (Exception e) {
        fail(e.getMessage());
      }
    }));
    await();
  }

  @Test
  public void testListenTwice2() {
    server.connectHandler(sock -> {
    });
    server.listen(ar -> {
      assertTrue(ar.succeeded());
      try {
        server.listen(sock -> {
        });
        fail("Should throw exception");
      } catch (IllegalStateException e) {
        // OK
      }
      testComplete();
    });
    await();
  }

  @Test
  public void testCloseTwice() {
    client.close();
    client.close(); // OK
  }

  @Test
  public void testAttemptConnectAfterClose() {
    client.close();
    try {
      client.connect(1234, "localhost", ar -> {
      });
      fail("Should throw exception");
    } catch (IllegalStateException e) {
      //OK
    }
  }

  @Test
  public void testClientMultiThreaded() throws Exception {
    int numThreads = 10;
    Thread[] threads = new Thread[numThreads];
    CountDownLatch latch = new CountDownLatch(numThreads);
    server.connectHandler(socket -> {
      socket.handler(socket::write);
    }).listen(ar -> {
      assertTrue(ar.succeeded());
      for (int i = 0; i < numThreads; i++) {
        threads[i] = new Thread() {
          public void run() {
            client.connect(1234, "localhost", result -> {
              assertTrue(result.succeeded());
              Buffer buff = TestUtils.randomBuffer(100000);
              NetSocket sock = result.result();
              sock.write(buff);
              Buffer received = Buffer.buffer();
              sock.handler(rec -> {
                received.appendBuffer(rec);
                if (received.length() == buff.length()) {
                  assertEquals(buff, received);
                  latch.countDown();
                }
              });
            });
          }
        };
        threads[i].start();
      }
    });
    awaitLatch(latch);
    for (int i = 0; i < numThreads; i++) {
      threads[i].join();
    }
  }

  @Test
  public void testInVerticle() throws Exception {
    testInVerticle(false);
  }

  private void testInVerticle(boolean worker) throws Exception {
    client.close();
    server.close();
    class MyVerticle extends AbstractVerticle {
      Context ctx;
      @Override
      public void start() {
        ctx = context;
        if (worker) {
          assertTrue(ctx instanceof WorkerContext);
        } else {
          assertTrue(ctx instanceof EventLoopContext);
        }
        Thread thr = Thread.currentThread();
        server = vertx.createNetServer(new NetServerOptions().setPort(1234).setHost("localhost"));
        server.connectHandler(sock -> {
          sock.handler(buff -> {
            sock.write(buff);
          });
          assertSame(ctx, context);
          if (!worker) {
            assertSame(thr, Thread.currentThread());
          }
        });
        server.listen(ar -> {
          assertTrue(ar.succeeded());
          assertSame(ctx, context);
          if (!worker) {
            assertSame(thr, Thread.currentThread());
          }
          client = vertx.createNetClient(new NetClientOptions());
          client.connect(1234, "localhost", ar2 -> {
            assertSame(ctx, context);
            if (!worker) {
              assertSame(thr, Thread.currentThread());
            }
            assertTrue(ar2.succeeded());
            NetSocket sock = ar2.result();
            Buffer buff = TestUtils.randomBuffer(10000);
            sock.write(buff);
            Buffer brec = Buffer.buffer();
            sock.handler(rec -> {
              assertSame(ctx, context);
              if (!worker) {
                assertSame(thr, Thread.currentThread());
              }
              brec.appendBuffer(rec);
              if (brec.length() == buff.length()) {
                testComplete();
              }
            });
          });
        });
      }
    }
    MyVerticle verticle = new MyVerticle();
    vertx.deployVerticle(verticle, new DeploymentOptions().setWorker(worker));
    await();
  }

  @Test
  public void testInMultithreadedWorker() throws Exception {
    class MyVerticle extends AbstractVerticle {
      @Override
      public void start() {
        try {
          server = vertx.createNetServer(new NetServerOptions());
          fail("Should throw exception");
        } catch (IllegalStateException e) {
          // OK
        }
        try {
          client = vertx.createNetClient(new NetClientOptions());
          fail("Should throw exception");
        } catch (IllegalStateException e) {
          // OK
        }
        testComplete();
      }
    }
    MyVerticle verticle = new MyVerticle();
    vertx.deployVerticle(verticle, new DeploymentOptions().setWorker(true).setMultiThreaded(true));
    await();
  }

  @Test
  public void testContexts() throws Exception {
    Set<ContextImpl> contexts = new ConcurrentHashSet<>();
    AtomicInteger cnt = new AtomicInteger();
    AtomicReference<ContextImpl> serverConnectContext = new AtomicReference<>();
    // Server connect handler should always be called with same context
    server.connectHandler(sock -> {
      sock.handler(sock::write);
      ContextImpl serverContext = ((VertxInternal) vertx).getContext();
      if (serverConnectContext.get() != null) {
        assertSame(serverConnectContext.get(), serverContext);
      } else {
        serverConnectContext.set(serverContext);
      }
    });
    CountDownLatch latch = new CountDownLatch(1);
    AtomicReference<ContextImpl> listenContext = new AtomicReference<>();
    server.listen(ar -> {
      assertTrue(ar.succeeded());
      listenContext.set(((VertxInternal) vertx).getContext());
      latch.countDown();
    });
    awaitLatch(latch);
    CountDownLatch latch2 = new CountDownLatch(1);
    int numConns = 10;
    // Each connect should be in its own context
    for (int i = 0; i < numConns; i++) {
      client.connect(1234, "localhost", conn -> {
        contexts.add(((VertxInternal) vertx).getContext());
        if (cnt.incrementAndGet() == numConns) {
          assertEquals(numConns, contexts.size());
          latch2.countDown();
        }
      });
    }
    awaitLatch(latch2);
    // Close should be in own context
    server.close(ar -> {
      assertTrue(ar.succeeded());
      ContextImpl closeContext = ((VertxInternal) vertx).getContext();
      assertFalse(contexts.contains(closeContext));
      assertNotSame(serverConnectContext.get(), closeContext);
      assertFalse(contexts.contains(listenContext.get()));
      assertSame(serverConnectContext.get(), listenContext.get());
      testComplete();
    });

    server = null;
    await();
  }

  @Test
  public void testReadStreamPauseResume() {
    server.close();
    server = vertx.createNetServer(new NetServerOptions().setAcceptBacklog(1).setPort(1234).setHost("localhost"));
    NetSocketStream socketStream = server.connectStream();
    AtomicBoolean paused = new AtomicBoolean();
    socketStream.handler(so -> {
      assertTrue(!paused.get());
      so.write("hello");
      so.close();
    });
    server.listen(ar -> {
      assertTrue(ar.succeeded());
      paused.set(true);
      socketStream.pause();
      client.connect(1234, "localhost", ar2 -> {
        assertTrue(ar2.succeeded());
        NetSocket so2 = ar2.result();
        so2.handler(buffer -> {
          fail();
        });
        so2.closeHandler(v -> {
          paused.set(false);
          socketStream.resume();
          client.connect(1234, "localhost", ar3 -> {
            assertTrue(ar3.succeeded());
            NetSocket so3 = ar3.result();
            Buffer buffer = Buffer.buffer();
            so3.handler(buffer::appendBuffer);
            so3.closeHandler(v3 -> {
              assertEquals("hello", buffer.toString("utf-8"));
              testComplete();
            });
          });
        });
      });
    });
    await();
  }

  @Test
  public void testNetSocketStreamCallbackIsAsync() {
    this.server = vertx.createNetServer(new NetServerOptions());
    AtomicInteger done = new AtomicInteger();
    NetSocketStream stream = server.connectStream();
    stream.handler(req -> {});
    ThreadLocal<Object> stack = new ThreadLocal<>();
    stack.set(true);
    stream.endHandler(v -> {
      assertTrue(Vertx.currentContext().isEventLoopContext());
      assertNull(stack.get());
      if (done.incrementAndGet() == 2) {
        testComplete();
      }
    });
    server.listen(ar -> {
      assertTrue(Vertx.currentContext().isEventLoopContext());
      assertNull(stack.get());
      ThreadLocal<Object> stack2 = new ThreadLocal<>();
      stack2.set(true);
      server.close(v -> {
        assertTrue(Vertx.currentContext().isEventLoopContext());
        assertNull(stack2.get());
        if (done.incrementAndGet() == 2) {
          testComplete();
        }
      });
      stack2.set(null);
    });
    await();
  }

  @Test
  public void testMultipleServerClose() {
    this.server = vertx.createNetServer(new NetServerOptions());
    AtomicInteger times = new AtomicInteger();
    // We assume the endHandler and the close completion handler are invoked in the same context task
    ThreadLocal stack = new ThreadLocal();
    stack.set(true);
    server.connectStream().endHandler(v -> {
      assertNull(stack.get());
      assertTrue(Vertx.currentContext().isEventLoopContext());
      times.incrementAndGet();
    });
    server.close(ar1 -> {
      assertNull(stack.get());
      assertTrue(Vertx.currentContext().isEventLoopContext());
      server.close(ar2 -> {
        server.close(ar3 -> {
          assertEquals(1, times.get());
          testComplete();
        });
      });
    });
    await();
  }

  @Test
  public void testInWorker() throws Exception {
    vertx.deployVerticle(new AbstractVerticle() {
      @Override
      public void start() throws Exception {
        assertTrue(Vertx.currentContext().isWorkerContext());
        assertTrue(Context.isOnWorkerThread());
        final Context context = Vertx.currentContext();
        NetServer server1 = vertx.createNetServer(new NetServerOptions().setHost("localhost").setPort(1234));
        server1.connectHandler(conn -> {
          assertTrue(Vertx.currentContext().isWorkerContext());
          assertTrue(Context.isOnWorkerThread());
          assertSame(context, Vertx.currentContext());
          conn.handler(conn::write);
          conn.closeHandler(v -> {
            testComplete();
          });
        }).listen(onSuccess(s -> {
          assertTrue(Vertx.currentContext().isWorkerContext());
          assertTrue(Context.isOnWorkerThread());
          assertSame(context, Vertx.currentContext());
          NetClient client = vertx.createNetClient();
          client.connect(1234, "localhost", onSuccess(res -> {
            assertTrue(Vertx.currentContext().isWorkerContext());
            assertTrue(Context.isOnWorkerThread());
            assertSame(context, Vertx.currentContext());
            res.write("foo");
            res.handler(buff -> {
              assertTrue(Vertx.currentContext().isWorkerContext());
              assertTrue(Context.isOnWorkerThread());
              assertSame(context, Vertx.currentContext());
              res.close();
            });
          }));
        }));
      }
    }, new DeploymentOptions().setWorker(true));
    await();
  }


  private File setupFile(String testDir, String fileName, String content) throws Exception {
    File file = new File(testDir, fileName);
    if (file.exists()) {
      file.delete();
    }
    BufferedWriter out = new BufferedWriter(new OutputStreamWriter(new FileOutputStream(file), "UTF-8"));
    out.write(content);
    out.close();
    return file;
  }

  @Test
  public void testServerWorkerMissBufferWhenBufferArriveBeforeConnectCallback() throws Exception {
    int size = getOptions().getWorkerPoolSize();
    List<Context> workers = createWorkers(size + 1);
    CountDownLatch latch1 = new CountDownLatch(workers.size() - 1);
    workers.get(0).runOnContext(v -> {
      NetServer server = vertx.createNetServer();
      server.connectHandler(so -> {
        so.handler(buf -> {
          assertEquals("hello", buf.toString());
          testComplete();
        });
      });
      server.listen(1234, ar -> {
        assertTrue(ar.succeeded());
        // Create a one second worker starvation
        for (int i = 1; i < workers.size(); i++) {
          workers.get(i).runOnContext(v2 -> {
            latch1.countDown();
            try {
              Thread.sleep(1000);
            } catch (InterruptedException ignore) {
            }
          });
        }
      });
    });
    awaitLatch(latch1);
    NetClient client = vertx.createNetClient();
    client.connect(1234, "localhost", ar -> {
      assertTrue(ar.succeeded());
      NetSocket so = ar.result();
      so.write(Buffer.buffer("hello"));
    });
    await();
  }

  @Test
  public void testClientWorkerMissBufferWhenBufferArriveBeforeConnectCallback() throws Exception {
    int size = getOptions().getWorkerPoolSize();
    List<Context> workers = createWorkers(size + 1);
    CountDownLatch latch1 = new CountDownLatch(1);
    CountDownLatch latch2 = new CountDownLatch(size);
    NetServer server = vertx.createNetServer();
    server.connectHandler(so -> {
      try {
        awaitLatch(latch2);
      } catch (InterruptedException e) {
        fail(e.getMessage());
        return;
      }
      so.write(Buffer.buffer("hello"));
    });
    server.listen(1234, ar -> {
      assertTrue(ar.succeeded());
      latch1.countDown();
    });
    awaitLatch(latch1);
    workers.get(0).runOnContext(v -> {
      NetClient client = vertx.createNetClient();
      client.connect(1234, "localhost", ar -> {
        assertTrue(ar.succeeded());
        NetSocket so = ar.result();
        so.handler(buf -> {
          assertEquals("hello", buf.toString());
          testComplete();
        });
      });
      // Create a one second worker starvation
      for (int i = 1; i < workers.size(); i++) {
        workers.get(i).runOnContext(v2 -> {
          latch2.countDown();
          try {
            Thread.sleep(1000);
          } catch (InterruptedException ignore) {
          }
        });
      }
    });
    await();
  }
}


File: src/test/java/io/vertx/test/core/TestUtils.java
/*
 *
 *  * Copyright 2014 Red Hat, Inc.
 *  *
 *  * All rights reserved. This program and the accompanying materials
 *  * are made available under the terms of the Eclipse Public License v1.0
 *  * and Apache License v2.0 which accompanies this distribution.
 *  *
 *  *     The Eclipse Public License is available at
 *  *     http://www.eclipse.org/legal/epl-v10.html
 *  *
 *  *     The Apache License v2.0 is available at
 *  *     http://www.opensource.org/licenses/apache2.0.php
 *  *
 *  * You may elect to redistribute this code under either of these licenses.
 *  *
 *
 */

package io.vertx.test.core;

import io.vertx.core.buffer.Buffer;

import java.util.Random;

import static org.junit.Assert.fail;

/**
 * @author <a href="http://tfox.org">Tim Fox</a>
 */
public class TestUtils {

  private static Random random = new Random();

  /**
   * Creates a Buffer of random bytes.
   * @param length The length of the Buffer
   * @return the Buffer
   */
  public static Buffer randomBuffer(int length) {
    return randomBuffer(length, false, (byte) 0);
  }

  /**
   * Create an array of random bytes
   * @param length The length of the created array
   * @return the byte array
   */
  public static byte[] randomByteArray(int length) {
    return randomByteArray(length, false, (byte) 0);
  }

  /**
   * Create an array of random bytes
   * @param length The length of the created array
   * @param avoid If true, the resulting array will not contain avoidByte
   * @param avoidByte A byte that is not to be included in the resulting array
   * @return an array of random bytes
   */
  public static byte[] randomByteArray(int length, boolean avoid, byte avoidByte) {
    byte[] line = new byte[length];
    for (int i = 0; i < length; i++) {
      byte rand;
      do {
        rand = randomByte();
      } while (avoid && rand == avoidByte);

      line[i] = rand;
    }
    return line;
  }

  /**
   * Creates a Buffer containing random bytes
   * @param length the size of the Buffer to create
   * @param avoid if true, the resulting Buffer will not contain avoidByte
   * @param avoidByte A byte that is not to be included in the resulting array
   * @return a Buffer of random bytes
   */
  public static Buffer randomBuffer(int length, boolean avoid, byte avoidByte) {
    byte[] line = randomByteArray(length, avoid, avoidByte);
    return Buffer.buffer(line);
  }

  /**
   * @return a random byte
   */
  public static byte randomByte() {
    return (byte) ((int) (Math.random() * 255) - 128);
  }

  /**
   * @return a random int
   */
  public static int randomInt() {
    return random.nextInt();
  }

  /**
   * @return a random port
   */
  public static int randomPortInt() {
    return random.nextInt(65536);
  }

  /**
   * @return a random positive int
   */
  public static int randomPositiveInt() {
    while (true) {
      int rand = random.nextInt();
      if (rand > 0) {
        return rand;
      }
    }
  }

  /**
   * @return a random positive long
   */
  public static long randomPositiveLong() {
    while (true) {
      long rand = random.nextLong();
      if (rand > 0) {
        return rand;
      }
    }
  }

  /**
   * @return a random long
   */
  public static long randomLong() {
    return random.nextLong();
  }

  /**
   * @return a random boolean
   */
  public static boolean randomBoolean() {
    return random.nextBoolean();
  }

  /**
   * @return a random char
   */
  public static char randomChar() {
    return (char)(random.nextInt(16));
  }

  /**
   * @return a random short
   */
  public static short randomShort() {
    return (short)(random.nextInt(16) - Short.MAX_VALUE);
  }

  /**
   * @return a random random float
   */
  public static float randomFloat() {
    return random.nextFloat();
  }

  /**
   * @return a random random double
   */
  public static double randomDouble() {
    return random.nextDouble();
  }

  /**
   * Creates a String containing random unicode characters
   * @param length The length of the string to create
   * @return a String of random unicode characters
   */
  public static String randomUnicodeString(int length) {
    StringBuilder builder = new StringBuilder(length);
    for (int i = 0; i < length; i++) {
      char c;
      do {
        c = (char) (0xFFFF * Math.random());
      } while ((c >= 0xFFFE && c <= 0xFFFF) || (c >= 0xD800 && c <= 0xDFFF)); //Illegal chars
      builder.append(c);
    }
    return builder.toString();
  }

  /**
   * Creates a random string of ascii alpha characters
   * @param length the length of the string to create
   * @return a String of random ascii alpha characters
   */
  public static String randomAlphaString(int length) {
    StringBuilder builder = new StringBuilder(length);
    for (int i = 0; i < length; i++) {
      char c = (char) (65 + 25 * Math.random());
      builder.append(c);
    }
    return builder.toString();
  }

  /**
   * Determine if two byte arrays are equal
   * @param b1 The first byte array to compare
   * @param b2 The second byte array to compare
   * @return true if the byte arrays are equal
   */
  public static boolean byteArraysEqual(byte[] b1, byte[] b2) {
    if (b1.length != b2.length) return false;
    for (int i = 0; i < b1.length; i++) {
      if (b1[i] != b2[i]) return false;
    }
    return true;
  }

  /**
   * Asserts that an IllegalArgumentException is thrown by the code block.
   * @param runnable code block to execute
   */
  public static void assertIllegalArgumentException(Runnable runnable) {
    try {
      runnable.run();
      fail("Should throw IllegalArgumentException");
    } catch (IllegalArgumentException e) {
      // OK
    }
  }

  /**
   * Asserts that a NullPointerException is thrown by the code block.
   * @param runnable code block to execute
   */
  public static void assertNullPointerException(Runnable runnable) {
    try {
      runnable.run();
      fail("Should throw NullPointerException");
    } catch (NullPointerException e) {
      // OK
    }
  }

  /**
   * Asserts that an IllegalStateException is thrown by the code block.
   * @param runnable code block to execute
   */
  public static void assertIllegalStateException(Runnable runnable) {
    try {
      runnable.run();
      fail("Should throw IllegalStateException");
    } catch (IllegalStateException e) {
      // OK
    }
  }

  /**
   * Asserts that an IndexOutOfBoundsException is thrown by the code block.
   * @param runnable code block to execute
   */
  public static void assertIndexOutOfBoundsException(Runnable runnable) {
    try {
      runnable.run();
      fail("Should throw IndexOutOfBoundsException");
    } catch (IndexOutOfBoundsException e) {
      // OK
    }
  }
}


File: src/test/java/io/vertx/test/core/WebsocketTest.java
/*
 * Copyright 2014 Red Hat, Inc.
 *
 * All rights reserved. This program and the accompanying materials
 * are made available under the terms of the Eclipse Public License v1.0
 * and Apache License v2.0 which accompanies this distribution.
 *
 * The Eclipse Public License is available at
 * http://www.eclipse.org/legal/epl-v10.html
 *
 * The Apache License v2.0 is available at
 * http://www.opensource.org/licenses/apache2.0.php
 *
 * You may elect to redistribute this code under either of these licenses.
 */

package io.vertx.test.core;


import io.netty.handler.codec.http.websocketx.WebSocketHandshakeException;
import io.vertx.core.AbstractVerticle;
import io.vertx.core.Context;
import io.vertx.core.DeploymentOptions;
import io.vertx.core.Vertx;
import io.vertx.core.buffer.Buffer;
import io.vertx.core.http.HttpClient;
import io.vertx.core.http.HttpClientOptions;
import io.vertx.core.http.HttpMethod;
import io.vertx.core.http.HttpServer;
import io.vertx.core.http.HttpServerOptions;
import io.vertx.core.http.HttpServerRequest;
import io.vertx.core.http.ServerWebSocket;
import io.vertx.core.http.ServerWebSocketStream;
import io.vertx.core.http.WebSocketBase;
import io.vertx.core.http.WebSocketFrame;
import io.vertx.core.http.WebSocketStream;
import io.vertx.core.http.WebsocketVersion;
import io.vertx.core.impl.ConcurrentHashSet;
import io.vertx.core.net.NetSocket;
import io.vertx.core.streams.ReadStream;
import org.junit.Test;

import java.security.MessageDigest;
import java.security.NoSuchAlgorithmException;
import java.util.ArrayList;
import java.util.Base64;
import java.util.List;
import java.util.Map;
import java.util.Set;
import java.util.concurrent.CompletableFuture;
import java.util.concurrent.ConcurrentHashMap;
import java.util.concurrent.CountDownLatch;
import java.util.concurrent.TimeUnit;
import java.util.concurrent.atomic.AtomicBoolean;
import java.util.concurrent.atomic.AtomicInteger;
import java.util.concurrent.atomic.AtomicReference;
import java.util.function.Consumer;

import static io.vertx.test.core.TestUtils.*;

/**
 * @author <a href="http://tfox.org">Tim Fox</a>
 */
public class WebsocketTest extends VertxTestBase {

  private HttpClient client;
  private HttpServer server;

  public void setUp() throws Exception {
    super.setUp();
    client = vertx.createHttpClient(new HttpClientOptions());
  }

  protected void tearDown() throws Exception {
    client.close();
    if (server != null) {
      CountDownLatch latch = new CountDownLatch(1);
      server.close(ar -> {
        assertTrue(ar.succeeded());
        latch.countDown();
      });
      awaitLatch(latch);
    }
    super.tearDown();
  }

  @Test
  public void testRejectHybi00() throws Exception {
    testReject(WebsocketVersion.V00);
  }

  @Test
  public void testRejectHybi08() throws Exception {
    testReject(WebsocketVersion.V08);
  }


  @Test
  public void testWSBinaryHybi00() throws Exception {
    testWSFrames(true, WebsocketVersion.V00);
  }

  @Test
  public void testWSStringHybi00() throws Exception {
    testWSFrames(false, WebsocketVersion.V00);
  }

  @Test
  public void testWSBinaryHybi08() throws Exception {
    testWSFrames(true, WebsocketVersion.V08);
  }

  @Test
  public void testWSStringHybi08() throws Exception {
    testWSFrames(false, WebsocketVersion.V08);
  }

  @Test
  public void testWSBinaryHybi17() throws Exception {
    testWSFrames(true, WebsocketVersion.V13);
  }

  @Test
  public void testWSStringHybi17() throws Exception {
    testWSFrames(false, WebsocketVersion.V13);
  }

  @Test
  public void testWSStreamsHybi00() throws Exception {
    testWSWriteStream(WebsocketVersion.V00);
  }

  @Test
  public void testWSStreamsHybi08() throws Exception {
    testWSWriteStream(WebsocketVersion.V08);
  }

  @Test
  public void testWSStreamsHybi17() throws Exception {
    testWSWriteStream(WebsocketVersion.V13);
  }

  @Test
  public void testWriteFromConnectHybi00() throws Exception {
    testWriteFromConnectHandler(WebsocketVersion.V00);
  }

  @Test
  public void testWriteFromConnectHybi08() throws Exception {
    testWriteFromConnectHandler(WebsocketVersion.V08);
  }

  @Test
  public void testWriteFromConnectHybi17() throws Exception {
    testWriteFromConnectHandler(WebsocketVersion.V13);
  }

  @Test
  public void testContinuationWriteFromConnectHybi08() throws Exception {
    testContinuationWriteFromConnectHandler(WebsocketVersion.V08);
  }

  @Test
  public void testContinuationWriteFromConnectHybi17() throws Exception {
    testContinuationWriteFromConnectHandler(WebsocketVersion.V13);
  }

  @Test
  public void testValidSubProtocolHybi00() throws Exception {
    testValidSubProtocol(WebsocketVersion.V00);
  }

  @Test
  public void testValidSubProtocolHybi08() throws Exception {
    testValidSubProtocol(WebsocketVersion.V08);
  }

  @Test
  public void testValidSubProtocolHybi17() throws Exception {
    testValidSubProtocol(WebsocketVersion.V13);
  }

  @Test
  public void testInvalidSubProtocolHybi00() throws Exception {
    testInvalidSubProtocol(WebsocketVersion.V00);
  }

  @Test
  public void testInvalidSubProtocolHybi08() throws Exception {
    testInvalidSubProtocol(WebsocketVersion.V08);
  }

  @Test
  public void testInvalidSubProtocolHybi17() throws Exception {
    testInvalidSubProtocol(WebsocketVersion.V13);
  }

  // TODO close and exception tests
  // TODO pause/resume/drain tests

  @Test
  // Client trusts all server certs
  public void testTLSClientTrustAll() throws Exception {
    testTLS(KeyCert.NONE, Trust.NONE, KeyCert.JKS, Trust.NONE, false, false, true, false, true);
  }

  @Test
  // Server specifies cert that the client trusts (not trust all)
  public void testTLSClientTrustServerCert() throws Exception {
    testTLS(KeyCert.NONE, Trust.JKS, KeyCert.JKS, Trust.NONE, false, false, false, false, true);
  }

  @Test
  // Server specifies cert that the client trusts (not trust all)
  public void testTLSClientTrustServerCertPKCS12() throws Exception {
    testTLS(KeyCert.NONE, Trust.JKS, KeyCert.PKCS12, Trust.NONE, false, false, false, false, true);
  }

  @Test
  // Server specifies cert that the client trusts (not trust all)
  public void testTLSClientTrustServerCertPEM() throws Exception {
    testTLS(KeyCert.NONE, Trust.JKS, KeyCert.PEM, Trust.NONE, false, false, false, false, true);
  }

  @Test
  // Server specifies cert that the client trusts via a CA (not trust all)
  public void testTLSClientTrustServerCertPEM_CA() throws Exception {
    testTLS(KeyCert.NONE, Trust.PEM_CA, KeyCert.PEM_CA, Trust.NONE, false, false, false, false, true);
  }

  @Test
  // Server specifies cert that the client trusts (not trust all)
  public void testTLSClientTrustPKCS12ServerCert() throws Exception {
    testTLS(KeyCert.NONE, Trust.PKCS12, KeyCert.JKS, Trust.NONE, false, false, false, false, true);
  }

  @Test
  // Server specifies cert that the client trusts (not trust all)
  public void testTLSClientTrustPEMServerCert() throws Exception {
    testTLS(KeyCert.NONE, Trust.PEM, KeyCert.JKS, Trust.NONE, false, false, false, false, true);
  }

  @Test
  // Server specifies cert that the client doesn't trust
  public void testTLSClientUntrustedServer() throws Exception {
    testTLS(KeyCert.NONE, Trust.NONE, KeyCert.JKS, Trust.NONE, false, false, false, false, false);
  }

  @Test
  //Client specifies cert even though it's not required
  public void testTLSClientCertNotRequired() throws Exception {
    testTLS(KeyCert.JKS, Trust.JKS, KeyCert.JKS, Trust.JKS, false, false, false, false, true);
  }

  @Test
  //Client specifies cert and it is required
  public void testTLSClientCertRequired() throws Exception {
    testTLS(KeyCert.JKS, Trust.JKS, KeyCert.JKS, Trust.JKS, true, false, false, false, true);
  }

  @Test
  //Client specifies cert and it is required
  public void testTLSClientCertRequiredPKCS12() throws Exception {
    testTLS(KeyCert.JKS, Trust.JKS, KeyCert.JKS, Trust.PKCS12, true, false, false, false, true);
  }

  @Test
  //Client specifies cert and it is required
  public void testTLSClientCertRequiredPEM() throws Exception {
    testTLS(KeyCert.JKS, Trust.JKS, KeyCert.JKS, Trust.PEM, true, false, false, false, true);
  }

  @Test
  //Client specifies cert and it is required
  public void testTLSClientCertPKCS12Required() throws Exception {
    testTLS(KeyCert.PKCS12, Trust.JKS, KeyCert.JKS, Trust.JKS, true, false, false, false, true);
  }

  @Test
  //Client specifies cert and it is required
  public void testTLSClientCertPEMRequired() throws Exception {
    testTLS(KeyCert.PEM, Trust.JKS, KeyCert.JKS, Trust.JKS, true, false, false, false, true);
  }

  @Test
  //Client specifies cert signed by CA and it is required
  public void testTLSClientCertPEM_CARequired() throws Exception {
    testTLS(KeyCert.PEM_CA, Trust.JKS, KeyCert.JKS, Trust.PEM_CA, true, false, false, false, true);
  }

  @Test
  //Client doesn't specify cert but it's required
  public void testTLSClientCertRequiredNoClientCert() throws Exception {
    testTLS(KeyCert.NONE, Trust.JKS, KeyCert.JKS, Trust.JKS, true, false, false, false, false);
  }

  @Test
  //Client specifies cert but it's not trusted
  public void testTLSClientCertClientNotTrusted() throws Exception {
    testTLS(KeyCert.JKS, Trust.JKS, KeyCert.JKS, Trust.NONE, true, false, false, false, false);
  }

  @Test
  // Server specifies cert that the client does not trust via a revoked certificate of the CA
  public void testTLSClientRevokedServerCert() throws Exception {
    testTLS(KeyCert.NONE, Trust.PEM_CA, KeyCert.PEM_CA, Trust.NONE, false, false, false, true, false);
  }

  @Test
  //Client specifies cert that the server does not trust via a revoked certificate of the CA
  public void testTLSRevokedClientCertServer() throws Exception {
    testTLS(KeyCert.PEM_CA, Trust.JKS, KeyCert.JKS, Trust.PEM_CA, true, true, false, false, false);
  }

  @Test
  // Test with cipher suites
  public void testTLSCipherSuites() throws Exception {
    testTLS(KeyCert.NONE, Trust.NONE, KeyCert.JKS, Trust.NONE, false, false, true, false, true, ENABLED_CIPHER_SUITES);
  }

  private void testTLS(KeyCert clientCert, Trust clientTrust,
                       KeyCert serverCert, Trust serverTrust,
                       boolean requireClientAuth, boolean serverUsesCrl, boolean clientTrustAll,
                       boolean clientUsesCrl, boolean shouldPass,
                       String... enabledCipherSuites) throws Exception {
    HttpClientOptions options = new HttpClientOptions();
    options.setSsl(true);
    if (clientTrustAll) {
      options.setTrustAll(true);
    }
    if (clientUsesCrl) {
      options.addCrlPath(findFileOnClasspath("tls/ca/crl.pem"));
    }
    setOptions(options, getClientTrustOptions(clientTrust));
    setOptions(options, getClientCertOptions(clientCert));
    for (String suite: enabledCipherSuites) {
      options.addEnabledCipherSuite(suite);
    }
    client = vertx.createHttpClient(options);
    HttpServerOptions serverOptions = new HttpServerOptions();
    serverOptions.setSsl(true);
    setOptions(serverOptions, getServerTrustOptions(serverTrust));
    setOptions(serverOptions, getServerCertOptions(serverCert));
    if (requireClientAuth) {
      serverOptions.setClientAuthRequired(true);
    }
    if (serverUsesCrl) {
      serverOptions.addCrlPath(findFileOnClasspath("tls/ca/crl.pem"));
    }
    for (String suite: enabledCipherSuites) {
      serverOptions.addEnabledCipherSuite(suite);
    }
    server = vertx.createHttpServer(serverOptions.setPort(4043));
    server.websocketHandler(ws -> {
      ws.handler(ws::write);
    });
    server.listen(ar -> {
      assertTrue(ar.succeeded());
      client.websocketStream(4043, HttpTestBase.DEFAULT_HTTP_HOST, "/").
          exceptionHandler(t -> {
            if (shouldPass) {
              t.printStackTrace();
              fail("Should not throw exception");
            } else {
              testComplete();
            }
          }).
          handler(ws -> {
            int size = 100;
            Buffer received = Buffer.buffer();
            ws.handler(data -> {
              received.appendBuffer(data);
              if (received.length() == size) {
                ws.close();
                testComplete();
          }
        });
        Buffer buff = Buffer.buffer(TestUtils.randomByteArray(size));
        ws.writeFrame(WebSocketFrame.binaryFrame(buff, true));
      });
    });
    await();
  }

  @Test
  // Let's manually handle the websocket handshake and write a frame to the client
  public void testHandleWSManually() throws Exception {
    String path = "/some/path";
    String message = "here is some text data";

    server = vertx.createHttpServer(new HttpServerOptions().setPort(HttpTestBase.DEFAULT_HTTP_PORT)).requestHandler(req -> {
      NetSocket sock = getUpgradedNetSocket(req, path);
      // Let's write a Text frame raw
      Buffer buff = Buffer.buffer();
      buff.appendByte((byte)129); // Text frame
      buff.appendByte((byte)message.length());
      buff.appendString(message);
      sock.write(buff);
    });
    server.listen(ar -> {
      assertTrue(ar.succeeded());
      client.websocketStream(HttpTestBase.DEFAULT_HTTP_PORT, HttpTestBase.DEFAULT_HTTP_HOST, path).
          exceptionHandler(t -> fail(t.getMessage())).
          handler(ws -> {
            ws.handler(buff -> {
              assertEquals(message, buff.toString("UTF-8"));
              testComplete();
            });
          });
    });
    await();
  }

  @Test
  public void testSharedServersRoundRobin() throws Exception {

    int numServers = 5;
    int numConnections = numServers * 100;

    List<HttpServer> servers = new ArrayList<>();
    Set<HttpServer> connectedServers = new ConcurrentHashSet<>();
    Map<HttpServer, Integer> connectCount = new ConcurrentHashMap<>();

    CountDownLatch latchListen = new CountDownLatch(numServers);
    CountDownLatch latchConns = new CountDownLatch(numConnections);
    for (int i = 0; i < numServers; i++) {
      HttpServer theServer = vertx.createHttpServer(new HttpServerOptions().setPort(HttpTestBase.DEFAULT_HTTP_PORT));
      servers.add(theServer);
      theServer.websocketHandler(ws -> {
        connectedServers.add(theServer);
        Integer cnt = connectCount.get(theServer);
        int icnt = cnt == null ? 0 : cnt;
        icnt++;
        connectCount.put(theServer, icnt);
        latchConns.countDown();
      }).listen(ar -> {
        if (ar.succeeded()) {
          latchListen.countDown();
        } else {
          fail("Failed to bind server");
        }
      });
    }
    assertTrue(latchListen.await(10, TimeUnit.SECONDS));

    // Create a bunch of connections
    CountDownLatch latchClient = new CountDownLatch(numConnections);
    for (int i = 0; i < numConnections; i++) {
      client.websocket(HttpTestBase.DEFAULT_HTTP_PORT, HttpTestBase.DEFAULT_HTTP_HOST, "/someuri", ws -> {
        ws.closeHandler(v -> latchClient.countDown());
        ws.close();
      });
    }

    assertTrue(latchClient.await(10, TimeUnit.SECONDS));
    assertTrue(latchConns.await(10, TimeUnit.SECONDS));

    assertEquals(numServers, connectedServers.size());
    for (HttpServer server: servers) {
      assertTrue(connectedServers.contains(server));
    }
    assertEquals(numServers, connectCount.size());
    for (int cnt: connectCount.values()) {
      assertEquals(numConnections / numServers, cnt);
    }

    CountDownLatch closeLatch = new CountDownLatch(numServers);

    for (HttpServer server: servers) {
      server.close(ar -> {
        assertTrue(ar.succeeded());
        closeLatch.countDown();
      });
    }

    assertTrue(closeLatch.await(10, TimeUnit.SECONDS));

    testComplete();
  }

  @Test
  public void testSharedServersRoundRobinWithOtherServerRunningOnDifferentPort() throws Exception {
    // Have a server running on a different port to make sure it doesn't interact
    CountDownLatch latch = new CountDownLatch(1);
    HttpServer theServer = vertx.createHttpServer(new HttpServerOptions().setPort(4321));
    theServer.websocketHandler(ws -> {
      fail("Should not connect");
    }).listen(ar -> {
      if (ar.succeeded()) {
        latch.countDown();
      } else {
        fail("Failed to bind server");
      }
    });
    awaitLatch(latch);
    testSharedServersRoundRobin();
  }

  @Test
  public void testSharedServersRoundRobinButFirstStartAndStopServer() throws Exception {
    // Start and stop a server on the same port/host before hand to make sure it doesn't interact
    CountDownLatch latch = new CountDownLatch(1);
    HttpServer theServer = vertx.createHttpServer(new HttpServerOptions().setPort(4321));
    theServer.websocketHandler(ws -> {
      fail("Should not connect");
    }).listen(ar -> {
      if (ar.succeeded()) {
        latch.countDown();
      } else {
        fail("Failed to bind server");
      }
    });
    awaitLatch(latch);
    CountDownLatch closeLatch = new CountDownLatch(1);
    theServer.close(ar -> {
      assertTrue(ar.succeeded());
      closeLatch.countDown();
    });
    assertTrue(closeLatch.await(10, TimeUnit.SECONDS));
    testSharedServersRoundRobin();
  }

  @Test
  public void testWebsocketFrameFactoryArguments() throws Exception {
    assertNullPointerException(() -> WebSocketFrame.binaryFrame(null, true));
    assertNullPointerException(() -> WebSocketFrame.textFrame(null, true));
    assertNullPointerException(() -> WebSocketFrame.continuationFrame(null, true));
  }

  private String sha1(String s) {
    try {
      MessageDigest md = MessageDigest.getInstance("SHA1");
      //Hash the data
      byte[] bytes = md.digest(s.getBytes("UTF-8"));
      return Base64.getEncoder().encodeToString(bytes);
    } catch (Exception e) {
      throw new InternalError("Failed to compute sha-1");
    }
  }


  private NetSocket getUpgradedNetSocket(HttpServerRequest req, String path) {
    assertEquals(path, req.path());
    assertEquals("Upgrade", req.headers().get("Connection"));
    NetSocket sock = req.netSocket();
    String secHeader = req.headers().get("Sec-WebSocket-Key");
    String tmp = secHeader + "258EAFA5-E914-47DA-95CA-C5AB0DC85B11";
    String encoded = sha1(tmp);
    sock.write("HTTP/1.1 101 Web Socket Protocol Handshake\r\n" +
        "Upgrade: WebSocket\r\n" +
        "Connection: Upgrade\r\n" +
        "Sec-WebSocket-Accept: " + encoded + "\r\n" +
        "\r\n");
    return sock;
  }

  private void testWSWriteStream(WebsocketVersion version) throws Exception {

    String path = "/some/path";
    String query = "foo=bar&wibble=eek";
    String uri = path + "?" + query;

    server = vertx.createHttpServer(new HttpServerOptions().setPort(HttpTestBase.DEFAULT_HTTP_PORT)).websocketHandler(ws -> {
      assertEquals(uri, ws.uri());
      assertEquals(path, ws.path());
      assertEquals(query, ws.query());
      assertEquals("Upgrade", ws.headers().get("Connection"));
      ws.handler(data -> ws.write(data));
    });

    server.listen(ar -> {
      assertTrue(ar.succeeded());
      int bsize = 100;
      int sends = 10;

      client.websocket(HttpTestBase.DEFAULT_HTTP_PORT, HttpTestBase.DEFAULT_HTTP_HOST, path + "?" + query, null, version, ws -> {
        final Buffer received = Buffer.buffer();
        ws.handler(data -> {
          received.appendBuffer(data);
          if (received.length() == bsize * sends) {
            ws.close();
            testComplete();
          }
        });
        final Buffer sent = Buffer.buffer();
        for (int i = 0; i < sends; i++) {
          Buffer buff = Buffer.buffer(TestUtils.randomByteArray(bsize));
          ws.write(buff);
          sent.appendBuffer(buff);
        }
      });
    });
    await();
  }

  private void testWSFrames(boolean binary, WebsocketVersion version) throws Exception {

    String path = "/some/path";
    String query = "foo=bar&wibble=eek";
    String uri = path + "?" + query;

    // version 0 doesn't support continuations so we just send 1 frame per message
    int frames = version == WebsocketVersion.V00 ? 1: 10;

    server = vertx.createHttpServer(new HttpServerOptions().setPort(HttpTestBase.DEFAULT_HTTP_PORT)).websocketHandler(ws -> {
      assertEquals(uri, ws.uri());
      assertEquals(path, ws.path());
      assertEquals(query, ws.query());
      assertEquals("Upgrade", ws.headers().get("Connection"));
      AtomicInteger count = new AtomicInteger();
      ws.frameHandler(frame -> {
        if (count.get() == 0) {
          if (binary) {
            assertTrue(frame.isBinary());
            assertFalse(frame.isText());
          } else {
            assertFalse(frame.isBinary());
            assertTrue(frame.isText());
          }
          assertFalse(frame.isContinuation());
        } else {
          assertFalse(frame.isBinary());
          assertFalse(frame.isText());
          assertTrue(frame.isContinuation());
        }
        if (count.get() == frames - 1) {
          assertTrue(frame.isFinal());
        } else {
          assertFalse(frame.isFinal());
        }
        ws.writeFrame(frame);
        if (count.incrementAndGet() == frames) {
          count.set(0);
        }
      });
    });

    server.listen(ar -> {
      assertTrue(ar.succeeded());
      int bsize = 100;

      int msgs = 10;

      client.websocket(HttpTestBase.DEFAULT_HTTP_PORT, HttpTestBase.DEFAULT_HTTP_HOST, path + "?" + query, null,
        version, ws -> {
          final List<Buffer> sent = new ArrayList<>();
          final List<Buffer> received = new ArrayList<>();

          AtomicReference<Buffer> currentReceived = new AtomicReference<>(Buffer.buffer());
          ws.frameHandler(frame -> {
            //received.appendBuffer(frame.binaryData());
            currentReceived.get().appendBuffer(frame.binaryData());
            if (frame.isFinal()) {
              received.add(currentReceived.get());
              currentReceived.set(Buffer.buffer());
            }
            if (received.size() == msgs) {
              int pos = 0;
              for (Buffer rec : received) {
                assertEquals(rec, sent.get(pos++));
              }
              testComplete();
            }
          });

          AtomicReference<Buffer> currentSent = new AtomicReference<>(Buffer.buffer());
          for (int i = 0; i < msgs; i++) {
            for (int j = 0; j < frames; j++) {
              Buffer buff;
              WebSocketFrame frame;
              if (binary) {
                buff = Buffer.buffer(TestUtils.randomByteArray(bsize));
                if (j == 0) {
                  frame = WebSocketFrame.binaryFrame(buff, false);
                } else {
                  frame = WebSocketFrame.continuationFrame(buff, j == frames - 1);
                }
              } else {
                String str = TestUtils.randomAlphaString(bsize);
                buff = Buffer.buffer(str);
                if (j == 0) {
                  frame = WebSocketFrame.textFrame(str, false);
                } else {
                  frame = WebSocketFrame.continuationFrame(buff, j == frames - 1);
                }
              }
              currentSent.get().appendBuffer(buff);
              ws.writeFrame(frame);
              if (j == frames - 1) {
                sent.add(currentSent.get());
                currentSent.set(Buffer.buffer());
              }
            }
          }
        });
    });
    await();
  }

  @Test
  public void testWriteFinalTextFrame() throws Exception {
    testWriteFinalFrame(false);
  }

  @Test
  public void testWriteFinalBinaryFrame() throws Exception {
    testWriteFinalFrame(true);
  }

  private void testWriteFinalFrame(boolean binary) throws Exception {

    String text = TestUtils.randomUnicodeString(100);
    Buffer data = TestUtils.randomBuffer(100);

    Consumer<WebSocketFrame> frameConsumer = frame -> {
      if (binary) {
        assertTrue(frame.isBinary());
        assertFalse(frame.isText());
        assertEquals(data, frame.binaryData());
      } else {
        assertFalse(frame.isBinary());
        assertTrue(frame.isText());
        assertEquals(text, frame.textData());
      }
      assertTrue(frame.isFinal());
    };

    server = vertx.createHttpServer(new HttpServerOptions().setPort(HttpTestBase.DEFAULT_HTTP_PORT)).websocketHandler(ws ->
      ws.frameHandler(frame -> {
        frameConsumer.accept(frame);
        if (binary) {
          ws.writeFinalBinaryFrame(frame.binaryData());
        } else {
          ws.writeFinalTextFrame(frame.textData());
        }
      })
    );

    server.listen(onSuccess(s ->
      client.websocket(HttpTestBase.DEFAULT_HTTP_PORT, HttpTestBase.DEFAULT_HTTP_HOST, "/", ws -> {
        ws.frameHandler(frame -> {
          frameConsumer.accept(frame);
          testComplete();
        });

        if (binary) {
          ws.writeFinalBinaryFrame(data);
        } else {
          ws.writeFinalTextFrame(text);
        }
      })
    ));

    await();
  }

  private void testContinuationWriteFromConnectHandler(WebsocketVersion version) throws Exception {
    String path = "/some/path";
    String firstFrame = "AAA";
    String continuationFrame = "BBB";

    server = vertx.createHttpServer(new HttpServerOptions().setPort(HttpTestBase.DEFAULT_HTTP_PORT)).requestHandler(req -> {
      NetSocket sock = getUpgradedNetSocket(req, path);

      // Let's write a Text frame raw
      Buffer buff = Buffer.buffer();
      buff.appendByte((byte) 0x01); // Incomplete Text frame
      buff.appendByte((byte) firstFrame.length());
      buff.appendString(firstFrame);
      sock.write(buff);

      buff = Buffer.buffer();
      buff.appendByte((byte) (0x00 | 0x80)); // Complete continuation frame
      buff.appendByte((byte) continuationFrame.length());
      buff.appendString(continuationFrame);
      sock.write(buff);
    });

    server.listen(ar -> {
      assertTrue(ar.succeeded());
      client.websocket(HttpTestBase.DEFAULT_HTTP_PORT, HttpTestBase.DEFAULT_HTTP_HOST, path, null, version, ws -> {
        AtomicBoolean receivedFirstFrame = new AtomicBoolean();
        ws.frameHandler(received -> {
          Buffer receivedBuffer = Buffer.buffer(received.textData());
          if (!received.isFinal()) {
            assertEquals(firstFrame, receivedBuffer.toString());
            receivedFirstFrame.set(true);
          } else if (receivedFirstFrame.get() && received.isFinal()) {
            assertEquals(continuationFrame, receivedBuffer.toString());
            ws.close();
            testComplete();
          }
        });
      });
    });
    await();
  }

  private void testWriteFromConnectHandler(WebsocketVersion version) throws Exception {

    String path = "/some/path";
    Buffer buff = Buffer.buffer("AAA");

    server = vertx.createHttpServer(new HttpServerOptions().setPort(HttpTestBase.DEFAULT_HTTP_PORT)).websocketHandler(ws -> {
      assertEquals(path, ws.path());
      ws.writeFrame(WebSocketFrame.binaryFrame(buff, true));
    });
    server.listen(ar -> {
      assertTrue(ar.succeeded());
      client.websocket(HttpTestBase.DEFAULT_HTTP_PORT, HttpTestBase.DEFAULT_HTTP_HOST, path, null, version, ws -> {
        Buffer received = Buffer.buffer();
        ws.handler(data -> {
          received.appendBuffer(data);
          if (received.length() == buff.length()) {
            assertEquals(buff, received);
            ws.close();
            testComplete();
          }
        });
      });
    });
    await();
  }

  private void testValidSubProtocol(WebsocketVersion version) throws Exception {
    String path = "/some/path";
    String subProtocol = "myprotocol";
    Buffer buff = Buffer.buffer("AAA");
    server = vertx.createHttpServer(new HttpServerOptions().setPort(HttpTestBase.DEFAULT_HTTP_PORT).setWebsocketSubProtocol(subProtocol)).websocketHandler(ws -> {
      assertEquals(path, ws.path());
      ws.writeFrame(WebSocketFrame.binaryFrame(buff, true));
    });
    server.listen(ar -> {
      assertTrue(ar.succeeded());
      client.websocket(HttpTestBase.DEFAULT_HTTP_PORT, HttpTestBase.DEFAULT_HTTP_HOST, path, null, version, subProtocol, ws -> {
        final Buffer received = Buffer.buffer();
        ws.handler(data -> {
          received.appendBuffer(data);
          if (received.length() == buff.length()) {
            assertEquals(buff, received);
            ws.close();
            testComplete();
          }
        });
      });
    });
    await();
  }

  private void testInvalidSubProtocol(WebsocketVersion version) throws Exception {
    String path = "/some/path";
    String subProtocol = "myprotocol";
    server = vertx.createHttpServer(new HttpServerOptions().setPort(HttpTestBase.DEFAULT_HTTP_PORT).setWebsocketSubProtocol("invalid")).websocketHandler(ws -> {
    });
    server.listen(onSuccess(ar -> {
      client.websocketStream(HttpTestBase.DEFAULT_HTTP_PORT, HttpTestBase.DEFAULT_HTTP_HOST, path, null, version, subProtocol).
          exceptionHandler(t -> {
            // Should fail
            testComplete();
          }).
          handler(ws -> {
          });
    }));
    await();
  }

  private void testReject(WebsocketVersion version) throws Exception {

    String path = "/some/path";

    server = vertx.createHttpServer(new HttpServerOptions().setPort(HttpTestBase.DEFAULT_HTTP_PORT)).websocketHandler(ws -> {
      assertEquals(path, ws.path());
      ws.reject();
    });

    server.listen(ar -> {
      assertTrue(ar.succeeded());
      client.websocketStream(HttpTestBase.DEFAULT_HTTP_PORT, HttpTestBase.DEFAULT_HTTP_HOST, path, null, version).
          exceptionHandler(t -> testComplete()).
          handler(ws -> fail("Should not be called"));
    });
    await();
  }

  @Test
  public void testWriteMessageHybi00() {
    testWriteMessage(256, WebsocketVersion.V00);
  }

  @Test
  public void testWriteFragmentedMessage1Hybi00() {
    testWriteMessage(65536 + 256, WebsocketVersion.V00);
  }

  @Test
  public void testWriteFragmentedMessage2Hybi00() {
    testWriteMessage(65536 + 65536 + 256, WebsocketVersion.V00);
  }

  @Test
  public void testWriteMessageHybi08() {
    testWriteMessage(256, WebsocketVersion.V08);
  }

  @Test
  public void testWriteFragmentedMessage1Hybi08() {
    testWriteMessage(65536 + 256, WebsocketVersion.V08);
  }

  @Test
  public void testWriteFragmentedMessage2Hybi08() {
    testWriteMessage(65536 + 65536 + 256, WebsocketVersion.V08);
  }

  @Test
  public void testWriteMessageHybi17() {
    testWriteMessage(256, WebsocketVersion.V13);
  }

  @Test
  public void testWriteFragmentedMessage1Hybi17() {
    testWriteMessage(65536 + 256, WebsocketVersion.V13);
  }

  @Test
  public void testWriteFragmentedMessage2Hybi17() {
    testWriteMessage(65536 + 65536 + 256, WebsocketVersion.V13);
  }

  private void testWriteMessage(int size, WebsocketVersion version) {
    String path = "/some/path";
    byte[] expected = TestUtils.randomByteArray(size);
    server = vertx.createHttpServer(new HttpServerOptions().setPort(HttpTestBase.DEFAULT_HTTP_PORT)).websocketHandler(ws -> {
      ws.writeBinaryMessage(Buffer.buffer(expected));
      ws.close();
    });
    server.listen(ar -> {
      assertTrue(ar.succeeded());
      client.websocket(HttpTestBase.DEFAULT_HTTP_PORT, HttpTestBase.DEFAULT_HTTP_HOST, path, null, version, ws -> {
        Buffer actual = Buffer.buffer();
        ws.handler(actual::appendBuffer);
        ws.closeHandler(v -> {
          assertArrayEquals(expected, actual.getBytes());
          testComplete();
        });
      });
    });
    await();
  }

  @Test
  public void testWebsocketPauseAndResume() {
    client.close();
    client = vertx.createHttpClient(new HttpClientOptions().setConnectTimeout(1000));
    String path = "/some/path";
    this.server = vertx.createHttpServer(new HttpServerOptions().setAcceptBacklog(1).setPort(HttpTestBase.DEFAULT_HTTP_PORT));
    AtomicBoolean paused = new AtomicBoolean();
    ReadStream<ServerWebSocket> stream = server.websocketStream();
    stream.handler(ws -> {
      assertFalse(paused.get());
      ws.writeBinaryMessage(Buffer.buffer("whatever"));
      ws.close();
    });
    server.listen(listenAR -> {
      assertTrue(listenAR.succeeded());
      stream.pause();
      paused.set(true);
      client.websocketStream(HttpTestBase.DEFAULT_HTTP_PORT, HttpTestBase.DEFAULT_HTTP_HOST, path).
          exceptionHandler(err -> {
            assertTrue(paused.get());
            assertTrue(err instanceof WebSocketHandshakeException);
            paused.set(false);
            stream.resume();
            client.websocket(HttpTestBase.DEFAULT_HTTP_PORT, HttpTestBase.DEFAULT_HTTP_HOST, path, ws -> {
              ws.handler(buffer -> {
                assertEquals("whatever", buffer.toString("UTF-8"));
                ws.closeHandler(v2 -> {
                  testComplete();
                });
              });
            });
          }).
          handler(ws -> fail());
    });
    await();
  }

  @Test
  public void testClosingServerClosesWebSocketStreamEndHandler() {
    this.server = vertx.createHttpServer(new HttpServerOptions().setPort(HttpTestBase.DEFAULT_HTTP_PORT));
    ReadStream<ServerWebSocket> stream = server.websocketStream();
    AtomicBoolean closed = new AtomicBoolean();
    stream.endHandler(v -> closed.set(true));
    stream.handler(ws -> {
    });
    server.listen(ar -> {
      assertTrue(ar.succeeded());
      assertFalse(closed.get());
      server.close(v -> {
        assertTrue(ar.succeeded());
        assertTrue(closed.get());
        testComplete();
      });
    });
    await();
  }

  @Test
  public void testWebsocketStreamCallbackAsynchronously() {
    this.server = vertx.createHttpServer(new HttpServerOptions().setPort(HttpTestBase.DEFAULT_HTTP_PORT));
    AtomicInteger done = new AtomicInteger();
    ServerWebSocketStream stream = server.websocketStream();
    stream.handler(req -> { });
    ThreadLocal<Object> stack = new ThreadLocal<>();
    stack.set(true);
    stream.endHandler(v -> {
      assertTrue(Vertx.currentContext().isEventLoopContext());
      assertNull(stack.get());
      if (done.incrementAndGet() == 2) {
        testComplete();
      }
    });
    server.listen(ar -> {
      assertTrue(Vertx.currentContext().isEventLoopContext());
      assertNull(stack.get());
      ThreadLocal<Object> stack2 = new ThreadLocal<>();
      stack2.set(true);
      server.close(v -> {
        assertTrue(Vertx.currentContext().isEventLoopContext());
        assertNull(stack2.get());
        if (done.incrementAndGet() == 2) {
          testComplete();
        }
      });
      stack2.set(null);
    });
    await();
  }

  @Test
  public void testMultipleServerClose() {
    this.server = vertx.createHttpServer(new HttpServerOptions().setPort(HttpTestBase.DEFAULT_HTTP_PORT));
    AtomicInteger times = new AtomicInteger();
    // We assume the endHandler and the close completion handler are invoked in the same context task
    ThreadLocal stack = new ThreadLocal();
    stack.set(true);
    server.websocketStream().endHandler(v -> {
      assertNull(stack.get());
      assertTrue(Vertx.currentContext().isEventLoopContext());
      times.incrementAndGet();
    });
    server.close(ar1 -> {
      assertNull(stack.get());
      assertTrue(Vertx.currentContext().isEventLoopContext());
      server.close(ar2 -> {
        server.close(ar3 -> {
          assertEquals(1, times.get());
          testComplete();
        });
      });
    });
    await();
  }

  @Test
  public void testEndHandlerCalled() {
    String path = "/some/path";
    server = vertx.createHttpServer(new HttpServerOptions().setPort(HttpTestBase.DEFAULT_HTTP_PORT)).websocketHandler(WebSocketBase::close);
    AtomicInteger doneCount = new AtomicInteger();
    server.listen(ar -> {
      assertTrue(ar.succeeded());
      client.websocketStream(HttpTestBase.DEFAULT_HTTP_PORT, HttpTestBase.DEFAULT_HTTP_HOST, path, null).
          endHandler(done -> doneCount.incrementAndGet()).
          handler(ws -> {
            assertEquals(0, doneCount.get());
            ws.closeHandler(v -> {
              assertEquals(1, doneCount.get());
              testComplete();
            });
          });
    });
    await();
  }

  @Test
  public void testClearClientHandlersOnEnd() {
    String path = "/some/path";
    server = vertx.createHttpServer(new HttpServerOptions().setPort(HttpTestBase.DEFAULT_HTTP_PORT)).websocketHandler(WebSocketBase::close);
    server.listen(ar -> {
      assertTrue(ar.succeeded());
      client.websocketStream(HttpTestBase.DEFAULT_HTTP_PORT, HttpTestBase.DEFAULT_HTTP_HOST, path, null).
          handler(ws -> {
            ws.endHandler(v -> {
              try {
                ws.endHandler(null);
                ws.exceptionHandler(null);
                ws.handler(null);
              } catch (Exception e) {
                fail("Was expecting to set to null the handlers when the socket is closed");
                return;
              }
              testComplete();
            });
          });
    });
    await();
  }

  @Test
  public void testUpgrade() {
    testUpgrade(false);
  }

  @Test
  public void testUpgradeDelayed() {
    testUpgrade(true);
  }

  private void testUpgrade(boolean delayed) {
    String path = "/some/path";
    server = vertx.createHttpServer(new HttpServerOptions().setPort(HttpTestBase.DEFAULT_HTTP_PORT));
    server.requestHandler(request -> {
      Runnable runner = () -> {
        ServerWebSocket ws = request.upgrade();
        ws.handler(buff -> {
          ws.write(Buffer.buffer("helloworld"));
          ws.close();
        });
      };
      if (delayed) {
        // This tests the case where the last http content comes of the request (its not full) comes in
        // before the upgrade has happened and before HttpServerImpl.expectWebsockets is true
        vertx.runOnContext(v -> {
          runner.run();
        });
      } else {
        runner.run();
      }
    });
    server.listen(ar -> {
      assertTrue(ar.succeeded());
      client.websocketStream(HttpTestBase.DEFAULT_HTTP_PORT, HttpTestBase.DEFAULT_HTTP_HOST, path, null).
        handler(ws -> {
          Buffer buff = Buffer.buffer();
          ws.handler(b -> {
            buff.appendBuffer(b);
          });
          ws.endHandler(v -> {
            assertEquals("helloworld", buff.toString());
            testComplete();
          });
          ws.write(Buffer.buffer("foo"));
        });
    });
    await();
  }



  @Test
  public void testUpgradeInvalidRequest() {
    server = vertx.createHttpServer(new HttpServerOptions().setPort(HttpTestBase.DEFAULT_HTTP_PORT));
    server.requestHandler(request -> {
      try {
        request.upgrade();
        fail("Should throw exception");
      } catch (IllegalStateException e) {
        // OK
      }
      testComplete();
    });
    server.listen(ar -> {
      assertTrue(ar.succeeded());
      client.request(HttpMethod.GET, HttpTestBase.DEFAULT_HTTP_PORT, HttpTestBase.DEFAULT_HTTP_HOST, "/", resp -> {
      }).end();
    });
    await();
  }

  @Test
  public void testRaceConditionWithWebsocketClientEventLoop() {
    testRaceConditionWithWebsocketClient(vertx.getOrCreateContext());
  }

  @Test
  public void testRaceConditionWithWebsocketClientWorker() throws Exception {
    CompletableFuture<Context> fut = new CompletableFuture<>();
    vertx.deployVerticle(new AbstractVerticle() {
      @Override
      public void start() throws Exception {
        fut.complete(context);
      }
    }, new DeploymentOptions().setWorker(true), ar -> {
      if (ar.failed()) {
        fut.completeExceptionally(ar.cause());
      }
    });
    testRaceConditionWithWebsocketClient(fut.get());
  }

  private void testRaceConditionWithWebsocketClient(Context context) {
    server = vertx.createHttpServer(new HttpServerOptions().setPort(HttpTestBase.DEFAULT_HTTP_PORT));
    // Handcrafted websocket handshake for sending a frame immediatly after the handshake
    server.requestHandler(req -> {
      byte[] accept;
      try {
        MessageDigest digest = MessageDigest.getInstance("SHA-1");
        byte[] inputBytes = (req.getHeader("Sec-WebSocket-Key") + "258EAFA5-E914-47DA-95CA-C5AB0DC85B11").getBytes();
        digest.update(inputBytes);
        byte[] hashedBytes = digest.digest();
        accept = Base64.getEncoder().encode(hashedBytes);
      } catch (NoSuchAlgorithmException e) {
        fail(e.getMessage());
        return;
      }
      NetSocket so = req.netSocket();
      Buffer data = Buffer.buffer();
      data.appendString("HTTP/1.1 101 Switching Protocols\r\n");
      data.appendString("Upgrade: websocket\r\n");
      data.appendString("Connection: Upgrade\r\n");
      data.appendString("Sec-WebSocket-Accept: " + new String(accept) + "\r\n");
      data.appendString("\r\n");
      data.appendBytes(new byte[]{
          (byte) 0x82,
          0x05,
          0x68,
          0x65,
          0x6c,
          0x6c,
          0x6f,
      });
      so.write(data);
    });
    server.listen(ar -> {
      assertTrue(ar.succeeded());
      context.runOnContext(v -> {
        client.websocket(HttpTestBase.DEFAULT_HTTP_PORT, HttpTestBase.DEFAULT_HTTP_HOST, "/", ws -> {
          ws.handler(buf -> {
            assertEquals("hello", buf.toString());
            testComplete();
          });
        });
      });
    });
    await();
  }

  @Test
  public void testRaceConditionWithWebsocketClientWorker2() throws Exception {
    int size = getOptions().getWorkerPoolSize() - 4;
    List<Context> workers = createWorkers(size + 1);
    server = vertx.createHttpServer(new HttpServerOptions().setPort(HttpTestBase.DEFAULT_HTTP_PORT));
    server.websocketHandler(ws -> {
      ws.write(Buffer.buffer("hello"));
    });
    server.listen(ar -> {
      assertTrue(ar.succeeded());
      workers.get(0).runOnContext(v -> {
        WebSocketStream webSocketStream = client.websocketStream(HttpTestBase.DEFAULT_HTTP_PORT, HttpTestBase.DEFAULT_HTTP_HOST, "/");
        webSocketStream.handler(ws -> {
          ws.handler(buf -> {
            assertEquals("hello", buf.toString());
            testComplete();
          });
        });
      });
    });
    await();
  }
}
