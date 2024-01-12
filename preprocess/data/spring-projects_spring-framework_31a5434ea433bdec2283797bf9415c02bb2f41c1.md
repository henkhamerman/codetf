Refactoring Types: ['Extract Method']
pringframework/http/converter/AbstractHttpMessageConverter.java
/*
 * Copyright 2002-2015 the original author or authors.
 *
 * Licensed under the Apache License, Version 2.0 (the "License");
 * you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at
 *
 *      http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 */

package org.springframework.http.converter;

import java.io.IOException;
import java.io.OutputStream;
import java.util.ArrayList;
import java.util.Arrays;
import java.util.Collections;
import java.util.List;

import org.apache.commons.logging.Log;
import org.apache.commons.logging.LogFactory;

import org.springframework.http.HttpHeaders;
import org.springframework.http.HttpInputMessage;
import org.springframework.http.HttpOutputMessage;
import org.springframework.http.MediaType;
import org.springframework.http.StreamingHttpOutputMessage;
import org.springframework.util.Assert;

/**
 * Abstract base class for most {@link HttpMessageConverter} implementations.
 *
 * <p>This base class adds support for setting supported {@code MediaTypes}, through the
 * {@link #setSupportedMediaTypes(List) supportedMediaTypes} bean property. It also adds
 * support for {@code Content-Type} and {@code Content-Length} when writing to output messages.
 *
 * @author Arjen Poutsma
 * @author Juergen Hoeller
 * @since 3.0
 */
public abstract class AbstractHttpMessageConverter<T> implements HttpMessageConverter<T> {

	/** Logger available to subclasses */
	protected final Log logger = LogFactory.getLog(getClass());

	private List<MediaType> supportedMediaTypes = Collections.emptyList();


	/**
	 * Construct an {@code AbstractHttpMessageConverter} with no supported media types.
	 * @see #setSupportedMediaTypes
	 */
	protected AbstractHttpMessageConverter() {
	}

	/**
	 * Construct an {@code AbstractHttpMessageConverter} with one supported media type.
	 * @param supportedMediaType the supported media type
	 */
	protected AbstractHttpMessageConverter(MediaType supportedMediaType) {
		setSupportedMediaTypes(Collections.singletonList(supportedMediaType));
	}

	/**
	 * Construct an {@code AbstractHttpMessageConverter} with multiple supported media type.
	 * @param supportedMediaTypes the supported media types
	 */
	protected AbstractHttpMessageConverter(MediaType... supportedMediaTypes) {
		setSupportedMediaTypes(Arrays.asList(supportedMediaTypes));
	}


	/**
	 * Set the list of {@link MediaType} objects supported by this converter.
	 */
	public void setSupportedMediaTypes(List<MediaType> supportedMediaTypes) {
		Assert.notEmpty(supportedMediaTypes, "'supportedMediaTypes' must not be empty");
		this.supportedMediaTypes = new ArrayList<MediaType>(supportedMediaTypes);
	}

	@Override
	public List<MediaType> getSupportedMediaTypes() {
		return Collections.unmodifiableList(this.supportedMediaTypes);
	}


	/**
	 * This implementation checks if the given class is {@linkplain #supports(Class) supported},
	 * and if the {@linkplain #getSupportedMediaTypes() supported media types}
	 * {@linkplain MediaType#includes(MediaType) include} the given media type.
	 */
	@Override
	public boolean canRead(Class<?> clazz, MediaType mediaType) {
		return supports(clazz) && canRead(mediaType);
	}

	/**
	 * Returns true if any of the {@linkplain #setSupportedMediaTypes(List) supported media types}
	 * include the given media type.
	 * @param mediaType the media type to read, can be {@code null} if not specified.
	 * Typically the value of a {@code Content-Type} header.
	 * @return {@code true} if the supported media types include the media type,
	 * or if the media type is {@code null}
	 */
	protected boolean canRead(MediaType mediaType) {
		if (mediaType == null) {
			return true;
		}
		for (MediaType supportedMediaType : getSupportedMediaTypes()) {
			if (supportedMediaType.includes(mediaType)) {
				return true;
			}
		}
		return false;
	}

	/**
	 * This implementation checks if the given class is {@linkplain #supports(Class) supported},
	 * and if the {@linkplain #getSupportedMediaTypes() supported media types}
	 * {@linkplain MediaType#includes(MediaType) include} the given media type.
	 */
	@Override
	public boolean canWrite(Class<?> clazz, MediaType mediaType) {
		return supports(clazz) && canWrite(mediaType);
		}

	/**
	 * Returns {@code true} if the given media type includes any of the
	 * {@linkplain #setSupportedMediaTypes(List) supported media types}.
	 * @param mediaType the media type to write, can be {@code null} if not specified.
	 * Typically the value of an {@code Accept} header.
	 * @return {@code true} if the supported media types are compatible with the media type,
	 * or if the media type is {@code null}
	 */
	protected boolean canWrite(MediaType mediaType) {
		if (mediaType == null || MediaType.ALL.equals(mediaType)) {
			return true;
		}
		for (MediaType supportedMediaType : getSupportedMediaTypes()) {
			if (supportedMediaType.isCompatibleWith(mediaType)) {
				return true;
			}
		}
		return false;
	}

	/**
	 * This implementation simple delegates to {@link #readInternal(Class, HttpInputMessage)}.
	 * Future implementations might add some default behavior, however.
	 */
	@Override
	public final T read(Class<? extends T> clazz, HttpInputMessage inputMessage) throws IOException {
		return readInternal(clazz, inputMessage);
	}

	/**
	 * This implementation delegates to {@link #getDefaultContentType(Object)} if a content
	 * type was not provided, calls {@link #getContentLength}, and sets the corresponding headers
	 * on the output message. It then calls {@link #writeInternal}.
	 */
	@Override
	public final void write(final T t, MediaType contentType, HttpOutputMessage outputMessage)
			throws IOException, HttpMessageNotWritableException {

		final HttpHeaders headers = outputMessage.getHeaders();
		if (headers.getContentType() == null) {
			MediaType contentTypeToUse = contentType;
			if (contentType == null || contentType.isWildcardType() || contentType.isWildcardSubtype()) {
				contentTypeToUse = getDefaultContentType(t);
			}
			else if (MediaType.APPLICATION_OCTET_STREAM.equals(contentType)) {
				MediaType type = getDefaultContentType(t);
				contentTypeToUse = (type != null ? type : contentTypeToUse);
			}
			if (contentTypeToUse != null) {
				headers.setContentType(contentTypeToUse);
			}
		}
		if (headers.getContentLength() == -1) {
			Long contentLength = getContentLength(t, headers.getContentType());
			if (contentLength != null) {
				headers.setContentLength(contentLength);
			}
		}

		if (outputMessage instanceof StreamingHttpOutputMessage) {
			StreamingHttpOutputMessage streamingOutputMessage =
					(StreamingHttpOutputMessage) outputMessage;
			streamingOutputMessage.setBody(new StreamingHttpOutputMessage.Body() {
				@Override
				public void writeTo(final OutputStream outputStream) throws IOException {
					writeInternal(t, new HttpOutputMessage() {
						@Override
						public OutputStream getBody() throws IOException {
							return outputStream;
						}
						@Override
						public HttpHeaders getHeaders() {
							return headers;
						}
					});
				}
			});
		}
		else {
			writeInternal(t, outputMessage);
			outputMessage.getBody().flush();
		}
	}

	/**
	 * Returns the default content type for the given type. Called when {@link #write}
	 * is invoked without a specified content type parameter.
	 * <p>By default, this returns the first element of the
	 * {@link #setSupportedMediaTypes(List) supportedMediaTypes} property, if any.
	 * Can be overridden in subclasses.
	 * @param t the type to return the content type for
	 * @return the content type, or {@code null} if not known
	 */
	protected MediaType getDefaultContentType(T t) throws IOException {
		List<MediaType> mediaTypes = getSupportedMediaTypes();
		return (!mediaTypes.isEmpty() ? mediaTypes.get(0) : null);
	}

	/**
	 * Returns the content length for the given type.
	 * <p>By default, this returns {@code null}, meaning that the content length is unknown.
	 * Can be overridden in subclasses.
	 * @param t the type to return the content length for
	 * @return the content length, or {@code null} if not known
	 */
	protected Long getContentLength(T t, MediaType contentType) throws IOException {
		return null;
	}


	/**
	 * Indicates whether the given class is supported by this converter.
	 * @param clazz the class to test for support
	 * @return {@code true} if supported; {@code false} otherwise
	 */
	protected abstract boolean supports(Class<?> clazz);

	/**
	 * Abstract template method that reads the actual object. Invoked from {@link #read}.
	 * @param clazz the type of object to return
	 * @param inputMessage the HTTP input message to read from
	 * @return the converted object
	 * @throws IOException in case of I/O errors
	 * @throws HttpMessageNotReadableException in case of conversion errors
	 */
	protected abstract T readInternal(Class<? extends T> clazz, HttpInputMessage inputMessage)
			throws IOException, HttpMessageNotReadableException;

	/**
	 * Abstract template method that writes the actual body. Invoked from {@link #write}.
	 * @param t the object to write to the output message
	 * @param outputMessage the HTTP output message to write to
	 * @throws IOException in case of I/O errors
	 * @throws HttpMessageNotWritableException in case of conversion errors
	 */
	protected abstract void writeInternal(T t, HttpOutputMessage outputMessage)
			throws IOException, HttpMessageNotWritableException;

}


File: spring-web/src/main/java/org/springframework/http/converter/GenericHttpMessageConverter.java
/*
 * Copyright 2002-2015 the original author or authors.
 *
 * Licensed under the Apache License, Version 2.0 (the "License");
 * you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at
 *
 *     http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 */

package org.springframework.http.converter;

import java.io.IOException;
import java.lang.reflect.Type;

import org.springframework.http.HttpInputMessage;
import org.springframework.http.MediaType;

/**
 * A specialization of {@link HttpMessageConverter} that can convert an HTTP
 * request into a target object of a specified generic type.
 *
 * @author Arjen Poutsma
 * @author Rossen Stoyanchev
 * @since 3.2
 * @see org.springframework.core.ParameterizedTypeReference
 */
public interface GenericHttpMessageConverter<T> extends HttpMessageConverter<T> {

	/**
	 * Indicates whether the given type can be read by this converter.
	 * @param type the type to test for readability
	 * @param contextClass a context class for the target type, for example a class
	 * in which the target type appears in a method signature (can be {@code null})
	 * @param mediaType the media type to read, can be {@code null} if not specified.
	 * Typically the value of a {@code Content-Type} header.
	 * @return {@code true} if readable; {@code false} otherwise
	 */
	boolean canRead(Type type, Class<?> contextClass, MediaType mediaType);

	/**
	 * Read an object of the given type form the given input message, and returns it.
	 * @param type the type of object to return. This type must have previously
	 * been passed to the {@link #canRead canRead} method of this interface,
	 * which must have returned {@code true}.
	 * @param contextClass a context class for the target type, for example a class
	 * in which the target type appears in a method signature (can be {@code null})
	 * @param inputMessage the HTTP input message to read from
	 * @return the converted object
	 * @throws IOException in case of I/O errors
	 * @throws HttpMessageNotReadableException in case of conversion errors
	 */
	T read(Type type, Class<?> contextClass, HttpInputMessage inputMessage)
			throws IOException, HttpMessageNotReadableException;

}


File: spring-web/src/main/java/org/springframework/http/converter/json/AbstractJackson2HttpMessageConverter.java
/*
 * Copyright 2002-2015 the original author or authors.
 *
 * Licensed under the Apache License, Version 2.0 (the "License");
 * you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at
 *
 *      http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 */

package org.springframework.http.converter.json;

import java.io.IOException;
import java.lang.reflect.Type;
import java.nio.charset.Charset;
import java.util.concurrent.atomic.AtomicReference;

import com.fasterxml.jackson.core.JsonEncoding;
import com.fasterxml.jackson.core.JsonGenerator;
import com.fasterxml.jackson.core.JsonProcessingException;
import com.fasterxml.jackson.core.util.DefaultPrettyPrinter;
import com.fasterxml.jackson.databind.JavaType;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.fasterxml.jackson.databind.SerializationFeature;
import com.fasterxml.jackson.databind.ser.FilterProvider;

import org.springframework.http.HttpInputMessage;
import org.springframework.http.HttpOutputMessage;
import org.springframework.http.MediaType;
import org.springframework.http.converter.AbstractHttpMessageConverter;
import org.springframework.http.converter.GenericHttpMessageConverter;
import org.springframework.http.converter.HttpMessageConverter;
import org.springframework.http.converter.HttpMessageNotReadableException;
import org.springframework.http.converter.HttpMessageNotWritableException;
import org.springframework.util.Assert;
import org.springframework.util.ClassUtils;

/**
 * Abstract base class for Jackson based and content type independent
 * {@link HttpMessageConverter} implementations.
 *
 * <p>Compatible with Jackson 2.1 and higher.
 *
 * @author Arjen Poutsma
 * @author Keith Donald
 * @author Rossen Stoyanchev
 * @author Juergen Hoeller
 * @author Sebastien Deleuze
 * @since 4.1
 */
