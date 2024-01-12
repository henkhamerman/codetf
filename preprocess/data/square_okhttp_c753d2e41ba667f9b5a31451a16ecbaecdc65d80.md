Refactoring Types: ['Move Class']
a/com/squareup/okhttp/mockwebserver/MockWebServer.java
/*
 * Copyright (C) 2011 Google Inc.
 * Copyright (C) 2013 Square, Inc.
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

package com.squareup.okhttp.mockwebserver;

import com.squareup.okhttp.Headers;
import com.squareup.okhttp.Protocol;
import com.squareup.okhttp.Request;
import com.squareup.okhttp.Response;
import com.squareup.okhttp.internal.NamedRunnable;
import com.squareup.okhttp.internal.Platform;
import com.squareup.okhttp.internal.Util;
import com.squareup.okhttp.internal.spdy.ErrorCode;
import com.squareup.okhttp.internal.spdy.Header;
import com.squareup.okhttp.internal.spdy.IncomingStreamHandler;
import com.squareup.okhttp.internal.spdy.SpdyConnection;
import com.squareup.okhttp.internal.spdy.SpdyStream;
import com.squareup.okhttp.internal.ws.RealWebSocket;
import com.squareup.okhttp.internal.ws.WebSocketProtocol;
import com.squareup.okhttp.ws.WebSocketListener;
import java.io.IOException;
import java.net.InetAddress;
import java.net.InetSocketAddress;
import java.net.MalformedURLException;
import java.net.ProtocolException;
import java.net.Proxy;
import java.net.ServerSocket;
import java.net.Socket;
import java.net.SocketException;
import java.net.URL;
import java.security.SecureRandom;
import java.security.cert.CertificateException;
import java.security.cert.X509Certificate;
import java.util.ArrayList;
import java.util.Collections;
import java.util.Iterator;
import java.util.List;
import java.util.Locale;
import java.util.Set;
import java.util.concurrent.BlockingQueue;
import java.util.concurrent.ConcurrentHashMap;
import java.util.concurrent.CountDownLatch;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;
import java.util.concurrent.LinkedBlockingDeque;
import java.util.concurrent.LinkedBlockingQueue;
import java.util.concurrent.ThreadPoolExecutor;
import java.util.concurrent.TimeUnit;
import java.util.concurrent.atomic.AtomicInteger;
import java.util.logging.Level;
import java.util.logging.Logger;
import javax.net.ServerSocketFactory;
import javax.net.ssl.SSLContext;
import javax.net.ssl.SSLSocket;
import javax.net.ssl.SSLSocketFactory;
import javax.net.ssl.TrustManager;
import javax.net.ssl.X509TrustManager;
import okio.Buffer;
import okio.BufferedSink;
import okio.BufferedSource;
import okio.ByteString;
import okio.Okio;
import okio.Sink;
import okio.Timeout;

import static com.squareup.okhttp.mockwebserver.SocketPolicy.DISCONNECT_AT_START;
import static com.squareup.okhttp.mockwebserver.SocketPolicy.FAIL_HANDSHAKE;
import static java.util.concurrent.TimeUnit.SECONDS;

/**
 * A scriptable web server. Callers supply canned responses and the server
 * replays them upon request in sequence.
 */
public final class MockWebServer {
  private static final X509TrustManager UNTRUSTED_TRUST_MANAGER = new X509TrustManager() {
    @Override public void checkClientTrusted(X509Certificate[] chain, String authType)
        throws CertificateException {
      throw new CertificateException();
    }

    @Override public void checkServerTrusted(X509Certificate[] chain, String authType) {
      throw new AssertionError();
    }

    @Override public X509Certificate[] getAcceptedIssuers() {
      throw new AssertionError();
    }
  };

  private static final Logger logger = Logger.getLogger(MockWebServer.class.getName());

  private final BlockingQueue<RecordedRequest> requestQueue = new LinkedBlockingQueue<>();

  private final Set<Socket> openClientSockets =
      Collections.newSetFromMap(new ConcurrentHashMap<Socket, Boolean>());
  private final Set<SpdyConnection> openSpdyConnections =
      Collections.newSetFromMap(new ConcurrentHashMap<SpdyConnection, Boolean>());
  private final AtomicInteger requestCount = new AtomicInteger();
  private long bodyLimit = Long.MAX_VALUE;
  private ServerSocketFactory serverSocketFactory = ServerSocketFactory.getDefault();
  private ServerSocket serverSocket;
  private SSLSocketFactory sslSocketFactory;
  private ExecutorService executor;
  private boolean tunnelProxy;
  private Dispatcher dispatcher = new QueueDispatcher();

  private int port = -1;
  private InetSocketAddress inetSocketAddress;
  private boolean protocolNegotiationEnabled = true;
  private List<Protocol> protocols
      = Util.immutableList(Protocol.HTTP_2, Protocol.SPDY_3, Protocol.HTTP_1_1);

  public void setServerSocketFactory(ServerSocketFactory serverSocketFactory) {
    if (serverSocketFactory == null) throw new IllegalArgumentException("null serverSocketFactory");
    this.serverSocketFactory = serverSocketFactory;
  }

  public int getPort() {
    if (port == -1) throw new IllegalStateException("Call start() before getPort()");
    return port;
  }

  public String getHostName() {
    if (inetSocketAddress == null) {
      throw new IllegalStateException("Call start() before getHostName()");
    }
    return inetSocketAddress.getHostName();
  }

  public Proxy toProxyAddress() {
    if (inetSocketAddress == null) {
      throw new IllegalStateException("Call start() before toProxyAddress()");
    }
    InetSocketAddress address = new InetSocketAddress(inetSocketAddress.getAddress(), getPort());
    return new Proxy(Proxy.Type.HTTP, address);
  }

  /**
   * Returns a URL for connecting to this server.
   * @param path the request path, such as "/".
   */
  public URL getUrl(String path) {
    try {
      return sslSocketFactory != null
          ? new URL("https://" + getHostName() + ":" + getPort() + path)
          : new URL("http://" + getHostName() + ":" + getPort() + path);
    } catch (MalformedURLException e) {
      throw new AssertionError(e);
    }
  }

  /**
   * Returns a cookie domain for this server. This returns the server's
   * non-loopback host name if it is known. Otherwise this returns ".local" for
   * this server's loopback name.
   */
  public String getCookieDomain() {
    String hostName = getHostName();
    return hostName.contains(".") ? hostName : ".local";
  }

  /**
   * Sets the number of bytes of the POST body to keep in memory to the given
   * limit.
   */
  public void setBodyLimit(long maxBodyLength) {
    this.bodyLimit = maxBodyLength;
  }

  /**
   * Sets whether ALPN is used on incoming HTTPS connections to
   * negotiate a protocol like HTTP/1.1 or HTTP/2. Call this method to disable
   * negotiation and restrict connections to HTTP/1.1.
   */
  public void setProtocolNegotiationEnabled(boolean protocolNegotiationEnabled) {
    this.protocolNegotiationEnabled = protocolNegotiationEnabled;
  }

  /**
   * Indicates the protocols supported by ALPN on incoming HTTPS
   * connections. This list is ignored when
   * {@link #setProtocolNegotiationEnabled negotiation is disabled}.
   *
   * @param protocols the protocols to use, in order of preference. The list
   *     must contain {@linkplain Protocol#HTTP_1_1}. It must not contain null.
   */
  public void setProtocols(List<Protocol> protocols) {
    protocols = Util.immutableList(protocols);
    if (!protocols.contains(Protocol.HTTP_1_1)) {
      throw new IllegalArgumentException("protocols doesn't contain http/1.1: " + protocols);
    }
    if (protocols.contains(null)) {
      throw new IllegalArgumentException("protocols must not contain null");
    }
    this.protocols = protocols;
  }

  /**
   * Serve requests with HTTPS rather than otherwise.
   * @param tunnelProxy true to expect the HTTP CONNECT method before
   *     negotiating TLS.
   */
  public void useHttps(SSLSocketFactory sslSocketFactory, boolean tunnelProxy) {
    this.sslSocketFactory = sslSocketFactory;
    this.tunnelProxy = tunnelProxy;
  }

  /**
   * Awaits the next HTTP request, removes it, and returns it. Callers should
   * use this to verify the request was sent as intended. This method will block until the
   * request is available, possibly forever.
   *
   * @return the head of the request queue
   */
  public RecordedRequest takeRequest() throws InterruptedException {
    return requestQueue.take();
  }

  /**
   * Awaits the next HTTP request (waiting up to the
   * specified wait time if necessary), removes it, and returns it. Callers should
   * use this to verify the request was sent as intended within the given time.
   *
   * @param timeout how long to wait before giving up, in units of
  *        {@code unit}
   * @param unit a {@code TimeUnit} determining how to interpret the
   *        {@code timeout} parameter
   * @return the head of the request queue
   */
  public RecordedRequest takeRequest(long timeout, TimeUnit unit) throws InterruptedException {
    return requestQueue.poll(timeout, unit);
  }

  /**
   * Returns the number of HTTP requests received thus far by this server. This
   * may exceed the number of HTTP connections when connection reuse is in
   * practice.
   */
  public int getRequestCount() {
    return requestCount.get();
  }

  /**
   * Scripts {@code response} to be returned to a request made in sequence. The
   * first request is served by the first enqueued response; the second request
   * by the second enqueued response; and so on.
   *
   * @throws ClassCastException if the default dispatcher has been replaced
   *     with {@link #setDispatcher(Dispatcher)}.
   */
  public void enqueue(MockResponse response) {
    ((QueueDispatcher) dispatcher).enqueueResponse(response.clone());
  }

  /** @deprecated Use {@link #start()}. */
  public void play() throws IOException {
    start();
  }

  /** @deprecated Use {@link #start(int)}. */
  public void play(int port) throws IOException {
    start(port);
  }

  /** Equivalent to {@code start(0)}. */
  public void start() throws IOException {
    start(0);
  }

  /**
   * Starts the server on the loopback interface for the given port.
   *
   * @param port the port to listen to, or 0 for any available port. Automated
   *     tests should always use port 0 to avoid flakiness when a specific port
   *     is unavailable.
   */
  public void start(int port) throws IOException {
    start(InetAddress.getByName("localhost"), port);
  }

  /**
   * Starts the server on the given address and port.
   *
   * @param inetAddress the address to create the server socket on
   *
   * @param port the port to listen to, or 0 for any available port. Automated
   *     tests should always use port 0 to avoid flakiness when a specific port
   *     is unavailable.
   */
  public void start(InetAddress inetAddress, int port) throws IOException {
    start(new InetSocketAddress(inetAddress, port));
  }

  /**
   * Starts the server and binds to the given socket address.
   *
   * @param inetSocketAddress the socket address to bind the server on
   */
  private void start(InetSocketAddress inetSocketAddress) throws IOException {
    if (executor != null) throw new IllegalStateException("start() already called");
    executor = Executors.newCachedThreadPool(Util.threadFactory("MockWebServer", false));
    this.inetSocketAddress = inetSocketAddress;
    serverSocket = serverSocketFactory.createServerSocket();
    // Reuse if the user specified a port
    serverSocket.setReuseAddress(inetSocketAddress.getPort() != 0);
    serverSocket.bind(inetSocketAddress, 50);

    port = serverSocket.getLocalPort();
    executor.execute(new NamedRunnable("MockWebServer %s", port) {
      @Override protected void execute() {
        try {
          logger.info(MockWebServer.this + " starting to accept connections");
          acceptConnections();
        } catch (Throwable e) {
          logger.log(Level.WARNING, MockWebServer.this + " failed unexpectedly", e);
        }

        // Release all sockets and all threads, even if any close fails.
        Util.closeQuietly(serverSocket);
        for (Iterator<Socket> s = openClientSockets.iterator(); s.hasNext(); ) {
          Util.closeQuietly(s.next());
          s.remove();
        }
        for (Iterator<SpdyConnection> s = openSpdyConnections.iterator(); s.hasNext(); ) {
          Util.closeQuietly(s.next());
          s.remove();
        }
        executor.shutdown();
      }

      private void acceptConnections() throws Exception {
        while (true) {
          Socket socket;
          try {
            socket = serverSocket.accept();
          } catch (SocketException e) {
            logger.info(MockWebServer.this + " done accepting connections: " + e.getMessage());
            return;
          }
          SocketPolicy socketPolicy = dispatcher.peek().getSocketPolicy();
          if (socketPolicy == DISCONNECT_AT_START) {
            dispatchBookkeepingRequest(0, socket);
            socket.close();
          } else {
            openClientSockets.add(socket);
            serveConnection(socket);
          }
        }
      }
    });
  }

  public void shutdown() throws IOException {
    if (serverSocket == null) throw new IllegalStateException("shutdown() before start()");

    // Cause acceptConnections() to break out.
    serverSocket.close();

    // Await shutdown.
    try {
      if (!executor.awaitTermination(5, TimeUnit.SECONDS)) {
        throw new IOException("Gave up waiting for executor to shut down");
      }
    } catch (InterruptedException e) {
      throw new AssertionError();
    }
  }

