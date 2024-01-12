Refactoring Types: ['Move Attribute']
m/spotify/helios/common/descriptors/TaskStatusEvent.java
/*
 * Copyright (c) 2014 Spotify AB.
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
 */

package com.spotify.helios.common.descriptors;

import com.google.common.base.Objects;

import com.fasterxml.jackson.annotation.JsonIgnoreProperties;
import com.fasterxml.jackson.annotation.JsonProperty;

/**
 * Represents something that has happened to a Task.
 *
 * A typical JSON representation of a task might be:
 * <pre>
 * {
 *   "status" : { #... see definition of TaskStatus },
 *   "timestamp" : 1410308461448,
 *   "host": "myhost"
 * }
 * </pre>
 */
@JsonIgnoreProperties(ignoreUnknown = true)
public class TaskStatusEvent {
  private final TaskStatus status;
  private final long timestamp;
  private final String host;

  /**
   * Constructor.
   *
   * @param status  The status of the task at the point of the event.
   * @param timestamp The timestamp of the event.
   * @param host The host on which the event occurred.
   */
  public TaskStatusEvent(@JsonProperty("status") final TaskStatus status,
                         @JsonProperty("timestamp") final long timestamp,
                         @JsonProperty("host") final String host) {
    this.status = status;
    this.timestamp = timestamp;
    this.host = host;
  }

  public String getHost() {
    return host;
  }

  public TaskStatus getStatus() {
    return status;
  }

  public long getTimestamp() {
    return timestamp;
  }

  @Override
  public String toString() {
    return Objects.toStringHelper(TaskStatusEvent.class)
        .add("timestamp", timestamp)
        .add("host", host)
        .add("status", status)
        .toString();
  }
}


File: helios-services/src/main/java/com/spotify/helios/agent/TaskHistoryWriter.java
/*
 * Copyright (c) 2014 Spotify AB.
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
 */

package com.spotify.helios.agent;

import com.google.common.annotations.VisibleForTesting;

import com.spotify.helios.common.descriptors.JobId;
import com.spotify.helios.common.descriptors.TaskStatus;
import com.spotify.helios.common.descriptors.TaskStatusEvent;
import com.spotify.helios.servicescommon.QueueingHistoryWriter;
import com.spotify.helios.servicescommon.coordination.Paths;
import com.spotify.helios.servicescommon.coordination.ZooKeeperClient;

import java.io.IOException;
import java.nio.file.Path;

/**
 * Writes task history to ZK.
 */
public class TaskHistoryWriter extends QueueingHistoryWriter<TaskStatusEvent> {

  private static final String KAFKA_TOPIC = "HeliosEvents";

  private final String hostname;

  @Override
  protected String getKey(final TaskStatusEvent event) {
    return event.getStatus().getJob().getId().toString();
  }

  @Override
  protected long getTimestamp(final TaskStatusEvent event) {
    return event.getTimestamp();
  }

  @Override
  protected byte[] toBytes(final TaskStatusEvent event) {
    return event.getStatus().toJsonBytes();
  }

  @Override
  protected String getKafkaTopic() {
    return KAFKA_TOPIC;
  }

  @Override
  protected String getZkEventsPath(TaskStatusEvent event) {
    final JobId jobId = event.getStatus().getJob().getId();
    return Paths.historyJobHostEvents(jobId, hostname);
  }

  public TaskHistoryWriter(final String hostname, final ZooKeeperClient client,
                           final KafkaClientProvider kafkaProvider,
                           final Path backingFile) throws IOException, InterruptedException {
    super(client, backingFile, kafkaProvider);
    this.hostname = hostname;
  }

  public void saveHistoryItem(final TaskStatus status)
      throws InterruptedException {
    saveHistoryItem(status, System.currentTimeMillis());
  }

  public void saveHistoryItem(final TaskStatus status, long timestamp)
      throws InterruptedException {
    add(new TaskStatusEvent(status, timestamp, hostname));
  }

  @Override @VisibleForTesting
  protected void startUp() throws Exception {
    super.startUp();
  }
}


File: helios-services/src/main/java/com/spotify/helios/agent/ZooKeeperAgentModel.java
/*
 * Copyright (c) 2014 Spotify AB.
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
 */

package com.spotify.helios.agent;

