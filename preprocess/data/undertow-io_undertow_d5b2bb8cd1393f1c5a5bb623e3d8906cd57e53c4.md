Refactoring Types: ['Move Method', 'Extract Method', 'Move Class']
oss, Home of Professional Open Source.
 * Copyright 2014 Red Hat, Inc., and individual contributors
 * as indicated by the @author tags.
 *
 * Licensed under the Apache License, Version 2.0 (the "License");
 * you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at
 *
 *     http://www.apache.org/licenses/LICENSE-2.0
 *
 *  Unless required by applicable law or agreed to in writing, software
 *  distributed under the License is distributed on an "AS IS" BASIS,
 *  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 *  See the License for the specific language governing permissions and
 *  limitations under the License.
 */

package io.undertow;

import io.undertow.client.ClientConnection;
import io.undertow.server.ServerConnection;
import io.undertow.util.HeaderMap;
import io.undertow.util.HttpString;
import org.jboss.logging.BasicLogger;
import org.jboss.logging.Logger;
import org.jboss.logging.annotations.Cause;
import org.jboss.logging.annotations.LogMessage;
import org.jboss.logging.annotations.Message;
import org.jboss.logging.annotations.MessageLogger;

import java.io.IOException;
import java.net.InetAddress;
import java.net.InetSocketAddress;
import java.net.SocketAddress;
import java.net.URI;
import java.nio.file.Path;
import java.sql.SQLException;
import java.util.List;

import static org.jboss.logging.Logger.Level.DEBUG;
import static org.jboss.logging.Logger.Level.INFO;
import static org.jboss.logging.Logger.Level.WARN;

/**
 * log messages start at 5000
 *
 * @author Stuart Douglas
 */
@MessageLogger(projectCode = "UT")
public interface UndertowLogger extends BasicLogger {

    UndertowLogger ROOT_LOGGER = Logger.getMessageLogger(UndertowLogger.class, UndertowLogger.class.getPackage().getName());
    UndertowLogger CLIENT_LOGGER = Logger.getMessageLogger(UndertowLogger.class, ClientConnection.class.getPackage().getName());

    UndertowLogger REQUEST_LOGGER = Logger.getMessageLogger(UndertowLogger.class, UndertowLogger.class.getPackage().getName() + ".request");
    UndertowLogger PROXY_REQUEST_LOGGER = Logger.getMessageLogger(UndertowLogger.class, UndertowLogger.class.getPackage().getName() + ".proxy");
    UndertowLogger REQUEST_DUMPER_LOGGER = Logger.getMessageLogger(UndertowLogger.class, UndertowLogger.class.getPackage().getName() + ".request.dump");
    /**
     * Logger used for IO exceptions. Generally these should be suppressed, because they are of little interest, and it is easy for an
     * attacker to fill up the logs by intentionally causing IO exceptions.
     */
    UndertowLogger REQUEST_IO_LOGGER = Logger.getMessageLogger(UndertowLogger.class, UndertowLogger.class.getPackage().getName() + ".request.io");

    @LogMessage(level = Logger.Level.ERROR)
    @Message(id = 5001, value = "An exception occurred processing the request")
    void exceptionProcessingRequest(@Cause Throwable cause);

    @LogMessage(level = INFO)
    @Message(id = 5002, value = "Exception reading file %s: %s")
    void exceptionReadingFile(final Path file, final IOException e);

    @LogMessage(level = Logger.Level.ERROR)
    @Message(id = 5003, value = "IOException reading from channel")
    void ioExceptionReadingFromChannel(@Cause IOException e);

    @LogMessage(level = Logger.Level.ERROR)
    @Message(id = 5005, value = "Cannot remove uploaded file %s")
    void cannotRemoveUploadedFile(Path file);

    @LogMessage(level = Logger.Level.ERROR)
    @Message(id = 5006, value = "Connection from %s terminated as request header was larger than %s")
    void requestHeaderWasTooLarge(SocketAddress address, int size);

    @LogMessage(level = DEBUG)
    @Message(id = 5007, value = "Request was not fully consumed")
    void requestWasNotFullyConsumed();

    @LogMessage(level = DEBUG)
    @Message(id = 5008, value = "An invalid token '%s' with value '%s' has been received.")
    void invalidTokenReceived(final String tokenName, final String tokenValue);

    @LogMessage(level = DEBUG)
    @Message(id = 5009, value = "A mandatory token %s is missing from the request.")
    void missingAuthorizationToken(final String tokenName);

    @LogMessage(level = DEBUG)
    @Message(id = 5010, value = "Verification of authentication tokens for user '%s' has failed using mechanism '%s'.")
    void authenticationFailed(final String userName, final String mechanism);

    @LogMessage(level = Logger.Level.ERROR)
    @Message(id = 5011, value = "Ignoring AJP request with prefix %s")
    void ignoringAjpRequestWithPrefixCode(byte prefix);

    @LogMessage(level = DEBUG)
    @Message(id = 5013, value = "An IOException occurred")
    void ioException(@Cause IOException e);

    @LogMessage(level = DEBUG)
    @Message(id = 5014, value = "Failed to parse HTTP request")
    void failedToParseRequest(@Cause Exception e);

    @LogMessage(level = Logger.Level.ERROR)
    @Message(id = 5015, value = "Error rotating access log")
    void errorRotatingAccessLog(@Cause IOException e);

    @LogMessage(level = Logger.Level.ERROR)
    @Message(id = 5016, value = "Error writing access log")
    void errorWritingAccessLog(@Cause IOException e);

    @LogMessage(level = Logger.Level.ERROR)
    @Message(id = 5017, value = "Unknown variable %s")
    void unknownVariable(String token);

    @LogMessage(level = Logger.Level.ERROR)
    @Message(id = 5018, value = "Exception invoking close listener %s")
    void exceptionInvokingCloseListener(ServerConnection.CloseListener l, @Cause Throwable e);

    @LogMessage(level = Logger.Level.ERROR)
    @Message(id = 5019, value = "Cannot upgrade connection")
    void cannotUpgradeConnection(@Cause Exception e);

    @LogMessage(level = Logger.Level.ERROR)
    @Message(id = 5020, value = "Error writing JDBC log")
    void errorWritingJDBCLog(@Cause SQLException e);

    @LogMessage(level = Logger.Level.ERROR)
    @Message(id = 5021, value = "Proxy request to %s timed out")
    void proxyRequestTimedOut(String requestURI);

    @LogMessage(level = Logger.Level.ERROR)
    @Message(id = 5022, value = "Exception generating error page %s")
    void exceptionGeneratingErrorPage(@Cause Exception e, String location);

    @LogMessage(level = Logger.Level.ERROR)
    @Message(id = 5023, value = "Exception handling request to %s")
    void exceptionHandlingRequest(@Cause Throwable t, String requestURI);

    @LogMessage(level = Logger.Level.ERROR)
    @Message(id = 5024, value = "Could not register resource change listener for caching resource manager, automatic invalidation of cached resource will not work")
    void couldNotRegisterChangeListener(@Cause Exception e);

    @LogMessage(level = Logger.Level.ERROR)
    @Message(id = 5025, value = "Could not initiate SPDY connection and no HTTP fallback defined")
    void couldNotInitiateSpdyConnection();

    @LogMessage(level = Logger.Level.ERROR)
    @Message(id = 5026, value = "Jetty ALPN support not found on boot class path, %s client will not be available.")
    void jettyALPNNotFound(String protocol);

    @LogMessage(level = Logger.Level.ERROR)
    @Message(id = 5027, value = "Timing out request to %s")
    void timingOutRequest(String requestURI);

    @LogMessage(level = Logger.Level.ERROR)
    @Message(id = 5028, value = "Proxy request to %s failed")
    void proxyRequestFailed(String requestURI, @Cause Exception e);

    @LogMessage(level = Logger.Level.ERROR)
    @Message(id = 5030, value = "Proxy request to %s could not resolve a backend server")
    void proxyRequestFailedToResolveBackend(String requestURI);

    @LogMessage(level = Logger.Level.ERROR)
    @Message(id = 5031, value = "Proxy request to %s could not connect to backend server %s")
    void proxyFailedToConnectToBackend(String requestURI, URI uri);

    @LogMessage(level = Logger.Level.ERROR)
    @Message(id = 5032, value = "Listener not making progress on framed channel, closing channel to prevent infinite loop")
    void listenerNotProgressing();

    @LogMessage(level = Logger.Level.ERROR)
    @Message(id = 5033, value = "Failed to initiate HTTP2 connection")
    void couldNotInitiateHttp2Connection();

    @LogMessage(level = Logger.Level.ERROR)
    @Message(id = 5034, value = "Remote endpoint failed to send initial settings frame in HTTP2 connection, frame type %s")
    void remoteEndpointFailedToSendInitialSettings(int type);

    @LogMessage(level = DEBUG)
    @Message(id = 5035, value = "Closing channel because of parse timeout for remote address %s")
    void parseRequestTimedOut(java.net.SocketAddress remoteAddress);

    @LogMessage(level = Logger.Level.ERROR)
    @Message(id = 5036, value = "ALPN negotiation failed for %s and no fallback defined, closing connection")
    void noALPNFallback(SocketAddress address);

    /**
     * Undertow mod_cluster proxy messages
     */
    @LogMessage(level = WARN)
    @Message(id = 5037, value = "Name of the cookie containing the session id, %s, had been too long and was truncated to: %s")
    void stickySessionCookieLengthTruncated(String original, String current);

