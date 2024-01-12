Refactoring Types: ['Pull Up Attribute']
hibernate/cache/internal/CacheDataDescriptionImpl.java
/*
 * Hibernate, Relational Persistence for Idiomatic Java
 *
 * License: GNU Lesser General Public License (LGPL), version 2.1 or later.
 * See the lgpl.txt file in the root directory or <http://www.gnu.org/licenses/lgpl-2.1.html>.
 */
package org.hibernate.cache.internal;

import java.util.Comparator;

import org.hibernate.cache.spi.CacheDataDescription;
import org.hibernate.mapping.Collection;
import org.hibernate.mapping.PersistentClass;
import org.hibernate.type.VersionType;

/**
 * Standard CacheDataDescription implementation.
 *
 * @author Steve Ebersole
 */
public class CacheDataDescriptionImpl implements CacheDataDescription {
	private final boolean mutable;
	private final boolean versioned;
	private final Comparator versionComparator;

	/**
	 * Constructs a CacheDataDescriptionImpl instance.  Generally speaking, code should use one of the
	 * overloaded {@link #decode} methods rather than direct instantiation.
	 *
	 * @param mutable Is the described data mutable?
	 * @param versioned Is the described data versioned?
	 * @param versionComparator The described data's version value comparator (if versioned).
	 */
	public CacheDataDescriptionImpl(boolean mutable, boolean versioned, Comparator versionComparator) {
		this.mutable = mutable;
		this.versioned = versioned;
		this.versionComparator = versionComparator;
	}

	@Override
	public boolean isMutable() {
		return mutable;
	}

	@Override
	public boolean isVersioned() {
		return versioned;
	}

	@Override
	public Comparator getVersionComparator() {
		return versionComparator;
	}

	/**
	 * Builds a CacheDataDescriptionImpl from the mapping model of an entity class.
	 *
	 * @param model The mapping model.
	 *
	 * @return The constructed CacheDataDescriptionImpl
	 */
	public static CacheDataDescriptionImpl decode(PersistentClass model) {
		return new CacheDataDescriptionImpl(
				model.isMutable(),
				model.isVersioned(),
				model.isVersioned()
						? ( (VersionType) model.getVersion().getType() ).getComparator()
						: null
		);
	}

	/**
	 * Builds a CacheDataDescriptionImpl from the mapping model of a collection
	 *
	 * @param model The mapping model.
	 *
	 * @return The constructed CacheDataDescriptionImpl
	 */
	public static CacheDataDescriptionImpl decode(Collection model) {
		return new CacheDataDescriptionImpl(
				model.isMutable(),
				model.getOwner().isVersioned(),
				model.getOwner().isVersioned()
						? ( (VersionType) model.getOwner().getVersion().getType() ).getComparator()
						: null
		);
	}

}


File: hibernate-core/src/main/java/org/hibernate/cache/internal/DefaultCacheKeysFactory.java
/*
 * Hibernate, Relational Persistence for Idiomatic Java
 *
 * License: GNU Lesser General Public License (LGPL), version 2.1 or later.
 * See the lgpl.txt file in the root directory or <http://www.gnu.org/licenses/lgpl-2.1.html>.
 */
package org.hibernate.cache.internal;

import org.hibernate.engine.spi.SessionFactoryImplementor;
import org.hibernate.engine.spi.SessionImplementor;
import org.hibernate.persister.collection.CollectionPersister;
import org.hibernate.persister.entity.EntityPersister;

/**
 * Second level cache providers now have the option to use custom key implementations.
 * This was done as the default key implementation is very generic and is quite
 * a large object to allocate in large quantities at runtime.
 * In some extreme cases, for example when the hit ratio is very low, this was making the efficiency
 * penalty vs its benefits tradeoff questionable.
 * <p/>
 * Depending on configuration settings there might be opportunities to
 * use simpler key implementations, for example when multi-tenancy is not being used to
 * avoid the tenant identifier, or when a cache instance is entirely dedicated to a single type
 * to use the primary id only, skipping the role or entity name.
 * <p/>
 * Even with multiple types sharing the same cache, their identifiers could be of the same
 * {@link org.hibernate.type.Type}; in this case the cache container could
 * use a single type reference to implement a custom equality function without having
 * to look it up on each equality check: that's a small optimisation but the
 * equality function is often invoked extremely frequently.
 * <p/>
 * Another reason is to make it more convenient to implement custom serialization protocols when the
 * implementation supports clustering.
 *
 * @see org.hibernate.type.Type#getHashCode(Object, SessionFactoryImplementor)
 * @see org.hibernate.type.Type#isEqual(Object, Object)
 * @author Sanne Grinovero
 * @since 5.0
 */
public class DefaultCacheKeysFactory {

	public static Object createCollectionKey(Object id, CollectionPersister persister, SessionFactoryImplementor factory, String tenantIdentifier) {
		return new OldCacheKeyImplementation( id, persister.getKeyType(), persister.getRole(), tenantIdentifier, factory );
	}

	public static Object createEntityKey(Object id, EntityPersister persister, SessionFactoryImplementor factory, String tenantIdentifier) {
		return new OldCacheKeyImplementation( id, persister.getIdentifierType(), persister.getRootEntityName(), tenantIdentifier, factory );
	}

	public static Object createNaturalIdKey(Object[] naturalIdValues, EntityPersister persister, SessionImplementor session) {
		return new OldNaturalIdCacheKey( naturalIdValues, persister, session );
	}

	public static Object getEntityId(Object cacheKey) {
		return ((OldCacheKeyImplementation) cacheKey).getId();
	}

	public static Object getCollectionId(Object cacheKey) {
		return ((OldCacheKeyImplementation) cacheKey).getId();
	}

	public static Object[] getNaturalIdValues(Object cacheKey) {
		return ((OldNaturalIdCacheKey) cacheKey).getNaturalIdValues();
	}
}


File: hibernate-core/src/main/java/org/hibernate/cache/internal/OldNaturalIdCacheKey.java
/*
 * Hibernate, Relational Persistence for Idiomatic Java
 *
 * License: GNU Lesser General Public License (LGPL), version 2.1 or later.
 * See the lgpl.txt file in the root directory or <http://www.gnu.org/licenses/lgpl-2.1.html>.
 */
package org.hibernate.cache.internal;

import java.io.IOException;
import java.io.ObjectInputStream;
import java.io.Serializable;
import java.util.Arrays;

import org.hibernate.engine.spi.SessionFactoryImplementor;
import org.hibernate.engine.spi.SessionImplementor;
import org.hibernate.internal.util.ValueHolder;
import org.hibernate.internal.util.compare.EqualsHelper;
import org.hibernate.persister.entity.EntityPersister;
import org.hibernate.type.EntityType;
import org.hibernate.type.Type;

/**
 * Defines a key for caching natural identifier resolutions into the second level cache.
 *
 * This was named org.hibernate.cache.spi.NaturalIdCacheKey in Hibernate until version 5.
 * Temporarily maintained as a reference while all components catch up with the refactoring to the caching interfaces.
 *
 * @author Eric Dalquist
 * @author Steve Ebersole
 *
 * @deprecated Cache implementation should provide optimized key.
 */
@Deprecated
public class OldNaturalIdCacheKey implements Serializable {
	private final Serializable[] naturalIdValues;
	private final String entityName;
	private final String tenantId;
	private final int hashCode;
	// "transient" is important here -- NaturalIdCacheKey needs to be Serializable
	private transient ValueHolder<String> toString;

	/**
	 * Construct a new key for a caching natural identifier resolutions into the second level cache.
	 *
	 * @param naturalIdValues The naturalIdValues associated with the cached data
	 * @param persister The persister for the entity
	 * @param session The originating session
	 */
	public OldNaturalIdCacheKey(
			final Object[] naturalIdValues,
			final EntityPersister persister,
			final SessionImplementor session) {

		this.entityName = persister.getRootEntityName();
		this.tenantId = session.getTenantIdentifier();

		this.naturalIdValues = new Serializable[naturalIdValues.length];

		final SessionFactoryImplementor factory = session.getFactory();
		final int[] naturalIdPropertyIndexes = persister.getNaturalIdentifierProperties();
		final Type[] propertyTypes = persister.getPropertyTypes();

		final int prime = 31;
		int result = 1;
		result = prime * result + ( ( this.entityName == null ) ? 0 : this.entityName.hashCode() );
		result = prime * result + ( ( this.tenantId == null ) ? 0 : this.tenantId.hashCode() );
		for ( int i = 0; i < naturalIdValues.length; i++ ) {
			final int naturalIdPropertyIndex = naturalIdPropertyIndexes[i];
			final Type type = propertyTypes[naturalIdPropertyIndex];
			final Object value = naturalIdValues[i];

			result = prime * result + (value != null ? type.getHashCode( value, factory ) : 0);

			// The natural id may not be fully resolved in some situations.  See HHH-7513 for one of them
			// (re-attaching a mutable natural id uses a database snapshot and hydration does not resolve associations).
			// TODO: The snapshot should probably be revisited at some point.  Consider semi-resolving, hydrating, etc.
			if (type instanceof EntityType && type.getSemiResolvedType( factory ).getReturnedClass().isInstance( value )) {
				this.naturalIdValues[i] = (Serializable) value;
			}
			else {
				this.naturalIdValues[i] = type.disassemble( value, session, null );
			}
		}

		this.hashCode = result;
		initTransients();
	}

	private void initTransients() {
		this.toString = new ValueHolder<String>(
				new ValueHolder.DeferredInitializer<String>() {
					@Override
					public String initialize() {
						//Complex toString is needed as naturalIds for entities are not simply based on a single value like primary keys
						//the only same way to differentiate the keys is to included the disassembled values in the string.
						final StringBuilder toStringBuilder = new StringBuilder( entityName ).append( "##NaturalId[" );
						for ( int i = 0; i < naturalIdValues.length; i++ ) {
							toStringBuilder.append( naturalIdValues[i] );
							if ( i + 1 < naturalIdValues.length ) {
								toStringBuilder.append( ", " );
							}
						}
						toStringBuilder.append( "]" );

						return toStringBuilder.toString();
					}
				}
		);
	}

	@SuppressWarnings( {"UnusedDeclaration"})
	public String getEntityName() {
		return entityName;
	}

	@SuppressWarnings( {"UnusedDeclaration"})
	public String getTenantId() {
		return tenantId;
	}

	@SuppressWarnings( {"UnusedDeclaration"})
	public Serializable[] getNaturalIdValues() {
		return naturalIdValues;
	}

	@Override
	public String toString() {
		return toString.getValue();
	}

	@Override
	public int hashCode() {
		return this.hashCode;
	}

	@Override
	public boolean equals(Object o) {
		if ( o == null ) {
			return false;
		}
		if ( this == o ) {
			return true;
		}

		if ( hashCode != o.hashCode() || !( o instanceof OldNaturalIdCacheKey ) ) {
			//hashCode is part of this check since it is pre-calculated and hash must match for equals to be true
			return false;
		}

		final OldNaturalIdCacheKey other = (OldNaturalIdCacheKey) o;
		return EqualsHelper.equals( entityName, other.entityName )
				&& EqualsHelper.equals( tenantId, other.tenantId )
				&& Arrays.deepEquals( this.naturalIdValues, other.naturalIdValues );
	}

	private void readObject(ObjectInputStream ois)
			throws ClassNotFoundException, IOException {
		ois.defaultReadObject();
		initTransients();
	}
}


File: hibernate-core/src/main/java/org/hibernate/cache/spi/CacheDataDescription.java
/*
 * Hibernate, Relational Persistence for Idiomatic Java
 *
 * License: GNU Lesser General Public License (LGPL), version 2.1 or later.
 * See the lgpl.txt file in the root directory or <http://www.gnu.org/licenses/lgpl-2.1.html>.
 */
package org.hibernate.cache.spi;

import java.util.Comparator;

/**
 * Describes attributes regarding the type of data to be cached.
 *
 * @author Steve Ebersole
 */
public interface CacheDataDescription {
	/**
	 * Is the data marked as being mutable?
	 *
	 * @return {@code true} if the data is mutable; {@code false} otherwise.
	 */
	public boolean isMutable();

	/**
	 * Is the data to be cached considered versioned?
	 *
	 * If {@code true}, it is illegal for {@link #getVersionComparator} to return {@code null}.
	 *
	 * @return {@code true} if the data is versioned; {@code false} otherwise.
	 */
	public boolean isVersioned();

	/**
	 * Get the comparator used to compare two different version values.  May return {@code null} <b>if</b>
	 * {@link #isVersioned()} returns false.
	 *
	 * @return The comparator for versions, or {@code null}
	 */
	public Comparator getVersionComparator();
}


File: hibernate-core/src/test/java/org/hibernate/cache/spi/NaturalIdCacheKeyTest.java
/*
 * Hibernate, Relational Persistence for Idiomatic Java
 *
 * License: GNU Lesser General Public License (LGPL), version 2.1 or later.
 * See the lgpl.txt file in the root directory or <http://www.gnu.org/licenses/lgpl-2.1.html>.
 */
package org.hibernate.cache.spi;

import java.io.ByteArrayInputStream;
import java.io.ByteArrayOutputStream;
import java.io.ObjectInputStream;
import java.io.ObjectOutputStream;

import org.hibernate.cache.internal.DefaultCacheKeysFactory;
import org.hibernate.cache.internal.OldNaturalIdCacheKey;
import org.hibernate.engine.spi.SessionFactoryImplementor;
import org.hibernate.engine.spi.SessionImplementor;
import org.hibernate.persister.entity.EntityPersister;
import org.hibernate.type.Type;
import org.junit.Test;
import org.mockito.invocation.InvocationOnMock;
import org.mockito.stubbing.Answer;

import static junit.framework.Assert.assertEquals;
import static org.junit.Assert.assertArrayEquals;
import static org.mockito.Matchers.anyObject;
import static org.mockito.Matchers.eq;
import static org.mockito.Mockito.mock;
import static org.mockito.Mockito.when;

public class NaturalIdCacheKeyTest {
    @Test
    public void testSerializationRoundTrip() throws Exception {
        final EntityPersister entityPersister = mock(EntityPersister.class);
        final SessionImplementor sessionImplementor = mock(SessionImplementor.class);
        final SessionFactoryImplementor sessionFactoryImplementor = mock(SessionFactoryImplementor.class);
        final Type mockType = mock(Type.class);
        
        when (entityPersister.getRootEntityName()).thenReturn("EntityName");
        
        when(sessionImplementor.getFactory()).thenReturn(sessionFactoryImplementor);
        
        when(entityPersister.getNaturalIdentifierProperties()).thenReturn(new int[] {0, 1, 2});
        when(entityPersister.getPropertyTypes()).thenReturn(new Type[] {
                mockType,
                mockType,
                mockType
        });
        
        when(mockType.getHashCode(anyObject(), eq(sessionFactoryImplementor))).thenAnswer(new Answer<Object>() {
            @Override
            public Object answer(InvocationOnMock invocation) throws Throwable {
                return invocation.getArguments()[0].hashCode();
            }
        });
        
        when(mockType.disassemble(anyObject(), eq(sessionImplementor), eq(null))).thenAnswer(new Answer<Object>() {
            @Override
            public Object answer(InvocationOnMock invocation) throws Throwable {
                return invocation.getArguments()[0];
            }
        });

        final OldNaturalIdCacheKey key = (OldNaturalIdCacheKey) DefaultCacheKeysFactory.createNaturalIdKey( new Object[] {"a", "b", "c"}, entityPersister, sessionImplementor );
        
        final ByteArrayOutputStream baos = new ByteArrayOutputStream();
        final ObjectOutputStream oos = new ObjectOutputStream(baos);
        oos.writeObject(key);
        
        final ObjectInputStream ois = new ObjectInputStream(new ByteArrayInputStream(baos.toByteArray()));
        final OldNaturalIdCacheKey keyClone = (OldNaturalIdCacheKey) ois.readObject();
        
        assertEquals(key, keyClone);
        assertEquals(key.hashCode(), keyClone.hashCode());
        assertEquals(key.toString(), keyClone.toString());
        assertEquals(key.getEntityName(), keyClone.getEntityName());
        assertArrayEquals(key.getNaturalIdValues(), keyClone.getNaturalIdValues());
        assertEquals(key.getTenantId(), keyClone.getTenantId());
        
    }
}


File: hibernate-infinispan/src/main/java/org/hibernate/cache/infinispan/InfinispanRegionFactory.java
/*
 * Hibernate, Relational Persistence for Idiomatic Java
 *
 * License: GNU Lesser General Public License (LGPL), version 2.1 or later.
 * See the lgpl.txt file in the root directory or <http://www.gnu.org/licenses/lgpl-2.1.html>.
 */
package org.hibernate.cache.infinispan;

import java.io.IOException;
import java.io.InputStream;
import java.util.ArrayList;
import java.util.Collections;
import java.util.Enumeration;
import java.util.HashMap;
import java.util.HashSet;
import java.util.List;
import java.util.Map;
import java.util.Properties;
import java.util.Set;
import java.util.concurrent.TimeUnit;

import org.hibernate.boot.registry.classloading.spi.ClassLoaderService;
import org.hibernate.boot.spi.SessionFactoryOptions;
import org.hibernate.cache.CacheException;
import org.hibernate.cache.infinispan.collection.CollectionRegionImpl;
import org.hibernate.cache.infinispan.entity.EntityRegionImpl;
import org.hibernate.cache.infinispan.impl.BaseRegion;
import org.hibernate.cache.infinispan.naturalid.NaturalIdRegionImpl;
import org.hibernate.cache.infinispan.query.QueryResultsRegionImpl;
import org.hibernate.cache.infinispan.timestamp.ClusteredTimestampsRegionImpl;
import org.hibernate.cache.infinispan.timestamp.TimestampTypeOverrides;
import org.hibernate.cache.infinispan.timestamp.TimestampsRegionImpl;
import org.hibernate.cache.infinispan.tm.HibernateTransactionManagerLookup;
import org.hibernate.cache.infinispan.util.CacheCommandFactory;
import org.hibernate.cache.infinispan.util.Caches;
import org.hibernate.cache.spi.CacheDataDescription;
import org.hibernate.cache.spi.CollectionRegion;
import org.hibernate.cache.spi.EntityRegion;
import org.hibernate.cache.spi.NaturalIdRegion;
import org.hibernate.cache.spi.QueryResultsRegion;
import org.hibernate.cache.spi.RegionFactory;
import org.hibernate.cache.spi.TimestampsRegion;
import org.hibernate.cache.spi.access.AccessType;
import org.hibernate.internal.util.config.ConfigurationHelper;
import org.hibernate.service.ServiceRegistry;

import org.infinispan.AdvancedCache;
import org.infinispan.commands.module.ModuleCommandFactory;
import org.infinispan.commons.util.FileLookup;
import org.infinispan.commons.util.FileLookupFactory;
import org.infinispan.commons.util.Util;
import org.infinispan.configuration.cache.CacheMode;
import org.infinispan.configuration.cache.Configuration;
import org.infinispan.configuration.cache.ConfigurationBuilder;
import org.infinispan.configuration.parsing.ConfigurationBuilderHolder;
import org.infinispan.configuration.parsing.ParserRegistry;
import org.infinispan.factories.GlobalComponentRegistry;
import org.infinispan.manager.DefaultCacheManager;
import org.infinispan.manager.EmbeddedCacheManager;
import org.infinispan.transaction.TransactionMode;
import org.infinispan.transaction.lookup.GenericTransactionManagerLookup;
import org.infinispan.util.concurrent.IsolationLevel;
import org.infinispan.util.logging.Log;
import org.infinispan.util.logging.LogFactory;

/**
 * A {@link RegionFactory} for <a href="http://www.jboss.org/infinispan">Infinispan</a>-backed cache
 * regions.
 *
 * @author Chris Bredesen
 * @author Galder Zamarreño
 * @since 3.5
 */
public class InfinispanRegionFactory implements RegionFactory {
	private static final Log log = LogFactory.getLog( InfinispanRegionFactory.class );

	private static final String PREFIX = "hibernate.cache.infinispan.";

	private static final String CONFIG_SUFFIX = ".cfg";

	private static final String STRATEGY_SUFFIX = ".eviction.strategy";

	private static final String WAKE_UP_INTERVAL_SUFFIX = ".eviction.wake_up_interval";

	private static final String MAX_ENTRIES_SUFFIX = ".eviction.max_entries";

	private static final String LIFESPAN_SUFFIX = ".expiration.lifespan";

	private static final String MAX_IDLE_SUFFIX = ".expiration.max_idle";

//   private static final String STATISTICS_SUFFIX = ".statistics";

	/**
	 * Classpath or filesystem resource containing Infinispan configurations the factory should use.
	 *
	 * @see #DEF_INFINISPAN_CONFIG_RESOURCE
	 */
	public static final String INFINISPAN_CONFIG_RESOURCE_PROP = "hibernate.cache.infinispan.cfg";

   /**
    * Property name that controls whether Infinispan statistics are enabled.
    * The property value is expected to be a boolean true or false, and it
    * overrides statistic configuration in base Infinispan configuration,
    * if provided.
    */
	public static final String INFINISPAN_GLOBAL_STATISTICS_PROP = "hibernate.cache.infinispan.statistics";

	/**
	 * Property that controls whether Infinispan should interact with the
	 * transaction manager as a {@link javax.transaction.Synchronization} or as
	 * an XA resource. If the property is set to true, it will be a
	 * synchronization, otherwise an XA resource.
	 *
	 * @see #DEF_USE_SYNCHRONIZATION
	 */
	public static final String INFINISPAN_USE_SYNCHRONIZATION_PROP = "hibernate.cache.infinispan.use_synchronization";

	private static final String NATURAL_ID_KEY = "naturalid";

	/**
	 * Name of the configuration that should be used for natural id caches.
	 *
	 * @see #DEF_ENTITY_RESOURCE
	 */
	@SuppressWarnings("UnusedDeclaration")
	public static final String NATURAL_ID_CACHE_RESOURCE_PROP = PREFIX + NATURAL_ID_KEY + CONFIG_SUFFIX;

	private static final String ENTITY_KEY = "entity";

	/**
	 * Name of the configuration that should be used for entity caches.
	 *
	 * @see #DEF_ENTITY_RESOURCE
	 */
	public static final String ENTITY_CACHE_RESOURCE_PROP = PREFIX + ENTITY_KEY + CONFIG_SUFFIX;

	private static final String IMMUTABLE_ENTITY_KEY = "immutable-entity";

	/**
	 * Name of the configuration that should be used for immutable entity caches.
	 */
	public static final String IMMUTABLE_ENTITY_CACHE_RESOURCE_PROP = PREFIX + IMMUTABLE_ENTITY_KEY + CONFIG_SUFFIX;

	private static final String COLLECTION_KEY = "collection";

	/**
	 * Name of the configuration that should be used for collection caches.
	 * No default value, as by default we try to use the same Infinispan cache
	 * instance we use for entity caching.
	 *
	 * @see #ENTITY_CACHE_RESOURCE_PROP
	 * @see #DEF_ENTITY_RESOURCE
	 */
	@SuppressWarnings("UnusedDeclaration")
	public static final String COLLECTION_CACHE_RESOURCE_PROP = PREFIX + COLLECTION_KEY + CONFIG_SUFFIX;

	private static final String TIMESTAMPS_KEY = "timestamps";

	/**
	 * Name of the configuration that should be used for timestamp caches.
	 *
	 * @see #DEF_TIMESTAMPS_RESOURCE
	 */
	@SuppressWarnings("UnusedDeclaration")
	public static final String TIMESTAMPS_CACHE_RESOURCE_PROP = PREFIX + TIMESTAMPS_KEY + CONFIG_SUFFIX;

	private static final String QUERY_KEY = "query";

	/**
	 * Name of the configuration that should be used for query caches.
	 *
	 * @see #DEF_QUERY_RESOURCE
	 */
	public static final String QUERY_CACHE_RESOURCE_PROP = PREFIX + QUERY_KEY + CONFIG_SUFFIX;

	/**
	 * Default value for {@link #INFINISPAN_CONFIG_RESOURCE_PROP}. Specifies the "infinispan-configs.xml" file in this package.
	 */
	public static final String DEF_INFINISPAN_CONFIG_RESOURCE = "org/hibernate/cache/infinispan/builder/infinispan-configs.xml";

	/**
	 * Default value for {@link #ENTITY_CACHE_RESOURCE_PROP}.
	 */
	public static final String DEF_ENTITY_RESOURCE = "entity";

	/**
	 * Default value for {@link #IMMUTABLE_ENTITY_CACHE_RESOURCE_PROP}.
	 */
	public static final String DEF_IMMUTABLE_ENTITY_RESOURCE = "immutable-entity";

	/**
	 * Default value for {@link #TIMESTAMPS_CACHE_RESOURCE_PROP}.
	 */
	public static final String DEF_TIMESTAMPS_RESOURCE = "timestamps";

	/**
	 * Default value for {@link #QUERY_CACHE_RESOURCE_PROP}.
	 */
	public static final String DEF_QUERY_RESOURCE = "local-query";

	/**
	 * Default value for {@link #INFINISPAN_USE_SYNCHRONIZATION_PROP}.
	 */
	public static final boolean DEF_USE_SYNCHRONIZATION = true;

	/**
	 * Name of the pending puts cache.
	 */
	public static final String PENDING_PUTS_CACHE_NAME = "pending-puts";

	private EmbeddedCacheManager manager;

	private final Map<String, TypeOverrides> typeOverrides = new HashMap<String, TypeOverrides>();

	private final Set<String> definedConfigurations = new HashSet<String>();

	private org.infinispan.transaction.lookup.TransactionManagerLookup transactionManagerlookup;

	private List<String> regionNames = new ArrayList<String>();

	/**
	 * Create a new instance using the default configuration.
	 */
	public InfinispanRegionFactory() {
	}

	/**
	 * Create a new instance using conifguration properties in <code>props</code>.
	 *
	 * @param props Environmental properties; currently unused.
	 */
	@SuppressWarnings("UnusedParameters")
	public InfinispanRegionFactory(Properties props) {
	}

	@Override
	public CollectionRegion buildCollectionRegion(
			String regionName,
			Properties properties,
			CacheDataDescription metadata) throws CacheException {
		if ( log.isDebugEnabled() ) {
			log.debug( "Building collection cache region [" + regionName + "]" );
		}
		final AdvancedCache cache = getCache( regionName, COLLECTION_KEY, properties );
		final CollectionRegionImpl region = new CollectionRegionImpl( cache, regionName, metadata, this );
		startRegion( region, regionName );
		return region;
	}

	@Override
	public EntityRegion buildEntityRegion(String regionName, Properties properties, CacheDataDescription metadata)
			throws CacheException {
		if ( log.isDebugEnabled() ) {
			log.debugf(
					"Building entity cache region [%s] (mutable=%s, versioned=%s)",
					regionName,
					metadata.isMutable(),
					metadata.isVersioned()
			);
		}
		final AdvancedCache cache = getCache( regionName, metadata.isMutable() ? ENTITY_KEY : IMMUTABLE_ENTITY_KEY, properties );
		final EntityRegionImpl region = new EntityRegionImpl( cache, regionName, metadata, this );
		startRegion( region, regionName );
		return region;
	}

