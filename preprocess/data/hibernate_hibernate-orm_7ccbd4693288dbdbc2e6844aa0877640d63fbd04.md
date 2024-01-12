Refactoring Types: ['Move Class']
va/org/hibernate/cfg/annotations/MapBinder.java
/*
 * Hibernate, Relational Persistence for Idiomatic Java
 *
 * License: GNU Lesser General Public License (LGPL), version 2.1 or later.
 * See the lgpl.txt file in the root directory or <http://www.gnu.org/licenses/lgpl-2.1.html>.
 */
package org.hibernate.cfg.annotations;

import org.hibernate.AnnotationException;
import org.hibernate.AssertionFailure;
import org.hibernate.FetchMode;
import org.hibernate.MappingException;
import org.hibernate.annotations.MapKeyType;
import org.hibernate.annotations.common.reflection.ClassLoadingException;
import org.hibernate.annotations.common.reflection.XClass;
import org.hibernate.annotations.common.reflection.XProperty;
import org.hibernate.boot.spi.MetadataBuildingContext;
import org.hibernate.cfg.AccessType;
import org.hibernate.cfg.AnnotatedClassType;
import org.hibernate.cfg.AnnotationBinder;
import org.hibernate.cfg.BinderHelper;
import org.hibernate.cfg.CollectionPropertyHolder;
import org.hibernate.cfg.CollectionSecondPass;
import org.hibernate.cfg.Ejb3Column;
import org.hibernate.cfg.Ejb3JoinColumn;
import org.hibernate.cfg.PropertyData;
import org.hibernate.cfg.PropertyHolderBuilder;
import org.hibernate.cfg.PropertyPreloadedData;
import org.hibernate.cfg.SecondPass;
import org.hibernate.dialect.HSQLDialect;
import org.hibernate.internal.util.StringHelper;
import org.hibernate.mapping.Collection;
import org.hibernate.mapping.Column;
import org.hibernate.mapping.Component;
import org.hibernate.mapping.DependantValue;
import org.hibernate.mapping.Formula;
import org.hibernate.mapping.Join;
import org.hibernate.mapping.ManyToOne;
import org.hibernate.mapping.OneToMany;
import org.hibernate.mapping.PersistentClass;
import org.hibernate.mapping.Property;
import org.hibernate.mapping.SimpleValue;
import org.hibernate.mapping.ToOne;
import org.hibernate.mapping.Value;
import org.hibernate.sql.Template;

import javax.persistence.AttributeOverride;
import javax.persistence.AttributeOverrides;
import javax.persistence.MapKeyClass;
import java.util.HashMap;
import java.util.Iterator;
import java.util.Map;
import java.util.Random;

/**
 * Implementation to bind a Map
 *
 * @author Emmanuel Bernard
 */
public class MapBinder extends CollectionBinder {
	public MapBinder(boolean sorted) {
		super( sorted );
	}

	public boolean isMap() {
		return true;
	}

	protected Collection createCollection(PersistentClass persistentClass) {
		return new org.hibernate.mapping.Map( getBuildingContext().getMetadataCollector(), persistentClass );
	}

	@Override
	public SecondPass getSecondPass(
			final Ejb3JoinColumn[] fkJoinColumns,
			final Ejb3JoinColumn[] keyColumns,
			final Ejb3JoinColumn[] inverseColumns,
			final Ejb3Column[] elementColumns,
			final Ejb3Column[] mapKeyColumns,
			final Ejb3JoinColumn[] mapKeyManyToManyColumns,
			final boolean isEmbedded,
			final XProperty property,
			final XClass collType,
			final boolean ignoreNotFound,
			final boolean unique,
			final TableBinder assocTableBinder,
			final MetadataBuildingContext buildingContext) {
		return new CollectionSecondPass( buildingContext, MapBinder.this.collection ) {
			public void secondPass(Map persistentClasses, Map inheritedMetas)
					throws MappingException {
				bindStarToManySecondPass(
						persistentClasses, collType, fkJoinColumns, keyColumns, inverseColumns, elementColumns,
						isEmbedded, property, unique, assocTableBinder, ignoreNotFound, buildingContext
				);
				bindKeyFromAssociationTable(
						collType, persistentClasses, mapKeyPropertyName, property, isEmbedded, buildingContext,
						mapKeyColumns, mapKeyManyToManyColumns,
						inverseColumns != null ? inverseColumns[0].getPropertyName() : null
				);
			}
		};
	}