    @LogMessage(level = DEBUG)
    @Message(id = 5038, value = "Balancer created: id: %s, name: %s, stickySession: %s, stickySessionCookie: %s, stickySessionPath: %s, stickySessionRemove: %s, stickySessionForce: %s, waitWorker: %s, maxattempts: %s")
    void balancerCreated(int id, String name, boolean stickySession, String stickySessionCookie, String stickySessionPath, boolean stickySessionRemove,
                                            boolean stickySessionForce, int waitWorker, int maxattempts);

    @LogMessage(level = INFO)
    @Message(id = 5039, value = "Undertow starts mod_cluster proxy advertisements on %s with frequency %s ms")
    void proxyAdvertisementsStarted(String address, int frequency);

    @LogMessage(level = DEBUG)
    @Message(id = 5040, value = "Gonna send payload:\n%s")
    void proxyAdvertiseMessagePayload(String payload);

    @LogMessage(level = Logger.Level.ERROR)
    @Message(id = 5041, value = "Cannot send advertise message. Address: %s")
    void proxyAdvertiseCannotSendMessage(@Cause Exception e, InetSocketAddress address);

    @LogMessage(level = DEBUG)
    @Message(id = 5042, value = "Undertow mod_cluster proxy MCMPHandler created")
    void mcmpHandlerCreated();

    @LogMessage(level = Logger.Level.ERROR)
    @Message(id = 5043, value = "Error in processing MCMP commands: Type:%s, Mess: %s")
    void mcmpProcessingError(String type, String errString);

    @LogMessage(level = INFO)
    @Message(id = 5044, value = "Removing node %s")
    void removingNode(String jvmRoute);

    // Aliases intentionally omitted from INFO level.
    @LogMessage(level = INFO)
    @Message(id = 5045, value = "Registering context %s, for node %s")
    void registeringContext(String contextPath, String jvmRoute);

    // Context path and JVMRoute redundantly logged with DEBUG soa s to provide meaning for aliases.
    @LogMessage(level = DEBUG)
    @Message(id = 5046, value = "Registering context %s, for node %s, with aliases %s")
    void registeringContext(String contextPath, String jvmRoute, List<String> aliases);

    @LogMessage(level = INFO)
    @Message(id = 5047, value = "Unregistering context %s, from node %s")
    void unregisteringContext(String contextPath, String jvmRoute);

    @LogMessage(level = DEBUG)
    @Message(id = 5048, value = "Node %s in error")
    void nodeIsInError(String jvmRoute);

    @LogMessage(level = DEBUG)
    @Message(id = 5049, value = "NodeConfig created: connectionURI: %s, balancer: %s, domain: %s, jvmRoute: %s, flushPackets: %s, flushwait: %s, ping: %s," +
            "ttl: %s, timeout: %s, maxConnections: %s, cacheConnections: %s, requestQueueSize: %s, queueNewRequests: %s")
    void nodeConfigCreated(URI connectionURI, String balancer, String domain, String jvmRoute, boolean flushPackets, int flushwait, int ping, long ttl,
                           int timeout, int maxConnections, int cacheConnections, int requestQueueSize, boolean queueNewRequests);

    @LogMessage(level = Logger.Level.ERROR)
    @Message(id = 5050, value = "Failed to process management request")
    void failedToProcessManagementReq(@Cause Exception e);

    @LogMessage(level = Logger.Level.ERROR)
    @Message(id = 5051, value = "Failed to send ping response")
    void failedToSendPingResponse(@Cause Exception e);

    @LogMessage(level = DEBUG)
    @Message(id = 5052, value = "Failed to send ping response, node.getJvmRoute(): %s, jvmRoute: %s")
    void failedToSendPingResponseDBG(@Cause Exception e, String node, String jvmRoute);

    @LogMessage(level = INFO)
    @Message(id = 5053, value = "Registering node %s, connection: %s")
    void registeringNode(String jvmRoute, URI connectionURI);

    @LogMessage(level = DEBUG)
    @Message(id = 5054, value = "MCMP processing, key: %s, value: %s")
    void mcmpKeyValue(HttpString name, String value);

    @LogMessage(level = DEBUG)
    @Message(id = 5055, value = "HttpClientPingTask run for connection: %s")
    void httpClientPingTask(URI connection);

    @LogMessage(level = DEBUG)
    @Message(id = 5056, value = "Received node load in STATUS message, node jvmRoute: %s, load: %s")
    void receivedNodeLoad(String jvmRoute, String loadValue);

    @LogMessage(level = DEBUG)
    @Message(id = 5057, value = "Sending MCMP response to destination: %s, HTTP status: %s, Headers: %s, response: %s")
    void mcmpSendingResponse(InetSocketAddress destination, int status, HeaderMap headers, String response);

    @LogMessage(level = WARN)
    @Message(id = 5058, value = "Could not bind multicast socket to %s (%s address): %s; make sure your multicast address is of the same type as the IP stack (IPv4 or IPv6). Multicast socket will not be bound to an address, but this may lead to cross talking (see http://www.jboss.org/community/docs/DOC-9469 for details).")
    void potentialCrossTalking(InetAddress group, String s, String localizedMessage);

    @LogMessage(level = WARN)
    @Message(id = 5059, value = "Request dumping handler is in use. This handler is intended for debugging use only, and may dump sensitive data to the logs")
    void warnRequestDumpingHandler();

    @LogMessage(level = org.jboss.logging.Logger.Level.WARN)
    @Message(id = 5060, value = "Predicate %s uses old style square braces to define predicates, which will be removed in a future release. predicate[value] should be changed to predicate(value)")
    void oldStylePredicateSyntax(String string);

}


File: core/src/main/java/io/undertow/predicate/ContainsPredicate.java
/*
 * JBoss, Home of Professional Open Source.
 * Copyright 2014 Red Hat, Inc., and individual contributors
 * as indicated by the @author tags.
 *
 * Licensed under the Apache License, Version 2.0 (the "License");
 * you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at
 *
 *     http://www.apache.org/licenses/LICENSE-2.0
 *
 *  Unless required by applicable law or agreed to in writing, software
 *  distributed under the License is distributed on an "AS IS" BASIS,
 *  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 *  See the License for the specific language governing permissions and
 *  limitations under the License.
 */

package io.undertow.predicate;

import java.util.HashMap;
import java.util.HashSet;
import java.util.Map;
import java.util.Set;

import io.undertow.attribute.ExchangeAttribute;
import io.undertow.server.HttpServerExchange;

/**
 * Returns true if the request header is present and contains one of the strings to match.
 *
 * @author Stuart Douglas
 */
class ContainsPredicate implements Predicate {

    private final ExchangeAttribute attribute;
    private final String[] values;

    ContainsPredicate(final ExchangeAttribute attribute, final String[] values) {
        this.attribute = attribute;
        this.values = new String[values.length];
        System.arraycopy(values, 0, this.values, 0, values.length);
    }

    @Override
    public boolean resolve(final HttpServerExchange value) {
        String attr = attribute.readAttribute(value);
        if (attr == null) {
            return false;
        }
        for (int i = 0; i < values.length; ++i) {
            if (attr.contains(values[i])) {
                return true;
            }
        }
        return false;
    }

    public static class Builder implements PredicateBuilder {

        @Override
        public String name() {
            return "contains";
        }

        @Override
        public Map<String, Class<?>> parameters() {
            final Map<String, Class<?>> params = new HashMap<>();
            params.put("value", ExchangeAttribute.class);
            params.put("search", String[].class);
            return params;
        }

        @Override
        public Set<String> requiredParameters() {
            final Set<String> params = new HashSet<>();
            params.add("value");
            params.add("search");
            return params;
        }

        @Override
        public String defaultParameter() {
            return null;
        }

        @Override
        public Predicate build(final Map<String, Object> config) {
            String[] search = (String[]) config.get("search");
            ExchangeAttribute values = (ExchangeAttribute) config.get("value");
            return new ContainsPredicate(values, search);
        }
    }
}


File: core/src/main/java/io/undertow/predicate/PredicateParser.java
/*
 * JBoss, Home of Professional Open Source.
 * Copyright 2014 Red Hat, Inc., and individual contributors
 * as indicated by the @author tags.
 *
 * Licensed under the Apache License, Version 2.0 (the "License");
 * you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at
 *
 *     http://www.apache.org/licenses/LICENSE-2.0
 *
 *  Unless required by applicable law or agreed to in writing, software
 *  distributed under the License is distributed on an "AS IS" BASIS,
 *  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 *  See the License for the specific language governing permissions and
 *  limitations under the License.
 */

package io.undertow.predicate;

import java.lang.reflect.Array;
import java.util.ArrayDeque;
import java.util.ArrayList;
import java.util.Collections;
import java.util.Deque;
import java.util.HashMap;
import java.util.HashSet;
import java.util.List;
import java.util.Map;
import java.util.ServiceLoader;
import java.util.Set;

import io.undertow.UndertowLogger;
import io.undertow.UndertowMessages;
import io.undertow.attribute.ExchangeAttribute;
import io.undertow.attribute.ExchangeAttributeParser;
import io.undertow.attribute.ExchangeAttributes;
import io.undertow.util.PredicateTokeniser;
import io.undertow.util.PredicateTokeniser.Token;

