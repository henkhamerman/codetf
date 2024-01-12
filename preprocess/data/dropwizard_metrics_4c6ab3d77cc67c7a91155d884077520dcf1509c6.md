Refactoring Types: ['Extract Method']
/com/codahale/metrics/graphite/GraphiteReporter.java
package com.codahale.metrics.graphite;

import com.codahale.metrics.*;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.io.IOException;
import java.util.Locale;
import java.util.Map;
import java.util.SortedMap;
import java.util.concurrent.TimeUnit;

/**
 * A reporter which publishes metric values to a Graphite server.
 *
 * @see <a href="http://graphite.wikidot.com/">Graphite - Scalable Realtime Graphing</a>
 */
public class GraphiteReporter extends ScheduledReporter {
    /**
     * Returns a new {@link Builder} for {@link GraphiteReporter}.
     *
     * @param registry the registry to report
     * @return a {@link Builder} instance for a {@link GraphiteReporter}
     */
    public static Builder forRegistry(MetricRegistry registry) {
        return new Builder(registry);
    }

    /**
     * A builder for {@link GraphiteReporter} instances. Defaults to not using a prefix, using the
     * default clock, converting rates to events/second, converting durations to milliseconds, and
     * not filtering metrics.
     */
    public static class Builder {
        private final MetricRegistry registry;
        private Clock clock;
        private String prefix;
        private TimeUnit rateUnit;
        private TimeUnit durationUnit;
        private MetricFilter filter;

        private Builder(MetricRegistry registry) {
            this.registry = registry;
            this.clock = Clock.defaultClock();
            this.prefix = null;
            this.rateUnit = TimeUnit.SECONDS;
            this.durationUnit = TimeUnit.MILLISECONDS;
            this.filter = MetricFilter.ALL;
        }

        /**
         * Use the given {@link Clock} instance for the time.
         *
         * @param clock a {@link Clock} instance
         * @return {@code this}
         */
        public Builder withClock(Clock clock) {
            this.clock = clock;
            return this;
        }

        /**
         * Prefix all metric names with the given string.
         *
         * @param prefix the prefix for all metric names
         * @return {@code this}
         */
        public Builder prefixedWith(String prefix) {
            this.prefix = prefix;
            return this;
        }

        /**
         * Convert rates to the given time unit.
         *
         * @param rateUnit a unit of time
         * @return {@code this}
         */
        public Builder convertRatesTo(TimeUnit rateUnit) {
            this.rateUnit = rateUnit;
            return this;
        }

        /**
         * Convert durations to the given time unit.
         *
         * @param durationUnit a unit of time
         * @return {@code this}
         */
        public Builder convertDurationsTo(TimeUnit durationUnit) {
            this.durationUnit = durationUnit;
            return this;
        }

        /**
         * Only report metrics which match the given filter.
         *
         * @param filter a {@link MetricFilter}
         * @return {@code this}
         */
        public Builder filter(MetricFilter filter) {
            this.filter = filter;
            return this;
        }

        /**
         * Builds a {@link GraphiteReporter} with the given properties, sending metrics using the
         * given {@link GraphiteSender}.
         *
         * @param graphite a {@link GraphiteSender}
         * @return a {@link GraphiteReporter}
         */
        public GraphiteReporter build(GraphiteSender graphite) {
            return new GraphiteReporter(registry,
                                        graphite,
                                        clock,
                                        prefix,
                                        rateUnit,
                                        durationUnit,
                                        filter);
        }
    }

    private static final Logger LOGGER = LoggerFactory.getLogger(GraphiteReporter.class);

    private final GraphiteSender graphite;
    private final Clock clock;
    private final String prefix;

    private GraphiteReporter(MetricRegistry registry,
                             GraphiteSender graphite,
                             Clock clock,
                             String prefix,
                             TimeUnit rateUnit,
                             TimeUnit durationUnit,
                             MetricFilter filter) {
        super(registry, "graphite-reporter", filter, rateUnit, durationUnit);
        this.graphite = graphite;
        this.clock = clock;
        this.prefix = prefix;
    }

