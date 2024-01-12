Refactoring Types: ['Move Method', 'Move Attribute']
ud/blueflood/http/DefaultHandler.java
/*
 * Copyright 2013 Rackspace
 *
 *    Licensed under the Apache License, Version 2.0 (the "License");
 *    you may not use this file except in compliance with the License.
 *    You may obtain a copy of the License at
 *
 *        http://www.apache.org/licenses/LICENSE-2.0
 *
 *    Unless required by applicable law or agreed to in writing, software
 *    distributed under the License is distributed on an "AS IS" BASIS,
 *    WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 *    See the License for the specific language governing permissions and
 *    limitations under the License.
 */

package com.rackspacecloud.blueflood.http;

import org.jboss.netty.channel.ChannelHandlerContext;
import org.jboss.netty.handler.codec.http.HttpRequest;
import org.jboss.netty.handler.codec.http.HttpResponseStatus;

public class DefaultHandler implements HttpRequestHandler {

    @Override
    public void handle(ChannelHandlerContext ctx, HttpRequest request) {
        HttpResponder.respond(ctx, request, HttpResponseStatus.OK);
    }
}

File: blueflood-http/src/main/java/com/rackspacecloud/blueflood/inputs/handlers/HttpEventsIngestionHandler.java
/*
 * Copyright 2013 Rackspace
 *
 *    Licensed under the Apache License, Version 2.0 (the "License");
 *    you may not use this file except in compliance with the License.
 *    You may obtain a copy of the License at
 *
 *        http://www.apache.org/licenses/LICENSE-2.0
 *
 *    Unless required by applicable law or agreed to in writing, software
 *    distributed under the License is distributed on an "AS IS" BASIS,
 *    WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 *    See the License for the specific language governing permissions and
 *    limitations under the License.
 */

package com.rackspacecloud.blueflood.inputs.handlers;

import com.rackspacecloud.blueflood.http.HttpRequestHandler;
import com.rackspacecloud.blueflood.http.HttpResponder;
import com.rackspacecloud.blueflood.io.GenericElasticSearchIO;
import com.rackspacecloud.blueflood.io.Constants;

import com.rackspacecloud.blueflood.types.Event;
import org.codehaus.jackson.map.ObjectMapper;
import org.jboss.netty.buffer.ChannelBuffers;
import org.jboss.netty.channel.ChannelHandlerContext;
import org.jboss.netty.handler.codec.http.*;
import org.joda.time.DateTime;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.util.*;


public class HttpEventsIngestionHandler implements HttpRequestHandler {
    private static final Logger log = LoggerFactory.getLogger(HttpEventsIngestionHandler.class);
    private GenericElasticSearchIO searchIO;

    public HttpEventsIngestionHandler(GenericElasticSearchIO searchIO) {
        this.searchIO = searchIO;
    }

    @Override
    public void handle(ChannelHandlerContext ctx, HttpRequest request) {
        final String tenantId = request.getHeader(Event.FieldLabels.tenantId.name());
        HttpResponseStatus status = HttpResponseStatus.OK;
        String response = "";
        ObjectMapper objectMapper = new ObjectMapper();
        try {
            Event event = objectMapper.readValue(request.getContent().array(), Event.class);
            if (event.getWhen() == 0) {
                event.setWhen(new DateTime().getMillis() / 1000);
            }

            if (event.getWhat().equals("")) {
                throw new Exception(String.format("Event should contain at least '%s' field.", Event.FieldLabels.what.name()));
            }
            searchIO.insert(tenantId, Arrays.asList(event.toMap()));
        }
        catch (Exception e) {
            log.error(String.format("Exception %s", e.toString()));
            response = String.format("Error: %s", e.getMessage());
            status = HttpResponseStatus.INTERNAL_SERVER_ERROR;
        }
        finally {
            sendResponse(ctx, request, response, status);
        }
    }

    private void sendResponse(ChannelHandlerContext channel, HttpRequest request, String messageBody,
                              HttpResponseStatus status) {
        HttpResponse response = new DefaultHttpResponse(HttpVersion.HTTP_1_1, status);
        if (messageBody != null && !messageBody.isEmpty()) {
            response.setContent(ChannelBuffers.copiedBuffer(messageBody, Constants.DEFAULT_CHARSET));
        }
        HttpResponder.respond(channel, request, response);
    }

}


File: blueflood-http/src/main/java/com/rackspacecloud/blueflood/inputs/handlers/HttpMetricsIngestionHandler.java
/*
 * Copyright 2013-2015 Rackspace
 *
 *    Licensed under the Apache License, Version 2.0 (the "License");
 *    you may not use this file except in compliance with the License.
 *    You may obtain a copy of the License at
 *
 *        http://www.apache.org/licenses/LICENSE-2.0
 *
 *    Unless required by applicable law or agreed to in writing, software
 *    distributed under the License is distributed on an "AS IS" BASIS,
 *    WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 *    See the License for the specific language governing permissions and
 *    limitations under the License.
 */

