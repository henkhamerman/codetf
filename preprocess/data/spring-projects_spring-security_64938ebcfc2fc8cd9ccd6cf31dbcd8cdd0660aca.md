Refactoring Types: ['Extract Method']
gframework/security/config/annotation/web/messaging/MessageSecurityMetadataSourceRegistry.java
/*
 * Copyright 2002-2014 the original author or authors.
 *
 * Licensed under the Apache License, Version 2.0 (the "License"); you may not
 * use this file except in compliance with the License. You may obtain a copy of
 * the License at
 *
 * http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
 * WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
 * License for the specific language governing permissions and limitations under
 * the License.
 */
package org.springframework.security.config.annotation.web.messaging;

import org.springframework.messaging.Message;
import org.springframework.messaging.simp.SimpMessageType;
import org.springframework.security.config.annotation.web.configurers.RememberMeConfigurer;
import org.springframework.security.messaging.access.expression.ExpressionBasedMessageSecurityMetadataSourceFactory;
import org.springframework.security.messaging.access.intercept.MessageSecurityMetadataSource;
import org.springframework.security.messaging.util.matcher.MessageMatcher;
import org.springframework.security.messaging.util.matcher.SimpDestinationMessageMatcher;
import org.springframework.security.messaging.util.matcher.SimpMessageTypeMatcher;
import org.springframework.util.AntPathMatcher;
import org.springframework.util.Assert;
import org.springframework.util.PathMatcher;
import org.springframework.util.StringUtils;

import java.util.*;

/**
 * Allows mapping security constraints using {@link MessageMatcher} to the security
 * expressions.
 *
 * @since 4.0
 * @author Rob Winch
 */
public class MessageSecurityMetadataSourceRegistry {
	private static final String permitAll = "permitAll";
	private static final String denyAll = "denyAll";
	private static final String anonymous = "anonymous";
	private static final String authenticated = "authenticated";
	private static final String fullyAuthenticated = "fullyAuthenticated";
	private static final String rememberMe = "rememberMe";

	private final LinkedHashMap<MatcherBuilder, String> matcherToExpression = new LinkedHashMap<MatcherBuilder, String>();

	private DelegatingPathMatcher pathMatcher = new DelegatingPathMatcher();

	private boolean defaultPathMatcher = true;

	/**
	 * Maps any {@link Message} to a security expression.
	 *
	 * @return the Expression to associate
	 */
	public Constraint anyMessage() {
		return matchers(MessageMatcher.ANY_MESSAGE);
	}

	/**
	 * Maps any {@link Message} that has a null SimpMessageHeaderAccessor destination
	 * header (i.e. CONNECT, CONNECT_ACK, HEARTBEAT, UNSUBSCRIBE, DISCONNECT,
	 * DISCONNECT_ACK, OTHER)
	 *
	 * @return the Expression to associate
	 */
	public Constraint nullDestMatcher() {
		return matchers(SimpDestinationMessageMatcher.NULL_DESTINATION_MATCHER);
	}

	/**
	 * Maps a {@link List} of {@link SimpDestinationMessageMatcher} instances.
	 *
	 * @param typesToMatch the {@link SimpMessageType} instance to match on
	 * @return the {@link Constraint} associated to the matchers.
	 */
	public Constraint simpTypeMatchers(SimpMessageType... typesToMatch) {
		MessageMatcher<?>[] typeMatchers = new MessageMatcher<?>[typesToMatch.length];
		for (int i = 0; i < typesToMatch.length; i++) {
			SimpMessageType typeToMatch = typesToMatch[i];
			typeMatchers[i] = new SimpMessageTypeMatcher(typeToMatch);
		}
		return matchers(typeMatchers);
	}

	/**
	 * Maps a {@link List} of {@link SimpDestinationMessageMatcher} instances without
	 * regard to the {@link SimpMessageType}. If no destination is found on the Message,
	 * then the Matcher returns false.
	 *
	 * @param patterns the patterns to create
	 * {@link org.springframework.security.messaging.util.matcher.SimpDestinationMessageMatcher}
	 * from. Uses
	 * {@link MessageSecurityMetadataSourceRegistry#simpDestPathMatcher(PathMatcher)} .
	 *
	 * @return the {@link Constraint} that is associated to the {@link MessageMatcher}
	 * @see {@link MessageSecurityMetadataSourceRegistry#simpDestPathMatcher(PathMatcher)}
	 */
	public Constraint simpDestMatchers(String... patterns) {
		return simpDestMatchers(null, patterns);
	}

	/**
	 * Maps a {@link List} of {@link SimpDestinationMessageMatcher} instances that match
	 * on {@code SimpMessageType.MESSAGE}. If no destination is found on the Message, then
	 * the Matcher returns false.
	 *
	 * @param patterns the patterns to create
	 * {@link org.springframework.security.messaging.util.matcher.SimpDestinationMessageMatcher}
	 * from. Uses
	 * {@link MessageSecurityMetadataSourceRegistry#simpDestPathMatcher(PathMatcher)}.
	 *
	 * @return the {@link Constraint} that is associated to the {@link MessageMatcher}
	 * @see {@link MessageSecurityMetadataSourceRegistry#simpDestPathMatcher(PathMatcher)}
	 */
	public Constraint simpMessageDestMatchers(String... patterns) {
		return simpDestMatchers(SimpMessageType.MESSAGE, patterns);
	}

	/**
	 * Maps a {@link List} of {@link SimpDestinationMessageMatcher} instances that match
	 * on {@code SimpMessageType.SUBSCRIBE}. If no destination is found on the Message,
	 * then the Matcher returns false.
	 *
	 * @param patterns the patterns to create
	 * {@link org.springframework.security.messaging.util.matcher.SimpDestinationMessageMatcher}
	 * from. Uses
	 * {@link MessageSecurityMetadataSourceRegistry#simpDestPathMatcher(PathMatcher)}.
	 *
	 * @return the {@link Constraint} that is associated to the {@link MessageMatcher}
	 * @see {@link MessageSecurityMetadataSourceRegistry#simpDestPathMatcher(PathMatcher)}
	 */
	public Constraint simpSubscribeDestMatchers(String... patterns) {
		return simpDestMatchers(SimpMessageType.SUBSCRIBE, patterns);
	}

	/**
	 * Maps a {@link List} of {@link SimpDestinationMessageMatcher} instances. If no
	 * destination is found on the Message, then the Matcher returns false.
	 *
	 * @param type the {@link SimpMessageType} to match on. If null, the
	 * {@link SimpMessageType} is not considered for matching.
	 * @param patterns the patterns to create
	 * {@link org.springframework.security.messaging.util.matcher.SimpDestinationMessageMatcher}
	 * from. Uses
	 * {@link MessageSecurityMetadataSourceRegistry#simpDestPathMatcher(PathMatcher)}.
	 *
	 * @return the {@link Constraint} that is associated to the {@link MessageMatcher}
	 * @see {@link MessageSecurityMetadataSourceRegistry#simpDestPathMatcher(PathMatcher)}
	 */
	private Constraint simpDestMatchers(SimpMessageType type, String... patterns) {
		List<MatcherBuilder> matchers = new ArrayList<MatcherBuilder>(patterns.length);
		for (String pattern : patterns) {
			matchers.add(new PathMatcherMessageMatcherBuilder(pattern, type));
		}
		return new Constraint(matchers);
	}

	/**
	 * The {@link PathMatcher} to be used with the
	 * {@link MessageSecurityMetadataSourceRegistry#simpDestMatchers(String...)}. The
	 * default is to use the default constructor of {@link AntPathMatcher}.
	 *
	 * @param pathMatcher the {@link PathMatcher} to use. Cannot be null.
	 * @return the {@link MessageSecurityMetadataSourceRegistry} for further
	 * customization.
	 */
	public MessageSecurityMetadataSourceRegistry simpDestPathMatcher(
			PathMatcher pathMatcher) {
		Assert.notNull(pathMatcher, "pathMatcher cannot be null");
		this.pathMatcher.setPathMatcher(pathMatcher);
		this.defaultPathMatcher = false;
		return this;
	}

	/**
	 * Determines if the {@link #simpDestPathMatcher(PathMatcher)} has been explicitly set.
	 *
	 * @return true if {@link #simpDestPathMatcher(PathMatcher)} has been explicitly set, else false.
	 */
	protected boolean isSimpDestPathMatcherConfigured() {
		return !this.defaultPathMatcher;
	}

