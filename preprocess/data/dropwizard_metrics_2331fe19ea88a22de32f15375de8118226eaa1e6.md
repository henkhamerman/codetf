Refactoring Types: ['Extract Method']
io/dropwizard/metrics/jersey2/InstrumentedResourceMethodApplicationListener.java
package io.dropwizard.metrics.jersey2;

import static io.dropwizard.metrics.MetricRegistry.name;
import jersey.repackaged.com.google.common.collect.ImmutableMap;

import org.glassfish.jersey.server.model.Resource;
import org.glassfish.jersey.server.model.ResourceMethod;
import org.glassfish.jersey.server.monitoring.ApplicationEvent;
import org.glassfish.jersey.server.monitoring.ApplicationEventListener;
import org.glassfish.jersey.server.monitoring.RequestEvent;
import org.glassfish.jersey.server.monitoring.RequestEventListener;

import io.dropwizard.metrics.annotation.ExceptionMetered;
import io.dropwizard.metrics.annotation.Metered;
import io.dropwizard.metrics.annotation.Timed;

import io.dropwizard.metrics.Meter;
import io.dropwizard.metrics.MetricName;
import io.dropwizard.metrics.MetricRegistry;
import io.dropwizard.metrics.Timer;

import javax.ws.rs.ext.Provider;

import java.lang.reflect.Method;

/**
 * An application event listener that listens for Jersey application initialization to
 * be finished, then creates a map of resource method that have metrics annotations.
 * <p/>
 * Finally, it listens for method start events, and returns a {@link RequestEventListener}
 * that updates the relevant metric for suitably annotated methods when it gets the
 * request events indicating that the method is about to be invoked, or just got done
 * being invoked.
 */

@Provider
public class InstrumentedResourceMethodApplicationListener implements ApplicationEventListener {

    private final MetricRegistry metrics;
    private ImmutableMap<Method, Timer> timers = ImmutableMap.of();
    private ImmutableMap<Method, Meter> meters = ImmutableMap.of();
    private ImmutableMap<Method, ExceptionMeterMetric> exceptionMeters = ImmutableMap.of();

    /**
     * Construct an application event listener using the given metrics registry.
     * <p/>
     * <p/>
     * When using this constructor, the {@link InstrumentedResourceMethodApplicationListener}
     * should be added to a Jersey {@code ResourceConfig} as a singleton.
     *
     * @param metrics a {@link MetricRegistry}
     */
    public InstrumentedResourceMethodApplicationListener(final MetricRegistry metrics) {
        this.metrics = metrics;
    }

    /**
     * A private class to maintain the metric for a method annotated with the
     * {@link ExceptionMetered} annotation, which needs to maintain both a meter
     * and a cause for which the meter should be updated.
     */
    private static class ExceptionMeterMetric {
        public final Meter meter;
        public final Class<? extends Throwable> cause;

        public ExceptionMeterMetric(final MetricRegistry registry,
                                    final ResourceMethod method,
                                    final ExceptionMetered exceptionMetered) {
            final MetricName name = chooseName(exceptionMetered.name(),
                    exceptionMetered.absolute(), method, ExceptionMetered.DEFAULT_NAME_SUFFIX);
            this.meter = registry.meter(name);
            this.cause = exceptionMetered.cause();
        }
    }

    private static class TimerRequestEventListener implements RequestEventListener {
        private final ImmutableMap<Method, Timer> timers;
        private Timer.Context context = null;

        public TimerRequestEventListener(final ImmutableMap<Method, Timer> timers) {
            this.timers = timers;
        }

        @Override
        public void onEvent(RequestEvent event) {
            if (event.getType() == RequestEvent.Type.RESOURCE_METHOD_START) {
                final Timer timer = this.timers.get(event.getUriInfo()
                        .getMatchedResourceMethod().getInvocable().getDefinitionMethod());
                if (timer != null) {
                    this.context = timer.time();
                }
            } else if (event.getType() == RequestEvent.Type.RESOURCE_METHOD_FINISHED) {
                if (this.context != null) {
                    this.context.close();
                }
            }
        }
    }

    private static class MeterRequestEventListener implements RequestEventListener {
        private final ImmutableMap<Method, Meter> meters;

        public MeterRequestEventListener(final ImmutableMap<Method, Meter> meters) {
            this.meters = meters;
        }

        @Override
        public void onEvent(RequestEvent event) {
            if (event.getType() == RequestEvent.Type.RESOURCE_METHOD_START) {
                final Meter meter = this.meters.get(event.getUriInfo()
                        .getMatchedResourceMethod().getInvocable().getDefinitionMethod());
                if (meter != null) {
                    meter.mark();
                }
            }
        }
    }

    private static class ExceptionMeterRequestEventListener implements RequestEventListener {
        private final ImmutableMap<Method, ExceptionMeterMetric> exceptionMeters;

