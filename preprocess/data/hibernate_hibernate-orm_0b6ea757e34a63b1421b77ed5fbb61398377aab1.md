Refactoring Types: ['Move Class']
c/test/java/org/hibernate/jpa/test/callbacks/CallbacksTest.java
/*
 * Hibernate, Relational Persistence for Idiomatic Java
 *
 * License: GNU Lesser General Public License (LGPL), version 2.1 or later.
 * See the lgpl.txt file in the root directory or <http://www.gnu.org/licenses/lgpl-2.1.html>.
 */
package org.hibernate.jpa.test.callbacks;

import java.util.ArrayList;
import java.util.Date;
import java.util.List;
import javax.persistence.EntityManager;

import org.junit.Test;

import org.hibernate.Hibernate;
import org.hibernate.internal.util.collections.ArrayHelper;
import org.hibernate.jpa.test.BaseEntityManagerFunctionalTestCase;
import org.hibernate.jpa.test.Cat;
import org.hibernate.jpa.test.Kitten;

import org.hibernate.testing.FailureExpected;
import org.hibernate.testing.TestForIssue;

import static org.junit.Assert.assertEquals;
import static org.junit.Assert.assertFalse;
import static org.junit.Assert.assertNotNull;
import static org.junit.Assert.assertTrue;
import static org.junit.Assert.fail;

/**
 * @author Emmanuel Bernard
 */
@SuppressWarnings("unchecked")
public class CallbacksTest extends BaseEntityManagerFunctionalTestCase {
	@Test
	public void testCallbackMethod() throws Exception {
		EntityManager em = getOrCreateEntityManager();
		Cat c = new Cat();
		c.setName( "Kitty" );
		c.setDateOfBirth( new Date( 90, 11, 15 ) );
		em.getTransaction().begin();
		em.persist( c );
		em.getTransaction().commit();
		em.clear();
		em.getTransaction().begin();
		c = em.find( Cat.class, c.getId() );
		assertFalse( c.getAge() == 0 );
		c.setName( "Tomcat" ); //update this entity
		em.getTransaction().commit();
		em.clear();
		em.getTransaction().begin();
		c = em.find( Cat.class, c.getId() );
		assertEquals( "Tomcat", c.getName() );
		em.getTransaction().commit();
		em.close();
	}

	@Test
	public void testEntityListener() throws Exception {
		EntityManager em = getOrCreateEntityManager();
		Cat c = new Cat();
		c.setName( "Kitty" );
		c.setLength( 12 );
		c.setDateOfBirth( new Date( 90, 11, 15 ) );
		em.getTransaction().begin();
		int previousVersion = c.getManualVersion();
		em.persist( c );
		em.getTransaction().commit();
		em.getTransaction().begin();
		c = em.find( Cat.class, c.getId() );
		assertNotNull( c.getLastUpdate() );
		assertTrue( previousVersion < c.getManualVersion() );
		assertEquals( 12, c.getLength() );
		previousVersion = c.getManualVersion();
		c.setName( "new name" );
		em.getTransaction().commit();
		em.getTransaction().begin();
		c = em.find( Cat.class, c.getId() );
		assertTrue( previousVersion < c.getManualVersion() );
		em.getTransaction().commit();

		em.close();
	}

	@Test
	public void testPostPersist() throws Exception {
		EntityManager em = getOrCreateEntityManager();
		Cat c = new Cat();
		em.getTransaction().begin();
		c.setLength( 23 );
		c.setAge( 2 );
		c.setName( "Beetle" );
		c.setDateOfBirth( new Date() );
		em.persist( c );
		em.getTransaction().commit();
		em.close();
		List ids = Cat.getIdList();
		Object id = Cat.getIdList().get( ids.size() - 1 );
		assertNotNull( id );
	}

	//Not a test since the spec did not make the proper change on listeners
	public void listenerAnnotation() throws Exception {
		EntityManager em = getOrCreateEntityManager();
		Translation tl = new Translation();
		em.getTransaction().begin();
		tl.setInto( "France" );
		em.persist( tl );
		tl = new Translation();
		tl.setInto( "Bimboland" );
		try {
			em.persist( tl );
			em.flush();
			fail( "Annotations annotated by a listener not used" );
		}
		catch (IllegalArgumentException e) {
			//success
		}
		finally {
			em.getTransaction().rollback();
			em.close();
		}
	}

