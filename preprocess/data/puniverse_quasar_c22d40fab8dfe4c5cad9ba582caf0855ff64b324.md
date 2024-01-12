Refactoring Types: ['Extract Method']
in/java/co/paralleluniverse/strands/channels/reactivestreams/ChannelPublisher.java
/*
 * Quasar: lightweight threads and actors for the JVM.
 * Copyright (c) 2013-2015, Parallel Universe Software Co. All rights reserved.
 * 
 * This program and the accompanying materials are dual-licensed under
 * either the terms of the Eclipse Public License v1.0 as published by
 * the Eclipse Foundation
 *  
 *   or (per the licensee's choosing)
 *  
 * under the terms of the GNU Lesser General Public License version 3.0
 * as published by the Free Software Foundation.
 */
package co.paralleluniverse.strands.channels.reactivestreams;

import co.paralleluniverse.fibers.Fiber;
import co.paralleluniverse.fibers.FiberFactory;
import co.paralleluniverse.strands.SuspendableCallable;
import co.paralleluniverse.strands.channels.ReceivePort;
import java.util.concurrent.atomic.AtomicBoolean;
import org.reactivestreams.Publisher;
import org.reactivestreams.Subscriber;

/**
 *
 * @author pron
 */
class ChannelPublisher<T> implements Publisher<T> {
    private final FiberFactory ff;
    private final Object channel;
    private final AtomicBoolean subscribed;

    public ChannelPublisher(FiberFactory ff, Object channel, boolean singleSubscriber) {
        this.ff = ff != null ? ff : defaultFiberFactory;
        this.channel = channel;

        subscribed = singleSubscriber ? new AtomicBoolean() : null;
    }

    @Override
    public void subscribe(Subscriber<? super T> s) {
        if (s == null)
            throw new NullPointerException(); // #1.9
        try {
            if (subscribed != null && !subscribed.compareAndSet(false, true))
                s.onError(new RuntimeException("already subscribed"));
            else
                ff.newFiber(newChannelSubscription(s, channel)).start();
        } catch (Exception e) {
            s.onError(e);
        }
    }

    protected ChannelSubscription<T> newChannelSubscription(Subscriber<? super T> s, Object channel) {
        return new ChannelSubscription<>(s, (ReceivePort<T>)channel);
    }

    private static final FiberFactory defaultFiberFactory = new FiberFactory() {
        @Override
        public <T> Fiber<T> newFiber(SuspendableCallable<T> target) {
            return new Fiber(target);
        }
    };
}


File: quasar-reactive-streams/src/main/java/co/paralleluniverse/strands/channels/reactivestreams/ChannelSubscriber.java
/*
 * Quasar: lightweight threads and actors for the JVM.
 * Copyright (c) 2013-2015, Parallel Universe Software Co. All rights reserved.
 * 
 * This program and the accompanying materials are dual-licensed under
 * either the terms of the Eclipse Public License v1.0 as published by
 * the Eclipse Foundation
 *  
 *   or (per the licensee's choosing)
 *  
 * under the terms of the GNU Lesser General Public License version 3.0
 * as published by the Free Software Foundation.
 */
package co.paralleluniverse.strands.channels.reactivestreams;

import co.paralleluniverse.fibers.SuspendExecution;
import co.paralleluniverse.fibers.Suspendable;
import co.paralleluniverse.strands.Strand;
import co.paralleluniverse.strands.Timeout;
import co.paralleluniverse.strands.channels.Channel;
import co.paralleluniverse.strands.channels.Channels.OverflowPolicy;
import co.paralleluniverse.strands.channels.QueueChannel;
import co.paralleluniverse.strands.channels.ReceivePort;
import java.util.concurrent.TimeUnit;
import org.reactivestreams.Subscriber;
import org.reactivestreams.Subscription;

/**
 *
 * @author pron
 */
class ChannelSubscriber<T> implements Subscriber<T>, ReceivePort<T> {
    private final QueueChannel<T> ch;
    private final long capacity;
    private Subscription subscription;
    private long consumed;
    private final boolean batch;

    public ChannelSubscriber(Channel<T> channel, boolean batch) {
        if (!(channel instanceof QueueChannel))
            throw new IllegalArgumentException("Channel of type " + channel.getClass().getName() + " is not supported.");
        if (!((QueueChannel<T>) channel).isSingleConsumer())
            throw new IllegalArgumentException("Provided channel must be single-consumer."); // #2.7
        this.ch = (QueueChannel<T>) channel;
        this.capacity = (ch.capacity() < 0 || ch.getOverflowPolicy() == OverflowPolicy.DISPLACE) ? Long.MAX_VALUE : ch.capacity();
        this.batch = (capacity > 1 && capacity < Long.MAX_VALUE) ? batch : false;
    }

    @Override
    public void onSubscribe(Subscription s) {
        if (s == null)
            throw new NullPointerException(); // #2.13
        if (subscription != null)             // #2.5 TODO: concurrency?
            s.cancel();
        else {
            this.subscription = s;
            subscription.request(capacity);
        }
    }