public abstract class AbstractJackson2HttpMessageConverter extends AbstractHttpMessageConverter<Object>
		implements GenericHttpMessageConverter<Object> {

	public static final Charset DEFAULT_CHARSET = Charset.forName("UTF-8");

	// Check for Jackson 2.3's overloaded canDeserialize/canSerialize variants with cause reference
	private static final boolean jackson23Available = ClassUtils.hasMethod(ObjectMapper.class,
			"canDeserialize", JavaType.class, AtomicReference.class);


	protected ObjectMapper objectMapper;

	private Boolean prettyPrint;


	protected AbstractJackson2HttpMessageConverter(ObjectMapper objectMapper) {
		this.objectMapper = objectMapper;
	}

	protected AbstractJackson2HttpMessageConverter(ObjectMapper objectMapper, MediaType supportedMediaType) {
		super(supportedMediaType);
		this.objectMapper = objectMapper;
	}

	protected AbstractJackson2HttpMessageConverter(ObjectMapper objectMapper, MediaType... supportedMediaTypes) {
		super(supportedMediaTypes);
		this.objectMapper = objectMapper;
	}


	/**
	 * Set the {@code ObjectMapper} for this view.
	 * If not set, a default {@link ObjectMapper#ObjectMapper() ObjectMapper} is used.
	 * <p>Setting a custom-configured {@code ObjectMapper} is one way to take further
	 * control of the JSON serialization process. For example, an extended
	 * {@link com.fasterxml.jackson.databind.ser.SerializerFactory}
	 * can be configured that provides custom serializers for specific types.
	 * The other option for refining the serialization process is to use Jackson's
	 * provided annotations on the types to be serialized, in which case a
	 * custom-configured ObjectMapper is unnecessary.
	 */
	public void setObjectMapper(ObjectMapper objectMapper) {
		Assert.notNull(objectMapper, "ObjectMapper must not be null");
		this.objectMapper = objectMapper;
		configurePrettyPrint();
	}

	/**
	 * Return the underlying {@code ObjectMapper} for this view.
	 */
	public ObjectMapper getObjectMapper() {
		return this.objectMapper;
	}

	/**
	 * Whether to use the {@link DefaultPrettyPrinter} when writing JSON.
	 * This is a shortcut for setting up an {@code ObjectMapper} as follows:
	 * <pre class="code">
	 * ObjectMapper mapper = new ObjectMapper();
	 * mapper.configure(SerializationFeature.INDENT_OUTPUT, true);
	 * converter.setObjectMapper(mapper);
	 * </pre>
	 */
	public void setPrettyPrint(boolean prettyPrint) {
		this.prettyPrint = prettyPrint;
		configurePrettyPrint();
	}

	private void configurePrettyPrint() {
		if (this.prettyPrint != null) {
			this.objectMapper.configure(SerializationFeature.INDENT_OUTPUT, this.prettyPrint);
		}
	}


	@Override
	public boolean canRead(Class<?> clazz, MediaType mediaType) {
		return canRead(clazz, null, mediaType);
	}

	@Override
	public boolean canRead(Type type, Class<?> contextClass, MediaType mediaType) {
		JavaType javaType = getJavaType(type, contextClass);
		if (!jackson23Available || !logger.isWarnEnabled()) {
			return (this.objectMapper.canDeserialize(javaType) && canRead(mediaType));
		}
		AtomicReference<Throwable> causeRef = new AtomicReference<Throwable>();
		if (this.objectMapper.canDeserialize(javaType, causeRef) && canRead(mediaType)) {
			return true;
		}
		Throwable cause = causeRef.get();
		if (cause != null) {
			String msg = "Failed to evaluate deserialization for type " + javaType;
			if (logger.isDebugEnabled()) {
				logger.warn(msg, cause);
			}
			else {
				logger.warn(msg + ": " + cause);
			}
		}
		return false;
	}

	@Override
	public boolean canWrite(Class<?> clazz, MediaType mediaType) {
		if (!jackson23Available || !logger.isWarnEnabled()) {
			return (this.objectMapper.canSerialize(clazz) && canWrite(mediaType));
		}
		AtomicReference<Throwable> causeRef = new AtomicReference<Throwable>();
		if (this.objectMapper.canSerialize(clazz, causeRef) && canWrite(mediaType)) {
			return true;
		}
		Throwable cause = causeRef.get();
		if (cause != null) {
			String msg = "Failed to evaluate serialization for type [" + clazz + "]";
			if (logger.isDebugEnabled()) {
				logger.warn(msg, cause);
			}
			else {
				logger.warn(msg + ": " + cause);
			}
		}
		return false;
	}

	@Override
	protected boolean supports(Class<?> clazz) {
		// should not be called, since we override canRead/Write instead
		throw new UnsupportedOperationException();
	}

	@Override
	protected Object readInternal(Class<?> clazz, HttpInputMessage inputMessage)
			throws IOException, HttpMessageNotReadableException {

		JavaType javaType = getJavaType(clazz, null);
		return readJavaType(javaType, inputMessage);
	}

	@Override
	public Object read(Type type, Class<?> contextClass, HttpInputMessage inputMessage)
			throws IOException, HttpMessageNotReadableException {

		JavaType javaType = getJavaType(type, contextClass);
		return readJavaType(javaType, inputMessage);
	}

	private Object readJavaType(JavaType javaType, HttpInputMessage inputMessage) {
		try {
			if (inputMessage instanceof MappingJacksonInputMessage) {
				Class<?> deserializationView = ((MappingJacksonInputMessage)inputMessage).getDeserializationView();
				if (deserializationView != null) {
					return this.objectMapper.readerWithView(deserializationView)
							.forType(javaType).readValue(inputMessage.getBody());
				}
			}
			return this.objectMapper.readValue(inputMessage.getBody(), javaType);
		}
		catch (IOException ex) {
			throw new HttpMessageNotReadableException("Could not read JSON: " + ex.getMessage(), ex);
		}
	}

	@Override
	protected void writeInternal(Object object, HttpOutputMessage outputMessage)
			throws IOException, HttpMessageNotWritableException {

		JsonEncoding encoding = getJsonEncoding(outputMessage.getHeaders().getContentType());
		JsonGenerator generator = this.objectMapper.getFactory().createGenerator(outputMessage.getBody(), encoding);
		try {
			writePrefix(generator, object);
			Class<?> serializationView = null;
			FilterProvider filters = null;
			Object value = object;
			if (value instanceof MappingJacksonValue) {
				MappingJacksonValue container = (MappingJacksonValue) object;
				value = container.getValue();
				serializationView = container.getSerializationView();
				filters = container.getFilters();
			}
			if (serializationView != null) {
				this.objectMapper.writerWithView(serializationView).writeValue(generator, value);
			}
			else if (filters != null) {
				this.objectMapper.writer(filters).writeValue(generator, value);
			}
			else {
				this.objectMapper.writeValue(generator, value);
			}
			writeSuffix(generator, object);
			generator.flush();

		}
		catch (JsonProcessingException ex) {
			throw new HttpMessageNotWritableException("Could not write content: " + ex.getMessage(), ex);
		}
	}

	/**
	 * Write a prefix before the main content.
	 * @param generator the generator to use for writing content.
	 * @param object the object to write to the output message.
	 */
	protected void writePrefix(JsonGenerator generator, Object object) throws IOException {

	}

	/**
	 * Write a suffix after the main content.
	 * @param generator the generator to use for writing content.
	 * @param object the object to write to the output message.
	 */
	protected void writeSuffix(JsonGenerator generator, Object object) throws IOException {

	}

	/**
	 * Return the Jackson {@link JavaType} for the specified type and context class.
	 * <p>The default implementation returns {@code typeFactory.constructType(type, contextClass)},
	 * but this can be overridden in subclasses, to allow for custom generic collection handling.
	 * For instance:
	 * <pre class="code">
	 * protected JavaType getJavaType(Type type) {
	 *   if (type instanceof Class && List.class.isAssignableFrom((Class)type)) {
	 *     return TypeFactory.collectionType(ArrayList.class, MyBean.class);
	 *   } else {
	 *     return super.getJavaType(type);
	 *   }
	 * }
	 * </pre>
	 * @param type the type to return the java type for
	 * @param contextClass a context class for the target type, for example a class
	 * in which the target type appears in a method signature, can be {@code null}
	 * signature, can be {@code null}
	 * @return the java type
	 */
	protected JavaType getJavaType(Type type, Class<?> contextClass) {
		return this.objectMapper.getTypeFactory().constructType(type, contextClass);
	}

	/**
	 * Determine the JSON encoding to use for the given content type.
	 * @param contentType the media type as requested by the caller
	 * @return the JSON encoding to use (never {@code null})
	 */
	protected JsonEncoding getJsonEncoding(MediaType contentType) {
		if (contentType != null && contentType.getCharSet() != null) {
			Charset charset = contentType.getCharSet();
			for (JsonEncoding encoding : JsonEncoding.values()) {
				if (charset.name().equals(encoding.getJavaName())) {
					return encoding;
				}
			}
		}
		return JsonEncoding.UTF8;
	}

	@Override
	protected MediaType getDefaultContentType(Object object) throws IOException {
		if (object instanceof MappingJacksonValue) {
			object = ((MappingJacksonValue) object).getValue();
		}
		return super.getDefaultContentType(object);
	}

	@Override
	protected Long getContentLength(Object object, MediaType contentType) throws IOException {
		if (object instanceof MappingJacksonValue) {
			object = ((MappingJacksonValue) object).getValue();
		}
		return super.getContentLength(object, contentType);
	}

}


File: spring-web/src/main/java/org/springframework/http/converter/json/GsonHttpMessageConverter.java
/*
 * Copyright 2002-2014 the original author or authors.
 *
 * Licensed under the Apache License, Version 2.0 (the "License");
 * you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at
 *
 *      http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 */

package org.springframework.http.converter.json;

import java.io.IOException;
import java.io.InputStreamReader;
import java.io.OutputStreamWriter;
import java.io.Reader;
import java.lang.reflect.Type;
import java.nio.charset.Charset;

import com.google.gson.Gson;
import com.google.gson.JsonIOException;
import com.google.gson.JsonParseException;
import com.google.gson.reflect.TypeToken;

import org.springframework.http.HttpHeaders;
import org.springframework.http.HttpInputMessage;
import org.springframework.http.HttpOutputMessage;
import org.springframework.http.MediaType;
import org.springframework.http.converter.AbstractHttpMessageConverter;
import org.springframework.http.converter.GenericHttpMessageConverter;
import org.springframework.http.converter.HttpMessageNotReadableException;
import org.springframework.http.converter.HttpMessageNotWritableException;
import org.springframework.util.Assert;

/**
 * Implementation of {@link org.springframework.http.converter.HttpMessageConverter}
 * that can read and write JSON using the
 * <a href="https://code.google.com/p/google-gson/">Google Gson</a> library's
 * {@link Gson} class.
 *
 * <p>This converter can be used to bind to typed beans or untyped {@code HashMap}s.
 * By default, it supports {@code application/json} and {@code application/*+json}.
 *
 * <p>Tested against Gson 2.3; compatible with Gson 2.0 and higher.
 *
 * @author Roy Clarkson
 * @since 4.1
 * @see #setGson
 * @see #setSupportedMediaTypes
 */
public class GsonHttpMessageConverter extends AbstractHttpMessageConverter<Object>
		implements GenericHttpMessageConverter<Object> {

	public static final Charset DEFAULT_CHARSET = Charset.forName("UTF-8");


	private Gson gson = new Gson();

	private String jsonPrefix;


	/**
	 * Construct a new {@code GsonHttpMessageConverter}.
	 */
	public GsonHttpMessageConverter() {
		super(new MediaType("application", "json", DEFAULT_CHARSET),
				new MediaType("application", "*+json", DEFAULT_CHARSET));
	}


	/**
	 * Set the {@code Gson} instance to use.
	 * If not set, a default {@link Gson#Gson() Gson} instance is used.
	 * <p>Setting a custom-configured {@code Gson} is one way to take further
	 * control of the JSON serialization process.
	 */
	public void setGson(Gson gson) {
		Assert.notNull(gson, "'gson' is required");
		this.gson = gson;
	}

	/**
	 * Return the configured {@code Gson} instance for this converter.
	 */
	public Gson getGson() {
		return this.gson;
	}

	/**
	 * Specify a custom prefix to use for JSON output. Default is none.
	 * @see #setPrefixJson
	 */
	public void setJsonPrefix(String jsonPrefix) {
		this.jsonPrefix = jsonPrefix;
	}

	/**
	 * Indicate whether the JSON output by this view should be prefixed with ")]}', ".
	 * Default is {@code false}.
	 * <p>Prefixing the JSON string in this manner is used to help prevent JSON
	 * Hijacking. The prefix renders the string syntactically invalid as a script
	 * so that it cannot be hijacked.
	 * This prefix should be stripped before parsing the string as JSON.
	 * @see #setJsonPrefix
	 */
	public void setPrefixJson(boolean prefixJson) {
		this.jsonPrefix = (prefixJson ? ")]}', " : null);
	}


	@Override
	public boolean canRead(Class<?> clazz, MediaType mediaType) {
		return canRead(mediaType);
	}

	@Override
	public boolean canRead(Type type, Class<?> contextClass, MediaType mediaType) {
		return canRead(mediaType);
	}

	@Override
	public boolean canWrite(Class<?> clazz, MediaType mediaType) {
		return canWrite(mediaType);
	}

	@Override
	protected boolean supports(Class<?> clazz) {
		// should not be called, since we override canRead/Write instead
		throw new UnsupportedOperationException();
	}

	@Override
	protected Object readInternal(Class<?> clazz, HttpInputMessage inputMessage)
			throws IOException, HttpMessageNotReadableException {

		TypeToken<?> token = getTypeToken(clazz);
		return readTypeToken(token, inputMessage);
	}

	@Override
	public Object read(Type type, Class<?> contextClass, HttpInputMessage inputMessage)
			throws IOException, HttpMessageNotReadableException {

		TypeToken<?> token = getTypeToken(type);
		return readTypeToken(token, inputMessage);
	}

	/**
	 * Return the Gson {@link TypeToken} for the specified type.
	 * <p>The default implementation returns {@code TypeToken.get(type)}, but
	 * this can be overridden in subclasses to allow for custom generic
	 * collection handling. For instance:
	 * <pre class="code">
	 * protected TypeToken<?> getTypeToken(Type type) {
	 *   if (type instanceof Class && List.class.isAssignableFrom((Class<?>) type)) {
	 *     return new TypeToken<ArrayList<MyBean>>() {};
	 *   }
	 *   else {
	 *     return super.getTypeToken(type);
	 *   }
	 * }
	 * </pre>
	 * @param type the type for which to return the TypeToken
	 * @return the type token
	 */
	protected TypeToken<?> getTypeToken(Type type) {
		return TypeToken.get(type);
	}

	private Object readTypeToken(TypeToken<?> token, HttpInputMessage inputMessage) throws IOException {
		Reader json = new InputStreamReader(inputMessage.getBody(), getCharset(inputMessage.getHeaders()));
		try {
			return this.gson.fromJson(json, token.getType());
		}
		catch (JsonParseException ex) {
			throw new HttpMessageNotReadableException("Could not read JSON: " + ex.getMessage(), ex);
		}
	}

	private Charset getCharset(HttpHeaders headers) {
		if (headers == null || headers.getContentType() == null || headers.getContentType().getCharSet() == null) {
			return DEFAULT_CHARSET;
		}
		return headers.getContentType().getCharSet();
	}

	@Override
	protected void writeInternal(Object o, HttpOutputMessage outputMessage)
			throws IOException, HttpMessageNotWritableException {

		Charset charset = getCharset(outputMessage.getHeaders());
		OutputStreamWriter writer = new OutputStreamWriter(outputMessage.getBody(), charset);
		try {
			if (this.jsonPrefix != null) {
				writer.append(this.jsonPrefix);
			}
			this.gson.toJson(o, writer);
			writer.close();
		}
		catch (JsonIOException ex) {
			throw new HttpMessageNotWritableException("Could not write JSON: " + ex.getMessage(), ex);
		}
	}

}


File: spring-web/src/main/java/org/springframework/http/converter/xml/Jaxb2CollectionHttpMessageConverter.java
/*
 * Copyright 2002-2014 the original author or authors.
 *
 * Licensed under the Apache License, Version 2.0 (the "License");
 * you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at
 *
 *     http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 */