        public ExceptionMeterRequestEventListener(final ImmutableMap<Method, ExceptionMeterMetric> exceptionMeters) {
            this.exceptionMeters = exceptionMeters;
        }

        @Override
        public void onEvent(RequestEvent event) {
            if (event.getType() == RequestEvent.Type.ON_EXCEPTION) {
                final ResourceMethod method = event.getUriInfo().getMatchedResourceMethod();
                final ExceptionMeterMetric metric = (method != null) ?
                        this.exceptionMeters.get(method.getInvocable().getDefinitionMethod()) : null;

                if (metric != null) {
                    if (metric.cause.isAssignableFrom(event.getException().getClass()) ||
                            (event.getException().getCause() != null &&
                                    metric.cause.isAssignableFrom(event.getException().getCause().getClass()))) {
                        metric.meter.mark();
                    }
                }
            }
        }
    }

    private static class ChainedRequestEventListener implements RequestEventListener {
        private final RequestEventListener[] listeners;

        private ChainedRequestEventListener(final RequestEventListener... listeners) {
            this.listeners = listeners;
        }

        @Override
        public void onEvent(final RequestEvent event) {
            for (RequestEventListener listener : listeners) {
                listener.onEvent(event);
            }
        }
    }

    @Override
    public void onEvent(ApplicationEvent event) {
        if (event.getType() == ApplicationEvent.Type.INITIALIZATION_APP_FINISHED) {
            final ImmutableMap.Builder<Method, Timer> timerBuilder = ImmutableMap.<Method, Timer>builder();
            final ImmutableMap.Builder<Method, Meter> meterBuilder = ImmutableMap.<Method, Meter>builder();
            final ImmutableMap.Builder<Method, ExceptionMeterMetric> exceptionMeterBuilder = ImmutableMap.<Method, ExceptionMeterMetric>builder();

            for (final Resource resource : event.getResourceModel().getResources()) {
                for (final ResourceMethod method : resource.getAllMethods()) {
                    registerTimedAnnotations(timerBuilder, method);
                    registerMeteredAnnotations(meterBuilder, method);
                    registerExceptionMeteredAnnotations(exceptionMeterBuilder, method);
                }

                for (final Resource childResource : resource.getChildResources()) {
                    for (final ResourceMethod method : childResource.getAllMethods()) {
                        registerTimedAnnotations(timerBuilder, method);
                        registerMeteredAnnotations(meterBuilder, method);
                        registerExceptionMeteredAnnotations(exceptionMeterBuilder, method);
                    }
                }
            }

            timers = timerBuilder.build();
            meters = meterBuilder.build();
            exceptionMeters = exceptionMeterBuilder.build();
        }
    }

    @Override
    public RequestEventListener onRequest(final RequestEvent event) {
        final RequestEventListener listener = new ChainedRequestEventListener(
                new TimerRequestEventListener(timers),
                new MeterRequestEventListener(meters),
                new ExceptionMeterRequestEventListener(exceptionMeters));

        return listener;
    }

    private void registerTimedAnnotations(final ImmutableMap.Builder<Method, Timer> builder,
                                          final ResourceMethod method) {
        final Method definitionMethod = method.getInvocable().getDefinitionMethod();
        final Timed annotation = definitionMethod.getAnnotation(Timed.class);

        if (annotation != null) {
            builder.put(definitionMethod, timerMetric(this.metrics, method, annotation));
        }
    }

    private void registerMeteredAnnotations(final ImmutableMap.Builder<Method, Meter> builder,
                                            final ResourceMethod method) {
        final Method definitionMethod = method.getInvocable().getDefinitionMethod();
        final Metered annotation = definitionMethod.getAnnotation(Metered.class);

        if (annotation != null) {
            builder.put(definitionMethod, meterMetric(metrics, method, annotation));
        }
    }

    private void registerExceptionMeteredAnnotations(final ImmutableMap.Builder<Method, ExceptionMeterMetric> builder,
                                                     final ResourceMethod method) {
        final Method definitionMethod = method.getInvocable().getDefinitionMethod();
        final ExceptionMetered annotation = definitionMethod.getAnnotation(ExceptionMetered.class);

        if (annotation != null) {
            builder.put(definitionMethod, new ExceptionMeterMetric(metrics, method, annotation));
        }
    }

    private static Timer timerMetric(final MetricRegistry registry,
                                     final ResourceMethod method,
                                     final Timed timed) {
        final MetricName name = chooseName(timed.name(), timed.absolute(), method);
        return registry.timer(name);
    }

    private static Meter meterMetric(final MetricRegistry registry,
                                     final ResourceMethod method,
                                     final Metered metered) {
        final MetricName name = chooseName(metered.name(), metered.absolute(), method);
        return registry.meter(name);
    }

