Refactoring Types: ['Extract Superclass', 'Extract Method']
exingAcceptanceTest.java
/*
 * Copyright (c) 2002-2015 "Neo Technology,"
 * Network Engine for Objects in Lund AB [http://neotechnology.com]
 *
 * This file is part of Neo4j.
 *
 * Neo4j is free software: you can redistribute it and/or modify
 * it under the terms of the GNU General Public License as published by
 * the Free Software Foundation, either version 3 of the License, or
 * (at your option) any later version.
 *
 * This program is distributed in the hope that it will be useful,
 * but WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
 * GNU General Public License for more details.
 *
 * You should have received a copy of the GNU General Public License
 * along with this program.  If not, see <http://www.gnu.org/licenses/>.
 */
package org.neo4j.graphdb;

import org.junit.Rule;
import org.junit.Test;

import java.util.Map;

import org.neo4j.graphdb.schema.IndexDefinition;
import org.neo4j.helpers.collection.Iterables;
import org.neo4j.test.ImpermanentDatabaseRule;

import static org.hamcrest.core.IsEqual.equalTo;
import static org.junit.Assert.assertEquals;
import static org.junit.Assert.assertThat;
import static org.neo4j.graphdb.Neo4jMatchers.containsOnly;
import static org.neo4j.graphdb.Neo4jMatchers.createIndex;
import static org.neo4j.graphdb.Neo4jMatchers.findNodesByLabelAndProperty;
import static org.neo4j.graphdb.Neo4jMatchers.hasProperty;
import static org.neo4j.graphdb.Neo4jMatchers.inTx;
import static org.neo4j.graphdb.Neo4jMatchers.isEmpty;
import static org.neo4j.graphdb.Neo4jMatchers.waitForIndex;
import static org.neo4j.helpers.collection.IteratorUtil.asSet;
import static org.neo4j.helpers.collection.IteratorUtil.count;
import static org.neo4j.helpers.collection.MapUtil.map;

public class IndexingAcceptanceTest
{
    /* This test is a bit interesting. It tests a case where we've got a property that sits in one
     * property block and the value is of a long type. So given that plus that there's an index for that
     * label/property, do an update that changes the long value into a value that requires two property blocks.
     * This is interesting because the transaction logic compares before/after views per property record and
     * not per node as a whole.
     *
     * In this case this change will be converted into one "add" and one "remove" property updates instead of
     * a single "change" property update. At the very basic level it's nice to test for this corner-case so
     * that the externally observed behavior is correct, even if this test doesn't assert anything about
     * the underlying add/remove vs. change internal details.
     */
    @Test
    public void shouldInterpretPropertyAsChangedEvenIfPropertyMovesFromOneRecordToAnother() throws Exception
    {
        // GIVEN
        GraphDatabaseService beansAPI = dbRule.getGraphDatabaseAPI();
        long smallValue = 10L, bigValue = 1L << 62;
        Node myNode;
        {
            try ( Transaction tx = beansAPI.beginTx() )
            {
                myNode = beansAPI.createNode( LABEL1 );
                myNode.setProperty( "pad0", true );
                myNode.setProperty( "pad1", true );
                myNode.setProperty( "pad2", true );
                // Use a small long here which will only occupy one property block
                myNode.setProperty( "key", smallValue );

                tx.success();
            }
        }
        {
            IndexDefinition indexDefinition;
            try ( Transaction tx = beansAPI.beginTx() )
            {
                indexDefinition = beansAPI.schema().indexFor( LABEL1 ).on( "key" ).create();

                tx.success();
            }
            waitForIndex( beansAPI, indexDefinition );
        }

        // WHEN
        try ( Transaction tx = beansAPI.beginTx() )
        {
            // A big long value which will occupy two property blocks
            myNode.setProperty( "key", bigValue );
            tx.success();
        }

        // THEN
        assertThat( findNodesByLabelAndProperty( LABEL1, "key", bigValue, beansAPI ), containsOnly( myNode ) );
        assertThat( findNodesByLabelAndProperty( LABEL1, "key", smallValue, beansAPI ), isEmpty() );
    }

    @Test
    public void shouldUseDynamicPropertiesToIndexANodeWhenAddedAlongsideExistingPropertiesInASeparateTransaction() throws Exception
    {
        // Given
        GraphDatabaseService beansAPI = dbRule.getGraphDatabaseAPI();

        // When
        long id;
        {
            try ( Transaction tx = beansAPI.beginTx() )
            {
                Node myNode = beansAPI.createNode();
                id = myNode.getId();
                myNode.setProperty( "key0", true );
                myNode.setProperty( "key1", true );

                tx.success();
            }
        }
        {
            IndexDefinition indexDefinition;
            try ( Transaction tx = beansAPI.beginTx() )
            {
                indexDefinition = beansAPI.schema().indexFor( LABEL1 ).on( "key2" ).create();

                tx.success();
            }
            waitForIndex( beansAPI, indexDefinition );
        }
        Node myNode;
        {
            try ( Transaction tx = beansAPI.beginTx() )
            {
                myNode = beansAPI.getNodeById( id );
                myNode.addLabel( LABEL1 );
                myNode.setProperty( "key2", LONG_STRING );
                myNode.setProperty( "key3", LONG_STRING );

                tx.success();
            }
        }

        // Then
        assertThat( myNode, inTx( beansAPI, hasProperty( "key2" ).withValue( LONG_STRING ) ) );
        assertThat( myNode, inTx( beansAPI, hasProperty( "key3" ).withValue( LONG_STRING ) ) );
        assertThat( findNodesByLabelAndProperty( LABEL1, "key2", LONG_STRING, beansAPI ), containsOnly( myNode ) );
    }

    @Test
    public void searchingForNodeByPropertyShouldWorkWithoutIndex() throws Exception
    {
        // Given
        GraphDatabaseService beansAPI = dbRule.getGraphDatabaseService();
        Node myNode = createNode( beansAPI, map( "name", "Hawking" ), LABEL1 );

        // When
        assertThat( findNodesByLabelAndProperty( LABEL1, "name", "Hawking", beansAPI ), containsOnly( myNode ) );
    }

    @Test
    public void searchingUsesIndexWhenItExists() throws Exception
    {
        // Given
        GraphDatabaseService beansAPI = dbRule.getGraphDatabaseService();
        Node myNode = createNode( beansAPI, map( "name", "Hawking" ), LABEL1 );
        createIndex( beansAPI, LABEL1, "name" );

        // When
        assertThat( findNodesByLabelAndProperty( LABEL1, "name", "Hawking", beansAPI ), containsOnly( myNode ) );
    }

    @Test
    public void shouldCorrectlyUpdateIndexesWhenChangingLabelsAndPropertyAtTheSameTime() throws Exception
    {
        // Given
        GraphDatabaseService beansAPI = dbRule.getGraphDatabaseService();
        Node myNode = createNode( beansAPI, map( "name", "Hawking" ), LABEL1, LABEL2 );
        createIndex( beansAPI, LABEL1, "name" );
        createIndex( beansAPI, LABEL2, "name" );
        createIndex( beansAPI, LABEL3, "name" );

        // When
        try ( Transaction tx = beansAPI.beginTx() )
        {
            myNode.removeLabel( LABEL1 );
            myNode.addLabel( LABEL3 );
            myNode.setProperty( "name", "Einstein" );
            tx.success();
        }

        // Then
        assertThat( myNode, inTx( beansAPI, hasProperty("name").withValue( "Einstein" ) ) );
        assertThat( labels( myNode ), containsOnly( LABEL2, LABEL3 ) );

        assertThat( findNodesByLabelAndProperty( LABEL1, "name", "Hawking", beansAPI ), isEmpty() );
        assertThat( findNodesByLabelAndProperty( LABEL1, "name", "Einstein", beansAPI ), isEmpty() );

        assertThat( findNodesByLabelAndProperty( LABEL2, "name", "Hawking", beansAPI ), isEmpty() );
        assertThat( findNodesByLabelAndProperty( LABEL2, "name", "Einstein", beansAPI ), containsOnly( myNode ) );

        assertThat( findNodesByLabelAndProperty( LABEL3, "name", "Hawking", beansAPI ), isEmpty() );
        assertThat( findNodesByLabelAndProperty( LABEL3, "name", "Einstein", beansAPI ), containsOnly( myNode ) );
    }

    @Test
    public void shouldCorrectlyUpdateIndexesWhenChangingLabelsAndPropertyMultipleTimesAllAtOnce() throws Exception
    {
        // Given
        GraphDatabaseService beansAPI = dbRule.getGraphDatabaseService();
        Node myNode = createNode( beansAPI, map( "name", "Hawking" ), LABEL1, LABEL2 );
        createIndex( beansAPI, LABEL1, "name" );
        createIndex( beansAPI, LABEL2, "name" );
        createIndex( beansAPI, LABEL3, "name" );

        // When
        try ( Transaction tx = beansAPI.beginTx() )
        {
            myNode.addLabel( LABEL3 );
            myNode.setProperty( "name", "Einstein" );
            myNode.removeLabel( LABEL1 );
            myNode.setProperty( "name", "Feynman" );
            tx.success();
        }

        // Then
        assertThat( myNode, inTx( beansAPI, hasProperty("name").withValue( "Feynman" ) ) );
        assertThat( labels( myNode ), containsOnly( LABEL2, LABEL3 ) );

        assertThat( findNodesByLabelAndProperty( LABEL1, "name", "Hawking", beansAPI ), isEmpty() );
        assertThat( findNodesByLabelAndProperty( LABEL1, "name", "Einstein", beansAPI ), isEmpty() );
        assertThat( findNodesByLabelAndProperty( LABEL1, "name", "Feynman", beansAPI ), isEmpty() );

        assertThat( findNodesByLabelAndProperty( LABEL2, "name", "Hawking", beansAPI ), isEmpty() );
        assertThat( findNodesByLabelAndProperty( LABEL1, "name", "Einstein", beansAPI ), isEmpty() );
        assertThat( findNodesByLabelAndProperty( LABEL2, "name", "Feynman", beansAPI ), containsOnly( myNode ) );

        assertThat( findNodesByLabelAndProperty( LABEL3, "name", "Hawking", beansAPI ), isEmpty() );
        assertThat( findNodesByLabelAndProperty( LABEL1, "name", "Einstein", beansAPI ), isEmpty() );
        assertThat( findNodesByLabelAndProperty( LABEL3, "name", "Feynman", beansAPI ), containsOnly( myNode ) );
    }

    @Test
    public void searchingByLabelAndPropertyReturnsEmptyWhenMissingLabelOrProperty() throws Exception
    {
        // Given
        GraphDatabaseService beansAPI = dbRule.getGraphDatabaseService();

        // When/Then
        assertThat( findNodesByLabelAndProperty( LABEL1, "name", "Hawking", beansAPI ), isEmpty() );
    }

    @Test
    public void shouldSeeIndexUpdatesWhenQueryingOutsideTransaction() throws Exception
    {
        // GIVEN
        GraphDatabaseService beansAPI = dbRule.getGraphDatabaseService();
        createIndex( beansAPI, LABEL1, "name" );
        Node firstNode = createNode( beansAPI, map( "name", "Mattias" ), LABEL1 );

        // WHEN THEN
        assertThat( findNodesByLabelAndProperty( LABEL1, "name", "Mattias", beansAPI ), containsOnly( firstNode ) );
        Node secondNode = createNode( beansAPI, map( "name", "Taylor" ), LABEL1 );
        assertThat( findNodesByLabelAndProperty( LABEL1, "name", "Taylor", beansAPI ), containsOnly( secondNode ) );
    }

    @Test
    public void createdNodeShouldShowUpWithinTransaction() throws Exception
    {
        // GIVEN
        GraphDatabaseService beansAPI = dbRule.getGraphDatabaseService();
        createIndex( beansAPI, LABEL1, "name" );

        // WHEN
        Transaction tx = beansAPI.beginTx();

        Node firstNode = createNode( beansAPI, map( "name", "Mattias" ), LABEL1 );
        long sizeBeforeDelete = count( beansAPI.findNodes( LABEL1, "name", "Mattias" ) );
        firstNode.delete();
        long sizeAfterDelete = count( beansAPI.findNodes( LABEL1, "name", "Mattias" ) );

        tx.close();

        // THEN
        assertThat( sizeBeforeDelete, equalTo(1l) );
        assertThat( sizeAfterDelete, equalTo(0l) );
    }

    @Test
    public void deletedNodeShouldShowUpWithinTransaction() throws Exception
    {
        // GIVEN
        GraphDatabaseService beansAPI = dbRule.getGraphDatabaseService();
        createIndex( beansAPI, LABEL1, "name" );
        Node firstNode = createNode( beansAPI, map( "name", "Mattias" ), LABEL1 );

        // WHEN
        Transaction tx = beansAPI.beginTx();

        long sizeBeforeDelete = count( beansAPI.findNodes( LABEL1, "name", "Mattias" ) );
        firstNode.delete();
        long sizeAfterDelete = count( beansAPI.findNodes( LABEL1, "name", "Mattias" ) );

        tx.close();

        // THEN
        assertThat( sizeBeforeDelete, equalTo(1l) );
        assertThat( sizeAfterDelete, equalTo(0l) );
    }

    @Test
    public void createdNodeShouldShowUpInIndexQuery() throws Exception
    {
        // GIVEN
        GraphDatabaseService beansAPI = dbRule.getGraphDatabaseService();
        createIndex( beansAPI, LABEL1, "name" );
        createNode( beansAPI, map( "name", "Mattias" ), LABEL1 );

        // WHEN
        Transaction tx = beansAPI.beginTx();

        long sizeBeforeDelete = count( beansAPI.findNodes( LABEL1, "name", "Mattias" ) );
        createNode( beansAPI, map( "name", "Mattias" ), LABEL1 );
        long sizeAfterDelete = count( beansAPI.findNodes( LABEL1, "name", "Mattias" ) );

        tx.close();

        // THEN
        assertThat( sizeBeforeDelete, equalTo(1l) );
        assertThat( sizeAfterDelete, equalTo(2l) );
    }