	private void bindKeyFromAssociationTable(
			XClass collType,
			Map persistentClasses,
			String mapKeyPropertyName,
			XProperty property,
			boolean isEmbedded,
			MetadataBuildingContext buildingContext,
			Ejb3Column[] mapKeyColumns,
			Ejb3JoinColumn[] mapKeyManyToManyColumns,
			String targetPropertyName) {
		if ( mapKeyPropertyName != null ) {
			//this is an EJB3 @MapKey
			PersistentClass associatedClass = (PersistentClass) persistentClasses.get( collType.getName() );
			if ( associatedClass == null ) throw new AnnotationException( "Associated class not found: " + collType );
			Property mapProperty = BinderHelper.findPropertyByName( associatedClass, mapKeyPropertyName );
			if ( mapProperty == null ) {
				throw new AnnotationException(
						"Map key property not found: " + collType + "." + mapKeyPropertyName
				);
			}
			org.hibernate.mapping.Map map = (org.hibernate.mapping.Map) this.collection;
			Value indexValue = createFormulatedValue(
					mapProperty.getValue(), map, targetPropertyName, associatedClass, buildingContext
			);
			map.setIndex( indexValue );
		}
		else {
			//this is a true Map mapping
			//TODO ugly copy/pastle from CollectionBinder.bindManyToManySecondPass
			String mapKeyType;
			Class target = void.class;
			/*
			 * target has priority over reflection for the map key type
			 * JPA 2 has priority
			 */
			if ( property.isAnnotationPresent( MapKeyClass.class ) ) {
				target = property.getAnnotation( MapKeyClass.class ).value();
			}
			if ( !void.class.equals( target ) ) {
				mapKeyType = target.getName();
			}
			else {
				mapKeyType = property.getMapKey().getName();
			}
			PersistentClass collectionEntity = (PersistentClass) persistentClasses.get( mapKeyType );
			boolean isIndexOfEntities = collectionEntity != null;
			ManyToOne element = null;
			org.hibernate.mapping.Map mapValue = (org.hibernate.mapping.Map) this.collection;
			if ( isIndexOfEntities ) {
				element = new ManyToOne( buildingContext.getMetadataCollector(), mapValue.getCollectionTable() );
				mapValue.setIndex( element );
				element.setReferencedEntityName( mapKeyType );
				//element.setFetchMode( fetchMode );
				//element.setLazy( fetchMode != FetchMode.JOIN );
				//make the second join non lazy
				element.setFetchMode( FetchMode.JOIN );
				element.setLazy( false );
				//does not make sense for a map key element.setIgnoreNotFound( ignoreNotFound );
			}
			else {
				XClass keyXClass;
				AnnotatedClassType classType;
				if ( BinderHelper.PRIMITIVE_NAMES.contains( mapKeyType ) ) {
					classType = AnnotatedClassType.NONE;
					keyXClass = null;
				}
				else {
					try {
						keyXClass = buildingContext.getBuildingOptions().getReflectionManager().classForName( mapKeyType );
					}
					catch (ClassLoadingException e) {
						throw new AnnotationException( "Unable to find class: " + mapKeyType, e );
					}
					classType = buildingContext.getMetadataCollector().getClassType( keyXClass );
					//force in case of attribute override
					boolean attributeOverride = property.isAnnotationPresent( AttributeOverride.class )
							|| property.isAnnotationPresent( AttributeOverrides.class );
					if ( isEmbedded || attributeOverride ) {
						classType = AnnotatedClassType.EMBEDDABLE;
					}
				}

				CollectionPropertyHolder holder = PropertyHolderBuilder.buildPropertyHolder(
						mapValue,
						StringHelper.qualify( mapValue.getRole(), "mapkey" ),
						keyXClass,
						property,
						propertyHolder,
						buildingContext
				);


				// 'propertyHolder' is the PropertyHolder for the owner of the collection
				// 'holder' is the CollectionPropertyHolder.
				// 'property' is the collection XProperty
				propertyHolder.startingProperty( property );
				holder.prepare( property );

				PersistentClass owner = mapValue.getOwner();
				AccessType accessType;
				// FIXME support @Access for collection of elements
				// String accessType = access != null ? access.value() : null;
				if ( owner.getIdentifierProperty() != null ) {
					accessType = owner.getIdentifierProperty().getPropertyAccessorName().equals( "property" )
							? AccessType.PROPERTY
							: AccessType.FIELD;
				}
				else if ( owner.getIdentifierMapper() != null && owner.getIdentifierMapper().getPropertySpan() > 0 ) {
					Property prop = (Property) owner.getIdentifierMapper().getPropertyIterator().next();
					accessType = prop.getPropertyAccessorName().equals( "property" ) ? AccessType.PROPERTY
							: AccessType.FIELD;
				}
				else {
					throw new AssertionFailure( "Unable to guess collection property accessor name" );
				}

				if ( AnnotatedClassType.EMBEDDABLE.equals( classType ) ) {
					EntityBinder entityBinder = new EntityBinder();

					PropertyData inferredData;
					if ( isHibernateExtensionMapping() ) {
						inferredData = new PropertyPreloadedData( AccessType.PROPERTY, "index", keyXClass );
					}
					else {
						//"key" is the JPA 2 prefix for map keys
						inferredData = new PropertyPreloadedData( AccessType.PROPERTY, "key", keyXClass );
					}

					//TODO be smart with isNullable
					Component component = AnnotationBinder.fillComponent(
							holder,
							inferredData,
							accessType,
							true,
							entityBinder,
							false,
							false,
							true,
							buildingContext,
							inheritanceStatePerClass
					);
					mapValue.setIndex( component );
				}
				else {
					SimpleValueBinder elementBinder = new SimpleValueBinder();
					elementBinder.setBuildingContext( buildingContext );
					elementBinder.setReturnedClassName( mapKeyType );

					Ejb3Column[] elementColumns = mapKeyColumns;
					if ( elementColumns == null || elementColumns.length == 0 ) {
						elementColumns = new Ejb3Column[1];
						Ejb3Column column = new Ejb3Column();
						column.setImplicit( false );
						column.setNullable( true );
						column.setLength( Ejb3Column.DEFAULT_COLUMN_LENGTH );
						column.setLogicalColumnName( Collection.DEFAULT_KEY_COLUMN_NAME );
						//TODO create an EMPTY_JOINS collection
						column.setJoins( new HashMap<String, Join>() );
						column.setBuildingContext( buildingContext );
						column.bind();
						elementColumns[0] = column;
					}
					//override the table
					for (Ejb3Column column : elementColumns) {
						column.setTable( mapValue.getCollectionTable() );
					}
					elementBinder.setColumns( elementColumns );
					//do not call setType as it extract the type from @Type
					//the algorithm generally does not apply for map key anyway
					elementBinder.setKey(true);
					MapKeyType mapKeyTypeAnnotation = property.getAnnotation( MapKeyType.class );
					if ( mapKeyTypeAnnotation != null
							&& !BinderHelper.isEmptyAnnotationValue( mapKeyTypeAnnotation.value() .type() ) ) {
						elementBinder.setExplicitType( mapKeyTypeAnnotation.value() );
					}
					else {
						elementBinder.setType(
								property,
								keyXClass,
								this.collection.getOwnerEntityName(),
								holder.keyElementAttributeConverterDefinition( keyXClass )
						);
					}
					elementBinder.setPersistentClassName( propertyHolder.getEntityName() );
					elementBinder.setAccessType( accessType );
					mapValue.setIndex( elementBinder.make() );
				}
			}
			//FIXME pass the Index Entity JoinColumns
			if ( !collection.isOneToMany() ) {
				//index column shoud not be null
				for (Ejb3JoinColumn col : mapKeyManyToManyColumns) {
					col.forceNotNull();
				}
			}
			if ( isIndexOfEntities ) {
				bindManytoManyInverseFk(
						collectionEntity,
						mapKeyManyToManyColumns,
						element,
						false, //a map key column has no unique constraint
						buildingContext
				);
			}
		}
	}

