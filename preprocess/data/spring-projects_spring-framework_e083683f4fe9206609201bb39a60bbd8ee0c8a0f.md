Refactoring Types: ['Extract Superclass']
/springframework/web/socket/config/HandlersBeanDefinitionParser.java
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

package org.springframework.web.socket.config;

import java.util.Arrays;
import java.util.List;

import org.w3c.dom.Element;

import org.springframework.beans.factory.config.BeanDefinition;
import org.springframework.beans.factory.config.ConstructorArgumentValues;
import org.springframework.beans.factory.config.RuntimeBeanReference;
import org.springframework.beans.factory.parsing.BeanComponentDefinition;
import org.springframework.beans.factory.parsing.CompositeComponentDefinition;
import org.springframework.beans.factory.support.ManagedList;
import org.springframework.beans.factory.support.ManagedMap;
import org.springframework.beans.factory.support.RootBeanDefinition;
import org.springframework.beans.factory.xml.BeanDefinitionParser;
import org.springframework.beans.factory.xml.ParserContext;
import org.springframework.util.StringUtils;
import org.springframework.util.xml.DomUtils;
import org.springframework.web.servlet.handler.SimpleUrlHandlerMapping;
import org.springframework.web.socket.server.support.OriginHandshakeInterceptor;
import org.springframework.web.socket.server.support.WebSocketHttpRequestHandler;
import org.springframework.web.socket.sockjs.support.SockJsHttpRequestHandler;

/**
 * Parses the configuration for the {@code <websocket:handlers/>} namespace
 * element. Registers a Spring MVC {@code SimpleUrlHandlerMapping} to map HTTP
 * WebSocket handshake (or SockJS) requests to
 * {@link org.springframework.web.socket.WebSocketHandler WebSocketHandler}s.
 *
 * @author Brian Clozel
 * @author Rossen Stoyanchev
 * @since 4.0
 */
class HandlersBeanDefinitionParser implements BeanDefinitionParser {

	private static final String SOCK_JS_SCHEDULER_NAME = "SockJsScheduler";

	private static final int DEFAULT_MAPPING_ORDER = 1;


	@Override
	public BeanDefinition parse(Element element, ParserContext context) {
		Object source = context.extractSource(element);
		CompositeComponentDefinition compDefinition = new CompositeComponentDefinition(element.getTagName(), source);
		context.pushContainingComponent(compDefinition);

		String orderAttribute = element.getAttribute("order");
		int order = orderAttribute.isEmpty() ? DEFAULT_MAPPING_ORDER : Integer.valueOf(orderAttribute);

		RootBeanDefinition handlerMappingDef = new RootBeanDefinition(SimpleUrlHandlerMapping.class);
		handlerMappingDef.setSource(source);
		handlerMappingDef.setRole(BeanDefinition.ROLE_INFRASTRUCTURE);
		handlerMappingDef.getPropertyValues().add("order", order);
		String handlerMappingName = context.getReaderContext().registerWithGeneratedName(handlerMappingDef);

		RuntimeBeanReference sockJsService = WebSocketNamespaceUtils.registerSockJsService(
				element, SOCK_JS_SCHEDULER_NAME, context, source);

		HandlerMappingStrategy strategy;
		if (sockJsService != null) {
			strategy = new SockJsHandlerMappingStrategy(sockJsService);
		}
		else {
			RuntimeBeanReference handshakeHandler = WebSocketNamespaceUtils.registerHandshakeHandler(element, context, source);
			Element interceptorsElement = DomUtils.getChildElementByTagName(element, "handshake-interceptors");
			ManagedList<? super Object> interceptors = WebSocketNamespaceUtils.parseBeanSubElements(interceptorsElement, context);
			String allowedOriginsAttribute = element.getAttribute("allowed-origins");
			List<String> allowedOrigins = Arrays.asList(StringUtils.tokenizeToStringArray(allowedOriginsAttribute, ","));
			interceptors.add(new OriginHandshakeInterceptor(allowedOrigins));
			strategy = new WebSocketHandlerMappingStrategy(handshakeHandler, interceptors);
		}

		ManagedMap<String, Object> urlMap = new ManagedMap<String, Object>();
		urlMap.setSource(source);
		for (Element mappingElement : DomUtils.getChildElementsByTagName(element, "mapping")) {
			strategy.addMapping(mappingElement, urlMap, context);
		}
		handlerMappingDef.getPropertyValues().add("urlMap", urlMap);

		context.registerComponent(new BeanComponentDefinition(handlerMappingDef, handlerMappingName));
		context.popAndRegisterContainingComponent();
		return null;
	}


	private interface HandlerMappingStrategy {

		void addMapping(Element mappingElement, ManagedMap<String, Object> map, ParserContext context);

	}

	private static class WebSocketHandlerMappingStrategy implements HandlerMappingStrategy {

		private final RuntimeBeanReference handshakeHandlerReference;

		private final ManagedList<?> interceptorsList;


		private WebSocketHandlerMappingStrategy(RuntimeBeanReference handshakeHandler, ManagedList<?> interceptors) {
			this.handshakeHandlerReference = handshakeHandler;
			this.interceptorsList = interceptors;
		}

		@Override
		public void addMapping(Element element, ManagedMap<String, Object> urlMap, ParserContext context) {
			String pathAttribute = element.getAttribute("path");
			List<String> mappings = Arrays.asList(StringUtils.tokenizeToStringArray(pathAttribute, ","));
			RuntimeBeanReference handlerReference = new RuntimeBeanReference(element.getAttribute("handler"));

			ConstructorArgumentValues cavs = new ConstructorArgumentValues();
			cavs.addIndexedArgumentValue(0, handlerReference);
			if (this.handshakeHandlerReference != null) {
				cavs.addIndexedArgumentValue(1, this.handshakeHandlerReference);
			}
			RootBeanDefinition requestHandlerDef = new RootBeanDefinition(WebSocketHttpRequestHandler.class, cavs, null);
			requestHandlerDef.setSource(context.extractSource(element));
			requestHandlerDef.setRole(BeanDefinition.ROLE_INFRASTRUCTURE);
			requestHandlerDef.getPropertyValues().add("handshakeInterceptors", this.interceptorsList);
			String requestHandlerName = context.getReaderContext().registerWithGeneratedName(requestHandlerDef);
			RuntimeBeanReference requestHandlerRef = new RuntimeBeanReference(requestHandlerName);

			for (String mapping : mappings) {
				urlMap.put(mapping, requestHandlerRef);
			}
		}
	}

	private static class SockJsHandlerMappingStrategy implements HandlerMappingStrategy {

		private final RuntimeBeanReference sockJsService;


		private SockJsHandlerMappingStrategy(RuntimeBeanReference sockJsService) {
			this.sockJsService = sockJsService;
		}

		@Override
		public void addMapping(Element element, ManagedMap<String, Object> urlMap, ParserContext context) {
			String pathAttribute = element.getAttribute("path");
			List<String> mappings = Arrays.asList(StringUtils.tokenizeToStringArray(pathAttribute, ","));
			RuntimeBeanReference handlerReference = new RuntimeBeanReference(element.getAttribute("handler"));

			ConstructorArgumentValues cavs = new ConstructorArgumentValues();
			cavs.addIndexedArgumentValue(0, this.sockJsService, "SockJsService");
			cavs.addIndexedArgumentValue(1, handlerReference, "WebSocketHandler");

			RootBeanDefinition requestHandlerDef = new RootBeanDefinition(SockJsHttpRequestHandler.class, cavs, null);
			requestHandlerDef.setSource(context.extractSource(element));
			requestHandlerDef.setRole(BeanDefinition.ROLE_INFRASTRUCTURE);
			String requestHandlerName = context.getReaderContext().registerWithGeneratedName(requestHandlerDef);
			RuntimeBeanReference requestHandlerRef = new RuntimeBeanReference(requestHandlerName);

			for (String mapping : mappings) {
				String pathPattern = (mapping.endsWith("/") ? mapping + "**" : mapping + "/**");
				urlMap.put(pathPattern, requestHandlerRef);
			}
		}
	}

}


File: spring-websocket/src/main/java/org/springframework/web/socket/config/annotation/ServletWebSocketHandlerRegistry.java
/*
 * Copyright 2002-2013 the original author or authors.
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

package org.springframework.web.socket.config.annotation;

import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;

import org.springframework.scheduling.TaskScheduler;
import org.springframework.scheduling.concurrent.ThreadPoolTaskScheduler;
import org.springframework.util.MultiValueMap;
import org.springframework.web.HttpRequestHandler;
import org.springframework.web.servlet.HandlerMapping;
import org.springframework.web.servlet.handler.AbstractHandlerMapping;
import org.springframework.web.servlet.handler.SimpleUrlHandlerMapping;
import org.springframework.web.socket.WebSocketHandler;
import org.springframework.web.util.UrlPathHelper;

/**
 * A {@link WebSocketHandlerRegistry} that maps {@link WebSocketHandler}s to URLs for use
 * in a Servlet container.
 *
 * @author Rossen Stoyanchev
 * @since 4.0
 */
public class ServletWebSocketHandlerRegistry implements WebSocketHandlerRegistry {

	private final List<ServletWebSocketHandlerRegistration> registrations =
			new ArrayList<ServletWebSocketHandlerRegistration>();

	private TaskScheduler sockJsTaskScheduler;

	private int order = 1;

	private UrlPathHelper urlPathHelper;


	public ServletWebSocketHandlerRegistry(ThreadPoolTaskScheduler sockJsTaskScheduler) {
		this.sockJsTaskScheduler = sockJsTaskScheduler;
	}

	@Override
	public WebSocketHandlerRegistration addHandler(WebSocketHandler webSocketHandler, String... paths) {
		ServletWebSocketHandlerRegistration registration =
				new ServletWebSocketHandlerRegistration(this.sockJsTaskScheduler);
		registration.addHandler(webSocketHandler, paths);
		this.registrations.add(registration);
		return registration;
	}

	/**
	 * Set the order for the resulting {@link SimpleUrlHandlerMapping} relative to
	 * other handler mappings configured in Spring MVC.
	 * <p>The default value is 1.
	 */
	public void setOrder(int order) {
		this.order = order;
	}

	public int getOrder() {
		return this.order;
	}

	/**
	 * Set the UrlPathHelper to configure on the {@code SimpleUrlHandlerMapping}
	 * used to map handshake requests.
	 */
	public void setUrlPathHelper(UrlPathHelper urlPathHelper) {
		this.urlPathHelper = urlPathHelper;
	}

	public UrlPathHelper getUrlPathHelper() {
		return this.urlPathHelper;
	}

	/**
	 * Return a {@link HandlerMapping} with mapped {@link HttpRequestHandler}s.
	 */
	public AbstractHandlerMapping getHandlerMapping() {
		Map<String, Object> urlMap = new LinkedHashMap<String, Object>();
		for (ServletWebSocketHandlerRegistration registration : this.registrations) {
			MultiValueMap<HttpRequestHandler, String> mappings = registration.getMappings();
			for (HttpRequestHandler httpHandler : mappings.keySet()) {
				for (String pattern : mappings.get(httpHandler)) {
					urlMap.put(pattern, httpHandler);
				}
			}
		}
		SimpleUrlHandlerMapping hm = new SimpleUrlHandlerMapping();
		hm.setUrlMap(urlMap);
		hm.setOrder(this.order);
		if (this.urlPathHelper != null) {
			hm.setUrlPathHelper(this.urlPathHelper);
		}
		return hm;
	}

}


File: spring-websocket/src/main/java/org/springframework/web/socket/server/jetty/JettyRequestUpgradeStrategy.java
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

package org.springframework.web.socket.server.jetty;

import java.io.IOException;
import java.security.Principal;
import java.util.ArrayList;
import java.util.List;
import java.util.Map;