    @Test
    public void shouldBeAbleToQuerySupportedPropertyTypes() throws Exception
    {
        // GIVEN
        String property = "name";
        GraphDatabaseService db = dbRule.getGraphDatabaseService();
        createIndex( db, LABEL1, property );

        // WHEN & THEN
        assertCanCreateAndFind( db, LABEL1, property, "A String" );
        assertCanCreateAndFind( db, LABEL1, property, true );
        assertCanCreateAndFind( db, LABEL1, property, false );
        assertCanCreateAndFind( db, LABEL1, property, (byte) 56 );
        assertCanCreateAndFind( db, LABEL1, property, 'z' );
        assertCanCreateAndFind( db, LABEL1, property, (short)12 );
        assertCanCreateAndFind( db, LABEL1, property, 12 );
        assertCanCreateAndFind( db, LABEL1, property, 12l );
        assertCanCreateAndFind( db, LABEL1, property, (float)12. );
        assertCanCreateAndFind( db, LABEL1, property, 12. );

        assertCanCreateAndFind( db, LABEL1, property, new String[]{"A String"} );
        assertCanCreateAndFind( db, LABEL1, property, new boolean[]{true} );
        assertCanCreateAndFind( db, LABEL1, property, new Boolean[]{false} );
        assertCanCreateAndFind( db, LABEL1, property, new byte[]{56} );
        assertCanCreateAndFind( db, LABEL1, property, new Byte[]{57} );
        assertCanCreateAndFind( db, LABEL1, property, new char[]{'a'} );
        assertCanCreateAndFind( db, LABEL1, property, new Character[]{'b'} );
        assertCanCreateAndFind( db, LABEL1, property, new short[]{12} );
        assertCanCreateAndFind( db, LABEL1, property, new Short[]{13} );
        assertCanCreateAndFind( db, LABEL1, property, new int[]{14} );
        assertCanCreateAndFind( db, LABEL1, property, new Integer[]{15} );
        assertCanCreateAndFind( db, LABEL1, property, new long[]{16l} );
        assertCanCreateAndFind( db, LABEL1, property, new Long[]{17l} );
        assertCanCreateAndFind( db, LABEL1, property, new float[]{(float)18.} );
        assertCanCreateAndFind( db, LABEL1, property, new Float[]{(float)19.} );
        assertCanCreateAndFind( db, LABEL1, property, new double[]{20.} );
        assertCanCreateAndFind( db, LABEL1, property, new Double[]{21.} );
    }

    @Test
    public void shouldRetrieveMultipleNodesWithSameValueFromIndex() throws Exception
    {
        // this test was included here for now as a precondition for the following test

        // given
        GraphDatabaseService graph = dbRule.getGraphDatabaseService();
        createIndex( graph, LABEL1, "name" );

        Node node1, node2;
        try ( Transaction tx = graph.beginTx() )
        {
            node1 = graph.createNode( LABEL1 );
            node1.setProperty( "name", "Stefan" );

            node2 = graph.createNode( LABEL1 );
            node2.setProperty( "name", "Stefan" );
            tx.success();
        }

        try ( Transaction tx = graph.beginTx() )
        {
            ResourceIterator<Node> result = graph.findNodes( LABEL1, "name", "Stefan" );
            assertEquals( asSet( node1, node2 ), asSet( result ) );

            tx.success();
        }
    }

    @Test( expected = MultipleFoundException.class )
    public void shouldThrowWhenMulitpleResultsForSingleNode() throws Exception
    {
        // given
        GraphDatabaseService graph = dbRule.getGraphDatabaseService();
        createIndex( graph, LABEL1, "name" );

        Node node1, node2;
        try ( Transaction tx = graph.beginTx() )
        {
            node1 = graph.createNode( LABEL1 );
            node1.setProperty( "name", "Stefan" );

            node2 = graph.createNode( LABEL1 );
            node2.setProperty( "name", "Stefan" );
            tx.success();
        }

        try ( Transaction tx = graph.beginTx() )
        {
            graph.findNode( LABEL1, "name", "Stefan" );
        }
    }

    @Test
    public void shouldAddIndexedPropertyToNodeWithDynamicLabels()
    {
        // Given
        int indexesCount = 20;
        String labelPrefix = "foo";
        String propertyKeyPrefix = "bar";
        String propertyValuePrefix = "baz";
        GraphDatabaseService db = dbRule.getGraphDatabaseService();

        for ( int i = 0; i < indexesCount; i++ )
        {
            createIndex( db, DynamicLabel.label( labelPrefix + i ), propertyKeyPrefix + i );
        }

        // When
        long nodeId;
        try ( Transaction tx = db.beginTx() )
        {
            nodeId = db.createNode().getId();
            tx.success();
        }

        try ( Transaction tx = db.beginTx() )
        {
            Node node = db.getNodeById( nodeId );
            for ( int i = 0; i < indexesCount; i++ )
            {
                node.addLabel( DynamicLabel.label( labelPrefix + i ) );
                node.setProperty( propertyKeyPrefix + i, propertyValuePrefix + i );
            }
            tx.success();
        }

        // Then
        try ( Transaction tx = db.beginTx() )
        {
            for ( int i = 0; i < indexesCount; i++ )
            {
                Label label = DynamicLabel.label( labelPrefix + i );
                String key = propertyKeyPrefix + i;
                String value = propertyValuePrefix + i;

                ResourceIterable<Node> nodes = db.findNodesByLabelAndProperty( label, key, value );
                assertEquals( 1, Iterables.count( nodes ) );
            }
            tx.success();
        }
    }

    private void assertCanCreateAndFind( GraphDatabaseService db, Label label, String propertyKey, Object value )
    {
        Node created = createNode( db, map( propertyKey, value ), label );

        try ( Transaction tx = db.beginTx() )
        {
            Node found = db.findNode( label, propertyKey, value );
            assertThat( found, equalTo( created ) );
            found.delete();
            tx.success();
        }
    }

    public static final String LONG_STRING = "a long string that has to be stored in dynamic records";

    public @Rule
    ImpermanentDatabaseRule dbRule = new ImpermanentDatabaseRule();

    private Label LABEL1 = DynamicLabel.label( "LABEL1" );
    private Label LABEL2 = DynamicLabel.label( "LABEL2" );
    private Label LABEL3 = DynamicLabel.label( "LABEL3" );

    private Node createNode( GraphDatabaseService beansAPI, Map<String, Object> properties, Label... labels )
    {
        try ( Transaction tx = beansAPI.beginTx() )
        {
            Node node = beansAPI.createNode( labels );
            for ( Map.Entry<String, Object> property : properties.entrySet() )
                node.setProperty( property.getKey(), property.getValue() );
            tx.success();
            return node;
        }
    }

    private Neo4jMatchers.Deferred<Label> labels( final Node myNode )
    {
        return new Neo4jMatchers.Deferred<Label>( dbRule.getGraphDatabaseService() )
        {
            @Override
            protected Iterable<Label> manifest()
            {
                return myNode.getLabels();
            }
        };
    }
}


File: community/kernel/src/test/java/org/neo4j/kernel/api/index/IndexAccessorCompatibility.java
/*
 * Copyright (c) 2002-2015 "Neo Technology,"
 * Network Engine for Objects in Lund AB [http://neotechnology.com]
 *
 * This file is part of Neo4j.
 *
 * Neo4j is free software: you can redistribute it and/or modify
 * it under the terms of the GNU General Public License as published by
 * the Free Software Foundation, either version 3 of the License, or
 * (at your option) any later version.
 *
 * This program is distributed in the hope that it will be useful,
 * but WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
 * GNU General Public License for more details.
 *
 * You should have received a copy of the GNU General Public License
 * along with this program.  If not, see <http://www.gnu.org/licenses/>.
 */
package org.neo4j.kernel.api.index;

import org.junit.After;
import org.junit.Before;

import java.io.IOException;
import java.util.Collections;
import java.util.LinkedList;
import java.util.List;

import org.neo4j.collection.primitive.PrimitiveLongIterator;
import org.neo4j.kernel.api.exceptions.index.IndexCapacityExceededException;
import org.neo4j.kernel.configuration.Config;
import org.neo4j.kernel.impl.api.index.IndexUpdateMode;
import org.neo4j.kernel.impl.api.index.sampling.IndexSamplingConfig;

public class IndexAccessorCompatibility extends IndexProviderCompatibilityTestSuite.Compatibility
{
    protected IndexAccessor accessor;

    private boolean isUnique = true;

    public IndexAccessorCompatibility( IndexProviderCompatibilityTestSuite testSuite, boolean isUnique )
    {
        super(testSuite);
        this.isUnique = isUnique;
    }

    @Before
    public void before() throws Exception
    {
        IndexConfiguration indexConfig = new IndexConfiguration( isUnique );
        IndexSamplingConfig indexSamplingConfig = new IndexSamplingConfig( new Config() );
        IndexPopulator populator = indexProvider.getPopulator( 17, descriptor, indexConfig, indexSamplingConfig );
        populator.create();
        populator.close( true );
        accessor = indexProvider.getOnlineAccessor( 17, indexConfig, indexSamplingConfig );
    }

    @After
    public void after() throws IOException
    {
        accessor.drop();
        accessor.close();
    }

    protected List<Long> getAllNodes( String propertyValue ) throws IOException
    {
        try ( IndexReader reader = accessor.newReader() )
        {
            List<Long> list = new LinkedList<>();
            for ( PrimitiveLongIterator iterator = reader.lookup( propertyValue ); iterator.hasNext(); )
            {
                list.add( iterator.next() );
            }
            Collections.sort( list );
            return list;
        }
    }

    protected List<Long> getAllNodes() throws IOException
    {
        try ( IndexReader reader = accessor.newReader() )
        {
            List<Long> list = new LinkedList<>();
            for ( PrimitiveLongIterator iterator = reader.scan(); iterator.hasNext(); )
            {
                list.add( iterator.next() );
            }
            Collections.sort( list );
            return list;
        }
    }

    protected void updateAndCommit( List<NodePropertyUpdate> updates )
            throws IOException, IndexEntryConflictException, IndexCapacityExceededException
    {
        try ( IndexUpdater updater = accessor.newUpdater( IndexUpdateMode.ONLINE ) )
        {
            for ( NodePropertyUpdate update : updates )
            {
                updater.process( update );
            }
        }
    }

}


File: community/kernel/src/test/java/org/neo4j/kernel/api/index/NonUniqueIndexAccessorCompatibility.java
/*
 * Copyright (c) 2002-2015 "Neo Technology,"
 * Network Engine for Objects in Lund AB [http://neotechnology.com]
 *
 * This file is part of Neo4j.
 *
 * Neo4j is free software: you can redistribute it and/or modify
 * it under the terms of the GNU General Public License as published by
 * the Free Software Foundation, either version 3 of the License, or
 * (at your option) any later version.
 *
 * This program is distributed in the hope that it will be useful,
 * but WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
 * GNU General Public License for more details.
 *
 * You should have received a copy of the GNU General Public License
 * along with this program.  If not, see <http://www.gnu.org/licenses/>.
 */
package org.neo4j.kernel.api.index;

import org.junit.Ignore;
import org.junit.Test;

import static java.util.Arrays.asList;
import static org.hamcrest.Matchers.equalTo;
import static org.junit.Assert.assertThat;

@Ignore( "Not a test. This is a compatibility suite that provides test cases for verifying" +
        " SchemaIndexProvider implementations. Each index provider that is to be tested by this suite" +
        " must create their own test class extending IndexProviderCompatibilityTestSuite." +
        " The @Ignore annotation doesn't prevent these tests to run, it rather removes some annoying" +
        " errors or warnings in some IDEs about test classes needing a public zero-arg constructor." )
public class NonUniqueIndexAccessorCompatibility extends IndexAccessorCompatibility
{
    private static final int PROPERTY_KEY_ID = 100;

    public NonUniqueIndexAccessorCompatibility( IndexProviderCompatibilityTestSuite testSuite )
    {
        super( testSuite, false );
    }

    @Ignore( "Invalid assumption since we currently must rely on close throwing exception for injected"
             + "transactions that violate a constraint" )
    @Test
    public void closingAnOnlineIndexUpdaterMustNotThrowEvenIfItHasBeenFedConflictingData() throws Exception
    {
        // The reason is that we use and close IndexUpdaters in commit - not in prepare - and therefor
        // we cannot have them go around and throw exceptions, because that could potentially break
        // recovery.
        // Conflicting data can happen because of faulty data coercion. These faults are resolved by
        // the exact-match filtering we do on index lookups in StateHandlingStatementOperations.

        updateAndCommit( asList(
                NodePropertyUpdate.add( 1L, PROPERTY_KEY_ID, "a", new long[]{1000} ),
                NodePropertyUpdate.add( 2L, PROPERTY_KEY_ID, "a", new long[]{1000} ) ) );

        assertThat( getAllNodes( "a" ), equalTo( asList( 1L, 2L ) ) );
    }

    @Test
    public void testIndexSeekAndScan() throws Exception
    {
        updateAndCommit( asList(
                NodePropertyUpdate.add( 1L, PROPERTY_KEY_ID, "a", new long[]{1000} ),
                NodePropertyUpdate.add( 2L, PROPERTY_KEY_ID, "a", new long[]{1000} ),
                NodePropertyUpdate.add( 3L, PROPERTY_KEY_ID, "b", new long[]{1000} ) ) );

        assertThat( getAllNodes( "a" ), equalTo( asList( 1L, 2L ) ) );
        assertThat( getAllNodes(), equalTo( asList( 1L, 2L, 3L ) ) );
    }
}

File: community/kernel/src/test/java/org/neo4j/kernel/api/index/UniqueIndexAccessorCompatibility.java
/*
 * Copyright (c) 2002-2015 "Neo Technology,"
 * Network Engine for Objects in Lund AB [http://neotechnology.com]
 *
 * This file is part of Neo4j.
 *
 * Neo4j is free software: you can redistribute it and/or modify
 * it under the terms of the GNU General Public License as published by
 * the Free Software Foundation, either version 3 of the License, or
 * (at your option) any later version.
 *
 * This program is distributed in the hope that it will be useful,
 * but WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
 * GNU General Public License for more details.
 *
 * You should have received a copy of the GNU General Public License
 * along with this program.  If not, see <http://www.gnu.org/licenses/>.
 */
package org.neo4j.kernel.api.index;