    @Override
    @Suspendable
    public void onNext(T element) {
        if (element == null)
            throw new NullPointerException(); // #2.13
        try {
            if (ch.isClosed())
                subscription.cancel();
            else
                ch.send(element);
        } catch (InterruptedException e) {
            Strand.interrupted();
        } catch (SuspendExecution e) {
            throw new AssertionError(e);
        }
    }

    @Override
    public void onError(Throwable cause) {
        if (cause == null)
            throw new NullPointerException(); // #2.13
        ch.close(cause);
    }

    @Override
    public void onComplete() {
        ch.close();
    }

    private void consumed() {
        if (capacity == Long.MAX_VALUE)
            return;

        if (!batch)
            subscription.request(1);
        else {
            if (++consumed >= capacity) {
                consumed = 0;
                subscription.request(capacity);
            }
        }
    }

    @Override
    public void close() {
        subscription.cancel();
        ch.close();
    }

    @Override
    public T receive() throws SuspendExecution, InterruptedException {
        T m = ch.receive();
        consumed();
        return m;
    }

    @Override
    public T receive(long timeout, TimeUnit unit) throws SuspendExecution, InterruptedException {
        T m = ch.receive(timeout, unit);
        if (m != null)
            consumed();
        return m;
    }

    @Override
    public T receive(Timeout timeout) throws SuspendExecution, InterruptedException {
        T m = ch.receive(timeout);
        if (m != null)
            consumed();
        return m;
    }

    @Override
    public T tryReceive() {
        T m = ch.tryReceive();
        if (m != null)
            consumed();
        return m;
    }

    @Override
    public boolean isClosed() {
        return ch.isClosed();
    }
}


File: quasar-reactive-streams/src/main/java/co/paralleluniverse/strands/channels/reactivestreams/ReactiveStreams.java
/*
 * Quasar: lightweight threads and actors for the JVM.
 * Copyright (c) 2013-2015, Parallel Universe Software Co. All rights reserved.
 * 
 * This program and the accompanying materials are dual-licensed under
 * either the terms of the Eclipse Public License v1.0 as published by
 * the Eclipse Foundation
 *  
 *   or (per the licensee's choosing)
 *  
 * under the terms of the GNU Lesser General Public License version 3.0
 * as published by the Free Software Foundation.
 */
package co.paralleluniverse.strands.channels.reactivestreams;

import co.paralleluniverse.fibers.FiberFactory;
import co.paralleluniverse.strands.channels.Channel;
import co.paralleluniverse.strands.channels.Channels;
import co.paralleluniverse.strands.channels.Channels.OverflowPolicy;
import co.paralleluniverse.strands.channels.ReceivePort;
import co.paralleluniverse.strands.channels.Topic;
import org.reactivestreams.Publisher;
import org.reactivestreams.Subscriber;

/**
 * Converts between Quasar channels and reactive streams
 * @author pron
 */
public class ReactiveStreams {
    /**
     * Subscribes to a given {@link Publisher} and return a {@link ReceivePort} to the subscription.
     * This creates an internal <b>single consumer</b> channel that will receive the published elements.
     * 
     * @param bufferSize the size of the buffer of the internal channel; may be {@code -1} for unbounded, but may not be {@code 0})
     * @param policy     the {@link OverflowPolicy} of the internal channel.
     * @param batch      if the channel has a bounded buffer, whether to request further elements from the publisher in batches
     *                   whenever the channel's buffer is depleted, or after consuming each element.
     * @param publisher  the subscriber
     * @return A {@link ReceivePort} which emits the elements published by the subscriber
     */
    public static <T> ReceivePort<T> subscribe(int bufferSize, OverflowPolicy policy, boolean batch, Publisher<T> publisher) {
        final Channel<T> channel = Channels.newChannel(bufferSize, policy, true, true);
        final ChannelSubscriber<T> sub = new ChannelSubscriber<>(channel, batch);
        publisher.subscribe(sub);
        return sub;
    }

    /**
     * Turns a {@link ReceivePort channel} to a {@link Publisher}. All items sent to the channel will be published by
     * the publisher.
     * <p>
     * The publisher will allow a single subscription, unless the channel is a {@link Channels#isTickerChannel(ReceivePort) ticker channel}
     * in which case, multiple subscribers will be allowed, and a new {@link Channels#newTickerConsumerFor(Channel) ticker consumer}
     * will be created for each.
     * <p>
     * Every subscription to the returned publisher creates an internal fiber, that will receive items from the
     * channel and publish them.
     *
     * @param channel the channel
     * @param ff      the {@link FiberFactory} to create the internal fiber(s); if {@code null} then a default factory is used.
     * @return a new publisher for the channel's items
     */
    public static <T> Publisher<T> toPublisher(ReceivePort<T> channel, FiberFactory ff) {
        if (Channels.isTickerChannel(channel)) {
            return new ChannelPublisher<T>(ff, channel, false) {
                @Override
                protected ChannelSubscription<T> newChannelSubscription(Subscriber<? super T> s, Object channel) {
                    return super.newChannelSubscription(s, Channels.newTickerConsumerFor((Channel<T>) channel));
                }
            };
        } else
            return new ChannelPublisher<T>(ff, channel, true);
    }

