Refactoring Types: ['Extract Method']
pache/camel/Message.java
/**
 * Licensed to the Apache Software Foundation (ASF) under one or more
 * contributor license agreements.  See the NOTICE file distributed with
 * this work for additional information regarding copyright ownership.
 * The ASF licenses this file to You under the Apache License, Version 2.0
 * (the "License"); you may not use this file except in compliance with
 * the License.  You may obtain a copy of the License at
 *
 *      http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 */
package org.apache.camel;

import java.util.Map;
import java.util.Set;

import javax.activation.DataHandler;

/**
 * Implements the <a
 * href="http://camel.apache.org/message.html">Message</a> pattern and
 * represents an inbound or outbound message as part of an {@link Exchange}.
 * <p/>
 * See {@link org.apache.camel.impl.DefaultMessage DefaultMessage} for how headers
 * is represented in Camel using a {@link org.apache.camel.util.CaseInsensitiveMap CaseInsensitiveMap}.
 *
 * @version 
 */
public interface Message {

    /**
     * Returns the id of the message
     *
     * @return the message id
     */
    String getMessageId();

    /**
     * Sets the id of the message
     *
     * @param messageId id of the message
     */
    void setMessageId(String messageId);

    /**
     * Returns the exchange this message is related to
     *
     * @return the exchange
     */
    Exchange getExchange();

    /**
     * Returns true if this message represents a fault
     *
     * @return <tt>true</tt> if this is a fault message, <tt>false</tt> for regular messages.
     */
    boolean isFault();

    /**
     * Sets the fault flag on this message
     *
     * @param fault the fault flag
     */
    void setFault(boolean fault);

    /**
     * Accesses a specific header
     *
     * @param name  name of header
     * @return the value of the given header or <tt>null</tt> if there is no
     *         header for the given name
     */
    Object getHeader(String name);

    /**
     * Accesses a specific header
     *
     * @param name  name of header
     * @param defaultValue the default value to return if header was absent
     * @return the value of the given header or <tt>defaultValue</tt> if there is no
     *         header for the given name
     */
    Object getHeader(String name, Object defaultValue);

    /**
     * Returns a header associated with this message by name and specifying the
     * type required
     *
     * @param name the name of the header
     * @param type the type of the header
     * @return the value of the given header or <tt>null</tt> if there is no header for
     *         the given name
     * @throws TypeConversionException is thrown if error during type conversion
     */
    <T> T getHeader(String name, Class<T> type);

    /**
     * Returns a header associated with this message by name and specifying the
     * type required
     *
     * @param name the name of the header
     * @param defaultValue the default value to return if header was absent
     * @param type the type of the header
     * @return the value of the given header or <tt>defaultValue</tt> if there is no header for
     *         the given name or <tt>null</tt> if it cannot be converted to the given type
     */
    <T> T getHeader(String name, Object defaultValue, Class<T> type);

    /**
     * Sets a header on the message
     *
     * @param name of the header
     * @param value to associate with the name
     */
    void setHeader(String name, Object value);

    /**
     * Removes the named header from this message
     *
     * @param name name of the header
     * @return the old value of the header
     */
    Object removeHeader(String name);

    /**
     * Removes the headers from this message
     *
     * @param pattern pattern of names
     * @return boolean whether any headers matched
     */
    boolean removeHeaders(String pattern);
    
    /**
     * Removes the headers from this message that match the given <tt>pattern</tt>, 
     * except for the ones matching one ore more <tt>excludePatterns</tt>
     * 
     * @param pattern pattern of names that should be removed
     * @param excludePatterns one or more pattern of header names that should be excluded (= preserved)
     * @return boolean whether any headers matched
     */ 
    boolean removeHeaders(String pattern, String... excludePatterns);

