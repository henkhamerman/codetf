Refactoring Types: ['Move Class']
l/jackson/databind/ser/BeanPropertyWriter.java
package com.fasterxml.jackson.databind.ser;

import java.lang.annotation.Annotation;
import java.lang.reflect.Field;
import java.lang.reflect.Method;
import java.lang.reflect.Type;
import java.util.HashMap;

import com.fasterxml.jackson.annotation.JsonInclude;
import com.fasterxml.jackson.core.JsonGenerator;
import com.fasterxml.jackson.core.SerializableString;
import com.fasterxml.jackson.core.io.SerializedString;
import com.fasterxml.jackson.databind.*;
import com.fasterxml.jackson.databind.annotation.JacksonStdImpl;
import com.fasterxml.jackson.databind.introspect.*;
import com.fasterxml.jackson.databind.jsonFormatVisitors.JsonObjectFormatVisitor;
import com.fasterxml.jackson.databind.jsonschema.SchemaAware;
import com.fasterxml.jackson.databind.jsontype.TypeSerializer;
import com.fasterxml.jackson.databind.node.ObjectNode;
import com.fasterxml.jackson.databind.ser.impl.PropertySerializerMap;
import com.fasterxml.jackson.databind.ser.impl.UnwrappingBeanPropertyWriter;
import com.fasterxml.jackson.databind.ser.std.BeanSerializerBase;
import com.fasterxml.jackson.databind.util.Annotations;
import com.fasterxml.jackson.databind.util.NameTransformer;

/**
 * Base bean property handler class, which implements common parts of
 * reflection-based functionality for accessing a property value
 * and serializing it.
 *<p> 
 * Note that current design tries to keep instances immutable (semi-functional
 * style); mostly because these instances are exposed to application
 * code and this is to reduce likelihood of data corruption and
 * synchronization issues.
 */