	@Override
	public NaturalIdRegion buildNaturalIdRegion(String regionName, Properties properties, CacheDataDescription metadata)
			throws CacheException {
		if ( log.isDebugEnabled() ) {
			log.debug( "Building natural id cache region [" + regionName + "]" );
		}
		final AdvancedCache cache = getCache( regionName, NATURAL_ID_KEY, properties );
		final NaturalIdRegionImpl region = new NaturalIdRegionImpl( cache, regionName, metadata, this );
		startRegion( region, regionName );
		return region;
	}

	@Override
	public QueryResultsRegion buildQueryResultsRegion(String regionName, Properties properties)
			throws CacheException {
		if ( log.isDebugEnabled() ) {
			log.debug( "Building query results cache region [" + regionName + "]" );
		}
		String cacheName = typeOverrides.get( QUERY_KEY ).getCacheName();
		// If region name is not default one, lookup a cache for that region name
		if ( !regionName.equals( "org.hibernate.cache.internal.StandardQueryCache" ) ) {
			cacheName = regionName;
		}

		final AdvancedCache cache = getCache( cacheName, QUERY_KEY, properties );
		final QueryResultsRegionImpl region = new QueryResultsRegionImpl( cache, regionName, this );
		startRegion( region, regionName );
		return region;
	}

	@Override
	public TimestampsRegion buildTimestampsRegion(String regionName, Properties properties)
			throws CacheException {
		if ( log.isDebugEnabled() ) {
			log.debug( "Building timestamps cache region [" + regionName + "]" );
		}
		final AdvancedCache cache = getCache( regionName, TIMESTAMPS_KEY, properties );
		final TimestampsRegionImpl region = createTimestampsRegion( cache, regionName );
		startRegion( region, regionName );
		return region;
	}

	protected TimestampsRegionImpl createTimestampsRegion(
			AdvancedCache cache, String regionName) {
		if ( Caches.isClustered( cache ) ) {
			return new ClusteredTimestampsRegionImpl( cache, regionName, this );
		}
		else {
			return new TimestampsRegionImpl( cache, regionName, this );
		}
	}

	@Override
	public boolean isMinimalPutsEnabledByDefault() {
		return true;
	}

	@Override
	public AccessType getDefaultAccessType() {
		return AccessType.TRANSACTIONAL;
	}

	@Override
	public long nextTimestamp() {
		return System.currentTimeMillis() / 100;
	}

	public void setCacheManager(EmbeddedCacheManager manager) {
		this.manager = manager;
	}

	public EmbeddedCacheManager getCacheManager() {
		return manager;
	}

	@Override
	public void start(SessionFactoryOptions settings, Properties properties) throws CacheException {
		log.debug( "Starting Infinispan region factory" );
		try {
			transactionManagerlookup = createTransactionManagerLookup( settings, properties );
			manager = createCacheManager( properties, settings.getServiceRegistry() );
			initGenericDataTypeOverrides();
			final Enumeration keys = properties.propertyNames();
			while ( keys.hasMoreElements() ) {
				final String key = (String) keys.nextElement();
				int prefixLoc;
				if ( (prefixLoc = key.indexOf( PREFIX )) != -1 ) {
					dissectProperty( prefixLoc, key, properties );
				}
			}
			defineGenericDataTypeCacheConfigurations( properties );
			definePendingPutsCache();
		}
		catch (CacheException ce) {
			throw ce;
		}
		catch (Throwable t) {
			throw new CacheException( "Unable to start region factory", t );
		}
	}

	private void definePendingPutsCache() {
		final ConfigurationBuilder builder = new ConfigurationBuilder();
		// A local, lightweight cache for pending puts, which is
		// non-transactional and has aggressive expiration settings.
		// Locking is still required since the putFromLoad validator
		// code uses conditional operations (i.e. putIfAbsent).
		builder.clustering().cacheMode( CacheMode.LOCAL )
				.transaction().transactionMode( TransactionMode.NON_TRANSACTIONAL )
				.expiration().maxIdle( TimeUnit.SECONDS.toMillis( 60 ) )
				.storeAsBinary().enabled( false )
				.locking().isolationLevel( IsolationLevel.READ_COMMITTED )
				.jmxStatistics().disable();

		manager.defineConfiguration( PENDING_PUTS_CACHE_NAME, builder.build() );
	}

	protected org.infinispan.transaction.lookup.TransactionManagerLookup createTransactionManagerLookup(
			SessionFactoryOptions settings, Properties properties) {
		return new HibernateTransactionManagerLookup( settings, properties );
	}

	@Override
	public void stop() {
		log.debug( "Stop region factory" );
		stopCacheRegions();
		stopCacheManager();
	}

	protected void stopCacheRegions() {
		log.debug( "Clear region references" );
		getCacheCommandFactory( manager.getCache().getAdvancedCache() )
				.clearRegions( regionNames );
		regionNames.clear();
	}

	protected void stopCacheManager() {
		log.debug( "Stop cache manager" );
		manager.stop();
	}

	/**
	 * Returns an unmodifiable map containing configured entity/collection type configuration overrides.
	 * This method should be used primarily for testing/checking purpouses.
	 *
	 * @return an unmodifiable map.
	 */
	public Map<String, TypeOverrides> getTypeOverrides() {
		return Collections.unmodifiableMap( typeOverrides );
	}

	public Set<String> getDefinedConfigurations() {
		return Collections.unmodifiableSet( definedConfigurations );
	}

	protected EmbeddedCacheManager createCacheManager(
			final Properties properties,
			final ServiceRegistry serviceRegistry) throws CacheException {
		final String configLoc = ConfigurationHelper.getString(
				INFINISPAN_CONFIG_RESOURCE_PROP,
				properties,
				DEF_INFINISPAN_CONFIG_RESOURCE
		);
		final FileLookup fileLookup = FileLookupFactory.newInstance();
		//The classloader of the current module:
		final ClassLoader infinispanClassLoader = InfinispanRegionFactory.class.getClassLoader();

		return serviceRegistry.getService( ClassLoaderService.class ).workWithClassLoader(
				new ClassLoaderService.Work<EmbeddedCacheManager>() {
					@Override
					public EmbeddedCacheManager doWork(ClassLoader classLoader) {
						InputStream is = null;
						try {
							is = fileLookup.lookupFile( configLoc, classLoader );
							if ( is == null ) {
								// when it's not a user-provided configuration file, it might be a default configuration file,
								// and if that's included in [this] module might not be visible to the ClassLoaderService:
								classLoader = infinispanClassLoader;
								// This time use lookupFile*Strict* so to provide an exception if we can't find it yet:
								is = FileLookupFactory.newInstance().lookupFileStrict( configLoc, classLoader );
							}
							final ParserRegistry parserRegistry = new ParserRegistry( infinispanClassLoader );
							final ConfigurationBuilderHolder holder = parseWithOverridenClassLoader( parserRegistry, is, infinispanClassLoader );

							// Override global jmx statistics exposure
							final String globalStats = extractProperty(
									INFINISPAN_GLOBAL_STATISTICS_PROP,
									properties
							);
							if ( globalStats != null ) {
								holder.getGlobalConfigurationBuilder()
										.globalJmxStatistics()
										.enabled( Boolean.parseBoolean( globalStats ) );
							}

							return createCacheManager( holder );
						}
						catch (IOException e) {
							throw new CacheException( "Unable to create default cache manager", e );
						}
						finally {
							Util.close( is );
						}
					}

				}
		);
	}

	private static ConfigurationBuilderHolder parseWithOverridenClassLoader(ParserRegistry configurationParser, InputStream is, ClassLoader infinispanClassLoader) {
		// Infinispan requires the context ClassLoader to have full visibility on all
		// its components and eventual extension points even *during* configuration parsing.
		final Thread currentThread = Thread.currentThread();
		final ClassLoader originalContextClassLoader = currentThread.getContextClassLoader();
		try {
			currentThread.setContextClassLoader( infinispanClassLoader );
			ConfigurationBuilderHolder builderHolder = configurationParser.parse( is );
			// Workaround Infinispan's ClassLoader strategies to bend to our will:
			builderHolder.getGlobalConfigurationBuilder().classLoader( infinispanClassLoader );
			return builderHolder;
		}
		finally {
			currentThread.setContextClassLoader( originalContextClassLoader );
		}
	}

	protected EmbeddedCacheManager createCacheManager(ConfigurationBuilderHolder holder) {
		return new DefaultCacheManager( holder, true );
	}

	private void startRegion(BaseRegion region, String regionName) {
		regionNames.add( regionName );
		getCacheCommandFactory( region.getCache() ).addRegion( regionName, region );
	}

	private Map<String, TypeOverrides> initGenericDataTypeOverrides() {
		final TypeOverrides entityOverrides = new TypeOverrides();
		entityOverrides.setCacheName( DEF_ENTITY_RESOURCE );
		typeOverrides.put( ENTITY_KEY, entityOverrides );
		final TypeOverrides immutableEntityOverrides = new TypeOverrides();
		immutableEntityOverrides.setCacheName( DEF_IMMUTABLE_ENTITY_RESOURCE );
		typeOverrides.put( IMMUTABLE_ENTITY_KEY, immutableEntityOverrides );
		final TypeOverrides collectionOverrides = new TypeOverrides();
		collectionOverrides.setCacheName( DEF_ENTITY_RESOURCE );
		typeOverrides.put( COLLECTION_KEY, collectionOverrides );
		final TypeOverrides naturalIdOverrides = new TypeOverrides();
		naturalIdOverrides.setCacheName( DEF_ENTITY_RESOURCE );
		typeOverrides.put( NATURAL_ID_KEY, naturalIdOverrides );
		final TypeOverrides timestampOverrides = new TimestampTypeOverrides();
		timestampOverrides.setCacheName( DEF_TIMESTAMPS_RESOURCE );
		typeOverrides.put( TIMESTAMPS_KEY, timestampOverrides );
		final TypeOverrides queryOverrides = new TypeOverrides();
		queryOverrides.setCacheName( DEF_QUERY_RESOURCE );
		typeOverrides.put( QUERY_KEY, queryOverrides );
		return typeOverrides;
	}

	private void dissectProperty(int prefixLoc, String key, Properties properties) {
		final TypeOverrides cfgOverride;
		int suffixLoc;
		if ( !key.equals( INFINISPAN_CONFIG_RESOURCE_PROP ) && (suffixLoc = key.indexOf( CONFIG_SUFFIX )) != -1 ) {
			cfgOverride = getOrCreateConfig( prefixLoc, key, suffixLoc );
			cfgOverride.setCacheName( extractProperty( key, properties ) );
		}
		else if ( (suffixLoc = key.indexOf( STRATEGY_SUFFIX )) != -1 ) {
			cfgOverride = getOrCreateConfig( prefixLoc, key, suffixLoc );
			cfgOverride.setEvictionStrategy( extractProperty( key, properties ) );
		}
		else if ( (suffixLoc = key.indexOf( WAKE_UP_INTERVAL_SUFFIX )) != -1 ) {
			cfgOverride = getOrCreateConfig( prefixLoc, key, suffixLoc );
			cfgOverride.setEvictionWakeUpInterval( Long.parseLong( extractProperty( key, properties ) ) );
		}
		else if ( (suffixLoc = key.indexOf( MAX_ENTRIES_SUFFIX )) != -1 ) {
			cfgOverride = getOrCreateConfig( prefixLoc, key, suffixLoc );
			cfgOverride.setEvictionMaxEntries( Integer.parseInt( extractProperty( key, properties ) ) );
		}
		else if ( (suffixLoc = key.indexOf( LIFESPAN_SUFFIX )) != -1 ) {
			cfgOverride = getOrCreateConfig( prefixLoc, key, suffixLoc );
			cfgOverride.setExpirationLifespan( Long.parseLong( extractProperty( key, properties ) ) );
		}
		else if ( (suffixLoc = key.indexOf( MAX_IDLE_SUFFIX )) != -1 ) {
			cfgOverride = getOrCreateConfig( prefixLoc, key, suffixLoc );
			cfgOverride.setExpirationMaxIdle( Long.parseLong( extractProperty( key, properties ) ) );
		}
	}

	private String extractProperty(String key, Properties properties) {
		final String value = ConfigurationHelper.extractPropertyValue( key, properties );
		log.debugf( "Configuration override via property %s: %s", key, value );
		return value;
	}

	private TypeOverrides getOrCreateConfig(int prefixLoc, String key, int suffixLoc) {
		final String name = key.substring( prefixLoc + PREFIX.length(), suffixLoc );
		TypeOverrides cfgOverride = typeOverrides.get( name );
		if ( cfgOverride == null ) {
			cfgOverride = new TypeOverrides();
			typeOverrides.put( name, cfgOverride );
		}
		return cfgOverride;
	}

	private void defineGenericDataTypeCacheConfigurations(Properties properties) {
		final String[] defaultGenericDataTypes = new String[] {ENTITY_KEY, IMMUTABLE_ENTITY_KEY, COLLECTION_KEY, TIMESTAMPS_KEY, QUERY_KEY};
		for ( String type : defaultGenericDataTypes ) {
			final TypeOverrides override = overrideStatisticsIfPresent( typeOverrides.get( type ), properties );
			final String cacheName = override.getCacheName();
			final ConfigurationBuilder builder = new ConfigurationBuilder();
			// Read base configuration
			applyConfiguration( cacheName, builder );

			// Apply overrides
			override.applyTo( builder );
			// Configure transaction manager
			configureTransactionManager( builder, cacheName, properties );
			// Define configuration, validate and then apply
			final Configuration cfg = builder.build();
			override.validateInfinispanConfiguration( cfg );
			manager.defineConfiguration( cacheName, cfg );
			definedConfigurations.add( cacheName );
		}
	}

	private AdvancedCache getCache(String regionName, String typeKey, Properties properties) {
		TypeOverrides regionOverride = typeOverrides.get( regionName );
		if ( !definedConfigurations.contains( regionName ) ) {
			final String templateCacheName;
			final ConfigurationBuilder builder = new ConfigurationBuilder();
			if ( regionOverride != null ) {
				if ( log.isDebugEnabled() ) {
					log.debug( "Cache region specific configuration exists: " + regionOverride );
				}
				final String cacheName = regionOverride.getCacheName();
				if ( cacheName != null ) {
					// Region specific override with a given cache name
					templateCacheName = cacheName;
				}
				else {
					// Region specific override without cache name, so template cache name is generic for data type.
					templateCacheName = typeOverrides.get( typeKey ).getCacheName();
				}

				// Read template configuration
				applyConfiguration( templateCacheName, builder );

				regionOverride = overrideStatisticsIfPresent( regionOverride, properties );
				regionOverride.applyTo( builder );

			}
			else {
				// No region specific overrides, template cache name is generic for data type.
				templateCacheName = typeOverrides.get( typeKey ).getCacheName();
				// Read template configuration
				builder.read( manager.getCacheConfiguration( templateCacheName ) );
				// Apply overrides
				typeOverrides.get( typeKey ).applyTo( builder );
			}
			// Configure transaction manager
			configureTransactionManager( builder, templateCacheName, properties );
			// Define configuration
			manager.defineConfiguration( regionName, builder.build() );
			definedConfigurations.add( regionName );
		}
		final AdvancedCache cache = manager.getCache( regionName ).getAdvancedCache();
		if ( !cache.getStatus().allowInvocations() ) {
			cache.start();
		}
		return createCacheWrapper( cache );
	}

	private void applyConfiguration(String cacheName, ConfigurationBuilder builder) {
		final Configuration cfg = manager.getCacheConfiguration( cacheName );
		if ( cfg != null ) {
			builder.read( cfg );
		}
	}

	private CacheCommandFactory getCacheCommandFactory(AdvancedCache cache) {
		final GlobalComponentRegistry globalCr = cache.getComponentRegistry().getGlobalComponentRegistry();

		final Map<Byte, ModuleCommandFactory> factories =
				(Map<Byte, ModuleCommandFactory>) globalCr.getComponent( "org.infinispan.modules.command.factories" );

		for ( ModuleCommandFactory factory : factories.values() ) {
			if ( factory instanceof CacheCommandFactory ) {
				return (CacheCommandFactory) factory;
			}
		}

		throw new CacheException(
				"Infinispan custom cache command factory not " +
						"installed (possibly because the classloader where Infinispan " +
						"lives couldn't find the Hibernate Infinispan cache provider)"
		);
	}

	protected AdvancedCache createCacheWrapper(AdvancedCache cache) {
		return cache;
	}

	private void configureTransactionManager(
			ConfigurationBuilder builder,
			String cacheName,
			Properties properties) {
		// Get existing configuration to verify whether a tm was configured or not.
		final Configuration baseCfg = manager.getCacheConfiguration( cacheName );
		if ( baseCfg != null && baseCfg.transaction().transactionMode().isTransactional() ) {
			final String ispnTmLookupClassName = baseCfg.transaction().transactionManagerLookup().getClass().getName();
			final String hbTmLookupClassName = org.hibernate.cache.infinispan.tm.HibernateTransactionManagerLookup.class.getName();
			if ( GenericTransactionManagerLookup.class.getName().equals( ispnTmLookupClassName ) ) {
				log.debug(
						"Using default Infinispan transaction manager lookup " +
								"instance (GenericTransactionManagerLookup), overriding it " +
								"with Hibernate transaction manager lookup"
				);
				builder.transaction().transactionManagerLookup( transactionManagerlookup );
			}
			else if ( ispnTmLookupClassName != null && !ispnTmLookupClassName.equals( hbTmLookupClassName ) ) {
				log.debug(
						"Infinispan is configured [" + ispnTmLookupClassName + "] with a different transaction manager lookup " +
								"class than Hibernate [" + hbTmLookupClassName + "]"
				);
			}
			else {
				// Infinispan TM lookup class null, so apply Hibernate one directly
				builder.transaction().transactionManagerLookup( transactionManagerlookup );
			}

			final String useSyncProp = extractProperty( INFINISPAN_USE_SYNCHRONIZATION_PROP, properties );
			final boolean useSync = useSyncProp == null ? DEF_USE_SYNCHRONIZATION : Boolean.parseBoolean( useSyncProp );
			builder.transaction().useSynchronization( useSync );
		}
	}

	private TypeOverrides overrideStatisticsIfPresent(TypeOverrides override, Properties properties) {
		final String globalStats = extractProperty( INFINISPAN_GLOBAL_STATISTICS_PROP, properties );
		if ( globalStats != null ) {
			override.setExposeStatistics( Boolean.parseBoolean( globalStats ) );
		}
		return override;
	}
}


File: hibernate-infinispan/src/main/java/org/hibernate/cache/infinispan/access/PutFromLoadValidator.java
/*
 * Hibernate, Relational Persistence for Idiomatic Java
 *
 * License: GNU Lesser General Public License (LGPL), version 2.1 or later.
 * See the lgpl.txt file in the root directory or <http://www.gnu.org/licenses/lgpl-2.1.html>.
 */
package org.hibernate.cache.infinispan.access;

import java.util.HashMap;
import java.util.LinkedList;
import java.util.List;
import java.util.Map;
import java.util.concurrent.ConcurrentHashMap;
import java.util.concurrent.ConcurrentMap;
import java.util.concurrent.TimeUnit;
import java.util.concurrent.locks.Lock;
import java.util.concurrent.locks.ReentrantLock;
import javax.transaction.SystemException;
import javax.transaction.Transaction;
import javax.transaction.TransactionManager;

import org.hibernate.cache.CacheException;
import org.hibernate.cache.infinispan.InfinispanRegionFactory;

import org.infinispan.AdvancedCache;
import org.infinispan.manager.EmbeddedCacheManager;

/**
 * Encapsulates logic to allow a {@link TransactionalAccessDelegate} to determine
 * whether a {@link TransactionalAccessDelegate#putFromLoad(Object, Object, long, Object, boolean)}
 * call should be allowed to update the cache. A <code>putFromLoad</code> has
 * the potential to store stale data, since the data may have been removed from the
 * database and the cache between the time when the data was read from the database
 * and the actual call to <code>putFromLoad</code>.
 * <p>
 * The expected usage of this class by a thread that read the cache and did
 * not find data is:
 * <p/>
 * <ol>
 * <li> Call {@link #registerPendingPut(Object)}</li>
 * <li> Read the database</li>
 * <li> Call {@link #acquirePutFromLoadLock(Object)}
 * <li> if above returns <code>false</code>, the thread should not cache the data;
 * only if above returns <code>true</code>, put data in the cache and...</li>
 * <li> then call {@link #releasePutFromLoadLock(Object)}</li>
 * </ol>
 * </p>
 * <p/>
 * <p>
 * The expected usage by a thread that is taking an action such that any pending
 * <code>putFromLoad</code> may have stale data and should not cache it is to either
 * call
 * <p/>
 * <ul>
 * <li> {@link #invalidateKey(Object)} (for a single key invalidation)</li>
 * <li>or {@link #invalidateRegion()} (for a general invalidation all pending puts)</li>
 * </ul>
 * </p>
 * <p/>
 * <p>
 * This class also supports the concept of "naked puts", which are calls to
 * {@link #acquirePutFromLoadLock(Object)} without a preceding {@link #registerPendingPut(Object)}
 * call.
 * </p>
 *
 * @author Brian Stansberry
 * @version $Revision: $
 */
public class PutFromLoadValidator {
	/**
	 * Period (in ms) after a removal during which a call to
	 * {@link #acquirePutFromLoadLock(Object)} that hasn't been
	 * {@link #registerPendingPut(Object) pre-registered} (aka a "naked put")
	 * will return false.
	 */
	public static final long NAKED_PUT_INVALIDATION_PERIOD = TimeUnit.SECONDS.toMillis( 20 );

	/**
	 * Used to determine whether the owner of a pending put is a thread or a transaction
	 */
	private final TransactionManager transactionManager;

	private final long nakedPutInvalidationPeriod;

	/**
	 * Registry of expected, future, isPutValid calls. If a key+owner is registered in this map, it
	 * is not a "naked put" and is allowed to proceed.
	 */
	private final ConcurrentMap<Object, PendingPutMap> pendingPuts;

	private final ConcurrentMap<Object, Long> recentRemovals = new ConcurrentHashMap<Object, Long>();
	/**
	 * List of recent removals. Used to ensure we don't leak memory via the recentRemovals map
	 */
	private final List<RecentRemoval> removalsQueue = new LinkedList<RecentRemoval>();
	/**
	 * The time when the first element in removalsQueue will expire. No reason to do housekeeping on
	 * the queue before this time.
	 */
	private volatile long earliestRemovalTimestamp;
	/**
	 * Lock controlling access to removalsQueue
	 */
	private final Lock removalsLock = new ReentrantLock();

	/**
	 * The time of the last call to regionRemoved(), plus NAKED_PUT_INVALIDATION_PERIOD. All naked
	 * puts will be rejected until the current time is greater than this value.
	 */
	private volatile long invalidationTimestamp;

	/**
	 * Creates a new put from load validator instance.
    *
    * @param cache Cache instance on which to store pending put information.
	 */
	public PutFromLoadValidator(AdvancedCache cache) {
		this( cache, NAKED_PUT_INVALIDATION_PERIOD );
	}

   /**
    * Constructor variant for use by unit tests; allows control of various timeouts by the test.
    *
    * @param cache Cache instance on which to store pending put information.
    * @param nakedPutInvalidationPeriod Period (in ms) after a removal during which a call to
    *                                   {@link #acquirePutFromLoadLock(Object)} that hasn't been
    *                                   {@link #registerPendingPut(Object) pre-registered} (aka a "naked put")
    *                                   will return false.
    */
	public PutFromLoadValidator(
			AdvancedCache cache,
			long nakedPutInvalidationPeriod) {
		this(
				cache.getCacheManager(), cache.getTransactionManager(),
				nakedPutInvalidationPeriod
		);
	}

   /**
    * Creates a new put from load validator instance.
    *
    * @param cacheManager where to find a cache to store pending put information
    * @param tm transaction manager
    * @param nakedPutInvalidationPeriod Period (in ms) after a removal during which a call to
    *                                   {@link #acquirePutFromLoadLock(Object)} that hasn't been
    *                                   {@link #registerPendingPut(Object) pre-registered} (aka a "naked put")
    *                                   will return false.
    */
	public PutFromLoadValidator(
			EmbeddedCacheManager cacheManager,
			TransactionManager tm, long nakedPutInvalidationPeriod) {
		this.pendingPuts = cacheManager
				.getCache( InfinispanRegionFactory.PENDING_PUTS_CACHE_NAME );
		this.transactionManager = tm;
		this.nakedPutInvalidationPeriod = nakedPutInvalidationPeriod;
	}

	// ----------------------------------------------------------------- Public

	/**
	 * Acquire a lock giving the calling thread the right to put data in the
	 * cache for the given key.
	 * <p>
	 * <strong>NOTE:</strong> A call to this method that returns <code>true</code>
	 * should always be matched with a call to {@link #releasePutFromLoadLock(Object)}.
	 * </p>
	 *
	 * @param key the key
	 *
	 * @return <code>true</code> if the lock is acquired and the cache put
	 *         can proceed; <code>false</code> if the data should not be cached
	 */
	public boolean acquirePutFromLoadLock(Object key) {
		boolean valid = false;
		boolean locked = false;
		final long now = System.currentTimeMillis();

		try {
			final PendingPutMap pending = pendingPuts.get( key );
			if ( pending != null ) {
				locked = pending.acquireLock( 100, TimeUnit.MILLISECONDS );
				if ( locked ) {
					try {
						final PendingPut toCancel = pending.remove( getOwnerForPut() );
						if ( toCancel != null ) {
							valid = !toCancel.completed;
							toCancel.completed = true;
						}
					}
					finally {
						if ( !valid ) {
							pending.releaseLock();
							locked = false;
						}
					}
				}
			}
			else {
				// Key wasn't in pendingPuts, so either this is a "naked put"
				// or regionRemoved has been called. Check if we can proceed
				if ( now > invalidationTimestamp ) {
					final Long removedTime = recentRemovals.get( key );
					if ( removedTime == null || now > removedTime ) {
						// It's legal to proceed. But we have to record this key
						// in pendingPuts so releasePutFromLoadLock can find it.
						// To do this we basically simulate a normal "register
						// then acquire lock" pattern
						registerPendingPut( key );
						locked = acquirePutFromLoadLock( key );
						valid = locked;
					}
				}
			}
		}
		catch (Throwable t) {
			if ( locked ) {
				final PendingPutMap toRelease = pendingPuts.get( key );
				if ( toRelease != null ) {
					toRelease.releaseLock();
				}
			}

			if ( t instanceof RuntimeException ) {
				throw (RuntimeException) t;
			}
			else if ( t instanceof Error ) {
				throw (Error) t;
			}
			else {
				throw new RuntimeException( t );
			}
		}

		return valid;
	}

