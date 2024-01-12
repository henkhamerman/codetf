Refactoring Types: ['Move Class']
tional/com/mongodb/async/client/CrudTest.java
/*
 * Copyright 2015 MongoDB, Inc.
 *
 * Licensed under the Apache License, Version 2.0 (the "License");
 * you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at
 *
 *  http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 */

package com.mongodb.async.client;

import com.mongodb.JsonPoweredTestHelper;
import com.mongodb.MongoNamespace;
import com.mongodb.async.FutureResultCallback;
import com.mongodb.client.model.CountOptions;
import com.mongodb.client.model.FindOneAndDeleteOptions;
import com.mongodb.client.model.FindOneAndReplaceOptions;
import com.mongodb.client.model.FindOneAndUpdateOptions;
import com.mongodb.client.model.ReturnDocument;
import com.mongodb.client.model.UpdateOptions;
import com.mongodb.client.result.DeleteResult;
import com.mongodb.client.result.UpdateResult;
import org.bson.BsonArray;
import org.bson.BsonDocument;
import org.bson.BsonInt32;
import org.bson.BsonNull;
import org.bson.BsonValue;
import org.junit.AssumptionViolatedException;
import org.junit.Before;
import org.junit.Test;
import org.junit.runner.RunWith;
import org.junit.runners.Parameterized;

import java.io.File;
import java.io.IOException;
import java.lang.reflect.InvocationTargetException;
import java.lang.reflect.Method;
import java.net.URISyntaxException;
import java.util.ArrayList;
import java.util.Collection;
import java.util.List;
import java.util.concurrent.ExecutionException;
import java.util.concurrent.TimeUnit;
import java.util.concurrent.TimeoutException;

import static com.mongodb.ClusterFixture.getDefaultDatabaseName;
import static com.mongodb.ClusterFixture.serverVersionAtLeast;
import static com.mongodb.async.client.Fixture.getDefaultDatabase;
import static java.util.Arrays.asList;
import static org.junit.Assert.assertEquals;
import static org.junit.Assume.assumeFalse;
import static org.junit.Assume.assumeTrue;

// See https://github.com/mongodb/specifications/tree/master/source/crud/tests
@RunWith(Parameterized.class)
public class CrudTest {
    private final String filename;
    private final String description;
    private final BsonArray data;
    private final BsonDocument definition;
    private MongoCollection<BsonDocument> collection;

    public CrudTest(final String filename, final String description, final BsonArray data, final BsonDocument definition) {
        this.filename = filename;
        this.description = description;
        this.data = data;
        this.definition = definition;
    }

    @Before
    public void setUp() throws InterruptedException, ExecutionException, TimeoutException {
        collection = Fixture.initializeCollection(new MongoNamespace(getDefaultDatabaseName(), getClass().getName()))
                .withDocumentClass(BsonDocument.class);
        new MongoOperation<Void>() {
            @Override
            void execute() {
                List<BsonDocument> documents = new ArrayList<BsonDocument>();
                for (BsonValue document : data) {
                    documents.add(document.asDocument());
                }
                collection.insertMany(documents, getCallback());
            }
        }.get();
    }

    @Test
    public void shouldPassAllOutcomes() {
        BsonDocument outcome = getOperationMongoOperations(definition.getDocument("operation"));
        BsonDocument expectedOutcome = definition.getDocument("outcome");

        if (checkResult()) {
            assertEquals(description, expectedOutcome.get("result"), outcome.get("result"));
        }
        if (expectedOutcome.containsKey("collection")) {
            assertCollectionEquals(expectedOutcome.getDocument("collection"));
        }
    }

    @Parameterized.Parameters(name = "{1}")
    public static Collection<Object[]> data() throws URISyntaxException, IOException {
        List<Object[]> data = new ArrayList<Object[]>();
        for (File file : JsonPoweredTestHelper.getTestFiles("/crud")) {
            BsonDocument testDocument = JsonPoweredTestHelper.getTestDocument(file);
            for (BsonValue test : testDocument.getArray("tests")) {
                data.add(new Object[]{file.getName(), test.asDocument().getString("description").getValue(),
                        testDocument.getArray("data"), test.asDocument()});
            }
        }
        return data;
    }

    private boolean checkResult() {
        if (filename.contains("insert")) {
            // We don't return any id's for insert commands
            return false;
        } else if (!serverVersionAtLeast(asList(3, 0, 0))
                && description.contains("when no documents match with upsert returning the document before modification")) {
            // Pre 3.0 versions of MongoDB return an empty document rather than a null
            return false;
        }
        return true;
    }

    private void assertCollectionEquals(final BsonDocument expectedCollection) {
        BsonArray actual = new MongoOperation<BsonArray>() {
            @Override
            void execute() {
                MongoCollection<BsonDocument> collectionToCompare = collection;
                if (expectedCollection.containsKey("name")) {
                    collectionToCompare = getDefaultDatabase().getCollection(expectedCollection.getString("name").getValue(),
                            BsonDocument.class);
                }
                collectionToCompare.find().into(new BsonArray(), getCallback());
            }
        }.get();
        assertEquals(description, expectedCollection.getArray("data"), actual);
    }

    private BsonDocument getOperationMongoOperations(final BsonDocument operation) {
        String name = operation.getString("name").getValue();
        BsonDocument arguments = operation.getDocument("arguments");

        String methodName = "get" + name.substring(0, 1).toUpperCase() + name.substring(1) + "MongoOperation";
        try {
            Method method = getClass().getDeclaredMethod(methodName, BsonDocument.class);
            return convertMongoOperationToResult(method.invoke(this, arguments));
        } catch (NoSuchMethodException e) {
            throw new UnsupportedOperationException("No handler for operation " + methodName);
        } catch (InvocationTargetException e) {
            if (e.getTargetException() instanceof AssumptionViolatedException) {
                throw (AssumptionViolatedException) e.getTargetException();
            }
            throw new UnsupportedOperationException("Invalid handler for operation " + methodName);
        } catch (IllegalAccessException e) {
            throw new UnsupportedOperationException("Invalid handler access for operation " + methodName);
        }
    }

