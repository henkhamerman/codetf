Refactoring Types: ['Extract Method']
rc/com/squareup/okhttp/Address.java
/*
 * Copyright (C) 2012 The Android Open Source Project
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
package com.squareup.okhttp;

import com.squareup.okhttp.internal.Util;
import java.net.Proxy;
import java.net.UnknownHostException;
import java.util.List;
import javax.net.ssl.HostnameVerifier;
import javax.net.ssl.SSLSocketFactory;

import static com.squareup.okhttp.internal.Util.equal;

/**
 * A specification for a connection to an origin server. For simple connections,
 * this is the server's hostname and port. If an explicit proxy is requested (or
 * {@link Proxy#NO_PROXY no proxy} is explicitly requested), this also includes
 * that proxy information. For secure connections the address also includes the
 * SSL socket factory and hostname verifier.
 *
 * <p>HTTP requests that share the same {@code Address} may also share the same
 * {@link Connection}.
 */
public final class Address {
  final Proxy proxy;
  final String uriHost;
  final int uriPort;
  final SSLSocketFactory sslSocketFactory;
  final HostnameVerifier hostnameVerifier;
  final OkAuthenticator authenticator;
  final List<String> transports;

  public Address(String uriHost, int uriPort, SSLSocketFactory sslSocketFactory,
      HostnameVerifier hostnameVerifier, OkAuthenticator authenticator, Proxy proxy,
      List<String> transports) throws UnknownHostException {
    if (uriHost == null) throw new NullPointerException("uriHost == null");
    if (uriPort <= 0) throw new IllegalArgumentException("uriPort <= 0: " + uriPort);
    if (authenticator == null) throw new IllegalArgumentException("authenticator == null");
    if (transports == null) throw new IllegalArgumentException("transports == null");
    this.proxy = proxy;
    this.uriHost = uriHost;
    this.uriPort = uriPort;
    this.sslSocketFactory = sslSocketFactory;
    this.hostnameVerifier = hostnameVerifier;
    this.authenticator = authenticator;
    this.transports = Util.immutableList(transports);
  }

  /** Returns the hostname of the origin server. */
  public String getUriHost() {
    return uriHost;
  }

  /**
   * Returns the port of the origin server; typically 80 or 443. Unlike
   * may {@code getPort()} accessors, this method never returns -1.
   */
  public int getUriPort() {
    return uriPort;
  }

  /**
   * Returns the SSL socket factory, or null if this is not an HTTPS
   * address.
   */
  public SSLSocketFactory getSslSocketFactory() {
    return sslSocketFactory;
  }

  /**
   * Returns the hostname verifier, or null if this is not an HTTPS
   * address.
   */
  public HostnameVerifier getHostnameVerifier() {
    return hostnameVerifier;
  }


  /**
   * Returns the client's authenticator. This method never returns null.
   */
  public OkAuthenticator getAuthenticator() {
    return authenticator;
  }

  /**
   * Returns the client's transports. This method always returns a non-null list
   * that contains "http/1.1", possibly among other transports.
   */
  public List<String> getTransports() {
    return transports;
  }

  /**
   * Returns this address's explicitly-specified HTTP proxy, or null to
   * delegate to the HTTP client's proxy selector.
   */
  public Proxy getProxy() {
    return proxy;
  }

  @Override public boolean equals(Object other) {
    if (other instanceof Address) {
      Address that = (Address) other;
      return equal(this.proxy, that.proxy)
          && this.uriHost.equals(that.uriHost)
          && this.uriPort == that.uriPort
          && equal(this.sslSocketFactory, that.sslSocketFactory)
          && equal(this.hostnameVerifier, that.hostnameVerifier)
          && equal(this.authenticator, that.authenticator)
          && equal(this.transports, that.transports);
    }
    return false;
  }

  @Override public int hashCode() {
    int result = 17;
    result = 31 * result + uriHost.hashCode();
    result = 31 * result + uriPort;
    result = 31 * result + (sslSocketFactory != null ? sslSocketFactory.hashCode() : 0);
    result = 31 * result + (hostnameVerifier != null ? hostnameVerifier.hashCode() : 0);
    result = 31 * result + (authenticator != null ? authenticator.hashCode() : 0);
    result = 31 * result + (proxy != null ? proxy.hashCode() : 0);
    result = 31 * result + transports.hashCode();
    return result;
  }
}


File: platforms/android/CordovaLib/src/com/squareup/okhttp/Connection.java
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
import com.squareup.okhttp.internal.http.HttpAuthenticator;
import com.squareup.okhttp.internal.http.HttpEngine;
import com.squareup.okhttp.internal.http.HttpTransport;
import com.squareup.okhttp.internal.http.RawHeaders;
import com.squareup.okhttp.internal.http.SpdyTransport;
import com.squareup.okhttp.internal.spdy.SpdyConnection;
import java.io.BufferedInputStream;
import java.io.BufferedOutputStream;
import java.io.Closeable;
import java.io.IOException;
import java.io.InputStream;
import java.io.OutputStream;
import java.net.Proxy;
import java.net.Socket;
import java.net.SocketTimeoutException;
import java.net.URL;
import java.util.Arrays;
import javax.net.ssl.SSLSocket;

import static java.net.HttpURLConnection.HTTP_OK;
import static java.net.HttpURLConnection.HTTP_PROXY_AUTH;

/**
 * Holds the sockets and streams of an HTTP, HTTPS, or HTTPS+SPDY connection,
 * which may be used for multiple HTTP request/response exchanges. Connections
 * may be direct to the origin server or via a proxy.
 *
 * <p>Typically instances of this class are created, connected and exercised
 * automatically by the HTTP client. Applications may use this class to monitor
 * HTTP connections as members of a {@link ConnectionPool connection pool}.
 *
 * <p>Do not confuse this class with the misnamed {@code HttpURLConnection},
 * which isn't so much a connection as a single request/response exchange.
 *
 * <h3>Modern TLS</h3>
 * There are tradeoffs when selecting which options to include when negotiating
 * a secure connection to a remote host. Newer TLS options are quite useful:
 * <ul>
 * <li>Server Name Indication (SNI) enables one IP address to negotiate secure
 * connections for multiple domain names.
 * <li>Next Protocol Negotiation (NPN) enables the HTTPS port (443) to be used
 * for both HTTP and SPDY transports.
 * </ul>
 * Unfortunately, older HTTPS servers refuse to connect when such options are
 * presented. Rather than avoiding these options entirely, this class allows a
 * connection to be attempted with modern options and then retried without them
 * should the attempt fail.
 */
public final class Connection implements Closeable {
  private static final byte[] NPN_PROTOCOLS = new byte[] {
      6, 's', 'p', 'd', 'y', '/', '3',
      8, 'h', 't', 't', 'p', '/', '1', '.', '1'
  };
  private static final byte[] SPDY3 = new byte[] {
      's', 'p', 'd', 'y', '/', '3'
  };
  private static final byte[] HTTP_11 = new byte[] {
      'h', 't', 't', 'p', '/', '1', '.', '1'
  };

  private final Route route;

  private Socket socket;
  private InputStream in;
  private OutputStream out;
  private boolean connected = false;
  private SpdyConnection spdyConnection;
  private int httpMinorVersion = 1; // Assume HTTP/1.1
  private long idleStartTimeNs;

  public Connection(Route route) {
    this.route = route;
  }

  public void connect(int connectTimeout, int readTimeout, TunnelRequest tunnelRequest)
      throws IOException {
    if (connected) throw new IllegalStateException("already connected");

    socket = (route.proxy.type() != Proxy.Type.HTTP) ? new Socket(route.proxy) : new Socket();
    Platform.get().connectSocket(socket, route.inetSocketAddress, connectTimeout);
    socket.setSoTimeout(readTimeout);
    in = socket.getInputStream();
    out = socket.getOutputStream();

    if (route.address.sslSocketFactory != null) {
      upgradeToTls(tunnelRequest);
    } else {
      streamWrapper();
    }
    connected = true;
  }

  /**
   * Create an {@code SSLSocket} and perform the TLS handshake and certificate
   * validation.
   */
  private void upgradeToTls(TunnelRequest tunnelRequest) throws IOException {
    Platform platform = Platform.get();

    // Make an SSL Tunnel on the first message pair of each SSL + proxy connection.
    if (requiresTunnel()) {
      makeTunnel(tunnelRequest);
    }

    // Create the wrapper over connected socket.
    socket = route.address.sslSocketFactory
        .createSocket(socket, route.address.uriHost, route.address.uriPort, true /* autoClose */);
    SSLSocket sslSocket = (SSLSocket) socket;
    if (route.modernTls) {
      platform.enableTlsExtensions(sslSocket, route.address.uriHost);
    } else {
      platform.supportTlsIntolerantServer(sslSocket);
    }

    boolean useNpn = route.modernTls && route.address.transports.contains("spdy/3");
    if (useNpn) {
      platform.setNpnProtocols(sslSocket, NPN_PROTOCOLS);
    }

    // Force handshake. This can throw!
    sslSocket.startHandshake();

    // Verify that the socket's certificates are acceptable for the target host.
    if (!route.address.hostnameVerifier.verify(route.address.uriHost, sslSocket.getSession())) {
      throw new IOException("Hostname '" + route.address.uriHost + "' was not verified");
    }

    out = sslSocket.getOutputStream();
    in = sslSocket.getInputStream();
    streamWrapper();

    byte[] selectedProtocol;
    if (useNpn && (selectedProtocol = platform.getNpnSelectedProtocol(sslSocket)) != null) {
      if (Arrays.equals(selectedProtocol, SPDY3)) {
        sslSocket.setSoTimeout(0); // SPDY timeouts are set per-stream.
        spdyConnection = new SpdyConnection.Builder(route.address.getUriHost(), true, in, out)
            .build();
        spdyConnection.sendConnectionHeader();
      } else if (!Arrays.equals(selectedProtocol, HTTP_11)) {
        throw new IOException(
            "Unexpected NPN transport " + new String(selectedProtocol, "ISO-8859-1"));
      }
    }
  }

  /** Returns true if {@link #connect} has been attempted on this connection. */
  public boolean isConnected() {
    return connected;
  }

  @Override public void close() throws IOException {
    socket.close();
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

  /** Returns true if this connection is alive. */
  public boolean isAlive() {
    return !socket.isClosed() && !socket.isInputShutdown() && !socket.isOutputShutdown();
  }

  /**
   * Returns true if we are confident that we can read data from this
   * connection. This is more expensive and more accurate than {@link
   * #isAlive()}; callers should check {@link #isAlive()} first.
   */
  public boolean isReadable() {
    if (!(in instanceof BufferedInputStream)) {
      return true; // Optimistic.
    }
    if (isSpdy()) {
      return true; // Optimistic. We can't test SPDY because its streams are in use.
    }
    BufferedInputStream bufferedInputStream = (BufferedInputStream) in;
    try {
      int readTimeout = socket.getSoTimeout();
      try {
        socket.setSoTimeout(1);
        bufferedInputStream.mark(1);
        if (bufferedInputStream.read() == -1) {
          return false; // Stream is exhausted; socket is closed.
        }
        bufferedInputStream.reset();
        return true;
      } finally {
        socket.setSoTimeout(readTimeout);
      }
    } catch (SocketTimeoutException ignored) {
      return true; // Read timed out; socket is good.
    } catch (IOException e) {
      return false; // Couldn't read; socket is closed.
    }
  }

  public void resetIdleStartTime() {
    if (spdyConnection != null) {
      throw new IllegalStateException("spdyConnection != null");
    }
    this.idleStartTimeNs = System.nanoTime();
  }

  /** Returns true if this connection is idle. */
  public boolean isIdle() {
    return spdyConnection == null || spdyConnection.isIdle();
  }

  /**
   * Returns true if this connection has been idle for longer than
   * {@code keepAliveDurationNs}.
   */
  public boolean isExpired(long keepAliveDurationNs) {
    return getIdleStartTimeNs() < System.nanoTime() - keepAliveDurationNs;
  }

  /**
   * Returns the time in ns when this connection became idle. Undefined if
   * this connection is not idle.
   */
  public long getIdleStartTimeNs() {
    return spdyConnection == null ? idleStartTimeNs : spdyConnection.getIdleStartTimeNs();
  }

  /** Returns the transport appropriate for this connection. */
  public Object newTransport(HttpEngine httpEngine) throws IOException {
    return (spdyConnection != null)
        ? new SpdyTransport(httpEngine, spdyConnection)
        : new HttpTransport(httpEngine, out, in);
  }

  /**
   * Returns true if this is a SPDY connection. Such connections can be used
   * in multiple HTTP requests simultaneously.
   */
  public boolean isSpdy() {
    return spdyConnection != null;
  }

  public SpdyConnection getSpdyConnection() {
    return spdyConnection;
  }

  /**
   * Returns the minor HTTP version that should be used for future requests on
   * this connection. Either 0 for HTTP/1.0, or 1 for HTTP/1.1. The default
   * value is 1 for new connections.
   */
  public int getHttpMinorVersion() {
    return httpMinorVersion;
  }

  public void setHttpMinorVersion(int httpMinorVersion) {
    this.httpMinorVersion = httpMinorVersion;
  }

  /**
   * Returns true if the HTTP connection needs to tunnel one protocol over
   * another, such as when using HTTPS through an HTTP proxy. When doing so,
   * we must avoid buffering bytes intended for the higher-level protocol.
   */
  public boolean requiresTunnel() {
    return route.address.sslSocketFactory != null && route.proxy.type() == Proxy.Type.HTTP;
  }

  public void updateReadTimeout(int newTimeout) throws IOException {
    if (!connected) throw new IllegalStateException("updateReadTimeout - not connected");
    socket.setSoTimeout(newTimeout);
  }

  /**
   * To make an HTTPS connection over an HTTP proxy, send an unencrypted
   * CONNECT request to create the proxy connection. This may need to be
   * retried if the proxy requires authorization.
   */
  private void makeTunnel(TunnelRequest tunnelRequest) throws IOException {
    RawHeaders requestHeaders = tunnelRequest.getRequestHeaders();
    while (true) {
      out.write(requestHeaders.toBytes());
      RawHeaders responseHeaders = RawHeaders.fromBytes(in);

      switch (responseHeaders.getResponseCode()) {
        case HTTP_OK:
          return;
        case HTTP_PROXY_AUTH:
          requestHeaders = new RawHeaders(requestHeaders);
          URL url = new URL("https", tunnelRequest.host, tunnelRequest.port, "/");
          boolean credentialsFound = HttpAuthenticator.processAuthHeader(
              route.address.authenticator, HTTP_PROXY_AUTH, responseHeaders, requestHeaders,
              route.proxy, url);
          if (credentialsFound) {
            continue;
          } else {
            throw new IOException("Failed to authenticate with proxy");
          }
        default:
          throw new IOException(
              "Unexpected response code for CONNECT: " + responseHeaders.getResponseCode());
      }
    }
  }

  private void streamWrapper() throws IOException {
    in = new BufferedInputStream(in, 4096);
    out = new BufferedOutputStream(out, 256);
  }
}


File: platforms/android/CordovaLib/src/com/squareup/okhttp/ConnectionPool.java
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
import java.util.concurrent.Callable;
import java.util.concurrent.ExecutorService;
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
public class ConnectionPool {
  private static final int MAX_CONNECTIONS_TO_CLEANUP = 2;
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

  private final LinkedList<Connection> connections = new LinkedList<Connection>();

  /** We use a single background thread to cleanup expired connections. */
  private final ExecutorService executorService = new ThreadPoolExecutor(0, 1,
      60L, TimeUnit.SECONDS, new LinkedBlockingQueue<Runnable>(),
      Util.daemonThreadFactory("OkHttp ConnectionPool"));
  private final Callable<Void> connectionsCleanupCallable = new Callable<Void>() {
    @Override public Void call() throws Exception {
      List<Connection> expiredConnections = new ArrayList<Connection>(MAX_CONNECTIONS_TO_CLEANUP);
      int idleConnectionCount = 0;
      synchronized (ConnectionPool.this) {
        for (ListIterator<Connection> i = connections.listIterator(connections.size());
            i.hasPrevious(); ) {
          Connection connection = i.previous();
          if (!connection.isAlive() || connection.isExpired(keepAliveDurationNs)) {
            i.remove();
            expiredConnections.add(connection);
            if (expiredConnections.size() == MAX_CONNECTIONS_TO_CLEANUP) break;
          } else if (connection.isIdle()) {
            idleConnectionCount++;
          }
        }

        for (ListIterator<Connection> i = connections.listIterator(connections.size());
            i.hasPrevious() && idleConnectionCount > maxIdleConnections; ) {
          Connection connection = i.previous();
          if (connection.isIdle()) {
            expiredConnections.add(connection);
            i.remove();
            --idleConnectionCount;
          }
        }
      }
      for (Connection expiredConnection : expiredConnections) {
        Util.closeQuietly(expiredConnection);
      }
      return null;
    }
  };

  public ConnectionPool(int maxIdleConnections, long keepAliveDurationMs) {
    this.maxIdleConnections = maxIdleConnections;
    this.keepAliveDurationNs = keepAliveDurationMs * 1000 * 1000;
  }

  /**
   * Returns a snapshot of the connections in this pool, ordered from newest to
   * oldest. Waits for the cleanup callable to run if it is currently scheduled.
   */
  List<Connection> getConnections() {
    waitForCleanupCallableToRun();
    synchronized (this) {
      return new ArrayList<Connection>(connections);
    }
  }

  /**
   * Blocks until the executor service has processed all currently enqueued
   * jobs.
   */
  private void waitForCleanupCallableToRun() {
    try {
      executorService.submit(new Runnable() {
        @Override public void run() {
        }
      }).get();
    } catch (Exception e) {
      throw new AssertionError();
    }
  }

  public static ConnectionPool getDefault() {
    return systemDefault;
  }

  /** Returns total number of connections in the pool. */
  public synchronized int getConnectionCount() {
    return connections.size();
  }

  /** Returns total number of spdy connections in the pool. */
  public synchronized int getSpdyConnectionCount() {
    int total = 0;
    for (Connection connection : connections) {
      if (connection.isSpdy()) total++;
    }
    return total;
  }

  /** Returns total number of http connections in the pool. */
  public synchronized int getHttpConnectionCount() {
    int total = 0;
    for (Connection connection : connections) {
      if (!connection.isSpdy()) total++;
    }
    return total;
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
          Util.closeQuietly(connection);
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

    executorService.submit(connectionsCleanupCallable);
    return foundConnection;
  }

  /**
   * Gives {@code connection} to the pool. The pool may store the connection,
   * or close it, as its policy describes.
   *
   * <p>It is an error to use {@code connection} after calling this method.
   */
  public void recycle(Connection connection) {
    if (connection.isSpdy()) {
      return;
    }

    if (!connection.isAlive()) {
      Util.closeQuietly(connection);
      return;
    }

    try {
      Platform.get().untagSocket(connection.getSocket());
    } catch (SocketException e) {
      // When unable to remove tagging, skip recycling and close.
      Platform.get().logW("Unable to untagSocket(): " + e);
      Util.closeQuietly(connection);
      return;
    }

    synchronized (this) {
      connections.addFirst(connection);
      connection.resetIdleStartTime();
    }

    executorService.submit(connectionsCleanupCallable);
  }

  /**
   * Shares the SPDY connection with the pool. Callers to this method may
   * continue to use {@code connection}.
   */
  public void maybeShare(Connection connection) {
    executorService.submit(connectionsCleanupCallable);
    if (!connection.isSpdy()) {
      // Only SPDY connections are sharable.
      return;
    }
    if (connection.isAlive()) {
      synchronized (this) {
        connections.addFirst(connection);
      }
    }
  }

  /** Close and remove all connections in the pool. */
  public void evictAll() {
    List<Connection> connections;
    synchronized (this) {
      connections = new ArrayList<Connection>(this.connections);
      this.connections.clear();
    }

    for (Connection connection : connections) {
      Util.closeQuietly(connection);
    }
  }
}


File: platforms/android/CordovaLib/src/com/squareup/okhttp/Dispatcher.java
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
package com.squareup.okhttp;

import com.squareup.okhttp.internal.http.ResponseHeaders;
import java.io.IOException;
import java.io.InputStream;
import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.concurrent.LinkedBlockingQueue;
import java.util.concurrent.ThreadPoolExecutor;
import java.util.concurrent.TimeUnit;

final class Dispatcher {
  // TODO: thread pool size should be configurable; possibly configurable per host.
  private final ThreadPoolExecutor executorService = new ThreadPoolExecutor(
      8, 8, 60, TimeUnit.SECONDS, new LinkedBlockingQueue<Runnable>());
  private final Map<Object, List<Job>> enqueuedJobs = new LinkedHashMap<Object, List<Job>>();

  public synchronized void enqueue(
      OkHttpClient client, Request request, Response.Receiver responseReceiver) {
    Job job = new Job(this, client, request, responseReceiver);
    List<Job> jobsForTag = enqueuedJobs.get(request.tag());
    if (jobsForTag == null) {
      jobsForTag = new ArrayList<Job>(2);
      enqueuedJobs.put(request.tag(), jobsForTag);
    }
    jobsForTag.add(job);
    executorService.execute(job);
  }

  public synchronized void cancel(Object tag) {
    List<Job> jobs = enqueuedJobs.remove(tag);
    if (jobs == null) return;
    for (Job job : jobs) {
      executorService.remove(job);
    }
  }

  synchronized void finished(Job job) {
    List<Job> jobs = enqueuedJobs.get(job.tag());
    if (jobs != null) jobs.remove(job);
  }

  static class RealResponseBody extends Response.Body {
    private final ResponseHeaders responseHeaders;
    private final InputStream in;

    RealResponseBody(ResponseHeaders responseHeaders, InputStream in) {
      this.responseHeaders = responseHeaders;
      this.in = in;
    }

    @Override public boolean ready() throws IOException {
      return true;
    }

    @Override public MediaType contentType() {
      String contentType = responseHeaders.getContentType();
      return contentType != null ? MediaType.parse(contentType) : null;
    }

    @Override public long contentLength() {
      return responseHeaders.getContentLength();
    }

    @Override public InputStream byteStream() throws IOException {
      return in;
    }
  }
}


File: platforms/android/CordovaLib/src/com/squareup/okhttp/Failure.java
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
package com.squareup.okhttp;

/**
 * A failure attempting to retrieve an HTTP response.
 *
 * <h3>Warning: Experimental OkHttp 2.0 API</h3>
 * This class is in beta. APIs are subject to change!
 */
/* OkHttp 2.0: public */ class Failure {
  private final Request request;
  private final Throwable exception;

  private Failure(Builder builder) {
    this.request = builder.request;
    this.exception = builder.exception;
  }

  public Request request() {
    return request;
  }

  public Throwable exception() {
    return exception;
  }

  public static class Builder {
    private Request request;
    private Throwable exception;

    public Builder request(Request request) {
      this.request = request;
      return this;
    }

    public Builder exception(Throwable exception) {
      this.exception = exception;
      return this;
    }

    public Failure build() {
      return new Failure(this);
    }
  }
}


File: platforms/android/CordovaLib/src/com/squareup/okhttp/HttpResponseCache.java
/*
 * Copyright (C) 2010 The Android Open Source Project
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

package com.squareup.okhttp;

import com.squareup.okhttp.internal.Base64;
import com.squareup.okhttp.internal.DiskLruCache;
import com.squareup.okhttp.internal.StrictLineReader;
import com.squareup.okhttp.internal.Util;
import com.squareup.okhttp.internal.http.HttpEngine;
import com.squareup.okhttp.internal.http.HttpURLConnectionImpl;
import com.squareup.okhttp.internal.http.HttpsEngine;
import com.squareup.okhttp.internal.http.HttpsURLConnectionImpl;
import com.squareup.okhttp.internal.http.RawHeaders;
import com.squareup.okhttp.internal.http.ResponseHeaders;
import java.io.BufferedWriter;
import java.io.ByteArrayInputStream;
import java.io.File;
import java.io.FilterInputStream;
import java.io.FilterOutputStream;
import java.io.IOException;
import java.io.InputStream;
import java.io.OutputStream;
import java.io.OutputStreamWriter;
import java.io.Writer;
import java.net.CacheRequest;
import java.net.CacheResponse;
import java.net.HttpURLConnection;
import java.net.ResponseCache;
import java.net.SecureCacheResponse;
import java.net.URI;
import java.net.URLConnection;
import java.security.Principal;
import java.security.cert.Certificate;
import java.security.cert.CertificateEncodingException;
import java.security.cert.CertificateException;
import java.security.cert.CertificateFactory;
import java.security.cert.X509Certificate;
import java.util.Arrays;
import java.util.List;
import java.util.Map;
import javax.net.ssl.SSLPeerUnverifiedException;
import javax.net.ssl.SSLSocket;

import static com.squareup.okhttp.internal.Util.US_ASCII;
import static com.squareup.okhttp.internal.Util.UTF_8;

/**
 * Caches HTTP and HTTPS responses to the filesystem so they may be reused,
 * saving time and bandwidth.
 *
 * <h3>Cache Optimization</h3>
 * To measure cache effectiveness, this class tracks three statistics:
 * <ul>
 *     <li><strong>{@link #getRequestCount() Request Count:}</strong> the number
 *         of HTTP requests issued since this cache was created.
 *     <li><strong>{@link #getNetworkCount() Network Count:}</strong> the
 *         number of those requests that required network use.
 *     <li><strong>{@link #getHitCount() Hit Count:}</strong> the number of
 *         those requests whose responses were served by the cache.
 * </ul>
 * Sometimes a request will result in a conditional cache hit. If the cache
 * contains a stale copy of the response, the client will issue a conditional
 * {@code GET}. The server will then send either the updated response if it has
 * changed, or a short 'not modified' response if the client's copy is still
 * valid. Such responses increment both the network count and hit count.
 *
 * <p>The best way to improve the cache hit rate is by configuring the web
 * server to return cacheable responses. Although this client honors all <a
 * href="http://www.ietf.org/rfc/rfc2616.txt">HTTP/1.1 (RFC 2068)</a> cache
 * headers, it doesn't cache partial responses.
 *
 * <h3>Force a Network Response</h3>
 * In some situations, such as after a user clicks a 'refresh' button, it may be
 * necessary to skip the cache, and fetch data directly from the server. To force
 * a full refresh, add the {@code no-cache} directive: <pre>   {@code
 *         connection.addRequestProperty("Cache-Control", "no-cache");
 * }</pre>
 * If it is only necessary to force a cached response to be validated by the
 * server, use the more efficient {@code max-age=0} instead: <pre>   {@code
 *         connection.addRequestProperty("Cache-Control", "max-age=0");
 * }</pre>
 *
 * <h3>Force a Cache Response</h3>
 * Sometimes you'll want to show resources if they are available immediately,
 * but not otherwise. This can be used so your application can show
 * <i>something</i> while waiting for the latest data to be downloaded. To
 * restrict a request to locally-cached resources, add the {@code
 * only-if-cached} directive: <pre>   {@code
 *     try {
 *         connection.addRequestProperty("Cache-Control", "only-if-cached");
 *         InputStream cached = connection.getInputStream();
 *         // the resource was cached! show it
 *     } catch (FileNotFoundException e) {
 *         // the resource was not cached
 *     }
 * }</pre>
 * This technique works even better in situations where a stale response is
 * better than no response. To permit stale cached responses, use the {@code
 * max-stale} directive with the maximum staleness in seconds: <pre>   {@code
 *         int maxStale = 60 * 60 * 24 * 28; // tolerate 4-weeks stale
 *         connection.addRequestProperty("Cache-Control", "max-stale=" + maxStale);
 * }</pre>
 */
public final class HttpResponseCache extends ResponseCache {
  // TODO: add APIs to iterate the cache?
  private static final int VERSION = 201105;
  private static final int ENTRY_METADATA = 0;
  private static final int ENTRY_BODY = 1;
  private static final int ENTRY_COUNT = 2;

  private final DiskLruCache cache;

  /* read and write statistics, all guarded by 'this' */
  private int writeSuccessCount;
  private int writeAbortCount;
  private int networkCount;
  private int hitCount;
  private int requestCount;

  /**
   * Although this class only exposes the limited ResponseCache API, it
   * implements the full OkResponseCache interface. This field is used as a
   * package private handle to the complete implementation. It delegates to
   * public and private members of this type.
   */
  final OkResponseCache okResponseCache = new OkResponseCache() {
    @Override public CacheResponse get(URI uri, String requestMethod,
        Map<String, List<String>> requestHeaders) throws IOException {
      return HttpResponseCache.this.get(uri, requestMethod, requestHeaders);
    }

    @Override public CacheRequest put(URI uri, URLConnection connection) throws IOException {
      return HttpResponseCache.this.put(uri, connection);
    }

    @Override public void maybeRemove(String requestMethod, URI uri) throws IOException {
      HttpResponseCache.this.maybeRemove(requestMethod, uri);
    }

    @Override public void update(
        CacheResponse conditionalCacheHit, HttpURLConnection connection) throws IOException {
      HttpResponseCache.this.update(conditionalCacheHit, connection);
    }

    @Override public void trackConditionalCacheHit() {
      HttpResponseCache.this.trackConditionalCacheHit();
    }

    @Override public void trackResponse(ResponseSource source) {
      HttpResponseCache.this.trackResponse(source);
    }
  };

  public HttpResponseCache(File directory, long maxSize) throws IOException {
    cache = DiskLruCache.open(directory, VERSION, ENTRY_COUNT, maxSize);
  }

  private String uriToKey(URI uri) {
    return Util.hash(uri.toString());
  }

  @Override public CacheResponse get(URI uri, String requestMethod,
      Map<String, List<String>> requestHeaders) {
    String key = uriToKey(uri);
    DiskLruCache.Snapshot snapshot;
    Entry entry;
    try {
      snapshot = cache.get(key);
      if (snapshot == null) {
        return null;
      }
      entry = new Entry(snapshot.getInputStream(ENTRY_METADATA));
    } catch (IOException e) {
      // Give up because the cache cannot be read.
      return null;
    }

    if (!entry.matches(uri, requestMethod, requestHeaders)) {
      snapshot.close();
      return null;
    }

    return entry.isHttps() ? new EntrySecureCacheResponse(entry, snapshot)
        : new EntryCacheResponse(entry, snapshot);
  }

  @Override public CacheRequest put(URI uri, URLConnection urlConnection) throws IOException {
    if (!(urlConnection instanceof HttpURLConnection)) {
      return null;
    }

    HttpURLConnection httpConnection = (HttpURLConnection) urlConnection;
    String requestMethod = httpConnection.getRequestMethod();

    if (maybeRemove(requestMethod, uri)) {
      return null;
    }
    if (!requestMethod.equals("GET")) {
      // Don't cache non-GET responses. We're technically allowed to cache
      // HEAD requests and some POST requests, but the complexity of doing
      // so is high and the benefit is low.
      return null;
    }

    HttpEngine httpEngine = getHttpEngine(httpConnection);
    if (httpEngine == null) {
      // Don't cache unless the HTTP implementation is ours.
      return null;
    }

    ResponseHeaders response = httpEngine.getResponseHeaders();
    if (response.hasVaryAll()) {
      return null;
    }

    RawHeaders varyHeaders =
        httpEngine.getRequestHeaders().getHeaders().getAll(response.getVaryFields());
    Entry entry = new Entry(uri, varyHeaders, httpConnection);
    DiskLruCache.Editor editor = null;
    try {
      editor = cache.edit(uriToKey(uri));
      if (editor == null) {
        return null;
      }
      entry.writeTo(editor);
      return new CacheRequestImpl(editor);
    } catch (IOException e) {
      abortQuietly(editor);
      return null;
    }
  }

  /**
   * Returns true if the supplied {@code requestMethod} potentially invalidates an entry in the
   * cache.
   */
  private boolean maybeRemove(String requestMethod, URI uri) {
    if (requestMethod.equals("POST") || requestMethod.equals("PUT") || requestMethod.equals(
        "DELETE")) {
      try {
        cache.remove(uriToKey(uri));
      } catch (IOException ignored) {
        // The cache cannot be written.
      }
      return true;
    }
    return false;
  }

  private void update(CacheResponse conditionalCacheHit, HttpURLConnection httpConnection)
      throws IOException {
    HttpEngine httpEngine = getHttpEngine(httpConnection);
    URI uri = httpEngine.getUri();
    ResponseHeaders response = httpEngine.getResponseHeaders();
    RawHeaders varyHeaders =
        httpEngine.getRequestHeaders().getHeaders().getAll(response.getVaryFields());
    Entry entry = new Entry(uri, varyHeaders, httpConnection);
    DiskLruCache.Snapshot snapshot = (conditionalCacheHit instanceof EntryCacheResponse)
        ? ((EntryCacheResponse) conditionalCacheHit).snapshot
        : ((EntrySecureCacheResponse) conditionalCacheHit).snapshot;
    DiskLruCache.Editor editor = null;
    try {
      editor = snapshot.edit(); // returns null if snapshot is not current
      if (editor != null) {
        entry.writeTo(editor);
        editor.commit();
      }
    } catch (IOException e) {
      abortQuietly(editor);
    }
  }

  private void abortQuietly(DiskLruCache.Editor editor) {
    // Give up because the cache cannot be written.
    try {
      if (editor != null) {
        editor.abort();
      }
    } catch (IOException ignored) {
    }
  }

  private HttpEngine getHttpEngine(URLConnection httpConnection) {
    if (httpConnection instanceof HttpURLConnectionImpl) {
      return ((HttpURLConnectionImpl) httpConnection).getHttpEngine();
    } else if (httpConnection instanceof HttpsURLConnectionImpl) {
      return ((HttpsURLConnectionImpl) httpConnection).getHttpEngine();
    } else {
      return null;
    }
  }

  /**
   * Closes the cache and deletes all of its stored values. This will delete
   * all files in the cache directory including files that weren't created by
   * the cache.
   */
  public void delete() throws IOException {
    cache.delete();
  }

  public synchronized int getWriteAbortCount() {
    return writeAbortCount;
  }

  public synchronized int getWriteSuccessCount() {
    return writeSuccessCount;
  }

  public long getSize() {
    return cache.size();
  }

  public long getMaxSize() {
    return cache.getMaxSize();
  }

  public void flush() throws IOException {
    cache.flush();
  }

  public void close() throws IOException {
    cache.close();
  }

  public File getDirectory() {
    return cache.getDirectory();
  }

  public boolean isClosed() {
    return cache.isClosed();
  }

  private synchronized void trackResponse(ResponseSource source) {
    requestCount++;

    switch (source) {
      case CACHE:
        hitCount++;
        break;
      case CONDITIONAL_CACHE:
      case NETWORK:
        networkCount++;
        break;
    }
  }

  private synchronized void trackConditionalCacheHit() {
    hitCount++;
  }

  public synchronized int getNetworkCount() {
    return networkCount;
  }

  public synchronized int getHitCount() {
    return hitCount;
  }

  public synchronized int getRequestCount() {
    return requestCount;
  }

  private final class CacheRequestImpl extends CacheRequest {
    private final DiskLruCache.Editor editor;
    private OutputStream cacheOut;
    private boolean done;
    private OutputStream body;

    public CacheRequestImpl(final DiskLruCache.Editor editor) throws IOException {
      this.editor = editor;
      this.cacheOut = editor.newOutputStream(ENTRY_BODY);
      this.body = new FilterOutputStream(cacheOut) {
        @Override public void close() throws IOException {
          synchronized (HttpResponseCache.this) {
            if (done) {
              return;
            }
            done = true;
            writeSuccessCount++;
          }
          super.close();
          editor.commit();
        }

        @Override public void write(byte[] buffer, int offset, int length) throws IOException {
          // Since we don't override "write(int oneByte)", we can write directly to "out"
          // and avoid the inefficient implementation from the FilterOutputStream.
          out.write(buffer, offset, length);
        }
      };
    }

    @Override public void abort() {
      synchronized (HttpResponseCache.this) {
        if (done) {
          return;
        }
        done = true;
        writeAbortCount++;
      }
      Util.closeQuietly(cacheOut);
      try {
        editor.abort();
      } catch (IOException ignored) {
      }
    }

    @Override public OutputStream getBody() throws IOException {
      return body;
    }
  }

  private static final class Entry {
    private final String uri;
    private final RawHeaders varyHeaders;
    private final String requestMethod;
    private final RawHeaders responseHeaders;
    private final String cipherSuite;
    private final Certificate[] peerCertificates;
    private final Certificate[] localCertificates;

    /**
     * Reads an entry from an input stream. A typical entry looks like this:
     * <pre>{@code
     *   http://google.com/foo
     *   GET
     *   2
     *   Accept-Language: fr-CA
     *   Accept-Charset: UTF-8
     *   HTTP/1.1 200 OK
     *   3
     *   Content-Type: image/png
     *   Content-Length: 100
     *   Cache-Control: max-age=600
     * }</pre>
     *
     * <p>A typical HTTPS file looks like this:
     * <pre>{@code
     *   https://google.com/foo
     *   GET
     *   2
     *   Accept-Language: fr-CA
     *   Accept-Charset: UTF-8
     *   HTTP/1.1 200 OK
     *   3
     *   Content-Type: image/png
     *   Content-Length: 100
     *   Cache-Control: max-age=600
     *
     *   AES_256_WITH_MD5
     *   2
     *   base64-encoded peerCertificate[0]
     *   base64-encoded peerCertificate[1]
     *   -1
     * }</pre>
     * The file is newline separated. The first two lines are the URL and
     * the request method. Next is the number of HTTP Vary request header
     * lines, followed by those lines.
     *
     * <p>Next is the response status line, followed by the number of HTTP
     * response header lines, followed by those lines.
     *
     * <p>HTTPS responses also contain SSL session information. This begins
     * with a blank line, and then a line containing the cipher suite. Next
     * is the length of the peer certificate chain. These certificates are
     * base64-encoded and appear each on their own line. The next line
     * contains the length of the local certificate chain. These
     * certificates are also base64-encoded and appear each on their own
     * line. A length of -1 is used to encode a null array.
     */
    public Entry(InputStream in) throws IOException {
      try {
        StrictLineReader reader = new StrictLineReader(in, US_ASCII);
        uri = reader.readLine();
        requestMethod = reader.readLine();
        varyHeaders = new RawHeaders();
        int varyRequestHeaderLineCount = reader.readInt();
        for (int i = 0; i < varyRequestHeaderLineCount; i++) {
          varyHeaders.addLine(reader.readLine());
        }

        responseHeaders = new RawHeaders();
        responseHeaders.setStatusLine(reader.readLine());
        int responseHeaderLineCount = reader.readInt();
        for (int i = 0; i < responseHeaderLineCount; i++) {
          responseHeaders.addLine(reader.readLine());
        }

        if (isHttps()) {
          String blank = reader.readLine();
          if (blank.length() > 0) {
            throw new IOException("expected \"\" but was \"" + blank + "\"");
          }
          cipherSuite = reader.readLine();
          peerCertificates = readCertArray(reader);
          localCertificates = readCertArray(reader);
        } else {
          cipherSuite = null;
          peerCertificates = null;
          localCertificates = null;
        }
      } finally {
        in.close();
      }
    }

    public Entry(URI uri, RawHeaders varyHeaders, HttpURLConnection httpConnection)
        throws IOException {
      this.uri = uri.toString();
      this.varyHeaders = varyHeaders;
      this.requestMethod = httpConnection.getRequestMethod();
      this.responseHeaders = RawHeaders.fromMultimap(httpConnection.getHeaderFields(), true);

      SSLSocket sslSocket = getSslSocket(httpConnection);
      if (sslSocket != null) {
        cipherSuite = sslSocket.getSession().getCipherSuite();
        Certificate[] peerCertificatesNonFinal = null;
        try {
          peerCertificatesNonFinal = sslSocket.getSession().getPeerCertificates();
        } catch (SSLPeerUnverifiedException ignored) {
        }
        peerCertificates = peerCertificatesNonFinal;
        localCertificates = sslSocket.getSession().getLocalCertificates();
      } else {
        cipherSuite = null;
        peerCertificates = null;
        localCertificates = null;
      }
    }

    /**
     * Returns the SSL socket used by {@code httpConnection} for HTTPS, nor null
     * if the connection isn't using HTTPS. Since we permit redirects across
     * protocols (HTTP to HTTPS or vice versa), the implementation type of the
     * connection doesn't necessarily match the implementation type of its HTTP
     * engine.
     */
    private SSLSocket getSslSocket(HttpURLConnection httpConnection) {
      HttpEngine engine = httpConnection instanceof HttpsURLConnectionImpl
          ? ((HttpsURLConnectionImpl) httpConnection).getHttpEngine()
          : ((HttpURLConnectionImpl) httpConnection).getHttpEngine();
      return engine instanceof HttpsEngine
          ? ((HttpsEngine) engine).getSslSocket()
          : null;
    }

    public void writeTo(DiskLruCache.Editor editor) throws IOException {
      OutputStream out = editor.newOutputStream(ENTRY_METADATA);
      Writer writer = new BufferedWriter(new OutputStreamWriter(out, UTF_8));

      writer.write(uri + '\n');
      writer.write(requestMethod + '\n');
      writer.write(Integer.toString(varyHeaders.length()) + '\n');
      for (int i = 0; i < varyHeaders.length(); i++) {
        writer.write(varyHeaders.getFieldName(i) + ": " + varyHeaders.getValue(i) + '\n');
      }

      writer.write(responseHeaders.getStatusLine() + '\n');
      writer.write(Integer.toString(responseHeaders.length()) + '\n');
      for (int i = 0; i < responseHeaders.length(); i++) {
        writer.write(responseHeaders.getFieldName(i) + ": " + responseHeaders.getValue(i) + '\n');
      }

      if (isHttps()) {
        writer.write('\n');
        writer.write(cipherSuite + '\n');
        writeCertArray(writer, peerCertificates);
        writeCertArray(writer, localCertificates);
      }
      writer.close();
    }

    private boolean isHttps() {
      return uri.startsWith("https://");
    }

    private Certificate[] readCertArray(StrictLineReader reader) throws IOException {
      int length = reader.readInt();
      if (length == -1) {
        return null;
      }
      try {
        CertificateFactory certificateFactory = CertificateFactory.getInstance("X.509");
        Certificate[] result = new Certificate[length];
        for (int i = 0; i < result.length; i++) {
          String line = reader.readLine();
          byte[] bytes = Base64.decode(line.getBytes("US-ASCII"));
          result[i] = certificateFactory.generateCertificate(new ByteArrayInputStream(bytes));
        }
        return result;
      } catch (CertificateException e) {
        throw new IOException(e.getMessage());
      }
    }

    private void writeCertArray(Writer writer, Certificate[] certificates) throws IOException {
      if (certificates == null) {
        writer.write("-1\n");
        return;
      }
      try {
        writer.write(Integer.toString(certificates.length) + '\n');
        for (Certificate certificate : certificates) {
          byte[] bytes = certificate.getEncoded();
          String line = Base64.encode(bytes);
          writer.write(line + '\n');
        }
      } catch (CertificateEncodingException e) {
        throw new IOException(e.getMessage());
      }
    }

    public boolean matches(URI uri, String requestMethod,
        Map<String, List<String>> requestHeaders) {
      return this.uri.equals(uri.toString())
          && this.requestMethod.equals(requestMethod)
          && new ResponseHeaders(uri, responseHeaders).varyMatches(varyHeaders.toMultimap(false),
          requestHeaders);
    }
  }

  /**
   * Returns an input stream that reads the body of a snapshot, closing the
   * snapshot when the stream is closed.
   */
  private static InputStream newBodyInputStream(final DiskLruCache.Snapshot snapshot) {
    return new FilterInputStream(snapshot.getInputStream(ENTRY_BODY)) {
      @Override public void close() throws IOException {
        snapshot.close();
        super.close();
      }
    };
  }

  static class EntryCacheResponse extends CacheResponse {
    private final Entry entry;
    private final DiskLruCache.Snapshot snapshot;
    private final InputStream in;

    public EntryCacheResponse(Entry entry, DiskLruCache.Snapshot snapshot) {
      this.entry = entry;
      this.snapshot = snapshot;
      this.in = newBodyInputStream(snapshot);
    }

    @Override public Map<String, List<String>> getHeaders() {
      return entry.responseHeaders.toMultimap(true);
    }

    @Override public InputStream getBody() {
      return in;
    }
  }

  static class EntrySecureCacheResponse extends SecureCacheResponse {
    private final Entry entry;
    private final DiskLruCache.Snapshot snapshot;
    private final InputStream in;

    public EntrySecureCacheResponse(Entry entry, DiskLruCache.Snapshot snapshot) {
      this.entry = entry;
      this.snapshot = snapshot;
      this.in = newBodyInputStream(snapshot);
    }

    @Override public Map<String, List<String>> getHeaders() {
      return entry.responseHeaders.toMultimap(true);
    }

    @Override public InputStream getBody() {
      return in;
    }

    @Override public String getCipherSuite() {
      return entry.cipherSuite;
    }

    @Override public List<Certificate> getServerCertificateChain()
        throws SSLPeerUnverifiedException {
      if (entry.peerCertificates == null || entry.peerCertificates.length == 0) {
        throw new SSLPeerUnverifiedException(null);
      }
      return Arrays.asList(entry.peerCertificates.clone());
    }

    @Override public Principal getPeerPrincipal() throws SSLPeerUnverifiedException {
      if (entry.peerCertificates == null || entry.peerCertificates.length == 0) {
        throw new SSLPeerUnverifiedException(null);
      }
      return ((X509Certificate) entry.peerCertificates[0]).getSubjectX500Principal();
    }

    @Override public List<Certificate> getLocalCertificateChain() {
      if (entry.localCertificates == null || entry.localCertificates.length == 0) {
        return null;
      }
      return Arrays.asList(entry.localCertificates.clone());
    }

    @Override public Principal getLocalPrincipal() {
      if (entry.localCertificates == null || entry.localCertificates.length == 0) {
        return null;
      }
      return ((X509Certificate) entry.localCertificates[0]).getSubjectX500Principal();
    }
  }
}


File: platforms/android/CordovaLib/src/com/squareup/okhttp/Job.java
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
package com.squareup.okhttp;

import com.squareup.okhttp.internal.http.HttpAuthenticator;
import com.squareup.okhttp.internal.http.HttpEngine;
import com.squareup.okhttp.internal.http.HttpTransport;
import com.squareup.okhttp.internal.http.HttpsEngine;
import com.squareup.okhttp.internal.http.Policy;
import com.squareup.okhttp.internal.http.RawHeaders;
import java.io.IOException;
import java.net.HttpURLConnection;
import java.net.ProtocolException;
import java.net.Proxy;
import java.net.URL;

import static com.squareup.okhttp.internal.Util.getEffectivePort;
import static com.squareup.okhttp.internal.http.HttpURLConnectionImpl.HTTP_MOVED_PERM;
import static com.squareup.okhttp.internal.http.HttpURLConnectionImpl.HTTP_MOVED_TEMP;
import static com.squareup.okhttp.internal.http.HttpURLConnectionImpl.HTTP_MULT_CHOICE;
import static com.squareup.okhttp.internal.http.HttpURLConnectionImpl.HTTP_PROXY_AUTH;
import static com.squareup.okhttp.internal.http.HttpURLConnectionImpl.HTTP_SEE_OTHER;
import static com.squareup.okhttp.internal.http.HttpURLConnectionImpl.HTTP_TEMP_REDIRECT;
import static com.squareup.okhttp.internal.http.HttpURLConnectionImpl.HTTP_UNAUTHORIZED;

final class Job implements Runnable, Policy {
  private final Dispatcher dispatcher;
  private final OkHttpClient client;
  private final Response.Receiver responseReceiver;

  /** The request; possibly a consequence of redirects or auth headers. */
  private Request request;

  public Job(Dispatcher dispatcher, OkHttpClient client, Request request,
      Response.Receiver responseReceiver) {
    this.dispatcher = dispatcher;
    this.client = client;
    this.request = request;
    this.responseReceiver = responseReceiver;
  }

  @Override public int getChunkLength() {
    return request.body().contentLength() == -1 ? HttpTransport.DEFAULT_CHUNK_LENGTH : -1;
  }

  @Override public long getFixedContentLength() {
    return request.body().contentLength();
  }

  @Override public boolean getUseCaches() {
    return false; // TODO.
  }

  @Override public HttpURLConnection getHttpConnectionToCache() {
    return null;
  }

  @Override public URL getURL() {
    return request.url();
  }

  @Override public long getIfModifiedSince() {
    return 0; // For HttpURLConnection only. We let the cache drive this.
  }

  @Override public boolean usingProxy() {
    return false; // We let the connection decide this.
  }

  @Override public void setSelectedProxy(Proxy proxy) {
    // Do nothing.
  }

  Object tag() {
    return request.tag();
  }

  @Override public void run() {
    try {
      Response response = execute();
      responseReceiver.onResponse(response);
    } catch (IOException e) {
      responseReceiver.onFailure(new Failure.Builder()
          .request(request)
          .exception(e)
          .build());
    } finally {
      // TODO: close the response body
      // TODO: release the HTTP engine (potentially multiple!)
      dispatcher.finished(this);
    }
  }

  private Response execute() throws IOException {
    Connection connection = null;
    Response redirectedBy = null;

    while (true) {
      HttpEngine engine = newEngine(connection);

      Request.Body body = request.body();
      if (body != null) {
        MediaType contentType = body.contentType();
        if (contentType == null) throw new IllegalStateException("contentType == null");
        if (engine.getRequestHeaders().getContentType() == null) {
          engine.getRequestHeaders().setContentType(contentType.toString());
        }
      }

      engine.sendRequest();

      if (body != null) {
        body.writeTo(engine.getRequestBody());
      }

      engine.readResponse();

      int responseCode = engine.getResponseCode();
      Dispatcher.RealResponseBody responseBody = new Dispatcher.RealResponseBody(
          engine.getResponseHeaders(), engine.getResponseBody());

      Response response = new Response.Builder(request, responseCode)
          .rawHeaders(engine.getResponseHeaders().getHeaders())
          .body(responseBody)
          .redirectedBy(redirectedBy)
          .build();

      Request redirect = processResponse(engine, response);

      if (redirect == null) {
        engine.automaticallyReleaseConnectionToPool();
        return response;
      }

      // TODO: fail if too many redirects
      // TODO: fail if not following redirects
      // TODO: release engine

      connection = sameConnection(request, redirect) ? engine.getConnection() : null;
      redirectedBy = response;
      request = redirect;
    }
  }

  HttpEngine newEngine(Connection connection) throws IOException {
    String protocol = request.url().getProtocol();
    RawHeaders requestHeaders = request.rawHeaders();
    if (protocol.equals("http")) {
      return new HttpEngine(client, this, request.method(), requestHeaders, connection, null);
    } else if (protocol.equals("https")) {
      return new HttpsEngine(client, this, request.method(), requestHeaders, connection, null);
    } else {
      throw new AssertionError();
    }
  }

  /**
   * Figures out the HTTP request to make in response to receiving {@code
   * response}. This will either add authentication headers or follow
   * redirects. If a follow-up is either unnecessary or not applicable, this
   * returns null.
   */
  private Request processResponse(HttpEngine engine, Response response) throws IOException {
    Request request = response.request();
    Proxy selectedProxy = engine.getConnection() != null
        ? engine.getConnection().getRoute().getProxy()
        : client.getProxy();
    int responseCode = response.code();

    switch (responseCode) {
      case HTTP_PROXY_AUTH:
        if (selectedProxy.type() != Proxy.Type.HTTP) {
          throw new ProtocolException("Received HTTP_PROXY_AUTH (407) code while not using proxy");
        }
        // fall-through
      case HTTP_UNAUTHORIZED:
        RawHeaders successorRequestHeaders = request.rawHeaders();
        boolean credentialsFound = HttpAuthenticator.processAuthHeader(client.getAuthenticator(),
            response.code(), response.rawHeaders(), successorRequestHeaders, selectedProxy,
            this.request.url());
        return credentialsFound
            ? request.newBuilder().rawHeaders(successorRequestHeaders).build()
            : null;

      case HTTP_MULT_CHOICE:
      case HTTP_MOVED_PERM:
      case HTTP_MOVED_TEMP:
      case HTTP_SEE_OTHER:
      case HTTP_TEMP_REDIRECT:
        String method = request.method();
        if (responseCode == HTTP_TEMP_REDIRECT && !method.equals("GET") && !method.equals("HEAD")) {
          // "If the 307 status code is received in response to a request other than GET or HEAD,
          // the user agent MUST NOT automatically redirect the request"
          return null;
        }

        String location = response.header("Location");
        if (location == null) {
          return null;
        }

        URL url = new URL(request.url(), location);
        if (!url.getProtocol().equals("https") && !url.getProtocol().equals("http")) {
          return null; // Don't follow redirects to unsupported protocols.
        }

        return this.request.newBuilder().url(url).build();

      default:
        return null;
    }
  }

  private boolean sameConnection(Request a, Request b) {
    return a.url().getHost().equals(b.url().getHost())
        && getEffectivePort(a.url()) == getEffectivePort(b.url())
        && a.url().getProtocol().equals(b.url().getProtocol());
  }
}


File: platforms/android/CordovaLib/src/com/squareup/okhttp/MediaType.java
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
package com.squareup.okhttp;

import java.nio.charset.Charset;
import java.util.Locale;
import java.util.regex.Matcher;
import java.util.regex.Pattern;

/**
 * An <a href="http://tools.ietf.org/html/rfc2045">RFC 2045</a> Media Type,
 * appropriate to describe the content type of an HTTP request or response body.
 */
public final class MediaType {
  private static final String TOKEN = "([a-zA-Z0-9-!#$%&'*+.^_`{|}~]+)";
  private static final String QUOTED = "\"([^\"]*)\"";
  private static final Pattern TYPE_SUBTYPE = Pattern.compile(TOKEN + "/" + TOKEN);
  private static final Pattern PARAMETER = Pattern.compile(
      ";\\s*" + TOKEN + "=(?:" + TOKEN + "|" + QUOTED + ")");

  private final String mediaType;
  private final String type;
  private final String subtype;
  private final String charset;

  private MediaType(String mediaType, String type, String subtype, String charset) {
    this.mediaType = mediaType;
    this.type = type;
    this.subtype = subtype;
    this.charset = charset;
  }

  /**
   * Returns a media type for {@code string}, or null if {@code string} is not a
   * well-formed media type.
   */
  public static MediaType parse(String string) {
    Matcher typeSubtype = TYPE_SUBTYPE.matcher(string);
    if (!typeSubtype.lookingAt()) return null;
    String type = typeSubtype.group(1).toLowerCase(Locale.US);
    String subtype = typeSubtype.group(2).toLowerCase(Locale.US);

    String charset = null;
    Matcher parameter = PARAMETER.matcher(string);
    for (int s = typeSubtype.end(); s < string.length(); s = parameter.end()) {
      parameter.region(s, string.length());
      if (!parameter.lookingAt()) return null; // This is not a well-formed media type.

      String name = parameter.group(1);
      if (name == null || !name.equalsIgnoreCase("charset")) continue;
      if (charset != null) throw new IllegalArgumentException("Multiple charsets: " + string);
      charset = parameter.group(2) != null
          ? parameter.group(2)  // Value is a token.
          : parameter.group(3); // Value is a quoted string.
    }

    return new MediaType(string, type, subtype, charset);
  }

  /**
   * Returns the high-level media type, such as "text", "image", "audio",
   * "video", or "application".
   */
  public String type() {
    return type;
  }

  /**
   * Returns a specific media subtype, such as "plain" or "png", "mpeg",
   * "mp4" or "xml".
   */
  public String subtype() {
    return subtype;
  }

  /**
   * Returns the charset of this media type, or null if this media type doesn't
   * specify a charset.
   */
  public Charset charset() {
    return charset != null ? Charset.forName(charset) : null;
  }

  /**
   * Returns the charset of this media type, or {@code defaultValue} if this
   * media type doesn't specify a charset.
   */
  public Charset charset(Charset defaultValue) {
    return charset != null ? Charset.forName(charset) : defaultValue;
  }

  /**
   * Returns the encoded media type, like "text/plain; charset=utf-8",
   * appropriate for use in a Content-Type header.
   */
  @Override public String toString() {
    return mediaType;
  }

  @Override public boolean equals(Object o) {
    return o instanceof MediaType && ((MediaType) o).mediaType.equals(mediaType);
  }

  @Override public int hashCode() {
    return mediaType.hashCode();
  }
}


File: platforms/android/CordovaLib/src/com/squareup/okhttp/OkAuthenticator.java
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
package com.squareup.okhttp;

import com.squareup.okhttp.internal.Base64;
import java.io.IOException;
import java.io.UnsupportedEncodingException;
import java.net.Proxy;
import java.net.URL;
import java.util.List;

/**
 * Responds to authentication challenges from the remote web or proxy server by
 * returning credentials.
 */
public interface OkAuthenticator {
  /**
   * Returns a credential that satisfies the authentication challenge made by
   * {@code url}. Returns null if the challenge cannot be satisfied. This method
   * is called in response to an HTTP 401 unauthorized status code sent by the
   * origin server.
   *
   * @param challenges parsed "WWW-Authenticate" challenge headers from the HTTP
   *     response.
   */
  Credential authenticate(Proxy proxy, URL url, List<Challenge> challenges) throws IOException;

  /**
   * Returns a credential that satisfies the authentication challenge made by
   * {@code proxy}. Returns null if the challenge cannot be satisfied. This
   * method is called in response to an HTTP 401 unauthorized status code sent
   * by the proxy server.
   *
   * @param challenges parsed "Proxy-Authenticate" challenge headers from the
   *     HTTP response.
   */
  Credential authenticateProxy(Proxy proxy, URL url, List<Challenge> challenges) throws IOException;

  /** An RFC 2617 challenge. */
  public final class Challenge {
    private final String scheme;
    private final String realm;

    public Challenge(String scheme, String realm) {
      this.scheme = scheme;
      this.realm = realm;
    }

    /** Returns the authentication scheme, like {@code Basic}. */
    public String getScheme() {
      return scheme;
    }

    /** Returns the protection space. */
    public String getRealm() {
      return realm;
    }

    @Override public boolean equals(Object o) {
      return o instanceof Challenge
          && ((Challenge) o).scheme.equals(scheme)
          && ((Challenge) o).realm.equals(realm);
    }

    @Override public int hashCode() {
      return scheme.hashCode() + 31 * realm.hashCode();
    }

    @Override public String toString() {
      return scheme + " realm=\"" + realm + "\"";
    }
  }

  /** An RFC 2617 credential. */
  public final class Credential {
    private final String headerValue;

    private Credential(String headerValue) {
      this.headerValue = headerValue;
    }

    /** Returns an auth credential for the Basic scheme. */
    public static Credential basic(String userName, String password) {
      try {
        String usernameAndPassword = userName + ":" + password;
        byte[] bytes = usernameAndPassword.getBytes("ISO-8859-1");
        String encoded = Base64.encode(bytes);
        return new Credential("Basic " + encoded);
      } catch (UnsupportedEncodingException e) {
        throw new AssertionError();
      }
    }

    public String getHeaderValue() {
      return headerValue;
    }

    @Override public boolean equals(Object o) {
      return o instanceof Credential && ((Credential) o).headerValue.equals(headerValue);
    }

    @Override public int hashCode() {
      return headerValue.hashCode();
    }

    @Override public String toString() {
      return headerValue;
    }
  }
}


File: platforms/android/CordovaLib/src/com/squareup/okhttp/OkHttpClient.java
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
package com.squareup.okhttp;

import com.squareup.okhttp.internal.Util;
import com.squareup.okhttp.internal.http.HttpAuthenticator;
import com.squareup.okhttp.internal.http.HttpURLConnectionImpl;
import com.squareup.okhttp.internal.http.HttpsURLConnectionImpl;
import com.squareup.okhttp.internal.http.OkResponseCacheAdapter;
import com.squareup.okhttp.internal.tls.OkHostnameVerifier;
import java.net.CookieHandler;
import java.net.HttpURLConnection;
import java.net.Proxy;
import java.net.ProxySelector;
import java.net.ResponseCache;
import java.net.URL;
import java.net.URLConnection;
import java.net.URLStreamHandler;
import java.net.URLStreamHandlerFactory;
import java.util.Arrays;
import java.util.List;
import java.util.concurrent.TimeUnit;
import javax.net.ssl.HostnameVerifier;
import javax.net.ssl.HttpsURLConnection;
import javax.net.ssl.SSLSocketFactory;

/** Configures and creates HTTP connections. */
public final class OkHttpClient implements URLStreamHandlerFactory {
  private static final List<String> DEFAULT_TRANSPORTS
      = Util.immutableList(Arrays.asList("spdy/3", "http/1.1"));

  private final RouteDatabase routeDatabase;
  private final Dispatcher dispatcher;
  private Proxy proxy;
  private List<String> transports;
  private ProxySelector proxySelector;
  private CookieHandler cookieHandler;
  private ResponseCache responseCache;
  private SSLSocketFactory sslSocketFactory;
  private HostnameVerifier hostnameVerifier;
  private OkAuthenticator authenticator;
  private ConnectionPool connectionPool;
  private boolean followProtocolRedirects = true;
  private int connectTimeout;
  private int readTimeout;

  public OkHttpClient() {
    routeDatabase = new RouteDatabase();
    dispatcher = new Dispatcher();
  }

  private OkHttpClient(OkHttpClient copyFrom) {
    routeDatabase = copyFrom.routeDatabase;
    dispatcher = copyFrom.dispatcher;
  }

  /**
   * Sets the default connect timeout for new connections. A value of 0 means no timeout.
   *
   * @see URLConnection#setConnectTimeout(int)
   */
  public void setConnectTimeout(long timeout, TimeUnit unit) {
    if (timeout < 0) {
      throw new IllegalArgumentException("timeout < 0");
    }
    if (unit == null) {
      throw new IllegalArgumentException("unit == null");
    }
    long millis = unit.toMillis(timeout);
    if (millis > Integer.MAX_VALUE) {
      throw new IllegalArgumentException("Timeout too large.");
    }
    connectTimeout = (int) millis;
  }

  /** Default connect timeout (in milliseconds). */
  public int getConnectTimeout() {
    return connectTimeout;
  }

  /**
   * Sets the default read timeout for new connections. A value of 0 means no timeout.
   *
   * @see URLConnection#setReadTimeout(int)
   */
  public void setReadTimeout(long timeout, TimeUnit unit) {
    if (timeout < 0) {
      throw new IllegalArgumentException("timeout < 0");
    }
    if (unit == null) {
      throw new IllegalArgumentException("unit == null");
    }
    long millis = unit.toMillis(timeout);
    if (millis > Integer.MAX_VALUE) {
      throw new IllegalArgumentException("Timeout too large.");
    }
    readTimeout = (int) millis;
  }

  /** Default read timeout (in milliseconds). */
  public int getReadTimeout() {
    return readTimeout;
  }

  /**
   * Sets the HTTP proxy that will be used by connections created by this
   * client. This takes precedence over {@link #setProxySelector}, which is
   * only honored when this proxy is null (which it is by default). To disable
   * proxy use completely, call {@code setProxy(Proxy.NO_PROXY)}.
   */
  public OkHttpClient setProxy(Proxy proxy) {
    this.proxy = proxy;
    return this;
  }

  public Proxy getProxy() {
    return proxy;
  }

  /**
   * Sets the proxy selection policy to be used if no {@link #setProxy proxy}
   * is specified explicitly. The proxy selector may return multiple proxies;
   * in that case they will be tried in sequence until a successful connection
   * is established.
   *
   * <p>If unset, the {@link ProxySelector#getDefault() system-wide default}
   * proxy selector will be used.
   */
  public OkHttpClient setProxySelector(ProxySelector proxySelector) {
    this.proxySelector = proxySelector;
    return this;
  }

  public ProxySelector getProxySelector() {
    return proxySelector;
  }

  /**
   * Sets the cookie handler to be used to read outgoing cookies and write
   * incoming cookies.
   *
   * <p>If unset, the {@link CookieHandler#getDefault() system-wide default}
   * cookie handler will be used.
   */
  public OkHttpClient setCookieHandler(CookieHandler cookieHandler) {
    this.cookieHandler = cookieHandler;
    return this;
  }

  public CookieHandler getCookieHandler() {
    return cookieHandler;
  }

  /**
   * Sets the response cache to be used to read and write cached responses.
   *
   * <p>If unset, the {@link ResponseCache#getDefault() system-wide default}
   * response cache will be used.
   */
  public OkHttpClient setResponseCache(ResponseCache responseCache) {
    this.responseCache = responseCache;
    return this;
  }

  public ResponseCache getResponseCache() {
    return responseCache;
  }

  public OkResponseCache getOkResponseCache() {
    if (responseCache instanceof HttpResponseCache) {
      return ((HttpResponseCache) responseCache).okResponseCache;
    } else if (responseCache != null) {
      return new OkResponseCacheAdapter(responseCache);
    } else {
      return null;
    }
  }

  /**
   * Sets the socket factory used to secure HTTPS connections.
   *
   * <p>If unset, the {@link HttpsURLConnection#getDefaultSSLSocketFactory()
   * system-wide default} SSL socket factory will be used.
   */
  public OkHttpClient setSslSocketFactory(SSLSocketFactory sslSocketFactory) {
    this.sslSocketFactory = sslSocketFactory;
    return this;
  }

  public SSLSocketFactory getSslSocketFactory() {
    return sslSocketFactory;
  }

  /**
   * Sets the verifier used to confirm that response certificates apply to
   * requested hostnames for HTTPS connections.
   *
   * <p>If unset, the {@link HttpsURLConnection#getDefaultHostnameVerifier()
   * system-wide default} hostname verifier will be used.
   */
  public OkHttpClient setHostnameVerifier(HostnameVerifier hostnameVerifier) {
    this.hostnameVerifier = hostnameVerifier;
    return this;
  }

  public HostnameVerifier getHostnameVerifier() {
    return hostnameVerifier;
  }

  /**
   * Sets the authenticator used to respond to challenges from the remote web
   * server or proxy server.
   *
   * <p>If unset, the {@link java.net.Authenticator#setDefault system-wide default}
   * authenticator will be used.
   */
  public OkHttpClient setAuthenticator(OkAuthenticator authenticator) {
    this.authenticator = authenticator;
    return this;
  }

  public OkAuthenticator getAuthenticator() {
    return authenticator;
  }

  /**
   * Sets the connection pool used to recycle HTTP and HTTPS connections.
   *
   * <p>If unset, the {@link ConnectionPool#getDefault() system-wide
   * default} connection pool will be used.
   */
  public OkHttpClient setConnectionPool(ConnectionPool connectionPool) {
    this.connectionPool = connectionPool;
    return this;
  }

  public ConnectionPool getConnectionPool() {
    return connectionPool;
  }

  /**
   * Configure this client to follow redirects from HTTPS to HTTP and from HTTP
   * to HTTPS.
   *
   * <p>If unset, protocol redirects will be followed. This is different than
   * the built-in {@code HttpURLConnection}'s default.
   */
  public OkHttpClient setFollowProtocolRedirects(boolean followProtocolRedirects) {
    this.followProtocolRedirects = followProtocolRedirects;
    return this;
  }

  public boolean getFollowProtocolRedirects() {
    return followProtocolRedirects;
  }

  public RouteDatabase getRoutesDatabase() {
    return routeDatabase;
  }

  /**
   * Configure the transports used by this client to communicate with remote
   * servers. By default this client will prefer the most efficient transport
   * available, falling back to more ubiquitous transports. Applications should
   * only call this method to avoid specific compatibility problems, such as web
   * servers that behave incorrectly when SPDY is enabled.
   *
   * <p>The following transports are currently supported:
   * <ul>
   *   <li><a href="http://www.w3.org/Protocols/rfc2616/rfc2616.html">http/1.1</a>
   *   <li><a href="http://www.chromium.org/spdy/spdy-protocol/spdy-protocol-draft3">spdy/3</a>
   * </ul>
   *
   * <p><strong>This is an evolving set.</strong> Future releases may drop
   * support for transitional transports (like spdy/3), in favor of their
   * successors (spdy/4 or http/2.0). The http/1.1 transport will never be
   * dropped.
   *
   * <p>If multiple protocols are specified, <a
   * href="https://technotes.googlecode.com/git/nextprotoneg.html">NPN</a> will
   * be used to negotiate a transport. Future releases may use another mechanism
   * (such as <a href="http://tools.ietf.org/html/draft-friedl-tls-applayerprotoneg-02">ALPN</a>)
   * to negotiate a transport.
   *
   * @param transports the transports to use, in order of preference. The list
   *     must contain "http/1.1". It must not contain null.
   */
  public OkHttpClient setTransports(List<String> transports) {
    transports = Util.immutableList(transports);
    if (!transports.contains("http/1.1")) {
      throw new IllegalArgumentException("transports doesn't contain http/1.1: " + transports);
    }
    if (transports.contains(null)) {
      throw new IllegalArgumentException("transports must not contain null");
    }
    if (transports.contains("")) {
      throw new IllegalArgumentException("transports contains an empty string");
    }
    this.transports = transports;
    return this;
  }

  public List<String> getTransports() {
    return transports;
  }

  /**
   * Schedules {@code request} to be executed.
   */
  /* OkHttp 2.0: public */ void enqueue(Request request, Response.Receiver responseReceiver) {
    // Create the HttpURLConnection immediately so the enqueued job gets the current settings of
    // this client. Otherwise changes to this client (socket factory, redirect policy, etc.) may
    // incorrectly be reflected in the request when it is dispatched later.
    dispatcher.enqueue(copyWithDefaults(), request, responseReceiver);
  }

  /**
   * Cancels all scheduled tasks tagged with {@code tag}. Requests that are already
   * in flight might not be canceled.
   */
  /* OkHttp 2.0: public */ void cancel(Object tag) {
    dispatcher.cancel(tag);
  }

  public HttpURLConnection open(URL url) {
    return open(url, proxy);
  }

  HttpURLConnection open(URL url, Proxy proxy) {
    String protocol = url.getProtocol();
    OkHttpClient copy = copyWithDefaults();
    copy.proxy = proxy;

    if (protocol.equals("http")) return new HttpURLConnectionImpl(url, copy);
    if (protocol.equals("https")) return new HttpsURLConnectionImpl(url, copy);
    throw new IllegalArgumentException("Unexpected protocol: " + protocol);
  }

  /**
   * Returns a shallow copy of this OkHttpClient that uses the system-wide default for
   * each field that hasn't been explicitly configured.
   */
  private OkHttpClient copyWithDefaults() {
    OkHttpClient result = new OkHttpClient(this);
    result.proxy = proxy;
    result.proxySelector = proxySelector != null ? proxySelector : ProxySelector.getDefault();
    result.cookieHandler = cookieHandler != null ? cookieHandler : CookieHandler.getDefault();
    result.responseCache = responseCache != null ? responseCache : ResponseCache.getDefault();
    result.sslSocketFactory = sslSocketFactory != null
        ? sslSocketFactory
        : HttpsURLConnection.getDefaultSSLSocketFactory();
    result.hostnameVerifier = hostnameVerifier != null
        ? hostnameVerifier
        : OkHostnameVerifier.INSTANCE;
    result.authenticator = authenticator != null
        ? authenticator
        : HttpAuthenticator.SYSTEM_DEFAULT;
    result.connectionPool = connectionPool != null ? connectionPool : ConnectionPool.getDefault();
    result.followProtocolRedirects = followProtocolRedirects;
    result.transports = transports != null ? transports : DEFAULT_TRANSPORTS;
    result.connectTimeout = connectTimeout;
    result.readTimeout = readTimeout;
    return result;
  }

  /**
   * Creates a URLStreamHandler as a {@link URL#setURLStreamHandlerFactory}.
   *
   * <p>This code configures OkHttp to handle all HTTP and HTTPS connections
   * created with {@link URL#openConnection()}: <pre>   {@code
   *
   *   OkHttpClient okHttpClient = new OkHttpClient();
   *   URL.setURLStreamHandlerFactory(okHttpClient);
   * }</pre>
   */
  public URLStreamHandler createURLStreamHandler(final String protocol) {
    if (!protocol.equals("http") && !protocol.equals("https")) return null;

    return new URLStreamHandler() {
      @Override protected URLConnection openConnection(URL url) {
        return open(url);
      }

      @Override protected URLConnection openConnection(URL url, Proxy proxy) {
        return open(url, proxy);
      }

      @Override protected int getDefaultPort() {
        if (protocol.equals("http")) return 80;
        if (protocol.equals("https")) return 443;
        throw new AssertionError();
      }
    };
  }
}


File: platforms/android/CordovaLib/src/com/squareup/okhttp/OkResponseCache.java
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
package com.squareup.okhttp;

import java.io.IOException;
import java.net.CacheRequest;
import java.net.CacheResponse;
import java.net.HttpURLConnection;
import java.net.URI;
import java.net.URLConnection;
import java.util.List;
import java.util.Map;

/**
 * An extended response cache API. Unlike {@link java.net.ResponseCache}, this
 * interface supports conditional caching and statistics.
 *
 * <h3>Warning: Experimental OkHttp 2.0 API</h3>
 * This class is in beta. APIs are subject to change!
 */
public interface OkResponseCache {
  CacheResponse get(URI uri, String requestMethod, Map<String, List<String>> requestHeaders)
      throws IOException;

  CacheRequest put(URI uri, URLConnection urlConnection) throws IOException;

  /** Remove any cache entries for the supplied {@code uri} if the request method invalidates. */
  void maybeRemove(String requestMethod, URI uri) throws IOException;

  /**
   * Handles a conditional request hit by updating the stored cache response
   * with the headers from {@code httpConnection}. The cached response body is
   * not updated. If the stored response has changed since {@code
   * conditionalCacheHit} was returned, this does nothing.
   */
  void update(CacheResponse conditionalCacheHit, HttpURLConnection connection) throws IOException;

  /** Track an conditional GET that was satisfied by this cache. */
  void trackConditionalCacheHit();

  /** Track an HTTP response being satisfied by {@code source}. */
  void trackResponse(ResponseSource source);
}


File: platforms/android/CordovaLib/src/com/squareup/okhttp/Request.java
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
package com.squareup.okhttp;

import com.squareup.okhttp.internal.Util;
import com.squareup.okhttp.internal.http.RawHeaders;
import java.io.File;
import java.io.FileInputStream;
import java.io.IOException;
import java.io.InputStream;
import java.io.OutputStream;
import java.io.UnsupportedEncodingException;
import java.net.MalformedURLException;
import java.net.URL;
import java.util.List;
import java.util.Set;

/**
 * An HTTP request. Instances of this class are immutable if their {@link #body}
 * is null or itself immutable.
 *
 * <h3>Warning: Experimental OkHttp 2.0 API</h3>
 * This class is in beta. APIs are subject to change!
 */
/* OkHttp 2.0: public */ final class Request {
  private final URL url;
  private final String method;
  private final RawHeaders headers;
  private final Body body;
  private final Object tag;

  private Request(Builder builder) {
    this.url = builder.url;
    this.method = builder.method;
    this.headers = new RawHeaders(builder.headers);
    this.body = builder.body;
    this.tag = builder.tag != null ? builder.tag : this;
  }

  public URL url() {
    return url;
  }

  public String urlString() {
    return url.toString();
  }

  public String method() {
    return method;
  }

  public String header(String name) {
    return headers.get(name);
  }

  public List<String> headers(String name) {
    return headers.values(name);
  }

  public Set<String> headerNames() {
    return headers.names();
  }

  RawHeaders rawHeaders() {
    return new RawHeaders(headers);
  }

  public int headerCount() {
    return headers.length();
  }

  public String headerName(int index) {
    return headers.getFieldName(index);
  }

  public String headerValue(int index) {
    return headers.getValue(index);
  }

  public Body body() {
    return body;
  }

  public Object tag() {
    return tag;
  }

  Builder newBuilder() {
    return new Builder(url)
        .method(method, body)
        .rawHeaders(headers)
        .tag(tag);
  }

  public abstract static class Body {
    /** Returns the Content-Type header for this body. */
    public abstract MediaType contentType();

    /**
     * Returns the number of bytes that will be written to {@code out} in a call
     * to {@link #writeTo}, or -1 if that count is unknown.
     */
    public long contentLength() {
      return -1;
    }

    /** Writes the content of this request to {@code out}. */
    public abstract void writeTo(OutputStream out) throws IOException;

    /**
     * Returns a new request body that transmits {@code content}. If {@code
     * contentType} lacks a charset, this will use UTF-8.
     */
    public static Body create(MediaType contentType, String content) {
      contentType = contentType.charset() != null
          ? contentType
          : MediaType.parse(contentType + "; charset=utf-8");
      try {
        byte[] bytes = content.getBytes(contentType.charset().name());
        return create(contentType, bytes);
      } catch (UnsupportedEncodingException e) {
        throw new AssertionError();
      }
    }

    /** Returns a new request body that transmits {@code content}. */
    public static Body create(final MediaType contentType, final byte[] content) {
      if (contentType == null) throw new NullPointerException("contentType == null");
      if (content == null) throw new NullPointerException("content == null");

      return new Body() {
        @Override public MediaType contentType() {
          return contentType;
        }

        @Override public long contentLength() {
          return content.length;
        }

        @Override public void writeTo(OutputStream out) throws IOException {
          out.write(content);
        }
      };
    }

    /** Returns a new request body that transmits the content of {@code file}. */
    public static Body create(final MediaType contentType, final File file) {
      if (contentType == null) throw new NullPointerException("contentType == null");
      if (file == null) throw new NullPointerException("content == null");

      return new Body() {
        @Override public MediaType contentType() {
          return contentType;
        }

        @Override public long contentLength() {
          return file.length();
        }

        @Override public void writeTo(OutputStream out) throws IOException {
          long length = contentLength();
          if (length == 0) return;

          InputStream in = null;
          try {
            in = new FileInputStream(file);
            byte[] buffer = new byte[(int) Math.min(8192, length)];
            for (int c; (c = in.read(buffer)) != -1; ) {
              out.write(buffer, 0, c);
            }
          } finally {
            Util.closeQuietly(in);
          }
        }
      };
    }
  }

  public static class Builder {
    private URL url;
    private String method = "GET";
    private RawHeaders headers = new RawHeaders();
    private Body body;
    private Object tag;

    public Builder(String url) {
      url(url);
    }

    public Builder(URL url) {
      url(url);
    }

    public Builder url(String url) {
      try {
        this.url = new URL(url);
        return this;
      } catch (MalformedURLException e) {
        throw new IllegalArgumentException("Malformed URL: " + url);
      }
    }

    public Builder url(URL url) {
      if (url == null) throw new IllegalStateException("url == null");
      this.url = url;
      return this;
    }

    /**
     * Sets the header named {@code name} to {@code value}. If this request
     * already has any headers with that name, they are all replaced.
     */
    public Builder header(String name, String value) {
      headers.set(name, value);
      return this;
    }

    /**
     * Adds a header with {@code name} and {@code value}. Prefer this method for
     * multiply-valued headers like "Cookie".
     */
    public Builder addHeader(String name, String value) {
      headers.add(name, value);
      return this;
    }

    Builder rawHeaders(RawHeaders rawHeaders) {
      headers = new RawHeaders(rawHeaders);
      return this;
    }

    public Builder get() {
      return method("GET", null);
    }

    public Builder head() {
      return method("HEAD", null);
    }

    public Builder post(Body body) {
      return method("POST", body);
    }

    public Builder put(Body body) {
      return method("PUT", body);
    }

    public Builder method(String method, Body body) {
      if (method == null || method.length() == 0) {
        throw new IllegalArgumentException("method == null || method.length() == 0");
      }
      this.method = method;
      this.body = body;
      return this;
    }

    /**
     * Attaches {@code tag} to the request. It can be used later to cancel the
     * request. If the tag is unspecified or null, the request is canceled by
     * using the request itself as the tag.
     */
    public Builder tag(Object tag) {
      this.tag = tag;
      return this;
    }

    public Request build() {
      return new Request(this);
    }
  }
}


File: platforms/android/CordovaLib/src/com/squareup/okhttp/Response.java
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
package com.squareup.okhttp;

import com.squareup.okhttp.internal.Util;
import com.squareup.okhttp.internal.http.RawHeaders;
import java.io.ByteArrayOutputStream;
import java.io.IOException;
import java.io.InputStream;
import java.io.InputStreamReader;
import java.io.Reader;
import java.nio.charset.Charset;
import java.util.List;
import java.util.Set;

import static com.squareup.okhttp.internal.Util.UTF_8;

/**
 * An HTTP response. Instances of this class are not immutable: the response
 * body is a one-shot value that may be consumed only once. All other properties
 * are immutable.
 *
 * <h3>Warning: Experimental OkHttp 2.0 API</h3>
 * This class is in beta. APIs are subject to change!
 */
/* OkHttp 2.0: public */ final class Response {
  private final Request request;
  private final int code;
  private final RawHeaders headers;
  private final Body body;
  private final Response redirectedBy;

  private Response(Builder builder) {
    this.request = builder.request;
    this.code = builder.code;
    this.headers = new RawHeaders(builder.headers);
    this.body = builder.body;
    this.redirectedBy = builder.redirectedBy;
  }

  /**
   * The wire-level request that initiated this HTTP response. This is usually
   * <strong>not</strong> the same request instance provided to the HTTP client:
   * <ul>
   *     <li>It may be transformed by the HTTP client. For example, the client
   *         may have added its own {@code Content-Encoding} header to enable
   *         response compression.
   *     <li>It may be the request generated in response to an HTTP redirect.
   *         In this case the request URL may be different than the initial
   *         request URL.
   * </ul>
   */
  public Request request() {
    return request;
  }

  public int code() {
    return code;
  }

  public String header(String name) {
    return header(name, null);
  }

  public String header(String name, String defaultValue) {
    String result = headers.get(name);
    return result != null ? result : defaultValue;
  }

  public List<String> headers(String name) {
    return headers.values(name);
  }

  public Set<String> headerNames() {
    return headers.names();
  }

  public int headerCount() {
    return headers.length();
  }

  public String headerName(int index) {
    return headers.getFieldName(index);
  }

  RawHeaders rawHeaders() {
    return new RawHeaders(headers);
  }

  public String headerValue(int index) {
    return headers.getValue(index);
  }

  public Body body() {
    return body;
  }

  /**
   * Returns the response for the HTTP redirect that triggered this response, or
   * null if this response wasn't triggered by an automatic redirect. The body
   * of the returned response should not be read because it has already been
   * consumed by the redirecting client.
   */
  public Response redirectedBy() {
    return redirectedBy;
  }

  public abstract static class Body {
    /** Multiple calls to {@link #charStream()} must return the same instance. */
    private Reader reader;

    /**
     * Returns true if further data from this response body should be read at
     * this time. For asynchronous transports like SPDY and HTTP/2.0, this will
     * return false once all locally-available body bytes have been read.
     *
     * <p>Clients with many concurrent downloads can use this method to reduce
     * the number of idle threads blocking on reads. See {@link
     * Receiver#onResponse} for details.
     */
    // <h3>Body.ready() vs. InputStream.available()</h3>
    // TODO: Can we fix response bodies to implement InputStream.available well?
    // The deflater implementation is broken by default but we could do better.
    public abstract boolean ready() throws IOException;

    public abstract MediaType contentType();

    /**
     * Returns the number of bytes in that will returned by {@link #bytes}, or
     * {@link #byteStream}, or -1 if unknown.
     */
    public abstract long contentLength();

    public abstract InputStream byteStream() throws IOException;

    public final byte[] bytes() throws IOException {
      long contentLength = contentLength();
      if (contentLength > Integer.MAX_VALUE) {
        throw new IOException("Cannot buffer entire body for content length: " + contentLength);
      }

      if (contentLength != -1) {
        byte[] content = new byte[(int) contentLength];
        InputStream in = byteStream();
        Util.readFully(in, content);
        if (in.read() != -1) throw new IOException("Content-Length and stream length disagree");
        return content;

      } else {
        ByteArrayOutputStream out = new ByteArrayOutputStream();
        Util.copy(byteStream(), out);
        return out.toByteArray();
      }
    }

    /**
     * Returns the response as a character stream decoded with the charset
     * of the Content-Type header. If that header is either absent or lacks a
     * charset, this will attempt to decode the response body as UTF-8.
     */
    public final Reader charStream() throws IOException {
      if (reader == null) {
        reader = new InputStreamReader(byteStream(), charset());
      }
      return reader;
    }

    /**
     * Returns the response as a string decoded with the charset of the
     * Content-Type header. If that header is either absent or lacks a charset,
     * this will attempt to decode the response body as UTF-8.
     */
    public final String string() throws IOException {
      return new String(bytes(), charset().name());
    }

    private Charset charset() {
      MediaType contentType = contentType();
      return contentType != null ? contentType.charset(UTF_8) : UTF_8;
    }
  }

  public interface Receiver {
    /**
     * Called when the request could not be executed due to a connectivity
     * problem or timeout. Because networks can fail during an exchange, it is
     * possible that the remote server accepted the request before the failure.
     */
    void onFailure(Failure failure);

    /**
     * Called when the HTTP response was successfully returned by the remote
     * server. The receiver may proceed to read the response body with the
     * response's {@link #body} method.
     *
     * <p>Note that transport-layer success (receiving a HTTP response code,
     * headers and body) does not necessarily indicate application-layer
     * success: {@code response} may still indicate an unhappy HTTP response
     * code like 404 or 500.
     *
     * <h3>Non-blocking responses</h3>
     *
     * <p>Receivers do not need to block while waiting for the response body to
     * download. Instead, they can get called back as data arrives. Use {@link
     * Body#ready} to check if bytes should be read immediately. While there is
     * data ready, read it. If there isn't, return false: receivers will be
     * called back with {@code onResponse()} as additional data is downloaded.
     *
     * <p>Return true to indicate that the receiver has finished handling the
     * response body. If the response body has unread data, it will be
     * discarded.
     *
     * <p>When the response body has been fully consumed the returned value is
     * undefined.
     *
     * <p>The current implementation of {@link Body#ready} always returns true
     * when the underlying transport is HTTP/1. This results in blocking on that
     * transport. For effective non-blocking your server must support SPDY or
     * HTTP/2.
     */
    boolean onResponse(Response response) throws IOException;
  }

  public static class Builder {
    private final Request request;
    private final int code;
    private RawHeaders headers = new RawHeaders();
    private Body body;
    private Response redirectedBy;

    public Builder(Request request, int code) {
      if (request == null) throw new IllegalArgumentException("request == null");
      if (code <= 0) throw new IllegalArgumentException("code <= 0");
      this.request = request;
      this.code = code;
    }

    /**
     * Sets the header named {@code name} to {@code value}. If this request
     * already has any headers with that name, they are all replaced.
     */
    public Builder header(String name, String value) {
      headers.set(name, value);
      return this;
    }

    /**
     * Adds a header with {@code name} and {@code value}. Prefer this method for
     * multiply-valued headers like "Set-Cookie".
     */
    public Builder addHeader(String name, String value) {
      headers.add(name, value);
      return this;
    }

    Builder rawHeaders(RawHeaders rawHeaders) {
      headers = new RawHeaders(rawHeaders);
      return this;
    }

    public Builder body(Body body) {
      this.body = body;
      return this;
    }

    public Builder redirectedBy(Response redirectedBy) {
      this.redirectedBy = redirectedBy;
      return this;
    }

    public Response build() {
      if (request == null) throw new IllegalStateException("Response has no request.");
      if (code == -1) throw new IllegalStateException("Response has no code.");
      return new Response(this);
    }
  }
}


File: platforms/android/CordovaLib/src/com/squareup/okhttp/ResponseSource.java
/*
 * Copyright (C) 2011 The Android Open Source Project
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
package com.squareup.okhttp;

/** The source of an HTTP response. */
public enum ResponseSource {

  /** The response was returned from the local cache. */
  CACHE,

  /**
   * The response is available in the cache but must be validated with the
   * network. The cache result will be used if it is still valid; otherwise
   * the network's response will be used.
   */
  CONDITIONAL_CACHE,

  /** The response was returned from the network. */
  NETWORK;

  public boolean requiresConnection() {
    return this == CONDITIONAL_CACHE || this == NETWORK;
  }
}


File: platforms/android/CordovaLib/src/com/squareup/okhttp/Route.java
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
package com.squareup.okhttp;

import java.net.InetSocketAddress;
import java.net.Proxy;

/** Represents the route used by a connection to reach an endpoint. */
public class Route {
  final Address address;
  final Proxy proxy;
  final InetSocketAddress inetSocketAddress;
  final boolean modernTls;

  public Route(Address address, Proxy proxy, InetSocketAddress inetSocketAddress,
      boolean modernTls) {
    if (address == null) throw new NullPointerException("address == null");
    if (proxy == null) throw new NullPointerException("proxy == null");
    if (inetSocketAddress == null) throw new NullPointerException("inetSocketAddress == null");
    this.address = address;
    this.proxy = proxy;
    this.inetSocketAddress = inetSocketAddress;
    this.modernTls = modernTls;
  }

  /** Returns the {@link Address} of this route. */
  public Address getAddress() {
    return address;
  }

  /**
   * Returns the {@link Proxy} of this route.
   *
   * <strong>Warning:</strong> This may be different than the proxy returned
   * by {@link #getAddress}! That is the proxy that the user asked to be
   * connected to; this returns the proxy that they were actually connected
   * to. The two may disagree when a proxy selector selects a different proxy
   * for a connection.
   */
  public Proxy getProxy() {
    return proxy;
  }

  /** Returns the {@link InetSocketAddress} of this route. */
  public InetSocketAddress getSocketAddress() {
    return inetSocketAddress;
  }

  /** Returns true if this route uses modern TLS. */
  public boolean isModernTls() {
    return modernTls;
  }

  /** Returns a copy of this route with flipped TLS mode. */
  Route flipTlsMode() {
    return new Route(address, proxy, inetSocketAddress, !modernTls);
  }

  @Override public boolean equals(Object obj) {
    if (obj instanceof Route) {
      Route other = (Route) obj;
      return (address.equals(other.address)
          && proxy.equals(other.proxy)
          && inetSocketAddress.equals(other.inetSocketAddress)
          && modernTls == other.modernTls);
    }
    return false;
  }

  @Override public int hashCode() {
    int result = 17;
    result = 31 * result + address.hashCode();
    result = 31 * result + proxy.hashCode();
    result = 31 * result + inetSocketAddress.hashCode();
    result = result + (modernTls ? (31 * result) : 0);
    return result;
  }
}


File: platforms/android/CordovaLib/src/com/squareup/okhttp/RouteDatabase.java
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
package com.squareup.okhttp;

import java.io.IOException;
import java.util.LinkedHashSet;
import java.util.Set;
import javax.net.ssl.SSLHandshakeException;

/**
 * A blacklist of failed routes to avoid when creating a new connection to a
 * target address. This is used so that OkHttp can learn from its mistakes: if
 * there was a failure attempting to connect to a specific IP address, proxy
 * server or TLS mode, that failure is remembered and alternate routes are
 * preferred.
 */
public final class RouteDatabase {
  private final Set<Route> failedRoutes = new LinkedHashSet<Route>();

  /** Records a failure connecting to {@code failedRoute}. */
  public synchronized void failed(Route failedRoute, IOException failure) {
    failedRoutes.add(failedRoute);

    if (!(failure instanceof SSLHandshakeException)) {
      // If the problem was not related to SSL then it will also fail with
      // a different TLS mode therefore we can be proactive about it.
      failedRoutes.add(failedRoute.flipTlsMode());
    }
  }

  /** Records success connecting to {@code failedRoute}. */
  public synchronized void connected(Route route) {
    failedRoutes.remove(route);
  }

  /** Returns true if {@code route} has failed recently and should be avoided. */
  public synchronized boolean shouldPostpone(Route route) {
    return failedRoutes.contains(route);
  }

  public synchronized int failedRoutesCount() {
    return failedRoutes.size();
  }
}


File: platforms/android/CordovaLib/src/com/squareup/okhttp/TunnelRequest.java
/*
 * Copyright (C) 2012 The Android Open Source Project
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
package com.squareup.okhttp;

import com.squareup.okhttp.internal.http.RawHeaders;

import static com.squareup.okhttp.internal.Util.getDefaultPort;

/**
 * Routing and authentication information sent to an HTTP proxy to create a
 * HTTPS to an origin server. Everything in the tunnel request is sent
 * unencrypted to the proxy server.
 *
 * <p>See <a href="http://www.ietf.org/rfc/rfc2817.txt">RFC 2817, Section
 * 5.2</a>.
 */
public final class TunnelRequest {
  final String host;
  final int port;
  final String userAgent;
  final String proxyAuthorization;

  /**
   * @param host the origin server's hostname. Not null.
   * @param port the origin server's port, like 80 or 443.
   * @param userAgent the client's user-agent. Not null.
   * @param proxyAuthorization proxy authorization, or null if the proxy is
   * used without an authorization header.
   */
  public TunnelRequest(String host, int port, String userAgent, String proxyAuthorization) {
    if (host == null) throw new NullPointerException("host == null");
    if (userAgent == null) throw new NullPointerException("userAgent == null");
    this.host = host;
    this.port = port;
    this.userAgent = userAgent;
    this.proxyAuthorization = proxyAuthorization;
  }

  /**
   * If we're creating a TLS tunnel, send only the minimum set of headers.
   * This avoids sending potentially sensitive data like HTTP cookies to
   * the proxy unencrypted.
   */
  RawHeaders getRequestHeaders() {
    RawHeaders result = new RawHeaders();
    result.setRequestLine("CONNECT " + host + ":" + port + " HTTP/1.1");

    // Always set Host and User-Agent.
    result.set("Host", port == getDefaultPort("https") ? host : (host + ":" + port));
    result.set("User-Agent", userAgent);

    // Copy over the Proxy-Authorization header if it exists.
    if (proxyAuthorization != null) {
      result.set("Proxy-Authorization", proxyAuthorization);
    }

    // Always set the Proxy-Connection to Keep-Alive for the benefit of
    // HTTP/1.0 proxies like Squid.
    result.set("Proxy-Connection", "Keep-Alive");
    return result;
  }
}


File: platforms/android/CordovaLib/src/com/squareup/okhttp/internal/AbstractOutputStream.java
/*
 * Copyright (C) 2010 The Android Open Source Project
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

package com.squareup.okhttp.internal;

import java.io.IOException;
import java.io.OutputStream;

/**
 * An output stream for an HTTP request body.
 *
 * <p>Since a single socket's output stream may be used to write multiple HTTP
 * requests to the same server, subclasses should not close the socket stream.
 */
public abstract class AbstractOutputStream extends OutputStream {
  protected boolean closed;

  @Override public final void write(int data) throws IOException {
    write(new byte[] { (byte) data });
  }

  protected final void checkNotClosed() throws IOException {
    if (closed) {
      throw new IOException("stream closed");
    }
  }

  /** Returns true if this stream was closed locally. */
  public boolean isClosed() {
    return closed;
  }
}


File: platforms/android/CordovaLib/src/com/squareup/okhttp/internal/Base64.java
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

/**
 * @author Alexander Y. Kleymenov
 */

package com.squareup.okhttp.internal;

import java.io.UnsupportedEncodingException;

import static com.squareup.okhttp.internal.Util.EMPTY_BYTE_ARRAY;

/**
 * <a href="http://www.ietf.org/rfc/rfc2045.txt">Base64</a> encoder/decoder.
 * In violation of the RFC, this encoder doesn't wrap lines at 76 columns.
 */
public final class Base64 {
  private Base64() {
  }

  public static byte[] decode(byte[] in) {
    return decode(in, in.length);
  }

  public static byte[] decode(byte[] in, int len) {
    // approximate output length
    int length = len / 4 * 3;
    // return an empty array on empty or short input without padding
    if (length == 0) {
      return EMPTY_BYTE_ARRAY;
    }
    // temporary array
    byte[] out = new byte[length];
    // number of padding characters ('=')
    int pad = 0;
    byte chr;
    // compute the number of the padding characters
    // and adjust the length of the input
    for (; ; len--) {
      chr = in[len - 1];
      // skip the neutral characters
      if ((chr == '\n') || (chr == '\r') || (chr == ' ') || (chr == '\t')) {
        continue;
      }
      if (chr == '=') {
        pad++;
      } else {
        break;
      }
    }
    // index in the output array
    int outIndex = 0;
    // index in the input array
    int inIndex = 0;
    // holds the value of the input character
    int bits = 0;
    // holds the value of the input quantum
    int quantum = 0;
    for (int i = 0; i < len; i++) {
      chr = in[i];
      // skip the neutral characters
      if ((chr == '\n') || (chr == '\r') || (chr == ' ') || (chr == '\t')) {
        continue;
      }
      if ((chr >= 'A') && (chr <= 'Z')) {
        // char ASCII value
        //  A    65    0
        //  Z    90    25 (ASCII - 65)
        bits = chr - 65;
      } else if ((chr >= 'a') && (chr <= 'z')) {
        // char ASCII value
        //  a    97    26
        //  z    122   51 (ASCII - 71)
        bits = chr - 71;
      } else if ((chr >= '0') && (chr <= '9')) {
        // char ASCII value
        //  0    48    52
        //  9    57    61 (ASCII + 4)
        bits = chr + 4;
      } else if (chr == '+') {
        bits = 62;
      } else if (chr == '/') {
        bits = 63;
      } else {
        return null;
      }
      // append the value to the quantum
      quantum = (quantum << 6) | (byte) bits;
      if (inIndex % 4 == 3) {
        // 4 characters were read, so make the output:
        out[outIndex++] = (byte) (quantum >> 16);
        out[outIndex++] = (byte) (quantum >> 8);
        out[outIndex++] = (byte) quantum;
      }
      inIndex++;
    }
    if (pad > 0) {
      // adjust the quantum value according to the padding
      quantum = quantum << (6 * pad);
      // make output
      out[outIndex++] = (byte) (quantum >> 16);
      if (pad == 1) {
        out[outIndex++] = (byte) (quantum >> 8);
      }
    }
    // create the resulting array
    byte[] result = new byte[outIndex];
    System.arraycopy(out, 0, result, 0, outIndex);
    return result;
  }

  private static final byte[] MAP = new byte[] {
      'A', 'B', 'C', 'D', 'E', 'F', 'G', 'H', 'I', 'J', 'K', 'L', 'M', 'N', 'O', 'P', 'Q', 'R', 'S',
      'T', 'U', 'V', 'W', 'X', 'Y', 'Z', 'a', 'b', 'c', 'd', 'e', 'f', 'g', 'h', 'i', 'j', 'k', 'l',
      'm', 'n', 'o', 'p', 'q', 'r', 's', 't', 'u', 'v', 'w', 'x', 'y', 'z', '0', '1', '2', '3', '4',
      '5', '6', '7', '8', '9', '+', '/'
  };

  public static String encode(byte[] in) {
    int length = (in.length + 2) * 4 / 3;
    byte[] out = new byte[length];
    int index = 0, end = in.length - in.length % 3;
    for (int i = 0; i < end; i += 3) {
      out[index++] = MAP[(in[i] & 0xff) >> 2];
      out[index++] = MAP[((in[i] & 0x03) << 4) | ((in[i + 1] & 0xff) >> 4)];
      out[index++] = MAP[((in[i + 1] & 0x0f) << 2) | ((in[i + 2] & 0xff) >> 6)];
      out[index++] = MAP[(in[i + 2] & 0x3f)];
    }
    switch (in.length % 3) {
      case 1:
        out[index++] = MAP[(in[end] & 0xff) >> 2];
        out[index++] = MAP[(in[end] & 0x03) << 4];
        out[index++] = '=';
        out[index++] = '=';
        break;
      case 2:
        out[index++] = MAP[(in[end] & 0xff) >> 2];
        out[index++] = MAP[((in[end] & 0x03) << 4) | ((in[end + 1] & 0xff) >> 4)];
        out[index++] = MAP[((in[end + 1] & 0x0f) << 2)];
        out[index++] = '=';
        break;
    }
    try {
      return new String(out, 0, index, "US-ASCII");
    } catch (UnsupportedEncodingException e) {
      throw new AssertionError(e);
    }
  }
}


File: platforms/android/CordovaLib/src/com/squareup/okhttp/internal/DiskLruCache.java
/*
 * Copyright (C) 2011 The Android Open Source Project
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

package com.squareup.okhttp.internal;

import java.io.BufferedWriter;
import java.io.Closeable;
import java.io.EOFException;
import java.io.File;
import java.io.FileInputStream;
import java.io.FileNotFoundException;
import java.io.FileOutputStream;
import java.io.FilterOutputStream;
import java.io.IOException;
import java.io.InputStream;
import java.io.InputStreamReader;
import java.io.OutputStream;
import java.io.OutputStreamWriter;
import java.io.Writer;
import java.util.ArrayList;
import java.util.Iterator;
import java.util.LinkedHashMap;
import java.util.Map;
import java.util.concurrent.Callable;
import java.util.concurrent.LinkedBlockingQueue;
import java.util.concurrent.ThreadPoolExecutor;
import java.util.concurrent.TimeUnit;
import java.util.regex.Matcher;
import java.util.regex.Pattern;

/**
 * A cache that uses a bounded amount of space on a filesystem. Each cache
 * entry has a string key and a fixed number of values. Each key must match
 * the regex <strong>[a-z0-9_-]{1,64}</strong>. Values are byte sequences,
 * accessible as streams or files. Each value must be between {@code 0} and
 * {@code Integer.MAX_VALUE} bytes in length.
 *
 * <p>The cache stores its data in a directory on the filesystem. This
 * directory must be exclusive to the cache; the cache may delete or overwrite
 * files from its directory. It is an error for multiple processes to use the
 * same cache directory at the same time.
 *
 * <p>This cache limits the number of bytes that it will store on the
 * filesystem. When the number of stored bytes exceeds the limit, the cache will
 * remove entries in the background until the limit is satisfied. The limit is
 * not strict: the cache may temporarily exceed it while waiting for files to be
 * deleted. The limit does not include filesystem overhead or the cache
 * journal so space-sensitive applications should set a conservative limit.
 *
 * <p>Clients call {@link #edit} to create or update the values of an entry. An
 * entry may have only one editor at one time; if a value is not available to be
 * edited then {@link #edit} will return null.
 * <ul>
 *     <li>When an entry is being <strong>created</strong> it is necessary to
 *         supply a full set of values; the empty value should be used as a
 *         placeholder if necessary.
 *     <li>When an entry is being <strong>edited</strong>, it is not necessary
 *         to supply data for every value; values default to their previous
 *         value.
 * </ul>
 * Every {@link #edit} call must be matched by a call to {@link Editor#commit}
 * or {@link Editor#abort}. Committing is atomic: a read observes the full set
 * of values as they were before or after the commit, but never a mix of values.
 *
 * <p>Clients call {@link #get} to read a snapshot of an entry. The read will
 * observe the value at the time that {@link #get} was called. Updates and
 * removals after the call do not impact ongoing reads.
 *
 * <p>This class is tolerant of some I/O errors. If files are missing from the
 * filesystem, the corresponding entries will be dropped from the cache. If
 * an error occurs while writing a cache value, the edit will fail silently.
 * Callers should handle other problems by catching {@code IOException} and
 * responding appropriately.
 */
public final class DiskLruCache implements Closeable {
  static final String JOURNAL_FILE = "journal";
  static final String JOURNAL_FILE_TEMP = "journal.tmp";
  static final String JOURNAL_FILE_BACKUP = "journal.bkp";
  static final String MAGIC = "libcore.io.DiskLruCache";
  static final String VERSION_1 = "1";
  static final long ANY_SEQUENCE_NUMBER = -1;
  static final Pattern LEGAL_KEY_PATTERN = Pattern.compile("[a-z0-9_-]{1,64}");
  private static final String CLEAN = "CLEAN";
  private static final String DIRTY = "DIRTY";
  private static final String REMOVE = "REMOVE";
  private static final String READ = "READ";

    /*
     * This cache uses a journal file named "journal". A typical journal file
     * looks like this:
     *     libcore.io.DiskLruCache
     *     1
     *     100
     *     2
     *
     *     CLEAN 3400330d1dfc7f3f7f4b8d4d803dfcf6 832 21054
     *     DIRTY 335c4c6028171cfddfbaae1a9c313c52
     *     CLEAN 335c4c6028171cfddfbaae1a9c313c52 3934 2342
     *     REMOVE 335c4c6028171cfddfbaae1a9c313c52
     *     DIRTY 1ab96a171faeeee38496d8b330771a7a
     *     CLEAN 1ab96a171faeeee38496d8b330771a7a 1600 234
     *     READ 335c4c6028171cfddfbaae1a9c313c52
     *     READ 3400330d1dfc7f3f7f4b8d4d803dfcf6
     *
     * The first five lines of the journal form its header. They are the
     * constant string "libcore.io.DiskLruCache", the disk cache's version,
     * the application's version, the value count, and a blank line.
     *
     * Each of the subsequent lines in the file is a record of the state of a
     * cache entry. Each line contains space-separated values: a state, a key,
     * and optional state-specific values.
     *   o DIRTY lines track that an entry is actively being created or updated.
     *     Every successful DIRTY action should be followed by a CLEAN or REMOVE
     *     action. DIRTY lines without a matching CLEAN or REMOVE indicate that
     *     temporary files may need to be deleted.
     *   o CLEAN lines track a cache entry that has been successfully published
     *     and may be read. A publish line is followed by the lengths of each of
     *     its values.
     *   o READ lines track accesses for LRU.
     *   o REMOVE lines track entries that have been deleted.
     *
     * The journal file is appended to as cache operations occur. The journal may
     * occasionally be compacted by dropping redundant lines. A temporary file named
     * "journal.tmp" will be used during compaction; that file should be deleted if
     * it exists when the cache is opened.
     */

  private final File directory;
  private final File journalFile;
  private final File journalFileTmp;
  private final File journalFileBackup;
  private final int appVersion;
  private long maxSize;
  private final int valueCount;
  private long size = 0;
  private Writer journalWriter;
  private final LinkedHashMap<String, Entry> lruEntries =
      new LinkedHashMap<String, Entry>(0, 0.75f, true);
  private int redundantOpCount;

  /**
   * To differentiate between old and current snapshots, each entry is given
   * a sequence number each time an edit is committed. A snapshot is stale if
   * its sequence number is not equal to its entry's sequence number.
   */
  private long nextSequenceNumber = 0;

  /** This cache uses a single background thread to evict entries. */
  final ThreadPoolExecutor executorService =
      new ThreadPoolExecutor(0, 1, 60L, TimeUnit.SECONDS, new LinkedBlockingQueue<Runnable>());
  private final Callable<Void> cleanupCallable = new Callable<Void>() {
    public Void call() throws Exception {
      synchronized (DiskLruCache.this) {
        if (journalWriter == null) {
          return null; // Closed.
        }
        trimToSize();
        if (journalRebuildRequired()) {
          rebuildJournal();
          redundantOpCount = 0;
        }
      }
      return null;
    }
  };

  private DiskLruCache(File directory, int appVersion, int valueCount, long maxSize) {
    this.directory = directory;
    this.appVersion = appVersion;
    this.journalFile = new File(directory, JOURNAL_FILE);
    this.journalFileTmp = new File(directory, JOURNAL_FILE_TEMP);
    this.journalFileBackup = new File(directory, JOURNAL_FILE_BACKUP);
    this.valueCount = valueCount;
    this.maxSize = maxSize;
  }

  /**
   * Opens the cache in {@code directory}, creating a cache if none exists
   * there.
   *
   * @param directory a writable directory
   * @param valueCount the number of values per cache entry. Must be positive.
   * @param maxSize the maximum number of bytes this cache should use to store
   * @throws IOException if reading or writing the cache directory fails
   */
  public static DiskLruCache open(File directory, int appVersion, int valueCount, long maxSize)
      throws IOException {
    if (maxSize <= 0) {
      throw new IllegalArgumentException("maxSize <= 0");
    }
    if (valueCount <= 0) {
      throw new IllegalArgumentException("valueCount <= 0");
    }

    // If a bkp file exists, use it instead.
    File backupFile = new File(directory, JOURNAL_FILE_BACKUP);
    if (backupFile.exists()) {
      File journalFile = new File(directory, JOURNAL_FILE);
      // If journal file also exists just delete backup file.
      if (journalFile.exists()) {
        backupFile.delete();
      } else {
        renameTo(backupFile, journalFile, false);
      }
    }

    // Prefer to pick up where we left off.
    DiskLruCache cache = new DiskLruCache(directory, appVersion, valueCount, maxSize);
    if (cache.journalFile.exists()) {
      try {
        cache.readJournal();
        cache.processJournal();
        cache.journalWriter = new BufferedWriter(
            new OutputStreamWriter(new FileOutputStream(cache.journalFile, true), Util.US_ASCII));
        return cache;
      } catch (IOException journalIsCorrupt) {
        Platform.get().logW("DiskLruCache " + directory + " is corrupt: "
            + journalIsCorrupt.getMessage() + ", removing");
        cache.delete();
      }
    }

    // Create a new empty cache.
    directory.mkdirs();
    cache = new DiskLruCache(directory, appVersion, valueCount, maxSize);
    cache.rebuildJournal();
    return cache;
  }

  private void readJournal() throws IOException {
    StrictLineReader reader = new StrictLineReader(new FileInputStream(journalFile), Util.US_ASCII);
    try {
      String magic = reader.readLine();
      String version = reader.readLine();
      String appVersionString = reader.readLine();
      String valueCountString = reader.readLine();
      String blank = reader.readLine();
      if (!MAGIC.equals(magic)
          || !VERSION_1.equals(version)
          || !Integer.toString(appVersion).equals(appVersionString)
          || !Integer.toString(valueCount).equals(valueCountString)
          || !"".equals(blank)) {
        throw new IOException("unexpected journal header: [" + magic + ", " + version + ", "
            + valueCountString + ", " + blank + "]");
      }

      int lineCount = 0;
      while (true) {
        try {
          readJournalLine(reader.readLine());
          lineCount++;
        } catch (EOFException endOfJournal) {
          break;
        }
      }
      redundantOpCount = lineCount - lruEntries.size();
    } finally {
      Util.closeQuietly(reader);
    }
  }

  private void readJournalLine(String line) throws IOException {
    int firstSpace = line.indexOf(' ');
    if (firstSpace == -1) {
      throw new IOException("unexpected journal line: " + line);
    }

    int keyBegin = firstSpace + 1;
    int secondSpace = line.indexOf(' ', keyBegin);
    final String key;
    if (secondSpace == -1) {
      key = line.substring(keyBegin);
      if (firstSpace == REMOVE.length() && line.startsWith(REMOVE)) {
        lruEntries.remove(key);
        return;
      }
    } else {
      key = line.substring(keyBegin, secondSpace);
    }

    Entry entry = lruEntries.get(key);
    if (entry == null) {
      entry = new Entry(key);
      lruEntries.put(key, entry);
    }

    if (secondSpace != -1 && firstSpace == CLEAN.length() && line.startsWith(CLEAN)) {
      String[] parts = line.substring(secondSpace + 1).split(" ");
      entry.readable = true;
      entry.currentEditor = null;
      entry.setLengths(parts);
    } else if (secondSpace == -1 && firstSpace == DIRTY.length() && line.startsWith(DIRTY)) {
      entry.currentEditor = new Editor(entry);
    } else if (secondSpace == -1 && firstSpace == READ.length() && line.startsWith(READ)) {
      // This work was already done by calling lruEntries.get().
    } else {
      throw new IOException("unexpected journal line: " + line);
    }
  }

  /**
   * Computes the initial size and collects garbage as a part of opening the
   * cache. Dirty entries are assumed to be inconsistent and will be deleted.
   */
  private void processJournal() throws IOException {
    deleteIfExists(journalFileTmp);
    for (Iterator<Entry> i = lruEntries.values().iterator(); i.hasNext(); ) {
      Entry entry = i.next();
      if (entry.currentEditor == null) {
        for (int t = 0; t < valueCount; t++) {
          size += entry.lengths[t];
        }
      } else {
        entry.currentEditor = null;
        for (int t = 0; t < valueCount; t++) {
          deleteIfExists(entry.getCleanFile(t));
          deleteIfExists(entry.getDirtyFile(t));
        }
        i.remove();
      }
    }
  }

  /**
   * Creates a new journal that omits redundant information. This replaces the
   * current journal if it exists.
   */
  private synchronized void rebuildJournal() throws IOException {
    if (journalWriter != null) {
      journalWriter.close();
    }

    Writer writer = new BufferedWriter(
        new OutputStreamWriter(new FileOutputStream(journalFileTmp), Util.US_ASCII));
    try {
      writer.write(MAGIC);
      writer.write("\n");
      writer.write(VERSION_1);
      writer.write("\n");
      writer.write(Integer.toString(appVersion));
      writer.write("\n");
      writer.write(Integer.toString(valueCount));
      writer.write("\n");
      writer.write("\n");

      for (Entry entry : lruEntries.values()) {
        if (entry.currentEditor != null) {
          writer.write(DIRTY + ' ' + entry.key + '\n');
        } else {
          writer.write(CLEAN + ' ' + entry.key + entry.getLengths() + '\n');
        }
      }
    } finally {
      writer.close();
    }

    if (journalFile.exists()) {
      renameTo(journalFile, journalFileBackup, true);
    }
    renameTo(journalFileTmp, journalFile, false);
    journalFileBackup.delete();

    journalWriter = new BufferedWriter(
        new OutputStreamWriter(new FileOutputStream(journalFile, true), Util.US_ASCII));
  }

  private static void deleteIfExists(File file) throws IOException {
    if (file.exists() && !file.delete()) {
      throw new IOException();
    }
  }

  private static void renameTo(File from, File to, boolean deleteDestination) throws IOException {
    if (deleteDestination) {
      deleteIfExists(to);
    }
    if (!from.renameTo(to)) {
      throw new IOException();
    }
  }

  /**
   * Returns a snapshot of the entry named {@code key}, or null if it doesn't
   * exist is not currently readable. If a value is returned, it is moved to
   * the head of the LRU queue.
   */
  public synchronized Snapshot get(String key) throws IOException {
    checkNotClosed();
    validateKey(key);
    Entry entry = lruEntries.get(key);
    if (entry == null) {
      return null;
    }

    if (!entry.readable) {
      return null;
    }

    // Open all streams eagerly to guarantee that we see a single published
    // snapshot. If we opened streams lazily then the streams could come
    // from different edits.
    InputStream[] ins = new InputStream[valueCount];
    try {
      for (int i = 0; i < valueCount; i++) {
        ins[i] = new FileInputStream(entry.getCleanFile(i));
      }
    } catch (FileNotFoundException e) {
      // A file must have been deleted manually!
      for (int i = 0; i < valueCount; i++) {
        if (ins[i] != null) {
          Util.closeQuietly(ins[i]);
        } else {
          break;
        }
      }
      return null;
    }

    redundantOpCount++;
    journalWriter.append(READ + ' ' + key + '\n');
    if (journalRebuildRequired()) {
      executorService.submit(cleanupCallable);
    }

    return new Snapshot(key, entry.sequenceNumber, ins, entry.lengths);
  }

  /**
   * Returns an editor for the entry named {@code key}, or null if another
   * edit is in progress.
   */
  public Editor edit(String key) throws IOException {
    return edit(key, ANY_SEQUENCE_NUMBER);
  }

  private synchronized Editor edit(String key, long expectedSequenceNumber) throws IOException {
    checkNotClosed();
    validateKey(key);
    Entry entry = lruEntries.get(key);
    if (expectedSequenceNumber != ANY_SEQUENCE_NUMBER && (entry == null
        || entry.sequenceNumber != expectedSequenceNumber)) {
      return null; // Snapshot is stale.
    }
    if (entry == null) {
      entry = new Entry(key);
      lruEntries.put(key, entry);
    } else if (entry.currentEditor != null) {
      return null; // Another edit is in progress.
    }

    Editor editor = new Editor(entry);
    entry.currentEditor = editor;

    // Flush the journal before creating files to prevent file leaks.
    journalWriter.write(DIRTY + ' ' + key + '\n');
    journalWriter.flush();
    return editor;
  }

  /** Returns the directory where this cache stores its data. */
  public File getDirectory() {
    return directory;
  }

  /**
   * Returns the maximum number of bytes that this cache should use to store
   * its data.
   */
  public long getMaxSize() {
    return maxSize;
  }

  /**
   * Changes the maximum number of bytes the cache can store and queues a job
   * to trim the existing store, if necessary.
   */
  public synchronized void setMaxSize(long maxSize) {
    this.maxSize = maxSize;
    executorService.submit(cleanupCallable);
  }

  /**
   * Returns the number of bytes currently being used to store the values in
   * this cache. This may be greater than the max size if a background
   * deletion is pending.
   */
  public synchronized long size() {
    return size;
  }

  private synchronized void completeEdit(Editor editor, boolean success) throws IOException {
    Entry entry = editor.entry;
    if (entry.currentEditor != editor) {
      throw new IllegalStateException();
    }

    // If this edit is creating the entry for the first time, every index must have a value.
    if (success && !entry.readable) {
      for (int i = 0; i < valueCount; i++) {
        if (!editor.written[i]) {
          editor.abort();
          throw new IllegalStateException("Newly created entry didn't create value for index " + i);
        }
        if (!entry.getDirtyFile(i).exists()) {
          editor.abort();
          return;
        }
      }
    }

    for (int i = 0; i < valueCount; i++) {
      File dirty = entry.getDirtyFile(i);
      if (success) {
        if (dirty.exists()) {
          File clean = entry.getCleanFile(i);
          dirty.renameTo(clean);
          long oldLength = entry.lengths[i];
          long newLength = clean.length();
          entry.lengths[i] = newLength;
          size = size - oldLength + newLength;
        }
      } else {
        deleteIfExists(dirty);
      }
    }

    redundantOpCount++;
    entry.currentEditor = null;
    if (entry.readable | success) {
      entry.readable = true;
      journalWriter.write(CLEAN + ' ' + entry.key + entry.getLengths() + '\n');
      if (success) {
        entry.sequenceNumber = nextSequenceNumber++;
      }
    } else {
      lruEntries.remove(entry.key);
      journalWriter.write(REMOVE + ' ' + entry.key + '\n');
    }
    journalWriter.flush();

    if (size > maxSize || journalRebuildRequired()) {
      executorService.submit(cleanupCallable);
    }
  }

  /**
   * We only rebuild the journal when it will halve the size of the journal
   * and eliminate at least 2000 ops.
   */
  private boolean journalRebuildRequired() {
    final int redundantOpCompactThreshold = 2000;
    return redundantOpCount >= redundantOpCompactThreshold //
        && redundantOpCount >= lruEntries.size();
  }

  /**
   * Drops the entry for {@code key} if it exists and can be removed. Entries
   * actively being edited cannot be removed.
   *
   * @return true if an entry was removed.
   */
  public synchronized boolean remove(String key) throws IOException {
    checkNotClosed();
    validateKey(key);
    Entry entry = lruEntries.get(key);
    if (entry == null || entry.currentEditor != null) {
      return false;
    }

    for (int i = 0; i < valueCount; i++) {
      File file = entry.getCleanFile(i);
      if (!file.delete()) {
        throw new IOException("failed to delete " + file);
      }
      size -= entry.lengths[i];
      entry.lengths[i] = 0;
    }

    redundantOpCount++;
    journalWriter.append(REMOVE + ' ' + key + '\n');
    lruEntries.remove(key);

    if (journalRebuildRequired()) {
      executorService.submit(cleanupCallable);
    }

    return true;
  }

  /** Returns true if this cache has been closed. */
  public boolean isClosed() {
    return journalWriter == null;
  }

  private void checkNotClosed() {
    if (journalWriter == null) {
      throw new IllegalStateException("cache is closed");
    }
  }

  /** Force buffered operations to the filesystem. */
  public synchronized void flush() throws IOException {
    checkNotClosed();
    trimToSize();
    journalWriter.flush();
  }

  /** Closes this cache. Stored values will remain on the filesystem. */
  public synchronized void close() throws IOException {
    if (journalWriter == null) {
      return; // Already closed.
    }
    for (Entry entry : new ArrayList<Entry>(lruEntries.values())) {
      if (entry.currentEditor != null) {
        entry.currentEditor.abort();
      }
    }
    trimToSize();
    journalWriter.close();
    journalWriter = null;
  }

  private void trimToSize() throws IOException {
    while (size > maxSize) {
      Map.Entry<String, Entry> toEvict = lruEntries.entrySet().iterator().next();
      remove(toEvict.getKey());
    }
  }

  /**
   * Closes the cache and deletes all of its stored values. This will delete
   * all files in the cache directory including files that weren't created by
   * the cache.
   */
  public void delete() throws IOException {
    close();
    Util.deleteContents(directory);
  }

  private void validateKey(String key) {
    Matcher matcher = LEGAL_KEY_PATTERN.matcher(key);
    if (!matcher.matches()) {
      throw new IllegalArgumentException("keys must match regex [a-z0-9_-]{1,64}: \"" + key + "\"");
    }
  }

  private static String inputStreamToString(InputStream in) throws IOException {
    return Util.readFully(new InputStreamReader(in, Util.UTF_8));
  }

  /** A snapshot of the values for an entry. */
  public final class Snapshot implements Closeable {
    private final String key;
    private final long sequenceNumber;
    private final InputStream[] ins;
    private final long[] lengths;

    private Snapshot(String key, long sequenceNumber, InputStream[] ins, long[] lengths) {
      this.key = key;
      this.sequenceNumber = sequenceNumber;
      this.ins = ins;
      this.lengths = lengths;
    }

    /**
     * Returns an editor for this snapshot's entry, or null if either the
     * entry has changed since this snapshot was created or if another edit
     * is in progress.
     */
    public Editor edit() throws IOException {
      return DiskLruCache.this.edit(key, sequenceNumber);
    }

    /** Returns the unbuffered stream with the value for {@code index}. */
    public InputStream getInputStream(int index) {
      return ins[index];
    }

    /** Returns the string value for {@code index}. */
    public String getString(int index) throws IOException {
      return inputStreamToString(getInputStream(index));
    }

    /** Returns the byte length of the value for {@code index}. */
    public long getLength(int index) {
      return lengths[index];
    }

    public void close() {
      for (InputStream in : ins) {
        Util.closeQuietly(in);
      }
    }
  }

  private static final OutputStream NULL_OUTPUT_STREAM = new OutputStream() {
    @Override
    public void write(int b) throws IOException {
      // Eat all writes silently. Nom nom.
    }
  };

  /** Edits the values for an entry. */
  public final class Editor {
    private final Entry entry;
    private final boolean[] written;
    private boolean hasErrors;
    private boolean committed;

    private Editor(Entry entry) {
      this.entry = entry;
      this.written = (entry.readable) ? null : new boolean[valueCount];
    }

    /**
     * Returns an unbuffered input stream to read the last committed value,
     * or null if no value has been committed.
     */
    public InputStream newInputStream(int index) throws IOException {
      synchronized (DiskLruCache.this) {
        if (entry.currentEditor != this) {
          throw new IllegalStateException();
        }
        if (!entry.readable) {
          return null;
        }
        try {
          return new FileInputStream(entry.getCleanFile(index));
        } catch (FileNotFoundException e) {
          return null;
        }
      }
    }

    /**
     * Returns the last committed value as a string, or null if no value
     * has been committed.
     */
    public String getString(int index) throws IOException {
      InputStream in = newInputStream(index);
      return in != null ? inputStreamToString(in) : null;
    }

    /**
     * Returns a new unbuffered output stream to write the value at
     * {@code index}. If the underlying output stream encounters errors
     * when writing to the filesystem, this edit will be aborted when
     * {@link #commit} is called. The returned output stream does not throw
     * IOExceptions.
     */
    public OutputStream newOutputStream(int index) throws IOException {
      synchronized (DiskLruCache.this) {
        if (entry.currentEditor != this) {
          throw new IllegalStateException();
        }
        if (!entry.readable) {
          written[index] = true;
        }
        File dirtyFile = entry.getDirtyFile(index);
        FileOutputStream outputStream;
        try {
          outputStream = new FileOutputStream(dirtyFile);
        } catch (FileNotFoundException e) {
          // Attempt to recreate the cache directory.
          directory.mkdirs();
          try {
            outputStream = new FileOutputStream(dirtyFile);
          } catch (FileNotFoundException e2) {
            // We are unable to recover. Silently eat the writes.
            return NULL_OUTPUT_STREAM;
          }
        }
        return new FaultHidingOutputStream(outputStream);
      }
    }

    /** Sets the value at {@code index} to {@code value}. */
    public void set(int index, String value) throws IOException {
      Writer writer = null;
      try {
        writer = new OutputStreamWriter(newOutputStream(index), Util.UTF_8);
        writer.write(value);
      } finally {
        Util.closeQuietly(writer);
      }
    }

    /**
     * Commits this edit so it is visible to readers.  This releases the
     * edit lock so another edit may be started on the same key.
     */
    public void commit() throws IOException {
      if (hasErrors) {
        completeEdit(this, false);
        remove(entry.key); // The previous entry is stale.
      } else {
        completeEdit(this, true);
      }
      committed = true;
    }

    /**
     * Aborts this edit. This releases the edit lock so another edit may be
     * started on the same key.
     */
    public void abort() throws IOException {
      completeEdit(this, false);
    }

    public void abortUnlessCommitted() {
      if (!committed) {
        try {
          abort();
        } catch (IOException ignored) {
        }
      }
    }

    private class FaultHidingOutputStream extends FilterOutputStream {
      private FaultHidingOutputStream(OutputStream out) {
        super(out);
      }

      @Override public void write(int oneByte) {
        try {
          out.write(oneByte);
        } catch (IOException e) {
          hasErrors = true;
        }
      }

      @Override public void write(byte[] buffer, int offset, int length) {
        try {
          out.write(buffer, offset, length);
        } catch (IOException e) {
          hasErrors = true;
        }
      }

      @Override public void close() {
        try {
          out.close();
        } catch (IOException e) {
          hasErrors = true;
        }
      }

      @Override public void flush() {
        try {
          out.flush();
        } catch (IOException e) {
          hasErrors = true;
        }
      }
    }
  }

  private final class Entry {
    private final String key;

    /** Lengths of this entry's files. */
    private final long[] lengths;

    /** True if this entry has ever been published. */
    private boolean readable;

    /** The ongoing edit or null if this entry is not being edited. */
    private Editor currentEditor;

    /** The sequence number of the most recently committed edit to this entry. */
    private long sequenceNumber;

    private Entry(String key) {
      this.key = key;
      this.lengths = new long[valueCount];
    }

    public String getLengths() throws IOException {
      StringBuilder result = new StringBuilder();
      for (long size : lengths) {
        result.append(' ').append(size);
      }
      return result.toString();
    }

    /** Set lengths using decimal numbers like "10123". */
    private void setLengths(String[] strings) throws IOException {
      if (strings.length != valueCount) {
        throw invalidLengths(strings);
      }

      try {
        for (int i = 0; i < strings.length; i++) {
          lengths[i] = Long.parseLong(strings[i]);
        }
      } catch (NumberFormatException e) {
        throw invalidLengths(strings);
      }
    }

    private IOException invalidLengths(String[] strings) throws IOException {
      throw new IOException("unexpected journal line: " + java.util.Arrays.toString(strings));
    }

    public File getCleanFile(int i) {
      return new File(directory, key + "." + i);
    }

    public File getDirtyFile(int i) {
      return new File(directory, key + "." + i + ".tmp");
    }
  }
}


File: platforms/android/CordovaLib/src/com/squareup/okhttp/internal/Dns.java
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
package com.squareup.okhttp.internal;

import java.net.InetAddress;
import java.net.UnknownHostException;

/**
 * Domain name service. Prefer this over {@link InetAddress#getAllByName} to
 * make code more testable.
 */
public interface Dns {
  Dns DEFAULT = new Dns() {
    @Override public InetAddress[] getAllByName(String host) throws UnknownHostException {
      return InetAddress.getAllByName(host);
    }
  };

  InetAddress[] getAllByName(String host) throws UnknownHostException;
}


File: platforms/android/CordovaLib/src/com/squareup/okhttp/internal/FaultRecoveringOutputStream.java
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
package com.squareup.okhttp.internal;

import java.io.ByteArrayOutputStream;
import java.io.IOException;
import java.io.OutputStream;

import static com.squareup.okhttp.internal.Util.checkOffsetAndCount;

/**
 * An output stream wrapper that recovers from failures in the underlying stream
 * by replacing it with another stream. This class buffers a fixed amount of
 * data under the assumption that failures occur early in a stream's life.
 * If a failure occurs after the buffer has been exhausted, no recovery is
 * attempted.
 *
 * <p>Subclasses must override {@link #replacementStream} which will request a
 * replacement stream each time an {@link IOException} is encountered on the
 * current stream.
 */
public abstract class FaultRecoveringOutputStream extends AbstractOutputStream {
  private final int maxReplayBufferLength;

  /** Bytes to transmit on the replacement stream, or null if no recovery is possible. */
  private ByteArrayOutputStream replayBuffer;
  private OutputStream out;

  /**
   * @param maxReplayBufferLength the maximum number of successfully written
   *     bytes to buffer so they can be replayed in the event of an error.
   *     Failure recoveries are not possible once this limit has been exceeded.
   */
  public FaultRecoveringOutputStream(int maxReplayBufferLength, OutputStream out) {
    if (maxReplayBufferLength < 0) throw new IllegalArgumentException();
    this.maxReplayBufferLength = maxReplayBufferLength;
    this.replayBuffer = new ByteArrayOutputStream(maxReplayBufferLength);
    this.out = out;
  }

  @Override public final void write(byte[] buffer, int offset, int count) throws IOException {
    if (closed) throw new IOException("stream closed");
    checkOffsetAndCount(buffer.length, offset, count);

    while (true) {
      try {
        out.write(buffer, offset, count);

        if (replayBuffer != null) {
          if (count + replayBuffer.size() > maxReplayBufferLength) {
            // Failure recovery is no longer possible once we overflow the replay buffer.
            replayBuffer = null;
          } else {
            // Remember the written bytes to the replay buffer.
            replayBuffer.write(buffer, offset, count);
          }
        }
        return;
      } catch (IOException e) {
        if (!recover(e)) throw e;
      }
    }
  }

  @Override public final void flush() throws IOException {
    if (closed) {
      return; // don't throw; this stream might have been closed on the caller's behalf
    }
    while (true) {
      try {
        out.flush();
        return;
      } catch (IOException e) {
        if (!recover(e)) throw e;
      }
    }
  }

  @Override public final void close() throws IOException {
    if (closed) {
      return;
    }
    while (true) {
      try {
        out.close();
        closed = true;
        return;
      } catch (IOException e) {
        if (!recover(e)) throw e;
      }
    }
  }

  /**
   * Attempt to replace {@code out} with another equivalent stream. Returns true
   * if a suitable replacement stream was found.
   */
  private boolean recover(IOException e) {
    if (replayBuffer == null) {
      return false; // Can't recover because we've dropped data that we would need to replay.
    }

    while (true) {
      OutputStream replacementStream = null;
      try {
        replacementStream = replacementStream(e);
        if (replacementStream == null) {
          return false;
        }
        replaceStream(replacementStream);
        return true;
      } catch (IOException replacementStreamFailure) {
        // The replacement was also broken. Loop to ask for another replacement.
        Util.closeQuietly(replacementStream);
        e = replacementStreamFailure;
      }
    }
  }

  /**
   * Returns true if errors in the underlying stream can currently be recovered.
   */
  public boolean isRecoverable() {
    return replayBuffer != null;
  }

  /**
   * Replaces the current output stream with {@code replacementStream}, writing
   * any replay bytes to it if they exist. The current output stream is closed.
   */
  public final void replaceStream(OutputStream replacementStream) throws IOException {
    if (!isRecoverable()) {
      throw new IllegalStateException();
    }
    if (this.out == replacementStream) {
      return; // Don't replace a stream with itself.
    }
    replayBuffer.writeTo(replacementStream);
    Util.closeQuietly(out);
    out = replacementStream;
  }

  /**
   * Returns a replacement output stream to recover from {@code e} thrown by the
   * previous stream. Returns a new OutputStream if recovery was successful, in
   * which case all previously-written data will be replayed. Returns null if
   * the failure cannot be recovered.
   */
  protected abstract OutputStream replacementStream(IOException e) throws IOException;
}


File: platforms/android/CordovaLib/src/com/squareup/okhttp/internal/NamedRunnable.java
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

package com.squareup.okhttp.internal;

/**
 * Runnable implementation which always sets its thread name.
 */
public abstract class NamedRunnable implements Runnable {
  private final String name;

  public NamedRunnable(String format, Object... args) {
    this.name = String.format(format, args);
  }

  @Override public final void run() {
    String oldName = Thread.currentThread().getName();
    Thread.currentThread().setName(name);
    try {
      execute();
    } finally {
      Thread.currentThread().setName(oldName);
    }
  }

  protected abstract void execute();
}


File: platforms/android/CordovaLib/src/com/squareup/okhttp/internal/Platform.java
/*
 * Copyright (C) 2012 Square, Inc.
 * Copyright (C) 2012 The Android Open Source Project
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
package com.squareup.okhttp.internal;

import java.io.IOException;
import java.io.OutputStream;
import java.io.UnsupportedEncodingException;
import java.lang.reflect.Constructor;
import java.lang.reflect.InvocationHandler;
import java.lang.reflect.InvocationTargetException;
import java.lang.reflect.Method;
import java.lang.reflect.Proxy;
import java.net.InetSocketAddress;
import java.net.Socket;
import java.net.SocketException;
import java.net.URI;
import java.net.URISyntaxException;
import java.net.URL;
import java.util.ArrayList;
import java.util.List;
import java.util.logging.Level;
import java.util.logging.Logger;
import java.util.zip.Deflater;
import java.util.zip.DeflaterOutputStream;
import javax.net.ssl.SSLSocket;

/**
 * Access to Platform-specific features necessary for SPDY and advanced TLS.
 *
 * <h3>SPDY</h3>
 * SPDY requires a TLS extension called NPN (Next Protocol Negotiation) that's
 * available in Android 4.1+ and OpenJDK 7+ (with the npn-boot extension). It
 * also requires a recent version of {@code DeflaterOutputStream} that is
 * public API in Java 7 and callable via reflection in Android 4.1+.
 */
public class Platform {
  private static final Platform PLATFORM = findPlatform();

  private Constructor<DeflaterOutputStream> deflaterConstructor;

  public static Platform get() {
    return PLATFORM;
  }

  /** Prefix used on custom headers. */
  public String getPrefix() {
    return "OkHttp";
  }

  public void logW(String warning) {
    System.out.println(warning);
  }

  public void tagSocket(Socket socket) throws SocketException {
  }

  public void untagSocket(Socket socket) throws SocketException {
  }

  public URI toUriLenient(URL url) throws URISyntaxException {
    return url.toURI(); // this isn't as good as the built-in toUriLenient
  }

  /**
   * Attempt a TLS connection with useful extensions enabled. This mode
   * supports more features, but is less likely to be compatible with older
   * HTTPS servers.
   */
  public void enableTlsExtensions(SSLSocket socket, String uriHost) {
  }

  /**
   * Attempt a secure connection with basic functionality to maximize
   * compatibility. Currently this uses SSL 3.0.
   */
  public void supportTlsIntolerantServer(SSLSocket socket) {
    socket.setEnabledProtocols(new String[] {"SSLv3"});
  }

  /** Returns the negotiated protocol, or null if no protocol was negotiated. */
  public byte[] getNpnSelectedProtocol(SSLSocket socket) {
    return null;
  }

  /**
   * Sets client-supported protocols on a socket to send to a server. The
   * protocols are only sent if the socket implementation supports NPN.
   */
  public void setNpnProtocols(SSLSocket socket, byte[] npnProtocols) {
  }

  public void connectSocket(Socket socket, InetSocketAddress address,
      int connectTimeout) throws IOException {
    socket.connect(address, connectTimeout);
  }

  /**
   * Returns a deflater output stream that supports SYNC_FLUSH for SPDY name
   * value blocks. This throws an {@link UnsupportedOperationException} on
   * Java 6 and earlier where there is no built-in API to do SYNC_FLUSH.
   */
  public OutputStream newDeflaterOutputStream(OutputStream out, Deflater deflater,
      boolean syncFlush) {
    try {
      Constructor<DeflaterOutputStream> constructor = deflaterConstructor;
      if (constructor == null) {
        constructor = deflaterConstructor = DeflaterOutputStream.class.getConstructor(
            OutputStream.class, Deflater.class, boolean.class);
      }
      return constructor.newInstance(out, deflater, syncFlush);
    } catch (NoSuchMethodException e) {
      throw new UnsupportedOperationException("Cannot SPDY; no SYNC_FLUSH available");
    } catch (InvocationTargetException e) {
      throw e.getCause() instanceof RuntimeException ? (RuntimeException) e.getCause()
          : new RuntimeException(e.getCause());
    } catch (InstantiationException e) {
      throw new RuntimeException(e);
    } catch (IllegalAccessException e) {
      throw new AssertionError();
    }
  }

  /** Attempt to match the host runtime to a capable Platform implementation. */
  private static Platform findPlatform() {
    // Attempt to find Android 2.3+ APIs.
    Class<?> openSslSocketClass;
    Method setUseSessionTickets;
    Method setHostname;
    try {
      try {
        openSslSocketClass = Class.forName("com.android.org.conscrypt.OpenSSLSocketImpl");
      } catch (ClassNotFoundException ignored) {
        // Older platform before being unbundled.
        openSslSocketClass = Class.forName(
            "org.apache.harmony.xnet.provider.jsse.OpenSSLSocketImpl");
      }

      setUseSessionTickets = openSslSocketClass.getMethod("setUseSessionTickets", boolean.class);
      setHostname = openSslSocketClass.getMethod("setHostname", String.class);

      // Attempt to find Android 4.1+ APIs.
      try {
        Method setNpnProtocols = openSslSocketClass.getMethod("setNpnProtocols", byte[].class);
        Method getNpnSelectedProtocol = openSslSocketClass.getMethod("getNpnSelectedProtocol");
        return new Android41(openSslSocketClass, setUseSessionTickets, setHostname,
            setNpnProtocols, getNpnSelectedProtocol);
      } catch (NoSuchMethodException ignored) {
        return new Android23(openSslSocketClass, setUseSessionTickets, setHostname);
      }
    } catch (ClassNotFoundException ignored) {
      // This isn't an Android runtime.
    } catch (NoSuchMethodException ignored) {
      // This isn't Android 2.3 or better.
    }

    // Attempt to find the Jetty's NPN extension for OpenJDK.
    try {
      String npnClassName = "org.eclipse.jetty.npn.NextProtoNego";
      Class<?> nextProtoNegoClass = Class.forName(npnClassName);
      Class<?> providerClass = Class.forName(npnClassName + "$Provider");
      Class<?> clientProviderClass = Class.forName(npnClassName + "$ClientProvider");
      Class<?> serverProviderClass = Class.forName(npnClassName + "$ServerProvider");
      Method putMethod = nextProtoNegoClass.getMethod("put", SSLSocket.class, providerClass);
      Method getMethod = nextProtoNegoClass.getMethod("get", SSLSocket.class);
      return new JdkWithJettyNpnPlatform(
          putMethod, getMethod, clientProviderClass, serverProviderClass);
    } catch (ClassNotFoundException ignored) {
      // NPN isn't on the classpath.
    } catch (NoSuchMethodException ignored) {
      // The NPN version isn't what we expect.
    }

    return new Platform();
  }

  /** Android version 2.3 and newer support TLS session tickets and server name indication (SNI). */
  private static class Android23 extends Platform {
    protected final Class<?> openSslSocketClass;
    private final Method setUseSessionTickets;
    private final Method setHostname;

    private Android23(
        Class<?> openSslSocketClass, Method setUseSessionTickets, Method setHostname) {
      this.openSslSocketClass = openSslSocketClass;
      this.setUseSessionTickets = setUseSessionTickets;
      this.setHostname = setHostname;
    }

    @Override public void connectSocket(Socket socket, InetSocketAddress address,
        int connectTimeout) throws IOException {
      try {
        socket.connect(address, connectTimeout);
      } catch (SecurityException se) {
        // Before android 4.3, socket.connect could throw a SecurityException
        // if opening a socket resulted in an EACCES error.
        IOException ioException = new IOException("Exception in connect");
        ioException.initCause(se);
        throw ioException;
      }
    }

    @Override public void enableTlsExtensions(SSLSocket socket, String uriHost) {
      super.enableTlsExtensions(socket, uriHost);
      if (openSslSocketClass.isInstance(socket)) {
        // This is Android: use reflection on OpenSslSocketImpl.
        try {
          setUseSessionTickets.invoke(socket, true);
          setHostname.invoke(socket, uriHost);
        } catch (InvocationTargetException e) {
          throw new RuntimeException(e);
        } catch (IllegalAccessException e) {
          throw new AssertionError(e);
        }
      }
    }
  }

  /** Android version 4.1 and newer support NPN. */
  private static class Android41 extends Android23 {
    private final Method setNpnProtocols;
    private final Method getNpnSelectedProtocol;

    private Android41(Class<?> openSslSocketClass, Method setUseSessionTickets, Method setHostname,
        Method setNpnProtocols, Method getNpnSelectedProtocol) {
      super(openSslSocketClass, setUseSessionTickets, setHostname);
      this.setNpnProtocols = setNpnProtocols;
      this.getNpnSelectedProtocol = getNpnSelectedProtocol;
    }

    @Override public void setNpnProtocols(SSLSocket socket, byte[] npnProtocols) {
      if (!openSslSocketClass.isInstance(socket)) {
        return;
      }
      try {
        setNpnProtocols.invoke(socket, new Object[] {npnProtocols});
      } catch (IllegalAccessException e) {
        throw new AssertionError(e);
      } catch (InvocationTargetException e) {
        throw new RuntimeException(e);
      }
    }

    @Override public byte[] getNpnSelectedProtocol(SSLSocket socket) {
      if (!openSslSocketClass.isInstance(socket)) {
        return null;
      }
      try {
        return (byte[]) getNpnSelectedProtocol.invoke(socket);
      } catch (InvocationTargetException e) {
        throw new RuntimeException(e);
      } catch (IllegalAccessException e) {
        throw new AssertionError(e);
      }
    }
  }

  /** OpenJDK 7 plus {@code org.mortbay.jetty.npn/npn-boot} on the boot class path. */
  private static class JdkWithJettyNpnPlatform extends Platform {
    private final Method getMethod;
    private final Method putMethod;
    private final Class<?> clientProviderClass;
    private final Class<?> serverProviderClass;

    public JdkWithJettyNpnPlatform(Method putMethod, Method getMethod, Class<?> clientProviderClass,
        Class<?> serverProviderClass) {
      this.putMethod = putMethod;
      this.getMethod = getMethod;
      this.clientProviderClass = clientProviderClass;
      this.serverProviderClass = serverProviderClass;
    }

    @Override public void setNpnProtocols(SSLSocket socket, byte[] npnProtocols) {
      try {
        List<String> strings = new ArrayList<String>();
        for (int i = 0; i < npnProtocols.length; ) {
          int length = npnProtocols[i++];
          strings.add(new String(npnProtocols, i, length, "US-ASCII"));
          i += length;
        }
        Object provider = Proxy.newProxyInstance(Platform.class.getClassLoader(),
            new Class[] {clientProviderClass, serverProviderClass},
            new JettyNpnProvider(strings));
        putMethod.invoke(null, socket, provider);
      } catch (UnsupportedEncodingException e) {
        throw new AssertionError(e);
      } catch (InvocationTargetException e) {
        throw new AssertionError(e);
      } catch (IllegalAccessException e) {
        throw new AssertionError(e);
      }
    }

    @Override public byte[] getNpnSelectedProtocol(SSLSocket socket) {
      try {
        JettyNpnProvider provider =
            (JettyNpnProvider) Proxy.getInvocationHandler(getMethod.invoke(null, socket));
        if (!provider.unsupported && provider.selected == null) {
          Logger logger = Logger.getLogger("com.squareup.okhttp.OkHttpClient");
          logger.log(Level.INFO,
              "NPN callback dropped so SPDY is disabled. " + "Is npn-boot on the boot class path?");
          return null;
        }
        return provider.unsupported ? null : provider.selected.getBytes("US-ASCII");
      } catch (UnsupportedEncodingException e) {
        throw new AssertionError();
      } catch (InvocationTargetException e) {
        throw new AssertionError();
      } catch (IllegalAccessException e) {
        throw new AssertionError();
      }
    }
  }

  /**
   * Handle the methods of NextProtoNego's ClientProvider and ServerProvider
   * without a compile-time dependency on those interfaces.
   */
  private static class JettyNpnProvider implements InvocationHandler {
    private final List<String> protocols;
    private boolean unsupported;
    private String selected;

    public JettyNpnProvider(List<String> protocols) {
      this.protocols = protocols;
    }

    @Override public Object invoke(Object proxy, Method method, Object[] args) throws Throwable {
      String methodName = method.getName();
      Class<?> returnType = method.getReturnType();
      if (args == null) {
        args = Util.EMPTY_STRING_ARRAY;
      }
      if (methodName.equals("supports") && boolean.class == returnType) {
        return true;
      } else if (methodName.equals("unsupported") && void.class == returnType) {
        this.unsupported = true;
        return null;
      } else if (methodName.equals("protocols") && args.length == 0) {
        return protocols;
      } else if (methodName.equals("selectProtocol")
          && String.class == returnType
          && args.length == 1
          && (args[0] == null || args[0] instanceof List)) {
        // TODO: use OpenSSL's algorithm which uses both lists
        List<?> serverProtocols = (List) args[0];
        this.selected = protocols.get(0);
        return selected;
      } else if (methodName.equals("protocolSelected") && args.length == 1) {
        this.selected = (String) args[0];
        return null;
      } else {
        return method.invoke(this, args);
      }
    }
  }
}


File: platforms/android/CordovaLib/src/com/squareup/okhttp/internal/StrictLineReader.java
/*
 * Copyright (C) 2012 The Android Open Source Project
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

package com.squareup.okhttp.internal;

import java.io.ByteArrayOutputStream;
import java.io.Closeable;
import java.io.EOFException;
import java.io.IOException;
import java.io.InputStream;
import java.io.UnsupportedEncodingException;
import java.nio.charset.Charset;

/**
 * Buffers input from an {@link InputStream} for reading lines.
 *
 * <p>This class is used for buffered reading of lines. For purposes of this class, a line ends with
 * "\n" or "\r\n". End of input is reported by throwing {@code EOFException}. Unterminated line at
 * end of input is invalid and will be ignored, the caller may use {@code hasUnterminatedLine()}
 * to detect it after catching the {@code EOFException}.
 *
 * <p>This class is intended for reading input that strictly consists of lines, such as line-based
 * cache entries or cache journal. Unlike the {@link java.io.BufferedReader} which in conjunction
 * with {@link java.io.InputStreamReader} provides similar functionality, this class uses different
 * end-of-input reporting and a more restrictive definition of a line.
 *
 * <p>This class supports only charsets that encode '\r' and '\n' as a single byte with value 13
 * and 10, respectively, and the representation of no other character contains these values.
 * We currently check in constructor that the charset is one of US-ASCII, UTF-8 and ISO-8859-1.
 * The default charset is US_ASCII.
 */
public class StrictLineReader implements Closeable {
  private static final byte CR = (byte) '\r';
  private static final byte LF = (byte) '\n';

  private final InputStream in;
  private final Charset charset;

  /*
   * Buffered data is stored in {@code buf}. As long as no exception occurs, 0 <= pos <= end
   * and the data in the range [pos, end) is buffered for reading. At end of input, if there is
   * an unterminated line, we set end == -1, otherwise end == pos. If the underlying
   * {@code InputStream} throws an {@code IOException}, end may remain as either pos or -1.
   */
  private byte[] buf;
  private int pos;
  private int end;

  /**
   * Constructs a new {@code LineReader} with the specified charset and the default capacity.
   *
   * @param in the {@code InputStream} to read data from.
   * @param charset the charset used to decode data. Only US-ASCII, UTF-8 and ISO-8859-1 are
   *     supported.
   * @throws NullPointerException if {@code in} or {@code charset} is null.
   * @throws IllegalArgumentException if the specified charset is not supported.
   */
  public StrictLineReader(InputStream in, Charset charset) {
    this(in, 8192, charset);
  }

  /**
   * Constructs a new {@code LineReader} with the specified capacity and charset.
   *
   * @param in the {@code InputStream} to read data from.
   * @param capacity the capacity of the buffer.
   * @param charset the charset used to decode data. Only US-ASCII, UTF-8 and ISO-8859-1 are
   *     supported.
   * @throws NullPointerException if {@code in} or {@code charset} is null.
   * @throws IllegalArgumentException if {@code capacity} is negative or zero
   *     or the specified charset is not supported.
   */
  public StrictLineReader(InputStream in, int capacity, Charset charset) {
    if (in == null || charset == null) {
      throw new NullPointerException();
    }
    if (capacity < 0) {
      throw new IllegalArgumentException("capacity <= 0");
    }
    if (!(charset.equals(Util.US_ASCII))) {
      throw new IllegalArgumentException("Unsupported encoding");
    }

    this.in = in;
    this.charset = charset;
    buf = new byte[capacity];
  }

  /**
   * Closes the reader by closing the underlying {@code InputStream} and
   * marking this reader as closed.
   *
   * @throws IOException for errors when closing the underlying {@code InputStream}.
   */
  public void close() throws IOException {
    synchronized (in) {
      if (buf != null) {
        buf = null;
        in.close();
      }
    }
  }

  /**
   * Reads the next line. A line ends with {@code "\n"} or {@code "\r\n"},
   * this end of line marker is not included in the result.
   *
   * @return the next line from the input.
   * @throws IOException for underlying {@code InputStream} errors.
   * @throws EOFException for the end of source stream.
   */
  public String readLine() throws IOException {
    synchronized (in) {
      if (buf == null) {
        throw new IOException("LineReader is closed");
      }

      // Read more data if we are at the end of the buffered data.
      // Though it's an error to read after an exception, we will let {@code fillBuf()}
      // throw again if that happens; thus we need to handle end == -1 as well as end == pos.
      if (pos >= end) {
        fillBuf();
      }
      // Try to find LF in the buffered data and return the line if successful.
      for (int i = pos; i != end; ++i) {
        if (buf[i] == LF) {
          int lineEnd = (i != pos && buf[i - 1] == CR) ? i - 1 : i;
          String res = new String(buf, pos, lineEnd - pos, charset.name());
          pos = i + 1;
          return res;
        }
      }

      // Let's anticipate up to 80 characters on top of those already read.
      ByteArrayOutputStream out = new ByteArrayOutputStream(end - pos + 80) {
        @Override public String toString() {
          int length = (count > 0 && buf[count - 1] == CR) ? count - 1 : count;
          try {
            return new String(buf, 0, length, charset.name());
          } catch (UnsupportedEncodingException e) {
            throw new AssertionError(e); // Since we control the charset this will never happen.
          }
        }
      };

      while (true) {
        out.write(buf, pos, end - pos);
        // Mark unterminated line in case fillBuf throws EOFException or IOException.
        end = -1;
        fillBuf();
        // Try to find LF in the buffered data and return the line if successful.
        for (int i = pos; i != end; ++i) {
          if (buf[i] == LF) {
            if (i != pos) {
              out.write(buf, pos, i - pos);
            }
            pos = i + 1;
            return out.toString();
          }
        }
      }
    }
  }

  /**
   * Read an {@code int} from a line containing its decimal representation.
   *
   * @return the value of the {@code int} from the next line.
   * @throws IOException for underlying {@code InputStream} errors or conversion error.
   * @throws EOFException for the end of source stream.
   */
  public int readInt() throws IOException {
    String intString = readLine();
    try {
      return Integer.parseInt(intString);
    } catch (NumberFormatException e) {
      throw new IOException("expected an int but was \"" + intString + "\"");
    }
  }

  /**
   * Reads new input data into the buffer. Call only with pos == end or end == -1,
   * depending on the desired outcome if the function throws.
   */
  private void fillBuf() throws IOException {
    int result = in.read(buf, 0, buf.length);
    if (result == -1) {
      throw new EOFException();
    }
    pos = 0;
    end = result;
  }
}



File: platforms/android/CordovaLib/src/com/squareup/okhttp/internal/Util.java
/*
 * Copyright (C) 2012 The Android Open Source Project
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

package com.squareup.okhttp.internal;

import java.io.Closeable;
import java.io.EOFException;
import java.io.File;
import java.io.IOException;
import java.io.InputStream;
import java.io.OutputStream;
import java.io.Reader;
import java.io.StringWriter;
import java.io.UnsupportedEncodingException;
import java.net.Socket;
import java.net.ServerSocket;
import java.net.URI;
import java.net.URL;
import java.nio.ByteOrder;
import java.nio.charset.Charset;
import java.security.MessageDigest;
import java.security.NoSuchAlgorithmException;
import java.util.ArrayList;
import java.util.Collections;
import java.util.List;
import java.util.concurrent.ThreadFactory;
import java.util.concurrent.atomic.AtomicReference;

/** Junk drawer of utility methods. */
public final class Util {
  public static final byte[] EMPTY_BYTE_ARRAY = new byte[0];
  public static final String[] EMPTY_STRING_ARRAY = new String[0];

  /** A cheap and type-safe constant for the ISO-8859-1 Charset. */
  public static final Charset ISO_8859_1 = Charset.forName("ISO-8859-1");

  /** A cheap and type-safe constant for the US-ASCII Charset. */
  public static final Charset US_ASCII = Charset.forName("US-ASCII");

  /** A cheap and type-safe constant for the UTF-8 Charset. */
  public static final Charset UTF_8 = Charset.forName("UTF-8");
  private static AtomicReference<byte[]> skipBuffer = new AtomicReference<byte[]>();

  private static final char[] DIGITS =
      { '0', '1', '2', '3', '4', '5', '6', '7', '8', '9', 'a', 'b', 'c', 'd', 'e', 'f' };

  private Util() {
  }

  public static int getEffectivePort(URI uri) {
    return getEffectivePort(uri.getScheme(), uri.getPort());
  }

  public static int getEffectivePort(URL url) {
    return getEffectivePort(url.getProtocol(), url.getPort());
  }

  private static int getEffectivePort(String scheme, int specifiedPort) {
    return specifiedPort != -1 ? specifiedPort : getDefaultPort(scheme);
  }

  public static int getDefaultPort(String scheme) {
    if ("http".equalsIgnoreCase(scheme)) {
      return 80;
    } else if ("https".equalsIgnoreCase(scheme)) {
      return 443;
    } else {
      return -1;
    }
  }

  public static void checkOffsetAndCount(int arrayLength, int offset, int count) {
    if ((offset | count) < 0 || offset > arrayLength || arrayLength - offset < count) {
      throw new ArrayIndexOutOfBoundsException();
    }
  }

  public static void pokeInt(byte[] dst, int offset, int value, ByteOrder order) {
    if (order == ByteOrder.BIG_ENDIAN) {
      dst[offset++] = (byte) ((value >> 24) & 0xff);
      dst[offset++] = (byte) ((value >> 16) & 0xff);
      dst[offset++] = (byte) ((value >> 8) & 0xff);
      dst[offset] = (byte) ((value >> 0) & 0xff);
    } else {
      dst[offset++] = (byte) ((value >> 0) & 0xff);
      dst[offset++] = (byte) ((value >> 8) & 0xff);
      dst[offset++] = (byte) ((value >> 16) & 0xff);
      dst[offset] = (byte) ((value >> 24) & 0xff);
    }
  }

  /** Returns true if two possibly-null objects are equal. */
  public static boolean equal(Object a, Object b) {
    return a == b || (a != null && a.equals(b));
  }

  /**
   * Closes {@code closeable}, ignoring any checked exceptions. Does nothing
   * if {@code closeable} is null.
   */
  public static void closeQuietly(Closeable closeable) {
    if (closeable != null) {
      try {
        closeable.close();
      } catch (RuntimeException rethrown) {
        throw rethrown;
      } catch (Exception ignored) {
      }
    }
  }

  /**
   * Closes {@code socket}, ignoring any checked exceptions. Does nothing if
   * {@code socket} is null.
   */
  public static void closeQuietly(Socket socket) {
    if (socket != null) {
      try {
        socket.close();
      } catch (RuntimeException rethrown) {
        throw rethrown;
      } catch (Exception ignored) {
      }
    }
  }

  /**
   * Closes {@code serverSocket}, ignoring any checked exceptions. Does nothing if
   * {@code serverSocket} is null.
   */
  public static void closeQuietly(ServerSocket serverSocket) {
    if (serverSocket != null) {
      try {
        serverSocket.close();
      } catch (RuntimeException rethrown) {
        throw rethrown;
      } catch (Exception ignored) {
      }
    }
  }

  /**
   * Closes {@code a} and {@code b}. If either close fails, this completes
   * the other close and rethrows the first encountered exception.
   */
  public static void closeAll(Closeable a, Closeable b) throws IOException {
    Throwable thrown = null;
    try {
      a.close();
    } catch (Throwable e) {
      thrown = e;
    }
    try {
      b.close();
    } catch (Throwable e) {
      if (thrown == null) thrown = e;
    }
    if (thrown == null) return;
    if (thrown instanceof IOException) throw (IOException) thrown;
    if (thrown instanceof RuntimeException) throw (RuntimeException) thrown;
    if (thrown instanceof Error) throw (Error) thrown;
    throw new AssertionError(thrown);
  }

  /**
   * Deletes the contents of {@code dir}. Throws an IOException if any file
   * could not be deleted, or if {@code dir} is not a readable directory.
   */
  public static void deleteContents(File dir) throws IOException {
    File[] files = dir.listFiles();
    if (files == null) {
      throw new IOException("not a readable directory: " + dir);
    }
    for (File file : files) {
      if (file.isDirectory()) {
        deleteContents(file);
      }
      if (!file.delete()) {
        throw new IOException("failed to delete file: " + file);
      }
    }
  }

  /**
   * Implements InputStream.read(int) in terms of InputStream.read(byte[], int, int).
   * InputStream assumes that you implement InputStream.read(int) and provides default
   * implementations of the others, but often the opposite is more efficient.
   */
  public static int readSingleByte(InputStream in) throws IOException {
    byte[] buffer = new byte[1];
    int result = in.read(buffer, 0, 1);
    return (result != -1) ? buffer[0] & 0xff : -1;
  }

  /**
   * Implements OutputStream.write(int) in terms of OutputStream.write(byte[], int, int).
   * OutputStream assumes that you implement OutputStream.write(int) and provides default
   * implementations of the others, but often the opposite is more efficient.
   */
  public static void writeSingleByte(OutputStream out, int b) throws IOException {
    byte[] buffer = new byte[1];
    buffer[0] = (byte) (b & 0xff);
    out.write(buffer);
  }

  /**
   * Fills 'dst' with bytes from 'in', throwing EOFException if insufficient bytes are available.
   */
  public static void readFully(InputStream in, byte[] dst) throws IOException {
    readFully(in, dst, 0, dst.length);
  }

  /**
   * Reads exactly 'byteCount' bytes from 'in' (into 'dst' at offset 'offset'), and throws
   * EOFException if insufficient bytes are available.
   *
   * Used to implement {@link java.io.DataInputStream#readFully(byte[], int, int)}.
   */
  public static void readFully(InputStream in, byte[] dst, int offset, int byteCount)
      throws IOException {
    if (byteCount == 0) {
      return;
    }
    if (in == null) {
      throw new NullPointerException("in == null");
    }
    if (dst == null) {
      throw new NullPointerException("dst == null");
    }
    checkOffsetAndCount(dst.length, offset, byteCount);
    while (byteCount > 0) {
      int bytesRead = in.read(dst, offset, byteCount);
      if (bytesRead < 0) {
        throw new EOFException();
      }
      offset += bytesRead;
      byteCount -= bytesRead;
    }
  }

  /** Returns the remainder of 'reader' as a string, closing it when done. */
  public static String readFully(Reader reader) throws IOException {
    try {
      StringWriter writer = new StringWriter();
      char[] buffer = new char[1024];
      int count;
      while ((count = reader.read(buffer)) != -1) {
        writer.write(buffer, 0, count);
      }
      return writer.toString();
    } finally {
      reader.close();
    }
  }

  public static void skipAll(InputStream in) throws IOException {
    do {
      in.skip(Long.MAX_VALUE);
    } while (in.read() != -1);
  }

  /**
   * Call {@code in.read()} repeatedly until either the stream is exhausted or
   * {@code byteCount} bytes have been read.
   *
   * <p>This method reuses the skip buffer but is careful to never use it at
   * the same time that another stream is using it. Otherwise streams that use
   * the caller's buffer for consistency checks like CRC could be clobbered by
   * other threads. A thread-local buffer is also insufficient because some
   * streams may call other streams in their skip() method, also clobbering the
   * buffer.
   */
  public static long skipByReading(InputStream in, long byteCount) throws IOException {
    if (byteCount == 0) return 0L;

    // acquire the shared skip buffer.
    byte[] buffer = skipBuffer.getAndSet(null);
    if (buffer == null) {
      buffer = new byte[4096];
    }

    long skipped = 0;
    while (skipped < byteCount) {
      int toRead = (int) Math.min(byteCount - skipped, buffer.length);
      int read = in.read(buffer, 0, toRead);
      if (read == -1) {
        break;
      }
      skipped += read;
      if (read < toRead) {
        break;
      }
    }

    // release the shared skip buffer.
    skipBuffer.set(buffer);

    return skipped;
  }

  /**
   * Copies all of the bytes from {@code in} to {@code out}. Neither stream is closed.
   * Returns the total number of bytes transferred.
   */
  public static int copy(InputStream in, OutputStream out) throws IOException {
    int total = 0;
    byte[] buffer = new byte[8192];
    int c;
    while ((c = in.read(buffer)) != -1) {
      total += c;
      out.write(buffer, 0, c);
    }
    return total;
  }

  /**
   * Returns the ASCII characters up to but not including the next "\r\n", or
   * "\n".
   *
   * @throws java.io.EOFException if the stream is exhausted before the next newline
   * character.
   */
  public static String readAsciiLine(InputStream in) throws IOException {
    // TODO: support UTF-8 here instead
    StringBuilder result = new StringBuilder(80);
    while (true) {
      int c = in.read();
      if (c == -1) {
        throw new EOFException();
      } else if (c == '\n') {
        break;
      }

      result.append((char) c);
    }
    int length = result.length();
    if (length > 0 && result.charAt(length - 1) == '\r') {
      result.setLength(length - 1);
    }
    return result.toString();
  }

  /** Returns a 32 character string containing a hash of {@code s}. */
  public static String hash(String s) {
    try {
      MessageDigest messageDigest = MessageDigest.getInstance("MD5");
      byte[] md5bytes = messageDigest.digest(s.getBytes("UTF-8"));
      return bytesToHexString(md5bytes);
    } catch (NoSuchAlgorithmException e) {
      throw new AssertionError(e);
    } catch (UnsupportedEncodingException e) {
      throw new AssertionError(e);
    }
  }

  private static String bytesToHexString(byte[] bytes) {
    char[] digits = DIGITS;
    char[] buf = new char[bytes.length * 2];
    int c = 0;
    for (byte b : bytes) {
      buf[c++] = digits[(b >> 4) & 0xf];
      buf[c++] = digits[b & 0xf];
    }
    return new String(buf);
  }

  /** Returns an immutable copy of {@code list}. */
  public static <T> List<T> immutableList(List<T> list) {
    return Collections.unmodifiableList(new ArrayList<T>(list));
  }

  public static ThreadFactory daemonThreadFactory(final String name) {
    return new ThreadFactory() {
      @Override public Thread newThread(Runnable runnable) {
        Thread result = new Thread(runnable, name);
        result.setDaemon(true);
        return result;
      }
    };
  }
}


File: platforms/android/CordovaLib/src/com/squareup/okhttp/internal/http/AbstractHttpInputStream.java
/*
 * Copyright (C) 2010 The Android Open Source Project
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

import com.squareup.okhttp.internal.Util;
import java.io.IOException;
import java.io.InputStream;
import java.io.OutputStream;
import java.net.CacheRequest;

/**
 * An input stream for the body of an HTTP response.
 *
 * <p>Since a single socket's input stream may be used to read multiple HTTP
 * responses from the same server, subclasses shouldn't close the socket stream.
 *
 * <p>A side effect of reading an HTTP response is that the response cache
 * is populated. If the stream is closed early, that cache entry will be
 * invalidated.
 */
abstract class AbstractHttpInputStream extends InputStream {
  protected final InputStream in;
  protected final HttpEngine httpEngine;
  private final CacheRequest cacheRequest;
  private final OutputStream cacheBody;
  protected boolean closed;

  AbstractHttpInputStream(InputStream in, HttpEngine httpEngine, CacheRequest cacheRequest)
      throws IOException {
    this.in = in;
    this.httpEngine = httpEngine;

    OutputStream cacheBody = cacheRequest != null ? cacheRequest.getBody() : null;

    // some apps return a null body; for compatibility we treat that like a null cache request
    if (cacheBody == null) {
      cacheRequest = null;
    }

    this.cacheBody = cacheBody;
    this.cacheRequest = cacheRequest;
  }

  /**
   * read() is implemented using read(byte[], int, int) so subclasses only
   * need to override the latter.
   */
  @Override public final int read() throws IOException {
    return Util.readSingleByte(this);
  }

  protected final void checkNotClosed() throws IOException {
    if (closed) {
      throw new IOException("stream closed");
    }
  }

  protected final void cacheWrite(byte[] buffer, int offset, int count) throws IOException {
    if (cacheBody != null) {
      cacheBody.write(buffer, offset, count);
    }
  }

  /**
   * Closes the cache entry and makes the socket available for reuse. This
   * should be invoked when the end of the body has been reached.
   */
  protected final void endOfInput() throws IOException {
    if (cacheRequest != null) {
      cacheBody.close();
    }
    httpEngine.release(false);
  }

  /**
   * Calls abort on the cache entry and disconnects the socket. This
   * should be invoked when the connection is closed unexpectedly to
   * invalidate the cache entry and to prevent the HTTP connection from
   * being reused. HTTP messages are sent in serial so whenever a message
   * cannot be read to completion, subsequent messages cannot be read
   * either and the connection must be discarded.
   *
   * <p>An earlier implementation skipped the remaining bytes, but this
   * requires that the entire transfer be completed. If the intention was
   * to cancel the transfer, closing the connection is the only solution.
   */
  protected final void unexpectedEndOfInput() {
    if (cacheRequest != null) {
      cacheRequest.abort();
    }
    httpEngine.release(true);
  }
}


File: platforms/android/CordovaLib/src/com/squareup/okhttp/internal/http/HeaderParser.java
/*
 * Copyright (C) 2011 The Android Open Source Project
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

final class HeaderParser {

  public interface CacheControlHandler {
    void handle(String directive, String parameter);
  }

  /** Parse a comma-separated list of cache control header values. */
  public static void parseCacheControl(String value, CacheControlHandler handler) {
    int pos = 0;
    while (pos < value.length()) {
      int tokenStart = pos;
      pos = skipUntil(value, pos, "=,;");
      String directive = value.substring(tokenStart, pos).trim();

      if (pos == value.length() || value.charAt(pos) == ',' || value.charAt(pos) == ';') {
        pos++; // consume ',' or ';' (if necessary)
        handler.handle(directive, null);
        continue;
      }

      pos++; // consume '='
      pos = skipWhitespace(value, pos);

      String parameter;

      // quoted string
      if (pos < value.length() && value.charAt(pos) == '\"') {
        pos++; // consume '"' open quote
        int parameterStart = pos;
        pos = skipUntil(value, pos, "\"");
        parameter = value.substring(parameterStart, pos);
        pos++; // consume '"' close quote (if necessary)

        // unquoted string
      } else {
        int parameterStart = pos;
        pos = skipUntil(value, pos, ",;");
        parameter = value.substring(parameterStart, pos).trim();
      }

      handler.handle(directive, parameter);
    }
  }

  /**
   * Returns the next index in {@code input} at or after {@code pos} that
   * contains a character from {@code characters}. Returns the input length if
   * none of the requested characters can be found.
   */
  public static int skipUntil(String input, int pos, String characters) {
    for (; pos < input.length(); pos++) {
      if (characters.indexOf(input.charAt(pos)) != -1) {
        break;
      }
    }
    return pos;
  }

  /**
   * Returns the next non-whitespace character in {@code input} that is white
   * space. Result is undefined if input contains newline characters.
   */
  public static int skipWhitespace(String input, int pos) {
    for (; pos < input.length(); pos++) {
      char c = input.charAt(pos);
      if (c != ' ' && c != '\t') {
        break;
      }
    }
    return pos;
  }

  /**
   * Returns {@code value} as a positive integer, or 0 if it is negative, or
   * -1 if it cannot be parsed.
   */
  public static int parseSeconds(String value) {
    try {
      long seconds = Long.parseLong(value);
      if (seconds > Integer.MAX_VALUE) {
        return Integer.MAX_VALUE;
      } else if (seconds < 0) {
        return 0;
      } else {
        return (int) seconds;
      }
    } catch (NumberFormatException e) {
      return -1;
    }
  }

  private HeaderParser() {
  }
}


File: platforms/android/CordovaLib/src/com/squareup/okhttp/internal/http/HttpAuthenticator.java
/*
 * Copyright (C) 2012 Square, Inc.
 * Copyright (C) 2011 The Android Open Source Project
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

import com.squareup.okhttp.OkAuthenticator;
import com.squareup.okhttp.OkAuthenticator.Challenge;
import java.io.IOException;
import java.net.Authenticator;
import java.net.InetAddress;
import java.net.InetSocketAddress;
import java.net.PasswordAuthentication;
import java.net.Proxy;
import java.net.URL;
import java.util.ArrayList;
import java.util.List;

import static com.squareup.okhttp.OkAuthenticator.Credential;
import static java.net.HttpURLConnection.HTTP_PROXY_AUTH;
import static java.net.HttpURLConnection.HTTP_UNAUTHORIZED;

/** Handles HTTP authentication headers from origin and proxy servers. */
public final class HttpAuthenticator {
  /** Uses the global authenticator to get the password. */
  public static final OkAuthenticator SYSTEM_DEFAULT = new OkAuthenticator() {
    @Override public Credential authenticate(
        Proxy proxy, URL url, List<Challenge> challenges) throws IOException {
      for (Challenge challenge : challenges) {
        if (!"Basic".equalsIgnoreCase(challenge.getScheme())) {
          continue;
        }

        PasswordAuthentication auth = Authenticator.requestPasswordAuthentication(url.getHost(),
            getConnectToInetAddress(proxy, url), url.getPort(), url.getProtocol(),
            challenge.getRealm(), challenge.getScheme(), url, Authenticator.RequestorType.SERVER);
        if (auth != null) {
          return Credential.basic(auth.getUserName(), new String(auth.getPassword()));
        }
      }
      return null;
    }

    @Override public Credential authenticateProxy(
        Proxy proxy, URL url, List<Challenge> challenges) throws IOException {
      for (Challenge challenge : challenges) {
        if (!"Basic".equalsIgnoreCase(challenge.getScheme())) {
          continue;
        }

        InetSocketAddress proxyAddress = (InetSocketAddress) proxy.address();
        PasswordAuthentication auth = Authenticator.requestPasswordAuthentication(
            proxyAddress.getHostName(), getConnectToInetAddress(proxy, url), proxyAddress.getPort(),
            url.getProtocol(), challenge.getRealm(), challenge.getScheme(), url,
            Authenticator.RequestorType.PROXY);
        if (auth != null) {
          return Credential.basic(auth.getUserName(), new String(auth.getPassword()));
        }
      }
      return null;
    }

    private InetAddress getConnectToInetAddress(Proxy proxy, URL url) throws IOException {
      return (proxy != null && proxy.type() != Proxy.Type.DIRECT)
          ? ((InetSocketAddress) proxy.address()).getAddress()
          : InetAddress.getByName(url.getHost());
    }
  };

  private HttpAuthenticator() {
  }

  /**
   * React to a failed authorization response by looking up new credentials.
   *
   * @return true if credentials have been added to successorRequestHeaders
   *         and another request should be attempted.
   */
  public static boolean processAuthHeader(OkAuthenticator authenticator, int responseCode,
      RawHeaders responseHeaders, RawHeaders successorRequestHeaders, Proxy proxy, URL url)
      throws IOException {
    String responseField;
    String requestField;
    if (responseCode == HTTP_UNAUTHORIZED) {
      responseField = "WWW-Authenticate";
      requestField = "Authorization";
    } else if (responseCode == HTTP_PROXY_AUTH) {
      responseField = "Proxy-Authenticate";
      requestField = "Proxy-Authorization";
    } else {
      throw new IllegalArgumentException(); // TODO: ProtocolException?
    }
    List<Challenge> challenges = parseChallenges(responseHeaders, responseField);
    if (challenges.isEmpty()) {
      return false; // Could not find a challenge so end the request cycle.
    }
    Credential credential = responseHeaders.getResponseCode() == HTTP_PROXY_AUTH
        ? authenticator.authenticateProxy(proxy, url, challenges)
        : authenticator.authenticate(proxy, url, challenges);
    if (credential == null) {
      return false; // Could not satisfy the challenge so end the request cycle.
    }
    // Add authorization credentials, bypassing the already-connected check.
    successorRequestHeaders.set(requestField, credential.getHeaderValue());
    return true;
  }

  /**
   * Parse RFC 2617 challenges. This API is only interested in the scheme
   * name and realm.
   */
  private static List<Challenge> parseChallenges(RawHeaders responseHeaders,
      String challengeHeader) {
    // auth-scheme = token
    // auth-param  = token "=" ( token | quoted-string )
    // challenge   = auth-scheme 1*SP 1#auth-param
    // realm       = "realm" "=" realm-value
    // realm-value = quoted-string
    List<Challenge> result = new ArrayList<Challenge>();
    for (int h = 0; h < responseHeaders.length(); h++) {
      if (!challengeHeader.equalsIgnoreCase(responseHeaders.getFieldName(h))) {
        continue;
      }
      String value = responseHeaders.getValue(h);
      int pos = 0;
      while (pos < value.length()) {
        int tokenStart = pos;
        pos = HeaderParser.skipUntil(value, pos, " ");

        String scheme = value.substring(tokenStart, pos).trim();
        pos = HeaderParser.skipWhitespace(value, pos);

        // TODO: This currently only handles schemes with a 'realm' parameter;
        //       It needs to be fixed to handle any scheme and any parameters
        //       http://code.google.com/p/android/issues/detail?id=11140

        if (!value.regionMatches(true, pos, "realm=\"", 0, "realm=\"".length())) {
          break; // Unexpected challenge parameter; give up!
        }

        pos += "realm=\"".length();
        int realmStart = pos;
        pos = HeaderParser.skipUntil(value, pos, "\"");
        String realm = value.substring(realmStart, pos);
        pos++; // Consume '"' close quote.
        pos = HeaderParser.skipUntil(value, pos, ",");
        pos++; // Consume ',' comma.
        pos = HeaderParser.skipWhitespace(value, pos);
        result.add(new Challenge(scheme, realm));
      }
    }
    return result;
  }
}


File: platforms/android/CordovaLib/src/com/squareup/okhttp/internal/http/HttpDate.java
/*
 * Copyright (C) 2011 The Android Open Source Project
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

import java.text.DateFormat;
import java.text.ParseException;
import java.text.SimpleDateFormat;
import java.util.Date;
import java.util.Locale;
import java.util.TimeZone;

/**
 * Best-effort parser for HTTP dates.
 */
final class HttpDate {

  /**
   * Most websites serve cookies in the blessed format. Eagerly create the parser to ensure such
   * cookies are on the fast path.
   */
  private static final ThreadLocal<DateFormat> STANDARD_DATE_FORMAT =
      new ThreadLocal<DateFormat>() {
        @Override protected DateFormat initialValue() {
          DateFormat rfc1123 = new SimpleDateFormat("EEE, dd MMM yyyy HH:mm:ss zzz", Locale.US);
          rfc1123.setTimeZone(TimeZone.getTimeZone("GMT"));
          return rfc1123;
        }
      };

  /** If we fail to parse a date in a non-standard format, try each of these formats in sequence. */
  private static final String[] BROWSER_COMPATIBLE_DATE_FORMAT_STRINGS = new String[] {
      "EEEE, dd-MMM-yy HH:mm:ss zzz", // RFC 1036
      "EEE MMM d HH:mm:ss yyyy", // ANSI C asctime()
      "EEE, dd-MMM-yyyy HH:mm:ss z", "EEE, dd-MMM-yyyy HH-mm-ss z", "EEE, dd MMM yy HH:mm:ss z",
      "EEE dd-MMM-yyyy HH:mm:ss z", "EEE dd MMM yyyy HH:mm:ss z", "EEE dd-MMM-yyyy HH-mm-ss z",
      "EEE dd-MMM-yy HH:mm:ss z", "EEE dd MMM yy HH:mm:ss z", "EEE,dd-MMM-yy HH:mm:ss z",
      "EEE,dd-MMM-yyyy HH:mm:ss z", "EEE, dd-MM-yyyy HH:mm:ss z",

            /* RI bug 6641315 claims a cookie of this format was once served by www.yahoo.com */
      "EEE MMM d yyyy HH:mm:ss z", };

  private static final DateFormat[] BROWSER_COMPATIBLE_DATE_FORMATS =
      new DateFormat[BROWSER_COMPATIBLE_DATE_FORMAT_STRINGS.length];

  /** Returns the date for {@code value}. Returns null if the value couldn't be parsed. */
  public static Date parse(String value) {
    try {
      return STANDARD_DATE_FORMAT.get().parse(value);
    } catch (ParseException ignored) {
    }
    synchronized (BROWSER_COMPATIBLE_DATE_FORMAT_STRINGS) {
      for (int i = 0, count = BROWSER_COMPATIBLE_DATE_FORMAT_STRINGS.length; i < count; i++) {
        DateFormat format = BROWSER_COMPATIBLE_DATE_FORMATS[i];
        if (format == null) {
          format = new SimpleDateFormat(BROWSER_COMPATIBLE_DATE_FORMAT_STRINGS[i], Locale.US);
          BROWSER_COMPATIBLE_DATE_FORMATS[i] = format;
        }
        try {
          return format.parse(value);
        } catch (ParseException ignored) {
        }
      }
    }
    return null;
  }

  /** Returns the string for {@code value}. */
  public static String format(Date value) {
    return STANDARD_DATE_FORMAT.get().format(value);
  }

  private HttpDate() {
  }
}


File: platforms/android/CordovaLib/src/com/squareup/okhttp/internal/http/HttpEngine.java
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

package com.squareup.okhttp.internal.http;

import com.squareup.okhttp.Address;
import com.squareup.okhttp.Connection;
import com.squareup.okhttp.OkHttpClient;
import com.squareup.okhttp.OkResponseCache;
import com.squareup.okhttp.ResponseSource;
import com.squareup.okhttp.TunnelRequest;
import com.squareup.okhttp.internal.Dns;
import com.squareup.okhttp.internal.Platform;
import com.squareup.okhttp.internal.Util;
import java.io.ByteArrayInputStream;
import java.io.IOException;
import java.io.InputStream;
import java.io.OutputStream;
import java.net.CacheRequest;
import java.net.CacheResponse;
import java.net.CookieHandler;
import java.net.HttpURLConnection;
import java.net.Proxy;
import java.net.URI;
import java.net.URISyntaxException;
import java.net.URL;
import java.net.UnknownHostException;
import java.util.Collections;
import java.util.Date;
import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.zip.GZIPInputStream;
import javax.net.ssl.HostnameVerifier;
import javax.net.ssl.SSLSocketFactory;

import static com.squareup.okhttp.internal.Util.EMPTY_BYTE_ARRAY;
import static com.squareup.okhttp.internal.Util.getDefaultPort;
import static com.squareup.okhttp.internal.Util.getEffectivePort;

/**
 * Handles a single HTTP request/response pair. Each HTTP engine follows this
 * lifecycle:
 * <ol>
 * <li>It is created.
 * <li>The HTTP request message is sent with sendRequest(). Once the request
 * is sent it is an error to modify the request headers. After
 * sendRequest() has been called the request body can be written to if
 * it exists.
 * <li>The HTTP response message is read with readResponse(). After the
 * response has been read the response headers and body can be read.
 * All responses have a response body input stream, though in some
 * instances this stream is empty.
 * </ol>
 *
 * <p>The request and response may be served by the HTTP response cache, by the
 * network, or by both in the event of a conditional GET.
 *
 * <p>This class may hold a socket connection that needs to be released or
 * recycled. By default, this socket connection is held when the last byte of
 * the response is consumed. To release the connection when it is no longer
 * required, use {@link #automaticallyReleaseConnectionToPool()}.
 */
public class HttpEngine {
  private static final CacheResponse GATEWAY_TIMEOUT_RESPONSE = new CacheResponse() {
    @Override public Map<String, List<String>> getHeaders() throws IOException {
      Map<String, List<String>> result = new HashMap<String, List<String>>();
      result.put(null, Collections.singletonList("HTTP/1.1 504 Gateway Timeout"));
      return result;
    }
    @Override public InputStream getBody() throws IOException {
      return new ByteArrayInputStream(EMPTY_BYTE_ARRAY);
    }
  };
  public static final int HTTP_CONTINUE = 100;

  protected final Policy policy;
  protected final OkHttpClient client;

  protected final String method;

  private ResponseSource responseSource;

  protected Connection connection;
  protected RouteSelector routeSelector;
  private OutputStream requestBodyOut;

  private Transport transport;

  private InputStream responseTransferIn;
  private InputStream responseBodyIn;

  private CacheResponse cacheResponse;
  private CacheRequest cacheRequest;

  /** The time when the request headers were written, or -1 if they haven't been written yet. */
  long sentRequestMillis = -1;

  /** Whether the connection has been established. */
  boolean connected;

  /**
   * True if this client added an "Accept-Encoding: gzip" header field and is
   * therefore responsible for also decompressing the transfer stream.
   */
  private boolean transparentGzip;

  final URI uri;

  final RequestHeaders requestHeaders;

  /** Null until a response is received from the network or the cache. */
  ResponseHeaders responseHeaders;

  // The cache response currently being validated on a conditional get. Null
  // if the cached response doesn't exist or doesn't need validation. If the
  // conditional get succeeds, these will be used for the response headers and
  // body. If it fails, these be closed and set to null.
  private ResponseHeaders cachedResponseHeaders;
  private InputStream cachedResponseBody;

  /**
   * True if the socket connection should be released to the connection pool
   * when the response has been fully read.
   */
  private boolean automaticallyReleaseConnectionToPool;

  /** True if the socket connection is no longer needed by this engine. */
  private boolean connectionReleased;

  /**
   * @param requestHeaders the client's supplied request headers. This class
   *     creates a private copy that it can mutate.
   * @param connection the connection used for an intermediate response
   *     immediately prior to this request/response pair, such as a same-host
   *     redirect. This engine assumes ownership of the connection and must
   *     release it when it is unneeded.
   */
  public HttpEngine(OkHttpClient client, Policy policy, String method, RawHeaders requestHeaders,
      Connection connection, RetryableOutputStream requestBodyOut) throws IOException {
    this.client = client;
    this.policy = policy;
    this.method = method;
    this.connection = connection;
    this.requestBodyOut = requestBodyOut;

    try {
      uri = Platform.get().toUriLenient(policy.getURL());
    } catch (URISyntaxException e) {
      throw new IOException(e.getMessage());
    }

    this.requestHeaders = new RequestHeaders(uri, new RawHeaders(requestHeaders));
  }

  public URI getUri() {
    return uri;
  }

  /**
   * Figures out what the response source will be, and opens a socket to that
   * source if necessary. Prepares the request headers and gets ready to start
   * writing the request body if it exists.
   */
  public final void sendRequest() throws IOException {
    if (responseSource != null) {
      return;
    }

    prepareRawRequestHeaders();
    initResponseSource();
    OkResponseCache responseCache = client.getOkResponseCache();
    if (responseCache != null) {
      responseCache.trackResponse(responseSource);
    }

    // The raw response source may require the network, but the request
    // headers may forbid network use. In that case, dispose of the network
    // response and use a GATEWAY_TIMEOUT response instead, as specified
    // by http://www.w3.org/Protocols/rfc2616/rfc2616-sec14.html#sec14.9.4.
    if (requestHeaders.isOnlyIfCached() && responseSource.requiresConnection()) {
      if (responseSource == ResponseSource.CONDITIONAL_CACHE) {
        Util.closeQuietly(cachedResponseBody);
      }
      this.responseSource = ResponseSource.CACHE;
      this.cacheResponse = GATEWAY_TIMEOUT_RESPONSE;
      RawHeaders rawResponseHeaders = RawHeaders.fromMultimap(cacheResponse.getHeaders(), true);
      setResponse(new ResponseHeaders(uri, rawResponseHeaders), cacheResponse.getBody());
    }

    if (responseSource.requiresConnection()) {
      sendSocketRequest();
    } else if (connection != null) {
      client.getConnectionPool().recycle(connection);
      connection = null;
    }
  }

  /**
   * Initialize the source for this response. It may be corrected later if the
   * request headers forbids network use.
   */
  private void initResponseSource() throws IOException {
    responseSource = ResponseSource.NETWORK;
    if (!policy.getUseCaches()) return;

    OkResponseCache responseCache = client.getOkResponseCache();
    if (responseCache == null) return;

    CacheResponse candidate = responseCache.get(
        uri, method, requestHeaders.getHeaders().toMultimap(false));
    if (candidate == null) return;

    Map<String, List<String>> responseHeadersMap = candidate.getHeaders();
    cachedResponseBody = candidate.getBody();
    if (!acceptCacheResponseType(candidate)
        || responseHeadersMap == null
        || cachedResponseBody == null) {
      Util.closeQuietly(cachedResponseBody);
      return;
    }

    RawHeaders rawResponseHeaders = RawHeaders.fromMultimap(responseHeadersMap, true);
    cachedResponseHeaders = new ResponseHeaders(uri, rawResponseHeaders);
    long now = System.currentTimeMillis();
    this.responseSource = cachedResponseHeaders.chooseResponseSource(now, requestHeaders);
    if (responseSource == ResponseSource.CACHE) {
      this.cacheResponse = candidate;
      setResponse(cachedResponseHeaders, cachedResponseBody);
    } else if (responseSource == ResponseSource.CONDITIONAL_CACHE) {
      this.cacheResponse = candidate;
    } else if (responseSource == ResponseSource.NETWORK) {
      Util.closeQuietly(cachedResponseBody);
    } else {
      throw new AssertionError();
    }
  }

  private void sendSocketRequest() throws IOException {
    if (connection == null) {
      connect();
    }

    if (transport != null) {
      throw new IllegalStateException();
    }

    transport = (Transport) connection.newTransport(this);

    if (hasRequestBody() && requestBodyOut == null) {
      // Create a request body if we don't have one already. We'll already
      // have one if we're retrying a failed POST.
      requestBodyOut = transport.createRequestBody();
    }
  }

  /** Connect to the origin server either directly or via a proxy. */
  protected final void connect() throws IOException {
    if (connection != null) {
      return;
    }
    if (routeSelector == null) {
      String uriHost = uri.getHost();
      if (uriHost == null) {
        throw new UnknownHostException(uri.toString());
      }
      SSLSocketFactory sslSocketFactory = null;
      HostnameVerifier hostnameVerifier = null;
      if (uri.getScheme().equalsIgnoreCase("https")) {
        sslSocketFactory = client.getSslSocketFactory();
        hostnameVerifier = client.getHostnameVerifier();
      }
      Address address = new Address(uriHost, getEffectivePort(uri), sslSocketFactory,
          hostnameVerifier, client.getAuthenticator(), client.getProxy(), client.getTransports());
      routeSelector = new RouteSelector(address, uri, client.getProxySelector(),
          client.getConnectionPool(), Dns.DEFAULT, client.getRoutesDatabase());
    }
    connection = routeSelector.next(method);
    if (!connection.isConnected()) {
      connection.connect(client.getConnectTimeout(), client.getReadTimeout(), getTunnelConfig());
      client.getConnectionPool().maybeShare(connection);
      client.getRoutesDatabase().connected(connection.getRoute());
    } else if (!connection.isSpdy()) {
        connection.updateReadTimeout(client.getReadTimeout());
    }
    connected(connection);
    if (connection.getRoute().getProxy() != client.getProxy()) {
      // Update the request line if the proxy changed; it may need a host name.
      requestHeaders.getHeaders().setRequestLine(getRequestLine());
    }
  }

  /**
   * Called after a socket connection has been created or retrieved from the
   * pool. Subclasses use this hook to get a reference to the TLS data.
   */
  protected void connected(Connection connection) {
    policy.setSelectedProxy(connection.getRoute().getProxy());
    connected = true;
  }

  /**
   * Called immediately before the transport transmits HTTP request headers.
   * This is used to observe the sent time should the request be cached.
   */
  public void writingRequestHeaders() {
    if (sentRequestMillis != -1) {
      throw new IllegalStateException();
    }
    sentRequestMillis = System.currentTimeMillis();
  }

  /**
   * @param body the response body, or null if it doesn't exist or isn't
   * available.
   */
  private void setResponse(ResponseHeaders headers, InputStream body) throws IOException {
    if (this.responseBodyIn != null) {
      throw new IllegalStateException();
    }
    this.responseHeaders = headers;
    if (body != null) {
      initContentStream(body);
    }
  }

  boolean hasRequestBody() {
    return method.equals("POST") || method.equals("PUT") || method.equals("PATCH");
  }

  /** Returns the request body or null if this request doesn't have a body. */
  public final OutputStream getRequestBody() {
    if (responseSource == null) {
      throw new IllegalStateException();
    }
    return requestBodyOut;
  }

  public final boolean hasResponse() {
    return responseHeaders != null;
  }

  public final RequestHeaders getRequestHeaders() {
    return requestHeaders;
  }

  public final ResponseHeaders getResponseHeaders() {
    if (responseHeaders == null) {
      throw new IllegalStateException();
    }
    return responseHeaders;
  }

  public final int getResponseCode() {
    if (responseHeaders == null) {
      throw new IllegalStateException();
    }
    return responseHeaders.getHeaders().getResponseCode();
  }

  public final InputStream getResponseBody() {
    if (responseHeaders == null) {
      throw new IllegalStateException();
    }
    return responseBodyIn;
  }

  public final CacheResponse getCacheResponse() {
    return cacheResponse;
  }

  public final Connection getConnection() {
    return connection;
  }

  /**
   * Returns true if {@code cacheResponse} is of the right type. This
   * condition is necessary but not sufficient for the cached response to
   * be used.
   */
  protected boolean acceptCacheResponseType(CacheResponse cacheResponse) {
    return true;
  }

  private void maybeCache() throws IOException {
    // Are we caching at all?
    if (!policy.getUseCaches()) return;
    OkResponseCache responseCache = client.getOkResponseCache();
    if (responseCache == null) return;

    HttpURLConnection connectionToCache = policy.getHttpConnectionToCache();

    // Should we cache this response for this request?
    if (!responseHeaders.isCacheable(requestHeaders)) {
      responseCache.maybeRemove(connectionToCache.getRequestMethod(), uri);
      return;
    }

    // Offer this request to the cache.
    cacheRequest = responseCache.put(uri, connectionToCache);
  }

  /**
   * Cause the socket connection to be released to the connection pool when
   * it is no longer needed. If it is already unneeded, it will be pooled
   * immediately. Otherwise the connection is held so that redirects can be
   * handled by the same connection.
   */
  public final void automaticallyReleaseConnectionToPool() {
    automaticallyReleaseConnectionToPool = true;
    if (connection != null && connectionReleased) {
      client.getConnectionPool().recycle(connection);
      connection = null;
    }
  }

  /**
   * Releases this engine so that its resources may be either reused or
   * closed. Also call {@link #automaticallyReleaseConnectionToPool} unless
   * the connection will be used to follow a redirect.
   */
  public final void release(boolean streamCanceled) {
    // If the response body comes from the cache, close it.
    if (responseBodyIn == cachedResponseBody) {
      Util.closeQuietly(responseBodyIn);
    }

    if (!connectionReleased && connection != null) {
      connectionReleased = true;

      if (transport == null
          || !transport.makeReusable(streamCanceled, requestBodyOut, responseTransferIn)) {
        Util.closeQuietly(connection);
        connection = null;
      } else if (automaticallyReleaseConnectionToPool) {
        client.getConnectionPool().recycle(connection);
        connection = null;
      }
    }
  }

  private void initContentStream(InputStream transferStream) throws IOException {
    responseTransferIn = transferStream;
    if (transparentGzip && responseHeaders.isContentEncodingGzip()) {
      // If the response was transparently gzipped, remove the gzip header field
      // so clients don't double decompress. http://b/3009828
      //
      // Also remove the Content-Length in this case because it contains the
      // length 528 of the gzipped response. This isn't terribly useful and is
      // dangerous because 529 clients can query the content length, but not
      // the content encoding.
      responseHeaders.stripContentEncoding();
      responseHeaders.stripContentLength();
      responseBodyIn = new GZIPInputStream(transferStream);
    } else {
      responseBodyIn = transferStream;
    }
  }

  /**
   * Returns true if the response must have a (possibly 0-length) body.
   * See RFC 2616 section 4.3.
   */
  public final boolean hasResponseBody() {
    int responseCode = responseHeaders.getHeaders().getResponseCode();

    // HEAD requests never yield a body regardless of the response headers.
    if (method.equals("HEAD")) {
      return false;
    }

    if ((responseCode < HTTP_CONTINUE || responseCode >= 200)
        && responseCode != HttpURLConnectionImpl.HTTP_NO_CONTENT
        && responseCode != HttpURLConnectionImpl.HTTP_NOT_MODIFIED) {
      return true;
    }

    // If the Content-Length or Transfer-Encoding headers disagree with the
    // response code, the response is malformed. For best compatibility, we
    // honor the headers.
    if (responseHeaders.getContentLength() != -1 || responseHeaders.isChunked()) {
      return true;
    }

    return false;
  }

  /**
   * Populates requestHeaders with defaults and cookies.
   *
   * <p>This client doesn't specify a default {@code Accept} header because it
   * doesn't know what content types the application is interested in.
   */
  private void prepareRawRequestHeaders() throws IOException {
    requestHeaders.getHeaders().setRequestLine(getRequestLine());

    if (requestHeaders.getUserAgent() == null) {
      requestHeaders.setUserAgent(getDefaultUserAgent());
    }

    if (requestHeaders.getHost() == null) {
      requestHeaders.setHost(getOriginAddress(policy.getURL()));
    }

    if ((connection == null || connection.getHttpMinorVersion() != 0)
        && requestHeaders.getConnection() == null) {
      requestHeaders.setConnection("Keep-Alive");
    }

    if (requestHeaders.getAcceptEncoding() == null) {
      transparentGzip = true;
      requestHeaders.setAcceptEncoding("gzip");
    }

    if (hasRequestBody() && requestHeaders.getContentType() == null) {
      requestHeaders.setContentType("application/x-www-form-urlencoded");
    }

    long ifModifiedSince = policy.getIfModifiedSince();
    if (ifModifiedSince != 0) {
      requestHeaders.setIfModifiedSince(new Date(ifModifiedSince));
    }

    CookieHandler cookieHandler = client.getCookieHandler();
    if (cookieHandler != null) {
      requestHeaders.addCookies(
          cookieHandler.get(uri, requestHeaders.getHeaders().toMultimap(false)));
    }
  }

  /**
   * Returns the request status line, like "GET / HTTP/1.1". This is exposed
   * to the application by {@link HttpURLConnectionImpl#getHeaderFields}, so
   * it needs to be set even if the transport is SPDY.
   */
  String getRequestLine() {
    String protocol =
        (connection == null || connection.getHttpMinorVersion() != 0) ? "HTTP/1.1" : "HTTP/1.0";
    return method + " " + requestString() + " " + protocol;
  }

  private String requestString() {
    URL url = policy.getURL();
    if (includeAuthorityInRequestLine()) {
      return url.toString();
    } else {
      return requestPath(url);
    }
  }

  /**
   * Returns the path to request, like the '/' in 'GET / HTTP/1.1'. Never
   * empty, even if the request URL is. Includes the query component if it
   * exists.
   */
  public static String requestPath(URL url) {
    String fileOnly = url.getFile();
    if (fileOnly == null) {
      return "/";
    } else if (!fileOnly.startsWith("/")) {
      return "/" + fileOnly;
    } else {
      return fileOnly;
    }
  }

  /**
   * Returns true if the request line should contain the full URL with host
   * and port (like "GET http://android.com/foo HTTP/1.1") or only the path
   * (like "GET /foo HTTP/1.1").
   *
   * <p>This is non-final because for HTTPS it's never necessary to supply the
   * full URL, even if a proxy is in use.
   */
  protected boolean includeAuthorityInRequestLine() {
    return connection == null
        ? policy.usingProxy() // A proxy was requested.
        : connection.getRoute().getProxy().type() == Proxy.Type.HTTP; // A proxy was selected.
  }

  public static String getDefaultUserAgent() {
    String agent = System.getProperty("http.agent");
    return agent != null ? agent : ("Java" + System.getProperty("java.version"));
  }

  public static String getOriginAddress(URL url) {
    int port = url.getPort();
    String result = url.getHost();
    if (port > 0 && port != getDefaultPort(url.getProtocol())) {
      result = result + ":" + port;
    }
    return result;
  }

  /**
   * Flushes the remaining request header and body, parses the HTTP response
   * headers and starts reading the HTTP response body if it exists.
   */
  public final void readResponse() throws IOException {
    if (hasResponse()) {
      responseHeaders.setResponseSource(responseSource);
      return;
    }

    if (responseSource == null) {
      throw new IllegalStateException("readResponse() without sendRequest()");
    }

    if (!responseSource.requiresConnection()) {
      return;
    }

    if (sentRequestMillis == -1) {
      if (requestBodyOut instanceof RetryableOutputStream) {
        int contentLength = ((RetryableOutputStream) requestBodyOut).contentLength();
        requestHeaders.setContentLength(contentLength);
      }
      transport.writeRequestHeaders();
    }

    if (requestBodyOut != null) {
      requestBodyOut.close();
      if (requestBodyOut instanceof RetryableOutputStream) {
        transport.writeRequestBody((RetryableOutputStream) requestBodyOut);
      }
    }

    transport.flushRequest();

    responseHeaders = transport.readResponseHeaders();
    responseHeaders.setLocalTimestamps(sentRequestMillis, System.currentTimeMillis());
    responseHeaders.setResponseSource(responseSource);

    if (responseSource == ResponseSource.CONDITIONAL_CACHE) {
      if (cachedResponseHeaders.validate(responseHeaders)) {
        release(false);
        ResponseHeaders combinedHeaders = cachedResponseHeaders.combine(responseHeaders);
        this.responseHeaders = combinedHeaders;

        // Update the cache after applying the combined headers but before initializing the content
        // stream, otherwise the Content-Encoding header (if present) will be stripped from the
        // combined headers and not end up in the cache file if transparent gzip compression is
        // turned on.
        OkResponseCache responseCache = client.getOkResponseCache();
        responseCache.trackConditionalCacheHit();
        responseCache.update(cacheResponse, policy.getHttpConnectionToCache());

        initContentStream(cachedResponseBody);
        return;
      } else {
        Util.closeQuietly(cachedResponseBody);
      }
    }

    if (hasResponseBody()) {
      maybeCache(); // reentrant. this calls into user code which may call back into this!
    }

    initContentStream(transport.getTransferStream(cacheRequest));
  }

  protected TunnelRequest getTunnelConfig() {
    return null;
  }

  public void receiveHeaders(RawHeaders headers) throws IOException {
    CookieHandler cookieHandler = client.getCookieHandler();
    if (cookieHandler != null) {
      cookieHandler.put(uri, headers.toMultimap(true));
    }
  }
}


File: platforms/android/CordovaLib/src/com/squareup/okhttp/internal/http/HttpTransport.java
/*
 * Copyright (C) 2012 The Android Open Source Project
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

import com.squareup.okhttp.Connection;
import com.squareup.okhttp.internal.AbstractOutputStream;
import com.squareup.okhttp.internal.Util;
import java.io.ByteArrayOutputStream;
import java.io.IOException;
import java.io.InputStream;
import java.io.OutputStream;
import java.net.CacheRequest;
import java.net.ProtocolException;
import java.net.Socket;

import static com.squareup.okhttp.internal.Util.checkOffsetAndCount;

public final class HttpTransport implements Transport {
  /**
   * The timeout to use while discarding a stream of input data. Since this is
   * used for connection reuse, this timeout should be significantly less than
   * the time it takes to establish a new connection.
   */
  private static final int DISCARD_STREAM_TIMEOUT_MILLIS = 100;

  public static final int DEFAULT_CHUNK_LENGTH = 1024;

  private final HttpEngine httpEngine;
  private final InputStream socketIn;
  private final OutputStream socketOut;

  /**
   * This stream buffers the request headers and the request body when their
   * combined size is less than MAX_REQUEST_BUFFER_LENGTH. By combining them
   * we can save socket writes, which in turn saves a packet transmission.
   * This is socketOut if the request size is large or unknown.
   */
  private OutputStream requestOut;

  public HttpTransport(HttpEngine httpEngine, OutputStream outputStream, InputStream inputStream) {
    this.httpEngine = httpEngine;
    this.socketOut = outputStream;
    this.requestOut = outputStream;
    this.socketIn = inputStream;
  }

  @Override public OutputStream createRequestBody() throws IOException {
    boolean chunked = httpEngine.requestHeaders.isChunked();
    if (!chunked
        && httpEngine.policy.getChunkLength() > 0
        && httpEngine.connection.getHttpMinorVersion() != 0) {
      httpEngine.requestHeaders.setChunked();
      chunked = true;
    }

    // Stream a request body of unknown length.
    if (chunked) {
      int chunkLength = httpEngine.policy.getChunkLength();
      if (chunkLength == -1) {
        chunkLength = DEFAULT_CHUNK_LENGTH;
      }
      writeRequestHeaders();
      return new ChunkedOutputStream(requestOut, chunkLength);
    }

    // Stream a request body of a known length.
    long fixedContentLength = httpEngine.policy.getFixedContentLength();
    if (fixedContentLength != -1) {
      httpEngine.requestHeaders.setContentLength(fixedContentLength);
      writeRequestHeaders();
      return new FixedLengthOutputStream(requestOut, fixedContentLength);
    }

    long contentLength = httpEngine.requestHeaders.getContentLength();
    if (contentLength > Integer.MAX_VALUE) {
      throw new IllegalArgumentException("Use setFixedLengthStreamingMode() or "
          + "setChunkedStreamingMode() for requests larger than 2 GiB.");
    }

    // Buffer a request body of a known length.
    if (contentLength != -1) {
      writeRequestHeaders();
      return new RetryableOutputStream((int) contentLength);
    }

    // Buffer a request body of an unknown length. Don't write request
    // headers until the entire body is ready; otherwise we can't set the
    // Content-Length header correctly.
    return new RetryableOutputStream();
  }

  @Override public void flushRequest() throws IOException {
    requestOut.flush();
    requestOut = socketOut;
  }

  @Override public void writeRequestBody(RetryableOutputStream requestBody) throws IOException {
    requestBody.writeToSocket(requestOut);
  }

  /**
   * Prepares the HTTP headers and sends them to the server.
   *
   * <p>For streaming requests with a body, headers must be prepared
   * <strong>before</strong> the output stream has been written to. Otherwise
   * the body would need to be buffered!
   *
   * <p>For non-streaming requests with a body, headers must be prepared
   * <strong>after</strong> the output stream has been written to and closed.
   * This ensures that the {@code Content-Length} header field receives the
   * proper value.
   */
  public void writeRequestHeaders() throws IOException {
    httpEngine.writingRequestHeaders();
    RawHeaders headersToSend = httpEngine.requestHeaders.getHeaders();
    byte[] bytes = headersToSend.toBytes();
    requestOut.write(bytes);
  }

  @Override public ResponseHeaders readResponseHeaders() throws IOException {
    RawHeaders rawHeaders = RawHeaders.fromBytes(socketIn);
    httpEngine.connection.setHttpMinorVersion(rawHeaders.getHttpMinorVersion());
    httpEngine.receiveHeaders(rawHeaders);

    ResponseHeaders headers = new ResponseHeaders(httpEngine.uri, rawHeaders);
    headers.setTransport("http/1.1");
    return headers;
  }

  public boolean makeReusable(boolean streamCanceled, OutputStream requestBodyOut,
      InputStream responseBodyIn) {
    if (streamCanceled) {
      return false;
    }

    // We cannot reuse sockets that have incomplete output.
    if (requestBodyOut != null && !((AbstractOutputStream) requestBodyOut).isClosed()) {
      return false;
    }

    // If the request specified that the connection shouldn't be reused, don't reuse it.
    if (httpEngine.requestHeaders.hasConnectionClose()) {
      return false;
    }

    // If the response specified that the connection shouldn't be reused, don't reuse it.
    if (httpEngine.responseHeaders != null && httpEngine.responseHeaders.hasConnectionClose()) {
      return false;
    }

    if (responseBodyIn instanceof UnknownLengthHttpInputStream) {
      return false;
    }

    if (responseBodyIn != null) {
      return discardStream(httpEngine, responseBodyIn);
    }

    return true;
  }

  /**
   * Discards the response body so that the connection can be reused. This
   * needs to be done judiciously, since it delays the current request in
   * order to speed up a potential future request that may never occur.
   *
   * <p>A stream may be discarded to encourage response caching (a response
   * cannot be cached unless it is consumed completely) or to enable connection
   * reuse.
   */
  private static boolean discardStream(HttpEngine httpEngine, InputStream responseBodyIn) {
    Connection connection = httpEngine.connection;
    if (connection == null) return false;
    Socket socket = connection.getSocket();
    if (socket == null) return false;
    try {
      int socketTimeout = socket.getSoTimeout();
      socket.setSoTimeout(DISCARD_STREAM_TIMEOUT_MILLIS);
      try {
        Util.skipAll(responseBodyIn);
        return true;
      } finally {
        socket.setSoTimeout(socketTimeout);
      }
    } catch (IOException e) {
      return false;
    }
  }

  @Override public InputStream getTransferStream(CacheRequest cacheRequest) throws IOException {
    if (!httpEngine.hasResponseBody()) {
      return new FixedLengthInputStream(socketIn, cacheRequest, httpEngine, 0);
    }

    if (httpEngine.responseHeaders.isChunked()) {
      return new ChunkedInputStream(socketIn, cacheRequest, this);
    }

    if (httpEngine.responseHeaders.getContentLength() != -1) {
      return new FixedLengthInputStream(socketIn, cacheRequest, httpEngine,
          httpEngine.responseHeaders.getContentLength());
    }

    // Wrap the input stream from the connection (rather than just returning
    // "socketIn" directly here), so that we can control its use after the
    // reference escapes.
    return new UnknownLengthHttpInputStream(socketIn, cacheRequest, httpEngine);
  }

  /** An HTTP body with a fixed length known in advance. */
  private static final class FixedLengthOutputStream extends AbstractOutputStream {
    private final OutputStream socketOut;
    private long bytesRemaining;

    private FixedLengthOutputStream(OutputStream socketOut, long bytesRemaining) {
      this.socketOut = socketOut;
      this.bytesRemaining = bytesRemaining;
    }

    @Override public void write(byte[] buffer, int offset, int count) throws IOException {
      checkNotClosed();
      checkOffsetAndCount(buffer.length, offset, count);
      if (count > bytesRemaining) {
        throw new ProtocolException("expected " + bytesRemaining + " bytes but received " + count);
      }
      socketOut.write(buffer, offset, count);
      bytesRemaining -= count;
    }

    @Override public void flush() throws IOException {
      if (closed) {
        return; // don't throw; this stream might have been closed on the caller's behalf
      }
      socketOut.flush();
    }

    @Override public void close() throws IOException {
      if (closed) {
        return;
      }
      closed = true;
      if (bytesRemaining > 0) {
        throw new ProtocolException("unexpected end of stream");
      }
    }
  }

  /**
   * An HTTP body with alternating chunk sizes and chunk bodies. Chunks are
   * buffered until {@code maxChunkLength} bytes are ready, at which point the
   * chunk is written and the buffer is cleared.
   */
  private static final class ChunkedOutputStream extends AbstractOutputStream {
    private static final byte[] CRLF = { '\r', '\n' };
    private static final byte[] HEX_DIGITS = {
        '0', '1', '2', '3', '4', '5', '6', '7', '8', '9', 'a', 'b', 'c', 'd', 'e', 'f'
    };
    private static final byte[] FINAL_CHUNK = new byte[] { '0', '\r', '\n', '\r', '\n' };

    /** Scratch space for up to 8 hex digits, and then a constant CRLF. */
    private final byte[] hex = { 0, 0, 0, 0, 0, 0, 0, 0, '\r', '\n' };

    private final OutputStream socketOut;
    private final int maxChunkLength;
    private final ByteArrayOutputStream bufferedChunk;

    private ChunkedOutputStream(OutputStream socketOut, int maxChunkLength) {
      this.socketOut = socketOut;
      this.maxChunkLength = Math.max(1, dataLength(maxChunkLength));
      this.bufferedChunk = new ByteArrayOutputStream(maxChunkLength);
    }

    /**
     * Returns the amount of data that can be transmitted in a chunk whose total
     * length (data+headers) is {@code dataPlusHeaderLength}. This is presumably
     * useful to match sizes with wire-protocol packets.
     */
    private int dataLength(int dataPlusHeaderLength) {
      int headerLength = 4; // "\r\n" after the size plus another "\r\n" after the data
      for (int i = dataPlusHeaderLength - headerLength; i > 0; i >>= 4) {
        headerLength++;
      }
      return dataPlusHeaderLength - headerLength;
    }

    @Override public synchronized void write(byte[] buffer, int offset, int count)
        throws IOException {
      checkNotClosed();
      checkOffsetAndCount(buffer.length, offset, count);

      while (count > 0) {
        int numBytesWritten;

        if (bufferedChunk.size() > 0 || count < maxChunkLength) {
          // fill the buffered chunk and then maybe write that to the stream
          numBytesWritten = Math.min(count, maxChunkLength - bufferedChunk.size());
          // TODO: skip unnecessary copies from buffer->bufferedChunk?
          bufferedChunk.write(buffer, offset, numBytesWritten);
          if (bufferedChunk.size() == maxChunkLength) {
            writeBufferedChunkToSocket();
          }
        } else {
          // write a single chunk of size maxChunkLength to the stream
          numBytesWritten = maxChunkLength;
          writeHex(numBytesWritten);
          socketOut.write(buffer, offset, numBytesWritten);
          socketOut.write(CRLF);
        }

        offset += numBytesWritten;
        count -= numBytesWritten;
      }
    }

    /**
     * Equivalent to, but cheaper than writing Integer.toHexString().getBytes()
     * followed by CRLF.
     */
    private void writeHex(int i) throws IOException {
      int cursor = 8;
      do {
        hex[--cursor] = HEX_DIGITS[i & 0xf];
      } while ((i >>>= 4) != 0);
      socketOut.write(hex, cursor, hex.length - cursor);
    }

    @Override public synchronized void flush() throws IOException {
      if (closed) {
        return; // don't throw; this stream might have been closed on the caller's behalf
      }
      writeBufferedChunkToSocket();
      socketOut.flush();
    }

    @Override public synchronized void close() throws IOException {
      if (closed) {
        return;
      }
      closed = true;
      writeBufferedChunkToSocket();
      socketOut.write(FINAL_CHUNK);
    }

    private void writeBufferedChunkToSocket() throws IOException {
      int size = bufferedChunk.size();
      if (size <= 0) {
        return;
      }

      writeHex(size);
      bufferedChunk.writeTo(socketOut);
      bufferedChunk.reset();
      socketOut.write(CRLF);
    }
  }

  /** An HTTP body with a fixed length specified in advance. */
  private static class FixedLengthInputStream extends AbstractHttpInputStream {
    private long bytesRemaining;

    public FixedLengthInputStream(InputStream is, CacheRequest cacheRequest, HttpEngine httpEngine,
        long length) throws IOException {
      super(is, httpEngine, cacheRequest);
      bytesRemaining = length;
      if (bytesRemaining == 0) {
        endOfInput();
      }
    }

    @Override public int read(byte[] buffer, int offset, int count) throws IOException {
      checkOffsetAndCount(buffer.length, offset, count);
      checkNotClosed();
      if (bytesRemaining == 0) {
        return -1;
      }
      int read = in.read(buffer, offset, (int) Math.min(count, bytesRemaining));
      if (read == -1) {
        unexpectedEndOfInput(); // the server didn't supply the promised content length
        throw new ProtocolException("unexpected end of stream");
      }
      bytesRemaining -= read;
      cacheWrite(buffer, offset, read);
      if (bytesRemaining == 0) {
        endOfInput();
      }
      return read;
    }

    @Override public int available() throws IOException {
      checkNotClosed();
      return bytesRemaining == 0 ? 0 : (int) Math.min(in.available(), bytesRemaining);
    }

    @Override public void close() throws IOException {
      if (closed) {
        return;
      }
      if (bytesRemaining != 0 && !discardStream(httpEngine, this)) {
        unexpectedEndOfInput();
      }
      closed = true;
    }
  }

  /** An HTTP body with alternating chunk sizes and chunk bodies. */
  private static class ChunkedInputStream extends AbstractHttpInputStream {
    private static final int NO_CHUNK_YET = -1;
    private final HttpTransport transport;
    private int bytesRemainingInChunk = NO_CHUNK_YET;
    private boolean hasMoreChunks = true;

    ChunkedInputStream(InputStream is, CacheRequest cacheRequest, HttpTransport transport)
        throws IOException {
      super(is, transport.httpEngine, cacheRequest);
      this.transport = transport;
    }

    @Override public int read(byte[] buffer, int offset, int count) throws IOException {
      checkOffsetAndCount(buffer.length, offset, count);
      checkNotClosed();

      if (!hasMoreChunks) {
        return -1;
      }
      if (bytesRemainingInChunk == 0 || bytesRemainingInChunk == NO_CHUNK_YET) {
        readChunkSize();
        if (!hasMoreChunks) {
          return -1;
        }
      }
      int read = in.read(buffer, offset, Math.min(count, bytesRemainingInChunk));
      if (read == -1) {
        unexpectedEndOfInput(); // the server didn't supply the promised chunk length
        throw new IOException("unexpected end of stream");
      }
      bytesRemainingInChunk -= read;
      cacheWrite(buffer, offset, read);
      return read;
    }

    private void readChunkSize() throws IOException {
      // read the suffix of the previous chunk
      if (bytesRemainingInChunk != NO_CHUNK_YET) {
        Util.readAsciiLine(in);
      }
      String chunkSizeString = Util.readAsciiLine(in);
      int index = chunkSizeString.indexOf(";");
      if (index != -1) {
        chunkSizeString = chunkSizeString.substring(0, index);
      }
      try {
        bytesRemainingInChunk = Integer.parseInt(chunkSizeString.trim(), 16);
      } catch (NumberFormatException e) {
        throw new ProtocolException("Expected a hex chunk size but was " + chunkSizeString);
      }
      if (bytesRemainingInChunk == 0) {
        hasMoreChunks = false;
        RawHeaders rawResponseHeaders = httpEngine.responseHeaders.getHeaders();
        RawHeaders.readHeaders(transport.socketIn, rawResponseHeaders);
        httpEngine.receiveHeaders(rawResponseHeaders);
        endOfInput();
      }
    }

    @Override public int available() throws IOException {
      checkNotClosed();
      if (!hasMoreChunks || bytesRemainingInChunk == NO_CHUNK_YET) {
        return 0;
      }
      return Math.min(in.available(), bytesRemainingInChunk);
    }

    @Override public void close() throws IOException {
      if (closed) {
        return;
      }
      if (hasMoreChunks && !discardStream(httpEngine, this)) {
        unexpectedEndOfInput();
      }
      closed = true;
    }
  }
}


File: platforms/android/CordovaLib/src/com/squareup/okhttp/internal/http/HttpURLConnectionImpl.java
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

package com.squareup.okhttp.internal.http;

import com.squareup.okhttp.Connection;
import com.squareup.okhttp.OkHttpClient;
import com.squareup.okhttp.internal.Platform;
import com.squareup.okhttp.internal.Util;
import java.io.FileNotFoundException;
import java.io.IOException;
import java.io.InputStream;
import java.io.OutputStream;
import java.net.HttpRetryException;
import java.net.HttpURLConnection;
import java.net.InetSocketAddress;
import java.net.ProtocolException;
import java.net.Proxy;
import java.net.SocketPermission;
import java.net.URL;
import java.security.Permission;
import java.security.cert.CertificateException;
import java.util.ArrayList;
import java.util.Collections;
import java.util.List;
import java.util.Map;
import java.util.concurrent.TimeUnit;
import javax.net.ssl.SSLHandshakeException;

import static com.squareup.okhttp.internal.Util.getEffectivePort;

/**
 * This implementation uses HttpEngine to send requests and receive responses.
 * This class may use multiple HttpEngines to follow redirects, authentication
 * retries, etc. to retrieve the final response body.
 *
 * <h3>What does 'connected' mean?</h3>
 * This class inherits a {@code connected} field from the superclass. That field
 * is <strong>not</strong> used to indicate not whether this URLConnection is
 * currently connected. Instead, it indicates whether a connection has ever been
 * attempted. Once a connection has been attempted, certain properties (request
 * header fields, request method, etc.) are immutable. Test the {@code
 * connection} field on this class for null/non-null to determine of an instance
 * is currently connected to a server.
 */
public class HttpURLConnectionImpl extends HttpURLConnection implements Policy {

  /** Numeric status code, 307: Temporary Redirect. */
  public static final int HTTP_TEMP_REDIRECT = 307;

  /**
   * How many redirects should we follow? Chrome follows 21; Firefox, curl,
   * and wget follow 20; Safari follows 16; and HTTP/1.0 recommends 5.
   */
  private static final int MAX_REDIRECTS = 20;

  final OkHttpClient client;

  private final RawHeaders rawRequestHeaders = new RawHeaders();
  /** Like the superclass field of the same name, but a long and available on all platforms. */
  private long fixedContentLength = -1;
  private int redirectionCount;
  protected IOException httpEngineFailure;
  protected HttpEngine httpEngine;
  private Proxy selectedProxy;

  public HttpURLConnectionImpl(URL url, OkHttpClient client) {
    super(url);
    this.client = client;
  }

  @Override public final void connect() throws IOException {
    initHttpEngine();
    boolean success;
    do {
      success = execute(false);
    } while (!success);
  }

  @Override public final void disconnect() {
    // Calling disconnect() before a connection exists should have no effect.
    if (httpEngine != null) {
      // We close the response body here instead of in
      // HttpEngine.release because that is called when input
      // has been completely read from the underlying socket.
      // However the response body can be a GZIPInputStream that
      // still has unread data.
      if (httpEngine.hasResponse()) {
        Util.closeQuietly(httpEngine.getResponseBody());
      }
      httpEngine.release(true);
    }
  }

  /**
   * Returns an input stream from the server in the case of error such as the
   * requested file (txt, htm, html) is not found on the remote server.
   */
  @Override public final InputStream getErrorStream() {
    try {
      HttpEngine response = getResponse();
      if (response.hasResponseBody() && response.getResponseCode() >= HTTP_BAD_REQUEST) {
        return response.getResponseBody();
      }
      return null;
    } catch (IOException e) {
      return null;
    }
  }

  /**
   * Returns the value of the field at {@code position}. Returns null if there
   * are fewer than {@code position} headers.
   */
  @Override public final String getHeaderField(int position) {
    try {
      return getResponse().getResponseHeaders().getHeaders().getValue(position);
    } catch (IOException e) {
      return null;
    }
  }

  /**
   * Returns the value of the field corresponding to the {@code fieldName}, or
   * null if there is no such field. If the field has multiple values, the
   * last value is returned.
   */
  @Override public final String getHeaderField(String fieldName) {
    try {
      RawHeaders rawHeaders = getResponse().getResponseHeaders().getHeaders();
      return fieldName == null ? rawHeaders.getStatusLine() : rawHeaders.get(fieldName);
    } catch (IOException e) {
      return null;
    }
  }

  @Override public final String getHeaderFieldKey(int position) {
    try {
      return getResponse().getResponseHeaders().getHeaders().getFieldName(position);
    } catch (IOException e) {
      return null;
    }
  }

  @Override public final Map<String, List<String>> getHeaderFields() {
    try {
      return getResponse().getResponseHeaders().getHeaders().toMultimap(true);
    } catch (IOException e) {
      return Collections.emptyMap();
    }
  }

  @Override public final Map<String, List<String>> getRequestProperties() {
    if (connected) {
      throw new IllegalStateException(
          "Cannot access request header fields after connection is set");
    }
    return rawRequestHeaders.toMultimap(false);
  }

  @Override public final InputStream getInputStream() throws IOException {
    if (!doInput) {
      throw new ProtocolException("This protocol does not support input");
    }

    HttpEngine response = getResponse();

    // if the requested file does not exist, throw an exception formerly the
    // Error page from the server was returned if the requested file was
    // text/html this has changed to return FileNotFoundException for all
    // file types
    if (getResponseCode() >= HTTP_BAD_REQUEST) {
      throw new FileNotFoundException(url.toString());
    }

    InputStream result = response.getResponseBody();
    if (result == null) {
      throw new ProtocolException("No response body exists; responseCode=" + getResponseCode());
    }
    return result;
  }

  @Override public final OutputStream getOutputStream() throws IOException {
    connect();

    OutputStream out = httpEngine.getRequestBody();
    if (out == null) {
      throw new ProtocolException("method does not support a request body: " + method);
    } else if (httpEngine.hasResponse()) {
      throw new ProtocolException("cannot write request body after response has been read");
    }

    return out;
  }

  @Override public final Permission getPermission() throws IOException {
    String hostName = getURL().getHost();
    int hostPort = Util.getEffectivePort(getURL());
    if (usingProxy()) {
      InetSocketAddress proxyAddress = (InetSocketAddress) client.getProxy().address();
      hostName = proxyAddress.getHostName();
      hostPort = proxyAddress.getPort();
    }
    return new SocketPermission(hostName + ":" + hostPort, "connect, resolve");
  }

  @Override public final String getRequestProperty(String field) {
    if (field == null) {
      return null;
    }
    return rawRequestHeaders.get(field);
  }

  @Override public void setConnectTimeout(int timeoutMillis) {
    client.setConnectTimeout(timeoutMillis, TimeUnit.MILLISECONDS);
  }

  @Override public int getConnectTimeout() {
    return client.getConnectTimeout();
  }

  @Override public void setReadTimeout(int timeoutMillis) {
    client.setReadTimeout(timeoutMillis, TimeUnit.MILLISECONDS);
  }

  @Override public int getReadTimeout() {
    return client.getReadTimeout();
  }

  private void initHttpEngine() throws IOException {
    if (httpEngineFailure != null) {
      throw httpEngineFailure;
    } else if (httpEngine != null) {
      return;
    }

    connected = true;
    try {
      if (doOutput) {
        if (method.equals("GET")) {
          // they are requesting a stream to write to. This implies a POST method
          method = "POST";
        } else if (!method.equals("POST") && !method.equals("PUT") && !method.equals("PATCH")) {
          // If the request method is neither POST nor PUT nor PATCH, then you're not writing
          throw new ProtocolException(method + " does not support writing");
        }
      }
      httpEngine = newHttpEngine(method, rawRequestHeaders, null, null);
    } catch (IOException e) {
      httpEngineFailure = e;
      throw e;
    }
  }

  @Override public HttpURLConnection getHttpConnectionToCache() {
    return this;
  }

  private HttpEngine newHttpEngine(String method, RawHeaders requestHeaders,
      Connection connection, RetryableOutputStream requestBody) throws IOException {
    if (url.getProtocol().equals("http")) {
      return new HttpEngine(client, this, method, requestHeaders, connection, requestBody);
    } else if (url.getProtocol().equals("https")) {
      return new HttpsEngine(client, this, method, requestHeaders, connection, requestBody);
    } else {
      throw new AssertionError();
    }
  }

  /**
   * Aggressively tries to get the final HTTP response, potentially making
   * many HTTP requests in the process in order to cope with redirects and
   * authentication.
   */
  private HttpEngine getResponse() throws IOException {
    initHttpEngine();

    if (httpEngine.hasResponse()) {
      return httpEngine;
    }

    while (true) {
      if (!execute(true)) {
        continue;
      }

      Retry retry = processResponseHeaders();
      if (retry == Retry.NONE) {
        httpEngine.automaticallyReleaseConnectionToPool();
        return httpEngine;
      }

      // The first request was insufficient. Prepare for another...
      String retryMethod = method;
      OutputStream requestBody = httpEngine.getRequestBody();

      // Although RFC 2616 10.3.2 specifies that a HTTP_MOVED_PERM
      // redirect should keep the same method, Chrome, Firefox and the
      // RI all issue GETs when following any redirect.
      int responseCode = httpEngine.getResponseCode();
      if (responseCode == HTTP_MULT_CHOICE
          || responseCode == HTTP_MOVED_PERM
          || responseCode == HTTP_MOVED_TEMP
          || responseCode == HTTP_SEE_OTHER) {
        retryMethod = "GET";
        requestBody = null;
      }

      if (requestBody != null && !(requestBody instanceof RetryableOutputStream)) {
        throw new HttpRetryException("Cannot retry streamed HTTP body", responseCode);
      }

      if (retry == Retry.DIFFERENT_CONNECTION) {
        httpEngine.automaticallyReleaseConnectionToPool();
      }

      httpEngine.release(false);

      httpEngine = newHttpEngine(retryMethod, rawRequestHeaders, httpEngine.getConnection(),
          (RetryableOutputStream) requestBody);

      if (requestBody == null) {
        // Drop the Content-Length header when redirected from POST to GET.
        httpEngine.getRequestHeaders().removeContentLength();
      }
    }
  }

  /**
   * Sends a request and optionally reads a response. Returns true if the
   * request was successfully executed, and false if the request can be
   * retried. Throws an exception if the request failed permanently.
   */
  private boolean execute(boolean readResponse) throws IOException {
    try {
      httpEngine.sendRequest();
      if (readResponse) {
        httpEngine.readResponse();
      }

      return true;
    } catch (IOException e) {
      if (handleFailure(e)) {
        return false;
      } else {
        throw e;
      }
    }
  }

  /**
   * Report and attempt to recover from {@code e}. Returns true if the HTTP
   * engine was replaced and the request should be retried. Otherwise the
   * failure is permanent.
   */
  private boolean handleFailure(IOException e) throws IOException {
    RouteSelector routeSelector = httpEngine.routeSelector;
    if (routeSelector != null && httpEngine.connection != null) {
      routeSelector.connectFailed(httpEngine.connection, e);
    }

    OutputStream requestBody = httpEngine.getRequestBody();
    boolean canRetryRequestBody = requestBody == null
        || requestBody instanceof RetryableOutputStream;
    if (routeSelector == null && httpEngine.connection == null // No connection.
        || routeSelector != null && !routeSelector.hasNext() // No more routes to attempt.
        || !isRecoverable(e)
        || !canRetryRequestBody) {
      httpEngineFailure = e;
      return false;
    }

    httpEngine.release(true);
    RetryableOutputStream retryableOutputStream = (RetryableOutputStream) requestBody;
    httpEngine = newHttpEngine(method, rawRequestHeaders, null, retryableOutputStream);
    httpEngine.routeSelector = routeSelector; // Keep the same routeSelector.
    return true;
  }

  private boolean isRecoverable(IOException e) {
    // If the problem was a CertificateException from the X509TrustManager,
    // do not retry, we didn't have an abrupt server initiated exception.
    boolean sslFailure =
        e instanceof SSLHandshakeException && e.getCause() instanceof CertificateException;
    boolean protocolFailure = e instanceof ProtocolException;
    return !sslFailure && !protocolFailure;
  }

  public HttpEngine getHttpEngine() {
    return httpEngine;
  }

  enum Retry {
    NONE,
    SAME_CONNECTION,
    DIFFERENT_CONNECTION
  }

  /**
   * Returns the retry action to take for the current response headers. The
   * headers, proxy and target URL for this connection may be adjusted to
   * prepare for a follow up request.
   */
  private Retry processResponseHeaders() throws IOException {
    Proxy selectedProxy = httpEngine.connection != null
        ? httpEngine.connection.getRoute().getProxy()
        : client.getProxy();
    final int responseCode = getResponseCode();
    switch (responseCode) {
      case HTTP_PROXY_AUTH:
        if (selectedProxy.type() != Proxy.Type.HTTP) {
          throw new ProtocolException("Received HTTP_PROXY_AUTH (407) code while not using proxy");
        }
        // fall-through
      case HTTP_UNAUTHORIZED:
        boolean credentialsFound = HttpAuthenticator.processAuthHeader(client.getAuthenticator(),
            getResponseCode(), httpEngine.getResponseHeaders().getHeaders(), rawRequestHeaders,
            selectedProxy, url);
        return credentialsFound ? Retry.SAME_CONNECTION : Retry.NONE;

      case HTTP_MULT_CHOICE:
      case HTTP_MOVED_PERM:
      case HTTP_MOVED_TEMP:
      case HTTP_SEE_OTHER:
      case HTTP_TEMP_REDIRECT:
        if (!getInstanceFollowRedirects()) {
          return Retry.NONE;
        }
        if (++redirectionCount > MAX_REDIRECTS) {
          throw new ProtocolException("Too many redirects: " + redirectionCount);
        }
        if (responseCode == HTTP_TEMP_REDIRECT && !method.equals("GET") && !method.equals("HEAD")) {
          // "If the 307 status code is received in response to a request other than GET or HEAD,
          // the user agent MUST NOT automatically redirect the request"
          return Retry.NONE;
        }
        String location = getHeaderField("Location");
        if (location == null) {
          return Retry.NONE;
        }
        URL previousUrl = url;
        url = new URL(previousUrl, location);
        if (!url.getProtocol().equals("https") && !url.getProtocol().equals("http")) {
          return Retry.NONE; // Don't follow redirects to unsupported protocols.
        }
        boolean sameProtocol = previousUrl.getProtocol().equals(url.getProtocol());
        if (!sameProtocol && !client.getFollowProtocolRedirects()) {
          return Retry.NONE; // This client doesn't follow redirects across protocols.
        }
        boolean sameHost = previousUrl.getHost().equals(url.getHost());
        boolean samePort = getEffectivePort(previousUrl) == getEffectivePort(url);
        if (sameHost && samePort && sameProtocol) {
          return Retry.SAME_CONNECTION;
        } else {
          return Retry.DIFFERENT_CONNECTION;
        }

      default:
        return Retry.NONE;
    }
  }

  /** @see java.net.HttpURLConnection#setFixedLengthStreamingMode(int) */
  @Override public final long getFixedContentLength() {
    return fixedContentLength;
  }

  @Override public final int getChunkLength() {
    return chunkLength;
  }

  @Override public final boolean usingProxy() {
    if (selectedProxy != null) {
      return isValidNonDirectProxy(selectedProxy);
    }

    // This behavior is a bit odd (but is probably justified by the
    // oddness of the APIs involved). Before a connection is established,
    // this method will return true only if this connection was explicitly
    // opened with a Proxy. We don't attempt to query the ProxySelector
    // at all.
    return isValidNonDirectProxy(client.getProxy());
  }

  private static boolean isValidNonDirectProxy(Proxy proxy) {
    return proxy != null && proxy.type() != Proxy.Type.DIRECT;
  }

  @Override public String getResponseMessage() throws IOException {
    return getResponse().getResponseHeaders().getHeaders().getResponseMessage();
  }

  @Override public final int getResponseCode() throws IOException {
    return getResponse().getResponseCode();
  }

  @Override public final void setRequestProperty(String field, String newValue) {
    if (connected) {
      throw new IllegalStateException("Cannot set request property after connection is made");
    }
    if (field == null) {
      throw new NullPointerException("field == null");
    }
    if (newValue == null) {
      // Silently ignore null header values for backwards compatibility with older
      // android versions as well as with other URLConnection implementations.
      //
      // Some implementations send a malformed HTTP header when faced with
      // such requests, we respect the spec and ignore the header.
      Platform.get().logW("Ignoring header " + field + " because its value was null.");
      return;
    }

    if ("X-Android-Transports".equals(field)) {
      setTransports(newValue, false /* append */);
    } else {
      rawRequestHeaders.set(field, newValue);
    }
  }

  @Override public final void addRequestProperty(String field, String value) {
    if (connected) {
      throw new IllegalStateException("Cannot add request property after connection is made");
    }
    if (field == null) {
      throw new NullPointerException("field == null");
    }
    if (value == null) {
      // Silently ignore null header values for backwards compatibility with older
      // android versions as well as with other URLConnection implementations.
      //
      // Some implementations send a malformed HTTP header when faced with
      // such requests, we respect the spec and ignore the header.
      Platform.get().logW("Ignoring header " + field + " because its value was null.");
      return;
    }

    if ("X-Android-Transports".equals(field)) {
      setTransports(value, true /* append */);
    } else {
      rawRequestHeaders.add(field, value);
    }
  }

  /*
   * Splits and validates a comma-separated string of transports.
   * When append == false, we require that the transport list contains "http/1.1".
   */
  private void setTransports(String transportsString, boolean append) {
    List<String> transportsList = new ArrayList<String>();
    if (append) {
      transportsList.addAll(client.getTransports());
    }
    for (String transport : transportsString.split(",", -1)) {
      transportsList.add(transport);
    }
    client.setTransports(transportsList);
  }

  @Override public void setFixedLengthStreamingMode(int contentLength) {
    setFixedLengthStreamingMode((long) contentLength);
  }

  // @Override Don't override: this overload method doesn't exist prior to Java 1.7.
  public void setFixedLengthStreamingMode(long contentLength) {
    if (super.connected) throw new IllegalStateException("Already connected");
    if (chunkLength > 0) throw new IllegalStateException("Already in chunked mode");
    if (contentLength < 0) throw new IllegalArgumentException("contentLength < 0");
    this.fixedContentLength = contentLength;
    super.fixedContentLength = (int) Math.min(contentLength, Integer.MAX_VALUE);
  }

  @Override public final void setSelectedProxy(Proxy proxy) {
    this.selectedProxy = proxy;
  }
}


File: platforms/android/CordovaLib/src/com/squareup/okhttp/internal/http/HttpsEngine.java
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
package com.squareup.okhttp.internal.http;

import com.squareup.okhttp.Connection;
import com.squareup.okhttp.OkHttpClient;
import com.squareup.okhttp.TunnelRequest;
import java.io.IOException;
import java.net.CacheResponse;
import java.net.SecureCacheResponse;
import java.net.URL;
import javax.net.ssl.SSLSocket;

import static com.squareup.okhttp.internal.Util.getEffectivePort;

public final class HttpsEngine extends HttpEngine {
  /**
   * Stash of HttpsEngine.connection.socket to implement requests like {@code
   * HttpsURLConnection#getCipherSuite} even after the connection has been
   * recycled.
   */
  private SSLSocket sslSocket;

  public HttpsEngine(OkHttpClient client, Policy policy, String method, RawHeaders requestHeaders,
      Connection connection, RetryableOutputStream requestBody) throws IOException {
    super(client, policy, method, requestHeaders, connection, requestBody);
    this.sslSocket = connection != null ? (SSLSocket) connection.getSocket() : null;
  }

  @Override protected void connected(Connection connection) {
    this.sslSocket = (SSLSocket) connection.getSocket();
    super.connected(connection);
  }

  @Override protected boolean acceptCacheResponseType(CacheResponse cacheResponse) {
    return cacheResponse instanceof SecureCacheResponse;
  }

  @Override protected boolean includeAuthorityInRequestLine() {
    // Even if there is a proxy, it isn't involved. Always request just the path.
    return false;
  }

  public SSLSocket getSslSocket() {
    return sslSocket;
  }

  @Override protected TunnelRequest getTunnelConfig() {
    String userAgent = requestHeaders.getUserAgent();
    if (userAgent == null) {
      userAgent = getDefaultUserAgent();
    }

    URL url = policy.getURL();
    return new TunnelRequest(url.getHost(), getEffectivePort(url), userAgent,
        requestHeaders.getProxyAuthorization());
  }
}


File: platforms/android/CordovaLib/src/com/squareup/okhttp/internal/http/HttpsURLConnectionImpl.java
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
package com.squareup.okhttp.internal.http;

import android.annotation.SuppressLint;
import com.squareup.okhttp.OkHttpClient;
import java.io.IOException;
import java.io.InputStream;
import java.io.OutputStream;
import java.net.HttpURLConnection;
import java.net.ProtocolException;
import java.net.SecureCacheResponse;
import java.net.URL;
import java.security.Permission;
import java.security.Principal;
import java.security.cert.Certificate;
import java.util.List;
import java.util.Map;
import javax.net.ssl.HostnameVerifier;
import javax.net.ssl.HttpsURLConnection;
import javax.net.ssl.SSLPeerUnverifiedException;
import javax.net.ssl.SSLSocket;
import javax.net.ssl.SSLSocketFactory;

public final class HttpsURLConnectionImpl extends HttpsURLConnection {

  /** HttpUrlConnectionDelegate allows reuse of HttpURLConnectionImpl. */
  private final HttpUrlConnectionDelegate delegate;

  public HttpsURLConnectionImpl(URL url, OkHttpClient client) {
    super(url);
    delegate = new HttpUrlConnectionDelegate(url, client);
  }

  @Override public String getCipherSuite() {
    SecureCacheResponse cacheResponse = delegate.getSecureCacheResponse();
    if (cacheResponse != null) {
      return cacheResponse.getCipherSuite();
    }
    SSLSocket sslSocket = getSslSocket();
    if (sslSocket != null) {
      return sslSocket.getSession().getCipherSuite();
    }
    return null;
  }

  @Override public Certificate[] getLocalCertificates() {
    SecureCacheResponse cacheResponse = delegate.getSecureCacheResponse();
    if (cacheResponse != null) {
      List<Certificate> result = cacheResponse.getLocalCertificateChain();
      return result != null ? result.toArray(new Certificate[result.size()]) : null;
    }
    SSLSocket sslSocket = getSslSocket();
    if (sslSocket != null) {
      return sslSocket.getSession().getLocalCertificates();
    }
    return null;
  }

  @Override public Certificate[] getServerCertificates() throws SSLPeerUnverifiedException {
    SecureCacheResponse cacheResponse = delegate.getSecureCacheResponse();
    if (cacheResponse != null) {
      List<Certificate> result = cacheResponse.getServerCertificateChain();
      return result != null ? result.toArray(new Certificate[result.size()]) : null;
    }
    SSLSocket sslSocket = getSslSocket();
    if (sslSocket != null) {
      return sslSocket.getSession().getPeerCertificates();
    }
    return null;
  }

  @Override public Principal getPeerPrincipal() throws SSLPeerUnverifiedException {
    SecureCacheResponse cacheResponse = delegate.getSecureCacheResponse();
    if (cacheResponse != null) {
      return cacheResponse.getPeerPrincipal();
    }
    SSLSocket sslSocket = getSslSocket();
    if (sslSocket != null) {
      return sslSocket.getSession().getPeerPrincipal();
    }
    return null;
  }

  @Override public Principal getLocalPrincipal() {
    SecureCacheResponse cacheResponse = delegate.getSecureCacheResponse();
    if (cacheResponse != null) {
      return cacheResponse.getLocalPrincipal();
    }
    SSLSocket sslSocket = getSslSocket();
    if (sslSocket != null) {
      return sslSocket.getSession().getLocalPrincipal();
    }
    return null;
  }

  public HttpEngine getHttpEngine() {
    return delegate.getHttpEngine();
  }

  private SSLSocket getSslSocket() {
    if (delegate.httpEngine == null || !delegate.httpEngine.connected) {
      throw new IllegalStateException("Connection has not yet been established");
    }
    return delegate.httpEngine instanceof HttpsEngine
        ? ((HttpsEngine) delegate.httpEngine).getSslSocket()
        : null; // Not HTTPS! Probably an https:// to http:// redirect.
  }

  @Override public void disconnect() {
    delegate.disconnect();
  }

  @Override public InputStream getErrorStream() {
    return delegate.getErrorStream();
  }

  @Override public String getRequestMethod() {
    return delegate.getRequestMethod();
  }

  @Override public int getResponseCode() throws IOException {
    return delegate.getResponseCode();
  }

  @Override public String getResponseMessage() throws IOException {
    return delegate.getResponseMessage();
  }

  @Override public void setRequestMethod(String method) throws ProtocolException {
    delegate.setRequestMethod(method);
  }

  @Override public boolean usingProxy() {
    return delegate.usingProxy();
  }

  @Override public boolean getInstanceFollowRedirects() {
    return delegate.getInstanceFollowRedirects();
  }

  @Override public void setInstanceFollowRedirects(boolean followRedirects) {
    delegate.setInstanceFollowRedirects(followRedirects);
  }

  @Override public void connect() throws IOException {
    connected = true;
    delegate.connect();
  }

  @Override public boolean getAllowUserInteraction() {
    return delegate.getAllowUserInteraction();
  }

  @Override public Object getContent() throws IOException {
    return delegate.getContent();
  }

  @SuppressWarnings("unchecked") // Spec does not generify
  @Override public Object getContent(Class[] types) throws IOException {
    return delegate.getContent(types);
  }

  @Override public String getContentEncoding() {
    return delegate.getContentEncoding();
  }

  @Override public int getContentLength() {
    return delegate.getContentLength();
  }

  @Override public String getContentType() {
    return delegate.getContentType();
  }

  @Override public long getDate() {
    return delegate.getDate();
  }

  @Override public boolean getDefaultUseCaches() {
    return delegate.getDefaultUseCaches();
  }

  @Override public boolean getDoInput() {
    return delegate.getDoInput();
  }

  @Override public boolean getDoOutput() {
    return delegate.getDoOutput();
  }

  @Override public long getExpiration() {
    return delegate.getExpiration();
  }

  @Override public String getHeaderField(int pos) {
    return delegate.getHeaderField(pos);
  }

  @Override public Map<String, List<String>> getHeaderFields() {
    return delegate.getHeaderFields();
  }

  @Override public Map<String, List<String>> getRequestProperties() {
    return delegate.getRequestProperties();
  }

  @Override public void addRequestProperty(String field, String newValue) {
    delegate.addRequestProperty(field, newValue);
  }

  @Override public String getHeaderField(String key) {
    return delegate.getHeaderField(key);
  }

  @Override public long getHeaderFieldDate(String field, long defaultValue) {
    return delegate.getHeaderFieldDate(field, defaultValue);
  }

  @Override public int getHeaderFieldInt(String field, int defaultValue) {
    return delegate.getHeaderFieldInt(field, defaultValue);
  }

  @Override public String getHeaderFieldKey(int position) {
    return delegate.getHeaderFieldKey(position);
  }

  @Override public long getIfModifiedSince() {
    return delegate.getIfModifiedSince();
  }

  @Override public InputStream getInputStream() throws IOException {
    return delegate.getInputStream();
  }

  @Override public long getLastModified() {
    return delegate.getLastModified();
  }

  @Override public OutputStream getOutputStream() throws IOException {
    return delegate.getOutputStream();
  }

  @Override public Permission getPermission() throws IOException {
    return delegate.getPermission();
  }

  @Override public String getRequestProperty(String field) {
    return delegate.getRequestProperty(field);
  }

  @Override public URL getURL() {
    return delegate.getURL();
  }

  @Override public boolean getUseCaches() {
    return delegate.getUseCaches();
  }

  @Override public void setAllowUserInteraction(boolean newValue) {
    delegate.setAllowUserInteraction(newValue);
  }

  @Override public void setDefaultUseCaches(boolean newValue) {
    delegate.setDefaultUseCaches(newValue);
  }

  @Override public void setDoInput(boolean newValue) {
    delegate.setDoInput(newValue);
  }

  @Override public void setDoOutput(boolean newValue) {
    delegate.setDoOutput(newValue);
  }

  @Override public void setIfModifiedSince(long newValue) {
    delegate.setIfModifiedSince(newValue);
  }

  @Override public void setRequestProperty(String field, String newValue) {
    delegate.setRequestProperty(field, newValue);
  }

  @Override public void setUseCaches(boolean newValue) {
    delegate.setUseCaches(newValue);
  }

  @Override public void setConnectTimeout(int timeoutMillis) {
    delegate.setConnectTimeout(timeoutMillis);
  }

  @Override public int getConnectTimeout() {
    return delegate.getConnectTimeout();
  }

  @Override public void setReadTimeout(int timeoutMillis) {
    delegate.setReadTimeout(timeoutMillis);
  }

  @Override public int getReadTimeout() {
    return delegate.getReadTimeout();
  }

  @Override public String toString() {
    return delegate.toString();
  }

  @Override public void setFixedLengthStreamingMode(int contentLength) {
    delegate.setFixedLengthStreamingMode(contentLength);
  }

  @Override public void setChunkedStreamingMode(int chunkLength) {
    delegate.setChunkedStreamingMode(chunkLength);
  }

  @Override public void setHostnameVerifier(HostnameVerifier hostnameVerifier) {
    delegate.client.setHostnameVerifier(hostnameVerifier);
  }

  @Override public HostnameVerifier getHostnameVerifier() {
    return delegate.client.getHostnameVerifier();
  }

  @Override public void setSSLSocketFactory(SSLSocketFactory sslSocketFactory) {
    delegate.client.setSslSocketFactory(sslSocketFactory);
  }

  @Override public SSLSocketFactory getSSLSocketFactory() {
    return delegate.client.getSslSocketFactory();
  }

  @SuppressLint("NewApi")
  @Override public void setFixedLengthStreamingMode(long contentLength) {
    delegate.setFixedLengthStreamingMode(contentLength);
  }

  private final class HttpUrlConnectionDelegate extends HttpURLConnectionImpl {
    private HttpUrlConnectionDelegate(URL url, OkHttpClient client) {
      super(url, client);
    }

    @Override public HttpURLConnection getHttpConnectionToCache() {
      return HttpsURLConnectionImpl.this;
    }

    public SecureCacheResponse getSecureCacheResponse() {
      return httpEngine instanceof HttpsEngine
          ? (SecureCacheResponse) httpEngine.getCacheResponse()
          : null;
    }
  }
}


File: platforms/android/CordovaLib/src/com/squareup/okhttp/internal/http/OkResponseCacheAdapter.java
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

import com.squareup.okhttp.OkResponseCache;
import com.squareup.okhttp.ResponseSource;
import java.io.IOException;
import java.net.CacheRequest;
import java.net.CacheResponse;
import java.net.HttpURLConnection;
import java.net.ResponseCache;
import java.net.URI;
import java.net.URLConnection;
import java.util.List;
import java.util.Map;

public final class OkResponseCacheAdapter implements OkResponseCache {
  private final ResponseCache responseCache;
  public OkResponseCacheAdapter(ResponseCache responseCache) {
    this.responseCache = responseCache;
  }

  @Override public CacheResponse get(URI uri, String requestMethod,
      Map<String, List<String>> requestHeaders) throws IOException {
    return responseCache.get(uri, requestMethod, requestHeaders);
  }

  @Override public CacheRequest put(URI uri, URLConnection urlConnection) throws IOException {
    return responseCache.put(uri, urlConnection);
  }

  @Override public void maybeRemove(String requestMethod, URI uri) throws IOException {
  }

  @Override public void update(CacheResponse conditionalCacheHit, HttpURLConnection connection)
      throws IOException {
  }

  @Override public void trackConditionalCacheHit() {
  }

  @Override public void trackResponse(ResponseSource source) {
  }
}


File: platforms/android/CordovaLib/src/com/squareup/okhttp/internal/http/Policy.java
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

import java.net.HttpURLConnection;
import java.net.Proxy;
import java.net.URL;

public interface Policy {
  /** Returns true if HTTP response caches should be used. */
  boolean getUseCaches();

  /** Returns the HttpURLConnection instance to store in the cache. */
  HttpURLConnection getHttpConnectionToCache();

  /** Returns the current destination URL, possibly a redirect. */
  URL getURL();

  /** Returns the If-Modified-Since timestamp, or 0 if none is set. */
  long getIfModifiedSince();

  /** Returns true if a non-direct proxy is specified. */
  boolean usingProxy();

  /** @see java.net.HttpURLConnection#setChunkedStreamingMode(int) */
  int getChunkLength();

  /** @see java.net.HttpURLConnection#setFixedLengthStreamingMode(int) */
  long getFixedContentLength();

  /**
   * Sets the current proxy that this connection is using.
   * @see java.net.HttpURLConnection#usingProxy
   */
  void setSelectedProxy(Proxy proxy);
}


File: platforms/android/CordovaLib/src/com/squareup/okhttp/internal/http/RawHeaders.java
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

package com.squareup.okhttp.internal.http;

import com.squareup.okhttp.internal.Util;
import java.io.IOException;
import java.io.InputStream;
import java.io.UnsupportedEncodingException;
import java.net.ProtocolException;
import java.util.ArrayList;
import java.util.Collections;
import java.util.Comparator;
import java.util.HashSet;
import java.util.List;
import java.util.Locale;
import java.util.Map;
import java.util.Map.Entry;
import java.util.Set;
import java.util.TreeMap;
import java.util.TreeSet;

/**
 * The HTTP status and unparsed header fields of a single HTTP message. Values
 * are represented as uninterpreted strings; use {@link RequestHeaders} and
 * {@link ResponseHeaders} for interpreted headers. This class maintains the
 * order of the header fields within the HTTP message.
 *
 * <p>This class tracks fields line-by-line. A field with multiple comma-
 * separated values on the same line will be treated as a field with a single
 * value by this class. It is the caller's responsibility to detect and split
 * on commas if their field permits multiple values. This simplifies use of
 * single-valued fields whose values routinely contain commas, such as cookies
 * or dates.
 *
 * <p>This class trims whitespace from values. It never returns values with
 * leading or trailing whitespace.
 */
public final class RawHeaders {
  private static final Comparator<String> FIELD_NAME_COMPARATOR = new Comparator<String>() {
    // @FindBugsSuppressWarnings("ES_COMPARING_PARAMETER_STRING_WITH_EQ")
    @Override public int compare(String a, String b) {
      if (a == b) {
        return 0;
      } else if (a == null) {
        return -1;
      } else if (b == null) {
        return 1;
      } else {
        return String.CASE_INSENSITIVE_ORDER.compare(a, b);
      }
    }
  };

  private final List<String> namesAndValues = new ArrayList<String>(20);
  private String requestLine;
  private String statusLine;
  private int httpMinorVersion = 1;
  private int responseCode = -1;
  private String responseMessage;

  public RawHeaders() {
  }

  public RawHeaders(RawHeaders copyFrom) {
    namesAndValues.addAll(copyFrom.namesAndValues);
    requestLine = copyFrom.requestLine;
    statusLine = copyFrom.statusLine;
    httpMinorVersion = copyFrom.httpMinorVersion;
    responseCode = copyFrom.responseCode;
    responseMessage = copyFrom.responseMessage;
  }

  /** Sets the request line (like "GET / HTTP/1.1"). */
  public void setRequestLine(String requestLine) {
    requestLine = requestLine.trim();
    this.requestLine = requestLine;
  }

  /** Sets the response status line (like "HTTP/1.0 200 OK"). */
  public void setStatusLine(String statusLine) throws IOException {
    // H T T P / 1 . 1   2 0 0   T e m p o r a r y   R e d i r e c t
    // 0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0
    if (this.responseMessage != null) {
      throw new IllegalStateException("statusLine is already set");
    }
    // We allow empty message without leading white space since some servers
    // do not send the white space when the message is empty.
    boolean hasMessage = statusLine.length() > 13;
    if (!statusLine.startsWith("HTTP/1.")
        || statusLine.length() < 12
        || statusLine.charAt(8) != ' '
        || (hasMessage && statusLine.charAt(12) != ' ')) {
      throw new ProtocolException("Unexpected status line: " + statusLine);
    }
    int httpMinorVersion = statusLine.charAt(7) - '0';
    if (httpMinorVersion < 0 || httpMinorVersion > 9) {
      throw new ProtocolException("Unexpected status line: " + statusLine);
    }
    int responseCode;
    try {
      responseCode = Integer.parseInt(statusLine.substring(9, 12));
    } catch (NumberFormatException e) {
      throw new ProtocolException("Unexpected status line: " + statusLine);
    }
    this.responseMessage = hasMessage ? statusLine.substring(13) : "";
    this.responseCode = responseCode;
    this.statusLine = statusLine;
    this.httpMinorVersion = httpMinorVersion;
  }

  /**
   * @param method like "GET", "POST", "HEAD", etc.
   * @param path like "/foo/bar.html"
   * @param version like "HTTP/1.1"
   * @param host like "www.android.com:1234"
   * @param scheme like "https"
   */
  public void addSpdyRequestHeaders(String method, String path, String version, String host,
      String scheme) {
    // TODO: populate the statusLine for the client's benefit?
    add(":method", method);
    add(":scheme", scheme);
    add(":path", path);
    add(":version", version);
    add(":host", host);
  }

  public String getStatusLine() {
    return statusLine;
  }

  /**
   * Returns the status line's HTTP minor version. This returns 0 for HTTP/1.0
   * and 1 for HTTP/1.1. This returns 1 if the HTTP version is unknown.
   */
  public int getHttpMinorVersion() {
    return httpMinorVersion != -1 ? httpMinorVersion : 1;
  }

  /** Returns the HTTP status code or -1 if it is unknown. */
  public int getResponseCode() {
    return responseCode;
  }

  /** Returns the HTTP status message or null if it is unknown. */
  public String getResponseMessage() {
    return responseMessage;
  }

  /**
   * Add an HTTP header line containing a field name, a literal colon, and a
   * value. This works around empty header names and header names that start
   * with a colon (created by old broken SPDY versions of the response cache).
   */
  public void addLine(String line) {
    int index = line.indexOf(":", 1);
    if (index != -1) {
      addLenient(line.substring(0, index), line.substring(index + 1));
    } else if (line.startsWith(":")) {
      addLenient("", line.substring(1)); // Empty header name.
    } else {
      addLenient("", line); // No header name.
    }
  }

  /** Add a field with the specified value. */
  public void add(String fieldName, String value) {
    if (fieldName == null) throw new IllegalArgumentException("fieldname == null");
    if (value == null) throw new IllegalArgumentException("value == null");
    if (fieldName.length() == 0 || fieldName.indexOf('\0') != -1 || value.indexOf('\0') != -1) {
      throw new IllegalArgumentException("Unexpected header: " + fieldName + ": " + value);
    }
    addLenient(fieldName, value);
  }

  /**
   * Add a field with the specified value without any validation. Only
   * appropriate for headers from the remote peer.
   */
  private void addLenient(String fieldName, String value) {
    namesAndValues.add(fieldName);
    namesAndValues.add(value.trim());
  }

  public void removeAll(String fieldName) {
    for (int i = 0; i < namesAndValues.size(); i += 2) {
      if (fieldName.equalsIgnoreCase(namesAndValues.get(i))) {
        namesAndValues.remove(i); // field name
        namesAndValues.remove(i); // value
      }
    }
  }

  public void addAll(String fieldName, List<String> headerFields) {
    for (String value : headerFields) {
      add(fieldName, value);
    }
  }

  /**
   * Set a field with the specified value. If the field is not found, it is
   * added. If the field is found, the existing values are replaced.
   */
  public void set(String fieldName, String value) {
    removeAll(fieldName);
    add(fieldName, value);
  }

  /** Returns the number of field values. */
  public int length() {
    return namesAndValues.size() / 2;
  }

  /** Returns the field at {@code position} or null if that is out of range. */
  public String getFieldName(int index) {
    int fieldNameIndex = index * 2;
    if (fieldNameIndex < 0 || fieldNameIndex >= namesAndValues.size()) {
      return null;
    }
    return namesAndValues.get(fieldNameIndex);
  }

  /** Returns an immutable case-insensitive set of header names. */
  public Set<String> names() {
    TreeSet<String> result = new TreeSet<String>(String.CASE_INSENSITIVE_ORDER);
    for (int i = 0; i < length(); i++) {
      result.add(getFieldName(i));
    }
    return Collections.unmodifiableSet(result);
  }

  /** Returns the value at {@code index} or null if that is out of range. */
  public String getValue(int index) {
    int valueIndex = index * 2 + 1;
    if (valueIndex < 0 || valueIndex >= namesAndValues.size()) {
      return null;
    }
    return namesAndValues.get(valueIndex);
  }

  /** Returns the last value corresponding to the specified field, or null. */
  public String get(String fieldName) {
    for (int i = namesAndValues.size() - 2; i >= 0; i -= 2) {
      if (fieldName.equalsIgnoreCase(namesAndValues.get(i))) {
        return namesAndValues.get(i + 1);
      }
    }
    return null;
  }

  /** Returns an immutable list of the header values for {@code name}. */
  public List<String> values(String name) {
    List<String> result = null;
    for (int i = 0; i < length(); i++) {
      if (name.equalsIgnoreCase(getFieldName(i))) {
        if (result == null) result = new ArrayList<String>(2);
        result.add(getValue(i));
      }
    }
    return result != null
        ? Collections.unmodifiableList(result)
        : Collections.<String>emptyList();
  }

  /** @param fieldNames a case-insensitive set of HTTP header field names. */
  public RawHeaders getAll(Set<String> fieldNames) {
    RawHeaders result = new RawHeaders();
    for (int i = 0; i < namesAndValues.size(); i += 2) {
      String fieldName = namesAndValues.get(i);
      if (fieldNames.contains(fieldName)) {
        result.add(fieldName, namesAndValues.get(i + 1));
      }
    }
    return result;
  }

  /** Returns bytes of a request header for sending on an HTTP transport. */
  public byte[] toBytes() throws UnsupportedEncodingException {
    StringBuilder result = new StringBuilder(256);
    result.append(requestLine).append("\r\n");
    for (int i = 0; i < namesAndValues.size(); i += 2) {
      result.append(namesAndValues.get(i))
          .append(": ")
          .append(namesAndValues.get(i + 1))
          .append("\r\n");
    }
    result.append("\r\n");
    return result.toString().getBytes("ISO-8859-1");
  }

  /** Parses bytes of a response header from an HTTP transport. */
  public static RawHeaders fromBytes(InputStream in) throws IOException {
    RawHeaders headers;
    do {
      headers = new RawHeaders();
      headers.setStatusLine(Util.readAsciiLine(in));
      readHeaders(in, headers);
    } while (headers.getResponseCode() == HttpEngine.HTTP_CONTINUE);
    return headers;
  }

  /** Reads headers or trailers into {@code out}. */
  public static void readHeaders(InputStream in, RawHeaders out) throws IOException {
    // parse the result headers until the first blank line
    String line;
    while ((line = Util.readAsciiLine(in)).length() != 0) {
      out.addLine(line);
    }
  }

  /**
   * Returns an immutable map containing each field to its list of values. The
   * status line is mapped to null.
   */
  public Map<String, List<String>> toMultimap(boolean response) {
    Map<String, List<String>> result = new TreeMap<String, List<String>>(FIELD_NAME_COMPARATOR);
    for (int i = 0; i < namesAndValues.size(); i += 2) {
      String fieldName = namesAndValues.get(i);
      String value = namesAndValues.get(i + 1);

      List<String> allValues = new ArrayList<String>();
      List<String> otherValues = result.get(fieldName);
      if (otherValues != null) {
        allValues.addAll(otherValues);
      }
      allValues.add(value);
      result.put(fieldName, Collections.unmodifiableList(allValues));
    }
    if (response && statusLine != null) {
      result.put(null, Collections.unmodifiableList(Collections.singletonList(statusLine)));
    } else if (requestLine != null) {
      result.put(null, Collections.unmodifiableList(Collections.singletonList(requestLine)));
    }
    return Collections.unmodifiableMap(result);
  }

  /**
   * Creates a new instance from the given map of fields to values. If
   * present, the null field's last element will be used to set the status
   * line.
   */
  public static RawHeaders fromMultimap(Map<String, List<String>> map, boolean response)
      throws IOException {
    if (!response) throw new UnsupportedOperationException();
    RawHeaders result = new RawHeaders();
    for (Entry<String, List<String>> entry : map.entrySet()) {
      String fieldName = entry.getKey();
      List<String> values = entry.getValue();
      if (fieldName != null) {
        for (String value : values) {
          result.addLenient(fieldName, value);
        }
      } else if (!values.isEmpty()) {
        result.setStatusLine(values.get(values.size() - 1));
      }
    }
    return result;
  }

  /**
   * Returns a list of alternating names and values. Names are all lower case.
   * No names are repeated. If any name has multiple values, they are
   * concatenated using "\0" as a delimiter.
   */
  public List<String> toNameValueBlock() {
    Set<String> names = new HashSet<String>();
    List<String> result = new ArrayList<String>();
    for (int i = 0; i < namesAndValues.size(); i += 2) {
      String name = namesAndValues.get(i).toLowerCase(Locale.US);
      String value = namesAndValues.get(i + 1);

      // Drop headers that are forbidden when layering HTTP over SPDY.
      if (name.equals("connection")
          || name.equals("host")
          || name.equals("keep-alive")
          || name.equals("proxy-connection")
          || name.equals("transfer-encoding")) {
        continue;
      }

      // If we haven't seen this name before, add the pair to the end of the list...
      if (names.add(name)) {
        result.add(name);
        result.add(value);
        continue;
      }

      // ...otherwise concatenate the existing values and this value.
      for (int j = 0; j < result.size(); j += 2) {
        if (name.equals(result.get(j))) {
          result.set(j + 1, result.get(j + 1) + "\0" + value);
          break;
        }
      }
    }
    return result;
  }

  /** Returns headers for a name value block containing a SPDY response. */
  public static RawHeaders fromNameValueBlock(List<String> nameValueBlock) throws IOException {
    if (nameValueBlock.size() % 2 != 0) {
      throw new IllegalArgumentException("Unexpected name value block: " + nameValueBlock);
    }
    String status = null;
    String version = null;
    RawHeaders result = new RawHeaders();
    for (int i = 0; i < nameValueBlock.size(); i += 2) {
      String name = nameValueBlock.get(i);
      String values = nameValueBlock.get(i + 1);
      for (int start = 0; start < values.length(); ) {
        int end = values.indexOf('\0', start);
        if (end == -1) {
          end = values.length();
        }
        String value = values.substring(start, end);
        if (":status".equals(name)) {
          status = value;
        } else if (":version".equals(name)) {
          version = value;
        } else {
          result.namesAndValues.add(name);
          result.namesAndValues.add(value);
        }
        start = end + 1;
      }
    }
    if (status == null) throw new ProtocolException("Expected ':status' header not present");
    if (version == null) throw new ProtocolException("Expected ':version' header not present");
    result.setStatusLine(version + " " + status);
    return result;
  }
}


File: platforms/android/CordovaLib/src/com/squareup/okhttp/internal/http/RequestHeaders.java
/*
 * Copyright (C) 2011 The Android Open Source Project
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

import java.net.URI;
import java.util.Date;
import java.util.List;
import java.util.Map;

/** Parsed HTTP request headers. */
public final class RequestHeaders {
  private final URI uri;
  private final RawHeaders headers;

  /** Don't use a cache to satisfy this request. */
  private boolean noCache;
  private int maxAgeSeconds = -1;
  private int maxStaleSeconds = -1;
  private int minFreshSeconds = -1;

  /**
   * This field's name "only-if-cached" is misleading. It actually means "do
   * not use the network". It is set by a client who only wants to make a
   * request if it can be fully satisfied by the cache. Cached responses that
   * would require validation (ie. conditional gets) are not permitted if this
   * header is set.
   */
  private boolean onlyIfCached;

  /**
   * True if the request contains an authorization field. Although this isn't
   * necessarily a shared cache, it follows the spec's strict requirements for
   * shared caches.
   */
  private boolean hasAuthorization;

  private long contentLength = -1;
  private String transferEncoding;
  private String userAgent;
  private String host;
  private String connection;
  private String acceptEncoding;
  private String contentType;
  private String ifModifiedSince;
  private String ifNoneMatch;
  private String proxyAuthorization;

  public RequestHeaders(URI uri, RawHeaders headers) {
    this.uri = uri;
    this.headers = headers;

    HeaderParser.CacheControlHandler handler = new HeaderParser.CacheControlHandler() {
      @Override public void handle(String directive, String parameter) {
        if ("no-cache".equalsIgnoreCase(directive)) {
          noCache = true;
        } else if ("max-age".equalsIgnoreCase(directive)) {
          maxAgeSeconds = HeaderParser.parseSeconds(parameter);
        } else if ("max-stale".equalsIgnoreCase(directive)) {
          maxStaleSeconds = HeaderParser.parseSeconds(parameter);
        } else if ("min-fresh".equalsIgnoreCase(directive)) {
          minFreshSeconds = HeaderParser.parseSeconds(parameter);
        } else if ("only-if-cached".equalsIgnoreCase(directive)) {
          onlyIfCached = true;
        }
      }
    };

    for (int i = 0; i < headers.length(); i++) {
      String fieldName = headers.getFieldName(i);
      String value = headers.getValue(i);
      if ("Cache-Control".equalsIgnoreCase(fieldName)) {
        HeaderParser.parseCacheControl(value, handler);
      } else if ("Pragma".equalsIgnoreCase(fieldName)) {
        if ("no-cache".equalsIgnoreCase(value)) {
          noCache = true;
        }
      } else if ("If-None-Match".equalsIgnoreCase(fieldName)) {
        ifNoneMatch = value;
      } else if ("If-Modified-Since".equalsIgnoreCase(fieldName)) {
        ifModifiedSince = value;
      } else if ("Authorization".equalsIgnoreCase(fieldName)) {
        hasAuthorization = true;
      } else if ("Content-Length".equalsIgnoreCase(fieldName)) {
        try {
          contentLength = Integer.parseInt(value);
        } catch (NumberFormatException ignored) {
        }
      } else if ("Transfer-Encoding".equalsIgnoreCase(fieldName)) {
        transferEncoding = value;
      } else if ("User-Agent".equalsIgnoreCase(fieldName)) {
        userAgent = value;
      } else if ("Host".equalsIgnoreCase(fieldName)) {
        host = value;
      } else if ("Connection".equalsIgnoreCase(fieldName)) {
        connection = value;
      } else if ("Accept-Encoding".equalsIgnoreCase(fieldName)) {
        acceptEncoding = value;
      } else if ("Content-Type".equalsIgnoreCase(fieldName)) {
        contentType = value;
      } else if ("Proxy-Authorization".equalsIgnoreCase(fieldName)) {
        proxyAuthorization = value;
      }
    }
  }

  public boolean isChunked() {
    return "chunked".equalsIgnoreCase(transferEncoding);
  }

  public boolean hasConnectionClose() {
    return "close".equalsIgnoreCase(connection);
  }

  public URI getUri() {
    return uri;
  }

  public RawHeaders getHeaders() {
    return headers;
  }

  public boolean isNoCache() {
    return noCache;
  }

  public int getMaxAgeSeconds() {
    return maxAgeSeconds;
  }

  public int getMaxStaleSeconds() {
    return maxStaleSeconds;
  }

  public int getMinFreshSeconds() {
    return minFreshSeconds;
  }

  public boolean isOnlyIfCached() {
    return onlyIfCached;
  }

  public boolean hasAuthorization() {
    return hasAuthorization;
  }

  public long getContentLength() {
    return contentLength;
  }

  public String getTransferEncoding() {
    return transferEncoding;
  }

  public String getUserAgent() {
    return userAgent;
  }

  public String getHost() {
    return host;
  }

  public String getConnection() {
    return connection;
  }

  public String getAcceptEncoding() {
    return acceptEncoding;
  }

  public String getContentType() {
    return contentType;
  }

  public String getIfModifiedSince() {
    return ifModifiedSince;
  }

  public String getIfNoneMatch() {
    return ifNoneMatch;
  }

  public String getProxyAuthorization() {
    return proxyAuthorization;
  }

  public void setChunked() {
    if (this.transferEncoding != null) {
      headers.removeAll("Transfer-Encoding");
    }
    headers.add("Transfer-Encoding", "chunked");
    this.transferEncoding = "chunked";
  }

  public void setContentLength(long contentLength) {
    if (this.contentLength != -1) {
      headers.removeAll("Content-Length");
    }
    headers.add("Content-Length", Long.toString(contentLength));
    this.contentLength = contentLength;
  }

  /**
   * Remove the Content-Length headers. Call this when dropping the body on a
   * request or response, such as when a redirect changes the method from POST
   * to GET.
   */
  public void removeContentLength() {
    if (contentLength != -1) {
      headers.removeAll("Content-Length");
      contentLength = -1;
    }
  }

  public void setUserAgent(String userAgent) {
    if (this.userAgent != null) {
      headers.removeAll("User-Agent");
    }
    headers.add("User-Agent", userAgent);
    this.userAgent = userAgent;
  }

  public void setHost(String host) {
    if (this.host != null) {
      headers.removeAll("Host");
    }
    headers.add("Host", host);
    this.host = host;
  }

  public void setConnection(String connection) {
    if (this.connection != null) {
      headers.removeAll("Connection");
    }
    headers.add("Connection", connection);
    this.connection = connection;
  }

  public void setAcceptEncoding(String acceptEncoding) {
    if (this.acceptEncoding != null) {
      headers.removeAll("Accept-Encoding");
    }
    headers.add("Accept-Encoding", acceptEncoding);
    this.acceptEncoding = acceptEncoding;
  }

  public void setContentType(String contentType) {
    if (this.contentType != null) {
      headers.removeAll("Content-Type");
    }
    headers.add("Content-Type", contentType);
    this.contentType = contentType;
  }

  public void setIfModifiedSince(Date date) {
    if (ifModifiedSince != null) {
      headers.removeAll("If-Modified-Since");
    }
    String formattedDate = HttpDate.format(date);
    headers.add("If-Modified-Since", formattedDate);
    ifModifiedSince = formattedDate;
  }

  public void setIfNoneMatch(String ifNoneMatch) {
    if (this.ifNoneMatch != null) {
      headers.removeAll("If-None-Match");
    }
    headers.add("If-None-Match", ifNoneMatch);
    this.ifNoneMatch = ifNoneMatch;
  }

  /**
   * Returns true if the request contains conditions that save the server from
   * sending a response that the client has locally. When the caller adds
   * conditions, this cache won't participate in the request.
   */
  public boolean hasConditions() {
    return ifModifiedSince != null || ifNoneMatch != null;
  }

  public void addCookies(Map<String, List<String>> allCookieHeaders) {
    for (Map.Entry<String, List<String>> entry : allCookieHeaders.entrySet()) {
      String key = entry.getKey();
      if (("Cookie".equalsIgnoreCase(key) || "Cookie2".equalsIgnoreCase(key))
          && !entry.getValue().isEmpty()) {
        headers.add(key, buildCookieHeader(entry.getValue()));
      }
    }
  }

  /**
   * Send all cookies in one big header, as recommended by
   * <a href="http://tools.ietf.org/html/rfc6265#section-4.2.1">RFC 6265</a>.
   */
  private String buildCookieHeader(List<String> cookies) {
    if (cookies.size() == 1) return cookies.get(0);
    StringBuilder sb = new StringBuilder();
    for (int i = 0; i < cookies.size(); i++) {
      if (i > 0) sb.append("; ");
      sb.append(cookies.get(i));
    }
    return sb.toString();
  }
}


File: platforms/android/CordovaLib/src/com/squareup/okhttp/internal/http/ResponseHeaders.java
/*
 * Copyright (C) 2011 The Android Open Source Project
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

import com.squareup.okhttp.ResponseSource;
import com.squareup.okhttp.internal.Platform;
import java.io.IOException;
import java.net.HttpURLConnection;
import java.net.URI;
import java.util.Collections;
import java.util.Date;
import java.util.List;
import java.util.Map;
import java.util.Set;
import java.util.TreeSet;
import java.util.concurrent.TimeUnit;

import static com.squareup.okhttp.internal.Util.equal;

/** Parsed HTTP response headers. */
public final class ResponseHeaders {

  /** HTTP header name for the local time when the request was sent. */
  private static final String SENT_MILLIS = Platform.get().getPrefix() + "-Sent-Millis";

  /** HTTP header name for the local time when the response was received. */
  private static final String RECEIVED_MILLIS = Platform.get().getPrefix() + "-Received-Millis";

  /** HTTP synthetic header with the response source. */
  static final String RESPONSE_SOURCE = Platform.get().getPrefix() + "-Response-Source";

  /** HTTP synthetic header with the selected transport (spdy/3, http/1.1, etc). */
  static final String SELECTED_TRANSPORT = Platform.get().getPrefix() + "-Selected-Transport";

  private final URI uri;
  private final RawHeaders headers;

  /** The server's time when this response was served, if known. */
  private Date servedDate;

  /** The last modified date of the response, if known. */
  private Date lastModified;

  /**
   * The expiration date of the response, if known. If both this field and the
   * max age are set, the max age is preferred.
   */
  private Date expires;

  /**
   * Extension header set by HttpURLConnectionImpl specifying the timestamp
   * when the HTTP request was first initiated.
   */
  private long sentRequestMillis;

  /**
   * Extension header set by HttpURLConnectionImpl specifying the timestamp
   * when the HTTP response was first received.
   */
  private long receivedResponseMillis;

  /**
   * In the response, this field's name "no-cache" is misleading. It doesn't
   * prevent us from caching the response; it only means we have to validate
   * the response with the origin server before returning it. We can do this
   * with a conditional get.
   */
  private boolean noCache;

  /** If true, this response should not be cached. */
  private boolean noStore;

  /**
   * The duration past the response's served date that it can be served
   * without validation.
   */
  private int maxAgeSeconds = -1;

  /**
   * The "s-maxage" directive is the max age for shared caches. Not to be
   * confused with "max-age" for non-shared caches, As in Firefox and Chrome,
   * this directive is not honored by this cache.
   */
  private int sMaxAgeSeconds = -1;

  /**
   * This request header field's name "only-if-cached" is misleading. It
   * actually means "do not use the network". It is set by a client who only
   * wants to make a request if it can be fully satisfied by the cache.
   * Cached responses that would require validation (ie. conditional gets) are
   * not permitted if this header is set.
   */
  private boolean isPublic;
  private boolean mustRevalidate;
  private String etag;
  private int ageSeconds = -1;

  /** Case-insensitive set of field names. */
  private Set<String> varyFields = Collections.emptySet();

  private String contentEncoding;
  private String transferEncoding;
  private long contentLength = -1;
  private String connection;
  private String contentType;

  public ResponseHeaders(URI uri, RawHeaders headers) {
    this.uri = uri;
    this.headers = headers;

    HeaderParser.CacheControlHandler handler = new HeaderParser.CacheControlHandler() {
      @Override public void handle(String directive, String parameter) {
        if ("no-cache".equalsIgnoreCase(directive)) {
          noCache = true;
        } else if ("no-store".equalsIgnoreCase(directive)) {
          noStore = true;
        } else if ("max-age".equalsIgnoreCase(directive)) {
          maxAgeSeconds = HeaderParser.parseSeconds(parameter);
        } else if ("s-maxage".equalsIgnoreCase(directive)) {
          sMaxAgeSeconds = HeaderParser.parseSeconds(parameter);
        } else if ("public".equalsIgnoreCase(directive)) {
          isPublic = true;
        } else if ("must-revalidate".equalsIgnoreCase(directive)) {
          mustRevalidate = true;
        }
      }
    };

    for (int i = 0; i < headers.length(); i++) {
      String fieldName = headers.getFieldName(i);
      String value = headers.getValue(i);
      if ("Cache-Control".equalsIgnoreCase(fieldName)) {
        HeaderParser.parseCacheControl(value, handler);
      } else if ("Date".equalsIgnoreCase(fieldName)) {
        servedDate = HttpDate.parse(value);
      } else if ("Expires".equalsIgnoreCase(fieldName)) {
        expires = HttpDate.parse(value);
      } else if ("Last-Modified".equalsIgnoreCase(fieldName)) {
        lastModified = HttpDate.parse(value);
      } else if ("ETag".equalsIgnoreCase(fieldName)) {
        etag = value;
      } else if ("Pragma".equalsIgnoreCase(fieldName)) {
        if ("no-cache".equalsIgnoreCase(value)) {
          noCache = true;
        }
      } else if ("Age".equalsIgnoreCase(fieldName)) {
        ageSeconds = HeaderParser.parseSeconds(value);
      } else if ("Vary".equalsIgnoreCase(fieldName)) {
        // Replace the immutable empty set with something we can mutate.
        if (varyFields.isEmpty()) {
          varyFields = new TreeSet<String>(String.CASE_INSENSITIVE_ORDER);
        }
        for (String varyField : value.split(",")) {
          varyFields.add(varyField.trim());
        }
      } else if ("Content-Encoding".equalsIgnoreCase(fieldName)) {
        contentEncoding = value;
      } else if ("Transfer-Encoding".equalsIgnoreCase(fieldName)) {
        transferEncoding = value;
      } else if ("Content-Length".equalsIgnoreCase(fieldName)) {
        try {
          contentLength = Long.parseLong(value);
        } catch (NumberFormatException ignored) {
        }
      } else if ("Content-Type".equalsIgnoreCase(fieldName)) {
        contentType = value;
      } else if ("Connection".equalsIgnoreCase(fieldName)) {
        connection = value;
      } else if (SENT_MILLIS.equalsIgnoreCase(fieldName)) {
        sentRequestMillis = Long.parseLong(value);
      } else if (RECEIVED_MILLIS.equalsIgnoreCase(fieldName)) {
        receivedResponseMillis = Long.parseLong(value);
      }
    }
  }

  public boolean isContentEncodingGzip() {
    return "gzip".equalsIgnoreCase(contentEncoding);
  }

  public void stripContentEncoding() {
    contentEncoding = null;
    headers.removeAll("Content-Encoding");
  }

  public void stripContentLength() {
    contentLength = -1;
    headers.removeAll("Content-Length");
  }

  public boolean isChunked() {
    return "chunked".equalsIgnoreCase(transferEncoding);
  }

  public boolean hasConnectionClose() {
    return "close".equalsIgnoreCase(connection);
  }

  public URI getUri() {
    return uri;
  }

  public RawHeaders getHeaders() {
    return headers;
  }

  public Date getServedDate() {
    return servedDate;
  }

  public Date getLastModified() {
    return lastModified;
  }

  public Date getExpires() {
    return expires;
  }

  public boolean isNoCache() {
    return noCache;
  }

  public boolean isNoStore() {
    return noStore;
  }

  public int getMaxAgeSeconds() {
    return maxAgeSeconds;
  }

  public int getSMaxAgeSeconds() {
    return sMaxAgeSeconds;
  }

  public boolean isPublic() {
    return isPublic;
  }

  public boolean isMustRevalidate() {
    return mustRevalidate;
  }

  public String getEtag() {
    return etag;
  }

  public Set<String> getVaryFields() {
    return varyFields;
  }

  public String getContentEncoding() {
    return contentEncoding;
  }

  public long getContentLength() {
    return contentLength;
  }

  public String getContentType() {
    return contentType;
  }

  public String getConnection() {
    return connection;
  }

  public void setLocalTimestamps(long sentRequestMillis, long receivedResponseMillis) {
    this.sentRequestMillis = sentRequestMillis;
    headers.add(SENT_MILLIS, Long.toString(sentRequestMillis));
    this.receivedResponseMillis = receivedResponseMillis;
    headers.add(RECEIVED_MILLIS, Long.toString(receivedResponseMillis));
  }

  public void setResponseSource(ResponseSource responseSource) {
    headers.set(RESPONSE_SOURCE, responseSource.toString() + " " + headers.getResponseCode());
  }

  public void setTransport(String transport) {
    headers.set(SELECTED_TRANSPORT, transport);
  }

  /**
   * Returns the current age of the response, in milliseconds. The calculation
   * is specified by RFC 2616, 13.2.3 Age Calculations.
   */
  private long computeAge(long nowMillis) {
    long apparentReceivedAge =
        servedDate != null ? Math.max(0, receivedResponseMillis - servedDate.getTime()) : 0;
    long receivedAge =
        ageSeconds != -1 ? Math.max(apparentReceivedAge, TimeUnit.SECONDS.toMillis(ageSeconds))
            : apparentReceivedAge;
    long responseDuration = receivedResponseMillis - sentRequestMillis;
    long residentDuration = nowMillis - receivedResponseMillis;
    return receivedAge + responseDuration + residentDuration;
  }

  /**
   * Returns the number of milliseconds that the response was fresh for,
   * starting from the served date.
   */
  private long computeFreshnessLifetime() {
    if (maxAgeSeconds != -1) {
      return TimeUnit.SECONDS.toMillis(maxAgeSeconds);
    } else if (expires != null) {
      long servedMillis = servedDate != null ? servedDate.getTime() : receivedResponseMillis;
      long delta = expires.getTime() - servedMillis;
      return delta > 0 ? delta : 0;
    } else if (lastModified != null && uri.getRawQuery() == null) {
      // As recommended by the HTTP RFC and implemented in Firefox, the
      // max age of a document should be defaulted to 10% of the
      // document's age at the time it was served. Default expiration
      // dates aren't used for URIs containing a query.
      long servedMillis = servedDate != null ? servedDate.getTime() : sentRequestMillis;
      long delta = servedMillis - lastModified.getTime();
      return delta > 0 ? (delta / 10) : 0;
    }
    return 0;
  }

  /**
   * Returns true if computeFreshnessLifetime used a heuristic. If we used a
   * heuristic to serve a cached response older than 24 hours, we are required
   * to attach a warning.
   */
  private boolean isFreshnessLifetimeHeuristic() {
    return maxAgeSeconds == -1 && expires == null;
  }

  /**
   * Returns true if this response can be stored to later serve another
   * request.
   */
  public boolean isCacheable(RequestHeaders request) {
    // Always go to network for uncacheable response codes (RFC 2616, 13.4),
    // This implementation doesn't support caching partial content.
    int responseCode = headers.getResponseCode();
    if (responseCode != HttpURLConnection.HTTP_OK
        && responseCode != HttpURLConnection.HTTP_NOT_AUTHORITATIVE
        && responseCode != HttpURLConnection.HTTP_MULT_CHOICE
        && responseCode != HttpURLConnection.HTTP_MOVED_PERM
        && responseCode != HttpURLConnection.HTTP_GONE) {
      return false;
    }

    // Responses to authorized requests aren't cacheable unless they include
    // a 'public', 'must-revalidate' or 's-maxage' directive.
    if (request.hasAuthorization() && !isPublic && !mustRevalidate && sMaxAgeSeconds == -1) {
      return false;
    }

    if (noStore) {
      return false;
    }

    return true;
  }

  /**
   * Returns true if a Vary header contains an asterisk. Such responses cannot
   * be cached.
   */
  public boolean hasVaryAll() {
    return varyFields.contains("*");
  }

  /**
   * Returns true if none of the Vary headers on this response have changed
   * between {@code cachedRequest} and {@code newRequest}.
   */
  public boolean varyMatches(Map<String, List<String>> cachedRequest,
      Map<String, List<String>> newRequest) {
    for (String field : varyFields) {
      if (!equal(cachedRequest.get(field), newRequest.get(field))) {
        return false;
      }
    }
    return true;
  }

  /** Returns the source to satisfy {@code request} given this cached response. */
  public ResponseSource chooseResponseSource(long nowMillis, RequestHeaders request) {
    // If this response shouldn't have been stored, it should never be used
    // as a response source. This check should be redundant as long as the
    // persistence store is well-behaved and the rules are constant.
    if (!isCacheable(request)) {
      return ResponseSource.NETWORK;
    }

    if (request.isNoCache() || request.hasConditions()) {
      return ResponseSource.NETWORK;
    }

    long ageMillis = computeAge(nowMillis);
    long freshMillis = computeFreshnessLifetime();

    if (request.getMaxAgeSeconds() != -1) {
      freshMillis = Math.min(freshMillis, TimeUnit.SECONDS.toMillis(request.getMaxAgeSeconds()));
    }

    long minFreshMillis = 0;
    if (request.getMinFreshSeconds() != -1) {
      minFreshMillis = TimeUnit.SECONDS.toMillis(request.getMinFreshSeconds());
    }

    long maxStaleMillis = 0;
    if (!mustRevalidate && request.getMaxStaleSeconds() != -1) {
      maxStaleMillis = TimeUnit.SECONDS.toMillis(request.getMaxStaleSeconds());
    }

    if (!noCache && ageMillis + minFreshMillis < freshMillis + maxStaleMillis) {
      if (ageMillis + minFreshMillis >= freshMillis) {
        headers.add("Warning", "110 HttpURLConnection \"Response is stale\"");
      }
      long oneDayMillis = 24 * 60 * 60 * 1000L;
      if (ageMillis > oneDayMillis && isFreshnessLifetimeHeuristic()) {
        headers.add("Warning", "113 HttpURLConnection \"Heuristic expiration\"");
      }
      return ResponseSource.CACHE;
    }

    if (lastModified != null) {
      request.setIfModifiedSince(lastModified);
    } else if (servedDate != null) {
      request.setIfModifiedSince(servedDate);
    }

    if (etag != null) {
      request.setIfNoneMatch(etag);
    }

    return request.hasConditions() ? ResponseSource.CONDITIONAL_CACHE : ResponseSource.NETWORK;
  }

  /**
   * Returns true if this cached response should be used; false if the
   * network response should be used.
   */
  public boolean validate(ResponseHeaders networkResponse) {
    if (networkResponse.headers.getResponseCode() == HttpURLConnection.HTTP_NOT_MODIFIED) {
      return true;
    }

    // The HTTP spec says that if the network's response is older than our
    // cached response, we may return the cache's response. Like Chrome (but
    // unlike Firefox), this client prefers to return the newer response.
    if (lastModified != null
        && networkResponse.lastModified != null
        && networkResponse.lastModified.getTime() < lastModified.getTime()) {
      return true;
    }

    return false;
  }

  /**
   * Combines this cached header with a network header as defined by RFC 2616,
   * 13.5.3.
   */
  public ResponseHeaders combine(ResponseHeaders network) throws IOException {
    RawHeaders result = new RawHeaders();
    result.setStatusLine(headers.getStatusLine());

    for (int i = 0; i < headers.length(); i++) {
      String fieldName = headers.getFieldName(i);
      String value = headers.getValue(i);
      if ("Warning".equals(fieldName) && value.startsWith("1")) {
        continue; // drop 100-level freshness warnings
      }
      if (!isEndToEnd(fieldName) || network.headers.get(fieldName) == null) {
        result.add(fieldName, value);
      }
    }

    for (int i = 0; i < network.headers.length(); i++) {
      String fieldName = network.headers.getFieldName(i);
      if (isEndToEnd(fieldName)) {
        result.add(fieldName, network.headers.getValue(i));
      }
    }

    return new ResponseHeaders(uri, result);
  }

  /**
   * Returns true if {@code fieldName} is an end-to-end HTTP header, as
   * defined by RFC 2616, 13.5.1.
   */
  private static boolean isEndToEnd(String fieldName) {
    return !"Connection".equalsIgnoreCase(fieldName)
        && !"Keep-Alive".equalsIgnoreCase(fieldName)
        && !"Proxy-Authenticate".equalsIgnoreCase(fieldName)
        && !"Proxy-Authorization".equalsIgnoreCase(fieldName)
        && !"TE".equalsIgnoreCase(fieldName)
        && !"Trailers".equalsIgnoreCase(fieldName)
        && !"Transfer-Encoding".equalsIgnoreCase(fieldName)
        && !"Upgrade".equalsIgnoreCase(fieldName);
  }
}


File: platforms/android/CordovaLib/src/com/squareup/okhttp/internal/http/RetryableOutputStream.java
/*
 * Copyright (C) 2010 The Android Open Source Project
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

import com.squareup.okhttp.internal.AbstractOutputStream;
import java.io.ByteArrayOutputStream;
import java.io.IOException;
import java.io.OutputStream;
import java.net.ProtocolException;

import static com.squareup.okhttp.internal.Util.checkOffsetAndCount;

/**
 * An HTTP request body that's completely buffered in memory. This allows
 * the post body to be transparently re-sent if the HTTP request must be
 * sent multiple times.
 */
final class RetryableOutputStream extends AbstractOutputStream {
  private final int limit;
  private final ByteArrayOutputStream content;

  public RetryableOutputStream(int limit) {
    this.limit = limit;
    this.content = new ByteArrayOutputStream(limit);
  }

  public RetryableOutputStream() {
    this.limit = -1;
    this.content = new ByteArrayOutputStream();
  }

  @Override public synchronized void close() throws IOException {
    if (closed) {
      return;
    }
    closed = true;
    if (content.size() < limit) {
      throw new ProtocolException(
          "content-length promised " + limit + " bytes, but received " + content.size());
    }
  }

  @Override public synchronized void write(byte[] buffer, int offset, int count)
      throws IOException {
    checkNotClosed();
    checkOffsetAndCount(buffer.length, offset, count);
    if (limit != -1 && content.size() > limit - count) {
      throw new ProtocolException("exceeded content-length limit of " + limit + " bytes");
    }
    content.write(buffer, offset, count);
  }

  public synchronized int contentLength() throws IOException {
    close();
    return content.size();
  }

  public void writeToSocket(OutputStream socketOut) throws IOException {
    content.writeTo(socketOut);
  }
}


File: platforms/android/CordovaLib/src/com/squareup/okhttp/internal/http/RouteSelector.java
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

import com.squareup.okhttp.Address;
import com.squareup.okhttp.Connection;
import com.squareup.okhttp.ConnectionPool;
import com.squareup.okhttp.Route;
import com.squareup.okhttp.RouteDatabase;
import com.squareup.okhttp.internal.Dns;
import java.io.IOException;
import java.net.InetAddress;
import java.net.InetSocketAddress;
import java.net.Proxy;
import java.net.ProxySelector;
import java.net.SocketAddress;
import java.net.URI;
import java.net.UnknownHostException;
import java.util.Iterator;
import java.util.LinkedList;
import java.util.List;
import java.util.NoSuchElementException;

import static com.squareup.okhttp.internal.Util.getEffectivePort;

/**
 * Selects routes to connect to an origin server. Each connection requires a
 * choice of proxy server, IP address, and TLS mode. Connections may also be
 * recycled.
 */
public final class RouteSelector {
  /** Uses {@link com.squareup.okhttp.internal.Platform#enableTlsExtensions}. */
  private static final int TLS_MODE_MODERN = 1;
  /** Uses {@link com.squareup.okhttp.internal.Platform#supportTlsIntolerantServer}. */
  private static final int TLS_MODE_COMPATIBLE = 0;
  /** No TLS mode. */
  private static final int TLS_MODE_NULL = -1;

  private final Address address;
  private final URI uri;
  private final ProxySelector proxySelector;
  private final ConnectionPool pool;
  private final Dns dns;
  private final RouteDatabase routeDatabase;

  /* The most recently attempted route. */
  private Proxy lastProxy;
  private InetSocketAddress lastInetSocketAddress;

  /* State for negotiating the next proxy to use. */
  private boolean hasNextProxy;
  private Proxy userSpecifiedProxy;
  private Iterator<Proxy> proxySelectorProxies;

  /* State for negotiating the next InetSocketAddress to use. */
  private InetAddress[] socketAddresses;
  private int nextSocketAddressIndex;
  private int socketPort;

  /* State for negotiating the next TLS configuration */
  private int nextTlsMode = TLS_MODE_NULL;

  /* State for negotiating failed routes */
  private final List<Route> postponedRoutes;

  public RouteSelector(Address address, URI uri, ProxySelector proxySelector, ConnectionPool pool,
      Dns dns, RouteDatabase routeDatabase) {
    this.address = address;
    this.uri = uri;
    this.proxySelector = proxySelector;
    this.pool = pool;
    this.dns = dns;
    this.routeDatabase = routeDatabase;
    this.postponedRoutes = new LinkedList<Route>();

    resetNextProxy(uri, address.getProxy());
  }

  /**
   * Returns true if there's another route to attempt. Every address has at
   * least one route.
   */
  public boolean hasNext() {
    return hasNextTlsMode() || hasNextInetSocketAddress() || hasNextProxy() || hasNextPostponed();
  }

  /**
   * Returns the next route address to attempt.
   *
   * @throws NoSuchElementException if there are no more routes to attempt.
   */
  public Connection next(String method) throws IOException {
    // Always prefer pooled connections over new connections.
    for (Connection pooled; (pooled = pool.get(address)) != null; ) {
      if (method.equals("GET") || pooled.isReadable()) return pooled;
      pooled.close();
    }

    // Compute the next route to attempt.
    if (!hasNextTlsMode()) {
      if (!hasNextInetSocketAddress()) {
        if (!hasNextProxy()) {
          if (!hasNextPostponed()) {
            throw new NoSuchElementException();
          }
          return new Connection(nextPostponed());
        }
        lastProxy = nextProxy();
        resetNextInetSocketAddress(lastProxy);
      }
      lastInetSocketAddress = nextInetSocketAddress();
      resetNextTlsMode();
    }

    boolean modernTls = nextTlsMode() == TLS_MODE_MODERN;
    Route route = new Route(address, lastProxy, lastInetSocketAddress, modernTls);
    if (routeDatabase.shouldPostpone(route)) {
      postponedRoutes.add(route);
      // We will only recurse in order to skip previously failed routes. They will be
      // tried last.
      return next(method);
    }

    return new Connection(route);
  }

  /**
   * Clients should invoke this method when they encounter a connectivity
   * failure on a connection returned by this route selector.
   */
  public void connectFailed(Connection connection, IOException failure) {
    Route failedRoute = connection.getRoute();
    if (failedRoute.getProxy().type() != Proxy.Type.DIRECT && proxySelector != null) {
      // Tell the proxy selector when we fail to connect on a fresh connection.
      proxySelector.connectFailed(uri, failedRoute.getProxy().address(), failure);
    }

    routeDatabase.failed(failedRoute, failure);
  }

  /** Resets {@link #nextProxy} to the first option. */
  private void resetNextProxy(URI uri, Proxy proxy) {
    this.hasNextProxy = true; // This includes NO_PROXY!
    if (proxy != null) {
      this.userSpecifiedProxy = proxy;
    } else {
      List<Proxy> proxyList = proxySelector.select(uri);
      if (proxyList != null) {
        this.proxySelectorProxies = proxyList.iterator();
      }
    }
  }

  /** Returns true if there's another proxy to try. */
  private boolean hasNextProxy() {
    return hasNextProxy;
  }

  /** Returns the next proxy to try. May be PROXY.NO_PROXY but never null. */
  private Proxy nextProxy() {
    // If the user specifies a proxy, try that and only that.
    if (userSpecifiedProxy != null) {
      hasNextProxy = false;
      return userSpecifiedProxy;
    }

    // Try each of the ProxySelector choices until one connection succeeds. If none succeed
    // then we'll try a direct connection below.
    if (proxySelectorProxies != null) {
      while (proxySelectorProxies.hasNext()) {
        Proxy candidate = proxySelectorProxies.next();
        if (candidate.type() != Proxy.Type.DIRECT) {
          return candidate;
        }
      }
    }

    // Finally try a direct connection.
    hasNextProxy = false;
    return Proxy.NO_PROXY;
  }

  /** Resets {@link #nextInetSocketAddress} to the first option. */
  private void resetNextInetSocketAddress(Proxy proxy) throws UnknownHostException {
    socketAddresses = null; // Clear the addresses. Necessary if getAllByName() below throws!

    String socketHost;
    if (proxy.type() == Proxy.Type.DIRECT) {
      socketHost = uri.getHost();
      socketPort = getEffectivePort(uri);
    } else {
      SocketAddress proxyAddress = proxy.address();
      if (!(proxyAddress instanceof InetSocketAddress)) {
        throw new IllegalArgumentException(
            "Proxy.address() is not an " + "InetSocketAddress: " + proxyAddress.getClass());
      }
      InetSocketAddress proxySocketAddress = (InetSocketAddress) proxyAddress;
      socketHost = proxySocketAddress.getHostName();
      socketPort = proxySocketAddress.getPort();
    }

    // Try each address for best behavior in mixed IPv4/IPv6 environments.
    socketAddresses = dns.getAllByName(socketHost);
    nextSocketAddressIndex = 0;
  }

  /** Returns true if there's another socket address to try. */
  private boolean hasNextInetSocketAddress() {
    return socketAddresses != null;
  }

  /** Returns the next socket address to try. */
  private InetSocketAddress nextInetSocketAddress() throws UnknownHostException {
    InetSocketAddress result =
        new InetSocketAddress(socketAddresses[nextSocketAddressIndex++], socketPort);
    if (nextSocketAddressIndex == socketAddresses.length) {
      socketAddresses = null; // So that hasNextInetSocketAddress() returns false.
      nextSocketAddressIndex = 0;
    }

    return result;
  }

  /** Resets {@link #nextTlsMode} to the first option. */
  private void resetNextTlsMode() {
    nextTlsMode = (address.getSslSocketFactory() != null) ? TLS_MODE_MODERN : TLS_MODE_COMPATIBLE;
  }

  /** Returns true if there's another TLS mode to try. */
  private boolean hasNextTlsMode() {
    return nextTlsMode != TLS_MODE_NULL;
  }

  /** Returns the next TLS mode to try. */
  private int nextTlsMode() {
    if (nextTlsMode == TLS_MODE_MODERN) {
      nextTlsMode = TLS_MODE_COMPATIBLE;
      return TLS_MODE_MODERN;
    } else if (nextTlsMode == TLS_MODE_COMPATIBLE) {
      nextTlsMode = TLS_MODE_NULL;  // So that hasNextTlsMode() returns false.
      return TLS_MODE_COMPATIBLE;
    } else {
      throw new AssertionError();
    }
  }

  /** Returns true if there is another postponed route to try. */
  private boolean hasNextPostponed() {
    return !postponedRoutes.isEmpty();
  }

  /** Returns the next postponed route to try. */
  private Route nextPostponed() {
    return postponedRoutes.remove(0);
  }
}


File: platforms/android/CordovaLib/src/com/squareup/okhttp/internal/http/SpdyTransport.java
/*
 * Copyright (C) 2012 The Android Open Source Project
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

import com.squareup.okhttp.internal.spdy.ErrorCode;
import com.squareup.okhttp.internal.spdy.SpdyConnection;
import com.squareup.okhttp.internal.spdy.SpdyStream;
import java.io.IOException;
import java.io.InputStream;
import java.io.OutputStream;
import java.net.CacheRequest;
import java.net.URL;
import java.util.List;

public final class SpdyTransport implements Transport {
  private final HttpEngine httpEngine;
  private final SpdyConnection spdyConnection;
  private SpdyStream stream;

  public SpdyTransport(HttpEngine httpEngine, SpdyConnection spdyConnection) {
    this.httpEngine = httpEngine;
    this.spdyConnection = spdyConnection;
  }

  @Override public OutputStream createRequestBody() throws IOException {
    long fixedContentLength = httpEngine.policy.getFixedContentLength();
    if (fixedContentLength != -1) {
      httpEngine.requestHeaders.setContentLength(fixedContentLength);
    }
    // TODO: if we aren't streaming up to the server, we should buffer the whole request
    writeRequestHeaders();
    return stream.getOutputStream();
  }

  @Override public void writeRequestHeaders() throws IOException {
    if (stream != null) {
      return;
    }
    httpEngine.writingRequestHeaders();
    RawHeaders requestHeaders = httpEngine.requestHeaders.getHeaders();
    String version = httpEngine.connection.getHttpMinorVersion() == 1 ? "HTTP/1.1" : "HTTP/1.0";
    URL url = httpEngine.policy.getURL();
    requestHeaders.addSpdyRequestHeaders(httpEngine.method, HttpEngine.requestPath(url), version,
        HttpEngine.getOriginAddress(url), httpEngine.uri.getScheme());
    boolean hasRequestBody = httpEngine.hasRequestBody();
    boolean hasResponseBody = true;
    stream = spdyConnection.newStream(requestHeaders.toNameValueBlock(), hasRequestBody,
        hasResponseBody);
    stream.setReadTimeout(httpEngine.client.getReadTimeout());
  }

  @Override public void writeRequestBody(RetryableOutputStream requestBody) throws IOException {
    throw new UnsupportedOperationException();
  }

  @Override public void flushRequest() throws IOException {
    stream.getOutputStream().close();
  }

  @Override public ResponseHeaders readResponseHeaders() throws IOException {
    List<String> nameValueBlock = stream.getResponseHeaders();
    RawHeaders rawHeaders = RawHeaders.fromNameValueBlock(nameValueBlock);
    httpEngine.receiveHeaders(rawHeaders);

    ResponseHeaders headers = new ResponseHeaders(httpEngine.uri, rawHeaders);
    headers.setTransport("spdy/3");
    return headers;
  }

  @Override public InputStream getTransferStream(CacheRequest cacheRequest) throws IOException {
    return new UnknownLengthHttpInputStream(stream.getInputStream(), cacheRequest, httpEngine);
  }

  @Override public boolean makeReusable(boolean streamCanceled, OutputStream requestBodyOut,
      InputStream responseBodyIn) {
    if (streamCanceled) {
      if (stream != null) {
        stream.closeLater(ErrorCode.CANCEL);
        return true;
      } else {
        // If stream is null, it either means that writeRequestHeaders wasn't called
        // or that SpdyConnection#newStream threw an IOException. In both cases there's
        // nothing to do here and this stream can't be reused.
        return false;
      }
    }
    return true;
  }
}


File: platforms/android/CordovaLib/src/com/squareup/okhttp/internal/http/Transport.java
/*
 * Copyright (C) 2012 The Android Open Source Project
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

import java.io.IOException;
import java.io.InputStream;
import java.io.OutputStream;
import java.net.CacheRequest;

interface Transport {
  /**
   * Returns an output stream where the request body can be written. The
   * returned stream will of one of two types:
   * <ul>
   * <li><strong>Direct.</strong> Bytes are written to the socket and
   * forgotten. This is most efficient, particularly for large request
   * bodies. The returned stream may be buffered; the caller must call
   * {@link #flushRequest} before reading the response.</li>
   * <li><strong>Buffered.</strong> Bytes are written to an in memory
   * buffer, and must be explicitly flushed with a call to {@link
   * #writeRequestBody}. This allows HTTP authorization (401, 407)
   * responses to be retransmitted transparently.</li>
   * </ul>
   */
  // TODO: don't bother retransmitting the request body? It's quite a corner
  // case and there's uncertainty whether Firefox or Chrome do this
  OutputStream createRequestBody() throws IOException;

  /** This should update the HTTP engine's sentRequestMillis field. */
  void writeRequestHeaders() throws IOException;

  /**
   * Sends the request body returned by {@link #createRequestBody} to the
   * remote peer.
   */
  void writeRequestBody(RetryableOutputStream requestBody) throws IOException;

  /** Flush the request body to the underlying socket. */
  void flushRequest() throws IOException;

  /** Read response headers and update the cookie manager. */
  ResponseHeaders readResponseHeaders() throws IOException;

  // TODO: make this the content stream?
  InputStream getTransferStream(CacheRequest cacheRequest) throws IOException;

  /** Returns true if the underlying connection can be recycled. */
  boolean makeReusable(boolean streamCanceled, OutputStream requestBodyOut,
      InputStream responseBodyIn);
}


File: platforms/android/CordovaLib/src/com/squareup/okhttp/internal/http/UnknownLengthHttpInputStream.java
/*
 * Copyright (C) 2012 The Android Open Source Project
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

import java.io.IOException;
import java.io.InputStream;
import java.net.CacheRequest;

import static com.squareup.okhttp.internal.Util.checkOffsetAndCount;

/** An HTTP message body terminated by the end of the underlying stream. */
final class UnknownLengthHttpInputStream extends AbstractHttpInputStream {
  private boolean inputExhausted;

  UnknownLengthHttpInputStream(InputStream in, CacheRequest cacheRequest, HttpEngine httpEngine)
      throws IOException {
    super(in, httpEngine, cacheRequest);
  }

  @Override public int read(byte[] buffer, int offset, int count) throws IOException {
    checkOffsetAndCount(buffer.length, offset, count);
    checkNotClosed();
    if (in == null || inputExhausted) {
      return -1;
    }
    int read = in.read(buffer, offset, count);
    if (read == -1) {
      inputExhausted = true;
      endOfInput();
      return -1;
    }
    cacheWrite(buffer, offset, read);
    return read;
  }

  @Override public int available() throws IOException {
    checkNotClosed();
    return in == null ? 0 : in.available();
  }

  @Override public void close() throws IOException {
    if (closed) {
      return;
    }
    closed = true;
    if (!inputExhausted) {
      unexpectedEndOfInput();
    }
  }
}


File: platforms/android/CordovaLib/src/com/squareup/okhttp/internal/spdy/ErrorCode.java
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

package com.squareup.okhttp.internal.spdy;

public enum ErrorCode {
  /** Not an error! For SPDY stream resets, prefer null over NO_ERROR. */
  NO_ERROR(0, -1, 0),

  PROTOCOL_ERROR(1, 1, 1),

  /** A subtype of PROTOCOL_ERROR used by SPDY. */
  INVALID_STREAM(1, 2, -1),

  /** A subtype of PROTOCOL_ERROR used by SPDY. */
  UNSUPPORTED_VERSION(1, 4, -1),

  /** A subtype of PROTOCOL_ERROR used by SPDY. */
  STREAM_IN_USE(1, 8, -1),

  /** A subtype of PROTOCOL_ERROR used by SPDY. */
  STREAM_ALREADY_CLOSED(1, 9, -1),

  INTERNAL_ERROR(2, 6, 2),

  FLOW_CONTROL_ERROR(3, 7, -1),

  STREAM_CLOSED(5, -1, -1),

  FRAME_TOO_LARGE(6, 11, -1),

  REFUSED_STREAM(7, 3, -1),

  CANCEL(8, 5, -1),

  COMPRESSION_ERROR(9, -1, -1),

  INVALID_CREDENTIALS(-1, 10, -1);

  public final int httpCode;
  public final int spdyRstCode;
  public final int spdyGoAwayCode;

  private ErrorCode(int httpCode, int spdyRstCode, int spdyGoAwayCode) {
    this.httpCode = httpCode;
    this.spdyRstCode = spdyRstCode;
    this.spdyGoAwayCode = spdyGoAwayCode;
  }

  public static ErrorCode fromSpdy3Rst(int code) {
    for (ErrorCode errorCode : ErrorCode.values()) {
      if (errorCode.spdyRstCode == code) return errorCode;
    }
    return null;
  }

  public static ErrorCode fromHttp2(int code) {
    for (ErrorCode errorCode : ErrorCode.values()) {
      if (errorCode.httpCode == code) return errorCode;
    }
    return null;
  }

  public static ErrorCode fromSpdyGoAway(int code) {
    for (ErrorCode errorCode : ErrorCode.values()) {
      if (errorCode.spdyGoAwayCode == code) return errorCode;
    }
    return null;
  }
}


File: platforms/android/CordovaLib/src/com/squareup/okhttp/internal/spdy/FrameReader.java
/*
 * Copyright (C) 2011 The Android Open Source Project
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

import java.io.Closeable;
import java.io.IOException;
import java.io.InputStream;
import java.util.List;

/** Reads transport frames for SPDY/3 or HTTP/2.0. */
public interface FrameReader extends Closeable {
  void readConnectionHeader() throws IOException;
  boolean nextFrame(Handler handler) throws IOException;

  public interface Handler {
    void data(boolean inFinished, int streamId, InputStream in, int length) throws IOException;
    /**
     * Create or update incoming headers, creating the corresponding streams
     * if necessary. Frames that trigger this are SPDY SYN_STREAM, HEADERS, and
     * SYN_REPLY, and HTTP/2.0 HEADERS and PUSH_PROMISE.
     *
     * @param inFinished true if the sender will not send further frames.
     * @param outFinished true if the receiver should not send further frames.
     * @param streamId the stream owning these headers.
     * @param associatedStreamId the stream that triggered the sender to create
     *     this stream.
     * @param priority or -1 for no priority. For SPDY, priorities range from 0
     *     (highest) thru 7 (lowest). For HTTP/2.0, priorities range from 0
     *     (highest) thru 2**31-1 (lowest).
     */
    void headers(boolean outFinished, boolean inFinished, int streamId, int associatedStreamId,
        int priority, List<String> nameValueBlock, HeadersMode headersMode);
    void rstStream(int streamId, ErrorCode errorCode);
    void settings(boolean clearPrevious, Settings settings);
    void noop();
    void ping(boolean reply, int payload1, int payload2);
    void goAway(int lastGoodStreamId, ErrorCode errorCode);
    void windowUpdate(int streamId, int deltaWindowSize, boolean endFlowControl);
    void priority(int streamId, int priority);
  }
}


File: platforms/android/CordovaLib/src/com/squareup/okhttp/internal/spdy/FrameWriter.java
/*
 * Copyright (C) 2011 The Android Open Source Project
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

import java.io.Closeable;
import java.io.IOException;
import java.util.List;

/** Writes transport frames for SPDY/3 or HTTP/2.0. */
public interface FrameWriter extends Closeable {
  /** HTTP/2.0 only. */
  void connectionHeader() throws IOException;

  /** SPDY/3 only. */
  void flush() throws IOException;
  void synStream(boolean outFinished, boolean inFinished, int streamId, int associatedStreamId,
      int priority, int slot, List<String> nameValueBlock) throws IOException;
  void synReply(boolean outFinished, int streamId, List<String> nameValueBlock) throws IOException;
  void headers(int streamId, List<String> nameValueBlock) throws IOException;
  void rstStream(int streamId, ErrorCode errorCode) throws IOException;
  void data(boolean outFinished, int streamId, byte[] data) throws IOException;
  void data(boolean outFinished, int streamId, byte[] data, int offset, int byteCount)
      throws IOException;
  void settings(Settings settings) throws IOException;
  void noop() throws IOException;
  void ping(boolean reply, int payload1, int payload2) throws IOException;
  void goAway(int lastGoodStreamId, ErrorCode errorCode) throws IOException;
  void windowUpdate(int streamId, int deltaWindowSize) throws IOException;
}


File: platforms/android/CordovaLib/src/com/squareup/okhttp/internal/spdy/HeadersMode.java
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
package com.squareup.okhttp.internal.spdy;

enum HeadersMode {
  SPDY_SYN_STREAM,
  SPDY_REPLY,
  SPDY_HEADERS,
  HTTP_20_HEADERS;

  /** Returns true if it is an error these headers to create a new stream. */
  public boolean failIfStreamAbsent() {
    return this == SPDY_REPLY || this == SPDY_HEADERS;
  }

  /** Returns true if it is an error these headers to update an existing stream. */
  public boolean failIfStreamPresent() {
    return this == SPDY_SYN_STREAM;
  }

  /**
   * Returns true if it is an error these headers to be the initial headers of a
   * response.
   */
  public boolean failIfHeadersAbsent() {
    return this == SPDY_HEADERS;
  }

  /**
   * Returns true if it is an error these headers to be update existing headers
   * of a response.
   */
  public boolean failIfHeadersPresent() {
    return this == SPDY_REPLY;
  }
}


File: platforms/android/CordovaLib/src/com/squareup/okhttp/internal/spdy/Hpack.java
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

package com.squareup.okhttp.internal.spdy;

import java.io.DataInputStream;
import java.io.IOException;
import java.io.OutputStream;
import java.util.ArrayList;
import java.util.Arrays;
import java.util.BitSet;
import java.util.List;

/**
 * Read and write HPACK v03.
 * http://tools.ietf.org/html/draft-ietf-httpbis-header-compression-03
 */
final class Hpack {

  static class HeaderEntry {
    private final String name;
    private final String value;

    HeaderEntry(String name, String value) {
      this.name = name;
      this.value = value;
    }

    // TODO: This needs to be the length in UTF-8 bytes, not the length in chars.
    int length() {
      return 32 + name.length() + value.length();
    }
  }

  static final int PREFIX_5_BITS = 0x1f;
  static final int PREFIX_6_BITS = 0x3f;
  static final int PREFIX_7_BITS = 0x7f;
  static final int PREFIX_8_BITS = 0xff;

  static final List<HeaderEntry> INITIAL_CLIENT_TO_SERVER_HEADER_TABLE = Arrays.asList(
      new HeaderEntry(":scheme", "http"),
      new HeaderEntry(":scheme", "https"),
      new HeaderEntry(":host", ""),
      new HeaderEntry(":path", "/"),
      new HeaderEntry(":method", "GET"),
      new HeaderEntry("accept", ""),
      new HeaderEntry("accept-charset", ""),
      new HeaderEntry("accept-encoding", ""),
      new HeaderEntry("accept-language", ""),
      new HeaderEntry("cookie", ""),
      new HeaderEntry("if-modified-since", ""),
      new HeaderEntry("user-agent", ""),
      new HeaderEntry("referer", ""),
      new HeaderEntry("authorization", ""),
      new HeaderEntry("allow", ""),
      new HeaderEntry("cache-control", ""),
      new HeaderEntry("connection", ""),
      new HeaderEntry("content-length", ""),
      new HeaderEntry("content-type", ""),
      new HeaderEntry("date", ""),
      new HeaderEntry("expect", ""),
      new HeaderEntry("from", ""),
      new HeaderEntry("if-match", ""),
      new HeaderEntry("if-none-match", ""),
      new HeaderEntry("if-range", ""),
      new HeaderEntry("if-unmodified-since", ""),
      new HeaderEntry("max-forwards", ""),
      new HeaderEntry("proxy-authorization", ""),
      new HeaderEntry("range", ""),
      new HeaderEntry("via", "")
  );

  static final List<HeaderEntry> INITIAL_SERVER_TO_CLIENT_HEADER_TABLE = Arrays.asList(
      new HeaderEntry(":status", "200"),
      new HeaderEntry("age", ""),
      new HeaderEntry("cache-control", ""),
      new HeaderEntry("content-length", ""),
      new HeaderEntry("content-type", ""),
      new HeaderEntry("date", ""),
      new HeaderEntry("etag", ""),
      new HeaderEntry("expires", ""),
      new HeaderEntry("last-modified", ""),
      new HeaderEntry("server", ""),
      new HeaderEntry("set-cookie", ""),
      new HeaderEntry("vary", ""),
      new HeaderEntry("via", ""),
      new HeaderEntry("access-control-allow-origin", ""),
      new HeaderEntry("accept-ranges", ""),
      new HeaderEntry("allow", ""),
      new HeaderEntry("connection", ""),
      new HeaderEntry("content-disposition", ""),
      new HeaderEntry("content-encoding", ""),
      new HeaderEntry("content-language", ""),
      new HeaderEntry("content-location", ""),
      new HeaderEntry("content-range", ""),
      new HeaderEntry("link", ""),
      new HeaderEntry("location", ""),
      new HeaderEntry("proxy-authenticate", ""),
      new HeaderEntry("refresh", ""),
      new HeaderEntry("retry-after", ""),
      new HeaderEntry("strict-transport-security", ""),
      new HeaderEntry("transfer-encoding", ""),
      new HeaderEntry("www-authenticate", "")
  );

  // Update these when initial tables change to sum of each entry length.
  static final int INITIAL_CLIENT_TO_SERVER_HEADER_TABLE_LENGTH = 1262;
  static final int INITIAL_SERVER_TO_CLIENT_HEADER_TABLE_LENGTH = 1304;

  private Hpack() {
  }

  static class Reader {
    private final long maxBufferSize = 4096; // TODO: needs to come from settings.
    private final DataInputStream in;

    private final BitSet referenceSet = new BitSet();
    private final List<HeaderEntry> headerTable;
    private final List<String> emittedHeaders = new ArrayList<String>();
    private long bufferSize = 0;
    private long bytesLeft = 0;

    Reader(DataInputStream in, boolean client) {
      this.in = in;
      if (client) {  // we are reading from the server
        this.headerTable = new ArrayList<HeaderEntry>(INITIAL_SERVER_TO_CLIENT_HEADER_TABLE);
        this.bufferSize = INITIAL_SERVER_TO_CLIENT_HEADER_TABLE_LENGTH;
      } else {
        this.headerTable = new ArrayList<HeaderEntry>(INITIAL_CLIENT_TO_SERVER_HEADER_TABLE);
        this.bufferSize = INITIAL_CLIENT_TO_SERVER_HEADER_TABLE_LENGTH;
      }
    }

    /**
     * Read {@code byteCount} bytes of headers from the source stream into the
     * set of emitted headers.
     */
    public void readHeaders(int byteCount) throws IOException {
      bytesLeft += byteCount;
      // TODO: limit to 'byteCount' bytes?

      while (bytesLeft > 0) {
        int b = readByte();

        if ((b & 0x80) != 0) {
          int index = readInt(b, PREFIX_7_BITS);
          readIndexedHeader(index);
        } else if (b == 0x60) {
          readLiteralHeaderWithoutIndexingNewName();
        } else if ((b & 0xe0) == 0x60) {
          int index = readInt(b, PREFIX_5_BITS);
          readLiteralHeaderWithoutIndexingIndexedName(index - 1);
        } else if (b == 0x40) {
          readLiteralHeaderWithIncrementalIndexingNewName();
        } else if ((b & 0xe0) == 0x40) {
          int index = readInt(b, PREFIX_5_BITS);
          readLiteralHeaderWithIncrementalIndexingIndexedName(index - 1);
        } else if (b == 0) {
          readLiteralHeaderWithSubstitutionIndexingNewName();
        } else if ((b & 0xc0) == 0) {
          int index = readInt(b, PREFIX_6_BITS);
          readLiteralHeaderWithSubstitutionIndexingIndexedName(index - 1);
        } else {
          throw new AssertionError();
        }
      }
    }

    public void emitReferenceSet() {
      for (int i = referenceSet.nextSetBit(0); i != -1; i = referenceSet.nextSetBit(i + 1)) {
        emittedHeaders.add(getName(i));
        emittedHeaders.add(getValue(i));
      }
    }

    /**
     * Returns all headers emitted since they were last cleared, then clears the
     * emitted headers.
     */
    public List<String> getAndReset() {
      List<String> result = new ArrayList<String>(emittedHeaders);
      emittedHeaders.clear();
      return result;
    }

    private void readIndexedHeader(int index) {
      if (referenceSet.get(index)) {
        referenceSet.clear(index);
      } else {
        referenceSet.set(index);
      }
    }

    private void readLiteralHeaderWithoutIndexingIndexedName(int index)
        throws IOException {
      String name = getName(index);
      String value = readString();
      emittedHeaders.add(name);
      emittedHeaders.add(value);
    }

    private void readLiteralHeaderWithoutIndexingNewName()
        throws IOException {
      String name = readString();
      String value = readString();
      emittedHeaders.add(name);
      emittedHeaders.add(value);
    }

    private void readLiteralHeaderWithIncrementalIndexingIndexedName(int nameIndex)
        throws IOException {
      String name = getName(nameIndex);
      String value = readString();
      int index = headerTable.size(); // append to tail
      insertIntoHeaderTable(index, new HeaderEntry(name, value));
    }

    private void readLiteralHeaderWithIncrementalIndexingNewName() throws IOException {
      String name = readString();
      String value = readString();
      int index = headerTable.size(); // append to tail
      insertIntoHeaderTable(index, new HeaderEntry(name, value));
    }

    private void readLiteralHeaderWithSubstitutionIndexingIndexedName(int nameIndex)
        throws IOException {
      int index = readInt(readByte(), PREFIX_8_BITS);
      String name = getName(nameIndex);
      String value = readString();
      insertIntoHeaderTable(index, new HeaderEntry(name, value));
    }

    private void readLiteralHeaderWithSubstitutionIndexingNewName() throws IOException {
      String name = readString();
      int index = readInt(readByte(), PREFIX_8_BITS);
      String value = readString();
      insertIntoHeaderTable(index, new HeaderEntry(name, value));
    }

    private String getName(int index) {
      return headerTable.get(index).name;
    }

    private String getValue(int index) {
      return headerTable.get(index).value;
    }

    private void insertIntoHeaderTable(int index, HeaderEntry entry) {
      int delta = entry.length();
      if (index != headerTable.size()) {
        delta -= headerTable.get(index).length();
      }

      // if the new or replacement header is too big, drop all entries.
      if (delta > maxBufferSize) {
        headerTable.clear();
        bufferSize = 0;
        // emit the large header to the callback.
        emittedHeaders.add(entry.name);
        emittedHeaders.add(entry.value);
        return;
      }

      // Prune headers to the required length.
      while (bufferSize + delta > maxBufferSize) {
        remove(0);
        index--;
      }

      if (index < 0) { // we pruned it, so insert at beginning
        index = 0;
        headerTable.add(index, entry);
      } else if (index == headerTable.size()) { // append to the end
        headerTable.add(index, entry);
      } else { // replace value at same position
        headerTable.set(index, entry);
      }

      bufferSize += delta;
      referenceSet.set(index);
    }

    private void remove(int index) {
      bufferSize -= headerTable.remove(index).length();
    }

    private int readByte() throws IOException {
      bytesLeft--;
      return in.readByte() & 0xff;
    }

    int readInt(int firstByte, int prefixMask) throws IOException {
      int prefix = firstByte & prefixMask;
      if (prefix < prefixMask) {
        return prefix; // This was a single byte value.
      }

      // This is a multibyte value. Read 7 bits at a time.
      int result = prefixMask;
      int shift = 0;
      while (true) {
        int b = readByte();
        if ((b & 0x80) != 0) { // Equivalent to (b >= 128) since b is in [0..255].
          result += (b & 0x7f) << shift;
          shift += 7;
        } else {
          result += b << shift; // Last byte.
          break;
        }
      }
      return result;
    }

    /**
     * Reads a UTF-8 encoded string. Since ASCII is a subset of UTF-8, this method
     * may be used to read strings that are known to be ASCII-only.
     */
    public String readString() throws IOException {
      int firstByte = readByte();
      int length = readInt(firstByte, PREFIX_8_BITS);
      byte[] encoded = new byte[length];
      bytesLeft -= length;
      in.readFully(encoded);
      return new String(encoded, "UTF-8");
    }
  }

  static class Writer {
    private final OutputStream out;

    Writer(OutputStream out) {
      this.out = out;
    }

    public void writeHeaders(List<String> nameValueBlock) throws IOException {
      // TODO: implement a compression strategy.
      for (int i = 0, size = nameValueBlock.size(); i < size; i += 2) {
        out.write(0x60); // Literal Header without Indexing - New Name.
        writeString(nameValueBlock.get(i));
        writeString(nameValueBlock.get(i + 1));
      }
    }

    public void writeInt(int value, int prefixMask, int bits) throws IOException {
      // Write the raw value for a single byte value.
      if (value < prefixMask) {
        out.write(bits | value);
        return;
      }

      // Write the mask to start a multibyte value.
      out.write(bits | prefixMask);
      value -= prefixMask;

      // Write 7 bits at a time 'til we're done.
      while (value >= 0x80) {
        int b = value & 0x7f;
        out.write(b | 0x80);
        value >>>= 7;
      }
      out.write(value);
    }

    /**
     * Writes a UTF-8 encoded string. Since ASCII is a subset of UTF-8, this
     * method can be used to write strings that are known to be ASCII-only.
     */
    public void writeString(String headerName) throws IOException {
      byte[] bytes = headerName.getBytes("UTF-8");
      writeInt(bytes.length, PREFIX_8_BITS, 0);
      out.write(bytes);
    }
  }
}


File: platforms/android/CordovaLib/src/com/squareup/okhttp/internal/spdy/Http20Draft06.java
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
package com.squareup.okhttp.internal.spdy;

import com.squareup.okhttp.internal.Util;
import java.io.ByteArrayOutputStream;
import java.io.DataInputStream;
import java.io.DataOutputStream;
import java.io.IOException;
import java.io.InputStream;
import java.io.OutputStream;
import java.io.UnsupportedEncodingException;
import java.util.Arrays;
import java.util.List;

/**
 * Read and write http/2 v06 frames.
 * http://tools.ietf.org/html/draft-ietf-httpbis-http2-06
 */
final class Http20Draft06 implements Variant {
  private static final byte[] CONNECTION_HEADER;
  static {
    try {
      CONNECTION_HEADER = "PRI * HTTP/2.0\r\n\r\nSM\r\n\r\n".getBytes("UTF-8");
    } catch (UnsupportedEncodingException e) {
      throw new AssertionError();
    }
  }

  static final int TYPE_DATA = 0x0;
  static final int TYPE_HEADERS = 0x1;
  static final int TYPE_PRIORITY = 0x2;
  static final int TYPE_RST_STREAM = 0x3;
  static final int TYPE_SETTINGS = 0x4;
  static final int TYPE_PUSH_PROMISE = 0x5;
  static final int TYPE_PING = 0x6;
  static final int TYPE_GOAWAY = 0x7;
  static final int TYPE_WINDOW_UPDATE = 0x9;
  static final int TYPE_CONTINUATION = 0xa;

  static final int FLAG_END_STREAM = 0x1;
  /** Used for headers, push-promise and continuation. */
  static final int FLAG_END_HEADERS = 0x4;
  static final int FLAG_PRIORITY = 0x8;
  static final int FLAG_PONG = 0x1;
  static final int FLAG_END_FLOW_CONTROL = 0x1;

  @Override public FrameReader newReader(InputStream in, boolean client) {
    return new Reader(in, client);
  }

  @Override public FrameWriter newWriter(OutputStream out, boolean client) {
    return new Writer(out, client);
  }

  static final class Reader implements FrameReader {
    private final DataInputStream in;
    private final boolean client;
    private final Hpack.Reader hpackReader;

    Reader(InputStream in, boolean client) {
      this.in = new DataInputStream(in);
      this.client = client;
      this.hpackReader = new Hpack.Reader(this.in, client);
    }

    @Override public void readConnectionHeader() throws IOException {
      if (client) return; // Nothing to read; servers don't send connection headers!
      byte[] connectionHeader = new byte[CONNECTION_HEADER.length];
      in.readFully(connectionHeader);
      if (!Arrays.equals(connectionHeader, CONNECTION_HEADER)) {
        throw ioException("Expected a connection header but was "
            + Arrays.toString(connectionHeader));
      }
    }

    @Override public boolean nextFrame(Handler handler) throws IOException {
      int w1;
      try {
        w1 = in.readInt();
      } catch (IOException e) {
        return false; // This might be a normal socket close.
      }
      int w2 = in.readInt();

      int length = (w1 & 0xffff0000) >> 16;
      int type = (w1 & 0xff00) >> 8;
      int flags = w1 & 0xff;
      // boolean r = (w2 & 0x80000000) != 0; // Reserved.
      int streamId = (w2 & 0x7fffffff);

      switch (type) {
        case TYPE_DATA:
          readData(handler, flags, length, streamId);
          return true;

        case TYPE_HEADERS:
          readHeaders(handler, flags, length, streamId);
          return true;

        case TYPE_PRIORITY:
          readPriority(handler, flags, length, streamId);
          return true;

        case TYPE_RST_STREAM:
          readRstStream(handler, flags, length, streamId);
          return true;

        case TYPE_SETTINGS:
          readSettings(handler, flags, length, streamId);
          return true;

        case TYPE_PUSH_PROMISE:
          readPushPromise(handler, flags, length, streamId);
          return true;

        case TYPE_PING:
          readPing(handler, flags, length, streamId);
          return true;

        case TYPE_GOAWAY:
          readGoAway(handler, flags, length, streamId);
          return true;

        case TYPE_WINDOW_UPDATE:
          readWindowUpdate(handler, flags, length, streamId);
          return true;
      }

      throw new UnsupportedOperationException("TODO");
    }

    private void readHeaders(Handler handler, int flags, int length, int streamId)
        throws IOException {
      if (streamId == 0) throw ioException("TYPE_HEADERS streamId == 0");

      boolean inFinished = (flags & FLAG_END_STREAM) != 0;

      while (true) {
        hpackReader.readHeaders(length);

        if ((flags & FLAG_END_HEADERS) != 0) {
          hpackReader.emitReferenceSet();
          List<String> namesAndValues = hpackReader.getAndReset();
          int priority = -1; // TODO: priority
          handler.headers(false, inFinished, streamId, -1, priority, namesAndValues,
              HeadersMode.HTTP_20_HEADERS);
          return;
        }

        // Read another continuation frame.
        int w1 = in.readInt();
        int w2 = in.readInt();

        length = (w1 & 0xffff0000) >> 16;
        int newType = (w1 & 0xff00) >> 8;
        flags = w1 & 0xff;

        // TODO: remove in draft 8: CONTINUATION no longer sets END_STREAM
        inFinished = (flags & FLAG_END_STREAM) != 0;

        // boolean u = (w2 & 0x80000000) != 0; // Unused.
        int newStreamId = (w2 & 0x7fffffff);

        if (newType != TYPE_CONTINUATION) {
          throw ioException("TYPE_CONTINUATION didn't have FLAG_END_HEADERS");
        }
        if (newStreamId != streamId) throw ioException("TYPE_CONTINUATION streamId changed");
      }
    }

    private void readData(Handler handler, int flags, int length, int streamId) throws IOException {
      boolean inFinished = (flags & FLAG_END_STREAM) != 0;
      handler.data(inFinished, streamId, in, length);
    }

    private void readPriority(Handler handler, int flags, int length, int streamId)
        throws IOException {
      if (length != 4) throw ioException("TYPE_PRIORITY length: %d != 4", length);
      if (streamId == 0) throw ioException("TYPE_PRIORITY streamId == 0");
      int w1 = in.readInt();
      // boolean r = (w1 & 0x80000000) != 0; // Reserved.
      int priority = (w1 & 0x7fffffff);
      handler.priority(streamId, priority);
    }

    private void readRstStream(Handler handler, int flags, int length, int streamId)
        throws IOException {
      if (length != 4) throw ioException("TYPE_RST_STREAM length: %d != 4", length);
      if (streamId == 0) throw ioException("TYPE_RST_STREAM streamId == 0");
      int errorCodeInt = in.readInt();
      ErrorCode errorCode = ErrorCode.fromHttp2(errorCodeInt);
      if (errorCode == null) {
        throw ioException("TYPE_RST_STREAM unexpected error code: %d", errorCodeInt);
      }
      handler.rstStream(streamId, errorCode);
    }

    private void readSettings(Handler handler, int flags, int length, int streamId)
        throws IOException {
      if (length % 8 != 0) throw ioException("TYPE_SETTINGS length %% 8 != 0: %s", length);
      if (streamId != 0) throw ioException("TYPE_SETTINGS streamId != 0");
      Settings settings = new Settings();
      for (int i = 0; i < length; i += 8) {
        int w1 = in.readInt();
        int value = in.readInt();
        // int r = (w1 & 0xff000000) >>> 24; // Reserved.
        int id = w1 & 0xffffff;
        settings.set(id, 0, value);
      }
      handler.settings(false, settings);
    }

    private void readPushPromise(Handler handler, int flags, int length, int streamId) {
      // TODO:
    }

    private void readPing(Handler handler, int flags, int length, int streamId) throws IOException {
      if (length != 8) throw ioException("TYPE_PING length != 8: %s", length);
      if (streamId != 0) throw ioException("TYPE_PING streamId != 0");
      int payload1 = in.readInt();
      int payload2 = in.readInt();
      boolean reply = (flags & FLAG_PONG) != 0;
      handler.ping(reply, payload1, payload2);
    }

    private void readGoAway(Handler handler, int flags, int length, int streamId)
        throws IOException {
      if (length < 8) throw ioException("TYPE_GOAWAY length < 8: %s", length);
      int lastStreamId = in.readInt();
      int errorCodeInt = in.readInt();
      int opaqueDataLength = length - 8;
      ErrorCode errorCode = ErrorCode.fromHttp2(errorCodeInt);
      if (errorCode == null) {
        throw ioException("TYPE_RST_STREAM unexpected error code: %d", errorCodeInt);
      }
      if (Util.skipByReading(in, opaqueDataLength) != opaqueDataLength) {
        throw new IOException("TYPE_GOAWAY opaque data was truncated");
      }
      handler.goAway(lastStreamId, errorCode);
    }

    private void readWindowUpdate(Handler handler, int flags, int length, int streamId)
        throws IOException {
      int w1 = in.readInt();
      // boolean r = (w1 & 0x80000000) != 0; // Reserved.
      int windowSizeIncrement = (w1 & 0x7fffffff);
      boolean endFlowControl = (flags & FLAG_END_FLOW_CONTROL) != 0;
      handler.windowUpdate(streamId, windowSizeIncrement, endFlowControl);
    }

    private static IOException ioException(String message, Object... args) throws IOException {
      throw new IOException(String.format(message, args));
    }

    @Override public void close() throws IOException {
      in.close();
    }
  }

  static final class Writer implements FrameWriter {
    private final DataOutputStream out;
    private final boolean client;
    private final ByteArrayOutputStream hpackBuffer;
    private final Hpack.Writer hpackWriter;

    Writer(OutputStream out, boolean client) {
      this.out = new DataOutputStream(out);
      this.client = client;
      this.hpackBuffer = new ByteArrayOutputStream();
      this.hpackWriter = new Hpack.Writer(hpackBuffer);
    }

    @Override public synchronized void flush() throws IOException {
      out.flush();
    }

    @Override public synchronized void connectionHeader() throws IOException {
      if (!client) return; // Nothing to write; servers don't send connection headers!
      out.write(CONNECTION_HEADER);
    }

    @Override public synchronized void synStream(boolean outFinished, boolean inFinished,
        int streamId, int associatedStreamId, int priority, int slot, List<String> nameValueBlock)
        throws IOException {
      if (inFinished) throw new UnsupportedOperationException();
      headers(outFinished, streamId, priority, nameValueBlock);
    }

    @Override public synchronized void synReply(boolean outFinished, int streamId,
        List<String> nameValueBlock) throws IOException {
      headers(outFinished, streamId, -1, nameValueBlock);
    }

    @Override public synchronized void headers(int streamId, List<String> nameValueBlock)
        throws IOException {
      headers(false, streamId, -1, nameValueBlock);
    }

    private void headers(boolean outFinished, int streamId, int priority,
        List<String> nameValueBlock) throws IOException {
      hpackBuffer.reset();
      hpackWriter.writeHeaders(nameValueBlock);
      int type = TYPE_HEADERS;
      // TODO: implement CONTINUATION
      int length = hpackBuffer.size();
      int flags = FLAG_END_HEADERS;
      if (outFinished) flags |= FLAG_END_STREAM;
      if (priority != -1) flags |= FLAG_PRIORITY;
      out.writeInt((length & 0xffff) << 16 | (type & 0xff) << 8 | (flags & 0xff));
      out.writeInt(streamId & 0x7fffffff);
      if (priority != -1) out.writeInt(priority & 0x7fffffff);
      hpackBuffer.writeTo(out);
    }

    @Override public synchronized void rstStream(int streamId, ErrorCode errorCode)
        throws IOException {
      throw new UnsupportedOperationException("TODO");
    }

    @Override public void data(boolean outFinished, int streamId, byte[] data) throws IOException {
      data(outFinished, streamId, data, 0, data.length);
    }

    @Override public synchronized void data(boolean outFinished, int streamId, byte[] data,
        int offset, int byteCount) throws IOException {
      int type = TYPE_DATA;
      int flags = 0;
      if (outFinished) flags |= FLAG_END_STREAM;
      out.writeInt((byteCount & 0xffff) << 16 | (type & 0xff) << 8 | (flags & 0xff));
      out.writeInt(streamId & 0x7fffffff);
      out.write(data, offset, byteCount);
    }

    @Override public synchronized void settings(Settings settings) throws IOException {
      int type = TYPE_SETTINGS;
      int length = settings.size() * 8;
      int flags = 0;
      int streamId = 0;
      out.writeInt((length & 0xffff) << 16 | (type & 0xff) << 8 | (flags & 0xff));
      out.writeInt(streamId & 0x7fffffff);
      for (int i = 0; i < Settings.COUNT; i++) {
        if (!settings.isSet(i)) continue;
        out.writeInt(i & 0xffffff);
        out.writeInt(settings.get(i));
      }
    }

    @Override public synchronized void noop() throws IOException {
      throw new UnsupportedOperationException();
    }

    @Override public synchronized void ping(boolean reply, int payload1, int payload2)
        throws IOException {
      // TODO
    }

    @Override public synchronized void goAway(int lastGoodStreamId, ErrorCode errorCode)
        throws IOException {
      // TODO
    }

    @Override public synchronized void windowUpdate(int streamId, int deltaWindowSize)
        throws IOException {
      // TODO
    }

    @Override public void close() throws IOException {
      out.close();
    }
  }
}


File: platforms/android/CordovaLib/src/com/squareup/okhttp/internal/spdy/IncomingStreamHandler.java
/*
 * Copyright (C) 2011 The Android Open Source Project
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

import java.io.IOException;

/** Listener to be notified when a connected peer creates a new stream. */
public interface IncomingStreamHandler {
  IncomingStreamHandler REFUSE_INCOMING_STREAMS = new IncomingStreamHandler() {
    @Override public void receive(SpdyStream stream) throws IOException {
      stream.close(ErrorCode.REFUSED_STREAM);
    }
  };

  /**
   * Handle a new stream from this connection's peer. Implementations should
   * respond by either {@link SpdyStream#reply replying to the stream} or
   * {@link SpdyStream#close closing it}. This response does not need to be
   * synchronous.
   */
  void receive(SpdyStream stream) throws IOException;
}


File: platforms/android/CordovaLib/src/com/squareup/okhttp/internal/spdy/NameValueBlockReader.java
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

package com.squareup.okhttp.internal.spdy;

import com.squareup.okhttp.internal.Util;
import java.io.Closeable;
import java.io.DataInputStream;
import java.io.IOException;
import java.io.InputStream;
import java.util.ArrayList;
import java.util.List;
import java.util.zip.DataFormatException;
import java.util.zip.Inflater;
import java.util.zip.InflaterInputStream;

/**
 * Reads a SPDY/3 Name/Value header block. This class is made complicated by the
 * requirement that we're strict with which bytes we put in the compressed bytes
 * buffer. We need to put all compressed bytes into that buffer -- but no other
 * bytes.
 */
class NameValueBlockReader implements Closeable {
  private final DataInputStream nameValueBlockIn;
  private final FillableInflaterInputStream fillableInflaterInputStream;
  private int compressedLimit;

  NameValueBlockReader(final InputStream in) {
    // Limit the inflater input stream to only those bytes in the Name/Value block. We cut the
    // inflater off at its source because we can't predict the ratio of compressed bytes to
    // uncompressed bytes.
    InputStream throttleStream = new InputStream() {
      @Override public int read() throws IOException {
        return Util.readSingleByte(this);
      }

      @Override public int read(byte[] buffer, int offset, int byteCount) throws IOException {
        byteCount = Math.min(byteCount, compressedLimit);
        int consumed = in.read(buffer, offset, byteCount);
        compressedLimit -= consumed;
        return consumed;
      }

      @Override public void close() throws IOException {
        in.close();
      }
    };

    // Subclass inflater to install a dictionary when it's needed.
    Inflater inflater = new Inflater() {
      @Override public int inflate(byte[] buffer, int offset, int count)
          throws DataFormatException {
        int result = super.inflate(buffer, offset, count);
        if (result == 0 && needsDictionary()) {
          setDictionary(Spdy3.DICTIONARY);
          result = super.inflate(buffer, offset, count);
        }
        return result;
      }
    };

    fillableInflaterInputStream = new FillableInflaterInputStream(throttleStream, inflater);
    nameValueBlockIn = new DataInputStream(fillableInflaterInputStream);
  }

  /** Extend the inflater stream so we can eagerly fill the compressed bytes buffer if necessary. */
  static class FillableInflaterInputStream extends InflaterInputStream {
    public FillableInflaterInputStream(InputStream in, Inflater inf) {
      super(in, inf);
    }

    @Override public void fill() throws IOException {
      super.fill(); // This method is protected in the superclass.
    }
  }

  public List<String> readNameValueBlock(int length) throws IOException {
    this.compressedLimit += length;
    try {
      int numberOfPairs = nameValueBlockIn.readInt();
      if (numberOfPairs < 0) {
        throw new IOException("numberOfPairs < 0: " + numberOfPairs);
      }
      if (numberOfPairs > 1024) {
        throw new IOException("numberOfPairs > 1024: " + numberOfPairs);
      }
      List<String> entries = new ArrayList<String>(numberOfPairs * 2);
      for (int i = 0; i < numberOfPairs; i++) {
        String name = readString();
        String values = readString();
        if (name.length() == 0) throw new IOException("name.length == 0");
        entries.add(name);
        entries.add(values);
      }

      doneReading();

      return entries;
    } catch (DataFormatException e) {
      throw new IOException(e.getMessage());
    }
  }

  private void doneReading() throws IOException {
    if (compressedLimit == 0) return;

    // Read any outstanding unread bytes. One side-effect of deflate compression is that sometimes
    // there are bytes remaining in the stream after we've consumed all of the content.
    fillableInflaterInputStream.fill();

    if (compressedLimit != 0) {
      throw new IOException("compressedLimit > 0: " + compressedLimit);
    }
  }

  private String readString() throws DataFormatException, IOException {
    int length = nameValueBlockIn.readInt();
    byte[] bytes = new byte[length];
    Util.readFully(nameValueBlockIn, bytes);
    return new String(bytes, 0, length, "UTF-8");
  }

  @Override public void close() throws IOException {
    nameValueBlockIn.close();
  }
}


File: platforms/android/CordovaLib/src/com/squareup/okhttp/internal/spdy/Ping.java
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
package com.squareup.okhttp.internal.spdy;

import java.util.concurrent.CountDownLatch;
import java.util.concurrent.TimeUnit;

/**
 * A locally-originated ping.
 */
public final class Ping {
  private final CountDownLatch latch = new CountDownLatch(1);
  private long sent = -1;
  private long received = -1;

  Ping() {
  }

  void send() {
    if (sent != -1) throw new IllegalStateException();
    sent = System.nanoTime();
  }

  void receive() {
    if (received != -1 || sent == -1) throw new IllegalStateException();
    received = System.nanoTime();
    latch.countDown();
  }

  void cancel() {
    if (received != -1 || sent == -1) throw new IllegalStateException();
    received = sent - 1;
    latch.countDown();
  }

  /**
   * Returns the round trip time for this ping in nanoseconds, waiting for the
   * response to arrive if necessary. Returns -1 if the response was
   * cancelled.
   */
  public long roundTripTime() throws InterruptedException {
    latch.await();
    return received - sent;
  }

  /**
   * Returns the round trip time for this ping in nanoseconds, or -1 if the
   * response was cancelled, or -2 if the timeout elapsed before the round
   * trip completed.
   */
  public long roundTripTime(long timeout, TimeUnit unit) throws InterruptedException {
    if (latch.await(timeout, unit)) {
      return received - sent;
    } else {
      return -2;
    }
  }
}


File: platforms/android/CordovaLib/src/com/squareup/okhttp/internal/spdy/Settings.java
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
package com.squareup.okhttp.internal.spdy;

final class Settings {
  /**
   * From the spdy/3 spec, the default initial window size for all streams is
   * 64 KiB. (Chrome 25 uses 10 MiB).
   */
  static final int DEFAULT_INITIAL_WINDOW_SIZE = 64 * 1024;

  /** Peer request to clear durable settings. */
  static final int FLAG_CLEAR_PREVIOUSLY_PERSISTED_SETTINGS = 0x1;

  /** Sent by servers only. The peer requests this setting persisted for future connections. */
  static final int PERSIST_VALUE = 0x1;
  /** Sent by clients only. The client is reminding the server of a persisted value. */
  static final int PERSISTED = 0x2;

  /** Sender's estimate of max incoming kbps. */
  static final int UPLOAD_BANDWIDTH = 1;
  /** Sender's estimate of max outgoing kbps. */
  static final int DOWNLOAD_BANDWIDTH = 2;
  /** Sender's estimate of milliseconds between sending a request and receiving a response. */
  static final int ROUND_TRIP_TIME = 3;
  /** Sender's maximum number of concurrent streams. */
  static final int MAX_CONCURRENT_STREAMS = 4;
  /** Current CWND in Packets. */
  static final int CURRENT_CWND = 5;
  /** Retransmission rate. Percentage */
  static final int DOWNLOAD_RETRANS_RATE = 6;
  /** Window size in bytes. */
  static final int INITIAL_WINDOW_SIZE = 7;
  /** Window size in bytes. */
  static final int CLIENT_CERTIFICATE_VECTOR_SIZE = 8;
  /** Flow control options. */
  static final int FLOW_CONTROL_OPTIONS = 9;

  /** Total number of settings. */
  static final int COUNT = 10;

  /** If set, flow control is disabled for streams directed to the sender of these settings. */
  static final int FLOW_CONTROL_OPTIONS_DISABLED = 0x1;

  /** Bitfield of which flags that values. */
  private int set;

  /** Bitfield of flags that have {@link #PERSIST_VALUE}. */
  private int persistValue;

  /** Bitfield of flags that have {@link #PERSISTED}. */
  private int persisted;

  /** Flag values. */
  private final int[] values = new int[COUNT];

  void set(int id, int idFlags, int value) {
    if (id >= values.length) {
      return; // Discard unknown settings.
    }

    int bit = 1 << id;
    set |= bit;
    if ((idFlags & PERSIST_VALUE) != 0) {
      persistValue |= bit;
    } else {
      persistValue &= ~bit;
    }
    if ((idFlags & PERSISTED) != 0) {
      persisted |= bit;
    } else {
      persisted &= ~bit;
    }

    values[id] = value;
  }

  /** Returns true if a value has been assigned for the setting {@code id}. */
  boolean isSet(int id) {
    int bit = 1 << id;
    return (set & bit) != 0;
  }

  /** Returns the value for the setting {@code id}, or 0 if unset. */
  int get(int id) {
    return values[id];
  }

  /** Returns the flags for the setting {@code id}, or 0 if unset. */
  int flags(int id) {
    int result = 0;
    if (isPersisted(id)) result |= Settings.PERSISTED;
    if (persistValue(id)) result |= Settings.PERSIST_VALUE;
    return result;
  }

  /** Returns the number of settings that have values assigned. */
  int size() {
    return Integer.bitCount(set);
  }

  int getUploadBandwidth(int defaultValue) {
    int bit = 1 << UPLOAD_BANDWIDTH;
    return (bit & set) != 0 ? values[UPLOAD_BANDWIDTH] : defaultValue;
  }

  int getDownloadBandwidth(int defaultValue) {
    int bit = 1 << DOWNLOAD_BANDWIDTH;
    return (bit & set) != 0 ? values[DOWNLOAD_BANDWIDTH] : defaultValue;
  }

  int getRoundTripTime(int defaultValue) {
    int bit = 1 << ROUND_TRIP_TIME;
    return (bit & set) != 0 ? values[ROUND_TRIP_TIME] : defaultValue;
  }

  int getMaxConcurrentStreams(int defaultValue) {
    int bit = 1 << MAX_CONCURRENT_STREAMS;
    return (bit & set) != 0 ? values[MAX_CONCURRENT_STREAMS] : defaultValue;
  }

  int getCurrentCwnd(int defaultValue) {
    int bit = 1 << CURRENT_CWND;
    return (bit & set) != 0 ? values[CURRENT_CWND] : defaultValue;
  }

  int getDownloadRetransRate(int defaultValue) {
    int bit = 1 << DOWNLOAD_RETRANS_RATE;
    return (bit & set) != 0 ? values[DOWNLOAD_RETRANS_RATE] : defaultValue;
  }

  int getInitialWindowSize(int defaultValue) {
    int bit = 1 << INITIAL_WINDOW_SIZE;
    return (bit & set) != 0 ? values[INITIAL_WINDOW_SIZE] : defaultValue;
  }

  int getClientCertificateVectorSize(int defaultValue) {
    int bit = 1 << CLIENT_CERTIFICATE_VECTOR_SIZE;
    return (bit & set) != 0 ? values[CLIENT_CERTIFICATE_VECTOR_SIZE] : defaultValue;
  }

  // TODO: honor this setting.
  boolean isFlowControlDisabled() {
    int bit = 1 << FLOW_CONTROL_OPTIONS;
    int value = (bit & set) != 0 ? values[FLOW_CONTROL_OPTIONS] : 0;
    return (value & FLOW_CONTROL_OPTIONS_DISABLED) != 0;
  }

  /**
   * Returns true if this user agent should use this setting in future SPDY
   * connections to the same host.
   */
  boolean persistValue(int id) {
    int bit = 1 << id;
    return (persistValue & bit) != 0;
  }

  /** Returns true if this setting was persisted. */
  boolean isPersisted(int id) {
    int bit = 1 << id;
    return (persisted & bit) != 0;
  }

  /**
   * Writes {@code other} into this. If any setting is populated by this and
   * {@code other}, the value and flags from {@code other} will be kept.
   */
  void merge(Settings other) {
    for (int i = 0; i < COUNT; i++) {
      if (!other.isSet(i)) continue;
      set(i, other.flags(i), other.get(i));
    }
  }
}


File: platforms/android/CordovaLib/src/com/squareup/okhttp/internal/spdy/Spdy3.java
/*
 * Copyright (C) 2011 The Android Open Source Project
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

import com.squareup.okhttp.internal.Platform;
import com.squareup.okhttp.internal.Util;
import java.io.ByteArrayOutputStream;
import java.io.DataInputStream;
import java.io.DataOutputStream;
import java.io.IOException;
import java.io.InputStream;
import java.io.OutputStream;
import java.io.UnsupportedEncodingException;
import java.net.ProtocolException;
import java.util.List;
import java.util.zip.Deflater;

final class Spdy3 implements Variant {
  static final int TYPE_DATA = 0x0;
  static final int TYPE_SYN_STREAM = 0x1;
  static final int TYPE_SYN_REPLY = 0x2;
  static final int TYPE_RST_STREAM = 0x3;
  static final int TYPE_SETTINGS = 0x4;
  static final int TYPE_NOOP = 0x5;
  static final int TYPE_PING = 0x6;
  static final int TYPE_GOAWAY = 0x7;
  static final int TYPE_HEADERS = 0x8;
  static final int TYPE_WINDOW_UPDATE = 0x9;
  static final int TYPE_CREDENTIAL = 0x10;

  static final int FLAG_FIN = 0x1;
  static final int FLAG_UNIDIRECTIONAL = 0x2;

  static final int VERSION = 3;

  static final byte[] DICTIONARY;
  static {
    try {
      DICTIONARY = ("\u0000\u0000\u0000\u0007options\u0000\u0000\u0000\u0004hea"
          + "d\u0000\u0000\u0000\u0004post\u0000\u0000\u0000\u0003put\u0000\u0000\u0000\u0006dele"
          + "te\u0000\u0000\u0000\u0005trace\u0000\u0000\u0000\u0006accept\u0000\u0000\u0000"
          + "\u000Eaccept-charset\u0000\u0000\u0000\u000Faccept-encoding\u0000\u0000\u0000\u000Fa"
          + "ccept-language\u0000\u0000\u0000\raccept-ranges\u0000\u0000\u0000\u0003age\u0000"
          + "\u0000\u0000\u0005allow\u0000\u0000\u0000\rauthorization\u0000\u0000\u0000\rcache-co"
          + "ntrol\u0000\u0000\u0000\nconnection\u0000\u0000\u0000\fcontent-base\u0000\u0000"
          + "\u0000\u0010content-encoding\u0000\u0000\u0000\u0010content-language\u0000\u0000"
          + "\u0000\u000Econtent-length\u0000\u0000\u0000\u0010content-location\u0000\u0000\u0000"
          + "\u000Bcontent-md5\u0000\u0000\u0000\rcontent-range\u0000\u0000\u0000\fcontent-type"
          + "\u0000\u0000\u0000\u0004date\u0000\u0000\u0000\u0004etag\u0000\u0000\u0000\u0006expe"
          + "ct\u0000\u0000\u0000\u0007expires\u0000\u0000\u0000\u0004from\u0000\u0000\u0000"
          + "\u0004host\u0000\u0000\u0000\bif-match\u0000\u0000\u0000\u0011if-modified-since"
          + "\u0000\u0000\u0000\rif-none-match\u0000\u0000\u0000\bif-range\u0000\u0000\u0000"
          + "\u0013if-unmodified-since\u0000\u0000\u0000\rlast-modified\u0000\u0000\u0000\blocati"
          + "on\u0000\u0000\u0000\fmax-forwards\u0000\u0000\u0000\u0006pragma\u0000\u0000\u0000"
          + "\u0012proxy-authenticate\u0000\u0000\u0000\u0013proxy-authorization\u0000\u0000"
          + "\u0000\u0005range\u0000\u0000\u0000\u0007referer\u0000\u0000\u0000\u000Bretry-after"
          + "\u0000\u0000\u0000\u0006server\u0000\u0000\u0000\u0002te\u0000\u0000\u0000\u0007trai"
          + "ler\u0000\u0000\u0000\u0011transfer-encoding\u0000\u0000\u0000\u0007upgrade\u0000"
          + "\u0000\u0000\nuser-agent\u0000\u0000\u0000\u0004vary\u0000\u0000\u0000\u0003via"
          + "\u0000\u0000\u0000\u0007warning\u0000\u0000\u0000\u0010www-authenticate\u0000\u0000"
          + "\u0000\u0006method\u0000\u0000\u0000\u0003get\u0000\u0000\u0000\u0006status\u0000"
          + "\u0000\u0000\u0006200 OK\u0000\u0000\u0000\u0007version\u0000\u0000\u0000\bHTTP/1.1"
          + "\u0000\u0000\u0000\u0003url\u0000\u0000\u0000\u0006public\u0000\u0000\u0000\nset-coo"
          + "kie\u0000\u0000\u0000\nkeep-alive\u0000\u0000\u0000\u0006origin100101201202205206300"
          + "302303304305306307402405406407408409410411412413414415416417502504505203 Non-Authori"
          + "tative Information204 No Content301 Moved Permanently400 Bad Request401 Unauthorized"
          + "403 Forbidden404 Not Found500 Internal Server Error501 Not Implemented503 Service Un"
          + "availableJan Feb Mar Apr May Jun Jul Aug Sept Oct Nov Dec 00:00:00 Mon, Tue, Wed, Th"
          + "u, Fri, Sat, Sun, GMTchunked,text/html,image/png,image/jpg,image/gif,application/xml"
          + ",application/xhtml+xml,text/plain,text/javascript,publicprivatemax-age=gzip,deflate,"
          + "sdchcharset=utf-8charset=iso-8859-1,utf-,*,enq=0.").getBytes(Util.UTF_8.name());
    } catch (UnsupportedEncodingException e) {
      throw new AssertionError();
    }
  }

  @Override public FrameReader newReader(InputStream in, boolean client) {
    return new Reader(in, client);
  }

  @Override public FrameWriter newWriter(OutputStream out, boolean client) {
    return new Writer(out, client);
  }

  /** Read spdy/3 frames. */
  static final class Reader implements FrameReader {
    private final DataInputStream in;
    private final boolean client;
    private final NameValueBlockReader nameValueBlockReader;

    Reader(InputStream in, boolean client) {
      this.in = new DataInputStream(in);
      this.nameValueBlockReader = new NameValueBlockReader(in);
      this.client = client;
    }

    @Override public void readConnectionHeader() {
    }

    /**
     * Send the next frame to {@code handler}. Returns true unless there are no
     * more frames on the stream.
     */
    @Override public boolean nextFrame(Handler handler) throws IOException {
      int w1;
      try {
        w1 = in.readInt();
      } catch (IOException e) {
        return false; // This might be a normal socket close.
      }
      int w2 = in.readInt();

      boolean control = (w1 & 0x80000000) != 0;
      int flags = (w2 & 0xff000000) >>> 24;
      int length = (w2 & 0xffffff);

      if (control) {
        int version = (w1 & 0x7fff0000) >>> 16;
        int type = (w1 & 0xffff);

        if (version != 3) {
          throw new ProtocolException("version != 3: " + version);
        }

        switch (type) {
          case TYPE_SYN_STREAM:
            readSynStream(handler, flags, length);
            return true;

          case TYPE_SYN_REPLY:
            readSynReply(handler, flags, length);
            return true;

          case TYPE_RST_STREAM:
            readRstStream(handler, flags, length);
            return true;

          case TYPE_SETTINGS:
            readSettings(handler, flags, length);
            return true;

          case TYPE_NOOP:
            if (length != 0) throw ioException("TYPE_NOOP length: %d != 0", length);
            handler.noop();
            return true;

          case TYPE_PING:
            readPing(handler, flags, length);
            return true;

          case TYPE_GOAWAY:
            readGoAway(handler, flags, length);
            return true;

          case TYPE_HEADERS:
            readHeaders(handler, flags, length);
            return true;

          case TYPE_WINDOW_UPDATE:
            readWindowUpdate(handler, flags, length);
            return true;

          case TYPE_CREDENTIAL:
            Util.skipByReading(in, length);
            throw new UnsupportedOperationException("TODO"); // TODO: implement

          default:
            throw new IOException("Unexpected frame");
        }
      } else {
        int streamId = w1 & 0x7fffffff;
        boolean inFinished = (flags & FLAG_FIN) != 0;
        handler.data(inFinished, streamId, in, length);
        return true;
      }
    }

    private void readSynStream(Handler handler, int flags, int length) throws IOException {
      int w1 = in.readInt();
      int w2 = in.readInt();
      int s3 = in.readShort();
      int streamId = w1 & 0x7fffffff;
      int associatedStreamId = w2 & 0x7fffffff;
      int priority = (s3 & 0xe000) >>> 13;
      int slot = s3 & 0xff;
      List<String> nameValueBlock = nameValueBlockReader.readNameValueBlock(length - 10);

      boolean inFinished = (flags & FLAG_FIN) != 0;
      boolean outFinished = (flags & FLAG_UNIDIRECTIONAL) != 0;
      handler.headers(outFinished, inFinished, streamId, associatedStreamId, priority,
          nameValueBlock, HeadersMode.SPDY_SYN_STREAM);
    }

    private void readSynReply(Handler handler, int flags, int length) throws IOException {
      int w1 = in.readInt();
      int streamId = w1 & 0x7fffffff;
      List<String> nameValueBlock = nameValueBlockReader.readNameValueBlock(length - 4);
      boolean inFinished = (flags & FLAG_FIN) != 0;
      handler.headers(false, inFinished, streamId, -1, -1, nameValueBlock, HeadersMode.SPDY_REPLY);
    }

    private void readRstStream(Handler handler, int flags, int length) throws IOException {
      if (length != 8) throw ioException("TYPE_RST_STREAM length: %d != 8", length);
      int streamId = in.readInt() & 0x7fffffff;
      int errorCodeInt = in.readInt();
      ErrorCode errorCode = ErrorCode.fromSpdy3Rst(errorCodeInt);
      if (errorCode == null) {
        throw ioException("TYPE_RST_STREAM unexpected error code: %d", errorCodeInt);
      }
      handler.rstStream(streamId, errorCode);
    }

    private void readHeaders(Handler handler, int flags, int length) throws IOException {
      int w1 = in.readInt();
      int streamId = w1 & 0x7fffffff;
      List<String> nameValueBlock = nameValueBlockReader.readNameValueBlock(length - 4);
      handler.headers(false, false, streamId, -1, -1, nameValueBlock, HeadersMode.SPDY_HEADERS);
    }

    private void readWindowUpdate(Handler handler, int flags, int length) throws IOException {
      if (length != 8) throw ioException("TYPE_WINDOW_UPDATE length: %d != 8", length);
      int w1 = in.readInt();
      int w2 = in.readInt();
      int streamId = w1 & 0x7fffffff;
      int deltaWindowSize = w2 & 0x7fffffff;
      handler.windowUpdate(streamId, deltaWindowSize, false);
    }

    private void readPing(Handler handler, int flags, int length) throws IOException {
      if (length != 4) throw ioException("TYPE_PING length: %d != 4", length);
      int id = in.readInt();
      boolean reply = client == ((id % 2) == 1);
      handler.ping(reply, id, 0);
    }

    private void readGoAway(Handler handler, int flags, int length) throws IOException {
      if (length != 8) throw ioException("TYPE_GOAWAY length: %d != 8", length);
      int lastGoodStreamId = in.readInt() & 0x7fffffff;
      int errorCodeInt = in.readInt();
      ErrorCode errorCode = ErrorCode.fromSpdyGoAway(errorCodeInt);
      if (errorCode == null) {
        throw ioException("TYPE_GOAWAY unexpected error code: %d", errorCodeInt);
      }
      handler.goAway(lastGoodStreamId, errorCode);
    }

    private void readSettings(Handler handler, int flags, int length) throws IOException {
      int numberOfEntries = in.readInt();
      if (length != 4 + 8 * numberOfEntries) {
        throw ioException("TYPE_SETTINGS length: %d != 4 + 8 * %d", length, numberOfEntries);
      }
      Settings settings = new Settings();
      for (int i = 0; i < numberOfEntries; i++) {
        int w1 = in.readInt();
        int value = in.readInt();
        int idFlags = (w1 & 0xff000000) >>> 24;
        int id = w1 & 0xffffff;
        settings.set(id, idFlags, value);
      }
      boolean clearPrevious = (flags & Settings.FLAG_CLEAR_PREVIOUSLY_PERSISTED_SETTINGS) != 0;
      handler.settings(clearPrevious, settings);
    }

    private static IOException ioException(String message, Object... args) throws IOException {
      throw new IOException(String.format(message, args));
    }

    @Override public void close() throws IOException {
      Util.closeAll(in, nameValueBlockReader);
    }
  }

  /** Write spdy/3 frames. */
  static final class Writer implements FrameWriter {
    private final DataOutputStream out;
    private final ByteArrayOutputStream nameValueBlockBuffer;
    private final DataOutputStream nameValueBlockOut;
    private final boolean client;

    Writer(OutputStream out, boolean client) {
      this.out = new DataOutputStream(out);
      this.client = client;

      Deflater deflater = new Deflater();
      deflater.setDictionary(DICTIONARY);
      nameValueBlockBuffer = new ByteArrayOutputStream();
      nameValueBlockOut = new DataOutputStream(
          Platform.get().newDeflaterOutputStream(nameValueBlockBuffer, deflater, true));
    }

    @Override public synchronized void connectionHeader() {
      // Do nothing: no connection header for SPDY/3.
    }

    @Override public synchronized void flush() throws IOException {
      out.flush();
    }

    @Override public synchronized void synStream(boolean outFinished, boolean inFinished,
        int streamId, int associatedStreamId, int priority, int slot, List<String> nameValueBlock)
        throws IOException {
      writeNameValueBlockToBuffer(nameValueBlock);
      int length = 10 + nameValueBlockBuffer.size();
      int type = TYPE_SYN_STREAM;
      int flags = (outFinished ? FLAG_FIN : 0) | (inFinished ? FLAG_UNIDIRECTIONAL : 0);

      int unused = 0;
      out.writeInt(0x80000000 | (VERSION & 0x7fff) << 16 | type & 0xffff);
      out.writeInt((flags & 0xff) << 24 | length & 0xffffff);
      out.writeInt(streamId & 0x7fffffff);
      out.writeInt(associatedStreamId & 0x7fffffff);
      out.writeShort((priority & 0x7) << 13 | (unused & 0x1f) << 8 | (slot & 0xff));
      nameValueBlockBuffer.writeTo(out);
      out.flush();
    }

    @Override public synchronized void synReply(
        boolean outFinished, int streamId, List<String> nameValueBlock) throws IOException {
      writeNameValueBlockToBuffer(nameValueBlock);
      int type = TYPE_SYN_REPLY;
      int flags = (outFinished ? FLAG_FIN : 0);
      int length = nameValueBlockBuffer.size() + 4;

      out.writeInt(0x80000000 | (VERSION & 0x7fff) << 16 | type & 0xffff);
      out.writeInt((flags & 0xff) << 24 | length & 0xffffff);
      out.writeInt(streamId & 0x7fffffff);
      nameValueBlockBuffer.writeTo(out);
      out.flush();
    }

    @Override public synchronized void headers(int streamId, List<String> nameValueBlock)
        throws IOException {
      writeNameValueBlockToBuffer(nameValueBlock);
      int flags = 0;
      int type = TYPE_HEADERS;
      int length = nameValueBlockBuffer.size() + 4;

      out.writeInt(0x80000000 | (VERSION & 0x7fff) << 16 | type & 0xffff);
      out.writeInt((flags & 0xff) << 24 | length & 0xffffff);
      out.writeInt(streamId & 0x7fffffff);
      nameValueBlockBuffer.writeTo(out);
      out.flush();
    }

    @Override public synchronized void rstStream(int streamId, ErrorCode errorCode)
        throws IOException {
      if (errorCode.spdyRstCode == -1) throw new IllegalArgumentException();
      int flags = 0;
      int type = TYPE_RST_STREAM;
      int length = 8;
      out.writeInt(0x80000000 | (VERSION & 0x7fff) << 16 | type & 0xffff);
      out.writeInt((flags & 0xff) << 24 | length & 0xffffff);
      out.writeInt(streamId & 0x7fffffff);
      out.writeInt(errorCode.spdyRstCode);
      out.flush();
    }

    @Override public synchronized void data(boolean outFinished, int streamId, byte[] data)
        throws IOException {
      data(outFinished, streamId, data, 0, data.length);
    }

    @Override public synchronized void data(boolean outFinished, int streamId, byte[] data,
        int offset, int byteCount) throws IOException {
      int flags = (outFinished ? FLAG_FIN : 0);
      out.writeInt(streamId & 0x7fffffff);
      out.writeInt((flags & 0xff) << 24 | byteCount & 0xffffff);
      out.write(data, offset, byteCount);
    }

    private void writeNameValueBlockToBuffer(List<String> nameValueBlock) throws IOException {
      nameValueBlockBuffer.reset();
      int numberOfPairs = nameValueBlock.size() / 2;
      nameValueBlockOut.writeInt(numberOfPairs);
      for (String s : nameValueBlock) {
        nameValueBlockOut.writeInt(s.length());
        nameValueBlockOut.write(s.getBytes("UTF-8"));
      }
      nameValueBlockOut.flush();
    }

    @Override public synchronized void settings(Settings settings) throws IOException {
      int type = TYPE_SETTINGS;
      int flags = 0;
      int size = settings.size();
      int length = 4 + size * 8;
      out.writeInt(0x80000000 | (VERSION & 0x7fff) << 16 | type & 0xffff);
      out.writeInt((flags & 0xff) << 24 | length & 0xffffff);
      out.writeInt(size);
      for (int i = 0; i <= Settings.COUNT; i++) {
        if (!settings.isSet(i)) continue;
        int settingsFlags = settings.flags(i);
        out.writeInt((settingsFlags & 0xff) << 24 | (i & 0xffffff));
        out.writeInt(settings.get(i));
      }
      out.flush();
    }

    @Override public synchronized void noop() throws IOException {
      int type = TYPE_NOOP;
      int length = 0;
      int flags = 0;
      out.writeInt(0x80000000 | (VERSION & 0x7fff) << 16 | type & 0xffff);
      out.writeInt((flags & 0xff) << 24 | length & 0xffffff);
      out.flush();
    }

    @Override public synchronized void ping(boolean reply, int payload1, int payload2)
        throws IOException {
      boolean payloadIsReply = client != ((payload1 % 2) == 1);
      if (reply != payloadIsReply) throw new IllegalArgumentException("payload != reply");
      int type = TYPE_PING;
      int flags = 0;
      int length = 4;
      out.writeInt(0x80000000 | (VERSION & 0x7fff) << 16 | type & 0xffff);
      out.writeInt((flags & 0xff) << 24 | length & 0xffffff);
      out.writeInt(payload1);
      out.flush();
    }

    @Override public synchronized void goAway(int lastGoodStreamId, ErrorCode errorCode)
        throws IOException {
      if (errorCode.spdyGoAwayCode == -1) throw new IllegalArgumentException();
      int type = TYPE_GOAWAY;
      int flags = 0;
      int length = 8;
      out.writeInt(0x80000000 | (VERSION & 0x7fff) << 16 | type & 0xffff);
      out.writeInt((flags & 0xff) << 24 | length & 0xffffff);
      out.writeInt(lastGoodStreamId);
      out.writeInt(errorCode.spdyGoAwayCode);
      out.flush();
    }

    @Override public synchronized void windowUpdate(int streamId, int deltaWindowSize)
        throws IOException {
      int type = TYPE_WINDOW_UPDATE;
      int flags = 0;
      int length = 8;
      out.writeInt(0x80000000 | (VERSION & 0x7fff) << 16 | type & 0xffff);
      out.writeInt((flags & 0xff) << 24 | length & 0xffffff);
      out.writeInt(streamId);
      out.writeInt(deltaWindowSize);
      out.flush();
    }

    @Override public void close() throws IOException {
      Util.closeAll(out, nameValueBlockOut);
    }
  }
}


File: platforms/android/CordovaLib/src/com/squareup/okhttp/internal/spdy/SpdyConnection.java
/*
 * Copyright (C) 2011 The Android Open Source Project
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

import com.squareup.okhttp.internal.NamedRunnable;
import com.squareup.okhttp.internal.Util;
import java.io.Closeable;
import java.io.IOException;
import java.io.InputStream;
import java.io.OutputStream;
import java.net.Socket;
import java.util.HashMap;
import java.util.Iterator;
import java.util.List;
import java.util.Map;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.SynchronousQueue;
import java.util.concurrent.ThreadPoolExecutor;
import java.util.concurrent.TimeUnit;

/**
 * A socket connection to a remote peer. A connection hosts streams which can
 * send and receive data.
 *
 * <p>Many methods in this API are <strong>synchronous:</strong> the call is
 * completed before the method returns. This is typical for Java but atypical
 * for SPDY. This is motivated by exception transparency: an IOException that
 * was triggered by a certain caller can be caught and handled by that caller.
 */
public final class SpdyConnection implements Closeable {

  // Internal state of this connection is guarded by 'this'. No blocking
  // operations may be performed while holding this lock!
  //
  // Socket writes are guarded by frameWriter.
  //
  // Socket reads are unguarded but are only made by the reader thread.
  //
  // Certain operations (like SYN_STREAM) need to synchronize on both the
  // frameWriter (to do blocking I/O) and this (to create streams). Such
  // operations must synchronize on 'this' last. This ensures that we never
  // wait for a blocking operation while holding 'this'.

  private static final ExecutorService executor = new ThreadPoolExecutor(0,
      Integer.MAX_VALUE, 60, TimeUnit.SECONDS, new SynchronousQueue<Runnable>(),
      Util.daemonThreadFactory("OkHttp SpdyConnection"));

  /** The protocol variant, like SPDY/3 or HTTP-draft-06/2.0. */
  final Variant variant;

  /** True if this peer initiated the connection. */
  final boolean client;

  /**
   * User code to run in response to an incoming stream. Callbacks must not be
   * run on the callback executor.
   */
  private final IncomingStreamHandler handler;
  private final FrameReader frameReader;
  private final FrameWriter frameWriter;

  private final Map<Integer, SpdyStream> streams = new HashMap<Integer, SpdyStream>();
  private final String hostName;
  private int lastGoodStreamId;
  private int nextStreamId;
  private boolean shutdown;
  private long idleStartTimeNs = System.nanoTime();

  /** Lazily-created map of in-flight pings awaiting a response. Guarded by this. */
  private Map<Integer, Ping> pings;
  private int nextPingId;

  /** Lazily-created settings for the peer. */
  Settings settings;

  private SpdyConnection(Builder builder) {
    variant = builder.variant;
    client = builder.client;
    handler = builder.handler;
    frameReader = variant.newReader(builder.in, client);
    frameWriter = variant.newWriter(builder.out, client);
    nextStreamId = builder.client ? 1 : 2;
    nextPingId = builder.client ? 1 : 2;

    hostName = builder.hostName;

    new Thread(new Reader(), "Spdy Reader " + hostName).start();
  }

  /**
   * Returns the number of {@link SpdyStream#isOpen() open streams} on this
   * connection.
   */
  public synchronized int openStreamCount() {
    return streams.size();
  }

  private synchronized SpdyStream getStream(int id) {
    return streams.get(id);
  }

  synchronized SpdyStream removeStream(int streamId) {
    SpdyStream stream = streams.remove(streamId);
    if (stream != null && streams.isEmpty()) {
      setIdle(true);
    }
    return stream;
  }

  private synchronized void setIdle(boolean value) {
    idleStartTimeNs = value ? System.nanoTime() : Long.MAX_VALUE;
  }

  /** Returns true if this connection is idle. */
  public synchronized boolean isIdle() {
    return idleStartTimeNs != Long.MAX_VALUE;
  }

  /**
   * Returns the time in ns when this connection became idle or Long.MAX_VALUE
   * if connection is not idle.
   */
  public synchronized long getIdleStartTimeNs() {
    return idleStartTimeNs;
  }

  /**
   * Returns a new locally-initiated stream.
   *
   * @param out true to create an output stream that we can use to send data
   *     to the remote peer. Corresponds to {@code FLAG_FIN}.
   * @param in true to create an input stream that the remote peer can use to
   *     send data to us. Corresponds to {@code FLAG_UNIDIRECTIONAL}.
   */
  public SpdyStream newStream(List<String> requestHeaders, boolean out, boolean in)
      throws IOException {
    boolean outFinished = !out;
    boolean inFinished = !in;
    int associatedStreamId = 0;  // TODO: permit the caller to specify an associated stream?
    int priority = 0; // TODO: permit the caller to specify a priority?
    int slot = 0; // TODO: permit the caller to specify a slot?
    SpdyStream stream;
    int streamId;

    synchronized (frameWriter) {
      synchronized (this) {
        if (shutdown) {
          throw new IOException("shutdown");
        }
        streamId = nextStreamId;
        nextStreamId += 2;
        stream = new SpdyStream(
            streamId, this, outFinished, inFinished, priority, requestHeaders, settings);
        if (stream.isOpen()) {
          streams.put(streamId, stream);
          setIdle(false);
        }
      }

      frameWriter.synStream(outFinished, inFinished, streamId, associatedStreamId, priority, slot,
          requestHeaders);
    }

    return stream;
  }

  void writeSynReply(int streamId, boolean outFinished, List<String> alternating)
      throws IOException {
    frameWriter.synReply(outFinished, streamId, alternating);
  }

  public void writeData(int streamId, boolean outFinished, byte[] buffer, int offset, int byteCount)
      throws IOException {
    frameWriter.data(outFinished, streamId, buffer, offset, byteCount);
  }

  void writeSynResetLater(final int streamId, final ErrorCode errorCode) {
    executor.submit(new NamedRunnable("OkHttp SPDY Writer %s stream %d", hostName, streamId) {
      @Override public void execute() {
        try {
          writeSynReset(streamId, errorCode);
        } catch (IOException ignored) {
        }
      }
    });
  }

  void writeSynReset(int streamId, ErrorCode statusCode) throws IOException {
    frameWriter.rstStream(streamId, statusCode);
  }

  void writeWindowUpdateLater(final int streamId, final int deltaWindowSize) {
    executor.submit(new NamedRunnable("OkHttp SPDY Writer %s stream %d", hostName, streamId) {
      @Override public void execute() {
        try {
          writeWindowUpdate(streamId, deltaWindowSize);
        } catch (IOException ignored) {
        }
      }
    });
  }

  void writeWindowUpdate(int streamId, int deltaWindowSize) throws IOException {
    frameWriter.windowUpdate(streamId, deltaWindowSize);
  }

  /**
   * Sends a ping frame to the peer. Use the returned object to await the
   * ping's response and observe its round trip time.
   */
  public Ping ping() throws IOException {
    Ping ping = new Ping();
    int pingId;
    synchronized (this) {
      if (shutdown) {
        throw new IOException("shutdown");
      }
      pingId = nextPingId;
      nextPingId += 2;
      if (pings == null) pings = new HashMap<Integer, Ping>();
      pings.put(pingId, ping);
    }
    writePing(false, pingId, 0x4f4b6f6b /* ASCII "OKok" */, ping);
    return ping;
  }

  private void writePingLater(
      final boolean reply, final int payload1, final int payload2, final Ping ping) {
    executor.submit(new NamedRunnable("OkHttp SPDY Writer %s ping %08x%08x",
        hostName, payload1, payload2) {
      @Override public void execute() {
        try {
          writePing(reply, payload1, payload2, ping);
        } catch (IOException ignored) {
        }
      }
    });
  }

  private void writePing(boolean reply, int payload1, int payload2, Ping ping) throws IOException {
    synchronized (frameWriter) {
      // Observe the sent time immediately before performing I/O.
      if (ping != null) ping.send();
      frameWriter.ping(reply, payload1, payload2);
    }
  }

  private synchronized Ping removePing(int id) {
    return pings != null ? pings.remove(id) : null;
  }

  /** Sends a noop frame to the peer. */
  public void noop() throws IOException {
    frameWriter.noop();
  }

  public void flush() throws IOException {
    frameWriter.flush();
  }

  /**
   * Degrades this connection such that new streams can neither be created
   * locally, nor accepted from the remote peer. Existing streams are not
   * impacted. This is intended to permit an endpoint to gracefully stop
   * accepting new requests without harming previously established streams.
   */
  public void shutdown(ErrorCode statusCode) throws IOException {
    synchronized (frameWriter) {
      int lastGoodStreamId;
      synchronized (this) {
        if (shutdown) {
          return;
        }
        shutdown = true;
        lastGoodStreamId = this.lastGoodStreamId;
      }
      frameWriter.goAway(lastGoodStreamId, statusCode);
    }
  }

  /**
   * Closes this connection. This cancels all open streams and unanswered
   * pings. It closes the underlying input and output streams and shuts down
   * internal executor services.
   */
  @Override public void close() throws IOException {
    close(ErrorCode.NO_ERROR, ErrorCode.CANCEL);
  }

  private void close(ErrorCode connectionCode, ErrorCode streamCode) throws IOException {
    assert (!Thread.holdsLock(this));
    IOException thrown = null;
    try {
      shutdown(connectionCode);
    } catch (IOException e) {
      thrown = e;
    }

    SpdyStream[] streamsToClose = null;
    Ping[] pingsToCancel = null;
    synchronized (this) {
      if (!streams.isEmpty()) {
        streamsToClose = streams.values().toArray(new SpdyStream[streams.size()]);
        streams.clear();
        setIdle(false);
      }
      if (pings != null) {
        pingsToCancel = pings.values().toArray(new Ping[pings.size()]);
        pings = null;
      }
    }

    if (streamsToClose != null) {
      for (SpdyStream stream : streamsToClose) {
        try {
          stream.close(streamCode);
        } catch (IOException e) {
          if (thrown != null) thrown = e;
        }
      }
    }

    if (pingsToCancel != null) {
      for (Ping ping : pingsToCancel) {
        ping.cancel();
      }
    }

    try {
      frameReader.close();
    } catch (IOException e) {
      thrown = e;
    }
    try {
      frameWriter.close();
    } catch (IOException e) {
      if (thrown == null) thrown = e;
    }

    if (thrown != null) throw thrown;
  }

  /**
   * Sends a connection header if the current variant requires it. This should
   * be called after {@link Builder#build} for all new connections.
   */
  public void sendConnectionHeader() throws IOException {
    frameWriter.connectionHeader();
    frameWriter.settings(new Settings());
  }

  /**
   * Reads a connection header if the current variant requires it. This should
   * be called after {@link Builder#build} for all new connections.
   */
  public void readConnectionHeader() throws IOException {
    frameReader.readConnectionHeader();
  }

  public static class Builder {
    private String hostName;
    private InputStream in;
    private OutputStream out;
    private IncomingStreamHandler handler = IncomingStreamHandler.REFUSE_INCOMING_STREAMS;
    private Variant variant = Variant.SPDY3;
    private boolean client;

    public Builder(boolean client, Socket socket) throws IOException {
      this("", client, socket.getInputStream(), socket.getOutputStream());
    }

    public Builder(boolean client, InputStream in, OutputStream out) {
      this("", client, in, out);
    }

    /**
     * @param client true if this peer initiated the connection; false if
     * this peer accepted the connection.
     */
    public Builder(String hostName, boolean client, Socket socket) throws IOException {
      this(hostName, client, socket.getInputStream(), socket.getOutputStream());
    }

    /**
     * @param client true if this peer initiated the connection; false if this
     * peer accepted the connection.
     */
    public Builder(String hostName, boolean client, InputStream in, OutputStream out) {
      this.hostName = hostName;
      this.client = client;
      this.in = in;
      this.out = out;
    }

    public Builder handler(IncomingStreamHandler handler) {
      this.handler = handler;
      return this;
    }

    public Builder spdy3() {
      this.variant = Variant.SPDY3;
      return this;
    }

    public Builder http20Draft06() {
      this.variant = Variant.HTTP_20_DRAFT_06;
      return this;
    }

    public SpdyConnection build() {
      return new SpdyConnection(this);
    }
  }

  private class Reader implements Runnable, FrameReader.Handler {
    @Override public void run() {
      ErrorCode connectionErrorCode = ErrorCode.INTERNAL_ERROR;
      ErrorCode streamErrorCode = ErrorCode.INTERNAL_ERROR;
      try {
        while (frameReader.nextFrame(this)) {
        }
        connectionErrorCode = ErrorCode.NO_ERROR;
        streamErrorCode = ErrorCode.CANCEL;
      } catch (IOException e) {
        connectionErrorCode = ErrorCode.PROTOCOL_ERROR;
        streamErrorCode = ErrorCode.PROTOCOL_ERROR;
      } finally {
        try {
          close(connectionErrorCode, streamErrorCode);
        } catch (IOException ignored) {
        }
      }
    }

    @Override public void data(boolean inFinished, int streamId, InputStream in, int length)
        throws IOException {
      SpdyStream dataStream = getStream(streamId);
      if (dataStream == null) {
        writeSynResetLater(streamId, ErrorCode.INVALID_STREAM);
        Util.skipByReading(in, length);
        return;
      }
      dataStream.receiveData(in, length);
      if (inFinished) {
        dataStream.receiveFin();
      }
    }

    @Override public void headers(boolean outFinished, boolean inFinished, int streamId,
        int associatedStreamId, int priority, List<String> nameValueBlock,
        HeadersMode headersMode) {
      SpdyStream stream;
      synchronized (SpdyConnection.this) {
        // If we're shutdown, don't bother with this stream.
        if (shutdown) return;

        stream = getStream(streamId);

        if (stream == null) {
          // The headers claim to be for an existing stream, but we don't have one.
          if (headersMode.failIfStreamAbsent()) {
            writeSynResetLater(streamId, ErrorCode.INVALID_STREAM);
            return;
          }

          // If the stream ID is less than the last created ID, assume it's already closed.
          if (streamId <= lastGoodStreamId) return;

          // If the stream ID is in the client's namespace, assume it's already closed.
          if (streamId % 2 == nextStreamId % 2) return;

          // Create a stream.
          final SpdyStream newStream = new SpdyStream(streamId, SpdyConnection.this, outFinished,
              inFinished, priority, nameValueBlock, settings);
          lastGoodStreamId = streamId;
          streams.put(streamId, newStream);
          executor.submit(new NamedRunnable("OkHttp Callback %s stream %d", hostName, streamId) {
            @Override public void execute() {
              try {
                handler.receive(newStream);
              } catch (IOException e) {
                throw new RuntimeException(e);
              }
            }
          });
          return;
        }
      }

      // The headers claim to be for a new stream, but we already have one.
      if (headersMode.failIfStreamPresent()) {
        stream.closeLater(ErrorCode.PROTOCOL_ERROR);
        removeStream(streamId);
        return;
      }

      // Update an existing stream.
      stream.receiveHeaders(nameValueBlock, headersMode);
      if (inFinished) stream.receiveFin();
    }

    @Override public void rstStream(int streamId, ErrorCode errorCode) {
      SpdyStream rstStream = removeStream(streamId);
      if (rstStream != null) {
        rstStream.receiveRstStream(errorCode);
      }
    }

    @Override public void settings(boolean clearPrevious, Settings newSettings) {
      SpdyStream[] streamsToNotify = null;
      synchronized (SpdyConnection.this) {
        if (settings == null || clearPrevious) {
          settings = newSettings;
        } else {
          settings.merge(newSettings);
        }
        if (!streams.isEmpty()) {
          streamsToNotify = streams.values().toArray(new SpdyStream[streams.size()]);
        }
      }
      if (streamsToNotify != null) {
        for (SpdyStream stream : streamsToNotify) {
          // The synchronization here is ugly. We need to synchronize on 'this' to guard
          // reads to 'settings'. We synchronize on 'stream' to guard the state change.
          // And we need to acquire the 'stream' lock first, since that may block.
          // TODO: this can block the reader thread until a write completes. That's bad!
          synchronized (stream) {
            synchronized (SpdyConnection.this) {
              stream.receiveSettings(settings);
            }
          }
        }
      }
    }

    @Override public void noop() {
    }

    @Override public void ping(boolean reply, int payload1, int payload2) {
      if (reply) {
        Ping ping = removePing(payload1);
        if (ping != null) {
          ping.receive();
        }
      } else {
        // Send a reply to a client ping if this is a server and vice versa.
        writePingLater(true, payload1, payload2, null);
      }
    }

    @Override public void goAway(int lastGoodStreamId, ErrorCode errorCode) {
      synchronized (SpdyConnection.this) {
        shutdown = true;

        // Fail all streams created after the last good stream ID.
        for (Iterator<Map.Entry<Integer, SpdyStream>> i = streams.entrySet().iterator();
            i.hasNext(); ) {
          Map.Entry<Integer, SpdyStream> entry = i.next();
          int streamId = entry.getKey();
          if (streamId > lastGoodStreamId && entry.getValue().isLocallyInitiated()) {
            entry.getValue().receiveRstStream(ErrorCode.REFUSED_STREAM);
            i.remove();
          }
        }
      }
    }

    @Override public void windowUpdate(int streamId, int deltaWindowSize, boolean endFlowControl) {
      if (streamId == 0) {
        // TODO: honor whole-stream flow control
        return;
      }

      // TODO: honor endFlowControl
      SpdyStream stream = getStream(streamId);
      if (stream != null) {
        stream.receiveWindowUpdate(deltaWindowSize);
      }
    }

    @Override public void priority(int streamId, int priority) {
      // TODO: honor priority.
    }
  }
}


File: platforms/android/CordovaLib/src/com/squareup/okhttp/internal/spdy/SpdyStream.java
/*
 * Copyright (C) 2011 The Android Open Source Project
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

import com.squareup.okhttp.internal.Util;
import java.io.IOException;
import java.io.InputStream;
import java.io.InterruptedIOException;
import java.io.OutputStream;
import java.net.SocketTimeoutException;
import java.util.ArrayList;
import java.util.List;

import static com.squareup.okhttp.internal.Util.checkOffsetAndCount;

/** A logical bidirectional stream. */
public final class SpdyStream {

  // Internal state is guarded by this. No long-running or potentially
  // blocking operations are performed while the lock is held.

  /**
   * The number of unacknowledged bytes at which the input stream will send
   * the peer a {@code WINDOW_UPDATE} frame. Must be less than this client's
   * window size, otherwise the remote peer will stop sending data on this
   * stream. (Chrome 25 uses 5 MiB.)
   */
  public static final int WINDOW_UPDATE_THRESHOLD = Settings.DEFAULT_INITIAL_WINDOW_SIZE / 2;

  private final int id;
  private final SpdyConnection connection;
  private final int priority;
  private long readTimeoutMillis = 0;
  private int writeWindowSize;

  /** Headers sent by the stream initiator. Immutable and non null. */
  private final List<String> requestHeaders;

  /** Headers sent in the stream reply. Null if reply is either not sent or not sent yet. */
  private List<String> responseHeaders;

  private final SpdyDataInputStream in = new SpdyDataInputStream();
  private final SpdyDataOutputStream out = new SpdyDataOutputStream();

  /**
   * The reason why this stream was abnormally closed. If there are multiple
   * reasons to abnormally close this stream (such as both peers closing it
   * near-simultaneously) then this is the first reason known to this peer.
   */
  private ErrorCode errorCode = null;

  SpdyStream(int id, SpdyConnection connection, boolean outFinished, boolean inFinished,
      int priority, List<String> requestHeaders, Settings settings) {
    if (connection == null) throw new NullPointerException("connection == null");
    if (requestHeaders == null) throw new NullPointerException("requestHeaders == null");
    this.id = id;
    this.connection = connection;
    this.in.finished = inFinished;
    this.out.finished = outFinished;
    this.priority = priority;
    this.requestHeaders = requestHeaders;

    setSettings(settings);
  }

  /**
   * Returns true if this stream is open. A stream is open until either:
   * <ul>
   * <li>A {@code SYN_RESET} frame abnormally terminates the stream.
   * <li>Both input and output streams have transmitted all data and
   * headers.
   * </ul>
   * Note that the input stream may continue to yield data even after a stream
   * reports itself as not open. This is because input data is buffered.
   */
  public synchronized boolean isOpen() {
    if (errorCode != null) {
      return false;
    }
    if ((in.finished || in.closed) && (out.finished || out.closed) && responseHeaders != null) {
      return false;
    }
    return true;
  }

  /** Returns true if this stream was created by this peer. */
  public boolean isLocallyInitiated() {
    boolean streamIsClient = (id % 2 == 1);
    return connection.client == streamIsClient;
  }

  public SpdyConnection getConnection() {
    return connection;
  }

  public List<String> getRequestHeaders() {
    return requestHeaders;
  }

  /**
   * Returns the stream's response headers, blocking if necessary if they
   * have not been received yet.
   */
  public synchronized List<String> getResponseHeaders() throws IOException {
    long remaining = 0;
    long start = 0;
    if (readTimeoutMillis != 0) {
      start = (System.nanoTime() / 1000000);
      remaining = readTimeoutMillis;
    }
    try {
      while (responseHeaders == null && errorCode == null) {
        if (readTimeoutMillis == 0) { // No timeout configured.
          wait();
        } else if (remaining > 0) {
          wait(remaining);
          remaining = start + readTimeoutMillis - (System.nanoTime() / 1000000);
        } else {
          throw new SocketTimeoutException("Read response header timeout. readTimeoutMillis: "
                            + readTimeoutMillis);
        }
      }
      if (responseHeaders != null) {
        return responseHeaders;
      }
      throw new IOException("stream was reset: " + errorCode);
    } catch (InterruptedException e) {
      InterruptedIOException rethrow = new InterruptedIOException();
      rethrow.initCause(e);
      throw rethrow;
    }
  }

  /**
   * Returns the reason why this stream was closed, or null if it closed
   * normally or has not yet been closed.
   */
  public synchronized ErrorCode getErrorCode() {
    return errorCode;
  }

  /**
   * Sends a reply to an incoming stream.
   *
   * @param out true to create an output stream that we can use to send data
   * to the remote peer. Corresponds to {@code FLAG_FIN}.
   */
  public void reply(List<String> responseHeaders, boolean out) throws IOException {
    assert (!Thread.holdsLock(SpdyStream.this));
    boolean outFinished = false;
    synchronized (this) {
      if (responseHeaders == null) {
        throw new NullPointerException("responseHeaders == null");
      }
      if (isLocallyInitiated()) {
        throw new IllegalStateException("cannot reply to a locally initiated stream");
      }
      if (this.responseHeaders != null) {
        throw new IllegalStateException("reply already sent");
      }
      this.responseHeaders = responseHeaders;
      if (!out) {
        this.out.finished = true;
        outFinished = true;
      }
    }
    connection.writeSynReply(id, outFinished, responseHeaders);
  }

  /**
   * Sets the maximum time to wait on input stream reads before failing with a
   * {@code SocketTimeoutException}, or {@code 0} to wait indefinitely.
   */
  public void setReadTimeout(long readTimeoutMillis) {
    this.readTimeoutMillis = readTimeoutMillis;
  }

  public long getReadTimeoutMillis() {
    return readTimeoutMillis;
  }

  /** Returns an input stream that can be used to read data from the peer. */
  public InputStream getInputStream() {
    return in;
  }

  /**
   * Returns an output stream that can be used to write data to the peer.
   *
   * @throws IllegalStateException if this stream was initiated by the peer
   * and a {@link #reply} has not yet been sent.
   */
  public OutputStream getOutputStream() {
    synchronized (this) {
      if (responseHeaders == null && !isLocallyInitiated()) {
        throw new IllegalStateException("reply before requesting the output stream");
      }
    }
    return out;
  }

  /**
   * Abnormally terminate this stream. This blocks until the {@code RST_STREAM}
   * frame has been transmitted.
   */
  public void close(ErrorCode rstStatusCode) throws IOException {
    if (!closeInternal(rstStatusCode)) {
      return; // Already closed.
    }
    connection.writeSynReset(id, rstStatusCode);
  }

  /**
   * Abnormally terminate this stream. This enqueues a {@code RST_STREAM}
   * frame and returns immediately.
   */
  public void closeLater(ErrorCode errorCode) {
    if (!closeInternal(errorCode)) {
      return; // Already closed.
    }
    connection.writeSynResetLater(id, errorCode);
  }

  /** Returns true if this stream was closed. */
  private boolean closeInternal(ErrorCode errorCode) {
    assert (!Thread.holdsLock(this));
    synchronized (this) {
      if (this.errorCode != null) {
        return false;
      }
      if (in.finished && out.finished) {
        return false;
      }
      this.errorCode = errorCode;
      notifyAll();
    }
    connection.removeStream(id);
    return true;
  }

  void receiveHeaders(List<String> headers, HeadersMode headersMode) {
    assert (!Thread.holdsLock(SpdyStream.this));
    ErrorCode errorCode = null;
    boolean open = true;
    synchronized (this) {
      if (responseHeaders == null) {
        if (headersMode.failIfHeadersAbsent()) {
          errorCode = ErrorCode.PROTOCOL_ERROR;
        } else {
          responseHeaders = headers;
          open = isOpen();
          notifyAll();
        }
      } else {
        if (headersMode.failIfHeadersPresent()) {
          errorCode = ErrorCode.STREAM_IN_USE;
        } else {
          List<String> newHeaders = new ArrayList<String>();
          newHeaders.addAll(responseHeaders);
          newHeaders.addAll(headers);
          this.responseHeaders = newHeaders;
        }
      }
    }
    if (errorCode != null) {
      closeLater(errorCode);
    } else if (!open) {
      connection.removeStream(id);
    }
  }

  void receiveData(InputStream in, int length) throws IOException {
    assert (!Thread.holdsLock(SpdyStream.this));
    this.in.receive(in, length);
  }

  void receiveFin() {
    assert (!Thread.holdsLock(SpdyStream.this));
    boolean open;
    synchronized (this) {
      this.in.finished = true;
      open = isOpen();
      notifyAll();
    }
    if (!open) {
      connection.removeStream(id);
    }
  }

  synchronized void receiveRstStream(ErrorCode errorCode) {
    if (this.errorCode == null) {
      this.errorCode = errorCode;
      notifyAll();
    }
  }

  private void setSettings(Settings settings) {
    // TODO: For HTTP/2.0, also adjust the stream flow control window size
    // by the difference between the new value and the old value.
    assert (Thread.holdsLock(connection)); // Because 'settings' is guarded by 'connection'.
    this.writeWindowSize = settings != null
        ? settings.getInitialWindowSize(Settings.DEFAULT_INITIAL_WINDOW_SIZE)
        : Settings.DEFAULT_INITIAL_WINDOW_SIZE;
  }

  void receiveSettings(Settings settings) {
    assert (Thread.holdsLock(this));
    setSettings(settings);
    notifyAll();
  }

  synchronized void receiveWindowUpdate(int deltaWindowSize) {
    out.unacknowledgedBytes -= deltaWindowSize;
    notifyAll();
  }

  int getPriority() {
    return priority;
  }

  /**
   * An input stream that reads the incoming data frames of a stream. Although
   * this class uses synchronization to safely receive incoming data frames,
   * it is not intended for use by multiple readers.
   */
  private final class SpdyDataInputStream extends InputStream {
    // Store incoming data bytes in a circular buffer. When the buffer is
    // empty, pos == -1. Otherwise pos is the first byte to read and limit
    // is the first byte to write.
    //
    // { - - - X X X X - - - }
    //         ^       ^
    //        pos    limit
    //
    // { X X X - - - - X X X }
    //         ^       ^
    //       limit    pos

    private final byte[] buffer = new byte[Settings.DEFAULT_INITIAL_WINDOW_SIZE];

    /** the next byte to be read, or -1 if the buffer is empty. Never buffer.length */
    private int pos = -1;

    /** the last byte to be read. Never buffer.length */
    private int limit;

    /** True if the caller has closed this stream. */
    private boolean closed;

    /**
     * True if either side has cleanly shut down this stream. We will
     * receive no more bytes beyond those already in the buffer.
     */
    private boolean finished;

    /**
     * The total number of bytes consumed by the application (with {@link
     * #read}), but not yet acknowledged by sending a {@code WINDOW_UPDATE}
     * frame.
     */
    private int unacknowledgedBytes = 0;

    @Override public int available() throws IOException {
      synchronized (SpdyStream.this) {
        checkNotClosed();
        if (pos == -1) {
          return 0;
        } else if (limit > pos) {
          return limit - pos;
        } else {
          return limit + (buffer.length - pos);
        }
      }
    }

    @Override public int read() throws IOException {
      return Util.readSingleByte(this);
    }

    @Override public int read(byte[] b, int offset, int count) throws IOException {
      synchronized (SpdyStream.this) {
        checkOffsetAndCount(b.length, offset, count);
        waitUntilReadable();
        checkNotClosed();

        if (pos == -1) {
          return -1;
        }

        int copied = 0;

        // drain from [pos..buffer.length)
        if (limit <= pos) {
          int bytesToCopy = Math.min(count, buffer.length - pos);
          System.arraycopy(buffer, pos, b, offset, bytesToCopy);
          pos += bytesToCopy;
          copied += bytesToCopy;
          if (pos == buffer.length) {
            pos = 0;
          }
        }

        // drain from [pos..limit)
        if (copied < count) {
          int bytesToCopy = Math.min(limit - pos, count - copied);
          System.arraycopy(buffer, pos, b, offset + copied, bytesToCopy);
          pos += bytesToCopy;
          copied += bytesToCopy;
        }

        // Flow control: notify the peer that we're ready for more data!
        unacknowledgedBytes += copied;
        if (unacknowledgedBytes >= WINDOW_UPDATE_THRESHOLD) {
          connection.writeWindowUpdateLater(id, unacknowledgedBytes);
          unacknowledgedBytes = 0;
        }

        if (pos == limit) {
          pos = -1;
          limit = 0;
        }

        return copied;
      }
    }

    /**
     * Returns once the input stream is either readable or finished. Throws
     * a {@link SocketTimeoutException} if the read timeout elapses before
     * that happens.
     */
    private void waitUntilReadable() throws IOException {
      long start = 0;
      long remaining = 0;
      if (readTimeoutMillis != 0) {
        start = (System.nanoTime() / 1000000);
        remaining = readTimeoutMillis;
      }
      try {
        while (pos == -1 && !finished && !closed && errorCode == null) {
          if (readTimeoutMillis == 0) {
            SpdyStream.this.wait();
          } else if (remaining > 0) {
            SpdyStream.this.wait(remaining);
            remaining = start + readTimeoutMillis - (System.nanoTime() / 1000000);
          } else {
            throw new SocketTimeoutException();
          }
        }
      } catch (InterruptedException e) {
        throw new InterruptedIOException();
      }
    }

    void receive(InputStream in, int byteCount) throws IOException {
      assert (!Thread.holdsLock(SpdyStream.this));

      if (byteCount == 0) {
        return;
      }

      int pos;
      int limit;
      int firstNewByte;
      boolean finished;
      boolean flowControlError;
      synchronized (SpdyStream.this) {
        finished = this.finished;
        pos = this.pos;
        firstNewByte = this.limit;
        limit = this.limit;
        flowControlError = byteCount > buffer.length - available();
      }

      // If the peer sends more data than we can handle, discard it and close the connection.
      if (flowControlError) {
        Util.skipByReading(in, byteCount);
        closeLater(ErrorCode.FLOW_CONTROL_ERROR);
        return;
      }

      // Discard data received after the stream is finished. It's probably a benign race.
      if (finished) {
        Util.skipByReading(in, byteCount);
        return;
      }

      // Fill the buffer without holding any locks. First fill [limit..buffer.length) if that
      // won't overwrite unread data. Then fill [limit..pos). We can't hold a lock, otherwise
      // writes will be blocked until reads complete.
      if (pos < limit) {
        int firstCopyCount = Math.min(byteCount, buffer.length - limit);
        Util.readFully(in, buffer, limit, firstCopyCount);
        limit += firstCopyCount;
        byteCount -= firstCopyCount;
        if (limit == buffer.length) {
          limit = 0;
        }
      }
      if (byteCount > 0) {
        Util.readFully(in, buffer, limit, byteCount);
        limit += byteCount;
      }

      synchronized (SpdyStream.this) {
        // Update the new limit, and mark the position as readable if necessary.
        this.limit = limit;
        if (this.pos == -1) {
          this.pos = firstNewByte;
          SpdyStream.this.notifyAll();
        }
      }
    }

    @Override public void close() throws IOException {
      synchronized (SpdyStream.this) {
        closed = true;
        SpdyStream.this.notifyAll();
      }
      cancelStreamIfNecessary();
    }

    private void checkNotClosed() throws IOException {
      if (closed) {
        throw new IOException("stream closed");
      }
      if (errorCode != null) {
        throw new IOException("stream was reset: " + errorCode);
      }
    }
  }

  private void cancelStreamIfNecessary() throws IOException {
    assert (!Thread.holdsLock(SpdyStream.this));
    boolean open;
    boolean cancel;
    synchronized (this) {
      cancel = !in.finished && in.closed && (out.finished || out.closed);
      open = isOpen();
    }
    if (cancel) {
      // RST this stream to prevent additional data from being sent. This
      // is safe because the input stream is closed (we won't use any
      // further bytes) and the output stream is either finished or closed
      // (so RSTing both streams doesn't cause harm).
      SpdyStream.this.close(ErrorCode.CANCEL);
    } else if (!open) {
      connection.removeStream(id);
    }
  }

  /**
   * An output stream that writes outgoing data frames of a stream. This class
   * is not thread safe.
   */
  private final class SpdyDataOutputStream extends OutputStream {
    private final byte[] buffer = new byte[8192];
    private int pos = 0;

    /** True if the caller has closed this stream. */
    private boolean closed;

    /**
     * True if either side has cleanly shut down this stream. We shall send
     * no more bytes.
     */
    private boolean finished;

    /**
     * The total number of bytes written out to the peer, but not yet
     * acknowledged with an incoming {@code WINDOW_UPDATE} frame. Writes
     * block if they cause this to exceed the {@code WINDOW_SIZE}.
     */
    private int unacknowledgedBytes = 0;

    @Override public void write(int b) throws IOException {
      Util.writeSingleByte(this, b);
    }

    @Override public void write(byte[] bytes, int offset, int count) throws IOException {
      assert (!Thread.holdsLock(SpdyStream.this));
      checkOffsetAndCount(bytes.length, offset, count);
      checkNotClosed();

      while (count > 0) {
        if (pos == buffer.length) {
          writeFrame(false);
        }
        int bytesToCopy = Math.min(count, buffer.length - pos);
        System.arraycopy(bytes, offset, buffer, pos, bytesToCopy);
        pos += bytesToCopy;
        offset += bytesToCopy;
        count -= bytesToCopy;
      }
    }

    @Override public void flush() throws IOException {
      assert (!Thread.holdsLock(SpdyStream.this));
      checkNotClosed();
      if (pos > 0) {
        writeFrame(false);
        connection.flush();
      }
    }

    @Override public void close() throws IOException {
      assert (!Thread.holdsLock(SpdyStream.this));
      synchronized (SpdyStream.this) {
        if (closed) {
          return;
        }
        closed = true;
      }
      if (!out.finished) {
        writeFrame(true);
      }
      connection.flush();
      cancelStreamIfNecessary();
    }

    private void writeFrame(boolean outFinished) throws IOException {
      assert (!Thread.holdsLock(SpdyStream.this));

      int length = pos;
      synchronized (SpdyStream.this) {
        waitUntilWritable(length, outFinished);
        unacknowledgedBytes += length;
      }
      connection.writeData(id, outFinished, buffer, 0, pos);
      pos = 0;
    }

    /**
     * Returns once the peer is ready to receive {@code count} bytes.
     *
     * @throws IOException if the stream was finished or closed, or the
     * thread was interrupted.
     */
    private void waitUntilWritable(int count, boolean last) throws IOException {
      try {
        while (unacknowledgedBytes + count >= writeWindowSize) {
          SpdyStream.this.wait(); // Wait until we receive a WINDOW_UPDATE.

          // The stream may have been closed or reset while we were waiting!
          if (!last && closed) {
            throw new IOException("stream closed");
          } else if (finished) {
            throw new IOException("stream finished");
          } else if (errorCode != null) {
            throw new IOException("stream was reset: " + errorCode);
          }
        }
      } catch (InterruptedException e) {
        throw new InterruptedIOException();
      }
    }

    private void checkNotClosed() throws IOException {
      synchronized (SpdyStream.this) {
        if (closed) {
          throw new IOException("stream closed");
        } else if (finished) {
          throw new IOException("stream finished");
        } else if (errorCode != null) {
          throw new IOException("stream was reset: " + errorCode);
        }
      }
    }
  }
}


File: platforms/android/CordovaLib/src/com/squareup/okhttp/internal/spdy/Variant.java
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
package com.squareup.okhttp.internal.spdy;

import java.io.InputStream;
import java.io.OutputStream;

/** A version and dialect of the framed socket protocol. */
interface Variant {
  Variant SPDY3 = new Spdy3();
  Variant HTTP_20_DRAFT_06 = new Http20Draft06();

  /**
   * @param client true if this is the HTTP client's reader, reading frames from
   *     a peer SPDY or HTTP/2 server.
   */
  FrameReader newReader(InputStream in, boolean client);

  /**
   * @param client true if this is the HTTP client's writer, writing frames to a
   *     peer SPDY or HTTP/2 server.
   */
  FrameWriter newWriter(OutputStream out, boolean client);
}


File: platforms/android/CordovaLib/src/com/squareup/okhttp/internal/tls/DistinguishedNameParser.java
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

package com.squareup.okhttp.internal.tls;

import javax.security.auth.x500.X500Principal;

/**
 * A distinguished name (DN) parser. This parser only supports extracting a
 * string value from a DN. It doesn't support values in the hex-string style.
 */
final class DistinguishedNameParser {
  private final String dn;
  private final int length;
  private int pos;
  private int beg;
  private int end;

  /** Temporary variable to store positions of the currently parsed item. */
  private int cur;

  /** Distinguished name characters. */
  private char[] chars;

  public DistinguishedNameParser(X500Principal principal) {
    // RFC2253 is used to ensure we get attributes in the reverse
    // order of the underlying ASN.1 encoding, so that the most
    // significant values of repeated attributes occur first.
    this.dn = principal.getName(X500Principal.RFC2253);
    this.length = this.dn.length();
  }

  // gets next attribute type: (ALPHA 1*keychar) / oid
  private String nextAT() {
    // skip preceding space chars, they can present after
    // comma or semicolon (compatibility with RFC 1779)
    for (; pos < length && chars[pos] == ' '; pos++) {
    }
    if (pos == length) {
      return null; // reached the end of DN
    }

    // mark the beginning of attribute type
    beg = pos;

    // attribute type chars
    pos++;
    for (; pos < length && chars[pos] != '=' && chars[pos] != ' '; pos++) {
      // we don't follow exact BNF syntax here:
      // accept any char except space and '='
    }
    if (pos >= length) {
      throw new IllegalStateException("Unexpected end of DN: " + dn);
    }

    // mark the end of attribute type
    end = pos;

    // skip trailing space chars between attribute type and '='
    // (compatibility with RFC 1779)
    if (chars[pos] == ' ') {
      for (; pos < length && chars[pos] != '=' && chars[pos] == ' '; pos++) {
      }

      if (chars[pos] != '=' || pos == length) {
        throw new IllegalStateException("Unexpected end of DN: " + dn);
      }
    }

    pos++; //skip '=' char

    // skip space chars between '=' and attribute value
    // (compatibility with RFC 1779)
    for (; pos < length && chars[pos] == ' '; pos++) {
    }

    // in case of oid attribute type skip its prefix: "oid." or "OID."
    // (compatibility with RFC 1779)
    if ((end - beg > 4) && (chars[beg + 3] == '.')
        && (chars[beg] == 'O' || chars[beg] == 'o')
        && (chars[beg + 1] == 'I' || chars[beg + 1] == 'i')
        && (chars[beg + 2] == 'D' || chars[beg + 2] == 'd')) {
      beg += 4;
    }

    return new String(chars, beg, end - beg);
  }

  // gets quoted attribute value: QUOTATION *( quotechar / pair ) QUOTATION
  private String quotedAV() {
    pos++;
    beg = pos;
    end = beg;
    while (true) {

      if (pos == length) {
        throw new IllegalStateException("Unexpected end of DN: " + dn);
      }

      if (chars[pos] == '"') {
        // enclosing quotation was found
        pos++;
        break;
      } else if (chars[pos] == '\\') {
        chars[end] = getEscaped();
      } else {
        // shift char: required for string with escaped chars
        chars[end] = chars[pos];
      }
      pos++;
      end++;
    }

    // skip trailing space chars before comma or semicolon.
    // (compatibility with RFC 1779)
    for (; pos < length && chars[pos] == ' '; pos++) {
    }

    return new String(chars, beg, end - beg);
  }

  // gets hex string attribute value: "#" hexstring
  private String hexAV() {
    if (pos + 4 >= length) {
      // encoded byte array  must be not less then 4 c
      throw new IllegalStateException("Unexpected end of DN: " + dn);
    }

    beg = pos; // store '#' position
    pos++;
    while (true) {

      // check for end of attribute value
      // looks for space and component separators
      if (pos == length || chars[pos] == '+' || chars[pos] == ','
          || chars[pos] == ';') {
        end = pos;
        break;
      }

      if (chars[pos] == ' ') {
        end = pos;
        pos++;
        // skip trailing space chars before comma or semicolon.
        // (compatibility with RFC 1779)
        for (; pos < length && chars[pos] == ' '; pos++) {
        }
        break;
      } else if (chars[pos] >= 'A' && chars[pos] <= 'F') {
        chars[pos] += 32; //to low case
      }

      pos++;
    }

    // verify length of hex string
    // encoded byte array  must be not less then 4 and must be even number
    int hexLen = end - beg; // skip first '#' char
    if (hexLen < 5 || (hexLen & 1) == 0) {
      throw new IllegalStateException("Unexpected end of DN: " + dn);
    }

    // get byte encoding from string representation
    byte[] encoded = new byte[hexLen / 2];
    for (int i = 0, p = beg + 1; i < encoded.length; p += 2, i++) {
      encoded[i] = (byte) getByte(p);
    }

    return new String(chars, beg, hexLen);
  }

  // gets string attribute value: *( stringchar / pair )
  private String escapedAV() {
    beg = pos;
    end = pos;
    while (true) {
      if (pos >= length) {
        // the end of DN has been found
        return new String(chars, beg, end - beg);
      }

      switch (chars[pos]) {
        case '+':
        case ',':
        case ';':
          // separator char has been found
          return new String(chars, beg, end - beg);
        case '\\':
          // escaped char
          chars[end++] = getEscaped();
          pos++;
          break;
        case ' ':
          // need to figure out whether space defines
          // the end of attribute value or not
          cur = end;

          pos++;
          chars[end++] = ' ';

          for (; pos < length && chars[pos] == ' '; pos++) {
            chars[end++] = ' ';
          }
          if (pos == length || chars[pos] == ',' || chars[pos] == '+'
              || chars[pos] == ';') {
            // separator char or the end of DN has been found
            return new String(chars, beg, cur - beg);
          }
          break;
        default:
          chars[end++] = chars[pos];
          pos++;
      }
    }
  }

  // returns escaped char
  private char getEscaped() {
    pos++;
    if (pos == length) {
      throw new IllegalStateException("Unexpected end of DN: " + dn);
    }

    switch (chars[pos]) {
      case '"':
      case '\\':
      case ',':
      case '=':
      case '+':
      case '<':
      case '>':
      case '#':
      case ';':
      case ' ':
      case '*':
      case '%':
      case '_':
        //FIXME: escaping is allowed only for leading or trailing space char
        return chars[pos];
      default:
        // RFC doesn't explicitly say that escaped hex pair is
        // interpreted as UTF-8 char. It only contains an example of such DN.
        return getUTF8();
    }
  }

  // decodes UTF-8 char
  // see http://www.unicode.org for UTF-8 bit distribution table
  private char getUTF8() {
    int res = getByte(pos);
    pos++; //FIXME tmp

    if (res < 128) { // one byte: 0-7F
      return (char) res;
    } else if (res >= 192 && res <= 247) {

      int count;
      if (res <= 223) { // two bytes: C0-DF
        count = 1;
        res = res & 0x1F;
      } else if (res <= 239) { // three bytes: E0-EF
        count = 2;
        res = res & 0x0F;
      } else { // four bytes: F0-F7
        count = 3;
        res = res & 0x07;
      }

      int b;
      for (int i = 0; i < count; i++) {
        pos++;
        if (pos == length || chars[pos] != '\\') {
          return 0x3F; //FIXME failed to decode UTF-8 char - return '?'
        }
        pos++;

        b = getByte(pos);
        pos++; //FIXME tmp
        if ((b & 0xC0) != 0x80) {
          return 0x3F; //FIXME failed to decode UTF-8 char - return '?'
        }

        res = (res << 6) + (b & 0x3F);
      }
      return (char) res;
    } else {
      return 0x3F; //FIXME failed to decode UTF-8 char - return '?'
    }
  }

  // Returns byte representation of a char pair
  // The char pair is composed of DN char in
  // specified 'position' and the next char
  // According to BNF syntax:
  // hexchar    = DIGIT / "A" / "B" / "C" / "D" / "E" / "F"
  //                    / "a" / "b" / "c" / "d" / "e" / "f"
  private int getByte(int position) {
    if (position + 1 >= length) {
      throw new IllegalStateException("Malformed DN: " + dn);
    }

    int b1, b2;

    b1 = chars[position];
    if (b1 >= '0' && b1 <= '9') {
      b1 = b1 - '0';
    } else if (b1 >= 'a' && b1 <= 'f') {
      b1 = b1 - 87; // 87 = 'a' - 10
    } else if (b1 >= 'A' && b1 <= 'F') {
      b1 = b1 - 55; // 55 = 'A' - 10
    } else {
      throw new IllegalStateException("Malformed DN: " + dn);
    }

    b2 = chars[position + 1];
    if (b2 >= '0' && b2 <= '9') {
      b2 = b2 - '0';
    } else if (b2 >= 'a' && b2 <= 'f') {
      b2 = b2 - 87; // 87 = 'a' - 10
    } else if (b2 >= 'A' && b2 <= 'F') {
      b2 = b2 - 55; // 55 = 'A' - 10
    } else {
      throw new IllegalStateException("Malformed DN: " + dn);
    }

    return (b1 << 4) + b2;
  }

  /**
   * Parses the DN and returns the most significant attribute value
   * for an attribute type, or null if none found.
   *
   * @param attributeType attribute type to look for (e.g. "ca")
   */
  public String findMostSpecific(String attributeType) {
    // Initialize internal state.
    pos = 0;
    beg = 0;
    end = 0;
    cur = 0;
    chars = dn.toCharArray();

    String attType = nextAT();
    if (attType == null) {
      return null;
    }
    while (true) {
      String attValue = "";

      if (pos == length) {
        return null;
      }

      switch (chars[pos]) {
        case '"':
          attValue = quotedAV();
          break;
        case '#':
          attValue = hexAV();
          break;
        case '+':
        case ',':
        case ';': // compatibility with RFC 1779: semicolon can separate RDNs
          //empty attribute value
          break;
        default:
          attValue = escapedAV();
      }

      // Values are ordered from most specific to least specific
      // due to the RFC2253 formatting. So take the first match
      // we see.
      if (attributeType.equalsIgnoreCase(attType)) {
        return attValue;
      }

      if (pos >= length) {
        return null;
      }

      if (chars[pos] == ',' || chars[pos] == ';') {
      } else if (chars[pos] != '+') {
        throw new IllegalStateException("Malformed DN: " + dn);
      }

      pos++;
      attType = nextAT();
      if (attType == null) {
        throw new IllegalStateException("Malformed DN: " + dn);
      }
    }
  }
}


File: platforms/android/CordovaLib/src/com/squareup/okhttp/internal/tls/OkHostnameVerifier.java
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

package com.squareup.okhttp.internal.tls;

import java.security.cert.Certificate;
import java.security.cert.CertificateParsingException;
import java.security.cert.X509Certificate;
import java.util.ArrayList;
import java.util.Collection;
import java.util.Collections;
import java.util.List;
import java.util.Locale;
import java.util.regex.Pattern;
import javax.net.ssl.HostnameVerifier;
import javax.net.ssl.SSLException;
import javax.net.ssl.SSLSession;
import javax.security.auth.x500.X500Principal;

/**
 * A HostnameVerifier consistent with <a
 * href="http://www.ietf.org/rfc/rfc2818.txt">RFC 2818</a>.
 */
public final class OkHostnameVerifier implements HostnameVerifier {
  public static final OkHostnameVerifier INSTANCE = new OkHostnameVerifier();

  /**
   * Quick and dirty pattern to differentiate IP addresses from hostnames. This
   * is an approximation of Android's private InetAddress#isNumeric API.
   *
   * <p>This matches IPv6 addresses as a hex string containing at least one
   * colon, and possibly including dots after the first colon. It matches IPv4
   * addresses as strings containing only decimal digits and dots. This pattern
   * matches strings like "a:.23" and "54" that are neither IP addresses nor
   * hostnames; they will be verified as IP addresses (which is a more strict
   * verification).
   */
  private static final Pattern VERIFY_AS_IP_ADDRESS = Pattern.compile(
      "([0-9a-fA-F]*:[0-9a-fA-F:.]*)|([\\d.]+)");

  private static final int ALT_DNS_NAME = 2;
  private static final int ALT_IPA_NAME = 7;

  private OkHostnameVerifier() {
  }

  public boolean verify(String host, SSLSession session) {
    try {
      Certificate[] certificates = session.getPeerCertificates();
      return verify(host, (X509Certificate) certificates[0]);
    } catch (SSLException e) {
      return false;
    }
  }

  public boolean verify(String host, X509Certificate certificate) {
    return verifyAsIpAddress(host)
        ? verifyIpAddress(host, certificate)
        : verifyHostName(host, certificate);
  }

  static boolean verifyAsIpAddress(String host) {
    return VERIFY_AS_IP_ADDRESS.matcher(host).matches();
  }

  /**
   * Returns true if {@code certificate} matches {@code ipAddress}.
   */
  private boolean verifyIpAddress(String ipAddress, X509Certificate certificate) {
    for (String altName : getSubjectAltNames(certificate, ALT_IPA_NAME)) {
      if (ipAddress.equalsIgnoreCase(altName)) {
        return true;
      }
    }
    return false;
  }

  /**
   * Returns true if {@code certificate} matches {@code hostName}.
   */
  private boolean verifyHostName(String hostName, X509Certificate certificate) {
    hostName = hostName.toLowerCase(Locale.US);
    boolean hasDns = false;
    for (String altName : getSubjectAltNames(certificate, ALT_DNS_NAME)) {
      hasDns = true;
      if (verifyHostName(hostName, altName)) {
        return true;
      }
    }

    if (!hasDns) {
      X500Principal principal = certificate.getSubjectX500Principal();
      // RFC 2818 advises using the most specific name for matching.
      String cn = new DistinguishedNameParser(principal).findMostSpecific("cn");
      if (cn != null) {
        return verifyHostName(hostName, cn);
      }
    }

    return false;
  }

  private List<String> getSubjectAltNames(X509Certificate certificate, int type) {
    List<String> result = new ArrayList<String>();
    try {
      Collection<?> subjectAltNames = certificate.getSubjectAlternativeNames();
      if (subjectAltNames == null) {
        return Collections.emptyList();
      }
      for (Object subjectAltName : subjectAltNames) {
        List<?> entry = (List<?>) subjectAltName;
        if (entry == null || entry.size() < 2) {
          continue;
        }
        Integer altNameType = (Integer) entry.get(0);
        if (altNameType == null) {
          continue;
        }
        if (altNameType == type) {
          String altName = (String) entry.get(1);
          if (altName != null) {
            result.add(altName);
          }
        }
      }
      return result;
    } catch (CertificateParsingException e) {
      return Collections.emptyList();
    }
  }

  /**
   * Returns true if {@code hostName} matches the name or pattern {@code cn}.
   *
   * @param hostName lowercase host name.
   * @param cn certificate host name. May include wildcards like
   *     {@code *.android.com}.
   */
  public boolean verifyHostName(String hostName, String cn) {
    // Check length == 0 instead of .isEmpty() to support Java 5.
    if (hostName == null || hostName.length() == 0 || cn == null || cn.length() == 0) {
      return false;
    }

    cn = cn.toLowerCase(Locale.US);

    if (!cn.contains("*")) {
      return hostName.equals(cn);
    }

    if (cn.startsWith("*.") && hostName.regionMatches(0, cn, 2, cn.length() - 2)) {
      return true; // "*.foo.com" matches "foo.com"
    }

    int asterisk = cn.indexOf('*');
    int dot = cn.indexOf('.');
    if (asterisk > dot) {
      return false; // malformed; wildcard must be in the first part of the cn
    }

    if (!hostName.regionMatches(0, cn, 0, asterisk)) {
      return false; // prefix before '*' doesn't match
    }

    int suffixLength = cn.length() - (asterisk + 1);
    int suffixStart = hostName.length() - suffixLength;
    if (hostName.indexOf('.', asterisk) < suffixStart) {
      // TODO: remove workaround for *.clients.google.com http://b/5426333
      if (!hostName.endsWith(".clients.google.com")) {
        return false; // wildcard '*' can't match a '.'
      }
    }

    if (!hostName.regionMatches(suffixStart, cn, asterisk + 1, suffixLength)) {
      return false; // suffix after '*' doesn't match
    }

    return true;
  }
}


File: platforms/android/CordovaLib/src/org/apache/cordova/App.java
/*
       Licensed to the Apache Software Foundation (ASF) under one
       or more contributor license agreements.  See the NOTICE file
       distributed with this work for additional information
       regarding copyright ownership.  The ASF licenses this file
       to you under the Apache License, Version 2.0 (the
       "License"); you may not use this file except in compliance
       with the License.  You may obtain a copy of the License at

         http://www.apache.org/licenses/LICENSE-2.0

       Unless required by applicable law or agreed to in writing,
       software distributed under the License is distributed on an
       "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY
       KIND, either express or implied.  See the License for the
       specific language governing permissions and limitations
       under the License.
*/

package org.apache.cordova;

import org.apache.cordova.CallbackContext;
import org.apache.cordova.CordovaPlugin;
import org.apache.cordova.LOG;
import org.apache.cordova.PluginResult;
import org.json.JSONArray;
import org.json.JSONException;
import org.json.JSONObject;

import android.content.BroadcastReceiver;
import android.content.Context;
import android.content.Intent;
import android.content.IntentFilter;
import android.telephony.TelephonyManager;
import android.view.KeyEvent;

import java.util.HashMap;

/**
 * This class exposes methods in Cordova that can be called from JavaScript.
 */
public class App extends CordovaPlugin {

    public static final String PLUGIN_NAME = "App";
    protected static final String TAG = "CordovaApp";
    private BroadcastReceiver telephonyReceiver;
    private CallbackContext messageChannel;

    /**
     * Send an event to be fired on the Javascript side.
     *
     * @param action The name of the event to be fired
     */
    public void fireJavascriptEvent(String action) {
        sendEventMessage(action);
    }

    /**
     * Sets the context of the Command. This can then be used to do things like
     * get file paths associated with the Activity.
     */
    @Override
    public void pluginInitialize() {
        this.initTelephonyReceiver();
    }

    /**
     * Executes the request and returns PluginResult.
     *
     * @param action            The action to execute.
     * @param args              JSONArry of arguments for the plugin.
     * @param callbackContext   The callback context from which we were invoked.
     * @return                  A PluginResult object with a status and message.
     */
    public boolean execute(String action, JSONArray args, CallbackContext callbackContext) throws JSONException {
        PluginResult.Status status = PluginResult.Status.OK;
        String result = "";

        try {
            if (action.equals("clearCache")) {
                this.clearCache();
            }
            else if (action.equals("show")) {
                // This gets called from JavaScript onCordovaReady to show the webview.
                // I recommend we change the name of the Message as spinner/stop is not
                // indicative of what this actually does (shows the webview).
                cordova.getActivity().runOnUiThread(new Runnable() {
                    public void run() {
                        webView.postMessage("spinner", "stop");
                    }
                });
            }
            else if (action.equals("loadUrl")) {
                this.loadUrl(args.getString(0), args.optJSONObject(1));
            }
            else if (action.equals("cancelLoadUrl")) {
                //this.cancelLoadUrl();
            }
            else if (action.equals("clearHistory")) {
                this.clearHistory();
            }
            else if (action.equals("backHistory")) {
                this.backHistory();
            }
            else if (action.equals("overrideButton")) {
                this.overrideButton(args.getString(0), args.getBoolean(1));
            }
            else if (action.equals("overrideBackbutton")) {
                this.overrideBackbutton(args.getBoolean(0));
            }
            else if (action.equals("exitApp")) {
                this.exitApp();
            }
			else if (action.equals("messageChannel")) {
                messageChannel = callbackContext;
                return true;
            }

            callbackContext.sendPluginResult(new PluginResult(status, result));
            return true;
        } catch (JSONException e) {
            callbackContext.sendPluginResult(new PluginResult(PluginResult.Status.JSON_EXCEPTION));
            return false;
        }
    }

    //--------------------------------------------------------------------------
    // LOCAL METHODS
    //--------------------------------------------------------------------------

    /**
     * Clear the resource cache.
     */
    public void clearCache() {
        cordova.getActivity().runOnUiThread(new Runnable() {
            public void run() {
                webView.clearCache(true);
            }
        });
    }

    /**
     * Load the url into the webview.
     *
     * @param url
     * @param props			Properties that can be passed in to the Cordova activity (i.e. loadingDialog, wait, ...)
     * @throws JSONException
     */
    public void loadUrl(String url, JSONObject props) throws JSONException {
        LOG.d("App", "App.loadUrl("+url+","+props+")");
        int wait = 0;
        boolean openExternal = false;
        boolean clearHistory = false;

        // If there are properties, then set them on the Activity
        HashMap<String, Object> params = new HashMap<String, Object>();
        if (props != null) {
            JSONArray keys = props.names();
            for (int i = 0; i < keys.length(); i++) {
                String key = keys.getString(i);
                if (key.equals("wait")) {
                    wait = props.getInt(key);
                }
                else if (key.equalsIgnoreCase("openexternal")) {
                    openExternal = props.getBoolean(key);
                }
                else if (key.equalsIgnoreCase("clearhistory")) {
                    clearHistory = props.getBoolean(key);
                }
                else {
                    Object value = props.get(key);
                    if (value == null) {

                    }
                    else if (value.getClass().equals(String.class)) {
                        params.put(key, (String)value);
                    }
                    else if (value.getClass().equals(Boolean.class)) {
                        params.put(key, (Boolean)value);
                    }
                    else if (value.getClass().equals(Integer.class)) {
                        params.put(key, (Integer)value);
                    }
                }
            }
        }

        // If wait property, then delay loading

        if (wait > 0) {
            try {
                synchronized(this) {
                    this.wait(wait);
                }
            } catch (InterruptedException e) {
                e.printStackTrace();
            }
        }
        this.webView.showWebPage(url, openExternal, clearHistory, params);
    }

    /**
     * Clear page history for the app.
     */
    public void clearHistory() {
        cordova.getActivity().runOnUiThread(new Runnable() {
            public void run() {
                webView.clearHistory();
            }
        });
    }

    /**
     * Go to previous page displayed.
     * This is the same as pressing the backbutton on Android device.
     */
    public void backHistory() {
        cordova.getActivity().runOnUiThread(new Runnable() {
            public void run() {
                webView.backHistory();
            }
        });
    }

    /**
     * Override the default behavior of the Android back button.
     * If overridden, when the back button is pressed, the "backKeyDown" JavaScript event will be fired.
     *
     * @param override		T=override, F=cancel override
     */
    public void overrideBackbutton(boolean override) {
        LOG.i("App", "WARNING: Back Button Default Behavior will be overridden.  The backbutton event will be fired!");
        webView.setButtonPlumbedToJs(KeyEvent.KEYCODE_BACK, override);
    }

    /**
     * Override the default behavior of the Android volume buttons.
     * If overridden, when the volume button is pressed, the "volume[up|down]button" JavaScript event will be fired.
     *
     * @param button        volumeup, volumedown
     * @param override      T=override, F=cancel override
     */
    public void overrideButton(String button, boolean override) {
        LOG.i("App", "WARNING: Volume Button Default Behavior will be overridden.  The volume event will be fired!");
        if (button.equals("volumeup")) {
            webView.setButtonPlumbedToJs(KeyEvent.KEYCODE_VOLUME_UP, override);
        }
        else if (button.equals("volumedown")) {
            webView.setButtonPlumbedToJs(KeyEvent.KEYCODE_VOLUME_DOWN, override);
        }
    }

    /**
     * Return whether the Android back button is overridden by the user.
     *
     * @return boolean
     */
    public boolean isBackbuttonOverridden() {
        return webView.isButtonPlumbedToJs(KeyEvent.KEYCODE_BACK);
    }

    /**
     * Exit the Android application.
     */
    public void exitApp() {
        this.webView.postMessage("exit", null);
    }


    /**
     * Listen for telephony events: RINGING, OFFHOOK and IDLE
     * Send these events to all plugins using
     *      CordovaActivity.onMessage("telephone", "ringing" | "offhook" | "idle")
     */
    private void initTelephonyReceiver() {
        IntentFilter intentFilter = new IntentFilter();
        intentFilter.addAction(TelephonyManager.ACTION_PHONE_STATE_CHANGED);
        //final CordovaInterface mycordova = this.cordova;
        this.telephonyReceiver = new BroadcastReceiver() {

            @Override
            public void onReceive(Context context, Intent intent) {

                // If state has changed
                if ((intent != null) && intent.getAction().equals(TelephonyManager.ACTION_PHONE_STATE_CHANGED)) {
                    if (intent.hasExtra(TelephonyManager.EXTRA_STATE)) {
                        String extraData = intent.getStringExtra(TelephonyManager.EXTRA_STATE);
                        if (extraData.equals(TelephonyManager.EXTRA_STATE_RINGING)) {
                            LOG.i(TAG, "Telephone RINGING");
                            webView.postMessage("telephone", "ringing");
                        }
                        else if (extraData.equals(TelephonyManager.EXTRA_STATE_OFFHOOK)) {
                            LOG.i(TAG, "Telephone OFFHOOK");
                            webView.postMessage("telephone", "offhook");
                        }
                        else if (extraData.equals(TelephonyManager.EXTRA_STATE_IDLE)) {
                            LOG.i(TAG, "Telephone IDLE");
                            webView.postMessage("telephone", "idle");
                        }
                    }
                }
            }
        };

        // Register the receiver
        webView.getContext().registerReceiver(this.telephonyReceiver, intentFilter);
    }

    private void sendEventMessage(String action) {
        JSONObject obj = new JSONObject();
        try {
            obj.put("action", action);
        } catch (JSONException e) {
            LOG.e(TAG, "Failed to create event message", e);
        }
        PluginResult pluginResult = new PluginResult(PluginResult.Status.OK, obj);
        pluginResult.setKeepCallback(true);
        if (messageChannel != null) {
            messageChannel.sendPluginResult(pluginResult);
        }
    }

    /*
     * Unregister the receiver
     *
     */
    public void onDestroy()
    {
        webView.getContext().unregisterReceiver(this.telephonyReceiver);
    }
}


File: platforms/android/CordovaLib/src/org/apache/cordova/Config.java
/*
       Licensed to the Apache Software Foundation (ASF) under one
       or more contributor license agreements.  See the NOTICE file
       distributed with this work for additional information
       regarding copyright ownership.  The ASF licenses this file
       to you under the Apache License, Version 2.0 (the
       "License"); you may not use this file except in compliance
       with the License.  You may obtain a copy of the License at

         http://www.apache.org/licenses/LICENSE-2.0

       Unless required by applicable law or agreed to in writing,
       software distributed under the License is distributed on an
       "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY
       KIND, either express or implied.  See the License for the
       specific language governing permissions and limitations
       under the License.
*/

package org.apache.cordova;

import java.util.List;

import android.app.Activity;
import android.util.Log;

@Deprecated // Use Whitelist, CordovaPrefences, etc. directly.
public class Config {
    private static final String TAG = "Config";

    static ConfigXmlParser parser;

    private Config() {
    }

    public static void init(Activity action) {
        parser = new ConfigXmlParser();
        parser.parse(action);
        parser.getPreferences().setPreferencesBundle(action.getIntent().getExtras());
        parser.getPreferences().copyIntoIntentExtras(action);
    }

    // Intended to be used for testing only; creates an empty configuration.
    public static void init() {
        if (parser == null) {
            parser = new ConfigXmlParser();
        }
    }
    
    /**
     * Add entry to approved list of URLs (whitelist)
     *
     * @param origin        URL regular expression to allow
     * @param subdomains    T=include all subdomains under origin
     */
    public static void addWhiteListEntry(String origin, boolean subdomains) {
        if (parser == null) {
            Log.e(TAG, "Config was not initialised. Did you forget to Config.init(this)?");
            return;
        }
        parser.getInternalWhitelist().addWhiteListEntry(origin, subdomains);
    }

    /**
     * Determine if URL is in approved list of URLs to load.
     *
     * @param url
     * @return true if whitelisted
     */
    public static boolean isUrlWhiteListed(String url) {
        if (parser == null) {
            Log.e(TAG, "Config was not initialised. Did you forget to Config.init(this)?");
            return false;
        }
        return parser.getInternalWhitelist().isUrlWhiteListed(url);
    }

    /**
     * Determine if URL is in approved list of URLs to launch external applications.
     *
     * @param url
     * @return true if whitelisted
     */
    public static boolean isUrlExternallyWhiteListed(String url) {
        if (parser == null) {
            Log.e(TAG, "Config was not initialised. Did you forget to Config.init(this)?");
            return false;
        }
        return parser.getExternalWhitelist().isUrlWhiteListed(url);
    }

    public static String getStartUrl() {
        if (parser == null) {
            return "file:///android_asset/www/index.html";
        }
        return parser.getLaunchUrl();
    }

    public static String getErrorUrl() {
        return parser.getPreferences().getString("errorurl", null);
    }

    public static Whitelist getWhitelist() {
        return parser.getInternalWhitelist();
    }

    public static Whitelist getExternalWhitelist() {
        return parser.getExternalWhitelist();
    }

    public static List<PluginEntry> getPluginEntries() {
        return parser.getPluginEntries();
    }
    
    public static CordovaPreferences getPreferences() {
        return parser.getPreferences();
    }

    public static boolean isInitialized() {
        return parser != null;
    }
}


File: platforms/android/CordovaLib/src/org/apache/cordova/ConfigXmlParser.java
/*
       Licensed to the Apache Software Foundation (ASF) under one
       or more contributor license agreements.  See the NOTICE file
       distributed with this work for additional information
       regarding copyright ownership.  The ASF licenses this file
       to you under the Apache License, Version 2.0 (the
       "License"); you may not use this file except in compliance
       with the License.  You may obtain a copy of the License at

         http://www.apache.org/licenses/LICENSE-2.0

       Unless required by applicable law or agreed to in writing,
       software distributed under the License is distributed on an
       "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY
       KIND, either express or implied.  See the License for the
       specific language governing permissions and limitations
       under the License.
*/

package org.apache.cordova;

import java.io.IOException;
import java.util.ArrayList;
import java.util.Locale;
import java.util.regex.Matcher;
import java.util.regex.Pattern;

import org.apache.cordova.LOG;
import org.xmlpull.v1.XmlPullParserException;

import android.app.Activity;
import android.content.res.XmlResourceParser;
import android.util.Log;

public class ConfigXmlParser {
    private static String TAG = "ConfigXmlParser";

    private String launchUrl = "file:///android_asset/www/index.html";
    private CordovaPreferences prefs = new CordovaPreferences();
    private Whitelist internalWhitelist = new Whitelist();
    private Whitelist externalWhitelist = new Whitelist();
    private ArrayList<PluginEntry> pluginEntries = new ArrayList<PluginEntry>(20);

    public Whitelist getInternalWhitelist() {
        return internalWhitelist;
    }

    public Whitelist getExternalWhitelist() {
        return externalWhitelist;
    }

    public CordovaPreferences getPreferences() {
        return prefs;
    }

    public ArrayList<PluginEntry> getPluginEntries() {
        return pluginEntries;
    }

    public String getLaunchUrl() {
        return launchUrl;
    }
    
    public void parse(Activity action) {
        // First checking the class namespace for config.xml
        int id = action.getResources().getIdentifier("config", "xml", action.getClass().getPackage().getName());
        if (id == 0) {
            // If we couldn't find config.xml there, we'll look in the namespace from AndroidManifest.xml
            id = action.getResources().getIdentifier("config", "xml", action.getPackageName());
            if (id == 0) {
                LOG.e(TAG, "res/xml/config.xml is missing!");
                return;
            }
        }
        parse(action.getResources().getXml(id));
    }

    public void parse(XmlResourceParser xml) {
        int eventType = -1;
        String service = "", pluginClass = "", paramType = "";
        boolean onload = false;
        boolean insideFeature = false;
        ArrayList<String> urlMap = null;

        // Add implicitly allowed URLs
        internalWhitelist.addWhiteListEntry("file:///*", false);
        internalWhitelist.addWhiteListEntry("content:///*", false);
        internalWhitelist.addWhiteListEntry("data:*", false);

        while (eventType != XmlResourceParser.END_DOCUMENT) {
            if (eventType == XmlResourceParser.START_TAG) {
                String strNode = xml.getName();
                if (strNode.equals("url-filter")) {
                    Log.w(TAG, "Plugin " + service + " is using deprecated tag <url-filter>");
                    if (urlMap == null) {
                        urlMap = new ArrayList<String>(2);
                    }
                    urlMap.add(xml.getAttributeValue(null, "value"));
                } else if (strNode.equals("feature")) {
                    //Check for supported feature sets  aka. plugins (Accelerometer, Geolocation, etc)
                    //Set the bit for reading params
                    insideFeature = true;
                    service = xml.getAttributeValue(null, "name");
                }
                else if (insideFeature && strNode.equals("param")) {
                    paramType = xml.getAttributeValue(null, "name");
                    if (paramType.equals("service")) // check if it is using the older service param
                        service = xml.getAttributeValue(null, "value");
                    else if (paramType.equals("package") || paramType.equals("android-package"))
                        pluginClass = xml.getAttributeValue(null,"value");
                    else if (paramType.equals("onload"))
                        onload = "true".equals(xml.getAttributeValue(null, "value"));
                }
                else if (strNode.equals("access")) {
                    String origin = xml.getAttributeValue(null, "origin");
                    String subdomains = xml.getAttributeValue(null, "subdomains");
                    boolean external = (xml.getAttributeValue(null, "launch-external") != null);
                    if (origin != null) {
                        if (external) {
                            externalWhitelist.addWhiteListEntry(origin, (subdomains != null) && (subdomains.compareToIgnoreCase("true") == 0));
                        } else {
                            if ("*".equals(origin)) {
                                // Special-case * origin to mean http and https when used for internal
                                // whitelist. This prevents external urls like sms: and geo: from being
                                // handled internally.
                                internalWhitelist.addWhiteListEntry("http://*/*", false);
                                internalWhitelist.addWhiteListEntry("https://*/*", false);
                            } else {
                                internalWhitelist.addWhiteListEntry(origin, (subdomains != null) && (subdomains.compareToIgnoreCase("true") == 0));
                            }
                        }
                    }
                }
                else if (strNode.equals("preference")) {
                    String name = xml.getAttributeValue(null, "name").toLowerCase(Locale.ENGLISH);
                    String value = xml.getAttributeValue(null, "value");
                    prefs.set(name, value);
                }
                else if (strNode.equals("content")) {
                    String src = xml.getAttributeValue(null, "src");
                    if (src != null) {
                        setStartUrl(src);
                    }
                }
            }
            else if (eventType == XmlResourceParser.END_TAG)
            {
                String strNode = xml.getName();
                if (strNode.equals("feature")) {
                    pluginEntries.add(new PluginEntry(service, pluginClass, onload, urlMap));

                    service = "";
                    pluginClass = "";
                    insideFeature = false;
                    onload = false;
                    urlMap = null;
                }
            }
            try {
                eventType = xml.next();
            } catch (XmlPullParserException e) {
                e.printStackTrace();
            } catch (IOException e) {
                e.printStackTrace();
            }
        }
    }

    private void setStartUrl(String src) {
        Pattern schemeRegex = Pattern.compile("^[a-z-]+://");
        Matcher matcher = schemeRegex.matcher(src);
        if (matcher.find()) {
            launchUrl = src;
        } else {
            if (src.charAt(0) == '/') {
                src = src.substring(1);
            }
            launchUrl = "file:///android_asset/www/" + src;
        }
    }
}


File: platforms/android/CordovaLib/src/org/apache/cordova/CordovaActivity.java
/*
       Licensed to the Apache Software Foundation (ASF) under one
       or more contributor license agreements.  See the NOTICE file
       distributed with this work for additional information
       regarding copyright ownership.  The ASF licenses this file
       to you under the Apache License, Version 2.0 (the
       "License"); you may not use this file except in compliance
       with the License.  You may obtain a copy of the License at

         http://www.apache.org/licenses/LICENSE-2.0

       Unless required by applicable law or agreed to in writing,
       software distributed under the License is distributed on an
       "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY
       KIND, either express or implied.  See the License for the
       specific language governing permissions and limitations
       under the License.
*/
package org.apache.cordova;

import java.util.ArrayList;
import java.util.HashMap;
import java.util.Locale;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;

import org.json.JSONArray;
import org.json.JSONException;
import org.json.JSONObject;

import android.annotation.SuppressLint;
import android.app.Activity;
import android.app.AlertDialog;
import android.content.Context;
import android.content.DialogInterface;
import android.content.Intent;
import android.graphics.Color;
import android.media.AudioManager;
import android.os.Bundle;
import android.util.Log;
import android.view.Display;
import android.view.KeyEvent;
import android.view.Menu;
import android.view.MenuItem;
import android.view.View;
import android.view.ViewGroup;
import android.view.ViewParent;
import android.view.Window;
import android.view.WindowManager;
import android.webkit.WebViewClient;
import android.widget.LinearLayout;

/**
 * This class is the main Android activity that represents the Cordova
 * application. It should be extended by the user to load the specific
 * html file that contains the application.
 *
 * As an example:
 * 
 * <pre>
 *     package org.apache.cordova.examples;
 *
 *     import android.os.Bundle;
 *     import org.apache.cordova.*;
 *
 *     public class Example extends CordovaActivity {
 *       &#64;Override
 *       public void onCreate(Bundle savedInstanceState) {
 *         super.onCreate(savedInstanceState);
 *         super.init();
 *         // Load your application
 *         loadUrl(launchUrl);
 *       }
 *     }
 * </pre>
 * 
 * Cordova xml configuration: Cordova uses a configuration file at 
 * res/xml/config.xml to specify its settings. See "The config.xml File"
 * guide in cordova-docs at http://cordova.apache.org/docs for the documentation
 * for the configuration. The use of the set*Property() methods is
 * deprecated in favor of the config.xml file.
 *
 */
public class CordovaActivity extends Activity implements CordovaInterface {
    public static String TAG = "CordovaActivity";

    // The webview for our app
    protected CordovaWebView appView;

    @Deprecated // unused.
    protected CordovaWebViewClient webViewClient;

    @Deprecated // Will be removed. Use findViewById() to retrieve views.
    protected LinearLayout root;

    private final ExecutorService threadPool = Executors.newCachedThreadPool();

    private static int ACTIVITY_STARTING = 0;
    private static int ACTIVITY_RUNNING = 1;
    private static int ACTIVITY_EXITING = 2;
    private int activityState = 0;  // 0=starting, 1=running (after 1st resume), 2=shutting down

    // Plugin to call when activity result is received
    protected int activityResultRequestCode;
    protected CordovaPlugin activityResultCallback;
    protected boolean activityResultKeepRunning;

    /*
     * The variables below are used to cache some of the activity properties.
     */

    // Draw a splash screen using an image located in the drawable resource directory.
    @Deprecated // Use "SplashScreen" preference instead.
    protected int splashscreen = 0;
    @Deprecated // Use "SplashScreenDelay" preference instead.
    protected int splashscreenTime = -1;

    // LoadUrl timeout value in msec (default of 20 sec)
    protected int loadUrlTimeoutValue = 20000;

    // Keep app running when pause is received. (default = true)
    // If true, then the JavaScript and native code continue to run in the background
    // when another application (activity) is started.
    protected boolean keepRunning = true;

    private String initCallbackClass;

    // Read from config.xml:
    protected CordovaPreferences preferences;
    protected Whitelist internalWhitelist;
    protected Whitelist externalWhitelist;
    protected String launchUrl;
    protected ArrayList<PluginEntry> pluginEntries;

    /**
    * Sets the authentication token.
    *
    * @param authenticationToken
    * @param host
    * @param realm
    */
    public void setAuthenticationToken(AuthenticationToken authenticationToken, String host, String realm) {
        if (this.appView != null && this.appView.viewClient != null) {
            this.appView.viewClient.setAuthenticationToken(authenticationToken, host, realm);
        }
    }

    /**
     * Removes the authentication token.
     *
     * @param host
     * @param realm
     *
     * @return the authentication token or null if did not exist
     */
    public AuthenticationToken removeAuthenticationToken(String host, String realm) {
        if (this.appView != null && this.appView.viewClient != null) {
            return this.appView.viewClient.removeAuthenticationToken(host, realm);
        }
        return null;
    }

    /**
     * Gets the authentication token.
     *
     * In order it tries:
     * 1- host + realm
     * 2- host
     * 3- realm
     * 4- no host, no realm
     *
     * @param host
     * @param realm
     *
     * @return the authentication token
     */
    public AuthenticationToken getAuthenticationToken(String host, String realm) {
        if (this.appView != null && this.appView.viewClient != null) {
            return this.appView.viewClient.getAuthenticationToken(host, realm);
        }
        return null;
    }

    /**
     * Clear all authentication tokens.
     */
    public void clearAuthenticationTokens() {
        if (this.appView != null && this.appView.viewClient != null) {
            this.appView.viewClient.clearAuthenticationTokens();
        }
    }

    /**
     * Called when the activity is first created.
     */
    @Override
    public void onCreate(Bundle savedInstanceState) {
        LOG.i(TAG, "Apache Cordova native platform version " + CordovaWebView.CORDOVA_VERSION + " is starting");
        LOG.d(TAG, "CordovaActivity.onCreate()");

        // need to activate preferences before super.onCreate to avoid "requestFeature() must be called before adding content" exception
        loadConfig();
        if(!preferences.getBoolean("ShowTitle", false))
        {
            getWindow().requestFeature(Window.FEATURE_NO_TITLE);
        }
        
        if(preferences.getBoolean("SetFullscreen", false))
        {
            Log.d(TAG, "The SetFullscreen configuration is deprecated in favor of Fullscreen, and will be removed in a future version.");
            getWindow().setFlags(WindowManager.LayoutParams.FLAG_FULLSCREEN,
                    WindowManager.LayoutParams.FLAG_FULLSCREEN);
        } else if (preferences.getBoolean("Fullscreen", false)) {
            getWindow().setFlags(WindowManager.LayoutParams.FLAG_FULLSCREEN,
                    WindowManager.LayoutParams.FLAG_FULLSCREEN);
        } else {
            getWindow().setFlags(WindowManager.LayoutParams.FLAG_FORCE_NOT_FULLSCREEN,
                    WindowManager.LayoutParams.FLAG_FORCE_NOT_FULLSCREEN);
        }

        super.onCreate(savedInstanceState);

        if(savedInstanceState != null)
        {
            initCallbackClass = savedInstanceState.getString("callbackClass");
        }
    }

    @SuppressWarnings("deprecation")
    protected void loadConfig() {
        ConfigXmlParser parser = new ConfigXmlParser();
        parser.parse(this);
        preferences = parser.getPreferences();
        preferences.setPreferencesBundle(getIntent().getExtras());
        preferences.copyIntoIntentExtras(this);
        internalWhitelist = parser.getInternalWhitelist();
        externalWhitelist = parser.getExternalWhitelist();
        launchUrl = parser.getLaunchUrl();
        pluginEntries = parser.getPluginEntries();
        Config.parser = parser;
    }

    @SuppressWarnings("deprecation")
    protected void createViews() {
        // This builds the view.  We could probably get away with NOT having a LinearLayout, but I like having a bucket!

        LOG.d(TAG, "CordovaActivity.createViews()");

        Display display = getWindowManager().getDefaultDisplay();
        int width = display.getWidth();
        int height = display.getHeight();

        root = new LinearLayoutSoftKeyboardDetect(this, width, height);
        root.setOrientation(LinearLayout.VERTICAL);
        root.setLayoutParams(new LinearLayout.LayoutParams(ViewGroup.LayoutParams.MATCH_PARENT,
                ViewGroup.LayoutParams.MATCH_PARENT, 0.0F));

        appView.setId(100);
        appView.setLayoutParams(new LinearLayout.LayoutParams(
                ViewGroup.LayoutParams.MATCH_PARENT,
                ViewGroup.LayoutParams.MATCH_PARENT,
                1.0F));

        // need to remove appView from any existing parent before invoking root.addView(appView)
        ViewParent parent = appView.getParent();
        if ((parent != null) && (parent != root)) {
            LOG.d(TAG, "removing appView from existing parent");
            ViewGroup parentGroup = (ViewGroup) parent;
            parentGroup.removeView(appView);
        }
        root.addView((View) appView);
        setContentView(root);

        int backgroundColor = preferences.getInteger("BackgroundColor", Color.BLACK);
        root.setBackgroundColor(backgroundColor);
    }

    /**
     * Get the Android activity.
     */
    @Override public Activity getActivity() {
        return this;
    }

    /**
     * Construct the default web view object.
     *
     * This is intended to be overridable by subclasses of CordovaIntent which
     * require a more specialized web view.
     */
    protected CordovaWebView makeWebView() {
        return new CordovaWebView(CordovaActivity.this);
    }

    /**
     * Construct the client for the default web view object.
     *
     * This is intended to be overridable by subclasses of CordovaIntent which
     * require a more specialized web view.
     *
     * @param webView the default constructed web view object
     */
    protected CordovaWebViewClient makeWebViewClient(CordovaWebView webView) {
        return webView.makeWebViewClient(this);
    }

    /**
     * Construct the chrome client for the default web view object.
     *
     * This is intended to be overridable by subclasses of CordovaIntent which
     * require a more specialized web view.
     *
     * @param webView the default constructed web view object
     */
    protected CordovaChromeClient makeChromeClient(CordovaWebView webView) {
        return webView.makeWebChromeClient(this);
    }

    public void init() {
        this.init(appView, null, null);
    }

    @SuppressLint("NewApi")
    @Deprecated // Call init() instead and override makeWebView() to customize.
    public void init(CordovaWebView webView, CordovaWebViewClient webViewClient, CordovaChromeClient webChromeClient) {
        LOG.d(TAG, "CordovaActivity.init()");

        if (splashscreenTime >= 0) {
            preferences.set("SplashScreenDelay", splashscreenTime);
        }
        if (splashscreen != 0) {
            preferences.set("SplashDrawableId", splashscreen);
        }

        appView = webView != null ? webView : makeWebView();

        // TODO: Have the views set this themselves.
        if (preferences.getBoolean("DisallowOverscroll", false)) {
            appView.setOverScrollMode(View.OVER_SCROLL_NEVER);
        }
        createViews();

        // Init plugins only after creating views
        if (appView.pluginManager == null) {
            appView.init(this, webViewClient != null ? webViewClient : makeWebViewClient(appView),
                    webChromeClient != null ? webChromeClient : makeChromeClient(appView),
                    pluginEntries, internalWhitelist, externalWhitelist, preferences);
        }

        // Wire the hardware volume controls to control media if desired.
        String volumePref = preferences.getString("DefaultVolumeStream", "");
        if ("media".equals(volumePref.toLowerCase(Locale.ENGLISH))) {
            setVolumeControlStream(AudioManager.STREAM_MUSIC);
        }
    }

    /**
     * Load the url into the webview.
     */
    public void loadUrl(String url) {
        if (appView == null) {
            init();
        }
        // If keepRunning
        this.keepRunning = preferences.getBoolean("KeepRunning", true);

        appView.loadUrlIntoView(url, true);
    }

    /**
     * Load the url into the webview after waiting for period of time.
     * This is used to display the splashscreen for certain amount of time.
     *
     * @param url
     * @param time              The number of ms to wait before loading webview
     */
    @Deprecated // Use loadUrl(String url) instead.
    public void loadUrl(final String url, int time) {

        this.splashscreenTime = time;
        this.loadUrl(url);
    }

    @Deprecated
    public void cancelLoadUrl() {
    }

    /**
     * Clear the resource cache.
     */
    @Deprecated // Call method on appView directly.
    public void clearCache() {
        if (appView == null) {
            init();
        }
        this.appView.clearCache(true);
    }

    /**
     * Clear web history in this web view.
     */
    @Deprecated // Call method on appView directly.
    public void clearHistory() {
        this.appView.clearHistory();
    }

    /**
     * Go to previous page in history.  (We manage our own history)
     *
     * @return true if we went back, false if we are already at top
     */
    @Deprecated // Call method on appView directly.
    public boolean backHistory() {
        if (this.appView != null) {
            return appView.backHistory();
        }
        return false;
    }

    /**
     * Get boolean property for activity.
     */
    @Deprecated // Call method on preferences directly.
    public boolean getBooleanProperty(String name, boolean defaultValue) {
        return preferences.getBoolean(name, defaultValue);
    }

    /**
     * Get int property for activity.
     */
    @Deprecated // Call method on preferences directly.
    public int getIntegerProperty(String name, int defaultValue) {
        return preferences.getInteger(name, defaultValue);
    }

    /**
     * Get string property for activity.
     */
    @Deprecated // Call method on preferences directly.
    public String getStringProperty(String name, String defaultValue) {
        return preferences.getString(name, defaultValue);
    }

    /**
     * Get double property for activity.
     */
    @Deprecated // Call method on preferences directly.
    public double getDoubleProperty(String name, double defaultValue) {
        return preferences.getDouble(name, defaultValue);
    }

    /**
     * Set boolean property on activity.
     * This method has been deprecated in 3.0 and will be removed at a future
     * time. Please use config.xml instead.
     *
     * @param name
     * @param value
     * @deprecated
     */
    @Deprecated
    public void setBooleanProperty(String name, boolean value) {
        Log.d(TAG, "Setting boolean properties in CordovaActivity will be deprecated in 3.0 on July 2013, please use config.xml");
        this.getIntent().putExtra(name.toLowerCase(), value);
    }

    /**
     * Set int property on activity.
     * This method has been deprecated in 3.0 and will be removed at a future
     * time. Please use config.xml instead.
     *
     * @param name
     * @param value
     * @deprecated
     */
    @Deprecated
    public void setIntegerProperty(String name, int value) {
        Log.d(TAG, "Setting integer properties in CordovaActivity will be deprecated in 3.0 on July 2013, please use config.xml");
        this.getIntent().putExtra(name.toLowerCase(), value);
    }

    /**
     * Set string property on activity.
     * This method has been deprecated in 3.0 and will be removed at a future
     * time. Please use config.xml instead.
     *
     * @param name
     * @param value
     * @deprecated
     */
    @Deprecated
    public void setStringProperty(String name, String value) {
        Log.d(TAG, "Setting string properties in CordovaActivity will be deprecated in 3.0 on July 2013, please use config.xml");
        this.getIntent().putExtra(name.toLowerCase(), value);
    }

    /**
     * Set double property on activity.
     * This method has been deprecated in 3.0 and will be removed at a future
     * time. Please use config.xml instead.
     *
     * @param name
     * @param value
     * @deprecated
     */
    @Deprecated
    public void setDoubleProperty(String name, double value) {
        Log.d(TAG, "Setting double properties in CordovaActivity will be deprecated in 3.0 on July 2013, please use config.xml");
        this.getIntent().putExtra(name.toLowerCase(), value);
    }

    /**
     * Called when the system is about to start resuming a previous activity.
     */
    @Override
    protected void onPause() {
        super.onPause();

        LOG.d(TAG, "Paused the application!");

        // Don't process pause if shutting down, since onDestroy() will be called
        if (this.activityState == ACTIVITY_EXITING) {
            return;
        }

        if (this.appView == null) {
            return;
        }
        else
        {
            this.appView.handlePause(this.keepRunning);
        }
    }

    /**
     * Called when the activity receives a new intent
     **/
    @Override
    protected void onNewIntent(Intent intent) {
        super.onNewIntent(intent);
        //Forward to plugins
        if (this.appView != null)
           this.appView.onNewIntent(intent);
    }

    /**
     * Called when the activity will start interacting with the user.
     */
    @Override
    protected void onResume() {
        super.onResume();
        LOG.d(TAG, "Resuming the App");
        
        if (this.activityState == ACTIVITY_STARTING) {
            this.activityState = ACTIVITY_RUNNING;
            return;
        }

        if (this.appView == null) {
            return;
        }
        // Force window to have focus, so application always
        // receive user input. Workaround for some devices (Samsung Galaxy Note 3 at least)
        this.getWindow().getDecorView().requestFocus();

        this.appView.handleResume(this.keepRunning, this.activityResultKeepRunning);

        // If app doesn't want to run in background
        if (!this.keepRunning || this.activityResultKeepRunning) {

            // Restore multitasking state
            if (this.activityResultKeepRunning) {
                this.keepRunning = this.activityResultKeepRunning;
                this.activityResultKeepRunning = false;
            }
        }
    }

    /**
     * The final call you receive before your activity is destroyed.
     */
    @Override
    public void onDestroy() {
        LOG.d(TAG, "CordovaActivity.onDestroy()");
        super.onDestroy();

        if (this.appView != null) {
            appView.handleDestroy();
        }
        else {
            this.activityState = ACTIVITY_EXITING; 
        }
    }

    /**
     * Send a message to all plugins.
     */
    public void postMessage(String id, Object data) {
        if (this.appView != null) {
            this.appView.postMessage(id, data);
        }
    }

    /**
     * @deprecated
     * Add services to res/xml/plugins.xml instead.
     *
     * Add a class that implements a service.
     */
    @Deprecated
    public void addService(String serviceType, String className) {
        if (this.appView != null && this.appView.pluginManager != null) {
            this.appView.pluginManager.addService(serviceType, className);
        }
    }

    /**
     * Send JavaScript statement back to JavaScript.
     * (This is a convenience method)
     *
     * @param statement
     */
    @Deprecated // Call method on appView directly.
    public void sendJavascript(String statement) {
        if (this.appView != null) {
            this.appView.bridge.getMessageQueue().addJavaScript(statement);
        }
    }

    /**
     * Show the spinner.  Must be called from the UI thread.
     *
     * @param title         Title of the dialog
     * @param message       The message of the dialog
     */
    @Deprecated // Call this directly on SplashScreen plugin instead.
    public void spinnerStart(final String title, final String message) {
        JSONArray args = new JSONArray();
        args.put(title);
        args.put(message);
        doSplashScreenAction("spinnerStart", args);
    }

    /**
     * Stop spinner - Must be called from UI thread
     */
    @Deprecated // Call this directly on SplashScreen plugin instead.
    public void spinnerStop() {
        doSplashScreenAction("spinnerStop", null);
    }

    /**
     * End this activity by calling finish for activity
     */
    public void endActivity() {
        this.activityState = ACTIVITY_EXITING;
        super.finish();
    }


    /**
     * Launch an activity for which you would like a result when it finished. When this activity exits,
     * your onActivityResult() method will be called.
     *
     * @param command           The command object
     * @param intent            The intent to start
     * @param requestCode       The request code that is passed to callback to identify the activity
     */
    public void startActivityForResult(CordovaPlugin command, Intent intent, int requestCode) {
        setActivityResultCallback(command);
        this.activityResultKeepRunning = this.keepRunning;

        // If multitasking turned on, then disable it for activities that return results
        if (command != null) {
            this.keepRunning = false;
        }

        try {
            startActivityForResult(intent, requestCode);
        } catch (RuntimeException e) { // E.g.: ActivityNotFoundException
            activityResultCallback = null;
            throw e;
        }
    }

    @Override
    public void startActivityForResult(Intent intent, int requestCode, Bundle options) {
        // Capture requestCode here so that it is captured in the setActivityResultCallback() case.
        activityResultRequestCode = requestCode;
        super.startActivityForResult(intent, requestCode, options);
    }

    /**
     * Called when an activity you launched exits, giving you the requestCode you started it with,
     * the resultCode it returned, and any additional data from it.
     *
     * @param requestCode       The request code originally supplied to startActivityForResult(),
     *                          allowing you to identify who this result came from.
     * @param resultCode        The integer result code returned by the child activity through its setResult().
     * @param intent            An Intent, which can return result data to the caller (various data can be attached to Intent "extras").
     */
    @Override
    protected void onActivityResult(int requestCode, int resultCode, Intent intent) {
        LOG.d(TAG, "Incoming Result. Request code = " + requestCode);
        super.onActivityResult(requestCode, resultCode, intent);
        CordovaPlugin callback = this.activityResultCallback;
        if(callback == null && initCallbackClass != null) {
            // The application was restarted, but had defined an initial callback
            // before being shut down.
            callback = appView.pluginManager.getPlugin(initCallbackClass);
        }
        initCallbackClass = null;
        activityResultCallback = null;

        if (callback != null) {
            LOG.d(TAG, "We have a callback to send this result to");
            callback.onActivityResult(requestCode, resultCode, intent);
        } else {
            LOG.w(TAG, "Got an activity result, but no plugin was registered to receive it.");
        }
    }

    public void setActivityResultCallback(CordovaPlugin plugin) {
        // Cancel any previously pending activity.
        if (activityResultCallback != null) {
            activityResultCallback.onActivityResult(activityResultRequestCode, Activity.RESULT_CANCELED, null);
        }
        this.activityResultCallback = plugin;
    }

    /**
     * Report an error to the host application. These errors are unrecoverable (i.e. the main resource is unavailable).
     * The errorCode parameter corresponds to one of the ERROR_* constants.
     *
     * @param errorCode    The error code corresponding to an ERROR_* value.
     * @param description  A String describing the error.
     * @param failingUrl   The url that failed to load.
     */
    public void onReceivedError(final int errorCode, final String description, final String failingUrl) {
        final CordovaActivity me = this;

        // If errorUrl specified, then load it
        final String errorUrl = preferences.getString("errorUrl", null);
        if ((errorUrl != null) && (errorUrl.startsWith("file://") || internalWhitelist.isUrlWhiteListed(errorUrl)) && (!failingUrl.equals(errorUrl))) {

            // Load URL on UI thread
            me.runOnUiThread(new Runnable() {
                public void run() {
                    me.appView.showWebPage(errorUrl, false, true, null);
                }
            });
        }
        // If not, then display error dialog
        else {
            final boolean exit = !(errorCode == WebViewClient.ERROR_HOST_LOOKUP);
            me.runOnUiThread(new Runnable() {
                public void run() {
                    if (exit) {
                        me.appView.setVisibility(View.GONE);
                        me.displayError("Application Error", description + " (" + failingUrl + ")", "OK", exit);
                    }
                }
            });
        }
    }

    /**
     * Display an error dialog and optionally exit application.
     */
    public void displayError(final String title, final String message, final String button, final boolean exit) {
        final CordovaActivity me = this;
        me.runOnUiThread(new Runnable() {
            public void run() {
                try {
                    AlertDialog.Builder dlg = new AlertDialog.Builder(me);
                    dlg.setMessage(message);
                    dlg.setTitle(title);
                    dlg.setCancelable(false);
                    dlg.setPositiveButton(button,
                            new AlertDialog.OnClickListener() {
                                public void onClick(DialogInterface dialog, int which) {
                                    dialog.dismiss();
                                    if (exit) {
                                        me.endActivity();
                                    }
                                }
                            });
                    dlg.create();
                    dlg.show();
                } catch (Exception e) {
                    finish();
                }
            }
        });
    }

    /**
     * Determine if URL is in approved list of URLs to load.
     */
    @Deprecated // Use whitelist object directly.
    public boolean isUrlWhiteListed(String url) {
        return internalWhitelist.isUrlWhiteListed(url);
    }

    /*
     * Hook in Cordova for menu plugins
     */
    @Override
    public boolean onCreateOptionsMenu(Menu menu) {
        this.postMessage("onCreateOptionsMenu", menu);
        return super.onCreateOptionsMenu(menu);
    }

    @Override
    public boolean onPrepareOptionsMenu(Menu menu) {
        this.postMessage("onPrepareOptionsMenu", menu);
        return true;
    }

    @Override
    public boolean onOptionsItemSelected(MenuItem item) {
        this.postMessage("onOptionsItemSelected", item);
        return true;
    }

    /**
     * Get Activity context.
     */
    @Deprecated
    public Context getContext() {
        LOG.d(TAG, "This will be deprecated December 2012");
        return this;
    }

    /**
     * Load the specified URL in the Cordova webview or a new browser instance.
     *
     * NOTE: If openExternal is false, only URLs listed in whitelist can be loaded.
     *
     * @param url           The url to load.
     * @param openExternal  Load url in browser instead of Cordova webview.
     * @param clearHistory  Clear the history stack, so new page becomes top of history
     * @param params        Parameters for new app
     */
    @Deprecated // Call method on appView directly.
    public void showWebPage(String url, boolean openExternal, boolean clearHistory, HashMap<String, Object> params) {
        if (this.appView != null) {
            appView.showWebPage(url, openExternal, clearHistory, params);
        }
    }

    private void doSplashScreenAction(String action, JSONArray args) {
        CordovaPlugin p = appView.pluginManager.getPlugin("org.apache.cordova.splashscreeninternal");
        if (p != null) {
            args = args == null ? new JSONArray() : args;
            try {
                p.execute(action, args, null);
            } catch (JSONException e) {
                e.printStackTrace();
            }
        }
    }

    /**
     * Removes the Dialog that displays the splash screen
     */
    @Deprecated
    public void removeSplashScreen() {
        doSplashScreenAction("hide", null);
    }

    /**
     * Shows the splash screen over the full Activity
     */
    @SuppressWarnings("deprecation")
    @Deprecated
    protected void showSplashScreen(final int time) {
        preferences.set("SplashScreenDelay", time);
        doSplashScreenAction("show", null);
    }

    @Override
    public boolean onKeyUp(int keyCode, KeyEvent event)
    {
        if (appView != null && (appView.isCustomViewShowing() || appView.getFocusedChild() != null ) &&
                (keyCode == KeyEvent.KEYCODE_BACK || keyCode == KeyEvent.KEYCODE_MENU)) {
            return appView.onKeyUp(keyCode, event);
        } else {
            return super.onKeyUp(keyCode, event);
    	}
    }
    
    /*
     * Android 2.x needs to be able to check where the cursor is.  Android 4.x does not
     * 
     * (non-Javadoc)
     * @see android.app.Activity#onKeyDown(int, android.view.KeyEvent)
     */
    
    @Override
    public boolean onKeyDown(int keyCode, KeyEvent event)
    {
        //Determine if the focus is on the current view or not
        if (appView != null && appView.getFocusedChild() != null && (keyCode == KeyEvent.KEYCODE_BACK || keyCode == KeyEvent.KEYCODE_MENU)) {
                    return appView.onKeyDown(keyCode, event);
        }
        else
            return super.onKeyDown(keyCode, event);
    }
    
    
    /**
     * Called when a message is sent to plugin.
     *
     * @param id            The message id
     * @param data          The message data
     * @return              Object or null
     */
    public Object onMessage(String id, Object data) {
        if (!"onScrollChanged".equals(id)) {
            LOG.d(TAG, "onMessage(" + id + "," + data + ")");
        }

        if ("onReceivedError".equals(id)) {
            JSONObject d = (JSONObject) data;
            try {
                this.onReceivedError(d.getInt("errorCode"), d.getString("description"), d.getString("url"));
            } catch (JSONException e) {
                e.printStackTrace();
            }
        }
        else if ("exit".equals(id)) {
            this.endActivity();
        }
        return null;
    }

    public ExecutorService getThreadPool() {
        return threadPool;
    }
    
    protected void onSaveInstanceState(Bundle outState)
    {
        super.onSaveInstanceState(outState);
        if(this.activityResultCallback != null)
        {
            String cClass = this.activityResultCallback.getClass().getName();
            outState.putString("callbackClass", cClass);
        }
    }
}


File: platforms/android/CordovaLib/src/org/apache/cordova/CordovaBridge.java
/*
       Licensed to the Apache Software Foundation (ASF) under one
       or more contributor license agreements.  See the NOTICE file
       distributed with this work for additional information
       regarding copyright ownership.  The ASF licenses this file
       to you under the Apache License, Version 2.0 (the
       "License"); you may not use this file except in compliance
       with the License.  You may obtain a copy of the License at

         http://www.apache.org/licenses/LICENSE-2.0

       Unless required by applicable law or agreed to in writing,
       software distributed under the License is distributed on an
       "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY
       KIND, either express or implied.  See the License for the
       specific language governing permissions and limitations
       under the License.
*/
package org.apache.cordova;

import java.security.SecureRandom;

import org.apache.cordova.PluginManager;
import org.json.JSONArray;
import org.json.JSONException;

import android.util.Log;

/**
 * Contains APIs that the JS can call. All functions in here should also have
 * an equivalent entry in CordovaChromeClient.java, and be added to
 * cordova-js/lib/android/plugin/android/promptbasednativeapi.js
 */
public class CordovaBridge {
    private static final String LOG_TAG = "CordovaBridge";
    private PluginManager pluginManager;
    private NativeToJsMessageQueue jsMessageQueue;
    private volatile int expectedBridgeSecret = -1; // written by UI thread, read by JS thread.
    private String loadedUrl;
    private String appContentUrlPrefix;

    public CordovaBridge(PluginManager pluginManager, NativeToJsMessageQueue jsMessageQueue, String packageName) {
        this.pluginManager = pluginManager;
        this.jsMessageQueue = jsMessageQueue;
        this.appContentUrlPrefix = "content://" + packageName + ".";
    }

    public String jsExec(int bridgeSecret, String service, String action, String callbackId, String arguments) throws JSONException, IllegalAccessException {
        if (!verifySecret("exec()", bridgeSecret)) {
            return null;
        }
        // If the arguments weren't received, send a message back to JS.  It will switch bridge modes and try again.  See CB-2666.
        // We send a message meant specifically for this case.  It starts with "@" so no other message can be encoded into the same string.
        if (arguments == null) {
            return "@Null arguments.";
        }

        jsMessageQueue.setPaused(true);
        try {
            // Tell the resourceApi what thread the JS is running on.
            CordovaResourceApi.jsThread = Thread.currentThread();

            pluginManager.exec(service, action, callbackId, arguments);
            String ret = null;
            if (!NativeToJsMessageQueue.DISABLE_EXEC_CHAINING) {
                ret = jsMessageQueue.popAndEncode(false);
            }
            return ret;
        } catch (Throwable e) {
            e.printStackTrace();
            return "";
        } finally {
            jsMessageQueue.setPaused(false);
        }
    }

    public void jsSetNativeToJsBridgeMode(int bridgeSecret, int value) throws IllegalAccessException {
        if (!verifySecret("setNativeToJsBridgeMode()", bridgeSecret)) {
            return;
        }
        jsMessageQueue.setBridgeMode(value);
    }

    public String jsRetrieveJsMessages(int bridgeSecret, boolean fromOnlineEvent) throws IllegalAccessException {
        if (!verifySecret("retrieveJsMessages()", bridgeSecret)) {
            return null;
        }
        return jsMessageQueue.popAndEncode(fromOnlineEvent);
    }

    private boolean verifySecret(String action, int bridgeSecret) throws IllegalAccessException {
        if (!jsMessageQueue.isBridgeEnabled()) {
            if (bridgeSecret == -1) {
                Log.d(LOG_TAG, action + " call made before bridge was enabled.");
            } else {
                Log.d(LOG_TAG, "Ignoring " + action + " from previous page load.");
            }
            return false;
        }
        // Bridge secret wrong and bridge not due to it being from the previous page.
        if (expectedBridgeSecret < 0 || bridgeSecret != expectedBridgeSecret) {
            Log.e(LOG_TAG, "Bridge access attempt with wrong secret token, possibly from malicious code. Disabling exec() bridge!");
            clearBridgeSecret();
            throw new IllegalAccessException();
        }
        return true;
    }

    /** Called on page transitions */
    void clearBridgeSecret() {
        expectedBridgeSecret = -1;
    }

    /** Called by cordova.js to initialize the bridge. */
    int generateBridgeSecret() {
        SecureRandom randGen = new SecureRandom();
        expectedBridgeSecret = randGen.nextInt(Integer.MAX_VALUE);
        return expectedBridgeSecret;
    }

    public void reset(String loadedUrl) {
        jsMessageQueue.reset();
        clearBridgeSecret();        
        this.loadedUrl = loadedUrl;
    }

    public String promptOnJsPrompt(String origin, String message, String defaultValue) {
        if (defaultValue != null && defaultValue.length() > 3 && defaultValue.startsWith("gap:")) {
            JSONArray array;
            try {
                array = new JSONArray(defaultValue.substring(4));
                int bridgeSecret = array.getInt(0);
                String service = array.getString(1);
                String action = array.getString(2);
                String callbackId = array.getString(3);
                String r = jsExec(bridgeSecret, service, action, callbackId, message);
                return r == null ? "" : r;
            } catch (JSONException e) {
                e.printStackTrace();
            } catch (IllegalAccessException e) {
                e.printStackTrace();
            }
            return "";
        }
        // Sets the native->JS bridge mode. 
        else if (defaultValue != null && defaultValue.startsWith("gap_bridge_mode:")) {
            try {
                int bridgeSecret = Integer.parseInt(defaultValue.substring(16));
                jsSetNativeToJsBridgeMode(bridgeSecret, Integer.parseInt(message));
            } catch (NumberFormatException e){
                e.printStackTrace();
            } catch (IllegalAccessException e) {
                e.printStackTrace();
            }
            return "";
        }
        // Polling for JavaScript messages 
        else if (defaultValue != null && defaultValue.startsWith("gap_poll:")) {
            int bridgeSecret = Integer.parseInt(defaultValue.substring(9));
            try {
                String r = jsRetrieveJsMessages(bridgeSecret, "1".equals(message));
                return r == null ? "" : r;
            } catch (IllegalAccessException e) {
                e.printStackTrace();
            }
            return "";
        }
        else if (defaultValue != null && defaultValue.startsWith("gap_init:")) {
            // Protect against random iframes being able to talk through the bridge.
            // Trust only file URLs and the start URL's domain.
            // The extra origin.startsWith("http") is to protect against iframes with data: having "" as origin.
            if (origin.startsWith("file:") ||
                origin.startsWith(this.appContentUrlPrefix) ||
                (origin.startsWith("http") && loadedUrl.startsWith(origin))) {
                // Enable the bridge
                int bridgeMode = Integer.parseInt(defaultValue.substring(9));
                jsMessageQueue.setBridgeMode(bridgeMode);
                // Tell JS the bridge secret.
                int secret = generateBridgeSecret();
                return ""+secret;
            } else {
                Log.e(LOG_TAG, "gap_init called from restricted origin: " + origin);
            }
            return "";
        }
        return null;
    }
    
    public NativeToJsMessageQueue getMessageQueue() {
        return jsMessageQueue;
    }
}


File: platforms/android/CordovaLib/src/org/apache/cordova/CordovaChromeClient.java
/*
       Licensed to the Apache Software Foundation (ASF) under one
       or more contributor license agreements.  See the NOTICE file
       distributed with this work for additional information
       regarding copyright ownership.  The ASF licenses this file
       to you under the Apache License, Version 2.0 (the
       "License"); you may not use this file except in compliance
       with the License.  You may obtain a copy of the License at

         http://www.apache.org/licenses/LICENSE-2.0

       Unless required by applicable law or agreed to in writing,
       software distributed under the License is distributed on an
       "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY
       KIND, either express or implied.  See the License for the
       specific language governing permissions and limitations
       under the License.
*/
package org.apache.cordova;

import org.apache.cordova.CordovaInterface;
import org.apache.cordova.LOG;

import android.annotation.TargetApi;
import android.app.Activity;
import android.app.AlertDialog;
import android.content.ActivityNotFoundException;
import android.content.DialogInterface;
import android.content.Intent;
import android.net.Uri;
import android.os.Build;
import android.util.Log;
import android.view.Gravity;
import android.view.KeyEvent;
import android.view.View;
import android.view.ViewGroup.LayoutParams;
import android.webkit.ConsoleMessage;
import android.webkit.JsPromptResult;
import android.webkit.JsResult;
import android.webkit.ValueCallback;
import android.webkit.WebChromeClient;
import android.webkit.WebStorage;
import android.webkit.WebView;
import android.webkit.GeolocationPermissions.Callback;
import android.widget.EditText;
import android.widget.LinearLayout;
import android.widget.ProgressBar;
import android.widget.RelativeLayout;

/**
 * This class is the WebChromeClient that implements callbacks for our web view.
 * The kind of callbacks that happen here are on the chrome outside the document,
 * such as onCreateWindow(), onConsoleMessage(), onProgressChanged(), etc. Related
 * to but different than CordovaWebViewClient.
 *
 * @see <a href="http://developer.android.com/reference/android/webkit/WebChromeClient.html">WebChromeClient</a>
 * @see <a href="http://developer.android.com/guide/webapps/webview.html">WebView guide</a>
 * @see CordovaWebViewClient
 * @see CordovaWebView
 */
public class CordovaChromeClient extends WebChromeClient {

    public static final int FILECHOOSER_RESULTCODE = 5173;
    private String TAG = "CordovaLog";
    private long MAX_QUOTA = 100 * 1024 * 1024;
    protected CordovaInterface cordova;
    protected CordovaWebView appView;

    // the video progress view
    private View mVideoProgressView;
    
    //Keep track of last AlertDialog showed
    private AlertDialog lastHandledDialog;

    @Deprecated
    public CordovaChromeClient(CordovaInterface cordova) {
        this.cordova = cordova;
    }

    public CordovaChromeClient(CordovaInterface ctx, CordovaWebView app) {
        this.cordova = ctx;
        this.appView = app;
    }

    @Deprecated
    public void setWebView(CordovaWebView view) {
        this.appView = view;
    }

    /**
     * Tell the client to display a javascript alert dialog.
     *
     * @param view
     * @param url
     * @param message
     * @param result
     * @see Other implementation in the Dialogs plugin.
     */
    @Override
    public boolean onJsAlert(WebView view, String url, String message, final JsResult result) {
        AlertDialog.Builder dlg = new AlertDialog.Builder(this.cordova.getActivity());
        dlg.setMessage(message);
        dlg.setTitle("Alert");
        //Don't let alerts break the back button
        dlg.setCancelable(true);
        dlg.setPositiveButton(android.R.string.ok,
                new AlertDialog.OnClickListener() {
                    public void onClick(DialogInterface dialog, int which) {
                        result.confirm();
                    }
                });
        dlg.setOnCancelListener(
                new DialogInterface.OnCancelListener() {
                    public void onCancel(DialogInterface dialog) {
                        result.cancel();
                    }
                });
        dlg.setOnKeyListener(new DialogInterface.OnKeyListener() {
            //DO NOTHING
            public boolean onKey(DialogInterface dialog, int keyCode, KeyEvent event) {
                if (keyCode == KeyEvent.KEYCODE_BACK)
                {
                    result.confirm();
                    return false;
                }
                else
                    return true;
            }
        });
        lastHandledDialog = dlg.show();
        return true;
    }

    /**
     * Tell the client to display a confirm dialog to the user.
     *
     * @param view
     * @param url
     * @param message
     * @param result
     * @see Other implementation in the Dialogs plugin.
     */
    @Override
    public boolean onJsConfirm(WebView view, String url, String message, final JsResult result) {
        AlertDialog.Builder dlg = new AlertDialog.Builder(this.cordova.getActivity());
        dlg.setMessage(message);
        dlg.setTitle("Confirm");
        dlg.setCancelable(true);
        dlg.setPositiveButton(android.R.string.ok,
                new DialogInterface.OnClickListener() {
                    public void onClick(DialogInterface dialog, int which) {
                        result.confirm();
                    }
                });
        dlg.setNegativeButton(android.R.string.cancel,
                new DialogInterface.OnClickListener() {
                    public void onClick(DialogInterface dialog, int which) {
                        result.cancel();
                    }
                });
        dlg.setOnCancelListener(
                new DialogInterface.OnCancelListener() {
                    public void onCancel(DialogInterface dialog) {
                        result.cancel();
                    }
                });
        dlg.setOnKeyListener(new DialogInterface.OnKeyListener() {
            //DO NOTHING
            public boolean onKey(DialogInterface dialog, int keyCode, KeyEvent event) {
                if (keyCode == KeyEvent.KEYCODE_BACK)
                {
                    result.cancel();
                    return false;
                }
                else
                    return true;
            }
        });
        lastHandledDialog = dlg.show();
        return true;
    }

    /**
     * Tell the client to display a prompt dialog to the user.
     * If the client returns true, WebView will assume that the client will
     * handle the prompt dialog and call the appropriate JsPromptResult method.
     *
     * Since we are hacking prompts for our own purposes, we should not be using them for
     * this purpose, perhaps we should hack console.log to do this instead!
     *
     * @see Other implementation in the Dialogs plugin.
     */
    @Override
    public boolean onJsPrompt(WebView view, String origin, String message, String defaultValue, JsPromptResult result) {
        // Unlike the @JavascriptInterface bridge, this method is always called on the UI thread.
        String handledRet = appView.bridge.promptOnJsPrompt(origin, message, defaultValue);
        if (handledRet != null) {
            result.confirm(handledRet);
        } else {
            // Returning false would also show a dialog, but the default one shows the origin (ugly).
            final JsPromptResult res = result;
            AlertDialog.Builder dlg = new AlertDialog.Builder(this.cordova.getActivity());
            dlg.setMessage(message);
            final EditText input = new EditText(this.cordova.getActivity());
            if (defaultValue != null) {
                input.setText(defaultValue);
            }
            dlg.setView(input);
            dlg.setCancelable(false);
            dlg.setPositiveButton(android.R.string.ok,
                    new DialogInterface.OnClickListener() {
                        public void onClick(DialogInterface dialog, int which) {
                            String usertext = input.getText().toString();
                            res.confirm(usertext);
                        }
                    });
            dlg.setNegativeButton(android.R.string.cancel,
                    new DialogInterface.OnClickListener() {
                        public void onClick(DialogInterface dialog, int which) {
                            res.cancel();
                        }
                    });
            lastHandledDialog = dlg.show();
        }
        return true;
    }

    /**
     * Handle database quota exceeded notification.
     */
    @Override
    public void onExceededDatabaseQuota(String url, String databaseIdentifier, long currentQuota, long estimatedSize,
            long totalUsedQuota, WebStorage.QuotaUpdater quotaUpdater)
    {
        LOG.d(TAG, "onExceededDatabaseQuota estimatedSize: %d  currentQuota: %d  totalUsedQuota: %d", estimatedSize, currentQuota, totalUsedQuota);
        quotaUpdater.updateQuota(MAX_QUOTA);
    }

    // console.log in api level 7: http://developer.android.com/guide/developing/debug-tasks.html
    // Expect this to not compile in a future Android release!
    @SuppressWarnings("deprecation")
    @Override
    public void onConsoleMessage(String message, int lineNumber, String sourceID)
    {
        //This is only for Android 2.1
        if(android.os.Build.VERSION.SDK_INT == android.os.Build.VERSION_CODES.ECLAIR_MR1)
        {
            LOG.d(TAG, "%s: Line %d : %s", sourceID, lineNumber, message);
            super.onConsoleMessage(message, lineNumber, sourceID);
        }
    }

    @TargetApi(8)
    @Override
    public boolean onConsoleMessage(ConsoleMessage consoleMessage)
    {
        if (consoleMessage.message() != null)
            LOG.d(TAG, "%s: Line %d : %s" , consoleMessage.sourceId() , consoleMessage.lineNumber(), consoleMessage.message());
         return super.onConsoleMessage(consoleMessage);
    }

    @Override
    /**
     * Instructs the client to show a prompt to ask the user to set the Geolocation permission state for the specified origin.
     *
     * @param origin
     * @param callback
     */
    public void onGeolocationPermissionsShowPrompt(String origin, Callback callback) {
        super.onGeolocationPermissionsShowPrompt(origin, callback);
        callback.invoke(origin, true, false);
    }
    
    // API level 7 is required for this, see if we could lower this using something else
    @Override
    public void onShowCustomView(View view, WebChromeClient.CustomViewCallback callback) {
        this.appView.showCustomView(view, callback);
    }

    @Override
    public void onHideCustomView() {
        this.appView.hideCustomView();
    }
    
    @Override
    /**
     * Ask the host application for a custom progress view to show while
     * a <video> is loading.
     * @return View The progress view.
     */
    public View getVideoLoadingProgressView() {

        if (mVideoProgressView == null) {            
            // Create a new Loading view programmatically.
            
            // create the linear layout
            LinearLayout layout = new LinearLayout(this.appView.getContext());
            layout.setOrientation(LinearLayout.VERTICAL);
            RelativeLayout.LayoutParams layoutParams = new RelativeLayout.LayoutParams(LayoutParams.WRAP_CONTENT, LayoutParams.WRAP_CONTENT);
            layoutParams.addRule(RelativeLayout.CENTER_IN_PARENT);
            layout.setLayoutParams(layoutParams);
            // the proress bar
            ProgressBar bar = new ProgressBar(this.appView.getContext());
            LinearLayout.LayoutParams barLayoutParams = new LinearLayout.LayoutParams(LayoutParams.WRAP_CONTENT, LayoutParams.WRAP_CONTENT);
            barLayoutParams.gravity = Gravity.CENTER;
            bar.setLayoutParams(barLayoutParams);   
            layout.addView(bar);
            
            mVideoProgressView = layout;
        }
    return mVideoProgressView; 
    }

    // <input type=file> support:
    // openFileChooser() is for pre KitKat and in KitKat mr1 (it's known broken in KitKat).
    // For Lollipop, we use onShowFileChooser().
    public void openFileChooser(ValueCallback<Uri> uploadMsg) {
        this.openFileChooser(uploadMsg, "*/*");
    }

    public void openFileChooser( ValueCallback<Uri> uploadMsg, String acceptType ) {
        this.openFileChooser(uploadMsg, acceptType, null);
    }
    
    public void openFileChooser(final ValueCallback<Uri> uploadMsg, String acceptType, String capture)
    {
        Intent intent = new Intent(Intent.ACTION_GET_CONTENT);
        intent.addCategory(Intent.CATEGORY_OPENABLE);
        intent.setType("*/*");
        cordova.startActivityForResult(new CordovaPlugin() {
            @Override
            public void onActivityResult(int requestCode, int resultCode, Intent intent) {
                Uri result = intent == null || resultCode != Activity.RESULT_OK ? null : intent.getData();
                Log.d(TAG, "Receive file chooser URL: " + result);
                uploadMsg.onReceiveValue(result);
            }
        }, intent, FILECHOOSER_RESULTCODE);
    }

    @TargetApi(Build.VERSION_CODES.LOLLIPOP)
    @Override
    public boolean onShowFileChooser(WebView webView, final ValueCallback<Uri[]> filePathsCallback, final WebChromeClient.FileChooserParams fileChooserParams) {
        Intent intent = fileChooserParams.createIntent();
        try {
            cordova.startActivityForResult(new CordovaPlugin() {
                @Override
                public void onActivityResult(int requestCode, int resultCode, Intent intent) {
                    Uri[] result = WebChromeClient.FileChooserParams.parseResult(resultCode, intent);
                    Log.d(TAG, "Receive file chooser URL: " + result);
                    filePathsCallback.onReceiveValue(result);
                }
            }, intent, FILECHOOSER_RESULTCODE);
        } catch (ActivityNotFoundException e) {
            Log.w("No activity found to handle file chooser intent.", e);
            filePathsCallback.onReceiveValue(null);
        }
        return true;
    }

    public void destroyLastDialog(){
        if(lastHandledDialog != null){
                lastHandledDialog.cancel();
        }
    }

}


File: platforms/android/CordovaLib/src/org/apache/cordova/CordovaPlugin.java
/*
       Licensed to the Apache Software Foundation (ASF) under one
       or more contributor license agreements.  See the NOTICE file
       distributed with this work for additional information
       regarding copyright ownership.  The ASF licenses this file
       to you under the Apache License, Version 2.0 (the
       "License"); you may not use this file except in compliance
       with the License.  You may obtain a copy of the License at

         http://www.apache.org/licenses/LICENSE-2.0

       Unless required by applicable law or agreed to in writing,
       software distributed under the License is distributed on an
       "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY
       KIND, either express or implied.  See the License for the
       specific language governing permissions and limitations
       under the License.
*/
package org.apache.cordova;

import org.apache.cordova.CordovaArgs;
import org.apache.cordova.CordovaWebView;
import org.apache.cordova.CordovaInterface;
import org.apache.cordova.CallbackContext;
import org.json.JSONArray;
import org.json.JSONException;

import android.content.Intent;
import android.net.Uri;

/**
 * Plugins must extend this class and override one of the execute methods.
 */
public class CordovaPlugin {
    @Deprecated // This is never set.
    public String id;
    public CordovaWebView webView;
    public CordovaInterface cordova;
    protected CordovaPreferences preferences;

    /**
     * Call this after constructing to initialize the plugin.
     * Final because we want to be able to change args without breaking plugins.
     */
    public final void privateInitialize(CordovaInterface cordova, CordovaWebView webView, CordovaPreferences preferences) {
        assert this.cordova == null;
        this.cordova = cordova;
        this.webView = webView;
        this.preferences = preferences;
        initialize(cordova, webView);
        pluginInitialize();
    }

    /**
     * Called after plugin construction and fields have been initialized.
     * Prefer to use pluginInitialize instead since there is no value in
     * having parameters on the initialize() function.
     */
    public void initialize(CordovaInterface cordova, CordovaWebView webView) {
    }

    /**
     * Called after plugin construction and fields have been initialized.
     */
    protected void pluginInitialize() {
    }
    
    /**
     * Executes the request.
     *
     * This method is called from the WebView thread. To do a non-trivial amount of work, use:
     *     cordova.getThreadPool().execute(runnable);
     *
     * To run on the UI thread, use:
     *     cordova.getActivity().runOnUiThread(runnable);
     *
     * @param action          The action to execute.
     * @param rawArgs         The exec() arguments in JSON form.
     * @param callbackContext The callback context used when calling back into JavaScript.
     * @return                Whether the action was valid.
     */
    public boolean execute(String action, String rawArgs, CallbackContext callbackContext) throws JSONException {
        JSONArray args = new JSONArray(rawArgs);
        return execute(action, args, callbackContext);
    }

    /**
     * Executes the request.
     *
     * This method is called from the WebView thread. To do a non-trivial amount of work, use:
     *     cordova.getThreadPool().execute(runnable);
     *
     * To run on the UI thread, use:
     *     cordova.getActivity().runOnUiThread(runnable);
     *
     * @param action          The action to execute.
     * @param args            The exec() arguments.
     * @param callbackContext The callback context used when calling back into JavaScript.
     * @return                Whether the action was valid.
     */
    public boolean execute(String action, JSONArray args, CallbackContext callbackContext) throws JSONException {
        CordovaArgs cordovaArgs = new CordovaArgs(args);
        return execute(action, cordovaArgs, callbackContext);
    }

    /**
     * Executes the request.
     *
     * This method is called from the WebView thread. To do a non-trivial amount of work, use:
     *     cordova.getThreadPool().execute(runnable);
     *
     * To run on the UI thread, use:
     *     cordova.getActivity().runOnUiThread(runnable);
     *
     * @param action          The action to execute.
     * @param args            The exec() arguments, wrapped with some Cordova helpers.
     * @param callbackContext The callback context used when calling back into JavaScript.
     * @return                Whether the action was valid.
     */
    public boolean execute(String action, CordovaArgs args, CallbackContext callbackContext) throws JSONException {
        return false;
    }

    /**
     * Called when the system is about to start resuming a previous activity.
     *
     * @param multitasking		Flag indicating if multitasking is turned on for app
     */
    public void onPause(boolean multitasking) {
    }

    /**
     * Called when the activity will start interacting with the user.
     *
     * @param multitasking		Flag indicating if multitasking is turned on for app
     */
    public void onResume(boolean multitasking) {
    }

    /**
     * Called when the activity receives a new intent.
     */
    public void onNewIntent(Intent intent) {
    }

    /**
     * The final call you receive before your activity is destroyed.
     */
    public void onDestroy() {
    }

    /**
     * Called when a message is sent to plugin.
     *
     * @param id            The message id
     * @param data          The message data
     * @return              Object to stop propagation or null
     */
    public Object onMessage(String id, Object data) {
        return null;
    }

    /**
     * Called when an activity you launched exits, giving you the requestCode you started it with,
     * the resultCode it returned, and any additional data from it.
     *
     * @param requestCode		The request code originally supplied to startActivityForResult(),
     * 							allowing you to identify who this result came from.
     * @param resultCode		The integer result code returned by the child activity through its setResult().
     * @param intent				An Intent, which can return result data to the caller (various data can be attached to Intent "extras").
     */
    public void onActivityResult(int requestCode, int resultCode, Intent intent) {
    }

    /**
     * By specifying a <url-filter> in config.xml you can map a URL (using startsWith atm) to this method.
     *
     * @param url				The URL that is trying to be loaded in the Cordova webview.
     * @return					Return true to prevent the URL from loading. Default is false.
     */
    public boolean onOverrideUrlLoading(String url) {
        return false;
    }

    /**
     * Hook for redirecting requests. Applies to WebView requests as well as requests made by plugins.
     */
    public Uri remapUri(Uri uri) {
        return null;
    }
    
    /**
     * Called when the WebView does a top-level navigation or refreshes.
     *
     * Plugins should stop any long-running processes and clean up internal state.
     *
     * Does nothing by default.
     */
    public void onReset() {
    }
    
    /**
     * Called when the system received an HTTP authentication request. Plugin can use
     * the supplied HttpAuthHandler to process this auth challenge.
     *
     * @param view              The WebView that is initiating the callback
     * @param handler           The HttpAuthHandler used to set the WebView's response
     * @param host              The host requiring authentication
     * @param realm             The realm for which authentication is required
     * 
     * @return                  Returns True if plugin will resolve this auth challenge, otherwise False
     * 
     */
    public boolean onReceivedHttpAuthRequest(CordovaWebView view, ICordovaHttpAuthHandler handler, String host, String realm) {
        return false;
    }
    
    /**
     * Called when he system received an SSL client certificate request.  Plugin can use
     * the supplied ClientCertRequest to process this certificate challenge.
     *
     * @param view              The WebView that is initiating the callback
     * @param request           The client certificate request
     *
     * @return                  Returns True if plugin will resolve this auth challenge, otherwise False
     *
     */
    public boolean onReceivedClientCertRequest(CordovaWebView view, ICordovaClientCertRequest request) {
        return false;
    }
}


File: platforms/android/CordovaLib/src/org/apache/cordova/CordovaPreferences.java
/*
       Licensed to the Apache Software Foundation (ASF) under one
       or more contributor license agreements.  See the NOTICE file
       distributed with this work for additional information
       regarding copyright ownership.  The ASF licenses this file
       to you under the Apache License, Version 2.0 (the
       "License"); you may not use this file except in compliance
       with the License.  You may obtain a copy of the License at

         http://www.apache.org/licenses/LICENSE-2.0

       Unless required by applicable law or agreed to in writing,
       software distributed under the License is distributed on an
       "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY
       KIND, either express or implied.  See the License for the
       specific language governing permissions and limitations
       under the License.
*/

package org.apache.cordova;

import java.util.HashMap;
import java.util.Locale;
import java.util.Map;

import org.apache.cordova.LOG;

import android.app.Activity;
import android.os.Bundle;

public class CordovaPreferences {
    private HashMap<String, String> prefs = new HashMap<String, String>(20);
    private Bundle preferencesBundleExtras;

    public void setPreferencesBundle(Bundle extras) {
        preferencesBundleExtras = extras;
    }

    public void set(String name, String value) {
        prefs.put(name.toLowerCase(Locale.ENGLISH), value);
    }

    public void set(String name, boolean value) {
        set(name, "" + value);
    }

    public void set(String name, int value) {
        set(name, "" + value);
    }
    
    public void set(String name, double value) {
        set(name, "" + value);
    }
    
    public Map<String, String> getAll() {
        return prefs;
    }

    public boolean getBoolean(String name, boolean defaultValue) {
        name = name.toLowerCase(Locale.ENGLISH);
        String value = prefs.get(name);
        if (value != null) {
            return Boolean.parseBoolean(value);
        } else if (preferencesBundleExtras != null) {
            Object bundleValue = preferencesBundleExtras.get(name);
            if (bundleValue instanceof String) {
                return "true".equals(bundleValue);
            }
            // Gives a nice warning if type is wrong.
            return preferencesBundleExtras.getBoolean(name, defaultValue);
        }
        return defaultValue;
    }

    public int getInteger(String name, int defaultValue) {
        name = name.toLowerCase(Locale.ENGLISH);
        String value = prefs.get(name);
        if (value != null) {
            // Use Integer.decode() can't handle it if the highest bit is set.
            return (int)(long)Long.decode(value);
        } else if (preferencesBundleExtras != null) {
            Object bundleValue = preferencesBundleExtras.get(name);
            if (bundleValue instanceof String) {
                return Integer.valueOf((String)bundleValue);
            }
            // Gives a nice warning if type is wrong.
            return preferencesBundleExtras.getInt(name, defaultValue);
        }
        return defaultValue;
    }

    public double getDouble(String name, double defaultValue) {
        name = name.toLowerCase(Locale.ENGLISH);
        String value = prefs.get(name);
        if (value != null) {
            return Double.valueOf(value);
        } else if (preferencesBundleExtras != null) {
            Object bundleValue = preferencesBundleExtras.get(name);
            if (bundleValue instanceof String) {
                return Double.valueOf((String)bundleValue);
            }
            // Gives a nice warning if type is wrong.
            return preferencesBundleExtras.getDouble(name, defaultValue);
        }
        return defaultValue;
    }

    public String getString(String name, String defaultValue) {
        name = name.toLowerCase(Locale.ENGLISH);
        String value = prefs.get(name);
        if (value != null) {
            return value;
        } else if (preferencesBundleExtras != null && !"errorurl".equals(name)) {
            Object bundleValue = preferencesBundleExtras.get(name);
            if (bundleValue != null) {
                return bundleValue.toString();
            }
        }
        return defaultValue;
    }

    // Plugins should not rely on values within the intent since this does not work
    // for apps with multiple webviews. Instead, they should retrieve prefs from the
    // Config object associated with their webview.
    public void copyIntoIntentExtras(Activity action) {
        for (String name : prefs.keySet()) {
            String value = prefs.get(name);
            if (value == null) {
                continue;
            }
            if (name.equals("loglevel")) {
                LOG.setLogLevel(value);
            } else if (name.equals("splashscreen")) {
                // Note: We should probably pass in the classname for the variable splash on splashscreen!
                int resource = action.getResources().getIdentifier(value, "drawable", action.getClass().getPackage().getName());
                if(resource == 0) {
                    resource = action.getResources().getIdentifier(value, "drawable", action.getPackageName());
                }
                action.getIntent().putExtra(name, resource);
            }
            else if(name.equals("backgroundcolor")) {
                int asInt = (int)(long)Long.decode(value);
                action.getIntent().putExtra(name, asInt);
            }
            else if(name.equals("loadurltimeoutvalue")) {
                int asInt = Integer.decode(value);
                action.getIntent().putExtra(name, asInt);
            }
            else if(name.equals("splashscreendelay")) {
                int asInt = Integer.decode(value);
                action.getIntent().putExtra(name, asInt);
            }
            else if(name.equals("keeprunning"))
            {
                boolean asBool = Boolean.parseBoolean(value);
                action.getIntent().putExtra(name, asBool);
            }
            else if(name.equals("inappbrowserstorageenabled"))
            {
                boolean asBool = Boolean.parseBoolean(value);
                action.getIntent().putExtra(name, asBool);
            }
            else if(name.equals("disallowoverscroll"))
            {
                boolean asBool = Boolean.parseBoolean(value);
                action.getIntent().putExtra(name, asBool);
            }
            else
            {
                action.getIntent().putExtra(name, value);
            }
        }
        // In the normal case, the intent extras are null until the first call to putExtra().
        if (preferencesBundleExtras == null) {
            preferencesBundleExtras = action.getIntent().getExtras();
        }
    }
}


File: platforms/android/CordovaLib/src/org/apache/cordova/CordovaResourceApi.java
/*
       Licensed to the Apache Software Foundation (ASF) under one
       or more contributor license agreements.  See the NOTICE file
       distributed with this work for additional information
       regarding copyright ownership.  The ASF licenses this file
       to you under the Apache License, Version 2.0 (the
       "License"); you may not use this file except in compliance
       with the License.  You may obtain a copy of the License at

         http://www.apache.org/licenses/LICENSE-2.0

       Unless required by applicable law or agreed to in writing,
       software distributed under the License is distributed on an
       "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY
       KIND, either express or implied.  See the License for the
       specific language governing permissions and limitations
       under the License.
 */
package org.apache.cordova;

import android.content.ContentResolver;
import android.content.Context;
import android.content.res.AssetFileDescriptor;
import android.content.res.AssetManager;
import android.database.Cursor;
import android.net.Uri;
import android.os.Looper;
import android.util.Base64;
import android.webkit.MimeTypeMap;

import com.squareup.okhttp.OkHttpClient;

import org.apache.http.util.EncodingUtils;

import java.io.ByteArrayInputStream;
import java.io.File;
import java.io.FileInputStream;
import java.io.FileNotFoundException;
import java.io.FileOutputStream;
import java.io.IOException;
import java.io.InputStream;
import java.io.OutputStream;
import java.net.HttpURLConnection;
import java.net.URL;
import java.nio.channels.FileChannel;
import java.util.Locale;

/**
 * What this class provides:
 * 1. Helpers for reading & writing to URLs.
 *   - E.g. handles assets, resources, content providers, files, data URIs, http[s]
 *   - E.g. Can be used to query for mime-type & content length.
 *
 * 2. To allow plugins to redirect URLs (via remapUrl).
 *   - All plugins should call remapUrl() on URLs they receive from JS *before*
 *     passing the URL onto other utility functions in this class.
 *   - For an example usage of this, refer to the org.apache.cordova.file plugin.
 *
 * 3. It exposes a way to use the OkHttp library that ships with Cordova.
 *   - Through createHttpConnection().
 *
 * Future Work:
 *   - Consider using a Cursor to query content URLs for their size (like the file plugin does).
 *   - Allow plugins to remapUri to "cdv-plugin://plugin-name/$ID", which CordovaResourceApi
 *     would then delegate to pluginManager.getPlugin(plugin-name).openForRead($ID)
 *     - Currently, plugins *can* do this by remapping to a data: URL, but it's inefficient
 *       for large payloads.
 */
public class CordovaResourceApi {
    @SuppressWarnings("unused")
    private static final String LOG_TAG = "CordovaResourceApi";

    public static final int URI_TYPE_FILE = 0;
    public static final int URI_TYPE_ASSET = 1;
    public static final int URI_TYPE_CONTENT = 2;
    public static final int URI_TYPE_RESOURCE = 3;
    public static final int URI_TYPE_DATA = 4;
    public static final int URI_TYPE_HTTP = 5;
    public static final int URI_TYPE_HTTPS = 6;
    public static final int URI_TYPE_UNKNOWN = -1;
    
    private static final String[] LOCAL_FILE_PROJECTION = { "_data" };
    
    // Creating this is light-weight.
    private static OkHttpClient httpClient = new OkHttpClient();
    
    static Thread jsThread;

    private final AssetManager assetManager;
    private final ContentResolver contentResolver;
    private final PluginManager pluginManager;
    private boolean threadCheckingEnabled = true;


    public CordovaResourceApi(Context context, PluginManager pluginManager) {
        this.contentResolver = context.getContentResolver();
        this.assetManager = context.getAssets();
        this.pluginManager = pluginManager;
    }
    
    public void setThreadCheckingEnabled(boolean value) {
        threadCheckingEnabled = value;
    }

    public boolean isThreadCheckingEnabled() {
        return threadCheckingEnabled;
    }
    
    
    public static int getUriType(Uri uri) {
        assertNonRelative(uri);
        String scheme = uri.getScheme();
        if (ContentResolver.SCHEME_CONTENT.equals(scheme)) {
            return URI_TYPE_CONTENT;
        }
        if (ContentResolver.SCHEME_ANDROID_RESOURCE.equals(scheme)) {
            return URI_TYPE_RESOURCE;
        }
        if (ContentResolver.SCHEME_FILE.equals(scheme)) {
            if (uri.getPath().startsWith("/android_asset/")) {
                return URI_TYPE_ASSET;
            }
            return URI_TYPE_FILE;
        }
        if ("data".equals(scheme)) {
            return URI_TYPE_DATA;
        }
        if ("http".equals(scheme)) {
            return URI_TYPE_HTTP;
        }
        if ("https".equals(scheme)) {
            return URI_TYPE_HTTPS;
        }
        return URI_TYPE_UNKNOWN;
    }
    
    public Uri remapUri(Uri uri) {
        assertNonRelative(uri);
        Uri pluginUri = pluginManager.remapUri(uri);
        return pluginUri != null ? pluginUri : uri;
    }

    public String remapPath(String path) {
        return remapUri(Uri.fromFile(new File(path))).getPath();
    }
    
    /**
     * Returns a File that points to the resource, or null if the resource
     * is not on the local filesystem.
     */
    public File mapUriToFile(Uri uri) {
        assertBackgroundThread();
        switch (getUriType(uri)) {
            case URI_TYPE_FILE:
                return new File(uri.getPath());
            case URI_TYPE_CONTENT: {
                Cursor cursor = contentResolver.query(uri, LOCAL_FILE_PROJECTION, null, null, null);
                if (cursor != null) {
                    try {
                        int columnIndex = cursor.getColumnIndex(LOCAL_FILE_PROJECTION[0]);
                        if (columnIndex != -1 && cursor.getCount() > 0) {
                            cursor.moveToFirst();
                            String realPath = cursor.getString(columnIndex);
                            if (realPath != null) {
                                return new File(realPath);
                            }
                        }
                    } finally {
                        cursor.close();
                    }
                }
            }
        }
        return null;
    }
    
    public String getMimeType(Uri uri) {
        switch (getUriType(uri)) {
            case URI_TYPE_FILE:
            case URI_TYPE_ASSET:
                return getMimeTypeFromPath(uri.getPath());
            case URI_TYPE_CONTENT:
            case URI_TYPE_RESOURCE:
                return contentResolver.getType(uri);
            case URI_TYPE_DATA: {
                return getDataUriMimeType(uri);
            }
            case URI_TYPE_HTTP:
            case URI_TYPE_HTTPS: {
                try {
                    HttpURLConnection conn = httpClient.open(new URL(uri.toString()));
                    conn.setDoInput(false);
                    conn.setRequestMethod("HEAD");
                    return conn.getHeaderField("Content-Type");
                } catch (IOException e) {
                }
            }
        }
        
        return null;
    }
    
    
    //This already exists
    private String getMimeTypeFromPath(String path) {
        String extension = path;
        int lastDot = extension.lastIndexOf('.');
        if (lastDot != -1) {
            extension = extension.substring(lastDot + 1);
        }
        // Convert the URI string to lower case to ensure compatibility with MimeTypeMap (see CB-2185).
        extension = extension.toLowerCase(Locale.getDefault());
        if (extension.equals("3ga")) {
            return "audio/3gpp";
        } else if (extension.equals("js")) {
            // Missing from the map :(.
            return "text/javascript";
        }
        return MimeTypeMap.getSingleton().getMimeTypeFromExtension(extension);
    }
    
    /**
     * Opens a stream to the given URI, also providing the MIME type & length.
     * @return Never returns null.
     * @throws Throws an InvalidArgumentException for relative URIs. Relative URIs should be
     *     resolved before being passed into this function.
     * @throws Throws an IOException if the URI cannot be opened.
     * @throws Throws an IllegalStateException if called on a foreground thread.
     */
    public OpenForReadResult openForRead(Uri uri) throws IOException {
        return openForRead(uri, false);
    }

    /**
     * Opens a stream to the given URI, also providing the MIME type & length.
     * @return Never returns null.
     * @throws Throws an InvalidArgumentException for relative URIs. Relative URIs should be
     *     resolved before being passed into this function.
     * @throws Throws an IOException if the URI cannot be opened.
     * @throws Throws an IllegalStateException if called on a foreground thread and skipThreadCheck is false.
     */
    public OpenForReadResult openForRead(Uri uri, boolean skipThreadCheck) throws IOException {
        if (!skipThreadCheck) {
            assertBackgroundThread();
        }
        switch (getUriType(uri)) {
            case URI_TYPE_FILE: {
                FileInputStream inputStream = new FileInputStream(uri.getPath());
                String mimeType = getMimeTypeFromPath(uri.getPath());
                long length = inputStream.getChannel().size();
                return new OpenForReadResult(uri, inputStream, mimeType, length, null);
            }
            case URI_TYPE_ASSET: {
                String assetPath = uri.getPath().substring(15);
                AssetFileDescriptor assetFd = null;
                InputStream inputStream;
                long length = -1;
                try {
                    assetFd = assetManager.openFd(assetPath);
                    inputStream = assetFd.createInputStream();
                    length = assetFd.getLength();
                } catch (FileNotFoundException e) {
                    // Will occur if the file is compressed.
                    inputStream = assetManager.open(assetPath);
                }
                String mimeType = getMimeTypeFromPath(assetPath);
                return new OpenForReadResult(uri, inputStream, mimeType, length, assetFd);
            }
            case URI_TYPE_CONTENT:
            case URI_TYPE_RESOURCE: {
                String mimeType = contentResolver.getType(uri);
                AssetFileDescriptor assetFd = contentResolver.openAssetFileDescriptor(uri, "r");
                InputStream inputStream = assetFd.createInputStream();
                long length = assetFd.getLength();
                return new OpenForReadResult(uri, inputStream, mimeType, length, assetFd);
            }
            case URI_TYPE_DATA: {
                OpenForReadResult ret = readDataUri(uri);
                if (ret == null) {
                    break;
                }
                return ret;
            }
            case URI_TYPE_HTTP:
            case URI_TYPE_HTTPS: {
                HttpURLConnection conn = httpClient.open(new URL(uri.toString()));
                conn.setDoInput(true);
                String mimeType = conn.getHeaderField("Content-Type");
                int length = conn.getContentLength();
                InputStream inputStream = conn.getInputStream();
                return new OpenForReadResult(uri, inputStream, mimeType, length, null);
            }
        }
        throw new FileNotFoundException("URI not supported by CordovaResourceApi: " + uri);
    }

    public OutputStream openOutputStream(Uri uri) throws IOException {
        return openOutputStream(uri, false);
    }

    /**
     * Opens a stream to the given URI.
     * @return Never returns null.
     * @throws Throws an InvalidArgumentException for relative URIs. Relative URIs should be
     *     resolved before being passed into this function.
     * @throws Throws an IOException if the URI cannot be opened.
     */
    public OutputStream openOutputStream(Uri uri, boolean append) throws IOException {
        assertBackgroundThread();
        switch (getUriType(uri)) {
            case URI_TYPE_FILE: {
                File localFile = new File(uri.getPath());
                File parent = localFile.getParentFile();
                if (parent != null) {
                    parent.mkdirs();
                }
                return new FileOutputStream(localFile, append);
            }
            case URI_TYPE_CONTENT:
            case URI_TYPE_RESOURCE: {
                AssetFileDescriptor assetFd = contentResolver.openAssetFileDescriptor(uri, append ? "wa" : "w");
                return assetFd.createOutputStream();
            }
        }
        throw new FileNotFoundException("URI not supported by CordovaResourceApi: " + uri);
    }
    
    public HttpURLConnection createHttpConnection(Uri uri) throws IOException {
        assertBackgroundThread();
        return httpClient.open(new URL(uri.toString()));
    }
    
    // Copies the input to the output in the most efficient manner possible.
    // Closes both streams.
    public void copyResource(OpenForReadResult input, OutputStream outputStream) throws IOException {
        assertBackgroundThread();
        try {
            InputStream inputStream = input.inputStream;
            if (inputStream instanceof FileInputStream && outputStream instanceof FileOutputStream) {
                FileChannel inChannel = ((FileInputStream)input.inputStream).getChannel();
                FileChannel outChannel = ((FileOutputStream)outputStream).getChannel();
                long offset = 0;
                long length = input.length;
                if (input.assetFd != null) {
                    offset = input.assetFd.getStartOffset();
                }
                outChannel.transferFrom(inChannel, offset, length);
            } else {
                final int BUFFER_SIZE = 8192;
                byte[] buffer = new byte[BUFFER_SIZE];
                
                for (;;) {
                    int bytesRead = inputStream.read(buffer, 0, BUFFER_SIZE);
                    
                    if (bytesRead <= 0) {
                        break;
                    }
                    outputStream.write(buffer, 0, bytesRead);
                }
            }            
        } finally {
            input.inputStream.close();
            if (outputStream != null) {
                outputStream.close();
            }
        }
    }

    public void copyResource(Uri sourceUri, OutputStream outputStream) throws IOException {
        copyResource(openForRead(sourceUri), outputStream);
    }

    // Added in 3.5.0.
    public void copyResource(Uri sourceUri, Uri dstUri) throws IOException {
        copyResource(openForRead(sourceUri), openOutputStream(dstUri));
    }
    
    private void assertBackgroundThread() {
        if (threadCheckingEnabled) {
            Thread curThread = Thread.currentThread();
            if (curThread == Looper.getMainLooper().getThread()) {
                throw new IllegalStateException("Do not perform IO operations on the UI thread. Use CordovaInterface.getThreadPool() instead.");
            }
            if (curThread == jsThread) {
                throw new IllegalStateException("Tried to perform an IO operation on the WebCore thread. Use CordovaInterface.getThreadPool() instead.");
            }
        }
    }
    
    private String getDataUriMimeType(Uri uri) {
        String uriAsString = uri.getSchemeSpecificPart();
        int commaPos = uriAsString.indexOf(',');
        if (commaPos == -1) {
            return null;
        }
        String[] mimeParts = uriAsString.substring(0, commaPos).split(";");
        if (mimeParts.length > 0) {
            return mimeParts[0];
        }
        return null;
    }

    private OpenForReadResult readDataUri(Uri uri) {
        String uriAsString = uri.getSchemeSpecificPart();
        int commaPos = uriAsString.indexOf(',');
        if (commaPos == -1) {
            return null;
        }
        String[] mimeParts = uriAsString.substring(0, commaPos).split(";");
        String contentType = null;
        boolean base64 = false;
        if (mimeParts.length > 0) {
            contentType = mimeParts[0];
        }
        for (int i = 1; i < mimeParts.length; ++i) {
            if ("base64".equalsIgnoreCase(mimeParts[i])) {
                base64 = true;
            }
        }
        String dataPartAsString = uriAsString.substring(commaPos + 1);
        byte[] data = base64 ? Base64.decode(dataPartAsString, Base64.DEFAULT) : EncodingUtils.getBytes(dataPartAsString, "UTF-8");
        InputStream inputStream = new ByteArrayInputStream(data);
        return new OpenForReadResult(uri, inputStream, contentType, data.length, null);
    }
    
    private static void assertNonRelative(Uri uri) {
        if (!uri.isAbsolute()) {
            throw new IllegalArgumentException("Relative URIs are not supported.");
        }
    }
    
    public static final class OpenForReadResult {
        public final Uri uri;
        public final InputStream inputStream;
        public final String mimeType;
        public final long length;
        public final AssetFileDescriptor assetFd;
        
        OpenForReadResult(Uri uri, InputStream inputStream, String mimeType, long length, AssetFileDescriptor assetFd) {
            this.uri = uri;
            this.inputStream = inputStream;
            this.mimeType = mimeType;
            this.length = length;
            this.assetFd = assetFd;
        }
    }
}


File: platforms/android/CordovaLib/src/org/apache/cordova/CordovaUriHelper.java
/*
       Licensed to the Apache Software Foundation (ASF) under one
       or more contributor license agreements.  See the NOTICE file
       distributed with this work for additional information
       regarding copyright ownership.  The ASF licenses this file
       to you under the Apache License, Version 2.0 (the
       "License"); you may not use this file except in compliance
       with the License.  You may obtain a copy of the License at

         http://www.apache.org/licenses/LICENSE-2.0

       Unless required by applicable law or agreed to in writing,
       software distributed under the License is distributed on an
       "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY
       KIND, either express or implied.  See the License for the
       specific language governing permissions and limitations
       under the License.
*/

package org.apache.cordova;

import android.annotation.TargetApi;
import android.content.Intent;
import android.net.Uri;
import android.os.Build;
import android.webkit.WebView;

class CordovaUriHelper {
    
    private static final String TAG = "CordovaUriHelper";
    
    private CordovaWebView appView;
    private CordovaInterface cordova;
    
    CordovaUriHelper(CordovaInterface cdv, CordovaWebView webView)
    {
        appView = webView;
        cordova = cdv;
    }
    
    /**
     * Give the host application a chance to take over the control when a new url
     * is about to be loaded in the current WebView.
     *
     * @param view          The WebView that is initiating the callback.
     * @param url           The url to be loaded.
     * @return              true to override, false for default behavior
     */
    @TargetApi(Build.VERSION_CODES.ICE_CREAM_SANDWICH_MR1)
    boolean shouldOverrideUrlLoading(WebView view, String url) {
        // Give plugins the chance to handle the url
        if (this.appView.pluginManager.onOverrideUrlLoading(url)) {
            // Do nothing other than what the plugins wanted.
            // If any returned true, then the request was handled.
            return true;
        }
        else if(url.startsWith("file://") | url.startsWith("data:"))
        {
            //This directory on WebKit/Blink based webviews contains SQLite databases!
            //DON'T CHANGE THIS UNLESS YOU KNOW WHAT YOU'RE DOING!
            return url.contains("app_webview");
        }
        else if (appView.getWhitelist().isUrlWhiteListed(url)) {
            // Allow internal navigation
            return false;
        }
        else if (appView.getExternalWhitelist().isUrlWhiteListed(url))
        {
            try {
                Intent intent = new Intent(Intent.ACTION_VIEW);
                intent.setData(Uri.parse(url));
                intent.addCategory(Intent.CATEGORY_BROWSABLE);
                intent.setComponent(null);
                if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.ICE_CREAM_SANDWICH_MR1) {
                    intent.setSelector(null);
                }
                this.cordova.getActivity().startActivity(intent);
                return true;
            } catch (android.content.ActivityNotFoundException e) {
                LOG.e(TAG, "Error loading url " + url, e);
            }
        }
        // Intercept the request and do nothing with it -- block it
        return true;
    }
}


File: platforms/android/CordovaLib/src/org/apache/cordova/CordovaWebView.java
/*
       Licensed to the Apache Software Foundation (ASF) under one
       or more contributor license agreements.  See the NOTICE file
       distributed with this work for additional information
       regarding copyright ownership.  The ASF licenses this file
       to you under the Apache License, Version 2.0 (the
       "License"); you may not use this file except in compliance
       with the License.  You may obtain a copy of the License at

         http://www.apache.org/licenses/LICENSE-2.0

       Unless required by applicable law or agreed to in writing,
       software distributed under the License is distributed on an
       "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY
       KIND, either express or implied.  See the License for the
       specific language governing permissions and limitations
       under the License.
*/

package org.apache.cordova;

import java.lang.reflect.InvocationTargetException;
import java.lang.reflect.Method;
import java.util.HashMap;
import java.util.HashSet;
import java.util.List;
import java.util.Locale;

import android.annotation.SuppressLint;
import android.annotation.TargetApi;
import android.content.BroadcastReceiver;
import android.content.Context;
import android.content.Intent;
import android.content.IntentFilter;
import android.content.pm.ApplicationInfo;
import android.net.Uri;
import android.os.Build;
import android.os.Bundle;
import android.util.AttributeSet;
import android.util.Log;
import android.view.Gravity;
import android.view.KeyEvent;
import android.view.View;
import android.view.ViewGroup;
import android.view.inputmethod.InputMethodManager;
import android.webkit.WebBackForwardList;
import android.webkit.WebHistoryItem;
import android.webkit.WebChromeClient;
import android.webkit.WebSettings;
import android.webkit.WebView;
import android.webkit.WebSettings.LayoutAlgorithm;
import android.webkit.WebViewClient;
import android.webkit.CookieManager;
import android.widget.FrameLayout;

/*
 * This class is our web view.
 *
 * @see <a href="http://developer.android.com/guide/webapps/webview.html">WebView guide</a>
 * @see <a href="http://developer.android.com/reference/android/webkit/WebView.html">WebView</a>
 */
public class CordovaWebView extends WebView {

    public static final String TAG = "CordovaWebView";
    public static final String CORDOVA_VERSION = "3.7.1";

    private HashSet<Integer> boundKeyCodes = new HashSet<Integer>();

    public PluginManager pluginManager;
    private boolean paused;

    private BroadcastReceiver receiver;


    /** Activities and other important classes **/
    private CordovaInterface cordova;
    CordovaWebViewClient viewClient;
    private CordovaChromeClient chromeClient;

    // Flag to track that a loadUrl timeout occurred
    int loadUrlTimeout = 0;

    private long lastMenuEventTime = 0;

    CordovaBridge bridge;

    /** custom view created by the browser (a video player for example) */
    private View mCustomView;
    private WebChromeClient.CustomViewCallback mCustomViewCallback;

    private CordovaResourceApi resourceApi;
    private Whitelist internalWhitelist;
    private Whitelist externalWhitelist;

    // The URL passed to loadUrl(), not necessarily the URL of the current page.
    String loadedUrl;
    private CordovaPreferences preferences;
    private App appPlugin;

    class ActivityResult {
        
        int request;
        int result;
        Intent incoming;
        
        public ActivityResult(int req, int res, Intent intent) {
            request = req;
            result = res;
            incoming = intent;
        }

        
    }
    
    static final FrameLayout.LayoutParams COVER_SCREEN_GRAVITY_CENTER =
            new FrameLayout.LayoutParams(
            ViewGroup.LayoutParams.MATCH_PARENT,
            ViewGroup.LayoutParams.MATCH_PARENT,
            Gravity.CENTER);
    
    public CordovaWebView(Context context) {
        this(context, null);
    }

    public CordovaWebView(Context context, AttributeSet attrs) {
        super(context, attrs);
    }

    @Deprecated
    public CordovaWebView(Context context, AttributeSet attrs, int defStyle) {
        super(context, attrs, defStyle);
    }

    @TargetApi(11)
    @Deprecated
    public CordovaWebView(Context context, AttributeSet attrs, int defStyle, boolean privateBrowsing) {
        super(context, attrs, defStyle, privateBrowsing);
    }

    // Use two-phase init so that the control will work with XML layouts.
    public void init(CordovaInterface cordova, CordovaWebViewClient webViewClient, CordovaChromeClient webChromeClient,
            List<PluginEntry> pluginEntries, Whitelist internalWhitelist, Whitelist externalWhitelist,
            CordovaPreferences preferences) {
        if (this.cordova != null) {
            throw new IllegalStateException();
        }
        this.cordova = cordova;
        this.viewClient = webViewClient;
        this.chromeClient = webChromeClient;
        this.internalWhitelist = internalWhitelist;
        this.externalWhitelist = externalWhitelist;
        this.preferences = preferences;
        super.setWebChromeClient(webChromeClient);
        super.setWebViewClient(webViewClient);

        pluginManager = new PluginManager(this, this.cordova, pluginEntries);
        bridge = new CordovaBridge(pluginManager, new NativeToJsMessageQueue(this, cordova), this.cordova.getActivity().getPackageName());
        resourceApi = new CordovaResourceApi(this.getContext(), pluginManager);

        pluginManager.addService(App.PLUGIN_NAME, "org.apache.cordova.App");
        // This will be removed in 4.0.x in favour of the plugin not being bundled.
        pluginManager.addService(new PluginEntry("SplashScreenInternal", "org.apache.cordova.SplashScreenInternal", true));
        pluginManager.init();
        initWebViewSettings();
        exposeJsInterface();
    }

    @SuppressWarnings("deprecation")
    private void initIfNecessary() {
        if (pluginManager == null) {
            Log.w(TAG, "CordovaWebView.init() was not called. This will soon be required.");
            // Before the refactor to a two-phase init, the Context needed to implement CordovaInterface. 
            CordovaInterface cdv = (CordovaInterface)getContext();
            if (!Config.isInitialized()) {
                Config.init(cdv.getActivity());
            }
            init(cdv, makeWebViewClient(cdv), makeWebChromeClient(cdv), Config.getPluginEntries(), Config.getWhitelist(), Config.getExternalWhitelist(), Config.getPreferences());
        }
    }

    @SuppressLint("SetJavaScriptEnabled")
    @SuppressWarnings("deprecation")
    private void initWebViewSettings() {
        this.setInitialScale(0);
        this.setVerticalScrollBarEnabled(false);
        // TODO: The Activity is the one that should call requestFocus().
        if (shouldRequestFocusOnInit()) {
			this.requestFocusFromTouch();
		}
		// Enable JavaScript
        WebSettings settings = this.getSettings();
        settings.setJavaScriptEnabled(true);
        settings.setJavaScriptCanOpenWindowsAutomatically(true);
        settings.setLayoutAlgorithm(LayoutAlgorithm.NORMAL);

        // Enable third-party cookies if on Lolipop. TODO: Make this configurable
        if(Build.VERSION.SDK_INT >= Build.VERSION_CODES.LOLLIPOP)
        {
            CookieManager cookieManager = CookieManager.getInstance();
            cookieManager.setAcceptThirdPartyCookies(this, true);
        }

        // Set the nav dump for HTC 2.x devices (disabling for ICS, deprecated entirely for Jellybean 4.2)
        try {
            Method gingerbread_getMethod =  WebSettings.class.getMethod("setNavDump", new Class[] { boolean.class });
            
            String manufacturer = android.os.Build.MANUFACTURER;
            Log.d(TAG, "CordovaWebView is running on device made by: " + manufacturer);
            if(android.os.Build.VERSION.SDK_INT < android.os.Build.VERSION_CODES.HONEYCOMB &&
                    android.os.Build.MANUFACTURER.contains("HTC"))
            {
                gingerbread_getMethod.invoke(settings, true);
            }
        } catch (NoSuchMethodException e) {
            Log.d(TAG, "We are on a modern version of Android, we will deprecate HTC 2.3 devices in 2.8");
        } catch (IllegalArgumentException e) {
            Log.d(TAG, "Doing the NavDump failed with bad arguments");
        } catch (IllegalAccessException e) {
            Log.d(TAG, "This should never happen: IllegalAccessException means this isn't Android anymore");
        } catch (InvocationTargetException e) {
            Log.d(TAG, "This should never happen: InvocationTargetException means this isn't Android anymore.");
        }

        //We don't save any form data in the application
        settings.setSaveFormData(false);
        settings.setSavePassword(false);
        
        // Jellybean rightfully tried to lock this down. Too bad they didn't give us a whitelist
        // while we do this
        if (android.os.Build.VERSION.SDK_INT >= android.os.Build.VERSION_CODES.JELLY_BEAN) {
            Level16Apis.enableUniversalAccess(settings);
        }
        if (android.os.Build.VERSION.SDK_INT >= android.os.Build.VERSION_CODES.JELLY_BEAN_MR1) {
            Level17Apis.setMediaPlaybackRequiresUserGesture(settings, false);
        }
        // Enable database
        // We keep this disabled because we use or shim to get around DOM_EXCEPTION_ERROR_16
        String databasePath = getContext().getApplicationContext().getDir("database", Context.MODE_PRIVATE).getPath();
        settings.setDatabaseEnabled(true);
        settings.setDatabasePath(databasePath);
        
        
        //Determine whether we're in debug or release mode, and turn on Debugging!
        ApplicationInfo appInfo = getContext().getApplicationContext().getApplicationInfo();
        if ((appInfo.flags & ApplicationInfo.FLAG_DEBUGGABLE) != 0 &&
            android.os.Build.VERSION.SDK_INT >= android.os.Build.VERSION_CODES.KITKAT) {
            enableRemoteDebugging();
        }
        
        settings.setGeolocationDatabasePath(databasePath);

        // Enable DOM storage
        settings.setDomStorageEnabled(true);

        // Enable built-in geolocation
        settings.setGeolocationEnabled(true);
        
        // Enable AppCache
        // Fix for CB-2282
        settings.setAppCacheMaxSize(5 * 1048576);
        settings.setAppCachePath(databasePath);
        settings.setAppCacheEnabled(true);
        
        // Fix for CB-1405
        // Google issue 4641
        settings.getUserAgentString();
        
        IntentFilter intentFilter = new IntentFilter();
        intentFilter.addAction(Intent.ACTION_CONFIGURATION_CHANGED);
        if (this.receiver == null) {
            this.receiver = new BroadcastReceiver() {
                @Override
                public void onReceive(Context context, Intent intent) {
                    getSettings().getUserAgentString();
                }
            };
            getContext().registerReceiver(this.receiver, intentFilter);
        }
        // end CB-1405
    }

    @TargetApi(Build.VERSION_CODES.KITKAT)
    private void enableRemoteDebugging() {
        try {
            WebView.setWebContentsDebuggingEnabled(true);
        } catch (IllegalArgumentException e) {
            Log.d(TAG, "You have one job! To turn on Remote Web Debugging! YOU HAVE FAILED! ");
            e.printStackTrace();
        }
    }

    public CordovaChromeClient makeWebChromeClient(CordovaInterface cordova) {
        return new CordovaChromeClient(cordova, this);
    }

    public CordovaWebViewClient makeWebViewClient(CordovaInterface cordova) {
        if (android.os.Build.VERSION.SDK_INT < android.os.Build.VERSION_CODES.ICE_CREAM_SANDWICH) {
            return new CordovaWebViewClient(cordova, this);
        }
        return new IceCreamCordovaWebViewClient(cordova, this);
    }

	/**
	 * Override this method to decide whether or not you need to request the
	 * focus when your application start
	 * 
	 * @return true unless this method is overriden to return a different value
	 */
    protected boolean shouldRequestFocusOnInit() {
		return true;
	}

    private void exposeJsInterface() {
        if ((Build.VERSION.SDK_INT < Build.VERSION_CODES.JELLY_BEAN_MR1)) {
            Log.i(TAG, "Disabled addJavascriptInterface() bridge since Android version is old.");
            // Bug being that Java Strings do not get converted to JS strings automatically.
            // This isn't hard to work-around on the JS side, but it's easier to just
            // use the prompt bridge instead.
            return;            
        } 
        this.addJavascriptInterface(new ExposedJsApi(bridge), "_cordovaNative");
    }

    @Override
    public void setWebViewClient(WebViewClient client) {
        this.viewClient = (CordovaWebViewClient)client;
        super.setWebViewClient(client);
    }

    @Override
    public void setWebChromeClient(WebChromeClient client) {
        this.chromeClient = (CordovaChromeClient)client;
        super.setWebChromeClient(client);
    }
    
    public CordovaChromeClient getWebChromeClient() {
        return this.chromeClient;
    }

    
    public Whitelist getWhitelist() {
        return this.internalWhitelist;
    }

    public Whitelist getExternalWhitelist() {
        return this.externalWhitelist;
    }

    /**
     * Load the url into the webview.
     *
     * @param url
     */
    @Override
    public void loadUrl(String url) {
        if (url.equals("about:blank") || url.startsWith("javascript:")) {
            this.loadUrlNow(url);
        }
        else {
            this.loadUrlIntoView(url);
        }
    }

    /**
     * Load the url into the webview after waiting for period of time.
     * This is used to display the splashscreen for certain amount of time.
     *
     * @param url
     * @param time              The number of ms to wait before loading webview
     */
    @Deprecated
    public void loadUrl(final String url, int time) {
        if(url == null)
        {
            this.loadUrlIntoView(Config.getStartUrl());
        }
        else
        {
            this.loadUrlIntoView(url);
        }
    }

    public void loadUrlIntoView(final String url) {
        loadUrlIntoView(url, true);
    }

    /**
     * Load the url into the webview.
     *
     * @param url
     */
    public void loadUrlIntoView(final String url, boolean recreatePlugins) {
        LOG.d(TAG, ">>> loadUrl(" + url + ")");

        initIfNecessary();

        if (recreatePlugins) {
            // Don't re-initialize on first load.
            if (loadedUrl != null) {
                this.pluginManager.init();
            }
            this.loadedUrl = url;
        }

        // Create a timeout timer for loadUrl
        final CordovaWebView me = this;
        final int currentLoadUrlTimeout = me.loadUrlTimeout;
        final int loadUrlTimeoutValue = Integer.parseInt(this.getProperty("LoadUrlTimeoutValue", "20000"));

        // Timeout error method
        final Runnable loadError = new Runnable() {
            public void run() {
                me.stopLoading();
                LOG.e(TAG, "CordovaWebView: TIMEOUT ERROR!");
                if (viewClient != null) {
                    viewClient.onReceivedError(me, -6, "The connection to the server was unsuccessful.", url);
                }
            }
        };

        // Timeout timer method
        final Runnable timeoutCheck = new Runnable() {
            public void run() {
                try {
                    synchronized (this) {
                        wait(loadUrlTimeoutValue);
                    }
                } catch (InterruptedException e) {
                    e.printStackTrace();
                }

                // If timeout, then stop loading and handle error
                if (me.loadUrlTimeout == currentLoadUrlTimeout) {
                    me.cordova.getActivity().runOnUiThread(loadError);
                }
            }
        };

        // Load url
        this.cordova.getActivity().runOnUiThread(new Runnable() {
            public void run() {
                cordova.getThreadPool().execute(timeoutCheck);
                me.loadUrlNow(url);
            }
        });
    }

    /**
     * Load URL in webview.
     *
     * @param url
     */
    void loadUrlNow(String url) {
        if (LOG.isLoggable(LOG.DEBUG) && !url.startsWith("javascript:")) {
            LOG.d(TAG, ">>> loadUrlNow()");
        }
        if (url.startsWith("file://") || url.startsWith("javascript:") || url.startsWith("about:") || internalWhitelist.isUrlWhiteListed(url)) {
            super.loadUrl(url);
        }
    }

    /**
     * Load the url into the webview after waiting for period of time.
     * This is used to display the splashscreen for certain amount of time.
     *
     * @param url
     * @param time              The number of ms to wait before loading webview
     */
    public void loadUrlIntoView(final String url, final int time) {

        // If not first page of app, then load immediately
        // Add support for browser history if we use it.
        if ((url.startsWith("javascript:")) || this.canGoBack()) {
        }

        // If first page, then show splashscreen
        else {

            LOG.d(TAG, "loadUrlIntoView(%s, %d)", url, time);
        }

        // Load url
        this.loadUrlIntoView(url);
    }
    
    @Override
    public void stopLoading() {
        viewClient.isCurrentlyLoading = false;
        super.stopLoading();
    }
    
    public void onScrollChanged(int l, int t, int oldl, int oldt)
    {
        super.onScrollChanged(l, t, oldl, oldt);
        //We should post a message that the scroll changed
        ScrollEvent myEvent = new ScrollEvent(l, t, oldl, oldt, this);
        this.postMessage("onScrollChanged", myEvent);
    }
    
    /**
     * Send JavaScript statement back to JavaScript.
     * Deprecated (https://issues.apache.org/jira/browse/CB-6851)
     * Instead of executing snippets of JS, you should use the exec bridge
     * to create a Java->JS communication channel.
     * To do this:
     * 1. Within plugin.xml (to have your JS run before deviceready):
     *    <js-module><runs/></js-module>
     * 2. Within your .js (call exec on start-up):
     *    require('cordova/channel').onCordovaReady.subscribe(function() {
     *      require('cordova/exec')(win, null, 'Plugin', 'method', []);
     *      function win(message) {
     *        ... process message from java here ...
     *      }
     *    });
     * 3. Within your .java:
     *    PluginResult dataResult = new PluginResult(PluginResult.Status.OK, CODE);
     *    dataResult.setKeepCallback(true);
     *    savedCallbackContext.sendPluginResult(dataResult);
     */
    @Deprecated
    public void sendJavascript(String statement) {
        this.bridge.getMessageQueue().addJavaScript(statement);
    }

    /**
     * Send a plugin result back to JavaScript.
     * (This is a convenience method)
     *
     * @param result
     * @param callbackId
     */
    public void sendPluginResult(PluginResult result, String callbackId) {
        this.bridge.getMessageQueue().addPluginResult(result, callbackId);
    }

    /**
     * Send a message to all plugins.
     *
     * @param id            The message id
     * @param data          The message data
     */
    public void postMessage(String id, Object data) {
        if (this.pluginManager != null) {
            this.pluginManager.postMessage(id, data);
        }
    }


    /**
     * Go to previous page in history.  (We manage our own history)
     *
     * @return true if we went back, false if we are already at top
     */
    public boolean backHistory() {
        // Check webview first to see if there is a history
        // This is needed to support curPage#diffLink, since they are added to appView's history, but not our history url array (JQMobile behavior)
        if (super.canGoBack()) {
            super.goBack();
            return true;
        }
        return false;
    }


    /**
     * Load the specified URL in the Cordova webview or a new browser instance.
     *
     * NOTE: If openExternal is false, only URLs listed in whitelist can be loaded.
     *
     * @param url           The url to load.
     * @param openExternal  Load url in browser instead of Cordova webview.
     * @param clearHistory  Clear the history stack, so new page becomes top of history
     * @param params        Parameters for new app
     */
    public void showWebPage(String url, boolean openExternal, boolean clearHistory, HashMap<String, Object> params) {
        LOG.d(TAG, "showWebPage(%s, %b, %b, HashMap", url, openExternal, clearHistory);

        // If clearing history
        if (clearHistory) {
            this.clearHistory();
        }

        // If loading into our webview
        if (!openExternal) {

            // Make sure url is in whitelist
            if (url.startsWith("file://") || internalWhitelist.isUrlWhiteListed(url)) {
                // TODO: What about params?
                // Load new URL
                this.loadUrl(url);
                return;
            }
            // Load in default viewer if not
            LOG.w(TAG, "showWebPage: Cannot load URL into webview since it is not in white list.  Loading into browser instead. (URL=" + url + ")");
        }
        try {
            // Omitting the MIME type for file: URLs causes "No Activity found to handle Intent".
            // Adding the MIME type to http: URLs causes them to not be handled by the downloader.
            Intent intent = new Intent(Intent.ACTION_VIEW);
            Uri uri = Uri.parse(url);
            if ("file".equals(uri.getScheme())) {
                intent.setDataAndType(uri, resourceApi.getMimeType(uri));
            } else {
                intent.setData(uri);
            }
            cordova.getActivity().startActivity(intent);
        } catch (android.content.ActivityNotFoundException e) {
            LOG.e(TAG, "Error loading url " + url, e);
        }
    }

    /**
     * Get string property for activity.
     *
     * @param name
     * @param defaultValue
     * @return the String value for the named property
     */
    public String getProperty(String name, String defaultValue) {
        Bundle bundle = this.cordova.getActivity().getIntent().getExtras();
        if (bundle == null) {
            return defaultValue;
        }
        name = name.toLowerCase(Locale.getDefault());
        Object p = bundle.get(name);
        if (p == null) {
            return defaultValue;
        }
        return p.toString();
    }

    @Override
    public boolean onKeyDown(int keyCode, KeyEvent event)
    {
        if(boundKeyCodes.contains(keyCode))
        {
            if (keyCode == KeyEvent.KEYCODE_VOLUME_DOWN) {
                sendJavascriptEvent("volumedownbutton");
                return true;
            }
            // If volumeup key
            else if (keyCode == KeyEvent.KEYCODE_VOLUME_UP) {
                sendJavascriptEvent("volumeupbutton");
                return true;
            }
            else
            {
                return super.onKeyDown(keyCode, event);
            }
        }
        else if(keyCode == KeyEvent.KEYCODE_BACK)
        {
            return !(this.startOfHistory()) || isButtonPlumbedToJs(KeyEvent.KEYCODE_BACK);
        }
        else if(keyCode == KeyEvent.KEYCODE_MENU)
        {
            //How did we get here?  Is there a childView?
            View childView = this.getFocusedChild();
            if(childView != null)
            {
                //Make sure we close the keyboard if it's present
                InputMethodManager imm = (InputMethodManager) cordova.getActivity().getSystemService(Context.INPUT_METHOD_SERVICE);
                imm.hideSoftInputFromWindow(childView.getWindowToken(), 0);
                cordova.getActivity().openOptionsMenu();
                return true;
            } else {
                return super.onKeyDown(keyCode, event);
            }
        }
        return super.onKeyDown(keyCode, event);
    }

    @Override
    public boolean onKeyUp(int keyCode, KeyEvent event)
    {
        // If back key
        if (keyCode == KeyEvent.KEYCODE_BACK) {
            // A custom view is currently displayed  (e.g. playing a video)
            if(mCustomView != null) {
                this.hideCustomView();
                return true;
            } else {
                // The webview is currently displayed
                // If back key is bound, then send event to JavaScript
                if (isButtonPlumbedToJs(KeyEvent.KEYCODE_BACK)) {
                    sendJavascriptEvent("backbutton");
                    return true;
                } else {
                    // If not bound
                    // Go to previous page in webview if it is possible to go back
                    if (this.backHistory()) {
                        return true;
                    }
                    // If not, then invoke default behavior
                }
            }
        }
        // Legacy
        else if (keyCode == KeyEvent.KEYCODE_MENU) {
            if (this.lastMenuEventTime < event.getEventTime()) {
                sendJavascriptEvent("menubutton");
            }
            this.lastMenuEventTime = event.getEventTime();
            return super.onKeyUp(keyCode, event);
        }
        // If search key
        else if (keyCode == KeyEvent.KEYCODE_SEARCH) {
            sendJavascriptEvent("searchbutton");
            return true;
        }

        //Does webkit change this behavior?
        return super.onKeyUp(keyCode, event);
    }

    private void sendJavascriptEvent(String event) {
        if (appPlugin == null) {
            appPlugin = (App)this.pluginManager.getPlugin(App.PLUGIN_NAME);
        }

        if (appPlugin == null) {
            LOG.w(TAG, "Unable to fire event without existing plugin");
            return;
        }
        appPlugin.fireJavascriptEvent(event);
    }

    public void setButtonPlumbedToJs(int keyCode, boolean override) {
        switch (keyCode) {
            case KeyEvent.KEYCODE_VOLUME_DOWN:
            case KeyEvent.KEYCODE_VOLUME_UP:
            case KeyEvent.KEYCODE_BACK:
                // TODO: Why are search and menu buttons handled separately?
                if (override) {
                    boundKeyCodes.add(keyCode);
                } else {
                    boundKeyCodes.remove(keyCode);
                }
                return;
            default:
                throw new IllegalArgumentException("Unsupported keycode: " + keyCode);
        }
    }

    @Deprecated // Use setButtonPlumbedToJs() instead.
    public void bindButton(boolean override)
    {
        setButtonPlumbedToJs(KeyEvent.KEYCODE_BACK, override);
    }

    @Deprecated // Use setButtonPlumbedToJs() instead.
    public void bindButton(String button, boolean override) {
        if (button.compareTo("volumeup")==0) {
            setButtonPlumbedToJs(KeyEvent.KEYCODE_VOLUME_UP, override);
        }
        else if (button.compareTo("volumedown")==0) {
            setButtonPlumbedToJs(KeyEvent.KEYCODE_VOLUME_DOWN, override);
        }
    }

    @Deprecated // Use setButtonPlumbedToJs() instead.
    public void bindButton(int keyCode, boolean keyDown, boolean override) {
        setButtonPlumbedToJs(keyCode, override);
    }

    @Deprecated // Use isButtonPlumbedToJs
    public boolean isBackButtonBound()
    {
        return isButtonPlumbedToJs(KeyEvent.KEYCODE_BACK);
    }

    public boolean isButtonPlumbedToJs(int keyCode)
    {
        return boundKeyCodes.contains(keyCode);
    }

    public void handlePause(boolean keepRunning)
    {
        LOG.d(TAG, "Handle the pause");
        // Send pause event to JavaScript
        sendJavascriptEvent("pause");

        // Forward to plugins
        if (this.pluginManager != null) {
            this.pluginManager.onPause(keepRunning);
        }

        // If app doesn't want to run in background
        if (!keepRunning) {
            // Pause JavaScript timers (including setInterval)
            this.pauseTimers();
        }
        paused = true;
   
    }
    
    public void handleResume(boolean keepRunning, boolean activityResultKeepRunning)
    {
        sendJavascriptEvent("resume");

        // Forward to plugins
        if (this.pluginManager != null) {
            this.pluginManager.onResume(keepRunning);
        }

        // Resume JavaScript timers (including setInterval)
        this.resumeTimers();
        paused = false;
    }
    
    public void handleDestroy()
    {
        // Cancel pending timeout timer.
        loadUrlTimeout++;

        // Load blank page so that JavaScript onunload is called
        this.loadUrl("about:blank");
        
        //Remove last AlertDialog
        this.chromeClient.destroyLastDialog();

        // Forward to plugins
        if (this.pluginManager != null) {
            this.pluginManager.onDestroy();
        }
        
        // unregister the receiver
        if (this.receiver != null) {
            try {
                getContext().unregisterReceiver(this.receiver);
            } catch (Exception e) {
                Log.e(TAG, "Error unregistering configuration receiver: " + e.getMessage(), e);
            }
        }
    }
    
    public void onNewIntent(Intent intent)
    {
        //Forward to plugins
        if (this.pluginManager != null) {
            this.pluginManager.onNewIntent(intent);
        }
    }
    
    public boolean isPaused()
    {
        return paused;
    }

    @Deprecated // This never did anything.
    public boolean hadKeyEvent() {
        return false;
    }

    // Wrapping these functions in their own class prevents warnings in adb like:
    // VFY: unable to resolve virtual method 285: Landroid/webkit/WebSettings;.setAllowUniversalAccessFromFileURLs
    @TargetApi(16)
    private static final class Level16Apis {
        static void enableUniversalAccess(WebSettings settings) {
            settings.setAllowUniversalAccessFromFileURLs(true);
        }
    }

    @TargetApi(17)
    private static final class Level17Apis {
        static void setMediaPlaybackRequiresUserGesture(WebSettings settings, boolean value) {
            settings.setMediaPlaybackRequiresUserGesture(value);
        }
    }

    public void printBackForwardList() {
        WebBackForwardList currentList = this.copyBackForwardList();
        int currentSize = currentList.getSize();
        for(int i = 0; i < currentSize; ++i)
        {
            WebHistoryItem item = currentList.getItemAtIndex(i);
            String url = item.getUrl();
            LOG.d(TAG, "The URL at index: " + Integer.toString(i) + " is " + url );
        }
    }
    
    
    //Can Go Back is BROKEN!
    public boolean startOfHistory()
    {
        WebBackForwardList currentList = this.copyBackForwardList();
        WebHistoryItem item = currentList.getItemAtIndex(0);
        if( item!=null){	// Null-fence in case they haven't called loadUrl yet (CB-2458)
	        String url = item.getUrl();
	        String currentUrl = this.getUrl();
	        LOG.d(TAG, "The current URL is: " + currentUrl);
	        LOG.d(TAG, "The URL at item 0 is: " + url);
	        return currentUrl.equals(url);
        }
        return false;
    }

    public void showCustomView(View view, WebChromeClient.CustomViewCallback callback) {
        // This code is adapted from the original Android Browser code, licensed under the Apache License, Version 2.0
        Log.d(TAG, "showing Custom View");
        // if a view already exists then immediately terminate the new one
        if (mCustomView != null) {
            callback.onCustomViewHidden();
            return;
        }
        
        // Store the view and its callback for later (to kill it properly)
        mCustomView = view;
        mCustomViewCallback = callback;
        
        // Add the custom view to its container.
        ViewGroup parent = (ViewGroup) this.getParent();
        parent.addView(view, COVER_SCREEN_GRAVITY_CENTER);
        
        // Hide the content view.
        this.setVisibility(View.GONE);
        
        // Finally show the custom view container.
        parent.setVisibility(View.VISIBLE);
        parent.bringToFront();
    }

    public void hideCustomView() {
        // This code is adapted from the original Android Browser code, licensed under the Apache License, Version 2.0
        Log.d(TAG, "Hiding Custom View");
        if (mCustomView == null) return;

        // Hide the custom view.
        mCustomView.setVisibility(View.GONE);
        
        // Remove the custom view from its container.
        ViewGroup parent = (ViewGroup) this.getParent();
        parent.removeView(mCustomView);
        mCustomView = null;
        mCustomViewCallback.onCustomViewHidden();
        
        // Show the content view.
        this.setVisibility(View.VISIBLE);
    }
    
    /**
     * if the video overlay is showing then we need to know 
     * as it effects back button handling
     * 
     * @return true if custom view is showing
     */
    public boolean isCustomViewShowing() {
        return mCustomView != null;
    }
    
    public WebBackForwardList restoreState(Bundle savedInstanceState)
    {
        WebBackForwardList myList = super.restoreState(savedInstanceState);
        Log.d(TAG, "WebView restoration crew now restoring!");
        //Initialize the plugin manager once more
        this.pluginManager.init();
        return myList;
    }

    @Deprecated // This never did anything
    public void storeResult(int requestCode, int resultCode, Intent intent) {
    }
    
    public CordovaResourceApi getResourceApi() {
        return resourceApi;
    }

    public CordovaPreferences getPreferences() {
        return preferences;
    }
}


File: platforms/android/CordovaLib/src/org/apache/cordova/CordovaWebViewClient.java
/*
       Licensed to the Apache Software Foundation (ASF) under one
       or more contributor license agreements.  See the NOTICE file
       distributed with this work for additional information
       regarding copyright ownership.  The ASF licenses this file
       to you under the Apache License, Version 2.0 (the
       "License"); you may not use this file except in compliance
       with the License.  You may obtain a copy of the License at

         http://www.apache.org/licenses/LICENSE-2.0

       Unless required by applicable law or agreed to in writing,
       software distributed under the License is distributed on an
       "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY
       KIND, either express or implied.  See the License for the
       specific language governing permissions and limitations
       under the License.
*/
package org.apache.cordova;

import java.util.Hashtable;

import org.apache.cordova.CordovaInterface;
import org.apache.cordova.LOG;
import org.json.JSONException;
import org.json.JSONObject;

import android.annotation.TargetApi;
import android.content.pm.ApplicationInfo;
import android.content.pm.PackageManager;
import android.content.pm.PackageManager.NameNotFoundException;
import android.graphics.Bitmap;
import android.net.http.SslError;
import android.view.View;
import android.webkit.ClientCertRequest;
import android.webkit.HttpAuthHandler;
import android.webkit.SslErrorHandler;
import android.webkit.WebView;
import android.webkit.WebViewClient;

/**
 * This class is the WebViewClient that implements callbacks for our web view.
 * The kind of callbacks that happen here are regarding the rendering of the
 * document instead of the chrome surrounding it, such as onPageStarted(), 
 * shouldOverrideUrlLoading(), etc. Related to but different than
 * CordovaChromeClient.
 *
 * @see <a href="http://developer.android.com/reference/android/webkit/WebViewClient.html">WebViewClient</a>
 * @see <a href="http://developer.android.com/guide/webapps/webview.html">WebView guide</a>
 * @see CordovaChromeClient
 * @see CordovaWebView
 */
public class CordovaWebViewClient extends WebViewClient {

	private static final String TAG = "CordovaWebViewClient";
    CordovaInterface cordova;
    CordovaWebView appView;
    CordovaUriHelper helper;
    private boolean doClearHistory = false;
    boolean isCurrentlyLoading;

    /** The authorization tokens. */
    private Hashtable<String, AuthenticationToken> authenticationTokens = new Hashtable<String, AuthenticationToken>();

    @Deprecated
    public CordovaWebViewClient(CordovaInterface cordova) {
        this.cordova = cordova;
    }

    /**
     * Constructor.
     *
     * @param cordova
     * @param view
     */
    public CordovaWebViewClient(CordovaInterface cordova, CordovaWebView view) {
        this.cordova = cordova;
        this.appView = view;
        helper = new CordovaUriHelper(cordova, view);
    }

    /**
     * Constructor.
     *
     * @param view
     */
    @Deprecated
    public void setWebView(CordovaWebView view) {
        this.appView = view;
        helper = new CordovaUriHelper(cordova, view);
    }

    /**
     * Give the host application a chance to take over the control when a new url
     * is about to be loaded in the current WebView.
     *
     * @param view          The WebView that is initiating the callback.
     * @param url           The url to be loaded.
     * @return              true to override, false for default behavior
     */
	@Override
    public boolean shouldOverrideUrlLoading(WebView view, String url) {
        return helper.shouldOverrideUrlLoading(view, url);
    }
    
    /**
     * On received http auth request.
     * The method reacts on all registered authentication tokens. There is one and only one authentication token for any host + realm combination
     *
     * @param view
     * @param handler
     * @param host
     * @param realm
     */
    @Override
    public void onReceivedHttpAuthRequest(WebView view, HttpAuthHandler handler, String host, String realm) {

        // Get the authentication token (if specified)
        AuthenticationToken token = this.getAuthenticationToken(host, realm);
        if (token != null) {
            handler.proceed(token.getUserName(), token.getPassword());
            return;
        }

        // Check if there is some plugin which can resolve this auth challenge
        PluginManager pluginManager = this.appView.pluginManager;
        if (pluginManager != null && pluginManager.onReceivedHttpAuthRequest(this.appView, new CordovaHttpAuthHandler(handler), host, realm)) {
            this.appView.loadUrlTimeout++;
            return;
        }

        // By default handle 401 like we'd normally do!
        super.onReceivedHttpAuthRequest(view, handler, host, realm);
    }
    
    /**
     * On received client cert request.
     * The method forwards the request to any running plugins before using the default implementation.
     *
     * @param view
     * @param request
     */
    @Override
    @TargetApi(21)
    public void onReceivedClientCertRequest (WebView view, ClientCertRequest request)
    {

        // Check if there is some plugin which can resolve this certificate request
        PluginManager pluginManager = this.appView.pluginManager;
        if (pluginManager != null && pluginManager.onReceivedClientCertRequest(this.appView, new CordovaClientCertRequest(request))) {
            this.appView.loadUrlTimeout++;
            return;
        }

        // By default pass to WebViewClient
        super.onReceivedClientCertRequest(view, request);
    }

    /**
     * Notify the host application that a page has started loading.
     * This method is called once for each main frame load so a page with iframes or framesets will call onPageStarted
     * one time for the main frame. This also means that onPageStarted will not be called when the contents of an
     * embedded frame changes, i.e. clicking a link whose target is an iframe.
     *
     * @param view          The webview initiating the callback.
     * @param url           The url of the page.
     */
    @Override
    public void onPageStarted(WebView view, String url, Bitmap favicon) {
        super.onPageStarted(view, url, favicon);
        isCurrentlyLoading = true;
        LOG.d(TAG, "onPageStarted(" + url + ")");
        // Flush stale messages.
        this.appView.bridge.reset(url);

        // Broadcast message that page has loaded
        this.appView.postMessage("onPageStarted", url);

        // Notify all plugins of the navigation, so they can clean up if necessary.
        if (this.appView.pluginManager != null) {
            this.appView.pluginManager.onReset();
        }
    }

    /**
     * Notify the host application that a page has finished loading.
     * This method is called only for main frame. When onPageFinished() is called, the rendering picture may not be updated yet.
     *
     *
     * @param view          The webview initiating the callback.
     * @param url           The url of the page.
     */
    @Override
    public void onPageFinished(WebView view, String url) {
        super.onPageFinished(view, url);
        // Ignore excessive calls, if url is not about:blank (CB-8317).
        if (!isCurrentlyLoading && !url.startsWith("about:")) {
            return;
        }
        isCurrentlyLoading = false;
        LOG.d(TAG, "onPageFinished(" + url + ")");

        /**
         * Because of a timing issue we need to clear this history in onPageFinished as well as
         * onPageStarted. However we only want to do this if the doClearHistory boolean is set to
         * true. You see when you load a url with a # in it which is common in jQuery applications
         * onPageStared is not called. Clearing the history at that point would break jQuery apps.
         */
        if (this.doClearHistory) {
            view.clearHistory();
            this.doClearHistory = false;
        }

        // Clear timeout flag
        this.appView.loadUrlTimeout++;

        // Broadcast message that page has loaded
        this.appView.postMessage("onPageFinished", url);

        // Make app visible after 2 sec in case there was a JS error and Cordova JS never initialized correctly
        if (this.appView.getVisibility() == View.INVISIBLE) {
            Thread t = new Thread(new Runnable() {
                public void run() {
                    try {
                        Thread.sleep(2000);
                        cordova.getActivity().runOnUiThread(new Runnable() {
                            public void run() {
                                appView.postMessage("spinner", "stop");
                            }
                        });
                    } catch (InterruptedException e) {
                    }
                }
            });
            t.start();
        }

        // Shutdown if blank loaded
        if (url.equals("about:blank")) {
            appView.postMessage("exit", null);
        }
    }

    /**
     * Report an error to the host application. These errors are unrecoverable (i.e. the main resource is unavailable).
     * The errorCode parameter corresponds to one of the ERROR_* constants.
     *
     * @param view          The WebView that is initiating the callback.
     * @param errorCode     The error code corresponding to an ERROR_* value.
     * @param description   A String describing the error.
     * @param failingUrl    The url that failed to load.
     */
    @Override
    public void onReceivedError(WebView view, int errorCode, String description, String failingUrl) {
        // Ignore error due to stopLoading().
        if (!isCurrentlyLoading) {
            return;
        }
        LOG.d(TAG, "CordovaWebViewClient.onReceivedError: Error code=%s Description=%s URL=%s", errorCode, description, failingUrl);

        // Clear timeout flag
        this.appView.loadUrlTimeout++;

        // If this is a "Protocol Not Supported" error, then revert to the previous
        // page. If there was no previous page, then punt. The application's config
        // is likely incorrect (start page set to sms: or something like that)
        if (errorCode == WebViewClient.ERROR_UNSUPPORTED_SCHEME) {
            if (view.canGoBack()) {
                view.goBack();
                return;
            } else {
                super.onReceivedError(view, errorCode, description, failingUrl);
            }
        }

        // Handle other errors by passing them to the webview in JS
        JSONObject data = new JSONObject();
        try {
            data.put("errorCode", errorCode);
            data.put("description", description);
            data.put("url", failingUrl);
        } catch (JSONException e) {
            e.printStackTrace();
        }
        this.appView.postMessage("onReceivedError", data);
    }

    /**
     * Notify the host application that an SSL error occurred while loading a resource.
     * The host application must call either handler.cancel() or handler.proceed().
     * Note that the decision may be retained for use in response to future SSL errors.
     * The default behavior is to cancel the load.
     *
     * @param view          The WebView that is initiating the callback.
     * @param handler       An SslErrorHandler object that will handle the user's response.
     * @param error         The SSL error object.
     */
    @TargetApi(8)
    @Override
    public void onReceivedSslError(WebView view, SslErrorHandler handler, SslError error) {

        final String packageName = this.cordova.getActivity().getPackageName();
        final PackageManager pm = this.cordova.getActivity().getPackageManager();

        ApplicationInfo appInfo;
        try {
            appInfo = pm.getApplicationInfo(packageName, PackageManager.GET_META_DATA);
            if ((appInfo.flags & ApplicationInfo.FLAG_DEBUGGABLE) != 0) {
                // debug = true
                handler.proceed();
                return;
            } else {
                // debug = false
                super.onReceivedSslError(view, handler, error);
            }
        } catch (NameNotFoundException e) {
            // When it doubt, lock it out!
            super.onReceivedSslError(view, handler, error);
        }
    }


    /**
     * Sets the authentication token.
     *
     * @param authenticationToken
     * @param host
     * @param realm
     */
    public void setAuthenticationToken(AuthenticationToken authenticationToken, String host, String realm) {
        if (host == null) {
            host = "";
        }
        if (realm == null) {
            realm = "";
        }
        this.authenticationTokens.put(host.concat(realm), authenticationToken);
    }

    /**
     * Removes the authentication token.
     *
     * @param host
     * @param realm
     *
     * @return the authentication token or null if did not exist
     */
    public AuthenticationToken removeAuthenticationToken(String host, String realm) {
        return this.authenticationTokens.remove(host.concat(realm));
    }

    /**
     * Gets the authentication token.
     *
     * In order it tries:
     * 1- host + realm
     * 2- host
     * 3- realm
     * 4- no host, no realm
     *
     * @param host
     * @param realm
     *
     * @return the authentication token
     */
    public AuthenticationToken getAuthenticationToken(String host, String realm) {
        AuthenticationToken token = null;
        token = this.authenticationTokens.get(host.concat(realm));

        if (token == null) {
            // try with just the host
            token = this.authenticationTokens.get(host);

            // Try the realm
            if (token == null) {
                token = this.authenticationTokens.get(realm);
            }

            // if no host found, just query for default
            if (token == null) {
                token = this.authenticationTokens.get("");
            }
        }

        return token;
    }

    /**
     * Clear all authentication tokens.
     */
    public void clearAuthenticationTokens() {
        this.authenticationTokens.clear();
    }

}


File: platforms/android/CordovaLib/src/org/apache/cordova/DirectoryManager.java
/*
       Licensed to the Apache Software Foundation (ASF) under one
       or more contributor license agreements.  See the NOTICE file
       distributed with this work for additional information
       regarding copyright ownership.  The ASF licenses this file
       to you under the Apache License, Version 2.0 (the
       "License"); you may not use this file except in compliance
       with the License.  You may obtain a copy of the License at

         http://www.apache.org/licenses/LICENSE-2.0

       Unless required by applicable law or agreed to in writing,
       software distributed under the License is distributed on an
       "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY
       KIND, either express or implied.  See the License for the
       specific language governing permissions and limitations
       under the License.
*/
package org.apache.cordova;

import java.io.File;

import android.content.Context;
import android.os.Environment;
import android.os.StatFs;

/**
 * This class provides file directory utilities.
 * All file operations are performed on the SD card.
 *
 * It is used by the FileUtils class.
 */
@Deprecated // Deprecated in 3.1. To be removed in 4.0.
public class DirectoryManager {

    @SuppressWarnings("unused")
    private static final String LOG_TAG = "DirectoryManager";

    /**
     * Determine if a file or directory exists.
     * @param name				The name of the file to check.
     * @return					T=exists, F=not found
     */
    public static boolean testFileExists(String name) {
        boolean status;

        // If SD card exists
        if ((testSaveLocationExists()) && (!name.equals(""))) {
            File path = Environment.getExternalStorageDirectory();
            File newPath = constructFilePaths(path.toString(), name);
            status = newPath.exists();
        }
        // If no SD card
        else {
            status = false;
        }
        return status;
    }

    /**
     * Get the free disk space
     * 
     * @return 		Size in KB or -1 if not available
     */
    public static long getFreeDiskSpace(boolean checkInternal) {
        String status = Environment.getExternalStorageState();
        long freeSpace = 0;

        // If SD card exists
        if (status.equals(Environment.MEDIA_MOUNTED)) {
            freeSpace = freeSpaceCalculation(Environment.getExternalStorageDirectory().getPath());
        }
        else if (checkInternal) {
            freeSpace = freeSpaceCalculation("/");
        }
        // If no SD card and we haven't been asked to check the internal directory then return -1
        else {
            return -1;
        }

        return freeSpace;
    }

    /**
     * Given a path return the number of free KB
     * 
     * @param path to the file system
     * @return free space in KB
     */
    private static long freeSpaceCalculation(String path) {
        StatFs stat = new StatFs(path);
        long blockSize = stat.getBlockSize();
        long availableBlocks = stat.getAvailableBlocks();
        return availableBlocks * blockSize / 1024;
    }

    /**
     * Determine if SD card exists.
     * 
     * @return				T=exists, F=not found
     */
    public static boolean testSaveLocationExists() {
        String sDCardStatus = Environment.getExternalStorageState();
        boolean status;

        // If SD card is mounted
        if (sDCardStatus.equals(Environment.MEDIA_MOUNTED)) {
            status = true;
        }

        // If no SD card
        else {
            status = false;
        }
        return status;
    }

    /**
     * Create a new file object from two file paths.
     *
     * @param file1			Base file path
     * @param file2			Remaining file path
     * @return				File object
     */
    private static File constructFilePaths (String file1, String file2) {
        File newPath;
        if (file2.startsWith(file1)) {
            newPath = new File(file2);
        }
        else {
            newPath = new File(file1 + "/" + file2);
        }
        return newPath;
    }

    /**
     * Determine if we can use the SD Card to store the temporary file.  If not then use
     * the internal cache directory.
     *
     * @return the absolute path of where to store the file
     */
    public static String getTempDirectoryPath(Context ctx) {
        File cache = null;

        // SD Card Mounted
        if (Environment.getExternalStorageState().equals(Environment.MEDIA_MOUNTED)) {
            cache = new File(Environment.getExternalStorageDirectory().getAbsolutePath() +
                    "/Android/data/" + ctx.getPackageName() + "/cache/");
        }
        // Use internal storage
        else {
            cache = ctx.getCacheDir();
        }

        // Create the cache directory if it doesn't exist
        if (!cache.exists()) {
            cache.mkdirs();
        }

        return cache.getAbsolutePath();
    }
}


File: platforms/android/CordovaLib/src/org/apache/cordova/DroidGap.java
/*
       Licensed to the Apache Software Foundation (ASF) under one
       or more contributor license agreements.  See the NOTICE file
       distributed with this work for additional information
       regarding copyright ownership.  The ASF licenses this file
       to you under the Apache License, Version 2.0 (the
       "License"); you may not use this file except in compliance
       with the License.  You may obtain a copy of the License at

         http://www.apache.org/licenses/LICENSE-2.0

       Unless required by applicable law or agreed to in writing,
       software distributed under the License is distributed on an
       "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY
       KIND, either express or implied.  See the License for the
       specific language governing permissions and limitations
       under the License.
*/

package org.apache.cordova;

/**
 * This used to be the class that should be extended by application
 * developers, but everything has been moved to CordovaActivity. So
 * you should extend CordovaActivity instead of DroidGap. This class
 * will be removed at a future time.
 *
 * @see CordovaActivity
 * @deprecated
 */
@Deprecated
public class DroidGap extends CordovaActivity {

}


File: platforms/android/CordovaLib/src/org/apache/cordova/ExifHelper.java
/*
       Licensed to the Apache Software Foundation (ASF) under one
       or more contributor license agreements.  See the NOTICE file
       distributed with this work for additional information
       regarding copyright ownership.  The ASF licenses this file
       to you under the Apache License, Version 2.0 (the
       "License"); you may not use this file except in compliance
       with the License.  You may obtain a copy of the License at

         http://www.apache.org/licenses/LICENSE-2.0

       Unless required by applicable law or agreed to in writing,
       software distributed under the License is distributed on an
       "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY
       KIND, either express or implied.  See the License for the
       specific language governing permissions and limitations
       under the License.
*/
package org.apache.cordova;

import java.io.IOException;

import android.media.ExifInterface;

@Deprecated // Deprecated in 3.1. To be removed in 4.0.
public class ExifHelper {
    private String aperture = null;
    private String datetime = null;
    private String exposureTime = null;
    private String flash = null;
    private String focalLength = null;
    private String gpsAltitude = null;
    private String gpsAltitudeRef = null;
    private String gpsDateStamp = null;
    private String gpsLatitude = null;
    private String gpsLatitudeRef = null;
    private String gpsLongitude = null;
    private String gpsLongitudeRef = null;
    private String gpsProcessingMethod = null;
    private String gpsTimestamp = null;
    private String iso = null;
    private String make = null;
    private String model = null;
    private String orientation = null;
    private String whiteBalance = null;

    private ExifInterface inFile = null;
    private ExifInterface outFile = null;

    /**
     * The file before it is compressed
     *
     * @param filePath
     * @throws IOException
     */
    public void createInFile(String filePath) throws IOException {
        this.inFile = new ExifInterface(filePath);
    }

    /**
     * The file after it has been compressed
     *
     * @param filePath
     * @throws IOException
     */
    public void createOutFile(String filePath) throws IOException {
        this.outFile = new ExifInterface(filePath);
    }

    /**
     * Reads all the EXIF data from the input file.
     */
    public void readExifData() {
        this.aperture = inFile.getAttribute(ExifInterface.TAG_APERTURE);
        this.datetime = inFile.getAttribute(ExifInterface.TAG_DATETIME);
        this.exposureTime = inFile.getAttribute(ExifInterface.TAG_EXPOSURE_TIME);
        this.flash = inFile.getAttribute(ExifInterface.TAG_FLASH);
        this.focalLength = inFile.getAttribute(ExifInterface.TAG_FOCAL_LENGTH);
        this.gpsAltitude = inFile.getAttribute(ExifInterface.TAG_GPS_ALTITUDE);
        this.gpsAltitudeRef = inFile.getAttribute(ExifInterface.TAG_GPS_ALTITUDE_REF);
        this.gpsDateStamp = inFile.getAttribute(ExifInterface.TAG_GPS_DATESTAMP);
        this.gpsLatitude = inFile.getAttribute(ExifInterface.TAG_GPS_LATITUDE);
        this.gpsLatitudeRef = inFile.getAttribute(ExifInterface.TAG_GPS_LATITUDE_REF);
        this.gpsLongitude = inFile.getAttribute(ExifInterface.TAG_GPS_LONGITUDE);
        this.gpsLongitudeRef = inFile.getAttribute(ExifInterface.TAG_GPS_LONGITUDE_REF);
        this.gpsProcessingMethod = inFile.getAttribute(ExifInterface.TAG_GPS_PROCESSING_METHOD);
        this.gpsTimestamp = inFile.getAttribute(ExifInterface.TAG_GPS_TIMESTAMP);
        this.iso = inFile.getAttribute(ExifInterface.TAG_ISO);
        this.make = inFile.getAttribute(ExifInterface.TAG_MAKE);
        this.model = inFile.getAttribute(ExifInterface.TAG_MODEL);
        this.orientation = inFile.getAttribute(ExifInterface.TAG_ORIENTATION);
        this.whiteBalance = inFile.getAttribute(ExifInterface.TAG_WHITE_BALANCE);
    }

    /**
     * Writes the previously stored EXIF data to the output file.
     *
     * @throws IOException
     */
    public void writeExifData() throws IOException {
        // Don't try to write to a null file
        if (this.outFile == null) {
            return;
        }

        if (this.aperture != null) {
            this.outFile.setAttribute(ExifInterface.TAG_APERTURE, this.aperture);
        }
        if (this.datetime != null) {
            this.outFile.setAttribute(ExifInterface.TAG_DATETIME, this.datetime);
        }
        if (this.exposureTime != null) {
            this.outFile.setAttribute(ExifInterface.TAG_EXPOSURE_TIME, this.exposureTime);
        }
        if (this.flash != null) {
            this.outFile.setAttribute(ExifInterface.TAG_FLASH, this.flash);
        }
        if (this.focalLength != null) {
            this.outFile.setAttribute(ExifInterface.TAG_FOCAL_LENGTH, this.focalLength);
        }
        if (this.gpsAltitude != null) {
            this.outFile.setAttribute(ExifInterface.TAG_GPS_ALTITUDE, this.gpsAltitude);
        }
        if (this.gpsAltitudeRef != null) {
            this.outFile.setAttribute(ExifInterface.TAG_GPS_ALTITUDE_REF, this.gpsAltitudeRef);
        }
        if (this.gpsDateStamp != null) {
            this.outFile.setAttribute(ExifInterface.TAG_GPS_DATESTAMP, this.gpsDateStamp);
        }
        if (this.gpsLatitude != null) {
            this.outFile.setAttribute(ExifInterface.TAG_GPS_LATITUDE, this.gpsLatitude);
        }
        if (this.gpsLatitudeRef != null) {
            this.outFile.setAttribute(ExifInterface.TAG_GPS_LATITUDE_REF, this.gpsLatitudeRef);
        }
        if (this.gpsLongitude != null) {
            this.outFile.setAttribute(ExifInterface.TAG_GPS_LONGITUDE, this.gpsLongitude);
        }
        if (this.gpsLongitudeRef != null) {
            this.outFile.setAttribute(ExifInterface.TAG_GPS_LONGITUDE_REF, this.gpsLongitudeRef);
        }
        if (this.gpsProcessingMethod != null) {
            this.outFile.setAttribute(ExifInterface.TAG_GPS_PROCESSING_METHOD, this.gpsProcessingMethod);
        }
        if (this.gpsTimestamp != null) {
            this.outFile.setAttribute(ExifInterface.TAG_GPS_TIMESTAMP, this.gpsTimestamp);
        }
        if (this.iso != null) {
            this.outFile.setAttribute(ExifInterface.TAG_ISO, this.iso);
        }
        if (this.make != null) {
            this.outFile.setAttribute(ExifInterface.TAG_MAKE, this.make);
        }
        if (this.model != null) {
            this.outFile.setAttribute(ExifInterface.TAG_MODEL, this.model);
        }
        if (this.orientation != null) {
            this.outFile.setAttribute(ExifInterface.TAG_ORIENTATION, this.orientation);
        }
        if (this.whiteBalance != null) {
            this.outFile.setAttribute(ExifInterface.TAG_WHITE_BALANCE, this.whiteBalance);
        }

        this.outFile.saveAttributes();
    }

    public int getOrientation() {
        int o = Integer.parseInt(this.orientation);

        if (o == ExifInterface.ORIENTATION_NORMAL) {
            return 0;
        } else if (o == ExifInterface.ORIENTATION_ROTATE_90) {
            return 90;
        } else if (o == ExifInterface.ORIENTATION_ROTATE_180) {
            return 180;
        } else if (o == ExifInterface.ORIENTATION_ROTATE_270) {
            return 270;
        } else {
            return 0;
        }
    }

    public void resetOrientation() {
        this.orientation = "" + ExifInterface.ORIENTATION_NORMAL;
    }
}


File: platforms/android/CordovaLib/src/org/apache/cordova/ExposedJsApi.java
/*
       Licensed to the Apache Software Foundation (ASF) under one
       or more contributor license agreements.  See the NOTICE file
       distributed with this work for additional information
       regarding copyright ownership.  The ASF licenses this file
       to you under the Apache License, Version 2.0 (the
       "License"); you may not use this file except in compliance
       with the License.  You may obtain a copy of the License at

         http://www.apache.org/licenses/LICENSE-2.0

       Unless required by applicable law or agreed to in writing,
       software distributed under the License is distributed on an
       "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY
       KIND, either express or implied.  See the License for the
       specific language governing permissions and limitations
       under the License.
*/
package org.apache.cordova;

import android.webkit.JavascriptInterface;

import org.json.JSONException;

/**
 * Contains APIs that the JS can call. All functions in here should also have
 * an equivalent entry in CordovaChromeClient.java, and be added to
 * cordova-js/lib/android/plugin/android/promptbasednativeapi.js
 */
/* package */ class ExposedJsApi {
    
    private CordovaBridge bridge;
    
    public ExposedJsApi(CordovaBridge bridge) {
        this.bridge = bridge;
    }

    @JavascriptInterface
    public String exec(int bridgeSecret, String service, String action, String callbackId, String arguments) throws JSONException, IllegalAccessException {
        return bridge.jsExec(bridgeSecret, service, action, callbackId, arguments);
    }
    
    @JavascriptInterface
    public void setNativeToJsBridgeMode(int bridgeSecret, int value) throws IllegalAccessException {
        bridge.jsSetNativeToJsBridgeMode(bridgeSecret, value);
    }
    
    @JavascriptInterface
    public String retrieveJsMessages(int bridgeSecret, boolean fromOnlineEvent) throws IllegalAccessException {
        return bridge.jsRetrieveJsMessages(bridgeSecret, fromOnlineEvent);
    }
}


File: platforms/android/CordovaLib/src/org/apache/cordova/FileHelper.java
/*
       Licensed to the Apache Software Foundation (ASF) under one
       or more contributor license agreements.  See the NOTICE file
       distributed with this work for additional information
       regarding copyright ownership.  The ASF licenses this file
       to you under the Apache License, Version 2.0 (the
       "License"); you may not use this file except in compliance
       with the License.  You may obtain a copy of the License at

         http://www.apache.org/licenses/LICENSE-2.0

       Unless required by applicable law or agreed to in writing,
       software distributed under the License is distributed on an
       "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY
       KIND, either express or implied.  See the License for the
       specific language governing permissions and limitations
       under the License.
 */
package org.apache.cordova;

import android.database.Cursor;
import android.net.Uri;
import android.webkit.MimeTypeMap;

import org.apache.cordova.CordovaInterface;
import org.apache.cordova.LOG;

import java.io.FileInputStream;
import java.io.FileNotFoundException;
import java.io.FileOutputStream;
import java.io.IOException;
import java.io.InputStream;
import java.io.OutputStream;
import java.nio.charset.Charset;
import java.util.Locale;

@Deprecated // Deprecated in 3.1. To be removed in 4.0.
public class FileHelper {
    private static final String LOG_TAG = "FileUtils";
    private static final String _DATA = "_data";

    /**
     * Returns the real path of the given URI string.
     * If the given URI string represents a content:// URI, the real path is retrieved from the media store.
     *
     * @param uriString the URI string of the audio/image/video
     * @param cordova the current application context
     * @return the full path to the file
     */
    @SuppressWarnings("deprecation")
    public static String getRealPath(String uriString, CordovaInterface cordova) {
        String realPath = null;

        if (uriString.startsWith("content://")) {
            String[] proj = { _DATA };
            Cursor cursor = cordova.getActivity().managedQuery(Uri.parse(uriString), proj, null, null, null);
            int column_index = cursor.getColumnIndexOrThrow(_DATA);
            cursor.moveToFirst();
            realPath = cursor.getString(column_index);
            if (realPath == null) {
                LOG.e(LOG_TAG, "Could get real path for URI string %s", uriString);
            }
        } else if (uriString.startsWith("file://")) {
            realPath = uriString.substring(7);
            if (realPath.startsWith("/android_asset/")) {
                LOG.e(LOG_TAG, "Cannot get real path for URI string %s because it is a file:///android_asset/ URI.", uriString);
                realPath = null;
            }
        } else {
            realPath = uriString;
        }

        return realPath;
    }

    /**
     * Returns the real path of the given URI.
     * If the given URI is a content:// URI, the real path is retrieved from the media store.
     *
     * @param uri the URI of the audio/image/video
     * @param cordova the current application context
     * @return the full path to the file
     */
    public static String getRealPath(Uri uri, CordovaInterface cordova) {
        return FileHelper.getRealPath(uri.toString(), cordova);
    }

    /**
     * Returns an input stream based on given URI string.
     *
     * @param uriString the URI string from which to obtain the input stream
     * @param cordova the current application context
     * @return an input stream into the data at the given URI or null if given an invalid URI string
     * @throws IOException
     */
    public static InputStream getInputStreamFromUriString(String uriString, CordovaInterface cordova) throws IOException {
        if (uriString.startsWith("content")) {
            Uri uri = Uri.parse(uriString);
            return cordova.getActivity().getContentResolver().openInputStream(uri);
        } else if (uriString.startsWith("file://")) {
            int question = uriString.indexOf("?");
            if (question > -1) {
            	uriString = uriString.substring(0,question);
            }
            if (uriString.startsWith("file:///android_asset/")) {
                Uri uri = Uri.parse(uriString);
                String relativePath = uri.getPath().substring(15);
                return cordova.getActivity().getAssets().open(relativePath);
            } else {
                return new FileInputStream(getRealPath(uriString, cordova));
            }
        } else {
            return new FileInputStream(getRealPath(uriString, cordova));
        }
    }

    /**
     * Removes the "file://" prefix from the given URI string, if applicable.
     * If the given URI string doesn't have a "file://" prefix, it is returned unchanged.
     *
     * @param uriString the URI string to operate on
     * @return a path without the "file://" prefix
     */
    public static String stripFileProtocol(String uriString) {
        if (uriString.startsWith("file://")) {
            uriString = uriString.substring(7);
        }
        return uriString;
    }

    public static String getMimeTypeForExtension(String path) {
        String extension = path;
        int lastDot = extension.lastIndexOf('.');
        if (lastDot != -1) {
            extension = extension.substring(lastDot + 1);
        }
        // Convert the URI string to lower case to ensure compatibility with MimeTypeMap (see CB-2185).
        extension = extension.toLowerCase(Locale.getDefault());
        if (extension.equals("3ga")) {
            return "audio/3gpp";
        }
        return MimeTypeMap.getSingleton().getMimeTypeFromExtension(extension);
    }
    
    /**
     * Returns the mime type of the data specified by the given URI string.
     *
     * @param uriString the URI string of the data
     * @return the mime type of the specified data
     */
    public static String getMimeType(String uriString, CordovaInterface cordova) {
        String mimeType = null;

        Uri uri = Uri.parse(uriString);
        if (uriString.startsWith("content://")) {
            mimeType = cordova.getActivity().getContentResolver().getType(uri);
        } else {
            mimeType = getMimeTypeForExtension(uri.getPath());
        }

        return mimeType;
    }
}


File: platforms/android/CordovaLib/src/org/apache/cordova/IceCreamCordovaWebViewClient.java
/*
       Licensed to the Apache Software Foundation (ASF) under one
       or more contributor license agreements.  See the NOTICE file
       distributed with this work for additional information
       regarding copyright ownership.  The ASF licenses this file
       to you under the Apache License, Version 2.0 (the
       "License"); you may not use this file except in compliance
       with the License.  You may obtain a copy of the License at

         http://www.apache.org/licenses/LICENSE-2.0

       Unless required by applicable law or agreed to in writing,
       software distributed under the License is distributed on an
       "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY
       KIND, either express or implied.  See the License for the
       specific language governing permissions and limitations
       under the License.
*/
package org.apache.cordova;

import java.io.FileNotFoundException;
import java.io.IOException;

import org.apache.cordova.CordovaInterface;
import org.apache.cordova.CordovaResourceApi.OpenForReadResult;
import org.apache.cordova.LOG;

import android.annotation.TargetApi;
import android.net.Uri;
import android.os.Build;
import android.webkit.WebResourceResponse;
import android.webkit.WebView;

@TargetApi(Build.VERSION_CODES.HONEYCOMB)
public class IceCreamCordovaWebViewClient extends CordovaWebViewClient {

    private static final String TAG = "IceCreamCordovaWebViewClient";
    private CordovaUriHelper helper;

    public IceCreamCordovaWebViewClient(CordovaInterface cordova) {
        super(cordova);
    }
    
    public IceCreamCordovaWebViewClient(CordovaInterface cordova, CordovaWebView view) {
        super(cordova, view);
    }

    @Override
    public WebResourceResponse shouldInterceptRequest(WebView view, String url) {
        try {
            // Check the against the whitelist and lock out access to the WebView directory
            // Changing this will cause problems for your application
            if (isUrlHarmful(url)) {
                LOG.w(TAG, "URL blocked by whitelist: " + url);
                // Results in a 404.
                return new WebResourceResponse("text/plain", "UTF-8", null);
            }

            CordovaResourceApi resourceApi = appView.getResourceApi();
            Uri origUri = Uri.parse(url);
            // Allow plugins to intercept WebView requests.
            Uri remappedUri = resourceApi.remapUri(origUri);
            
            if (!origUri.equals(remappedUri) || needsSpecialsInAssetUrlFix(origUri) || needsKitKatContentUrlFix(origUri)) {
                OpenForReadResult result = resourceApi.openForRead(remappedUri, true);
                return new WebResourceResponse(result.mimeType, "UTF-8", result.inputStream);
            }
            // If we don't need to special-case the request, let the browser load it.
            return null;
        } catch (IOException e) {
            if (!(e instanceof FileNotFoundException)) {
                LOG.e("IceCreamCordovaWebViewClient", "Error occurred while loading a file (returning a 404).", e);
            }
            // Results in a 404.
            return new WebResourceResponse("text/plain", "UTF-8", null);
        }
    }

    private boolean isUrlHarmful(String url) {
        return ((url.startsWith("http:") || url.startsWith("https:")) && !appView.getWhitelist().isUrlWhiteListed(url))
            || url.contains("app_webview");
    }

    private static boolean needsKitKatContentUrlFix(Uri uri) {
        return android.os.Build.VERSION.SDK_INT >= android.os.Build.VERSION_CODES.KITKAT && "content".equals(uri.getScheme());
    }

    private static boolean needsSpecialsInAssetUrlFix(Uri uri) {
        if (CordovaResourceApi.getUriType(uri) != CordovaResourceApi.URI_TYPE_ASSET) {
            return false;
        }
        if (uri.getQuery() != null || uri.getFragment() != null) {
            return true;
        }
        
        if (!uri.toString().contains("%")) {
            return false;
        }

        switch(android.os.Build.VERSION.SDK_INT){
            case android.os.Build.VERSION_CODES.ICE_CREAM_SANDWICH:
            case android.os.Build.VERSION_CODES.ICE_CREAM_SANDWICH_MR1:
                return true;
        }
        return false;
    }
}


File: platforms/android/CordovaLib/src/org/apache/cordova/JSONUtils.java
/*
       Licensed to the Apache Software Foundation (ASF) under one
       or more contributor license agreements.  See the NOTICE file
       distributed with this work for additional information
       regarding copyright ownership.  The ASF licenses this file
       to you under the Apache License, Version 2.0 (the
       "License"); you may not use this file except in compliance
       with the License.  You may obtain a copy of the License at

         http://www.apache.org/licenses/LICENSE-2.0

       Unless required by applicable law or agreed to in writing,
       software distributed under the License is distributed on an
       "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY
       KIND, either express or implied.  See the License for the
       specific language governing permissions and limitations
       under the License.
*/
package org.apache.cordova;

import java.util.ArrayList;
import java.util.List;

import org.json.JSONArray;
import org.json.JSONException;

@Deprecated // Deprecated in 3.1. To be removed in 4.0.
public class JSONUtils {
	public static List<String> toStringList(JSONArray array) throws JSONException {
        if(array == null) {
            return null;
        }
        else {
            List<String> list = new ArrayList<String>();

            for (int i = 0; i < array.length(); i++) {
                list.add(array.get(i).toString());
            }

            return list;
        }
    }
}


File: platforms/android/CordovaLib/src/org/apache/cordova/LinearLayoutSoftKeyboardDetect.java
/*
       Licensed to the Apache Software Foundation (ASF) under one
       or more contributor license agreements.  See the NOTICE file
       distributed with this work for additional information
       regarding copyright ownership.  The ASF licenses this file
       to you under the Apache License, Version 2.0 (the
       "License"); you may not use this file except in compliance
       with the License.  You may obtain a copy of the License at

         http://www.apache.org/licenses/LICENSE-2.0

       Unless required by applicable law or agreed to in writing,
       software distributed under the License is distributed on an
       "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY
       KIND, either express or implied.  See the License for the
       specific language governing permissions and limitations
       under the License.
*/
package org.apache.cordova;

import android.content.Context;
import android.widget.LinearLayout;

/**
 * This class is used to detect when the soft keyboard is shown and hidden in the web view.
 */
public class LinearLayoutSoftKeyboardDetect extends LinearLayout {

    private static final String TAG = "SoftKeyboardDetect";

    private int oldHeight = 0;  // Need to save the old height as not to send redundant events
    private int oldWidth = 0; // Need to save old width for orientation change
    private int screenWidth = 0;
    private int screenHeight = 0;
    private CordovaActivity app = null;
    private App appPlugin = null;

    public LinearLayoutSoftKeyboardDetect(Context context, int width, int height) {
        super(context);
        screenWidth = width;
        screenHeight = height;
        app = (CordovaActivity) context;
    }

    @Override
    /**
     * Start listening to new measurement events.  Fire events when the height
     * gets smaller fire a show keyboard event and when height gets bigger fire
     * a hide keyboard event.
     *
     * Note: We are using the core App plugin to send events over the bridge to Javascript
     *
     * @param widthMeasureSpec
     * @param heightMeasureSpec
     */
    protected void onMeasure(int widthMeasureSpec, int heightMeasureSpec) {
        super.onMeasure(widthMeasureSpec, heightMeasureSpec);

        LOG.v(TAG, "We are in our onMeasure method");

        // Get the current height of the visible part of the screen.
        // This height will not included the status bar.\
        int width, height;

        height = MeasureSpec.getSize(heightMeasureSpec);
        width = MeasureSpec.getSize(widthMeasureSpec);
        LOG.v(TAG, "Old Height = %d", oldHeight);
        LOG.v(TAG, "Height = %d", height);
        LOG.v(TAG, "Old Width = %d", oldWidth);
        LOG.v(TAG, "Width = %d", width);

        // If the oldHeight = 0 then this is the first measure event as the app starts up.
        // If oldHeight == height then we got a measurement change that doesn't affect us.
        if (oldHeight == 0 || oldHeight == height) {
            LOG.d(TAG, "Ignore this event");
        }
        // Account for orientation change and ignore this event/Fire orientation change
        else if (screenHeight == width)
        {
            int tmp_var = screenHeight;
            screenHeight = screenWidth;
            screenWidth = tmp_var;
            LOG.v(TAG, "Orientation Change");
        }
        // If the height as gotten bigger then we will assume the soft keyboard has
        // gone away.
        else if (height > oldHeight) {
            sendEvent("hidekeyboard");
        }
        // If the height as gotten smaller then we will assume the soft keyboard has
        // been displayed.
        else if (height < oldHeight) {
            sendEvent("showkeyboard");
        }

        // Update the old height for the next event
        oldHeight = height;
        oldWidth = width;
    }

    private void sendEvent(String event) {
        if (appPlugin == null) {
            appPlugin = (App)app.appView.pluginManager.getPlugin(App.PLUGIN_NAME);
        }

        if (appPlugin == null) {
            LOG.w(TAG, "Unable to fire event without existing plugin");
            return;
        }
        appPlugin.fireJavascriptEvent(event);
    }
}


File: platforms/android/CordovaLib/src/org/apache/cordova/NativeToJsMessageQueue.java
/*
       Licensed to the Apache Software Foundation (ASF) under one
       or more contributor license agreements.  See the NOTICE file
       distributed with this work for additional information
       regarding copyright ownership.  The ASF licenses this file
       to you under the Apache License, Version 2.0 (the
       "License"); you may not use this file except in compliance
       with the License.  You may obtain a copy of the License at

         http://www.apache.org/licenses/LICENSE-2.0

       Unless required by applicable law or agreed to in writing,
       software distributed under the License is distributed on an
       "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY
       KIND, either express or implied.  See the License for the
       specific language governing permissions and limitations
       under the License.
*/
package org.apache.cordova;

import java.lang.reflect.Field;
import java.lang.reflect.Method;
import java.util.LinkedList;

import org.apache.cordova.CordovaInterface;
import org.apache.cordova.PluginResult;

import android.os.Message;
import android.util.Log;
import android.webkit.WebView;

/**
 * Holds the list of messages to be sent to the WebView.
 */
public class NativeToJsMessageQueue {
    private static final String LOG_TAG = "JsMessageQueue";

    // Set this to true to force plugin results to be encoding as
    // JS instead of the custom format (useful for benchmarking).
    // Doesn't work for multipart messages.
    private static final boolean FORCE_ENCODE_USING_EVAL = false;

    // Disable sending back native->JS messages during an exec() when the active
    // exec() is asynchronous. Set this to true when running bridge benchmarks.
    static final boolean DISABLE_EXEC_CHAINING = false;

    // Arbitrarily chosen upper limit for how much data to send to JS in one shot.
    // This currently only chops up on message boundaries. It may be useful
    // to allow it to break up messages.
    private static int MAX_PAYLOAD_SIZE = 50 * 1024 * 10240;
    
    /**
     * When true, the active listener is not fired upon enqueue. When set to false,
     * the active listener will be fired if the queue is non-empty. 
     */
    private boolean paused;
    
    /**
     * The list of JavaScript statements to be sent to JavaScript.
     */
    private final LinkedList<JsMessage> queue = new LinkedList<JsMessage>();

    /**
     * The array of listeners that can be used to send messages to JS.
     */
    private final BridgeMode[] registeredListeners;    
    
    /**
     * When null, the bridge is disabled. This occurs during page transitions.
     * When disabled, all callbacks are dropped since they are assumed to be
     * relevant to the previous page.
     */
    private BridgeMode activeBridgeMode;

    private final CordovaInterface cordova;
    private final CordovaWebView webView;

    public NativeToJsMessageQueue(CordovaWebView webView, CordovaInterface cordova) {
        this.cordova = cordova;
        this.webView = webView;
        registeredListeners = new BridgeMode[4];
        registeredListeners[0] = new PollingBridgeMode();
        registeredListeners[1] = new LoadUrlBridgeMode();
        registeredListeners[2] = new OnlineEventsBridgeMode();
        registeredListeners[3] = new PrivateApiBridgeMode();
        reset();
    }

    public boolean isBridgeEnabled() {
        return activeBridgeMode != null;
    }

    /**
     * Changes the bridge mode.
     */
    public void setBridgeMode(int value) {
        if (value < -1 || value >= registeredListeners.length) {
            Log.d(LOG_TAG, "Invalid NativeToJsBridgeMode: " + value);
        } else {
            BridgeMode newMode = value < 0 ? null : registeredListeners[value];
            if (newMode != activeBridgeMode) {
                Log.d(LOG_TAG, "Set native->JS mode to " + (newMode == null ? "null" : newMode.getClass().getSimpleName()));
                synchronized (this) {
                    activeBridgeMode = newMode;
                    if (newMode != null) {
                        newMode.reset();
                        if (!paused && !queue.isEmpty()) {
                            newMode.onNativeToJsMessageAvailable();
                        }
                    }
                }
            }
        }
    }
    
    /**
     * Clears all messages and resets to the default bridge mode.
     */
    public void reset() {
        synchronized (this) {
            queue.clear();
            setBridgeMode(-1);
        }
    }

    private int calculatePackedMessageLength(JsMessage message) {
        int messageLen = message.calculateEncodedLength();
        String messageLenStr = String.valueOf(messageLen);
        return messageLenStr.length() + messageLen + 1;        
    }
    
    private void packMessage(JsMessage message, StringBuilder sb) {
        int len = message.calculateEncodedLength();
        sb.append(len)
          .append(' ');
        message.encodeAsMessage(sb);
    }
    
    /**
     * Combines and returns queued messages combined into a single string.
     * Combines as many messages as possible, while staying under MAX_PAYLOAD_SIZE.
     * Returns null if the queue is empty.
     */
    public String popAndEncode(boolean fromOnlineEvent) {
        synchronized (this) {
            if (activeBridgeMode == null) {
                return null;
            }
            activeBridgeMode.notifyOfFlush(fromOnlineEvent);
            if (queue.isEmpty()) {
                return null;
            }
            int totalPayloadLen = 0;
            int numMessagesToSend = 0;
            for (JsMessage message : queue) {
                int messageSize = calculatePackedMessageLength(message);
                if (numMessagesToSend > 0 && totalPayloadLen + messageSize > MAX_PAYLOAD_SIZE && MAX_PAYLOAD_SIZE > 0) {
                    break;
                }
                totalPayloadLen += messageSize;
                numMessagesToSend += 1;
            }

            StringBuilder sb = new StringBuilder(totalPayloadLen);
            for (int i = 0; i < numMessagesToSend; ++i) {
                JsMessage message = queue.removeFirst();
                packMessage(message, sb);
            }
            
            if (!queue.isEmpty()) {
                // Attach a char to indicate that there are more messages pending.
                sb.append('*');
            }
            String ret = sb.toString();
            return ret;
        }
    }
    
    /**
     * Same as popAndEncode(), except encodes in a form that can be executed as JS.
     */
    private String popAndEncodeAsJs() {
        synchronized (this) {
            int length = queue.size();
            if (length == 0) {
                return null;
            }
            int totalPayloadLen = 0;
            int numMessagesToSend = 0;
            for (JsMessage message : queue) {
                int messageSize = message.calculateEncodedLength() + 50; // overestimate.
                if (numMessagesToSend > 0 && totalPayloadLen + messageSize > MAX_PAYLOAD_SIZE && MAX_PAYLOAD_SIZE > 0) {
                    break;
                }
                totalPayloadLen += messageSize;
                numMessagesToSend += 1;
            }
            boolean willSendAllMessages = numMessagesToSend == queue.size();
            StringBuilder sb = new StringBuilder(totalPayloadLen + (willSendAllMessages ? 0 : 100));
            // Wrap each statement in a try/finally so that if one throws it does 
            // not affect the next.
            for (int i = 0; i < numMessagesToSend; ++i) {
                JsMessage message = queue.removeFirst();
                if (willSendAllMessages && (i + 1 == numMessagesToSend)) {
                    message.encodeAsJsMessage(sb);
                } else {
                    sb.append("try{");
                    message.encodeAsJsMessage(sb);
                    sb.append("}finally{");
                }
            }
            if (!willSendAllMessages) {
                sb.append("window.setTimeout(function(){cordova.require('cordova/plugin/android/polling').pollOnce();},0);");
            }
            for (int i = willSendAllMessages ? 1 : 0; i < numMessagesToSend; ++i) {
                sb.append('}');
            }
            String ret = sb.toString();
            return ret;
        }
    }   

    /**
     * Add a JavaScript statement to the list.
     */
    public void addJavaScript(String statement) {
        enqueueMessage(new JsMessage(statement));
    }

    /**
     * Add a JavaScript statement to the list.
     */
    public void addPluginResult(PluginResult result, String callbackId) {
        if (callbackId == null) {
            Log.e(LOG_TAG, "Got plugin result with no callbackId", new Throwable());
            return;
        }
        // Don't send anything if there is no result and there is no need to
        // clear the callbacks.
        boolean noResult = result.getStatus() == PluginResult.Status.NO_RESULT.ordinal();
        boolean keepCallback = result.getKeepCallback();
        if (noResult && keepCallback) {
            return;
        }
        JsMessage message = new JsMessage(result, callbackId);
        if (FORCE_ENCODE_USING_EVAL) {
            StringBuilder sb = new StringBuilder(message.calculateEncodedLength() + 50);
            message.encodeAsJsMessage(sb);
            message = new JsMessage(sb.toString());
        }

        enqueueMessage(message);
    }

    private void enqueueMessage(JsMessage message) {
        synchronized (this) {
            if (activeBridgeMode == null) {
                Log.d(LOG_TAG, "Dropping Native->JS message due to disabled bridge");
                return;
            }
            queue.add(message);
            if (!paused) {
                activeBridgeMode.onNativeToJsMessageAvailable();
            }
        }
    }

    public void setPaused(boolean value) {
        if (paused && value) {
            // This should never happen. If a use-case for it comes up, we should
            // change pause to be a counter.
            Log.e(LOG_TAG, "nested call to setPaused detected.", new Throwable());
        }
        paused = value;
        if (!value) {
            synchronized (this) {
                if (!queue.isEmpty() && activeBridgeMode != null) {
                    activeBridgeMode.onNativeToJsMessageAvailable();
                }
            }   
        }
    }

    private abstract class BridgeMode {
        abstract void onNativeToJsMessageAvailable();
        void notifyOfFlush(boolean fromOnlineEvent) {}
        void reset() {}
    }

    /** Uses JS polls for messages on a timer.. */
    private class PollingBridgeMode extends BridgeMode {
        @Override void onNativeToJsMessageAvailable() {
        }
    }

    /** Uses webView.loadUrl("javascript:") to execute messages. */
    private class LoadUrlBridgeMode extends BridgeMode {
        final Runnable runnable = new Runnable() {
            public void run() {
                String js = popAndEncodeAsJs();
                if (js != null) {
                    webView.loadUrlNow("javascript:" + js);
                }
            }
        };
        
        @Override void onNativeToJsMessageAvailable() {
            cordova.getActivity().runOnUiThread(runnable);
        }
    }

    /** Uses online/offline events to tell the JS when to poll for messages. */
    private class OnlineEventsBridgeMode extends BridgeMode {
        private boolean online;
        private boolean ignoreNextFlush;

        final Runnable toggleNetworkRunnable = new Runnable() {
            public void run() {
                if (!queue.isEmpty()) {
                    ignoreNextFlush = false;
                    webView.setNetworkAvailable(online);
                }
            }
        };
        final Runnable resetNetworkRunnable = new Runnable() {
            public void run() {
                online = false;
                // If the following call triggers a notifyOfFlush, then ignore it.
                ignoreNextFlush = true;
                webView.setNetworkAvailable(true);
            }
        };
        @Override void reset() {
            cordova.getActivity().runOnUiThread(resetNetworkRunnable);
        }
        @Override void onNativeToJsMessageAvailable() {
            cordova.getActivity().runOnUiThread(toggleNetworkRunnable);
        }
        // Track when online/offline events are fired so that we don't fire excess events.
        @Override void notifyOfFlush(boolean fromOnlineEvent) {
            if (fromOnlineEvent && !ignoreNextFlush) {
                online = !online;
            }
        }
    }
    
    /**
     * Uses Java reflection to access an API that lets us eval JS.
     * Requires Android 3.2.4 or above. 
     */
    private class PrivateApiBridgeMode extends BridgeMode {
    	// Message added in commit:
    	// http://omapzoom.org/?p=platform/frameworks/base.git;a=commitdiff;h=9497c5f8c4bc7c47789e5ccde01179abc31ffeb2
    	// Which first appeared in 3.2.4ish.
    	private static final int EXECUTE_JS = 194;
    	
    	Method sendMessageMethod;
    	Object webViewCore;
    	boolean initFailed;

    	@SuppressWarnings("rawtypes")
    	private void initReflection() {
        	Object webViewObject = webView;
    		Class webViewClass = WebView.class;
        	try {
    			Field f = webViewClass.getDeclaredField("mProvider");
    			f.setAccessible(true);
    			webViewObject = f.get(webView);
    			webViewClass = webViewObject.getClass();
        	} catch (Throwable e) {
        		// mProvider is only required on newer Android releases.
    		}
        	
        	try {
    			Field f = webViewClass.getDeclaredField("mWebViewCore");
                f.setAccessible(true);
    			webViewCore = f.get(webViewObject);
    			
    			if (webViewCore != null) {
    				sendMessageMethod = webViewCore.getClass().getDeclaredMethod("sendMessage", Message.class);
	    			sendMessageMethod.setAccessible(true);	    			
    			}
    		} catch (Throwable e) {
    			initFailed = true;
				Log.e(LOG_TAG, "PrivateApiBridgeMode failed to find the expected APIs.", e);
    		}
    	}
    	
        @Override void onNativeToJsMessageAvailable() {
        	if (sendMessageMethod == null && !initFailed) {
        		initReflection();
        	}
        	// webViewCore is lazily initialized, and so may not be available right away.
        	if (sendMessageMethod != null) {
	        	String js = popAndEncodeAsJs();
	        	Message execJsMessage = Message.obtain(null, EXECUTE_JS, js);
				try {
				    sendMessageMethod.invoke(webViewCore, execJsMessage);
				} catch (Throwable e) {
					Log.e(LOG_TAG, "Reflection message bridge failed.", e);
				}
        	}
        }
    }    
    private static class JsMessage {
        final String jsPayloadOrCallbackId;
        final PluginResult pluginResult;
        JsMessage(String js) {
            if (js == null) {
                throw new NullPointerException();
            }
            jsPayloadOrCallbackId = js;
            pluginResult = null;
        }
        JsMessage(PluginResult pluginResult, String callbackId) {
            if (callbackId == null || pluginResult == null) {
                throw new NullPointerException();
            }
            jsPayloadOrCallbackId = callbackId;
            this.pluginResult = pluginResult;
        }
        
        static int calculateEncodedLengthHelper(PluginResult pluginResult) {
            switch (pluginResult.getMessageType()) {
                case PluginResult.MESSAGE_TYPE_BOOLEAN: // f or t
                case PluginResult.MESSAGE_TYPE_NULL: // N
                    return 1;
                case PluginResult.MESSAGE_TYPE_NUMBER: // n
                    return 1 + pluginResult.getMessage().length();
                case PluginResult.MESSAGE_TYPE_STRING: // s
                    return 1 + pluginResult.getStrMessage().length();
                case PluginResult.MESSAGE_TYPE_BINARYSTRING:
                    return 1 + pluginResult.getMessage().length();
                case PluginResult.MESSAGE_TYPE_ARRAYBUFFER:
                    return 1 + pluginResult.getMessage().length();
                case PluginResult.MESSAGE_TYPE_MULTIPART:
                    int ret = 1;
                    for (int i = 0; i < pluginResult.getMultipartMessagesSize(); i++) {
                        int length = calculateEncodedLengthHelper(pluginResult.getMultipartMessage(i));
                        int argLength = String.valueOf(length).length();
                        ret += argLength + 1 + length;
                    }
                    return ret;
                case PluginResult.MESSAGE_TYPE_JSON:
                default:
                    return pluginResult.getMessage().length();
            }
        }
        
        int calculateEncodedLength() {
            if (pluginResult == null) {
                return jsPayloadOrCallbackId.length() + 1;
            }
            int statusLen = String.valueOf(pluginResult.getStatus()).length();
            int ret = 2 + statusLen + 1 + jsPayloadOrCallbackId.length() + 1;
            return ret + calculateEncodedLengthHelper(pluginResult);
            }

        static void encodeAsMessageHelper(StringBuilder sb, PluginResult pluginResult) {
            switch (pluginResult.getMessageType()) {
                case PluginResult.MESSAGE_TYPE_BOOLEAN:
                    sb.append(pluginResult.getMessage().charAt(0)); // t or f.
                    break;
                case PluginResult.MESSAGE_TYPE_NULL: // N
                    sb.append('N');
                    break;
                case PluginResult.MESSAGE_TYPE_NUMBER: // n
                    sb.append('n')
                      .append(pluginResult.getMessage());
                    break;
                case PluginResult.MESSAGE_TYPE_STRING: // s
                    sb.append('s');
                    sb.append(pluginResult.getStrMessage());
                    break;
                case PluginResult.MESSAGE_TYPE_BINARYSTRING: // S
                    sb.append('S');
                    sb.append(pluginResult.getMessage());
                    break;                    
                case PluginResult.MESSAGE_TYPE_ARRAYBUFFER: // A
                    sb.append('A');
                    sb.append(pluginResult.getMessage());
                    break;
                case PluginResult.MESSAGE_TYPE_MULTIPART:
                    sb.append('M');
                    for (int i = 0; i < pluginResult.getMultipartMessagesSize(); i++) {
                        PluginResult multipartMessage = pluginResult.getMultipartMessage(i);
                        sb.append(String.valueOf(calculateEncodedLengthHelper(multipartMessage)));
                        sb.append(' ');
                        encodeAsMessageHelper(sb, multipartMessage);
                    }
                    break;
                case PluginResult.MESSAGE_TYPE_JSON:
                default:
                    sb.append(pluginResult.getMessage()); // [ or {
            }
        }
        
        void encodeAsMessage(StringBuilder sb) {
            if (pluginResult == null) {
                sb.append('J')
                  .append(jsPayloadOrCallbackId);
                return;
            }
            int status = pluginResult.getStatus();
            boolean noResult = status == PluginResult.Status.NO_RESULT.ordinal();
            boolean resultOk = status == PluginResult.Status.OK.ordinal();
            boolean keepCallback = pluginResult.getKeepCallback();

            sb.append((noResult || resultOk) ? 'S' : 'F')
              .append(keepCallback ? '1' : '0')
              .append(status)
              .append(' ')
              .append(jsPayloadOrCallbackId)
              .append(' ');

            encodeAsMessageHelper(sb, pluginResult);
        }

        void encodeAsJsMessage(StringBuilder sb) {
            if (pluginResult == null) {
                sb.append(jsPayloadOrCallbackId);
            } else {
                int status = pluginResult.getStatus();
                boolean success = (status == PluginResult.Status.OK.ordinal()) || (status == PluginResult.Status.NO_RESULT.ordinal());
                sb.append("cordova.callbackFromNative('")
                  .append(jsPayloadOrCallbackId)
                  .append("',")
                  .append(success)
                  .append(",")
                  .append(status)
                  .append(",[");
                switch (pluginResult.getMessageType()) {
                    case PluginResult.MESSAGE_TYPE_BINARYSTRING:
                        sb.append("atob('")
                          .append(pluginResult.getMessage())
                          .append("')");
                        break;
                    case PluginResult.MESSAGE_TYPE_ARRAYBUFFER:
                        sb.append("cordova.require('cordova/base64').toArrayBuffer('")
                          .append(pluginResult.getMessage())
                          .append("')");
                        break;
                    default:
                    sb.append(pluginResult.getMessage());
                }
                sb.append("],")
                  .append(pluginResult.getKeepCallback())
                  .append(");");
            }
        }
    }
}


File: platforms/android/CordovaLib/src/org/apache/cordova/PluginEntry.java
/*
       Licensed to the Apache Software Foundation (ASF) under one
       or more contributor license agreements.  See the NOTICE file
       distributed with this work for additional information
       regarding copyright ownership.  The ASF licenses this file
       to you under the Apache License, Version 2.0 (the
       "License"); you may not use this file except in compliance
       with the License.  You may obtain a copy of the License at

         http://www.apache.org/licenses/LICENSE-2.0

       Unless required by applicable law or agreed to in writing,
       software distributed under the License is distributed on an
       "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY
       KIND, either express or implied.  See the License for the
       specific language governing permissions and limitations
       under the License.
 */
package org.apache.cordova;

import java.util.List;

import org.apache.cordova.CordovaPlugin;

/**
 * This class represents a service entry object.
 */
public class PluginEntry {

    /**
     * The name of the service that this plugin implements
     */
    public String service;

    /**
     * The plugin class name that implements the service.
     */
    public String pluginClass;

    /**
     * The pre-instantiated plugin to use for this entry.
     */
    public CordovaPlugin plugin;

    /**
     * Flag that indicates the plugin object should be created when PluginManager is initialized.
     */
    public boolean onload;

    private List<String> urlFilters;


    /**
     * Constructs with a CordovaPlugin already instantiated.
     */
    public PluginEntry(String service, CordovaPlugin plugin) {
        this(service, plugin.getClass().getName(), true, plugin, null);
    }

    /**
     * @param service               The name of the service
     * @param pluginClass           The plugin class name
     * @param onload                Create plugin object when HTML page is loaded
     */
    public PluginEntry(String service, String pluginClass, boolean onload) {
        this(service, pluginClass, onload, null, null);
    }
    
    @Deprecated // urlFilters are going away
    public PluginEntry(String service, String pluginClass, boolean onload, List<String> urlFilters) {
        this.service = service;
        this.pluginClass = pluginClass;
        this.onload = onload;
        this.urlFilters = urlFilters;
        plugin = null;
    }

    private PluginEntry(String service, String pluginClass, boolean onload, CordovaPlugin plugin, List<String> urlFilters) {
        this.service = service;
        this.pluginClass = pluginClass;
        this.onload = onload;
        this.urlFilters = urlFilters;
        this.plugin = plugin;
    }

    public List<String> getUrlFilters() {
        return urlFilters;
    }
}


File: platforms/android/CordovaLib/src/org/apache/cordova/PluginManager.java
/*
       Licensed to the Apache Software Foundation (ASF) under one
       or more contributor license agreements.  See the NOTICE file
       distributed with this work for additional information
       regarding copyright ownership.  The ASF licenses this file
       to you under the Apache License, Version 2.0 (the
       "License"); you may not use this file except in compliance
       with the License.  You may obtain a copy of the License at

         http://www.apache.org/licenses/LICENSE-2.0

       Unless required by applicable law or agreed to in writing,
       software distributed under the License is distributed on an
       "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY
       KIND, either express or implied.  See the License for the
       specific language governing permissions and limitations
       under the License.
 */
package org.apache.cordova;

import java.util.HashMap;
import java.util.List;

import org.apache.cordova.CordovaWebView;
import org.apache.cordova.CallbackContext;
import org.apache.cordova.CordovaInterface;
import org.apache.cordova.CordovaPlugin;
import org.apache.cordova.PluginEntry;
import org.apache.cordova.PluginResult;
import org.json.JSONException;

import android.content.Intent;
import android.net.Uri;
import android.os.Debug;
import android.util.Log;

/**
 * PluginManager is exposed to JavaScript in the Cordova WebView.
 *
 * Calling native plugin code can be done by calling PluginManager.exec(...)
 * from JavaScript.
 */
public class PluginManager {
    private static String TAG = "PluginManager";
    private static final int SLOW_EXEC_WARNING_THRESHOLD = Debug.isDebuggerConnected() ? 60 : 16;

    // List of service entries
    private final HashMap<String, CordovaPlugin> pluginMap = new HashMap<String, CordovaPlugin>();
    private final HashMap<String, PluginEntry> entryMap = new HashMap<String, PluginEntry>();

    private final CordovaInterface ctx;
    private final CordovaWebView app;

    // Stores mapping of Plugin Name -> <url-filter> values.
    // Using <url-filter> is deprecated.
    protected HashMap<String, List<String>> urlMap = new HashMap<String, List<String>>();

    @Deprecated
    PluginManager(CordovaWebView cordovaWebView, CordovaInterface cordova) {
        this(cordovaWebView, cordova, null);
    }

    PluginManager(CordovaWebView cordovaWebView, CordovaInterface cordova, List<PluginEntry> pluginEntries) {
        this.ctx = cordova;
        this.app = cordovaWebView;
        if (pluginEntries == null) {
            ConfigXmlParser parser = new ConfigXmlParser();
            parser.parse(ctx.getActivity());
            pluginEntries = parser.getPluginEntries();
        }
        setPluginEntries(pluginEntries);
    }

    public void setPluginEntries(List<PluginEntry> pluginEntries) {
        this.onPause(false);
        this.onDestroy();
        pluginMap.clear();
        urlMap.clear();
        for (PluginEntry entry : pluginEntries) {
            addService(entry);
        }
    }

    /**
     * Init when loading a new HTML page into webview.
     */
    public void init() {
        LOG.d(TAG, "init()");
        this.onPause(false);
        this.onDestroy();
        pluginMap.clear();
        this.startupPlugins();
    }

    @Deprecated
    public void loadPlugins() {
    }

    /**
     * Delete all plugin objects.
     */
    @Deprecated // Should not be exposed as public.
    public void clearPluginObjects() {
        pluginMap.clear();
    }

    /**
     * Create plugins objects that have onload set.
     */
    @Deprecated // Should not be exposed as public.
    public void startupPlugins() {
        for (PluginEntry entry : entryMap.values()) {
            // Add a null entry to for each non-startup plugin to avoid ConcurrentModificationException
            // When iterating plugins.
            if (entry.onload) {
                getPlugin(entry.service);
            } else {
                pluginMap.put(entry.service, null);
            }
        }
    }

    /**
     * Receives a request for execution and fulfills it by finding the appropriate
     * Java class and calling it's execute method.
     *
     * PluginManager.exec can be used either synchronously or async. In either case, a JSON encoded
     * string is returned that will indicate if any errors have occurred when trying to find
     * or execute the class denoted by the clazz argument.
     *
     * @param service       String containing the service to run
     * @param action        String containing the action that the class is supposed to perform. This is
     *                      passed to the plugin execute method and it is up to the plugin developer
     *                      how to deal with it.
     * @param callbackId    String containing the id of the callback that is execute in JavaScript if
     *                      this is an async plugin call.
     * @param rawArgs       An Array literal string containing any arguments needed in the
     *                      plugin execute method.
     */
    public void exec(final String service, final String action, final String callbackId, final String rawArgs) {
        CordovaPlugin plugin = getPlugin(service);
        if (plugin == null) {
            Log.d(TAG, "exec() call to unknown plugin: " + service);
            PluginResult cr = new PluginResult(PluginResult.Status.CLASS_NOT_FOUND_EXCEPTION);
            app.sendPluginResult(cr, callbackId);
            return;
        }
        CallbackContext callbackContext = new CallbackContext(callbackId, app);
        try {
            long pluginStartTime = System.currentTimeMillis();
            boolean wasValidAction = plugin.execute(action, rawArgs, callbackContext);
            long duration = System.currentTimeMillis() - pluginStartTime;

            if (duration > SLOW_EXEC_WARNING_THRESHOLD) {
                Log.w(TAG, "THREAD WARNING: exec() call to " + service + "." + action + " blocked the main thread for " + duration + "ms. Plugin should use CordovaInterface.getThreadPool().");
            }
            if (!wasValidAction) {
                PluginResult cr = new PluginResult(PluginResult.Status.INVALID_ACTION);
                callbackContext.sendPluginResult(cr);
            }
        } catch (JSONException e) {
            PluginResult cr = new PluginResult(PluginResult.Status.JSON_EXCEPTION);
            callbackContext.sendPluginResult(cr);
        } catch (Exception e) {
            Log.e(TAG, "Uncaught exception from plugin", e);
            callbackContext.error(e.getMessage());
        }
    }

    @Deprecated
    public void exec(String service, String action, String callbackId, String jsonArgs, boolean async) {
        exec(service, action, callbackId, jsonArgs);
    }

    /**
     * Get the plugin object that implements the service.
     * If the plugin object does not already exist, then create it.
     * If the service doesn't exist, then return null.
     *
     * @param service       The name of the service.
     * @return              CordovaPlugin or null
     */
    public CordovaPlugin getPlugin(String service) {
        CordovaPlugin ret = pluginMap.get(service);
        if (ret == null) {
            PluginEntry pe = entryMap.get(service);
            if (pe == null) {
                return null;
            }
            if (pe.plugin != null) {
                ret = pe.plugin;
            } else {
                ret = instantiatePlugin(pe.pluginClass);
            }
            ret.privateInitialize(ctx, app, app.getPreferences());
            pluginMap.put(service, ret);
        }
        return ret;
    }

    /**
     * Add a plugin class that implements a service to the service entry table.
     * This does not create the plugin object instance.
     *
     * @param service           The service name
     * @param className         The plugin class name
     */
    public void addService(String service, String className) {
        PluginEntry entry = new PluginEntry(service, className, false);
        this.addService(entry);
    }

    /**
     * Add a plugin class that implements a service to the service entry table.
     * This does not create the plugin object instance.
     *
     * @param entry             The plugin entry
     */
    public void addService(PluginEntry entry) {
        this.entryMap.put(entry.service, entry);
        List<String> urlFilters = entry.getUrlFilters();
        if (urlFilters != null) {
            urlMap.put(entry.service, urlFilters);
        }
        if (entry.plugin != null) {
            entry.plugin.privateInitialize(ctx, app, app.getPreferences());
            pluginMap.put(entry.service, entry.plugin);
        }

    }

    /**
     * Called when the system is about to start resuming a previous activity.
     *
     * @param multitasking      Flag indicating if multitasking is turned on for app
     */
    public void onPause(boolean multitasking) {
        for (CordovaPlugin plugin : this.pluginMap.values()) {
            if (plugin != null) {
                plugin.onPause(multitasking);
            }
        }
    }

    /**
     * Called when the system received an HTTP authentication request. Plugins can use
     * the supplied HttpAuthHandler to process this auth challenge.
     *
     * @param view              The WebView that is initiating the callback
     * @param handler           The HttpAuthHandler used to set the WebView's response
     * @param host              The host requiring authentication
     * @param realm             The realm for which authentication is required
     * 
     * @return                  Returns True if there is a plugin which will resolve this auth challenge, otherwise False
     * 
     */
    public boolean onReceivedHttpAuthRequest(CordovaWebView view, ICordovaHttpAuthHandler handler, String host, String realm) {
        for (CordovaPlugin plugin : this.pluginMap.values()) {
            if (plugin != null && plugin.onReceivedHttpAuthRequest(view, handler, host, realm)) {
                return true;
            }
        }
        return false;
    }
    
    /**
     * Called when he system received an SSL client certificate request.  Plugin can use
     * the supplied ClientCertRequest to process this certificate challenge.
     *
     * @param view              The WebView that is initiating the callback
     * @param request           The client certificate request
     *
     * @return                  Returns True if plugin will resolve this auth challenge, otherwise False
     *
     */
    public boolean onReceivedClientCertRequest(CordovaWebView view, ICordovaClientCertRequest request) {
        for (CordovaPlugin plugin : this.pluginMap.values()) {
            if (plugin != null && plugin.onReceivedClientCertRequest(view, request)) {
                return true;
            }
        }
        return false;
    }

    /**
     * Called when the activity will start interacting with the user.
     *
     * @param multitasking      Flag indicating if multitasking is turned on for app
     */
    public void onResume(boolean multitasking) {
        for (CordovaPlugin plugin : this.pluginMap.values()) {
            if (plugin != null) {
                plugin.onResume(multitasking);
            }
        }
    }

    /**
     * The final call you receive before your activity is destroyed.
     */
    public void onDestroy() {
        for (CordovaPlugin plugin : this.pluginMap.values()) {
            if (plugin != null) {
                plugin.onDestroy();
            }
        }
    }

    /**
     * Send a message to all plugins.
     *
     * @param id                The message id
     * @param data              The message data
     * @return                  Object to stop propagation or null
     */
    public Object postMessage(String id, Object data) {
        Object obj = this.ctx.onMessage(id, data);
        if (obj != null) {
            return obj;
        }
        for (CordovaPlugin plugin : this.pluginMap.values()) {
            if (plugin != null) {
                obj = plugin.onMessage(id, data);
                if (obj != null) {
                    return obj;
                }
            }
        }
        return null;
    }

    /**
     * Called when the activity receives a new intent.
     */
    public void onNewIntent(Intent intent) {
        for (CordovaPlugin plugin : this.pluginMap.values()) {
            if (plugin != null) {
                plugin.onNewIntent(intent);
            }
        }
    }

    /**
     * Called when the URL of the webview changes.
     *
     * @param url               The URL that is being changed to.
     * @return                  Return false to allow the URL to load, return true to prevent the URL from loading.
     */
    public boolean onOverrideUrlLoading(String url) {
        // Deprecated way to intercept URLs. (process <url-filter> tags).
        // Instead, plugins should not include <url-filter> and instead ensure
        // that they are loaded before this function is called (either by setting
        // the onload <param> or by making an exec() call to them)
        for (PluginEntry entry : this.entryMap.values()) {
            List<String> urlFilters = urlMap.get(entry.service);
            if (urlFilters != null) {
                for (String s : urlFilters) {
                    if (url.startsWith(s)) {
                        return getPlugin(entry.service).onOverrideUrlLoading(url);
                    }
                }
            } else {
                CordovaPlugin plugin = pluginMap.get(entry.service);
                if (plugin != null && plugin.onOverrideUrlLoading(url)) {
                    return true;
                }
            }
        }
        return false;
    }

    /**
     * Called when the app navigates or refreshes.
     */
    public void onReset() {
        for (CordovaPlugin plugin : this.pluginMap.values()) {
            if (plugin != null) {
                plugin.onReset();
            }
        }
    }

    Uri remapUri(Uri uri) {
        for (CordovaPlugin plugin : this.pluginMap.values()) {
            if (plugin != null) {
                Uri ret = plugin.remapUri(uri);
                if (ret != null) {
                    return ret;
                }
            }
        }
        return null;
    }

    /**
     * Create a plugin based on class name.
     */
    private CordovaPlugin instantiatePlugin(String className) {
        CordovaPlugin ret = null;
        try {
            Class<?> c = null;
            if ((className != null) && !("".equals(className))) {
                c = Class.forName(className);
            }
            if (c != null & CordovaPlugin.class.isAssignableFrom(c)) {
                ret = (CordovaPlugin) c.newInstance();
            }
        } catch (Exception e) {
            e.printStackTrace();
            System.out.println("Error adding plugin " + className + ".");
        }
        return ret;
    }
}


File: platforms/android/CordovaLib/src/org/apache/cordova/ScrollEvent.java
/*
       Licensed to the Apache Software Foundation (ASF) under one
       or more contributor license agreements.  See the NOTICE file
       distributed with this work for additional information
       regarding copyright ownership.  The ASF licenses this file
       to you under the Apache License, Version 2.0 (the
       "License"); you may not use this file except in compliance
       with the License.  You may obtain a copy of the License at

         http://www.apache.org/licenses/LICENSE-2.0

       Unless required by applicable law or agreed to in writing,
       software distributed under the License is distributed on an
       "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY
       KIND, either express or implied.  See the License for the
       specific language governing permissions and limitations
       under the License.
*/

package org.apache.cordova;

import android.view.View;

/*
 * This can be used by any view, including native views
 * 
 */


public class ScrollEvent {
    
    public int l, t, nl, nt;
    private View targetView;
    
    /*
     * ScrollEvent constructor
     * No idea why it uses l and t instead of x and y
     * 
     * @param x
     * @param y
     * @param nx
     * @param ny
     * @param view
     */
    
    ScrollEvent(int nx, int ny, int x, int y, View view)
    {
        l = x; y = t; nl = nx; nt = ny;
        targetView = view;
    }
    
    public int dl()
    {
        return nl - l;
    }
    
    public int dt()
    {
        return nt - t;
    }
    
    public View getTargetView()
    {
        return targetView;
    }

}


File: platforms/android/CordovaLib/src/org/apache/cordova/SplashScreenInternal.java
/*
       Licensed to the Apache Software Foundation (ASF) under one
       or more contributor license agreements.  See the NOTICE file
       distributed with this work for additional information
       regarding copyright ownership.  The ASF licenses this file
       to you under the Apache License, Version 2.0 (the
       "License"); you may not use this file except in compliance
       with the License.  You may obtain a copy of the License at

         http://www.apache.org/licenses/LICENSE-2.0

       Unless required by applicable law or agreed to in writing,
       software distributed under the License is distributed on an
       "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY
       KIND, either express or implied.  See the License for the
       specific language governing permissions and limitations
       under the License.
*/

package org.apache.cordova;

import android.app.Dialog;
import android.app.ProgressDialog;
import android.content.Context;
import android.content.DialogInterface;
import android.graphics.Color;
import android.os.Handler;
import android.view.Display;
import android.view.View;
import android.view.ViewGroup;
import android.view.WindowManager;
import android.widget.LinearLayout;

import org.json.JSONArray;
import org.json.JSONException;

// This file is a copy of SplashScreen.java from cordova-plugin-splashscreen, and is required only
// for pre-4.0 Cordova as a transition path to it being extracted into the plugin.
public class SplashScreenInternal extends CordovaPlugin {
    private static final String LOG_TAG = "SplashScreenInternal";
    private static Dialog splashDialog;
    private static ProgressDialog spinnerDialog;
    private static boolean firstShow = true;

    @Override
    protected void pluginInitialize() {
        if (!firstShow) {
            return;
        }
        // Make WebView invisible while loading URL
        webView.setVisibility(View.INVISIBLE);
        int drawableId = preferences.getInteger("SplashDrawableId", 0);
        if (drawableId == 0) {
            String splashResource = preferences.getString("SplashScreen", null);
            if (splashResource != null) {
                drawableId = cordova.getActivity().getResources().getIdentifier(splashResource, "drawable", cordova.getActivity().getClass().getPackage().getName());
                if (drawableId == 0) {
                    drawableId = cordova.getActivity().getResources().getIdentifier(splashResource, "drawable", cordova.getActivity().getPackageName());
                }
                preferences.set("SplashDrawableId", drawableId);
            }
        }

        firstShow = false;
        loadSpinner();
        showSplashScreen(true);
    }

    @Override
    public void onPause(boolean multitasking) {
        // hide the splash screen to avoid leaking a window
        this.removeSplashScreen();
    }

    @Override
    public void onDestroy() {
        // hide the splash screen to avoid leaking a window
        this.removeSplashScreen();
        firstShow = true;
    }

    @Override
    public boolean execute(String action, JSONArray args, CallbackContext callbackContext) throws JSONException {
        if (action.equals("hide")) {
            cordova.getActivity().runOnUiThread(new Runnable() {
                public void run() {
                    webView.postMessage("splashscreen", "hide");
                }
            });
        } else if (action.equals("show")) {
            cordova.getActivity().runOnUiThread(new Runnable() {
                public void run() {
                    webView.postMessage("splashscreen", "show");
                }
            });
        } else if (action.equals("spinnerStart")) {
            final String title = args.getString(0);
            final String message = args.getString(1);
            cordova.getActivity().runOnUiThread(new Runnable() {
                public void run() {
                    spinnerStart(title, message);
                }
            });
        } else {
            return false;
        }

        callbackContext.success();
        return true;
    }

    @Override
    public Object onMessage(String id, Object data) {
        if ("splashscreen".equals(id)) {
            if ("hide".equals(data.toString())) {
                this.removeSplashScreen();
            } else {
                this.showSplashScreen(false);
            }
        } else if ("spinner".equals(id)) {
            if ("stop".equals(data.toString())) {
                this.spinnerStop();
                webView.setVisibility(View.VISIBLE);
            }
        } else if ("onReceivedError".equals(id)) {
            spinnerStop();
        }
        return null;
    }

    private void removeSplashScreen() {
        cordova.getActivity().runOnUiThread(new Runnable() {
            public void run() {
                if (splashDialog != null && splashDialog.isShowing()) {
                    splashDialog.dismiss();
                    splashDialog = null;
                }
            }
        });
    }

    /**
     * Shows the splash screen over the full Activity
     */
    @SuppressWarnings("deprecation")
    private void showSplashScreen(final boolean hideAfterDelay) {
        final int splashscreenTime = preferences.getInteger("SplashScreenDelay", 3000);
        final int drawableId = preferences.getInteger("SplashDrawableId", 0);

        // If the splash dialog is showing don't try to show it again
        if (this.splashDialog != null && splashDialog.isShowing()) {
            return;
        }
        if (drawableId == 0 || (splashscreenTime <= 0 && hideAfterDelay)) {
            return;
        }

        cordova.getActivity().runOnUiThread(new Runnable() {
            public void run() {
                // Get reference to display
                Display display = cordova.getActivity().getWindowManager().getDefaultDisplay();
                Context context = webView.getContext();

                // Create the layout for the dialog
                LinearLayout root = new LinearLayout(context);
                root.setMinimumHeight(display.getHeight());
                root.setMinimumWidth(display.getWidth());
                root.setOrientation(LinearLayout.VERTICAL);

                // TODO: Use the background color of the webview's parent instead of using the
                // preference.
                root.setBackgroundColor(preferences.getInteger("backgroundColor", Color.BLACK));
                root.setLayoutParams(new LinearLayout.LayoutParams(ViewGroup.LayoutParams.MATCH_PARENT,
                        ViewGroup.LayoutParams.MATCH_PARENT, 0.0F));
                root.setBackgroundResource(drawableId);

                // Create and show the dialog
                splashDialog = new Dialog(context, android.R.style.Theme_Translucent_NoTitleBar);
                // check to see if the splash screen should be full screen
                if ((cordova.getActivity().getWindow().getAttributes().flags & WindowManager.LayoutParams.FLAG_FULLSCREEN)
                        == WindowManager.LayoutParams.FLAG_FULLSCREEN) {
                    splashDialog.getWindow().setFlags(WindowManager.LayoutParams.FLAG_FULLSCREEN,
                            WindowManager.LayoutParams.FLAG_FULLSCREEN);
                }
                splashDialog.setContentView(root);
                splashDialog.setCancelable(false);
                splashDialog.show();

                // Set Runnable to remove splash screen just in case
                if (hideAfterDelay) {
                    final Handler handler = new Handler();
                    handler.postDelayed(new Runnable() {
                        public void run() {
                            removeSplashScreen();
                        }
                    }, splashscreenTime);
                }
            }
        });
    }

    /*
     * Load the spinner
     */
    private void loadSpinner() {
        // If loadingDialog property, then show the App loading dialog for first page of app
        String loading = null;
        if (webView.canGoBack()) {
            loading = preferences.getString("LoadingDialog", null);
        }
        else {
            loading = preferences.getString("LoadingPageDialog", null);
        }
        if (loading != null) {
            String title = "";
            String message = "Loading Application...";

            if (loading.length() > 0) {
                int comma = loading.indexOf(',');
                if (comma > 0) {
                    title = loading.substring(0, comma);
                    message = loading.substring(comma + 1);
                }
                else {
                    title = "";
                    message = loading;
                }
            }
            spinnerStart(title, message);
        }
    }

    private void spinnerStart(final String title, final String message) {
        cordova.getActivity().runOnUiThread(new Runnable() {
            public void run() {
                spinnerStop();
                spinnerDialog = ProgressDialog.show(webView.getContext(), title, message, true, true,
                        new DialogInterface.OnCancelListener() {
                            public void onCancel(DialogInterface dialog) {
                                spinnerDialog = null;
                            }
                        });
            }
        });
    }

    private void spinnerStop() {
        cordova.getActivity().runOnUiThread(new Runnable() {
            public void run() {
                if (spinnerDialog != null && spinnerDialog.isShowing()) {
                    spinnerDialog.dismiss();
                    spinnerDialog = null;
                }
            }
        });
    }
}


File: platforms/android/src/de/appplant/cordova/plugin/local_notification/example/MainActivity.java
/*
       Licensed to the Apache Software Foundation (ASF) under one
       or more contributor license agreements.  See the NOTICE file
       distributed with this work for additional information
       regarding copyright ownership.  The ASF licenses this file
       to you under the Apache License, Version 2.0 (the
       "License"); you may not use this file except in compliance
       with the License.  You may obtain a copy of the License at

         http://www.apache.org/licenses/LICENSE-2.0

       Unless required by applicable law or agreed to in writing,
       software distributed under the License is distributed on an
       "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY
       KIND, either express or implied.  See the License for the
       specific language governing permissions and limitations
       under the License.
 */

package de.appplant.cordova.plugin.local_notification.example;

import android.os.Bundle;
import org.apache.cordova.*;

public class MainActivity extends CordovaActivity
{
    @Override
    public void onCreate(Bundle savedInstanceState)
    {
        super.onCreate(savedInstanceState);
        super.init();
        // Set by <content src="index.html" /> in config.xml
        loadUrl(launchUrl);
    }
}


File: platforms/android/src/de/appplant/cordova/plugin/localnotification/LocalNotification.java
/*
 * Copyright (c) 2013-2015 by appPlant UG. All rights reserved.
 *
 * @APPPLANT_LICENSE_HEADER_START@
 *
 * This file contains Original Code and/or Modifications of Original Code
 * as defined in and that are subject to the Apache License
 * Version 2.0 (the 'License'). You may not use this file except in
 * compliance with the License. Please obtain a copy of the License at
 * http://opensource.org/licenses/Apache-2.0/ and read it before using this
 * file.
 *
 * The Original Code and all software distributed under the License are
 * distributed on an 'AS IS' basis, WITHOUT WARRANTY OF ANY KIND, EITHER
 * EXPRESS OR IMPLIED, AND APPLE HEREBY DISCLAIMS ALL SUCH WARRANTIES,
 * INCLUDING WITHOUT LIMITATION, ANY WARRANTIES OF MERCHANTABILITY,
 * FITNESS FOR A PARTICULAR PURPOSE, QUIET ENJOYMENT OR NON-INFRINGEMENT.
 * Please see the License for the specific language governing rights and
 * limitations under the License.
 *
 * @APPPLANT_LICENSE_HEADER_END@
 */

package de.appplant.cordova.plugin.localnotification;

import android.os.Build;

import org.apache.cordova.CallbackContext;
import org.apache.cordova.CordovaInterface;
import org.apache.cordova.CordovaPlugin;
import org.apache.cordova.CordovaWebView;
import org.apache.cordova.PluginResult;
import org.json.JSONArray;
import org.json.JSONException;
import org.json.JSONObject;

import java.util.ArrayList;
import java.util.List;

import de.appplant.cordova.plugin.notification.Manager;
import de.appplant.cordova.plugin.notification.Notification;

/**
 * This plugin utilizes the Android AlarmManager in combination with local
 * notifications. When a local notification is scheduled the alarm manager takes
 * care of firing the event. When the event is processed, a notification is put
 * in the Android notification center and status bar.
 */
public class LocalNotification extends CordovaPlugin {

    // Reference to the web view for static access
    private static CordovaWebView webView = null;

    // Indicates if the device is ready (to receive events)
    private static Boolean deviceready = false;

    // To inform the user about the state of the app in callbacks
    protected static Boolean isInBackground = true;

    // Queues all events before deviceready
    private static ArrayList<String> eventQueue = new ArrayList<String>();

    /**
     * Called after plugin construction and fields have been initialized.
     * Prefer to use pluginInitialize instead since there is no value in
     * having parameters on the initialize() function.
     *
     * pluginInitialize is not available for cordova 3.0-3.5 !
     */
    @Override
    public void initialize (CordovaInterface cordova, CordovaWebView webView) {
        LocalNotification.webView = super.webView;
    }

    /**
     * Called when the system is about to start resuming a previous activity.
     *
     * @param multitasking
     *      Flag indicating if multitasking is turned on for app
     */
    @Override
    public void onPause(boolean multitasking) {
        super.onPause(multitasking);
        isInBackground = true;
    }

    /**
     * Called when the activity will start interacting with the user.
     *
     * @param multitasking
     *      Flag indicating if multitasking is turned on for app
     */
    @Override
    public void onResume(boolean multitasking) {
        super.onResume(multitasking);
        isInBackground = false;
        deviceready();
    }

    /**
     * The final call you receive before your activity is destroyed.
     */
    @Override
    public void onDestroy() {
        deviceready = false;
        isInBackground = true;
    }

    /**
     * Executes the request.
     *
     * This method is called from the WebView thread. To do a non-trivial
     * amount of work, use:
     *      cordova.getThreadPool().execute(runnable);
     *
     * To run on the UI thread, use:
     *     cordova.getActivity().runOnUiThread(runnable);
     *
     * @param action
     *      The action to execute.
     * @param args
     *      The exec() arguments in JSON form.
     * @param command
     *      The callback context used when calling back into JavaScript.
     * @return
     *      Whether the action was valid.
     */
    @Override
    public boolean execute (final String action, final JSONArray args,
                            final CallbackContext command) throws JSONException {

        Notification.setDefaultTriggerReceiver(TriggerReceiver.class);

        cordova.getThreadPool().execute(new Runnable() {
            public void run() {
                if (action.equals("schedule")) {
                    schedule(args);
                    command.success();
                }
                else if (action.equals("update")) {
                    update(args);
                    command.success();
                }
                else if (action.equals("cancel")) {
                    cancel(args);
                    command.success();
                }
                else if (action.equals("cancelAll")) {
                    cancelAll();
                    command.success();
                }
                else if (action.equals("clear")) {
                    clear(args);
                    command.success();
                }
                else if (action.equals("clearAll")) {
                    clearAll();
                    command.success();
                }
                else if (action.equals("isPresent")) {
                    isPresent(args.optInt(0), command);
                }
                else if (action.equals("isScheduled")) {
                    isScheduled(args.optInt(0), command);
                }
                else if (action.equals("isTriggered")) {
                    isTriggered(args.optInt(0), command);
                }
                else if (action.equals("getAllIds")) {
                    getAllIds(command);
                }
                else if (action.equals("getScheduledIds")) {
                    getScheduledIds(command);
                }
                else if (action.equals("getTriggeredIds")) {
                    getTriggeredIds(command);
                }
                else if (action.equals("getSingle")) {
                    getSingle(args, command);
                }
                else if (action.equals("getSingleScheduled")) {
                    getSingleScheduled(args, command);
                }
                else if (action.equals("getSingleTriggered")) {
                    getSingleTriggered(args, command);
                }
                else if (action.equals("getAll")) {
                    getAll(args, command);
                }
                else if (action.equals("getScheduled")) {
                    getScheduled(args, command);
                }
                else if (action.equals("getTriggered")) {
                    getTriggered(args, command);
                }
                else if (action.equals("deviceready")) {
                    deviceready();
                }
            }
        });

        return true;
    }

    /**
     * Schedule multiple local notifications.
     *
     * @param notifications
     *      Properties for each local notification
     */
    private void schedule (JSONArray notifications) {
        for (int i = 0; i < notifications.length(); i++) {
            JSONObject options = notifications.optJSONObject(i);

            Notification notification =
                    getNotificationMgr().schedule(options, TriggerReceiver.class);

            fireEvent("schedule", notification);
        }
    }

    /**
     * Update multiple local notifications.
     *
     * @param updates
     *      Notification properties including their IDs
     */
    private void update (JSONArray updates) {
        for (int i = 0; i < updates.length(); i++) {
            JSONObject update = updates.optJSONObject(i);
            int id = update.optInt("id", 0);

            Notification notification =
                    getNotificationMgr().update(id, update, TriggerReceiver.class);

            fireEvent("update", notification);
        }
    }

    /**
     * Cancel multiple local notifications.
     *
     * @param ids
     *      Set of local notification IDs
     */
    private void cancel (JSONArray ids) {
        for (int i = 0; i < ids.length(); i++) {
            int id = ids.optInt(i, 0);

            Notification notification =
                    getNotificationMgr().cancel(id);

            if (notification != null) {
                fireEvent("cancel", notification);
            }
        }
    }

    /**
     * Cancel all scheduled notifications.
     */
    private void cancelAll() {
        getNotificationMgr().cancelAll();
        fireEvent("cancelall");
    }

    /**
     * Clear multiple local notifications without canceling them.
     *
     * @param ids
     *      Set of local notification IDs
     */
    private void clear(JSONArray ids){
        for (int i = 0; i < ids.length(); i++) {
            int id = ids.optInt(i, 0);

            Notification notification =
                    getNotificationMgr().clear(id);

            if (notification != null) {
                fireEvent("clear", notification);
            }
        }
    }

    /**
     * Clear all triggered notifications without canceling them.
     */
    private void clearAll() {
        getNotificationMgr().clearAll();
        fireEvent("clearall");
    }

    /**
     * If a notification with an ID is present.
     *
     * @param id
     *      Notification ID
     * @param command
     *      The callback context used when calling back into JavaScript.
     */
    private void isPresent (int id, CallbackContext command) {
        boolean exist = getNotificationMgr().exist(id);

        PluginResult result = new PluginResult(
                PluginResult.Status.OK, exist);

        command.sendPluginResult(result);
    }

    /**
     * If a notification with an ID is scheduled.
     *
     * @param id
     *      Notification ID
     * @param command
     *      The callback context used when calling back into JavaScript.
     */
    private void isScheduled (int id, CallbackContext command) {
        boolean exist = getNotificationMgr().exist(
                id, Notification.Type.SCHEDULED);

        PluginResult result = new PluginResult(
                PluginResult.Status.OK, exist);

        command.sendPluginResult(result);
    }

    /**
     * If a notification with an ID is triggered.
     *
     * @param id
     *      Notification ID
     * @param command
     *      The callback context used when calling back into JavaScript.
     */
    private void isTriggered (int id, CallbackContext command) {
        boolean exist = getNotificationMgr().exist(
                id, Notification.Type.TRIGGERED);

        PluginResult result = new PluginResult(
                PluginResult.Status.OK, exist);

        command.sendPluginResult(result);
    }

    /**
     * Set of IDs from all existent notifications.
     *
     * @param command
     *      The callback context used when calling back into JavaScript.
     */
    private void getAllIds (CallbackContext command) {
        List<Integer> ids = getNotificationMgr().getIds();

        command.success(new JSONArray(ids));
    }

    /**
     * Set of IDs from all scheduled notifications.
     *
     * @param command
     *      The callback context used when calling back into JavaScript.
     */
    private void getScheduledIds (CallbackContext command) {
        List<Integer> ids = getNotificationMgr().getIdsByType(
                Notification.Type.SCHEDULED);

        command.success(new JSONArray(ids));
    }

    /**
     * Set of IDs from all triggered notifications.
     *
     * @param command
     *      The callback context used when calling back into JavaScript.
     */
    private void getTriggeredIds (CallbackContext command) {
        List<Integer> ids = getNotificationMgr().getIdsByType(
                Notification.Type.TRIGGERED);

        command.success(new JSONArray(ids));
    }

    /**
     * Options from local notification.
     *
     * @param ids
     *      Set of local notification IDs
     * @param command
     *      The callback context used when calling back into JavaScript.
     */
    private void getSingle (JSONArray ids, CallbackContext command) {
        getOptions(ids.optString(0), Notification.Type.ALL, command);
    }

    /**
     * Options from scheduled notification.
     *
     * @param ids
     *      Set of local notification IDs
     * @param command
     *      The callback context used when calling back into JavaScript.
     */
    private void getSingleScheduled (JSONArray ids, CallbackContext command) {
        getOptions(ids.optString(0), Notification.Type.SCHEDULED, command);
    }

    /**
     * Options from triggered notification.
     *
     * @param ids
     *      Set of local notification IDs
     * @param command
     *      The callback context used when calling back into JavaScript.
     */
    private void getSingleTriggered (JSONArray ids, CallbackContext command) {
        getOptions(ids.optString(0), Notification.Type.TRIGGERED, command);
    }

    /**
     * Set of options from local notification.
     *
     * @param ids
     *      Set of local notification IDs
     * @param command
     *      The callback context used when calling back into JavaScript.
     */
    private void getAll (JSONArray ids, CallbackContext command) {
        getOptions(ids, Notification.Type.ALL, command);
    }

    /**
     * Set of options from scheduled notifications.
     *
     * @param ids
     *      Set of local notification IDs
     * @param command
     *      The callback context used when calling back into JavaScript.
     */
    private void getScheduled (JSONArray ids, CallbackContext command) {
        getOptions(ids, Notification.Type.SCHEDULED, command);
    }

    /**
     * Set of options from triggered notifications.
     *
     * @param ids
     *      Set of local notification IDs
     * @param command
     *      The callback context used when calling back into JavaScript.
     */
    private void getTriggered (JSONArray ids, CallbackContext command) {
        getOptions(ids, Notification.Type.TRIGGERED, command);
    }

    /**
     * Options from local notification.
     *
     * @param id
     *      Set of local notification IDs
     * @param type
     *      The local notification life cycle type
     * @param command
     *      The callback context used when calling back into JavaScript.
     */
    private void getOptions (String id, Notification.Type type,
                             CallbackContext command) {

        JSONArray ids = new JSONArray().put(id);

        JSONObject options =
                getNotificationMgr().getOptionsBy(type, toList(ids)).get(0);

        command.success(options);
    }

    /**
     * Set of options from local notifications.
     *
     * @param ids
     *      Set of local notification IDs
     * @param type
     *      The local notification life cycle type
     * @param command
     *      The callback context used when calling back into JavaScript.
     */
    private void getOptions (JSONArray ids, Notification.Type type,
                             CallbackContext command) {

        List<JSONObject> options;

        if (ids.length() == 0) {
            options = getNotificationMgr().getOptionsByType(type);
        } else {
            options = getNotificationMgr().getOptionsBy(type, toList(ids));
        }

        command.success(new JSONArray(options));
    }

    /**
     * Call all pending callbacks after the deviceready event has been fired.
     */
    private static synchronized void deviceready () {
        isInBackground = false;
        deviceready = true;

        for (String js : eventQueue) {
            sendJavascript(js);
        }

        eventQueue.clear();
    }

    /**
     * Fire given event on JS side. Does inform all event listeners.
     *
     * @param event
     *      The event name
     */
    private void fireEvent (String event) {
        fireEvent(event, null);
    }

    /**
     * Fire given event on JS side. Does inform all event listeners.
     *
     * @param event
     *      The event name
     * @param notification
     *      Optional local notification to pass the id and properties.
     */
    static void fireEvent (String event, Notification notification) {
        String state = getApplicationState();
        String params = "\"" + state + "\"";

        if (notification != null) {
            params = notification.toString() + "," + params;
        }

        String js = "cordova.plugins.notification.local.core.fireEvent(" +
                "\"" + event + "\"," + params + ")";

        sendJavascript(js);
    }

    /**
     * Use this instead of deprecated sendJavascript
     *
     * @param js
     *       JS code snippet as string
     */
    private static synchronized void sendJavascript(final String js) {

        if (!deviceready) {
            eventQueue.add(js);
            return;
        }

        webView.post(new Runnable(){
            public void run(){
                if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.KITKAT) {
                    webView.evaluateJavascript(js, null);
                } else {
                    webView.loadUrl("javascript:" + js);
                }
            }
        });
    }

    /**
     * Convert JSON array of integers to List.
     *
     * @param ary
     *      Array of integers
     */
    private List<Integer> toList (JSONArray ary) {
        ArrayList<Integer> list = new ArrayList<Integer>();

        for (int i = 0; i < ary.length(); i++) {
            list.add(ary.optInt(i));
        }

        return list;
    }

    /**
     * Current application state.
     *
     * @return
     *      "background" or "foreground"
     */
    static String getApplicationState () {
        return isInBackground ? "background" : "foreground";
    }

    /**
     * Notification manager instance.
     */
    private Manager getNotificationMgr() {
        return Manager.getInstance(cordova.getActivity());
    }

}


File: platforms/android/src/nl/xservices/plugins/Toast.java
package nl.xservices.plugins;

import android.view.Gravity;
import org.apache.cordova.CallbackContext;
import org.apache.cordova.CordovaPlugin;
import org.json.JSONArray;
import org.json.JSONException;

/*
    // TODO nice way for the Toast plugin to offer a longer delay than the default short and long options
    // TODO also look at https://github.com/JohnPersano/Supertoasts
    new CountDownTimer(6000, 1000) {
      public void onTick(long millisUntilFinished) {toast.show();}
      public void onFinish() {toast.show();}
    }.start();

    Also, check https://github.com/JohnPersano/SuperToasts
 */
public class Toast extends CordovaPlugin {

  private static final String ACTION_SHOW_EVENT = "show";

  private android.widget.Toast mostRecentToast;

  @Override
  public boolean execute(String action, JSONArray args, final CallbackContext callbackContext) throws JSONException {
    if (ACTION_SHOW_EVENT.equals(action)) {

      if (webView.isPaused()) {
        // suppress while paused
        return true;
      }

      final String message = args.getString(0);
      final String duration = args.getString(1);
      final String position = args.getString(2);

      cordova.getActivity().runOnUiThread(new Runnable() {
        public void run() {
          android.widget.Toast toast = android.widget.Toast.makeText(webView.getContext(), message, 0);

          if ("top".equals(position)) {
            toast.setGravity(Gravity.TOP|Gravity.CENTER_HORIZONTAL, 0, 20);
          } else  if ("bottom".equals(position)) {
            toast.setGravity(Gravity.BOTTOM|Gravity.CENTER_HORIZONTAL, 0, 20);
          } else if ("center".equals(position)) {
            toast.setGravity(Gravity.CENTER_VERTICAL|Gravity.CENTER_HORIZONTAL, 0, 0);
          } else {
            callbackContext.error("invalid position. valid options are 'top', 'center' and 'bottom'");
            return;
          }

          if ("short".equals(duration)) {
            toast.setDuration(android.widget.Toast.LENGTH_SHORT);
          } else if ("long".equals(duration)) {
            toast.setDuration(android.widget.Toast.LENGTH_LONG);
          } else {
            callbackContext.error("invalid duration. valid options are 'short' and 'long'");
            return;
          }

          toast.show();
          mostRecentToast = toast;
          callbackContext.success();
        }
      });

      return true;
    } else {
      callbackContext.error("toast." + action + " is not a supported function. Did you mean '" + ACTION_SHOW_EVENT + "'?");
      return false;
    }
  }

  @Override
  public void onPause(boolean multitasking) {
    if (mostRecentToast != null) {
      mostRecentToast.cancel();
    }
  }
}

File: plugins/de.appplant.cordova.plugin.local-notification/src/android/LocalNotification.java
/*
 * Copyright (c) 2013-2015 by appPlant UG. All rights reserved.
 *
 * @APPPLANT_LICENSE_HEADER_START@
 *
 * This file contains Original Code and/or Modifications of Original Code
 * as defined in and that are subject to the Apache License
 * Version 2.0 (the 'License'). You may not use this file except in
 * compliance with the License. Please obtain a copy of the License at
 * http://opensource.org/licenses/Apache-2.0/ and read it before using this
 * file.
 *
 * The Original Code and all software distributed under the License are
 * distributed on an 'AS IS' basis, WITHOUT WARRANTY OF ANY KIND, EITHER
 * EXPRESS OR IMPLIED, AND APPLE HEREBY DISCLAIMS ALL SUCH WARRANTIES,
 * INCLUDING WITHOUT LIMITATION, ANY WARRANTIES OF MERCHANTABILITY,
 * FITNESS FOR A PARTICULAR PURPOSE, QUIET ENJOYMENT OR NON-INFRINGEMENT.
 * Please see the License for the specific language governing rights and
 * limitations under the License.
 *
 * @APPPLANT_LICENSE_HEADER_END@
 */

package de.appplant.cordova.plugin.localnotification;

import android.os.Build;

import org.apache.cordova.CallbackContext;
import org.apache.cordova.CordovaInterface;
import org.apache.cordova.CordovaPlugin;
import org.apache.cordova.CordovaWebView;
import org.apache.cordova.PluginResult;
import org.json.JSONArray;
import org.json.JSONException;
import org.json.JSONObject;

import java.util.ArrayList;
import java.util.List;

import de.appplant.cordova.plugin.notification.Manager;
import de.appplant.cordova.plugin.notification.Notification;

/**
 * This plugin utilizes the Android AlarmManager in combination with local
 * notifications. When a local notification is scheduled the alarm manager takes
 * care of firing the event. When the event is processed, a notification is put
 * in the Android notification center and status bar.
 */
public class LocalNotification extends CordovaPlugin {

    // Reference to the web view for static access
    private static CordovaWebView webView = null;

    // Indicates if the device is ready (to receive events)
    private static Boolean deviceready = false;

    // To inform the user about the state of the app in callbacks
    protected static Boolean isInBackground = true;

    // Queues all events before deviceready
    private static ArrayList<String> eventQueue = new ArrayList<String>();

    /**
     * Called after plugin construction and fields have been initialized.
     * Prefer to use pluginInitialize instead since there is no value in
     * having parameters on the initialize() function.
     *
     * pluginInitialize is not available for cordova 3.0-3.5 !
     */
    @Override
    public void initialize (CordovaInterface cordova, CordovaWebView webView) {
        LocalNotification.webView = super.webView;
    }

    /**
     * Called when the system is about to start resuming a previous activity.
     *
     * @param multitasking
     *      Flag indicating if multitasking is turned on for app
     */
    @Override
    public void onPause(boolean multitasking) {
        super.onPause(multitasking);
        isInBackground = true;
    }

    /**
     * Called when the activity will start interacting with the user.
     *
     * @param multitasking
     *      Flag indicating if multitasking is turned on for app
     */
    @Override
    public void onResume(boolean multitasking) {
        super.onResume(multitasking);
        isInBackground = false;
        deviceready();
    }

    /**
     * The final call you receive before your activity is destroyed.
     */
    @Override
    public void onDestroy() {
        deviceready = false;
        isInBackground = true;
    }

    /**
     * Executes the request.
     *
     * This method is called from the WebView thread. To do a non-trivial
     * amount of work, use:
     *      cordova.getThreadPool().execute(runnable);
     *
     * To run on the UI thread, use:
     *     cordova.getActivity().runOnUiThread(runnable);
     *
     * @param action
     *      The action to execute.
     * @param args
     *      The exec() arguments in JSON form.
     * @param command
     *      The callback context used when calling back into JavaScript.
     * @return
     *      Whether the action was valid.
     */
    @Override
    public boolean execute (final String action, final JSONArray args,
                            final CallbackContext command) throws JSONException {

        Notification.setDefaultTriggerReceiver(TriggerReceiver.class);

        cordova.getThreadPool().execute(new Runnable() {
            public void run() {
                if (action.equals("schedule")) {
                    schedule(args);
                    command.success();
                }
                else if (action.equals("update")) {
                    update(args);
                    command.success();
                }
                else if (action.equals("cancel")) {
                    cancel(args);
                    command.success();
                }
                else if (action.equals("cancelAll")) {
                    cancelAll();
                    command.success();
                }
                else if (action.equals("clear")) {
                    clear(args);
                    command.success();
                }
                else if (action.equals("clearAll")) {
                    clearAll();
                    command.success();
                }
                else if (action.equals("isPresent")) {
                    isPresent(args.optInt(0), command);
                }
                else if (action.equals("isScheduled")) {
                    isScheduled(args.optInt(0), command);
                }
                else if (action.equals("isTriggered")) {
                    isTriggered(args.optInt(0), command);
                }
                else if (action.equals("getAllIds")) {
                    getAllIds(command);
                }
                else if (action.equals("getScheduledIds")) {
                    getScheduledIds(command);
                }
                else if (action.equals("getTriggeredIds")) {
                    getTriggeredIds(command);
                }
                else if (action.equals("getSingle")) {
                    getSingle(args, command);
                }
                else if (action.equals("getSingleScheduled")) {
                    getSingleScheduled(args, command);
                }
                else if (action.equals("getSingleTriggered")) {
                    getSingleTriggered(args, command);
                }
                else if (action.equals("getAll")) {
                    getAll(args, command);
                }
                else if (action.equals("getScheduled")) {
                    getScheduled(args, command);
                }
                else if (action.equals("getTriggered")) {
                    getTriggered(args, command);
                }
                else if (action.equals("deviceready")) {
                    deviceready();
                }
            }
        });

        return true;
    }

    /**
     * Schedule multiple local notifications.
     *
     * @param notifications
     *      Properties for each local notification
     */
    private void schedule (JSONArray notifications) {
        for (int i = 0; i < notifications.length(); i++) {
            JSONObject options = notifications.optJSONObject(i);

            Notification notification =
                    getNotificationMgr().schedule(options, TriggerReceiver.class);

            fireEvent("schedule", notification);
        }
    }

    /**
     * Update multiple local notifications.
     *
     * @param updates
     *      Notification properties including their IDs
     */
    private void update (JSONArray updates) {
        for (int i = 0; i < updates.length(); i++) {
            JSONObject update = updates.optJSONObject(i);
            int id = update.optInt("id", 0);

            Notification notification =
                    getNotificationMgr().update(id, update, TriggerReceiver.class);

            fireEvent("update", notification);
        }
    }

    /**
     * Cancel multiple local notifications.
     *
     * @param ids
     *      Set of local notification IDs
     */
    private void cancel (JSONArray ids) {
        for (int i = 0; i < ids.length(); i++) {
            int id = ids.optInt(i, 0);

            Notification notification =
                    getNotificationMgr().cancel(id);

            if (notification != null) {
                fireEvent("cancel", notification);
            }
        }
    }

    /**
     * Cancel all scheduled notifications.
     */
    private void cancelAll() {
        getNotificationMgr().cancelAll();
        fireEvent("cancelall");
    }

    /**
     * Clear multiple local notifications without canceling them.
     *
     * @param ids
     *      Set of local notification IDs
     */
    private void clear(JSONArray ids){
        for (int i = 0; i < ids.length(); i++) {
            int id = ids.optInt(i, 0);

            Notification notification =
                    getNotificationMgr().clear(id);

            if (notification != null) {
                fireEvent("clear", notification);
            }
        }
    }

    /**
     * Clear all triggered notifications without canceling them.
     */
    private void clearAll() {
        getNotificationMgr().clearAll();
        fireEvent("clearall");
    }

    /**
     * If a notification with an ID is present.
     *
     * @param id
     *      Notification ID
     * @param command
     *      The callback context used when calling back into JavaScript.
     */
    private void isPresent (int id, CallbackContext command) {
        boolean exist = getNotificationMgr().exist(id);

        PluginResult result = new PluginResult(
                PluginResult.Status.OK, exist);

        command.sendPluginResult(result);
    }

    /**
     * If a notification with an ID is scheduled.
     *
     * @param id
     *      Notification ID
     * @param command
     *      The callback context used when calling back into JavaScript.
     */
    private void isScheduled (int id, CallbackContext command) {
        boolean exist = getNotificationMgr().exist(
                id, Notification.Type.SCHEDULED);

        PluginResult result = new PluginResult(
                PluginResult.Status.OK, exist);

        command.sendPluginResult(result);
    }

    /**
     * If a notification with an ID is triggered.
     *
     * @param id
     *      Notification ID
     * @param command
     *      The callback context used when calling back into JavaScript.
     */
    private void isTriggered (int id, CallbackContext command) {
        boolean exist = getNotificationMgr().exist(
                id, Notification.Type.TRIGGERED);

        PluginResult result = new PluginResult(
                PluginResult.Status.OK, exist);

        command.sendPluginResult(result);
    }

    /**
     * Set of IDs from all existent notifications.
     *
     * @param command
     *      The callback context used when calling back into JavaScript.
     */
    private void getAllIds (CallbackContext command) {
        List<Integer> ids = getNotificationMgr().getIds();

        command.success(new JSONArray(ids));
    }

    /**
     * Set of IDs from all scheduled notifications.
     *
     * @param command
     *      The callback context used when calling back into JavaScript.
     */
    private void getScheduledIds (CallbackContext command) {
        List<Integer> ids = getNotificationMgr().getIdsByType(
                Notification.Type.SCHEDULED);

        command.success(new JSONArray(ids));
    }

    /**
     * Set of IDs from all triggered notifications.
     *
     * @param command
     *      The callback context used when calling back into JavaScript.
     */
    private void getTriggeredIds (CallbackContext command) {
        List<Integer> ids = getNotificationMgr().getIdsByType(
                Notification.Type.TRIGGERED);

        command.success(new JSONArray(ids));
    }

    /**
     * Options from local notification.
     *
     * @param ids
     *      Set of local notification IDs
     * @param command
     *      The callback context used when calling back into JavaScript.
     */
    private void getSingle (JSONArray ids, CallbackContext command) {
        getOptions(ids.optString(0), Notification.Type.ALL, command);
    }

    /**
     * Options from scheduled notification.
     *
     * @param ids
     *      Set of local notification IDs
     * @param command
     *      The callback context used when calling back into JavaScript.
     */
    private void getSingleScheduled (JSONArray ids, CallbackContext command) {
        getOptions(ids.optString(0), Notification.Type.SCHEDULED, command);
    }

    /**
     * Options from triggered notification.
     *
     * @param ids
     *      Set of local notification IDs
     * @param command
     *      The callback context used when calling back into JavaScript.
     */
    private void getSingleTriggered (JSONArray ids, CallbackContext command) {
        getOptions(ids.optString(0), Notification.Type.TRIGGERED, command);
    }

    /**
     * Set of options from local notification.
     *
     * @param ids
     *      Set of local notification IDs
     * @param command
     *      The callback context used when calling back into JavaScript.
     */
    private void getAll (JSONArray ids, CallbackContext command) {
        getOptions(ids, Notification.Type.ALL, command);
    }

    /**
     * Set of options from scheduled notifications.
     *
     * @param ids
     *      Set of local notification IDs
     * @param command
     *      The callback context used when calling back into JavaScript.
     */
    private void getScheduled (JSONArray ids, CallbackContext command) {
        getOptions(ids, Notification.Type.SCHEDULED, command);
    }

    /**
     * Set of options from triggered notifications.
     *
     * @param ids
     *      Set of local notification IDs
     * @param command
     *      The callback context used when calling back into JavaScript.
     */
    private void getTriggered (JSONArray ids, CallbackContext command) {
        getOptions(ids, Notification.Type.TRIGGERED, command);
    }

    /**
     * Options from local notification.
     *
     * @param id
     *      Set of local notification IDs
     * @param type
     *      The local notification life cycle type
     * @param command
     *      The callback context used when calling back into JavaScript.
     */
    private void getOptions (String id, Notification.Type type,
                             CallbackContext command) {

        JSONArray ids = new JSONArray().put(id);

        JSONObject options =
                getNotificationMgr().getOptionsBy(type, toList(ids)).get(0);

        command.success(options);
    }

    /**
     * Set of options from local notifications.
     *
     * @param ids
     *      Set of local notification IDs
     * @param type
     *      The local notification life cycle type
     * @param command
     *      The callback context used when calling back into JavaScript.
     */
    private void getOptions (JSONArray ids, Notification.Type type,
                             CallbackContext command) {

        List<JSONObject> options;

        if (ids.length() == 0) {
            options = getNotificationMgr().getOptionsByType(type);
        } else {
            options = getNotificationMgr().getOptionsBy(type, toList(ids));
        }

        command.success(new JSONArray(options));
    }

    /**
     * Call all pending callbacks after the deviceready event has been fired.
     */
    private static synchronized void deviceready () {
        isInBackground = false;
        deviceready = true;

        for (String js : eventQueue) {
            sendJavascript(js);
        }

        eventQueue.clear();
    }

    /**
     * Fire given event on JS side. Does inform all event listeners.
     *
     * @param event
     *      The event name
     */
    private void fireEvent (String event) {
        fireEvent(event, null);
    }

    /**
     * Fire given event on JS side. Does inform all event listeners.
     *
     * @param event
     *      The event name
     * @param notification
     *      Optional local notification to pass the id and properties.
     */
    static void fireEvent (String event, Notification notification) {
        String state = getApplicationState();
        String params = "\"" + state + "\"";

        if (notification != null) {
            params = notification.toString() + "," + params;
        }

        String js = "cordova.plugins.notification.local.core.fireEvent(" +
                "\"" + event + "\"," + params + ")";

        sendJavascript(js);
    }

    /**
     * Use this instead of deprecated sendJavascript
     *
     * @param js
     *       JS code snippet as string
     */
    private static synchronized void sendJavascript(final String js) {

        if (!deviceready) {
            eventQueue.add(js);
            return;
        }

        webView.post(new Runnable(){
            public void run(){
                if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.KITKAT) {
                    webView.evaluateJavascript(js, null);
                } else {
                    webView.loadUrl("javascript:" + js);
                }
            }
        });
    }

    /**
     * Convert JSON array of integers to List.
     *
     * @param ary
     *      Array of integers
     */
    private List<Integer> toList (JSONArray ary) {
        ArrayList<Integer> list = new ArrayList<Integer>();

        for (int i = 0; i < ary.length(); i++) {
            list.add(ary.optInt(i));
        }

        return list;
    }

    /**
     * Current application state.
     *
     * @return
     *      "background" or "foreground"
     */
    static String getApplicationState () {
        return isInBackground ? "background" : "foreground";
    }

    /**
     * Notification manager instance.
     */
    private Manager getNotificationMgr() {
        return Manager.getInstance(cordova.getActivity());
    }

}


File: plugins/nl.x-services.plugins.toast/src/android/nl/xservices/plugins/Toast.java
package nl.xservices.plugins;

import android.view.Gravity;
import org.apache.cordova.CallbackContext;
import org.apache.cordova.CordovaPlugin;
import org.json.JSONArray;
import org.json.JSONException;

/*
    // TODO nice way for the Toast plugin to offer a longer delay than the default short and long options
    // TODO also look at https://github.com/JohnPersano/Supertoasts
    new CountDownTimer(6000, 1000) {
      public void onTick(long millisUntilFinished) {toast.show();}
      public void onFinish() {toast.show();}
    }.start();

    Also, check https://github.com/JohnPersano/SuperToasts
 */
public class Toast extends CordovaPlugin {

  private static final String ACTION_SHOW_EVENT = "show";

  private android.widget.Toast mostRecentToast;

  @Override
  public boolean execute(String action, JSONArray args, final CallbackContext callbackContext) throws JSONException {
    if (ACTION_SHOW_EVENT.equals(action)) {

      if (webView.isPaused()) {
        // suppress while paused
        return true;
      }

      final String message = args.getString(0);
      final String duration = args.getString(1);
      final String position = args.getString(2);

      cordova.getActivity().runOnUiThread(new Runnable() {
        public void run() {
          android.widget.Toast toast = android.widget.Toast.makeText(webView.getContext(), message, 0);

          if ("top".equals(position)) {
            toast.setGravity(Gravity.TOP|Gravity.CENTER_HORIZONTAL, 0, 20);
          } else  if ("bottom".equals(position)) {
            toast.setGravity(Gravity.BOTTOM|Gravity.CENTER_HORIZONTAL, 0, 20);
          } else if ("center".equals(position)) {
            toast.setGravity(Gravity.CENTER_VERTICAL|Gravity.CENTER_HORIZONTAL, 0, 0);
          } else {
            callbackContext.error("invalid position. valid options are 'top', 'center' and 'bottom'");
            return;
          }

          if ("short".equals(duration)) {
            toast.setDuration(android.widget.Toast.LENGTH_SHORT);
          } else if ("long".equals(duration)) {
            toast.setDuration(android.widget.Toast.LENGTH_LONG);
          } else {
            callbackContext.error("invalid duration. valid options are 'short' and 'long'");
            return;
          }

          toast.show();
          mostRecentToast = toast;
          callbackContext.success();
        }
      });

      return true;
    } else {
      callbackContext.error("toast." + action + " is not a supported function. Did you mean '" + ACTION_SHOW_EVENT + "'?");
      return false;
    }
  }

  @Override
  public void onPause(boolean multitasking) {
    if (mostRecentToast != null) {
      mostRecentToast.cancel();
    }
  }
}