  private void serveConnection(final Socket raw) {
    executor.execute(new NamedRunnable("MockWebServer %s", raw.getRemoteSocketAddress()) {
      int sequenceNumber = 0;

      @Override protected void execute() {
        try {
          processConnection();
        } catch (IOException e) {
          logger.info(
              MockWebServer.this + " connection from " + raw.getInetAddress() + " failed: " + e);
        } catch (Exception e) {
          logger.log(Level.SEVERE,
              MockWebServer.this + " connection from " + raw.getInetAddress() + " crashed", e);
        }
      }

      public void processConnection() throws Exception {
        Protocol protocol = Protocol.HTTP_1_1;
        Socket socket;
        if (sslSocketFactory != null) {
          if (tunnelProxy) {
            createTunnel();
          }
          SocketPolicy socketPolicy = dispatcher.peek().getSocketPolicy();
          if (socketPolicy == FAIL_HANDSHAKE) {
            dispatchBookkeepingRequest(sequenceNumber, raw);
            processHandshakeFailure(raw);
            return;
          }
          socket = sslSocketFactory.createSocket(raw, raw.getInetAddress().getHostAddress(),
              raw.getPort(), true);
          SSLSocket sslSocket = (SSLSocket) socket;
          sslSocket.setUseClientMode(false);
          openClientSockets.add(socket);

          if (protocolNegotiationEnabled) {
            Platform.get().configureTlsExtensions(sslSocket, null, protocols);
          }

          sslSocket.startHandshake();

          if (protocolNegotiationEnabled) {
            String protocolString = Platform.get().getSelectedProtocol(sslSocket);
            protocol = protocolString != null ? Protocol.get(protocolString) : Protocol.HTTP_1_1;
          }
          openClientSockets.remove(raw);
        } else {
          socket = raw;
        }

        if (protocol != Protocol.HTTP_1_1) {
          SpdySocketHandler spdySocketHandler = new SpdySocketHandler(socket, protocol);
          SpdyConnection spdyConnection =
              new SpdyConnection.Builder(false, socket).protocol(protocol)
                  .handler(spdySocketHandler)
                  .build();
          openSpdyConnections.add(spdyConnection);
          openClientSockets.remove(socket);
          return;
        }

        BufferedSource source = Okio.buffer(Okio.source(socket));
        BufferedSink sink = Okio.buffer(Okio.sink(socket));

        while (processOneRequest(socket, source, sink)) {
        }

        if (sequenceNumber == 0) {
          logger.warning(MockWebServer.this
              + " connection from "
              + raw.getInetAddress()
              + " didn't make a request");
        }

        source.close();
        sink.close();
        socket.close();
        openClientSockets.remove(socket);
      }

      /**
       * Respond to CONNECT requests until a SWITCH_TO_SSL_AT_END response is
       * dispatched.
       */
      private void createTunnel() throws IOException, InterruptedException {
        BufferedSource source = Okio.buffer(Okio.source(raw));
        BufferedSink sink = Okio.buffer(Okio.sink(raw));
        while (true) {
          SocketPolicy socketPolicy = dispatcher.peek().getSocketPolicy();
          if (!processOneRequest(raw, source, sink)) {
            throw new IllegalStateException("Tunnel without any CONNECT!");
          }
          if (socketPolicy == SocketPolicy.UPGRADE_TO_SSL_AT_END) return;
        }
      }

      /**
       * Reads a request and writes its response. Returns true if further calls should be attempted
       * on the socket.
       */
      private boolean processOneRequest(Socket socket, BufferedSource source, BufferedSink sink)
          throws IOException, InterruptedException {
        RecordedRequest request = readRequest(socket, source, sink, sequenceNumber);
        if (request == null) return false;

        requestCount.incrementAndGet();
        requestQueue.add(request);

        MockResponse response = dispatcher.dispatch(request);
        if (response.getSocketPolicy() == SocketPolicy.DISCONNECT_AFTER_REQUEST) {
          socket.close();
          return false;
        }
        if (response.getSocketPolicy() == SocketPolicy.NO_RESPONSE) {
          // This read should block until the socket is closed. (Because nobody is writing.)
          if (source.exhausted()) return false;
          throw new ProtocolException("unexpected data");
        }

        boolean reuseSocket = true;
        boolean requestWantsWebSockets = "Upgrade".equalsIgnoreCase(request.getHeader("Connection"))
            && "websocket".equalsIgnoreCase(request.getHeader("Upgrade"));
        boolean responseWantsWebSockets = response.getWebSocketListener() != null;
        if (requestWantsWebSockets && responseWantsWebSockets) {
          handleWebSocketUpgrade(socket, source, sink, request, response);
          reuseSocket = false;
        } else {
          writeHttpResponse(socket, sink, response);
        }

        if (logger.isLoggable(Level.INFO)) {
          logger.info(MockWebServer.this + " received request: " + request
              + " and responded: " + response);
        }

        if (response.getSocketPolicy() == SocketPolicy.DISCONNECT_AT_END) {
          socket.close();
          return false;
        } else if (response.getSocketPolicy() == SocketPolicy.SHUTDOWN_INPUT_AT_END) {
          socket.shutdownInput();
        } else if (response.getSocketPolicy() == SocketPolicy.SHUTDOWN_OUTPUT_AT_END) {
          socket.shutdownOutput();
        }

        sequenceNumber++;
        return reuseSocket;
      }
    });
  }

  private void processHandshakeFailure(Socket raw) throws Exception {
    SSLContext context = SSLContext.getInstance("TLS");
    context.init(null, new TrustManager[] { UNTRUSTED_TRUST_MANAGER }, new SecureRandom());
    SSLSocketFactory sslSocketFactory = context.getSocketFactory();
    SSLSocket socket = (SSLSocket) sslSocketFactory.createSocket(
        raw, raw.getInetAddress().getHostAddress(), raw.getPort(), true);
    try {
      socket.startHandshake(); // we're testing a handshake failure
      throw new AssertionError();
    } catch (IOException expected) {
    }
    socket.close();
  }

  private void dispatchBookkeepingRequest(int sequenceNumber, Socket socket)
      throws InterruptedException {
    requestCount.incrementAndGet();
    dispatcher.dispatch(new RecordedRequest(null, null, null, -1, null, sequenceNumber, socket));
  }

  /** @param sequenceNumber the index of this request on this connection. */
  private RecordedRequest readRequest(Socket socket, BufferedSource source, BufferedSink sink,
      int sequenceNumber) throws IOException {
    String request;
    try {
      request = source.readUtf8LineStrict();
    } catch (IOException streamIsClosed) {
      return null; // no request because we closed the stream
    }
    if (request.length() == 0) {
      return null; // no request because the stream is exhausted
    }

    Headers.Builder headers = new Headers.Builder();
    long contentLength = -1;
    boolean chunked = false;
    boolean expectContinue = false;
    String header;
    while ((header = source.readUtf8LineStrict()).length() != 0) {
      headers.add(header);
      String lowercaseHeader = header.toLowerCase(Locale.US);
      if (contentLength == -1 && lowercaseHeader.startsWith("content-length:")) {
        contentLength = Long.parseLong(header.substring(15).trim());
      }
      if (lowercaseHeader.startsWith("transfer-encoding:")
          && lowercaseHeader.substring(18).trim().equals("chunked")) {
        chunked = true;
      }
      if (lowercaseHeader.startsWith("expect:")
          && lowercaseHeader.substring(7).trim().equals("100-continue")) {
        expectContinue = true;
      }
    }

    if (expectContinue) {
      sink.writeUtf8("HTTP/1.1 100 Continue\r\n");
      sink.writeUtf8("Content-Length: 0\r\n");
      sink.writeUtf8("\r\n");
      sink.flush();
    }

    boolean hasBody = false;
    TruncatingBuffer requestBody = new TruncatingBuffer(bodyLimit);
    List<Integer> chunkSizes = new ArrayList<>();
    MockResponse throttlePolicy = dispatcher.peek();
    if (contentLength != -1) {
      hasBody = contentLength > 0;
      throttledTransfer(throttlePolicy, socket, source, Okio.buffer(requestBody), contentLength);
    } else if (chunked) {
      hasBody = true;
      while (true) {
        int chunkSize = Integer.parseInt(source.readUtf8LineStrict().trim(), 16);
        if (chunkSize == 0) {
          readEmptyLine(source);
          break;
        }
        chunkSizes.add(chunkSize);
        throttledTransfer(throttlePolicy, socket, source, Okio.buffer(requestBody), chunkSize);
        readEmptyLine(source);
      }
    }

    if (request.startsWith("OPTIONS ")
        || request.startsWith("GET ")
        || request.startsWith("HEAD ")
        || request.startsWith("TRACE ")
        || request.startsWith("CONNECT ")) {
      if (hasBody) {
        throw new IllegalArgumentException("Request must not have a body: " + request);
      }
    } else if (!request.startsWith("POST ")
        && !request.startsWith("PUT ")
        && !request.startsWith("PATCH ")
        && !request.startsWith("DELETE ")) { // Permitted as spec is ambiguous.
      throw new UnsupportedOperationException("Unexpected method: " + request);
    }

    return new RecordedRequest(request, headers.build(), chunkSizes, requestBody.receivedByteCount,
        requestBody.buffer, sequenceNumber, socket);
  }

  private void handleWebSocketUpgrade(Socket socket, BufferedSource source, BufferedSink sink,
      RecordedRequest request, MockResponse response) throws IOException {
    String key = request.getHeader("Sec-WebSocket-Key");
    String acceptKey = Util.shaBase64(key + WebSocketProtocol.ACCEPT_MAGIC);
    response.setHeader("Sec-WebSocket-Accept", acceptKey);

    writeHttpResponse(socket, sink, response);

    final WebSocketListener listener = response.getWebSocketListener();
    final CountDownLatch connectionClose = new CountDownLatch(1);

    ThreadPoolExecutor replyExecutor =
        new ThreadPoolExecutor(1, 1, 1, SECONDS, new LinkedBlockingDeque<Runnable>(),
            Util.threadFactory(String.format("MockWebServer %s WebSocket", request.getPath()),
                true));
    replyExecutor.allowCoreThreadTimeOut(true);
    final RealWebSocket webSocket =
        new RealWebSocket(false /* is server */, source, sink, new SecureRandom(), replyExecutor,
            listener, request.getPath()) {
          @Override protected void closeConnection() throws IOException {
            connectionClose.countDown();
          }
        };

    // Adapt the request and response into our Request and Response domain model.
    String scheme = request.getTlsVersion() != null ? "https" : "http";
    String authority = request.getHeader("Host"); // Has host and port.
    final Request fancyRequest = new Request.Builder()
        .url(scheme + "://" + authority + "/")
        .headers(request.getHeaders())
        .build();
    final Response fancyResponse = new Response.Builder()
        .code(Integer.parseInt(response.getStatus().split(" ")[1]))
        .message(response.getStatus().split(" ", 3)[2])
        .headers(response.getHeaders())
        .request(fancyRequest)
        .protocol(Protocol.HTTP_1_1)
        .build();

    listener.onOpen(webSocket, fancyResponse);

    while (webSocket.readMessage()) {
    }

    // Even if messages are no longer being read we need to wait for the connection close signal.
    try {
      connectionClose.await();
    } catch (InterruptedException e) {
      throw new RuntimeException(e);
    }

    Util.closeQuietly(sink);
    Util.closeQuietly(source);
  }

  private void writeHttpResponse(Socket socket, BufferedSink sink, MockResponse response)
      throws IOException {
    sink.writeUtf8(response.getStatus());
    sink.writeUtf8("\r\n");

    Headers headers = response.getHeaders();
    for (int i = 0, size = headers.size(); i < size; i++) {
      sink.writeUtf8(headers.name(i));
      sink.writeUtf8(": ");
      sink.writeUtf8(headers.value(i));
      sink.writeUtf8("\r\n");
    }
    sink.writeUtf8("\r\n");
    sink.flush();

    Buffer body = response.getBody();
    if (body == null) return;
    sleepIfDelayed(response);
    throttledTransfer(response, socket, body, sink, Long.MAX_VALUE);
  }

  private void sleepIfDelayed(MockResponse response) {
    long delayMs = response.getBodyDelay(TimeUnit.MILLISECONDS);
    if (delayMs != 0) {
      try {
        Thread.sleep(delayMs);
      } catch (InterruptedException e) {
        throw new AssertionError(e);
      }
    }
  }

  /**
   * Transfer bytes from {@code source} to {@code sink} until either {@code byteCount}
   * bytes have been transferred or {@code source} is exhausted. The transfer is
   * throttled according to {@code throttlePolicy}.
   */
  private void throttledTransfer(MockResponse throttlePolicy, Socket socket, BufferedSource source,
      BufferedSink sink, long byteCount) throws IOException {
    if (byteCount == 0) return;

    Buffer buffer = new Buffer();
    long bytesPerPeriod = throttlePolicy.getThrottleBytesPerPeriod();
    long periodDelayMs = throttlePolicy.getThrottlePeriod(TimeUnit.MILLISECONDS);

    while (!socket.isClosed()) {
      for (int b = 0; b < bytesPerPeriod; ) {
        long toRead = Math.min(Math.min(2048, byteCount), bytesPerPeriod - b);
        long read = source.read(buffer, toRead);
        if (read == -1) return;

        sink.write(buffer, read);
        sink.flush();
        b += read;
        byteCount -= read;

        if (byteCount == 0) return;
      }

      if (periodDelayMs != 0) {
        try {
          Thread.sleep(periodDelayMs);
        } catch (InterruptedException e) {
          throw new AssertionError();
        }
      }
    }
  }

