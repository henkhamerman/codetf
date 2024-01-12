Refactoring Types: ['Extract Method']
/org/neo4j/kernel/AvailabilityGuard.java
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
package org.neo4j.kernel;

import java.util.List;
import java.util.concurrent.CopyOnWriteArrayList;
import java.util.concurrent.atomic.AtomicInteger;

import org.neo4j.function.Function;
import org.neo4j.helpers.Clock;
import org.neo4j.helpers.Format;
import org.neo4j.helpers.Listeners;
import org.neo4j.helpers.collection.Iterables;

import static org.neo4j.helpers.Listeners.notifyListeners;
import static org.neo4j.helpers.collection.Iterables.join;

/**
 * The availability guard is what ensures that the database will only take calls when it is in an ok state. It allows
 * query handling to easily determine if it is ok to call the database by calling {@link #isAvailable(long)}.
 * <p>
 * The implementation uses an atomic integer that is initialized to the nr of conditions that must be met for the
 * database to be available. Each such condition will then call grant/deny accordingly,
 * and if the integer becomes 0 access is granted.
 */
public class AvailabilityGuard
{
    public interface AvailabilityListener
    {
        void available();

        void unavailable();
    }

    /**
     * Represents a description of why someone is denying access to the database, to help debugging. Components
     * granting and revoking access should use the same denial reason for both method calls, as it is used to track
     * who is blocking access to the database.
     */
    public interface AvailabilityRequirement
    {
        String description();
    }

    public static AvailabilityRequirement availabilityRequirement( final String descriptionWhenBlocking )
    {
        return new AvailabilityRequirement()
        {
            @Override
            public String description()
            {
                return descriptionWhenBlocking;
            }
        };
    }

    private Iterable<AvailabilityListener> listeners = Listeners.newListeners();

    private final AtomicInteger available;
    private final List<AvailabilityRequirement> blockingComponents = new CopyOnWriteArrayList<>();
    private final Clock clock;

    public AvailabilityGuard( Clock clock )
    {
        this(clock, 0);
    }

    public AvailabilityGuard( Clock clock, int conditionCount )
    {
        this.clock = clock;
        available = new AtomicInteger( conditionCount );
    }

    public void deny( AvailabilityRequirement requirementNotMet )
    {
        int val;
        do
        {
            val = available.get();

            if ( val == -1 )
            {
                return;
            }

        } while ( !available.compareAndSet( val, val + 1 ) );

        blockingComponents.add( requirementNotMet );

        if ( val == 0 )
        {
            notifyListeners( listeners, new Listeners.Notification<AvailabilityListener>()
            {
                @Override
                public void notify( AvailabilityListener listener )
                {
                    listener.unavailable();
                }
            } );
        }
    }

    public void grant( AvailabilityRequirement requirementNowMet )
    {
        int val;
        do
        {
            val = available.get();

            if ( val == -1 )
            {
                return;
            }

        } while ( !available.compareAndSet( val, val - 1 ) );

        assert available.get() >= 0;
        blockingComponents.remove( requirementNowMet );

        if ( val == 1 )
        {
            notifyListeners( listeners, new Listeners.Notification<AvailabilityListener>()
            {
                @Override
                public void notify( AvailabilityListener listener )
                {
                    listener.available();
                }
            } );
        }
    }

    public void shutdown()
    {
        int val = available.getAndSet( -1 );
        if ( val == 0 )
        {
            notifyListeners( listeners, new Listeners.Notification<AvailabilityListener>()
            {
                @Override
                public void notify( AvailabilityListener listener )
                {
                    listener.unavailable();
                }
            } );
        }
    }

    private static enum Availability
    {
        AVAILABLE( true, true ),
        TEMPORARILY_UNAVAILABLE( false, true ),
        UNAVAILABLE( false, false );

        private final boolean available;
        private final boolean temporarily;

        private Availability( boolean available, boolean temporarily )
        {
            this.available = available;
            this.temporarily = temporarily;
        }
    }

    /**
     * Determines if the database is available for transactions to use.
     *
     * @param millis to wait if not yet available.
     * @return true if it is available, otherwise false. Returns false immediately if shutdown.
     */
    public boolean isAvailable( long millis )
    {
        return availability( millis ).available;
    }

    private Availability availability( long millis )
    {
        int val = available.get();
        if ( val == 0 )
        {
            return Availability.AVAILABLE;
        }
        else if ( val == -1 )
        {
            return Availability.UNAVAILABLE;
        }
        else
        {
            long start = clock.currentTimeMillis();

            while ( clock.currentTimeMillis() < start + millis )
            {
                val = available.get();
                if ( val == 0 )
                {
                    return Availability.AVAILABLE;
                }
                else if ( val == -1 )
                {
                    return Availability.UNAVAILABLE;
                }

                try
                {
                    Thread.sleep( 10 );
                }
                catch ( InterruptedException e )
                {
                    Thread.interrupted();
                    break;
                }
                Thread.yield();
            }

            return Availability.TEMPORARILY_UNAVAILABLE;
        }
    }

    public <EXCEPTION extends Throwable> void checkAvailability( long millis, Class<EXCEPTION> cls )
            throws EXCEPTION
    {
        Availability availability = availability( millis );
        if ( !availability.available )
        {
            EXCEPTION exception;
            try
            {
                String description = availability.temporarily
                        ? "Timeout waiting for database to become available and allow new transactions. Waited " +
                                Format.duration( millis ) + ". " + describeWhoIsBlocking()
                        : "Database not available because it's shutting down";
                exception = cls.getConstructor( String.class ).newInstance( description );
            }
            catch ( NoSuchMethodException e )
            {
                throw new Error( "Bad exception class given to this method, it doesn't have a (String) constructor", e );
            }
            catch ( Exception e )
            {
                throw new RuntimeException( e );
            }
            throw exception;
        }
    }

    public void addListener( AvailabilityListener listener )
    {
        listeners = Listeners.addListener( listener, listeners );
    }

    public void removeListener( AvailabilityListener listener )
    {
        listeners = Listeners.removeListener( listener, listeners );
    }

    /** Provide a textual description of what components, if any, are blocking access. */
    public String describeWhoIsBlocking()
    {
        if(blockingComponents.size() > 0 || available.get() > 0)
        {
            String causes = join( ", ", Iterables.map( DESCRIPTION, blockingComponents ) );
            return available.get() + " reasons for blocking: " + causes + ".";
        }
        return "No blocking components";
    }

    public static final Function<AvailabilityRequirement,String> DESCRIPTION = new Function<AvailabilityRequirement,
            String>()
    {

        @Override
        public String apply( AvailabilityRequirement availabilityRequirement )
        {
            return availabilityRequirement.description();
        }
    };
}


File: community/kernel/src/main/java/org/neo4j/kernel/DatabaseAvailability.java
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
package org.neo4j.kernel;

import java.util.concurrent.TimeUnit;

import org.neo4j.kernel.impl.transaction.TransactionCounters;
import org.neo4j.kernel.lifecycle.Lifecycle;

import static java.util.concurrent.TimeUnit.MILLISECONDS;
import static java.util.concurrent.locks.LockSupport.parkNanos;

import static org.neo4j.helpers.Clock.SYSTEM_CLOCK;

/**
 * This class handles whether the database as a whole is available to use at all.
 * As it runs as the last service in the lifecycle list, the stop() is called first
 * on stop, shutdown or restart, and thus blocks access to everything else for outsiders.
 */
public class DatabaseAvailability
        implements Lifecycle, AvailabilityGuard.AvailabilityRequirement
{
    private final AvailabilityGuard availabilityGuard;
    private final TransactionCounters transactionMonitor;
    private final long awaitActiveTransactionDeadlineMillis;

    public DatabaseAvailability( AvailabilityGuard availabilityGuard, TransactionCounters transactionMonitor )
    {
        this( availabilityGuard, transactionMonitor, TimeUnit.SECONDS.toMillis( 10 ) );
    }

    public DatabaseAvailability( AvailabilityGuard availabilityGuard, TransactionCounters transactionMonitor,
            long awaitActiveTransactionDeadlineMillis )
    {
        this.availabilityGuard = availabilityGuard;
        this.transactionMonitor = transactionMonitor;
        this.awaitActiveTransactionDeadlineMillis = awaitActiveTransactionDeadlineMillis;

        // On initial setup, deny availability
        availabilityGuard.deny( this );
    }

    @Override
    public void init()
            throws Throwable
    {
    }

    @Override
    public void start()
            throws Throwable
    {
        availabilityGuard.grant( this );
    }

    @Override
    public void stop()
            throws Throwable
    {
        // Database is no longer available for use
        // Deny beginning new transactions
        availabilityGuard.deny( this );

        // Await transactions stopped
        awaitTransactionsClosedWithinTimeout();
    }

    private void awaitTransactionsClosedWithinTimeout()
    {
        long deadline = SYSTEM_CLOCK.currentTimeMillis() + awaitActiveTransactionDeadlineMillis;
        while ( transactionMonitor.getNumberOfActiveTransactions() > 0 && SYSTEM_CLOCK.currentTimeMillis() < deadline )
        {
            parkNanos( MILLISECONDS.toNanos( 10 ) );
        }
    }

    @Override
    public void shutdown()
            throws Throwable
    {
        // TODO: Starting database. Make sure none can access it through lock or CAS
    }

    @Override
    public String description()
    {
        return "Database is stopped";
    }
}


File: community/kernel/src/main/java/org/neo4j/kernel/impl/factory/GraphDatabaseFacade.java
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
package org.neo4j.kernel.impl.factory;

import java.io.File;
import java.util.Collections;
import java.util.Map;