import com.google.common.base.Throwables;
import com.google.common.collect.Maps;
import com.google.common.util.concurrent.AbstractIdleService;

import com.spotify.helios.common.Json;
import com.spotify.helios.common.descriptors.JobId;
import com.spotify.helios.common.descriptors.Task;
import com.spotify.helios.common.descriptors.TaskStatus;
import com.spotify.helios.servicescommon.coordination.Paths;
import com.spotify.helios.servicescommon.coordination.PersistentPathChildrenCache;
import com.spotify.helios.servicescommon.coordination.ZooKeeperClient;
import com.spotify.helios.servicescommon.coordination.ZooKeeperClientProvider;
import com.spotify.helios.servicescommon.coordination.ZooKeeperUpdatingPersistentDirectory;

import org.apache.curator.framework.state.ConnectionState;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.io.IOException;
import java.nio.file.Path;
import java.util.Map;
import java.util.concurrent.CopyOnWriteArrayList;

import static com.google.common.base.Preconditions.checkNotNull;
import static com.spotify.helios.common.descriptors.Descriptor.parse;

/**
 * The Helios Agent's view into ZooKeeper.
 *
 * This caches ZK state to local disk so the agent can continue to function in the face of a ZK
 * outage.
 */
public class ZooKeeperAgentModel extends AbstractIdleService implements AgentModel {

  private static final Logger log = LoggerFactory.getLogger(ZooKeeperAgentModel.class);

  private static final String TASK_CONFIG_FILENAME = "task-config.json";
  private static final String TASK_HISTORY_FILENAME = "task-history.json";
  private static final String TASK_STATUS_FILENAME = "task-status.json";

  private final PersistentPathChildrenCache<Task> tasks;
  private final ZooKeeperUpdatingPersistentDirectory taskStatuses;
  private final TaskHistoryWriter historyWriter;

  private final String agent;
  private final CopyOnWriteArrayList<AgentModel.Listener> listeners = new CopyOnWriteArrayList<>();

  public ZooKeeperAgentModel(final ZooKeeperClientProvider provider,
                             final KafkaClientProvider kafkaProvider, final String host,
                             final Path stateDirectory) throws IOException, InterruptedException {
    // TODO(drewc): we're constructing too many heavyweight things in the ctor, these kinds of
    // things should be passed in/provider'd/etc.
    final ZooKeeperClient client = provider.get("ZooKeeperAgentModel_ctor");
    this.agent = checkNotNull(host);
    final Path taskConfigFile = stateDirectory.resolve(TASK_CONFIG_FILENAME);

    this.tasks = client.pathChildrenCache(Paths.configHostJobs(host), taskConfigFile,
                                          Json.type(Task.class));
    tasks.addListener(new JobsListener());
    final Path taskStatusFile = stateDirectory.resolve(TASK_STATUS_FILENAME);

    this.taskStatuses = ZooKeeperUpdatingPersistentDirectory.create("agent-model-task-statuses",
                                                                    provider,
                                                                    taskStatusFile,
                                                                    Paths.statusHostJobs(host));
    this.historyWriter = new TaskHistoryWriter(host, client, kafkaProvider,
        stateDirectory.resolve(TASK_HISTORY_FILENAME));
  }

  @Override
  protected void startUp() throws Exception {
    tasks.startAsync().awaitRunning();
    taskStatuses.startAsync().awaitRunning();
    historyWriter.startAsync().awaitRunning();
  }

  @Override
  protected void shutDown() throws Exception {
    tasks.stopAsync().awaitTerminated();
    taskStatuses.stopAsync().awaitTerminated();
    historyWriter.stopAsync().awaitTerminated();
  }

  private JobId jobIdFromTaskPath(final String path) {
    final String prefix = Paths.configHostJobs(agent) + "/";
    return JobId.fromString(path.replaceFirst(prefix, ""));
  }

  /**
   * Returns the tasks (basically, a pair of {@link JobId} and {@link Task}) for the current agent.
   */
  @Override
  public Map<JobId, Task> getTasks() {
    final Map<JobId, Task> tasks = Maps.newHashMap();
    for (Map.Entry<String, Task> entry : this.tasks.getNodes().entrySet()) {
      final JobId id = jobIdFromTaskPath(entry.getKey());
      tasks.put(id, entry.getValue());
    }
    return tasks;
  }