/**
 * Parser that can build a predicate from a string representation. The underlying syntax is quite simple, and example is
 * shown below:
 * <p>
 * <code>
 * path["/MyPath"] or (method[value="POST"] and not headersPresent[value={Content-Type, "Content-Encoding"}, ignoreTrailer=true]
 * </code>
 * <p>
 * The following boolean operators are built in, listed in order or precedence:
 * - not
 * - and
 * - or
 * <p>
 * They work pretty much as you would expect them to. All other tokens are taken
 * to be predicate names. If the predicate does not require any parameters then the
 * brackets can be omitted, otherwise they are mandatory.
 * <p>
 * If a predicate is only being passed a single parameter then the parameter name can be omitted.
 * Strings can be enclosed in optional double or single quotations marks, and quotation marks can be escaped using
 * <code>\"</code>.
 * <p>
 * Array types are represented via a comma separated list of values enclosed in curly braces.
 * <p>
 * TODO: should we use antlr (or whatever) here? I don't really want an extra dependency just for this...
 *
 * @author Stuart Douglas
 */
public class PredicateParser {

    public static final Predicate parse(String string, final ClassLoader classLoader) {
        final Map<String, PredicateBuilder> builders = loadBuilders(classLoader);
        final ExchangeAttributeParser attributeParser = ExchangeAttributes.parser(classLoader);
        Deque<Token> tokens = PredicateTokeniser.tokenize(string);
        return parse(string, tokens, builders, attributeParser);
    }

    public static final Predicate parse(String string, Deque<Token> tokens, final ClassLoader classLoader) {
        final Map<String, PredicateBuilder> builders = loadBuilders(classLoader);
        final ExchangeAttributeParser attributeParser = ExchangeAttributes.parser(classLoader);
        return parse(string, new ArrayDeque<>(tokens), builders, attributeParser);
    }

    private static Map<String, PredicateBuilder> loadBuilders(final ClassLoader classLoader) {
        ServiceLoader<PredicateBuilder> loader = ServiceLoader.load(PredicateBuilder.class, classLoader);
        final Map<String, PredicateBuilder> ret = new HashMap<>();
        for (PredicateBuilder builder : loader) {
            if (ret.containsKey(builder.name())) {
                if (ret.get(builder.name()).getClass() != builder.getClass()) {
                    throw UndertowMessages.MESSAGES.moreThanOnePredicateWithName(builder.name(), builder.getClass(), ret.get(builder.name()).getClass());
                }
            } else {
                ret.put(builder.name(), builder);
            }
        }
        return ret;
    }

    static Predicate parse(final String string, Deque<Token> tokens, final Map<String, PredicateBuilder> builders, final ExchangeAttributeParser attributeParser) {

        //shunting yard algorithm
        //gets rid or parentheses and fixes up operator ordering
        Deque<String> operatorStack = new ArrayDeque<>();

        //the output, consisting of predicate nodes and string representations of operators
        //it is a bit yuck mixing up the types, but whatever
        Deque<Object> output = new ArrayDeque<>();

        while (!tokens.isEmpty()) {
            Token token = tokens.poll();
            if (isSpecialChar(token.getToken())) {
                if (token.getToken().equals("(")) {
                    operatorStack.push("(");
                } else if (token.getToken().equals(")")) {
                    for (; ; ) {
                        String op = operatorStack.pop();
                        if (op == null) {
                            throw PredicateTokeniser.error(string, token.getPosition(), "Unexpected end of input");
                        } else if (op.equals("(")) {
                            break;
                        } else {
                            output.push(op);
                        }
                    }
                } else {
                    throw PredicateTokeniser.error(string, token.getPosition(), "Mismatched parenthesis");
                }
            } else {
                if (isOperator(token.getToken())) {
                    int prec = precedence(token.getToken());
                    String top = operatorStack.peek();
                    while (top != null) {
                        if (top.equals("(")) {
                            break;
                        }
                        int exitingPrec = precedence(top);
                        if (prec <= exitingPrec) {
                            output.push(operatorStack.pop());
                        } else {
                            break;
                        }
                        top = operatorStack.peek();
                    }
                    operatorStack.push(token.getToken());
                } else {
                    output.push(parsePredicate(string, token, tokens, builders, attributeParser));
                }
            }
        }
        while (!operatorStack.isEmpty()) {
            String op = operatorStack.pop();
            if (op.equals(")")) {
                throw PredicateTokeniser.error(string, string.length(), "Mismatched parenthesis");
            }
            output.push(op);
        }
        //now we have our tokens
        Predicate predicate = collapseOutput(output.pop(), output).resolve();
        if (!output.isEmpty()) {
            throw PredicateTokeniser.error(string, 0, "Invalid expression");
        }
        return predicate;

    }

    private static Node collapseOutput(final Object token, final Deque<Object> tokens) {
        if (token instanceof Node) {
            return (Node) token;
        } else if (token.equals("and")) {
            Node n1 = collapseOutput(tokens.pop(), tokens);
            Node n2 = collapseOutput(tokens.pop(), tokens);
            return new AndNode(n2, n1);
        } else if (token.equals("or")) {
            Node n1 = collapseOutput(tokens.pop(), tokens);
            Node n2 = collapseOutput(tokens.pop(), tokens);
            return new OrNode(n2, n1);
        } else if (token.equals("not")) {
            Node n1 = collapseOutput(tokens.pop(), tokens);
            return new NotNode(n1);
        } else {
            throw new IllegalStateException("Invalid operator " + token);
        }

    }

    private static Object parsePredicate(final String string, final Token token, final Deque<Token> tokens, final Map<String, PredicateBuilder> builders, final ExchangeAttributeParser attributeParser) {
        if (token.getToken().equals("true")) {
            return new PredicateNode(TruePredicate.instance());
        } else if (token.getToken().equals("false")) {
            return new PredicateNode(FalsePredicate.instance());
        } else {
            PredicateBuilder builder = builders.get(token.getToken());
            if (builder == null) {

                throw PredicateTokeniser.error(string, token.getPosition(), "no predicate named " + token.getToken() + " known predicates: " + builders.keySet());
            }
            Token next = tokens.peek();
            String endChar = ")";
            if (next.getToken().equals("[") || next.getToken().equals("(")) {
                if(next.getToken().equals("[")) {
                    endChar = "]";
                    UndertowLogger.ROOT_LOGGER.oldStylePredicateSyntax(string);
                }
                final Map<String, Object> values = new HashMap<>();

                tokens.poll();
                next = tokens.poll();
                if (next == null) {
                    throw PredicateTokeniser.error(string, string.length(), "Unexpected end of input");
                }
                if (next.getToken().equals("{")) {
                    return handleSingleArrayValue(string, builder, tokens, next, attributeParser, endChar);
                }
                while (!next.getToken().equals(endChar)) {
                    Token equals = tokens.poll();
                    if(equals == null) {
                        throw PredicateTokeniser.error(string, string.length(), "Unexpected end of input");
                    }
                    if (!equals.getToken().equals("=")) {
                        if (equals.getToken().equals(endChar) && values.isEmpty()) {
                            //single value case
                            return handleSingleValue(string, builder, next, attributeParser);
                        } else if (equals.getToken().equals(",")) {
                            tokens.push(equals);
                            tokens.push(next);
                            return handleSingleVarArgsValue(string, builder, tokens, next, attributeParser, endChar);
                        }
                        throw PredicateTokeniser.error(string, equals.getPosition(), "Unexpected token");
                    }
                    Token value = tokens.poll();
                    if (value == null) {
                        throw PredicateTokeniser.error(string, string.length(), "Unexpected end of input");
                    }
                    if (value.getToken().equals("{")) {
                        values.put(next.getToken(), readArrayType(string, tokens, next, builder, attributeParser, "}"));
                    } else {
                        if (isOperator(value.getToken()) || isSpecialChar(value.getToken())) {
                            throw PredicateTokeniser.error(string, value.getPosition(), "Unexpected token");
                        }

                        Class<?> type = builder.parameters().get(next.getToken());
                        if (type == null) {
                            throw PredicateTokeniser.error(string, next.getPosition(), "Unexpected parameter " + next.getToken());
                        }
                        values.put(next.getToken(), coerceToType(string, value, type, attributeParser));
                    }

                    next = tokens.poll();
                    if (next == null) {
                        throw PredicateTokeniser.error(string, string.length(), "Unexpected end of input");
                    }
                    if (!next.getToken().equals(endChar)) {
                        if (!next.getToken().equals(",")) {
                            throw PredicateTokeniser.error(string, string.length(), "Expecting , or " + endChar);
                        }
                        next = tokens.poll();
                        if (next == null) {
                            throw PredicateTokeniser.error(string, string.length(), "Unexpected end of input");
                        }
                    }
                }
                checkParameters(string, next.getPosition(), values, builder);
                return new BuilderNode(builder, values);

            } else {
                if (isSpecialChar(next.getToken())) {
                    throw PredicateTokeniser.error(string, next.getPosition(), "Unexpected character");
                }
                return new BuilderNode(builder);
            }
        }
    }

    private static Node handleSingleArrayValue(final String string, final PredicateBuilder builder, final Deque<Token> tokens, final Token token, final ExchangeAttributeParser attributeParser, String endChar) {
        String sv = builder.defaultParameter();
        if (sv == null) {
            throw PredicateTokeniser.error(string, token.getPosition(), "default parameter not supported");
        }
        Object array = readArrayType(string, tokens, new Token(sv, token.getPosition()), builder, attributeParser, "}");
        Token close = tokens.poll();
        if (!close.getToken().equals(endChar)) {
            throw PredicateTokeniser.error(string, close.getPosition(), "expected " + endChar);
        }
        return new BuilderNode(builder, Collections.singletonMap(sv, array));
    }