	/**
	 * Maps a {@link List} of {@link MessageMatcher} instances to a security expression.
	 *
	 * @param matchers the {@link MessageMatcher} instances to map.
	 * @return The {@link Constraint} that is associated to the {@link MessageMatcher}
	 * instances
	 */
	public Constraint matchers(MessageMatcher<?>... matchers) {
		List<MatcherBuilder> builders = new ArrayList<MatcherBuilder>(matchers.length);
		for (MessageMatcher<?> matcher : matchers) {
			builders.add(new PreBuiltMatcherBuilder(matcher));
		}
		return new Constraint(builders);
	}

	/**
	 * Allows subclasses to create creating a {@link MessageSecurityMetadataSource}.
	 *
	 * <p>
	 * This is not exposed so as not to confuse users of the API, which should never
	 * invoke this method.
	 * </p>
	 *
	 * @return the {@link MessageSecurityMetadataSource} to use
	 */
	protected MessageSecurityMetadataSource createMetadataSource() {
		LinkedHashMap<MessageMatcher<?>, String> matcherToExpression = new LinkedHashMap<MessageMatcher<?>, String>();
		for (Map.Entry<MatcherBuilder, String> entry : this.matcherToExpression
				.entrySet()) {
			matcherToExpression.put(entry.getKey().build(), entry.getValue());
		}
		return ExpressionBasedMessageSecurityMetadataSourceFactory
				.createExpressionMessageMetadataSource(matcherToExpression);
	}

	/**
	 * Allows determining if a mapping was added.
	 *
	 * <p>
	 * This is not exposed so as not to confuse users of the API, which should never need
	 * to invoke this method.
	 * </p>
	 *
	 * @return true if a mapping was added, else false
	 */
	protected boolean containsMapping() {
		return !this.matcherToExpression.isEmpty();
	}

	/**
	 * Represents the security constraint to be applied to the {@link MessageMatcher}
	 * instances.
	 */
	public class Constraint {
		private final List<? extends MatcherBuilder> messageMatchers;

		/**
		 * Creates a new instance
		 *
		 * @param messageMatchers the {@link MessageMatcher} instances to map to this
		 * constraint
		 */
		private Constraint(List<? extends MatcherBuilder> messageMatchers) {
			Assert.notEmpty(messageMatchers, "messageMatchers cannot be null or empty");
			this.messageMatchers = messageMatchers;
		}

		/**
		 * Shortcut for specifying {@link Message} instances require a particular role. If
		 * you do not want to have "ROLE_" automatically inserted see
		 * {@link #hasAuthority(String)}.
		 *
		 * @param role the role to require (i.e. USER, ADMIN, etc). Note, it should not
		 * start with "ROLE_" as this is automatically inserted.
		 * @return the {@link MessageSecurityMetadataSourceRegistry} for further
		 * customization
		 */
		public MessageSecurityMetadataSourceRegistry hasRole(String role) {
			return access(MessageSecurityMetadataSourceRegistry.hasRole(role));
		}

		/**
		 * Shortcut for specifying {@link Message} instances require any of a number of
		 * roles. If you do not want to have "ROLE_" automatically inserted see
		 * {@link #hasAnyAuthority(String...)}
		 *
		 * @param roles the roles to require (i.e. USER, ADMIN, etc). Note, it should not
		 * start with "ROLE_" as this is automatically inserted.
		 * @return the {@link MessageSecurityMetadataSourceRegistry} for further
		 * customization
		 */
		public MessageSecurityMetadataSourceRegistry hasAnyRole(String... roles) {
			return access(MessageSecurityMetadataSourceRegistry.hasAnyRole(roles));
		}

		/**
		 * Specify that {@link Message} instances require a particular authority.
		 *
		 * @param authority the authority to require (i.e. ROLE_USER, ROLE_ADMIN, etc).
		 * @return the {@link MessageSecurityMetadataSourceRegistry} for further
		 * customization
		 */
		public MessageSecurityMetadataSourceRegistry hasAuthority(String authority) {
			return access(MessageSecurityMetadataSourceRegistry.hasAuthority(authority));
		}

		/**
		 * Specify that {@link Message} instances requires any of a number authorities.
		 *
		 * @param authorities the requests require at least one of the authorities (i.e.
		 * "ROLE_USER","ROLE_ADMIN" would mean either "ROLE_USER" or "ROLE_ADMIN" is
		 * required).
		 * @return the {@link MessageSecurityMetadataSourceRegistry} for further
		 * customization
		 */
		public MessageSecurityMetadataSourceRegistry hasAnyAuthority(
				String... authorities) {
			return access(MessageSecurityMetadataSourceRegistry
					.hasAnyAuthority(authorities));
		}

		/**
		 * Specify that Messages are allowed by anyone.
		 *
		 * @return the {@link MessageSecurityMetadataSourceRegistry} for further
		 * customization
		 */
		public MessageSecurityMetadataSourceRegistry permitAll() {
			return access(permitAll);
		}

		/**
		 * Specify that Messages are allowed by anonymous users.
		 *
		 * @return the {@link MessageSecurityMetadataSourceRegistry} for further
		 * customization
		 */
		public MessageSecurityMetadataSourceRegistry anonymous() {
			return access(anonymous);
		}

		/**
		 * Specify that Messages are allowed by users that have been remembered.
		 *
		 * @return the {@link MessageSecurityMetadataSourceRegistry} for further
		 * customization
		 * @see {@link RememberMeConfigurer}
		 */
		public MessageSecurityMetadataSourceRegistry rememberMe() {
			return access(rememberMe);
		}

		/**
		 * Specify that Messages are not allowed by anyone.
		 *
		 * @return the {@link MessageSecurityMetadataSourceRegistry} for further
		 * customization
		 */
		public MessageSecurityMetadataSourceRegistry denyAll() {
			return access(denyAll);
		}

		/**
		 * Specify that Messages are allowed by any authenticated user.
		 *
		 * @return the {@link MessageSecurityMetadataSourceRegistry} for further
		 * customization
		 */
		public MessageSecurityMetadataSourceRegistry authenticated() {
			return access(authenticated);
		}

		/**
		 * Specify that Messages are allowed by users who have authenticated and were not
		 * "remembered".
		 *
		 * @return the {@link MessageSecurityMetadataSourceRegistry} for further
		 * customization
		 * @see {@link RememberMeConfigurer}
		 */
		public MessageSecurityMetadataSourceRegistry fullyAuthenticated() {
			return access(fullyAuthenticated);
		}

		/**
		 * Allows specifying that Messages are secured by an arbitrary expression
		 *
		 * @param attribute the expression to secure the URLs (i.e.
		 * "hasRole('ROLE_USER') and hasRole('ROLE_SUPER')")
		 * @return the {@link MessageSecurityMetadataSourceRegistry} for further
		 * customization
		 */
		public MessageSecurityMetadataSourceRegistry access(String attribute) {
			for (MatcherBuilder messageMatcher : messageMatchers) {
				matcherToExpression.put(messageMatcher, attribute);
			}
			return MessageSecurityMetadataSourceRegistry.this;
		}
	}

	private static String hasAnyRole(String... authorities) {
		String anyAuthorities = StringUtils.arrayToDelimitedString(authorities,
				"','ROLE_");
		return "hasAnyRole('ROLE_" + anyAuthorities + "')";
	}

	private static String hasRole(String role) {
		Assert.notNull(role, "role cannot be null");
		if (role.startsWith("ROLE_")) {
			throw new IllegalArgumentException(
					"role should not start with 'ROLE_' since it is automatically inserted. Got '"
							+ role + "'");
		}
		return "hasRole('ROLE_" + role + "')";
	}

	private static String hasAuthority(String authority) {
		return "hasAuthority('" + authority + "')";
	}

	private static String hasAnyAuthority(String... authorities) {
		String anyAuthorities = StringUtils.arrayToDelimitedString(authorities, "','");
		return "hasAnyAuthority('" + anyAuthorities + "')";
	}

	private static class PreBuiltMatcherBuilder implements MatcherBuilder {
		private MessageMatcher<?> matcher;

		private PreBuiltMatcherBuilder(MessageMatcher<?> matcher) {
			this.matcher = matcher;
		}

		public MessageMatcher<?> build() {
			return matcher;
		}
	}

	private class PathMatcherMessageMatcherBuilder implements MatcherBuilder {
		private final String pattern;
		private final SimpMessageType type;

		private PathMatcherMessageMatcherBuilder(String pattern, SimpMessageType type) {
			this.pattern = pattern;
			this.type = type;
		}

		public MessageMatcher<?> build() {
			if (type == null) {
				return new SimpDestinationMessageMatcher(pattern, pathMatcher);
			}
			else if (SimpMessageType.MESSAGE == type) {
				return SimpDestinationMessageMatcher.createMessageMatcher(pattern,
						pathMatcher);
			}
			else if (SimpMessageType.SUBSCRIBE == type) {
				return SimpDestinationMessageMatcher.createSubscribeMatcher(pattern,
						pathMatcher);
			}
			throw new IllegalStateException(type
					+ " is not supported since it does not have a destination");
		}
	}