	/**
	 * Releases the lock previously obtained by a call to
	 * {@link #acquirePutFromLoadLock(Object)} that returned <code>true</code>.
	 *
	 * @param key the key
	 */
	public void releasePutFromLoadLock(Object key) {
		final PendingPutMap pending = pendingPuts.get( key );
		if ( pending != null ) {
			if ( pending.size() == 0 ) {
				pendingPuts.remove( key, pending );
			}
			pending.releaseLock();
		}
	}

	/**
	 * Invalidates any {@link #registerPendingPut(Object) previously registered pending puts} ensuring a subsequent call to
	 * {@link #acquirePutFromLoadLock(Object)} will return <code>false</code>. <p> This method will block until any
	 * concurrent thread that has {@link #acquirePutFromLoadLock(Object) acquired the putFromLoad lock} for the given key
	 * has released the lock. This allows the caller to be certain the putFromLoad will not execute after this method
	 * returns, possibly caching stale data. </p>
	 *
	 * @param key key identifying data whose pending puts should be invalidated
	 *
	 * @return <code>true</code> if the invalidation was successful; <code>false</code> if a problem occured (which the
	 *         caller should treat as an exception condition)
	 */
	public boolean invalidateKey(Object key) {
		boolean success = true;

		// Invalidate any pending puts
		final PendingPutMap pending = pendingPuts.get( key );
		if ( pending != null ) {
			// This lock should be available very quickly, but we'll be
			// very patient waiting for it as callers should treat not
			// acquiring it as an exception condition
			if ( pending.acquireLock( 60, TimeUnit.SECONDS ) ) {
				try {
					pending.invalidate();
				}
				finally {
					pending.releaseLock();
				}
			}
			else {
				success = false;
			}
		}

		// Record when this occurred to invalidate later naked puts
		final RecentRemoval removal = new RecentRemoval( key, this.nakedPutInvalidationPeriod );
		recentRemovals.put( key, removal.timestamp );

		// Don't let recentRemovals map become a memory leak
		RecentRemoval toClean = null;
		final boolean attemptClean = removal.timestamp > earliestRemovalTimestamp;
		removalsLock.lock();
		try {
			removalsQueue.add( removal );

			if ( attemptClean ) {
				if ( removalsQueue.size() > 1 ) {
					// we have at least one as we just added it
					toClean = removalsQueue.remove( 0 );
				}
				earliestRemovalTimestamp = removalsQueue.get( 0 ).timestamp;
			}
		}
		finally {
			removalsLock.unlock();
		}

		if ( toClean != null ) {
			Long cleaned = recentRemovals.get( toClean.key );
			if ( cleaned != null && cleaned.equals( toClean.timestamp ) ) {
				cleaned = recentRemovals.remove( toClean.key );
				if ( cleaned != null && !cleaned.equals( toClean.timestamp ) ) {
					// Oops; removed the wrong timestamp; restore it
					recentRemovals.putIfAbsent( toClean.key, cleaned );
				}
			}
		}

		return success;
	}

	/**
	 * Invalidates all {@link #registerPendingPut(Object) previously registered pending puts} ensuring a subsequent call to
	 * {@link #acquirePutFromLoadLock(Object)} will return <code>false</code>. <p> This method will block until any
	 * concurrent thread that has {@link #acquirePutFromLoadLock(Object) acquired the putFromLoad lock} for the any key has
	 * released the lock. This allows the caller to be certain the putFromLoad will not execute after this method returns,
	 * possibly caching stale data. </p>
	 *
	 * @return <code>true</code> if the invalidation was successful; <code>false</code> if a problem occured (which the
	 *         caller should treat as an exception condition)
	 */
	public boolean invalidateRegion() {

		boolean ok = false;
		invalidationTimestamp = System.currentTimeMillis() + this.nakedPutInvalidationPeriod;

		try {

			// Acquire the lock for each entry to ensure any ongoing
			// work associated with it is completed before we return
			for ( PendingPutMap entry : pendingPuts.values() ) {
				if ( entry.acquireLock( 60, TimeUnit.SECONDS ) ) {
					try {
						entry.invalidate();
					}
					finally {
						entry.releaseLock();
					}
				}
				else {
					ok = false;
				}
			}

			removalsLock.lock();
			try {
				recentRemovals.clear();
				removalsQueue.clear();

				ok = true;

			}
			finally {
				removalsLock.unlock();
			}
		}
		catch (Exception e) {
			ok = false;
		}
		finally {
			earliestRemovalTimestamp = invalidationTimestamp;
		}

		return ok;
	}

	/**
	 * Notifies this validator that it is expected that a database read followed by a subsequent {@link
	 * #acquirePutFromLoadLock(Object)} call will occur. The intent is this method would be called following a cache miss
	 * wherein it is expected that a database read plus cache put will occur. Calling this method allows the validator to
	 * treat the subsequent <code>acquirePutFromLoadLock</code> as if the database read occurred when this method was
	 * invoked. This allows the validator to compare the timestamp of this call against the timestamp of subsequent removal
	 * notifications. A put that occurs without this call preceding it is "naked"; i.e the validator must assume the put is
	 * not valid if any relevant removal has occurred within {@link #NAKED_PUT_INVALIDATION_PERIOD} milliseconds.
	 *
	 * @param key key that will be used for subsequent cache put
	 */
	public void registerPendingPut(Object key) {
		final PendingPut pendingPut = new PendingPut( getOwnerForPut() );
		final PendingPutMap pendingForKey = new PendingPutMap( pendingPut );

		for (; ; ) {
			final PendingPutMap existing = pendingPuts.putIfAbsent( key, pendingForKey );
			if ( existing != null ) {
				if ( existing.acquireLock( 10, TimeUnit.SECONDS ) ) {

					try {
						existing.put( pendingPut );
						final PendingPutMap doublecheck = pendingPuts.putIfAbsent( key, existing );
						if ( doublecheck == null || doublecheck == existing ) {
							break;
						}
						// else we hit a race and need to loop to try again
					}
					finally {
						existing.releaseLock();
					}
				}
				else {
					// Can't get the lock; when we come back we'll be a "naked put"
					break;
				}
			}
			else {
				// normal case
				break;
			}
		}
	}

	// -------------------------------------------------------------- Protected

	/**
	 * Only for use by unit tests; may be removed at any time
	 */
	protected int getRemovalQueueLength() {
		removalsLock.lock();
		try {
			return removalsQueue.size();
		}
		finally {
			removalsLock.unlock();
		}
	}

	// ---------------------------------------------------------------- Private

	private Object getOwnerForPut() {
		Transaction tx = null;
		try {
			if ( transactionManager != null ) {
				tx = transactionManager.getTransaction();
			}
		}
		catch (SystemException se) {
			throw new CacheException( "Could not obtain transaction", se );
		}
		return tx == null ? Thread.currentThread() : tx;

	}

	/**
	 * Lazy-initialization map for PendingPut. Optimized for the expected usual case where only a
	 * single put is pending for a given key.
	 * <p/>
	 * This class is NOT THREAD SAFE. All operations on it must be performed with the lock held.
	 */
	private static class PendingPutMap {
		private PendingPut singlePendingPut;
		private Map<Object, PendingPut> fullMap;
		private final Lock lock = new ReentrantLock();

		PendingPutMap(PendingPut singleItem) {
			this.singlePendingPut = singleItem;
		}

		public void put(PendingPut pendingPut) {
			if ( singlePendingPut == null ) {
				if ( fullMap == null ) {
					// initial put
					singlePendingPut = pendingPut;
				}
				else {
					fullMap.put( pendingPut.owner, pendingPut );
				}
			}
			else {
				// 2nd put; need a map
				fullMap = new HashMap<Object, PendingPut>( 4 );
				fullMap.put( singlePendingPut.owner, singlePendingPut );
				singlePendingPut = null;
				fullMap.put( pendingPut.owner, pendingPut );
			}
		}

		public PendingPut remove(Object ownerForPut) {
			PendingPut removed = null;
			if ( fullMap == null ) {
				if ( singlePendingPut != null
						&& singlePendingPut.owner.equals( ownerForPut ) ) {
					removed = singlePendingPut;
					singlePendingPut = null;
				}
			}
			else {
				removed = fullMap.remove( ownerForPut );
			}
			return removed;
		}

		public int size() {
			return fullMap == null ? (singlePendingPut == null ? 0 : 1)
					: fullMap.size();
		}

		public boolean acquireLock(long time, TimeUnit unit) {
			try {
				return lock.tryLock( time, unit );
			}
			catch (InterruptedException e) {
				Thread.currentThread().interrupt();
				return false;
			}
		}

		public void releaseLock() {
			lock.unlock();
		}

		public void invalidate() {
			if ( singlePendingPut != null ) {
				singlePendingPut.completed = true;
				// Nullify to avoid leaking completed pending puts
				singlePendingPut = null;
			}
			else if ( fullMap != null ) {
				for ( PendingPut pp : fullMap.values() ) {
					pp.completed = true;
				}
				// Nullify to avoid leaking completed pending puts
				fullMap = null;
			}
		}
	}

	private static class PendingPut {
		private final Object owner;
		private volatile boolean completed;

		private PendingPut(Object owner) {
			this.owner = owner;
		}
	}

	private static class RecentRemoval {
		private final Object key;
		private final Long timestamp;

		private RecentRemoval(Object key, long nakedPutInvalidationPeriod) {
			this.key = key;
			timestamp = System.currentTimeMillis() + nakedPutInvalidationPeriod;
		}
	}

}


File: hibernate-infinispan/src/main/java/org/hibernate/cache/infinispan/collection/CollectionRegionImpl.java
/*
 * Hibernate, Relational Persistence for Idiomatic Java
 *
 * License: GNU Lesser General Public License (LGPL), version 2.1 or later.
 * See the lgpl.txt file in the root directory or <http://www.gnu.org/licenses/lgpl-2.1.html>.
 */
package org.hibernate.cache.infinispan.collection;

import org.hibernate.cache.CacheException;
import org.hibernate.cache.infinispan.access.PutFromLoadValidator;
import org.hibernate.cache.infinispan.impl.BaseTransactionalDataRegion;
import org.hibernate.cache.spi.CacheDataDescription;
import org.hibernate.cache.spi.CollectionRegion;
import org.hibernate.cache.spi.RegionFactory;
import org.hibernate.cache.spi.access.AccessType;
import org.hibernate.cache.spi.access.CollectionRegionAccessStrategy;

import org.infinispan.AdvancedCache;

/**
 * Collection region implementation
 *
 * @author Chris Bredesen
 * @author Galder Zamarreño
 * @since 3.5
 */
public class CollectionRegionImpl extends BaseTransactionalDataRegion implements CollectionRegion {

   /**
    * Construct a collection region
    *
    * @param cache instance to store collection instances
    * @param name of collection type
    * @param metadata for the collection type
    * @param factory for the region
    */
	public CollectionRegionImpl(
			AdvancedCache cache, String name,
			CacheDataDescription metadata, RegionFactory factory) {
		super( cache, name, metadata, factory );
	}

	@Override
	public CollectionRegionAccessStrategy buildAccessStrategy(AccessType accessType) throws CacheException {
		if ( AccessType.READ_ONLY.equals( accessType )
				|| AccessType.TRANSACTIONAL.equals( accessType ) ) {
			return new TransactionalAccess( this );
		}

		throw new CacheException( "Unsupported access type [" + accessType.getExternalName() + "]" );
	}

	public PutFromLoadValidator getPutFromLoadValidator() {
		return new PutFromLoadValidator( cache );
	}

}


File: hibernate-infinispan/src/main/java/org/hibernate/cache/infinispan/collection/TransactionalAccess.java
/*
 * Hibernate, Relational Persistence for Idiomatic Java
 *
 * License: GNU Lesser General Public License (LGPL), version 2.1 or later.
 * See the lgpl.txt file in the root directory or <http://www.gnu.org/licenses/lgpl-2.1.html>.
 */
package org.hibernate.cache.infinispan.collection;

import org.hibernate.cache.CacheException;
import org.hibernate.cache.infinispan.access.TransactionalAccessDelegate;
import org.hibernate.cache.internal.DefaultCacheKeysFactory;
import org.hibernate.cache.spi.CollectionRegion;
import org.hibernate.cache.spi.access.CollectionRegionAccessStrategy;
import org.hibernate.cache.spi.access.SoftLock;
import org.hibernate.engine.spi.SessionFactoryImplementor;
import org.hibernate.persister.collection.CollectionPersister;

/**
 * Transactional collection region access for Infinispan.
 *
 * @author Chris Bredesen
 * @author Galder Zamarreño
 * @since 3.5
 */
class TransactionalAccess implements CollectionRegionAccessStrategy {

	private final CollectionRegionImpl region;

	private final TransactionalAccessDelegate delegate;

	TransactionalAccess(CollectionRegionImpl region) {
		this.region = region;
		this.delegate = new TransactionalAccessDelegate( region, region.getPutFromLoadValidator() );
	}

	public void evict(Object key) throws CacheException {
		delegate.evict( key );
	}

	public void evictAll() throws CacheException {
		delegate.evictAll();
	}

	public Object get(Object key, long txTimestamp) throws CacheException {
		return delegate.get( key, txTimestamp );
	}

	public boolean putFromLoad(Object key, Object value, long txTimestamp, Object version) throws CacheException {
		return delegate.putFromLoad( key, value, txTimestamp, version );
	}

	public boolean putFromLoad(Object key, Object value, long txTimestamp, Object version, boolean minimalPutOverride)
			throws CacheException {
		return delegate.putFromLoad( key, value, txTimestamp, version, minimalPutOverride );
	}

	public void remove(Object key) throws CacheException {
		delegate.remove( key );
	}

	public void removeAll() throws CacheException {
		delegate.removeAll();
	}

	public CollectionRegion getRegion() {
		return region;
	}

	public SoftLock lockItem(Object key, Object version) throws CacheException {
		return null;
	}

	public SoftLock lockRegion() throws CacheException {
		return null;
	}

	public void unlockItem(Object key, SoftLock lock) throws CacheException {
	}

	public void unlockRegion(SoftLock lock) throws CacheException {
	}

	@Override
	public Object generateCacheKey(Object id, CollectionPersister persister, SessionFactoryImplementor factory, String tenantIdentifier) {
		return DefaultCacheKeysFactory.createCollectionKey(id, persister, factory, tenantIdentifier);
	}

	@Override
	public Object getCacheKeyId(Object cacheKey) {
		return DefaultCacheKeysFactory.getCollectionId(cacheKey);
	}

}


File: hibernate-infinispan/src/main/java/org/hibernate/cache/infinispan/entity/EntityRegionImpl.java
/*
 * Hibernate, Relational Persistence for Idiomatic Java
 *
 * License: GNU Lesser General Public License (LGPL), version 2.1 or later.
 * See the lgpl.txt file in the root directory or <http://www.gnu.org/licenses/lgpl-2.1.html>.
 */
package org.hibernate.cache.infinispan.entity;

import org.hibernate.cache.CacheException;
import org.hibernate.cache.infinispan.access.PutFromLoadValidator;
import org.hibernate.cache.infinispan.impl.BaseTransactionalDataRegion;
import org.hibernate.cache.spi.CacheDataDescription;
import org.hibernate.cache.spi.EntityRegion;
import org.hibernate.cache.spi.RegionFactory;
import org.hibernate.cache.spi.access.AccessType;
import org.hibernate.cache.spi.access.EntityRegionAccessStrategy;

import org.infinispan.AdvancedCache;

/**
 * Entity region implementation
 *
 * @author Chris Bredesen
 * @author Galder Zamarreño
 * @since 3.5
 */
public class EntityRegionImpl extends BaseTransactionalDataRegion implements EntityRegion {

   /**
    * Construct a entity region
    *
    * @param cache instance to store entity instances
    * @param name of entity type
    * @param metadata for the entity type
    * @param factory for the region
    */
	public EntityRegionImpl(
			AdvancedCache cache, String name,
			CacheDataDescription metadata, RegionFactory factory) {
		super( cache, name, metadata, factory );
	}

	@Override
	public EntityRegionAccessStrategy buildAccessStrategy(AccessType accessType) throws CacheException {
		switch ( accessType ) {
			case READ_ONLY:
				return new ReadOnlyAccess( this );
			case TRANSACTIONAL:
				if ( getCacheDataDescription().isMutable() ) {
					return new TransactionalAccess( this );
				}
				else {
					return new ReadOnlyAccess( this );
				}
			default:
				throw new CacheException( "Unsupported access type [" + accessType.getExternalName() + "]" );
		}
	}

	public PutFromLoadValidator getPutFromLoadValidator() {
		return new PutFromLoadValidator( cache );
	}

}


File: hibernate-infinispan/src/main/java/org/hibernate/cache/infinispan/entity/TransactionalAccess.java
/*
 * Hibernate, Relational Persistence for Idiomatic Java
 *
 * License: GNU Lesser General Public License (LGPL), version 2.1 or later.
 * See the lgpl.txt file in the root directory or <http://www.gnu.org/licenses/lgpl-2.1.html>.
 */
package org.hibernate.cache.infinispan.entity;

import org.hibernate.cache.CacheException;
import org.hibernate.cache.infinispan.access.TransactionalAccessDelegate;
import org.hibernate.cache.internal.DefaultCacheKeysFactory;
import org.hibernate.cache.spi.EntityRegion;
import org.hibernate.cache.spi.access.EntityRegionAccessStrategy;
import org.hibernate.cache.spi.access.SoftLock;
import org.hibernate.engine.spi.SessionFactoryImplementor;
import org.hibernate.persister.entity.EntityPersister;

/**
 * Transactional entity region access for Infinispan.
 *
 * @author Chris Bredesen
 * @author Galder Zamarreño
 * @since 3.5
 */
class TransactionalAccess implements EntityRegionAccessStrategy {

	private final EntityRegionImpl region;

	private final TransactionalAccessDelegate delegate;

	TransactionalAccess(EntityRegionImpl region) {
		this.region = region;
		this.delegate = new TransactionalAccessDelegate( region, region.getPutFromLoadValidator() );
	}

	public void evict(Object key) throws CacheException {
		delegate.evict( key );
	}

	public void evictAll() throws CacheException {
		delegate.evictAll();
	}

	public Object get(Object key, long txTimestamp) throws CacheException {
		return delegate.get( key, txTimestamp );
	}

	public EntityRegion getRegion() {
		return this.region;
	}

	public boolean insert(Object key, Object value, Object version) throws CacheException {
		return delegate.insert( key, value, version );
	}

	public boolean putFromLoad(Object key, Object value, long txTimestamp, Object version) throws CacheException {
		return delegate.putFromLoad( key, value, txTimestamp, version );
	}

	public boolean putFromLoad(Object key, Object value, long txTimestamp, Object version, boolean minimalPutOverride)
			throws CacheException {
		return delegate.putFromLoad( key, value, txTimestamp, version, minimalPutOverride );
	}

	public void remove(Object key) throws CacheException {
		delegate.remove( key );
	}

	public void removeAll() throws CacheException {
		delegate.removeAll();
	}

	public boolean update(Object key, Object value, Object currentVersion, Object previousVersion)
			throws CacheException {
		return delegate.update( key, value, currentVersion, previousVersion );
	}

	public SoftLock lockItem(Object key, Object version) throws CacheException {
		return null;
	}

	public SoftLock lockRegion() throws CacheException {
		return null;
	}

	public void unlockItem(Object key, SoftLock lock) throws CacheException {
	}

	public void unlockRegion(SoftLock lock) throws CacheException {
	}

	public boolean afterInsert(Object key, Object value, Object version) throws CacheException {
		return false;
	}

	public boolean afterUpdate(Object key, Object value, Object currentVersion, Object previousVersion, SoftLock lock)
			throws CacheException {
		return false;
	}

	@Override
	public Object generateCacheKey(Object id, EntityPersister persister, SessionFactoryImplementor factory, String tenantIdentifier) {
		return DefaultCacheKeysFactory.createEntityKey(id, persister, factory, tenantIdentifier);
	}

	@Override
	public Object getCacheKeyId(Object cacheKey) {
		return DefaultCacheKeysFactory.getEntityId(cacheKey);
	}
}


File: hibernate-infinispan/src/main/java/org/hibernate/cache/infinispan/impl/BaseTransactionalDataRegion.java
/*
 * Hibernate, Relational Persistence for Idiomatic Java
 *
 * License: GNU Lesser General Public License (LGPL), version 2.1 or later.
 * See the lgpl.txt file in the root directory or <http://www.gnu.org/licenses/lgpl-2.1.html>.
 */
package org.hibernate.cache.infinispan.impl;

import org.hibernate.cache.spi.CacheDataDescription;
import org.hibernate.cache.spi.RegionFactory;
import org.hibernate.cache.spi.TransactionalDataRegion;

import org.infinispan.AdvancedCache;

/**
 * Support for Inifinispan {@link org.hibernate.cache.spi.TransactionalDataRegion} implementors.
 *
 * @author Chris Bredesen
 * @author Galder Zamarreño
 * @since 3.5
 */
public abstract class BaseTransactionalDataRegion
		extends BaseRegion implements TransactionalDataRegion {

	private final CacheDataDescription metadata;

   /**
    * Base transactional region constructor
    *
    * @param cache instance to store transactional data
    * @param name of the transactional region
    * @param metadata for the transactional region
    * @param factory for the transactional region
    */
	public BaseTransactionalDataRegion(
			AdvancedCache cache, String name,
			CacheDataDescription metadata, RegionFactory factory) {
		super( cache, name, factory );
		this.metadata = metadata;
	}

	@Override
	public CacheDataDescription getCacheDataDescription() {
		return metadata;
	}

}


File: hibernate-infinispan/src/main/java/org/hibernate/cache/infinispan/naturalid/NaturalIdRegionImpl.java
/*
 * Hibernate, Relational Persistence for Idiomatic Java
 *
 * License: GNU Lesser General Public License (LGPL), version 2.1 or later.
 * See the lgpl.txt file in the root directory or <http://www.gnu.org/licenses/lgpl-2.1.html>.
 */
package org.hibernate.cache.infinispan.naturalid;

import org.hibernate.cache.CacheException;
import org.hibernate.cache.infinispan.access.PutFromLoadValidator;
import org.hibernate.cache.infinispan.impl.BaseTransactionalDataRegion;
import org.hibernate.cache.spi.CacheDataDescription;
import org.hibernate.cache.spi.NaturalIdRegion;
import org.hibernate.cache.spi.RegionFactory;
import org.hibernate.cache.spi.access.AccessType;
import org.hibernate.cache.spi.access.NaturalIdRegionAccessStrategy;

import org.infinispan.AdvancedCache;

/**
 * Natural ID cache region
 *
 * @author Strong Liu <stliu@hibernate.org>
 * @author Galder Zamarreño
 */
public class NaturalIdRegionImpl extends BaseTransactionalDataRegion
		implements NaturalIdRegion {

   /**
    * Constructor for the natural id region.
    *
    * @param cache instance to store natural ids
    * @param name of natural id region
    * @param metadata for the natural id region
    * @param factory for the natural id region
    */
	public NaturalIdRegionImpl(
			AdvancedCache cache, String name,
			CacheDataDescription metadata, RegionFactory factory) {
		super( cache, name, metadata, factory );
	}

	@Override
	public NaturalIdRegionAccessStrategy buildAccessStrategy(AccessType accessType) throws CacheException {
		switch ( accessType ) {
			case READ_ONLY:
				return new ReadOnlyAccess( this );
			case TRANSACTIONAL:
				return new TransactionalAccess( this );
			default:
				throw new CacheException( "Unsupported access type [" + accessType.getExternalName() + "]" );
		}
	}

	public PutFromLoadValidator getPutFromLoadValidator() {
		return new PutFromLoadValidator( cache );
	}

}


File: hibernate-infinispan/src/main/java/org/hibernate/cache/infinispan/naturalid/TransactionalAccess.java
/*
 * Hibernate, Relational Persistence for Idiomatic Java
 *
 * License: GNU Lesser General Public License (LGPL), version 2.1 or later.
 * See the lgpl.txt file in the root directory or <http://www.gnu.org/licenses/lgpl-2.1.html>.
 */
package org.hibernate.cache.infinispan.naturalid;

import org.hibernate.cache.CacheException;
import org.hibernate.cache.infinispan.access.TransactionalAccessDelegate;
import org.hibernate.cache.internal.DefaultCacheKeysFactory;
import org.hibernate.cache.spi.NaturalIdRegion;
import org.hibernate.cache.spi.access.NaturalIdRegionAccessStrategy;
import org.hibernate.cache.spi.access.SoftLock;
import org.hibernate.engine.spi.SessionImplementor;
import org.hibernate.persister.entity.EntityPersister;

/**
 * @author Strong Liu <stliu@hibernate.org>
 */
class TransactionalAccess implements NaturalIdRegionAccessStrategy {
	private final NaturalIdRegionImpl region;
	private final TransactionalAccessDelegate delegate;

	TransactionalAccess(NaturalIdRegionImpl region) {
		this.region = region;
		this.delegate = new TransactionalAccessDelegate( region, region.getPutFromLoadValidator() );
	}

	@Override
	public boolean insert(Object key, Object value) throws CacheException {
		return delegate.insert( key, value, null );
	}

	@Override
	public boolean update(Object key, Object value) throws CacheException {
		return delegate.update( key, value, null, null );
	}

	@Override
	public NaturalIdRegion getRegion() {
		return region;
	}

	@Override
	public void evict(Object key) throws CacheException {
		delegate.evict( key );
	}

	@Override
	public void evictAll() throws CacheException {
		delegate.evictAll();
	}

	@Override
	public Object get(Object key, long txTimestamp) throws CacheException {
		return delegate.get( key, txTimestamp );
	}

	@Override
	public boolean putFromLoad(Object key, Object value, long txTimestamp, Object version) throws CacheException {
		return delegate.putFromLoad( key, value, txTimestamp, version );
	}

	@Override
	public boolean putFromLoad(Object key, Object value, long txTimestamp, Object version, boolean minimalPutOverride)
			throws CacheException {
		return delegate.putFromLoad( key, value, txTimestamp, version, minimalPutOverride );
	}

	@Override
	public void remove(Object key) throws CacheException {
		delegate.remove( key );
	}

	@Override
	public void removeAll() throws CacheException {
		delegate.removeAll();
	}

	@Override
	public SoftLock lockItem(Object key, Object version) throws CacheException {
		return null;
	}

	@Override
	public SoftLock lockRegion() throws CacheException {
		return null;
	}

	@Override
	public void unlockItem(Object key, SoftLock lock) throws CacheException {
	}

	@Override
	public void unlockRegion(SoftLock lock) throws CacheException {
	}

	@Override
	public boolean afterInsert(Object key, Object value) throws CacheException {
		return false;
	}

	@Override
	public boolean afterUpdate(Object key, Object value, SoftLock lock) throws CacheException {
		return false;
	}

	@Override
	public Object generateCacheKey(Object[] naturalIdValues, EntityPersister persister, SessionImplementor session) {
		return DefaultCacheKeysFactory.createNaturalIdKey( naturalIdValues, persister, session );
	}

	@Override
	public Object[] getNaturalIdValues(Object cacheKey) {
		return DefaultCacheKeysFactory.getNaturalIdValues(cacheKey);
	}
}