    @Override
    public void report(SortedMap<String, Gauge> gauges,
                       SortedMap<String, Counter> counters,
                       SortedMap<String, Histogram> histograms,
                       SortedMap<String, Meter> meters,
                       SortedMap<String, Timer> timers) {
        final long timestamp = clock.getTime() / 1000;

        // oh it'd be lovely to use Java 7 here
        try {
            if (!graphite.isConnected()) {
    	          graphite.connect();
            }

            for (Map.Entry<String, Gauge> entry : gauges.entrySet()) {
                reportGauge(entry.getKey(), entry.getValue(), timestamp);
            }

            for (Map.Entry<String, Counter> entry : counters.entrySet()) {
                reportCounter(entry.getKey(), entry.getValue(), timestamp);
            }

            for (Map.Entry<String, Histogram> entry : histograms.entrySet()) {
                reportHistogram(entry.getKey(), entry.getValue(), timestamp);
            }

            for (Map.Entry<String, Meter> entry : meters.entrySet()) {
                reportMetered(entry.getKey(), entry.getValue(), timestamp);
            }

            for (Map.Entry<String, Timer> entry : timers.entrySet()) {
                reportTimer(entry.getKey(), entry.getValue(), timestamp);
            }

            graphite.flush();
        } catch (IOException e) {
            LOGGER.warn("Unable to report to Graphite", graphite, e);
            try {
                graphite.close();
            } catch (IOException e1) {
                LOGGER.warn("Error closing Graphite", graphite, e1);
            }
        }
    }

    @Override
    public void stop() {
        try {
            super.stop();
        } finally {
            try {
                graphite.close();
            } catch (IOException e) {
                LOGGER.debug("Error disconnecting from Graphite", graphite, e);
            }
        }
    }

    private void reportTimer(String name, Timer timer, long timestamp) throws IOException {
        final Snapshot snapshot = timer.getSnapshot();

        graphite.send(prefix(name, "max"), format(convertDuration(snapshot.getMax())), timestamp);
        graphite.send(prefix(name, "mean"), format(convertDuration(snapshot.getMean())), timestamp);
        graphite.send(prefix(name, "min"), format(convertDuration(snapshot.getMin())), timestamp);
        graphite.send(prefix(name, "stddev"),
                      format(convertDuration(snapshot.getStdDev())),
                      timestamp);
        graphite.send(prefix(name, "p50"),
                      format(convertDuration(snapshot.getMedian())),
                      timestamp);
        graphite.send(prefix(name, "p75"),
                      format(convertDuration(snapshot.get75thPercentile())),
                      timestamp);
        graphite.send(prefix(name, "p95"),
                      format(convertDuration(snapshot.get95thPercentile())),
                      timestamp);
        graphite.send(prefix(name, "p98"),
                      format(convertDuration(snapshot.get98thPercentile())),
                      timestamp);
        graphite.send(prefix(name, "p99"),
                      format(convertDuration(snapshot.get99thPercentile())),
                      timestamp);
        graphite.send(prefix(name, "p999"),
                      format(convertDuration(snapshot.get999thPercentile())),
                      timestamp);

        reportMetered(name, timer, timestamp);
    }

    private void reportMetered(String name, Metered meter, long timestamp) throws IOException {
        graphite.send(prefix(name, "count"), format(meter.getCount()), timestamp);
        graphite.send(prefix(name, "m1_rate"),
                      format(convertRate(meter.getOneMinuteRate())),
                      timestamp);
        graphite.send(prefix(name, "m5_rate"),
                      format(convertRate(meter.getFiveMinuteRate())),
                      timestamp);
        graphite.send(prefix(name, "m15_rate"),
                      format(convertRate(meter.getFifteenMinuteRate())),
                      timestamp);
        graphite.send(prefix(name, "mean_rate"),
                      format(convertRate(meter.getMeanRate())),
                      timestamp);
    }

