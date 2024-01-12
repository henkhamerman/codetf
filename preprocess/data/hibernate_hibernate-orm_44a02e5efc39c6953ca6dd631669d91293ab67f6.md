Refactoring Types: ['Rename Package']
rg/hibernate/bytecode/enhance/internal/PersistentAttributesEnhancer.java
/*
 * Hibernate, Relational Persistence for Idiomatic Java
 *
 * License: GNU Lesser General Public License (LGPL), version 2.1 or later.
 * See the lgpl.txt file in the root directory or <http://www.gnu.org/licenses/lgpl-2.1.html>.
 */
package org.hibernate.bytecode.enhance.internal;

import javassist.CannotCompileException;
import javassist.CtClass;
import javassist.CtField;
import javassist.CtMethod;
import javassist.Modifier;
import javassist.NotFoundException;
import javassist.bytecode.BadBytecode;
import javassist.bytecode.CodeIterator;
import javassist.bytecode.ConstPool;
import javassist.bytecode.MethodInfo;
import javassist.bytecode.Opcode;
import javassist.bytecode.SignatureAttribute;
import javassist.bytecode.stackmap.MapMaker;

import org.hibernate.bytecode.enhance.spi.EnhancementContext;
import org.hibernate.bytecode.enhance.spi.EnhancementException;
import org.hibernate.bytecode.enhance.spi.Enhancer;
import org.hibernate.bytecode.enhance.spi.EnhancerConstants;
import org.hibernate.engine.spi.CompositeOwner;
import org.hibernate.engine.spi.CompositeTracker;
import org.hibernate.internal.CoreLogging;
import org.hibernate.internal.CoreMessageLogger;

import javax.persistence.Embedded;
import javax.persistence.ManyToMany;
import javax.persistence.ManyToOne;
import javax.persistence.OneToMany;
import javax.persistence.OneToOne;
import java.util.IdentityHashMap;
import java.util.LinkedList;
import java.util.List;

/**
 * enhancer for persistent attributes of any type of entity
 *
 * @author <a href="mailto:lbarreiro@redhat.com">Luis Barreiro</a>
 */
public class PersistentAttributesEnhancer extends Enhancer {

	private static final CoreMessageLogger log = CoreLogging.messageLogger( PersistentAttributesEnhancer.class );

	public PersistentAttributesEnhancer(EnhancementContext context) {
		super( context );
	}

	public void enhance(CtClass managedCtClass) {
		final IdentityHashMap<String, PersistentAttributeAccessMethods> attrDescriptorMap = new IdentityHashMap<String, PersistentAttributeAccessMethods>();

		for ( CtField persistentField : collectPersistentFields( managedCtClass ) ) {
			attrDescriptorMap.put(
					persistentField.getName(), enhancePersistentAttribute(
							managedCtClass,
							persistentField
					)
			);
		}

		// lastly, find all references to the transformed fields and replace with calls to the added reader/writer methods
		enhanceAttributesAccess( managedCtClass, attrDescriptorMap );
	}

	private CtField[] collectPersistentFields(CtClass managedCtClass) {
		final List<CtField> persistentFieldList = new LinkedList<CtField>();
		for ( CtField ctField : managedCtClass.getDeclaredFields() ) {
			// skip static fields and skip fields added by enhancement
			if ( Modifier.isStatic( ctField.getModifiers() ) || ctField.getName().startsWith( "$$_hibernate_" ) ) {
				continue;
			}
			if ( enhancementContext.isPersistentField( ctField ) ) {
				persistentFieldList.add( ctField );
			}
		}
		return enhancementContext.order( persistentFieldList.toArray( new CtField[persistentFieldList.size()] ) );
	}

	private PersistentAttributeAccessMethods enhancePersistentAttribute(
			CtClass managedCtClass,
			CtField persistentField) {
		try {
			final AttributeTypeDescriptor typeDescriptor = AttributeTypeDescriptor.resolve( persistentField );
			return new PersistentAttributeAccessMethods(
					generateFieldReader( managedCtClass, persistentField, typeDescriptor ),
					generateFieldWriter( managedCtClass, persistentField, typeDescriptor )
			);
		}
		catch (Exception e) {
			final String msg = String.format(
					"Unable to enhance persistent attribute [%s:%s]",
					managedCtClass.getName(),
					persistentField.getName()
			);
			throw new EnhancementException( msg, e );
		}
	}

	private CtMethod generateFieldReader(
			CtClass managedCtClass,
			CtField persistentField,
			AttributeTypeDescriptor typeDescriptor) {
		final String fieldName = persistentField.getName();
		final String readerName = EnhancerConstants.PERSISTENT_FIELD_READER_PREFIX + fieldName;

		// read attempts only have to deal lazy-loading support, not dirty checking;
		// so if the field is not enabled as lazy-loadable return a plain simple getter as the reader
		if ( !enhancementContext.isLazyLoadable( persistentField ) ) {
			return MethodWriter.addGetter( managedCtClass, fieldName, readerName );
		}

		// TODO: temporary solution...
		try {
			return MethodWriter.write(
					managedCtClass, "public %s %s() {%n  %s%n  return this.%s;%n}",
					persistentField.getType().getName(),
					readerName,
					typeDescriptor.buildReadInterceptionBodyFragment( fieldName ),
					fieldName
			);
		}
		catch (CannotCompileException cce) {
			final String msg = String.format(
					"Could not enhance entity class [%s] to add field reader method [%s]",
					managedCtClass.getName(),
					readerName
			);
			throw new EnhancementException( msg, cce );
		}
		catch (NotFoundException nfe) {
			final String msg = String.format(
					"Could not enhance entity class [%s] to add field reader method [%s]",
					managedCtClass.getName(),
					readerName
			);
			throw new EnhancementException( msg, nfe );
		}
	}

	private CtMethod generateFieldWriter(
			CtClass managedCtClass,
			CtField persistentField,
			AttributeTypeDescriptor typeDescriptor) {
		final String fieldName = persistentField.getName();
		final String writerName = EnhancerConstants.PERSISTENT_FIELD_WRITER_PREFIX + fieldName;

		try {
			final CtMethod writer;

			if ( !enhancementContext.isLazyLoadable( persistentField ) ) {
				writer = MethodWriter.addSetter( managedCtClass, fieldName, writerName );
			}
			else {
				writer = MethodWriter.write(
						managedCtClass,
						"public void %s(%s %s) {%n  %s%n}",
						writerName,
						persistentField.getType().getName(),
						fieldName,
						typeDescriptor.buildWriteInterceptionBodyFragment( fieldName )
				);
			}

			if ( enhancementContext.isCompositeClass( managedCtClass ) ) {
				writer.insertBefore(
						String.format(
								"if (%s != null) { %<s.callOwner(\".%s\"); }%n",
								EnhancerConstants.TRACKER_COMPOSITE_FIELD_NAME,
								fieldName
						)
				);
			}
			else if ( enhancementContext.doDirtyCheckingInline( managedCtClass ) ) {
				writer.insertBefore(
						typeDescriptor.buildInLineDirtyCheckingBodyFragment(
								enhancementContext,
								persistentField
						)
				);
			}

			handleCompositeField( managedCtClass, persistentField, writer );

			if ( enhancementContext.doBiDirectionalAssociationManagement( persistentField ) ) {
				handleBiDirectionalAssociation( managedCtClass, persistentField, writer );
			}
			return writer;
		}
		catch (CannotCompileException cce) {
			final String msg = String.format(
					"Could not enhance entity class [%s] to add field writer method [%s]",
					managedCtClass.getName(),
					writerName
			);
			throw new EnhancementException( msg, cce );
		}
		catch (NotFoundException nfe) {
			final String msg = String.format(
					"Could not enhance entity class [%s] to add field writer method [%s]",
					managedCtClass.getName(),
					writerName
			);
			throw new EnhancementException( msg, nfe );
		}
	}