File: hibernate-infinispan/src/main/java/org/hibernate/cache/infinispan/query/QueryResultsRegionImpl.java
/*
 * Hibernate, Relational Persistence for Idiomatic Java
 *
 * License: GNU Lesser General Public License (LGPL), version 2.1 or later.
 * See the lgpl.txt file in the root directory or <http://www.gnu.org/licenses/lgpl-2.1.html>.
 */
package org.hibernate.cache.infinispan.query;

import javax.transaction.Transaction;

import org.hibernate.cache.CacheException;
import org.hibernate.cache.infinispan.impl.BaseTransactionalDataRegion;
import org.hibernate.cache.infinispan.util.Caches;
import org.hibernate.cache.spi.QueryResultsRegion;
import org.hibernate.cache.spi.RegionFactory;

import org.infinispan.AdvancedCache;
import org.infinispan.context.Flag;

/**
 * Region for caching query results.
 *
 * @author Chris Bredesen
 * @author Galder Zamarreño
 * @since 3.5
 */
public class QueryResultsRegionImpl extends BaseTransactionalDataRegion implements QueryResultsRegion {

	private final AdvancedCache evictCache;
	private final AdvancedCache putCache;
	private final AdvancedCache getCache;

   /**
    * Query region constructor
    *
    * @param cache instance to store queries
    * @param name of the query region
    * @param factory for the query region
    */
	public QueryResultsRegionImpl(AdvancedCache cache, String name, RegionFactory factory) {
		super( cache, name, null, factory );
		// If Infinispan is using INVALIDATION for query cache, we don't want to propagate changes.
		// We use the Timestamps cache to manage invalidation
		final boolean localOnly = Caches.isInvalidationCache( cache );

		this.evictCache = localOnly ? Caches.localCache( cache ) : cache;

		this.putCache = localOnly ?
				Caches.failSilentWriteCache( cache, Flag.CACHE_MODE_LOCAL ) :
				Caches.failSilentWriteCache( cache );

		this.getCache = Caches.failSilentReadCache( cache );
	}

	@Override
	public void evict(Object key) throws CacheException {
		evictCache.remove( key );
	}

	@Override
	public void evictAll() throws CacheException {
		final Transaction tx = suspend();
		try {
			// Invalidate the local region and then go remote
			invalidateRegion();
			Caches.broadcastEvictAll( cache );
		}
		finally {
			resume( tx );
		}
	}

	@Override
	public Object get(Object key) throws CacheException {
		// If the region is not valid, skip cache store to avoid going remote to retrieve the query.
		// The aim of this is to maintain same logic/semantics as when state transfer was configured.
		// TODO: Once https://issues.jboss.org/browse/ISPN-835 has been resolved, revert to state transfer and remove workaround
		boolean skipCacheStore = false;
		if ( !isValid() ) {
			skipCacheStore = true;
		}

		if ( !checkValid() ) {
			return null;
		}

		// In Infinispan get doesn't acquire any locks, so no need to suspend the tx.
		// In the past, when get operations acquired locks, suspending the tx was a way
		// to avoid holding locks that would prevent updates.
		// Add a zero (or low) timeout option so we don't block
		// waiting for tx's that did a put to commit
		if ( skipCacheStore ) {
			return getCache.withFlags( Flag.SKIP_CACHE_STORE ).get( key );
		}
		else {
			return getCache.get( key );
		}
	}

	@Override
	@SuppressWarnings("unchecked")
	public void put(Object key, Object value) throws CacheException {
		if ( checkValid() ) {
			// Here we don't want to suspend the tx. If we do:
			// 1) We might be caching query results that reflect uncommitted
			// changes. No tx == no WL on cache node, so other threads
			// can prematurely see those query results
			// 2) No tx == immediate replication. More overhead, plus we
			// spread issue #1 above around the cluster

			// Add a zero (or quite low) timeout option so we don't block.
			// Ignore any TimeoutException. Basically we forego caching the
			// query result in order to avoid blocking.
			// Reads are done with suspended tx, so they should not hold the
			// lock for long.  Not caching the query result is OK, since
			// any subsequent read will just see the old result with its
			// out-of-date timestamp; that result will be discarded and the
			// db query performed again.
			putCache.put( key, value );
		}
	}

}


File: hibernate-infinispan/src/test/java/org/hibernate/test/cache/infinispan/AbstractEntityCollectionRegionTestCase.java
/*
 * Hibernate, Relational Persistence for Idiomatic Java
 *
 * License: GNU Lesser General Public License (LGPL), version 2.1 or later.
 * See the lgpl.txt file in the root directory or <http://www.gnu.org/licenses/lgpl-2.1.html>.
 */
package org.hibernate.test.cache.infinispan;

import java.util.Properties;

import org.hibernate.boot.registry.StandardServiceRegistry;
import org.hibernate.boot.registry.StandardServiceRegistryBuilder;
import org.hibernate.cache.infinispan.InfinispanRegionFactory;
import org.hibernate.cache.spi.CacheDataDescription;
import org.hibernate.cache.spi.RegionFactory;
import org.hibernate.cache.spi.TransactionalDataRegion;
import org.hibernate.cache.spi.access.AccessType;
import org.hibernate.test.cache.infinispan.util.CacheTestUtil;
import org.junit.Test;

import static org.junit.Assert.assertEquals;
import static org.junit.Assert.assertNotNull;
import static org.junit.Assert.assertTrue;

/**
 * Base class for tests of EntityRegion and CollectionRegion implementations.
 *
 * @author Galder Zamarreño
 * @since 3.5
 */
public abstract class AbstractEntityCollectionRegionTestCase extends AbstractRegionImplTestCase {
	@Test
	public void testSupportedAccessTypes() throws Exception {
		supportedAccessTypeTest();
	}

	private void supportedAccessTypeTest() throws Exception {
		StandardServiceRegistryBuilder ssrb = CacheTestUtil.buildBaselineStandardServiceRegistryBuilder(
				"test",
				InfinispanRegionFactory.class,
				true,
				false
		);
		ssrb.applySetting( InfinispanRegionFactory.ENTITY_CACHE_RESOURCE_PROP, "entity" );
		final StandardServiceRegistry registry = ssrb.build();
		try {
			InfinispanRegionFactory regionFactory = CacheTestUtil.startRegionFactory(
					registry,
					getCacheTestSupport()
			);
			supportedAccessTypeTest( regionFactory, CacheTestUtil.toProperties( ssrb.getSettings() ) );
		}
		finally {
			StandardServiceRegistryBuilder.destroy( registry );
		}
	}

	/**
	 * Creates a Region using the given factory, and then ensure that it handles calls to
	 * buildAccessStrategy as expected when all the various {@link AccessType}s are passed as
	 * arguments.
	 */
	protected abstract void supportedAccessTypeTest(RegionFactory regionFactory, Properties properties);

	@Test
	public void testIsTransactionAware() throws Exception {
		StandardServiceRegistryBuilder ssrb = CacheTestUtil.buildBaselineStandardServiceRegistryBuilder(
				"test",
				InfinispanRegionFactory.class,
				true,
				false
		);
		final StandardServiceRegistry registry = ssrb.build();
		try {
			Properties properties = CacheTestUtil.toProperties( ssrb.getSettings() );
			InfinispanRegionFactory regionFactory = CacheTestUtil.startRegionFactory(
					registry,
					getCacheTestSupport()
			);
			TransactionalDataRegion region = (TransactionalDataRegion) createRegion(
					regionFactory,
					"test/test",
					properties,
					getCacheDataDescription()
			);
			assertTrue( "Region is transaction-aware", region.isTransactionAware() );
			CacheTestUtil.stopRegionFactory( regionFactory, getCacheTestSupport() );
		}
		finally {
			StandardServiceRegistryBuilder.destroy( registry );
		}
	}

	@Test
	public void testGetCacheDataDescription() throws Exception {
		StandardServiceRegistryBuilder ssrb = CacheTestUtil.buildBaselineStandardServiceRegistryBuilder(
				"test",
				InfinispanRegionFactory.class,
				true,
				false
		);
		final StandardServiceRegistry registry = ssrb.build();
		try {
			Properties properties = CacheTestUtil.toProperties( ssrb.getSettings() );
			InfinispanRegionFactory regionFactory = CacheTestUtil.startRegionFactory(
					registry,
					getCacheTestSupport()
			);
			TransactionalDataRegion region = (TransactionalDataRegion) createRegion(
					regionFactory,
					"test/test",
					properties,
					getCacheDataDescription()
			);
			CacheDataDescription cdd = region.getCacheDataDescription();
			assertNotNull( cdd );
			CacheDataDescription expected = getCacheDataDescription();
			assertEquals( expected.isMutable(), cdd.isMutable() );
			assertEquals( expected.isVersioned(), cdd.isVersioned() );
			assertEquals( expected.getVersionComparator(), cdd.getVersionComparator() );
		}
		finally {
			StandardServiceRegistryBuilder.destroy( registry );
		}
	}
}


File: hibernate-infinispan/src/test/java/org/hibernate/test/cache/infinispan/AbstractGeneralDataRegionTestCase.java
/*
 * Hibernate, Relational Persistence for Idiomatic Java
 *
 * License: GNU Lesser General Public License (LGPL), version 2.1 or later.
 * See the lgpl.txt file in the root directory or <http://www.gnu.org/licenses/lgpl-2.1.html>.
 */
package org.hibernate.test.cache.infinispan;

import java.util.Properties;
import java.util.Set;
import java.util.concurrent.Callable;
import java.util.concurrent.TimeUnit;

import org.hibernate.boot.registry.StandardServiceRegistry;
import org.hibernate.boot.registry.StandardServiceRegistryBuilder;
import org.hibernate.cache.infinispan.InfinispanRegionFactory;
import org.hibernate.cache.spi.GeneralDataRegion;
import org.hibernate.cache.spi.QueryResultsRegion;
import org.hibernate.cache.spi.Region;
import org.hibernate.test.cache.infinispan.util.CacheTestUtil;
import org.infinispan.AdvancedCache;
import org.infinispan.transaction.tm.BatchModeTransactionManager;
import org.jboss.logging.Logger;
import org.junit.Test;

import static org.hibernate.test.cache.infinispan.util.CacheTestUtil.assertEqualsEventually;
import static org.junit.Assert.assertEquals;
import static org.junit.Assert.assertNull;

/**
 * Base class for tests of QueryResultsRegion and TimestampsRegion.
 *
 * @author Galder Zamarreño
 * @since 3.5
 */
public abstract class AbstractGeneralDataRegionTestCase extends AbstractRegionImplTestCase {
	private static final Logger log = Logger.getLogger( AbstractGeneralDataRegionTestCase.class );

	protected static final String KEY = "Key";

	protected static final String VALUE1 = "value1";
	protected static final String VALUE2 = "value2";

	protected StandardServiceRegistryBuilder createStandardServiceRegistryBuilder() {
		return CacheTestUtil.buildBaselineStandardServiceRegistryBuilder(
				"test",
				InfinispanRegionFactory.class,
				false,
				true
		);
	}

	@Override
	protected void putInRegion(Region region, Object key, Object value) {
		((GeneralDataRegion) region).put( key, value );
	}

	@Override
	protected void removeFromRegion(Region region, Object key) {
		((GeneralDataRegion) region).evict( key );
	}

	@Test
	public void testEvict() throws Exception {
		evictOrRemoveTest();
	}

	private void evictOrRemoveTest() throws Exception {
		final StandardServiceRegistryBuilder ssrb = createStandardServiceRegistryBuilder();
		StandardServiceRegistry registry1 = ssrb.build();
		StandardServiceRegistry registry2 = ssrb.build();
		try {
			InfinispanRegionFactory regionFactory = CacheTestUtil.startRegionFactory(
					registry1,
					getCacheTestSupport()
			);

			final Properties properties = CacheTestUtil.toProperties( ssrb.getSettings() );

			boolean invalidation = false;

			// Sleep a bit to avoid concurrent FLUSH problem
			avoidConcurrentFlush();

			final GeneralDataRegion localRegion = (GeneralDataRegion) createRegion(
					regionFactory,
					getStandardRegionName( REGION_PREFIX ),
					properties,
					null
			);

			regionFactory = CacheTestUtil.startRegionFactory(
					registry2,
					getCacheTestSupport()
			);

			final GeneralDataRegion remoteRegion = (GeneralDataRegion) createRegion(
					regionFactory,
					getStandardRegionName( REGION_PREFIX ),
					properties,
					null
			);
			assertNull( "local is clean", localRegion.get( KEY ) );
			assertNull( "remote is clean", remoteRegion.get( KEY ) );

			regionPut( localRegion );

			Callable<Object> getFromLocalRegion = new Callable<Object>() {
				@Override
				public Object call() throws Exception {
					return localRegion.get(KEY);
				}
			};
			Callable<Object> getFromRemoteRegion = new Callable<Object>() {
				@Override
				public Object call() throws Exception {
					return remoteRegion.get(KEY);
				}
			};

			assertEqualsEventually(VALUE1, getFromLocalRegion, 10, TimeUnit.SECONDS);
			Object expected = invalidation ? null : VALUE1;
			assertEqualsEventually(expected, getFromRemoteRegion, 10, TimeUnit.SECONDS);

			regionEvict(localRegion);

			assertEqualsEventually(null, getFromLocalRegion, 10, TimeUnit.SECONDS);
			assertEqualsEventually(null, getFromRemoteRegion, 10, TimeUnit.SECONDS);
		} finally {
			StandardServiceRegistryBuilder.destroy( registry1 );
			StandardServiceRegistryBuilder.destroy( registry2 );
		}
	}

   protected void regionEvict(GeneralDataRegion region) throws Exception {
      region.evict(KEY);
   }

   protected void regionPut(GeneralDataRegion region) throws Exception {
      region.put(KEY, VALUE1);
   }

   protected abstract String getStandardRegionName(String regionPrefix);

	/**
	 * Test method for {@link QueryResultsRegion#evictAll()}.
	 * <p/>
	 * FIXME add testing of the "immediately without regard for transaction isolation" bit in the
	 * CollectionRegionAccessStrategy API.
	 */
	public void testEvictAll() throws Exception {
		evictOrRemoveAllTest( "entity" );
	}

	private void evictOrRemoveAllTest(String configName) throws Exception {
		final StandardServiceRegistryBuilder ssrb = createStandardServiceRegistryBuilder();
		StandardServiceRegistry registry1 = ssrb.build();
		StandardServiceRegistry registry2 = ssrb.build();

		try {
			final Properties properties = CacheTestUtil.toProperties( ssrb.getSettings() );

			InfinispanRegionFactory regionFactory = CacheTestUtil.startRegionFactory(
					registry1,
					getCacheTestSupport()
			);
			AdvancedCache localCache = getInfinispanCache( regionFactory );

			// Sleep a bit to avoid concurrent FLUSH problem
			avoidConcurrentFlush();

			GeneralDataRegion localRegion = (GeneralDataRegion) createRegion(
					regionFactory,
					getStandardRegionName( REGION_PREFIX ),
					properties,
					null
			);

			regionFactory = CacheTestUtil.startRegionFactory(
					registry2,
					getCacheTestSupport()
			);
			AdvancedCache remoteCache = getInfinispanCache( regionFactory );

			// Sleep a bit to avoid concurrent FLUSH problem
			avoidConcurrentFlush();

			GeneralDataRegion remoteRegion = (GeneralDataRegion) createRegion(
					regionFactory,
					getStandardRegionName( REGION_PREFIX ),
					properties,
					null
			);

			Set keys = localCache.keySet();
			assertEquals( "No valid children in " + keys, 0, getValidKeyCount( keys ) );

			keys = remoteCache.keySet();
			assertEquals( "No valid children in " + keys, 0, getValidKeyCount( keys ) );

			assertNull( "local is clean", localRegion.get( KEY ) );
			assertNull( "remote is clean", remoteRegion.get( KEY ) );

			regionPut(localRegion);
			assertEquals( VALUE1, localRegion.get( KEY ) );

			// Allow async propagation
			sleep( 250 );

			regionPut(remoteRegion);
			assertEquals( VALUE1, remoteRegion.get( KEY ) );

			// Allow async propagation
			sleep( 250 );

			localRegion.evictAll();

			// allow async propagation
			sleep( 250 );
			// This should re-establish the region root node in the optimistic case
			assertNull( localRegion.get( KEY ) );
			assertEquals( "No valid children in " + keys, 0, getValidKeyCount( localCache.keySet() ) );

			// Re-establishing the region root on the local node doesn't
			// propagate it to other nodes. Do a get on the remote node to re-establish
			// This only adds a node in the case of optimistic locking
			assertEquals( null, remoteRegion.get( KEY ) );
			assertEquals( "No valid children in " + keys, 0, getValidKeyCount( remoteCache.keySet() ) );

			assertEquals( "local is clean", null, localRegion.get( KEY ) );
			assertEquals( "remote is clean", null, remoteRegion.get( KEY ) );
		}
		finally {
			StandardServiceRegistryBuilder.destroy( registry1 );
			StandardServiceRegistryBuilder.destroy( registry2 );
		}
	}

	protected void rollback() {
		try {
			BatchModeTransactionManager.getInstance().rollback();
		}
		catch (Exception e) {
			log.error( e.getMessage(), e );
		}
	}
}

File: hibernate-infinispan/src/test/java/org/hibernate/test/cache/infinispan/AbstractRegionImplTestCase.java
/*
 * Hibernate, Relational Persistence for Idiomatic Java
 *
 * License: GNU Lesser General Public License (LGPL), version 2.1 or later.
 * See the lgpl.txt file in the root directory or <http://www.gnu.org/licenses/lgpl-2.1.html>.
 */
package org.hibernate.test.cache.infinispan;

import java.util.Properties;

import org.hibernate.cache.infinispan.InfinispanRegionFactory;
import org.hibernate.cache.internal.CacheDataDescriptionImpl;
import org.hibernate.cache.spi.CacheDataDescription;
import org.hibernate.cache.spi.Region;
import org.hibernate.internal.util.compare.ComparableComparator;
import org.infinispan.AdvancedCache;

/**
 * Base class for tests of Region implementations.
 * 
 * @author Galder Zamarreño
 * @since 3.5
 */
public abstract class AbstractRegionImplTestCase extends AbstractNonFunctionalTestCase {

   protected abstract AdvancedCache getInfinispanCache(InfinispanRegionFactory regionFactory);

   protected abstract Region createRegion(InfinispanRegionFactory regionFactory, String regionName, Properties properties, CacheDataDescription cdd);

   protected abstract void putInRegion(Region region, Object key, Object value);

   protected abstract void removeFromRegion(Region region, Object key);

   protected CacheDataDescription getCacheDataDescription() {
      return new CacheDataDescriptionImpl(true, true, ComparableComparator.INSTANCE);
   }

}


File: hibernate-infinispan/src/test/java/org/hibernate/test/cache/infinispan/InfinispanRegionFactoryTestCase.java
/*
 * Hibernate, Relational Persistence for Idiomatic Java
 *
 * License: GNU Lesser General Public License (LGPL), version 2.1 or later.
 * See the lgpl.txt file in the root directory or <http://www.gnu.org/licenses/lgpl-2.1.html>.
 */
package org.hibernate.test.cache.infinispan;

import java.util.Properties;
import javax.transaction.TransactionManager;

import org.hibernate.boot.internal.SessionFactoryBuilderImpl;
import org.hibernate.boot.internal.SessionFactoryOptionsImpl;
import org.hibernate.boot.spi.SessionFactoryOptions;
import org.hibernate.cache.CacheException;
import org.hibernate.cache.infinispan.InfinispanRegionFactory;
import org.hibernate.cache.infinispan.collection.CollectionRegionImpl;
import org.hibernate.cache.infinispan.entity.EntityRegionImpl;
import org.hibernate.cache.infinispan.query.QueryResultsRegionImpl;
import org.hibernate.cache.infinispan.timestamp.TimestampsRegionImpl;
import org.hibernate.cache.infinispan.tm.HibernateTransactionManagerLookup;
import org.hibernate.cache.internal.CacheDataDescriptionImpl;
import org.hibernate.cache.spi.CacheDataDescription;
import org.hibernate.cfg.Environment;
import org.hibernate.engine.transaction.jta.platform.internal.AbstractJtaPlatform;
import org.hibernate.engine.transaction.jta.platform.internal.JBossStandAloneJtaPlatform;
import org.hibernate.service.ServiceRegistry;

import org.hibernate.testing.ServiceRegistryBuilder;
import org.hibernate.test.cache.infinispan.functional.SingleNodeTestCase;
import org.hibernate.testing.boot.ServiceRegistryTestingImpl;
import org.junit.Test;

import org.infinispan.AdvancedCache;
import org.infinispan.configuration.cache.CacheMode;
import org.infinispan.configuration.cache.Configuration;
import org.infinispan.configuration.cache.ConfigurationBuilder;
import org.infinispan.configuration.global.GlobalConfigurationBuilder;
import org.infinispan.eviction.EvictionStrategy;
import org.infinispan.manager.DefaultCacheManager;
import org.infinispan.manager.EmbeddedCacheManager;
import org.infinispan.test.TestingUtil;
import org.infinispan.transaction.TransactionMode;

import static org.junit.Assert.assertEquals;
import static org.junit.Assert.assertFalse;
import static org.junit.Assert.assertNotNull;
import static org.junit.Assert.assertNull;
import static org.junit.Assert.assertTrue;
import static org.junit.Assert.fail;

/**
 * InfinispanRegionFactoryTestCase.
 * 
 * @author Galder Zamarreño
 * @since 3.5
 */
public class InfinispanRegionFactoryTestCase  {
   private static CacheDataDescription MUTABLE_NON_VERSIONED = new CacheDataDescriptionImpl(true, false, null);
   private static CacheDataDescription IMMUTABLE_NON_VERSIONED = new CacheDataDescriptionImpl(false, false, null);

   @Test
   public void testConfigurationProcessing() {
      final String person = "com.acme.Person";
      final String addresses = "com.acme.Person.addresses";
      Properties p = createProperties();
      p.setProperty("hibernate.cache.infinispan.com.acme.Person.cfg", "person-cache");
      p.setProperty("hibernate.cache.infinispan.com.acme.Person.eviction.strategy", "LRU");
      p.setProperty("hibernate.cache.infinispan.com.acme.Person.eviction.wake_up_interval", "2000");
      p.setProperty("hibernate.cache.infinispan.com.acme.Person.eviction.max_entries", "5000");
      p.setProperty("hibernate.cache.infinispan.com.acme.Person.expiration.lifespan", "60000");
      p.setProperty("hibernate.cache.infinispan.com.acme.Person.expiration.max_idle", "30000");
      p.setProperty("hibernate.cache.infinispan.com.acme.Person.addresses.cfg", "person-addresses-cache");
      p.setProperty("hibernate.cache.infinispan.com.acme.Person.addresses.expiration.lifespan", "120000");
      p.setProperty("hibernate.cache.infinispan.com.acme.Person.addresses.expiration.max_idle", "60000");
      p.setProperty("hibernate.cache.infinispan.query.cfg", "my-query-cache");
      p.setProperty("hibernate.cache.infinispan.query.eviction.strategy", "LIRS");
      p.setProperty("hibernate.cache.infinispan.query.eviction.wake_up_interval", "3000");
      p.setProperty("hibernate.cache.infinispan.query.eviction.max_entries", "10000");

      InfinispanRegionFactory factory = createRegionFactory(p);

      try {
         assertEquals("entity", factory.getTypeOverrides().get("entity").getCacheName());
         assertEquals("entity", factory.getTypeOverrides().get("collection").getCacheName());
         assertEquals("timestamps", factory.getTypeOverrides().get("timestamps").getCacheName());

         assertEquals("person-cache", factory.getTypeOverrides().get(person).getCacheName());
         assertEquals(EvictionStrategy.LRU, factory.getTypeOverrides().get(person).getEvictionStrategy());
         assertEquals(2000, factory.getTypeOverrides().get(person).getEvictionWakeUpInterval());
         assertEquals(5000, factory.getTypeOverrides().get(person).getEvictionMaxEntries());
         assertEquals(60000, factory.getTypeOverrides().get(person).getExpirationLifespan());
         assertEquals(30000, factory.getTypeOverrides().get(person).getExpirationMaxIdle());

         assertEquals("person-addresses-cache", factory.getTypeOverrides().get(addresses).getCacheName());
         assertEquals(120000, factory.getTypeOverrides().get(addresses).getExpirationLifespan());
         assertEquals(60000, factory.getTypeOverrides().get(addresses).getExpirationMaxIdle());

         assertEquals("my-query-cache", factory.getTypeOverrides().get("query").getCacheName());
         assertEquals(EvictionStrategy.LIRS, factory.getTypeOverrides().get("query").getEvictionStrategy());
         assertEquals(3000, factory.getTypeOverrides().get("query").getEvictionWakeUpInterval());
         assertEquals(10000, factory.getTypeOverrides().get("query").getEvictionMaxEntries());
      } finally {
         factory.stop();
      }
   }