import org.neo4j.collection.primitive.PrimitiveLongCollections;
import org.neo4j.collection.primitive.PrimitiveLongIterator;
import org.neo4j.function.LongFunction;
import org.neo4j.function.Supplier;
import org.neo4j.graphdb.ConstraintViolationException;
import org.neo4j.graphdb.DependencyResolver;
import org.neo4j.graphdb.Label;
import org.neo4j.graphdb.MultipleFoundException;
import org.neo4j.graphdb.Node;
import org.neo4j.graphdb.NotFoundException;
import org.neo4j.graphdb.QueryExecutionException;
import org.neo4j.graphdb.Relationship;
import org.neo4j.graphdb.RelationshipType;
import org.neo4j.graphdb.ResourceIterable;
import org.neo4j.graphdb.ResourceIterator;
import org.neo4j.graphdb.Result;
import org.neo4j.graphdb.Transaction;
import org.neo4j.graphdb.TransactionFailureException;
import org.neo4j.graphdb.event.KernelEventHandler;
import org.neo4j.graphdb.event.TransactionEventHandler;
import org.neo4j.graphdb.index.IndexManager;
import org.neo4j.graphdb.schema.Schema;
import org.neo4j.graphdb.traversal.BidirectionalTraversalDescription;
import org.neo4j.graphdb.traversal.TraversalDescription;
import org.neo4j.helpers.collection.IteratorUtil;
import org.neo4j.helpers.collection.ResourceClosingIterator;
import org.neo4j.kernel.AvailabilityGuard;
import org.neo4j.kernel.GraphDatabaseAPI;
import org.neo4j.kernel.IdType;
import org.neo4j.kernel.KernelEventHandlers;
import org.neo4j.kernel.PlaceboTransaction;
import org.neo4j.kernel.TopLevelTransaction;
import org.neo4j.kernel.TransactionEventHandlers;
import org.neo4j.kernel.api.EntityType;
import org.neo4j.kernel.api.KernelAPI;
import org.neo4j.kernel.api.KernelTransaction;
import org.neo4j.kernel.api.ReadOperations;
import org.neo4j.kernel.api.Statement;
import org.neo4j.kernel.api.exceptions.EntityNotFoundException;
import org.neo4j.kernel.api.exceptions.InvalidTransactionTypeKernelException;
import org.neo4j.kernel.api.exceptions.index.IndexNotFoundKernelException;
import org.neo4j.kernel.api.exceptions.schema.ConstraintValidationKernelException;
import org.neo4j.kernel.api.exceptions.schema.SchemaKernelException;
import org.neo4j.kernel.api.exceptions.schema.SchemaRuleNotFoundException;
import org.neo4j.kernel.api.index.IndexDescriptor;
import org.neo4j.kernel.api.index.InternalIndexState;
import org.neo4j.kernel.impl.api.operations.KeyReadOperations;
import org.neo4j.kernel.impl.core.NodeManager;
import org.neo4j.kernel.impl.core.ThreadToStatementContextBridge;
import org.neo4j.kernel.impl.query.QueryEngineProvider;
import org.neo4j.kernel.impl.query.QueryExecutionEngine;
import org.neo4j.kernel.impl.query.QueryExecutionKernelException;
import org.neo4j.kernel.impl.store.StoreId;
import org.neo4j.kernel.impl.traversal.BidirectionalTraversalDescriptionImpl;
import org.neo4j.kernel.impl.traversal.MonoDirectionalTraversalDescription;
import org.neo4j.kernel.lifecycle.LifeSupport;
import org.neo4j.kernel.lifecycle.LifecycleException;
import org.neo4j.logging.Log;
import org.neo4j.tooling.GlobalGraphOperations;

import static java.lang.String.format;

import static org.neo4j.collection.primitive.PrimitiveLongCollections.map;
import static org.neo4j.helpers.collection.IteratorUtil.emptyIterator;
import static org.neo4j.kernel.impl.api.operations.KeyReadOperations.NO_SUCH_LABEL;
import static org.neo4j.kernel.impl.api.operations.KeyReadOperations.NO_SUCH_PROPERTY_KEY;

/**
 * Implementation of the GraphDatabaseService/GraphDatabaseService interfaces. This delegates to the
 * services created by the {@link org.neo4j.kernel.impl.factory.GraphDatabaseFacadeFactory}.
 *
 * To make a custom GraphDatabaseFacade, the best option is to subclass an existing GraphDatabaseFacadeFactory. Another
 * alternative, used by legacy database implementations, is to subclass this class and call
 * {@link org.neo4j.kernel.impl.factory.GraphDatabaseFacadeFactory#newFacade(java.io.File, java.util.Map, org.neo4j.kernel.impl.factory.GraphDatabaseFacadeFactory.Dependencies, GraphDatabaseFacade)} in the constructor.
 */