@JacksonStdImpl // since 2.6. NOTE: sub-classes typically are not
public class BeanPropertyWriter extends PropertyWriter
    implements BeanProperty
{
    /**
     * Marker object used to indicate "do not serialize if empty"
     */
    public final static Object MARKER_FOR_EMPTY = JsonInclude.Include.NON_EMPTY;

    /*
    /**********************************************************
    /* Settings for accessing property value to serialize
    /**********************************************************
     */

    /**
     * Member (field, method) that represents property and allows access
     * to associated annotations.
     */
    protected final AnnotatedMember _member;

    /**
     * Annotations from context (most often, class that declares property,
     * or in case of sub-class serializer, from that sub-class)
     */
    protected final Annotations _contextAnnotations;
    
    /**
     * Type property is declared to have, either in class definition 
     * or associated annotations.
     */
    protected final JavaType _declaredType;
    
    /**
     * Accessor method used to get property value, for
     * method-accessible properties.
     * Null if and only if {@link #_field} is null.
     */
    protected final Method _accessorMethod;
    
    /**
     * Field that contains the property value for field-accessible
     * properties.
     * Null if and only if {@link #_accessorMethod} is null.
     */
    protected final Field _field;
    
    /*
    /**********************************************************
    /* Opaque internal data that bean serializer factory and
    /* bean serializers can add.
    /**********************************************************
     */

    protected HashMap<Object,Object> _internalSettings;
    
    /*
    /**********************************************************
    /* Basic property metadata: name, type, other
    /**********************************************************
     */

    /**
     * Logical name of the property; will be used as the field name
     * under which value for the property is written.
     *<p>
     * NOTE: do NOT change name of this field; it is accessed by
     * Afterburner module (until 2.4; not directly from 2.5)
     * ALSO NOTE: ... and while it really ought to be `SerializableString`,
     * changing that is also binary-incompatible change. So nope.
     */
    protected final SerializedString _name;

    /**
     * Wrapper name to use for this element, if any
     * 
     * @since 2.2
     */
    protected final PropertyName _wrapperName;

    /**
     * Type to use for locating serializer; normally same as return
     * type of the accessor method, but may be overridden by annotations.
     */
    protected final JavaType _cfgSerializationType;

    /**
     * Base type of the property, if the declared type is "non-trivial";
     * meaning it is either a structured type (collection, map, array),
     * or parameterized. Used to retain type information about contained
     * type, which is mostly necessary if type meta-data is to be
     * included.
     */
    protected JavaType _nonTrivialBaseType;

    /**
     * Additional information about property
     *
     * @since 2.3
     */
    protected final PropertyMetadata _metadata;

    /*
    /**********************************************************
    /* Serializers needed
    /**********************************************************
     */

    /**
     * Serializer to use for writing out the value: null if it can not
     * be known statically; non-null if it can.
     */
    protected JsonSerializer<Object> _serializer;

    /**
     * Serializer used for writing out null values, if any: if null,
     * null values are to be suppressed.
     */
    protected JsonSerializer<Object> _nullSerializer;

    /**
     * If property being serialized needs type information to be
     * included this is the type serializer to use.
     * Declared type (possibly augmented with annotations) of property
     * is used for determining exact mechanism to use (compared to
     * actual runtime type used for serializing actual state).
     */
    protected final TypeSerializer _typeSerializer;

    /**
     * In case serializer is not known statically (i.e. <code>_serializer</code>
     * is null), we will use a lookup structure for storing dynamically
     * resolved mapping from type(s) to serializer(s).
     */
    protected transient PropertySerializerMap _dynamicSerializers;

    /*
    /**********************************************************
    /* Filtering
    /**********************************************************
     */

    /**
     * Whether null values are to be suppressed (nothing written out if
     * value is null) or not. Note that this is a configuration value
     * during construction, and actual handling relies on setting
     * (or not) of {@link #_nullSerializer}.
     */
    protected final boolean _suppressNulls;

    /**
     * Value that is considered default value of the property; used for
     * default-value-suppression if enabled.
     */
    protected final Object _suppressableValue;

    /**
     * Alternate set of property writers used when view-based filtering
     * is available for the Bean.
     */
    protected final Class<?>[] _includeInViews;

    /*
    /**********************************************************
    /* Construction, configuration
    /**********************************************************
     */

    @SuppressWarnings("unchecked")
    public BeanPropertyWriter(BeanPropertyDefinition propDef,
            AnnotatedMember member, Annotations contextAnnotations,
            JavaType declaredType,
            JsonSerializer<?> ser, TypeSerializer typeSer, JavaType serType,
            boolean suppressNulls, Object suppressableValue)
    {
        _member = member;
        _contextAnnotations = contextAnnotations;

        _name = new SerializedString(propDef.getName());
        _wrapperName = propDef.getWrapperName();
        _metadata = propDef.getMetadata();
        _includeInViews = propDef.findViews();

        _declaredType = declaredType;
        _serializer = (JsonSerializer<Object>) ser;
        _dynamicSerializers = (ser == null) ? PropertySerializerMap.emptyForProperties() : null;
        _typeSerializer = typeSer;
        _cfgSerializationType = serType;

        if (member instanceof AnnotatedField) {
            _accessorMethod = null;
            _field = (Field) member.getMember();
        } else if (member instanceof AnnotatedMethod) {
            _accessorMethod = (Method) member.getMember();
            _field = null;
        } else {
            // 01-Dec-2014, tatu: Used to be illegal, but now explicitly allowed for virtual props
            _accessorMethod = null;
            _field = null;
        }
        _suppressNulls = suppressNulls;
        _suppressableValue = suppressableValue;

        // this will be resolved later on, unless nulls are to be suppressed
        _nullSerializer = null;
    }

    /**
     * Constructor that may be of use to virtual properties, when there is need for
     * the zero-arg ("default") constructor, and actual initialization is done
     * after constructor call.
     * 
     * @since 2.5
     */
    protected BeanPropertyWriter() {
        _member = null;
        _contextAnnotations = null;

        _name = null;
        _wrapperName = null;
        _metadata = null;
        _includeInViews = null;

        _declaredType = null;
        _serializer = null;
        _dynamicSerializers = null;
        _typeSerializer = null;
        _cfgSerializationType = null;

        _accessorMethod = null;
        _field = null;
        _suppressNulls = false;
        _suppressableValue = null;

        _nullSerializer = null;
    }

    /**
     * "Copy constructor" to be used by filtering sub-classes
     */
    protected BeanPropertyWriter(BeanPropertyWriter base) {
        this(base, base._name);
    }

    /**
     * @since 2.5
     */
    protected BeanPropertyWriter(BeanPropertyWriter base, PropertyName name)
    {
        /* 02-Dec-2014, tatu: This is a big mess, alas, what with dependency
         *   to MapperConfig to encode, and Afterburner having heartburn
         *   for SerializableString (vs SerializedString).
         *   Hope it can be resolved/reworker in 2.6 timeframe, if not for 2.5
         */
        _name = new SerializedString(name.getSimpleName());
        _wrapperName = base._wrapperName;

        _member = base._member;
        _contextAnnotations = base._contextAnnotations;
        _declaredType = base._declaredType;
        _accessorMethod = base._accessorMethod;
        _field = base._field;
        _serializer = base._serializer;
        _nullSerializer = base._nullSerializer;
        // one more thing: copy internal settings, if any (since 1.7)
        if (base._internalSettings != null) {
            _internalSettings = new HashMap<Object,Object>(base._internalSettings);
        }
        _cfgSerializationType = base._cfgSerializationType;
        _dynamicSerializers = base._dynamicSerializers;
        _suppressNulls = base._suppressNulls;
        _suppressableValue = base._suppressableValue;
        _includeInViews = base._includeInViews;
        _typeSerializer = base._typeSerializer;
        _nonTrivialBaseType = base._nonTrivialBaseType;
        _metadata = base._metadata;
    }

    protected BeanPropertyWriter(BeanPropertyWriter base, SerializedString name) {
        _name = name;
        _wrapperName = base._wrapperName;

        _member = base._member;
        _contextAnnotations = base._contextAnnotations;
        _declaredType = base._declaredType;
        _accessorMethod = base._accessorMethod;
        _field = base._field;
        _serializer = base._serializer;
        _nullSerializer = base._nullSerializer;
        if (base._internalSettings != null) {
            _internalSettings = new HashMap<Object,Object>(base._internalSettings);
        }
        _cfgSerializationType = base._cfgSerializationType;
        _dynamicSerializers = base._dynamicSerializers;
        _suppressNulls = base._suppressNulls;
        _suppressableValue = base._suppressableValue;
        _includeInViews = base._includeInViews;
        _typeSerializer = base._typeSerializer;
        _nonTrivialBaseType = base._nonTrivialBaseType;
        _metadata = base._metadata;
    }

    /**
     * @since 2.6
     */
    protected BeanPropertyWriter(BeanPropertyWriter base, TypeSerializer typeSer)
    {
        _name = base._name;
        _wrapperName = base._wrapperName;

        _member = base._member;
        _contextAnnotations = base._contextAnnotations;
        _declaredType = base._declaredType;
        _accessorMethod = base._accessorMethod;
        _field = base._field;
        _serializer = base._serializer;
        _nullSerializer = base._nullSerializer;
        _internalSettings = base._internalSettings; // safe, as per usage
        _cfgSerializationType = base._cfgSerializationType;
        _dynamicSerializers = base._dynamicSerializers;
        _suppressNulls = base._suppressNulls;
        _suppressableValue = base._suppressableValue;
        _includeInViews = base._includeInViews;
        _nonTrivialBaseType = base._nonTrivialBaseType;
        _metadata = base._metadata;

        _typeSerializer = typeSer;
    }
    
    public BeanPropertyWriter rename(NameTransformer transformer) {
        String newName = transformer.transform(_name.getValue());
        if (newName.equals(_name.toString())) {
            return this;
        }
        return new BeanPropertyWriter(this, PropertyName.construct(newName));
    }

    /**
     * Mutant factory to construct and return a new {@link BeanPropertyWriter} with
     * specified type serializer, unless this instance already has that 
     * type serializer configured.
     * 
     * @since 2.6
     */
    public BeanPropertyWriter withTypeSerializer(TypeSerializer typeSer) {
        if (typeSer == _typeSerializer) {
            return this;
        }
        return new BeanPropertyWriter(this, typeSer);
    }

    /**
     * Method called to assign value serializer for property
     * 
     * @since 2.0
     */
    public void assignSerializer(JsonSerializer<Object> ser) {
        // may need to disable check in future?
        if (_serializer != null && _serializer != ser) {
            throw new IllegalStateException("Can not override serializer");
        }
        _serializer = ser;
    }

    /**
     * Method called to assign null value serializer for property
     * 
     * @since 2.0
     */
    public void assignNullSerializer(JsonSerializer<Object> nullSer) {
        // may need to disable check in future?
        if (_nullSerializer != null && _nullSerializer != nullSer) {
            throw new IllegalStateException("Can not override null serializer");
        }
        _nullSerializer = nullSer;
    }

    /**
     * Method called create an instance that handles details of unwrapping
     * contained value.
     */
    public BeanPropertyWriter unwrappingWriter(NameTransformer unwrapper) {
        return new UnwrappingBeanPropertyWriter(this, unwrapper);
    }

    /**
     * Method called to define type to consider as "non-trivial" basetype,
     * needed for dynamic serialization resolution for complex (usually container)
     * types
     */
    public void setNonTrivialBaseType(JavaType t) {
        _nonTrivialBaseType = t;
    }

    /*
    /**********************************************************
    /* BeanProperty impl
    /**********************************************************
     */

    // Note: also part of 'PropertyWriter'
    @Override public String getName() { return _name.getValue(); }

    // Note: also part of 'PropertyWriter'
    @Override public PropertyName getFullName() { // !!! TODO: impl properly
        return new PropertyName(_name.getValue());
    }

    @Override public JavaType getType() { return _declaredType; }
    @Override public PropertyName getWrapperName() { return _wrapperName; }
    @Override public boolean isRequired() { return _metadata.isRequired(); }
    @Override public PropertyMetadata getMetadata() { return _metadata; }

    // Note: also part of 'PropertyWriter'
    @Override
    public <A extends Annotation> A getAnnotation(Class<A> acls) {
        return (_member == null) ? null : _member.getAnnotation(acls);
    }

    // Note: also part of 'PropertyWriter'
    @Override
    public <A extends Annotation> A getContextAnnotation(Class<A> acls) {
        return (_contextAnnotations == null) ? null : _contextAnnotations.get(acls);
    }

    @Override public AnnotatedMember getMember() { return _member; }

    // @since 2.3 -- needed so it can be overridden by unwrapping writer
    protected void _depositSchemaProperty(ObjectNode propertiesNode, JsonNode schemaNode) {
        propertiesNode.set(getName(), schemaNode);
    }

    /**
     * Note: will be defined in {@link BeanProperty}; as of now is not yet.
     *<p>
     * TODO: move to {@link BeanProperty} in near future, once all standard
     * implementations define it.
     * 
     * @since 2.5
     */
    public boolean isVirtual() { return false; }
    
    /*
    /**********************************************************
    /* Managing and accessing of opaque internal settings
    /* (used by extensions)
    /**********************************************************
     */
    
    /**
     * Method for accessing value of specified internal setting.
     * 
     * @return Value of the setting, if any; null if none.
     */
    public Object getInternalSetting(Object key)  {
        return (_internalSettings == null) ? null : _internalSettings.get(key);
    }
    
    /**
     * Method for setting specific internal setting to given value
     * 
     * @return Old value of the setting, if any (null if none)
     */
    public Object setInternalSetting(Object key, Object value) {
        if (_internalSettings == null) {
            _internalSettings = new HashMap<Object,Object>();
        }
        return _internalSettings.put(key, value);
    }

    /**
     * Method for removing entry for specified internal setting.
     * 
     * @return Existing value of the setting, if any (null if none)
     */
    public Object removeInternalSetting(Object key) {
        Object removed = null;
        if (_internalSettings != null) {
            removed = _internalSettings.remove(key);
            // to reduce memory usage, let's also drop the Map itself, if empty
            if (_internalSettings.size() == 0) {
                _internalSettings = null;
            }
        }
        return removed;
    }
    
    /*
    /**********************************************************
    /* Accessors
    /**********************************************************
     */

    public SerializableString getSerializedName() { return _name; }
    
    public boolean hasSerializer() { return _serializer != null; }
    public boolean hasNullSerializer() { return _nullSerializer != null; }

    /**
     * @since 2.6
     */
    public TypeSerializer getTypeSerializer() { return _typeSerializer; }

    /**
     * Accessor that will return true if this bean property has to support
     * "unwrapping"; ability to replace POJO structural wrapping with optional
     * name prefix and/or suffix (or in some cases, just removal of wrapper name).
     *<p>
     * Default implementation simply returns false.
     * 
     * @since 2.3
     */
    public boolean isUnwrapping() { return false; }
    
    public boolean willSuppressNulls() { return _suppressNulls; }

    /**
     * Method called to check to see if this property has a name that would
     * conflict with a given name.
     *
     * @since 2.6
     */
    public boolean wouldConflictWithName(PropertyName name) {
        if (_wrapperName != null) {
            return _wrapperName.equals(name);
        }
        // Bit convoluted since our support for namespaces is spotty but:
        return name.hasSimpleName(_name.getValue())
                && !name.hasNamespace();
    }
    
    // Needed by BeanSerializer#getSchema
    public JsonSerializer<Object> getSerializer() { return _serializer; }

    public JavaType getSerializationType() { return _cfgSerializationType; }

    public Class<?> getRawSerializationType() {
        return (_cfgSerializationType == null) ? null : _cfgSerializationType.getRawClass();
    }
    
    public Class<?> getPropertyType() {
        return (_accessorMethod != null) ? _accessorMethod.getReturnType() : _field.getType();
    }

    /**
     * Get the generic property type of this property writer.
     *
     * @return The property type, or null if not found.
     */
    public Type getGenericPropertyType() {
        if (_accessorMethod != null) {
            return _accessorMethod.getGenericReturnType();
        }
        if (_field != null) {
            return _field.getGenericType();
        }
        return null;
    }

    public Class<?>[] getViews() { return _includeInViews; }

    /*
    /**********************************************************
    /* PropertyWriter methods (serialization)
    /**********************************************************
     */

    /**
     * Method called to access property that this bean stands for, from
     * within given bean, and to serialize it as a JSON Object field
     * using appropriate serializer.
     */
    @Override
    public void serializeAsField(Object bean, JsonGenerator gen, SerializerProvider prov) throws Exception
    {
        // inlined 'get()'
        final Object value = (_accessorMethod == null) ? _field.get(bean) : _accessorMethod.invoke(bean);

        // Null handling is bit different, check that first
        if (value == null) {
            if (_nullSerializer != null) {
                gen.writeFieldName(_name);
                _nullSerializer.serialize(null, gen, prov);
            }
            return;
        }
        // then find serializer to use
        JsonSerializer<Object> ser = _serializer;
        if (ser == null) {
            Class<?> cls = value.getClass();
            PropertySerializerMap m = _dynamicSerializers;
            ser = m.serializerFor(cls);
            if (ser == null) {
                ser = _findAndAddDynamic(m, cls, prov);
            }
        }
        // and then see if we must suppress certain values (default, empty)
        if (_suppressableValue != null) {
            if (MARKER_FOR_EMPTY == _suppressableValue) {
                if (ser.isEmpty(prov, value)) {
                    return;
                }
            } else if (_suppressableValue.equals(value)) {
                return;
            }
        }
        // For non-nulls: simple check for direct cycles
        if (value == bean) {
            // three choices: exception; handled by call; or pass-through
            if (_handleSelfReference(bean, gen, prov, ser)) {
                return;
            }
        }
        gen.writeFieldName(_name);
        if (_typeSerializer == null) {
            ser.serialize(value, gen, prov);
        } else {
            ser.serializeWithType(value, gen, prov, _typeSerializer);
        }
    }

    /**
     * Method called to indicate that serialization of a field was omitted
     * due to filtering, in cases where backend data format does not allow
     * basic omission.
     * 
     * @since 2.3
     */
    @Override
    public void serializeAsOmittedField(Object bean, JsonGenerator gen, SerializerProvider prov) throws Exception
    {
        if (!gen.canOmitFields()) {
            gen.writeOmittedField(_name.getValue());
        }
    }
    
    /**
     * Alternative to {@link #serializeAsField} that is used when a POJO
     * is serialized as JSON Array; the difference is that no field names
     * are written.
     * 
     * @since 2.3
     */
    @Override
    public void serializeAsElement(Object bean, JsonGenerator gen, SerializerProvider prov)
        throws Exception
    {
        // inlined 'get()'
        final Object value = (_accessorMethod == null) ? _field.get(bean) : _accessorMethod.invoke(bean);
        if (value == null) { // nulls need specialized handling
            if (_nullSerializer != null) {
                _nullSerializer.serialize(null, gen, prov);
            } else { // can NOT suppress entries in tabular output
                gen.writeNull();
            }
            return;
        }
        // otherwise find serializer to use
        JsonSerializer<Object> ser = _serializer;
        if (ser == null) {
            Class<?> cls = value.getClass();
            PropertySerializerMap map = _dynamicSerializers;
            ser = map.serializerFor(cls);
            if (ser == null) {
                ser = _findAndAddDynamic(map, cls, prov);
            }
        }
        // and then see if we must suppress certain values (default, empty)
        if (_suppressableValue != null) {
            if (MARKER_FOR_EMPTY == _suppressableValue) {
                if (ser.isEmpty(prov, value)) { // can NOT suppress entries in tabular output
                    serializeAsPlaceholder(bean, gen, prov);
                    return;
                }
            } else if (_suppressableValue.equals(value)) { // can NOT suppress entries in tabular output
                serializeAsPlaceholder(bean, gen, prov);
                return;
            }
        }
        // For non-nulls: simple check for direct cycles
        if (value == bean) {
            if (_handleSelfReference(bean, gen, prov, ser)) {
                return;
            }
        }
        if (_typeSerializer == null) {
            ser.serialize(value, gen, prov);
        } else {
            ser.serializeWithType(value, gen, prov, _typeSerializer);
        }
    }

    /**
     * Method called to serialize a placeholder used in tabular output when
     * real value is not to be included (is filtered out), but when we need
     * an entry so that field indexes will not be off. Typically this should
     * output null or empty String, depending on datatype.
     * 
     * @since 2.1
     */
    @Override
    public void serializeAsPlaceholder(Object bean, JsonGenerator gen, SerializerProvider prov)
        throws Exception
    {
        if (_nullSerializer != null) {
            _nullSerializer.serialize(null, gen, prov);
        } else {
            gen.writeNull();
        }
    }
    
    /*
    /**********************************************************
    /* PropertyWriter methods (schema generation)
    /**********************************************************
     */

    // Also part of BeanProperty implementation
    @Override
    public void depositSchemaProperty(JsonObjectFormatVisitor v)
        throws JsonMappingException
    {
        if (v != null) {
            if (isRequired()) {
                v.property(this); 
            } else {
                v.optionalProperty(this);
            }
        }
    }

    // // // Legacy support for JsonFormatVisitable

    /**
     * Attempt to add the output of the given {@link BeanPropertyWriter} in the given {@link ObjectNode}.
     * Otherwise, add the default schema {@link JsonNode} in place of the writer's output
     * 
     * @param propertiesNode Node which the given property would exist within
     * @param provider Provider that can be used for accessing dynamic aspects of serialization
     *  processing
     */
    @Override
    @Deprecated
    public void depositSchemaProperty(ObjectNode propertiesNode, SerializerProvider provider)
        throws JsonMappingException
    {
        JavaType propType = getSerializationType();
        // 03-Dec-2010, tatu: SchemaAware REALLY should use JavaType, but alas it doesn't...
        Type hint = (propType == null) ? getGenericPropertyType() : propType.getRawClass();
        JsonNode schemaNode;
        // Maybe it already has annotated/statically configured serializer?
        JsonSerializer<Object> ser = getSerializer();
        if (ser == null) { // nope
            ser = provider.findValueSerializer(getType(), this);
        }
        boolean isOptional = !isRequired();
        if (ser instanceof SchemaAware) {
            schemaNode =  ((SchemaAware) ser).getSchema(provider, hint, isOptional) ;
        } else {  
            schemaNode = com.fasterxml.jackson.databind.jsonschema.JsonSchema.getDefaultSchemaNode(); 
        }
        _depositSchemaProperty(propertiesNode, schemaNode);
    }
    
    /*
    /**********************************************************
    /* Helper methods
    /**********************************************************
     */
    
    protected JsonSerializer<Object> _findAndAddDynamic(PropertySerializerMap map,
            Class<?> type, SerializerProvider provider) throws JsonMappingException
    {
        PropertySerializerMap.SerializerAndMapResult result;
        if (_nonTrivialBaseType != null) {
            JavaType t = provider.constructSpecializedType(_nonTrivialBaseType, type);
            result = map.findAndAddPrimarySerializer(t, provider, this);
        } else {
            result = map.findAndAddPrimarySerializer(type, provider, this);
        }
        // did we get a new map of serializers? If so, start using it
        if (map != result.map) {
            _dynamicSerializers = result.map;
        }
        return result.serializer;
    }
    
    /**
     * Method that can be used to access value of the property this
     * Object describes, from given bean instance.
     *<p>
     * Note: method is final as it should not need to be overridden -- rather,
     * calling method(s) ({@link #serializeAsField}) should be overridden
     * to change the behavior
     */
    public final Object get(Object bean) throws Exception {
        return (_accessorMethod == null) ? _field.get(bean) : _accessorMethod.invoke(bean);
    }

    /**
     * Method called to handle a direct self-reference through this property.
     * Method can choose to indicate an error by throwing {@link JsonMappingException};
     * fully handle serialization (and return true); or indicate that it should be
     * serialized normally (return false).
     *<p>
     * Default implementation will throw {@link JsonMappingException} if
     * {@link SerializationFeature#FAIL_ON_SELF_REFERENCES} is enabled;
     * or return <code>false</code> if it is disabled.
     *
     * @return True if method fully handled self-referential value; false if not (caller
     *    is to handle it) or {@link JsonMappingException} if there is no way handle it
     */
    protected boolean _handleSelfReference(Object bean, JsonGenerator gen, SerializerProvider prov, JsonSerializer<?> ser)
            throws JsonMappingException {
        if (prov.isEnabled(SerializationFeature.FAIL_ON_SELF_REFERENCES)
                && !ser.usesObjectId()) {
            // 05-Feb-2013, tatu: Usually a problem, but NOT if we are handling
            //    object id; this may be the case for BeanSerializers at least.
            // 13-Feb-2014, tatu: another possible ok case: custom serializer (something
            //   OTHER than {@link BeanSerializerBase}
            if (ser instanceof BeanSerializerBase) {
                throw new JsonMappingException("Direct self-reference leading to cycle");
            }
        }
        return false;
    }

    @Override
    public String toString() {
        StringBuilder sb = new StringBuilder(40);
        sb.append("property '").append(getName()).append("' (");
        if (_accessorMethod != null) {
            sb.append("via method ").append(_accessorMethod.getDeclaringClass().getName()).append("#").append(_accessorMethod.getName());
        } else if (_field != null) {
            sb.append("field \"").append(_field.getDeclaringClass().getName()).append("#").append(_field.getName());
        } else {
            sb.append("virtual");
        }
        if (_serializer == null) {
            sb.append(", no static serializer");
        } else {
            sb.append(", static serializer of type "+_serializer.getClass().getName());
        }
        sb.append(')');
        return sb.toString();
    }
}