  /**
   * Returns the {@link TaskStatus}es for all tasks assigned to the current agent.
   */
  @Override
  public Map<JobId, TaskStatus> getTaskStatuses() {
    final Map<JobId, TaskStatus> statuses = Maps.newHashMap();
    for (Map.Entry<String, byte[]> entry : this.taskStatuses.entrySet()) {
      try {
        final JobId id = JobId.fromString(entry.getKey());
        final TaskStatus status = Json.read(entry.getValue(), TaskStatus.class);
        statuses.put(id, status);
      } catch (IOException e) {
        throw Throwables.propagate(e);
      }
    }
    return statuses;
  }

  /**
   * Set the {@link TaskStatus} for the job identified by {@code jobId}.
   */
  @Override
  public void setTaskStatus(final JobId jobId, final TaskStatus status)
      throws InterruptedException {
    log.debug("setting task status: {}", status);
    taskStatuses.put(jobId.toString(), status.toJsonBytes());
    historyWriter.saveHistoryItem(status);
  }

  /**
   * Get the {@link TaskStatus} for the job identified by {@code jobId}.
   */
  @Override
  public TaskStatus getTaskStatus(final JobId jobId) {
    final byte[] data = taskStatuses.get(jobId.toString());
    if (data == null) {
      return null;
    }
    try {
      return parse(data, TaskStatus.class);
    } catch (IOException e) {
      throw Throwables.propagate(e);
    }
  }

  /**
   * Remove the {@link TaskStatus} for the job identified by {@code jobId}.
   */
  @Override
  public void removeTaskStatus(final JobId jobId) throws InterruptedException {
    taskStatuses.remove(jobId.toString());
  }

  /**
   * Add a listener that will be notified when tasks are changed.
   */
  @Override
  public void addListener(final AgentModel.Listener listener) {
    listeners.add(listener);
    listener.tasksChanged(this);
  }

  /**
   * Remove a listener that will be notified when tasks are changed.
   */
  @Override
  public void removeListener(final AgentModel.Listener listener) {
    listeners.remove(listener);
  }

  protected void fireTasksUpdated() {
    for (final AgentModel.Listener listener : listeners) {
      try {
        listener.tasksChanged(this);
      } catch (Exception e) {
        log.error("listener threw exception", e);
      }
    }
  }

  private class JobsListener implements PersistentPathChildrenCache.Listener {

    @Override
    public void nodesChanged(final PersistentPathChildrenCache<?> cache) {
      fireTasksUpdated();
    }

    @Override
    public void connectionStateChanged(final ConnectionState state) {
      // ignore
    }
  }
}


File: helios-services/src/main/java/com/spotify/helios/servicescommon/QueueingHistoryWriter.java
/*
 * Copyright (c) 2014 Spotify AB.
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
 */

package com.spotify.helios.servicescommon;

import com.google.common.base.Function;
import com.google.common.base.Optional;
import com.google.common.base.Supplier;
import com.google.common.collect.ImmutableSet;
import com.google.common.collect.Iterables;
import com.google.common.collect.Lists;
import com.google.common.collect.Maps;
import com.google.common.util.concurrent.AbstractIdleService;
import com.google.common.util.concurrent.MoreExecutors;

import com.fasterxml.jackson.core.type.TypeReference;
import com.spotify.helios.agent.KafkaClientProvider;
import com.spotify.helios.servicescommon.coordination.PathFactory;
import com.spotify.helios.servicescommon.coordination.ZooKeeperClient;

import org.apache.curator.framework.recipes.locks.InterProcessMutex;
import org.apache.kafka.clients.producer.KafkaProducer;
import org.apache.kafka.clients.producer.ProducerRecord;
import org.apache.kafka.clients.producer.RecordMetadata;
import org.apache.kafka.common.serialization.Serializer;
import org.apache.kafka.common.serialization.StringSerializer;
import org.apache.zookeeper.KeeperException;
import org.apache.zookeeper.KeeperException.ConnectionLossException;
import org.apache.zookeeper.KeeperException.NodeExistsException;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.io.IOException;
import java.nio.channels.ClosedByInterruptException;
import java.nio.file.Path;
import java.util.Collections;
import java.util.Deque;
import java.util.List;
import java.util.Map;
import java.util.concurrent.ConcurrentLinkedDeque;
import java.util.concurrent.ConcurrentMap;
import java.util.concurrent.ExecutionException;
import java.util.concurrent.Executors;
import java.util.concurrent.Future;
import java.util.concurrent.ScheduledExecutorService;
import java.util.concurrent.ScheduledThreadPoolExecutor;
import java.util.concurrent.TimeUnit;
import java.util.concurrent.TimeoutException;
import java.util.concurrent.atomic.AtomicInteger;