	protected Value createFormulatedValue(
			Value value,
			Collection collection,
			String targetPropertyName,
			PersistentClass associatedClass,
			MetadataBuildingContext buildingContext) {
		Value element = collection.getElement();
		String fromAndWhere = null;
		if ( !( element instanceof OneToMany ) ) {
			String referencedPropertyName = null;
			if ( element instanceof ToOne ) {
				referencedPropertyName = ( (ToOne) element ).getReferencedPropertyName();
			}
			else if ( element instanceof DependantValue ) {
				//TODO this never happen I think
				if ( propertyName != null ) {
					referencedPropertyName = collection.getReferencedPropertyName();
				}
				else {
					throw new AnnotationException( "SecondaryTable JoinColumn cannot reference a non primary key" );
				}
			}
			Iterator referencedEntityColumns;
			if ( referencedPropertyName == null ) {
				referencedEntityColumns = associatedClass.getIdentifier().getColumnIterator();
			}
			else {
				Property referencedProperty = associatedClass.getRecursiveProperty( referencedPropertyName );
				referencedEntityColumns = referencedProperty.getColumnIterator();
			}
			String alias = "$alias$";
			StringBuilder fromAndWhereSb = new StringBuilder( " from " )
					.append( associatedClass.getTable().getName() )
							//.append(" as ") //Oracle doesn't support it in subqueries
					.append( " " )
					.append( alias ).append( " where " );
			Iterator collectionTableColumns = element.getColumnIterator();
			while ( collectionTableColumns.hasNext() ) {
				Column colColumn = (Column) collectionTableColumns.next();
				Column refColumn = (Column) referencedEntityColumns.next();
				fromAndWhereSb.append( alias ).append( '.' ).append( refColumn.getQuotedName() )
						.append( '=' ).append( colColumn.getQuotedName() ).append( " and " );
			}
			fromAndWhere = fromAndWhereSb.substring( 0, fromAndWhereSb.length() - 5 );
		}

		if ( value instanceof Component ) {
			Component component = (Component) value;
			Iterator properties = component.getPropertyIterator();
			Component indexComponent = new Component( getBuildingContext().getMetadataCollector(), collection );
			indexComponent.setComponentClassName( component.getComponentClassName() );
			//TODO I don't know if this is appropriate
			indexComponent.setNodeName( "index" );
			while ( properties.hasNext() ) {
				Property current = (Property) properties.next();
				Property newProperty = new Property();
				newProperty.setCascade( current.getCascade() );
				newProperty.setValueGenerationStrategy( current.getValueGenerationStrategy() );
				newProperty.setInsertable( false );
				newProperty.setUpdateable( false );
				newProperty.setMetaAttributes( current.getMetaAttributes() );
				newProperty.setName( current.getName() );
				newProperty.setNodeName( current.getNodeName() );
				newProperty.setNaturalIdentifier( false );
				//newProperty.setOptimisticLocked( false );
				newProperty.setOptional( false );
				newProperty.setPersistentClass( current.getPersistentClass() );
				newProperty.setPropertyAccessorName( current.getPropertyAccessorName() );
				newProperty.setSelectable( current.isSelectable() );
				newProperty.setValue(
						createFormulatedValue(
								current.getValue(), collection, targetPropertyName, associatedClass, buildingContext
						)
				);
				indexComponent.addProperty( newProperty );
			}
			return indexComponent;
		}
		else if ( value instanceof SimpleValue ) {
			SimpleValue sourceValue = (SimpleValue) value;
			SimpleValue targetValue;
			if ( value instanceof ManyToOne ) {
				ManyToOne sourceManyToOne = (ManyToOne) sourceValue;
				ManyToOne targetManyToOne = new ManyToOne( getBuildingContext().getMetadataCollector(), collection.getCollectionTable() );
				targetManyToOne.setFetchMode( FetchMode.DEFAULT );
				targetManyToOne.setLazy( true );
				//targetValue.setIgnoreNotFound( ); does not make sense for a map key
				targetManyToOne.setReferencedEntityName( sourceManyToOne.getReferencedEntityName() );
				targetValue = targetManyToOne;
			}
			else {
				targetValue = new SimpleValue( getBuildingContext().getMetadataCollector(), collection.getCollectionTable() );
				targetValue.setTypeName( sourceValue.getTypeName() );
				targetValue.setTypeParameters( sourceValue.getTypeParameters() );
			}
			Iterator columns = sourceValue.getColumnIterator();
			Random random = new Random();
			while ( columns.hasNext() ) {
				Object current = columns.next();
				Formula formula = new Formula();
				String formulaString;
				if ( current instanceof Column ) {
					formulaString = ( (Column) current ).getQuotedName();
				}
				else if ( current instanceof Formula ) {
					formulaString = ( (Formula) current ).getFormula();
				}
				else {
					throw new AssertionFailure( "Unknown element in column iterator: " + current.getClass() );
				}
				if ( fromAndWhere != null ) {
					formulaString = Template.renderWhereStringTemplate( formulaString, "$alias$", new HSQLDialect() );
					formulaString = "(select " + formulaString + fromAndWhere + ")";
					formulaString = StringHelper.replace(
							formulaString,
							"$alias$",
							"a" + random.nextInt( 16 )
					);
				}
				formula.setFormula( formulaString );
				targetValue.addFormula( formula );

			}
			return targetValue;
		}
		else {
			throw new AssertionFailure( "Unknown type encounters for map key: " + value.getClass() );
		}
	}
}


File: hibernate-core/src/main/java/org/hibernate/cfg/annotations/SimpleValueBinder.java
/*
 * Hibernate, Relational Persistence for Idiomatic Java
 *
 * License: GNU Lesser General Public License (LGPL), version 2.1 or later.
 * See the lgpl.txt file in the root directory or <http://www.gnu.org/licenses/lgpl-2.1.html>.
 */
package org.hibernate.cfg.annotations;

import java.io.Serializable;
import java.util.Calendar;
import java.util.Date;
import java.util.Properties;
import javax.persistence.Enumerated;
import javax.persistence.Id;
import javax.persistence.Lob;
import javax.persistence.MapKeyEnumerated;
import javax.persistence.MapKeyTemporal;
import javax.persistence.Temporal;
import javax.persistence.TemporalType;

import org.hibernate.AnnotationException;
import org.hibernate.AssertionFailure;
import org.hibernate.MappingException;
import org.hibernate.annotations.Nationalized;
import org.hibernate.annotations.Parameter;
import org.hibernate.annotations.Type;
import org.hibernate.annotations.common.reflection.ClassLoadingException;
import org.hibernate.annotations.common.reflection.XClass;
import org.hibernate.annotations.common.reflection.XProperty;
import org.hibernate.annotations.common.util.StandardClassLoaderDelegateImpl;
import org.hibernate.boot.model.TypeDefinition;
import org.hibernate.boot.spi.MetadataBuildingContext;
import org.hibernate.cfg.AccessType;
import org.hibernate.cfg.AttributeConverterDefinition;
import org.hibernate.cfg.BinderHelper;
import org.hibernate.cfg.Ejb3Column;
import org.hibernate.cfg.Ejb3JoinColumn;
import org.hibernate.cfg.NotYetImplementedException;
import org.hibernate.cfg.PkDrivenByDefaultMapsIdSecondPass;
import org.hibernate.cfg.SetSimpleValueTypeSecondPass;
import org.hibernate.internal.CoreMessageLogger;
import org.hibernate.internal.util.StringHelper;
import org.hibernate.mapping.SimpleValue;
import org.hibernate.mapping.Table;
import org.hibernate.type.CharacterArrayClobType;
import org.hibernate.type.CharacterArrayNClobType;
import org.hibernate.type.CharacterNCharType;
import org.hibernate.type.EnumType;
import org.hibernate.type.PrimitiveCharacterArrayClobType;
import org.hibernate.type.PrimitiveCharacterArrayNClobType;
import org.hibernate.type.SerializableToBlobType;
import org.hibernate.type.StandardBasicTypes;
import org.hibernate.type.StringNVarcharType;
import org.hibernate.type.WrappedMaterializedBlobType;
import org.hibernate.usertype.DynamicParameterizedType;

import org.jboss.logging.Logger;

/**
 * @author Emmanuel Bernard
 */
public class SimpleValueBinder {
    private static final CoreMessageLogger LOG = Logger.getMessageLogger(CoreMessageLogger.class, SimpleValueBinder.class.getName());

	private MetadataBuildingContext buildingContext;

	private String propertyName;
	private String returnedClassName;
	private Ejb3Column[] columns;
	private String persistentClassName;
	private String explicitType = "";
	private String defaultType = "";
	private Properties typeParameters = new Properties();
	private boolean isNationalized;

	private Table table;
	private SimpleValue simpleValue;
	private boolean isVersion;
	private String timeStampVersionType;
	//is a Map key
	private boolean key;
	private String referencedEntityName;
	private XProperty xproperty;
	private AccessType accessType;

	private AttributeConverterDefinition attributeConverterDefinition;

	public void setReferencedEntityName(String referencedEntityName) {
		this.referencedEntityName = referencedEntityName;
	}

	public boolean isVersion() {
		return isVersion;
	}