package org.springframework.http.converter.xml;

import java.io.ByteArrayInputStream;
import java.io.IOException;
import java.lang.reflect.ParameterizedType;
import java.lang.reflect.Type;
import java.util.ArrayList;
import java.util.Collection;
import java.util.LinkedHashSet;
import java.util.List;
import java.util.SortedSet;
import java.util.TreeSet;
import javax.xml.bind.JAXBException;
import javax.xml.bind.UnmarshalException;
import javax.xml.bind.Unmarshaller;
import javax.xml.bind.annotation.XmlRootElement;
import javax.xml.bind.annotation.XmlType;
import javax.xml.stream.XMLInputFactory;
import javax.xml.stream.XMLResolver;
import javax.xml.stream.XMLStreamException;
import javax.xml.stream.XMLStreamReader;
import javax.xml.transform.Result;
import javax.xml.transform.Source;

import org.springframework.http.HttpHeaders;
import org.springframework.http.HttpInputMessage;
import org.springframework.http.MediaType;
import org.springframework.http.converter.GenericHttpMessageConverter;
import org.springframework.http.converter.HttpMessageConversionException;
import org.springframework.http.converter.HttpMessageNotReadableException;

/**
 * An {@code HttpMessageConverter} that can read XML collections using JAXB2.
 *
 * <p>This converter can read {@linkplain Collection collections} that contain classes
 * annotated with {@link XmlRootElement} and {@link XmlType}. Note that this converter
 * does not support writing.
 *
 * @author Arjen Poutsma
 * @author Rossen Stoyanchev
 * @since 3.2
 */
@SuppressWarnings("rawtypes")
public class Jaxb2CollectionHttpMessageConverter<T extends Collection>
		extends AbstractJaxb2HttpMessageConverter<T> implements GenericHttpMessageConverter<T> {

	private final XMLInputFactory inputFactory = createXmlInputFactory();


	/**
	 * Always returns {@code false} since Jaxb2CollectionHttpMessageConverter
	 * required generic type information in order to read a Collection.
	 */
	@Override
	public boolean canRead(Class<?> clazz, MediaType mediaType) {
		return false;
	}

	/**
	 * {@inheritDoc}
	 * <p>Jaxb2CollectionHttpMessageConverter can read a generic
	 * {@link Collection} where the generic type is a JAXB type annotated with
	 * {@link XmlRootElement} or {@link XmlType}.
	 */
	@Override
	public boolean canRead(Type type, Class<?> contextClass, MediaType mediaType) {
		if (!(type instanceof ParameterizedType)) {
			return false;
		}
		ParameterizedType parameterizedType = (ParameterizedType) type;
		if (!(parameterizedType.getRawType() instanceof Class)) {
			return false;
		}
		Class<?> rawType = (Class<?>) parameterizedType.getRawType();
		if (!(Collection.class.isAssignableFrom(rawType))) {
			return false;
		}
		if (parameterizedType.getActualTypeArguments().length != 1) {
			return false;
		}
		Type typeArgument = parameterizedType.getActualTypeArguments()[0];
		if (!(typeArgument instanceof Class)) {
			return false;
		}
		Class<?> typeArgumentClass = (Class<?>) typeArgument;
		return (typeArgumentClass.isAnnotationPresent(XmlRootElement.class) ||
				typeArgumentClass.isAnnotationPresent(XmlType.class)) && canRead(mediaType);
	}

	/**
	 * Always returns {@code false} since Jaxb2CollectionHttpMessageConverter
	 * does not convert collections to XML.
	 */
	@Override
	public boolean canWrite(Class<?> clazz, MediaType mediaType) {
		return false;
	}

	@Override
	protected boolean supports(Class<?> clazz) {
		// should not be called, since we override canRead/Write
		throw new UnsupportedOperationException();
	}

	@Override
	protected T readFromSource(Class<? extends T> clazz, HttpHeaders headers, Source source) throws IOException {
		// should not be called, since we return false for canRead(Class)
		throw new UnsupportedOperationException();
	}

	@Override
	@SuppressWarnings("unchecked")
	public T read(Type type, Class<?> contextClass, HttpInputMessage inputMessage)
			throws IOException, HttpMessageNotReadableException {

		ParameterizedType parameterizedType = (ParameterizedType) type;
		T result = createCollection((Class<?>) parameterizedType.getRawType());
		Class<?> elementClass = (Class<?>) parameterizedType.getActualTypeArguments()[0];

		try {
			Unmarshaller unmarshaller = createUnmarshaller(elementClass);
			XMLStreamReader streamReader = this.inputFactory.createXMLStreamReader(inputMessage.getBody());
			int event = moveToFirstChildOfRootElement(streamReader);

			while (event != XMLStreamReader.END_DOCUMENT) {
				if (elementClass.isAnnotationPresent(XmlRootElement.class)) {
					result.add(unmarshaller.unmarshal(streamReader));
				}
				else if (elementClass.isAnnotationPresent(XmlType.class)) {
					result.add(unmarshaller.unmarshal(streamReader, elementClass).getValue());
				}
				else {
					// should not happen, since we check in canRead(Type)
					throw new HttpMessageConversionException("Could not unmarshal to [" + elementClass + "]");
				}
				event = moveToNextElement(streamReader);
			}
			return result;
		}
		catch (UnmarshalException ex) {
			throw new HttpMessageNotReadableException("Could not unmarshal to [" + elementClass + "]: " + ex.getMessage(), ex);
		}
		catch (JAXBException ex) {
			throw new HttpMessageConversionException("Could not instantiate JAXBContext: " + ex.getMessage(), ex);
		}
		catch (XMLStreamException ex) {
			throw new HttpMessageConversionException(ex.getMessage(), ex);
		}
	}

	/**
	 * Create a Collection of the given type, with the given initial capacity
	 * (if supported by the Collection type).
	 * @param collectionClass the type of Collection to instantiate
	 * @return the created Collection instance
	 */
	@SuppressWarnings("unchecked")
	protected T createCollection(Class<?> collectionClass) {
		if (!collectionClass.isInterface()) {
			try {
				return (T) collectionClass.newInstance();
			}
			catch (Exception ex) {
				throw new IllegalArgumentException(
						"Could not instantiate collection class [" +
								collectionClass.getName() + "]: " + ex.getMessage());
			}
		}
		else if (List.class == collectionClass) {
			return (T) new ArrayList();
		}
		else if (SortedSet.class == collectionClass) {
			return (T) new TreeSet();
		}
		else {
			return (T) new LinkedHashSet();
		}
	}

	private int moveToFirstChildOfRootElement(XMLStreamReader streamReader) throws XMLStreamException {
		// root
		int event = streamReader.next();
		while (event != XMLStreamReader.START_ELEMENT) {
			event = streamReader.next();
		}

		// first child
		event = streamReader.next();
		while ((event != XMLStreamReader.START_ELEMENT) && (event != XMLStreamReader.END_DOCUMENT)) {
			event = streamReader.next();
		}
		return event;
	}

	private int moveToNextElement(XMLStreamReader streamReader) throws XMLStreamException {
		int event = streamReader.getEventType();
		while (event != XMLStreamReader.START_ELEMENT && event != XMLStreamReader.END_DOCUMENT) {
			event = streamReader.next();
		}
		return event;
	}

	@Override
	protected void writeToResult(T t, HttpHeaders headers, Result result) throws IOException {
		throw new UnsupportedOperationException();
	}

	/**
	 * Create a {@code XMLInputFactory} that this converter will use to create {@link
	 * javax.xml.stream.XMLStreamReader} and {@link javax.xml.stream.XMLEventReader} objects.
	 * <p>Can be overridden in subclasses, adding further initialization of the factory.
	 * The resulting factory is cached, so this method will only be called once.
	 */
	protected XMLInputFactory createXmlInputFactory() {
		XMLInputFactory inputFactory = XMLInputFactory.newInstance();
		inputFactory.setProperty(XMLInputFactory.IS_SUPPORTING_EXTERNAL_ENTITIES, false);
		inputFactory.setXMLResolver(NO_OP_XML_RESOLVER);
		return inputFactory;
	}


	private static final XMLResolver NO_OP_XML_RESOLVER = new XMLResolver() {
		@Override
		public Object resolveEntity(String publicID, String systemID, String base, String ns) {
			return new ByteArrayInputStream(new byte[0]);
		}
	};

}


File: spring-web/src/test/java/org/springframework/http/converter/json/GsonHttpMessageConverterTests.java
/*
 * Copyright 2002-2014 the original author or authors.
 *
 * Licensed under the Apache License, Version 2.0 (the "License");
 * you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at
 *
 *      http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 */

package org.springframework.http.converter.json;

import java.io.IOException;
import java.lang.reflect.Type;
import java.nio.charset.Charset;
import java.util.ArrayList;
import java.util.HashMap;
import java.util.List;
import java.util.Map;

import com.google.gson.reflect.TypeToken;
import org.junit.Test;

import org.springframework.core.ParameterizedTypeReference;
import org.springframework.http.MediaType;
import org.springframework.http.MockHttpInputMessage;
import org.springframework.http.MockHttpOutputMessage;
import org.springframework.http.converter.HttpMessageNotReadableException;

import static org.junit.Assert.*;

/**
 * Gson 2.x converter tests.
 *
 * @author Roy Clarkson
 */
public class GsonHttpMessageConverterTests {

	private static final Charset UTF8 = Charset.forName("UTF-8");

	private GsonHttpMessageConverter converter = new GsonHttpMessageConverter();


	@Test
	public void canRead() {
		assertTrue(this.converter.canRead(MyBean.class, new MediaType("application", "json")));
		assertTrue(this.converter.canRead(Map.class, new MediaType("application", "json")));
	}

	@Test
	public void canWrite() {
		assertTrue(this.converter.canWrite(MyBean.class, new MediaType("application", "json")));
		assertTrue(this.converter.canWrite(Map.class, new MediaType("application", "json")));
	}

	@Test
	public void canReadAndWriteMicroformats() {
		assertTrue(this.converter.canRead(MyBean.class, new MediaType("application", "vnd.test-micro-type+json")));
		assertTrue(this.converter.canWrite(MyBean.class, new MediaType("application", "vnd.test-micro-type+json")));
	}

	@Test
	public void readTyped() throws IOException {
		String body = "{\"bytes\":[1,2],\"array\":[\"Foo\",\"Bar\"]," +
				"\"number\":42,\"string\":\"Foo\",\"bool\":true,\"fraction\":42.0}";
		MockHttpInputMessage inputMessage = new MockHttpInputMessage(body.getBytes("UTF-8"));
		inputMessage.getHeaders().setContentType(new MediaType("application", "json"));
		MyBean result = (MyBean) this.converter.read(MyBean.class, inputMessage);

		assertEquals("Foo", result.getString());
		assertEquals(42, result.getNumber());
		assertEquals(42F, result.getFraction(), 0F);
		assertArrayEquals(new String[]{"Foo", "Bar"}, result.getArray());
		assertTrue(result.isBool());
		assertArrayEquals(new byte[]{0x1, 0x2}, result.getBytes());
	}

	@Test
	@SuppressWarnings("unchecked")
	public void readUntyped() throws IOException {
		String body = "{\"bytes\":[1,2],\"array\":[\"Foo\",\"Bar\"]," +
				"\"number\":42,\"string\":\"Foo\",\"bool\":true,\"fraction\":42.0}";
		MockHttpInputMessage inputMessage = new MockHttpInputMessage(body.getBytes("UTF-8"));
		inputMessage.getHeaders().setContentType(new MediaType("application", "json"));
		HashMap<String, Object> result = (HashMap<String, Object>) this.converter.read(HashMap.class, inputMessage);
		assertEquals("Foo", result.get("string"));
		Number n = (Number) result.get("number");
		assertEquals(42, n.longValue());
		n = (Number) result.get("fraction");
		assertEquals(42D, n.doubleValue(), 0D);
		List<String> array = new ArrayList<String>();
		array.add("Foo");
		array.add("Bar");
		assertEquals(array, result.get("array"));
		assertEquals(Boolean.TRUE, result.get("bool"));
		byte[] bytes = new byte[2];
		List<Number> resultBytes = (ArrayList<Number>)result.get("bytes");
		for (int i = 0; i < 2; i++) {
			bytes[i] = resultBytes.get(i).byteValue();
		}
		assertArrayEquals(new byte[]{0x1, 0x2}, bytes);
	}

	@Test
	public void write() throws IOException {
		MockHttpOutputMessage outputMessage = new MockHttpOutputMessage();
		MyBean body = new MyBean();
		body.setString("Foo");
		body.setNumber(42);
		body.setFraction(42F);
		body.setArray(new String[]{"Foo", "Bar"});
		body.setBool(true);
		body.setBytes(new byte[]{0x1, 0x2});
		this.converter.write(body, null, outputMessage);
		Charset utf8 = Charset.forName("UTF-8");
		String result = outputMessage.getBodyAsString(utf8);
		assertTrue(result.contains("\"string\":\"Foo\""));
		assertTrue(result.contains("\"number\":42"));
		assertTrue(result.contains("fraction\":42.0"));
		assertTrue(result.contains("\"array\":[\"Foo\",\"Bar\"]"));
		assertTrue(result.contains("\"bool\":true"));
		assertTrue(result.contains("\"bytes\":[1,2]"));
		assertEquals("Invalid content-type", new MediaType("application", "json", utf8),
				outputMessage.getHeaders().getContentType());
	}

	@Test
	public void writeUTF16() throws IOException {
		Charset utf16 = Charset.forName("UTF-16BE");
		MediaType contentType = new MediaType("application", "json", utf16);
		MockHttpOutputMessage outputMessage = new MockHttpOutputMessage();
		String body = "H\u00e9llo W\u00f6rld";
		this.converter.write(body, contentType, outputMessage);
		assertEquals("Invalid result", "\"" + body + "\"", outputMessage.getBodyAsString(utf16));
		assertEquals("Invalid content-type", contentType, outputMessage.getHeaders().getContentType());
	}

	@Test(expected = HttpMessageNotReadableException.class)
	public void readInvalidJson() throws IOException {
		String body = "FooBar";
		MockHttpInputMessage inputMessage = new MockHttpInputMessage(body.getBytes("UTF-8"));
		inputMessage.getHeaders().setContentType(new MediaType("application", "json"));
		this.converter.read(MyBean.class, inputMessage);
	}