    private void reportHistogram(String name, Histogram histogram, long timestamp) throws IOException {
        final Snapshot snapshot = histogram.getSnapshot();
        graphite.send(prefix(name, "count"), format(histogram.getCount()), timestamp);
        graphite.send(prefix(name, "max"), format(snapshot.getMax()), timestamp);
        graphite.send(prefix(name, "mean"), format(snapshot.getMean()), timestamp);
        graphite.send(prefix(name, "min"), format(snapshot.getMin()), timestamp);
        graphite.send(prefix(name, "stddev"), format(snapshot.getStdDev()), timestamp);
        graphite.send(prefix(name, "p50"), format(snapshot.getMedian()), timestamp);
        graphite.send(prefix(name, "p75"), format(snapshot.get75thPercentile()), timestamp);
        graphite.send(prefix(name, "p95"), format(snapshot.get95thPercentile()), timestamp);
        graphite.send(prefix(name, "p98"), format(snapshot.get98thPercentile()), timestamp);
        graphite.send(prefix(name, "p99"), format(snapshot.get99thPercentile()), timestamp);
        graphite.send(prefix(name, "p999"), format(snapshot.get999thPercentile()), timestamp);
    }

    private void reportCounter(String name, Counter counter, long timestamp) throws IOException {
        graphite.send(prefix(name, "count"), format(counter.getCount()), timestamp);
    }

    private void reportGauge(String name, Gauge gauge, long timestamp) throws IOException {
        final String value = format(gauge.getValue());
        if (value != null) {
            graphite.send(prefix(name), value, timestamp);
        }
    }

    private String format(Object o) {
        if (o instanceof Float) {
            return format(((Float) o).doubleValue());
        } else if (o instanceof Double) {
            return format(((Double) o).doubleValue());
        } else if (o instanceof Byte) {
            return format(((Byte) o).longValue());
        } else if (o instanceof Short) {
            return format(((Short) o).longValue());
        } else if (o instanceof Integer) {
            return format(((Integer) o).longValue());
        } else if (o instanceof Long) {
            return format(((Long) o).longValue());
        }
        return null;
    }

    private String prefix(String... components) {
        return MetricRegistry.name(prefix, components);
    }

    private String format(long n) {
        return Long.toString(n);
    }

    private String format(double v) {
        // the Carbon plaintext format is pretty underspecified, but it seems like it just wants
        // US-formatted digits
        return String.format(Locale.US, "%2.2f", v);
    }
}


File: metrics-graphite/src/test/java/com/codahale/metrics/graphite/GraphiteReporterTest.java
package com.codahale.metrics.graphite;

import com.codahale.metrics.*;
import org.junit.Before;
import org.junit.Test;
import org.mockito.InOrder;

import java.net.UnknownHostException;
import java.util.SortedMap;
import java.util.TreeMap;
import java.util.concurrent.TimeUnit;

import static org.mockito.Mockito.*;

public class GraphiteReporterTest {
    private final long timestamp = 1000198;
    private final Clock clock = mock(Clock.class);
    private final Graphite graphite = mock(Graphite.class);
    private final MetricRegistry registry = mock(MetricRegistry.class);
    private final GraphiteReporter reporter = GraphiteReporter.forRegistry(registry)
                                                              .withClock(clock)
                                                              .prefixedWith("prefix")
                                                              .convertRatesTo(TimeUnit.SECONDS)
                                                              .convertDurationsTo(TimeUnit.MILLISECONDS)
                                                              .filter(MetricFilter.ALL)
                                                              .build(graphite);

    @Before
    public void setUp() throws Exception {
        when(clock.getTime()).thenReturn(timestamp * 1000);
    }

    @Test
    public void doesNotReportStringGaugeValues() throws Exception {
        reporter.report(map("gauge", gauge("value")),
                        this.<Counter>map(),
                        this.<Histogram>map(),
                        this.<Meter>map(),
                        this.<Timer>map());

        final InOrder inOrder = inOrder(graphite);
        inOrder.verify(graphite).isConnected();
        inOrder.verify(graphite).connect();
        inOrder.verify(graphite, never()).send("prefix.gauge", "value", timestamp);
        inOrder.verify(graphite).flush();

        verifyNoMoreInteractions(graphite);
    }