	public void setVersion(boolean isVersion) {
		this.isVersion = isVersion;
	}

	public void setTimestampVersionType(String versionType) {
		this.timeStampVersionType = versionType;
	}

	public void setPropertyName(String propertyName) {
		this.propertyName = propertyName;
	}

	public void setReturnedClassName(String returnedClassName) {
		this.returnedClassName = returnedClassName;

		if ( defaultType.length() == 0 ) {
			defaultType = returnedClassName;
		}
	}

	public void setTable(Table table) {
		this.table = table;
	}

	public void setColumns(Ejb3Column[] columns) {
		this.columns = columns;
	}


	public void setPersistentClassName(String persistentClassName) {
		this.persistentClassName = persistentClassName;
	}

	//TODO execute it lazily to be order safe

	public void setType(XProperty property, XClass returnedClass, String declaringClassName, AttributeConverterDefinition attributeConverterDefinition) {
		if ( returnedClass == null ) {
			// we cannot guess anything
			return;
		}
		XClass returnedClassOrElement = returnedClass;
                boolean isArray = false;
		if ( property.isArray() ) {
			returnedClassOrElement = property.getElementClass();
			isArray = true;
		}
		this.xproperty = property;
		Properties typeParameters = this.typeParameters;
		typeParameters.clear();
		String type = BinderHelper.ANNOTATION_STRING_DEFAULT;

		isNationalized = property.isAnnotationPresent( Nationalized.class )
				|| buildingContext.getBuildingOptions().useNationalizedCharacterData();

		Type annType = property.getAnnotation( Type.class );
		if ( annType != null ) {
			setExplicitType( annType );
			type = explicitType;
		}
		else if ( ( !key && property.isAnnotationPresent( Temporal.class ) )
				|| ( key && property.isAnnotationPresent( MapKeyTemporal.class ) ) ) {

			boolean isDate;
			if ( buildingContext.getBuildingOptions().getReflectionManager().equals( returnedClassOrElement, Date.class ) ) {
				isDate = true;
			}
			else if ( buildingContext.getBuildingOptions().getReflectionManager().equals( returnedClassOrElement, Calendar.class ) ) {
				isDate = false;
			}
			else {
				throw new AnnotationException(
						"@Temporal should only be set on a java.util.Date or java.util.Calendar property: "
								+ StringHelper.qualify( persistentClassName, propertyName )
				);
			}
			final TemporalType temporalType = getTemporalType( property );
			switch ( temporalType ) {
				case DATE:
					type = isDate ? "date" : "calendar_date";
					break;
				case TIME:
					type = "time";
					if ( !isDate ) {
						throw new NotYetImplementedException(
								"Calendar cannot persist TIME only"
										+ StringHelper.qualify( persistentClassName, propertyName )
						);
					}
					break;
				case TIMESTAMP:
					type = isDate ? "timestamp" : "calendar";
					break;
				default:
					throw new AssertionFailure( "Unknown temporal type: " + temporalType );
			}
			explicitType = type;
		}
		else if ( !key && property.isAnnotationPresent( Lob.class ) ) {
			if ( buildingContext.getBuildingOptions().getReflectionManager().equals( returnedClassOrElement, java.sql.Clob.class ) ) {
				type = isNationalized
						? StandardBasicTypes.NCLOB.getName()
						: StandardBasicTypes.CLOB.getName();
			}
			else if ( buildingContext.getBuildingOptions().getReflectionManager().equals( returnedClassOrElement, java.sql.NClob.class ) ) {
				type = StandardBasicTypes.NCLOB.getName();
			}
			else if ( buildingContext.getBuildingOptions().getReflectionManager().equals( returnedClassOrElement, java.sql.Blob.class ) ) {
				type = "blob";
			}
			else if ( buildingContext.getBuildingOptions().getReflectionManager().equals( returnedClassOrElement, String.class ) ) {
				type = isNationalized
						? StandardBasicTypes.MATERIALIZED_NCLOB.getName()
						: StandardBasicTypes.MATERIALIZED_CLOB.getName();
			}
			else if ( buildingContext.getBuildingOptions().getReflectionManager().equals( returnedClassOrElement, Character.class ) && isArray ) {
				type = isNationalized
						? CharacterArrayNClobType.class.getName()
						: CharacterArrayClobType.class.getName();
			}
			else if ( buildingContext.getBuildingOptions().getReflectionManager().equals( returnedClassOrElement, char.class ) && isArray ) {
				type = isNationalized
						? PrimitiveCharacterArrayNClobType.class.getName()
						: PrimitiveCharacterArrayClobType.class.getName();
			}
			else if ( buildingContext.getBuildingOptions().getReflectionManager().equals( returnedClassOrElement, Byte.class ) && isArray ) {
				type = WrappedMaterializedBlobType.class.getName();
			}
			else if ( buildingContext.getBuildingOptions().getReflectionManager().equals( returnedClassOrElement, byte.class ) && isArray ) {
				type = StandardBasicTypes.MATERIALIZED_BLOB.getName();
			}
			else if ( buildingContext.getBuildingOptions().getReflectionManager()
					.toXClass( Serializable.class )
					.isAssignableFrom( returnedClassOrElement ) ) {
				type = SerializableToBlobType.class.getName();
				typeParameters.setProperty(
						SerializableToBlobType.CLASS_NAME,
						returnedClassOrElement.getName()
				);
			}
			else {
				type = "blob";
			}
			explicitType = type;
		}
		else if ( ( !key && property.isAnnotationPresent( Enumerated.class ) )
				|| ( key && property.isAnnotationPresent( MapKeyEnumerated.class ) ) ) {
			final Class attributeJavaType = buildingContext.getBuildingOptions().getReflectionManager().toClass( returnedClassOrElement );
			if ( !Enum.class.isAssignableFrom( attributeJavaType ) ) {
				throw new AnnotationException(
						String.format(
								"Attribute [%s.%s] was annotated as enumerated, but its java type is not an enum [%s]",
								declaringClassName,
								xproperty.getName(),
								attributeJavaType.getName()
						)
				);
			}
			type = EnumType.class.getName();
			explicitType = type;
		}
		else if ( isNationalized ) {
			if ( buildingContext.getBuildingOptions().getReflectionManager().equals( returnedClassOrElement, String.class ) ) {
				// nvarchar
				type = StringNVarcharType.INSTANCE.getName();
				explicitType = type;
			}
			else if ( buildingContext.getBuildingOptions().getReflectionManager().equals( returnedClassOrElement, Character.class ) ) {
				if ( isArray ) {
					// nvarchar
					type = StringNVarcharType.INSTANCE.getName();
				}
				else {
					// nchar
					type = CharacterNCharType.INSTANCE.getName();
				}
				explicitType = type;
			}
		}

		// implicit type will check basic types and Serializable classes
		if ( columns == null ) {
			throw new AssertionFailure( "SimpleValueBinder.setColumns should be set before SimpleValueBinder.setType" );
		}

		if ( BinderHelper.ANNOTATION_STRING_DEFAULT.equals( type ) ) {
			if ( returnedClassOrElement.isEnum() ) {
				type = EnumType.class.getName();
			}
		}

		defaultType = BinderHelper.isEmptyAnnotationValue( type ) ? returnedClassName : type;
		this.typeParameters = typeParameters;

		applyAttributeConverter( property, attributeConverterDefinition );
	}