    /**
     * Returns all of the headers associated with the message.
     * <p/>
     * See {@link org.apache.camel.impl.DefaultMessage DefaultMessage} for how headers
     * is represented in Camel using a {@link org.apache.camel.util.CaseInsensitiveMap CaseInsensitiveMap}.
     * <p/>
     * <b>Important:</b> If you want to walk the returned {@link Map} and fetch all the keys and values, you should use
     * the {@link java.util.Map#entrySet()} method, which ensure you get the keys in the original case.
     *
     * @return all the headers in a Map
     */
    Map<String, Object> getHeaders();

    /**
     * Set all the headers associated with this message
     * <p/>
     * <b>Important:</b> If you want to copy headers from another {@link Message} to this {@link Message}, then
     * use <tt>getHeaders().putAll(other)</tt> to copy the headers, where <tt>other</tt> is the other headers.
     *
     * @param headers headers to set
     */
    void setHeaders(Map<String, Object> headers);

    /**
     * Returns whether has any headers has been set.
     *
     * @return <tt>true</tt> if any headers has been set
     */
    boolean hasHeaders();

    /**
     * Returns the body of the message as a POJO
     * <p/>
     * The body can be <tt>null</tt> if no body is set
     *
     * @return the body, can be <tt>null</tt>
     */
    Object getBody();

    /**
     * Returns the body of the message as a POJO
     *
     * @return the body, is never <tt>null</tt>
     * @throws InvalidPayloadException Is thrown if the body being <tt>null</tt> or wrong class type
     */
    Object getMandatoryBody() throws InvalidPayloadException;

    /**
     * Returns the body as the specified type
     *
     * @param type the type that the body
     * @return the body of the message as the specified type, or <tt>null</tt> if no body exists
     * @throws TypeConversionException is thrown if error during type conversion
     */
    <T> T getBody(Class<T> type);

    /**
     * Returns the mandatory body as the specified type
     *
     * @param type the type that the body
     * @return the body of the message as the specified type, is never <tt>null</tt>.
     * @throws InvalidPayloadException Is thrown if the body being <tt>null</tt> or wrong class type
     */
    <T> T getMandatoryBody(Class<T> type) throws InvalidPayloadException;

    /**
     * Sets the body of the message
     *
     * @param body the body
     */
    void setBody(Object body);

    /**
     * Sets the body of the message as a specific type
     *
     * @param body the body
     * @param type the type of the body
     */
    <T> void setBody(Object body, Class<T> type);

    /**
     * Creates a copy of this message so that it can be used and possibly
     * modified further in another exchange
     *
     * @return a new message instance copied from this message
     */
    Message copy();

    /**
     * Copies the contents of the other message into this message
     *
     * @param message the other message
     */
    void copyFrom(Message message);

    /**
     * Returns the attachment specified by the id
     *
     * @param id the id under which the attachment is stored
     * @return the data handler for this attachment or <tt>null</tt>
     */
    DataHandler getAttachment(String id);

    /**
     * Returns a set of attachment names of the message
     *
     * @return a set of attachment names
     */
    Set<String> getAttachmentNames();

    /**
     * Removes the attachment specified by the id
     *
     * @param id   the id of the attachment to remove
     */
    void removeAttachment(String id);

    /**
     * Adds an attachment to the message using the id
     *
     * @param id        the id to store the attachment under
     * @param content   the data handler for the attachment
     */
    void addAttachment(String id, DataHandler content);

    /**
     * Returns all attachments of the message
     *
     * @return the attachments in a map or <tt>null</tt>
     */
    Map<String, DataHandler> getAttachments();

    /**
     * Set all the attachments associated with this message
     *
     * @param attachments the attachments
     */
    void setAttachments(Map<String, DataHandler> attachments);

    /**
     * Returns whether this message has attachments.
     *
     * @return <tt>true</tt> if this message has any attachments.
     */
    boolean hasAttachments();

    /**
     * Returns the unique ID for a message exchange if this message is capable
     * of creating one or <tt>null</tt> if not
     *
     * @return the created exchange id, or <tt>null</tt> if not capable of creating
     * @deprecated will be removed in Camel 3.0. It is discouraged for messages to create exchange ids
     */
    @Deprecated
    String createExchangeId();
}