    @Test
    public void reportsByteGaugeValues() throws Exception {
        reporter.report(map("gauge", gauge((byte) 1)),
                        this.<Counter>map(),
                        this.<Histogram>map(),
                        this.<Meter>map(),
                        this.<Timer>map());

        final InOrder inOrder = inOrder(graphite);
        inOrder.verify(graphite).isConnected();
        inOrder.verify(graphite).connect();
        inOrder.verify(graphite).send("prefix.gauge", "1", timestamp);
        inOrder.verify(graphite).flush();

        verifyNoMoreInteractions(graphite);
    }

    @Test
    public void reportsShortGaugeValues() throws Exception {
        reporter.report(map("gauge", gauge((short) 1)),
                        this.<Counter>map(),
                        this.<Histogram>map(),
                        this.<Meter>map(),
                        this.<Timer>map());

        final InOrder inOrder = inOrder(graphite);
        inOrder.verify(graphite).isConnected();
        inOrder.verify(graphite).connect();
        inOrder.verify(graphite).send("prefix.gauge", "1", timestamp);
        inOrder.verify(graphite).flush();

        verifyNoMoreInteractions(graphite);
    }

    @Test
    public void reportsIntegerGaugeValues() throws Exception {
        reporter.report(map("gauge", gauge(1)),
                        this.<Counter>map(),
                        this.<Histogram>map(),
                        this.<Meter>map(),
                        this.<Timer>map());

        final InOrder inOrder = inOrder(graphite);
        inOrder.verify(graphite).isConnected();
        inOrder.verify(graphite).connect();
        inOrder.verify(graphite).send("prefix.gauge", "1", timestamp);
        inOrder.verify(graphite).flush();

        verifyNoMoreInteractions(graphite);
    }

    @Test
    public void reportsLongGaugeValues() throws Exception {
        reporter.report(map("gauge", gauge(1L)),
                        this.<Counter>map(),
                        this.<Histogram>map(),
                        this.<Meter>map(),
                        this.<Timer>map());

        final InOrder inOrder = inOrder(graphite);
        inOrder.verify(graphite).isConnected();
        inOrder.verify(graphite).connect();
        inOrder.verify(graphite).send("prefix.gauge", "1", timestamp);
        inOrder.verify(graphite).flush();

        verifyNoMoreInteractions(graphite);
    }

    @Test
    public void reportsFloatGaugeValues() throws Exception {
        reporter.report(map("gauge", gauge(1.1f)),
                        this.<Counter>map(),
                        this.<Histogram>map(),
                        this.<Meter>map(),
                        this.<Timer>map());

        final InOrder inOrder = inOrder(graphite);
        inOrder.verify(graphite).isConnected();
        inOrder.verify(graphite).connect();
        inOrder.verify(graphite).send("prefix.gauge", "1.10", timestamp);
        inOrder.verify(graphite).flush();

        verifyNoMoreInteractions(graphite);
    }

    @Test
    public void reportsDoubleGaugeValues() throws Exception {
        reporter.report(map("gauge", gauge(1.1)),
                        this.<Counter>map(),
                        this.<Histogram>map(),
                        this.<Meter>map(),
                        this.<Timer>map());

        final InOrder inOrder = inOrder(graphite);
        inOrder.verify(graphite).isConnected();
        inOrder.verify(graphite).connect();
        inOrder.verify(graphite).send("prefix.gauge", "1.10", timestamp);
        inOrder.verify(graphite).flush();

        verifyNoMoreInteractions(graphite);
    }

    @Test
    public void reportsCounters() throws Exception {
        final Counter counter = mock(Counter.class);
        when(counter.getCount()).thenReturn(100L);

        reporter.report(this.<Gauge>map(),
                        this.<Counter>map("counter", counter),
                        this.<Histogram>map(),
                        this.<Meter>map(),
                        this.<Timer>map());

        final InOrder inOrder = inOrder(graphite);
        inOrder.verify(graphite).isConnected();
        inOrder.verify(graphite).connect();
        inOrder.verify(graphite).send("prefix.counter.count", "100", timestamp);
        inOrder.verify(graphite).flush();

        verifyNoMoreInteractions(graphite);
    }