  private void readEmptyLine(BufferedSource source) throws IOException {
    String line = source.readUtf8LineStrict();
    if (line.length() != 0) throw new IllegalStateException("Expected empty but was: " + line);
  }

  /**
   * Sets the dispatcher used to match incoming requests to mock responses.
   * The default dispatcher simply serves a fixed sequence of responses from
   * a {@link #enqueue(MockResponse) queue}; custom dispatchers can vary the
   * response based on timing or the content of the request.
   */
  public void setDispatcher(Dispatcher dispatcher) {
    if (dispatcher == null) throw new NullPointerException();
    this.dispatcher = dispatcher;
  }

  @Override public String toString() {
    return "MockWebServer[" + port + "]";
  }

  /** A buffer wrapper that drops data after {@code bodyLimit} bytes. */
  private static class TruncatingBuffer implements Sink {
    private final Buffer buffer = new Buffer();
    private long remainingByteCount;
    private long receivedByteCount;

    TruncatingBuffer(long bodyLimit) {
      remainingByteCount = bodyLimit;
    }

    @Override public void write(Buffer source, long byteCount) throws IOException {
      long toRead = Math.min(remainingByteCount, byteCount);
      if (toRead > 0) {
        source.read(buffer, toRead);
      }
      long toSkip = byteCount - toRead;
      if (toSkip > 0) {
        source.skip(toSkip);
      }
      remainingByteCount -= toRead;
      receivedByteCount += byteCount;
    }

    @Override public void flush() throws IOException {
    }

    @Override public Timeout timeout() {
      return Timeout.NONE;
    }

    @Override public void close() throws IOException {
    }
  }

  /** Processes HTTP requests layered over SPDY/3. */
  private class SpdySocketHandler implements IncomingStreamHandler {
    private final Socket socket;
    private final Protocol protocol;
    private final AtomicInteger sequenceNumber = new AtomicInteger();

    private SpdySocketHandler(Socket socket, Protocol protocol) {
      this.socket = socket;
      this.protocol = protocol;
    }

    @Override public void receive(SpdyStream stream) throws IOException {
      RecordedRequest request = readRequest(stream);
      requestQueue.add(request);
      MockResponse response;
      try {
        response = dispatcher.dispatch(request);
      } catch (InterruptedException e) {
        throw new AssertionError(e);
      }
      writeResponse(stream, response);
      if (logger.isLoggable(Level.INFO)) {
        logger.info(MockWebServer.this + " received request: " + request
            + " and responded: " + response + " protocol is " + protocol.toString());
      }
    }

    private RecordedRequest readRequest(SpdyStream stream) throws IOException {
      List<Header> spdyHeaders = stream.getRequestHeaders();
      Headers.Builder httpHeaders = new Headers.Builder();
      String method = "<:method omitted>";
      String path = "<:path omitted>";
      String version = protocol == Protocol.SPDY_3 ? "<:version omitted>" : "HTTP/1.1";
      for (int i = 0, size = spdyHeaders.size(); i < size; i++) {
        ByteString name = spdyHeaders.get(i).name;
        String value = spdyHeaders.get(i).value.utf8();
        if (name.equals(Header.TARGET_METHOD)) {
          method = value;
        } else if (name.equals(Header.TARGET_PATH)) {
          path = value;
        } else if (name.equals(Header.VERSION)) {
          version = value;
        } else {
          httpHeaders.add(name.utf8(), value);
        }
      }

      Buffer body = new Buffer();
      body.writeAll(stream.getSource());
      body.close();

      String requestLine = method + ' ' + path + ' ' + version;
      List<Integer> chunkSizes = Collections.emptyList(); // No chunked encoding for SPDY.
      return new RecordedRequest(requestLine, httpHeaders.build(), chunkSizes, body.size(), body,
          sequenceNumber.getAndIncrement(), socket);
    }

    private void writeResponse(SpdyStream stream, MockResponse response) throws IOException {
      if (response.getSocketPolicy() == SocketPolicy.NO_RESPONSE) {
        return;
      }
      List<Header> spdyHeaders = new ArrayList<>();
      String[] statusParts = response.getStatus().split(" ", 2);
      if (statusParts.length != 2) {
        throw new AssertionError("Unexpected status: " + response.getStatus());
      }
      // TODO: constants for well-known header names.
      spdyHeaders.add(new Header(Header.RESPONSE_STATUS, statusParts[1]));
      if (protocol == Protocol.SPDY_3) {
        spdyHeaders.add(new Header(Header.VERSION, statusParts[0]));
      }
      Headers headers = response.getHeaders();
      for (int i = 0, size = headers.size(); i < size; i++) {
        spdyHeaders.add(new Header(headers.name(i), headers.value(i)));
      }

      Buffer body = response.getBody();
      boolean closeStreamAfterHeaders = body != null || !response.getPushPromises().isEmpty();
      stream.reply(spdyHeaders, closeStreamAfterHeaders);
      pushPromises(stream, response.getPushPromises());
      if (body != null) {
        BufferedSink sink = Okio.buffer(stream.getSink());
        sleepIfDelayed(response);
        throttledTransfer(response, socket, body, sink, bodyLimit);
        sink.close();
      } else if (closeStreamAfterHeaders) {
        stream.close(ErrorCode.NO_ERROR);
      }
    }

    private void pushPromises(SpdyStream stream, List<PushPromise> promises) throws IOException {
      for (PushPromise pushPromise : promises) {
        List<Header> pushedHeaders = new ArrayList<>();
        pushedHeaders.add(new Header(stream.getConnection().getProtocol() == Protocol.SPDY_3
            ? Header.TARGET_HOST
            : Header.TARGET_AUTHORITY, getUrl(pushPromise.getPath()).getHost()));
        pushedHeaders.add(new Header(Header.TARGET_METHOD, pushPromise.getMethod()));
        pushedHeaders.add(new Header(Header.TARGET_PATH, pushPromise.getPath()));
        Headers pushPromiseHeaders = pushPromise.getHeaders();
        for (int i = 0, size = pushPromiseHeaders.size(); i < size; i++) {
          pushedHeaders.add(new Header(pushPromiseHeaders.name(i), pushPromiseHeaders.value(i)));
        }
        String requestLine = pushPromise.getMethod() + ' ' + pushPromise.getPath() + " HTTP/1.1";
        List<Integer> chunkSizes = Collections.emptyList(); // No chunked encoding for SPDY.
        requestQueue.add(new RecordedRequest(requestLine, pushPromise.getHeaders(), chunkSizes, 0,
            new Buffer(), sequenceNumber.getAndIncrement(), socket));
        boolean hasBody = pushPromise.getResponse().getBody() != null;
        SpdyStream pushedStream =
            stream.getConnection().pushStream(stream.getId(), pushedHeaders, hasBody);
        writeResponse(pushedStream, pushPromise.getResponse());
      }
    }
  }
}


File: okcurl/src/main/java/com/squareup/okhttp/curl/Main.java
/*
 * Copyright (C) 2014 Square, Inc.
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
package com.squareup.okhttp.curl;

import com.google.common.base.Joiner;
import com.squareup.okhttp.ConnectionPool;
import com.squareup.okhttp.Headers;
import com.squareup.okhttp.MediaType;
import com.squareup.okhttp.OkHttpClient;
import com.squareup.okhttp.Protocol;
import com.squareup.okhttp.Request;
import com.squareup.okhttp.RequestBody;
import com.squareup.okhttp.Response;
import com.squareup.okhttp.internal.http.StatusLine;
import com.squareup.okhttp.internal.spdy.Http2;

import io.airlift.command.Arguments;
import io.airlift.command.Command;
import io.airlift.command.HelpOption;
import io.airlift.command.Option;
import io.airlift.command.SingleCommand;
import java.io.IOException;
import java.io.InputStream;
import java.security.cert.CertificateException;
import java.security.cert.X509Certificate;
import java.util.List;
import java.util.Properties;
import java.util.logging.ConsoleHandler;
import java.util.logging.Level;
import java.util.logging.LogRecord;
import java.util.logging.Logger;
import java.util.logging.SimpleFormatter;
import javax.net.ssl.HostnameVerifier;
import javax.net.ssl.SSLContext;
import javax.net.ssl.SSLSession;
import javax.net.ssl.SSLSocketFactory;
import javax.net.ssl.TrustManager;
import javax.net.ssl.X509TrustManager;
import okio.BufferedSource;
import okio.Okio;
import okio.Sink;

import static java.util.concurrent.TimeUnit.SECONDS;

@Command(name = Main.NAME, description = "A curl for the next-generation web.")
public class Main extends HelpOption implements Runnable {
  static final String NAME = "okcurl";
  static final int DEFAULT_TIMEOUT = -1;

  static Main fromArgs(String... args) {
    return SingleCommand.singleCommand(Main.class).parse(args);
  }

  public static void main(String... args) {
    fromArgs(args).run();
  }

  private static String versionString() {
    try {
      Properties prop = new Properties();
      InputStream in = Main.class.getResourceAsStream("/okcurl-version.properties");
      prop.load(in);
      in.close();
      return prop.getProperty("version");
    } catch (IOException e) {
      throw new AssertionError("Could not load okcurl-version.properties.");
    }
  }

  private static String protocols() {
    return Joiner.on(", ").join(Protocol.values());
  }

  @Option(name = { "-X", "--request" }, description = "Specify request command to use")
  public String method;

  @Option(name = { "-d", "--data" }, description = "HTTP POST data")
  public String data;

  @Option(name = { "-H", "--header" }, description = "Custom header to pass to server")
  public List<String> headers;

  @Option(name = { "-A", "--user-agent" }, description = "User-Agent to send to server")
  public String userAgent = NAME + "/" + versionString();

  @Option(name = "--connect-timeout", description = "Maximum time allowed for connection (seconds)")
  public int connectTimeout = DEFAULT_TIMEOUT;

  @Option(name = "--read-timeout", description = "Maximum time allowed for reading data (seconds)")
  public int readTimeout = DEFAULT_TIMEOUT;

  @Option(name = { "-L", "--location" }, description = "Follow redirects")
  public boolean followRedirects;

  @Option(name = { "-k", "--insecure" },
      description = "Allow connections to SSL sites without certs")
  public boolean allowInsecure;

  @Option(name = { "-i", "--include" }, description = "Include protocol headers in the output")
  public boolean showHeaders;

  @Option(name = "--frames", description = "Log HTTP/2 frames to STDERR")
  public boolean showHttp2Frames;

  @Option(name = { "-e", "--referer" }, description = "Referer URL")
  public String referer;

  @Option(name = { "-V", "--version" }, description = "Show version number and quit")
  public boolean version;

  @Arguments(title = "url", description = "Remote resource URL")
  public String url;

  private OkHttpClient client;

  @Override public void run() {
    if (showHelpIfRequested()) {
      return;
    }
    if (version) {
      System.out.println(NAME + " " + versionString());
      System.out.println("Protocols: " + protocols());
      return;
    }

    if (showHttp2Frames) {
      enableHttp2FrameLogging();
    }

    client = createClient();
    Request request = createRequest();
    try {
      Response response = client.newCall(request).execute();
      if (showHeaders) {
        System.out.println(StatusLine.get(response));
        Headers headers = response.headers();
        for (int i = 0, size = headers.size(); i < size; i++) {
          System.out.println(headers.name(i) + ": " + headers.value(i));
        }
        System.out.println();
      }

      // Stream the response to the System.out as it is returned from the server.
      Sink out = Okio.sink(System.out);
      BufferedSource source = response.body().source();
      while (!source.exhausted()) {
        out.write(source.buffer(), source.buffer().size());
        out.flush();
      }

      response.body().close();
    } catch (IOException e) {
      e.printStackTrace();
    } finally {
      close();
    }
  }

  private OkHttpClient createClient() {
    OkHttpClient client = new OkHttpClient();
    client.setFollowSslRedirects(followRedirects);
    if (connectTimeout != DEFAULT_TIMEOUT) {
      client.setConnectTimeout(connectTimeout, SECONDS);
    }
    if (readTimeout != DEFAULT_TIMEOUT) {
      client.setReadTimeout(readTimeout, SECONDS);
    }
    if (allowInsecure) {
      client.setSslSocketFactory(createInsecureSslSocketFactory());
      client.setHostnameVerifier(createInsecureHostnameVerifier());
    }
    // If we don't set this reference, there's no way to clean shutdown persistent connections.
    client.setConnectionPool(ConnectionPool.getDefault());
    return client;
  }

  private String getRequestMethod() {
    if (method != null) {
      return method;
    }
    if (data != null) {
      return "POST";
    }
    return "GET";
  }

  private RequestBody getRequestBody() {
    if (data == null) {
      return null;
    }
    String bodyData = data;

    String mimeType = "application/x-form-urlencoded";
    if (headers != null) {
      for (String header : headers) {
        String[] parts = header.split(":", -1);
        if ("Content-Type".equalsIgnoreCase(parts[0])) {
          mimeType = parts[1].trim();
          headers.remove(header);
          break;
        }
      }
    }

    return RequestBody.create(MediaType.parse(mimeType), bodyData);
  }

  Request createRequest() {
    Request.Builder request = new Request.Builder();

    request.url(url);
    request.method(getRequestMethod(), getRequestBody());

    if (headers != null) {
      for (String header : headers) {
        String[] parts = header.split(":", 2);
        request.header(parts[0], parts[1]);
      }
    }
    if (referer != null) {
      request.header("Referer", referer);
    }
    request.header("User-Agent", userAgent);

    return request.build();
  }

  private void close() {
    client.getConnectionPool().evictAll(); // Close any persistent connections.
  }

  private static SSLSocketFactory createInsecureSslSocketFactory() {
    try {
      SSLContext context = SSLContext.getInstance("TLS");
      TrustManager permissive = new X509TrustManager() {
        @Override public void checkClientTrusted(X509Certificate[] chain, String authType)
            throws CertificateException {
        }

        @Override public void checkServerTrusted(X509Certificate[] chain, String authType)
            throws CertificateException {
        }

        @Override public X509Certificate[] getAcceptedIssuers() {
          return null;
        }
      };
      context.init(null, new TrustManager[] { permissive }, null);
      return context.getSocketFactory();
    } catch (Exception e) {
      throw new AssertionError(e);
    }
  }

  private static HostnameVerifier createInsecureHostnameVerifier() {
    return new HostnameVerifier() {
      @Override public boolean verify(String s, SSLSession sslSession) {
        return true;
      }
    };
  }

  private static void enableHttp2FrameLogging() {
    Logger logger = Logger.getLogger(Http2.class.getName() + "$FrameLogger");
    logger.setLevel(Level.FINE);
    ConsoleHandler handler = new ConsoleHandler();
    handler.setLevel(Level.FINE);
    handler.setFormatter(new SimpleFormatter() {
      @Override public String format(LogRecord record) {
        return String.format("%s%n", record.getMessage());
      }
    });
    logger.addHandler(handler);
  }
}


File: okhttp-hpacktests/src/test/java/com/squareup/okhttp/internal/spdy/HpackDecodeInteropTest.java
/*
 * Copyright (C) 2014 Square, Inc.
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
package com.squareup.okhttp.internal.spdy;

import com.squareup.okhttp.internal.spdy.hpackjson.Story;
import java.util.Collection;
import org.junit.Test;
import org.junit.runner.RunWith;
import org.junit.runners.Parameterized;

import static com.squareup.okhttp.internal.spdy.hpackjson.HpackJsonUtil.storiesForCurrentDraft;

@RunWith(Parameterized.class)
public class HpackDecodeInteropTest extends HpackDecodeTestBase {

  public HpackDecodeInteropTest(Story story) {
    super(story);
  }

  @Parameterized.Parameters(name="{0}")
  public static Collection<Story[]> createStories() throws Exception {
    return createStories(storiesForCurrentDraft());
  }

  @Test
  public void testGoodDecoderInterop() throws Exception {
    testDecoder();
  }
}


File: okhttp-hpacktests/src/test/java/com/squareup/okhttp/internal/spdy/HpackDecodeTestBase.java
/*
 * Copyright (C) 2014 Square, Inc.
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
package com.squareup.okhttp.internal.spdy;

import com.squareup.okhttp.internal.spdy.hpackjson.Case;
import com.squareup.okhttp.internal.spdy.hpackjson.HpackJsonUtil;
import com.squareup.okhttp.internal.spdy.hpackjson.Story;
import java.util.ArrayList;
import java.util.Collection;
import java.util.LinkedHashSet;
import java.util.List;
import okio.Buffer;

import static org.junit.Assert.assertEquals;
import static org.junit.Assert.fail;

/**
 * Tests Hpack implementation using https://github.com/http2jp/hpack-test-case/
 */
