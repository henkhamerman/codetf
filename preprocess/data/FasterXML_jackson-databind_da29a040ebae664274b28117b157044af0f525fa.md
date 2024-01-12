Refactoring Types: ['Inline Method']
ackson/databind/ObjectWriter.java
package com.fasterxml.jackson.databind;

import java.io.*;
import java.text.*;
import java.util.*;
import java.util.concurrent.atomic.AtomicReference;

import com.fasterxml.jackson.core.*;
import com.fasterxml.jackson.core.io.CharacterEscapes;
import com.fasterxml.jackson.core.io.SegmentedStringWriter;
import com.fasterxml.jackson.core.io.SerializedString;
import com.fasterxml.jackson.core.type.TypeReference;
import com.fasterxml.jackson.core.util.*;
import com.fasterxml.jackson.databind.cfg.ContextAttributes;
import com.fasterxml.jackson.databind.jsonFormatVisitors.JsonFormatVisitorWrapper;
import com.fasterxml.jackson.databind.jsontype.TypeSerializer;
import com.fasterxml.jackson.databind.ser.*;
import com.fasterxml.jackson.databind.ser.impl.TypeWrappedSerializer;
import com.fasterxml.jackson.databind.type.TypeFactory;

/**
 * Builder object that can be used for per-serialization configuration of
 * serialization parameters, such as JSON View and root type to use.
 * (and thus fully thread-safe with no external synchronization);
 * new instances are constructed for different configurations.
 * Instances are initially constructed by {@link ObjectMapper} and can be
 * reused in completely thread-safe manner with no explicit synchronization
 */