    protected static MetricName chooseName(final String explicitName, final boolean absolute, final ResourceMethod method, final String... suffixes) {
        if (explicitName != null && !explicitName.isEmpty()) {
            if (absolute) {
                return MetricName.build(explicitName);
            }
            return name(method.getInvocable().getDefinitionMethod().getDeclaringClass(), explicitName);
        }

        Method definitionMethod = method.getInvocable().getDefinitionMethod();
        return MetricName.join(name(definitionMethod.getDeclaringClass(), definitionMethod.getName()), MetricName.build(suffixes));
    }
}


File: metrics-jersey2/src/test/java/io/dropwizard/metrics/jersey2/SingletonMetricsJerseyTest.java
package io.dropwizard.metrics.jersey2;

import static io.dropwizard.metrics.MetricRegistry.name;

import org.glassfish.jersey.client.ClientResponse;
import org.glassfish.jersey.server.ResourceConfig;
import org.glassfish.jersey.test.JerseyTest;
import org.junit.Test;

import io.dropwizard.metrics.jersey2.resources.InstrumentedResource;

import io.dropwizard.metrics.jersey2.InstrumentedResourceMethodApplicationListener;
import io.dropwizard.metrics.jersey2.MetricsFeature;
import io.dropwizard.metrics.Meter;
import io.dropwizard.metrics.MetricRegistry;
import io.dropwizard.metrics.Timer;

import javax.ws.rs.NotFoundException;
import javax.ws.rs.ProcessingException;
import javax.ws.rs.core.Application;
import javax.ws.rs.core.Response;

import java.io.IOException;
import java.util.logging.Level;
import java.util.logging.Logger;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.failBecauseExceptionWasNotThrown;

/**
 * Tests registering {@link InstrumentedResourceMethodApplicationListener} as a singleton
 * in a Jersey {@link org.glassfish.jersey.server.ResourceConfig}
 */

public class SingletonMetricsJerseyTest extends JerseyTest {
    static {
        Logger.getLogger("org.glassfish.jersey").setLevel(Level.OFF);
    }

    private MetricRegistry registry;

    @Override
    protected Application configure() {
        this.registry = new MetricRegistry();

        ResourceConfig config = new ResourceConfig();
        config = config.register(new MetricsFeature(this.registry));
        config = config.register(InstrumentedResource.class);

        return config;
    }

    @Test
    public void timedMethodsAreTimed() {
        assertThat(target("timed")
                .request()
                .get(String.class))
                .isEqualTo("yay");

        final Timer timer = registry.timer(name(InstrumentedResource.class, "timed"));

        assertThat(timer.getCount()).isEqualTo(1);
    }

    @Test
    public void meteredMethodsAreMetered() {
        assertThat(target("metered")
                .request()
                .get(String.class))
                .isEqualTo("woo");

        final Meter meter = registry.meter(name(InstrumentedResource.class, "metered"));
        assertThat(meter.getCount()).isEqualTo(1);
    }

    @Test
    public void exceptionMeteredMethodsAreExceptionMetered() {
        final Meter meter = registry.meter(name(InstrumentedResource.class,
                "exceptionMetered",
                "exceptions"));

        assertThat(target("exception-metered")
                .request()
                .get(String.class))
                .isEqualTo("fuh");

        assertThat(meter.getCount()).isZero();

        try {
            target("exception-metered")
                    .queryParam("splode", true)
                    .request()
                    .get(String.class);

            failBecauseExceptionWasNotThrown(ProcessingException.class);
        } catch (ProcessingException e) {
            assertThat(e.getCause()).isInstanceOf(IOException.class);
        }

        assertThat(meter.getCount()).isEqualTo(1);
    }

    @Test
    public void testResourceNotFound() {
        final Response response = target().path("not-found").request().get();
        assertThat(response.getStatus()).isEqualTo(404);

        try {
            target().path("not-found").request().get(ClientResponse.class);
            failBecauseExceptionWasNotThrown(NotFoundException.class);
        } catch (NotFoundException e) {
            assertThat(e.getMessage()).isEqualTo("HTTP 404 Not Found");
        }
    }
}

File: metrics-jersey2/src/test/java/io/dropwizard/metrics/jersey2/resources/InstrumentedResource.java
package io.dropwizard.metrics.jersey2.resources;

import io.dropwizard.metrics.annotation.ExceptionMetered;
import io.dropwizard.metrics.annotation.Metered;
import io.dropwizard.metrics.annotation.Timed;

import javax.ws.rs.*;
import javax.ws.rs.core.MediaType;

import java.io.IOException;

@Path("/")
@Produces(MediaType.TEXT_PLAIN)
public class InstrumentedResource {
    @GET
    @Timed
    @Path("/timed")
    public String timed() {
        return "yay";
    }

    @GET
    @Metered
    @Path("/metered")
    public String metered() {
        return "woo";
    }

    @GET
    @ExceptionMetered(cause = IOException.class)
    @Path("/exception-metered")
    public String exceptionMetered(@QueryParam("splode") @DefaultValue("false") boolean splode) throws IOException {
        if (splode) {
            throw new IOException("AUGH");
        }
        return "fuh";
    }
}