    @SuppressWarnings({"unchecked", "rawtypes"})
    private BsonDocument convertMongoOperationToResult(final Object result) {
        if (result instanceof MongoOperationLong) {
            return toResult(new BsonInt32(((MongoOperationLong) result).get().intValue()));
        } else if (result instanceof MongoOperationVoid) {
            ((MongoOperationVoid) result).get();
            return toResult(BsonNull.VALUE);
        } else if (result instanceof MongoOperationBsonDocument) {
            return toResult((MongoOperationBsonDocument) result);
        } else if (result instanceof MongoOperationUpdateResult) {
            return toResult((MongoOperationUpdateResult) result);
        } else if (result instanceof MongoOperationDeleteResult) {
            return toResult((MongoOperationDeleteResult) result);
        } else if (result instanceof DistinctIterable<?>) {
            return toResult((DistinctIterable<BsonInt32>) result);
        } else if (result instanceof MongoIterable<?>) {
            return toResult((MongoIterable) result);
        } else if (result instanceof BsonValue) {
            return toResult((BsonValue) result);
        }
        throw new UnsupportedOperationException("Unknown object type cannot convert: " + result);
    }

    private BsonDocument toResult(final MongoOperationBsonDocument results) {
        return toResult(results.get());
    }

    private BsonDocument toResult(final DistinctIterable<BsonInt32> results) {
        return toResult(new MongoOperation<BsonArray>() {
            @Override
            void execute() {
                results.into(new BsonArray(), getCallback());
            }
        }.get());
    }

    private BsonDocument toResult(final MongoIterable<BsonDocument> results) {
        return toResult(new MongoOperation<BsonArray>() {
            @Override
            void execute() {
                results.into(new BsonArray(), getCallback());
            }
        }.get());
    }

    private BsonDocument toResult(final MongoOperationUpdateResult operation) {
        assumeTrue(serverVersionAtLeast(asList(2, 6, 0))); // ModifiedCount is not accessible pre 2.6

        UpdateResult updateResult = operation.get();
        BsonDocument resultDoc = new BsonDocument("matchedCount", new BsonInt32((int) updateResult.getMatchedCount()))
                .append("modifiedCount", new BsonInt32((int) updateResult.getModifiedCount()));
        if (updateResult.getUpsertedId() != null) {
            resultDoc.append("upsertedId", updateResult.getUpsertedId());
        }
        return toResult(resultDoc);
    }

    private BsonDocument toResult(final MongoOperationDeleteResult operation) {
        DeleteResult deleteResult = operation.get();
        return toResult(new BsonDocument("deletedCount", new BsonInt32((int) deleteResult.getDeletedCount())));
    }

    private BsonDocument toResult(final BsonValue results) {
        return new BsonDocument("result", results != null ? results : BsonNull.VALUE);
    }

    private AggregateIterable<BsonDocument> getAggregateMongoOperation(final BsonDocument arguments) {
        if (!serverVersionAtLeast(asList(2, 6, 0))) {
            assumeFalse(description.contains("$out"));
        }

        List<BsonDocument> pipeline = new ArrayList<BsonDocument>();
        for (BsonValue stage : arguments.getArray("pipeline")) {
            pipeline.add(stage.asDocument());
        }
        return collection.aggregate(pipeline).batchSize(arguments.getNumber("batchSize").intValue());
    }

    private MongoOperationLong getCountMongoOperation(final BsonDocument arguments) {
        return new MongoOperationLong() {
            @Override
            void execute() {
                CountOptions options = new CountOptions();
                if (arguments.containsKey("skip")) {
                    options.skip(arguments.getNumber("skip").intValue());
                }
                if (arguments.containsKey("limit")) {
                    options.limit(arguments.getNumber("limit").intValue());
                }
                collection.count(arguments.getDocument("filter"), options, getCallback());
            }
        };
    }

    private DistinctIterable<BsonInt32> getDistinctMongoOperation(final BsonDocument arguments) {
        return collection.distinct(arguments.getString("fieldName").getValue(), arguments.getDocument("filter"), BsonInt32.class);
    }

    private FindIterable<BsonDocument> getFindMongoOperation(final BsonDocument arguments) {
        FindIterable<BsonDocument> findIterable = collection.find(arguments.getDocument("filter"));
        if (arguments.containsKey("skip")) {
            findIterable.skip(arguments.getNumber("skip").intValue());
        }
        if (arguments.containsKey("limit")) {
            findIterable.limit(arguments.getNumber("limit").intValue());
        }
        if (arguments.containsKey("batchSize")) {
            findIterable.batchSize(arguments.getNumber("batchSize").intValue());
        }
        return findIterable;
    }

    private MongoOperationDeleteResult getDeleteManyMongoOperation(final BsonDocument arguments) {
        return new MongoOperationDeleteResult() {
            @Override
            void execute() {
                collection.deleteMany(arguments.getDocument("filter"), getCallback());
            }
        };
    }

    private MongoOperationDeleteResult getDeleteOneMongoOperation(final BsonDocument arguments) {
        return new MongoOperationDeleteResult() {
            @Override
            void execute() {
                collection.deleteOne(arguments.getDocument("filter"), getCallback());
            }
        };
    }

    private MongoOperationBsonDocument getFindOneAndDeleteMongoOperation(final BsonDocument arguments) {
        return new MongoOperationBsonDocument() {
            @Override
            void execute() {
                FindOneAndDeleteOptions options = new FindOneAndDeleteOptions();
                if (arguments.containsKey("projection")) {
                    options.projection(arguments.getDocument("projection"));
                }
                if (arguments.containsKey("sort")) {
                    options.sort(arguments.getDocument("sort"));
                }
                collection.findOneAndDelete(arguments.getDocument("filter"), options, getCallback());
            }
        };
    }