File: src/main/java/com/fasterxml/jackson/databind/ser/BeanSerializerFactory.java
package com.fasterxml.jackson.databind.ser;

import java.util.*;

import com.fasterxml.jackson.annotation.ObjectIdGenerator;
import com.fasterxml.jackson.annotation.ObjectIdGenerators;
import com.fasterxml.jackson.annotation.JsonTypeInfo.As;
import com.fasterxml.jackson.databind.*;
import com.fasterxml.jackson.databind.cfg.SerializerFactoryConfig;
import com.fasterxml.jackson.databind.introspect.*;
import com.fasterxml.jackson.databind.jsontype.NamedType;
import com.fasterxml.jackson.databind.jsontype.TypeResolverBuilder;
import com.fasterxml.jackson.databind.jsontype.TypeSerializer;
import com.fasterxml.jackson.databind.ser.impl.FilteredBeanPropertyWriter;
import com.fasterxml.jackson.databind.ser.impl.ObjectIdWriter;
import com.fasterxml.jackson.databind.ser.impl.PropertyBasedObjectIdGenerator;
import com.fasterxml.jackson.databind.ser.std.MapSerializer;
import com.fasterxml.jackson.databind.ser.std.StdDelegatingSerializer;
import com.fasterxml.jackson.databind.type.*;
import com.fasterxml.jackson.databind.util.ArrayBuilders;
import com.fasterxml.jackson.databind.util.ClassUtil;
import com.fasterxml.jackson.databind.util.Converter;