public class HpackDecodeTestBase {

  /**
   * Reads all stories in the folders provided, asserts if no story found.
   */
  protected static Collection<Story[]> createStories(String[] interopTests)
      throws Exception {
    List<Story[]> result = new ArrayList<>();
    for (String interopTestName : interopTests) {
      List<Story> stories = HpackJsonUtil.readStories(interopTestName);
      if (stories.isEmpty()) {
        fail("No stories for: " + interopTestName);
      }
      for (Story story : stories) {
        result.add(new Story[] { story });
      }
    }
    return result;
  }

  private final Buffer bytesIn = new Buffer();
  private final Hpack.Reader hpackReader = new Hpack.Reader(4096, bytesIn);

  private final Story story;

  public HpackDecodeTestBase(Story story) {
    this.story = story;
  }

  /**
   * Expects wire to be set for all cases, and compares the decoder's output to
   * expected headers.
   */
  protected void testDecoder() throws Exception {
    testDecoder(story);
  }

  protected void testDecoder(Story story) throws Exception {
    for (Case caze : story.getCases()) {
      bytesIn.write(caze.getWire());
      hpackReader.readHeaders();
      assertSetEquals(String.format("seqno=%d", caze.getSeqno()), caze.getHeaders(),
          hpackReader.getAndResetHeaderList());
    }
  }
  /**
   * Checks if {@code expected} and {@code observed} are equal when viewed as a
   * set and headers are deduped.
   *
   * TODO: See if duped headers should be preserved on decode and verify.
   */
  private static void assertSetEquals(
      String message, List<Header> expected, List<Header> observed) {
    assertEquals(message, new LinkedHashSet<>(expected), new LinkedHashSet<>(observed));
  }

  protected Story getStory() {
    return story;
  }
}


File: okhttp-hpacktests/src/test/java/com/squareup/okhttp/internal/spdy/HpackRoundTripTest.java
/*
 * Copyright (C) 2014 Square, Inc.
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
package com.squareup.okhttp.internal.spdy;

import com.squareup.okhttp.internal.spdy.hpackjson.Case;
import com.squareup.okhttp.internal.spdy.hpackjson.Story;
import okio.Buffer;
import org.junit.Test;
import org.junit.runner.RunWith;
import org.junit.runners.Parameterized;

import java.util.Collection;

/**
 * Tests for round-tripping headers through hpack..
 */
// TODO: update hpack-test-case with the output of our encoder.
// This test will hide complementary bugs in the encoder and decoder,
// We should test that the encoder is producing responses that are
// d]
@RunWith(Parameterized.class)
public class HpackRoundTripTest extends HpackDecodeTestBase {

  private static final String[] RAW_DATA = { "raw-data" };

  @Parameterized.Parameters(name="{0}")
  public static Collection<Story[]> getStories() throws Exception {
    return createStories(RAW_DATA);
  }

  private Buffer bytesOut = new Buffer();
  private Hpack.Writer hpackWriter = new Hpack.Writer(bytesOut);

  public HpackRoundTripTest(Story story) {
    super(story);
  }

  @Test
  public void testRoundTrip() throws Exception {
    Story story = getStory().clone();
    // Mutate cases in base class.
    for (Case caze : story.getCases()) {
      hpackWriter.writeHeaders(caze.getHeaders());
      caze.setWire(bytesOut.readByteString());
    }

    testDecoder(story);
  }

}


File: okhttp-hpacktests/src/test/java/com/squareup/okhttp/internal/spdy/hpackjson/Case.java
/*
 * Copyright (C) 2014 Square, Inc.
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
package com.squareup.okhttp.internal.spdy.hpackjson;

import com.squareup.okhttp.internal.spdy.Header;
import okio.ByteString;

import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;

/**
 * Representation of an individual case (set of headers and wire format).
 * There are many cases for a single story.  This class is used reflectively
 * with Gson to parse stories.
 */
public class Case implements Cloneable {

  private int seqno;
  private String wire;
  private List<Map<String, String>> headers;

  public List<Header> getHeaders() {
    List<Header> result = new ArrayList<>();
    for (Map<String, String> inputHeader : headers) {
      Map.Entry<String, String> entry = inputHeader.entrySet().iterator().next();
      result.add(new Header(entry.getKey(), entry.getValue()));
    }
    return result;
  }

  public ByteString getWire() {
    return ByteString.decodeHex(wire);
  }

  public int getSeqno() {
    return seqno;
  }

  public void setWire(ByteString wire) {
    this.wire = wire.hex();
  }

  @Override
  protected Case clone() throws CloneNotSupportedException {
    Case result = new Case();
    result.seqno = seqno;
    result.wire = wire;
    result.headers = new ArrayList<>();
    for (Map<String, String> header : headers) {
      result.headers.add(new LinkedHashMap<String, String>(header));
    }
    return result;
  }
}


File: okhttp-hpacktests/src/test/java/com/squareup/okhttp/internal/spdy/hpackjson/HpackJsonUtil.java
/*
 * Copyright (C) 2014 Square, Inc.
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
package com.squareup.okhttp.internal.spdy.hpackjson;

import com.google.gson.Gson;
import com.google.gson.GsonBuilder;
import java.io.File;
import java.io.FileInputStream;
import java.io.IOException;
import java.io.InputStream;
import java.io.InputStreamReader;
import java.net.URISyntaxException;
import java.util.ArrayList;
import java.util.Arrays;
import java.util.List;

/**
 * Utilities for reading HPACK tests.
 */
public final class HpackJsonUtil {
  /** Earliest draft that is code-compatible with latest. */
  private static final int BASE_DRAFT = 9;

  private static final String STORY_RESOURCE_FORMAT = "/hpack-test-case/%s/story_%02d.json";

  private static final Gson GSON = new GsonBuilder().create();

  private static Story readStory(InputStream jsonResource) throws IOException {
    return GSON.fromJson(new InputStreamReader(jsonResource, "UTF-8"), Story.class);
  }

  /** Iterate through the hpack-test-case resources, only picking stories for the current draft. */
  public static String[] storiesForCurrentDraft() throws URISyntaxException {
    File testCaseDirectory = new File(HpackJsonUtil.class.getResource("/hpack-test-case").toURI());
    List<String> storyNames = new ArrayList<String>();
    for (File path : testCaseDirectory.listFiles()) {
      if (path.isDirectory() && Arrays.asList(path.list()).contains("story_00.json")) {
        try {
          Story firstStory = readStory(new FileInputStream(new File(path, "story_00.json")));
          if (firstStory.getDraft() >= BASE_DRAFT) {
            storyNames.add(path.getName());
          }
        } catch (IOException ignored) {
          // Skip this path.
        }
      }
    }
    return storyNames.toArray(new String[storyNames.size()]);
  }

  /**
   * Reads stories named "story_xx.json" from the folder provided.
   */
  public static List<Story> readStories(String testFolderName) throws Exception {
    List<Story> result = new ArrayList<>();
    int i = 0;
    while (true) { // break after last test.
      String storyResourceName = String.format(STORY_RESOURCE_FORMAT, testFolderName, i);
      InputStream storyInputStream = HpackJsonUtil.class.getResourceAsStream(storyResourceName);
      if (storyInputStream == null) {
        break;
      }
      try {
        Story story = readStory(storyInputStream);
        story.setFileName(storyResourceName);
        result.add(story);
        i++;
      } finally {
        storyInputStream.close();
      }
    }
    return result;
  }

  private HpackJsonUtil() { } // Utilities only.
}

File: okhttp-hpacktests/src/test/java/com/squareup/okhttp/internal/spdy/hpackjson/Story.java
/*
 * Copyright (C) 2014 Square, Inc.
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
package com.squareup.okhttp.internal.spdy.hpackjson;

import java.util.ArrayList;
import java.util.List;

/**
 * Representation of one story, a set of request headers to encode or decode.
 * This class is used reflectively with Gson to parse stories from files.
 */
public class Story implements Cloneable {

  private transient String fileName;
  private List<Case> cases;
  private int draft;
  private String description;

  /**
   * The filename is only used in the toString representation.
   */
  void setFileName(String fileName) {
    this.fileName = fileName;
  }

  public List<Case> getCases() {
    return cases;
  }

  /** We only expect stories that match the draft we've implemented to pass. */
  public int getDraft() {
    return draft;
  }

  @Override
  public Story clone() throws CloneNotSupportedException {
    Story story = new Story();
    story.fileName = this.fileName;
    story.cases = new ArrayList<>();
    for (Case caze : cases) {
      story.cases.add(caze.clone());
    }
    story.draft = draft;
    story.description = description;
    return story;
  }

  @Override
  public String toString() {
    // Used as the test name.
    return fileName;
  }
}


File: okhttp-tests/src/test/java/com/squareup/okhttp/TestUtil.java
package com.squareup.okhttp;

import com.squareup.okhttp.internal.spdy.Header;
import java.util.ArrayList;
import java.util.Arrays;
import java.util.Collection;
import java.util.LinkedHashSet;
import java.util.List;
import java.util.Set;

public final class TestUtil {
  private TestUtil() {
  }

  public static List<Header> headerEntries(String... elements) {
    List<Header> result = new ArrayList<>(elements.length / 2);
    for (int i = 0; i < elements.length; i += 2) {
      result.add(new Header(elements[i], elements[i + 1]));
    }
    return result;
  }