	private interface MatcherBuilder {
		MessageMatcher<?> build();
	}


	static class DelegatingPathMatcher implements PathMatcher {

		private PathMatcher delegate = new AntPathMatcher();

		public boolean isPattern(String path) {
			return delegate.isPattern(path);
		}

		public boolean match(String pattern, String path) {
			return delegate.match(pattern, path);
		}

		public boolean matchStart(String pattern, String path) {
			return delegate.matchStart(pattern, path);
		}

		public String extractPathWithinPattern(String pattern, String path) {
			return delegate.extractPathWithinPattern(pattern, path);
		}

		public Map<String, String> extractUriTemplateVariables(String pattern, String path) {
			return delegate.extractUriTemplateVariables(pattern, path);
		}

		public Comparator<String> getPatternComparator(String path) {
			return delegate.getPatternComparator(path);
		}

		public String combine(String pattern1, String pattern2) {
			return delegate.combine(pattern1, pattern2);
		}

		void setPathMatcher(PathMatcher pathMatcher) {
			this.delegate = pathMatcher;
		}
	}
}


File: config/src/main/java/org/springframework/security/config/annotation/web/socket/AbstractSecurityWebSocketMessageBrokerConfigurer.java
/*
 * Copyright 2002-2014 the original author or authors.
 *
 * Licensed under the Apache License, Version 2.0 (the "License"); you may not
 * use this file except in compliance with the License. You may obtain a copy of
 * the License at
 *
 * http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
 * WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
 * License for the specific language governing permissions and limitations under
 * the License.
 */
package org.springframework.security.config.annotation.web.socket;

import java.util.ArrayList;
import java.util.List;
import java.util.Map;

import org.springframework.beans.factory.NoSuchBeanDefinitionException;
import org.springframework.beans.factory.SmartInitializingSingleton;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.context.ApplicationContext;
import org.springframework.context.annotation.Bean;
import org.springframework.core.Ordered;
import org.springframework.core.annotation.Order;
import org.springframework.messaging.handler.invocation.HandlerMethodArgumentResolver;
import org.springframework.messaging.simp.annotation.support.SimpAnnotationMethodMessageHandler;
import org.springframework.messaging.simp.config.ChannelRegistration;
import org.springframework.security.access.AccessDecisionVoter;
import org.springframework.security.access.vote.AffirmativeBased;
import org.springframework.security.config.annotation.web.messaging.MessageSecurityMetadataSourceRegistry;
import org.springframework.security.messaging.access.expression.MessageExpressionVoter;
import org.springframework.security.messaging.access.intercept.ChannelSecurityInterceptor;
import org.springframework.security.messaging.access.intercept.MessageSecurityMetadataSource;
import org.springframework.security.messaging.context.AuthenticationPrincipalArgumentResolver;
import org.springframework.security.messaging.context.SecurityContextChannelInterceptor;
import org.springframework.security.messaging.web.csrf.CsrfChannelInterceptor;
import org.springframework.security.messaging.web.socket.server.CsrfTokenHandshakeInterceptor;
import org.springframework.util.AntPathMatcher;
import org.springframework.util.PathMatcher;
import org.springframework.web.servlet.handler.SimpleUrlHandlerMapping;
import org.springframework.web.socket.config.annotation.AbstractWebSocketMessageBrokerConfigurer;
import org.springframework.web.socket.config.annotation.StompEndpointRegistry;
import org.springframework.web.socket.server.HandshakeInterceptor;
import org.springframework.web.socket.server.support.WebSocketHttpRequestHandler;
import org.springframework.web.socket.sockjs.SockJsService;
import org.springframework.web.socket.sockjs.support.SockJsHttpRequestHandler;
import org.springframework.web.socket.sockjs.transport.TransportHandlingSockJsService;

/**
 * Allows configuring WebSocket Authorization.
 *
 * <p>
 * For example:
 * </p>
 *
 * <pre>
 * &#064;Configuration
 * public class WebSocketSecurityConfig extends
 * 		AbstractSecurityWebSocketMessageBrokerConfigurer {
 *
 * 	&#064;Override
 * 	protected void configureInbound(MessageSecurityMetadataSourceRegistry messages) {
 * 		messages.simpDestMatchers(&quot;/user/queue/errors&quot;).permitAll()
 * 				.simpDestMatchers(&quot;/admin/**&quot;).hasRole(&quot;ADMIN&quot;).anyMessage()
 * 				.authenticated();
 * 	}
 * }
 * </pre>
 *
 *
 * @since 4.0
 * @author Rob Winch
 */
@Order(Ordered.HIGHEST_PRECEDENCE + 100)
public abstract class AbstractSecurityWebSocketMessageBrokerConfigurer extends
		AbstractWebSocketMessageBrokerConfigurer implements SmartInitializingSingleton {
	private final WebSocketMessageSecurityMetadataSourceRegistry inboundRegistry = new WebSocketMessageSecurityMetadataSourceRegistry();

	private ApplicationContext context;

	public void registerStompEndpoints(StompEndpointRegistry registry) {
	}

	@Override
	public void addArgumentResolvers(List<HandlerMethodArgumentResolver> argumentResolvers) {
		argumentResolvers.add(new AuthenticationPrincipalArgumentResolver());
	}

	@Override
	public final void configureClientInboundChannel(ChannelRegistration registration) {
		ChannelSecurityInterceptor inboundChannelSecurity = inboundChannelSecurity();
		registration.setInterceptors(securityContextChannelInterceptor());
		if (!sameOriginDisabled()) {
			registration.setInterceptors(csrfChannelInterceptor());
		}
		if (inboundRegistry.containsMapping()) {
			registration.setInterceptors(inboundChannelSecurity);
		}
		customizeClientInboundChannel(registration);
	}

	private PathMatcher getDefaultPathMatcher() {
		try {
			return context.getBean(SimpAnnotationMethodMessageHandler.class).getPathMatcher();
		} catch(NoSuchBeanDefinitionException e) {
			return new AntPathMatcher();
		}
	}

	/**
	 * <p>
	 * Determines if a CSRF token is required for connecting. This protects against remote
	 * sites from connecting to the application and being able to read/write data over the
	 * connection. The default is false (the token is required).
	 * </p>
	 * <p>
	 * Subclasses can override this method to disable CSRF protection
	 * </p>
	 *
	 * @return false if a CSRF token is required for connecting, else true
	 */
	protected boolean sameOriginDisabled() {
		return false;
	}

	/**
	 * Allows subclasses to customize the configuration of the {@link ChannelRegistration}
	 * .
	 *
	 * @param registration the {@link ChannelRegistration} to customize
	 */
	protected void customizeClientInboundChannel(ChannelRegistration registration) {
	}

	@Bean
	public CsrfChannelInterceptor csrfChannelInterceptor() {
		return new CsrfChannelInterceptor();
	}

	@Bean
	public ChannelSecurityInterceptor inboundChannelSecurity() {
		ChannelSecurityInterceptor channelSecurityInterceptor = new ChannelSecurityInterceptor(
				inboundMessageSecurityMetadataSource());
		List<AccessDecisionVoter<? extends Object>> voters = new ArrayList<AccessDecisionVoter<? extends Object>>();
		voters.add(new MessageExpressionVoter<Object>());
		AffirmativeBased manager = new AffirmativeBased(voters);
		channelSecurityInterceptor.setAccessDecisionManager(manager);
		return channelSecurityInterceptor;
	}

	@Bean
	public SecurityContextChannelInterceptor securityContextChannelInterceptor() {
		return new SecurityContextChannelInterceptor();
	}

	@Bean
	public MessageSecurityMetadataSource inboundMessageSecurityMetadataSource() {
		configureInbound(inboundRegistry);
		return inboundRegistry.createMetadataSource();
	}

	/**
	 *
	 * @param messages
	 */
	protected void configureInbound(MessageSecurityMetadataSourceRegistry messages) {
	}

	private static class WebSocketMessageSecurityMetadataSourceRegistry extends
			MessageSecurityMetadataSourceRegistry {
		@Override
		public MessageSecurityMetadataSource createMetadataSource() {
			return super.createMetadataSource();
		}

		@Override
		protected boolean containsMapping() {
			return super.containsMapping();
		}

		@Override
		protected boolean isSimpDestPathMatcherConfigured() {
			return super.isSimpDestPathMatcherConfigured();
		}
	}

	@Autowired
	public void setApplicationContext(ApplicationContext context) {
		this.context = context;
	}

	public void afterSingletonsInstantiated() {
		if (sameOriginDisabled()) {
			return;
		}

		String beanName = "stompWebSocketHandlerMapping";
		SimpleUrlHandlerMapping mapping = context.getBean(beanName,
				SimpleUrlHandlerMapping.class);
		Map<String, Object> mappings = mapping.getHandlerMap();
		for (Object object : mappings.values()) {
			if (object instanceof SockJsHttpRequestHandler) {
				SockJsHttpRequestHandler sockjsHandler = (SockJsHttpRequestHandler) object;
				SockJsService sockJsService = sockjsHandler.getSockJsService();
				if (!(sockJsService instanceof TransportHandlingSockJsService)) {
					throw new IllegalStateException(
							"sockJsService must be instance of TransportHandlingSockJsService got "
									+ sockJsService);
				}

				TransportHandlingSockJsService transportHandlingSockJsService = (TransportHandlingSockJsService) sockJsService;
				List<HandshakeInterceptor> handshakeInterceptors = transportHandlingSockJsService
						.getHandshakeInterceptors();
				List<HandshakeInterceptor> interceptorsToSet = new ArrayList<HandshakeInterceptor>(
						handshakeInterceptors.size() + 1);
				interceptorsToSet.add(new CsrfTokenHandshakeInterceptor());
				interceptorsToSet.addAll(handshakeInterceptors);

				transportHandlingSockJsService
						.setHandshakeInterceptors(interceptorsToSet);
			}
			else if (object instanceof WebSocketHttpRequestHandler) {
				WebSocketHttpRequestHandler handler = (WebSocketHttpRequestHandler) object;
				List<HandshakeInterceptor> handshakeInterceptors = handler
						.getHandshakeInterceptors();
				List<HandshakeInterceptor> interceptorsToSet = new ArrayList<HandshakeInterceptor>(
						handshakeInterceptors.size() + 1);
				interceptorsToSet.add(new CsrfTokenHandshakeInterceptor());
				interceptorsToSet.addAll(handshakeInterceptors);

				handler.setHandshakeInterceptors(interceptorsToSet);
			}
			else {
				throw new IllegalStateException(
						"Bean "
								+ beanName
								+ " is expected to contain mappings to either a SockJsHttpRequestHandler or a WebSocketHttpRequestHandler but got "
								+ object);
			}
		}

		if (inboundRegistry.containsMapping() && !inboundRegistry.isSimpDestPathMatcherConfigured()) {
			PathMatcher pathMatcher = getDefaultPathMatcher();
			inboundRegistry.simpDestPathMatcher(pathMatcher);
		}
	}
}