    private static Node handleSingleVarArgsValue(final String string, final PredicateBuilder builder, final Deque<Token> tokens, final Token token, final ExchangeAttributeParser attributeParser, String endChar) {
        String sv = builder.defaultParameter();
        if (sv == null) {
            throw PredicateTokeniser.error(string, token.getPosition(), "default parameter not supported");
        }
        Object array = readArrayType(string, tokens, new Token(sv, token.getPosition()), builder, attributeParser, endChar);
        return new BuilderNode(builder, Collections.singletonMap(sv, array));
    }

    private static Object readArrayType(final String string, final Deque<Token> tokens, Token paramName, PredicateBuilder builder, final ExchangeAttributeParser attributeParser, String expectedEndToken) {
        Class<?> type = builder.parameters().get(paramName.getToken());
        if (type == null) {
            throw PredicateTokeniser.error(string, paramName.getPosition(), "no parameter called " + paramName.getToken());
        } else if (!type.isArray()) {
            throw PredicateTokeniser.error(string, paramName.getPosition(), "parameter is not an array type " + paramName.getToken());
        }

        Class<?> componentType = type.getComponentType();
        final List<Object> values = new ArrayList<>();
        Token token = tokens.poll();
        while (token != null) {
            Token commaOrEnd = tokens.poll();
            values.add(coerceToType(string, token, componentType, attributeParser));
            if (commaOrEnd.getToken().equals(expectedEndToken)) {
                Object array = Array.newInstance(componentType, values.size());
                for (int i = 0; i < values.size(); ++i) {
                    Array.set(array, i, values.get(i));
                }
                return array;
            } else if (!commaOrEnd.getToken().equals(",")) {
                throw PredicateTokeniser.error(string, commaOrEnd.getPosition(), "expected either , or }");
            }
            token = tokens.poll();
        }
        throw PredicateTokeniser.error(string, string.length(), "unexpected end of input in array");
    }


    private static Object handleSingleValue(final String string, final PredicateBuilder builder, final Token next, final ExchangeAttributeParser attributeParser) {
        String sv = builder.defaultParameter();
        if (sv == null) {
            throw PredicateTokeniser.error(string, next.getPosition(), "default parameter not supported");
        }
        Map<String, Object> values = Collections.singletonMap(sv, coerceToType(string, next, builder.parameters().get(sv), attributeParser));
        checkParameters(string, next.getPosition(), values, builder);
        return new BuilderNode(builder, values);
    }

    private static void checkParameters(final String string, int pos, final Map<String, Object> values, final PredicateBuilder builder) {
        final Set<String> required = new HashSet<>(builder.requiredParameters());
        for (String key : values.keySet()) {
            required.remove(key);
        }
        if (!required.isEmpty()) {
            throw PredicateTokeniser.error(string, pos, "Missing required parameters " + required);
        }
    }


    private static Object coerceToType(final String string, final Token token, final Class<?> type, final ExchangeAttributeParser attributeParser) {
        if (type.isArray()) {
            Object array = Array.newInstance(type.getComponentType(), 1);
            Array.set(array, 0, coerceToType(string, token, type.getComponentType(), attributeParser));
            return array;
        }

        if (type == String.class) {
            return token.getToken();
        } else if (type.equals(Boolean.class) || type.equals(boolean.class)) {
            return Boolean.valueOf(token.getToken());
        } else if (type.equals(Byte.class) || type.equals(byte.class)) {
            return Byte.valueOf(token.getToken());
        } else if (type.equals(Character.class) || type.equals(char.class)) {
            if (token.getToken().length() != 1) {
                throw PredicateTokeniser.error(string, token.getPosition(), "Cannot coerce " + token.getToken() + " to a Character");
            }
            return Character.valueOf(token.getToken().charAt(0));
        } else if (type.equals(Short.class) || type.equals(short.class)) {
            return Short.valueOf(token.getToken());
        } else if (type.equals(Integer.class) || type.equals(int.class)) {
            return Integer.valueOf(token.getToken());
        } else if (type.equals(Long.class) || type.equals(long.class)) {
            return Long.valueOf(token.getToken());
        } else if (type.equals(Float.class) || type.equals(float.class)) {
            return Float.valueOf(token.getToken());
        } else if (type.equals(Double.class) || type.equals(double.class)) {
            return Double.valueOf(token.getToken());
        } else if (type.equals(ExchangeAttribute.class)) {
            return attributeParser.parse(token.getToken());
        }

        return token.getToken();
    }

    private static int precedence(String operator) {
        if (operator.equals("not")) {
            return 3;
        } else if (operator.equals("and")) {
            return 2;
        } else if (operator.equals("or")) {
            return 1;
        }
        throw new IllegalStateException();
    }


    private static boolean isOperator(final String op) {
        return op.equals("and") || op.equals("or") || op.equals("not");
    }

    private static boolean isSpecialChar(String token) {
        if (token.length() != 1) {
            return false;
        }
        char c = token.charAt(0);
        switch (c) {
            case '(':
            case ')':
            case ',':
            case '=':
            case '{':
            case '}':
            case '[':
            case ']':
                return true;
            default:
                return false;
        }
    }

    private interface Node {

        Predicate resolve();
    }

    private static class AndNode implements Node {

        private final Node node1, node2;

        private AndNode(final Node node1, final Node node2) {
            this.node1 = node1;
            this.node2 = node2;
        }

        @Override
        public Predicate resolve() {
            return new AndPredicate(node1.resolve(), node2.resolve());
        }
    }


    private static class OrNode implements Node {

        private final Node node1, node2;

        private OrNode(final Node node1, final Node node2) {
            this.node1 = node1;
            this.node2 = node2;
        }

        @Override
        public Predicate resolve() {
            return new OrPredicate(node1.resolve(), node2.resolve());
        }
    }


    private static class NotNode implements Node {

        private final Node node;

        private NotNode(final Node node) {
            this.node = node;
        }

        @Override
        public Predicate resolve() {
            return new NotPredicate(node.resolve());
        }
    }

    private static class BuilderNode implements Node {

        private final PredicateBuilder builder;
        private final Map<String, Object> parameters;

        private BuilderNode(final PredicateBuilder builder) {
            this.builder = builder;
            this.parameters = Collections.emptyMap();
        }

        private BuilderNode(final PredicateBuilder builder, final Map<String, Object> parameters) {
            this.builder = builder;
            this.parameters = parameters;
        }

        @Override
        public Predicate resolve() {
            return builder.build(parameters);
        }
    }

    private static class PredicateNode implements Node {

        private final Predicate predicate;

        private PredicateNode(final Predicate predicate) {
            this.predicate = predicate;
        }

        @Override
        public Predicate resolve() {
            return predicate;
        }
    }

}


File: core/src/main/java/io/undertow/predicate/PredicatesHandler.java
/*
 * JBoss, Home of Professional Open Source.
 * Copyright 2014 Red Hat, Inc., and individual contributors
 * as indicated by the @author tags.
 *
 * Licensed under the Apache License, Version 2.0 (the "License");
 * you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at
 *
 *     http://www.apache.org/licenses/LICENSE-2.0
 *
 *  Unless required by applicable law or agreed to in writing, software
 *  distributed under the License is distributed on an "AS IS" BASIS,
 *  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 *  See the License for the specific language governing permissions and
 *  limitations under the License.
 */

package io.undertow.predicate;

import io.undertow.server.HandlerWrapper;
import io.undertow.server.HttpHandler;
import io.undertow.server.HttpServerExchange;
import io.undertow.server.handlers.builder.HandlerBuilder;
import io.undertow.server.handlers.builder.PredicatedHandler;
import io.undertow.util.AttachmentKey;

import java.util.Collections;
import java.util.Map;
import java.util.Set;
import java.util.TreeMap;

/**
 * Handler that can deal with a large number of predicates. chaining together a large number of {@link io.undertow.predicate.PredicatesHandler.Holder}
 * instances will make the stack grow to large, so this class is used that can deal with a large number of predicates.
 *
 * @author Stuart Douglas
 */
public class PredicatesHandler implements HttpHandler {

    /**
     * static done marker. If this is attached to the exchange it will drop out immediately.
     */
    public static final AttachmentKey<Boolean> DONE = AttachmentKey.create(Boolean.class);

    private volatile Holder[] handlers = new Holder[0];
    private volatile HttpHandler next;
    private final boolean outerHandler;

    //non-static, so multiple handlers can co-exist
    private final AttachmentKey<Integer> CURRENT_POSITION = AttachmentKey.create(Integer.class);

    public PredicatesHandler(HttpHandler next) {
        this.next = next;
        this.outerHandler = true;
    }
    public PredicatesHandler(HttpHandler next, boolean outerHandler) {
        this.next = next;
        this.outerHandler = outerHandler;
    }

    @Override
    public void handleRequest(HttpServerExchange exchange) throws Exception {
        final int length = handlers.length;
        Integer current = exchange.getAttachment(CURRENT_POSITION);
        int pos;
        if (current == null) {
            if(outerHandler) {
                exchange.removeAttachment(DONE);
            }
            pos = 0;
            exchange.putAttachment(Predicate.PREDICATE_CONTEXT, new TreeMap<String, Object>());
        } else {
            //if it has been marked as done
            if(exchange.getAttachment(DONE) != null) {
                exchange.removeAttachment(CURRENT_POSITION);
                next.handleRequest(exchange);
                return;
            }
            pos = current;
        }
        for (; pos < length; ++pos) {
            final Holder handler = handlers[pos];
            if (handler.predicate.resolve(exchange)) {
                exchange.putAttachment(CURRENT_POSITION, pos + 1);
                handler.handler.handleRequest(exchange);
                return;
            }
        }
        next.handleRequest(exchange);

    }