    @Test
    public void reportsHistograms() throws Exception {
        final Histogram histogram = mock(Histogram.class);
        when(histogram.getCount()).thenReturn(1L);

        final Snapshot snapshot = mock(Snapshot.class);
        when(snapshot.getMax()).thenReturn(2L);
        when(snapshot.getMean()).thenReturn(3.0);
        when(snapshot.getMin()).thenReturn(4L);
        when(snapshot.getStdDev()).thenReturn(5.0);
        when(snapshot.getMedian()).thenReturn(6.0);
        when(snapshot.get75thPercentile()).thenReturn(7.0);
        when(snapshot.get95thPercentile()).thenReturn(8.0);
        when(snapshot.get98thPercentile()).thenReturn(9.0);
        when(snapshot.get99thPercentile()).thenReturn(10.0);
        when(snapshot.get999thPercentile()).thenReturn(11.0);

        when(histogram.getSnapshot()).thenReturn(snapshot);

        reporter.report(this.<Gauge>map(),
                        this.<Counter>map(),
                        this.<Histogram>map("histogram", histogram),
                        this.<Meter>map(),
                        this.<Timer>map());

        final InOrder inOrder = inOrder(graphite);
        inOrder.verify(graphite).isConnected();
        inOrder.verify(graphite).connect();
        inOrder.verify(graphite).send("prefix.histogram.count", "1", timestamp);
        inOrder.verify(graphite).send("prefix.histogram.max", "2", timestamp);
        inOrder.verify(graphite).send("prefix.histogram.mean", "3.00", timestamp);
        inOrder.verify(graphite).send("prefix.histogram.min", "4", timestamp);
        inOrder.verify(graphite).send("prefix.histogram.stddev", "5.00", timestamp);
        inOrder.verify(graphite).send("prefix.histogram.p50", "6.00", timestamp);
        inOrder.verify(graphite).send("prefix.histogram.p75", "7.00", timestamp);
        inOrder.verify(graphite).send("prefix.histogram.p95", "8.00", timestamp);
        inOrder.verify(graphite).send("prefix.histogram.p98", "9.00", timestamp);
        inOrder.verify(graphite).send("prefix.histogram.p99", "10.00", timestamp);
        inOrder.verify(graphite).send("prefix.histogram.p999", "11.00", timestamp);
        inOrder.verify(graphite).flush();

        verifyNoMoreInteractions(graphite);
    }

    @Test
    public void reportsMeters() throws Exception {
        final Meter meter = mock(Meter.class);
        when(meter.getCount()).thenReturn(1L);
        when(meter.getOneMinuteRate()).thenReturn(2.0);
        when(meter.getFiveMinuteRate()).thenReturn(3.0);
        when(meter.getFifteenMinuteRate()).thenReturn(4.0);
        when(meter.getMeanRate()).thenReturn(5.0);

        reporter.report(this.<Gauge>map(),
                        this.<Counter>map(),
                        this.<Histogram>map(),
                        this.<Meter>map("meter", meter),
                        this.<Timer>map());

        final InOrder inOrder = inOrder(graphite);
        inOrder.verify(graphite).isConnected();
        inOrder.verify(graphite).connect();
        inOrder.verify(graphite).send("prefix.meter.count", "1", timestamp);
        inOrder.verify(graphite).send("prefix.meter.m1_rate", "2.00", timestamp);
        inOrder.verify(graphite).send("prefix.meter.m5_rate", "3.00", timestamp);
        inOrder.verify(graphite).send("prefix.meter.m15_rate", "4.00", timestamp);
        inOrder.verify(graphite).send("prefix.meter.mean_rate", "5.00", timestamp);
        inOrder.verify(graphite).flush();

        verifyNoMoreInteractions(graphite);
    }