File: config/src/main/java/org/springframework/security/config/websocket/WebSocketMessageBrokerSecurityBeanDefinitionParser.java
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
package org.springframework.security.config.websocket;

import java.util.Comparator;
import java.util.List;
import java.util.Map;

import org.springframework.beans.BeansException;
import org.springframework.beans.PropertyValue;
import org.springframework.beans.factory.config.BeanDefinition;
import org.springframework.beans.factory.config.BeanReference;
import org.springframework.beans.factory.config.ConfigurableListableBeanFactory;
import org.springframework.beans.factory.config.RuntimeBeanReference;
import org.springframework.beans.factory.support.BeanDefinitionBuilder;
import org.springframework.beans.factory.support.BeanDefinitionRegistry;
import org.springframework.beans.factory.support.BeanDefinitionRegistryPostProcessor;
import org.springframework.beans.factory.support.ManagedList;
import org.springframework.beans.factory.support.ManagedMap;
import org.springframework.beans.factory.support.RootBeanDefinition;
import org.springframework.beans.factory.xml.BeanDefinitionParser;
import org.springframework.beans.factory.xml.ParserContext;
import org.springframework.beans.factory.xml.XmlReaderContext;
import org.springframework.messaging.simp.SimpMessageType;
import org.springframework.messaging.simp.annotation.support.SimpAnnotationMethodMessageHandler;
import org.springframework.security.access.vote.ConsensusBased;
import org.springframework.security.config.Elements;
import org.springframework.security.messaging.access.expression.ExpressionBasedMessageSecurityMetadataSourceFactory;
import org.springframework.security.messaging.access.expression.MessageExpressionVoter;
import org.springframework.security.messaging.access.intercept.ChannelSecurityInterceptor;
import org.springframework.security.messaging.context.AuthenticationPrincipalArgumentResolver;
import org.springframework.security.messaging.context.SecurityContextChannelInterceptor;
import org.springframework.security.messaging.util.matcher.SimpDestinationMessageMatcher;
import org.springframework.security.messaging.util.matcher.SimpMessageTypeMatcher;
import org.springframework.security.messaging.web.csrf.CsrfChannelInterceptor;
import org.springframework.security.messaging.web.socket.server.CsrfTokenHandshakeInterceptor;
import org.springframework.util.AntPathMatcher;
import org.springframework.util.PathMatcher;
import org.springframework.util.StringUtils;
import org.springframework.util.xml.DomUtils;
import org.w3c.dom.Element;

/**
 * Parses Spring Security's websocket namespace support. A simple example is:
 *
 * <code>
 * &lt;websocket-message-broker&gt;
 *     &lt;intercept-message pattern='/permitAll' access='permitAll' /&gt;
 *     &lt;intercept-message pattern='/denyAll' access='denyAll' /&gt;
 * &lt;/websocket-message-broker&gt;
 * </code>
 *
 * <p>
 * The above configuration will ensure that any SimpAnnotationMethodMessageHandler has the
 * AuthenticationPrincipalArgumentResolver registered as a custom argument resolver. It
 * also ensures that the SecurityContextChannelInterceptor is automatically registered for
 * the clientInboundChannel. Last, it ensures that a ChannelSecurityInterceptor is
 * registered with the clientInboundChannel.
 * </p>
 *
 * <p>
 * If finer control is necessary, the id attribute can be used as shown below:
 * </p>
 *
 * <code>
 * &lt;websocket-message-broker id="channelSecurityInterceptor"&gt;
 *     &lt;intercept-message pattern='/permitAll' access='permitAll' /&gt;
 *     &lt;intercept-message pattern='/denyAll' access='denyAll' /&gt;
 * &lt;/websocket-message-broker&gt;
 * </code>
 *
 * <p>
 * Now the configuration will only create a bean named ChannelSecurityInterceptor and
 * assign it to the id of channelSecurityInterceptor. Users can explicitly wire Spring
 * Security using the standard Spring Messaging XML namespace support.
 * </p>
 *
 * @author Rob Winch
 * @since 4.0
 */