File: camel-core/src/main/java/org/apache/camel/impl/DefaultExchange.java
/**
 * Licensed to the Apache Software Foundation (ASF) under one or more
 * contributor license agreements.  See the NOTICE file distributed with
 * this work for additional information regarding copyright ownership.
 * The ASF licenses this file to You under the Apache License, Version 2.0
 * (the "License"); you may not use this file except in compliance with
 * the License.  You may obtain a copy of the License at
 *
 *      http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 */
package org.apache.camel.impl;

import java.util.ArrayList;
import java.util.List;
import java.util.Map;
import java.util.concurrent.ConcurrentHashMap;

import org.apache.camel.CamelContext;
import org.apache.camel.Endpoint;
import org.apache.camel.Exchange;
import org.apache.camel.ExchangePattern;
import org.apache.camel.Message;
import org.apache.camel.MessageHistory;
import org.apache.camel.spi.Synchronization;
import org.apache.camel.spi.UnitOfWork;
import org.apache.camel.util.CaseInsensitiveMap;
import org.apache.camel.util.EndpointHelper;
import org.apache.camel.util.ExchangeHelper;
import org.apache.camel.util.ObjectHelper;

/**
 * A default implementation of {@link Exchange}
 *
 * @version 
 */
public final class DefaultExchange implements Exchange {

    protected final CamelContext context;
    private Map<String, Object> properties;
    private Message in;
    private Message out;
    private Exception exception;
    private String exchangeId;
    private UnitOfWork unitOfWork;
    private ExchangePattern pattern;
    private Endpoint fromEndpoint;
    private String fromRouteId;
    private List<Synchronization> onCompletions;

    public DefaultExchange(CamelContext context) {
        this(context, ExchangePattern.InOnly);
    }

    public DefaultExchange(CamelContext context, ExchangePattern pattern) {
        this.context = context;
        this.pattern = pattern;
    }

    public DefaultExchange(Exchange parent) {
        this(parent.getContext(), parent.getPattern());
        this.fromEndpoint = parent.getFromEndpoint();
        this.fromRouteId = parent.getFromRouteId();
        this.unitOfWork = parent.getUnitOfWork();
    }

    public DefaultExchange(Endpoint fromEndpoint) {
        this(fromEndpoint, ExchangePattern.InOnly);
    }

    public DefaultExchange(Endpoint fromEndpoint, ExchangePattern pattern) {
        this(fromEndpoint.getCamelContext(), pattern);
        this.fromEndpoint = fromEndpoint;
    }

    @Override
    public String toString() {
        return "Exchange[" + (out == null ? in : out) + "]";
    }

    public Exchange copy() {
        // to be backwards compatible as today
        return copy(false);
    }

    public Exchange copy(boolean safeCopy) {
        DefaultExchange exchange = new DefaultExchange(this);

        if (hasProperties()) {
            exchange.setProperties(safeCopyProperties(getProperties()));
        }

        if (safeCopy) {
            exchange.getIn().setBody(getIn().getBody());
            if (getIn().hasHeaders()) {
                exchange.getIn().setHeaders(safeCopyHeaders(getIn().getHeaders()));
            }
            if (hasOut()) {
                exchange.getOut().setBody(getOut().getBody());
                if (getOut().hasHeaders()) {
                    exchange.getOut().setHeaders(safeCopyHeaders(getOut().getHeaders()));
                }
            }
        } else {
            // old way of doing copy which is @deprecated
            // TODO: remove this in Camel 3.0, and always do a safe copy
            exchange.setIn(getIn().copy());
            if (hasOut()) {
                exchange.setOut(getOut().copy());
            }
        }
        exchange.setException(getException());
        return exchange;
    }

    @SuppressWarnings("unchecked")
    private static Map<String, Object> safeCopyHeaders(Map<String, Object> headers) {
        if (headers == null) {
            return null;
        }

        Map<String, Object> answer = new CaseInsensitiveMap();
        answer.putAll(headers);
        return answer;
    }