/**
 * Factory class that can provide serializers for any regular Java beans
 * (as defined by "having at least one get method recognizable as bean
 * accessor" -- where {@link Object#getClass} does not count);
 * as well as for "standard" JDK types. Latter is achieved
 * by delegating calls to {@link BasicSerializerFactory} 
 * to find serializers both for "standard" JDK types (and in some cases,
 * sub-classes as is the case for collection classes like
 * {@link java.util.List}s and {@link java.util.Map}s) and bean (value)
 * classes.
 *<p>
 * Note about delegating calls to {@link BasicSerializerFactory}:
 * although it would be nicer to use linear delegation
 * for construction (to essentially dispatch all calls first to the
 * underlying {@link BasicSerializerFactory}; or alternatively after
 * failing to provide bean-based serializer}, there is a problem:
 * priority levels for detecting standard types are mixed. That is,
 * we want to check if a type is a bean after some of "standard" JDK
 * types, but before the rest.
 * As a result, "mixed" delegation used, and calls are NOT done using
 * regular {@link SerializerFactory} interface but rather via
 * direct calls to {@link BasicSerializerFactory}.
 *<p>
 * Finally, since all caching is handled by the serializer provider
 * (not factory) and there is no configurability, this
 * factory is stateless.
 * This means that a global singleton instance can be used.
 */