  public static <T> Set<T> setOf(T... elements) {
    return setOf(Arrays.asList(elements));
  }

  public static <T> Set<T> setOf(Collection<T> elements) {
    return new LinkedHashSet<>(elements);
  }
}


File: okhttp-tests/src/test/java/com/squareup/okhttp/internal/http/HeadersTest.java
/*
 * Copyright (C) 2012 Square, Inc.
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
package com.squareup.okhttp.internal.http;

import com.squareup.okhttp.Headers;
import com.squareup.okhttp.Protocol;
import com.squareup.okhttp.Request;
import com.squareup.okhttp.Response;
import com.squareup.okhttp.internal.spdy.Header;
import java.io.IOException;
import java.util.Arrays;
import java.util.Collections;
import java.util.HashMap;
import java.util.List;
import java.util.Map;

import org.junit.Test;

import static com.squareup.okhttp.TestUtil.headerEntries;
import static org.junit.Assert.assertEquals;
import static org.junit.Assert.assertNull;
import static org.junit.Assert.fail;

public final class HeadersTest {
  @Test public void parseNameValueBlock() throws IOException {
    List<Header> headerBlock = headerEntries(
        "cache-control", "no-cache, no-store",
        "set-cookie", "Cookie1\u0000Cookie2",
        ":status", "200 OK",
        ":version", "HTTP/1.1");
    Request request = new Request.Builder().url("http://square.com/").build();
    Response response =
        SpdyTransport.readNameValueBlock(headerBlock, Protocol.SPDY_3).request(request).build();
    Headers headers = response.headers();
    assertEquals(4, headers.size());
    assertEquals(Protocol.SPDY_3, response.protocol());
    assertEquals(200, response.code());
    assertEquals("OK", response.message());
    assertEquals("no-cache, no-store", headers.get("cache-control"));
    assertEquals("Cookie2", headers.get("set-cookie"));
    assertEquals(Protocol.SPDY_3.toString(), headers.get(OkHeaders.SELECTED_PROTOCOL));
    assertEquals(OkHeaders.SELECTED_PROTOCOL, headers.name(0));
    assertEquals(Protocol.SPDY_3.toString(), headers.value(0));
    assertEquals("cache-control", headers.name(1));
    assertEquals("no-cache, no-store", headers.value(1));
    assertEquals("set-cookie", headers.name(2));
    assertEquals("Cookie1", headers.value(2));
    assertEquals("set-cookie", headers.name(3));
    assertEquals("Cookie2", headers.value(3));
    assertNull(headers.get(":status"));
    assertNull(headers.get(":version"));
  }

  @Test public void readNameValueBlockDropsForbiddenHeadersSpdy3() throws IOException {
    List<Header> headerBlock = headerEntries(
        ":status", "200 OK",
        ":version", "HTTP/1.1",
        "connection", "close");
    Request request = new Request.Builder().url("http://square.com/").build();
    Response response =
        SpdyTransport.readNameValueBlock(headerBlock, Protocol.SPDY_3).request(request).build();
    Headers headers = response.headers();
    assertEquals(1, headers.size());
    assertEquals(OkHeaders.SELECTED_PROTOCOL, headers.name(0));
    assertEquals(Protocol.SPDY_3.toString(), headers.value(0));
  }

  @Test public void readNameValueBlockDropsForbiddenHeadersHttp2() throws IOException {
    List<Header> headerBlock = headerEntries(
        ":status", "200 OK",
        ":version", "HTTP/1.1",
        "connection", "close");
    Request request = new Request.Builder().url("http://square.com/").build();
    Response response = SpdyTransport.readNameValueBlock(headerBlock, Protocol.HTTP_2)
        .request(request).build();
    Headers headers = response.headers();
    assertEquals(1, headers.size());
    assertEquals(OkHeaders.SELECTED_PROTOCOL, headers.name(0));
    assertEquals(Protocol.HTTP_2.toString(), headers.value(0));
  }

  @Test public void toNameValueBlock() {
    Request request = new Request.Builder()
        .url("http://square.com/")
        .header("cache-control", "no-cache, no-store")
        .addHeader("set-cookie", "Cookie1")
        .addHeader("set-cookie", "Cookie2")
        .header(":status", "200 OK")
        .build();
    List<Header> headerBlock =
        SpdyTransport.writeNameValueBlock(request, Protocol.SPDY_3, "HTTP/1.1");
    List<Header> expected = headerEntries(
        ":method", "GET",
        ":path", "/",
        ":version", "HTTP/1.1",
        ":host", "square.com",
        ":scheme", "http",
        "cache-control", "no-cache, no-store",
        "set-cookie", "Cookie1\u0000Cookie2",
        ":status", "200 OK");
    assertEquals(expected, headerBlock);
  }

  @Test public void toNameValueBlockDropsForbiddenHeadersSpdy3() {
    Request request = new Request.Builder()
        .url("http://square.com/")
        .header("Connection", "close")
        .header("Transfer-Encoding", "chunked")
        .build();
    List<Header> expected = headerEntries(
        ":method", "GET",
        ":path", "/",
        ":version", "HTTP/1.1",
        ":host", "square.com",
        ":scheme", "http");
    assertEquals(expected, SpdyTransport.writeNameValueBlock(request, Protocol.SPDY_3, "HTTP/1.1"));
  }

  @Test public void toNameValueBlockDropsForbiddenHeadersHttp2() {
    Request request = new Request.Builder()
        .url("http://square.com/")
        .header("Connection", "upgrade")
        .header("Upgrade", "websocket")
        .build();
    List<Header> expected = headerEntries(
        ":method", "GET",
        ":path", "/",
        ":authority", "square.com",
        ":scheme", "http");
    assertEquals(expected,
        SpdyTransport.writeNameValueBlock(request, Protocol.HTTP_2, "HTTP/1.1"));
  }

  @Test public void ofTrims() {
    Headers headers = Headers.of("\t User-Agent \n", " \r OkHttp ");
    assertEquals("User-Agent", headers.name(0));
    assertEquals("OkHttp", headers.value(0));
  }

  @Test public void addParsing() {
    Headers headers = new Headers.Builder()
        .add("foo: bar")
        .add(" foo: baz") // Name leading whitespace is trimmed.
        .add("foo : bak") // Name trailing whitespace is trimmed.
        .add("ping:  pong  ") // Value whitespace is trimmed.
        .add("kit:kat") // Space after colon is not required.
        .build();
    assertEquals(Arrays.asList("bar", "baz", "bak"), headers.values("foo"));
    assertEquals(Arrays.asList("pong"), headers.values("ping"));
    assertEquals(Arrays.asList("kat"), headers.values("kit"));
  }

  @Test public void addThrowsOnEmptyName() {
    try {
      new Headers.Builder().add(": bar");
      fail();
    } catch (IllegalArgumentException expected) {
    }
    try {
      new Headers.Builder().add(" : bar");
      fail();
    } catch (IllegalArgumentException expected) {
    }
  }

  @Test public void addThrowsOnNoColon() {
    try {
      new Headers.Builder().add("foo bar");
      fail();
    } catch (IllegalArgumentException expected) {
    }
  }

  @Test public void addThrowsOnMultiColon() {
    try {
      new Headers.Builder().add(":status: 200 OK");
      fail();
    } catch (IllegalArgumentException expected) {
    }
  }

  @Test public void ofThrowsOddNumberOfHeaders() {
    try {
      Headers.of("User-Agent", "OkHttp", "Content-Length");
      fail();
    } catch (IllegalArgumentException expected) {
    }
  }

  @Test public void ofThrowsOnNull() {
    try {
      Headers.of("User-Agent", null);
      fail();
    } catch (IllegalArgumentException expected) {
    }
  }

  @Test public void ofThrowsOnEmptyName() {
    try {
      Headers.of("", "OkHttp");
      fail();
    } catch (IllegalArgumentException expected) {
    }
  }

  @Test public void ofAcceptsEmptyValue() {
    Headers headers = Headers.of("User-Agent", "");
    assertEquals("", headers.value(0));
  }

  @Test public void ofMakesDefensiveCopy() {
    String[] namesAndValues = {
        "User-Agent",
        "OkHttp"
    };
    Headers headers = Headers.of(namesAndValues);
    namesAndValues[1] = "Chrome";
    assertEquals("OkHttp", headers.value(0));
  }

  @Test public void ofRejectsNulChar() {
    try {
      Headers.of("User-Agent", "Square\u0000OkHttp");
      fail();
    } catch (IllegalArgumentException expected) {
    }
  }

  @Test public void ofMapThrowsOnNull() {
    try {
      Headers.of(Collections.<String, String>singletonMap("User-Agent", null));
      fail();
    } catch (IllegalArgumentException expected) {
    }
  }

  @Test public void ofMapThrowsOnEmptyName() {
    try {
      Headers.of(Collections.singletonMap("", "OkHttp"));
      fail();
    } catch (IllegalArgumentException expected) {
    }
  }

  @Test public void ofMapThrowsOnBlankName() {
    try {
      Headers.of(Collections.singletonMap(" ", "OkHttp"));
      fail();
    } catch (IllegalArgumentException expected) {
    }
  }

  @Test public void ofMapAcceptsEmptyValue() {
    Headers headers = Headers.of(Collections.singletonMap("User-Agent", ""));
    assertEquals("", headers.value(0));
  }

  @Test public void ofMapTrimsKey() {
    Headers headers = Headers.of(Collections.singletonMap(" User-Agent ", "OkHttp"));
    assertEquals("User-Agent", headers.name(0));
  }

  @Test public void ofMapTrimsValue() {
    Headers headers = Headers.of(Collections.singletonMap("User-Agent", " OkHttp "));
    assertEquals("OkHttp", headers.value(0));
  }

  @Test public void ofMapMakesDefensiveCopy() {
    Map<String, String> namesAndValues = new HashMap<>();
    namesAndValues.put("User-Agent", "OkHttp");

    Headers headers = Headers.of(namesAndValues);
    namesAndValues.put("User-Agent", "Chrome");
    assertEquals("OkHttp", headers.value(0));
  }

  @Test public void ofMapRejectsNulCharInName() {
    try {
      Headers.of(Collections.singletonMap("User-Agent", "Square\u0000OkHttp"));
      fail();
    } catch (IllegalArgumentException expected) {
    }
  }

  @Test public void ofMapRejectsNulCharInValue() {
    try {
      Headers.of(Collections.singletonMap("User-\u0000Agent", "OkHttp"));
      fail();
    } catch (IllegalArgumentException expected) {
    }
  }

  @Test public void toMultimapGroupsHeaders() {
    Headers headers = Headers.of(
        "cache-control", "no-cache",
        "cache-control", "no-store",
        "user-agent", "OkHttp");
    Map<String, List<String>> headerMap = headers.toMultimap();
    assertEquals(2, headerMap.get("cache-control").size());
    assertEquals(1, headerMap.get("user-agent").size());
  }
}


File: okhttp-tests/src/test/java/com/squareup/okhttp/internal/http/HttpOverSpdyTest.java
/*
 * Copyright (C) 2013 Square, Inc.
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
package com.squareup.okhttp.internal.http;

import com.squareup.okhttp.Cache;
import com.squareup.okhttp.ConnectionPool;
import com.squareup.okhttp.OkHttpClient;
import com.squareup.okhttp.OkUrlFactory;
import com.squareup.okhttp.Protocol;
import com.squareup.okhttp.internal.RecordingAuthenticator;
import com.squareup.okhttp.internal.SslContextBuilder;
import com.squareup.okhttp.internal.Util;
import com.squareup.okhttp.mockwebserver.MockResponse;
import com.squareup.okhttp.mockwebserver.RecordedRequest;
import com.squareup.okhttp.mockwebserver.SocketPolicy;
import com.squareup.okhttp.mockwebserver.rule.MockWebServerRule;
import java.io.IOException;
import java.io.InputStream;
import java.net.Authenticator;
import java.net.CookieManager;
import java.net.HttpURLConnection;
import java.net.SocketTimeoutException;
import java.net.URL;
import java.util.Arrays;
import java.util.Collections;
import java.util.List;
import java.util.Map;
import java.util.concurrent.CountDownLatch;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;
import java.util.concurrent.TimeUnit;
import javax.net.ssl.HostnameVerifier;
import javax.net.ssl.SSLContext;
import javax.net.ssl.SSLSession;
import okio.Buffer;
import okio.BufferedSink;
import okio.GzipSink;
import okio.Okio;
import org.junit.After;
import org.junit.Before;
import org.junit.Ignore;
import org.junit.Rule;
import org.junit.Test;
import org.junit.rules.TemporaryFolder;

import static java.util.concurrent.TimeUnit.SECONDS;
import static org.junit.Assert.assertArrayEquals;
import static org.junit.Assert.assertEquals;
import static org.junit.Assert.assertNull;
import static org.junit.Assert.fail;

/** Test how SPDY interacts with HTTP features. */
public abstract class HttpOverSpdyTest {
  private static final SSLContext sslContext = SslContextBuilder.localhost();

  private static final HostnameVerifier NULL_HOSTNAME_VERIFIER = new HostnameVerifier() {
    public boolean verify(String hostname, SSLSession session) {
      return true;
    }
  };