public final class WebSocketMessageBrokerSecurityBeanDefinitionParser implements
		BeanDefinitionParser {
	private static final String ID_ATTR = "id";

	private static final String DISABLED_ATTR = "same-origin-disabled";

	private static final String PATTERN_ATTR = "pattern";

	private static final String ACCESS_ATTR = "access";

	private static final String TYPE_ATTR = "type";

	private static final String PATH_MATCHER_BEAN_NAME = "springSecurityMessagePathMatcher";

	/**
	 * @param element
	 * @param parserContext
	 * @return
	 */
	public BeanDefinition parse(Element element, ParserContext parserContext) {
		BeanDefinitionRegistry registry = parserContext.getRegistry();
		XmlReaderContext context = parserContext.getReaderContext();

		ManagedMap<BeanDefinition, String> matcherToExpression = new ManagedMap<BeanDefinition, String>();

		String id = element.getAttribute(ID_ATTR);
		boolean sameOriginDisabled = Boolean.parseBoolean(element
				.getAttribute(DISABLED_ATTR));

		List<Element> interceptMessages = DomUtils.getChildElementsByTagName(element,
				Elements.INTERCEPT_MESSAGE);
		for (Element interceptMessage : interceptMessages) {
			String matcherPattern = interceptMessage.getAttribute(PATTERN_ATTR);
			String accessExpression = interceptMessage.getAttribute(ACCESS_ATTR);
			String messageType = interceptMessage.getAttribute(TYPE_ATTR);

			BeanDefinition matcher = createMatcher(matcherPattern, messageType,
					parserContext, interceptMessage);
			matcherToExpression.put(matcher, accessExpression);
		}

		BeanDefinitionBuilder mds = BeanDefinitionBuilder
				.rootBeanDefinition(ExpressionBasedMessageSecurityMetadataSourceFactory.class);
		mds.setFactoryMethod("createExpressionMessageMetadataSource");
		mds.addConstructorArgValue(matcherToExpression);

		String mdsId = context.registerWithGeneratedName(mds.getBeanDefinition());

		ManagedList<BeanDefinition> voters = new ManagedList<BeanDefinition>();
		voters.add(new RootBeanDefinition(MessageExpressionVoter.class));
		BeanDefinitionBuilder adm = BeanDefinitionBuilder
				.rootBeanDefinition(ConsensusBased.class);
		adm.addConstructorArgValue(voters);

		BeanDefinitionBuilder inboundChannelSecurityInterceptor = BeanDefinitionBuilder
				.rootBeanDefinition(ChannelSecurityInterceptor.class);
		inboundChannelSecurityInterceptor.addConstructorArgValue(registry
				.getBeanDefinition(mdsId));
		inboundChannelSecurityInterceptor.addPropertyValue("accessDecisionManager",
				adm.getBeanDefinition());
		String inSecurityInterceptorName = context
				.registerWithGeneratedName(inboundChannelSecurityInterceptor
						.getBeanDefinition());

		if (StringUtils.hasText(id)) {
			registry.registerAlias(inSecurityInterceptorName, id);

			if(!registry.containsBeanDefinition(PATH_MATCHER_BEAN_NAME)) {
				registry.registerBeanDefinition(PATH_MATCHER_BEAN_NAME, new RootBeanDefinition(AntPathMatcher.class));
			}
		}
		else {
			BeanDefinitionBuilder mspp = BeanDefinitionBuilder
					.rootBeanDefinition(MessageSecurityPostProcessor.class);
			mspp.addConstructorArgValue(inSecurityInterceptorName);
			mspp.addConstructorArgValue(sameOriginDisabled);
			context.registerWithGeneratedName(mspp.getBeanDefinition());
		}

		return null;
	}

	private BeanDefinition createMatcher(String matcherPattern, String messageType,
			ParserContext parserContext, Element interceptMessage) {
		boolean hasPattern = StringUtils.hasText(matcherPattern);
		boolean hasMessageType = StringUtils.hasText(messageType);
		if (!hasPattern) {
			BeanDefinitionBuilder matcher = BeanDefinitionBuilder
					.rootBeanDefinition(SimpMessageTypeMatcher.class);
			matcher.addConstructorArgValue(messageType);
			return matcher.getBeanDefinition();
		}

		String factoryName = null;
		if (hasPattern && hasMessageType) {
			SimpMessageType type = SimpMessageType.valueOf(messageType);
			if (SimpMessageType.MESSAGE == type) {
				factoryName = "createMessageMatcher";
			}
			else if (SimpMessageType.SUBSCRIBE == type) {
				factoryName = "createSubscribeMatcher";
			}
			else {
				parserContext
						.getReaderContext()
						.error("Cannot use intercept-websocket@message-type="
								+ messageType
								+ " with a pattern because the type does not have a destination.",
								interceptMessage);
			}
		}

		BeanDefinitionBuilder matcher = BeanDefinitionBuilder
				.rootBeanDefinition(SimpDestinationMessageMatcher.class);
		matcher.setFactoryMethod(factoryName);
		matcher.addConstructorArgValue(matcherPattern);
		matcher.addConstructorArgValue(new RuntimeBeanReference("springSecurityMessagePathMatcher"));
		return matcher.getBeanDefinition();
	}

	static class MessageSecurityPostProcessor implements
			BeanDefinitionRegistryPostProcessor {

		/**
		 * This is not available prior to Spring 4.2
		 */
		private static final String WEB_SOCKET_AMMH_CLASS_NAME = "org.springframework.web.socket.messaging.WebSocketAnnotationMethodMessageHandler";

		private static final String CLIENT_INBOUND_CHANNEL_BEAN_ID = "clientInboundChannel";

		private static final String INTERCEPTORS_PROP = "interceptors";

		private static final String CUSTOM_ARG_RESOLVERS_PROP = "customArgumentResolvers";

		private final String inboundSecurityInterceptorId;

		private final boolean sameOriginDisabled;

		public MessageSecurityPostProcessor(String inboundSecurityInterceptorId,
				boolean sameOriginDisabled) {
			this.inboundSecurityInterceptorId = inboundSecurityInterceptorId;
			this.sameOriginDisabled = sameOriginDisabled;
		}

		public void postProcessBeanDefinitionRegistry(BeanDefinitionRegistry registry)
				throws BeansException {
			String[] beanNames = registry.getBeanDefinitionNames();
			for (String beanName : beanNames) {
				BeanDefinition bd = registry.getBeanDefinition(beanName);
				String beanClassName = bd.getBeanClassName();
				if (beanClassName.equals(SimpAnnotationMethodMessageHandler.class
						.getName()) || beanClassName.equals(WEB_SOCKET_AMMH_CLASS_NAME)) {
					PropertyValue current = bd.getPropertyValues().getPropertyValue(
							CUSTOM_ARG_RESOLVERS_PROP);
					ManagedList<Object> argResolvers = new ManagedList<Object>();
					if (current != null) {
						argResolvers.addAll((ManagedList<?>) current.getValue());
					}
					argResolvers.add(new RootBeanDefinition(
							AuthenticationPrincipalArgumentResolver.class));
					bd.getPropertyValues().add(CUSTOM_ARG_RESOLVERS_PROP, argResolvers);

					if(!registry.containsBeanDefinition(PATH_MATCHER_BEAN_NAME)) {
						PropertyValue pathMatcherProp = bd.getPropertyValues().getPropertyValue("pathMatcher");
						Object pathMatcher = pathMatcherProp == null ? null : pathMatcherProp.getValue();
						if(pathMatcher instanceof BeanReference) {
							registry.registerAlias(((BeanReference) pathMatcher).getBeanName(), PATH_MATCHER_BEAN_NAME);
						}
					}
				}
				else if (beanClassName
						.equals("org.springframework.web.socket.server.support.WebSocketHttpRequestHandler")) {
					addCsrfTokenHandshakeInterceptor(bd);
				}
				else if (beanClassName
						.equals("org.springframework.web.socket.sockjs.transport.TransportHandlingSockJsService")) {
					addCsrfTokenHandshakeInterceptor(bd);
				}
				else if (beanClassName
						.equals("org.springframework.web.socket.sockjs.transport.handler.DefaultSockJsService")) {
					addCsrfTokenHandshakeInterceptor(bd);
				}
			}

			if (!registry.containsBeanDefinition(CLIENT_INBOUND_CHANNEL_BEAN_ID)) {
				return;
			}
			ManagedList<Object> interceptors = new ManagedList();
			interceptors.add(new RootBeanDefinition(
					SecurityContextChannelInterceptor.class));
			if (!sameOriginDisabled) {
				interceptors.add(new RootBeanDefinition(CsrfChannelInterceptor.class));
			}
			interceptors.add(registry.getBeanDefinition(inboundSecurityInterceptorId));

			BeanDefinition inboundChannel = registry
					.getBeanDefinition(CLIENT_INBOUND_CHANNEL_BEAN_ID);
			PropertyValue currentInterceptorsPv = inboundChannel.getPropertyValues()
					.getPropertyValue(INTERCEPTORS_PROP);
			if (currentInterceptorsPv != null) {
				ManagedList<?> currentInterceptors = (ManagedList<?>) currentInterceptorsPv
						.getValue();
				interceptors.addAll(currentInterceptors);
			}

			inboundChannel.getPropertyValues().add(INTERCEPTORS_PROP, interceptors);

			if(!registry.containsBeanDefinition(PATH_MATCHER_BEAN_NAME)) {
				registry.registerBeanDefinition(PATH_MATCHER_BEAN_NAME, new RootBeanDefinition(AntPathMatcher.class));
			}
		}

		private void addCsrfTokenHandshakeInterceptor(BeanDefinition bd) {
			if (sameOriginDisabled) {
				return;
			}
			String interceptorPropertyName = "handshakeInterceptors";
			ManagedList<? super Object> interceptors = new ManagedList<Object>();
			interceptors.add(new RootBeanDefinition(CsrfTokenHandshakeInterceptor.class));
			interceptors.addAll((ManagedList<Object>) bd.getPropertyValues().get(
					interceptorPropertyName));
			bd.getPropertyValues().add(interceptorPropertyName, interceptors);
		}

		public void postProcessBeanFactory(ConfigurableListableBeanFactory beanFactory)
				throws BeansException {

		}
	}

	static class DelegatingPathMatcher implements PathMatcher {

		private PathMatcher delegate = new AntPathMatcher();

		public boolean isPattern(String path) {
			return delegate.isPattern(path);
		}

		public boolean match(String pattern, String path) {
			return delegate.match(pattern, path);
		}

		public boolean matchStart(String pattern, String path) {
			return delegate.matchStart(pattern, path);
		}

		public String extractPathWithinPattern(String pattern, String path) {
			return delegate.extractPathWithinPattern(pattern, path);
		}

		public Map<String, String> extractUriTemplateVariables(String pattern, String path) {
			return delegate.extractUriTemplateVariables(pattern, path);
		}

		public Comparator<String> getPatternComparator(String path) {
			return delegate.getPatternComparator(path);
		}

		public String combine(String pattern1, String pattern2) {
			return delegate.combine(pattern1, pattern2);
		}

		void setPathMatcher(PathMatcher pathMatcher) {
			this.delegate = pathMatcher;
		}
	}
}