	@Test
	@SuppressWarnings("unchecked")
	public void readGenerics() throws IOException {
		GsonHttpMessageConverter converter = new GsonHttpMessageConverter() {
			@Override
			protected TypeToken<?> getTypeToken(Type type) {
				if (type instanceof Class && List.class.isAssignableFrom((Class<?>) type)) {
					return new TypeToken<ArrayList<MyBean>>() {
					};
				}
				else {
					return super.getTypeToken(type);
				}
			}
		};
		String body = "[{\"bytes\":[1,2],\"array\":[\"Foo\",\"Bar\"]," +
				"\"number\":42,\"string\":\"Foo\",\"bool\":true,\"fraction\":42.0}]";
		MockHttpInputMessage inputMessage = new MockHttpInputMessage(
				body.getBytes(UTF8));
		inputMessage.getHeaders().setContentType(new MediaType("application", "json"));

		List<MyBean> results = (List<MyBean>) converter.read(List.class, inputMessage);
		assertEquals(1, results.size());
		MyBean result = results.get(0);
		assertEquals("Foo", result.getString());
		assertEquals(42, result.getNumber());
		assertEquals(42F, result.getFraction(), 0F);
		assertArrayEquals(new String[] { "Foo", "Bar" }, result.getArray());
		assertTrue(result.isBool());
		assertArrayEquals(new byte[] { 0x1, 0x2 }, result.getBytes());
	}

	@Test
	@SuppressWarnings("unchecked")
	public void readParameterizedType() throws IOException {
		ParameterizedTypeReference<List<MyBean>> beansList = new ParameterizedTypeReference<List<MyBean>>() {
		};

		String body = "[{\"bytes\":[1,2],\"array\":[\"Foo\",\"Bar\"]," +
				"\"number\":42,\"string\":\"Foo\",\"bool\":true,\"fraction\":42.0}]";
		MockHttpInputMessage inputMessage = new MockHttpInputMessage(
				body.getBytes(UTF8));
		inputMessage.getHeaders().setContentType(new MediaType("application", "json"));

		GsonHttpMessageConverter converter = new GsonHttpMessageConverter();
		List<MyBean> results = (List<MyBean>) converter.read(beansList.getType(), null, inputMessage);
		assertEquals(1, results.size());
		MyBean result = results.get(0);
		assertEquals("Foo", result.getString());
		assertEquals(42, result.getNumber());
		assertEquals(42F, result.getFraction(), 0F);
		assertArrayEquals(new String[] { "Foo", "Bar" }, result.getArray());
		assertTrue(result.isBool());
		assertArrayEquals(new byte[] { 0x1, 0x2 }, result.getBytes());
	}

	@Test
	public void prefixJson() throws Exception {
		MockHttpOutputMessage outputMessage = new MockHttpOutputMessage();
		this.converter.setPrefixJson(true);
		this.converter.writeInternal("foo", outputMessage);
		assertEquals(")]}', \"foo\"", outputMessage.getBodyAsString(UTF8));
	}

	@Test
	public void prefixJsonCustom() throws Exception {
		MockHttpOutputMessage outputMessage = new MockHttpOutputMessage();
		this.converter.setJsonPrefix(")))");
		this.converter.writeInternal("foo", outputMessage);
		assertEquals(")))\"foo\"", outputMessage.getBodyAsString(UTF8));
	}


	public static class MyBean {

		private String string;

		private int number;

		private float fraction;

		private String[] array;

		private boolean bool;

		private byte[] bytes;

		public byte[] getBytes() {
			return bytes;
		}

		public void setBytes(byte[] bytes) {
			this.bytes = bytes;
		}

		public boolean isBool() {
			return bool;
		}

		public void setBool(boolean bool) {
			this.bool = bool;
		}

		public String getString() {
			return string;
		}

		public void setString(String string) {
			this.string = string;
		}

		public int getNumber() {
			return number;
		}

		public void setNumber(int number) {
			this.number = number;
		}

		public float getFraction() {
			return fraction;
		}

		public void setFraction(float fraction) {
			this.fraction = fraction;
		}

		public String[] getArray() {
			return array;
		}

		public void setArray(String[] array) {
			this.array = array;
		}
	}

}


File: spring-web/src/test/java/org/springframework/http/converter/json/MappingJackson2HttpMessageConverterTests.java
/*
 * Copyright 2002-2015 the original author or authors.
 *
 * Licensed under the Apache License, Version 2.0 (the "License");
 * you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at
 *
 *      http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 */

package org.springframework.http.converter.json;

import java.io.IOException;
import java.lang.reflect.Type;
import java.nio.charset.Charset;
import java.util.ArrayList;
import java.util.HashMap;
import java.util.List;
import java.util.Map;

import com.fasterxml.jackson.annotation.JsonFilter;
import com.fasterxml.jackson.annotation.JsonView;
import com.fasterxml.jackson.databind.JavaType;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.fasterxml.jackson.databind.ser.FilterProvider;
import com.fasterxml.jackson.databind.ser.impl.SimpleBeanPropertyFilter;
import com.fasterxml.jackson.databind.ser.impl.SimpleFilterProvider;
import org.junit.Test;

import org.springframework.core.ParameterizedTypeReference;
import org.springframework.http.MediaType;
import org.springframework.http.MockHttpInputMessage;
import org.springframework.http.MockHttpOutputMessage;
import org.springframework.http.converter.HttpMessageNotReadableException;

import static org.hamcrest.CoreMatchers.*;
import static org.junit.Assert.*;

/**
 * Jackson 2.x converter tests.
 *
 * @author Rossen Stoyanchev
 * @author Sebastien Deleuze
 */
public class MappingJackson2HttpMessageConverterTests {

	protected static final String NEWLINE_SYSTEM_PROPERTY = System.getProperty("line.separator");

	private final MappingJackson2HttpMessageConverter converter = new MappingJackson2HttpMessageConverter();


	@Test
	public void canRead() {
		assertTrue(converter.canRead(MyBean.class, new MediaType("application", "json")));
		assertTrue(converter.canRead(Map.class, new MediaType("application", "json")));
	}

	@Test
	public void canWrite() {
		assertTrue(converter.canWrite(MyBean.class, new MediaType("application", "json")));
		assertTrue(converter.canWrite(Map.class, new MediaType("application", "json")));
	}

	// SPR-7905

	@Test
	public void canReadAndWriteMicroformats() {
		assertTrue(converter.canRead(MyBean.class, new MediaType("application", "vnd.test-micro-type+json")));
		assertTrue(converter.canWrite(MyBean.class, new MediaType("application", "vnd.test-micro-type+json")));
	}

	@Test
	public void readTyped() throws IOException {
		String body =
				"{\"bytes\":\"AQI=\",\"array\":[\"Foo\",\"Bar\"],\"number\":42,\"string\":\"Foo\",\"bool\":true,\"fraction\":42.0}";
		MockHttpInputMessage inputMessage = new MockHttpInputMessage(body.getBytes("UTF-8"));
		inputMessage.getHeaders().setContentType(new MediaType("application", "json"));
		MyBean result = (MyBean) converter.read(MyBean.class, inputMessage);
		assertEquals("Foo", result.getString());
		assertEquals(42, result.getNumber());
		assertEquals(42F, result.getFraction(), 0F);
		assertArrayEquals(new String[]{"Foo", "Bar"}, result.getArray());
		assertTrue(result.isBool());
		assertArrayEquals(new byte[]{0x1, 0x2}, result.getBytes());
	}

	@Test
	@SuppressWarnings("unchecked")
	public void readUntyped() throws IOException {
		String body =
				"{\"bytes\":\"AQI=\",\"array\":[\"Foo\",\"Bar\"],\"number\":42,\"string\":\"Foo\",\"bool\":true,\"fraction\":42.0}";
		MockHttpInputMessage inputMessage = new MockHttpInputMessage(body.getBytes("UTF-8"));
		inputMessage.getHeaders().setContentType(new MediaType("application", "json"));
		HashMap<String, Object> result = (HashMap<String, Object>) converter.read(HashMap.class, inputMessage);
		assertEquals("Foo", result.get("string"));
		assertEquals(42, result.get("number"));
		assertEquals(42D, (Double) result.get("fraction"), 0D);
		List<String> array = new ArrayList<String>();
		array.add("Foo");
		array.add("Bar");
		assertEquals(array, result.get("array"));
		assertEquals(Boolean.TRUE, result.get("bool"));
		assertEquals("AQI=", result.get("bytes"));
	}

	@Test
	public void write() throws IOException {
		MockHttpOutputMessage outputMessage = new MockHttpOutputMessage();
		MyBean body = new MyBean();
		body.setString("Foo");
		body.setNumber(42);
		body.setFraction(42F);
		body.setArray(new String[]{"Foo", "Bar"});
		body.setBool(true);
		body.setBytes(new byte[]{0x1, 0x2});
		converter.write(body, null, outputMessage);
		Charset utf8 = Charset.forName("UTF-8");
		String result = outputMessage.getBodyAsString(utf8);
		assertTrue(result.contains("\"string\":\"Foo\""));
		assertTrue(result.contains("\"number\":42"));
		assertTrue(result.contains("fraction\":42.0"));
		assertTrue(result.contains("\"array\":[\"Foo\",\"Bar\"]"));
		assertTrue(result.contains("\"bool\":true"));
		assertTrue(result.contains("\"bytes\":\"AQI=\""));
		assertEquals("Invalid content-type", new MediaType("application", "json", utf8),
				outputMessage.getHeaders().getContentType());
	}

	@Test
	public void writeUTF16() throws IOException {
		Charset utf16 = Charset.forName("UTF-16BE");
		MediaType contentType = new MediaType("application", "json", utf16);
		MockHttpOutputMessage outputMessage = new MockHttpOutputMessage();
		String body = "H\u00e9llo W\u00f6rld";
		converter.write(body, contentType, outputMessage);
		assertEquals("Invalid result", "\"" + body + "\"", outputMessage.getBodyAsString(utf16));
		assertEquals("Invalid content-type", contentType, outputMessage.getHeaders().getContentType());
	}

	@Test(expected = HttpMessageNotReadableException.class)
	public void readInvalidJson() throws IOException {
		String body = "FooBar";
		MockHttpInputMessage inputMessage = new MockHttpInputMessage(body.getBytes("UTF-8"));
		inputMessage.getHeaders().setContentType(new MediaType("application", "json"));
		converter.read(MyBean.class, inputMessage);
	}

	@Test
	public void readValidJsonWithUnknownProperty() throws IOException {
		String body = "{\"string\":\"string\",\"unknownProperty\":\"value\"}";
		MockHttpInputMessage inputMessage = new MockHttpInputMessage(body.getBytes("UTF-8"));
		inputMessage.getHeaders().setContentType(new MediaType("application", "json"));
		converter.read(MyBean.class, inputMessage);
		// Assert no HttpMessageNotReadableException is thrown
	}

	@Test
	@SuppressWarnings("unchecked")
	public void readGenerics() throws IOException {
		MappingJackson2HttpMessageConverter converter = new MappingJackson2HttpMessageConverter() {

			@Override
			protected JavaType getJavaType(Type type, Class<?> contextClass) {
				if (type instanceof Class && List.class.isAssignableFrom((Class<?>)type)) {
					return new ObjectMapper().getTypeFactory().constructCollectionType(ArrayList.class, MyBean.class);
				}
				else {
					return super.getJavaType(type, contextClass);
				}
			}
		};
		String body =
				"[{\"bytes\":\"AQI=\",\"array\":[\"Foo\",\"Bar\"],\"number\":42,\"string\":\"Foo\",\"bool\":true,\"fraction\":42.0}]";
		MockHttpInputMessage inputMessage = new MockHttpInputMessage(body.getBytes("UTF-8"));
		inputMessage.getHeaders().setContentType(new MediaType("application", "json"));

		List<MyBean> results = (List<MyBean>) converter.read(List.class, inputMessage);
		assertEquals(1, results.size());
		MyBean result = results.get(0);
		assertEquals("Foo", result.getString());
		assertEquals(42, result.getNumber());
		assertEquals(42F, result.getFraction(), 0F);
		assertArrayEquals(new String[]{"Foo", "Bar"}, result.getArray());
		assertTrue(result.isBool());
		assertArrayEquals(new byte[]{0x1, 0x2}, result.getBytes());
	}

	@Test
	@SuppressWarnings("unchecked")
	public void readParameterizedType() throws IOException {
		ParameterizedTypeReference<List<MyBean>> beansList = new ParameterizedTypeReference<List<MyBean>>() {};

		String body =
				"[{\"bytes\":\"AQI=\",\"array\":[\"Foo\",\"Bar\"],\"number\":42,\"string\":\"Foo\",\"bool\":true,\"fraction\":42.0}]";
		MockHttpInputMessage inputMessage = new MockHttpInputMessage(body.getBytes("UTF-8"));
		inputMessage.getHeaders().setContentType(new MediaType("application", "json"));

		MappingJackson2HttpMessageConverter converter = new MappingJackson2HttpMessageConverter();
		List<MyBean> results = (List<MyBean>) converter.read(beansList.getType(), null, inputMessage);
		assertEquals(1, results.size());
		MyBean result = results.get(0);
		assertEquals("Foo", result.getString());
		assertEquals(42, result.getNumber());
		assertEquals(42F, result.getFraction(), 0F);
		assertArrayEquals(new String[]{"Foo", "Bar"}, result.getArray());
		assertTrue(result.isBool());
		assertArrayEquals(new byte[]{0x1, 0x2}, result.getBytes());
	}


	@Test
	public void prettyPrint() throws Exception {
		MockHttpOutputMessage outputMessage = new MockHttpOutputMessage();
		PrettyPrintBean bean = new PrettyPrintBean();
		bean.setName("Jason");

		this.converter.setPrettyPrint(true);
		this.converter.writeInternal(bean, outputMessage);
		String result = outputMessage.getBodyAsString(Charset.forName("UTF-8"));

		assertEquals("{" + NEWLINE_SYSTEM_PROPERTY + "  \"name\" : \"Jason\"" + NEWLINE_SYSTEM_PROPERTY + "}", result);
	}

	@Test
	public void prefixJson() throws Exception {
		MockHttpOutputMessage outputMessage = new MockHttpOutputMessage();
		this.converter.setPrefixJson(true);
		this.converter.writeInternal("foo", outputMessage);

		assertEquals(")]}', \"foo\"", outputMessage.getBodyAsString(Charset.forName("UTF-8")));
	}

	@Test
	public void prefixJsonCustom() throws Exception {
		MockHttpOutputMessage outputMessage = new MockHttpOutputMessage();
		this.converter.setJsonPrefix(")))");
		this.converter.writeInternal("foo", outputMessage);

		assertEquals(")))\"foo\"", outputMessage.getBodyAsString(Charset.forName("UTF-8")));
	}