  @Rule public final TemporaryFolder tempDir = new TemporaryFolder();
  @Rule public final MockWebServerRule server = new MockWebServerRule();

  /** Protocol to test, for example {@link com.squareup.okhttp.Protocol#SPDY_3} */
  private final Protocol protocol;
  protected String hostHeader = ":host";

  protected final OkUrlFactory client = new OkUrlFactory(new OkHttpClient());
  protected HttpURLConnection connection;
  protected Cache cache;

  protected HttpOverSpdyTest(Protocol protocol){
    this.protocol = protocol;
  }

  @Before public void setUp() throws Exception {
    server.get().useHttps(sslContext.getSocketFactory(), false);
    client.client().setProtocols(Arrays.asList(protocol, Protocol.HTTP_1_1));
    client.client().setSslSocketFactory(sslContext.getSocketFactory());
    client.client().setHostnameVerifier(NULL_HOSTNAME_VERIFIER);
    cache = new Cache(tempDir.getRoot(), Integer.MAX_VALUE);
  }

  @After public void tearDown() throws Exception {
    Authenticator.setDefault(null);
  }

  @Test public void get() throws Exception {
    MockResponse response = new MockResponse().setBody("ABCDE").setStatus("HTTP/1.1 200 Sweet");
    server.enqueue(response);

    connection = client.open(server.getUrl("/foo"));
    assertContent("ABCDE", connection, Integer.MAX_VALUE);
    assertEquals(200, connection.getResponseCode());
    assertEquals("Sweet", connection.getResponseMessage());

    RecordedRequest request = server.takeRequest();
    assertEquals("GET /foo HTTP/1.1", request.getRequestLine());
    assertEquals("https", request.getHeader(":scheme"));
    assertEquals(server.getHostName() + ":" + server.getPort(), request.getHeader(hostHeader));
  }

  @Test public void emptyResponse() throws IOException {
    server.enqueue(new MockResponse());

    connection = client.open(server.getUrl("/foo"));
    assertEquals(-1, connection.getInputStream().read());
  }

  byte[] postBytes = "FGHIJ".getBytes(Util.UTF_8);

  @Test public void noDefaultContentLengthOnStreamingPost() throws Exception {
    server.enqueue(new MockResponse().setBody("ABCDE"));

    connection = client.open(server.getUrl("/foo"));
    connection.setDoOutput(true);
    connection.setChunkedStreamingMode(0);
    connection.getOutputStream().write(postBytes);
    assertContent("ABCDE", connection, Integer.MAX_VALUE);

    RecordedRequest request = server.takeRequest();
    assertEquals("POST /foo HTTP/1.1", request.getRequestLine());
    assertArrayEquals(postBytes, request.getBody().readByteArray());
    assertNull(request.getHeader("Content-Length"));
  }

  @Test public void userSuppliedContentLengthHeader() throws Exception {
    server.enqueue(new MockResponse().setBody("ABCDE"));

    connection = client.open(server.getUrl("/foo"));
    connection.setRequestProperty("Content-Length", String.valueOf(postBytes.length));
    connection.setDoOutput(true);
    connection.getOutputStream().write(postBytes);
    assertContent("ABCDE", connection, Integer.MAX_VALUE);

    RecordedRequest request = server.takeRequest();
    assertEquals("POST /foo HTTP/1.1", request.getRequestLine());
    assertArrayEquals(postBytes, request.getBody().readByteArray());
    assertEquals(postBytes.length, Integer.parseInt(request.getHeader("Content-Length")));
  }

  @Test public void closeAfterFlush() throws Exception {
    server.enqueue(new MockResponse().setBody("ABCDE"));

    connection = client.open(server.getUrl("/foo"));
    connection.setRequestProperty("Content-Length", String.valueOf(postBytes.length));
    connection.setDoOutput(true);
    connection.getOutputStream().write(postBytes); // push bytes into SpdyDataOutputStream.buffer
    connection.getOutputStream().flush(); // SpdyConnection.writeData subject to write window
    connection.getOutputStream().close(); // SpdyConnection.writeData empty frame
    assertContent("ABCDE", connection, Integer.MAX_VALUE);

    RecordedRequest request = server.takeRequest();
    assertEquals("POST /foo HTTP/1.1", request.getRequestLine());
    assertArrayEquals(postBytes, request.getBody().readByteArray());
    assertEquals(postBytes.length, Integer.parseInt(request.getHeader("Content-Length")));
  }

  @Test public void setFixedLengthStreamingModeSetsContentLength() throws Exception {
    server.enqueue(new MockResponse().setBody("ABCDE"));

    connection = client.open(server.getUrl("/foo"));
    connection.setFixedLengthStreamingMode(postBytes.length);
    connection.setDoOutput(true);
    connection.getOutputStream().write(postBytes);
    assertContent("ABCDE", connection, Integer.MAX_VALUE);

    RecordedRequest request = server.takeRequest();
    assertEquals("POST /foo HTTP/1.1", request.getRequestLine());
    assertArrayEquals(postBytes, request.getBody().readByteArray());
    assertEquals(postBytes.length, Integer.parseInt(request.getHeader("Content-Length")));
  }

  @Test public void spdyConnectionReuse() throws Exception {
    server.enqueue(new MockResponse().setBody("ABCDEF"));
    server.enqueue(new MockResponse().setBody("GHIJKL"));

    HttpURLConnection connection1 = client.open(server.getUrl("/r1"));
    HttpURLConnection connection2 = client.open(server.getUrl("/r2"));
    assertEquals("ABC", readAscii(connection1.getInputStream(), 3));
    assertEquals("GHI", readAscii(connection2.getInputStream(), 3));
    assertEquals("DEF", readAscii(connection1.getInputStream(), 3));
    assertEquals("JKL", readAscii(connection2.getInputStream(), 3));
    assertEquals(0, server.takeRequest().getSequenceNumber());
    assertEquals(1, server.takeRequest().getSequenceNumber());
  }

  @Test @Ignore public void synchronousSpdyRequest() throws Exception {
    server.enqueue(new MockResponse().setBody("A"));
    server.enqueue(new MockResponse().setBody("A"));

    ExecutorService executor = Executors.newCachedThreadPool();
    CountDownLatch countDownLatch = new CountDownLatch(2);
    executor.execute(new SpdyRequest("/r1", countDownLatch));
    executor.execute(new SpdyRequest("/r2", countDownLatch));
    countDownLatch.await();
    assertEquals(0, server.takeRequest().getSequenceNumber());
    assertEquals(1, server.takeRequest().getSequenceNumber());
  }

  @Test public void gzippedResponseBody() throws Exception {
    server.enqueue(
        new MockResponse().addHeader("Content-Encoding: gzip").setBody(gzip("ABCABCABC")));
    assertContent("ABCABCABC", client.open(server.getUrl("/r1")), Integer.MAX_VALUE);
  }

  @Test public void authenticate() throws Exception {
    server.enqueue(new MockResponse().setResponseCode(HttpURLConnection.HTTP_UNAUTHORIZED)
        .addHeader("www-authenticate: Basic realm=\"protected area\"")
        .setBody("Please authenticate."));
    server.enqueue(new MockResponse().setBody("Successful auth!"));

    Authenticator.setDefault(new RecordingAuthenticator());
    connection = client.open(server.getUrl("/"));
    assertEquals("Successful auth!", readAscii(connection.getInputStream(), Integer.MAX_VALUE));

    RecordedRequest denied = server.takeRequest();
    assertNull(denied.getHeader("Authorization"));
    RecordedRequest accepted = server.takeRequest();
    assertEquals("GET / HTTP/1.1", accepted.getRequestLine());
    assertEquals("Basic " + RecordingAuthenticator.BASE_64_CREDENTIALS,
        accepted.getHeader("Authorization"));
  }

  @Test public void redirect() throws Exception {
    server.enqueue(new MockResponse().setResponseCode(HttpURLConnection.HTTP_MOVED_TEMP)
        .addHeader("Location: /foo")
        .setBody("This page has moved!"));
    server.enqueue(new MockResponse().setBody("This is the new location!"));

    connection = client.open(server.getUrl("/"));
    assertContent("This is the new location!", connection, Integer.MAX_VALUE);

    RecordedRequest request1 = server.takeRequest();
    assertEquals("/", request1.getPath());
    RecordedRequest request2 = server.takeRequest();
    assertEquals("/foo", request2.getPath());
  }

  @Test public void readAfterLastByte() throws Exception {
    server.enqueue(new MockResponse().setBody("ABC"));

    connection = client.open(server.getUrl("/"));
    InputStream in = connection.getInputStream();
    assertEquals("ABC", readAscii(in, 3));
    assertEquals(-1, in.read());
    assertEquals(-1, in.read());
  }

  @Ignore // See https://github.com/square/okhttp/issues/578
  @Test(timeout = 3000) public void readResponseHeaderTimeout() throws Exception {
    server.enqueue(new MockResponse().setSocketPolicy(SocketPolicy.NO_RESPONSE));
    server.enqueue(new MockResponse().setBody("A"));

    connection = client.open(server.getUrl("/"));
    connection.setReadTimeout(1000);
    assertContent("A", connection, Integer.MAX_VALUE);
  }

  /**
   * Test to ensure we don't  throw a read timeout on responses that are
   * progressing.  For this case, we take a 4KiB body and throttle it to
   * 1KiB/second.  We set the read timeout to two seconds.  If our
   * implementation is acting correctly, it will not throw, as it is
   * progressing.
   */
  @Test public void readTimeoutMoreGranularThanBodySize() throws Exception {
    char[] body = new char[4096]; // 4KiB to read
    Arrays.fill(body, 'y');
    server.enqueue(new MockResponse().setBody(new String(body)).throttleBody(1024, 1, SECONDS)); // slow connection 1KiB/second

    connection = client.open(server.getUrl("/"));
    connection.setReadTimeout(2000); // 2 seconds to read something.
    assertContent(new String(body), connection, Integer.MAX_VALUE);
  }

  /**
   * Test to ensure we throw a read timeout on responses that are progressing
   * too slowly.  For this case, we take a 2KiB body and throttle it to
   * 1KiB/second.  We set the read timeout to half a second.  If our
   * implementation is acting correctly, it will throw, as a byte doesn't
   * arrive in time.
   */
  @Test public void readTimeoutOnSlowConnection() throws Exception {
    char[] body = new char[2048]; // 2KiB to read
    Arrays.fill(body, 'y');
    server.enqueue(new MockResponse()
        .setBody(new String(body))
        .throttleBody(1024, 1, SECONDS)); // slow connection 1KiB/second

    connection = client.open(server.getUrl("/"));
    connection.setReadTimeout(500); // half a second to read something
    connection.connect();
    try {
      readAscii(connection.getInputStream(), Integer.MAX_VALUE);
      fail("Should have timed out!");
    } catch (SocketTimeoutException expected) {
      assertEquals("timeout", expected.getMessage());
    }
  }

  @Test public void spdyConnectionTimeout() throws Exception {
    MockResponse response = new MockResponse().setBody("A");
    response.setBodyDelay(1, TimeUnit.SECONDS);
    server.enqueue(response);

    HttpURLConnection connection1 = client.open(server.getUrl("/"));
    connection1.setReadTimeout(2000);
    HttpURLConnection connection2 = client.open(server.getUrl("/"));
    connection2.setReadTimeout(200);
    connection1.connect();
    connection2.connect();
    assertContent("A", connection1, Integer.MAX_VALUE);
  }

  @Test public void responsesAreCached() throws IOException {
    client.client().setCache(cache);

    server.enqueue(new MockResponse().addHeader("cache-control: max-age=60").setBody("A"));

    assertContent("A", client.open(server.getUrl("/")), Integer.MAX_VALUE);
    assertEquals(1, cache.getRequestCount());
    assertEquals(1, cache.getNetworkCount());
    assertEquals(0, cache.getHitCount());
    assertContent("A", client.open(server.getUrl("/")), Integer.MAX_VALUE);
    assertContent("A", client.open(server.getUrl("/")), Integer.MAX_VALUE);
    assertEquals(3, cache.getRequestCount());
    assertEquals(1, cache.getNetworkCount());
    assertEquals(2, cache.getHitCount());
  }

  @Test public void conditionalCache() throws IOException {
    client.client().setCache(cache);

    server.enqueue(new MockResponse().addHeader("ETag: v1").setBody("A"));
    server.enqueue(new MockResponse().setResponseCode(HttpURLConnection.HTTP_NOT_MODIFIED));

    assertContent("A", client.open(server.getUrl("/")), Integer.MAX_VALUE);
    assertEquals(1, cache.getRequestCount());
    assertEquals(1, cache.getNetworkCount());
    assertEquals(0, cache.getHitCount());
    assertContent("A", client.open(server.getUrl("/")), Integer.MAX_VALUE);
    assertEquals(2, cache.getRequestCount());
    assertEquals(2, cache.getNetworkCount());
    assertEquals(1, cache.getHitCount());
  }