File: config/src/test/java/org/springframework/security/config/annotation/web/socket/AbstractSecurityWebSocketMessageBrokerConfigurerTests.java
/*
 *
 * Licensed under the Apache License, Version 2.0 (the "License"); you may not
 * use this file except in compliance with the License. You may obtain a copy of
 * the License at
 *
 * http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
 * WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
 * License for the specific language governing permissions and limitations under
 * the License.
 */
package org.springframework.security.config.annotation.web.socket;

import org.junit.After;
import org.junit.Before;
import org.junit.Test;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.context.annotation.Import;
import org.springframework.core.MethodParameter;
import org.springframework.http.server.ServerHttpRequest;
import org.springframework.http.server.ServerHttpResponse;
import org.springframework.messaging.Message;
import org.springframework.messaging.MessageChannel;
import org.springframework.messaging.MessageDeliveryException;
import org.springframework.messaging.handler.annotation.MessageMapping;
import org.springframework.messaging.handler.invocation.HandlerMethodArgumentResolver;
import org.springframework.messaging.simp.SimpMessageHeaderAccessor;
import org.springframework.messaging.simp.SimpMessageType;
import org.springframework.messaging.simp.config.MessageBrokerRegistry;
import org.springframework.messaging.support.GenericMessage;
import org.springframework.mock.web.MockHttpServletRequest;
import org.springframework.mock.web.MockHttpServletResponse;
import org.springframework.mock.web.MockServletConfig;
import org.springframework.security.access.AccessDeniedException;
import org.springframework.security.authentication.TestingAuthenticationToken;
import org.springframework.security.config.annotation.web.messaging.MessageSecurityMetadataSourceRegistry;
import org.springframework.security.core.annotation.AuthenticationPrincipal;
import org.springframework.security.web.csrf.CsrfToken;
import org.springframework.security.web.csrf.DefaultCsrfToken;
import org.springframework.security.web.csrf.MissingCsrfTokenException;
import org.springframework.stereotype.Controller;
import org.springframework.test.util.ReflectionTestUtils;
import org.springframework.util.AntPathMatcher;
import org.springframework.web.HttpRequestHandler;
import org.springframework.web.context.support.AnnotationConfigWebApplicationContext;
import org.springframework.web.servlet.HandlerMapping;
import org.springframework.web.socket.WebSocketHandler;
import org.springframework.web.socket.config.annotation.EnableWebSocketMessageBroker;
import org.springframework.web.socket.config.annotation.StompEndpointRegistry;
import org.springframework.web.socket.server.HandshakeFailureException;
import org.springframework.web.socket.server.HandshakeHandler;
import org.springframework.web.socket.server.support.HttpSessionHandshakeInterceptor;
import org.springframework.web.socket.sockjs.transport.handler.SockJsWebSocketHandler;
import org.springframework.web.socket.sockjs.transport.session.WebSocketServerSockJsSession;

import javax.servlet.http.HttpServletRequest;

import java.util.HashMap;
import java.util.Map;

import static org.fest.assertions.Assertions.assertThat;
import static org.junit.Assert.fail;

public class AbstractSecurityWebSocketMessageBrokerConfigurerTests {
	AnnotationConfigWebApplicationContext context;

	TestingAuthenticationToken messageUser;

	CsrfToken token;

	String sessionAttr;

	@Before
	public void setup() {
		token = new DefaultCsrfToken("header", "param", "token");
		sessionAttr = "sessionAttr";
		messageUser = new TestingAuthenticationToken("user", "pass", "ROLE_USER");
	}

	@After
	public void cleanup() {
		if (context != null) {
			context.close();
		}
	}

	@Test
	public void simpleRegistryMappings() {
		loadConfig(SockJsSecurityConfig.class);

		clientInboundChannel().send(message("/permitAll"));

		try {
			clientInboundChannel().send(message("/denyAll"));
			fail("Expected Exception");
		}
		catch (MessageDeliveryException expected) {
			assertThat(expected.getCause()).isInstanceOf(AccessDeniedException.class);
		}
	}

	@Test
	public void annonymousSupported() {
		loadConfig(SockJsSecurityConfig.class);

		messageUser = null;
		clientInboundChannel().send(message("/permitAll"));
	}

	@Test
	public void addsAuthenticationPrincipalResolver() throws InterruptedException {
		loadConfig(SockJsSecurityConfig.class);

		MessageChannel messageChannel = clientInboundChannel();
		Message<String> message = message("/permitAll/authentication");
		messageChannel.send(message);

		assertThat(context.getBean(MyController.class).authenticationPrincipal)
				.isEqualTo((String) messageUser.getPrincipal());
	}

	@Test
	public void addsAuthenticationPrincipalResolverWhenNoAuthorization()
			throws InterruptedException {
		loadConfig(NoInboundSecurityConfig.class);

		MessageChannel messageChannel = clientInboundChannel();
		Message<String> message = message("/permitAll/authentication");
		messageChannel.send(message);

		assertThat(context.getBean(MyController.class).authenticationPrincipal)
				.isEqualTo((String) messageUser.getPrincipal());
	}

	@Test
	public void addsCsrfProtectionWhenNoAuthorization() throws InterruptedException {
		loadConfig(NoInboundSecurityConfig.class);

		SimpMessageHeaderAccessor headers = SimpMessageHeaderAccessor
				.create(SimpMessageType.CONNECT);
		Message<?> message = message(headers, "/authentication");
		MessageChannel messageChannel = clientInboundChannel();

		try {
			messageChannel.send(message);
			fail("Expected Exception");
		}
		catch (MessageDeliveryException success) {
			assertThat(success.getCause()).isInstanceOf(MissingCsrfTokenException.class);
		}
	}

	@Test
	public void csrfProtectionForConnect() throws InterruptedException {
		loadConfig(SockJsSecurityConfig.class);

		SimpMessageHeaderAccessor headers = SimpMessageHeaderAccessor
				.create(SimpMessageType.CONNECT);
		Message<?> message = message(headers, "/authentication");
		MessageChannel messageChannel = clientInboundChannel();

		try {
			messageChannel.send(message);
			fail("Expected Exception");
		}
		catch (MessageDeliveryException success) {
			assertThat(success.getCause()).isInstanceOf(MissingCsrfTokenException.class);
		}
	}

	@Test
	public void csrfProtectionDisabledForConnect() throws InterruptedException {
		loadConfig(CsrfDisabledSockJsSecurityConfig.class);

		SimpMessageHeaderAccessor headers = SimpMessageHeaderAccessor
				.create(SimpMessageType.CONNECT);
		Message<?> message = message(headers, "/permitAll/connect");
		MessageChannel messageChannel = clientInboundChannel();

		messageChannel.send(message);
	}

	@Test
	public void messagesConnectUseCsrfTokenHandshakeInterceptor() throws Exception {

		loadConfig(SockJsSecurityConfig.class);

		SimpMessageHeaderAccessor headers = SimpMessageHeaderAccessor
				.create(SimpMessageType.CONNECT);
		Message<?> message = message(headers, "/authentication");
		MockHttpServletRequest request = sockjsHttpRequest("/chat");
		HttpRequestHandler handler = handler(request);

		handler.handleRequest(request, new MockHttpServletResponse());

		assertHandshake(request);
	}

	@Test
	public void messagesConnectUseCsrfTokenHandshakeInterceptorMultipleMappings()
			throws Exception {
		loadConfig(SockJsSecurityConfig.class);

		SimpMessageHeaderAccessor headers = SimpMessageHeaderAccessor
				.create(SimpMessageType.CONNECT);
		Message<?> message = message(headers, "/authentication");
		MockHttpServletRequest request = sockjsHttpRequest("/other");
		HttpRequestHandler handler = handler(request);

		handler.handleRequest(request, new MockHttpServletResponse());

		assertHandshake(request);
	}

	@Test
	public void messagesConnectWebSocketUseCsrfTokenHandshakeInterceptor()
			throws Exception {
		loadConfig(WebSocketSecurityConfig.class);

		SimpMessageHeaderAccessor headers = SimpMessageHeaderAccessor
				.create(SimpMessageType.CONNECT);
		Message<?> message = message(headers, "/authentication");
		MockHttpServletRequest request = websocketHttpRequest("/websocket");
		HttpRequestHandler handler = handler(request);

		handler.handleRequest(request, new MockHttpServletResponse());

		assertHandshake(request);
	}