package com.rackspacecloud.blueflood.inputs.handlers;

import com.codahale.metrics.Counter;
import com.codahale.metrics.Timer;
import com.google.common.util.concurrent.ListenableFuture;
import com.rackspacecloud.blueflood.cache.ConfigTtlProvider;
import com.rackspacecloud.blueflood.exceptions.InvalidDataException;
import com.rackspacecloud.blueflood.http.HttpRequestHandler;
import com.rackspacecloud.blueflood.http.HttpResponder;
import com.rackspacecloud.blueflood.inputs.formats.JSONMetricsContainer;
import com.rackspacecloud.blueflood.io.Constants;
import com.rackspacecloud.blueflood.types.IMetric;
import com.rackspacecloud.blueflood.types.Metric;
import com.rackspacecloud.blueflood.types.MetricsCollection;
import com.rackspacecloud.blueflood.utils.Metrics;
import com.rackspacecloud.blueflood.utils.TimeValue;
import org.codehaus.jackson.JsonParseException;
import org.codehaus.jackson.map.JsonMappingException;
import org.codehaus.jackson.map.ObjectMapper;
import org.codehaus.jackson.map.type.TypeFactory;
import org.jboss.netty.buffer.ChannelBuffers;
import org.jboss.netty.channel.ChannelHandlerContext;
import org.jboss.netty.handler.codec.http.*;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.io.IOException;
import java.util.ArrayList;
import java.util.List;
import java.util.concurrent.TimeoutException;

public class HttpMetricsIngestionHandler implements HttpRequestHandler {
    private static final Logger log = LoggerFactory.getLogger(HttpMetricsIngestionHandler.class);
    private static final Counter requestCount = Metrics.counter(HttpMetricsIngestionHandler.class, "HTTP Request Count");


    protected final ObjectMapper mapper;
    protected final TypeFactory typeFactory;
    private final HttpMetricsIngestionServer.Processor processor;
    private final TimeValue timeout;

    // Metrics
    private static final Timer jsonTimer = Metrics.timer(HttpMetricsIngestionHandler.class, "HTTP Ingestion json processing timer");
    private static final Timer persistingTimer = Metrics.timer(HttpMetricsIngestionHandler.class, "HTTP Ingestion persisting timer");
    private static final Timer sendResponseTimer = Metrics.timer(HttpMetricsIngestionHandler.class, "HTTP Ingestion response sending timer");


    public HttpMetricsIngestionHandler(HttpMetricsIngestionServer.Processor processor, TimeValue timeout) {
        this.mapper = new ObjectMapper();
        this.typeFactory = TypeFactory.defaultInstance();
        this.timeout = timeout;
        this.processor = processor;
    }

    protected JSONMetricsContainer createContainer(String body, String tenantId) throws JsonParseException, JsonMappingException, IOException {
        List<JSONMetricsContainer.JSONMetric> jsonMetrics =
                mapper.readValue(
                        body,
                        typeFactory.constructCollectionType(List.class,
                                JSONMetricsContainer.JSONMetric.class)
                );
        return new JSONMetricsContainer(tenantId, jsonMetrics);
    }