    @SuppressWarnings("unchecked")
    private static Map<String, Object> safeCopyProperties(Map<String, Object> properties) {
        if (properties == null) {
            return null;
        }

        // TODO: properties should use same map kind as headers
        Map<String, Object> answer = new ConcurrentHashMap<String, Object>(properties);

        // safe copy message history using a defensive copy
        List<MessageHistory> history = (List<MessageHistory>) answer.remove(Exchange.MESSAGE_HISTORY);
        if (history != null) {
            answer.put(Exchange.MESSAGE_HISTORY, new ArrayList<MessageHistory>(history));
        }

        return answer;
    }

    public CamelContext getContext() {
        return context;
    }

    public Object getProperty(String name) {
        if (properties != null) {
            return properties.get(name);
        }
        return null;
    }

    public Object getProperty(String name, Object defaultValue) {
        Object answer = getProperty(name);
        return answer != null ? answer : defaultValue;
    }

    @SuppressWarnings("unchecked")
    public <T> T getProperty(String name, Class<T> type) {
        Object value = getProperty(name);
        if (value == null) {
            // lets avoid NullPointerException when converting to boolean for null values
            if (boolean.class.isAssignableFrom(type)) {
                return (T) Boolean.FALSE;
            }
            return null;
        }

        // eager same instance type test to avoid the overhead of invoking the type converter
        // if already same type
        if (type.isInstance(value)) {
            return type.cast(value);
        }

        return ExchangeHelper.convertToType(this, type, value);
    }

    @SuppressWarnings("unchecked")
    public <T> T getProperty(String name, Object defaultValue, Class<T> type) {
        Object value = getProperty(name, defaultValue);
        if (value == null) {
            // lets avoid NullPointerException when converting to boolean for null values
            if (boolean.class.isAssignableFrom(type)) {
                return (T) Boolean.FALSE;
            }
            return null;
        }

        // eager same instance type test to avoid the overhead of invoking the type converter
        // if already same type
        if (type.isInstance(value)) {
            return type.cast(value);
        }

        return ExchangeHelper.convertToType(this, type, value);
    }

    public void setProperty(String name, Object value) {
        if (value != null) {
            // avoid the NullPointException
            getProperties().put(name, value);
        } else {
            // if the value is null, we just remove the key from the map
            if (name != null) {
                getProperties().remove(name);
            }
        }
    }

    public Object removeProperty(String name) {
        if (!hasProperties()) {
            return null;
        }
        return getProperties().remove(name);
    }

    public boolean removeProperties(String pattern) {
        return removeProperties(pattern, (String[]) null);
    }

    public boolean removeProperties(String pattern, String... excludePatterns) {
        if (!hasProperties()) {
            return false;
        }

        boolean matches = false;
        for (Map.Entry<String, Object> entry : properties.entrySet()) {
            String key = entry.getKey();
            if (EndpointHelper.matchPattern(key, pattern)) {
                if (excludePatterns != null && isExcludePatternMatch(key, excludePatterns)) {
                    continue;
                }
                matches = true;
                properties.remove(entry.getKey());
            }

        }
        return matches;
    }

    public Map<String, Object> getProperties() {
        if (properties == null) {
            properties = new ConcurrentHashMap<String, Object>();
        }
        return properties;
    }

    public boolean hasProperties() {
        return properties != null && !properties.isEmpty();
    }

    public void setProperties(Map<String, Object> properties) {
        this.properties = properties;
    }

    public Message getIn() {
        if (in == null) {
            in = new DefaultMessage();
            configureMessage(in);
        }
        return in;
    }

    public <T> T getIn(Class<T> type) {
        Message in = getIn();

        // eager same instance type test to avoid the overhead of invoking the type converter
        // if already same type
        if (type.isInstance(in)) {
            return type.cast(in);
        }

        // fallback to use type converter
        return context.getTypeConverter().convertTo(type, this, in);
    }

    public void setIn(Message in) {
        this.in = in;
        configureMessage(in);
    }