	private void handleBiDirectionalAssociation(CtClass managedCtClass, CtField persistentField, CtMethod fieldWriter)
			throws NotFoundException, CannotCompileException {
		if ( !isPossibleBiDirectionalAssociation( persistentField ) ) {
			return;
		}
		final CtClass targetEntity = getTargetEntityClass( persistentField );
		if ( targetEntity == null ) {
			log.debugf(
					"Could not find type of bi-directional association for field [%s#%s]",
					managedCtClass.getName(),
					persistentField.getName()
			);
			return;
		}
		final String mappedBy = getMappedBy( persistentField, targetEntity );
		if ( mappedBy.isEmpty() ) {
			log.debugf(
					"Could not find bi-directional association for field [%s#%s]",
					managedCtClass.getName(),
					persistentField.getName()
			);
			return;
		}

		// create a temporary getter and setter on the target entity to be able to compile our code
		final String mappedByGetterName = EnhancerConstants.PERSISTENT_FIELD_READER_PREFIX + mappedBy;
		final String mappedBySetterName = EnhancerConstants.PERSISTENT_FIELD_WRITER_PREFIX + mappedBy;
		MethodWriter.addGetter( targetEntity, mappedBy, mappedByGetterName );
		MethodWriter.addSetter( targetEntity, mappedBy, mappedBySetterName );

		if ( persistentField.hasAnnotation( OneToOne.class ) ) {
			// only unset when $1 != null to avoid recursion
			fieldWriter.insertBefore(
					String.format(
							"if ($0.%s != null && $1 != null) $0.%<s.%s(null);%n",
							persistentField.getName(),
							mappedBySetterName
					)
			);
			fieldWriter.insertAfter(
					String.format(
							"if ($1 != null && $1.%s() != $0) $1.%s($0);%n",
							mappedByGetterName,
							mappedBySetterName
					)
			);
		}
		if ( persistentField.hasAnnotation( OneToMany.class ) ) {
			// only remove elements not in the new collection or else we would loose those elements
			fieldWriter.insertBefore(
					String.format(
							"if ($0.%s != null) for (java.util.Iterator itr = $0.%<s.iterator(); itr.hasNext(); ) { %s target = (%<s) itr.next(); if ($1 == null || !$1.contains(target)) target.%s(null); }%n",
							persistentField.getName(),
							targetEntity.getName(),
							mappedBySetterName
					)
			);
			fieldWriter.insertAfter(
					String.format(
							"if ($1 != null) for (java.util.Iterator itr = $1.iterator(); itr.hasNext(); ) { %s target = (%<s) itr.next(); if (target.%s() != $0) target.%s((%s)$0); }%n",
							targetEntity.getName(),
							mappedByGetterName,
							mappedBySetterName,
							managedCtClass.getName()
					)
			);
		}
		if ( persistentField.hasAnnotation( ManyToOne.class ) ) {
			fieldWriter.insertBefore(
					String.format(
							"if ($0.%1$s != null && $0.%1$s.%2$s() != null) $0.%1$s.%2$s().remove($0);%n",
							persistentField.getName(),
							mappedByGetterName
					)
			);
			// check .contains($0) to avoid double inserts (but preventing duplicates)
			fieldWriter.insertAfter(
					String.format(
							"if ($1 != null && $1.%s() != null && !$1.%<s().contains($0) ) $1.%<s().add($0);%n",
							mappedByGetterName
					)
			);
		}
		if ( persistentField.hasAnnotation( ManyToMany.class ) ) {
			fieldWriter.insertBefore(
					String.format(
							"if ($0.%s != null) for (java.util.Iterator itr = $0.%<s.iterator(); itr.hasNext(); ) { %s target = (%<s) itr.next(); if ($1 == null || !$1.contains(target)) target.%s().remove($0); }%n",
							persistentField.getName(),
							targetEntity.getName(),
							mappedByGetterName
					)
			);
			fieldWriter.insertAfter(
					String.format(
							"if ($1 != null) for (java.util.Iterator itr = $1.iterator(); itr.hasNext(); ) { %s target = (%<s) itr.next(); if (target.%s() != $0 && target.%<s() != null) target.%<s().add($0); }%n",
							targetEntity.getName(),
							mappedByGetterName
					)
			);
		}
		// implementation note: association management @OneToMany and @ManyToMay works for add() operations but for remove() a snapshot of the collection is needed so we know what associations to break.
		// another approach that could force that behavior would be to return Collections.unmodifiableCollection() ...
	}

	private boolean isPossibleBiDirectionalAssociation(CtField persistentField) {
		return persistentField.hasAnnotation( OneToOne.class ) ||
				persistentField.hasAnnotation( OneToMany.class ) ||
				persistentField.hasAnnotation( ManyToOne.class ) ||
				persistentField.hasAnnotation( ManyToMany.class );
	}

	private String getMappedBy(CtField persistentField, CtClass targetEntity) {
		final String local = getMappedByFromAnnotation( persistentField );
		return local.isEmpty() ? getMappedByFromTargetEntity( persistentField, targetEntity ) : local;
	}

	private String getMappedByFromAnnotation(CtField persistentField) {
		try {
			if ( persistentField.hasAnnotation( OneToOne.class ) ) {
				return ( (OneToOne) persistentField.getAnnotation( OneToOne.class ) ).mappedBy();
			}
			if ( persistentField.hasAnnotation( OneToMany.class ) ) {
				return ( (OneToMany) persistentField.getAnnotation( OneToMany.class ) ).mappedBy();
			}
			// For @ManyToOne associations, mappedBy must come from the @OneToMany side of the association
			if ( persistentField.hasAnnotation( ManyToMany.class ) ) {
				return ( (ManyToMany) persistentField.getAnnotation( ManyToMany.class ) ).mappedBy();
			}
		}
		catch (ClassNotFoundException ignore) {
		}
		return "";
	}

	private String getMappedByFromTargetEntity(CtField persistentField, CtClass targetEntity) {
		// get mappedBy value by searching in the fields of the target entity class
		for ( CtField f : targetEntity.getDeclaredFields() ) {
			if ( enhancementContext.isPersistentField( f ) && getMappedByFromAnnotation( f ).equals( persistentField.getName() ) ) {
				log.debugf(
						"mappedBy association for field [%s:%s] is [%s:%s]",
						persistentField.getDeclaringClass().getName(),
						persistentField.getName(),
						targetEntity.getName(),
						f.getName()
				);
				return f.getName();
			}
		}
		return "";
	}

	private CtClass getTargetEntityClass(CtField persistentField) throws NotFoundException {
		// get targetEntity defined in the annotation
		try {
			Class<?> targetClass = null;
			if ( persistentField.hasAnnotation( OneToOne.class ) ) {
				targetClass = ( (OneToOne) persistentField.getAnnotation( OneToOne.class ) ).targetEntity();
			}
			if ( persistentField.hasAnnotation( OneToMany.class ) ) {
				targetClass = ( (OneToMany) persistentField.getAnnotation( OneToMany.class ) ).targetEntity();
			}
			if ( persistentField.hasAnnotation( ManyToOne.class ) ) {
				targetClass = ( (ManyToOne) persistentField.getAnnotation( ManyToOne.class ) ).targetEntity();
			}
			if ( persistentField.hasAnnotation( ManyToMany.class ) ) {
				targetClass = ( (ManyToMany) persistentField.getAnnotation( ManyToMany.class ) ).targetEntity();
			}
			if ( targetClass != null && targetClass != void.class ) {
				return classPool.get( targetClass.getName() );
			}
		}
		catch (ClassNotFoundException ignore) {
		}

		// infer targetEntity from generic type signature
		if ( persistentField.hasAnnotation( OneToOne.class ) || persistentField.hasAnnotation( ManyToOne.class ) ) {
			return persistentField.getType();
		}
		if ( persistentField.hasAnnotation( OneToMany.class ) || persistentField.hasAnnotation( ManyToMany.class ) ) {
			try {
				final SignatureAttribute.TypeArgument target = ( (SignatureAttribute.ClassType) SignatureAttribute.toFieldSignature(
						persistentField.getGenericSignature()
				) ).getTypeArguments()[0];
				return persistentField.getDeclaringClass().getClassPool().get( target.toString() );
			}
			catch (BadBytecode ignore) {
			}
		}
		return null;
	}

	private void handleCompositeField(CtClass managedCtClass, CtField persistentField, CtMethod fieldWriter)
			throws NotFoundException, CannotCompileException {
		if ( !persistentField.hasAnnotation( Embedded.class ) ) {
			return;
		}

		// make sure to add the CompositeOwner interface
		managedCtClass.addInterface( classPool.get( CompositeOwner.class.getName() ) );

		if ( enhancementContext.isCompositeClass( managedCtClass ) ) {
			// if a composite have a embedded field we need to implement the TRACKER_CHANGER_NAME method as well
			MethodWriter.write(
					managedCtClass, "" +
							"public void %1$s(String name) {%n" +
							"  if (%2$s != null) { %2$s.callOwner(\".\" + name) ; }%n}",
					EnhancerConstants.TRACKER_CHANGER_NAME,
					EnhancerConstants.TRACKER_COMPOSITE_FIELD_NAME
			);
		}

		// cleanup previous owner
		fieldWriter.insertBefore(
				String.format(
						"" +
								"if (%1$s != null) { ((%2$s) %1$s).%3$s(\"%1$s\"); }%n",
						persistentField.getName(),
						CompositeTracker.class.getName(),
						EnhancerConstants.TRACKER_COMPOSITE_CLEAR_OWNER
				)
		);

		// trigger track changes
		fieldWriter.insertAfter(
				String.format(
						"" +
								"((%2$s) %1$s).%4$s(\"%1$s\", (%3$s) this);%n" +
								"%5$s(\"%1$s\");",
						persistentField.getName(),
						CompositeTracker.class.getName(),
						CompositeOwner.class.getName(),
						EnhancerConstants.TRACKER_COMPOSITE_SET_OWNER,
						EnhancerConstants.TRACKER_CHANGER_NAME
				)
		);
	}

	protected void enhanceAttributesAccess(
			CtClass managedCtClass,
			IdentityHashMap<String, PersistentAttributeAccessMethods> attributeDescriptorMap) {
		final ConstPool constPool = managedCtClass.getClassFile().getConstPool();

		for ( Object oMethod : managedCtClass.getClassFile().getMethods() ) {
			final MethodInfo methodInfo = (MethodInfo) oMethod;
			final String methodName = methodInfo.getName();

			// skip methods added by enhancement and abstract methods (methods without any code)
			if ( methodName.startsWith( "$$_hibernate_" ) || methodInfo.getCodeAttribute() == null ) {
				continue;
			}

			try {
				final CodeIterator itr = methodInfo.getCodeAttribute().iterator();
				while ( itr.hasNext() ) {
					final int index = itr.next();
					final int op = itr.byteAt( index );
					if ( op != Opcode.PUTFIELD && op != Opcode.GETFIELD ) {
						continue;
					}
					final String fieldName = constPool.getFieldrefName( itr.u16bitAt( index + 1 ) );
					final PersistentAttributeAccessMethods attributeMethods = attributeDescriptorMap.get( fieldName );

					// its not a field we have enhanced for interception, so skip it
					if ( attributeMethods == null ) {
						continue;
					}
					//System.out.printf( "Transforming access to field [%s] from method [%s]%n", fieldName, methodName );
					log.debugf( "Transforming access to field [%s] from method [%s]", fieldName, methodName );

					if ( op == Opcode.GETFIELD ) {
						final int methodIndex = MethodWriter.addMethod( constPool, attributeMethods.getReader() );
						itr.writeByte( Opcode.INVOKESPECIAL, index );
						itr.write16bit( methodIndex, index + 1 );
					}
					else {
						final int methodIndex = MethodWriter.addMethod( constPool, attributeMethods.getWriter() );
						itr.writeByte( Opcode.INVOKESPECIAL, index );
						itr.write16bit( methodIndex, index + 1 );
					}
				}
				methodInfo.getCodeAttribute().setAttribute( MapMaker.make( classPool, methodInfo ) );
			}
			catch (BadBytecode bb) {
				final String msg = String.format(
						"Unable to perform field access transformation in method [%s]",
						methodName
				);
				throw new EnhancementException( msg, bb );
			}
		}
	}