import org.junit.Ignore;
import org.junit.Test;

import static java.util.Arrays.asList;
import static org.hamcrest.Matchers.equalTo;
import static org.junit.Assert.assertThat;

@Ignore( "Not a test. This is a compatibility suite that provides test cases for verifying" +
        " SchemaIndexProvider implementations. Each index provider that is to be tested by this suite" +
        " must create their own test class extending IndexProviderCompatibilityTestSuite." +
        " The @Ignore annotation doesn't prevent these tests to run, it rather removes some annoying" +
        " errors or warnings in some IDEs about test classes needing a public zero-arg constructor." )
public class UniqueIndexAccessorCompatibility extends IndexAccessorCompatibility
{
    private static final int PROPERTY_KEY_ID = 100;

    public UniqueIndexAccessorCompatibility( IndexProviderCompatibilityTestSuite testSuite )
    {
        super( testSuite, true );
    }

    @Ignore( "Invalid assumption since we currently must rely on close throwing exception for injected"
            + "transactions that violate a constraint" )
    @Test
    public void closingAnOnlineIndexUpdaterMustNotThrowEvenIfItHasBeenFedConflictingData() throws Exception
    {
        // The reason is that we use and close IndexUpdaters in commit - not in prepare - and therefor
        // we cannot have them go around and throw exceptions, because that could potentially break
        // recovery.
        // Conflicting data can happen because of faulty data coercion. These faults are resolved by
        // the exact-match filtering we do on index lookups in StateHandlingStatementOperations.

        updateAndCommit( asList(
                NodePropertyUpdate.add( 1L, PROPERTY_KEY_ID, "a", new long[]{1000} ),
                NodePropertyUpdate.add( 2L, PROPERTY_KEY_ID, "a", new long[]{1000} ) ) );

        assertThat( getAllNodes( "a" ), equalTo( asList( 1L, 2L ) ) );
    }

    @Test
    public void testIndexSeekAndScan() throws Exception
    {
        updateAndCommit( asList(
                NodePropertyUpdate.add( 1L, PROPERTY_KEY_ID, "a", new long[]{1000} ),
                NodePropertyUpdate.add( 2L, PROPERTY_KEY_ID, "b", new long[]{1000} ),
                NodePropertyUpdate.add( 3L, PROPERTY_KEY_ID, "c", new long[]{1000} ) ) );

        assertThat( getAllNodes( "a" ), equalTo( asList( 1L ) ) );
        assertThat( getAllNodes(), equalTo( asList( 1L, 2L, 3L ) ) );
    }
}


File: community/kernel/src/test/java/org/neo4j/kernel/impl/api/index/inmemory/HashBasedIndex.java
/*
 * Copyright (c) 2002-2015 "Neo Technology,"
 * Network Engine for Objects in Lund AB [http://neotechnology.com]
 *
 * This file is part of Neo4j.
 *
 * Neo4j is free software: you can redistribute it and/or modify
 * it under the terms of the GNU General Public License as published by
 * the Free Software Foundation, either version 3 of the License, or
 * (at your option) any later version.
 *
 * This program is distributed in the hope that it will be useful,
 * but WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
 * GNU General Public License for more details.
 *
 * You should have received a copy of the GNU General Public License
 * along with this program.  If not, see <http://www.gnu.org/licenses/>.
 */
package org.neo4j.kernel.impl.api.index.inmemory;

import java.lang.reflect.Array;
import java.util.Collection;
import java.util.Collections;
import java.util.HashMap;
import java.util.HashSet;
import java.util.Iterator;
import java.util.Map;
import java.util.Set;

import org.neo4j.collection.primitive.PrimitiveLongCollections;
import org.neo4j.collection.primitive.PrimitiveLongIterator;
import org.neo4j.helpers.collection.Iterables;
import org.neo4j.kernel.api.exceptions.index.IndexNotFoundKernelException;

import static org.neo4j.collection.primitive.PrimitiveLongCollections.toPrimitiveIterator;
import static org.neo4j.register.Register.DoubleLong;

class HashBasedIndex extends InMemoryIndexImplementation
{
    private Map<Object, Set<Long>> data;

    public Map<Object, Set<Long>> data()
    {
        if ( data == null )
        {
            throw new IllegalStateException( "Index has not been created, or has been dropped." );
        }
        return data;
    }

    @Override
    public String toString()
    {
        return getClass().getSimpleName() + data;
    }

    @Override
    void initialize()
    {
        data = new HashMap<>();
    }

    @Override
    void drop()
    {
        data = null;
    }

    @Override
    PrimitiveLongIterator doLookup( Object propertyValue )
    {
        Set<Long> nodes = data().get( propertyValue );
        return nodes == null ? PrimitiveLongCollections.emptyIterator() : toPrimitiveIterator( nodes.iterator() );
    }

    @Override
    public PrimitiveLongIterator lookupByPrefixSearch( String prefix )
    {
        throw new UnsupportedOperationException();
    }

    @Override
    public PrimitiveLongIterator scan()
    {
        Iterable<Long> all = Iterables.flattenIterable( data.values() );
        return toPrimitiveIterator( all.iterator() );
    }

    @Override
    boolean doAdd( Object propertyValue, long nodeId, boolean applyIdempotently )
    {
        Set<Long> nodes = data().get( propertyValue );
        if ( nodes == null )
        {
            data().put( propertyValue, nodes = new HashSet<>() );
        }
        // In this implementation we don't care about idempotency.
        return nodes.add( nodeId );
    }

    @Override
    void doRemove( Object propertyValue, long nodeId )
    {
        Set<Long> nodes = data().get( propertyValue );
        if ( nodes != null )
        {
            nodes.remove( nodeId );
        }
    }

    @Override
    void remove( long nodeId )
    {
        for ( Set<Long> nodes : data().values() )
        {
            nodes.remove( nodeId );
        }
    }

    @Override
    void iterateAll( IndexEntryIterator iterator ) throws Exception
    {
        for ( Map.Entry<Object, Set<Long>> entry : data().entrySet() )
        {
            iterator.visitEntry( entry.getKey(), entry.getValue() );
        }
    }

    @Override
    public long maxCount()
    {
        return ids().size();
    }

    @Override
    public Iterator<Long> iterator()
    {
        return ids().iterator();
    }

    private Collection<Long> ids()
    {
        Set<Long> allIds = new HashSet<>();
        for ( Set<Long> someIds : data().values() )
        {
            allIds.addAll( someIds );
        }
        return allIds;
    }

    @Override
    InMemoryIndexImplementation snapshot()
    {
        HashBasedIndex snapshot = new HashBasedIndex();
        snapshot.initialize();
        for ( Map.Entry<Object, Set<Long>> entry : data().entrySet() )
        {
            snapshot.data().put( entry.getKey(), new HashSet<>( entry.getValue() ) );
        }
        return snapshot;
    }

    @Override
    public int getIndexedCount( long nodeId, Object propertyValue )
    {
        Set<Long> candidates = data().get( propertyValue );
        return candidates != null && candidates.contains( nodeId ) ? 1 : 0;
    }

    @Override
    public Set<Class> valueTypesInIndex()
    {
        if ( data == null )
        {
            return Collections.emptySet();
        }
        Set<Class> result = new HashSet<>();
        for ( Object value : data.keySet() )
        {
            if ( value instanceof Number )
            {
                result.add( Number.class );
            }
            else if ( value instanceof String )
            {
                result.add( String.class );
            }
            else if ( value instanceof Boolean )
            {
                result.add( Boolean.class );
            }
            else if ( value instanceof ArrayKey )
            {
                result.add( Array.class );
            }
        }
        return result;
    }

    @Override
    public long sampleIndex( final DoubleLong.Out result ) throws IndexNotFoundKernelException
    {
        if ( data == null )
        {
            throw new IndexNotFoundKernelException( "Index dropped while sampling." );
        }
        final long[] uniqueAndSize = {0, 0};
        try
        {
            iterateAll( new IndexEntryIterator()
            {
                @Override
                public void visitEntry( Object value, Set<Long> nodeIds ) throws Exception
                {
                    int ids = nodeIds.size();
                    if ( ids > 0 )
                    {
                        uniqueAndSize[0] += 1;
                        uniqueAndSize[1] += ids;
                    }
                }
            });
        }
        catch ( Exception ex )
        {
            throw new RuntimeException( ex );
        }

        result.write( uniqueAndSize[0], uniqueAndSize[1] );
        return uniqueAndSize[1];
    }
}


File: community/lucene-index/src/main/java/org/neo4j/kernel/api/impl/index/DeferredConstraintVerificationUniqueLuceneIndexPopulator.java
/*
 * Copyright (c) 2002-2015 "Neo Technology,"
 * Network Engine for Objects in Lund AB [http://neotechnology.com]
 *
 * This file is part of Neo4j.
 *
 * Neo4j is free software: you can redistribute it and/or modify
 * it under the terms of the GNU General Public License as published by
 * the Free Software Foundation, either version 3 of the License, or
 * (at your option) any later version.
 *
 * This program is distributed in the hope that it will be useful,
 * but WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
 * GNU General Public License for more details.
 *
 * You should have received a copy of the GNU General Public License
 * along with this program.  If not, see <http://www.gnu.org/licenses/>.
 */
package org.neo4j.kernel.api.impl.index;

import org.apache.lucene.document.Document;
import org.apache.lucene.document.Fieldable;
import org.apache.lucene.index.IndexReader;
import org.apache.lucene.index.Term;
import org.apache.lucene.index.TermEnum;
import org.apache.lucene.search.Collector;
import org.apache.lucene.search.IndexSearcher;
import org.apache.lucene.search.Query;
import org.apache.lucene.search.ReferenceManager;
import org.apache.lucene.search.Scorer;
import org.apache.lucene.search.TermQuery;

import java.io.File;
import java.io.IOException;
import java.util.ArrayList;
import java.util.List;

import org.neo4j.collection.primitive.PrimitiveLongSet;
import org.neo4j.helpers.ThisShouldNotHappenError;
import org.neo4j.kernel.api.StatementConstants;
import org.neo4j.kernel.api.exceptions.KernelException;
import org.neo4j.kernel.api.exceptions.index.IndexCapacityExceededException;
import org.neo4j.kernel.api.index.IndexDescriptor;
import org.neo4j.kernel.api.index.IndexEntryConflictException;
import org.neo4j.kernel.api.index.IndexUpdater;
import org.neo4j.kernel.api.index.NodePropertyUpdate;
import org.neo4j.kernel.api.index.PreexistingIndexEntryConflictException;
import org.neo4j.kernel.api.index.PropertyAccessor;
import org.neo4j.kernel.api.index.Reservation;
import org.neo4j.kernel.api.index.util.FailureStorage;
import org.neo4j.kernel.api.properties.Property;
import org.neo4j.kernel.impl.api.index.sampling.UniqueIndexSampler;
import org.neo4j.register.Register.DoubleLong;

import static org.neo4j.kernel.api.impl.index.LuceneDocumentStructure.NODE_ID_KEY;

class DeferredConstraintVerificationUniqueLuceneIndexPopulator extends LuceneIndexPopulator
{
    private final IndexDescriptor descriptor;
    private final UniqueIndexSampler sampler;

    private final SearcherManagerFactory searcherManagerFactory;
    private ReferenceManager<IndexSearcher> searcherManager;

    DeferredConstraintVerificationUniqueLuceneIndexPopulator( LuceneDocumentStructure documentStructure,
                                                              IndexWriterFactory<LuceneIndexWriter> writers,
                                                              SearcherManagerFactory searcherManagerFactory,
                                                              DirectoryFactory dirFactory, File dirFile,
                                                              FailureStorage failureStorage, long indexId,
                                                              IndexDescriptor descriptor )
    {
        super( documentStructure, writers, dirFactory, dirFile, failureStorage, indexId );
        this.descriptor = descriptor;
        this.sampler = new UniqueIndexSampler();
        this.searcherManagerFactory = searcherManagerFactory;
    }

    @Override
    public void create() throws IOException
    {
        super.create();
        searcherManager = searcherManagerFactory.create( writer );
    }

    @Override
    public void drop() throws IOException
    {
        try
        {
            if ( searcherManager != null )
            {
                searcherManager.close();
            }
        }
        finally
        {
            super.drop();
        }
    }

    @Override
    protected void flush() throws IOException
    {
        // no need to do anything yet.
    }

    @Override
    public void add( long nodeId, Object propertyValue )
            throws IndexEntryConflictException, IOException, IndexCapacityExceededException
    {
        sampler.increment( 1 );
        Fieldable encodedValue = documentStructure.encodeAsFieldable( propertyValue );
        Document doc = documentStructure.newDocumentRepresentingProperty( nodeId, encodedValue );
        writer.addDocument( doc );
    }

    @Override
    public void verifyDeferredConstraints( PropertyAccessor accessor ) throws IndexEntryConflictException, IOException
    {
        searcherManager.maybeRefresh();
        IndexSearcher searcher = searcherManager.acquire();

        try
        {
            DuplicateCheckingCollector collector = duplicateCheckingCollector( accessor );
            TermEnum terms = searcher.getIndexReader().terms();
            while ( terms.next() )
            {
                Term term = terms.term();

                if ( !NODE_ID_KEY.equals( term.field() ) && terms.docFreq() > 1 )
                {
                    collector.reset();
                    searcher.search( new TermQuery( term ), collector );
                }
            }
        }
        catch ( IOException e )
        {
            Throwable cause = e.getCause();
            if ( cause instanceof IndexEntryConflictException )
            {
                throw (IndexEntryConflictException) cause;
            }
            throw e;
        }
        finally
        {
            searcherManager.release( searcher );
        }
    }

    private DuplicateCheckingCollector duplicateCheckingCollector( PropertyAccessor accessor )
    {
        return new DuplicateCheckingCollector( accessor, documentStructure, descriptor.getPropertyKeyId() );
    }

