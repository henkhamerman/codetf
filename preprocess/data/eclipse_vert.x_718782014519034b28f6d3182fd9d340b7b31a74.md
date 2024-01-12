Refactoring Types: ['Push Down Attribute']
m/impl/DatagramServerHandler.java
/*
 * Copyright (c) 2011-2013 The original author or authors
 * ------------------------------------------------------
 * All rights reserved. This program and the accompanying materials
 * are made available under the terms of the Eclipse Public License v1.0
 * and Apache License v2.0 which accompanies this distribution.
 *
 *     The Eclipse Public License is available at
 *     http://www.eclipse.org/legal/epl-v10.html
 *
 *     The Apache License v2.0 is available at
 *     http://www.opensource.org/licenses/apache2.0.php
 *
 * You may elect to redistribute this code under either of these licenses.
 */
package io.vertx.core.datagram.impl;

import io.netty.buffer.ByteBuf;
import io.netty.buffer.ByteBufAllocator;
import io.netty.channel.Channel;
import io.netty.channel.ChannelHandlerContext;
import io.netty.channel.socket.DatagramPacket;
import io.vertx.core.buffer.Buffer;
import io.vertx.core.impl.ContextImpl;
import io.vertx.core.impl.VertxInternal;
import io.vertx.core.net.impl.VertxHandler;

import java.util.HashMap;

/**
 * @author <a href="mailto:nmaurer@redhat.com">Norman Maurer</a>
 */
final class DatagramServerHandler extends VertxHandler<DatagramSocketImpl> {
  private final DatagramSocketImpl server;

  DatagramServerHandler(VertxInternal vertx, DatagramSocketImpl server) {
        super(vertx, new HashMap<>());
    this.server = server;
  }

  @Override
  public void handlerAdded(ChannelHandlerContext ctx) throws Exception {
    super.handlerAdded(ctx);
    connectionMap.put(ctx.channel(), server);
  }

  @SuppressWarnings("unchecked")
  @Override
  protected void channelRead(final DatagramSocketImpl server, final ContextImpl context, ChannelHandlerContext chctx, final Object msg) throws Exception {
    context.executeFromIO(() -> server.handlePacket((io.vertx.core.datagram.DatagramPacket) msg));
  }

  @Override
  protected Object safeObject(Object msg, ByteBufAllocator allocator) throws Exception {
    if (msg instanceof DatagramPacket) {
      DatagramPacket packet = (DatagramPacket) msg;
      ByteBuf content = packet.content();
      if (content.isDirect())  {
        content = safeBuffer(content, allocator);
      }
      return new DatagramPacketImpl(packet.sender(), Buffer.buffer(content));
    }
    return msg;
  }
}


File: src/main/java/io/vertx/core/http/impl/ClientConnection.java
/*
 * Copyright (c) 2011-2013 The original author or authors
 * ------------------------------------------------------
 * All rights reserved. This program and the accompanying materials
 * are made available under the terms of the Eclipse Public License v1.0
 * and Apache License v2.0 which accompanies this distribution.
 *
 *     The Eclipse Public License is available at
 *     http://www.eclipse.org/legal/epl-v10.html
 *
 *     The Apache License v2.0 is available at
 *     http://www.opensource.org/licenses/apache2.0.php
 *
 * You may elect to redistribute this code under either of these licenses.
 */

package io.vertx.core.http.impl;

import io.netty.channel.Channel;
import io.netty.channel.ChannelHandler;
import io.netty.channel.ChannelHandlerContext;
import io.netty.channel.ChannelInboundHandlerAdapter;
import io.netty.channel.ChannelPipeline;
import io.netty.handler.codec.http.DefaultFullHttpResponse;
import io.netty.handler.codec.http.DefaultHttpHeaders;
import io.netty.handler.codec.http.FullHttpResponse;
import io.netty.handler.codec.http.HttpContent;
import io.netty.handler.codec.http.HttpContentDecompressor;
import io.netty.handler.codec.http.HttpHeaders;
import io.netty.handler.codec.http.HttpMethod;
import io.netty.handler.codec.http.HttpResponse;
import io.netty.handler.codec.http.LastHttpContent;
import io.netty.handler.codec.http.websocketx.CloseWebSocketFrame;
import io.netty.handler.codec.http.websocketx.WebSocketClientHandshaker;
import io.netty.handler.codec.http.websocketx.WebSocketClientHandshakerFactory;
import io.netty.handler.codec.http.websocketx.WebSocketHandshakeException;
import io.netty.handler.codec.http.websocketx.WebSocketVersion;
import io.netty.util.ReferenceCountUtil;
import io.vertx.core.Handler;
import io.vertx.core.MultiMap;
import io.vertx.core.buffer.Buffer;
import io.vertx.core.http.WebSocket;
import io.vertx.core.http.WebsocketVersion;
import io.vertx.core.http.impl.ws.WebSocketFrameInternal;
import io.vertx.core.impl.ContextImpl;
import io.vertx.core.impl.VertxInternal;
import io.vertx.core.logging.Logger;
import io.vertx.core.logging.LoggerFactory;
import io.vertx.core.spi.metrics.HttpClientMetrics;
import io.vertx.core.net.NetSocket;
import io.vertx.core.net.impl.ConnectionBase;
import io.vertx.core.net.impl.NetSocketImpl;
import io.vertx.core.net.impl.VertxNetHandler;

import java.net.URI;
import java.util.ArrayDeque;
import java.util.HashMap;
import java.util.Map;
import java.util.Queue;

/**
 *
 * This class is optimised for performance when used on the same event loop. However it can be used safely from other threads.
 *
 * The internal state is protected using the synchronized keyword. If always used on the same event loop, then
 * we benefit from biased locking which makes the overhead of synchronized near zero.
 *
 * @author <a href="http://tfox.org">Tim Fox</a>
 */
class ClientConnection extends ConnectionBase {

  private static final Logger log = LoggerFactory.getLogger(ClientConnection.class);

  private final HttpClientImpl client;
  private final String hostHeader;
  private final boolean ssl;
  private final String host;
  private final int port;
  private final ConnectionLifeCycleListener listener;
  // Requests can be pipelined so we need a queue to keep track of requests
  private final Queue<HttpClientRequestImpl> requests = new ArrayDeque<>();
  private final Handler<Throwable> exceptionHandler;
  private final Object metric;
  private final HttpClientMetrics metrics;

  private WebSocketClientHandshaker handshaker;
  private HttpClientRequestImpl currentRequest;
  private HttpClientResponseImpl currentResponse;
  private HttpClientRequestImpl requestForResponse;
  private WebSocketImpl ws;

  ClientConnection(VertxInternal vertx, HttpClientImpl client, Handler<Throwable> exceptionHandler, Channel channel, boolean ssl, String host,
                   int port, ContextImpl context, ConnectionLifeCycleListener listener, HttpClientMetrics metrics) {
    super(vertx, channel, context, metrics);
    this.client = client;
    this.ssl = ssl;
    this.host = host;
    this.port = port;
    if ((port == 80 && !ssl) || (port == 443 && ssl)) {
      this.hostHeader = host;
    } else {
      this.hostHeader = host + ':' + port;
    }
    this.listener = listener;
    this.exceptionHandler = exceptionHandler;
    this.metrics = metrics;
    this.metric = metrics.connected(remoteAddress());
  }

  @Override
  protected Object metric() {
    return metric;
  }

  protected HttpClientMetrics metrics() {
    return metrics;
  }

  synchronized void toWebSocket(String requestURI, MultiMap headers, WebsocketVersion vers, String subProtocols,
                   int maxWebSocketFrameSize, Handler<WebSocket> wsConnect) {
    if (ws != null) {
      throw new IllegalStateException("Already websocket");
    }

    try {
      URI wsuri = new URI(requestURI);
      if (!wsuri.isAbsolute()) {
        // Netty requires an absolute url
        wsuri = new URI((ssl ? "https:" : "http:") + "//" + host + ":" + port + requestURI);
      }
      WebSocketVersion version =
         WebSocketVersion.valueOf((vers == null ?
           WebSocketVersion.V13 : vers).toString());
      HttpHeaders nettyHeaders;
      if (headers != null) {
        nettyHeaders = new DefaultHttpHeaders();
        for (Map.Entry<String, String> entry: headers) {
          nettyHeaders.add(entry.getKey(), entry.getValue());
        }
      } else {
        nettyHeaders = null;
      }
      handshaker = WebSocketClientHandshakerFactory.newHandshaker(wsuri, version, subProtocols, false,
                                                                  nettyHeaders, maxWebSocketFrameSize);
      ChannelPipeline p = channel.pipeline();
      p.addBefore("handler", "handshakeCompleter", new HandshakeInboundHandler(wsConnect, version != WebSocketVersion.V00));
      handshaker.handshake(channel).addListener(future -> {
        if (!future.isSuccess() && exceptionHandler != null) {
          exceptionHandler.handle(future.cause());
        }
      });
    } catch (Exception e) {
      handleException(e);
    }
  }

  private final class HandshakeInboundHandler extends ChannelInboundHandlerAdapter {

    private final boolean supportsContinuation;
    private final Handler<WebSocket> wsConnect;
    private final ContextImpl context;
    private final Queue<Object> buffered = new ArrayDeque<>();
    private FullHttpResponse response;
    private boolean handshaking = true;

    public HandshakeInboundHandler(Handler<WebSocket> wsConnect, boolean supportsContinuation) {
      this.supportsContinuation = supportsContinuation;
      this.wsConnect = wsConnect;
      this.context = vertx.getContext();
    }

    @Override
    public void channelInactive(ChannelHandlerContext ctx) throws Exception {
      super.channelInactive(ctx);
      // if still handshaking this means we not got any response back from the server and so need to notify the client
      // about it as otherwise the client would never been notified.
      if (handshaking) {
        handleException(new WebSocketHandshakeException("Connection closed while handshake in process"));
      }
    }

    @Override
    public void channelRead(ChannelHandlerContext ctx, Object msg) throws Exception {
      if (handshaker != null && handshaking) {
        if (msg instanceof HttpResponse) {
          HttpResponse resp = (HttpResponse) msg;
          if (resp.getStatus().code() != 101) {
            handleException(new WebSocketHandshakeException("Websocket connection attempt returned HTTP status code " + resp.getStatus().code()));
            return;
          }
          response = new DefaultFullHttpResponse(resp.getProtocolVersion(), resp.getStatus());
          response.headers().add(resp.headers());
        }

        if (msg instanceof HttpContent) {
          if (response != null) {
            response.content().writeBytes(((HttpContent) msg).content());
            if (msg instanceof LastHttpContent) {
              response.trailingHeaders().add(((LastHttpContent) msg).trailingHeaders());
              try {
                handshakeComplete(ctx, response);
                channel.pipeline().remove(HandshakeInboundHandler.this);
                for (; ; ) {
                  Object m = buffered.poll();
                  if (m == null) {
                    break;
                  }
                  ctx.fireChannelRead(m);
                }
              } catch (WebSocketHandshakeException e) {
                close();
                handleException(e);
              }
            }
          }
        }
      } else {
        buffered.add(msg);
      }
    }

    private void handleException(WebSocketHandshakeException e) {
      handshaking = false;
      buffered.clear();
      if (exceptionHandler != null) {
        context.executeFromIO(() -> {
          exceptionHandler.handle(e);
        });
      } else {
        log.error("Error in websocket handshake", e);
      }
    }

    private void handshakeComplete(ChannelHandlerContext ctx, FullHttpResponse response) {
      handshaking = false;
      ChannelHandler handler = ctx.pipeline().get(HttpContentDecompressor.class);
      if (handler != null) {
        // remove decompressor as its not needed anymore once connection was upgraded to websockets
        ctx.pipeline().remove(handler);
      }

      // Need to set context before constructor is called as writehandler registration needs this
      ContextImpl.setContext(context);
      WebSocketImpl webSocket = new WebSocketImpl(vertx, ClientConnection.this, supportsContinuation,
                                                  client.getOptions().getMaxWebsocketFrameSize());
      ws = webSocket;
      handshaker.finishHandshake(channel, response);
      context.executeFromIO(() -> {
        log.debug("WebSocket handshake complete");
        webSocket.setMetric(metrics().connected(metric(), webSocket));
        wsConnect.handle(webSocket);
      });
    }
  }

  public void closeHandler(Handler<Void> handler) {
    this.closeHandler = handler;
  }

  boolean isClosed() {
    return !channel.isOpen();
  }

  int getOutstandingRequestCount() {
    return requests.size();
  }

  @Override
  public synchronized void handleInterestedOpsChanged() {
    if (!isNotWritable()) {
      if (currentRequest != null) {
        currentRequest.handleDrained();
      } else if (ws != null) {
        ws.writable();
      }
    }
  }

  void handleResponse(HttpResponse resp) {
    if (resp.getStatus().code() == 100) {
      //If we get a 100 continue it will be followed by the real response later, so we don't remove it yet
      requestForResponse = requests.peek();
    } else {
      requestForResponse = requests.poll();
    }
    if (requestForResponse == null) {
      throw new IllegalStateException("No response handler");
    }
    HttpClientResponseImpl nResp = new HttpClientResponseImpl(vertx, requestForResponse, this, resp);
    currentResponse = nResp;
    requestForResponse.handleResponse(nResp);
  }

  void handleResponseChunk(Buffer buff) {
    currentResponse.handleChunk(buff);
  }

  void handleResponseEnd(LastHttpContent trailer) {
    currentResponse.handleEnd(trailer);

    // We don't signal response end for a 100-continue response as a real response will follow
    // Also we keep the connection open for an HTTP CONNECT
    if (currentResponse.statusCode() != 100 && requestForResponse.getRequest().getMethod() != HttpMethod.CONNECT) {
      listener.responseEnded(this);
    }
  }

  synchronized void handleWsFrame(WebSocketFrameInternal frame) {
    if (ws != null) {
      ws.handleFrame(frame);
    }
  }

  protected synchronized void handleClosed() {
    super.handleClosed();
    if (ws != null) {
      ws.handleClosed();
    }
  }

  protected ContextImpl getContext() {
    return super.getContext();
  }

  @Override
  protected synchronized void handleException(Throwable e) {
    super.handleException(e);
    if (currentRequest != null) {
      currentRequest.handleException(e);
    } else if (currentResponse != null) {
      currentResponse.handleException(e);
    }
  }

  synchronized void setCurrentRequest(HttpClientRequestImpl req) {
    if (currentRequest != null) {
      throw new IllegalStateException("Connection is already writing a request");
    }
    this.currentRequest = req;
    this.requests.add(req);
  }

  synchronized void endRequest() {
    if (currentRequest == null) {
      throw new IllegalStateException("No write in progress");
    }
    currentRequest = null;
    listener.requestEnded(this);
  }

  public String hostHeader() {
    return hostHeader;
  }

  @Override
  public synchronized void close() {
    if (handshaker == null) {
      super.close();
    } else {
      // make sure everything is flushed out on close
      endReadAndFlush();
      // close the websocket connection by sending a close frame.
      handshaker.close(channel, new CloseWebSocketFrame(1000, null));
    }
  }

  NetSocket createNetSocket() {
    // connection was upgraded to raw TCP socket
    NetSocketImpl socket = new NetSocketImpl(vertx, channel, context, client.getSslHelper(), true, metrics);
    Map<Channel, NetSocketImpl> connectionMap = new HashMap<>(1);
    connectionMap.put(channel, socket);

    // Flush out all pending data
    endReadAndFlush();

    // remove old http handlers and replace the old handler with one that handle plain sockets
    ChannelPipeline pipeline = channel.pipeline();
    ChannelHandler inflater = pipeline.get(HttpContentDecompressor.class);
    if (inflater != null) {
      pipeline.remove(inflater);
    }
    pipeline.remove("codec");
    pipeline.replace("handler", "handler", new VertxNetHandler(client.getVertx(), connectionMap) {
      @Override
      public void exceptionCaught(ChannelHandlerContext chctx, Throwable t) throws Exception {
        // remove from the real mapping
        client.removeChannel(channel);
        super.exceptionCaught(chctx, t);
      }

      @Override
      public void channelInactive(ChannelHandlerContext chctx) throws Exception {
        // remove from the real mapping
        client.removeChannel(channel);
        super.channelInactive(chctx);
      }

      @Override
      public void channelRead(ChannelHandlerContext chctx, Object msg) throws Exception {
        if (msg instanceof HttpContent) {
          ReferenceCountUtil.release(msg);
          return;
        }
        super.channelRead(chctx, msg);
      }
    });
    return socket;
  }
}


File: src/main/java/io/vertx/core/http/impl/HttpClientImpl.java
/*
 * Copyright (c) 2011-2013 The original author or authors
 * ------------------------------------------------------
 * All rights reserved. This program and the accompanying materials
 * are made available under the terms of the Eclipse Public License v1.0
 * and Apache License v2.0 which accompanies this distribution.
 *
 *     The Eclipse Public License is available at
 *     http://www.eclipse.org/legal/epl-v10.html
 *
 *     The Apache License v2.0 is available at
 *     http://www.opensource.org/licenses/apache2.0.php
 *
 * You may elect to redistribute this code under either of these licenses.
 */

package io.vertx.core.http.impl;

import io.netty.bootstrap.Bootstrap;
import io.netty.channel.Channel;
import io.netty.channel.ChannelFuture;
import io.netty.channel.ChannelFutureListener;
import io.netty.channel.ChannelHandlerContext;
import io.netty.channel.ChannelInitializer;
import io.netty.channel.ChannelOption;
import io.netty.channel.ChannelPipeline;
import io.netty.channel.FixedRecvByteBufAllocator;
import io.netty.channel.socket.nio.NioSocketChannel;
import io.netty.handler.codec.http.HttpClientCodec;
import io.netty.handler.codec.http.HttpContent;
import io.netty.handler.codec.http.HttpContentDecompressor;
import io.netty.handler.codec.http.HttpResponse;
import io.netty.handler.codec.http.LastHttpContent;
import io.netty.handler.ssl.SslHandler;
import io.netty.handler.timeout.IdleStateHandler;
import io.vertx.core.Future;
import io.vertx.core.Handler;
import io.vertx.core.MultiMap;
import io.vertx.core.VertxException;
import io.vertx.core.buffer.Buffer;
import io.vertx.core.http.HttpClient;
import io.vertx.core.http.HttpClientOptions;
import io.vertx.core.http.HttpClientRequest;
import io.vertx.core.http.HttpClientResponse;
import io.vertx.core.http.HttpMethod;
import io.vertx.core.http.WebSocket;
import io.vertx.core.http.WebSocketStream;
import io.vertx.core.http.WebsocketVersion;
import io.vertx.core.http.impl.ws.WebSocketFrameImpl;
import io.vertx.core.http.impl.ws.WebSocketFrameInternal;
import io.vertx.core.impl.Closeable;
import io.vertx.core.impl.ContextImpl;
import io.vertx.core.impl.VertxInternal;
import io.vertx.core.logging.Logger;
import io.vertx.core.logging.LoggerFactory;
import io.vertx.core.spi.metrics.Metrics;
import io.vertx.core.spi.metrics.HttpClientMetrics;
import io.vertx.core.net.impl.KeyStoreHelper;
import io.vertx.core.net.impl.PartialPooledByteBufAllocator;
import io.vertx.core.net.impl.SSLHelper;
import io.vertx.core.spi.metrics.MetricsProvider;

import javax.net.ssl.SSLHandshakeException;
import java.net.InetSocketAddress;
import java.net.MalformedURLException;
import java.net.URL;
import java.util.Map;
import java.util.Objects;
import java.util.concurrent.ConcurrentHashMap;

/**
 *
 * This class is thread-safe
 *
 * @author <a href="http://tfox.org">Tim Fox</a>
 */
public class HttpClientImpl implements HttpClient, MetricsProvider {

  private static final Logger log = LoggerFactory.getLogger(HttpClientImpl.class);

  private final VertxInternal vertx;
  private final HttpClientOptions options;
  private final Map<Channel, ClientConnection> connectionMap = new ConcurrentHashMap<>();
  private final ContextImpl creatingContext;
  private final ConnectionManager pool;
  private final Closeable closeHook;
  private final SSLHelper sslHelper;
  private final HttpClientMetrics metrics;
  private volatile boolean closed;

  public HttpClientImpl(VertxInternal vertx, HttpClientOptions options) {
    this.vertx = vertx;
    this.options = new HttpClientOptions(options);
    this.sslHelper = new SSLHelper(options, KeyStoreHelper.create(vertx, options.getKeyCertOptions()), KeyStoreHelper.create(vertx, options.getTrustOptions()));
    this.creatingContext = vertx.getContext();
    closeHook = completionHandler -> {
      HttpClientImpl.this.close();
      completionHandler.handle(Future.succeededFuture());
    };
    if (creatingContext != null) {
      if (creatingContext.isMultiThreadedWorkerContext()) {
        throw new IllegalStateException("Cannot use HttpClient in a multi-threaded worker verticle");
      }
      creatingContext.addCloseHook(closeHook);
    }
    pool = new ConnectionManager(options.getMaxPoolSize(), options.isKeepAlive(), options.isPipelining())  {
      protected void connect(String host, int port, Handler<ClientConnection> connectHandler, Handler<Throwable> connectErrorHandler, ContextImpl context,
                             ConnectionLifeCycleListener listener) {
        internalConnect(context, port, host, connectHandler, connectErrorHandler, listener);
      }
    };
    this.metrics = vertx.metricsSPI().createMetrics(this, options);
  }

  @Override
  public HttpClient websocket(int port, String host, String requestURI, Handler<WebSocket> wsConnect) {
    websocketStream(port, host, requestURI, null, null).handler(wsConnect);
    return this;
  }

  @Override
  public HttpClient websocket(String host, String requestURI, Handler<WebSocket> wsConnect) {
    return websocket(options.getDefaultPort(), host, requestURI, wsConnect);
  }

  @Override
  public HttpClient websocket(int port, String host, String requestURI, MultiMap headers, Handler<WebSocket> wsConnect) {
    websocketStream(port, host, requestURI, headers, null).handler(wsConnect);
    return this;
  }

  @Override
  public HttpClient websocket(String host, String requestURI, MultiMap headers, Handler<WebSocket> wsConnect) {
    return websocket(options.getDefaultPort(), host, requestURI, headers, wsConnect);
  }

  @Override
  public HttpClient websocket(int port, String host, String requestURI, MultiMap headers, WebsocketVersion version, Handler<WebSocket> wsConnect) {
    websocketStream(port, host, requestURI, headers, version, null).handler(wsConnect);
    return this;
  }

  @Override
  public HttpClient websocket(String host, String requestURI, MultiMap headers, WebsocketVersion version, Handler<WebSocket> wsConnect) {
    return websocket(options.getDefaultPort(), host, requestURI, headers, version, wsConnect);
  }