public class GraphDatabaseFacade
    implements GraphDatabaseAPI
{
    private static final long MAX_NODE_ID = IdType.NODE.getMaxValue();
    private static final long MAX_RELATIONSHIP_ID = IdType.RELATIONSHIP.getMaxValue();

    private boolean initialized = false;

    private ThreadToStatementContextBridge threadToTransactionBridge;
    private NodeManager nodeManager;
    private IndexManager indexManager;
    private Schema schema;
    private AvailabilityGuard availabilityGuard;
    private Log msgLog;
    private LifeSupport life;
    private Supplier<KernelAPI> kernel;
    private Supplier<QueryExecutionEngine> queryExecutor;
    private KernelEventHandlers kernelEventHandlers;
    private TransactionEventHandlers transactionEventHandlers;

    private long transactionStartTimeout;
    private DependencyResolver dependencies;
    private Supplier<StoreId> storeId;
    protected File storeDir;

    public PlatformModule platformModule;
    public EditionModule editionModule;
    public DataSourceModule dataSourceModule;

    /**
     * When {@link org.neo4j.kernel.impl.factory.GraphDatabaseFacadeFactory#newFacade(java.io.File, java.util.Map, org.neo4j.kernel.impl.factory.GraphDatabaseFacadeFactory.Dependencies, GraphDatabaseFacade)} has created the different
     * modules of a database, it calls this method so that the facade can get access to the created services.
     *
     * @param platformModule
     * @param editionModule
     * @param dataSourceModule
     */
    public void init(PlatformModule platformModule, EditionModule editionModule, DataSourceModule dataSourceModule)
    {
        this.platformModule = platformModule;
        this.editionModule = editionModule;
        this.dataSourceModule = dataSourceModule;
        this.threadToTransactionBridge = dataSourceModule.threadToTransactionBridge;
        this.nodeManager = dataSourceModule.nodeManager;
        this.indexManager = dataSourceModule.indexManager;
        this.schema = dataSourceModule.schema;
        this.availabilityGuard = platformModule.availabilityGuard;
        this.msgLog = platformModule.logging.getInternalLog( getClass() );
        this.life = platformModule.life;
        this.kernel = dataSourceModule.kernelAPI;
        this.queryExecutor = dataSourceModule.queryExecutor;
        this.kernelEventHandlers = dataSourceModule.kernelEventHandlers;
        this.transactionEventHandlers = dataSourceModule.transactionEventHandlers;
        this.transactionStartTimeout = editionModule.transactionStartTimeout;
        this.dependencies = platformModule.dependencies;
        this.storeId = dataSourceModule.storeId;
        this.storeDir = platformModule.storeDir;

        initialized = true;
    }

    @Override
    public Node createNode()
    {
        try ( Statement statement = threadToTransactionBridge.get() )
        {
            return nodeManager.newNodeProxyById( statement.dataWriteOperations().nodeCreate() );
        }
        catch ( InvalidTransactionTypeKernelException e )
        {
            throw new ConstraintViolationException( e.getMessage(), e );
        }
    }

    @Override
    public Node createNode( Label... labels )
    {
        try ( Statement statement = threadToTransactionBridge.get() )
        {
            long nodeId = statement.dataWriteOperations().nodeCreate();
            for ( Label label : labels )
            {
                int labelId = statement.tokenWriteOperations().labelGetOrCreateForName( label.name() );
                try
                {
                    statement.dataWriteOperations().nodeAddLabel( nodeId, labelId );
                }
                catch ( EntityNotFoundException e )
                {
                    throw new NotFoundException( "No node with id " + nodeId + " found.", e );
                }
            }
            return nodeManager.newNodeProxyById( nodeId );
        }
        catch ( ConstraintValidationKernelException e )
        {
            throw new ConstraintViolationException( "Unable to add label.", e );
        }
        catch ( SchemaKernelException e )
        {
            throw new IllegalArgumentException( e );
        }
        catch ( InvalidTransactionTypeKernelException e )
        {
            throw new ConstraintViolationException( e.getMessage(), e );
        }
    }

    @Override
    public Node getNodeById( long id )
    {
        if ( id < 0 || id > MAX_NODE_ID )
        {
            throw new NotFoundException( format( "Node %d not found", id ),
                    new EntityNotFoundException( EntityType.NODE, id ) );
        }
        try ( Statement statement = threadToTransactionBridge.get() )
        {
            if ( !statement.readOperations().nodeExists( id ) )
            {
                throw new NotFoundException( format( "Node %d not found", id ),
                        new EntityNotFoundException( EntityType.NODE, id ) );
            }

            return nodeManager.newNodeProxyById( id );
        }
    }

    @Override
    public Relationship getRelationshipById( long id )
    {
        if ( id < 0 || id > MAX_RELATIONSHIP_ID )
        {
            throw new NotFoundException( format( "Relationship %d not found", id ),
                    new EntityNotFoundException( EntityType.RELATIONSHIP, id ));
        }
        try ( Statement statement = threadToTransactionBridge.get() )
        {
            if ( !statement.readOperations().relationshipExists( id ) )
            {
                throw new NotFoundException( format( "Relationship %d not found", id ),
                        new EntityNotFoundException( EntityType.RELATIONSHIP, id ));
            }

            return nodeManager.newRelationshipProxy( id );
        }
    }

    @Override
    public IndexManager index()
    {
        // TODO: txManager.assertInUnterminatedTransaction();
        return indexManager;
    }

    @Override
    public Schema schema()
    {
        threadToTransactionBridge.assertInUnterminatedTransaction();
        return schema;
    }

    @Override
    public boolean isAvailable( long timeout )
    {
        return availabilityGuard.isAvailable( timeout );
    }

    @Override
    public void shutdown()
    {
        if (initialized)
        {
            try
            {
                msgLog.info( "Shutdown started" );
                availabilityGuard.shutdown();
                life.shutdown();
            }
            catch ( LifecycleException throwable )
            {
                msgLog.warn( "Shutdown failed", throwable );
                throw throwable;
            }
        }
    }

    @Override
     public Transaction beginTx()
     {
         availabilityGuard.checkAvailability( transactionStartTimeout, TransactionFailureException.class );

         TopLevelTransaction topLevelTransaction =
                 threadToTransactionBridge.getTopLevelTransactionBoundToThisThread( false );
         if ( topLevelTransaction != null )
         {
             return new PlaceboTransaction( topLevelTransaction );
         }

         try
         {
             KernelTransaction transaction = kernel.get().newTransaction();
             topLevelTransaction = new TopLevelTransaction( transaction, threadToTransactionBridge );
             threadToTransactionBridge.bindTransactionToCurrentThread( topLevelTransaction );
             return topLevelTransaction;
         }
         catch ( org.neo4j.kernel.api.exceptions.TransactionFailureException e )
         {
             throw new TransactionFailureException( "Failure to begin transaction", e );
         }
     }

     @Override
     public Result execute( String query ) throws QueryExecutionException
     {
         return execute( query, Collections.<String,Object>emptyMap() );
     }

     @Override
     public Result execute( String query, Map<String, Object> parameters ) throws QueryExecutionException
     {
         availabilityGuard.checkAvailability( transactionStartTimeout, TransactionFailureException.class );
         try
         {
             return queryExecutor.get().executeQuery( query, parameters, QueryEngineProvider.embeddedSession() );
         }
         catch ( QueryExecutionKernelException e )
         {
             throw e.asUserException();
         }
     }

    @Override
    public Iterable<Node> getAllNodes()
    {
        return GlobalGraphOperations.at( this ).getAllNodes();
    }

    @Override
    public Iterable<RelationshipType> getRelationshipTypes()
    {
        return GlobalGraphOperations.at( this ).getAllRelationshipTypes();
    }

    @Override
    public KernelEventHandler registerKernelEventHandler(
            KernelEventHandler handler )
    {
        return kernelEventHandlers.registerKernelEventHandler( handler );
    }

    @Override
    public <T> TransactionEventHandler<T> registerTransactionEventHandler(
            TransactionEventHandler<T> handler )
    {
        return transactionEventHandlers.registerTransactionEventHandler( handler );
    }

    @Override
    public KernelEventHandler unregisterKernelEventHandler(
            KernelEventHandler handler )
    {
        return kernelEventHandlers.unregisterKernelEventHandler( handler );
    }

    @Override
    public <T> TransactionEventHandler<T> unregisterTransactionEventHandler(
            TransactionEventHandler<T> handler )
    {
        return transactionEventHandlers.unregisterTransactionEventHandler( handler );
    }

    @Override
    public ResourceIterator<Node> findNodes( final Label myLabel, final String key, final Object value )
    {
        return nodesByLabelAndProperty( myLabel, key, value );
    }

    @Override
    public Node findNode( final Label myLabel, final String key, final Object value )
    {
        try ( ResourceIterator<Node> iterator = findNodes( myLabel, key, value ) )
        {
            if ( !iterator.hasNext() )
            {
                return null;
            }
            Node node = iterator.next();
            if ( iterator.hasNext() )
            {
                throw new MultipleFoundException();
            }
            return node;
        }
    }

    @Override
    public ResourceIterator<Node> findNodes( final Label myLabel )
    {
        return allNodesWithLabel( myLabel );
    }

    @Override
    public ResourceIterable<Node> findNodesByLabelAndProperty( final Label myLabel, final String key,
                                                               final Object value )
    {
        return new ResourceIterable<Node>()
        {
            @Override
            public ResourceIterator<Node> iterator()
            {
                return nodesByLabelAndProperty( myLabel, key, value );
            }
        };
    }

    private ResourceIterator<Node> nodesByLabelAndProperty( Label myLabel, String key, Object value )
    {
        Statement statement = threadToTransactionBridge.get();

        ReadOperations readOps = statement.readOperations();
        int propertyId = readOps.propertyKeyGetForName( key );
        int labelId = readOps.labelGetForName( myLabel.name() );

        if ( propertyId == NO_SUCH_PROPERTY_KEY || labelId == NO_SUCH_LABEL )
        {
            statement.close();
            return IteratorUtil.emptyIterator();
        }

        IndexDescriptor descriptor = findAnyIndexByLabelAndProperty( readOps, propertyId, labelId );

        try
        {
            if ( null != descriptor )
            {
                // Ha! We found an index - let's use it to find matching nodes
                return map2nodes( readOps.nodesGetFromIndexLookup( descriptor, value ), statement );
            }
        }
        catch ( IndexNotFoundKernelException e )
        {
            // weird at this point but ignore and fallback to a label scan
        }

        return getNodesByLabelAndPropertyWithoutIndex( propertyId, value, statement, labelId );
    }

    private IndexDescriptor findAnyIndexByLabelAndProperty( ReadOperations readOps, int propertyId, int labelId )
    {
        try
        {
            IndexDescriptor descriptor = readOps.indexesGetForLabelAndPropertyKey( labelId, propertyId );

            if ( readOps.indexGetState( descriptor ) == InternalIndexState.ONLINE )
            {
                // Ha! We found an index - let's use it to find matching nodes
                return descriptor;
            }
        }
        catch ( SchemaRuleNotFoundException | IndexNotFoundKernelException e )
        {
            // If we don't find a matching index rule, we'll scan all nodes and filter manually (below)
        }
        return null;
    }

    private ResourceIterator<Node> getNodesByLabelAndPropertyWithoutIndex( int propertyId, Object value,
                                                                           Statement statement, int labelId )
    {
        return map2nodes(
                new PropertyValueFilteringNodeIdIterator(
                        statement.readOperations().nodesGetForLabel( labelId ),
                        statement.readOperations(), propertyId, value ), statement );
    }

    private ResourceIterator<Node> allNodesWithLabel( final Label myLabel )
    {
        Statement statement = threadToTransactionBridge.get();

        int labelId = statement.readOperations().labelGetForName( myLabel.name() );
        if ( labelId == KeyReadOperations.NO_SUCH_LABEL )
        {
            statement.close();
            return emptyIterator();
        }

        final PrimitiveLongIterator nodeIds = statement.readOperations().nodesGetForLabel( labelId );
        return ResourceClosingIterator.newResourceIterator( statement, map( new LongFunction<Node>()
        {
            @Override
            public Node apply( long nodeId )
            {
                return nodeManager.newNodeProxyById( nodeId );
            }
        }, nodeIds ) );
    }

    private ResourceIterator<Node> map2nodes( PrimitiveLongIterator input, Statement statement )
    {
        return ResourceClosingIterator.newResourceIterator( statement, map( new LongFunction<Node>()
        {
            @Override
            public Node apply( long id )
            {
                return getNodeById( id );
            }
        }, input ) );
    }

    @Override
    public TraversalDescription traversalDescription()
    {
        return new MonoDirectionalTraversalDescription( threadToTransactionBridge );
    }

    @Override
    public BidirectionalTraversalDescription bidirectionalTraversalDescription()
    {
        return new BidirectionalTraversalDescriptionImpl( threadToTransactionBridge );
    }

    // GraphDatabaseAPI
    @Override
    public DependencyResolver getDependencyResolver()
    {
        return dependencies;
    }

    @Override
    public StoreId storeId()
    {
        return storeId.get();
    }

    @Override
    public String getStoreDir()
    {
        return storeDir.toString();
    }

    @Override
    public String toString()
    {
        return platformModule.config.get( GraphDatabaseFacadeFactory.Configuration.editionName)+" ["+storeDir+"]";
    }

    private static class PropertyValueFilteringNodeIdIterator extends PrimitiveLongCollections.PrimitiveLongBaseIterator
    {
        private final PrimitiveLongIterator nodesWithLabel;
        private final ReadOperations statement;
        private final int propertyKeyId;
        private final Object value;

        PropertyValueFilteringNodeIdIterator( PrimitiveLongIterator nodesWithLabel, ReadOperations statement,
                                              int propertyKeyId, Object value )
        {
            this.nodesWithLabel = nodesWithLabel;
            this.statement = statement;
            this.propertyKeyId = propertyKeyId;
            this.value = value;
        }

        @Override
        protected boolean fetchNext()
        {
            for ( boolean hasNext = nodesWithLabel.hasNext(); hasNext; hasNext = nodesWithLabel.hasNext() )
            {
                long nextValue = nodesWithLabel.next();
                try
                {
                    if ( statement.nodeGetProperty( nextValue, propertyKeyId ).valueEquals( value ) )
                    {
                        return next( nextValue );
                    }
                }
                catch ( EntityNotFoundException e )
                {
                    // continue to the next node
                }
            }
            return false;
        }
    }
}


File: community/kernel/src/test/java/org/neo4j/kernel/AvailabilityGuardTest.java
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
package org.neo4j.kernel;

import java.util.concurrent.atomic.AtomicBoolean;

import org.junit.Test;

import org.neo4j.helpers.TickingClock;

import static org.hamcrest.CoreMatchers.equalTo;
import static org.junit.Assert.assertThat;

public class AvailabilityGuardTest
{
    private final AvailabilityGuard.AvailabilityRequirement REQUIREMENT = new AvailabilityGuard.AvailabilityRequirement()
    {
        @Override
        public String description()
        {
            return "Thing";
        }
    };