	private void applyAttributeConverter(XProperty property, AttributeConverterDefinition attributeConverterDefinition) {
		if ( attributeConverterDefinition == null ) {
			return;
		}

		LOG.debugf( "Starting applyAttributeConverter [%s:%s]", persistentClassName, property.getName() );

		if ( property.isAnnotationPresent( Id.class ) ) {
			LOG.debugf( "Skipping AttributeConverter checks for Id attribute [%s]", property.getName() );
			return;
		}

		if ( isVersion ) {
			LOG.debugf( "Skipping AttributeConverter checks for version attribute [%s]", property.getName() );
			return;
		}

		if ( property.isAnnotationPresent( Temporal.class ) ) {
			LOG.debugf( "Skipping AttributeConverter checks for Temporal attribute [%s]", property.getName() );
			return;
		}

		if ( property.isAnnotationPresent( Enumerated.class ) ) {
			LOG.debugf( "Skipping AttributeConverter checks for Enumerated attribute [%s]", property.getName() );
			return;
		}

		if ( isAssociation() ) {
			LOG.debugf( "Skipping AttributeConverter checks for association attribute [%s]", property.getName() );
			return;
		}

		this.attributeConverterDefinition = attributeConverterDefinition;
	}

	private boolean isAssociation() {
		// todo : this information is only known to caller(s), need to pass that information in somehow.
		// or, is this enough?
		return referencedEntityName != null;
	}

	private TemporalType getTemporalType(XProperty property) {
		if ( key ) {
			MapKeyTemporal ann = property.getAnnotation( MapKeyTemporal.class );
			return ann.value();
		}
		else {
			Temporal ann = property.getAnnotation( Temporal.class );
			return ann.value();
		}
	}

	public void setExplicitType(String explicitType) {
		this.explicitType = explicitType;
	}

	//FIXME raise an assertion failure  if setResolvedTypeMapping(String) and setResolvedTypeMapping(Type) are use at the same time

	public void setExplicitType(Type typeAnn) {
		if ( typeAnn != null ) {
			explicitType = typeAnn.type();
			typeParameters.clear();
			for ( Parameter param : typeAnn.parameters() ) {
				typeParameters.setProperty( param.name(), param.value() );
			}
		}
	}

	public void setBuildingContext(MetadataBuildingContext buildingContext) {
		this.buildingContext = buildingContext;
	}

	private void validate() {
		//TODO check necessary params
		Ejb3Column.checkPropertyConsistency( columns, propertyName );
	}

	public SimpleValue make() {

		validate();
		LOG.debugf( "building SimpleValue for %s", propertyName );
		if ( table == null ) {
			table = columns[0].getTable();
		}
		simpleValue = new SimpleValue( buildingContext.getMetadataCollector(), table );
		if ( isNationalized ) {
			simpleValue.makeNationalized();
		}

		linkWithValue();

		boolean isInSecondPass = buildingContext.getMetadataCollector().isInSecondPass();
		if ( !isInSecondPass ) {
			//Defer this to the second pass
			buildingContext.getMetadataCollector().addSecondPass( new SetSimpleValueTypeSecondPass( this ) );
		}
		else {
			//We are already in second pass
			fillSimpleValue();
		}
		return simpleValue;
	}

	public void linkWithValue() {
		if ( columns[0].isNameDeferred() && !buildingContext.getMetadataCollector().isInSecondPass() && referencedEntityName != null ) {
			buildingContext.getMetadataCollector().addSecondPass(
					new PkDrivenByDefaultMapsIdSecondPass(
							referencedEntityName, (Ejb3JoinColumn[]) columns, simpleValue
					)
			);
		}
		else {
			for ( Ejb3Column column : columns ) {
				column.linkWithValue( simpleValue );
			}
		}
	}

	public void fillSimpleValue() {
		LOG.debugf( "Starting fillSimpleValue for %s", propertyName );
                
		if ( attributeConverterDefinition != null ) {
			if ( ! BinderHelper.isEmptyAnnotationValue( explicitType ) ) {
				throw new AnnotationException(
						String.format(
								"AttributeConverter and explicit Type cannot be applied to same attribute [%s.%s];" +
										"remove @Type or specify @Convert(disableConversion = true)",
								persistentClassName,
								propertyName
						)
				);
			}
			LOG.debugf(
					"Applying JPA AttributeConverter [%s] to [%s:%s]",
					attributeConverterDefinition,
					persistentClassName,
					propertyName
			);
			simpleValue.setJpaAttributeConverterDefinition( attributeConverterDefinition );
		}
		else {
			String type;
			TypeDefinition typeDef;

			if ( !BinderHelper.isEmptyAnnotationValue( explicitType ) ) {
				type = explicitType;
				typeDef = buildingContext.getMetadataCollector().getTypeDefinition( type );
			}
			else {
				// try implicit type
				TypeDefinition implicitTypeDef = buildingContext.getMetadataCollector().getTypeDefinition( returnedClassName );
				if ( implicitTypeDef != null ) {
					typeDef = implicitTypeDef;
					type = returnedClassName;
				}
				else {
					typeDef = buildingContext.getMetadataCollector().getTypeDefinition( defaultType );
					type = defaultType;
				}
			}

			if ( typeDef != null ) {
				type = typeDef.getTypeImplementorClass().getName();
				simpleValue.setTypeParameters( typeDef.getParametersAsProperties() );
			}
			if ( typeParameters != null && typeParameters.size() != 0 ) {
				//explicit type params takes precedence over type def params
				simpleValue.setTypeParameters( typeParameters );
			}
			simpleValue.setTypeName( type );
		}

		if ( persistentClassName != null || attributeConverterDefinition != null ) {
			simpleValue.setTypeUsingReflection( persistentClassName, propertyName );
		}

		if ( !simpleValue.isTypeSpecified() && isVersion() ) {
			simpleValue.setTypeName( "integer" );
		}

		// HHH-5205
		if ( timeStampVersionType != null ) {
			simpleValue.setTypeName( timeStampVersionType );
		}
		
		if ( simpleValue.getTypeName() != null && simpleValue.getTypeName().length() > 0
				&& simpleValue.getMetadata().getTypeResolver().basic( simpleValue.getTypeName() ) == null ) {
			try {
				Class typeClass = buildingContext.getClassLoaderAccess().classForName( simpleValue.getTypeName() );

				if ( typeClass != null && DynamicParameterizedType.class.isAssignableFrom( typeClass ) ) {
					Properties parameters = simpleValue.getTypeParameters();
					if ( parameters == null ) {
						parameters = new Properties();
					}
					parameters.put( DynamicParameterizedType.IS_DYNAMIC, Boolean.toString( true ) );
					parameters.put( DynamicParameterizedType.RETURNED_CLASS, returnedClassName );
					parameters.put( DynamicParameterizedType.IS_PRIMARY_KEY, Boolean.toString( key ) );

					parameters.put( DynamicParameterizedType.ENTITY, persistentClassName );
					parameters.put( DynamicParameterizedType.XPROPERTY, xproperty );
					parameters.put( DynamicParameterizedType.PROPERTY, xproperty.getName() );
					parameters.put( DynamicParameterizedType.ACCESS_TYPE, accessType.getType() );
					simpleValue.setTypeParameters( parameters );
				}
			}
			catch (ClassLoadingException e) {
				throw new MappingException( "Could not determine type for: " + simpleValue.getTypeName(), e );
			}
		}

	}