	private static class PersistentAttributeAccessMethods {
		private final CtMethod reader;
		private final CtMethod writer;

		private PersistentAttributeAccessMethods(CtMethod reader, CtMethod writer) {
			this.reader = reader;
			this.writer = writer;
		}

		private CtMethod getReader() {
			return reader;
		}

		private CtMethod getWriter() {
			return writer;
		}
	}

}


File: hibernate-core/src/test/java/org/hibernate/test/bytecode/enhancement/CustomerEnhancerTest.java
/*
 * Hibernate, Relational Persistence for Idiomatic Java
 *
 * License: GNU Lesser General Public License (LGPL), version 2.1 or later.
 * See the lgpl.txt file in the root directory or <http://www.gnu.org/licenses/lgpl-2.1.html>.
 */
package org.hibernate.test.bytecode.enhancement;

import java.lang.reflect.Method;
import java.util.Collection;
import java.util.HashSet;
import java.util.Set;
import java.util.UUID;

import org.hibernate.bytecode.enhance.spi.EnhancerConstants;
import org.hibernate.engine.spi.EntityEntry;
import org.hibernate.engine.spi.ManagedEntity;
import org.hibernate.engine.spi.PersistentAttributeInterceptor;

import org.hibernate.testing.junit4.BaseUnitTestCase;
import org.hibernate.test.bytecode.enhancement.entity.customer.Address;
import org.hibernate.test.bytecode.enhancement.entity.customer.Customer;
import org.hibernate.test.bytecode.enhancement.entity.customer.CustomerInventory;
import org.hibernate.test.bytecode.enhancement.entity.customer.Group;
import org.hibernate.test.bytecode.enhancement.entity.customer.SupplierComponentPK;
import org.hibernate.test.bytecode.enhancement.entity.customer.User;
import org.junit.Test;

import static org.hibernate.testing.junit4.ExtraAssertions.assertTyping;
import static org.junit.Assert.assertEquals;
import static org.junit.Assert.assertNotNull;
import static org.junit.Assert.assertNull;
import static org.junit.Assert.assertSame;
import static org.junit.Assert.assertTrue;

/**
 * @author Steve Ebersole
 */
public class CustomerEnhancerTest extends BaseUnitTestCase {

    @Test
    public void testEnhancement() throws Exception {
        testFor(Customer.class);
    }

    private void testFor(Class entityClassToEnhance) throws Exception {
        ClassLoader cl = new ClassLoader() {
        };

        // just for debugging
        Class<?> addressClass = EnhancerTestUtils.enhanceAndDecompile(Address.class, cl);
        Class<?> customerInventoryClass = EnhancerTestUtils.enhanceAndDecompile(CustomerInventory.class, cl);
        Class<?> supplierComponentPKCtClass = EnhancerTestUtils.enhanceAndDecompile(SupplierComponentPK.class, cl);

        Class<?> entityClass = EnhancerTestUtils.enhanceAndDecompile(entityClassToEnhance, cl);
        Object entityInstance = entityClass.newInstance();
        assertTyping(ManagedEntity.class, entityInstance);

        // call the new methods
        Method setter = entityClass.getMethod(EnhancerConstants.ENTITY_ENTRY_SETTER_NAME, EntityEntry.class);
        Method getter = entityClass.getMethod(EnhancerConstants.ENTITY_ENTRY_GETTER_NAME);
        assertNull(getter.invoke(entityInstance));
        setter.invoke(entityInstance, EnhancerTestUtils.makeEntityEntry());
        assertNotNull(getter.invoke(entityInstance));
        setter.invoke(entityInstance, new Object[]{null});
        assertNull(getter.invoke(entityInstance));

        Method entityInstanceGetter = entityClass.getMethod(EnhancerConstants.ENTITY_INSTANCE_GETTER_NAME);
        assertSame(entityInstance, entityInstanceGetter.invoke(entityInstance));

        Method previousGetter = entityClass.getMethod(EnhancerConstants.PREVIOUS_GETTER_NAME);
        Method previousSetter = entityClass.getMethod(EnhancerConstants.PREVIOUS_SETTER_NAME, ManagedEntity.class);
        previousSetter.invoke(entityInstance, entityInstance);
        assertSame(entityInstance, previousGetter.invoke(entityInstance));

        Method nextGetter = entityClass.getMethod(EnhancerConstants.PREVIOUS_GETTER_NAME);
        Method nextSetter = entityClass.getMethod(EnhancerConstants.PREVIOUS_SETTER_NAME, ManagedEntity.class);
        nextSetter.invoke(entityInstance, entityInstance);
        assertSame(entityInstance, nextGetter.invoke(entityInstance));

        // add an attribute interceptor...
        assertNull(entityClass.getMethod(EnhancerConstants.INTERCEPTOR_GETTER_NAME).invoke(entityInstance));
        entityClass.getMethod("getId").invoke(entityInstance);

        Method interceptorSetter = entityClass.getMethod(EnhancerConstants.INTERCEPTOR_SETTER_NAME, PersistentAttributeInterceptor.class);
        interceptorSetter.invoke(entityInstance, new EnhancerTestUtils.LocalPersistentAttributeInterceptor());
        assertNotNull(entityClass.getMethod(EnhancerConstants.INTERCEPTOR_GETTER_NAME).invoke(entityInstance));

        // dirty checking is unfortunately just printlns for now... just verify the test output
        entityClass.getMethod("getId").invoke(entityInstance);
        entityClass.getMethod("setId", Integer.class).invoke(entityInstance, entityClass.getMethod("getId").invoke(entityInstance));
        entityClass.getMethod("setId", Integer.class).invoke(entityInstance, 1);
        EnhancerTestUtils.checkDirtyTracking(entityInstance, "id");

        entityClass.getMethod("setFirstName", String.class).invoke(entityInstance, "Erik");
        entityClass.getMethod("setLastName", String.class).invoke(entityInstance, "Mykland");

        EnhancerTestUtils.checkDirtyTracking(entityInstance, "id", "firstName", "lastName");
        EnhancerTestUtils.clearDirtyTracking(entityInstance);

        // testing composite object
        Object address = addressClass.newInstance();

        entityClass.getMethod("setAddress", addressClass).invoke(entityInstance, address);
        addressClass.getMethod("setCity", String.class).invoke(address, "Arendal");
        EnhancerTestUtils.checkDirtyTracking(entityInstance, "address", "address.city");
        EnhancerTestUtils.clearDirtyTracking(entityInstance);

        //make sure that new composite instances are cleared
        Object address2 = addressClass.newInstance();
        entityClass.getMethod("setAddress", addressClass).invoke(entityInstance, address2);
        addressClass.getMethod("setStreet1", String.class).invoke(address, "Heggedalveien");
        EnhancerTestUtils.checkDirtyTracking(entityInstance, "address");
    }