import javax.servlet.http.HttpServletRequest;
import javax.servlet.http.HttpServletResponse;

import org.eclipse.jetty.websocket.api.UpgradeRequest;
import org.eclipse.jetty.websocket.api.UpgradeResponse;
import org.eclipse.jetty.websocket.api.WebSocketPolicy;
import org.eclipse.jetty.websocket.api.extensions.ExtensionConfig;
import org.eclipse.jetty.websocket.server.HandshakeRFC6455;
import org.eclipse.jetty.websocket.server.WebSocketServerFactory;
import org.eclipse.jetty.websocket.servlet.ServletUpgradeRequest;
import org.eclipse.jetty.websocket.servlet.ServletUpgradeResponse;
import org.eclipse.jetty.websocket.servlet.WebSocketCreator;

import org.springframework.context.Lifecycle;
import org.springframework.core.NamedThreadLocal;
import org.springframework.http.server.ServerHttpRequest;
import org.springframework.http.server.ServerHttpResponse;
import org.springframework.http.server.ServletServerHttpRequest;
import org.springframework.http.server.ServletServerHttpResponse;
import org.springframework.util.Assert;
import org.springframework.util.CollectionUtils;
import org.springframework.web.socket.WebSocketExtension;
import org.springframework.web.socket.WebSocketHandler;
import org.springframework.web.socket.adapter.jetty.JettyWebSocketHandlerAdapter;
import org.springframework.web.socket.adapter.jetty.JettyWebSocketSession;
import org.springframework.web.socket.adapter.jetty.WebSocketToJettyExtensionConfigAdapter;
import org.springframework.web.socket.server.HandshakeFailureException;
import org.springframework.web.socket.server.RequestUpgradeStrategy;

/**
 * {@link RequestUpgradeStrategy} for use with Jetty 9. Based on Jetty's internal
 * {@code org.eclipse.jetty.websocket.server.WebSocketHandler} class.
 *
 * @author Phillip Webb
 * @author Rossen Stoyanchev
 * @since 4.0
 */
public class JettyRequestUpgradeStrategy implements RequestUpgradeStrategy, Lifecycle {

	private static final ThreadLocal<WebSocketHandlerContainer> wsContainerHolder =
			new NamedThreadLocal<WebSocketHandlerContainer>("WebSocket Handler Container");


	private final WebSocketServerFactory factory;

	private volatile List<WebSocketExtension> supportedExtensions;

	private volatile boolean running = false;


	/**
	 * Default constructor that creates {@link WebSocketServerFactory} through its default
	 * constructor thus using a default {@link WebSocketPolicy}.
	 */
	public JettyRequestUpgradeStrategy() {
		this(new WebSocketServerFactory());
	}

	/**
	 * A constructor accepting a {@link WebSocketServerFactory}. This may be useful for
	 * modifying the factory's {@link WebSocketPolicy} via
	 * {@link WebSocketServerFactory#getPolicy()}.
	 */
	public JettyRequestUpgradeStrategy(WebSocketServerFactory factory) {
		Assert.notNull(factory, "WebSocketServerFactory must not be null");
		this.factory = factory;
		this.factory.setCreator(new WebSocketCreator() {
			@Override
			public Object createWebSocket(ServletUpgradeRequest request, ServletUpgradeResponse response) {
				// Cast to avoid infinite recursion
				return createWebSocket((UpgradeRequest) request, (UpgradeResponse) response);
			}

			// For Jetty 9.0.x
			public Object createWebSocket(UpgradeRequest request, UpgradeResponse response) {
				WebSocketHandlerContainer container = wsContainerHolder.get();
				Assert.state(container != null, "Expected WebSocketHandlerContainer");
				response.setAcceptedSubProtocol(container.getSelectedProtocol());
				response.setExtensions(container.getExtensionConfigs());
				return container.getHandler();
			}
		});
	}


	@Override
	public String[] getSupportedVersions() {
		return new String[] { String.valueOf(HandshakeRFC6455.VERSION) };
	}

	@Override
	public List<WebSocketExtension> getSupportedExtensions(ServerHttpRequest request) {
		if (this.supportedExtensions == null) {
			this.supportedExtensions = getWebSocketExtensions();
		}
		return this.supportedExtensions;
	}

	private List<WebSocketExtension> getWebSocketExtensions() {
		List<WebSocketExtension> result = new ArrayList<WebSocketExtension>();
		for (String name : this.factory.getExtensionFactory().getExtensionNames()) {
			result.add(new WebSocketExtension(name));
		}
		return result;
	}

	@Override
	public boolean isRunning() {
		return this.running;
	}


	@Override
	public void start() {
		if (!isRunning()) {
			this.running = true;
			try {
				this.factory.init();
			}
			catch (Exception ex) {
				throw new IllegalStateException("Unable to initialize Jetty WebSocketServerFactory", ex);
			}
		}
	}

	@Override
	public void stop() {
		if (isRunning()) {
			this.running = false;
			this.factory.cleanup();
		}
	}

	@Override
	public void upgrade(ServerHttpRequest request, ServerHttpResponse response,
			String selectedProtocol, List<WebSocketExtension> selectedExtensions, Principal user,
			WebSocketHandler wsHandler, Map<String, Object> attributes) throws HandshakeFailureException {

		Assert.isInstanceOf(ServletServerHttpRequest.class, request);
		HttpServletRequest servletRequest = ((ServletServerHttpRequest) request).getServletRequest();

		Assert.isInstanceOf(ServletServerHttpResponse.class, response);
		HttpServletResponse servletResponse = ((ServletServerHttpResponse) response).getServletResponse();

		Assert.isTrue(this.factory.isUpgradeRequest(servletRequest, servletResponse), "Not a WebSocket handshake");

		JettyWebSocketSession session = new JettyWebSocketSession(attributes, user);
		JettyWebSocketHandlerAdapter handlerAdapter = new JettyWebSocketHandlerAdapter(wsHandler, session);

		WebSocketHandlerContainer container =
				new WebSocketHandlerContainer(handlerAdapter, selectedProtocol, selectedExtensions);

		try {
			wsContainerHolder.set(container);
			this.factory.acceptWebSocket(servletRequest, servletResponse);
		}
		catch (IOException ex) {
			throw new HandshakeFailureException(
					"Response update failed during upgrade to WebSocket, uri=" + request.getURI(), ex);
		}
		finally {
			wsContainerHolder.remove();
		}
	}


	private static class WebSocketHandlerContainer {

		private final JettyWebSocketHandlerAdapter handler;

		private final String selectedProtocol;

		private final List<ExtensionConfig> extensionConfigs;

		public WebSocketHandlerContainer(JettyWebSocketHandlerAdapter handler, String protocol, List<WebSocketExtension> extensions) {
			this.handler = handler;
			this.selectedProtocol = protocol;
			if (CollectionUtils.isEmpty(extensions)) {
				this.extensionConfigs = null;
			}
			else {
				this.extensionConfigs = new ArrayList<ExtensionConfig>();
				for (WebSocketExtension e : extensions) {
					this.extensionConfigs.add(new WebSocketToJettyExtensionConfigAdapter(e));
				}
			}
		}

		public JettyWebSocketHandlerAdapter getHandler() {
			return this.handler;
		}

		public String getSelectedProtocol() {
			return this.selectedProtocol;
		}

		public List<ExtensionConfig> getExtensionConfigs() {
			return this.extensionConfigs;
		}
	}

}


File: spring-websocket/src/main/java/org/springframework/web/socket/server/support/DefaultHandshakeHandler.java
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

package org.springframework.web.socket.server.support;

import java.io.IOException;
import java.nio.charset.Charset;
import java.security.Principal;
import java.util.ArrayList;
import java.util.Arrays;
import java.util.Collections;
import java.util.List;
import java.util.Map;

import org.apache.commons.logging.Log;
import org.apache.commons.logging.LogFactory;

import org.springframework.context.Lifecycle;
import org.springframework.http.HttpMethod;
import org.springframework.http.HttpStatus;
import org.springframework.http.server.ServerHttpRequest;
import org.springframework.http.server.ServerHttpResponse;
import org.springframework.util.Assert;
import org.springframework.util.ClassUtils;
import org.springframework.util.StringUtils;
import org.springframework.web.socket.SubProtocolCapable;
import org.springframework.web.socket.WebSocketExtension;
import org.springframework.web.socket.WebSocketHandler;
import org.springframework.web.socket.WebSocketHttpHeaders;
import org.springframework.web.socket.handler.WebSocketHandlerDecorator;
import org.springframework.web.socket.server.HandshakeFailureException;
import org.springframework.web.socket.server.HandshakeHandler;
import org.springframework.web.socket.server.RequestUpgradeStrategy;

/**
 * A default {@link org.springframework.web.socket.server.HandshakeHandler} implementation.
 * Performs initial validation of the WebSocket handshake request -- possibly rejecting it
 * through the appropriate HTTP status code -- while also allowing sub-classes to override
 * various parts of the negotiation process (e.g. origin validation, sub-protocol negotiation,
 * extensions negotiation, etc).
 *
 * <p>If the negotiation succeeds, the actual upgrade is delegated to a server-specific
 * {@link org.springframework.web.socket.server.RequestUpgradeStrategy}, which will update
 * the response as necessary and initialize the WebSocket. Currently supported servers are
 * Tomcat 7 and 8, Jetty 9, and GlassFish 4.
 *
 * @author Rossen Stoyanchev
 * @since 4.0
 */
public class DefaultHandshakeHandler implements HandshakeHandler, Lifecycle {

	private static final Charset UTF8_CHARSET = Charset.forName("UTF-8");


	private static final boolean jettyWsPresent = ClassUtils.isPresent(
			"org.eclipse.jetty.websocket.server.WebSocketServerFactory", DefaultHandshakeHandler.class.getClassLoader());

	private static final boolean tomcatWsPresent = ClassUtils.isPresent(
			"org.apache.tomcat.websocket.server.WsHttpUpgradeHandler", DefaultHandshakeHandler.class.getClassLoader());

	private static final boolean undertowWsPresent = ClassUtils.isPresent(
			"io.undertow.websockets.jsr.ServerWebSocketContainer", DefaultHandshakeHandler.class.getClassLoader());

	private static final boolean glassFishWsPresent = ClassUtils.isPresent(
			"org.glassfish.tyrus.servlet.TyrusHttpUpgradeHandler", DefaultHandshakeHandler.class.getClassLoader());

	private static final boolean webLogicWsPresent = ClassUtils.isPresent(
			"weblogic.websocket.tyrus.TyrusServletWriter", DefaultHandshakeHandler.class.getClassLoader());


	protected final Log logger = LogFactory.getLog(getClass());

	private final RequestUpgradeStrategy requestUpgradeStrategy;

	private final List<String> supportedProtocols = new ArrayList<String>();

	private volatile boolean running = false;


	/**
	 * Default constructor that autodetects and instantiates a
	 * {@link RequestUpgradeStrategy} suitable for the runtime container.
	 * @throws IllegalStateException if no {@link RequestUpgradeStrategy} can be found.
	 */
	public DefaultHandshakeHandler() {
		this(initRequestUpgradeStrategy());
	}

	/**
	 * A constructor that accepts a runtime-specific {@link RequestUpgradeStrategy}.
	 * @param requestUpgradeStrategy the upgrade strategy to use
	 */
	public DefaultHandshakeHandler(RequestUpgradeStrategy requestUpgradeStrategy) {
		Assert.notNull(requestUpgradeStrategy, "RequestUpgradeStrategy must not be null");
		this.requestUpgradeStrategy = requestUpgradeStrategy;
	}