    private MongoOperationBsonDocument getFindOneAndReplaceMongoOperation(final BsonDocument arguments) {
        assumeTrue(serverVersionAtLeast(asList(2, 6, 0))); // in 2.4 the server can ignore the supplied _id and creates an ObjectID

        return new MongoOperationBsonDocument() {
            @Override
            void execute() {
                FindOneAndReplaceOptions options = new FindOneAndReplaceOptions();
                if (arguments.containsKey("projection")) {
                    options.projection(arguments.getDocument("projection"));
                }
                if (arguments.containsKey("sort")) {
                    options.sort(arguments.getDocument("sort"));
                }
                if (arguments.containsKey("upsert")) {
                    options.upsert(arguments.getBoolean("upsert").getValue());
                }
                if (arguments.containsKey("returnDocument")) {
                    options.returnDocument(arguments.getString("returnDocument").getValue().equals("After") ? ReturnDocument.AFTER
                            : ReturnDocument.BEFORE);
                }
                collection.findOneAndReplace(arguments.getDocument("filter"), arguments.getDocument("replacement"), options, getCallback());
            }
        };
    }

    private MongoOperationBsonDocument getFindOneAndUpdateMongoOperation(final BsonDocument arguments) {
        return new MongoOperationBsonDocument() {
            @Override
            void execute() {

                FindOneAndUpdateOptions options = new FindOneAndUpdateOptions();
                if (arguments.containsKey("projection")) {
                    options.projection(arguments.getDocument("projection"));
                }
                if (arguments.containsKey("sort")) {
                    options.sort(arguments.getDocument("sort"));
                }
                if (arguments.containsKey("upsert")) {
                    options.upsert(arguments.getBoolean("upsert").getValue());
                }
                if (arguments.containsKey("returnDocument")) {
                    options.returnDocument(arguments.getString("returnDocument").getValue().equals("After") ? ReturnDocument.AFTER
                            : ReturnDocument.BEFORE);
                }
                collection.findOneAndUpdate(arguments.getDocument("filter"), arguments.getDocument("update"), options, getCallback());
            }
        };
    }

    private MongoOperationVoid getInsertOneMongoOperation(final BsonDocument arguments) {
        return new MongoOperationVoid() {
            @Override
            void execute() {
                collection.insertOne(arguments.getDocument("document"), getCallback());
            }
        };
    }

    private MongoOperationVoid getInsertManyMongoOperation(final BsonDocument arguments) {
        return new MongoOperationVoid() {
            @Override
            void execute() {
                List<BsonDocument> documents = new ArrayList<BsonDocument>();
                for (BsonValue document : arguments.getArray("documents")) {
                    documents.add(document.asDocument());
                }
                collection.insertMany(documents, getCallback());
            }
        };
    }

    private MongoOperationUpdateResult getReplaceOneMongoOperation(final BsonDocument arguments) {
        return new MongoOperationUpdateResult() {
            @Override
            void execute() {
                UpdateOptions options = new UpdateOptions();
                if (arguments.containsKey("upsert")) {
                    options.upsert(arguments.getBoolean("upsert").getValue());
                }
                collection.replaceOne(arguments.getDocument("filter"), arguments.getDocument("replacement"), options, getCallback());
            }
        };
    }

    private MongoOperationUpdateResult getUpdateManyMongoOperation(final BsonDocument arguments) {
        return new MongoOperationUpdateResult() {
            @Override
            void execute() {
                UpdateOptions options = new UpdateOptions();
                if (arguments.containsKey("upsert")) {
                    options.upsert(arguments.getBoolean("upsert").getValue());
                }
                collection.updateMany(arguments.getDocument("filter"), arguments.getDocument("update"), options, getCallback());
            }
        };
    }

    private MongoOperationUpdateResult getUpdateOneMongoOperation(final BsonDocument arguments) {
        return new MongoOperationUpdateResult() {
            @Override
            void execute() {
                UpdateOptions options = new UpdateOptions();
                if (arguments.containsKey("upsert")) {
                    options.upsert(arguments.getBoolean("upsert").getValue());
                }
                collection.updateOne(arguments.getDocument("filter"), arguments.getDocument("update"), options, getCallback());
            }
        };
    }

    abstract class MongoOperationLong extends MongoOperation<Long> {
    }

    abstract class MongoOperationBsonDocument extends MongoOperation<BsonDocument> {
    }


    abstract class MongoOperationUpdateResult extends MongoOperation<UpdateResult> {
    }

    abstract class MongoOperationDeleteResult extends MongoOperation<DeleteResult> {
    }

    abstract class MongoOperationVoid extends MongoOperation<Void> {
    }

    private abstract class MongoOperation<TResult> {
        private FutureResultCallback<TResult> callback = new FutureResultCallback<TResult>();

        public FutureResultCallback<TResult> getCallback() {
            return callback;
        }

        public TResult get() {
            execute();
            try {
                return callback.get(60, TimeUnit.SECONDS);
            } catch (Throwable t) {
                throw new RuntimeException(t);
            }
        }

        abstract void execute();
    }

}


File: driver-core/src/test/unit/com/mongodb/connection/ServerDiscoveryAndMonitoringTest.java
/*
 * Copyright 2014-2015 MongoDB, Inc.
 *
 * Licensed under the Apache License, Version 2.0 (the "License");
 * you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at
 *
 *   http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 */

package com.mongodb.connection;

import com.mongodb.ConnectionString;
import com.mongodb.JsonPoweredTestHelper;
import com.mongodb.ServerAddress;
import org.bson.BsonArray;
import org.bson.BsonDocument;
import org.bson.BsonInt32;
import org.bson.BsonValue;
import org.junit.Test;
import org.junit.runner.RunWith;
import org.junit.runners.Parameterized;

import java.io.File;
import java.io.IOException;
import java.net.URISyntaxException;
import java.util.ArrayList;
import java.util.Collection;
import java.util.List;
import java.util.concurrent.TimeUnit;