    /**
     * Turns a {@link ReceivePort channel} to a {@link Publisher}. All items sent to the channel will be published by
     * the publisher.
     * <p>
     * The publisher will allow a single subscription, unless the channel is a {@link Channels#isTickerChannel(ReceivePort) ticker channel}
     * in which case, multiple subscribers will be allowed, and a new {@link Channels#newTickerConsumerFor(Channel) ticker consumer}
     * will be created for each.
     * <p>
     * Every subscription to the returned publisher creates an internal fiber, that will receive items from the
     * channel and publish them.
     * <p>
     * Calling this method is the same as calling {@link #toPublisher(ReceivePort, FiberFactory) toPublisher(channel, null)
     *
     * @param channel the channel
     * @return a new publisher for the channel's items
     */
    public static <T> Publisher<T> toPublisher(ReceivePort<T> channel) {
        return toPublisher(channel, null);
    }

    /**
     * Turns a {@link Topic topic} to a {@link Publisher}. All items sent to the topic will be published by
     * the publisher.
     * <p>
     * A new <i>transfer channel</i> (i.e. a blocking channel with a buffer of size 0) subscribed to the topic will be created for every subscriber.
     * <p>
     * Every subscription to the returned publisher creates an internal fiber, that will receive items from the
     * subscription's channel and publish them.
     *
     * @param topic the topic
     * @param ff    the {@link FiberFactory} to create the internal fiber(s); if {@code null} then a default factory is used.
     * @return a new publisher for the topic's items
     */
    public static <T> Publisher<T> toPublisher(Topic<T> topic, final FiberFactory ff) {
        return new ChannelPublisher<T>(ff, topic, false) {
            @Override
            protected ChannelSubscription<T> newChannelSubscription(Subscriber<? super T> s, Object channel) {
                final Topic<T> topic = (Topic<T>) channel;
                final Channel<T> ch = Channels.newChannel(0);
                try {
                    topic.subscribe(ch);
                    return new ChannelSubscription<T>(s, ch) {
                        @Override
                        public void cancel() {
                            super.cancel();
                            topic.unsubscribe(ch);
                        }
                    };
                } catch (Exception e) {
                    topic.unsubscribe(ch);
                    throw e;
                }
            }
        };
    }

    /**
     * Turns a {@link Topic topic} to a {@link Publisher}. All items sent to the topic will be published by
     * the publisher.
     * <p>
     * A new <i>transfer channel</i> (i.e. a blocking channel with a buffer of size 0) subscribed to the topic will be created for every subscriber.
     * <p>
     * Every subscription to the returned publisher creates an internal fiber, that will receive items from the
     * subscription's channel and publish them.
     * <p>
     * Calling this method is the same as calling {@link #toPublisher(ReceivePort, FiberFactory) toPublisher(channel, null)
     *
     * @param topic the topic
     * @return a new publisher for the topic's items
     */
    public static <T> Publisher<T> toPublisher(Topic<T> topic) {
        return toPublisher(topic, null);
    }
}


File: quasar-reactive-streams/src/test/java/co/paralleluniverse/strands/channels/reactivestreams/TestHelper.java
/*
 * Copyright (c) 2013-2015, Parallel Universe Software Co. All rights reserved.
 * 
 * This program and the accompanying materials are dual-licensed under
 * either the terms of the Eclipse Public License v1.0 as published by
 * the Eclipse Foundation
 *  
 *   or (per the licensee's choosing)
 *  
 * under the terms of the GNU Lesser General Public License version 3.0
 * as published by the Free Software Foundation.
 */
package co.paralleluniverse.strands.channels.reactivestreams;

import co.paralleluniverse.fibers.Fiber;
import co.paralleluniverse.fibers.SuspendExecution;
import co.paralleluniverse.strands.Strand;
import co.paralleluniverse.strands.SuspendableRunnable;
import co.paralleluniverse.strands.channels.SendPort;

public class TestHelper {
    public static <T extends SendPort<Integer>> T startPublisherFiber(final T s, final long delay, final long elements) {
        new Fiber<Void>(new SuspendableRunnable() {
            @Override
            public void run() throws SuspendExecution, InterruptedException {
                if (delay > 0)
                    Strand.sleep(delay);

                // we only emit up to 100K elements or 100ms, the later of the two (the TCK asks for 2^31-1)
                long start = elements > 100_000 ? System.nanoTime() : 0L;
                for (long i = 0; i < elements; i++) {
                    s.send((int) (i % 10000));

                    if (start > 0) {
                        long elapsed = (System.nanoTime() - start) / 1_000_000;
                        if (elapsed > 100)
                            break;
                    }
                }
                s.close();
            }
        }).start();
        return s;
    }

    public static <T extends SendPort<Integer>> T startFailedPublisherFiber(final T s, final long delay) {
        new Fiber<Void>(new SuspendableRunnable() {
            @Override
            public void run() throws SuspendExecution, InterruptedException {
                if (delay > 0)
                    Strand.sleep(delay);
                s.close(new Exception("failure"));
            }
        }).start();
        return s;
    }
}