	@Test
	public void testPrePersistOnCascade() throws Exception {
		EntityManager em = getOrCreateEntityManager();
		em.getTransaction().begin();
		Television tv = new Television();
		RemoteControl rc = new RemoteControl();
		em.persist( tv );
		em.flush();
		tv.setControl( rc );
		tv.init();
		em.flush();
		assertNotNull( rc.getCreationDate() );
		em.getTransaction().rollback();
		em.close();
	}

	@Test
	public void testCallBackListenersHierarchy() throws Exception {
		EntityManager em = getOrCreateEntityManager();
		em.getTransaction().begin();
		Television tv = new Television();
		em.persist( tv );
		tv.setName( "Myaio" );
		tv.init();
		em.flush();
		assertEquals( 1, tv.counter );
		em.getTransaction().rollback();
		em.close();
		assertEquals( 5, tv.communication );
		assertTrue( tv.isLast );
	}

	@Test
	public void testException() throws Exception {
		EntityManager em = getOrCreateEntityManager();
		em.getTransaction().begin();
		Rythm r = new Rythm();
		try {
			em.persist( r );
			em.flush();
			fail("should have raised an ArythmeticException:");
		}
		catch (ArithmeticException e) {
			//success
		}
		catch( Exception e ) {
			fail("should have raised an ArythmeticException:" + e.getClass() );
		}

		em.getTransaction().rollback();
		em.close();

	}

	@Test
	public void testIdNullSetByPrePersist() throws Exception {
		Plant plant = new Plant();
		plant.setName( "Origuna plantula gigantic" );
		EntityManager em = getOrCreateEntityManager();
		em.getTransaction().begin();
		em.persist( plant );
		em.flush();
		em.getTransaction().rollback();
		em.close();
	}
	
	@Test
	@FailureExpected(message = "collection change does not trigger an event", jiraKey = "EJB-288")
	public void testPostUpdateCollection() throws Exception {
		// create a cat
		EntityManager em = getOrCreateEntityManager();
		Cat cat = new Cat();
		em.getTransaction().begin();
		cat.setLength( 23 );
		cat.setAge( 2 );
		cat.setName( "Beetle" );
		cat.setDateOfBirth( new Date() );
		em.persist( cat );
		em.getTransaction().commit();

		// assert it is persisted
		List ids = Cat.getIdList();
		Object id = Cat.getIdList().get( ids.size() - 1 );
		assertNotNull( id );

		// add a kitten to the cat - triggers PostCollectionRecreateEvent
		int postVersion = Cat.postVersion;
		em.getTransaction().begin();
		Kitten kitty = new Kitten();
		kitty.setName("kitty");
		List kittens = new ArrayList<Kitten>();
		kittens.add(kitty);
		cat.setKittens(kittens);
		em.getTransaction().commit();
		assertEquals("Post version should have been incremented.", postVersion + 1, Cat.postVersion);

		// add another kitten - triggers PostCollectionUpdateEvent.
		postVersion = Cat.postVersion;
		em.getTransaction().begin();
		Kitten tom = new Kitten();
		tom.setName("Tom");
		cat.getKittens().add(tom);
		em.getTransaction().commit();
		assertEquals("Post version should have been incremented.", postVersion + 1, Cat.postVersion);

		// delete a kitty - triggers PostCollectionUpdateEvent
		postVersion = Cat.postVersion;
		em.getTransaction().begin();
		cat.getKittens().remove(tom);
		em.getTransaction().commit();
		assertEquals("Post version should have been incremented.", postVersion + 1, Cat.postVersion);

		// delete and recreate kittens - triggers PostCollectionRemoveEvent and PostCollectionRecreateEvent)
		postVersion = Cat.postVersion;
		em.getTransaction().begin();
		cat.setKittens(new ArrayList<Kitten>());
		em.getTransaction().commit();
		assertEquals("Post version should have been incremented.", postVersion + 2, Cat.postVersion);

		em.close();
	}