   @Test
   public void testBuildEntityCollectionRegionsPersonPlusEntityCollectionOverrides() {
      final String person = "com.acme.Person";
      final String address = "com.acme.Address";
      final String car = "com.acme.Car";
      final String addresses = "com.acme.Person.addresses";
      final String parts = "com.acme.Car.parts";
      Properties p = createProperties();
      // First option, cache defined for entity and overrides for generic entity data type and entity itself.
      p.setProperty("hibernate.cache.infinispan.com.acme.Person.cfg", "person-cache");
      p.setProperty("hibernate.cache.infinispan.com.acme.Person.eviction.strategy", "LRU");
      p.setProperty("hibernate.cache.infinispan.com.acme.Person.eviction.wake_up_interval", "2000");
      p.setProperty("hibernate.cache.infinispan.com.acme.Person.eviction.max_entries", "5000");
      p.setProperty("hibernate.cache.infinispan.com.acme.Person.expiration.lifespan", "60000");
      p.setProperty("hibernate.cache.infinispan.com.acme.Person.expiration.max_idle", "30000");
      p.setProperty("hibernate.cache.infinispan.entity.cfg", "myentity-cache");
      p.setProperty("hibernate.cache.infinispan.entity.eviction.strategy", "LIRS");
      p.setProperty("hibernate.cache.infinispan.entity.eviction.wake_up_interval", "3000");
      p.setProperty("hibernate.cache.infinispan.entity.eviction.max_entries", "20000");
      p.setProperty("hibernate.cache.infinispan.com.acme.Person.addresses.cfg", "addresses-cache");
      p.setProperty("hibernate.cache.infinispan.com.acme.Person.addresses.eviction.strategy", "LIRS");
      p.setProperty("hibernate.cache.infinispan.com.acme.Person.addresses.eviction.wake_up_interval", "2500");
      p.setProperty("hibernate.cache.infinispan.com.acme.Person.addresses.eviction.max_entries", "5500");
      p.setProperty("hibernate.cache.infinispan.com.acme.Person.addresses.expiration.lifespan", "65000");
      p.setProperty("hibernate.cache.infinispan.com.acme.Person.addresses.expiration.max_idle", "35000");
      p.setProperty("hibernate.cache.infinispan.collection.cfg", "mycollection-cache");
      p.setProperty("hibernate.cache.infinispan.collection.eviction.strategy", "LRU");
      p.setProperty("hibernate.cache.infinispan.collection.eviction.wake_up_interval", "3500");
      p.setProperty("hibernate.cache.infinispan.collection.eviction.max_entries", "25000");
      InfinispanRegionFactory factory = createRegionFactory(p);
      try {
         EmbeddedCacheManager manager = factory.getCacheManager();
         assertFalse(manager.getCacheManagerConfiguration()
               .globalJmxStatistics().enabled());
         assertNotNull(factory.getTypeOverrides().get(person));
         assertFalse(factory.getDefinedConfigurations().contains(person));
         assertNotNull(factory.getTypeOverrides().get(addresses));
         assertFalse(factory.getDefinedConfigurations().contains(addresses));
         AdvancedCache cache;

         EntityRegionImpl region = (EntityRegionImpl) factory.buildEntityRegion(person, p, MUTABLE_NON_VERSIONED);
         assertNotNull(factory.getTypeOverrides().get(person));
         assertTrue(factory.getDefinedConfigurations().contains(person));
         assertNull(factory.getTypeOverrides().get(address));
         cache = region.getCache();
         Configuration cacheCfg = cache.getCacheConfiguration();
         assertEquals(EvictionStrategy.LRU, cacheCfg.eviction().strategy());
         assertEquals(2000, cacheCfg.expiration().wakeUpInterval());
         assertEquals(5000, cacheCfg.eviction().maxEntries());
         assertEquals(60000, cacheCfg.expiration().lifespan());
         assertEquals(30000, cacheCfg.expiration().maxIdle());
         assertFalse(cacheCfg.jmxStatistics().enabled());

         region = (EntityRegionImpl) factory.buildEntityRegion(address, p, MUTABLE_NON_VERSIONED);
         assertNotNull(factory.getTypeOverrides().get(person));
         assertTrue(factory.getDefinedConfigurations().contains(person));
         assertNull(factory.getTypeOverrides().get(address));
         cache = region.getCache();
         cacheCfg = cache.getCacheConfiguration();
         assertEquals(EvictionStrategy.LIRS, cacheCfg.eviction().strategy());
         assertEquals(3000, cacheCfg.expiration().wakeUpInterval());
         assertEquals(20000, cacheCfg.eviction().maxEntries());
         assertFalse(cacheCfg.jmxStatistics().enabled());

         region = (EntityRegionImpl) factory.buildEntityRegion(car, p, MUTABLE_NON_VERSIONED);
         assertNotNull(factory.getTypeOverrides().get(person));
         assertTrue(factory.getDefinedConfigurations().contains(person));
         assertNull(factory.getTypeOverrides().get(address));
         cache = region.getCache();
         cacheCfg = cache.getCacheConfiguration();
         assertEquals(EvictionStrategy.LIRS, cacheCfg.eviction().strategy());
         assertEquals(3000, cacheCfg.expiration().wakeUpInterval());
         assertEquals(20000, cacheCfg.eviction().maxEntries());
         assertFalse(cacheCfg.jmxStatistics().enabled());

         CollectionRegionImpl collectionRegion = (CollectionRegionImpl)
               factory.buildCollectionRegion(addresses, p, MUTABLE_NON_VERSIONED);
         assertNotNull(factory.getTypeOverrides().get(addresses));
         assertTrue(factory.getDefinedConfigurations().contains(person));
         assertNull(factory.getTypeOverrides().get(parts));
         cache = collectionRegion .getCache();
         cacheCfg = cache.getCacheConfiguration();
         assertEquals(EvictionStrategy.LIRS, cacheCfg.eviction().strategy());
         assertEquals(2500, cacheCfg.expiration().wakeUpInterval());
         assertEquals(5500, cacheCfg.eviction().maxEntries());
         assertEquals(65000, cacheCfg.expiration().lifespan());
         assertEquals(35000, cacheCfg.expiration().maxIdle());
         assertFalse(cacheCfg.jmxStatistics().enabled());

         collectionRegion = (CollectionRegionImpl) factory.buildCollectionRegion(parts, p, MUTABLE_NON_VERSIONED);
         assertNotNull(factory.getTypeOverrides().get(addresses));
         assertTrue(factory.getDefinedConfigurations().contains(addresses));
         assertNull(factory.getTypeOverrides().get(parts));
         cache = collectionRegion.getCache();
         cacheCfg = cache.getCacheConfiguration();
         assertEquals(EvictionStrategy.LRU, cacheCfg.eviction().strategy());
         assertEquals(3500, cacheCfg.expiration().wakeUpInterval());
         assertEquals(25000, cacheCfg.eviction().maxEntries());
         assertFalse(cacheCfg.jmxStatistics().enabled());

         collectionRegion = (CollectionRegionImpl) factory.buildCollectionRegion(parts, p, MUTABLE_NON_VERSIONED);
         assertNotNull(factory.getTypeOverrides().get(addresses));
         assertTrue(factory.getDefinedConfigurations().contains(addresses));
         assertNull(factory.getTypeOverrides().get(parts));
         cache = collectionRegion.getCache();
         cacheCfg = cache.getCacheConfiguration();
         assertEquals(EvictionStrategy.LRU, cacheCfg.eviction().strategy());
         assertEquals(3500, cacheCfg.expiration().wakeUpInterval());
         assertEquals(25000, cacheCfg.eviction().maxEntries());
         assertFalse(cacheCfg.jmxStatistics().enabled());
      } finally {
         factory.stop();
      }
   }

   @Test
   public void testBuildEntityCollectionRegionOverridesOnly() {
      AdvancedCache cache;
      Properties p = createProperties();
      p.setProperty("hibernate.cache.infinispan.entity.eviction.strategy", "LIRS");
      p.setProperty("hibernate.cache.infinispan.entity.eviction.wake_up_interval", "3000");
      p.setProperty("hibernate.cache.infinispan.entity.eviction.max_entries", "30000");
      p.setProperty("hibernate.cache.infinispan.collection.eviction.strategy", "LRU");
      p.setProperty("hibernate.cache.infinispan.collection.eviction.wake_up_interval", "3500");
      p.setProperty("hibernate.cache.infinispan.collection.eviction.max_entries", "35000");
      InfinispanRegionFactory factory = createRegionFactory(p);
      try {
         factory.getCacheManager();
         EntityRegionImpl region = (EntityRegionImpl) factory.buildEntityRegion("com.acme.Address", p, MUTABLE_NON_VERSIONED);
         assertNull(factory.getTypeOverrides().get("com.acme.Address"));
         cache = region.getCache();
         Configuration cacheCfg = cache.getCacheConfiguration();
         assertEquals(EvictionStrategy.LIRS, cacheCfg.eviction().strategy());
         assertEquals(3000, cacheCfg.expiration().wakeUpInterval());
         assertEquals(30000, cacheCfg.eviction().maxEntries());
         // Max idle value comes from base XML configuration
         assertEquals(100000, cacheCfg.expiration().maxIdle());

         CollectionRegionImpl collectionRegion = (CollectionRegionImpl)
               factory.buildCollectionRegion("com.acme.Person.addresses", p, MUTABLE_NON_VERSIONED);
         assertNull(factory.getTypeOverrides().get("com.acme.Person.addresses"));
         cache = collectionRegion.getCache();
         cacheCfg = cache.getCacheConfiguration();
         assertEquals(EvictionStrategy.LRU, cacheCfg.eviction().strategy());
         assertEquals(3500, cacheCfg.expiration().wakeUpInterval());
         assertEquals(35000, cacheCfg.eviction().maxEntries());
         assertEquals(100000, cacheCfg.expiration().maxIdle());
      } finally {
         factory.stop();
      }
   }
   @Test
   public void testBuildEntityRegionPersonPlusEntityOverridesWithoutCfg() {
      final String person = "com.acme.Person";
      Properties p = createProperties();
      // Third option, no cache defined for entity and overrides for generic entity data type and entity itself.
      p.setProperty("hibernate.cache.infinispan.com.acme.Person.eviction.strategy", "LRU");
      p.setProperty("hibernate.cache.infinispan.com.acme.Person.expiration.lifespan", "60000");
      p.setProperty("hibernate.cache.infinispan.com.acme.Person.expiration.max_idle", "30000");
      p.setProperty("hibernate.cache.infinispan.entity.cfg", "myentity-cache");
      p.setProperty("hibernate.cache.infinispan.entity.eviction.strategy", "FIFO");
      p.setProperty("hibernate.cache.infinispan.entity.eviction.wake_up_interval", "3000");
      p.setProperty("hibernate.cache.infinispan.entity.eviction.max_entries", "10000");
      InfinispanRegionFactory factory = createRegionFactory(p);
      try {
         factory.getCacheManager();
         assertNotNull( factory.getTypeOverrides().get( person ) );
         assertFalse( factory.getDefinedConfigurations().contains( person ) );
         EntityRegionImpl region = (EntityRegionImpl) factory.buildEntityRegion( person, p, MUTABLE_NON_VERSIONED );
         assertNotNull(factory.getTypeOverrides().get(person));
         assertTrue( factory.getDefinedConfigurations().contains( person ) );
         AdvancedCache cache = region.getCache();
         Configuration cacheCfg = cache.getCacheConfiguration();
         assertEquals(EvictionStrategy.LRU, cacheCfg.eviction().strategy());
         assertEquals(3000, cacheCfg.expiration().wakeUpInterval());
         assertEquals(10000, cacheCfg.eviction().maxEntries());
         assertEquals(60000, cacheCfg.expiration().lifespan());
         assertEquals(30000, cacheCfg.expiration().maxIdle());
      } finally {
         factory.stop();
      }
   }

   @Test
   public void testBuildImmutableEntityRegion() {
      AdvancedCache cache;
      Properties p = new Properties();
      InfinispanRegionFactory factory = createRegionFactory(p);
      try {
         factory.getCacheManager();
         EntityRegionImpl region = (EntityRegionImpl) factory.buildEntityRegion("com.acme.Address", p, IMMUTABLE_NON_VERSIONED);
         assertNull( factory.getTypeOverrides().get( "com.acme.Address" ) );
         cache = region.getCache();
         Configuration cacheCfg = cache.getCacheConfiguration();
         assertEquals("Immutable entity should get non-transactional cache", TransactionMode.NON_TRANSACTIONAL, cacheCfg.transaction().transactionMode());
      } finally {
         factory.stop();
      }
   }

   @Test(expected = CacheException.class)
   public void testTimestampValidation() {
      Properties p = createProperties();
      final DefaultCacheManager manager = new DefaultCacheManager(GlobalConfigurationBuilder.defaultClusteredBuilder().build());
      try {
         InfinispanRegionFactory factory = createRegionFactory(manager, p);
         ConfigurationBuilder builder = new ConfigurationBuilder();
         builder.clustering().cacheMode(CacheMode.INVALIDATION_SYNC);
         manager.defineConfiguration( "timestamps", builder.build() );
         factory.start(null, p);
         fail( "Should have failed saying that invalidation is not allowed for timestamp caches." );
      } finally {
         TestingUtil.killCacheManagers( manager );
      }
   }

   @Test
   public void testBuildDefaultTimestampsRegion() {
      final String timestamps = "org.hibernate.cache.spi.UpdateTimestampsCache";
      Properties p = createProperties();
      InfinispanRegionFactory factory = createRegionFactory(p);
      try {
         assertTrue(factory.getDefinedConfigurations().contains("timestamps"));
         assertTrue(factory.getTypeOverrides().get("timestamps")
               .getCacheName().equals("timestamps"));
         TimestampsRegionImpl region = (TimestampsRegionImpl)
               factory.buildTimestampsRegion(timestamps, p);
         AdvancedCache cache = region.getCache();
         Configuration cacheCfg = cache.getCacheConfiguration();
         assertEquals( EvictionStrategy.NONE, cacheCfg.eviction().strategy() );
         assertEquals( CacheMode.REPL_ASYNC, cacheCfg.clustering().cacheMode() );
         assertFalse( cacheCfg.jmxStatistics().enabled() );
      } finally {
         factory.stop();
      }
   }

   @Test
   public void testBuildDiffCacheNameTimestampsRegion() {
      final String timestamps = "org.hibernate.cache.spi.UpdateTimestampsCache";
      Properties p = createProperties();
      p.setProperty("hibernate.cache.infinispan.timestamps.cfg", "unrecommended-timestamps");
      InfinispanRegionFactory factory = createRegionFactory(p);
      try {
         EmbeddedCacheManager manager = factory.getCacheManager();
         assertFalse(factory.getDefinedConfigurations().contains("timestamp"));
         assertTrue(factory.getDefinedConfigurations().contains("unrecommended-timestamps"));
         assertTrue(factory.getTypeOverrides().get("timestamps").getCacheName().equals("unrecommended-timestamps"));
         ConfigurationBuilder builder = new ConfigurationBuilder();
         builder.clustering().stateTransfer().fetchInMemoryState(true);
         builder.clustering().cacheMode( CacheMode.REPL_SYNC );
         manager.defineConfiguration( "unrecommended-timestamps", builder.build() );
         TimestampsRegionImpl region = (TimestampsRegionImpl) factory.buildTimestampsRegion(timestamps, p);
         AdvancedCache cache = region.getCache();
         Configuration cacheCfg = cache.getCacheConfiguration();
         assertEquals(EvictionStrategy.NONE, cacheCfg.eviction().strategy());
         assertEquals(CacheMode.REPL_SYNC, cacheCfg.clustering().cacheMode());
         assertFalse( cacheCfg.storeAsBinary().enabled() );
         assertFalse(cacheCfg.jmxStatistics().enabled());
      } finally {
         factory.stop();
      }
   }

   @Test
   public void testBuildTimestamRegionWithCacheNameOverride() {
      final String timestamps = "org.hibernate.cache.spi.UpdateTimestampsCache";
      Properties p = createProperties();
      p.setProperty("hibernate.cache.infinispan.timestamps.cfg", "mytimestamps-cache");
      InfinispanRegionFactory factory = createRegionFactory(p);
      try {
         factory.buildTimestampsRegion(timestamps, p);
         assertTrue(factory.getDefinedConfigurations().contains("mytimestamps-cache"));
      } finally {
         factory.stop();
      }
   }

   @Test
   public void testBuildTimestamRegionWithFifoEvictionOverride() {
      final String timestamps = "org.hibernate.cache.spi.UpdateTimestampsCache";
      Properties p = createProperties();
      p.setProperty("hibernate.cache.infinispan.timestamps.cfg", "mytimestamps-cache");
      p.setProperty("hibernate.cache.infinispan.timestamps.eviction.strategy", "FIFO");
      p.setProperty("hibernate.cache.infinispan.timestamps.eviction.wake_up_interval", "3000");
      p.setProperty("hibernate.cache.infinispan.timestamps.eviction.max_entries", "10000");
      InfinispanRegionFactory factory = null;
      try {
         factory = createRegionFactory(p);
         factory.buildTimestampsRegion(timestamps, p);
         assertTrue( factory.getDefinedConfigurations().contains( "mytimestamps-cache" ) );
         fail( "Should fail cos no eviction configurations are allowed for timestamp caches" );
      } catch(CacheException ce) {
      } finally {
         if (factory != null) factory.stop();
      }
   }

   @Test
   public void testBuildTimestamRegionWithNoneEvictionOverride() {
      final String timestamps = "org.hibernate.cache.spi.UpdateTimestampsCache";
      Properties p = createProperties();
      p.setProperty("hibernate.cache.infinispan.timestamps.cfg", "timestamps-none-eviction");
      p.setProperty("hibernate.cache.infinispan.timestamps.eviction.strategy", "NONE");
      p.setProperty("hibernate.cache.infinispan.timestamps.eviction.wake_up_interval", "3000");
      p.setProperty("hibernate.cache.infinispan.timestamps.eviction.max_entries", "0");
      InfinispanRegionFactory factory = createRegionFactory(p);
      try {
         factory.buildTimestampsRegion( timestamps, p );
         assertTrue( factory.getDefinedConfigurations().contains( "timestamps-none-eviction" ) );
      } finally {
         factory.stop();
      }
   }

   @Test
   public void testBuildQueryRegion() {
      final String query = "org.hibernate.cache.internal.StandardQueryCache";
      Properties p = createProperties();
      InfinispanRegionFactory factory = createRegionFactory(p);
      try {
         assertTrue(factory.getDefinedConfigurations().contains("local-query"));
         QueryResultsRegionImpl region = (QueryResultsRegionImpl) factory.buildQueryResultsRegion(query, p);
         AdvancedCache cache = region.getCache();
         Configuration cacheCfg = cache.getCacheConfiguration();
         assertEquals( CacheMode.LOCAL, cacheCfg.clustering().cacheMode() );
         assertFalse( cacheCfg.jmxStatistics().enabled() );
      } finally {
         factory.stop();
      }
   }

   @Test
   public void testBuildQueryRegionWithCustomRegionName() {
      final String queryRegionName = "myquery";
      Properties p = createProperties();
      p.setProperty("hibernate.cache.infinispan.myquery.cfg", "timestamps-none-eviction");
      p.setProperty("hibernate.cache.infinispan.myquery.eviction.strategy", "LIRS");
      p.setProperty("hibernate.cache.infinispan.myquery.eviction.wake_up_interval", "2222");
      p.setProperty("hibernate.cache.infinispan.myquery.eviction.max_entries", "11111");
      InfinispanRegionFactory factory = createRegionFactory(p);
      try {
         assertTrue(factory.getDefinedConfigurations().contains("local-query"));
         QueryResultsRegionImpl region = (QueryResultsRegionImpl) factory.buildQueryResultsRegion(queryRegionName, p);
         assertNotNull(factory.getTypeOverrides().get(queryRegionName));
         assertTrue(factory.getDefinedConfigurations().contains(queryRegionName));
         AdvancedCache cache = region.getCache();
         Configuration cacheCfg = cache.getCacheConfiguration();
         assertEquals(EvictionStrategy.LIRS, cacheCfg.eviction().strategy());
         assertEquals(2222, cacheCfg.expiration().wakeUpInterval());
         assertEquals( 11111, cacheCfg.eviction().maxEntries() );
      } finally {
         factory.stop();
      }
   }
   @Test
   public void testEnableStatistics() {
      Properties p = createProperties();
      p.setProperty("hibernate.cache.infinispan.statistics", "true");
      p.setProperty("hibernate.cache.infinispan.com.acme.Person.expiration.lifespan", "60000");
      p.setProperty("hibernate.cache.infinispan.com.acme.Person.expiration.max_idle", "30000");
      p.setProperty("hibernate.cache.infinispan.entity.cfg", "myentity-cache");
      p.setProperty("hibernate.cache.infinispan.entity.eviction.strategy", "FIFO");
      p.setProperty("hibernate.cache.infinispan.entity.eviction.wake_up_interval", "3000");
      p.setProperty("hibernate.cache.infinispan.entity.eviction.max_entries", "10000");
      InfinispanRegionFactory factory = createRegionFactory(p);
      try {
         EmbeddedCacheManager manager = factory.getCacheManager();
         assertTrue(manager.getCacheManagerConfiguration().globalJmxStatistics().enabled());
         EntityRegionImpl region = (EntityRegionImpl) factory.buildEntityRegion("com.acme.Address", p, MUTABLE_NON_VERSIONED);
         AdvancedCache cache = region.getCache();
         assertTrue(factory.getTypeOverrides().get("entity").isExposeStatistics());
         assertTrue(cache.getCacheConfiguration().jmxStatistics().enabled());

         region = (EntityRegionImpl) factory.buildEntityRegion("com.acme.Person", p, MUTABLE_NON_VERSIONED);
         cache = region.getCache();
         assertTrue(factory.getTypeOverrides().get("com.acme.Person").isExposeStatistics());
         assertTrue(cache.getCacheConfiguration().jmxStatistics().enabled());

         final String query = "org.hibernate.cache.internal.StandardQueryCache";
         QueryResultsRegionImpl queryRegion = (QueryResultsRegionImpl)
               factory.buildQueryResultsRegion(query, p);
         cache = queryRegion.getCache();
         assertTrue(factory.getTypeOverrides().get("query").isExposeStatistics());
         assertTrue(cache.getCacheConfiguration().jmxStatistics().enabled());

         final String timestamps = "org.hibernate.cache.spi.UpdateTimestampsCache";
         ConfigurationBuilder builder = new ConfigurationBuilder();
         builder.clustering().stateTransfer().fetchInMemoryState(true);
         manager.defineConfiguration("timestamps", builder.build());
         TimestampsRegionImpl timestampsRegion = (TimestampsRegionImpl)
               factory.buildTimestampsRegion(timestamps, p);
         cache = timestampsRegion.getCache();
         assertTrue(factory.getTypeOverrides().get("timestamps").isExposeStatistics());
         assertTrue(cache.getCacheConfiguration().jmxStatistics().enabled());

         CollectionRegionImpl collectionRegion = (CollectionRegionImpl)
               factory.buildCollectionRegion("com.acme.Person.addresses", p, MUTABLE_NON_VERSIONED);
         cache = collectionRegion.getCache();
         assertTrue(factory.getTypeOverrides().get("collection").isExposeStatistics());
         assertTrue(cache.getCacheConfiguration().jmxStatistics().enabled());
      } finally {
         factory.stop();
      }
   }

   @Test
   public void testDisableStatistics() {
      Properties p = createProperties();
      p.setProperty("hibernate.cache.infinispan.statistics", "false");
      p.setProperty("hibernate.cache.infinispan.com.acme.Person.expiration.lifespan", "60000");
      p.setProperty("hibernate.cache.infinispan.com.acme.Person.expiration.max_idle", "30000");
      p.setProperty("hibernate.cache.infinispan.entity.cfg", "myentity-cache");
      p.setProperty("hibernate.cache.infinispan.entity.eviction.strategy", "FIFO");
      p.setProperty("hibernate.cache.infinispan.entity.eviction.wake_up_interval", "3000");
      p.setProperty("hibernate.cache.infinispan.entity.eviction.max_entries", "10000");
      InfinispanRegionFactory factory = createRegionFactory(p);
      try {
         EntityRegionImpl region = (EntityRegionImpl) factory.buildEntityRegion("com.acme.Address", p, MUTABLE_NON_VERSIONED);
         AdvancedCache cache = region.getCache();
         assertFalse( factory.getTypeOverrides().get( "entity" ).isExposeStatistics() );
         assertFalse( cache.getCacheConfiguration().jmxStatistics().enabled() );

         region = (EntityRegionImpl) factory.buildEntityRegion("com.acme.Person", p, MUTABLE_NON_VERSIONED);
         cache = region.getCache();
         assertFalse( factory.getTypeOverrides().get( "com.acme.Person" ).isExposeStatistics() );
         assertFalse( cache.getCacheConfiguration().jmxStatistics().enabled() );

         final String query = "org.hibernate.cache.internal.StandardQueryCache";
         QueryResultsRegionImpl queryRegion = (QueryResultsRegionImpl) factory.buildQueryResultsRegion(query, p);
         cache = queryRegion.getCache();
         assertFalse( factory.getTypeOverrides().get( "query" ).isExposeStatistics() );
         assertFalse( cache.getCacheConfiguration().jmxStatistics().enabled() );

         final String timestamps = "org.hibernate.cache.spi.UpdateTimestampsCache";
         ConfigurationBuilder builder = new ConfigurationBuilder();
         builder.clustering().stateTransfer().fetchInMemoryState(true);
         factory.getCacheManager().defineConfiguration( "timestamps", builder.build() );
         TimestampsRegionImpl timestampsRegion = (TimestampsRegionImpl)
               factory.buildTimestampsRegion(timestamps, p);
         cache = timestampsRegion.getCache();
         assertFalse( factory.getTypeOverrides().get( "timestamps" ).isExposeStatistics() );
         assertFalse( cache.getCacheConfiguration().jmxStatistics().enabled() );

         CollectionRegionImpl collectionRegion = (CollectionRegionImpl)
               factory.buildCollectionRegion("com.acme.Person.addresses", p, MUTABLE_NON_VERSIONED);
         cache = collectionRegion.getCache();
         assertFalse( factory.getTypeOverrides().get( "collection" ).isExposeStatistics() );
         assertFalse( cache.getCacheConfiguration().jmxStatistics().enabled() );
      } finally {
         factory.stop();
      }
   }

   private InfinispanRegionFactory createRegionFactory(Properties p) {
      return createRegionFactory(null, p);
   }

   private InfinispanRegionFactory createRegionFactory(final EmbeddedCacheManager manager, Properties p) {
      final InfinispanRegionFactory factory = new SingleNodeTestCase.TestInfinispanRegionFactory() {

         @Override
         protected org.infinispan.transaction.lookup.TransactionManagerLookup createTransactionManagerLookup(SessionFactoryOptions settings, Properties properties) {
            return new HibernateTransactionManagerLookup(null, null) {
               @Override
               public TransactionManager getTransactionManager() throws Exception {
                  AbstractJtaPlatform jta = new JBossStandAloneJtaPlatform();
                  jta.injectServices(ServiceRegistryBuilder.buildServiceRegistry());
                  return jta.getTransactionManager();
               }
            };
         }

         @Override
         protected EmbeddedCacheManager createCacheManager(Properties properties, ServiceRegistry serviceRegistry) throws CacheException {
            if (manager != null)
               return manager;
            else
               return super.createCacheManager( properties, serviceRegistry);
         }

      };

      factory.start( sfOptionsForStart(), p );
      return factory;
   }

   private SessionFactoryOptions sfOptionsForStart() {
      return new SessionFactoryOptionsImpl(
              new SessionFactoryBuilderImpl.SessionFactoryOptionsStateStandardImpl(
                      ServiceRegistryTestingImpl.forUnitTesting()
              )
      );
   }

   private static Properties createProperties() {
      final Properties properties = new Properties();
      // If configured in the environment, add configuration file name to properties.
      final String cfgFileName =
              (String) Environment.getProperties().get( InfinispanRegionFactory.INFINISPAN_CONFIG_RESOURCE_PROP );
      if ( cfgFileName != null ) {
         properties.put( InfinispanRegionFactory.INFINISPAN_CONFIG_RESOURCE_PROP, cfgFileName );
      }
      return properties;
   }
}


File: hibernate-infinispan/src/test/java/org/hibernate/test/cache/infinispan/access/PutFromLoadValidatorUnitTestCase.java
/*
 * Hibernate, Relational Persistence for Idiomatic Java
 *
 * License: GNU Lesser General Public License (LGPL), version 2.1 or later.
 * See the lgpl.txt file in the root directory or <http://www.gnu.org/licenses/lgpl-2.1.html>.
 */
package org.hibernate.test.cache.infinispan.access;

import java.util.concurrent.Callable;
import java.util.concurrent.CountDownLatch;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;
import java.util.concurrent.Future;
import java.util.concurrent.TimeUnit;
import java.util.concurrent.TimeoutException;
import java.util.concurrent.atomic.AtomicInteger;
import java.util.concurrent.atomic.AtomicReference;
import javax.transaction.TransactionManager;