	@Test
	public void msmsRegistryCustomPatternMatcher()
			throws Exception {
		loadConfig(MsmsRegistryCustomPatternMatcherConfig.class);

		clientInboundChannel().send(message("/app/a.b"));

		try {
			clientInboundChannel().send(message("/app/a.b.c"));
			fail("Expected Exception");
		}
		catch (MessageDeliveryException expected) {
			assertThat(expected.getCause()).isInstanceOf(AccessDeniedException.class);
		}
	}

	@Configuration
	@EnableWebSocketMessageBroker
	@Import(SyncExecutorConfig.class)
	static class MsmsRegistryCustomPatternMatcherConfig extends
			AbstractSecurityWebSocketMessageBrokerConfigurer {

		// @formatter:off
		public void registerStompEndpoints(StompEndpointRegistry registry) {
			registry
				.addEndpoint("/other")
				.setHandshakeHandler(testHandshakeHandler());
		}
		// @formatter:on

		// @formatter:off
		@Override
		protected void configureInbound(MessageSecurityMetadataSourceRegistry messages) {
			messages
				.simpDestMatchers("/app/a.*").permitAll()
				.anyMessage().denyAll();
		}
		// @formatter:on

		@Override
		public void configureMessageBroker(MessageBrokerRegistry registry) {
			registry.setPathMatcher(new AntPathMatcher("."));
			registry.enableSimpleBroker("/queue/", "/topic/");
			registry.setApplicationDestinationPrefixes("/app");
		}

		@Bean
		public TestHandshakeHandler testHandshakeHandler() {
			return new TestHandshakeHandler();
		}
	}

	@Test
	public void overrideMsmsRegistryCustomPatternMatcher()
			throws Exception {
		loadConfig(OverrideMsmsRegistryCustomPatternMatcherConfig.class);

		clientInboundChannel().send(message("/app/a/b"));

		try {
			clientInboundChannel().send(message("/app/a/b/c"));
			fail("Expected Exception");
		}
		catch (MessageDeliveryException expected) {
			assertThat(expected.getCause()).isInstanceOf(AccessDeniedException.class);
		}
	}

	@Configuration
	@EnableWebSocketMessageBroker
	@Import(SyncExecutorConfig.class)
	static class OverrideMsmsRegistryCustomPatternMatcherConfig extends
			AbstractSecurityWebSocketMessageBrokerConfigurer {

		// @formatter:off
		public void registerStompEndpoints(StompEndpointRegistry registry) {
			registry
				.addEndpoint("/other")
				.setHandshakeHandler(testHandshakeHandler());
		}
		// @formatter:on


		// @formatter:off
		@Override
		protected void configureInbound(MessageSecurityMetadataSourceRegistry messages) {
			messages
				.simpDestPathMatcher(new AntPathMatcher())
				.simpDestMatchers("/app/a/*").permitAll()
				.anyMessage().denyAll();
		}
		// @formatter:on

		@Override
		public void configureMessageBroker(MessageBrokerRegistry registry) {
			registry.setPathMatcher(new AntPathMatcher("."));
			registry.enableSimpleBroker("/queue/", "/topic/");
			registry.setApplicationDestinationPrefixes("/app");
		}

		@Bean
		public TestHandshakeHandler testHandshakeHandler() {
			return new TestHandshakeHandler();
		}
	}

	@Test
	public void defaultPatternMatcher()
			throws Exception {
		loadConfig(DefaultPatternMatcherConfig.class);

		clientInboundChannel().send(message("/app/a/b"));

		try {
			clientInboundChannel().send(message("/app/a/b/c"));
			fail("Expected Exception");
		}
		catch (MessageDeliveryException expected) {
			assertThat(expected.getCause()).isInstanceOf(AccessDeniedException.class);
		}
	}

	@Configuration
	@EnableWebSocketMessageBroker
	@Import(SyncExecutorConfig.class)
	static class DefaultPatternMatcherConfig extends
			AbstractSecurityWebSocketMessageBrokerConfigurer {

		// @formatter:off
		public void registerStompEndpoints(StompEndpointRegistry registry) {
			registry
				.addEndpoint("/other")
				.setHandshakeHandler(testHandshakeHandler());
		}
		// @formatter:on

		// @formatter:off
		@Override
		protected void configureInbound(MessageSecurityMetadataSourceRegistry messages) {
			messages
				.simpDestMatchers("/app/a/*").permitAll()
				.anyMessage().denyAll();
		}
		// @formatter:on

		@Override
		public void configureMessageBroker(MessageBrokerRegistry registry) {
			registry.enableSimpleBroker("/queue/", "/topic/");
			registry.setApplicationDestinationPrefixes("/app");
		}

		@Bean
		public TestHandshakeHandler testHandshakeHandler() {
			return new TestHandshakeHandler();
		}
	}

	private void assertHandshake(HttpServletRequest request) {
		TestHandshakeHandler handshakeHandler = context
				.getBean(TestHandshakeHandler.class);
		assertThat(handshakeHandler.attributes.get(CsrfToken.class.getName())).isSameAs(
				token);
		assertThat(handshakeHandler.attributes.get(sessionAttr)).isEqualTo(
				request.getSession().getAttribute(sessionAttr));
	}

	private HttpRequestHandler handler(HttpServletRequest request) throws Exception {
		HandlerMapping handlerMapping = context.getBean(HandlerMapping.class);
		return (HttpRequestHandler) handlerMapping.getHandler(request).getHandler();
	}

	private MockHttpServletRequest websocketHttpRequest(String mapping) {
		MockHttpServletRequest request = sockjsHttpRequest(mapping);
		request.setRequestURI(mapping);
		return request;
	}

	private MockHttpServletRequest sockjsHttpRequest(String mapping) {
		MockHttpServletRequest request = new MockHttpServletRequest();
		request.setMethod("GET");
		request.setAttribute(HandlerMapping.PATH_WITHIN_HANDLER_MAPPING_ATTRIBUTE,
				"/289/tpyx6mde/websocket");
		request.setRequestURI(mapping + "/289/tpyx6mde/websocket");
		request.getSession().setAttribute(sessionAttr, "sessionValue");

		request.setAttribute(CsrfToken.class.getName(), token);
		return request;
	}

	private Message<String> message(String destination) {
		SimpMessageHeaderAccessor headers = SimpMessageHeaderAccessor.create();
		return message(headers, destination);
	}

	private Message<String> message(SimpMessageHeaderAccessor headers, String destination) {
		headers.setSessionId("123");
		headers.setSessionAttributes(new HashMap<String, Object>());
		if (destination != null) {
			headers.setDestination(destination);
		}
		if (messageUser != null) {
			headers.setUser(messageUser);
		}
		return new GenericMessage<String>("hi", headers.getMessageHeaders());
	}

	private MessageChannel clientInboundChannel() {
		return context.getBean("clientInboundChannel", MessageChannel.class);
	}

	private void loadConfig(Class<?>... configs) {
		context = new AnnotationConfigWebApplicationContext();
		context.register(configs);
		context.setServletConfig(new MockServletConfig());
		context.refresh();
	}

	@Controller
	static class MyController {

		String authenticationPrincipal;
		MyCustomArgument myCustomArgument;

		@MessageMapping("/authentication")
		public void authentication(@AuthenticationPrincipal String un) {
			this.authenticationPrincipal = un;
		}

		@MessageMapping("/myCustom")
		public void myCustom(MyCustomArgument myCustomArgument) {
			this.myCustomArgument = myCustomArgument;
		}
	}

	static class MyCustomArgument {
		MyCustomArgument(String notDefaultConstr) {
		}
	}

	static class MyCustomArgumentResolver implements HandlerMethodArgumentResolver {

		public boolean supportsParameter(MethodParameter parameter) {
			return parameter.getParameterType().isAssignableFrom(MyCustomArgument.class);
		}

		public Object resolveArgument(MethodParameter parameter, Message<?> message)
				throws Exception {
			return new MyCustomArgument("");
		}
	}

	static class TestHandshakeHandler implements HandshakeHandler {
		Map<String, Object> attributes;

		public boolean doHandshake(ServerHttpRequest request,
				ServerHttpResponse response, WebSocketHandler wsHandler,
				Map<String, Object> attributes) throws HandshakeFailureException {
			this.attributes = attributes;
			if (wsHandler instanceof SockJsWebSocketHandler) {
				// work around SPR-12716
				SockJsWebSocketHandler sockJs = (SockJsWebSocketHandler) wsHandler;
				WebSocketServerSockJsSession session = (WebSocketServerSockJsSession) ReflectionTestUtils
						.getField(sockJs, "sockJsSession");
				this.attributes = session.getAttributes();
			}
			return true;
		}
	}