public class ObjectWriter
    implements Versioned,
        java.io.Serializable // since 2.1
{
    private static final long serialVersionUID = 1; // since 2.5

    /**
     * We need to keep track of explicit disabling of pretty printing;
     * easiest to do by a token value.
     */
    protected final static PrettyPrinter NULL_PRETTY_PRINTER = new MinimalPrettyPrinter();

    /*
    /**********************************************************
    /* Immutable configuration from ObjectMapper
    /**********************************************************
     */

    /**
     * General serialization configuration settings
     */
    protected final SerializationConfig _config;

    protected final DefaultSerializerProvider _serializerProvider;

    protected final SerializerFactory _serializerFactory;

    /**
     * Factory used for constructing {@link JsonGenerator}s
     */
    protected final JsonFactory _generatorFactory;

    /*
    /**********************************************************
    /* Configuration that can be changed via mutant factories
    /**********************************************************
     */

    /**
     * Container for settings that need to be passed to {@link JsonGenerator}
     * constructed for serializing values.
     *
     * @since 2.5
     */
    protected final GeneratorSettings _generatorSettings;

    /**
     * We may pre-fetch serializer if root type
     * is known (has been explicitly declared), and if so, reuse it afterwards.
     * This allows avoiding further serializer lookups and increases
     * performance a bit on cases where readers are reused.
     *
     * @since 2.5
     */
    protected final Prefetch _prefetch;
    
    /*
    /**********************************************************
    /* Life-cycle, constructors
    /**********************************************************
     */

    /**
     * Constructor used by {@link ObjectMapper} for initial instantiation
     */
    protected ObjectWriter(ObjectMapper mapper, SerializationConfig config,
            JavaType rootType, PrettyPrinter pp)
    {
        _config = config;
        _serializerProvider = mapper._serializerProvider;
        _serializerFactory = mapper._serializerFactory;
        _generatorFactory = mapper._jsonFactory;
        _generatorSettings = (pp == null) ? GeneratorSettings.empty
                : new GeneratorSettings(pp, null, null, null);

        // 29-Apr-2014, tatu: There is no "untyped serializer", so:
        if (rootType == null || rootType.hasRawClass(Object.class)) {
            _prefetch = Prefetch.empty;
        } else {
            rootType = rootType.withStaticTyping();
            _prefetch = _prefetchRootSerializer(config, rootType);
        }
    }

    /**
     * Alternative constructor for initial instantiation by {@link ObjectMapper}
     */
    protected ObjectWriter(ObjectMapper mapper, SerializationConfig config)
    {
        _config = config;
        _serializerProvider = mapper._serializerProvider;
        _serializerFactory = mapper._serializerFactory;
        _generatorFactory = mapper._jsonFactory;

        _generatorSettings = GeneratorSettings.empty;
        _prefetch = Prefetch.empty;
    }

    /**
     * Alternative constructor for initial instantiation by {@link ObjectMapper}
     */
    protected ObjectWriter(ObjectMapper mapper, SerializationConfig config,
            FormatSchema s)
    {
        _config = config;

        _serializerProvider = mapper._serializerProvider;
        _serializerFactory = mapper._serializerFactory;
        _generatorFactory = mapper._jsonFactory;

        _generatorSettings = (s == null) ? GeneratorSettings.empty
                : new GeneratorSettings(null, s, null, null);
        _prefetch = Prefetch.empty;
    }
    
    /**
     * Copy constructor used for building variations.
     */
    protected ObjectWriter(ObjectWriter base, SerializationConfig config,
            GeneratorSettings genSettings, Prefetch prefetch)
    {
        _config = config;

        _serializerProvider = base._serializerProvider;
        _serializerFactory = base._serializerFactory;
        _generatorFactory = base._generatorFactory;

        _generatorSettings = genSettings;
        _prefetch = prefetch;
    }

    /**
     * Copy constructor used for building variations.
     */
    protected ObjectWriter(ObjectWriter base, SerializationConfig config)
    {
        _config = config;

        _serializerProvider = base._serializerProvider;
        _serializerFactory = base._serializerFactory;
        _generatorFactory = base._generatorFactory;

        _generatorSettings = base._generatorSettings;
        _prefetch = base._prefetch;
    }

    /**
     * @since 2.3
     */
    protected ObjectWriter(ObjectWriter base, JsonFactory f)
    {
        // may need to override ordering, based on data format capabilities
        _config = base._config
            .with(MapperFeature.SORT_PROPERTIES_ALPHABETICALLY, f.requiresPropertyOrdering());

        _serializerProvider = base._serializerProvider;
        _serializerFactory = base._serializerFactory;
        _generatorFactory = base._generatorFactory;

        _generatorSettings = base._generatorSettings;
        _prefetch = base._prefetch;
    }

    /**
     * Method that will return version information stored in and read from jar
     * that contains this class.
     */
    @Override
    public Version version() {
        return com.fasterxml.jackson.databind.cfg.PackageVersion.VERSION;
    }

    /*
    /**********************************************************
    /* Methods sub-classes MUST override, used for constructing
    /* writer instances, (re)configuring parser instances.
    /* Added in 2.5
    /**********************************************************
     */

    /**
     * Overridable factory method called by various "withXxx()" methods
     * 
     * @since 2.5
     */
    protected ObjectWriter _new(ObjectWriter base, JsonFactory f) {
        return new ObjectWriter(base, f);
    }

    /**
     * Overridable factory method called by various "withXxx()" methods
     * 
     * @since 2.5
     */
    protected ObjectWriter _new(ObjectWriter base, SerializationConfig config) {
        return new ObjectWriter(base, config);
    }

    /**
     * Overridable factory method called by various "withXxx()" methods.
     * It assumes `this` as base for settings other than those directly
     * passed in.
     * 
     * @since 2.5
     */
    protected ObjectWriter _new(GeneratorSettings genSettings, Prefetch prefetch) {
        return new ObjectWriter(this, _config, genSettings, prefetch);
    }

    /**
     * Overridable factory method called by {@link #writeValues(OutputStream)}
     * method (and its various overrides), and initializes it as necessary.
     * 
     * @since 2.5
     */
    @SuppressWarnings("resource")
    protected SequenceWriter _newSequenceWriter(boolean wrapInArray,
            JsonGenerator gen, boolean managedInput)
        throws IOException
    {
        _configureGenerator(gen);
        return new SequenceWriter(_serializerProvider(_config),
                gen, managedInput, _prefetch)
            .init(wrapInArray);
    }

    /*
    /**********************************************************
    /* Life-cycle, fluent factories for SerializationFeature
    /**********************************************************
     */

    /**
     * Method for constructing a new instance that is configured
     * with specified feature enabled.
     */
    public ObjectWriter with(SerializationFeature feature)  {
        SerializationConfig newConfig = _config.with(feature);
        return (newConfig == _config) ? this : _new(this, newConfig);
    }

    /**
     * Method for constructing a new instance that is configured
     * with specified features enabled.
     */
    public ObjectWriter with(SerializationFeature first, SerializationFeature... other) {
        SerializationConfig newConfig = _config.with(first, other);
        return (newConfig == _config) ? this : _new(this, newConfig);
    }    

    /**
     * Method for constructing a new instance that is configured
     * with specified features enabled.
     */
    public ObjectWriter withFeatures(SerializationFeature... features) {
        SerializationConfig newConfig = _config.withFeatures(features);
        return (newConfig == _config) ? this : _new(this, newConfig);
    }    
    
    /**
     * Method for constructing a new instance that is configured
     * with specified feature enabled.
     */
    public ObjectWriter without(SerializationFeature feature) {
        SerializationConfig newConfig = _config.without(feature);
        return (newConfig == _config) ? this : _new(this, newConfig);
    }    

    /**
     * Method for constructing a new instance that is configured
     * with specified features enabled.
     */
    public ObjectWriter without(SerializationFeature first, SerializationFeature... other) {
        SerializationConfig newConfig = _config.without(first, other);
        return (newConfig == _config) ? this : _new(this, newConfig);
    }    

    /**
     * Method for constructing a new instance that is configured
     * with specified features enabled.
     */
    public ObjectWriter withoutFeatures(SerializationFeature... features) {
        SerializationConfig newConfig = _config.withoutFeatures(features);
        return (newConfig == _config) ? this : _new(this, newConfig);
    }

    /*
    /**********************************************************
    /* Life-cycle, fluent factories for JsonGenerator.Feature
    /**********************************************************
     */

    /**
     * @since 2.5
     */
    public ObjectWriter with(JsonGenerator.Feature feature)  {
        SerializationConfig newConfig = _config.with(feature);
        return (newConfig == _config) ? this : _new(this, newConfig);
    }

    /**
     * @since 2.5
     */
    public ObjectWriter withFeatures(JsonGenerator.Feature... features) {
        SerializationConfig newConfig = _config.withFeatures(features);
        return (newConfig == _config) ? this : _new(this, newConfig);
    }

    /**
     * @since 2.5
     */
    public ObjectWriter without(JsonGenerator.Feature feature) {
        SerializationConfig newConfig = _config.without(feature);
        return (newConfig == _config) ? this : _new(this, newConfig);
    }

    /**
     * @since 2.5
     */
    public ObjectWriter withoutFeatures(JsonGenerator.Feature... features) {
        SerializationConfig newConfig = _config.withoutFeatures(features);
        return (newConfig == _config) ? this : _new(this, newConfig);
    }

    /*
    /**********************************************************
    /* Life-cycle, fluent factories, other
    /**********************************************************
     */

    /**
     * Fluent factory method that will construct a new writer instance that will
     * use specified date format for serializing dates; or if null passed, one
     * that will serialize dates as numeric timestamps.
     *<p>
     * Note that the method does NOT change state of this reader, but
     * rather construct and returns a newly configured instance.
     */
    public ObjectWriter with(DateFormat df) {
        SerializationConfig newConfig = _config.with(df);
        return (newConfig == _config) ? this : _new(this, newConfig);
    }

    /**
     * Method that will construct a new instance that will use the default
     * pretty printer for serialization.
     */
    public ObjectWriter withDefaultPrettyPrinter() {
        return with(_config.getDefaultPrettyPrinter());
    }

    /**
     * Method that will construct a new instance that uses specified
     * provider for resolving filter instances by id.
     */
    public ObjectWriter with(FilterProvider filterProvider) {
        return (filterProvider == _config.getFilterProvider()) ? this
                 : _new(this, _config.withFilters(filterProvider));
    }

    /**
     * Method that will construct a new instance that will use specified pretty
     * printer (or, if null, will not do any pretty-printing)
     */
    public ObjectWriter with(PrettyPrinter pp) {
        GeneratorSettings genSet = _generatorSettings.with(pp);
        if (genSet == _generatorSettings) {
            return this;
        }
        return _new(genSet, _prefetch);
    }

    /**
     * Method for constructing a new instance with configuration that
     * specifies what root name to use for "root element wrapping".
     * See {@link SerializationConfig#withRootName(String)} for details.
     *<p>
     * Note that method does NOT change state of this reader, but
     * rather construct and returns a newly configured instance.
     * 
     * @param rootName Root name to use, if non-empty; `null` for "use defaults",
     *    and empty String ("") for "do NOT add root wrapper"
     */
    public ObjectWriter withRootName(String rootName) {
        SerializationConfig newConfig = _config.withRootName(rootName);
        return (newConfig == _config) ? this :  _new(this, newConfig);
    }

    /**
     * @since 2.6
     */
    public ObjectWriter withRootName(PropertyName rootName) {
        SerializationConfig newConfig = _config.withRootName(rootName);
        return (newConfig == _config) ? this :  _new(this, newConfig);
    }

    /**
     * Convenience method that is same as calling:
     *<code>
     *   withRootName("")
     *</code>
     * which will forcibly prevent use of root name wrapping when writing
     * values with this {@link ObjectWriter}.
     * 
     * @since 2.6
     */
    public ObjectWriter withoutRootName() {
        SerializationConfig newConfig = _config.withRootName(PropertyName.NO_NAME);
        return (newConfig == _config) ? this :  _new(this, newConfig);
    }
    
    /**
     * Method that will construct a new instance that uses specific format schema
     * for serialization.
     *<p>
     * Note that method does NOT change state of this reader, but
     * rather construct and returns a newly configured instance.
     */
    public ObjectWriter with(FormatSchema schema) {
        GeneratorSettings genSet = _generatorSettings.with(schema);
        if (genSet == _generatorSettings) {
            return this;
        }
        _verifySchemaType(schema);
        return _new(genSet, _prefetch);
    }

    /**
     * @deprecated Since 2.5 use {@link #with(FormatSchema)} instead
     */
    @Deprecated
    public ObjectWriter withSchema(FormatSchema schema) {
        return with(schema);
    }

    /**
     * Method that will construct a new instance that uses specific type
     * as the root type for serialization, instead of runtime dynamic
     * type of the root object itself.
     *<p>
     * Note that method does NOT change state of this reader, but
     * rather construct and returns a newly configured instance.
     * 
     * @since 2.5
     */
    public ObjectWriter forType(JavaType rootType)
    {
        Prefetch pf;
        if (rootType == null || rootType.hasRawClass(Object.class)) {
            pf = Prefetch.empty;
        } else {
            // 15-Mar-2013, tatu: Important! Indicate that static typing is needed:
            /* 19-Mar-2015, tatu: Except when dealing with Collection, Map types, where
             *    this does more harm than help.
             */
            if (!rootType.isContainerType()) {
                rootType = rootType.withStaticTyping();
            }
            pf = _prefetchRootSerializer(_config, rootType);
        }
        return (pf == _prefetch) ? this : _new(_generatorSettings, pf);
    }

    /**
     * Method that will construct a new instance that uses specific type
     * as the root type for serialization, instead of runtime dynamic
     * type of the root object itself.
     * 
     * @since 2.5
     */
    public ObjectWriter forType(Class<?> rootType) {
        if (rootType == Object.class) {
            return forType((JavaType) null);
        }
        return forType(_config.constructType(rootType));
    }

    public ObjectWriter forType(TypeReference<?> rootType) {
        return forType(_config.getTypeFactory().constructType(rootType.getType()));
    }

    /**
     * @deprecated since 2.5 Use {@link #forType(JavaType)} instead
     */
    @Deprecated // since 2.5
    public ObjectWriter withType(JavaType rootType) {
        return forType(rootType);
    }

    /**
     * @deprecated since 2.5 Use {@link #forType(Class)} instead
     */
    @Deprecated // since 2.5
    public ObjectWriter withType(Class<?> rootType) {
        return forType(rootType);
    }

    /**
     * @deprecated since 2.5 Use {@link #forType(TypeReference)} instead
     */
    @Deprecated // since 2.5
    public ObjectWriter withType(TypeReference<?> rootType) {
        return forType(rootType);
    }

    /**
     * Method that will construct a new instance that uses specified
     * serialization view for serialization (with null basically disables
     * view processing)
     *<p>
     * Note that the method does NOT change state of this reader, but
     * rather construct and returns a newly configured instance.
     */
    public ObjectWriter withView(Class<?> view) {
        SerializationConfig newConfig = _config.withView(view);
        return (newConfig == _config) ? this :  _new(this, newConfig);
    }    

    public ObjectWriter with(Locale l) {
        SerializationConfig newConfig = _config.with(l);
        return (newConfig == _config) ? this :  _new(this, newConfig);
    }

    public ObjectWriter with(TimeZone tz) {
        SerializationConfig newConfig = _config.with(tz);
        return (newConfig == _config) ? this :  _new(this, newConfig);
    }

    /**
     * Method that will construct a new instance that uses specified default
     * {@link Base64Variant} for base64 encoding
     * 
     * @since 2.1
     */
    public ObjectWriter with(Base64Variant b64variant) {
        SerializationConfig newConfig = _config.with(b64variant);
        return (newConfig == _config) ? this :  _new(this, newConfig);
    }

    /**
     * @since 2.3
     */
    public ObjectWriter with(CharacterEscapes escapes) {
        GeneratorSettings genSet = _generatorSettings.with(escapes);
        if (genSet == _generatorSettings) {
            return this;
        }
        return _new(genSet, _prefetch);
    }

    /**
     * @since 2.3
     */
    public ObjectWriter with(JsonFactory f) {
        return (f == _generatorFactory) ? this : _new(this, f);
    }    

    /**
     * @since 2.3
     */
    public ObjectWriter with(ContextAttributes attrs) {
        SerializationConfig newConfig = _config.with(attrs);
        return (newConfig == _config) ? this :  _new(this, newConfig);
    }

    /**
     * @since 2.3
     */
    public ObjectWriter withAttributes(Map<Object,Object> attrs) {
        SerializationConfig newConfig = _config.withAttributes(attrs);
        return (newConfig == _config) ? this :  _new(this, newConfig);
    }

    /**
     * @since 2.3
     */
    public ObjectWriter withAttribute(Object key, Object value) {
        SerializationConfig newConfig = _config.withAttribute(key, value);
        return (newConfig == _config) ? this :  _new(this, newConfig);
    }

    /**
     * @since 2.3
     */
    public ObjectWriter withoutAttribute(Object key) {
        SerializationConfig newConfig = _config.withoutAttribute(key);
        return (newConfig == _config) ? this :  _new(this, newConfig);
    }

    /**
     * @since 2.5
     */
    public ObjectWriter withRootValueSeparator(String sep) {
        GeneratorSettings genSet = _generatorSettings.withRootValueSeparator(sep);
        if (genSet == _generatorSettings) {
            return this;
        }
        return _new(genSet, _prefetch);
    }

    /**
     * @since 2.5
     */
    public ObjectWriter withRootValueSeparator(SerializableString sep) {
        GeneratorSettings genSet = _generatorSettings.withRootValueSeparator(sep);
        if (genSet == _generatorSettings) {
            return this;
        }
        return _new(genSet, _prefetch);
    }

    /*
    /**********************************************************
    /* Factory methods for sequence writers (2.5)
    /**********************************************************
     */

    /**
     * Method for creating a {@link SequenceWriter} to write a sequence of root
     * values using configuration of this {@link ObjectWriter}.
     * Sequence is not surrounded by JSON array; some backend types may not
     * support writing of such sequences as root level.
     * Resulting writer needs to be {@link SequenceWriter#close()}d after all
     * values have been written to ensure closing of underlying generator and
     * output stream.
     *
     * @param out Target file to write value sequence to.
     *
     * @since 2.5
     */
    public SequenceWriter writeValues(File out) throws IOException {
        return _newSequenceWriter(false,
                _generatorFactory.createGenerator(out, JsonEncoding.UTF8), true);
    }

    /**
     * Method for creating a {@link SequenceWriter} to write a sequence of root
     * values using configuration of this {@link ObjectWriter}.
     * Sequence is not surrounded by JSON array; some backend types may not
     * support writing of such sequences as root level.
     * Resulting writer needs to be {@link SequenceWriter#close()}d after all
     * values have been written to ensure that all content gets flushed by
     * the generator. However, since a {@link JsonGenerator} is explicitly passed,
     * it will NOT be closed when {@link SequenceWriter#close()} is called.
     *
     * @param gen Low-level generator caller has already constructed that will
     *   be used for actual writing of token stream.
     *
     * @since 2.5
     */
    public SequenceWriter writeValues(JsonGenerator gen) throws IOException {
        _configureGenerator(gen);
        return _newSequenceWriter(false, gen, false);
    }

    /**
     * Method for creating a {@link SequenceWriter} to write a sequence of root
     * values using configuration of this {@link ObjectWriter}.
     * Sequence is not surrounded by JSON array; some backend types may not
     * support writing of such sequences as root level.
     * Resulting writer needs to be {@link SequenceWriter#close()}d after all
     * values have been written to ensure closing of underlying generator and
     * output stream.
     *
     * @param out Target writer to use for writing the token stream
     *
     * @since 2.5
     */
    public SequenceWriter writeValues(Writer out) throws IOException {
        return _newSequenceWriter(false,
                _generatorFactory.createGenerator(out), true);
    }

    /**
     * Method for creating a {@link SequenceWriter} to write a sequence of root
     * values using configuration of this {@link ObjectWriter}.
     * Sequence is not surrounded by JSON array; some backend types may not
     * support writing of such sequences as root level.
     * Resulting writer needs to be {@link SequenceWriter#close()}d after all
     * values have been written to ensure closing of underlying generator and
     * output stream.
     *
     * @param out Physical output stream to use for writing the token stream
     *
     * @since 2.5
     */
    public SequenceWriter writeValues(OutputStream out) throws IOException {
        return _newSequenceWriter(false,
                _generatorFactory.createGenerator(out, JsonEncoding.UTF8), true);
    }

    /**
     * Method for creating a {@link SequenceWriter} to write an array of
     * root-level values, using configuration of this {@link ObjectWriter}.
     * Resulting writer needs to be {@link SequenceWriter#close()}d after all
     * values have been written to ensure closing of underlying generator and
     * output stream.
     *<p>
     * Note that the type to use with {@link ObjectWriter#forType(Class)} needs to
     * be type of individual values (elements) to write and NOT matching array
     * or {@link java.util.Collection} type.
     *
     * @param out File to write token stream to
     *
     * @since 2.5
     */
    public SequenceWriter writeValuesAsArray(File out) throws IOException {
        return _newSequenceWriter(true,
                _generatorFactory.createGenerator(out, JsonEncoding.UTF8), true);
    }

    /**
     * Method for creating a {@link SequenceWriter} to write an array of
     * root-level values, using configuration of this {@link ObjectWriter}.
     * Resulting writer needs to be {@link SequenceWriter#close()}d after all
     * values have been written to ensure that all content gets flushed by
     * the generator. However, since a {@link JsonGenerator} is explicitly passed,
     * it will NOT be closed when {@link SequenceWriter#close()} is called.
     *<p>
     * Note that the type to use with {@link ObjectWriter#forType(Class)} needs to
     * be type of individual values (elements) to write and NOT matching array
     * or {@link java.util.Collection} type.
     *
     * @param gen Underlying generator to use for writing the token stream
     *
     * @since 2.5
     */
    public SequenceWriter writeValuesAsArray(JsonGenerator gen) throws IOException {
        return _newSequenceWriter(true, gen, false);
    }

    /**
     * Method for creating a {@link SequenceWriter} to write an array of
     * root-level values, using configuration of this {@link ObjectWriter}.
     * Resulting writer needs to be {@link SequenceWriter#close()}d after all
     * values have been written to ensure closing of underlying generator and
     * output stream.
     *<p>
     * Note that the type to use with {@link ObjectWriter#forType(Class)} needs to
     * be type of individual values (elements) to write and NOT matching array
     * or {@link java.util.Collection} type.
     *
     * @param out Writer to use for writing the token stream
     *
     * @since 2.5
     */
    public SequenceWriter writeValuesAsArray(Writer out) throws IOException {
        return _newSequenceWriter(true, _generatorFactory.createGenerator(out), true);
    }

    /**
     * Method for creating a {@link SequenceWriter} to write an array of
     * root-level values, using configuration of this {@link ObjectWriter}.
     * Resulting writer needs to be {@link SequenceWriter#close()}d after all
     * values have been written to ensure closing of underlying generator and
     * output stream.
     *<p>
     * Note that the type to use with {@link ObjectWriter#forType(Class)} needs to
     * be type of individual values (elements) to write and NOT matching array
     * or {@link java.util.Collection} type.
     *
     * @param out Physical output stream to use for writing the token stream
     *
     * @since 2.5
     */
    public SequenceWriter writeValuesAsArray(OutputStream out) throws IOException {
        return _newSequenceWriter(true,
                _generatorFactory.createGenerator(out, JsonEncoding.UTF8), true);
    }

    /*
    /**********************************************************
    /* Simple accessors
    /**********************************************************
     */

    public boolean isEnabled(SerializationFeature f) {
        return _config.isEnabled(f);
    }

    public boolean isEnabled(MapperFeature f) {
        return _config.isEnabled(f);
    }

    public boolean isEnabled(JsonParser.Feature f) {
        return _generatorFactory.isEnabled(f);
    }

    /**
     * @since 2.2
     */
    public SerializationConfig getConfig() {
        return _config;
    }

    /**
     * @since 2.2
     */
    public JsonFactory getFactory() {
        return _generatorFactory;
    }
    
    public TypeFactory getTypeFactory() {
        return _config.getTypeFactory();
    }

    /**
     * Diagnostics method that can be called to check whether this writer
     * has pre-fetched serializer to use: pre-fetching improves performance
     * when writer instances are reused as it avoids a per-call serializer
     * lookup.
     * 
     * @since 2.2
     */
    public boolean hasPrefetchedSerializer() {
        return _prefetch.hasSerializer();
    }

    /**
     * @since 2.3
     */
    public ContextAttributes getAttributes() {
        return _config.getAttributes();
    }
    
    /*
    /**********************************************************
    /* Serialization methods; ones from ObjectCodec first
    /**********************************************************
     */

    /**
     * Method that can be used to serialize any Java value as
     * JSON output, using provided {@link JsonGenerator}.
     */
    public void writeValue(JsonGenerator gen, Object value)
        throws IOException, JsonGenerationException, JsonMappingException
    {
        _configureGenerator(gen);
        if (_config.isEnabled(SerializationFeature.CLOSE_CLOSEABLE)
                && (value instanceof Closeable)) {
            _writeCloseableValue(gen, value, _config);
        } else {
            JsonSerializer<Object> ser = _prefetch.valueSerializer;
            if (ser != null) {
                _serializerProvider(_config).serializeValue(gen, value, _prefetch.rootType, ser);
            } else if (_prefetch.typeSerializer != null) {
                _serializerProvider(_config).serializePolymorphic(gen, value,
                        _prefetch.rootType, _prefetch.typeSerializer);
            } else {
                _serializerProvider(_config).serializeValue(gen, value);
            }
            if (_config.isEnabled(SerializationFeature.FLUSH_AFTER_WRITE_VALUE)) {
                gen.flush();
            }
        }
    }

    /*
    /**********************************************************
    /* Serialization methods, others
    /**********************************************************
     */

    /**
     * Method that can be used to serialize any Java value as
     * JSON output, written to File provided.
     */
    public void writeValue(File resultFile, Object value)
        throws IOException, JsonGenerationException, JsonMappingException
    {
        _configAndWriteValue(_generatorFactory.createGenerator(resultFile, JsonEncoding.UTF8), value);
    }

    /**
     * Method that can be used to serialize any Java value as
     * JSON output, using output stream provided (using encoding
     * {@link JsonEncoding#UTF8}).
     *<p>
     * Note: method does not close the underlying stream explicitly
     * here; however, {@link JsonFactory} this mapper uses may choose
     * to close the stream depending on its settings (by default,
     * it will try to close it when {@link JsonGenerator} we construct
     * is closed).
     */
    public void writeValue(OutputStream out, Object value)
        throws IOException, JsonGenerationException, JsonMappingException
    {
        _configAndWriteValue(_generatorFactory.createGenerator(out, JsonEncoding.UTF8), value);
    }

    /**
     * Method that can be used to serialize any Java value as
     * JSON output, using Writer provided.
     *<p>
     * Note: method does not close the underlying stream explicitly
     * here; however, {@link JsonFactory} this mapper uses may choose
     * to close the stream depending on its settings (by default,
     * it will try to close it when {@link JsonGenerator} we construct
     * is closed).
     */
    public void writeValue(Writer w, Object value)
        throws IOException, JsonGenerationException, JsonMappingException
    {
        _configAndWriteValue(_generatorFactory.createGenerator(w), value);
    }

    /**
     * Method that can be used to serialize any Java value as
     * a String. Functionally equivalent to calling
     * {@link #writeValue(Writer,Object)} with {@link java.io.StringWriter}
     * and constructing String, but more efficient.
     *<p>
     * Note: prior to version 2.1, throws clause included {@link IOException}; 2.1 removed it.
     */
    @SuppressWarnings("resource")
    public String writeValueAsString(Object value)
        throws JsonProcessingException
    {        
        // alas, we have to pull the recycler directly here...
        SegmentedStringWriter sw = new SegmentedStringWriter(_generatorFactory._getBufferRecycler());
        try {
            _configAndWriteValue(_generatorFactory.createGenerator(sw), value);
        } catch (JsonProcessingException e) { // to support [JACKSON-758]
            throw e;
        } catch (IOException e) { // shouldn't really happen, but is declared as possibility so:
            throw JsonMappingException.fromUnexpectedIOE(e);
        }
        return sw.getAndClear();
    }
    
    /**
     * Method that can be used to serialize any Java value as
     * a byte array. Functionally equivalent to calling
     * {@link #writeValue(Writer,Object)} with {@link java.io.ByteArrayOutputStream}
     * and getting bytes, but more efficient.
     * Encoding used will be UTF-8.
     *<p>
     * Note: prior to version 2.1, throws clause included {@link IOException}; 2.1 removed it.
     */
    @SuppressWarnings("resource")
    public byte[] writeValueAsBytes(Object value)
        throws JsonProcessingException
    {
        ByteArrayBuilder bb = new ByteArrayBuilder(_generatorFactory._getBufferRecycler());
        try {
            _configAndWriteValue(_generatorFactory.createGenerator(bb, JsonEncoding.UTF8), value);
        } catch (JsonProcessingException e) { // to support [JACKSON-758]
            throw e;
        } catch (IOException e) { // shouldn't really happen, but is declared as possibility so:
            throw JsonMappingException.fromUnexpectedIOE(e);
        }
        byte[] result = bb.toByteArray();
        bb.release();
        return result;
    }

    /*
    /**********************************************************
    /* Other public methods
    /**********************************************************
     */

    /**
     * Method for visiting type hierarchy for given type, using specified visitor.
     * Visitation uses <code>Serializer</code> hierarchy and related properties
     *<p>
     * This method can be used for things like
     * generating <a href="http://json-schema.org/">Json Schema</a>
     * instance for specified type.
     *
     * @param type Type to generate schema for (possibly with generic signature)
     * 
     * @since 2.2
     */
    public void acceptJsonFormatVisitor(JavaType type, JsonFormatVisitorWrapper visitor) throws JsonMappingException
    {
        if (type == null) {
            throw new IllegalArgumentException("type must be provided");
        }
        _serializerProvider(_config).acceptJsonFormatVisitor(type, visitor);
    }

    /**
     * Since 2.6
     */
    public void acceptJsonFormatVisitor(Class<?> rawType, JsonFormatVisitorWrapper visitor) throws JsonMappingException {
        acceptJsonFormatVisitor(_config.constructType(rawType), visitor);
    }

    public boolean canSerialize(Class<?> type) {
        return _serializerProvider(_config).hasSerializerFor(type, null);
    }

    /**
     * Method for checking whether instances of given type can be serialized,
     * and optionally why (as per {@link Throwable} returned).
     * 
     * @since 2.3
     */
    public boolean canSerialize(Class<?> type, AtomicReference<Throwable> cause) {
        return _serializerProvider(_config).hasSerializerFor(type, cause);
    }

    /*
    /**********************************************************
    /* Overridable helper methods
    /**********************************************************
     */

    /**
     * Overridable helper method used for constructing
     * {@link SerializerProvider} to use for serialization.
     */
    protected DefaultSerializerProvider _serializerProvider(SerializationConfig config) {
        return _serializerProvider.createInstance(config, _serializerFactory);
    }

    /*
    /**********************************************************
    /* Internal methods
    /**********************************************************
     */

    /**
     * @since 2.2
     */
    protected void _verifySchemaType(FormatSchema schema)
    {
        if (schema != null) {
            if (!_generatorFactory.canUseSchema(schema)) {
                    throw new IllegalArgumentException("Can not use FormatSchema of type "+schema.getClass().getName()
                            +" for format "+_generatorFactory.getFormatName());
            }
        }
    }

    /**
     * Method called to configure the generator as necessary and then
     * call write functionality
     */
    protected final void _configAndWriteValue(JsonGenerator gen, Object value) throws IOException
    {
        _configureGenerator(gen);
        // [JACKSON-282]: consider Closeable
        if (_config.isEnabled(SerializationFeature.CLOSE_CLOSEABLE) && (value instanceof Closeable)) {
            _writeCloseable(gen, value, _config);
            return;
        }
        boolean closed = false;
        try {
            if (_prefetch.valueSerializer != null) {
                _serializerProvider(_config).serializeValue(gen, value, _prefetch.rootType,
                        _prefetch.valueSerializer);
            } else if (_prefetch.typeSerializer != null) {
                _serializerProvider(_config).serializePolymorphic(gen, value,
                        _prefetch.rootType, _prefetch.typeSerializer);
            } else {
                _serializerProvider(_config).serializeValue(gen, value);
            }
            closed = true;
            gen.close();
        } finally {
            /* won't try to close twice; also, must catch exception (so it 
             * will not mask exception that is pending)
             */
            if (!closed) {
                /* 04-Mar-2014, tatu: But! Let's try to prevent auto-closing of
                 *    structures, which typically causes more damage.
                 */
                gen.disable(JsonGenerator.Feature.AUTO_CLOSE_JSON_CONTENT);
                try {
                    gen.close();
                } catch (IOException ioe) { }
            }
        }
    }

    /**
     * Helper method used when value to serialize is {@link Closeable} and its <code>close()</code>
     * method is to be called right after serialization has been called
     */
    private final void _writeCloseable(JsonGenerator gen, Object value, SerializationConfig cfg)
        throws IOException
    {
        Closeable toClose = (Closeable) value;
        try {
            if (_prefetch.valueSerializer != null) {
                _serializerProvider(cfg).serializeValue(gen, value, _prefetch.rootType,
                        _prefetch.valueSerializer);
            } else if (_prefetch.typeSerializer != null) {
                _serializerProvider(cfg).serializePolymorphic(gen, value,
                        _prefetch.rootType, _prefetch.typeSerializer);
            } else {
                _serializerProvider(cfg).serializeValue(gen, value);
            }
            JsonGenerator tmpGen = gen;
            gen = null;
            tmpGen.close();
            Closeable tmpToClose = toClose;
            toClose = null;
            tmpToClose.close();
        } finally {
            /* Need to close both generator and value, as long as they haven't yet
             * been closed
             */
            if (gen != null) {
                /* 04-Mar-2014, tatu: But! Let's try to prevent auto-closing of
                 *    structures, which typically causes more damage.
                 */
                gen.disable(JsonGenerator.Feature.AUTO_CLOSE_JSON_CONTENT);
                try {
                    gen.close();
                } catch (IOException ioe) { }
            }
            if (toClose != null) {
                try {
                    toClose.close();
                } catch (IOException ioe) { }
            }
        }
    }
    
    /**
     * Helper method used when value to serialize is {@link Closeable} and its <code>close()</code>
     * method is to be called right after serialization has been called
     */
    private final void _writeCloseableValue(JsonGenerator gen, Object value, SerializationConfig cfg)
        throws IOException
    {
        Closeable toClose = (Closeable) value;
        try {
            if (_prefetch.valueSerializer != null) {
                _serializerProvider(cfg).serializeValue(gen, value, _prefetch.rootType,
                        _prefetch.valueSerializer);
            } else if (_prefetch.typeSerializer != null) {
                _serializerProvider(cfg).serializePolymorphic(gen, value,
                        _prefetch.rootType, _prefetch.typeSerializer);
            } else {
                _serializerProvider(cfg).serializeValue(gen, value);
            }
            if (_config.isEnabled(SerializationFeature.FLUSH_AFTER_WRITE_VALUE)) {
                gen.flush();
            }
            Closeable tmpToClose = toClose;
            toClose = null;
            tmpToClose.close();
        } finally {
            if (toClose != null) {
                try {
                    toClose.close();
                } catch (IOException ioe) { }
            }
        }
    }

    /**
     * Method called to locate (root) serializer ahead of time, if permitted
     * by configuration. Method also is NOT to throw an exception if
     * access fails.
     */
    protected Prefetch _prefetchRootSerializer(SerializationConfig config, JavaType valueType)
    {
        if (valueType != null && _config.isEnabled(SerializationFeature.EAGER_SERIALIZER_FETCH)) {
            /* 17-Dec-2014, tatu: Need to be bit careful here; TypeSerializers are NOT cached,
             *   so although it'd seem like a good idea to look for those first, and avoid
             *   serializer for polymorphic types, it is actually more efficient to do the
             *   reverse here.
             */
            try {
                JsonSerializer<Object> ser = _serializerProvider(config).findTypedValueSerializer(valueType, true, null);
                // Important: for polymorphic types, "unwrap"...
                if (ser instanceof TypeWrappedSerializer) {
                    return Prefetch.construct(valueType, ((TypeWrappedSerializer) ser).typeSerializer());
                }
                return Prefetch.construct(valueType,  ser);
            } catch (JsonProcessingException e) {
                // need to swallow?
                ;
            }
        }
        return Prefetch.empty;
    }

    /**
     * Helper method called to set or override settings of passed-in
     * {@link JsonGenerator}
     * 
     * @since 2.5
     */
    protected final void _configureGenerator(JsonGenerator gen)
    {
        // order is slightly significant: both may change PrettyPrinter
        // settings.
        _config.initialize(gen); // since 2.5
        _generatorSettings.initialize(gen);
    }

    /*
    /**********************************************************
    /* Helper classes for configuration
    /**********************************************************
     */

    /**
     * Helper class used for containing settings specifically related
     * to (re)configuring {@link JsonGenerator} constructed for
     * writing output.
     * 
     * @since 2.5
     */
    public final static class GeneratorSettings
        implements java.io.Serializable
    {
        private static final long serialVersionUID = 1L;

        public final static GeneratorSettings empty = new GeneratorSettings(null, null, null, null);

        /**
         * To allow for dynamic enabling/disabling of pretty printing,
         * pretty printer can be optionally configured for writer
         * as well
         */
        public final PrettyPrinter prettyPrinter;

        /**
         * When using data format that uses a schema, schema is passed
         * to generator.
         */
        public final FormatSchema schema;

        /**
         * Caller may want to specify character escaping details, either as
         * defaults, or on call-by-call basis.
         */
        public final CharacterEscapes characterEscapes;

        /**
         * Caller may want to override so-called "root value separator",
         * String added (verbatim, with no quoting or escaping) between
         * values in root context. Default value is a single space character,
         * but this is often changed to linefeed.
         */
        public final SerializableString rootValueSeparator;

        public GeneratorSettings(PrettyPrinter pp, FormatSchema sch,
                CharacterEscapes esc, SerializableString rootSep) {
            prettyPrinter = pp;
            schema = sch;
            characterEscapes = esc;
            rootValueSeparator = rootSep;
        }

        public GeneratorSettings with(PrettyPrinter pp) {
            // since null would mean "don't care", need to use placeholder to indicate "disable"
            if (pp == null) {
                pp = NULL_PRETTY_PRINTER;
            }
            return (pp == prettyPrinter) ? this
                    : new GeneratorSettings(pp, schema, characterEscapes, rootValueSeparator);
        }

        public GeneratorSettings with(FormatSchema sch) {
            return (schema == sch) ? this
                    : new GeneratorSettings(prettyPrinter, sch, characterEscapes, rootValueSeparator);
        }

        public GeneratorSettings with(CharacterEscapes esc) {
            return (characterEscapes == esc) ? this
                    : new GeneratorSettings(prettyPrinter, schema, esc, rootValueSeparator);
        }

        public GeneratorSettings withRootValueSeparator(String sep) {
            if (sep == null) {
                if (rootValueSeparator == null) {
                    return this;
                }
            } else if (sep.equals(rootValueSeparator)) {
                return this;
            }
            return new GeneratorSettings(prettyPrinter, schema, characterEscapes,
                    (sep == null) ? null : new SerializedString(sep));
        }

        public GeneratorSettings withRootValueSeparator(SerializableString sep) {
            if (sep == null) {
                if (rootValueSeparator == null) {
                    return this;
                }
            } else {
                if (rootValueSeparator != null
                        && sep.getValue().equals(rootValueSeparator.getValue())) {
                    return this;
                }
            }
            return new GeneratorSettings(prettyPrinter, schema, characterEscapes, sep);
        }

        /**
         * @since 2.6
         */
        public void initialize(JsonGenerator gen)
        {
            PrettyPrinter pp = prettyPrinter;
            if (prettyPrinter != null) {
                if (pp == NULL_PRETTY_PRINTER) {
                    gen.setPrettyPrinter(null);
                } else {
                    if (pp instanceof Instantiatable<?>) {
                        pp = (PrettyPrinter) ((Instantiatable<?>) pp).createInstance();
                    }
                    gen.setPrettyPrinter(pp);
                }
            }
            if (characterEscapes != null) {
                gen.setCharacterEscapes(characterEscapes);
            }
            if (schema != null) {
                gen.setSchema(schema);
            }
            if (rootValueSeparator != null) {
                gen.setRootValueSeparator(rootValueSeparator);
            }
        }
    }

    /**
     * As a minor optimization, we will make an effort to pre-fetch a serializer,
     * or at least relevant <code>TypeSerializer</code>, if given enough
     * information.
     * 
     * @since 2.5
     */
    public final static class Prefetch
        implements java.io.Serializable
    {
        private static final long serialVersionUID = 1L;

        public final static Prefetch empty = new Prefetch(null, null, null);
        
        /**
         * Specified root serialization type to use; can be same
         * as runtime type, but usually one of its super types
         */
        public final JavaType rootType;

        /**
         * We may pre-fetch serializer if {@link #rootType}
         * is known, and if so, reuse it afterwards.
         * This allows avoiding further serializer lookups and increases
         * performance a bit on cases where readers are reused.
         */
        public final JsonSerializer<Object> valueSerializer;

        /**
         * When dealing with polymorphic types, we can not pre-fetch
         * serializer, but we can pre-fetch {@link TypeSerializer}.
         */
        public final TypeSerializer typeSerializer;
        
        private Prefetch(JavaType type, JsonSerializer<Object> ser, TypeSerializer typeSer)
        {
            rootType = type;
            valueSerializer = ser;
            typeSerializer = typeSer;
        }

        public static Prefetch construct(JavaType type, JsonSerializer<Object> ser) {
            if (type == null && ser == null) {
                return empty;
            }
            return new Prefetch(type, ser, null);
        }
        
        public static Prefetch construct(JavaType type, TypeSerializer typeSer) {
            if (type == null && typeSer == null) {
                return empty;
            }
            return new Prefetch(type, null, typeSer);
        }

        public boolean hasSerializer() {
            return (valueSerializer != null) || (typeSerializer != null);
        }
    }
}