	@Test
	public void jsonView() throws Exception {
		MockHttpOutputMessage outputMessage = new MockHttpOutputMessage();
		JacksonViewBean bean = new JacksonViewBean();
		bean.setWithView1("with");
		bean.setWithView2("with");
		bean.setWithoutView("without");

		MappingJacksonValue jacksonValue = new MappingJacksonValue(bean);
		jacksonValue.setSerializationView(MyJacksonView1.class);
		this.converter.writeInternal(jacksonValue, outputMessage);

		String result = outputMessage.getBodyAsString(Charset.forName("UTF-8"));
		assertThat(result, containsString("\"withView1\":\"with\""));
		assertThat(result, not(containsString("\"withView2\":\"with\"")));
		assertThat(result, not(containsString("\"withoutView\":\"without\"")));
	}

	@Test
	public void filters() throws Exception {
		MockHttpOutputMessage outputMessage = new MockHttpOutputMessage();
		JacksonFilteredBean bean = new JacksonFilteredBean();
		bean.setProperty1("value");
		bean.setProperty2("value");

		MappingJacksonValue jacksonValue = new MappingJacksonValue(bean);
		FilterProvider filters = new SimpleFilterProvider().addFilter("myJacksonFilter",
				SimpleBeanPropertyFilter.serializeAllExcept("property2"));
		jacksonValue.setFilters(filters);
		this.converter.writeInternal(jacksonValue, outputMessage);

		String result = outputMessage.getBodyAsString(Charset.forName("UTF-8"));
		assertThat(result, containsString("\"property1\":\"value\""));
		assertThat(result, not(containsString("\"property2\":\"value\"")));
	}

	@Test
	public void jsonp() throws Exception {
		MappingJacksonValue jacksonValue = new MappingJacksonValue("foo");
		jacksonValue.setSerializationView(MyJacksonView1.class);
		jacksonValue.setJsonpFunction("callback");

		MockHttpOutputMessage outputMessage = new MockHttpOutputMessage();
		this.converter.writeInternal(jacksonValue, outputMessage);

		assertEquals("callback(\"foo\");", outputMessage.getBodyAsString(Charset.forName("UTF-8")));
	}

	@Test
	public void jsonpAndJsonView() throws Exception {
		MockHttpOutputMessage outputMessage = new MockHttpOutputMessage();
		JacksonViewBean bean = new JacksonViewBean();
		bean.setWithView1("with");
		bean.setWithView2("with");
		bean.setWithoutView("without");

		MappingJacksonValue jacksonValue = new MappingJacksonValue(bean);
		jacksonValue.setSerializationView(MyJacksonView1.class);
		jacksonValue.setJsonpFunction("callback");
		this.converter.writeInternal(jacksonValue, outputMessage);

		String result = outputMessage.getBodyAsString(Charset.forName("UTF-8"));
		assertThat(result, startsWith("callback("));
		assertThat(result, endsWith(");"));
		assertThat(result, containsString("\"withView1\":\"with\""));
		assertThat(result, not(containsString("\"withView2\":\"with\"")));
		assertThat(result, not(containsString("\"withoutView\":\"without\"")));
	}


	public static class MyBean {

		private String string;

		private int number;

		private float fraction;

		private String[] array;

		private boolean bool;

		private byte[] bytes;

		public byte[] getBytes() {
			return bytes;
		}

		public void setBytes(byte[] bytes) {
			this.bytes = bytes;
		}

		public boolean isBool() {
			return bool;
		}

		public void setBool(boolean bool) {
			this.bool = bool;
		}

		public String getString() {
			return string;
		}

		public void setString(String string) {
			this.string = string;
		}

		public int getNumber() {
			return number;
		}

		public void setNumber(int number) {
			this.number = number;
		}

		public float getFraction() {
			return fraction;
		}

		public void setFraction(float fraction) {
			this.fraction = fraction;
		}

		public String[] getArray() {
			return array;
		}

		public void setArray(String[] array) {
			this.array = array;
		}
	}


	public static class PrettyPrintBean {

		private String name;

		public String getName() {
			return name;
		}

		public void setName(String name) {
			this.name = name;
		}
	}

	private interface MyJacksonView1 {};
	private interface MyJacksonView2 {};

	private static class JacksonViewBean {

		@JsonView(MyJacksonView1.class)
		private String withView1;

		@JsonView(MyJacksonView2.class)
		private String withView2;

		private String withoutView;

		public String getWithView1() {
			return withView1;
		}

		public void setWithView1(String withView1) {
			this.withView1 = withView1;
		}

		public String getWithView2() {
			return withView2;
		}

		public void setWithView2(String withView2) {
			this.withView2 = withView2;
		}

		public String getWithoutView() {
			return withoutView;
		}

		public void setWithoutView(String withoutView) {
			this.withoutView = withoutView;
		}
	}

	@JsonFilter("myJacksonFilter")
	private static class JacksonFilteredBean {

		private String property1;
		private String property2;

		public String getProperty1() {
			return property1;
		}

		public void setProperty1(String property1) {
			this.property1 = property1;
		}

		public String getProperty2() {
			return property2;
		}

		public void setProperty2(String property2) {
			this.property2 = property2;
		}
	}

}


File: spring-web/src/test/java/org/springframework/http/converter/xml/MappingJackson2XmlHttpMessageConverterTests.java
/*
 * Copyright 2002-2014 the original author or authors.
 *
 * Licensed under the Apache License, Version 2.0 (the "License");
 * you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at
 *
 *      http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 */

package org.springframework.http.converter.xml;

import java.io.IOException;
import java.lang.reflect.InvocationTargetException;
import java.lang.reflect.Method;
import java.nio.charset.Charset;

import com.fasterxml.jackson.annotation.JsonView;
import com.fasterxml.jackson.dataformat.xml.XmlMapper;
import org.junit.Test;

import org.springframework.http.HttpOutputMessage;
import org.springframework.http.MediaType;
import org.springframework.http.MockHttpInputMessage;
import org.springframework.http.MockHttpOutputMessage;
import org.springframework.http.converter.HttpMessageNotReadableException;
import org.springframework.http.converter.json.AbstractJackson2HttpMessageConverter;
import org.springframework.http.converter.json.MappingJacksonValue;

import static org.hamcrest.CoreMatchers.*;
import static org.junit.Assert.*;

/**
 * Jackson 2.x XML converter tests.
 *
 * @author Sebastien Deleuze
 */
public class MappingJackson2XmlHttpMessageConverterTests {

	private final MappingJackson2XmlHttpMessageConverter converter = new MappingJackson2XmlHttpMessageConverter();


	@Test
	public void canRead() {
		assertTrue(converter.canRead(MyBean.class, new MediaType("application", "xml")));
		assertTrue(converter.canRead(MyBean.class, new MediaType("text", "xml")));
		assertTrue(converter.canRead(MyBean.class, new MediaType("application", "soap+xml")));
	}

	@Test
	public void canWrite() {
		assertTrue(converter.canWrite(MyBean.class, new MediaType("application", "xml")));
		assertTrue(converter.canWrite(MyBean.class, new MediaType("text", "xml")));
		assertTrue(converter.canWrite(MyBean.class, new MediaType("application", "soap+xml")));
	}

	@Test
	public void read() throws IOException {
		String body =
				"<MyBean><string>Foo</string><number>42</number><fraction>42.0</fraction><array><array>Foo</array><array>Bar</array></array><bool>true</bool><bytes>AQI=</bytes></MyBean>";
		MockHttpInputMessage inputMessage = new MockHttpInputMessage(body.getBytes("UTF-8"));
		inputMessage.getHeaders().setContentType(new MediaType("application", "xml"));
		MyBean result = (MyBean) converter.read(MyBean.class, inputMessage);
		assertEquals("Foo", result.getString());
		assertEquals(42, result.getNumber());
		assertEquals(42F, result.getFraction(), 0F);
		assertArrayEquals(new String[]{"Foo", "Bar"}, result.getArray());
		assertTrue(result.isBool());
		assertArrayEquals(new byte[]{0x1, 0x2}, result.getBytes());
	}

	@Test
	public void write() throws IOException {
		MockHttpOutputMessage outputMessage = new MockHttpOutputMessage();
		MyBean body = new MyBean();
		body.setString("Foo");
		body.setNumber(42);
		body.setFraction(42F);
		body.setArray(new String[]{"Foo", "Bar"});
		body.setBool(true);
		body.setBytes(new byte[]{0x1, 0x2});
		converter.write(body, null, outputMessage);
		Charset utf8 = Charset.forName("UTF-8");
		String result = outputMessage.getBodyAsString(utf8);
		assertTrue(result.contains("<string>Foo</string>"));
		assertTrue(result.contains("<number>42</number>"));
		assertTrue(result.contains("<fraction>42.0</fraction>"));
		assertTrue(result.contains("<array><array>Foo</array><array>Bar</array></array>"));
		assertTrue(result.contains("<bool>true</bool>"));
		assertTrue(result.contains("<bytes>AQI=</bytes>"));
		assertEquals("Invalid content-type", new MediaType("application", "xml", utf8),
				outputMessage.getHeaders().getContentType());
	}

	@Test(expected = HttpMessageNotReadableException.class)
	public void readInvalidXml() throws IOException {
		String body = "FooBar";
		MockHttpInputMessage inputMessage = new MockHttpInputMessage(body.getBytes("UTF-8"));
		inputMessage.getHeaders().setContentType(new MediaType("application", "xml"));
		converter.read(MyBean.class, inputMessage);
	}

	@Test
	public void readValidXmlWithUnknownProperty() throws IOException {
		String body = "<MyBean><string>string</string><unknownProperty>value</unknownProperty></MyBean>";
		MockHttpInputMessage inputMessage = new MockHttpInputMessage(body.getBytes("UTF-8"));
		inputMessage.getHeaders().setContentType(new MediaType("application", "xml"));
		converter.read(MyBean.class, inputMessage);
		// Assert no HttpMessageNotReadableException is thrown
	}

	@Test
	public void jsonView() throws Exception {
		MockHttpOutputMessage outputMessage = new MockHttpOutputMessage();
		JacksonViewBean bean = new JacksonViewBean();
		bean.setWithView1("with");
		bean.setWithView2("with");
		bean.setWithoutView("without");

		MappingJacksonValue jacksonValue = new MappingJacksonValue(bean);
		jacksonValue.setSerializationView(MyJacksonView1.class);
		this.writeInternal(jacksonValue, outputMessage);

		String result = outputMessage.getBodyAsString(Charset.forName("UTF-8"));
		assertThat(result, containsString("<withView1>with</withView1>"));
		assertThat(result, not(containsString("<withView2>with</withView2>")));
		assertThat(result, not(containsString("<withoutView>without</withoutView>")));
	}

	@Test
	public void customXmlMapper() {
		new MappingJackson2XmlHttpMessageConverter(new MyXmlMapper());
		// Assert no exception is thrown
	}

	private void writeInternal(Object object, HttpOutputMessage outputMessage)
			throws NoSuchMethodException, InvocationTargetException,
			IllegalAccessException {
		Method method = AbstractJackson2HttpMessageConverter.class.getDeclaredMethod(
				"writeInternal", Object.class, HttpOutputMessage.class);
		method.setAccessible(true);
		method.invoke(this.converter, object, outputMessage);
	}


	public static class MyBean {

		private String string;

		private int number;

		private float fraction;

		private String[] array;

		private boolean bool;

		private byte[] bytes;

		public byte[] getBytes() {
			return bytes;
		}

		public void setBytes(byte[] bytes) {
			this.bytes = bytes;
		}

		public boolean isBool() {
			return bool;
		}

		public void setBool(boolean bool) {
			this.bool = bool;
		}

		public String getString() {
			return string;
		}

		public void setString(String string) {
			this.string = string;
		}

		public int getNumber() {
			return number;
		}

		public void setNumber(int number) {
			this.number = number;
		}

		public float getFraction() {
			return fraction;
		}

		public void setFraction(float fraction) {
			this.fraction = fraction;
		}

		public String[] getArray() {
			return array;
		}

		public void setArray(String[] array) {
			this.array = array;
		}
	}

	private interface MyJacksonView1 {};
	private interface MyJacksonView2 {};

	@SuppressWarnings("unused")
	private static class JacksonViewBean {

		@JsonView(MyJacksonView1.class)
		private String withView1;

		@JsonView(MyJacksonView2.class)
		private String withView2;

		private String withoutView;

		public String getWithView1() {
			return withView1;
		}

		public void setWithView1(String withView1) {
			this.withView1 = withView1;
		}

		public String getWithView2() {
			return withView2;
		}

		public void setWithView2(String withView2) {
			this.withView2 = withView2;
		}

		public String getWithoutView() {
			return withoutView;
		}

		public void setWithoutView(String withoutView) {
			this.withoutView = withoutView;
		}
	}

	@SuppressWarnings("serial")
	private static class MyXmlMapper extends XmlMapper {
	}

}


File: spring-webmvc/src/main/java/org/springframework/web/servlet/mvc/method/annotation/AbstractMessageConverterMethodProcessor.java
/*
 * Copyright 2002-2015 the original author or authors.
 *
 * Licensed under the Apache License, Version 2.0 (the "License");
 * you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at
 *
 *      http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 */

package org.springframework.web.servlet.mvc.method.annotation;

import java.io.IOException;
import java.util.ArrayList;
import java.util.Collections;
import java.util.LinkedHashSet;
import java.util.List;
import java.util.Set;

import javax.servlet.http.HttpServletRequest;
import javax.servlet.http.HttpServletResponse;

import org.springframework.core.MethodParameter;
import org.springframework.http.HttpOutputMessage;
import org.springframework.http.MediaType;
import org.springframework.http.converter.HttpMessageConverter;
import org.springframework.http.server.ServletServerHttpRequest;
import org.springframework.http.server.ServletServerHttpResponse;
import org.springframework.util.Assert;
import org.springframework.util.CollectionUtils;
import org.springframework.web.HttpMediaTypeNotAcceptableException;
import org.springframework.web.accept.ContentNegotiationManager;
import org.springframework.web.context.request.NativeWebRequest;
import org.springframework.web.context.request.ServletWebRequest;
import org.springframework.web.method.support.HandlerMethodReturnValueHandler;
import org.springframework.web.servlet.HandlerMapping;

/**
 * Extends {@link AbstractMessageConverterMethodArgumentResolver} with the ability to handle
 * method return values by writing to the response with {@link HttpMessageConverter}s.
 *
 * @author Arjen Poutsma
 * @author Rossen Stoyanchev
 * @since 3.1
 */