	private static RequestUpgradeStrategy initRequestUpgradeStrategy() {
		String className;
		if (jettyWsPresent) {
			className = "org.springframework.web.socket.server.jetty.JettyRequestUpgradeStrategy";
		}
		else if (tomcatWsPresent) {
			className = "org.springframework.web.socket.server.standard.TomcatRequestUpgradeStrategy";
		}
		else if (undertowWsPresent) {
			className = "org.springframework.web.socket.server.standard.UndertowRequestUpgradeStrategy";
		}
		else if (glassFishWsPresent) {
			className = "org.springframework.web.socket.server.standard.GlassFishRequestUpgradeStrategy";
		}
		else if (webLogicWsPresent) {
			className = "org.springframework.web.socket.server.standard.WebLogicRequestUpgradeStrategy";
		}
		else {
			throw new IllegalStateException("No suitable default RequestUpgradeStrategy found");
		}
		try {
			Class<?> clazz = ClassUtils.forName(className, DefaultHandshakeHandler.class.getClassLoader());
			return (RequestUpgradeStrategy) clazz.newInstance();
		}
		catch (Throwable ex) {
			throw new IllegalStateException("Failed to instantiate RequestUpgradeStrategy: " + className, ex);
		}
	}


	/**
	 * Use this property to configure the list of supported sub-protocols.
	 * The first configured sub-protocol that matches a client-requested sub-protocol
	 * is accepted. If there are no matches the response will not contain a
	 * {@literal Sec-WebSocket-Protocol} header.
	 * <p>Note that if the WebSocketHandler passed in at runtime is an instance of
	 * {@link SubProtocolCapable} then there is not need to explicitly configure
	 * this property. That is certainly the case with the built-in STOMP over
	 * WebSocket support. Therefore this property should be configured explicitly
	 * only if the WebSocketHandler does not implement {@code SubProtocolCapable}.
	 */
	public void setSupportedProtocols(String... protocols) {
		this.supportedProtocols.clear();
		for (String protocol : protocols) {
			this.supportedProtocols.add(protocol.toLowerCase());
		}
	}

	/**
	 * Return the list of supported sub-protocols.
	 */
	public String[] getSupportedProtocols() {
		return this.supportedProtocols.toArray(new String[this.supportedProtocols.size()]);
	}

	@Override
	public boolean isRunning() {
		return this.running;
	}

	@Override
	public void start() {
		if (!isRunning()) {
			this.running = true;
			if (this.requestUpgradeStrategy instanceof Lifecycle) {
				((Lifecycle) this.requestUpgradeStrategy).start();
			}
		}
	}

	@Override
	public void stop() {
		if (isRunning()) {
			this.running = false;
			if (this.requestUpgradeStrategy instanceof Lifecycle) {
				((Lifecycle) this.requestUpgradeStrategy).stop();
			}
		}
	}


	@Override
	public final boolean doHandshake(ServerHttpRequest request, ServerHttpResponse response,
			WebSocketHandler wsHandler, Map<String, Object> attributes) throws HandshakeFailureException {

		WebSocketHttpHeaders headers = new WebSocketHttpHeaders(request.getHeaders());
		if (logger.isTraceEnabled()) {
			logger.trace("Processing request " + request.getURI() + " with headers=" + headers);
		}
		try {
			if (!HttpMethod.GET.equals(request.getMethod())) {
				response.setStatusCode(HttpStatus.METHOD_NOT_ALLOWED);
				response.getHeaders().setAllow(Collections.singleton(HttpMethod.GET));
				if (logger.isErrorEnabled()) {
					logger.error("Handshake failed due to unexpected HTTP method: " + request.getMethod());
				}
				return false;
			}
			if (!"WebSocket".equalsIgnoreCase(headers.getUpgrade())) {
				handleInvalidUpgradeHeader(request, response);
				return false;
			}
			if (!headers.getConnection().contains("Upgrade") && !headers.getConnection().contains("upgrade")) {
				handleInvalidConnectHeader(request, response);
				return false;
			}
			if (!isWebSocketVersionSupported(headers)) {
				handleWebSocketVersionNotSupported(request, response);
				return false;
			}
			if (!isValidOrigin(request)) {
				response.setStatusCode(HttpStatus.FORBIDDEN);
				return false;
			}
			String wsKey = headers.getSecWebSocketKey();
			if (wsKey == null) {
				if (logger.isErrorEnabled()) {
					logger.error("Missing \"Sec-WebSocket-Key\" header");
				}
				response.setStatusCode(HttpStatus.BAD_REQUEST);
				return false;
			}
		}
		catch (IOException ex) {
			throw new HandshakeFailureException(
					"Response update failed during upgrade to WebSocket, uri=" + request.getURI(), ex);
		}

		String subProtocol = selectProtocol(headers.getSecWebSocketProtocol(), wsHandler);
		List<WebSocketExtension> requested = headers.getSecWebSocketExtensions();
		List<WebSocketExtension> supported = this.requestUpgradeStrategy.getSupportedExtensions(request);
		List<WebSocketExtension> extensions = filterRequestedExtensions(request, requested, supported);
		Principal user = determineUser(request, wsHandler, attributes);

		if (logger.isTraceEnabled()) {
			logger.trace("Upgrading to WebSocket, subProtocol=" + subProtocol + ", extensions=" + extensions);
		}
		this.requestUpgradeStrategy.upgrade(request, response, subProtocol, extensions, user, wsHandler, attributes);
		return true;
	}

	protected void handleInvalidUpgradeHeader(ServerHttpRequest request, ServerHttpResponse response) throws IOException {
		if (logger.isErrorEnabled()) {
			logger.error("Handshake failed due to invalid Upgrade header: " + request.getHeaders().getUpgrade());
		}
		response.setStatusCode(HttpStatus.BAD_REQUEST);
		response.getBody().write("Can \"Upgrade\" only to \"WebSocket\".".getBytes(UTF8_CHARSET));
	}

	protected void handleInvalidConnectHeader(ServerHttpRequest request, ServerHttpResponse response) throws IOException {
		if (logger.isErrorEnabled()) {
			logger.error("Handshake failed due to invalid Connection header " + request.getHeaders().getConnection());
		}
		response.setStatusCode(HttpStatus.BAD_REQUEST);
		response.getBody().write("\"Connection\" must be \"upgrade\".".getBytes(UTF8_CHARSET));
	}

	protected boolean isWebSocketVersionSupported(WebSocketHttpHeaders httpHeaders) {
		String version = httpHeaders.getSecWebSocketVersion();
		String[] supportedVersions = getSupportedVersions();
		for (String supportedVersion : supportedVersions) {
			if (supportedVersion.trim().equals(version)) {
				return true;
			}
		}
		return false;
	}

	protected String[] getSupportedVersions() {
		return this.requestUpgradeStrategy.getSupportedVersions();
	}

	protected void handleWebSocketVersionNotSupported(ServerHttpRequest request, ServerHttpResponse response) {
		if (logger.isErrorEnabled()) {
			String version = request.getHeaders().getFirst("Sec-WebSocket-Version");
			logger.error("Handshake failed due to unsupported WebSocket version: " + version +
					". Supported versions: " + Arrays.toString(getSupportedVersions()));
		}
		response.setStatusCode(HttpStatus.UPGRADE_REQUIRED);
		response.getHeaders().put(WebSocketHttpHeaders.SEC_WEBSOCKET_VERSION,
				Arrays.asList(StringUtils.arrayToCommaDelimitedString(getSupportedVersions())));
	}

	/**
	 * Return whether the request {@code Origin} header value is valid or not.
	 * By default, all origins as considered as valid. Consider using an
	 * {@link OriginHandshakeInterceptor} for filtering origins if needed.
	 */
	protected boolean isValidOrigin(ServerHttpRequest request) {
		return true;
	}

	/**
	 * Perform the sub-protocol negotiation based on requested and supported sub-protocols.
	 * For the list of supported sub-protocols, this method first checks if the target
	 * WebSocketHandler is a {@link SubProtocolCapable} and then also checks if any
	 * sub-protocols have been explicitly configured with
	 * {@link #setSupportedProtocols(String...)}.
	 * @param requestedProtocols the requested sub-protocols
	 * @param webSocketHandler the WebSocketHandler that will be used
	 * @return the selected protocols or {@code null}
	 * @see #determineHandlerSupportedProtocols(org.springframework.web.socket.WebSocketHandler)
	 */
	protected String selectProtocol(List<String> requestedProtocols, WebSocketHandler webSocketHandler) {
		if (requestedProtocols != null) {
			List<String> handlerProtocols = determineHandlerSupportedProtocols(webSocketHandler);
			for (String protocol : requestedProtocols) {
				if (handlerProtocols.contains(protocol.toLowerCase())) {
					return protocol;
				}
				if (this.supportedProtocols.contains(protocol.toLowerCase())) {
					return protocol;
				}
			}
		}
		return null;
	}

	/**
	 * Determine the sub-protocols supported by the given WebSocketHandler by
	 * checking whether it is an instance of {@link SubProtocolCapable}.
	 * @param handler the handler to check
	 * @return a list of supported protocols, or an empty list if none available
	 */
	protected final List<String> determineHandlerSupportedProtocols(WebSocketHandler handler) {
		WebSocketHandler handlerToCheck = WebSocketHandlerDecorator.unwrap(handler);
		List<String> subProtocols = null;
		if (handlerToCheck instanceof SubProtocolCapable) {
			subProtocols = ((SubProtocolCapable) handlerToCheck).getSubProtocols();
		}
		return (subProtocols != null ? subProtocols : Collections.<String>emptyList());
	}

	/**
	 * Filter the list of requested WebSocket extensions.
	 * <p>As of 4.1 the default implementation of this method filters the list to
	 * leave only extensions that are both requested and supported.
	 * @param request the current request
	 * @param requestedExtensions the list of extensions requested by the client
	 * @param supportedExtensions the list of extensions supported by the server
	 * @return the selected extensions or an empty list
	 */
	protected List<WebSocketExtension> filterRequestedExtensions(ServerHttpRequest request,
			List<WebSocketExtension> requestedExtensions, List<WebSocketExtension> supportedExtensions) {

		List<WebSocketExtension> result = new ArrayList<WebSocketExtension>(requestedExtensions.size());
		for (WebSocketExtension extension : requestedExtensions) {
			if (supportedExtensions.contains(extension)) {
				result.add(extension);
			}
		}
		return result;
	}

	/**
	 * A method that can be used to associate a user with the WebSocket session
	 * in the process of being established. The default implementation calls
	 * {@link org.springframework.http.server.ServerHttpRequest#getPrincipal()}
	 * <p>Subclasses can provide custom logic for associating a user with a session,
	 * for example for assigning a name to anonymous users (i.e. not fully
	 * authenticated).
	 * @param request the handshake request
	 * @param wsHandler the WebSocket handler that will handle messages
	 * @param attributes handshake attributes to pass to the WebSocket session
	 * @return the user for the WebSocket session, or {@code null} if not available
	 */
	protected Principal determineUser(ServerHttpRequest request, WebSocketHandler wsHandler,
			Map<String, Object> attributes) {

		return request.getPrincipal();
	}

}


File: spring-websocket/src/main/java/org/springframework/web/socket/server/support/WebSocketHandlerMapping.java
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
package org.springframework.web.socket.server.support;

import org.springframework.context.Lifecycle;
import org.springframework.context.SmartLifecycle;
import org.springframework.web.servlet.handler.SimpleUrlHandlerMapping;

/**
 * An extension of {@link SimpleUrlHandlerMapping} that is also a
 * {@link SmartLifecycle} container and propagates start and stop calls to any
 * handlers that implement {@link Lifecycle}. The handlers are typically expected
 * to be {@code WebSocketHttpRequestHandler} or {@code SockJsHttpRequestHandler}.
 *
 * @author Rossen Stoyanchev
 * @since 4.2
 */