    @Override
    public void handle(ChannelHandlerContext ctx, HttpRequest request) {
        try {
            requestCount.inc();
            final String tenantId = request.getHeader("tenantId");
            JSONMetricsContainer jsonMetricsContainer = null;
            final Timer.Context jsonTimerContext = jsonTimer.time();

            final String body = request.getContent().toString(Constants.DEFAULT_CHARSET);
            try {
                jsonMetricsContainer = createContainer(body, tenantId);
                if (!jsonMetricsContainer.isValid()) {
                    throw new IOException("Invalid JSONMetricsContainer");
                }
            } catch (JsonParseException e) {
                log.warn("Exception parsing content", e);
                sendResponse(ctx, request, "Cannot parse content", HttpResponseStatus.BAD_REQUEST);
                return;
            } catch (JsonMappingException e) {
                log.warn("Exception parsing content", e);
                sendResponse(ctx, request, "Cannot parse content", HttpResponseStatus.BAD_REQUEST);
                return;
            } catch (IOException e) {
                log.warn("IO Exception parsing content", e);
                sendResponse(ctx, request, "Cannot parse content", HttpResponseStatus.BAD_REQUEST);
                return;
            } catch (Exception e) {
                log.warn("Other exception while trying to parse content", e);
                sendResponse(ctx, request, "Failed parsing content", HttpResponseStatus.INTERNAL_SERVER_ERROR);
                return;
            }

            if (jsonMetricsContainer == null) {
                log.warn(ctx.getChannel().getRemoteAddress() + " No valid metrics");
                sendResponse(ctx, request, "No valid metrics", HttpResponseStatus.BAD_REQUEST);
                return;
            }

            List<Metric> containerMetrics;
            try {
                containerMetrics = jsonMetricsContainer.toMetrics();
                forceTTLsIfConfigured(containerMetrics);
            } catch (InvalidDataException ex) {
                // todo: we should measure these. if they spike, we track down the bad client.
                // this is strictly a client problem. Someting wasn't right (data out of range, etc.)
                log.warn(ctx.getChannel().getRemoteAddress() + " " + ex.getMessage());
                sendResponse(ctx, request, "Invalid data " + ex.getMessage(), HttpResponseStatus.BAD_REQUEST);
                return;
            } catch (Exception e) {
                // todo: when you see these in logs, go and fix them (throw InvalidDataExceptions) so they can be reduced
                // to single-line log statements.
                log.warn("Exception converting JSON container to metric objects", e);
                // This could happen if clients send BigIntegers as metric values. BF doesn't handle them. So let's send a
                // BAD REQUEST message until we start handling BigIntegers.
                sendResponse(ctx, request, "Error converting JSON payload to metric objects",
                        HttpResponseStatus.BAD_REQUEST);
                return;
            } finally {
                jsonTimerContext.stop();
            }

            if (containerMetrics == null || containerMetrics.isEmpty()) {
                log.warn(ctx.getChannel().getRemoteAddress() + " No valid metrics");
                sendResponse(ctx, request, "No valid metrics", HttpResponseStatus.BAD_REQUEST);
            }

            final MetricsCollection collection = new MetricsCollection();
            collection.add(new ArrayList<IMetric>(containerMetrics));
            final Timer.Context persistingTimerContext = persistingTimer.time();
            try {
                ListenableFuture<List<Boolean>> futures = processor.apply(collection);
                List<Boolean> persisteds = futures.get(timeout.getValue(), timeout.getUnit());
                for (Boolean persisted : persisteds) {
                    if (!persisted) {
                        sendResponse(ctx, request, null, HttpResponseStatus.INTERNAL_SERVER_ERROR);
                        return;
                    }
                }
                sendResponse(ctx, request, null, HttpResponseStatus.OK);
            } catch (TimeoutException e) {
                sendResponse(ctx, request, "Timed out persisting metrics", HttpResponseStatus.ACCEPTED);
            } catch (Exception e) {
                log.error("Exception persisting metrics", e);
                sendResponse(ctx, request, "Error persisting metrics", HttpResponseStatus.INTERNAL_SERVER_ERROR);
            } finally {
                persistingTimerContext.stop();
            }
        } finally {
            requestCount.dec();
        }
    }

    private void forceTTLsIfConfigured(List<Metric> containerMetrics) {
        ConfigTtlProvider configTtlProvider = ConfigTtlProvider.getInstance();

        if(configTtlProvider.areTTLsForced()) {
            for(Metric m : containerMetrics) {
                m.setTtl(configTtlProvider.getConfigTTLForIngestion());
            }
        }
    }

    public static void sendResponse(ChannelHandlerContext channel, HttpRequest request, String messageBody, HttpResponseStatus status) {
        HttpResponse response = new DefaultHttpResponse(HttpVersion.HTTP_1_1, status);
        final Timer.Context sendResponseTimerContext = sendResponseTimer.time();

        try {
            if (messageBody != null && !messageBody.isEmpty()) {
                response.setContent(ChannelBuffers.copiedBuffer(messageBody, Constants.DEFAULT_CHARSET));
            }
            HttpResponder.respond(channel, request, response);
        } finally {
            sendResponseTimerContext.stop();
        }
    }
}


File: blueflood-http/src/main/java/com/rackspacecloud/blueflood/inputs/handlers/HttpStatsDIngestionHandler.java
/*
 * Copyright 2014-2015 Rackspace
 *
 *    Licensed under the Apache License, Version 2.0 (the "License");
 *    you may not use this file except in compliance with the License.
 *    You may obtain a copy of the License at
 *
 *        http://www.apache.org/licenses/LICENSE-2.0
 *
 *    Unless required by applicable law or agreed to in writing, software
 *    distributed under the License is distributed on an "AS IS" BASIS,
 *    WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 *    See the License for the specific language governing permissions and
 *    limitations under the License.
 */

package com.rackspacecloud.blueflood.inputs.handlers;