    @Override
    public IndexUpdater newPopulatingUpdater( final PropertyAccessor accessor ) throws IOException
    {
        return new IndexUpdater()
        {
            List<Object> updatedPropertyValues = new ArrayList<>();

            @Override
            public Reservation validate( Iterable<NodePropertyUpdate> updates ) throws IOException
            {
                return Reservation.EMPTY;
            }

            @Override
            public void process( NodePropertyUpdate update )
                    throws IOException, IndexEntryConflictException, IndexCapacityExceededException
            {
                long nodeId = update.getNodeId();
                switch ( update.getUpdateMode() )
                {
                    case ADDED:
                        sampler.increment( 1 ); // add new value

                        // We don't look at the "before" value, so adding and changing idempotently is done the same way.
                        Fieldable encodedValue = documentStructure.encodeAsFieldable( update.getValueAfter() );
                        writer.updateDocument( documentStructure.newQueryForChangeOrRemove( nodeId ),
                                documentStructure.newDocumentRepresentingProperty( nodeId, encodedValue ) );
                        updatedPropertyValues.add( update.getValueAfter() );
                        break;
                    case CHANGED:
                        // do nothing on the sampler, since it would be something like:
                        // sampler.increment( -1 ); // remove old vale
                        // sampler.increment( 1 ); // add new value

                        // We don't look at the "before" value, so adding and changing idempotently is done the same way.
                        Fieldable encodedValueAfter = documentStructure.encodeAsFieldable( update.getValueAfter() );
                        writer.updateDocument( documentStructure.newQueryForChangeOrRemove( nodeId ),
                                documentStructure.newDocumentRepresentingProperty( nodeId, encodedValueAfter ) );
                        updatedPropertyValues.add( update.getValueAfter() );
                        break;
                    case REMOVED:
                        sampler.increment( -1 ); // remove old value
                        writer.deleteDocuments( documentStructure.newQueryForChangeOrRemove( nodeId ) );
                        break;
                    default:
                        throw new IllegalStateException( "Unknown update mode " + update.getUpdateMode() );
                }
            }

            @Override
            public void close() throws IOException, IndexEntryConflictException
            {
                searcherManager.maybeRefresh();
                IndexSearcher searcher = searcherManager.acquire();
                try
                {
                    DuplicateCheckingCollector collector = duplicateCheckingCollector( accessor );
                    for ( Object propertyValue : updatedPropertyValues )
                    {
                        collector.reset();
                        Query query = documentStructure.newQuery( propertyValue );
                        searcher.search( query, collector );
                    }
                }
                catch ( IOException e )
                {
                    Throwable cause = e.getCause();
                    if ( cause instanceof IndexEntryConflictException )
                    {
                        throw (IndexEntryConflictException) cause;
                    }
                    throw e;
                }
                finally
                {
                    searcherManager.release( searcher );
                }
            }

            @Override
            public void remove( PrimitiveLongSet nodeIds )
            {
                throw new UnsupportedOperationException( "should not remove() from populating index" );
            }
        };
    }

    @Override
    public long sampleResult( DoubleLong.Out result )
    {
        return sampler.result( result );
    }

    @Override
    public void close( boolean populationCompletedSuccessfully ) throws IOException, IndexCapacityExceededException
    {
        try
        {
            searcherManager.close();
        }
        finally
        {
            super.close( populationCompletedSuccessfully );
        }
    }

    private static class DuplicateCheckingCollector extends Collector
    {
        private final PropertyAccessor accessor;
        private final LuceneDocumentStructure documentStructure;
        private final int propertyKeyId;
        private final EntrySet actualValues;
        private IndexReader reader;
        private int docBase;

        public DuplicateCheckingCollector(
                PropertyAccessor accessor,
                LuceneDocumentStructure documentStructure,
                int propertyKeyId )
        {
            this.accessor = accessor;
            this.documentStructure = documentStructure;
            this.propertyKeyId = propertyKeyId;
            actualValues = new EntrySet();
        }

        @Override
        public void setScorer( Scorer scorer ) throws IOException
        {
        }

        @Override
        public void collect( int doc ) throws IOException
        {
            try
            {
                doCollect( doc );
            }
            catch ( KernelException e )
            {
                throw new ThisShouldNotHappenError(
                        "Chris", "Indexed node should exist and have the indexed property.", e );
            }
            catch ( PreexistingIndexEntryConflictException e )
            {
                throw new IOException( e );
            }
        }

        private void doCollect( int doc ) throws IOException, KernelException, PreexistingIndexEntryConflictException
        {
            Document document = reader.document( doc );
            long nodeId = documentStructure.getNodeId( document );
            Property property = accessor.getProperty( nodeId, propertyKeyId );

            // We either have to find the first conflicting entry set element,
            // or append one for the property we just fetched:
            EntrySet current = actualValues;
            scan:do {
                for ( int i = 0; i < EntrySet.INCREMENT; i++ )
                {
                    Object value = current.value[i];

                    if ( current.nodeId[i] == StatementConstants.NO_SUCH_NODE )
                    {
                        current.value[i] = property.value();
                        current.nodeId[i] = nodeId;
                        if ( i == EntrySet.INCREMENT - 1 )
                        {
                            current.next = new EntrySet();
                        }
                        break scan;
                    }
                    else if ( property.valueEquals( value ) )
                    {
                        throw new PreexistingIndexEntryConflictException(
                                value, current.nodeId[i], nodeId );
                    }
                }
                current = current.next;
            } while ( current != null );
        }

        @Override
        public void setNextReader( IndexReader reader, int docBase ) throws IOException
        {
            this.reader = reader;
            this.docBase = docBase;
        }

        @Override
        public boolean acceptsDocsOutOfOrder()
        {
            return true;
        }

        public void reset()
        {
            actualValues.reset(); // TODO benchmark this vs. not clearing and instead creating a new object, perhaps
        }
    }

    /**
     * A small struct of arrays of nodeId + property value pairs, with a next pointer.
     * Should exhibit fairly fast linear iteration, small memory overhead and dynamic growth.
     *
     * NOTE: Must always call reset() before use!
     */
    private static class EntrySet
    {
        static final int INCREMENT = 100;

        Object[] value = new Object[INCREMENT];
        long[] nodeId = new long[INCREMENT];
        EntrySet next;

        public void reset()
        {
            EntrySet current = this;
            do {
                for (int i = 0; i < INCREMENT; i++)
                {
                    current.value[i] = null;
                    current.nodeId[i] = StatementConstants.NO_SUCH_NODE;
                }
                current = next;
            } while ( current != null );
        }
    }
}


File: community/lucene-index/src/main/java/org/neo4j/kernel/api/impl/index/LuceneDocumentStructure.java
/*
 * Copyright (c) 2002-2015 "Neo Technology,"
 * Network Engine for Objects in Lund AB [http://neotechnology.com]
 *
 * This file is part of Neo4j.
 *
 * Neo4j is free software: you can redistribute it and/or modify
 * it under the terms of the GNU General Public License as published by
 * the Free Software Foundation, either version 3 of the License, or
 * (at your option) any later version.
 *
 * This program is distributed in the hope that it will be useful,
 * but WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
 * GNU General Public License for more details.
 *
 * You should have received a copy of the GNU General Public License
 * along with this program.  If not, see <http://www.gnu.org/licenses/>.
 */
package org.neo4j.kernel.api.impl.index;

import org.apache.lucene.document.Document;
import org.apache.lucene.document.Field;
import org.apache.lucene.document.Fieldable;
import org.apache.lucene.index.FieldInfo.IndexOptions;
import org.apache.lucene.index.Term;
import org.apache.lucene.search.MatchAllDocsQuery;
import org.apache.lucene.search.Query;
import org.apache.lucene.search.TermQuery;
import org.apache.lucene.util.NumericUtils;

import org.neo4j.kernel.api.index.ArrayEncoder;

import static java.lang.String.format;
import static org.apache.lucene.document.Field.Index.NOT_ANALYZED;
import static org.apache.lucene.document.Field.Store.NO;
import static org.apache.lucene.document.Field.Store.YES;

public class LuceneDocumentStructure
{
    static final String NODE_ID_KEY = "id";

    Document newDocument( long nodeId )
    {
        Document document = new Document();
        document.add( field( NODE_ID_KEY, "" + nodeId, YES ) );
        return document;
    }

    enum ValueEncoding
    {
        Number
        {
            @Override
            String key()
            {
                return "number";
            }

            @Override
            boolean canEncode( Object value )
            {
                return value instanceof Number;
            }

            @Override
            Fieldable encodeField( Object value )
            {
                String encodedString = NumericUtils.doubleToPrefixCoded( ((Number)value).doubleValue() );
                return field( key(), encodedString );
            }

            @Override
            Query encodeQuery( Object value )
            {
                String encodedString = NumericUtils.doubleToPrefixCoded( ((Number)value).doubleValue() );
                return new TermQuery( new Term( key(), encodedString ) );
            }
        },
        Array
        {
            @Override
            String key()
            {
                return "array";
            }

            @Override
            boolean canEncode( Object value )
            {
                return value.getClass().isArray();
            }

            @Override
            Fieldable encodeField( Object value )
            {
                return field( key(), ArrayEncoder.encode( value ) );
            }

            @Override
            Query encodeQuery( Object value )
            {
                return new TermQuery( new Term( key(), ArrayEncoder.encode( value ) ) );
            }
        },
        Bool
        {
            @Override
            String key()
            {
                return "bool";
            }

            @Override
            boolean canEncode( Object value )
            {
                return value instanceof Boolean;
            }

            @Override
            Fieldable encodeField( Object value )
            {
                return field( key(), value.toString() );
            }

            @Override
            Query encodeQuery( Object value )
            {
                return new TermQuery( new Term( key(), value.toString() ) );
            }
        },
        String
        {
            @Override
            String key()
            {
                return "string";
            }

            @Override
            boolean canEncode( Object value )
            {
                // Any other type can be safely serialised as a string
                return true;
            }

            @Override
            Fieldable encodeField( Object value )
            {
                return field( key(), value.toString() );
            }

            @Override
            Query encodeQuery( Object value )
            {
                return new TermQuery( new Term( key(), value.toString() ) );
            }
        };

        abstract String key();

        abstract boolean canEncode( Object value );
        abstract Fieldable encodeField( Object value );
        abstract Query encodeQuery( Object value );

        public static ValueEncoding fromKey( String key )
        {
            switch ( key )
            {
            case "number":
                return Number;
            case "array":
                return Array;
            case "bool":
                return Bool;
            case "string":
                return String;
            }
            throw new IllegalArgumentException( "Unknown key: " + key );
        }
    }

    public Document newDocumentRepresentingProperty( long nodeId, Fieldable encodedValue )
    {
        Document document = newDocument( nodeId );
        document.add( encodedValue );
        return document;
    }

    public Fieldable encodeAsFieldable( Object value )
    {
        for ( ValueEncoding encoding : ValueEncoding.values() )
        {
            if ( encoding.canEncode( value ) )
            {
                return encoding.encodeField( value );
            }
        }

        throw new IllegalStateException( "Unable to encode the value " + value );
    }

    private static Field field( String fieldIdentifier, String value )
    {
        return field( fieldIdentifier, value, NO );
    }

    private static Field field( String fieldIdentifier, String value, Field.Store store )
    {
        Field result = new Field( fieldIdentifier, value, store, NOT_ANALYZED );
        result.setOmitNorms( true );
        result.setIndexOptions( IndexOptions.DOCS_ONLY );
        return result;
    }

    public Query newMatchAllQuery()
    {
        return new MatchAllDocsQuery();
    }

    public Query newQuery( Object value )
    {
        for ( ValueEncoding encoding : ValueEncoding.values() )
        {
            if ( encoding.canEncode( value ) )
            {
                return encoding.encodeQuery( value );
            }
        }
        throw new IllegalArgumentException( format( "Unable to create newQuery for %s", value ) );
    }

    public Term newQueryForChangeOrRemove( long nodeId )
    {
        return new Term( NODE_ID_KEY, "" + nodeId );
    }

    public long getNodeId( Document from )
    {
        return Long.parseLong( from.get( NODE_ID_KEY ) );
    }
}


File: community/lucene-index/src/main/java/org/neo4j/kernel/api/impl/index/LuceneIndexAccessor.java
/*
 * Copyright (c) 2002-2015 "Neo Technology,"
 * Network Engine for Objects in Lund AB [http://neotechnology.com]
 *
 * This file is part of Neo4j.
 *
 * Neo4j is free software: you can redistribute it and/or modify
 * it under the terms of the GNU General Public License as published by
 * the Free Software Foundation, either version 3 of the License, or
 * (at your option) any later version.
 *
 * This program is distributed in the hope that it will be useful,
 * but WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
 * GNU General Public License for more details.
 *
 * You should have received a copy of the GNU General Public License
 * along with this program.  If not, see <http://www.gnu.org/licenses/>.
 */
package org.neo4j.kernel.api.impl.index;

import org.apache.lucene.document.Fieldable;
import org.apache.lucene.search.IndexSearcher;
import org.apache.lucene.search.ReferenceManager;
import org.apache.lucene.store.Directory;

import java.io.Closeable;
import java.io.File;
import java.io.IOException;
import java.util.concurrent.TimeUnit;

import org.neo4j.collection.primitive.PrimitiveLongSet;
import org.neo4j.collection.primitive.PrimitiveLongVisitor;
import org.neo4j.graphdb.ResourceIterator;
import org.neo4j.helpers.CancellationRequest;
import org.neo4j.helpers.TaskControl;
import org.neo4j.helpers.TaskCoordinator;
import org.neo4j.helpers.ThisShouldNotHappenError;
import org.neo4j.kernel.api.direct.BoundedIterable;
import org.neo4j.kernel.api.exceptions.index.IndexCapacityExceededException;
import org.neo4j.kernel.api.index.IndexAccessor;
import org.neo4j.kernel.api.index.IndexEntryConflictException;
import org.neo4j.kernel.api.index.IndexReader;
import org.neo4j.kernel.api.index.IndexUpdater;
import org.neo4j.kernel.api.index.NodePropertyUpdate;
import org.neo4j.kernel.api.index.Reservation;
import org.neo4j.kernel.impl.api.index.IndexUpdateMode;
import org.neo4j.kernel.impl.api.index.UpdateMode;

import static org.neo4j.kernel.api.impl.index.DirectorySupport.deleteDirectoryContents;

abstract class LuceneIndexAccessor implements IndexAccessor
{
    protected final LuceneDocumentStructure documentStructure;
    protected final ReferenceManager<IndexSearcher> searcherManager;
    protected final ReservingLuceneIndexWriter writer;