public class BeanSerializerFactory
    extends BasicSerializerFactory
    implements java.io.Serializable // since 2.1
{
    private static final long serialVersionUID = 1;

    /**
     * Like {@link BasicSerializerFactory}, this factory is stateless, and
     * thus a single shared global (== singleton) instance can be used
     * without thread-safety issues.
     */
    public final static BeanSerializerFactory instance = new BeanSerializerFactory(null);

    /*
    /**********************************************************
    /* Life-cycle: creation, configuration
    /**********************************************************
     */

    /**
     * Constructor for creating instances with specified configuration.
     */
    protected BeanSerializerFactory(SerializerFactoryConfig config)
    {
        super(config);
    }
    
    /**
     * Method used by module registration functionality, to attach additional
     * serializer providers into this serializer factory. This is typically
     * handled by constructing a new instance with additional serializers,
     * to ensure thread-safe access.
     */
    @Override
    public SerializerFactory withConfig(SerializerFactoryConfig config)
    {
        if (_factoryConfig == config) {
            return this;
        }
        /* 22-Nov-2010, tatu: Handling of subtypes is tricky if we do immutable-with-copy-ctor;
         *    and we pretty much have to here either choose between losing subtype instance
         *    when registering additional serializers, or losing serializers.
         *    Instead, let's actually just throw an error if this method is called when subtype
         *    has not properly overridden this method; this to indicate problem as soon as possible.
         */
        if (getClass() != BeanSerializerFactory.class) {
            throw new IllegalStateException("Subtype of BeanSerializerFactory ("+getClass().getName()
                    +") has not properly overridden method 'withAdditionalSerializers': can not instantiate subtype with "
                    +"additional serializer definitions");
        }
        return new BeanSerializerFactory(config);
    }

    @Override
    protected Iterable<Serializers> customSerializers() {
        return _factoryConfig.serializers();
    }
    
    /*
    /**********************************************************
    /* SerializerFactory impl
    /**********************************************************
     */

    /**
     * Main serializer constructor method. We will have to be careful
     * with respect to ordering of various method calls: essentially
     * we want to reliably figure out which classes are standard types,
     * and which are beans. The problem is that some bean Classes may
     * implement standard interfaces (say, {@link java.lang.Iterable}.
     *<p>
     * Note: sub-classes may choose to complete replace implementation,
     * if they want to alter priority of serializer lookups.
     */
    @Override
    @SuppressWarnings("unchecked")
    public JsonSerializer<Object> createSerializer(SerializerProvider prov,
            JavaType origType)
        throws JsonMappingException
    {
        // Very first thing, let's check if there is explicit serializer annotation:
        final SerializationConfig config = prov.getConfig();
        BeanDescription beanDesc = config.introspect(origType);
        JsonSerializer<?> ser = findSerializerFromAnnotation(prov, beanDesc.getClassInfo());
        if (ser != null) {
            return (JsonSerializer<Object>) ser;
        }
        boolean staticTyping;
        // Next: we may have annotations that further define types to use...
        JavaType type = modifyTypeByAnnotation(config, beanDesc.getClassInfo(), origType);
        if (type == origType) { // no changes, won't force static typing
            staticTyping = false;
        } else { // changes; assume static typing; plus, need to re-introspect if class differs
            staticTyping = true;
            if (!type.hasRawClass(origType.getRawClass())) {
                beanDesc = config.introspect(type);
            }
        }
        // Slight detour: do we have a Converter to consider?
        Converter<Object,Object> conv = beanDesc.findSerializationConverter();
        if (conv == null) { // no, simple
            return (JsonSerializer<Object>) _createSerializer2(prov, type, beanDesc, staticTyping);
        }
        JavaType delegateType = conv.getOutputType(prov.getTypeFactory());
        
        // One more twist, as per [Issue#288]; probably need to get new BeanDesc
        if (!delegateType.hasRawClass(type.getRawClass())) {
            beanDesc = config.introspect(delegateType);
            // [#359]: explicitly check (again) for @JsonSerializer...
            ser = findSerializerFromAnnotation(prov, beanDesc.getClassInfo());
        }
        // [databind#731]: Should skip if nominally java.lang.Object
        if (ser == null && !delegateType.isJavaLangObject()) {
            ser = _createSerializer2(prov, delegateType, beanDesc, true);
        }
        return new StdDelegatingSerializer(conv, delegateType, ser);
    }

    protected JsonSerializer<?> _createSerializer2(SerializerProvider prov,
            JavaType type, BeanDescription beanDesc, boolean staticTyping)
        throws JsonMappingException
    {
        // Then JsonSerializable, @JsonValue etc:
        JsonSerializer<?> ser = findSerializerByAnnotations(prov, type, beanDesc);
        if (ser != null) {
            return ser;
        }
        final SerializationConfig config = prov.getConfig();
        
        // Container types differ from non-container types
        // (note: called method checks for module-provided serializers)
        if (type.isContainerType()) {
            if (!staticTyping) {
                staticTyping = usesStaticTyping(config, beanDesc, null);
                // [Issue#23]: Need to figure out how to force passed parameterization
                //  to stick...
                /*
                if (property == null) {
                    JavaType t = origType.getContentType();
                    if (t != null && !t.hasRawClass(Object.class)) {
                        staticTyping = true;
                    }
                }
                */
            }
            // 03-Aug-2012, tatu: As per [Issue#40], may require POJO serializer...
            ser =  buildContainerSerializer(prov, type, beanDesc, staticTyping);
            // Will return right away, since called method does post-processing:
            if (ser != null) {
                return ser;
            }
        } else {
            // Modules may provide serializers of POJO types:
            for (Serializers serializers : customSerializers()) {
                ser = serializers.findSerializer(config, type, beanDesc);
                if (ser != null) {
                    break;
                }
            }
        }
        
        // Otherwise, we will check "primary types"; both marker types that
        // indicate specific handling (JsonSerializable), or main types that have
        // precedence over container types
        if (ser == null) {
            ser = findSerializerByLookup(type, config, beanDesc, staticTyping);
            if (ser == null) {
                ser = findSerializerByPrimaryType(prov, type, beanDesc, staticTyping);
                if (ser == null) {
                    // And this is where this class comes in: if type is not a
                    // known "primary JDK type", perhaps it's a bean? We can still
                    // get a null, if we can't find a single suitable bean property.
                    ser = findBeanSerializer(prov, type, beanDesc);
                    // Finally: maybe we can still deal with it as an implementation of some basic JDK interface?
                    if (ser == null) {
                        ser = findSerializerByAddonType(config, type, beanDesc, staticTyping);
                        // 18-Sep-2014, tatu: Actually, as per [jackson-databind#539], need to get
                        //   'unknown' serializer assigned earlier, here, so that it gets properly
                        //   post-processed
                        if (ser == null) {
                            ser = prov.getUnknownTypeSerializer(beanDesc.getBeanClass());
                        }
                    }
                }
            }
        }
        if (ser != null) {
            // [Issue#120]: Allow post-processing
            if (_factoryConfig.hasSerializerModifiers()) {
                for (BeanSerializerModifier mod : _factoryConfig.serializerModifiers()) {
                    ser = mod.modifySerializer(config, beanDesc, ser);
                }
            }
        }
        return ser;
    }
    
    /*
    /**********************************************************
    /* Other public methods that are not part of
    /* JsonSerializerFactory API
    /**********************************************************
     */

    /**
     * Method that will try to construct a {@link BeanSerializer} for
     * given class. Returns null if no properties are found.
     */
    public JsonSerializer<Object> findBeanSerializer(SerializerProvider prov, JavaType type, BeanDescription beanDesc)
        throws JsonMappingException
    {
        // First things first: we know some types are not beans...
        if (!isPotentialBeanType(type.getRawClass())) {
            // 03-Aug-2012, tatu: Except we do need to allow serializers for Enums,
            //   as per [Issue#24]
            if (!type.isEnumType()) {
                return null;
            }
        }
        return constructBeanSerializer(prov, beanDesc);
    }

    /**
     * Method called to create a type information serializer for values of given
     * non-container property
     * if one is needed. If not needed (no polymorphic handling configured), should
     * return null.
     *
     * @param baseType Declared type to use as the base type for type information serializer
     * 
     * @return Type serializer to use for property values, if one is needed; null if not.
     */
    public TypeSerializer findPropertyTypeSerializer(JavaType baseType,
            SerializationConfig config, AnnotatedMember accessor)
        throws JsonMappingException
    {
        AnnotationIntrospector ai = config.getAnnotationIntrospector();
        TypeResolverBuilder<?> b = ai.findPropertyTypeResolver(config, accessor, baseType);        
        TypeSerializer typeSer;

        // Defaulting: if no annotations on member, check value class
        if (b == null) {
            typeSer = createTypeSerializer(config, baseType);
        } else {
            Collection<NamedType> subtypes = config.getSubtypeResolver().collectAndResolveSubtypesByClass(
                    config, accessor, baseType);
            typeSer = b.buildTypeSerializer(config, baseType, subtypes);
        }
        return typeSer;
    }

    /**
     * Method called to create a type information serializer for values of given
     * container property
     * if one is needed. If not needed (no polymorphic handling configured), should
     * return null.
     *
     * @param containerType Declared type of the container to use as the base type for type information serializer
     * 
     * @return Type serializer to use for property value contents, if one is needed; null if not.
     */    
    public TypeSerializer findPropertyContentTypeSerializer(JavaType containerType,
            SerializationConfig config, AnnotatedMember accessor)
        throws JsonMappingException
    {
        JavaType contentType = containerType.getContentType();
        AnnotationIntrospector ai = config.getAnnotationIntrospector();
        TypeResolverBuilder<?> b = ai.findPropertyContentTypeResolver(config, accessor, containerType);        
        TypeSerializer typeSer;

        // Defaulting: if no annotations on member, check value class
        if (b == null) {
            typeSer = createTypeSerializer(config, contentType);
        } else {
            Collection<NamedType> subtypes = config.getSubtypeResolver().collectAndResolveSubtypesByClass(config,
                    accessor, contentType);
            typeSer = b.buildTypeSerializer(config, contentType, subtypes);
        }
        return typeSer;
    }

    /*
    /**********************************************************
    /* Overridable non-public factory methods
    /**********************************************************
     */

    /**
     * Method called to construct serializer for serializing specified bean type.
     * 
     * @since 2.1
     */
    @SuppressWarnings("unchecked")
    protected JsonSerializer<Object> constructBeanSerializer(SerializerProvider prov,
            BeanDescription beanDesc)
        throws JsonMappingException
    {
        // 13-Oct-2010, tatu: quick sanity check: never try to create bean serializer for plain Object
        // 05-Jul-2012, tatu: ... but we should be able to just return "unknown type" serializer, right?
        if (beanDesc.getBeanClass() == Object.class) {
            return prov.getUnknownTypeSerializer(Object.class);
//            throw new IllegalArgumentException("Can not create bean serializer for Object.class");
        }
        final SerializationConfig config = prov.getConfig();
        BeanSerializerBuilder builder = constructBeanSerializerBuilder(beanDesc);
        builder.setConfig(config);

        // First: any detectable (auto-detect, annotations) properties to serialize?
        List<BeanPropertyWriter> props = findBeanProperties(prov, beanDesc, builder);
        if (props == null) {
            props = new ArrayList<BeanPropertyWriter>();
        } else {
            props = removeOverlappingTypeIds(prov, beanDesc, builder, props);
        }
        
        // [databind#638]: Allow injection of "virtual" properties:
        prov.getAnnotationIntrospector().findAndAddVirtualProperties(config, beanDesc.getClassInfo(), props);

        // [JACKSON-440] Need to allow modification bean properties to serialize:
        if (_factoryConfig.hasSerializerModifiers()) {
            for (BeanSerializerModifier mod : _factoryConfig.serializerModifiers()) {
                props = mod.changeProperties(config, beanDesc, props);
            }
        }

        // Any properties to suppress?
        props = filterBeanProperties(config, beanDesc, props);

        // [JACKSON-440] Need to allow reordering of properties to serialize
        if (_factoryConfig.hasSerializerModifiers()) {
            for (BeanSerializerModifier mod : _factoryConfig.serializerModifiers()) {
                props = mod.orderProperties(config, beanDesc, props);
            }
        }

        /* And if Object Id is needed, some preparation for that as well: better
         * do before view handling, mostly for the custom id case which needs
         * access to a property
         */
        builder.setObjectIdWriter(constructObjectIdHandler(prov, beanDesc, props));
        
        builder.setProperties(props);
        builder.setFilterId(findFilterId(config, beanDesc));
        
        AnnotatedMember anyGetter = beanDesc.findAnyGetter();
        if (anyGetter != null) {
            if (config.canOverrideAccessModifiers()) {
                anyGetter.fixAccess();
            }
            JavaType type = anyGetter.getType(beanDesc.bindingsForBeanType());
            // copied from BasicSerializerFactory.buildMapSerializer():
            boolean staticTyping = config.isEnabled(MapperFeature.USE_STATIC_TYPING);
            JavaType valueType = type.getContentType();
            TypeSerializer typeSer = createTypeSerializer(config, valueType);
            // last 2 nulls; don't know key, value serializers (yet)
            // 23-Feb-2015, tatu: As per [#705], need to support custom serializers
            JsonSerializer<?> anySer = findSerializerFromAnnotation(prov, anyGetter);
            if (anySer == null) {
                // TODO: support '@JsonIgnoreProperties' with any setter?
                anySer = MapSerializer.construct(/* ignored props*/ null, type, staticTyping,
                        typeSer, null, null, /*filterId*/ null);
            }
            // TODO: can we find full PropertyName?
            PropertyName name = PropertyName.construct(anyGetter.getName());
            BeanProperty.Std anyProp = new BeanProperty.Std(name, valueType, null,
                    beanDesc.getClassAnnotations(), anyGetter, PropertyMetadata.STD_OPTIONAL);
            builder.setAnyGetter(new AnyGetterWriter(anyProp, anyGetter, anySer));
        }
        // Next: need to gather view information, if any:
        processViews(config, builder);

        // Finally: let interested parties mess with the result bit more...
        if (_factoryConfig.hasSerializerModifiers()) {
            for (BeanSerializerModifier mod : _factoryConfig.serializerModifiers()) {
                builder = mod.updateBuilder(config, beanDesc, builder);
            }
        }
        
        JsonSerializer<Object> ser = (JsonSerializer<Object>) builder.build();
        
        if (ser == null) {
            // If we get this far, there were no properties found, so no regular BeanSerializer
            // would be constructed. But, couple of exceptions.
            // First: if there are known annotations, just create 'empty bean' serializer
            if (beanDesc.hasKnownClassAnnotations()) {
                return builder.createDummy();
            }
        }
        return ser;
    }

    protected ObjectIdWriter constructObjectIdHandler(SerializerProvider prov,
            BeanDescription beanDesc, List<BeanPropertyWriter> props)
        throws JsonMappingException
    {
        ObjectIdInfo objectIdInfo = beanDesc.getObjectIdInfo();
        if (objectIdInfo == null) {
            return null;
        }
        ObjectIdGenerator<?> gen;
        Class<?> implClass = objectIdInfo.getGeneratorType();

        // Just one special case: Property-based generator is trickier
        if (implClass == ObjectIdGenerators.PropertyGenerator.class) { // most special one, needs extra work
            String propName = objectIdInfo.getPropertyName().getSimpleName();
            BeanPropertyWriter idProp = null;

            for (int i = 0, len = props.size() ;; ++i) {
                if (i == len) {
                    throw new IllegalArgumentException("Invalid Object Id definition for "+beanDesc.getBeanClass().getName()
                            +": can not find property with name '"+propName+"'");
                }
                BeanPropertyWriter prop = props.get(i);
                if (propName.equals(prop.getName())) {
                    idProp = prop;
                    /* Let's force it to be the first property to output
                     * (although it may still get rearranged etc)
                     */
                    if (i > 0) {
                        props.remove(i);
                        props.add(0, idProp);
                    }
                    break;
                }
            }
            JavaType idType = idProp.getType();
            gen = new PropertyBasedObjectIdGenerator(objectIdInfo, idProp);
            // one more thing: must ensure that ObjectIdWriter does not actually write the value:
            return ObjectIdWriter.construct(idType, (PropertyName) null, gen, objectIdInfo.getAlwaysAsId());
            
        } 
        // other types are simpler
        JavaType type = prov.constructType(implClass);
        // Could require type to be passed explicitly, but we should be able to find it too:
        JavaType idType = prov.getTypeFactory().findTypeParameters(type, ObjectIdGenerator.class)[0];
        gen = prov.objectIdGeneratorInstance(beanDesc.getClassInfo(), objectIdInfo);
        return ObjectIdWriter.construct(idType, objectIdInfo.getPropertyName(), gen,
                objectIdInfo.getAlwaysAsId());
    }

    /**
     * Method called to construct a filtered writer, for given view
     * definitions. Default implementation constructs filter that checks
     * active view type to views property is to be included in.
     */
    protected BeanPropertyWriter constructFilteredBeanWriter(BeanPropertyWriter writer,
            Class<?>[] inViews)
    {
        return FilteredBeanPropertyWriter.constructViewBased(writer, inViews);
    }
    
    protected PropertyBuilder constructPropertyBuilder(SerializationConfig config,
            BeanDescription beanDesc)
    {
        return new PropertyBuilder(config, beanDesc);
    }

    protected BeanSerializerBuilder constructBeanSerializerBuilder(BeanDescription beanDesc) {
        return new BeanSerializerBuilder(beanDesc);
    }
    
    /*
    /**********************************************************
    /* Overridable non-public introspection methods
    /**********************************************************
     */
    
    /**
     * Helper method used to skip processing for types that we know
     * can not be (i.e. are never consider to be) beans: 
     * things like primitives, Arrays, Enums, and proxy types.
     *<p>
     * Note that usually we shouldn't really be getting these sort of
     * types anyway; but better safe than sorry.
     */
    protected boolean isPotentialBeanType(Class<?> type)
    {
        return (ClassUtil.canBeABeanType(type) == null) && !ClassUtil.isProxyType(type);
    }

    /**
     * Method used to collect all actual serializable properties.
     * Can be overridden to implement custom detection schemes.
     */
    protected List<BeanPropertyWriter> findBeanProperties(SerializerProvider prov,
            BeanDescription beanDesc, BeanSerializerBuilder builder)
        throws JsonMappingException
    {
        List<BeanPropertyDefinition> properties = beanDesc.findProperties();
        final SerializationConfig config = prov.getConfig();

        // [JACKSON-429]: ignore specified types
        removeIgnorableTypes(config, beanDesc, properties);
        
        // and possibly remove ones without matching mutator...
        if (config.isEnabled(MapperFeature.REQUIRE_SETTERS_FOR_GETTERS)) {
            removeSetterlessGetters(config, beanDesc, properties);
        }
        
        // nothing? can't proceed (caller may or may not throw an exception)
        if (properties.isEmpty()) {
            return null;
        }
        // null is for value type serializer, which we don't have access to from here (ditto for bean prop)
        boolean staticTyping = usesStaticTyping(config, beanDesc, null);
        PropertyBuilder pb = constructPropertyBuilder(config, beanDesc);
        
        ArrayList<BeanPropertyWriter> result = new ArrayList<BeanPropertyWriter>(properties.size());
        TypeBindings typeBind = beanDesc.bindingsForBeanType();
        for (BeanPropertyDefinition property : properties) {
            final AnnotatedMember accessor = property.getAccessor();
            // [JACKSON-762]: type id? Requires special handling:
            if (property.isTypeId()) {
                if (accessor != null) { // only add if we can access... but otherwise?
                    if (config.canOverrideAccessModifiers()) {
                        accessor.fixAccess();
                    }
                    builder.setTypeId(accessor);
                }
                continue;
            }
            // [JACKSON-235]: suppress writing of back references
            AnnotationIntrospector.ReferenceProperty refType = property.findReferenceType();
            if (refType != null && refType.isBackReference()) {
                continue;
            }
            if (accessor instanceof AnnotatedMethod) {
                result.add(_constructWriter(prov, property, typeBind, pb, staticTyping, (AnnotatedMethod) accessor));
            } else {
                result.add(_constructWriter(prov, property, typeBind, pb, staticTyping, (AnnotatedField) accessor));
            }
        }
        return result;
    }

    /*
    /**********************************************************
    /* Overridable non-public methods for manipulating bean properties
    /**********************************************************
     */
    
    /**
     * Overridable method that can filter out properties. Default implementation
     * checks annotations class may have.
     */
    protected List<BeanPropertyWriter> filterBeanProperties(SerializationConfig config,
            BeanDescription beanDesc, List<BeanPropertyWriter> props)
    {
        AnnotationIntrospector intr = config.getAnnotationIntrospector();
        AnnotatedClass ac = beanDesc.getClassInfo();
        String[] ignored = intr.findPropertiesToIgnore(ac, true);
        if (ignored != null && ignored.length > 0) {
            HashSet<String> ignoredSet = ArrayBuilders.arrayToSet(ignored);
            Iterator<BeanPropertyWriter> it = props.iterator();
            while (it.hasNext()) {
                if (ignoredSet.contains(it.next().getName())) {
                    it.remove();
                }
            }
        }
        return props;
    }

    /**
     * Method called to handle view information for constructed serializer,
     * based on bean property writers.
     *<p>
     * Note that this method is designed to be overridden by sub-classes
     * if they want to provide custom view handling. As such it is not
     * considered an internal implementation detail, and will be supported
     * as part of API going forward.
     */
    protected void processViews(SerializationConfig config, BeanSerializerBuilder builder)
    {
        // [JACKSON-232]: whether non-annotated fields are included by default or not is configurable
        List<BeanPropertyWriter> props = builder.getProperties();
        boolean includeByDefault = config.isEnabled(MapperFeature.DEFAULT_VIEW_INCLUSION);
        final int propCount = props.size();
        int viewsFound = 0;
        BeanPropertyWriter[] filtered = new BeanPropertyWriter[propCount];
        // Simple: view information is stored within individual writers, need to combine:
        for (int i = 0; i < propCount; ++i) {
            BeanPropertyWriter bpw = props.get(i);
            Class<?>[] views = bpw.getViews();
            if (views == null) { // no view info? include or exclude by default?
                if (includeByDefault) {
                    filtered[i] = bpw;
                }
            } else {
                ++viewsFound;
                filtered[i] = constructFilteredBeanWriter(bpw, views);
            }
        }
        // minor optimization: if no view info, include-by-default, can leave out filtering info altogether:
        if (includeByDefault && viewsFound == 0) {
            return;
        }
        builder.setFilteredProperties(filtered);
    }

    /**
     * Method that will apply by-type limitations (as per [JACKSON-429]);
     * by default this is based on {@link com.fasterxml.jackson.annotation.JsonIgnoreType}
     * annotation but can be supplied by module-provided introspectors too.
     */
    protected void removeIgnorableTypes(SerializationConfig config, BeanDescription beanDesc,
            List<BeanPropertyDefinition> properties)
    {
        AnnotationIntrospector intr = config.getAnnotationIntrospector();
        HashMap<Class<?>,Boolean> ignores = new HashMap<Class<?>,Boolean>();
        Iterator<BeanPropertyDefinition> it = properties.iterator();
        while (it.hasNext()) {
            BeanPropertyDefinition property = it.next();
            AnnotatedMember accessor = property.getAccessor();
            if (accessor == null) {
                it.remove();
                continue;
            }
            Class<?> type = accessor.getRawType();
            Boolean result = ignores.get(type);
            if (result == null) {
                BeanDescription desc = config.introspectClassAnnotations(type);
                AnnotatedClass ac = desc.getClassInfo();
                result = intr.isIgnorableType(ac);
                // default to false, non-ignorable
                if (result == null) {
                    result = Boolean.FALSE;
                }
                ignores.put(type, result);
            }
            // lotsa work, and yes, it is ignorable type, so:
            if (result.booleanValue()) {
                it.remove();
            }
        }
    }

    /**
     * Helper method that will remove all properties that do not have a mutator.
     */
    protected void removeSetterlessGetters(SerializationConfig config, BeanDescription beanDesc,
            List<BeanPropertyDefinition> properties)
    {
        Iterator<BeanPropertyDefinition> it = properties.iterator();
        while (it.hasNext()) {
            BeanPropertyDefinition property = it.next();
            // one caveat: as per [JACKSON-806], only remove implicit properties;
            // explicitly annotated ones should remain
            if (!property.couldDeserialize() && !property.isExplicitlyIncluded()) {
                it.remove();
            }
        }
    }

    /**
     * Helper method called to ensure that we do not have "duplicate" type ids.
     * Added to resolve [databind#222]
     *
     * @since 2.6
     */
    protected List<BeanPropertyWriter> removeOverlappingTypeIds(SerializerProvider prov,
            BeanDescription beanDesc, BeanSerializerBuilder builder,
            List<BeanPropertyWriter> props)
    {
        for (int i = 0, end = props.size(); i < end; ++i) {
            BeanPropertyWriter bpw = props.get(i);
            TypeSerializer td = bpw.getTypeSerializer();
            if ((td == null) || (td.getTypeInclusion() != As.EXTERNAL_PROPERTY)) {
                continue;
            }
            String n = td.getPropertyName();
            PropertyName typePropName = PropertyName.construct(n);
            for (BeanPropertyWriter w2 : props) {
                if ((w2 != bpw) && w2.wouldConflictWithName(typePropName)) {
                    props.set(i, bpw.withTypeSerializer(null));
                    break;
                }
            }
        }
        return props;
    }
    
    /*
    /**********************************************************
    /* Internal helper methods
    /**********************************************************
     */

    /**
     * Secondary helper method for constructing {@link BeanPropertyWriter} for
     * given member (field or method).
     */
    protected BeanPropertyWriter _constructWriter(SerializerProvider prov,
            BeanPropertyDefinition propDef, TypeBindings typeContext,
            PropertyBuilder pb, boolean staticTyping, AnnotatedMember accessor)
        throws JsonMappingException
    {
        final PropertyName name = propDef.getFullName();
        if (prov.canOverrideAccessModifiers()) {
            accessor.fixAccess();
        }
        JavaType type = accessor.getType(typeContext);
        BeanProperty.Std property = new BeanProperty.Std(name, type, propDef.getWrapperName(),
                pb.getClassAnnotations(), accessor, propDef.getMetadata());

        // Does member specify a serializer? If so, let's use it.
        JsonSerializer<?> annotatedSerializer = findSerializerFromAnnotation(prov,
                accessor);
        /* 02-Feb-2012, tatu: Unlike most other code paths, serializer produced
         *  here will NOT be resolved or contextualized, unless done here, so:
         */
        if (annotatedSerializer instanceof ResolvableSerializer) {
            ((ResolvableSerializer) annotatedSerializer).resolve(prov);
        }
        // 05-Sep-2013, tatu: should be primary property serializer so:
        annotatedSerializer = prov.handlePrimaryContextualization(annotatedSerializer, property);
        // And how about polymorphic typing? First special to cover JAXB per-field settings:
        TypeSerializer contentTypeSer = null;
        // 16-Feb-2014, cgc: contentType serializers for collection-like and map-like types
        if (ClassUtil.isCollectionMapOrArray(type.getRawClass())
                || type.isCollectionLikeType() || type.isMapLikeType()) {
            contentTypeSer = findPropertyContentTypeSerializer(type, prov.getConfig(), accessor);
        }
        // and if not JAXB collection/array with annotations, maybe regular type info?
        TypeSerializer typeSer = findPropertyTypeSerializer(type, prov.getConfig(), accessor);
        BeanPropertyWriter pbw = pb.buildWriter(prov, propDef, type, annotatedSerializer,
                        typeSer, contentTypeSer, accessor, staticTyping);
        return pbw;
    }
}