	public void setKey(boolean key) {
		this.key = key;
	}

	public AccessType getAccessType() {
		return accessType;
	}

	public void setAccessType(AccessType accessType) {
		this.accessType = accessType;
	}
}


File: hibernate-core/src/test/java/org/hibernate/test/annotations/enumerated/EntityEnum.java
/*
 * Hibernate, Relational Persistence for Idiomatic Java
 *
 * License: GNU Lesser General Public License (LGPL), version 2.1 or later.
 * See the lgpl.txt file in the root directory or <http://www.gnu.org/licenses/lgpl-2.1.html>.
 */
package org.hibernate.test.annotations.enumerated;

import java.util.HashSet;
import java.util.Set;
import javax.persistence.Column;
import javax.persistence.ElementCollection;
import javax.persistence.Entity;
import javax.persistence.EnumType;
import javax.persistence.Enumerated;
import javax.persistence.FetchType;
import javax.persistence.GeneratedValue;
import javax.persistence.Id;
import javax.persistence.JoinColumn;
import javax.persistence.JoinTable;

import org.hibernate.annotations.Formula;
import org.hibernate.annotations.Type;
import org.hibernate.annotations.TypeDef;
import org.hibernate.annotations.TypeDefs;

/**
 * @author Janario Oliveira
 * @author Brett Meyer
 */
@Entity
@TypeDefs({ @TypeDef(typeClass = LastNumberType.class, defaultForType = EntityEnum.LastNumber.class) })
public class EntityEnum {

	enum Common {

		A1, A2, B1, B2
	}

	enum FirstLetter {

		A_LETTER, B_LETTER, C_LETTER
	}

	enum LastNumber {

		NUMBER_1, NUMBER_2, NUMBER_3
	}

	enum Trimmed {

		A, B, C
	}

	@Id
	@GeneratedValue
	private long id;
	private Common ordinal;
	@Enumerated(EnumType.STRING)
	private Common string;
	@Type(type = "org.hibernate.test.annotations.enumerated.FirstLetterType")
	private FirstLetter firstLetter;
	private LastNumber lastNumber;
	@Enumerated(EnumType.STRING)
	private LastNumber explicitOverridingImplicit;
	@Column(columnDefinition = "char(5)")
	@Enumerated(EnumType.STRING)
	private Trimmed trimmed;

	@Formula("upper('a')")
	@Enumerated(EnumType.STRING)
	private Trimmed formula;

	@Enumerated(EnumType.STRING)
	@ElementCollection(targetClass = Common.class, fetch = FetchType.LAZY)
	@JoinTable(name = "set_enum", joinColumns = { @JoinColumn(name = "entity_id") })
	@Column(name = "common_enum", nullable = false)
	private Set<Common> set = new HashSet<Common>();

	public long getId() {
		return id;
	}

	public void setId(long id) {
		this.id = id;
	}

	public Common getOrdinal() {
		return ordinal;
	}

	public void setOrdinal(Common ordinal) {
		this.ordinal = ordinal;
	}

	public Common getString() {
		return string;
	}

	public void setString(Common string) {
		this.string = string;
	}

	public FirstLetter getFirstLetter() {
		return firstLetter;
	}

	public void setFirstLetter(FirstLetter firstLetter) {
		this.firstLetter = firstLetter;
	}

	public LastNumber getLastNumber() {
		return lastNumber;
	}

	public void setLastNumber(LastNumber lastNumber) {
		this.lastNumber = lastNumber;
	}

	public LastNumber getExplicitOverridingImplicit() {
		return explicitOverridingImplicit;
	}

	public void setExplicitOverridingImplicit(LastNumber explicitOverridingImplicit) {
		this.explicitOverridingImplicit = explicitOverridingImplicit;
	}

	public Trimmed getTrimmed() {
		return trimmed;
	}

	public void setTrimmed(Trimmed trimmed) {
		this.trimmed = trimmed;
	}

	public Trimmed getFormula() {
		return formula;
	}

	public void setFormula(Trimmed formula) {
		this.formula = formula;
	}

	public Set<Common> getSet() {
		return set;
	}

	public void setSet(Set<Common> set) {
		this.set = set;
	}
}


File: hibernate-core/src/test/java/org/hibernate/test/annotations/enumerated/EnumeratedTypeTest.java
/*
 * Hibernate, Relational Persistence for Idiomatic Java
 *
 * License: GNU Lesser General Public License (LGPL), version 2.1 or later.
 * See the lgpl.txt file in the root directory or <http://www.gnu.org/licenses/lgpl-2.1.html>.
 */
package org.hibernate.test.annotations.enumerated;

import java.io.Serializable;
import java.sql.Connection;
import java.sql.SQLException;
import java.sql.Statement;
import java.util.List;

import org.hibernate.Query;
import org.hibernate.Session;
import org.hibernate.criterion.Restrictions;
import org.hibernate.dialect.AbstractHANADialect;
import org.hibernate.dialect.Oracle8iDialect;
import org.hibernate.engine.spi.SessionImplementor;
import org.hibernate.mapping.PersistentClass;
import org.hibernate.type.EnumType;
import org.hibernate.type.Type;

import org.junit.Test;

import org.hibernate.testing.SkipForDialect;
import org.hibernate.testing.TestForIssue;
import org.hibernate.testing.junit4.BaseNonConfigCoreFunctionalTestCase;
import org.hibernate.test.annotations.enumerated.EntityEnum.Common;
import org.hibernate.test.annotations.enumerated.EntityEnum.FirstLetter;
import org.hibernate.test.annotations.enumerated.EntityEnum.LastNumber;
import org.hibernate.test.annotations.enumerated.EntityEnum.Trimmed;

import static org.junit.Assert.assertEquals;

/**
 * Test type definition for enum
 * 
 * @author Janario Oliveira
 */
public class EnumeratedTypeTest extends BaseNonConfigCoreFunctionalTestCase {

	@Test
	public void testTypeDefinition() {
		PersistentClass pc = metadata().getEntityBinding( EntityEnum.class.getName() );

		// ordinal default of EnumType
		Type ordinalEnum = pc.getProperty( "ordinal" ).getType();
		assertEquals( Common.class, ordinalEnum.getReturnedClass() );
		assertEquals( EnumType.class.getName(), ordinalEnum.getName() );

		// string defined by Enumerated(STRING)
		Type stringEnum = pc.getProperty( "string" ).getType();
		assertEquals( Common.class, stringEnum.getReturnedClass() );
		assertEquals( EnumType.class.getName(), stringEnum.getName() );

		// explicit defined by @Type
		Type first = pc.getProperty( "firstLetter" ).getType();
		assertEquals( FirstLetter.class, first.getReturnedClass() );
		assertEquals( FirstLetterType.class.getName(), first.getName() );

		// implicit defined by @TypeDef in somewhere
		Type last = pc.getProperty( "lastNumber" ).getType();
		assertEquals( LastNumber.class, last.getReturnedClass() );
		assertEquals( LastNumberType.class.getName(), last.getName() );

		// implicit defined by @TypeDef in anywhere, but overrided by Enumerated(STRING)
		Type implicitOverrideExplicit = pc.getProperty( "explicitOverridingImplicit" ).getType();
		assertEquals( LastNumber.class, implicitOverrideExplicit.getReturnedClass() );
		assertEquals( EnumType.class.getName(), implicitOverrideExplicit.getName() );
	}