    public Message getOut() {
        // lazy create
        if (out == null) {
            out = (in != null && in instanceof MessageSupport)
                ? ((MessageSupport)in).newInstance() : new DefaultMessage();
            configureMessage(out);
        }
        return out;
    }

    public <T> T getOut(Class<T> type) {
        if (!hasOut()) {
            return null;
        }

        Message out = getOut();

        // eager same instance type test to avoid the overhead of invoking the type converter
        // if already same type
        if (type.isInstance(out)) {
            return type.cast(out);
        }

        // fallback to use type converter
        return context.getTypeConverter().convertTo(type, this, out);
    }

    public boolean hasOut() {
        return out != null;
    }

    public void setOut(Message out) {
        this.out = out;
        configureMessage(out);
    }

    public Exception getException() {
        return exception;
    }

    public <T> T getException(Class<T> type) {
        return ObjectHelper.getException(type, exception);
    }

    public void setException(Throwable t) {
        if (t == null) {
            this.exception = null;
        } else if (t instanceof Exception) {
            this.exception = (Exception) t;
        } else {
            // wrap throwable into an exception
            this.exception = ObjectHelper.wrapCamelExecutionException(this, t);
        }
    }

    public ExchangePattern getPattern() {
        return pattern;
    }

    public void setPattern(ExchangePattern pattern) {
        this.pattern = pattern;
    }

    public Endpoint getFromEndpoint() {
        return fromEndpoint;
    }

    public void setFromEndpoint(Endpoint fromEndpoint) {
        this.fromEndpoint = fromEndpoint;
    }

    public String getFromRouteId() {
        return fromRouteId;
    }

    public void setFromRouteId(String fromRouteId) {
        this.fromRouteId = fromRouteId;
    }

    public String getExchangeId() {
        if (exchangeId == null) {
            exchangeId = createExchangeId();
        }
        return exchangeId;
    }

    public void setExchangeId(String id) {
        this.exchangeId = id;
    }

    public boolean isFailed() {
        if (exception != null) {
            return true;
        }
        return hasOut() ? getOut().isFault() : getIn().isFault();
    }

    public boolean isTransacted() {
        UnitOfWork uow = getUnitOfWork();
        if (uow != null) {
            return uow.isTransacted();
        } else {
            return false;
        }
    }

    public Boolean isExternalRedelivered() {
        Boolean answer = null;

        // check property first, as the implementation details to know if the message
        // was externally redelivered is message specific, and thus the message implementation
        // could potentially change during routing, and therefore later we may not know if the
        // original message was externally redelivered or not, therefore we store this detail
        // as a exchange property to keep it around for the lifecycle of the exchange
        if (hasProperties()) {
            answer = getProperty(Exchange.EXTERNAL_REDELIVERED, null, Boolean.class);
        }
        
        if (answer == null) {
            // lets avoid adding methods to the Message API, so we use the
            // DefaultMessage to allow component specific messages to extend
            // and implement the isExternalRedelivered method.
            DefaultMessage msg = getIn(DefaultMessage.class);
            if (msg != null) {
                answer = msg.isTransactedRedelivered();
                // store as property to keep around
                setProperty(Exchange.EXTERNAL_REDELIVERED, answer);
            }
        }

        return answer;
    }

    public boolean isRollbackOnly() {
        return Boolean.TRUE.equals(getProperty(Exchange.ROLLBACK_ONLY)) || Boolean.TRUE.equals(getProperty(Exchange.ROLLBACK_ONLY_LAST));
    }

    public UnitOfWork getUnitOfWork() {
        return unitOfWork;
    }

    public void setUnitOfWork(UnitOfWork unitOfWork) {
        this.unitOfWork = unitOfWork;
        if (unitOfWork != null && onCompletions != null) {
            // now an unit of work has been assigned so add the on completions
            // we might have registered already
            for (Synchronization onCompletion : onCompletions) {
                unitOfWork.addSynchronization(onCompletion);
            }
            // cleanup the temporary on completion list as they now have been registered
            // on the unit of work
            onCompletions.clear();
            onCompletions = null;
        }
    }