    private final Directory dir;
    private final File dirFile;
    private final int bufferSizeLimit;
    private final TaskCoordinator taskCoordinator = new TaskCoordinator( 10, TimeUnit.MILLISECONDS );

    private final PrimitiveLongVisitor<IOException> removeFromLucene = new PrimitiveLongVisitor<IOException>()
    {
        @Override
        public boolean visited( long nodeId ) throws IOException
        {
            LuceneIndexAccessor.this.remove( nodeId );
            return false;
        }
    };


    LuceneIndexAccessor( LuceneDocumentStructure documentStructure,
                         IndexWriterFactory<ReservingLuceneIndexWriter> indexWriterFactory,
                         DirectoryFactory dirFactory, File dirFile, int bufferSizeLimit ) throws IOException
    {
        this.documentStructure = documentStructure;
        this.dirFile = dirFile;
        this.bufferSizeLimit = bufferSizeLimit;
        this.dir = dirFactory.open( dirFile );
        this.writer = indexWriterFactory.create( dir );
        this.searcherManager = writer.createSearcherManager();
    }

    @Override
    public IndexUpdater newUpdater( IndexUpdateMode mode )
    {
        switch ( mode )
        {
            case ONLINE:
                return new LuceneIndexUpdater( false );

            case RECOVERY:
                return new LuceneIndexUpdater( true );

            default:
                throw new ThisShouldNotHappenError( "Stefan", "Unsupported update mode" );
        }
    }

    @Override
    public void drop() throws IOException
    {
        taskCoordinator.cancel();
        closeIndexResources();
        try
        {
            taskCoordinator.awaitCompletion();
        }
        catch ( InterruptedException e )
        {
            throw new IOException( "Interrupted while waiting for concurrent tasks to complete.", e );
        }
        deleteDirectoryContents( dir );
    }

    @Override
    public void force() throws IOException
    {
        writer.commitAsOnline();
        searcherManager.maybeRefresh();
    }

    @Override
    public void close() throws IOException
    {
        closeIndexResources();
        dir.close();
    }

    private void closeIndexResources() throws IOException
    {
        writer.close();
        searcherManager.close();
    }

    @Override
    public IndexReader newReader()
    {
        final IndexSearcher searcher = searcherManager.acquire();
        final TaskControl token = taskCoordinator.newInstance();
        final Closeable closeable = new Closeable()
        {
            @Override
            public void close() throws IOException
            {
                searcherManager.release( searcher );
                token.close();
            }
        };
        return makeNewReader( searcher, closeable, token );
    }

    protected IndexReader makeNewReader( IndexSearcher searcher, Closeable closeable, CancellationRequest cancellation )
    {
        return new LuceneIndexAccessorReader( searcher, documentStructure, closeable, cancellation, bufferSizeLimit );
    }

    @Override
    public BoundedIterable<Long> newAllEntriesReader()
    {
        return new LuceneAllEntriesIndexAccessorReader( new LuceneAllDocumentsReader( searcherManager ), documentStructure );
    }

    @Override
    public ResourceIterator<File> snapshotFiles() throws IOException
    {
        return new LuceneSnapshotter().snapshot( this.dirFile, writer );
    }

    private void addRecovered( long nodeId, Object value ) throws IOException, IndexCapacityExceededException
    {
        Fieldable encodedValue = documentStructure.encodeAsFieldable( value );
        writer.updateDocument( documentStructure.newQueryForChangeOrRemove( nodeId ),
                documentStructure.newDocumentRepresentingProperty( nodeId, encodedValue ) );
    }

    protected void add( long nodeId, Object value ) throws IOException, IndexCapacityExceededException
    {
        Fieldable encodedValue = documentStructure.encodeAsFieldable( value );
        writer.addDocument( documentStructure.newDocumentRepresentingProperty( nodeId, encodedValue ) );
    }

    protected void change( long nodeId, Object value ) throws IOException, IndexCapacityExceededException
    {
        Fieldable encodedValue = documentStructure.encodeAsFieldable( value );
        writer.updateDocument( documentStructure.newQueryForChangeOrRemove( nodeId ),
                documentStructure.newDocumentRepresentingProperty( nodeId, encodedValue ) );
    }

    protected void remove( long nodeId ) throws IOException
    {
        writer.deleteDocuments( documentStructure.newQueryForChangeOrRemove( nodeId ) );
    }

    // This method should be synchronized because we need every thread to perform actual refresh
    // and not just skip it because some other refresh is in progress
    private synchronized void refreshSearcherManager() throws IOException
    {
        searcherManager.maybeRefresh();
    }

    private class LuceneIndexUpdater implements IndexUpdater
    {
        private final boolean inRecovery;

        private LuceneIndexUpdater( boolean inRecovery )
        {
            this.inRecovery = inRecovery;
        }

        @Override
        public Reservation validate( Iterable<NodePropertyUpdate> updates )
                throws IOException, IndexCapacityExceededException
        {
            int insertionsCount = 0;
            for ( NodePropertyUpdate update : updates )
            {
                // Only count additions and updates, since removals will not affect the size of the index
                // until it is merged. Each update is in fact atomic (delete + add).
                if ( update.getUpdateMode() == UpdateMode.ADDED || update.getUpdateMode() == UpdateMode.CHANGED )
                {
                    insertionsCount++;
                }
            }

            writer.reserveInsertions( insertionsCount );

            final int insertions = insertionsCount;
            return new Reservation()
            {
                boolean released;

                @Override
                public void release()
                {
                    if ( released )
                    {
                        throw new IllegalStateException( "Reservation was already released. " +
                                                         "Previously reserved " + insertions + " insertions" );
                    }
                    writer.removeReservedInsertions( insertions );
                    released = true;
                }
            };
        }

        @Override
        public void process( NodePropertyUpdate update ) throws IOException, IndexCapacityExceededException
        {
            switch ( update.getUpdateMode() )
            {
                case ADDED:
                    if ( inRecovery )
                    {
                        addRecovered( update.getNodeId(), update.getValueAfter() );
                    }
                    else
                    {
                        add( update.getNodeId(), update.getValueAfter() );
                    }
                    break;
                case CHANGED:
                    change( update.getNodeId(), update.getValueAfter() );
                    break;
                case REMOVED:
                    LuceneIndexAccessor.this.remove( update.getNodeId() );
                    break;
                default:
                    throw new UnsupportedOperationException();
            }
        }

        @Override
        public void close() throws IOException, IndexEntryConflictException
        {
            if ( !inRecovery )
            {
                refreshSearcherManager();
            }
        }

        @Override
        public void remove( PrimitiveLongSet nodeIds ) throws IOException
        {
            nodeIds.visitKeys( removeFromLucene );
        }
    }
}



File: community/lucene-index/src/main/java/org/neo4j/kernel/api/impl/index/LuceneIndexAccessorReader.java
/*
 * Copyright (c) 2002-2015 "Neo Technology,"
 * Network Engine for Objects in Lund AB [http://neotechnology.com]
 *
 * This file is part of Neo4j.
 *
 * Neo4j is free software: you can redistribute it and/or modify
 * it under the terms of the GNU General Public License as published by
 * the Free Software Foundation, either version 3 of the License, or
 * (at your option) any later version.
 *
 * This program is distributed in the hope that it will be useful,
 * but WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
 * GNU General Public License for more details.
 *
 * You should have received a copy of the GNU General Public License
 * along with this program.  If not, see <http://www.gnu.org/licenses/>.
 */
package org.neo4j.kernel.api.impl.index;

import org.apache.lucene.index.Term;
import org.apache.lucene.index.TermEnum;
import org.apache.lucene.search.BooleanClause;
import org.apache.lucene.search.BooleanQuery;
import org.apache.lucene.search.IndexSearcher;
import org.apache.lucene.search.Query;
import org.apache.lucene.search.TermQuery;

import java.io.Closeable;
import java.io.IOException;
import java.lang.reflect.Array;
import java.util.HashSet;
import java.util.Set;

import org.neo4j.collection.primitive.PrimitiveLongIterator;
import org.neo4j.helpers.CancellationRequest;
import org.neo4j.index.impl.lucene.Hits;
import org.neo4j.kernel.api.exceptions.index.IndexNotFoundKernelException;
import org.neo4j.kernel.api.index.IndexReader;
import org.neo4j.kernel.impl.api.index.sampling.NonUniqueIndexSampler;

import static org.neo4j.kernel.api.impl.index.LuceneDocumentStructure.*;
import static org.neo4j.kernel.api.impl.index.LuceneDocumentStructure.NODE_ID_KEY;
import static org.neo4j.register.Register.DoubleLong;

class LuceneIndexAccessorReader implements IndexReader
{
    private final IndexSearcher searcher;
    private final LuceneDocumentStructure documentLogic;
    private final Closeable onClose;
    private final CancellationRequest cancellation;
    private final int bufferSizeLimit;

    LuceneIndexAccessorReader( IndexSearcher searcher, LuceneDocumentStructure documentLogic, Closeable onClose,
                               CancellationRequest cancellation, int bufferSizeLimit )
    {
        this.searcher = searcher;
        this.documentLogic = documentLogic;
        this.onClose = onClose;
        this.cancellation = cancellation;
        this.bufferSizeLimit = bufferSizeLimit;
    }

    @Override
    public long sampleIndex( DoubleLong.Out result ) throws IndexNotFoundKernelException
    {
        NonUniqueIndexSampler sampler = new NonUniqueIndexSampler( bufferSizeLimit );
        try ( TermEnum terms = luceneIndexReader().terms() )
        {
            while ( terms.next() )
            {
                Term term = terms.term();
                if ( !NODE_ID_KEY.equals( term.field() ))
                {
                    String value = term.text();
                    sampler.include( value );
                }
                checkCancellation();
            }
        }
        catch ( IOException e )
        {
            throw new RuntimeException( e );
        }

        return sampler.result( result );
    }

    @Override
    public PrimitiveLongIterator lookup( Object value )
    {
        try
        {
            Hits hits = new Hits( searcher, documentLogic.newQuery( value ), null );
            return new HitsPrimitiveLongIterator( hits, documentLogic );
        }
        catch ( IOException e )
        {
            throw new RuntimeException( e );
        }
    }

    @Override
    public PrimitiveLongIterator lookupByPrefixSearch( String prefix )
    {
        throw new UnsupportedOperationException();
    }

    @Override
    public PrimitiveLongIterator scan()
    {
        try
        {
            Hits hits = new Hits( searcher, documentLogic.newMatchAllQuery(), null );
            return new HitsPrimitiveLongIterator( hits, documentLogic );
        }
        catch ( IOException e )
        {
            throw new RuntimeException( e );
        }
    }

    @Override
    public int getIndexedCount( long nodeId, Object propertyValue )
    {
        Query nodeIdQuery = new TermQuery( documentLogic.newQueryForChangeOrRemove( nodeId ) );
        Query valueQuery = documentLogic.newQuery( propertyValue );
        BooleanQuery nodeIdAndValueQuery = new BooleanQuery( true );
        nodeIdAndValueQuery.add( nodeIdQuery, BooleanClause.Occur.MUST );
        nodeIdAndValueQuery.add( valueQuery, BooleanClause.Occur.MUST );
        try
        {
            Hits hits = new Hits( searcher, nodeIdAndValueQuery, null );
            // A <label,propertyKeyId,nodeId> tuple should only match at most a single propertyValue
            return hits.length();
        }
        catch ( IOException e )
        {
            throw new RuntimeException( e );
        }
    }

    @Override
    public Set<Class> valueTypesInIndex()
    {
        Set<Class> types = new HashSet<>();
        try ( TermEnum terms = luceneIndexReader().terms() )
        {
            while ( terms.next() )
            {
                String field = terms.term().field();
                if ( !NODE_ID_KEY.equals( field ) )
                {
                    switch ( ValueEncoding.fromKey( field ) )
                    {
                    case Number:
                        types.add( Number.class );
                        break;
                    case String:
                        types.add( String.class );
                        break;
                    case Array:
                        types.add( Array.class );
                        break;
                    case Bool:
                        types.add( Boolean.class );
                        break;
                    }
                }
            }

        }
        catch ( IOException ex )
        {
            throw new RuntimeException( ex );
        }
        return types;
    }

    @Override
    public void close()
    {
        try
        {
            onClose.close();
        }
        catch ( IOException e )
        {
            throw new RuntimeException( e );
        }
    }

    protected void checkCancellation() throws IndexNotFoundKernelException
    {
        if ( cancellation.cancellationRequested() )
        {
            throw new IndexNotFoundKernelException( "Index dropped while sampling." );
        }
    }

    protected org.apache.lucene.index.IndexReader luceneIndexReader()
    {
        return searcher.getIndexReader();
    }
}


File: community/lucene-index/src/main/java/org/neo4j/kernel/api/impl/index/NonUniqueLuceneIndexPopulator.java
/*
 * Copyright (c) 2002-2015 "Neo Technology,"
 * Network Engine for Objects in Lund AB [http://neotechnology.com]
 *
 * This file is part of Neo4j.
 *
 * Neo4j is free software: you can redistribute it and/or modify
 * it under the terms of the GNU General Public License as published by
 * the Free Software Foundation, either version 3 of the License, or
 * (at your option) any later version.
 *
 * This program is distributed in the hope that it will be useful,
 * but WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
 * GNU General Public License for more details.
 *
 * You should have received a copy of the GNU General Public License
 * along with this program.  If not, see <http://www.gnu.org/licenses/>.
 */
package org.neo4j.kernel.api.impl.index;

import org.apache.lucene.document.Fieldable;

import java.io.File;
import java.io.IOException;
import java.util.ArrayList;
import java.util.List;

import org.neo4j.collection.primitive.PrimitiveLongSet;
import org.neo4j.kernel.api.exceptions.index.IndexCapacityExceededException;
import org.neo4j.kernel.api.index.IndexEntryConflictException;
import org.neo4j.kernel.api.index.IndexUpdater;
import org.neo4j.kernel.api.index.NodePropertyUpdate;
import org.neo4j.kernel.api.index.PropertyAccessor;
import org.neo4j.kernel.api.index.Reservation;
import org.neo4j.kernel.api.index.util.FailureStorage;
import org.neo4j.kernel.impl.api.index.sampling.IndexSamplingConfig;
import org.neo4j.kernel.impl.api.index.sampling.NonUniqueIndexSampler;
import org.neo4j.register.Register;