File: src/test/java/com/fasterxml/jackson/databind/jsontype/TestExternalId.java
package com.fasterxml.jackson.databind.jsontype;

import java.util.*;

import com.fasterxml.jackson.annotation.*;
import com.fasterxml.jackson.annotation.JsonTypeInfo.As;
import com.fasterxml.jackson.annotation.JsonTypeInfo.Id;

import com.fasterxml.jackson.databind.BaseMapTest;
import com.fasterxml.jackson.databind.ObjectMapper;

// Tests for [JACKSON-453]
public class TestExternalId extends BaseMapTest
{
    /*
    /**********************************************************
    /* Helper types
    /**********************************************************
     */
    
    static class ExternalBean
    {
        @JsonTypeInfo(use=Id.NAME, include=As.EXTERNAL_PROPERTY, property="extType")
        public Object bean;

        public ExternalBean() { }
        public ExternalBean(int v) {
            bean = new ValueBean(v);
        }
    }

    // for [Issue#96]
    static class ExternalBeanWithDefault
    {
        @JsonTypeInfo(use=Id.CLASS, include=As.EXTERNAL_PROPERTY, property="extType",
                defaultImpl=ValueBean.class)
        public Object bean;

        public ExternalBeanWithDefault() { }
        public ExternalBeanWithDefault(int v) {
            bean = new ValueBean(v);
        }
    }