    @Test
    public void givenAccessGuardWith2ConditionsWhenAwaitThenTimeoutAndReturnFalse() throws Exception
    {
        // Given
        TickingClock clock = new TickingClock( 0, 100 );
        AvailabilityGuard availabilityGuard = new AvailabilityGuard( clock, 2 );

        // When
        boolean result = availabilityGuard.isAvailable( 1000 );

        // Then
        assertThat( result, equalTo( false ) );
    }

    @Test
    public void givenAccessGuardWith2ConditionsWhenAwaitThenActuallyWaitGivenTimeout() throws Exception
    {
        // Given
        TickingClock clock = new TickingClock( 0, 100 );
        AvailabilityGuard availabilityGuard = new AvailabilityGuard( clock, 2 );

        // When
        long start = clock.currentTimeMillis();
        boolean result = availabilityGuard.isAvailable( 1000 );
        long end = clock.currentTimeMillis();

        // Then
        long waitTime = end - start;
        assertThat( result, equalTo( false ) );
        assertThat( waitTime, equalTo( 1200L ) );
    }

    @Test
    public void givenAccessGuardWith2ConditionsWhenGrantOnceAndAwaitThenTimeoutAndReturnFalse() throws Exception
    {
        // Given
        TickingClock clock = new TickingClock( 0, 100 );
        AvailabilityGuard availabilityGuard = new AvailabilityGuard( clock, 2 );

        // When
        long start = clock.currentTimeMillis();
        availabilityGuard.grant(REQUIREMENT);
        boolean result = availabilityGuard.isAvailable( 1000 );
        long end = clock.currentTimeMillis();

        // Then
        long waitTime = end - start;
        assertThat( result, equalTo( false ) );
        assertThat( waitTime, equalTo( 1200L ) );

    }

    @Test
    public void givenAccessGuardWith2ConditionsWhenGrantTwiceAndAwaitThenTrue() throws Exception
    {
        // Given
        TickingClock clock = new TickingClock( 0, 100 );
        AvailabilityGuard availabilityGuard = new AvailabilityGuard( clock, 2 );

        // When
        availabilityGuard.grant(REQUIREMENT);
        availabilityGuard.grant(REQUIREMENT);

        long start = clock.currentTimeMillis();
        boolean result = availabilityGuard.isAvailable( 1000 );
        long end = clock.currentTimeMillis();

        // Then
        long waitTime = end - start;
        assertThat( result, equalTo( true ) );
        assertThat( waitTime, equalTo( 100L ) );

    }

    @Test
    public void givenAccessGuardWith2ConditionsWhenGrantTwiceAndDenyOnceAndAwaitThenTimeoutAndReturnFalse() throws
            Exception
    {
        // Given
        TickingClock clock = new TickingClock( 0, 100 );
        AvailabilityGuard availabilityGuard = new AvailabilityGuard( clock, 2 );

        // When
        availabilityGuard.grant(REQUIREMENT);
        availabilityGuard.grant(REQUIREMENT);
        availabilityGuard.deny(REQUIREMENT);

        long start = clock.currentTimeMillis();
        boolean result = availabilityGuard.isAvailable( 1000 );
        long end = clock.currentTimeMillis();

        // Then
        long waitTime = end - start;
        assertThat( result, equalTo( false ) );
        assertThat( waitTime, equalTo( 1200L ) );
    }

    @Test
    public void givenAccessGuardWith2ConditionsWhenGrantOnceAndAwaitAndGrantAgainDuringAwaitThenReturnTrue() throws
            Exception
    {
        // Given
        TickingClock clock = new TickingClock( 0, 100 );
        final AvailabilityGuard availabilityGuard = new AvailabilityGuard( clock, 2 );

        // When
        clock.at( 500, new Runnable()
        {
            @Override
            public void run()
            {
                availabilityGuard.grant(REQUIREMENT);
            }
        } );
        availabilityGuard.grant(REQUIREMENT);

        long start = clock.currentTimeMillis();
        boolean result = availabilityGuard.isAvailable( 1000 );
        long end = clock.currentTimeMillis();

        // Then
        long waitTime = end - start;
        assertThat( result, equalTo( true ) );
        assertThat( waitTime, equalTo( 600L ) );
    }

    @Test
    public void givenAccessGuardWithConditionWhenGrantThenNotifyListeners() throws Exception
    {
        // Given
        TickingClock clock = new TickingClock( 0, 100 );
        final AvailabilityGuard availabilityGuard = new AvailabilityGuard( clock, 1 );
        final AtomicBoolean notified = new AtomicBoolean();
        AvailabilityGuard.AvailabilityListener availabilityListener = new AvailabilityGuard.AvailabilityListener()
        {
            @Override
            public void available()
            {
                notified.set( true );
            }

            @Override
            public void unavailable()
            {
            }
        };

        availabilityGuard.addListener( availabilityListener );

        // When
        availabilityGuard.grant(REQUIREMENT);

        // Then
        assertThat( notified.get(), equalTo( true ) );
    }

    @Test
    public void givenAccessGuardWithConditionWhenGrantAndDenyThenNotifyListeners() throws Exception
    {
        // Given
        TickingClock clock = new TickingClock( 0, 100 );
        final AvailabilityGuard availabilityGuard = new AvailabilityGuard( clock, 1 );
        final AtomicBoolean notified = new AtomicBoolean();
        AvailabilityGuard.AvailabilityListener availabilityListener = new AvailabilityGuard.AvailabilityListener()
        {
            @Override
            public void available()
            {
            }

            @Override
            public void unavailable()
            {
                notified.set( true );
            }
        };

        availabilityGuard.addListener( availabilityListener );

        // When
        availabilityGuard.grant(REQUIREMENT);
        availabilityGuard.deny(REQUIREMENT);

        // Then
        assertThat( notified.get(), equalTo( true ) );
    }

    @Test
    public void givenAccessGuardWithConditionWhenShutdownThenInstantlyDenyAccess() throws Exception
    {
        // Given
        TickingClock clock = new TickingClock( 0, 100 );
        final AvailabilityGuard availabilityGuard = new AvailabilityGuard( clock, 1 );

        // When
        availabilityGuard.shutdown();

        // Then
        boolean result = availabilityGuard.isAvailable( 1000 );

        assertThat( result, equalTo( false ) );
        assertThat( clock.currentTimeMillis(), equalTo( 0L ) );
    }

    @Test
    public void shouldExplainWhoIsBlockingAccess() throws
            Exception
    {
        // Given
        TickingClock clock = new TickingClock( 0, 100 );
        AvailabilityGuard availabilityGuard = new AvailabilityGuard( clock, 0 );

        // When
        availabilityGuard.deny(REQUIREMENT);
        availabilityGuard.deny(REQUIREMENT);

        // Then
        assertThat( availabilityGuard.describeWhoIsBlocking(), equalTo( "2 reasons for blocking: Thing, Thing." ) );
    }
}


File: enterprise/ha/src/main/java/org/neo4j/kernel/ha/cluster/HighAvailabilityMemberStateMachine.java
/*
 * Copyright (c) 2002-2015 "Neo Technology,"
 * Network Engine for Objects in Lund AB [http://neotechnology.com]
 *
 * This file is part of Neo4j.
 *
 * Neo4j is free software: you can redistribute it and/or modify
 * it under the terms of the GNU Affero General Public License as
 * published by the Free Software Foundation, either version 3 of the
 * License, or (at your option) any later version.
 *
 * This program is distributed in the hope that it will be useful,
 * but WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
 * GNU Affero General Public License for more details.
 *
 * You should have received a copy of the GNU Affero General Public License
 * along with this program. If not, see <http://www.gnu.org/licenses/>.
 */
package org.neo4j.kernel.ha.cluster;

import java.net.URI;

import org.neo4j.cluster.InstanceId;
import org.neo4j.cluster.member.ClusterMemberEvents;
import org.neo4j.cluster.member.ClusterMemberListener;
import org.neo4j.cluster.protocol.election.Election;
import org.neo4j.helpers.Listeners;
import org.neo4j.helpers.collection.Iterables;
import org.neo4j.kernel.AvailabilityGuard;
import org.neo4j.kernel.ha.cluster.member.ClusterMembers;
import org.neo4j.kernel.impl.store.StoreId;
import org.neo4j.kernel.lifecycle.LifecycleAdapter;
import org.neo4j.logging.Log;
import org.neo4j.logging.LogProvider;

import static org.neo4j.cluster.util.Quorums.isQuorum;

/**
 * State machine that listens for global cluster events, and coordinates
 * the internal transitions between ClusterMemberStates. Internal services
 * that wants to know what is going on should register ClusterMemberListener implementations
 * which will receive callbacks on state changes.
 */