import static com.mongodb.connection.ClusterType.REPLICA_SET;
import static com.mongodb.connection.ClusterType.SHARDED;
import static com.mongodb.connection.ClusterType.UNKNOWN;
import static com.mongodb.connection.DescriptionHelper.createServerDescription;
import static com.mongodb.connection.DescriptionHelper.getVersion;
import static com.mongodb.connection.ServerConnectionState.CONNECTING;
import static java.util.Arrays.asList;
import static org.junit.Assert.assertEquals;
import static org.junit.Assert.assertNotNull;
import static org.junit.Assert.fail;

// See https://github.com/mongodb/specifications/tree/master/source/server-discovery-and-monitoring/tests
@RunWith(Parameterized.class)
public class ServerDiscoveryAndMonitoringTest {
    private final TestClusterableServerFactory factory = new TestClusterableServerFactory();
    private final BsonDocument definition;
    private final BaseCluster cluster;

    public ServerDiscoveryAndMonitoringTest(final String description, final BsonDocument definition) {
        this.definition = definition;
        cluster = getCluster(definition.getString("uri").getValue());
    }

    @Test
    public void shouldPassAllOutcomes() {
        for (BsonValue phase : definition.getArray("phases")) {
            for (BsonValue response : phase.asDocument().getArray("responses")) {
                applyResponse(response.asArray());
            }
            BsonDocument outcome = phase.asDocument().getDocument("outcome");
            assertTopologyType(outcome.getString("topologyType").getValue());
            assertServers(outcome.getDocument("servers"));
        }
    }

    @Parameterized.Parameters(name = "{0}")
    public static Collection<Object[]> data() throws URISyntaxException, IOException {
        List<Object[]> data = new ArrayList<Object[]>();
        for (File file : JsonPoweredTestHelper.getTestFiles("/server-discovery-and-monitoring")) {
            BsonDocument testDocument = JsonPoweredTestHelper.getTestDocument(file);
            data.add(new Object[]{testDocument.getString("description").getValue(), testDocument});
        }
        return data;
    }

    private void assertServers(final BsonDocument servers) {
        if (servers.size() != cluster.getCurrentDescription().getAll().size()) {
            fail("Cluster description contains servers that are not part of the expected outcome");
        }

        for (String serverName : servers.keySet()) {
            assertServer(serverName, servers.getDocument(serverName));
        }
    }

    private void assertServer(final String serverName, final BsonDocument expectedServerDescriptionDocument) {
        ServerDescription serverDescription = getServerDescription(serverName);

        assertNotNull(serverDescription);
        assertEquals(getServerType(expectedServerDescriptionDocument.getString("type").getValue()), serverDescription.getType());

        if (expectedServerDescriptionDocument.isString("setName")) {
            assertNotNull(serverDescription.getSetName());
            assertEquals(serverDescription.getSetName(), expectedServerDescriptionDocument.getString("setName").getValue());
        }
    }

    private ServerDescription getServerDescription(final String serverName) {
        ServerDescription serverDescription  = null;
        for (ServerDescription cur: cluster.getCurrentDescription().getAll()) {
            if (cur.getAddress().equals(new ServerAddress(serverName))) {
                serverDescription = cur;
                break;
            }
        }
        return serverDescription;
    }

    private ServerType getServerType(final String serverTypeString) {
        ServerType serverType;
        if (serverTypeString.equals("RSPrimary")) {
            serverType = ServerType.REPLICA_SET_PRIMARY;
        } else if (serverTypeString.equals("RSSecondary")) {
            serverType = ServerType.REPLICA_SET_SECONDARY;
        } else if (serverTypeString.equals("RSArbiter")) {
            serverType = ServerType.REPLICA_SET_ARBITER;
        } else if (serverTypeString.equals("RSGhost")) {
            serverType = ServerType.REPLICA_SET_GHOST;
        } else if (serverTypeString.equals("RSOther")) {
            serverType = ServerType.REPLICA_SET_OTHER;
        } else if (serverTypeString.equals("Mongos")) {
            serverType = ServerType.SHARD_ROUTER;
        } else if (serverTypeString.equals("Standalone")) {
            serverType = ServerType.STANDALONE;
        } else if (serverTypeString.equals("PossiblePrimary")) {
            serverType = ServerType.UNKNOWN;
        } else if (serverTypeString.equals("Unknown")) {
            serverType = ServerType.UNKNOWN;
        } else {
            throw new UnsupportedOperationException("No handler for server type " + serverTypeString);
        }
        return serverType;
    }

    private void assertTopologyType(final String topologyType) {
        if (topologyType.equals("Single")) {
            assertEquals(SingleServerCluster.class, cluster.getClass());
        } else if (topologyType.equals("ReplicaSetWithPrimary")) {
            assertEquals(MultiServerCluster.class, cluster.getClass());
            assertEquals(REPLICA_SET, cluster.getCurrentDescription().getType());
            assertEquals(1, cluster.getCurrentDescription().getPrimaries().size());
        } else if (topologyType.equals("ReplicaSetNoPrimary")) {
            assertEquals(MultiServerCluster.class, cluster.getClass());
            assertEquals(REPLICA_SET, cluster.getCurrentDescription().getType());
            assertEquals(0, cluster.getCurrentDescription().getPrimaries().size());
        } else if (topologyType.equals("Sharded")) {
            assertEquals(MultiServerCluster.class, cluster.getClass());
            assertEquals(SHARDED, cluster.getCurrentDescription().getType());
        } else if (topologyType.equals("Unknown")) {
            assertEquals(UNKNOWN, cluster.getCurrentDescription().getType());
        } else {
            throw new UnsupportedOperationException("No handler for topology type " + topologyType);
        }
    }