  @Override
  public HttpClient websocket(int port, String host, String requestURI, MultiMap headers, WebsocketVersion version,
                              String subProtocols, Handler<WebSocket> wsConnect) {
    websocketStream(port, host, requestURI, headers, version, subProtocols).handler(wsConnect);
    return this;
  }

  @Override
  public HttpClient websocket(String host, String requestURI, MultiMap headers, WebsocketVersion version, String subProtocols, Handler<WebSocket> wsConnect) {
    return websocket(options.getDefaultPort(), host, requestURI, headers, version, subProtocols, wsConnect);
  }

  @Override
  public HttpClient websocket(String requestURI, Handler<WebSocket> wsConnect) {
    return websocket(options.getDefaultPort(), options.getDefaultHost(), requestURI, wsConnect);
  }

  @Override
  public HttpClient websocket(String requestURI, MultiMap headers, Handler<WebSocket> wsConnect) {
    return websocket(options.getDefaultPort(), options.getDefaultHost(), requestURI, headers, wsConnect);
  }

  @Override
  public HttpClient websocket(String requestURI, MultiMap headers, WebsocketVersion version, Handler<WebSocket> wsConnect) {
    return websocket(options.getDefaultPort(), options.getDefaultHost(), requestURI, headers, version, wsConnect);
  }

  @Override
  public HttpClient websocket(String requestURI, MultiMap headers, WebsocketVersion version, String subProtocols, Handler<WebSocket> wsConnect) {
    return websocket(options.getDefaultPort(), options.getDefaultHost(), requestURI, headers, version, subProtocols, wsConnect);
  }

  @Override
  public WebSocketStream websocketStream(int port, String host, String requestURI) {
    return websocketStream(port, host, requestURI, null, null);
  }

  @Override
  public WebSocketStream websocketStream(String host, String requestURI) {
    return websocketStream(options.getDefaultPort(), host, requestURI);
  }

  @Override
  public WebSocketStream websocketStream(int port, String host, String requestURI, MultiMap headers) {
    return websocketStream(port, host, requestURI, headers, null);
  }

  @Override
  public WebSocketStream websocketStream(String host, String requestURI, MultiMap headers) {
    return websocketStream(options.getDefaultPort(), host, requestURI, headers);
  }

  @Override
  public WebSocketStream websocketStream(int port, String host, String requestURI, MultiMap headers, WebsocketVersion version) {
    return websocketStream(port, host, requestURI, headers, version, null);
  }

  @Override
  public WebSocketStream websocketStream(String host, String requestURI, MultiMap headers, WebsocketVersion version) {
    return websocketStream(options.getDefaultPort(), host, requestURI, headers, version);
  }

  @Override
  public WebSocketStream websocketStream(int port, String host, String requestURI, MultiMap headers, WebsocketVersion version,
                                         String subProtocols) {
    return new WebSocketStreamImpl(port, host, requestURI, headers, version, subProtocols);
  }

  @Override
  public WebSocketStream websocketStream(String host, String requestURI, MultiMap headers, WebsocketVersion version, String subProtocols) {
    return websocketStream(options.getDefaultPort(), host, requestURI, headers, version, subProtocols);
  }

  @Override
  public WebSocketStream websocketStream(String requestURI) {
    return websocketStream(options.getDefaultPort(), options.getDefaultHost(), requestURI);
  }

  @Override
  public WebSocketStream websocketStream(String requestURI, MultiMap headers) {
    return websocketStream(options.getDefaultPort(), options.getDefaultHost(), requestURI, headers);
  }

  @Override
  public WebSocketStream websocketStream(String requestURI, MultiMap headers, WebsocketVersion version) {
    return websocketStream(options.getDefaultPort(), options.getDefaultHost(), requestURI, headers, version);
  }

  @Override
  public WebSocketStream websocketStream(String requestURI, MultiMap headers, WebsocketVersion version, String subProtocols) {
    return websocketStream(options.getDefaultPort(), options.getDefaultHost(), requestURI, headers, version, subProtocols);
  }

  @Override
  public HttpClientRequest requestAbs(HttpMethod method, String absoluteURI, Handler<HttpClientResponse> responseHandler) {
    Objects.requireNonNull(responseHandler, "no null responseHandler accepted");
    return requestAbs(method, absoluteURI).handler(responseHandler);
  }

  @Override
  public HttpClientRequest request(HttpMethod method, int port, String host, String requestURI, Handler<HttpClientResponse> responseHandler) {
    Objects.requireNonNull(responseHandler, "no null responseHandler accepted");
    return request(method, port, host, requestURI).handler(responseHandler);
  }

  @Override
  public HttpClientRequest request(HttpMethod method, String host, String requestURI, Handler<HttpClientResponse> responseHandler) {
    return request(method, options.getDefaultPort(), host, requestURI, responseHandler);
  }

  @Override
  public HttpClientRequest request(HttpMethod method, String requestURI) {
    return request(method, options.getDefaultPort(), options.getDefaultHost(), requestURI);
  }

  @Override
  public HttpClientRequest request(HttpMethod method, String requestURI, Handler<HttpClientResponse> responseHandler) {
    return request(method, options.getDefaultPort(), options.getDefaultHost(), requestURI, responseHandler);
  }

  @Override
  public HttpClientRequest requestAbs(HttpMethod method, String absoluteURI) {
    URL url = parseUrl(absoluteURI);
    return doRequest(method, url.getHost(), url.getPort(), url.getFile(), null);
  }

  @Override
  public HttpClientRequest request(HttpMethod method, int port, String host, String requestURI) {
    return doRequest(method, host, port, requestURI, null);
  }

  @Override
  public HttpClientRequest request(HttpMethod method, String host, String requestURI) {
    return request(method, options.getDefaultPort(), host, requestURI);
  }

  @Override
  public HttpClientRequest get(int port, String host, String requestURI) {
    return request(HttpMethod.GET, port, host, requestURI);
  }

  @Override
  public HttpClientRequest get(String host, String requestURI) {
    return get(options.getDefaultPort(), host, requestURI);
  }

  @Override
  public HttpClientRequest get(int port, String host, String requestURI, Handler<HttpClientResponse> responseHandler) {
    return request(HttpMethod.GET, port, host, requestURI, responseHandler);
  }

  @Override
  public HttpClientRequest get(String host, String requestURI, Handler<HttpClientResponse> responseHandler) {
    return get(options.getDefaultPort(), host, requestURI, responseHandler);
  }

  @Override
  public HttpClientRequest get(String requestURI) {
    return request(HttpMethod.GET, requestURI);
  }

  @Override
  public HttpClientRequest get(String requestURI, Handler<HttpClientResponse> responseHandler) {
    return request(HttpMethod.GET, requestURI, responseHandler);
  }

  @Override
  public HttpClientRequest getAbs(String absoluteURI) {
    return requestAbs(HttpMethod.GET, absoluteURI);
  }

  @Override
  public HttpClientRequest getAbs(String absoluteURI, Handler<HttpClientResponse> responseHandler) {
    return requestAbs(HttpMethod.GET, absoluteURI, responseHandler);
  }

  @Override
  public HttpClient getNow(int port, String host, String requestURI, Handler<HttpClientResponse> responseHandler) {
    get(port, host, requestURI, responseHandler).end();
    return this;
  }

  @Override
  public HttpClient getNow(String host, String requestURI, Handler<HttpClientResponse> responseHandler) {
    return getNow(options.getDefaultPort(), host, requestURI, responseHandler);
  }

  @Override
  public HttpClient getNow(String requestURI, Handler<HttpClientResponse> responseHandler) {
    get(requestURI, responseHandler).end();
    return this;
  }

  @Override
  public HttpClientRequest post(int port, String host, String requestURI) {
    return request(HttpMethod.POST, port, host, requestURI);
  }

  @Override
  public HttpClientRequest post(String host, String requestURI) {
    return post(options.getDefaultPort(), host, requestURI);
  }

  @Override
  public HttpClientRequest post(int port, String host, String requestURI, Handler<HttpClientResponse> responseHandler) {
    return request(HttpMethod.POST, port, host, requestURI, responseHandler);
  }

  @Override
  public HttpClientRequest post(String host, String requestURI, Handler<HttpClientResponse> responseHandler) {
    return post(options.getDefaultPort(), host, requestURI, responseHandler);
  }

  @Override
  public HttpClientRequest post(String requestURI) {
    return request(HttpMethod.POST, requestURI);
  }

  @Override
  public HttpClientRequest post(String requestURI, Handler<HttpClientResponse> responseHandler) {
    return request(HttpMethod.POST, requestURI, responseHandler);
  }

  @Override
  public HttpClientRequest postAbs(String absoluteURI) {
    return requestAbs(HttpMethod.POST, absoluteURI);
  }

  @Override
  public HttpClientRequest postAbs(String absoluteURI, Handler<HttpClientResponse> responseHandler) {
    return requestAbs(HttpMethod.POST, absoluteURI, responseHandler);
  }

  @Override
  public HttpClientRequest head(int port, String host, String requestURI) {
    return request(HttpMethod.HEAD, port, host, requestURI);
  }

  @Override
  public HttpClientRequest head(String host, String requestURI) {
    return head(options.getDefaultPort(), host, requestURI);
  }

  @Override
  public HttpClientRequest head(int port, String host, String requestURI, Handler<HttpClientResponse> responseHandler) {
    return request(HttpMethod.HEAD, port, host, requestURI, responseHandler);
  }

  @Override
  public HttpClientRequest head(String host, String requestURI, Handler<HttpClientResponse> responseHandler) {
    return head(options.getDefaultPort(), host, requestURI, responseHandler);
  }

  @Override
  public HttpClientRequest head(String requestURI) {
    return request(HttpMethod.HEAD, requestURI);
  }

  @Override
  public HttpClientRequest head(String requestURI, Handler<HttpClientResponse> responseHandler) {
    return request(HttpMethod.HEAD, requestURI, responseHandler);
  }

  @Override
  public HttpClientRequest headAbs(String absoluteURI) {
    return requestAbs(HttpMethod.HEAD, absoluteURI);
  }

  @Override
  public HttpClientRequest headAbs(String absoluteURI, Handler<HttpClientResponse> responseHandler) {
    return requestAbs(HttpMethod.HEAD, absoluteURI, responseHandler);
  }

  @Override
  public HttpClient headNow(int port, String host, String requestURI, Handler<HttpClientResponse> responseHandler) {
    head(port, host, requestURI, responseHandler).end();
    return this;
  }

  @Override
  public HttpClient headNow(String host, String requestURI, Handler<HttpClientResponse> responseHandler) {
    return headNow(options.getDefaultPort(), host, requestURI, responseHandler);
  }

  @Override
  public HttpClient headNow(String requestURI, Handler<HttpClientResponse> responseHandler) {
    head(requestURI, responseHandler).end();
    return this;
  }

  @Override
  public HttpClientRequest options(int port, String host, String requestURI) {
    return request(HttpMethod.OPTIONS, port, host, requestURI);
  }

  @Override
  public HttpClientRequest options(String host, String requestURI) {
    return options(options.getDefaultPort(), host, requestURI);
  }

  @Override
  public HttpClientRequest options(int port, String host, String requestURI, Handler<HttpClientResponse> responseHandler) {
    return request(HttpMethod.OPTIONS, port, host, requestURI, responseHandler);
  }

  @Override
  public HttpClientRequest options(String host, String requestURI, Handler<HttpClientResponse> responseHandler) {
    return options(options.getDefaultPort(), host, requestURI, responseHandler);
  }

  @Override
  public HttpClientRequest options(String requestURI) {
    return request(HttpMethod.OPTIONS, requestURI);
  }

  @Override
  public HttpClientRequest options(String requestURI, Handler<HttpClientResponse> responseHandler) {
    return request(HttpMethod.OPTIONS, requestURI, responseHandler);
  }

  @Override
  public HttpClientRequest optionsAbs(String absoluteURI) {
    return requestAbs(HttpMethod.OPTIONS, absoluteURI);
  }

  @Override
  public HttpClientRequest optionsAbs(String absoluteURI, Handler<HttpClientResponse> responseHandler) {
    return requestAbs(HttpMethod.OPTIONS, absoluteURI, responseHandler);
  }

  @Override
  public HttpClient optionsNow(int port, String host, String requestURI, Handler<HttpClientResponse> responseHandler) {
    options(port, host, requestURI, responseHandler).end();
    return this;
  }

  @Override
  public HttpClient optionsNow(String host, String requestURI, Handler<HttpClientResponse> responseHandler) {
    return optionsNow(options.getDefaultPort(), host, requestURI, responseHandler);
  }

  @Override
  public HttpClient optionsNow(String requestURI, Handler<HttpClientResponse> responseHandler) {
    options(requestURI, responseHandler).end();
    return this;
  }

  @Override
  public HttpClientRequest put(int port, String host, String requestURI) {
    return request(HttpMethod.PUT, port, host, requestURI);
  }

  @Override
  public HttpClientRequest put(String host, String requestURI) {
    return put(options.getDefaultPort(), host, requestURI);
  }

  @Override
  public HttpClientRequest put(int port, String host, String requestURI, Handler<HttpClientResponse> responseHandler) {
    return request(HttpMethod.PUT, port, host, requestURI, responseHandler);
  }

  @Override
  public HttpClientRequest put(String host, String requestURI, Handler<HttpClientResponse> responseHandler) {
    return put(options.getDefaultPort(), host, requestURI, responseHandler);
  }

  @Override
  public HttpClientRequest put(String requestURI) {
    return request(HttpMethod.PUT, requestURI);
  }

  @Override
  public HttpClientRequest put(String requestURI, Handler<HttpClientResponse> responseHandler) {
    return request(HttpMethod.PUT, requestURI, responseHandler);
  }

  @Override
  public HttpClientRequest putAbs(String absoluteURI) {
    return requestAbs(HttpMethod.PUT, absoluteURI);
  }

  @Override
  public HttpClientRequest putAbs(String absoluteURI, Handler<HttpClientResponse> responseHandler) {
    return requestAbs(HttpMethod.PUT, absoluteURI, responseHandler);
  }

  @Override
  public HttpClientRequest delete(int port, String host, String requestURI) {
    return request(HttpMethod.DELETE, port, host, requestURI);
  }

  @Override
  public HttpClientRequest delete(String host, String requestURI) {
    return delete(options.getDefaultPort(), host, requestURI);
  }

  @Override
  public HttpClientRequest delete(int port, String host, String requestURI, Handler<HttpClientResponse> responseHandler) {
    return request(HttpMethod.DELETE, port, host, requestURI, responseHandler);
  }

  @Override
  public HttpClientRequest delete(String host, String requestURI, Handler<HttpClientResponse> responseHandler) {
    return delete(options.getDefaultPort(), host, requestURI, responseHandler);
  }

  @Override
  public HttpClientRequest delete(String requestURI) {
    return request(HttpMethod.DELETE, requestURI);
  }

  @Override
  public HttpClientRequest delete(String requestURI, Handler<HttpClientResponse> responseHandler) {
    return request(HttpMethod.DELETE, requestURI, responseHandler);
  }

  @Override
  public HttpClientRequest deleteAbs(String absoluteURI) {
    return requestAbs(HttpMethod.DELETE, absoluteURI);
  }

  @Override
  public HttpClientRequest deleteAbs(String absoluteURI, Handler<HttpClientResponse> responseHandler) {
    return requestAbs(HttpMethod.DELETE, absoluteURI, responseHandler);
  }

  @Override
  public synchronized void close() {
    checkClosed();
    pool.close();
    for (ClientConnection conn : connectionMap.values()) {
      conn.close();
    }
    if (creatingContext != null) {
      creatingContext.removeCloseHook(closeHook);
    }
    closed = true;
    metrics.close();
  }

  @Override
  public boolean isMetricsEnabled() {
    return metrics != null && metrics.isEnabled();
  }

  @Override
  public Metrics getMetrics() {
    return metrics;
  }

  HttpClientOptions getOptions() {
    return options;
  }

  void getConnection(int port, String host, Handler<ClientConnection> handler, Handler<Throwable> connectionExceptionHandler,
                     ContextImpl context) {
    pool.getConnection(port, host, handler, connectionExceptionHandler, context);
  }

  /**
   * @return the vertx, for use in package related classes only.
   */
  VertxInternal getVertx() {
    return vertx;
  }

  SSLHelper getSslHelper() {
    return sslHelper;
  }

  void removeChannel(Channel channel) {
    connectionMap.remove(channel);
  }

  HttpClientMetrics httpClientMetrics() {
    return metrics;
  }

  private void applyConnectionOptions(Bootstrap bootstrap) {
    bootstrap.option(ChannelOption.TCP_NODELAY, options.isTcpNoDelay());
    if (options.getSendBufferSize() != -1) {
      bootstrap.option(ChannelOption.SO_SNDBUF, options.getSendBufferSize());
    }
    if (options.getReceiveBufferSize() != -1) {
      bootstrap.option(ChannelOption.SO_RCVBUF, options.getReceiveBufferSize());
      bootstrap.option(ChannelOption.RCVBUF_ALLOCATOR, new FixedRecvByteBufAllocator(options.getReceiveBufferSize()));
    }
    bootstrap.option(ChannelOption.SO_LINGER, options.getSoLinger());
    if (options.getTrafficClass() != -1) {
      bootstrap.option(ChannelOption.IP_TOS, options.getTrafficClass());
    }
    bootstrap.option(ChannelOption.CONNECT_TIMEOUT_MILLIS, options.getConnectTimeout());
    bootstrap.option(ChannelOption.ALLOCATOR, PartialPooledByteBufAllocator.INSTANCE);
    bootstrap.option(ChannelOption.SO_KEEPALIVE, options.isTcpKeepAlive());
    bootstrap.option(ChannelOption.SO_REUSEADDR, options.isReuseAddress());
  }

  private void internalConnect(ContextImpl context, int port, String host, Handler<ClientConnection> connectHandler,
                               Handler<Throwable> connectErrorHandler, ConnectionLifeCycleListener listener) {
    Bootstrap bootstrap = new Bootstrap();
    bootstrap.group(context.eventLoop());
    bootstrap.channel(NioSocketChannel.class);
    sslHelper.validate(vertx);
    bootstrap.handler(new ChannelInitializer<Channel>() {
      @Override
      protected void initChannel(Channel ch) throws Exception {
        ChannelPipeline pipeline = ch.pipeline();
        if (options.isSsl()) {
          pipeline.addLast("ssl", sslHelper.createSslHandler(vertx, true, host, port));
        }

        pipeline.addLast("codec", new HttpClientCodec(4096, 8192, 8192, false, false));
        if (options.isTryUseCompression()) {
          pipeline.addLast("inflater", new HttpContentDecompressor(true));
        }
        if (options.getIdleTimeout() > 0) {
          pipeline.addLast("idle", new IdleStateHandler(0, 0, options.getIdleTimeout()));
        }
        pipeline.addLast("handler", new ClientHandler(context));
      }
    });
    applyConnectionOptions(bootstrap);
    ChannelFuture future = bootstrap.connect(new InetSocketAddress(host, port));
    future.addListener((ChannelFuture channelFuture) -> {
      Channel ch = channelFuture.channel();
      if (channelFuture.isSuccess()) {
        if (options.isSsl()) {
          // TCP connected, so now we must do the SSL handshake

          SslHandler sslHandler = ch.pipeline().get(SslHandler.class);

          io.netty.util.concurrent.Future<Channel> fut = sslHandler.handshakeFuture();
          fut.addListener(fut2 -> {
            if (fut2.isSuccess()) {
              connected(context, port, host, ch, connectHandler, connectErrorHandler, listener);
            } else {
              connectionFailed(context, ch, connectErrorHandler, new SSLHandshakeException("Failed to create SSL connection"),
                               listener);
            }
          });
        } else {
          connected(context, port, host, ch, connectHandler, connectErrorHandler, listener);
        }
      } else {
        connectionFailed(context, ch, connectErrorHandler, channelFuture.cause(), listener);
      }
    });
  }

  private URL parseUrl(String surl) {
    // Note - parsing a URL this way is slower than specifying host, port and relativeURI
    try {
      return new URL(surl);
    } catch (MalformedURLException e) {
      throw new VertxException("Invalid url: " + surl);
    }
  }

  private HttpClientRequest doRequest(HttpMethod method, String host, int port, String relativeURI, MultiMap headers) {
    Objects.requireNonNull(method, "no null method accepted");
    Objects.requireNonNull(host, "no null host accepted");
    Objects.requireNonNull(relativeURI, "no null relativeURI accepted");
    checkClosed();
    HttpClientRequest req = new HttpClientRequestImpl(this, method, host, port, relativeURI, vertx);
    if (headers != null) {
      req.headers().setAll(headers);
    }
    return req;
  }

  private synchronized void checkClosed() {
    if (closed) {
      throw new IllegalStateException("Client is closed");
    }
  }

  private void connected(ContextImpl context, int port, String host, Channel ch, Handler<ClientConnection> connectHandler,
                         Handler<Throwable> exceptionHandler,
                         ConnectionLifeCycleListener listener) {
    context.executeFromIO(() -> createConn(context, port, host, ch, connectHandler, exceptionHandler, listener));
  }

  private void createConn(ContextImpl context, int port, String host, Channel ch, Handler<ClientConnection> connectHandler,
                          Handler<Throwable> exceptionHandler,
                          ConnectionLifeCycleListener listener) {
    ClientConnection conn = new ClientConnection(vertx, HttpClientImpl.this, exceptionHandler, ch,
        options.isSsl(), host, port, context, listener, metrics);
    conn.closeHandler(v -> {
      // The connection has been closed - tell the pool about it, this allows the pool to create more
      // connections. Note the pool doesn't actually remove the connection, when the next person to get a connection
      // gets the closed on, they will check if it's closed and if so get another one.
      listener.connectionClosed(conn);
    });
    connectionMap.put(ch, conn);
    connectHandler.handle(conn);
  }

  private void connectionFailed(ContextImpl context, Channel ch, Handler<Throwable> connectionExceptionHandler,
                                Throwable t, ConnectionLifeCycleListener listener) {
    // If no specific exception handler is provided, fall back to the HttpClient's exception handler.
    // If that doesn't exist just log it
    Handler<Throwable> exHandler =
      connectionExceptionHandler == null ? log::error : connectionExceptionHandler;

    context.executeFromIO(() -> {
      listener.connectionClosed(null);
      try {
        ch.close();
      } catch (Exception ignore) {
      }
      if (exHandler != null) {
        exHandler.handle(t);
      } else {
        log.error(t);
      }
    });
  }

  private class ClientHandler extends VertxHttpHandler<ClientConnection> {
    private boolean closeFrameSent;
    private ContextImpl context;