  @Test public void responseCachedWithoutConsumingFullBody() throws IOException {
    client.client().setCache(cache);

    server.enqueue(new MockResponse().addHeader("cache-control: max-age=60").setBody("ABCD"));
    server.enqueue(new MockResponse().addHeader("cache-control: max-age=60").setBody("EFGH"));

    HttpURLConnection connection1 = client.open(server.getUrl("/"));
    InputStream in1 = connection1.getInputStream();
    assertEquals("AB", readAscii(in1, 2));
    in1.close();

    HttpURLConnection connection2 = client.open(server.getUrl("/"));
    InputStream in2 = connection2.getInputStream();
    assertEquals("ABCD", readAscii(in2, Integer.MAX_VALUE));
    in2.close();
  }

  @Test public void acceptAndTransmitCookies() throws Exception {
    CookieManager cookieManager = new CookieManager();
    client.client().setCookieHandler(cookieManager);

    server.enqueue(new MockResponse()
        .addHeader("set-cookie: c=oreo; domain=" + server.get().getCookieDomain())
        .setBody("A"));
    server.enqueue(new MockResponse()
        .setBody("B"));

    URL url = server.getUrl("/");
    assertContent("A", client.open(url), Integer.MAX_VALUE);
    Map<String, List<String>> requestHeaders = Collections.emptyMap();
    assertEquals(Collections.singletonMap("Cookie", Arrays.asList("c=oreo")),
        cookieManager.get(url.toURI(), requestHeaders));

    assertContent("B", client.open(url), Integer.MAX_VALUE);
    RecordedRequest requestA = server.takeRequest();
    assertNull(requestA.getHeader("Cookie"));
    RecordedRequest requestB = server.takeRequest();
    assertEquals("c=oreo", requestB.getHeader("Cookie"));
  }

  /** https://github.com/square/okhttp/issues/1191 */
  @Test public void disconnectWithStreamNotEstablished() throws Exception {
    ConnectionPool connectionPool = new ConnectionPool(5, 5000);
    client.client().setConnectionPool(connectionPool);

    server.enqueue(new MockResponse().setBody("abc"));

    // Disconnect before the stream is created. A connection is still established!
    HttpURLConnection connection1 = client.open(server.getUrl("/"));
    connection1.connect();
    connection1.disconnect();

    // That connection is pooled, and it works.
    assertEquals(1, connectionPool.getSpdyConnectionCount());
    HttpURLConnection connection2 = client.open(server.getUrl("/"));
    assertContent("abc", connection2, 3);
    assertEquals(0, server.takeRequest().getSequenceNumber());
  }

  void assertContent(String expected, HttpURLConnection connection, int limit)
      throws IOException {
    connection.connect();
    assertEquals(expected, readAscii(connection.getInputStream(), limit));
  }

  private String readAscii(InputStream in, int count) throws IOException {
    StringBuilder result = new StringBuilder();
    for (int i = 0; i < count; i++) {
      int value = in.read();
      if (value == -1) {
        in.close();
        break;
      }
      result.append((char) value);
    }
    return result.toString();
  }

  public Buffer gzip(String bytes) throws IOException {
    Buffer bytesOut = new Buffer();
    BufferedSink sink = Okio.buffer(new GzipSink(bytesOut));
    sink.writeUtf8(bytes);
    sink.close();
    return bytesOut;
  }

  class SpdyRequest implements Runnable {
    String path;
    CountDownLatch countDownLatch;
    public SpdyRequest(String path, CountDownLatch countDownLatch) {
      this.path = path;
      this.countDownLatch = countDownLatch;
    }

    @Override public void run() {
      try {
        HttpURLConnection conn = client.open(server.getUrl(path));
        assertEquals("A", readAscii(conn.getInputStream(), 1));
        countDownLatch.countDown();
      } catch (Exception e) {
        throw new RuntimeException(e);
      }
    }
  }
}


File: okhttp/src/main/java/com/squareup/okhttp/Connection.java
/*
 *  Licensed to the Apache Software Foundation (ASF) under one or more
 *  contributor license agreements.  See the NOTICE file distributed with
 *  this work for additional information regarding copyright ownership.
 *  The ASF licenses this file to You under the Apache License, Version 2.0
 *  (the "License"); you may not use this file except in compliance with
 *  the License.  You may obtain a copy of the License at
 *
 *     http://www.apache.org/licenses/LICENSE-2.0
 *
 *  Unless required by applicable law or agreed to in writing, software
 *  distributed under the License is distributed on an "AS IS" BASIS,
 *  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 *  See the License for the specific language governing permissions and
 *  limitations under the License.
 */
package com.squareup.okhttp;

import com.squareup.okhttp.internal.http.HttpConnection;
import com.squareup.okhttp.internal.http.HttpEngine;
import com.squareup.okhttp.internal.http.HttpTransport;
import com.squareup.okhttp.internal.http.RouteException;
import com.squareup.okhttp.internal.http.SocketConnector;
import com.squareup.okhttp.internal.http.SpdyTransport;
import com.squareup.okhttp.internal.http.Transport;
import com.squareup.okhttp.internal.spdy.SpdyConnection;
import java.io.IOException;
import java.net.Socket;
import java.net.UnknownServiceException;
import java.util.List;
import okio.BufferedSink;
import okio.BufferedSource;

/**
 * The sockets and streams of an HTTP, HTTPS, or HTTPS+SPDY connection. May be
 * used for multiple HTTP request/response exchanges. Connections may be direct
 * to the origin server or via a proxy.
 *
 * <p>Typically instances of this class are created, connected and exercised
 * automatically by the HTTP client. Applications may use this class to monitor
 * HTTP connections as members of a {@linkplain ConnectionPool connection pool}.
 *
 * <p>Do not confuse this class with the misnamed {@code HttpURLConnection},
 * which isn't so much a connection as a single request/response exchange.
 *
 * <h3>Modern TLS</h3>
 * There are tradeoffs when selecting which options to include when negotiating
 * a secure connection to a remote host. Newer TLS options are quite useful:
 * <ul>
 *   <li>Server Name Indication (SNI) enables one IP address to negotiate secure
 *       connections for multiple domain names.
 *   <li>Application Layer Protocol Negotiation (ALPN) enables the HTTPS port
 *       (443) to be used for different HTTP and SPDY protocols.
 * </ul>
 * Unfortunately, older HTTPS servers refuse to connect when such options are
 * presented. Rather than avoiding these options entirely, this class allows a
 * connection to be attempted with modern options and then retried without them
 * should the attempt fail.
 */
public final class Connection {
  private final ConnectionPool pool;
  private final Route route;

  private Socket socket;
  private boolean connected = false;
  private HttpConnection httpConnection;
  private SpdyConnection spdyConnection;
  private Protocol protocol = Protocol.HTTP_1_1;
  private long idleStartTimeNs;
  private Handshake handshake;
  private int recycleCount;

  /**
   * The object that owns this connection. Null if it is shared (for SPDY),
   * belongs to a pool, or has been discarded. Guarded by {@code pool}, which
   * clears the owner when an incoming connection is recycled.
   */
  private Object owner;

  public Connection(ConnectionPool pool, Route route) {
    this.pool = pool;
    this.route = route;
  }

  Object getOwner() {
    synchronized (pool) {
      return owner;
    }
  }

  void setOwner(Object owner) {
    if (isSpdy()) return; // SPDY connections are shared.
    synchronized (pool) {
      if (this.owner != null) throw new IllegalStateException("Connection already has an owner!");
      this.owner = owner;
    }
  }

  /**
   * Attempts to clears the owner of this connection. Returns true if the owner
   * was cleared and the connection can be pooled or reused. This will return
   * false if the connection cannot be pooled or reused, such as if it was
   * closed with {@link #closeIfOwnedBy}.
   */
  boolean clearOwner() {
    synchronized (pool) {
      if (owner == null) {
        // No owner? Don't reuse this connection.
        return false;
      }

      owner = null;
      return true;
    }
  }

  /**
   * Closes this connection if it is currently owned by {@code owner}. This also
   * strips the ownership of the connection so it cannot be pooled or reused.
   */
  void closeIfOwnedBy(Object owner) throws IOException {
    if (isSpdy()) throw new IllegalStateException();
    synchronized (pool) {
      if (this.owner != owner) {
        return; // Wrong owner. Perhaps a late disconnect?
      }

      this.owner = null; // Drop the owner so the connection won't be reused.
    }

    // Don't close() inside the synchronized block.
    socket.close();
  }

  void connect(int connectTimeout, int readTimeout, int writeTimeout, Request request,
      List<ConnectionSpec> connectionSpecs, boolean connectionRetryEnabled) throws RouteException {
    if (connected) throw new IllegalStateException("already connected");

    SocketConnector socketConnector = new SocketConnector(this, pool);
    SocketConnector.ConnectedSocket connectedSocket;
    if (route.address.getSslSocketFactory() != null) {
      // https:// communication
      connectedSocket = socketConnector.connectTls(connectTimeout, readTimeout, writeTimeout,
          request, route, connectionSpecs, connectionRetryEnabled);
    } else {
      // http:// communication.
      if (!connectionSpecs.contains(ConnectionSpec.CLEARTEXT)) {
        throw new RouteException(
            new UnknownServiceException(
                "CLEARTEXT communication not supported: " + connectionSpecs));
      }
      connectedSocket = socketConnector.connectCleartext(connectTimeout, readTimeout, route);
    }

    socket = connectedSocket.socket;
    handshake = connectedSocket.handshake;
    protocol = connectedSocket.alpnProtocol == null
        ? Protocol.HTTP_1_1 : connectedSocket.alpnProtocol;

    try {
      if (protocol == Protocol.SPDY_3 || protocol == Protocol.HTTP_2) {
        socket.setSoTimeout(0); // SPDY timeouts are set per-stream.
        spdyConnection = new SpdyConnection.Builder(route.address.uriHost, true, socket)
            .protocol(protocol).build();
        spdyConnection.sendConnectionPreface();
      } else {
        httpConnection = new HttpConnection(pool, this, socket);
      }
    } catch (IOException e) {
      throw new RouteException(e);
    }
    connected = true;
  }

  /**
   * Connects this connection if it isn't already. This creates tunnels, shares
   * the connection with the connection pool, and configures timeouts.
   */
  void connectAndSetOwner(OkHttpClient client, Object owner, Request request)
      throws RouteException {
    setOwner(owner);

    if (!isConnected()) {
      List<ConnectionSpec> connectionSpecs = route.address.getConnectionSpecs();
      connect(client.getConnectTimeout(), client.getReadTimeout(), client.getWriteTimeout(),
          request, connectionSpecs, client.getRetryOnConnectionFailure());
      if (isSpdy()) {
        client.getConnectionPool().share(this);
      }
      client.routeDatabase().connected(getRoute());
    }

    setTimeouts(client.getReadTimeout(), client.getWriteTimeout());
  }

  /** Returns true if {@link #connect} has been attempted on this connection. */
  boolean isConnected() {
    return connected;
  }

  /** Returns the route used by this connection. */
  public Route getRoute() {
    return route;
  }

  /**
   * Returns the socket that this connection uses, or null if the connection
   * is not currently connected.
   */
  public Socket getSocket() {
    return socket;
  }

  BufferedSource rawSource() {
    if (httpConnection == null) throw new UnsupportedOperationException();
    return httpConnection.rawSource();
  }

  BufferedSink rawSink() {
    if (httpConnection == null) throw new UnsupportedOperationException();
    return httpConnection.rawSink();
  }

  /** Returns true if this connection is alive. */
  boolean isAlive() {
    return !socket.isClosed() && !socket.isInputShutdown() && !socket.isOutputShutdown();
  }

  /**
   * Returns true if we are confident that we can read data from this
   * connection. This is more expensive and more accurate than {@link
   * #isAlive()}; callers should check {@link #isAlive()} first.
   */
  boolean isReadable() {
    if (httpConnection != null) return httpConnection.isReadable();
    return true; // SPDY connections, and connections before connect() are both optimistic.
  }

  void resetIdleStartTime() {
    if (spdyConnection != null) throw new IllegalStateException("spdyConnection != null");
    this.idleStartTimeNs = System.nanoTime();
  }

  /** Returns true if this connection is idle. */
  boolean isIdle() {
    return spdyConnection == null || spdyConnection.isIdle();
  }

  /**
   * Returns the time in ns when this connection became idle. Undefined if
   * this connection is not idle.
   */
  long getIdleStartTimeNs() {
    return spdyConnection == null ? idleStartTimeNs : spdyConnection.getIdleStartTimeNs();
  }

  public Handshake getHandshake() {
    return handshake;
  }

  /** Returns the transport appropriate for this connection. */
  Transport newTransport(HttpEngine httpEngine) throws IOException {
    return (spdyConnection != null)
        ? new SpdyTransport(httpEngine, spdyConnection)
        : new HttpTransport(httpEngine, httpConnection);
  }

  /**
   * Returns true if this is a SPDY connection. Such connections can be used
   * in multiple HTTP requests simultaneously.
   */
  boolean isSpdy() {
    return spdyConnection != null;
  }

  /**
   * Returns the protocol negotiated by this connection, or {@link
   * Protocol#HTTP_1_1} if no protocol has been negotiated.
   */
  public Protocol getProtocol() {
    return protocol;
  }