    public void addOnCompletion(Synchronization onCompletion) {
        if (unitOfWork == null) {
            // unit of work not yet registered so we store the on completion temporary
            // until the unit of work is assigned to this exchange by the unit of work
            if (onCompletions == null) {
                onCompletions = new ArrayList<Synchronization>();
            }
            onCompletions.add(onCompletion);
        } else {
            getUnitOfWork().addSynchronization(onCompletion);
        }
    }

    public boolean containsOnCompletion(Synchronization onCompletion) {
        if (unitOfWork != null) {
            // if there is an unit of work then the completions is moved there
            return unitOfWork.containsSynchronization(onCompletion);
        } else {
            // check temporary completions if no unit of work yet
            return onCompletions != null && onCompletions.contains(onCompletion);
        }
    }

    public void handoverCompletions(Exchange target) {
        if (onCompletions != null) {
            for (Synchronization onCompletion : onCompletions) {
                target.addOnCompletion(onCompletion);
            }
            // cleanup the temporary on completion list as they have been handed over
            onCompletions.clear();
            onCompletions = null;
        } else if (unitOfWork != null) {
            // let unit of work handover
            unitOfWork.handoverSynchronization(target);
        }
    }

    public List<Synchronization> handoverCompletions() {
        List<Synchronization> answer = null;
        if (onCompletions != null) {
            answer = new ArrayList<Synchronization>(onCompletions);
            onCompletions.clear();
            onCompletions = null;
        }
        return answer;
    }

    /**
     * Configures the message after it has been set on the exchange
     */
    protected void configureMessage(Message message) {
        if (message instanceof MessageSupport) {
            MessageSupport messageSupport = (MessageSupport)message;
            messageSupport.setExchange(this);
        }
    }

    @SuppressWarnings("deprecation")
    protected String createExchangeId() {
        String answer = null;
        if (in != null) {
            answer = in.createExchangeId();
        }
        if (answer == null) {
            answer = context.getUuidGenerator().generateUuid();
        }
        return answer;
    }
    
    private static boolean isExcludePatternMatch(String key, String... excludePatterns) {
        for (String pattern : excludePatterns) {
            if (EndpointHelper.matchPattern(key, pattern)) {
                return true;
            }
        }
        return false;
    }
}


File: camel-core/src/main/java/org/apache/camel/impl/MessageSupport.java
/**
 * Licensed to the Apache Software Foundation (ASF) under one or more
 * contributor license agreements.  See the NOTICE file distributed with
 * this work for additional information regarding copyright ownership.
 * The ASF licenses this file to You under the Apache License, Version 2.0
 * (the "License"); you may not use this file except in compliance with
 * the License.  You may obtain a copy of the License at
 *
 *      http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 */
package org.apache.camel.impl;

import org.apache.camel.Exchange;
import org.apache.camel.InvalidPayloadException;
import org.apache.camel.Message;
import org.apache.camel.TypeConverter;

/**
 * A base class for implementation inheritance providing the core
 * {@link Message} body handling features but letting the derived class deal
 * with headers.
 *
 * Unless a specific provider wishes to do something particularly clever with
 * headers you probably want to just derive from {@link DefaultMessage}
 *
 * @version 
 */
public abstract class MessageSupport implements Message {
    private Exchange exchange;
    private Object body;
    private String messageId;

    public Object getBody() {
        if (body == null) {
            body = createBody();
        }
        return body;
    }

    public <T> T getBody(Class<T> type) {
        return getBody(type, getBody());
    }

    public Object getMandatoryBody() throws InvalidPayloadException {
        Object answer = getBody();
        if (answer == null) {
            throw new InvalidPayloadException(getExchange(), Object.class, this);
        }
        return answer;
    }