    private void applyResponse(final BsonArray response) {
        ServerAddress serverAddress = new ServerAddress(response.get(0).asString().getValue());
        BsonDocument isMasterResult = response.get(1).asDocument();
        ServerDescription serverDescription;

        if (isMasterResult.isEmpty()) {
            serverDescription = ServerDescription.builder().type(ServerType.UNKNOWN).state(CONNECTING).address(serverAddress).build();
        } else {
            serverDescription = createServerDescription(serverAddress, isMasterResult,
                                                        getVersion(new BsonDocument("versionArray",
                                                                                    new BsonArray(asList(new BsonInt32(2),
                                                                                                         new BsonInt32(6),
                                                                                                         new BsonInt32(0))))),
                                                        5000000);
        }
        factory.sendNotification(serverAddress, serverDescription);
    }

    BaseCluster getCluster(final String uri) {
        ConnectionString connectionString = new ConnectionString(uri);

        ClusterSettings settings = ClusterSettings.builder()
                                                  .serverSelectionTimeout(1, TimeUnit.SECONDS)
                                                  .hosts(getHosts(connectionString))
                                                  .mode(getMode(connectionString))
                                                  .requiredReplicaSetName(connectionString.getRequiredReplicaSetName())
                                                  .build();

        if (settings.getMode() == ClusterConnectionMode.SINGLE) {
            return new SingleServerCluster(new ClusterId(), settings, factory, new NoOpClusterListener());
        } else {
            return new MultiServerCluster(new ClusterId(), settings, factory, new NoOpClusterListener());
        }
    }

    private List<ServerAddress> getHosts(final ConnectionString connectionString) {
        List<ServerAddress> serverAddresses = new ArrayList<ServerAddress>();
        for (String host : connectionString.getHosts()) {
            serverAddresses.add(new ServerAddress(host));
        }
        return serverAddresses;
    }

    private ClusterConnectionMode getMode(final ConnectionString connectionString) {
        if (connectionString.getHosts().size() > 1 || connectionString.getRequiredReplicaSetName() != null) {
            return ClusterConnectionMode.MULTIPLE;
        } else {
            return ClusterConnectionMode.SINGLE;
        }
    }
}


File: driver-core/src/test/unit/com/mongodb/connection/ServerSelectionRttTest.java
/*
 * Copyright 2015 MongoDB, Inc.
 *
 * Licensed under the Apache License, Version 2.0 (the "License");
 * you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at
 *
 *   http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 */

package com.mongodb.connection;

import com.mongodb.JsonPoweredTestHelper;
import org.bson.BsonDocument;
import org.bson.BsonValue;
import org.junit.Test;
import org.junit.runner.RunWith;
import org.junit.runners.Parameterized;

import java.io.File;
import java.io.IOException;
import java.net.URISyntaxException;
import java.util.ArrayList;
import java.util.Collection;
import java.util.List;

import static org.junit.Assert.assertEquals;

// See https://github.com/mongodb/specifications/tree/master/source/server-selection/tests
@RunWith(Parameterized.class)
public class ServerSelectionRttTest {
    private final BsonDocument definition;

    public ServerSelectionRttTest(final String description, final BsonDocument definition) {
        this.definition = definition;
    }

    @Test
    public void shouldPassAllOutcomes() {
        ExponentiallyWeightedMovingAverage subject = new ExponentiallyWeightedMovingAverage(0.2);

        BsonValue current = definition.get("avg_rtt_ms");
        if (current.isNumber()) {
            subject.addSample(current.asNumber().longValue());
        }

        subject.addSample(definition.getNumber("new_rtt_ms").longValue());
        long expected = definition.getNumber("new_avg_rtt").asNumber().longValue();

        assertEquals(subject.getAverage(), expected);
    }

    @Parameterized.Parameters(name = "{0}")
    public static Collection<Object[]> data() throws URISyntaxException, IOException {
        List<Object[]> data = new ArrayList<Object[]>();
        for (File file : JsonPoweredTestHelper.getTestFiles("/server-selection/rtt")) {
            data.add(new Object[]{file.getName(), JsonPoweredTestHelper.getTestDocument(file)});
        }
        return data;
    }

}


File: driver-core/src/test/unit/com/mongodb/connection/ServerSelectionSelectionTest.java
/*
 * Copyright 2015 MongoDB, Inc.
 *
 * Licensed under the Apache License, Version 2.0 (the "License");
 * you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at
 *
 *  http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 */

package com.mongodb.connection;

import com.mongodb.JsonPoweredTestHelper;
import com.mongodb.ReadPreference;
import com.mongodb.ServerAddress;
import com.mongodb.Tag;
import com.mongodb.TagSet;
import com.mongodb.selector.CompositeServerSelector;
import com.mongodb.selector.LatencyMinimizingServerSelector;
import com.mongodb.selector.PrimaryServerSelector;
import com.mongodb.selector.ReadPreferenceServerSelector;
import com.mongodb.selector.ServerSelector;
import org.bson.BsonArray;
import org.bson.BsonDocument;
import org.bson.BsonValue;
import org.junit.Test;
import org.junit.runner.RunWith;
import org.junit.runners.Parameterized;

import java.io.File;
import java.io.IOException;
import java.net.URISyntaxException;
import java.util.ArrayList;
import java.util.Collection;
import java.util.List;
import java.util.concurrent.TimeUnit;

import static java.util.Arrays.asList;
import static org.junit.Assert.assertEquals;
import static org.junit.Assert.assertTrue;

// See https://github.com/mongodb/specifications/tree/master/source/server-selection/tests
@RunWith(Parameterized.class)
public class ServerSelectionSelectionTest {
    private final BsonDocument definition;
    private final ClusterDescription clusterDescription;

    public ServerSelectionSelectionTest(final String description, final BsonDocument definition) {
        this.definition = definition;
        this.clusterDescription = buildClusterDescription(definition.getDocument("topology_description"));
    }