class NonUniqueLuceneIndexPopulator extends LuceneIndexPopulator
{
    static final int DEFAULT_QUEUE_THRESHOLD = 10000;
    private final int queueThreshold;
    private final NonUniqueIndexSampler sampler;
    private final List<NodePropertyUpdate> updates = new ArrayList<>();

    NonUniqueLuceneIndexPopulator( int queueThreshold, LuceneDocumentStructure documentStructure,
                                   IndexWriterFactory<LuceneIndexWriter> indexWriterFactory,
                                   DirectoryFactory dirFactory, File dirFile, FailureStorage failureStorage,
                                   long indexId, IndexSamplingConfig samplingConfig )
    {
        super( documentStructure, indexWriterFactory, dirFactory, dirFile, failureStorage, indexId );
        this.queueThreshold = queueThreshold;
        this.sampler = new NonUniqueIndexSampler( samplingConfig.bufferSize() );
    }

    @Override
    public void add( long nodeId, Object propertyValue ) throws IOException, IndexCapacityExceededException
    {
        Fieldable encodedValue = documentStructure.encodeAsFieldable( propertyValue );
        sampler.include( encodedValue.stringValue() );
        writer.addDocument( documentStructure.newDocumentRepresentingProperty( nodeId, encodedValue ) );
    }

    @Override
    public void verifyDeferredConstraints( PropertyAccessor accessor ) throws IndexEntryConflictException, IOException
    {
        // no constraints to verify so do nothing
    }

    @Override
    public IndexUpdater newPopulatingUpdater( PropertyAccessor propertyAccessor ) throws IOException
    {
        return new IndexUpdater()
        {
            @Override
            public Reservation validate( Iterable<NodePropertyUpdate> updates ) throws IOException
            {
                return Reservation.EMPTY;
            }

            @Override
            public void process( NodePropertyUpdate update ) throws IOException, IndexEntryConflictException
            {
                switch ( update.getUpdateMode() )
                {
                    case ADDED:
                        // We don't look at the "before" value, so adding and changing idempotently is done the same way.
                        Fieldable encodedValue = documentStructure.encodeAsFieldable( update.getValueAfter() );
                        sampler.include( encodedValue.stringValue() );
                        break;
                    case CHANGED:
                        // We don't look at the "before" value, so adding and changing idempotently is done the same way.
                        Fieldable encodedValueBefore = documentStructure.encodeAsFieldable( update.getValueBefore() );
                        sampler.exclude( encodedValueBefore.stringValue() );
                        Fieldable encodedValueAfter = documentStructure.encodeAsFieldable( update.getValueAfter() );
                        sampler.include( encodedValueAfter.stringValue() );
                        break;
                    case REMOVED:
                        Fieldable removedValue = documentStructure.encodeAsFieldable( update.getValueBefore() );
                        sampler.exclude( removedValue.stringValue() );
                        break;
                    default:
                        throw new IllegalStateException( "Unknown update mode " + update.getUpdateMode() );
                }

                updates.add( update );
            }

            @Override
            public void close() throws IOException, IndexEntryConflictException, IndexCapacityExceededException
            {
                if ( updates.size() > queueThreshold )
                {
                    flush();
                    updates.clear();
                }

            }

            @Override
            public void remove( PrimitiveLongSet nodeIds ) throws IOException
            {
                throw new UnsupportedOperationException( "Should not remove() from populating index." );
            }
        };
    }

    @Override
    public long sampleResult( Register.DoubleLong.Out result )
    {
        return sampler.result( result );
    }

    @Override
    protected void flush() throws IOException, IndexCapacityExceededException
    {
        for ( NodePropertyUpdate update : this.updates )
        {
            long nodeId = update.getNodeId();
            switch ( update.getUpdateMode() )
            {
            case ADDED:
            case CHANGED:
                // We don't look at the "before" value, so adding and changing idempotently is done the same way.
                Fieldable encodedValue = documentStructure.encodeAsFieldable( update.getValueAfter() );
                writer.updateDocument( documentStructure.newQueryForChangeOrRemove( nodeId ),
                                       documentStructure.newDocumentRepresentingProperty( nodeId, encodedValue ) );
                break;
            case REMOVED:
                writer.deleteDocuments( documentStructure.newQueryForChangeOrRemove( nodeId ) );
                break;
            default:
                throw new IllegalStateException( "Unknown update mode " + update.getUpdateMode() );
            }
        }
    }
}


File: community/lucene-index/src/main/java/org/neo4j/kernel/api/impl/index/UniqueLuceneIndexAccessor.java
/*
 * Copyright (c) 2002-2015 "Neo Technology,"
 * Network Engine for Objects in Lund AB [http://neotechnology.com]
 *
 * This file is part of Neo4j.
 *
 * Neo4j is free software: you can redistribute it and/or modify
 * it under the terms of the GNU General Public License as published by
 * the Free Software Foundation, either version 3 of the License, or
 * (at your option) any later version.
 *
 * This program is distributed in the hope that it will be useful,
 * but WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
 * GNU General Public License for more details.
 *
 * You should have received a copy of the GNU General Public License
 * along with this program.  If not, see <http://www.gnu.org/licenses/>.
 */
package org.neo4j.kernel.api.impl.index;

import java.io.Closeable;
import java.io.File;
import java.io.IOException;

import org.apache.lucene.document.Document;
import org.apache.lucene.search.IndexSearcher;
import org.apache.lucene.search.TopDocs;

import org.neo4j.collection.primitive.PrimitiveLongSet;
import org.neo4j.helpers.CancellationRequest;
import org.neo4j.kernel.api.exceptions.index.IndexCapacityExceededException;
import org.neo4j.kernel.api.index.IndexEntryConflictException;
import org.neo4j.kernel.api.index.IndexReader;
import org.neo4j.kernel.api.index.IndexUpdater;
import org.neo4j.kernel.api.index.NodePropertyUpdate;
import org.neo4j.kernel.api.index.Reservation;
import org.neo4j.kernel.impl.api.index.IndexUpdateMode;
import org.neo4j.kernel.impl.api.index.UniquePropertyIndexUpdater;

/**
 * Variant of {@link LuceneIndexAccessor} that also verifies uniqueness constraints.
 */
class UniqueLuceneIndexAccessor extends LuceneIndexAccessor implements UniquePropertyIndexUpdater.Lookup
{
    public UniqueLuceneIndexAccessor( LuceneDocumentStructure documentStructure,
                                      IndexWriterFactory<ReservingLuceneIndexWriter> indexWriterFactory,
                                      DirectoryFactory dirFactory, File dirFile ) throws IOException
    {
        super( documentStructure, indexWriterFactory, dirFactory, dirFile, -1 /* unused */ );
    }

    @Override
    public IndexUpdater newUpdater( final IndexUpdateMode mode )
    {
        if ( mode != IndexUpdateMode.RECOVERY )
        {
            return new LuceneUniquePropertyIndexUpdater( super.newUpdater( mode ) );
        }
        else
        {
            /* If we are in recovery, don't handle the business logic of validating uniqueness. */
            return super.newUpdater( mode );
        }
    }

    @Override
    protected IndexReader makeNewReader( IndexSearcher searcher, Closeable closeable, CancellationRequest cancellation )
    {
        return new LuceneUniqueIndexAccessorReader( searcher, documentStructure, closeable, cancellation );
    }

    @Override
    public Long currentlyIndexedNode( Object value ) throws IOException
    {
        IndexSearcher searcher = searcherManager.acquire();
        try
        {
            TopDocs docs = searcher.search( documentStructure.newQuery( value ), 1 );
            if ( docs.scoreDocs.length > 0 )
            {
                Document doc = searcher.getIndexReader().document( docs.scoreDocs[0].doc );
                return documentStructure.getNodeId( doc );
            }
        }
        finally
        {
            searcherManager.release( searcher );
        }
        return null;
    }

    /* The fact that this is here is a sign of a design error, and we should revisit and
         * remove this later on. Specifically, this is here because the unique indexes do validation
         * of uniqueness, which they really shouldn't be doing. In fact, they shouldn't exist, the unique
         * indexes are just indexes, and the logic of how they are used is not the responsibility of the
         * storage system to handle, that should go in the kernel layer.
         *
         * Anyway, where was I.. right: The kernel depends on the unique indexes to handle the business
         * logic of verifying domain uniqueness, and if they did not do that, race conditions appear for
         * index creation (not online operations, note) where concurrent violation of a currently created
         * index may break uniqueness.
         *
         * Phew. So, unique indexes currently have to pick up the slack here. The problem is that while
         * they serve the role of business logic execution, they also happen to be indexes, which is part
         * of the storage layer. There is one golden rule in the storage layer, which must never ever be
         * violated: Operations are idempotent. All operations against the storage layer have to be
         * executable over and over and have the same result, this is the basis of data recovery and
         * system consistency.
         *
         * Clearly, the uniqueness indexes don't do this, and so they fail in fulfilling their primary
         * contract in order to pick up the slack for the kernel not fulfilling it's contract. We hack
         * around this issue by tracking state - we know that probably the only time the idempotent
         * requirement will be invoked is during recovery, and we know that by happenstance, recovery is
         * single-threaded. As such, when we are in recovery, we turn off the business logic part and
         * correctly fulfill our actual contract. As soon as the database is online, we flip back to
         * running business logic in the storage layer and incorrectly implementing the storage layer
         * contract.
         *
         * One day, we should fix this.
         */
    private class LuceneUniquePropertyIndexUpdater extends UniquePropertyIndexUpdater
    {
        final IndexUpdater delegate;

        public LuceneUniquePropertyIndexUpdater( IndexUpdater delegate )
        {
            super( UniqueLuceneIndexAccessor.this );
            this.delegate = delegate;
        }

        @Override
        protected void flushUpdates( Iterable<NodePropertyUpdate> updates )
                throws IOException, IndexEntryConflictException, IndexCapacityExceededException
        {
            for ( NodePropertyUpdate update : updates )
            {
                delegate.process( update );
            }
            delegate.close();
        }

        @Override
        public Reservation validate( Iterable<NodePropertyUpdate> updates )
                throws IOException, IndexCapacityExceededException
        {
            return delegate.validate( updates );
        }

        @Override
        public void remove( PrimitiveLongSet nodeIds ) throws IOException
        {
            delegate.remove( nodeIds );
        }
    }
}


File: community/lucene-index/src/main/java/org/neo4j/kernel/api/impl/index/UniqueLuceneIndexPopulator.java
/*
 * Copyright (c) 2002-2015 "Neo Technology,"
 * Network Engine for Objects in Lund AB [http://neotechnology.com]
 *
 * This file is part of Neo4j.
 *
 * Neo4j is free software: you can redistribute it and/or modify
 * it under the terms of the GNU General Public License as published by
 * the Free Software Foundation, either version 3 of the License, or
 * (at your option) any later version.
 *
 * This program is distributed in the hope that it will be useful,
 * but WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
 * GNU General Public License for more details.
 *
 * You should have received a copy of the GNU General Public License
 * along with this program.  If not, see <http://www.gnu.org/licenses/>.
 */
package org.neo4j.kernel.api.impl.index;

import org.apache.lucene.document.Document;
import org.apache.lucene.document.Fieldable;
import org.apache.lucene.search.IndexSearcher;
import org.apache.lucene.search.SearcherManager;
import org.apache.lucene.search.TopDocs;

import java.io.File;
import java.io.IOException;
import java.util.HashMap;
import java.util.Map;

import org.neo4j.collection.primitive.PrimitiveLongSet;
import org.neo4j.kernel.api.exceptions.index.IndexCapacityExceededException;
import org.neo4j.kernel.api.index.IndexEntryConflictException;
import org.neo4j.kernel.api.index.IndexUpdater;
import org.neo4j.kernel.api.index.NodePropertyUpdate;
import org.neo4j.kernel.api.index.PreexistingIndexEntryConflictException;
import org.neo4j.kernel.api.index.PropertyAccessor;
import org.neo4j.kernel.api.index.Reservation;
import org.neo4j.kernel.api.index.util.FailureStorage;
import org.neo4j.register.Register;

/**
 * @deprecated Use {@link DeferredConstraintVerificationUniqueLuceneIndexPopulator} instead.
 */
@Deprecated
class UniqueLuceneIndexPopulator extends LuceneIndexPopulator
{
    private static final float LOAD_FACTOR = 0.75f;
    private final int batchSize;
    private SearcherManager searcherManager;
    private Map<Object, Long> currentBatch = newBatchMap();

    UniqueLuceneIndexPopulator( int batchSize, LuceneDocumentStructure documentStructure,
                                IndexWriterFactory<LuceneIndexWriter> indexWriterFactory,
                                DirectoryFactory dirFactory, File dirFile,
                                FailureStorage failureStorage, long indexId )
    {
        super( documentStructure, indexWriterFactory, dirFactory, dirFile, failureStorage, indexId );
        this.batchSize = batchSize;
    }

    private HashMap<Object, Long> newBatchMap()
    {
        return new HashMap<>( (int) (batchSize / LOAD_FACTOR), LOAD_FACTOR );
    }

    @Override
    public void create() throws IOException
    {
        super.create();
        searcherManager = writer.createSearcherManager();
    }

    @Override
    public void drop()
    {
        currentBatch.clear();
    }

    @Override
    protected void flush() throws IOException
    {
        // no need to do anything yet.
    }

    @Override
    public void add( long nodeId, Object propertyValue )
            throws IndexEntryConflictException, IOException, IndexCapacityExceededException
    {
        Long previousEntry = currentBatch.get( propertyValue );
        if ( previousEntry == null )
        {
            IndexSearcher searcher = searcherManager.acquire();
            try
            {
                TopDocs docs = searcher.search( documentStructure.newQuery( propertyValue ), 1 );
                if ( docs.totalHits > 0 )
                {
                    Document doc = searcher.getIndexReader().document( docs.scoreDocs[0].doc );
                    previousEntry = documentStructure.getNodeId( doc );
                }
            }
            finally
            {
                searcherManager.release( searcher );
            }
        }
        if ( previousEntry != null )
        {
            if ( previousEntry != nodeId )
            {
                throw new PreexistingIndexEntryConflictException( propertyValue, previousEntry, nodeId );
            }
        }
        else
        {
            currentBatch.put( propertyValue, nodeId );
            Fieldable encodedValue = documentStructure.encodeAsFieldable( propertyValue );
            writer.addDocument( documentStructure.newDocumentRepresentingProperty( nodeId, encodedValue ) );
            if ( currentBatch.size() >= batchSize )
            {
                startNewBatch();
            }
        }
    }