    /**
     * Adds a new predicated handler.
     * <p>
     *
     * @param predicate
     * @param handlerWrapper
     */
    public PredicatesHandler addPredicatedHandler(final Predicate predicate, final HandlerWrapper handlerWrapper) {
        Holder[] old = handlers;
        Holder[] handlers = new Holder[old.length + 1];
        System.arraycopy(old, 0, handlers, 0, old.length);
        handlers[old.length] = new Holder(predicate, handlerWrapper.wrap(this));
        this.handlers = handlers;
        return this;
    }

    public PredicatesHandler addPredicatedHandler(final PredicatedHandler handler) {
        return addPredicatedHandler(handler.getPredicate(), handler.getHandler());
    }

    public void setNext(HttpHandler next) {
        this.next = next;
    }

    public HttpHandler getNext() {
        return next;
    }

    private static final class Holder {
        final Predicate predicate;
        final HttpHandler handler;

        private Holder(Predicate predicate, HttpHandler handler) {
            this.predicate = predicate;
            this.handler = handler;
        }
    }

    public static final class DoneHandlerBuilder implements HandlerBuilder {

        @Override
        public String name() {
            return "done";
        }

        @Override
        public Map<String, Class<?>> parameters() {
            return Collections.emptyMap();
        }

        @Override
        public Set<String> requiredParameters() {
            return Collections.emptySet();
        }

        @Override
        public String defaultParameter() {
            return null;
        }

        @Override
        public HandlerWrapper build(Map<String, Object> config) {
            return new HandlerWrapper() {
                @Override
                public HttpHandler wrap(final HttpHandler handler) {
                    return new HttpHandler() {
                        @Override
                        public void handleRequest(HttpServerExchange exchange) throws Exception {
                            exchange.putAttachment(DONE, true);
                            handler.handleRequest(exchange);
                        }
                    };
                }
            };
        }
    }
}


File: core/src/main/java/io/undertow/server/handlers/AllowedMethodsHandler.java
/*
 * JBoss, Home of Professional Open Source.
 * Copyright 2014 Red Hat, Inc., and individual contributors
 * as indicated by the @author tags.
 *
 * Licensed under the Apache License, Version 2.0 (the "License");
 * you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at
 *
 *     http://www.apache.org/licenses/LICENSE-2.0
 *
 *  Unless required by applicable law or agreed to in writing, software
 *  distributed under the License is distributed on an "AS IS" BASIS,
 *  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 *  See the License for the specific language governing permissions and
 *  limitations under the License.
 */

package io.undertow.server.handlers;

import java.util.Arrays;
import java.util.Collections;
import java.util.HashSet;
import java.util.Map;
import java.util.Set;

import io.undertow.server.HandlerWrapper;
import io.undertow.server.HttpHandler;
import io.undertow.server.HttpServerExchange;
import io.undertow.server.handlers.builder.HandlerBuilder;
import io.undertow.util.HttpString;
import io.undertow.util.StatusCodes;

/**
 * Handler that whitelists certain HTTP methods. Only requests with a method in
 * the allowed methods set will be allowed to continue.
 *
 * @author Stuart Douglas
 */
public class AllowedMethodsHandler implements HttpHandler {

    private final Set<HttpString> allowedMethods;
    private final HttpHandler next;

    public AllowedMethodsHandler(final HttpHandler next, final Set<HttpString> allowedMethods) {
        this.allowedMethods = new HashSet<>(allowedMethods);
        this.next = next;
    }

    public AllowedMethodsHandler(final HttpHandler next, final HttpString... allowedMethods) {
        this.allowedMethods = new HashSet<>(Arrays.asList(allowedMethods));
        this.next = next;
    }

    @Override
    public void handleRequest(final HttpServerExchange exchange) throws Exception {
        if (allowedMethods.contains(exchange.getRequestMethod())) {
            next.handleRequest(exchange);
        } else {
            exchange.setResponseCode(StatusCodes.METHOD_NOT_ALLOWED);
            exchange.endExchange();
        }
    }

    public static class Builder implements HandlerBuilder {

        @Override
        public String name() {
            return "allowed-methods";
        }

        @Override
        public Map<String, Class<?>> parameters() {
            return Collections.<String, Class<?>>singletonMap("methods", String[].class);
        }

        @Override
        public Set<String> requiredParameters() {
            return Collections.singleton("methods");
        }

        @Override
        public String defaultParameter() {
            return "methods";
        }

        @Override
        public HandlerWrapper build(Map<String, Object> config) {
            return new Wrapper((String[]) config.get("methods"));
        }

    }

    private static class Wrapper implements HandlerWrapper {

        private final String[] methods;

        private Wrapper(String[] methods) {
            this.methods = methods;
        }

        @Override
        public HttpHandler wrap(HttpHandler handler) {
            HttpString[] strings = new HttpString[methods.length];
                for(int i = 0; i < methods.length; ++i) {
                    strings[i] = new HttpString(methods[i]);
                }

            return new AllowedMethodsHandler(handler, strings);
        }
    }
}


File: core/src/main/java/io/undertow/server/handlers/SetHeaderHandler.java
/*
 * JBoss, Home of Professional Open Source.
 * Copyright 2014 Red Hat, Inc., and individual contributors
 * as indicated by the @author tags.
 *
 * Licensed under the Apache License, Version 2.0 (the "License");
 * you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at
 *
 *     http://www.apache.org/licenses/LICENSE-2.0
 *
 *  Unless required by applicable law or agreed to in writing, software
 *  distributed under the License is distributed on an "AS IS" BASIS,
 *  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 *  See the License for the specific language governing permissions and
 *  limitations under the License.
 */

package io.undertow.server.handlers;

import io.undertow.UndertowMessages;
import io.undertow.attribute.ExchangeAttribute;
import io.undertow.attribute.ExchangeAttributes;
import io.undertow.server.HandlerWrapper;
import io.undertow.server.HttpHandler;
import io.undertow.server.HttpServerExchange;
import io.undertow.server.handlers.builder.HandlerBuilder;
import io.undertow.util.HttpString;

import java.util.HashMap;
import java.util.HashSet;
import java.util.Map;
import java.util.Set;

/**
 * Set a fixed response header.
 *
 * @author Stuart Douglas
 */
public class SetHeaderHandler implements HttpHandler {

    private final HttpString header;
    private final ExchangeAttribute value;
    private final HttpHandler next;

    public SetHeaderHandler(final String header, final String value) {
        if(value == null) {
            throw UndertowMessages.MESSAGES.argumentCannotBeNull("value");
        }
        if(header == null) {
            throw UndertowMessages.MESSAGES.argumentCannotBeNull("header");
        }
        this.next = ResponseCodeHandler.HANDLE_404;
        this.value = ExchangeAttributes.constant(value);
        this.header = new HttpString(header);
    }

    public SetHeaderHandler(final HttpHandler next, final String header, final ExchangeAttribute value) {
        if(value == null) {
            throw UndertowMessages.MESSAGES.argumentCannotBeNull("value");
        }
        if(header == null) {
            throw UndertowMessages.MESSAGES.argumentCannotBeNull("header");
        }
        if(next == null) {
            throw UndertowMessages.MESSAGES.argumentCannotBeNull("next");
        }
        this.next = next;
        this.value = value;
        this.header = new HttpString(header);
    }

    public SetHeaderHandler(final HttpHandler next, final String header, final String value) {
        if(value == null) {
            throw UndertowMessages.MESSAGES.argumentCannotBeNull("value");
        }
        if(header == null) {
            throw UndertowMessages.MESSAGES.argumentCannotBeNull("header");
        }
        if(next == null) {
            throw UndertowMessages.MESSAGES.argumentCannotBeNull("next");
        }
        this.next = next;
        this.value = ExchangeAttributes.constant(value);
        this.header = new HttpString(header);
    }
    @Override
    public void handleRequest(final HttpServerExchange exchange) throws Exception {
        exchange.getResponseHeaders().put(header, value.readAttribute(exchange));
        next.handleRequest(exchange);
    }


    public static class Builder implements HandlerBuilder {
        @Override
        public String name() {
            return "header";
        }

        @Override
        public Map<String, Class<?>> parameters() {
            Map<String, Class<?>> parameters = new HashMap<>();
            parameters.put("header", String.class);
            parameters.put("value", ExchangeAttribute.class);

            return parameters;
        }

        @Override
        public Set<String> requiredParameters() {
            final Set<String> req = new HashSet<>();
            req.add("value");
            req.add("header");
            return req;
        }

        @Override
        public String defaultParameter() {
            return null;
        }

        @Override
        public HandlerWrapper build(final Map<String, Object> config) {
            final ExchangeAttribute value = (ExchangeAttribute) config.get("value");
            final String header = (String) config.get("header");

            return new HandlerWrapper() {
                @Override
                public HttpHandler wrap(HttpHandler handler) {
                    return new SetHeaderHandler(handler, header, value);
                }
            };
        }
    }
}


File: core/src/main/java/io/undertow/server/handlers/builder/HandlerParser.java
/*
 * JBoss, Home of Professional Open Source.
 * Copyright 2014 Red Hat, Inc., and individual contributors
 * as indicated by the @author tags.
 *
 * Licensed under the Apache License, Version 2.0 (the "License");
 * you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at
 *
 *     http://www.apache.org/licenses/LICENSE-2.0
 *
 *  Unless required by applicable law or agreed to in writing, software
 *  distributed under the License is distributed on an "AS IS" BASIS,
 *  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 *  See the License for the specific language governing permissions and
 *  limitations under the License.
 */

package io.undertow.server.handlers.builder;