    @Test
    public void shouldPassAllOutcomes() {
        ServerSelector serverSelector = getServerSelector();

        List<ServerDescription> suitableServers = buildServerDescriptions(definition.getArray("suitable_servers"));
        List<ServerDescription> selectedServers = serverSelector.select(clusterDescription);
        assertServers(selectedServers, suitableServers);

        ServerSelector latencyBasedServerSelector = new CompositeServerSelector(asList(serverSelector,
                new LatencyMinimizingServerSelector(15, TimeUnit.MILLISECONDS)));
        List<ServerDescription> inLatencyWindowServers = buildServerDescriptions(definition.getArray("in_latency_window"));
        List<ServerDescription> latencyBasedSelectedServers = latencyBasedServerSelector.select(clusterDescription);
        assertServers(latencyBasedSelectedServers, inLatencyWindowServers);
    }

    @Parameterized.Parameters(name = "{0}")
    public static Collection<Object[]> data() throws URISyntaxException, IOException {
        List<Object[]> data = new ArrayList<Object[]>();
        for (File file : JsonPoweredTestHelper.getTestFiles("/server-selection/server_selection")) {
            data.add(new Object[]{file.getName(), JsonPoweredTestHelper.getTestDocument(file)});
        }
        return data;
    }

    private ClusterDescription buildClusterDescription(final BsonDocument topologyDescription) {
        ClusterType clusterType = getClusterType(topologyDescription.getString("type").getValue());
        ClusterConnectionMode connectionMode = clusterType == ClusterType.STANDALONE ? ClusterConnectionMode.SINGLE
                : ClusterConnectionMode.MULTIPLE;
        List<ServerDescription> servers = buildServerDescriptions(topologyDescription.getArray("servers"));
        return new ClusterDescription(connectionMode, clusterType, servers);
    }

    private ClusterType getClusterType(final String type) {
        if (type.equals("Single")) {
            return ClusterType.STANDALONE;
        } else if (type.startsWith("ReplicaSet")) {
            return ClusterType.REPLICA_SET;
        } else if (type.equals("Sharded")) {
            return ClusterType.SHARDED;
        } else if (type.equals("Unknown")) {
            return ClusterType.UNKNOWN;
        }

        throw new UnsupportedOperationException("Unknown topology type: " + type);
    }

    private List<ServerDescription> buildServerDescriptions(final BsonArray serverDescriptions) {
        List<ServerDescription> descriptions = new ArrayList<ServerDescription>();
        for (BsonValue document : serverDescriptions) {
            descriptions.add(buildServerDescription(document.asDocument()));
        }
        return descriptions;
    }

    private ServerDescription buildServerDescription(final BsonDocument serverDescription) {
        ServerDescription.Builder builder = ServerDescription.builder();
        builder.address(new ServerAddress(serverDescription.getString("address").getValue()));
        builder.type(getServerType(serverDescription.getString("type").getValue()));
        builder.tagSet(buildTagSet(serverDescription.getDocument("tags")));
        builder.roundTripTime(serverDescription.getNumber("avg_rtt_ms").asInt32().getValue(), TimeUnit.MILLISECONDS);
        builder.state(ServerConnectionState.CONNECTED);
        builder.ok(true);
        return builder.build();
    }

    private ServerType getServerType(final String serverTypeString) {
        ServerType serverType;
        if (serverTypeString.equals("RSPrimary")) {
            serverType = ServerType.REPLICA_SET_PRIMARY;
        } else if (serverTypeString.equals("RSSecondary")) {
            serverType = ServerType.REPLICA_SET_SECONDARY;
        } else if (serverTypeString.equals("RSArbiter")) {
            serverType = ServerType.REPLICA_SET_ARBITER;
        } else if (serverTypeString.equals("RSGhost")) {
            serverType = ServerType.REPLICA_SET_GHOST;
        } else if (serverTypeString.equals("RSOther")) {
            serverType = ServerType.REPLICA_SET_OTHER;
        } else if (serverTypeString.equals("Mongos")) {
            serverType = ServerType.SHARD_ROUTER;
        } else if (serverTypeString.equals("Standalone")) {
            serverType = ServerType.STANDALONE;
        } else if (serverTypeString.equals("PossiblePrimary")) {
            serverType = ServerType.UNKNOWN;
        } else if (serverTypeString.equals("Unknown")) {
            serverType = ServerType.UNKNOWN;
        } else {
            throw new UnsupportedOperationException("No handler for server type " + serverTypeString);
        }
        return serverType;
    }

    private List<TagSet> buildTagSets(final BsonArray tags) {
        List<TagSet> tagSets = new ArrayList<TagSet>();
        for (BsonValue tag : tags) {
            tagSets.add(buildTagSet(tag.asDocument()));
        }
        return tagSets;
    }


    private TagSet buildTagSet(final BsonDocument tags) {
        List<Tag> tagsSetTags = new ArrayList<Tag>();
        for (String key: tags.keySet()) {
            tagsSetTags.add(new Tag(key, tags.getString(key).getValue()));
        }
        return new TagSet(tagsSetTags);
    }

    private ServerSelector getServerSelector() {
        if (definition.getString("operation").getValue().equals("write")) {
            return new PrimaryServerSelector();
        } else {
            BsonDocument readPreferenceDefinition = definition.getDocument("read_preference");
            ReadPreference readPreference;
            if (readPreferenceDefinition.getString("mode").getValue().equals("Primary")) {
                readPreference = ReadPreference.valueOf("Primary");
            } else {
                readPreference = ReadPreference.valueOf(readPreferenceDefinition.getString("mode").getValue(),
                        buildTagSets(readPreferenceDefinition.getArray("tag_sets")));
            }
            return new ReadPreferenceServerSelector(readPreference);
        }
    }

    private void assertServers(final List<ServerDescription> actual, final List<ServerDescription> expected) {
        assertEquals(actual.size(), expected.size());
        assertTrue(actual.containsAll(expected));
    }
}


File: driver/src/test/functional/com/mongodb/client/CrudTest.java
/*
 * Copyright 2015 MongoDB, Inc.
 *
 * Licensed under the Apache License, Version 2.0 (the "License");
 * you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at
 *
 *  http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 */

package com.mongodb.client;