    public ClientHandler(ContextImpl context) {
      super(vertx, HttpClientImpl.this.connectionMap);
      this.context = context;
    }

    @Override
    protected ContextImpl getContext(ClientConnection connection) {
      return context;
    }

    @Override
    protected void doMessageReceived(ClientConnection conn, ChannelHandlerContext ctx, Object msg) {
      if (conn == null) {
        return;
      }
      boolean valid = false;
      if (msg instanceof HttpResponse) {
        HttpResponse response = (HttpResponse) msg;
        conn.handleResponse(response);
        valid = true;
      }
      if (msg instanceof HttpContent) {
        HttpContent chunk = (HttpContent) msg;
        if (chunk.content().isReadable()) {
          Buffer buff = Buffer.buffer(chunk.content().slice());
          conn.handleResponseChunk(buff);
        }
        if (chunk instanceof LastHttpContent) {
          conn.handleResponseEnd((LastHttpContent)chunk);
        }
        valid = true;
      } else if (msg instanceof WebSocketFrameInternal) {
        WebSocketFrameInternal frame = (WebSocketFrameInternal) msg;
        switch (frame.type()) {
          case BINARY:
          case CONTINUATION:
          case TEXT:
            conn.handleWsFrame(frame);
            break;
          case PING:
            // Echo back the content of the PING frame as PONG frame as specified in RFC 6455 Section 5.5.2
            ctx.writeAndFlush(new WebSocketFrameImpl(FrameType.PONG, frame.getBinaryData()));
            break;
          case CLOSE:
            if (!closeFrameSent) {
              // Echo back close frame and close the connection once it was written.
              // This is specified in the WebSockets RFC 6455 Section  5.4.1
              ctx.writeAndFlush(frame).addListener(ChannelFutureListener.CLOSE);
              closeFrameSent = true;
            }
            break;
          default:
            throw new IllegalStateException("Invalid type: " + frame.type());
        }
        valid = true;
      }
      if (!valid) {
        throw new IllegalStateException("Invalid object " + msg);
      }
    }
  }

  private class WebSocketStreamImpl implements WebSocketStream {

    final int port;
    final String host;
    final String requestURI;
    final MultiMap headers;
    final WebsocketVersion version;
    final String subProtocols;
    private Handler<WebSocket> handler;
    private Handler<Throwable> exceptionHandler;
    private Handler<Void> endHandler;

    public WebSocketStreamImpl(int port, String host, String requestURI, MultiMap headers, WebsocketVersion version, String subProtocols) {
      this.port = port;
      this.host = host;
      this.requestURI = requestURI;
      this.headers = headers;
      this.version = version;
      this.subProtocols = subProtocols;
    }

    @Override
    public synchronized WebSocketStream exceptionHandler(Handler<Throwable> handler) {
      exceptionHandler = handler;
      return this;
    }

    @Override
    public synchronized WebSocketStream handler(Handler<WebSocket> handler) {
      if (this.handler == null && handler != null) {
        this.handler = handler;
        checkClosed();
        ContextImpl context = vertx.getOrCreateContext();
        Handler<Throwable> connectionExceptionHandler = exceptionHandler;
        if (connectionExceptionHandler == null) {
          connectionExceptionHandler = log::error;
        }
        Handler<WebSocket> wsConnect;
        if (endHandler != null) {
          Handler<Void> endCallback = endHandler;
          wsConnect = ws -> {
            handler.handle(ws);
            endCallback.handle(null);
          };
        } else {
          wsConnect = handler;
        }
        getConnection(port, host, conn -> {
          if (!conn.isClosed()) {
            conn.toWebSocket(requestURI, headers, version, subProtocols, options.getMaxWebsocketFrameSize(), wsConnect);
          } else {
            websocket(port, host, requestURI, headers, version, subProtocols, wsConnect);
          }
        }, connectionExceptionHandler, context);
      }
      return this;
    }

    @Override
    public synchronized WebSocketStream endHandler(Handler<Void> endHandler) {
      this.endHandler = endHandler;
      return this;
    }

    @Override
    public WebSocketStream pause() {
      return this;
    }

    @Override
    public WebSocketStream resume() {
      return this;
    }
  }

  @Override
  protected void finalize() throws Throwable {
    // Make sure this gets cleaned up if there are no more references to it
    // so as not to leave connections and resources dangling until the system is shutdown
    // which could make the JVM run out of file handles.
    close();
    super.finalize();
  }

}


File: src/main/java/io/vertx/core/http/impl/HttpClientRequestImpl.java
/*
 * Copyright (c) 2011-2013 The original author or authors
 * ------------------------------------------------------
 * All rights reserved. This program and the accompanying materials
 * are made available under the terms of the Eclipse Public License v1.0
 * and Apache License v2.0 which accompanies this distribution.
 *
 *     The Eclipse Public License is available at
 *     http://www.eclipse.org/legal/epl-v10.html
 *
 *     The Apache License v2.0 is available at
 *     http://www.opensource.org/licenses/apache2.0.php
 *
 * You may elect to redistribute this code under either of these licenses.
 */

package io.vertx.core.http.impl;

import io.netty.buffer.ByteBuf;
import io.netty.buffer.CompositeByteBuf;
import io.netty.buffer.Unpooled;
import io.netty.handler.codec.http.*;
import io.vertx.core.Handler;
import io.vertx.core.MultiMap;
import io.vertx.core.buffer.Buffer;
import io.vertx.core.http.HttpClientRequest;
import io.vertx.core.http.HttpClientResponse;
import io.vertx.core.impl.ContextImpl;
import io.vertx.core.impl.VertxInternal;
import io.vertx.core.logging.Logger;
import io.vertx.core.logging.LoggerFactory;
import io.vertx.core.net.NetSocket;
import io.vertx.core.spi.metrics.HttpClientMetrics;

import java.util.List;
import java.util.Objects;
import java.util.concurrent.TimeoutException;

import static io.vertx.core.http.HttpHeaders.*;

/**
 * This class is optimised for performance when used on the same event loop that is was passed to the handler with.
 * However it can be used safely from other threads.
 *
 * The internal state is protected using the synchronized keyword. If always used on the same event loop, then
 * we benefit from biased locking which makes the overhead of synchronized near zero.
 *
 * @author <a href="http://tfox.org">Tim Fox</a>
 */
public class HttpClientRequestImpl implements HttpClientRequest {

  private static final Logger log = LoggerFactory.getLogger(HttpClientRequestImpl.class);

  private final String host;
  private final int port;
  private final HttpClientImpl client;
  private final HttpRequest request;
  private final VertxInternal vertx;
  private final io.vertx.core.http.HttpMethod method;
  private Handler<HttpClientResponse> respHandler;
  private Handler<Void> endHandler;
  private boolean chunked;
  private Handler<Void> continueHandler;
  private ClientConnection conn;
  private Handler<Void> drainHandler;
  private Handler<Throwable> exceptionHandler;
  private boolean headWritten;
  private boolean completed;
  private ByteBuf pendingChunks;
  private int pendingMaxSize = -1;
  private boolean connecting;
  private boolean writeHead;
  private long written;
  private long currentTimeoutTimerId = -1;
  private MultiMap headers;
  private boolean exceptionOccurred;
  private long lastDataReceived;
  private Object metric;

  HttpClientRequestImpl(HttpClientImpl client, io.vertx.core.http.HttpMethod method, String host, int port,
                        String relativeURI, VertxInternal vertx) {
    this.host = host;
    this.port = port;
    this.client = client;
    this.request = new DefaultHttpRequest(HttpVersion.HTTP_1_1, toNettyHttpMethod(method), relativeURI, false);
    this.chunked = false;
    this.method = method;
    this.vertx = vertx;
  }

  @Override
  public synchronized  HttpClientRequest handler(Handler<HttpClientResponse> handler) {
    if (handler != null) {
      checkComplete();
      respHandler = checkConnect(method, handler);
    } else {
      respHandler = null;
    }
    return this;
  }

  @Override
  public HttpClientRequest pause() {
    return this;
  }

  @Override
  public HttpClientRequest resume() {
    return this;
  }

  @Override
  public synchronized HttpClientRequest endHandler(Handler<Void> endHandler) {
    if (endHandler != null) {
      checkComplete();
    }
    this.endHandler = endHandler;
    return this;
  }

  @Override
  public synchronized HttpClientRequestImpl setChunked(boolean chunked) {
    checkComplete();
    if (written > 0) {
      throw new IllegalStateException("Cannot set chunked after data has been written on request");
    }
    this.chunked = chunked;
    return this;
  }

  @Override
  public synchronized boolean isChunked() {
    return chunked;
  }

  @Override
  public io.vertx.core.http.HttpMethod method() {
    return method;
  }

  @Override
  public String uri() {
    return request.getUri();
  }

  @Override
  public synchronized MultiMap headers() {
    if (headers == null) {
      headers = new HeadersAdaptor(request.headers());
    }
    return headers;
  }

  @Override
  public synchronized HttpClientRequest putHeader(String name, String value) {
    checkComplete();
    headers().set(name, value);
    return this;
  }

  @Override
  public synchronized HttpClientRequest putHeader(String name, Iterable<String> values) {
    checkComplete();
    headers().set(name, values);
    return this;
  }

  @Override
  public synchronized HttpClientRequestImpl write(Buffer chunk) {
    checkComplete();
    checkResponseHandler();
    ByteBuf buf = chunk.getByteBuf();
    write(buf, false);
    return this;
  }

  @Override
  public synchronized HttpClientRequestImpl write(String chunk) {
    checkComplete();
    checkResponseHandler();
    return write(Buffer.buffer(chunk));
  }

  @Override
  public synchronized HttpClientRequestImpl write(String chunk, String enc) {
    Objects.requireNonNull(enc, "no null encoding accepted");
    checkComplete();
    checkResponseHandler();
    return write(Buffer.buffer(chunk, enc));
  }

  @Override
  public synchronized HttpClientRequest setWriteQueueMaxSize(int maxSize) {
    checkComplete();
    if (conn != null) {
      conn.doSetWriteQueueMaxSize(maxSize);
    } else {
      pendingMaxSize = maxSize;
    }
    return this;
  }

  @Override
  public synchronized boolean writeQueueFull() {
    checkComplete();
    return conn != null && conn.isNotWritable();
  }

  @Override
  public synchronized HttpClientRequest drainHandler(Handler<Void> handler) {
    checkComplete();
    this.drainHandler = handler;
    if (conn != null) {
      conn.getContext().runOnContext(v -> conn.handleInterestedOpsChanged());
    }
    return this;
  }

  @Override
  public synchronized HttpClientRequest exceptionHandler(Handler<Throwable> handler) {
    if (handler != null) {
      checkComplete();
      this.exceptionHandler = t -> {
        cancelOutstandingTimeoutTimer();
        handler.handle(t);
      };
    } else {
      this.exceptionHandler = null;
    }
    return this;
  }

  @Override
  public synchronized HttpClientRequest continueHandler(Handler<Void> handler) {
    checkComplete();
    this.continueHandler = handler;
    return this;
  }

  @Override
  public synchronized HttpClientRequestImpl sendHead() {
    checkComplete();
    checkResponseHandler();
    if (conn != null) {
      if (!headWritten) {
        writeHead();
      }
    } else {
      connect();
      writeHead = true;
    }
    return this;
  }

  @Override
  public synchronized void end(String chunk) {
    end(Buffer.buffer(chunk));
  }

  @Override
  public synchronized void end(String chunk, String enc) {
    Objects.requireNonNull(enc, "no null encoding accepted");
    end(Buffer.buffer(chunk, enc));
  }

  @Override
  public synchronized void end(Buffer chunk) {
    checkComplete();
    checkResponseHandler();
    if (!chunked && !contentLengthSet()) {
      headers().set(CONTENT_LENGTH, String.valueOf(chunk.length()));
    }
    write(chunk.getByteBuf(), true);
  }

  @Override
  public synchronized void end() {
    checkComplete();
    checkResponseHandler();
    write(Unpooled.EMPTY_BUFFER, true);
  }

  @Override
  public synchronized HttpClientRequest setTimeout(long timeoutMs) {
    cancelOutstandingTimeoutTimer();
    currentTimeoutTimerId = client.getVertx().setTimer(timeoutMs, id ->  handleTimeout(timeoutMs));
    return this;
  }

  @Override
  public synchronized HttpClientRequest putHeader(CharSequence name, CharSequence value) {
    checkComplete();
    headers().set(name, value);
    return this;
  }

  @Override
  public synchronized HttpClientRequest putHeader(CharSequence name, Iterable<CharSequence> values) {
    checkComplete();
    headers().set(name, values);
    return this;
  }

  synchronized void dataReceived() {
    if (currentTimeoutTimerId != -1) {
      lastDataReceived = System.currentTimeMillis();
    }
  }

  synchronized void handleDrained() {
    if (drainHandler != null) {
      drainHandler.handle(null);
    }
  }

  synchronized void handleException(Throwable t) {
    cancelOutstandingTimeoutTimer();
    exceptionOccurred = true;
    getExceptionHandler().handle(t);
  }

  synchronized void handleResponse(HttpClientResponseImpl resp) {
    // If an exception occurred (e.g. a timeout fired) we won't receive the response.
    if (!exceptionOccurred) {
      cancelOutstandingTimeoutTimer();
      try {
        if (resp.statusCode() == 100) {
          if (continueHandler != null) {
            continueHandler.handle(null);
          }
        } else {
          if (respHandler != null) {
            respHandler.handle(resp);
          }
          if (endHandler != null) {
            endHandler.handle(null);
          }
        }
      } catch (Throwable t) {
        handleException(t);
      }
    }
  }

  synchronized HttpRequest getRequest() {
    return request;
  }

  private Handler<HttpClientResponse> checkConnect(io.vertx.core.http.HttpMethod method, Handler<HttpClientResponse> handler) {
    if (method == io.vertx.core.http.HttpMethod.CONNECT) {
      // special handling for CONNECT
      handler = connectHandler(handler);
    }
    return handler;
  }

  private Handler<HttpClientResponse> connectHandler(Handler<HttpClientResponse> responseHandler) {
    Objects.requireNonNull(responseHandler, "no null responseHandler accepted");
    return resp -> {
      HttpClientResponse response;
      if (resp.statusCode() == 200) {
        // connect successful force the modification of the ChannelPipeline
        // beside this also pause the socket for now so the user has a chance to register its dataHandler
        // after received the NetSocket
        NetSocket socket = resp.netSocket();
        socket.pause();

        response = new HttpClientResponse() {
          private boolean resumed;

          @Override
          public int statusCode() {
            return resp.statusCode();
          }

          @Override
          public String statusMessage() {
            return resp.statusMessage();
          }

          @Override
          public MultiMap headers() {
            return resp.headers();
          }

          @Override
          public String getHeader(String headerName) {
            return resp.getHeader(headerName);
          }

          @Override
          public String getTrailer(String trailerName) {
            return resp.getTrailer(trailerName);
          }

          @Override
          public MultiMap trailers() {
            return resp.trailers();
          }

          @Override
          public List<String> cookies() {
            return resp.cookies();
          }

          @Override
          public HttpClientResponse bodyHandler(Handler<Buffer> bodyHandler) {
            resp.bodyHandler(bodyHandler);
            return this;
          }

          @Override
          public synchronized NetSocket netSocket() {
            if (!resumed) {
              resumed = true;
              ContextImpl ctx = vertx.getContext();
              System.out.println("in netSocket() ctx is " + ctx);
              ctx.runOnContext((v) -> socket.resume()); // resume the socket now as the user had the chance to register a dataHandler
            }
            return socket;
          }

          @Override
          public HttpClientResponse endHandler(Handler<Void> endHandler) {
            resp.endHandler(endHandler);
            return this;
          }

          @Override
          public HttpClientResponse handler(Handler<Buffer> handler) {
            resp.handler(handler);
            return this;
          }

          @Override
          public HttpClientResponse pause() {
            resp.pause();
            return this;
          }

          @Override
          public HttpClientResponse resume() {
            resp.resume();
            return this;
          }

          @Override
          public HttpClientResponse exceptionHandler(Handler<Throwable> handler) {
            resp.exceptionHandler(handler);
            return this;
          }
        };
      } else {
        response = resp;
      }
      responseHandler.handle(response);
    };
  }

  private Handler<Throwable> getExceptionHandler() {
    return exceptionHandler != null ? exceptionHandler : log::error;
  }

  private void cancelOutstandingTimeoutTimer() {
    if (currentTimeoutTimerId != -1) {
      client.getVertx().cancelTimer(currentTimeoutTimerId);
      currentTimeoutTimerId = -1;
    }
  }

  private void handleTimeout(long timeoutMs) {
    if (lastDataReceived == 0) {
      timeout(timeoutMs);
    } else {
      long now = System.currentTimeMillis();
      long timeSinceLastData = now - lastDataReceived;
      if (timeSinceLastData >= timeoutMs) {
        timeout(timeoutMs);
      } else {
        // reschedule
        lastDataReceived = 0;
        setTimeout(timeoutMs - timeSinceLastData);
      }
    }
  }

  private void timeout(long timeoutMs) {
    handleException(new TimeoutException("The timeout period of " + timeoutMs + "ms has been exceeded"));
  }

  private synchronized void connect() {
    if (!connecting) {
      // We defer actual connection until the first part of body is written or end is called
      // This gives the user an opportunity to set an exception handler before connecting so
      // they can capture any exceptions on connection
      client.getConnection(port, host, conn -> {
        synchronized (this) {
          if (exceptionOccurred) {
            // The request already timed out before it has left the pool waiter queue
            // So return it
            conn.close();
          } else if (!conn.isClosed()) {
            connected(conn);
          } else {
            // The connection has been closed - closed connections can be in the pool
            // Get another connection - Note that we DO NOT call connectionClosed() on the pool at this point
            // that is done asynchronously in the connection closeHandler()
            connect();
          }
        }
      }, exceptionHandler, vertx.getOrCreateContext());

      connecting = true;
    }
  }

  private void connected(ClientConnection conn) {
    conn.setCurrentRequest(this);
    this.conn = conn;
    this.metric = client.httpClientMetrics().requestBegin(conn.metric(), conn.localAddress(), conn.remoteAddress(), this);

    // If anything was written or the request ended before we got the connection, then
    // we need to write it now

    if (pendingMaxSize != -1) {
      conn.doSetWriteQueueMaxSize(pendingMaxSize);
    }

    if (pendingChunks != null) {
      ByteBuf pending = pendingChunks;
      pendingChunks = null;

      if (completed) {
        // we also need to write the head so optimize this and write all out in once
        writeHeadWithContent(pending, true);

        conn.reportBytesWritten(written);

        if (respHandler != null) {
          conn.endRequest();
        }
      } else {
        writeHeadWithContent(pending, false);
      }
    } else {
      if (completed) {
        // we also need to write the head so optimize this and write all out in once
        writeHeadWithContent(Unpooled.EMPTY_BUFFER, true);

        conn.reportBytesWritten(written);

        if (respHandler != null) {
          conn.endRequest();
        }
      } else {
        if (writeHead) {
          writeHead();
        }
      }
    }
  }

  void reportResponseEnd(HttpClientResponseImpl resp) {
    HttpClientMetrics metrics = client.httpClientMetrics();
    if (metrics.isEnabled()) {
      metrics.responseEnd(metric, resp);
    }
  }


  private boolean contentLengthSet() {
    return headers != null && request.headers().contains(CONTENT_LENGTH);
  }

  private void writeHead() {
    prepareHeaders();
    conn.writeToChannel(request);
    headWritten = true;
  }

  private void writeHeadWithContent(ByteBuf buf, boolean end) {
    prepareHeaders();
    if (end) {
      conn.writeToChannel(new AssembledFullHttpRequest(request, buf));
    } else {
      conn.writeToChannel(new AssembledHttpRequest(request, buf));
    }
    headWritten = true;
  }

  private void prepareHeaders() {
    HttpHeaders headers = request.headers();
    headers.remove(TRANSFER_ENCODING);
    if (!headers.contains(HOST)) {
      request.headers().set(HOST, conn.hostHeader());
    }
    if (chunked) {
      HttpHeaders.setTransferEncodingChunked(request);
    }
    if (client.getOptions().isTryUseCompression() && request.headers().get(ACCEPT_ENCODING) == null) {
      // if compression should be used but nothing is specified by the user support deflate and gzip.
      request.headers().set(ACCEPT_ENCODING, DEFLATE_GZIP);
    }
  }

  private void write(ByteBuf buff, boolean end) {
    int readableBytes = buff.readableBytes();
    if (readableBytes == 0 && !end) {
      // nothing to write to the connection just return
      return;
    }

    if (end) {
      completed = true;
    }
    if (!end && !chunked && !contentLengthSet()) {
      throw new IllegalStateException("You must set the Content-Length header to be the total size of the message "
              + "body BEFORE sending any data if you are not using HTTP chunked encoding.");
    }

    written += buff.readableBytes();
    if (conn == null) {
      if (pendingChunks == null) {
        pendingChunks = buff;
      } else {
        CompositeByteBuf pending;
        if (pendingChunks instanceof CompositeByteBuf) {
          pending = (CompositeByteBuf) pendingChunks;
        } else {
          pending = Unpooled.compositeBuffer();
          pending.addComponent(pendingChunks).writerIndex(pendingChunks.writerIndex());
          pendingChunks = pending;
        }
        pending.addComponent(buff).writerIndex(pending.writerIndex() + buff.writerIndex());
      }
      connect();
    } else {
      if (!headWritten) {
        writeHeadWithContent(buff, end);
      } else {
        if (end) {
          if (buff.isReadable()) {
            conn.writeToChannel(new DefaultLastHttpContent(buff, false));
          } else {
            conn.writeToChannel(LastHttpContent.EMPTY_LAST_CONTENT);
          }
        } else {
          conn.writeToChannel(new DefaultHttpContent(buff));
        }
      }
      if (end) {
        conn.reportBytesWritten(written);

        if (respHandler != null) {
          conn.endRequest();
        }
      }
    }
  }

  private void checkComplete() {
    if (completed) {
      throw new IllegalStateException("Request already complete");
    }
  }

  private void checkResponseHandler() {
    if (respHandler == null) {
      throw new IllegalStateException("You must set an handler for the HttpClientResponse before connecting");
    }
  }

  private HttpMethod toNettyHttpMethod(io.vertx.core.http.HttpMethod method) {
    switch (method) {
      case CONNECT: {
        return HttpMethod.CONNECT;
      }
      case GET: {
        return HttpMethod.GET;
      }
      case PUT: {
        return HttpMethod.PUT;
      }
      case POST: {
        return HttpMethod.POST;
      }
      case DELETE: {
        return HttpMethod.DELETE;
      }
      case HEAD: {
        return HttpMethod.HEAD;
      }
      case OPTIONS: {
        return HttpMethod.OPTIONS;
      }
      case TRACE: {
        return HttpMethod.TRACE;
      }
      case PATCH: {
        return HttpMethod.PATCH;
      }
      default: throw new IllegalArgumentException();
    }
  }

}