File: src/main/java/com/fasterxml/jackson/databind/SequenceWriter.java
package com.fasterxml.jackson.databind;

import java.io.Closeable;
import java.io.IOException;
import java.util.Collection;

import com.fasterxml.jackson.core.*;
import com.fasterxml.jackson.databind.jsontype.TypeSerializer;
import com.fasterxml.jackson.databind.ser.DefaultSerializerProvider;
import com.fasterxml.jackson.databind.ser.impl.PropertySerializerMap;
import com.fasterxml.jackson.databind.ser.impl.TypeWrappedSerializer;

/**
 * Writer class similar to {@link ObjectWriter}, except that it can be used
 * for writing sequences of values, not just a single value.
 * The main use case is in writing very long sequences, or sequences where
 * values are incrementally produced; cases where it would be impractical
 * or at least inconvenient to construct a wrapper container around values
 * (or where no JSON array is desired around values).
 *<p>
 * Differences from {@link ObjectWriter} include:
 *<ul>
 *  <li>Instances of {@link SequenceWriter} are stateful, and not thread-safe:
 *    if sharing, external synchronization must be used.
 *  <li>Explicit {@link #close} is needed after all values have been written
 *     ({@link ObjectWriter} can auto-close after individual value writes)
 *</ul>
 * 
 * @since 2.5
 */