public class HighAvailabilityMemberStateMachine extends LifecycleAdapter implements HighAvailability,
        AvailabilityGuard.AvailabilityRequirement
{
    private final HighAvailabilityMemberContext context;
    private final AvailabilityGuard availabilityGuard;
    private final ClusterMemberEvents events;
    private Log log;
    private Iterable<HighAvailabilityMemberListener> memberListeners = Listeners.newListeners();
    private volatile HighAvailabilityMemberState state;
    private StateMachineClusterEventListener eventsListener;
    private final ClusterMembers members;
    private final Election election;

    public HighAvailabilityMemberStateMachine( HighAvailabilityMemberContext context,
                                               AvailabilityGuard availabilityGuard,
                                               ClusterMembers members, ClusterMemberEvents events, Election election,
                                               LogProvider logProvider )
    {
        this.context = context;
        this.availabilityGuard = availabilityGuard;
        this.members = members;
        this.events = events;
        this.election = election;
        this.log = logProvider.getLog( getClass() );
        state = HighAvailabilityMemberState.PENDING;
    }

    @Override
    public void init() throws Throwable
    {
        events.addClusterMemberListener( eventsListener = new StateMachineClusterEventListener() );
        // On initial startup, disallow database access
        availabilityGuard.deny( this );
    }

    @Override
    public void stop() throws Throwable
    {
        events.removeClusterMemberListener( eventsListener );
        HighAvailabilityMemberState oldState = state;
        state = HighAvailabilityMemberState.PENDING;
        final HighAvailabilityMemberChangeEvent event =
                new HighAvailabilityMemberChangeEvent( oldState, state, null, null );
        Listeners.notifyListeners( memberListeners, new Listeners.Notification<HighAvailabilityMemberListener>()
        {
            @Override
            public void notify( HighAvailabilityMemberListener listener )
            {
                listener.instanceStops( event );
            }
        } );

        // If we are in a state that allows access, we must deny now that we shut down.
        if ( oldState.isAccessAllowed() )
        {
            availabilityGuard.deny(this);
        }

        context.setAvailableHaMasterId( null );
    }

    @Override
    public void addHighAvailabilityMemberListener( HighAvailabilityMemberListener toAdd )
    {
        memberListeners = Listeners.addListener( toAdd, memberListeners );
    }

    @Override
    public void removeHighAvailabilityMemberListener( HighAvailabilityMemberListener toRemove )
    {
        memberListeners = Listeners.removeListener( toRemove, memberListeners );
    }

    public HighAvailabilityMemberState getCurrentState()
    {
        return state;
    }

    public boolean isMaster()
    {
        return getCurrentState() == HighAvailabilityMemberState.MASTER;
    }

    @Override
    public String description()
    {
        return "Cluster state is '" + getCurrentState() + "'";
    }

    private class StateMachineClusterEventListener implements ClusterMemberListener
    {
        @Override
        public synchronized void coordinatorIsElected( InstanceId coordinatorId )
        {
            try
            {
                HighAvailabilityMemberState oldState = state;
                InstanceId previousElected = context.getElectedMasterId();

                // Check if same coordinator was elected
//                if ( !coordinatorId.equals( previousElected ) )
                {
                    context.setAvailableHaMasterId( null );
                    state = state.masterIsElected( context, coordinatorId );


                    context.setElectedMasterId( coordinatorId );
                    final HighAvailabilityMemberChangeEvent event = new HighAvailabilityMemberChangeEvent( oldState,
                            state, coordinatorId,
                            null );
                    Listeners.notifyListeners( memberListeners,
                            new Listeners.Notification<HighAvailabilityMemberListener>()
                            {
                                @Override
                                public void notify( HighAvailabilityMemberListener listener )
                                {
                                    listener.masterIsElected( event );
                                }
                            } );

                    if ( oldState.isAccessAllowed() && oldState != state )
                    {
                        availabilityGuard.deny(HighAvailabilityMemberStateMachine.this);
                    }

                    log.debug( "Got masterIsElected(" + coordinatorId + "), moved to " + state + " from " + oldState
                            + ". Previous elected master is " + previousElected );
                }
            }
            catch ( Throwable t )
            {
                throw new RuntimeException( t );
            }
        }

        @Override
        public synchronized void memberIsAvailable( String role, InstanceId instanceId, URI roleUri, StoreId storeId )
        {
            try
            {
                if ( role.equals( HighAvailabilityModeSwitcher.MASTER ) )
                {
//                    if ( !roleUri.equals( context.getAvailableHaMaster() ) )
                    {
                        HighAvailabilityMemberState oldState = state;
                        context.setAvailableHaMasterId( roleUri );
                        state = state.masterIsAvailable( context, instanceId, roleUri );
                        log.debug( "Got masterIsAvailable(" + instanceId + "), moved to " + state + " from " +
                                oldState );
                        final HighAvailabilityMemberChangeEvent event = new HighAvailabilityMemberChangeEvent( oldState,
                                state, instanceId, roleUri );
                        Listeners.notifyListeners( memberListeners,
                                new Listeners.Notification<HighAvailabilityMemberListener>()
                                {
                                    @Override
                                    public void notify( HighAvailabilityMemberListener listener )
                                    {
                                        listener.masterIsAvailable( event );
                                    }
                                } );

                        if ( oldState == HighAvailabilityMemberState.TO_MASTER && state ==
                                HighAvailabilityMemberState.MASTER )
                        {
                            availabilityGuard.grant( HighAvailabilityMemberStateMachine.this );
                        }
                    }
                }
                else if ( role.equals( HighAvailabilityModeSwitcher.SLAVE ) )
                {
                    HighAvailabilityMemberState oldState = state;
                    state = state.slaveIsAvailable( context, instanceId, roleUri );
                    log.debug( "Got slaveIsAvailable(" + instanceId + "), " +
                            "moved to " + state + " from " + oldState );
                    final HighAvailabilityMemberChangeEvent event = new HighAvailabilityMemberChangeEvent( oldState,
                            state, instanceId, roleUri );
                    Listeners.notifyListeners( memberListeners,
                            new Listeners.Notification<HighAvailabilityMemberListener>()
                            {
                                @Override
                                public void notify( HighAvailabilityMemberListener listener )
                                {
                                    listener.slaveIsAvailable( event );
                                }
                            } );

                    if ( oldState == HighAvailabilityMemberState.TO_SLAVE &&
                            state == HighAvailabilityMemberState.SLAVE )
                    {
                        availabilityGuard.grant( HighAvailabilityMemberStateMachine.this );
                    }
                }
            }
            catch ( Throwable throwable )
            {
                log.warn( "Exception while receiving member availability notification", throwable );
            }
        }

        @Override
        public void memberIsUnavailable( String role, InstanceId unavailableId )
        {
            if ( context.getMyId().equals( unavailableId ) &&
                 HighAvailabilityModeSwitcher.SLAVE.equals( role ) &&
                 state == HighAvailabilityMemberState.SLAVE )
            {
                HighAvailabilityMemberState oldState = state;
                changeStateToPending();
                log.debug( "Got memberIsUnavailable(" + unavailableId + "), moved to " + state + " from " + oldState );
            }
            else
            {
                log.debug( "Got memberIsUnavailable(" + unavailableId + ")" );
            }
        }

        @Override
        public void memberIsFailed( InstanceId instanceId )
        {
            if ( !isQuorum( getAliveCount(), getTotalCount() ) )
            {
                HighAvailabilityMemberState oldState = state;
                changeStateToPending();
                log.debug( "Got memberIsFailed(" + instanceId + ") and cluster lost quorum to continue, moved to "
                        + state + " from " + oldState );
            }
            else
            {
                log.debug( "Got memberIsFailed(" + instanceId + ")" );
            }
        }

        @Override
        public void memberIsAlive( InstanceId instanceId )
        {
            if ( isQuorum(getAliveCount(), getTotalCount()) && state.equals( HighAvailabilityMemberState.PENDING ) )
            {
                election.performRoleElections();
            }
        }

        private void changeStateToPending()
        {
            if ( state.isAccessAllowed() )
            {
                availabilityGuard.deny( HighAvailabilityMemberStateMachine.this );
            }

            final HighAvailabilityMemberChangeEvent event =
                    new HighAvailabilityMemberChangeEvent( state, HighAvailabilityMemberState.PENDING, null, null );

            state = HighAvailabilityMemberState.PENDING;

            Listeners.notifyListeners( memberListeners, new Listeners.Notification<HighAvailabilityMemberListener>()
            {
                @Override
                public void notify( HighAvailabilityMemberListener listener )
                {
                    listener.instanceStops( event );
                }
            } );

            context.setAvailableHaMasterId( null );
            context.setElectedMasterId( null );
        }

        private long getAliveCount()
        {
            return Iterables.count( Iterables.filter( ClusterMembers.ALIVE, members.getMembers() ) );
        }

        private long getTotalCount()
        {
            return Iterables.count( members.getMembers() );
        }
    }
}


File: enterprise/ha/src/main/java/org/neo4j/kernel/ha/lock/SlaveLocksClient.java
/*
 * Copyright (c) 2002-2015 "Neo Technology,"
 * Network Engine for Objects in Lund AB [http://neotechnology.com]
 *
 * This file is part of Neo4j.
 *
 * Neo4j is free software: you can redistribute it and/or modify
 * it under the terms of the GNU Affero General Public License as
 * published by the Free Software Foundation, either version 3 of the
 * License, or (at your option) any later version.
 *
 * This program is distributed in the hope that it will be useful,
 * but WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
 * GNU Affero General Public License for more details.
 *
 * You should have received a copy of the GNU Affero General Public License
 * along with this program. If not, see <http://www.gnu.org/licenses/>.
 */
package org.neo4j.kernel.ha.lock;

import java.util.ArrayList;
import java.util.HashMap;
import java.util.Map;
import java.util.concurrent.atomic.AtomicInteger;

import org.neo4j.com.RequestContext;
import org.neo4j.com.Response;
import org.neo4j.kernel.AvailabilityGuard;
import org.neo4j.kernel.DeadlockDetectedException;
import org.neo4j.kernel.api.exceptions.TransactionFailureException;
import org.neo4j.kernel.ha.com.RequestContextFactory;
import org.neo4j.kernel.ha.com.master.Master;
import org.neo4j.kernel.impl.locking.AcquireLockTimeoutException;
import org.neo4j.kernel.impl.locking.LockManager;
import org.neo4j.kernel.impl.locking.Locks;
import org.neo4j.kernel.impl.locking.ResourceTypes;

import static org.neo4j.kernel.impl.locking.LockType.READ;
import static org.neo4j.kernel.impl.locking.LockType.WRITE;

/**
 * The slave locks client is responsible for managing locks on behalf of some actor on a slave machine. An actor
 * could be a transaction or some other job that runs in the database.
 *
 * The client maintains a local "real" lock client, backed by some regular Locks implementation, but it also coordinates
 * with the master for certain types of locks. If you grab a lock on a node, for instance, this class will grab a
 * cluster-global lock by talking to the master machine, and then grab that same lock locally before returning.
 */