public class WebSocketHandlerMapping extends SimpleUrlHandlerMapping implements SmartLifecycle {

	private volatile boolean running = false;


	@Override
	public boolean isAutoStartup() {
		return true;
	}

	@Override
	public boolean isRunning() {
		return this.running;
	}

	@Override
	public int getPhase() {
		return Integer.MAX_VALUE;
	}

	@Override
	public void start() {
		if (!isRunning()) {
			this.running = true;
			for (Object handler : getUrlMap().values()) {
				if (handler instanceof Lifecycle) {
					((Lifecycle) handler).start();
				}
			}
		}
	}

	@Override
	public void stop() {
		if (isRunning()) {
			this.running = false;
			for (Object handler : getUrlMap().values()) {
				if (handler instanceof Lifecycle) {
					((Lifecycle) handler).stop();
				}
			}
		}
	}

	@Override
	public void stop(Runnable callback) {
		stop();
		callback.run();
	}

}


File: spring-websocket/src/main/java/org/springframework/web/socket/server/support/WebSocketHttpRequestHandler.java
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

package org.springframework.web.socket.server.support;

import java.io.IOException;
import java.util.ArrayList;
import java.util.HashMap;
import java.util.List;
import java.util.Map;
import javax.servlet.ServletException;
import javax.servlet.http.HttpServletRequest;
import javax.servlet.http.HttpServletResponse;

import org.apache.commons.logging.Log;
import org.apache.commons.logging.LogFactory;

import org.springframework.context.Lifecycle;
import org.springframework.http.server.ServerHttpRequest;
import org.springframework.http.server.ServerHttpResponse;
import org.springframework.http.server.ServletServerHttpRequest;
import org.springframework.http.server.ServletServerHttpResponse;
import org.springframework.util.Assert;
import org.springframework.web.HttpRequestHandler;
import org.springframework.web.socket.WebSocketHandler;
import org.springframework.web.socket.handler.ExceptionWebSocketHandlerDecorator;
import org.springframework.web.socket.handler.LoggingWebSocketHandlerDecorator;
import org.springframework.web.socket.server.HandshakeFailureException;
import org.springframework.web.socket.server.HandshakeHandler;
import org.springframework.web.socket.server.HandshakeInterceptor;

/**
 * A {@link HttpRequestHandler} for processing WebSocket handshake requests.
 *
 * <p>This is the main class to use when configuring a server WebSocket at a specific URL.
 * It is a very thin wrapper around a {@link WebSocketHandler} and a {@link HandshakeHandler},
 * also adapting the {@link HttpServletRequest} and {@link HttpServletResponse} to
 * {@link ServerHttpRequest} and {@link ServerHttpResponse}, respectively.
 *
 * @author Rossen Stoyanchev
 * @since 4.0
 */
public class WebSocketHttpRequestHandler implements HttpRequestHandler, Lifecycle {

	private final Log logger = LogFactory.getLog(WebSocketHttpRequestHandler.class);

	private final WebSocketHandler wsHandler;

	private final HandshakeHandler handshakeHandler;

	private final List<HandshakeInterceptor> interceptors = new ArrayList<HandshakeInterceptor>();

	private volatile boolean running = false;


	public WebSocketHttpRequestHandler(WebSocketHandler wsHandler) {
		this(wsHandler, new DefaultHandshakeHandler());
	}

	public WebSocketHttpRequestHandler(WebSocketHandler wsHandler, HandshakeHandler handshakeHandler) {
		Assert.notNull(wsHandler, "wsHandler must not be null");
		Assert.notNull(handshakeHandler, "handshakeHandler must not be null");
		this.wsHandler = new ExceptionWebSocketHandlerDecorator(new LoggingWebSocketHandlerDecorator(wsHandler));
		this.handshakeHandler = handshakeHandler;
	}


	/**
	 * Return the WebSocketHandler.
	 */
	public WebSocketHandler getWebSocketHandler() {
		return this.wsHandler;
	}

	/**
	 * Return the HandshakeHandler.
	 */
	public HandshakeHandler getHandshakeHandler() {
		return this.handshakeHandler;
	}

	/**
	 * Configure one or more WebSocket handshake request interceptors.
	 */
	public void setHandshakeInterceptors(List<HandshakeInterceptor> interceptors) {
		this.interceptors.clear();
		if (interceptors != null) {
			this.interceptors.addAll(interceptors);
		}
	}

	/**
	 * Return the configured WebSocket handshake request interceptors.
	 */
	public List<HandshakeInterceptor> getHandshakeInterceptors() {
		return this.interceptors;
	}

	@Override
	public boolean isRunning() {
		return this.running;
	}

	@Override
	public void start() {
		if (!isRunning()) {
			this.running = true;
			if (this.handshakeHandler instanceof Lifecycle) {
				((Lifecycle) this.handshakeHandler).start();
			}
		}
	}

	@Override
	public void stop() {
		if (isRunning()) {
			this.running = false;
			if (this.handshakeHandler instanceof Lifecycle) {
				((Lifecycle) this.handshakeHandler).stop();
			}
		}
	}


	@Override
	public void handleRequest(HttpServletRequest servletRequest, HttpServletResponse servletResponse)
			throws ServletException, IOException {

		ServerHttpRequest request = new ServletServerHttpRequest(servletRequest);
		ServerHttpResponse response = new ServletServerHttpResponse(servletResponse);

		HandshakeInterceptorChain chain = new HandshakeInterceptorChain(this.interceptors, this.wsHandler);
		HandshakeFailureException failure = null;

		try {
			if (logger.isDebugEnabled()) {
				logger.debug(servletRequest.getMethod() + " " + servletRequest.getRequestURI());
			}
			Map<String, Object> attributes = new HashMap<String, Object>();
			if (!chain.applyBeforeHandshake(request, response, attributes)) {
				return;
			}
			this.handshakeHandler.doHandshake(request, response, this.wsHandler, attributes);
			chain.applyAfterHandshake(request, response, null);
			response.close();
		}
		catch (HandshakeFailureException ex) {
			failure = ex;
		}
		catch (Throwable ex) {
			failure = new HandshakeFailureException("Uncaught failure for request " + request.getURI(), ex);
		}
		finally {
			if (failure != null) {
				chain.applyAfterHandshake(request, response, failure);
				throw failure;
			}
		}
	}

}


File: spring-websocket/src/main/java/org/springframework/web/socket/sockjs/support/SockJsHttpRequestHandler.java
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

package org.springframework.web.socket.sockjs.support;

import java.io.IOException;

import javax.servlet.ServletException;
import javax.servlet.http.HttpServletRequest;
import javax.servlet.http.HttpServletResponse;

import org.springframework.context.Lifecycle;
import org.springframework.http.server.ServerHttpRequest;
import org.springframework.http.server.ServerHttpResponse;
import org.springframework.http.server.ServletServerHttpRequest;
import org.springframework.http.server.ServletServerHttpResponse;
import org.springframework.util.Assert;
import org.springframework.web.HttpRequestHandler;
import org.springframework.web.cors.CorsConfiguration;
import org.springframework.web.cors.CorsConfigurationSource;
import org.springframework.web.servlet.HandlerMapping;
import org.springframework.web.socket.WebSocketHandler;
import org.springframework.web.socket.handler.ExceptionWebSocketHandlerDecorator;
import org.springframework.web.socket.handler.LoggingWebSocketHandlerDecorator;
import org.springframework.web.socket.sockjs.SockJsException;
import org.springframework.web.socket.sockjs.SockJsService;

/**
 * An {@link HttpRequestHandler} that allows mapping a {@link SockJsService} to requests
 * in a Servlet container.
 *
 * @author Rossen Stoyanchev
 * @author Sebastien Deleuze
 * @since 4.0
 */
public class SockJsHttpRequestHandler
		implements HttpRequestHandler, CorsConfigurationSource, Lifecycle {

	// No logging: HTTP transports too verbose and we don't know enough to log anything of value

	private final SockJsService sockJsService;

	private final WebSocketHandler webSocketHandler;

	private volatile boolean running = false;


	/**
	 * Create a new SockJsHttpRequestHandler.
	 * @param sockJsService the SockJS service
	 * @param webSocketHandler the websocket handler
	 */
	public SockJsHttpRequestHandler(SockJsService sockJsService, WebSocketHandler webSocketHandler) {
		Assert.notNull(sockJsService, "sockJsService must not be null");
		Assert.notNull(webSocketHandler, "webSocketHandler must not be null");
		this.sockJsService = sockJsService;
		this.webSocketHandler =
				new ExceptionWebSocketHandlerDecorator(new LoggingWebSocketHandlerDecorator(webSocketHandler));
	}


	/**
	 * Return the {@link SockJsService}.
	 */
	public SockJsService getSockJsService() {
		return this.sockJsService;
	}

	/**
	 * Return the {@link WebSocketHandler}.
	 */
	public WebSocketHandler getWebSocketHandler() {
		return this.webSocketHandler;
	}

	@Override
	public boolean isRunning() {
		return this.running;
	}

	@Override
	public void start() {
		if (!isRunning()) {
			this.running = true;
			if (this.sockJsService instanceof Lifecycle) {
				((Lifecycle) this.sockJsService).start();
			}
		}
	}

	@Override
	public void stop() {
		if (isRunning()) {
			this.running = false;
			if (this.sockJsService instanceof Lifecycle) {
				((Lifecycle) this.sockJsService).stop();
			}
		}
	}


	@Override
	public void handleRequest(HttpServletRequest servletRequest, HttpServletResponse servletResponse)
			throws ServletException, IOException {

		ServerHttpRequest request = new ServletServerHttpRequest(servletRequest);
		ServerHttpResponse response = new ServletServerHttpResponse(servletResponse);

		try {
			this.sockJsService.handleRequest(request, response, getSockJsPath(servletRequest), this.webSocketHandler);
		}
		catch (Throwable ex) {
			throw new SockJsException("Uncaught failure in SockJS request, uri=" + request.getURI(), ex);
		}
	}

	private String getSockJsPath(HttpServletRequest servletRequest) {
		String attribute = HandlerMapping.PATH_WITHIN_HANDLER_MAPPING_ATTRIBUTE;
		String path = (String) servletRequest.getAttribute(attribute);
		return ((path.length() > 0) && (path.charAt(0) != '/')) ? "/" + path : path;
	}

	@Override
	public CorsConfiguration getCorsConfiguration(HttpServletRequest request) {
		if (sockJsService instanceof CorsConfigurationSource) {
			return ((CorsConfigurationSource)sockJsService).getCorsConfiguration(request);
		}
		return null;
	}

}


File: spring-websocket/src/main/java/org/springframework/web/socket/sockjs/transport/handler/DefaultSockJsService.java
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

package org.springframework.web.socket.sockjs.transport.handler;

import java.util.Arrays;
import java.util.Collection;
import java.util.LinkedHashSet;
import java.util.Set;

import org.apache.commons.logging.Log;
import org.apache.commons.logging.LogFactory;

import org.springframework.scheduling.TaskScheduler;
import org.springframework.web.socket.server.support.DefaultHandshakeHandler;
import org.springframework.web.socket.sockjs.transport.TransportHandler;
import org.springframework.web.socket.sockjs.transport.TransportHandlingSockJsService;

/**
 * A default implementation of {@link org.springframework.web.socket.sockjs.SockJsService}
 * with all default {@link TransportHandler} implementations pre-registered.
 *
 * @author Rossen Stoyanchev
 * @author Juergen Hoeller
 * @since 4.0
 */
public class DefaultSockJsService extends TransportHandlingSockJsService {