import static com.google.common.base.Preconditions.checkNotNull;
import static com.google.common.base.Preconditions.checkState;
import static java.util.concurrent.TimeUnit.SECONDS;

/**
 * Writes historical events to ZooKeeper and sends them to Kafka. We attempt to gracefully handle
 * the case where ZK is down by persisting events in a backing file.
 *
 * Theory of operation:
 *
 * 1. Adding an event should never block for any significant amount of time. Specifically, it
 *    should not block on ZK being in any particular state, and ideally not while a file write is
 *    occurring, as the file may get large if ZK has been away for a long time.
 *
 * 2. We set limits on the maximum number of events stored at any particular ZK path, and also the
 *    overall total number of events.
 *
 * To use this class, implement a QueueingHistoryWriter for a specific type of event and call the
 * add(TEvent) method to add an event.
 */
public abstract class QueueingHistoryWriter<TEvent>
    extends AbstractIdleService implements Runnable {
  private static final Logger log = LoggerFactory.getLogger(QueueingHistoryWriter.class);

  public static final int DEFAULT_MAX_EVENTS_PER_PATH = 30;
  public static final int DEFAULT_MAX_TOTAL_EVENTS = 600;

  private static final int DEFAULT_MAX_QUEUE_SIZE = 30;

  private final ScheduledExecutorService zkWriterExecutor =
      MoreExecutors.getExitingScheduledExecutorService(
          (ScheduledThreadPoolExecutor) Executors.newScheduledThreadPool(1), 0, SECONDS);
  private final Map<String, InterProcessMutex> mutexes = Maps.newHashMap();

  private final ConcurrentMap<String, Deque<TEvent>> events;
  private final AtomicInteger count;
  private final ZooKeeperClient client;
  private final PersistentAtomicReference<ConcurrentMap<String, Deque<TEvent>>> backingStore;

  private final Optional<KafkaProducer<String, TEvent>> kafkaProducer;

  /**
   * Get the key associated with an event.
   * @param event
   * @return Key for the event.
   */
  protected abstract String getKey(TEvent event);

  /**
   * Get the Unix timestamp for an event.
   * @param event
   * @return Timestamp for the event.
   */
  protected abstract long getTimestamp(TEvent event);

  /**
   * Get the Kafka topic for events sent to Kafka.
   * @return Topic string.
   */
  protected abstract String getKafkaTopic();

  /**
   * Get the path at which events should be stored. Generally the path will differ based on
   * some parameters of the event. For example, all events associated with a particular host
   * might be stored at a single path.
   *
   * All events will be stored as children of the returned path.
   *
   * @param event
   * @return A ZooKeeper path.
   */
  protected abstract String getZkEventsPath(TEvent event);

  protected abstract byte[] toBytes(TEvent event);

  public int getMaxEventsPerPath() {
    return DEFAULT_MAX_EVENTS_PER_PATH;
  }

  public int getMaxTotalEvents() {
    return DEFAULT_MAX_TOTAL_EVENTS;
  }

  protected int getMaxQueueSize() {
    return DEFAULT_MAX_QUEUE_SIZE;
  }

  public QueueingHistoryWriter(final ZooKeeperClient client, final Path backingFile,
                               final KafkaClientProvider kafkaProvider)
      throws IOException, InterruptedException {
    this.client = checkNotNull(client, "client");
    this.backingStore = PersistentAtomicReference.create(
        checkNotNull(backingFile, "backingFile"),
        new TypeReference<ConcurrentMap<String, Deque<TEvent>>>(){},
        new Supplier<ConcurrentMap<String, Deque<TEvent>>>() {
          @Override public ConcurrentMap<String, Deque<TEvent>> get() {
            return Maps.newConcurrentMap();
          }
        });
    this.events = backingStore.get();

    if (kafkaProvider != null) {
      // Get the Kafka Producer suitable for TaskStatus events.
      this.kafkaProducer = kafkaProvider.getProducer(
          new StringSerializer(), new KafkaEventSerializer());
    } else {
      this.kafkaProducer = Optional.absent();
    }

    // Clean out any errant null values.  Normally shouldn't have any, but we did have a few
    // where it happened, and this will make sure we can get out of a bad state if we get into it.
    final ImmutableSet<String> curKeys = ImmutableSet.copyOf(this.events.keySet());
    for (Object key : curKeys) {
      if (this.events.get(key) == null) {
        this.events.remove(key);
      }
    }

    int eventCount = 0;
    for (Deque<TEvent> deque : events.values()) {
      eventCount += deque.size();
    }
    this.count = new AtomicInteger(eventCount);
  }

  @Override
  protected void startUp() throws Exception {
    zkWriterExecutor.scheduleAtFixedRate(this, 1, 1, TimeUnit.SECONDS);
  }

  @Override
  protected void shutDown() throws Exception {
    zkWriterExecutor.shutdownNow();
    zkWriterExecutor.awaitTermination(1, TimeUnit.MINUTES);

    if (kafkaProducer.isPresent()) {
      // Otherwise it enters an infinite loop for some reason.
      kafkaProducer.get().close();
    }
  }

  /**
   * Add an event to the queue to be written to ZooKeeper and optionally sent to Kafka.
   * @param event
   * @throws InterruptedException
   */
  protected void add(TEvent event) throws InterruptedException {
    // If too many "globally", toss them
    while (count.get() >= getMaxTotalEvents()) {
      getNext();
    }

    final String key = getKey(event);
    final Deque<TEvent> deque = getDeque(key);

    synchronized (deque) {
      // if too many in the particular deque, toss them
      while (deque.size() >= getMaxQueueSize()) {
        deque.remove();
        count.decrementAndGet();
      }
      deque.add(event);
      count.incrementAndGet();
    }

    try {
      backingStore.set(events);
    } catch (ClosedByInterruptException e) {
      log.debug("Writing task status event to backing store was interrupted");
    } catch (IOException e) { // We are best effort after all...
      log.warn("Failed to write task status event to backing store", e);
    }
  }

  private Deque<TEvent> getDeque(final String key) {
    synchronized (events) {
      final Deque<TEvent> deque = events.get(key);
      if (deque == null) {  // try more assertively to get a deque
        final ConcurrentLinkedDeque<TEvent> newDeque =
            new ConcurrentLinkedDeque<TEvent>();
        events.put(key, newDeque);
        return newDeque;
      }
      return deque;
    }
  }

  private TEvent getNext() {
    // Some explanation: We first find the eldest event from amongst the queues (ok, they're
    // deques, but we really use it as a put back queue), and only then to we try to get
    // a lock on the relevant queue from whence we got the event.  Assuming that all worked
    // *and* that the event we have wasn't rolled off due to max-size limitations, we then
    // pull the event off the queue and return it.  We're basically doing optimistic concurrency,
    // and skewing things so that adding to this should be cheap.

    while (true) {
      final TEvent current = findEldestEvent();

      // Didn't find anything that needed processing?
      if (current == null) {
        return null;
      }

      final String key = getKey(current);
      final Deque<TEvent> deque = events.get(key);
      if (deque == null) {
        // shouldn't happen because we should be the only one pulling events off, but....
        continue;
      }

      synchronized (deque) {
        if (!deque.peek().equals(current)) {
          // event got rolled off, try again
          continue;
        }

        // Pull it off the queue and be paranoid.
        final TEvent newCurrent = deque.poll();
        count.decrementAndGet();
        checkState(current.equals(newCurrent), "current should equal newCurrent");
        // Safe because this is the *only* place we hold these two locks at the same time.
        synchronized (events) {
          // Extra paranoia: curDeque should always == deque
          final Deque<TEvent> curDeque = events.get(key);
          if (curDeque != null && curDeque.isEmpty()) {
            events.remove(key);
          }
        }
        return current;
      }
    }
  }

  public boolean isEmpty() {
    return count.get() == 0;
  }

  private void putBack(TEvent event) {
    final String key = getKey(event);
    final Deque<TEvent> queue = getDeque(key);
    synchronized (queue) {
      if (queue.size() >= getMaxQueueSize()) {
        // already full, just toss the event
        return;
      }
      queue.push(event);
      count.incrementAndGet();
    }
  }

  private TEvent findEldestEvent() {
    // We don't lock anything because in the worst case, we just put things in out of order which
    // while not perfect, won't cause any actual harm.  Out of order meaning between jobids, not
    // within the same job id.  Whether this is the best strategy (as opposed to fullest deque)
    // is arguable.
    TEvent current = null;
    for (Deque<TEvent> queue : events.values()) {
      if (queue == null) {
        continue;
      }
      final TEvent event = queue.peek();
      if (current == null || (getTimestamp(event) < getTimestamp(current))) {
        current = event;
      }
    }
    return current;
  }

  private String getZkEventPath(final String eventsPath, final long timestamp) {
    return new PathFactory(eventsPath).path(String.valueOf(timestamp));
  }

  @Override
  public void run() {
    while (true) {
      final TEvent event = getNext();
      if (event == null) {
        return;
      }

      if (tryWriteToZooKeeper(event)) {
        // managed to write to ZK. also send to kafka if we need to. we do it like this
        // to avoid sending duplicate events to kafka in case ZK write fails.
        if (kafkaProducer.isPresent()) {
          sendToKafka(event);
        }
      } else {
        putBack(event);
      }
    }
  }

  private boolean tryWriteToZooKeeper(TEvent event) {
    final String eventsPath = getZkEventsPath(event);

    if (!mutexes.containsKey(eventsPath)) {
      mutexes.put(eventsPath, new InterProcessMutex(client.getCuratorFramework(),
                                                    eventsPath + "_lock"));
    }

    final InterProcessMutex mutex = mutexes.get(eventsPath);
    try {
      mutex.acquire();
    } catch (Exception e) {
      log.error("error acquiring lock for event {} - {}", getKey(event), e);
      return false;
    }

    try {
      log.debug("writing queued event to zookeeper {} {}", getKey(event),
                getTimestamp(event));

      client.ensurePath(eventsPath);
      client.createAndSetData(getZkEventPath(eventsPath, getTimestamp(event)), toBytes(event));

      // See if too many
      final List<String> events = client.getChildren(eventsPath);
      if (events.size() > getMaxEventsPerPath()) {
        trimStatusEvents(events, eventsPath);
      }
    } catch (NodeExistsException e) {
      // Ahh, the two generals problem...  We handle by doing nothing since the thing
      // we wanted in, is in.
      log.debug("event we wanted in is already there");
    } catch (ConnectionLossException e) {
      log.warn("Connection lost while putting event into zookeeper, will retry");
      return false;
    } catch (KeeperException e) {
      log.error("Error putting event into zookeeper, will retry", e);
      return false;
    } finally {
      try {
        mutex.release();
      } catch (Exception e) {
        log.error("error releasing lock for event {} - {}", getKey(event), e);
      }
    }

    return true;
  }

  private void sendToKafka(TEvent event) {
    try {
      final Future<RecordMetadata> future = kafkaProducer.get().send(
          new ProducerRecord<String, TEvent>(getKafkaTopic(), event));
      final RecordMetadata metadata = future.get(5, TimeUnit.SECONDS);
      log.debug("Sent an event to Kafka, meta: {}", metadata);
    } catch (ExecutionException | InterruptedException | TimeoutException e) {
      log.error("Unable to send an event to Kafka", e);
    }
  }

  private void trimStatusEvents(final List<String> events, final String eventsPath) {
    // All this to sort numerically instead of lexically....
    final List<Long> eventsAsLongs = Lists.newArrayList(Iterables.transform(events,
      new Function<String, Long>() {
      @Override
      public Long apply(String name) {
        return Long.valueOf(name);
      }
    }));
    Collections.sort(eventsAsLongs);

    for (int i = 0; i < (eventsAsLongs.size() - getMaxEventsPerPath()); i++) {
      try {
        client.delete(getZkEventPath(eventsPath, eventsAsLongs.get(i)));
      } catch (KeeperException e) {
        log.warn("failure deleting overflow of status events - we're hoping a later"
            + " execution will fix", e);
      }
    }
  }

  public class KafkaEventSerializer implements Serializer<TEvent> {
    @Override
    public void configure(final Map<String, ?> configs, final boolean isKey) { }

    @Override
    public byte[] serialize(final String topic, final TEvent value) {
      return toBytes(value);
    }

    @Override
    public void close() { }
  }
}