import com.mongodb.JsonPoweredTestHelper;
import com.mongodb.client.model.CountOptions;
import com.mongodb.client.model.FindOneAndDeleteOptions;
import com.mongodb.client.model.FindOneAndReplaceOptions;
import com.mongodb.client.model.FindOneAndUpdateOptions;
import com.mongodb.client.model.ReturnDocument;
import com.mongodb.client.model.UpdateOptions;
import com.mongodb.client.result.UpdateResult;
import org.bson.BsonArray;
import org.bson.BsonDocument;
import org.bson.BsonInt32;
import org.bson.BsonNull;
import org.bson.BsonValue;
import org.junit.AssumptionViolatedException;
import org.junit.Before;
import org.junit.Test;
import org.junit.runner.RunWith;
import org.junit.runners.Parameterized;

import java.io.File;
import java.io.IOException;
import java.lang.reflect.InvocationTargetException;
import java.lang.reflect.Method;
import java.net.URISyntaxException;
import java.util.ArrayList;
import java.util.Collection;
import java.util.List;

import static com.mongodb.ClusterFixture.serverVersionAtLeast;
import static java.util.Arrays.asList;
import static org.junit.Assert.assertEquals;
import static org.junit.Assume.assumeFalse;
import static org.junit.Assume.assumeTrue;

// See https://github.com/mongodb/specifications/tree/master/source/crud/tests
@RunWith(Parameterized.class)
public class CrudTest extends DatabaseTestCase {
    private final String filename;
    private final String description;
    private final BsonArray data;
    private final BsonDocument definition;
    private MongoCollection<BsonDocument> collection;

    public CrudTest(final String filename, final String description, final BsonArray data, final BsonDocument definition) {
        this.filename = filename;
        this.description = description;
        this.data = data;
        this.definition = definition;
    }

    @Before
    public void setUp() {
        super.setUp();
        List<BsonDocument> documents = new ArrayList<BsonDocument>();
        for (BsonValue document: data) {
            documents.add(document.asDocument());
        }
        getCollectionHelper().insertDocuments(documents);
        collection = database.getCollection(getClass().getName(), BsonDocument.class);
    }

    @Test
    public void shouldPassAllOutcomes() {
        BsonDocument outcome = getOperationResults(definition.getDocument("operation"));
        BsonDocument expectedOutcome = definition.getDocument("outcome");

        if (checkResult()) {
            assertEquals(description, expectedOutcome.get("result"), outcome.get("result"));
        }
        if (expectedOutcome.containsKey("collection")) {
            assertCollectionEquals(expectedOutcome.getDocument("collection"));
        }
    }

    @Parameterized.Parameters(name = "{1}")
    public static Collection<Object[]> data() throws URISyntaxException, IOException {
        List<Object[]> data = new ArrayList<Object[]>();
        for (File file : JsonPoweredTestHelper.getTestFiles("/crud")) {
            BsonDocument testDocument = JsonPoweredTestHelper.getTestDocument(file);
            for (BsonValue test: testDocument.getArray("tests")) {
                data.add(new Object[]{file.getName(), test.asDocument().getString("description").getValue(),
                        testDocument.getArray("data"), test.asDocument()});
            }
        }
        return data;
    }

    private boolean checkResult() {
        if (filename.contains("insert")) {
            // We don't return any id's for insert commands
            return false;
        } else if (!serverVersionAtLeast(asList(3, 0, 0))
                && description.contains("when no documents match with upsert returning the document before modification")) {
            // Pre 3.0 versions of MongoDB return an empty document rather than a null
            return false;
        }
        return true;
    }

    private void assertCollectionEquals(final BsonDocument expectedCollection) {
        MongoCollection<BsonDocument> collectionToCompare = collection;
        if (expectedCollection.containsKey("name")) {
            collectionToCompare = database.getCollection(expectedCollection.getString("name").getValue(), BsonDocument.class);
        }
        assertEquals(description, expectedCollection.getArray("data"), collectionToCompare.find().into(new BsonArray()));
    }

    private BsonDocument getOperationResults(final BsonDocument operation) {
        String name = operation.getString("name").getValue();
        BsonDocument arguments = operation.getDocument("arguments");

        String methodName = "get" + name.substring(0, 1).toUpperCase() + name.substring(1) + "Result";
        try {
            Method method = getClass().getDeclaredMethod(methodName, BsonDocument.class);
            return (BsonDocument) method.invoke(this, arguments);
        } catch (NoSuchMethodException e) {
            throw new UnsupportedOperationException("No handler for operation " + methodName);
        } catch (InvocationTargetException e) {
            if (e.getTargetException() instanceof AssumptionViolatedException) {
                throw (AssumptionViolatedException) e.getTargetException();
            }
            throw new UnsupportedOperationException("Invalid handler for operation " + methodName);
        } catch (IllegalAccessException e) {
            throw new UnsupportedOperationException("Invalid handler access for operation " + methodName);
        }
    }

    private BsonDocument toResult(final int count) {
        return toResult(new BsonInt32(count));
    }
    private BsonDocument toResult(final MongoIterable<BsonDocument> results) {
        return toResult(new BsonArray(results.into(new ArrayList<BsonDocument>())));
    }
    private BsonDocument toResult(final String key, final BsonValue value) {
        return toResult(new BsonDocument(key, value));
    }
    private BsonDocument toResult(final UpdateResult updateResult) {
        assumeTrue(serverVersionAtLeast(asList(2, 6, 0))); // ModifiedCount is not accessible pre 2.6
        BsonDocument resultDoc = new BsonDocument("matchedCount", new BsonInt32((int) updateResult.getMatchedCount()))
                .append("modifiedCount", new BsonInt32((int) updateResult.getModifiedCount()));
        if (updateResult.getUpsertedId() != null) {
            resultDoc.append("upsertedId", updateResult.getUpsertedId());
        }
        return toResult(resultDoc);
    }
    private BsonDocument toResult(final BsonValue results) {
        return new BsonDocument("result", results != null ? results : BsonNull.VALUE);
    }
    private BsonDocument getAggregateResult(final BsonDocument arguments) {
        if (!serverVersionAtLeast(asList(2, 6, 0))) {
            assumeFalse(description.contains("$out"));
        }

        List<BsonDocument> pipeline = new ArrayList<BsonDocument>();
        for (BsonValue stage: arguments.getArray("pipeline")) {
            pipeline.add(stage.asDocument());
        }
        return toResult(collection.aggregate(pipeline).batchSize(arguments.getNumber("batchSize").intValue()));
    }