public abstract class AbstractMessageConverterMethodProcessor extends AbstractMessageConverterMethodArgumentResolver
		implements HandlerMethodReturnValueHandler {

	private static final MediaType MEDIA_TYPE_APPLICATION = new MediaType("application");

	private final ContentNegotiationManager contentNegotiationManager;


	protected AbstractMessageConverterMethodProcessor(List<HttpMessageConverter<?>> converters) {
		this(converters, null);
	}

	protected AbstractMessageConverterMethodProcessor(List<HttpMessageConverter<?>> converters,
			ContentNegotiationManager contentNegotiationManager) {

		this(converters, contentNegotiationManager, null);
	}

	protected AbstractMessageConverterMethodProcessor(List<HttpMessageConverter<?>> converters,
			ContentNegotiationManager manager, List<Object> requestResponseBodyAdvice) {

		super(converters, requestResponseBodyAdvice);
		this.contentNegotiationManager = (manager != null ? manager : new ContentNegotiationManager());
	}


	/**
	 * Creates a new {@link HttpOutputMessage} from the given {@link NativeWebRequest}.
	 * @param webRequest the web request to create an output message from
	 * @return the output message
	 */
	protected ServletServerHttpResponse createOutputMessage(NativeWebRequest webRequest) {
		HttpServletResponse response = webRequest.getNativeResponse(HttpServletResponse.class);
		return new ServletServerHttpResponse(response);
	}

	/**
	 * Writes the given return value to the given web request. Delegates to
	 * {@link #writeWithMessageConverters(Object, MethodParameter, ServletServerHttpRequest, ServletServerHttpResponse)}
	 */
	protected <T> void writeWithMessageConverters(T returnValue, MethodParameter returnType, NativeWebRequest webRequest)
			throws IOException, HttpMediaTypeNotAcceptableException {

		ServletServerHttpRequest inputMessage = createInputMessage(webRequest);
		ServletServerHttpResponse outputMessage = createOutputMessage(webRequest);
		writeWithMessageConverters(returnValue, returnType, inputMessage, outputMessage);
	}

	/**
	 * Writes the given return type to the given output message.
	 * @param returnValue the value to write to the output message
	 * @param returnType the type of the value
	 * @param inputMessage the input messages. Used to inspect the {@code Accept} header.
	 * @param outputMessage the output message to write to
	 * @throws IOException thrown in case of I/O errors
	 * @throws HttpMediaTypeNotAcceptableException thrown when the conditions indicated by {@code Accept} header on
	 * the request cannot be met by the message converters
	 */
	@SuppressWarnings("unchecked")
	protected <T> void writeWithMessageConverters(T returnValue, MethodParameter returnType,
			ServletServerHttpRequest inputMessage, ServletServerHttpResponse outputMessage)
			throws IOException, HttpMediaTypeNotAcceptableException {

		Class<?> returnValueClass = getReturnValueType(returnValue, returnType);
		HttpServletRequest servletRequest = inputMessage.getServletRequest();
		List<MediaType> requestedMediaTypes = getAcceptableMediaTypes(servletRequest);
		List<MediaType> producibleMediaTypes = getProducibleMediaTypes(servletRequest, returnValueClass);

		Assert.isTrue(returnValue == null || !producibleMediaTypes.isEmpty(),
				"No converter found for return value of type: " + returnValueClass);

		Set<MediaType> compatibleMediaTypes = new LinkedHashSet<MediaType>();
		for (MediaType requestedType : requestedMediaTypes) {
			for (MediaType producibleType : producibleMediaTypes) {
				if (requestedType.isCompatibleWith(producibleType)) {
					compatibleMediaTypes.add(getMostSpecificMediaType(requestedType, producibleType));
				}
			}
		}
		if (compatibleMediaTypes.isEmpty()) {
			if (returnValue != null) {
				throw new HttpMediaTypeNotAcceptableException(producibleMediaTypes);
			}
			return;
		}

		List<MediaType> mediaTypes = new ArrayList<MediaType>(compatibleMediaTypes);
		MediaType.sortBySpecificityAndQuality(mediaTypes);

		MediaType selectedMediaType = null;
		for (MediaType mediaType : mediaTypes) {
			if (mediaType.isConcrete()) {
				selectedMediaType = mediaType;
				break;
			}
			else if (mediaType.equals(MediaType.ALL) || mediaType.equals(MEDIA_TYPE_APPLICATION)) {
				selectedMediaType = MediaType.APPLICATION_OCTET_STREAM;
				break;
			}
		}

		if (selectedMediaType != null) {
			selectedMediaType = selectedMediaType.removeQualityValue();
			for (HttpMessageConverter<?> messageConverter : this.messageConverters) {
				if (messageConverter.canWrite(returnValueClass, selectedMediaType)) {
					returnValue = (T) getAdvice().beforeBodyWrite(returnValue, returnType, selectedMediaType,
							(Class<? extends HttpMessageConverter<?>>) messageConverter.getClass(),
							inputMessage, outputMessage);
					if (returnValue != null) {
						((HttpMessageConverter<T>) messageConverter).write(returnValue, selectedMediaType, outputMessage);
						if (logger.isDebugEnabled()) {
							logger.debug("Written [" + returnValue + "] as \"" +
									selectedMediaType + "\" using [" + messageConverter + "]");
						}
					}
					return;
				}
			}
		}

		if (returnValue != null) {
			throw new HttpMediaTypeNotAcceptableException(this.allSupportedMediaTypes);
		}
	}

	/**
	 * Return the type of the value to be written to the response. Typically this
	 * is a simple check via getClass on the returnValue but if the returnValue is
	 * null, then the returnType needs to be examined possibly including generic
	 * type determination (e.g. {@code ResponseEntity<T>}).
	 */
	protected Class<?> getReturnValueType(Object returnValue, MethodParameter returnType) {
		return (returnValue != null ? returnValue.getClass() : returnType.getParameterType());
	}

	/**
	 * Returns the media types that can be produced:
	 * <ul>
	 * <li>The producible media types specified in the request mappings, or
	 * <li>Media types of configured converters that can write the specific return value, or
	 * <li>{@link MediaType#ALL}
	 * </ul>
	 */
	@SuppressWarnings("unchecked")
	protected List<MediaType> getProducibleMediaTypes(HttpServletRequest request, Class<?> returnValueClass) {
		Set<MediaType> mediaTypes = (Set<MediaType>) request.getAttribute(HandlerMapping.PRODUCIBLE_MEDIA_TYPES_ATTRIBUTE);
		if (!CollectionUtils.isEmpty(mediaTypes)) {
			return new ArrayList<MediaType>(mediaTypes);
		}
		else if (!this.allSupportedMediaTypes.isEmpty()) {
			List<MediaType> result = new ArrayList<MediaType>();
			for (HttpMessageConverter<?> converter : this.messageConverters) {
				if (converter.canWrite(returnValueClass, null)) {
					result.addAll(converter.getSupportedMediaTypes());
				}
			}
			return result;
		}
		else {
			return Collections.singletonList(MediaType.ALL);
		}
	}

	private List<MediaType> getAcceptableMediaTypes(HttpServletRequest request) throws HttpMediaTypeNotAcceptableException {
		List<MediaType> mediaTypes = this.contentNegotiationManager.resolveMediaTypes(new ServletWebRequest(request));
		return (mediaTypes.isEmpty() ? Collections.singletonList(MediaType.ALL) : mediaTypes);
	}

	/**
	 * Return the more specific of the acceptable and the producible media types
	 * with the q-value of the former.
	 */
	private MediaType getMostSpecificMediaType(MediaType acceptType, MediaType produceType) {
		MediaType produceTypeToUse = produceType.copyQualityValue(acceptType);
		return (MediaType.SPECIFICITY_COMPARATOR.compare(acceptType, produceTypeToUse) <= 0 ? acceptType : produceTypeToUse);
	}

}


File: spring-webmvc/src/test/java/org/springframework/web/servlet/mvc/method/annotation/HttpEntityMethodProcessorTests.java
/*
 * Copyright 2002-2015 the original author or authors.
 *
 * Licensed under the Apache License, Version 2.0 (the "License");
 * you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at
 *
 *      http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 */

package org.springframework.web.servlet.mvc.method.annotation;

import static org.junit.Assert.*;

import java.io.Serializable;
import java.lang.reflect.Method;
import java.util.ArrayList;
import java.util.Arrays;
import java.util.List;

import org.junit.Before;
import org.junit.Test;

import org.springframework.core.MethodParameter;
import org.springframework.http.HttpEntity;
import org.springframework.http.MediaType;
import org.springframework.http.converter.HttpMessageConverter;
import org.springframework.http.converter.json.MappingJackson2HttpMessageConverter;
import org.springframework.mock.web.test.MockHttpServletRequest;
import org.springframework.mock.web.test.MockHttpServletResponse;
import org.springframework.validation.beanvalidation.LocalValidatorFactoryBean;
import org.springframework.web.bind.WebDataBinder;
import org.springframework.web.bind.support.WebDataBinderFactory;
import org.springframework.web.context.request.NativeWebRequest;
import org.springframework.web.context.request.ServletWebRequest;
import org.springframework.web.method.HandlerMethod;
import org.springframework.web.method.support.ModelAndViewContainer;

/**
 * Test fixture with {@link HttpEntityMethodProcessor} delegating to
 * actual {@link HttpMessageConverter} instances.
 *
 * <p>Also see {@link HttpEntityMethodProcessorMockTests}.
 *
 * @author Rossen Stoyanchev
 */
public class HttpEntityMethodProcessorTests {

	private MethodParameter paramList;

	private MethodParameter paramSimpleBean;

	private ModelAndViewContainer mavContainer;

	private WebDataBinderFactory binderFactory;

	private MockHttpServletRequest servletRequest;

	private ServletWebRequest webRequest;


	@Before
	public void setUp() throws Exception {
		Method method = getClass().getMethod("handle", HttpEntity.class, HttpEntity.class);
		paramList = new MethodParameter(method, 0);
		paramSimpleBean = new MethodParameter(method, 1);

		mavContainer = new ModelAndViewContainer();
		binderFactory = new ValidatingBinderFactory();
		servletRequest = new MockHttpServletRequest();
		webRequest = new ServletWebRequest(servletRequest, new MockHttpServletResponse());
	}

	@Test
	public void resolveArgument() throws Exception {
		String content = "{\"name\" : \"Jad\"}";
		this.servletRequest.setContent(content.getBytes("UTF-8"));
		this.servletRequest.setContentType("application/json");

		List<HttpMessageConverter<?>> converters = new ArrayList<HttpMessageConverter<?>>();
		converters.add(new MappingJackson2HttpMessageConverter());
		HttpEntityMethodProcessor processor = new HttpEntityMethodProcessor(converters);

		@SuppressWarnings("unchecked")
		HttpEntity<SimpleBean> result = (HttpEntity<SimpleBean>) processor.resolveArgument(
				paramSimpleBean, mavContainer, webRequest, binderFactory);

		assertNotNull(result);
		assertEquals("Jad", result.getBody().getName());
	}

	// SPR-12861

	@Test
	public void resolveArgumentWithEmptyBody() throws Exception {
		this.servletRequest.setContent(new byte[0]);
		this.servletRequest.setContentType("application/json");

		List<HttpMessageConverter<?>> converters = Arrays.asList(new MappingJackson2HttpMessageConverter());
		HttpEntityMethodProcessor processor = new HttpEntityMethodProcessor(converters);

		HttpEntity<?> result = (HttpEntity<?>) processor.resolveArgument(this.paramSimpleBean,
				this.mavContainer, this.webRequest, this.binderFactory);

		assertNotNull(result);
		assertNull(result.getBody());
	}

	@Test
	public void resolveGenericArgument() throws Exception {
		String content = "[{\"name\" : \"Jad\"}, {\"name\" : \"Robert\"}]";
		this.servletRequest.setContent(content.getBytes("UTF-8"));
		this.servletRequest.setContentType("application/json");

		List<HttpMessageConverter<?>> converters = new ArrayList<HttpMessageConverter<?>>();
		converters.add(new MappingJackson2HttpMessageConverter());
		HttpEntityMethodProcessor processor = new HttpEntityMethodProcessor(converters);

		@SuppressWarnings("unchecked")
		HttpEntity<List<SimpleBean>> result = (HttpEntity<List<SimpleBean>>) processor.resolveArgument(
				paramList, mavContainer, webRequest, binderFactory);

		assertNotNull(result);
		assertEquals("Jad", result.getBody().get(0).getName());
		assertEquals("Robert", result.getBody().get(1).getName());
	}

	@Test
	public void resolveArgumentTypeVariable() throws Exception {
		Method method = MySimpleParameterizedController.class.getMethod("handleDto", HttpEntity.class);
		HandlerMethod handlerMethod = new HandlerMethod(new MySimpleParameterizedController(), method);
		MethodParameter methodParam = handlerMethod.getMethodParameters()[0];

		String content = "{\"name\" : \"Jad\"}";
		this.servletRequest.setContent(content.getBytes("UTF-8"));
		this.servletRequest.setContentType(MediaType.APPLICATION_JSON_VALUE);

		List<HttpMessageConverter<?>> converters = new ArrayList<HttpMessageConverter<?>>();
		converters.add(new MappingJackson2HttpMessageConverter());
		HttpEntityMethodProcessor processor = new HttpEntityMethodProcessor(converters);

		@SuppressWarnings("unchecked")
		HttpEntity<SimpleBean> result = (HttpEntity<SimpleBean>)
				processor.resolveArgument(methodParam, mavContainer, webRequest, binderFactory);

		assertNotNull(result);
		assertEquals("Jad", result.getBody().getName());
	}


	@SuppressWarnings("unused")
	public void handle(HttpEntity<List<SimpleBean>> arg1, HttpEntity<SimpleBean> arg2) {
	}

	@SuppressWarnings("unused")
	private static abstract class MyParameterizedController<DTO extends Identifiable> {

		public void handleDto(HttpEntity<DTO> dto) {
		}
	}

	@SuppressWarnings("unused")
	private static class MySimpleParameterizedController extends MyParameterizedController<SimpleBean> {
	}

	private interface Identifiable extends Serializable {

		public Long getId();

		public void setId(Long id);
	}


	@SuppressWarnings({ "serial" })
	private static class SimpleBean implements Identifiable {

		private Long id;

		private String name;

		@Override
		public Long getId() {
			return id;
		}

		@Override
		public void setId(Long id) {
			this.id = id;
		}

		public String getName() {
			return name;
		}

		@SuppressWarnings("unused")
		public void setName(String name) {
			this.name = name;
		}
	}


	private final class ValidatingBinderFactory implements WebDataBinderFactory {

		@Override
		public WebDataBinder createBinder(NativeWebRequest webRequest, Object target, String objectName) {
			LocalValidatorFactoryBean validator = new LocalValidatorFactoryBean();
			validator.afterPropertiesSet();
			WebDataBinder dataBinder = new WebDataBinder(target, objectName);
			dataBinder.setValidator(validator);
			return dataBinder;
		}
	}

}


File: spring-webmvc/src/test/java/org/springframework/web/servlet/mvc/method/annotation/RequestResponseBodyMethodProcessorTests.java
/*
 * Copyright 2002-2015 the original author or authors.
 *
 * Licensed under the Apache License, Version 2.0 (the "License");
 * you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at
 *
 *      http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 */