import io.undertow.UndertowLogger;
import io.undertow.UndertowMessages;
import io.undertow.attribute.ExchangeAttribute;
import io.undertow.attribute.ExchangeAttributeParser;
import io.undertow.attribute.ExchangeAttributes;
import io.undertow.server.HandlerWrapper;
import io.undertow.util.PredicateTokeniser;
import io.undertow.util.PredicateTokeniser.Token;

import java.lang.reflect.Array;
import java.util.ArrayDeque;
import java.util.ArrayList;
import java.util.Collections;
import java.util.Deque;
import java.util.HashMap;
import java.util.HashSet;
import java.util.List;
import java.util.Map;
import java.util.ServiceLoader;
import java.util.Set;

/**
 * Parser that can build a handler from a string representation. The underlying syntax is quite simple, and example is
 * shown below:
 * <p>
 * <code>
 * rewrite[value="/path"]
 * </code>
 * If a handler is only being passed a single parameter then the parameter name can be omitted.
 * Strings can be enclosed in optional double or single quotations marks, and quotation marks can be escaped using
 * <code>\"</code>.
 * <p>
 * Array types are represented via a comma separated list of values enclosed in curly braces.
 * <p>
 *
 * @author Stuart Douglas
 */
public class HandlerParser {


    public static final HandlerWrapper parse(String string, final ClassLoader classLoader) {
        final Map<String, HandlerBuilder> builders = loadBuilders(classLoader);
        final ExchangeAttributeParser attributeParser = ExchangeAttributes.parser(classLoader);
        Deque<Token> tokens = tokenize(string);
        return parse(string, tokens, builders, attributeParser);
    }


    public static final HandlerWrapper parse(String string, Deque<Token> tokens, final ClassLoader classLoader) {
        final Map<String, HandlerBuilder> builders = loadBuilders(classLoader);
        final ExchangeAttributeParser attributeParser = ExchangeAttributes.parser(classLoader);
        return parse(string, new ArrayDeque<Token>(tokens), builders, attributeParser);
    }

    private static Map<String, HandlerBuilder> loadBuilders(final ClassLoader classLoader) {
        ServiceLoader<HandlerBuilder> loader = ServiceLoader.load(HandlerBuilder.class, classLoader);
        final Map<String, HandlerBuilder> ret = new HashMap<>();
        for (HandlerBuilder builder : loader) {
            if (ret.containsKey(builder.name())) {
                if (ret.get(builder.name()).getClass() != builder.getClass()) {
                    throw UndertowMessages.MESSAGES.moreThanOneHandlerWithName(builder.name(), builder.getClass(), ret.get(builder.name()).getClass());
                }
            } else {
                ret.put(builder.name(), builder);
            }
        }
        return ret;
    }

    static HandlerWrapper parse(final String string, final Map<String, HandlerBuilder> builders, final ExchangeAttributeParser attributeParser) {

        //shunting yard algorithm
        //gets rid or parentheses and fixes up operator ordering
        Deque<Token> tokens = tokenize(string);
        return parseBuilder(string, tokens.pop(), tokens, builders, attributeParser);

    }

    static HandlerWrapper parse(final String string, Deque<Token> tokens, final Map<String, HandlerBuilder> builders, final ExchangeAttributeParser attributeParser) {
        return parseBuilder(string, tokens.pop(), tokens, builders, attributeParser);
    }

    private static HandlerWrapper parseBuilder(final String string, final Token token, final Deque<Token> tokens, final Map<String, HandlerBuilder> builders, final ExchangeAttributeParser attributeParser) {
        HandlerBuilder builder = builders.get(token.getToken());
        if (builder == null) {
            throw PredicateTokeniser.error(string, token.getPosition(), "no handler named " + token.getToken());
        }
        if(!tokens.isEmpty()) {
            Token last = tokens.isEmpty() ? token : tokens.getLast();
            Token next = tokens.peek();
            String endChar = ")";
            if (next.getToken().equals("(") || next.getToken().equals("[")) {
                if (next.getToken().equals("[")) {
                    UndertowLogger.ROOT_LOGGER.oldStylePredicateSyntax(string);
                    endChar = "]";
                }
                final Map<String, Object> values = new HashMap<>();

                tokens.poll();
                next = tokens.poll();
                if (next == null) {
                    throw PredicateTokeniser.error(string, last.getPosition(), "Unexpected end of input");
                }
                if (next.getToken().equals("{")) {
                    return handleSingleArrayValue(string, builder, tokens, next, attributeParser, endChar, last);
                }
                while (!next.getToken().equals(endChar)) {
                    Token equals = tokens.poll();
                    if (!equals.getToken().equals("=")) {
                        if (equals.getToken().equals(endChar) && values.isEmpty()) {
                            //single value case
                            return handleSingleValue(string, builder, next, attributeParser);
                        } else if (equals.getToken().equals(",")) {
                            tokens.push(equals);
                            tokens.push(next);
                            return handleSingleVarArgsValue(string, builder, tokens, next, attributeParser, endChar, last);
                        }
                        throw PredicateTokeniser.error(string, equals.getPosition(), "Unexpected token");
                    }
                    Token value = tokens.poll();
                    if (value == null) {
                        throw PredicateTokeniser.error(string, string.length(), "Unexpected end of input");
                    }
                    if (value.getToken().equals("{")) {
                        values.put(next.getToken(), readArrayType(string, tokens, next, builder, attributeParser, "}", last));
                    } else {
                        if (isOperator(value.getToken()) || isSpecialChar(value.getToken())) {
                            throw PredicateTokeniser.error(string, value.getPosition(), "Unexpected token");
                        }

                        Class<?> type = builder.parameters().get(next.getToken());
                        if (type == null) {
                            throw PredicateTokeniser.error(string, next.getPosition(), "Unexpected parameter " + next.getToken());
                        }
                        values.put(next.getToken(), coerceToType(string, value, type, attributeParser));
                    }

                    next = tokens.poll();
                    if (next == null) {
                        throw PredicateTokeniser.error(string, last.getPosition(), "Unexpected end of input");
                    }
                    if (!next.getToken().equals(endChar)) {
                        if (!next.getToken().equals(",")) {
                            throw PredicateTokeniser.error(string, next.getPosition(), "Expecting , or " + endChar);
                        }
                        next = tokens.poll();
                        if (next == null) {
                            throw PredicateTokeniser.error(string, last.getPosition(), "Unexpected end of input");
                        }
                    }
                }
                checkParameters(string, next.getPosition(), values, builder);
                return builder.build(values);

            } else {
                throw PredicateTokeniser.error(string, next.getPosition(), "Unexpected character");
            }
        } else {
            checkParameters(string, token.getPosition(), Collections.<String,Object>emptyMap(), builder);
            return builder.build(Collections.<String,Object>emptyMap());
        }
    }

    private static HandlerWrapper handleSingleArrayValue(final String string, final HandlerBuilder builder, final Deque<Token> tokens, final Token token, final ExchangeAttributeParser attributeParser, String endChar, Token last) {
        String sv = builder.defaultParameter();
        if (sv == null) {
            throw PredicateTokeniser.error(string, token.getPosition(), "default parameter not supported");
        }
        Object array = readArrayType(string, tokens, new Token(sv, token.getPosition()), builder, attributeParser, "}", last);
        Token close = tokens.poll();
        if (!close.getToken().equals(endChar)) {
            throw PredicateTokeniser.error(string, close.getPosition(), "expected " + endChar);
        }
        return builder.build(Collections.singletonMap(sv, array));
    }

    private static HandlerWrapper handleSingleVarArgsValue(final String string, final HandlerBuilder builder, final Deque<Token> tokens, final Token token, final ExchangeAttributeParser attributeParser, String endChar, Token last) {
        String sv = builder.defaultParameter();
        if (sv == null) {
            throw PredicateTokeniser.error(string, token.getPosition(), "default parameter not supported");
        }
        Object array = readArrayType(string, tokens, new Token(sv, token.getPosition()), builder, attributeParser, endChar, last);
        return builder.build(Collections.singletonMap(sv, array));
    }

    private static Object readArrayType(final String string, final Deque<Token> tokens, Token paramName, HandlerBuilder builder, final ExchangeAttributeParser attributeParser, String expectedEndToken, Token last) {
        Class<?> type = builder.parameters().get(paramName.getToken());
        if (type == null) {
            throw PredicateTokeniser.error(string, paramName.getPosition(), "no parameter called " + paramName.getToken());
        } else if (!type.isArray()) {
            throw PredicateTokeniser.error(string, paramName.getPosition(), "parameter is not an array type " + paramName.getToken());
        }

        Class<?> componentType = type.getComponentType();
        final List<Object> values = new ArrayList<>();
        Token token = tokens.poll();
        while (token != null) {
            Token commaOrEnd = tokens.poll();
            values.add(coerceToType(string, token, componentType, attributeParser));
            if (commaOrEnd.getToken().equals(expectedEndToken)) {
                Object array = Array.newInstance(componentType, values.size());
                for (int i = 0; i < values.size(); ++i) {
                    Array.set(array, i, values.get(i));
                }
                return array;
            } else if (!commaOrEnd.getToken().equals(",")) {
                throw PredicateTokeniser.error(string, commaOrEnd.getPosition(), "expected either , or }");
            }
            token = tokens.poll();
        }
        throw PredicateTokeniser.error(string, last.getPosition(), "unexpected end of input in array");
    }