File: src/main/java/io/vertx/core/http/impl/HttpServerImpl.java
/*
 * Copyright (c) 2011-2013 The original author or authors
 * ------------------------------------------------------
 * All rights reserved. This program and the accompanying materials
 * are made available under the terms of the Eclipse Public License v1.0
 * and Apache License v2.0 which accompanies this distribution.
 *
 *     The Eclipse Public License is available at
 *     http://www.eclipse.org/legal/epl-v10.html
 *
 *     The Apache License v2.0 is available at
 *     http://www.opensource.org/licenses/apache2.0.php
 *
 * You may elect to redistribute this code under either of these licenses.
 */

package io.vertx.core.http.impl;

import io.netty.bootstrap.ServerBootstrap;
import io.netty.channel.*;
import io.netty.channel.group.ChannelGroup;
import io.netty.channel.group.ChannelGroupFuture;
import io.netty.channel.group.DefaultChannelGroup;
import io.netty.channel.socket.nio.NioServerSocketChannel;
import io.netty.handler.codec.http.*;
import io.netty.handler.codec.http.HttpHeaders;
import io.netty.handler.codec.http.HttpMethod;
import io.netty.handler.codec.http.websocketx.WebSocketHandshakeException;
import io.netty.handler.codec.http.websocketx.WebSocketServerHandshaker;
import io.netty.handler.codec.http.websocketx.WebSocketServerHandshakerFactory;
import io.netty.handler.codec.http.websocketx.WebSocketVersion;
import io.netty.handler.ssl.SslHandler;
import io.netty.handler.stream.ChunkedWriteHandler;
import io.netty.handler.timeout.IdleStateHandler;
import io.netty.util.CharsetUtil;
import io.netty.util.concurrent.GlobalEventExecutor;
import io.vertx.core.AsyncResult;
import io.vertx.core.AsyncResultHandler;
import io.vertx.core.Future;
import io.vertx.core.Handler;
import io.vertx.core.http.*;
import io.vertx.core.http.impl.cgbystrom.FlashPolicyHandler;
import io.vertx.core.http.impl.ws.WebSocketFrameImpl;
import io.vertx.core.http.impl.ws.WebSocketFrameInternal;
import io.vertx.core.impl.Closeable;
import io.vertx.core.impl.ContextImpl;
import io.vertx.core.impl.VertxInternal;
import io.vertx.core.logging.Logger;
import io.vertx.core.logging.LoggerFactory;
import io.vertx.core.net.impl.*;
import io.vertx.core.spi.metrics.HttpServerMetrics;
import io.vertx.core.spi.metrics.Metrics;
import io.vertx.core.spi.metrics.MetricsProvider;
import io.vertx.core.streams.ReadStream;

import java.net.InetAddress;
import java.net.InetSocketAddress;
import java.net.URI;
import java.net.URISyntaxException;
import java.util.Map;
import java.util.concurrent.ConcurrentHashMap;

import static io.netty.handler.codec.http.HttpResponseStatus.*;
import static io.netty.handler.codec.http.HttpVersion.HTTP_1_1;

/**
 * This class is thread-safe
 *
 * @author <a href="http://tfox.org">Tim Fox</a>
 */
public class HttpServerImpl implements HttpServer, Closeable, MetricsProvider {

  private static final Logger log = LoggerFactory.getLogger(HttpServerImpl.class);

  private final HttpServerOptions options;
  private final VertxInternal vertx;
  private final SSLHelper sslHelper;
  private final ContextImpl creatingContext;
  private final Map<Channel, ServerConnection> connectionMap = new ConcurrentHashMap<>();
  private final VertxEventLoopGroup availableWorkers = new VertxEventLoopGroup();
  private final HandlerManager<HttpServerRequest> reqHandlerManager = new HandlerManager<>(availableWorkers);
  private final HandlerManager<ServerWebSocket> wsHandlerManager = new HandlerManager<>(availableWorkers);
  private final ServerWebSocketStreamImpl wsStream = new ServerWebSocketStreamImpl();
  private final HttpServerRequestStreamImpl requestStream = new HttpServerRequestStreamImpl();
  private final String subProtocols;
  private String serverOrigin;

  private ChannelGroup serverChannelGroup;
  private volatile boolean listening;
  private ChannelFuture bindFuture;
  private ServerID id;
  private HttpServerImpl actualServer;
  private ContextImpl listenContext;
  private HttpServerMetrics metrics;

  public HttpServerImpl(VertxInternal vertx, HttpServerOptions options) {
    this.options = new HttpServerOptions(options);
    this.vertx = vertx;
    this.creatingContext = vertx.getContext();
    if (creatingContext != null) {
      if (creatingContext.isMultiThreadedWorkerContext()) {
        throw new IllegalStateException("Cannot use HttpServer in a multi-threaded worker verticle");
      }
      creatingContext.addCloseHook(this);
    }
    this.sslHelper = new SSLHelper(options, KeyStoreHelper.create(vertx, options.getKeyCertOptions()), KeyStoreHelper.create(vertx, options.getTrustOptions()));
    this.subProtocols = options.getWebsocketSubProtocols();
  }

  @Override
  public synchronized HttpServer requestHandler(Handler<HttpServerRequest> handler) {
    requestStream.handler(handler);
    return this;
  }

  @Override
  public HttpServerRequestStream requestStream() {
    return requestStream;
  }

  @Override
  public HttpServer websocketHandler(Handler<ServerWebSocket> handler) {
    websocketStream().handler(handler);
    return this;
  }

  @Override
  public Handler<HttpServerRequest> requestHandler() {
    return requestStream.handler();
  }

  @Override
  public Handler<ServerWebSocket> websocketHandler() {
    return wsStream.handler();
  }

  @Override
  public ServerWebSocketStream websocketStream() {
    return wsStream;
  }

  @Override
  public HttpServer listen() {
    return listen(options.getPort(), options.getHost(), null);
  }

  @Override
  public HttpServer listen(Handler<AsyncResult<HttpServer>> listenHandler) {
    return listen(options.getPort(), options.getHost(), listenHandler);
  }

  @Override
  public HttpServer listen(int port, String host) {
    return listen(port, host, null);
  }

  @Override
  public HttpServer listen(int port) {
    return listen(port, "0.0.0.0", null);
  }

  @Override
  public HttpServer listen(int port, Handler<AsyncResult<HttpServer>> listenHandler) {
    return listen(port, "0.0.0.0", listenHandler);
  }


  public synchronized HttpServer listen(int port, String host, Handler<AsyncResult<HttpServer>> listenHandler) {
    if (requestStream.handler() == null && wsStream.handler() == null) {
      throw new IllegalStateException("Set request or websocket handler first");
    }
    if (listening) {
      throw new IllegalStateException("Already listening");
    }
    listenContext = vertx.getOrCreateContext();
    listening = true;
    serverOrigin = (options.isSsl() ? "https" : "http") + "://" + host + ":" + port;
    synchronized (vertx.sharedHttpServers()) {
      id = new ServerID(port, host);
      HttpServerImpl shared = vertx.sharedHttpServers().get(id);
      if (shared == null) {
        serverChannelGroup = new DefaultChannelGroup("vertx-acceptor-channels", GlobalEventExecutor.INSTANCE);
        ServerBootstrap bootstrap = new ServerBootstrap();
        bootstrap.group(availableWorkers);
        bootstrap.channel(NioServerSocketChannel.class);
        applyConnectionOptions(bootstrap);
        sslHelper.validate(vertx);
        bootstrap.childHandler(new ChannelInitializer<Channel>() {
            @Override
            protected void initChannel(Channel ch) throws Exception {
              if (requestStream.isPaused() || wsStream.isPaused()) {
                ch.close();
                return;
              }
              ChannelPipeline pipeline = ch.pipeline();
              if (sslHelper.isSSL()) {
                pipeline.addLast("ssl", sslHelper.createSslHandler(vertx, false));
              }
              pipeline.addLast("flashpolicy", new FlashPolicyHandler());
              pipeline.addLast("httpDecoder", new HttpRequestDecoder(4096, 8192, 8192, false));
              pipeline.addLast("httpEncoder", new VertxHttpResponseEncoder());
              if (options.isCompressionSupported()) {
                pipeline.addLast("deflater", new HttpChunkContentCompressor());
              }
              if (sslHelper.isSSL() || options.isCompressionSupported()) {
                // only add ChunkedWriteHandler when SSL is enabled otherwise it is not needed as FileRegion is used.
                pipeline.addLast("chunkedWriter", new ChunkedWriteHandler());       // For large file / sendfile support
              }
              if (options.getIdleTimeout() > 0) {
                pipeline.addLast("idle", new IdleStateHandler(0, 0, options.getIdleTimeout()));
              }
              pipeline.addLast("handler", new ServerHandler());
            }
        });

        addHandlers(this, listenContext);
        try {
          bindFuture = bootstrap.bind(new InetSocketAddress(InetAddress.getByName(host), port));
          Channel serverChannel = bindFuture.channel();
          serverChannelGroup.add(serverChannel);
          bindFuture.addListener(channelFuture -> {
              if (!channelFuture.isSuccess()) {
                vertx.sharedHttpServers().remove(id);
              } else {
                metrics = vertx.metricsSPI().createMetrics(this, new SocketAddressImpl(port, host), options);
              }
            });
        } catch (final Throwable t) {
          // Make sure we send the exception back through the handler (if any)
          if (listenHandler != null) {
            vertx.runOnContext(v -> listenHandler.handle(Future.failedFuture(t)));
          } else {
            // No handler - log so user can see failure
            log.error(t);
          }
          listening = false;
          return this;
        }
        vertx.sharedHttpServers().put(id, this);
        actualServer = this;
      } else {
        // Server already exists with that host/port - we will use that
        actualServer = shared;
        addHandlers(actualServer, listenContext);
        metrics = vertx.metricsSPI().createMetrics(this, new SocketAddressImpl(port, host), options);
      }
      actualServer.bindFuture.addListener(future -> {
        if (listenHandler != null) {
          final AsyncResult<HttpServer> res;
          if (future.isSuccess()) {
            res = Future.succeededFuture(HttpServerImpl.this);
          } else {
            res = Future.failedFuture(future.cause());
            listening = false;
          }
          // FIXME - workaround for https://github.com/netty/netty/issues/2586
          // If listen already succeeded on a different event loop, and then addListener is called again
          // on the completed future from a different event loop then the handler will be called on the original
          // event loop not on the when that called addListener.
          // To reproduce set the boolean parameter on execute (below) to true.
          // Then run Httptest.testTwoServersSameAddressDifferentContext()
          try {
            listenContext.runOnContext((v) -> listenHandler.handle(res));
          } catch (Exception e) {
            e.printStackTrace();
          }
        } else if (!future.isSuccess()) {
          listening  = false;
          // No handler - log so user can see failure
          log.error(future.cause());
        }
      });
    }
    return this;
  }

  @Override
  public void close() {
    close(null);
  }

  @Override
  public synchronized void close(Handler<AsyncResult<Void>> done) {
    if (wsStream.endHandler() != null || requestStream.endHandler() != null) {
      Handler<Void> wsEndHandler = wsStream.endHandler();
      wsStream.endHandler(null);
      Handler<Void> requestEndHandler = requestStream.endHandler();
      requestStream.endHandler(null);
      Handler<AsyncResult<Void>> next = done;
      done = new AsyncResultHandler<Void>() {
        @Override
        public void handle(AsyncResult<Void> event) {
          if (event.succeeded()) {
            if (wsEndHandler != null) {
              wsEndHandler.handle(event.result());
            }
            if (requestEndHandler != null) {
              requestEndHandler.handle(event.result());
            }
          }
          if (next != null) {
            next.handle(event);
          }
        }
      };
    }

    ContextImpl context = vertx.getOrCreateContext();
    if (!listening) {
      executeCloseDone(context, done, null);
      return;
    }
    listening = false;

    synchronized (vertx.sharedHttpServers()) {

      if (actualServer != null) {

        if (requestStream.handler() != null) {
          actualServer.reqHandlerManager.removeHandler(requestStream.handler(), listenContext);
        }
        if (wsStream.handler() != null) {
          actualServer.wsHandlerManager.removeHandler(wsStream.handler(), listenContext);
        }

        if (actualServer.reqHandlerManager.hasHandlers() || actualServer.wsHandlerManager.hasHandlers()) {
          // The actual server still has handlers so we don't actually close it
          if (done != null) {
            executeCloseDone(context, done, null);
          }
        } else {
          // No Handlers left so close the actual server
          // The done handler needs to be executed on the context that calls close, NOT the context
          // of the actual server
          actualServer.actualClose(context, done);
        }
      }
    }
    if (creatingContext != null) {
      creatingContext.removeCloseHook(this);
    }
  }

  @Override
  public Metrics getMetrics() {
    return metrics;
  }

  @Override
  public boolean isMetricsEnabled() {
    return metrics != null && metrics.isEnabled();
  }

  SSLHelper getSslHelper() {
    return sslHelper;
  }

  void removeChannel(Channel channel) {
    connectionMap.remove(channel);
  }

  private void applyConnectionOptions(ServerBootstrap bootstrap) {
    bootstrap.childOption(ChannelOption.TCP_NODELAY, options.isTcpNoDelay());
    if (options.getSendBufferSize() != -1) {
      bootstrap.childOption(ChannelOption.SO_SNDBUF, options.getSendBufferSize());
    }
    if (options.getReceiveBufferSize() != -1) {
      bootstrap.childOption(ChannelOption.SO_RCVBUF, options.getReceiveBufferSize());
      bootstrap.childOption(ChannelOption.RCVBUF_ALLOCATOR, new FixedRecvByteBufAllocator(options.getReceiveBufferSize()));
    }

    bootstrap.option(ChannelOption.SO_LINGER, options.getSoLinger());
    if (options.getTrafficClass() != -1) {
      bootstrap.childOption(ChannelOption.IP_TOS, options.getTrafficClass());
    }
    bootstrap.childOption(ChannelOption.ALLOCATOR, PartialPooledByteBufAllocator.INSTANCE);

    bootstrap.childOption(ChannelOption.SO_KEEPALIVE, options.isTcpKeepAlive());
    bootstrap.option(ChannelOption.SO_REUSEADDR, options.isReuseAddress());
    bootstrap.option(ChannelOption.SO_BACKLOG, options.getAcceptBacklog());
  }


  private void addHandlers(HttpServerImpl server, ContextImpl context) {
    if (requestStream.handler() != null) {
      server.reqHandlerManager.addHandler(requestStream.handler(), context);
    }
    if (wsStream.handler() != null) {
      server.wsHandlerManager.addHandler(wsStream.handler(), context);
    }
  }

  private void actualClose(final ContextImpl closeContext, final Handler<AsyncResult<Void>> done) {
    if (id != null) {
      vertx.sharedHttpServers().remove(id);
    }

    ContextImpl currCon = vertx.getContext();

    for (ServerConnection conn : connectionMap.values()) {
      conn.close();
    }

    // Sanity check
    if (vertx.getContext() != currCon) {
      throw new IllegalStateException("Context was changed");
    }

    if (metrics != null) {
      metrics.close();
    }

    ChannelGroupFuture fut = serverChannelGroup.close();
    fut.addListener(cgf -> executeCloseDone(closeContext, done, fut.cause()));
  }

  private void executeCloseDone(final ContextImpl closeContext, final Handler<AsyncResult<Void>> done, final Exception e) {
    if (done != null) {
      closeContext.runOnContext((v) -> done.handle(Future.failedFuture(e)));
    }
  }

  public class ServerHandler extends VertxHttpHandler<ServerConnection> {
    private boolean closeFrameSent;

    public ServerHandler() {
      super(vertx, HttpServerImpl.this.connectionMap);
    }

    private void sendError(CharSequence err, HttpResponseStatus status, Channel ch) {
      FullHttpResponse resp = new DefaultFullHttpResponse(HTTP_1_1, status);
      if (status.code() == METHOD_NOT_ALLOWED.code()) {
        // SockJS requires this
        resp.headers().set(io.vertx.core.http.HttpHeaders.ALLOW, io.vertx.core.http.HttpHeaders.GET);
      }
      if (err != null) {
        resp.content().writeBytes(err.toString().getBytes(CharsetUtil.UTF_8));
        HttpHeaders.setContentLength(resp, err.length());
      } else {
        HttpHeaders.setContentLength(resp, 0);
      }

      ch.writeAndFlush(resp);
    }

    FullHttpRequest wsRequest;

    @Override
    protected void doMessageReceived(ServerConnection conn, ChannelHandlerContext ctx, Object msg) throws Exception {
      Channel ch = ctx.channel();

      if (msg instanceof HttpRequest) {
        final HttpRequest request = (HttpRequest) msg;

        if (log.isTraceEnabled()) log.trace("Server received request: " + request.getUri());

        if (HttpHeaders.is100ContinueExpected(request)) {
          ch.writeAndFlush(new DefaultFullHttpResponse(HTTP_1_1, CONTINUE));
        }

        if (request.headers().contains(io.vertx.core.http.HttpHeaders.UPGRADE, io.vertx.core.http.HttpHeaders.WEBSOCKET, true)) {
          // As a fun part, Firefox 6.0.2 supports Websockets protocol '7'. But,
          // it doesn't send a normal 'Connection: Upgrade' header. Instead it
          // sends: 'Connection: keep-alive, Upgrade'. Brilliant.
          String connectionHeader = request.headers().get(io.vertx.core.http.HttpHeaders.CONNECTION);
          if (connectionHeader == null || !connectionHeader.toLowerCase().contains("upgrade")) {
            sendError("\"Connection\" must be \"Upgrade\".", BAD_REQUEST, ch);
            return;
          }

          if (request.getMethod() != HttpMethod.GET) {
            sendError(null, METHOD_NOT_ALLOWED, ch);
            return;
          }

          if (wsRequest == null) {
            if (request instanceof FullHttpRequest) {
              handshake((FullHttpRequest) request, ch, ctx);
            } else {
              wsRequest = new DefaultFullHttpRequest(request.getProtocolVersion(), request.getMethod(), request.getUri());
              wsRequest.headers().set(request.headers());
            }
          }
        } else {
          //HTTP request
          if (conn == null) {
            HandlerHolder<HttpServerRequest> reqHandler = reqHandlerManager.chooseHandler(ch.eventLoop());
            if (reqHandler != null) {
              createConnAndHandle(reqHandler, ch, (HttpRequest)msg, null);
            }
          } else {
            conn.handleMessage(msg);
          }
        }
      } else if (msg instanceof WebSocketFrameInternal) {
        //Websocket frame
        WebSocketFrameInternal wsFrame = (WebSocketFrameInternal)msg;
        switch (wsFrame.type()) {
          case BINARY:
          case CONTINUATION:
          case TEXT:
            if (conn != null) {
              conn.handleMessage(msg);
            }
            break;
          case PING:
            // Echo back the content of the PING frame as PONG frame as specified in RFC 6455 Section 5.5.2
            ch.writeAndFlush(new WebSocketFrameImpl(FrameType.PONG, wsFrame.getBinaryData()));
            break;
          case CLOSE:
            if (!closeFrameSent) {
              // Echo back close frame and close the connection once it was written.
              // This is specified in the WebSockets RFC 6455 Section  5.4.1
              ch.writeAndFlush(wsFrame).addListener(ChannelFutureListener.CLOSE);
              closeFrameSent = true;
            }
            break;
          default:
            throw new IllegalStateException("Invalid type: " + wsFrame.type());
        }
      } else if (msg instanceof HttpContent) {
        if (wsRequest != null) {
          wsRequest.content().writeBytes(((HttpContent) msg).content());
          if (msg instanceof LastHttpContent) {
            FullHttpRequest req = wsRequest;
            wsRequest = null;
            handshake(req, ch, ctx);
            return;
          }
        }
        if (conn != null) {
          conn.handleMessage(msg);
        }
      } else {
        throw new IllegalStateException("Invalid message " + msg);
      }
    }

    private String getWebSocketLocation(ChannelPipeline pipeline, FullHttpRequest req) throws Exception {
      String prefix;
      if (pipeline.get(SslHandler.class) == null) {
        prefix = "ws://";
      } else {
        prefix = "wss://";
      }
      URI uri = new URI(req.getUri());
      String path = uri.getRawPath();
      String loc =  prefix + HttpHeaders.getHost(req) + path;
      String query = uri.getRawQuery();
      if (query != null) {
        loc += "?" + query;
      }
      return loc;
    }

    private void createConnAndHandle(HandlerHolder<HttpServerRequest> reqHandler, Channel ch, HttpRequest request,
                                     WebSocketServerHandshaker shake) {
      ServerConnection conn = new ServerConnection(vertx, HttpServerImpl.this, ch, reqHandler.context, serverOrigin, shake, metrics);
      conn.requestHandler(reqHandler.handler);
      connectionMap.put(ch, conn);
      reqHandler.context.executeFromIO(() -> {
        conn.setMetric(metrics.connected(conn.remoteAddress()));
        conn.handleMessage(request);
      });
    }

    private void handshake(FullHttpRequest request, Channel ch, ChannelHandlerContext ctx) throws Exception {

      WebSocketServerHandshakerFactory factory =
          new WebSocketServerHandshakerFactory(getWebSocketLocation(ch.pipeline(), request), subProtocols, false,
                                               options.getMaxWebsocketFrameSize());
      WebSocketServerHandshaker shake = factory.newHandshaker(request);

      if (shake == null) {
        log.error("Unrecognised websockets handshake");
        WebSocketServerHandshakerFactory.sendUnsupportedVersionResponse(ch);
        return;
      }
      HandlerHolder<ServerWebSocket> wsHandler = wsHandlerManager.chooseHandler(ch.eventLoop());

      if (wsHandler == null) {
        HandlerHolder<HttpServerRequest> reqHandler = reqHandlerManager.chooseHandler(ch.eventLoop());
        if (reqHandler != null) {
          createConnAndHandle(reqHandler, ch, request, shake);
        }
      } else {

        wsHandler.context.executeFromIO(() -> {
          URI theURI;
          try {
            theURI = new URI(request.getUri());
          } catch (URISyntaxException e2) {
            throw new IllegalArgumentException("Invalid uri " + request.getUri()); //Should never happen
          }

          ServerConnection wsConn = new ServerConnection(vertx, HttpServerImpl.this, ch, wsHandler.context,
            serverOrigin, shake, metrics);
          wsConn.setMetric(metrics.connected(wsConn.remoteAddress()));
          wsConn.wsHandler(wsHandler.handler);

          Runnable connectRunnable = () -> {
            connectionMap.put(ch, wsConn);
            try {
              shake.handshake(ch, request);
            } catch (WebSocketHandshakeException e) {
              wsConn.handleException(e);
            } catch (Exception e) {
              log.error("Failed to generate shake response", e);
            }
          };

          ServerWebSocketImpl ws = new ServerWebSocketImpl(vertx, theURI.toString(), theURI.getPath(),
            theURI.getQuery(), new HeadersAdaptor(request.headers()), wsConn, shake.version() != WebSocketVersion.V00,
            connectRunnable, options.getMaxWebsocketFrameSize());
          ws.metric = metrics.connected(wsConn.metric(), ws);
          wsConn.handleWebsocketConnect(ws);
          if (!ws.isRejected()) {
            ChannelHandler handler = ctx.pipeline().get(HttpChunkContentCompressor.class);
            if (handler != null) {
              // remove compressor as its not needed anymore once connection was upgraded to websockets
              ctx.pipeline().remove(handler);
            }
            ws.connectNow();
          } else {
            ch.writeAndFlush(new DefaultFullHttpResponse(HTTP_1_1, BAD_GATEWAY));
          }
        });

      }
    }
  }