    @Test
    public void testBiDirectionalAssociationManagement() throws Exception {
        ClassLoader cl = new ClassLoader() {
        };

        Class<?> userClass = EnhancerTestUtils.enhanceAndDecompile(User.class, cl);
        Class<?> groupClass = EnhancerTestUtils.enhanceAndDecompile(Group.class, cl);
        Class<?> customerClass = EnhancerTestUtils.enhanceAndDecompile(Customer.class, cl);
        Class<?> customerInventoryClass = EnhancerTestUtils.enhanceAndDecompile(CustomerInventory.class, cl);

        Object userInstance = userClass.newInstance();
        assertTyping(ManagedEntity.class, userInstance);

        Object groupInstance = groupClass.newInstance();
        assertTyping(ManagedEntity.class, groupInstance);

        Object customerInstance = customerClass.newInstance();
        assertTyping(ManagedEntity.class, customerInstance);

        Object customerInventoryInstance = customerInventoryClass.newInstance();
        assertTyping(ManagedEntity.class, customerInventoryInstance);

        Method interceptorSetter = userClass.getMethod(EnhancerConstants.INTERCEPTOR_SETTER_NAME, PersistentAttributeInterceptor.class);
        interceptorSetter.invoke(userInstance, new EnhancerTestUtils.LocalPersistentAttributeInterceptor());

        /* --- @OneToOne */

        userClass.getMethod("setLogin", String.class).invoke(userInstance, UUID.randomUUID().toString());

        customerClass.getMethod("setUser", userClass).invoke(customerInstance, userInstance);
        assertEquals(customerInstance, userClass.getMethod("getCustomer").invoke(userInstance));

        // check dirty tracking is set automatically with bi-directional association management
        EnhancerTestUtils.checkDirtyTracking(userInstance, "login", "customer");

        Object anotherUser = userClass.newInstance();
        userClass.getMethod("setLogin", String.class).invoke(anotherUser, UUID.randomUUID().toString());

        customerClass.getMethod("setUser", userClass).invoke(customerInstance, anotherUser);
        assertEquals(null, userClass.getMethod("getCustomer").invoke(userInstance));
        assertEquals(customerInstance, userClass.getMethod("getCustomer").invoke(anotherUser));

        userClass.getMethod("setCustomer", customerClass).invoke(userInstance, customerClass.newInstance());
        assertEquals(userInstance, customerClass.getMethod("getUser").invoke(userClass.getMethod("getCustomer").invoke(userInstance)));

        /* --- @OneToMany @ManyToOne */

        assertTrue(((Collection<?>) customerClass.getMethod("getInventories").invoke(customerInstance)).isEmpty());
        customerInventoryClass.getMethod("setCustomer", customerClass).invoke(customerInventoryInstance, customerInstance);

        Collection<?> inventories = (Collection < ?>) customerClass.getMethod("getInventories").invoke(customerInstance);
        assertTrue(inventories.size() == 1);
        assertTrue(inventories.contains(customerInventoryInstance));

        Object anotherCustomer = customerClass.newInstance();
        customerInventoryClass.getMethod("setCustomer", customerClass).invoke(customerInventoryInstance, anotherCustomer);
        assertTrue(((Collection<?>) customerClass.getMethod("getInventories").invoke(customerInstance)).isEmpty());

        customerClass.getMethod("addInventory", customerInventoryClass).invoke(customerInstance, customerInventoryInstance);
        assertTrue(customerInventoryClass.getMethod("getCustomer").invoke(customerInventoryInstance) == customerInstance);

        inventories = (Collection < ?>) customerClass.getMethod("getInventories").invoke(customerInstance);
        assertTrue(inventories.size() == 1);

        customerClass.getMethod("addInventory", customerInventoryClass).invoke(customerInstance, customerInventoryClass.newInstance());
        assertTrue(((Collection<?>) customerClass.getMethod("getInventories").invoke(customerInstance)).size() == 2);

        /* --- @ManyToMany */

        Object anotherGroup = groupClass.newInstance();
        userClass.getMethod("addGroup", groupClass).invoke(userInstance, groupInstance);
        userClass.getMethod("addGroup", groupClass).invoke(userInstance, anotherGroup);
        userClass.getMethod("addGroup", groupClass).invoke(anotherUser, groupInstance);

        assertTrue(((Collection<?>) groupClass.getMethod("getUsers").invoke(groupInstance)).size() == 2);

        groupClass.getMethod("setUsers", Set.class).invoke(groupInstance, new HashSet());
        assertTrue(((Collection<?>) userClass.getMethod("getGroups").invoke(userInstance)).size() == 1);

    }

}


File: hibernate-core/src/test/java/org/hibernate/test/bytecode/enhancement/EnhancerTest.java
/*
 * Hibernate, Relational Persistence for Idiomatic Java
 *
 * License: GNU Lesser General Public License (LGPL), version 2.1 or later.
 * See the lgpl.txt file in the root directory or <http://www.gnu.org/licenses/lgpl-2.1.html>.
 */
package org.hibernate.test.bytecode.enhancement;

import java.lang.reflect.Method;
import java.util.ArrayList;
import java.util.HashSet;
import java.util.List;
import java.util.Set;

import org.hibernate.bytecode.enhance.spi.EnhancerConstants;
import org.hibernate.engine.spi.EntityEntry;
import org.hibernate.engine.spi.ManagedEntity;

import org.hibernate.testing.junit4.BaseUnitTestCase;
import org.hibernate.test.bytecode.enhancement.entity.Address;
import org.hibernate.test.bytecode.enhancement.entity.Country;
import org.hibernate.test.bytecode.enhancement.entity.SimpleEntity;
import org.hibernate.test.bytecode.enhancement.entity.SubEntity;
import org.junit.Test;

import static org.hibernate.testing.junit4.ExtraAssertions.assertTyping;
import static org.junit.Assert.assertNotNull;
import static org.junit.Assert.assertNull;
import static org.junit.Assert.assertSame;

/**
 * @author Steve Ebersole
 */
public class EnhancerTest extends BaseUnitTestCase {

    @Test
    public void testEnhancement() throws Exception {
        testFor(SimpleEntity.class);
        testFor(SubEntity.class);
    }

    private void testFor(Class<?> entityClassToEnhance) throws Exception {
        ClassLoader cl = new ClassLoader() {};
        Class<?> entityClass = EnhancerTestUtils.enhanceAndDecompile(entityClassToEnhance, cl);
        Object entityInstance = entityClass.newInstance();

        assertTyping(ManagedEntity.class, entityInstance);

        // call the new methods
        Method setter = entityClass.getMethod(EnhancerConstants.ENTITY_ENTRY_SETTER_NAME, EntityEntry.class);
        Method getter = entityClass.getMethod(EnhancerConstants.ENTITY_ENTRY_GETTER_NAME);

        assertNull(getter.invoke(entityInstance));
        setter.invoke(entityInstance, EnhancerTestUtils.makeEntityEntry());
        assertNotNull(getter.invoke(entityInstance));
        setter.invoke(entityInstance, new Object[] { null } );
        assertNull(getter.invoke(entityInstance));

        Method entityInstanceGetter = entityClass.getMethod(EnhancerConstants.ENTITY_INSTANCE_GETTER_NAME);
        assertSame(entityInstance, entityInstanceGetter.invoke(entityInstance));

        Method previousGetter = entityClass.getMethod(EnhancerConstants.PREVIOUS_GETTER_NAME);
        Method previousSetter = entityClass.getMethod(EnhancerConstants.PREVIOUS_SETTER_NAME, ManagedEntity.class);
        previousSetter.invoke(entityInstance, entityInstance);
        assertSame(entityInstance, previousGetter.invoke(entityInstance));

        Method nextGetter = entityClass.getMethod(EnhancerConstants.PREVIOUS_GETTER_NAME);
        Method nextSetter = entityClass.getMethod(EnhancerConstants.PREVIOUS_SETTER_NAME, ManagedEntity.class);
        nextSetter.invoke( entityInstance, entityInstance );
        assertSame( entityInstance, nextGetter.invoke( entityInstance ) );

        entityClass.getMethod("getId").invoke(entityInstance);
        entityClass.getMethod("setId", Long.class).invoke(entityInstance, entityClass.getMethod("getId").invoke(entityInstance));
        entityClass.getMethod("setId", Long.class).invoke(entityInstance, 1L);
        EnhancerTestUtils.checkDirtyTracking(entityInstance, "id");

        entityClass.getMethod("isActive").invoke(entityInstance);
        entityClass.getMethod("setActive", boolean.class).invoke(entityInstance, entityClass.getMethod("isActive").invoke(entityInstance));
        entityClass.getMethod("setActive", boolean.class).invoke(entityInstance, true);

        entityClass.getMethod("getSomeNumber").invoke(entityInstance);
        entityClass.getMethod("setSomeNumber", long.class).invoke(entityInstance, entityClass.getMethod("getSomeNumber").invoke(entityInstance));
        entityClass.getMethod("setSomeNumber", long.class).invoke(entityInstance, 1L);

        EnhancerTestUtils.checkDirtyTracking(entityInstance, "id", "active", "someNumber");
        EnhancerTestUtils.clearDirtyTracking(entityInstance);

        // setting the same value should not make it dirty
        entityClass.getMethod("setSomeNumber", long.class).invoke(entityInstance, 1L);
        EnhancerTestUtils.checkDirtyTracking(entityInstance);

        if(entityClassToEnhance.getName().endsWith(SimpleEntity.class.getSimpleName())) {
            cl = new ClassLoader() {};

            Class<?> addressClass = EnhancerTestUtils.enhanceAndDecompile(Address.class, cl);
            Class<?> countryClass = EnhancerTestUtils.enhanceAndDecompile(Country.class, cl);

            entityClass = EnhancerTestUtils.enhanceAndDecompile(entityClassToEnhance, cl);
            entityInstance = entityClass.newInstance();

            List<String> strings = new ArrayList<String>();
            strings.add("FooBar");
            entityClass.getMethod("setSomeStrings", List.class).invoke(entityInstance, strings);
            EnhancerTestUtils.checkDirtyTracking(entityInstance, "someStrings");
            EnhancerTestUtils.clearDirtyTracking(entityInstance);

            strings.add("JADA!");
            EnhancerTestUtils.checkDirtyTracking(entityInstance, "someStrings");
            EnhancerTestUtils.clearDirtyTracking(entityInstance);

            // this should not set the entity to dirty
            Set<Integer> intSet = new HashSet<Integer>();
            intSet.add(42);
            entityClass.getMethod("setSomeInts", Set.class).invoke(entityInstance, intSet);
            EnhancerTestUtils.checkDirtyTracking(entityInstance);

            // testing composite object
            Object address = addressClass.newInstance();
            Object country = countryClass.newInstance();

            entityClass.getMethod("setAddress", addressClass).invoke(entityInstance, address);
            addressClass.getMethod("setCity", String.class).invoke(address, "Arendal");
            EnhancerTestUtils.checkDirtyTracking(entityInstance, "address", "address.city");

            entityClass.getMethod(EnhancerConstants.TRACKER_CLEAR_NAME).invoke(entityInstance);

            // make sure that new composite instances are cleared
            Object address2 = addressClass.newInstance();

            entityClass.getMethod("setAddress", addressClass).invoke(entityInstance, address2);
            addressClass.getMethod("setStreet1", String.class).invoke(address, "Heggedalveien");
            EnhancerTestUtils.checkDirtyTracking(entityInstance, "address");

            addressClass.getMethod("setCountry", countryClass).invoke(address2, country);
            countryClass.getMethod("setName", String.class).invoke(country, "Norway");
            EnhancerTestUtils.checkDirtyTracking(entityInstance, "address", "address.country", "address.country.name");
        }
    }

}