    private static HandlerWrapper handleSingleValue(final String string, final HandlerBuilder builder, final Token next, final ExchangeAttributeParser attributeParser) {
        String sv = builder.defaultParameter();
        if (sv == null) {
            throw PredicateTokeniser.error(string, next.getPosition(), "default parameter not supported");
        }
        Map<String, Object> values = Collections.singletonMap(sv, coerceToType(string, next, builder.parameters().get(sv), attributeParser));
        checkParameters(string, next.getPosition(), values, builder);
        return builder.build(values);
    }

    private static void checkParameters(final String string, int pos, final Map<String, Object> values, final HandlerBuilder builder) {
        final Set<String> required = new HashSet<>(builder.requiredParameters());
        for (String key : values.keySet()) {
            required.remove(key);
        }
        if (!required.isEmpty()) {
            throw PredicateTokeniser.error(string, pos, "Missing required parameters " + required);
        }
    }


    private static Object coerceToType(final String string, final Token token, final Class<?> type, final ExchangeAttributeParser attributeParser) {
        if (type.isArray()) {
            Object array = Array.newInstance(type.getComponentType(), 1);
            Array.set(array, 0, coerceToType(string, token, type.getComponentType(), attributeParser));
            return array;
        }

        if (type == String.class) {
            return token.getToken();
        } else if (type.equals(Boolean.class) || type.equals(boolean.class)) {
            return Boolean.valueOf(token.getToken());
        } else if (type.equals(Byte.class) || type.equals(byte.class)) {
            return Byte.valueOf(token.getToken());
        } else if (type.equals(Character.class) || type.equals(char.class)) {
            if (token.getToken().length() != 1) {
                throw PredicateTokeniser.error(string, token.getPosition(), "Cannot coerce " + token.getToken() + " to a Character");
            }
            return Character.valueOf(token.getToken().charAt(0));
        } else if (type.equals(Short.class) || type.equals(short.class)) {
            return Short.valueOf(token.getToken());
        } else if (type.equals(Integer.class) || type.equals(int.class)) {
            return Integer.valueOf(token.getToken());
        } else if (type.equals(Long.class) || type.equals(long.class)) {
            return Long.valueOf(token.getToken());
        } else if (type.equals(Float.class) || type.equals(float.class)) {
            return Float.valueOf(token.getToken());
        } else if (type.equals(Double.class) || type.equals(double.class)) {
            return Double.valueOf(token.getToken());
        } else if (type.equals(ExchangeAttribute.class)) {
            return attributeParser.parse(token.getToken());
        }

        return token.getToken();
    }

    private static int precedence(String operator) {
        if (operator.equals("not")) {
            return 3;
        } else if (operator.equals("and")) {
            return 2;
        } else if (operator.equals("or")) {
            return 1;
        }
        throw new IllegalStateException();
    }


    private static boolean isOperator(final String op) {
        return op.equals("and") || op.equals("or") || op.equals("not");
    }

    private static boolean isSpecialChar(String token) {
        if (token.length() != 1) {
            return false;
        }
        char c = token.charAt(0);
        switch (c) {
            case '(':
            case ')':
            case ',':
            case '=':
            case '{':
            case '}':
            case '[':
            case ']':
                return true;
            default:
                return false;
        }
    }

    static Deque<Token> tokenize(final String string) {
        char currentStringDelim = 0;
        boolean inVariable = false;

        int pos = 0;
        StringBuilder current = new StringBuilder();
        Deque<Token> ret = new ArrayDeque<>();
        while (pos < string.length()) {
            char c = string.charAt(pos);
            if (currentStringDelim != 0) {
                if (c == currentStringDelim && current.charAt(current.length() - 1) != '\\') {
                    ret.add(new Token(current.toString(), pos));
                    current.setLength(0);
                    currentStringDelim = 0;
                } else {
                    current.append(c);
                }
            } else {
                switch (c) {
                    case ' ':
                    case '\t': {
                        if (current.length() != 0) {
                            ret.add(new Token(current.toString(), pos));
                            current.setLength(0);
                        }
                        break;
                    }
                    case '(':
                    case ')':
                    case ',':
                    case '=':
                    case '[':
                    case ']':
                    case '{':
                    case '}': {
                        if (inVariable) {
                            current.append(c);
                            if (c == '}') {
                                inVariable = false;
                            }
                        } else {
                            if (current.length() != 0) {
                                ret.add(new Token(current.toString(), pos));
                                current.setLength(0);
                            }
                            ret.add(new Token("" + c, pos));
                        }
                        break;
                    }
                    case '"':
                    case '\'': {
                        if (current.length() != 0) {
                            throw PredicateTokeniser.error(string, pos, "Unexpected token");
                        }
                        currentStringDelim = c;
                        break;
                    }
                    case '%': {
                        current.append(c);
                        if (string.charAt(pos + 1) == '{') {
                            inVariable = true;
                        }
                        break;
                    }
                    default:
                        current.append(c);
                }
            }
            ++pos;
        }
        if (current.length() > 0) {
            ret.add(new Token(current.toString(), string.length()));
        }
        return ret;
    }
}


File: core/src/main/java/io/undertow/server/handlers/builder/PredicatedHandler.java
/*
 * JBoss, Home of Professional Open Source.
 * Copyright 2014 Red Hat, Inc., and individual contributors
 * as indicated by the @author tags.
 *
 * Licensed under the Apache License, Version 2.0 (the "License");
 * you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at
 *
 *     http://www.apache.org/licenses/LICENSE-2.0
 *
 *  Unless required by applicable law or agreed to in writing, software
 *  distributed under the License is distributed on an "AS IS" BASIS,
 *  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 *  See the License for the specific language governing permissions and
 *  limitations under the License.
 */

package io.undertow.server.handlers.builder;

import io.undertow.predicate.Predicate;
import io.undertow.server.HandlerWrapper;

/**
 * @author Stuart Douglas
 */
public class PredicatedHandler {
    private final Predicate predicate;
    private final HandlerWrapper handler;

    public PredicatedHandler(Predicate predicate, HandlerWrapper handler) {
        this.predicate = predicate;
        this.handler = handler;
    }

    public Predicate getPredicate() {
        return predicate;
    }

    public HandlerWrapper getHandler() {
        return handler;
    }
}


File: core/src/main/java/io/undertow/server/handlers/builder/PredicatedHandlersParser.java
/*
 * JBoss, Home of Professional Open Source.
 * Copyright 2014 Red Hat, Inc., and individual contributors
 * as indicated by the @author tags.
 *
 * Licensed under the Apache License, Version 2.0 (the "License");
 * you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at
 *
 *     http://www.apache.org/licenses/LICENSE-2.0
 *
 *  Unless required by applicable law or agreed to in writing, software
 *  distributed under the License is distributed on an "AS IS" BASIS,
 *  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 *  See the License for the specific language governing permissions and
 *  limitations under the License.
 */

package io.undertow.server.handlers.builder;

import io.undertow.predicate.Predicate;
import io.undertow.predicate.PredicateParser;
import io.undertow.predicate.Predicates;
import io.undertow.server.HandlerWrapper;
import io.undertow.util.ChainedHandlerWrapper;
import io.undertow.util.FileUtils;
import io.undertow.util.PredicateTokeniser;
import io.undertow.util.PredicateTokeniser.Token;

import java.io.File;
import java.io.IOException;
import java.io.InputStream;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.ArrayDeque;
import java.util.ArrayList;
import java.util.Arrays;
import java.util.Deque;
import java.util.List;

/**
 * Parser for the undertow-handlers.conf file.
 * <p>
 * This file has a line by line syntax, specifying predicate -&gt; handler. If no predicate is specified then
 * the line is assumed to just contain a handler.
 *
 * @author Stuart Douglas
 */
public class PredicatedHandlersParser {

    public static List<PredicatedHandler> parse(final File file, final ClassLoader classLoader) {
        return parse(file.toPath(), classLoader);
    }

    public static List<PredicatedHandler> parse(final Path file, final ClassLoader classLoader) {
        try {
            return parse(new String(Files.readAllBytes(file)), classLoader);
        } catch (IOException e) {
            throw new RuntimeException(e);
        }
    }

    public static List<PredicatedHandler> parse(final InputStream inputStream, final ClassLoader classLoader) {
        return parse(FileUtils.readFile(inputStream), classLoader);
    }

    public static List<PredicatedHandler> parse(final String contents, final ClassLoader classLoader) {
        String[] lines = contents.split("\\n");
        final List<PredicatedHandler> wrappers = new ArrayList<>();

        Deque<Token> tokens = PredicateTokeniser.tokenize(contents);
        while (!tokens.isEmpty()) {
            List<Deque<Token>> others = new ArrayList<>();
            Predicate predicate;
            HandlerWrapper handler;
            Deque<Token> predicatePart = new ArrayDeque<>();
            Deque<Token> current = predicatePart;
            boolean done = false;
            while (!tokens.isEmpty() && !done) {
                Token token = tokens.poll();
                if (token.getToken().equals("->")) {
                    current = new ArrayDeque<>();
                    others.add(current);
                } else if(token.getToken().equals("\n")) {
                    done = true;
                } else {
                    current.add(token);
                }
            }
            if (others.isEmpty()) {
                predicate = Predicates.truePredicate();
                handler = HandlerParser.parse(contents, predicatePart, classLoader);
            } else if (others.size() == 1) {
                predicate = PredicateParser.parse(contents, predicatePart, classLoader);
                handler = HandlerParser.parse(contents, others.get(0), classLoader);
            } else {
                predicate = PredicateParser.parse(contents, predicatePart, classLoader);
                HandlerWrapper[] handlers = new HandlerWrapper[others.size()];
                for (int i = 0; i < handlers.length; ++i) {
                    handlers[i] = HandlerParser.parse(contents, others.get(i), classLoader);
                }
                handler = new ChainedHandlerWrapper(Arrays.asList(handlers));
            }
            wrappers.add(new PredicatedHandler(predicate, handler));
        }


        return wrappers;
    }

}