  @Override
  protected void finalize() throws Throwable {
    // Make sure this gets cleaned up if there are no more references to it
    // so as not to leave connections and resources dangling until the system is shutdown
    // which could make the JVM run out of file handles.
    close();
    super.finalize();
  }

  HttpServerOptions options() {
    return options;
  }

  Map<Channel, ServerConnection> connectionMap() {
    return connectionMap;
  }

  /*
    Needs to be protected using the HttpServerImpl monitor as that protects the listening variable
    In practice synchronized overhead should be close to zero assuming most access is from the same thread due
    to biased locks
  */
  private class HttpStreamHandler<R extends ReadStream<C>, C extends ReadStream<?>> implements ReadStream<C> {

    private Handler<C> handler;
    private boolean paused;
    private Handler<Void> endHandler;

    Handler<C> handler() {
      synchronized (HttpServerImpl.this) {
        return handler;
      }
    }

    boolean isPaused() {
      synchronized (HttpServerImpl.this) {
        return paused;
      }
    }

    Handler<Void> endHandler() {
      synchronized (HttpServerImpl.this) {
        return endHandler;
      }
    }

    @Override
    public R handler(Handler<C> handler) {
      synchronized (HttpServerImpl.this) {
        if (listening) {
          throw new IllegalStateException("Please set handler before server is listening");
        }
        this.handler = handler;
        return (R) this;
      }
    }

    @Override
    public R pause() {
      synchronized (HttpServerImpl.this) {
        if (!paused) {
          paused = true;
        }
        return (R) this;
      }
    }

    @Override
    public R resume() {
      synchronized (HttpServerImpl.this) {
        if (paused) {
          paused = false;
        }
        return (R) this;
      }
    }

    @Override
    public R endHandler(Handler<Void> endHandler) {
      synchronized (HttpServerImpl.this) {
        this.endHandler = endHandler;
        return (R) this;
      }
    }

    @Override
    public R exceptionHandler(Handler<Throwable> handler) {
      // Should we use it in the server close exception handler ?
      return (R) this;
    }
  }

  class HttpServerRequestStreamImpl extends HttpStreamHandler<HttpServerRequestStream, HttpServerRequest> implements HttpServerRequestStream {
  }

  class ServerWebSocketStreamImpl extends HttpStreamHandler<ServerWebSocketStream, ServerWebSocket> implements ServerWebSocketStream {
  }
}


File: src/main/java/io/vertx/core/http/impl/VertxHttpHandler.java
/*
 * Copyright (c) 2011-2013 The original author or authors
 * ------------------------------------------------------
 * All rights reserved. This program and the accompanying materials
 * are made available under the terms of the Eclipse Public License v1.0
 * and Apache License v2.0 which accompanies this distribution.
 *
 *     The Eclipse Public License is available at
 *     http://www.eclipse.org/legal/epl-v10.html
 *
 *     The Apache License v2.0 is available at
 *     http://www.opensource.org/licenses/apache2.0.php
 *
 * You may elect to redistribute this code under either of these licenses.
 */
package io.vertx.core.http.impl;

import io.netty.buffer.ByteBuf;
import io.netty.buffer.ByteBufAllocator;
import io.netty.buffer.ByteBufHolder;
import io.netty.buffer.Unpooled;
import io.netty.channel.Channel;
import io.netty.channel.ChannelHandlerContext;
import io.netty.channel.ChannelPromise;
import io.netty.handler.codec.DecoderResult;
import io.netty.handler.codec.http.DefaultHttpContent;
import io.netty.handler.codec.http.HttpContent;
import io.netty.handler.codec.http.HttpObject;
import io.netty.handler.codec.http.LastHttpContent;
import io.netty.handler.codec.http.websocketx.BinaryWebSocketFrame;
import io.netty.handler.codec.http.websocketx.CloseWebSocketFrame;
import io.netty.handler.codec.http.websocketx.ContinuationWebSocketFrame;
import io.netty.handler.codec.http.websocketx.PingWebSocketFrame;
import io.netty.handler.codec.http.websocketx.PongWebSocketFrame;
import io.netty.handler.codec.http.websocketx.TextWebSocketFrame;
import io.netty.handler.codec.http.websocketx.WebSocketFrame;
import io.vertx.core.http.impl.ws.WebSocketFrameImpl;
import io.vertx.core.http.impl.ws.WebSocketFrameInternal;
import io.vertx.core.impl.ContextImpl;
import io.vertx.core.impl.VertxInternal;
import io.vertx.core.net.impl.ConnectionBase;
import io.vertx.core.net.impl.VertxHandler;

import java.util.Map;

/**
 * @author <a href="mailto:nmaurer@redhat.com">Norman Maurer</a>
 */
public abstract class VertxHttpHandler<C extends ConnectionBase> extends VertxHandler<C> {
  private final VertxInternal vertx;

  protected VertxHttpHandler(VertxInternal vertx, Map<Channel, C> connectionMap) {
    super(vertx, connectionMap);
    this.vertx = vertx;
  }

  private static ByteBuf safeBuffer(ByteBufHolder holder, ByteBufAllocator allocator) {
    return safeBuffer(holder.content(), allocator);
  }

  @Override
  protected void channelRead(final C connection, final ContextImpl context, final ChannelHandlerContext chctx, final Object msg) throws Exception {
    if (msg instanceof HttpObject) {
      DecoderResult result = ((HttpObject) msg).getDecoderResult();
      if (result.isFailure()) {
        chctx.pipeline().fireExceptionCaught(result.cause());
        return;
      }
    }
    if (connection != null) {
      context.executeFromIO(() -> doMessageReceived(connection, chctx, msg));
    } else {
      // We execute this directly as we don't have a context yet, the context will have to be set manually
      // inside doMessageReceived();
      try {
        doMessageReceived(null, chctx, msg);
      } catch (Throwable t) {
        chctx.pipeline().fireExceptionCaught(t);
      }
    }
  }

  @Override
  protected Object safeObject(Object msg, ByteBufAllocator allocator) throws Exception {
    if (msg instanceof HttpContent) {
      HttpContent content = (HttpContent) msg;
      ByteBuf buf = content.content();
      if (buf != Unpooled.EMPTY_BUFFER && buf.isDirect()) {
        ByteBuf newBuf = safeBuffer(content, allocator);
        if (msg instanceof LastHttpContent) {
          LastHttpContent last = (LastHttpContent) msg;
          return new AssembledLastHttpContent(newBuf, last.trailingHeaders(), last.getDecoderResult());
        } else {
          return new DefaultHttpContent(newBuf);
        }
      }
    } else if (msg instanceof WebSocketFrame) {
      ByteBuf payload = safeBuffer((WebSocketFrame) msg, allocator);
      boolean isFinal = ((WebSocketFrame) msg).isFinalFragment();
        FrameType frameType;
      if (msg instanceof BinaryWebSocketFrame) {
        frameType = FrameType.BINARY;
      } else if (msg instanceof CloseWebSocketFrame) {
        frameType = FrameType.CLOSE;
      } else if (msg instanceof PingWebSocketFrame) {
        frameType = FrameType.PING;
      } else if (msg instanceof PongWebSocketFrame) {
        frameType = FrameType.PONG;
      } else if (msg instanceof TextWebSocketFrame) {
        frameType = FrameType.TEXT;
      } else if (msg instanceof ContinuationWebSocketFrame) {
        frameType = FrameType.CONTINUATION;
      } else {
        throw new IllegalStateException("Unsupported websocket msg " + msg);
      }
      return new WebSocketFrameImpl(frameType, payload, isFinal);
    }
    return msg;
  }


  @Override
  public void write(ChannelHandlerContext ctx, Object msg, ChannelPromise promise) throws Exception {
    if (msg instanceof WebSocketFrameInternal) {
      WebSocketFrameInternal frame = (WebSocketFrameInternal) msg;
      ByteBuf buf = frame.getBinaryData();
      if (buf != Unpooled.EMPTY_BUFFER) {
         buf = safeBuffer(buf, ctx.alloc());
      }
      switch (frame.type()) {
        case BINARY:
          msg = new BinaryWebSocketFrame(frame.isFinal(), 0, buf);
          break;
        case TEXT:
          msg = new TextWebSocketFrame(frame.isFinal(), 0, buf);
          break;
        case CLOSE:
          msg = new CloseWebSocketFrame(true, 0, buf);
          break;
        case CONTINUATION:
          msg = new ContinuationWebSocketFrame(frame.isFinal(), 0, buf);
          break;
        case PONG:
          msg = new PongWebSocketFrame(buf);
          break;
        case PING:
          msg = new PingWebSocketFrame(buf);
          break;
        default:
          throw new IllegalStateException("Unsupported websocket msg " + msg);
      }
    }
    ctx.write(msg, promise);
  }

  protected abstract void doMessageReceived(C connection, ChannelHandlerContext ctx, Object msg) throws Exception;

}


File: src/main/java/io/vertx/core/net/impl/VertxHandler.java
/*
 * Copyright (c) 2011-2013 The original author or authors
 * ------------------------------------------------------
 * All rights reserved. This program and the accompanying materials
 * are made available under the terms of the Eclipse Public License v1.0
 * and Apache License v2.0 which accompanies this distribution.
 *
 *     The Eclipse Public License is available at
 *     http://www.eclipse.org/legal/epl-v10.html
 *
 *     The Apache License v2.0 is available at
 *     http://www.opensource.org/licenses/apache2.0.php
 *
 * You may elect to redistribute this code under either of these licenses.
 */
package io.vertx.core.net.impl;

import io.netty.buffer.ByteBuf;
import io.netty.buffer.ByteBufAllocator;
import io.netty.buffer.CompositeByteBuf;
import io.netty.buffer.Unpooled;
import io.netty.channel.Channel;
import io.netty.channel.ChannelDuplexHandler;
import io.netty.channel.ChannelHandlerContext;
import io.netty.handler.timeout.IdleState;
import io.netty.handler.timeout.IdleStateEvent;
import io.vertx.core.impl.ContextImpl;
import io.vertx.core.impl.VertxInternal;

import java.util.Map;

/**
 * @author <a href="mailto:nmaurer@redhat.com">Norman Maurer</a>
 */
public abstract class VertxHandler<C extends ConnectionBase> extends ChannelDuplexHandler {

  protected final VertxInternal vertx;
  protected final Map<Channel, C> connectionMap;

  protected VertxHandler(VertxInternal vertx, Map<Channel, C> connectionMap) {
    this.vertx = vertx;
    this.connectionMap = connectionMap;
  }

  protected ContextImpl getContext(C connection) {
    return connection.getContext();
  }

  protected static ByteBuf safeBuffer(ByteBuf buf, ByteBufAllocator allocator) {
    if (buf == Unpooled.EMPTY_BUFFER) {
      return buf;
    }
    if (buf.isDirect() || buf instanceof CompositeByteBuf) {
      try {
        if (buf.isReadable()) {
          ByteBuf buffer =  allocator.heapBuffer(buf.readableBytes());
          buffer.writeBytes(buf);
          return buffer;
        } else {
          return Unpooled.EMPTY_BUFFER;
        }
      } finally {
        buf.release();
      }
    }
    return buf;
  }

  @Override
  public void channelWritabilityChanged(ChannelHandlerContext ctx) throws Exception {
    Channel ch = ctx.channel();
    C conn = connectionMap.get(ch);
    if (conn != null) {
      ContextImpl context = getContext(conn);
      context.executeFromIO(conn::handleInterestedOpsChanged);
    }
  }

  @Override
  public void exceptionCaught(ChannelHandlerContext chctx, final Throwable t) throws Exception {
    Channel ch = chctx.channel();
    // Don't remove the connection at this point, or the handleClosed won't be called when channelInactive is called!
    C connection = connectionMap.get(ch);
    if (connection != null) {
      ContextImpl context = getContext(connection);
      context.executeFromIO(() -> {
        try {
          if (ch.isOpen()) {
            ch.close();
          }
        } catch (Throwable ignore) {
        }
        connection.handleException(t);
      });
    } else {
      ch.close();
    }
  }

  @Override
  public void channelInactive(ChannelHandlerContext chctx) throws Exception {
    Channel ch = chctx.channel();
    C connection = connectionMap.remove(ch);
    if (connection != null) {
      ContextImpl context = getContext(connection);
      context.executeFromIO(connection::handleClosed);
    }
  }

  @Override
  public void channelReadComplete(ChannelHandlerContext ctx) throws Exception {
    C conn = connectionMap.get(ctx.channel());
    if (conn != null) {
      conn.endReadAndFlush();
    }
  }

  @Override
  public void channelRead(ChannelHandlerContext chctx, Object msg) throws Exception {
    Object message = safeObject(msg, chctx.alloc());
    C connection = connectionMap.get(chctx.channel());
    ContextImpl context;
    if (connection != null) {
      context = getContext(connection);
      connection.startRead();
    } else {
      context = null;
    }
    channelRead(connection, context, chctx, message);
  }

  @Override
  public void userEventTriggered(ChannelHandlerContext ctx, Object evt) throws Exception {
    if (evt instanceof IdleStateEvent && ((IdleStateEvent) evt).state() == IdleState.ALL_IDLE) {
      ctx.close();
    }
  }

  protected abstract void channelRead(C connection, ContextImpl context, ChannelHandlerContext chctx, Object msg) throws Exception;

  protected abstract Object safeObject(Object msg, ByteBufAllocator allocator) throws Exception;
}


File: src/main/java/io/vertx/core/net/impl/VertxNetHandler.java
/*
 * Copyright (c) 2011-2013 The original author or authors
 * ------------------------------------------------------
 * All rights reserved. This program and the accompanying materials
 * are made available under the terms of the Eclipse Public License v1.0
 * and Apache License v2.0 which accompanies this distribution.
 *
 *     The Eclipse Public License is available at
 *     http://www.eclipse.org/legal/epl-v10.html
 *
 *     The Apache License v2.0 is available at
 *     http://www.opensource.org/licenses/apache2.0.php
 *
 * You may elect to redistribute this code under either of these licenses.
 */

package io.vertx.core.net.impl;

import io.netty.buffer.ByteBuf;
import io.netty.buffer.ByteBufAllocator;
import io.netty.channel.Channel;
import io.netty.channel.ChannelHandlerContext;
import io.vertx.core.buffer.Buffer;
import io.vertx.core.impl.ContextImpl;
import io.vertx.core.impl.VertxInternal;

import java.util.Map;

/**
 * @author <a href="mailto:nmaurer@redhat.com">Norman Maurer</a>
 */
public class VertxNetHandler extends VertxHandler<NetSocketImpl> {

  public VertxNetHandler(VertxInternal vertx, Map<Channel, NetSocketImpl> connectionMap) {
    super(vertx, connectionMap);
  }

  @Override
  protected void channelRead(NetSocketImpl sock, ContextImpl context, ChannelHandlerContext chctx, Object msg) throws Exception {
    if (sock != null) {
      ByteBuf buf = (ByteBuf) msg;
      context.executeFromIO(() -> sock.handleDataReceived(Buffer.buffer(buf)));
    } else {
      // just discard
    }
  }

  @Override
  protected Object safeObject(Object msg, ByteBufAllocator allocator) throws Exception {
    if (msg instanceof ByteBuf) {
      return safeBuffer((ByteBuf) msg, allocator);
    }
    return msg;
  }
}


File: src/test/java/io/vertx/test/core/NetTest.java
/*
 * Copyright 2014 Red Hat, Inc.
 *
 * All rights reserved. This program and the accompanying materials
 * are made available under the terms of the Eclipse Public License v1.0
 * and Apache License v2.0 which accompanies this distribution.
 *
 * The Eclipse Public License is available at
 * http://www.eclipse.org/legal/epl-v10.html
 *
 * The Apache License v2.0 is available at
 * http://www.opensource.org/licenses/apache2.0.php
 *
 * You may elect to redistribute this code under either of these licenses.
 */

package io.vertx.test.core;

import io.vertx.core.*;
import io.vertx.core.buffer.Buffer;
import io.vertx.core.eventbus.Message;
import io.vertx.core.eventbus.MessageConsumer;
import io.vertx.core.impl.*;
import io.vertx.core.json.JsonArray;
import io.vertx.core.json.JsonObject;
import io.vertx.core.net.*;
import io.vertx.core.net.impl.SocketAddressImpl;
import io.vertx.core.net.impl.SocketDefaults;
import org.junit.Assume;
import org.junit.Rule;
import org.junit.Test;
import org.junit.rules.TemporaryFolder;

import javax.net.ssl.SSLPeerUnverifiedException;
import javax.security.cert.X509Certificate;
import java.io.BufferedWriter;
import java.io.File;
import java.io.FileOutputStream;
import java.io.OutputStreamWriter;
import java.util.*;
import java.util.concurrent.ConcurrentHashMap;
import java.util.concurrent.CountDownLatch;
import java.util.concurrent.TimeUnit;
import java.util.concurrent.atomic.AtomicBoolean;
import java.util.concurrent.atomic.AtomicInteger;
import java.util.concurrent.atomic.AtomicReference;
import java.util.function.Consumer;

import static io.vertx.test.core.TestUtils.assertIllegalArgumentException;
import static io.vertx.test.core.TestUtils.assertNullPointerException;

/**
 * @author <a href="http://tfox.org">Tim Fox</a>
 */
public class NetTest extends VertxTestBase {

  private NetServer server;
  private NetClient client;

  @Rule
  public TemporaryFolder testFolder = new TemporaryFolder();

  public void setUp() throws Exception {
    super.setUp();
    client = vertx.createNetClient(new NetClientOptions().setConnectTimeout(1000));
    server = vertx.createNetServer(new NetServerOptions().setPort(1234).setHost("localhost"));
  }

  protected void awaitClose(NetServer server) throws InterruptedException {
    CountDownLatch latch = new CountDownLatch(1);
    server.close((asyncResult) -> {
      latch.countDown();
    });
    awaitLatch(latch);
  }

  protected void tearDown() throws Exception {
    if (client != null) {
      client.close();
    }
    if (server != null) {
      awaitClose(server);
    }
    super.tearDown();
  }

  @Test
  public void testClientOptions() {
    NetClientOptions options = new NetClientOptions();

    assertEquals(NetworkOptions.DEFAULT_SEND_BUFFER_SIZE, options.getSendBufferSize());
    int rand = TestUtils.randomPositiveInt();
    assertEquals(options, options.setSendBufferSize(rand));
    assertEquals(rand, options.getSendBufferSize());
    assertIllegalArgumentException(() -> options.setSendBufferSize(0));
    assertIllegalArgumentException(() -> options.setSendBufferSize(-123));

    assertEquals(NetworkOptions.DEFAULT_RECEIVE_BUFFER_SIZE, options.getReceiveBufferSize());
    rand = TestUtils.randomPositiveInt();
    assertEquals(options, options.setReceiveBufferSize(rand));
    assertEquals(rand, options.getReceiveBufferSize());
    assertIllegalArgumentException(() -> options.setReceiveBufferSize(0));
    assertIllegalArgumentException(() -> options.setReceiveBufferSize(-123));

    assertTrue(options.isReuseAddress());
    assertEquals(options, options.setReuseAddress(false));
    assertFalse(options.isReuseAddress());

    assertEquals(NetworkOptions.DEFAULT_TRAFFIC_CLASS, options.getTrafficClass());
    rand = 23;
    assertEquals(options, options.setTrafficClass(rand));
    assertEquals(rand, options.getTrafficClass());
    assertIllegalArgumentException(() -> options.setTrafficClass(-1));
    assertIllegalArgumentException(() -> options.setTrafficClass(256));

    assertTrue(options.isTcpNoDelay());
    assertEquals(options, options.setTcpNoDelay(false));
    assertFalse(options.isTcpNoDelay());

    boolean tcpKeepAlive = SocketDefaults.instance.isTcpKeepAlive();
    assertEquals(tcpKeepAlive, options.isTcpKeepAlive());
    assertEquals(options, options.setTcpKeepAlive(!tcpKeepAlive));
    assertEquals(!tcpKeepAlive, options.isTcpKeepAlive());

    int soLinger = SocketDefaults.instance.getSoLinger();
    assertEquals(soLinger, options.getSoLinger());
    rand = TestUtils.randomPositiveInt();
    assertEquals(options, options.setSoLinger(rand));
    assertEquals(rand, options.getSoLinger());
    assertIllegalArgumentException(() -> options.setSoLinger(-1));

    assertFalse(options.isUsePooledBuffers());
    assertEquals(options, options.setUsePooledBuffers(true));
    assertTrue(options.isUsePooledBuffers());

    rand = TestUtils.randomPositiveInt();
    assertEquals(0, options.getIdleTimeout());
    assertEquals(options, options.setIdleTimeout(rand));
    assertEquals(rand, options.getIdleTimeout());

    assertFalse(options.isSsl());
    assertEquals(options, options.setSsl(true));
    assertTrue(options.isSsl());

    assertNull(options.getKeyCertOptions());
    JksOptions keyStoreOptions = new JksOptions().setPath(TestUtils.randomAlphaString(100)).setPassword(TestUtils.randomAlphaString(100));
    assertEquals(options, options.setKeyStoreOptions(keyStoreOptions));
    assertEquals(keyStoreOptions, options.getKeyCertOptions());

    assertNull(options.getTrustOptions());
    JksOptions trustStoreOptions = new JksOptions().setPath(TestUtils.randomAlphaString(100)).setPassword(TestUtils.randomAlphaString(100));
    assertEquals(options, options.setTrustStoreOptions(trustStoreOptions));
    assertEquals(trustStoreOptions, options.getTrustOptions());

    assertFalse(options.isTrustAll());
    assertEquals(options, options.setTrustAll(true));
    assertTrue(options.isTrustAll());

    assertEquals(0, options.getReconnectAttempts());
    assertIllegalArgumentException(() -> options.setReconnectAttempts(-2));
    rand = TestUtils.randomPositiveInt();
    assertEquals(options, options.setReconnectAttempts(rand));
    assertEquals(rand, options.getReconnectAttempts());

    assertEquals(1000, options.getReconnectInterval());
    assertIllegalArgumentException(() -> options.setReconnectInterval(0));
    rand = TestUtils.randomPositiveInt();
    assertEquals(options, options.setReconnectInterval(rand));
    assertEquals(rand, options.getReconnectInterval());

    assertTrue(options.getEnabledCipherSuites().isEmpty());
    assertEquals(options, options.addEnabledCipherSuite("foo"));
    assertEquals(options, options.addEnabledCipherSuite("bar"));
    assertNotNull(options.getEnabledCipherSuites());
    assertTrue(options.getEnabledCipherSuites().contains("foo"));
    assertTrue(options.getEnabledCipherSuites().contains("bar"));

    testComplete();
  }