    private BsonDocument getCountResult(final BsonDocument arguments) {
        CountOptions options = new CountOptions();
        if (arguments.containsKey("skip")) {
            options.skip(arguments.getNumber("skip").intValue());
        }
        if (arguments.containsKey("limit")) {
            options.limit(arguments.getNumber("limit").intValue());
        }

        return toResult((int) collection.count(arguments.getDocument("filter"), options));
    }

    private BsonDocument getDistinctResult(final BsonDocument arguments) {
        return toResult(collection.distinct(arguments.getString("fieldName").getValue(), BsonInt32.class)
                .filter(arguments.getDocument("filter")).into(new BsonArray()));
    }

    private BsonDocument getFindResult(final BsonDocument arguments) {
        FindIterable<BsonDocument> findIterable = collection.find(arguments.getDocument("filter"));
        if (arguments.containsKey("skip")) {
            findIterable.skip(arguments.getNumber("skip").intValue());
        }
        if (arguments.containsKey("limit")) {
            findIterable.limit(arguments.getNumber("limit").intValue());
        }
        if (arguments.containsKey("batchSize")) {
            findIterable.batchSize(arguments.getNumber("batchSize").intValue());
        }
        return toResult(findIterable);
    }

    private BsonDocument getDeleteManyResult(final BsonDocument arguments) {
        return toResult("deletedCount",
                new BsonInt32((int) collection.deleteMany(arguments.getDocument("filter")).getDeletedCount()));
    }

    private BsonDocument getDeleteOneResult(final BsonDocument arguments) {
        return toResult("deletedCount", new BsonInt32((int) collection.deleteOne(arguments.getDocument("filter")).getDeletedCount()));
    }

    private BsonDocument getFindOneAndDeleteResult(final BsonDocument arguments) {
        FindOneAndDeleteOptions options = new FindOneAndDeleteOptions();
        if (arguments.containsKey("projection")) {
            options.projection(arguments.getDocument("projection"));
        }
        if (arguments.containsKey("sort")) {
            options.sort(arguments.getDocument("sort"));
        }
        return toResult(collection.findOneAndDelete(arguments.getDocument("filter"), options));
    }

    private BsonDocument getFindOneAndReplaceResult(final BsonDocument arguments) {
        assumeTrue(serverVersionAtLeast(asList(2, 6, 0))); // in 2.4 the server can ignore the supplied _id and creates an ObjectID
        FindOneAndReplaceOptions options = new FindOneAndReplaceOptions();
        if (arguments.containsKey("projection")) {
            options.projection(arguments.getDocument("projection"));
        }
        if (arguments.containsKey("sort")) {
            options.sort(arguments.getDocument("sort"));
        }
        if (arguments.containsKey("upsert")) {
            options.upsert(arguments.getBoolean("upsert").getValue());
        }
        if (arguments.containsKey("returnDocument")) {
            options.returnDocument(arguments.getString("returnDocument").getValue().equals("After") ? ReturnDocument.AFTER
                    : ReturnDocument.BEFORE);
        }
        return toResult(collection.findOneAndReplace(arguments.getDocument("filter"), arguments.getDocument("replacement"), options));
    }

    private BsonDocument getFindOneAndUpdateResult(final BsonDocument arguments) {
        FindOneAndUpdateOptions options = new FindOneAndUpdateOptions();
        if (arguments.containsKey("projection")) {
            options.projection(arguments.getDocument("projection"));
        }
        if (arguments.containsKey("sort")) {
            options.sort(arguments.getDocument("sort"));
        }
        if (arguments.containsKey("upsert")) {
            options.upsert(arguments.getBoolean("upsert").getValue());
        }
        if (arguments.containsKey("returnDocument")) {
            options.returnDocument(arguments.getString("returnDocument").getValue().equals("After") ? ReturnDocument.AFTER
                    : ReturnDocument.BEFORE);
        }
        return toResult(collection.findOneAndUpdate(arguments.getDocument("filter"), arguments.getDocument("update"), options));
    }

    private BsonDocument getInsertOneResult(final BsonDocument arguments) {
        collection.insertOne(arguments.getDocument("document"));
        return toResult((BsonValue) null);
    }

    private BsonDocument getInsertManyResult(final BsonDocument arguments) {
        List<BsonDocument> documents = new ArrayList<BsonDocument>();
        for (BsonValue document : arguments.getArray("documents")) {
            documents.add(document.asDocument());
        }
        collection.insertMany(documents);
        return toResult((BsonValue) null);
    }

    private BsonDocument getReplaceOneResult(final BsonDocument arguments) {
        UpdateOptions options = new UpdateOptions();
        if (arguments.containsKey("upsert")) {
            options.upsert(arguments.getBoolean("upsert").getValue());
        }
        return toResult(collection.replaceOne(arguments.getDocument("filter"), arguments.getDocument("replacement"), options));
    }

    private BsonDocument getUpdateManyResult(final BsonDocument arguments) {
        UpdateOptions options = new UpdateOptions();
        if (arguments.containsKey("upsert")) {
            options.upsert(arguments.getBoolean("upsert").getValue());
        }
        return toResult(collection.updateMany(arguments.getDocument("filter"), arguments.getDocument("update"), options));
    }

    private BsonDocument getUpdateOneResult(final BsonDocument arguments) {
        UpdateOptions options = new UpdateOptions();
        if (arguments.containsKey("upsert")) {
            options.upsert(arguments.getBoolean("upsert").getValue());
        }
        return toResult(collection.updateOne(arguments.getDocument("filter"), arguments.getDocument("update"), options));
    }
}