package org.springframework.web.servlet.mvc.method.annotation;

import static org.junit.Assert.*;

import java.io.ByteArrayOutputStream;
import java.io.OutputStream;
import java.io.Serializable;
import java.lang.reflect.Method;
import java.lang.reflect.Type;
import java.util.ArrayList;
import java.util.Collections;
import java.util.List;

import com.fasterxml.jackson.annotation.JsonView;
import org.junit.Before;
import org.junit.Test;

import org.springframework.aop.framework.ProxyFactory;
import org.springframework.aop.target.SingletonTargetSource;
import org.springframework.core.MethodParameter;
import org.springframework.core.io.ClassPathResource;
import org.springframework.core.io.Resource;
import org.springframework.http.HttpEntity;
import org.springframework.http.HttpInputMessage;
import org.springframework.http.HttpStatus;
import org.springframework.http.MediaType;
import org.springframework.http.ResponseEntity;
import org.springframework.http.converter.ByteArrayHttpMessageConverter;
import org.springframework.http.converter.HttpMessageConverter;
import org.springframework.http.converter.HttpMessageNotReadableException;
import org.springframework.http.converter.ResourceHttpMessageConverter;
import org.springframework.http.converter.StringHttpMessageConverter;
import org.springframework.http.converter.json.MappingJackson2HttpMessageConverter;
import org.springframework.http.converter.support.AllEncompassingFormHttpMessageConverter;
import org.springframework.http.converter.xml.MappingJackson2XmlHttpMessageConverter;
import org.springframework.mock.web.test.MockHttpServletRequest;
import org.springframework.mock.web.test.MockHttpServletResponse;
import org.springframework.util.MultiValueMap;
import org.springframework.validation.beanvalidation.LocalValidatorFactoryBean;
import org.springframework.web.bind.WebDataBinder;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.ResponseBody;
import org.springframework.web.bind.annotation.RestController;
import org.springframework.web.bind.support.WebDataBinderFactory;
import org.springframework.web.context.request.NativeWebRequest;
import org.springframework.web.context.request.ServletWebRequest;
import org.springframework.web.method.HandlerMethod;
import org.springframework.web.method.support.ModelAndViewContainer;
import org.springframework.web.servlet.ModelAndView;
import org.springframework.web.servlet.view.json.MappingJackson2JsonView;

/**
 * Test fixture for a {@link RequestResponseBodyMethodProcessor} with
 * actual delegation to {@link HttpMessageConverter} instances.
 *
 * <p>Also see {@link RequestResponseBodyMethodProcessorMockTests}.
 *
 * @author Rossen Stoyanchev
 * @author Sebastien Deleuze
 */
@SuppressWarnings("unused")
public class RequestResponseBodyMethodProcessorTests {

	private MethodParameter paramGenericList;
	private MethodParameter paramSimpleBean;
	private MethodParameter paramMultiValueMap;
	private MethodParameter paramString;
	private MethodParameter returnTypeString;

	private ModelAndViewContainer mavContainer;

	private NativeWebRequest webRequest;

	private MockHttpServletRequest servletRequest;

	private MockHttpServletResponse servletResponse;

	private ValidatingBinderFactory binderFactory;


	@Before
	public void setUp() throws Exception {

		Method method = getClass().getDeclaredMethod("handle", List.class,
				SimpleBean.class, MultiValueMap.class, String.class);

		paramGenericList = new MethodParameter(method, 0);
		paramSimpleBean = new MethodParameter(method, 1);
		paramMultiValueMap = new MethodParameter(method, 2);
		paramString = new MethodParameter(method, 3);
		returnTypeString = new MethodParameter(method, -1);

		mavContainer = new ModelAndViewContainer();

		servletRequest = new MockHttpServletRequest();
		servletResponse = new MockHttpServletResponse();
		webRequest = new ServletWebRequest(servletRequest, servletResponse);

		this.binderFactory = new ValidatingBinderFactory();
	}

	@Test
	public void resolveArgumentParameterizedType() throws Exception {
		String content = "[{\"name\" : \"Jad\"}, {\"name\" : \"Robert\"}]";
		this.servletRequest.setContent(content.getBytes("UTF-8"));
		this.servletRequest.setContentType(MediaType.APPLICATION_JSON_VALUE);

		List<HttpMessageConverter<?>> converters = new ArrayList<HttpMessageConverter<?>>();
		converters.add(new MappingJackson2HttpMessageConverter());
		RequestResponseBodyMethodProcessor processor = new RequestResponseBodyMethodProcessor(converters);

		@SuppressWarnings("unchecked")
		List<SimpleBean> result = (List<SimpleBean>) processor.resolveArgument(
				paramGenericList, mavContainer, webRequest, binderFactory);

		assertNotNull(result);
		assertEquals("Jad", result.get(0).getName());
		assertEquals("Robert", result.get(1).getName());
	}

	@Test
	public void resolveArgumentRawTypeFromParameterizedType() throws Exception {
		String content = "fruit=apple&vegetable=kale";
		this.servletRequest.setContent(content.getBytes("UTF-8"));
		this.servletRequest.setContentType(MediaType.APPLICATION_FORM_URLENCODED_VALUE);

		List<HttpMessageConverter<?>> converters = new ArrayList<HttpMessageConverter<?>>();
		converters.add(new AllEncompassingFormHttpMessageConverter());
		RequestResponseBodyMethodProcessor processor = new RequestResponseBodyMethodProcessor(converters);

		@SuppressWarnings("unchecked")
		MultiValueMap<String, String> result = (MultiValueMap<String, String>) processor.resolveArgument(
				paramMultiValueMap, mavContainer, webRequest, binderFactory);

		assertNotNull(result);
		assertEquals("apple", result.getFirst("fruit"));
		assertEquals("kale", result.getFirst("vegetable"));
	}

	@Test
	public void resolveArgumentClassJson() throws Exception {
		String content = "{\"name\" : \"Jad\"}";
		this.servletRequest.setContent(content.getBytes("UTF-8"));
		this.servletRequest.setContentType("application/json");

		List<HttpMessageConverter<?>> converters = new ArrayList<HttpMessageConverter<?>>();
		converters.add(new MappingJackson2HttpMessageConverter());
		RequestResponseBodyMethodProcessor processor = new RequestResponseBodyMethodProcessor(converters);

		SimpleBean result = (SimpleBean) processor.resolveArgument(
				paramSimpleBean, mavContainer, webRequest, binderFactory);

		assertNotNull(result);
		assertEquals("Jad", result.getName());
	}

	@Test
	public void resolveArgumentClassString() throws Exception {
		String content = "foobarbaz";
		this.servletRequest.setContent(content.getBytes("UTF-8"));
		this.servletRequest.setContentType("application/json");

		List<HttpMessageConverter<?>> converters = new ArrayList<HttpMessageConverter<?>>();
		converters.add(new StringHttpMessageConverter());
		RequestResponseBodyMethodProcessor processor = new RequestResponseBodyMethodProcessor(converters);

		String result = (String) processor.resolveArgument(
				paramString, mavContainer, webRequest, binderFactory);

		assertNotNull(result);
		assertEquals("foobarbaz", result);
	}

	@Test(expected = HttpMessageNotReadableException.class)  // SPR-9942
	public void resolveArgumentRequiredNoContent() throws Exception {
		this.servletRequest.setContent(new byte[0]);
		this.servletRequest.setContentType("text/plain");
		List<HttpMessageConverter<?>> converters = new ArrayList<HttpMessageConverter<?>>();
		converters.add(new StringHttpMessageConverter());
		RequestResponseBodyMethodProcessor processor = new RequestResponseBodyMethodProcessor(converters);
		processor.resolveArgument(paramString, mavContainer, webRequest, binderFactory);
	}

	@Test  // SPR-12778
	public void resolveArgumentRequiredNoContentDefaultValue() throws Exception {
		this.servletRequest.setContent(new byte[0]);
		this.servletRequest.setContentType("text/plain");
		List<HttpMessageConverter<?>> converters = Collections.singletonList(new StringHttpMessageConverter());
		List<Object> advice = Collections.singletonList(new EmptyRequestBodyAdvice());
		RequestResponseBodyMethodProcessor processor = new RequestResponseBodyMethodProcessor(converters, advice);
		String arg = (String) processor.resolveArgument(paramString, mavContainer, webRequest, binderFactory);
		assertNotNull(arg);
		assertEquals("default value for empty body", arg);
	}

	@Test  // SPR-9964
	public void resolveArgumentTypeVariable() throws Exception {
		Method method = MyParameterizedController.class.getMethod("handleDto", Identifiable.class);
		HandlerMethod handlerMethod = new HandlerMethod(new MySimpleParameterizedController(), method);
		MethodParameter methodParam = handlerMethod.getMethodParameters()[0];

		String content = "{\"name\" : \"Jad\"}";
		this.servletRequest.setContent(content.getBytes("UTF-8"));
		this.servletRequest.setContentType(MediaType.APPLICATION_JSON_VALUE);

		List<HttpMessageConverter<?>> converters = new ArrayList<HttpMessageConverter<?>>();
		converters.add(new MappingJackson2HttpMessageConverter());
		RequestResponseBodyMethodProcessor processor = new RequestResponseBodyMethodProcessor(converters);

		SimpleBean result = (SimpleBean) processor.resolveArgument(methodParam, mavContainer, webRequest, binderFactory);

		assertNotNull(result);
		assertEquals("Jad", result.getName());
	}

	@Test  // SPR-11225
	public void resolveArgumentTypeVariableWithNonGenericConverter() throws Exception {
		Method method = MyParameterizedController.class.getMethod("handleDto", Identifiable.class);
		HandlerMethod handlerMethod = new HandlerMethod(new MySimpleParameterizedController(), method);
		MethodParameter methodParam = handlerMethod.getMethodParameters()[0];

		String content = "{\"name\" : \"Jad\"}";
		this.servletRequest.setContent(content.getBytes("UTF-8"));
		this.servletRequest.setContentType(MediaType.APPLICATION_JSON_VALUE);

		List<HttpMessageConverter<?>> converters = new ArrayList<HttpMessageConverter<?>>();
		HttpMessageConverter target = new MappingJackson2HttpMessageConverter();
		HttpMessageConverter proxy = ProxyFactory.getProxy(HttpMessageConverter.class, new SingletonTargetSource(target));
		converters.add(proxy);
		RequestResponseBodyMethodProcessor processor = new RequestResponseBodyMethodProcessor(converters);

		SimpleBean result = (SimpleBean) processor.resolveArgument(methodParam, mavContainer, webRequest, binderFactory);

		assertNotNull(result);
		assertEquals("Jad", result.getName());
	}

	@Test  // SPR-9160
	public void handleReturnValueSortByQuality() throws Exception {
		this.servletRequest.addHeader("Accept", "text/plain; q=0.5, application/json");

		List<HttpMessageConverter<?>> converters = new ArrayList<HttpMessageConverter<?>>();
		converters.add(new MappingJackson2HttpMessageConverter());
		converters.add(new StringHttpMessageConverter());
		RequestResponseBodyMethodProcessor processor = new RequestResponseBodyMethodProcessor(converters);

		processor.writeWithMessageConverters("Foo", returnTypeString, webRequest);

		assertEquals("application/json;charset=UTF-8", servletResponse.getHeader("Content-Type"));
	}

	@Test
	public void handleReturnValueString() throws Exception {
		List<HttpMessageConverter<?>>converters = new ArrayList<HttpMessageConverter<?>>();
		converters.add(new ByteArrayHttpMessageConverter());
		converters.add(new StringHttpMessageConverter());

		RequestResponseBodyMethodProcessor processor = new RequestResponseBodyMethodProcessor(converters);
		processor.handleReturnValue("Foo", returnTypeString, mavContainer, webRequest);

		assertEquals("text/plain;charset=ISO-8859-1", servletResponse.getHeader("Content-Type"));
		assertEquals("Foo", servletResponse.getContentAsString());
	}

	@Test
	public void handleReturnValueStringAcceptCharset() throws Exception {
		this.servletRequest.addHeader("Accept", "text/plain;charset=UTF-8");

		List<HttpMessageConverter<?>> converters = new ArrayList<HttpMessageConverter<?>>();
		converters.add(new ByteArrayHttpMessageConverter());
		converters.add(new StringHttpMessageConverter());
		RequestResponseBodyMethodProcessor processor = new RequestResponseBodyMethodProcessor(converters);

		processor.writeWithMessageConverters("Foo", returnTypeString, webRequest);

		assertEquals("text/plain;charset=UTF-8", servletResponse.getHeader("Content-Type"));
	}

	// SPR-12894

	@Test
	public void handleReturnValueImage() throws Exception {
		this.servletRequest.addHeader("Accept", "*/*");

		Method method = getClass().getDeclaredMethod("getImage");
		MethodParameter returnType = new MethodParameter(method, -1);

		List<HttpMessageConverter<?>> converters = Collections.singletonList(new ResourceHttpMessageConverter());
		RequestResponseBodyMethodProcessor processor = new RequestResponseBodyMethodProcessor(converters);

		ClassPathResource resource = new ClassPathResource("logo.jpg", getClass());
		processor.writeWithMessageConverters(resource, returnType, this.webRequest);

		assertEquals("image/jpeg", this.servletResponse.getHeader("Content-Type"));
	}

	// SPR-13135

	@Test(expected = IllegalArgumentException.class)
	public void handleReturnValueWithInvalidReturnType() throws Exception {
		Method method = getClass().getDeclaredMethod("handleAndReturnOutputStream");
		MethodParameter returnType = new MethodParameter(method, -1);
		RequestResponseBodyMethodProcessor processor = new RequestResponseBodyMethodProcessor(new ArrayList<>());
		processor.writeWithMessageConverters(new ByteArrayOutputStream(), returnType, this.webRequest);
	}

	@Test
	public void supportsReturnTypeResponseBodyOnType() throws Exception {
		Method method = ResponseBodyController.class.getMethod("handle");
		MethodParameter returnType = new MethodParameter(method, -1);

		List<HttpMessageConverter<?>> converters = new ArrayList<HttpMessageConverter<?>>();
		converters.add(new StringHttpMessageConverter());

		RequestResponseBodyMethodProcessor processor = new RequestResponseBodyMethodProcessor(converters);

		assertTrue("Failed to recognize type-level @ResponseBody", processor.supportsReturnType(returnType));
	}

	@Test
	public void supportsReturnTypeRestController() throws Exception {
		Method method = TestRestController.class.getMethod("handle");
		MethodParameter returnType = new MethodParameter(method, -1);

		List<HttpMessageConverter<?>> converters = new ArrayList<HttpMessageConverter<?>>();
		converters.add(new StringHttpMessageConverter());

		RequestResponseBodyMethodProcessor processor = new RequestResponseBodyMethodProcessor(converters);

		assertTrue("Failed to recognize type-level @RestController", processor.supportsReturnType(returnType));
	}