  @Test
  public void testServerOptions() {
    NetServerOptions options = new NetServerOptions();

    assertEquals(NetworkOptions.DEFAULT_SEND_BUFFER_SIZE, options.getSendBufferSize());
    int rand = TestUtils.randomPositiveInt();
    assertEquals(options, options.setSendBufferSize(rand));
    assertEquals(rand, options.getSendBufferSize());
    assertIllegalArgumentException(() -> options.setSendBufferSize(0));
    assertIllegalArgumentException(() -> options.setSendBufferSize(-123));

    assertEquals(NetworkOptions.DEFAULT_RECEIVE_BUFFER_SIZE, options.getReceiveBufferSize());
    rand = TestUtils.randomPositiveInt();
    assertEquals(options, options.setReceiveBufferSize(rand));
    assertEquals(rand, options.getReceiveBufferSize());
    assertIllegalArgumentException(() -> options.setReceiveBufferSize(0));
    assertIllegalArgumentException(() -> options.setReceiveBufferSize(-123));

    assertTrue(options.isReuseAddress());
    assertEquals(options, options.setReuseAddress(false));
    assertFalse(options.isReuseAddress());

    assertEquals(NetworkOptions.DEFAULT_TRAFFIC_CLASS, options.getTrafficClass());
    rand = 23;
    assertEquals(options, options.setTrafficClass(rand));
    assertEquals(rand, options.getTrafficClass());
    assertIllegalArgumentException(() -> options.setTrafficClass(-1));
    assertIllegalArgumentException(() -> options.setTrafficClass(256));

    assertTrue(options.isTcpNoDelay());
    assertEquals(options, options.setTcpNoDelay(false));
    assertFalse(options.isTcpNoDelay());

    boolean tcpKeepAlive = SocketDefaults.instance.isTcpKeepAlive();
    assertEquals(tcpKeepAlive, options.isTcpKeepAlive());
    assertEquals(options, options.setTcpKeepAlive(!tcpKeepAlive));
    assertEquals(!tcpKeepAlive, options.isTcpKeepAlive());

    int soLinger = SocketDefaults.instance.getSoLinger();
    assertEquals(soLinger, options.getSoLinger());
    rand = TestUtils.randomPositiveInt();
    assertEquals(options, options.setSoLinger(rand));
    assertEquals(rand, options.getSoLinger());
    assertIllegalArgumentException(() -> options.setSoLinger(-1));

    assertFalse(options.isUsePooledBuffers());
    assertEquals(options, options.setUsePooledBuffers(true));
    assertTrue(options.isUsePooledBuffers());

    rand = TestUtils.randomPositiveInt();
    assertEquals(0, options.getIdleTimeout());
    assertEquals(options, options.setIdleTimeout(rand));
    assertEquals(rand, options.getIdleTimeout());
    assertIllegalArgumentException(() -> options.setIdleTimeout(-1));

    assertFalse(options.isSsl());
    assertEquals(options, options.setSsl(true));
    assertTrue(options.isSsl());

    assertNull(options.getKeyCertOptions());
    JksOptions keyStoreOptions = new JksOptions().setPath(TestUtils.randomAlphaString(100)).setPassword(TestUtils.randomAlphaString(100));
    assertEquals(options, options.setKeyStoreOptions(keyStoreOptions));
    assertEquals(keyStoreOptions, options.getKeyCertOptions());

    assertNull(options.getTrustOptions());
    JksOptions trustStoreOptions = new JksOptions().setPath(TestUtils.randomAlphaString(100)).setPassword(TestUtils.randomAlphaString(100));
    assertEquals(options, options.setTrustStoreOptions(trustStoreOptions));
    assertEquals(trustStoreOptions, options.getTrustOptions());

    assertEquals(1024, options.getAcceptBacklog());
    rand = TestUtils.randomPositiveInt();
    assertEquals(options, options.setAcceptBacklog(rand));
    assertEquals(rand, options.getAcceptBacklog());

    assertEquals(0, options.getPort());
    assertEquals(options, options.setPort(1234));
    assertEquals(1234, options.getPort());
    assertIllegalArgumentException(() -> options.setPort(-1));
    assertIllegalArgumentException(() -> options.setPort(65536));

    assertEquals("0.0.0.0", options.getHost());
    String randString = TestUtils.randomUnicodeString(100);
    assertEquals(options, options.setHost(randString));
    assertEquals(randString, options.getHost());

    assertTrue(options.getEnabledCipherSuites().isEmpty());
    assertEquals(options, options.addEnabledCipherSuite("foo"));
    assertEquals(options, options.addEnabledCipherSuite("bar"));
    assertNotNull(options.getEnabledCipherSuites());
    assertTrue(options.getEnabledCipherSuites().contains("foo"));
    assertTrue(options.getEnabledCipherSuites().contains("bar"));

    testComplete();
  }

  @Test
  public void testCopyClientOptions() {
    NetClientOptions options = new NetClientOptions();
    int sendBufferSize = TestUtils.randomPositiveInt();
    int receiverBufferSize = TestUtils.randomPortInt();
    Random rand = new Random();
    boolean reuseAddress = rand.nextBoolean();
    int trafficClass = TestUtils.randomByte() + 127;
    boolean tcpNoDelay = rand.nextBoolean();
    boolean tcpKeepAlive = rand.nextBoolean();
    int soLinger = TestUtils.randomPositiveInt();
    boolean usePooledBuffers = rand.nextBoolean();
    int idleTimeout = TestUtils.randomPositiveInt();
    boolean ssl = rand.nextBoolean();
    JksOptions keyStoreOptions = new JksOptions();
    String ksPassword = TestUtils.randomAlphaString(100);
    keyStoreOptions.setPassword(ksPassword);
    JksOptions trustStoreOptions = new JksOptions();
    String tsPassword = TestUtils.randomAlphaString(100);
    trustStoreOptions.setPassword(tsPassword);
    String enabledCipher = TestUtils.randomAlphaString(100);
    int connectTimeout = TestUtils.randomPositiveInt();
    boolean trustAll = rand.nextBoolean();
    String crlPath = TestUtils.randomUnicodeString(100);
    Buffer crlValue = TestUtils.randomBuffer(100);
    int reconnectAttempts = TestUtils.randomPositiveInt();
    long reconnectInterval = TestUtils.randomPositiveInt();
    options.setSendBufferSize(sendBufferSize);
    options.setReceiveBufferSize(receiverBufferSize);
    options.setReuseAddress(reuseAddress);
    options.setTrafficClass(trafficClass);
    options.setSsl(ssl);
    options.setTcpNoDelay(tcpNoDelay);
    options.setTcpKeepAlive(tcpKeepAlive);
    options.setSoLinger(soLinger);
    options.setUsePooledBuffers(usePooledBuffers);
    options.setIdleTimeout(idleTimeout);
    options.setKeyStoreOptions(keyStoreOptions);
    options.setTrustStoreOptions(trustStoreOptions);
    options.addEnabledCipherSuite(enabledCipher);
    options.setConnectTimeout(connectTimeout);
    options.setTrustAll(trustAll);
    options.addCrlPath(crlPath);
    options.addCrlValue(crlValue);
    options.setReconnectAttempts(reconnectAttempts);
    options.setReconnectInterval(reconnectInterval);
    NetClientOptions copy = new NetClientOptions(options);
    assertEquals(sendBufferSize, copy.getSendBufferSize());
    assertEquals(receiverBufferSize, copy.getReceiveBufferSize());
    assertEquals(reuseAddress, copy.isReuseAddress());
    assertEquals(trafficClass, copy.getTrafficClass());
    assertEquals(tcpNoDelay, copy.isTcpNoDelay());
    assertEquals(tcpKeepAlive, copy.isTcpKeepAlive());
    assertEquals(soLinger, copy.getSoLinger());
    assertEquals(usePooledBuffers, copy.isUsePooledBuffers());
    assertEquals(idleTimeout, copy.getIdleTimeout());
    assertEquals(ssl, copy.isSsl());
    assertNotSame(keyStoreOptions, copy.getKeyCertOptions());
    assertEquals(ksPassword, ((JksOptions) copy.getKeyCertOptions()).getPassword());
    assertNotSame(trustStoreOptions, copy.getTrustOptions());
    assertEquals(tsPassword, ((JksOptions)copy.getTrustOptions()).getPassword());
    assertEquals(1, copy.getEnabledCipherSuites().size());
    assertTrue(copy.getEnabledCipherSuites().contains(enabledCipher));
    assertEquals(connectTimeout, copy.getConnectTimeout());
    assertEquals(trustAll, copy.isTrustAll());
    assertEquals(1, copy.getCrlPaths().size());
    assertEquals(crlPath, copy.getCrlPaths().get(0));
    assertEquals(1, copy.getCrlValues().size());
    assertEquals(crlValue, copy.getCrlValues().get(0));
    assertEquals(reconnectAttempts, copy.getReconnectAttempts());
    assertEquals(reconnectInterval, copy.getReconnectInterval());
  }

  @Test
  public void testDefaultClientOptionsJson() {
    NetClientOptions def = new NetClientOptions();
    NetClientOptions json = new NetClientOptions(new JsonObject());
    assertEquals(def.getReconnectAttempts(), json.getReconnectAttempts());
    assertEquals(def.getReconnectInterval(), json.getReconnectInterval());
    assertEquals(def.isTrustAll(), json.isTrustAll());
    assertEquals(def.getCrlPaths(), json.getCrlPaths());
    assertEquals(def.getCrlValues(), json.getCrlValues());
    assertEquals(def.getConnectTimeout(), json.getConnectTimeout());
    assertEquals(def.isTcpNoDelay(), json.isTcpNoDelay());
    assertEquals(def.isTcpKeepAlive(), json.isTcpKeepAlive());
    assertEquals(def.getSoLinger(), json.getSoLinger());
    assertEquals(def.isUsePooledBuffers(), json.isUsePooledBuffers());
    assertEquals(def.isSsl(), json.isSsl());
  }

  @Test
  public void testClientOptionsJson() {
    int sendBufferSize = TestUtils.randomPositiveInt();
    int receiverBufferSize = TestUtils.randomPortInt();
    Random rand = new Random();
    boolean reuseAddress = rand.nextBoolean();
    int trafficClass = TestUtils.randomByte() + 127;
    boolean tcpNoDelay = rand.nextBoolean();
    boolean tcpKeepAlive = rand.nextBoolean();
    int soLinger = TestUtils.randomPositiveInt();
    boolean usePooledBuffers = rand.nextBoolean();
    int idleTimeout = TestUtils.randomPositiveInt();
    boolean ssl = rand.nextBoolean();
    JksOptions keyStoreOptions = new JksOptions();
    String ksPassword = TestUtils.randomAlphaString(100);
    keyStoreOptions.setPassword(ksPassword);
    String ksPath = TestUtils.randomAlphaString(100);
    keyStoreOptions.setPath(ksPath);
    JksOptions trustStoreOptions = new JksOptions();
    String tsPassword = TestUtils.randomAlphaString(100);
    trustStoreOptions.setPassword(tsPassword);
    String tsPath = TestUtils.randomAlphaString(100);
    trustStoreOptions.setPath(tsPath);
    String enabledCipher = TestUtils.randomAlphaString(100);
    int connectTimeout = TestUtils.randomPositiveInt();
    boolean trustAll = rand.nextBoolean();
    String crlPath = TestUtils.randomUnicodeString(100);
    int reconnectAttempts = TestUtils.randomPositiveInt();
    long reconnectInterval = TestUtils.randomPositiveInt();

    JsonObject json = new JsonObject();
    json.put("sendBufferSize", sendBufferSize)
        .put("receiveBufferSize", receiverBufferSize)
        .put("reuseAddress", reuseAddress)
        .put("trafficClass", trafficClass)
        .put("tcpNoDelay", tcpNoDelay)
        .put("tcpKeepAlive", tcpKeepAlive)
        .put("soLinger", soLinger)
        .put("usePooledBuffers", usePooledBuffers)
        .put("idleTimeout", idleTimeout)
        .put("ssl", ssl)
        .put("enabledCipherSuites", new JsonArray().add(enabledCipher))
        .put("connectTimeout", connectTimeout)
        .put("trustAll", trustAll)
        .put("crlPaths", new JsonArray().add(crlPath))
        .put("keyStoreOptions", new JsonObject().put("type", "jks").put("password", ksPassword).put("path", ksPath))
        .put("trustStoreOptions", new JsonObject().put("type", "jks").put("password", tsPassword).put("path", tsPath))
        .put("reconnectAttempts", reconnectAttempts)
        .put("reconnectInterval", reconnectInterval);

    NetClientOptions options = new NetClientOptions(json);
    assertEquals(sendBufferSize, options.getSendBufferSize());
    assertEquals(receiverBufferSize, options.getReceiveBufferSize());
    assertEquals(reuseAddress, options.isReuseAddress());
    assertEquals(trafficClass, options.getTrafficClass());
    assertEquals(tcpKeepAlive, options.isTcpKeepAlive());
    assertEquals(tcpNoDelay, options.isTcpNoDelay());
    assertEquals(soLinger, options.getSoLinger());
    assertEquals(usePooledBuffers, options.isUsePooledBuffers());
    assertEquals(idleTimeout, options.getIdleTimeout());
    assertEquals(ssl, options.isSsl());
    assertNotSame(keyStoreOptions, options.getKeyCertOptions());
    assertEquals(ksPassword, ((JksOptions) options.getKeyCertOptions()).getPassword());
    assertEquals(ksPath, ((JksOptions) options.getKeyCertOptions()).getPath());
    assertNotSame(trustStoreOptions, options.getTrustOptions());
    assertEquals(tsPassword, ((JksOptions) options.getTrustOptions()).getPassword());
    assertEquals(tsPath, ((JksOptions) options.getTrustOptions()).getPath());
    assertEquals(1, options.getEnabledCipherSuites().size());
    assertTrue(options.getEnabledCipherSuites().contains(enabledCipher));
    assertEquals(connectTimeout, options.getConnectTimeout());
    assertEquals(trustAll, options.isTrustAll());
    assertEquals(1, options.getCrlPaths().size());
    assertEquals(crlPath, options.getCrlPaths().get(0));
    assertEquals(reconnectAttempts, options.getReconnectAttempts());
    assertEquals(reconnectInterval, options.getReconnectInterval());

    // Test other keystore/truststore types
    json.remove("keyStoreOptions");
    json.remove("trustStoreOptions");
    json.put("pfxKeyCertOptions", new JsonObject().put("password", ksPassword))
      .put("pfxTrustOptions", new JsonObject().put("password", tsPassword));
    options = new NetClientOptions(json);
    assertTrue(options.getTrustOptions() instanceof PfxOptions);
    assertTrue(options.getKeyCertOptions() instanceof PfxOptions);

    json.remove("pfxKeyCertOptions");
    json.remove("pfxTrustOptions");
    json.put("pemKeyCertOptions", new JsonObject())
      .put("pemTrustOptions", new JsonObject());
    options = new NetClientOptions(json);
    assertTrue(options.getTrustOptions() instanceof PemTrustOptions);
    assertTrue(options.getKeyCertOptions() instanceof PemKeyCertOptions);
  }

  @Test
  public void testCopyServerOptions() {
    NetServerOptions options = new NetServerOptions();
    int sendBufferSize = TestUtils.randomPositiveInt();
    int receiverBufferSize = TestUtils.randomPortInt();
    Random rand = new Random();
    boolean reuseAddress = rand.nextBoolean();
    int trafficClass = TestUtils.randomByte() + 128;
    boolean tcpNoDelay = rand.nextBoolean();
    boolean tcpKeepAlive = rand.nextBoolean();
    int soLinger = TestUtils.randomPositiveInt();
    boolean usePooledBuffers = rand.nextBoolean();
    int idleTimeout = TestUtils.randomPositiveInt();
    boolean ssl = rand.nextBoolean();
    JksOptions keyStoreOptions = new JksOptions();
    String ksPassword = TestUtils.randomAlphaString(100);
    keyStoreOptions.setPassword(ksPassword);
    JksOptions trustStoreOptions = new JksOptions();
    String tsPassword = TestUtils.randomAlphaString(100);
    trustStoreOptions.setPassword(tsPassword);
    String enabledCipher = TestUtils.randomAlphaString(100);
    String crlPath = TestUtils.randomUnicodeString(100);
    Buffer crlValue = TestUtils.randomBuffer(100);
    int port = 1234;
    String host = TestUtils.randomAlphaString(100);
    int acceptBacklog = TestUtils.randomPortInt();
    options.setSendBufferSize(sendBufferSize);
    options.setReceiveBufferSize(receiverBufferSize);
    options.setReuseAddress(reuseAddress);
    options.setTrafficClass(trafficClass);
    options.setTcpNoDelay(tcpNoDelay);
    options.setTcpKeepAlive(tcpKeepAlive);
    options.setSoLinger(soLinger);
    options.setUsePooledBuffers(usePooledBuffers);
    options.setIdleTimeout(idleTimeout);
    options.setSsl(ssl);
    options.setKeyStoreOptions(keyStoreOptions);
    options.setTrustStoreOptions(trustStoreOptions);
    options.addEnabledCipherSuite(enabledCipher);
    options.addCrlPath(crlPath);
    options.addCrlValue(crlValue);
    options.setPort(port);
    options.setHost(host);
    options.setAcceptBacklog(acceptBacklog);
    NetServerOptions copy = new NetServerOptions(options);
    assertEquals(sendBufferSize, copy.getSendBufferSize());
    assertEquals(receiverBufferSize, copy.getReceiveBufferSize());
    assertEquals(reuseAddress, copy.isReuseAddress());
    assertEquals(trafficClass, copy.getTrafficClass());
    assertEquals(tcpNoDelay, copy.isTcpNoDelay());
    assertEquals(tcpKeepAlive, copy.isTcpKeepAlive());
    assertEquals(soLinger, copy.getSoLinger());
    assertEquals(usePooledBuffers, copy.isUsePooledBuffers());
    assertEquals(idleTimeout, copy.getIdleTimeout());
    assertEquals(ssl, copy.isSsl());
    assertNotSame(keyStoreOptions, copy.getKeyCertOptions());
    assertEquals(ksPassword, ((JksOptions) copy.getKeyCertOptions()).getPassword());
    assertNotSame(trustStoreOptions, copy.getTrustOptions());
    assertEquals(tsPassword, ((JksOptions)copy.getTrustOptions()).getPassword());
    assertEquals(1, copy.getEnabledCipherSuites().size());
    assertTrue(copy.getEnabledCipherSuites().contains(enabledCipher));
    assertEquals(1, copy.getCrlPaths().size());
    assertEquals(crlPath, copy.getCrlPaths().get(0));
    assertEquals(1, copy.getCrlValues().size());
    assertEquals(crlValue, copy.getCrlValues().get(0));
    assertEquals(port, copy.getPort());
    assertEquals(host, copy.getHost());
    assertEquals(acceptBacklog, copy.getAcceptBacklog());
  }

  @Test
  public void testDefaultServerOptionsJson() {
    NetServerOptions def = new NetServerOptions();
    NetServerOptions json = new NetServerOptions(new JsonObject());
    assertEquals(def.isClientAuthRequired(), json.isClientAuthRequired());
    assertEquals(def.getCrlPaths(), json.getCrlPaths());
    assertEquals(def.getCrlValues(), json.getCrlValues());
    assertEquals(def.getAcceptBacklog(), json.getAcceptBacklog());
    assertEquals(def.getPort(), json.getPort());
    assertEquals(def.getHost(), json.getHost());
    assertEquals(def.isClientAuthRequired(), json.isClientAuthRequired());
    assertEquals(def.getCrlPaths(), json.getCrlPaths());
    assertEquals(def.getCrlValues(), json.getCrlValues());
    assertEquals(def.getAcceptBacklog(), json.getAcceptBacklog());
    assertEquals(def.getPort(), json.getPort());
    assertEquals(def.getHost(), json.getHost());
    assertEquals(def.isTcpNoDelay(), json.isTcpNoDelay());
    assertEquals(def.isTcpKeepAlive(), json.isTcpKeepAlive());
    assertEquals(def.getSoLinger(), json.getSoLinger());
    assertEquals(def.isUsePooledBuffers(), json.isUsePooledBuffers());
    assertEquals(def.isSsl(), json.isSsl());
  }