	/**
	 * Create a DefaultSockJsService with default {@link TransportHandler handler} types.
	 * @param scheduler a task scheduler for heart-beat messages and removing
	 * timed-out sessions; the provided TaskScheduler should be declared as a
	 * Spring bean to ensure it is initialized at start up and shut down when the
	 * application stops.
	 */
	public DefaultSockJsService(TaskScheduler scheduler) {
		this(scheduler, getDefaultTransportHandlers(null));
	}

	/**
	 * Create a DefaultSockJsService with overridden {@link TransportHandler handler} types
	 * replacing the corresponding default handler implementation.
	 * @param scheduler a task scheduler for heart-beat messages and removing timed-out sessions;
	 * the provided TaskScheduler should be declared as a Spring bean to ensure it gets
	 * initialized at start-up and shuts down when the application stops
	 * @param handlerOverrides zero or more overrides to the default transport handler types
	 */
	public DefaultSockJsService(TaskScheduler scheduler, TransportHandler... handlerOverrides) {
		this(scheduler, Arrays.asList(handlerOverrides));
	}

	/**
	 * Create a DefaultSockJsService with overridden {@link TransportHandler handler} types
	 * replacing the corresponding default handler implementation.
	 * @param scheduler a task scheduler for heart-beat messages and removing timed-out sessions;
	 * the provided TaskScheduler should be declared as a Spring bean to ensure it gets
	 * initialized at start-up and shuts down when the application stops
	 * @param handlerOverrides zero or more overrides to the default transport handler types
	 */
	public DefaultSockJsService(TaskScheduler scheduler, Collection<TransportHandler> handlerOverrides) {
		super(scheduler, getDefaultTransportHandlers(handlerOverrides));
	}


	private static Set<TransportHandler> getDefaultTransportHandlers(Collection<TransportHandler> overrides) {
		Set<TransportHandler> result = new LinkedHashSet<TransportHandler>(8);
		result.add(new XhrPollingTransportHandler());
		result.add(new XhrReceivingTransportHandler());
		result.add(new XhrStreamingTransportHandler());
		result.add(new JsonpPollingTransportHandler());
		result.add(new JsonpReceivingTransportHandler());
		result.add(new EventSourceTransportHandler());
		result.add(new HtmlFileTransportHandler());
		try {
			result.add(new WebSocketTransportHandler(new DefaultHandshakeHandler()));
		}
		catch (Exception ex) {
			Log logger = LogFactory.getLog(DefaultSockJsService.class);
			if (logger.isWarnEnabled()) {
				logger.warn("Failed to create a default WebSocketTransportHandler", ex);
			}
		}
		if (overrides != null) {
			result.addAll(overrides);
		}
		return result;
	}

}


File: spring-websocket/src/main/java/org/springframework/web/socket/sockjs/transport/handler/WebSocketTransportHandler.java
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

package org.springframework.web.socket.sockjs.transport.handler;

import java.util.Map;

import org.springframework.context.Lifecycle;
import org.springframework.http.server.ServerHttpRequest;
import org.springframework.http.server.ServerHttpResponse;
import org.springframework.util.Assert;
import org.springframework.web.socket.CloseStatus;
import org.springframework.web.socket.WebSocketHandler;
import org.springframework.web.socket.server.HandshakeFailureException;
import org.springframework.web.socket.server.HandshakeHandler;
import org.springframework.web.socket.sockjs.SockJsException;
import org.springframework.web.socket.sockjs.SockJsTransportFailureException;
import org.springframework.web.socket.sockjs.transport.SockJsSession;
import org.springframework.web.socket.sockjs.transport.SockJsSessionFactory;
import org.springframework.web.socket.sockjs.transport.TransportHandler;
import org.springframework.web.socket.sockjs.transport.TransportType;
import org.springframework.web.socket.sockjs.transport.session.AbstractSockJsSession;
import org.springframework.web.socket.sockjs.transport.session.WebSocketServerSockJsSession;

/**
 * WebSocket-based {@link TransportHandler}. Uses {@link SockJsWebSocketHandler} and
 * {@link WebSocketServerSockJsSession} to add SockJS processing.
 *
 * <p>Also implements {@link HandshakeHandler} to support raw WebSocket communication at
 * SockJS URL "/websocket".
 *
 * @author Rossen Stoyanchev
 * @since 4.0
 */
public class WebSocketTransportHandler extends AbstractTransportHandler
		implements SockJsSessionFactory, HandshakeHandler, Lifecycle {

	private final HandshakeHandler handshakeHandler;

	private boolean running;


	public WebSocketTransportHandler(HandshakeHandler handshakeHandler) {
		Assert.notNull(handshakeHandler, "handshakeHandler must not be null");
		this.handshakeHandler = handshakeHandler;
	}


	@Override
	public TransportType getTransportType() {
		return TransportType.WEBSOCKET;
	}

	public HandshakeHandler getHandshakeHandler() {
		return this.handshakeHandler;
	}

	@Override
	public boolean isRunning() {
		return this.running;
	}

	@Override
	public void start() {
		if (!isRunning()) {
			this.running = true;
			if (this.handshakeHandler instanceof Lifecycle) {
				((Lifecycle) this.handshakeHandler).start();
			}
		}
	}

	@Override
	public void stop() {
		if (isRunning()) {
			this.running = false;
			if (this.handshakeHandler instanceof Lifecycle) {
				((Lifecycle) this.handshakeHandler).stop();
			}
		}
	}

	@Override
	public AbstractSockJsSession createSession(String id, WebSocketHandler handler, Map<String, Object> attrs) {
		return new WebSocketServerSockJsSession(id, getServiceConfig(), handler, attrs);
	}

	@Override
	public void handleRequest(ServerHttpRequest request, ServerHttpResponse response,
			WebSocketHandler wsHandler, SockJsSession wsSession) throws SockJsException {

		WebSocketServerSockJsSession sockJsSession = (WebSocketServerSockJsSession) wsSession;
		try {
			wsHandler = new SockJsWebSocketHandler(getServiceConfig(), wsHandler, sockJsSession);
			this.handshakeHandler.doHandshake(request, response, wsHandler, sockJsSession.getAttributes());
		}
		catch (Throwable ex) {
			sockJsSession.tryCloseWithSockJsTransportError(ex, CloseStatus.SERVER_ERROR);
			throw new SockJsTransportFailureException("WebSocket handshake failure", wsSession.getId(), ex);
		}
	}

	@Override
	public boolean doHandshake(ServerHttpRequest request, ServerHttpResponse response,
			WebSocketHandler handler, Map<String, Object> attributes) throws HandshakeFailureException {

		return this.handshakeHandler.doHandshake(request, response, handler, attributes);
	}
}


File: spring-websocket/src/test/java/org/springframework/web/socket/AbstractWebSocketIntegrationTests.java
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

package org.springframework.web.socket;

import java.util.HashMap;
import java.util.Map;

import org.apache.commons.logging.Log;
import org.apache.commons.logging.LogFactory;
import org.junit.After;
import org.junit.Before;
import org.junit.Rule;
import org.junit.rules.TestName;
import org.junit.runners.Parameterized.Parameter;

import org.springframework.context.Lifecycle;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.util.concurrent.ListenableFuture;
import org.springframework.web.context.support.AnnotationConfigWebApplicationContext;
import org.springframework.web.socket.client.WebSocketClient;
import org.springframework.web.socket.server.RequestUpgradeStrategy;
import org.springframework.web.socket.server.jetty.JettyRequestUpgradeStrategy;
import org.springframework.web.socket.server.standard.TomcatRequestUpgradeStrategy;
import org.springframework.web.socket.server.standard.UndertowRequestUpgradeStrategy;
import org.springframework.web.socket.server.support.DefaultHandshakeHandler;

/**
 * Base class for WebSocket integration tests.
 *
 * @author Rossen Stoyanchev
 */
public abstract class AbstractWebSocketIntegrationTests {

	protected Log logger = LogFactory.getLog(getClass());

	private static Map<Class<?>, Class<?>> upgradeStrategyConfigTypes = new HashMap<Class<?>, Class<?>>();

	static {
		upgradeStrategyConfigTypes.put(JettyWebSocketTestServer.class, JettyUpgradeStrategyConfig.class);
		upgradeStrategyConfigTypes.put(TomcatWebSocketTestServer.class, TomcatUpgradeStrategyConfig.class);
		upgradeStrategyConfigTypes.put(UndertowTestServer.class, UndertowUpgradeStrategyConfig.class);
	}

	@Rule
	public final TestName testName = new TestName();

	@Parameter(0)
	public WebSocketTestServer server;

	@Parameter(1)
	public WebSocketClient webSocketClient;

	protected AnnotationConfigWebApplicationContext wac;


	@Before
	public void setup() throws Exception {

		logger.debug("Setting up '" + this.testName.getMethodName() + "', client=" +
				this.webSocketClient.getClass().getSimpleName() + ", server=" +
				this.server.getClass().getSimpleName());

		this.wac = new AnnotationConfigWebApplicationContext();
		this.wac.register(getAnnotatedConfigClasses());
		this.wac.register(upgradeStrategyConfigTypes.get(this.server.getClass()));
		this.wac.refresh();

		if (this.webSocketClient instanceof Lifecycle) {
			((Lifecycle) this.webSocketClient).start();
		}

		this.server.setup();
		this.server.deployConfig(this.wac);
		this.server.start();
	}

	protected abstract Class<?>[] getAnnotatedConfigClasses();

	@After
	public void teardown() throws Exception {
		try {
			if (this.webSocketClient instanceof Lifecycle) {
				((Lifecycle) this.webSocketClient).stop();
			}
		}
		catch (Throwable t) {
			logger.error("Failed to stop WebSocket client", t);
		}
		try {
			this.server.undeployConfig();
		}
		catch (Throwable t) {
			logger.error("Failed to undeploy application config", t);
		}
		try {
			this.server.stop();
		}
		catch (Throwable t) {
			logger.error("Failed to stop server", t);
		}
		try {
			this.wac.close();
		}
		catch (Throwable t) {
			logger.error("Failed to close WebApplicationContext", t);
		}
	}

	protected String getWsBaseUrl() {
		return "ws://localhost:" + this.server.getPort();
	}

	protected ListenableFuture<WebSocketSession> doHandshake(WebSocketHandler clientHandler, String endpointPath) {
		return this.webSocketClient.doHandshake(clientHandler, getWsBaseUrl() + endpointPath);
	}


	static abstract class AbstractRequestUpgradeStrategyConfig {

		@Bean
		public DefaultHandshakeHandler handshakeHandler() {
			return new DefaultHandshakeHandler(requestUpgradeStrategy());
		}

		public abstract RequestUpgradeStrategy requestUpgradeStrategy();
	}


	@Configuration
	static class JettyUpgradeStrategyConfig extends AbstractRequestUpgradeStrategyConfig {

		@Bean
		public RequestUpgradeStrategy requestUpgradeStrategy() {
			return new JettyRequestUpgradeStrategy();
		}
	}

	@Configuration
	static class TomcatUpgradeStrategyConfig extends AbstractRequestUpgradeStrategyConfig {

		@Bean
		public RequestUpgradeStrategy requestUpgradeStrategy() {
			return new TomcatRequestUpgradeStrategy();
		}
	}

	@Configuration
	static class UndertowUpgradeStrategyConfig extends AbstractRequestUpgradeStrategyConfig {

		@Bean
		public RequestUpgradeStrategy requestUpgradeStrategy() {
			return new UndertowRequestUpgradeStrategy();
		}
	}

}


File: spring-websocket/src/test/java/org/springframework/web/socket/TomcatWebSocketTestServer.java
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

package org.springframework.web.socket;

import java.io.File;
import java.io.IOException;

import javax.servlet.Filter;

