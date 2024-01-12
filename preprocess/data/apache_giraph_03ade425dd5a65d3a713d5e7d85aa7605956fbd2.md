Refactoring Types: ['Move Attribute']
apache/giraph/bsp/CentralizedServiceWorker.java
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

package org.apache.giraph.bsp;

import org.apache.giraph.comm.ServerData;
import org.apache.giraph.comm.WorkerClient;
import org.apache.giraph.graph.FinishedSuperstepStats;
import org.apache.giraph.graph.GlobalStats;
import org.apache.giraph.graph.GraphTaskManager;
import org.apache.giraph.graph.VertexEdgeCount;
import org.apache.giraph.io.superstep_output.SuperstepOutput;
import org.apache.giraph.master.MasterInfo;
import org.apache.giraph.metrics.GiraphTimerContext;
import org.apache.giraph.partition.PartitionOwner;
import org.apache.giraph.partition.PartitionStats;
import org.apache.giraph.partition.PartitionStore;
import org.apache.giraph.worker.WorkerAggregatorHandler;
import org.apache.giraph.worker.WorkerContext;
import org.apache.giraph.worker.WorkerInfo;
import org.apache.giraph.worker.WorkerObserver;
import org.apache.hadoop.io.Writable;
import org.apache.hadoop.io.WritableComparable;

import java.io.IOException;
import java.util.Collection;
import java.util.List;

/**
 * All workers should have access to this centralized service to
 * execute the following methods.
 *
 * @param <I> Vertex id
 * @param <V> Vertex value
 * @param <E> Edge value
 */
@SuppressWarnings("rawtypes")
public interface CentralizedServiceWorker<I extends WritableComparable,
  V extends Writable, E extends Writable>
  extends CentralizedService<I, V, E> {
  /**
   * Setup (must be called prior to any other function)
   *
   * @return Finished superstep stats for the input superstep
   */
  FinishedSuperstepStats setup();

  /**
   * Get the worker information
   *
   * @return Worker information
   */
  WorkerInfo getWorkerInfo();

  /**
   * Get the worker client (for instantiating WorkerClientRequestProcessor
   * instances.
   *
   * @return Worker client
   */
  WorkerClient<I, V, E> getWorkerClient();

  /**
   * Get the worker context.
   *
   * @return worker's WorkerContext
   */
  WorkerContext getWorkerContext();

  /**
   * Get the observers for this Worker.
   *
   * @return array of WorkerObservers.
   */
  WorkerObserver[] getWorkerObservers();

  /**
   * Get the partition store for this worker.
   * The partitions contain the vertices for
   * this worker and can be used to run compute() for the vertices or do
   * checkpointing.
   *
   * @return The partition store for this worker.
   */
  PartitionStore<I, V, E> getPartitionStore();

  /**
   *  Both the vertices and the messages need to be checkpointed in order
   *  for them to be used.  This is done after all messages have been
   *  delivered, but prior to a superstep starting.
   */
  void storeCheckpoint() throws IOException;

  /**
   * Load the vertices, edges, messages from the beginning of a superstep.
   * Will load the vertex partitions as designated by the master and set the
   * appropriate superstep.
   *
   * @param superstep which checkpoint to use
   * @return Graph-wide vertex and edge counts
   * @throws IOException
   */
  VertexEdgeCount loadCheckpoint(long superstep) throws IOException;

  /**
   * Take all steps prior to actually beginning the computation of a
   * superstep.
   *
   * @return Collection of all the partition owners from the master for this
   *         superstep.
   */
  Collection<? extends PartitionOwner> startSuperstep();

  /**
   * Worker is done with its portion of the superstep.  Report the
   * worker level statistics after the computation.
   *
   * @param partitionStatsList All the partition stats for this worker
   * @param superstepTimerContext superstep timer context only given when the
   *      function needs to stop the timer, otherwise null.
   * @return Stats of the superstep completion
   */
  FinishedSuperstepStats finishSuperstep(
      List<PartitionStats> partitionStatsList,
      GiraphTimerContext superstepTimerContext);

  /**
   * Get the partition id that a vertex id would belong to.
   *
   * @param vertexId Vertex id
   * @return Partition id
   */
  int getPartitionId(I vertexId);

  /**
   * Whether a partition with given id exists on this worker.
   *
   * @param partitionId Partition id
   * @return True iff this worker has the specified partition
   */
  boolean hasPartition(Integer partitionId);

  /**
   * Every client will need to get a partition owner from a vertex id so that
   * they know which worker to sent the request to.
   *
   * @param vertexId Vertex index to look for
   * @return PartitionOnwer that should contain this vertex if it exists
   */
  PartitionOwner getVertexPartitionOwner(I vertexId);

  /**
   * Get all partition owners.
   *
   * @return Iterable through partition owners
   */
  Iterable<? extends PartitionOwner> getPartitionOwners();

  /**
   * If desired by the user, vertex partitions are redistributed among
   * workers according to the chosen WorkerGraphPartitioner.
   *
   * @param masterSetPartitionOwners Partition owner info passed from the
   *        master.
   */
  void exchangeVertexPartitions(
      Collection<? extends PartitionOwner> masterSetPartitionOwners);

  /**
   * Get master info
   *
   * @return Master info
   */
  MasterInfo getMasterInfo();

  /**
   * Get the GraphTaskManager that this service is using.  Vertices need to know
   * this.
   *
   * @return the GraphTaskManager instance for this compute node
   */
  GraphTaskManager<I, V, E> getGraphTaskManager();

  /**
   * Operations that will be called if there is a failure by a worker.
   */
  void failureCleanup();

  /**
   * Get server data
   *
   * @return Server data
   */
  ServerData<I, V, E> getServerData();

  /**
   * Get worker aggregator handler
   *
   * @return Worker aggregator handler
   */
  WorkerAggregatorHandler getAggregatorHandler();

  /**
   * Final preparation for superstep, called after startSuperstep and
   * potential loading from checkpoint, right before the computation started
   * TODO how to avoid this additional function
   */
  void prepareSuperstep();

  /**
   * Get the superstep output class
   *
   * @return SuperstepOutput
   */
  SuperstepOutput<I, V, E> getSuperstepOutput();

  /**
   * Clean up the service (no calls may be issued after this)
   *
   * @param finishedSuperstepStats Finished supestep stats
   * @throws IOException
   * @throws InterruptedException
   */
  void cleanup(FinishedSuperstepStats finishedSuperstepStats)
    throws IOException, InterruptedException;

  /**
   * Loads Global stats from zookeeper.
   * @return global stats stored in zookeeper for
   * previous superstep.
   */
  GlobalStats getGlobalStats();
}


File: giraph-core/src/main/java/org/apache/giraph/comm/ServerData.java
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

package org.apache.giraph.comm;

import java.io.IOException;
import java.util.ArrayList;
import java.util.Collections;
import java.util.List;
import java.util.Map;
import java.util.concurrent.ConcurrentMap;

import com.google.common.collect.Iterables;
import com.google.common.collect.Maps;

import org.apache.giraph.bsp.CentralizedServiceWorker;
import org.apache.giraph.comm.aggregators.AllAggregatorServerData;
import org.apache.giraph.comm.aggregators.OwnerAggregatorServerData;
import org.apache.giraph.comm.messages.MessageStore;
import org.apache.giraph.comm.messages.MessageStoreFactory;
import org.apache.giraph.comm.messages.queue.AsyncMessageStoreWrapper;
import org.apache.giraph.conf.GiraphConstants;
import org.apache.giraph.conf.ImmutableClassesGiraphConfiguration;
import org.apache.giraph.edge.EdgeStore;
import org.apache.giraph.edge.EdgeStoreFactory;
import org.apache.giraph.graph.Vertex;
import org.apache.giraph.graph.VertexMutations;
import org.apache.giraph.graph.VertexResolver;
import org.apache.giraph.partition.DiskBackedPartitionStore;
import org.apache.giraph.partition.Partition;
import org.apache.giraph.partition.PartitionStore;
import org.apache.giraph.partition.SimplePartitionStore;
import org.apache.hadoop.io.Writable;
import org.apache.hadoop.io.WritableComparable;
import org.apache.hadoop.mapreduce.Mapper;
import org.apache.log4j.Logger;

/**
 * Anything that the server stores
 *
 * @param <I> Vertex id
 * @param <V> Vertex data
 * @param <E> Edge data
 */
@SuppressWarnings("rawtypes")
public class ServerData<I extends WritableComparable,
    V extends Writable, E extends Writable> {
  /** Class logger */
  private static final Logger LOG =
      Logger.getLogger(ServerData.class);
  /** Configuration */
  private final ImmutableClassesGiraphConfiguration<I, V, E> conf;
  /** Partition store for this worker. */
  private volatile PartitionStore<I, V, E> partitionStore;
  /** Edge store for this worker. */
  private final EdgeStore<I, V, E> edgeStore;
  /** Message store factory */
  private final MessageStoreFactory<I, Writable, MessageStore<I, Writable>>
  messageStoreFactory;
  /**
   * Message store for incoming messages (messages which will be consumed
   * in the next super step)
   */
  private volatile MessageStore<I, Writable> incomingMessageStore;
  /**
   * Message store for current messages (messages which we received in
   * previous super step and which will be consumed in current super step)
   */
  private volatile MessageStore<I, Writable> currentMessageStore;
  /**
   * Map of partition ids to vertex mutations from other workers. These are
   * mutations that should be applied before execution of *current* super step.
   * (accesses to keys should be thread-safe as multiple threads may resolve
   * mutations of different partitions at the same time)
   */
  private ConcurrentMap<Integer,
      ConcurrentMap<I, VertexMutations<I, V, E>>>
      oldPartitionMutations = Maps.newConcurrentMap();
  /**
   * Map of partition ids to vertex mutations from other workers. These are
   * mutations that are coming from other workers as the execution goes one in a
   * super step. These mutations should be applied in the *next* super step.
   * (this should be thread-safe)
   */
  private ConcurrentMap<Integer,
      ConcurrentMap<I, VertexMutations<I, V, E>>>
      partitionMutations = Maps.newConcurrentMap();
  /**
   * Holds aggregtors which current worker owns from current superstep
   */
  private final OwnerAggregatorServerData ownerAggregatorData;
  /**
   * Holds old aggregators from previous superstep
   */
  private final AllAggregatorServerData allAggregatorData;
  /** Service worker */
  private final CentralizedServiceWorker<I, V, E> serviceWorker;

  /** Store for current messages from other workers to this worker */
  private volatile List<Writable> currentWorkerToWorkerMessages =
      Collections.synchronizedList(new ArrayList<Writable>());
  /** Store for message from other workers to this worker for next superstep */
  private volatile List<Writable> incomingWorkerToWorkerMessages =
      Collections.synchronizedList(new ArrayList<Writable>());

  /** Job context (for progress) */
  private final Mapper<?, ?, ?, ?>.Context context;

  /**
   * Constructor.
   *
   * @param service Service worker
   * @param conf Configuration
   * @param messageStoreFactory Factory for message stores
   * @param context Mapper context
   */
  public ServerData(
      CentralizedServiceWorker<I, V, E> service,
      ImmutableClassesGiraphConfiguration<I, V, E> conf,
      MessageStoreFactory<I, Writable, MessageStore<I, Writable>>
          messageStoreFactory,
      Mapper<?, ?, ?, ?>.Context context) {
    this.serviceWorker = service;
    this.conf = conf;
    this.messageStoreFactory = messageStoreFactory;
    if (GiraphConstants.USE_OUT_OF_CORE_GRAPH.get(conf)) {
      partitionStore =
          new DiskBackedPartitionStore<I, V, E>(conf, context,
              getServiceWorker());
    } else {
      partitionStore =
          new SimplePartitionStore<I, V, E>(conf, context);
    }
    EdgeStoreFactory<I, V, E> edgeStoreFactory = conf.createEdgeStoreFactory();
    edgeStoreFactory.initialize(service, conf, context);
    edgeStore = edgeStoreFactory.newStore();
    ownerAggregatorData = new OwnerAggregatorServerData(context);
    allAggregatorData = new AllAggregatorServerData(context, conf);
    this.context = context;
  }

  public EdgeStore<I, V, E> getEdgeStore() {
    return edgeStore;
  }

  /**
   * Return the partition store for this worker.
   *
   * @return The partition store
   */
  public PartitionStore<I, V, E> getPartitionStore() {
    return partitionStore;
  }

  /**
   * Get message store for incoming messages (messages which will be consumed
   * in the next super step)
   *
   * @param <M> Message data
   * @return Incoming message store
   */
  public <M extends Writable> MessageStore<I, M> getIncomingMessageStore() {
    return (MessageStore<I, M>) incomingMessageStore;
  }

  /**
   * Get message store for current messages (messages which we received in
   * previous super step and which will be consumed in current super step)
   *
   * @param <M> Message data
   * @return Current message store
   */
  public <M extends Writable> MessageStore<I, M> getCurrentMessageStore() {
    return (MessageStore<I, M>) currentMessageStore;
  }

  /**
   * Re-initialize message stores.
   * Discards old values if any.
   * @throws IOException
   */
  public void resetMessageStores() throws IOException {
    if (currentMessageStore != null) {
      currentMessageStore.clearAll();
      currentMessageStore = null;
    }
    if (incomingMessageStore != null) {
      incomingMessageStore.clearAll();
      incomingMessageStore = null;
    }
    prepareSuperstep();
  }

  /** Prepare for next super step */
  public void prepareSuperstep() {
    if (currentMessageStore != null) {
      try {
        currentMessageStore.clearAll();
      } catch (IOException e) {
        throw new IllegalStateException(
            "Failed to clear previous message store");
      }
    }
    currentMessageStore =
        incomingMessageStore != null ? incomingMessageStore :
            messageStoreFactory.newStore(conf.getIncomingMessageClasses());
    incomingMessageStore =
        messageStoreFactory.newStore(conf.getOutgoingMessageClasses());
    // finalize current message-store before resolving mutations
    currentMessageStore.finalizeStore();

    currentWorkerToWorkerMessages = incomingWorkerToWorkerMessages;
    incomingWorkerToWorkerMessages =
        Collections.synchronizedList(new ArrayList<Writable>());
  }

  /**
   * In case of async message store we have to wait for all messages
   * to be processed before going into next superstep.
   */
  public void waitForComplete() {
    if (incomingMessageStore instanceof AsyncMessageStoreWrapper) {
      ((AsyncMessageStoreWrapper) incomingMessageStore).waitToComplete();
    }
  }

  /**
   * Get the vertex mutations (synchronize on the values)
   *
   * @return Vertex mutations
   */
  public ConcurrentMap<Integer, ConcurrentMap<I, VertexMutations<I, V, E>>>
  getPartitionMutations() {
    return partitionMutations;
  }

  /**
   * Get holder for aggregators which current worker owns
   *
   * @return Holder for aggregators which current worker owns
   */
  public OwnerAggregatorServerData getOwnerAggregatorData() {
    return ownerAggregatorData;
  }

  /**
   * Get holder for aggregators from previous superstep
   *
   * @return Holder for aggregators from previous superstep
   */
  public AllAggregatorServerData getAllAggregatorData() {
    return allAggregatorData;
  }

  /**
   * Get the reference of the service worker.
   *
   * @return CentralizedServiceWorker
   */
  public CentralizedServiceWorker<I, V, E> getServiceWorker() {
    return this.serviceWorker;
  }

  /**
   * Get and clear worker to worker messages for this superstep. Can be
   * called only once per superstep.
   *
   * @return List of messages for this worker
   */
  public List<Writable> getAndClearCurrentWorkerToWorkerMessages() {
    List<Writable> ret = currentWorkerToWorkerMessages;
    currentWorkerToWorkerMessages = null;
    return ret;
  }

  /**
   * Add incoming message to this worker for next superstep. Thread-safe.
   *
   * @param message Message received
   */
  public void addIncomingWorkerToWorkerMessage(Writable message) {
    incomingWorkerToWorkerMessages.add(message);
  }


  /**
   * Get worker to worker messages received in previous superstep.
   * @return list of current worker to worker messages.
   */
  public List<Writable> getCurrentWorkerToWorkerMessages() {
    return currentWorkerToWorkerMessages;
  }

  /**
   * Prepare resolving mutation.
   */
  public void prepareResolveMutations() {
    oldPartitionMutations = partitionMutations;
    partitionMutations = Maps.newConcurrentMap();
  }

  /**
   * Resolve mutations specific for a partition. This method is called once
   * per partition, before the computation for that partition starts.
   * @param partition The partition to resolve mutations for
   */
  public void resolvePartitionMutation(Partition<I, V, E> partition) {
    Integer partitionId = partition.getId();
    VertexResolver<I, V, E> vertexResolver = conf.createVertexResolver();
    ConcurrentMap<I, VertexMutations<I, V, E>> prevPartitionMutations =
        oldPartitionMutations.get(partitionId);

    // Resolve mutations that are explicitly sent for this partition
    if (prevPartitionMutations != null) {
      for (Map.Entry<I, VertexMutations<I, V, E>> entry : prevPartitionMutations
          .entrySet()) {
        I vertexId = entry.getKey();
        Vertex<I, V, E> originalVertex = partition.getVertex(vertexId);
        VertexMutations<I, V, E> vertexMutations = entry.getValue();
        Vertex<I, V, E> vertex = vertexResolver.resolve(vertexId,
            originalVertex, vertexMutations,
            getCurrentMessageStore().hasMessagesForVertex(entry.getKey()));

        if (LOG.isDebugEnabled()) {
          LOG.debug("resolvePartitionMutations: Resolved vertex index " +
              vertexId + " in partition index " + partitionId +
              " with original vertex " + originalVertex +
              ", returned vertex " + vertex + " on superstep " +
              serviceWorker.getSuperstep() + " with mutations " +
              vertexMutations);
        }

        if (vertex != null) {
          partition.putVertex(vertex);
        } else if (originalVertex != null) {
          partition.removeVertex(vertexId);
          try {
            getCurrentMessageStore().clearVertexMessages(vertexId);
          } catch (IOException e) {
            throw new IllegalStateException("resolvePartitionMutations: " +
                "Caught IOException while clearing messages for a deleted " +
                "vertex due to a mutation");
          }
        }
        context.progress();
      }
    }

    // Keep track of vertices which are not here in the partition, but have
    // received messages
    Iterable<I> destinations = getCurrentMessageStore().
        getPartitionDestinationVertices(partitionId);
    if (!Iterables.isEmpty(destinations)) {
      for (I vertexId : destinations) {
        if (partition.getVertex(vertexId) == null) {
          Vertex<I, V, E> vertex =
              vertexResolver.resolve(vertexId, null, null, true);

          if (LOG.isDebugEnabled()) {
            LOG.debug("resolvePartitionMutations: A non-existing vertex has " +
                "message(s). Added vertex index " + vertexId +
                " in partition index " + partitionId +
                ", vertex = " + vertex + ", on superstep " +
                serviceWorker.getSuperstep());
          }

          if (vertex != null) {
            partition.putVertex(vertex);
          }
          context.progress();
        }
      }
    }
  }
}


File: giraph-core/src/main/java/org/apache/giraph/comm/messages/primitives/long_id/LongAbstractListMessageStore.java
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

package org.apache.giraph.comm.messages.primitives.long_id;

import it.unimi.dsi.fastutil.ints.Int2ObjectOpenHashMap;
import it.unimi.dsi.fastutil.longs.Long2ObjectOpenHashMap;
import org.apache.giraph.bsp.CentralizedServiceWorker;
import org.apache.giraph.conf.ImmutableClassesGiraphConfiguration;
import org.apache.giraph.factories.MessageValueFactory;
import org.apache.giraph.graph.Vertex;
import org.apache.giraph.partition.Partition;
import org.apache.giraph.partition.PartitionOwner;
import org.apache.giraph.utils.VertexIdIterator;
import org.apache.hadoop.io.LongWritable;
import org.apache.hadoop.io.Writable;

import java.util.List;

/**
 * Special message store to be used when ids are LongWritable and no combiner
 * is used.
 * Uses fastutil primitive maps in order to decrease number of objects and
 * get better performance.
 *
 * @param <M> message type
 * @param <L> list type
 */
public abstract class LongAbstractListMessageStore<M extends Writable,
  L extends List> extends LongAbstractMessageStore<M, L> {
  /**
   * Map used to store messages for nascent vertices i.e., ones
   * that did not exist at the start of current superstep but will get
   * created because of sending message to a non-existent vertex id
   */
  private final
  Int2ObjectOpenHashMap<Long2ObjectOpenHashMap<L>> nascentMap;

  /**
   * Constructor
   *
   * @param messageValueFactory Factory for creating message values
   * @param service             Service worker
   * @param config              Hadoop configuration
   */
  public LongAbstractListMessageStore(
      MessageValueFactory<M> messageValueFactory,
      CentralizedServiceWorker<LongWritable, Writable, Writable> service,
      ImmutableClassesGiraphConfiguration<LongWritable,
          Writable, Writable> config) {
    super(messageValueFactory, service, config);
    populateMap();

    // create map for vertex ids (i.e., nascent vertices) not known yet
    nascentMap = new Int2ObjectOpenHashMap<>();
    for (int partitionId : service.getPartitionStore().getPartitionIds()) {
      nascentMap.put(partitionId, new Long2ObjectOpenHashMap<L>());
    }
  }

  /**
   * Populate the map with all vertexIds for each partition
   */
  private void populateMap() { // TODO - can parallelize?
    // populate with vertex ids already known
    for (int partitionId : service.getPartitionStore().getPartitionIds()) {
      Partition<LongWritable, ?, ?> partition = service.getPartitionStore()
          .getOrCreatePartition(partitionId);
      Long2ObjectOpenHashMap<L> partitionMap = map.get(partitionId);
      for (Vertex<LongWritable, ?, ?> vertex : partition) {
        partitionMap.put(vertex.getId().get(), createList());
      }
    }
  }

  /**
   * Create an instance of L
   * @return instance of L
   */
  protected abstract L createList();

  /**
   * Get list for the current vertexId
   *
   * @param iterator vertexId iterator
   * @return list for current vertexId
   */
  protected L getList(
    VertexIdIterator<LongWritable> iterator) {
    PartitionOwner owner =
        service.getVertexPartitionOwner(iterator.getCurrentVertexId());
    long vertexId = iterator.getCurrentVertexId().get();
    int partitionId = owner.getPartitionId();
    Long2ObjectOpenHashMap<L> partitionMap = map.get(partitionId);
    if (!partitionMap.containsKey(vertexId)) {
      synchronized (nascentMap) {
        // assumption: not many nascent vertices are created
        // so overall synchronization is negligible
        Long2ObjectOpenHashMap<L> nascentPartitionMap =
          nascentMap.get(partitionId);
        if (nascentPartitionMap.get(vertexId) == null) {
          nascentPartitionMap.put(vertexId, createList());
        }
        return nascentPartitionMap.get(vertexId);
      }
    }
    return partitionMap.get(vertexId);
  }

  @Override
  public void finalizeStore() {
    for (int partitionId : nascentMap.keySet()) {
      // nascent vertices are present only in nascent map
      map.get(partitionId).putAll(nascentMap.get(partitionId));
    }
    nascentMap.clear();
  }

  // TODO - discussion
  /*
  some approaches for ensuring correctness with parallel inserts
  - current approach: uses a small extra bit of memory by pre-populating
  map & pushes everything map cannot handle to nascentMap
  at the beginning of next superstep compute a single threaded finalizeStore is
  called (so little extra memory + 1 sequential finish ops)
  - used striped parallel fast utils instead (unsure of perf)
  - use concurrent map (every get gets far slower)
  - use reader writer locks (unsure of perf)
  (code looks something like underneath)

      private final ReadWriteLock rwl = new ReentrantReadWriteLock();
      rwl.readLock().lock();
      L list = partitionMap.get(vertexId);
      if (list == null) {
        rwl.readLock().unlock();
        rwl.writeLock().lock();
        if (partitionMap.get(vertexId) == null) {
          list = createList();
          partitionMap.put(vertexId, list);
        }
        rwl.readLock().lock();
        rwl.writeLock().unlock();
      }
      rwl.readLock().unlock();
  - adopted from the article
    http://docs.oracle.com/javase/1.5.0/docs/api/java/util/concurrent/locks/\
    ReentrantReadWriteLock.html
   */
}


File: giraph-core/src/main/java/org/apache/giraph/comm/requests/SendWorkerEdgesRequest.java
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

package org.apache.giraph.comm.requests;

import org.apache.giraph.comm.ServerData;
import org.apache.giraph.edge.Edge;
import org.apache.giraph.utils.ByteArrayVertexIdEdges;
import org.apache.giraph.utils.PairList;
import org.apache.giraph.utils.VertexIdEdges;
import org.apache.hadoop.io.Writable;
import org.apache.hadoop.io.WritableComparable;

/**
 * Send a collection of edges for a partition.
 *
 * @param <I> Vertex id
 * @param <E> Edge data
 */
@SuppressWarnings("unchecked")
public class SendWorkerEdgesRequest<I extends WritableComparable,
    E extends Writable>
    extends SendWorkerDataRequest<I, Edge<I, E>,
    VertexIdEdges<I, E>> {
  /**
   * Constructor used for reflection only
   */
  public SendWorkerEdgesRequest() { }

  /**
   * Constructor used to send request.
   *
   * @param partVertEdges Map of remote partitions =>
   *                     ByteArrayVertexIdEdges
   */
  public SendWorkerEdgesRequest(
      PairList<Integer, VertexIdEdges<I, E>> partVertEdges) {
    this.partitionVertexData = partVertEdges;
  }

  @Override
  public VertexIdEdges<I, E> createVertexIdData() {
    return new ByteArrayVertexIdEdges<>();
  }

  @Override
  public RequestType getType() {
    return RequestType.SEND_WORKER_EDGES_REQUEST;
  }

  @Override
  public void doRequest(ServerData serverData) {
    PairList<Integer, VertexIdEdges<I, E>>.Iterator
        iterator = partitionVertexData.getIterator();
    while (iterator.hasNext()) {
      iterator.next();
      serverData.getEdgeStore().
          addPartitionEdges(iterator.getCurrentFirst(),
              iterator.getCurrentSecond());
    }
  }
}


File: giraph-core/src/main/java/org/apache/giraph/comm/requests/SendWorkerVerticesRequest.java
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

package org.apache.giraph.comm.requests;

import org.apache.giraph.comm.ServerData;
import org.apache.giraph.conf.ImmutableClassesGiraphConfiguration;
import org.apache.giraph.utils.ExtendedDataOutput;
import org.apache.giraph.utils.PairList;
import org.apache.giraph.utils.VertexIterator;
import org.apache.giraph.utils.WritableUtils;
import org.apache.hadoop.io.Writable;
import org.apache.hadoop.io.WritableComparable;
import org.apache.giraph.partition.PartitionStore;
import org.apache.giraph.partition.Partition;
import org.apache.log4j.Logger;
import java.io.DataInput;
import java.io.DataOutput;
import java.io.IOException;

/**
 * Send to a worker one or more partitions of vertices
 *
 * @param <I> Vertex id
 * @param <V> Vertex data
 * @param <E> Edge data
 */
@SuppressWarnings("rawtypes")
public class SendWorkerVerticesRequest<I extends WritableComparable,
    V extends Writable, E extends Writable> extends
    WritableRequest<I, V, E> implements WorkerRequest<I, V, E> {
  /** Class logger */
  private static final Logger LOG =
      Logger.getLogger(SendWorkerVerticesRequest.class);
  /** Worker partitions to be sent */
  private PairList<Integer, ExtendedDataOutput> workerPartitions;

  /**
   * Constructor used for reflection only
   */
  public SendWorkerVerticesRequest() { }

  /**
   * Constructor for sending a request.
   *
   * @param conf Configuration
   * @param workerPartitions Partitions to be send in this request
   */
  public SendWorkerVerticesRequest(
      ImmutableClassesGiraphConfiguration<I, V, E> conf,
      PairList<Integer, ExtendedDataOutput> workerPartitions) {
    this.workerPartitions = workerPartitions;
    setConf(conf);
  }

  @Override
  public void readFieldsRequest(DataInput input) throws IOException {
    int numPartitions = input.readInt();
    workerPartitions = new PairList<Integer, ExtendedDataOutput>();
    workerPartitions.initialize(numPartitions);
    while (numPartitions-- > 0) {
      final int partitionId = input.readInt();
      ExtendedDataOutput partitionData =
          WritableUtils.readExtendedDataOutput(input, getConf());
      workerPartitions.add(partitionId, partitionData);
    }
  }

  @Override
  public void writeRequest(DataOutput output) throws IOException {
    output.writeInt(workerPartitions.getSize());
    PairList<Integer, ExtendedDataOutput>.Iterator
        iterator = workerPartitions.getIterator();
    while (iterator.hasNext()) {
      iterator.next();
      output.writeInt(iterator.getCurrentFirst());
      WritableUtils.writeExtendedDataOutput(
          iterator.getCurrentSecond(), output);
    }
  }

  @Override
  public RequestType getType() {
    return RequestType.SEND_WORKER_VERTICES_REQUEST;
  }

  @Override
  public void doRequest(ServerData<I, V, E> serverData) {
    PairList<Integer, ExtendedDataOutput>.Iterator
        iterator = workerPartitions.getIterator();
    while (iterator.hasNext()) {
      iterator.next();
      VertexIterator<I, V, E> vertexIterator =
          new VertexIterator<I, V, E>(
          iterator.getCurrentSecond(), getConf());

      Partition<I, V, E> partition;
      PartitionStore store = serverData.getPartitionStore();
      partition = store.getOrCreatePartition(iterator.getCurrentFirst());
      partition.addPartitionVertices(vertexIterator);
      store.putPartition(partition);
    }
  }

  @Override
  public int getSerializedSize() {
    // 4 for number of partitions
    int size = super.getSerializedSize() + 4;
    PairList<Integer, ExtendedDataOutput>.Iterator iterator =
        workerPartitions.getIterator();
    while (iterator.hasNext()) {
      iterator.next();
      // 4 bytes for the partition id and 4 bytes for the size
      size += 8 + iterator.getCurrentSecond().getPos();
    }
    return size;
  }
}



File: giraph-core/src/main/java/org/apache/giraph/conf/GiraphConfiguration.java
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

package org.apache.giraph.conf;

import io.netty.buffer.ByteBufAllocator;
import io.netty.buffer.PooledByteBufAllocator;
import io.netty.buffer.UnpooledByteBufAllocator;

import java.net.UnknownHostException;

import org.apache.giraph.aggregators.AggregatorWriter;
import org.apache.giraph.bsp.checkpoints.CheckpointSupportedChecker;
import org.apache.giraph.combiner.MessageCombiner;
import org.apache.giraph.edge.OutEdges;
import org.apache.giraph.edge.ReuseObjectsOutEdges;
import org.apache.giraph.factories.ComputationFactory;
import org.apache.giraph.factories.VertexValueFactory;
import org.apache.giraph.graph.Computation;
import org.apache.giraph.graph.Vertex;
import org.apache.giraph.graph.VertexResolver;
import org.apache.giraph.graph.VertexValueCombiner;
import org.apache.giraph.io.EdgeInputFormat;
import org.apache.giraph.io.EdgeOutputFormat;
import org.apache.giraph.io.MappingInputFormat;
import org.apache.giraph.io.VertexInputFormat;
import org.apache.giraph.io.VertexOutputFormat;
import org.apache.giraph.io.filters.EdgeInputFilter;
import org.apache.giraph.io.filters.VertexInputFilter;
import org.apache.giraph.job.GiraphJobObserver;
import org.apache.giraph.job.GiraphJobRetryChecker;
import org.apache.giraph.master.MasterCompute;
import org.apache.giraph.master.MasterObserver;
import org.apache.giraph.partition.GraphPartitionerFactory;
import org.apache.giraph.partition.Partition;
import org.apache.giraph.partition.ReusesObjectsPartition;
import org.apache.giraph.utils.ReflectionUtils;
import org.apache.giraph.worker.WorkerContext;
import org.apache.giraph.worker.WorkerObserver;
import org.apache.hadoop.conf.Configuration;
import org.apache.hadoop.mapreduce.Mapper;
import org.apache.hadoop.net.DNS;

/**
 * Adds user methods specific to Giraph.  This will be put into an
 * ImmutableClassesGiraphConfiguration that provides the configuration plus
 * the immutable classes.
 *
 * Keeps track of parameters which were set so it easily set them in another
 * copy of configuration.
 */
public class GiraphConfiguration extends Configuration
    implements GiraphConstants {
  /** ByteBufAllocator to be used by netty */
  private ByteBufAllocator nettyBufferAllocator = null;

  /**
   * Constructor that creates the configuration
   */
  public GiraphConfiguration() {
    configureHadoopSecurity();
  }

  /**
   * Constructor.
   *
   * @param conf Configuration
   */
  public GiraphConfiguration(Configuration conf) {
    super(conf);
    configureHadoopSecurity();
  }

  /**
   * Get name of computation being run. We leave this up to the
   * {@link ComputationFactory} to decide what to return.
   *
   * @return Name of computation being run
   */
  public String getComputationName() {
    ComputationFactory compFactory = ReflectionUtils.newInstance(
        getComputationFactoryClass());
    return compFactory.computationName(this);
  }

  /**
   * Get the user's subclassed {@link ComputationFactory}
   *
   * @return User's computation factory class
   */
  public Class<? extends ComputationFactory> getComputationFactoryClass() {
    return COMPUTATION_FACTORY_CLASS.get(this);
  }

  /**
   * Get the user's subclassed {@link Computation}
   *
   * @return User's computation class
   */
  public Class<? extends Computation> getComputationClass() {
    return COMPUTATION_CLASS.get(this);
  }

  /**
   * Set the computation class (required)
   *
   * @param computationClass Runs vertex computation
   */
  public void setComputationClass(
      Class<? extends Computation> computationClass) {
    COMPUTATION_CLASS.set(this, computationClass);
  }

  /**
   * Set the vertex value factory class
   *
   * @param vertexValueFactoryClass Creates default vertex values
   */
  public final void setVertexValueFactoryClass(
      Class<? extends VertexValueFactory> vertexValueFactoryClass) {
    VERTEX_VALUE_FACTORY_CLASS.set(this, vertexValueFactoryClass);
  }

  /**
   * Set the edge input filter class
   *
   * @param edgeFilterClass class to use
   */
  public void setEdgeInputFilterClass(
      Class<? extends EdgeInputFilter> edgeFilterClass) {
    EDGE_INPUT_FILTER_CLASS.set(this, edgeFilterClass);
  }

  /**
   * Set the vertex input filter class
   *
   * @param vertexFilterClass class to use
   */
  public void setVertexInputFilterClass(
      Class<? extends VertexInputFilter> vertexFilterClass) {
    VERTEX_INPUT_FILTER_CLASS.set(this, vertexFilterClass);
  }

  /**
   * Get the vertex edges class
   *
   * @return vertex edges class
   */
  public Class<? extends OutEdges> getOutEdgesClass() {
    return VERTEX_EDGES_CLASS.get(this);
  }

  /**
   * Set the vertex edges class
   *
   * @param outEdgesClass Determines the way edges are stored
   */
  public final void setOutEdgesClass(
      Class<? extends OutEdges> outEdgesClass) {
    VERTEX_EDGES_CLASS.set(this, outEdgesClass);
  }

  /**
   * Set the vertex implementation class
   *
   * @param vertexClass class of the vertex implementation
   */
  public final void setVertexClass(Class<? extends Vertex> vertexClass) {
    VERTEX_CLASS.set(this, vertexClass);
  }


  /**
   * Set the vertex edges class used during edge-based input (if different
   * from the one used during computation)
   *
   * @param inputOutEdgesClass Determines the way edges are stored
   */
  public final void setInputOutEdgesClass(
      Class<? extends OutEdges> inputOutEdgesClass) {
    INPUT_VERTEX_EDGES_CLASS.set(this, inputOutEdgesClass);
  }

  /**
   * True if the {@link org.apache.giraph.edge.OutEdges} implementation
   * copies the passed edges to its own data structure,
   * i.e. it doesn't keep references to Edge objects, target vertex ids or edge
   * values passed to add() or initialize().
   * This makes it possible to reuse edge objects passed to the data
   * structure, to minimize object instantiation (see for example
   * EdgeStore#addPartitionEdges()).
   *
   * @return True iff we can reuse the edge objects
   */
  public boolean reuseEdgeObjects() {
    return ReuseObjectsOutEdges.class.isAssignableFrom(
        getOutEdgesClass());
  }

  /**
   * True if the {@link Partition} implementation copies the passed vertices
   * to its own data structure, i.e. it doesn't keep references to Vertex
   * objects passed to it.
   * This makes it possible to reuse vertex objects passed to the data
   * structure, to minimize object instantiation.
   *
   * @return True iff we can reuse the vertex objects
   */
  public boolean reuseVertexObjects() {
    return ReusesObjectsPartition.class.isAssignableFrom(getPartitionClass());
  }

  /**
   * Get Partition class used
   * @return Partition class
   */
  public Class<? extends Partition> getPartitionClass() {
    return PARTITION_CLASS.get(this);
  }

  /**
   * Does the job have a {@link VertexInputFormat}?
   *
   * @return True iff a {@link VertexInputFormat} has been specified.
   */
  public boolean hasVertexInputFormat() {
    return VERTEX_INPUT_FORMAT_CLASS.get(this) != null;
  }

  /**
   * Set the vertex input format class (required)
   *
   * @param vertexInputFormatClass Determines how graph is input
   */
  public void setVertexInputFormatClass(
      Class<? extends VertexInputFormat> vertexInputFormatClass) {
    VERTEX_INPUT_FORMAT_CLASS.set(this, vertexInputFormatClass);
  }

  /**
   * Does the job have a {@link EdgeInputFormat}?
   *
   * @return True iff a {@link EdgeInputFormat} has been specified.
   */
  public boolean hasEdgeInputFormat() {
    return EDGE_INPUT_FORMAT_CLASS.get(this) != null;
  }

  /**
   * Set the edge input format class (required)
   *
   * @param edgeInputFormatClass Determines how graph is input
   */
  public void setEdgeInputFormatClass(
      Class<? extends EdgeInputFormat> edgeInputFormatClass) {
    EDGE_INPUT_FORMAT_CLASS.set(this, edgeInputFormatClass);
  }

  /**
   * Set the mapping input format class (optional)
   *
   * @param mappingInputFormatClass Determines how mappings are input
   */
  public void setMappingInputFormatClass(
    Class<? extends MappingInputFormat> mappingInputFormatClass) {
    MAPPING_INPUT_FORMAT_CLASS.set(this, mappingInputFormatClass);
  }

  /**
   * Set the master class (optional)
   *
   * @param masterComputeClass Runs master computation
   */
  public final void setMasterComputeClass(
      Class<? extends MasterCompute> masterComputeClass) {
    MASTER_COMPUTE_CLASS.set(this, masterComputeClass);
  }

  /**
   * Add a MasterObserver class (optional)
   *
   * @param masterObserverClass MasterObserver class to add.
   */
  public final void addMasterObserverClass(
      Class<? extends MasterObserver> masterObserverClass) {
    MASTER_OBSERVER_CLASSES.add(this, masterObserverClass);
  }

  /**
   * Add a WorkerObserver class (optional)
   *
   * @param workerObserverClass WorkerObserver class to add.
   */
  public final void addWorkerObserverClass(
      Class<? extends WorkerObserver> workerObserverClass) {
    WORKER_OBSERVER_CLASSES.add(this, workerObserverClass);
  }

  /**
   * Get job observer class
   *
   * @return GiraphJobObserver class set.
   */
  public Class<? extends GiraphJobObserver> getJobObserverClass() {
    return JOB_OBSERVER_CLASS.get(this);
  }

  /**
   * Set job observer class
   *
   * @param klass GiraphJobObserver class to set.
   */
  public void setJobObserverClass(Class<? extends GiraphJobObserver> klass) {
    JOB_OBSERVER_CLASS.set(this, klass);
  }

  /**
   * Get job retry checker class
   *
   * @return GiraphJobRetryChecker class set.
   */
  public Class<? extends GiraphJobRetryChecker> getJobRetryCheckerClass() {
    return JOB_RETRY_CHECKER_CLASS.get(this);
  }

  /**
   * Set job retry checker class
   *
   * @param klass GiraphJobRetryChecker class to set.
   */
  public void setJobRetryCheckerClass(
      Class<? extends GiraphJobRetryChecker> klass) {
    JOB_RETRY_CHECKER_CLASS.set(this, klass);
  }

  /**
   * Check whether to enable jmap dumping thread.
   *
   * @return true if jmap dumper is enabled.
   */
  public boolean isJMapHistogramDumpEnabled() {
    return JMAP_ENABLE.get(this);
  }

  /**
   * Check whether to enable heap memory supervisor thread
   *
   * @return true if jmap dumper is reactively enabled
   */
  public boolean isReactiveJmapHistogramDumpEnabled() {
    return REACTIVE_JMAP_ENABLE.get(this);
  }

  /**
   * Set mapping from a key name to a list of classes.
   *
   * @param name String key name to use.
   * @param xface interface of the classes being set.
   * @param klasses Classes to set.
   */
  public final void setClasses(String name, Class<?> xface,
                               Class<?> ... klasses) {
    String[] klassNames = new String[klasses.length];
    for (int i = 0; i < klasses.length; ++i) {
      Class<?> klass = klasses[i];
      if (!xface.isAssignableFrom(klass)) {
        throw new RuntimeException(klass + " does not implement " +
            xface.getName());
      }
      klassNames[i] = klasses[i].getName();
    }
    setStrings(name, klassNames);
  }

  /**
   * Does the job have a {@link VertexOutputFormat}?
   *
   * @return True iff a {@link VertexOutputFormat} has been specified.
   */
  public boolean hasVertexOutputFormat() {
    return VERTEX_OUTPUT_FORMAT_CLASS.get(this) != null;
  }

  /**
   * Set the vertex output format class (optional)
   *
   * @param vertexOutputFormatClass Determines how graph is output
   */
  public final void setVertexOutputFormatClass(
      Class<? extends VertexOutputFormat> vertexOutputFormatClass) {
    VERTEX_OUTPUT_FORMAT_CLASS.set(this, vertexOutputFormatClass);
  }


  /**
   * Does the job have a {@link EdgeOutputFormat} subdir?
   *
   * @return True iff a {@link EdgeOutputFormat} subdir has been specified.
   */
  public boolean hasVertexOutputFormatSubdir() {
    return !VERTEX_OUTPUT_FORMAT_SUBDIR.get(this).isEmpty();
  }

  /**
   * Set the vertex output format path
   *
   * @param path path where the verteces will be written
   */
  public final void setVertexOutputFormatSubdir(String path) {
    VERTEX_OUTPUT_FORMAT_SUBDIR.set(this, path);
  }

  /**
   * Check if output should be done during computation
   *
   * @return True iff output should be done during computation
   */
  public final boolean doOutputDuringComputation() {
    return DO_OUTPUT_DURING_COMPUTATION.get(this);
  }

  /**
   * Set whether or not we should do output during computation
   *
   * @param doOutputDuringComputation True iff we want output to happen
   *                                  during computation
   */
  public final void setDoOutputDuringComputation(
      boolean doOutputDuringComputation) {
    DO_OUTPUT_DURING_COMPUTATION.set(this, doOutputDuringComputation);
  }

  /**
   * Check if VertexOutputFormat is thread-safe
   *
   * @return True iff VertexOutputFormat is thread-safe
   */
  public final boolean vertexOutputFormatThreadSafe() {
    return VERTEX_OUTPUT_FORMAT_THREAD_SAFE.get(this);
  }

  /**
   * Set whether or not selected VertexOutputFormat is thread-safe
   *
   * @param vertexOutputFormatThreadSafe True iff selected VertexOutputFormat
   *                                     is thread-safe
   */
  public final void setVertexOutputFormatThreadSafe(
      boolean vertexOutputFormatThreadSafe) {
    VERTEX_OUTPUT_FORMAT_THREAD_SAFE.set(this, vertexOutputFormatThreadSafe);
  }

  /**
   * Does the job have a {@link EdgeOutputFormat}?
   *
   * @return True iff a {@link EdgeOutputFormat} has been specified.
   */
  public boolean hasEdgeOutputFormat() {
    return EDGE_OUTPUT_FORMAT_CLASS.get(this) != null;
  }

  /**
   * Set the edge output format class (optional)
   *
   * @param edgeOutputFormatClass Determines how graph is output
   */
  public final void setEdgeOutputFormatClass(
      Class<? extends EdgeOutputFormat> edgeOutputFormatClass) {
    EDGE_OUTPUT_FORMAT_CLASS.set(this, edgeOutputFormatClass);
  }

  /**
   * Does the job have a {@link EdgeOutputFormat} subdir?
   *
   * @return True iff a {@link EdgeOutputFormat} subdir has been specified.
   */
  public boolean hasEdgeOutputFormatSubdir() {
    return !EDGE_OUTPUT_FORMAT_SUBDIR.get(this).isEmpty();
  }

  /**
   * Set the edge output format path
   *
   * @param path path where the edges will be written
   */
  public final void setEdgeOutputFormatSubdir(String path) {
    EDGE_OUTPUT_FORMAT_SUBDIR.set(this, path);
  }

  /**
   * Get the number of threads to use for writing output in the end of the
   * application. If output format is not thread safe, returns 1.
   *
   * @return Number of output threads
   */
  public final int getNumOutputThreads() {
    if (!vertexOutputFormatThreadSafe()) {
      return 1;
    } else {
      return NUM_OUTPUT_THREADS.get(this);
    }
  }

  /**
   * Set the number of threads to use for writing output in the end of the
   * application. Will be used only if {#vertexOutputFormatThreadSafe} is true.
   *
   * @param numOutputThreads Number of output threads
   */
  public void setNumOutputThreads(int numOutputThreads) {
    NUM_OUTPUT_THREADS.set(this, numOutputThreads);
  }

  /**
   * Set the message combiner class (optional)
   *
   * @param messageCombinerClass Determines how vertex messages are combined
   */
  public void setMessageCombinerClass(
      Class<? extends MessageCombiner> messageCombinerClass) {
    MESSAGE_COMBINER_CLASS.set(this, messageCombinerClass);
  }

  /**
   * Set the graph partitioner class (optional)
   *
   * @param graphPartitionerFactoryClass Determines how the graph is partitioned
   */
  public final void setGraphPartitionerFactoryClass(
      Class<? extends GraphPartitionerFactory> graphPartitionerFactoryClass) {
    GRAPH_PARTITIONER_FACTORY_CLASS.set(this, graphPartitionerFactoryClass);
  }

  /**
   * Set the vertex resolver class (optional)
   *
   * @param vertexResolverClass Determines how vertex mutations are resolved
   */
  public final void setVertexResolverClass(
      Class<? extends VertexResolver> vertexResolverClass) {
    VERTEX_RESOLVER_CLASS.set(this, vertexResolverClass);
  }

  /**
   * Whether to create a vertex that doesn't exist when it receives messages.
   * This only affects DefaultVertexResolver.
   *
   * @return true if we should create non existent vertices that get messages.
   */
  public final boolean getResolverCreateVertexOnMessages() {
    return RESOLVER_CREATE_VERTEX_ON_MSGS.get(this);
  }

  /**
   * Set whether to create non existent vertices when they receive messages.
   *
   * @param v true if we should create vertices when they get messages.
   */
  public final void setResolverCreateVertexOnMessages(boolean v) {
    RESOLVER_CREATE_VERTEX_ON_MSGS.set(this, v);
  }

  /**
   * Set the vertex value combiner class (optional)
   *
   * @param vertexValueCombinerClass Determines how vertices are combined
   */
  public final void setVertexValueCombinerClass(
      Class<? extends VertexValueCombiner> vertexValueCombinerClass) {
    VERTEX_VALUE_COMBINER_CLASS.set(this, vertexValueCombinerClass);
  }

  /**
   * Set the worker context class (optional)
   *
   * @param workerContextClass Determines what code is executed on a each
   *        worker before and after each superstep and computation
   */
  public final void setWorkerContextClass(
      Class<? extends WorkerContext> workerContextClass) {
    WORKER_CONTEXT_CLASS.set(this, workerContextClass);
  }

  /**
   * Set the aggregator writer class (optional)
   *
   * @param aggregatorWriterClass Determines how the aggregators are
   *        written to file at the end of the job
   */
  public final void setAggregatorWriterClass(
      Class<? extends AggregatorWriter> aggregatorWriterClass) {
    AGGREGATOR_WRITER_CLASS.set(this, aggregatorWriterClass);
  }

  /**
   * Set the partition class (optional)
   *
   * @param partitionClass Determines the why partitions are stored
   */
  public final void setPartitionClass(
      Class<? extends Partition> partitionClass) {
    PARTITION_CLASS.set(this, partitionClass);
  }

  /**
   * Set worker configuration for determining what is required for
   * a superstep.
   *
   * @param minWorkers Minimum workers to do a superstep
   * @param maxWorkers Maximum workers to do a superstep
   *        (max map tasks in job)
   * @param minPercentResponded 0 - 100 % of the workers required to
   *        have responded before continuing the superstep
   */
  public final void setWorkerConfiguration(int minWorkers,
                                           int maxWorkers,
                                           float minPercentResponded) {
    setInt(MIN_WORKERS, minWorkers);
    setInt(MAX_WORKERS, maxWorkers);
    MIN_PERCENT_RESPONDED.set(this, minPercentResponded);
  }

  public final int getMinWorkers() {
    return getInt(MIN_WORKERS, -1);
  }

  public final int getMaxWorkers() {
    return getInt(MAX_WORKERS, -1);
  }

  public final float getMinPercentResponded() {
    return MIN_PERCENT_RESPONDED.get(this);
  }

  /**
   * Utilize an existing ZooKeeper service.  If this is not set, ZooKeeper
   * will be dynamically started by Giraph for this job.
   *
   * @param serverList Comma separated list of servers and ports
   *        (i.e. zk1:2221,zk2:2221)
   */
  public final void setZooKeeperConfiguration(String serverList) {
    ZOOKEEPER_LIST.set(this, serverList);
  }

  /**
   * Getter for SPLIT_MASTER_WORKER flag.
   *
   * @return boolean flag value.
   */
  public final boolean getSplitMasterWorker() {
    return SPLIT_MASTER_WORKER.get(this);
  }

  /**
   * Get array of MasterObserver classes set in the configuration.
   *
   * @return array of MasterObserver classes.
   */
  public Class<? extends MasterObserver>[] getMasterObserverClasses() {
    return MASTER_OBSERVER_CLASSES.getArray(this);
  }

  /**
   * Get array of WorkerObserver classes set in configuration.
   *
   * @return array of WorkerObserver classes.
   */
  public Class<? extends WorkerObserver>[] getWorkerObserverClasses() {
    return WORKER_OBSERVER_CLASSES.getArray(this);
  }

  /**
   * Whether to track, print, and aggregate metrics.
   *
   * @return true if metrics are enabled, false otherwise (default)
   */
  public boolean metricsEnabled() {
    return METRICS_ENABLE.isTrue(this);
  }

  /**
   * Get the task partition
   *
   * @return The task partition or -1 if not set
   */
  public int getTaskPartition() {
    return getInt("mapred.task.partition", -1);
  }

  /**
   * Is this a "pure YARN" Giraph job, or is a MapReduce layer (v1 or v2)
   * actually managing our cluster nodes, i.e. each task is a Mapper.
   *
   * @return TRUE if this is a pure YARN job.
   */
  public boolean isPureYarnJob() {
    return IS_PURE_YARN_JOB.get(this);
  }

  /**
   * Jars required in "Pure YARN" jobs (names only, no paths) should
   * be listed here in full, including Giraph framework jar(s).
   *
   * @return the comma-separated list of jar names for export to cluster.
   */
  public String getYarnLibJars() {
    return GIRAPH_YARN_LIBJARS.get(this);
  }

  /**
   * Populate jar list for Pure YARN jobs.
   *
   * @param jarList a comma-separated list of jar names
   */
  public void setYarnLibJars(String jarList) {
    GIRAPH_YARN_LIBJARS.set(this, jarList);
  }

  /**
   * Get heap size (in MB) for each task in our Giraph job run,
   * assuming this job will run on the "pure YARN" profile.
   *
   * @return the heap size for all tasks, in MB
   */
  public int getYarnTaskHeapMb() {
    return GIRAPH_YARN_TASK_HEAP_MB.get(this);
  }

  /**
   * Set heap size for Giraph tasks in our job run, assuming
   * the job will run on the "pure YARN" profile.
   *
   * @param heapMb the heap size for all tasks
   */
  public void setYarnTaskHeapMb(int heapMb) {
    GIRAPH_YARN_TASK_HEAP_MB.set(this, heapMb);
  }

  /**
   * Get the ZooKeeper list.
   *
   * @return ZooKeeper list of strings, comma separated or null if none set.
   */
  public String getZookeeperList() {
    return ZOOKEEPER_LIST.get(this);
  }

  /**
   * Set the ZooKeeper list to the provided list. This method is used when the
   * ZooKeeper is started internally and will set the zkIsExternal option to
   * false as well.
   *
   * @param zkList list of strings, comma separated of zookeeper servers
   */
  public void setZookeeperList(String zkList) {
    ZOOKEEPER_LIST.set(this, zkList);
    ZOOKEEPER_IS_EXTERNAL.set(this, false);
  }

  /**
   * Was ZooKeeper provided externally?
   *
   * @return true iff was zookeeper is external
   */
  public boolean isZookeeperExternal() {
    return ZOOKEEPER_IS_EXTERNAL.get(this);
  }

  public String getLocalLevel() {
    return LOG_LEVEL.get(this);
  }

  /**
   * Use the log thread layout option?
   *
   * @return True if use the log thread layout option, false otherwise
   */
  public boolean useLogThreadLayout() {
    return LOG_THREAD_LAYOUT.get(this);
  }

  /**
   * is this job run a local test?
   *
   * @return the test status as recorded in the Configuration
   */
  public boolean getLocalTestMode() {
    return LOCAL_TEST_MODE.get(this);
  }

  /**
   * Flag this job as a local test run.
   *
   * @param flag the test status for this job
   */
  public void setLocalTestMode(boolean flag) {
    LOCAL_TEST_MODE.set(this, flag);
  }

  /**
   * The number of server tasks in our ZK quorum for
   * this job run.
   *
   * @return the number of ZK servers in the quorum
   */
  public int getZooKeeperServerCount() {
    return ZOOKEEPER_SERVER_COUNT.get(this);
  }

  public int getZooKeeperSessionTimeout() {
    return ZOOKEEPER_SESSION_TIMEOUT.get(this);
  }

  public int getZookeeperOpsMaxAttempts() {
    return ZOOKEEPER_OPS_MAX_ATTEMPTS.get(this);
  }

  public int getZookeeperOpsRetryWaitMsecs() {
    return ZOOKEEPER_OPS_RETRY_WAIT_MSECS.get(this);
  }

  public boolean getNettyServerUseExecutionHandler() {
    return NETTY_SERVER_USE_EXECUTION_HANDLER.get(this);
  }

  public int getNettyServerThreads() {
    return NETTY_SERVER_THREADS.get(this);
  }

  public int getNettyServerExecutionThreads() {
    return NETTY_SERVER_EXECUTION_THREADS.get(this);
  }

  /**
   * Get the netty server execution concurrency.  This depends on whether the
   * netty server execution handler exists.
   *
   * @return Server concurrency
   */
  public int getNettyServerExecutionConcurrency() {
    if (getNettyServerUseExecutionHandler()) {
      return getNettyServerExecutionThreads();
    } else {
      return getNettyServerThreads();
    }
  }

  /**
   * Used by netty client and server to create ByteBufAllocator
   *
   * @return ByteBufAllocator
   */
  public ByteBufAllocator getNettyAllocator() {
    if (nettyBufferAllocator == null) {
      if (NETTY_USE_POOLED_ALLOCATOR.get(this)) { // Use pooled allocator
        nettyBufferAllocator = new PooledByteBufAllocator(
          NETTY_USE_DIRECT_MEMORY.get(this));
      } else { // Use un-pooled allocator
        // Note: Current default settings create un-pooled heap allocator
        nettyBufferAllocator = new UnpooledByteBufAllocator(
            NETTY_USE_DIRECT_MEMORY.get(this));
      }
    }
    return nettyBufferAllocator;
  }

  public int getZookeeperConnectionAttempts() {
    return ZOOKEEPER_CONNECTION_ATTEMPTS.get(this);
  }

  public int getZooKeeperMinSessionTimeout() {
    return ZOOKEEPER_MIN_SESSION_TIMEOUT.get(this);
  }

  public int getZooKeeperMaxSessionTimeout() {
    return ZOOKEEPER_MAX_SESSION_TIMEOUT.get(this);
  }

  public boolean getZooKeeperForceSync() {
    return ZOOKEEPER_FORCE_SYNC.get(this);
  }

  public boolean getZooKeeperSkipAcl() {
    return ZOOKEEPER_SKIP_ACL.get(this);
  }

  /**
   * Get the number of map tasks in this job
   *
   * @return Number of map tasks in this job
   */
  public int getMapTasks() {
    int mapTasks = getInt("mapred.map.tasks", -1);
    if (mapTasks == -1) {
      throw new IllegalStateException("getMapTasks: Failed to get the map " +
          "tasks!");
    }
    return mapTasks;
  }

  /**
   * Use authentication? (if supported)
   *
   * @return True if should authenticate, false otherwise
   */
  public boolean authenticate() {
    return AUTHENTICATE.get(this);
  }

  /**
   * Set the number of compute threads
   *
   * @param numComputeThreads Number of compute threads to use
   */
  public void setNumComputeThreads(int numComputeThreads) {
    NUM_COMPUTE_THREADS.set(this, numComputeThreads);
  }

  public int getNumComputeThreads() {
    return NUM_COMPUTE_THREADS.get(this);
  }

  /**
   * Set the number of input split threads
   *
   * @param numInputSplitsThreads Number of input split threads to use
   */
  public void setNumInputSplitsThreads(int numInputSplitsThreads) {
    NUM_INPUT_THREADS.set(this, numInputSplitsThreads);
  }

  public int getNumInputSplitsThreads() {
    return NUM_INPUT_THREADS.get(this);
  }

  public long getInputSplitMaxVertices() {
    return INPUT_SPLIT_MAX_VERTICES.get(this);
  }

  public long getInputSplitMaxEdges() {
    return INPUT_SPLIT_MAX_EDGES.get(this);
  }

  /**
   * Set whether to use unsafe serialization
   *
   * @param useUnsafeSerialization If true, use unsafe serialization
   */
  public void useUnsafeSerialization(boolean useUnsafeSerialization) {
    USE_UNSAFE_SERIALIZATION.set(this, useUnsafeSerialization);
  }

  /**
   * Use message size encoding?  This feature may help with complex message
   * objects.
   *
   * @return Whether to use message size encoding
   */
  public boolean useMessageSizeEncoding() {
    return USE_MESSAGE_SIZE_ENCODING.get(this);
  }

  /**
   * Set the checkpoint frequeuncy of how many supersteps to wait before
   * checkpointing
   *
   * @param checkpointFrequency How often to checkpoint (0 means never)
   */
  public void setCheckpointFrequency(int checkpointFrequency) {
    CHECKPOINT_FREQUENCY.set(this, checkpointFrequency);
  }

  /**
   * Get the checkpoint frequeuncy of how many supersteps to wait
   * before checkpointing
   *
   * @return Checkpoint frequency (0 means never)
   */
  public int getCheckpointFrequency() {
    return CHECKPOINT_FREQUENCY.get(this);
  }

  /**
   * Check if checkpointing is used
   *
   * @return True iff checkpointing is used
   */
  public boolean useCheckpointing() {
    return getCheckpointFrequency() != 0;
  }

  /**
   * Set runtime checkpoint support checker.
   * The instance of this class will have to decide whether
   * checkpointing is allowed on current superstep.
   *
   * @param clazz checkpoint supported checker class
   */
  public void setCheckpointSupportedChecker(
      Class<? extends CheckpointSupportedChecker> clazz) {
    GiraphConstants.CHECKPOINT_SUPPORTED_CHECKER.set(this, clazz);
  }

  /**
   * Set the max task attempts
   *
   * @param maxTaskAttempts Max task attempts to use
   */
  public void setMaxTaskAttempts(int maxTaskAttempts) {
    MAX_TASK_ATTEMPTS.set(this, maxTaskAttempts);
  }

  /**
   * Get the max task attempts
   *
   * @return Max task attempts or -1, if not set
   */
  public int getMaxTaskAttempts() {
    return MAX_TASK_ATTEMPTS.get(this);
  }

  /**
   * Get the number of milliseconds to wait for an event before continuing on
   *
   * @return Number of milliseconds to wait for an event before continuing on
   */
  public int getEventWaitMsecs() {
    return EVENT_WAIT_MSECS.get(this);
  }

  /**
   * Set the number of milliseconds to wait for an event before continuing on
   *
   * @param eventWaitMsecs Number of milliseconds to wait for an event before
   *                       continuing on
   */
  public void setEventWaitMsecs(int eventWaitMsecs) {
    EVENT_WAIT_MSECS.set(this, eventWaitMsecs);
  }

  /**
   * Get the maximum milliseconds to wait before giving up trying to get the
   * minimum number of workers before a superstep.
   *
   * @return Maximum milliseconds to wait before giving up trying to get the
   *         minimum number of workers before a superstep
   */
  public int getMaxMasterSuperstepWaitMsecs() {
    return MAX_MASTER_SUPERSTEP_WAIT_MSECS.get(this);
  }

  /**
   * Set the maximum milliseconds to wait before giving up trying to get the
   * minimum number of workers before a superstep.
   *
   * @param maxMasterSuperstepWaitMsecs Maximum milliseconds to wait before
   *                                    giving up trying to get the minimum
   *                                    number of workers before a superstep
   */
  public void setMaxMasterSuperstepWaitMsecs(int maxMasterSuperstepWaitMsecs) {
    MAX_MASTER_SUPERSTEP_WAIT_MSECS.set(this, maxMasterSuperstepWaitMsecs);
  }

  /**
   * Check environment for Hadoop security token location in case we are
   * executing the Giraph job on a MRv1 Hadoop cluster.
   */
  public void configureHadoopSecurity() {
    String hadoopTokenFilePath = System.getenv("HADOOP_TOKEN_FILE_LOCATION");
    if (hadoopTokenFilePath != null) {
      set("mapreduce.job.credentials.binary", hadoopTokenFilePath);
    }
  }

  /**
   * Check if we want to prioritize input splits which reside on the host.
   *
   * @return True iff we want to use input split locality
   */
  public boolean useInputSplitLocality() {
    return USE_INPUT_SPLIT_LOCALITY.get(this);
  }

  /**
   * Get the local hostname on the given interface.
   *
   * @return The local hostname
   * @throws UnknownHostException
   */
  public String getLocalHostname() throws UnknownHostException {
    return DNS.getDefaultHost(
        GiraphConstants.DNS_INTERFACE.get(this),
        GiraphConstants.DNS_NAMESERVER.get(this)).toLowerCase();
  }

  /**
   * Set the maximum number of supersteps of this application.  After this
   * many supersteps are executed, the application will shutdown.
   *
   * @param maxNumberOfSupersteps Maximum number of supersteps
   */
  public void setMaxNumberOfSupersteps(int maxNumberOfSupersteps) {
    MAX_NUMBER_OF_SUPERSTEPS.set(this, maxNumberOfSupersteps);
  }

  /**
   * Get the maximum number of supersteps of this application.  After this
   * many supersteps are executed, the application will shutdown.
   *
   * @return Maximum number of supersteps
   */
  public int getMaxNumberOfSupersteps() {
    return MAX_NUMBER_OF_SUPERSTEPS.get(this);
  }

  /**
   * Whether the application with change or not the graph topology.
   *
   * @return true if the graph is static, false otherwise.
   */
  public boolean isStaticGraph() {
    return STATIC_GRAPH.isTrue(this);
  }

  /**
   * Get the output directory to write YourKit snapshots to
   *
   * @param context Map context
   * @return output directory
   */
  public String getYourKitOutputDir(Mapper.Context context) {
    final String cacheKey = "giraph.yourkit.outputDirCached";
    String outputDir = get(cacheKey);
    if (outputDir == null) {
      outputDir = getStringVars(YOURKIT_OUTPUT_DIR, YOURKIT_OUTPUT_DIR_DEFAULT,
          context);
      set(cacheKey, outputDir);
    }
    return outputDir;
  }

  /**
   * Get string, replacing variables in the output.
   *
   * %JOB_ID% => job id
   * %TASK_ID% => task id
   * %USER% => owning user name
   *
   * @param key name of key to lookup
   * @param context mapper context
   * @return value for key, with variables expanded
   */
  public String getStringVars(String key, Mapper.Context context) {
    return getStringVars(key, null, context);
  }

  /**
   * Get string, replacing variables in the output.
   *
   * %JOB_ID% => job id
   * %TASK_ID% => task id
   * %USER% => owning user name
   *
   * @param key name of key to lookup
   * @param defaultValue value to return if no mapping exists. This can also
   *                     have variables, which will be substituted.
   * @param context mapper context
   * @return value for key, with variables expanded
   */
  public String getStringVars(String key, String defaultValue,
                              Mapper.Context context) {
    String value = get(key);
    if (value == null) {
      if (defaultValue == null) {
        return null;
      }
      value = defaultValue;
    }
    value = value.replace("%JOB_ID%", context.getJobID().toString());
    value = value.replace("%TASK_ID%", context.getTaskAttemptID().toString());
    value = value.replace("%USER%", get("user.name", "unknown_user"));
    return value;
  }

  /**
   * Get option whether to create a source vertex present only in edge input
   *
   * @return CREATE_EDGE_SOURCE_VERTICES option
   */
  public boolean getCreateSourceVertex() {
    return CREATE_EDGE_SOURCE_VERTICES.get(this);
  }

  /**
   * set option whether to create a source vertex present only in edge input
   * @param createVertex create source vertex option
   */
  public void setCreateSourceVertex(boolean createVertex) {
    CREATE_EDGE_SOURCE_VERTICES.set(this, createVertex);
  }

  /**
   * Get the maximum timeout (in milliseconds) for waiting for all tasks
   * to complete after the job is done.
   *
   * @return Wait task done timeout in milliseconds.
   */
  public int getWaitTaskDoneTimeoutMs() {
    return WAIT_TASK_DONE_TIMEOUT_MS.get(this);
  }

  /**
   * Set the maximum timeout (in milliseconds) for waiting for all tasks
   * to complete after the job is done.
   *
   * @param ms Milliseconds to set
   */
  public void setWaitTaskDoneTimeoutMs(int ms) {
    WAIT_TASK_DONE_TIMEOUT_MS.set(this, ms);
  }

  /**
   * Check whether to track job progress on client or not
   *
   * @return True if job progress should be tracked on client
   */
  public boolean trackJobProgressOnClient() {
    return TRACK_JOB_PROGRESS_ON_CLIENT.get(this);
  }

  /**
   * @return Number of retries when creating an HDFS file before failing.
   */
  public int getHdfsFileCreationRetries() {
    return HDFS_FILE_CREATION_RETRIES.get(this);
  }

  /**
   * @return Milliseconds to wait before retrying an HDFS file creation
   *         operation.
   */
  public int getHdfsFileCreationRetryWaitMs() {
    return HDFS_FILE_CREATION_RETRY_WAIT_MS.get(this);
  }
}


File: giraph-core/src/main/java/org/apache/giraph/conf/GiraphConstants.java
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
package org.apache.giraph.conf;

import static java.util.concurrent.TimeUnit.MINUTES;
import static java.util.concurrent.TimeUnit.SECONDS;

import org.apache.giraph.aggregators.AggregatorWriter;
import org.apache.giraph.aggregators.TextAggregatorWriter;
import org.apache.giraph.bsp.BspOutputFormat;
import org.apache.giraph.bsp.checkpoints.CheckpointSupportedChecker;
import org.apache.giraph.bsp.checkpoints.DefaultCheckpointSupportedChecker;
import org.apache.giraph.combiner.MessageCombiner;
import org.apache.giraph.comm.messages.InMemoryMessageStoreFactory;
import org.apache.giraph.comm.messages.MessageEncodeAndStoreType;
import org.apache.giraph.comm.messages.MessageStoreFactory;
import org.apache.giraph.edge.ByteArrayEdges;
import org.apache.giraph.edge.EdgeStoreFactory;
import org.apache.giraph.edge.InMemoryEdgeStoreFactory;
import org.apache.giraph.edge.OutEdges;
import org.apache.giraph.factories.ComputationFactory;
import org.apache.giraph.factories.DefaultComputationFactory;
import org.apache.giraph.factories.DefaultEdgeValueFactory;
import org.apache.giraph.factories.DefaultMessageValueFactory;
import org.apache.giraph.factories.DefaultVertexIdFactory;
import org.apache.giraph.factories.DefaultVertexValueFactory;
import org.apache.giraph.factories.EdgeValueFactory;
import org.apache.giraph.factories.MessageValueFactory;
import org.apache.giraph.factories.VertexIdFactory;
import org.apache.giraph.factories.VertexValueFactory;
import org.apache.giraph.graph.Computation;
import org.apache.giraph.graph.DefaultVertex;
import org.apache.giraph.graph.DefaultVertexResolver;
import org.apache.giraph.graph.DefaultVertexValueCombiner;
import org.apache.giraph.graph.Language;
import org.apache.giraph.graph.Vertex;
import org.apache.giraph.graph.VertexResolver;
import org.apache.giraph.graph.VertexValueCombiner;
import org.apache.giraph.io.EdgeInputFormat;
import org.apache.giraph.io.EdgeOutputFormat;
import org.apache.giraph.io.MappingInputFormat;
import org.apache.giraph.io.VertexInputFormat;
import org.apache.giraph.io.VertexOutputFormat;
import org.apache.giraph.io.filters.DefaultEdgeInputFilter;
import org.apache.giraph.io.filters.DefaultVertexInputFilter;
import org.apache.giraph.io.filters.EdgeInputFilter;
import org.apache.giraph.io.filters.VertexInputFilter;
import org.apache.giraph.job.DefaultGiraphJobRetryChecker;
import org.apache.giraph.job.DefaultJobObserver;
import org.apache.giraph.job.GiraphJobObserver;
import org.apache.giraph.job.GiraphJobRetryChecker;
import org.apache.giraph.job.HaltApplicationUtils;
import org.apache.giraph.mapping.MappingStore;
import org.apache.giraph.mapping.MappingStoreOps;
import org.apache.giraph.mapping.translate.TranslateEdge;
import org.apache.giraph.master.DefaultMasterCompute;
import org.apache.giraph.master.MasterCompute;
import org.apache.giraph.master.MasterObserver;
import org.apache.giraph.partition.GraphPartitionerFactory;
import org.apache.giraph.partition.HashPartitionerFactory;
import org.apache.giraph.partition.Partition;
import org.apache.giraph.partition.SimplePartition;
import org.apache.giraph.worker.DefaultWorkerContext;
import org.apache.giraph.worker.WorkerContext;
import org.apache.giraph.worker.WorkerObserver;
import org.apache.hadoop.io.Writable;
import org.apache.hadoop.io.WritableComparable;
import org.apache.hadoop.mapreduce.OutputFormat;

/**
 * Constants used all over Giraph for configuration.
 */
// CHECKSTYLE: stop InterfaceIsTypeCheck
public interface GiraphConstants {
  /** 1KB in bytes */
  int ONE_KB = 1024;

  /** Mapping related information */
  ClassConfOption<MappingStore> MAPPING_STORE_CLASS =
      ClassConfOption.create("giraph.mappingStoreClass", null,
          MappingStore.class, "MappingStore Class");

  /** Class to use for performing read operations on mapping store */
  ClassConfOption<MappingStoreOps> MAPPING_STORE_OPS_CLASS =
      ClassConfOption.create("giraph.mappingStoreOpsClass", null,
          MappingStoreOps.class, "MappingStoreOps class");

  /** Upper value of LongByteMappingStore */
  IntConfOption LB_MAPPINGSTORE_UPPER =
      new IntConfOption("giraph.lbMappingStoreUpper", -1,
          "'upper' value used by lbmappingstore");
  /** Lower value of LongByteMappingStore */
  IntConfOption LB_MAPPINGSTORE_LOWER =
      new IntConfOption("giraph.lbMappingStoreLower", -1,
          "'lower' value used by lbMappingstore");
  /** Class used to conduct expensive edge translation during vertex input */
  ClassConfOption EDGE_TRANSLATION_CLASS =
      ClassConfOption.create("giraph.edgeTranslationClass", null,
          TranslateEdge.class, "Class used to conduct expensive edge " +
              "translation during vertex input phase");

  /** Computation class - required */
  ClassConfOption<Computation> COMPUTATION_CLASS =
      ClassConfOption.create("giraph.computationClass", null,
          Computation.class, "Computation class - required");
  /** Computation factory class - optional */
  ClassConfOption<ComputationFactory> COMPUTATION_FACTORY_CLASS =
      ClassConfOption.create("giraph.computation.factory.class",
          DefaultComputationFactory.class, ComputationFactory.class,
          "Computation factory class - optional");

  /** TypesHolder, used if Computation not set - optional */
  ClassConfOption<TypesHolder> TYPES_HOLDER_CLASS =
      ClassConfOption.create("giraph.typesHolder", null,
          TypesHolder.class,
          "TypesHolder, used if Computation not set - optional");

  /** Edge Store Factory */
  ClassConfOption<EdgeStoreFactory> EDGE_STORE_FACTORY_CLASS =
      ClassConfOption.create("giraph.edgeStoreFactoryClass",
          InMemoryEdgeStoreFactory.class,
          EdgeStoreFactory.class,
          "Edge Store Factory class to use for creating edgeStore");

  /** Message Store Factory */
  ClassConfOption<MessageStoreFactory> MESSAGE_STORE_FACTORY_CLASS =
      ClassConfOption.create("giraph.messageStoreFactoryClass",
          InMemoryMessageStoreFactory.class,
          MessageStoreFactory.class,
          "Message Store Factory Class that is to be used");

  /** Language user's graph types are implemented in */
  PerGraphTypeEnumConfOption<Language> GRAPH_TYPE_LANGUAGES =
      PerGraphTypeEnumConfOption.create("giraph.types.language",
          Language.class, Language.JAVA,
          "Language user graph types (IVEMM) are implemented in");

  /** Whether user graph types need wrappers */
  PerGraphTypeBooleanConfOption GRAPH_TYPES_NEEDS_WRAPPERS =
      new PerGraphTypeBooleanConfOption("giraph.jython.type.wrappers",
          false, "Whether user graph types (IVEMM) need Jython wrappers");

  /** Vertex id factory class - optional */
  ClassConfOption<VertexIdFactory> VERTEX_ID_FACTORY_CLASS =
      ClassConfOption.create("giraph.vertexIdFactoryClass",
          DefaultVertexIdFactory.class, VertexIdFactory.class,
          "Vertex ID factory class - optional");
  /** Vertex value factory class - optional */
  ClassConfOption<VertexValueFactory> VERTEX_VALUE_FACTORY_CLASS =
      ClassConfOption.create("giraph.vertexValueFactoryClass",
          DefaultVertexValueFactory.class, VertexValueFactory.class,
          "Vertex value factory class - optional");
  /** Edge value factory class - optional */
  ClassConfOption<EdgeValueFactory> EDGE_VALUE_FACTORY_CLASS =
      ClassConfOption.create("giraph.edgeValueFactoryClass",
          DefaultEdgeValueFactory.class, EdgeValueFactory.class,
          "Edge value factory class - optional");
  /** Outgoing message value factory class - optional */
  ClassConfOption<MessageValueFactory>
  OUTGOING_MESSAGE_VALUE_FACTORY_CLASS =
      ClassConfOption.create("giraph.outgoingMessageValueFactoryClass",
          DefaultMessageValueFactory.class, MessageValueFactory.class,
          "Outgoing message value factory class - optional");

  /** Vertex edges class - optional */
  ClassConfOption<OutEdges> VERTEX_EDGES_CLASS =
      ClassConfOption.create("giraph.outEdgesClass", ByteArrayEdges.class,
          OutEdges.class, "Vertex edges class - optional");
  /** Vertex edges class to be used during edge input only - optional */
  ClassConfOption<OutEdges> INPUT_VERTEX_EDGES_CLASS =
      ClassConfOption.create("giraph.inputOutEdgesClass",
          ByteArrayEdges.class, OutEdges.class,
          "Vertex edges class to be used during edge input only - optional");

  /** Class for Master - optional */
  ClassConfOption<MasterCompute> MASTER_COMPUTE_CLASS =
      ClassConfOption.create("giraph.masterComputeClass",
          DefaultMasterCompute.class, MasterCompute.class,
          "Class for Master - optional");
  /** Classes for Master Observer - optional */
  ClassConfOption<MasterObserver> MASTER_OBSERVER_CLASSES =
      ClassConfOption.create("giraph.master.observers",
          null, MasterObserver.class, "Classes for Master Observer - optional");
  /** Classes for Worker Observer - optional */
  ClassConfOption<WorkerObserver> WORKER_OBSERVER_CLASSES =
      ClassConfOption.create("giraph.worker.observers", null,
          WorkerObserver.class, "Classes for Worker Observer - optional");
  /** Message combiner class - optional */
  ClassConfOption<MessageCombiner> MESSAGE_COMBINER_CLASS =
      ClassConfOption.create("giraph.messageCombinerClass", null,
          MessageCombiner.class, "Message combiner class - optional");
  /** Vertex resolver class - optional */
  ClassConfOption<VertexResolver> VERTEX_RESOLVER_CLASS =
      ClassConfOption.create("giraph.vertexResolverClass",
          DefaultVertexResolver.class, VertexResolver.class,
          "Vertex resolver class - optional");
  /** Vertex value combiner class - optional */
  ClassConfOption<VertexValueCombiner> VERTEX_VALUE_COMBINER_CLASS =
      ClassConfOption.create("giraph.vertexValueCombinerClass",
          DefaultVertexValueCombiner.class, VertexValueCombiner.class,
          "Vertex value combiner class - optional");

  /** Which language computation is implemented in */
  EnumConfOption<Language> COMPUTATION_LANGUAGE =
      EnumConfOption.create("giraph.computation.language",
          Language.class, Language.JAVA,
          "Which language computation is implemented in");

  /**
   * Option of whether to create vertexes that were not existent before but
   * received messages
   */
  BooleanConfOption RESOLVER_CREATE_VERTEX_ON_MSGS =
      new BooleanConfOption("giraph.vertex.resolver.create.on.msgs", true,
          "Option of whether to create vertexes that were not existent " +
          "before but received messages");
  /** Graph partitioner factory class - optional */
  ClassConfOption<GraphPartitionerFactory> GRAPH_PARTITIONER_FACTORY_CLASS =
      ClassConfOption.create("giraph.graphPartitionerFactoryClass",
          HashPartitionerFactory.class, GraphPartitionerFactory.class,
          "Graph partitioner factory class - optional");

  /** Observer class to watch over job status - optional */
  ClassConfOption<GiraphJobObserver> JOB_OBSERVER_CLASS =
      ClassConfOption.create("giraph.jobObserverClass",
          DefaultJobObserver.class, GiraphJobObserver.class,
          "Observer class to watch over job status - optional");

  /** Observer class to watch over job status - optional */
  ClassConfOption<GiraphJobRetryChecker> JOB_RETRY_CHECKER_CLASS =
      ClassConfOption.create("giraph.jobRetryCheckerClass",
          DefaultGiraphJobRetryChecker.class, GiraphJobRetryChecker.class,
          "Class which decides whether a failed job should be retried - " +
              "optional");

  /**
   * Maximum allowed time for job to run after getting all resources before it
   * will be killed, in milliseconds (-1 if it has no limit)
   */
  LongConfOption MAX_ALLOWED_JOB_TIME_MS =
      new LongConfOption("giraph.maxAllowedJobTimeMilliseconds", -1,
          "Maximum allowed time for job to run after getting all resources " +
              "before it will be killed, in milliseconds " +
              "(-1 if it has no limit)");

  // At least one of the input format classes is required.
  /** VertexInputFormat class */
  ClassConfOption<VertexInputFormat> VERTEX_INPUT_FORMAT_CLASS =
      ClassConfOption.create("giraph.vertexInputFormatClass", null,
          VertexInputFormat.class, "VertexInputFormat class (at least " +
          "one of the input format classes is required)");
  /** EdgeInputFormat class */
  ClassConfOption<EdgeInputFormat> EDGE_INPUT_FORMAT_CLASS =
      ClassConfOption.create("giraph.edgeInputFormatClass", null,
          EdgeInputFormat.class, "EdgeInputFormat class");
  /** MappingInputFormat class */
  ClassConfOption<MappingInputFormat> MAPPING_INPUT_FORMAT_CLASS =
      ClassConfOption.create("giraph.mappingInputFormatClass", null,
          MappingInputFormat.class, "MappingInputFormat class");

  /** EdgeInputFilter class */
  ClassConfOption<EdgeInputFilter> EDGE_INPUT_FILTER_CLASS =
      ClassConfOption.create("giraph.edgeInputFilterClass",
          DefaultEdgeInputFilter.class, EdgeInputFilter.class,
          "EdgeInputFilter class");
  /** VertexInputFilter class */
  ClassConfOption<VertexInputFilter> VERTEX_INPUT_FILTER_CLASS =
      ClassConfOption.create("giraph.vertexInputFilterClass",
          DefaultVertexInputFilter.class, VertexInputFilter.class,
          "VertexInputFilter class");
  /** Vertex class */
  ClassConfOption<Vertex> VERTEX_CLASS =
      ClassConfOption.create("giraph.vertexClass",
          DefaultVertex.class, Vertex.class,
          "Vertex class");
  /** VertexOutputFormat class */
  ClassConfOption<VertexOutputFormat> VERTEX_OUTPUT_FORMAT_CLASS =
      ClassConfOption.create("giraph.vertexOutputFormatClass", null,
          VertexOutputFormat.class, "VertexOutputFormat class");
  /** EdgeOutputFormat sub-directory */
  StrConfOption VERTEX_OUTPUT_FORMAT_SUBDIR =
    new StrConfOption("giraph.vertex.output.subdir", "",
                      "VertexOutputFormat sub-directory");
  /** EdgeOutputFormat class */
  ClassConfOption<EdgeOutputFormat> EDGE_OUTPUT_FORMAT_CLASS =
      ClassConfOption.create("giraph.edgeOutputFormatClass", null,
          EdgeOutputFormat.class, "EdgeOutputFormat class");
  /** EdgeOutputFormat sub-directory */
  StrConfOption EDGE_OUTPUT_FORMAT_SUBDIR =
    new StrConfOption("giraph.edge.output.subdir", "",
                      "EdgeOutputFormat sub-directory");

  /** GiraphTextOuputFormat Separator */
  StrConfOption GIRAPH_TEXT_OUTPUT_FORMAT_SEPARATOR =
    new StrConfOption("giraph.textoutputformat.separator", "\t",
                      "GiraphTextOuputFormat Separator");
  /** Reverse values in the output */
  BooleanConfOption GIRAPH_TEXT_OUTPUT_FORMAT_REVERSE =
      new BooleanConfOption("giraph.textoutputformat.reverse", false,
                            "Reverse values in the output");

  /**
   * If you use this option, instead of having saving vertices in the end of
   * application, saveVertex will be called right after each vertex.compute()
   * is called.
   * NOTE: This feature doesn't work well with checkpointing - if you restart
   * from a checkpoint you won't have any output from previous supersteps.
   */
  BooleanConfOption DO_OUTPUT_DURING_COMPUTATION =
      new BooleanConfOption("giraph.doOutputDuringComputation", false,
          "If you use this option, instead of having saving vertices in the " +
          "end of application, saveVertex will be called right after each " +
          "vertex.compute() is called." +
          "NOTE: This feature doesn't work well with checkpointing - if you " +
          "restart from a checkpoint you won't have any ouptut from previous " +
          "supresteps.");
  /**
   * Vertex output format thread-safe - if your VertexOutputFormat allows
   * several vertexWriters to be created and written to in parallel,
   * you should set this to true.
   */
  BooleanConfOption VERTEX_OUTPUT_FORMAT_THREAD_SAFE =
      new BooleanConfOption("giraph.vertexOutputFormatThreadSafe", false,
          "Vertex output format thread-safe - if your VertexOutputFormat " +
          "allows several vertexWriters to be created and written to in " +
          "parallel, you should set this to true.");
  /** Number of threads for writing output in the end of the application */
  IntConfOption NUM_OUTPUT_THREADS =
      new IntConfOption("giraph.numOutputThreads", 1,
          "Number of threads for writing output in the end of the application");

  /** conf key for comma-separated list of jars to export to YARN workers */
  StrConfOption GIRAPH_YARN_LIBJARS =
    new StrConfOption("giraph.yarn.libjars", "",
        "conf key for comma-separated list of jars to export to YARN workers");
  /** Name of the XML file that will export our Configuration to YARN workers */
  String GIRAPH_YARN_CONF_FILE = "giraph-conf.xml";
  /** Giraph default heap size for all tasks when running on YARN profile */
  int GIRAPH_YARN_TASK_HEAP_MB_DEFAULT = 1024;
  /** Name of Giraph property for user-configurable heap memory per worker */
  IntConfOption GIRAPH_YARN_TASK_HEAP_MB = new IntConfOption(
    "giraph.yarn.task.heap.mb", GIRAPH_YARN_TASK_HEAP_MB_DEFAULT,
    "Name of Giraph property for user-configurable heap memory per worker");
  /** Default priority level in YARN for our task containers */
  int GIRAPH_YARN_PRIORITY = 10;
  /** Is this a pure YARN job (i.e. no MapReduce layer managing Giraph tasks) */
  BooleanConfOption IS_PURE_YARN_JOB =
    new BooleanConfOption("giraph.pure.yarn.job", false,
        "Is this a pure YARN job (i.e. no MapReduce layer managing Giraph " +
        "tasks)");

  /** Vertex index class */
  ClassConfOption<WritableComparable> VERTEX_ID_CLASS =
      ClassConfOption.create("giraph.vertexIdClass", null,
          WritableComparable.class, "Vertex index class");
  /** Vertex value class */
  ClassConfOption<Writable> VERTEX_VALUE_CLASS =
      ClassConfOption.create("giraph.vertexValueClass", null, Writable.class,
          "Vertex value class");
  /** Edge value class */
  ClassConfOption<Writable> EDGE_VALUE_CLASS =
      ClassConfOption.create("giraph.edgeValueClass", null, Writable.class,
          "Edge value class");
  /** Outgoing message value class */
  ClassConfOption<Writable> OUTGOING_MESSAGE_VALUE_CLASS =
      ClassConfOption.create("giraph.outgoingMessageValueClass", null,
          Writable.class, "Outgoing message value class");
  /** Worker context class */
  ClassConfOption<WorkerContext> WORKER_CONTEXT_CLASS =
      ClassConfOption.create("giraph.workerContextClass",
          DefaultWorkerContext.class, WorkerContext.class,
          "Worker contextclass");
  /** AggregatorWriter class - optional */
  ClassConfOption<AggregatorWriter> AGGREGATOR_WRITER_CLASS =
      ClassConfOption.create("giraph.aggregatorWriterClass",
          TextAggregatorWriter.class, AggregatorWriter.class,
          "AggregatorWriter class - optional");

  /** Partition class - optional */
  ClassConfOption<Partition> PARTITION_CLASS =
      ClassConfOption.create("giraph.partitionClass", SimplePartition.class,
          Partition.class, "Partition class - optional");

  /**
   * Minimum number of simultaneous workers before this job can run (int)
   */
  String MIN_WORKERS = "giraph.minWorkers";
  /**
   * Maximum number of simultaneous worker tasks started by this job (int).
   */
  String MAX_WORKERS = "giraph.maxWorkers";

  /**
   * Separate the workers and the master tasks.  This is required
   * to support dynamic recovery. (boolean)
   */
  BooleanConfOption SPLIT_MASTER_WORKER =
      new BooleanConfOption("giraph.SplitMasterWorker", true,
          "Separate the workers and the master tasks.  This is required to " +
          "support dynamic recovery. (boolean)");

  /** Indicates whether this job is run in an internal unit test */
  BooleanConfOption LOCAL_TEST_MODE =
      new BooleanConfOption("giraph.localTestMode", false,
          "Indicates whether this job is run in an internal unit test");

  /** Override the Hadoop log level and set the desired log level. */
  StrConfOption LOG_LEVEL = new StrConfOption("giraph.logLevel", "info",
      "Override the Hadoop log level and set the desired log level.");

  /** Use thread level debugging? */
  BooleanConfOption LOG_THREAD_LAYOUT =
      new BooleanConfOption("giraph.logThreadLayout", false,
          "Use thread level debugging?");

  /** Configuration key to enable jmap printing */
  BooleanConfOption JMAP_ENABLE =
      new BooleanConfOption("giraph.jmap.histo.enable", false,
          "Configuration key to enable jmap printing");

  /** Configuration key for msec to sleep between calls */
  IntConfOption JMAP_SLEEP_MILLIS =
      new IntConfOption("giraph.jmap.histo.msec", SECONDS.toMillis(30),
          "Configuration key for msec to sleep between calls");

  /** Configuration key for how many lines to print */
  IntConfOption JMAP_PRINT_LINES =
      new IntConfOption("giraph.jmap.histo.print_lines", 30,
          "Configuration key for how many lines to print");

  /**
   * Configuration key for printing live objects only
   * This option will trigger Full GC for every jmap dump
   * and so can significantly hinder performance.
   */
  BooleanConfOption JMAP_LIVE_ONLY =
      new BooleanConfOption("giraph.jmap.histo.live", false,
          "Only print live objects in jmap?");

  /**
   * Option used by ReactiveJMapHistoDumper to check for an imminent
   * OOM in worker or master process
   */
  IntConfOption MIN_FREE_MBS_ON_HEAP =
      new IntConfOption("giraph.heap.minFreeMb", 128, "Option used by " +
          "worker and master observers to check for imminent OOM exception");
  /**
   * Option can be used to enable reactively dumping jmap histo when
   * OOM is imminent
   */
  BooleanConfOption REACTIVE_JMAP_ENABLE =
      new BooleanConfOption("giraph.heap.enableReactiveJmapDumping", false,
          "Option to enable dumping jmap histogram reactively based on " +
              "free memory on heap");

  /**
   * Minimum percent of the maximum number of workers that have responded
   * in order to continue progressing. (float)
   */
  FloatConfOption MIN_PERCENT_RESPONDED =
      new FloatConfOption("giraph.minPercentResponded", 100.0f,
          "Minimum percent of the maximum number of workers that have " +
          "responded in order to continue progressing. (float)");

  /** Enable the Metrics system */
  BooleanConfOption METRICS_ENABLE =
      new BooleanConfOption("giraph.metrics.enable", false,
          "Enable the Metrics system");

  /** Directory in HDFS to write master metrics to, instead of stderr */
  StrConfOption METRICS_DIRECTORY =
      new StrConfOption("giraph.metrics.directory", "",
          "Directory in HDFS to write master metrics to, instead of stderr");

  /**
   *  ZooKeeper comma-separated list (if not set,
   *  will start up ZooKeeper locally). Consider that after locally-starting
   *  zookeeper, this parameter will updated the configuration with the corrent
   *  configuration value.
   */
  StrConfOption ZOOKEEPER_LIST =
      new StrConfOption("giraph.zkList", "",
          "ZooKeeper comma-separated list (if not set, will start up " +
          "ZooKeeper locally). Consider that after locally-starting " +
          "zookeeper, this parameter will updated the configuration with " +
          "the corrent configuration value.");

  /**
   * Zookeeper List will always hold a value during the computation while
   * this option provides information regarding whether the zookeeper was
   * internally started or externally provided.
   */
  BooleanConfOption ZOOKEEPER_IS_EXTERNAL =
    new BooleanConfOption("giraph.zkIsExternal", true,
                          "Zookeeper List will always hold a value during " +
                          "the computation while this option provides " +
                          "information regarding whether the zookeeper was " +
                          "internally started or externally provided.");

  /** ZooKeeper session millisecond timeout */
  IntConfOption ZOOKEEPER_SESSION_TIMEOUT =
      new IntConfOption("giraph.zkSessionMsecTimeout", MINUTES.toMillis(1),
          "ZooKeeper session millisecond timeout");

  /** Polling interval to check for the ZooKeeper server data */
  IntConfOption ZOOKEEPER_SERVERLIST_POLL_MSECS =
      new IntConfOption("giraph.zkServerlistPollMsecs", SECONDS.toMillis(3),
          "Polling interval to check for the ZooKeeper server data");

  /** Number of nodes (not tasks) to run Zookeeper on */
  IntConfOption ZOOKEEPER_SERVER_COUNT =
      new IntConfOption("giraph.zkServerCount", 1,
          "Number of nodes (not tasks) to run Zookeeper on");

  /** ZooKeeper port to use */
  IntConfOption ZOOKEEPER_SERVER_PORT =
      new IntConfOption("giraph.zkServerPort", 22181, "ZooKeeper port to use");

  /** Local ZooKeeper directory to use */
  String ZOOKEEPER_DIR = "giraph.zkDir";

  /** Max attempts for handling ZooKeeper connection loss */
  IntConfOption ZOOKEEPER_OPS_MAX_ATTEMPTS =
      new IntConfOption("giraph.zkOpsMaxAttempts", 3,
          "Max attempts for handling ZooKeeper connection loss");

  /**
   * Msecs to wait before retrying a failed ZooKeeper op due to connection loss.
   */
  IntConfOption ZOOKEEPER_OPS_RETRY_WAIT_MSECS =
      new IntConfOption("giraph.zkOpsRetryWaitMsecs", SECONDS.toMillis(5),
          "Msecs to wait before retrying a failed ZooKeeper op due to " +
          "connection loss.");

  /**
   * Should start zookeeper inside master java process or separately?
   * In process by default.
   */
  BooleanConfOption ZOOKEEEPER_RUNS_IN_PROCESS = new BooleanConfOption(
      "giraph.zkRunsInProcess",
      true, "If true run zookeeper in master process, if false starts " +
      "separate process for zookeeper");

  /** TCP backlog (defaults to number of workers) */
  IntConfOption TCP_BACKLOG = new IntConfOption("giraph.tcpBacklog", 1,
      "TCP backlog (defaults to number of workers)");

  /** Use netty pooled memory buffer allocator */
  BooleanConfOption NETTY_USE_POOLED_ALLOCATOR = new BooleanConfOption(
      "giraph.useNettyPooledAllocator", false, "Should netty use pooled " +
      "memory allocator?");

  /** Use direct memory buffers in netty */
  BooleanConfOption NETTY_USE_DIRECT_MEMORY = new BooleanConfOption(
      "giraph.useNettyDirectMemory", false, "Should netty use direct " +
      "memory buffers");

  /** How big to make the encoder buffer? */
  IntConfOption NETTY_REQUEST_ENCODER_BUFFER_SIZE =
      new IntConfOption("giraph.nettyRequestEncoderBufferSize", 32 * ONE_KB,
          "How big to make the encoder buffer?");

  /** Netty client threads */
  IntConfOption NETTY_CLIENT_THREADS =
      new IntConfOption("giraph.nettyClientThreads", 4, "Netty client threads");

  /** Netty server threads */
  IntConfOption NETTY_SERVER_THREADS =
      new IntConfOption("giraph.nettyServerThreads", 16,
          "Netty server threads");

  /** Use the execution handler in netty on the client? */
  BooleanConfOption NETTY_CLIENT_USE_EXECUTION_HANDLER =
      new BooleanConfOption("giraph.nettyClientUseExecutionHandler", true,
          "Use the execution handler in netty on the client?");

  /** Netty client execution threads (execution handler) */
  IntConfOption NETTY_CLIENT_EXECUTION_THREADS =
      new IntConfOption("giraph.nettyClientExecutionThreads", 8,
          "Netty client execution threads (execution handler)");

  /** Where to place the netty client execution handle? */
  StrConfOption NETTY_CLIENT_EXECUTION_AFTER_HANDLER =
      new StrConfOption("giraph.nettyClientExecutionAfterHandler",
          "request-encoder",
          "Where to place the netty client execution handle?");

  /** Use the execution handler in netty on the server? */
  BooleanConfOption NETTY_SERVER_USE_EXECUTION_HANDLER =
      new BooleanConfOption("giraph.nettyServerUseExecutionHandler", true,
          "Use the execution handler in netty on the server?");

  /** Netty server execution threads (execution handler) */
  IntConfOption NETTY_SERVER_EXECUTION_THREADS =
      new IntConfOption("giraph.nettyServerExecutionThreads", 8,
          "Netty server execution threads (execution handler)");

  /** Where to place the netty server execution handle? */
  StrConfOption NETTY_SERVER_EXECUTION_AFTER_HANDLER =
      new StrConfOption("giraph.nettyServerExecutionAfterHandler",
          "requestFrameDecoder",
          "Where to place the netty server execution handle?");

  /** Netty simulate a first request closed */
  BooleanConfOption NETTY_SIMULATE_FIRST_REQUEST_CLOSED =
      new BooleanConfOption("giraph.nettySimulateFirstRequestClosed", false,
          "Netty simulate a first request closed");

  /** Netty simulate a first response failed */
  BooleanConfOption NETTY_SIMULATE_FIRST_RESPONSE_FAILED =
      new BooleanConfOption("giraph.nettySimulateFirstResponseFailed", false,
          "Netty simulate a first response failed");

  /** Netty - set which compression to use */
  StrConfOption NETTY_COMPRESSION_ALGORITHM =
      new StrConfOption("giraph.nettyCompressionAlgorithm", "",
          "Which compression algorithm to use in netty");

  /** Max resolve address attempts */
  IntConfOption MAX_RESOLVE_ADDRESS_ATTEMPTS =
      new IntConfOption("giraph.maxResolveAddressAttempts", 5,
          "Max resolve address attempts");

  /** Msecs to wait between waiting for all requests to finish */
  IntConfOption WAITING_REQUEST_MSECS =
      new IntConfOption("giraph.waitingRequestMsecs", SECONDS.toMillis(15),
          "Msecs to wait between waiting for all requests to finish");

  /** Millseconds to wait for an event before continuing */
  IntConfOption EVENT_WAIT_MSECS =
      new IntConfOption("giraph.eventWaitMsecs", SECONDS.toMillis(30),
          "Millseconds to wait for an event before continuing");

  /**
   * Maximum milliseconds to wait before giving up trying to get the minimum
   * number of workers before a superstep (int).
   */
  IntConfOption MAX_MASTER_SUPERSTEP_WAIT_MSECS =
      new IntConfOption("giraph.maxMasterSuperstepWaitMsecs",
          MINUTES.toMillis(10),
          "Maximum milliseconds to wait before giving up trying to get the " +
          "minimum number of workers before a superstep (int).");

  /** Milliseconds for a request to complete (or else resend) */
  IntConfOption MAX_REQUEST_MILLISECONDS =
      new IntConfOption("giraph.maxRequestMilliseconds", MINUTES.toMillis(10),
          "Milliseconds for a request to complete (or else resend)");

  /** Netty max connection failures */
  IntConfOption NETTY_MAX_CONNECTION_FAILURES =
      new IntConfOption("giraph.nettyMaxConnectionFailures", 1000,
          "Netty max connection failures");

  /** Initial port to start using for the IPC communication */
  IntConfOption IPC_INITIAL_PORT =
      new IntConfOption("giraph.ipcInitialPort", 30000,
          "Initial port to start using for the IPC communication");

  /** Maximum bind attempts for different IPC ports */
  IntConfOption MAX_IPC_PORT_BIND_ATTEMPTS =
      new IntConfOption("giraph.maxIpcPortBindAttempts", 20,
          "Maximum bind attempts for different IPC ports");
  /**
   * Fail first IPC port binding attempt, simulate binding failure
   * on real grid testing
   */
  BooleanConfOption FAIL_FIRST_IPC_PORT_BIND_ATTEMPT =
      new BooleanConfOption("giraph.failFirstIpcPortBindAttempt", false,
          "Fail first IPC port binding attempt, simulate binding failure " +
          "on real grid testing");

  /** Client send buffer size */
  IntConfOption CLIENT_SEND_BUFFER_SIZE =
      new IntConfOption("giraph.clientSendBufferSize", 512 * ONE_KB,
          "Client send buffer size");

  /** Client receive buffer size */
  IntConfOption CLIENT_RECEIVE_BUFFER_SIZE =
      new IntConfOption("giraph.clientReceiveBufferSize", 32 * ONE_KB,
          "Client receive buffer size");

  /** Server send buffer size */
  IntConfOption SERVER_SEND_BUFFER_SIZE =
      new IntConfOption("giraph.serverSendBufferSize", 32 * ONE_KB,
          "Server send buffer size");

  /** Server receive buffer size */
  IntConfOption SERVER_RECEIVE_BUFFER_SIZE =
      new IntConfOption("giraph.serverReceiveBufferSize", 512 * ONE_KB,
          "Server receive buffer size");

  /** Maximum size of messages (in bytes) per peer before flush */
  IntConfOption MAX_MSG_REQUEST_SIZE =
      new IntConfOption("giraph.msgRequestSize", 512 * ONE_KB,
          "Maximum size of messages (in bytes) per peer before flush");

  /**
   * How much bigger than the average per partition size to make initial per
   * partition buffers.
   * If this value is A, message request size is M,
   * and a worker has P partitions, than its initial partition buffer size
   * will be (M / P) * (1 + A).
   */
  FloatConfOption ADDITIONAL_MSG_REQUEST_SIZE =
      new FloatConfOption("giraph.additionalMsgRequestSize", 0.2f,
          "How much bigger than the average per partition size to make " +
          "initial per partition buffers. If this value is A, message " +
          "request size is M, and a worker has P partitions, than its " +
          "initial partition buffer size will be (M / P) * (1 + A).");


  /** Warn if msg request size exceeds default size by this factor */
  FloatConfOption REQUEST_SIZE_WARNING_THRESHOLD = new FloatConfOption(
      "giraph.msgRequestWarningThreshold", 2.0f,
      "If request sizes are bigger than the buffer size by this factor " +
      "warnings are printed to the log and to the command line");

  /** Maximum size of vertices (in bytes) per peer before flush */
  IntConfOption MAX_VERTEX_REQUEST_SIZE =
      new IntConfOption("giraph.vertexRequestSize", 512 * ONE_KB,
          "Maximum size of vertices (in bytes) per peer before flush");

  /**
   * Additional size (expressed as a ratio) of each per-partition buffer on
   * top of the average size for vertices.
   */
  FloatConfOption ADDITIONAL_VERTEX_REQUEST_SIZE =
      new FloatConfOption("giraph.additionalVertexRequestSize", 0.2f,
          "Additional size (expressed as a ratio) of each per-partition " +
              "buffer on top of the average size.");

  /** Maximum size of edges (in bytes) per peer before flush */
  IntConfOption MAX_EDGE_REQUEST_SIZE =
      new IntConfOption("giraph.edgeRequestSize", 512 * ONE_KB,
          "Maximum size of edges (in bytes) per peer before flush");

  /**
   * Additional size (expressed as a ratio) of each per-partition buffer on
   * top of the average size for edges.
   */
  FloatConfOption ADDITIONAL_EDGE_REQUEST_SIZE =
      new FloatConfOption("giraph.additionalEdgeRequestSize", 0.2f,
          "Additional size (expressed as a ratio) of each per-partition " +
          "buffer on top of the average size.");

  /** Maximum number of mutations per partition before flush */
  IntConfOption MAX_MUTATIONS_PER_REQUEST =
      new IntConfOption("giraph.maxMutationsPerRequest", 100,
          "Maximum number of mutations per partition before flush");

  /**
   * Use message size encoding (typically better for complex objects,
   * not meant for primitive wrapped messages)
   */
  BooleanConfOption USE_MESSAGE_SIZE_ENCODING =
      new BooleanConfOption("giraph.useMessageSizeEncoding", false,
          "Use message size encoding (typically better for complex objects, " +
          "not meant for primitive wrapped messages)");

  /** Number of channels used per server */
  IntConfOption CHANNELS_PER_SERVER =
      new IntConfOption("giraph.channelsPerServer", 1,
          "Number of channels used per server");

  /** Number of flush threads per peer */
  String MSG_NUM_FLUSH_THREADS = "giraph.msgNumFlushThreads";

  /** Number of threads for vertex computation */
  IntConfOption NUM_COMPUTE_THREADS =
      new IntConfOption("giraph.numComputeThreads", 1,
          "Number of threads for vertex computation");

  /** Number of threads for input split loading */
  IntConfOption NUM_INPUT_THREADS =
      new IntConfOption("giraph.numInputThreads", 1,
          "Number of threads for input split loading");

  /** Minimum stragglers of the superstep before printing them out */
  IntConfOption PARTITION_LONG_TAIL_MIN_PRINT =
      new IntConfOption("giraph.partitionLongTailMinPrint", 1,
          "Minimum stragglers of the superstep before printing them out");

  /** Use superstep counters? (boolean) */
  BooleanConfOption USE_SUPERSTEP_COUNTERS =
      new BooleanConfOption("giraph.useSuperstepCounters", true,
          "Use superstep counters? (boolean)");

  /**
   * Input split sample percent - Used only for sampling and testing, rather
   * than an actual job.  The idea is that to test, you might only want a
   * fraction of the actual input splits from your VertexInputFormat to
   * load (values should be [0, 100]).
   */
  FloatConfOption INPUT_SPLIT_SAMPLE_PERCENT =
      new FloatConfOption("giraph.inputSplitSamplePercent", 100f,
          "Input split sample percent - Used only for sampling and testing, " +
          "rather than an actual job.  The idea is that to test, you might " +
          "only want a fraction of the actual input splits from your " +
          "VertexInputFormat to load (values should be [0, 100]).");

  /**
   * To limit outlier vertex input splits from producing too many vertices or
   * to help with testing, the number of vertices loaded from an input split
   * can be limited.  By default, everything is loaded.
   */
  LongConfOption INPUT_SPLIT_MAX_VERTICES =
      new LongConfOption("giraph.InputSplitMaxVertices", -1,
          "To limit outlier vertex input splits from producing too many " +
              "vertices or to help with testing, the number of vertices " +
              "loaded from an input split can be limited. By default, " +
              "everything is loaded.");

  /**
   * To limit outlier vertex input splits from producing too many vertices or
   * to help with testing, the number of edges loaded from an input split
   * can be limited.  By default, everything is loaded.
   */
  LongConfOption INPUT_SPLIT_MAX_EDGES =
      new LongConfOption("giraph.InputSplitMaxEdges", -1,
          "To limit outlier vertex input splits from producing too many " +
              "vertices or to help with testing, the number of edges loaded " +
              "from an input split can be limited. By default, everything is " +
              "loaded.");

  /**
   * To minimize network usage when reading input splits,
   * each worker can prioritize splits that reside on its host.
   * This, however, comes at the cost of increased load on ZooKeeper.
   * Hence, users with a lot of splits and input threads (or with
   * configurations that can't exploit locality) may want to disable it.
   */
  BooleanConfOption USE_INPUT_SPLIT_LOCALITY =
      new BooleanConfOption("giraph.useInputSplitLocality", true,
          "To minimize network usage when reading input splits, each worker " +
          "can prioritize splits that reside on its host. " +
          "This, however, comes at the cost of increased load on ZooKeeper. " +
          "Hence, users with a lot of splits and input threads (or with " +
          "configurations that can't exploit locality) may want to disable " +
          "it.");

  /** Multiplier for the current workers squared */
  FloatConfOption PARTITION_COUNT_MULTIPLIER =
      new FloatConfOption("giraph.masterPartitionCountMultiplier", 1.0f,
          "Multiplier for the current workers squared");

  /** Overrides default partition count calculation if not -1 */
  IntConfOption USER_PARTITION_COUNT =
      new IntConfOption("giraph.userPartitionCount", -1,
          "Overrides default partition count calculation if not -1");

  /** Vertex key space size for
   * {@link org.apache.giraph.partition.SimpleWorkerPartitioner}
   */
  String PARTITION_VERTEX_KEY_SPACE_SIZE = "giraph.vertexKeySpaceSize";

  /** Java opts passed to ZooKeeper startup */
  StrConfOption ZOOKEEPER_JAVA_OPTS =
      new StrConfOption("giraph.zkJavaOpts",
          "-Xmx512m -XX:ParallelGCThreads=4 -XX:+UseConcMarkSweepGC " +
          "-XX:CMSInitiatingOccupancyFraction=70 -XX:MaxGCPauseMillis=100",
          "Java opts passed to ZooKeeper startup");

  /**
   *  How often to checkpoint (i.e. 0, means no checkpoint,
   *  1 means every superstep, 2 is every two supersteps, etc.).
   */
  IntConfOption CHECKPOINT_FREQUENCY =
      new IntConfOption("giraph.checkpointFrequency", 0,
          "How often to checkpoint (i.e. 0, means no checkpoint, 1 means " +
          "every superstep, 2 is every two supersteps, etc.).");

  /**
   * Delete checkpoints after a successful job run?
   */
  BooleanConfOption CLEANUP_CHECKPOINTS_AFTER_SUCCESS =
      new BooleanConfOption("giraph.cleanupCheckpointsAfterSuccess", true,
          "Delete checkpoints after a successful job run?");

  /**
   * An application can be restarted manually by selecting a superstep.  The
   * corresponding checkpoint must exist for this to work.  The user should
   * set a long value.  Default is start from scratch.
   */
  String RESTART_SUPERSTEP = "giraph.restartSuperstep";

  /**
   * If application is restarted manually we need to specify job ID
   * to restart from.
   */
  StrConfOption RESTART_JOB_ID = new StrConfOption("giraph.restart.jobId",
      null, "Which job ID should I try to restart?");

  /**
   * Base ZNode for Giraph's state in the ZooKeeper cluster.  Must be a root
   * znode on the cluster beginning with "/"
   */
  String BASE_ZNODE_KEY = "giraph.zkBaseZNode";

  /**
   * If ZOOKEEPER_LIST is not set, then use this directory to manage
   * ZooKeeper
   */
  StrConfOption ZOOKEEPER_MANAGER_DIRECTORY =
      new StrConfOption("giraph.zkManagerDirectory",
          "_bsp/_defaultZkManagerDir",
          "If ZOOKEEPER_LIST is not set, then use this directory to manage " +
          "ZooKeeper");

  /** Number of ZooKeeper client connection attempts before giving up. */
  IntConfOption ZOOKEEPER_CONNECTION_ATTEMPTS =
      new IntConfOption("giraph.zkConnectionAttempts", 10,
          "Number of ZooKeeper client connection attempts before giving up.");

  /** This directory has/stores the available checkpoint files in HDFS. */
  StrConfOption CHECKPOINT_DIRECTORY =
      new StrConfOption("giraph.checkpointDirectory", "_bsp/_checkpoints/",
          "This directory has/stores the available checkpoint files in HDFS.");

  /**
   * Comma-separated list of directories in the local file system for
   * out-of-core messages.
   */
  StrConfOption MESSAGES_DIRECTORY =
      new StrConfOption("giraph.messagesDirectory", "_bsp/_messages/",
          "Comma-separated list of directories in the local file system for " +
          "out-of-core messages.");

  /**
   * If using out-of-core messaging, it tells how much messages do we keep
   * in memory.
   */
  IntConfOption MAX_MESSAGES_IN_MEMORY =
      new IntConfOption("giraph.maxMessagesInMemory", 1000000,
          "If using out-of-core messaging, it tells how much messages do we " +
          "keep in memory.");
  /** Size of buffer when reading and writing messages out-of-core. */
  IntConfOption MESSAGES_BUFFER_SIZE =
      new IntConfOption("giraph.messagesBufferSize", 8 * ONE_KB,
          "Size of buffer when reading and writing messages out-of-core.");

  /**
   * Comma-separated list of directories in the local filesystem for
   * out-of-core partitions.
   */
  StrConfOption PARTITIONS_DIRECTORY =
      new StrConfOption("giraph.partitionsDirectory", "_bsp/_partitions",
          "Comma-separated list of directories in the local filesystem for " +
          "out-of-core partitions.");

  /** Enable out-of-core graph. */
  BooleanConfOption USE_OUT_OF_CORE_GRAPH =
      new BooleanConfOption("giraph.useOutOfCoreGraph", false,
          "Enable out-of-core graph.");

  /** Directory to write YourKit snapshots to */
  String YOURKIT_OUTPUT_DIR = "giraph.yourkit.outputDir";
  /** Default directory to write YourKit snapshots to */
  String YOURKIT_OUTPUT_DIR_DEFAULT = "/tmp/giraph/%JOB_ID%/%TASK_ID%";

  /** Maximum number of partitions to hold in memory for each worker. */
  IntConfOption MAX_PARTITIONS_IN_MEMORY =
      new IntConfOption("giraph.maxPartitionsInMemory", 10,
          "Maximum number of partitions to hold in memory for each worker.");

  /** Set number of sticky partitions if sticky mode is enabled.  */
  IntConfOption MAX_STICKY_PARTITIONS =
      new IntConfOption("giraph.stickyPartitions", 0,
          "Set number of sticky partitions if sticky mode is enabled.");

  /** Keep the zookeeper output for debugging? Default is to remove it. */
  BooleanConfOption KEEP_ZOOKEEPER_DATA =
      new BooleanConfOption("giraph.keepZooKeeperData", false,
          "Keep the zookeeper output for debugging? Default is to remove it.");

  /** Default ZooKeeper tick time. */
  int DEFAULT_ZOOKEEPER_TICK_TIME = 6000;
  /** Default ZooKeeper init limit (in ticks). */
  int DEFAULT_ZOOKEEPER_INIT_LIMIT = 10;
  /** Default ZooKeeper sync limit (in ticks). */
  int DEFAULT_ZOOKEEPER_SYNC_LIMIT = 5;
  /** Default ZooKeeper snap count. */
  int DEFAULT_ZOOKEEPER_SNAP_COUNT = 50000;
  /** Default ZooKeeper maximum client connections. */
  int DEFAULT_ZOOKEEPER_MAX_CLIENT_CNXNS = 10000;
  /** ZooKeeper minimum session timeout */
  IntConfOption ZOOKEEPER_MIN_SESSION_TIMEOUT =
      new IntConfOption("giraph.zKMinSessionTimeout", MINUTES.toMillis(10),
          "ZooKeeper minimum session timeout");
  /** ZooKeeper maximum session timeout */
  IntConfOption ZOOKEEPER_MAX_SESSION_TIMEOUT =
      new IntConfOption("giraph.zkMaxSessionTimeout", MINUTES.toMillis(15),
          "ZooKeeper maximum session timeout");
  /** ZooKeeper force sync */
  BooleanConfOption ZOOKEEPER_FORCE_SYNC =
      new BooleanConfOption("giraph.zKForceSync", false,
          "ZooKeeper force sync");
  /** ZooKeeper skip ACLs */
  BooleanConfOption ZOOKEEPER_SKIP_ACL =
      new BooleanConfOption("giraph.ZkSkipAcl", true, "ZooKeeper skip ACLs");

  /**
   * Whether to use SASL with DIGEST and Hadoop Job Tokens to authenticate
   * and authorize Netty BSP Clients to Servers.
   */
  BooleanConfOption AUTHENTICATE =
      new BooleanConfOption("giraph.authenticate", false,
          "Whether to use SASL with DIGEST and Hadoop Job Tokens to " +
          "authenticate and authorize Netty BSP Clients to Servers.");

  /** Use unsafe serialization? */
  BooleanConfOption USE_UNSAFE_SERIALIZATION =
      new BooleanConfOption("giraph.useUnsafeSerialization", true,
          "Use unsafe serialization?");

  /**
   * Use BigDataIO for messages? If there are super-vertices in the
   * graph which receive a lot of messages (total serialized size of messages
   * goes beyond the maximum size of a byte array), setting this option to true
   * will remove that limit. The maximum memory available for a single vertex
   * will be limited to the maximum heap size available.
   */
  BooleanConfOption USE_BIG_DATA_IO_FOR_MESSAGES =
      new BooleanConfOption("giraph.useBigDataIOForMessages", false,
          "Use BigDataIO for messages?");

  /**
   * Maximum number of attempts a master/worker will retry before killing
   * the job.  This directly maps to the number of map task attempts in
   * Hadoop.
   */
  IntConfOption MAX_TASK_ATTEMPTS =
      new IntConfOption("mapred.map.max.attempts", -1,
          "Maximum number of attempts a master/worker will retry before " +
          "killing the job.  This directly maps to the number of map task " +
          "attempts in Hadoop.");

  /** Interface to use for hostname resolution */
  StrConfOption DNS_INTERFACE =
      new StrConfOption("giraph.dns.interface", "default",
          "Interface to use for hostname resolution");
  /** Server for hostname resolution */
  StrConfOption DNS_NAMESERVER =
      new StrConfOption("giraph.dns.nameserver", "default",
          "Server for hostname resolution");

  /**
   * The application will halt after this many supersteps is completed.  For
   * instance, if it is set to 3, the application will run at most 0, 1,
   * and 2 supersteps and then go into the shutdown superstep.
   */
  IntConfOption MAX_NUMBER_OF_SUPERSTEPS =
      new IntConfOption("giraph.maxNumberOfSupersteps", 1,
          "The application will halt after this many supersteps is " +
          "completed. For instance, if it is set to 3, the application will " +
          "run at most 0, 1, and 2 supersteps and then go into the shutdown " +
          "superstep.");

  /**
   * The application will not mutate the graph topology (the edges). It is used
   * to optimise out-of-core graph, by not writing back edges every time.
   */
  BooleanConfOption STATIC_GRAPH =
      new BooleanConfOption("giraph.isStaticGraph", false,
          "The application will not mutate the graph topology (the edges). " +
          "It is used to optimise out-of-core graph, by not writing back " +
          "edges every time.");

  /**
   * This option will tell which message encode & store enum to use when
   * combining is not enabled
   */
  EnumConfOption<MessageEncodeAndStoreType> MESSAGE_ENCODE_AND_STORE_TYPE =
      EnumConfOption.create("giraph.messageEncodeAndStoreType",
          MessageEncodeAndStoreType.class,
          MessageEncodeAndStoreType.BYTEARRAY_PER_PARTITION,
          "Select the message_encode_and_store_type to use");

  /**
   * This option can be used to specify if a source vertex present in edge
   * input but not in vertex input can be created
   */
  BooleanConfOption CREATE_EDGE_SOURCE_VERTICES =
      new BooleanConfOption("giraph.createEdgeSourceVertices", true,
          "Create a source vertex if present in edge input but not " +
          "necessarily in vertex input");

  /**
   * This counter group will contain one counter whose name is the ZooKeeper
   * server:port which this job is using
   */
  String ZOOKEEPER_SERVER_PORT_COUNTER_GROUP = "Zookeeper server:port";

  /**
   * This counter group will contain one counter whose name is the ZooKeeper
   * node path which should be created to trigger computation halt
   */
  String ZOOKEEPER_HALT_NODE_COUNTER_GROUP = "Zookeeper halt node";

  /**
   * This counter group will contain one counter whose name is the ZooKeeper
   * node path which contains all data about this job
   */
  String ZOOKEEPER_BASE_PATH_COUNTER_GROUP = "Zookeeper base path";

  /**
   * Which class to use to write instructions on how to halt the application
   */
  ClassConfOption<HaltApplicationUtils.HaltInstructionsWriter>
  HALT_INSTRUCTIONS_WRITER_CLASS = ClassConfOption.create(
      "giraph.haltInstructionsWriter",
      HaltApplicationUtils.DefaultHaltInstructionsWriter.class,
      HaltApplicationUtils.HaltInstructionsWriter.class,
      "Class used to write instructions on how to halt the application");

  /**
   * Maximum timeout (in milliseconds) for waiting for all tasks
   * to complete after the job is done.  Defaults to 15 minutes.
   */
  IntConfOption WAIT_TASK_DONE_TIMEOUT_MS =
      new IntConfOption("giraph.waitTaskDoneTimeoutMs", MINUTES.toMillis(15),
          "Maximum timeout (in ms) for waiting for all all tasks to " +
              "complete");

  /** Whether to track job progress on client or not */
  BooleanConfOption TRACK_JOB_PROGRESS_ON_CLIENT =
      new BooleanConfOption("giraph.trackJobProgressOnClient", false,
          "Whether to track job progress on client or not");

  /** Number of retries for creating the HDFS files */
  IntConfOption HDFS_FILE_CREATION_RETRIES =
      new IntConfOption("giraph.hdfs.file.creation.retries", 10,
          "Retries to create an HDFS file before failing");

  /** Number of milliseconds to wait before retrying HDFS file creation */
  IntConfOption HDFS_FILE_CREATION_RETRY_WAIT_MS =
      new IntConfOption("giraph.hdfs.file.creation.retry.wait.ms", 30_000,
          "Milliseconds to wait prior to retrying creation of an HDFS file");

  /** Number of threads for writing and reading checkpoints */
  IntConfOption NUM_CHECKPOINT_IO_THREADS =
      new IntConfOption("giraph.checkpoint.io.threads", 8,
          "Number of threads for writing and reading checkpoints");

  /**
   * Compression algorithm to be used for checkpointing.
   * Defined by extension for hadoop compatibility reasons.
   */
  StrConfOption CHECKPOINT_COMPRESSION_CODEC =
      new StrConfOption("giraph.checkpoint.compression.codec",
          ".deflate",
          "Defines compression algorithm we will be using for " +
              "storing checkpoint. Available options include but " +
              "not restricted to: .deflate, .gz, .bz2, .lzo");

  /**
   * Defines if and when checkpointing is supported by this job.
   * By default checkpointing is always supported unless output during the
   * computation is enabled.
   */
  ClassConfOption<CheckpointSupportedChecker> CHECKPOINT_SUPPORTED_CHECKER =
      ClassConfOption.create("giraph.checkpoint.supported.checker",
          DefaultCheckpointSupportedChecker.class,
          CheckpointSupportedChecker.class,
          "This is the way to specify if checkpointing is " +
              "supported by the job");


  /** Number of threads to use in async message store, 0 means
   * we should not use async message processing */
  IntConfOption ASYNC_MESSAGE_STORE_THREADS_COUNT =
      new IntConfOption("giraph.async.message.store.threads", 0,
          "Number of threads to be used in async message store.");

  /** Output format class for hadoop to use (for committing) */
  ClassConfOption<OutputFormat> HADOOP_OUTPUT_FORMAT_CLASS =
      ClassConfOption.create("giraph.hadoopOutputFormatClass",
          BspOutputFormat.class, OutputFormat.class,
          "Output format class for hadoop to use (for committing)");
}
// CHECKSTYLE: resume InterfaceIsTypeCheck


File: giraph-core/src/main/java/org/apache/giraph/edge/AbstractEdgeStore.java
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

package org.apache.giraph.edge;

import com.google.common.collect.MapMaker;
import org.apache.giraph.bsp.CentralizedServiceWorker;
import org.apache.giraph.conf.DefaultImmutableClassesGiraphConfigurable;
import org.apache.giraph.conf.ImmutableClassesGiraphConfiguration;
import org.apache.giraph.graph.Vertex;
import org.apache.giraph.partition.Partition;
import org.apache.giraph.utils.CallableFactory;
import org.apache.giraph.utils.ProgressableUtils;
import org.apache.giraph.utils.Trimmable;
import org.apache.giraph.utils.VertexIdEdgeIterator;
import org.apache.giraph.utils.VertexIdEdges;
import org.apache.hadoop.io.Writable;
import org.apache.hadoop.io.WritableComparable;
import org.apache.hadoop.util.Progressable;
import org.apache.log4j.Logger;

import java.util.Iterator;
import java.util.Map;
import java.util.concurrent.ArrayBlockingQueue;
import java.util.concurrent.BlockingQueue;
import java.util.concurrent.Callable;
import java.util.concurrent.ConcurrentMap;

/**
 * Basic implementation of edges store, extended this to easily define simple
 * and primitive edge stores
 *
 * @param <I> Vertex id
 * @param <V> Vertex value
 * @param <E> Edge value
 * @param <K> Key corresponding to Vertex id
 * @param <Et> Entry type
 */
public abstract class AbstractEdgeStore<I extends WritableComparable,
  V extends Writable, E extends Writable, K, Et>
  extends DefaultImmutableClassesGiraphConfigurable<I, V, E>
  implements EdgeStore<I, V, E> {
  /** Class logger */
  private static final Logger LOG = Logger.getLogger(AbstractEdgeStore.class);
  /** Service worker. */
  protected CentralizedServiceWorker<I, V, E> service;
  /** Giraph configuration. */
  protected ImmutableClassesGiraphConfiguration<I, V, E> configuration;
  /** Progressable to report progress. */
  protected Progressable progressable;
  /** Map used to temporarily store incoming edges. */
  protected ConcurrentMap<Integer, Map<K, OutEdges<I, E>>> transientEdges;
  /**
   * Whether the chosen {@link OutEdges} implementation allows for Edge
   * reuse.
   */
  protected boolean reuseEdgeObjects;
  /**
   * Whether the {@link OutEdges} class used during input is different
   * from the one used during computation.
   */
  protected boolean useInputOutEdges;

  /**
   * Constructor.
   *
   * @param service Service worker
   * @param configuration Configuration
   * @param progressable Progressable
   */
  public AbstractEdgeStore(
    CentralizedServiceWorker<I, V, E> service,
    ImmutableClassesGiraphConfiguration<I, V, E> configuration,
    Progressable progressable) {
    this.service = service;
    this.configuration = configuration;
    this.progressable = progressable;
    transientEdges = new MapMaker().concurrencyLevel(
      configuration.getNettyServerExecutionConcurrency()).makeMap();
    reuseEdgeObjects = configuration.reuseEdgeObjects();
    useInputOutEdges = configuration.useInputOutEdges();
  }

  /**
   * Get vertexId for a given key
   *
   * @param entry for vertexId key
   * @param representativeVertexId representativeVertexId
   * @return vertex Id
   */
  protected abstract I getVertexId(Et entry, I representativeVertexId);

  /**
   * Create vertexId from a given key
   *
   * @param entry for vertexId key
   * @return new vertexId
   */
  protected abstract I createVertexId(Et entry);

  /**
   * Get OutEdges for a given partition
   *
   * @param partitionId id of partition
   * @return OutEdges for the partition
   */
  protected abstract Map<K, OutEdges<I, E>> getPartitionEdges(int partitionId);

  /**
   * Return the OutEdges for a given partition
   *
   * @param entry for vertexId key
   * @return out edges
   */
  protected abstract OutEdges<I, E> getPartitionEdges(Et entry);

  /**
   * Get iterator for partition edges
   *
   * @param partitionEdges map of out-edges for vertices in a partition
   * @return iterator
   */
  protected abstract Iterator<Et>
  getPartitionEdgesIterator(Map<K, OutEdges<I, E>> partitionEdges);

  /**
   * Get out-edges for a given vertex
   *
   * @param vertexIdEdgeIterator vertex Id Edge iterator
   * @param partitionEdgesIn map of out-edges for vertices in a partition
   * @return out-edges for the vertex
   */
  protected abstract OutEdges<I, E> getVertexOutEdges(
    VertexIdEdgeIterator<I, E> vertexIdEdgeIterator,
    Map<K, OutEdges<I, E>> partitionEdgesIn);

  @Override
  public void addPartitionEdges(
    int partitionId, VertexIdEdges<I, E> edges) {
    Map<K, OutEdges<I, E>> partitionEdges = getPartitionEdges(partitionId);

    VertexIdEdgeIterator<I, E> vertexIdEdgeIterator =
        edges.getVertexIdEdgeIterator();
    while (vertexIdEdgeIterator.hasNext()) {
      vertexIdEdgeIterator.next();
      Edge<I, E> edge = reuseEdgeObjects ?
          vertexIdEdgeIterator.getCurrentEdge() :
          vertexIdEdgeIterator.releaseCurrentEdge();
      OutEdges<I, E> outEdges = getVertexOutEdges(vertexIdEdgeIterator,
          partitionEdges);
      synchronized (outEdges) {
        outEdges.add(edge);
      }
    }
  }

  /**
   * Convert the input edges to the {@link OutEdges} data structure used
   * for computation (if different).
   *
   * @param inputEdges Input edges
   * @return Compute edges
   */
  private OutEdges<I, E> convertInputToComputeEdges(
    OutEdges<I, E> inputEdges) {
    if (!useInputOutEdges) {
      return inputEdges;
    } else {
      return configuration.createAndInitializeOutEdges(inputEdges);
    }
  }

  @Override
  public void moveEdgesToVertices() {
    final boolean createSourceVertex = configuration.getCreateSourceVertex();
    if (transientEdges.isEmpty()) {
      if (LOG.isInfoEnabled()) {
        LOG.info("moveEdgesToVertices: No edges to move");
      }
      return;
    }

    if (LOG.isInfoEnabled()) {
      LOG.info("moveEdgesToVertices: Moving incoming edges to vertices.");
    }

    final BlockingQueue<Integer> partitionIdQueue =
        new ArrayBlockingQueue<>(transientEdges.size());
    partitionIdQueue.addAll(transientEdges.keySet());
    int numThreads = configuration.getNumInputSplitsThreads();

    CallableFactory<Void> callableFactory = new CallableFactory<Void>() {
      @Override
      public Callable<Void> newCallable(int callableId) {
        return new Callable<Void>() {
          @Override
          public Void call() throws Exception {
            Integer partitionId;
            I representativeVertexId = configuration.createVertexId();
            while ((partitionId = partitionIdQueue.poll()) != null) {
              Partition<I, V, E> partition =
                  service.getPartitionStore().getOrCreatePartition(partitionId);
              Map<K, OutEdges<I, E>> partitionEdges =
                  transientEdges.remove(partitionId);
              Iterator<Et> iterator =
                  getPartitionEdgesIterator(partitionEdges);
              // process all vertices in given partition
              while (iterator.hasNext()) {
                Et entry = iterator.next();
                I vertexId = getVertexId(entry, representativeVertexId);
                OutEdges<I, E> outEdges = convertInputToComputeEdges(
                  getPartitionEdges(entry));
                Vertex<I, V, E> vertex = partition.getVertex(vertexId);
                // If the source vertex doesn't exist, create it. Otherwise,
                // just set the edges.
                if (vertex == null) {
                  if (createSourceVertex) {
                    // createVertex only if it is allowed by configuration
                    vertex = configuration.createVertex();
                    vertex.initialize(createVertexId(entry),
                        configuration.createVertexValue(), outEdges);
                    partition.putVertex(vertex);
                  }
                } else {
                  // A vertex may exist with or without edges initially
                  // and optimize the case of no initial edges
                  if (vertex.getNumEdges() == 0) {
                    vertex.setEdges(outEdges);
                  } else {
                    for (Edge<I, E> edge : outEdges) {
                      vertex.addEdge(edge);
                    }
                  }
                  if (vertex instanceof Trimmable) {
                    ((Trimmable) vertex).trim();
                  }
                  // Some Partition implementations (e.g. ByteArrayPartition)
                  // require us to put back the vertex after modifying it.
                  partition.saveVertex(vertex);
                }
                iterator.remove();
              }
              // Some PartitionStore implementations
              // (e.g. DiskBackedPartitionStore) require us to put back the
              // partition after modifying it.
              service.getPartitionStore().putPartition(partition);
            }
            return null;
          }
        };
      }
    };
    ProgressableUtils.getResultsWithNCallables(callableFactory, numThreads,
        "move-edges-%d", progressable);

    // remove all entries
    transientEdges.clear();

    if (LOG.isInfoEnabled()) {
      LOG.info("moveEdgesToVertices: Finished moving incoming edges to " +
          "vertices.");
    }
  }
}


File: giraph-core/src/main/java/org/apache/giraph/edge/EdgeStore.java
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

package org.apache.giraph.edge;

import org.apache.giraph.utils.VertexIdEdges;
import org.apache.hadoop.io.Writable;
import org.apache.hadoop.io.WritableComparable;

/**
 * Collects incoming edges for vertices owned by this worker.
 *
 * @param <I> Vertex id
 * @param <V> Vertex value
 * @param <E> Edge value
 */
public interface EdgeStore<I extends WritableComparable,
   V extends Writable, E extends Writable> {
  /**
   * Add edges belonging to a given partition on this worker.
   * Note: This method is thread-safe.
   *
   * @param partitionId Partition id for the incoming edges.
   * @param edges Incoming edges
   */
  void addPartitionEdges(int partitionId, VertexIdEdges<I, E> edges);

  /**
   * Move all edges from temporary storage to their source vertices.
   * Note: this method is not thread-safe.
   */
  void moveEdgesToVertices();
}


File: giraph-core/src/main/java/org/apache/giraph/edge/SimpleEdgeStore.java
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

package org.apache.giraph.edge;

import org.apache.giraph.bsp.CentralizedServiceWorker;
import org.apache.giraph.conf.ImmutableClassesGiraphConfiguration;
import org.apache.giraph.utils.VertexIdEdgeIterator;
import org.apache.hadoop.io.Writable;
import org.apache.hadoop.io.WritableComparable;
import org.apache.hadoop.util.Progressable;

import com.google.common.collect.MapMaker;

import java.util.Iterator;
import java.util.Map;
import java.util.concurrent.ConcurrentMap;

/**
 * Simple in memory edge store which supports any type of ids.
 *
 * @param <I> Vertex id
 * @param <V> Vertex value
 * @param <E> Edge value
 */
public class SimpleEdgeStore<I extends WritableComparable,
  V extends Writable, E extends Writable>
  extends AbstractEdgeStore<I, V, E, I,
  Map.Entry<I, OutEdges<I, E>>> {

  /**
   * Constructor.
   *
   * @param service Service worker
   * @param configuration Configuration
   * @param progressable Progressable
   */
  public SimpleEdgeStore(
    CentralizedServiceWorker<I, V, E> service,
    ImmutableClassesGiraphConfiguration<I, V, E> configuration,
    Progressable progressable) {
    super(service, configuration, progressable);
  }

  @Override
  protected I getVertexId(Map.Entry<I, OutEdges<I, E>> entry,
    I representativeVertexId) {
    return entry.getKey();
  }

  @Override
  protected I createVertexId(Map.Entry<I, OutEdges<I, E>> entry) {
    return entry.getKey();
  }

  @Override
  protected ConcurrentMap<I, OutEdges<I, E>> getPartitionEdges(
    int partitionId) {
    ConcurrentMap<I, OutEdges<I, E>> partitionEdges =
        (ConcurrentMap<I, OutEdges<I, E>>) transientEdges.get(partitionId);
    if (partitionEdges == null) {
      ConcurrentMap<I, OutEdges<I, E>> newPartitionEdges =
          new MapMaker().concurrencyLevel(
              configuration.getNettyServerExecutionConcurrency()).makeMap();
      partitionEdges = (ConcurrentMap<I, OutEdges<I, E>>)
          transientEdges.putIfAbsent(partitionId, newPartitionEdges);
      if (partitionEdges == null) {
        partitionEdges = newPartitionEdges;
      }
    }
    return partitionEdges;
  }

  @Override
  protected OutEdges<I, E> getPartitionEdges(
    Map.Entry<I, OutEdges<I, E>> entry) {
    return entry.getValue();
  }

  @Override
  protected Iterator<Map.Entry<I, OutEdges<I, E>>>
  getPartitionEdgesIterator(Map<I, OutEdges<I, E>> partitionEdges) {
    return partitionEdges.entrySet().iterator();
  }

  @Override
  protected OutEdges<I, E> getVertexOutEdges(
      VertexIdEdgeIterator<I, E> vertexIdEdgeIterator,
      Map<I, OutEdges<I, E>> partitionEdgesIn) {
    ConcurrentMap<I, OutEdges<I, E>> partitionEdges =
        (ConcurrentMap<I, OutEdges<I, E>>) partitionEdgesIn;
    I vertexId = vertexIdEdgeIterator.getCurrentVertexId();
    OutEdges<I, E> outEdges = partitionEdges.get(vertexId);
    if (outEdges == null) {
      OutEdges<I, E> newOutEdges =
          configuration.createAndInitializeInputOutEdges();
      outEdges = partitionEdges.putIfAbsent(vertexId, newOutEdges);
      if (outEdges == null) {
        outEdges = newOutEdges;
        // Since we had to use the vertex id as a new key in the map,
        // we need to release the object.
        vertexIdEdgeIterator.releaseCurrentVertexId();
      }
    }
    return outEdges;
  }
}


File: giraph-core/src/main/java/org/apache/giraph/edge/primitives/IntEdgeStore.java
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

package org.apache.giraph.edge.primitives;

import org.apache.giraph.bsp.CentralizedServiceWorker;
import org.apache.giraph.conf.ImmutableClassesGiraphConfiguration;
import org.apache.giraph.edge.AbstractEdgeStore;
import org.apache.giraph.edge.OutEdges;
import org.apache.giraph.utils.VertexIdEdgeIterator;
import org.apache.hadoop.io.IntWritable;
import org.apache.hadoop.io.Writable;
import org.apache.hadoop.util.Progressable;

import it.unimi.dsi.fastutil.ints.Int2ObjectMaps;
import it.unimi.dsi.fastutil.ints.Int2ObjectOpenHashMap;
import it.unimi.dsi.fastutil.ints.Int2ObjectMap;

import java.util.Iterator;
import java.util.Map;

/**
 * Special edge store to be used when ids are IntWritable.
 * Uses fastutil primitive maps in order to decrease number of objects and
 * get better performance.
 *
 * @param <V> Vertex value
 * @param <E> Edge value
 */
public class IntEdgeStore<V extends Writable, E extends Writable>
  extends AbstractEdgeStore<IntWritable, V, E, Integer,
  Int2ObjectMap.Entry<OutEdges<IntWritable, E>>> {

  /**
   * Constructor.
   *
   * @param service       Service worker
   * @param configuration Configuration
   * @param progressable  Progressable
   */
  public IntEdgeStore(
      CentralizedServiceWorker<IntWritable, V, E> service,
      ImmutableClassesGiraphConfiguration<IntWritable, V, E> configuration,
      Progressable progressable) {
    super(service, configuration, progressable);
  }

  @Override
  protected IntWritable getVertexId(
    Int2ObjectMap.Entry<OutEdges<IntWritable, E>> entry,
    IntWritable representativeVertexId) {
    representativeVertexId.set(entry.getIntKey());
    return representativeVertexId;
  }

  @Override
  protected IntWritable createVertexId(
    Int2ObjectMap.Entry<OutEdges<IntWritable, E>> entry) {
    return new IntWritable(entry.getIntKey());
  }

  @Override
  protected OutEdges<IntWritable, E> getPartitionEdges(
    Int2ObjectMap.Entry<OutEdges<IntWritable, E>> entry) {
    return entry.getValue();
  }

  @Override
  protected Iterator<Int2ObjectMap.Entry<OutEdges<IntWritable, E>>>
  getPartitionEdgesIterator(
    Map<Integer, OutEdges<IntWritable, E>> partitionEdges) {
    return  ((Int2ObjectMap<OutEdges<IntWritable, E>>) partitionEdges)
        .int2ObjectEntrySet()
        .iterator();
  }

  @Override
  protected Int2ObjectMap<OutEdges<IntWritable, E>> getPartitionEdges(
      int partitionId) {
    Int2ObjectMap<OutEdges<IntWritable, E>> partitionEdges =
        (Int2ObjectMap<OutEdges<IntWritable, E>>)
            transientEdges.get(partitionId);
    if (partitionEdges == null) {
      Int2ObjectMap<OutEdges<IntWritable, E>> newPartitionEdges =
          Int2ObjectMaps.synchronize(
              new Int2ObjectOpenHashMap<OutEdges<IntWritable, E>>());
      partitionEdges = (Int2ObjectMap<OutEdges<IntWritable, E>>)
          transientEdges.putIfAbsent(partitionId,
              newPartitionEdges);
      if (partitionEdges == null) {
        partitionEdges = newPartitionEdges;
      }
    }
    return partitionEdges;
  }

  @Override
  protected OutEdges<IntWritable, E> getVertexOutEdges(
      VertexIdEdgeIterator<IntWritable, E> vertexIdEdgeIterator,
      Map<Integer, OutEdges<IntWritable, E>> partitionEdgesIn) {
    Int2ObjectMap<OutEdges<IntWritable, E>> partitionEdges =
        (Int2ObjectMap<OutEdges<IntWritable, E>>) partitionEdgesIn;
    IntWritable vertexId = vertexIdEdgeIterator.getCurrentVertexId();
    OutEdges<IntWritable, E> outEdges = partitionEdges.get(vertexId.get());
    if (outEdges == null) {
      synchronized (partitionEdges) {
        outEdges = partitionEdges.get(vertexId.get());
        if (outEdges == null) {
          outEdges = configuration.createAndInitializeInputOutEdges();
          partitionEdges.put(vertexId.get(), outEdges);
        }
      }
    }
    return outEdges;
  }
}


File: giraph-core/src/main/java/org/apache/giraph/edge/primitives/LongEdgeStore.java
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

package org.apache.giraph.edge.primitives;

import org.apache.giraph.bsp.CentralizedServiceWorker;
import org.apache.giraph.conf.ImmutableClassesGiraphConfiguration;
import org.apache.giraph.edge.AbstractEdgeStore;
import org.apache.giraph.edge.OutEdges;
import org.apache.giraph.utils.VertexIdEdgeIterator;
import org.apache.hadoop.io.LongWritable;
import org.apache.hadoop.io.Writable;
import org.apache.hadoop.util.Progressable;

import it.unimi.dsi.fastutil.longs.Long2ObjectMap;
import it.unimi.dsi.fastutil.longs.Long2ObjectMaps;
import it.unimi.dsi.fastutil.longs.Long2ObjectOpenHashMap;

import java.util.Iterator;
import java.util.Map;

/**
 * Special edge store to be used when ids are LongWritable.
 * Uses fastutil primitive maps in order to decrease number of objects and
 * get better performance.
 *
 * @param <V> Vertex value
 * @param <E> Edge value
 */
public class LongEdgeStore<V extends Writable, E extends Writable>
  extends AbstractEdgeStore<LongWritable, V, E, Long,
  Long2ObjectMap.Entry<OutEdges<LongWritable, E>>> {

  /**
   * Constructor.
   *
   * @param service Service worker
   * @param configuration Configuration
   * @param progressable Progressable
   */
  public LongEdgeStore(
    CentralizedServiceWorker<LongWritable, V, E> service,
    ImmutableClassesGiraphConfiguration<LongWritable, V, E> configuration,
    Progressable progressable) {
    super(service, configuration, progressable);
  }

  @Override
  protected LongWritable getVertexId(
    Long2ObjectMap.Entry<OutEdges<LongWritable, E>> entry,
    LongWritable representativeVertexId) {
    representativeVertexId.set(entry.getLongKey());
    return representativeVertexId;
  }

  @Override
  protected LongWritable createVertexId(
    Long2ObjectMap.Entry<OutEdges<LongWritable, E>> entry) {
    return new LongWritable(entry.getLongKey());
  }


  @Override
  protected OutEdges<LongWritable, E> getPartitionEdges(
    Long2ObjectMap.Entry<OutEdges<LongWritable, E>> entry) {
    return entry.getValue();
  }

  @Override
  protected Iterator<Long2ObjectMap.Entry<OutEdges<LongWritable, E>>>
  getPartitionEdgesIterator(
      Map<Long, OutEdges<LongWritable, E>> partitionEdges) {
    return ((Long2ObjectMap<OutEdges<LongWritable, E>>) partitionEdges)
        .long2ObjectEntrySet()
        .iterator();
  }

  @Override
  protected Long2ObjectMap<OutEdges<LongWritable, E>> getPartitionEdges(
    int partitionId) {
    Long2ObjectMap<OutEdges<LongWritable, E>> partitionEdges =
      (Long2ObjectMap<OutEdges<LongWritable, E>>)
        transientEdges.get(partitionId);
    if (partitionEdges == null) {
      Long2ObjectMap<OutEdges<LongWritable, E>> newPartitionEdges =
          Long2ObjectMaps.synchronize(
              new Long2ObjectOpenHashMap<OutEdges<LongWritable, E>>());
      partitionEdges = (Long2ObjectMap<OutEdges<LongWritable, E>>)
          transientEdges.putIfAbsent(partitionId,
          newPartitionEdges);
      if (partitionEdges == null) {
        partitionEdges = newPartitionEdges;
      }
    }
    return partitionEdges;
  }

  @Override
  protected OutEdges<LongWritable, E> getVertexOutEdges(
    VertexIdEdgeIterator<LongWritable, E> vertexIdEdgeIterator,
    Map<Long, OutEdges<LongWritable, E>> partitionEdgesIn) {
    Long2ObjectMap<OutEdges<LongWritable, E>> partitionEdges =
        (Long2ObjectMap<OutEdges<LongWritable, E>>) partitionEdgesIn;
    LongWritable vertexId = vertexIdEdgeIterator.getCurrentVertexId();
    OutEdges<LongWritable, E> outEdges = partitionEdges.get(vertexId.get());
    if (outEdges == null) {
      synchronized (partitionEdges) {
        outEdges = partitionEdges.get(vertexId.get());
        if (outEdges == null) {
          outEdges = configuration.createAndInitializeInputOutEdges();
          partitionEdges.put(vertexId.get(), outEdges);
        }
      }
    }
    return outEdges;
  }
}


File: giraph-core/src/main/java/org/apache/giraph/graph/ComputeCallable.java
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
package org.apache.giraph.graph;

import java.io.IOException;
import java.util.Collection;
import java.util.List;
import java.util.concurrent.BlockingQueue;
import java.util.concurrent.Callable;

import org.apache.giraph.bsp.CentralizedServiceWorker;
import org.apache.giraph.comm.WorkerClientRequestProcessor;
import org.apache.giraph.comm.messages.MessageStore;
import org.apache.giraph.comm.netty.NettyWorkerClientRequestProcessor;
import org.apache.giraph.conf.ImmutableClassesGiraphConfiguration;
import org.apache.giraph.io.SimpleVertexWriter;
import org.apache.giraph.metrics.GiraphMetrics;
import org.apache.giraph.metrics.MetricNames;
import org.apache.giraph.metrics.SuperstepMetricsRegistry;
import org.apache.giraph.partition.Partition;
import org.apache.giraph.partition.PartitionStats;
import org.apache.giraph.time.SystemTime;
import org.apache.giraph.time.Time;
import org.apache.giraph.time.Times;
import org.apache.giraph.utils.MemoryUtils;
import org.apache.giraph.utils.TimedLogger;
import org.apache.giraph.utils.Trimmable;
import org.apache.giraph.worker.WorkerContext;
import org.apache.giraph.worker.WorkerProgress;
import org.apache.giraph.worker.WorkerThreadGlobalCommUsage;
import org.apache.hadoop.io.Writable;
import org.apache.hadoop.io.WritableComparable;
import org.apache.hadoop.mapreduce.Mapper;
import org.apache.log4j.Logger;

import com.google.common.collect.Iterables;
import com.google.common.collect.Lists;
import com.yammer.metrics.core.Counter;
import com.yammer.metrics.core.Histogram;

/**
 * Compute as many vertex partitions as possible.  Every thread will has its
 * own instance of WorkerClientRequestProcessor to send requests.  Note that
 * the partition ids are used in the partitionIdQueue rather than the actual
 * partitions since that would cause the partitions to be loaded into memory
 * when using the out-of-core graph partition store.  We should only load on
 * demand.
 *
 * @param <I> Vertex index value
 * @param <V> Vertex value
 * @param <E> Edge value
 * @param <M1> Incoming message type
 * @param <M2> Outgoing message type
 */
public class ComputeCallable<I extends WritableComparable, V extends Writable,
    E extends Writable, M1 extends Writable, M2 extends Writable>
    implements Callable<Collection<PartitionStats>> {
  /** Class logger */
  private static final Logger LOG  = Logger.getLogger(ComputeCallable.class);
  /** Class time object */
  private static final Time TIME = SystemTime.get();
  /** How often to update WorkerProgress */
  private static final long VERTICES_TO_UPDATE_PROGRESS = 100000;
  /** Context */
  private final Mapper<?, ?, ?, ?>.Context context;
  /** Graph state */
  private final GraphState graphState;
  /** Thread-safe queue of all partition ids */
  private final BlockingQueue<Integer> partitionIdQueue;
  /** Message store */
  private final MessageStore<I, M1> messageStore;
  /** Configuration */
  private final ImmutableClassesGiraphConfiguration<I, V, E> configuration;
  /** Worker (for NettyWorkerClientRequestProcessor) */
  private final CentralizedServiceWorker<I, V, E> serviceWorker;
  /** Dump some progress every 30 seconds */
  private final TimedLogger timedLogger = new TimedLogger(30 * 1000, LOG);
  /** VertexWriter for this ComputeCallable */
  private SimpleVertexWriter<I, V, E> vertexWriter;
  /** Get the start time in nanos */
  private final long startNanos = TIME.getNanoseconds();

  // Per-Superstep Metrics
  /** Messages sent */
  private final Counter messagesSentCounter;
  /** Message bytes sent */
  private final Counter messageBytesSentCounter;
  /** Compute time per partition */
  private final Histogram histogramComputePerPartition;

  /**
   * Constructor
   *
   * @param context Context
   * @param graphState Current graph state (use to create own graph state)
   * @param messageStore Message store
   * @param partitionIdQueue Queue of partition ids (thread-safe)
   * @param configuration Configuration
   * @param serviceWorker Service worker
   */
  public ComputeCallable(
      Mapper<?, ?, ?, ?>.Context context, GraphState graphState,
      MessageStore<I, M1> messageStore,
      BlockingQueue<Integer> partitionIdQueue,
      ImmutableClassesGiraphConfiguration<I, V, E> configuration,
      CentralizedServiceWorker<I, V, E> serviceWorker) {
    this.context = context;
    this.configuration = configuration;
    this.partitionIdQueue = partitionIdQueue;
    this.messageStore = messageStore;
    this.serviceWorker = serviceWorker;
    this.graphState = graphState;

    SuperstepMetricsRegistry metrics = GiraphMetrics.get().perSuperstep();
    messagesSentCounter = metrics.getCounter(MetricNames.MESSAGES_SENT);
    messageBytesSentCounter =
      metrics.getCounter(MetricNames.MESSAGE_BYTES_SENT);
    histogramComputePerPartition = metrics.getUniformHistogram(
        MetricNames.HISTOGRAM_COMPUTE_PER_PARTITION);
  }

  @Override
  public Collection<PartitionStats> call() {
    // Thread initialization (for locality)
    WorkerClientRequestProcessor<I, V, E> workerClientRequestProcessor =
        new NettyWorkerClientRequestProcessor<I, V, E>(
            context, configuration, serviceWorker,
            configuration.getOutgoingMessageEncodeAndStoreType().
              useOneMessageToManyIdsEncoding());
    WorkerThreadGlobalCommUsage aggregatorUsage =
        serviceWorker.getAggregatorHandler().newThreadAggregatorUsage();
    WorkerContext workerContext = serviceWorker.getWorkerContext();

    vertexWriter = serviceWorker.getSuperstepOutput().getVertexWriter();

    Computation<I, V, E, M1, M2> computation =
        (Computation<I, V, E, M1, M2>) configuration.createComputation();
    computation.initialize(graphState, workerClientRequestProcessor,
        serviceWorker.getGraphTaskManager(), aggregatorUsage, workerContext);
    computation.preSuperstep();

    List<PartitionStats> partitionStatsList = Lists.newArrayList();
    while (!partitionIdQueue.isEmpty()) {
      Integer partitionId = partitionIdQueue.poll();
      if (partitionId == null) {
        break;
      }

      long startTime = System.currentTimeMillis();
      Partition<I, V, E> partition =
          serviceWorker.getPartitionStore().getOrCreatePartition(partitionId);

      try {
        serviceWorker.getServerData().resolvePartitionMutation(partition);
        PartitionStats partitionStats =
            computePartition(computation, partition);
        partitionStatsList.add(partitionStats);
        long partitionMsgs = workerClientRequestProcessor.resetMessageCount();
        partitionStats.addMessagesSentCount(partitionMsgs);
        messagesSentCounter.inc(partitionMsgs);
        long partitionMsgBytes =
          workerClientRequestProcessor.resetMessageBytesCount();
        partitionStats.addMessageBytesSentCount(partitionMsgBytes);
        messageBytesSentCounter.inc(partitionMsgBytes);
        timedLogger.info("call: Completed " +
            partitionStatsList.size() + " partitions, " +
            partitionIdQueue.size() + " remaining " +
            MemoryUtils.getRuntimeMemoryStats());
      } catch (IOException e) {
        throw new IllegalStateException("call: Caught unexpected IOException," +
            " failing.", e);
      } catch (InterruptedException e) {
        throw new IllegalStateException("call: Caught unexpected " +
            "InterruptedException, failing.", e);
      } finally {
        serviceWorker.getPartitionStore().putPartition(partition);
      }

      histogramComputePerPartition.update(
          System.currentTimeMillis() - startTime);
    }

    computation.postSuperstep();

    // Return VertexWriter after the usage
    serviceWorker.getSuperstepOutput().returnVertexWriter(vertexWriter);

    if (LOG.isInfoEnabled()) {
      float seconds = Times.getNanosSince(TIME, startNanos) /
          Time.NS_PER_SECOND_AS_FLOAT;
      LOG.info("call: Computation took " + seconds + " secs for "  +
          partitionStatsList.size() + " partitions on superstep " +
          graphState.getSuperstep() + ".  Flushing started");
    }
    try {
      workerClientRequestProcessor.flush();
      // The messages flushed out from the cache is
      // from the last partition processed
      if (partitionStatsList.size() > 0) {
        long partitionMsgBytes =
          workerClientRequestProcessor.resetMessageBytesCount();
        partitionStatsList.get(partitionStatsList.size() - 1).
          addMessageBytesSentCount(partitionMsgBytes);
        messageBytesSentCounter.inc(partitionMsgBytes);
      }
      aggregatorUsage.finishThreadComputation();
    } catch (IOException e) {
      throw new IllegalStateException("call: Flushing failed.", e);
    }
    return partitionStatsList;
  }

  /**
   * Compute a single partition
   *
   * @param computation Computation to use
   * @param partition Partition to compute
   * @return Partition stats for this computed partition
   */
  private PartitionStats computePartition(
      Computation<I, V, E, M1, M2> computation,
      Partition<I, V, E> partition) throws IOException, InterruptedException {
    PartitionStats partitionStats =
        new PartitionStats(partition.getId(), 0, 0, 0, 0, 0);
    long verticesComputedProgress = 0;
    // Make sure this is thread-safe across runs
    synchronized (partition) {
      for (Vertex<I, V, E> vertex : partition) {
        Iterable<M1> messages = messageStore.getVertexMessages(vertex.getId());
        if (vertex.isHalted() && !Iterables.isEmpty(messages)) {
          vertex.wakeUp();
        }
        if (!vertex.isHalted()) {
          context.progress();
          computation.compute(vertex, messages);
          // Need to unwrap the mutated edges (possibly)
          vertex.unwrapMutableEdges();
          //Compact edges representation if possible
          if (vertex instanceof Trimmable) {
            ((Trimmable) vertex).trim();
          }
          // Write vertex to superstep output (no-op if it is not used)
          vertexWriter.writeVertex(vertex);
          // Need to save the vertex changes (possibly)
          partition.saveVertex(vertex);
        }
        if (vertex.isHalted()) {
          partitionStats.incrFinishedVertexCount();
        }
        // Remove the messages now that the vertex has finished computation
        messageStore.clearVertexMessages(vertex.getId());

        // Add statistics for this vertex
        partitionStats.incrVertexCount();
        partitionStats.addEdgeCount(vertex.getNumEdges());

        verticesComputedProgress++;
        if (verticesComputedProgress == VERTICES_TO_UPDATE_PROGRESS) {
          WorkerProgress.get().addVerticesComputed(verticesComputedProgress);
          verticesComputedProgress = 0;
        }
      }

      messageStore.clearPartition(partition.getId());
    }
    WorkerProgress.get().addVerticesComputed(verticesComputedProgress);
    WorkerProgress.get().incrementPartitionsComputed();
    return partitionStats;
  }
}



File: giraph-core/src/main/java/org/apache/giraph/graph/GraphTaskManager.java
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

package org.apache.giraph.graph;

import java.io.IOException;
import java.net.URL;
import java.net.URLDecoder;
import java.util.ArrayList;
import java.util.Collection;
import java.util.Enumeration;
import java.util.List;
import java.util.concurrent.ArrayBlockingQueue;
import java.util.concurrent.BlockingQueue;
import java.util.concurrent.Callable;
import java.util.concurrent.ExecutionException;
import java.util.concurrent.TimeUnit;

import org.apache.giraph.bsp.BspService;
import org.apache.giraph.bsp.CentralizedServiceMaster;
import org.apache.giraph.bsp.CentralizedServiceWorker;
import org.apache.giraph.bsp.checkpoints.CheckpointStatus;
import org.apache.giraph.comm.messages.MessageStore;
import org.apache.giraph.conf.ClassConfOption;
import org.apache.giraph.conf.GiraphConstants;
import org.apache.giraph.conf.ImmutableClassesGiraphConfiguration;
import org.apache.giraph.job.JobProgressTracker;
import org.apache.giraph.master.BspServiceMaster;
import org.apache.giraph.master.MasterThread;
import org.apache.giraph.metrics.GiraphMetrics;
import org.apache.giraph.metrics.GiraphMetricsRegistry;
import org.apache.giraph.metrics.GiraphTimer;
import org.apache.giraph.metrics.GiraphTimerContext;
import org.apache.giraph.metrics.ResetSuperstepMetricsObserver;
import org.apache.giraph.metrics.SuperstepMetricsRegistry;
import org.apache.giraph.partition.PartitionOwner;
import org.apache.giraph.partition.PartitionStats;
import org.apache.giraph.partition.PartitionStore;
import org.apache.giraph.scripting.ScriptLoader;
import org.apache.giraph.utils.CallableFactory;
import org.apache.giraph.utils.MemoryUtils;
import org.apache.giraph.utils.ProgressableUtils;
import org.apache.giraph.worker.BspServiceWorker;
import org.apache.giraph.worker.InputSplitsCallable;
import org.apache.giraph.worker.WorkerContext;
import org.apache.giraph.worker.WorkerObserver;
import org.apache.giraph.worker.WorkerProgress;
import org.apache.giraph.zk.ZooKeeperManager;
import org.apache.hadoop.conf.Configuration;
import org.apache.hadoop.fs.Path;
import org.apache.hadoop.io.Writable;
import org.apache.hadoop.io.WritableComparable;
import org.apache.hadoop.mapreduce.Mapper;
import org.apache.log4j.Appender;
import org.apache.log4j.Level;
import org.apache.log4j.LogManager;
import org.apache.log4j.Logger;
import org.apache.log4j.PatternLayout;

/**
 * The Giraph-specific business logic for a single BSP
 * compute node in whatever underlying type of cluster
 * our Giraph job will run on. Owning object will provide
 * the glue into the underlying cluster framework
 * and will call this object to perform Giraph work.
 *
 * @param <I> Vertex id
 * @param <V> Vertex data
 * @param <E> Edge data
 */
@SuppressWarnings("rawtypes")
public class GraphTaskManager<I extends WritableComparable, V extends Writable,
  E extends Writable> implements
  ResetSuperstepMetricsObserver {
/*if_not[PURE_YARN]
  static { // Eliminate this? Even MRv1 tasks should not need it here.
    Configuration.addDefaultResource("giraph-site.xml");
  }
end[PURE_YARN]*/
  /**
   * Class which checks if an exception on some thread should cause worker
   * to fail
   */
  public static final ClassConfOption<CheckerIfWorkerShouldFailAfterException>
  CHECKER_IF_WORKER_SHOULD_FAIL_AFTER_EXCEPTION_CLASS = ClassConfOption.create(
      "giraph.checkerIfWorkerShouldFailAfterExceptionClass",
      FailWithEveryExceptionOccurred.class,
      CheckerIfWorkerShouldFailAfterException.class,
      "Class which checks if an exception on some thread should cause worker " +
          "to fail, by default all exceptions cause failure");
  /** Name of metric for superstep time in msec */
  public static final String TIMER_SUPERSTEP_TIME = "superstep-time-ms";
  /** Name of metric for compute on all vertices in msec */
  public static final String TIMER_COMPUTE_ALL = "compute-all-ms";
  /** Name of metric for time from begin compute to first message sent */
  public static final String TIMER_TIME_TO_FIRST_MSG =
      "time-to-first-message-ms";
  /** Name of metric for time from first message till last message flushed */
  public static final String TIMER_COMMUNICATION_TIME = "communication-time-ms";

  /** Class logger */
  private static final Logger LOG = Logger.getLogger(GraphTaskManager.class);
  /** Coordination service worker */
  private CentralizedServiceWorker<I, V, E> serviceWorker;
  /** Coordination service master */
  private CentralizedServiceMaster<I, V, E> serviceMaster;
  /** Coordination service master thread */
  private Thread masterThread = null;
  /** The worker should be run exactly once, or else there is a problem. */
  private boolean alreadyRun = false;
  /** Manages the ZooKeeper servers if necessary (dynamic startup) */
  private ZooKeeperManager zkManager;
  /** Configuration */
  private ImmutableClassesGiraphConfiguration<I, V, E> conf;
  /** Already complete? */
  private boolean done = false;
  /** What kind of functions is this mapper doing? */
  private GraphFunctions graphFunctions = GraphFunctions.UNKNOWN;
  /** Superstep stats */
  private FinishedSuperstepStats finishedSuperstepStats =
      new FinishedSuperstepStats(0, false, 0, 0, false, CheckpointStatus.NONE);
  /** Job progress tracker */
  private JobProgressTrackerClient jobProgressTracker;

  // Per-Job Metrics
  /** Timer for WorkerContext#preApplication() */
  private GiraphTimer wcPreAppTimer;
  /** Timer for WorkerContext#postApplication() */
  private GiraphTimer wcPostAppTimer;

  // Per-Superstep Metrics
  /** Time for how long superstep took */
  private GiraphTimer superstepTimer;
  /** Time for all compute() calls in a superstep */
  private GiraphTimer computeAll;
  /** Time from starting compute to sending first message */
  private GiraphTimer timeToFirstMessage;
  /** Context for timing time to first message above */
  private GiraphTimerContext timeToFirstMessageTimerContext;
  /** Time from first sent message till last message flushed. */
  private GiraphTimer communicationTimer;
  /** Context for timing communication time above */
  private GiraphTimerContext communicationTimerContext;
  /** Timer for WorkerContext#preSuperstep() */
  private GiraphTimer wcPreSuperstepTimer;
  /** The Hadoop Mapper#Context for this job */
  private final Mapper<?, ?, ?, ?>.Context context;
  /** is this GraphTaskManager the master? */
  private boolean isMaster;

  /**
   * Default constructor for GiraphTaskManager.
   * @param context a handle to the underlying cluster framework.
   *                For Hadoop clusters, this is a Mapper#Context.
   */
  public GraphTaskManager(Mapper<?, ?, ?, ?>.Context context) {
    this.context = context;
    this.isMaster = false;
  }

  /**
   * Run the user's input checking code.
   */
  private void checkInput() {
    if (conf.hasEdgeInputFormat()) {
      conf.createWrappedEdgeInputFormat().checkInputSpecs(conf);
    }
    if (conf.hasVertexInputFormat()) {
      conf.createWrappedVertexInputFormat().checkInputSpecs(conf);
    }
  }

  /**
   * In order for job client to know which ZooKeeper the job is using,
   * we create a counter with server:port as its name inside of
   * ZOOKEEPER_SERVER_PORT_COUNTER_GROUP.
   *
   * @param serverPortList Server:port list for ZooKeeper used
   */
  private void createZooKeeperCounter(String serverPortList) {
    // Getting the counter will actually create it.
    context.getCounter(GiraphConstants.ZOOKEEPER_SERVER_PORT_COUNTER_GROUP,
        serverPortList);
  }

  /**
   * Called by owner of this GraphTaskManager on each compute node
   *
   * @param zkPathList the path to the ZK jars we need to run the job
   */
  public void setup(Path[] zkPathList)
    throws IOException, InterruptedException {
    context.setStatus("setup: Beginning worker setup.");
    Configuration hadoopConf = context.getConfiguration();
    conf = new ImmutableClassesGiraphConfiguration<I, V, E>(hadoopConf);
    initializeJobProgressTracker();
    // Write user's graph types (I,V,E,M) back to configuration parameters so
    // that they are set for quicker access later. These types are often
    // inferred from the Computation class used.
    conf.getGiraphTypes().writeIfUnset(conf);
    // configure global logging level for Giraph job
    initializeAndConfigureLogging();
    // init the metrics objects
    setupAndInitializeGiraphMetrics();
    // Check input
    checkInput();
    // Load any scripts that were deployed
    ScriptLoader.loadScripts(conf);
    // One time setup for computation factory
    conf.createComputationFactory().initialize(conf);
    // Do some task setup (possibly starting up a Zookeeper service)
    context.setStatus("setup: Initializing Zookeeper services.");
    String serverPortList = conf.getZookeeperList();
    if (serverPortList.isEmpty()) {
      if (startZooKeeperManager()) {
        return; // ZK connect/startup failed
      }
    } else {
      createZooKeeperCounter(serverPortList);
    }
    if (zkManager != null && zkManager.runsZooKeeper()) {
      if (LOG.isInfoEnabled()) {
        LOG.info("setup: Chosen to run ZooKeeper...");
      }
    }
    context
        .setStatus("setup: Connected to Zookeeper service " + serverPortList);
    this.graphFunctions = determineGraphFunctions(conf, zkManager);
    // Sometimes it takes a while to get multiple ZooKeeper servers up
    if (conf.getZooKeeperServerCount() > 1) {
      Thread.sleep(GiraphConstants.DEFAULT_ZOOKEEPER_INIT_LIMIT *
        GiraphConstants.DEFAULT_ZOOKEEPER_TICK_TIME);
    }
    try {
      instantiateBspService();
    } catch (IOException e) {
      LOG.error("setup: Caught exception just before end of setup", e);
      if (zkManager != null) {
        zkManager.offlineZooKeeperServers(ZooKeeperManager.State.FAILED);
      }
      throw new RuntimeException(
        "setup: Offlining servers due to exception...", e);
    }
    context.setStatus(getGraphFunctions().toString() + " starting...");
  }

  /**
   * Create and connect a client to JobProgressTrackerService,
   * or no-op implementation if progress shouldn't be tracked or something
   * goes wrong
   */
  private void initializeJobProgressTracker() {
    if (!conf.trackJobProgressOnClient()) {
      jobProgressTracker = new JobProgressTrackerClientNoOp();
    } else {
      try {
        jobProgressTracker = new RetryableJobProgressTrackerClient(conf);
      } catch (InterruptedException | ExecutionException e) {
        LOG.warn("createJobProgressClient: Exception occurred while trying to" +
            " connect to JobProgressTracker - not reporting progress", e);
        jobProgressTracker = new JobProgressTrackerClientNoOp();
      }
    }
    jobProgressTracker.mapperStarted();
  }

  /**
  * Perform the work assigned to this compute node for this job run.
  * 1) Run checkpoint per frequency policy.
  * 2) For every vertex on this mapper, run the compute() function
  * 3) Wait until all messaging is done.
  * 4) Check if all vertices are done.  If not goto 2).
  * 5) Dump output.
  */
  public void execute() throws IOException, InterruptedException {
    if (checkTaskState()) {
      return;
    }
    preLoadOnWorkerObservers();
    finishedSuperstepStats = serviceWorker.setup();
    if (collectInputSuperstepStats(finishedSuperstepStats)) {
      return;
    }
    prepareGraphStateAndWorkerContext();
    List<PartitionStats> partitionStatsList = new ArrayList<PartitionStats>();
    int numComputeThreads = conf.getNumComputeThreads();

    // main superstep processing loop
    while (!finishedSuperstepStats.allVerticesHalted()) {
      final long superstep = serviceWorker.getSuperstep();
      GiraphTimerContext superstepTimerContext =
        getTimerForThisSuperstep(superstep);
      GraphState graphState = new GraphState(superstep,
          finishedSuperstepStats.getVertexCount(),
          finishedSuperstepStats.getEdgeCount(),
          context);
      Collection<? extends PartitionOwner> masterAssignedPartitionOwners =
        serviceWorker.startSuperstep();
      if (LOG.isDebugEnabled()) {
        LOG.debug("execute: " + MemoryUtils.getRuntimeMemoryStats());
      }
      context.progress();
      serviceWorker.exchangeVertexPartitions(masterAssignedPartitionOwners);
      context.progress();
      boolean hasBeenRestarted = checkSuperstepRestarted(superstep);

      GlobalStats globalStats = serviceWorker.getGlobalStats();

      if (hasBeenRestarted) {
        graphState = new GraphState(superstep,
            finishedSuperstepStats.getVertexCount(),
            finishedSuperstepStats.getEdgeCount(),
            context);
      } else if (storeCheckpoint(globalStats.getCheckpointStatus())) {
        break;
      }
      serviceWorker.getServerData().prepareResolveMutations();
      context.progress();
      prepareForSuperstep(graphState);
      context.progress();
      MessageStore<I, Writable> messageStore =
        serviceWorker.getServerData().getCurrentMessageStore();
      int numPartitions = serviceWorker.getPartitionStore().getNumPartitions();
      int numThreads = Math.min(numComputeThreads, numPartitions);
      if (LOG.isInfoEnabled()) {
        LOG.info("execute: " + numPartitions + " partitions to process with " +
          numThreads + " compute thread(s), originally " +
          numComputeThreads + " thread(s) on superstep " + superstep);
      }
      partitionStatsList.clear();
      // execute the current superstep
      if (numPartitions > 0) {
        processGraphPartitions(context, partitionStatsList, graphState,
          messageStore, numPartitions, numThreads);
      }
      finishedSuperstepStats = completeSuperstepAndCollectStats(
        partitionStatsList, superstepTimerContext);

      // END of superstep compute loop
    }

    if (LOG.isInfoEnabled()) {
      LOG.info("execute: BSP application done (global vertices marked done)");
    }
    updateSuperstepGraphState();
    postApplication();
  }

  /**
   * Handle post-application callbacks.
   */
  private void postApplication() throws IOException, InterruptedException {
    GiraphTimerContext postAppTimerContext = wcPostAppTimer.time();
    serviceWorker.getWorkerContext().postApplication();
    serviceWorker.getSuperstepOutput().postApplication();
    postAppTimerContext.stop();
    context.progress();

    for (WorkerObserver obs : serviceWorker.getWorkerObservers()) {
      obs.postApplication();
      context.progress();
    }
  }

  /**
   * Sets the "isMaster" flag for final output commit to happen on master.
   * @param im the boolean input to set isMaster. Applies to "pure YARN only"
   */
  public void setIsMaster(final boolean im) {
    this.isMaster = im;
  }

  /**
   * Get "isMaster" status flag -- we need to know if we're the master in the
   * "finally" block of our GiraphYarnTask#execute() to commit final job output.
   * @return true if this task IS the master.
   */
  public boolean isMaster() {
    return isMaster;
  }

  /**
   * Produce a reference to the "start" superstep timer for the current
   * superstep.
   * @param superstep the current superstep count
   * @return a GiraphTimerContext representing the "start" of the supestep
   */
  private GiraphTimerContext getTimerForThisSuperstep(long superstep) {
    GiraphMetrics.get().resetSuperstepMetrics(superstep);
    return superstepTimer.time();
  }

  /**
   * Utility to encapsulate Giraph metrics setup calls
   */
  private void setupAndInitializeGiraphMetrics() {
    GiraphMetrics.init(conf);
    GiraphMetrics.get().addSuperstepResetObserver(this);
    initJobMetrics();
    MemoryUtils.initMetrics();
    InputSplitsCallable.initMetrics();
  }

  /**
   * Instantiate and configure ZooKeeperManager for this job. This will
   * result in a Giraph-owned Zookeeper instance, a connection to an
   * existing quorum as specified in the job configuration, or task failure
   * @return true if this task should terminate
   */
  private boolean startZooKeeperManager()
    throws IOException, InterruptedException {
    zkManager = new ZooKeeperManager(context, conf);
    context.setStatus("setup: Setting up Zookeeper manager.");
    zkManager.setup();
    if (zkManager.computationDone()) {
      done = true;
      return true;
    }
    zkManager.onlineZooKeeperServers();
    String serverPortList = zkManager.getZooKeeperServerPortString();
    conf.setZookeeperList(serverPortList);
    createZooKeeperCounter(serverPortList);
    return false;
  }

  /**
   * Utility to place a new, updated GraphState object into the serviceWorker.
   */
  private void updateSuperstepGraphState() {
    serviceWorker.getWorkerContext().setGraphState(
        new GraphState(serviceWorker.getSuperstep(),
            finishedSuperstepStats.getVertexCount(),
            finishedSuperstepStats.getEdgeCount(), context));
  }

  /**
   * Utility function for boilerplate updates and cleanup done at the
   * end of each superstep processing loop in the <code>execute</code> method.
   * @param partitionStatsList list of stas for each superstep to append to
   * @param superstepTimerContext for job metrics
   * @return the collected stats at the close of the current superstep.
   */
  private FinishedSuperstepStats completeSuperstepAndCollectStats(
    List<PartitionStats> partitionStatsList,
    GiraphTimerContext superstepTimerContext) {

    // the superstep timer is stopped inside the finishSuperstep function
    // (otherwise metrics are not available at the end of the computation
    //  using giraph.metrics.enable=true).
    finishedSuperstepStats =
      serviceWorker.finishSuperstep(partitionStatsList, superstepTimerContext);
    if (conf.metricsEnabled()) {
      GiraphMetrics.get().perSuperstep().printSummary(System.err);
    }
    return finishedSuperstepStats;
  }

  /**
   * Utility function to prepare various objects managing BSP superstep
   * operations for the next superstep.
   * @param graphState graph state metadata object
   */
  private void prepareForSuperstep(GraphState graphState) {
    serviceWorker.prepareSuperstep();

    serviceWorker.getWorkerContext().setGraphState(graphState);
    serviceWorker.getWorkerContext().setupSuperstep(serviceWorker);
    GiraphTimerContext preSuperstepTimer = wcPreSuperstepTimer.time();
    serviceWorker.getWorkerContext().preSuperstep();
    preSuperstepTimer.stop();
    context.progress();

    for (WorkerObserver obs : serviceWorker.getWorkerObservers()) {
      obs.preSuperstep(graphState.getSuperstep());
      context.progress();
    }
  }

  /**
   * Prepare graph state and worker context for superstep cycles.
   */
  private void prepareGraphStateAndWorkerContext() {
    updateSuperstepGraphState();
    workerContextPreApp();
  }

  /**
    * Get the worker function enum.
    *
    * @return an enum detailing the roles assigned to this
    *         compute node for this Giraph job.
    */
  public GraphFunctions getGraphFunctions() {
    return graphFunctions;
  }

  public final WorkerContext getWorkerContext() {
    return serviceWorker.getWorkerContext();
  }

  public JobProgressTracker getJobProgressTracker() {
    return jobProgressTracker;
  }

  /**
   * Copied from JobConf to get the location of this jar.  Workaround for
   * things like Oozie map-reduce jobs. NOTE: Pure YARN profile cannot
   * make use of this, as the jars are unpacked at each container site.
   *
   * @param myClass Class to search the class loader path for to locate
   *        the relevant jar file
   * @return Location of the jar file containing myClass
   */
  private static String findContainingJar(Class<?> myClass) {
    ClassLoader loader = myClass.getClassLoader();
    String classFile =
        myClass.getName().replaceAll("\\.", "/") + ".class";
    try {
      for (Enumeration<?> itr = loader.getResources(classFile);
          itr.hasMoreElements();) {
        URL url = (URL) itr.nextElement();
        if ("jar".equals(url.getProtocol())) {
          String toReturn = url.getPath();
          if (toReturn.startsWith("file:")) {
            toReturn = toReturn.substring("file:".length());
          }
          toReturn = URLDecoder.decode(toReturn, "UTF-8");
          return toReturn.replaceAll("!.*$", "");
        }
      }
    } catch (IOException e) {
      throw new RuntimeException(e);
    }
    return null;
  }

  /**
   * Figure out what roles this BSP compute node should take on in the job.
   * Basic logic is as follows:
   * 1) If not split master, everyone does the everything and/or running
   *    ZooKeeper.
   * 2) If split master/worker, masters also run ZooKeeper
   *
   * 3) If split master/worker == true and <code>giraph.zkList</code> is
   *    externally provided, the master will not instantiate a ZK instance, but
   *    will assume a quorum is already active on the cluster for Giraph to use.
   *
   * @param conf Configuration to use
   * @param zkManager ZooKeeper manager to help determine whether to run
   *        ZooKeeper.
   * @return Functions that this mapper should do.
   */
  private static GraphFunctions determineGraphFunctions(
      ImmutableClassesGiraphConfiguration conf,
      ZooKeeperManager zkManager) {
    boolean splitMasterWorker = conf.getSplitMasterWorker();
    int taskPartition = conf.getTaskPartition();
    boolean zkAlreadyProvided = conf.isZookeeperExternal();
    GraphFunctions functions = GraphFunctions.UNKNOWN;
    // What functions should this mapper do?
    if (!splitMasterWorker) {
      if ((zkManager != null) && zkManager.runsZooKeeper()) {
        functions = GraphFunctions.ALL;
      } else {
        functions = GraphFunctions.ALL_EXCEPT_ZOOKEEPER;
      }
    } else {
      if (zkAlreadyProvided) {
        int masterCount = conf.getZooKeeperServerCount();
        if (taskPartition < masterCount) {
          functions = GraphFunctions.MASTER_ONLY;
        } else {
          functions = GraphFunctions.WORKER_ONLY;
        }
      } else {
        if ((zkManager != null) && zkManager.runsZooKeeper()) {
          functions = GraphFunctions.MASTER_ZOOKEEPER_ONLY;
        } else {
          functions = GraphFunctions.WORKER_ONLY;
        }
      }
    }
    return functions;
  }

  /**
   * Instantiate the appropriate BspService object (Master or Worker)
   * for this compute node.
   */
  private void instantiateBspService()
    throws IOException, InterruptedException {
    if (graphFunctions.isMaster()) {
      if (LOG.isInfoEnabled()) {
        LOG.info("setup: Starting up BspServiceMaster " +
          "(master thread)...");
      }
      serviceMaster = new BspServiceMaster<I, V, E>(context, this);
      masterThread = new MasterThread<I, V, E>(serviceMaster, context);
      masterThread.start();
    }
    if (graphFunctions.isWorker()) {
      if (LOG.isInfoEnabled()) {
        LOG.info("setup: Starting up BspServiceWorker...");
      }
      serviceWorker = new BspServiceWorker<I, V, E>(context, this);
      if (LOG.isInfoEnabled()) {
        LOG.info("setup: Registering health of this worker...");
      }
    }
  }

  /**
   * Initialize the root logger and appender to the settings in conf.
   */
  private void initializeAndConfigureLogging() {
    // Set the log level
    String logLevel = conf.getLocalLevel();
    if (!Logger.getRootLogger().getLevel().equals(Level.toLevel(logLevel))) {
      Logger.getRootLogger().setLevel(Level.toLevel(logLevel));
      if (LOG.isInfoEnabled()) {
        LOG.info("setup: Set log level to " + logLevel);
      }
    } else {
      if (LOG.isInfoEnabled()) {
        LOG.info("setup: Log level remains at " + logLevel);
      }
    }
    // Sets pattern layout for all appenders
    if (conf.useLogThreadLayout()) {
      PatternLayout layout =
        new PatternLayout("%-7p %d [%t] %c %x - %m%n");
      Enumeration<Appender> appenderEnum =
        Logger.getRootLogger().getAllAppenders();
      while (appenderEnum.hasMoreElements()) {
        appenderEnum.nextElement().setLayout(layout);
      }
    }
    // Change ZooKeeper logging level to error (info is quite verbose) for
    // testing only
    if (conf.getLocalTestMode()) {
      LogManager.getLogger(org.apache.zookeeper.server.PrepRequestProcessor.
          class.getName()).setLevel(Level.ERROR);
    }
  }

  /**
   * Initialize job-level metrics used by this class.
   */
  private void initJobMetrics() {
    GiraphMetricsRegistry jobMetrics = GiraphMetrics.get().perJobOptional();
    wcPreAppTimer = new GiraphTimer(jobMetrics, "worker-context-pre-app",
        TimeUnit.MILLISECONDS);
    wcPostAppTimer = new GiraphTimer(jobMetrics, "worker-context-post-app",
        TimeUnit.MILLISECONDS);
  }

  @Override
  public void newSuperstep(SuperstepMetricsRegistry superstepMetrics) {
    superstepTimer = new GiraphTimer(superstepMetrics,
        TIMER_SUPERSTEP_TIME, TimeUnit.MILLISECONDS);
    computeAll = new GiraphTimer(superstepMetrics,
        TIMER_COMPUTE_ALL, TimeUnit.MILLISECONDS);
    timeToFirstMessage = new GiraphTimer(superstepMetrics,
        TIMER_TIME_TO_FIRST_MSG, TimeUnit.MICROSECONDS);
    communicationTimer = new GiraphTimer(superstepMetrics,
        TIMER_COMMUNICATION_TIME, TimeUnit.MILLISECONDS);
    wcPreSuperstepTimer = new GiraphTimer(superstepMetrics,
        "worker-context-pre-superstep", TimeUnit.MILLISECONDS);
  }

  /**
   * Notification from Vertex that a message has been sent.
   */
  public void notifySentMessages() {
    // We are tracking the time between when the compute started and the first
    // message get sent. We use null to flag that we have already recorded it.
    GiraphTimerContext tmp = timeToFirstMessageTimerContext;
    if (tmp != null) {
      synchronized (timeToFirstMessage) {
        if (timeToFirstMessageTimerContext != null) {
          timeToFirstMessageTimerContext.stop();
          timeToFirstMessageTimerContext = null;
          communicationTimerContext = communicationTimer.time();
        }
      }
    }
  }

  /**
   * Notification of last message flushed. Comes when we finish the superstep
   * and are done waiting for all messages to send.
   */
  public void notifyFinishedCommunication() {
    GiraphTimerContext tmp = communicationTimerContext;
    if (tmp != null) {
      synchronized (communicationTimer) {
        if (communicationTimerContext != null) {
          communicationTimerContext.stop();
          communicationTimerContext = null;
        }
      }
    }
  }

  /**
   * Process graph data partitions active in this superstep.
   * @param context handle to the underlying cluster framework
   * @param partitionStatsList to pick up this superstep's processing stats
   * @param graphState the BSP graph state
   * @param messageStore the messages to be processed in this superstep
   * @param numPartitions the number of data partitions (vertices) to process
   * @param numThreads number of concurrent threads to do processing
   */
  private void processGraphPartitions(final Mapper<?, ?, ?, ?>.Context context,
      List<PartitionStats> partitionStatsList,
      final GraphState graphState,
      final MessageStore<I, Writable> messageStore,
      int numPartitions,
      int numThreads) {
    final BlockingQueue<Integer> computePartitionIdQueue =
      new ArrayBlockingQueue<Integer>(numPartitions);
    long verticesToCompute = 0;
    PartitionStore<I, V, E> partitionStore = serviceWorker.getPartitionStore();
    for (Integer partitionId : partitionStore.getPartitionIds()) {
      computePartitionIdQueue.add(partitionId);
      verticesToCompute += partitionStore.getPartitionVertexCount(partitionId);
    }
    WorkerProgress.get().startSuperstep(
        serviceWorker.getSuperstep(), verticesToCompute,
        serviceWorker.getPartitionStore().getNumPartitions());

    GiraphTimerContext computeAllTimerContext = computeAll.time();
    timeToFirstMessageTimerContext = timeToFirstMessage.time();

    CallableFactory<Collection<PartitionStats>> callableFactory =
      new CallableFactory<Collection<PartitionStats>>() {
        @Override
        public Callable<Collection<PartitionStats>> newCallable(
            int callableId) {
          return new ComputeCallable<I, V, E, Writable, Writable>(
              context,
              graphState,
              messageStore,
              computePartitionIdQueue,
              conf,
              serviceWorker);
        }
      };
    List<Collection<PartitionStats>> results =
        ProgressableUtils.getResultsWithNCallables(callableFactory, numThreads,
            "compute-%d", context);

    for (Collection<PartitionStats> result : results) {
      partitionStatsList.addAll(result);
    }

    computeAllTimerContext.stop();
  }

  /**
   * Handle the event that this superstep is a restart of a failed one.
   * @param superstep current superstep
   * @return the graph state, updated if this is a restart superstep
   */
  private boolean checkSuperstepRestarted(long superstep) throws IOException {
    // Might need to restart from another superstep
    // (manually or automatic), or store a checkpoint
    if (serviceWorker.getRestartedSuperstep() == superstep) {
      if (LOG.isInfoEnabled()) {
        LOG.info("execute: Loading from checkpoint " + superstep);
      }
      VertexEdgeCount vertexEdgeCount = serviceWorker.loadCheckpoint(
        serviceWorker.getRestartedSuperstep());
      finishedSuperstepStats = new FinishedSuperstepStats(0, false,
          vertexEdgeCount.getVertexCount(), vertexEdgeCount.getEdgeCount(),
          false, CheckpointStatus.NONE);
      return true;
    }
    return false;
  }

  /**
   * Check if it's time to checkpoint and actually does checkpointing
   * if it is.
   * @param checkpointStatus master's decision
   * @return true if we need to stop computation after checkpoint
   * @throws IOException
   */
  private boolean storeCheckpoint(CheckpointStatus checkpointStatus)
    throws IOException {
    if (checkpointStatus != CheckpointStatus.NONE) {
      serviceWorker.storeCheckpoint();
    }
    return checkpointStatus == CheckpointStatus.CHECKPOINT_AND_HALT;
  }

  /**
   * Attempt to collect the final statistics on the graph data
   * processed in this superstep by this compute node
   * @param inputSuperstepStats the final graph data stats object for the
   *                            input superstep
   * @return true if the graph data has no vertices (error?) and
   *         this node should terminate
   */
  private boolean collectInputSuperstepStats(
    FinishedSuperstepStats inputSuperstepStats) {
    if (inputSuperstepStats.getVertexCount() == 0 &&
        !inputSuperstepStats.mustLoadCheckpoint()) {
      LOG.warn("map: No vertices in the graph, exiting.");
      return true;
    }
    if (conf.metricsEnabled()) {
      GiraphMetrics.get().perSuperstep().printSummary(System.err);
    }
    return false;
  }

  /**
   * Did the state of this compute node change?
   * @return true if the processing of supersteps should terminate.
   */
  private boolean checkTaskState() {
    if (done) {
      return true;
    }
    GiraphMetrics.get().resetSuperstepMetrics(BspService.INPUT_SUPERSTEP);
    if (graphFunctions.isNotAWorker()) {
      if (LOG.isInfoEnabled()) {
        LOG.info("map: No need to do anything when not a worker");
      }
      return true;
    }
    if (alreadyRun) {
      throw new RuntimeException("map: In BSP, map should have only been" +
        " run exactly once, (already run)");
    }
    alreadyRun = true;
    return false;
  }

  /**
   * Call to the WorkerContext before application begins.
   */
  private void workerContextPreApp() {
    GiraphTimerContext preAppTimerContext = wcPreAppTimer.time();
    try {
      serviceWorker.getWorkerContext().preApplication();
    } catch (InstantiationException e) {
      LOG.fatal("execute: preApplication failed in instantiation", e);
      throw new RuntimeException(
          "execute: preApplication failed in instantiation", e);
    } catch (IllegalAccessException e) {
      LOG.fatal("execute: preApplication failed in access", e);
      throw new RuntimeException(
          "execute: preApplication failed in access", e);
    }
    preAppTimerContext.stop();
    context.progress();

    for (WorkerObserver obs : serviceWorker.getWorkerObservers()) {
      obs.preApplication();
      context.progress();
    }
  }

  /**
   * Executes preLoad() on worker observers.
   */
  private void preLoadOnWorkerObservers() {
    for (WorkerObserver obs : serviceWorker.getWorkerObservers()) {
      obs.preLoad();
      context.progress();
    }
  }

  /**
   * Executes postSave() on worker observers.
   */
  private void postSaveOnWorkerObservers() {
    for (WorkerObserver obs : serviceWorker.getWorkerObservers()) {
      obs.postSave();
      context.progress();
    }
  }

  /**
   * Called by owner of this GraphTaskManager object on each compute node
   */
  public void cleanup()
    throws IOException, InterruptedException {
    if (LOG.isInfoEnabled()) {
      LOG.info("cleanup: Starting for " + getGraphFunctions());
    }
    jobProgressTracker.cleanup();
    if (done) {
      return;
    }

    if (serviceWorker != null) {
      serviceWorker.cleanup(finishedSuperstepStats);
      postSaveOnWorkerObservers();
    }
    try {
      if (masterThread != null) {
        masterThread.join();
        LOG.info("cleanup: Joined with master thread");
      }
    } catch (InterruptedException e) {
      // cleanup phase -- just log the error
      LOG.error("cleanup: Master thread couldn't join");
    }
    if (zkManager != null) {
      LOG.info("cleanup: Offlining ZooKeeper servers");
      try {
        zkManager.offlineZooKeeperServers(ZooKeeperManager.State.FINISHED);
      // We need this here cause apparently exceptions are eaten by Hadoop
      // when they come from the cleanup lifecycle and it's useful to know
      // if something is wrong.
      //
      // And since it's cleanup nothing too bad should happen if we don't
      // propagate and just allow the job to finish normally.
      // CHECKSTYLE: stop IllegalCatch
      } catch (Throwable e) {
      // CHECKSTYLE: resume IllegalCatch
        LOG.error("cleanup: Error offlining zookeeper", e);
      }
    }

    // Stop tracking metrics
    GiraphMetrics.get().shutdown();
  }

  /**
   * Cleanup a ZooKeeper instance managed by this
   * GiraphWorker upon job run failure.
   */
  public void zooKeeperCleanup() {
    if (graphFunctions.isZooKeeper()) {
      // ZooKeeper may have had an issue
      if (zkManager != null) {
        zkManager.cleanup();
      }
    }
  }

  /**
   * Cleanup all of Giraph's framework-agnostic resources
   * regardless of which type of cluster Giraph is running on.
   */
  public void workerFailureCleanup() {
    try {
      if (graphFunctions.isWorker()) {
        serviceWorker.failureCleanup();
      }
      // Stop tracking metrics
      GiraphMetrics.get().shutdown();
    // Checkstyle exception due to needing to get the original
    // exception on failure
    // CHECKSTYLE: stop IllegalCatch
    } catch (RuntimeException e1) {
    // CHECKSTYLE: resume IllegalCatch
      LOG.error("run: Worker failure failed on another RuntimeException, " +
          "original expection will be rethrown", e1);
    }
  }

  /**
   * Creates exception handler that will terminate process gracefully in case
   * of any uncaught exception.
   * @return new exception handler object.
   */
  public Thread.UncaughtExceptionHandler createUncaughtExceptionHandler() {
    return new OverrideExceptionHandler(
        CHECKER_IF_WORKER_SHOULD_FAIL_AFTER_EXCEPTION_CLASS.newInstance(
            getConf()));
  }

  public ImmutableClassesGiraphConfiguration<I, V, E> getConf() {
    return conf;
  }


  /**
   * Default handler for uncaught exceptions.
   * It will do the best to clean up and then will terminate current giraph job.
   */
  class OverrideExceptionHandler implements Thread.UncaughtExceptionHandler {
    /** Checker if worker should fail after a thread gets an exception */
    private final CheckerIfWorkerShouldFailAfterException checker;

    /**
     * Constructor
     *
     * @param checker Checker if worker should fail after a thread gets an
     *                exception
     */
    public OverrideExceptionHandler(
        CheckerIfWorkerShouldFailAfterException checker) {
      this.checker = checker;
    }

    @Override
    public void uncaughtException(final Thread t, final Throwable e) {
      if (!checker.checkIfWorkerShouldFail(t, e)) {
        return;
      }
      try {
        LOG.fatal(
            "uncaughtException: OverrideExceptionHandler on thread " +
                t.getName() + ", msg = " +  e.getMessage() + ", exiting...", e);

        zooKeeperCleanup();
        workerFailureCleanup();
      } finally {
        System.exit(1);
      }
    }
  }

  /**
   * Interface to check if worker should fail after a thread gets an exception
   */
  public interface CheckerIfWorkerShouldFailAfterException {
    /**
     * Check if worker should fail after a thread gets an exception
     *
     * @param thread Thread which raised the exception
     * @param exception Exception which occurred
     * @return True iff worker should fail after this exception
     */
    boolean checkIfWorkerShouldFail(Thread thread, Throwable exception);
  }

  /**
   * Class to use by default, where each exception causes job failure
   */
  public static class FailWithEveryExceptionOccurred
      implements CheckerIfWorkerShouldFailAfterException {
    @Override
    public boolean checkIfWorkerShouldFail(Thread thread, Throwable exception) {
      return true;
    }
  }
}


File: giraph-core/src/main/java/org/apache/giraph/partition/DiskBackedPartitionStore.java
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

package org.apache.giraph.partition;

import static org.apache.giraph.conf.GiraphConstants.MAX_PARTITIONS_IN_MEMORY;
import static org.apache.giraph.conf.GiraphConstants.MAX_STICKY_PARTITIONS;
import static org.apache.giraph.conf.GiraphConstants.NUM_COMPUTE_THREADS;
import static org.apache.giraph.conf.GiraphConstants.NUM_INPUT_THREADS;
import static org.apache.giraph.conf.GiraphConstants.NUM_OUTPUT_THREADS;
import static org.apache.giraph.conf.GiraphConstants.PARTITIONS_DIRECTORY;

import java.io.BufferedInputStream;
import java.io.BufferedOutputStream;
import java.io.DataInput;
import java.io.DataInputStream;
import java.io.DataOutput;
import java.io.DataOutputStream;
import java.io.File;
import java.io.FileInputStream;
import java.io.FileOutputStream;
import java.io.IOException;
import java.util.Iterator;
import java.util.Map;
import java.util.Map.Entry;
import java.util.concurrent.ConcurrentMap;
import java.util.concurrent.atomic.AtomicInteger;
import java.util.concurrent.atomic.AtomicLong;

import org.apache.giraph.bsp.CentralizedServiceWorker;
import org.apache.giraph.conf.ImmutableClassesGiraphConfiguration;
import org.apache.giraph.edge.OutEdges;
import org.apache.giraph.graph.Vertex;
import org.apache.hadoop.io.Writable;
import org.apache.hadoop.io.WritableComparable;
import org.apache.hadoop.mapreduce.Mapper;
import org.apache.hadoop.mapreduce.Mapper.Context;
import org.apache.log4j.Logger;

import com.google.common.collect.Iterables;
import com.google.common.collect.Maps;
import com.google.common.hash.HashFunction;
import com.google.common.hash.Hashing;

/**
 * Disk-backed PartitionStore. Partitions are stored in memory on a LRU basis.
 * The operations are thread-safe, and guarantees safety for concurrent
 * execution of different operations on each partition.<br />
 * <br />
 * The algorithm implemented by this class is quite intricate due to the
 * interaction of several locks to guarantee performance. For this reason, here
 * follows an overview of the implemented algorithm.<br />
 * <b>ALGORITHM</b>:
 * In general, the partition store keeps N partitions in memory. To improve
 * I/O performance, part of the N partitions are kept in memory in a sticky
 * manner while preserving the capability of each thread to swap partitions on
 * the disk. This means that, for T threads, at least T partitions must remain
 * non-sticky. The number of sicky partitions can also be specified manually.
 * <b>CONCURRENCY</b>:
 * <ul>
 *   <li>
 *     <b>Meta Partition Lock</b>.All the partitions are held in a
 *     container, called the MetaPartition. This object contains also meta
 *     information about the partition. All these objects are used to
 *     atomically operate on partitions. In fact, each time a thread accesses
 *     a partition, it will firstly acquire a lock on the container,
 *     guaranteeing exclusion in managing the partition. Besides, this
 *     partition-based lock allows the threads to concurrently operate on
 *     different partitions, guaranteeing performance.
 *   </li>
 *   <li>
 *     <b>Meta Partition Container</b>. All the references to the meta
 *     partition objects are kept in a concurrent hash map. This ADT guarantees
 *     performance and atomic access to each single reference, which is then
 *     use for atomic operations on partitions, as previously described.
 *   </li>
 *   <li>
 *     <b>LRU Lock</b>. Finally, an additional ADT is used to keep the LRU
 *     order of unused partitions. In this case, the ADT is not thread safe and
 *     to guarantee safety, we use its intrinsic lock. Additionally, this lock
 *     is used for all in memory count changes. In fact, the amount of elements
 *     in memory and the inactive partitions are very strictly related and this
 *     justifies the sharing of the same lock.
 *   </li>
 * </ul>
 * <b>XXX</b>:<br/>
 * while most of the concurrent behaviors are gracefully handled, the
 * concurrent call of {@link #getOrCreatePartition(Integer partitionId)} and
 * {@link #deletePartition(Integer partitionId)} need yet to be handled. Since
 * the usage of this class does not currently incure in this type of concurrent
 * behavior, it has been left as a future work.
 *
 * @param <I> Vertex id
 * @param <V> Vertex data
 * @param <E> Edge data
 */
@SuppressWarnings("rawtypes")
public class DiskBackedPartitionStore<I extends WritableComparable,
    V extends Writable, E extends Writable>
    extends PartitionStore<I, V, E> {
  /** Class logger. */
  private static final Logger LOG =
      Logger.getLogger(DiskBackedPartitionStore.class);
  /** States the partition can be found in */
  private enum State { INIT, ACTIVE, INACTIVE, ONDISK };

  /** Hash map containing all the partitions  */
  private final ConcurrentMap<Integer, MetaPartition> partitions =
    Maps.newConcurrentMap();
  /** Inactive partitions to re-activate or spill to disk to make space */
  private final Map<Integer, MetaPartition> lru = Maps.newLinkedHashMap();

  /** Giraph configuration */
  private final
  ImmutableClassesGiraphConfiguration<I, V, E> conf;
  /** Mapper context */
  private final Context context;
  /** Base path where the partition files are written to */
  private final String[] basePaths;
  /** Used to hash partition Ids */
  private final HashFunction hasher = Hashing.murmur3_32();
  /** Maximum number of slots. Read-only value, no need for concurrency
      safety. */
  private final int maxPartitionsInMem;
  /** Number of slots used */
  private AtomicInteger numPartitionsInMem;
  /** service worker reference */
  private CentralizedServiceWorker<I, V, E> serviceWorker;
  /** mumber of slots that are always kept in memory */
  private AtomicLong numOfStickyPartitions;
  /** counter */
  private long passedThroughEdges;

  /**
   * Constructor
   *
   * @param conf Configuration
   * @param context Context
   * @param serviceWorker service worker reference
   */
  public DiskBackedPartitionStore(
      ImmutableClassesGiraphConfiguration<I, V, E> conf,
      Mapper<?, ?, ?, ?>.Context context,
      CentralizedServiceWorker<I, V, E> serviceWorker) {
    this.conf = conf;
    this.context = context;
    this.serviceWorker = serviceWorker;

    this.passedThroughEdges = 0;
    this.numPartitionsInMem = new AtomicInteger(0);

    // We must be able to hold at least one partition in memory
    this.maxPartitionsInMem = Math.max(MAX_PARTITIONS_IN_MEMORY.get(conf), 1);

    int numInputThreads = NUM_INPUT_THREADS.get(conf);
    int numComputeThreads = NUM_COMPUTE_THREADS.get(conf);
    int numOutputThreads = NUM_OUTPUT_THREADS.get(conf);

    int maxThreads =
      Math.max(numInputThreads,
        Math.max(numComputeThreads, numOutputThreads));

    // check if the sticky partition option is set and, if so, set the
    long maxSticky = MAX_STICKY_PARTITIONS.get(conf);

    // number of sticky partitions
    if (maxSticky > 0 && maxPartitionsInMem - maxSticky >= maxThreads) {
      this.numOfStickyPartitions = new AtomicLong(maxSticky);
    } else {
      if (maxPartitionsInMem - maxSticky >= maxThreads) {
        if (LOG.isInfoEnabled()) {
          LOG.info("giraph.maxSticky parameter unset or improperly set " +
            "resetting to automatically computed value.");
        }
      }

      if (maxPartitionsInMem == 1 || maxThreads >= maxPartitionsInMem) {
        this.numOfStickyPartitions = new AtomicLong(0);
      } else {
        this.numOfStickyPartitions =
          new AtomicLong(maxPartitionsInMem - maxThreads);
      }
    }

    // Take advantage of multiple disks
    String[] userPaths = PARTITIONS_DIRECTORY.getArray(conf);
    basePaths = new String[userPaths.length];
    int i = 0;
    for (String path : userPaths) {
      basePaths[i++] = path + "/" + conf.get("mapred.job.id", "Unknown Job");
    }
    if (LOG.isInfoEnabled()) {
      LOG.info("DiskBackedPartitionStore with maxInMemoryPartitions=" +
        maxPartitionsInMem + ", isStaticGraph=" + conf.isStaticGraph());
    }
  }

  @Override
  public Iterable<Integer> getPartitionIds() {
    return Iterables.unmodifiableIterable(partitions.keySet());
  }

  @Override
  public boolean hasPartition(final Integer id) {
    return partitions.containsKey(id);
  }

  @Override
  public int getNumPartitions() {
    return partitions.size();
  }

  @Override
  public long getPartitionVertexCount(int partitionId) {
    MetaPartition meta = partitions.get(partitionId);
    if (meta.getState() == State.ONDISK) {
      return meta.getVertexCount();
    } else {
      return meta.getPartition().getVertexCount();
    }
  }

  @Override
  public long getPartitionEdgeCount(int partitionId) {
    MetaPartition meta = partitions.get(partitionId);
    if (meta.getState() == State.ONDISK) {
      return meta.getEdgeCount();
    } else {
      return meta.getPartition().getEdgeCount();
    }
  }

  @Override
  public Partition<I, V, E> getOrCreatePartition(Integer id) {
    MetaPartition meta = new MetaPartition(id);
    MetaPartition temp;

    temp = partitions.putIfAbsent(id, meta);
    if (temp != null) {
      meta = temp;
    }

    synchronized (meta) {
      if (temp == null && numOfStickyPartitions.getAndDecrement() > 0) {
        meta.setSticky();
      }
      getPartition(meta);
      if (meta.getPartition() == null) {
        Partition<I, V, E> partition = conf.createPartition(id, context);
        meta.setPartition(partition);
        addPartition(meta, partition);
        if (meta.getState() == State.INIT) {
          LOG.warn("Partition was still INIT after ADD (not possibile).");
        }
        // This get is necessary. When creating a new partition, it will be
        // placed by default as INACTIVE. However, here the user will retrieve
        // a reference to it, and hence there is the need to update the
        // reference count, as well as the state of the object.
        getPartition(meta);
        if (meta.getState() == State.INIT) {
          LOG.warn("Partition was still INIT after GET (not possibile).");
        }
      }

      if (meta.getState() == State.INIT) {
        String msg = "Getting a partition which is in INIT state is " +
                     "not allowed. " + meta;
        LOG.error(msg);
        throw new IllegalStateException(msg);
      }

      return meta.getPartition();
    }
  }

  @Override
  public void putPartition(Partition<I, V, E> partition) {
    Integer id = partition.getId();
    MetaPartition meta = partitions.get(id);
    putPartition(meta);
  }

  @Override
  public void deletePartition(Integer id) {
    if (hasPartition(id)) {
      MetaPartition meta = partitions.get(id);
      deletePartition(meta);
    }
  }

  @Override
  public Partition<I, V, E> removePartition(Integer id) {
    if (hasPartition(id)) {
      MetaPartition meta;

      meta = partitions.get(id);
      synchronized (meta) {
        getPartition(meta);
        putPartition(meta);
        deletePartition(id);
      }
      return meta.getPartition();
    }
    return null;
  }

  @Override
  public void addPartition(Partition<I, V, E> partition) {
    Integer id = partition.getId();
    MetaPartition meta = new MetaPartition(id);
    MetaPartition temp;

    meta.setPartition(partition);
    temp = partitions.putIfAbsent(id, meta);
    if (temp != null) {
      meta = temp;
    }

    synchronized (meta) {
      if (temp == null && numOfStickyPartitions.getAndDecrement() > 0) {
        meta.setSticky();
      }
      addPartition(meta, partition);
    }
  }

  @Override
  public void shutdown() {
    for (MetaPartition e : partitions.values()) {
      if (e.getState() == State.ONDISK) {
        deletePartitionFiles(e.getId());
      }
    }
  }

  @Override
  public String toString() {
    StringBuilder sb = new StringBuilder();
    for (MetaPartition e : partitions.values()) {
      sb.append(e.toString() + "\n");
    }
    return sb.toString();
  }

  /**
   * Writes vertex data (Id, value and halted state) to stream.
   *
   * @param output The output stream
   * @param vertex The vertex to serialize
   * @throws IOException
   */
  private void writeVertexData(DataOutput output, Vertex<I, V, E> vertex)
    throws IOException {

    vertex.getId().write(output);
    vertex.getValue().write(output);
    output.writeBoolean(vertex.isHalted());
  }

  /**
   * Writes vertex edges (Id, edges) to stream.
   *
   * @param output The output stream
   * @param vertex The vertex to serialize
   * @throws IOException
   */
  @SuppressWarnings("unchecked")
  private void writeOutEdges(DataOutput output, Vertex<I, V, E> vertex)
    throws IOException {

    vertex.getId().write(output);
    OutEdges<I, E> edges = (OutEdges<I, E>) vertex.getEdges();
    edges.write(output);
  }

  /**
   * Read vertex data from an input and initialize the vertex.
   *
   * @param in The input stream
   * @param vertex The vertex to initialize
   * @throws IOException
   */
  private void readVertexData(DataInput in, Vertex<I, V, E> vertex)
    throws IOException {

    I id = conf.createVertexId();
    id.readFields(in);
    V value = conf.createVertexValue();
    value.readFields(in);
    OutEdges<I, E> edges = conf.createAndInitializeOutEdges(0);
    vertex.initialize(id, value, edges);
    if (in.readBoolean()) {
      vertex.voteToHalt();
    } else {
      vertex.wakeUp();
    }
  }

  /**
   * Read vertex edges from an input and set them to the vertex.
   *
   * @param in The input stream
   * @param partition The partition owning the vertex
   * @throws IOException
   */
  @SuppressWarnings("unchecked")
  private void readOutEdges(DataInput in, Partition<I, V, E> partition)
    throws IOException {

    I id = conf.createVertexId();
    id.readFields(in);
    Vertex<I, V, E> v = partition.getVertex(id);
    OutEdges<I, E> edges = (OutEdges<I, E>) v.getEdges();
    edges.readFields(in);
    partition.saveVertex(v);
  }

  /**
   * Load a partition from disk. It deletes the files after the load,
   * except for the edges, if the graph is static.
   *
   * @param id The id of the partition to load
   * @param numVertices The number of vertices contained on disk
   * @return The partition
   * @throws IOException
   */
  private Partition<I, V, E> loadPartition(int id, long numVertices)
    throws IOException {

    Partition<I, V, E> partition = conf.createPartition(id, context);

    // Vertices
    File file = new File(getVerticesPath(id));
    if (LOG.isDebugEnabled()) {
      LOG.debug("loadPartition: loading partition vertices " +
        partition.getId() + " from " + file.getAbsolutePath());
    }

    FileInputStream filein = new FileInputStream(file);
    BufferedInputStream bufferin = new BufferedInputStream(filein);
    DataInputStream inputStream  = new DataInputStream(bufferin);
    for (int i = 0; i < numVertices; ++i) {
      Vertex<I, V , E> vertex = conf.createVertex();
      readVertexData(inputStream, vertex);
      partition.putVertex(vertex);
    }
    inputStream.close();
    if (!file.delete()) {
      String msg = "loadPartition: failed to delete " + file.getAbsolutePath();
      LOG.error(msg);
      throw new IllegalStateException(msg);
    }

    // Edges
    file = new File(getEdgesPath(id));

    if (LOG.isDebugEnabled()) {
      LOG.debug("loadPartition: loading partition edges " +
        partition.getId() + " from " + file.getAbsolutePath());
    }

    filein = new FileInputStream(file);
    bufferin = new BufferedInputStream(filein);
    inputStream  = new DataInputStream(bufferin);
    for (int i = 0; i < numVertices; ++i) {
      readOutEdges(inputStream, partition);
    }
    inputStream.close();
    // If the graph is static, keep the file around.
    if (!conf.isStaticGraph() && !file.delete()) {
      String msg = "loadPartition: failed to delete " + file.getAbsolutePath();
      LOG.error(msg);
      throw new IllegalStateException(msg);
    }
    return partition;
  }

  /**
   * Write a partition to disk.
   *
   * @param meta meta partition containing the partition to offload
   * @throws IOException
   */
  private void offloadPartition(MetaPartition meta) throws IOException {

    Partition<I, V, E> partition = meta.getPartition();
    File file = new File(getVerticesPath(partition.getId()));
    File parent = file.getParentFile();
    if (!parent.exists() && !parent.mkdirs() && LOG.isDebugEnabled()) {
      LOG.debug("offloadPartition: directory " + parent.getAbsolutePath() +
        " already exists.");
    }

    if (!file.createNewFile()) {
      String msg = "offloadPartition: file " + parent.getAbsolutePath() +
        " already exists.";
      LOG.error(msg);
      throw new IllegalStateException(msg);
    }

    if (LOG.isDebugEnabled()) {
      LOG.debug("offloadPartition: writing partition vertices " +
        partition.getId() + " to " + file.getAbsolutePath());
    }

    FileOutputStream fileout = new FileOutputStream(file);
    BufferedOutputStream bufferout = new BufferedOutputStream(fileout);
    DataOutputStream outputStream  = new DataOutputStream(bufferout);
    for (Vertex<I, V, E> vertex : partition) {
      writeVertexData(outputStream, vertex);
    }
    outputStream.close();

    // Avoid writing back edges if we have already written them once and
    // the graph is not changing.
    // If we are in the input superstep, we need to write the files
    // at least the first time, even though the graph is static.
    file = new File(getEdgesPath(partition.getId()));
    if (meta.getPrevVertexCount() != partition.getVertexCount() ||
        !conf.isStaticGraph() || !file.exists()) {

      meta.setPrevVertexCount(partition.getVertexCount());

      if (!file.createNewFile() && LOG.isDebugEnabled()) {
        LOG.debug("offloadPartition: file " + file.getAbsolutePath() +
            " already exists.");
      }

      if (LOG.isDebugEnabled()) {
        LOG.debug("offloadPartition: writing partition edges " +
          partition.getId() + " to " + file.getAbsolutePath());
      }

      fileout = new FileOutputStream(file);
      bufferout = new BufferedOutputStream(fileout);
      outputStream = new DataOutputStream(bufferout);
      for (Vertex<I, V, E> vertex : partition) {
        writeOutEdges(outputStream, vertex);
      }
      outputStream.close();
    }
  }

  /**
   * Append a partition on disk at the end of the file. Expects the caller
   * to hold the global lock.
   *
   * @param meta      meta partition container for the partitiont to save
   *                  to disk
   * @param partition The partition
   * @throws IOException
   */
  private void addToOOCPartition(MetaPartition meta,
    Partition<I, V, E> partition) throws IOException {

    Integer id = partition.getId();
    File file = new File(getVerticesPath(id));
    DataOutputStream outputStream = null;

    FileOutputStream fileout = new FileOutputStream(file, true);
    BufferedOutputStream bufferout = new BufferedOutputStream(fileout);
    outputStream = new DataOutputStream(bufferout);
    for (Vertex<I, V, E> vertex : partition) {
      writeVertexData(outputStream, vertex);
    }
    outputStream.close();

    file = new File(getEdgesPath(id));
    fileout = new FileOutputStream(file, true);
    bufferout = new BufferedOutputStream(fileout);
    outputStream = new DataOutputStream(bufferout);
    for (Vertex<I, V, E> vertex : partition) {
      writeOutEdges(outputStream, vertex);
    }
    outputStream.close();
  }

  /**
   * Delete a partition's files.
   *
   * @param id The id of the partition owning the file.
   */
  public void deletePartitionFiles(Integer id) {
    // File containing vertices
    File file = new File(getVerticesPath(id));
    if (file.exists() && !file.delete()) {
      String msg = "deletePartitionFiles: Failed to delete file " +
        file.getAbsolutePath();
      LOG.error(msg);
      throw new IllegalStateException(msg);
    }

    // File containing edges
    file = new File(getEdgesPath(id));
    if (file.exists() && !file.delete()) {
      String msg = "deletePartitionFiles: Failed to delete file " +
        file.getAbsolutePath();
      LOG.error(msg);
      throw new IllegalStateException(msg);
    }
  }

  /**
   * Get the path and basename of the storage files.
   *
   * @param partitionId The partition
   * @return The path to the given partition
   */
  private String getPartitionPath(Integer partitionId) {
    int hash = hasher.hashInt(partitionId).asInt();
    int idx = Math.abs(hash % basePaths.length);
    return basePaths[idx] + "/partition-" + partitionId;
  }

  /**
   * Get the path to the file where vertices are stored.
   *
   * @param partitionId The partition
   * @return The path to the vertices file
   */
  private String getVerticesPath(Integer partitionId) {
    return getPartitionPath(partitionId) + "_vertices";
  }

  /**
   * Get the path to the file where edges are stored.
   *
   * @param partitionId The partition
   * @return The path to the edges file
   */
  private String getEdgesPath(Integer partitionId) {
    return getPartitionPath(partitionId) + "_edges";
  }

  /**
   * Removes and returns the last recently used entry.
   *
   * @return The last recently used entry.
   */
  private MetaPartition getLRUPartition() {
    synchronized (lru) {
      Iterator<Entry<Integer, MetaPartition>> i =
          lru.entrySet().iterator();
      Entry<Integer, MetaPartition> entry = i.next();
      i.remove();
      return entry.getValue();
    }
  }

  /**
   * Method that gets a partition from the store.
   * The partition is produced as a side effect of the computation and is
   * reflected inside the META object provided as parameter.
   * This function is thread-safe since it locks the whole computation
   * on the metapartition provided.<br />
   * <br />
   * <b>ONDISK case</b><br />
   * When a thread tries to access an element on disk, it waits until it
   * space in memory and inactive data to swap resources.
   * It is possible that multiple threads wait for a single
   * partition to be restored from disk. The semantic of this
   * function is that only the first thread interested will be
   * in charge to load it back to memory, hence waiting on 'lru'.
   * The others, will be waiting on the lock to be available,
   * preventing consistency issues.<br />
   * <br />
   * <b>Deadlock</b><br />
   * The code of this method can in principle lead to a deadlock, due to the
   * fact that two locks are held together while running the "wait" method.
   * However, this problem does not occur. The two locks held are:
   * <ol>
   *  <li><b>Meta Object</b>, which is the object the thread is trying to
   *  acquire and is currently stored on disk.</li>
   *  <li><b>LRU data structure</b>, which keeps track of the objects which are
   *  inactive and hence swappable.</li>
   * </ol>
   * It is not possible that two getPartition calls cross because this means
   * that LRU objects are both INACTIVE and ONDISK at the same time, which is
   * not possible.
   *
   * @param meta meta partition container with the partition itself
   */
  @edu.umd.cs.findbugs.annotations.SuppressWarnings(
    value = "TLW_TWO_LOCK_WAIT",
    justification = "The two locks held do not produce a deadlock")
  private void getPartition(MetaPartition meta) {
    synchronized (meta) {
      boolean isNotDone = true;

      if (meta.getState() != State.INIT) {
        State state;

        while (isNotDone) {
          state = meta.getState();
          switch (state) {
          case ONDISK:
            MetaPartition swapOutPartition = null;
            long numVertices = meta.getVertexCount();

          synchronized (lru) {
            try {
              while (numPartitionsInMem.get() >= maxPartitionsInMem &&
                     lru.isEmpty()) {
                // notification for threads waiting on this are
                // required in two cases:
                // a) when an element is added to the LRU (hence
                //    a new INACTIVE partition is added).
                // b) when additioanl space is available in memory (hence
                //    in memory counter is decreased).
                lru.wait();
              }
            } catch (InterruptedException e) {
              LOG.error("getPartition: error while waiting on " +
                "LRU data structure: " + e.getMessage());
              throw new IllegalStateException(e);
            }

            // We have to make some space first, by removing the least used
            // partition (hence the first in the LRU data structure).
            //
            // NB: In case the LRU is not empty, we are _swapping_ elements.
            //     This, means that there is no need to "make space" by
            //     changing the in-memory counter. Differently, if the element
            //     can directly be placed into memory, the memory usage
            //     increases by one.
            if (numPartitionsInMem.get() >= maxPartitionsInMem &&
                !lru.isEmpty()) {
              swapOutPartition = getLRUPartition();
            } else if (numPartitionsInMem.get() < maxPartitionsInMem) {
              numPartitionsInMem.getAndIncrement();
            } else {
              String msg = "lru is empty and there is not space in memory, " +
                           "hence the partition cannot be loaded.";
              LOG.error(msg);
              throw new IllegalStateException(msg);
            }
          }

            if (swapOutPartition != null) {
              synchronized (swapOutPartition) {
                if (swapOutPartition.isSticky()) {
                  String msg = "Partition " + meta.getId() + " is sticky " +
                    " and cannot be offloaded.";
                  LOG.error(msg);
                  throw new IllegalStateException(msg);
                }
                // safety check
                if (swapOutPartition.getState() != State.INACTIVE) {
                  String msg = "Someone is holding the partition with id " +
                    swapOutPartition.getId() + " but is supposed to be " +
                    "inactive.";
                  LOG.error(msg);
                  throw new IllegalStateException(msg);
                }

                try {
                  offloadPartition(swapOutPartition);
                  Partition<I, V, E> p = swapOutPartition.getPartition();
                  swapOutPartition.setOnDisk(p);
                  // notify all the threads waiting to the offloading process,
                  // that they are allowed again to access the
                  // swapped-out object.
                  swapOutPartition.notifyAll();
                } catch (IOException e)  {
                  LOG.error("getPartition: Failed while Offloading " +
                    "New Partition: " + e.getMessage());
                  throw new IllegalStateException(e);
                }
              }
            }

            // If it was needed, the partition to be swpped out is on disk.
            // Additionally, we are guaranteed that we have a free spot in
            // memory, in fact,
            // a) either there was space in memory, and hence the in memory
            //    counter was incremented reserving the space for this element.
            // b) or the space has been created by swapping out the partition
            //    that was inactive in the LRU.
            // This means that, even in the case that concurrently swapped
            // element is restored back to memory, there must have been
            // place for only an additional partition.
            Partition<I, V, E> partition;
            try {
              partition = loadPartition(meta.getId(), numVertices);
            } catch (IOException e)  {
              LOG.error("getPartition: Failed while Loading Partition from " +
                "disk: " + e.getMessage());
              throw new IllegalStateException(e);
            }
            meta.setActive(partition);

            isNotDone = false;
            break;
          case INACTIVE:
            MetaPartition p = null;

            if (meta.isSticky()) {
              meta.setActive();
              isNotDone = false;
              break;
            }

          synchronized (lru) {
            p = lru.remove(meta.getId());
          }
            if (p == meta && p.getState() == State.INACTIVE) {
              meta.setActive();
              isNotDone = false;
            } else {
              try {
                // A thread could wait here when an inactive partition is
                // concurrently swapped to disk. In fact, the meta object is
                // locked but, even though the object is inactive, it is not
                // present in the LRU ADT.
                // The thread need to be signaled when the partition is
                // finally swapped out of the disk.
                meta.wait();
              } catch (InterruptedException e) {
                LOG.error("getPartition: error while waiting on " +
                  "previously Inactive Partition: " + e.getMessage());
                throw new IllegalStateException(e);
              }
              isNotDone = true;
            }
            break;
          case ACTIVE:
            meta.incrementReferences();
            isNotDone = false;
            break;
          default:
            throw new IllegalStateException("illegal state " + meta.getState() +
              " for partition " + meta.getId());
          }
        }
      }
    }
  }

  /**
   * Method that puts a partition back to the store. This function is
   * thread-safe using meta partition intrinsic lock.
   *
   * @param meta meta partition container with the partition itself
   */
  private void putPartition(MetaPartition meta) {
    synchronized (meta) {
      if (meta.getState() != State.ACTIVE) {
        String msg = "It is not possible to put back a partition which is " +
          "not ACTIVE.\n" + meta.toString();
        LOG.error(msg);
        throw new IllegalStateException(msg);
      }

      if (meta.decrementReferences() == 0) {
        meta.setState(State.INACTIVE);
        if (!meta.isSticky()) {
          synchronized (lru) {
            lru.put(meta.getId(), meta);
            lru.notifyAll();  // notify every waiting process about the fact
                              // that the LRU is not empty anymore
          }
        }
        meta.notifyAll(); // needed for the threads that are waiting for the
                          // partition to become inactive, when
                          // trying to delete the partition
      }
    }
  }

  /**
   * Task that adds a partition to the store.
   * This function is thread-safe since it locks using the intrinsic lock of
   * the meta partition.
   *
   * @param meta meta partition container with the partition itself
   * @param partition partition to be added
   */
  private void addPartition(MetaPartition meta, Partition<I, V, E> partition) {
    synchronized (meta) {
      // If the state of the partition is INIT, this means that the META
      // object was just created, and hence the partition is new.
      if (meta.getState() == State.INIT) {
        // safety check to guarantee that the partition was set.
        if (partition == null) {
          String msg = "No partition was provided.";
          LOG.error(msg);
          throw new IllegalStateException(msg);
        }

        // safety check to guarantee that the partition provided is the one
        // that is also set in the meta partition.
        if (partition != meta.getPartition()) {
          String msg = "Partition and Meta-Partition should " +
            "contain the same data";
          LOG.error(msg);
          throw new IllegalStateException(msg);
        }

        synchronized (lru) {
          if (numPartitionsInMem.get() < maxPartitionsInMem || meta.isSticky) {
            meta.setState(State.INACTIVE);
            numPartitionsInMem.getAndIncrement();
            if (!meta.isSticky) {
              lru.put(meta.getId(), meta);
              lru.notifyAll();  // signaling that at least one element is
                                // present in the LRU ADT.
            }
            return; // this is used to exit the function and avoid using the
                    // else clause. This is required to keep only this part of
                    // the code under lock and aoivd keeping the lock when
                    // performing the Offload I/O
          }
        }

        // ELSE
        try {
          offloadPartition(meta);
          meta.setOnDisk(partition);
        } catch (IOException e)  {
          LOG.error("addPartition: Failed while Offloading New Partition: " +
            e.getMessage());
          throw new IllegalStateException(e);
        }
      } else {
        Partition<I, V, E> existing = null;
        boolean isOOC = false;
        boolean isNotDone = true;
        State state;

        while (isNotDone) {
          state = meta.getState();
          switch (state) {
          case ONDISK:
            isOOC = true;
            isNotDone = false;
            meta.addToVertexCount(partition.getVertexCount());
            break;
          case INACTIVE:
            MetaPartition p = null;

            if (meta.isSticky()) {
              existing = meta.getPartition();
              isNotDone = false;
              break;
            }

          synchronized (lru) {
            p = lru.get(meta.getId());
          }
            // this check is safe because, even though we are out of the LRU
            // lock, we still hold the lock on the partition. This means that
            // a) if the partition was removed from the LRU, p will be null
            //    and the current thread will wait.
            // b) if the partition was not removed, its state cannot be
            //    modified since the lock is held on meta, which refers to
            //    the same object.
            if (p == meta) {
              existing = meta.getPartition();
              isNotDone = false;
            } else {
              try {
                // A thread could wait here when an inactive partition is
                // concurrently swapped to disk. In fact, the meta object is
                // locked but, even though the object is inactive, it is not
                // present in the LRU ADT.
                // The thread need to be signaled when the partition is finally
                // swapped out of the disk.
                meta.wait();
              } catch (InterruptedException e) {
                LOG.error("addPartition: error while waiting on " +
                  "previously inactive partition: " + e.getMessage());
                throw new IllegalStateException(e);
              }

              isNotDone = true;
            }
            break;
          case ACTIVE:
            existing = meta.getPartition();
            isNotDone = false;
            break;
          default:
            throw new IllegalStateException("illegal state " + state +
              " for partition " + meta.getId());
          }
        }

        if (isOOC) {
          try {
            addToOOCPartition(meta, partition);
          } catch (IOException e) {
            LOG.error("addPartition: Failed while Adding to OOC Partition: " +
              e.getMessage());
            throw new IllegalStateException(e);
          }
        } else {
          existing.addPartition(partition);
        }
      }
    }
  }

  /**
   * Task that deletes a partition to the store
   * This function is thread-safe using the intrinsic lock of the meta
   * partition object
   *
   * @param meta meta partition container with the partition itself
   */
  private void deletePartition(MetaPartition meta) {
    synchronized (meta) {
      boolean isDone = false;
      int id = meta.getId();

      State state;
      while (!isDone) {
        state = meta.getState();
        switch (state) {
        case ONDISK:
          deletePartitionFiles(id);
          isDone = true;
          break;
        case INACTIVE:
          MetaPartition p;

          if (meta.isSticky()) {
            isDone = true;
            numPartitionsInMem.getAndDecrement();
            break;
          }

        synchronized (lru) {
          p = lru.remove(id);
          if (p == meta && p.getState() == State.INACTIVE) {
            isDone = true;
            numPartitionsInMem.getAndDecrement();
            lru.notifyAll(); // notify all waiting processes that there is now
                             // at least one new free place in memory.
            // XXX: attention, here a race condition with getPartition is
            //      possible, since changing lru is separated by the removal
            //      of the element from the parittions ADT.
            break;
          }
        }
          try {
            // A thread could wait here when an inactive partition is
            // concurrently swapped to disk. In fact, the meta object is
            // locked but, even though the object is inactive, it is not
            // present in the LRU ADT.
            // The thread need to be signaled when the partition is
            // finally swapped out of the disk.
            meta.wait();
          } catch (InterruptedException e) {
            LOG.error("deletePartition: error while waiting on " +
              "previously inactive partition: " + e.getMessage());
            throw new IllegalStateException(e);
          }
          isDone = false;
          break;
        case ACTIVE:
          try {
            // the thread waits that the object to be deleted becomes inactive,
            // otherwise the deletion is not possible.
            // The thread needs to be signaled when the partition becomes
            // inactive.
            meta.wait();
          } catch (InterruptedException e) {
            LOG.error("deletePartition: error while waiting on " +
              "active partition: " + e.getMessage());
            throw new IllegalStateException(e);
          }
          break;
        default:
          throw new IllegalStateException("illegal state " + state +
            " for partition " + id);
        }
      }
      partitions.remove(id);
    }
  }

  /**
   * Partition container holding additional meta data associated with each
   * partition.
   */
  private class MetaPartition {
    // ---- META INFORMATION ----
    /** ID of the partition */
    private int id;
    /** State in which the partition is */
    private State state;
    /**
     * Counter used to keep track of the number of references retained by
     * user-threads
     */
    private int references;
    /** Number of vertices contained in the partition */
    private long vertexCount;
    /** Previous number of vertices contained in the partition */
    private long prevVertexCount;
    /** Number of edges contained in the partition */
    private long edgeCount;
    /**
     * Sticky bit; if set, this partition is never supposed to be
     * written to disk
     */
    private boolean isSticky;

    // ---- PARTITION ----
    /** the actual partition. Depending on the state of the partition,
        this object could be empty. */
    private Partition<I, V, E> partition;

    /**
     * Initialization of the metadata enriched partition.
     *
     * @param id id of the partition
     */
    public MetaPartition(int id) {
      this.id = id;
      this.state = State.INIT;
      this.references = 0;
      this.vertexCount = 0;
      this.prevVertexCount = 0;
      this.edgeCount = 0;
      this.isSticky = false;

      this.partition = null;
    }

    /**
     * @return the id
     */
    public int getId() {
      return id;
    }

    /**
     * @return the state
     */
    public State getState() {
      return state;
    }

    /**
     * This function sets the metadata for on-disk partition.
     *
     * @param partition partition related to this container
     */
    public void setOnDisk(Partition<I, V, E> partition) {
      this.state = State.ONDISK;
      this.partition = null;
      this.vertexCount = partition.getVertexCount();
      this.edgeCount = partition.getEdgeCount();
    }

    /**
     *
     */
    public void setActive() {
      this.setActive(null);
    }

    /**
     *
     * @param partition the partition associate to this container
     */
    public void setActive(Partition<I, V, E> partition) {
      if (partition != null) {
        this.partition = partition;
      }
      this.state = State.ACTIVE;
      this.prevVertexCount = this.vertexCount;
      this.vertexCount = 0;
      this.incrementReferences();
    }

    /**
     * @param state the state to set
     */
    public void setState(State state) {
      this.state = state;
    }

    /**
     * @return decremented references
     */
    public int decrementReferences() {
      if (references > 0) {
        references -= 1;
      }
      return references;
    }

    /**
     * @return incremented references
     */
    public int incrementReferences() {
      return ++references;
    }

    /**
     * set previous number of vertexes
     * @param vertexCount number of vertexes
     */
    public void setPrevVertexCount(long vertexCount) {
      this.prevVertexCount = vertexCount;
    }

    /**
     * @return the vertexCount
     */
    public long getPrevVertexCount() {
      return prevVertexCount;
    }

    /**
     * @return the vertexCount
     */
    public long getVertexCount() {
      return vertexCount;
    }

    /**
     * @return the edgeCount
     */
    public long getEdgeCount() {
      return edgeCount;
    }

    /**
     * @param inc amount to add to the vertex count
     */
    public void addToVertexCount(long inc) {
      this.vertexCount += inc;
      this.prevVertexCount = vertexCount;
    }

    /**
     * @return the partition
     */
    public Partition<I, V, E> getPartition() {
      return partition;
    }

    /**
     * @param partition the partition to set
     */
    public void setPartition(Partition<I, V, E> partition) {
      this.partition = partition;
    }

    /**
     * Set sticky bit to this partition
     */
    public void setSticky() {
      this.isSticky = true;
    }

    /**
     * Get sticky bit to this partition
     * @return boolean ture iff the sticky bit is set
     */
    public boolean isSticky() {
      return this.isSticky;
    }

    @Override
    public String toString() {
      StringBuffer sb = new StringBuffer();

      sb.append("Meta Data: { ");
      sb.append("ID: " + id + "; ");
      sb.append("State: " + state + "; ");
      sb.append("Number of References: " + references + "; ");
      sb.append("Number of Vertices: " + vertexCount + "; ");
      sb.append("Previous number of Vertices: " + prevVertexCount + "; ");
      sb.append("Number of edges: " + edgeCount + "; ");
      sb.append("Is Sticky: " + isSticky + "; ");
      sb.append("Partition: " + partition + "; }");

      return sb.toString();
    }
  }
}


File: giraph-core/src/main/java/org/apache/giraph/partition/PartitionStore.java
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

package org.apache.giraph.partition;

import org.apache.hadoop.io.Writable;
import org.apache.hadoop.io.WritableComparable;

/**
 * Structure that stores partitions for a worker.
 *
 * @param <I> Vertex id
 * @param <V> Vertex data
 * @param <E> Edge data
 */
public abstract class PartitionStore<I extends WritableComparable,
    V extends Writable, E extends Writable> {
  /**
   * Add a new partition to the store or just the vertices from the partition
   * to the old partition.
   *
   * @param partition Partition to add
   */
  public abstract void addPartition(Partition<I, V, E> partition);

  /**
   * Get or create a partition. Note: user has to put back
   * it to the store through {@link #putPartition(Partition)} after use.
   *
   * @param partitionId Partition id
   * @return The requested partition (never null)
   */
  public abstract Partition<I, V, E> getOrCreatePartition(Integer partitionId);

  /**
   * Put a partition back to the store. Use this method to be put a partition
   * back after it has been retrieved through
   * {@link #getOrCreatePartition(Integer)}.
   *
   * @param partition Partition
   */
  public abstract void putPartition(Partition<I, V, E> partition);

  /**
   * Remove a partition and return it.
   *
   * @param partitionId Partition id
   * @return The removed partition
   */
  public abstract Partition<I, V, E> removePartition(Integer partitionId);

  /**
   * Just delete a partition
   * (more efficient than {@link #removePartition(Integer partitionID)} if the
   * partition is out of core).
   *
   * @param partitionId Partition id
   */
  public abstract void deletePartition(Integer partitionId);

  /**
   * Whether a specific partition is present in the store.
   *
   * @param partitionId Partition id
   * @return True iff the partition is present
   */
  public abstract boolean hasPartition(Integer partitionId);

  /**
   * Return the ids of all the stored partitions as an Iterable.
   *
   * @return The partition ids
   */
  public abstract Iterable<Integer> getPartitionIds();

  /**
   * Return the number of stored partitions.
   *
   * @return The number of partitions
   */
  public abstract int getNumPartitions();

  /**
   * Return the number of vertices in a partition.
   * @param partitionId Partition id
   * @return The number of vertices in the specified partition
   */
  public abstract long getPartitionVertexCount(int partitionId);

  /**
   * Return the number of edges in a partition.
   * @param partitionId Partition id
   * @return The number of edges in the specified partition
   */
  public abstract long getPartitionEdgeCount(int partitionId);

  /**
   * Whether the partition store is empty.
   *
   * @return True iff there are no partitions in the store
   */
  public boolean isEmpty() {
    return getNumPartitions() == 0;
  }

  /**
   * Called at the end of the computation.
   */
  public void shutdown() { }
}


File: giraph-core/src/main/java/org/apache/giraph/partition/SimplePartitionStore.java
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

package org.apache.giraph.partition;

import com.google.common.collect.Maps;
import org.apache.giraph.conf.ImmutableClassesGiraphConfiguration;
import org.apache.hadoop.io.Writable;
import org.apache.hadoop.io.WritableComparable;
import org.apache.hadoop.mapreduce.Mapper;

import java.util.concurrent.ConcurrentMap;

/**
 * A simple in-memory partition store.
 *
 * @param <I> Vertex id
 * @param <V> Vertex data
 * @param <E> Edge data
 */
public class SimplePartitionStore<I extends WritableComparable,
    V extends Writable, E extends Writable>
    extends PartitionStore<I, V, E> {
  /** Map of stored partitions. */
  private final ConcurrentMap<Integer, Partition<I, V, E>> partitions =
      Maps.newConcurrentMap();
  /** Configuration. */
  private final ImmutableClassesGiraphConfiguration<I, V, E> conf;
  /** Context used to report progress */
  private final Mapper<?, ?, ?, ?>.Context context;

  /**
   * Constructor.
   *
   * @param conf Configuration
   * @param context Mapper context
   */
  public SimplePartitionStore(
      ImmutableClassesGiraphConfiguration<I, V, E> conf,
      Mapper<?, ?, ?, ?>.Context context) {
    this.conf = conf;
    this.context = context;
  }

  @Override
  public void addPartition(Partition<I, V, E> partition) {
    Partition<I, V, E> oldPartition = partitions.get(partition.getId());
    if (oldPartition == null) {
      oldPartition = partitions.putIfAbsent(partition.getId(), partition);
      if (oldPartition == null) {
        return;
      }
    }
    // This is thread-safe
    oldPartition.addPartition(partition);
  }

  @Override
  public Partition<I, V, E> getOrCreatePartition(Integer partitionId) {
    Partition<I, V, E> oldPartition = partitions.get(partitionId);
    if (oldPartition == null) {
      Partition<I, V, E> newPartition =
          conf.createPartition(partitionId, context);
      oldPartition = partitions.putIfAbsent(partitionId, newPartition);
      if (oldPartition == null) {
        return newPartition;
      }
    }
    return oldPartition;
  }

  @Override
  public Partition<I, V, E> removePartition(Integer partitionId) {
    return partitions.remove(partitionId);
  }

  @Override
  public void deletePartition(Integer partitionId) {
    partitions.remove(partitionId);
  }

  @Override
  public boolean hasPartition(Integer partitionId) {
    return partitions.containsKey(partitionId);
  }

  @Override
  public Iterable<Integer> getPartitionIds() {
    return partitions.keySet();
  }

  @Override
  public int getNumPartitions() {
    return partitions.size();
  }

  @Override
  public long getPartitionVertexCount(int partitionId) {
    Partition partition = partitions.get(partitionId);
    if (partition == null) {
      return 0;
    } else {
      return partition.getVertexCount();
    }
  }

  @Override
  public long getPartitionEdgeCount(int partitionId) {
    Partition partition = partitions.get(partitionId);
    if (partition == null) {
      return 0;
    } else {
      return partition.getEdgeCount();
    }
  }

  @Override
  public void putPartition(Partition<I, V, E> partition) { }
}


File: giraph-core/src/main/java/org/apache/giraph/worker/BspServiceWorker.java
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

package org.apache.giraph.worker;

import java.io.DataInputStream;
import java.io.DataOutputStream;
import java.io.IOException;
import java.nio.charset.Charset;
import java.util.ArrayList;
import java.util.Collection;
import java.util.Collections;
import java.util.HashSet;
import java.util.LinkedList;
import java.util.List;
import java.util.Map;
import java.util.Map.Entry;
import java.util.Queue;
import java.util.Set;
import java.util.concurrent.ArrayBlockingQueue;
import java.util.concurrent.Callable;
import java.util.concurrent.ConcurrentLinkedQueue;
import java.util.concurrent.TimeUnit;

import net.iharder.Base64;

import org.apache.giraph.bsp.ApplicationState;
import org.apache.giraph.bsp.BspService;
import org.apache.giraph.bsp.CentralizedServiceWorker;
import org.apache.giraph.bsp.checkpoints.CheckpointStatus;
import org.apache.giraph.comm.ServerData;
import org.apache.giraph.comm.WorkerClient;
import org.apache.giraph.comm.WorkerClientRequestProcessor;
import org.apache.giraph.comm.WorkerServer;
import org.apache.giraph.comm.aggregators.WorkerAggregatorRequestProcessor;
import org.apache.giraph.comm.messages.MessageStore;
import org.apache.giraph.comm.messages.queue.AsyncMessageStoreWrapper;
import org.apache.giraph.comm.netty.NettyWorkerAggregatorRequestProcessor;
import org.apache.giraph.comm.netty.NettyWorkerClient;
import org.apache.giraph.comm.netty.NettyWorkerClientRequestProcessor;
import org.apache.giraph.comm.netty.NettyWorkerServer;
import org.apache.giraph.conf.GiraphConstants;
import org.apache.giraph.conf.ImmutableClassesGiraphConfiguration;
import org.apache.giraph.edge.Edge;
import org.apache.giraph.graph.AddressesAndPartitionsWritable;
import org.apache.giraph.graph.FinishedSuperstepStats;
import org.apache.giraph.graph.GlobalStats;
import org.apache.giraph.graph.GraphTaskManager;
import org.apache.giraph.graph.InputSplitEvents;
import org.apache.giraph.graph.InputSplitPaths;
import org.apache.giraph.graph.Vertex;
import org.apache.giraph.graph.VertexEdgeCount;
import org.apache.giraph.io.EdgeOutputFormat;
import org.apache.giraph.io.EdgeWriter;
import org.apache.giraph.io.VertexOutputFormat;
import org.apache.giraph.io.VertexWriter;
import org.apache.giraph.io.superstep_output.SuperstepOutput;
import org.apache.giraph.mapping.translate.TranslateEdge;
import org.apache.giraph.master.MasterInfo;
import org.apache.giraph.master.SuperstepClasses;
import org.apache.giraph.metrics.GiraphMetrics;
import org.apache.giraph.metrics.GiraphTimer;
import org.apache.giraph.metrics.GiraphTimerContext;
import org.apache.giraph.metrics.ResetSuperstepMetricsObserver;
import org.apache.giraph.metrics.SuperstepMetricsRegistry;
import org.apache.giraph.metrics.WorkerSuperstepMetrics;
import org.apache.giraph.partition.Partition;
import org.apache.giraph.partition.PartitionExchange;
import org.apache.giraph.partition.PartitionOwner;
import org.apache.giraph.partition.PartitionStats;
import org.apache.giraph.partition.PartitionStore;
import org.apache.giraph.partition.WorkerGraphPartitioner;
import org.apache.giraph.utils.CallableFactory;
import org.apache.giraph.utils.CheckpointingUtils;
import org.apache.giraph.utils.JMapHistoDumper;
import org.apache.giraph.utils.LoggerUtils;
import org.apache.giraph.utils.MemoryUtils;
import org.apache.giraph.utils.ProgressableUtils;
import org.apache.giraph.utils.ReactiveJMapHistoDumper;
import org.apache.giraph.utils.WritableUtils;
import org.apache.giraph.zk.BspEvent;
import org.apache.giraph.zk.PredicateLock;
import org.apache.hadoop.fs.FSDataInputStream;
import org.apache.hadoop.fs.FSDataOutputStream;
import org.apache.hadoop.fs.Path;
import org.apache.hadoop.io.Writable;
import org.apache.hadoop.io.WritableComparable;
import org.apache.hadoop.io.compress.CompressionCodec;
import org.apache.hadoop.io.compress.CompressionCodecFactory;
import org.apache.hadoop.mapreduce.Mapper;
import org.apache.hadoop.mapreduce.OutputCommitter;
import org.apache.log4j.Level;
import org.apache.log4j.Logger;
import org.apache.zookeeper.CreateMode;
import org.apache.zookeeper.KeeperException;
import org.apache.zookeeper.WatchedEvent;
import org.apache.zookeeper.Watcher.Event.EventType;
import org.apache.zookeeper.ZooDefs.Ids;
import org.apache.zookeeper.data.Stat;
import org.json.JSONArray;
import org.json.JSONException;
import org.json.JSONObject;

import com.google.common.collect.Iterables;
import com.google.common.collect.Lists;

/**
 * ZooKeeper-based implementation of {@link CentralizedServiceWorker}.
 *
 * @param <I> Vertex id
 * @param <V> Vertex data
 * @param <E> Edge data
 */
@SuppressWarnings("rawtypes")
public class BspServiceWorker<I extends WritableComparable,
    V extends Writable, E extends Writable>
    extends BspService<I, V, E>
    implements CentralizedServiceWorker<I, V, E>,
    ResetSuperstepMetricsObserver {
  /** Name of gauge for time spent waiting on other workers */
  public static final String TIMER_WAIT_REQUESTS = "wait-requests-us";
  /** Class logger */
  private static final Logger LOG = Logger.getLogger(BspServiceWorker.class);
  /** My process health znode */
  private String myHealthZnode;
  /** Worker info */
  private final WorkerInfo workerInfo;
  /** Worker graph partitioner */
  private final WorkerGraphPartitioner<I, V, E> workerGraphPartitioner;
  /** Local Data for each worker */
  private final LocalData<I, V, E, ? extends Writable> localData;
  /** Used to translate Edges during vertex input phase based on localData */
  private final TranslateEdge<I, E> translateEdge;
  /** IPC Client */
  private final WorkerClient<I, V, E> workerClient;
  /** IPC Server */
  private final WorkerServer<I, V, E> workerServer;
  /** Request processor for aggregator requests */
  private final WorkerAggregatorRequestProcessor
  workerAggregatorRequestProcessor;
  /** Master info */
  private MasterInfo masterInfo = new MasterInfo();
  /** List of workers */
  private List<WorkerInfo> workerInfoList = Lists.newArrayList();
  /** Have the partition exchange children (workers) changed? */
  private final BspEvent partitionExchangeChildrenChanged;

  /** Worker Context */
  private final WorkerContext workerContext;

  /** Handler for aggregators */
  private final WorkerAggregatorHandler globalCommHandler;

  /** Superstep output */
  private final SuperstepOutput<I, V, E> superstepOutput;

  /** array of observers to call back to */
  private final WorkerObserver[] observers;
  /** Writer for worker progress */
  private final WorkerProgressWriter workerProgressWriter;

  // Per-Superstep Metrics
  /** Timer for WorkerContext#postSuperstep */
  private GiraphTimer wcPostSuperstepTimer;
  /** Time spent waiting on requests to finish */
  private GiraphTimer waitRequestsTimer;

  /** InputSplit handlers used in INPUT_SUPERSTEP for vertex splits */
  private InputSplitsHandler vertexSplitsHandler;
  /** InputSplit handlers used in INPUT_SUPERSTEP for edge splits */
  private InputSplitsHandler edgeSplitsHandler;

  /**
   * Constructor for setting up the worker.
   *
   * @param context Mapper context
   * @param graphTaskManager GraphTaskManager for this compute node
   * @throws IOException
   * @throws InterruptedException
   */
  public BspServiceWorker(
    Mapper<?, ?, ?, ?>.Context context,
    GraphTaskManager<I, V, E> graphTaskManager)
    throws IOException, InterruptedException {
    super(context, graphTaskManager);
    ImmutableClassesGiraphConfiguration<I, V, E> conf = getConfiguration();
    localData = new LocalData<>(conf);
    translateEdge = getConfiguration().edgeTranslationInstance();
    if (translateEdge != null) {
      translateEdge.initialize(this);
    }
    partitionExchangeChildrenChanged = new PredicateLock(context);
    registerBspEvent(partitionExchangeChildrenChanged);
    workerGraphPartitioner =
        getGraphPartitionerFactory().createWorkerGraphPartitioner();
    workerInfo = new WorkerInfo();
    workerServer = new NettyWorkerServer<I, V, E>(conf, this, context,
        graphTaskManager.createUncaughtExceptionHandler());
    workerInfo.setInetSocketAddress(workerServer.getMyAddress());
    workerInfo.setTaskId(getTaskPartition());
    workerClient = new NettyWorkerClient<I, V, E>(context, conf, this,
        graphTaskManager.createUncaughtExceptionHandler());

    workerAggregatorRequestProcessor =
        new NettyWorkerAggregatorRequestProcessor(getContext(), conf, this);

    globalCommHandler = new WorkerAggregatorHandler(this, conf, context);

    workerContext = conf.createWorkerContext();
    workerContext.setWorkerGlobalCommUsage(globalCommHandler);

    superstepOutput = conf.createSuperstepOutput(context);

    if (conf.isJMapHistogramDumpEnabled()) {
      conf.addWorkerObserverClass(JMapHistoDumper.class);
    }
    if (conf.isReactiveJmapHistogramDumpEnabled()) {
      conf.addWorkerObserverClass(ReactiveJMapHistoDumper.class);
    }
    observers = conf.createWorkerObservers();

    WorkerProgress.get().setTaskId(getTaskPartition());
    workerProgressWriter = conf.trackJobProgressOnClient() ?
        new WorkerProgressWriter(graphTaskManager.getJobProgressTracker()) :
        null;

    GiraphMetrics.get().addSuperstepResetObserver(this);
    vertexSplitsHandler = null;
    edgeSplitsHandler = null;
  }

  @Override
  public void newSuperstep(SuperstepMetricsRegistry superstepMetrics) {
    waitRequestsTimer = new GiraphTimer(superstepMetrics,
        TIMER_WAIT_REQUESTS, TimeUnit.MICROSECONDS);
    wcPostSuperstepTimer = new GiraphTimer(superstepMetrics,
        "worker-context-post-superstep", TimeUnit.MICROSECONDS);
  }

  @Override
  public WorkerContext getWorkerContext() {
    return workerContext;
  }

  @Override
  public WorkerObserver[] getWorkerObservers() {
    return observers;
  }

  @Override
  public WorkerClient<I, V, E> getWorkerClient() {
    return workerClient;
  }

  public LocalData<I, V, E, ? extends Writable> getLocalData() {
    return localData;
  }

  public TranslateEdge<I, E> getTranslateEdge() {
    return translateEdge;
  }

  /**
   * Intended to check the health of the node.  For instance, can it ssh,
   * dmesg, etc. For now, does nothing.
   * TODO: Make this check configurable by the user (i.e. search dmesg for
   * problems).
   *
   * @return True if healthy (always in this case).
   */
  public boolean isHealthy() {
    return true;
  }

  /**
   * Load the vertices/edges from input slits. Do this until all the
   * InputSplits have been processed.
   * All workers will try to do as many InputSplits as they can.  The master
   * will monitor progress and stop this once all the InputSplits have been
   * loaded and check-pointed.  Keep track of the last input split path to
   * ensure the input split cache is flushed prior to marking the last input
   * split complete.
   *
   * Use one or more threads to do the loading.
   *
   * @param inputSplitPathList List of input split paths
   * @param inputSplitsCallableFactory Factory for {@link InputSplitsCallable}s
   * @return Statistics of the vertices and edges loaded
   * @throws InterruptedException
   * @throws KeeperException
   */
  private VertexEdgeCount loadInputSplits(
      List<String> inputSplitPathList,
      CallableFactory<VertexEdgeCount> inputSplitsCallableFactory)
    throws KeeperException, InterruptedException {
    VertexEdgeCount vertexEdgeCount = new VertexEdgeCount();
    // Determine how many threads to use based on the number of input splits
    int maxInputSplitThreads = (inputSplitPathList.size() - 1) /
        getConfiguration().getMaxWorkers() + 1;
    int numThreads = Math.min(getConfiguration().getNumInputSplitsThreads(),
        maxInputSplitThreads);
    if (LOG.isInfoEnabled()) {
      LOG.info("loadInputSplits: Using " + numThreads + " thread(s), " +
          "originally " + getConfiguration().getNumInputSplitsThreads() +
          " threads(s) for " + inputSplitPathList.size() + " total splits.");
    }

    List<VertexEdgeCount> results =
        ProgressableUtils.getResultsWithNCallables(inputSplitsCallableFactory,
            numThreads, "load-%d", getContext());
    for (VertexEdgeCount result : results) {
      vertexEdgeCount = vertexEdgeCount.incrVertexEdgeCount(result);
    }

    workerClient.waitAllRequests();
    return vertexEdgeCount;
  }

  /**
   * Load the mapping entries from the user-defined
   * {@link org.apache.giraph.io.MappingReader}
   *
   * @return Count of mapping entries loaded
   */
  private long loadMapping() throws KeeperException,
    InterruptedException {
    List<String> inputSplitPathList =
        getZkExt().getChildrenExt(mappingInputSplitsPaths.getPath(),
        false, false, true);

    InputSplitPathOrganizer splitOrganizer =
        new InputSplitPathOrganizer(getZkExt(),
            inputSplitPathList, getWorkerInfo().getHostname(),
            getConfiguration().useInputSplitLocality());

    MappingInputSplitsCallableFactory<I, V, E, ? extends Writable>
        mappingInputSplitsCallableFactory =
        new MappingInputSplitsCallableFactory<>(
            getConfiguration().createWrappedMappingInputFormat(),
            splitOrganizer,
            getContext(),
            getConfiguration(),
            this,
            getZkExt());

    long entriesLoaded = 0;
    // Determine how many threads to use based on the number of input splits
    int maxInputSplitThreads = inputSplitPathList.size();
    int numThreads = Math.min(getConfiguration().getNumInputSplitsThreads(),
        maxInputSplitThreads);
    if (LOG.isInfoEnabled()) {
      LOG.info("loadInputSplits: Using " + numThreads + " thread(s), " +
          "originally " + getConfiguration().getNumInputSplitsThreads() +
          " threads(s) for " + inputSplitPathList.size() + " total splits.");
    }

    List<Integer> results =
        ProgressableUtils.getResultsWithNCallables(
            mappingInputSplitsCallableFactory,
            numThreads, "load-mapping-%d", getContext());
    for (Integer result : results) {
      entriesLoaded += result;
    }
    // after all threads finish loading - call postFilling
    localData.getMappingStore().postFilling();
    return entriesLoaded;
  }

  /**
   * Load the vertices from the user-defined
   * {@link org.apache.giraph.io.VertexReader}
   *
   * @return Count of vertices and edges loaded
   */
  private VertexEdgeCount loadVertices() throws KeeperException,
      InterruptedException {
    List<String> inputSplitPathList =
        getZkExt().getChildrenExt(vertexInputSplitsPaths.getPath(),
            false, false, true);

    InputSplitPathOrganizer splitOrganizer =
        new InputSplitPathOrganizer(getZkExt(),
            inputSplitPathList, getWorkerInfo().getHostname(),
            getConfiguration().useInputSplitLocality());
    vertexSplitsHandler = new InputSplitsHandler(
        splitOrganizer,
        getZkExt(),
        getContext(),
        BspService.VERTEX_INPUT_SPLIT_RESERVED_NODE,
        BspService.VERTEX_INPUT_SPLIT_FINISHED_NODE);

    VertexInputSplitsCallableFactory<I, V, E> inputSplitsCallableFactory =
        new VertexInputSplitsCallableFactory<I, V, E>(
            getConfiguration().createWrappedVertexInputFormat(),
            getContext(),
            getConfiguration(),
            this,
            vertexSplitsHandler,
            getZkExt());

    return loadInputSplits(inputSplitPathList, inputSplitsCallableFactory);
  }

  /**
   * Load the edges from the user-defined
   * {@link org.apache.giraph.io.EdgeReader}.
   *
   * @return Number of edges loaded
   */
  private long loadEdges() throws KeeperException, InterruptedException {
    List<String> inputSplitPathList =
        getZkExt().getChildrenExt(edgeInputSplitsPaths.getPath(),
            false, false, true);

    InputSplitPathOrganizer splitOrganizer =
        new InputSplitPathOrganizer(getZkExt(),
            inputSplitPathList, getWorkerInfo().getHostname(),
            getConfiguration().useInputSplitLocality());
    edgeSplitsHandler = new InputSplitsHandler(
        splitOrganizer,
        getZkExt(),
        getContext(),
        BspService.EDGE_INPUT_SPLIT_RESERVED_NODE,
        BspService.EDGE_INPUT_SPLIT_FINISHED_NODE);

    EdgeInputSplitsCallableFactory<I, V, E> inputSplitsCallableFactory =
        new EdgeInputSplitsCallableFactory<I, V, E>(
            getConfiguration().createWrappedEdgeInputFormat(),
            getContext(),
            getConfiguration(),
            this,
            edgeSplitsHandler,
            getZkExt());

    return loadInputSplits(inputSplitPathList, inputSplitsCallableFactory).
        getEdgeCount();
  }

  @Override
  public MasterInfo getMasterInfo() {
    return masterInfo;
  }

  @Override
  public List<WorkerInfo> getWorkerInfoList() {
    return workerInfoList;
  }

  /**
   * Ensure the input splits are ready for processing
   *
   * @param inputSplitPaths Input split paths
   * @param inputSplitEvents Input split events
   */
  private void ensureInputSplitsReady(InputSplitPaths inputSplitPaths,
                                      InputSplitEvents inputSplitEvents) {
    while (true) {
      Stat inputSplitsReadyStat;
      try {
        inputSplitsReadyStat = getZkExt().exists(
            inputSplitPaths.getAllReadyPath(), true);
      } catch (KeeperException e) {
        throw new IllegalStateException("ensureInputSplitsReady: " +
            "KeeperException waiting on input splits", e);
      } catch (InterruptedException e) {
        throw new IllegalStateException("ensureInputSplitsReady: " +
            "InterruptedException waiting on input splits", e);
      }
      if (inputSplitsReadyStat != null) {
        break;
      }
      inputSplitEvents.getAllReadyChanged().waitForever();
      inputSplitEvents.getAllReadyChanged().reset();
    }
  }

  /**
   * Mark current worker as done and then wait for all workers
   * to finish processing input splits.
   *
   * @param inputSplitPaths Input split paths
   * @param inputSplitEvents Input split events
   */
  private void markCurrentWorkerDoneThenWaitForOthers(
    InputSplitPaths inputSplitPaths,
    InputSplitEvents inputSplitEvents) {
    String workerInputSplitsDonePath =
        inputSplitPaths.getDonePath() + "/" +
            getWorkerInfo().getHostnameId();
    try {
      getZkExt().createExt(workerInputSplitsDonePath,
          null,
          Ids.OPEN_ACL_UNSAFE,
          CreateMode.PERSISTENT,
          true);
    } catch (KeeperException e) {
      throw new IllegalStateException(
          "markCurrentWorkerDoneThenWaitForOthers: " +
          "KeeperException creating worker done splits", e);
    } catch (InterruptedException e) {
      throw new IllegalStateException(
          "markCurrentWorkerDoneThenWaitForOthers: " +
          "InterruptedException creating worker done splits", e);
    }
    while (true) {
      Stat inputSplitsDoneStat;
      try {
        inputSplitsDoneStat =
            getZkExt().exists(inputSplitPaths.getAllDonePath(),
                true);
      } catch (KeeperException e) {
        throw new IllegalStateException(
            "markCurrentWorkerDoneThenWaitForOthers: " +
            "KeeperException waiting on worker done splits", e);
      } catch (InterruptedException e) {
        throw new IllegalStateException(
            "markCurrentWorkerDoneThenWaitForOthers: " +
            "InterruptedException waiting on worker done splits", e);
      }
      if (inputSplitsDoneStat != null) {
        break;
      }
      inputSplitEvents.getAllDoneChanged().waitForever();
      inputSplitEvents.getAllDoneChanged().reset();
    }
  }

  @Override
  public FinishedSuperstepStats setup() {
    // Unless doing a restart, prepare for computation:
    // 1. Start superstep INPUT_SUPERSTEP (no computation)
    // 2. Wait until the INPUT_SPLIT_ALL_READY_PATH node has been created
    // 3. Process input splits until there are no more.
    // 4. Wait until the INPUT_SPLIT_ALL_DONE_PATH node has been created
    // 5. Process any mutations deriving from add edge requests
    // 6. Wait for superstep INPUT_SUPERSTEP to complete.
    if (getRestartedSuperstep() != UNSET_SUPERSTEP) {
      setCachedSuperstep(getRestartedSuperstep());
      return new FinishedSuperstepStats(0, false, 0, 0, true,
          CheckpointStatus.NONE);
    }

    JSONObject jobState = getJobState();
    if (jobState != null) {
      try {
        if ((ApplicationState.valueOf(jobState.getString(JSONOBJ_STATE_KEY)) ==
            ApplicationState.START_SUPERSTEP) &&
            jobState.getLong(JSONOBJ_SUPERSTEP_KEY) ==
            getSuperstep()) {
          if (LOG.isInfoEnabled()) {
            LOG.info("setup: Restarting from an automated " +
                "checkpointed superstep " +
                getSuperstep() + ", attempt " +
                getApplicationAttempt());
          }
          setRestartedSuperstep(getSuperstep());
          return new FinishedSuperstepStats(0, false, 0, 0, true,
              CheckpointStatus.NONE);
        }
      } catch (JSONException e) {
        throw new RuntimeException(
            "setup: Failed to get key-values from " +
                jobState.toString(), e);
      }
    }

    // Add the partitions that this worker owns
    Collection<? extends PartitionOwner> masterSetPartitionOwners =
        startSuperstep();
    workerGraphPartitioner.updatePartitionOwners(
        getWorkerInfo(), masterSetPartitionOwners);

/*if[HADOOP_NON_SECURE]
    workerClient.setup();
else[HADOOP_NON_SECURE]*/
    workerClient.setup(getConfiguration().authenticate());
/*end[HADOOP_NON_SECURE]*/

    // Initialize aggregator at worker side during setup.
    // Do this just before vertex and edge loading.
    globalCommHandler.prepareSuperstep(workerAggregatorRequestProcessor);

    VertexEdgeCount vertexEdgeCount;
    long entriesLoaded;

    if (getConfiguration().hasMappingInputFormat()) {
      // Ensure the mapping InputSplits are ready for processing
      ensureInputSplitsReady(mappingInputSplitsPaths, mappingInputSplitsEvents);
      getContext().progress();
      try {
        entriesLoaded = loadMapping();
        // successfully loaded mapping
        // now initialize graphPartitionerFactory with this data
        getGraphPartitionerFactory().initialize(localData);
      } catch (InterruptedException e) {
        throw new IllegalStateException(
            "setup: loadMapping failed with InterruptedException", e);
      } catch (KeeperException e) {
        throw new IllegalStateException(
            "setup: loadMapping failed with KeeperException", e);
      }
      getContext().progress();
      if (LOG.isInfoEnabled()) {
        LOG.info("setup: Finally loaded a total of " +
            entriesLoaded + " entries from inputSplits");
      }

      // Workers wait for each other to finish, coordinated by master
      markCurrentWorkerDoneThenWaitForOthers(mappingInputSplitsPaths,
          mappingInputSplitsEvents);
      // Print stats for data stored in localData once mapping is fully
      // loaded on all the workers
      localData.printStats();
    }

    if (getConfiguration().hasVertexInputFormat()) {
      // Ensure the vertex InputSplits are ready for processing
      ensureInputSplitsReady(vertexInputSplitsPaths, vertexInputSplitsEvents);
      getContext().progress();
      try {
        vertexEdgeCount = loadVertices();
      } catch (InterruptedException e) {
        throw new IllegalStateException(
            "setup: loadVertices failed with InterruptedException", e);
      } catch (KeeperException e) {
        throw new IllegalStateException(
            "setup: loadVertices failed with KeeperException", e);
      }
      getContext().progress();
    } else {
      vertexEdgeCount = new VertexEdgeCount();
    }
    WorkerProgress.get().finishLoadingVertices();

    if (getConfiguration().hasEdgeInputFormat()) {
      // Ensure the edge InputSplits are ready for processing
      ensureInputSplitsReady(edgeInputSplitsPaths, edgeInputSplitsEvents);
      getContext().progress();
      try {
        vertexEdgeCount = vertexEdgeCount.incrVertexEdgeCount(0, loadEdges());
      } catch (InterruptedException e) {
        throw new IllegalStateException(
            "setup: loadEdges failed with InterruptedException", e);
      } catch (KeeperException e) {
        throw new IllegalStateException(
            "setup: loadEdges failed with KeeperException", e);
      }
      getContext().progress();
    }
    WorkerProgress.get().finishLoadingEdges();

    if (LOG.isInfoEnabled()) {
      LOG.info("setup: Finally loaded a total of " + vertexEdgeCount);
    }

    if (getConfiguration().hasVertexInputFormat()) {
      // Workers wait for each other to finish, coordinated by master
      markCurrentWorkerDoneThenWaitForOthers(vertexInputSplitsPaths,
          vertexInputSplitsEvents);
    }

    if (getConfiguration().hasEdgeInputFormat()) {
      // Workers wait for each other to finish, coordinated by master
      markCurrentWorkerDoneThenWaitForOthers(edgeInputSplitsPaths,
          edgeInputSplitsEvents);
    }

    // Create remaining partitions owned by this worker.
    for (PartitionOwner partitionOwner : masterSetPartitionOwners) {
      if (partitionOwner.getWorkerInfo().equals(getWorkerInfo()) &&
          !getPartitionStore().hasPartition(
              partitionOwner.getPartitionId())) {
        Partition<I, V, E> partition =
            getConfiguration().createPartition(
                partitionOwner.getPartitionId(), getContext());
        getPartitionStore().addPartition(partition);
      }
    }

    // remove mapping store if possible
    localData.removeMappingStoreIfPossible();

    if (getConfiguration().hasEdgeInputFormat()) {
      // Move edges from temporary storage to their source vertices.
      getServerData().getEdgeStore().moveEdgesToVertices();
    }

    // Generate the partition stats for the input superstep and process
    // if necessary
    List<PartitionStats> partitionStatsList =
        new ArrayList<PartitionStats>();
    PartitionStore<I, V, E> partitionStore = getPartitionStore();
    for (Integer partitionId : partitionStore.getPartitionIds()) {
      PartitionStats partitionStats =
          new PartitionStats(partitionId,
              partitionStore.getPartitionVertexCount(partitionId),
              0,
              partitionStore.getPartitionEdgeCount(partitionId),
              0, 0);
      partitionStatsList.add(partitionStats);
    }
    workerGraphPartitioner.finalizePartitionStats(
        partitionStatsList, getPartitionStore());

    return finishSuperstep(partitionStatsList, null);
  }

  /**
   * Register the health of this worker for a given superstep
   *
   * @param superstep Superstep to register health on
   */
  private void registerHealth(long superstep) {
    JSONArray hostnamePort = new JSONArray();
    hostnamePort.put(getHostname());

    hostnamePort.put(workerInfo.getPort());

    String myHealthPath = null;
    if (isHealthy()) {
      myHealthPath = getWorkerInfoHealthyPath(getApplicationAttempt(),
          getSuperstep());
    } else {
      myHealthPath = getWorkerInfoUnhealthyPath(getApplicationAttempt(),
          getSuperstep());
    }
    myHealthPath = myHealthPath + "/" + workerInfo.getHostnameId();
    try {
      myHealthZnode = getZkExt().createExt(
          myHealthPath,
          WritableUtils.writeToByteArray(workerInfo),
          Ids.OPEN_ACL_UNSAFE,
          CreateMode.EPHEMERAL,
          true);
    } catch (KeeperException.NodeExistsException e) {
      LOG.warn("registerHealth: myHealthPath already exists (likely " +
          "from previous failure): " + myHealthPath +
          ".  Waiting for change in attempts " +
          "to re-join the application");
      getApplicationAttemptChangedEvent().waitForever();
      if (LOG.isInfoEnabled()) {
        LOG.info("registerHealth: Got application " +
            "attempt changed event, killing self");
      }
      throw new IllegalStateException(
          "registerHealth: Trying " +
              "to get the new application attempt by killing self", e);
    } catch (KeeperException e) {
      throw new IllegalStateException("Creating " + myHealthPath +
          " failed with KeeperException", e);
    } catch (InterruptedException e) {
      throw new IllegalStateException("Creating " + myHealthPath +
          " failed with InterruptedException", e);
    }
    if (LOG.isInfoEnabled()) {
      LOG.info("registerHealth: Created my health node for attempt=" +
          getApplicationAttempt() + ", superstep=" +
          getSuperstep() + " with " + myHealthZnode +
          " and workerInfo= " + workerInfo);
    }
  }

  /**
   * Do this to help notify the master quicker that this worker has failed.
   */
  private void unregisterHealth() {
    LOG.error("unregisterHealth: Got failure, unregistering health on " +
        myHealthZnode + " on superstep " + getSuperstep());
    try {
      getZkExt().deleteExt(myHealthZnode, -1, false);
    } catch (InterruptedException e) {
      throw new IllegalStateException(
          "unregisterHealth: InterruptedException - Couldn't delete " +
              myHealthZnode, e);
    } catch (KeeperException e) {
      throw new IllegalStateException(
          "unregisterHealth: KeeperException - Couldn't delete " +
              myHealthZnode, e);
    }
  }

  @Override
  public void failureCleanup() {
    unregisterHealth();
  }

  @Override
  public Collection<? extends PartitionOwner> startSuperstep() {
    // Algorithm:
    // 1. Communication service will combine message from previous
    //    superstep
    // 2. Register my health for the next superstep.
    // 3. Wait until the partition assignment is complete and get it
    // 4. Get the aggregator values from the previous superstep
    if (getSuperstep() != INPUT_SUPERSTEP) {
      workerServer.prepareSuperstep();
    }

    registerHealth(getSuperstep());

    String addressesAndPartitionsPath =
        getAddressesAndPartitionsPath(getApplicationAttempt(),
            getSuperstep());
    AddressesAndPartitionsWritable addressesAndPartitions =
        new AddressesAndPartitionsWritable(
            workerGraphPartitioner.createPartitionOwner().getClass());
    try {
      while (getZkExt().exists(addressesAndPartitionsPath, true) ==
          null) {
        getAddressesAndPartitionsReadyChangedEvent().waitForever();
        getAddressesAndPartitionsReadyChangedEvent().reset();
      }
      WritableUtils.readFieldsFromZnode(
          getZkExt(),
          addressesAndPartitionsPath,
          false,
          null,
          addressesAndPartitions);
    } catch (KeeperException e) {
      throw new IllegalStateException(
          "startSuperstep: KeeperException getting assignments", e);
    } catch (InterruptedException e) {
      throw new IllegalStateException(
          "startSuperstep: InterruptedException getting assignments", e);
    }

    workerInfoList.clear();
    workerInfoList = addressesAndPartitions.getWorkerInfos();
    masterInfo = addressesAndPartitions.getMasterInfo();

    if (LOG.isInfoEnabled()) {
      LOG.info("startSuperstep: " + masterInfo);
      LOG.info("startSuperstep: Ready for computation on superstep " +
          getSuperstep() + " since worker " +
          "selection and vertex range assignments are done in " +
          addressesAndPartitionsPath);
    }

    getContext().setStatus("startSuperstep: " +
        getGraphTaskManager().getGraphFunctions().toString() +
        " - Attempt=" + getApplicationAttempt() +
        ", Superstep=" + getSuperstep());

    if (LOG.isDebugEnabled()) {
      LOG.debug("startSuperstep: addressesAndPartitions" +
          addressesAndPartitions.getWorkerInfos());
      for (PartitionOwner partitionOwner : addressesAndPartitions
          .getPartitionOwners()) {
        LOG.debug(partitionOwner.getPartitionId() + " " +
            partitionOwner.getWorkerInfo());
      }
    }

    return addressesAndPartitions.getPartitionOwners();
  }

  @Override
  public FinishedSuperstepStats finishSuperstep(
      List<PartitionStats> partitionStatsList,
      GiraphTimerContext superstepTimerContext) {
    // This barrier blocks until success (or the master signals it to
    // restart).
    //
    // Master will coordinate the barriers and aggregate "doneness" of all
    // the vertices.  Each worker will:
    // 1. Ensure that the requests are complete
    // 2. Execute user postSuperstep() if necessary.
    // 3. Save aggregator values that are in use.
    // 4. Report the statistics (vertices, edges, messages, etc.)
    //    of this worker
    // 5. Let the master know it is finished.
    // 6. Wait for the master's superstep info, and check if done
    waitForRequestsToFinish();

    getGraphTaskManager().notifyFinishedCommunication();

    long workerSentMessages = 0;
    long workerSentMessageBytes = 0;
    long localVertices = 0;
    for (PartitionStats partitionStats : partitionStatsList) {
      workerSentMessages += partitionStats.getMessagesSentCount();
      workerSentMessageBytes += partitionStats.getMessageBytesSentCount();
      localVertices += partitionStats.getVertexCount();
    }

    if (getSuperstep() != INPUT_SUPERSTEP) {
      postSuperstepCallbacks();
    } else {
      if (getConfiguration().hasVertexInputFormat()) {
        vertexSplitsHandler.setDoneReadingGraph(true);
      }
      if (getConfiguration().hasEdgeInputFormat()) {
        edgeSplitsHandler.setDoneReadingGraph(true);
      }
    }

    globalCommHandler.finishSuperstep(workerAggregatorRequestProcessor);

    MessageStore<I, Writable> incomingMessageStore =
        getServerData().getIncomingMessageStore();
    if (incomingMessageStore instanceof AsyncMessageStoreWrapper) {
      ((AsyncMessageStoreWrapper) incomingMessageStore).waitToComplete();
    }

    if (LOG.isInfoEnabled()) {
      LOG.info("finishSuperstep: Superstep " + getSuperstep() +
          ", messages = " + workerSentMessages + " " +
          ", message bytes = " + workerSentMessageBytes + " , " +
          MemoryUtils.getRuntimeMemoryStats());
    }

    if (superstepTimerContext != null) {
      superstepTimerContext.stop();
    }
    writeFinshedSuperstepInfoToZK(partitionStatsList,
      workerSentMessages, workerSentMessageBytes);

    LoggerUtils.setStatusAndLog(getContext(), LOG, Level.INFO,
        "finishSuperstep: (waiting for rest " +
            "of workers) " +
            getGraphTaskManager().getGraphFunctions().toString() +
            " - Attempt=" + getApplicationAttempt() +
            ", Superstep=" + getSuperstep());

    String superstepFinishedNode =
        getSuperstepFinishedPath(getApplicationAttempt(), getSuperstep());

    waitForOtherWorkers(superstepFinishedNode);

    GlobalStats globalStats = new GlobalStats();
    SuperstepClasses superstepClasses = SuperstepClasses.createToRead(
        getConfiguration());
    WritableUtils.readFieldsFromZnode(
        getZkExt(), superstepFinishedNode, false, null, globalStats,
        superstepClasses);
    if (LOG.isInfoEnabled()) {
      LOG.info("finishSuperstep: Completed superstep " + getSuperstep() +
          " with global stats " + globalStats + " and classes " +
          superstepClasses);
    }
    getContext().setStatus("finishSuperstep: (all workers done) " +
        getGraphTaskManager().getGraphFunctions().toString() +
        " - Attempt=" + getApplicationAttempt() +
        ", Superstep=" + getSuperstep());
    incrCachedSuperstep();
    getConfiguration().updateSuperstepClasses(superstepClasses);

    return new FinishedSuperstepStats(
        localVertices,
        globalStats.getHaltComputation(),
        globalStats.getVertexCount(),
        globalStats.getEdgeCount(),
        false,
        globalStats.getCheckpointStatus());
  }

  /**
   * Handle post-superstep callbacks
   */
  private void postSuperstepCallbacks() {
    GiraphTimerContext timerContext = wcPostSuperstepTimer.time();
    getWorkerContext().postSuperstep();
    timerContext.stop();
    getContext().progress();

    for (WorkerObserver obs : getWorkerObservers()) {
      obs.postSuperstep(getSuperstep());
      getContext().progress();
    }
  }

  /**
   * Wait for all the requests to finish.
   */
  private void waitForRequestsToFinish() {
    if (LOG.isInfoEnabled()) {
      LOG.info("finishSuperstep: Waiting on all requests, superstep " +
          getSuperstep() + " " +
          MemoryUtils.getRuntimeMemoryStats());
    }
    GiraphTimerContext timerContext = waitRequestsTimer.time();
    workerClient.waitAllRequests();
    timerContext.stop();
  }

  /**
   * Wait for all the other Workers to finish the superstep.
   *
   * @param superstepFinishedNode ZooKeeper path to wait on.
   */
  private void waitForOtherWorkers(String superstepFinishedNode) {
    try {
      while (getZkExt().exists(superstepFinishedNode, true) == null) {
        getSuperstepFinishedEvent().waitForever();
        getSuperstepFinishedEvent().reset();
      }
    } catch (KeeperException e) {
      throw new IllegalStateException(
          "finishSuperstep: Failed while waiting for master to " +
              "signal completion of superstep " + getSuperstep(), e);
    } catch (InterruptedException e) {
      throw new IllegalStateException(
          "finishSuperstep: Failed while waiting for master to " +
              "signal completion of superstep " + getSuperstep(), e);
    }
  }

  /**
   * Write finished superstep info to ZooKeeper.
   *
   * @param partitionStatsList List of partition stats from superstep.
   * @param workerSentMessages Number of messages sent in superstep.
   * @param workerSentMessageBytes Number of message bytes sent
   *                               in superstep.
   */
  private void writeFinshedSuperstepInfoToZK(
      List<PartitionStats> partitionStatsList, long workerSentMessages,
      long workerSentMessageBytes) {
    Collection<PartitionStats> finalizedPartitionStats =
        workerGraphPartitioner.finalizePartitionStats(
            partitionStatsList, getPartitionStore());
    List<PartitionStats> finalizedPartitionStatsList =
        new ArrayList<PartitionStats>(finalizedPartitionStats);
    byte[] partitionStatsBytes =
        WritableUtils.writeListToByteArray(finalizedPartitionStatsList);
    WorkerSuperstepMetrics metrics = new WorkerSuperstepMetrics();
    metrics.readFromRegistry();
    byte[] metricsBytes = WritableUtils.writeToByteArray(metrics);

    JSONObject workerFinishedInfoObj = new JSONObject();
    try {
      workerFinishedInfoObj.put(JSONOBJ_PARTITION_STATS_KEY,
          Base64.encodeBytes(partitionStatsBytes));
      workerFinishedInfoObj.put(JSONOBJ_NUM_MESSAGES_KEY, workerSentMessages);
      workerFinishedInfoObj.put(JSONOBJ_NUM_MESSAGE_BYTES_KEY,
        workerSentMessageBytes);
      workerFinishedInfoObj.put(JSONOBJ_METRICS_KEY,
          Base64.encodeBytes(metricsBytes));
    } catch (JSONException e) {
      throw new RuntimeException(e);
    }

    String finishedWorkerPath =
        getWorkerFinishedPath(getApplicationAttempt(), getSuperstep()) +
        "/" + getHostnamePartitionId();
    try {
      getZkExt().createExt(finishedWorkerPath,
          workerFinishedInfoObj.toString().getBytes(Charset.defaultCharset()),
          Ids.OPEN_ACL_UNSAFE,
          CreateMode.PERSISTENT,
          true);
    } catch (KeeperException.NodeExistsException e) {
      LOG.warn("finishSuperstep: finished worker path " +
          finishedWorkerPath + " already exists!");
    } catch (KeeperException e) {
      throw new IllegalStateException("Creating " + finishedWorkerPath +
          " failed with KeeperException", e);
    } catch (InterruptedException e) {
      throw new IllegalStateException("Creating " + finishedWorkerPath +
          " failed with InterruptedException", e);
    }
  }

  /**
   * Save the vertices using the user-defined VertexOutputFormat from our
   * vertexArray based on the split.
   *
   * @param numLocalVertices Number of local vertices
   * @throws InterruptedException
   */
  private void saveVertices(long numLocalVertices) throws IOException,
      InterruptedException {
    ImmutableClassesGiraphConfiguration<I, V, E>  conf = getConfiguration();

    if (conf.getVertexOutputFormatClass() == null) {
      LOG.warn("saveVertices: " +
          GiraphConstants.VERTEX_OUTPUT_FORMAT_CLASS +
          " not specified -- there will be no saved output");
      return;
    }
    if (conf.doOutputDuringComputation()) {
      if (LOG.isInfoEnabled()) {
        LOG.info("saveVertices: The option for doing output during " +
            "computation is selected, so there will be no saving of the " +
            "output in the end of application");
      }
      return;
    }

    final int numPartitions = getPartitionStore().getNumPartitions();
    int numThreads = Math.min(getConfiguration().getNumOutputThreads(),
        numPartitions);
    LoggerUtils.setStatusAndLog(getContext(), LOG, Level.INFO,
        "saveVertices: Starting to save " + numLocalVertices + " vertices " +
            "using " + numThreads + " threads");
    final VertexOutputFormat<I, V, E> vertexOutputFormat =
        getConfiguration().createWrappedVertexOutputFormat();

    final Queue<Integer> partitionIdQueue =
        (numPartitions == 0) ? new LinkedList<Integer>() :
            new ArrayBlockingQueue<Integer>(numPartitions);
    Iterables.addAll(partitionIdQueue, getPartitionStore().getPartitionIds());

    long verticesToStore = 0;
    PartitionStore<I, V, E> partitionStore = getPartitionStore();
    for (int partitionId : partitionStore.getPartitionIds()) {
      verticesToStore += partitionStore.getPartitionVertexCount(partitionId);
    }
    WorkerProgress.get().startStoring(
        verticesToStore, getPartitionStore().getNumPartitions());

    CallableFactory<Void> callableFactory = new CallableFactory<Void>() {
      @Override
      public Callable<Void> newCallable(int callableId) {
        return new Callable<Void>() {
          /** How often to update WorkerProgress */
          private static final long VERTICES_TO_UPDATE_PROGRESS = 100000;

          @Override
          public Void call() throws Exception {
            VertexWriter<I, V, E> vertexWriter =
                vertexOutputFormat.createVertexWriter(getContext());
            vertexWriter.setConf(getConfiguration());
            vertexWriter.initialize(getContext());
            long nextPrintVertices = 0;
            long nextUpdateProgressVertices = VERTICES_TO_UPDATE_PROGRESS;
            long nextPrintMsecs = System.currentTimeMillis() + 15000;
            int partitionIndex = 0;
            int numPartitions = getPartitionStore().getNumPartitions();
            while (!partitionIdQueue.isEmpty()) {
              Integer partitionId = partitionIdQueue.poll();
              if (partitionId == null) {
                break;
              }

              Partition<I, V, E> partition =
                  getPartitionStore().getOrCreatePartition(partitionId);
              long verticesWritten = 0;
              for (Vertex<I, V, E> vertex : partition) {
                vertexWriter.writeVertex(vertex);
                ++verticesWritten;

                // Update status at most every 250k vertices or 15 seconds
                if (verticesWritten > nextPrintVertices &&
                    System.currentTimeMillis() > nextPrintMsecs) {
                  LoggerUtils.setStatusAndLog(getContext(), LOG, Level.INFO,
                      "saveVertices: Saved " + verticesWritten + " out of " +
                          partition.getVertexCount() + " partition vertices, " +
                          "on partition " + partitionIndex +
                          " out of " + numPartitions);
                  nextPrintMsecs = System.currentTimeMillis() + 15000;
                  nextPrintVertices = verticesWritten + 250000;
                }

                if (verticesWritten >= nextUpdateProgressVertices) {
                  WorkerProgress.get().addVerticesStored(
                      VERTICES_TO_UPDATE_PROGRESS);
                  nextUpdateProgressVertices += VERTICES_TO_UPDATE_PROGRESS;
                }
              }
              getPartitionStore().putPartition(partition);
              ++partitionIndex;
              WorkerProgress.get().addVerticesStored(
                  verticesWritten % VERTICES_TO_UPDATE_PROGRESS);
              WorkerProgress.get().incrementPartitionsStored();
            }
            vertexWriter.close(getContext()); // the temp results are saved now
            return null;
          }
        };
      }
    };
    ProgressableUtils.getResultsWithNCallables(callableFactory, numThreads,
        "save-vertices-%d", getContext());

    LoggerUtils.setStatusAndLog(getContext(), LOG, Level.INFO,
      "saveVertices: Done saving vertices.");
    // YARN: must complete the commit the "task" output, Hadoop isn't there.
    if (getConfiguration().isPureYarnJob() &&
      getConfiguration().getVertexOutputFormatClass() != null) {
      try {
        OutputCommitter outputCommitter =
          vertexOutputFormat.getOutputCommitter(getContext());
        if (outputCommitter.needsTaskCommit(getContext())) {
          LoggerUtils.setStatusAndLog(getContext(), LOG, Level.INFO,
            "OutputCommitter: committing task output.");
          // transfer from temp dirs to "task commit" dirs to prep for
          // the master's OutputCommitter#commitJob(context) call to finish.
          outputCommitter.commitTask(getContext());
        }
      } catch (InterruptedException ie) {
        LOG.error("Interrupted while attempting to obtain " +
          "OutputCommitter.", ie);
      } catch (IOException ioe) {
        LOG.error("Master task's attempt to commit output has " +
          "FAILED.", ioe);
      }
    }
  }

  /**
   * Save the edges using the user-defined EdgeOutputFormat from our
   * vertexArray based on the split.
   *
   * @throws InterruptedException
   */
  private void saveEdges() throws IOException, InterruptedException {
    final ImmutableClassesGiraphConfiguration<I, V, E>  conf =
      getConfiguration();

    if (conf.getEdgeOutputFormatClass() == null) {
      LOG.warn("saveEdges: " +
               GiraphConstants.EDGE_OUTPUT_FORMAT_CLASS +
               "Make sure that the EdgeOutputFormat is not required.");
      return;
    }

    final int numPartitions = getPartitionStore().getNumPartitions();
    int numThreads = Math.min(conf.getNumOutputThreads(),
        numPartitions);
    LoggerUtils.setStatusAndLog(getContext(), LOG, Level.INFO,
        "saveEdges: Starting to save the edges using " +
        numThreads + " threads");
    final EdgeOutputFormat<I, V, E> edgeOutputFormat =
        conf.createWrappedEdgeOutputFormat();

    final Queue<Integer> partitionIdQueue =
        (numPartitions == 0) ? new LinkedList<Integer>() :
            new ArrayBlockingQueue<Integer>(numPartitions);
    Iterables.addAll(partitionIdQueue, getPartitionStore().getPartitionIds());

    CallableFactory<Void> callableFactory = new CallableFactory<Void>() {
      @Override
      public Callable<Void> newCallable(int callableId) {
        return new Callable<Void>() {
          @Override
          public Void call() throws Exception {
            EdgeWriter<I, V, E>  edgeWriter =
                edgeOutputFormat.createEdgeWriter(getContext());
            edgeWriter.setConf(conf);
            edgeWriter.initialize(getContext());

            long nextPrintVertices = 0;
            long nextPrintMsecs = System.currentTimeMillis() + 15000;
            int partitionIndex = 0;
            int numPartitions = getPartitionStore().getNumPartitions();
            while (!partitionIdQueue.isEmpty()) {
              Integer partitionId = partitionIdQueue.poll();
              if (partitionId == null) {
                break;
              }

              Partition<I, V, E> partition =
                  getPartitionStore().getOrCreatePartition(partitionId);
              long vertices = 0;
              long edges = 0;
              long partitionEdgeCount = partition.getEdgeCount();
              for (Vertex<I, V, E> vertex : partition) {
                for (Edge<I, E> edge : vertex.getEdges()) {
                  edgeWriter.writeEdge(vertex.getId(), vertex.getValue(), edge);
                  ++edges;
                }
                ++vertices;

                // Update status at most every 250k vertices or 15 seconds
                if (vertices > nextPrintVertices &&
                    System.currentTimeMillis() > nextPrintMsecs) {
                  LoggerUtils.setStatusAndLog(getContext(), LOG, Level.INFO,
                      "saveEdges: Saved " + edges +
                      " edges out of " + partitionEdgeCount +
                      " partition edges, on partition " + partitionIndex +
                      " out of " + numPartitions);
                  nextPrintMsecs = System.currentTimeMillis() + 15000;
                  nextPrintVertices = vertices + 250000;
                }
              }
              getPartitionStore().putPartition(partition);
              ++partitionIndex;
            }
            edgeWriter.close(getContext()); // the temp results are saved now
            return null;
          }
        };
      }
    };
    ProgressableUtils.getResultsWithNCallables(callableFactory, numThreads,
        "save-vertices-%d", getContext());

    LoggerUtils.setStatusAndLog(getContext(), LOG, Level.INFO,
      "saveEdges: Done saving edges.");
    // YARN: must complete the commit the "task" output, Hadoop isn't there.
    if (conf.isPureYarnJob() &&
      conf.getVertexOutputFormatClass() != null) {
      try {
        OutputCommitter outputCommitter =
          edgeOutputFormat.getOutputCommitter(getContext());
        if (outputCommitter.needsTaskCommit(getContext())) {
          LoggerUtils.setStatusAndLog(getContext(), LOG, Level.INFO,
            "OutputCommitter: committing task output.");
          // transfer from temp dirs to "task commit" dirs to prep for
          // the master's OutputCommitter#commitJob(context) call to finish.
          outputCommitter.commitTask(getContext());
        }
      } catch (InterruptedException ie) {
        LOG.error("Interrupted while attempting to obtain " +
          "OutputCommitter.", ie);
      } catch (IOException ioe) {
        LOG.error("Master task's attempt to commit output has " +
          "FAILED.", ioe);
      }
    }
  }

  @Override
  public void cleanup(FinishedSuperstepStats finishedSuperstepStats)
    throws IOException, InterruptedException {
    workerClient.closeConnections();
    setCachedSuperstep(getSuperstep() - 1);
    if (finishedSuperstepStats.getCheckpointStatus() !=
        CheckpointStatus.CHECKPOINT_AND_HALT) {
      saveVertices(finishedSuperstepStats.getLocalVertexCount());
      saveEdges();
    }
    WorkerProgress.get().finishStoring();
    if (workerProgressWriter != null) {
      workerProgressWriter.stop();
    }
    getPartitionStore().shutdown();
    // All worker processes should denote they are done by adding special
    // znode.  Once the number of znodes equals the number of partitions
    // for workers and masters, the master will clean up the ZooKeeper
    // znodes associated with this job.
    String workerCleanedUpPath = cleanedUpPath  + "/" +
        getTaskPartition() + WORKER_SUFFIX;
    try {
      String finalFinishedPath =
          getZkExt().createExt(workerCleanedUpPath,
              null,
              Ids.OPEN_ACL_UNSAFE,
              CreateMode.PERSISTENT,
              true);
      if (LOG.isInfoEnabled()) {
        LOG.info("cleanup: Notifying master its okay to cleanup with " +
            finalFinishedPath);
      }
    } catch (KeeperException.NodeExistsException e) {
      if (LOG.isInfoEnabled()) {
        LOG.info("cleanup: Couldn't create finished node '" +
            workerCleanedUpPath);
      }
    } catch (KeeperException e) {
      // Cleaning up, it's okay to fail after cleanup is successful
      LOG.error("cleanup: Got KeeperException on notification " +
          "to master about cleanup", e);
    } catch (InterruptedException e) {
      // Cleaning up, it's okay to fail after cleanup is successful
      LOG.error("cleanup: Got InterruptedException on notification " +
          "to master about cleanup", e);
    }
    try {
      getZkExt().close();
    } catch (InterruptedException e) {
      // cleanup phase -- just log the error
      LOG.error("cleanup: Zookeeper failed to close with " + e);
    }

    if (getConfiguration().metricsEnabled()) {
      GiraphMetrics.get().dumpToStream(System.err);
    }

    // Preferably would shut down the service only after
    // all clients have disconnected (or the exceptions on the
    // client side ignored).
    workerServer.close();
  }

  @Override
  public void storeCheckpoint() throws IOException {
    LoggerUtils.setStatusAndLog(getContext(), LOG, Level.INFO,
        "storeCheckpoint: Starting checkpoint " +
            getGraphTaskManager().getGraphFunctions().toString() +
            " - Attempt=" + getApplicationAttempt() +
            ", Superstep=" + getSuperstep());

    // Algorithm:
    // For each partition, dump vertices and messages
    Path metadataFilePath = createCheckpointFilePathSafe(
        CheckpointingUtils.CHECKPOINT_METADATA_POSTFIX);
    Path validFilePath = createCheckpointFilePathSafe(
        CheckpointingUtils.CHECKPOINT_VALID_POSTFIX);
    Path checkpointFilePath = createCheckpointFilePathSafe(
        CheckpointingUtils.CHECKPOINT_DATA_POSTFIX);


    // Metadata is buffered and written at the end since it's small and
    // needs to know how many partitions this worker owns
    FSDataOutputStream metadataOutputStream =
        getFs().create(metadataFilePath);
    metadataOutputStream.writeInt(getPartitionStore().getNumPartitions());

    for (Integer partitionId : getPartitionStore().getPartitionIds()) {
      metadataOutputStream.writeInt(partitionId);
    }
    metadataOutputStream.close();

    storeCheckpointVertices();

    FSDataOutputStream checkpointOutputStream =
        getFs().create(checkpointFilePath);
    workerContext.write(checkpointOutputStream);
    getContext().progress();

    for (Integer partitionId : getPartitionStore().getPartitionIds()) {
      // write messages
      checkpointOutputStream.writeInt(partitionId);
      getServerData().getCurrentMessageStore().writePartition(
          checkpointOutputStream, partitionId);
      getContext().progress();

    }

    List<Writable> w2wMessages =
        getServerData().getCurrentWorkerToWorkerMessages();
    WritableUtils.writeList(w2wMessages, checkpointOutputStream);

    checkpointOutputStream.close();

    getFs().createNewFile(validFilePath);

    // Notify master that checkpoint is stored
    String workerWroteCheckpoint =
        getWorkerWroteCheckpointPath(getApplicationAttempt(),
            getSuperstep()) + "/" + getHostnamePartitionId();
    try {
      getZkExt().createExt(workerWroteCheckpoint,
          new byte[0],
          Ids.OPEN_ACL_UNSAFE,
          CreateMode.PERSISTENT,
          true);
    } catch (KeeperException.NodeExistsException e) {
      LOG.warn("storeCheckpoint: wrote checkpoint worker path " +
          workerWroteCheckpoint + " already exists!");
    } catch (KeeperException e) {
      throw new IllegalStateException("Creating " + workerWroteCheckpoint +
          " failed with KeeperException", e);
    } catch (InterruptedException e) {
      throw new IllegalStateException("Creating " +
          workerWroteCheckpoint +
          " failed with InterruptedException", e);
    }
  }

  /**
   * Create checkpoint file safely. If file already exists remove it first.
   * @param name file extension
   * @return full file path to newly created file
   * @throws IOException
   */
  private Path createCheckpointFilePathSafe(String name) throws IOException {
    Path validFilePath = new Path(getCheckpointBasePath(getSuperstep()) + '.' +
        getWorkerId(workerInfo) + name);
    // Remove these files if they already exist (shouldn't though, unless
    // of previous failure of this worker)
    if (getFs().delete(validFilePath, false)) {
      LOG.warn("storeCheckpoint: Removed " + name + " file " +
          validFilePath);
    }
    return validFilePath;
  }

  /**
   * Returns path to saved checkpoint.
   * Doesn't check if file actually exists.
   * @param superstep saved superstep.
   * @param name extension name
   * @return fill file path to checkpoint file
   */
  private Path getSavedCheckpoint(long superstep, String name) {
    return new Path(getSavedCheckpointBasePath(superstep) + '.' +
        getWorkerId(workerInfo) + name);
  }

  /**
   * Save partitions. To speed up this operation
   * runs in multiple threads.
   */
  private void storeCheckpointVertices() {
    final int numPartitions = getPartitionStore().getNumPartitions();
    int numThreads = Math.min(
        GiraphConstants.NUM_CHECKPOINT_IO_THREADS.get(getConfiguration()),
        numPartitions);

    final Queue<Integer> partitionIdQueue =
        (numPartitions == 0) ? new LinkedList<Integer>() :
            new ArrayBlockingQueue<Integer>(numPartitions);
    Iterables.addAll(partitionIdQueue, getPartitionStore().getPartitionIds());

    final CompressionCodec codec =
        new CompressionCodecFactory(getConfiguration())
            .getCodec(new Path(
                GiraphConstants.CHECKPOINT_COMPRESSION_CODEC
                    .get(getConfiguration())));

    long t0 = System.currentTimeMillis();

    CallableFactory<Void> callableFactory = new CallableFactory<Void>() {
      @Override
      public Callable<Void> newCallable(int callableId) {
        return new Callable<Void>() {

          @Override
          public Void call() throws Exception {
            while (!partitionIdQueue.isEmpty()) {
              Integer partitionId = partitionIdQueue.poll();
              if (partitionId == null) {
                break;
              }
              Path path =
                  createCheckpointFilePathSafe("_" + partitionId +
                      CheckpointingUtils.CHECKPOINT_VERTICES_POSTFIX);

              FSDataOutputStream uncompressedStream =
                  getFs().create(path);


              DataOutputStream stream = codec == null ? uncompressedStream :
                  new DataOutputStream(
                      codec.createOutputStream(uncompressedStream));

              Partition<I, V, E> partition =
                  getPartitionStore().getOrCreatePartition(partitionId);

              partition.write(stream);

              getPartitionStore().putPartition(partition);

              stream.close();
              uncompressedStream.close();
            }
            return null;
          }


        };
      }
    };

    ProgressableUtils.getResultsWithNCallables(callableFactory, numThreads,
        "checkpoint-vertices-%d", getContext());

    LOG.info("Save checkpoint in " + (System.currentTimeMillis() - t0) +
        " ms, using " + numThreads + " threads");
  }

  /**
   * Load saved partitions in multiple threads.
   * @param superstep superstep to load
   * @param partitions list of partitions to load
   */
  private void loadCheckpointVertices(final long superstep,
                                      List<Integer> partitions) {
    int numThreads = Math.min(
        GiraphConstants.NUM_CHECKPOINT_IO_THREADS.get(getConfiguration()),
        partitions.size());

    final Queue<Integer> partitionIdQueue =
        new ConcurrentLinkedQueue<>(partitions);

    final CompressionCodec codec =
        new CompressionCodecFactory(getConfiguration())
            .getCodec(new Path(
                GiraphConstants.CHECKPOINT_COMPRESSION_CODEC
                    .get(getConfiguration())));

    long t0 = System.currentTimeMillis();

    CallableFactory<Void> callableFactory = new CallableFactory<Void>() {
      @Override
      public Callable<Void> newCallable(int callableId) {
        return new Callable<Void>() {

          @Override
          public Void call() throws Exception {
            while (!partitionIdQueue.isEmpty()) {
              Integer partitionId = partitionIdQueue.poll();
              if (partitionId == null) {
                break;
              }
              Path path =
                  getSavedCheckpoint(superstep, "_" + partitionId +
                      CheckpointingUtils.CHECKPOINT_VERTICES_POSTFIX);

              FSDataInputStream compressedStream =
                  getFs().open(path);

              DataInputStream stream = codec == null ? compressedStream :
                  new DataInputStream(
                      codec.createInputStream(compressedStream));

              Partition<I, V, E> partition =
                  getConfiguration().createPartition(partitionId, getContext());

              partition.readFields(stream);

              getPartitionStore().addPartition(partition);

              stream.close();
            }
            return null;
          }

        };
      }
    };

    ProgressableUtils.getResultsWithNCallables(callableFactory, numThreads,
        "load-vertices-%d", getContext());

    LOG.info("Loaded checkpoint in " + (System.currentTimeMillis() - t0) +
        " ms, using " + numThreads + " threads");
  }

  @Override
  public VertexEdgeCount loadCheckpoint(long superstep) {
    Path metadataFilePath = getSavedCheckpoint(
        superstep, CheckpointingUtils.CHECKPOINT_METADATA_POSTFIX);

    Path checkpointFilePath = getSavedCheckpoint(
        superstep, CheckpointingUtils.CHECKPOINT_DATA_POSTFIX);
    // Algorithm:
    // Examine all the partition owners and load the ones
    // that match my hostname and id from the master designated checkpoint
    // prefixes.
    try {
      DataInputStream metadataStream =
          getFs().open(metadataFilePath);

      int partitions = metadataStream.readInt();
      List<Integer> partitionIds = new ArrayList<>(partitions);
      for (int i = 0; i < partitions; i++) {
        int partitionId = metadataStream.readInt();
        partitionIds.add(partitionId);
      }

      loadCheckpointVertices(superstep, partitionIds);

      getContext().progress();

      metadataStream.close();

      DataInputStream checkpointStream =
          getFs().open(checkpointFilePath);
      workerContext.readFields(checkpointStream);

      // Load global stats and superstep classes
      GlobalStats globalStats = new GlobalStats();
      SuperstepClasses superstepClasses = SuperstepClasses.createToRead(
          getConfiguration());
      String finalizedCheckpointPath = getSavedCheckpointBasePath(superstep) +
          CheckpointingUtils.CHECKPOINT_FINALIZED_POSTFIX;
      DataInputStream finalizedStream =
          getFs().open(new Path(finalizedCheckpointPath));
      globalStats.readFields(finalizedStream);
      superstepClasses.readFields(finalizedStream);
      getConfiguration().updateSuperstepClasses(superstepClasses);
      getServerData().resetMessageStores();

      for (int i = 0; i < partitions; i++) {
        int partitionId = checkpointStream.readInt();
        getServerData().getCurrentMessageStore().readFieldsForPartition(
            checkpointStream, partitionId);
      }

      List<Writable> w2wMessages = (List<Writable>) WritableUtils.readList(
          checkpointStream);
      getServerData().getCurrentWorkerToWorkerMessages().addAll(w2wMessages);

      checkpointStream.close();

      if (LOG.isInfoEnabled()) {
        LOG.info("loadCheckpoint: Loaded " +
            workerGraphPartitioner.getPartitionOwners().size() +
            " total.");
      }

      // Communication service needs to setup the connections prior to
      // processing vertices
/*if[HADOOP_NON_SECURE]
      workerClient.setup();
else[HADOOP_NON_SECURE]*/
      workerClient.setup(getConfiguration().authenticate());
/*end[HADOOP_NON_SECURE]*/
      return new VertexEdgeCount(globalStats.getVertexCount(),
          globalStats.getEdgeCount());

    } catch (IOException e) {
      throw new RuntimeException(
          "loadCheckpoint: Failed for superstep=" + superstep, e);
    }
  }

  /**
   * Send the worker partitions to their destination workers
   *
   * @param workerPartitionMap Map of worker info to the partitions stored
   *        on this worker to be sent
   */
  private void sendWorkerPartitions(
      Map<WorkerInfo, List<Integer>> workerPartitionMap) {
    List<Entry<WorkerInfo, List<Integer>>> randomEntryList =
        new ArrayList<Entry<WorkerInfo, List<Integer>>>(
            workerPartitionMap.entrySet());
    Collections.shuffle(randomEntryList);
    WorkerClientRequestProcessor<I, V, E> workerClientRequestProcessor =
        new NettyWorkerClientRequestProcessor<I, V, E>(getContext(),
            getConfiguration(), this,
            false /* useOneMessageToManyIdsEncoding */);
    for (Entry<WorkerInfo, List<Integer>> workerPartitionList :
      randomEntryList) {
      for (Integer partitionId : workerPartitionList.getValue()) {
        Partition<I, V, E> partition =
            getPartitionStore().removePartition(partitionId);
        if (partition == null) {
          throw new IllegalStateException(
              "sendWorkerPartitions: Couldn't find partition " +
                  partitionId + " to send to " +
                  workerPartitionList.getKey());
        }
        if (LOG.isInfoEnabled()) {
          LOG.info("sendWorkerPartitions: Sending worker " +
              workerPartitionList.getKey() + " partition " +
              partitionId);
        }
        workerClientRequestProcessor.sendPartitionRequest(
            workerPartitionList.getKey(),
            partition);
      }
    }

    try {
      workerClientRequestProcessor.flush();
      workerClient.waitAllRequests();
    } catch (IOException e) {
      throw new IllegalStateException("sendWorkerPartitions: Flush failed", e);
    }
    String myPartitionExchangeDonePath =
        getPartitionExchangeWorkerPath(
            getApplicationAttempt(), getSuperstep(), getWorkerInfo());
    try {
      getZkExt().createExt(myPartitionExchangeDonePath,
          null,
          Ids.OPEN_ACL_UNSAFE,
          CreateMode.PERSISTENT,
          true);
    } catch (KeeperException e) {
      throw new IllegalStateException(
          "sendWorkerPartitions: KeeperException to create " +
              myPartitionExchangeDonePath, e);
    } catch (InterruptedException e) {
      throw new IllegalStateException(
          "sendWorkerPartitions: InterruptedException to create " +
              myPartitionExchangeDonePath, e);
    }
    if (LOG.isInfoEnabled()) {
      LOG.info("sendWorkerPartitions: Done sending all my partitions.");
    }
  }

  @Override
  public final void exchangeVertexPartitions(
      Collection<? extends PartitionOwner> masterSetPartitionOwners) {
    // 1. Fix the addresses of the partition ids if they have changed.
    // 2. Send all the partitions to their destination workers in a random
    //    fashion.
    // 3. Notify completion with a ZooKeeper stamp
    // 4. Wait for all my dependencies to be done (if any)
    // 5. Add the partitions to myself.
    PartitionExchange partitionExchange =
        workerGraphPartitioner.updatePartitionOwners(
            getWorkerInfo(), masterSetPartitionOwners);
    workerClient.openConnections();

    Map<WorkerInfo, List<Integer>> sendWorkerPartitionMap =
        partitionExchange.getSendWorkerPartitionMap();
    if (!getPartitionStore().isEmpty()) {
      sendWorkerPartitions(sendWorkerPartitionMap);
    }

    Set<WorkerInfo> myDependencyWorkerSet =
        partitionExchange.getMyDependencyWorkerSet();
    Set<String> workerIdSet = new HashSet<String>();
    for (WorkerInfo tmpWorkerInfo : myDependencyWorkerSet) {
      if (!workerIdSet.add(tmpWorkerInfo.getHostnameId())) {
        throw new IllegalStateException(
            "exchangeVertexPartitions: Duplicate entry " + tmpWorkerInfo);
      }
    }
    if (myDependencyWorkerSet.isEmpty() && getPartitionStore().isEmpty()) {
      if (LOG.isInfoEnabled()) {
        LOG.info("exchangeVertexPartitions: Nothing to exchange, " +
            "exiting early");
      }
      return;
    }

    String vertexExchangePath =
        getPartitionExchangePath(getApplicationAttempt(), getSuperstep());
    List<String> workerDoneList;
    try {
      while (true) {
        workerDoneList = getZkExt().getChildrenExt(
            vertexExchangePath, true, false, false);
        workerIdSet.removeAll(workerDoneList);
        if (workerIdSet.isEmpty()) {
          break;
        }
        if (LOG.isInfoEnabled()) {
          LOG.info("exchangeVertexPartitions: Waiting for workers " +
              workerIdSet);
        }
        getPartitionExchangeChildrenChangedEvent().waitForever();
        getPartitionExchangeChildrenChangedEvent().reset();
      }
    } catch (KeeperException | InterruptedException e) {
      throw new RuntimeException(
          "exchangeVertexPartitions: Got runtime exception", e);
    }

    if (LOG.isInfoEnabled()) {
      LOG.info("exchangeVertexPartitions: Done with exchange.");
    }
  }

  /**
   * Get event when the state of a partition exchange has changed.
   *
   * @return Event to check.
   */
  public final BspEvent getPartitionExchangeChildrenChangedEvent() {
    return partitionExchangeChildrenChanged;
  }

  @Override
  protected boolean processEvent(WatchedEvent event) {
    boolean foundEvent = false;
    if (event.getPath().startsWith(masterJobStatePath) &&
        (event.getType() == EventType.NodeChildrenChanged)) {
      if (LOG.isInfoEnabled()) {
        LOG.info("processEvent: Job state changed, checking " +
            "to see if it needs to restart");
      }
      JSONObject jsonObj = getJobState();
      // in YARN, we have to manually commit our own output in 2 stages that we
      // do not have to do in Hadoop-based Giraph. So jsonObj can be null.
      if (getConfiguration().isPureYarnJob() && null == jsonObj) {
        LOG.error("BspServiceWorker#getJobState() came back NULL.");
        return false; // the event has been processed.
      }
      try {
        if ((ApplicationState.valueOf(jsonObj.getString(JSONOBJ_STATE_KEY)) ==
            ApplicationState.START_SUPERSTEP) &&
            jsonObj.getLong(JSONOBJ_APPLICATION_ATTEMPT_KEY) !=
            getApplicationAttempt()) {
          LOG.fatal("processEvent: Worker will restart " +
              "from command - " + jsonObj.toString());
          System.exit(-1);
        }
      } catch (JSONException e) {
        throw new RuntimeException(
            "processEvent: Couldn't properly get job state from " +
                jsonObj.toString());
      }
      foundEvent = true;
    } else if (event.getPath().contains(PARTITION_EXCHANGE_DIR) &&
        event.getType() == EventType.NodeChildrenChanged) {
      if (LOG.isInfoEnabled()) {
        LOG.info("processEvent : partitionExchangeChildrenChanged " +
            "(at least one worker is done sending partitions)");
      }
      partitionExchangeChildrenChanged.signal();
      foundEvent = true;
    }

    return foundEvent;
  }

  @Override
  public WorkerInfo getWorkerInfo() {
    return workerInfo;
  }

  @Override
  public PartitionStore<I, V, E> getPartitionStore() {
    return getServerData().getPartitionStore();
  }

  @Override
  public PartitionOwner getVertexPartitionOwner(I vertexId) {
    return workerGraphPartitioner.getPartitionOwner(vertexId);
  }

  @Override
  public Iterable<? extends PartitionOwner> getPartitionOwners() {
    return workerGraphPartitioner.getPartitionOwners();
  }

  @Override
  public int getPartitionId(I vertexId) {
    PartitionOwner partitionOwner = getVertexPartitionOwner(vertexId);
    return partitionOwner.getPartitionId();
  }

  @Override
  public boolean hasPartition(Integer partitionId) {
    return getPartitionStore().hasPartition(partitionId);
  }

  @Override
  public ServerData<I, V, E> getServerData() {
    return workerServer.getServerData();
  }


  @Override
  public WorkerAggregatorHandler getAggregatorHandler() {
    return globalCommHandler;
  }

  @Override
  public void prepareSuperstep() {
    if (getSuperstep() != INPUT_SUPERSTEP) {
      globalCommHandler.prepareSuperstep(workerAggregatorRequestProcessor);
    }
  }

  @Override
  public SuperstepOutput<I, V, E> getSuperstepOutput() {
    return superstepOutput;
  }

  @Override
  public GlobalStats getGlobalStats() {
    GlobalStats globalStats = new GlobalStats();
    if (getSuperstep() > Math.max(INPUT_SUPERSTEP, getRestartedSuperstep())) {
      String superstepFinishedNode =
          getSuperstepFinishedPath(getApplicationAttempt(),
              getSuperstep() - 1);
      WritableUtils.readFieldsFromZnode(
          getZkExt(), superstepFinishedNode, false, null,
          globalStats);
    }
    return globalStats;
  }
}


File: giraph-core/src/test/java/org/apache/giraph/comm/RequestTest.java
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

package org.apache.giraph.comm;

import org.apache.giraph.comm.netty.NettyClient;
import org.apache.giraph.comm.netty.NettyServer;
import org.apache.giraph.comm.netty.handler.WorkerRequestServerHandler;
import org.apache.giraph.comm.requests.SendPartitionMutationsRequest;
import org.apache.giraph.comm.requests.SendVertexRequest;
import org.apache.giraph.comm.requests.SendWorkerMessagesRequest;
import org.apache.giraph.comm.requests.SendWorkerOneMessageToManyRequest;
import org.apache.giraph.conf.GiraphConfiguration;
import org.apache.giraph.conf.GiraphConstants;
import org.apache.giraph.conf.ImmutableClassesGiraphConfiguration;
import org.apache.giraph.edge.Edge;
import org.apache.giraph.edge.EdgeFactory;
import org.apache.giraph.factories.TestMessageValueFactory;
import org.apache.giraph.graph.Vertex;
import org.apache.giraph.graph.VertexMutations;
import org.apache.giraph.metrics.GiraphMetrics;
import org.apache.giraph.partition.Partition;
import org.apache.giraph.partition.PartitionStore;
import org.apache.giraph.utils.ByteArrayOneMessageToManyIds;
import org.apache.giraph.utils.VertexIdMessages;
import org.apache.giraph.utils.ByteArrayVertexIdMessages;
import org.apache.giraph.utils.ExtendedDataOutput;
import org.apache.giraph.utils.IntNoOpComputation;
import org.apache.giraph.utils.MockUtils;
import org.apache.giraph.utils.PairList;
import org.apache.giraph.worker.WorkerInfo;
import org.apache.hadoop.io.IntWritable;
import org.apache.hadoop.mapreduce.Mapper.Context;
import org.junit.Before;
import org.junit.Test;

import com.google.common.collect.Lists;
import com.google.common.collect.Maps;

import java.io.IOException;
import java.util.Map;
import java.util.Map.Entry;
import java.util.concurrent.ConcurrentMap;

import static org.junit.Assert.assertEquals;
import static org.junit.Assert.assertTrue;
import static org.mockito.Mockito.mock;
import static org.mockito.Mockito.when;

/**
 * Test all the different netty requests.
 */
@SuppressWarnings("unchecked")
public class RequestTest {
  /** Configuration */
  private ImmutableClassesGiraphConfiguration conf;
  /** Server data */
  private ServerData<IntWritable, IntWritable, IntWritable> serverData;
  /** Server */
  private NettyServer server;
  /** Client */
  private NettyClient client;
  /** Worker info */
  private WorkerInfo workerInfo;

  @Before
  public void setUp() throws IOException {
    // Setup the conf
    GiraphConfiguration tmpConf = new GiraphConfiguration();
    GiraphConstants.COMPUTATION_CLASS.set(tmpConf, IntNoOpComputation.class);
    conf = new ImmutableClassesGiraphConfiguration(tmpConf);

    @SuppressWarnings("rawtypes")
    Context context = mock(Context.class);
    when(context.getConfiguration()).thenReturn(conf);

    // Start the service
    serverData = MockUtils.createNewServerData(conf, context);
    serverData.prepareSuperstep();
    workerInfo = new WorkerInfo();
    server = new NettyServer(conf,
        new WorkerRequestServerHandler.Factory(serverData), workerInfo,
            context, new MockExceptionHandler());
    server.start();

    workerInfo.setInetSocketAddress(server.getMyAddress());
    client = new NettyClient(context, conf, new WorkerInfo(),
        new MockExceptionHandler());
    client.connectAllAddresses(
        Lists.<WorkerInfo>newArrayList(workerInfo));
  }

  @Test
  public void sendVertexPartition() throws IOException {
    // Data to send
    int partitionId = 13;
    Partition<IntWritable, IntWritable, IntWritable> partition =
        conf.createPartition(partitionId, null);
    for (int i = 0; i < 10; ++i) {
      Vertex vertex = conf.createVertex();
      vertex.initialize(new IntWritable(i), new IntWritable(i));
      partition.putVertex(vertex);
    }

    // Send the request
    SendVertexRequest<IntWritable, IntWritable, IntWritable> request =
      new SendVertexRequest<IntWritable, IntWritable, IntWritable>(partition);
    client.sendWritableRequest(workerInfo.getTaskId(), request);
    client.waitAllRequests();

    // Stop the service
    client.stop();
    server.stop();

    // Check the output
    PartitionStore<IntWritable, IntWritable, IntWritable> partitionStore =
        serverData.getPartitionStore();
    assertTrue(partitionStore.hasPartition(partitionId));
    int total = 0;
    Partition<IntWritable, IntWritable, IntWritable> partition2 =
        partitionStore.getOrCreatePartition(partitionId);
    for (Vertex<IntWritable, IntWritable, IntWritable> vertex : partition2) {
      total += vertex.getId().get();
    }
    partitionStore.putPartition(partition2);
    assertEquals(total, 45);
    partitionStore.shutdown();
  }

  @Test
  public void sendWorkerMessagesRequest() throws IOException {
    // Data to send
    PairList<Integer, VertexIdMessages<IntWritable,
            IntWritable>>
        dataToSend = new PairList<>();
    dataToSend.initialize();
    int partitionId = 0;
    ByteArrayVertexIdMessages<IntWritable,
            IntWritable> vertexIdMessages =
        new ByteArrayVertexIdMessages<>(
            new TestMessageValueFactory<>(IntWritable.class));
    vertexIdMessages.setConf(conf);
    vertexIdMessages.initialize();
    dataToSend.add(partitionId, vertexIdMessages);
    for (int i = 1; i < 7; ++i) {
      IntWritable vertexId = new IntWritable(i);
      for (int j = 0; j < i; ++j) {
        vertexIdMessages.add(vertexId, new IntWritable(j));
      }
    }

    // Send the request
    SendWorkerMessagesRequest<IntWritable, IntWritable> request =
      new SendWorkerMessagesRequest<>(dataToSend);
    request.setConf(conf);

    client.sendWritableRequest(workerInfo.getTaskId(), request);
    client.waitAllRequests();

    // Stop the service
    client.stop();
    server.stop();

    // Check the output
    Iterable<IntWritable> vertices =
        serverData.getIncomingMessageStore().getPartitionDestinationVertices(0);
    int keySum = 0;
    int messageSum = 0;
    for (IntWritable vertexId : vertices) {
      keySum += vertexId.get();
      Iterable<IntWritable> messages =
          serverData.<IntWritable>getIncomingMessageStore().getVertexMessages(
              vertexId);
      synchronized (messages) {
        for (IntWritable message : messages) {
          messageSum += message.get();
        }
      }
    }
    assertEquals(21, keySum);
    assertEquals(35, messageSum);
  }

  @Test
  public void sendWorkerIndividualMessagesRequest() throws IOException {
    // Data to send
    ByteArrayOneMessageToManyIds<IntWritable, IntWritable>
        dataToSend = new ByteArrayOneMessageToManyIds<>(new
        TestMessageValueFactory<>(IntWritable.class));
    dataToSend.setConf(conf);
    dataToSend.initialize();
    ExtendedDataOutput output = conf.createExtendedDataOutput();
    for (int i = 1; i <= 7; ++i) {
      IntWritable vertexId = new IntWritable(i);
      vertexId.write(output);
    }
    dataToSend.add(output.getByteArray(), output.getPos(), 7, new IntWritable(1));

    // Send the request
    SendWorkerOneMessageToManyRequest<IntWritable, IntWritable> request =
      new SendWorkerOneMessageToManyRequest<>(dataToSend, conf);
    client.sendWritableRequest(workerInfo.getTaskId(), request);
    client.waitAllRequests();

    // Stop the service
    client.stop();
    server.stop();

    // Check the output
    Iterable<IntWritable> vertices =
        serverData.getIncomingMessageStore().getPartitionDestinationVertices(0);
    int keySum = 0;
    int messageSum = 0;
    for (IntWritable vertexId : vertices) {
      keySum += vertexId.get();
      Iterable<IntWritable> messages =
          serverData.<IntWritable>getIncomingMessageStore().getVertexMessages(
              vertexId);
      synchronized (messages) {
        for (IntWritable message : messages) {
          messageSum += message.get();
        }
      }
    }
    assertEquals(28, keySum);
    assertEquals(7, messageSum);
  }

  @Test
  public void sendPartitionMutationsRequest() throws IOException {
    // Data to send
    int partitionId = 19;
    Map<IntWritable, VertexMutations<IntWritable, IntWritable,
    IntWritable>> vertexIdMutations =
        Maps.newHashMap();
    for (int i = 0; i < 11; ++i) {
      VertexMutations<IntWritable, IntWritable, IntWritable> mutations =
          new VertexMutations<IntWritable, IntWritable, IntWritable>();
      for (int j = 0; j < 3; ++j) {
        Vertex vertex = conf.createVertex();
        vertex.initialize(new IntWritable(i), new IntWritable(j));
        mutations.addVertex(vertex);
      }
      for (int j = 0; j < 2; ++j) {
        mutations.removeVertex();
      }
      for (int j = 0; j < 5; ++j) {
        Edge<IntWritable, IntWritable> edge =
            EdgeFactory.create(new IntWritable(i), new IntWritable(2 * j));
        mutations.addEdge(edge);
      }
      for (int j = 0; j < 7; ++j) {
        mutations.removeEdge(new IntWritable(j));
      }
      vertexIdMutations.put(new IntWritable(i), mutations);
    }

    // Send the request
    SendPartitionMutationsRequest<IntWritable, IntWritable, IntWritable>
        request = new SendPartitionMutationsRequest<IntWritable, IntWritable,
        IntWritable>(partitionId,
        vertexIdMutations);
    GiraphMetrics.init(conf);
    client.sendWritableRequest(workerInfo.getTaskId(), request);
    client.waitAllRequests();

    // Stop the service
    client.stop();
    server.stop();

    // Check the output
    ConcurrentMap<IntWritable,
        VertexMutations<IntWritable, IntWritable, IntWritable>>
        inVertexIdMutations =
        serverData.getPartitionMutations().get(partitionId);
    int keySum = 0;
    for (Entry<IntWritable,
        VertexMutations<IntWritable, IntWritable, IntWritable>> entry :
        inVertexIdMutations
        .entrySet()) {
      synchronized (entry.getValue()) {
        keySum += entry.getKey().get();
        int vertexValueSum = 0;
        for (Vertex<IntWritable, IntWritable, IntWritable> vertex : entry
            .getValue().getAddedVertexList()) {
          vertexValueSum += vertex.getValue().get();
        }
        assertEquals(3, vertexValueSum);
        assertEquals(2, entry.getValue().getRemovedVertexCount());
        int removeEdgeValueSum = 0;
        for (Edge<IntWritable, IntWritable> edge : entry.getValue()
            .getAddedEdgeList()) {
          removeEdgeValueSum += edge.getValue().get();
        }
        assertEquals(20, removeEdgeValueSum);
      }
    }
    assertEquals(55, keySum);
  }
}

File: giraph-core/src/test/java/org/apache/giraph/comm/messages/TestIntFloatPrimitiveMessageStores.java
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

package org.apache.giraph.comm.messages;

import java.io.IOException;
import java.util.Iterator;

import junit.framework.Assert;

import org.apache.giraph.bsp.CentralizedServiceWorker;
import org.apache.giraph.combiner.FloatSumMessageCombiner;
import org.apache.giraph.comm.messages.primitives.IntByteArrayMessageStore;
import org.apache.giraph.comm.messages.primitives.IntFloatMessageStore;
import org.apache.giraph.conf.GiraphConfiguration;
import org.apache.giraph.conf.GiraphConstants;
import org.apache.giraph.conf.ImmutableClassesGiraphConfiguration;
import org.apache.giraph.factories.TestMessageValueFactory;
import org.apache.giraph.graph.BasicComputation;
import org.apache.giraph.graph.Vertex;
import org.apache.giraph.partition.Partition;
import org.apache.giraph.partition.PartitionStore;
import org.apache.giraph.utils.ByteArrayVertexIdMessages;
import org.apache.hadoop.io.FloatWritable;
import org.apache.hadoop.io.IntWritable;
import org.apache.hadoop.io.NullWritable;
import org.apache.hadoop.io.Writable;
import org.junit.Before;
import org.junit.Test;
import org.mockito.Mockito;
import org.mockito.invocation.InvocationOnMock;
import org.mockito.stubbing.Answer;

import com.google.common.collect.Iterables;
import com.google.common.collect.Lists;

public class TestIntFloatPrimitiveMessageStores {
  private static final int NUM_PARTITIONS = 2;
  private static CentralizedServiceWorker<IntWritable, Writable, Writable>
    service;
  private static ImmutableClassesGiraphConfiguration<IntWritable, Writable,
      Writable> conf;

  @Before
  public void prepare() throws IOException {
    service = Mockito.mock(CentralizedServiceWorker.class);
    Mockito.when(
        service.getPartitionId(Mockito.any(IntWritable.class))).thenAnswer(
        new Answer<Integer>() {
          @Override
          public Integer answer(InvocationOnMock invocation) {
            IntWritable vertexId = (IntWritable) invocation.getArguments()[0];
            return vertexId.get() % NUM_PARTITIONS;
          }
        }
    );
    PartitionStore partitionStore = Mockito.mock(PartitionStore.class);
    Mockito.when(service.getPartitionStore()).thenReturn(partitionStore);
    Mockito.when(partitionStore.getPartitionIds()).thenReturn(
        Lists.newArrayList(0, 1));
    Partition partition = Mockito.mock(Partition.class);
    Mockito.when(partition.getVertexCount()).thenReturn(Long.valueOf(1));
    Mockito.when(partitionStore.getOrCreatePartition(0)).thenReturn(partition);
    Mockito.when(partitionStore.getOrCreatePartition(1)).thenReturn(partition);

    GiraphConfiguration initConf = new GiraphConfiguration();
    initConf.setComputationClass(IntFloatNoOpComputation.class);
    conf = new ImmutableClassesGiraphConfiguration(initConf);
  }

  private static class IntFloatNoOpComputation extends
      BasicComputation<IntWritable, NullWritable, NullWritable,
          FloatWritable> {
    @Override
    public void compute(Vertex<IntWritable, NullWritable, NullWritable> vertex,
        Iterable<FloatWritable> messages) throws IOException {
    }
  }

  private static ByteArrayVertexIdMessages<IntWritable, FloatWritable>
  createIntFloatMessages() {
    ByteArrayVertexIdMessages<IntWritable, FloatWritable> messages =
        new ByteArrayVertexIdMessages<IntWritable, FloatWritable>(
            new TestMessageValueFactory<FloatWritable>(FloatWritable.class));
    messages.setConf(conf);
    messages.initialize();
    return messages;
  }

  private static void insertIntFloatMessages(
      MessageStore<IntWritable, FloatWritable> messageStore) throws
      IOException {
    ByteArrayVertexIdMessages<IntWritable, FloatWritable> messages =
        createIntFloatMessages();
    messages.add(new IntWritable(0), new FloatWritable(1));
    messages.add(new IntWritable(2), new FloatWritable(3));
    messages.add(new IntWritable(0), new FloatWritable(4));
    messageStore.addPartitionMessages(0, messages);
    messages = createIntFloatMessages();
    messages.add(new IntWritable(1), new FloatWritable(1));
    messages.add(new IntWritable(1), new FloatWritable(3));
    messages.add(new IntWritable(1), new FloatWritable(4));
    messageStore.addPartitionMessages(1, messages);
    messages = createIntFloatMessages();
    messages.add(new IntWritable(0), new FloatWritable(5));
    messageStore.addPartitionMessages(0, messages);
  }

  @Test
  public void testIntFloatMessageStore() throws IOException {
    IntFloatMessageStore messageStore =
        new IntFloatMessageStore(service, new FloatSumMessageCombiner());
    insertIntFloatMessages(messageStore);

    Iterable<FloatWritable> m0 =
        messageStore.getVertexMessages(new IntWritable(0));
    Assert.assertEquals(1, Iterables.size(m0));
    Assert.assertEquals((float) 10.0, m0.iterator().next().get());
    Iterable<FloatWritable> m1 =
        messageStore.getVertexMessages(new IntWritable(1));
    Assert.assertEquals(1, Iterables.size(m1));
    Assert.assertEquals((float) 8.0, m1.iterator().next().get());
    Iterable<FloatWritable> m2 =
        messageStore.getVertexMessages(new IntWritable(2));
    Assert.assertEquals(1, Iterables.size(m2));
    Assert.assertEquals((float) 3.0, m2.iterator().next().get());
    Assert.assertTrue(
        Iterables.isEmpty(messageStore.getVertexMessages(new IntWritable(3))));
  }

  @Test
  public void testIntByteArrayMessageStore() throws IOException {
    IntByteArrayMessageStore<FloatWritable> messageStore =
        new IntByteArrayMessageStore<FloatWritable>(new
            TestMessageValueFactory<FloatWritable>(FloatWritable.class),
            service, conf);
    insertIntFloatMessages(messageStore);

    Iterable<FloatWritable> m0 =
        messageStore.getVertexMessages(new IntWritable(0));
    Assert.assertEquals(3, Iterables.size(m0));
    Iterator<FloatWritable> i0 = m0.iterator();
    Assert.assertEquals((float) 1.0, i0.next().get());
    Assert.assertEquals((float) 4.0, i0.next().get());
    Assert.assertEquals((float) 5.0, i0.next().get());
    Iterable<FloatWritable> m1 =
        messageStore.getVertexMessages(new IntWritable(1));
    Assert.assertEquals(3, Iterables.size(m1));
    Iterator<FloatWritable> i1 = m1.iterator();
    Assert.assertEquals((float) 1.0, i1.next().get());
    Assert.assertEquals((float) 3.0, i1.next().get());
    Assert.assertEquals((float) 4.0, i1.next().get());
    Iterable<FloatWritable> m2 =
        messageStore.getVertexMessages(new IntWritable(2));
    Assert.assertEquals(1, Iterables.size(m2));
    Assert.assertEquals((float) 3.0, m2.iterator().next().get());
    Assert.assertTrue(
        Iterables.isEmpty(messageStore.getVertexMessages(new IntWritable(3))));
  }

  @Test
  public void testIntByteArrayMessageStoreWithMessageEncoding() throws
      IOException {
    GiraphConstants.USE_MESSAGE_SIZE_ENCODING.set(conf, true);
    testIntByteArrayMessageStore();
    GiraphConstants.USE_MESSAGE_SIZE_ENCODING.set(conf, false);
  }
}


File: giraph-core/src/test/java/org/apache/giraph/comm/messages/TestLongDoublePrimitiveMessageStores.java
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

package org.apache.giraph.comm.messages;

import java.io.IOException;
import java.util.Iterator;

import junit.framework.Assert;

import org.apache.giraph.bsp.CentralizedServiceWorker;
import org.apache.giraph.combiner.DoubleSumMessageCombiner;
import org.apache.giraph.comm.messages.primitives.long_id.LongByteArrayMessageStore;
import org.apache.giraph.comm.messages.primitives.LongDoubleMessageStore;
import org.apache.giraph.conf.GiraphConfiguration;
import org.apache.giraph.conf.ImmutableClassesGiraphConfiguration;
import org.apache.giraph.factories.TestMessageValueFactory;
import org.apache.giraph.graph.BasicComputation;
import org.apache.giraph.graph.Vertex;
import org.apache.giraph.partition.Partition;
import org.apache.giraph.partition.PartitionStore;
import org.apache.giraph.utils.ByteArrayVertexIdMessages;
import org.apache.hadoop.io.DoubleWritable;
import org.apache.hadoop.io.LongWritable;
import org.apache.hadoop.io.NullWritable;
import org.apache.hadoop.io.Writable;
import org.junit.Before;
import org.junit.Test;
import org.mockito.Mockito;
import org.mockito.invocation.InvocationOnMock;
import org.mockito.stubbing.Answer;

import com.google.common.collect.Iterables;
import com.google.common.collect.Lists;

public class TestLongDoublePrimitiveMessageStores {
  private static final int NUM_PARTITIONS = 2;
  private static CentralizedServiceWorker<LongWritable, Writable, Writable>
    service;

  @Before
  public void prepare() throws IOException {
    service = Mockito.mock(CentralizedServiceWorker.class);
    Mockito.when(
        service.getPartitionId(Mockito.any(LongWritable.class))).thenAnswer(
        new Answer<Integer>() {
          @Override
          public Integer answer(InvocationOnMock invocation) {
            LongWritable vertexId = (LongWritable) invocation.getArguments()[0];
            return (int) (vertexId.get() % NUM_PARTITIONS);
          }
        }
    );
    PartitionStore partitionStore = Mockito.mock(PartitionStore.class);
    Mockito.when(service.getPartitionStore()).thenReturn(partitionStore);
    Mockito.when(partitionStore.getPartitionIds()).thenReturn(
        Lists.newArrayList(0, 1));
    Partition partition = Mockito.mock(Partition.class);
    Mockito.when(partition.getVertexCount()).thenReturn(Long.valueOf(1));
    Mockito.when(partitionStore.getOrCreatePartition(0)).thenReturn(partition);
    Mockito.when(partitionStore.getOrCreatePartition(1)).thenReturn(partition);
  }

  private static class LongDoubleNoOpComputation extends
      BasicComputation<LongWritable, NullWritable, NullWritable,
          DoubleWritable> {
    @Override
    public void compute(Vertex<LongWritable, NullWritable, NullWritable> vertex,
        Iterable<DoubleWritable> messages) throws IOException {
    }
  }

  private static ImmutableClassesGiraphConfiguration<LongWritable, Writable,
    Writable> createLongDoubleConf() {

    GiraphConfiguration initConf = new GiraphConfiguration();
    initConf.setComputationClass(LongDoubleNoOpComputation.class);
    return new ImmutableClassesGiraphConfiguration(initConf);
  }

  private static ByteArrayVertexIdMessages<LongWritable, DoubleWritable>
  createLongDoubleMessages() {
    ByteArrayVertexIdMessages<LongWritable, DoubleWritable> messages =
        new ByteArrayVertexIdMessages<LongWritable, DoubleWritable>(
            new TestMessageValueFactory<DoubleWritable>(DoubleWritable.class));
    messages.setConf(createLongDoubleConf());
    messages.initialize();
    return messages;
  }

  private static void insertLongDoubleMessages(
      MessageStore<LongWritable, DoubleWritable> messageStore) throws
      IOException {
    ByteArrayVertexIdMessages<LongWritable, DoubleWritable> messages =
        createLongDoubleMessages();
    messages.add(new LongWritable(0), new DoubleWritable(1));
    messages.add(new LongWritable(2), new DoubleWritable(3));
    messages.add(new LongWritable(0), new DoubleWritable(4));
    messageStore.addPartitionMessages(0, messages);
    messages = createLongDoubleMessages();
    messages.add(new LongWritable(1), new DoubleWritable(1));
    messages.add(new LongWritable(1), new DoubleWritable(3));
    messages.add(new LongWritable(1), new DoubleWritable(4));
    messageStore.addPartitionMessages(1, messages);
    messages = createLongDoubleMessages();
    messages.add(new LongWritable(0), new DoubleWritable(5));
    messageStore.addPartitionMessages(0, messages);
  }

  @Test
  public void testLongDoubleMessageStore() throws IOException {
    LongDoubleMessageStore messageStore =
        new LongDoubleMessageStore(service, new DoubleSumMessageCombiner());
    insertLongDoubleMessages(messageStore);

    Iterable<DoubleWritable> m0 =
        messageStore.getVertexMessages(new LongWritable(0));
    Assert.assertEquals(1, Iterables.size(m0));
    Assert.assertEquals(10.0, m0.iterator().next().get());
    Iterable<DoubleWritable> m1 =
        messageStore.getVertexMessages(new LongWritable(1));
    Assert.assertEquals(1, Iterables.size(m1));
    Assert.assertEquals(8.0, m1.iterator().next().get());
    Iterable<DoubleWritable> m2 =
        messageStore.getVertexMessages(new LongWritable(2));
    Assert.assertEquals(1, Iterables.size(m2));
    Assert.assertEquals(3.0, m2.iterator().next().get());
    Assert.assertTrue(
        Iterables.isEmpty(messageStore.getVertexMessages(new LongWritable(3))));
  }

  @Test
  public void testLongByteArrayMessageStore() throws IOException {
    LongByteArrayMessageStore<DoubleWritable> messageStore =
        new LongByteArrayMessageStore<DoubleWritable>(
            new TestMessageValueFactory<DoubleWritable>(DoubleWritable.class),
            service, createLongDoubleConf());
    insertLongDoubleMessages(messageStore);

    Iterable<DoubleWritable> m0 =
        messageStore.getVertexMessages(new LongWritable(0));
    Assert.assertEquals(3, Iterables.size(m0));
    Iterator<DoubleWritable> i0 = m0.iterator();
    Assert.assertEquals(1.0, i0.next().get());
    Assert.assertEquals(4.0, i0.next().get());
    Assert.assertEquals(5.0, i0.next().get());
    Iterable<DoubleWritable> m1 =
        messageStore.getVertexMessages(new LongWritable(1));
    Assert.assertEquals(3, Iterables.size(m1));
    Iterator<DoubleWritable> i1 = m1.iterator();
    Assert.assertEquals(1.0, i1.next().get());
    Assert.assertEquals(3.0, i1.next().get());
    Assert.assertEquals(4.0, i1.next().get());
    Iterable<DoubleWritable> m2 =
        messageStore.getVertexMessages(new LongWritable(2));
    Assert.assertEquals(1, Iterables.size(m2));
    Assert.assertEquals(3.0, m2.iterator().next().get());
    Assert.assertTrue(
        Iterables.isEmpty(messageStore.getVertexMessages(new LongWritable(3))));
  }
}


File: giraph-core/src/test/java/org/apache/giraph/partition/TestPartitionStores.java
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

package org.apache.giraph.partition;

import static org.apache.giraph.conf.GiraphConstants.MAX_PARTITIONS_IN_MEMORY;
import static org.apache.giraph.conf.GiraphConstants.PARTITIONS_DIRECTORY;
import static org.apache.giraph.conf.GiraphConstants.USER_PARTITION_COUNT;
import static org.apache.giraph.conf.GiraphConstants.USE_OUT_OF_CORE_GRAPH;
import static org.junit.Assert.assertEquals;
import static org.junit.Assert.assertFalse;
import static org.junit.Assert.assertTrue;

import java.io.File;
import java.io.IOException;
import java.util.Iterator;
import java.util.Random;
import java.util.concurrent.ExecutorCompletionService;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;
import java.util.concurrent.atomic.AtomicInteger;

import org.apache.commons.io.FileUtils;
import org.apache.giraph.bsp.BspService;
import org.apache.giraph.bsp.CentralizedServiceWorker;
import org.apache.giraph.conf.GiraphConfiguration;
import org.apache.giraph.conf.GiraphConstants;
import org.apache.giraph.conf.ImmutableClassesGiraphConfiguration;
import org.apache.giraph.edge.EdgeFactory;
import org.apache.giraph.graph.BasicComputation;
import org.apache.giraph.graph.Vertex;
import org.apache.giraph.io.formats.IdWithValueTextOutputFormat;
import org.apache.giraph.io.formats.JsonLongDoubleFloatDoubleVertexInputFormat;
import org.apache.giraph.utils.InternalVertexRunner;
import org.apache.giraph.utils.NoOpComputation;
import org.apache.giraph.utils.UnsafeByteArrayInputStream;
import org.apache.giraph.utils.UnsafeByteArrayOutputStream;
import org.apache.hadoop.io.DoubleWritable;
import org.apache.hadoop.io.FloatWritable;
import org.apache.hadoop.io.IntWritable;
import org.apache.hadoop.io.LongWritable;
import org.apache.hadoop.io.NullWritable;
import org.apache.hadoop.mapreduce.Mapper;
import org.junit.Before;
import org.junit.Test;
import org.mockito.Mockito;

import com.google.common.collect.Iterables;
import com.google.common.io.Files;

/**
 * Test case for partition stores.
 */
@SuppressWarnings("unchecked")
public class TestPartitionStores {
  private ImmutableClassesGiraphConfiguration<IntWritable, IntWritable,
      NullWritable> conf;
  private Mapper<?, ?, ?, ?>.Context context;

  /* these static variables are used for the multithreaded tests */
  private static final int NUM_OF_VERTEXES_PER_THREAD = 10;
  private static final int NUM_OF_EDGES_PER_VERTEX = 5;
  private static final int NUM_OF_THREADS = 10;
  private static final int NUM_OF_PARTITIONS = 3;

  public static class MyComputation extends NoOpComputation<IntWritable,
      IntWritable, NullWritable, IntWritable> { }

  private Partition<IntWritable, IntWritable, NullWritable> createPartition(
      ImmutableClassesGiraphConfiguration<IntWritable, IntWritable,
          NullWritable> conf,
      Integer id,
      Vertex<IntWritable, IntWritable, NullWritable>... vertices) {
    Partition<IntWritable, IntWritable, NullWritable> partition =
        conf.createPartition(id, context);
    for (Vertex<IntWritable, IntWritable, NullWritable> v : vertices) {
      partition.putVertex(v);
    }
    return partition;
  }

  @Before
  public void setUp() {
    GiraphConfiguration configuration = new GiraphConfiguration();
    configuration.setComputationClass(MyComputation.class);
    conf = new ImmutableClassesGiraphConfiguration<IntWritable, IntWritable,
        NullWritable>(configuration);
    context = Mockito.mock(Mapper.Context.class);
  }

  @Test
  public void testSimplePartitionStore() {
    PartitionStore<IntWritable, IntWritable, NullWritable>
        partitionStore = new SimplePartitionStore<IntWritable, IntWritable,
                NullWritable>(conf, context);
    testReadWrite(partitionStore, conf);
    partitionStore.shutdown();
  }

  @Test
  public void testUnsafePartitionSerializationClass() throws IOException {
    conf.setPartitionClass(ByteArrayPartition.class);
    Vertex<IntWritable, IntWritable, NullWritable> v1 =
        conf.createVertex();
    v1.initialize(new IntWritable(1), new IntWritable(1));
    Vertex<IntWritable, IntWritable, NullWritable> v2 = conf.createVertex();
    v2.initialize(new IntWritable(2), new IntWritable(2));
    Vertex<IntWritable, IntWritable, NullWritable> v3 = conf.createVertex();
    v3.initialize(new IntWritable(3), new IntWritable(3));
    Vertex<IntWritable, IntWritable, NullWritable> v4 = conf.createVertex();
    v4.initialize(new IntWritable(4), new IntWritable(4));
    Vertex<IntWritable, IntWritable, NullWritable> v5 = conf.createVertex();
    v5.initialize(new IntWritable(5), new IntWritable(5));
    Vertex<IntWritable, IntWritable, NullWritable> v6 = conf.createVertex();
    v6.initialize(new IntWritable(6), new IntWritable(6));
    Vertex<IntWritable, IntWritable, NullWritable> v7 = conf.createVertex();
    v7.initialize(new IntWritable(7), new IntWritable(7));

    Partition<IntWritable, IntWritable, NullWritable> partition =
        createPartition(conf, 3, v1, v2, v3, v4, v5, v6, v7);
    assertEquals(3, partition.getId());
    assertEquals(0, partition.getEdgeCount());
    assertEquals(7, partition.getVertexCount());
    UnsafeByteArrayOutputStream outputStream = new
        UnsafeByteArrayOutputStream();
    partition.write(outputStream);
    UnsafeByteArrayInputStream inputStream = new UnsafeByteArrayInputStream(
        outputStream.getByteArray(), 0, outputStream.getPos());
    Partition<IntWritable, IntWritable, NullWritable> deserializatedPartition =
        conf.createPartition(-1, context);
    deserializatedPartition.readFields(inputStream);

    assertEquals(3, deserializatedPartition.getId());
    assertEquals(0, deserializatedPartition.getEdgeCount());
    assertEquals(7, deserializatedPartition.getVertexCount());
  }
  
  @Test
  public void testDiskBackedPartitionStoreWithByteArrayPartition()
    throws IOException {

    File directory = Files.createTempDir();
    GiraphConstants.PARTITIONS_DIRECTORY.set(
        conf, new File(directory, "giraph_partitions").toString());
    GiraphConstants.USE_OUT_OF_CORE_GRAPH.set(conf, true);
    GiraphConstants.MAX_PARTITIONS_IN_MEMORY.set(conf, 1);
    conf.setPartitionClass(ByteArrayPartition.class);

    CentralizedServiceWorker<IntWritable, IntWritable, NullWritable>
      serviceWorker = Mockito.mock(CentralizedServiceWorker.class);
    Mockito.when(serviceWorker.getSuperstep()).thenReturn(
      BspService.INPUT_SUPERSTEP);

    PartitionStore<IntWritable, IntWritable, NullWritable> partitionStore =
        new DiskBackedPartitionStore<IntWritable, IntWritable, NullWritable>(
            conf, context, serviceWorker);
    testReadWrite(partitionStore, conf);
    partitionStore.shutdown();
    FileUtils.deleteDirectory(directory);
  }

  @Test
  public void testDiskBackedPartitionStore() throws IOException {
    File directory = Files.createTempDir();
    GiraphConstants.PARTITIONS_DIRECTORY.set(
        conf, new File(directory, "giraph_partitions").toString());
    GiraphConstants.USE_OUT_OF_CORE_GRAPH.set(conf, true);
    GiraphConstants.MAX_PARTITIONS_IN_MEMORY.set(conf, 1);

    CentralizedServiceWorker<IntWritable, IntWritable, NullWritable>
    serviceWorker = Mockito.mock(CentralizedServiceWorker.class);

    Mockito.when(serviceWorker.getSuperstep()).thenReturn(
      BspService.INPUT_SUPERSTEP);

    PartitionStore<IntWritable, IntWritable, NullWritable> partitionStore =
        new DiskBackedPartitionStore<IntWritable, IntWritable, NullWritable>(
            conf, context, serviceWorker);
    testReadWrite(partitionStore, conf);
    partitionStore.shutdown();

    GiraphConstants.MAX_PARTITIONS_IN_MEMORY.set(conf, 2);
    partitionStore = new DiskBackedPartitionStore<IntWritable,
            IntWritable, NullWritable>(conf, context, serviceWorker);
    testReadWrite(partitionStore, conf);
    partitionStore.shutdown();
    FileUtils.deleteDirectory(directory);
  }

  @Test
  public void testDiskBackedPartitionStoreWithByteArrayComputation()
    throws Exception {

    Iterable<String> results;
    String[] graph =
    {
      "[1,0,[]]", "[2,0,[]]", "[3,0,[]]", "[4,0,[]]", "[5,0,[]]",
      "[6,0,[]]", "[7,0,[]]", "[8,0,[]]", "[9,0,[]]", "[10,0,[]]"
    };
    String[] expected =
    {
      "1\t0", "2\t0", "3\t0", "4\t0", "5\t0",
      "6\t0", "7\t0", "8\t0", "9\t0", "10\t0"
    };

    USE_OUT_OF_CORE_GRAPH.set(conf, true);
    MAX_PARTITIONS_IN_MEMORY.set(conf, 1);
    USER_PARTITION_COUNT.set(conf, 10);

    File directory = Files.createTempDir();
    PARTITIONS_DIRECTORY.set(conf,
      new File(directory, "giraph_partitions").toString());

    conf.setPartitionClass(ByteArrayPartition.class);
    conf.setComputationClass(EmptyComputation.class);
    conf.setVertexInputFormatClass(JsonLongDoubleFloatDoubleVertexInputFormat.class);
    conf.setVertexOutputFormatClass(IdWithValueTextOutputFormat.class);

    results = InternalVertexRunner.run(conf, graph);
    checkResults(results, expected);
    FileUtils.deleteDirectory(directory);
  }

  @Test
  public void testDiskBackedPartitionStoreMT() throws Exception {
    GiraphConstants.STATIC_GRAPH.set(conf, false);
    testMultiThreaded();
  }

  /*
  @Test
  public void testDiskBackedPartitionStoreMTStatic() throws Exception {
    GiraphConstants.STATIC_GRAPH.set(conf, true);
    testMultiThreaded();
  }
  */

  private void testMultiThreaded() throws Exception {
    final AtomicInteger vertexCounter = new AtomicInteger(0);
    ExecutorService pool = Executors.newFixedThreadPool(NUM_OF_THREADS);
    ExecutorCompletionService<Boolean> executor =
      new ExecutorCompletionService<Boolean>(pool);

    File directory = Files.createTempDir();
    GiraphConstants.PARTITIONS_DIRECTORY.set(
        conf, new File(directory, "giraph_partitions").toString());
    GiraphConstants.USE_OUT_OF_CORE_GRAPH.set(conf, true);
    GiraphConstants.MAX_PARTITIONS_IN_MEMORY.set(conf, 1);

    CentralizedServiceWorker<IntWritable, IntWritable, NullWritable>
    serviceWorker = Mockito.mock(CentralizedServiceWorker.class);

    Mockito.when(serviceWorker.getSuperstep()).thenReturn(
      BspService.INPUT_SUPERSTEP);

    PartitionStore<IntWritable, IntWritable, NullWritable> store =
        new DiskBackedPartitionStore<IntWritable, IntWritable, NullWritable>(
            conf, context, serviceWorker);

    // Create a new Graph in memory using multiple threads
    for (int i = 0; i < NUM_OF_THREADS; ++i) {
      int partitionId = i % NUM_OF_PARTITIONS;
      Worker worker =
        new Worker(vertexCounter, store, partitionId, conf);
      executor.submit(worker, new Boolean(true));
    }
    for (int i = 0; i < NUM_OF_THREADS; ++i)
      executor.take();
    pool.shutdownNow();

    // Check the number of vertices
    int totalVertexes = 0;
    int totalEdges = 0;
    Partition<IntWritable, IntWritable, NullWritable> partition;
    for (int i = 0; i < NUM_OF_PARTITIONS; ++i) {
      totalVertexes += store.getPartitionVertexCount(i);
      totalEdges += store.getPartitionEdgeCount(i);
    }
    assert vertexCounter.get() == NUM_OF_THREADS * NUM_OF_VERTEXES_PER_THREAD;
    assert totalVertexes == NUM_OF_THREADS * NUM_OF_VERTEXES_PER_THREAD;
    assert totalEdges == totalVertexes * NUM_OF_EDGES_PER_VERTEX;

    // Check the content of the vertices
    int expected = 0;
    for (int i = 0; i < NUM_OF_VERTEXES_PER_THREAD * NUM_OF_VERTEXES_PER_THREAD; ++i) {
      expected += i;
    }
    int totalValues = 0;
    for (int i = 0; i < NUM_OF_PARTITIONS; ++i) {
      partition = store.getOrCreatePartition(i);
      Iterator<Vertex<IntWritable, IntWritable, NullWritable>> vertexes = 
        partition.iterator();

      while (vertexes.hasNext()) {
        Vertex<IntWritable, IntWritable, NullWritable> v = vertexes.next();
        totalValues += v.getId().get();
      }
      store.putPartition(partition);
    }
    assert totalValues == expected;
    
    store.shutdown();
  }

  @Test
  public void testDiskBackedPartitionStoreComputation() throws Exception {
    Iterable<String> results;
    String[] graph =
    {
      "[1,0,[]]", "[2,0,[]]", "[3,0,[]]", "[4,0,[]]", "[5,0,[]]",
      "[6,0,[]]", "[7,0,[]]", "[8,0,[]]", "[9,0,[]]", "[10,0,[]]"
    };
    String[] expected =
    {
      "1\t0", "2\t0", "3\t0", "4\t0", "5\t0",
      "6\t0", "7\t0", "8\t0", "9\t0", "10\t0"
    };

    USE_OUT_OF_CORE_GRAPH.set(conf, true);
    MAX_PARTITIONS_IN_MEMORY.set(conf, 1);
    USER_PARTITION_COUNT.set(conf, 10);

    File directory = Files.createTempDir();
    PARTITIONS_DIRECTORY.set(conf,
      new File(directory, "giraph_partitions").toString());

    conf.setComputationClass(EmptyComputation.class);
    conf.setVertexInputFormatClass(JsonLongDoubleFloatDoubleVertexInputFormat.class);
    conf.setVertexOutputFormatClass(IdWithValueTextOutputFormat.class);

    results = InternalVertexRunner.run(conf, graph);
    checkResults(results, expected);
    FileUtils.deleteDirectory(directory);
  }

  /**
   * Test reading/writing to/from a partition store
   *
   * @param partitionStore Partition store to test
   * @param conf Configuration to use
   */
  public void testReadWrite(
      PartitionStore<IntWritable, IntWritable,
          NullWritable> partitionStore,
      ImmutableClassesGiraphConfiguration<IntWritable, IntWritable,
          NullWritable> conf) {
    Vertex<IntWritable, IntWritable, NullWritable> v1 = conf.createVertex();
    v1.initialize(new IntWritable(1), new IntWritable(1));
    Vertex<IntWritable, IntWritable, NullWritable> v2 = conf.createVertex();
    v2.initialize(new IntWritable(2), new IntWritable(2));
    Vertex<IntWritable, IntWritable, NullWritable> v3 = conf.createVertex();
    v3.initialize(new IntWritable(3), new IntWritable(3));
    Vertex<IntWritable, IntWritable, NullWritable> v4 = conf.createVertex();
    v4.initialize(new IntWritable(4), new IntWritable(4));
    Vertex<IntWritable, IntWritable, NullWritable> v5 = conf.createVertex();
    v5.initialize(new IntWritable(5), new IntWritable(5));
    Vertex<IntWritable, IntWritable, NullWritable> v6 = conf.createVertex();
    v6.initialize(new IntWritable(7), new IntWritable(7));
    Vertex<IntWritable, IntWritable, NullWritable> v7 = conf.createVertex();
    v7.initialize(new IntWritable(7), new IntWritable(7));
    v7.addEdge(EdgeFactory.create(new IntWritable(1)));
    v7.addEdge(EdgeFactory.create(new IntWritable(2)));

    partitionStore.addPartition(createPartition(conf, 1, v1, v2));
    partitionStore.addPartition(createPartition(conf, 2, v3));
    partitionStore.addPartition(createPartition(conf, 2, v4));
    partitionStore.addPartition(createPartition(conf, 3, v5));
    partitionStore.addPartition(createPartition(conf, 1, v6));
    partitionStore.addPartition(createPartition(conf, 4, v7));

    Partition<IntWritable, IntWritable, NullWritable> partition1 =
        partitionStore.getOrCreatePartition(1);
    partitionStore.putPartition(partition1);
    Partition<IntWritable, IntWritable, NullWritable> partition2 =
        partitionStore.getOrCreatePartition(2);
    partitionStore.putPartition(partition2);
    Partition<IntWritable, IntWritable, NullWritable> partition3 =
        partitionStore.removePartition(3);
    Partition<IntWritable, IntWritable, NullWritable> partition4 =
        partitionStore.getOrCreatePartition(4);
    partitionStore.putPartition(partition4);

    assertEquals(3, partitionStore.getNumPartitions());
    assertEquals(3, Iterables.size(partitionStore.getPartitionIds()));
    int partitionsNumber = 0;
    for (Integer partitionId : partitionStore.getPartitionIds()) {
      Partition<IntWritable, IntWritable, NullWritable> p =
          partitionStore.getOrCreatePartition(partitionId);
      partitionStore.putPartition(p);
      partitionsNumber++;
    }
    Partition<IntWritable, IntWritable, NullWritable> partition;
    assertEquals(3, partitionsNumber);
    assertTrue(partitionStore.hasPartition(1));
    assertTrue(partitionStore.hasPartition(2));
    assertFalse(partitionStore.hasPartition(3));
    assertTrue(partitionStore.hasPartition(4));
    assertEquals(3, partitionStore.getPartitionVertexCount(1));
    assertEquals(2, partitionStore.getPartitionVertexCount(2));
    assertEquals(1, partitionStore.getPartitionVertexCount(4));
    assertEquals(2, partitionStore.getPartitionEdgeCount(4));
    partitionStore.deletePartition(2);
    assertEquals(2, partitionStore.getNumPartitions());
  }

  /**
   * Internal checker to verify the correctness of the tests.
   * @param results   the actual results obtaind
   * @param expected  expected results
   */
  private void checkResults(Iterable<String> results, String[] expected) {
    Iterator<String> result = results.iterator();

    assert results != null;

    while(result.hasNext()) {
      String  resultStr = result.next();
      boolean found = false;

      for (int j = 0; j < expected.length; ++j) {
        if (expected[j].equals(resultStr)) {
          found = true;
        }
      }

      assert found;
    }
  }

  /**
   * Test compute method that sends each edge a notification of its parents.
   * The test set only has a 1-1 parent-to-child ratio for this unit test.
   */
  public static class EmptyComputation
    extends BasicComputation<LongWritable, DoubleWritable, FloatWritable,
      LongWritable> {

    @Override
    public void compute(
      Vertex<LongWritable, DoubleWritable,FloatWritable> vertex,
      Iterable<LongWritable> messages) throws IOException {

      vertex.voteToHalt();
    }
  }

  @Test
  public void testEdgeCombineWithSimplePartition() throws IOException {
    testEdgeCombine(SimplePartition.class);
  }
 
  @Test
  public void testEdgeCombineWithByteArrayPartition() throws IOException {
    testEdgeCombine(ByteArrayPartition.class);
  }
 
  private void testEdgeCombine(Class<? extends Partition> partitionClass)
      throws IOException {
    Vertex<IntWritable, IntWritable, NullWritable> v1 = conf.createVertex();
    v1.initialize(new IntWritable(1), new IntWritable(1));
    Vertex<IntWritable, IntWritable, NullWritable> v2 = conf.createVertex();
    v2.initialize(new IntWritable(2), new IntWritable(2));
    Vertex<IntWritable, IntWritable, NullWritable> v3 = conf.createVertex();
    v3.initialize(new IntWritable(3), new IntWritable(3));
    Vertex<IntWritable, IntWritable, NullWritable> v1e2 = conf.createVertex();
    v1e2.initialize(new IntWritable(1), new IntWritable(1));
    v1e2.addEdge(EdgeFactory.create(new IntWritable(2)));
    Vertex<IntWritable, IntWritable, NullWritable> v1e3 = conf.createVertex();
    v1e3.initialize(new IntWritable(1), new IntWritable(1));
    v1e3.addEdge(EdgeFactory.create(new IntWritable(3)));

    GiraphConfiguration newconf = new GiraphConfiguration(conf);
    newconf.setPartitionClass(partitionClass);
    Partition<IntWritable, IntWritable, NullWritable> partition =
        (new ImmutableClassesGiraphConfiguration<IntWritable, IntWritable,
            NullWritable>(newconf)).createPartition(1, context);
    assertEquals(partitionClass, partition.getClass());
    partition.putVertex(v1);
    partition.putVertex(v2);
    partition.putVertex(v3);
    assertEquals(3, partition.getVertexCount());
    assertEquals(0, partition.getEdgeCount());
    partition.putOrCombine(v1e2);
    assertEquals(3, partition.getVertexCount());
    assertEquals(1, partition.getEdgeCount());
    partition.putOrCombine(v1e3);
    assertEquals(3, partition.getVertexCount());
    assertEquals(2, partition.getEdgeCount());
    v1 = partition.getVertex(new IntWritable(1));
    assertEquals(new IntWritable(1), v1.getId());
    assertEquals(new IntWritable(1), v1.getValue());
    assertEquals(2, v1.getNumEdges());
  }

  private class Worker implements Runnable {

    private final AtomicInteger vertexCounter;
    private final PartitionStore<IntWritable, IntWritable, NullWritable>
      partitionStore;
    private final int partitionId;
    private final ImmutableClassesGiraphConfiguration<IntWritable, IntWritable,
            NullWritable> conf;

    public Worker(AtomicInteger vertexCounter,
        PartitionStore<IntWritable, IntWritable, NullWritable> partitionStore,
        int partitionId,
        ImmutableClassesGiraphConfiguration<IntWritable, IntWritable,
          NullWritable> conf) {

      this.vertexCounter = vertexCounter;
      this.partitionStore = partitionStore;
      this.partitionId = partitionId;
      this.conf = conf;
    }

    public void run() {
      for (int i = 0; i < NUM_OF_VERTEXES_PER_THREAD; ++i) {
        int id = vertexCounter.getAndIncrement();
        Vertex<IntWritable, IntWritable, NullWritable> v = conf.createVertex();
        v.initialize(new IntWritable(id), new IntWritable(id));

        Partition<IntWritable, IntWritable, NullWritable> partition =
          partitionStore.getOrCreatePartition(partitionId);

        Random rand = new Random(id);
        for (int j = 0; j < NUM_OF_EDGES_PER_VERTEX; ++j) {
          int dest = rand.nextInt(id + 1);
          v.addEdge(EdgeFactory.create(new IntWritable(dest)));
        }

        partition.putVertex(v);
        partitionStore.putPartition(partition);
      }
    }
  }
}