  @Test
  public void testServerOptionsJson() {
    int sendBufferSize = TestUtils.randomPositiveInt();
    int receiverBufferSize = TestUtils.randomPortInt();
    Random rand = new Random();
    boolean reuseAddress = rand.nextBoolean();
    int trafficClass = TestUtils.randomByte() + 127;
    boolean tcpNoDelay = rand.nextBoolean();
    boolean tcpKeepAlive = rand.nextBoolean();
    int soLinger = TestUtils.randomPositiveInt();
    boolean usePooledBuffers = rand.nextBoolean();
    int idleTimeout = TestUtils.randomInt();
    boolean ssl = rand.nextBoolean();
    JksOptions keyStoreOptions = new JksOptions();
    String ksPassword = TestUtils.randomAlphaString(100);
    keyStoreOptions.setPassword(ksPassword);
    String ksPath = TestUtils.randomAlphaString(100);
    keyStoreOptions.setPath(ksPath);
    JksOptions trustStoreOptions = new JksOptions();
    String tsPassword = TestUtils.randomAlphaString(100);
    trustStoreOptions.setPassword(tsPassword);
    String tsPath = TestUtils.randomAlphaString(100);
    trustStoreOptions.setPath(tsPath);
    String enabledCipher = TestUtils.randomAlphaString(100);
    String crlPath = TestUtils.randomUnicodeString(100);
    int port = 1234;
    String host = TestUtils.randomAlphaString(100);
    int acceptBacklog = TestUtils.randomPortInt();

    JsonObject json = new JsonObject();
    json.put("sendBufferSize", sendBufferSize)
      .put("receiveBufferSize", receiverBufferSize)
      .put("reuseAddress", reuseAddress)
      .put("trafficClass", trafficClass)
      .put("tcpNoDelay", tcpNoDelay)
      .put("tcpKeepAlive", tcpKeepAlive)
      .put("soLinger", soLinger)
      .put("usePooledBuffers", usePooledBuffers)
      .put("idleTimeout", idleTimeout)
      .put("ssl", ssl)
      .put("enabledCipherSuites", new JsonArray().add(enabledCipher))
      .put("crlPaths", new JsonArray().add(crlPath))
      .put("keyStoreOptions", new JsonObject().put("password", ksPassword).put("path", ksPath))
      .put("trustStoreOptions", new JsonObject().put("password", tsPassword).put("path", tsPath))
      .put("port", port)
      .put("host", host)
      .put("acceptBacklog", acceptBacklog);

    NetServerOptions options = new NetServerOptions(json);
    assertEquals(sendBufferSize, options.getSendBufferSize());
    assertEquals(receiverBufferSize, options.getReceiveBufferSize());
    assertEquals(reuseAddress, options.isReuseAddress());
    assertEquals(trafficClass, options.getTrafficClass());
    assertEquals(tcpKeepAlive, options.isTcpKeepAlive());
    assertEquals(tcpNoDelay, options.isTcpNoDelay());
    assertEquals(soLinger, options.getSoLinger());
    assertEquals(usePooledBuffers, options.isUsePooledBuffers());
    assertEquals(idleTimeout, options.getIdleTimeout());
    assertEquals(ssl, options.isSsl());
    assertNotSame(keyStoreOptions, options.getKeyCertOptions());
    assertEquals(ksPassword, ((JksOptions) options.getKeyCertOptions()).getPassword());
    assertEquals(ksPath, ((JksOptions) options.getKeyCertOptions()).getPath());
    assertNotSame(trustStoreOptions, options.getTrustOptions());
    assertEquals(tsPassword, ((JksOptions) options.getTrustOptions()).getPassword());
    assertEquals(tsPath, ((JksOptions) options.getTrustOptions()).getPath());
    assertEquals(1, options.getEnabledCipherSuites().size());
    assertTrue(options.getEnabledCipherSuites().contains(enabledCipher));
    assertEquals(1, options.getCrlPaths().size());
    assertEquals(crlPath, options.getCrlPaths().get(0));
    assertEquals(port, options.getPort());
    assertEquals(host, options.getHost());
    assertEquals(acceptBacklog, options.getAcceptBacklog());

    // Test other keystore/truststore types
    json.remove("keyStoreOptions");
    json.remove("trustStoreOptions");
    json.put("pfxKeyCertOptions", new JsonObject().put("password", ksPassword))
      .put("pfxTrustOptions", new JsonObject().put("password", tsPassword));
    options = new NetServerOptions(json);
    assertTrue(options.getTrustOptions() instanceof PfxOptions);
    assertTrue(options.getKeyCertOptions() instanceof PfxOptions);

    json.remove("pfxKeyCertOptions");
    json.remove("pfxTrustOptions");
    json.put("pemKeyCertOptions", new JsonObject())
      .put("pemTrustOptions", new JsonObject());
    options = new NetServerOptions(json);
    assertTrue(options.getTrustOptions() instanceof PemTrustOptions);
    assertTrue(options.getKeyCertOptions() instanceof PemKeyCertOptions);
  }

  @Test
  public void testSocketAddress() throws Exception {
    assertNullPointerException(() -> new SocketAddressImpl(0, null));
    assertIllegalArgumentException(() -> new SocketAddressImpl(0, ""));
    assertIllegalArgumentException(() -> new SocketAddressImpl(-1, "someHost"));
    assertIllegalArgumentException(() -> new SocketAddressImpl(65536, "someHost"));
  }

  @Test
  public void testEchoBytes() {
    Buffer sent = TestUtils.randomBuffer(100);
    testEcho(sock -> sock.write(sent), buff -> assertEquals(sent, buff), sent.length());
  }

  @Test
  public void testEchoString() {
    String sent = TestUtils.randomUnicodeString(100);
    Buffer buffSent = Buffer.buffer(sent);
    testEcho(sock -> sock.write(sent), buff -> assertEquals(buffSent, buff), buffSent.length());
  }

  @Test
  public void testEchoStringUTF8() {
    testEchoStringWithEncoding("UTF-8");
  }

  @Test
  public void testEchoStringUTF16() {
    testEchoStringWithEncoding("UTF-16");
  }

  void testEchoStringWithEncoding(String encoding) {
    String sent = TestUtils.randomUnicodeString(100);
    Buffer buffSent = Buffer.buffer(sent, encoding);
    testEcho(sock -> sock.write(sent, encoding), buff -> assertEquals(buffSent, buff), buffSent.length());
  }

  void testEcho(Consumer<NetSocket> writer, Consumer<Buffer> dataChecker, int length) {
    Handler<AsyncResult<NetSocket>> clientHandler = (asyncResult) -> {
      if (asyncResult.succeeded()) {
        NetSocket sock = asyncResult.result();
        Buffer buff = Buffer.buffer();
        sock.handler((buffer) -> {
          buff.appendBuffer(buffer);
          if (buff.length() == length) {
            dataChecker.accept(buff);
            testComplete();
          }
          if (buff.length() > length) {
            fail("Too many bytes received");
          }
        });
        writer.accept(sock);
      } else {
        fail("failed to connect");
      }
    };
    startEchoServer(s -> client.connect(1234, "localhost", clientHandler));
    await();
  }

  void startEchoServer(Handler<AsyncResult<NetServer>> listenHandler) {
    Handler<NetSocket> serverHandler = socket -> socket.handler(socket::write);
    server.connectHandler(serverHandler).listen(listenHandler);
  }

  @Test
  public void testConnectLocalHost() {
    connect(1234, "localhost");
  }

  void connect(int port, String host) {
    startEchoServer(s -> {
      final int numConnections = 100;
      final AtomicInteger connCount = new AtomicInteger(0);
      for (int i = 0; i < numConnections; i++) {
        AsyncResultHandler<NetSocket> handler = res -> {
          if (res.succeeded()) {
            res.result().close();
            if (connCount.incrementAndGet() == numConnections) {
              testComplete();
            }
          }
        };
        client.connect(port, host, handler);
      }
    });
    await();
  }

  @Test
  public void testConnectInvalidPort() {
    assertIllegalArgumentException(() -> client.connect(-1, "localhost", res -> {}));
    assertIllegalArgumentException(() -> client.connect(65536, "localhost", res -> {}));
    client.connect(9998, "localhost", res -> {
      assertTrue(res.failed());
      assertFalse(res.succeeded());
      assertNotNull(res.cause());
      testComplete();
    });
    await();
  }

  @Test
  public void testConnectInvalidHost() {
    assertNullPointerException(() -> client.connect(80, null, res -> {}));
    client.connect(1234, "127.0.0.2", res -> {
      assertTrue(res.failed());
      assertFalse(res.succeeded());
      assertNotNull(res.cause());
      testComplete();
    });
    await();
  }

  @Test
  public void testConnectInvalidConnectHandler() throws Exception {
    assertNullPointerException(() -> client.connect(80, "localhost", null));
  }

  @Test
  public void testListenInvalidPort() {
    /* Port 80 is free to use by any application on Windows, so this test fails. */
    Assume.assumeFalse(System.getProperty("os.name").startsWith("Windows"));
    server.close();
    server = vertx.createNetServer(new NetServerOptions().setPort(80));
    server.connectHandler((netSocket) -> {
    }).listen(ar -> {
      assertTrue(ar.failed());
      assertFalse(ar.succeeded());
      assertNotNull(ar.cause());
      testComplete();
    });
    await();
  }

  @Test
  public void testListenInvalidHost() {
    server.close();
    server = vertx.createNetServer(new NetServerOptions().setPort(1234).setHost("uhqwduhqwudhqwuidhqwiudhqwudqwiuhd"));
    server.connectHandler(netSocket -> {
    }).listen(ar -> {
      assertTrue(ar.failed());
      assertFalse(ar.succeeded());
      assertNotNull(ar.cause());
      testComplete();
    });
    await();
  }

  @Test
  public void testListenOnWildcardPort() {
    server.close();
    server = vertx.createNetServer(new NetServerOptions().setPort(0));
    server.connectHandler((netSocket) -> {
    }).listen(ar -> {
      assertFalse(ar.failed());
      assertTrue(ar.succeeded());
      assertNull(ar.cause());
      assertTrue(server.actualPort() > 1024);
      assertEquals(server, ar.result());
      testComplete();
    });
    await();
  }

  @Test
  public void testClientCloseHandlersCloseFromClient() {
    startEchoServer(s -> clientCloseHandlers(true));
    await();
  }

  @Test
  public void testClientCloseHandlersCloseFromServer() {
    server.connectHandler((netSocket) -> netSocket.close()).listen((s) -> clientCloseHandlers(false));
    await();
  }

  void clientCloseHandlers(boolean closeFromClient) {
    client.connect(1234, "localhost", ar -> {
      AtomicInteger counter = new AtomicInteger(0);
      ar.result().endHandler(v -> assertEquals(1, counter.incrementAndGet()));
      ar.result().closeHandler(v -> {
        assertEquals(2, counter.incrementAndGet());
        testComplete();
      });
      if (closeFromClient) {
        ar.result().close();
      }
    });
  }

  @Test
  public void testServerCloseHandlersCloseFromClient() {
    serverCloseHandlers(false, s -> client.connect(1234, "localhost", ar -> ar.result().close()));
    await();
  }

  @Test
  public void testServerCloseHandlersCloseFromServer() {
    serverCloseHandlers(true, s -> client.connect(1234, "localhost", ar -> {
    }));
    await();
  }

  void serverCloseHandlers(boolean closeFromServer, Handler<AsyncResult<NetServer>> listenHandler) {
    server.connectHandler((sock) -> {
      AtomicInteger counter = new AtomicInteger(0);
      sock.endHandler(v -> assertEquals(1, counter.incrementAndGet()));
      sock.closeHandler(v -> {
        assertEquals(2, counter.incrementAndGet());
        testComplete();
      });
      if (closeFromServer) {
        sock.close();
      }
    }).listen(listenHandler);
  }

  @Test
  public void testClientDrainHandler() {
    pausingServer((s) -> {
      client.connect(1234, "localhost", ar -> {
        NetSocket sock = ar.result();
        assertFalse(sock.writeQueueFull());
        sock.setWriteQueueMaxSize(1000);
        Buffer buff = TestUtils.randomBuffer(10000);
        vertx.setPeriodic(1, id -> {
          sock.write(buff.copy());
          if (sock.writeQueueFull()) {
            vertx.cancelTimer(id);
            sock.drainHandler(v -> {
              assertFalse(sock.writeQueueFull());
              testComplete();
            });
            // Tell the server to resume
            vertx.eventBus().send("server_resume", "");
          }
        });
      });
    });
    await();
  }

  void pausingServer(Handler<AsyncResult<NetServer>> listenHandler) {
    server.connectHandler(sock -> {
      sock.pause();
      Handler<Message<Buffer>> resumeHandler = (m) -> sock.resume();
      MessageConsumer reg = vertx.eventBus().<Buffer>consumer("server_resume").handler(resumeHandler);
      sock.closeHandler(v -> reg.unregister());
    }).listen(listenHandler);
  }

  @Test
  public void testServerDrainHandler() {
    drainingServer(s -> {
      client.connect(1234, "localhost", ar -> {
        NetSocket sock = ar.result();
        sock.pause();
        setHandlers(sock);
        sock.handler(buf -> {
        });
      });
    });
    await();
  }

  void setHandlers(NetSocket sock) {
    Handler<Message<Buffer>> resumeHandler = m -> sock.resume();
    MessageConsumer reg = vertx.eventBus().<Buffer>consumer("client_resume").handler(resumeHandler);
    sock.closeHandler(v -> reg.unregister());
  }

  void drainingServer(Handler<AsyncResult<NetServer>> listenHandler) {
    server.connectHandler(sock -> {
      assertFalse(sock.writeQueueFull());
      sock.setWriteQueueMaxSize(1000);

      Buffer buff = TestUtils.randomBuffer(10000);
      //Send data until the buffer is full
      vertx.setPeriodic(1, id -> {
        sock.write(buff.copy());
        if (sock.writeQueueFull()) {
          vertx.cancelTimer(id);
          sock.drainHandler(v -> {
            assertFalse(sock.writeQueueFull());
            // End test after a short delay to give the client some time to read the data
            vertx.setTimer(100, id2 -> testComplete());
          });

          // Tell the client to resume
          vertx.eventBus().send("client_resume", "");
        }
      });
    }).listen(listenHandler);
  }

  @Test
  public void testReconnectAttemptsInfinite() {
    reconnectAttempts(-1);
  }

  @Test
  public void testReconnectAttemptsMany() {
    reconnectAttempts(100000);
  }

  void reconnectAttempts(int attempts) {
    client.close();
    client = vertx.createNetClient(new NetClientOptions().setReconnectAttempts(attempts).setReconnectInterval(10));

    //The server delays starting for a a few seconds, but it should still connect
    client.connect(1234, "localhost", (res) -> {
      assertTrue(res.succeeded());
      assertFalse(res.failed());
      testComplete();
    });

    // Start the server after a delay
    vertx.setTimer(2000, id -> startEchoServer(s -> {
    }));

    await();
  }

  @Test
  public void testReconnectAttemptsNotEnough() {
    client.close();
    client = vertx.createNetClient(new NetClientOptions().setReconnectAttempts(100).setReconnectInterval(10));

    client.connect(1234, "localhost", (res) -> {
      assertFalse(res.succeeded());
      assertTrue(res.failed());
      testComplete();
    });

    await();
  }

  @Test
  public void testServerIdleTimeout() {
    server.close();
    server = vertx.createNetServer(new NetServerOptions().setPort(1234).setHost("localhost").setIdleTimeout(1));
    server.connectHandler(s -> {}).listen(ar -> {
      assertTrue(ar.succeeded());
      client.connect(1234, "localhost", res -> {
        assertTrue(res.succeeded());
        NetSocket socket = res.result();
        socket.closeHandler(v -> testComplete());
      });
    });
    await();
  }

  @Test
  public void testClientIdleTimeout() {
    client.close();
    client = vertx.createNetClient(new NetClientOptions().setIdleTimeout(1));

    server.connectHandler(s -> {
    }).listen(ar -> {
      assertTrue(ar.succeeded());
      client.connect(1234, "localhost", res -> {
        assertTrue(res.succeeded());
        NetSocket socket = res.result();
        socket.closeHandler(v -> testComplete());
      });
    });


    await();
  }

  @Test
  // StartTLS
  public void testStartTLSClientTrustAll() throws Exception {
    testTLS(false, false, true, false, false, true, true, true);
  }

  @Test
  // Client trusts all server certs
  public void testTLSClientTrustAll() throws Exception {
    testTLS(false, false, true, false, false, true, true, false);
  }

  @Test
  // Server specifies cert that the client trusts (not trust all)
  public void testTLSClientTrustServerCert() throws Exception {
    testTLS(false, true, true, false, false, false, true, false);
  }

  @Test
  // Server specifies cert that the client doesn't trust
  public void testTLSClientUntrustedServer() throws Exception {
    testTLS(false, false, true, false, false, false, false, false);
  }

  @Test
  //Client specifies cert even though it's not required
  public void testTLSClientCertNotRequired() throws Exception {
    testTLS(true, true, true, true, false, false, true, false);
  }

  @Test
  //Client specifies cert and it's not required
  public void testTLSClientCertRequired() throws Exception {
    testTLS(true, true, true, true, true, false, true, false);
  }

  @Test
  //Client doesn't specify cert but it's required
  public void testTLSClientCertRequiredNoClientCert() throws Exception {
    testTLS(false, true, true, true, true, false, false, false);
  }

  @Test
  //Client specifies cert but it's not trusted
  public void testTLSClientCertClientNotTrusted() throws Exception {
    testTLS(true, true, true, false, true, false, false, false);
  }

  @Test
  // Specify some cipher suites
  public void testTLSCipherSuites() throws Exception {
    testTLS(false, false, true, false, false, true, true, false, ENABLED_CIPHER_SUITES);
  }

  void testTLS(boolean clientCert, boolean clientTrust,
               boolean serverCert, boolean serverTrust,
               boolean requireClientAuth, boolean clientTrustAll,
               boolean shouldPass, boolean startTLS,
               String... enabledCipherSuites) throws Exception {
    server.close();
    NetServerOptions options = new NetServerOptions();
    if (!startTLS) {
      options.setSsl(true);
    }
    if (serverTrust) {
      options.setTrustStoreOptions(new JksOptions().setPath(findFileOnClasspath("tls/server-truststore.jks")).setPassword("wibble"));
    }
    if (serverCert) {
      options.setKeyStoreOptions(new JksOptions().setPath(findFileOnClasspath("tls/server-keystore.jks")).setPassword("wibble"));
    }
    if (requireClientAuth) {
      options.setClientAuthRequired(true);
    }
    for (String suite: enabledCipherSuites) {
      options.addEnabledCipherSuite(suite);
    }

    options.setPort(4043);
    server = vertx.createNetServer(options);
    Handler<NetSocket> serverHandler = socket -> {
      try {
        X509Certificate[] certs = socket.peerCertificateChain();
        if (clientCert) {
          assertNotNull(certs);
          assertEquals(1, certs.length);
        } else {
          assertNull(certs);
        }
        System.out.println("certs are " + certs);
      } catch (SSLPeerUnverifiedException e) {
        assertTrue(clientTrust || clientTrustAll);
      }

      AtomicBoolean upgradedServer = new AtomicBoolean();
      socket.handler(buff -> {
        socket.write(buff); // echo the data
        if (startTLS && !upgradedServer.get()) {
          assertFalse(socket.isSsl());
          socket.upgradeToSsl(v -> assertTrue(socket.isSsl()));
          upgradedServer.set(true);
        } else {
          assertTrue(socket.isSsl());
        }
      });
    };
    server.connectHandler(serverHandler).listen(ar -> {
      client.close();
      NetClientOptions clientOptions = new NetClientOptions();
      if (!startTLS) {
        clientOptions.setSsl(true);
        if (clientTrustAll) {
          clientOptions.setTrustAll(true);
        }
        if (clientTrust) {
          clientOptions.setTrustStoreOptions(new JksOptions().setPath(findFileOnClasspath("tls/client-truststore.jks")).setPassword("wibble"));
        }
        if (clientCert) {
          clientOptions.setKeyStoreOptions(new JksOptions().setPath(findFileOnClasspath("tls/client-keystore.jks")).setPassword("wibble"));
        }
        for (String suite: enabledCipherSuites) {
          clientOptions.addEnabledCipherSuite(suite);
        }
      }
      client = vertx.createNetClient(clientOptions);
      client.connect(4043, "localhost", ar2 -> {
        if (ar2.succeeded()) {
          if (!shouldPass) {
            fail("Should not connect");
            return;
          }
          final int numChunks = 100;
          final int chunkSize = 100;
          final Buffer received = Buffer.buffer();
          final Buffer sent = Buffer.buffer();
          final NetSocket socket = ar2.result();

          final AtomicBoolean upgradedClient = new AtomicBoolean();
          socket.handler(buffer -> {
            received.appendBuffer(buffer);
            if (received.length() == sent.length()) {
              assertEquals(sent, received);
              testComplete();
            }
            if (startTLS && !upgradedClient.get()) {
              assertFalse(socket.isSsl());
              socket.upgradeToSsl(v -> {
                assertTrue(socket.isSsl());
                // Now send the rest
                for (int i = 1; i < numChunks; i++) {
                  sendBuffer(socket, sent, chunkSize);
                }
              });
            } else {
              assertTrue(socket.isSsl());
            }
          });

          //Now send some data
          int numToSend = startTLS ? 1 : numChunks;
          for (int i = 0; i < numToSend; i++) {
            sendBuffer(socket, sent, chunkSize);
          }
        } else {
          if (shouldPass) {
            fail("Should not fail to connect");
          } else {
            testComplete();
          }
        }
      });
    });
    await();
  }

  void sendBuffer(NetSocket socket, Buffer sent, int chunkSize) {
    Buffer buff = TestUtils.randomBuffer(chunkSize);
    sent.appendBuffer(buff);
    socket.write(buff);
  }

  @Test
  // Need to:
  // sudo sysctl -w net.core.somaxconn=10000
  // sudo sysctl -w net.ipv4.tcp_max_syn_backlog=10000
  // To get this to reliably pass with a lot of connections.
  public void testSharedServersRoundRobin() throws Exception {

    int numServers = 5;
    int numConnections = numServers * 20;

    List<NetServer> servers = new ArrayList<>();
    Set<NetServer> connectedServers = new ConcurrentHashSet<>();
    Map<NetServer, Integer> connectCount = new ConcurrentHashMap<>();

    CountDownLatch latchListen = new CountDownLatch(numServers);
    CountDownLatch latchConns = new CountDownLatch(numConnections);
    for (int i = 0; i < numServers; i++) {
      NetServer theServer = vertx.createNetServer(new NetServerOptions().setHost("localhost").setPort(1234));
      servers.add(theServer);
      theServer.connectHandler(sock -> {
        connectedServers.add(theServer);
        Integer cnt = connectCount.get(theServer);
        int icnt = cnt == null ? 0 : cnt;
        icnt++;
        connectCount.put(theServer, icnt);
        latchConns.countDown();
      }).listen(ar -> {
        if (ar.succeeded()) {
          latchListen.countDown();
        } else {
          fail("Failed to bind server");
        }
      });
    }
    assertTrue(latchListen.await(10, TimeUnit.SECONDS));

    // Create a bunch of connections
    client.close();
    client = vertx.createNetClient(new NetClientOptions());
    CountDownLatch latchClient = new CountDownLatch(numConnections);
    for (int i = 0; i < numConnections; i++) {
      client.connect(1234, "localhost", res -> {
        if (res.succeeded()) {
          latchClient.countDown();
        } else {
          res.cause().printStackTrace();
          fail("Failed to connect");
        }
      });
    }

    assertTrue(latchClient.await(10, TimeUnit.SECONDS));
    assertTrue(latchConns.await(10, TimeUnit.SECONDS));

    assertEquals(numServers, connectedServers.size());
    for (NetServer server : servers) {
      assertTrue(connectedServers.contains(server));
    }
    assertEquals(numServers, connectCount.size());
    for (int cnt : connectCount.values()) {
      assertEquals(numConnections / numServers, cnt);
    }

    CountDownLatch closeLatch = new CountDownLatch(numServers);

    for (NetServer server : servers) {
      server.close(ar -> {
        assertTrue(ar.succeeded());
        closeLatch.countDown();
      });
    }

    assertTrue(closeLatch.await(10, TimeUnit.SECONDS));

    testComplete();
  }