public class SequenceWriter
    implements Versioned, java.io.Closeable, java.io.Flushable
{
    /*
    /**********************************************************
    /* Configuration
    /**********************************************************
     */

    protected final DefaultSerializerProvider _provider;
    protected final SerializationConfig _config;
    protected final JsonGenerator _generator;

    protected final JsonSerializer<Object> _rootSerializer;
    protected final TypeSerializer _typeSerializer;
    
    protected final boolean _closeGenerator;
    protected final boolean _cfgFlush;
    protected final boolean _cfgCloseCloseable;

    /*
    /**********************************************************
    /* State
    /**********************************************************
     */

    /**
     * If {@link #_rootSerializer} is not defined (no root type
     * was used for constructing {@link ObjectWriter}), we will
     * use simple scheme for keeping track of serializers needed.
     * Assumption is that
     */
    protected PropertySerializerMap _dynamicSerializers;
    
    /**
     * State flag for keeping track of need to write matching END_ARRAY,
     * if a START_ARRAY was written during initialization
     */
    protected boolean _openArray;
    protected boolean _closed;

    /*
    /**********************************************************
    /* Life-cycle
    /**********************************************************
     */

    public SequenceWriter(DefaultSerializerProvider prov, JsonGenerator gen,
            boolean closeGenerator, ObjectWriter.Prefetch prefetch)
        throws IOException
    {
        _provider = prov;
        _generator = gen;
        _closeGenerator = closeGenerator;
        _rootSerializer = prefetch.valueSerializer;
        _typeSerializer = prefetch.typeSerializer;

        _config = prov.getConfig();
        _cfgFlush = _config.isEnabled(SerializationFeature.FLUSH_AFTER_WRITE_VALUE);
        _cfgCloseCloseable = _config.isEnabled(SerializationFeature.CLOSE_CLOSEABLE);
        // important: need to cache "root value" serializers, to handle polymorphic
        // types properly
        _dynamicSerializers = PropertySerializerMap.emptyForRootValues();
    }

    public SequenceWriter init(boolean wrapInArray) throws IOException
    {
        if (wrapInArray) {
            _generator.writeStartArray();
            _openArray = true;
        }
        return this;
    }

    /*
    /**********************************************************
    /* Public API, basic accessors
    /**********************************************************
     */

    /**
     * Method that will return version information stored in and read from jar
     * that contains this class.
     */
    @Override
    public Version version() {
        return com.fasterxml.jackson.databind.cfg.PackageVersion.VERSION;
    }

    /*
    /**********************************************************
    /* Public API, write operations, related
    /**********************************************************
     */

    /**
     * Method for writing given value into output, as part of sequence
     * to write. If root type was specified for {@link ObjectWriter},
     * value must be of compatible type (same or subtype).
     */
    public SequenceWriter write(Object value) throws IOException
    {
        if (value == null) {
            _provider.serializeValue(_generator, null);
            return this;
        }
        
        if (_cfgCloseCloseable && (value instanceof Closeable)) {
            return _writeCloseableValue(value);
        }
        JsonSerializer<Object> ser = _rootSerializer;
        if (ser == null) {
            Class<?> type = value.getClass();
            ser = _dynamicSerializers.serializerFor(type);
            if (ser == null) {
                ser = _findAndAddDynamic(type);
            }
        }
        _provider.serializeValue(_generator, value, null, ser);
        if (_cfgFlush) {
            _generator.flush();
        }
        return this;
    }

    /**
     * Method for writing given value into output, as part of sequence
     * to write; further, full type (often generic, like {@link java.util.Map}
     * is passed in case a new
     * {@link JsonSerializer} needs to be fetched to handle type
     * 
     * If root type was specified for {@link ObjectWriter},
     * value must be of compatible type (same or subtype).
     */
    public SequenceWriter write(Object value, JavaType type) throws IOException
    {
        if (value == null) {
            _provider.serializeValue(_generator, null);
            return this;
        }
        
        if (_cfgCloseCloseable && (value instanceof Closeable)) {
            return _writeCloseableValue(value, type);
        }
        /* 15-Dec-2014, tatu: I wonder if this could be come problematic. It shouldn't
         *   really, since trying to use differently paramterized types in a sequence
         *   is likely to run into other issues. But who knows; if it does become an
         *   issue, may need to implement alternative, JavaType-based map.
         */
        JsonSerializer<Object> ser = _dynamicSerializers.serializerFor(type.getRawClass());
        if (ser == null) {
            ser = _findAndAddDynamic(type);
        }
        _provider.serializeValue(_generator, value, type, ser);
        if (_cfgFlush) {
            _generator.flush();
        }
        return this;
    }

    public SequenceWriter writeAll(Object[] value) throws IOException
    {
        for (int i = 0, len = value.length; i < len; ++i) {
            write(value[i]);
        }
        return this;
    }

    public <C extends Collection<?>> SequenceWriter writeAll(C container) throws IOException
    {
        for (Object value : container) {
            write(value);
        }
        return this;
    }

    @Override
    public void flush() throws IOException {
        if (!_closed) {
            _generator.flush();
        }
    }

    @Override
    public void close() throws IOException
    {
        if (!_closed) {
            _closed = true;
            if (_openArray) {
                _openArray = false;
                _generator.writeEndArray();
            }
            if (_closeGenerator) {
                _generator.close();
            }
        }
    }

    /*
    /**********************************************************
    /* Internal helper methods, serializer lookups
    /**********************************************************
     */

    protected SequenceWriter _writeCloseableValue(Object value) throws IOException
    {
        Closeable toClose = (Closeable) value;
        try {
            JsonSerializer<Object> ser = _rootSerializer;
            if (ser == null) {
                Class<?> type = value.getClass();
                ser = _dynamicSerializers.serializerFor(type);
                if (ser == null) {
                    ser = _findAndAddDynamic(type);
                }
            }
            _provider.serializeValue(_generator, value, null, ser);
            if (_cfgFlush) {
                _generator.flush();
            }
            Closeable tmpToClose = toClose;
            toClose = null;
            tmpToClose.close();
        } finally {
            if (toClose != null) {
                try {
                    toClose.close();
                } catch (IOException ioe) { }
            }
        }
        return this;
    }

    protected SequenceWriter _writeCloseableValue(Object value, JavaType type) throws IOException
    {
        Closeable toClose = (Closeable) value;
        try {
            // 15-Dec-2014, tatu: As per above, could be problem that we do not pass generic type
            JsonSerializer<Object> ser = _dynamicSerializers.serializerFor(type.getRawClass());
            if (ser == null) {
                ser = _findAndAddDynamic(type);
            }
            _provider.serializeValue(_generator, value, type, ser);
            if (_cfgFlush) {
                _generator.flush();
            }
            Closeable tmpToClose = toClose;
            toClose = null;
            tmpToClose.close();
        } finally {
            if (toClose != null) {
                try {
                    toClose.close();
                } catch (IOException ioe) { }
            }
        }
        return this;
    }

    private final JsonSerializer<Object> _findAndAddDynamic(Class<?> type) throws JsonMappingException
    {
        PropertySerializerMap.SerializerAndMapResult result;
        if (_typeSerializer == null) {
            result = _dynamicSerializers.findAndAddRootValueSerializer(type, _provider);
        } else {
            result = _dynamicSerializers.addSerializer(type,
                    new TypeWrappedSerializer(_typeSerializer, _provider.findValueSerializer(type, null)));
        }
        _dynamicSerializers = result.map;
        return result.serializer;
    }

    private final JsonSerializer<Object> _findAndAddDynamic(JavaType type) throws JsonMappingException
    {
        PropertySerializerMap.SerializerAndMapResult result;
        if (_typeSerializer == null) {
            result = _dynamicSerializers.findAndAddRootValueSerializer(type, _provider);
        } else {
            result = _dynamicSerializers.addSerializer(type,
                    new TypeWrappedSerializer(_typeSerializer, _provider.findValueSerializer(type, null)));
        }
        _dynamicSerializers = result.map;
        return result.serializer;
    }
}