    static class ExternalBean3
    {
        @JsonTypeInfo(use=Id.NAME, include=As.EXTERNAL_PROPERTY, property="extType1")
        public Object value1;
        
        @JsonTypeInfo(use=Id.NAME, include=As.EXTERNAL_PROPERTY, property="extType2")
        public Object value2;

        public int foo;
        
        @JsonTypeInfo(use=Id.NAME, include=As.EXTERNAL_PROPERTY, property="extType3")
        public Object value3;
        
        public ExternalBean3() { }
        public ExternalBean3(int v) {
            value1 = new ValueBean(v);
            value2 = new ValueBean(v+1);
            value3 = new ValueBean(v+2);
            foo = v;
        }
    }

    static class ExternalBeanWithCreator
    {
        @JsonTypeInfo(use=Id.NAME, include=As.EXTERNAL_PROPERTY, property="extType")
        public Object value;

        public int foo;
        
        @JsonCreator
        public ExternalBeanWithCreator(@JsonProperty("foo") int f)
        {
            foo = f;
            value = new ValueBean(f);
        }
    }
    
    @JsonTypeName("vbean")
    static class ValueBean {
        public int value;
        
        public ValueBean() { }
        public ValueBean(int v) { value = v; }
    }

    @JsonTypeName("funk")
    @JsonTypeInfo(use=Id.NAME, include=As.EXTERNAL_PROPERTY, property="extType")
    static class FunkyExternalBean {
        public int i = 3;
    }

    // [JACKSON-798]: problems with polymorphic types, external prop

    @JsonSubTypes(value= { @JsonSubTypes.Type(value=Derived1.class, name="d1"),
            @JsonSubTypes.Type(value=Derived2.class, name="d2") })
    interface Base {
        String getBaseProperty();
    }
  
    static class Derived1 implements Base {
        private String derived1Property;
        private String baseProperty;
        protected  Derived1() { throw new IllegalStateException("wrong constructor called"); }
        
        @JsonCreator
        public Derived1(@JsonProperty("derived1Property") String d1p,
                        @JsonProperty("baseProperty") String bp) {
            derived1Property = d1p;
            baseProperty = bp;
        }

        @Override
        @JsonProperty public String getBaseProperty() {
            return baseProperty;
        }

        @JsonProperty public String getDerived1Property() {
            return derived1Property;
        }
    }

    static class Derived2 implements Base {
        private String derived2Property;
        private String baseProperty;
        protected  Derived2() { throw new IllegalStateException("wrong constructor called"); }

        @JsonCreator
        public Derived2(@JsonProperty("derived2Property") String d2p,
                        @JsonProperty("baseProperty") String bp) {
            derived2Property = d2p;
            baseProperty = bp;
        }

        @Override
        @JsonProperty public String getBaseProperty() {
            return baseProperty;
        }

        @JsonProperty public String getDerived2Property() {
            return derived2Property;
        }
    }
    
    static class BaseContainer {
        protected final Base base;
        protected final String baseContainerProperty;
        protected BaseContainer() { throw new IllegalStateException("wrong constructor called"); }

        @JsonCreator
        public BaseContainer(@JsonProperty("baseContainerProperty") String bcp, @JsonProperty("base") Base b) {
            baseContainerProperty = bcp;
            base = b;
        }

        @JsonProperty
        public String getBaseContainerProperty() { return baseContainerProperty; }

        @JsonTypeInfo(use=JsonTypeInfo.Id.NAME, include=JsonTypeInfo.As.EXTERNAL_PROPERTY, property="type")
        @JsonProperty
        public Base getBase() { return base; }
    }

    // [JACKSON-831]: should allow a property to map id to as well
    
    interface Pet {}

    static class Dog implements Pet {
        public String name;
    }

    static class House831 {
        protected String petType;

        @JsonTypeInfo(use = Id.NAME, include = As.EXTERNAL_PROPERTY, property = "petType")
        @JsonSubTypes({@JsonSubTypes.Type(name = "dog", value = Dog.class)})
        public Pet pet;

        public String getPetType() {
            return petType;
        }

        public void setPetType(String petType) {
            this.petType = petType;
        }
    }    

    // for [Issue#118]
    static class ExternalTypeWithNonPOJO {
        @JsonTypeInfo(use = JsonTypeInfo.Id.NAME,
                property = "type",
                visible = true,
                include = JsonTypeInfo.As.EXTERNAL_PROPERTY,
                defaultImpl = String.class)
        @JsonSubTypes({
            @JsonSubTypes.Type(value = Date.class, name = "date"),
            @JsonSubTypes.Type(value = AsValueThingy.class, name = "thingy")
        })
        public Object value;

        public ExternalTypeWithNonPOJO() { }
        public ExternalTypeWithNonPOJO(Object o) { value = o; }
    }    

    // for [Issue#119]
    static class AsValueThingy {
        public long rawDate;

        public AsValueThingy(long l) { rawDate = l; }
        public AsValueThingy() { }
        
        @JsonValue public Date serialization() {
            return new Date(rawDate);
        }
    }

    /*
    /**********************************************************
    /* Unit tests, serialization
    /**********************************************************
     */

    private final ObjectMapper MAPPER = new ObjectMapper();
    
    public void testSimpleSerialization() throws Exception
    {
        ObjectMapper mapper = new ObjectMapper();
        mapper.registerSubtypes(ValueBean.class);
        // This may look odd, but one implementation nastiness is the fact
        // that we can not properly serialize type id before the object,
        // because call is made after property name (for object) has already
        // been written out. So we'll write it after...
        // Deserializer will work either way as it can not rely on ordering
        // anyway.
        assertEquals("{\"bean\":{\"value\":11},\"extType\":\"vbean\"}",
                mapper.writeValueAsString(new ExternalBean(11)));
    }

    // If trying to use with Class, should just become "PROPERTY" instead:
    public void testImproperExternalIdSerialization() throws Exception
    {
        ObjectMapper mapper = new ObjectMapper();
        assertEquals("{\"extType\":\"funk\",\"i\":3}",
                mapper.writeValueAsString(new FunkyExternalBean()));
    }

    /*
    /**********************************************************
    /* Unit tests, deserialization
    /**********************************************************
     */
    
    public void testSimpleDeserialization() throws Exception
    {
        ObjectMapper mapper = new ObjectMapper();
        mapper.registerSubtypes(ValueBean.class);
        ExternalBean result = mapper.readValue("{\"bean\":{\"value\":11},\"extType\":\"vbean\"}", ExternalBean.class);
        assertNotNull(result);
        assertNotNull(result.bean);
        ValueBean vb = (ValueBean) result.bean;
        assertEquals(11, vb.value);
    }

    // Test for verifying that it's ok to have multiple (say, 3)
    // externally typed things, mixed with other stuff...
    public void testMultipleTypeIdsDeserialization() throws Exception
    {
        ObjectMapper mapper = new ObjectMapper();
        mapper.registerSubtypes(ValueBean.class);
        String json = mapper.writeValueAsString(new ExternalBean3(3));
        ExternalBean3 result = mapper.readValue(json, ExternalBean3.class);
        assertNotNull(result);
        assertNotNull(result.value1);
        assertNotNull(result.value2);
        assertNotNull(result.value3);
        assertEquals(3, ((ValueBean)result.value1).value);
        assertEquals(4, ((ValueBean)result.value2).value);
        assertEquals(5, ((ValueBean)result.value3).value);
        assertEquals(3, result.foo);
    }