File: hibernate-core/src/test/java/org/hibernate/test/bytecode/enhancement/EnhancerTestUtils.java
/*
 * Hibernate, Relational Persistence for Idiomatic Java
 *
 * License: GNU Lesser General Public License (LGPL), version 2.1 or later.
 * See the lgpl.txt file in the root directory or <http://www.gnu.org/licenses/lgpl-2.1.html>.
 */
package org.hibernate.test.bytecode.enhancement;

import java.io.ByteArrayInputStream;
import java.io.File;
import java.io.IOException;
import java.util.Arrays;
import java.util.Collections;
import java.util.HashSet;
import java.util.Set;
import javax.tools.JavaCompiler;
import javax.tools.JavaFileObject;
import javax.tools.StandardJavaFileManager;
import javax.tools.StandardLocation;
import javax.tools.ToolProvider;

import javassist.ClassPool;
import javassist.CtClass;
import javassist.LoaderClassPath;

import org.hibernate.LockMode;
import org.hibernate.bytecode.enhance.spi.DefaultEnhancementContext;
import org.hibernate.bytecode.enhance.spi.EnhancementContext;
import org.hibernate.bytecode.enhance.spi.Enhancer;
import org.hibernate.bytecode.enhance.spi.EnhancerConstants;
import org.hibernate.engine.internal.MutableEntityEntryFactory;
import org.hibernate.engine.spi.CompositeOwner;
import org.hibernate.engine.spi.CompositeTracker;
import org.hibernate.engine.spi.EntityEntry;
import org.hibernate.engine.spi.ManagedEntity;
import org.hibernate.engine.spi.PersistentAttributeInterceptor;
import org.hibernate.engine.spi.SelfDirtinessTracker;
import org.hibernate.engine.spi.Status;
import org.hibernate.internal.CoreLogging;
import org.hibernate.internal.CoreMessageLogger;

import org.hibernate.testing.junit4.BaseUnitTestCase;

import com.sun.tools.classfile.ConstantPoolException;
import com.sun.tools.javap.JavapTask;

import static org.junit.Assert.assertEquals;
import static org.junit.Assert.assertFalse;
import static org.junit.Assert.assertNotNull;
import static org.junit.Assert.assertNull;
import static org.junit.Assert.assertTrue;

/**
 * utility class to use in bytecode enhancement tests
 *
 * @author Steve Ebersole
 */
public abstract class EnhancerTestUtils extends BaseUnitTestCase {

	private static EnhancementContext enhancementContext = new DefaultEnhancementContext();

	private static String workingDir = System.getProperty( "java.io.tmpdir" );

	private static final CoreMessageLogger log = CoreLogging.messageLogger( EnhancerTestUtils.class );

	/**
	 * method that performs the enhancement of a class
	 * also checks the signature of enhanced entities methods using 'javap' decompiler
	 */
	static Class<?> enhanceAndDecompile(Class<?> classToEnhance, ClassLoader cl) throws Exception {
		CtClass entityCtClass = generateCtClassForAnEntity( classToEnhance );

		byte[] original = entityCtClass.toBytecode();
		byte[] enhanced = new Enhancer( enhancementContext ).enhance( entityCtClass.getName(), original );
		assertFalse( "entity was not enhanced", Arrays.equals( original, enhanced ) );
		log.infof( "enhanced entity [%s]", entityCtClass.getName() );

		ClassPool cp = new ClassPool( false );
		cp.appendClassPath( new LoaderClassPath( cl ) );
		CtClass enhancedCtClass = cp.makeClass( new ByteArrayInputStream( enhanced ) );

		enhancedCtClass.debugWriteFile( workingDir );
		decompileDumpedClass( classToEnhance.getName() );

		Class<?> enhancedClass = enhancedCtClass.toClass( cl, EnhancerTestUtils.class.getProtectionDomain() );
		assertNotNull( enhancedClass );
		return enhancedClass;
	}

	private static void decompileDumpedClass(String className) {
		try {
			JavaCompiler compiler = ToolProvider.getSystemJavaCompiler();
			StandardJavaFileManager fileManager = compiler.getStandardFileManager( null, null, null );
			fileManager.setLocation(
					StandardLocation.CLASS_OUTPUT,
					Collections.singletonList( new File( workingDir ) )
			);

			JavapTask javapTask = new JavapTask();
			for ( JavaFileObject jfo : fileManager.getJavaFileObjects(
					workingDir + File.separator + getFilenameForClassName(
							className
					)
			) ) {
				try {
					Set<String> interfaceNames = new HashSet<String>();
					Set<String> fieldNames = new HashSet<String>();
					Set<String> methodNames = new HashSet<String>();

					JavapTask.ClassFileInfo info = javapTask.read( jfo );

					log.infof( "decompiled class [%s]", info.cf.getName() );

					for ( int i : info.cf.interfaces ) {
						interfaceNames.add( info.cf.constant_pool.getClassInfo( i ).getName() );
						log.debugf( "declared iFace  = ", info.cf.constant_pool.getClassInfo( i ).getName() );
					}
					for ( com.sun.tools.classfile.Field f : info.cf.fields ) {
						fieldNames.add( f.getName( info.cf.constant_pool ) );
						log.debugf( "declared field  = ", f.getName( info.cf.constant_pool ) );
					}
					for ( com.sun.tools.classfile.Method m : info.cf.methods ) {
						methodNames.add( m.getName( info.cf.constant_pool ) );
						log.debugf( "declared method = ", m.getName( info.cf.constant_pool ) );
					}

					// checks signature against known interfaces
					if ( interfaceNames.contains( PersistentAttributeInterceptor.class.getName() ) ) {
						assertTrue( fieldNames.contains( EnhancerConstants.INTERCEPTOR_FIELD_NAME ) );
						assertTrue( methodNames.contains( EnhancerConstants.INTERCEPTOR_GETTER_NAME ) );
						assertTrue( methodNames.contains( EnhancerConstants.INTERCEPTOR_SETTER_NAME ) );
					}
					if ( interfaceNames.contains( ManagedEntity.class.getName() ) ) {
						assertTrue( methodNames.contains( EnhancerConstants.ENTITY_INSTANCE_GETTER_NAME ) );

						assertTrue( fieldNames.contains( EnhancerConstants.ENTITY_ENTRY_FIELD_NAME ) );
						assertTrue( methodNames.contains( EnhancerConstants.ENTITY_ENTRY_GETTER_NAME ) );
						assertTrue( methodNames.contains( EnhancerConstants.ENTITY_ENTRY_SETTER_NAME ) );

						assertTrue( fieldNames.contains( EnhancerConstants.PREVIOUS_FIELD_NAME ) );
						assertTrue( methodNames.contains( EnhancerConstants.PREVIOUS_GETTER_NAME ) );
						assertTrue( methodNames.contains( EnhancerConstants.PREVIOUS_SETTER_NAME ) );

						assertTrue( fieldNames.contains( EnhancerConstants.NEXT_FIELD_NAME ) );
						assertTrue( methodNames.contains( EnhancerConstants.NEXT_GETTER_NAME ) );
						assertTrue( methodNames.contains( EnhancerConstants.NEXT_SETTER_NAME ) );
					}
					if ( interfaceNames.contains( SelfDirtinessTracker.class.getName() ) ) {
						assertTrue( fieldNames.contains( EnhancerConstants.TRACKER_FIELD_NAME ) );
						assertTrue( methodNames.contains( EnhancerConstants.TRACKER_GET_NAME ) );
						assertTrue( methodNames.contains( EnhancerConstants.TRACKER_CLEAR_NAME ) );
						assertTrue( methodNames.contains( EnhancerConstants.TRACKER_HAS_CHANGED_NAME ) );
					}
					if ( interfaceNames.contains( CompositeTracker.class.getName() ) ) {
						assertTrue( fieldNames.contains( EnhancerConstants.TRACKER_COMPOSITE_FIELD_NAME ) );
						assertTrue( methodNames.contains( EnhancerConstants.TRACKER_COMPOSITE_SET_OWNER ) );
						assertTrue( methodNames.contains( EnhancerConstants.TRACKER_COMPOSITE_SET_OWNER ) );
					}
					if ( interfaceNames.contains( CompositeOwner.class.getName() ) ) {
						assertTrue( fieldNames.contains( EnhancerConstants.TRACKER_CHANGER_NAME ) );
						assertTrue( methodNames.contains( EnhancerConstants.TRACKER_CHANGER_NAME ) );
					}
				}
				catch (ConstantPoolException e) {
					e.printStackTrace();
				}
			}
		}
		catch (IOException ioe) {
			assertNull( "Failed to open class file", ioe );
		}
		catch (RuntimeException re) {
			log.warnf( re, "WARNING: UNABLE DECOMPILE DUE TO %s", re.getMessage() );
		}
	}