File: src/main/java/com/fasterxml/jackson/databind/cfg/MapperConfigBase.java
package com.fasterxml.jackson.databind.cfg;

import java.text.DateFormat;
import java.util.Locale;
import java.util.Map;
import java.util.TimeZone;

import com.fasterxml.jackson.annotation.JsonAutoDetect;
import com.fasterxml.jackson.annotation.PropertyAccessor;
import com.fasterxml.jackson.core.Base64Variant;
import com.fasterxml.jackson.databind.AnnotationIntrospector;
import com.fasterxml.jackson.databind.JavaType;
import com.fasterxml.jackson.databind.MapperFeature;
import com.fasterxml.jackson.databind.PropertyName;
import com.fasterxml.jackson.databind.PropertyNamingStrategy;
import com.fasterxml.jackson.databind.introspect.ClassIntrospector;
import com.fasterxml.jackson.databind.introspect.ClassIntrospector.MixInResolver;
import com.fasterxml.jackson.databind.introspect.SimpleMixInResolver;
import com.fasterxml.jackson.databind.introspect.VisibilityChecker;
import com.fasterxml.jackson.databind.jsontype.SubtypeResolver;
import com.fasterxml.jackson.databind.jsontype.TypeResolverBuilder;
import com.fasterxml.jackson.databind.type.TypeFactory;
import com.fasterxml.jackson.databind.util.RootNameLookup;