    @Test
    public void reportsTimers() throws Exception {
        final Timer timer = mock(Timer.class);
        when(timer.getCount()).thenReturn(1L);
        when(timer.getMeanRate()).thenReturn(2.0);
        when(timer.getOneMinuteRate()).thenReturn(3.0);
        when(timer.getFiveMinuteRate()).thenReturn(4.0);
        when(timer.getFifteenMinuteRate()).thenReturn(5.0);

        final Snapshot snapshot = mock(Snapshot.class);
        when(snapshot.getMax()).thenReturn(TimeUnit.MILLISECONDS.toNanos(100));
        when(snapshot.getMean()).thenReturn((double) TimeUnit.MILLISECONDS.toNanos(200));
        when(snapshot.getMin()).thenReturn(TimeUnit.MILLISECONDS.toNanos(300));
        when(snapshot.getStdDev()).thenReturn((double) TimeUnit.MILLISECONDS.toNanos(400));
        when(snapshot.getMedian()).thenReturn((double) TimeUnit.MILLISECONDS.toNanos(500));
        when(snapshot.get75thPercentile()).thenReturn((double) TimeUnit.MILLISECONDS.toNanos(600));
        when(snapshot.get95thPercentile()).thenReturn((double) TimeUnit.MILLISECONDS.toNanos(700));
        when(snapshot.get98thPercentile()).thenReturn((double) TimeUnit.MILLISECONDS.toNanos(800));
        when(snapshot.get99thPercentile()).thenReturn((double) TimeUnit.MILLISECONDS.toNanos(900));
        when(snapshot.get999thPercentile()).thenReturn((double) TimeUnit.MILLISECONDS
                                                                        .toNanos(1000));

        when(timer.getSnapshot()).thenReturn(snapshot);

        reporter.report(this.<Gauge>map(),
                        this.<Counter>map(),
                        this.<Histogram>map(),
                        this.<Meter>map(),
                        map("timer", timer));

        final InOrder inOrder = inOrder(graphite);
        inOrder.verify(graphite).isConnected();
        inOrder.verify(graphite).connect();
        inOrder.verify(graphite).send("prefix.timer.max", "100.00", timestamp);
        inOrder.verify(graphite).send("prefix.timer.mean", "200.00", timestamp);
        inOrder.verify(graphite).send("prefix.timer.min", "300.00", timestamp);
        inOrder.verify(graphite).send("prefix.timer.stddev", "400.00", timestamp);
        inOrder.verify(graphite).send("prefix.timer.p50", "500.00", timestamp);
        inOrder.verify(graphite).send("prefix.timer.p75", "600.00", timestamp);
        inOrder.verify(graphite).send("prefix.timer.p95", "700.00", timestamp);
        inOrder.verify(graphite).send("prefix.timer.p98", "800.00", timestamp);
        inOrder.verify(graphite).send("prefix.timer.p99", "900.00", timestamp);
        inOrder.verify(graphite).send("prefix.timer.p999", "1000.00", timestamp);
        inOrder.verify(graphite).send("prefix.timer.count", "1", timestamp);
        inOrder.verify(graphite).send("prefix.timer.m1_rate", "3.00", timestamp);
        inOrder.verify(graphite).send("prefix.timer.m5_rate", "4.00", timestamp);
        inOrder.verify(graphite).send("prefix.timer.m15_rate", "5.00", timestamp);
        inOrder.verify(graphite).send("prefix.timer.mean_rate", "2.00", timestamp);
        inOrder.verify(graphite).flush();

        verifyNoMoreInteractions(graphite);
    }

    @Test
    public void closesConnectionIfGraphiteIsUnavailable() throws Exception {
        doThrow(new UnknownHostException("UNKNOWN-HOST")).when(graphite).connect();
        reporter.report(map("gauge", gauge(1)),
            this.<Counter>map(),
            this.<Histogram>map(),
            this.<Meter>map(),
            this.<Timer>map());

        final InOrder inOrder = inOrder(graphite);
        inOrder.verify(graphite).isConnected();
        inOrder.verify(graphite).connect();
        inOrder.verify(graphite).close();

        verifyNoMoreInteractions(graphite);
    }

    @Test
    public void closesConnectionOnReporterStop() throws Exception {
        reporter.stop();

        verify(graphite).close();

        verifyNoMoreInteractions(graphite);
    }

    private <T> SortedMap<String, T> map() {
        return new TreeMap<String, T>();
    }

    private <T> SortedMap<String, T> map(String name, T metric) {
        final TreeMap<String, T> map = new TreeMap<String, T>();
        map.put(name, metric);
        return map;
    }

    private <T> Gauge gauge(T value) {
        final Gauge gauge = mock(Gauge.class);
        when(gauge.getValue()).thenReturn(value);
        return gauge;
    }
}