	private static CtClass generateCtClassForAnEntity(Class<?> entityClassToEnhance) throws Exception {
		ClassPool cp = new ClassPool( false );
		return cp.makeClass(
				EnhancerTestUtils.class.getClassLoader().getResourceAsStream(
						getFilenameForClassName(
								entityClassToEnhance.getName()
						)
				)
		);
	}

	private static String getFilenameForClassName(String className) {
		return className.replace( '.', File.separatorChar ) + JavaFileObject.Kind.CLASS.extension;
	}

	/**
	 * clears the dirty set for an entity
	 */
	public static void clearDirtyTracking(Object entityInstance) {
		( (SelfDirtinessTracker) entityInstance ).$$_hibernate_clearDirtyAttributes();
	}

	/**
	 * compares the dirty fields of an entity with a set of expected values
	 */
	public static void checkDirtyTracking(Object entityInstance, String... dirtyFields) {
		final SelfDirtinessTracker selfDirtinessTracker = (SelfDirtinessTracker) entityInstance;
		assertEquals( dirtyFields.length > 0, selfDirtinessTracker.$$_hibernate_hasDirtyAttributes() );
		String[] tracked = selfDirtinessTracker.$$_hibernate_getDirtyAttributes();
		assertEquals( dirtyFields.length, tracked.length );
		assertTrue( Arrays.asList( tracked ).containsAll( Arrays.asList( dirtyFields ) ) );
	}

	static EntityEntry makeEntityEntry() {
		return MutableEntityEntryFactory.INSTANCE.createEntityEntry(
				Status.MANAGED,
				null,
				null,
				1,
				null,
				LockMode.NONE,
				false,
				null,
				false,
				false,
				null
		);
	}

	public static class LocalPersistentAttributeInterceptor implements PersistentAttributeInterceptor {

		@Override
		public boolean readBoolean(Object obj, String name, boolean oldValue) {
			log.infof( "Reading boolean [%s]", name );
			return oldValue;
		}

		@Override
		public boolean writeBoolean(Object obj, String name, boolean oldValue, boolean newValue) {
			log.infof( "Writing boolean []", name );
			return newValue;
		}

		@Override
		public byte readByte(Object obj, String name, byte oldValue) {
			log.infof( "Reading byte [%s]", name );
			return oldValue;
		}

		@Override
		public byte writeByte(Object obj, String name, byte oldValue, byte newValue) {
			log.infof( "Writing byte [%s]", name );
			return newValue;
		}

		@Override
		public char readChar(Object obj, String name, char oldValue) {
			log.infof( "Reading char [%s]", name );
			return oldValue;
		}

		@Override
		public char writeChar(Object obj, String name, char oldValue, char newValue) {
			log.infof( "Writing char [%s]", name );
			return newValue;
		}

		@Override
		public short readShort(Object obj, String name, short oldValue) {
			log.infof( "Reading short [%s]", name );
			return oldValue;
		}

		@Override
		public short writeShort(Object obj, String name, short oldValue, short newValue) {
			log.infof( "Writing short [%s]", name );
			return newValue;
		}

		@Override
		public int readInt(Object obj, String name, int oldValue) {
			log.infof( "Reading int [%s]", name );
			return oldValue;
		}

		@Override
		public int writeInt(Object obj, String name, int oldValue, int newValue) {
			log.infof( "Writing int [%s]", name );
			return newValue;
		}

		@Override
		public float readFloat(Object obj, String name, float oldValue) {
			log.infof( "Reading float [%s]", name );
			return oldValue;
		}

		@Override
		public float writeFloat(Object obj, String name, float oldValue, float newValue) {
			log.infof( "Writing float [%s]", name );
			return newValue;
		}

		@Override
		public double readDouble(Object obj, String name, double oldValue) {
			log.infof( "Reading double [%s]", name );
			return oldValue;
		}

		@Override
		public double writeDouble(Object obj, String name, double oldValue, double newValue) {
			log.infof( "Writing double [%s]", name );
			return newValue;
		}

		@Override
		public long readLong(Object obj, String name, long oldValue) {
			log.infof( "Reading long [%s]", name );
			return oldValue;
		}

		@Override
		public long writeLong(Object obj, String name, long oldValue, long newValue) {
			log.infof( "Writing long [%s]", name );
			return newValue;
		}

		@Override
		public Object readObject(Object obj, String name, Object oldValue) {
			log.infof( "Reading Object [%s]", name );
			return oldValue;
		}

		@Override
		public Object writeObject(Object obj, String name, Object oldValue, Object newValue) {
			log.infof( "Writing Object [%s]", name );
			return newValue;
		}
	}

}


File: hibernate-core/src/test/java/org/hibernate/test/bytecode/enhancement/entity/Address.java
/*
 * Hibernate, Relational Persistence for Idiomatic Java
 *
 * License: GNU Lesser General Public License (LGPL), version 2.1 or later.
 * See the lgpl.txt file in the root directory or <http://www.gnu.org/licenses/lgpl-2.1.html>.
 */
package org.hibernate.test.bytecode.enhancement.entity;

import javax.persistence.Embeddable;
import javax.persistence.Embedded;
import java.io.Serializable;

/**
 * @author <a href="mailto:stale.pedersen@jboss.org">Ståle W. Pedersen</a>
 */
@Embeddable
public class Address implements Serializable {

    private String street1;
    private String street2;
    private String city;
    private String state;

    @Embedded
    private Country country;
    private String zip;
    private String phone;

    public Address() {
    }

    public String getStreet1() {
        return street1;
    }

    public void setStreet1(String street1) {
        this.street1 = street1;
    }

    public String getStreet2() {
        return street2;
    }

    public void setStreet2(String street2) {
        this.street2 = street2;
    }

    public String getCity() {
        return city;
    }

    public void setCity(String city) {
        this.city = city;
    }

    public String getState() {
        return state;
    }

    public void setState(String state) {
        this.state = state;
    }

    public Country getCountry() {
        return country;
    }

    public void setCountry(Country country) {
        this.country = country;
    }

    public String getZip() {
        return zip;
    }

    public void setZip(String zip) {
        this.zip = zip;
    }

    public String getPhone() {
        return phone;
    }

    public void setPhone(String phone) {
        this.phone = phone;
    }

}


File: hibernate-core/src/test/java/org/hibernate/test/bytecode/enhancement/entity/SampleEntity.java
/*
 * Hibernate, Relational Persistence for Idiomatic Java
 *
 * License: GNU Lesser General Public License (LGPL), version 2.1 or later.
 * See the lgpl.txt file in the root directory or <http://www.gnu.org/licenses/lgpl-2.1.html>.
 */
package org.hibernate.test.bytecode.enhancement.entity;

import javax.persistence.Id;
import javax.persistence.Transient;

import org.hibernate.engine.spi.EntityEntry;
import org.hibernate.engine.spi.ManagedEntity;
import org.hibernate.engine.spi.PersistentAttributeInterceptable;
import org.hibernate.engine.spi.PersistentAttributeInterceptor;

/**
 * @author Steve Ebersole
 */
public class SampleEntity implements ManagedEntity, PersistentAttributeInterceptable {
	@Transient
	private transient EntityEntry entityEntry;
	@Transient
	private transient ManagedEntity previous;
	@Transient
	private transient ManagedEntity next;
	@Transient
	private transient PersistentAttributeInterceptor interceptor;

	private Long id;
	private String name;

	@Id
	public Long getId() {
		return hibernate_read_id();
	}

	public void setId(Long id) {
		hibernate_write_id( id );
	}

	public String getName() {
		return hibernate_read_name();
	}

	public void setName(String name) {
		hibernate_write_name( name );
	}

	private Long hibernate_read_id() {
		if ( $$_hibernate_getInterceptor() != null ) {
			this.id = (Long) $$_hibernate_getInterceptor().readObject( this, "id", this.id );
		}
		return id;
	}

	private void hibernate_write_id(Long id) {
		Long localVar = id;
		if ( $$_hibernate_getInterceptor() != null ) {
			localVar = (Long) $$_hibernate_getInterceptor().writeObject( this, "id", this.id, id );
		}
		this.id = localVar;
	}

	private String hibernate_read_name() {
		if ( $$_hibernate_getInterceptor() != null ) {
			this.name = (String) $$_hibernate_getInterceptor().readObject( this, "name", this.name );
		}
		return name;
	}

	private void hibernate_write_name(String name) {
		String localName = name;
		if ( $$_hibernate_getInterceptor() != null ) {
			localName = (String) $$_hibernate_getInterceptor().writeObject( this, "name", this.name, name );
		}
		this.name = localName;
	}

	@Override
	public Object $$_hibernate_getEntityInstance() {
		return this;
	}

	@Override
	public EntityEntry $$_hibernate_getEntityEntry() {
		return entityEntry;
	}

	@Override
	public void $$_hibernate_setEntityEntry(EntityEntry entityEntry) {
		this.entityEntry = entityEntry;
	}

	@Override
	public ManagedEntity $$_hibernate_getNextManagedEntity() {
		return next;
	}

	@Override
	public void $$_hibernate_setNextManagedEntity(ManagedEntity next) {
		this.next = next;
	}

	@Override
	public ManagedEntity $$_hibernate_getPreviousManagedEntity() {
		return previous;
	}

	@Override
	public void $$_hibernate_setPreviousManagedEntity(ManagedEntity previous) {
		this.previous = previous;
	}

	@Override
	public PersistentAttributeInterceptor $$_hibernate_getInterceptor() {
		return interceptor;
	}

	@Override
	public void $$_hibernate_setInterceptor(PersistentAttributeInterceptor interceptor) {
		this.interceptor = interceptor;
	}
}