class SlaveLocksClient implements Locks.Client
{
    private final Master master;
    private final Locks.Client client;
    private final Locks localLockManager;
    private final RequestContextFactory requestContextFactory;
    private final AvailabilityGuard availabilityGuard;
    private final SlaveLockManager.Configuration config;

    // Using atomic ints to avoid creating garbage through boxing.
    private final Map<Locks.ResourceType, Map<Long, AtomicInteger>> sharedLocks;
    private final Map<Locks.ResourceType, Map<Long, AtomicInteger>> exclusiveLocks;
    private boolean initialized = false;

    public SlaveLocksClient(
            Master master,
            Locks.Client local,
            Locks localLockManager,
            RequestContextFactory requestContextFactory,
            AvailabilityGuard availabilityGuard,
            SlaveLockManager.Configuration config )
    {
        this.master = master;
        this.client = local;
        this.localLockManager = localLockManager;
        this.requestContextFactory = requestContextFactory;
        this.availabilityGuard = availabilityGuard;
        this.config = config;
        sharedLocks = new HashMap<>();
        exclusiveLocks = new HashMap<>();
    }

    private Map<Long, AtomicInteger> getLockMap(
            Map<Locks.ResourceType, Map<Long, AtomicInteger>> resourceMap,
            Locks.ResourceType resourceType )
    {
        Map<Long, AtomicInteger> lockMap = resourceMap.get( resourceType );
        if ( lockMap == null )
        {
            lockMap = new HashMap<>();
            resourceMap.put( resourceType, lockMap );
        }
        return lockMap;
    }

    @Override
    public void acquireShared( Locks.ResourceType resourceType, long... resourceIds ) throws AcquireLockTimeoutException
    {
        Map<Long, AtomicInteger> lockMap = getLockMap( sharedLocks, resourceType );
        long[] untakenIds = incrementAndRemoveAlreadyTakenLocks( lockMap, resourceIds );
        if ( untakenIds.length > 0 && getReadLockOnMaster( resourceType, untakenIds ) )
        {
            if ( client.trySharedLock( resourceType, untakenIds ) )
            {
                for ( int i = 0; i < untakenIds.length; i++ )
                {
                    lockMap.put( untakenIds[i], new AtomicInteger( 1 ) );
                }
            }
            else
            {
                throw new LocalDeadlockDetectedException( client, localLockManager, resourceType, resourceIds, READ );

            }
        }
    }

    @Override
    public void acquireExclusive( Locks.ResourceType resourceType, long... resourceIds ) throws
            AcquireLockTimeoutException
    {
        Map<Long, AtomicInteger> lockMap = getLockMap( exclusiveLocks, resourceType );
        long[] untakenIds = incrementAndRemoveAlreadyTakenLocks( lockMap, resourceIds );
        if ( untakenIds.length > 0 && acquireExclusiveOnMaster( resourceType, untakenIds ) )
        {
            if ( client.tryExclusiveLock( resourceType, untakenIds ) )
            {
                for ( int i = 0; i < untakenIds.length; i++ )
                {
                    lockMap.put( untakenIds[i], new AtomicInteger( 1 ) );
                }
            }
            else
            {
                throw new LocalDeadlockDetectedException( client, localLockManager, resourceType, resourceIds, WRITE );
            }
        }
    }

    private long[] incrementAndRemoveAlreadyTakenLocks(
            Map<Long, AtomicInteger> takenLocks,
            long[] resourceIds )
    {
        ArrayList<Long> untakenIds = new ArrayList<>();
        for ( int i = 0; i < resourceIds.length; i++ )
        {
            long id = resourceIds[i];
            AtomicInteger counter = takenLocks.get( id );
            if ( counter != null )
            {
                counter.incrementAndGet();
            }
            else
            {
                untakenIds.add( id );
            }
        }
        long[] untaken = new long[untakenIds.size()];
        for ( int i = 0; i < untaken.length; i++ )
        {
            long id = untakenIds.get( i );
            untaken[i] = id;
        }
        return untaken;
    }

    @Override
    public boolean tryExclusiveLock( Locks.ResourceType resourceType, long... resourceIds )
    {
        throw newUnsupportedDirectTryLockUsageException();
    }

    @Override
    public boolean trySharedLock( Locks.ResourceType resourceType, long... resourceIds )
    {
        throw newUnsupportedDirectTryLockUsageException();
    }

    @Override
    public void releaseShared( Locks.ResourceType resourceType, long... resourceIds )
    {
        Map<Long, AtomicInteger> lockMap = getLockMap( sharedLocks, resourceType );
        for ( long resourceId : resourceIds )
        {
            AtomicInteger counter = lockMap.get( resourceId );
            if(counter == null)
            {
                throw new IllegalStateException( this + " cannot release lock it does not hold: EXCLUSIVE " +
                        resourceType + "[" + resourceId + "]" );
            }
            if(counter.decrementAndGet() == 0)
            {
                lockMap.remove( resourceId );
                client.releaseShared( resourceType, resourceId );
            }
        }
    }

    @Override
    public void releaseExclusive( Locks.ResourceType resourceType, long... resourceIds )
    {
        Map<Long, AtomicInteger> lockMap = getLockMap( exclusiveLocks, resourceType );
        for ( long resourceId : resourceIds )
        {
            AtomicInteger counter = lockMap.get( resourceId );
            if(counter == null)
            {
                throw new IllegalStateException( this + " cannot release lock it does not hold: EXCLUSIVE " +
                        resourceType + "[" + resourceId + "]" );
            }
            if(counter.decrementAndGet() == 0)
            {
                lockMap.remove( resourceId );
                client.releaseExclusive( resourceType, resourceId );
            }
        }
    }

    @Override
    public void releaseAllShared()
    {
        sharedLocks.clear();
        client.releaseAllShared();
    }

    @Override
    public void releaseAllExclusive()
    {
        exclusiveLocks.clear();
        client.releaseAllExclusive();
    }

    @Override
    public void releaseAll()
    {
        sharedLocks.clear();
        exclusiveLocks.clear();
        if ( initialized )
        {
            try ( Response<Void> ignored = master.endLockSession( newRequestContextFor( client ), true ) )
            {
                // Lock session is closed on master at this point
            }
            initialized = false;
        }
        client.releaseAll();
    }

    @Override
    public void close()
    {
        sharedLocks.clear();
        exclusiveLocks.clear();
        if ( initialized )
        {
            try ( Response<Void> ignored = master.endLockSession( newRequestContextFor( client ), true ) )
            {
                // Lock session is closed on master at this point
            }
        }
        client.close();
    }

    @Override
    public int getLockSessionId()
    {
        return initialized ? client.getLockSessionId() : -1;
    }

    private boolean getReadLockOnMaster( Locks.ResourceType resourceType, long ... resourceId )
    {
        if ( resourceType == ResourceTypes.NODE
            || resourceType == ResourceTypes.RELATIONSHIP
            || resourceType == ResourceTypes.GRAPH_PROPS
            || resourceType == ResourceTypes.LEGACY_INDEX )
        {
            makeSureTxHasBeenInitialized();

            RequestContext requestContext = newRequestContextFor( this );
            try ( Response<LockResult> response = master.acquireSharedLock( requestContext, resourceType, resourceId ) )
            {
                return receiveLockResponse( response );
            }
        }
        else
        {
            return true;
        }
    }

    private boolean acquireExclusiveOnMaster( Locks.ResourceType resourceType, long... resourceId )
    {
        makeSureTxHasBeenInitialized();
        RequestContext requestContext = newRequestContextFor( this );
        try ( Response<LockResult> response = master.acquireExclusiveLock( requestContext, resourceType, resourceId ) )
        {
            return receiveLockResponse( response );
        }
    }

    private boolean receiveLockResponse( Response<LockResult> response )
    {
        LockResult result = response.response();

        switch ( result.getStatus() )
        {
            case DEAD_LOCKED:
                throw new DeadlockDetectedException( result.getDeadlockMessage() );
            case NOT_LOCKED:
                throw new UnsupportedOperationException();
            case OK_LOCKED:
                break;
            default:
                throw new UnsupportedOperationException( result.toString() );
        }

        return true;
    }

    private void makeSureTxHasBeenInitialized()
    {
        availabilityGuard.checkAvailability( config.getAvailabilityTimeout(), RuntimeException.class );
        if ( !initialized )
        {
            try ( Response<Void> ignored = master.newLockSession( newRequestContextFor( client ) ) )
            {
                // Lock session is initialized on master at this point
            }
            catch ( TransactionFailureException e )
            {
                // Temporary wrapping, we should review the exception structure of the Locks API to allow this to
                // not use runtime exceptions here.
                throw new org.neo4j.graphdb.TransactionFailureException( "Failed to acquire lock in cluster: " + e.getMessage(), e );
            }
            initialized = true;
        }
    }

    private RequestContext newRequestContextFor( Locks.Client client )
    {
        return requestContextFactory.newRequestContext( client.getLockSessionId() );
    }

    private UnsupportedOperationException newUnsupportedDirectTryLockUsageException()
    {
        return new UnsupportedOperationException( "At the time of adding \"try lock\" semantics there was no usage of " +
                getClass().getSimpleName() + " calling it directly. It was designed to be called on a local " +
                LockManager.class.getSimpleName() + " delegated to from within the waiting version" );
    }
}


File: enterprise/ha/src/test/java/org/neo4j/kernel/ha/cluster/HighAvailabilityMemberStateMachineTest.java
/*
 * Copyright (c) 2002-2015 "Neo Technology,"
 * Network Engine for Objects in Lund AB [http://neotechnology.com]
 *
 * This file is part of Neo4j.
 *
 * Neo4j is free software: you can redistribute it and/or modify
 * it under the terms of the GNU Affero General Public License as
 * published by the Free Software Foundation, either version 3 of the
 * License, or (at your option) any later version.
 *
 * This program is distributed in the hope that it will be useful,
 * but WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
 * GNU Affero General Public License for more details.
 *
 * You should have received a copy of the GNU Affero General Public License
 * along with this program. If not, see <http://www.gnu.org/licenses/>.
 */