	@Test
	public void testTypeQuery() {
		Session session = openSession();
		session.getTransaction().begin();

		// persist
		EntityEnum entityEnum = new EntityEnum();
		entityEnum.setOrdinal( Common.A2 );
		Serializable id = session.save( entityEnum );

		session.getTransaction().commit();
		session.close();

		session = openSession();
		session.getTransaction().begin();

		// find
		entityEnum = (EntityEnum) session.createQuery( "from EntityEnum ee where ee.ordinal=1" ).uniqueResult();
		assertEquals( id, entityEnum.getId() );
		assertEquals( Common.A2, entityEnum.getOrdinal() );
		// find parameter
		entityEnum = (EntityEnum) session.createQuery( "from EntityEnum ee where ee.ordinal=:ordinal" )
				.setParameter( "ordinal", Common.A2 ).uniqueResult();
		assertEquals( id, entityEnum.getId() );
		assertEquals( Common.A2, entityEnum.getOrdinal() );
		// delete
		assertEquals( 1, session.createSQLQuery( "DELETE FROM EntityEnum where ordinal=1" ).executeUpdate() );

		session.getTransaction().commit();
		session.close();

		// **************
		session = openSession();
		session.getTransaction().begin();

		// persist
		entityEnum = new EntityEnum();
		entityEnum.setString( Common.B1 );
		id = session.save( entityEnum );

		session.getTransaction().commit();
		session.close();

		session = openSession();
		session.getTransaction().begin();

		// find
		entityEnum = (EntityEnum) session.createQuery( "from EntityEnum ee where ee.string='B1'" ).uniqueResult();
		assertEquals( id, entityEnum.getId() );
		assertEquals( Common.B1, entityEnum.getString() );
		// find parameter
		entityEnum = (EntityEnum) session.createQuery( "from EntityEnum ee where ee.string=:string" )
				.setParameter( "string", Common.B1 ).uniqueResult();
		assertEquals( id, entityEnum.getId() );
		assertEquals( Common.B1, entityEnum.getString() );
		// delete
		assertEquals( 1, session.createSQLQuery( "DELETE FROM EntityEnum where string='B1'" ).executeUpdate() );
		session.getTransaction().commit();
		session.close();

		// **************
		session = openSession();
		session.getTransaction().begin();

		// persist
		entityEnum = new EntityEnum();
		entityEnum.setFirstLetter( FirstLetter.C_LETTER );
		id = session.save( entityEnum );

		session.getTransaction().commit();
		session.close();

		session = openSession();
		session.getTransaction().begin();

		// find
		entityEnum = (EntityEnum) session.createQuery( "from EntityEnum ee where ee.firstLetter='C'" ).uniqueResult();
		assertEquals( id, entityEnum.getId() );
		assertEquals( FirstLetter.C_LETTER, entityEnum.getFirstLetter() );
		// find parameter
		entityEnum = (EntityEnum) session.createQuery( "from EntityEnum ee where ee.firstLetter=:firstLetter" )
				.setParameter( "firstLetter", FirstLetter.C_LETTER ).uniqueResult();
		assertEquals( id, entityEnum.getId() );
		assertEquals( FirstLetter.C_LETTER, entityEnum.getFirstLetter() );
		// delete
		assertEquals( 1, session.createSQLQuery( "DELETE FROM EntityEnum where firstLetter='C'" ).executeUpdate() );

		session.getTransaction().commit();
		session.close();

		// **************
		session = openSession();
		session.getTransaction().begin();

		// persist
		entityEnum = new EntityEnum();
		entityEnum.setLastNumber( LastNumber.NUMBER_1 );
		id = session.save( entityEnum );

		session.getTransaction().commit();
		session.close();

		session = openSession();
		session.getTransaction().begin();

		// find
		entityEnum = (EntityEnum) session.createQuery( "from EntityEnum ee where ee.lastNumber='1'" ).uniqueResult();
		assertEquals( id, entityEnum.getId() );
		assertEquals( LastNumber.NUMBER_1, entityEnum.getLastNumber() );
		// find parameter
		entityEnum = (EntityEnum) session.createQuery( "from EntityEnum ee where ee.lastNumber=:lastNumber" )
				.setParameter( "lastNumber", LastNumber.NUMBER_1 ).uniqueResult();
		assertEquals( id, entityEnum.getId() );
		assertEquals( LastNumber.NUMBER_1, entityEnum.getLastNumber() );
		// delete
		assertEquals( 1, session.createSQLQuery( "DELETE FROM EntityEnum where lastNumber='1'" ).executeUpdate() );

		session.getTransaction().commit();
		session.close();

		// **************
		session = openSession();
		session.getTransaction().begin();

		// persist
		entityEnum = new EntityEnum();
		entityEnum.setExplicitOverridingImplicit( LastNumber.NUMBER_2 );
		id = session.save( entityEnum );

		session.getTransaction().commit();
		session.close();

		session = openSession();
		session.getTransaction().begin();

		// find
		entityEnum = (EntityEnum) session.createQuery(
				"from EntityEnum ee where ee.explicitOverridingImplicit='NUMBER_2'" ).uniqueResult();
		assertEquals( id, entityEnum.getId() );
		assertEquals( LastNumber.NUMBER_2, entityEnum.getExplicitOverridingImplicit() );
		// find parameter
		entityEnum = (EntityEnum) session
				.createQuery( "from EntityEnum ee where ee.explicitOverridingImplicit=:override" )
				.setParameter( "override", LastNumber.NUMBER_2 ).uniqueResult();
		assertEquals( id, entityEnum.getId() );
		assertEquals( LastNumber.NUMBER_2, entityEnum.getExplicitOverridingImplicit() );
		// delete
		assertEquals( 1, session.createSQLQuery( "DELETE FROM EntityEnum where explicitOverridingImplicit='NUMBER_2'" )
				.executeUpdate() );

		session.getTransaction().commit();
		session.close();
	}