@SuppressWarnings("serial")
public abstract class MapperConfigBase<CFG extends ConfigFeature,
    T extends MapperConfigBase<CFG,T>>
    extends MapperConfig<T>
    implements java.io.Serializable
{
    private final static int DEFAULT_MAPPER_FEATURES = collectFeatureDefaults(MapperFeature.class);

    /*
    /**********************************************************
    /* Immutable config
    /**********************************************************
     */

    /**
     * Mix-in annotation mappings to use, if any: immutable,
     * can not be changed once defined.
     * 
     * @since 2.6
     */
    protected final SimpleMixInResolver _mixIns;

    /**
     * Registered concrete subtypes that can be used instead of (or
     * in addition to) ones declared using annotations.
     */
    protected final SubtypeResolver _subtypeResolver;

    /**
     * Explicitly defined root name to use, if any; if empty
     * String, will disable root-name wrapping; if null, will
     * use defaults
     */
    protected final PropertyName _rootName;

    /**
     * View to use for filtering out properties to serialize
     * or deserialize.
     * Null if none (will also be assigned null if <code>Object.class</code>
     * is defined), meaning that all properties are to be included.
     */
    protected final Class<?> _view;

    /**
     * Contextual attributes accessible (get and set) during processing,
     * on per-call basis.
     * 
     * @since 2.3
     */
    protected final ContextAttributes _attributes;

    /**
     * @since 2.6
     */
    protected final RootNameLookup _rootNames;
    
    /*
    /**********************************************************
    /* Construction
    /**********************************************************
     */

    /**
     * Constructor used when creating a new instance (compared to
     * that of creating fluent copies)
     */
    protected MapperConfigBase(BaseSettings base,
            SubtypeResolver str, SimpleMixInResolver mixins,
            RootNameLookup rootNames)
    {
        super(base, DEFAULT_MAPPER_FEATURES);
        _mixIns = mixins;
        _subtypeResolver = str;
        _rootNames = rootNames;
        _rootName = null;
        _view = null;
        // default to "no attributes"
        _attributes = ContextAttributes.getEmpty();
    }
    
    /**
     * Pass-through constructor used when no changes are needed to the
     * base class.
     */
    protected MapperConfigBase(MapperConfigBase<CFG,T> src)
    {
        super(src);
        _mixIns = src._mixIns;
        _subtypeResolver = src._subtypeResolver;
        _rootNames = src._rootNames;
        _rootName = src._rootName;
        _view = src._view;
        _attributes = src._attributes;
    }

    protected MapperConfigBase(MapperConfigBase<CFG,T> src, BaseSettings base)
    {
        super(src, base);
        _mixIns = src._mixIns;
        _subtypeResolver = src._subtypeResolver;
        _rootNames = src._rootNames;
        _rootName = src._rootName;
        _view = src._view;
        _attributes = src._attributes;
    }
    
    protected MapperConfigBase(MapperConfigBase<CFG,T> src, int mapperFeatures)
    {
        super(src, mapperFeatures);
        _mixIns = src._mixIns;
        _subtypeResolver = src._subtypeResolver;
        _rootNames = src._rootNames;
        _rootName = src._rootName;
        _view = src._view;
        _attributes = src._attributes;
    }

    protected MapperConfigBase(MapperConfigBase<CFG,T> src, SubtypeResolver str) {
        super(src);
        _mixIns = src._mixIns;
        _subtypeResolver = str;
        _rootNames = src._rootNames;
        _rootName = src._rootName;
        _view = src._view;
        _attributes = src._attributes;
    }

    protected MapperConfigBase(MapperConfigBase<CFG,T> src, PropertyName rootName) {
        super(src);
        _mixIns = src._mixIns;
        _subtypeResolver = src._subtypeResolver;
        _rootNames = src._rootNames;
        _rootName = rootName;
        _view = src._view;
        _attributes = src._attributes;
    }

    protected MapperConfigBase(MapperConfigBase<CFG,T> src, Class<?> view)
    {
        super(src);
        _mixIns = src._mixIns;
        _subtypeResolver = src._subtypeResolver;
        _rootNames = src._rootNames;
        _rootName = src._rootName;
        _view = view;
        _attributes = src._attributes;
    }

    /**
     * @since 2.1
     */
    protected MapperConfigBase(MapperConfigBase<CFG,T> src, SimpleMixInResolver mixins)
    {
        super(src);
        _mixIns = mixins;
        _subtypeResolver = src._subtypeResolver;
        _rootNames = src._rootNames;
        _rootName = src._rootName;
        _view = src._view;
        _attributes = src._attributes;
    }
    
    /**
     * @since 2.3
     */
    protected MapperConfigBase(MapperConfigBase<CFG,T> src, ContextAttributes attr)
    {
        super(src);
        _mixIns = src._mixIns;
        _subtypeResolver = src._subtypeResolver;
        _rootNames = src._rootNames;
        _rootName = src._rootName;
        _view = src._view;
        _attributes = attr;
    }

    /**
     * @since 2.6
     */
    protected MapperConfigBase(MapperConfigBase<CFG,T> src, SimpleMixInResolver mixins,
            RootNameLookup rootNames)
    {
        super(src);
        _mixIns = mixins;
        _subtypeResolver = src._subtypeResolver;
        _rootNames = rootNames;
        _rootName = src._rootName;
        _view = src._view;
        _attributes = src._attributes;
    }
    
    /*
    /**********************************************************
    /* Addition fluent factory methods, common to all sub-types
    /**********************************************************
     */

    /**
     * Method for constructing and returning a new instance with different
     * {@link AnnotationIntrospector} to use (replacing old one).
     *<p>
     * NOTE: make sure to register new instance with <code>ObjectMapper</code>
     * if directly calling this method.
     */
    public abstract T with(AnnotationIntrospector ai);

    /**
     * Method for constructing and returning a new instance with additional
     * {@link AnnotationIntrospector} appended (as the lowest priority one)
     */
    public abstract T withAppendedAnnotationIntrospector(AnnotationIntrospector introspector);

    /**
     * Method for constructing and returning a new instance with additional
     * {@link AnnotationIntrospector} inserted (as the highest priority one)
     */
    public abstract T withInsertedAnnotationIntrospector(AnnotationIntrospector introspector);
    
    /**
     * Method for constructing and returning a new instance with different
     * {@link ClassIntrospector}
     * to use.
     *<p>
     * NOTE: make sure to register new instance with <code>ObjectMapper</code>
     * if directly calling this method.
     */
    public abstract T with(ClassIntrospector ci);

    /**
     * Method for constructing and returning a new instance with different
     * {@link DateFormat}
     * to use.
     *<p>
     * NOTE: make sure to register new instance with <code>ObjectMapper</code>
     * if directly calling this method.
     */
    public abstract T with(DateFormat df);

    /**
     * Method for constructing and returning a new instance with different
     * {@link HandlerInstantiator}
     * to use.
     *<p>
     * NOTE: make sure to register new instance with <code>ObjectMapper</code>
     * if directly calling this method.
     */
    public abstract T with(HandlerInstantiator hi);
    
    /**
     * Method for constructing and returning a new instance with different
     * {@link PropertyNamingStrategy}
     * to use.
     *<p>
     * NOTE: make sure to register new instance with <code>ObjectMapper</code>
     * if directly calling this method.
     */
    public abstract T with(PropertyNamingStrategy strategy);
    
    /**
     * Method for constructing and returning a new instance with different
     * root name to use (none, if null).
     *<p>
     * Note that when a root name is set to a non-Empty String, this will automatically force use
     * of root element wrapping with given name. If empty String passed, will
     * disable root name wrapping; and if null used, will instead use
     * <code>SerializationFeature</code> to determine if to use wrapping, and annotation
     * (or default name) for actual root name to use.
     * 
     * @param rootName to use: if null, means "use default" (clear setting);
     *   if empty String ("") means that no root name wrapping is used;
     *   otherwise defines root name to use.
     *   
     * @since 2.6
     */
    public abstract T withRootName(PropertyName rootName);

    public T withRootName(String rootName) {
        if (rootName == null) {
            return withRootName((PropertyName) null);
        }
        return withRootName(PropertyName.construct(rootName));
    }
    
    /**
     * Method for constructing and returning a new instance with different
     * {@link SubtypeResolver}
     * to use.
     *<p>
     * NOTE: make sure to register new instance with <code>ObjectMapper</code>
     * if directly calling this method.
     */
    public abstract T with(SubtypeResolver str);
    
    /**
     * Method for constructing and returning a new instance with different
     * {@link TypeFactory}
     * to use.
     */
    public abstract T with(TypeFactory typeFactory);

    /**
     * Method for constructing and returning a new instance with different
     * {@link TypeResolverBuilder} to use.
     */
    public abstract T with(TypeResolverBuilder<?> trb);

    /**
     * Method for constructing and returning a new instance with different
     * view to use.
     */
    public abstract T withView(Class<?> view);
    
    /**
     * Method for constructing and returning a new instance with different
     * {@link VisibilityChecker}
     * to use.
     */
    public abstract T with(VisibilityChecker<?> vc);

    /**
     * Method for constructing and returning a new instance with different
     * minimal visibility level for specified property type
     */
    public abstract T withVisibility(PropertyAccessor forMethod, JsonAutoDetect.Visibility visibility);

    /**
     * Method for constructing and returning a new instance with different
     * default {@link java.util.Locale} to use for formatting.
     */
    public abstract T with(Locale l);

    /**
     * Method for constructing and returning a new instance with different
     * default {@link java.util.TimeZone} to use for formatting of date values.
     */
    public abstract T with(TimeZone tz);

    /**
     * Method for constructing and returning a new instance with different
     * default {@link Base64Variant} to use with base64-encoded binary values.
     */
    public abstract T with(Base64Variant base64);

    /**
     * Method for constructing an instance that has specified
     * contextual attributes.
     * 
     * @since 2.3
     */
    public abstract T with(ContextAttributes attrs);

    /**
     * Method for constructing an instance that has only specified
     * attributes, removing any attributes that exist before the call.
     * 
     * @since 2.3
     */
    public T withAttributes(Map<Object,Object> attributes) {
        return with(getAttributes().withSharedAttributes(attributes));
    }
    
    /**
     * Method for constructing an instance that has specified
     * value for attribute for given key.
     * 
     * @since 2.3
     */
    public T withAttribute(Object key, Object value) {
        return with(getAttributes().withSharedAttribute(key, value));
    }

    /**
     * Method for constructing an instance that has no
     * value for attribute for given key.
     * 
     * @since 2.3
     */
    public T withoutAttribute(Object key) {
        return with(getAttributes().withoutSharedAttribute(key));
    }
    
    /*
    /**********************************************************
    /* Simple accessors
    /**********************************************************
     */
    
    /**
     * Accessor for object used for finding out all reachable subtypes
     * for supertypes; needed when a logical type name is used instead
     * of class name (or custom scheme).
     */
    @Override
    public final SubtypeResolver getSubtypeResolver() {
        return _subtypeResolver;
    }

    /**
     * @deprecated Since 2.6 use {@link #getFullRootName} instead.
     */
    @Deprecated // since 2.6
    public final String getRootName() {
        return (_rootName == null) ? null : _rootName.getSimpleName();
    }

    /**
     * @since 2.6
     */
    public final PropertyName getFullRootName() {
        return _rootName;
    }

    public final Class<?> getActiveView() {
        return _view;
    }

    @Override
    public final ContextAttributes getAttributes() {
        return _attributes;
    }

    /*
    /**********************************************************
    /* Other config access
    /**********************************************************
     */

    @Override
    public PropertyName findRootName(JavaType rootType) {
        if (_rootName != null) {
            return _rootName;
        }
        return _rootNames.findRootName(rootType, this);
    }

    @Override
    public PropertyName findRootName(Class<?> rawRootType) {
        if (_rootName != null) {
            return _rootName;
        }
        return _rootNames.findRootName(rawRootType, this);
    }
    
    /*
    /**********************************************************
    /* ClassIntrospector.MixInResolver impl:
    /**********************************************************
     */

    /**
     * Method that will check if there are "mix-in" classes (with mix-in
     * annotations) for given class
     */
    @Override
    public final Class<?> findMixInClassFor(Class<?> cls) {
        return _mixIns.findMixInClassFor(cls);
    }

    // Not really relevant here (should not get called)
    @Override
    public MixInResolver copy() {
        throw new UnsupportedOperationException();
    }
    
    /**
     * Test-only method -- does not reflect possibly open-ended set that external
     * mix-in resolver might provide.
     */
    public final int mixInCount() {
        return _mixIns.localSize();
    }
}