File: hibernate-core/src/test/java/org/hibernate/test/bytecode/enhancement/entity/customer/Address.java
/*
 * Hibernate, Relational Persistence for Idiomatic Java
 *
 * License: GNU Lesser General Public License (LGPL), version 2.1 or later.
 * See the lgpl.txt file in the root directory or <http://www.gnu.org/licenses/lgpl-2.1.html>.
 */package org.hibernate.test.bytecode.enhancement.entity.customer;

import javax.persistence.Embeddable;
import java.io.Serializable;

/**
 * @author <a href="mailto:stale.pedersen@jboss.org">Ståle W. Pedersen</a>
 */
@Embeddable
public class Address implements Serializable {
    private String street1;
    private String street2;
    private String city;
    private String state;
    private String country;
    private String zip;
    private String phone;

    public Address() {
    }
    public Address(String street1, String street2, String city, String state,
                   String country, String zip, String phone) {
        this.street1 = street1;
        this.street2 = street2;
        this.city    = city;
        this.state   = state;
        this.country = country;
        setZip(zip);
        setPhone(phone);
    }

    public String toString() {
        return street1 + "\n" + street2 + "\n" + city + "," + state + " " + zip + "\n" + phone;
    }

    public String getStreet1() {
        return street1;
    }

    public void setStreet1(String street1) {
        this.street1 = street1;
    }

    public String getStreet2() {
        return street2;
    }

    public void setStreet2(String street2) {
        this.street2 = street2;
    }

    public String getCity() {
        return city;
    }

    public void setCity(String city) {
        this.city = city;
    }

    public String getState() {
        return state;
    }

    public void setState(String state) {
        this.state = state;
    }

    public String getCountry() {
        return country;
    }

    public void setCountry(String country) {
        this.country = country;
    }

    public String getZip() {
        return zip;
    }

    public void setZip(String zip) {
        assertNumeric(zip, "Non-numeric zip ");
        this.zip = zip;

    }

    public String getPhone() {
        return phone;
    }

    public void setPhone(String phone) {
        assertNumeric(zip, "Non-numeric phone ");
        this.phone = phone;
    }

    void assertNumeric(String s, String error) {
        for (int i=0; i<s.length(); i++) {
            if (!Character.isDigit(s.charAt(i))) {
                throw new IllegalArgumentException(error + s);
            }
        }
    }
}


File: hibernate-core/src/test/java/org/hibernate/test/bytecode/enhancement/entity/customer/Customer.java
/*
 * Hibernate, Relational Persistence for Idiomatic Java
 *
 * License: GNU Lesser General Public License (LGPL), version 2.1 or later.
 * See the lgpl.txt file in the root directory or <http://www.gnu.org/licenses/lgpl-2.1.html>.
 */
package org.hibernate.test.bytecode.enhancement.entity.customer;

import javax.persistence.AttributeOverride;
import javax.persistence.AttributeOverrides;
import javax.persistence.CascadeType;
import javax.persistence.Column;
import javax.persistence.Embedded;
import javax.persistence.Entity;
import javax.persistence.FetchType;
import javax.persistence.Id;
import javax.persistence.OneToMany;
import javax.persistence.OneToOne;
import javax.persistence.Table;
import javax.persistence.Temporal;
import javax.persistence.TemporalType;
import javax.persistence.Version;
import java.math.BigDecimal;
import java.util.ArrayList;
import java.util.Calendar;
import java.util.List;

/**
 * @author <a href="mailto:stale.pedersen@jboss.org">Ståle W. Pedersen</a>
 */
@Entity
@Table(name="O_CUSTOMER")
public class Customer {
    public static final String QUERY_ALL = "Customer.selectAll";
    public static final String QUERY_COUNT = "Customer.count";
    public static final String QUERY_BY_CREDIT = "Customer.selectByCreditLimit";

    public static final String BAD_CREDIT = "BC";

    @Id
    @Column(name="C_ID")
    private int id;

    @OneToOne
    private User user;

    @Column(name="C_FIRST")
    private String firstName;

    @Column(name="C_LAST")
    private String lastName;

    @Column(name="C_CONTACT")
    private String contact;

    @Column(name="C_CREDIT")
    private String credit;

    @Column(name="C_CREDIT_LIMIT")
    private BigDecimal creditLimit;

    @Column(name="C_SINCE")
    @Temporal(TemporalType.DATE)
    private Calendar since;

    @Column(name="C_BALANCE")
    private BigDecimal balance;

    @Column(name="C_YTD_PAYMENT")
    private BigDecimal ytdPayment;

    @OneToMany(mappedBy="customer", cascade= CascadeType.ALL, fetch= FetchType.EAGER)
    private List<CustomerInventory> customerInventories;

    @Embedded
    @AttributeOverrides(
            {@AttributeOverride(name="street1",column=@Column(name="C_STREET1")),
                    @AttributeOverride(name="street2",column=@Column(name="C_STREET2")),
                    @AttributeOverride(name="city",   column=@Column(name="C_CITY")),
                    @AttributeOverride(name="state",  column=@Column(name="C_STATE")),
                    @AttributeOverride(name="country",column=@Column(name="C_COUNTRY")),
                    @AttributeOverride(name="zip",    column=@Column(name="C_ZIP")),
                    @AttributeOverride(name="phone",  column=@Column(name="C_PHONE"))})
    private Address       address;

    @Version
    @Column(name = "C_VERSION")
    private int version;

    public Customer() {
    }

    public Customer(String first, String last, Address address,
                    String contact, String credit, BigDecimal creditLimit,
                    BigDecimal balance, BigDecimal YtdPayment) {

        this.firstName   = first;
        this.lastName    = last;
        this.address     = address;
        this.contact     = contact;
        this.since       = Calendar.getInstance();
        this.credit      = credit;
        this.creditLimit = creditLimit;
        this.balance     = balance;
        this.ytdPayment  = YtdPayment;
    }

    public Integer getId() {
        return id;
    }

    public void setId(Integer customerId) {
        this.id = customerId;
    }

    public String getFirstName() {
        return firstName;
    }

    public void setFirstName(String firstName) {
        this.firstName = firstName;
    }

    public String getLastName() {
        return lastName;
    }

    public void setLastName(String lastName) {
        this.lastName = lastName;
    }

    public Address getAddress() {
        return address;
    }

    public void setAddress(Address address) {
        this.address = address;
    }

    public String getContact() {
        return contact;
    }

    public void setContact(String contact) {
        this.contact = contact;
    }

    public String getCredit() {
        return credit;
    }

    public void setCredit(String credit) {
        this.credit = credit;
    }

    public BigDecimal getCreditLimit() {
        return creditLimit;
    }

    public void setCreditLimit(BigDecimal creditLimit) {
        this.creditLimit = creditLimit;
    }

    public Calendar getSince() {
        return since;
    }

    public void setSince(Calendar since) {
        this.since = since;
    }

    public BigDecimal getBalance() {
        return balance;
    }

    public void setBalance(BigDecimal balance) {
        this.balance = balance;
    }

    public void changeBalance(BigDecimal change) {
        setBalance(balance.add(change).setScale(2, BigDecimal.ROUND_DOWN));
    }

    public BigDecimal getYtdPayment() {
        return ytdPayment;
    }

    public void setYtdPayment(BigDecimal ytdPayment) {
        this.ytdPayment = ytdPayment;
    }

    public List<CustomerInventory> getInventories() {
        if (customerInventories == null){
            customerInventories = new ArrayList<CustomerInventory>();
        }
        return customerInventories;
    }

    public User getUser() {
        return user;
    }

    public void setUser(User user) {
        this.user = user;
    }

    public void addInventory(CustomerInventory inventory) {
        List<CustomerInventory> list = getInventories();
        list.add(inventory);
        customerInventories = list;
    }

    public CustomerInventory addInventory(String item, int quantity,
                                          BigDecimal totalValue) {

        CustomerInventory inventory = new CustomerInventory(this, item,
                quantity, totalValue);
        getInventories().add(inventory);
        return inventory;
    }

    public int getVersion() {
        return version;
    }

    public boolean hasSufficientCredit(BigDecimal amount) {
        return !BAD_CREDIT.equals(getCredit())
                && creditLimit != null
                && creditLimit.compareTo(amount) >= 0;
    }

    @Override
    public boolean equals(Object o) {
        if (this == o)
            return true;
        if (o == null || getClass() != o.getClass())
            return false;
        return id == ((Customer) o).id;
    }

    @Override
    public int hashCode() {
        return new Integer(id).hashCode();
    }

    @Override
    public String toString() {
        return this.getFirstName() + " " + this.getLastName();
    }
}


File: hibernate-core/src/test/java/org/hibernate/test/bytecode/enhancement/entity/customer/CustomerInventory.java
/*
 * Hibernate, Relational Persistence for Idiomatic Java
 *
 * License: GNU Lesser General Public License (LGPL), version 2.1 or later.
 * See the lgpl.txt file in the root directory or <http://www.gnu.org/licenses/lgpl-2.1.html>.
 */
package org.hibernate.test.bytecode.enhancement.entity.customer;

/**
 * @author <a href="mailto:stale.pedersen@jboss.org">Ståle W. Pedersen</a>
 */

import java.io.Serializable;
import java.math.BigDecimal;
import java.util.Comparator;
import javax.persistence.CascadeType;
import javax.persistence.Column;
import javax.persistence.Entity;
import javax.persistence.GeneratedValue;
import javax.persistence.GenerationType;
import javax.persistence.Id;
import javax.persistence.IdClass;
import javax.persistence.JoinColumn;
import javax.persistence.ManyToOne;
import javax.persistence.Table;
import javax.persistence.TableGenerator;
import javax.persistence.Version;