import org.hibernate.cache.infinispan.access.PutFromLoadValidator;

import org.hibernate.test.cache.infinispan.functional.cluster.DualNodeJtaTransactionManagerImpl;
import org.junit.After;
import org.junit.Before;
import org.junit.Test;

import org.infinispan.manager.EmbeddedCacheManager;
import org.infinispan.test.CacheManagerCallable;
import org.infinispan.test.fwk.TestCacheManagerFactory;
import org.infinispan.util.logging.Log;
import org.infinispan.util.logging.LogFactory;

import static org.infinispan.test.TestingUtil.withCacheManager;
import static org.junit.Assert.assertEquals;
import static org.junit.Assert.assertFalse;
import static org.junit.Assert.assertNull;
import static org.junit.Assert.assertTrue;
import static org.junit.Assert.fail;

/**
 * Tests of {@link PutFromLoadValidator}.
 *
 * @author Brian Stansberry
 * @author Galder Zamarreño
 * @version $Revision: $
 */
public class PutFromLoadValidatorUnitTestCase {

   private static final Log log = LogFactory.getLog(
         PutFromLoadValidatorUnitTestCase.class);

   private Object KEY1 = "KEY1";

   private TransactionManager tm;

   @Before
   public void setUp() throws Exception {
      tm = DualNodeJtaTransactionManagerImpl.getInstance("test");
   }

   @After
   public void tearDown() throws Exception {
      tm = null;
      try {
         DualNodeJtaTransactionManagerImpl.cleanupTransactions();
      }
      finally {
         DualNodeJtaTransactionManagerImpl.cleanupTransactionManagers();
      }
    }

   @Test
   public void testNakedPut() throws Exception {
      nakedPutTest(false);
   }
   @Test
   public void testNakedPutTransactional() throws Exception {
      nakedPutTest(true);
   }

   private void nakedPutTest(final boolean transactional) throws Exception {
      withCacheManager(new CacheManagerCallable(
            TestCacheManagerFactory.createCacheManager(false)) {
         @Override
         public void call() {
            try {
               PutFromLoadValidator testee = new PutFromLoadValidator(cm,
                     transactional ? tm : null,
                     PutFromLoadValidator.NAKED_PUT_INVALIDATION_PERIOD);
               if (transactional) {
                  tm.begin();
               }
               boolean lockable = testee.acquirePutFromLoadLock(KEY1);
               try {
                  assertTrue(lockable);
               }
               finally {
                  if (lockable) {
                     testee.releasePutFromLoadLock(KEY1);
                  }
               }
            } catch (Exception e) {
               throw new RuntimeException(e);
            }
         }
      });
   }
   @Test
   public void testRegisteredPut() throws Exception {
      registeredPutTest(false);
   }
   @Test
   public void testRegisteredPutTransactional() throws Exception {
      registeredPutTest(true);
   }

   private void registeredPutTest(final boolean transactional) throws Exception {
      withCacheManager(new CacheManagerCallable(
            TestCacheManagerFactory.createCacheManager(false)) {
         @Override
         public void call() {
            PutFromLoadValidator testee = new PutFromLoadValidator(cm,
                  transactional ? tm : null,
                  PutFromLoadValidator.NAKED_PUT_INVALIDATION_PERIOD);
            try {
               if (transactional) {
                  tm.begin();
               }
               testee.registerPendingPut(KEY1);

               boolean lockable = testee.acquirePutFromLoadLock(KEY1);
               try {
                  assertTrue(lockable);
               }
               finally {
                  if (lockable) {
                     testee.releasePutFromLoadLock(KEY1);
                  }
               }
            } catch (Exception e) {
               throw new RuntimeException(e);
            }
         }
      });
   }
   @Test
   public void testNakedPutAfterKeyRemoval() throws Exception {
      nakedPutAfterRemovalTest(false, false);
   }
   @Test
   public void testNakedPutAfterKeyRemovalTransactional() throws Exception {
      nakedPutAfterRemovalTest(true, false);
   }
   @Test
   public void testNakedPutAfterRegionRemoval() throws Exception {
      nakedPutAfterRemovalTest(false, true);
   }
   @Test
   public void testNakedPutAfterRegionRemovalTransactional() throws Exception {
      nakedPutAfterRemovalTest(true, true);
   }

   private void nakedPutAfterRemovalTest(final boolean transactional,
         final boolean removeRegion) throws Exception {
      withCacheManager(new CacheManagerCallable(
            TestCacheManagerFactory.createCacheManager(false)) {
         @Override
         public void call() {
            PutFromLoadValidator testee = new PutFromLoadValidator(cm,
                  transactional ? tm : null,
                  PutFromLoadValidator.NAKED_PUT_INVALIDATION_PERIOD);
            if (removeRegion) {
               testee.invalidateRegion();
            } else {
               testee.invalidateKey(KEY1);
            }
            try {
               if (transactional) {
                  tm.begin();
               }

               boolean lockable = testee.acquirePutFromLoadLock(KEY1);
               try {
                  assertFalse(lockable);
               }
               finally {
                  if (lockable) {
                     testee.releasePutFromLoadLock(KEY1);
                  }
               }
            } catch (Exception e) {
               throw new RuntimeException(e);
            }
         }
      });

   }
   @Test
   public void testRegisteredPutAfterKeyRemoval() throws Exception {
      registeredPutAfterRemovalTest(false, false);
   }
   @Test
   public void testRegisteredPutAfterKeyRemovalTransactional() throws Exception {
      registeredPutAfterRemovalTest(true, false);
   }
    @Test
   public void testRegisteredPutAfterRegionRemoval() throws Exception {
      registeredPutAfterRemovalTest(false, true);
   }
    @Test
   public void testRegisteredPutAfterRegionRemovalTransactional() throws Exception {
      registeredPutAfterRemovalTest(true, true);
   }

   private void registeredPutAfterRemovalTest(final boolean transactional,
         final boolean removeRegion) throws Exception {
      withCacheManager(new CacheManagerCallable(
            TestCacheManagerFactory.createCacheManager(false)) {
         @Override
         public void call() {
            PutFromLoadValidator testee = new PutFromLoadValidator(cm,
                  transactional ? tm : null,
                  PutFromLoadValidator.NAKED_PUT_INVALIDATION_PERIOD);
            if (removeRegion) {
               testee.invalidateRegion();
            } else {
               testee.invalidateKey(KEY1);
            }
            try {
               if (transactional) {
                  tm.begin();
               }
               testee.registerPendingPut(KEY1);

               boolean lockable = testee.acquirePutFromLoadLock(KEY1);
               try {
                  assertTrue(lockable);
               }
               finally {
                  if (lockable) {
                     testee.releasePutFromLoadLock(KEY1);
                  }
               }
            } catch (Exception e) {
               throw new RuntimeException(e);
            }
         }
      });

   }
    @Test
   public void testRegisteredPutWithInterveningKeyRemoval() throws Exception {
      registeredPutWithInterveningRemovalTest(false, false);
   }
    @Test
   public void testRegisteredPutWithInterveningKeyRemovalTransactional() throws Exception {
      registeredPutWithInterveningRemovalTest(true, false);
   }
    @Test
   public void testRegisteredPutWithInterveningRegionRemoval() throws Exception {
      registeredPutWithInterveningRemovalTest(false, true);
   }
    @Test
   public void testRegisteredPutWithInterveningRegionRemovalTransactional() throws Exception {
      registeredPutWithInterveningRemovalTest(true, true);
   }

   private void registeredPutWithInterveningRemovalTest(
         final boolean transactional, final boolean removeRegion)
         throws Exception {
      withCacheManager(new CacheManagerCallable(
            TestCacheManagerFactory.createCacheManager(false)) {
         @Override
         public void call() {
            PutFromLoadValidator testee = new PutFromLoadValidator(cm,
                  transactional ? tm : null,
                  PutFromLoadValidator.NAKED_PUT_INVALIDATION_PERIOD);
            try {
               if (transactional) {
                  tm.begin();
               }
               testee.registerPendingPut(KEY1);
               if (removeRegion) {
                  testee.invalidateRegion();
               } else {
                  testee.invalidateKey(KEY1);
               }

               boolean lockable = testee.acquirePutFromLoadLock(KEY1);
               try {
                  assertFalse(lockable);
               }
               finally {
                  if (lockable) {
                     testee.releasePutFromLoadLock(KEY1);
                  }
               }
            } catch (Exception e) {
               throw new RuntimeException(e);
            }
         }
      });
   }
   @Test
   public void testDelayedNakedPutAfterKeyRemoval() throws Exception {
      delayedNakedPutAfterRemovalTest(false, false);
   }
   @Test
   public void testDelayedNakedPutAfterKeyRemovalTransactional() throws Exception {
      delayedNakedPutAfterRemovalTest(true, false);
   }
    @Test
   public void testDelayedNakedPutAfterRegionRemoval() throws Exception {
      delayedNakedPutAfterRemovalTest(false, true);
   }
   @Test
   public void testDelayedNakedPutAfterRegionRemovalTransactional() throws Exception {
      delayedNakedPutAfterRemovalTest(true, true);
   }

   private void delayedNakedPutAfterRemovalTest(
         final boolean transactional, final boolean removeRegion)
         throws Exception {
      withCacheManager(new CacheManagerCallable(
            TestCacheManagerFactory.createCacheManager(false)) {
         @Override
         public void call() {
            PutFromLoadValidator testee = new TestValidator(cm,
                  transactional ? tm : null, 100);
            if (removeRegion) {
               testee.invalidateRegion();
            } else {
               testee.invalidateKey(KEY1);
            }
            try {
               if (transactional) {
                  tm.begin();
               }
               Thread.sleep(110);

               boolean lockable = testee.acquirePutFromLoadLock(KEY1);
               try {
                  assertTrue(lockable);
               } finally {
                  if (lockable) {
                     testee.releasePutFromLoadLock(KEY1);
                  }
               }
            } catch (Exception e) {
               throw new RuntimeException(e);
            }
         }
      });
   }

   @Test
   public void testMultipleRegistrations() throws Exception {
      multipleRegistrationtest(false);
   }

   @Test
   public void testMultipleRegistrationsTransactional() throws Exception {
      multipleRegistrationtest(true);
   }

   private void multipleRegistrationtest(final boolean transactional) throws Exception {
      withCacheManager(new CacheManagerCallable(
            TestCacheManagerFactory.createCacheManager(false)) {
         @Override
         public void call() {
            final PutFromLoadValidator testee = new PutFromLoadValidator(cm,
                  transactional ? tm : null,
                  PutFromLoadValidator.NAKED_PUT_INVALIDATION_PERIOD);

            final CountDownLatch registeredLatch = new CountDownLatch(3);
            final CountDownLatch finishedLatch = new CountDownLatch(3);
            final AtomicInteger success = new AtomicInteger();

            Runnable r = new Runnable() {
               public void run() {
                  try {
                     if (transactional) {
                        tm.begin();
                     }
                     testee.registerPendingPut(KEY1);
                     registeredLatch.countDown();
                     registeredLatch.await(5, TimeUnit.SECONDS);
                     if (testee.acquirePutFromLoadLock(KEY1)) {
                        try {
                           log.trace("Put from load lock acquired for key = " + KEY1);
                           success.incrementAndGet();
                        } finally {
                           testee.releasePutFromLoadLock(KEY1);
                        }
                     } else {
                        log.trace("Unable to acquired putFromLoad lock for key = " + KEY1);
                     }
                     finishedLatch.countDown();
                  } catch (Exception e) {
                     e.printStackTrace();
                  }
               }
            };

            ExecutorService executor = Executors.newFixedThreadPool(3);

            // Start with a removal so the "isPutValid" calls will fail if
            // any of the concurrent activity isn't handled properly

            testee.invalidateRegion();

            // Do the registration + isPutValid calls
            executor.execute(r);
            executor.execute(r);
            executor.execute(r);

            try {
               finishedLatch.await(5, TimeUnit.SECONDS);
            } catch (InterruptedException e) {
               throw new RuntimeException(e);
            }

            assertEquals("All threads succeeded", 3, success.get());
         }
      });
   }

   @Test
   public void testInvalidateKeyBlocksForInProgressPut() throws Exception {
      invalidationBlocksForInProgressPutTest(true);
   }

   @Test
   public void testInvalidateRegionBlocksForInProgressPut() throws Exception {
      invalidationBlocksForInProgressPutTest(false);
   }

   private void invalidationBlocksForInProgressPutTest(final boolean keyOnly) throws Exception {
      withCacheManager(new CacheManagerCallable(
            TestCacheManagerFactory.createCacheManager(false)) {
         @Override
         public void call() {
            final PutFromLoadValidator testee = new PutFromLoadValidator(
                  cm, null, PutFromLoadValidator.NAKED_PUT_INVALIDATION_PERIOD);
            final CountDownLatch removeLatch = new CountDownLatch(1);
            final CountDownLatch pferLatch = new CountDownLatch(1);
            final AtomicReference<Object> cache = new AtomicReference<Object>("INITIAL");

            Callable<Boolean> pferCallable = new Callable<Boolean>() {
               public Boolean call() throws Exception {
                  testee.registerPendingPut(KEY1);
                  if (testee.acquirePutFromLoadLock(KEY1)) {
                     try {
                        removeLatch.countDown();
                        pferLatch.await();
                        cache.set("PFER");
                        return Boolean.TRUE;
                     }
                     finally {
                        testee.releasePutFromLoadLock(KEY1);
                     }
                  }
                  return Boolean.FALSE;
               }
            };

            Callable<Void> invalidateCallable = new Callable<Void>() {
               public Void call() throws Exception {
                  removeLatch.await();
                  if (keyOnly) {
                     testee.invalidateKey(KEY1);
                  } else {
                     testee.invalidateRegion();
                  }
                  cache.set(null);
                  return null;
               }
            };

            ExecutorService executorService = Executors.newCachedThreadPool();
            Future<Boolean> pferFuture = executorService.submit(pferCallable);
            Future<Void> invalidateFuture = executorService.submit(invalidateCallable);

            try {
               try {
                  invalidateFuture.get(1, TimeUnit.SECONDS);
                  fail("invalidateFuture did not block");
               }
               catch (TimeoutException good) {}

               pferLatch.countDown();

               assertTrue(pferFuture.get(5, TimeUnit.SECONDS));
               invalidateFuture.get(5, TimeUnit.SECONDS);

               assertNull(cache.get());
            } catch (Exception e) {
               throw new RuntimeException(e);
            }
         }
      });
   }

   private static class TestValidator extends PutFromLoadValidator {

      protected TestValidator(EmbeddedCacheManager cm,
            TransactionManager transactionManager,
            long nakedPutInvalidationPeriod) {
         super(cm, transactionManager, nakedPutInvalidationPeriod);
      }

      @Override
      public int getRemovalQueueLength() {
         return super.getRemovalQueueLength();
      }

   }
}


File: hibernate-infinispan/src/test/java/org/hibernate/test/cache/infinispan/collection/AbstractCollectionRegionAccessStrategyTestCase.java
/*
 * Hibernate, Relational Persistence for Idiomatic Java
 *
 * License: GNU Lesser General Public License (LGPL), version 2.1 or later.
 * See the lgpl.txt file in the root directory or <http://www.gnu.org/licenses/lgpl-2.1.html>.
 */
package org.hibernate.test.cache.infinispan.collection;

import javax.transaction.TransactionManager;
import java.util.concurrent.Callable;
import java.util.concurrent.CountDownLatch;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;
import java.util.concurrent.Future;
import java.util.concurrent.TimeUnit;

import junit.framework.AssertionFailedError;
import org.hibernate.boot.registry.StandardServiceRegistryBuilder;
import org.hibernate.cache.infinispan.InfinispanRegionFactory;
import org.hibernate.cache.infinispan.access.PutFromLoadValidator;
import org.hibernate.cache.infinispan.access.TransactionalAccessDelegate;
import org.hibernate.cache.infinispan.collection.CollectionRegionImpl;
import org.hibernate.cache.infinispan.util.Caches;
import org.hibernate.cache.internal.CacheDataDescriptionImpl;
import org.hibernate.cache.spi.CacheDataDescription;
import org.hibernate.cache.spi.access.AccessType;
import org.hibernate.cache.spi.access.CollectionRegionAccessStrategy;
import org.hibernate.internal.util.compare.ComparableComparator;
import org.hibernate.test.cache.infinispan.AbstractNonFunctionalTestCase;
import org.hibernate.test.cache.infinispan.NodeEnvironment;
import org.hibernate.test.cache.infinispan.util.CacheTestUtil;
import org.hibernate.test.cache.infinispan.util.TestingKeyFactory;
import org.infinispan.test.CacheManagerCallable;
import org.infinispan.test.fwk.TestCacheManagerFactory;
import org.infinispan.transaction.tm.BatchModeTransactionManager;
import org.jboss.logging.Logger;
import org.junit.After;
import org.junit.Before;
import org.junit.Test;

import static org.infinispan.test.TestingUtil.withCacheManager;
import static org.junit.Assert.assertEquals;
import static org.junit.Assert.assertFalse;
import static org.junit.Assert.assertNull;
import static org.junit.Assert.assertTrue;

/**
 * Base class for tests of CollectionRegionAccessStrategy impls.
 *
 * @author Galder Zamarreño
 * @since 3.5
 */
public abstract class AbstractCollectionRegionAccessStrategyTestCase extends AbstractNonFunctionalTestCase {
	private static final Logger log = Logger.getLogger( AbstractCollectionRegionAccessStrategyTestCase.class );
	public static final String REGION_NAME = "test/com.foo.test";
	public static final String KEY_BASE = "KEY";
	public static final String VALUE1 = "VALUE1";
	public static final String VALUE2 = "VALUE2";

	protected static int testCount;

	protected NodeEnvironment localEnvironment;
	protected CollectionRegionImpl localCollectionRegion;
	protected CollectionRegionAccessStrategy localAccessStrategy;

	protected NodeEnvironment remoteEnvironment;
	protected CollectionRegionImpl remoteCollectionRegion;
	protected CollectionRegionAccessStrategy remoteAccessStrategy;

	protected boolean invalidation;
	protected boolean synchronous;

	protected Exception node1Exception;
	protected Exception node2Exception;

	protected AssertionFailedError node1Failure;
	protected AssertionFailedError node2Failure;

	protected abstract AccessType getAccessType();

	@Before
	public void prepareResources() throws Exception {
		// to mimic exactly the old code results, both environments here are exactly the same...
		StandardServiceRegistryBuilder ssrb = createStandardServiceRegistryBuilder( getConfigurationName() );
		localEnvironment = new NodeEnvironment( ssrb );
		localEnvironment.prepare();

		localCollectionRegion = localEnvironment.getCollectionRegion( REGION_NAME, getCacheDataDescription() );
		localAccessStrategy = localCollectionRegion.buildAccessStrategy( getAccessType() );

		invalidation = Caches.isInvalidationCache(localCollectionRegion.getCache());
		synchronous = Caches.isSynchronousCache(localCollectionRegion.getCache());

		// Sleep a bit to avoid concurrent FLUSH problem
		avoidConcurrentFlush();

		remoteEnvironment = new NodeEnvironment( ssrb );
		remoteEnvironment.prepare();

		remoteCollectionRegion = remoteEnvironment.getCollectionRegion( REGION_NAME, getCacheDataDescription() );
		remoteAccessStrategy = remoteCollectionRegion.buildAccessStrategy( getAccessType() );
	}

	protected abstract String getConfigurationName();

	protected static StandardServiceRegistryBuilder createStandardServiceRegistryBuilder(String configName) {
		final StandardServiceRegistryBuilder ssrb = CacheTestUtil.buildBaselineStandardServiceRegistryBuilder(
				REGION_PREFIX,
				InfinispanRegionFactory.class,
				true,
				false
		);
		ssrb.applySetting( InfinispanRegionFactory.ENTITY_CACHE_RESOURCE_PROP, configName );
		return ssrb;
	}

	protected CacheDataDescription getCacheDataDescription() {
		return new CacheDataDescriptionImpl( true, true, ComparableComparator.INSTANCE );
	}

	@After
	public void releaseResources() throws Exception {
		if ( localEnvironment != null ) {
			localEnvironment.release();
		}
		if ( remoteEnvironment != null ) {
			remoteEnvironment.release();
		}
	}

	protected boolean isUsingInvalidation() {
		return invalidation;
	}

	protected boolean isSynchronous() {
		return synchronous;
	}

	@Test
	public abstract void testCacheConfiguration();

	@Test
	public void testGetRegion() {
		assertEquals( "Correct region", localCollectionRegion, localAccessStrategy.getRegion() );
	}

	@Test
	public void testPutFromLoadRemoveDoesNotProduceStaleData() throws Exception {
		final CountDownLatch pferLatch = new CountDownLatch( 1 );
		final CountDownLatch removeLatch = new CountDownLatch( 1 );
      final TransactionManager remoteTm = remoteCollectionRegion.getTransactionManager();
      withCacheManager(new CacheManagerCallable(TestCacheManagerFactory.createCacheManager(false)) {
         @Override
         public void call() {
            PutFromLoadValidator validator = new PutFromLoadValidator(cm,
                  remoteTm, 20000) {
               @Override
               public boolean acquirePutFromLoadLock(Object key) {
                  boolean acquired = super.acquirePutFromLoadLock( key );
                  try {
                     removeLatch.countDown();
                     pferLatch.await( 2, TimeUnit.SECONDS );
                  }
                  catch (InterruptedException e) {
                     log.debug( "Interrupted" );
                     Thread.currentThread().interrupt();
                  }
                  catch (Exception e) {
                     log.error( "Error", e );
                     throw new RuntimeException( "Error", e );
                  }
                  return acquired;
               }
            };

            final TransactionalAccessDelegate delegate =
                  new TransactionalAccessDelegate(localCollectionRegion, validator);
            final TransactionManager localTm = localCollectionRegion.getTransactionManager();

            Callable<Void> pferCallable = new Callable<Void>() {
               public Void call() throws Exception {
                  delegate.putFromLoad( "k1", "v1", 0, null );
                  return null;
               }
            };

            Callable<Void> removeCallable = new Callable<Void>() {
               public Void call() throws Exception {
                  removeLatch.await();
                  Caches.withinTx(localTm, new Callable<Void>() {
                     @Override
                     public Void call() throws Exception {
                        delegate.remove("k1");
                        return null;
                     }
                  });
                  pferLatch.countDown();
                  return null;
               }
            };

            ExecutorService executorService = Executors.newCachedThreadPool();
            Future<Void> pferFuture = executorService.submit( pferCallable );
            Future<Void> removeFuture = executorService.submit( removeCallable );

            try {
               pferFuture.get();
               removeFuture.get();
            } catch (Exception e) {
               throw new RuntimeException(e);
            }

            assertFalse(localCollectionRegion.getCache().containsKey("k1"));
         }
      });
	}

	@Test
	public void testPutFromLoad() throws Exception {
		putFromLoadTest( false );
	}

	@Test
	public void testPutFromLoadMinimal() throws Exception {
		putFromLoadTest( true );
	}

	private void putFromLoadTest(final boolean useMinimalAPI) throws Exception {

		final Object KEY = TestingKeyFactory.generateCollectionCacheKey( KEY_BASE + testCount++ );

		final CountDownLatch writeLatch1 = new CountDownLatch( 1 );
		final CountDownLatch writeLatch2 = new CountDownLatch( 1 );
		final CountDownLatch completionLatch = new CountDownLatch( 2 );

		Thread node1 = new Thread() {

			public void run() {

				try {
					long txTimestamp = System.currentTimeMillis();
					BatchModeTransactionManager.getInstance().begin();

					assertEquals( "node1 starts clean", null, localAccessStrategy.get( KEY, txTimestamp ) );

					writeLatch1.await();

					if ( useMinimalAPI ) {
						localAccessStrategy.putFromLoad( KEY, VALUE2, txTimestamp, new Integer( 2 ), true );
					}
					else {
						localAccessStrategy.putFromLoad( KEY, VALUE2, txTimestamp, new Integer( 2 ) );
					}

					BatchModeTransactionManager.getInstance().commit();
				}
				catch (Exception e) {
					log.error( "node1 caught exception", e );
					node1Exception = e;
					rollback();
				}
				catch (AssertionFailedError e) {
					node1Failure = e;
					rollback();
				}
				finally {
					// Let node2 write
					writeLatch2.countDown();
					completionLatch.countDown();
				}
			}
		};

		Thread node2 = new Thread() {

			public void run() {

				try {
					long txTimestamp = System.currentTimeMillis();
					BatchModeTransactionManager.getInstance().begin();

					assertNull( "node2 starts clean", remoteAccessStrategy.get( KEY, txTimestamp ) );

					// Let node1 write
					writeLatch1.countDown();
					// Wait for node1 to finish
					writeLatch2.await();

					// Let the first PFER propagate
					sleep( 200 );

					if ( useMinimalAPI ) {
						remoteAccessStrategy.putFromLoad( KEY, VALUE1, txTimestamp, new Integer( 1 ), true );
					}
					else {
						remoteAccessStrategy.putFromLoad( KEY, VALUE1, txTimestamp, new Integer( 1 ) );
					}

					BatchModeTransactionManager.getInstance().commit();
				}
				catch (Exception e) {
					log.error( "node2 caught exception", e );
					node2Exception = e;
					rollback();
				}
				catch (AssertionFailedError e) {
					node2Failure = e;
					rollback();
				}
				finally {
					completionLatch.countDown();
				}
			}
		};

		node1.setDaemon( true );
		node2.setDaemon( true );

		node1.start();
		node2.start();

		assertTrue( "Threads completed", completionLatch.await( 2, TimeUnit.SECONDS ) );

		if ( node1Failure != null ) {
			throw node1Failure;
		}
		if ( node2Failure != null ) {
			throw node2Failure;
		}

		assertEquals( "node1 saw no exceptions", null, node1Exception );
		assertEquals( "node2 saw no exceptions", null, node2Exception );

		// let the final PFER propagate
		sleep( 100 );

		long txTimestamp = System.currentTimeMillis();
		String msg1 = "Correct node1 value";
		String msg2 = "Correct node2 value";
		Object expected1 = null;
		Object expected2 = null;
		if ( isUsingInvalidation() ) {
			// PFER does not generate any invalidation, so each node should
			// succeed. We count on database locking and Hibernate removing
			// the collection on any update to prevent the situation we have
			// here where the caches have inconsistent data
			expected1 = VALUE2;
			expected2 = VALUE1;
		}
		else {
			// the initial VALUE2 should prevent the node2 put
			expected1 = VALUE2;
			expected2 = VALUE2;
		}

		assertEquals( msg1, expected1, localAccessStrategy.get( KEY, txTimestamp ) );
		assertEquals( msg2, expected2, remoteAccessStrategy.get( KEY, txTimestamp ) );
	}

	@Test
	public void testRemove() throws Exception {
		evictOrRemoveTest( false );
	}

	@Test
	public void testRemoveAll() throws Exception {
		evictOrRemoveAllTest( false );
	}