File: src/main/java/com/fasterxml/jackson/databind/ser/DefaultSerializerProvider.java
package com.fasterxml.jackson.databind.ser;

import java.io.IOException;
import java.util.*;
import java.util.concurrent.atomic.AtomicReference;

import com.fasterxml.jackson.annotation.ObjectIdGenerator;
import com.fasterxml.jackson.core.JsonGenerator;
import com.fasterxml.jackson.databind.*;
import com.fasterxml.jackson.databind.cfg.HandlerInstantiator;
import com.fasterxml.jackson.databind.introspect.Annotated;
import com.fasterxml.jackson.databind.jsonFormatVisitors.JsonFormatVisitorWrapper;
import com.fasterxml.jackson.databind.jsonschema.SchemaAware;
import com.fasterxml.jackson.databind.jsontype.TypeSerializer;
import com.fasterxml.jackson.databind.node.ObjectNode;
import com.fasterxml.jackson.databind.ser.impl.WritableObjectId;
import com.fasterxml.jackson.databind.util.ClassUtil;

/**
 * Standard implementation used by {@link ObjectMapper}:
 * adds methods only exposed to {@link ObjectMapper},
 * as well as constructors.
 *<p>
 * Note that class is abstract just because it does not
 * define {@link #createInstance} method.
 *<p>
 * Also note that all custom {@link SerializerProvider}
 * implementations must sub-class this class: {@link ObjectMapper}
 * requires this type, not basic provider type.
 */