@SuppressWarnings("serial")
@Entity
@Table(name="O_CUSTINVENTORY")
@IdClass(CustomerInventoryPK.class)
public class CustomerInventory implements Serializable, Comparator<CustomerInventory> {

        public static final String QUERY_COUNT = "CustomerInventory.count";

        @Id
        @TableGenerator(name="inventory",
            table="U_SEQUENCES",
            pkColumnName="S_ID",
            valueColumnName="S_NEXTNUM",
            pkColumnValue="inventory",
            allocationSize=1000)
    @GeneratedValue(strategy= GenerationType.TABLE,generator="inventory")
    @Column(name="CI_ID")
    private Long         id;

    @Id
    @Column(name = "CI_CUSTOMERID", insertable = false, updatable = false)
    private int             custId;

    @ManyToOne(cascade= CascadeType.MERGE)
    @JoinColumn(name="CI_CUSTOMERID")
    private Customer        customer;

    @ManyToOne(cascade=CascadeType.MERGE)
    @JoinColumn(name = "CI_ITEMID")
    private String            vehicle;

    @Column(name="CI_VALUE")
    private BigDecimal totalCost;

    @Column(name="CI_QUANTITY")
    private int             quantity;

    @Version
    @Column(name = "CI_VERSION")
    private int             version;

    public CustomerInventory() {
    }

        CustomerInventory(Customer customer, String vehicle, int quantity,
                      BigDecimal totalValue) {
        this.customer = customer;
        this.vehicle = vehicle;
        this.quantity = quantity;
        this.totalCost = totalValue;
    }

    public String getVehicle() {
        return vehicle;
    }

    public BigDecimal getTotalCost() {
        return totalCost;
    }

    public int getQuantity() {
        return quantity;
    }

    public Long getId() {
        return id;
    }

    public Customer getCustomer() {
        return customer;
    }

    public void setCustomer(Customer customer) {
        this.customer = customer;
    }

    public int getCustId() {
        return custId;
    }

    public int getVersion() {
        return version;
    }

    public int compare(CustomerInventory cdb1, CustomerInventory cdb2) {
        return cdb1.id.compareTo(cdb2.id);
    }

            @Override
    public boolean equals(Object obj) {
        if (obj == this)
            return true;
        if (obj == null || !(obj instanceof CustomerInventory))
            return false;
        if (this.id == ((CustomerInventory)obj).id)
            return true;
        if (this.id != null && ((CustomerInventory)obj).id == null)
            return false;
        if (this.id == null && ((CustomerInventory)obj).id != null)
            return false;

        return this.id.equals(((CustomerInventory)obj).id);
    }

    @Override
    public int hashCode() {
        int result = id.hashCode();
        result = 31 * result + custId;
        return result;
    }

}


File: hibernate-core/src/test/java/org/hibernate/test/bytecode/enhancement/entity/customer/CustomerInventoryPK.java
/*
 * Hibernate, Relational Persistence for Idiomatic Java
 *
 * License: GNU Lesser General Public License (LGPL), version 2.1 or later.
 * See the lgpl.txt file in the root directory or <http://www.gnu.org/licenses/lgpl-2.1.html>.
 */
package org.hibernate.test.bytecode.enhancement.entity.customer;

import java.io.Serializable;

/**
 * @author <a href="mailto:stale.pedersen@jboss.org">Ståle W. Pedersen</a>
 */
public class CustomerInventoryPK implements Serializable {

    private Long id;
    private int custId;

    public CustomerInventoryPK() {
    }

    public CustomerInventoryPK(Long id, int custId) {
        this.id = id;
        this.custId = custId;
    }

    public boolean equals(Object other) {
        if (other == this) {
            return true;
        }
        if (other == null || getClass() != other.getClass()) {
            return false;
        }
        CustomerInventoryPK cip = (CustomerInventoryPK) other;
        return (custId == cip.custId && (id == cip.id ||
                ( id != null && id.equals(cip.id))));
    }

    public int hashCode() {
        return (id == null ? 0 : id.hashCode()) ^ custId;
    }

    public Long getId() {
        return id;
    }

    public int getCustId() {
        return custId;
    }
}


File: hibernate-core/src/test/java/org/hibernate/test/bytecode/enhancement/entity/customer/Group.java
/*
 * Hibernate, Relational Persistence for Idiomatic Java
 *
 * License: GNU Lesser General Public License (LGPL), version 2.1 or later.
 * See the lgpl.txt file in the root directory or <http://www.gnu.org/licenses/lgpl-2.1.html>.
 */
package org.hibernate.test.bytecode.enhancement.entity.customer;

import javax.persistence.Column;
import javax.persistence.Entity;
import javax.persistence.GeneratedValue;
import javax.persistence.GenerationType;
import javax.persistence.ManyToMany;
import javax.persistence.SequenceGenerator;
import javax.persistence.Table;
import java.util.HashSet;
import java.util.Set;

/**
 * @author <a href="mailto:stale.pedersen@jboss.org">Ståle W. Pedersen</a>
 */
@Entity
@Table(name = "GROUP")
@SequenceGenerator(name = "GROUP_SEQUENCE", sequenceName = "GROUP_SEQUENCE", allocationSize = 1, initialValue = 0)
public class Group {

    @GeneratedValue(strategy = GenerationType.SEQUENCE, generator = "GROUP_SEQUENCE")
    private int id;

    @Column
    private String name;

    @ManyToMany(mappedBy = "groups")
    private Set<User> users = new HashSet<User>();

    public Group() {
    }

    public String getName() {
        return name;
    }

    public void setName(String name) {
        this.name = name;
    }

    public Set<User> getUsers() {
        return users;
    }

    public void setUsers(Set<User> users) {
        this.users = users;
    }

    public void removeUser(User user) {
        Set<User> set = this.users;
        set.remove(user);
        this.users = set;
    }
}

File: hibernate-core/src/test/java/org/hibernate/test/bytecode/enhancement/entity/customer/SupplierComponentPK.java
/*
 * Hibernate, Relational Persistence for Idiomatic Java
 *
 * License: GNU Lesser General Public License (LGPL), version 2.1 or later.
 * See the lgpl.txt file in the root directory or <http://www.gnu.org/licenses/lgpl-2.1.html>.
 */
package org.hibernate.test.bytecode.enhancement.entity.customer;

import javax.persistence.Embeddable;

/**
 * @author <a href="mailto:stale.pedersen@jboss.org">Ståle W. Pedersen</a>
 */
@Embeddable
public class SupplierComponentPK {

    String componentID;
    int supplierID;

    public SupplierComponentPK() {
    }

    public SupplierComponentPK(String suppCompID, int suppCompSuppID) {
        this.componentID = suppCompID;
        this.supplierID = suppCompSuppID;
    }

    public String getComponentID() {
        return componentID;
    }

    public int getSupplierID() {
        return supplierID;
    }

    @Override
    public int hashCode() {
        final int PRIME = 31;
        int result = 1;
        result = PRIME * result + componentID.hashCode();
        result = PRIME * result + supplierID;
        return result;
    }

    @Override
    public boolean equals(Object obj) {
        if (this == obj)
            return true;
        if (obj == null || getClass() != obj.getClass())
            return false;
        final SupplierComponentPK other = (SupplierComponentPK) obj;
        return componentID.equals(other.componentID);
    }
}


File: hibernate-core/src/test/java/org/hibernate/test/bytecode/enhancement/entity/customer/User.java
/*
 * Hibernate, Relational Persistence for Idiomatic Java
 *
 * License: GNU Lesser General Public License (LGPL), version 2.1 or later.
 * See the lgpl.txt file in the root directory or <http://www.gnu.org/licenses/lgpl-2.1.html>.
 */
package org.hibernate.test.bytecode.enhancement.entity.customer;

import javax.persistence.Column;
import javax.persistence.Entity;
import javax.persistence.GeneratedValue;
import javax.persistence.GenerationType;
import javax.persistence.ManyToMany;
import javax.persistence.OneToOne;
import javax.persistence.SequenceGenerator;
import javax.persistence.Table;
import java.util.HashSet;
import java.util.Set;

/**
 * @author <a href="mailto:stale.pedersen@jboss.org">Ståle W. Pedersen</a>
 */
@Entity
@Table(name = "USER")
@SequenceGenerator(name = "USER_SEQUENCE", sequenceName = "USER_SEQUENCE", allocationSize = 1, initialValue = 0)
public class User {

    @GeneratedValue(strategy = GenerationType.SEQUENCE, generator = "USER_SEQUENCE")
    private int id;

    @Column
    private String login;

    @Column
    private String password;

    @OneToOne(mappedBy = "user")
    private Customer customer;

    @ManyToMany
    private Set<Group> groups;

    public User() {
    }

    public Customer getCustomer() {
        return customer;
    }

    public void setCustomer(Customer customer) {
        this.customer = customer;
    }

    public String getLogin() {
        return login;
    }

    public void setLogin(String login) {
        this.login = login;
    }

    public String getPassword() {
        return password;
    }

    public void setPassword(String password) {
        this.password = password;
    }

    public void addGroup(Group group) {
        Set<Group> set = (groups == null ? new HashSet<Group>() : groups);
        set.add(group);
        groups = set;
    }

    public Set<Group> getGroups() {
        return groups;
    }

    public void setGroups(Set<Group> groups) {
        this.groups = groups;
    }
}