	@Test
	public void testEvict() throws Exception {
		evictOrRemoveTest( true );
	}

	@Test
	public void testEvictAll() throws Exception {
		evictOrRemoveAllTest( true );
	}

	private void evictOrRemoveTest(final boolean evict) throws Exception {

		final Object KEY = TestingKeyFactory.generateCollectionCacheKey( KEY_BASE + testCount++ );

		assertNull( "local is clean", localAccessStrategy.get( KEY, System.currentTimeMillis() ) );
		assertNull( "remote is clean", remoteAccessStrategy.get( KEY, System.currentTimeMillis() ) );

		localAccessStrategy.putFromLoad( KEY, VALUE1, System.currentTimeMillis(), new Integer( 1 ) );
		assertEquals( VALUE1, localAccessStrategy.get( KEY, System.currentTimeMillis() ) );
		remoteAccessStrategy.putFromLoad( KEY, VALUE1, System.currentTimeMillis(), new Integer( 1 ) );
		assertEquals( VALUE1, remoteAccessStrategy.get( KEY, System.currentTimeMillis() ) );

		// Wait for async propagation
		sleep( 250 );

      Caches.withinTx(localCollectionRegion.getTransactionManager(), new Callable<Void>() {
         @Override
         public Void call() throws Exception {
            if (evict)
               localAccessStrategy.evict(KEY);
            else
               localAccessStrategy.remove(KEY);
            return null;
         }
      });

		assertEquals( null, localAccessStrategy.get( KEY, System.currentTimeMillis() ) );

		assertEquals( null, remoteAccessStrategy.get( KEY, System.currentTimeMillis() ) );
	}

	private void evictOrRemoveAllTest(final boolean evict) throws Exception {

		final Object KEY = TestingKeyFactory.generateCollectionCacheKey( KEY_BASE + testCount++ );

		assertEquals( 0, getValidKeyCount( localCollectionRegion.getCache().keySet() ) );

		assertEquals( 0, getValidKeyCount( remoteCollectionRegion.getCache().keySet() ) );

		assertNull( "local is clean", localAccessStrategy.get( KEY, System.currentTimeMillis() ) );
		assertNull( "remote is clean", remoteAccessStrategy.get( KEY, System.currentTimeMillis() ) );

		localAccessStrategy.putFromLoad( KEY, VALUE1, System.currentTimeMillis(), new Integer( 1 ) );
		assertEquals( VALUE1, localAccessStrategy.get( KEY, System.currentTimeMillis() ) );
		remoteAccessStrategy.putFromLoad( KEY, VALUE1, System.currentTimeMillis(), new Integer( 1 ) );
		assertEquals( VALUE1, remoteAccessStrategy.get( KEY, System.currentTimeMillis() ) );

		// Wait for async propagation
		sleep( 250 );

      Caches.withinTx(localCollectionRegion.getTransactionManager(), new Callable<Void>() {
         @Override
         public Void call() throws Exception {
            if (evict)
               localAccessStrategy.evictAll();
            else
               localAccessStrategy.removeAll();
            return null;
         }
      });

		// This should re-establish the region root node
		assertNull( localAccessStrategy.get( KEY, System.currentTimeMillis() ) );

		assertEquals( 0, getValidKeyCount( localCollectionRegion.getCache().keySet() ) );

		// Re-establishing the region root on the local node doesn't
		// propagate it to other nodes. Do a get on the remote node to re-establish
		assertEquals( null, remoteAccessStrategy.get( KEY, System.currentTimeMillis() ) );

		assertEquals( 0, getValidKeyCount( remoteCollectionRegion.getCache().keySet() ) );

		// Test whether the get above messes up the optimistic version
		remoteAccessStrategy.putFromLoad( KEY, VALUE1, System.currentTimeMillis(), new Integer( 1 ) );
		assertEquals( VALUE1, remoteAccessStrategy.get( KEY, System.currentTimeMillis() ) );

		assertEquals( 1, getValidKeyCount( remoteCollectionRegion.getCache().keySet() ) );

		// Wait for async propagation of the putFromLoad
		sleep( 250 );

		assertEquals(
				"local is correct", (isUsingInvalidation() ? null : VALUE1), localAccessStrategy.get(
				KEY, System
				.currentTimeMillis()
		)
		);
		assertEquals( "remote is correct", VALUE1, remoteAccessStrategy.get( KEY, System.currentTimeMillis() ) );
	}

	private void rollback() {
		try {
			BatchModeTransactionManager.getInstance().rollback();
		}
		catch (Exception e) {
			log.error( e.getMessage(), e );
		}

	}

}


File: hibernate-infinispan/src/test/java/org/hibernate/test/cache/infinispan/collection/CollectionRegionImplTestCase.java
/*
 * Hibernate, Relational Persistence for Idiomatic Java
 *
 * License: GNU Lesser General Public License (LGPL), version 2.1 or later.
 * See the lgpl.txt file in the root directory or <http://www.gnu.org/licenses/lgpl-2.1.html>.
 */
package org.hibernate.test.cache.infinispan.collection;

import java.util.Properties;

import org.hibernate.cache.CacheException;
import org.hibernate.cache.infinispan.InfinispanRegionFactory;
import org.hibernate.cache.internal.CacheDataDescriptionImpl;
import org.hibernate.cache.spi.CacheDataDescription;
import org.hibernate.cache.spi.CollectionRegion;
import org.hibernate.cache.spi.Region;
import org.hibernate.cache.spi.RegionFactory;
import org.hibernate.cache.spi.access.AccessType;
import org.hibernate.cache.spi.access.CollectionRegionAccessStrategy;
import org.hibernate.test.cache.infinispan.AbstractEntityCollectionRegionTestCase;
import org.infinispan.AdvancedCache;

import static org.junit.Assert.assertNull;
import static org.junit.Assert.fail;

/**
 * Tests of CollectionRegionImpl.
 * 
 * @author Galder Zamarreño
 */
public class CollectionRegionImplTestCase extends AbstractEntityCollectionRegionTestCase {

   private static CacheDataDescription MUTABLE_NON_VERSIONED = new CacheDataDescriptionImpl(true, false, null);

   @Override
   protected void supportedAccessTypeTest(RegionFactory regionFactory, Properties properties) {
      CollectionRegion region = regionFactory.buildCollectionRegion("test", properties, MUTABLE_NON_VERSIONED);
      assertNull("Got TRANSACTIONAL", region.buildAccessStrategy(AccessType.TRANSACTIONAL)
               .lockRegion());
      try {
         region.buildAccessStrategy(AccessType.NONSTRICT_READ_WRITE);
         fail("Incorrectly got NONSTRICT_READ_WRITE");
      } catch (CacheException good) {
      }

      try {
         region.buildAccessStrategy(AccessType.READ_WRITE);
         fail("Incorrectly got READ_WRITE");
      } catch (CacheException good) {
      }
   }

   @Override
   protected Region createRegion(InfinispanRegionFactory regionFactory, String regionName, Properties properties, CacheDataDescription cdd) {
      return regionFactory.buildCollectionRegion(regionName, properties, cdd);
   }

   @Override
   protected AdvancedCache getInfinispanCache(InfinispanRegionFactory regionFactory) {
      return regionFactory.getCacheManager().getCache(InfinispanRegionFactory.DEF_ENTITY_RESOURCE).getAdvancedCache();
   }

   @Override
   protected void putInRegion(Region region, Object key, Object value) {
      CollectionRegionAccessStrategy strategy = ((CollectionRegion) region).buildAccessStrategy(AccessType.TRANSACTIONAL);
      strategy.putFromLoad(key, value, System.currentTimeMillis(), new Integer(1));
   }

   @Override
   protected void removeFromRegion(Region region, Object key) {
      ((CollectionRegion) region).buildAccessStrategy(AccessType.TRANSACTIONAL).remove(key);
   }

}


File: hibernate-infinispan/src/test/java/org/hibernate/test/cache/infinispan/collection/TransactionalExtraAPITestCase.java
/*
 * Hibernate, Relational Persistence for Idiomatic Java
 *
 * License: GNU Lesser General Public License (LGPL), version 2.1 or later.
 * See the lgpl.txt file in the root directory or <http://www.gnu.org/licenses/lgpl-2.1.html>.
 */
package org.hibernate.test.cache.infinispan.collection;

import org.hibernate.boot.registry.StandardServiceRegistryBuilder;
import org.hibernate.cache.infinispan.InfinispanRegionFactory;
import org.hibernate.cache.spi.access.AccessType;
import org.hibernate.cache.spi.access.CollectionRegionAccessStrategy;
import org.hibernate.cache.spi.access.SoftLock;
import org.hibernate.test.cache.infinispan.AbstractNonFunctionalTestCase;
import org.hibernate.test.cache.infinispan.NodeEnvironment;
import org.hibernate.test.cache.infinispan.util.CacheTestUtil;
import org.hibernate.test.cache.infinispan.util.TestingKeyFactory;
import org.junit.After;
import org.junit.Before;
import org.junit.Test;

import static org.junit.Assert.assertNull;

/**
 * TransactionalExtraAPITestCase.
 *
 * @author Galder Zamarreño
 * @since 3.5
 */
public class TransactionalExtraAPITestCase extends AbstractNonFunctionalTestCase {

	public static final String REGION_NAME = "test/com.foo.test";
	public static final Object KEY = TestingKeyFactory.generateCollectionCacheKey( "KEY" );
	public static final String VALUE1 = "VALUE1";
	public static final String VALUE2 = "VALUE2";

	private NodeEnvironment environment;
	private static CollectionRegionAccessStrategy accessStrategy;

	@Before
	public final void prepareLocalAccessStrategy() throws Exception {
		environment = new NodeEnvironment( createStandardServiceRegistryBuilder() );
		environment.prepare();

		// Sleep a bit to avoid concurrent FLUSH problem
		avoidConcurrentFlush();

		accessStrategy = environment.getCollectionRegion( REGION_NAME, null ).buildAccessStrategy( getAccessType() );
	}

	protected StandardServiceRegistryBuilder createStandardServiceRegistryBuilder() {
		StandardServiceRegistryBuilder ssrb = CacheTestUtil.buildBaselineStandardServiceRegistryBuilder(
				REGION_PREFIX, InfinispanRegionFactory.class, true, false
		);
		ssrb.applySetting( InfinispanRegionFactory.ENTITY_CACHE_RESOURCE_PROP, getCacheConfigName() );
		return ssrb;
	}

	protected String getCacheConfigName() {
		return "entity";
	}

	protected AccessType getAccessType() {
		return AccessType.TRANSACTIONAL;
	}

	@After
	public final void releaseLocalAccessStrategy() throws Exception {
		if ( environment != null ) {
			environment.release();
		}
	}

	protected CollectionRegionAccessStrategy getCollectionAccessStrategy() {
		return accessStrategy;
	}

	@Test
	public void testLockItem() {
		assertNull( getCollectionAccessStrategy().lockItem( KEY, new Integer( 1 ) ) );
	}

	@Test
	public void testLockRegion() {
		assertNull( getCollectionAccessStrategy().lockRegion() );
	}

	@Test
	public void testUnlockItem() {
		getCollectionAccessStrategy().unlockItem( KEY, new MockSoftLock() );
	}

	@Test
	public void testUnlockRegion() {
		getCollectionAccessStrategy().unlockItem( KEY, new MockSoftLock() );
	}

	public static class MockSoftLock implements SoftLock {
	}
}


File: hibernate-infinispan/src/test/java/org/hibernate/test/cache/infinispan/entity/AbstractEntityRegionAccessStrategyTestCase.java
/*
 * Hibernate, Relational Persistence for Idiomatic Java
 *
 * License: GNU Lesser General Public License (LGPL), version 2.1 or later.
 * See the lgpl.txt file in the root directory or <http://www.gnu.org/licenses/lgpl-2.1.html>.
 */
package org.hibernate.test.cache.infinispan.entity;

import java.util.Arrays;
import java.util.concurrent.Callable;
import java.util.concurrent.CountDownLatch;
import java.util.concurrent.TimeUnit;

import junit.framework.AssertionFailedError;
import org.hibernate.boot.registry.StandardServiceRegistryBuilder;
import org.hibernate.cache.infinispan.InfinispanRegionFactory;
import org.hibernate.cache.infinispan.entity.EntityRegionImpl;
import org.hibernate.cache.infinispan.util.Caches;
import org.hibernate.cache.internal.CacheDataDescriptionImpl;
import org.hibernate.cache.spi.CacheDataDescription;
import org.hibernate.cache.spi.access.AccessType;
import org.hibernate.cache.spi.access.EntityRegionAccessStrategy;
import org.hibernate.internal.util.compare.ComparableComparator;
import org.hibernate.test.cache.infinispan.AbstractNonFunctionalTestCase;
import org.hibernate.test.cache.infinispan.NodeEnvironment;
import org.hibernate.test.cache.infinispan.util.CacheTestUtil;
import org.hibernate.test.cache.infinispan.util.TestingKeyFactory;
import org.infinispan.Cache;
import org.infinispan.test.TestingUtil;
import org.infinispan.transaction.tm.BatchModeTransactionManager;
import org.jboss.logging.Logger;
import org.junit.After;
import org.junit.Before;
import org.junit.Test;

import static org.junit.Assert.assertEquals;
import static org.junit.Assert.assertNull;
import static org.junit.Assert.assertTrue;

/**
 * Base class for tests of EntityRegionAccessStrategy impls.
 *
 * @author Galder Zamarreño
 * @since 3.5
 */
public abstract class AbstractEntityRegionAccessStrategyTestCase extends AbstractNonFunctionalTestCase {

   private static final Logger log = Logger.getLogger(AbstractEntityRegionAccessStrategyTestCase.class);

   public static final String REGION_NAME = "test/com.foo.test";
   public static final String KEY_BASE = "KEY";
   public static final String VALUE1 = "VALUE1";
   public static final String VALUE2 = "VALUE2";

   protected static int testCount;

   protected NodeEnvironment localEnvironment;
   protected EntityRegionImpl localEntityRegion;
   protected EntityRegionAccessStrategy localAccessStrategy;

   protected NodeEnvironment remoteEnvironment;
   protected EntityRegionImpl remoteEntityRegion;
   protected EntityRegionAccessStrategy remoteAccessStrategy;

   protected boolean invalidation;
   protected boolean synchronous;

   protected Exception node1Exception;
   protected Exception node2Exception;

   protected AssertionFailedError node1Failure;
   protected AssertionFailedError node2Failure;

   @Before
   public void prepareResources() throws Exception {
      // to mimic exactly the old code results, both environments here are exactly the same...
      StandardServiceRegistryBuilder ssrb = createStandardServiceRegistryBuilder( getConfigurationName() );
      localEnvironment = new NodeEnvironment( ssrb );
      localEnvironment.prepare();

      localEntityRegion = localEnvironment.getEntityRegion(REGION_NAME, getCacheDataDescription());
      localAccessStrategy = localEntityRegion.buildAccessStrategy(getAccessType());

      invalidation = Caches.isInvalidationCache(localEntityRegion.getCache());
      synchronous = Caches.isSynchronousCache(localEntityRegion.getCache());

      // Sleep a bit to avoid concurrent FLUSH problem
      avoidConcurrentFlush();

      remoteEnvironment = new NodeEnvironment( ssrb );
      remoteEnvironment.prepare();

      remoteEntityRegion = remoteEnvironment.getEntityRegion(REGION_NAME, getCacheDataDescription());
      remoteAccessStrategy = remoteEntityRegion.buildAccessStrategy(getAccessType());

      waitForClusterToForm(localEntityRegion.getCache(),
            remoteEntityRegion.getCache());
   }

   protected void waitForClusterToForm(Cache... caches) {
      TestingUtil.blockUntilViewsReceived(10000, Arrays.asList(caches));
   }

   protected abstract String getConfigurationName();

   protected static StandardServiceRegistryBuilder createStandardServiceRegistryBuilder(String configName) {
      StandardServiceRegistryBuilder ssrb = CacheTestUtil.buildBaselineStandardServiceRegistryBuilder(
            REGION_PREFIX,
            InfinispanRegionFactory.class,
            true,
            false
      );
      ssrb.applySetting( InfinispanRegionFactory.ENTITY_CACHE_RESOURCE_PROP, configName );
      return ssrb;
   }

   protected CacheDataDescription getCacheDataDescription() {
      return new CacheDataDescriptionImpl(true, true, ComparableComparator.INSTANCE);
   }

   @After
   public void releaseResources() throws Exception {
      try {
         if (localEnvironment != null) {
            localEnvironment.release();
         }
      } finally {
         if (remoteEnvironment != null) {
            remoteEnvironment.release();
         }
      }
   }

   protected abstract AccessType getAccessType();

   protected boolean isUsingInvalidation() {
      return invalidation;
   }

   protected boolean isSynchronous() {
      return synchronous;
   }

   protected void assertThreadsRanCleanly() {
      if (node1Failure != null) {
         throw node1Failure;
      }
      if (node2Failure != null) {
         throw node2Failure;
      }

      if (node1Exception != null) {
         log.error("node1 saw an exception", node1Exception);
         assertEquals("node1 saw no exceptions", null, node1Exception);
      }

      if (node2Exception != null) {
         log.error("node2 saw an exception", node2Exception);
         assertEquals("node2 saw no exceptions", null, node2Exception);
      }
   }

   @Test
   public abstract void testCacheConfiguration();

   @Test
   public void testGetRegion() {
      assertEquals("Correct region", localEntityRegion, localAccessStrategy.getRegion());
   }

   @Test
   public void testPutFromLoad() throws Exception {
      putFromLoadTest(false);
   }

   @Test
   public void testPutFromLoadMinimal() throws Exception {
      putFromLoadTest(true);
   }

   /**
    * Simulate 2 nodes, both start, tx do a get, experience a cache miss, then
    * 'read from db.' First does a putFromLoad, then an update. Second tries to
    * do a putFromLoad with stale data (i.e. it took longer to read from the db).
    * Both commit their tx. Then both start a new tx and get. First should see
    * the updated data; second should either see the updated data
    * (isInvalidation() == false) or null (isInvalidation() == true).
    *
    * @param useMinimalAPI
    * @throws Exception
    */
   private void putFromLoadTest(final boolean useMinimalAPI) throws Exception {

      final Object KEY = TestingKeyFactory.generateEntityCacheKey( KEY_BASE + testCount++ );

      final CountDownLatch writeLatch1 = new CountDownLatch(1);
      final CountDownLatch writeLatch2 = new CountDownLatch(1);
      final CountDownLatch completionLatch = new CountDownLatch(2);

      Thread node1 = new Thread() {

         @Override
         public void run() {

            try {
               long txTimestamp = System.currentTimeMillis();
               BatchModeTransactionManager.getInstance().begin();

               assertNull("node1 starts clean", localAccessStrategy.get(KEY, txTimestamp));

               writeLatch1.await();

               if (useMinimalAPI) {
                  localAccessStrategy.putFromLoad(KEY, VALUE1, txTimestamp, new Integer(1), true);
               } else {
                  localAccessStrategy.putFromLoad(KEY, VALUE1, txTimestamp, new Integer(1));
               }

               localAccessStrategy.update(KEY, VALUE2, new Integer(2), new Integer(1));

               BatchModeTransactionManager.getInstance().commit();
            } catch (Exception e) {
               log.error("node1 caught exception", e);
               node1Exception = e;
               rollback();
            } catch (AssertionFailedError e) {
               node1Failure = e;
               rollback();
            } finally {
               // Let node2 write
               writeLatch2.countDown();
               completionLatch.countDown();
            }
         }
      };

      Thread node2 = new Thread() {

         @Override
         public void run() {

            try {
               long txTimestamp = System.currentTimeMillis();
               BatchModeTransactionManager.getInstance().begin();

               assertNull("node1 starts clean", remoteAccessStrategy.get(KEY, txTimestamp));

               // Let node1 write
               writeLatch1.countDown();
               // Wait for node1 to finish
               writeLatch2.await();

               if (useMinimalAPI) {
                  remoteAccessStrategy.putFromLoad(KEY, VALUE1, txTimestamp, new Integer(1), true);
               } else {
                  remoteAccessStrategy.putFromLoad(KEY, VALUE1, txTimestamp, new Integer(1));
               }

               BatchModeTransactionManager.getInstance().commit();
            } catch (Exception e) {
               log.error("node2 caught exception", e);
               node2Exception = e;
               rollback();
            } catch (AssertionFailedError e) {
               node2Failure = e;
               rollback();
            } finally {
               completionLatch.countDown();
            }
         }
      };

      node1.setDaemon(true);
      node2.setDaemon(true);

      node1.start();
      node2.start();

      assertTrue("Threads completed", completionLatch.await(2, TimeUnit.SECONDS));

      assertThreadsRanCleanly();

      long txTimestamp = System.currentTimeMillis();
      assertEquals("Correct node1 value", VALUE2, localAccessStrategy.get(KEY, txTimestamp));

      if (isUsingInvalidation()) {
         // no data version to prevent the PFER; we count on db locks preventing this
         assertEquals("Expected node2 value", VALUE1, remoteAccessStrategy.get(KEY, txTimestamp));
      } else {
         // The node1 update is replicated, preventing the node2 PFER
         assertEquals("Correct node2 value", VALUE2, remoteAccessStrategy.get(KEY, txTimestamp));
      }
   }

   @Test
   public void testInsert() throws Exception {

      final Object KEY = TestingKeyFactory.generateEntityCacheKey( KEY_BASE + testCount++ );

      final CountDownLatch readLatch = new CountDownLatch(1);
      final CountDownLatch commitLatch = new CountDownLatch(1);
      final CountDownLatch completionLatch = new CountDownLatch(2);

      Thread inserter = new Thread() {

         @Override
         public void run() {

            try {
               long txTimestamp = System.currentTimeMillis();
               BatchModeTransactionManager.getInstance().begin();

               assertNull("Correct initial value", localAccessStrategy.get(KEY, txTimestamp));

               localAccessStrategy.insert(KEY, VALUE1, new Integer(1));

               readLatch.countDown();
               commitLatch.await();

               BatchModeTransactionManager.getInstance().commit();
            } catch (Exception e) {
               log.error("node1 caught exception", e);
               node1Exception = e;
               rollback();
            } catch (AssertionFailedError e) {
               node1Failure = e;
               rollback();
            } finally {
               completionLatch.countDown();
            }
         }
      };

      Thread reader = new Thread() {

         @Override
         public void run() {

            try {
               long txTimestamp = System.currentTimeMillis();
               BatchModeTransactionManager.getInstance().begin();

               readLatch.await();
//               Object expected = !isBlockingReads() ? null : VALUE1;
               Object expected = null;

               assertEquals(
                     "Correct initial value", expected, localAccessStrategy.get(
                     KEY,
                     txTimestamp
               )
               );

               BatchModeTransactionManager.getInstance().commit();
            } catch (Exception e) {
               log.error("node1 caught exception", e);
               node1Exception = e;
               rollback();
            } catch (AssertionFailedError e) {
               node1Failure = e;
               rollback();
            } finally {
               commitLatch.countDown();
               completionLatch.countDown();
            }
         }
      };

      inserter.setDaemon(true);
      reader.setDaemon(true);
      inserter.start();
      reader.start();

      assertTrue("Threads completed", completionLatch.await(1, TimeUnit.SECONDS));

      assertThreadsRanCleanly();

      long txTimestamp = System.currentTimeMillis();
      assertEquals("Correct node1 value", VALUE1, localAccessStrategy.get(KEY, txTimestamp));
      Object expected = isUsingInvalidation() ? null : VALUE1;
      assertEquals("Correct node2 value", expected, remoteAccessStrategy.get(KEY, txTimestamp));
   }

   @Test
   public void testUpdate() throws Exception {

      final Object KEY = TestingKeyFactory.generateEntityCacheKey( KEY_BASE + testCount++ );

      // Set up initial state
      localAccessStrategy.putFromLoad(KEY, VALUE1, System.currentTimeMillis(), new Integer(1));
      remoteAccessStrategy.putFromLoad(KEY, VALUE1, System.currentTimeMillis(), new Integer(1));

      // Let the async put propagate
      sleep(250);

      final CountDownLatch readLatch = new CountDownLatch(1);
      final CountDownLatch commitLatch = new CountDownLatch(1);
      final CountDownLatch completionLatch = new CountDownLatch(2);

      Thread updater = new Thread("testUpdate-updater") {

         @Override
         public void run() {
            boolean readerUnlocked = false;
            try {
               long txTimestamp = System.currentTimeMillis();
               BatchModeTransactionManager.getInstance().begin();
               log.debug("Transaction began, get initial value");
               assertEquals("Correct initial value", VALUE1, localAccessStrategy.get(KEY, txTimestamp));
               log.debug("Now update value");
               localAccessStrategy.update(KEY, VALUE2, new Integer(2), new Integer(1));
               log.debug("Notify the read latch");
               readLatch.countDown();
               readerUnlocked = true;
               log.debug("Await commit");
               commitLatch.await();
               BatchModeTransactionManager.getInstance().commit();
            } catch (Exception e) {
               log.error("node1 caught exception", e);
               node1Exception = e;
               rollback();
            } catch (AssertionFailedError e) {
               node1Failure = e;
               rollback();
            } finally {
               if (!readerUnlocked) {
                  readLatch.countDown();
               }
               log.debug("Completion latch countdown");
               completionLatch.countDown();
            }
         }
      };

      Thread reader = new Thread("testUpdate-reader") {

         @Override
         public void run() {
            try {
               long txTimestamp = System.currentTimeMillis();
               BatchModeTransactionManager.getInstance().begin();
               log.debug("Transaction began, await read latch");
               readLatch.await();
               log.debug("Read latch acquired, verify local access strategy");

               // This won't block w/ mvc and will read the old value
               Object expected = VALUE1;
               assertEquals("Correct value", expected, localAccessStrategy.get(KEY, txTimestamp));

               BatchModeTransactionManager.getInstance().commit();
            } catch (Exception e) {
               log.error("node1 caught exception", e);
               node1Exception = e;
               rollback();
            } catch (AssertionFailedError e) {
               node1Failure = e;
               rollback();
            } finally {
               commitLatch.countDown();
               log.debug("Completion latch countdown");
               completionLatch.countDown();
            }
         }
      };

      updater.setDaemon(true);
      reader.setDaemon(true);
      updater.start();
      reader.start();

      // Should complete promptly
      assertTrue(completionLatch.await(2, TimeUnit.SECONDS));

      assertThreadsRanCleanly();

      long txTimestamp = System.currentTimeMillis();
      assertEquals("Correct node1 value", VALUE2, localAccessStrategy.get(KEY, txTimestamp));
      Object expected = isUsingInvalidation() ? null : VALUE2;
      assertEquals("Correct node2 value", expected, remoteAccessStrategy.get(KEY, txTimestamp));
   }

   @Test
   public void testRemove() throws Exception {
      evictOrRemoveTest(false);
   }

   @Test
   public void testRemoveAll() throws Exception {
      evictOrRemoveAllTest(false);
   }