    // Also, it should be ok to use @JsonCreator as well...
    public void testExternalTypeWithCreator() throws Exception
    {
        ObjectMapper mapper = new ObjectMapper();
        mapper.registerSubtypes(ValueBean.class);
        String json = mapper.writeValueAsString(new ExternalBeanWithCreator(7));
        ExternalBeanWithCreator result = mapper.readValue(json, ExternalBeanWithCreator.class);
        assertNotNull(result);
        assertNotNull(result.value);
        assertEquals(7, ((ValueBean)result.value).value);
        assertEquals(7, result.foo);
    }
    
    // If trying to use with Class, should just become "PROPERTY" instead:
    public void testImproperExternalIdDeserialization() throws Exception
    {
        FunkyExternalBean result = MAPPER.readValue("{\"extType\":\"funk\",\"i\":3}",
                FunkyExternalBean.class);
        assertNotNull(result);
        assertEquals(3, result.i);
    }

    public void testIssue798() throws Exception
    {
        Base base = new Derived1("derived1 prop val", "base prop val");
        BaseContainer baseContainer = new BaseContainer("bc prop val", base);
        String generatedJson = MAPPER.writeValueAsString(baseContainer);
        BaseContainer baseContainer2 = MAPPER.readValue(generatedJson,BaseContainer.class);
        assertEquals("bc prop val", baseContainer.getBaseContainerProperty());

        Base b = baseContainer2.getBase();
        assertNotNull(b);
        if (b.getClass() != Derived1.class) {
            fail("Should have type Derived1, was "+b.getClass().getName());
        }

        Derived1 derived1 = (Derived1) b;
        assertEquals("base prop val", derived1.getBaseProperty());
        assertEquals("derived1 prop val", derived1.getDerived1Property());
    }

    // There seems to be some problems if type is also visible...
    public void testIssue831() throws Exception
    {
        final String JSON = "{ \"petType\": \"dog\",\n"
                +"\"pet\": { \"name\": \"Pluto\" }\n}";
        House831 result = MAPPER.readValue(JSON, House831.class);
        assertNotNull(result);
        assertNotNull(result.pet);
        assertSame(Dog.class, result.pet.getClass());
        assertEquals("dog", result.petType);
    }

    // For [Issue#96]: should allow use of default impl, if property missing
    /* 18-Jan-2013, tatu: Unfortunately this collides with [Issue#118], and I don't
     *   know what the best resolution is. For now at least 
     */
    /*
    public void testWithDefaultAndMissing() throws Exception
    {
        ExternalBeanWithDefault input = new ExternalBeanWithDefault(13);
        // baseline: include type, verify things work:
        String fullJson = MAPPER.writeValueAsString(input);
        ExternalBeanWithDefault output = MAPPER.readValue(fullJson, ExternalBeanWithDefault.class);
        assertNotNull(output);
        assertNotNull(output.bean);
        // and then try without type info...
        ExternalBeanWithDefault defaulted = MAPPER.readValue("{\"bean\":{\"value\":13}}",
                ExternalBeanWithDefault.class);
        assertNotNull(defaulted);
        assertNotNull(defaulted.bean);
        assertSame(ValueBean.class, defaulted.bean.getClass());
    }
    */

    // For [Issue#118]
    // Note: String works fine, since no type id will used; other scalar types have issues
    public void testWithScalar118() throws Exception
    {
        ExternalTypeWithNonPOJO input = new ExternalTypeWithNonPOJO(new java.util.Date(123L));
        String json = MAPPER.writeValueAsString(input);
        assertNotNull(json);

        // and back just to be sure:
        ExternalTypeWithNonPOJO result = MAPPER.readValue(json, ExternalTypeWithNonPOJO.class);
        assertNotNull(result.value);
        assertTrue(result.value instanceof java.util.Date);
    }

    // For [Issue#118] using "natural" type(s)
    public void testWithNaturalScalar118() throws Exception
    {
        ExternalTypeWithNonPOJO input = new ExternalTypeWithNonPOJO(Integer.valueOf(13));
        String json = MAPPER.writeValueAsString(input);
        assertNotNull(json);
        // and back just to be sure:
        ExternalTypeWithNonPOJO result = MAPPER.readValue(json, ExternalTypeWithNonPOJO.class);
        assertNotNull(result.value);
        assertTrue(result.value instanceof Integer);

        // ditto with others types
        input = new ExternalTypeWithNonPOJO(Boolean.TRUE);
        json = MAPPER.writeValueAsString(input);
        assertNotNull(json);
        result = MAPPER.readValue(json, ExternalTypeWithNonPOJO.class);
        assertNotNull(result.value);
        assertTrue(result.value instanceof Boolean);

        input = new ExternalTypeWithNonPOJO("foobar");
        json = MAPPER.writeValueAsString(input);
        assertNotNull(json);
        result = MAPPER.readValue(json, ExternalTypeWithNonPOJO.class);
        assertNotNull(result.value);
        assertTrue(result.value instanceof String);
        assertEquals("foobar", result.value);
    }
    
    // For [Issue#119]... and bit of [#167] as well
    public void testWithAsValue() throws Exception
    {
        ExternalTypeWithNonPOJO input = new ExternalTypeWithNonPOJO(new AsValueThingy(12345L));
        String json = MAPPER.writeValueAsString(input);
        assertNotNull(json);
        assertEquals("{\"value\":12345,\"type\":\"date\"}", json);

        // and get it back too:
        ExternalTypeWithNonPOJO result = MAPPER.readValue(json, ExternalTypeWithNonPOJO.class);
        assertNotNull(result);
        assertNotNull(result.value);
        /* 13-Feb-2013, tatu: Urgh. I don't think this can work quite as intended...
         *   since POJO type, and type of thing @JsonValue annotated method returns
         *   are not related. Best we can do is thus this:
         */
        /*
        assertEquals(AsValueThingy.class, result.value.getClass());
        assertEquals(12345L, ((AsValueThingy) result.value).rawDate);
        */
        assertEquals(Date.class, result.value.getClass());
        assertEquals(12345L, ((Date) result.value).getTime());
    }
}


File: src/test/java/com/fasterxml/jackson/failing/TestExternalTypeId222.java
package com.fasterxml.jackson.failing;

import com.fasterxml.jackson.annotation.*;
import com.fasterxml.jackson.databind.*;

public class TestExternalTypeId222 extends BaseMapTest
{
    // 25-Feb-2015, tatu: Where does this belong? Not related to #222...

    /*
	@SuppressWarnings("unused")
	public void testTypes() throws IOException {
        final ObjectMapper mapper = new ObjectMapper();
        mapper.configure(DeserializationFeature.FAIL_ON_UNKNOWN_PROPERTIES, false);

        final Point _date = new Point(new Date());
        final Point _integer = new Point(12231321);
        final Point _boolean = new Point(Boolean.TRUE);
        final Point _long = new Point(1234L);

        final Point _pojo = new Point(new Pojo(1));
        final String s_date = mapper.writeValueAsString(_date);
        final String s_integer = mapper.writeValueAsString(_integer);

//System.err.println("Int -> "+s_integer);   
    
        final String s_boolean = mapper.writeValueAsString(_boolean);
        final String s_long = mapper.writeValueAsString(_long);
        final String s_pojo = mapper.writeValueAsString(_pojo);

        final Point d_date = mapper.readValue(s_date, Point.class);
        final Point d_long = mapper.readValue(s_long, Point.class);
        final Point d_pojo = mapper.readValue(s_pojo, Point.class);
        final Point d_integer = mapper.readValue(s_integer, Point.class);
        final Point d_boolean = mapper.readValue(s_boolean, Point.class);
    }

    @JsonAutoDetect(fieldVisibility = JsonAutoDetect.Visibility.ANY,
        getterVisibility = JsonAutoDetect.Visibility.NONE,
        setterVisibility = JsonAutoDetect.Visibility.NONE)
    static class Point {
        @JsonTypeInfo(use = JsonTypeInfo.Id.NAME,
        property = "t",
        visible = true,
        include = JsonTypeInfo.As.EXTERNAL_PROPERTY,
        defaultImpl = String.class)
        @JsonSubTypes({
        @JsonSubTypes.Type(value = Date.class, name = "date"),
        @JsonSubTypes.Type(value = Integer.class, name = "int"),
        @JsonSubTypes.Type(value = Long.class, name = "long"),
        @JsonSubTypes.Type(value = Boolean.class, name = "bool"),
        @JsonSubTypes.Type(value = Pojo.class, name = "pojo"),
        @JsonSubTypes.Type(value = String.class, name = "")
        })
        private final Object v;
    
        @JsonCreator
        public Point(@JsonProperty("v") Object v) {
            this.v = v;
        }
    
        public Object getValue() {
            return v;
        }
    }
     

    static class Pojo {
        public final int p;

        @JsonCreator
        Pojo(@JsonProperty("p") int p) {
            this.p = p;
        }
    }
    */

    // [Issue#222]
    static class Issue222Bean
    {
        @JsonTypeInfo(use = JsonTypeInfo.Id.NAME,
                property = "type",
                include = JsonTypeInfo.As.EXTERNAL_PROPERTY)
        public Issue222BeanB value;

        public String type = "foo";
        
        public Issue222Bean() { }
        public Issue222Bean(int v) {
            value = new Issue222BeanB(v);
        }
    }

    @JsonTypeName("222b") // shouldn't actually matter
    static class Issue222BeanB
    {
        public int x;
        
        public Issue222BeanB() { }
        public Issue222BeanB(int value) { x = value; }
    }

    public void testIssue222() throws Exception
    {
        final ObjectMapper mapper = new ObjectMapper();
        Issue222Bean input = new Issue222Bean(13);
        String json = mapper.writeValueAsString(input);
        assertEquals("{\"value\":{\"x\":13},\"type\":\"foo\"}", json);
    }
}