  @Test
  public void testSharedServersRoundRobinWithOtherServerRunningOnDifferentPort() throws Exception {
    CountDownLatch latch = new CountDownLatch(1);
    // Have a server running on a different port to make sure it doesn't interact
    server.close();
    server = vertx.createNetServer(new NetServerOptions().setPort(4321));
    server.connectHandler(sock -> {
      fail("Should not connect");
    }).listen(ar2 -> {
      if (ar2.succeeded()) {
        latch.countDown();
      } else {
        fail("Failed to bind server");
      }
    });
    awaitLatch(latch);
    testSharedServersRoundRobin();
  }

  @Test
  public void testSharedServersRoundRobinButFirstStartAndStopServer() throws Exception {
    // Start and stop a server on the same port/host before hand to make sure it doesn't interact
    server.close();
    CountDownLatch latch = new CountDownLatch(1);
    server = vertx.createNetServer(new NetServerOptions().setPort(1234));
    server.connectHandler(sock -> {
      fail("Should not connect");
    }).listen(ar -> {
      if (ar.succeeded()) {
        latch.countDown();
      } else {
        fail("Failed to bind server");
      }
    });
    awaitLatch(latch);
    CountDownLatch closeLatch = new CountDownLatch(1);
    server.close(ar -> {
      assertTrue(ar.succeeded());
      closeLatch.countDown();
    });
    assertTrue(closeLatch.await(10, TimeUnit.SECONDS));
    testSharedServersRoundRobin();
  }

  @Test
  // This tests using NetSocket.writeHandlerID (on the server side)
  // Send some data and make sure it is fanned out to all connections
  public void testFanout() throws Exception {

    CountDownLatch latch = new CountDownLatch(1);
    Set<String> connections = new ConcurrentHashSet<>();
    server.connectHandler(socket -> {
      connections.add(socket.writeHandlerID());
      socket.handler(buffer -> {
        for (String actorID : connections) {
          vertx.eventBus().publish(actorID, buffer);
        }
      });
      socket.closeHandler(v -> {
        connections.remove(socket.writeHandlerID());
      });
    });
    server.listen(ar -> {
      assertTrue(ar.succeeded());
      latch.countDown();
    });
    awaitLatch(latch);

    int numConnections = 10;
    CountDownLatch connectLatch = new CountDownLatch(numConnections);
    CountDownLatch receivedLatch = new CountDownLatch(numConnections);
    for (int i = 0; i < numConnections; i++) {
      client.connect(1234, "localhost", res -> {
        connectLatch.countDown();
        res.result().handler(data -> {
          receivedLatch.countDown();
        });
      });
    }
    assertTrue(connectLatch.await(10, TimeUnit.SECONDS));

    // Send some data
    client.connect(1234, "localhost", res -> {
      res.result().write("foo");
    });
    assertTrue(receivedLatch.await(10, TimeUnit.SECONDS));

    testComplete();
  }

  @Test
  public void testRemoteAddress() throws Exception {
    server.connectHandler(socket -> {
      SocketAddress addr = socket.remoteAddress();
      assertEquals("127.0.0.1", addr.host());
    }).listen(ar -> {
      assertTrue(ar.succeeded());
      vertx.createNetClient(new NetClientOptions()).connect(1234, "localhost", result -> {
        NetSocket socket = result.result();
        SocketAddress addr = socket.remoteAddress();
        assertEquals("127.0.0.1", addr.host());
        assertEquals(addr.port(), 1234);
        testComplete();
      });
    });
    await();
  }

  @Test
  public void testWriteSameBufferMoreThanOnce() throws Exception {
    server.connectHandler(socket -> {
      Buffer received = Buffer.buffer();
      socket.handler(buff -> {
        received.appendBuffer(buff);
        if (received.toString().equals("foofoo")) {
          testComplete();
        }
      });
    }).listen(ar -> {
      assertTrue(ar.succeeded());
      client.connect(1234, "localhost", result -> {
        NetSocket socket = result.result();
        Buffer buff = Buffer.buffer("foo");
        socket.write(buff);
        socket.write(buff);
      });
    });
    await();
  }

  @Test
  public void sendFileClientToServer() throws Exception {
    File fDir = testFolder.newFolder();
    String content = TestUtils.randomUnicodeString(10000);
    File file = setupFile(fDir.toString(), "some-file.txt", content);
    Buffer expected = Buffer.buffer(content);
    Buffer received = Buffer.buffer();
    server.connectHandler(sock -> {
      sock.handler(buff -> {
        received.appendBuffer(buff);
        if (received.length() == expected.length()) {
          assertEquals(expected, received);
          testComplete();
        }
      });
      // Send some data to the client to trigger the sendfile
      sock.write("foo");
    });
    server.listen(ar -> {
      assertTrue(ar.succeeded());
      client.connect(1234, "localhost", ar2 -> {
        assertTrue(ar2.succeeded());
        NetSocket sock = ar2.result();
        sock.handler(buf -> {
          sock.sendFile(file.getAbsolutePath());
        });
      });
    });

    await();
  }

  @Test
  public void sendFileServerToClient() throws Exception {
    File fDir = testFolder.newFolder();
    String content = TestUtils.randomUnicodeString(10000);
    File file = setupFile(fDir.toString(), "some-file.txt", content);
    Buffer expected = Buffer.buffer(content);
    Buffer received = Buffer.buffer();
    server.connectHandler(sock -> {
      sock.handler(buf -> {
        sock.sendFile(file.getAbsolutePath());
      });
    });
    server.listen(ar -> {
      assertTrue(ar.succeeded());
      client.connect(1234, "localhost", ar2 -> {
        assertTrue(ar2.succeeded());
        NetSocket sock = ar2.result();
        sock.handler(buff -> {
          received.appendBuffer(buff);
          if (received.length() == expected.length()) {
            assertEquals(expected, received);
            testComplete();
          }
        });
        sock.write("foo");
      });
    });

    await();
  }

  @Test
  public void testSendFileDirectory() throws Exception {
    File fDir = testFolder.newFolder();
    server.connectHandler(socket -> {
      SocketAddress addr = socket.remoteAddress();
      assertEquals("127.0.0.1", addr.host());
    }).listen(ar -> {
      assertTrue(ar.succeeded());
      client.connect(1234, "localhost", result -> {
        assertTrue(result.succeeded());
        NetSocket socket = result.result();
        try {
          socket.sendFile(fDir.getAbsolutePath().toString());
          // should throw exception and never hit the assert
          fail("Should throw exception");
        } catch (IllegalArgumentException e) {
          testComplete();
        }
      });
    });
    await();
  }

  @Test
  public void testServerOptionsCopiedBeforeUse() {
    server.close();
    NetServerOptions options = new NetServerOptions().setPort(1234);
    NetServer server = vertx.createNetServer(options);
    // Now change something - but server should still listen at previous port
    options.setPort(1235);
    server.connectHandler(sock -> {
      testComplete();
    });
    server.listen(ar -> {
      assertTrue(ar.succeeded());
      client.connect(1234, "localhost", ar2 -> {
        assertTrue(ar2.succeeded());
      });
    });
    await();
  }

  @Test
  public void testClientOptionsCopiedBeforeUse() {
    client.close();
    NetClientOptions options = new NetClientOptions();
    client = vertx.createNetClient(options);
    options.setSsl(true);
    // Now change something - but server should ignore this
    server.connectHandler(sock -> {
      testComplete();
    });
    server.listen(ar -> {
      assertTrue(ar.succeeded());
      client.connect(1234, "localhost", ar2 -> {
        assertTrue(ar2.succeeded());
      });
    });
    await();
  }

  @Test
  public void testListenWithNoHandler() {
    try {
      server.listen();
      fail("Should throw exception");
    } catch (IllegalStateException e) {
      // OK
    }
  }

  @Test
  public void testListenWithNoHandler2() {
    try {
      server.listen(ar -> {
        assertFalse(ar.succeeded());
      });
      fail("Should throw exception");
    } catch (IllegalStateException e) {
      // OK
    }
  }

  @Test
  public void testSetHandlerAfterListen() {
    server.connectHandler(sock -> {
    });
    server.listen();
    try {
      server.connectHandler(sock -> {
      });
      fail("Should throw exception");
    } catch (IllegalStateException e) {
      // OK
    }
  }

  @Test
  public void testSetHandlerAfterListen2() {
    server.connectHandler(sock -> {
    });
    server.listen(ar -> {
      assertTrue(ar.succeeded());
      try {
        server.connectHandler(sock -> {
        });
        fail("Should throw exception");
      } catch (IllegalStateException e) {
        // OK
      }
      testComplete();
    });
    await();
  }

  @Test
  public void testListenTwice() {
    server.connectHandler(sock -> {
    });
    server.listen(onSuccess(s -> {
      try {
        server.listen(res -> {});
        fail("Should throw exception");
      } catch (IllegalStateException e) {
        // OK
        testComplete();
      } catch (Exception e) {
        fail(e.getMessage());
      }
    }));
    await();
  }

  @Test
  public void testListenTwice2() {
    server.connectHandler(sock -> {
    });
    server.listen(ar -> {
      assertTrue(ar.succeeded());
      try {
        server.listen(sock -> {
        });
        fail("Should throw exception");
      } catch (IllegalStateException e) {
        // OK
      }
      testComplete();
    });
    await();
  }

  @Test
  public void testCloseTwice() {
    client.close();
    client.close(); // OK
  }

  @Test
  public void testAttemptConnectAfterClose() {
    client.close();
    try {
      client.connect(1234, "localhost", ar -> {
      });
      fail("Should throw exception");
    } catch (IllegalStateException e) {
      //OK
    }
  }

  @Test
  public void testClientMultiThreaded() throws Exception {
    int numThreads = 10;
    Thread[] threads = new Thread[numThreads];
    CountDownLatch latch = new CountDownLatch(numThreads);
    server.connectHandler(socket -> {
      socket.handler(socket::write);
    }).listen(ar -> {
      assertTrue(ar.succeeded());
      for (int i = 0; i < numThreads; i++) {
        threads[i] = new Thread() {
          public void run() {
            client.connect(1234, "localhost", result -> {
              assertTrue(result.succeeded());
              Buffer buff = TestUtils.randomBuffer(100000);
              NetSocket sock = result.result();
              sock.write(buff);
              Buffer received = Buffer.buffer();
              sock.handler(rec -> {
                received.appendBuffer(rec);
                if (received.length() == buff.length()) {
                  assertEquals(buff, received);
                  latch.countDown();
                }
              });
            });
          }
        };
        threads[i].start();
      }
    });
    awaitLatch(latch);
    for (int i = 0; i < numThreads; i++) {
      threads[i].join();
    }
  }

  @Test
  public void testInVerticle() throws Exception {
    testInVerticle(false);
  }

  private void testInVerticle(boolean worker) throws Exception {
    client.close();
    server.close();
    class MyVerticle extends AbstractVerticle {
      Context ctx;
      @Override
      public void start() {
        ctx = context;
        if (worker) {
          assertTrue(ctx instanceof WorkerContext);
        } else {
          assertTrue(ctx instanceof EventLoopContext);
        }
        Thread thr = Thread.currentThread();
        server = vertx.createNetServer(new NetServerOptions().setPort(1234).setHost("localhost"));
        server.connectHandler(sock -> {
          sock.handler(buff -> {
            sock.write(buff);
          });
          assertSame(ctx, context);
          if (!worker) {
            assertSame(thr, Thread.currentThread());
          }
        });
        server.listen(ar -> {
          assertTrue(ar.succeeded());
          assertSame(ctx, context);
          if (!worker) {
            assertSame(thr, Thread.currentThread());
          }
          client = vertx.createNetClient(new NetClientOptions());
          client.connect(1234, "localhost", ar2 -> {
            assertSame(ctx, context);
            if (!worker) {
              assertSame(thr, Thread.currentThread());
            }
            assertTrue(ar2.succeeded());
            NetSocket sock = ar2.result();
            Buffer buff = TestUtils.randomBuffer(10000);
            sock.write(buff);
            Buffer brec = Buffer.buffer();
            sock.handler(rec -> {
              assertSame(ctx, context);
              if (!worker) {
                assertSame(thr, Thread.currentThread());
              }
              brec.appendBuffer(rec);
              if (brec.length() == buff.length()) {
                testComplete();
              }
            });
          });
        });
      }
    }
    MyVerticle verticle = new MyVerticle();
    vertx.deployVerticle(verticle, new DeploymentOptions().setWorker(worker));
    await();
  }

  @Test
  public void testInMultithreadedWorker() throws Exception {
    class MyVerticle extends AbstractVerticle {
      @Override
      public void start() {
        try {
          server = vertx.createNetServer(new NetServerOptions());
          fail("Should throw exception");
        } catch (IllegalStateException e) {
          // OK
        }
        try {
          client = vertx.createNetClient(new NetClientOptions());
          fail("Should throw exception");
        } catch (IllegalStateException e) {
          // OK
        }
        testComplete();
      }
    }
    MyVerticle verticle = new MyVerticle();
    vertx.deployVerticle(verticle, new DeploymentOptions().setWorker(true).setMultiThreaded(true));
    await();
  }

  @Test
  public void testContexts() throws Exception {
    Set<ContextImpl> contexts = new ConcurrentHashSet<>();
    AtomicInteger cnt = new AtomicInteger();
    AtomicReference<ContextImpl> serverConnectContext = new AtomicReference<>();
    // Server connect handler should always be called with same context
    server.connectHandler(sock -> {
      sock.handler(sock::write);
      ContextImpl serverContext = ((VertxInternal) vertx).getContext();
      if (serverConnectContext.get() != null) {
        assertSame(serverConnectContext.get(), serverContext);
      } else {
        serverConnectContext.set(serverContext);
      }
    });
    CountDownLatch latch = new CountDownLatch(1);
    AtomicReference<ContextImpl> listenContext = new AtomicReference<>();
    server.listen(ar -> {
      assertTrue(ar.succeeded());
      listenContext.set(((VertxInternal) vertx).getContext());
      latch.countDown();
    });
    awaitLatch(latch);
    CountDownLatch latch2 = new CountDownLatch(1);
    int numConns = 10;
    // Each connect should be in its own context
    for (int i = 0; i < numConns; i++) {
      client.connect(1234, "localhost", conn -> {
        contexts.add(((VertxInternal) vertx).getContext());
        if (cnt.incrementAndGet() == numConns) {
          assertEquals(numConns, contexts.size());
          latch2.countDown();
        }
      });
    }
    awaitLatch(latch2);
    // Close should be in own context
    server.close(ar -> {
      assertTrue(ar.succeeded());
      ContextImpl closeContext = ((VertxInternal) vertx).getContext();
      assertFalse(contexts.contains(closeContext));
      assertNotSame(serverConnectContext.get(), closeContext);
      assertFalse(contexts.contains(listenContext.get()));
      assertSame(serverConnectContext.get(), listenContext.get());
      testComplete();
    });

    server = null;
    await();
  }

  @Test
  public void testReadStreamPauseResume() {
    server.close();
    server = vertx.createNetServer(new NetServerOptions().setAcceptBacklog(1).setPort(1234).setHost("localhost"));
    NetSocketStream socketStream = server.connectStream();
    AtomicBoolean paused = new AtomicBoolean();
    socketStream.handler(so -> {
      assertTrue(!paused.get());
      so.write("hello");
      so.close();
    });
    server.listen(ar -> {
      assertTrue(ar.succeeded());
      paused.set(true);
      socketStream.pause();
      client.connect(1234, "localhost", ar2 -> {
        assertTrue(ar2.succeeded());
        NetSocket so2 = ar2.result();
        so2.handler(buffer -> {
          fail();
        });
        so2.closeHandler(v -> {
          paused.set(false);
          socketStream.resume();
          client.connect(1234, "localhost", ar3 -> {
            assertTrue(ar3.succeeded());
            NetSocket so3 = ar3.result();
            Buffer buffer = Buffer.buffer();
            so3.handler(buffer::appendBuffer);
            so3.closeHandler(v3 -> {
              assertEquals("hello", buffer.toString("utf-8"));
              testComplete();
            });
          });
        });
      });
    });
    await();
  }

  @Test
  public void testNetSocketStreamCallbackIsAsync() {
    this.server = vertx.createNetServer(new NetServerOptions());
    AtomicInteger done = new AtomicInteger();
    NetSocketStream stream = server.connectStream();
    stream.handler(req -> {});
    ThreadLocal<Object> stack = new ThreadLocal<>();
    stack.set(true);
    stream.endHandler(v -> {
      assertTrue(Vertx.currentContext().isEventLoopContext());
      assertNull(stack.get());
      if (done.incrementAndGet() == 2) {
        testComplete();
      }
    });
    server.listen(ar -> {
      assertTrue(Vertx.currentContext().isEventLoopContext());
      assertNull(stack.get());
      ThreadLocal<Object> stack2 = new ThreadLocal<>();
      stack2.set(true);
      server.close(v -> {
        assertTrue(Vertx.currentContext().isEventLoopContext());
        assertNull(stack2.get());
        if (done.incrementAndGet() == 2) {
          testComplete();
        }
      });
      stack2.set(null);
    });
    await();
  }

  @Test
  public void testMultipleServerClose() {
    this.server = vertx.createNetServer(new NetServerOptions());
    AtomicInteger times = new AtomicInteger();
    // We assume the endHandler and the close completion handler are invoked in the same context task
    ThreadLocal stack = new ThreadLocal();
    stack.set(true);
    server.connectStream().endHandler(v -> {
      assertNull(stack.get());
      assertTrue(Vertx.currentContext().isEventLoopContext());
      times.incrementAndGet();
    });
    server.close(ar1 -> {
      assertNull(stack.get());
      assertTrue(Vertx.currentContext().isEventLoopContext());
      server.close(ar2 -> {
        server.close(ar3 -> {
          assertEquals(1, times.get());
          testComplete();
        });
      });
    });
    await();
  }

  @Test
  public void testInWorker() throws Exception {
    vertx.deployVerticle(new AbstractVerticle() {
      @Override
      public void start() throws Exception {
        assertTrue(Vertx.currentContext().isWorkerContext());
        assertTrue(Context.isOnWorkerThread());
        final Context context = Vertx.currentContext();
        NetServer server1 = vertx.createNetServer(new NetServerOptions().setHost("localhost").setPort(1234));
        server1.connectHandler(conn -> {
          assertTrue(Vertx.currentContext().isWorkerContext());
          assertTrue(Context.isOnWorkerThread());
          assertSame(context, Vertx.currentContext());
          conn.handler(conn::write);
          conn.closeHandler(v -> {
            testComplete();
          });
        }).listen(onSuccess(s -> {
          assertTrue(Vertx.currentContext().isWorkerContext());
          assertTrue(Context.isOnWorkerThread());
          assertSame(context, Vertx.currentContext());
          NetClient client = vertx.createNetClient();
          client.connect(1234, "localhost", onSuccess(res -> {
            assertTrue(Vertx.currentContext().isWorkerContext());
            assertTrue(Context.isOnWorkerThread());
            assertSame(context, Vertx.currentContext());
            res.write("foo");
            res.handler(buff -> {
              assertTrue(Vertx.currentContext().isWorkerContext());
              assertTrue(Context.isOnWorkerThread());
              assertSame(context, Vertx.currentContext());
              res.close();
            });
          }));
        }));
      }
    }, new DeploymentOptions().setWorker(true));
    await();
  }


  private File setupFile(String testDir, String fileName, String content) throws Exception {
    File file = new File(testDir, fileName);
    if (file.exists()) {
      file.delete();
    }
    BufferedWriter out = new BufferedWriter(new OutputStreamWriter(new FileOutputStream(file), "UTF-8"));
    out.write(content);
    out.close();
    return file;
  }

  @Test
  public void testServerWorkerMissBufferWhenBufferArriveBeforeConnectCallback() throws Exception {
    int size = getOptions().getWorkerPoolSize();
    List<Context> workers = createWorkers(size + 1);
    CountDownLatch latch1 = new CountDownLatch(workers.size() - 1);
    workers.get(0).runOnContext(v -> {
      NetServer server = vertx.createNetServer();
      server.connectHandler(so -> {
        so.handler(buf -> {
          assertEquals("hello", buf.toString());
          testComplete();
        });
      });
      server.listen(1234, ar -> {
        assertTrue(ar.succeeded());
        // Create a one second worker starvation
        for (int i = 1; i < workers.size(); i++) {
          workers.get(i).runOnContext(v2 -> {
            latch1.countDown();
            try {
              Thread.sleep(1000);
            } catch (InterruptedException ignore) {
            }
          });
        }
      });
    });
    awaitLatch(latch1);
    NetClient client = vertx.createNetClient();
    client.connect(1234, "localhost", ar -> {
      assertTrue(ar.succeeded());
      NetSocket so = ar.result();
      so.write(Buffer.buffer("hello"));
    });
    await();
  }

  @Test
  public void testClientWorkerMissBufferWhenBufferArriveBeforeConnectCallback() throws Exception {
    int size = getOptions().getWorkerPoolSize();
    List<Context> workers = createWorkers(size + 1);
    CountDownLatch latch1 = new CountDownLatch(1);
    CountDownLatch latch2 = new CountDownLatch(size);
    NetServer server = vertx.createNetServer();
    server.connectHandler(so -> {
      try {
        awaitLatch(latch2);
      } catch (InterruptedException e) {
        fail(e.getMessage());
        return;
      }
      so.write(Buffer.buffer("hello"));
    });
    server.listen(1234, ar -> {
      assertTrue(ar.succeeded());
      latch1.countDown();
    });
    awaitLatch(latch1);
    workers.get(0).runOnContext(v -> {
      NetClient client = vertx.createNetClient();
      client.connect(1234, "localhost", ar -> {
        assertTrue(ar.succeeded());
        NetSocket so = ar.result();
        so.handler(buf -> {
          assertEquals("hello", buf.toString());
          testComplete();
        });
      });
      // Create a one second worker starvation
      for (int i = 1; i < workers.size(); i++) {
        workers.get(i).runOnContext(v2 -> {
          latch2.countDown();
          try {
            Thread.sleep(1000);
          } catch (InterruptedException ignore) {
          }
        });
      }
    });
    await();
  }
}