  /**
   * Sets the protocol negotiated by this connection. Typically this is used
   * when an HTTP/1.1 request is sent and an HTTP/1.0 response is received.
   */
  void setProtocol(Protocol protocol) {
    if (protocol == null) throw new IllegalArgumentException("protocol == null");
    this.protocol = protocol;
  }

  void setTimeouts(int readTimeoutMillis, int writeTimeoutMillis)
      throws RouteException {
    if (!connected) throw new IllegalStateException("setTimeouts - not connected");

    // Don't set timeouts on shared SPDY connections.
    if (httpConnection != null) {
      try {
        socket.setSoTimeout(readTimeoutMillis);
      } catch (IOException e) {
        throw new RouteException(e);
      }
      httpConnection.setTimeouts(readTimeoutMillis, writeTimeoutMillis);
    }
  }

  void incrementRecycleCount() {
    recycleCount++;
  }

  /**
   * Returns the number of times this connection has been returned to the
   * connection pool.
   */
  int recycleCount() {
    return recycleCount;
  }

  @Override public String toString() {
    return "Connection{"
        + route.address.uriHost + ":" + route.address.uriPort
        + ", proxy="
        + route.proxy
        + " hostAddress="
        + route.inetSocketAddress.getAddress().getHostAddress()
        + " cipherSuite="
        + (handshake != null ? handshake.cipherSuite() : "none")
        + " protocol="
        + protocol
        + '}';
  }
}


File: okhttp/src/main/java/com/squareup/okhttp/ConnectionPool.java
/*
 *  Licensed to the Apache Software Foundation (ASF) under one or more
 *  contributor license agreements.  See the NOTICE file distributed with
 *  this work for additional information regarding copyright ownership.
 *  The ASF licenses this file to You under the Apache License, Version 2.0
 *  (the "License"); you may not use this file except in compliance with
 *  the License.  You may obtain a copy of the License at
 *
 *     http://www.apache.org/licenses/LICENSE-2.0
 *
 *  Unless required by applicable law or agreed to in writing, software
 *  distributed under the License is distributed on an "AS IS" BASIS,
 *  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 *  See the License for the specific language governing permissions and
 *  limitations under the License.
 */
package com.squareup.okhttp;

import com.squareup.okhttp.internal.Platform;
import com.squareup.okhttp.internal.Util;
import java.net.SocketException;
import java.util.ArrayList;
import java.util.LinkedList;
import java.util.List;
import java.util.ListIterator;
import java.util.concurrent.Executor;
import java.util.concurrent.LinkedBlockingQueue;
import java.util.concurrent.ThreadPoolExecutor;
import java.util.concurrent.TimeUnit;

/**
 * Manages reuse of HTTP and SPDY connections for reduced network latency. HTTP
 * requests that share the same {@link com.squareup.okhttp.Address} may share a
 * {@link com.squareup.okhttp.Connection}. This class implements the policy of
 * which connections to keep open for future use.
 *
 * <p>The {@link #getDefault() system-wide default} uses system properties for
 * tuning parameters:
 * <ul>
 *     <li>{@code http.keepAlive} true if HTTP and SPDY connections should be
 *         pooled at all. Default is true.
 *     <li>{@code http.maxConnections} maximum number of idle connections to
 *         each to keep in the pool. Default is 5.
 *     <li>{@code http.keepAliveDuration} Time in milliseconds to keep the
 *         connection alive in the pool before closing it. Default is 5 minutes.
 *         This property isn't used by {@code HttpURLConnection}.
 * </ul>
 *
 * <p>The default instance <i>doesn't</i> adjust its configuration as system
 * properties are changed. This assumes that the applications that set these
 * parameters do so before making HTTP connections, and that this class is
 * initialized lazily.
 */
public final class ConnectionPool {
  private static final long DEFAULT_KEEP_ALIVE_DURATION_MS = 5 * 60 * 1000; // 5 min

  private static final ConnectionPool systemDefault;

  static {
    String keepAlive = System.getProperty("http.keepAlive");
    String keepAliveDuration = System.getProperty("http.keepAliveDuration");
    String maxIdleConnections = System.getProperty("http.maxConnections");
    long keepAliveDurationMs = keepAliveDuration != null ? Long.parseLong(keepAliveDuration)
        : DEFAULT_KEEP_ALIVE_DURATION_MS;
    if (keepAlive != null && !Boolean.parseBoolean(keepAlive)) {
      systemDefault = new ConnectionPool(0, keepAliveDurationMs);
    } else if (maxIdleConnections != null) {
      systemDefault = new ConnectionPool(Integer.parseInt(maxIdleConnections), keepAliveDurationMs);
    } else {
      systemDefault = new ConnectionPool(5, keepAliveDurationMs);
    }
  }

  /** The maximum number of idle connections for each address. */
  private final int maxIdleConnections;
  private final long keepAliveDurationNs;

  private final LinkedList<Connection> connections = new LinkedList<>();

  /**
   * A background thread is used to cleanup expired connections. There will be, at most, a single
   * thread running per connection pool.
   *
   * <p>A {@link ThreadPoolExecutor} is used and not a
   * {@link java.util.concurrent.ScheduledThreadPoolExecutor}; ScheduledThreadPoolExecutors do not
   * shrink. This executor shrinks the thread pool after a period of inactivity, and starts threads
   * as needed. Delays are instead handled by the {@link #connectionsCleanupRunnable}. It is
   * important that the {@link #connectionsCleanupRunnable} stops eventually, otherwise it will pin
   * the thread, and thus the connection pool, in memory.
   */
  private Executor executor = new ThreadPoolExecutor(
      0 /* corePoolSize */, 1 /* maximumPoolSize */, 60L /* keepAliveTime */, TimeUnit.SECONDS,
      new LinkedBlockingQueue<Runnable>(), Util.threadFactory("OkHttp ConnectionPool", true));

  private final Runnable connectionsCleanupRunnable = new Runnable() {
    @Override public void run() {
      runCleanupUntilPoolIsEmpty();
    }
  };

  public ConnectionPool(int maxIdleConnections, long keepAliveDurationMs) {
    this.maxIdleConnections = maxIdleConnections;
    this.keepAliveDurationNs = keepAliveDurationMs * 1000 * 1000;
  }

  public static ConnectionPool getDefault() {
    return systemDefault;
  }

  /** Returns total number of connections in the pool. */
  public synchronized int getConnectionCount() {
    return connections.size();
  }

  /** @deprecated Use {@link #getMultiplexedConnectionCount()}. */
  @Deprecated
  public synchronized int getSpdyConnectionCount() {
    return getMultiplexedConnectionCount();
  }

  /** Returns total number of multiplexed connections in the pool. */
  public synchronized int getMultiplexedConnectionCount() {
    int total = 0;
    for (Connection connection : connections) {
      if (connection.isSpdy()) total++;
    }
    return total;
  }

  /** Returns total number of http connections in the pool. */
  public synchronized int getHttpConnectionCount() {
    return connections.size() - getMultiplexedConnectionCount();
  }

  /** Returns a recycled connection to {@code address}, or null if no such connection exists. */
  public synchronized Connection get(Address address) {
    Connection foundConnection = null;
    for (ListIterator<Connection> i = connections.listIterator(connections.size());
        i.hasPrevious(); ) {
      Connection connection = i.previous();
      if (!connection.getRoute().getAddress().equals(address)
          || !connection.isAlive()
          || System.nanoTime() - connection.getIdleStartTimeNs() >= keepAliveDurationNs) {
        continue;
      }
      i.remove();
      if (!connection.isSpdy()) {
        try {
          Platform.get().tagSocket(connection.getSocket());
        } catch (SocketException e) {
          Util.closeQuietly(connection.getSocket());
          // When unable to tag, skip recycling and close
          Platform.get().logW("Unable to tagSocket(): " + e);
          continue;
        }
      }
      foundConnection = connection;
      break;
    }

    if (foundConnection != null && foundConnection.isSpdy()) {
      connections.addFirst(foundConnection); // Add it back after iteration.
    }

    return foundConnection;
  }

  /**
   * Gives {@code connection} to the pool. The pool may store the connection,
   * or close it, as its policy describes.
   *
   * <p>It is an error to use {@code connection} after calling this method.
   */
  void recycle(Connection connection) {
    if (connection.isSpdy()) {
      return;
    }

    if (!connection.clearOwner()) {
      return; // This connection isn't eligible for reuse.
    }

    if (!connection.isAlive()) {
      Util.closeQuietly(connection.getSocket());
      return;
    }

    try {
      Platform.get().untagSocket(connection.getSocket());
    } catch (SocketException e) {
      // When unable to remove tagging, skip recycling and close.
      Platform.get().logW("Unable to untagSocket(): " + e);
      Util.closeQuietly(connection.getSocket());
      return;
    }

    synchronized (this) {
      addConnection(connection);
      connection.incrementRecycleCount();
      connection.resetIdleStartTime();
    }
  }

  private void addConnection(Connection connection) {
    boolean empty = connections.isEmpty();
    connections.addFirst(connection);
    if (empty) {
      executor.execute(connectionsCleanupRunnable);
    } else {
      notifyAll();
    }
  }

  /**
   * Shares the SPDY connection with the pool. Callers to this method may
   * continue to use {@code connection}.
   */
  void share(Connection connection) {
    if (!connection.isSpdy()) throw new IllegalArgumentException();
    if (!connection.isAlive()) return;
    synchronized (this) {
      addConnection(connection);
    }
  }

  /** Close and remove all connections in the pool. */
  public void evictAll() {
    List<Connection> toEvict;
    synchronized (this) {
      toEvict = new ArrayList<>(connections);
      connections.clear();
      notifyAll();
    }

    for (int i = 0, size = toEvict.size(); i < size; i++) {
      Util.closeQuietly(toEvict.get(i).getSocket());
    }
  }

  private void runCleanupUntilPoolIsEmpty() {
    while (true) {
      if (!performCleanup()) return; // Halt cleanup.
    }
  }

  /**
   * Attempts to make forward progress on connection eviction. There are three possible outcomes:
   *
   * <h3>The pool is empty.</h3>
   * In this case, this method returns false and the eviction job should exit because there are no
   * further cleanup tasks coming. (If additional connections are added to the pool, another cleanup
   * job must be enqueued.)
   *
   * <h3>Connections were evicted.</h3>
   * At least one connections was eligible for immediate eviction and was evicted. The method
   * returns true and cleanup should continue.
   *
   * <h3>We waited to evict.</h3>
   * None of the pooled connections were eligible for immediate eviction. Instead, we waited until
   * either a connection became eligible for eviction, or the connections list changed. In either
   * case, the method returns true and cleanup should continue.
   */
  // VisibleForTesting
  boolean performCleanup() {
    List<Connection> evictableConnections;

    synchronized (this) {
      if (connections.isEmpty()) return false; // Halt cleanup.

      evictableConnections = new ArrayList<>();
      int idleConnectionCount = 0;
      long now = System.nanoTime();
      long nanosUntilNextEviction = keepAliveDurationNs;

      // Collect connections eligible for immediate eviction.
      for (ListIterator<Connection> i = connections.listIterator(connections.size());
          i.hasPrevious(); ) {
        Connection connection = i.previous();
        long nanosUntilEviction = connection.getIdleStartTimeNs() + keepAliveDurationNs - now;
        if (nanosUntilEviction <= 0 || !connection.isAlive()) {
          i.remove();
          evictableConnections.add(connection);
        } else if (connection.isIdle()) {
          idleConnectionCount++;
          nanosUntilNextEviction = Math.min(nanosUntilNextEviction, nanosUntilEviction);
        }
      }

      // If the pool has too many idle connections, gather more! Oldest to newest.
      for (ListIterator<Connection> i = connections.listIterator(connections.size());
          i.hasPrevious() && idleConnectionCount > maxIdleConnections; ) {
        Connection connection = i.previous();
        if (connection.isIdle()) {
          evictableConnections.add(connection);
          i.remove();
          --idleConnectionCount;
        }
      }

      // If there's nothing to evict, wait. (This will be interrupted if connections are added.)
      if (evictableConnections.isEmpty()) {
        try {
          long millisUntilNextEviction = nanosUntilNextEviction / (1000 * 1000);
          long remainderNanos = nanosUntilNextEviction - millisUntilNextEviction * (1000 * 1000);
          this.wait(millisUntilNextEviction, (int) remainderNanos);
          return true; // Cleanup continues.
        } catch (InterruptedException ignored) {
        }
      }
    }

    // Actually do the eviction. Note that we avoid synchronized() when closing sockets.
    for (int i = 0, size = evictableConnections.size(); i < size; i++) {
      Connection expiredConnection = evictableConnections.get(i);
      Util.closeQuietly(expiredConnection.getSocket());
    }

    return true; // Cleanup continues.
  }

  /**
   * Replace the default {@link Executor} with a different one. Only use in tests.
   */
  // VisibleForTesting
  void replaceCleanupExecutorForTests(Executor cleanupExecutor) {
    this.executor = cleanupExecutor;
  }

  /**
   * Returns a snapshot of the connections in this pool, ordered from newest to
   * oldest. Only use in tests.
   */
  // VisibleForTesting
  synchronized List<Connection> getConnections() {
    return new ArrayList<>(connections);
  }
}