    @Override
    public void verifyDeferredConstraints( PropertyAccessor accessor ) throws IndexEntryConflictException, IOException
    {
        // constraints are checked in add() so do nothing
    }

    @Override
    public IndexUpdater newPopulatingUpdater( PropertyAccessor propertyAccessor ) throws IOException
    {
        return new IndexUpdater()
        {
            @Override
            public Reservation validate( Iterable<NodePropertyUpdate> updates ) throws IOException
            {
                return Reservation.EMPTY;
            }

            @Override
            public void process( NodePropertyUpdate update )
                    throws IOException, IndexEntryConflictException, IndexCapacityExceededException
            {
                add( update.getNodeId(), update.getValueAfter() );
            }

            @Override
            public void close() throws IOException, IndexEntryConflictException
            {
            }

            @Override
            public void remove( PrimitiveLongSet nodeIds )
            {
                throw new UnsupportedOperationException( "should not remove() from populating index" );
            }
        };
    }

    @Override
    public long sampleResult( Register.DoubleLong.Out result )
    {
        throw new UnsupportedOperationException();
    }

    private void startNewBatch() throws IOException
    {
        searcherManager.maybeRefresh();
        currentBatch = newBatchMap();
    }
}


File: community/lucene-index/src/test/java/org/neo4j/kernel/api/impl/index/AllNodesCollector.java
/*
 * Copyright (c) 2002-2015 "Neo Technology,"
 * Network Engine for Objects in Lund AB [http://neotechnology.com]
 *
 * This file is part of Neo4j.
 *
 * Neo4j is free software: you can redistribute it and/or modify
 * it under the terms of the GNU General Public License as published by
 * the Free Software Foundation, either version 3 of the License, or
 * (at your option) any later version.
 *
 * This program is distributed in the hope that it will be useful,
 * but WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
 * GNU General Public License for more details.
 *
 * You should have received a copy of the GNU General Public License
 * along with this program.  If not, see <http://www.gnu.org/licenses/>.
 */
package org.neo4j.kernel.api.impl.index;

import java.io.File;
import java.io.IOException;
import java.util.ArrayList;
import java.util.List;

import org.apache.lucene.index.IndexReader;
import org.apache.lucene.search.Collector;
import org.apache.lucene.search.IndexSearcher;
import org.apache.lucene.search.Query;
import org.apache.lucene.search.Scorer;
import org.apache.lucene.search.SearcherFactory;
import org.apache.lucene.search.SearcherManager;
import org.apache.lucene.store.Directory;

class AllNodesCollector extends Collector
{
    static List<Long> getAllNodes( DirectoryFactory dirFactory, File indexDir, Object propertyValue ) throws IOException
    {
        try ( Directory directory = dirFactory.open( indexDir );
              SearcherManager manager = new SearcherManager( directory, new SearcherFactory() );
              IndexSearcher searcher = manager.acquire() )
        {
            List<Long> nodes = new ArrayList<>();
            LuceneDocumentStructure documentStructure = new LuceneDocumentStructure();
            Query query = documentStructure.newQuery( propertyValue );
            searcher.search( query, new AllNodesCollector( documentStructure, nodes ) );
            return nodes;
        }
    }

    private final List<Long> nodeIds;
    private final LuceneDocumentStructure documentLogic;
    private IndexReader reader;

    AllNodesCollector( LuceneDocumentStructure documentLogic, List<Long> nodeIds )
    {
        this.documentLogic = documentLogic;
        this.nodeIds = nodeIds;
    }

    @Override
    public void setScorer( Scorer scorer ) throws IOException
    {
    }

    @Override
    public void collect( int doc ) throws IOException
    {
        nodeIds.add( documentLogic.getNodeId( reader.document( doc ) ) );
    }

    @Override
    public void setNextReader( IndexReader reader, int docBase ) throws IOException
    {
        this.reader = reader;
    }

    @Override
    public boolean acceptsDocsOutOfOrder()
    {
        return true;
    }
}


File: community/lucene-index/src/test/java/org/neo4j/kernel/api/impl/index/LuceneDocumentStructureTest.java
/*
 * Copyright (c) 2002-2015 "Neo Technology,"
 * Network Engine for Objects in Lund AB [http://neotechnology.com]
 *
 * This file is part of Neo4j.
 *
 * Neo4j is free software: you can redistribute it and/or modify
 * it under the terms of the GNU General Public License as published by
 * the Free Software Foundation, either version 3 of the License, or
 * (at your option) any later version.
 *
 * This program is distributed in the hope that it will be useful,
 * but WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
 * GNU General Public License for more details.
 *
 * You should have received a copy of the GNU General Public License
 * along with this program.  If not, see <http://www.gnu.org/licenses/>.
 */
package org.neo4j.kernel.api.impl.index;

import static junit.framework.TestCase.assertEquals;
import static org.neo4j.kernel.api.impl.index.LuceneDocumentStructure.NODE_ID_KEY;
import static org.neo4j.kernel.api.impl.index.LuceneDocumentStructure.ValueEncoding.Array;
import static org.neo4j.kernel.api.impl.index.LuceneDocumentStructure.ValueEncoding.Bool;
import static org.neo4j.kernel.api.impl.index.LuceneDocumentStructure.ValueEncoding.Number;
import static org.neo4j.kernel.api.impl.index.LuceneDocumentStructure.ValueEncoding.String;

import org.apache.lucene.document.Document;
import org.apache.lucene.document.Fieldable;
import org.apache.lucene.search.TermQuery;
import org.apache.lucene.util.NumericUtils;
import org.junit.Test;

public class LuceneDocumentStructureTest
{
    private final LuceneDocumentStructure documentStructure = new LuceneDocumentStructure();

    @Test
    public void shouldBuildDocumentRepresentingStringProperty() throws Exception
    {
        // given
        Fieldable fieldable = documentStructure.encodeAsFieldable( "hello" );
        Document document = documentStructure.newDocumentRepresentingProperty( 123, fieldable );

        // then
        assertEquals("123", document.get( NODE_ID_KEY ));
        assertEquals("hello", document.get( String.key() ));
    }

    @Test
    public void shouldBuildDocumentRepresentingBoolProperty() throws Exception
    {
        // given
        Fieldable fieldable = documentStructure.encodeAsFieldable( true );
        Document document = documentStructure.newDocumentRepresentingProperty( 123, fieldable );

        // then
        assertEquals("123", document.get( NODE_ID_KEY ));
        assertEquals("true", document.get( Bool.key() ));
    }

    @Test
    public void shouldBuildDocumentRepresentingNumberProperty() throws Exception
    {
        // given
        Fieldable fieldable = documentStructure.encodeAsFieldable( 12 );
        Document document = documentStructure.newDocumentRepresentingProperty( 123, fieldable );

        // then
        assertEquals("123", document.get( NODE_ID_KEY ));
        assertEquals( NumericUtils.doubleToPrefixCoded( 12.0 ), document.get( Number.key() ) );
    }

    @Test
    public void shouldBuildDocumentRepresentingArrayProperty() throws Exception
    {
        // given
        Fieldable fieldable = documentStructure.encodeAsFieldable( new Integer[]{1, 2, 3} );
        Document document = documentStructure.newDocumentRepresentingProperty( 123, fieldable );

        // then
        assertEquals("123", document.get( NODE_ID_KEY ));
        assertEquals("D1.0|2.0|3.0|", document.get( Array.key() ));
    }

    @Test
    public void shouldBuildQueryRepresentingBoolProperty() throws Exception
    {
        // given
        TermQuery query = (TermQuery) documentStructure.newQuery( true );

        // then
        assertEquals( "true", query.getTerm().text() );
    }

    @Test
    public void shouldBuildQueryRepresentingStringProperty() throws Exception
    {
        // given
        TermQuery query = (TermQuery) documentStructure.newQuery( "Characters" );

        // then
        assertEquals( "Characters", query.getTerm().text() );
    }

    @SuppressWarnings("unchecked")
    @Test
    public void shouldBuildQueryRepresentingNumberProperty() throws Exception
    {
        // given
        TermQuery query = (TermQuery) documentStructure.newQuery( 12 );

        // then
        assertEquals(  NumericUtils.doubleToPrefixCoded( 12.0 ), query.getTerm().text() );
    }

    @Test
    public void shouldBuildQueryRepresentingArrayProperty() throws Exception
    {
        // given
        TermQuery query = (TermQuery) documentStructure.newQuery( new Integer[]{1, 2, 3} );

        // then
        assertEquals( "D1.0|2.0|3.0|", query.getTerm().text() );
    }
}


File: community/lucene-index/src/test/java/org/neo4j/kernel/api/impl/index/LuceneIndexAccessorReaderTest.java
/*
 * Copyright (c) 2002-2015 "Neo Technology,"
 * Network Engine for Objects in Lund AB [http://neotechnology.com]
 *
 * This file is part of Neo4j.
 *
 * Neo4j is free software: you can redistribute it and/or modify
 * it under the terms of the GNU General Public License as published by
 * the Free Software Foundation, either version 3 of the License, or
 * (at your option) any later version.
 *
 * This program is distributed in the hope that it will be useful,
 * but WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
 * GNU General Public License for more details.
 *
 * You should have received a copy of the GNU General Public License
 * along with this program.  If not, see <http://www.gnu.org/licenses/>.
 */
package org.neo4j.kernel.api.impl.index;

import org.apache.lucene.index.IndexReader;
import org.apache.lucene.index.Term;
import org.apache.lucene.index.TermEnum;
import org.apache.lucene.search.IndexSearcher;
import org.junit.Before;
import org.junit.Test;

import java.io.Closeable;
import java.io.IOException;
import java.lang.reflect.Array;
import java.util.Arrays;
import java.util.HashSet;
import java.util.Set;

import org.neo4j.register.Register.DoubleLongRegister;
import org.neo4j.register.Registers;

import static org.junit.Assert.assertEquals;
import static org.junit.Assert.assertSame;
import static org.junit.Assert.assertTrue;
import static org.junit.Assert.fail;
import static org.mockito.Mockito.mock;
import static org.mockito.Mockito.when;
import static org.neo4j.helpers.CancellationRequest.NEVER_CANCELLED;
import static org.neo4j.kernel.api.impl.index.LuceneDocumentStructure.NODE_ID_KEY;

public class LuceneIndexAccessorReaderTest
{
    private static final int BUFFER_SIZE_LIMIT = 100_000;

    private final Closeable closeable = mock( Closeable.class );
    private final LuceneDocumentStructure documentLogic = mock( LuceneDocumentStructure.class );
    private final IndexSearcher searcher = mock( IndexSearcher.class );
    private final IndexReader reader = mock( IndexReader.class );
    private final TermEnum terms = mock( TermEnum.class );
    private final LuceneIndexAccessorReader accessor =
            new LuceneIndexAccessorReader( searcher, documentLogic, closeable, NEVER_CANCELLED, BUFFER_SIZE_LIMIT );

    @Before
    public void setup() throws IOException
    {
        when( searcher.getIndexReader() ).thenReturn( reader );
        when( reader.terms() ).thenReturn( terms );
    }

    @Test
    public void shouldProvideTheIndexUniqueValuesForAnEmptyIndex() throws Exception
    {
        // When
        final DoubleLongRegister output = Registers.newDoubleLongRegister();
        long indexSize = accessor.sampleIndex( output );

        // Then
        assertEquals( 0, indexSize );
        assertEquals( 0, output.readFirst() );
        assertEquals( 0, output.readSecond() );
    }

    @Test
    public void shouldProvideTheIndexUniqueValuesForAnIndexWithDuplicates() throws Exception
    {
        // Given
        when( terms.next() ).thenReturn( true, true, true, false );
        when( terms.term() ).thenReturn(
                new Term( "string", "aaa" ),
                new Term( "string", "ccc" ),
                new Term( "string", "ccc" )
        );

        // When
        final DoubleLongRegister output = Registers.newDoubleLongRegister();
        long indexSize = accessor.sampleIndex( output );

        // Then
        assertEquals( 3, indexSize );
        assertEquals( 2, output.readFirst() );
        assertEquals( 3, output.readSecond() );
    }


    @Test
    public void shouldSkipTheNonNodeIdKeyEntriesWhenCalculatingIndexUniqueValues() throws Exception
    {
        // Given
        when( terms.next() ).thenReturn( true, true, false );
        when( terms.term() ).thenReturn(
                new Term( NODE_ID_KEY, "aaa" ), // <- this should be ignored
                new Term( "string", "bbb" )
        );

        // When

        final DoubleLongRegister output = Registers.newDoubleLongRegister();
        long indexSize = accessor.sampleIndex( output );

        // Then
        assertEquals( 1, indexSize );
        assertEquals( 1, output.readFirst() );
        assertEquals( 1, output.readSecond() );
    }

    @Test
    public void shouldWrapAnIOExceptionIntoARuntimeExceptionWhenCalculatingIndexUniqueValues() throws Exception
    {
        // Given
        final IOException ioex = new IOException();
        when( terms.next() ).thenThrow( ioex );

        // When
        try
        {
            accessor.sampleIndex( Registers.newDoubleLongRegister() );
            fail( "should have thrown" );
        }
        catch ( RuntimeException ex )
        {
            // Then
            assertSame( ioex, ex.getCause() );
        }
    }

    @Test
    public void shouldReturnNoValueTypesIfTheIndexIsEmpty() throws Exception
    {
        // Given
        when( terms.next() ).thenReturn( false );

        // When
        final Set<Class> types = accessor.valueTypesInIndex();

        // Then
        assertTrue( types.isEmpty() );
    }