import org.apache.catalina.Context;
import org.apache.catalina.connector.Connector;
import org.apache.catalina.startup.Tomcat;
import org.apache.coyote.http11.Http11NioProtocol;
import org.apache.tomcat.util.descriptor.web.FilterDef;
import org.apache.tomcat.util.descriptor.web.FilterMap;
import org.apache.tomcat.websocket.server.WsContextListener;

import org.springframework.util.Assert;
import org.springframework.util.SocketUtils;
import org.springframework.web.context.WebApplicationContext;
import org.springframework.web.servlet.DispatcherServlet;

/**
 * Tomcat based {@link WebSocketTestServer}.
 *
 * @author Rossen Stoyanchev
 */
public class TomcatWebSocketTestServer implements WebSocketTestServer {

	private Tomcat tomcatServer;

	private int port = -1;

	private Context context;


	@Override
	public void setup() {
		this.port = SocketUtils.findAvailableTcpPort();

		Connector connector = new Connector(Http11NioProtocol.class.getName());
		connector.setPort(this.port);

		File baseDir = createTempDir("tomcat");
		String baseDirPath = baseDir.getAbsolutePath();

		this.tomcatServer = new Tomcat();
		this.tomcatServer.setBaseDir(baseDirPath);
		this.tomcatServer.setPort(this.port);
		this.tomcatServer.getService().addConnector(connector);
		this.tomcatServer.setConnector(connector);
	}

	private File createTempDir(String prefix) {
		try {
			File tempFolder = File.createTempFile(prefix + ".", "." + getPort());
			tempFolder.delete();
			tempFolder.mkdir();
			tempFolder.deleteOnExit();
			return tempFolder;
		}
		catch (IOException ex) {
			throw new RuntimeException("Unable to create temp directory", ex);
		}
	}

	@Override
	public int getPort() {
		return this.port;
	}

	@Override
	public void deployConfig(WebApplicationContext wac, Filter... filters) {
		Assert.state(this.port != -1, "setup() was never called.");
		this.context = this.tomcatServer.addContext("", System.getProperty("java.io.tmpdir"));
        this.context.addApplicationListener(WsContextListener.class.getName());
		Tomcat.addServlet(this.context, "dispatcherServlet", new DispatcherServlet(wac)).setAsyncSupported(true);
		this.context.addServletMapping("/", "dispatcherServlet");
		for (Filter filter : filters) {
			FilterDef filterDef = new FilterDef();
			filterDef.setFilterName(filter.getClass().getName());
			filterDef.setFilter(filter);
			filterDef.setAsyncSupported("true");
			this.context.addFilterDef(filterDef);
			FilterMap filterMap = new FilterMap();
			filterMap.setFilterName(filter.getClass().getName());
			filterMap.addURLPattern("/*");
			filterMap.setDispatcher("REQUEST,FORWARD,INCLUDE,ASYNC");
			this.context.addFilterMap(filterMap);
		}
	}

	@Override
	public void undeployConfig() {
		if (this.context != null) {
			this.context.removeServletMapping("/");
			this.tomcatServer.getHost().removeChild(this.context);
		}
	}

	@Override
	public void start() throws Exception {
		this.tomcatServer.start();
	}

	@Override
	public void stop() throws Exception {
		this.tomcatServer.stop();
	}

}


File: spring-websocket/src/test/java/org/springframework/web/socket/WebSocketIntegrationTests.java
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

package org.springframework.web.socket;

import java.net.URI;
import java.util.ArrayList;
import java.util.Arrays;
import java.util.List;
import java.util.concurrent.CountDownLatch;
import java.util.concurrent.TimeUnit;

import org.junit.Test;
import org.junit.runner.RunWith;
import org.junit.runners.Parameterized;
import org.junit.runners.Parameterized.Parameters;

import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.web.socket.client.jetty.JettyWebSocketClient;
import org.springframework.web.socket.client.standard.StandardWebSocketClient;
import org.springframework.web.socket.config.annotation.EnableWebSocket;
import org.springframework.web.socket.config.annotation.WebSocketConfigurer;
import org.springframework.web.socket.config.annotation.WebSocketHandlerRegistry;
import org.springframework.web.socket.handler.AbstractWebSocketHandler;
import org.springframework.web.socket.handler.TextWebSocketHandler;
import org.springframework.web.socket.server.support.DefaultHandshakeHandler;

import static org.junit.Assert.*;

/**
 * Client and server-side WebSocket integration tests.
 *
 * @author Rossen Stoyanchev
 */
@RunWith(Parameterized.class)
public class WebSocketIntegrationTests extends  AbstractWebSocketIntegrationTests {

	@Parameters(name = "server [{0}], client [{1}]")
	public static Iterable<Object[]> arguments() {
		return Arrays.asList(new Object[][] {
				{new JettyWebSocketTestServer(), new JettyWebSocketClient()},
				{new TomcatWebSocketTestServer(), new StandardWebSocketClient()},
				{new UndertowTestServer(), new JettyWebSocketClient()}
		});
	}


	@Override
	protected Class<?>[] getAnnotatedConfigClasses() {
		return new Class<?>[] { TestConfig.class };
	}

	@Test
	public void subProtocolNegotiation() throws Exception {
		WebSocketHttpHeaders headers = new WebSocketHttpHeaders();
		headers.setSecWebSocketProtocol("foo");
		URI url = new URI(getWsBaseUrl() + "/ws");
		WebSocketSession session = this.webSocketClient.doHandshake(new TextWebSocketHandler(), headers, url).get();
		assertEquals("foo", session.getAcceptedProtocol());
		session.close();
	}

	// SPR-12727

	@Test
	public void unsolicitedPongWithEmptyPayload() throws Exception {
		TestWebSocketHandler serverHandler = this.wac.getBean(TestWebSocketHandler.class);
		serverHandler.setWaitMessageCount(1);

		String url = getWsBaseUrl() + "/ws";
		WebSocketSession session = this.webSocketClient.doHandshake(new AbstractWebSocketHandler() {}, url).get();
		session.sendMessage(new PongMessage());

		serverHandler.await();
		assertNull(serverHandler.getTransportError());
		assertEquals(1, serverHandler.getReceivedMessages().size());
		assertEquals(PongMessage.class, serverHandler.getReceivedMessages().get(0).getClass());
	}


	@Configuration
	@EnableWebSocket
	static class TestConfig implements WebSocketConfigurer {

		@Autowired
		private DefaultHandshakeHandler handshakeHandler;  // can't rely on classpath for server detection

		@Override
		public void registerWebSocketHandlers(WebSocketHandlerRegistry registry) {
			this.handshakeHandler.setSupportedProtocols("foo", "bar", "baz");
			registry.addHandler(handler(), "/ws").setHandshakeHandler(this.handshakeHandler);
		}

		@Bean
		public TestWebSocketHandler handler() {
			return new TestWebSocketHandler();
		}

	}

	@SuppressWarnings("rawtypes")
	private static class TestWebSocketHandler extends AbstractWebSocketHandler {

		private List<WebSocketMessage> receivedMessages = new ArrayList<>();

		private int waitMessageCount;

		private final CountDownLatch latch = new CountDownLatch(1);

		private Throwable transportError;


		public void setWaitMessageCount(int waitMessageCount) {
			this.waitMessageCount = waitMessageCount;
		}

		public List<WebSocketMessage> getReceivedMessages() {
			return this.receivedMessages;
		}

		public Throwable getTransportError() {
			return this.transportError;
		}

		@Override
		public void handleMessage(WebSocketSession session, WebSocketMessage<?> message) throws Exception {
			this.receivedMessages.add(message);
			if (this.receivedMessages.size() >= this.waitMessageCount) {
				this.latch.countDown();
			}
		}

		@Override
		public void handleTransportError(WebSocketSession session, Throwable exception) throws Exception {
			this.transportError = exception;
			this.latch.countDown();
		}

		public void await() throws InterruptedException {
			this.latch.await(5, TimeUnit.SECONDS);
		}
	}

}


File: spring-websocket/src/test/java/org/springframework/web/socket/config/MessageBrokerBeanDefinitionParserTests.java
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

package org.springframework.web.socket.config;

import static org.hamcrest.Matchers.*;
import static org.junit.Assert.*;

import java.util.ArrayList;
import java.util.Arrays;
import java.util.Collection;
import java.util.Collections;
import java.util.List;
import java.util.Map;

import org.hamcrest.Matchers;
import org.junit.Before;
import org.junit.Test;

import org.springframework.beans.DirectFieldAccessor;
import org.springframework.beans.factory.NoSuchBeanDefinitionException;
import org.springframework.beans.factory.config.CustomScopeConfigurer;
import org.springframework.beans.factory.xml.XmlBeanDefinitionReader;
import org.springframework.core.MethodParameter;
import org.springframework.core.io.ClassPathResource;
import org.springframework.messaging.Message;
import org.springframework.messaging.MessageHandler;
import org.springframework.messaging.converter.ByteArrayMessageConverter;
import org.springframework.messaging.converter.CompositeMessageConverter;
import org.springframework.messaging.converter.ContentTypeResolver;
import org.springframework.messaging.converter.DefaultContentTypeResolver;
import org.springframework.messaging.converter.MappingJackson2MessageConverter;
import org.springframework.messaging.converter.MessageConverter;
import org.springframework.messaging.converter.StringMessageConverter;
import org.springframework.messaging.handler.invocation.HandlerMethodArgumentResolver;
import org.springframework.messaging.handler.invocation.HandlerMethodReturnValueHandler;
import org.springframework.messaging.simp.SimpMessagingTemplate;
import org.springframework.messaging.simp.annotation.support.SimpAnnotationMethodMessageHandler;
import org.springframework.messaging.simp.broker.SimpleBrokerMessageHandler;
import org.springframework.messaging.simp.stomp.StompBrokerRelayMessageHandler;
import org.springframework.messaging.simp.user.DefaultUserDestinationResolver;
import org.springframework.messaging.simp.user.MultiServerUserRegistry;
import org.springframework.messaging.simp.user.SimpUserRegistry;
import org.springframework.messaging.simp.user.UserDestinationMessageHandler;
import org.springframework.messaging.simp.user.UserDestinationResolver;
import org.springframework.messaging.simp.user.UserRegistryMessageHandler;
import org.springframework.messaging.support.AbstractSubscribableChannel;
import org.springframework.messaging.support.ChannelInterceptor;
import org.springframework.messaging.support.ImmutableMessageChannelInterceptor;
import org.springframework.scheduling.concurrent.ThreadPoolTaskExecutor;
import org.springframework.scheduling.concurrent.ThreadPoolTaskScheduler;
import org.springframework.util.MimeTypeUtils;
import org.springframework.web.HttpRequestHandler;
import org.springframework.web.context.support.GenericWebApplicationContext;
import org.springframework.web.servlet.HandlerMapping;
import org.springframework.web.servlet.handler.SimpleUrlHandlerMapping;
import org.springframework.web.socket.WebSocketHandler;
import org.springframework.web.socket.WebSocketSession;
import org.springframework.web.socket.handler.TestWebSocketSession;
import org.springframework.web.socket.handler.WebSocketHandlerDecorator;
import org.springframework.web.socket.handler.WebSocketHandlerDecoratorFactory;
import org.springframework.web.socket.messaging.DefaultSimpUserRegistry;
import org.springframework.web.socket.messaging.StompSubProtocolErrorHandler;
import org.springframework.web.socket.messaging.StompSubProtocolHandler;
import org.springframework.web.socket.messaging.SubProtocolHandler;
import org.springframework.web.socket.messaging.SubProtocolWebSocketHandler;
import org.springframework.web.socket.server.HandshakeHandler;
import org.springframework.web.socket.server.HandshakeInterceptor;
import org.springframework.web.socket.server.support.OriginHandshakeInterceptor;
import org.springframework.web.socket.server.support.WebSocketHttpRequestHandler;
import org.springframework.web.socket.sockjs.support.SockJsHttpRequestHandler;
import org.springframework.web.socket.sockjs.transport.TransportType;
import org.springframework.web.socket.sockjs.transport.handler.DefaultSockJsService;
import org.springframework.web.socket.sockjs.transport.handler.WebSocketTransportHandler;