	@Test
	public void testTypeCriteria() {
		Session session = openSession();
		session.getTransaction().begin();

		// persist
		EntityEnum entityEnum = new EntityEnum();
		entityEnum.setOrdinal( Common.A1 );
		Serializable id = session.save( entityEnum );

		session.getTransaction().commit();
		session.close();
		session = openSession();
		session.getTransaction().begin();

		// find
		entityEnum = (EntityEnum) session.createCriteria( EntityEnum.class )
				.add( Restrictions.eq( "ordinal", Common.A1 ) ).uniqueResult();
		assertEquals( id, entityEnum.getId() );
		assertEquals( Common.A1, entityEnum.getOrdinal() );
		// delete
		assertEquals( 1, session.createSQLQuery( "DELETE FROM EntityEnum where ordinal=0" ).executeUpdate() );

		session.getTransaction().commit();
		session.close();

		// **************
		session = openSession();
		session.getTransaction().begin();

		// persist
		entityEnum = new EntityEnum();
		entityEnum.setString( Common.B2 );
		id = session.save( entityEnum );

		session.getTransaction().commit();
		session.close();
		session = openSession();
		session.getTransaction().begin();

		// find
		entityEnum = (EntityEnum) session.createCriteria( EntityEnum.class )
				.add( Restrictions.eq( "string", Common.B2 ) ).uniqueResult();
		assertEquals( id, entityEnum.getId() );
		assertEquals( Common.B2, entityEnum.getString() );
		// delete
		assertEquals( 1, session.createSQLQuery( "DELETE FROM EntityEnum where string='B2'" ).executeUpdate() );

		session.getTransaction().commit();
		session.close();

		// **************
		session = openSession();
		session.getTransaction().begin();

		// persist
		entityEnum = new EntityEnum();
		entityEnum.setFirstLetter( FirstLetter.A_LETTER );
		id = session.save( entityEnum );

		session.getTransaction().commit();
		session.close();
		session = openSession();
		session.getTransaction().begin();

		// find
		entityEnum = (EntityEnum) session.createCriteria( EntityEnum.class )
				.add( Restrictions.eq( "firstLetter", FirstLetter.A_LETTER ) ).uniqueResult();
		assertEquals( id, entityEnum.getId() );
		assertEquals( FirstLetter.A_LETTER, entityEnum.getFirstLetter() );
		// delete
		assertEquals( 1, session.createSQLQuery( "DELETE FROM EntityEnum where firstLetter='A'" ).executeUpdate() );

		session.getTransaction().commit();
		session.close();

		// **************
		session = openSession();
		session.getTransaction().begin();

		// persist
		entityEnum = new EntityEnum();
		entityEnum.setLastNumber( LastNumber.NUMBER_3 );
		id = session.save( entityEnum );

		session.getTransaction().commit();
		session.close();
		session = openSession();
		session.getTransaction().begin();

		// find
		entityEnum = (EntityEnum) session.createCriteria( EntityEnum.class )
				.add( Restrictions.eq( "lastNumber", LastNumber.NUMBER_3 ) ).uniqueResult();
		assertEquals( id, entityEnum.getId() );
		assertEquals( LastNumber.NUMBER_3, entityEnum.getLastNumber() );
		// delete
		assertEquals( 1, session.createSQLQuery( "DELETE FROM EntityEnum where lastNumber='3'" ).executeUpdate() );

		session.getTransaction().commit();
		session.close();

		// **************
		session = openSession();
		session.getTransaction().begin();

		// persist
		entityEnum = new EntityEnum();
		entityEnum.setExplicitOverridingImplicit( LastNumber.NUMBER_2 );
		id = session.save( entityEnum );

		session.getTransaction().commit();
		session.close();
		session = openSession();
		session.getTransaction().begin();

		// find
		entityEnum = (EntityEnum) session.createCriteria( EntityEnum.class )
				.add( Restrictions.eq( "explicitOverridingImplicit", LastNumber.NUMBER_2 ) ).uniqueResult();
		assertEquals( id, entityEnum.getId() );
		assertEquals( LastNumber.NUMBER_2, entityEnum.getExplicitOverridingImplicit() );
		// delete
		assertEquals( 1, session.createSQLQuery( "DELETE FROM EntityEnum where explicitOverridingImplicit='NUMBER_2'" )
				.executeUpdate() );

		session.getTransaction().commit();
		session.close();

	}
	
	@Test
	@TestForIssue(jiraKey = "HHH-4699")
	@SkipForDialect(value = { Oracle8iDialect.class, AbstractHANADialect.class }, jiraKey = "HHH-8516",
			comment = "HHH-4699 was specifically for using a CHAR, but Oracle/HANA do not handle the 2nd query correctly without VARCHAR. ")
	public void testTrimmedEnumChar() throws SQLException {
		// use native SQL to insert, forcing whitespace to occur
		final Session s = openSession();
        final Connection connection = ((SessionImplementor)s).connection();
        final Statement statement = connection.createStatement();
        statement.execute("insert into EntityEnum (id, trimmed) values(1, '" + Trimmed.A.name() + "')");
        statement.execute("insert into EntityEnum (id, trimmed) values(2, '" + Trimmed.B.name() + "')");

        s.getTransaction().begin();

        // ensure EnumType can do #fromName with the trimming
        List<EntityEnum> resultList = s.createQuery("select e from EntityEnum e").list();
        assertEquals( resultList.size(), 2 );
        assertEquals( resultList.get(0).getTrimmed(), Trimmed.A );
        assertEquals( resultList.get(1).getTrimmed(), Trimmed.B );

        // ensure querying works
        final Query query = s.createQuery("select e from EntityEnum e where e.trimmed=?");
        query.setParameter( 0, Trimmed.A );
        resultList = query.list();
        assertEquals( resultList.size(), 1 );
        assertEquals( resultList.get(0).getTrimmed(), Trimmed.A );

		statement.execute( "delete from EntityEnum" );

        s.getTransaction().commit();
        s.close();
	}

	@Test
	@TestForIssue(jiraKey = "HHH-9369")
	public void testFormula() throws SQLException {
		// use native SQL to insert, forcing whitespace to occur
		final Session s = openSession();
		final Connection connection = ((SessionImplementor)s).connection();
		final Statement statement = connection.createStatement();
		statement.execute("insert into EntityEnum (id) values(1)");

		s.getTransaction().begin();

		// ensure EnumType can do #fromName with the trimming
		List<EntityEnum> resultList = s.createQuery("select e from EntityEnum e").list();
		assertEquals( resultList.size(), 1 );
		assertEquals( resultList.get(0).getFormula(), Trimmed.A );

		statement.execute( "delete from EntityEnum" );

		s.getTransaction().commit();
		s.close();
	}


	@Test
	@TestForIssue(jiraKey = "HHH-9605")
	public void testSet() throws SQLException {

		// **************
		Session session = openSession();
		session.getTransaction().begin();

		// persist
		EntityEnum entityEnum = new EntityEnum();
		entityEnum.setString( Common.B2 );
		entityEnum.getSet().add( Common.B2 );
		Serializable id = session.save( entityEnum );

		session.getTransaction().commit();
		session.close();
		session = openSession();
		session.getTransaction().begin();

		String sql = "select e from EntityEnum e where :param in elements( e.set ) ";
		Query queryObject = session.createQuery( sql );
		queryObject.setParameter( "param", Common.B2 );

		// ensure EnumType can do #fromName with the trimming
		List<EntityEnum> resultList = queryObject.list();
		assertEquals( resultList.size(), 1 );
		entityEnum = resultList.get( 0 );

		assertEquals( id, entityEnum.getId() );
		assertEquals( Common.B2, entityEnum.getSet().iterator().next() );

		// delete
		assertEquals( 1, session.createSQLQuery( "DELETE FROM set_enum" ).executeUpdate() );
		assertEquals( 1, session.createSQLQuery( "DELETE FROM EntityEnum" ).executeUpdate() );

		session.getTransaction().commit();
		session.close();
	}


	@Override
	protected Class[] getAnnotatedClasses() {
		return new Class[] { EntityEnum.class };
	}
}