File: helios-services/src/test/java/com/spotify/helios/agent/TaskHistoryWriterTest.java
/*
 * Copyright (c) 2014 Spotify AB.
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
 */

package com.spotify.helios.agent;

import com.google.common.collect.ImmutableList;
import com.google.common.collect.Iterables;

import com.spotify.helios.Polling;
import com.spotify.helios.ZooKeeperTestManager;
import com.spotify.helios.ZooKeeperTestingServerManager;
import com.spotify.helios.common.descriptors.Job;
import com.spotify.helios.common.descriptors.JobId;
import com.spotify.helios.common.descriptors.TaskStatus;
import com.spotify.helios.common.descriptors.TaskStatus.State;
import com.spotify.helios.common.descriptors.TaskStatusEvent;
import com.spotify.helios.master.ZooKeeperMasterModel;
import com.spotify.helios.servicescommon.coordination.DefaultZooKeeperClient;
import com.spotify.helios.servicescommon.coordination.Paths;
import com.spotify.helios.servicescommon.coordination.ZooKeeperClient;
import com.spotify.helios.servicescommon.coordination.ZooKeeperClientProvider;
import com.spotify.helios.servicescommon.coordination.ZooKeeperModelReporter;

import org.apache.zookeeper.KeeperException;
import org.junit.After;
import org.junit.Before;
import org.junit.Test;
import org.mockito.invocation.InvocationOnMock;
import org.mockito.stubbing.Answer;