	@Test
	public void jacksonJsonViewWithResponseBodyAndJsonMessageConverter() throws Exception {
		Method method = JacksonViewController.class.getMethod("handleResponseBody");
		HandlerMethod handlerMethod = new HandlerMethod(new JacksonViewController(), method);
		MethodParameter methodReturnType = handlerMethod.getReturnType();

		List<HttpMessageConverter<?>> converters = new ArrayList<HttpMessageConverter<?>>();
		converters.add(new MappingJackson2HttpMessageConverter());

		RequestResponseBodyMethodProcessor processor = new RequestResponseBodyMethodProcessor(
				converters, null, Collections.singletonList(new JsonViewResponseBodyAdvice()));

		Object returnValue = new JacksonViewController().handleResponseBody();
		processor.handleReturnValue(returnValue, methodReturnType, this.mavContainer, this.webRequest);

		String content = this.servletResponse.getContentAsString();
		assertFalse(content.contains("\"withView1\":\"with\""));
		assertTrue(content.contains("\"withView2\":\"with\""));
		assertFalse(content.contains("\"withoutView\":\"without\""));
	}

	@Test
	public void jacksonJsonViewWithResponseEntityAndJsonMessageConverter() throws Exception {
		Method method = JacksonViewController.class.getMethod("handleResponseEntity");
		HandlerMethod handlerMethod = new HandlerMethod(new JacksonViewController(), method);
		MethodParameter methodReturnType = handlerMethod.getReturnType();

		List<HttpMessageConverter<?>> converters = new ArrayList<HttpMessageConverter<?>>();
		converters.add(new MappingJackson2HttpMessageConverter());

		HttpEntityMethodProcessor processor = new HttpEntityMethodProcessor(
				converters, null, Collections.singletonList(new JsonViewResponseBodyAdvice()));

		Object returnValue = new JacksonViewController().handleResponseEntity();
		processor.handleReturnValue(returnValue, methodReturnType, this.mavContainer, this.webRequest);

		String content = this.servletResponse.getContentAsString();
		assertFalse(content.contains("\"withView1\":\"with\""));
		assertTrue(content.contains("\"withView2\":\"with\""));
		assertFalse(content.contains("\"withoutView\":\"without\""));
	}

	@Test  // SPR-12149
	public void jacksonJsonViewWithResponseBodyAndXmlMessageConverter() throws Exception {
		Method method = JacksonViewController.class.getMethod("handleResponseBody");
		HandlerMethod handlerMethod = new HandlerMethod(new JacksonViewController(), method);
		MethodParameter methodReturnType = handlerMethod.getReturnType();

		List<HttpMessageConverter<?>> converters = new ArrayList<HttpMessageConverter<?>>();
		converters.add(new MappingJackson2XmlHttpMessageConverter());

		RequestResponseBodyMethodProcessor processor = new RequestResponseBodyMethodProcessor(
				converters, null, Collections.singletonList(new JsonViewResponseBodyAdvice()));

		Object returnValue = new JacksonViewController().handleResponseBody();
		processor.handleReturnValue(returnValue, methodReturnType, this.mavContainer, this.webRequest);

		String content = this.servletResponse.getContentAsString();
		assertFalse(content.contains("<withView1>with</withView1>"));
		assertTrue(content.contains("<withView2>with</withView2>"));
		assertFalse(content.contains("<withoutView>without</withoutView>"));
	}

	@Test  // SPR-12149
	public void jacksonJsonViewWithResponseEntityAndXmlMessageConverter() throws Exception {
		Method method = JacksonViewController.class.getMethod("handleResponseEntity");
		HandlerMethod handlerMethod = new HandlerMethod(new JacksonViewController(), method);
		MethodParameter methodReturnType = handlerMethod.getReturnType();

		List<HttpMessageConverter<?>> converters = new ArrayList<HttpMessageConverter<?>>();
		converters.add(new MappingJackson2XmlHttpMessageConverter());

		HttpEntityMethodProcessor processor = new HttpEntityMethodProcessor(
				converters, null, Collections.singletonList(new JsonViewResponseBodyAdvice()));

		Object returnValue = new JacksonViewController().handleResponseEntity();
		processor.handleReturnValue(returnValue, methodReturnType, this.mavContainer, this.webRequest);

		String content = this.servletResponse.getContentAsString();
		assertFalse(content.contains("<withView1>with</withView1>"));
		assertTrue(content.contains("<withView2>with</withView2>"));
		assertFalse(content.contains("<withoutView>without</withoutView>"));
	}

	@Test  // SPR-12501
	public void resolveArgumentWithJacksonJsonView() throws Exception {
		String content = "{\"withView1\" : \"with\", \"withView2\" : \"with\", \"withoutView\" : \"without\"}";
		this.servletRequest.setContent(content.getBytes("UTF-8"));
		this.servletRequest.setContentType(MediaType.APPLICATION_JSON_VALUE);

		Method method = JacksonViewController.class.getMethod("handleRequestBody", JacksonViewBean.class);
		HandlerMethod handlerMethod = new HandlerMethod(new JacksonViewController(), method);
		MethodParameter methodParameter = handlerMethod.getMethodParameters()[0];

		List<HttpMessageConverter<?>> converters = new ArrayList<HttpMessageConverter<?>>();
		converters.add(new MappingJackson2HttpMessageConverter());

		RequestResponseBodyMethodProcessor processor = new RequestResponseBodyMethodProcessor(
				converters, null, Collections.singletonList(new JsonViewRequestBodyAdvice()));

		@SuppressWarnings("unchecked")
		JacksonViewBean result = (JacksonViewBean)processor.resolveArgument(methodParameter,
				this.mavContainer, this.webRequest, this.binderFactory);

		assertNotNull(result);
		assertEquals("with", result.getWithView1());
		assertNull(result.getWithView2());
		assertNull(result.getWithoutView());
	}

	@Test  // SPR-12501
	public void resolveHttpEntityArgumentWithJacksonJsonView() throws Exception {
		String content = "{\"withView1\" : \"with\", \"withView2\" : \"with\", \"withoutView\" : \"without\"}";
		this.servletRequest.setContent(content.getBytes("UTF-8"));
		this.servletRequest.setContentType(MediaType.APPLICATION_JSON_VALUE);

		Method method = JacksonViewController.class.getMethod("handleHttpEntity", HttpEntity.class);
		HandlerMethod handlerMethod = new HandlerMethod(new JacksonViewController(), method);
		MethodParameter methodParameter = handlerMethod.getMethodParameters()[0];

		List<HttpMessageConverter<?>> converters = new ArrayList<HttpMessageConverter<?>>();
		converters.add(new MappingJackson2HttpMessageConverter());

		HttpEntityMethodProcessor processor = new HttpEntityMethodProcessor(
				converters, null, Collections.singletonList(new JsonViewRequestBodyAdvice()));

		@SuppressWarnings("unchecked")
		HttpEntity<JacksonViewBean> result = (HttpEntity<JacksonViewBean>)processor.resolveArgument(methodParameter,
				this.mavContainer, this.webRequest, this.binderFactory);

		assertNotNull(result);
		assertNotNull(result.getBody());
		assertEquals("with", result.getBody().getWithView1());
		assertNull(result.getBody().getWithView2());
		assertNull(result.getBody().getWithoutView());
	}

	@Test  // SPR-12501
	public void resolveArgumentWithJacksonJsonViewAndXmlMessageConverter() throws Exception {
		String content = "<root><withView1>with</withView1><withView2>with</withView2><withoutView>without</withoutView></root>";
		this.servletRequest.setContent(content.getBytes("UTF-8"));
		this.servletRequest.setContentType(MediaType.APPLICATION_XML_VALUE);

		Method method = JacksonViewController.class.getMethod("handleRequestBody", JacksonViewBean.class);
		HandlerMethod handlerMethod = new HandlerMethod(new JacksonViewController(), method);
		MethodParameter methodParameter = handlerMethod.getMethodParameters()[0];

		List<HttpMessageConverter<?>> converters = new ArrayList<HttpMessageConverter<?>>();
		converters.add(new MappingJackson2XmlHttpMessageConverter());

		RequestResponseBodyMethodProcessor processor = new RequestResponseBodyMethodProcessor(
				converters, null, Collections.singletonList(new JsonViewRequestBodyAdvice()));

		@SuppressWarnings("unchecked")
		JacksonViewBean result = (JacksonViewBean)processor.resolveArgument(methodParameter,
				this.mavContainer, this.webRequest, this.binderFactory);

		assertNotNull(result);
		assertEquals("with", result.getWithView1());
		assertNull(result.getWithView2());
		assertNull(result.getWithoutView());
	}

	@Test  // SPR-12501
	public void resolveHttpEntityArgumentWithJacksonJsonViewAndXmlMessageConverter() throws Exception {
		String content = "<root><withView1>with</withView1><withView2>with</withView2><withoutView>without</withoutView></root>";
		this.servletRequest.setContent(content.getBytes("UTF-8"));
		this.servletRequest.setContentType(MediaType.APPLICATION_XML_VALUE);

		Method method = JacksonViewController.class.getMethod("handleHttpEntity", HttpEntity.class);
		HandlerMethod handlerMethod = new HandlerMethod(new JacksonViewController(), method);
		MethodParameter methodParameter = handlerMethod.getMethodParameters()[0];

		List<HttpMessageConverter<?>> converters = new ArrayList<HttpMessageConverter<?>>();
		converters.add(new MappingJackson2XmlHttpMessageConverter());

		HttpEntityMethodProcessor processor = new HttpEntityMethodProcessor(
				converters, null, Collections.singletonList(new JsonViewRequestBodyAdvice()));

		@SuppressWarnings("unchecked")
		HttpEntity<JacksonViewBean> result = (HttpEntity<JacksonViewBean>)processor.resolveArgument(methodParameter,
				this.mavContainer, this.webRequest, this.binderFactory);

		assertNotNull(result);
		assertNotNull(result.getBody());
		assertEquals("with", result.getBody().getWithView1());
		assertNull(result.getBody().getWithView2());
		assertNull(result.getBody().getWithoutView());
	}


	String handle(
			@RequestBody List<SimpleBean> list,
			@RequestBody SimpleBean simpleBean,
			@RequestBody MultiValueMap<String, String> multiValueMap,
			@RequestBody String string) {

		return null;
	}

	Resource getImage() {
		return null;
	}

	@RequestMapping
	OutputStream handleAndReturnOutputStream() {
		return null;
	}

	private static abstract class MyParameterizedController<DTO extends Identifiable> {

		@SuppressWarnings("unused")
		public void handleDto(@RequestBody DTO dto) {}
	}

	private static class MySimpleParameterizedController extends MyParameterizedController<SimpleBean> {
	}

	private interface Identifiable extends Serializable {

		Long getId();

		void setId(Long id);
	}


	@SuppressWarnings({ "serial" })
	private static class SimpleBean implements Identifiable {

		private Long id;

		private String name;

		@Override
		public Long getId() {
			return id;
		}

		@Override
		public void setId(Long id) {
			this.id = id;
		}

		public String getName() {
			return name;
		}

		public void setName(String name) {
			this.name = name;
		}
	}


	private final class ValidatingBinderFactory implements WebDataBinderFactory {

		@Override
		public WebDataBinder createBinder(NativeWebRequest webRequest, Object target, String objectName) throws Exception {
			LocalValidatorFactoryBean validator = new LocalValidatorFactoryBean();
			validator.afterPropertiesSet();
			WebDataBinder dataBinder = new WebDataBinder(target, objectName);
			dataBinder.setValidator(validator);
			return dataBinder;
		}
	}


	@ResponseBody
	private static class ResponseBodyController {

		@RequestMapping
		public String handle() {
			return "hello";
		}
	}


	@RestController
	private static class TestRestController {

		@RequestMapping
		public String handle() {
			return "hello";
		}
	}

	private interface MyJacksonView1 {}
	private interface MyJacksonView2 {}

	private static class JacksonViewBean {

		@JsonView(MyJacksonView1.class)
		private String withView1;

		@JsonView(MyJacksonView2.class)
		private String withView2;

		private String withoutView;

		public String getWithView1() {
			return withView1;
		}

		public void setWithView1(String withView1) {
			this.withView1 = withView1;
		}

		public String getWithView2() {
			return withView2;
		}

		public void setWithView2(String withView2) {
			this.withView2 = withView2;
		}

		public String getWithoutView() {
			return withoutView;
		}

		public void setWithoutView(String withoutView) {
			this.withoutView = withoutView;
		}
	}

	private static class JacksonViewController {

		@RequestMapping
		@ResponseBody
		@JsonView(MyJacksonView2.class)
		public JacksonViewBean handleResponseBody() {
			JacksonViewBean bean = new JacksonViewBean();
			bean.setWithView1("with");
			bean.setWithView2("with");
			bean.setWithoutView("without");
			return bean;
		}

		@RequestMapping
		@JsonView(MyJacksonView2.class)
		public ResponseEntity<JacksonViewBean> handleResponseEntity() {
			JacksonViewBean bean = new JacksonViewBean();
			bean.setWithView1("with");
			bean.setWithView2("with");
			bean.setWithoutView("without");
			ModelAndView mav = new ModelAndView(new MappingJackson2JsonView());
			mav.addObject("bean", bean);
			return new ResponseEntity<JacksonViewBean>(bean, HttpStatus.OK);
		}

		@RequestMapping
		@ResponseBody
		public JacksonViewBean handleRequestBody(@JsonView(MyJacksonView1.class) @RequestBody JacksonViewBean bean) {
			return bean;
		}

		@RequestMapping
		@ResponseBody
		public JacksonViewBean handleHttpEntity(@JsonView(MyJacksonView1.class) HttpEntity<JacksonViewBean> entity) {
			return entity.getBody();
		}
	}

	private static class EmptyRequestBodyAdvice implements RequestBodyAdvice {

		@Override
		public boolean supports(MethodParameter methodParameter, Type targetType,
				Class<? extends HttpMessageConverter<?>> converterType) {

			return StringHttpMessageConverter.class.equals(converterType);
		}

		@Override
		public Object handleEmptyBody(Object body, HttpInputMessage inputMessage, MethodParameter parameter,
				Type targetType, Class<? extends HttpMessageConverter<?>> converterType) {

			return "default value for empty body";
		}

		@Override
		public HttpInputMessage beforeBodyRead(HttpInputMessage inputMessage, MethodParameter parameter,
				Type targetType, Class<? extends HttpMessageConverter<?>> converterType) {

			return inputMessage;
		}

		@Override
		public Object afterBodyRead(Object body, HttpInputMessage inputMessage, MethodParameter parameter,
				Type targetType, Class<? extends HttpMessageConverter<?>> converterType) {

			return body;
		}
	}

}
