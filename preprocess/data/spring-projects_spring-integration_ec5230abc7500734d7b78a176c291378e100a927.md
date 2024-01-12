Refactoring Types: ['Inline Method']
n/java/org/springframework/integration/ip/tcp/TcpInboundGateway.java
/*
 * Copyright 2002-2011 the original author or authors.
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
package org.springframework.integration.ip.tcp;

import java.util.Map;
import java.util.concurrent.ConcurrentHashMap;
import java.util.concurrent.ScheduledFuture;
import java.util.concurrent.atomic.AtomicInteger;

import org.springframework.context.ApplicationEventPublisher;
import org.springframework.integration.context.OrderlyShutdownCapable;
import org.springframework.integration.gateway.MessagingGatewaySupport;
import org.springframework.integration.ip.IpHeaders;
import org.springframework.integration.ip.tcp.connection.AbstractClientConnectionFactory;
import org.springframework.integration.ip.tcp.connection.AbstractConnectionFactory;
import org.springframework.integration.ip.tcp.connection.AbstractServerConnectionFactory;
import org.springframework.integration.ip.tcp.connection.ClientModeCapable;
import org.springframework.integration.ip.tcp.connection.ClientModeConnectionManager;
import org.springframework.integration.ip.tcp.connection.TcpConnection;
import org.springframework.integration.ip.tcp.connection.TcpConnectionFailedCorrelationEvent;
import org.springframework.integration.ip.tcp.connection.TcpListener;
import org.springframework.integration.ip.tcp.connection.TcpSender;
import org.springframework.messaging.Message;
import org.springframework.messaging.MessagingException;
import org.springframework.messaging.support.ErrorMessage;
import org.springframework.util.Assert;

/**
 * Inbound Gateway using a server connection factory - threading is controlled by the
 * factory. For java.net connections, each socket can process only one message at a time.
 * For java.nio connections, messages may be multiplexed but the client will need to
 * provide correlation logic. If the client is a {@link TcpOutboundGateway} multiplexing
 * is not used, but multiple concurrent connections can be used if the connection factory uses
 * single-use connections. For true asynchronous bi-directional communication, a pair of
 * inbound / outbound channel adapters should be used.
 * @author Gary Russell
 * @since 2.0
 *
 */
public class TcpInboundGateway extends MessagingGatewaySupport implements
		TcpListener, TcpSender, ClientModeCapable, OrderlyShutdownCapable {

	private volatile AbstractServerConnectionFactory serverConnectionFactory;

	private volatile AbstractClientConnectionFactory clientConnectionFactory;

	private final Map<String, TcpConnection> connections = new ConcurrentHashMap<String, TcpConnection>();

	private volatile boolean isClientMode;

	private volatile long retryInterval = 60000;

	private volatile ScheduledFuture<?> scheduledFuture;

	private volatile ClientModeConnectionManager clientModeConnectionManager;

	private volatile boolean active;

	private volatile boolean shuttingDown;

	private final AtomicInteger activeCount = new AtomicInteger();

	@Override
	public boolean onMessage(Message<?> message) {
		if (this.shuttingDown) {
			if (logger.isInfoEnabled()) {
				logger.info("Inbound message ignored; shutting down; " + message.toString());
			}
		}
		else {
			if (message instanceof ErrorMessage) {
				/*
				 * Socket errors are sent here so they can be conveyed to any waiting thread.
				 * There's not one here; simply ignore.
				 */
				return false;
			}
			this.activeCount.incrementAndGet();
			try {
				return doOnMessage(message);
			}
			finally {
				this.activeCount.decrementAndGet();
			}
		}
		return false;
	}

	private boolean doOnMessage(Message<?> message) {
		Message<?> reply = this.sendAndReceiveMessage(message);
		if (reply == null) {
			if (logger.isDebugEnabled()) {
				logger.debug("null reply received for " + message + " nothing to send");
			}
			return false;
		}
		String connectionId = (String) message.getHeaders().get(IpHeaders.CONNECTION_ID);
		TcpConnection connection = null;
		if (connectionId != null) {
			connection = connections.get(connectionId);
		}
		if (connection == null) {
			publishNoConnectionEvent(message, connectionId);
			logger.error("Connection not found when processing reply " + reply + " for " + message);
			return false;
		}
		try {
			connection.send(reply);
		}
		catch (Exception e) {
			logger.error("Failed to send reply", e);
		}
		return false;
	}

	private void publishNoConnectionEvent(Message<?> message, String connectionId) {
		AbstractConnectionFactory cf = this.serverConnectionFactory != null ? this.serverConnectionFactory
				: this.clientConnectionFactory;
		ApplicationEventPublisher applicationEventPublisher = cf.getApplicationEventPublisher();
		if (applicationEventPublisher != null) {
			applicationEventPublisher.publishEvent(
				new TcpConnectionFailedCorrelationEvent(this, connectionId, new MessagingException(message)));
		}
	}

	/**
	 * @return true if the associated connection factory is listening.
	 */
	public boolean isListening() {
		return this.serverConnectionFactory == null ? false
				: this.serverConnectionFactory.isListening();
	}

	/**
	 * Must be {@link AbstractClientConnectionFactory} or {@link AbstractServerConnectionFactory}.
	 *
	 * @param connectionFactory the Connection Factory
	 */
	public void setConnectionFactory(AbstractConnectionFactory connectionFactory) {
		Assert.notNull(connectionFactory, "Connection factory must not be null");
		if (connectionFactory instanceof AbstractServerConnectionFactory) {
			this.serverConnectionFactory = (AbstractServerConnectionFactory) connectionFactory;
		} else if (connectionFactory instanceof AbstractClientConnectionFactory) {
			this.clientConnectionFactory = (AbstractClientConnectionFactory) connectionFactory;
		} else {
			throw new IllegalArgumentException("Connection factory must be either an " +
					"AbstractServerConnectionFactory or an AbstractClientConnectionFactory");
		}
		connectionFactory.registerListener(this);
		connectionFactory.registerSender(this);
	}

	@Override
	public void addNewConnection(TcpConnection connection) {
		connections.put(connection.getConnectionId(), connection);
	}

	@Override
	public void removeDeadConnection(TcpConnection connection) {
		connections.remove(connection.getConnectionId());
	}
	@Override
	public String getComponentType(){
		return "ip:tcp-inbound-gateway";
	}

	@Override
	protected void onInit() throws Exception {
		super.onInit();
		if (this.isClientMode) {
			Assert.notNull(this.clientConnectionFactory,
					"For client-mode, connection factory must be type='client'");
			Assert.isTrue(!this.clientConnectionFactory.isSingleUse(),
					"For client-mode, connection factory must have single-use='false'");
		}
	}

	@Override // protected by super#lifecycleLock
	protected void doStart() {
		super.doStart();
		if (!this.active) {
			this.active = true;
			this.shuttingDown = false;
			if (this.serverConnectionFactory != null) {
				this.serverConnectionFactory.start();
			}
			if (this.clientConnectionFactory != null) {
				this.clientConnectionFactory.start();
			}
			if (this.isClientMode) {
				ClientModeConnectionManager manager = new ClientModeConnectionManager(
						this.clientConnectionFactory);
				this.clientModeConnectionManager = manager;
				Assert.state(this.getTaskScheduler() != null, "Client mode requires a task scheduler");
				this.scheduledFuture = this.getTaskScheduler().scheduleAtFixedRate(manager, this.retryInterval);
			}
		}
	}

	@Override // protected by super#lifecycleLock
	protected void doStop() {
		super.doStop();
		if (this.active) {
			this.active = false;
			if (this.scheduledFuture != null) {
				this.scheduledFuture.cancel(true);
			}
			this.clientModeConnectionManager = null;
			if (this.clientConnectionFactory != null) {
				this.clientConnectionFactory.stop();
			}
			if (this.serverConnectionFactory != null) {
				this.serverConnectionFactory.stop();
			}
		}
	}

	/**
	 * @return the isClientMode
	 */
	@Override
	public boolean isClientMode() {
		return isClientMode;
	}

	/**
	 * @param isClientMode
	 *            the isClientMode to set
	 */
	public void setClientMode(boolean isClientMode) {
		this.isClientMode = isClientMode;
	}

	/**
	 * @return the retryInterval
	 */
	public long getRetryInterval() {
		return retryInterval;
	}

	/**
	 * @param retryInterval
	 *            the retryInterval to set
	 */
	public void setRetryInterval(long retryInterval) {
		this.retryInterval = retryInterval;
	}

	@Override
	public boolean isClientModeConnected() {
		if (this.isClientMode && this.clientModeConnectionManager != null) {
			return this.clientModeConnectionManager.isConnected();
		} else {
			return false;
		}
	}

	@Override
	public void retryConnection() {
		if (this.active && this.isClientMode && this.clientModeConnectionManager != null) {
			this.clientModeConnectionManager.run();
		}
	}

	@Override
	public int beforeShutdown() {
		this.shuttingDown = true;
		return this.activeCount.get();
	}

	@Override
	public int afterShutdown() {
		this.stop();
		return this.activeCount.get();
	}
}


File: spring-integration-ip/src/main/java/org/springframework/integration/ip/tcp/TcpOutboundGateway.java
/*
 * Copyright 2001-2015 the original author or authors.
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

package org.springframework.integration.ip.tcp;

import java.util.Map;
import java.util.concurrent.ConcurrentHashMap;
import java.util.concurrent.CountDownLatch;
import java.util.concurrent.Semaphore;
import java.util.concurrent.TimeUnit;

import org.springframework.context.ApplicationEventPublisher;
import org.springframework.context.Lifecycle;
import org.springframework.context.SmartLifecycle;
import org.springframework.expression.EvaluationContext;
import org.springframework.expression.Expression;
import org.springframework.expression.common.LiteralExpression;
import org.springframework.expression.spel.support.StandardEvaluationContext;
import org.springframework.integration.MessageTimeoutException;
import org.springframework.integration.expression.IntegrationEvaluationContextAware;
import org.springframework.integration.handler.AbstractReplyProducingMessageHandler;
import org.springframework.integration.ip.IpHeaders;
import org.springframework.integration.ip.tcp.connection.AbstractClientConnectionFactory;
import org.springframework.integration.ip.tcp.connection.AbstractConnectionFactory;
import org.springframework.integration.ip.tcp.connection.CloseDeferrable;
import org.springframework.integration.ip.tcp.connection.TcpConnection;
import org.springframework.integration.ip.tcp.connection.TcpConnectionFailedCorrelationEvent;
import org.springframework.integration.ip.tcp.connection.TcpListener;
import org.springframework.integration.ip.tcp.connection.TcpSender;
import org.springframework.messaging.Message;
import org.springframework.messaging.MessageChannel;
import org.springframework.messaging.MessagingException;
import org.springframework.messaging.support.ErrorMessage;
import org.springframework.util.Assert;

/**
 * TCP outbound gateway that uses a client connection factory. If the factory is configured
 * for single-use connections, each request is sent on a new connection; if the factory does not use
 * single use connections, each request is blocked until the previous response is received
 * (or times out). Asynchronous requests/responses over the same connection are not
 * supported - use a pair of outbound/inbound adapters for that use case.
 * <p>
 * {@link SmartLifecycle} methods delegate to the underlying {@link AbstractConnectionFactory}
 *
 *
 * @author Gary Russell
 * @since 2.0
 */
public class TcpOutboundGateway extends AbstractReplyProducingMessageHandler
		implements TcpSender, TcpListener, IntegrationEvaluationContextAware, Lifecycle {

	private volatile AbstractClientConnectionFactory connectionFactory;

	private final Map<String, AsyncReply> pendingReplies = new ConcurrentHashMap<String, AsyncReply>();

	private final Semaphore semaphore = new Semaphore(1, true);

	private volatile Expression remoteTimeoutExpression = new LiteralExpression("10000");

	private volatile long requestTimeout = 10000;

	private volatile EvaluationContext evaluationContext = new StandardEvaluationContext();

	/**
	 * @param requestTimeout the requestTimeout to set
	 */
	public void setRequestTimeout(long requestTimeout) {
		this.requestTimeout = requestTimeout;
	}

	/**
	 * @param remoteTimeout the remoteTimeout to set
	 */
	public void setRemoteTimeout(long remoteTimeout) {
		this.remoteTimeoutExpression = new LiteralExpression("" + remoteTimeout);
	}

	/**
	 * @param remoteTimeoutExpression the remoteTimeoutExpression to set
	 */
	public void setRemoteTimeoutExpression(Expression remoteTimeoutExpression) {
		this.remoteTimeoutExpression = remoteTimeoutExpression;
	}

	@Override
	public void setIntegrationEvaluationContext(EvaluationContext evaluationContext) {
		this.evaluationContext = evaluationContext;
	}

	@Override
	protected Object handleRequestMessage(Message<?> requestMessage) {
		Assert.notNull(connectionFactory, this.getClass().getName() +
				" requires a client connection factory");
		boolean haveSemaphore = false;
		String connectionId = null;
		try {
			boolean singleUseConnection = this.connectionFactory.isSingleUse();
			if (!singleUseConnection) {
				logger.debug("trying semaphore");
				if (!this.semaphore.tryAcquire(this.requestTimeout, TimeUnit.MILLISECONDS)) {
					throw new MessageTimeoutException(requestMessage, "Timed out waiting for connection");
				}
				haveSemaphore = true;
				if (logger.isDebugEnabled()) {
					logger.debug("got semaphore");
				}
			}
			TcpConnection connection = this.connectionFactory.getConnection();
			AsyncReply reply = new AsyncReply(this.remoteTimeoutExpression.getValue(this.evaluationContext,
					requestMessage, Long.class));
			connectionId = connection.getConnectionId();
			pendingReplies.put(connectionId, reply);
			if (logger.isDebugEnabled()) {
				logger.debug("Added " + connection.getConnectionId());
			}
			connection.send(requestMessage);
			Message<?> replyMessage = reply.getReply();
			if (replyMessage == null) {
				if (logger.isDebugEnabled()) {
					logger.debug("Remote Timeout on " + connection.getConnectionId());
				}
				// The connection is dirty - force it closed.
				this.connectionFactory.forceClose(connection);
				throw new MessageTimeoutException(requestMessage, "Timed out waiting for response");
			}
			if (logger.isDebugEnabled()) {
				logger.debug("Response " + replyMessage);
			}
			return replyMessage;
		}
		catch (Exception e) {
			logger.error("Tcp Gateway exception", e);
			if (e instanceof MessagingException) {
				throw (MessagingException) e;
			}
			throw new MessagingException("Failed to send or receive", e);
		}
		finally {
			if (connectionId != null) {
				pendingReplies.remove(connectionId);
			}
			if (haveSemaphore) {
				this.semaphore.release();
				if (logger.isDebugEnabled()) {
					logger.debug("released semaphore");
				}
			}
			if (this.connectionFactory instanceof CloseDeferrable) {
				((CloseDeferrable) this.connectionFactory).closeDeferred(connectionId);
			}
		}
	}

	@Override
	public boolean onMessage(Message<?> message) {
		String connectionId = (String) message.getHeaders().get(IpHeaders.CONNECTION_ID);
		if (connectionId == null) {
			logger.error("Cannot correlate response - no connection id");
			publishNoConnectionEvent(message, null, "Cannot correlate response - no connection id");
			return false;
		}
		if (logger.isTraceEnabled()) {
			logger.trace("onMessage: " + connectionId + "(" + message + ")");
		}
		AsyncReply reply = pendingReplies.get(connectionId);
		if (reply == null) {
			if (message instanceof ErrorMessage) {
				/*
				 * Socket errors are sent here so they can be conveyed to any waiting thread.
				 * If there's not one, simply ignore.
				 */
				return false;
			}
			else {
				String errorMessage = "Cannot correlate response - no pending reply for " + connectionId;
				logger.error(errorMessage);
				publishNoConnectionEvent(message, connectionId, errorMessage);
				return false;
			}
		}
		reply.setReply(message);
		return false;
	}

	private void publishNoConnectionEvent(Message<?> message, String connectionId, String errorMessage) {
		ApplicationEventPublisher applicationEventPublisher = this.connectionFactory.getApplicationEventPublisher();
		if (applicationEventPublisher != null) {
			applicationEventPublisher.publishEvent(new TcpConnectionFailedCorrelationEvent(this, connectionId,
					new MessagingException(message, errorMessage)));
		}
	}

	public void setConnectionFactory(AbstractConnectionFactory connectionFactory) {
		// TODO: In 3.0 Change parameter type to AbstractClientConnectionFactory
		Assert.isTrue(connectionFactory instanceof AbstractClientConnectionFactory,
				this.getClass().getName() + " requires a client connection factory");
		this.connectionFactory = (AbstractClientConnectionFactory) connectionFactory;
		connectionFactory.registerListener(this);
		connectionFactory.registerSender(this);
	}

	@Override
	public void addNewConnection(TcpConnection connection) {
		// do nothing - no asynchronous multiplexing supported
	}

	@Override
	public void removeDeadConnection(TcpConnection connection) {
		// do nothing - no asynchronous multiplexing supported
	}

	/**
	 * Specify the Spring Integration reply channel. If this property is not
	 * set the gateway will check for a 'replyChannel' header on the request.
	 *
	 * @param replyChannel The reply channel.
	 */
	public void setReplyChannel(MessageChannel replyChannel) {
		this.setOutputChannel(replyChannel);
	}
	@Override
	public String getComponentType(){
		return "ip:tcp-outbound-gateway";
	}

	@Override
	public void start() {
		if (this.connectionFactory instanceof CloseDeferrable) {
			((CloseDeferrable) this.connectionFactory).enableCloseDeferral(true);
		}
		this.connectionFactory.start();
	}

	@Override
	public void stop() {
		this.connectionFactory.stop();
	}

	@Override
	public boolean isRunning() {
		return this.connectionFactory.isRunning();
	}

	/**
	 * @return the connectionFactory
	 */
	protected AbstractConnectionFactory getConnectionFactory() {
		return connectionFactory;
	}

	/**
	 * Class used to coordinate the asynchronous reply to its request.
	 *
	 * @author Gary Russell
	 * @since 2.0
	 */
	private class AsyncReply {

		private final CountDownLatch latch;

		private final CountDownLatch secondChanceLatch;

		private final long remoteTimeout;

		private volatile Message<?> reply;

		public AsyncReply(long remoteTimeout) {
			this.latch = new CountDownLatch(1);
			this.secondChanceLatch = new CountDownLatch(1);
			this.remoteTimeout = remoteTimeout;
		}

		/**
		 * Sender blocks here until the reply is received, or we time out
		 * @return The return message or null if we time out
		 * @throws Exception
		 */
		public Message<?> getReply() throws Exception {
			try {
				if (!this.latch.await(this.remoteTimeout, TimeUnit.MILLISECONDS)) {
					return null;
				}
			}
			catch (InterruptedException e) {
				Thread.currentThread().interrupt();
			}
			boolean waitForMessageAfterError = true;
			while (reply instanceof ErrorMessage) {
				if (waitForMessageAfterError) {
					/*
					 * Possible race condition with NIO; we might have received the close
					 * before the reply, on a different thread.
					 */
					logger.debug("second chance");
					this.secondChanceLatch.await(2, TimeUnit.SECONDS);
					waitForMessageAfterError = false;
				}
				else if (reply.getPayload() instanceof MessagingException) {
					throw (MessagingException) reply.getPayload();
				}
				else {
					throw new MessagingException("Exception while awaiting reply", (Throwable) reply.getPayload());
				}
			}
			return this.reply;
		}

		/**
		 * We have a race condition when a socket is closed right after the reply is received. The close "error"
		 * might arrive before the actual reply. Overwrite an error with a good reply, but not vice-versa.
		 * @param reply the reply message.
		 */
		public void setReply(Message<?> reply) {
			if (this.reply == null) {
				this.reply = reply;
				this.latch.countDown();
			}
			else if (this.reply instanceof ErrorMessage) {
				this.reply = reply;
				this.secondChanceLatch.countDown();
			}
		}
	}

}


File: spring-integration-ip/src/main/java/org/springframework/integration/ip/tcp/TcpReceivingChannelAdapter.java
/*
 * Copyright 2002-2011 the original author or authors.
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
package org.springframework.integration.ip.tcp;

import java.util.concurrent.ScheduledFuture;
import java.util.concurrent.atomic.AtomicInteger;

import org.springframework.messaging.Message;
import org.springframework.messaging.support.ErrorMessage;
import org.springframework.integration.context.OrderlyShutdownCapable;
import org.springframework.integration.endpoint.MessageProducerSupport;
import org.springframework.integration.ip.tcp.connection.AbstractClientConnectionFactory;
import org.springframework.integration.ip.tcp.connection.AbstractConnectionFactory;
import org.springframework.integration.ip.tcp.connection.AbstractServerConnectionFactory;
import org.springframework.integration.ip.tcp.connection.ClientModeCapable;
import org.springframework.integration.ip.tcp.connection.ClientModeConnectionManager;
import org.springframework.integration.ip.tcp.connection.ConnectionFactory;
import org.springframework.integration.ip.tcp.connection.TcpListener;
import org.springframework.util.Assert;

/**
 * Tcp inbound channel adapter using a TcpConnection to
 * receive data - if the connection factory is a server
 * factory, this Listener owns the connections. If it is
 * a client factory, the sender owns the connection.
 *
 * @author Gary Russell
 * @since 2.0
 *
 */
public class TcpReceivingChannelAdapter
	extends MessageProducerSupport implements TcpListener, ClientModeCapable, OrderlyShutdownCapable {

	private AbstractConnectionFactory clientConnectionFactory;

	private AbstractConnectionFactory serverConnectionFactory;

	private volatile boolean isClientMode;

	private volatile long retryInterval = 60000;

	private volatile ScheduledFuture<?> scheduledFuture;

	private volatile ClientModeConnectionManager clientModeConnectionManager;

	private volatile boolean active;

	private volatile boolean shuttingDown;

	private final AtomicInteger activeCount = new AtomicInteger();

	public boolean onMessage(Message<?> message) {
		if (this.shuttingDown) {
			if (logger.isInfoEnabled()) {
				logger.info("Inbound message ignored; shutting down; " + message.toString());
			}
		}
		else {
			if (message instanceof ErrorMessage) {
				/*
				 * Socket errors are sent here so they can be conveyed to any waiting thread.
				 * There's not one here; simply ignore.
				 */
				return false;
			}
			this.activeCount.incrementAndGet();
			try {
				sendMessage(message);
			}
			finally {
				this.activeCount.decrementAndGet();
			}
		}
		return false;
	}

	@Override
	protected void onInit() {
		super.onInit();
		if (this.isClientMode) {
			Assert.notNull(this.clientConnectionFactory,
					"For client-mode, connection factory must be type='client'");
			Assert.isTrue(!this.clientConnectionFactory.isSingleUse(),
					"For client-mode, connection factory must have single-use='false'");
		}
	}

	@Override // protected by super#lifecycleLock
	protected void doStart() {
		super.doStart();
		if (!this.active) {
			this.active = true;
			this.shuttingDown = false;
			if (this.serverConnectionFactory != null) {
				this.serverConnectionFactory.start();
			}
			if (this.clientConnectionFactory != null) {
				this.clientConnectionFactory.start();
			}
			if (this.isClientMode) {
				ClientModeConnectionManager manager = new ClientModeConnectionManager(
						this.clientConnectionFactory);
				this.clientModeConnectionManager = manager;
				Assert.state(this.getTaskScheduler() != null, "Client mode requires a task scheduler");
				this.scheduledFuture = this.getTaskScheduler().scheduleAtFixedRate(manager, this.retryInterval);
			}
		}
	}

	@Override // protected by super#lifecycleLock
	protected void doStop() {
		super.doStop();
		if (this.active) {
			this.active = false;
			if (this.scheduledFuture != null) {
				this.scheduledFuture.cancel(true);
			}
			this.clientModeConnectionManager = null;
			if (this.clientConnectionFactory != null) {
				this.clientConnectionFactory.stop();
			}
			if (this.serverConnectionFactory != null) {
				this.serverConnectionFactory.stop();
			}
		}
	}

	/**
	 * Sets the client or server connection factory; for this (an inbound adapter), if
	 * the factory is a client connection factory, the sockets are owned by a sending
	 * channel adapter and this adapter is used to receive replies.
	 *
	 * @param connectionFactory the connectionFactory to set
	 */
	public void setConnectionFactory(AbstractConnectionFactory connectionFactory) {
		if (connectionFactory instanceof AbstractClientConnectionFactory) {
			this.clientConnectionFactory = connectionFactory;
		} else {
			this.serverConnectionFactory = connectionFactory;
		}
		connectionFactory.registerListener(this);
	}

	public boolean isListening() {
		if (this.serverConnectionFactory == null) {
			return false;
		}
		if (this.serverConnectionFactory instanceof AbstractServerConnectionFactory) {
			return ((AbstractServerConnectionFactory) this.serverConnectionFactory).isListening();
		}
		return false;
	}

	@Override
	public String getComponentType(){
		return "ip:tcp-inbound-channel-adapter";
	}

	/**
	 * @return the clientConnectionFactory
	 */
	protected ConnectionFactory getClientConnectionFactory() {
		return clientConnectionFactory;
	}

	/**
	 * @return the serverConnectionFactory
	 */
	protected ConnectionFactory getServerConnectionFactory() {
		return serverConnectionFactory;
	}

	/**
	 * @return the isClientMode
	 */
	public boolean isClientMode() {
		return this.isClientMode;
	}

	/**
	 * @param isClientMode
	 *            the isClientMode to set
	 */
	public void setClientMode(boolean isClientMode) {
		this.isClientMode = isClientMode;
	}

	/**
	 * @return the retryInterval
	 */
	public long getRetryInterval() {
		return this.retryInterval;
	}

	/**
	 * @param retryInterval
	 *            the retryInterval to set
	 */
	public void setRetryInterval(long retryInterval) {
		this.retryInterval = retryInterval;
	}

	public boolean isClientModeConnected() {
		if (this.isClientMode && this.clientModeConnectionManager != null) {
			return this.clientModeConnectionManager.isConnected();
		} else {
			return false;
		}
	}

	public void retryConnection() {
		if (this.active && this.isClientMode && this.clientModeConnectionManager != null) {
			this.clientModeConnectionManager.run();
		}
	}

	public int beforeShutdown() {
		this.shuttingDown = true;
		return this.activeCount.get();
	}

	public int afterShutdown() {
		this.stop();
		return this.activeCount.get();
	}
}


File: spring-integration-ip/src/main/java/org/springframework/integration/ip/tcp/TcpSendingMessageHandler.java
/*
 * Copyright 2002-2011 the original author or authors.
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
package org.springframework.integration.ip.tcp;

import java.io.IOException;
import java.util.Map;
import java.util.concurrent.ConcurrentHashMap;
import java.util.concurrent.ScheduledFuture;

import org.springframework.context.ApplicationEventPublisher;
import org.springframework.context.Lifecycle;
import org.springframework.integration.handler.AbstractMessageHandler;
import org.springframework.integration.ip.IpHeaders;
import org.springframework.integration.ip.tcp.connection.AbstractClientConnectionFactory;
import org.springframework.integration.ip.tcp.connection.AbstractConnectionFactory;
import org.springframework.integration.ip.tcp.connection.ClientModeCapable;
import org.springframework.integration.ip.tcp.connection.ClientModeConnectionManager;
import org.springframework.integration.ip.tcp.connection.ConnectionFactory;
import org.springframework.integration.ip.tcp.connection.TcpConnection;
import org.springframework.integration.ip.tcp.connection.TcpConnectionFailedCorrelationEvent;
import org.springframework.integration.ip.tcp.connection.TcpSender;
import org.springframework.messaging.Message;
import org.springframework.messaging.MessageHandlingException;
import org.springframework.scheduling.TaskScheduler;
import org.springframework.util.Assert;

/**
 * Tcp outbound channel adapter using a TcpConnection to
 * send data - if the connection factory is a server
 * factory, the TcpListener owns the connections. If it is
 * a client factory, this object owns the connection.
 * @author Gary Russell
 * @since 2.0
 *
 */
public class TcpSendingMessageHandler extends AbstractMessageHandler implements
		TcpSender, Lifecycle, ClientModeCapable {

	private volatile AbstractConnectionFactory clientConnectionFactory;

	private volatile AbstractConnectionFactory serverConnectionFactory;

	private final Map<String, TcpConnection> connections = new ConcurrentHashMap<String, TcpConnection>();

	private volatile boolean isClientMode;

	private volatile long retryInterval = 60000;

	private volatile ScheduledFuture<?> scheduledFuture;

	private volatile ClientModeConnectionManager clientModeConnectionManager;

	protected final Object lifecycleMonitor = new Object();

	private volatile boolean active;

	protected TcpConnection obtainConnection(Message<?> message) {
		TcpConnection connection = null;
		Assert.notNull(this.clientConnectionFactory, "'clientConnectionFactory' cannot be null");
		try {
			connection = this.clientConnectionFactory.getConnection();
		}
		catch (Exception e) {
			logger.error("Error creating connection", e);
			throw new MessageHandlingException(message, "Failed to obtain a connection", e);
		}
		return connection;
	}

	/**
	 * Writes the message payload to the underlying socket, using the specified
	 * message format.
	 * @see org.springframework.messaging.MessageHandler#handleMessage(org.springframework.messaging.Message)
	 */
	@Override
	public void handleMessageInternal(final Message<?> message) throws
			MessageHandlingException {
		if (this.serverConnectionFactory != null) {
			// We don't own the connection, we are asynchronously replying
			Object connectionId = message.getHeaders().get(IpHeaders.CONNECTION_ID);
			TcpConnection connection = null;
			if (connectionId != null) {
				connection = connections.get(connectionId);
			}
			if (connection != null) {
				try {
					connection.send(message);
				}
				catch (Exception e) {
					logger.error("Error sending message", e);
					connection.close();
					if (e instanceof MessageHandlingException) {
						throw (MessageHandlingException) e;
					}
					else {
						throw new MessageHandlingException(message, "Error sending message", e);
					}
				}
			}
			else {
				logger.error("Unable to find outbound socket for " + message);
				MessageHandlingException messageHandlingException = new MessageHandlingException(message,
						"Unable to find outbound socket");
				publishNoConnectionEvent(messageHandlingException, (String) connectionId);
				throw messageHandlingException;
			}
			return;
		}
		else {
			// we own the connection
			try {
				doWrite(message);
			}
			catch (MessageHandlingException e) {
				// retry - socket may have closed
				if (e.getCause() instanceof IOException) {
					if (logger.isDebugEnabled()) {
						logger.debug("Fail on first write attempt", e);
					}
					doWrite(message);
				}
				else {
					throw e;
				}
			}
		}
	}

	/**
	 * Method that actually does the write.
	 * @param message The message to write.
	 */
	protected void doWrite(Message<?> message) {
		TcpConnection connection = null;
		try {
			connection = obtainConnection(message);
			if (logger.isDebugEnabled()) {
				logger.debug("Got Connection " + connection.getConnectionId());
			}
			connection.send(message);
		}
		catch (Exception e) {
			String connectionId = null;
			if (connection != null) {
				connectionId = connection.getConnectionId();
			}
			if (e instanceof MessageHandlingException) {
				throw (MessageHandlingException) e;
			}
			throw new MessageHandlingException(message, "Failed to handle message using " + connectionId, e);
		}
	}

	private void publishNoConnectionEvent(MessageHandlingException messageHandlingException, String connectionId) {
		AbstractConnectionFactory cf = this.serverConnectionFactory != null ? this.serverConnectionFactory
				: this.clientConnectionFactory;
		ApplicationEventPublisher applicationEventPublisher = cf.getApplicationEventPublisher();
		if (applicationEventPublisher != null) {
			applicationEventPublisher.publishEvent(
				new TcpConnectionFailedCorrelationEvent(this, connectionId, messageHandlingException));
		}
	}

	/**
	 * Sets the client or server connection factory; for this (an outbound adapter), if
	 * the factory is a server connection factory, the sockets are owned by a receiving
	 * channel adapter and this adapter is used to send replies.
	 *
	 * @param connectionFactory the connectionFactory to set
	 */
	public void setConnectionFactory(AbstractConnectionFactory connectionFactory) {
		if (connectionFactory instanceof AbstractClientConnectionFactory) {
			this.clientConnectionFactory = connectionFactory;
		} else {
			this.serverConnectionFactory = connectionFactory;
			connectionFactory.registerSender(this);
		}
	}

	@Override
	public void addNewConnection(TcpConnection connection) {
		connections.put(connection.getConnectionId(), connection);
	}

	@Override
	public void removeDeadConnection(TcpConnection connection) {
		connections.remove(connection.getConnectionId());
	}

	@Override
	public String getComponentType(){
		return "ip:tcp-outbound-channel-adapter";
	}

	@Override
	protected void onInit() throws Exception {
		super.onInit();
		if (this.isClientMode) {
			Assert.notNull(this.clientConnectionFactory,
					"For client-mode, connection factory must be type='client'");
			Assert.isTrue(!this.clientConnectionFactory.isSingleUse(),
					"For client-mode, connection factory must have single-use='false'");
		}
	}

	@Override
	public void start() {
		synchronized (this.lifecycleMonitor) {
			if (!this.active) {
				this.active = true;
				if (this.clientConnectionFactory != null) {
					this.clientConnectionFactory.start();
				}
				if (this.serverConnectionFactory != null) {
					this.serverConnectionFactory.start();
				}
				if (this.isClientMode) {
					ClientModeConnectionManager manager = new ClientModeConnectionManager(
							this.clientConnectionFactory);
					this.clientModeConnectionManager = manager;
					Assert.state(this.getTaskScheduler() != null, "Client mode requires a task scheduler");
					this.scheduledFuture = this.getTaskScheduler().scheduleAtFixedRate(manager, this.retryInterval);
				}
			}
		}
	}

	@Override
	public void stop() {
		synchronized (this.lifecycleMonitor) {
			if (this.active) {
				this.active = false;
				if (this.scheduledFuture != null) {
					this.scheduledFuture.cancel(true);
				}
				if (this.clientConnectionFactory != null) {
					this.clientConnectionFactory.stop();
				}
				if (this.serverConnectionFactory != null) {
					this.serverConnectionFactory.stop();
				}
			}
		}
	}

	@Override
	public boolean isRunning() {
		return this.active;
	}

	public void stop(Runnable callback) {
		synchronized (this.lifecycleMonitor) {
			if (this.active) {
				this.active = false;
				if (this.scheduledFuture != null) {
					this.scheduledFuture.cancel(true);
				}
				this.clientModeConnectionManager = null;
				if (this.clientConnectionFactory != null) {
					this.clientConnectionFactory.stop(callback);
				}
				if (this.serverConnectionFactory != null) {
					this.serverConnectionFactory.stop(callback);
				}
			}
		}
	}

	/**
	 * @return the clientConnectionFactory
	 */
	protected ConnectionFactory getClientConnectionFactory() {
		return clientConnectionFactory;
	}

	/**
	 * @return the serverConnectionFactory
	 */
	protected ConnectionFactory getServerConnectionFactory() {
		return serverConnectionFactory;
	}

	/**
	 * @return the connections
	 */
	protected Map<String, TcpConnection> getConnections() {
		return connections;
	}

	/**
	 * @return the isClientMode
	 */
	@Override
	public boolean isClientMode() {
		return this.isClientMode;
	}

	/**
	 * @param isClientMode
	 *            the isClientMode to set
	 */
	public void setClientMode(boolean isClientMode) {
		this.isClientMode = isClientMode;
	}

	@Override // super class is protected
	public void setTaskScheduler(TaskScheduler taskScheduler) {
		super.setTaskScheduler(taskScheduler);
	}

	/**
	 * @return the retryInterval
	 */
	public long getRetryInterval() {
		return this.retryInterval;
	}

	/**
	 * @param retryInterval
	 *            the retryInterval to set
	 */
	public void setRetryInterval(long retryInterval) {
		this.retryInterval = retryInterval;
	}

	@Override
	public boolean isClientModeConnected() {
		if (this.isClientMode && this.clientModeConnectionManager != null) {
			return this.clientModeConnectionManager.isConnected();
		} else {
			return false;
		}
	}

	@Override
	public void retryConnection() {
		if (this.active && this.isClientMode && this.clientModeConnectionManager != null) {
			this.clientModeConnectionManager.run();
		}
	}

}


File: spring-integration-ip/src/main/java/org/springframework/integration/ip/tcp/connection/AbstractClientConnectionFactory.java
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

package org.springframework.integration.ip.tcp.connection;

import java.net.Socket;
import java.util.concurrent.locks.ReadWriteLock;
import java.util.concurrent.locks.ReentrantReadWriteLock;

/**
 * Abstract class for client connection factories; client connection factories
 * establish outgoing connections.
 * @author Gary Russell
 * @author Artem Bilan
 * @since 2.0
 *
 */
public abstract class AbstractClientConnectionFactory extends AbstractConnectionFactory {

	private final ReadWriteLock theConnectionLock = new ReentrantReadWriteLock();

	private volatile TcpConnectionSupport theConnection;

	private volatile boolean manualListenerRegistration;

	/**
	 * Constructs a factory that will established connections to the host and port.
	 * @param host The host.
	 * @param port The port.
	 */
	public AbstractClientConnectionFactory(String host, int port) {
		super(host, port);
	}

	/**
	 * Set whether to automatically (default) or manually add a {@link TcpListener} to the
	 * connections created by this factory. By default, the factory automatically configures
	 * the listener. When manual registration is in place, incoming messages will be delayed
	 * until the listener is registered.
	 * @since 1.4.5
	 */
	public void enableManualListenerRegistration() {
		this.manualListenerRegistration = true;
	}

	/**
	 * Obtains a connection - if {@link #setSingleUse(boolean)} was called with
	 * true, a new connection is returned; otherwise a single connection is
	 * reused for all requests while the connection remains open.
	 */
	@Override
	public TcpConnectionSupport getConnection() throws Exception {
		this.checkActive();
		return this.obtainConnection();
	}

	protected TcpConnectionSupport obtainConnection() throws Exception {
		if (!this.isSingleUse()) {
			TcpConnectionSupport connection = this.obtainSharedConnection();
			if (connection != null) {
				return connection;
			}
		}
		return this.obtainNewConnection();
	}

	protected final TcpConnectionSupport obtainSharedConnection() throws InterruptedException {
		this.theConnectionLock.readLock().lockInterruptibly();
		try {
			TcpConnectionSupport theConnection = this.getTheConnection();
			if (theConnection != null && theConnection.isOpen()) {
				return theConnection;
			}
		}
		finally {
			this.theConnectionLock.readLock().unlock();
		}

		return null;
	}

	protected final TcpConnectionSupport obtainNewConnection() throws Exception {
		boolean singleUse = this.isSingleUse();
		if (!singleUse) {
			this.theConnectionLock.writeLock().lockInterruptibly();
		}
		try {
			TcpConnectionSupport connection;
			if (!singleUse) {
				// Another write lock holder might have created a new one by now.
				connection = this.obtainSharedConnection();
				if (connection != null) {
					return connection;
				}
			}

			if (logger.isDebugEnabled()) {
				logger.debug("Opening new socket connection to " + this.getHost() + ":" + this.getPort());
			}

			connection = this.buildNewConnection();
			if (!singleUse) {
				this.setTheConnection(connection);
			}
			connection.publishConnectionOpenEvent();
			return connection;
		}
		finally {
			if (!singleUse) {
				this.theConnectionLock.writeLock().unlock();
			}
		}
	}

	protected TcpConnectionSupport buildNewConnection() throws Exception {
		throw new UnsupportedOperationException("Factories that don't override this class' obtainConnection() must implement this method");
	}

	/**
	 * Transfers attributes such as (de)serializers, singleUse etc to a new connection.
	 * When the connection factory has a reference to a TCPListener (to read
	 * responses), or for single use connections, the connection is executed.
	 * Single use connections need to read from the connection in order to
	 * close it after the socket timeout.
	 * @param connection The new connection.
	 * @param socket The new socket.
	 */
	protected void initializeConnection(TcpConnectionSupport connection, Socket socket) {
		if (this.manualListenerRegistration) {
			connection.enableManualListenerRegistration();
		}
		else {
			TcpListener listener = this.getListener();
			if (listener != null) {
				connection.registerListener(listener);
			}
		}
		TcpSender sender = this.getSender();
		if (sender != null) {
			connection.registerSender(sender);
		}
		connection.setMapper(this.getMapper());
		connection.setDeserializer(this.getDeserializer());
		connection.setSerializer(this.getSerializer());
		connection.setSingleUse(this.isSingleUse());
	}

	/**
	 * @param theConnection the theConnection to set
	 */
	protected void setTheConnection(TcpConnectionSupport theConnection) {
		this.theConnection = theConnection;
	}

	/**
	 * @return the theConnection
	 */
	protected TcpConnectionSupport getTheConnection() {
		return theConnection;
	}

	/**
	 * Force close the connection and null the field if it's
	 * a shared connection.
	 *
	 * @param connection The connection.
	 */
	public void forceClose(TcpConnection connection) {
		if (this.theConnection == connection) {
			this.theConnection = null;
		}
		connection.close();
	}

}


File: spring-integration-ip/src/main/java/org/springframework/integration/ip/tcp/connection/AbstractConnectionFactory.java
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

package org.springframework.integration.ip.tcp.connection;

import java.io.EOFException;
import java.io.IOException;
import java.net.Socket;
import java.net.SocketException;
import java.net.SocketTimeoutException;
import java.nio.channels.CancelledKeyException;
import java.nio.channels.SelectionKey;
import java.nio.channels.Selector;
import java.nio.channels.ServerSocketChannel;
import java.nio.channels.SocketChannel;
import java.util.ArrayList;
import java.util.Collections;
import java.util.Iterator;
import java.util.LinkedList;
import java.util.List;
import java.util.Map;
import java.util.Map.Entry;
import java.util.Set;
import java.util.concurrent.BlockingQueue;
import java.util.concurrent.Executor;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;
import java.util.concurrent.LinkedBlockingQueue;
import java.util.concurrent.RejectedExecutionException;
import java.util.concurrent.TimeUnit;

import org.springframework.context.ApplicationEventPublisher;
import org.springframework.context.ApplicationEventPublisherAware;
import org.springframework.context.SmartLifecycle;
import org.springframework.core.serializer.Deserializer;
import org.springframework.core.serializer.Serializer;
import org.springframework.integration.context.IntegrationObjectSupport;
import org.springframework.integration.ip.tcp.serializer.ByteArrayCrLfSerializer;
import org.springframework.messaging.MessagingException;
import org.springframework.util.Assert;

/**
 * Base class for all connection factories.
 *
 * @author Gary Russell
 * @since 2.0
 *
 */
public abstract class AbstractConnectionFactory extends IntegrationObjectSupport
		implements ConnectionFactory, SmartLifecycle, ApplicationEventPublisherAware {

	protected static final int DEFAULT_REPLY_TIMEOUT = 10000;

	private static final int DEFAULT_NIO_HARVEST_INTERVAL = 2000;

	private static final int DEFAULT_READ_DELAY = 100;

	private volatile String host;

	private volatile int port;

	private volatile TcpListener listener;

	private volatile TcpSender sender;

	private volatile int soTimeout = -1;

	private volatile int soSendBufferSize;

	private volatile int soReceiveBufferSize;

	private volatile boolean soTcpNoDelay;

	private volatile int soLinger  = -1; // don't set by default

	private volatile boolean soKeepAlive;

	private volatile int soTrafficClass = -1; // don't set by default

	private volatile Executor taskExecutor;

	private volatile boolean privateExecutor;

	private volatile Deserializer<?> deserializer = new ByteArrayCrLfSerializer();

	private volatile boolean deserializerSet;

	private volatile Serializer<?> serializer = new ByteArrayCrLfSerializer();

	private volatile TcpMessageMapper mapper = new TcpMessageMapper();

	private volatile boolean mapperSet;

	private volatile boolean singleUse;

	private volatile boolean active;

	private volatile TcpConnectionInterceptorFactoryChain interceptorFactoryChain;

	private volatile boolean lookupHost = true;

	private final List<TcpConnectionSupport> connections = new LinkedList<TcpConnectionSupport>();

	private volatile TcpSocketSupport tcpSocketSupport = new DefaultTcpSocketSupport();

	protected final Object lifecycleMonitor = new Object();

	private volatile long nextCheckForClosedNioConnections;

	private volatile int nioHarvestInterval = DEFAULT_NIO_HARVEST_INTERVAL;

	private volatile ApplicationEventPublisher applicationEventPublisher;

	private final BlockingQueue<PendingIO> delayedReads = new LinkedBlockingQueue<AbstractConnectionFactory.PendingIO>();

	private volatile long readDelay = DEFAULT_READ_DELAY;

	public AbstractConnectionFactory(int port) {
		this.port = port;
	}

	public AbstractConnectionFactory(String host, int port) {
		Assert.notNull(host, "host must not be null");
		this.host = host;
		this.port = port;
	}

	@Override
	public void setApplicationEventPublisher(ApplicationEventPublisher applicationEventPublisher) {
		this.applicationEventPublisher = applicationEventPublisher;
		if (!this.deserializerSet && this.deserializer instanceof ApplicationEventPublisherAware) {
			((ApplicationEventPublisherAware) this.deserializer)
					.setApplicationEventPublisher(applicationEventPublisher);
		}
	}

	public ApplicationEventPublisher getApplicationEventPublisher() {
		return applicationEventPublisher;
	}

	/**
	 * Sets socket attributes on the socket.
	 * @param socket The socket.
	 * @throws SocketException Any SocketException.
	 */
	protected void setSocketAttributes(Socket socket) throws SocketException {
		if (this.soTimeout >= 0) {
			socket.setSoTimeout(this.soTimeout);
		}
		if (this.soSendBufferSize > 0) {
			socket.setSendBufferSize(this.soSendBufferSize);
		}
		if (this.soReceiveBufferSize > 0) {
			socket.setReceiveBufferSize(this.soReceiveBufferSize);
		}
		socket.setTcpNoDelay(this.soTcpNoDelay);
		if (this.soLinger >= 0) {
			socket.setSoLinger(true, this.soLinger);
		}
		if (this.soTrafficClass >= 0) {
			socket.setTrafficClass(this.soTrafficClass);
		}
		socket.setKeepAlive(this.soKeepAlive);
		this.tcpSocketSupport.postProcessSocket(socket);
	}

	/**
	 * @return the soTimeout
	 */
	public int getSoTimeout() {
		return soTimeout;
	}

	/**
	 * @param soTimeout the soTimeout to set
	 */
	public void setSoTimeout(int soTimeout) {
		this.soTimeout = soTimeout;
	}

	/**
	 * @return the soReceiveBufferSize
	 */
	public int getSoReceiveBufferSize() {
		return soReceiveBufferSize;
	}

	/**
	 * @param soReceiveBufferSize the soReceiveBufferSize to set
	 */
	public void setSoReceiveBufferSize(int soReceiveBufferSize) {
		this.soReceiveBufferSize = soReceiveBufferSize;
	}

	/**
	 * @return the soSendBufferSize
	 */
	public int getSoSendBufferSize() {
		return soSendBufferSize;
	}

	/**
	 * @param soSendBufferSize the soSendBufferSize to set
	 */
	public void setSoSendBufferSize(int soSendBufferSize) {
		this.soSendBufferSize = soSendBufferSize;
	}

	/**
	 * @return the soTcpNoDelay
	 */
	public boolean isSoTcpNoDelay() {
		return soTcpNoDelay;
	}

	/**
	 * @param soTcpNoDelay the soTcpNoDelay to set
	 */
	public void setSoTcpNoDelay(boolean soTcpNoDelay) {
		this.soTcpNoDelay = soTcpNoDelay;
	}

	/**
	 * @return the soLinger
	 */
	public int getSoLinger() {
		return soLinger;
	}

	/**
	 * @param soLinger the soLinger to set
	 */
	public void setSoLinger(int soLinger) {
		this.soLinger = soLinger;
	}

	/**
	 * @return the soKeepAlive
	 */
	public boolean isSoKeepAlive() {
		return soKeepAlive;
	}

	/**
	 * @param soKeepAlive the soKeepAlive to set
	 */
	public void setSoKeepAlive(boolean soKeepAlive) {
		this.soKeepAlive = soKeepAlive;
	}

	/**
	 * @return the soTrafficClass
	 */
	public int getSoTrafficClass() {
		return soTrafficClass;
	}

	/**
	 * @param soTrafficClass the soTrafficClass to set
	 */
	public void setSoTrafficClass(int soTrafficClass) {
		this.soTrafficClass = soTrafficClass;
	}

	/**
	 * @return the host
	 */
	public String getHost() {
		return host;
	}

	/**
	 * @return the port
	 */
	public int getPort() {
		return port;
	}

	/**
	 * @return the listener
	 */
	public TcpListener getListener() {
		return listener;
	}

	/**
	 * @return the sender
	 */
	public TcpSender getSender() {
		return sender;
	}

	/**
	 * @return the serializer
	 */
	public Serializer<?> getSerializer() {
		return serializer;
	}

	/**
	 * @return the deserializer
	 */
	public Deserializer<?> getDeserializer() {
		return deserializer;
	}

	/**
	 * @return the mapper
	 */
	public TcpMessageMapper getMapper() {
		return mapper;
	}

	/**
	 * Registers a TcpListener to receive messages after
	 * the payload has been converted from the input data.
	 * @param listener the TcpListener.
	 */
	public void registerListener(TcpListener listener) {
		Assert.isNull(this.listener, this.getClass().getName() +
				" may only be used by one inbound adapter");
		this.listener = listener;
	}

	/**
	 * Registers a TcpSender; for server sockets, used to
	 * provide connection information so a sender can be used
	 * to reply to incoming messages.
	 * @param sender The sender
	 */
	public void registerSender(TcpSender sender) {
		Assert.isNull(this.sender, this.getClass().getName() +
				" may only be used by one outbound adapter");
		this.sender = sender;
	}

	/**
	 * @param taskExecutor the taskExecutor to set
	 */
	public void setTaskExecutor(Executor taskExecutor) {
		this.taskExecutor = taskExecutor;
	}

	/**
	 *
	 * @param deserializer the deserializer to set
	 */
	public void setDeserializer(Deserializer<?> deserializer) {
		this.deserializer = deserializer;
		this.deserializerSet = true;
	}

	/**
	 *
	 * @param serializer the serializer to set
	 */
	public void setSerializer(Serializer<?> serializer) {
		this.serializer = serializer;
	}

	/**
	 *
	 * @param mapper the mapper to set; defaults to a {@link TcpMessageMapper}
	 */
	public void setMapper(TcpMessageMapper mapper) {
		this.mapper = mapper;
		this.mapperSet = true;
	}

	/**
	 * @return the singleUse
	 */
	public boolean isSingleUse() {
		return singleUse;
	}

	/**
	 * If true, sockets created by this factory will be used once.
	 * @param singleUse The singleUse to set.
	 */
	public void setSingleUse(boolean singleUse) {
		this.singleUse = singleUse;
	}


	public void setInterceptorFactoryChain(TcpConnectionInterceptorFactoryChain interceptorFactoryChain) {
		this.interceptorFactoryChain = interceptorFactoryChain;
	}

	/**
	 * If true, DNS reverse lookup is done on the remote ip address.
	 * Default true.
	 * @param lookupHost the lookupHost to set
	 */
	public void setLookupHost(boolean lookupHost) {
		this.lookupHost = lookupHost;
	}

	/**
	 * @return the lookupHost
	 */
	public boolean isLookupHost() {
		return lookupHost;
	}

	/**
	 * How often we clean up closed NIO connections if soTimeout is 0.
	 * Ignored when {@code soTimeout > 0} because the clean up
	 * process is run as part of the timeout handling.
	 * Default 2000 milliseconds.
	 * @param nioHarvestInterval The interval in milliseconds.
	 */
	public void setNioHarvestInterval(int nioHarvestInterval) {
		Assert.isTrue(nioHarvestInterval > 0, "NIO Harvest interval must be > 0");
		this.nioHarvestInterval = nioHarvestInterval;
	}

	protected BlockingQueue<PendingIO> getDelayedReads() {
		return delayedReads;
	}

	protected long getReadDelay() {
		return readDelay;
	}

	/**
	 * The delay (in milliseconds) before retrying a read after the previous attempt
	 * failed due to insufficient threads. Default 100.
	 * @param readDelay the readDelay to set.
	 */
	public void setReadDelay(long readDelay) {
		Assert.isTrue(readDelay > 0, "'readDelay' must be positive");
		this.readDelay = readDelay;
	}

	@Override
	protected void onInit() throws Exception {
		super.onInit();
		if (!this.mapperSet) {
			this.mapper.setBeanFactory(this.getBeanFactory());
		}
	}

	@Override
	public void start() {
		if (logger.isInfoEnabled()) {
			logger.info("started " + this);
		}
	}

	/**
	 * Creates a taskExecutor (if one was not provided).
	 * @return The executor.
	 */
	protected Executor getTaskExecutor() {
		if (!this.active) {
			throw new MessagingException("Connection Factory not started");
		}
		synchronized (this.lifecycleMonitor) {
			if (this.taskExecutor == null) {
				this.privateExecutor = true;
				this.taskExecutor = Executors.newCachedThreadPool();
			}
			return this.taskExecutor;
		}
	}

	/**
	 * Stops the server.
	 */
	@Override
	public void stop() {
		this.active = false;
		synchronized (this.connections) {
			Iterator<TcpConnectionSupport> iterator = this.connections.iterator();
			while (iterator.hasNext()) {
				TcpConnection connection = iterator.next();
				connection.close();
				iterator.remove();
			}
		}
		synchronized (this.lifecycleMonitor) {
			if (this.privateExecutor) {
				ExecutorService executorService = (ExecutorService) this.taskExecutor;
				executorService.shutdown();
				try {
					if (!executorService.awaitTermination(10, TimeUnit.SECONDS)) {
						logger.debug("Forcing executor shutdown");
						executorService.shutdownNow();
						if (!executorService.awaitTermination(10, TimeUnit.SECONDS)) {
							logger.debug("Executor failed to shutdown");
						}
					}
				} catch (InterruptedException e) {
					executorService.shutdownNow();
					Thread.currentThread().interrupt();
				} finally {
					this.taskExecutor = null;
					this.privateExecutor = false;
				}
			}
		}
		if (logger.isInfoEnabled()) {
			logger.info("stopped " + this);
		}
	}

	protected TcpConnectionSupport wrapConnection(TcpConnectionSupport connection) throws Exception {
		try {
			if (this.interceptorFactoryChain == null) {
				return connection;
			}
			TcpConnectionInterceptorFactory[] interceptorFactories =
				this.interceptorFactoryChain.getInterceptorFactories();
			if (interceptorFactories == null) {
				return connection;
			}
			for (TcpConnectionInterceptorFactory factory : interceptorFactories) {
				TcpConnectionInterceptorSupport wrapper = factory.getInterceptor();
				wrapper.setTheConnection(connection);
				// if no ultimate listener or sender, register each wrapper in turn
				if (this.listener == null) {
					connection.registerListener(wrapper);
				}
				if (this.sender == null) {
					connection.registerSender(wrapper);
				}
				connection = wrapper;
			}
			return connection;
		} finally {
			this.addConnection(connection);
		}
	}

	/**
	 *
	 * Times out any expired connections then, if {@code selectionCount > 0},
	 * processes the selected keys.
	 * Removes closed connections from the connections field, and from the connections parameter.
	 *
	 * @param selectionCount Number of IO Events, if 0 we were probably woken up by a close.
	 * @param selector The selector.
	 * @param server The server socket channel.
	 * @param connections Map of connections.
	 * @throws IOException Any IOException.
	 */
	protected void processNioSelections(int selectionCount, final Selector selector, ServerSocketChannel server,
			Map<SocketChannel, TcpNioConnection> connections) throws IOException {
		final long now = System.currentTimeMillis();
		rescheduleDelayedReads(selector, now);
		if (this.soTimeout > 0 ||
				now >= this.nextCheckForClosedNioConnections ||
				selectionCount == 0) {
			this.nextCheckForClosedNioConnections = now + this.nioHarvestInterval;
			Iterator<Entry<SocketChannel, TcpNioConnection>> it = connections.entrySet().iterator();
			while (it.hasNext()) {
				SocketChannel channel = it.next().getKey();
				if (!channel.isOpen()) {
					logger.debug("Removing closed channel");
					it.remove();
				}
				else if (soTimeout > 0) {
					TcpNioConnection connection = connections.get(channel);
					if (now - connection.getLastRead() >= this.soTimeout) {
						/*
						 * For client connections, we have to wait for 2 timeouts if the last
						 * send was within the current timeout.
						 */
						if (!connection.isServer() &&
							now - connection.getLastSend() < this.soTimeout &&
							now - connection.getLastRead() < this.soTimeout * 2)
						{
							if (logger.isDebugEnabled()) {
								logger.debug("Skipping a connection timeout because we have a recent send "
										+ connection.getConnectionId());
							}
						}
						else {
							if (logger.isWarnEnabled()) {
								logger.warn("Timing out TcpNioConnection " +
										    connection.getConnectionId());
							}
							connection.publishConnectionExceptionEvent(new SocketTimeoutException("Timing out connection"));
							connection.timeout();
						}
					}
				}
			}
		}
		this.harvestClosedConnections();
		if (logger.isTraceEnabled()) {
			if (host == null) {
				logger.trace("Port " + this.port + " SelectionCount: " + selectionCount);
			} else {
				logger.trace("Host " + this.host + " port " + this.port + " SelectionCount: " + selectionCount);
			}
		}
		if (selectionCount > 0) {
			Set<SelectionKey> keys = selector.selectedKeys();
			Iterator<SelectionKey> iterator = keys.iterator();
			while (iterator.hasNext()) {
				final SelectionKey key = iterator.next();
				iterator.remove();
				try {
					if (!key.isValid()) {
						logger.debug("Selection key no longer valid");
					}
					else if (key.isReadable()) {
						key.interestOps(key.interestOps() - SelectionKey.OP_READ);
						final TcpNioConnection connection;
						connection = (TcpNioConnection) key.attachment();
						connection.setLastRead(System.currentTimeMillis());
						try {
							this.taskExecutor.execute(new Runnable() {
								@Override
								public void run() {
									boolean delayed = false;
									try {
										connection.readPacket();
									}
									catch (RejectedExecutionException e) {
										delayRead(selector, now, key);
										delayed = true;
									}
									catch (Exception e) {
										if (connection.isOpen()) {
											logger.error("Exception on read " +
													connection.getConnectionId() + " " +
													e.getMessage());
											connection.close();
										}
										else {
											logger.debug("Connection closed");
										}
									}
									if (!delayed) {
										if (key.channel().isOpen()) {
											key.interestOps(SelectionKey.OP_READ);
											selector.wakeup();
										}
										else {
											connection.sendExceptionToListener(new EOFException("Connection is closed"));
										}
									}
								}});
						}
						catch (RejectedExecutionException e) {
							delayRead(selector, now, key);
						}
					}
					else if (key.isAcceptable()) {
						try {
							doAccept(selector, server, now);
						} catch (Exception e) {
							logger.error("Exception accepting new connection", e);
						}
					}
					else {
						logger.error("Unexpected key: " + key);
					}
				}
				catch (CancelledKeyException e) {
					if (logger.isDebugEnabled()) {
						logger.debug("Selection key " + key + " cancelled");
					}
				}
				catch (Exception e) {
					logger.error("Exception on selection key " + key, e);
				}
			}
		}
	}

	protected void delayRead(Selector selector, long now, final SelectionKey key) {
		TcpNioConnection connection = (TcpNioConnection) key.attachment();
		if (!this.delayedReads.add(new PendingIO(now, key))) { // should never happen - unbounded queue
			logger.error("Failed to delay read; closing " + connection.getConnectionId());
			connection.close();
		}
		else {
			if (logger.isDebugEnabled()) {
				logger.debug("No threads available, delaying read for " + connection.getConnectionId());
			}
			// wake the selector in case it is currently blocked, and waiting for longer than readDelay
			selector.wakeup();
		}
	}

	/**
	 * If any reads were delayed due to insufficient threads, reschedule them if
	 * the readDelay has passed.
	 * @param selector the selector to wake if necessary.
	 * @param now the current time.
	 */
	private void rescheduleDelayedReads(Selector selector, long now) {
		boolean wakeSelector = false;
		try {
			while (this.delayedReads.size() > 0) {
				if (this.delayedReads.peek().failedAt + this.readDelay < now) {
					PendingIO pendingRead = this.delayedReads.take();
					if (pendingRead.key.channel().isOpen()) {
						pendingRead.key.interestOps(SelectionKey.OP_READ);
						wakeSelector = true;
						if (logger.isDebugEnabled()) {
							logger.debug("Rescheduling delayed read for " + ((TcpNioConnection) pendingRead.key.attachment()).getConnectionId());
						}
					}
					else {
						((TcpNioConnection) pendingRead.key.attachment()).sendExceptionToListener(new EOFException("Connection is closed"));
					}
				}
				else {
					// remaining delayed reads have not expired yet.
					break;
				}
			}
		}
		catch (InterruptedException e) {
			Thread.currentThread().interrupt();
		}
		finally {
			if (wakeSelector) {
				selector.wakeup();
			}
		}
	}

	/**
	 * @param selector The selector.
	 * @param server The server socket channel.
	 * @param now The current time.
	 * @throws IOException Any IOException.
	 */
	protected void doAccept(final Selector selector, ServerSocketChannel server, long now) throws IOException {
		throw new UnsupportedOperationException("Nio server factory must override this method");
	}

	@Override
	public int getPhase() {
		return 0;
	}

	/**
	 * We are controlled by the startup options of
	 * the bound endpoint.
	 */
	@Override
	public boolean isAutoStartup() {
		return false;
	}

	@Override
	public void stop(Runnable callback) {
		stop();
		callback.run();
	}

	protected void addConnection(TcpConnectionSupport connection) {
		synchronized (this.connections) {
			if (!this.active) {
				connection.close();
				return;
			}
			this.connections.add(connection);
		}
	}

	/**
	 * Cleans up this.connections by removing any closed connections.
	 * @return a list of open connection ids.
	 */
	private List<String> removeClosedConnectionsAndReturnOpenConnectionIds() {
		synchronized (this.connections) {
			List<String> openConnectionIds = new ArrayList<String>();
			Iterator<TcpConnectionSupport> iterator = this.connections.iterator();
			while (iterator.hasNext()) {
				TcpConnection connection = iterator.next();
				if (!connection.isOpen()) {
					iterator.remove();
				}
				else {
					openConnectionIds.add(connection.getConnectionId());
				}
			}
			return openConnectionIds;
		}
	}

	/**
	 * Cleans up this.connections by removing any closed connections.
	 */
	protected void harvestClosedConnections() {
		this.removeClosedConnectionsAndReturnOpenConnectionIds();
	}

	@Override
	public boolean isRunning() {
		return this.active;
	}

	/**
	 * @return the active
	 */
	protected boolean isActive() {
		return active;
	}

	/**
	 * @param active the active to set
	 */
	protected void setActive(boolean active) {
		this.active = active;
	}

	protected void checkActive() throws IOException {
		if (!this.isActive()) {
			throw new IOException(this + " connection factory has not been started");
		}
	}

	protected TcpSocketSupport getTcpSocketSupport() {
		return tcpSocketSupport;
	}

	public void setTcpSocketSupport(TcpSocketSupport tcpSocketSupport) {
		Assert.notNull(tcpSocketSupport, "TcpSocketSupport must not be null");
		this.tcpSocketSupport = tcpSocketSupport;
	}

	/**
	 * Returns a list of (currently) open {@link TcpConnection} connection ids; allows,
	 * for example, broadcast operations to all open connections.
	 * @return the list of connection ids.
	 */
	public List<String> getOpenConnectionIds() {
		return Collections.unmodifiableList(this.removeClosedConnectionsAndReturnOpenConnectionIds());
	}

	/**
	 * Close a connection with the specified connection id.
	 * @param connectionId the connection id.
	 * @return true if the connection was closed.
	 */
	public boolean closeConnection(String connectionId) {
		Assert.notNull(connectionId, "'connectionId' to close must not be null");
		synchronized(this.connections) {
			boolean closed = false;
			for (TcpConnectionSupport connection : connections) {
				if (connectionId.equals(connection.getConnectionId())) {
					try {
						connection.close();
						closed = true;
						break;
					}
					catch (Exception e) {
						if (logger.isDebugEnabled()) {
							logger.debug("Failed to close connection " + connectionId, e);
						}
						connection.publishConnectionExceptionEvent(e);
					}
				}
			}
			return closed;
		}
	}

	private class PendingIO {

		private final long failedAt;

		private final SelectionKey key;

		private PendingIO(long failedAt, SelectionKey key) {
			this.failedAt = failedAt;
			this.key = key;
		}

	}

}


File: spring-integration-ip/src/main/java/org/springframework/integration/ip/tcp/connection/AbstractServerConnectionFactory.java
/*
 * Copyright 2001-2015 the original author or authors.
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

package org.springframework.integration.ip.tcp.connection;

import java.net.ServerSocket;
import java.net.Socket;
import java.net.SocketException;

import org.springframework.integration.context.OrderlyShutdownCapable;
import org.springframework.scheduling.SchedulingAwareRunnable;
import org.springframework.util.Assert;

/**
 * Base class for all server connection factories. Server connection factories
 * listen on a port for incoming connections and create new TcpConnection objects
 * for each new connection.
 *
 * @author Gary Russell
 * @since 2.0
 */
public abstract class AbstractServerConnectionFactory
		extends AbstractConnectionFactory implements SchedulingAwareRunnable, OrderlyShutdownCapable {

	private static final int DEFAULT_BACKLOG = 5;

	private volatile boolean listening;

	private volatile String localAddress;

	private volatile int backlog = DEFAULT_BACKLOG;

	private volatile boolean shuttingDown;


	/**
	 * The port on which the factory will listen.
	 *
	 * @param port The port.
	 */
	public AbstractServerConnectionFactory(int port) {
		super(port);
	}

	@Override
	public boolean isLongLived() {
		return true;
	}

	@Override
	public void start() {
		synchronized (this.lifecycleMonitor) {
			if (!isActive()) {
				this.setActive(true);
				this.shuttingDown = false;
				getTaskExecutor().execute(this);
			}
		}
		super.start();
	}

	/**
	 * Not supported because the factory manages multiple connections and this
	 * method cannot discriminate.
	 */
	@Override
	public TcpConnection getConnection() throws Exception {
		throw new UnsupportedOperationException("Getting a connection from a server factory is not supported");
	}

	/**
	 * @param listening the listening to set
	 */
	protected void setListening(boolean listening) {
		this.listening = listening;
	}


	/**
	 *
	 * @return true if the server is listening on the port.
	 */
	public boolean isListening() {
		return listening;
	}

	protected boolean isShuttingDown() {
		return shuttingDown;
	}

	/**
	 * Transfers attributes such as (de)serializer, singleUse etc to a new connection.
	 * For single use sockets, enforces a socket timeout (default 10 seconds).
	 * @param connection The new connection.
	 * @param socket The new socket.
	 */
	protected void initializeConnection(TcpConnectionSupport connection, Socket socket) {
		TcpListener listener = getListener();
		if (listener != null) {
			connection.registerListener(listener);
		}
		connection.registerSender(getSender());
		connection.setMapper(getMapper());
		connection.setDeserializer(getDeserializer());
		connection.setSerializer(getSerializer());
		connection.setSingleUse(isSingleUse());
		/*
		 * If we are configured
		 * for single use; need to enforce a timeout on the socket so we will close
		 * if the client connects, but sends nothing. (Protect against DoS).
		 * Behavior can be overridden by explicitly setting the timeout to zero.
		 */
		if (isSingleUse() && getSoTimeout() < 0) {
			try {
				socket.setSoTimeout(DEFAULT_REPLY_TIMEOUT);
			} catch (SocketException e) {
				logger.error("Error setting default reply timeout", e);
			}
		}

	}

	protected void postProcessServerSocket(ServerSocket serverSocket) {
		getTcpSocketSupport().postProcessServerSocket(serverSocket);
	}

	/**
	 *
	 * @return the localAddress
	 */
	public String getLocalAddress() {
		return localAddress;
	}

	/**
	 * Used on multi-homed systems to enforce the server to listen
	 * on a specfic network address instead of all network adapters.
	 * @param localAddress the ip address of the required adapter.
	 */
	public void setLocalAddress(String localAddress) {
		this.localAddress = localAddress;
	}


	/**
	 * The number of sockets in the server connection backlog.
	 * @return The backlog.
	 */
	public int getBacklog() {
		return this.backlog;
	}

	/**
	 * The number of sockets in the connection backlog. Default 5;
	 * increase if you expect high connection rates.
	 * @param backlog The backlog to set.
	 */
	public void setBacklog(int backlog) {
		Assert.isTrue(backlog >= 0, "You cannot set backlog negative");
		this.backlog = backlog;
	}

	@Override
	public int beforeShutdown() {
		this.shuttingDown = true;
		return 0;
	}

	@Override
	public int afterShutdown() {
		stop();
		return 0;
	}

	protected void publishServerExceptionEvent(Exception e) {
		getApplicationEventPublisher().publishEvent(new TcpConnectionServerExceptionEvent(this, e));
	}

}


File: spring-integration-ip/src/main/java/org/springframework/integration/ip/tcp/connection/CachingClientConnectionFactory.java
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

package org.springframework.integration.ip.tcp.connection;

import java.util.HashMap;
import java.util.HashSet;
import java.util.Map;
import java.util.Set;
import java.util.concurrent.ConcurrentHashMap;
import java.util.concurrent.Executor;

import org.springframework.core.serializer.Deserializer;
import org.springframework.core.serializer.Serializer;
import org.springframework.integration.ip.IpHeaders;
import org.springframework.integration.support.AbstractIntegrationMessageBuilder;
import org.springframework.integration.util.SimplePool;
import org.springframework.messaging.Message;
import org.springframework.messaging.MessagingException;
import org.springframework.messaging.support.ErrorMessage;

/**
 * Connection factory that caches connections from the underlying target factory. The underlying
 * factory will be reconfigured to have {@code singleUse=true} in order for the connection to be
 * returned to the cache after use. Users should not subsequently set the underlying property to
 * false, or cache starvation will result.
 *
 * @author Gary Russell
 * @since 2.2
 *
 */
public class CachingClientConnectionFactory extends AbstractClientConnectionFactory implements CloseDeferrable {

	private final AbstractClientConnectionFactory targetConnectionFactory;

	private final SimplePool<TcpConnectionSupport> pool;

	private final Map<String, CachedConnection> deferredClosures =
			new ConcurrentHashMap<String, CachedConnection>();

	private final Set<String> okToRelease = new HashSet<String>();

	private volatile boolean deferClose;

	/**
	 * Construct a caching connection factory that delegates to the provided factory, with
	 * the provided pool size.
	 * @param target the target factory.
	 * @param poolSize the number of connections to allow.
	 */
	public CachingClientConnectionFactory(AbstractClientConnectionFactory target, int poolSize) {
		super("", 0);
		// override single-use to true to force "close" after use
		target.setSingleUse(true);
		this.targetConnectionFactory = target;
		this.pool = new SimplePool<TcpConnectionSupport>(poolSize,
				new SimplePool.PoolItemCallback<TcpConnectionSupport>() {

					@Override
					public TcpConnectionSupport createForPool() {
						try {
							return targetConnectionFactory.getConnection();
						}
						catch (Exception e) {
							throw new MessagingException("Failed to obtain connection", e);
						}
					}

					@Override
					public boolean isStale(TcpConnectionSupport connection) {
						return !connection.isOpen();
					}

					@Override
					public void removedFromPool(TcpConnectionSupport connection) {
						connection.close();
					}

				});
	}

	/**
	 * @param connectionWaitTimeout the new timeout.
	 * @see SimplePool#setWaitTimeout(long)
	 */
	public void setConnectionWaitTimeout(int connectionWaitTimeout) {
		this.pool.setWaitTimeout(connectionWaitTimeout);
	}

	/**
	 * @param poolSize the new pool size.
	 * @see SimplePool#setPoolSize(int)
	 */
	public synchronized void setPoolSize(int poolSize) {
		this.pool.setPoolSize(poolSize);
	}

	/**
	 * @see SimplePool#getPoolSize()
	 * @return the pool size.
	 */
	public int getPoolSize() {
		return this.pool.getPoolSize();
	}

	/**
	 * @see SimplePool#getIdleCount()
	 * @return the idle count.
	 */
	public int getIdleCount() {
		return this.pool.getIdleCount();
	}

	/**
	 * @see SimplePool#getActiveCount()
	 * @return the active count.
	 */
	public int getActiveCount() {
		return this.pool.getActiveCount();
	}

	/**
	 * @see SimplePool#getAllocatedCount()
	 * @return the allocated count.
	 */
	public int getAllocatedCount() {
		return this.pool.getAllocatedCount();
	}

	@Override
	public TcpConnectionSupport obtainConnection() throws Exception {
		return new CachedConnection(this.pool.getItem(), getListener());
	}

	@Override
	public void enableCloseDeferral(boolean defer) {
		this.deferClose = defer;
	}

	@Override
	public void closeDeferred(String connectionId) {
		synchronized(this.okToRelease) {
			CachedConnection deferred = this.deferredClosures.remove(connectionId);
			if (deferred != null) {
				deferred.doClose();
			}
			else {
				this.okToRelease.add(connectionId);
			}
		}
	}

	private class CachedConnection extends TcpConnectionInterceptorSupport {

		private volatile boolean released;

		public CachedConnection(TcpConnectionSupport connection, TcpListener tcpListener) {
			super.setTheConnection(connection);
			registerListener(tcpListener);
		}

		@Override
		public void close() {
			synchronized(okToRelease) {
				if (deferClose && !this.released && !okToRelease.remove(getConnectionId())) {
					deferredClosures.put(getConnectionId(), this);
				}
				else {
					doClose();
				}
			}
		}

		private synchronized void doClose() {
			if (this.released) {
				if (logger.isDebugEnabled()) {
					logger.debug("Connection " + getConnectionId() + " has already been released");
				}
			}
			else {
				/**
				 * If the delegate is stopped, actually close the connection, but still release
				 * it to the pool, it will be discarded/renewed the next time it is retrieved.
				 */
				if (!isRunning()) {
					if (logger.isDebugEnabled()) {
						logger.debug("Factory not running - closing " + getConnectionId());
					}
					super.close();
				}
				pool.releaseItem(getTheConnection());
				this.released = true;
			}
		}

		@Override
		public String getConnectionId() {
			return "Cached:" + super.getConnectionId();
		}

		@Override
		public String toString() {
			return getConnectionId();
		}

		/**
		 * We have to intercept the message to replace the connectionId header with
		 * ours so the listener can correlate a response with a request. We supply
		 * the actual connectionId in another header for convenience and tracing
		 * purposes.
		 */
		@Override
		public boolean onMessage(Message<?> message) {
			Message<?> modifiedMessage;
			if (message instanceof ErrorMessage) {
				Map<String, Object> headers = new HashMap<String, Object>(message.getHeaders());
				headers.put(IpHeaders.CONNECTION_ID, getConnectionId());
				if (headers.get(IpHeaders.ACTUAL_CONNECTION_ID) == null) {
					headers.put(IpHeaders.ACTUAL_CONNECTION_ID,
							message.getHeaders().get(IpHeaders.CONNECTION_ID));
				}
				modifiedMessage = new ErrorMessage((Throwable) message.getPayload(), headers);
			}
			else {
				AbstractIntegrationMessageBuilder<?> messageBuilder =
						CachingClientConnectionFactory.this.getMessageBuilderFactory()
								.fromMessage(message)
								.setHeader(IpHeaders.CONNECTION_ID, getConnectionId());
				if (message.getHeaders().get(IpHeaders.ACTUAL_CONNECTION_ID) == null) {
					messageBuilder.setHeader(IpHeaders.ACTUAL_CONNECTION_ID,
							message.getHeaders().get(IpHeaders.CONNECTION_ID));
				}
				modifiedMessage = messageBuilder.build();
			}
			TcpListener listener = getListener();
			if (listener != null) {
				listener.onMessage(modifiedMessage);
			}
			else {
				if (logger.isDebugEnabled()) {
					logger.debug("Message discarded; no listener: " + message);
				}
			}
			close(); // return to pool after response is received
			return true; // true so the single-use connection doesn't close itself
		}

		private void physicallyClose() {
			getTheConnection().close();
		}

	}

///////////////// DELEGATE METHODS ///////////////////////

	@Override
	public boolean isRunning() {
		return this.targetConnectionFactory.isRunning();
	}

	@Override
	public int hashCode() {
		return this.targetConnectionFactory.hashCode();
	}

	@Override
	public void setComponentName(String componentName) {
		this.targetConnectionFactory.setComponentName(componentName);
	}

	@Override
	public String getComponentType() {
		return this.targetConnectionFactory.getComponentType();
	}

	@Override
	public boolean equals(Object o) {
		if (this == o) {
			return true;
		}
		if (o == null || getClass() != o.getClass()) {
			return false;
		}

		CachingClientConnectionFactory that = (CachingClientConnectionFactory) o;

		return this.targetConnectionFactory.equals(that.targetConnectionFactory);

	}

	@Override
	public int getSoTimeout() {
		return this.targetConnectionFactory.getSoTimeout();
	}

	@Override
	public void setSoTimeout(int soTimeout) {
		this.targetConnectionFactory.setSoTimeout(soTimeout);
	}

	@Override
	public int getSoReceiveBufferSize() {
		return this.targetConnectionFactory.getSoReceiveBufferSize();
	}

	@Override
	public void setSoReceiveBufferSize(int soReceiveBufferSize) {
		this.targetConnectionFactory.setSoReceiveBufferSize(soReceiveBufferSize);
	}

	@Override
	public int getSoSendBufferSize() {
		return this.targetConnectionFactory.getSoSendBufferSize();
	}

	@Override
	public void setSoSendBufferSize(int soSendBufferSize) {
		this.targetConnectionFactory.setSoSendBufferSize(soSendBufferSize);
	}

	@Override
	public boolean isSoTcpNoDelay() {
		return this.targetConnectionFactory.isSoTcpNoDelay();
	}

	@Override
	public void setSoTcpNoDelay(boolean soTcpNoDelay) {
		this.targetConnectionFactory.setSoTcpNoDelay(soTcpNoDelay);
	}

	@Override
	public int getSoLinger() {
		return this.targetConnectionFactory.getSoLinger();
	}

	@Override
	public void setSoLinger(int soLinger) {
		this.targetConnectionFactory.setSoLinger(soLinger);
	}

	@Override
	public boolean isSoKeepAlive() {
		return this.targetConnectionFactory.isSoKeepAlive();
	}

	@Override
	public void setSoKeepAlive(boolean soKeepAlive) {
		this.targetConnectionFactory.setSoKeepAlive(soKeepAlive);
	}

	@Override
	public int getSoTrafficClass() {
		return this.targetConnectionFactory.getSoTrafficClass();
	}

	@Override
	public void setSoTrafficClass(int soTrafficClass) {
		this.targetConnectionFactory.setSoTrafficClass(soTrafficClass);
	}

	@Override
	public String getHost() {
		return this.targetConnectionFactory.getHost();
	}

	@Override
	public int getPort() {
		return this.targetConnectionFactory.getPort();
	}

	@Override
	public TcpSender getSender() {
		return this.targetConnectionFactory.getSender();
	}

	@Override
	public Serializer<?> getSerializer() {
		return this.targetConnectionFactory.getSerializer();
	}

	@Override
	public Deserializer<?> getDeserializer() {
		return this.targetConnectionFactory.getDeserializer();
	}

	@Override
	public TcpMessageMapper getMapper() {
		return this.targetConnectionFactory.getMapper();
	}

	/**
	 * Delegate TCP Client Connection factories that are used to receive
	 * data need a Listener to send the messages to.
	 * This applies to client factories used for outbound gateways
	 * or for a pair of collaborating channel adapters.
	 * <p>
	 * During initialization, if a factory detects it has no listener
	 * it's listening logic (active thread) is terminated.
	 * <p>
	 * The listener registered with a factory is provided to each
	 * connection it creates so it can call the onMessage() method.
	 * <p>
	 * This code satisfies the first requirement in that this
	 * listener signals to the factory that it needs to run
	 * its listening logic.
	 * <p>
	 * When we wrap actual connections with CachedConnections,
	 * the connection is given the wrapper as a listener, so it
	 * can enhance the headers in onMessage(); the wrapper then invokes
	 * the real listener supplied here, with the modified message.
	 */
	@Override
	public void registerListener(TcpListener listener) {
		super.registerListener(listener);
		this.targetConnectionFactory.enableManualListenerRegistration();
	}

	@Override
	public void registerSender(TcpSender sender) {
		this.targetConnectionFactory.registerSender(sender);
	}

	@Override
	public void setTaskExecutor(Executor taskExecutor) {
		this.targetConnectionFactory.setTaskExecutor(taskExecutor);
	}

	@Override
	public void setDeserializer(Deserializer<?> deserializer) {
		this.targetConnectionFactory.setDeserializer(deserializer);
	}

	@Override
	public void setSerializer(Serializer<?> serializer) {
		this.targetConnectionFactory.setSerializer(serializer);
	}

	@Override
	public void setMapper(TcpMessageMapper mapper) {
		this.targetConnectionFactory.setMapper(mapper);
	}

	@Override
	public boolean isSingleUse() {
		return this.targetConnectionFactory.isSingleUse();
	}

	/**
	 * Ignored on this factory; connections are always cached in the pool. The underlying
	 * connection factory will have its singleUse property coerced to true (causing the
	 * connection to be returned). Setting it to false on the underlying factory after initialization
	 * will cause cache starvation.
	 * @param singleUse the singleUse.
	 */
	@Override
	public void setSingleUse(boolean singleUse) {
		if (!singleUse && logger.isDebugEnabled()) {
			logger.debug("singleUse=false is not supported; cached connections are never closed");
		}
	}

	@Override
	public void setInterceptorFactoryChain(TcpConnectionInterceptorFactoryChain interceptorFactoryChain) {
		this.targetConnectionFactory.setInterceptorFactoryChain(interceptorFactoryChain);
	}

	@Override
	public void setLookupHost(boolean lookupHost) {
		this.targetConnectionFactory.setLookupHost(lookupHost);
	}

	@Override
	public boolean isLookupHost() {
		return this.targetConnectionFactory.isLookupHost();
	}


	@Override
	public void forceClose(TcpConnection connection) {
		if (connection instanceof CachedConnection) {
			((CachedConnection) connection).physicallyClose();
		}
		// will be returned to pool but stale, so will be re-established
		super.forceClose(connection);
	}

	@Override
	public void start() {
		setActive(true);
		this.targetConnectionFactory.start();
		super.start();
	}

	@Override
	public synchronized void stop() {
		this.targetConnectionFactory.stop();
		this.pool.removeAllIdleItems();
	}

	@Override
	public int getPhase() {
		return this.targetConnectionFactory.getPhase();
	}

	@Override
	public boolean isAutoStartup() {
		return this.targetConnectionFactory.isAutoStartup();
	}

	@Override
	public void stop(Runnable callback) {
		this.targetConnectionFactory.stop(callback);
	}

}


File: spring-integration-ip/src/main/java/org/springframework/integration/ip/tcp/connection/CloseDeferrable.java
/*
 * Copyright 2015 the original author or authors.
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
package org.springframework.integration.ip.tcp.connection;

/**
 * Temporary interface on the {@code CachingClientConnectionFactory} enabling the gateway
 * to defer the implicit close after onMessage so the connection is not reused until after the
 * gateway has completely finished with it. Will be removed when INT-3654 is resolved, whereby
 * the gateway will be completely responsible for the close.
 *
 * @author Gary Russell
 * @since 4.1.5
 *
 */
public interface CloseDeferrable {

	/**
	 * Enable deferred closure.
	 * @param defer true to defer.
	 */
	void enableCloseDeferral(boolean defer);

	/**
	 * Close (release) the connection if deferred.
	 * @param connectionId the connection id.
	 */
	void closeDeferred(String connectionId);

}


File: spring-integration-ip/src/main/java/org/springframework/integration/ip/tcp/connection/FailoverClientConnectionFactory.java
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
package org.springframework.integration.ip.tcp.connection;

import java.io.IOException;
import java.util.Iterator;
import java.util.List;
import java.util.UUID;
import java.util.concurrent.atomic.AtomicLong;

import javax.net.ssl.SSLSession;

import org.springframework.core.serializer.Deserializer;
import org.springframework.core.serializer.Serializer;
import org.springframework.integration.ip.IpHeaders;
import org.springframework.integration.support.AbstractIntegrationMessageBuilder;
import org.springframework.messaging.Message;
import org.springframework.messaging.support.ErrorMessage;
import org.springframework.util.Assert;

/**
 * Given a list of connection factories, serves up {@link TcpConnection}s
 * that can iterate over a connection from each factory until the write
 * succeeds or the list is exhausted.
 * @author Gary Russell
 * @since 2.2
 *
 */
public class FailoverClientConnectionFactory extends AbstractClientConnectionFactory {

	private final List<AbstractClientConnectionFactory> factories;

	public FailoverClientConnectionFactory(List<AbstractClientConnectionFactory> factories) {
		super("", 0);
		Assert.notEmpty(factories, "At least one factory is required");
		this.factories = factories;
	}

	@Override
	protected void onInit() throws Exception {
		super.onInit();
		for (AbstractClientConnectionFactory factory : factories) {
			Assert.state(!(this.isSingleUse() ^ factory.isSingleUse()),
				"Inconsistent singleUse - delegate factories must match this one");
		}
	}

	/**
	 * Delegate TCP Client Connection factories that are used to receive
	 * data need a Listener to send the messages to.
	 * This applies to client factories used for outbound gateways
	 * or for a pair of collaborating channel adapters.
	 * <p>
	 * During initialization, if a factory detects it has no listener
	 * it's listening logic (active thread) is terminated.
	 * <p>
	 * The listener registered with a factory is provided to each
	 * connection it creates so it can call the onMessage() method.
	 * <p>
	 * This code satisfies the first requirement in that this
	 * listener signals to the factory that it needs to run
	 * its listening logic.
	 * <p>
	 * When we wrap actual connections with FailoverTcpConnections,
	 * the connection is given the wrapper as a listener, so it
	 * can enhance the headers in onMessage(); the wrapper then invokes
	 * the real listener supplied here, with the modified message.
	 */
	@Override
	public void registerListener(TcpListener listener) {
		super.registerListener(listener);
		for (AbstractClientConnectionFactory factory : this.factories) {
			factory.registerListener(new TcpListener() {
				@Override
				public boolean onMessage(Message<?> message) {
					if (!(message instanceof ErrorMessage)) {
						throw new UnsupportedOperationException("This should never be called");
					}
					return false;
				}
			});
		}
	}

	@Override
	public void enableManualListenerRegistration() {
		for (AbstractClientConnectionFactory factory : this.factories) {
			factory.enableManualListenerRegistration();
		}
	}

	@Override
	public void registerSender(TcpSender sender) {
		for (AbstractClientConnectionFactory factory : this.factories) {
			factory.registerSender(sender);
		}
	}

	@Override
	protected TcpConnectionSupport obtainConnection() throws Exception {
		TcpConnectionSupport connection = this.getTheConnection();
		if (connection != null && connection.isOpen()) {
			((FailoverTcpConnection) connection).incrementEpoch();
			return connection;
		}
		FailoverTcpConnection failoverTcpConnection = new FailoverTcpConnection(this.factories);
		failoverTcpConnection.registerListener(this.getListener());
		failoverTcpConnection.incrementEpoch();
		return failoverTcpConnection;
	}


	@Override
	public void start() {
		for (AbstractClientConnectionFactory factory : this.factories) {
			factory.start();
		}
		this.setActive(true);
		super.start();
	}

	@Override
	public void stop() {
		this.setActive(false);
		for (AbstractClientConnectionFactory factory : this.factories) {
			factory.stop();
		}
	}

	/**
	 * Returns true if all factories are running
	 */
	@Override
	public boolean isRunning() {
		boolean isRunning = true;
		for (AbstractClientConnectionFactory factory : this.factories) {
			isRunning = !isRunning ? false : factory.isRunning();
		}
		return isRunning;
	}

	/**
	 * Wrapper for a list of factories; delegates to a connection from
	 * one of those factories and fails over to another if necessary.
	 * @author Gary Russell
	 * @since 2.2
	 *
	 */
	private class FailoverTcpConnection extends TcpConnectionSupport implements TcpListener {

		private final List<AbstractClientConnectionFactory> factories;

		private final String connectionId;

		private volatile Iterator<AbstractClientConnectionFactory> factoryIterator;

		private volatile AbstractClientConnectionFactory currentFactory;

		private volatile TcpConnectionSupport delegate;

		private volatile boolean open = true;

		private final AtomicLong epoch = new AtomicLong();

		public FailoverTcpConnection(List<AbstractClientConnectionFactory> factories) throws Exception {
			this.factories = factories;
			this.factoryIterator = factories.iterator();
			findAConnection();
			this.connectionId = UUID.randomUUID().toString();
		}

		void incrementEpoch() {
			this.epoch.incrementAndGet();
		}

		/**
		 * Finds a connection from the underlying list of factories. If necessary,
		 * each factory is tried; including the current one if we wrap around.
		 * This allows for the condition where the current connection is closed,
		 * the current factory can serve up a new connection, but all other
		 * factories are down.
		 * @throws Exception
		 */
		private synchronized void findAConnection() throws Exception {
			boolean success = false;
			AbstractClientConnectionFactory lastFactoryToTry = this.currentFactory;
			AbstractClientConnectionFactory nextFactory = null;
			if (!this.factoryIterator.hasNext()) {
				this.factoryIterator = this.factories.iterator();
			}
			boolean retried = false;
			while (!success) {
				try {
					nextFactory = this.factoryIterator.next();
					this.delegate = nextFactory.getConnection();
					this.delegate.registerListener(this);
					this.currentFactory = nextFactory;
					success = this.delegate.isOpen();
				}
				catch (IOException e) {
					if (!this.factoryIterator.hasNext()) {
						if (retried && lastFactoryToTry == null || lastFactoryToTry == nextFactory) {
							/*
							 *  We've tried every factory including the
							 *  one the current connection was on.
							 */
							this.open = false;
							throw e;
						}
						this.factoryIterator = this.factories.iterator();
						retried = true;
					}
				}
			}
		}

		@Override
		public void close() {
			this.delegate.close();
			this.open = false;
		}

		@Override
		public boolean isOpen() {
			return this.open;
		}

		/**
		 * Sends to the current connection; if it fails, attempts to
		 * send to a new connection obtained from {@link #findAConnection()}.
		 * If send fails on a connection from every factory, we give up.
		 */
		@Override
		public synchronized void send(Message<?> message) throws Exception {
			boolean success = false;
			AbstractClientConnectionFactory lastFactoryToTry = this.currentFactory;
			AbstractClientConnectionFactory lastFactoryTried = null;
			boolean retried = false;
			while (!success) {
				try {
					lastFactoryTried = this.currentFactory;
					this.delegate.send(message);
					success = true;
				}
				catch (IOException e) {
					if (retried && lastFactoryTried == lastFactoryToTry) {
						logger.error("All connection factories exhausted", e);
						this.open = false;
						throw e;
					}
					retried = true;
					if (logger.isDebugEnabled()) {
						logger.debug("Send to " + this.delegate.getConnectionId() + " failed; attempting failover", e);
					}
					this.delegate.close();
					findAConnection();
					if (logger.isDebugEnabled()) {
						logger.debug("Failing over to " + this.delegate.getConnectionId());
					}
				}
			}
		}

		@Override
		public Object getPayload() throws Exception {
			return this.delegate.getPayload();
		}

		@Override
		public void run() {
			throw new UnsupportedOperationException("Not supported on FailoverTcpConnection");
		}

		@Override
		public String getHostName() {
			return this.delegate.getHostName();
		}

		@Override
		public String getHostAddress() {
			return this.delegate.getHostAddress();
		}

		@Override
		public int getPort() {
			return this.delegate.getPort();
		}

		@Override
		public Object getDeserializerStateKey() {
			return this.delegate.getDeserializerStateKey();
		}

		@Override
		public void registerSender(TcpSender sender) {
			this.delegate.registerSender(sender);
		}

		@Override
		public String getConnectionId() {
			return this.connectionId + ":" + epoch;
		}

		@Override
		public void setSingleUse(boolean singleUse) {
			this.delegate.setSingleUse(singleUse);
		}

		@Override
		public boolean isSingleUse() {
			return this.delegate.isSingleUse();
		}

		@Override
		public boolean isServer() {
			return this.delegate.isServer();
		}

		@Override
		public void setMapper(TcpMessageMapper mapper) {
			this.delegate.setMapper(mapper);
		}

		@Override
		public Deserializer<?> getDeserializer() {
			return this.delegate.getDeserializer();
		}

		@Override
		public void setDeserializer(Deserializer<?> deserializer) {
			this.delegate.setDeserializer(deserializer);
		}

		@Override
		public Serializer<?> getSerializer() {
			return this.delegate.getSerializer();
		}

		@Override
		public void setSerializer(Serializer<?> serializer) {
			this.delegate.setSerializer(serializer);
		}

		@Override
		public SSLSession getSslSession() {
			return this.delegate.getSslSession();
		}

		/**
		 * We have to intercept the message to replace the connectionId header with
		 * ours so the listener can correlate a response with a request. We supply
		 * the actual connectionId in another header for convenience and tracing
		 * purposes.
		 */
		@Override
		public boolean onMessage(Message<?> message) {
			if (this.delegate.getConnectionId().equals(message.getHeaders().get(IpHeaders.CONNECTION_ID))) {
				AbstractIntegrationMessageBuilder<?> messageBuilder = FailoverClientConnectionFactory.this
						.getMessageBuilderFactory().fromMessage(message)
							.setHeader(IpHeaders.CONNECTION_ID, this.getConnectionId());
				if (message.getHeaders().get(IpHeaders.ACTUAL_CONNECTION_ID) == null) {
					messageBuilder.setHeader(IpHeaders.ACTUAL_CONNECTION_ID,
							message.getHeaders().get(IpHeaders.CONNECTION_ID));
				}
				return this.getListener().onMessage(messageBuilder.build());
			}
			else {
				if (logger.isDebugEnabled()) {
					logger.debug("Message from defunct connection ignored " + message);
				}
				return false;
			}
		}

	}
}


File: spring-integration-ip/src/main/java/org/springframework/integration/ip/tcp/connection/TcpConnection.java
/*
 * Copyright 2001-2015 the original author or authors.
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

package org.springframework.integration.ip.tcp.connection;

import java.net.Socket;
import java.nio.channels.SocketChannel;

import javax.net.ssl.SSLSession;

import org.springframework.core.serializer.Deserializer;
import org.springframework.core.serializer.Serializer;
import org.springframework.messaging.Message;

/**
 * An abstraction over {@link Socket} and {@link SocketChannel} that
 * sends {@link Message} objects by serializing the payload
 * and streaming it to the destination. Requires a {@link TcpListener}
 * to receive incoming messages.
 *
 * @author Gary Russell
 * @since 2.0
 *
 */
public interface TcpConnection extends Runnable {

	/**
	 * Closes the connection.
	 */
	void close();

	/**
	 * @return true if the connection is open.
	 */
	boolean isOpen();

	/**
	 * Converts and sends the message.
	 * @param message The message,
	 * @throws Exception Any Exception.
	 */
	void send(Message<?> message) throws Exception;

	/**
	 * Uses the deserializer to obtain the message payload
	 * from the connection's input stream.
	 * @return The payload.
	 * @throws Exception Any Exception.
	 */
	Object getPayload() throws Exception;

	/**
	 * @return the host name
	 */
	String getHostName();

	/**
	 * @return the host address
	 */
	String getHostAddress();

	/**
	 * @return the port
	 */
	int getPort();

	/**
	 * @return a string uniquely representing a connection.
	 */
	String getConnectionId();

	/**
	 *
	 * @return True if connection is used once.
	 */
	boolean isSingleUse();

	/**
	 *
	 * @return True if connection is used once.
	 */
	boolean isServer();

	/**
	 *
	 * @return the deserializer
	 */
	Deserializer<?> getDeserializer();

	/**
	 *
	 * @return the serializer
	 */
	Serializer<?> getSerializer();

	/**
	 * @return this connection's listener
	 */
	TcpListener getListener();

	/**
	 * @return the next sequence number for a message received on this socket
	 */
	long incrementAndGetConnectionSequence();

	/**
	 * @return a key that can be used to reference state in a {@link Deserializer} that
	 * maintains state for this connection. Currently, this would be the InputStream
	 * associated with the connection, but the object should be treated as opaque
	 * and ONLY used as a key.
	 */
	Object getDeserializerStateKey();

	/**
	 * @return the {@link SSLSession} associated with this connection, if SSL is in use,
	 * null otherwise.
	 * @since 4.2
	 */
	SSLSession getSslSession();

}


File: spring-integration-ip/src/main/java/org/springframework/integration/ip/tcp/connection/TcpConnectionInterceptorSupport.java
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

package org.springframework.integration.ip.tcp.connection;

import javax.net.ssl.SSLSession;

import org.springframework.context.ApplicationEventPublisher;
import org.springframework.core.serializer.Deserializer;
import org.springframework.core.serializer.Serializer;
import org.springframework.messaging.Message;
import org.springframework.messaging.support.ErrorMessage;

/**
 * Base class for TcpConnectionIntercepters; passes all method calls through
 * to the underlying {@link TcpConnection}.
 *
 * @author Gary Russell
 * @since 2.0
 */
public abstract class TcpConnectionInterceptorSupport extends TcpConnectionSupport implements TcpConnectionInterceptor {

	private TcpConnectionSupport theConnection;

	private TcpListener tcpListener;

	private TcpSender tcpSender;

	private Boolean realSender;

	public TcpConnectionInterceptorSupport() {
		super();
	}

	public TcpConnectionInterceptorSupport(ApplicationEventPublisher applicationEventPublisher) {
		super(applicationEventPublisher);
	}

	@Override
	public void close() {
		this.theConnection.close();
	}

	@Override
	public boolean isOpen() {
		return this.theConnection.isOpen();
	}

	@Override
	public Object getPayload() throws Exception {
		return this.theConnection.getPayload();
	}

	@Override
	public String getHostName() {
		return this.theConnection.getHostName();
	}

	@Override
	public String getHostAddress() {
		return this.theConnection.getHostAddress();
	}

	@Override
	public int getPort() {
		return this.theConnection.getPort();
	}

	@Override
	public Object getDeserializerStateKey() {
		return this.theConnection.getDeserializerStateKey();
	}

	@Override
	public void registerListener(TcpListener listener) {
		this.tcpListener = listener;
		this.theConnection.registerListener(this);
	}

	@Override
	public void registerSender(TcpSender sender) {
		this.tcpSender = sender;
		this.theConnection.registerSender(this);
	}

	@Override
	public String getConnectionId() {
		return this.theConnection.getConnectionId();
	}

	@Override
	public boolean isSingleUse() {
		return this.theConnection.isSingleUse();
	}

	@Override
	public void run() {
		this.theConnection.run();
	}

	@Override
	public void setSingleUse(boolean singleUse) {
		this.theConnection.setSingleUse(singleUse);
	}

	@Override
	public void setMapper(TcpMessageMapper mapper) {
		this.theConnection.setMapper(mapper);
	}

	@Override
	public Deserializer<?> getDeserializer() {
		return this.theConnection.getDeserializer();
	}

	@Override
	public void setDeserializer(Deserializer<?> deserializer) {
		this.theConnection.setDeserializer(deserializer);
	}

	@Override
	public Serializer<?> getSerializer() {
		return this.theConnection.getSerializer();
	}

	@Override
	public void setSerializer(Serializer<?> serializer) {
		this.theConnection.setSerializer(serializer);
	}

	@Override
	public boolean isServer() {
		return this.theConnection.isServer();
	}

	@Override
	public SSLSession getSslSession() {
		return this.theConnection.getSslSession();
	}

	@Override
	public boolean onMessage(Message<?> message) {
		if (this.tcpListener == null) {
			if (message instanceof ErrorMessage) {
				return false;
			}
			else {
				throw new NoListenerException("No listener registered for message reception");
			}
		}
		return this.tcpListener.onMessage(message);
	}

	@Override
	public void send(Message<?> message) throws Exception {
		this.theConnection.send(message);
	}

	/**
	 * Returns the underlying connection (or next interceptor)
	 * @return the connection
	 */
	public TcpConnectionSupport getTheConnection() {
		return this.theConnection;
	}

	/**
	 * Sets the underlying connection (or next interceptor)
	 * @param theConnection the connection
	 */
	public void setTheConnection(TcpConnectionSupport theConnection) {
		this.theConnection = theConnection;
	}

	/**
	 * @return the listener
	 */
	@Override
	public TcpListener getListener() {
		return tcpListener;
	}

	@Override
	public void addNewConnection(TcpConnection connection) {
		if (this.tcpSender != null) {
			this.tcpSender.addNewConnection(this);
		}
	}

	@Override
	public void removeDeadConnection(TcpConnection connection) {
		if (this.tcpSender != null) {
			this.tcpSender.removeDeadConnection(this);
		}
	}

	@Override
	public long incrementAndGetConnectionSequence() {
		return this.theConnection.incrementAndGetConnectionSequence();
	}

	@Override
	public TcpSender getSender() {
		return this.tcpSender;
	}

	protected boolean hasRealSender() {
		if (this.realSender != null) {
			return this.realSender;
		}
		TcpSender sender = this.getSender();
		while (sender instanceof TcpConnectionInterceptorSupport) {
			sender = ((TcpConnectionInterceptorSupport) sender).getSender();
		}
		this.realSender = sender != null;
		return this.realSender;
	}

}


File: spring-integration-ip/src/main/java/org/springframework/integration/ip/tcp/connection/TcpConnectionSupport.java
/*
 * Copyright 2001-2015 the original author or authors.
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

package org.springframework.integration.ip.tcp.connection;

import java.net.InetAddress;
import java.net.Socket;
import java.net.SocketException;
import java.util.Collections;
import java.util.Map;
import java.util.UUID;
import java.util.concurrent.CountDownLatch;
import java.util.concurrent.TimeUnit;
import java.util.concurrent.atomic.AtomicBoolean;
import java.util.concurrent.atomic.AtomicLong;

import org.apache.commons.logging.Log;
import org.apache.commons.logging.LogFactory;

import org.springframework.context.ApplicationEventPublisher;
import org.springframework.core.serializer.Deserializer;
import org.springframework.core.serializer.Serializer;
import org.springframework.integration.ip.IpHeaders;
import org.springframework.integration.ip.tcp.serializer.AbstractByteArraySerializer;
import org.springframework.messaging.Message;
import org.springframework.messaging.MessagingException;
import org.springframework.messaging.support.ErrorMessage;
import org.springframework.util.Assert;

/**
 * Base class for TcpConnections. TcpConnections are established by
 * client connection factories (outgoing) or server connection factories
 * (incoming).
 *
 * @author Gary Russell
 * @since 2.0
 *
 */
public abstract class TcpConnectionSupport implements TcpConnection {

	protected final Log logger = LogFactory.getLog(this.getClass());

	private final CountDownLatch listenerRegisteredLatch = new CountDownLatch(1);

	@SuppressWarnings("rawtypes")
	private volatile Deserializer deserializer;

	@SuppressWarnings("rawtypes")
	private volatile Serializer serializer;

	private volatile TcpMessageMapper mapper;

	private volatile TcpListener listener;

	private volatile TcpListener actualListener;

	private volatile TcpSender sender;

	private volatile boolean singleUse;

	private final boolean server;

	private volatile String connectionId;

	private final AtomicLong sequence = new AtomicLong();

	private volatile int soLinger = -1;

	private volatile String hostName = "unknown";

	private volatile String hostAddress = "unknown";

	private volatile String connectionFactoryName = "unknown";

	private final ApplicationEventPublisher applicationEventPublisher;

	private final AtomicBoolean closePublished = new AtomicBoolean();

	private final AtomicBoolean exceptionSent = new AtomicBoolean();

	private volatile boolean noReadErrorOnClose;

	private volatile boolean manualListenerRegistration;

	public TcpConnectionSupport() {
		this(null);
	}

	public TcpConnectionSupport(ApplicationEventPublisher applicationEventPublisher) {
		this.server = false;
		this.applicationEventPublisher = applicationEventPublisher;
	}

	/**
	 * Creates a {@link TcpConnectionSupport} object and publishes a
	 * {@link TcpConnectionOpenEvent}, if an event publisher is provided.
	 * @param socket the underlying socket.
	 * @param server true if this connection is a server connection
	 * @param lookupHost true if reverse lookup of the host name should be performed,
	 * otherwise, the ip address will be used for identification purposes.
	 * @param applicationEventPublisher the publisher to which open, close and exception events will
	 * be sent; may be null if event publishing is not required.
	 * @param connectionFactoryName the name of the connection factory creating this connection; used
	 * during event publishing, may be null, in which case "unknown" will be used.
	 */
	public TcpConnectionSupport(Socket socket, boolean server, boolean lookupHost,
			ApplicationEventPublisher applicationEventPublisher,
			String connectionFactoryName) {
		this.server = server;
		InetAddress inetAddress = socket.getInetAddress();
		if (inetAddress != null) {
			this.hostAddress = inetAddress.getHostAddress();
			if (lookupHost) {
				this.hostName = inetAddress.getHostName();
			}
			else {
				this.hostName = this.hostAddress;
			}
		}
		int port = socket.getPort();
		int localPort = socket.getLocalPort();
		this.connectionId = this.hostName + ":" + port + ":" + localPort + ":" + UUID.randomUUID().toString();
		try {
			this.soLinger = socket.getSoLinger();
		}
		catch (SocketException e) { }
		this.applicationEventPublisher = applicationEventPublisher;
		if (connectionFactoryName != null) {
			this.connectionFactoryName = connectionFactoryName;
		}
		if (logger.isDebugEnabled()) {
			logger.debug("New connection " + this.getConnectionId());
		}
	}

	public void afterSend(Message<?> message) throws Exception {
		if (logger.isDebugEnabled()) {
			logger.debug("Message sent " + message);
		}
		if (this.singleUse) {
			// if (we're a server socket, or a send-only socket), and soLinger <> 0, close
			if ((this.isServer() || this.actualListener == null) && this.soLinger != 0) {
				if (logger.isDebugEnabled()) {
					logger.debug("Closing single-use connection" + this.getConnectionId());
				}
				this.closeConnection(false);
			}
		}
	}

	/**
	 * Closes this connection.
	 */
	@Override
	public void close() {
		if (this.sender != null) {
			this.sender.removeDeadConnection(this);
		}
		// close() may be called multiple times; only publish once
		if (!this.closePublished.getAndSet(true)) {
			this.publishConnectionCloseEvent();
		}
	}

	/**
	 * If we have been intercepted, propagate the close from the outermost interceptor;
	 * otherwise, just call close().
	 *
	 * @param isException true when this call is the result of an Exception.
	 */
	protected void closeConnection(boolean isException) {
		TcpListener listener = getListener();
		if (!(listener instanceof TcpConnectionInterceptor)) {
			close();
		}
		else {
			TcpConnectionInterceptor outerInterceptor = (TcpConnectionInterceptor) listener;
			while (outerInterceptor.getListener() instanceof TcpConnectionInterceptor) {
				outerInterceptor = (TcpConnectionInterceptor) outerInterceptor.getListener();
			}
			outerInterceptor.close();
			if (isException) {
				// ensure physical close in case the interceptor did not close
				this.close();
			}
		}
	}

	/**
	 * @return the mapper
	 */
	public TcpMessageMapper getMapper() {
		return mapper;
	}

	/**
	 * @param mapper the mapper to set
	 */
	public void setMapper(TcpMessageMapper mapper) {
		Assert.notNull(mapper, this.getClass().getName() + " Mapper may not be null");
		this.mapper = mapper;
		if (this.serializer != null &&
			 !(this.serializer instanceof AbstractByteArraySerializer)) {
			mapper.setStringToBytes(false);
		}
	}

	/**
	 *
	 * @return the deserializer
	 */
	@Override
	public Deserializer<?> getDeserializer() {
		return this.deserializer;
	}

	/**
	 * @param deserializer the deserializer to set
	 */
	public void setDeserializer(Deserializer<?> deserializer) {
		this.deserializer = deserializer;
	}

	/**
	 *
	 * @return the serializer
	 */
	@Override
	public Serializer<?> getSerializer() {
		return this.serializer;
	}

	/**
	 * @param serializer the serializer to set
	 */
	public void setSerializer(Serializer<?> serializer) {
		this.serializer = serializer;
		if (!(serializer instanceof AbstractByteArraySerializer)) {
			this.mapper.setStringToBytes(false);
		}
	}

	/**
	 * Set the listener that will receive incoming Messages.
	 * @param listener The listener.
	 */
	public void registerListener(TcpListener listener) {
		this.listener = listener;
		// Determine the actual listener for this connection
		if (!(this.listener instanceof TcpConnectionInterceptor)) {
			this.actualListener = this.listener;
		}
		else {
			TcpConnectionInterceptor outerInterceptor = (TcpConnectionInterceptor) this.listener;
			while (outerInterceptor.getListener() instanceof TcpConnectionInterceptor) {
				outerInterceptor = (TcpConnectionInterceptor) outerInterceptor.getListener();
			}
			this.actualListener = outerInterceptor.getListener();
		}
		this.listenerRegisteredLatch.countDown();
	}

	/**
	 * Set whether or not automatic or manual registration of the {@link TcpListener} is to be
	 * used. (Default automatic). When manual registration is in place, incoming messages will
	 * be delayed until the listener is registered.
	 * @since 1.4.5
	 */
	public void enableManualListenerRegistration() {
		this.manualListenerRegistration = true;
		this.listener = new TcpListener() {

			@Override
			public boolean onMessage(Message<?> message) {
				return getListener().onMessage(message);
			}

		};
	}

	/**
	 * Registers a sender. Used on server side connections so a
	 * sender can determine which connection to send a reply
	 * to.
	 * @param sender the sender.
	 */
	public void registerSender(TcpSender sender) {
		this.sender = sender;
		if (sender != null) {
			sender.addNewConnection(this);
		}
	}

	/**
	 * @return the listener
	 */
	@Override
	public TcpListener getListener() {
		if (this.manualListenerRegistration) {
			waitForListenerRegistration();
		}
		return this.listener;
	}

	private void waitForListenerRegistration() {
		try {
			Assert.state(listenerRegisteredLatch.await(1, TimeUnit.MINUTES), "TcpListener not registered");
			manualListenerRegistration = false;
		}
		catch (InterruptedException e) {
			Thread.currentThread().interrupt();
			throw new MessagingException("Interrupted while waiting for listener registration", e);
		}
	}

	/**
	 * @return the sender
	 */
	public TcpSender getSender() {
		return sender;
	}

	/**
	 * @param singleUse true if this socket is to used once and
	 * discarded.
	 */
	public void setSingleUse(boolean singleUse) {
		this.singleUse = singleUse;
	}

	/**
	 *
	 * @return True if connection is used once.
	 */
	@Override
	public boolean isSingleUse() {
		return this.singleUse;
	}

	@Override
	public boolean isServer() {
		return server;
	}

	@Override
	public long incrementAndGetConnectionSequence() {
		return this.sequence.incrementAndGet();
	}

	@Override
	public String getHostAddress() {
		return this.hostAddress;
	}

	@Override
	public String getHostName() {
		return this.hostName;
	}

	@Override
	public String getConnectionId() {
		return this.connectionId;
	}

	protected boolean isNoReadErrorOnClose() {
		return noReadErrorOnClose;
	}

	protected void setNoReadErrorOnClose(boolean noReadErrorOnClose) {
		this.noReadErrorOnClose = noReadErrorOnClose;
	}

	protected final void sendExceptionToListener(Exception e) {
		if (!this.exceptionSent.getAndSet(true) && this.getListener() != null) {
			Map<String, Object> headers = Collections.singletonMap(IpHeaders.CONNECTION_ID,
					(Object) this.getConnectionId());
			ErrorMessage errorMessage = new ErrorMessage(e, headers);
			this.getListener().onMessage(errorMessage);
		}
	}

	protected void publishConnectionOpenEvent() {
		TcpConnectionEvent event = new TcpConnectionOpenEvent(this,
				this.connectionFactoryName);
		doPublish(event);
	}

	protected void publishConnectionCloseEvent() {
		TcpConnectionEvent event = new TcpConnectionCloseEvent(this,
				this.connectionFactoryName);
		doPublish(event);
	}

	protected void publishConnectionExceptionEvent(Throwable t) {
		TcpConnectionEvent event = new TcpConnectionExceptionEvent(this,
				this.connectionFactoryName, t);
		doPublish(event);
	}

	/**
	 * Allow interceptors etc to publish events, perhaps subclasses of
	 * TcpConnectionEvent. The event source must be this connection.
	 * @param event the event to publish.
	 */
	public void publishEvent(TcpConnectionEvent event) {
		Assert.isTrue(event.getSource() == this, "Can only publish events with this as the source");
		this.doPublish(event);
	}

	private void doPublish(TcpConnectionEvent event) {
		try {
			if (this.applicationEventPublisher == null) {
				logger.warn("No publisher available to publish " + event);
			}
			else {
				this.applicationEventPublisher.publishEvent(event);
			}
		}
		catch (Exception e) {
			if (logger.isDebugEnabled()) {
				logger.debug("Failed to publish " + event, e);
			}
			else if (logger.isWarnEnabled()) {
				logger.warn("Failed to publish " + event + ":" + e.getMessage());
			}
		}
	}

}


File: spring-integration-ip/src/main/java/org/springframework/integration/ip/tcp/connection/TcpNetConnection.java
/*
 * Copyright 2001-2015 the original author or authors.
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

package org.springframework.integration.ip.tcp.connection;

import java.io.BufferedOutputStream;
import java.io.OutputStream;
import java.net.Socket;
import java.net.SocketException;
import java.net.SocketTimeoutException;

import javax.net.ssl.SSLSession;
import javax.net.ssl.SSLSocket;

import org.springframework.context.ApplicationEventPublisher;
import org.springframework.core.serializer.Deserializer;
import org.springframework.core.serializer.Serializer;
import org.springframework.integration.ip.tcp.serializer.SoftEndOfStreamException;
import org.springframework.messaging.Message;
import org.springframework.messaging.MessagingException;
import org.springframework.scheduling.SchedulingAwareRunnable;

/**
 * A TcpConnection that uses and underlying {@link Socket}.
 *
 * @author Gary Russell
 * @since 2.0
 *
 */
public class TcpNetConnection extends TcpConnectionSupport implements SchedulingAwareRunnable {

	private final Socket socket;

	private volatile OutputStream socketOutputStream;

	private volatile long lastRead = System.currentTimeMillis();

	private volatile long lastSend;

	/**
	 * Constructs a TcpNetConnection for the socket.
	 * @param socket the socket
	 * @param server if true this connection was created as
	 * a result of an incoming request.
	 * @param lookupHost true if hostname lookup should be performed, otherwise the connection will
	 * be identified using the ip address.
	 * @param applicationEventPublisher the publisher to which OPEN, CLOSE and EXCEPTION events will
	 * be sent; may be null if event publishing is not required.
	 * @param connectionFactoryName the name of the connection factory creating this connection; used
	 * during event publishing, may be null, in which case "unknown" will be used.
	 */
	public TcpNetConnection(Socket socket, boolean server, boolean lookupHost,
			ApplicationEventPublisher applicationEventPublisher, String connectionFactoryName) {
		super(socket, server, lookupHost, applicationEventPublisher, connectionFactoryName);
		this.socket = socket;
	}

	@Override
	public boolean isLongLived() {
		return true;
	}

	/**
	 * Closes this connection.
	 */
	@Override
	public void close() {
		this.setNoReadErrorOnClose(true);
		try {
			this.socket.close();
		}
		catch (Exception e) {}
		super.close();
	}

	@Override
	public boolean isOpen() {
		return !this.socket.isClosed();
	}

	@Override
	@SuppressWarnings("unchecked")
	public synchronized void send(Message<?> message) throws Exception {
		if (this.socketOutputStream == null) {
			int writeBufferSize = this.socket.getSendBufferSize();
			this.socketOutputStream = new BufferedOutputStream(socket.getOutputStream(),
					writeBufferSize > 0 ? writeBufferSize : 8192);
		}
		Object object = this.getMapper().fromMessage(message);
		this.lastSend = System.currentTimeMillis();
		try {
			((Serializer<Object>) this.getSerializer()).serialize(object, this.socketOutputStream);
			this.socketOutputStream.flush();
		}
		catch (Exception e) {
			this.publishConnectionExceptionEvent(new MessagingException(message, e));
			this.closeConnection(true);
			throw e;
		}
		this.afterSend(message);
	}

	@Override
	public Object getPayload() throws Exception {
		return this.getDeserializer().deserialize(this.socket.getInputStream());
	}

	@Override
	public int getPort() {
		return this.socket.getPort();
	}

	@Override
	public Object getDeserializerStateKey() {
		try {
			return this.socket.getInputStream();
		}
		catch (Exception e) {
			return null;
		}
	}

	@Override
	public SSLSession getSslSession() {
		if (this.socket instanceof SSLSocket) {
			return ((SSLSocket) this.socket).getSession();
		}
		else {
			return null;
		}
	}

	/**
	 * If there is no listener, and this connection is not for single use,
	 * this method exits. When there is a listener, the method runs in a
	 * loop reading input from the connection's stream, data is converted
	 * to an object using the {@link Deserializer} and the listener's
	 * {@link TcpListener#onMessage(Message)} method is called. For single use
	 * connections with no listener, the socket is closed after its timeout
	 * expires. If data is received on a single use socket with no listener,
	 * a warning is logged.
	 */
	@Override
	public void run() {
		boolean singleUse = this.isSingleUse();
		TcpListener listener = this.getListener();
		if (listener == null && !singleUse) {
			logger.debug("TcpListener exiting - no listener and not single use");
			return;
		}
		boolean okToRun = true;
		if (logger.isDebugEnabled()) {
			logger.debug(this.getConnectionId() + " Reading...");
		}
		boolean intercepted = false;
		while (okToRun) {
			Message<?> message = null;
			try {
				message = this.getMapper().toMessage(this);
				this.lastRead = System.currentTimeMillis();
			}
			catch (Exception e) {
				this.publishConnectionExceptionEvent(e);
				if (handleReadException(e)) {
					okToRun = false;
				}
			}
			if (okToRun && message != null) {
				if (logger.isDebugEnabled()) {
					logger.debug("Message received " + message);
				}
				try {
					if (listener == null) {
						logger.warn("Unexpected message - no inbound adapter registered with connection " + message);
						continue;
					}
					intercepted = this.getListener().onMessage(message);
				}
				catch (NoListenerException nle) {
					if (singleUse) {
						logger.debug("Closing single use socket after inbound message " + this.getConnectionId());
						this.closeConnection(true);
						okToRun = false;
					} else {
						logger.warn("Unexpected message - no inbound adapter registered with connection " + message);
					}
				}
				catch (Exception e2) {
					logger.error("Exception sending message: " + message, e2);
				}
				/*
				 * For single use sockets, we close after receipt if we are on the client
				 * side, and the data was not intercepted,
				 * or the server side has no outbound adapter registered
				 */
				if (singleUse && ((!this.isServer() && !intercepted) || (this.isServer() && this.getSender() == null))) {
					logger.debug("Closing single use socket after inbound message " + this.getConnectionId());
					this.closeConnection(false);
					okToRun = false;
				}
			}
		}
	}

	protected boolean handleReadException(Exception e) {
		boolean doClose = true;
		/*
		 * For client connections, we have to wait for 2 timeouts if the last
		 * send was within the current timeout.
		 */
		if (!this.isServer() && e instanceof SocketTimeoutException) {
			long now = System.currentTimeMillis();
			try {
				int soTimeout = this.socket.getSoTimeout();
				if (now - this.lastSend < soTimeout && now - this.lastRead < soTimeout * 2) {
					doClose = false;
				}
				if (!doClose && logger.isDebugEnabled()) {
					logger.debug("Skipping a socket timeout because we have a recent send " + this.getConnectionId());
				}
			}
			catch (SocketException e1) {
				logger.error("Error accessing soTimeout", e1);
			}
		}
		if (doClose) {
			boolean noReadErrorOnClose = this.isNoReadErrorOnClose();
			this.closeConnection(true);
			if (!(e instanceof SoftEndOfStreamException)) {
				if (e instanceof SocketTimeoutException && this.isSingleUse()) {
					if (logger.isDebugEnabled()) {
						logger.debug("Closed single use socket after timeout:" + this.getConnectionId());
					}
				}
				else {
					if (noReadErrorOnClose) {
						if (logger.isTraceEnabled()) {
							logger.trace("Read exception " +
									 this.getConnectionId(), e);
						}
						else if (logger.isDebugEnabled()) {
							logger.debug("Read exception " +
									 this.getConnectionId() + " " +
									 e.getClass().getSimpleName() +
								     ":" + (e.getCause() != null ? e.getCause() + ":" : "") + e.getMessage());
						}
					}
					else if (logger.isTraceEnabled()) {
						logger.error("Read exception " +
								 this.getConnectionId(), e);
					}
					else {
						logger.error("Read exception " +
									 this.getConnectionId() + " " +
									 e.getClass().getSimpleName() +
								     ":" + (e.getCause() != null ? e.getCause() + ":" : "") + e.getMessage());
					}
					this.sendExceptionToListener(e);
				}
			}
		}
		return doClose;
	}

}


File: spring-integration-ip/src/main/java/org/springframework/integration/ip/tcp/connection/TcpNioConnection.java
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

package org.springframework.integration.ip.tcp.connection;

import java.io.BufferedOutputStream;
import java.io.IOException;
import java.io.InputStream;
import java.io.OutputStream;
import java.net.SocketTimeoutException;
import java.nio.ByteBuffer;
import java.nio.channels.ClosedChannelException;
import java.nio.channels.SelectionKey;
import java.nio.channels.Selector;
import java.nio.channels.SocketChannel;
import java.util.concurrent.BlockingQueue;
import java.util.concurrent.CountDownLatch;
import java.util.concurrent.Executor;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;
import java.util.concurrent.LinkedBlockingQueue;
import java.util.concurrent.RejectedExecutionException;
import java.util.concurrent.TimeUnit;
import java.util.concurrent.atomic.AtomicInteger;

import javax.net.ssl.SSLSession;

import org.springframework.context.ApplicationEventPublisher;
import org.springframework.core.serializer.Serializer;
import org.springframework.integration.ip.tcp.serializer.SoftEndOfStreamException;
import org.springframework.integration.util.CompositeExecutor;
import org.springframework.messaging.Message;
import org.springframework.messaging.MessagingException;
import org.springframework.util.Assert;

/**
 * A TcpConnection that uses and underlying {@link SocketChannel}.
 *
 * @author Gary Russell
 * @author John Anderson
 * @since 2.0
 *
 */
public class TcpNioConnection extends TcpConnectionSupport {

	private static final long DEFAULT_PIPE_TIMEOUT = 60000;

	private final SocketChannel socketChannel;

	private final ChannelOutputStream channelOutputStream;

	private final ChannelInputStream channelInputStream = new ChannelInputStream();

	private volatile OutputStream bufferedOutputStream;

	private volatile boolean usingDirectBuffers;

	private volatile CompositeExecutor taskExecutor;

	private volatile ByteBuffer rawBuffer;

	private volatile int maxMessageSize = 60 * 1024;

	private volatile long lastRead;

	private volatile long lastSend;

	private final AtomicInteger executionControl = new AtomicInteger();

	private volatile boolean writingToPipe;

	private volatile CountDownLatch writingLatch;

	private volatile long pipeTimeout = DEFAULT_PIPE_TIMEOUT;

	/**
	 * Constructs a TcpNetConnection for the SocketChannel.
	 * @param socketChannel The socketChannel.
	 * @param server If true, this connection was created as
	 * a result of an incoming request.
	 * @param lookupHost true to perform reverse lookups.
	 * @param applicationEventPublisher The event publisher.
	 * @param connectionFactoryName The name of the connection factory creating this connection.
	 * @throws Exception Any Exception.
	 */
	public TcpNioConnection(SocketChannel socketChannel, boolean server, boolean lookupHost,
			ApplicationEventPublisher applicationEventPublisher,
			String connectionFactoryName) throws Exception {
			super(socketChannel.socket(), server, lookupHost, applicationEventPublisher, connectionFactoryName);
		this.socketChannel = socketChannel;
		int receiveBufferSize = socketChannel.socket().getReceiveBufferSize();
		if (receiveBufferSize <= 0) {
			receiveBufferSize = this.maxMessageSize;
		}
		this.channelOutputStream = new ChannelOutputStream();
	}

	public void setPipeTimeout(long pipeTimeout) {
		this.pipeTimeout = pipeTimeout;
	}

	@Override
	public void close() {
		this.setNoReadErrorOnClose(true);
		doClose();
	}

	private void doClose() {
		try {
			channelInputStream.close();
		}
		catch (IOException e) {}
		try {
			this.socketChannel.close();
		}
		catch (Exception e) {}
		super.close();
	}

	@Override
	public boolean isOpen() {
		return this.socketChannel.isOpen();
	}

	@Override
	@SuppressWarnings("unchecked")
	public void send(Message<?> message) throws Exception {
		synchronized(this.socketChannel) {
			if (this.bufferedOutputStream == null) {
				int writeBufferSize = this.socketChannel.socket().getSendBufferSize();
				this.bufferedOutputStream = new BufferedOutputStream(this.getChannelOutputStream(),
						writeBufferSize > 0 ? writeBufferSize : 8192);
			}
			Object object = this.getMapper().fromMessage(message);
			this.lastSend = System.currentTimeMillis();
			try {
				((Serializer<Object>) this.getSerializer()).serialize(object, this.bufferedOutputStream);
				this.bufferedOutputStream.flush();
			}
			catch (Exception e) {
				this.publishConnectionExceptionEvent(new MessagingException(message, e));
				this.closeConnection(true);
				throw e;
			}
			this.afterSend(message);
		}
	}

	@Override
	public Object getPayload() throws Exception {
		return this.getDeserializer().deserialize(this.channelInputStream);
	}

	@Override
	public int getPort() {
		return this.socketChannel.socket().getPort();
	}

	@Override
	public Object getDeserializerStateKey() {
		return this.channelInputStream;
	}

	@Override
	public SSLSession getSslSession() {
		return null;
	}

	/**
	 * Allocates a ByteBuffer of the requested length using normal or
	 * direct buffers, depending on the usingDirectBuffers field.
	 *
	 * @param length The buffer length.
	 * @return The buffer.
	 */
	protected ByteBuffer allocate(int length) {
		ByteBuffer buffer;
		if (this.usingDirectBuffers) {
			buffer = ByteBuffer.allocateDirect(length);
		} else {
			buffer = ByteBuffer.allocate(length);
		}
		return buffer;
	}

	/**
	 * If there is no listener, and this connection is not for single use,
	 * this method exits. When there is a listener, this method assembles
	 * data into messages by invoking convertAndSend whenever there is
	 * data in the input Stream. Method exits when a message is complete
	 * and there is no more data; thus freeing the thread to work on other
	 * sockets.
	 */
	@Override
	public void run() {
		if (logger.isTraceEnabled()) {
			logger.trace(this.getConnectionId() + " Nio message assembler running...");
		}
		boolean moreDataAvailable = true;
		while(moreDataAvailable) {
			try {
				if (this.getListener() == null && !this.isSingleUse()) {
					logger.debug("TcpListener exiting - no listener and not single use");
					return;
				}
				try {
					if (dataAvailable()) {
						Message<?> message = convert();
						if (dataAvailable()) {
							// there is more data in the pipe; run another assembler
							// to assemble the next message, while we send ours
							this.executionControl.incrementAndGet();
							try {
								this.taskExecutor.execute2(this);
							}
							catch (RejectedExecutionException e) {
								this.executionControl.decrementAndGet();
								if (logger.isInfoEnabled()) {
									logger.info(getConnectionId() + " Insufficient threads in the assembler fixed thread pool; consider " +
											"increasing this task executor pool size; data avail: " + this.channelInputStream.available());
								}
							}
						}
						this.executionControl.decrementAndGet();
						if (message != null) {
							sendToChannel(message);
						}
					}
					else {
						this.executionControl.decrementAndGet();
					}
				}
				catch (Exception e) {
					if (logger.isTraceEnabled()) {
						logger.error("Read exception " +
								 this.getConnectionId(), e);
					}
					else if (!this.isNoReadErrorOnClose()) {
						logger.error("Read exception " +
									 this.getConnectionId() + " " +
									 e.getClass().getSimpleName() +
								     ":" + e.getCause() + ":" + e.getMessage());
					}
					else {
						if (logger.isDebugEnabled()) {
							logger.debug("Read exception " +
										 this.getConnectionId() + " " +
										 e.getClass().getSimpleName() +
									     ":" + e.getCause() + ":" + e.getMessage());
						}
					}
					this.closeConnection(true);
					this.sendExceptionToListener(e);
					return;
				}
			}
			finally {
				moreDataAvailable = false;
				// Final check in case new data came in and the
				// timing was such that we were the last assembler and
				// a new one wasn't run
				try {
					if (dataAvailable()) {
						synchronized(this.executionControl) {
							if (this.executionControl.incrementAndGet() <= 1) {
								// only continue if we don't already have another assembler running
								this.executionControl.set(1);
								moreDataAvailable = true;

							}
							else {
								this.executionControl.decrementAndGet();
							}
						}
					}
					if (moreDataAvailable) {
						if (logger.isTraceEnabled()) {
							logger.trace(this.getConnectionId() + " Nio message assembler continuing...");
						}
					}
					else {
						if (logger.isTraceEnabled()) {
							logger.trace(this.getConnectionId() + " Nio message assembler exiting... avail: " + this.channelInputStream.available());
						}
					}
				}
				catch (IOException e) {
					logger.error("Exception when checking for assembler", e);
				}
			}
		}
	}

	private boolean dataAvailable() throws IOException {
		if (logger.isTraceEnabled()) {
			logger.trace(getConnectionId() + " checking data avail: " + this.channelInputStream.available() +
					" pending: " + (this.writingToPipe));
		}
		return writingToPipe || this.channelInputStream.available() > 0;
	}

	/**
	 * Blocks until a complete message has been assembled.
	 * Synchronized to avoid concurrency.
	 * @return The Message or null if no data is available.
	 * @throws IOException
	 */
	private synchronized Message<?> convert() throws Exception {
		if (logger.isTraceEnabled()) {
			logger.trace(getConnectionId() + " checking data avail (convert): " + this.channelInputStream.available() +
					" pending: " + (this.writingToPipe));
		}
		if (this.channelInputStream.available() <= 0) {
			try {
				if (this.writingLatch.await(60, TimeUnit.SECONDS)) {
					if (this.channelInputStream.available() <= 0) {
						return null;
					}
				}
				else { // should never happen
					throw new IOException("Timed out waiting for IO");
				}
			}
			catch (InterruptedException e) {
				Thread.currentThread().interrupt();
				throw new IOException("Interrupted waiting for IO");
			}
		}
		Message<?> message = null;
		try {
			message = this.getMapper().toMessage(this);
		}
		catch (Exception e) {
			this.closeConnection(true);
			if (e instanceof SocketTimeoutException && this.isSingleUse()) {
				if (logger.isDebugEnabled()) {
					logger.debug("Closing single use socket after timeout " + this.getConnectionId());
				}
			} else {
				if (!(e instanceof SoftEndOfStreamException)) {
					throw e;
				}
			}
			return null;
		}
		return message;
	}

	private void sendToChannel(Message<?> message) {
		boolean intercepted = false;
		try {
			if (message != null) {
				intercepted = getListener().onMessage(message);
			}
		}
		catch (Exception e) {
			if (e instanceof NoListenerException) {
				if (this.isSingleUse()) {
					if (logger.isDebugEnabled()) {
						logger.debug("Closing single use channel after inbound message " + this.getConnectionId());
					}
					this.closeConnection(true);
				}
			}
			else {
				logger.error("Exception sending message: " + message, e);
			}
		}
		/*
		 * For single use sockets, we close after receipt if we are on the client
		 * side, and the data was not intercepted,
		 * or the server side has no outbound adapter registered
		 */
		if (this.isSingleUse() && ((!this.isServer() && !intercepted) || (this.isServer() && this.getSender() == null))) {
			if (logger.isDebugEnabled()) {
				logger.debug("Closing single use channel after inbound message " + this.getConnectionId());
			}
			this.closeConnection(false);
		}
	}

	private void doRead() throws Exception {
		if (this.rawBuffer == null) {
			this.rawBuffer = allocate(maxMessageSize);
		}

		this.writingLatch = new CountDownLatch(1);
		this.writingToPipe = true;
		try {
			if (this.taskExecutor == null) {
				ExecutorService executor = Executors.newCachedThreadPool();
				this.taskExecutor = new CompositeExecutor(executor, executor);
			}
			// If there is no assembler running, start one
			checkForAssembler();

			if (logger.isTraceEnabled()) {
				logger.trace("Before read:" + this.rawBuffer.position() + "/" + this.rawBuffer.limit());
			}
			int len = this.socketChannel.read(this.rawBuffer);
			if (len < 0) {
				this.writingToPipe = false;
				this.closeConnection(true);
			}
			if (logger.isTraceEnabled()) {
				logger.trace("After read:" + this.rawBuffer.position() + "/" + this.rawBuffer.limit());
			}
			this.rawBuffer.flip();
			if (logger.isTraceEnabled()) {
				logger.trace("After flip:" + this.rawBuffer.position() + "/" + this.rawBuffer.limit());
			}
			if (logger.isDebugEnabled()) {
				logger.debug("Read " + rawBuffer.limit() + " into raw buffer");
			}
			this.sendToPipe(rawBuffer);
		}
		catch (RejectedExecutionException e) {
			throw e;
		}
		catch (Exception e) {
			this.publishConnectionExceptionEvent(e);
			throw e;
		}
		finally {
			this.writingToPipe = false;
			this.writingLatch.countDown();
		}
	}

	protected void sendToPipe(ByteBuffer rawBuffer) throws IOException {
		Assert.notNull(rawBuffer, "rawBuffer cannot be null");
		if (logger.isTraceEnabled()) {
			logger.trace(this.getConnectionId() + " Sending " + rawBuffer.limit() + " to pipe");
		}
		this.channelInputStream.write(rawBuffer.array(), rawBuffer.limit());
		rawBuffer.clear();
	}

	private void checkForAssembler() {
		synchronized(this.executionControl) {
			if (this.executionControl.incrementAndGet() <= 1) {
				// only execute run() if we don't already have one running
				this.executionControl.set(1);
				if (logger.isDebugEnabled()) {
					logger.debug(this.getConnectionId() + " Running an assembler");
				}
				try {
					this.taskExecutor.execute2(this);
				}
				catch (RejectedExecutionException e) {
					this.executionControl.decrementAndGet();
					if (logger.isInfoEnabled()) {
						logger.info("Insufficient threads in the assembler fixed thread pool; consider increasing " +
								"this task executor pool size");
					}
					throw e;
				}
			}
			else {
				this.executionControl.decrementAndGet();
			}
		}
	}

	/**
	 * Invoked by the factory when there is data to be read.
	 */
	public void readPacket() {
		if (logger.isDebugEnabled()) {
			logger.debug(this.getConnectionId() + " Reading...");
		}
		try {
			doRead();
		}
		catch (ClosedChannelException cce) {
			if (logger.isDebugEnabled()) {
				logger.debug(this.getConnectionId() + " Channel is closed");
			}
			this.closeConnection(true);
		}
		catch (RejectedExecutionException e) {
			throw e;
		}
		catch (Exception e) {
			logger.error("Exception on Read " +
					     this.getConnectionId() + " " +
					     e.getMessage(), e);
			this.closeConnection(true);
		}
	}

	/**
	 * Close the socket due to timeout.
	 */
	void timeout() {
		this.closeConnection(true);
	}

	/**
	 *
	 * @param taskExecutor the taskExecutor to set
	 */
	public void setTaskExecutor(Executor taskExecutor) {
		if (taskExecutor instanceof CompositeExecutor) {
			this.taskExecutor = (CompositeExecutor) taskExecutor;
		}
		else {
			this.taskExecutor = new CompositeExecutor(taskExecutor, taskExecutor);
		}
	}

	/**
	 * If true, connection will attempt to use direct buffers where
	 * possible.
	 * @param usingDirectBuffers the usingDirectBuffers to set.
	 */
	public void setUsingDirectBuffers(boolean usingDirectBuffers) {
		this.usingDirectBuffers = usingDirectBuffers;
	}

	protected boolean isUsingDirectBuffers() {
		return usingDirectBuffers;
	}

	protected ChannelOutputStream getChannelOutputStream() {
		return channelOutputStream;
	}

	/**
	 *
	 * @return Time of last read.
	 */
	public long getLastRead() {
		return lastRead;
	}

	/**
	 *
	 * @param lastRead The time of the last read.
	 */
	public void setLastRead(long lastRead) {
		this.lastRead = lastRead;
	}

	/**
	 * @return the time of the last send
	 */
	public long getLastSend() {
		return lastSend;
	}

	/**
	 * OutputStream to wrap a SocketChannel; implements timeout on write.
	 *
	 */
	class ChannelOutputStream extends OutputStream {

		private Selector selector;

		private int soTimeout;

		@Override
		public void write(int b) throws IOException {
			byte[] bytes = new byte[1];
			bytes[0] = (byte) b;
			ByteBuffer buffer = ByteBuffer.wrap(bytes);
			doWrite(buffer);
		}

		@Override
		public void close() throws IOException {
			doClose();
		}

		@Override
		public void flush() throws IOException {
		}

		@Override
		public void write(byte[] b, int off, int len) throws IOException {
			ByteBuffer buffer = ByteBuffer.wrap(b, off, len);
			doWrite(buffer);
		}

		@Override
		public void write(byte[] b) throws IOException {
			ByteBuffer buffer = ByteBuffer.wrap(b);
			doWrite(buffer);
		}

		protected synchronized void doWrite(ByteBuffer buffer) throws IOException {
			if (logger.isDebugEnabled()) {
				logger.debug(getConnectionId() + " writing " + buffer.remaining());
			}
			socketChannel.write(buffer);
			int remaining = buffer.remaining();
			if (remaining == 0) {
				return;
			}
			if (this.selector == null) {
				this.selector = Selector.open();
				this.soTimeout = socketChannel.socket().getSoTimeout();
			}
			socketChannel.register(selector, SelectionKey.OP_WRITE);
			while (remaining > 0) {
				int selectionCount = this.selector.select(this.soTimeout);
				if (selectionCount == 0) {
					throw new SocketTimeoutException("Timeout on write");
				}
				selector.selectedKeys().clear();
				socketChannel.write(buffer);
				remaining = buffer.remaining();
			}
		}

	}

	/**
	 * Provides an InputStream to receive data from {@link SocketChannel#read(ByteBuffer)}
	 * operations. Each new buffer is added to a BlockingQueue; when the reading thread
	 * exhausts the current buffer, it retrieves the next from the queue.
	 * Writes block for up to the pipeTimeout if 5 buffers are queued to be read.
	 *
	 */
	class ChannelInputStream extends InputStream {

		private static final int BUFFER_LIMIT = 5;

		private final BlockingQueue<byte[]> buffers = new LinkedBlockingQueue<byte[]>(BUFFER_LIMIT);

		private volatile byte[] currentBuffer;

		private volatile int currentOffset;

		private final AtomicInteger available = new AtomicInteger();

		private volatile boolean isClosed;

		@Override
		public int read(byte[] b, int off, int len) throws IOException {
			Assert.notNull(b, "byte[] cannot be null");
			if (off < 0 || len < 0 || len > b.length - off) {
			    throw new IndexOutOfBoundsException();
			}
			else if (len == 0) {
			    return 0;
			}

			int n = 0;
			while ((this.available.get() > 0 || n == 0) &&
						n < len) {
				int bite = read();
				if (bite < 0) {
					if (n == 0) {
						return -1;
					}
					else {
						return n;
					}
				}
				b[off + n++] = (byte) bite;
			}
			return n;
		}

		@Override
		public synchronized int read() throws IOException {
			if (this.isClosed && available.get() == 0) {
				return -1;
			}
			if (this.currentBuffer == null) {
				this.currentBuffer = getNextBuffer();
				this.currentOffset = 0;
				if (this.currentBuffer == null) {
					return -1;
				}
			}
			int bite;
			bite = this.currentBuffer[this.currentOffset++] & 0xff;
			this.available.decrementAndGet();
			if (this.currentOffset >= this.currentBuffer.length) {
				this.currentBuffer = null;
			}
			return bite;
		}

		private byte[] getNextBuffer() throws IOException {
			byte[] buffer = null;
			while (buffer == null) {
				try {
					buffer = buffers.poll(1, TimeUnit.SECONDS);
					if (buffer == null && this.isClosed) {
						return null;
					}
				}
				catch (InterruptedException e) {
					Thread.currentThread().interrupt();
					throw new IOException("Interrupted while waiting for data", e);
				}
			}
			return buffer;
		}

		/**
		 * Blocks if the blocking queue already contains 5 buffers.
		 * @param array
		 * @param bytesToWrite
		 * @throws IOException
		 */
		public void write(byte[] array, int bytesToWrite) throws IOException {
			if (bytesToWrite > 0) {
				byte[] buffer = new byte[bytesToWrite];
				System.arraycopy(array, 0, buffer, 0, bytesToWrite);
				this.available.addAndGet(bytesToWrite);
				if (TcpNioConnection.this.writingLatch != null) {
					TcpNioConnection.this.writingLatch.countDown();
				}
				try {
					if (!this.buffers.offer(buffer, pipeTimeout, TimeUnit.MILLISECONDS)) {
						throw new IOException("Timed out waiting for buffer space");
					}
				}
				catch (InterruptedException e) {
					Thread.currentThread().interrupt();
					throw new IOException("Interrupted while waiting for buffer space", e);
				}
				TcpNioConnection.this.writingLatch = new CountDownLatch(1);
			}
		}

		@Override
		public void close() throws IOException {
			super.close();
			this.isClosed = true;
		}

		@Override
		public int available() throws IOException {
			return this.available.get();
		}

	}
}


File: spring-integration-ip/src/test/java/org/springframework/integration/ip/config/ParserUnitTests.java
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

package org.springframework.integration.ip.config;

import static org.junit.Assert.assertEquals;
import static org.junit.Assert.assertFalse;
import static org.junit.Assert.assertNotNull;
import static org.junit.Assert.assertNotSame;
import static org.junit.Assert.assertNull;
import static org.junit.Assert.assertSame;
import static org.junit.Assert.assertTrue;
import static org.mockito.Mockito.mock;

import java.util.Iterator;
import java.util.Set;

import org.junit.Test;
import org.junit.runner.RunWith;

import org.springframework.beans.DirectFieldAccessor;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.beans.factory.annotation.Qualifier;
import org.springframework.context.ApplicationContext;
import org.springframework.core.io.ClassPathResource;
import org.springframework.core.io.UrlResource;
import org.springframework.core.serializer.Deserializer;
import org.springframework.core.serializer.Serializer;
import org.springframework.core.task.TaskExecutor;
import org.springframework.integration.channel.DirectChannel;
import org.springframework.integration.channel.QueueChannel;
import org.springframework.integration.core.MessagingTemplate;
import org.springframework.integration.endpoint.AbstractEndpoint;
import org.springframework.integration.endpoint.EventDrivenConsumer;
import org.springframework.integration.handler.advice.AbstractRequestHandlerAdvice;
import org.springframework.integration.ip.tcp.TcpInboundGateway;
import org.springframework.integration.ip.tcp.TcpOutboundGateway;
import org.springframework.integration.ip.tcp.TcpReceivingChannelAdapter;
import org.springframework.integration.ip.tcp.TcpSendingMessageHandler;
import org.springframework.integration.ip.tcp.connection.AbstractConnectionFactory;
import org.springframework.integration.ip.tcp.connection.DefaultTcpNetSSLSocketFactorySupport;
import org.springframework.integration.ip.tcp.connection.DefaultTcpNioSSLConnectionSupport;
import org.springframework.integration.ip.tcp.connection.DefaultTcpSSLContextSupport;
import org.springframework.integration.ip.tcp.connection.TcpConnectionEvent;
import org.springframework.integration.ip.tcp.connection.TcpConnectionEventListeningMessageProducer;
import org.springframework.integration.ip.tcp.connection.TcpConnectionOpenEvent;
import org.springframework.integration.ip.tcp.connection.TcpConnectionSupport;
import org.springframework.integration.ip.tcp.connection.TcpMessageMapper;
import org.springframework.integration.ip.tcp.connection.TcpNetClientConnectionFactory;
import org.springframework.integration.ip.tcp.connection.TcpNetServerConnectionFactory;
import org.springframework.integration.ip.tcp.connection.TcpNioClientConnectionFactory;
import org.springframework.integration.ip.tcp.connection.TcpNioServerConnectionFactory;
import org.springframework.integration.ip.tcp.connection.TcpSSLContextSupport;
import org.springframework.integration.ip.tcp.connection.TcpSocketFactorySupport;
import org.springframework.integration.ip.tcp.connection.TcpSocketSupport;
import org.springframework.integration.ip.udp.DatagramPacketMessageMapper;
import org.springframework.integration.ip.udp.MulticastReceivingChannelAdapter;
import org.springframework.integration.ip.udp.MulticastSendingMessageHandler;
import org.springframework.integration.ip.udp.UnicastReceivingChannelAdapter;
import org.springframework.integration.ip.udp.UnicastSendingMessageHandler;
import org.springframework.integration.support.MessageBuilderFactory;
import org.springframework.integration.test.util.TestUtils;
import org.springframework.messaging.Message;
import org.springframework.messaging.MessageChannel;
import org.springframework.messaging.MessageHandler;
import org.springframework.messaging.support.GenericMessage;
import org.springframework.scheduling.TaskScheduler;
import org.springframework.test.context.ContextConfiguration;
import org.springframework.test.context.junit4.SpringJUnit4ClassRunner;

/**
 * @author Gary Russell
 * @author Oleg Zhurakousky
 * @since 2.0
 */
@ContextConfiguration
@RunWith(SpringJUnit4ClassRunner.class)
public class ParserUnitTests {

	@Autowired
	ApplicationContext ctx;

	@Autowired
	@Qualifier(value="testInUdp")
	UnicastReceivingChannelAdapter udpIn;

	@Autowired
	@Qualifier(value="testInUdpMulticast")
	MulticastReceivingChannelAdapter udpInMulticast;

	@Autowired
	@Qualifier(value="testInTcp")
	TcpReceivingChannelAdapter tcpIn;

	@Autowired
	@Qualifier(value="testOutUdp.handler")
	UnicastSendingMessageHandler udpOut;

	@Autowired
	@Qualifier(value="testOutUdpiMulticast.handler")
	MulticastSendingMessageHandler udpOutMulticast;

	@Autowired
	@Qualifier(value="testOutTcpNio")
	AbstractEndpoint tcpOutEndpoint;

	@Autowired
	@Qualifier(value="testOutTcpNio.handler")
	TcpSendingMessageHandler tcpOut;

	@Autowired
	EventDrivenConsumer testOutTcpNio;

	@Autowired
	@Qualifier(value="inGateway1")
	TcpInboundGateway tcpInboundGateway1;

	@Autowired
	@Qualifier(value="inGateway2")
	TcpInboundGateway tcpInboundGateway2;

	@Autowired
	@Qualifier(value="outGateway.handler")
	TcpOutboundGateway tcpOutboundGateway;

	@Autowired
	@Qualifier(value="outAdviceGateway.handler")
	TcpOutboundGateway outAdviceGateway;

	// verify we can still inject by generated name
	@Autowired
	@Qualifier(value="org.springframework.integration.ip.tcp.TcpOutboundGateway#0")
	TcpOutboundGateway tcpOutboundGatewayByGeneratedName;

	@Autowired
	EventDrivenConsumer outGateway;

	@Autowired
	@Qualifier(value="externalTE")
	TaskExecutor taskExecutor;

	@Autowired
	AbstractConnectionFactory client1;

	@Autowired
	AbstractConnectionFactory client2;

	@Autowired
	AbstractConnectionFactory cfC1;

	@Autowired
	AbstractConnectionFactory cfC2;

	@Autowired
	AbstractConnectionFactory cfC3;

	@Autowired
	AbstractConnectionFactory cfC4;

	@Autowired
	AbstractConnectionFactory cfC5;

	@Autowired
	Serializer<?> serializer;

	@Autowired
	Deserializer<?> deserializer;

	@Autowired
	AbstractConnectionFactory server1;

	@Autowired
	AbstractConnectionFactory server2;

	@Autowired
	AbstractConnectionFactory cfS1;

	@Autowired
	AbstractConnectionFactory cfS1Nio;

	@Autowired
	AbstractConnectionFactory cfS2;

	@Autowired
	AbstractConnectionFactory cfS3;

	@Autowired
	@Qualifier(value="tcpNewOut1.handler")
	TcpSendingMessageHandler tcpNewOut1;

	@Autowired
	@Qualifier(value="tcpNewOut2.handler")
	TcpSendingMessageHandler tcpNewOut2;

	@Autowired
	TcpReceivingChannelAdapter tcpNewIn1;

	@Autowired
	TcpReceivingChannelAdapter tcpNewIn2;

	@Autowired
	private MessageChannel errorChannel;

	@Autowired
	private DirectChannel udpChannel;

	@Autowired
	private DirectChannel udpAdviceChannel;

	@Autowired
	private DirectChannel tcpAdviceChannel;

	@Autowired
	private DirectChannel tcpAdviceGateChannel;

	@Autowired
	private DirectChannel tcpChannel;

	@Autowired
	TcpReceivingChannelAdapter tcpInClientMode;

	@Autowired
	TcpInboundGateway inGatewayClientMode;

	@Autowired
	TaskScheduler sched;

	@Autowired
	@Qualifier(value="tcpOutClientMode.handler")
	TcpSendingMessageHandler tcpOutClientMode;

	@Autowired
	MessageChannel tcpAutoChannel;

	@Autowired
	MessageChannel udpAutoChannel;

	@Autowired @Qualifier("tcpAutoChannel.adapter")
	TcpReceivingChannelAdapter tcpAutoAdapter;

	@Autowired @Qualifier("udpAutoChannel.adapter")
	UnicastReceivingChannelAdapter udpAutoAdapter;

	@Autowired
	TcpNetServerConnectionFactory secureServer;

	@Autowired
	TcpSocketFactorySupport socketFactorySupport;

	@Autowired
	TcpSocketSupport socketSupport;

	@Autowired
	TcpSSLContextSupport contextSupport;

	@Autowired
	TcpMessageMapper mapper;

	@Autowired
	TcpConnectionEventListeningMessageProducer eventAdapter;

	@Autowired
	QueueChannel eventChannel;

	private static volatile int adviceCalled;

	@Test
	public void testInUdp() {
		DirectFieldAccessor dfa = new DirectFieldAccessor(udpIn);
		assertTrue(udpIn.getPort() >= 5000);
		assertEquals(27, dfa.getPropertyValue("poolSize"));
		assertEquals(29, dfa.getPropertyValue("receiveBufferSize"));
		assertEquals(30, dfa.getPropertyValue("soReceiveBufferSize"));
		assertEquals(31, dfa.getPropertyValue("soSendBufferSize"));
		assertEquals(32, dfa.getPropertyValue("soTimeout"));
		assertEquals("testInUdp",udpIn.getComponentName());
		assertEquals("ip:udp-inbound-channel-adapter", udpIn.getComponentType());
		assertEquals("127.0.0.1", dfa.getPropertyValue("localAddress"));
		assertSame(taskExecutor, dfa.getPropertyValue("taskExecutor"));
		assertEquals(errorChannel, dfa.getPropertyValue("errorChannel"));
		DatagramPacketMessageMapper mapper = (DatagramPacketMessageMapper) dfa.getPropertyValue("mapper");
		DirectFieldAccessor mapperAccessor = new DirectFieldAccessor(mapper);
		assertFalse((Boolean)mapperAccessor.getPropertyValue("lookupHost"));
		assertFalse(TestUtils.getPropertyValue(udpIn, "autoStartup", Boolean.class));
		assertEquals(1234, dfa.getPropertyValue("phase"));
	}

	@Test
	public void testInUdpMulticast() {
		DirectFieldAccessor dfa = new DirectFieldAccessor(udpInMulticast);
		assertTrue(udpInMulticast.getPort() >= 5100);
		assertEquals("225.6.7.8", dfa.getPropertyValue("group"));
		assertEquals(27, dfa.getPropertyValue("poolSize"));
		assertEquals(29, dfa.getPropertyValue("receiveBufferSize"));
		assertEquals(30, dfa.getPropertyValue("soReceiveBufferSize"));
		assertEquals(31, dfa.getPropertyValue("soSendBufferSize"));
		assertEquals(32, dfa.getPropertyValue("soTimeout"));
		assertEquals("127.0.0.1", dfa.getPropertyValue("localAddress"));
		assertNotSame(taskExecutor, dfa.getPropertyValue("taskExecutor"));
		assertNull(dfa.getPropertyValue("errorChannel"));
		DatagramPacketMessageMapper mapper = (DatagramPacketMessageMapper) dfa.getPropertyValue("mapper");
		DirectFieldAccessor mapperAccessor = new DirectFieldAccessor(mapper);
		assertTrue((Boolean)mapperAccessor.getPropertyValue("lookupHost"));
	}

	@Test
	public void testInTcp() {
		DirectFieldAccessor dfa = new DirectFieldAccessor(tcpIn);
		assertSame(cfS1, dfa.getPropertyValue("serverConnectionFactory"));
		assertEquals("testInTcp",tcpIn.getComponentName());
		assertEquals("ip:tcp-inbound-channel-adapter", tcpIn.getComponentType());
		assertEquals(errorChannel, dfa.getPropertyValue("errorChannel"));
		assertFalse(cfS1.isLookupHost());
		assertFalse(tcpIn.isAutoStartup());
		assertEquals(124, tcpIn.getPhase());
		TcpMessageMapper cfS1Mapper = TestUtils.getPropertyValue(cfS1, "mapper", TcpMessageMapper.class);
		assertSame(mapper, cfS1Mapper);
		assertTrue((Boolean) TestUtils.getPropertyValue(cfS1Mapper, "applySequence"));
		Object socketSupport = TestUtils.getPropertyValue(cfS1, "tcpSocketFactorySupport");
		assertTrue(socketSupport instanceof DefaultTcpNetSSLSocketFactorySupport);
		assertNotNull(TestUtils.getPropertyValue(socketSupport, "sslContext"));

		TcpSSLContextSupport contextSupport = TestUtils.getPropertyValue(cfS1, "tcpSocketFactorySupport.sslContextSupport", TcpSSLContextSupport.class);
		assertSame(contextSupport, this.contextSupport);
		assertTrue(TestUtils.getPropertyValue(contextSupport, "keyStore") instanceof ClassPathResource);
		assertTrue(TestUtils.getPropertyValue(contextSupport, "trustStore") instanceof ClassPathResource);

		contextSupport = new DefaultTcpSSLContextSupport("http:foo", "file:bar", "", "");
		assertTrue(TestUtils.getPropertyValue(contextSupport, "keyStore") instanceof UrlResource);
		assertTrue(TestUtils.getPropertyValue(contextSupport, "trustStore") instanceof UrlResource);
	}

	@Test
	public void testInTcpNioSSLDefaultConfig() {
		assertFalse(cfS1Nio.isLookupHost());
		assertTrue((Boolean) TestUtils.getPropertyValue(cfS1Nio, "mapper.applySequence"));
		Object connectionSupport = TestUtils.getPropertyValue(cfS1Nio, "tcpNioConnectionSupport");
		assertTrue(connectionSupport instanceof DefaultTcpNioSSLConnectionSupport);
		assertNotNull(TestUtils.getPropertyValue(connectionSupport, "sslContext"));
	}

	@Test
	public void testOutUdp() {
		DirectFieldAccessor dfa = new DirectFieldAccessor(udpOut);
		assertTrue(udpOut.getPort() >= 5400);
		assertEquals("localhost", dfa.getPropertyValue("host"));
		int ackPort = (Integer) dfa.getPropertyValue("ackPort");
		assertTrue("Expected ackPort >= 5300 was:" + ackPort, ackPort >= 5300);
		DatagramPacketMessageMapper mapper = (DatagramPacketMessageMapper) dfa
				.getPropertyValue("mapper");
		String ackAddress = (String) new DirectFieldAccessor(mapper)
				.getPropertyValue("ackAddress");
		assertEquals("somehost:" + ackPort, ackAddress);
		assertEquals(51, dfa.getPropertyValue("ackTimeout"));
		assertEquals(true, dfa.getPropertyValue("waitForAck"));
		assertEquals(52, dfa.getPropertyValue("soReceiveBufferSize"));
		assertEquals(53, dfa.getPropertyValue("soSendBufferSize"));
		assertEquals(54, dfa.getPropertyValue("soTimeout"));
		assertEquals("127.0.0.1", dfa.getPropertyValue("localAddress"));
		assertSame(taskExecutor, dfa.getPropertyValue("taskExecutor"));
		assertEquals(23, dfa.getPropertyValue("order"));
		assertEquals("testOutUdp",udpOut.getComponentName());
		assertEquals("ip:udp-outbound-channel-adapter", udpOut.getComponentType());
	}

	@Test
	public void testOutUdpMulticast() {
		DirectFieldAccessor dfa = new DirectFieldAccessor(udpOutMulticast);
		assertTrue(udpOutMulticast.getPort() >= 5600);
		assertEquals("225.6.7.8", dfa.getPropertyValue("host"));
		int ackPort = (Integer) dfa.getPropertyValue("ackPort");
		assertTrue("Expected ackPort >= 5500 was:" + ackPort, ackPort >= 5500);
		DatagramPacketMessageMapper mapper = (DatagramPacketMessageMapper) dfa
				.getPropertyValue("mapper");
		String ackAddress = (String) new DirectFieldAccessor(mapper)
				.getPropertyValue("ackAddress");
		assertEquals("somehost:" + ackPort, ackAddress);
		assertEquals(51, dfa.getPropertyValue("ackTimeout"));
		assertEquals(true, dfa.getPropertyValue("waitForAck"));
		assertEquals(52, dfa.getPropertyValue("soReceiveBufferSize"));
		assertEquals(53, dfa.getPropertyValue("soSendBufferSize"));
		assertEquals(54, dfa.getPropertyValue("soTimeout"));
		assertEquals(55, dfa.getPropertyValue("timeToLive"));
		assertEquals(12, dfa.getPropertyValue("order"));
	}

	@Test
	public void testUdpOrder() {
		@SuppressWarnings("unchecked")
		Set<MessageHandler> handlers = (Set<MessageHandler>) TestUtils
				.getPropertyValue(
						TestUtils.getPropertyValue(this.udpChannel, "dispatcher"),
						"handlers");
		Iterator<MessageHandler> iterator = handlers.iterator();
		assertSame(this.udpOutMulticast, iterator.next());
		assertSame(this.udpOut, iterator.next());
	}

	@Test
	public void udpAdvice() {
		adviceCalled = 0;
		this.udpAdviceChannel.send(new GenericMessage<String>("foo"));
		assertEquals(1, adviceCalled);
	}

	@Test
	public void tcpAdvice() {
		adviceCalled = 0;
		this.tcpAdviceChannel.send(new GenericMessage<String>("foo"));
		assertEquals(1, adviceCalled);
	}

	@Test
	public void tcpGatewayAdvice() {
		adviceCalled = 0;
		this.tcpAdviceGateChannel.send(new GenericMessage<String>("foo"));
		assertEquals(1, adviceCalled);
	}

	@Test
	public void testOutTcp() {
		DirectFieldAccessor dfa = new DirectFieldAccessor(tcpOut);
		assertSame(cfC1, dfa.getPropertyValue("clientConnectionFactory"));
		assertEquals("testOutTcpNio",tcpOut.getComponentName());
		assertEquals("ip:tcp-outbound-channel-adapter", tcpOut.getComponentType());
		assertFalse(cfC1.isLookupHost());
		assertEquals(35, dfa.getPropertyValue("order"));
		assertFalse(tcpOutEndpoint.isAutoStartup());
		assertEquals(125, tcpOutEndpoint.getPhase());
		assertFalse((Boolean) TestUtils.getPropertyValue(
				TestUtils.getPropertyValue(cfC1, "mapper"), "applySequence"));
		assertEquals(10000L, TestUtils.getPropertyValue(cfC1, "readDelay"));
	}

	@Test
	public void testInGateway1() {
		DirectFieldAccessor dfa = new DirectFieldAccessor(tcpInboundGateway1);
		assertSame(cfS2, dfa.getPropertyValue("serverConnectionFactory"));
		assertEquals(456L, dfa.getPropertyValue("replyTimeout"));
		assertEquals("inGateway1",tcpInboundGateway1.getComponentName());
		assertEquals("ip:tcp-inbound-gateway", tcpInboundGateway1.getComponentType());
		assertEquals(errorChannel, dfa.getPropertyValue("errorChannel"));
		assertTrue(cfS2.isLookupHost());
		assertFalse(tcpInboundGateway1.isAutoStartup());
		assertEquals(126, tcpInboundGateway1.getPhase());
		assertFalse((Boolean) TestUtils.getPropertyValue(
				TestUtils.getPropertyValue(cfS2, "mapper"), "applySequence"));
		assertEquals(100L, TestUtils.getPropertyValue(cfS2, "readDelay"));
	}

	@Test
	public void testInGateway2() {
		DirectFieldAccessor dfa = new DirectFieldAccessor(tcpInboundGateway2);
		assertSame(cfS3, dfa.getPropertyValue("serverConnectionFactory"));
		assertEquals(456L, dfa.getPropertyValue("replyTimeout"));
		assertEquals("inGateway2",tcpInboundGateway2.getComponentName());
		assertEquals("ip:tcp-inbound-gateway", tcpInboundGateway2.getComponentType());
		assertNull(dfa.getPropertyValue("errorChannel"));
		assertEquals(Boolean.FALSE, dfa.getPropertyValue("isClientMode"));
		assertNull(dfa.getPropertyValue("taskScheduler"));
		assertEquals(60000L, dfa.getPropertyValue("retryInterval"));
	}

	@Test
	public void testOutGateway() {
		DirectFieldAccessor dfa = new DirectFieldAccessor(tcpOutboundGateway);
		assertSame(cfC2, dfa.getPropertyValue("connectionFactory"));
		assertEquals(234L, dfa.getPropertyValue("requestTimeout"));
		MessagingTemplate messagingTemplate = TestUtils.getPropertyValue(tcpOutboundGateway, "messagingTemplate",
				MessagingTemplate.class);
		assertEquals(Long.valueOf(567), TestUtils.getPropertyValue(messagingTemplate, "sendTimeout", Long.class));
		assertEquals("789", TestUtils.getPropertyValue(tcpOutboundGateway, "remoteTimeoutExpression.literalValue"));
		assertEquals("outGateway",tcpOutboundGateway.getComponentName());
		assertEquals("ip:tcp-outbound-gateway", tcpOutboundGateway.getComponentType());
		assertTrue(cfC2.isLookupHost());
		assertEquals(24, dfa.getPropertyValue("order"));

		assertEquals("4000", TestUtils.getPropertyValue(outAdviceGateway, "remoteTimeoutExpression.expression"));
	}

	@Test
	public void testConnClient1() {
		assertTrue(client1 instanceof TcpNioClientConnectionFactory);
		assertEquals("localhost", client1.getHost());
		assertTrue(client1.getPort() >= 6000);
		assertEquals(54, client1.getSoLinger());
		assertEquals(1234, client1.getSoReceiveBufferSize());
		assertEquals(1235, client1.getSoSendBufferSize());
		assertEquals(1236, client1.getSoTimeout());
		assertEquals(12, client1.getSoTrafficClass());
		DirectFieldAccessor dfa = new DirectFieldAccessor(client1);
		assertSame(serializer, dfa.getPropertyValue("serializer"));
		assertSame(deserializer, dfa.getPropertyValue("deserializer"));
		assertEquals(true, dfa.getPropertyValue("soTcpNoDelay"));
		assertEquals(true, dfa.getPropertyValue("singleUse"));
		assertSame(taskExecutor, dfa.getPropertyValue("taskExecutor"));
		assertEquals(true, dfa.getPropertyValue("usingDirectBuffers"));
		assertNotNull(dfa.getPropertyValue("interceptorFactoryChain"));
	}

	@Test
	public void testConnServer1() {
		assertTrue(server1 instanceof TcpNioServerConnectionFactory);
		assertEquals(client1.getPort(), server1.getPort());
		assertEquals(55, server1.getSoLinger());
		assertEquals(1234, server1.getSoReceiveBufferSize());
		assertEquals(1235, server1.getSoSendBufferSize());
		assertEquals(1236, server1.getSoTimeout());
		assertEquals(12, server1.getSoTrafficClass());
		DirectFieldAccessor dfa = new DirectFieldAccessor(server1);
		assertSame(serializer, dfa.getPropertyValue("serializer"));
		assertSame(deserializer, dfa.getPropertyValue("deserializer"));
		assertEquals(true, dfa.getPropertyValue("soTcpNoDelay"));
		assertEquals(true, dfa.getPropertyValue("singleUse"));
		assertSame(taskExecutor, dfa.getPropertyValue("taskExecutor"));
		assertEquals(123, dfa.getPropertyValue("backlog"));
		assertEquals(true, dfa.getPropertyValue("usingDirectBuffers"));
		assertNotNull(dfa.getPropertyValue("interceptorFactoryChain"));
	}

	@Test
	public void testConnClient2() {
		assertTrue(client2 instanceof TcpNetClientConnectionFactory);
		assertEquals("localhost", client1.getHost());
		assertTrue(client1.getPort() >= 6000);
		assertEquals(54, client1.getSoLinger());
		assertEquals(1234, client1.getSoReceiveBufferSize());
		assertEquals(1235, client1.getSoSendBufferSize());
		assertEquals(1236, client1.getSoTimeout());
		assertEquals(12, client1.getSoTrafficClass());
		DirectFieldAccessor dfa = new DirectFieldAccessor(client1);
		assertSame(serializer, dfa.getPropertyValue("serializer"));
		assertSame(deserializer, dfa.getPropertyValue("deserializer"));
		assertEquals(true, dfa.getPropertyValue("soTcpNoDelay"));
		assertEquals(true, dfa.getPropertyValue("singleUse"));
		assertSame(taskExecutor, dfa.getPropertyValue("taskExecutor"));
		assertNotNull(dfa.getPropertyValue("interceptorFactoryChain"));
	}

	@Test
	public void testConnServer2() {
		assertTrue(server2 instanceof TcpNetServerConnectionFactory);
		assertEquals(client1.getPort(), server1.getPort());
		assertEquals(55, server1.getSoLinger());
		assertEquals(1234, server1.getSoReceiveBufferSize());
		assertEquals(1235, server1.getSoSendBufferSize());
		assertEquals(1236, server1.getSoTimeout());
		assertEquals(12, server1.getSoTrafficClass());
		DirectFieldAccessor dfa = new DirectFieldAccessor(server1);
		assertSame(serializer, dfa.getPropertyValue("serializer"));
		assertSame(deserializer, dfa.getPropertyValue("deserializer"));
		assertEquals(true, dfa.getPropertyValue("soTcpNoDelay"));
		assertEquals(true, dfa.getPropertyValue("singleUse"));
		assertSame(taskExecutor, dfa.getPropertyValue("taskExecutor"));
		assertEquals(123, dfa.getPropertyValue("backlog"));
		assertNotNull(dfa.getPropertyValue("interceptorFactoryChain"));
	}

	@Test
	public void testNewOut1() {
		DirectFieldAccessor dfa = new DirectFieldAccessor(tcpNewOut1);
		assertSame(client1, dfa.getPropertyValue("clientConnectionFactory"));
		assertEquals(25, dfa.getPropertyValue("order"));
		assertEquals(Boolean.FALSE, dfa.getPropertyValue("isClientMode"));
		assertNull(dfa.getPropertyValue("taskScheduler"));
		assertEquals(60000L, dfa.getPropertyValue("retryInterval"));
	}

	@Test
	public void testNewOut2() {
		DirectFieldAccessor dfa = new DirectFieldAccessor(tcpNewOut2);
		assertSame(server1, dfa.getPropertyValue("serverConnectionFactory"));
		assertEquals(15, dfa.getPropertyValue("order"));
	}

	@Test
	public void testNewIn1() {
		DirectFieldAccessor dfa = new DirectFieldAccessor(tcpNewIn1);
		assertSame(client1, dfa.getPropertyValue("clientConnectionFactory"));
		assertNull(dfa.getPropertyValue("errorChannel"));
		assertEquals(Boolean.FALSE, dfa.getPropertyValue("isClientMode"));
		assertNull(dfa.getPropertyValue("taskScheduler"));
		assertEquals(60000L, dfa.getPropertyValue("retryInterval"));
	}

	@Test
	public void testNewIn2() {
		DirectFieldAccessor dfa = new DirectFieldAccessor(tcpNewIn2);
		assertSame(server1, dfa.getPropertyValue("serverConnectionFactory"));
	}

	@Test
	public void testtCPOrder() {
		this.outGateway.start();
		this.testOutTcpNio.start();
		@SuppressWarnings("unchecked")
		Set<MessageHandler> handlers = (Set<MessageHandler>) TestUtils
				.getPropertyValue(
						TestUtils.getPropertyValue(this.tcpChannel, "dispatcher"),
						"handlers");
		Iterator<MessageHandler> iterator = handlers.iterator();
		assertSame(this.tcpNewOut2, iterator.next());			//15
		assertSame(this.tcpOutboundGateway, iterator.next());	//24
		assertSame(this.tcpNewOut1, iterator.next());			//25
		assertSame(this.tcpOut, iterator.next());				//35
	}

	@Test
	public void testInClientMode() {
		DirectFieldAccessor dfa = new DirectFieldAccessor(tcpInClientMode);
		assertSame(cfC3, dfa.getPropertyValue("clientConnectionFactory"));
		assertNull(dfa.getPropertyValue("serverConnectionFactory"));
		assertEquals(Boolean.TRUE, dfa.getPropertyValue("isClientMode"));
		assertSame(sched, dfa.getPropertyValue("taskScheduler"));
		assertEquals(123000L, dfa.getPropertyValue("retryInterval"));
	}

	@Test
	public void testOutClientMode() {
		DirectFieldAccessor dfa = new DirectFieldAccessor(tcpOutClientMode);
		assertSame(cfC4, dfa.getPropertyValue("clientConnectionFactory"));
		assertNull(dfa.getPropertyValue("serverConnectionFactory"));
		assertEquals(Boolean.TRUE, dfa.getPropertyValue("isClientMode"));
		assertSame(sched, dfa.getPropertyValue("taskScheduler"));
		assertEquals(124000L, dfa.getPropertyValue("retryInterval"));
	}

	@Test
	public void testInGatewayClientMode() {
		DirectFieldAccessor dfa = new DirectFieldAccessor(inGatewayClientMode);
		assertSame(cfC5, dfa.getPropertyValue("clientConnectionFactory"));
		assertNull(dfa.getPropertyValue("serverConnectionFactory"));
		assertEquals(Boolean.TRUE, dfa.getPropertyValue("isClientMode"));
		assertSame(sched, dfa.getPropertyValue("taskScheduler"));
		assertEquals(125000L, dfa.getPropertyValue("retryInterval"));
	}

	@Test
	public void testAutoTcp() {
		assertSame(tcpAutoChannel, TestUtils.getPropertyValue(tcpAutoAdapter, "outputChannel"));
	}

	@Test
	public void testAutoUdp() {
		assertSame(udpAutoChannel, TestUtils.getPropertyValue(udpAutoAdapter, "outputChannel"));
	}

	@Test
	public void testSecureServer() {
		DirectFieldAccessor dfa = new DirectFieldAccessor(secureServer);
		assertSame(socketFactorySupport, dfa.getPropertyValue("tcpSocketFactorySupport"));
		assertSame(socketSupport, dfa.getPropertyValue("tcpSocketSupport"));
	}

	@SuppressWarnings("unchecked")
	@Test
	public void testEventAdapter() {
		Set<?> eventTypes = TestUtils.getPropertyValue(this.eventAdapter, "eventTypes", Set.class);
		assertEquals(2, eventTypes.size());
		assertTrue(eventTypes.contains(EventSubclass1.class));
		assertTrue(eventTypes.contains(EventSubclass2.class));
		assertFalse(TestUtils.getPropertyValue(this.eventAdapter, "autoStartup", Boolean.class));
		assertEquals(23, TestUtils.getPropertyValue(this.eventAdapter, "phase"));
		assertEquals("eventErrors", TestUtils.getPropertyValue(this.eventAdapter, "errorChannel",
				DirectChannel.class).getComponentName());

		TcpConnectionSupport connection = mock(TcpConnectionSupport.class);
		TcpConnectionEvent event = new TcpConnectionOpenEvent(connection, "foo");
		Class<TcpConnectionEvent>[] types = (Class<TcpConnectionEvent>[]) new Class<?>[]{TcpConnectionEvent.class};
		this.eventAdapter.setEventTypes(types);
		this.eventAdapter.onApplicationEvent(event);
		assertNull(this.eventChannel.receive(0));
		this.eventAdapter.start();
		this.eventAdapter.onApplicationEvent(event);
		Message<?> eventMessage = this.eventChannel.receive(0);
		assertNotNull(eventMessage);
		assertSame(event, eventMessage.getPayload());
	}

	public static class FooAdvice extends AbstractRequestHandlerAdvice {

		@Override
		protected Object doInvoke(ExecutionCallback callback, Object target, Message<?> message) throws Exception {
			adviceCalled++;
			return null;
		}

	}

	@SuppressWarnings("serial")
	public static class EventSubclass1 extends TcpConnectionEvent {

		public EventSubclass1(TcpConnectionSupport connection, String connectionFactoryName) {
			super(connection, connectionFactoryName);
		}
	}

	@SuppressWarnings("serial")
	public static class EventSubclass2 extends TcpConnectionEvent {

		public EventSubclass2(TcpConnectionSupport connection, String connectionFactoryName) {
			super(connection, connectionFactoryName);
		}
	}
}


File: spring-integration-ip/src/test/java/org/springframework/integration/ip/tcp/ConnectionToConnectionTests.java
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

package org.springframework.integration.ip.tcp;

import static org.junit.Assert.assertEquals;
import static org.junit.Assert.assertFalse;
import static org.junit.Assert.assertNotNull;
import static org.junit.Assert.assertTrue;

import java.util.Properties;

import org.junit.FixMethodOrder;
import org.junit.Test;
import org.junit.runner.RunWith;
import org.junit.runners.MethodSorters;

import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.context.ConfigurableApplicationContext;
import org.springframework.context.support.AbstractApplicationContext;
import org.springframework.context.support.ClassPathXmlApplicationContext;
import org.springframework.messaging.Message;
import org.springframework.integration.channel.QueueChannel;
import org.springframework.integration.history.MessageHistory;
import org.springframework.integration.ip.tcp.connection.AbstractClientConnectionFactory;
import org.springframework.integration.ip.tcp.connection.AbstractServerConnectionFactory;
import org.springframework.integration.ip.tcp.connection.TcpConnection;
import org.springframework.integration.ip.tcp.connection.TcpConnectionCloseEvent;
import org.springframework.integration.ip.tcp.connection.TcpConnectionEvent;
import org.springframework.integration.ip.tcp.connection.TcpConnectionExceptionEvent;
import org.springframework.integration.ip.tcp.connection.TcpConnectionOpenEvent;
import org.springframework.integration.ip.tcp.serializer.ByteArrayRawSerializer;
import org.springframework.integration.ip.util.TestingUtilities;
import org.springframework.integration.support.MessageBuilder;
import org.springframework.integration.test.util.TestUtils;
import org.springframework.test.context.ContextConfiguration;
import org.springframework.test.context.junit4.SpringJUnit4ClassRunner;


/**
 * @author Gary Russell
 * @author Gunnar Hillert
 * @since 2.0
 *
 */
@ContextConfiguration
@RunWith(SpringJUnit4ClassRunner.class)
@FixMethodOrder(MethodSorters.NAME_ASCENDING)
public class ConnectionToConnectionTests {

	@Autowired
	AbstractApplicationContext ctx;

	@Autowired
	private AbstractClientConnectionFactory clientNet;

	@Autowired
	private AbstractServerConnectionFactory serverNet;

	@Autowired
	private AbstractClientConnectionFactory clientNio;

	@Autowired
	private AbstractServerConnectionFactory serverNio;

	@Autowired
	private QueueChannel serverSideChannel;

	@Autowired
	private QueueChannel events;

	// Test jvm shutdown
	public static void main(String[] args) {
		ConfigurableApplicationContext ctx = new ClassPathXmlApplicationContext(
				ConnectionToConnectionTests.class.getPackage().getName()
						.replaceAll("\\.", "/")
						+ "/common-context.xml");
		ctx.close();
		ctx = new ClassPathXmlApplicationContext(
				ConnectionToConnectionTests.class.getPackage().getName()
						.replaceAll("\\.", "/")
						+ "/ConnectionToConnectionTests-context.xml");
		ctx.close();
	}

	@Test
	public void testConnectNet() throws Exception {
		testConnectGuts(this.clientNet, this.serverNet, "gwNet", true);
	}

	@Test
	public void testConnectNio() throws Exception {
		testConnectGuts(this.clientNio, this.serverNio, "gwNio", false);
	}

	@SuppressWarnings("unchecked")
	private void testConnectGuts(AbstractClientConnectionFactory client, AbstractServerConnectionFactory server,
			String gatewayName, boolean expectExceptionOnClose) throws Exception {
		TestingUtilities.waitListening(server, null);
		client.start();
		for (int i = 0; i < 100; i++) {
			TcpConnection connection = client.getConnection();
			connection.send(MessageBuilder.withPayload("Test").build());
			Message<?> message = serverSideChannel.receive(10000);
			assertNotNull(message);
			MessageHistory history = MessageHistory.read(message);
			//org.springframework.integration.test.util.TestUtils
			Properties componentHistoryRecord = TestUtils.locateComponentInHistory(history, gatewayName, 0);
			assertNotNull(componentHistoryRecord);
			assertTrue(componentHistoryRecord.get("type").equals("ip:tcp-inbound-gateway"));
			assertNotNull(message);
			assertEquals("Test", new String((byte[]) message.getPayload()));
		}
		int clientOpens = 0;
		int clientCloses = 0;
		int serverOpens = 0;
		int serverCloses = 0;
		int clientExceptions = 0;
		Message<TcpConnectionEvent> eventMessage;
		while ((eventMessage = (Message<TcpConnectionEvent>) events.receive(1000)) != null) {
			TcpConnectionEvent event = eventMessage.getPayload();
			if (event.getConnectionFactoryName().startsWith("client")) {
				if (event instanceof TcpConnectionOpenEvent) {
					clientOpens++;
				}
				else if (event instanceof TcpConnectionCloseEvent) {
					clientCloses++;
				}
				else if (event instanceof TcpConnectionExceptionEvent) {
					clientExceptions++;
				}
			}
			else if (event.getConnectionFactoryName().startsWith("server")) {
				if (event instanceof TcpConnectionOpenEvent) {
					serverOpens++;
				}
				else if (event instanceof TcpConnectionCloseEvent) {
					serverCloses++;
				}
			}
		}
		assertEquals(100, clientOpens);
		assertEquals(100, clientCloses);
		if (expectExceptionOnClose) {
			assertEquals(100, clientExceptions);
		}
		assertEquals(100, serverOpens);
		assertEquals(100, serverCloses);
	}

	@Test
	public void testConnectRaw() throws Exception {
		ByteArrayRawSerializer serializer = new ByteArrayRawSerializer();
		clientNet.setSerializer(serializer);
		serverNet.setDeserializer(serializer);
		clientNet.start();
		TcpConnection connection = clientNet.getConnection();
		connection.send(MessageBuilder.withPayload("Test").build());
		Message<?> message = serverSideChannel.receive(10000);
		assertNotNull(message);
		MessageHistory history = MessageHistory.read(message);
		//org.springframework.integration.test.util.TestUtils
		Properties componentHistoryRecord = TestUtils.locateComponentInHistory(history, "gwNet", 0);
		assertNotNull(componentHistoryRecord);
		assertTrue(componentHistoryRecord.get("type").equals("ip:tcp-inbound-gateway"));
		assertNotNull(message);
		assertEquals("Test", new String((byte[]) message.getPayload()));
	}

	@Test
	public void testLookup() throws Exception {
		clientNet.start();
		TcpConnection connection = clientNet.getConnection();
		assertFalse(connection.getConnectionId().contains("localhost"));
		connection.close();
		clientNet.setLookupHost(true);
		connection = clientNet.getConnection();
		assertTrue(connection.getConnectionId().contains("localhost"));
		connection.close();
		clientNet.setLookupHost(false);
		connection = clientNet.getConnection();
		assertFalse(connection.getConnectionId().contains("localhost"));
		connection.close();
	}

}


File: spring-integration-ip/src/test/java/org/springframework/integration/ip/tcp/SyslogdTests.java
/*
 * Copyright 2002-2012 the original author or authors.
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
package org.springframework.integration.ip.tcp;

import org.springframework.context.support.AbstractApplicationContext;
import org.springframework.context.support.ClassPathXmlApplicationContext;

/**
 * @author Gary Russell
 * @since 2.2
 *
 */
public class SyslogdTests {

	public static void main(String[] args) throws Exception {
		AbstractApplicationContext ctx = new ClassPathXmlApplicationContext("SyslogdTests-context.xml", SyslogdTests.class);
		System.out.println("Hit enter to terminate");
		System.in.read();
		ctx.destroy();
	}

}


File: spring-integration-ip/src/test/java/org/springframework/integration/ip/tcp/TcpOutboundGatewayTests.java
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

package org.springframework.integration.ip.tcp;

import static org.junit.Assert.assertEquals;
import static org.junit.Assert.assertNotNull;
import static org.junit.Assert.assertNull;
import static org.junit.Assert.assertTrue;
import static org.junit.Assert.fail;
import static org.mockito.Mockito.doThrow;
import static org.mockito.Mockito.mock;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.when;

import java.io.EOFException;
import java.io.IOException;
import java.io.ObjectInputStream;
import java.io.ObjectOutputStream;
import java.net.ServerSocket;
import java.net.Socket;
import java.util.ArrayList;
import java.util.Collections;
import java.util.HashSet;
import java.util.List;
import java.util.Map;
import java.util.Set;
import java.util.concurrent.Callable;
import java.util.concurrent.CountDownLatch;
import java.util.concurrent.ExecutionException;
import java.util.concurrent.Executors;
import java.util.concurrent.Future;
import java.util.concurrent.TimeUnit;
import java.util.concurrent.atomic.AtomicBoolean;
import java.util.concurrent.atomic.AtomicReference;

import javax.net.ServerSocketFactory;

import org.apache.commons.logging.Log;
import org.apache.commons.logging.LogFactory;
import org.junit.Test;
import org.mockito.Mockito;

import org.springframework.beans.factory.BeanFactory;
import org.springframework.core.serializer.DefaultDeserializer;
import org.springframework.core.serializer.DefaultSerializer;
import org.springframework.expression.spel.standard.SpelExpressionParser;
import org.springframework.integration.MessageTimeoutException;
import org.springframework.integration.channel.QueueChannel;
import org.springframework.integration.ip.tcp.connection.AbstractClientConnectionFactory;
import org.springframework.integration.ip.tcp.connection.AbstractConnectionFactory;
import org.springframework.integration.ip.tcp.connection.CachingClientConnectionFactory;
import org.springframework.integration.ip.tcp.connection.FailoverClientConnectionFactory;
import org.springframework.integration.ip.tcp.connection.TcpConnectionSupport;
import org.springframework.integration.ip.tcp.connection.TcpNetClientConnectionFactory;
import org.springframework.integration.ip.tcp.connection.TcpNioClientConnectionFactory;
import org.springframework.integration.support.MessageBuilder;
import org.springframework.integration.test.util.SocketUtils;
import org.springframework.integration.test.util.TestUtils;
import org.springframework.messaging.Message;
import org.springframework.messaging.PollableChannel;
import org.springframework.messaging.support.GenericMessage;

/**
 * @author Gary Russell
 * @since 2.0
 */
public class TcpOutboundGatewayTests {

	private final Log logger = LogFactory.getLog(this.getClass());

	@Test
	public void testGoodNetSingle() throws Exception {
		final int port = SocketUtils.findAvailableServerSocket();
		AbstractConnectionFactory ccf = new TcpNetClientConnectionFactory("localhost", port);
		final CountDownLatch latch = new CountDownLatch(1);
		final AtomicBoolean done = new AtomicBoolean();
		final AtomicReference<ServerSocket> serverSocket = new AtomicReference<ServerSocket>();
		Executors.newSingleThreadExecutor().execute(new Runnable() {
			@Override
			public void run() {
				try {
					ServerSocket server = ServerSocketFactory.getDefault().createServerSocket(port, 100);
					serverSocket.set(server);
					latch.countDown();
					List<Socket> sockets = new ArrayList<Socket>();
					int i = 0;
					while (true) {
						Socket socket = server.accept();
						ObjectInputStream ois = new ObjectInputStream(socket.getInputStream());
						ois.readObject();
						ObjectOutputStream oos = new ObjectOutputStream(socket.getOutputStream());
						oos.writeObject("Reply" + (i++));
						sockets.add(socket);
					}
				}
				catch (Exception e) {
					if (!done.get()) {
						e.printStackTrace();
					}
				}
			}
		});
		ccf.setSerializer(new DefaultSerializer());
		ccf.setDeserializer(new DefaultDeserializer());
		ccf.setSoTimeout(10000);
		ccf.setSingleUse(true);
		ccf.start();
		assertTrue(latch.await(10000, TimeUnit.MILLISECONDS));
		TcpOutboundGateway gateway = new TcpOutboundGateway();
		gateway.setConnectionFactory(ccf);
		QueueChannel replyChannel = new QueueChannel();
		gateway.setRequiresReply(true);
		gateway.setOutputChannel(replyChannel);
		// check the default remote timeout
		assertEquals("10000", TestUtils.getPropertyValue(gateway, "remoteTimeoutExpression.literalValue"));
		gateway.setSendTimeout(123);
		gateway.setRemoteTimeout(60000);
		gateway.setSendTimeout(61000);
		// ensure this did NOT change the remote timeout
		assertEquals("60000", TestUtils.getPropertyValue(gateway, "remoteTimeoutExpression.literalValue"));
		gateway.setRequestTimeout(60000);
		for (int i = 100; i < 200; i++) {
			gateway.handleMessage(MessageBuilder.withPayload("Test" + i).build());
		}
		Set<String> replies = new HashSet<String>();
		for (int i = 100; i < 200; i++) {
			Message<?> m = replyChannel.receive(10000);
			assertNotNull(m);
			replies.add((String) m.getPayload());
		}
		for (int i = 0; i < 100; i++) {
			assertTrue(replies.remove("Reply" + i));
		}
		done.set(true);
		serverSocket.get().close();
	}

	@Test
	public void testGoodNetMultiplex() throws Exception {
		final int port = SocketUtils.findAvailableServerSocket();
		final CountDownLatch latch = new CountDownLatch(1);
		final AtomicBoolean done = new AtomicBoolean();
		Executors.newSingleThreadExecutor().execute(new Runnable() {
			@Override
			public void run() {
				try {
					ServerSocket server = ServerSocketFactory.getDefault().createServerSocket(port, 10);
					latch.countDown();
					int i = 0;
					Socket socket = server.accept();
					while (true) {
						ObjectInputStream ois = new ObjectInputStream(socket.getInputStream());
						ois.readObject();
						ObjectOutputStream oos = new ObjectOutputStream(socket.getOutputStream());
						oos.writeObject("Reply" + (i++));
					}
				} catch (Exception e) {
					if (!done.get()) {
						e.printStackTrace();
					}
				}
			}
		});
		AbstractConnectionFactory ccf = new TcpNetClientConnectionFactory("localhost", port);
		ccf.setSerializer(new DefaultSerializer());
		ccf.setDeserializer(new DefaultDeserializer());
		ccf.setSoTimeout(10000);
		ccf.setSingleUse(false);
		ccf.start();
		assertTrue(latch.await(10000, TimeUnit.MILLISECONDS));
		TcpOutboundGateway gateway = new TcpOutboundGateway();
		gateway.setConnectionFactory(ccf);
		QueueChannel replyChannel = new QueueChannel();
		gateway.setRequiresReply(true);
		gateway.setOutputChannel(replyChannel);
		for (int i = 100; i < 110; i++) {
			gateway.handleMessage(MessageBuilder.withPayload("Test" + i).build());
		}
		Set<String> replies = new HashSet<String>();
		for (int i = 100; i < 110; i++) {
			Message<?> m = replyChannel.receive(10000);
			assertNotNull(m);
			replies.add((String) m.getPayload());
		}
		for (int i = 0; i < 10; i++) {
			assertTrue(replies.remove("Reply" + i));
		}
		done.set(true);
		gateway.stop();
	}

	@Test
	public void testGoodNetTimeout() throws Exception {
		final int port = SocketUtils.findAvailableServerSocket();
		final CountDownLatch latch = new CountDownLatch(1);
		final AtomicBoolean done = new AtomicBoolean();
		Executors.newSingleThreadExecutor().execute(new Runnable() {
			@Override
			public void run() {
				try {
					ServerSocket server = ServerSocketFactory.getDefault().createServerSocket(port);
					latch.countDown();
					int i = 0;
					Socket socket = server.accept();
					while (true) {
						ObjectInputStream ois = new ObjectInputStream(socket.getInputStream());
						ois.readObject();
						ObjectOutputStream oos = new ObjectOutputStream(socket.getOutputStream());
						Thread.sleep(1000);
						oos.writeObject("Reply" + (i++));
					}
				} catch (Exception e) {
					if (!done.get()) {
						e.printStackTrace();
					}
				}
			}
		});
		AbstractConnectionFactory ccf = new TcpNetClientConnectionFactory("localhost", port);
		ccf.setSerializer(new DefaultSerializer());
		ccf.setDeserializer(new DefaultDeserializer());
		ccf.setSoTimeout(10000);
		ccf.setSingleUse(false);
		ccf.start();
		assertTrue(latch.await(10000, TimeUnit.MILLISECONDS));
		final TcpOutboundGateway gateway = new TcpOutboundGateway();
		gateway.setConnectionFactory(ccf);
		gateway.setRequestTimeout(1);
		QueueChannel replyChannel = new QueueChannel();
		gateway.setRequiresReply(true);
		gateway.setOutputChannel(replyChannel);
		@SuppressWarnings("unchecked")
		Future<Integer>[] results = (Future<Integer>[]) new Future<?>[2];
		for (int i = 0; i < 2; i++) {
			final int j = i;
			results[j] = (Executors.newSingleThreadExecutor().submit(new Callable<Integer>(){
				@Override
				public Integer call() throws Exception {
					gateway.handleMessage(MessageBuilder.withPayload("Test" + j).build());
					return 0;
				}
			}));
		}
		Set<String> replies = new HashSet<String>();
		int timeouts = 0;
		for (int i = 0; i < 2; i++) {
			try {
				results[i].get();
			} catch (ExecutionException e) {
				if (timeouts > 0) {
					fail("Unexpected " + e.getMessage());
				} else {
					assertNotNull(e.getCause());
					assertTrue(e.getCause() instanceof MessageTimeoutException);
				}
				timeouts++;
				continue;
			}
			Message<?> m = replyChannel.receive(10000);
			assertNotNull(m);
			replies.add((String) m.getPayload());
		}
		if (timeouts < 1) {
			fail("Expected ExecutionException");
		}
		for (int i = 0; i < 1; i++) {
			assertTrue(replies.remove("Reply" + i));
		}
		done.set(true);
		gateway.stop();
	}

	@Test
	public void testGoodNetGWTimeout() throws Exception {
		final int port = SocketUtils.findAvailableServerSocket();
		AbstractClientConnectionFactory ccf = buildCF(port);
		ccf.start();
		testGoodNetGWTimeoutGuts(port, ccf);
	}

	@Test
	public void testGoodNetGWTimeoutCached() throws Exception {
		final int port = SocketUtils.findAvailableServerSocket();
		AbstractClientConnectionFactory ccf = buildCF(port);
		CachingClientConnectionFactory cccf = new CachingClientConnectionFactory(ccf, 1);
		cccf.start();
		testGoodNetGWTimeoutGuts(port, cccf);
	}

	private AbstractClientConnectionFactory buildCF(final int port) {
		AbstractClientConnectionFactory ccf = new TcpNetClientConnectionFactory("localhost", port);
		ccf.setSerializer(new DefaultSerializer());
		ccf.setDeserializer(new DefaultDeserializer());
		ccf.setSoTimeout(10000);
		ccf.setSingleUse(false);
		return ccf;
	}

	/**
	 * Sends 2 concurrent messages on a shared connection. The GW single threads
	 * these requests. The first will timeout; the second should receive its
	 * own response, not that for the first.
	 * @throws Exception
	 */
	private void testGoodNetGWTimeoutGuts(final int port, AbstractConnectionFactory ccf) throws InterruptedException {
		final CountDownLatch latch = new CountDownLatch(1);
		final AtomicBoolean done = new AtomicBoolean();
		/*
		 * The payload of the last message received by the remote side;
		 * used to verify the correct response is received.
		 */
		final AtomicReference<String> lastReceived = new AtomicReference<String>();
		final CountDownLatch serverLatch = new CountDownLatch(2);

		Executors.newSingleThreadExecutor().execute(new Runnable() {

			@Override
			public void run() {
				try {
					ServerSocket server = ServerSocketFactory.getDefault().createServerSocket(port);
					latch.countDown();
					int i = 0;
					while (!done.get()) {
						Socket socket = server.accept();
						i++;
						while (!socket.isClosed()) {
							try {
								ObjectInputStream ois = new ObjectInputStream(socket.getInputStream());
								String request = (String) ois.readObject();
								logger.debug("Read " + request);
								ObjectOutputStream oos = new ObjectOutputStream(socket.getOutputStream());
								if (i < 2) {
									Thread.sleep(1000);
								}
								oos.writeObject(request.replace("Test", "Reply"));
								logger.debug("Replied to " + request);
								lastReceived.set(request);
								serverLatch.countDown();
							}
							catch (IOException e) {
								logger.debug("error on write " + e.getClass().getSimpleName());
								socket.close();
							}
						}
					}
				}
				catch (Exception e) {
					if (!done.get()) {
						e.printStackTrace();
					}
				}
			}
		});
		assertTrue(latch.await(10000, TimeUnit.MILLISECONDS));
		final TcpOutboundGateway gateway = new TcpOutboundGateway();
		gateway.setConnectionFactory(ccf);
		gateway.setRequestTimeout(Integer.MAX_VALUE);
		QueueChannel replyChannel = new QueueChannel();
		gateway.setRequiresReply(true);
		gateway.setOutputChannel(replyChannel);
		gateway.setRemoteTimeout(500);
		@SuppressWarnings("unchecked")
		Future<Integer>[] results = (Future<Integer>[]) new Future<?>[2];
		for (int i = 0; i < 2; i++) {
			final int j = i;
			results[j] = (Executors.newSingleThreadExecutor().submit(new Callable<Integer>() {
				@Override
				public Integer call() throws Exception {
					// increase the timeout after the first send
					if (j > 0) {
						gateway.setRemoteTimeout(5000);
					}
					gateway.handleMessage(MessageBuilder.withPayload("Test" + j).build());
					return j;
				}
			}));
			Thread.sleep(50);
		}
		// wait until the server side has processed both requests
		assertTrue(serverLatch.await(10, TimeUnit.SECONDS));
		List<String> replies = new ArrayList<String>();
		int timeouts = 0;
		for (int i = 0; i < 2; i++) {
			try {
				int result = results[i].get();
				String reply = (String) replyChannel.receive(1000).getPayload();
				logger.debug(i + " got " + result + " " + reply);
				replies.add(reply);
			}
			catch (ExecutionException e) {
				if (timeouts >= 2) {
					fail("Unexpected " + e.getMessage());
				}
				else {
					assertNotNull(e.getCause());
					assertTrue(e.getCause() instanceof MessageTimeoutException);
				}
				timeouts++;
				continue;
			}
		}
		assertEquals("Expected exactly one ExecutionException", 1, timeouts);
		assertEquals(1, replies.size());
		assertEquals(lastReceived.get().replace("Test", "Reply"), replies.get(0));
		done.set(true);
		assertEquals(0, TestUtils.getPropertyValue(gateway, "pendingReplies", Map.class).size());
		gateway.stop();
	}

	@Test
	public void testCachingFailover() throws Exception {
		final int port = SocketUtils.findAvailableServerSocket();
		final CountDownLatch latch = new CountDownLatch(1);
		final AtomicBoolean done = new AtomicBoolean();
		final CountDownLatch serverLatch = new CountDownLatch(1);

		Executors.newSingleThreadExecutor().execute(new Runnable() {

			@Override
			public void run() {
				try {
					ServerSocket server = ServerSocketFactory.getDefault().createServerSocket(port);
					latch.countDown();
					while (!done.get()) {
						Socket socket = server.accept();
						while (!socket.isClosed()) {
							try {
								ObjectInputStream ois = new ObjectInputStream(socket.getInputStream());
								String request = (String) ois.readObject();
								logger.debug("Read " + request);
								ObjectOutputStream oos = new ObjectOutputStream(socket.getOutputStream());
								oos.writeObject("bar");
								logger.debug("Replied to " + request);
								serverLatch.countDown();
							}
							catch (IOException e) {
								logger.debug("error on write " + e.getClass().getSimpleName());
								socket.close();
							}
						}
					}
				}
				catch (Exception e) {
					if (!done.get()) {
						e.printStackTrace();
					}
				}
			}
		});
		assertTrue(latch.await(10000, TimeUnit.MILLISECONDS));

		// Failover
		AbstractClientConnectionFactory factory1 = mock(AbstractClientConnectionFactory.class);
		TcpConnectionSupport mockConn1 = makeMockConnection();
		when(factory1.getConnection()).thenReturn(mockConn1);
		doThrow(new IOException("fail")).when(mockConn1).send(Mockito.any(Message.class));

		AbstractClientConnectionFactory factory2 = new TcpNetClientConnectionFactory("localhost", port);
		factory2.setSerializer(new DefaultSerializer());
		factory2.setDeserializer(new DefaultDeserializer());
		factory2.setSoTimeout(10000);
		factory2.setSingleUse(false);

		List<AbstractClientConnectionFactory> factories = new ArrayList<AbstractClientConnectionFactory>();
		factories.add(factory1);
		factories.add(factory2);
		FailoverClientConnectionFactory failoverFactory = new FailoverClientConnectionFactory(factories);
		failoverFactory.start();

		// Cache
		CachingClientConnectionFactory cachingFactory = new CachingClientConnectionFactory(failoverFactory, 2);
		cachingFactory.start();
		TcpOutboundGateway gateway = new TcpOutboundGateway();
		gateway.setConnectionFactory(cachingFactory);
		PollableChannel outputChannel = new QueueChannel();
		gateway.setOutputChannel(outputChannel);
		gateway.setBeanFactory(mock(BeanFactory.class));
		gateway.afterPropertiesSet();
		gateway.start();

		GenericMessage<String> message = new GenericMessage<String>("foo");
		gateway.handleMessage(message);
		Message<?> reply = outputChannel.receive(0);
		assertNotNull(reply);
		assertEquals("bar", reply.getPayload());
		done.set(true);
		gateway.stop();
		verify(mockConn1).send(Mockito.any(Message.class));
	}

	@Test
	public void testFailoverCached() throws Exception {
		final int port = SocketUtils.findAvailableServerSocket();
		final CountDownLatch latch = new CountDownLatch(1);
		final AtomicBoolean done = new AtomicBoolean();
		final CountDownLatch serverLatch = new CountDownLatch(1);

		Executors.newSingleThreadExecutor().execute(new Runnable() {

			@Override
			public void run() {
				try {
					ServerSocket server = ServerSocketFactory.getDefault().createServerSocket(port);
					latch.countDown();
					while (!done.get()) {
						Socket socket = server.accept();
						while (!socket.isClosed()) {
							try {
								ObjectInputStream ois = new ObjectInputStream(socket.getInputStream());
								String request = (String) ois.readObject();
								logger.debug("Read " + request);
								ObjectOutputStream oos = new ObjectOutputStream(socket.getOutputStream());
								oos.writeObject("bar");
								logger.debug("Replied to " + request);
								serverLatch.countDown();
							}
							catch (IOException e) {
								logger.debug("error on write " + e.getClass().getSimpleName());
								socket.close();
							}
						}
					}
				}
				catch (Exception e) {
					if (!done.get()) {
						e.printStackTrace();
					}
				}
			}
		});
		assertTrue(latch.await(10000, TimeUnit.MILLISECONDS));

		// Cache
		AbstractClientConnectionFactory factory1 = mock(AbstractClientConnectionFactory.class);
		TcpConnectionSupport mockConn1 = makeMockConnection();
		when(factory1.getConnection()).thenReturn(mockConn1);
		doThrow(new IOException("fail")).when(mockConn1).send(Mockito.any(Message.class));
		CachingClientConnectionFactory cachingFactory1 = new CachingClientConnectionFactory(factory1, 1);

		AbstractClientConnectionFactory factory2 = new TcpNetClientConnectionFactory("localhost", port);
		factory2.setSerializer(new DefaultSerializer());
		factory2.setDeserializer(new DefaultDeserializer());
		factory2.setSoTimeout(10000);
		factory2.setSingleUse(false);
		CachingClientConnectionFactory cachingFactory2 = new CachingClientConnectionFactory(factory2, 1);

		// Failover
		List<AbstractClientConnectionFactory> factories = new ArrayList<AbstractClientConnectionFactory>();
		factories.add(cachingFactory1);
		factories.add(cachingFactory2);
		FailoverClientConnectionFactory failoverFactory = new FailoverClientConnectionFactory(factories);
		failoverFactory.start();

		TcpOutboundGateway gateway = new TcpOutboundGateway();
		gateway.setConnectionFactory(failoverFactory);
		PollableChannel outputChannel = new QueueChannel();
		gateway.setOutputChannel(outputChannel);
		gateway.setBeanFactory(mock(BeanFactory.class));
		gateway.afterPropertiesSet();
		gateway.start();

		GenericMessage<String> message = new GenericMessage<String>("foo");
		gateway.handleMessage(message);
		Message<?> reply = outputChannel.receive(0);
		assertNotNull(reply);
		assertEquals("bar", reply.getPayload());
		done.set(true);
		gateway.stop();
		verify(mockConn1).send(Mockito.any(Message.class));
	}

	public TcpConnectionSupport makeMockConnection() {
		TcpConnectionSupport connection = mock(TcpConnectionSupport.class);
		when(connection.isOpen()).thenReturn(true);
		return connection;
	}

	@Test
	public void testNetGWPropagatesSocketClose() throws Exception {
		final int port = SocketUtils.findAvailableServerSocket();
		AbstractClientConnectionFactory ccf = new TcpNetClientConnectionFactory("localhost", port);
		ccf.setSerializer(new DefaultSerializer());
		ccf.setDeserializer(new DefaultDeserializer());
		ccf.setSoTimeout(10000);
		ccf.setSingleUse(false);
		ccf.start();
		testGWPropagatesSocketCloseGuts(port, ccf);
	}

	@Test
	public void testNioGWPropagatesSocketClose() throws Exception {
		final int port = SocketUtils.findAvailableServerSocket();
		AbstractClientConnectionFactory ccf = new TcpNioClientConnectionFactory("localhost", port);
		ccf.setSerializer(new DefaultSerializer());
		ccf.setDeserializer(new DefaultDeserializer());
		ccf.setSoTimeout(10000);
		ccf.setSingleUse(false);
		ccf.start();
		testGWPropagatesSocketCloseGuts(port, ccf);
	}

	@Test
	public void testCachedGWPropagatesSocketClose() throws Exception {
		final int port = SocketUtils.findAvailableServerSocket();
		AbstractClientConnectionFactory ccf = new TcpNetClientConnectionFactory("localhost", port);
		ccf.setSerializer(new DefaultSerializer());
		ccf.setDeserializer(new DefaultDeserializer());
		ccf.setSoTimeout(10000);
		ccf.setSingleUse(false);
		CachingClientConnectionFactory cccf = new CachingClientConnectionFactory(ccf, 1);
		cccf.start();
		testGWPropagatesSocketCloseGuts(port, cccf);
	}

	@Test
	public void testFailoverGWPropagatesSocketClose() throws Exception {
		final int port = SocketUtils.findAvailableServerSocket();
		AbstractClientConnectionFactory ccf = new TcpNetClientConnectionFactory("localhost", port);
		ccf.setSerializer(new DefaultSerializer());
		ccf.setDeserializer(new DefaultDeserializer());
		ccf.setSoTimeout(10000);
		ccf.setSingleUse(false);
		FailoverClientConnectionFactory focf = new FailoverClientConnectionFactory(
				Collections.singletonList(ccf));
		focf.start();
		testGWPropagatesSocketCloseGuts(port, focf);
	}

	private void testGWPropagatesSocketCloseGuts(final int port, AbstractClientConnectionFactory ccf) throws Exception {
		final CountDownLatch latch = new CountDownLatch(1);
		final AtomicBoolean done = new AtomicBoolean();
		final AtomicReference<String> lastReceived = new AtomicReference<String>();
		final CountDownLatch serverLatch = new CountDownLatch(1);

		Executors.newSingleThreadExecutor().execute(new Runnable() {

			@Override
			public void run() {
				try {
					ServerSocket server = ServerSocketFactory.getDefault().createServerSocket(port);
					latch.countDown();
					while (!done.get()) {
						Socket socket = server.accept();
						while (!socket.isClosed()) {
							try {
								ObjectInputStream ois = new ObjectInputStream(socket.getInputStream());
								String request = (String) ois.readObject();
								logger.debug("Read " + request + " closing socket");
								socket.close();
								lastReceived.set(request);
								serverLatch.countDown();
							}
							catch (IOException e) {
								socket.close();
							}
						}
					}
				}
				catch (Exception e) {
					if (!done.get()) {
						e.printStackTrace();
					}
				}
			}
		});
		assertTrue(latch.await(10000, TimeUnit.MILLISECONDS));
		final TcpOutboundGateway gateway = new TcpOutboundGateway();
		gateway.setConnectionFactory(ccf);
		gateway.setRequestTimeout(Integer.MAX_VALUE);
		QueueChannel replyChannel = new QueueChannel();
		gateway.setRequiresReply(true);
		gateway.setOutputChannel(replyChannel);
		gateway.setRemoteTimeoutExpression(new SpelExpressionParser().parseExpression("5000"));
		gateway.setBeanFactory(mock(BeanFactory.class));
		gateway.afterPropertiesSet();
		gateway.start();
		try {
			gateway.handleMessage(MessageBuilder.withPayload("Test").build());
			fail("expected failure");
		}
		catch (Exception e) {
			assertTrue(e.getCause() instanceof EOFException);
		}
		assertEquals(0, TestUtils.getPropertyValue(gateway, "pendingReplies", Map.class).size());
		Message<?> reply = replyChannel.receive(0);
		assertNull(reply);
		done.set(true);
		ccf.getConnection();
	}

}


File: spring-integration-ip/src/test/java/org/springframework/integration/ip/tcp/TcpSendingMessageHandlerTests.java
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

package org.springframework.integration.ip.tcp;

import static org.junit.Assert.assertEquals;
import static org.junit.Assert.assertNotNull;
import static org.junit.Assert.assertTrue;
import static org.junit.Assert.fail;
import static org.mockito.Mockito.mock;

import java.io.IOException;
import java.io.InputStream;
import java.io.ObjectInputStream;
import java.io.ObjectOutputStream;
import java.net.ServerSocket;
import java.net.Socket;
import java.net.SocketException;
import java.util.ArrayList;
import java.util.HashSet;
import java.util.List;
import java.util.Set;
import java.util.TreeSet;
import java.util.concurrent.CountDownLatch;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;
import java.util.concurrent.Semaphore;
import java.util.concurrent.TimeUnit;
import java.util.concurrent.atomic.AtomicBoolean;

import javax.net.ServerSocketFactory;

import org.apache.commons.logging.Log;
import org.apache.commons.logging.LogFactory;
import org.junit.Test;
import org.mockito.Mockito;
import org.mockito.invocation.InvocationOnMock;
import org.mockito.stubbing.Answer;

import org.springframework.beans.factory.BeanFactory;
import org.springframework.context.support.AbstractApplicationContext;
import org.springframework.context.support.ClassPathXmlApplicationContext;
import org.springframework.core.serializer.DefaultDeserializer;
import org.springframework.core.serializer.DefaultSerializer;
import org.springframework.integration.channel.QueueChannel;
import org.springframework.integration.ip.tcp.connection.AbstractClientConnectionFactory;
import org.springframework.integration.ip.tcp.connection.AbstractConnectionFactory;
import org.springframework.integration.ip.tcp.connection.AbstractServerConnectionFactory;
import org.springframework.integration.ip.tcp.connection.TcpConnectionInterceptorFactory;
import org.springframework.integration.ip.tcp.connection.TcpConnectionInterceptorFactoryChain;
import org.springframework.integration.ip.tcp.connection.TcpNetClientConnectionFactory;
import org.springframework.integration.ip.tcp.connection.TcpNioClientConnectionFactory;
import org.springframework.integration.ip.tcp.serializer.ByteArrayCrLfSerializer;
import org.springframework.integration.ip.tcp.serializer.ByteArrayLengthHeaderSerializer;
import org.springframework.integration.ip.tcp.serializer.ByteArrayStxEtxSerializer;
import org.springframework.integration.ip.util.TestingUtilities;
import org.springframework.integration.support.MessageBuilder;
import org.springframework.integration.test.util.SocketUtils;
import org.springframework.messaging.Message;
import org.springframework.messaging.MessageChannel;
import org.springframework.messaging.MessagingException;
import org.springframework.messaging.PollableChannel;
import org.springframework.messaging.support.GenericMessage;
import org.springframework.scheduling.concurrent.ThreadPoolTaskScheduler;


/**
 * @author Gary Russell
 * @author Artem Bilan
 * @since 2.0
 */
public class TcpSendingMessageHandlerTests extends AbstractTcpChannelAdapterTests {

	private static final Log logger = LogFactory.getLog(TcpSendingMessageHandlerTests.class);


	private void readFully(InputStream is, byte[] buff) throws IOException {
		for (int i = 0; i < buff.length; i++) {
			buff[i] = (byte) is.read();
		}
	}

	@Test
	public void testNetCrLf() throws Exception {
		final int port = SocketUtils.findAvailableServerSocket();
		final CountDownLatch latch = new CountDownLatch(1);
		final AtomicBoolean done = new AtomicBoolean();
		Executors.newSingleThreadExecutor().execute(new Runnable() {
			@Override
			public void run() {
				try {
					ServerSocket server = ServerSocketFactory.getDefault().createServerSocket(port);
					latch.countDown();
					Socket socket = server.accept();
					int i = 0;
					while (true) {
						byte[] b = new byte[6];
						readFully(socket.getInputStream(), b);
						b = ("Reply" + (++i) + "\r\n").getBytes();
						socket.getOutputStream().write(b);
					}
				}
				catch (Exception e) {
					if (!done.get()) {
						e.printStackTrace();
					}
				}
			}
		});
		AbstractConnectionFactory ccf = new TcpNetClientConnectionFactory("localhost", port);
		noopPublisher(ccf);
		ByteArrayCrLfSerializer serializer = new ByteArrayCrLfSerializer();
		ccf.setSerializer(serializer);
		ccf.setDeserializer(serializer);
		ccf.setSoTimeout(10000);
		ccf.start();
		TcpSendingMessageHandler handler = new TcpSendingMessageHandler();
		handler.setConnectionFactory(ccf);
		TcpReceivingChannelAdapter adapter = new TcpReceivingChannelAdapter();
		adapter.setConnectionFactory(ccf);
		QueueChannel channel = new QueueChannel();
		adapter.setOutputChannel(channel);
		assertTrue(latch.await(10, TimeUnit.SECONDS));
		handler.handleMessage(MessageBuilder.withPayload("Test").build());
		handler.handleMessage(MessageBuilder.withPayload("Test").build());
		Message<?> mOut = channel.receive(10000);
		assertNotNull(mOut);
		assertEquals("Reply1", new String((byte[]) mOut.getPayload()));
		mOut = channel.receive(10000);
		assertNotNull(mOut);
		assertEquals("Reply2", new String((byte[]) mOut.getPayload()));
		done.set(true);
		ccf.stop();
	}

	@Test
	public void testNetCrLfClientMode() throws Exception {
		final int port = SocketUtils.findAvailableServerSocket();
		final CountDownLatch latch = new CountDownLatch(1);
		final AtomicBoolean done = new AtomicBoolean();
		Executors.newSingleThreadExecutor().execute(new Runnable() {
			@Override
			public void run() {
				try {
					ServerSocket server = ServerSocketFactory.getDefault().createServerSocket(port);
					latch.countDown();
					Socket socket = server.accept();
					int i = 0;
					while (true) {
						byte[] b = new byte[6];
						readFully(socket.getInputStream(), b);
						b = ("Reply" + (++i) + "\r\n").getBytes();
						socket.getOutputStream().write(b);
					}
				}
				catch (Exception e) {
					if (!done.get()) {
						e.printStackTrace();
					}
				}
			}
		});
		AbstractConnectionFactory ccf = new TcpNetClientConnectionFactory("localhost", port);
		noopPublisher(ccf);
		ByteArrayCrLfSerializer serializer = new ByteArrayCrLfSerializer();
		ccf.setSerializer(serializer);
		ccf.setDeserializer(serializer);
		ccf.setSoTimeout(Integer.MAX_VALUE);
		TcpSendingMessageHandler handler = new TcpSendingMessageHandler();
		handler.setConnectionFactory(ccf);
		TcpReceivingChannelAdapter adapter = new TcpReceivingChannelAdapter();
		adapter.setConnectionFactory(ccf);
		QueueChannel channel = new QueueChannel();
		adapter.setOutputChannel(channel);
		assertTrue(latch.await(10, TimeUnit.SECONDS));
		handler.setClientMode(true);
		handler.setRetryInterval(10000);
		handler.setBeanFactory(mock(BeanFactory.class));
		handler.afterPropertiesSet();
		ThreadPoolTaskScheduler taskScheduler = new ThreadPoolTaskScheduler();
		taskScheduler.setPoolSize(1);
		taskScheduler.initialize();
		handler.setTaskScheduler(taskScheduler);
		handler.start();
		adapter.start();
		handler.handleMessage(MessageBuilder.withPayload("Test").build());
		handler.handleMessage(MessageBuilder.withPayload("Test").build());
		Message<?> mOut = channel.receive(10000);
		assertNotNull(mOut);
		assertEquals("Reply1", new String((byte[]) mOut.getPayload()));
		mOut = channel.receive(10000);
		assertNotNull(mOut);
		assertEquals("Reply2", new String((byte[]) mOut.getPayload()));
		done.set(true);
		handler.stop();
		handler.start();
		handler.stop();
		adapter.stop();
	}

	@Test
	public void testNioCrLf() throws Exception {
		final int port = SocketUtils.findAvailableServerSocket();
		final CountDownLatch latch = new CountDownLatch(1);
		final AtomicBoolean done = new AtomicBoolean();
		Executors.newSingleThreadExecutor().execute(new Runnable() {
			@Override
			public void run() {
				try {
					ServerSocket server = ServerSocketFactory.getDefault().createServerSocket(port);
					latch.countDown();
					Socket socket = server.accept();
					int i = 0;
					while (true) {
						byte[] b = new byte[6];
						readFully(socket.getInputStream(), b);
						b = ("Reply" + (++i) + "\r\n").getBytes();
						socket.getOutputStream().write(b);
					}
				} catch (Exception e) {
					if (!done.get()) {
						e.printStackTrace();
					}
				}
			}
		});
		AbstractConnectionFactory ccf = new TcpNioClientConnectionFactory("localhost", port);
		noopPublisher(ccf);
		ByteArrayCrLfSerializer serializer = new ByteArrayCrLfSerializer();
		ccf.setSerializer(serializer);
		ccf.setDeserializer(serializer);
		ccf.setSoTimeout(10000);
		ccf.start();
		TcpSendingMessageHandler handler = new TcpSendingMessageHandler();
		handler.setConnectionFactory(ccf);
		TcpReceivingChannelAdapter adapter = new TcpReceivingChannelAdapter();
		adapter.setConnectionFactory(ccf);
		QueueChannel channel = new QueueChannel();
		adapter.setOutputChannel(channel);
		assertTrue(latch.await(10, TimeUnit.SECONDS));
		handler.handleMessage(MessageBuilder.withPayload("Test").build());
		handler.handleMessage(MessageBuilder.withPayload("Test").build());
		Set<String> results = new HashSet<String>();
		Message<?> mOut = channel.receive(10000);
		assertNotNull(mOut);
		results.add(new String((byte[]) mOut.getPayload()));
		mOut = channel.receive(10000);
		assertNotNull(mOut);
		results.add(new String((byte[]) mOut.getPayload()));
		assertTrue(results.remove("Reply1"));
		assertTrue(results.remove("Reply2"));
		done.set(true);
		ccf.stop();
	}

	@Test
	public void testNetStxEtx() throws Exception {
		final int port = SocketUtils.findAvailableServerSocket();
		final CountDownLatch latch = new CountDownLatch(1);
		final AtomicBoolean done = new AtomicBoolean();
		Executors.newSingleThreadExecutor().execute(new Runnable() {
			@Override
			public void run() {
				try {
					ServerSocket server = ServerSocketFactory.getDefault().createServerSocket(port);
					latch.countDown();
					Socket socket = server.accept();
					int i = 0;
					while (true) {
						byte[] b = new byte[6];
						readFully(socket.getInputStream(), b);
						b = ("\u0002Reply" + (++i) + "\u0003").getBytes();
						socket.getOutputStream().write(b);
					}
				} catch (Exception e) {
					if (!done.get()) {
						e.printStackTrace();
					}
				}
			}
		});
		AbstractConnectionFactory ccf = new TcpNetClientConnectionFactory("localhost", port);
		noopPublisher(ccf);
		ByteArrayStxEtxSerializer serializer = new ByteArrayStxEtxSerializer();
		ccf.setSerializer(serializer);
		ccf.setDeserializer(serializer);
		ccf.setSoTimeout(10000);
		ccf.start();
		TcpSendingMessageHandler handler = new TcpSendingMessageHandler();
		handler.setConnectionFactory(ccf);
		TcpReceivingChannelAdapter adapter = new TcpReceivingChannelAdapter();
		adapter.setConnectionFactory(ccf);
		QueueChannel channel = new QueueChannel();
		adapter.setOutputChannel(channel);
		assertTrue(latch.await(10, TimeUnit.SECONDS));
		handler.handleMessage(MessageBuilder.withPayload("Test").build());
		handler.handleMessage(MessageBuilder.withPayload("Test").build());
		Message<?> mOut = channel.receive(10000);
		assertNotNull(mOut);
		assertEquals("Reply1", new String((byte[]) mOut.getPayload()));
		mOut = channel.receive(10000);
		assertNotNull(mOut);
		assertEquals("Reply2", new String((byte[]) mOut.getPayload()));
		done.set(true);
		ccf.stop();
	}

	@Test
	public void testNioStxEtx() throws Exception {
		final int port = SocketUtils.findAvailableServerSocket();
		final CountDownLatch latch = new CountDownLatch(1);
		final AtomicBoolean done = new AtomicBoolean();
		Executors.newSingleThreadExecutor().execute(new Runnable() {
			@Override
			public void run() {
				try {
					ServerSocket server = ServerSocketFactory.getDefault().createServerSocket(port);
					latch.countDown();
					Socket socket = server.accept();
					int i = 0;
					while (true) {
						byte[] b = new byte[6];
						readFully(socket.getInputStream(), b);
						b = ("\u0002Reply" + (++i) + "\u0003").getBytes();
						socket.getOutputStream().write(b);
					}
				} catch (Exception e) {
					if (!done.get()) {
						e.printStackTrace();
					}
				}
			}
		});
		AbstractConnectionFactory ccf = new TcpNioClientConnectionFactory("localhost", port);
		noopPublisher(ccf);
		ByteArrayStxEtxSerializer serializer = new ByteArrayStxEtxSerializer();
		ccf.setSerializer(serializer);
		ccf.setDeserializer(serializer);
		ccf.setSoTimeout(10000);
		ccf.start();
		TcpSendingMessageHandler handler = new TcpSendingMessageHandler();
		handler.setConnectionFactory(ccf);
		TcpReceivingChannelAdapter adapter = new TcpReceivingChannelAdapter();
		adapter.setConnectionFactory(ccf);
		QueueChannel channel = new QueueChannel();
		adapter.setOutputChannel(channel);
		assertTrue(latch.await(10, TimeUnit.SECONDS));
		handler.handleMessage(MessageBuilder.withPayload("Test").build());
		handler.handleMessage(MessageBuilder.withPayload("Test").build());
		Set<String> results = new HashSet<String>();
		Message<?> mOut = channel.receive(10000);
		assertNotNull(mOut);
		results.add(new String((byte[]) mOut.getPayload()));
		mOut = channel.receive(10000);
		assertNotNull(mOut);
		results.add(new String((byte[]) mOut.getPayload()));
		assertTrue(results.remove("Reply1"));
		assertTrue(results.remove("Reply2"));
		done.set(true);
		ccf.stop();
	}

	@Test
	public void testNetLength() throws Exception {
		final int port = SocketUtils.findAvailableServerSocket();
		final CountDownLatch latch = new CountDownLatch(1);
		final AtomicBoolean done = new AtomicBoolean();
		Executors.newSingleThreadExecutor().execute(new Runnable() {
			@Override
			public void run() {
				try {
					ServerSocket server = ServerSocketFactory.getDefault().createServerSocket(port);
					latch.countDown();
					Socket socket = server.accept();
					int i = 0;
					while (true) {
						byte[] b = new byte[8];
						readFully(socket.getInputStream(), b);
						if (!"\u0000\u0000\u0000\u0004Test".equals(new String(b))) {
							throw new RuntimeException("Bad Data");
						}
						b = ("\u0000\u0000\u0000\u0006Reply" + (++i)).getBytes();
						socket.getOutputStream().write(b);
					}
				} catch (Exception e) {
					if (!done.get()) {
						e.printStackTrace();
					}
				}
			}
		});
		AbstractConnectionFactory ccf = new TcpNetClientConnectionFactory("localhost", port);
		noopPublisher(ccf);
		ByteArrayLengthHeaderSerializer serializer = new ByteArrayLengthHeaderSerializer();
		ccf.setSerializer(serializer);
		ccf.setDeserializer(serializer);
		ccf.setSoTimeout(10000);
		ccf.start();
		TcpSendingMessageHandler handler = new TcpSendingMessageHandler();
		handler.setConnectionFactory(ccf);
		TcpReceivingChannelAdapter adapter = new TcpReceivingChannelAdapter();
		adapter.setConnectionFactory(ccf);
		QueueChannel channel = new QueueChannel();
		adapter.setOutputChannel(channel);
		assertTrue(latch.await(10, TimeUnit.SECONDS));
		handler.handleMessage(MessageBuilder.withPayload("Test").build());
		handler.handleMessage(MessageBuilder.withPayload("Test").build());
		Message<?> mOut = channel.receive(10000);
		assertNotNull(mOut);
		assertEquals("Reply1", new String((byte[]) mOut.getPayload()));
		mOut = channel.receive(10000);
		assertNotNull(mOut);
		assertEquals("Reply2", new String((byte[]) mOut.getPayload()));
		done.set(true);
		ccf.stop();
	}

	@Test
	public void testNioLength() throws Exception {
		final int port = SocketUtils.findAvailableServerSocket();
		final CountDownLatch latch = new CountDownLatch(1);
		final AtomicBoolean done = new AtomicBoolean();
		Executors.newSingleThreadExecutor().execute(new Runnable() {
			@Override
			public void run() {
				try {
					ServerSocket server = ServerSocketFactory.getDefault().createServerSocket(port);
					latch.countDown();
					Socket socket = server.accept();
					int i = 0;
					while (true) {
						byte[] b = new byte[8];
						readFully(socket.getInputStream(), b);
						if (!"\u0000\u0000\u0000\u0004Test".equals(new String(b))) {
							throw new RuntimeException("Bad Data");
						}
						b = ("\u0000\u0000\u0000\u0006Reply" + (++i)).getBytes();
						socket.getOutputStream().write(b);
					}
				} catch (Exception e) {
					if (!done.get()) {
						e.printStackTrace();
					}
				}
			}
		});
		AbstractConnectionFactory ccf = new TcpNioClientConnectionFactory("localhost", port);
		noopPublisher(ccf);
		ByteArrayLengthHeaderSerializer serializer = new ByteArrayLengthHeaderSerializer();
		ccf.setSerializer(serializer);
		ccf.setDeserializer(serializer);
		ccf.setSoTimeout(10000);
		ccf.start();
		TcpSendingMessageHandler handler = new TcpSendingMessageHandler();
		handler.setConnectionFactory(ccf);
		TcpReceivingChannelAdapter adapter = new TcpReceivingChannelAdapter();
		adapter.setConnectionFactory(ccf);
		QueueChannel channel = new QueueChannel();
		adapter.setOutputChannel(channel);
		assertTrue(latch.await(10, TimeUnit.SECONDS));
		handler.handleMessage(MessageBuilder.withPayload("Test").build());
		handler.handleMessage(MessageBuilder.withPayload("Test").build());
		Set<String> results = new HashSet<String>();
		Message<?> mOut = channel.receive(10000);
		assertNotNull(mOut);
		results.add(new String((byte[]) mOut.getPayload()));
		mOut = channel.receive(10000);
		assertNotNull(mOut);
		results.add(new String((byte[]) mOut.getPayload()));
		assertTrue(results.remove("Reply1"));
		assertTrue(results.remove("Reply2"));
		done.set(true);
		ccf.stop();
	}

	@Test
	public void testNetSerial() throws Exception {
		final int port = SocketUtils.findAvailableServerSocket();
		final CountDownLatch latch = new CountDownLatch(1);
		final AtomicBoolean done = new AtomicBoolean();
		Executors.newSingleThreadExecutor().execute(new Runnable() {
			@Override
			public void run() {
				try {
					ServerSocket server = ServerSocketFactory.getDefault().createServerSocket(port);
					latch.countDown();
					Socket socket = server.accept();
					int i = 0;
					while (true) {
						ObjectInputStream ois = new ObjectInputStream(socket.getInputStream());
						ois.readObject();
						ObjectOutputStream oos = new ObjectOutputStream(socket.getOutputStream());
						oos.writeObject("Reply" + (++i));
					}
				} catch (Exception e) {
					if (!done.get()) {
						e.printStackTrace();
					}
				}
			}
		});
		AbstractConnectionFactory ccf = new TcpNetClientConnectionFactory("localhost", port);
		noopPublisher(ccf);
		ccf.setSerializer(new DefaultSerializer());
		ccf.setDeserializer(new DefaultDeserializer());
		ccf.setSoTimeout(10000);
		ccf.start();
		TcpSendingMessageHandler handler = new TcpSendingMessageHandler();
		handler.setConnectionFactory(ccf);
		TcpReceivingChannelAdapter adapter = new TcpReceivingChannelAdapter();
		adapter.setConnectionFactory(ccf);
		QueueChannel channel = new QueueChannel();
		adapter.setOutputChannel(channel);
		assertTrue(latch.await(10, TimeUnit.SECONDS));
		handler.handleMessage(MessageBuilder.withPayload("Test").build());
		handler.handleMessage(MessageBuilder.withPayload("Test").build());
		Message<?> mOut = channel.receive(10000);
		assertNotNull(mOut);
		assertEquals("Reply1", mOut.getPayload());
		mOut = channel.receive(10000);
		assertNotNull(mOut);
		assertEquals("Reply2", mOut.getPayload());
		done.set(true);
		ccf.stop();
	}

	@Test
	public void testNioSerial() throws Exception {
		final int port = SocketUtils.findAvailableServerSocket();
		final CountDownLatch latch = new CountDownLatch(1);
		final AtomicBoolean done = new AtomicBoolean();
		Executors.newSingleThreadExecutor().execute(new Runnable() {
			@Override
			public void run() {
				try {
					ServerSocket server = ServerSocketFactory.getDefault().createServerSocket(port);
					latch.countDown();
					Socket socket = server.accept();
					int i = 0;
					while (true) {
						ObjectInputStream ois = new ObjectInputStream(socket.getInputStream());
						ois.readObject();
						ObjectOutputStream oos = new ObjectOutputStream(socket.getOutputStream());
						oos.writeObject("Reply" + (++i));
					}
				} catch (Exception e) {
					if (!done.get()) {
						e.printStackTrace();
					}
				}
			}
		});
		AbstractConnectionFactory ccf = new TcpNioClientConnectionFactory("localhost", port);
		noopPublisher(ccf);
		ccf.setSerializer(new DefaultSerializer());
		ccf.setDeserializer(new DefaultDeserializer());
		ccf.setSoTimeout(10000);
		ccf.start();
		TcpSendingMessageHandler handler = new TcpSendingMessageHandler();
		handler.setConnectionFactory(ccf);
		TcpReceivingChannelAdapter adapter = new TcpReceivingChannelAdapter();
		adapter.setConnectionFactory(ccf);
		QueueChannel channel = new QueueChannel();
		adapter.setOutputChannel(channel);
		assertTrue(latch.await(10, TimeUnit.SECONDS));
		handler.handleMessage(MessageBuilder.withPayload("Test").build());
		handler.handleMessage(MessageBuilder.withPayload("Test").build());
		Set<String> results = new HashSet<String>();
		Message<?> mOut = channel.receive(10000);
		assertNotNull(mOut);
		results.add((String) mOut.getPayload());
		mOut = channel.receive(10000);
		assertNotNull(mOut);
		results.add((String) mOut.getPayload());
		assertTrue(results.remove("Reply1"));
		assertTrue(results.remove("Reply2"));
		done.set(true);
		ccf.stop();
	}

	@Test
	public void testNetSingleUseNoInbound() throws Exception  {
		final int port = SocketUtils.findAvailableServerSocket();
		final CountDownLatch latch = new CountDownLatch(1);
		final Semaphore semaphore = new Semaphore(0);
		final AtomicBoolean done = new AtomicBoolean();
		Executors.newSingleThreadExecutor().execute(new Runnable() {
			@Override
			public void run() {
				try {
					ServerSocket server = ServerSocketFactory.getDefault().createServerSocket(port);
					latch.countDown();
					for (int i = 0; i < 2; i++) {
						Socket socket = server.accept();
						semaphore.release();
						byte[] b = new byte[6];
						readFully(socket.getInputStream(), b);
						semaphore.release();
						socket.close();
					}
					server.close();
				} catch (Exception e) {
					if (!done.get()) {
						e.printStackTrace();
					}
				}
			}
		});
		AbstractConnectionFactory ccf = new TcpNetClientConnectionFactory("localhost", port);
		noopPublisher(ccf);
		ByteArrayCrLfSerializer serializer = new ByteArrayCrLfSerializer();
		ccf.setSerializer(serializer);
		ccf.setDeserializer(serializer);
		ccf.setSoTimeout(10000);
		ccf.start();
		ccf.setSingleUse(true);
		TcpSendingMessageHandler handler = new TcpSendingMessageHandler();
		handler.setConnectionFactory(ccf);
		assertTrue(latch.await(10, TimeUnit.SECONDS));
		handler.handleMessage(MessageBuilder.withPayload("Test").build());
		handler.handleMessage(MessageBuilder.withPayload("Test").build());
		assertTrue(semaphore.tryAcquire(4, 10000, TimeUnit.MILLISECONDS));
		done.set(true);
		ccf.stop();
	}

	@Test
	public void testNioSingleUseNoInbound() throws Exception  {
		final int port = SocketUtils.findAvailableServerSocket();
		final CountDownLatch latch = new CountDownLatch(1);
		final Semaphore semaphore = new Semaphore(0);
		final AtomicBoolean done = new AtomicBoolean();
		Executors.newSingleThreadExecutor().execute(new Runnable() {
			@Override
			public void run() {
				try {
					ServerSocket server = ServerSocketFactory.getDefault().createServerSocket(port);
					latch.countDown();
					for (int i = 0; i < 2; i++) {
						Socket socket = server.accept();
						semaphore.release();
						byte[] b = new byte[8];
						readFully(socket.getInputStream(), b);
						semaphore.release();
						socket.close();
					}
					server.close();
				} catch (Exception e) {
					if (!done.get()) {
						e.printStackTrace();
					}
				}
			}
		});
		AbstractConnectionFactory ccf = new TcpNioClientConnectionFactory("localhost", port);
		noopPublisher(ccf);
		ByteArrayCrLfSerializer serializer = new ByteArrayCrLfSerializer();
		ccf.setSerializer(serializer);
		ccf.setDeserializer(serializer);
		ccf.setSoTimeout(5000);
		ccf.start();
		ccf.setSingleUse(true);
		TcpSendingMessageHandler handler = new TcpSendingMessageHandler();
		handler.setConnectionFactory(ccf);
		assertTrue(latch.await(10, TimeUnit.SECONDS));
		handler.handleMessage(MessageBuilder.withPayload("Test.1").build());
		handler.handleMessage(MessageBuilder.withPayload("Test.2").build());
		assertTrue(semaphore.tryAcquire(4, 10000, TimeUnit.MILLISECONDS));
		done.set(true);
		ccf.stop();
	}

	@Test
	public void testNetSingleUseWithInbound() throws Exception  {
		final int port = SocketUtils.findAvailableServerSocket();
		final CountDownLatch latch = new CountDownLatch(1);
		final Semaphore semaphore = new Semaphore(0);
		final AtomicBoolean done = new AtomicBoolean();
		Executors.newSingleThreadExecutor().execute(new Runnable() {
			@Override
			public void run() {
				try {
					ServerSocket server = ServerSocketFactory.getDefault().createServerSocket(port);
					latch.countDown();
					for (int i = 1; i < 3; i++) {
						Socket socket = server.accept();
						semaphore.release();
						byte[] b = new byte[6];
						readFully(socket.getInputStream(), b);
						b = ("Reply" + i + "\r\n").getBytes();
						socket.getOutputStream().write(b);
						socket.close();
					}
					server.close();
				} catch (Exception e) {
					if (!done.get()) {
						e.printStackTrace();
					}
				}
			}
		});
		AbstractConnectionFactory ccf = new TcpNetClientConnectionFactory("localhost", port);
		noopPublisher(ccf);
		ByteArrayCrLfSerializer serializer = new ByteArrayCrLfSerializer();
		ccf.setSerializer(serializer);
		ccf.setDeserializer(serializer);
		ccf.setSoTimeout(10000);
		ccf.start();
		ccf.setSingleUse(true);
		TcpSendingMessageHandler handler = new TcpSendingMessageHandler();
		handler.setConnectionFactory(ccf);
		TcpReceivingChannelAdapter adapter = new TcpReceivingChannelAdapter();
		adapter.setConnectionFactory(ccf);
		QueueChannel channel = new QueueChannel();
		adapter.setOutputChannel(channel);
		assertTrue(latch.await(10, TimeUnit.SECONDS));
		handler.handleMessage(MessageBuilder.withPayload("Test").build());
		handler.handleMessage(MessageBuilder.withPayload("Test").build());
		assertTrue(semaphore.tryAcquire(2, 10000, TimeUnit.MILLISECONDS));
		Set<String> replies = new HashSet<String>();
		for (int i = 0; i < 2; i++) {
			Message<?> mOut = channel.receive(10000);
			assertNotNull(mOut);
			replies.add(new String((byte[])mOut.getPayload()));
		}
		assertTrue(replies.remove("Reply1"));
		assertTrue(replies.remove("Reply2"));
		done.set(true);
		ccf.stop();
	}

	@Test
	public void testNioSingleUseWithInbound() throws Exception  {
		final int port = SocketUtils.findAvailableServerSocket();
		final CountDownLatch latch = new CountDownLatch(1);
		final Semaphore semaphore = new Semaphore(0);
		final AtomicBoolean done = new AtomicBoolean();
		Executors.newSingleThreadExecutor().execute(new Runnable() {
			@Override
			public void run() {
				try {
					ServerSocket server = ServerSocketFactory.getDefault().createServerSocket(port);
					latch.countDown();
					for (int i = 1; i < 3; i++) {
						Socket socket = server.accept();
						semaphore.release();
						byte[] b = new byte[6];
						readFully(socket.getInputStream(), b);
						b = ("Reply" + i + "\r\n").getBytes();
						socket.getOutputStream().write(b);
						socket.close();
					}
					server.close();
				} catch (Exception e) {
					if (!done.get()) {
						e.printStackTrace();
					}
				}
			}
		});
		AbstractConnectionFactory ccf = new TcpNioClientConnectionFactory("localhost", port);
		noopPublisher(ccf);
		ByteArrayCrLfSerializer serializer = new ByteArrayCrLfSerializer();
		ccf.setSerializer(serializer);
		ccf.setDeserializer(serializer);
		ccf.setSoTimeout(10000);
		ccf.start();
		ccf.setSingleUse(true);
		TcpSendingMessageHandler handler = new TcpSendingMessageHandler();
		handler.setConnectionFactory(ccf);
		TcpReceivingChannelAdapter adapter = new TcpReceivingChannelAdapter();
		adapter.setConnectionFactory(ccf);
		QueueChannel channel = new QueueChannel();
		adapter.setOutputChannel(channel);
		assertTrue(latch.await(10, TimeUnit.SECONDS));
		handler.handleMessage(MessageBuilder.withPayload("Test").build());
		handler.handleMessage(MessageBuilder.withPayload("Test").build());
		assertTrue(semaphore.tryAcquire(2, 10000, TimeUnit.MILLISECONDS));
		Set<String> replies = new HashSet<String>();
		for (int i = 0; i < 2; i++) {
			Message<?> mOut = channel.receive(10000);
			assertNotNull(mOut);
			replies.add(new String((byte[])mOut.getPayload()));
		}
		assertTrue(replies.remove("Reply1"));
		assertTrue(replies.remove("Reply2"));
		done.set(true);
		ccf.stop();
	}

	@Test
	public void testNioSingleUseWithInboundMany() throws Exception  {
		final int port = SocketUtils.findAvailableServerSocket();
		final CountDownLatch latch = new CountDownLatch(1);
		final Semaphore semaphore = new Semaphore(0);
		final AtomicBoolean done = new AtomicBoolean();
		final List<Socket> serverSockets = new ArrayList<Socket>();
		final ExecutorService exec = Executors.newCachedThreadPool();
		exec.execute(new Runnable() {
			@Override
			public void run() {
				try {
					ServerSocket server = ServerSocketFactory.getDefault().createServerSocket(port, 100);
					latch.countDown();
					for (int i = 0; i < 100; i++) {
						final Socket socket = server.accept();
						serverSockets.add(socket);
						final int j = i;
						exec.execute(new Runnable() {

							@Override
							public void run() {
								semaphore.release();
								byte[] b = new byte[9];
								try {
									readFully(socket.getInputStream(), b);
									b = ("Reply" + j + "\r\n").getBytes();
									socket.getOutputStream().write(b);
								}
								catch (IOException e) {
									e.printStackTrace();
								}
								finally {
									try {
										socket.close();
									}
									catch (IOException e) { }
								}
							}
						});
					}
					server.close();
				} catch (Exception e) {
					if (!done.get()) {
						e.printStackTrace();
					}
				}
			}
		});
		AbstractConnectionFactory ccf = new TcpNioClientConnectionFactory("localhost", port);
		noopPublisher(ccf);
		ByteArrayCrLfSerializer serializer = new ByteArrayCrLfSerializer();
		ccf.setSerializer(serializer);
		ccf.setDeserializer(serializer);
		ccf.setSoTimeout(10000);
		ccf.setSingleUse(true);
		ccf.setTaskExecutor(Executors.newCachedThreadPool());
		ccf.start();
		TcpSendingMessageHandler handler = new TcpSendingMessageHandler();
		handler.setConnectionFactory(ccf);
		TcpReceivingChannelAdapter adapter = new TcpReceivingChannelAdapter();
		adapter.setConnectionFactory(ccf);
		QueueChannel channel = new QueueChannel();
		adapter.setOutputChannel(channel);
		assertTrue(latch.await(10, TimeUnit.SECONDS));
		int i = 0;
		try {
			for (i = 100; i < 200; i++) {
				handler.handleMessage(MessageBuilder.withPayload("Test" + i).build());
			}
		} catch (Exception e) {
			e.printStackTrace();
			fail("Exception at " + i);
		}
		assertTrue(semaphore.tryAcquire(100, 20000, TimeUnit.MILLISECONDS));
		Set<String> replies = new HashSet<String>();
		for (i = 100; i < 200; i++) {
			Message<?> mOut = channel.receive(20000);
			assertNotNull(mOut);
			replies.add(new String((byte[])mOut.getPayload()));
		}
		for (i = 0; i < 100; i++) {
			assertTrue("Reply" + i + " missing", replies.remove("Reply" + i));
		}
		done.set(true);
		ccf.stop();
	}

	@Test
	public void testNetNegotiate() throws Exception {
		final int port = SocketUtils.findAvailableServerSocket();
		final CountDownLatch latch = new CountDownLatch(1);
		final AtomicBoolean done = new AtomicBoolean();
		Executors.newSingleThreadExecutor().execute(new Runnable() {
			@Override
			public void run() {
				try {
					ServerSocket server = ServerSocketFactory.getDefault().createServerSocket(port);
					latch.countDown();
					Socket socket = server.accept();
					int i = 0;
					while (true) {
						ObjectInputStream ois = new ObjectInputStream(socket.getInputStream());
						Object in = null;
						ObjectOutputStream oos = new ObjectOutputStream(socket.getOutputStream());
						if (i == 0) {
							in = ois.readObject();
							logger.debug("read object: " + in);
							oos.writeObject("world!");
							ois = new ObjectInputStream(socket.getInputStream());
							oos = new ObjectOutputStream(socket.getOutputStream());
							in = ois.readObject();
							logger.debug("read object: " + in);
							oos.writeObject("world!");
							ois = new ObjectInputStream(socket.getInputStream());
							oos = new ObjectOutputStream(socket.getOutputStream());
						}
						in = ois.readObject();
						oos.writeObject("Reply" + (++i));
					}
				}
				catch (Exception e) {
					if (!done.get()) {
						e.printStackTrace();
					}
				}
			}
		});
		AbstractConnectionFactory ccf = new TcpNetClientConnectionFactory("localhost", port);
		noopPublisher(ccf);
		ccf.setSerializer(new DefaultSerializer());
		ccf.setDeserializer(new DefaultDeserializer());
		ccf.setSoTimeout(10000);
		TcpConnectionInterceptorFactoryChain fc = new TcpConnectionInterceptorFactoryChain();
		fc.setInterceptors(new TcpConnectionInterceptorFactory[] {
				newInterceptorFactory(),
				newInterceptorFactory()
		});
		ccf.setInterceptorFactoryChain(fc);
		ccf.start();
		TcpSendingMessageHandler handler = new TcpSendingMessageHandler();
		handler.setConnectionFactory(ccf);
		TcpReceivingChannelAdapter adapter = new TcpReceivingChannelAdapter();
		adapter.setConnectionFactory(ccf);
		QueueChannel channel = new QueueChannel();
		adapter.setOutputChannel(channel);
		assertTrue(latch.await(10, TimeUnit.SECONDS));
		handler.handleMessage(MessageBuilder.withPayload("Test").build());
		handler.handleMessage(MessageBuilder.withPayload("Test").build());
		Message<?> mOut = channel.receive(10000);
		assertNotNull(mOut);
		assertEquals("Reply1", mOut.getPayload());
		mOut = channel.receive(10000);
		assertNotNull(mOut);
		assertEquals("Reply2", mOut.getPayload());
		done.set(true);
		ccf.stop();
	}

	@Test
	public void testNioNegotiate() throws Exception {
		final int port = SocketUtils.findAvailableServerSocket();
		final CountDownLatch latch = new CountDownLatch(1);
		final AtomicBoolean done = new AtomicBoolean();
		Executors.newSingleThreadExecutor().execute(new Runnable() {
			@Override
			public void run() {
				try {
					ServerSocket server = ServerSocketFactory.getDefault().createServerSocket(port);
					latch.countDown();
					Socket socket = server.accept();
					int i = 100;
					while (true) {
						ObjectInputStream ois = new ObjectInputStream(socket.getInputStream());
						Object in;
						ObjectOutputStream oos = new ObjectOutputStream(socket.getOutputStream());
						if (i == 100) {
							in = ois.readObject();
							logger.debug("read object: " + in);
							oos.writeObject("world!");
							ois = new ObjectInputStream(socket.getInputStream());
							oos = new ObjectOutputStream(socket.getOutputStream());
							Thread.sleep(500);
						}
						in = ois.readObject();
						oos.writeObject("Reply" + (i++));
					}
				} catch (Exception e) {
					if (!done.get()) {
						e.printStackTrace();
					}
				}
			}
		});
		AbstractConnectionFactory ccf = new TcpNioClientConnectionFactory("localhost", port);
		noopPublisher(ccf);
		ccf.setSerializer(new DefaultSerializer());
		ccf.setDeserializer(new DefaultDeserializer());
		ccf.setSoTimeout(10000);
		TcpConnectionInterceptorFactoryChain fc = new TcpConnectionInterceptorFactoryChain();
		fc.setInterceptors(new TcpConnectionInterceptorFactory[] {newInterceptorFactory()});
		ccf.setInterceptorFactoryChain(fc);
		ccf.start();
		TcpSendingMessageHandler handler = new TcpSendingMessageHandler();
		handler.setConnectionFactory(ccf);
		TcpReceivingChannelAdapter adapter = new TcpReceivingChannelAdapter();
		adapter.setConnectionFactory(ccf);
		QueueChannel channel = new QueueChannel();
		adapter.setOutputChannel(channel);
		assertTrue(latch.await(10, TimeUnit.SECONDS));
		for (int i = 0; i < 1000; i++) {
			handler.handleMessage(MessageBuilder.withPayload("Test").build());
		}
		Set<String> results = new TreeSet<String>();
		for (int i = 0; i < 1000; i++) {
			Message<?> mOut = channel.receive(10000);
			assertNotNull(mOut);
			results.add((String) mOut.getPayload());
		}
		logger.debug("results: " + results);
		for (int i = 100; i < 1100; i++) {
			assertTrue("Missing Reply" + i, results.remove("Reply" + i));
		}
		done.set(true);
		ccf.stop();
	}

	@Test
	public void testNetNegotiateSingleNoListen() throws Exception {
		final int port = SocketUtils.findAvailableServerSocket();
		final CountDownLatch latch = new CountDownLatch(1);
		final AtomicBoolean done = new AtomicBoolean();
		Executors.newSingleThreadExecutor().execute(new Runnable() {
			@Override
			public void run() {
				try {
					ServerSocket server = ServerSocketFactory.getDefault().createServerSocket(port);
					latch.countDown();
					Socket socket = server.accept();
					int i = 0;
					ObjectInputStream ois = new ObjectInputStream(socket.getInputStream());
					Object in = null;
					ObjectOutputStream oos = new ObjectOutputStream(socket.getOutputStream());
					if (i == 0) {
						in = ois.readObject();
						logger.debug("read object: " + in);
						oos.writeObject("world!");
						ois = new ObjectInputStream(socket.getInputStream());
						oos = new ObjectOutputStream(socket.getOutputStream());
						in = ois.readObject();
						logger.debug("read object: " + in);
						oos.writeObject("world!");
						ois = new ObjectInputStream(socket.getInputStream());
						oos = new ObjectOutputStream(socket.getOutputStream());
					}
					in = ois.readObject();
					oos.writeObject("Reply" + (++i));
					socket.close();
					server.close();
				}
				catch (Exception e) {
					if (!done.get()) {
						e.printStackTrace();
					}
				}
			}
		});
		AbstractConnectionFactory ccf = new TcpNetClientConnectionFactory("localhost", port);
		noopPublisher(ccf);
		ccf.setSerializer(new DefaultSerializer());
		ccf.setDeserializer(new DefaultDeserializer());
		ccf.setSoTimeout(10000);
		TcpConnectionInterceptorFactoryChain fc = new TcpConnectionInterceptorFactoryChain();
		fc.setInterceptors(new TcpConnectionInterceptorFactory[] {
				newInterceptorFactory(),
				newInterceptorFactory()
		});
		ccf.setInterceptorFactoryChain(fc);
		ccf.setSingleUse(true);
		ccf.start();
		TcpSendingMessageHandler handler = new TcpSendingMessageHandler();
		handler.setConnectionFactory(ccf);
		assertTrue(latch.await(10, TimeUnit.SECONDS));
		handler.handleMessage(MessageBuilder.withPayload("Test").build());
		done.set(true);
		ccf.stop();
	}

	@Test
	public void testNioNegotiateSingleNoListen() throws Exception {
		final int port = SocketUtils.findAvailableServerSocket();
		final CountDownLatch latch = new CountDownLatch(1);
		final AtomicBoolean done = new AtomicBoolean();
		Executors.newSingleThreadExecutor().execute(new Runnable() {
			@Override
			public void run() {
				int i = 0;
				try {
					ServerSocket server = ServerSocketFactory.getDefault().createServerSocket(port);
					latch.countDown();
					Socket socket = server.accept();
					ObjectInputStream ois = new ObjectInputStream(socket.getInputStream());
					Object in = null;
					ObjectOutputStream oos = new ObjectOutputStream(socket.getOutputStream());
					if (i == 0) {
						in = ois.readObject();
						logger.debug("read object: " + in);
						oos.writeObject("world!");
						ois = new ObjectInputStream(socket.getInputStream());
						oos = new ObjectOutputStream(socket.getOutputStream());
						in = ois.readObject();
						logger.debug("read object: " + in);
						oos.writeObject("world!");
						ois = new ObjectInputStream(socket.getInputStream());
						oos = new ObjectOutputStream(socket.getOutputStream());
					}
					in = ois.readObject();
					oos.writeObject("Reply" + (++i));
					socket.close();
					server.close();
				} catch (Exception e) {
					if (i == 0) {
						e.printStackTrace();
					}
				}
			}
		});
		AbstractConnectionFactory ccf = new TcpNioClientConnectionFactory("localhost", port);
		noopPublisher(ccf);
		ccf.setSerializer(new DefaultSerializer());
		ccf.setDeserializer(new DefaultDeserializer());
		ccf.setSoTimeout(10000);
		TcpConnectionInterceptorFactoryChain fc = new TcpConnectionInterceptorFactoryChain();
		fc.setInterceptors(new TcpConnectionInterceptorFactory[] {
				newInterceptorFactory(),
				newInterceptorFactory()
		});
		ccf.setInterceptorFactoryChain(fc);
		ccf.setSingleUse(true);
		ccf.start();
		TcpSendingMessageHandler handler = new TcpSendingMessageHandler();
		handler.setConnectionFactory(ccf);
		assertTrue(latch.await(10, TimeUnit.SECONDS));
		handler.handleMessage(MessageBuilder.withPayload("Test").build());
		done.set(true);
		ccf.stop();
	}

	@Test
	public void testOutboundChannelAdapterWithinChain() throws Exception {
		AbstractApplicationContext ctx = new ClassPathXmlApplicationContext(
				"TcpOutboundChannelAdapterWithinChainTests-context.xml", this.getClass());
		AbstractServerConnectionFactory scf = ctx.getBean(AbstractServerConnectionFactory.class);
		TestingUtilities.waitListening(scf, null);
		MessageChannel channelAdapterWithinChain = ctx.getBean("tcpOutboundChannelAdapterWithinChain", MessageChannel.class);
		PollableChannel inbound = ctx.getBean("inbound", PollableChannel.class);
		String testPayload = "Hello, world!";
		channelAdapterWithinChain.send(new GenericMessage<String>(testPayload));
		Message<?> m = inbound.receive(1000);
		assertNotNull(m);
		assertEquals(testPayload, new String((byte[]) m.getPayload()));
		ctx.destroy();
	}

	@Test
	public void testConnectionException() throws Exception {
		TcpSendingMessageHandler handler = new TcpSendingMessageHandler();
		AbstractConnectionFactory mockCcf = mock(AbstractClientConnectionFactory.class);
		Mockito.doAnswer(new Answer<Object>() {

			@Override
			public Object answer(InvocationOnMock invocation) throws Throwable {
				throw new SocketException("Failed to connect");
			}
		}).when(mockCcf).getConnection();
		handler.setConnectionFactory(mockCcf);
		try {
			handler.handleMessage(new GenericMessage<String>("foo"));
			fail("Expected exception");
		}
		catch (Exception e) {
			assertTrue(e instanceof MessagingException);
			assertTrue(e.getCause() != null);
			assertTrue(e.getCause() instanceof SocketException);
			assertEquals("Failed to connect", e.getCause().getMessage());
		}
	}
}


File: spring-integration-ip/src/test/java/org/springframework/integration/ip/tcp/TcpSendingNoSocketTests.java
/*
 * Copyright 2002-2012 the original author or authors.
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
package org.springframework.integration.ip.tcp;

import static org.junit.Assert.assertEquals;
import static org.junit.Assert.fail;

import org.junit.Test;
import org.junit.runner.RunWith;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.messaging.MessageChannel;
import org.springframework.messaging.MessageHandlingException;
import org.springframework.messaging.support.GenericMessage;
import org.springframework.test.context.ContextConfiguration;
import org.springframework.test.context.junit4.SpringJUnit4ClassRunner;

/**
 * @author Gary Russell
 * @since 2.2
 *
 */
@ContextConfiguration
@RunWith(SpringJUnit4ClassRunner.class)
public class TcpSendingNoSocketTests {

	@Autowired
	private MessageChannel shouldFail;

	@Autowired
	private MessageChannel advised;

	@Test
	public void exceptionExpected() {
		try {
			shouldFail.send(new GenericMessage<String>("foo"));
			fail("Exception expected");
		}
		catch (MessageHandlingException e) {
			assertEquals("Unable to find outbound socket", e.getMessage());
		}
	}

	@Test
	public void exceptionTrapped() {
		advised.send(new GenericMessage<String>("foo"));
	}
}


File: spring-integration-ip/src/test/java/org/springframework/integration/ip/tcp/connection/CachingClientConnectionFactoryTests.java
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

package org.springframework.integration.ip.tcp.connection;

import static org.hamcrest.Matchers.startsWith;
import static org.junit.Assert.assertEquals;
import static org.junit.Assert.assertFalse;
import static org.junit.Assert.assertNotNull;
import static org.junit.Assert.assertNotSame;
import static org.junit.Assert.assertSame;
import static org.junit.Assert.assertThat;
import static org.junit.Assert.assertTrue;
import static org.junit.Assert.fail;
import static org.mockito.Matchers.any;
import static org.mockito.Matchers.anyInt;
import static org.mockito.Matchers.anyString;
import static org.mockito.Mockito.doAnswer;
import static org.mockito.Mockito.doThrow;
import static org.mockito.Mockito.mock;
import static org.mockito.Mockito.never;
import static org.mockito.Mockito.spy;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.when;

import java.io.ByteArrayInputStream;
import java.io.IOException;
import java.io.OutputStream;
import java.net.Socket;
import java.nio.ByteBuffer;
import java.nio.channels.SocketChannel;
import java.util.ArrayList;
import java.util.List;
import java.util.concurrent.BlockingQueue;
import java.util.concurrent.CountDownLatch;
import java.util.concurrent.Executors;
import java.util.concurrent.Semaphore;
import java.util.concurrent.TimeUnit;
import java.util.concurrent.atomic.AtomicBoolean;
import java.util.concurrent.atomic.AtomicInteger;
import java.util.concurrent.atomic.AtomicReference;

import org.apache.commons.logging.Log;
import org.junit.Test;
import org.junit.runner.RunWith;
import org.mockito.ArgumentCaptor;
import org.mockito.Mockito;
import org.mockito.invocation.InvocationOnMock;
import org.mockito.stubbing.Answer;

import org.springframework.beans.DirectFieldAccessor;
import org.springframework.beans.factory.BeanFactory;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.beans.factory.annotation.Qualifier;
import org.springframework.context.ApplicationEvent;
import org.springframework.context.ApplicationEventPublisher;
import org.springframework.integration.channel.QueueChannel;
import org.springframework.integration.ip.IpHeaders;
import org.springframework.integration.ip.tcp.TcpOutboundGateway;
import org.springframework.integration.ip.tcp.TcpSendingMessageHandler;
import org.springframework.integration.ip.tcp.serializer.ByteArrayCrLfSerializer;
import org.springframework.integration.ip.util.TestingUtilities;
import org.springframework.integration.support.MessageBuilder;
import org.springframework.integration.test.util.TestUtils;
import org.springframework.messaging.Message;
import org.springframework.messaging.MessagingException;
import org.springframework.messaging.PollableChannel;
import org.springframework.messaging.SubscribableChannel;
import org.springframework.messaging.support.ErrorMessage;
import org.springframework.messaging.support.GenericMessage;
import org.springframework.test.annotation.DirtiesContext;
import org.springframework.test.annotation.DirtiesContext.ClassMode;
import org.springframework.test.context.ContextConfiguration;
import org.springframework.test.context.junit4.SpringJUnit4ClassRunner;
import org.springframework.util.SocketUtils;

/**
 * @author Gary Russell
 * @since 2.2
 *
 */
@ContextConfiguration
@RunWith(SpringJUnit4ClassRunner.class)
@DirtiesContext(classMode = ClassMode.AFTER_EACH_TEST_METHOD)
public class CachingClientConnectionFactoryTests {

	@Autowired
	SubscribableChannel outbound;

	@Autowired
	PollableChannel inbound;

	@Autowired
	AbstractServerConnectionFactory serverCf;

	@Autowired
	SubscribableChannel toGateway;

	@Autowired
	SubscribableChannel replies;

	@Autowired
	PollableChannel fromGateway;

	@Autowired
	@Qualifier("gateway.caching.ccf")
	CachingClientConnectionFactory gatewayCF;

	@Test
	public void testReuse() throws Exception {
		AbstractClientConnectionFactory factory = mock(AbstractClientConnectionFactory.class);
		when(factory.isRunning()).thenReturn(true);
		TcpConnectionSupport mockConn1 = makeMockConnection("conn1");
		TcpConnectionSupport mockConn2 = makeMockConnection("conn2");
		when(factory.getConnection()).thenReturn(mockConn1).thenReturn(mockConn2);
		CachingClientConnectionFactory cachingFactory = new CachingClientConnectionFactory(factory, 2);
		cachingFactory.start();
		TcpConnection conn1 = cachingFactory.getConnection();
		// INT-3652
		TcpConnectionInterceptorSupport cachedConn1 = (TcpConnectionInterceptorSupport) conn1;
		Log logger = spy(TestUtils.getPropertyValue(cachedConn1, "logger", Log.class));
		when(logger.isDebugEnabled()).thenReturn(true);
		new DirectFieldAccessor(cachedConn1).setPropertyValue("logger", logger);
		cachedConn1.onMessage(new ErrorMessage(new RuntimeException()));
		ArgumentCaptor<String> captor = ArgumentCaptor.forClass(String.class);
		verify(logger).debug(captor.capture());
		assertThat(captor.getValue(), startsWith("Message discarded; no listener:"));
		// end INT-3652
		assertEquals("Cached:" + mockConn1.toString(), conn1.toString());
		conn1.close();
		conn1 = cachingFactory.getConnection();
		assertEquals("Cached:" + mockConn1.toString(), conn1.toString());
		TcpConnection conn2 = cachingFactory.getConnection();
		assertEquals("Cached:" + mockConn2.toString(), conn2.toString());
		conn1.close();
		conn2.close();
	}

	@Test
	public void testReuseNoLimit() throws Exception {
		AbstractClientConnectionFactory factory = mock(AbstractClientConnectionFactory.class);
		when(factory.isRunning()).thenReturn(true);
		TcpConnectionSupport mockConn1 = makeMockConnection("conn1");
		TcpConnectionSupport mockConn2 = makeMockConnection("conn2");
		when(factory.getConnection()).thenReturn(mockConn1).thenReturn(mockConn2);
		CachingClientConnectionFactory cachingFactory = new CachingClientConnectionFactory(factory, 0);
		cachingFactory.start();
		TcpConnection conn1 = cachingFactory.getConnection();
		assertEquals("Cached:" + mockConn1.toString(), conn1.toString());
		conn1.close();
		conn1 = cachingFactory.getConnection();
		assertEquals("Cached:" + mockConn1.toString(), conn1.toString());
		TcpConnection conn2 = cachingFactory.getConnection();
		assertEquals("Cached:" + mockConn2.toString(), conn2.toString());
		conn1.close();
		conn2.close();
	}

	@Test
	public void testReuseClosed() throws Exception {
		AbstractClientConnectionFactory factory = mock(AbstractClientConnectionFactory.class);
		when(factory.isRunning()).thenReturn(true);
		TcpConnectionSupport mockConn1 = makeMockConnection("conn1");
		TcpConnectionSupport mockConn2 = makeMockConnection("conn2");
		doAnswer(new Answer<Object>() {

			@Override
			public Object answer(InvocationOnMock invocation) throws Throwable {
				return null;
			}

		}).when(mockConn1).close();
		when(factory.getConnection()).thenReturn(mockConn1)
				.thenReturn(mockConn2).thenReturn(mockConn1)
				.thenReturn(mockConn2);
		CachingClientConnectionFactory cachingFactory = new CachingClientConnectionFactory(factory, 2);
		cachingFactory.start();
		TcpConnection conn1 = cachingFactory.getConnection();
		assertEquals("Cached:" + mockConn1.toString(), conn1.toString());
		conn1.close();
		conn1 = cachingFactory.getConnection();
		assertEquals("Cached:" + mockConn1.toString(), conn1.toString());
		TcpConnection conn2 = cachingFactory.getConnection();
		assertEquals("Cached:" + mockConn2.toString(), conn2.toString());
		conn1.close();
		conn2.close();
		when(mockConn1.isOpen()).thenReturn(false);
		TcpConnection conn2a = cachingFactory.getConnection();
		assertEquals("Cached:" + mockConn2.toString(), conn2a.toString());
		assertSame(TestUtils.getPropertyValue(conn2, "theConnection"),
				TestUtils.getPropertyValue(conn2a, "theConnection"));
		conn2a.close();
	}

	@Test(expected = MessagingException.class)
	public void testLimit() throws Exception {
		AbstractClientConnectionFactory factory = mock(AbstractClientConnectionFactory.class);
		when(factory.isRunning()).thenReturn(true);
		TcpConnectionSupport mockConn1 = makeMockConnection("conn1");
		TcpConnectionSupport mockConn2 = makeMockConnection("conn2");
		when(factory.getConnection()).thenReturn(mockConn1).thenReturn(mockConn2);
		CachingClientConnectionFactory cachingFactory = new CachingClientConnectionFactory(factory, 2);
		cachingFactory.setConnectionWaitTimeout(10);
		cachingFactory.start();
		TcpConnection conn1 = cachingFactory.getConnection();
		assertEquals("Cached:" + mockConn1.toString(), conn1.toString());
		conn1.close();
		conn1 = cachingFactory.getConnection();
		assertEquals("Cached:" + mockConn1.toString(), conn1.toString());
		TcpConnection conn2 = cachingFactory.getConnection();
		assertEquals("Cached:" + mockConn2.toString(), conn2.toString());
		cachingFactory.getConnection();
	}

	@Test
	public void testStop() throws Exception {
		AbstractClientConnectionFactory factory = mock(AbstractClientConnectionFactory.class);
		when(factory.isRunning()).thenReturn(true);
		TcpConnectionSupport mockConn1 = makeMockConnection("conn1");
		TcpConnectionSupport mockConn2 = makeMockConnection("conn2");
		int i = 3;
		when(factory.getConnection()).thenReturn(mockConn1)
				.thenReturn(mockConn2)
				.thenReturn(makeMockConnection("conn" + (i++)));
		CachingClientConnectionFactory cachingFactory = new CachingClientConnectionFactory(factory, 2);
		cachingFactory.start();
		TcpConnection conn1 = cachingFactory.getConnection();
		assertEquals("Cached:" + mockConn1.toString(), conn1.toString());
		conn1.close();
		conn1 = cachingFactory.getConnection();
		assertEquals("Cached:" + mockConn1.toString(), conn1.toString());
		TcpConnection conn2 = cachingFactory.getConnection();
		assertEquals("Cached:" + mockConn2.toString(), conn2.toString());
		cachingFactory.stop();
		Answer<Object> answer = new Answer<Object>() {

			@Override
			public Object answer(InvocationOnMock invocation) throws Throwable {
				return null;
			}

		};
		doAnswer(answer).when(mockConn1).close();
		doAnswer(answer).when(mockConn2).close();
		when(factory.isRunning()).thenReturn(false);
		conn1.close();
		conn2.close();
		verify(mockConn1).close();
		verify(mockConn2).close();
		when(mockConn1.isOpen()).thenReturn(false);
		when(mockConn2.isOpen()).thenReturn(false);
		when(factory.isRunning()).thenReturn(true);
		TcpConnection conn3 = cachingFactory.getConnection();
		assertNotSame(TestUtils.getPropertyValue(conn1, "theConnection"),
				TestUtils.getPropertyValue(conn3, "theConnection"));
		assertNotSame(TestUtils.getPropertyValue(conn2, "theConnection"),
				TestUtils.getPropertyValue(conn3, "theConnection"));
	}

	@Test
	public void testEnlargePool() throws Exception {
		AbstractClientConnectionFactory factory = mock(AbstractClientConnectionFactory.class);
		when(factory.isRunning()).thenReturn(true);
		TcpConnectionSupport mockConn1 = makeMockConnection("conn1");
		TcpConnectionSupport mockConn2 = makeMockConnection("conn2");
		TcpConnectionSupport mockConn3 = makeMockConnection("conn3");
		TcpConnectionSupport mockConn4 = makeMockConnection("conn4");
		when(factory.getConnection()).thenReturn(mockConn1, mockConn2, mockConn3, mockConn4);
		CachingClientConnectionFactory cachingFactory = new CachingClientConnectionFactory(factory, 2);
		cachingFactory.start();
		TcpConnection conn1 = cachingFactory.getConnection();
		TcpConnection conn2 = cachingFactory.getConnection();
		assertNotSame(conn1, conn2);
		Semaphore semaphore = TestUtils.getPropertyValue(
				TestUtils.getPropertyValue(cachingFactory, "pool"), "permits", Semaphore.class);
		assertEquals(0, semaphore.availablePermits());
		cachingFactory.setPoolSize(4);
		TcpConnection conn3 = cachingFactory.getConnection();
		TcpConnection conn4 = cachingFactory.getConnection();
		assertEquals(0, semaphore.availablePermits());
		conn1.close();
		conn1.close();
		conn2.close();
		conn3.close();
		conn4.close();
		assertEquals(4, semaphore.availablePermits());
	}

	@Test
	public void testReducePool() throws Exception {
		AbstractClientConnectionFactory factory = mock(AbstractClientConnectionFactory.class);
		when(factory.isRunning()).thenReturn(true);
		TcpConnectionSupport mockConn1 = makeMockConnection("conn1", true);
		TcpConnectionSupport mockConn2 = makeMockConnection("conn2", true);
		TcpConnectionSupport mockConn3 = makeMockConnection("conn3", true);
		TcpConnectionSupport mockConn4 = makeMockConnection("conn4", true);
		when(factory.getConnection()).thenReturn(mockConn1)
				.thenReturn(mockConn2).thenReturn(mockConn3)
				.thenReturn(mockConn4);
		CachingClientConnectionFactory cachingFactory = new CachingClientConnectionFactory(factory, 4);
		cachingFactory.start();
		TcpConnection conn1 = cachingFactory.getConnection();
		TcpConnection conn2 = cachingFactory.getConnection();
		TcpConnection conn3 = cachingFactory.getConnection();
		TcpConnection conn4 = cachingFactory.getConnection();
		Semaphore semaphore = TestUtils.getPropertyValue(
				TestUtils.getPropertyValue(cachingFactory, "pool"), "permits", Semaphore.class);
		assertEquals(0, semaphore.availablePermits());
		conn1.close();
		assertEquals(1, semaphore.availablePermits());
		cachingFactory.setPoolSize(2);
		assertEquals(0, semaphore.availablePermits());
		assertEquals(3, cachingFactory.getActiveCount());
		conn2.close();
		assertEquals(0, semaphore.availablePermits());
		assertEquals(2, cachingFactory.getActiveCount());
		conn3.close();
		assertEquals(1, cachingFactory.getActiveCount());
		assertEquals(1, cachingFactory.getIdleCount());
		conn4.close();
		assertEquals(2, semaphore.availablePermits());
		assertEquals(0, cachingFactory.getActiveCount());
		assertEquals(2, cachingFactory.getIdleCount());
		verify(mockConn1).close();
		verify(mockConn2).close();
	}

	@Test
	public void testExceptionOnSendNet() throws Exception {
		TcpConnectionSupport conn1 = mockedTcpNetConnection();
		TcpConnectionSupport conn2 = mockedTcpNetConnection();

		CachingClientConnectionFactory cccf = createCCCFWith2Connections(conn1, conn2);
		doTestCloseOnSendError(conn1, conn2, cccf);
	}

	@Test
	public void testExceptionOnSendNio() throws Exception {
		TcpConnectionSupport conn1 = mockedTcpNioConnection();
		TcpConnectionSupport conn2 = mockedTcpNioConnection();

		CachingClientConnectionFactory cccf = createCCCFWith2Connections(conn1, conn2);
		doTestCloseOnSendError(conn1, conn2, cccf);
	}

	private void doTestCloseOnSendError(TcpConnection conn1, TcpConnection conn2,
			CachingClientConnectionFactory cccf) throws Exception {
		TcpConnection cached1 = cccf.getConnection();
		try {
			cached1.send(new GenericMessage<String>("foo"));
			fail("Expected IOException");
		}
		catch (IOException e) {
			assertEquals("Foo", e.getMessage());
		}
		// Before INT-3163 this failed with a timeout - connection not returned to pool after failure on send()
		TcpConnection cached2 = cccf.getConnection();
		assertTrue(cached1.getConnectionId().contains(conn1.getConnectionId()));
		assertTrue(cached2.getConnectionId().contains(conn2.getConnectionId()));
	}

	private CachingClientConnectionFactory createCCCFWith2Connections(TcpConnectionSupport conn1, TcpConnectionSupport conn2)
			throws Exception {
		AbstractClientConnectionFactory factory = mock(AbstractClientConnectionFactory.class);
		when(factory.isRunning()).thenReturn(true);
		when(factory.getConnection()).thenReturn(conn1, conn2);
		CachingClientConnectionFactory cccf = new CachingClientConnectionFactory(factory, 1);
		cccf.setConnectionWaitTimeout(1);
		cccf.start();
		return cccf;
	}

	private TcpConnectionSupport mockedTcpNetConnection() throws IOException {
		Socket socket = mock(Socket.class);
		when(socket.isClosed()).thenReturn(true); // closed when next retrieved
		OutputStream stream = mock(OutputStream.class);
		doThrow(new IOException("Foo")).when(stream).write(any(byte[].class), anyInt(), anyInt());
		when(socket.getOutputStream()).thenReturn(stream);
		TcpNetConnection conn = new TcpNetConnection(socket, false, false, new ApplicationEventPublisher() {

			@Override
			public void publishEvent(ApplicationEvent event) {
			}

			@Override
			public void publishEvent(Object event) {

			}

		}, "foo");
		conn.setMapper(new TcpMessageMapper());
		conn.setSerializer(new ByteArrayCrLfSerializer());
		return conn;
	}

	private TcpConnectionSupport mockedTcpNioConnection() throws Exception {
		SocketChannel socketChannel = mock(SocketChannel.class);
		new DirectFieldAccessor(socketChannel).setPropertyValue("open", false);
		doThrow(new IOException("Foo")).when(socketChannel).write(Mockito.any(ByteBuffer.class));
		when(socketChannel.socket()).thenReturn(mock(Socket.class));
		TcpNioConnection conn = new TcpNioConnection(socketChannel, false, false, new ApplicationEventPublisher() {

			@Override
			public void publishEvent(ApplicationEvent event) {
			}

			@Override
			public void publishEvent(Object event) {

			}

		}, "foo");
		conn.setMapper(new TcpMessageMapper());
		conn.setSerializer(new ByteArrayCrLfSerializer());
		return conn;
	}

	private TcpConnectionSupport makeMockConnection(String name) {
		return makeMockConnection(name, false);
	}

	private TcpConnectionSupport makeMockConnection(String name, boolean closeOk) {
		TcpConnectionSupport mockConn1 = mock(TcpConnectionSupport.class);
		when(mockConn1.getConnectionId()).thenReturn(name);
		when(mockConn1.toString()).thenReturn(name);
		when(mockConn1.isOpen()).thenReturn(true);
		if (!closeOk) {
			doThrow(new RuntimeException("close() not expected")).when(mockConn1).close();
		}
		return mockConn1;
	}

	@Test
	public void integrationTest() throws Exception {
		TestingUtilities.waitListening(serverCf, null);
		outbound.send(new GenericMessage<String>("Hello, world!"));
		Message<?> m = inbound.receive(1000);
		assertNotNull(m);
		String connectionId = m.getHeaders().get(IpHeaders.CONNECTION_ID, String.class);

		// assert we use the same connection from the pool
		outbound.send(new GenericMessage<String>("Hello, world!"));
		m = inbound.receive(1000);
		assertNotNull(m);
		assertEquals(connectionId, m.getHeaders().get(IpHeaders.CONNECTION_ID, String.class));
	}

	@Test
//	@Repeat(1000) // INT-3722
	public void gatewayIntegrationTest() throws Exception {
		final List<String> connectionIds = new ArrayList<String>();
		final AtomicBoolean okToRun = new AtomicBoolean(true);
		Executors.newSingleThreadExecutor().execute(new Runnable() {

			@Override
			public void run() {
				while (okToRun.get()) {
					Message<?> m = inbound.receive(1000);
					if (m != null) {
						connectionIds.add((String) m.getHeaders().get(IpHeaders.CONNECTION_ID));
						replies.send(MessageBuilder.withPayload("foo:" + new String((byte[]) m.getPayload()))
								.copyHeaders(m.getHeaders())
								.build());
					}
				}
			}

		});
		TestingUtilities.waitListening(serverCf, null);
		toGateway.send(new GenericMessage<String>("Hello, world!"));
		Message<?> m = fromGateway.receive(1000);
		assertNotNull(m);
		assertEquals("foo:" + "Hello, world!", new String((byte[]) m.getPayload()));

		BlockingQueue<?> connections = TestUtils
				.getPropertyValue(this.gatewayCF, "pool.available", BlockingQueue.class);
		// wait until the connection is returned to the pool
		int n = 0;
		while (n++ < 100 && connections.size() == 0) {
			Thread.sleep(100);
		}

		// assert we use the same connection from the pool
		toGateway.send(new GenericMessage<String>("Hello, world2!"));
		m = fromGateway.receive(1000);
		assertNotNull(m);
		assertEquals("foo:" + "Hello, world2!", new String((byte[]) m.getPayload()));

		assertEquals(2, connectionIds.size());
		assertEquals(connectionIds.get(0), connectionIds.get(1));

		okToRun.set(false);
	}

	@Test
	public void testCloseOnTimeoutNet() throws Exception {
		TcpNetClientConnectionFactory cf = new TcpNetClientConnectionFactory("localhost", serverCf.getPort());
		testCloseOnTimeoutGuts(cf);
	}

	@Test
	public void testCloseOnTimeoutNio() throws Exception {
		TcpNioClientConnectionFactory cf = new TcpNioClientConnectionFactory("localhost", serverCf.getPort());
		testCloseOnTimeoutGuts(cf);
	}

	private void testCloseOnTimeoutGuts(AbstractClientConnectionFactory cf) throws Exception {
		TestingUtilities.waitListening(serverCf, null);
		cf.setSoTimeout(100);
		CachingClientConnectionFactory cccf = new CachingClientConnectionFactory(cf, 1);
		cccf.start();
		TcpConnection connection = cccf.getConnection();
		int n = 0;
		while (n++ < 100 && connection.isOpen()) {
			Thread.sleep(100);
		}
		assertFalse(connection.isOpen());
		cccf.stop();
	}

	@Test
	public void testCachedFailover() throws Exception {
		// Failover
		AbstractClientConnectionFactory factory1 = mock(AbstractClientConnectionFactory.class);
		AbstractClientConnectionFactory factory2 = mock(AbstractClientConnectionFactory.class);
		List<AbstractClientConnectionFactory> factories = new ArrayList<AbstractClientConnectionFactory>();
		factories.add(factory1);
		factories.add(factory2);
		TcpConnectionSupport mockConn1 = makeMockConnection();
		TcpConnectionSupport mockConn2 = makeMockConnection();
		when(factory1.getConnection()).thenReturn(mockConn1);
		when(factory2.getConnection()).thenReturn(mockConn2);
		when(factory1.isActive()).thenReturn(true);
		when(factory2.isActive()).thenReturn(true);
		doThrow(new IOException("fail")).when(mockConn1).send(Mockito.any(Message.class));
		doAnswer(new Answer<Object>() {

			@Override
			public Object answer(InvocationOnMock invocation) throws Throwable {
				return null;
			}

		}).when(mockConn2).send(Mockito.any(Message.class));
		FailoverClientConnectionFactory failoverFactory = new FailoverClientConnectionFactory(factories);
		failoverFactory.start();

		// Cache
		CachingClientConnectionFactory cachingFactory = new CachingClientConnectionFactory(failoverFactory, 2);
		cachingFactory.start();
		TcpConnection conn1 = cachingFactory.getConnection();
		GenericMessage<String> message = new GenericMessage<String>("foo");
		conn1 = cachingFactory.getConnection();
		conn1.send(message);
		Mockito.verify(mockConn2).send(message);
	}

	@Test //INT-3650
	public void testRealConnection() throws Exception {
		int port = SocketUtils.findAvailableTcpPort();
		TcpNetServerConnectionFactory in = new TcpNetServerConnectionFactory(port);
		final CountDownLatch latch1 = new CountDownLatch(2);
		final CountDownLatch latch2 = new CountDownLatch(102);
		final List<String> connectionIds = new ArrayList<String>();
		in.registerListener(new TcpListener() {

			@Override
			public boolean onMessage(Message<?> message) {
				connectionIds.add((String) message.getHeaders().get(IpHeaders.CONNECTION_ID));
				latch1.countDown();
				latch2.countDown();
				return false;
			}

		});
		in.start();
		int n = 0;
		while (n++ < 100 && !in.isListening()) {
			Thread.sleep(100);
		}
		assertTrue(in.isListening());
		TcpNetClientConnectionFactory out = new TcpNetClientConnectionFactory("localhost", port);
		CachingClientConnectionFactory cache = new CachingClientConnectionFactory(out, 1);
		cache.setSingleUse(false);
		cache.start();
		TcpConnectionSupport connection1 = cache.getConnection();
		connection1.send(new GenericMessage<String>("foo"));
		TcpConnectionSupport connection2 = cache.getConnection();
		connection2.send(new GenericMessage<String>("foo"));
		assertTrue(latch1.await(10, TimeUnit.SECONDS));
		assertSame(connectionIds.get(0), connectionIds.get(1));
		for (int i = 0; i < 100; i++) {
			TcpConnectionSupport connection = cache.getConnection();
			connection.send(new GenericMessage<String>("foo"));
		}
		assertTrue(latch2.await(10, TimeUnit.SECONDS));
		assertSame(connectionIds.get(0), connectionIds.get(101));
		in.stop();
		cache.stop();
	}

	@SuppressWarnings("unchecked")
	@Test //INT-3722
	public void testGatewayRelease() throws Exception {
		int port = SocketUtils.findAvailableTcpPort();
		TcpNetServerConnectionFactory in = new TcpNetServerConnectionFactory(port);
		in.setApplicationEventPublisher(mock(ApplicationEventPublisher.class));
		final TcpSendingMessageHandler handler = new TcpSendingMessageHandler();
		handler.setConnectionFactory(in);
		final AtomicInteger count = new AtomicInteger(2);
		in.registerListener(new TcpListener() {

			@Override
			public boolean onMessage(Message<?> message) {
				if (!(message instanceof ErrorMessage)) {
					if (count.decrementAndGet() < 1) {
						try {
							Thread.sleep(1000);
						}
						catch (InterruptedException e) {
							Thread.currentThread().interrupt();
						}
					}
					handler.handleMessage(message);
				}
				return false;
			}

		});
		handler.setBeanFactory(mock(BeanFactory.class));
		handler.afterPropertiesSet();
		handler.start();
		int n = 0;
		while (n++ < 100 && !in.isListening()) {
			Thread.sleep(100);
		}
		assertTrue(in.isListening());
		TcpNetClientConnectionFactory out = new TcpNetClientConnectionFactory("localhost", port);
		out.setApplicationEventPublisher(mock(ApplicationEventPublisher.class));
		CachingClientConnectionFactory cache = new CachingClientConnectionFactory(out, 2);
		final TcpOutboundGateway gate = new TcpOutboundGateway();
		gate.setConnectionFactory(cache);
		QueueChannel outputChannel = new QueueChannel();
		gate.setOutputChannel(outputChannel);
		gate.setBeanFactory(mock(BeanFactory.class));
		gate.afterPropertiesSet();
		Log logger = spy(TestUtils.getPropertyValue(gate, "logger", Log.class));
		new DirectFieldAccessor(gate).setPropertyValue("logger", logger);
		when(logger.isDebugEnabled()).thenReturn(true);
		doAnswer(new Answer<Void>() {

			private final CountDownLatch latch = new CountDownLatch(2);

			@Override
			public Void answer(InvocationOnMock invocation) throws Throwable {
				String log = (String) invocation.getArguments()[0];
				if (log.startsWith("Response")) {
					Executors.newSingleThreadScheduledExecutor().execute(new Runnable() {

						@Override
						public void run() {
							gate.handleMessage(new GenericMessage<String>("bar"));
						}
					});
					// hold up the first thread until the second has added its pending reply
					latch.await(10, TimeUnit.SECONDS);
				}
				else if (log.startsWith("Added")) {
					latch.countDown();
				}
				return null;
			}
		}).when(logger).debug(anyString());
		gate.start();
		gate.handleMessage(new GenericMessage<String>("foo"));
		Message<byte[]> result = (Message<byte[]>) outputChannel.receive(10000);
		assertNotNull(result);
		assertEquals("foo", new String(result.getPayload()));
		result = (Message<byte[]>) outputChannel.receive(10000);
		assertNotNull(result);
		assertEquals("bar", new String(result.getPayload()));
		handler.stop();
		gate.stop();
		verify(logger, never()).error(anyString());
	}

	@Test // INT-3728
	public void testEarlyReceive() throws Exception {
		final CountDownLatch latch = new CountDownLatch(1);
		final AbstractClientConnectionFactory factory = new TcpNetClientConnectionFactory("", 0) {

			@Override
			protected Socket createSocket(String host, int port) throws IOException {
				Socket mock = mock(Socket.class);
				when(mock.getInputStream()).thenReturn(new ByteArrayInputStream("foo\r\n".getBytes()));
				return mock;
			}

			@Override
			public boolean isActive() {
				return true;
			}

		};
		factory.setApplicationEventPublisher(mock(ApplicationEventPublisher.class));
		final CachingClientConnectionFactory cachingFactory = new CachingClientConnectionFactory(factory, 1);
		final AtomicReference<Message<?>> received = new AtomicReference<Message<?>>();
		cachingFactory.registerListener(new TcpListener() {

			@Override
			public boolean onMessage(Message<?> message) {
				if (!(message instanceof ErrorMessage)) {
					received.set(message);
					latch.countDown();
				}
				return false;
			}
		});
		cachingFactory.start();

		cachingFactory.getConnection();
		assertTrue(latch.await(10, TimeUnit.SECONDS));
		assertNotNull(received.get());
		assertNotNull(received.get().getHeaders().get(IpHeaders.ACTUAL_CONNECTION_ID));
		cachingFactory.stop();
	}

	private TcpConnectionSupport makeMockConnection() {
		TcpConnectionSupport connection = mock(TcpConnectionSupport.class);
		when(connection.isOpen()).thenReturn(true);
		return connection;
	}

}


File: spring-integration-ip/src/test/java/org/springframework/integration/ip/tcp/connection/FailoverClientConnectionFactoryTests.java
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

package org.springframework.integration.ip.tcp.connection;

import static org.junit.Assert.assertNotNull;
import static org.junit.Assert.assertTrue;
import static org.junit.Assert.fail;
import static org.mockito.Mockito.doAnswer;
import static org.mockito.Mockito.doThrow;
import static org.mockito.Mockito.mock;
import static org.mockito.Mockito.times;
import static org.mockito.Mockito.when;

import java.io.IOException;
import java.net.Socket;
import java.nio.channels.SocketChannel;
import java.util.ArrayList;
import java.util.List;
import java.util.concurrent.Executor;
import java.util.concurrent.Executors;
import java.util.concurrent.atomic.AtomicBoolean;
import java.util.concurrent.atomic.AtomicInteger;
import java.util.concurrent.atomic.AtomicReference;

import org.junit.Test;
import org.mockito.Mockito;
import org.mockito.invocation.InvocationOnMock;
import org.mockito.stubbing.Answer;

import org.springframework.beans.factory.BeanFactory;
import org.springframework.context.ApplicationEvent;
import org.springframework.context.ApplicationEventPublisher;
import org.springframework.integration.channel.DirectChannel;
import org.springframework.integration.channel.QueueChannel;
import org.springframework.integration.ip.IpHeaders;
import org.springframework.integration.ip.tcp.TcpInboundGateway;
import org.springframework.integration.ip.tcp.TcpOutboundGateway;
import org.springframework.integration.ip.util.TestingUtilities;
import org.springframework.integration.test.util.SocketUtils;
import org.springframework.integration.test.util.TestUtils;
import org.springframework.messaging.Message;
import org.springframework.messaging.MessageChannel;
import org.springframework.messaging.MessageHandler;
import org.springframework.messaging.MessagingException;
import org.springframework.messaging.SubscribableChannel;
import org.springframework.messaging.support.GenericMessage;

/**
 * @author Gary Russell
 * @since 2.2
 *
 */
public class FailoverClientConnectionFactoryTests {

	@Test
	public void testFailoverGood() throws Exception {
		AbstractClientConnectionFactory factory1 = mock(AbstractClientConnectionFactory.class);
		AbstractClientConnectionFactory factory2 = mock(AbstractClientConnectionFactory.class);
		List<AbstractClientConnectionFactory> factories = new ArrayList<AbstractClientConnectionFactory>();
		factories.add(factory1);
		factories.add(factory2);
		TcpConnectionSupport conn1 = makeMockConnection();
		TcpConnectionSupport conn2 = makeMockConnection();
		when(factory1.getConnection()).thenReturn(conn1);
		when(factory2.getConnection()).thenReturn(conn2);
		when(factory1.isActive()).thenReturn(true);
		when(factory2.isActive()).thenReturn(true);
		doThrow(new IOException("fail")).when(conn1).send(Mockito.any(Message.class));
		doAnswer(new Answer<Object>() {
			@Override
			public Object answer(InvocationOnMock invocation) throws Throwable {
				return null;
			}
		}).when(conn2).send(Mockito.any(Message.class));
		FailoverClientConnectionFactory failoverFactory = new FailoverClientConnectionFactory(factories);
		failoverFactory.start();
		GenericMessage<String> message = new GenericMessage<String>("foo");
		failoverFactory.getConnection().send(message);
		Mockito.verify(conn2).send(message);
	}

	@Test(expected=IOException.class)
	public void testFailoverAllDead() throws Exception {
		AbstractClientConnectionFactory factory1 = mock(AbstractClientConnectionFactory.class);
		AbstractClientConnectionFactory factory2 = mock(AbstractClientConnectionFactory.class);
		List<AbstractClientConnectionFactory> factories = new ArrayList<AbstractClientConnectionFactory>();
		factories.add(factory1);
		factories.add(factory2);
		TcpConnectionSupport conn1 = makeMockConnection();
		TcpConnectionSupport conn2 = makeMockConnection();
		when(factory1.getConnection()).thenReturn(conn1);
		when(factory2.getConnection()).thenReturn(conn2);
		when(factory1.isActive()).thenReturn(true);
		when(factory2.isActive()).thenReturn(true);
		doThrow(new IOException("fail")).when(conn1).send(Mockito.any(Message.class));
		doThrow(new IOException("fail")).when(conn2).send(Mockito.any(Message.class));
		FailoverClientConnectionFactory failoverFactory = new FailoverClientConnectionFactory(factories);
		failoverFactory.start();
		GenericMessage<String> message = new GenericMessage<String>("foo");
		failoverFactory.getConnection().send(message);
		Mockito.verify(conn2).send(message);
	}

	@Test
	public void testFailoverAllDeadButOriginalOkAgain() throws Exception {
		AbstractClientConnectionFactory factory1 = mock(AbstractClientConnectionFactory.class);
		AbstractClientConnectionFactory factory2 = mock(AbstractClientConnectionFactory.class);
		List<AbstractClientConnectionFactory> factories = new ArrayList<AbstractClientConnectionFactory>();
		factories.add(factory1);
		factories.add(factory2);
		TcpConnectionSupport conn1 = makeMockConnection();
		TcpConnectionSupport conn2 = makeMockConnection();
		when(factory1.getConnection()).thenReturn(conn1);
		when(factory2.getConnection()).thenReturn(conn2);
		when(factory1.isActive()).thenReturn(true);
		when(factory2.isActive()).thenReturn(true);
		final AtomicBoolean failedOnce = new AtomicBoolean();
		doAnswer(new Answer<Object>() {
			@Override
			public Object answer(InvocationOnMock invocation) throws Throwable {
				if (!failedOnce.get()) {
					failedOnce.set(true);
					throw new IOException("fail");
				}
				return null;
			}
		}).when(conn1).send(Mockito.any(Message.class));
		doThrow(new IOException("fail")).when(conn2).send(Mockito.any(Message.class));
		FailoverClientConnectionFactory failoverFactory = new FailoverClientConnectionFactory(factories);
		failoverFactory.start();
		GenericMessage<String> message = new GenericMessage<String>("foo");
		failoverFactory.getConnection().send(message);
		Mockito.verify(conn2).send(message);
		Mockito.verify(conn1, times(2)).send(message);
	}

	@Test(expected=IOException.class)
	public void testFailoverConnectNone() throws Exception {
		AbstractClientConnectionFactory factory1 = mock(AbstractClientConnectionFactory.class);
		AbstractClientConnectionFactory factory2 = mock(AbstractClientConnectionFactory.class);
		List<AbstractClientConnectionFactory> factories = new ArrayList<AbstractClientConnectionFactory>();
		factories.add(factory1);
		factories.add(factory2);
		when(factory1.getConnection()).thenThrow(new IOException("fail"));
		when(factory2.getConnection()).thenThrow(new IOException("fail"));
		when(factory1.isActive()).thenReturn(true);
		when(factory2.isActive()).thenReturn(true);
		FailoverClientConnectionFactory failoverFactory = new FailoverClientConnectionFactory(factories);
		failoverFactory.start();
		GenericMessage<String> message = new GenericMessage<String>("foo");
		failoverFactory.getConnection().send(message);
	}

	@Test
	public void testFailoverConnectToFirstAfterTriedAll() throws Exception {
		AbstractClientConnectionFactory factory1 = mock(AbstractClientConnectionFactory.class);
		AbstractClientConnectionFactory factory2 = mock(AbstractClientConnectionFactory.class);
		List<AbstractClientConnectionFactory> factories = new ArrayList<AbstractClientConnectionFactory>();
		factories.add(factory1);
		factories.add(factory2);
		TcpConnectionSupport conn1 = makeMockConnection();
		doAnswer(new Answer<Object>() {
			@Override
			public Object answer(InvocationOnMock invocation) throws Throwable {
				return null;
			}
		}).when(conn1).send(Mockito.any(Message.class));
		when(factory1.getConnection()).thenThrow(new IOException("fail")).thenReturn(conn1);
		when(factory2.getConnection()).thenThrow(new IOException("fail"));
		when(factory1.isActive()).thenReturn(true);
		when(factory2.isActive()).thenReturn(true);
		FailoverClientConnectionFactory failoverFactory = new FailoverClientConnectionFactory(factories);
		failoverFactory.start();
		GenericMessage<String> message = new GenericMessage<String>("foo");
		failoverFactory.getConnection().send(message);
		Mockito.verify(conn1).send(message);
	}

	@Test
	public void testOkAgainAfterCompleteFailure() throws Exception {
		AbstractClientConnectionFactory factory1 = mock(AbstractClientConnectionFactory.class);
		AbstractClientConnectionFactory factory2 = mock(AbstractClientConnectionFactory.class);
		List<AbstractClientConnectionFactory> factories = new ArrayList<AbstractClientConnectionFactory>();
		factories.add(factory1);
		factories.add(factory2);
		TcpConnectionSupport conn1 = makeMockConnection();
		TcpConnectionSupport conn2 = makeMockConnection();
		when(factory1.getConnection()).thenReturn(conn1);
		when(factory2.getConnection()).thenReturn(conn2);
		when(factory1.isActive()).thenReturn(true);
		when(factory2.isActive()).thenReturn(true);
		final AtomicInteger failCount = new AtomicInteger();
		doAnswer(new Answer<Object>() {
			@Override
			public Object answer(InvocationOnMock invocation) throws Throwable {
				if (failCount.incrementAndGet() < 3) {
					throw new IOException("fail");
				}
				return null;
			}
		}).when(conn1).send(Mockito.any(Message.class));
		doThrow(new IOException("fail")).when(conn2).send(Mockito.any(Message.class));
		FailoverClientConnectionFactory failoverFactory = new FailoverClientConnectionFactory(factories);
		failoverFactory.start();
		GenericMessage<String> message = new GenericMessage<String>("foo");
		try {
			failoverFactory.getConnection().send(message);
			fail("ExpectedFailure");
		}
		catch (IOException e) {}
		failoverFactory.getConnection().send(message);
		Mockito.verify(conn2).send(message);
		Mockito.verify(conn1, times(3)).send(message);
	}

	public TcpConnectionSupport makeMockConnection() {
		TcpConnectionSupport connection = mock(TcpConnectionSupport.class);
		when(connection.isOpen()).thenReturn(true);
		return connection;
	}

	@Test
	public void testRealNet() throws Exception {

		final List<Integer> openPorts = SocketUtils.findAvailableServerSockets(SocketUtils.getRandomSeedPort(), 2);

		int port1 = openPorts.get(0);
		int port2 = openPorts.get(1);
		AbstractClientConnectionFactory client1 = new TcpNetClientConnectionFactory("localhost", port1);
		AbstractClientConnectionFactory client2 = new TcpNetClientConnectionFactory("localhost", port2);
		AbstractServerConnectionFactory server1 = new TcpNetServerConnectionFactory(port1);
		AbstractServerConnectionFactory server2 = new TcpNetServerConnectionFactory(port2);
		testRealGuts(client1, client2, server1, server2);
	}

	@Test
	public void testRealNio() throws Exception {

		final List<Integer> openPorts = SocketUtils.findAvailableServerSockets(SocketUtils.getRandomSeedPort(), 2);

		int port1 = openPorts.get(0);
		int port2 = openPorts.get(1);

		AbstractClientConnectionFactory client1 = new TcpNioClientConnectionFactory("localhost", port1);
		AbstractClientConnectionFactory client2 = new TcpNioClientConnectionFactory("localhost", port2);
		AbstractServerConnectionFactory server1 = new TcpNioServerConnectionFactory(port1);
		AbstractServerConnectionFactory server2 = new TcpNioServerConnectionFactory(port2);
		testRealGuts(client1, client2, server1, server2);
	}

	@Test
	public void testRealNetSingleUse() throws Exception {

		final List<Integer> openPorts = SocketUtils.findAvailableServerSockets(SocketUtils.getRandomSeedPort(), 2);

		int port1 = openPorts.get(0);
		int port2 = openPorts.get(1);

		AbstractClientConnectionFactory client1 = new TcpNetClientConnectionFactory("localhost", port1);
		AbstractClientConnectionFactory client2 = new TcpNetClientConnectionFactory("localhost", port2);
		AbstractServerConnectionFactory server1 = new TcpNetServerConnectionFactory(port1);
		AbstractServerConnectionFactory server2 = new TcpNetServerConnectionFactory(port2);
		client1.setSingleUse(true);
		client2.setSingleUse(true);
		testRealGuts(client1, client2, server1, server2);
	}

	@Test
	public void testRealNioSingleUse() throws Exception {

		final List<Integer> openPorts = SocketUtils.findAvailableServerSockets(SocketUtils.getRandomSeedPort(), 2);

		int port1 = openPorts.get(0);
		int port2 = openPorts.get(1);

		AbstractClientConnectionFactory client1 = new TcpNioClientConnectionFactory("localhost", port1);
		AbstractClientConnectionFactory client2 = new TcpNioClientConnectionFactory("localhost", port2);
		AbstractServerConnectionFactory server1 = new TcpNioServerConnectionFactory(port1);
		AbstractServerConnectionFactory server2 = new TcpNioServerConnectionFactory(port2);
		client1.setSingleUse(true);
		client2.setSingleUse(true);
		testRealGuts(client1, client2, server1, server2);
	}

	private void testRealGuts(AbstractClientConnectionFactory client1, AbstractClientConnectionFactory client2,
			AbstractServerConnectionFactory server1, AbstractServerConnectionFactory server2) throws Exception {
		int port1;
		int port2;
		Executor exec = Executors.newCachedThreadPool();
		client1.setTaskExecutor(exec);
		client2.setTaskExecutor(exec);
		server1.setTaskExecutor(exec);
		server2.setTaskExecutor(exec);
		ApplicationEventPublisher pub = new ApplicationEventPublisher() {

			@Override
			public void publishEvent(ApplicationEvent event) {
			}

			@Override
			public void publishEvent(Object event) {
				
			}
			
		};
		client1.setApplicationEventPublisher(pub);
		client2.setApplicationEventPublisher(pub);
		server1.setApplicationEventPublisher(pub);
		server2.setApplicationEventPublisher(pub);
		TcpInboundGateway gateway1 = new TcpInboundGateway();
		gateway1.setConnectionFactory(server1);
		SubscribableChannel channel = new DirectChannel();
		final AtomicReference<String> connectionId = new AtomicReference<String>();
		channel.subscribe(new MessageHandler() {
			@Override
			public void handleMessage(Message<?> message) throws MessagingException {
				connectionId.set((String) message.getHeaders().get(IpHeaders.CONNECTION_ID));
				((MessageChannel) message.getHeaders().getReplyChannel()).send(message);
			}
		});
		gateway1.setRequestChannel(channel);
		gateway1.setBeanFactory(mock(BeanFactory.class));
		gateway1.afterPropertiesSet();
		gateway1.start();
		TcpInboundGateway gateway2 = new TcpInboundGateway();
		gateway2.setConnectionFactory(server2);
		gateway2.setRequestChannel(channel);
		gateway2.setBeanFactory(mock(BeanFactory.class));
		gateway2.afterPropertiesSet();
		gateway2.start();
		TestingUtilities.waitListening(server1, null);
		TestingUtilities.waitListening(server2, null);
		List<AbstractClientConnectionFactory> factories = new ArrayList<AbstractClientConnectionFactory>();
		factories.add(client1);
		factories.add(client2);
		FailoverClientConnectionFactory failFactory = new FailoverClientConnectionFactory(factories);
		boolean singleUse = client1.isSingleUse();
		failFactory.setSingleUse(singleUse);
		failFactory.setBeanFactory(mock(BeanFactory.class));
		failFactory.afterPropertiesSet();
		TcpOutboundGateway outGateway = new TcpOutboundGateway();
		outGateway.setConnectionFactory(failFactory);
		outGateway.start();
		QueueChannel replyChannel = new QueueChannel();
		outGateway.setReplyChannel(replyChannel);
		Message<String> message = new GenericMessage<String>("foo");
		outGateway.setRemoteTimeout(120000);
		outGateway.handleMessage(message);
		Socket socket = getSocket(client1);
		port1 = socket.getLocalPort();
		assertTrue(singleUse | connectionId.get().contains(Integer.toString(port1)));
		Message<?> replyMessage = replyChannel.receive(10000);
		assertNotNull(replyMessage);
		server1.stop();
		TestingUtilities.waitUntilFactoryHasThisNumberOfConnections(client1, 0);
		outGateway.handleMessage(message);
		socket = getSocket(client2);
		port2 = socket.getLocalPort();
		assertTrue(singleUse | connectionId.get().contains(Integer.toString(port2)));
		replyMessage = replyChannel.receive(10000);
		assertNotNull(replyMessage);
		gateway2.stop();
		outGateway.stop();
	}

	private Socket getSocket(AbstractClientConnectionFactory client) throws Exception {
		if (client instanceof TcpNetClientConnectionFactory) {
			return TestUtils.getPropertyValue(client.getConnection(), "socket", Socket.class);
		}
		else {
			return TestUtils.getPropertyValue(client.getConnection(), "socketChannel", SocketChannel.class).socket();
		}

	}

}



File: spring-integration-ip/src/test/java/org/springframework/integration/ip/tcp/connection/TcpNioConnectionTests.java
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

package org.springframework.integration.ip.tcp.connection;

import static org.hamcrest.Matchers.containsString;
import static org.hamcrest.Matchers.not;
import static org.junit.Assert.assertEquals;
import static org.junit.Assert.assertNotNull;
import static org.junit.Assert.assertThat;
import static org.junit.Assert.assertTrue;
import static org.junit.Assert.fail;
import static org.mockito.Matchers.any;
import static org.mockito.Mockito.doAnswer;
import static org.mockito.Mockito.doReturn;
import static org.mockito.Mockito.mock;
import static org.mockito.Mockito.spy;
import static org.mockito.Mockito.when;

import java.io.ByteArrayOutputStream;
import java.io.IOException;
import java.io.InputStream;
import java.lang.reflect.Field;
import java.lang.reflect.Method;
import java.net.ConnectException;
import java.net.ServerSocket;
import java.net.Socket;
import java.net.SocketTimeoutException;
import java.nio.ByteBuffer;
import java.nio.channels.SelectionKey;
import java.nio.channels.Selector;
import java.nio.channels.SocketChannel;
import java.util.ArrayList;
import java.util.Arrays;
import java.util.HashMap;
import java.util.HashSet;
import java.util.List;
import java.util.Map;
import java.util.concurrent.Callable;
import java.util.concurrent.CountDownLatch;
import java.util.concurrent.ExecutionException;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;
import java.util.concurrent.Future;
import java.util.concurrent.ThreadPoolExecutor.AbortPolicy;
import java.util.concurrent.TimeUnit;
import java.util.concurrent.atomic.AtomicReference;

import javax.net.ServerSocketFactory;
import javax.net.SocketFactory;

import org.apache.commons.logging.Log;
import org.junit.Test;
import org.mockito.Matchers;
import org.mockito.Mockito;
import org.mockito.invocation.InvocationOnMock;
import org.mockito.stubbing.Answer;

import org.springframework.beans.DirectFieldAccessor;
import org.springframework.context.ApplicationEvent;
import org.springframework.context.ApplicationEventPublisher;
import org.springframework.integration.ip.tcp.connection.TcpNioConnection.ChannelInputStream;
import org.springframework.integration.ip.tcp.serializer.ByteArrayCrLfSerializer;
import org.springframework.integration.ip.tcp.serializer.MapJsonSerializer;
import org.springframework.integration.ip.util.TestingUtilities;
import org.springframework.integration.support.MessageBuilder;
import org.springframework.integration.support.converter.MapMessageConverter;
import org.springframework.integration.test.util.SocketUtils;
import org.springframework.integration.test.util.TestUtils;
import org.springframework.integration.util.CompositeExecutor;
import org.springframework.messaging.Message;
import org.springframework.messaging.support.ErrorMessage;
import org.springframework.scheduling.concurrent.ThreadPoolTaskExecutor;
import org.springframework.util.ReflectionUtils;
import org.springframework.util.ReflectionUtils.FieldCallback;
import org.springframework.util.ReflectionUtils.FieldFilter;


/**
 * @author Gary Russell
 * @author John Anderson
 * @since 2.0
 *
 */
public class TcpNioConnectionTests {

	private final ApplicationEventPublisher nullPublisher = new ApplicationEventPublisher() {
		
		@Override
		public void publishEvent(ApplicationEvent event) {
		}

		@Override
		public void publishEvent(Object event) {
			
		}
		
	};

	@Test
	public void testWriteTimeout() throws Exception {
		final int port = SocketUtils.findAvailableServerSocket();
		TcpNioClientConnectionFactory factory = new TcpNioClientConnectionFactory("localhost", port);
		factory.setSoTimeout(1000);
		factory.start();
		final CountDownLatch latch = new CountDownLatch(1);
		final CountDownLatch done = new CountDownLatch(1);
		final AtomicReference<ServerSocket> serverSocket = new AtomicReference<ServerSocket>();
		Executors.newSingleThreadExecutor().execute(new Runnable() {
			@Override
			@SuppressWarnings("unused")
			public void run() {
				try {
					ServerSocket server = ServerSocketFactory.getDefault().createServerSocket(port);
					serverSocket.set(server);
					latch.countDown();
					Socket s = server.accept();
					// block so we fill the buffer
					done.await(10, TimeUnit.SECONDS);
				}
				catch (Exception e) {
					e.printStackTrace();
				}
			}
		});
		assertTrue(latch.await(10000, TimeUnit.MILLISECONDS));
		try {
			TcpConnection connection = factory.getConnection();
			connection.send(MessageBuilder.withPayload(new byte[1000000]).build());
		}
		catch (Exception e) {
			assertTrue("Expected SocketTimeoutException, got " + e.getClass().getSimpleName() +
					   ":" + e.getMessage(), e instanceof SocketTimeoutException);
		}
		done.countDown();
		serverSocket.get().close();
	}

	@Test
	public void testReadTimeout() throws Exception {
		final int port = SocketUtils.findAvailableServerSocket();
		TcpNioClientConnectionFactory factory = new TcpNioClientConnectionFactory("localhost", port);
		factory.setSoTimeout(1000);
		factory.start();
		final CountDownLatch latch = new CountDownLatch(1);
		final CountDownLatch done = new CountDownLatch(1);
		final AtomicReference<ServerSocket> serverSocket = new AtomicReference<ServerSocket>();
		Executors.newSingleThreadExecutor().execute(new Runnable() {
			@Override
			public void run() {
				try {
					ServerSocket server = ServerSocketFactory.getDefault().createServerSocket(port);
					serverSocket.set(server);
					latch.countDown();
					Socket socket = server.accept();
					byte[] b = new byte[6];
					readFully(socket.getInputStream(), b);
					// block to cause timeout on read.
					done.await(10, TimeUnit.SECONDS);
				}
				catch (Exception e) {
					e.printStackTrace();
				}
			}
		});
		assertTrue(latch.await(10000, TimeUnit.MILLISECONDS));
		try {
			TcpConnection connection = factory.getConnection();
			connection.send(MessageBuilder.withPayload("Test").build());
			int n = 0;
			while (connection.isOpen()) {
				Thread.sleep(100);
				if (n++ > 200) {
					break;
				}
			}
			assertTrue(!connection.isOpen());
		}
		catch (Exception e) {
			fail("Unexpected exception " + e);
		}
		done.countDown();
		serverSocket.get().close();
	}

	@Test
	public void testMemoryLeak() throws Exception {
		final int port = SocketUtils.findAvailableServerSocket();
		TcpNioClientConnectionFactory factory = new TcpNioClientConnectionFactory("localhost", port);
		factory.setNioHarvestInterval(100);
		factory.start();
		final CountDownLatch latch = new CountDownLatch(1);
		final AtomicReference<ServerSocket> serverSocket = new AtomicReference<ServerSocket>();
		Executors.newSingleThreadExecutor().execute(new Runnable() {
			@Override
			public void run() {
				try {
					ServerSocket server = ServerSocketFactory.getDefault().createServerSocket(port);
					serverSocket.set(server);
					latch.countDown();
					Socket socket = server.accept();
					byte[] b = new byte[6];
					readFully(socket.getInputStream(), b);
				}
				catch (Exception e) {
					e.printStackTrace();
				}
			}
		});
		assertTrue(latch.await(10000, TimeUnit.MILLISECONDS));
		try {
			TcpConnection connection = factory.getConnection();
			Map<SocketChannel, TcpNioConnection> connections = factory.getConnections();
			assertEquals(1, connections.size());
			connection.close();
			assertTrue(!connection.isOpen());
			TestUtils.getPropertyValue(factory, "selector", Selector.class).wakeup();
			int n = 0;
			while (connections.size() > 0) {
				Thread.sleep(100);
				if (n++ > 100) {
					break;
				}
			}
			assertEquals(0, connections.size());
		}
		catch (Exception e) {
			e.printStackTrace();
			fail("Unexpected exception " + e);
		}
		factory.stop();
		serverSocket.get().close();
	}

	@Test
	public void testCleanup() throws Exception {
		TcpNioClientConnectionFactory factory = new TcpNioClientConnectionFactory("localhost", 0);
		factory.setNioHarvestInterval(100);
		Map<SocketChannel, TcpNioConnection> connections = new HashMap<SocketChannel, TcpNioConnection>();
		SocketChannel chan1 = mock(SocketChannel.class);
		SocketChannel chan2 = mock(SocketChannel.class);
		SocketChannel chan3 = mock(SocketChannel.class);
		TcpNioConnection conn1 = mock(TcpNioConnection.class);
		TcpNioConnection conn2 = mock(TcpNioConnection.class);
		TcpNioConnection conn3 = mock(TcpNioConnection.class);
		connections.put(chan1, conn1);
		connections.put(chan2, conn2);
		connections.put(chan3, conn3);
		final List<Field> fields = new ArrayList<Field>();
		ReflectionUtils.doWithFields(SocketChannel.class, new FieldCallback() {

			@Override
			public void doWith(Field field) throws IllegalArgumentException,
					IllegalAccessException {
				field.setAccessible(true);
				fields.add(field);
			}
		}, new FieldFilter() {

			@Override
			public boolean matches(Field field) {
				return field.getName().equals("open");
			}});
		Field field = fields.get(0);
		// Can't use Mockito because isOpen() is final
		ReflectionUtils.setField(field, chan1, true);
		ReflectionUtils.setField(field, chan2, true);
		ReflectionUtils.setField(field, chan3, true);
		Selector selector = mock(Selector.class);
		HashSet<SelectionKey> keys = new HashSet<SelectionKey>();
		when(selector.selectedKeys()).thenReturn(keys);
		factory.processNioSelections(1, selector, null, connections);
		assertEquals(3, connections.size()); // all open

		ReflectionUtils.setField(field, chan1, false);
		factory.processNioSelections(1, selector, null, connections);
		assertEquals(3, connections.size()); // interval didn't pass
		Thread.sleep(110);
		factory.processNioSelections(1, selector, null, connections);
		assertEquals(2, connections.size()); // first is closed

		ReflectionUtils.setField(field, chan2, false);
		factory.processNioSelections(1, selector, null, connections);
		assertEquals(2, connections.size()); // interval didn't pass
		Thread.sleep(110);
		factory.processNioSelections(1, selector, null, connections);
		assertEquals(1, connections.size()); // second is closed

		ReflectionUtils.setField(field, chan3, false);
		factory.processNioSelections(1, selector, null, connections);
		assertEquals(1, connections.size()); // interval didn't pass
		Thread.sleep(110);
		factory.processNioSelections(1, selector, null, connections);
		assertEquals(0, connections.size()); // third is closed

		assertEquals(0, TestUtils.getPropertyValue(factory, "connections", List.class).size());
	}

	@Test
	public void testInsufficientThreads() throws Exception {
		final ExecutorService exec = Executors.newFixedThreadPool(2);
		Future<Object> future = exec.submit(new Callable<Object>() {
			@Override
			public Object call() throws Exception {
				SocketChannel channel = mock(SocketChannel.class);
				Socket socket = mock(Socket.class);
				Mockito.when(channel.socket()).thenReturn(socket);
				doAnswer(new Answer<Integer>() {
					@Override
					public Integer answer(InvocationOnMock invocation) throws Throwable {
						ByteBuffer buffer = (ByteBuffer) invocation.getArguments()[0];
						buffer.position(1);
						return 1;
					}
				}).when(channel).read(Mockito.any(ByteBuffer.class));
				when(socket.getReceiveBufferSize()).thenReturn(1024);
				final TcpNioConnection connection = new TcpNioConnection(channel, false, false, null, null);
				connection.setTaskExecutor(exec);
				connection.setPipeTimeout(200);
				Method method = TcpNioConnection.class.getDeclaredMethod("doRead");
				method.setAccessible(true);
				// Nobody reading, should timeout on 6th write.
				try {
					for (int i = 0; i < 6; i++) {
						method.invoke(connection);
					}
				}
				catch (Exception e) {
					e.printStackTrace();
					throw (Exception) e.getCause();
				}
				return null;
			}
		});
		try {
			Object o = future.get(10, TimeUnit.SECONDS);
			fail("Expected exception, got " + o);
		}
		catch (ExecutionException e) {
			assertEquals("Timed out waiting for buffer space", e.getCause().getMessage());
		}
	}

	@Test
	public void testSufficientThreads() throws Exception {
		final ExecutorService exec = Executors.newFixedThreadPool(3);
		final CountDownLatch messageLatch = new CountDownLatch(1);
		Future<Object> future = exec.submit(new Callable<Object>() {
			@Override
			public Object call() throws Exception {
				SocketChannel channel = mock(SocketChannel.class);
				Socket socket = mock(Socket.class);
				Mockito.when(channel.socket()).thenReturn(socket);
				doAnswer(new Answer<Integer>() {
					@Override
					public Integer answer(InvocationOnMock invocation) throws Throwable {
						ByteBuffer buffer = (ByteBuffer) invocation.getArguments()[0];
						buffer.position(1025);
						buffer.put((byte) '\r');
						buffer.put((byte) '\n');
						return 1027;
					}
				}).when(channel).read(Mockito.any(ByteBuffer.class));
				final TcpNioConnection connection = new TcpNioConnection(channel, false, false, null, null);
				connection.setTaskExecutor(exec);
				connection.registerListener(new TcpListener(){
					@Override
					public boolean onMessage(Message<?> message) {
						messageLatch.countDown();
						return false;
					}
				});
				connection.setMapper(new TcpMessageMapper());
				connection.setDeserializer(new ByteArrayCrLfSerializer());
				Method method = TcpNioConnection.class.getDeclaredMethod("doRead");
				method.setAccessible(true);
				try {
					for (int i = 0; i < 20; i++) {
						method.invoke(connection);
					}
				}
				catch (Exception e) {
					e.printStackTrace();
					throw (Exception) e.getCause();
				}
				return null;
			}
		});
		future.get(60, TimeUnit.SECONDS);
		assertTrue(messageLatch.await(10, TimeUnit.SECONDS));
	}

	@Test
	public void testByteArrayRead() throws Exception {
		SocketChannel socketChannel = mock(SocketChannel.class);
		Socket socket = mock(Socket.class);
		when(socketChannel.socket()).thenReturn(socket);
		TcpNioConnection connection = new TcpNioConnection(socketChannel, false, false, null, null);
		TcpNioConnection.ChannelInputStream stream = (ChannelInputStream) new DirectFieldAccessor(connection)
				.getPropertyValue("channelInputStream");
		stream.write("foo".getBytes(), 3);
		byte[] out = new byte[2];
		int n = stream.read(out);
		assertEquals(2, n);
		assertEquals("fo", new String(out));
		out = new byte[2];
		n = stream.read(out);
		assertEquals(1, n);
		assertEquals("o\u0000", new String(out));
	}

	@Test
	public void testByteArrayReadMulti() throws Exception {
		SocketChannel socketChannel = mock(SocketChannel.class);
		Socket socket = mock(Socket.class);
		when(socketChannel.socket()).thenReturn(socket);
		TcpNioConnection connection = new TcpNioConnection(socketChannel, false, false, null, null);
		TcpNioConnection.ChannelInputStream stream = (ChannelInputStream) new DirectFieldAccessor(connection)
				.getPropertyValue("channelInputStream");
		stream.write("foo".getBytes(), 3);
		stream.write("bar".getBytes(), 3);
		byte[] out = new byte[6];
		int n = stream.read(out);
		assertEquals(6, n);
		assertEquals("foobar", new String(out));
	}

	@Test
	public void testByteArrayReadWithOffset() throws Exception {
		SocketChannel socketChannel = mock(SocketChannel.class);
		Socket socket = mock(Socket.class);
		when(socketChannel.socket()).thenReturn(socket);
		TcpNioConnection connection = new TcpNioConnection(socketChannel, false, false, null, null);
		TcpNioConnection.ChannelInputStream stream = (ChannelInputStream) new DirectFieldAccessor(connection)
				.getPropertyValue("channelInputStream");
		stream.write("foo".getBytes(), 3);
		byte[] out = new byte[5];
		int n = stream.read(out, 1, 4);
		assertEquals(3, n);
		assertEquals("\u0000foo\u0000", new String(out));
	}

	@Test
	public void testByteArrayReadWithBadArgs() throws Exception {
		SocketChannel socketChannel = mock(SocketChannel.class);
		Socket socket = mock(Socket.class);
		when(socketChannel.socket()).thenReturn(socket);
		TcpNioConnection connection = new TcpNioConnection(socketChannel, false, false, null, null);
		TcpNioConnection.ChannelInputStream stream = (ChannelInputStream) new DirectFieldAccessor(connection)
				.getPropertyValue("channelInputStream");
		stream.write("foo".getBytes(), 3);
		byte[] out = new byte[5];
		try {
			stream.read(out, 1, 5);
			fail("Expected IndexOutOfBoundsException");
		}
		catch (IndexOutOfBoundsException e) {}
		try {
			stream.read(null, 1, 5);
			fail("Expected IllegalArgumentException");
		}
		catch (IllegalArgumentException e) {}
		assertEquals(0, stream.read(out, 0, 0));
		assertEquals(3, stream.read(out));
	}

	@Test
	public void testByteArrayBlocksForZeroRead() throws Exception {
		SocketChannel socketChannel = mock(SocketChannel.class);
		Socket socket = mock(Socket.class);
		when(socketChannel.socket()).thenReturn(socket);
		TcpNioConnection connection = new TcpNioConnection(socketChannel, false, false, null, null);
		final TcpNioConnection.ChannelInputStream stream = (ChannelInputStream) new DirectFieldAccessor(connection)
				.getPropertyValue("channelInputStream");
		final CountDownLatch latch = new CountDownLatch(1);
		final byte[] out = new byte[4];
		ExecutorService exec = Executors.newSingleThreadExecutor();
		exec.execute(new Runnable(){
			@Override
			public void run() {
				try {
					stream.read(out);
				}
				catch (IOException e) {
					e.printStackTrace();
				}
				latch.countDown();
			}
		});
		Thread.sleep(1000);
		assertEquals(0x00, out[0]);
		stream.write("foo".getBytes(), 3);
		assertTrue(latch.await(10, TimeUnit.SECONDS));
		assertEquals("foo\u0000", new String(out));
	}

	@Test
	public void transferHeaders() throws Exception {
		Socket inSocket = mock(Socket.class);
		SocketChannel inChannel = mock(SocketChannel.class);
		when(inChannel.socket()).thenReturn(inSocket);

		TcpNioConnection inboundConnection = new TcpNioConnection(inChannel, true, false, nullPublisher, null);
		inboundConnection.setDeserializer(new MapJsonSerializer());
		MapMessageConverter inConverter = new MapMessageConverter();
		MessageConvertingTcpMessageMapper inMapper = new MessageConvertingTcpMessageMapper(inConverter);
		inboundConnection.setMapper(inMapper);
		final ByteArrayOutputStream written = new ByteArrayOutputStream();
		doAnswer(new Answer<Integer>() {
			@Override
			public Integer answer(InvocationOnMock invocation) throws Throwable {
				ByteBuffer buff = (ByteBuffer) invocation.getArguments()[0];
				byte[] bytes = written.toByteArray();
				buff.put(bytes);
				return bytes.length;
			}
		}).when(inChannel).read(any(ByteBuffer.class));

		Socket outSocket = mock(Socket.class);
		SocketChannel outChannel = mock(SocketChannel.class);
		when(outChannel.socket()).thenReturn(outSocket);
		TcpNioConnection outboundConnection = new TcpNioConnection(outChannel, true, false, nullPublisher, null);
		doAnswer(new Answer<Object>() {
			@Override
			public Object answer(InvocationOnMock invocation) throws Throwable {
				ByteBuffer buff = (ByteBuffer) invocation.getArguments()[0];
				byte[] bytes = new byte[buff.limit()];
				buff.get(bytes);
				written.write(bytes);
				return null;
			}
		}).when(outChannel).write(any(ByteBuffer.class));

		MapMessageConverter outConverter = new MapMessageConverter();
		outConverter.setHeaderNames("bar");
		MessageConvertingTcpMessageMapper outMapper = new MessageConvertingTcpMessageMapper(outConverter);
		outboundConnection.setMapper(outMapper);
		outboundConnection.setSerializer(new MapJsonSerializer());

		Message<String> message = MessageBuilder.withPayload("foo")
				.setHeader("bar", "baz")
				.build();
		outboundConnection.send(message);

		final AtomicReference<Message<?>> inboundMessage = new AtomicReference<Message<?>>();
		final CountDownLatch latch = new CountDownLatch(1);
		TcpListener listener = new TcpListener() {

			@Override
			public boolean onMessage(Message<?> message) {
				inboundMessage.set(message);
				latch.countDown();
				return false;
			}
		};
		inboundConnection.registerListener(listener);
		inboundConnection.readPacket();
		assertTrue(latch.await(10, TimeUnit.SECONDS));
		assertNotNull(inboundMessage.get());
		assertEquals("foo", inboundMessage.get().getPayload());
		assertEquals("baz", inboundMessage.get().getHeaders().get("bar"));
	}

	@Test
	public void testAssemblerUsesSecondaryExecutor() throws Exception {
		final int port = SocketUtils.findAvailableServerSocket();
		TcpNioServerConnectionFactory factory = new TcpNioServerConnectionFactory(port);
		factory.setApplicationEventPublisher(mock(ApplicationEventPublisher.class));

		CompositeExecutor compositeExec = compositeExecutor();

		factory.setSoTimeout(1000);
		factory.setTaskExecutor(compositeExec);
		final AtomicReference<String> threadName = new AtomicReference<String>();
		final CountDownLatch latch = new CountDownLatch(1);
		factory.registerListener(new TcpListener() {

			@Override
			public boolean onMessage(Message<?> message) {
				if (!(message instanceof ErrorMessage)) {
					threadName.set(Thread.currentThread().getName());
					latch.countDown();
				}
				return false;
			}

		});
		factory.start();

		Socket socket = null;
		int n = 0;
		while (n++ < 100) {
			try {
				socket = SocketFactory.getDefault().createSocket("localhost", port);
				break;
			}
			catch (ConnectException e) {}
			Thread.sleep(100);
		}
		assertTrue("Could not open socket to localhost:" + port, n < 100);
		socket.getOutputStream().write("foo\r\n".getBytes());
		socket.close();

		assertTrue(latch.await(10, TimeUnit.SECONDS));
		assertThat(threadName.get(), containsString("assembler"));

		factory.stop();
	}

	@Test
	public void testAllMessagesDelivered() throws Exception {
		final int numberOfSockets = 100;
		final int port = SocketUtils.findAvailableServerSocket();
		TcpNioServerConnectionFactory factory = new TcpNioServerConnectionFactory(port);
		factory.setApplicationEventPublisher(mock(ApplicationEventPublisher.class));

		CompositeExecutor compositeExec = compositeExecutor();

		factory.setTaskExecutor(compositeExec);
		final CountDownLatch latch = new CountDownLatch(numberOfSockets * 4);
		factory.registerListener(new TcpListener() {

			@Override
			public boolean onMessage(Message<?> message) {
				if (!(message instanceof ErrorMessage)) {
					latch.countDown();
				}
				return false;
			}

		});
		factory.start();

		Socket[] sockets = new Socket[numberOfSockets];
		for (int i = 0; i < numberOfSockets; i++) {
			Socket socket = null;
			int n = 0;
			while (n++ < 100) {
				try {
					socket = SocketFactory.getDefault().createSocket("localhost", port);
					break;
				}
				catch (ConnectException e) {}
				Thread.sleep(100);
			}
			assertTrue("Could not open socket to localhost:" + port, n < 100);
			sockets[i] = socket;
		}
		for (int i = 0; i < numberOfSockets; i++) {
			sockets[i].getOutputStream().write("foo1 and...".getBytes());
			sockets[i].getOutputStream().flush();
		}
		Thread.sleep(100);
		for (int i = 0; i < numberOfSockets; i++) {
			sockets[i].getOutputStream().write(("...foo2\r\nbar1 and...").getBytes());
			sockets[i].getOutputStream().flush();
		}
		for (int i = 0; i < numberOfSockets; i++) {
			sockets[i].getOutputStream().write(("...bar2\r\n").getBytes());
			sockets[i].getOutputStream().flush();
		}
		for (int i = 0; i < numberOfSockets; i++) {
			sockets[i].getOutputStream().write("foo3 and...".getBytes());
			sockets[i].getOutputStream().flush();
		}
		Thread.sleep(100);
		for (int i = 0; i < numberOfSockets; i++) {
			sockets[i].getOutputStream().write(("...foo4\r\nbar3 and...").getBytes());
			sockets[i].getOutputStream().flush();
		}
		for (int i = 0; i < numberOfSockets; i++) {
			sockets[i].getOutputStream().write(("...bar4\r\n").getBytes());
			sockets[i].close();
		}

		assertTrue("latch is still " + latch.getCount(), latch.await(60, TimeUnit.SECONDS));

		factory.stop();
	}

	private CompositeExecutor compositeExecutor() {
		ThreadPoolTaskExecutor ioExec = new ThreadPoolTaskExecutor();
		ioExec.setCorePoolSize(2);
		ioExec.setMaxPoolSize(4);
		ioExec.setQueueCapacity(0);
		ioExec.setThreadNamePrefix("io-");
		ioExec.setRejectedExecutionHandler(new AbortPolicy());
		ioExec.initialize();
		ThreadPoolTaskExecutor assemblerExec = new ThreadPoolTaskExecutor();
		assemblerExec.setCorePoolSize(2);
		assemblerExec.setMaxPoolSize(5);
		assemblerExec.setQueueCapacity(0);
		assemblerExec.setThreadNamePrefix("assembler-");
		assemblerExec.setRejectedExecutionHandler(new AbortPolicy());
		assemblerExec.initialize();
		return new CompositeExecutor(ioExec, assemblerExec);
	}

	@Test
	public void int3453RaceTest() throws Exception {
		final int port = SocketUtils.findAvailableServerSocket();
		TcpNioServerConnectionFactory factory = new TcpNioServerConnectionFactory(port);
		final CountDownLatch connectionLatch = new CountDownLatch(1);
		factory.setApplicationEventPublisher(new ApplicationEventPublisher() {

			@Override
			public void publishEvent(ApplicationEvent event) {
				connectionLatch.countDown();
			}

			@Override
			public void publishEvent(Object event) {
				
			}
			
		});
		final CountDownLatch assemblerLatch = new CountDownLatch(1);
		final AtomicReference<Thread> assembler = new AtomicReference<Thread>();
		factory.registerListener(new TcpListener() {

			@Override
			public boolean onMessage(Message<?> message) {
				if (!(message instanceof ErrorMessage)) {
					assemblerLatch.countDown();
					assembler.set(Thread.currentThread());
				}
				return false;
			}

		});
		ThreadPoolTaskExecutor te = new ThreadPoolTaskExecutor();
		te.setCorePoolSize(3); // selector, reader, assembler
		te.setMaxPoolSize(3);
		te.setQueueCapacity(0);
		te.initialize();
		factory.setTaskExecutor(te);
		factory.start();
		TestingUtilities.waitListening(factory, 10000L);
		Socket socket = SocketFactory.getDefault().createSocket("localhost", port);
		assertTrue(connectionLatch.await(10,  TimeUnit.SECONDS));

		TcpNioConnection connection = (TcpNioConnection) TestUtils.getPropertyValue(factory, "connections", List.class).get(0);
		Log logger = spy(TestUtils.getPropertyValue(connection, "logger", Log.class));
		DirectFieldAccessor dfa = new DirectFieldAccessor(connection);
		dfa.setPropertyValue("logger", logger);

		ChannelInputStream cis = spy(TestUtils.getPropertyValue(connection, "channelInputStream", ChannelInputStream.class));
		dfa.setPropertyValue("channelInputStream", cis);

		final CountDownLatch readerLatch = new CountDownLatch(4); // 3 dataAvailable, 1 continuing
		final CountDownLatch readerFinishedLatch = new CountDownLatch(1);
		doAnswer(new Answer<Void>() {

			@Override
			public Void answer(InvocationOnMock invocation) throws Throwable {
				invocation.callRealMethod();
				// delay the reader thread resetting writingToPipe
				readerLatch.await(10, TimeUnit.SECONDS);
				Thread.sleep(100);
				readerFinishedLatch.countDown();
				return null;
			}
		}).when(cis).write(any(byte[].class), Matchers.anyInt());

		doReturn(true).when(logger).isTraceEnabled();
		doAnswer(new Answer<Void>() {

			@Override
			public Void answer(InvocationOnMock invocation) throws Throwable {
				invocation.callRealMethod();
				readerLatch.countDown();
				return null;
			}
		}).when(logger).trace(Matchers.contains("checking data avail"));

		doAnswer(new Answer<Void>() {

			@Override
			public Void answer(InvocationOnMock invocation) throws Throwable {
				invocation.callRealMethod();
				readerLatch.countDown();
				return null;
			}
		}).when(logger).trace(Matchers.contains("Nio assembler continuing"));

		socket.getOutputStream().write("foo\r\n".getBytes());

		assertTrue(assemblerLatch.await(10, TimeUnit.SECONDS));
		assertTrue(readerFinishedLatch.await(10, TimeUnit.SECONDS));

		StackTraceElement[] stackTrace = assembler.get().getStackTrace();
		assertThat(Arrays.asList(stackTrace).toString(), not(containsString("ChannelInputStream.getNextBuffer")));
		socket.close();
		factory.stop();
	}

	private void readFully(InputStream is, byte[] buff) throws IOException {
		for (int i = 0; i < buff.length; i++) {
			buff[i] = (byte) is.read();
		}
	}

}