import java.nio.file.Files;
import java.nio.file.Path;
import java.util.List;
import java.util.concurrent.Callable;
import java.util.concurrent.TimeUnit;

import static com.spotify.helios.Polling.await;
import static com.spotify.helios.common.descriptors.Goal.START;
import static org.apache.zookeeper.KeeperException.ConnectionLossException;
import static org.junit.Assert.assertEquals;
import static org.mockito.AdditionalAnswers.delegatesTo;
import static org.mockito.Mockito.doAnswer;
import static org.mockito.Mockito.doThrow;
import static org.mockito.Mockito.mock;
import static org.mockito.Mockito.timeout;
import static org.mockito.Mockito.verify;

public class TaskHistoryWriterTest {

  private static final long TIMESTAMP = 8675309L;
  private static final String HOSTNAME = "hostname";
  private static final Job JOB = Job.newBuilder()
      .setCommand(ImmutableList.<String>of())
      .setImage("image")
      .setName("foo")
      .setVersion("version")
      .build();
  private static final JobId JOB_ID = JOB.getId();
  private static final TaskStatus TASK_STATUS =  TaskStatus.newBuilder()
      .setState(State.CREATING)
      .setJob(JOB)
      .setGoal(START)
      .setContainerId("containerId")
      .build();

  private ZooKeeperTestManager zk;
  private DefaultZooKeeperClient client;
  private KafkaClientProvider kafkaProvider;
  private TaskHistoryWriter writer;
  private ZooKeeperMasterModel masterModel;
  private Path agentStateDirs;