    @Test
    public void shouldReturnAllValueTypesContainedInTheIndex1() throws Exception
    {
        // Given
        when( terms.next() ).thenReturn( true, true, true, false );
        when( terms.term() ).thenReturn( new Term( "array" ), new Term( "string" ), new Term( "array" ) );

        // When
        final Set<Class> types = accessor.valueTypesInIndex();

        // Then

        assertEquals( new HashSet<Class>( Arrays.asList( Array.class, String.class ) ), types );
    }

    @Test
    public void shouldReturnAllValueTypesContainedInTheIndex2() throws Exception
    {
        // Given
        when( terms.next() ).thenReturn( true, true, true, true, false );
        when( terms.term() )
                .thenReturn( new Term( "array" ), new Term( "number" ), new Term( "string" ), new Term( "bool" ) );

        // When
        final Set<Class> types = accessor.valueTypesInIndex();

        // Then
        assertEquals( new HashSet<Class>( Arrays.asList( Array.class, Number.class, String.class, Boolean.class ) ), types );
    }

    @Test
    public void shouldWrapIOExceptionInRuntimeExceptionWhenAskingAllValueTypes() throws Exception
    {
        // Given
        final IOException ioex = new IOException();
        when( terms.next() ).thenThrow( ioex );

        // When
        try
        {
            accessor.valueTypesInIndex();
            fail("Should have thrown");
        }
        catch ( RuntimeException ex )
        {
            // then
            assertSame( ioex, ex.getCause() );
        }
    }
}


File: community/lucene-index/src/test/java/org/neo4j/kernel/api/impl/index/LuceneSchemaIndexPopulatorTest.java
/*
 * Copyright (c) 2002-2015 "Neo Technology,"
 * Network Engine for Objects in Lund AB [http://neotechnology.com]
 *
 * This file is part of Neo4j.
 *
 * Neo4j is free software: you can redistribute it and/or modify
 * it under the terms of the GNU General Public License as published by
 * the Free Software Foundation, either version 3 of the License, or
 * (at your option) any later version.
 *
 * This program is distributed in the hope that it will be useful,
 * but WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
 * GNU General Public License for more details.
 *
 * You should have received a copy of the GNU General Public License
 * along with this program.  If not, see <http://www.gnu.org/licenses/>.
 */
package org.neo4j.kernel.api.impl.index;

import org.apache.lucene.document.Document;
import org.apache.lucene.index.IndexReader;
import org.apache.lucene.search.IndexSearcher;
import org.apache.lucene.search.TopDocs;
import org.apache.lucene.store.Directory;
import org.apache.lucene.store.RAMDirectory;
import org.junit.After;
import org.junit.Before;
import org.junit.Test;

import java.io.File;
import java.io.IOException;
import java.util.HashSet;
import java.util.Set;

import org.neo4j.kernel.api.exceptions.index.IndexCapacityExceededException;
import org.neo4j.kernel.api.index.IndexConfiguration;
import org.neo4j.kernel.api.index.IndexDescriptor;
import org.neo4j.kernel.api.index.IndexEntryConflictException;
import org.neo4j.kernel.api.index.IndexPopulator;
import org.neo4j.kernel.api.index.IndexUpdater;
import org.neo4j.kernel.api.index.InternalIndexState;
import org.neo4j.kernel.api.index.NodePropertyUpdate;
import org.neo4j.kernel.api.index.PropertyAccessor;
import org.neo4j.kernel.configuration.Config;
import org.neo4j.kernel.impl.api.index.IndexStoreView;
import org.neo4j.kernel.impl.api.index.sampling.IndexSamplingConfig;

import static java.lang.Long.parseLong;
import static java.util.Arrays.asList;
import static org.junit.Assert.assertEquals;
import static org.mockito.Mockito.mock;
import static org.neo4j.helpers.collection.IteratorUtil.asSet;

public class LuceneSchemaIndexPopulatorTest
{
    @Test
    public void addingValuesShouldPersistThem() throws Exception
    {
        // WHEN
        index.add( 1, "First" );
        index.add( 2, "Second" );
        index.add( 3, (byte)1 );
        index.add( 4, (short)2 );
        index.add( 5, 3 );
        index.add( 6, 4L );
        index.add( 7, 5F );
        index.add( 8, 6D );

        // THEN
        assertIndexedValues(
                hit( "First", 1 ),
                hit( "Second", 2 ),
                hit( (byte)1, 3 ),
                hit( (short)2, 4 ),
                hit( 3, 5 ),
                hit( 4L, 6 ),
                hit( 5F, 7 ),
                hit( 6D, 8 ) );
    }

    @Test
    public void multipleEqualValues() throws Exception
    {
        // WHEN
        index.add( 1, "value" );
        index.add( 2, "value" );
        index.add( 3, "value" );

        // THEN
        assertIndexedValues(
                hit( "value", 1L, 2L, 3L ) );
    }

    @Test
    public void multipleEqualValuesWithUpdateThatRemovesOne() throws Exception
    {
        // WHEN
        index.add( 1, "value" );
        index.add( 2, "value" );
        index.add( 3, "value" );
        updatePopulator( index, asList( remove( 2, "value" ) ), indexStoreView );

        // THEN
        assertIndexedValues(
                hit( "value", 1L, 3L ) );
    }

    @Test
    public void changeUpdatesInterleavedWithAdds() throws Exception
    {
        // WHEN
        index.add( 1, "1" );
        index.add( 2, "2" );
        updatePopulator( index, asList( change( 1, "1", "1a" ) ), indexStoreView );
        index.add( 3, "3" );

        // THEN
        assertIndexedValues(
                no( "1" ),
                hit( "1a", 1 ),
                hit( "2", 2 ),
                hit( "3", 3 ) );
    }

    @Test
    public void addUpdatesInterleavedWithAdds() throws Exception
    {
        // WHEN
        index.add( 1, "1" );
        index.add( 2, "2" );
        updatePopulator( index,  asList( remove( 1, "1" ), add( 1, "1a" ) ), indexStoreView );
        index.add( 3, "3" );

        // THEN
        assertIndexedValues(
                hit( "1a", 1 ),
                hit( "2", 2 ),
                hit( "3", 3 ),
                no( "1" ) );
    }

    @Test
    public void removeUpdatesInterleavedWithAdds() throws Exception
    {
        // WHEN
        index.add( 1, "1" );
        index.add( 2, "2" );
        updatePopulator( index,  asList( remove( 2, "2" ) ), indexStoreView );
        index.add( 3, "3" );

        // THEN
        assertIndexedValues(
                hit( "1", 1 ),
                no( "2" ),
                hit( "3", 3 ) );
    }

    @Test
    public void multipleInterleaves() throws Exception
    {
        // WHEN
        index.add( 1, "1" );
        index.add( 2, "2" );
        updatePopulator( index,  asList( change( 1, "1", "1a" ), change( 2, "2", "2a" ) ), indexStoreView );
        index.add( 3, "3" );
        index.add( 4, "4" );
        updatePopulator( index,  asList( change( 1, "1a", "1b" ), change( 4, "4", "4a" ) ), indexStoreView );

        // THEN
        assertIndexedValues(
                no( "1" ),
                no( "1a" ),
                hit( "1b", 1 ),
                no( "2" ),
                hit( "2a", 2 ),
                hit( "3", 3 ),
                no( "4" ),
                hit( "4a", 4 ) );
    }

    private Hit hit( Object value, Long... nodeIds )
    {
        return new Hit( value, nodeIds );
    }

    private Hit hit( Object value, long nodeId )
    {
        return new Hit( value, nodeId );
    }

    private Hit no( Object value )
    {
        return new Hit( value );
    }

    private static class Hit
    {
        private final Object value;
        private final Long[] nodeIds;

        Hit( Object value, Long... nodeIds )
        {
            this.value = value;
            this.nodeIds = nodeIds;
        }
    }

    private NodePropertyUpdate add( long nodeId, Object value )
    {
        return NodePropertyUpdate.add( nodeId, 0, value, new long[0] );
    }

    private NodePropertyUpdate change( long nodeId, Object valueBefore, Object valueAfter )
    {
        return NodePropertyUpdate.change( nodeId, 0, valueBefore, new long[0], valueAfter, new long[0] );
    }

    private NodePropertyUpdate remove( long nodeId, Object removedValue )
    {
        return NodePropertyUpdate.remove( nodeId, 0, removedValue, new long[0] );
    }

    private IndexDescriptor indexDescriptor;
    private IndexStoreView indexStoreView;
    private LuceneSchemaIndexProvider provider;
    private Directory directory;
    private IndexPopulator index;
    private IndexReader reader;
    private IndexSearcher searcher;
    private final long indexId = 0;
    private int propertyKeyId = 666;
    private final LuceneDocumentStructure documentLogic = new LuceneDocumentStructure();

    @Before
    public void before() throws Exception
    {
        directory = new RAMDirectory();
        DirectoryFactory directoryFactory = new DirectoryFactory.Single(
                new DirectoryFactory.UncloseableDirectory( directory ) );
        provider = new LuceneSchemaIndexProvider( directoryFactory, new File( "target/whatever" ) );
        indexDescriptor = new IndexDescriptor( 42, propertyKeyId );
        indexStoreView = mock( IndexStoreView.class );
        IndexConfiguration indexConfig = new IndexConfiguration( false );
        IndexSamplingConfig samplingConfig = new IndexSamplingConfig( new Config() );
        index = provider.getPopulator( indexId, indexDescriptor, indexConfig, samplingConfig );
        index.create();
    }

    @After
    public void after() throws Exception
    {
        if ( reader != null )
            reader.close();
        directory.close();
    }

    private void assertIndexedValues( Hit... expectedHits ) throws IOException, IndexCapacityExceededException
    {
        switchToVerification();

        for ( Hit hit : expectedHits )
        {
            TopDocs hits = searcher.search( documentLogic.newQuery( hit.value ), 10 );
            assertEquals( "Unexpected number of index results from " + hit.value, hit.nodeIds.length, hits.totalHits );
            Set<Long> foundNodeIds = new HashSet<>();
            for ( int i = 0; i < hits.totalHits; i++ )
            {
                Document document = searcher.doc( hits.scoreDocs[i].doc );
                foundNodeIds.add( parseLong( document.get( "id" ) ) );
            }
            assertEquals( asSet( hit.nodeIds ), foundNodeIds );
        }
    }

    private void switchToVerification() throws IOException, IndexCapacityExceededException
    {
        index.close( true );
        assertEquals( InternalIndexState.ONLINE, provider.getInitialState( indexId ) );
        reader = IndexReader.open( directory );
        searcher = new IndexSearcher( reader );
    }

    private static void updatePopulator(
            IndexPopulator populator,
            Iterable<NodePropertyUpdate> updates,
            PropertyAccessor accessor )
            throws IOException, IndexEntryConflictException, IndexCapacityExceededException
    {
        try ( IndexUpdater updater = populator.newPopulatingUpdater( accessor ) )
        {
            for ( NodePropertyUpdate update :  updates )
            {
                updater.process( update );
            }
        }
    }
}


File: community/lucene-index/src/test/java/org/neo4j/kernel/api/impl/index/LuceneUniqueIndexAccessorReaderTest.java
/*
 * Copyright (c) 2002-2015 "Neo Technology,"
 * Network Engine for Objects in Lund AB [http://neotechnology.com]
 *
 * This file is part of Neo4j.
 *
 * Neo4j is free software: you can redistribute it and/or modify
 * it under the terms of the GNU General Public License as published by
 * the Free Software Foundation, either version 3 of the License, or
 * (at your option) any later version.
 *
 * This program is distributed in the hope that it will be useful,
 * but WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
 * GNU General Public License for more details.
 *
 * You should have received a copy of the GNU General Public License
 * along with this program.  If not, see <http://www.gnu.org/licenses/>.
 */
package org.neo4j.kernel.api.impl.index;

import org.apache.lucene.index.IndexReader;
import org.apache.lucene.search.IndexSearcher;
import org.junit.Before;
import org.junit.Test;

import java.io.Closeable;
import java.io.IOException;

import org.neo4j.kernel.api.exceptions.index.IndexNotFoundKernelException;
import org.neo4j.register.Register.DoubleLongRegister;
import org.neo4j.register.Registers;

import static org.junit.Assert.assertEquals;
import static org.mockito.Mockito.mock;
import static org.mockito.Mockito.when;
import static org.neo4j.helpers.CancellationRequest.NEVER_CANCELLED;

public class LuceneUniqueIndexAccessorReaderTest
{
    private final Closeable closeable = mock( Closeable.class );
    private final LuceneDocumentStructure documentLogic = mock( LuceneDocumentStructure.class );
    private final IndexSearcher searcher = mock( IndexSearcher.class );
    private final IndexReader reader = mock( IndexReader.class );

    @Before
    public void setup() throws IOException
    {
        when( searcher.getIndexReader() ).thenReturn( reader );
    }

    @Test
    public void shouldProvideTheIndexUniqueValuesForAnEmptyIndex() throws Exception
    {
        // Given
        when( reader.numDocs() ).thenReturn( 0 );
        final LuceneUniqueIndexAccessorReader accessor =
                new LuceneUniqueIndexAccessorReader( searcher, documentLogic, closeable, NEVER_CANCELLED );

        // When
        final DoubleLongRegister output = Registers.newDoubleLongRegister();
        long indexSize = sampleAccessor( accessor, output );

        // Then
        assertEquals( 0, indexSize );
        assertEquals( 0, output.readFirst() );
        assertEquals( 0, output.readSecond() );
    }

    @Test
    public void shouldSkipTheNonNodeIdKeyEntriesWhenCalculatingIndexUniqueValues() throws Exception
    {
        // Given
        when( reader.numDocs() ).thenReturn( 2 );
        final LuceneUniqueIndexAccessorReader accessor =
                new LuceneUniqueIndexAccessorReader( searcher, documentLogic, closeable, NEVER_CANCELLED );

        // When
        final DoubleLongRegister output = Registers.newDoubleLongRegister();
        long indexSize = sampleAccessor( accessor, output );

        // Then
        assertEquals( 2, indexSize );
        assertEquals( 2, output.readFirst() );
        assertEquals( 2, output.readSecond() );
    }

    private long sampleAccessor( LuceneIndexAccessorReader reader, DoubleLongRegister output )
            throws IndexNotFoundKernelException
    {
        return reader.sampleIndex( output );
    }
}