package org.neo4j.kernel.ha.cluster;

import java.net.URI;
import java.util.HashSet;
import java.util.LinkedList;
import java.util.List;
import java.util.Set;

import org.junit.Test;
import org.mockito.Matchers;
import org.mockito.invocation.InvocationOnMock;
import org.mockito.stubbing.Answer;

import org.neo4j.cluster.InstanceId;
import org.neo4j.cluster.member.ClusterMemberEvents;
import org.neo4j.cluster.member.ClusterMemberListener;
import org.neo4j.cluster.protocol.election.Election;
import org.neo4j.kernel.AvailabilityGuard;
import org.neo4j.kernel.ha.cluster.member.ClusterMember;
import org.neo4j.kernel.ha.cluster.member.ClusterMembers;
import org.neo4j.kernel.impl.store.StoreId;
import org.neo4j.logging.NullLogProvider;

import static org.hamcrest.CoreMatchers.equalTo;
import static org.hamcrest.CoreMatchers.is;
import static org.junit.Assert.assertThat;
import static org.mockito.Mockito.any;
import static org.mockito.Mockito.doAnswer;
import static org.mockito.Mockito.mock;
import static org.mockito.Mockito.times;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.when;

import static org.neo4j.kernel.ha.cluster.HighAvailabilityModeSwitcher.MASTER;
import static org.neo4j.kernel.ha.cluster.HighAvailabilityModeSwitcher.SLAVE;

public class HighAvailabilityMemberStateMachineTest
{
    @Test
    public void shouldStartFromPending() throws Exception
    {
        // Given
        HighAvailabilityMemberContext context = mock( HighAvailabilityMemberContext.class );
        AvailabilityGuard guard = mock( AvailabilityGuard.class );
        ClusterMembers members = mock( ClusterMembers.class );
        ClusterMemberEvents events = mock( ClusterMemberEvents.class );
        Election election = mock( Election.class );
        HighAvailabilityMemberStateMachine toTest =
                new HighAvailabilityMemberStateMachine( context, guard, members, events, election, NullLogProvider.getInstance() );

        // Then
        assertThat( toTest.getCurrentState(), equalTo( HighAvailabilityMemberState.PENDING ) );
    }

    @Test
    public void shouldMoveToToMasterFromPendingOnMasterElectedForItself() throws Throwable
    {
        // Given
        InstanceId me = new InstanceId( 1 );
        HighAvailabilityMemberContext context = new SimpleHighAvailabilityMemberContext( me, false );
        AvailabilityGuard guard = mock( AvailabilityGuard.class );
        ClusterMembers members = mock( ClusterMembers.class );
        ClusterMemberEvents events = mock( ClusterMemberEvents.class );

        final Set<ClusterMemberListener> listener = new HashSet<>();

        doAnswer( new Answer()
        {
            @Override
            public Object answer( InvocationOnMock invocation ) throws Throwable
            {
                listener.add( (ClusterMemberListener) invocation.getArguments()[0] );
                return null;
            }

        } ).when( events ).addClusterMemberListener( Matchers.<ClusterMemberListener>any() );

        Election election = mock( Election.class );
        HighAvailabilityMemberStateMachine toTest =
                new HighAvailabilityMemberStateMachine( context, guard, members, events, election, NullLogProvider.getInstance() );
        toTest.init();
        ClusterMemberListener theListener = listener.iterator().next();

        // When
        theListener.coordinatorIsElected( me );

        // Then
        assertThat( listener.size(), equalTo( 1 ) ); // Sanity check.
        assertThat( toTest.getCurrentState(), equalTo( HighAvailabilityMemberState.TO_MASTER ) );
    }

    @Test
    public void shouldRemainToPendingOnMasterElectedForSomeoneElse() throws Throwable
    {
        // Given
        InstanceId me = new InstanceId( 1 );
        HighAvailabilityMemberContext context = new SimpleHighAvailabilityMemberContext( me, false );
        AvailabilityGuard guard = mock( AvailabilityGuard.class );
        ClusterMembers members = mock( ClusterMembers.class );
        ClusterMemberEvents events = mock( ClusterMemberEvents.class );

        final Set<ClusterMemberListener> listener = new HashSet<>();

        doAnswer( new Answer()
        {
            @Override
            public Object answer( InvocationOnMock invocation ) throws Throwable
            {
                listener.add( (ClusterMemberListener) invocation.getArguments()[0] );
                return null;
            }

        } ).when( events ).addClusterMemberListener( Matchers.<ClusterMemberListener>any() );

        Election election = mock( Election.class );
        HighAvailabilityMemberStateMachine toTest =
                new HighAvailabilityMemberStateMachine( context, guard, members, events, election, NullLogProvider.getInstance() );
        toTest.init();
        ClusterMemberListener theListener = listener.iterator().next();

        // When
        theListener.coordinatorIsElected( new InstanceId( 2 ) );

        // Then
        assertThat( listener.size(), equalTo( 1 ) ); // Sanity check.
        assertThat( toTest.getCurrentState(), equalTo( HighAvailabilityMemberState.PENDING ) );
    }

    @Test
    public void shouldSwitchToToSlaveOnMasterAvailableForSomeoneElse() throws Throwable
    {
        // Given
        InstanceId me = new InstanceId( 1 );
        HighAvailabilityMemberContext context = new SimpleHighAvailabilityMemberContext( me, false );
        AvailabilityGuard guard = mock( AvailabilityGuard.class );
        ClusterMembers members = mock( ClusterMembers.class );
        ClusterMemberEvents events = mock( ClusterMemberEvents.class );

        final Set<ClusterMemberListener> listener = new HashSet<>();

        doAnswer( new Answer()
        {
            @Override
            public Object answer( InvocationOnMock invocation ) throws Throwable
            {
                listener.add( (ClusterMemberListener) invocation.getArguments()[0] );
                return null;
            }

        } ).when( events ).addClusterMemberListener( Matchers.<ClusterMemberListener>any() );

        Election election = mock( Election.class );
        HighAvailabilityMemberStateMachine toTest =
                new HighAvailabilityMemberStateMachine( context, guard, members, events, election, NullLogProvider.getInstance() );
        toTest.init();
        ClusterMemberListener theListener = listener.iterator().next();
        HAStateChangeListener probe = new HAStateChangeListener();
        toTest.addHighAvailabilityMemberListener( probe );

        // When
        theListener.memberIsAvailable( MASTER, new InstanceId( 2 ), URI.create( "ha://whatever" ), StoreId.DEFAULT );

        // Then
        assertThat( listener.size(), equalTo( 1 ) ); // Sanity check.
        assertThat( toTest.getCurrentState(), equalTo( HighAvailabilityMemberState.TO_SLAVE ) );
        assertThat( probe.masterIsAvailable, is( true ) );
    }

    @Test
    public void whenInMasterStateLosingQuorumShouldPutInPending() throws Throwable
    {
        // Given
        InstanceId me = new InstanceId( 1 );
        InstanceId other = new InstanceId( 2 );
        HighAvailabilityMemberContext context = new SimpleHighAvailabilityMemberContext( me, false );
        AvailabilityGuard guard = mock( AvailabilityGuard.class );
        ClusterMembers members = mock( ClusterMembers.class );
        ClusterMemberEvents events = mock( ClusterMemberEvents.class );

        List<ClusterMember> membersList = new LinkedList<>();
        // we cannot set outside of the package the isAlive to return false. So do it with a mock
        ClusterMember otherMemberMock = mock( ClusterMember.class );
        when ( otherMemberMock.getInstanceId() ).thenReturn( other );
        when( otherMemberMock.isAlive() ).thenReturn( false );
        membersList.add( otherMemberMock );

        membersList.add( new ClusterMember( me ) );
        when( members.getMembers() ).thenReturn( membersList );

        final Set<ClusterMemberListener> listener = new HashSet<>();

        doAnswer( new Answer()
        {
            @Override
            public Object answer( InvocationOnMock invocation ) throws Throwable
            {
                listener.add( (ClusterMemberListener) invocation.getArguments()[0] );
                return null;
            }

        } ).when( events ).addClusterMemberListener( Matchers.<ClusterMemberListener>any() );

        Election election = mock( Election.class );
        HighAvailabilityMemberStateMachine toTest =
                new HighAvailabilityMemberStateMachine( context, guard, members, events, election, NullLogProvider.getInstance() );
        toTest.init();
        ClusterMemberListener theListener = listener.iterator().next();
        HAStateChangeListener probe = new HAStateChangeListener();
        toTest.addHighAvailabilityMemberListener( probe );

        // Send it to MASTER
        theListener.coordinatorIsElected( me );
        theListener.memberIsAvailable( MASTER, me, URI.create("ha://whatever"), StoreId.DEFAULT );

        assertThat( toTest.getCurrentState(), equalTo( HighAvailabilityMemberState.MASTER) );

        // When
        theListener.memberIsFailed( new InstanceId( 2 ) );

        // Then
        assertThat( listener.size(), equalTo( 1 ) ); // Sanity check.
        assertThat( toTest.getCurrentState(), equalTo( HighAvailabilityMemberState.PENDING ) );
        assertThat( probe.instanceStops, is( true ) );
        verify(guard, times(2)).deny( any( AvailabilityGuard.AvailabilityRequirement.class) );
    }