/**
 * Test fixture for MessageBrokerBeanDefinitionParser.
 * See test configuration files websocket-config-broker-*.xml.
 *
 * @author Brian Clozel
 * @author Artem Bilan
 * @author Rossen Stoyanchev
 */
public class MessageBrokerBeanDefinitionParserTests {

	private GenericWebApplicationContext appContext;


	@Before
	public void setup() {
		this.appContext = new GenericWebApplicationContext();
	}


	@Test
	@SuppressWarnings("unchecked")
	public void simpleBroker() throws Exception {
		loadBeanDefinitions("websocket-config-broker-simple.xml");

		HandlerMapping hm = this.appContext.getBean(HandlerMapping.class);
		assertThat(hm, Matchers.instanceOf(SimpleUrlHandlerMapping.class));
		SimpleUrlHandlerMapping suhm = (SimpleUrlHandlerMapping) hm;
		assertThat(suhm.getUrlMap().keySet(), Matchers.hasSize(4));
		assertThat(suhm.getUrlMap().values(), Matchers.hasSize(4));

		HttpRequestHandler httpRequestHandler = (HttpRequestHandler) suhm.getUrlMap().get("/foo");
		assertNotNull(httpRequestHandler);
		assertThat(httpRequestHandler, Matchers.instanceOf(WebSocketHttpRequestHandler.class));

		WebSocketHttpRequestHandler wsHttpRequestHandler = (WebSocketHttpRequestHandler) httpRequestHandler;
		HandshakeHandler handshakeHandler = wsHttpRequestHandler.getHandshakeHandler();
		assertNotNull(handshakeHandler);
		assertTrue(handshakeHandler instanceof TestHandshakeHandler);
		List<HandshakeInterceptor> interceptors = wsHttpRequestHandler.getHandshakeInterceptors();
		assertThat(interceptors, contains(instanceOf(FooTestInterceptor.class),
				instanceOf(BarTestInterceptor.class), instanceOf(OriginHandshakeInterceptor.class)));

		WebSocketSession session = new TestWebSocketSession("id");
		wsHttpRequestHandler.getWebSocketHandler().afterConnectionEstablished(session);
		assertEquals(true, session.getAttributes().get("decorated"));

		WebSocketHandler wsHandler = unwrapWebSocketHandler(wsHttpRequestHandler.getWebSocketHandler());
		assertNotNull(wsHandler);
		assertThat(wsHandler, Matchers.instanceOf(SubProtocolWebSocketHandler.class));

		SubProtocolWebSocketHandler subProtocolWsHandler = (SubProtocolWebSocketHandler) wsHandler;
		assertEquals(Arrays.asList("v10.stomp", "v11.stomp", "v12.stomp"), subProtocolWsHandler.getSubProtocols());
		assertEquals(25 * 1000, subProtocolWsHandler.getSendTimeLimit());
		assertEquals(1024 * 1024, subProtocolWsHandler.getSendBufferSizeLimit());

		Map<String, SubProtocolHandler> handlerMap = subProtocolWsHandler.getProtocolHandlerMap();
		StompSubProtocolHandler stompHandler = (StompSubProtocolHandler) handlerMap.get("v12.stomp");
		assertNotNull(stompHandler);
		assertEquals(128 * 1024, stompHandler.getMessageSizeLimit());
		assertNotNull(stompHandler.getErrorHandler());
		assertEquals(TestStompErrorHandler.class, stompHandler.getErrorHandler().getClass());

		assertNotNull(new DirectFieldAccessor(stompHandler).getPropertyValue("eventPublisher"));

		httpRequestHandler = (HttpRequestHandler) suhm.getUrlMap().get("/test/**");
		assertNotNull(httpRequestHandler);
		assertThat(httpRequestHandler, Matchers.instanceOf(SockJsHttpRequestHandler.class));

		SockJsHttpRequestHandler sockJsHttpRequestHandler = (SockJsHttpRequestHandler) httpRequestHandler;
		wsHandler = unwrapWebSocketHandler(sockJsHttpRequestHandler.getWebSocketHandler());
		assertNotNull(wsHandler);
		assertThat(wsHandler, Matchers.instanceOf(SubProtocolWebSocketHandler.class));
		assertNotNull(sockJsHttpRequestHandler.getSockJsService());
		assertThat(sockJsHttpRequestHandler.getSockJsService(), Matchers.instanceOf(DefaultSockJsService.class));

		DefaultSockJsService defaultSockJsService = (DefaultSockJsService) sockJsHttpRequestHandler.getSockJsService();
		WebSocketTransportHandler wsTransportHandler = (WebSocketTransportHandler) defaultSockJsService
				.getTransportHandlers().get(TransportType.WEBSOCKET);
		assertNotNull(wsTransportHandler.getHandshakeHandler());
		assertThat(wsTransportHandler.getHandshakeHandler(), Matchers.instanceOf(TestHandshakeHandler.class));
		assertFalse(defaultSockJsService.shouldSuppressCors());

		ThreadPoolTaskScheduler scheduler = (ThreadPoolTaskScheduler) defaultSockJsService.getTaskScheduler();
		assertEquals(Runtime.getRuntime().availableProcessors(), scheduler.getScheduledThreadPoolExecutor().getCorePoolSize());
		assertTrue(scheduler.getScheduledThreadPoolExecutor().getRemoveOnCancelPolicy());

		interceptors = defaultSockJsService.getHandshakeInterceptors();
		assertThat(interceptors, contains(instanceOf(FooTestInterceptor.class),
				instanceOf(BarTestInterceptor.class), instanceOf(OriginHandshakeInterceptor.class)));
		assertEquals(Arrays.asList("http://mydomain3.com", "http://mydomain4.com"), defaultSockJsService.getAllowedOrigins());

		SimpUserRegistry userRegistry = this.appContext.getBean(SimpUserRegistry.class);
		assertNotNull(userRegistry);
		assertEquals(DefaultSimpUserRegistry.class, userRegistry.getClass());

		UserDestinationResolver userDestResolver = this.appContext.getBean(UserDestinationResolver.class);
		assertNotNull(userDestResolver);
		assertThat(userDestResolver, Matchers.instanceOf(DefaultUserDestinationResolver.class));
		DefaultUserDestinationResolver defaultUserDestResolver = (DefaultUserDestinationResolver) userDestResolver;
		assertEquals("/personal/", defaultUserDestResolver.getDestinationPrefix());

		UserDestinationMessageHandler userDestHandler = this.appContext.getBean(UserDestinationMessageHandler.class);
		assertNotNull(userDestHandler);

		SimpleBrokerMessageHandler brokerMessageHandler = this.appContext.getBean(SimpleBrokerMessageHandler.class);
		assertNotNull(brokerMessageHandler);
		Collection<String> prefixes = brokerMessageHandler.getDestinationPrefixes();
		assertEquals(Arrays.asList("/topic", "/queue"), new ArrayList<String>(prefixes));
		assertNotNull(brokerMessageHandler.getTaskScheduler());
		assertArrayEquals(new long[] {15000, 15000}, brokerMessageHandler.getHeartbeatValue());

		List<Class<? extends MessageHandler>> subscriberTypes =
				Arrays.<Class<? extends MessageHandler>>asList(SimpAnnotationMethodMessageHandler.class,
						UserDestinationMessageHandler.class, SimpleBrokerMessageHandler.class);
		testChannel("clientInboundChannel", subscriberTypes, 2);
		testExecutor("clientInboundChannel", Runtime.getRuntime().availableProcessors() * 2, Integer.MAX_VALUE, 60);

		subscriberTypes = Collections.singletonList(SubProtocolWebSocketHandler.class);
		testChannel("clientOutboundChannel", subscriberTypes, 1);
		testExecutor("clientOutboundChannel", Runtime.getRuntime().availableProcessors() * 2, Integer.MAX_VALUE, 60);

		subscriberTypes = Arrays.<Class<? extends MessageHandler>>asList(
				SimpleBrokerMessageHandler.class, UserDestinationMessageHandler.class);
		testChannel("brokerChannel", subscriberTypes, 1);
		try {
			this.appContext.getBean("brokerChannelExecutor", ThreadPoolTaskExecutor.class);
			fail("expected exception");
		}
		catch (NoSuchBeanDefinitionException ex) {
			// expected
		}

		assertNotNull(this.appContext.getBean("webSocketScopeConfigurer", CustomScopeConfigurer.class));

		DirectFieldAccessor subscriptionRegistryAccessor = new DirectFieldAccessor(brokerMessageHandler.getSubscriptionRegistry());
		String pathSeparator = (String)new DirectFieldAccessor(subscriptionRegistryAccessor.getPropertyValue("pathMatcher")).getPropertyValue("pathSeparator");
		assertEquals(".", pathSeparator);
	}