	@Override
	public Class[] getAnnotatedClasses() {
		return new Class[]{
				Cat.class,
				Translation.class,
				Television.class,
				RemoteControl.class,
				Rythm.class,
				Plant.class,
				Kitten.class,
				EntityWithLazyProperty.class
		};
	}

	/**
	 * Test for HHH-7573.
	 * Load some test data into an entity which has a lazy property and a @PreUpdate callback, then reload and update a
	 * non lazy field which will trigger the PreUpdate lifecycle callback.
	 * @throws Exception
	 */
	@Test
	@TestForIssue( jiraKey = "HHH-7573" )
	public void testJpaFlushEntityEventListener() throws Exception {
		EntityWithLazyProperty entity;
		EntityManager em = getOrCreateEntityManager();

		byte[] testArray = new byte[]{0x2A};

		//persist the test entity.
		em.getTransaction().begin();
		entity = new EntityWithLazyProperty();
		entity.setSomeField("TEST");
		entity.setLazyData(testArray);
		em.persist(entity);
		em.getTransaction().commit();
		em.close();

		checkLazyField(entity, em, testArray);

		/**
		 * Set a non lazy field, therefore the lazyData field will be LazyPropertyInitializer.UNFETCHED_PROPERTY
		 * for both state and newState so the field should not change. This should no longer cause a ClassCastException.
		 */
		em = getOrCreateEntityManager();
	  	em.getTransaction().begin();
		entity = em.find(EntityWithLazyProperty.class, entity.getId());
		entity.setSomeField("TEST1");
		assertFalse( Hibernate.isPropertyInitialized( entity, "lazyData" ) );
		em.getTransaction().commit();
		assertFalse( Hibernate.isPropertyInitialized( entity, "lazyData" ) );
		em.close();

		checkLazyField(entity, em, testArray);

		/**
		 * Set the updateLazyFieldInPreUpdate flag so that the lazy field is updated from within the
		 * PreUpdate annotated callback method. So state == LazyPropertyInitializer.UNFETCHED_PROPERTY and
		 * newState == EntityWithLazyProperty.PRE_UPDATE_VALUE. This should no longer cause a ClassCastException.
		 */
		em = getOrCreateEntityManager();
		em.getTransaction().begin();
		entity = em.find(EntityWithLazyProperty.class, entity.getId());
		entity.setUpdateLazyFieldInPreUpdate(true);
		entity.setSomeField("TEST2");
		assertFalse( Hibernate.isPropertyInitialized( entity, "lazyData" ) );
		em.getTransaction().commit();
		assertTrue( Hibernate.isPropertyInitialized( entity, "lazyData" ) );
		em.close();

		checkLazyField(entity, em, EntityWithLazyProperty.PRE_UPDATE_VALUE);

		/**
		 * Set the updateLazyFieldInPreUpdate flag so that the lazy field is updated from within the
		 * PreUpdate annotated callback method and also set the lazyData field directly to testArray1. When we reload we
		 * should get EntityWithLazyProperty.PRE_UPDATE_VALUE.
		 */
		em = getOrCreateEntityManager();
		em.getTransaction().begin();
		entity = em.find(EntityWithLazyProperty.class, entity.getId());
		entity.setUpdateLazyFieldInPreUpdate(true);
		assertFalse( Hibernate.isPropertyInitialized( entity, "lazyData" ) );
		entity.setLazyData(testArray);
		assertTrue( Hibernate.isPropertyInitialized( entity, "lazyData" ) );
		entity.setSomeField("TEST3");
		em.getTransaction().commit();
		em.close();

		checkLazyField( entity, em, EntityWithLazyProperty.PRE_UPDATE_VALUE);
	}

	private void checkLazyField(EntityWithLazyProperty entity, EntityManager em, byte[] expected) {
		// reload the entity and check the lazy value matches what we expect.
		em = getOrCreateEntityManager();
		em.getTransaction().begin();
		entity = em.find(EntityWithLazyProperty.class, entity.getId());
		assertFalse( Hibernate.isPropertyInitialized( entity, "lazyData") );
		assertTrue( ArrayHelper.isEquals( expected, entity.getLazyData() ) );
		assertTrue( Hibernate.isPropertyInitialized( entity, "lazyData" ) );
		em.getTransaction().commit();
		em.close();
	}
}