  @Before
  public void setUp() throws Exception {
    zk = new ZooKeeperTestingServerManager();
    agentStateDirs = Files.createTempDirectory("helios-agents");

    client = new DefaultZooKeeperClient(zk.curator());
    kafkaProvider = KafkaClientProvider.getTestingProvider();
    makeWriter(client, kafkaProvider);
    masterModel = new ZooKeeperMasterModel(new ZooKeeperClientProvider(client,
        ZooKeeperModelReporter.noop()));
    client.ensurePath(Paths.configJobs());
    client.ensurePath(Paths.configJobRefs());
    client.ensurePath(Paths.historyJobHostEvents(JOB_ID, HOSTNAME));
    masterModel.registerHost(HOSTNAME, "foo");
    masterModel.addJob(JOB);
  }

  @After
  public void tearDown() throws Exception {
    writer.stopAsync().awaitTerminated();
    zk.stop();
  }

  private void makeWriter(ZooKeeperClient client, KafkaClientProvider kafkaProvider)
          throws Exception {
    writer = new TaskHistoryWriter(HOSTNAME, client, kafkaProvider,
        agentStateDirs.resolve("task-history.json"));
    writer.startUp();
  }

  @Test
  public void testZooKeeperErrorDoesntLoseItemsReally() throws Exception {
    final ZooKeeperClient mockClient = mock(ZooKeeperClient.class, delegatesTo(client));
    makeWriter(mockClient, kafkaProvider);
    final String path = Paths.historyJobHostEventsTimestamp(JOB_ID, HOSTNAME, TIMESTAMP);
    final KeeperException exc = new ConnectionLossException();
    // make save operations fail
    doThrow(exc).when(mockClient).createAndSetData(path, TASK_STATUS.toJsonBytes());

    writer.saveHistoryItem(TASK_STATUS, TIMESTAMP);
    // wait up to 10s for it to fail twice -- and make sure I mocked it correctly.
    verify(mockClient, timeout(10000).atLeast(2)).createAndSetData(path, TASK_STATUS.toJsonBytes());

    // now make the client work
    doAnswer(new Answer<Void>() {
      @Override
      public Void answer(InvocationOnMock invocation) throws Throwable {
        client.createAndSetData(
          (String) invocation.getArguments()[0],
          (byte[]) invocation.getArguments()[1]);
        return null;
      }
    }).when(mockClient).createAndSetData(path, TASK_STATUS.toJsonBytes());

    awaitHistoryItems();
  }