	@Configuration
	@EnableWebSocketMessageBroker
	@Import(SyncExecutorConfig.class)
	static class SockJsSecurityConfig extends
			AbstractSecurityWebSocketMessageBrokerConfigurer {

		public void registerStompEndpoints(StompEndpointRegistry registry) {
			registry.addEndpoint("/other").setHandshakeHandler(testHandshakeHandler())
					.withSockJS().setInterceptors(new HttpSessionHandshakeInterceptor());

			registry.addEndpoint("/chat").setHandshakeHandler(testHandshakeHandler())
					.withSockJS().setInterceptors(new HttpSessionHandshakeInterceptor());
		}

		// @formatter:off
		@Override
		protected void configureInbound(MessageSecurityMetadataSourceRegistry messages) {
			messages
				.simpDestMatchers("/permitAll/**").permitAll()
				.anyMessage().denyAll();
		}
		// @formatter:on

		@Override
		public void configureMessageBroker(MessageBrokerRegistry registry) {
			registry.enableSimpleBroker("/queue/", "/topic/");
			registry.setApplicationDestinationPrefixes("/permitAll", "/denyAll");
		}

		@Bean
		public MyController myController() {
			return new MyController();
		}

		@Bean
		public TestHandshakeHandler testHandshakeHandler() {
			return new TestHandshakeHandler();
		}
	}

	@Configuration
	@EnableWebSocketMessageBroker
	@Import(SyncExecutorConfig.class)
	static class NoInboundSecurityConfig extends
			AbstractSecurityWebSocketMessageBrokerConfigurer {

		public void registerStompEndpoints(StompEndpointRegistry registry) {
			registry.addEndpoint("/other").withSockJS()
					.setInterceptors(new HttpSessionHandshakeInterceptor());

			registry.addEndpoint("/chat").withSockJS()
					.setInterceptors(new HttpSessionHandshakeInterceptor());
		}

		@Override
		protected void configureInbound(MessageSecurityMetadataSourceRegistry messages) {
		}

		@Override
		public void configureMessageBroker(MessageBrokerRegistry registry) {
			registry.enableSimpleBroker("/queue/", "/topic/");
			registry.setApplicationDestinationPrefixes("/permitAll", "/denyAll");
		}

		@Bean
		public MyController myController() {
			return new MyController();
		}
	}

	@Configuration
	static class CsrfDisabledSockJsSecurityConfig extends SockJsSecurityConfig {

		@Override
		protected boolean sameOriginDisabled() {
			return true;
		}
	}

	@Configuration
	@EnableWebSocketMessageBroker
	@Import(SyncExecutorConfig.class)
	static class WebSocketSecurityConfig extends
			AbstractSecurityWebSocketMessageBrokerConfigurer {

		public void registerStompEndpoints(StompEndpointRegistry registry) {
			registry.addEndpoint("/websocket")
					.setHandshakeHandler(testHandshakeHandler())
					.addInterceptors(new HttpSessionHandshakeInterceptor());
		}

		// @formatter:off
		@Override
		protected void configureInbound(MessageSecurityMetadataSourceRegistry messages) {
			messages
				.simpDestMatchers("/permitAll/**").permitAll()
				.anyMessage().denyAll();
		}
		// @formatter:on

		@Bean
		public TestHandshakeHandler testHandshakeHandler() {
			return new TestHandshakeHandler();
		}
	}

	@Configuration
	static class SyncExecutorConfig {
		@Bean
		public static SyncExecutorSubscribableChannelPostProcessor postProcessor() {
			return new SyncExecutorSubscribableChannelPostProcessor();
		}
	}
}

File: messaging/src/main/java/org/springframework/security/messaging/access/expression/ExpressionBasedMessageSecurityMetadataSourceFactory.java
/*
 * Copyright 2002-2014 the original author or authors.
 *
 * Licensed under the Apache License, Version 2.0 (the "License"); you may not
 * use this file except in compliance with the License. You may obtain a copy of
 * the License at
 *
 * http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
 * WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
 * License for the specific language governing permissions and limitations under
 * the License.
 */
package org.springframework.security.messaging.access.expression;

import org.springframework.expression.Expression;
import org.springframework.security.access.ConfigAttribute;
import org.springframework.security.messaging.access.intercept.DefaultMessageSecurityMetadataSource;
import org.springframework.security.messaging.access.intercept.MessageSecurityMetadataSource;
import org.springframework.security.messaging.util.matcher.MessageMatcher;

import java.util.Arrays;
import java.util.Collection;
import java.util.LinkedHashMap;
import java.util.Map;

/**
 * A class used to create a {@link MessageSecurityMetadataSource} that uses
 * {@link MessageMatcher} mapped to Spring Expressions.
 *
 * @since 4.0
 * @author Rob Winch
 */
public final class ExpressionBasedMessageSecurityMetadataSourceFactory {

	/**
	 * Create a {@link MessageSecurityMetadataSource} that uses {@link MessageMatcher}
	 * mapped to Spring Expressions. Each entry is considered in order and only the first
	 * match is used.
	 *
	 * For example:
	 *
	 * <pre>
	 *     LinkedHashMap<MessageMatcher<?> matcherToExpression = new LinkedHashMap<MessageMatcher<Object>();
	 *     matcherToExpression.put(new SimDestinationMessageMatcher("/public/**"), "permitAll");
	 *     matcherToExpression.put(new SimDestinationMessageMatcher("/admin/**"), "hasRole('ROLE_ADMIN')");
	 *     matcherToExpression.put(new SimDestinationMessageMatcher("/**"), "authenticated");
	 * 
	 *     MessageSecurityMetadataSource metadataSource = createExpressionMessageMetadataSource(matcherToExpression);
	 * </pre>
	 *
	 * <p>
	 * If our destination is "/public/hello", it would match on "/public/**" and on "/**".
	 * However, only "/public/**" would be used since it is the first entry. That means
	 * that a destination of "/public/hello" will be mapped to "permitAll".
	 * </p>
	 *
	 * <p>
	 * For a complete listing of expressions see {@link MessageSecurityExpressionRoot}
	 * </p>
	 *
	 * @param matcherToExpression an ordered mapping of {@link MessageMatcher} to Strings
	 * that are turned into an Expression using
	 * {@link DefaultMessageSecurityExpressionHandler#getExpressionParser()}
	 * @return the {@link MessageSecurityMetadataSource} to use. Cannot be null.
	 */
	public static MessageSecurityMetadataSource createExpressionMessageMetadataSource(
			LinkedHashMap<MessageMatcher<?>, String> matcherToExpression) {
		DefaultMessageSecurityExpressionHandler<Object> handler = new DefaultMessageSecurityExpressionHandler<Object>();

		LinkedHashMap<MessageMatcher<?>, Collection<ConfigAttribute>> matcherToAttrs = new LinkedHashMap<MessageMatcher<?>, Collection<ConfigAttribute>>();

		for (Map.Entry<MessageMatcher<?>, String> entry : matcherToExpression.entrySet()) {
			MessageMatcher<?> matcher = entry.getKey();
			String rawExpression = entry.getValue();
			Expression expression = handler.getExpressionParser().parseExpression(
					rawExpression);
			ConfigAttribute attribute = new MessageExpressionConfigAttribute(expression);
			matcherToAttrs.put(matcher, Arrays.asList(attribute));
		}
		return new DefaultMessageSecurityMetadataSource(matcherToAttrs);
	}

	private ExpressionBasedMessageSecurityMetadataSourceFactory() {
	}
}

File: messaging/src/main/java/org/springframework/security/messaging/access/expression/MessageSecurityExpressionRoot.java
/*
 * Copyright 2002-2015 the original author or authors.
 *
 * Licensed under the Apache License, Version 2.0 (the "License"); you may not
 * use this file except in compliance with the License. You may obtain a copy of
 * the License at
 *
 * http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
 * WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
 * License for the specific language governing permissions and limitations under
 * the License.
 */
package org.springframework.security.messaging.access.expression;

import org.springframework.messaging.Message;
import org.springframework.security.access.expression.SecurityExpressionRoot;
import org.springframework.security.core.Authentication;

/**
 * The {@link SecurityExpressionRoot} used for {@link Message} expressions.
 *
 * @since 4.0
 * @author Rob Winch
 */
public final class MessageSecurityExpressionRoot extends SecurityExpressionRoot {

	public final Message<?> message;

	public MessageSecurityExpressionRoot(Authentication authentication, Message<?> message) {
		super(authentication);
		this.message = message;
	}
}