   @Test
   public void testEvict() throws Exception {
      evictOrRemoveTest(true);
   }

   @Test
   public void testEvictAll() throws Exception {
      evictOrRemoveAllTest(true);
   }

   private void evictOrRemoveTest(final boolean evict) throws Exception {
      final Object KEY = TestingKeyFactory.generateEntityCacheKey( KEY_BASE + testCount++ );
      assertEquals(0, getValidKeyCount(localEntityRegion.getCache().keySet()));
      assertEquals(0, getValidKeyCount(remoteEntityRegion.getCache().keySet()));

      assertNull("local is clean", localAccessStrategy.get(KEY, System.currentTimeMillis()));
      assertNull("remote is clean", remoteAccessStrategy.get(KEY, System.currentTimeMillis()));

      localAccessStrategy.putFromLoad(KEY, VALUE1, System.currentTimeMillis(), new Integer(1));
      assertEquals(VALUE1, localAccessStrategy.get(KEY, System.currentTimeMillis()));
      remoteAccessStrategy.putFromLoad(KEY, VALUE1, System.currentTimeMillis(), new Integer(1));
      assertEquals(VALUE1, remoteAccessStrategy.get(KEY, System.currentTimeMillis()));

      Caches.withinTx(localEntityRegion.getTransactionManager(), new Callable<Void>() {
         @Override
         public Void call() throws Exception {
            if (evict)
               localAccessStrategy.evict(KEY);
            else
               localAccessStrategy.remove(KEY);
            return null;
         }
      });
      assertEquals(null, localAccessStrategy.get(KEY, System.currentTimeMillis()));
      assertEquals(0, getValidKeyCount(localEntityRegion.getCache().keySet()));
      assertEquals(null, remoteAccessStrategy.get(KEY, System.currentTimeMillis()));
      assertEquals(0, getValidKeyCount(remoteEntityRegion.getCache().keySet()));
   }

   private void evictOrRemoveAllTest(final boolean evict) throws Exception {
      final Object KEY = TestingKeyFactory.generateEntityCacheKey( KEY_BASE + testCount++ );
      assertEquals(0, getValidKeyCount(localEntityRegion.getCache().keySet()));
      assertEquals(0, getValidKeyCount(remoteEntityRegion.getCache().keySet()));
      assertNull("local is clean", localAccessStrategy.get(KEY, System.currentTimeMillis()));
      assertNull("remote is clean", remoteAccessStrategy.get(KEY, System.currentTimeMillis()));

      localAccessStrategy.putFromLoad(KEY, VALUE1, System.currentTimeMillis(), new Integer(1));
      assertEquals(VALUE1, localAccessStrategy.get(KEY, System.currentTimeMillis()));

      // Wait for async propagation
      sleep(250);

      remoteAccessStrategy.putFromLoad(KEY, VALUE1, System.currentTimeMillis(), new Integer(1));
      assertEquals(VALUE1, remoteAccessStrategy.get(KEY, System.currentTimeMillis()));

      // Wait for async propagation
      sleep(250);

      Caches.withinTx(localEntityRegion.getTransactionManager(), new Callable<Void>() {
         @Override
         public Void call() throws Exception {
            if (evict) {
               log.debug("Call evict all locally");
               localAccessStrategy.evictAll();
            } else {
               localAccessStrategy.removeAll();
            }
            return null;
         }
      });

      // This should re-establish the region root node in the optimistic case
      assertNull(localAccessStrategy.get(KEY, System.currentTimeMillis()));
      assertEquals(0, getValidKeyCount(localEntityRegion.getCache().keySet()));

      // Re-establishing the region root on the local node doesn't
      // propagate it to other nodes. Do a get on the remote node to re-establish
      assertEquals(null, remoteAccessStrategy.get(KEY, System.currentTimeMillis()));
      assertEquals(0, getValidKeyCount(remoteEntityRegion.getCache().keySet()));

      // Test whether the get above messes up the optimistic version
      remoteAccessStrategy.putFromLoad(KEY, VALUE1, System.currentTimeMillis(), new Integer(1));
      assertEquals(VALUE1, remoteAccessStrategy.get(KEY, System.currentTimeMillis()));
      assertEquals(1, getValidKeyCount(remoteEntityRegion.getCache().keySet()));

      // Wait for async propagation
      sleep(250);

      assertEquals(
            "local is correct", (isUsingInvalidation() ? null : VALUE1), localAccessStrategy
            .get(KEY, System.currentTimeMillis())
      );
      assertEquals(
            "remote is correct", VALUE1, remoteAccessStrategy.get(
            KEY, System
            .currentTimeMillis()
      )
      );
   }

   protected void rollback() {
      try {
         BatchModeTransactionManager.getInstance().rollback();
      } catch (Exception e) {
         log.error(e.getMessage(), e);
      }
   }
}


File: hibernate-infinispan/src/test/java/org/hibernate/test/cache/infinispan/entity/EntityRegionImplTestCase.java
/*
 * Hibernate, Relational Persistence for Idiomatic Java
 *
 * License: GNU Lesser General Public License (LGPL), version 2.1 or later.
 * See the lgpl.txt file in the root directory or <http://www.gnu.org/licenses/lgpl-2.1.html>.
 */
package org.hibernate.test.cache.infinispan.entity;

import java.util.Properties;

import org.hibernate.cache.CacheException;
import org.hibernate.cache.infinispan.InfinispanRegionFactory;
import org.hibernate.cache.internal.CacheDataDescriptionImpl;
import org.hibernate.cache.spi.CacheDataDescription;
import org.hibernate.cache.spi.EntityRegion;
import org.hibernate.cache.spi.Region;
import org.hibernate.cache.spi.RegionFactory;
import org.hibernate.cache.spi.access.AccessType;
import org.hibernate.test.cache.infinispan.AbstractEntityCollectionRegionTestCase;
import org.infinispan.AdvancedCache;

import static org.junit.Assert.assertNull;
import static org.junit.Assert.fail;

/**
 * Tests of EntityRegionImpl.
 * 
 * @author Galder Zamarreño
 * @since 3.5
 */
public class EntityRegionImplTestCase extends AbstractEntityCollectionRegionTestCase {

   private static CacheDataDescription MUTABLE_NON_VERSIONED = new CacheDataDescriptionImpl(true, false, null);

   @Override
   protected void supportedAccessTypeTest(RegionFactory regionFactory, Properties properties) {
      EntityRegion region = regionFactory.buildEntityRegion("test", properties, MUTABLE_NON_VERSIONED);
      assertNull("Got TRANSACTIONAL",
            region.buildAccessStrategy(AccessType.TRANSACTIONAL).lockRegion());
      try {
         region.buildAccessStrategy(AccessType.NONSTRICT_READ_WRITE);
         fail("Incorrectly got NONSTRICT_READ_WRITE");
      } catch (CacheException good) {
      }

      try {
         region.buildAccessStrategy(AccessType.READ_WRITE);
         fail("Incorrectly got READ_WRITE");
      } catch (CacheException good) {
      }
   }

   @Override
   protected void putInRegion(Region region, Object key, Object value) {
      ((EntityRegion) region).buildAccessStrategy(AccessType.TRANSACTIONAL).insert(key, value, 1);
   }

   @Override
   protected void removeFromRegion(Region region, Object key) {
      ((EntityRegion) region).buildAccessStrategy(AccessType.TRANSACTIONAL).remove(key);
   }

   @Override
   protected Region createRegion(InfinispanRegionFactory regionFactory, String regionName, Properties properties, CacheDataDescription cdd) {
      return regionFactory.buildEntityRegion(regionName, properties, cdd);
   }

   @Override
   protected AdvancedCache getInfinispanCache(InfinispanRegionFactory regionFactory) {
      return regionFactory.getCacheManager().getCache(
            InfinispanRegionFactory.DEF_ENTITY_RESOURCE).getAdvancedCache();
   }

}


File: hibernate-infinispan/src/test/java/org/hibernate/test/cache/infinispan/entity/TransactionalExtraAPITestCase.java
/*
 * Hibernate, Relational Persistence for Idiomatic Java
 *
 * License: GNU Lesser General Public License (LGPL), version 2.1 or later.
 * See the lgpl.txt file in the root directory or <http://www.gnu.org/licenses/lgpl-2.1.html>.
 */
package org.hibernate.test.cache.infinispan.entity;

import org.hibernate.boot.registry.StandardServiceRegistryBuilder;
import org.hibernate.cache.infinispan.InfinispanRegionFactory;
import org.hibernate.cache.internal.CacheDataDescriptionImpl;
import org.hibernate.cache.spi.access.AccessType;
import org.hibernate.cache.spi.access.EntityRegionAccessStrategy;
import org.hibernate.cache.spi.access.SoftLock;
import org.hibernate.test.cache.infinispan.AbstractNonFunctionalTestCase;
import org.hibernate.test.cache.infinispan.NodeEnvironment;
import org.hibernate.test.cache.infinispan.util.CacheTestUtil;
import org.hibernate.test.cache.infinispan.util.TestingKeyFactory;
import org.junit.After;
import org.junit.Before;
import org.junit.Test;

import static org.junit.Assert.assertFalse;
import static org.junit.Assert.assertNull;

/**
 * Tests for the "extra API" in EntityRegionAccessStrategy;.
 * <p>
 * By "extra API" we mean those methods that are superfluous to the 
 * function of the JBC integration, where the impl is a no-op or a static
 * false return value, UnsupportedOperationException, etc.
 * 
 * @author Galder Zamarreño
 * @since 3.5
 */
public class TransactionalExtraAPITestCase extends AbstractNonFunctionalTestCase {
	public static final String REGION_NAME = "test/com.foo.test";
	public static final Object KEY = TestingKeyFactory.generateEntityCacheKey( "KEY" );
	public static final String VALUE1 = "VALUE1";
	public static final String VALUE2 = "VALUE2";

	private NodeEnvironment environment;
	private EntityRegionAccessStrategy accessStrategy;

	@Before
	public final void prepareLocalAccessStrategy() throws Exception {
		environment = new NodeEnvironment( createStandardServiceRegistryBuilder() );
		environment.prepare();

		// Sleep a bit to avoid concurrent FLUSH problem
		avoidConcurrentFlush();

		accessStrategy = environment.getEntityRegion( REGION_NAME, new CacheDataDescriptionImpl(true, false, null)).buildAccessStrategy( getAccessType() );
   }

	protected StandardServiceRegistryBuilder createStandardServiceRegistryBuilder() {
		StandardServiceRegistryBuilder ssrb = CacheTestUtil.buildBaselineStandardServiceRegistryBuilder(
				REGION_PREFIX,
				InfinispanRegionFactory.class,
				true,
				false
		);
		ssrb.applySetting( InfinispanRegionFactory.ENTITY_CACHE_RESOURCE_PROP, getCacheConfigName() );
		return ssrb;
	}

	@After
	public final void releaseLocalAccessStrategy() throws Exception {
		if ( environment != null ) {
			environment.release();
		}
	}

	protected final EntityRegionAccessStrategy getEntityAccessStrategy() {
		return accessStrategy;
	}

	protected String getCacheConfigName() {
		return "entity";
	}

	protected AccessType getAccessType() {
		return AccessType.TRANSACTIONAL;
	}

	@Test
	@SuppressWarnings( {"UnnecessaryBoxing"})
	public void testLockItem() {
		assertNull( getEntityAccessStrategy().lockItem( KEY, Integer.valueOf( 1 ) ) );
	}

	@Test
	public void testLockRegion() {
		assertNull( getEntityAccessStrategy().lockRegion() );
	}

	@Test
	public void testUnlockItem() {
		getEntityAccessStrategy().unlockItem( KEY, new MockSoftLock() );
	}

	@Test
	public void testUnlockRegion() {
		getEntityAccessStrategy().unlockItem( KEY, new MockSoftLock() );
	}

	@Test
	@SuppressWarnings( {"UnnecessaryBoxing"})
	public void testAfterInsert() {
		assertFalse(
				"afterInsert always returns false",
				getEntityAccessStrategy().afterInsert(
						KEY,
						VALUE1,
						Integer.valueOf( 1 )
				)
		);
	}

	@Test
	@SuppressWarnings( {"UnnecessaryBoxing"})
	public void testAfterUpdate() {
		assertFalse(
				"afterInsert always returns false",
				getEntityAccessStrategy().afterUpdate(
						KEY,
						VALUE2,
						Integer.valueOf( 1 ),
						Integer.valueOf( 2 ),
						new MockSoftLock()
				)
		);
	}

	public static class MockSoftLock implements SoftLock {
	}
}


File: hibernate-infinispan/src/test/java/org/hibernate/test/cache/infinispan/functional/cluster/EntityCollectionInvalidationTestCase.java
/*
 * Hibernate, Relational Persistence for Idiomatic Java
 *
 * License: GNU Lesser General Public License (LGPL), version 2.1 or later.
 * See the lgpl.txt file in the root directory or <http://www.gnu.org/licenses/lgpl-2.1.html>.
 */
package org.hibernate.test.cache.infinispan.functional.cluster;

import javax.transaction.TransactionManager;
import java.util.HashSet;
import java.util.Iterator;
import java.util.Set;

import org.hibernate.Session;
import org.hibernate.SessionFactory;
import org.hibernate.test.cache.infinispan.functional.Contact;
import org.hibernate.test.cache.infinispan.functional.Customer;
import org.infinispan.Cache;
import org.infinispan.manager.CacheContainer;
import org.infinispan.notifications.Listener;
import org.infinispan.notifications.cachelistener.annotation.CacheEntryVisited;
import org.infinispan.notifications.cachelistener.event.CacheEntryVisitedEvent;
import org.infinispan.util.logging.Log;
import org.infinispan.util.logging.LogFactory;
import org.jboss.util.collection.ConcurrentSet;
import org.junit.Test;

import static org.junit.Assert.assertEquals;
import static org.junit.Assert.assertTrue;

/**
 * EntityCollectionInvalidationTestCase.
 *
 * @author Galder Zamarreño
 * @since 3.5
 */
public class EntityCollectionInvalidationTestCase extends DualNodeTestCase {
	private static final Log log = LogFactory.getLog( EntityCollectionInvalidationTestCase.class );

	private static final long SLEEP_TIME = 50l;
	private static final Integer CUSTOMER_ID = new Integer( 1 );

	static int test = 0;

	@Test
	public void testAll() throws Exception {
		log.info( "*** testAll()" );

		// Bind a listener to the "local" cache
		// Our region factory makes its CacheManager available to us
		CacheContainer localManager = ClusterAwareRegionFactory.getCacheManager( DualNodeTestCase.LOCAL );
		// Cache localCache = localManager.getCache("entity");
		Cache localCustomerCache = localManager.getCache( Customer.class.getName() );
		Cache localContactCache = localManager.getCache( Contact.class.getName() );
		Cache localCollectionCache = localManager.getCache( Customer.class.getName() + ".contacts" );
		MyListener localListener = new MyListener( "local" );
		localCustomerCache.addListener( localListener );
		localContactCache.addListener( localListener );
		localCollectionCache.addListener( localListener );
		TransactionManager localTM = DualNodeJtaTransactionManagerImpl.getInstance( DualNodeTestCase.LOCAL );

		// Bind a listener to the "remote" cache
		CacheContainer remoteManager = ClusterAwareRegionFactory.getCacheManager( DualNodeTestCase.REMOTE );
		Cache remoteCustomerCache = remoteManager.getCache( Customer.class.getName() );
		Cache remoteContactCache = remoteManager.getCache( Contact.class.getName() );
		Cache remoteCollectionCache = remoteManager.getCache( Customer.class.getName() + ".contacts" );
		MyListener remoteListener = new MyListener( "remote" );
		remoteCustomerCache.addListener( remoteListener );
		remoteContactCache.addListener( remoteListener );
		remoteCollectionCache.addListener( remoteListener );
		TransactionManager remoteTM = DualNodeJtaTransactionManagerImpl.getInstance( DualNodeTestCase.REMOTE );

		SessionFactory localFactory = sessionFactory();
		SessionFactory remoteFactory = secondNodeEnvironment().getSessionFactory();

		try {
			assertTrue( remoteListener.isEmpty() );
			assertTrue( localListener.isEmpty() );

			log.debug( "Create node 0" );
			IdContainer ids = createCustomer( localFactory, localTM );

			assertTrue( remoteListener.isEmpty() );
			assertTrue( localListener.isEmpty() );

			// Sleep a bit to let async commit propagate. Really just to
			// help keep the logs organized for debugging any issues
			sleep( SLEEP_TIME );

			log.debug( "Find node 0" );
			// This actually brings the collection into the cache
			getCustomer( ids.customerId, localFactory, localTM );

			sleep( SLEEP_TIME );

			// Now the collection is in the cache so, the 2nd "get"
			// should read everything from the cache
			log.debug( "Find(2) node 0" );
			localListener.clear();
			getCustomer( ids.customerId, localFactory, localTM );

			// Check the read came from the cache
			log.debug( "Check cache 0" );
			assertLoadedFromCache( localListener, ids.customerId, ids.contactIds );

			log.debug( "Find node 1" );
			// This actually brings the collection into the cache since invalidation is in use
			getCustomer( ids.customerId, remoteFactory, remoteTM );

			// Now the collection is in the cache so, the 2nd "get"
			// should read everything from the cache
			log.debug( "Find(2) node 1" );
			remoteListener.clear();
			getCustomer( ids.customerId, remoteFactory, remoteTM );

			// Check the read came from the cache
			log.debug( "Check cache 1" );
			assertLoadedFromCache( remoteListener, ids.customerId, ids.contactIds );

			// Modify customer in remote
			remoteListener.clear();
			ids = modifyCustomer( ids.customerId, remoteFactory, remoteTM );
			sleep( 250 );
			assertLoadedFromCache( remoteListener, ids.customerId, ids.contactIds );

			// After modification, local cache should have been invalidated and hence should be empty
			assertEquals( 0, getValidKeyCount( localCollectionCache.keySet() ) );
			assertEquals( 0, getValidKeyCount( localCustomerCache.keySet() ) );
		}
		catch (Exception e) {
			log.error( "Error", e );
			throw e;
		}
		finally {
			// cleanup the db
			log.debug( "Cleaning up" );
			cleanup( localFactory, localTM );
		}
	}

	private IdContainer createCustomer(SessionFactory sessionFactory, TransactionManager tm)
			throws Exception {
		log.debug( "CREATE CUSTOMER" );

		tm.begin();

		try {
			Session session = sessionFactory.getCurrentSession();
			Customer customer = new Customer();
			customer.setName( "JBoss" );
			Set<Contact> contacts = new HashSet<Contact>();

			Contact kabir = new Contact();
			kabir.setCustomer( customer );
			kabir.setName( "Kabir" );
			kabir.setTlf( "1111" );
			contacts.add( kabir );

			Contact bill = new Contact();
			bill.setCustomer( customer );
			bill.setName( "Bill" );
			bill.setTlf( "2222" );
			contacts.add( bill );

			customer.setContacts( contacts );

			session.save( customer );
			tm.commit();

			IdContainer ids = new IdContainer();
			ids.customerId = customer.getId();
			Set contactIds = new HashSet();
			contactIds.add( kabir.getId() );
			contactIds.add( bill.getId() );
			ids.contactIds = contactIds;

			return ids;
		}
		catch (Exception e) {
			log.error( "Caught exception creating customer", e );
			try {
				tm.rollback();
			}
			catch (Exception e1) {
				log.error( "Exception rolling back txn", e1 );
			}
			throw e;
		}
		finally {
			log.debug( "CREATE CUSTOMER -  END" );
		}
	}

	private Customer getCustomer(Integer id, SessionFactory sessionFactory, TransactionManager tm) throws Exception {
		log.debug( "Find customer with id=" + id );
		tm.begin();
		try {
			Session session = sessionFactory.getCurrentSession();
			Customer customer = doGetCustomer( id, session, tm );
			tm.commit();
			return customer;
		}
		catch (Exception e) {
			try {
				tm.rollback();
			}
			catch (Exception e1) {
				log.error( "Exception rolling back txn", e1 );
			}
			throw e;
		}
		finally {
			log.debug( "Find customer ended." );
		}
	}

	private Customer doGetCustomer(Integer id, Session session, TransactionManager tm) throws Exception {
		Customer customer = (Customer) session.get( Customer.class, id );
		// Access all the contacts
		for ( Iterator it = customer.getContacts().iterator(); it.hasNext(); ) {
			((Contact) it.next()).getName();
		}
		return customer;
	}

	private IdContainer modifyCustomer(Integer id, SessionFactory sessionFactory, TransactionManager tm)
			throws Exception {
		log.debug( "Modify customer with id=" + id );
		tm.begin();
		try {
			Session session = sessionFactory.getCurrentSession();
			IdContainer ids = new IdContainer();
			Set contactIds = new HashSet();
			Customer customer = doGetCustomer( id, session, tm );
			customer.setName( "NewJBoss" );
			ids.customerId = customer.getId();
			Set<Contact> contacts = customer.getContacts();
			for ( Contact c : contacts ) {
				contactIds.add( c.getId() );
			}
			Contact contact = contacts.iterator().next();
			contacts.remove( contact );
			contactIds.remove( contact.getId() );
			ids.contactIds = contactIds;
			contact.setCustomer( null );

			session.save( customer );
			tm.commit();
			return ids;
		}
		catch (Exception e) {
			try {
				tm.rollback();
			}
			catch (Exception e1) {
				log.error( "Exception rolling back txn", e1 );
			}
			throw e;
		}
		finally {
			log.debug( "Find customer ended." );
		}
	}

	private void cleanup(SessionFactory sessionFactory, TransactionManager tm) throws Exception {
		tm.begin();
		try {
			Session session = sessionFactory.getCurrentSession();
			Customer c = (Customer) session.get( Customer.class, CUSTOMER_ID );
			if ( c != null ) {
				Set contacts = c.getContacts();
				for ( Iterator it = contacts.iterator(); it.hasNext(); ) {
					session.delete( it.next() );
				}
				c.setContacts( null );
				session.delete( c );
			}

			tm.commit();
		}
		catch (Exception e) {
			try {
				tm.rollback();
			}
			catch (Exception e1) {
				log.error( "Exception rolling back txn", e1 );
			}
			log.error( "Caught exception in cleanup", e );
		}
	}

	private void assertLoadedFromCache(MyListener listener, Integer custId, Set contactIds) {
		assertTrue(
				"Customer#" + custId + " was in cache", listener.visited.contains(
				"Customer#"
						+ custId
		)
		);
		for ( Iterator it = contactIds.iterator(); it.hasNext(); ) {
			Integer contactId = (Integer) it.next();
			assertTrue(
					"Contact#" + contactId + " was in cache", listener.visited.contains(
					"Contact#"
							+ contactId
			)
			);
			assertTrue(
					"Contact#" + contactId + " was in cache", listener.visited.contains(
					"Contact#"
							+ contactId
			)
			);
		}
		assertTrue(
				"Customer.contacts" + custId + " was in cache", listener.visited
				.contains( "Customer.contacts#" + custId )
		);
	}

	protected int getValidKeyCount(Set keys) {
      return keys.size();
	}

	@Listener
	public static class MyListener {
		private static final Log log = LogFactory.getLog( MyListener.class );
		private Set<String> visited = new ConcurrentSet<String>();
		private final String name;

		public MyListener(String name) {
			this.name = name;
		}

		public void clear() {
			visited.clear();
		}

		public boolean isEmpty() {
			return visited.isEmpty();
		}

		@CacheEntryVisited
		public void nodeVisited(CacheEntryVisitedEvent event) {
			log.debug( event.toString() );
			if ( !event.isPre() ) {
				String key = String.valueOf(event.getKey());
				log.debug( "MyListener[" + name + "] - Visiting key " + key );
				// String name = fqn.toString();
				String token = ".functional.";
				int index = key.indexOf( token );
				if ( index > -1 ) {
					index += token.length();
					key = key.substring( index );
					log.debug( "MyListener[" + name + "] - recording visit to " + key );
					visited.add( key );
				}
			}
		}
	}

	private class IdContainer {
		Integer customerId;
		Set<Integer> contactIds;
	}

}


File: hibernate-infinispan/src/test/java/org/hibernate/test/cache/infinispan/tm/XaConnectionProvider.java
/*
 * Hibernate, Relational Persistence for Idiomatic Java
 *
 * License: GNU Lesser General Public License (LGPL), version 2.1 or later.
 * See the lgpl.txt file in the root directory or <http://www.gnu.org/licenses/lgpl-2.1.html>.
 */
package org.hibernate.test.cache.infinispan.tm;

import java.sql.Connection;
import java.sql.SQLException;
import java.util.Properties;

import org.hibernate.HibernateException;
import org.hibernate.service.UnknownUnwrapTypeException;
import org.hibernate.engine.jdbc.connections.spi.ConnectionProvider;
import org.hibernate.service.spi.Stoppable;
import org.hibernate.testing.env.ConnectionProviderBuilder;

/**
 * XaConnectionProvider.
 *
 * @author Galder Zamarreño
 * @since 3.5
 */
public class XaConnectionProvider implements ConnectionProvider {
	private static ConnectionProvider actualConnectionProvider = ConnectionProviderBuilder.buildConnectionProvider();
	private boolean isTransactional;

	public static ConnectionProvider getActualConnectionProvider() {
		return actualConnectionProvider;
	}

	@Override
	public boolean isUnwrappableAs(Class unwrapType) {
		return XaConnectionProvider.class.isAssignableFrom( unwrapType ) ||
				ConnectionProvider.class.equals( unwrapType ) ||
				actualConnectionProvider.getClass().isAssignableFrom( unwrapType );
	}

	@Override
	@SuppressWarnings( {"unchecked"})
	public <T> T unwrap(Class<T> unwrapType) {
		if ( XaConnectionProvider.class.isAssignableFrom( unwrapType ) ) {
			return (T) this;
		}
		else if ( ConnectionProvider.class.isAssignableFrom( unwrapType ) ||
				actualConnectionProvider.getClass().isAssignableFrom( unwrapType ) ) {
			return (T) getActualConnectionProvider();
		}
		else {
			throw new UnknownUnwrapTypeException( unwrapType );
		}
	}

	public void configure(Properties props) throws HibernateException {
	}

	public Connection getConnection() throws SQLException {
		XaTransactionImpl currentTransaction = XaTransactionManagerImpl.getInstance().getCurrentTransaction();
		if ( currentTransaction == null ) {
			isTransactional = false;
			return actualConnectionProvider.getConnection();
		}
		else {
			isTransactional = true;
			Connection connection = currentTransaction.getEnlistedConnection();
			if ( connection == null ) {
				connection = actualConnectionProvider.getConnection();
				currentTransaction.enlistConnection( connection );
			}
			return connection;
		}
	}

	public void closeConnection(Connection conn) throws SQLException {
		if ( !isTransactional ) {
			conn.close();
		}
	}

	public void close() throws HibernateException {
		if ( actualConnectionProvider instanceof Stoppable ) {
			((Stoppable) actualConnectionProvider).stop();
		}
	}

	public boolean supportsAggressiveRelease() {
		return true;
	}
}