File: core/src/main/java/io/undertow/util/PredicateTokeniser.java
/*
 * JBoss, Home of Professional Open Source.
 * Copyright 2014 Red Hat, Inc., and individual contributors
 * as indicated by the @author tags.
 *
 * Licensed under the Apache License, Version 2.0 (the "License");
 * you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at
 *
 *     http://www.apache.org/licenses/LICENSE-2.0
 *
 *  Unless required by applicable law or agreed to in writing, software
 *  distributed under the License is distributed on an "AS IS" BASIS,
 *  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 *  See the License for the specific language governing permissions and
 *  limitations under the License.
 */

package io.undertow.util;

import io.undertow.UndertowMessages;

import java.util.ArrayDeque;
import java.util.Deque;

/**
 * Tokeniser that is re-used by the predicate and handler parsers, as well as the combined predicated
 * handlers parser.
 *
 * @author Stuart Douglas
 */
public class PredicateTokeniser {


    public static Deque<Token> tokenize(final String string) {
        char currentStringDelim = 0;
        boolean inVariable = false;

        int pos = 0;
        StringBuilder current = new StringBuilder();
        Deque<Token> ret = new ArrayDeque<>();
        while (pos < string.length()) {
            char c = string.charAt(pos);
            if (currentStringDelim != 0) {
                if (c == currentStringDelim && current.charAt(current.length() - 1) != '\\') {
                    ret.add(new Token(current.toString(), pos));
                    current.setLength(0);
                    currentStringDelim = 0;
                } else if(c == '\n') {
                    ret.add(new Token(current.toString(), pos));
                    current.setLength(0);
                    currentStringDelim = 0;
                    ret.add(new Token("\n", pos));
                } else {
                    current.append(c);
                }
            } else {
                switch (c) {
                    case ' ':
                    case '\t': {
                        if (current.length() != 0) {
                            ret.add(new Token(current.toString(), pos));
                            current.setLength(0);
                        }
                        break;
                    }
                    case '\n': {
                        if (current.length() != 0) {
                            ret.add(new Token(current.toString(), pos));
                            current.setLength(0);
                        }
                        ret.add(new Token("\n", pos));
                        break;
                    }
                    case '(':
                    case ')':
                    case ',':
                    case '=':
                    case '[':
                    case ']':
                    case '{':
                    case '}': {
                        if (inVariable) {
                            current.append(c);
                            if (c == '}') {
                                inVariable = false;
                            }
                        } else {
                            if (current.length() != 0) {
                                ret.add(new Token(current.toString(), pos));
                                current.setLength(0);
                            }
                            ret.add(new Token("" + c, pos));
                        }
                        break;
                    }
                    case '"':
                    case '\'': {
                        if (current.length() != 0) {
                            throw error(string, pos, "Unexpected token");
                        }
                        currentStringDelim = c;
                        break;
                    }
                    case '%':
                    case '$': {
                        current.append(c);
                        if (string.charAt(pos + 1) == '{') {
                            inVariable = true;
                        }
                        break;
                    }
                    case '-':
                        if (inVariable) {
                            current.append(c);
                        } else {
                            if (pos != string.length() && string.charAt(pos + 1) == '>') {
                                pos++;
                                if (current.length() != 0) {
                                    ret.add(new Token(current.toString(), pos));
                                    current.setLength(0);
                                }
                                ret.add(new Token("->", pos));
                            } else {
                                current.append(c);
                            }
                        }
                        break;
                    default:
                        current.append(c);
                }
            }
            ++pos;
        }
        if (current.length() > 0) {
            ret.add(new Token(current.toString(), string.length()));
        }
        return ret;
    }

    public static final class Token {
        private final String token;
        private final int position;

        public Token(final String token, final int position) {
            this.token = token;
            this.position = position;
        }

        public String getToken() {
            return token;
        }

        public int getPosition() {
            return position;
        }

        @Override
        public String toString() {
            return token + " <" + position + ">";
        }
    }


    public static IllegalStateException error(final String string, int pos, String reason) {
        StringBuilder b = new StringBuilder();
        int linePos = 0;
        for(int i = 0; i < string.length(); ++i) {
            if(string.charAt(i) == '\n') {
                if(i >= pos) {
                    //truncate the string at the error line
                    break;
                } else {
                    linePos = 0;
                }
            } else if(i < pos) {
                linePos++;
            }
            b.append(string.charAt(i));
        }
        b.append('\n');
        for (int i = 0; i < linePos; ++i) {
            b.append(' ');
        }
        b.append('^');
        throw UndertowMessages.MESSAGES.errorParsingPredicateString(reason, b.toString());
    }

}


File: core/src/test/java/io/undertow/server/handlers/PredicatedHandlersTestCase.java
/*
 * JBoss, Home of Professional Open Source.
 * Copyright 2014 Red Hat, Inc., and individual contributors
 * as indicated by the @author tags.
 *
 * Licensed under the Apache License, Version 2.0 (the "License");
 * you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at
 *
 *     http://www.apache.org/licenses/LICENSE-2.0
 *
 *  Unless required by applicable law or agreed to in writing, software
 *  distributed under the License is distributed on an "AS IS" BASIS,
 *  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 *  See the License for the specific language governing permissions and
 *  limitations under the License.
 */

package io.undertow.server.handlers;

import io.undertow.Handlers;
import io.undertow.server.HttpHandler;
import io.undertow.server.HttpServerExchange;
import io.undertow.server.handlers.builder.PredicatedHandlersParser;
import io.undertow.testutils.DefaultServer;
import io.undertow.testutils.HttpClientUtils;
import io.undertow.testutils.TestHttpClient;
import io.undertow.util.StatusCodes;
import org.apache.http.HttpResponse;
import org.apache.http.client.methods.HttpGet;
import org.junit.Assert;
import org.junit.Test;
import org.junit.runner.RunWith;

import java.io.IOException;

/**
 * @author Stuart Douglas
 */
@RunWith(DefaultServer.class)
public class PredicatedHandlersTestCase {

    @Test
    public void testRewrite() throws IOException {
        DefaultServer.setRootHandler(
                Handlers.predicates(

                        PredicatedHandlersParser.parse(
                                        "path(/skipallrules) -> done\n" +
                                        "method(GET) -> set(attribute='%{o,type}', value=get)\n" +
                                        "regex('(.*).css') -> rewrite['${1}.xcss'] -> set(attribute='%{o,chained}', value=true)\n" +
                                        "regex('(.*).redirect$') -> redirect['${1}.redirected']\n" +
                                        "set[attribute='%{o,someHeader}', value=always]\n" +
                                        "path-template('/foo/{bar}/{f}') -> set[attribute='%{o,template}', value='${bar}']\n" +
                                        "path-template('/bar->foo') -> redirect(/)", getClass().getClassLoader()), new HttpHandler() {
                    @Override
                    public void handleRequest(HttpServerExchange exchange) throws Exception {
                        exchange.getResponseSender().send(exchange.getRelativePath());
                    }
                }));

        TestHttpClient client = new TestHttpClient();
        try {
            HttpGet get = new HttpGet(DefaultServer.getDefaultServerURL() + "/foo/a/b");
            HttpResponse result = client.execute(get);
            Assert.assertEquals(StatusCodes.OK, result.getStatusLine().getStatusCode());
            String response = HttpClientUtils.readResponse(result);
            Assert.assertEquals("get", result.getHeaders("type")[0].getValue());
            Assert.assertEquals("always", result.getHeaders("someHeader")[0].getValue());
            Assert.assertEquals("a", result.getHeaders("template")[0].getValue());
            Assert.assertEquals("/foo/a/b", response);

            get = new HttpGet(DefaultServer.getDefaultServerURL() + "/foo/a/b.css");
            result = client.execute(get);
            Assert.assertEquals(StatusCodes.OK, result.getStatusLine().getStatusCode());
            response = HttpClientUtils.readResponse(result);
            Assert.assertEquals("get", result.getHeaders("type")[0].getValue());
            Assert.assertEquals("true", result.getHeaders("chained")[0].getValue());
            Assert.assertEquals("always", result.getHeaders("someHeader")[0].getValue());
            Assert.assertEquals("a", result.getHeaders("template")[0].getValue());
            Assert.assertEquals("/foo/a/b.xcss", response);

            get = new HttpGet(DefaultServer.getDefaultServerURL() + "/foo/a/b.redirect");
            result = client.execute(get);
            Assert.assertEquals(StatusCodes.OK, result.getStatusLine().getStatusCode());
            response = HttpClientUtils.readResponse(result);
            Assert.assertEquals("get", result.getHeaders("type")[0].getValue());
            Assert.assertEquals("always", result.getHeaders("someHeader")[0].getValue());
            Assert.assertEquals("a", result.getHeaders("template")[0].getValue());
            Assert.assertEquals("/foo/a/b.redirected", response);


            get = new HttpGet(DefaultServer.getDefaultServerURL() + "/skipallrules");
            result = client.execute(get);
            Assert.assertEquals(StatusCodes.OK, result.getStatusLine().getStatusCode());
            response = HttpClientUtils.readResponse(result);
            Assert.assertEquals(0, result.getHeaders("someHeader").length);
        } finally {
            client.getConnectionManager().shutdown();
        }
    }

}