public abstract class DefaultSerializerProvider
    extends SerializerProvider
    implements java.io.Serializable // since 2.1; only because ObjectWriter needs it
{
    private static final long serialVersionUID = 1L;

    /*
    /**********************************************************
    /* State, for non-blueprint instances: Object Id handling
    /**********************************************************
     */

    /**
     * Per-serialization map Object Ids that have seen so far, iff
     * Object Id handling is enabled.
     */
    protected transient Map<Object, WritableObjectId> _seenObjectIds;
    
    protected transient ArrayList<ObjectIdGenerator<?>> _objectIdGenerators;
    
    /*
    /**********************************************************
    /* Life-cycle
    /**********************************************************
     */

    protected DefaultSerializerProvider() { super(); }

    protected DefaultSerializerProvider(SerializerProvider src,
            SerializationConfig config,SerializerFactory f) {
        super(src, config, f);
    }

    protected DefaultSerializerProvider(DefaultSerializerProvider src) {
        super(src);
    }

    /**
     * Method needed to ensure that {@link ObjectMapper#copy} will work
     * properly; specifically, that caches are cleared, but settings
     * will otherwise remain identical; and that no sharing of state
     * occurs.
     *
     * @since 2.5
     */
    public DefaultSerializerProvider copy() {
        throw new IllegalStateException("DefaultSerializerProvider sub-class not overriding copy()");
    }
    
    /*
    /**********************************************************
    /* Extended API: methods that ObjectMapper will call
    /**********************************************************
     */

    /**
     * Overridable method, used to create a non-blueprint instances from the blueprint.
     * This is needed to retain state during serialization.
     */
    public abstract DefaultSerializerProvider createInstance(SerializationConfig config,
            SerializerFactory jsf);

    /**
     * The method to be called by {@link ObjectMapper} and {@link ObjectWriter}
     * for serializing given value, using serializers that
     * this provider has access to (via caching and/or creating new serializers
     * as need be).
     */
    public void serializeValue(JsonGenerator gen, Object value) throws IOException
    {
        if (value == null) {
            _serializeNull(gen);
            return;
        }
        Class<?> cls = value.getClass();
        // true, since we do want to cache root-level typed serializers (ditto for null property)
        final JsonSerializer<Object> ser = findTypedValueSerializer(cls, true, null);

        // Ok: should we wrap result in an additional property ("root name")?
        final boolean wrap;
        PropertyName rootName = _config.getFullRootName();

        if (rootName == null) { // not explicitly specified
            // [JACKSON-163]
            wrap = _config.isEnabled(SerializationFeature.WRAP_ROOT_VALUE);
            if (wrap) {
                gen.writeStartObject();
                PropertyName pname = _config.findRootName(value.getClass());
                gen.writeFieldName(pname.simpleAsEncoded(_config));
            }
        } else if (rootName.isEmpty()) {
            wrap = false;
        } else { // [JACKSON-764]
            // empty String means explicitly disabled; non-empty that it is enabled
            wrap = true;
            gen.writeStartObject();
            gen.writeFieldName(rootName.getSimpleName());
        }
        try {
            ser.serialize(value, gen, this);
            if (wrap) {
                gen.writeEndObject();
            }
        } catch (IOException ioe) { // As per [JACKSON-99], pass IOException and subtypes as-is
            throw ioe;
        } catch (Exception e) { // but wrap RuntimeExceptions, to get path information
            String msg = e.getMessage();
            if (msg == null) {
                msg = "[no message for "+e.getClass().getName()+"]";
            }
            throw new JsonMappingException(msg, e);
        }
    }

    /**
     * The method to be called by {@link ObjectMapper} and {@link ObjectWriter}
     * for serializing given value (assumed to be of specified root type,
     * instead of runtime type of value),
     * using serializers that
     * this provider has access to (via caching and/or creating new serializers
     * as need be),
     * 
     * @param rootType Type to use for locating serializer to use, instead of actual
     *    runtime type. Must be actual type, or one of its super types
     */
    public void serializeValue(JsonGenerator gen, Object value, JavaType rootType) throws IOException
    {
        if (value == null) {
            _serializeNull(gen);
            return;
        }
        // Let's ensure types are compatible at this point
        if (!rootType.getRawClass().isAssignableFrom(value.getClass())) {
            _reportIncompatibleRootType(value, rootType);
        }
        // root value, not reached via property:
        JsonSerializer<Object> ser = findTypedValueSerializer(rootType, true, null);

        // Ok: should we wrap result in an additional property ("root name")?
        final boolean wrap;
        PropertyName rootName = _config.getFullRootName();
        if (rootName == null) { // not explicitly specified
            // [JACKSON-163]
            wrap = _config.isEnabled(SerializationFeature.WRAP_ROOT_VALUE);
            if (wrap) {
                gen.writeStartObject();
                PropertyName pname = _config.findRootName(value.getClass());
                gen.writeFieldName(pname.simpleAsEncoded(_config));
            }
        } else if (rootName.isEmpty()) {
            wrap = false;
        } else { // [JACKSON-764]
            // empty String means explicitly disabled; non-empty that it is enabled
            wrap = true;
            gen.writeStartObject();
            gen.writeFieldName(rootName.getSimpleName());
        }
        try {
            ser.serialize(value, gen, this);
            if (wrap) {
                gen.writeEndObject();
            }
        } catch (IOException ioe) { // no wrapping for IO (and derived)
            throw ioe;
        } catch (Exception e) { // but others do need to be, to get path etc
            String msg = e.getMessage();
            if (msg == null) {
                msg = "[no message for "+e.getClass().getName()+"]";
            }
            throw new JsonMappingException(msg, e);
        }
    }

    /**
     * The method to be called by {@link ObjectWriter}
     * for serializing given value (assumed to be of specified root type,
     * instead of runtime type of value), when it may know specific
     * {@link JsonSerializer} to use.
     * 
     * @param rootType Type to use for locating serializer to use, instead of actual
     *    runtime type, if no serializer is passed
     * @param ser Root Serializer to use, if not null
     * 
     * @since 2.1
     */
    public void serializeValue(JsonGenerator gen, Object value, JavaType rootType, JsonSerializer<Object> ser) throws IOException
    {
        if (value == null) {
            _serializeNull(gen);
            return;
        }
        // Let's ensure types are compatible at this point
        if ((rootType != null) && !rootType.getRawClass().isAssignableFrom(value.getClass())) {
            _reportIncompatibleRootType(value, rootType);
        }
        // root value, not reached via property:
        if (ser == null) {
            ser = findTypedValueSerializer(rootType, true, null);
        }
        // Ok: should we wrap result in an additional property ("root name")?
        final boolean wrap;
        PropertyName rootName = _config.getFullRootName();
        if (rootName == null) { // not explicitly specified
            // [JACKSON-163]
            wrap = _config.isEnabled(SerializationFeature.WRAP_ROOT_VALUE);
            if (wrap) {
                gen.writeStartObject();
                PropertyName pname = (rootType == null)
                        ? _config.findRootName(value.getClass())
                        : _config.findRootName(rootType);
                gen.writeFieldName(pname.simpleAsEncoded(_config));
            }
        } else if (rootName.isEmpty()) {
            wrap = false;
        } else { // [JACKSON-764]
            // empty String means explicitly disabled; non-empty that it is enabled
            wrap = true;
            gen.writeStartObject();
            gen.writeFieldName(rootName.getSimpleName());
        }
        try {
            ser.serialize(value, gen, this);
            if (wrap) {
                gen.writeEndObject();
            }
        } catch (IOException ioe) { // no wrapping for IO (and derived)
            throw ioe;
        } catch (Exception e) { // but others do need to be, to get path etc
            String msg = e.getMessage();
            if (msg == null) {
                msg = "[no message for "+e.getClass().getName()+"]";
            }
            throw new JsonMappingException(msg, e);
        }
    }

    /**
     * Alternate serialization call used for polymorphic types, when {@link TypeSerializer}
     * is already known, but not actual value serializer.
     *
     * @since 2.6
     */
    public void serializePolymorphic(JsonGenerator gen, Object value,
            JavaType rootType, TypeSerializer typeSer)
        throws IOException
    {
        if (value == null) {
            _serializeNull(gen);
            return;
        }
        // Let's ensure types are compatible at this point
        if ((rootType != null) && !rootType.getRawClass().isAssignableFrom(value.getClass())) {
            _reportIncompatibleRootType(value, rootType);
        }
        JsonSerializer<Object> ser;
        /* 12-Jun-2015, tatu: nominal root type is necessary for Maps at least;
         *   possibly collections, but can cause problems for other polymorphic
         *   types. We really need to distinguish between serialization type,
         *   base type; but right we don't. Hence this check
         */
        if ((rootType != null) && rootType.isContainerType()) {
            ser = findValueSerializer(rootType, null);
        } else {
            ser = findValueSerializer(value.getClass(), null);
        }

        final boolean wrap;
        PropertyName rootName = _config.getFullRootName();
        if (rootName == null) {
            wrap = _config.isEnabled(SerializationFeature.WRAP_ROOT_VALUE);
            if (wrap) {
                gen.writeStartObject();
                PropertyName pname = _config.findRootName(value.getClass());
                gen.writeFieldName(pname.simpleAsEncoded(_config));
            }
        } else if (rootName.isEmpty()) {
            wrap = false;
        } else {
            wrap = true;
            gen.writeStartObject();
            gen.writeFieldName(rootName.getSimpleName());
        }
        try {
            ser.serializeWithType(value, gen, this, typeSer);
            if (wrap) {
                gen.writeEndObject();
            }
        } catch (IOException ioe) { // no wrapping for IO (and derived)
            throw ioe;
        } catch (Exception e) { // but others do need to be, to get path etc
            String msg = e.getMessage();
            if (msg == null) {
                msg = "[no message for "+e.getClass().getName()+"]";
            }
            throw new JsonMappingException(msg, e);
        }
    }

    /**
     * @deprecated since 2.6; remove from 2.7 or later
     */
    @Deprecated
    public void serializePolymorphic(JsonGenerator gen, Object value, TypeSerializer typeSer)
            throws IOException
    {
        JavaType t = (value == null) ? null : _config.constructType(value.getClass());
        serializePolymorphic(gen, value, t, typeSer);
    }

    /**
     * Helper method called when root value to serialize is null
     * 
     * @since 2.3
     */
    protected void _serializeNull(JsonGenerator gen) throws IOException
    {
        JsonSerializer<Object> ser = getDefaultNullValueSerializer();
        try {
            ser.serialize(null, gen, this);
        } catch (IOException ioe) { // no wrapping for IO (and derived)
            throw ioe;
        } catch (Exception e) { // but others do need to be, to get path etc
            String msg = e.getMessage();
            if (msg == null) {
                msg = "[no message for "+e.getClass().getName()+"]";
            }
            throw new JsonMappingException(msg, e);
        }
    }

    /**
     * The method to be called by {@link ObjectMapper}
     * to generate <a href="http://json-schema.org/">JSON schema</a> for
     * given type.
     *
     * @param type The type for which to generate schema
     * 
     * @deprecated Should not be used any more
     */
    @Deprecated // since 2.6
    public com.fasterxml.jackson.databind.jsonschema.JsonSchema generateJsonSchema(Class<?> type)
        throws JsonMappingException
    {
        if (type == null) {
            throw new IllegalArgumentException("A class must be provided");
        }
        /* no need for embedded type information for JSON schema generation (all
         * type information it needs is accessible via "untyped" serializer)
         */
        JsonSerializer<Object> ser = findValueSerializer(type, null);
        JsonNode schemaNode = (ser instanceof SchemaAware) ?
                ((SchemaAware) ser).getSchema(this, null) : com.fasterxml.jackson.databind.jsonschema.JsonSchema.getDefaultSchemaNode();
        if (!(schemaNode instanceof ObjectNode)) {
            throw new IllegalArgumentException("Class " + type.getName()
                    +" would not be serialized as a JSON object and therefore has no schema");
        }
        return new com.fasterxml.jackson.databind.jsonschema.JsonSchema((ObjectNode) schemaNode);
    }
    
    /**
     * The method to be called by {@link ObjectMapper} and {@link ObjectWriter}
     * to to expose the format of the given to to the given visitor
     *
     * @param javaType The type for which to generate format
     * @param visitor the visitor to accept the format
     */
    public void acceptJsonFormatVisitor(JavaType javaType, JsonFormatVisitorWrapper visitor)
        throws JsonMappingException
    {
        if (javaType == null) {
            throw new IllegalArgumentException("A class must be provided");
        }
        /* no need for embedded type information for JSON schema generation (all
         * type information it needs is accessible via "untyped" serializer)
         */
        visitor.setProvider(this);
        findValueSerializer(javaType, null).acceptJsonFormatVisitor(visitor, javaType);
    }

    /**
     * Method that can be called to see if this serializer provider
     * can find a serializer for an instance of given class.
     *<p>
     * Note that no Exceptions are thrown, including unchecked ones:
     * implementations are to swallow exceptions if necessary.
     */
    public boolean hasSerializerFor(Class<?> cls, AtomicReference<Throwable> cause)
    {
        try {
            JsonSerializer<?> ser = _findExplicitUntypedSerializer(cls);
            return (ser != null);
        } catch (JsonMappingException e) {
            if (cause != null) {
                cause.set(e);
            }
        } catch (RuntimeException e) {
            if (cause == null) { // earlier behavior
                throw e;
            }
            cause.set(e);
        }
        return false;
    }

    /*
    /********************************************************
    /* Access to caching details
    /********************************************************
     */

    /**
     * Method that can be used to determine how many serializers this
     * provider is caching currently
     * (if it does caching: default implementation does)
     * Exact count depends on what kind of serializers get cached;
     * default implementation caches all serializers, including ones that
     * are eagerly constructed (for optimal access speed)
     *<p> 
     * The main use case for this method is to allow conditional flushing of
     * serializer cache, if certain number of entries is reached.
     */
    public int cachedSerializersCount() {
        return _serializerCache.size();
    }

    /**
     * Method that will drop all serializers currently cached by this provider.
     * This can be used to remove memory usage (in case some serializers are
     * only used once or so), or to force re-construction of serializers after
     * configuration changes for mapper than owns the provider.
     */
    public void flushCachedSerializers() {
        _serializerCache.flush();
    }

    /*
    /**********************************************************
    /* Object Id handling
    /**********************************************************
     */
    
    @Override
    public WritableObjectId findObjectId(Object forPojo, ObjectIdGenerator<?> generatorType)
    {
        if (_seenObjectIds == null) {
            _seenObjectIds = _createObjectIdMap();
        } else {
            WritableObjectId oid = _seenObjectIds.get(forPojo);
            if (oid != null) {
                return oid;
            }
        }
        // Not seen yet; must add an entry, return it. For that, we need generator
        ObjectIdGenerator<?> generator = null;
        
        if (_objectIdGenerators == null) {
            _objectIdGenerators = new ArrayList<ObjectIdGenerator<?>>(8);
        } else {
            for (int i = 0, len = _objectIdGenerators.size(); i < len; ++i) {
                ObjectIdGenerator<?> gen = _objectIdGenerators.get(i);
                if (gen.canUseFor(generatorType)) {
                    generator = gen;
                    break;
                }
            }
        }
        if (generator == null) {
            generator = generatorType.newForSerialization(this);
            _objectIdGenerators.add(generator);
        }
        WritableObjectId oid = new WritableObjectId(generator);
        _seenObjectIds.put(forPojo, oid);
        return oid;
    }

    /**
     * Overridable helper method used for creating {@link java.util.Map}
     * used for storing mappings from serializable objects to their
     * Object Ids.
     * 
     * @since 2.3
     */
    protected Map<Object,WritableObjectId> _createObjectIdMap()
    {
        /* 06-Aug-2013, tatu: We may actually want to use equality,
         *   instead of identity... so:
         */
        if (isEnabled(SerializationFeature.USE_EQUALITY_FOR_OBJECT_ID)) {
            return new HashMap<Object,WritableObjectId>();
        }
        return new IdentityHashMap<Object,WritableObjectId>();
    }
    
    /*
    /**********************************************************
    /* Factory method impls
    /**********************************************************
     */
    
    @Override
    public JsonSerializer<Object> serializerInstance(Annotated annotated, Object serDef) throws JsonMappingException
    {
        if (serDef == null) {
            return null;
        }
        JsonSerializer<?> ser;
        
        if (serDef instanceof JsonSerializer) {
            ser = (JsonSerializer<?>) serDef;
        } else {
            /* Alas, there's no way to force return type of "either class
             * X or Y" -- need to throw an exception after the fact
             */
            if (!(serDef instanceof Class)) {
                throw new IllegalStateException("AnnotationIntrospector returned serializer definition of type "
                        +serDef.getClass().getName()+"; expected type JsonSerializer or Class<JsonSerializer> instead");
            }
            Class<?> serClass = (Class<?>)serDef;
            // there are some known "no class" markers to consider too:
            if (serClass == JsonSerializer.None.class || ClassUtil.isBogusClass(serClass)) {
                return null;
            }
            if (!JsonSerializer.class.isAssignableFrom(serClass)) {
                throw new IllegalStateException("AnnotationIntrospector returned Class "
                        +serClass.getName()+"; expected Class<JsonSerializer>");
            }
            HandlerInstantiator hi = _config.getHandlerInstantiator();
            ser = (hi == null) ? null : hi.serializerInstance(_config, annotated, serClass);
            if (ser == null) {
                ser = (JsonSerializer<?>) ClassUtil.createInstance(serClass,
                        _config.canOverrideAccessModifiers());
            }
        }
        return (JsonSerializer<Object>) _handleResolvable(ser);
    }

    /*
    /**********************************************************
    /* Helper classes
    /**********************************************************
     */

    /**
     * Concrete implementation that defines factory method(s),
     * defined as final.
     */
    public final static class Impl extends DefaultSerializerProvider {
        private static final long serialVersionUID = 1L;

        public Impl() { super(); }
        public Impl(Impl src) { super(src); }

        protected Impl(SerializerProvider src, SerializationConfig config,SerializerFactory f) {
            super(src, config, f);
        }

        @Override
        public DefaultSerializerProvider copy()
        {
            if (getClass() != Impl.class) {
                return super.copy();
            }
            return new Impl(this);
        }
        
        @Override
        public Impl createInstance(SerializationConfig config, SerializerFactory jsf) {
            return new Impl(this, config, jsf);
        }
    }
}


File: src/test/java/com/fasterxml/jackson/databind/seq/PolyMapWriter827Test.java
package com.fasterxml.jackson.databind.seq;

import java.io.IOException;
import java.util.HashMap;
import java.util.Map;

import org.junit.Assert;

import com.fasterxml.jackson.core.JsonGenerator;
import com.fasterxml.jackson.core.JsonProcessingException;
import com.fasterxml.jackson.core.type.TypeReference;
import com.fasterxml.jackson.databind.*;
import com.fasterxml.jackson.databind.module.SimpleModule;

// for [databind#827]
public class PolyMapWriter827Test extends BaseMapTest
{
    static class CustomKey {
        String a;
        int b;

        public String toString() { return "BAD-KEY"; }
    }

    public class CustomKeySerializer extends JsonSerializer<CustomKey> {
        @Override
        public void serialize(CustomKey key, JsonGenerator jsonGenerator, SerializerProvider serializerProvider) throws IOException, JsonProcessingException {
            jsonGenerator.writeFieldName(key.a + "," + key.b);
        }
    }

    public void testPolyCustomKeySerializer() throws Exception
    {
        ObjectMapper mapper = new ObjectMapper();
        mapper.enableDefaultTyping(ObjectMapper.DefaultTyping.NON_FINAL);

        mapper.registerModule(new SimpleModule("keySerializerModule")
            .addKeySerializer(CustomKey.class, new CustomKeySerializer()));

        Map<CustomKey, String> map = new HashMap<CustomKey, String>();
        CustomKey key = new CustomKey();
        key.a = "foo";
        key.b = 1;
        map.put(key, "bar");

        final ObjectWriter writer = mapper.writerFor(new TypeReference<Map<CustomKey,String>>() { });
        String json = writer.writeValueAsString(map);
        Assert.assertEquals("[\"java.util.HashMap\",{\"foo,1\":\"bar\"}]", json);
    }
}