  @Test
  public void testSimpleWorkage() throws Exception {
    writer.saveHistoryItem(TASK_STATUS, TIMESTAMP);

    final TaskStatusEvent historyItem = Iterables.getOnlyElement(awaitHistoryItems());
    assertEquals(JOB_ID, historyItem.getStatus().getJob().getId());
  }

  private Iterable<TaskStatusEvent> awaitHistoryItems() throws Exception {
    return await(40L, TimeUnit.SECONDS, new Callable<Iterable<TaskStatusEvent>>() {
      @Override
      public Iterable<TaskStatusEvent> call() throws Exception {
        final List<TaskStatusEvent> items = masterModel.getJobHistory(JOB_ID);
        return items.isEmpty() ? null : items;
      }
    });
  }

  @Test
  public void testWriteWithZooKeeperDown() throws Exception {
    zk.stop();
    writer.saveHistoryItem(TASK_STATUS, TIMESTAMP);
    zk.start();
    final TaskStatusEvent historyItem = Iterables.getOnlyElement(awaitHistoryItems());
    assertEquals(JOB_ID, historyItem.getStatus().getJob().getId());
  }

  @Test
  public void testWriteWithZooKeeperDownAndInterveningCrash() throws Exception {
    zk.stop();
    writer.saveHistoryItem(TASK_STATUS, TIMESTAMP);
    // simulate a crash by recreating the writer
    writer.stopAsync().awaitTerminated();
    makeWriter(client, kafkaProvider);
    zk.start();
    final TaskStatusEvent historyItem = Iterables.getOnlyElement(awaitHistoryItems());
    assertEquals(JOB_ID, historyItem.getStatus().getJob().getId());
  }

  @Test
  public void testKeepsNoMoreThanMaxHistoryItems() throws Exception {
    // And that it keeps the correct items!

    // Save a superflouous number of events
    for (int i = 0; i < writer.getMaxEventsPerPath() + 20; i++) {
      writer.saveHistoryItem(TASK_STATUS, TIMESTAMP + i);
      Thread.sleep(50);  // just to allow other stuff a chance to run in the background
    }
    // Should converge to 30 items
    List<TaskStatusEvent> events = Polling.await(1, TimeUnit.MINUTES,
      new Callable<List<TaskStatusEvent>>() {
      @Override
      public List<TaskStatusEvent> call() throws Exception {
        if (!writer.isEmpty()) {
          return null;
        }
        final List<TaskStatusEvent> events = masterModel.getJobHistory(JOB_ID);
        if (events.size() == writer.getMaxEventsPerPath()) {
          return events;
        }
        return null;
      }
    });
    assertEquals(TIMESTAMP + writer.getMaxEventsPerPath() + 19,
        Iterables.getLast(events).getTimestamp());
    assertEquals(TIMESTAMP + 20, Iterables.get(events, 0).getTimestamp());
  }
}