import com.codahale.metrics.Counter;
import com.codahale.metrics.Timer;
import com.google.common.util.concurrent.ListenableFuture;
import com.google.gson.Gson;
import com.google.gson.JsonParseException;
import com.netflix.astyanax.connectionpool.exceptions.ConnectionException;
import com.rackspacecloud.blueflood.concurrent.FunctionWithThreadPool;
import com.rackspacecloud.blueflood.http.HttpRequestHandler;
import com.rackspacecloud.blueflood.inputs.handlers.wrappers.Bundle;
import com.rackspacecloud.blueflood.io.AstyanaxWriter;
import com.rackspacecloud.blueflood.io.CassandraModel;
import com.rackspacecloud.blueflood.io.Constants;
import com.rackspacecloud.blueflood.types.IMetric;
import com.rackspacecloud.blueflood.types.MetricsCollection;
import com.rackspacecloud.blueflood.utils.Metrics;
import com.rackspacecloud.blueflood.utils.TimeValue;
import org.jboss.netty.channel.ChannelHandlerContext;
import org.jboss.netty.handler.codec.http.HttpRequest;
import org.jboss.netty.handler.codec.http.HttpResponseStatus;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.util.Collection;
import java.util.List;
import java.util.concurrent.Callable;
import java.util.concurrent.ThreadPoolExecutor;
import java.util.concurrent.TimeoutException;

public class HttpStatsDIngestionHandler implements HttpRequestHandler {
    
    private static final Logger log = LoggerFactory.getLogger(HttpStatsDIngestionHandler.class);
    
    private static final Timer handlerTimer = Metrics.timer(HttpStatsDIngestionHandler.class, "HTTP statsd metrics ingestion timer");
    private static final Counter requestCount = Metrics.counter(HttpStatsDIngestionHandler.class, "HTTP Request Count");
    
    private final HttpMetricsIngestionServer.Processor processor;
    private final TimeValue timeout;
    
    public HttpStatsDIngestionHandler(HttpMetricsIngestionServer.Processor processor, TimeValue timeout) {
        this.processor = processor;
        this.timeout = timeout;
    }
    
    // our own stuff.
    @Override
    public void handle(ChannelHandlerContext ctx, HttpRequest request) {
        
        final Timer.Context timerContext = handlerTimer.time();
        
        // this is all JSON.
        final String body = request.getContent().toString(Constants.DEFAULT_CHARSET);
        try {
            // block until things get ingested.
            requestCount.inc();
            MetricsCollection collection = new MetricsCollection();
            collection.add(PreaggregateConversions.buildMetricsCollection(createBundle(body)));
            ListenableFuture<List<Boolean>> futures = processor.apply(collection);
            List<Boolean> persisteds = futures.get(timeout.getValue(), timeout.getUnit());
            for (Boolean persisted : persisteds) {
                if (!persisted) {
                    HttpMetricsIngestionHandler.sendResponse(ctx, request, null, HttpResponseStatus.INTERNAL_SERVER_ERROR);
                    return;
                }
            }
            HttpMetricsIngestionHandler.sendResponse(ctx, request, null, HttpResponseStatus.OK);

        } catch (JsonParseException ex) {
            log.debug(String.format("BAD JSON: %s", body));
            log.error(ex.getMessage(), ex);
            HttpMetricsIngestionHandler.sendResponse(ctx, request, ex.getMessage(), HttpResponseStatus.BAD_REQUEST);
        } catch (ConnectionException ex) {
            log.error(ex.getMessage(), ex);
            HttpMetricsIngestionHandler.sendResponse(ctx, request, "Internal error saving data", HttpResponseStatus.INTERNAL_SERVER_ERROR);
        } catch (TimeoutException ex) {
            HttpMetricsIngestionHandler.sendResponse(ctx, request, "Timed out persisting metrics", HttpResponseStatus.ACCEPTED);
        } catch (Exception ex) {
            log.debug(String.format("BAD JSON: %s", body));
            log.error("Other exception while trying to parse content", ex);
            HttpMetricsIngestionHandler.sendResponse(ctx, request, "Failed parsing content", HttpResponseStatus.INTERNAL_SERVER_ERROR);
        } finally {
            requestCount.dec();
            timerContext.stop();
        }
    }
    
    public static Bundle createBundle(String json) {
        Bundle bundle = new Gson().fromJson(json, Bundle.class);
        return bundle;
    }

    public static class WriteMetrics extends FunctionWithThreadPool<Collection<IMetric>, ListenableFuture<Boolean>> {
        private final AstyanaxWriter writer;
        
        public WriteMetrics(ThreadPoolExecutor executor, AstyanaxWriter writer) {
            super(executor);
            this.writer = writer;
        }

        @Override
        public ListenableFuture<Boolean> apply(final Collection<IMetric> input) throws Exception {
            return this.getThreadPool().submit(new Callable<Boolean>() {
                @Override
                public Boolean call() throws Exception {
                    writer.insertMetrics(input, CassandraModel.CF_METRICS_PREAGGREGATED_FULL);
                    return true;
                }
            });
        }
    }
}