	@Test
	public void stompBrokerRelay() {
		loadBeanDefinitions("websocket-config-broker-relay.xml");

		HandlerMapping hm = this.appContext.getBean(HandlerMapping.class);
		assertNotNull(hm);
		assertThat(hm, Matchers.instanceOf(SimpleUrlHandlerMapping.class));

		SimpleUrlHandlerMapping suhm = (SimpleUrlHandlerMapping) hm;
		assertThat(suhm.getUrlMap().keySet(), Matchers.hasSize(1));
		assertThat(suhm.getUrlMap().values(), Matchers.hasSize(1));
		assertEquals(2, suhm.getOrder());

		HttpRequestHandler httpRequestHandler = (HttpRequestHandler) suhm.getUrlMap().get("/foo/**");
		assertNotNull(httpRequestHandler);
		assertThat(httpRequestHandler, Matchers.instanceOf(SockJsHttpRequestHandler.class));
		SockJsHttpRequestHandler sockJsHttpRequestHandler = (SockJsHttpRequestHandler) httpRequestHandler;
		WebSocketHandler wsHandler = unwrapWebSocketHandler(sockJsHttpRequestHandler.getWebSocketHandler());
		assertNotNull(wsHandler);
		assertThat(wsHandler, Matchers.instanceOf(SubProtocolWebSocketHandler.class));
		assertNotNull(sockJsHttpRequestHandler.getSockJsService());

		UserDestinationResolver userDestResolver = this.appContext.getBean(UserDestinationResolver.class);
		assertNotNull(userDestResolver);
		assertThat(userDestResolver, Matchers.instanceOf(DefaultUserDestinationResolver.class));
		DefaultUserDestinationResolver defaultUserDestResolver = (DefaultUserDestinationResolver) userDestResolver;
		assertEquals("/user/", defaultUserDestResolver.getDestinationPrefix());

		StompBrokerRelayMessageHandler messageBroker = this.appContext.getBean(StompBrokerRelayMessageHandler.class);
		assertNotNull(messageBroker);
		assertEquals("clientlogin", messageBroker.getClientLogin());
		assertEquals("clientpass", messageBroker.getClientPasscode());
		assertEquals("syslogin", messageBroker.getSystemLogin());
		assertEquals("syspass", messageBroker.getSystemPasscode());
		assertEquals("relayhost", messageBroker.getRelayHost());
		assertEquals(1234, messageBroker.getRelayPort());
		assertEquals("spring.io", messageBroker.getVirtualHost());
		assertEquals(5000, messageBroker.getSystemHeartbeatReceiveInterval());
		assertEquals(5000, messageBroker.getSystemHeartbeatSendInterval());
		assertThat(messageBroker.getDestinationPrefixes(), Matchers.containsInAnyOrder("/topic","/queue"));

		List<Class<? extends MessageHandler>> subscriberTypes =
				Arrays.<Class<? extends MessageHandler>>asList(SimpAnnotationMethodMessageHandler.class,
						UserDestinationMessageHandler.class, StompBrokerRelayMessageHandler.class);
		testChannel("clientInboundChannel", subscriberTypes, 2);
		testExecutor("clientInboundChannel", Runtime.getRuntime().availableProcessors() * 2, Integer.MAX_VALUE, 60);

		subscriberTypes = Collections.singletonList(SubProtocolWebSocketHandler.class);
		testChannel("clientOutboundChannel", subscriberTypes, 1);
		testExecutor("clientOutboundChannel", Runtime.getRuntime().availableProcessors() * 2, Integer.MAX_VALUE, 60);

		subscriberTypes = Arrays.<Class<? extends MessageHandler>>asList(
				StompBrokerRelayMessageHandler.class, UserDestinationMessageHandler.class);
		testChannel("brokerChannel", subscriberTypes, 1);
		try {
			this.appContext.getBean("brokerChannelExecutor", ThreadPoolTaskExecutor.class);
			fail("expected exception");
		}
		catch (NoSuchBeanDefinitionException ex) {
			// expected
		}

		String destination = "/topic/unresolved-user-destination";
		UserDestinationMessageHandler userDestHandler = this.appContext.getBean(UserDestinationMessageHandler.class);
		assertEquals(destination, userDestHandler.getBroadcastDestination());
		assertNotNull(messageBroker.getSystemSubscriptions());
		assertSame(userDestHandler, messageBroker.getSystemSubscriptions().get(destination));

		destination = "/topic/simp-user-registry";
		UserRegistryMessageHandler userRegistryHandler = this.appContext.getBean(UserRegistryMessageHandler.class);
		assertEquals(destination, userRegistryHandler.getBroadcastDestination());
		assertNotNull(messageBroker.getSystemSubscriptions());
		assertSame(userRegistryHandler, messageBroker.getSystemSubscriptions().get(destination));

		SimpUserRegistry userRegistry = this.appContext.getBean(SimpUserRegistry.class);
		assertEquals(MultiServerUserRegistry.class, userRegistry.getClass());

		String name = "webSocketMessageBrokerStats";
		WebSocketMessageBrokerStats stats = this.appContext.getBean(name, WebSocketMessageBrokerStats.class);
		String actual = stats.toString();
		String expected = "WebSocketSession\\[0 current WS\\(0\\)-HttpStream\\(0\\)-HttpPoll\\(0\\), " +
				"0 total, 0 closed abnormally \\(0 connect failure, 0 send limit, 0 transport error\\)\\], " +
				"stompSubProtocol\\[processed CONNECT\\(0\\)-CONNECTED\\(0\\)-DISCONNECT\\(0\\)\\], " +
				"stompBrokerRelay\\[0 sessions, relayhost:1234 \\(not available\\), processed CONNECT\\(0\\)-CONNECTED\\(0\\)-DISCONNECT\\(0\\)\\], " +
				"inboundChannel\\[pool size = \\d, active threads = \\d, queued tasks = \\d, completed tasks = \\d\\], " +
				"outboundChannelpool size = \\d, active threads = \\d, queued tasks = \\d, completed tasks = \\d\\], " +
				"sockJsScheduler\\[pool size = \\d, active threads = \\d, queued tasks = \\d, completed tasks = \\d\\]";

		assertTrue("\nExpected: " + expected.replace("\\", "") + "\n  Actual: " + actual, actual.matches(expected));
	}

	@Test
	public void annotationMethodMessageHandler() {
		loadBeanDefinitions("websocket-config-broker-simple.xml");

		SimpAnnotationMethodMessageHandler annotationMethodMessageHandler =
				this.appContext.getBean(SimpAnnotationMethodMessageHandler.class);

		assertNotNull(annotationMethodMessageHandler);
		MessageConverter messageConverter = annotationMethodMessageHandler.getMessageConverter();
		assertNotNull(messageConverter);
		assertTrue(messageConverter instanceof CompositeMessageConverter);

		CompositeMessageConverter compositeMessageConverter = this.appContext.getBean(CompositeMessageConverter.class);
		assertNotNull(compositeMessageConverter);

		SimpMessagingTemplate simpMessagingTemplate = this.appContext.getBean(SimpMessagingTemplate.class);
		assertNotNull(simpMessagingTemplate);
		assertEquals("/personal/", simpMessagingTemplate.getUserDestinationPrefix());

		List<MessageConverter> converters = compositeMessageConverter.getConverters();
		assertThat(converters.size(), Matchers.is(3));
		assertThat(converters.get(0), Matchers.instanceOf(StringMessageConverter.class));
		assertThat(converters.get(1), Matchers.instanceOf(ByteArrayMessageConverter.class));
		assertThat(converters.get(2), Matchers.instanceOf(MappingJackson2MessageConverter.class));

		ContentTypeResolver resolver = ((MappingJackson2MessageConverter) converters.get(2)).getContentTypeResolver();
		assertEquals(MimeTypeUtils.APPLICATION_JSON, ((DefaultContentTypeResolver) resolver).getDefaultMimeType());

		DirectFieldAccessor handlerAccessor = new DirectFieldAccessor(annotationMethodMessageHandler);
		String pathSeparator = (String)new DirectFieldAccessor(handlerAccessor.getPropertyValue("pathMatcher")).getPropertyValue("pathSeparator");
		assertEquals(".", pathSeparator);
	}

	@Test
	public void customChannels() {
		loadBeanDefinitions("websocket-config-broker-customchannels.xml");

		List<Class<? extends MessageHandler>> subscriberTypes =
				Arrays.<Class<? extends MessageHandler>>asList(SimpAnnotationMethodMessageHandler.class,
						UserDestinationMessageHandler.class, SimpleBrokerMessageHandler.class);

		testChannel("clientInboundChannel", subscriberTypes, 3);
		testExecutor("clientInboundChannel", 100, 200, 600);

		subscriberTypes = Collections.singletonList(SubProtocolWebSocketHandler.class);

		testChannel("clientOutboundChannel", subscriberTypes, 3);
		testExecutor("clientOutboundChannel", 101, 201, 601);

		subscriberTypes = Arrays.<Class<? extends MessageHandler>>asList(SimpleBrokerMessageHandler.class,
				UserDestinationMessageHandler.class);

		testChannel("brokerChannel", subscriberTypes, 1);
		testExecutor("brokerChannel", 102, 202, 602);
	}

	// SPR-11623

	@Test
	public void customChannelsWithDefaultExecutor() {
		loadBeanDefinitions("websocket-config-broker-customchannels-default-executor.xml");

		testExecutor("clientInboundChannel", Runtime.getRuntime().availableProcessors() * 2, Integer.MAX_VALUE, 60);
		testExecutor("clientOutboundChannel", Runtime.getRuntime().availableProcessors() * 2, Integer.MAX_VALUE, 60);
		assertFalse(this.appContext.containsBean("brokerChannelExecutor"));
	}

	@Test
	public void customArgumentAndReturnValueTypes() {
		loadBeanDefinitions("websocket-config-broker-custom-argument-and-return-value-types.xml");

		SimpAnnotationMethodMessageHandler handler = this.appContext.getBean(SimpAnnotationMethodMessageHandler.class);

		List<HandlerMethodArgumentResolver> customResolvers = handler.getCustomArgumentResolvers();
		assertEquals(2, customResolvers.size());
		assertTrue(handler.getArgumentResolvers().contains(customResolvers.get(0)));
		assertTrue(handler.getArgumentResolvers().contains(customResolvers.get(1)));

		List<HandlerMethodReturnValueHandler> customHandlers = handler.getCustomReturnValueHandlers();
		assertEquals(2, customHandlers.size());
		assertTrue(handler.getReturnValueHandlers().contains(customHandlers.get(0)));
		assertTrue(handler.getReturnValueHandlers().contains(customHandlers.get(1)));
	}

	@Test
	public void messageConverters() {
		loadBeanDefinitions("websocket-config-broker-converters.xml");

		CompositeMessageConverter compositeConverter = this.appContext.getBean(CompositeMessageConverter.class);
		assertNotNull(compositeConverter);

		assertEquals(4, compositeConverter.getConverters().size());
		assertEquals(StringMessageConverter.class, compositeConverter.getConverters().iterator().next().getClass());
	}

	@Test
	public void messageConvertersDefaultsOff() {
		loadBeanDefinitions("websocket-config-broker-converters-defaults-off.xml");

		CompositeMessageConverter compositeConverter = this.appContext.getBean(CompositeMessageConverter.class);
		assertNotNull(compositeConverter);

		assertEquals(1, compositeConverter.getConverters().size());
		assertEquals(StringMessageConverter.class, compositeConverter.getConverters().iterator().next().getClass());
	}


	private void testChannel(String channelName, List<Class<? extends  MessageHandler>> subscriberTypes,
			int interceptorCount) {

		AbstractSubscribableChannel channel = this.appContext.getBean(channelName, AbstractSubscribableChannel.class);

		for (Class<? extends  MessageHandler> subscriberType : subscriberTypes) {
			MessageHandler subscriber = this.appContext.getBean(subscriberType);
			assertNotNull("No subsription for " + subscriberType, subscriber);
			assertTrue(channel.hasSubscription(subscriber));
		}

		List<ChannelInterceptor> interceptors = channel.getInterceptors();
		assertEquals(interceptorCount, interceptors.size());
		assertEquals(ImmutableMessageChannelInterceptor.class, interceptors.get(interceptors.size()-1).getClass());
	}

	private void testExecutor(String channelName, int corePoolSize, int maxPoolSize, int keepAliveSeconds) {

		ThreadPoolTaskExecutor taskExecutor =
				this.appContext.getBean(channelName + "Executor", ThreadPoolTaskExecutor.class);

		assertEquals(corePoolSize, taskExecutor.getCorePoolSize());
		assertEquals(maxPoolSize, taskExecutor.getMaxPoolSize());
		assertEquals(keepAliveSeconds, taskExecutor.getKeepAliveSeconds());
	}

	private void loadBeanDefinitions(String fileName) {
		XmlBeanDefinitionReader reader = new XmlBeanDefinitionReader(this.appContext);
		ClassPathResource resource = new ClassPathResource(fileName, MessageBrokerBeanDefinitionParserTests.class);
		reader.loadBeanDefinitions(resource);
		this.appContext.refresh();
	}

	private WebSocketHandler unwrapWebSocketHandler(WebSocketHandler handler) {
		return (handler instanceof WebSocketHandlerDecorator) ?
				((WebSocketHandlerDecorator) handler).getLastHandler() : handler;
	}

}

class CustomArgumentResolver implements HandlerMethodArgumentResolver {

	@Override
	public boolean supportsParameter(MethodParameter parameter) {
		return false;
	}

	@Override
	public Object resolveArgument(MethodParameter parameter, Message<?> message) throws Exception {
		return null;
	}
}

class CustomReturnValueHandler implements HandlerMethodReturnValueHandler {

	@Override
	public boolean supportsReturnType(MethodParameter returnType) {
		return false;
	}

	@Override
	public void handleReturnValue(Object returnValue, MethodParameter returnType, Message<?> message) throws Exception {

	}
}

class TestWebSocketHandlerDecoratorFactory implements WebSocketHandlerDecoratorFactory {

	@Override
	public WebSocketHandler decorate(WebSocketHandler handler) {
		return new WebSocketHandlerDecorator(handler) {
			@Override
			public void afterConnectionEstablished(WebSocketSession session) throws Exception {
				session.getAttributes().put("decorated", true);
				super.afterConnectionEstablished(session);
			}
		};
	}
}

class TestStompErrorHandler extends StompSubProtocolErrorHandler {

}