    protected <T> T getBody(Class<T> type, Object body) {
        // eager same instance type test to avoid the overhead of invoking the type converter
        // if already same type
        if (type.isInstance(body)) {
            return type.cast(body);
        }

        Exchange e = getExchange();
        if (e != null) {
            TypeConverter converter = e.getContext().getTypeConverter();

            // lets first try converting the body itself first
            // as for some types like InputStream v Reader its more efficient to do the transformation
            // from the body itself as its got efficient implementations of them, before trying the message
            T answer = converter.convertTo(type, e, body);
            if (answer != null) {
                return answer;
            }

            // fallback and try the message itself (e.g. used in camel-http)
            answer = converter.tryConvertTo(type, e, this);
            if (answer != null) {
                return answer;
            }
        }

        // not possible to convert
        return null;
    }

    public <T> T getMandatoryBody(Class<T> type) throws InvalidPayloadException {
        // eager same instance type test to avoid the overhead of invoking the type converter
        // if already same type
        if (type.isInstance(body)) {
            return type.cast(body);
        }

        Exchange e = getExchange();
        if (e != null) {
            TypeConverter converter = e.getContext().getTypeConverter();
            try {
                return converter.mandatoryConvertTo(type, e, getBody());
            } catch (Exception cause) {
                throw new InvalidPayloadException(e, type, this, cause);
            }
        }
        throw new InvalidPayloadException(e, type, this);
    }

    public void setBody(Object body) {
        this.body = body;
    }

    public <T> void setBody(Object value, Class<T> type) {
        Exchange e = getExchange();
        if (e != null) {
            T v = e.getContext().getTypeConverter().convertTo(type, e, value);
            if (v != null) {
                value = v;
            }
        }
        setBody(value);
    }

    public Message copy() {
        Message answer = newInstance();
        answer.copyFrom(this);
        return answer;
    }

    public void copyFrom(Message that) {
        if (that == this) {
            // the same instance so do not need to copy
            return;
        }

        setMessageId(that.getMessageId());
        setBody(that.getBody());
        setFault(that.isFault());

        // the headers may be the same instance if the end user has made some mistake
        // and set the OUT message with the same header instance of the IN message etc
        boolean sameHeadersInstance = false;
        if (hasHeaders() && that.hasHeaders() && getHeaders() == that.getHeaders()) {
            sameHeadersInstance = true;
        }

        if (!sameHeadersInstance) {
            if (hasHeaders()) {
                // okay its safe to clear the headers
                getHeaders().clear();
            }
            if (that.hasHeaders()) {
                getHeaders().putAll(that.getHeaders());
            }
        }

        // the attachments may be the same instance if the end user has made some mistake
        // and set the OUT message with the same attachment instance of the IN message etc
        boolean sameAttachments = false;
        if (hasAttachments() && that.hasAttachments() && getAttachments() == that.getAttachments()) {
            sameAttachments = true;
        }

        if (!sameAttachments) {
            if (hasAttachments()) {
                // okay its safe to clear the attachments
                getAttachments().clear();
            }
            if (that.hasAttachments()) {
                getAttachments().putAll(that.getAttachments());
            }
        }
    }

    public Exchange getExchange() {
        return exchange;
    }

    public void setExchange(Exchange exchange) {
        this.exchange = exchange;
    }

    /**
     * Returns a new instance
     */
    public abstract Message newInstance();

    /**
     * A factory method to allow a provider to lazily create the message body
     * for inbound messages from other sources
     *
     * @return the value of the message body or null if there is no value
     *         available
     */
    protected Object createBody() {
        return null;
    }

    public String getMessageId() {
        if (messageId == null) {
            messageId = createMessageId();
        }
        return this.messageId;
    }

    public void setMessageId(String messageId) {
        this.messageId = messageId;
    }

    /**
     * Allow implementations to auto-create a messageId
     */
    protected String createMessageId() {
        String uuid = null;
        if (exchange != null) {
            uuid = exchange.getContext().getUuidGenerator().generateUuid();
        }
        // fall back to the simple UUID generator
        if (uuid == null) {
            uuid = new SimpleUuidGenerator().generateUuid();
        }
        return uuid;
    }
}