    @Test
    public void whenInSlaveStateLosingQuorumShouldPutInPending() throws Throwable
    {
        // Given
        InstanceId me = new InstanceId( 1 );
        InstanceId other = new InstanceId( 2 );
        HighAvailabilityMemberContext context = new SimpleHighAvailabilityMemberContext( me, false );
        AvailabilityGuard guard = mock( AvailabilityGuard.class );
        ClusterMembers members = mock( ClusterMembers.class );
        ClusterMemberEvents events = mock( ClusterMemberEvents.class );

        List<ClusterMember> membersList = new LinkedList<>();
        // we cannot set outside of the package the isAlive to return false. So do it with a mock
        ClusterMember otherMemberMock = mock( ClusterMember.class );
        when ( otherMemberMock.getInstanceId() ).thenReturn( other );
        when( otherMemberMock.isAlive() ).thenReturn( false );
        membersList.add( otherMemberMock );

        membersList.add( new ClusterMember( me ) );
        when( members.getMembers() ).thenReturn( membersList );

        final Set<ClusterMemberListener> listener = new HashSet<>();

        doAnswer( new Answer()
        {
            @Override
            public Object answer( InvocationOnMock invocation ) throws Throwable
            {
                listener.add( (ClusterMemberListener) invocation.getArguments()[0] );
                return null;
            }

        } ).when( events ).addClusterMemberListener( Matchers.<ClusterMemberListener>any() );

        Election election = mock( Election.class );
        HighAvailabilityMemberStateMachine toTest =
                new HighAvailabilityMemberStateMachine( context, guard, members, events, election, NullLogProvider.getInstance() );
        toTest.init();
        ClusterMemberListener theListener = listener.iterator().next();
        HAStateChangeListener probe = new HAStateChangeListener();
        toTest.addHighAvailabilityMemberListener( probe );

        // Send it to MASTER
        theListener.memberIsAvailable( MASTER, other, URI.create( "ha://whatever" ), StoreId.DEFAULT );
        theListener.memberIsAvailable( SLAVE, me, URI.create( "ha://whatever2" ), StoreId.DEFAULT );

        assertThat( toTest.getCurrentState(), equalTo( HighAvailabilityMemberState.SLAVE) );

        // When
        theListener.memberIsFailed( new InstanceId( 2 ) );

        // Then
        assertThat( listener.size(), equalTo( 1 ) ); // Sanity check.
        assertThat( toTest.getCurrentState(), equalTo( HighAvailabilityMemberState.PENDING ) );
        assertThat( probe.instanceStops, is( true ) );
        verify(guard, times(2)).deny( any( AvailabilityGuard.AvailabilityRequirement.class) );
    }

    @Test
    public void whenInToMasterStateLosingQuorumShouldPutInPending() throws Throwable
    {
        // Given
        InstanceId me = new InstanceId( 1 );
        InstanceId other = new InstanceId( 2 );
        HighAvailabilityMemberContext context = new SimpleHighAvailabilityMemberContext( me, false );
        AvailabilityGuard guard = mock( AvailabilityGuard.class );
        ClusterMembers members = mock( ClusterMembers.class );
        ClusterMemberEvents events = mock( ClusterMemberEvents.class );

        List<ClusterMember> membersList = new LinkedList<>();
        // we cannot set outside of the package the isAlive to return false. So do it with a mock
        ClusterMember otherMemberMock = mock( ClusterMember.class );
        when ( otherMemberMock.getInstanceId() ).thenReturn( other );
        when( otherMemberMock.isAlive() ).thenReturn( false );
        membersList.add( otherMemberMock );

        membersList.add( new ClusterMember( me ) );
        when( members.getMembers() ).thenReturn( membersList );

        final Set<ClusterMemberListener> listener = new HashSet<>();

        doAnswer( new Answer()
        {
            @Override
            public Object answer( InvocationOnMock invocation ) throws Throwable
            {
                listener.add( (ClusterMemberListener) invocation.getArguments()[0] );
                return null;
            }

        } ).when( events ).addClusterMemberListener( Matchers.<ClusterMemberListener>any() );

        Election election = mock( Election.class );
        HighAvailabilityMemberStateMachine toTest =
                new HighAvailabilityMemberStateMachine( context, guard, members, events, election, NullLogProvider.getInstance() );
        toTest.init();
        ClusterMemberListener theListener = listener.iterator().next();
        HAStateChangeListener probe = new HAStateChangeListener();
        toTest.addHighAvailabilityMemberListener( probe );

        // Send it to MASTER
        theListener.coordinatorIsElected( me );

        assertThat( toTest.getCurrentState(), equalTo( HighAvailabilityMemberState.TO_MASTER) );

        // When
        theListener.memberIsFailed( new InstanceId( 2 ) );

        // Then
        assertThat( listener.size(), equalTo( 1 ) ); // Sanity check.
        assertThat( toTest.getCurrentState(), equalTo( HighAvailabilityMemberState.PENDING ) );
        assertThat( probe.instanceStops, is( true ) );
        verify(guard, times(1)).deny( any( AvailabilityGuard.AvailabilityRequirement.class) );
    }

    @Test
    public void whenInToSlaveStateLosingQuorumShouldPutInPending() throws Throwable
    {
        // Given
        InstanceId me = new InstanceId( 1 );
        InstanceId other = new InstanceId( 2 );
        HighAvailabilityMemberContext context = new SimpleHighAvailabilityMemberContext( me, false );
        AvailabilityGuard guard = mock( AvailabilityGuard.class );
        ClusterMembers members = mock( ClusterMembers.class );
        ClusterMemberEvents events = mock( ClusterMemberEvents.class );

        List<ClusterMember> membersList = new LinkedList<>();
        // we cannot set outside of the package the isAlive to return false. So do it with a mock
        ClusterMember otherMemberMock = mock( ClusterMember.class );
        when ( otherMemberMock.getInstanceId() ).thenReturn( other );
        when( otherMemberMock.isAlive() ).thenReturn( false );
        membersList.add( otherMemberMock );

        membersList.add( new ClusterMember( me ) );
        when( members.getMembers() ).thenReturn( membersList );

        final Set<ClusterMemberListener> listener = new HashSet<>();

        doAnswer( new Answer()
        {
            @Override
            public Object answer( InvocationOnMock invocation ) throws Throwable
            {
                listener.add( (ClusterMemberListener) invocation.getArguments()[0] );
                return null;
            }

        } ).when( events ).addClusterMemberListener( Matchers.<ClusterMemberListener>any() );

        Election election = mock( Election.class );
        HighAvailabilityMemberStateMachine toTest =
                new HighAvailabilityMemberStateMachine( context, guard, members, events, election, NullLogProvider.getInstance() );
        toTest.init();
        ClusterMemberListener theListener = listener.iterator().next();
        HAStateChangeListener probe = new HAStateChangeListener();
        toTest.addHighAvailabilityMemberListener( probe );

        // Send it to MASTER
        theListener.memberIsAvailable( MASTER, other, URI.create("ha://whatever"), StoreId.DEFAULT );

        assertThat( toTest.getCurrentState(), equalTo( HighAvailabilityMemberState.TO_SLAVE) );

        // When
        theListener.memberIsFailed( new InstanceId( 2 ) );

        // Then
        assertThat( listener.size(), equalTo( 1 ) ); // Sanity check.
        assertThat( toTest.getCurrentState(), equalTo( HighAvailabilityMemberState.PENDING ) );
        assertThat( probe.instanceStops, is( true ) );
        verify(guard, times(1)).deny( any( AvailabilityGuard.AvailabilityRequirement.class) );
    }

    @Test
    public void whenSlaveOnlyIsElectedStayInPending() throws Throwable
    {
        // Given
        InstanceId me = new InstanceId( 1 );
        HighAvailabilityMemberContext context = new SimpleHighAvailabilityMemberContext( me, true );
        AvailabilityGuard guard = mock( AvailabilityGuard.class );
        ClusterMembers members = mock( ClusterMembers.class );
        ClusterMemberEvents events = mock( ClusterMemberEvents.class );

        final Set<ClusterMemberListener> listener = new HashSet<>();

        doAnswer( new Answer()
        {
            @Override
            public Object answer( InvocationOnMock invocation ) throws Throwable
            {
                listener.add( (ClusterMemberListener) invocation.getArguments()[0] );
                return null;
            }

        } ).when( events ).addClusterMemberListener( Matchers.<ClusterMemberListener>any() );

        Election election = mock( Election.class );
        HighAvailabilityMemberStateMachine toTest =
                new HighAvailabilityMemberStateMachine( context, guard, members, events, election, NullLogProvider.getInstance() );

        toTest.init();

        ClusterMemberListener theListener = listener.iterator().next();

        // When
        theListener.coordinatorIsElected( me );

        // Then
        assertThat( toTest.getCurrentState(), equalTo( HighAvailabilityMemberState.PENDING ) );

    }

    private static final class HAStateChangeListener implements HighAvailabilityMemberListener
    {
        boolean masterIsElected = false;
        boolean masterIsAvailable = false;
        boolean slaveIsAvailable = false;
        boolean instanceStops = false;
        HighAvailabilityMemberChangeEvent lastEvent = null;

        @Override
        public void masterIsElected( HighAvailabilityMemberChangeEvent event )
        {
            masterIsElected = true;
            masterIsAvailable = false;
            slaveIsAvailable = false;
            instanceStops = false;
            lastEvent = event;
        }

        @Override
        public void masterIsAvailable( HighAvailabilityMemberChangeEvent event )
        {
            masterIsElected = false;
            masterIsAvailable = true;
            slaveIsAvailable = false;
            instanceStops = false;
            lastEvent = event;
        }

        @Override
        public void slaveIsAvailable( HighAvailabilityMemberChangeEvent event )
        {
            masterIsElected = false;
            masterIsAvailable = false;
            slaveIsAvailable = true;
            instanceStops = false;
            lastEvent = event;
        }

        @Override
        public void instanceStops( HighAvailabilityMemberChangeEvent event )
        {
            masterIsElected = false;
            masterIsAvailable = false;
            slaveIsAvailable = false;
            instanceStops = true;
            lastEvent = event;
        }
    }
}
