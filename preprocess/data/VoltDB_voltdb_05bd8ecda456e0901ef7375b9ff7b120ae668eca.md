Refactoring Types: ['Move Class']
hmark/src/exportbenchmark/ExportBenchmark.java
/* This file is part of VoltDB.
 * Copyright (C) 2008-2015 VoltDB Inc.
 *
 * Permission is hereby granted, free of charge, to any person obtaining
 * a copy of this software and associated documentation files (the
 * "Software"), to deal in the Software without restriction, including
 * without limitation the rights to use, copy, modify, merge, publish,
 * distribute, sublicense, and/or sell copies of the Software, and to
 * permit persons to whom the Software is furnished to do so, subject to
 * the following conditions:
 *
 * The above copyright notice and this permission notice shall be
 * included in all copies or substantial portions of the Software.
 *
 * THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,
 * EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF
 * MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT.
 * IN NO EVENT SHALL THE AUTHORS BE LIABLE FOR ANY CLAIM, DAMAGES OR
 * OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE,
 * ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR
 * OTHER DEALINGS IN THE SOFTWARE.
 */
/*
 * This samples uses multiple threads to post synchronous requests to the
 * VoltDB server, simulating multiple client application posting
 * synchronous requests to the database, using the native VoltDB client
 * library.
 *
 * While synchronous processing can cause performance bottlenecks (each
 * caller waits for a transaction answer before calling another
 * transaction), the VoltDB cluster at large is still able to perform at
 * blazing speeds when many clients are connected to it.
 */

package exportbenchmark;

import java.io.FileWriter;
import java.io.IOException;
import java.lang.Math;
import java.math.BigDecimal;
import java.math.RoundingMode;
import java.net.InetSocketAddress;
import java.nio.BufferUnderflowException;
import java.nio.ByteBuffer;
import java.nio.channels.DatagramChannel;
import java.nio.channels.SelectionKey;
import java.nio.channels.Selector;
import java.nio.channels.spi.SelectorProvider;
import java.text.SimpleDateFormat;
import java.util.ArrayList;
import java.util.Date;
import java.util.HashMap;
import java.util.Timer;
import java.util.TimerTask;
import java.util.concurrent.CountDownLatch;
import java.util.concurrent.atomic.AtomicBoolean;
import java.util.concurrent.atomic.AtomicLong;

import org.json_voltpatches.JSONException;
import org.json_voltpatches.JSONObject;
import org.voltcore.utils.CoreUtils;
import org.voltdb.CLIConfig;
import org.voltdb.VoltTable;
import org.voltdb.VoltType;
import org.voltdb.client.Client;
import org.voltdb.client.ClientConfig;
import org.voltdb.client.ClientFactory;
import org.voltdb.client.ClientResponse;
import org.voltdb.client.ClientStats;
import org.voltdb.client.ClientStatsContext;
import org.voltdb.client.NoConnectionsException;
import org.voltdb.client.NullCallback;
import org.voltdb.client.ProcCallException;
import org.voltdb.client.ProcedureCallback;
import org.voltdb.types.TimestampType;

/**
 * Asychronously sends data to an export table to test VoltDB export performance.
 */
public class ExportBenchmark {

    // handy, rather than typing this out several times
    static final String HORIZONTAL_RULE =
            "----------" + "----------" + "----------" + "----------" +
            "----------" + "----------" + "----------" + "----------" + "\n";

    // Client connection to the server
    final Client client;
    // Validated CLI config
    final ExportBenchConfig config;
    // Network variables
    Selector statsSocketSelector;
    Thread statsThread;
    ByteBuffer buffer = ByteBuffer.allocate(1024);
    // Statistics manager objects from the client
    final ClientStatsContext periodicStatsContext;
    final ClientStatsContext fullStatsContext;
    // Timer for periodic stats
    Timer periodicStatsTimer;
    // Test stats variables
    long totalInserts = 0;
    AtomicLong successfulInserts = new AtomicLong(0);
    AtomicLong failedInserts = new AtomicLong(0);
    AtomicBoolean testFinished = new AtomicBoolean(false);
    // Server-side stats
    ArrayList<StatClass> serverStats = new ArrayList<StatClass>();
    // Test timestamp markers
    long benchmarkStartTS, benchmarkWarmupEndTS, benchmarkEndTS, serverStartTS, serverEndTS, decodeTime, partCount;

    class StatClass {
        public Integer m_partition;
        public Long m_transactions;
        public Long m_decode;
        public Long m_startTime;
        public Long m_endTime;

        StatClass (Integer partition, Long transactions, Long decode, Long startTime, Long endTime) {
            m_partition = partition;
            m_transactions = transactions;
            m_decode = decode;
            m_startTime = startTime;
            m_endTime = endTime;
        }
    }

    static final SimpleDateFormat LOG_DF = new SimpleDateFormat("yyyy-MM-dd HH:mm:ss,SSS");

    /**
     * Uses included {@link CLIConfig} class to
     * declaratively state command line options with defaults
     * and validation.
     */
    static class ExportBenchConfig extends CLIConfig {
        @Option(desc = "Interval for performance feedback, in seconds.")
        long displayinterval = 5;

        @Option(desc = "Benchmark duration, in seconds.")
        int duration = 25;

        @Option(desc = "Warmup duration in seconds.")
        int warmup = 10;

        @Option(desc = "Comma separated list of the form server[:port] to connect to.")
        String servers = "localhost";

        @Option (desc = "Port on which to listen for statistics info from export clients")
        int statsPort = 5001;

        @Option(desc = "Filename to write raw summary statistics to.")
        String statsfile = "";

        @Option(desc = "Filename to write periodic stat infomation in CSV format")
        String csvfile = "";

        @Override
        public void validate() {
            if (duration <= 0) exitWithMessageAndUsage("duration must be > 0");
            if (warmup < 0) exitWithMessageAndUsage("warmup must be >= 0");
            if (displayinterval <= 0) exitWithMessageAndUsage("displayinterval must be > 0");
        }
    }

    /**
     * Callback for export insert method. Tracks successes & failures
     */
    class ExportCallback implements ProcedureCallback {
        @Override
        public void clientCallback(ClientResponse response) {
            if (response.getStatus() == ClientResponse.SUCCESS) {
                successfulInserts.incrementAndGet();
            } else {
                failedInserts.incrementAndGet();
            }
        }
    }

    /**
     * Clean way of exiting from an exception
     * @param message   Message to accompany the exception
     * @param e         The exception thrown
     */
    private void exitWithException(String message, Exception e) {
        System.err.println(message);
        System.err.println(e.getLocalizedMessage());
        System.exit(-1);
    }

    /**
     * Creates a new instance of the test to be run.
     * Establishes a client connection to a voltdb server, which should already be running
     * @param args The arguments passed to the program
     */
    public ExportBenchmark(ExportBenchConfig config) {
        this.config = config;
        ClientConfig clientConfig = new ClientConfig();
        clientConfig.setReconnectOnConnectionLoss(true);
        clientConfig.setClientAffinity(true);
        client = ClientFactory.createClient(clientConfig);

        fullStatsContext = client.createStatsContext();
        periodicStatsContext = client.createStatsContext();

        serverStartTS = serverEndTS = decodeTime = partCount = 0;
    }

    /**
    * Create a Timer task to display performance data.
    * It calls printStatistics() every displayInterval seconds
    */
    public void schedulePeriodicStats() {
        periodicStatsTimer = new Timer();
        TimerTask statsPrinting = new TimerTask() {
            @Override
            public void run() { printStatistics(); }
        };
        periodicStatsTimer.scheduleAtFixedRate(statsPrinting,
                                    config.displayinterval * 1000,
                                    config.displayinterval * 1000);
    }

    /**
     * Checks the export table to make sure that everything has been successfully
     * processed.
     * @throws ProcCallException
     * @throws IOException
     * @throws InterruptedException
     */
    public boolean waitForStreamedAllocatedMemoryZero() throws ProcCallException,IOException,InterruptedException {
        boolean passed = false;

        VoltTable stats = null;
        long ftime = 0;
        long st = System.currentTimeMillis();
        //Wait 10 mins only
        long end = st + (10 * 60 * 1000);
        while (true) {
            stats = client.callProcedure("@Statistics", "table", 0).getResults()[0];
            boolean passedThisTime = true;
            long ctime = System.currentTimeMillis();
            if (ctime > end) {
                System.out.println("Waited too long...");
                System.out.println(stats);
                break;
            }
            if (ctime - st > (3 * 60 * 1000)) {
                System.out.println(stats);
                st = System.currentTimeMillis();
            }
            long ts = 0;
            while (stats.advanceRow()) {
                String ttype = stats.getString("TABLE_TYPE");
                Long tts = stats.getLong("TIMESTAMP");
                //Get highest timestamp and watch is change
                if (tts > ts) {
                    ts = tts;
                }
                if ("StreamedTable".equals(ttype)) {
                    if (0 != stats.getLong("TUPLE_ALLOCATED_MEMORY")) {
                        passedThisTime = false;
                        System.out.println("Partition Not Zero.");
                        break;
                    }
                }
            }
            if (passedThisTime) {
                if (ftime == 0) {
                    ftime = ts;
                    continue;
                }
                //we got 0 stats 2 times in row with diff highest timestamp.
                if (ftime != ts) {
                    passed = true;
                    break;
                }
                System.out.println("Passed but not ready to declare victory.");
            }
            Thread.sleep(5000);
        }
        System.out.println("Passed is: " + passed);
        System.out.println(stats);
        return passed;
    }

    /**
     * Connect to a single server with retry. Limited exponential backoff.
     * No timeout. This will run until the process is killed if it's not
     * able to connect.
     *
     * @param server hostname:port or just hostname (hostname can be ip).
     */
    void connectToOneServerWithRetry(String server) {
        int sleep = 1000;
        while (true) {
            try {
                client.createConnection(server);
                break;
            }
            catch (IOException e) {
                System.err.printf("Connection failed - retrying in %d second(s).\n", sleep / 1000);
                try { Thread.sleep(sleep); } catch (InterruptedException interruted) {}
                if (sleep < 8000) sleep += sleep;
            }
        }
        System.out.printf("Connected to VoltDB node at: %s.\n", server);
    }

    /**
     * Connect to a set of servers in parallel. Each will retry until
     * connection. This call will block until all have connected.
     *
     * @param servers A comma separated list of servers using the hostname:port
     * syntax (where :port is optional).
     * @throws InterruptedException if anything bad happens with the threads.
     */
    void connect(String servers) throws InterruptedException {
        System.out.println("Connecting to VoltDB...");

        String[] serverArray = servers.split(",");
        final CountDownLatch connections = new CountDownLatch(serverArray.length);

        // use a new thread to connect to each server
        for (final String server : serverArray) {
            new Thread(new Runnable() {
                @Override
                public void run() {
                    connectToOneServerWithRetry(server);
                    connections.countDown();
                }
            }).start();
        }
        // block until all have connected
        connections.await();
    }

    /**
     * Inserts values into the export table for the test. First it does warmup
     * inserts, then tracked inserts.
     * @throws InterruptedException
     * @throws NoConnectionsException
     */
    public void doInserts(Client client) {

        // Don't track warmup inserts
        System.out.println("Warming up...");
        long now = System.currentTimeMillis();
        AtomicLong rowId = new AtomicLong(0);
        while (benchmarkWarmupEndTS > now) {
            try {
                client.callProcedure(
                        new NullCallback(),
                        "InsertExport",
                        rowId.getAndIncrement(),
                        0);
                // Check the time every 50 transactions to avoid invoking System.currentTimeMillis() too much
                if (++totalInserts % 50 == 0) {
                    now = System.currentTimeMillis();
                }
            } catch (Exception ignore) {}
        }
        System.out.println("Warmup complete");
        rowId.set(0);

        // reset the stats after warmup is done
        fullStatsContext.fetchAndResetBaseline();
        periodicStatsContext.fetchAndResetBaseline();

        schedulePeriodicStats();

        // Insert objects until we've run for long enough
        System.out.println("Running benchmark...");
        now = System.currentTimeMillis();
        while (benchmarkEndTS > now) {
            try {
                client.callProcedure(
                        new ExportCallback(),
                        "InsertExport",
                        rowId.getAndIncrement(),
                        0);
                // Check the time every 50 transactions to avoid invoking System.currentTimeMillis() too much
                if (++totalInserts % 50 == 0) {
                    now = System.currentTimeMillis();
                }
            } catch (Exception e) {
                System.err.println("Couldn't insert into VoltDB\n");
                e.printStackTrace();
                System.exit(1);
            }
        }

        try {
            client.drain();
        } catch (Exception e) {
            e.printStackTrace();
        }

        System.out.println("Benchmark complete: wrote " + successfulInserts.get() + " objects");
        System.out.println("Failed to insert " + failedInserts.get() + " objects");

        testFinished.set(true);
        statsSocketSelector.wakeup();
    }

    /**
     * Listens on a UDP socket for incoming statistics packets, until the
     * test is finished.
     */
    private void listenForStats() {

        while (true) {
            // Wait for an event...
            try {
                statsSocketSelector.select();
            } catch (IOException e) {
                exitWithException("Can't select a new socket", e);
            }

            // See if we're done
            if (testFinished.get() == true) {
                return;
            }

            // We have events. Process each one.
            for (SelectionKey key : statsSocketSelector.selectedKeys()) {
                if (!key.isValid()) {
                    continue;           // Ignore invalid keys
                }

                if (key.isReadable()) {
                    getStatsMessage((DatagramChannel)key.channel());
                }
            }
        }
    }

    /**
     * Parses a received statistics message & logs the information
     * @param channel   The channel with the incoming packet
     */
    private void getStatsMessage(DatagramChannel channel) {
        String message = null;

        // Read the data
        try {
            buffer.clear();
            channel.receive(buffer);

            buffer.flip();
            int messageLength = buffer.get();

            if (messageLength > buffer.capacity()) {
                System.out.println("WARN: packet exceeds allocate size; message truncated");
            }

            byte[] localBuf = new byte[messageLength];
            buffer.get(localBuf, 0, messageLength);
            message = new String(localBuf);
        } catch (IOException e) {
            exitWithException("Couldn't read from socket", e);
        }

        // Parse the stats message
        JSONObject json;
        try {
            json = new JSONObject(message);
        } catch (JSONException e) {
            System.err.println("Received invalid JSON: " + e.getLocalizedMessage());
            return;
        }

        final Integer partitionId;
        final Long transactions;
        final Long decode;
        final Long startTime;
        final Long endTime;
        try {
            partitionId = new Integer(json.getInt("partitionId"));
            transactions = new Long(json.getLong("transactions"));
            decode = new Long(json.getLong("decodeTime"));
            startTime = new Long(json.getLong("startTime"));
            endTime = new Long(json.getLong("endTime"));
        } catch (JSONException e) {
            System.err.println("Unable to parse JSON " + e.getLocalizedMessage());
            return;
        }
        // This should always be true
        if (transactions > 0 && decode > 0 && startTime > 0 && endTime > startTime) {
            serverStats.add(new StatClass(partitionId, transactions, decode, startTime, endTime));
            if (startTime < serverStartTS || serverStartTS == 0) {
                serverStartTS = startTime;
            }
            if (endTime > serverEndTS) {
                serverEndTS = endTime;
            }
            if (partitionId > partCount) {
                partCount = partitionId;
            }
            decodeTime += decode;
        }
        // If the else is called it means we received invalid data from the export client
        else {
            System.out.println("WARN: invalid data received - partitionId: " + partitionId + " | transactions: " + transactions + " | decode: " + decode +
                    " | startTime: " + startTime + " | endTime: " + endTime);
        }
    }

    /**
     * Sets up a UDP socket on a certain port to listen for connections.
     */
    private void setupSocketListener() {
        DatagramChannel channel = null;

        // Setup Listener
        try {
            statsSocketSelector = SelectorProvider.provider().openSelector();
            channel = DatagramChannel.open();
            channel.configureBlocking(false);
        } catch (IOException e) {
            exitWithException("Couldn't set up network channels", e);
        }

        // Bind to port & register with a channel
        try {
            InetSocketAddress isa = new InetSocketAddress(
                                            CoreUtils.getLocalAddress(),
                                            config.statsPort);
            channel.socket().setReuseAddress(true);
            channel.socket().bind(isa);
            channel.register(statsSocketSelector, SelectionKey.OP_READ);
        } catch (IOException e) {
            exitWithException("Couldn't bind to socket", e);
        }
    }

    /**
     * Runs the export benchmark test
     * @throws InterruptedException
     * @throws NoConnectionsException
     */
    private void runTest() throws InterruptedException {
        // Connect to servers
        try {
            System.out.println("Test initialization");
            connect(config.servers);
        } catch (InterruptedException e) {
            System.err.println("Error connecting to VoltDB");
            e.printStackTrace();
            System.exit(1);
        }

        // Figure out how long to run for
        benchmarkStartTS = System.currentTimeMillis();
        benchmarkWarmupEndTS = benchmarkStartTS + (config.warmup * 1000);
        benchmarkEndTS = benchmarkWarmupEndTS + (config.duration * 1000);

        // Do the inserts in a separate thread
        Thread writes = new Thread(new Runnable() {
            @Override
            public void run() {
                doInserts(client);
            }
        });
        writes.start();

        // Listen for stats until we stop
        Thread.sleep(config.warmup * 1000);
        setupSocketListener();
        listenForStats();

        writes.join();
        periodicStatsTimer.cancel();
        System.out.println("Client flushed; waiting for export to finish");

        // Wait until export is done
        boolean success = false;
        try {
            success = waitForStreamedAllocatedMemoryZero();
        } catch (IOException e) {
            System.err.println("Error while waiting for export: ");
            e.getLocalizedMessage();
        } catch (ProcCallException e) {
            System.err.println("Error while calling procedures: ");
            e.getLocalizedMessage();
        }

        System.out.println("Finished benchmark");

        // Print results & close
        printResults(benchmarkEndTS-benchmarkWarmupEndTS);
        client.close();

        // Make sure we got serverside stats
        if (serverStats.size() == 0) {
            System.err.println("ERROR: Never received stats from export clients");
            success = false;
        }

        if (!success) {
            System.exit(-1);
        }
    }

    /**
     * Prints a one line update on performance that can be printed
     * periodically during a benchmark.
     */
    public synchronized void printStatistics() {
        ClientStats stats = periodicStatsContext.fetchAndResetBaseline().getStats();

        // Print an ISO8601 timestamp (of the same kind Python logging uses) to help
        // log merger correlate correctly
        System.out.print(LOG_DF.format(new Date(stats.getEndTimestamp())));
        System.out.printf(" Throughput %d/s, ", stats.getTxnThroughput());
        System.out.printf("Aborts/Failures %d/%d, ",
                stats.getInvocationAborts(), stats.getInvocationErrors());
        System.out.printf("Avg/99.999%% Latency %.2f/%.2fms\n", stats.getAverageLatency(),
                stats.kPercentileLatencyAsDouble(0.99999));
    }

    public synchronized Double calcRatio(StatClass index, StatClass indexPrime) {
        Double ratio = new Double(0);
        // Check for overlap format:
        //      |-----index window-----|
        //   |-----indexPrime window-----|
        if (indexPrime.m_endTime >= index.m_endTime && indexPrime.m_startTime <= index.m_startTime) {
            ratio = new Double(index.m_endTime - index.m_startTime) / (indexPrime.m_endTime - indexPrime.m_startTime);
            if (ratio <= 0 || ratio > 1) {
                System.out.println("Bad Ratio 1 - ratio: " + ratio + " || index.endTime: " + index.m_endTime +
                        " || index.startTime: " + index.m_startTime + " || indexPrime.endTime: " + indexPrime.m_endTime +
                        " || indexPrime.startTime: " + indexPrime.m_startTime);
                System.exit(-1);
            }
        }
        // Check for overlap format:
        //      |-----index window-----|
        //        |-indexPrime window-|
        else if (indexPrime.m_endTime <= index.m_endTime && indexPrime.m_startTime >= index.m_startTime) {
            ratio = new Double(1);
        }
        // Check for overlap format:
        //      |-----index window-----|
        //            |--indexPrime window--|
        else if (indexPrime.m_startTime >= index.m_startTime && indexPrime.m_startTime < index.m_endTime) {
            ratio = new Double(index.m_endTime - indexPrime.m_startTime) / (indexPrime.m_endTime - indexPrime.m_startTime);
            if (ratio <= 0 || ratio > 1) {
                System.out.println("Bad Ratio 2 - ratio: " + ratio + " || index.endTime: " + index.m_endTime +
                        " || index.startTime: " + index.m_startTime + " || indexPrime.endTime: " + indexPrime.m_endTime +
                        " || indexPrime.startTime: " + indexPrime.m_startTime);
                System.exit(-1);
            }
        }
        // Check for overlap format:
        //      |-----index window-----|
        // |--indexPrime window--|
        else if (indexPrime.m_endTime <= index.m_endTime && indexPrime.m_endTime > index.m_startTime) {
            ratio = new Double(indexPrime.m_endTime - index.m_startTime) / (indexPrime.m_endTime - indexPrime.m_startTime);
            if (ratio <= 0 || ratio > 1) {
                System.out.println("Bad Ratio 3 - ratio: " + ratio + " || index.endTime: " + index.m_endTime +
                        " || index.startTime: " + index.m_startTime + " || indexPrime.endTime: " + indexPrime.m_endTime +
                        " || indexPrime.startTime: " + indexPrime.m_startTime);
                System.exit(-1);
            }
        }
        return ratio;
    }

    /**
     * Prints the results of the voting simulation and statistics
     * about performance.
     * @param duration   How long the test by count ran
     * @param count      How many objects the test by duration inserted
     * @throws Exception if anything unexpected happens.
     */
    public synchronized void printResults(long duration) {
        ClientStats stats = fullStatsContext.fetch().getStats();

        ArrayList<StatClass> indexStats = new ArrayList<StatClass>();
        for (StatClass index : serverStats) {
            if (index.m_partition.equals(0)) {
                Double transactions = new Double(index.m_transactions);
                Double decode = new Double(index.m_decode);
                for (StatClass indexPrime : serverStats) {
                    // If indexPrime is not partition 0 check for window overlap
                    if (!indexPrime.m_partition.equals(0)) {
                        Double ratio = calcRatio(index, indexPrime);
                        transactions +=  ratio * indexPrime.m_transactions;
                        decode += ratio * indexPrime.m_transactions;
                    }
                }
                indexStats.add(new StatClass(index.m_partition, transactions.longValue(), decode.longValue(), index.m_startTime, index.m_endTime));
            }
        }

        Double tpsSum = new Double(0);
        Double decodeSum = new Double(0);
        for (StatClass index : indexStats) {
            tpsSum += (new Double(index.m_transactions * 1000) / (index.m_endTime - index.m_startTime));
            decodeSum += (new Double(index.m_decode) / index.m_transactions);
        }
        tpsSum = (tpsSum / indexStats.size());
        decodeSum = (decodeSum / indexStats.size());

        // Performance statistics
        System.out.print(HORIZONTAL_RULE);
        System.out.println(" Client Workload Statistics");
        System.out.println(HORIZONTAL_RULE);

        System.out.printf("Average throughput:            %,9d txns/sec\n", stats.getTxnThroughput());
        System.out.printf("Average latency:               %,9.2f ms\n", stats.getAverageLatency());
        System.out.printf("10th percentile latency:       %,9.2f ms\n", stats.kPercentileLatencyAsDouble(.1));
        System.out.printf("25th percentile latency:       %,9.2f ms\n", stats.kPercentileLatencyAsDouble(.25));
        System.out.printf("50th percentile latency:       %,9.2f ms\n", stats.kPercentileLatencyAsDouble(.5));
        System.out.printf("75th percentile latency:       %,9.2f ms\n", stats.kPercentileLatencyAsDouble(.75));
        System.out.printf("90th percentile latency:       %,9.2f ms\n", stats.kPercentileLatencyAsDouble(.9));
        System.out.printf("95th percentile latency:       %,9.2f ms\n", stats.kPercentileLatencyAsDouble(.95));
        System.out.printf("99th percentile latency:       %,9.2f ms\n", stats.kPercentileLatencyAsDouble(.99));
        System.out.printf("99.5th percentile latency:     %,9.2f ms\n", stats.kPercentileLatencyAsDouble(.995));
        System.out.printf("99.9th percentile latency:     %,9.2f ms\n", stats.kPercentileLatencyAsDouble(.999));
        System.out.printf("99.999th percentile latency:   %,9.2f ms\n", stats.kPercentileLatencyAsDouble(.99999));

        System.out.print("\n" + HORIZONTAL_RULE);
        System.out.println(" System Server Statistics");
        System.out.printf("Average throughput:            %,9d txns/sec\n", tpsSum.longValue());
        System.out.printf("Average decode time:           %,9.2f ns\n", decodeSum);
        Double decodePerc = (new Double(decodeTime) / (((serverEndTS - serverStartTS) * (partCount + 1)) * 1000000)) * 100;
        System.out.printf("Percent decode row time:       %,9.2f %%\n", decodePerc);

        System.out.println(HORIZONTAL_RULE);

        System.out.printf("Reported Internal Avg Latency: %,9.2f ms\n", stats.getAverageInternalLatency());

        System.out.print("\n" + HORIZONTAL_RULE);
        System.out.println(" Latency Histogram");
        System.out.println(HORIZONTAL_RULE);
        System.out.println(stats.latencyHistoReport());

        // Write stats to file if requested
        try {
            if ((config.statsfile != null) && (config.statsfile.length() != 0)) {
                FileWriter fw = new FileWriter(config.statsfile);
                fw.append(String.format("%d,%d,%d,%d,%d,%d,%d,0,0,0,0,0,0\n",
                                    stats.getStartTimestamp(),
                                    duration,
                                    successfulInserts.get(),
                                    serverEndTS - serverStartTS,
                                    decodeTime,
                                    decodeSum.longValue(),
                                    tpsSum.longValue()));
                fw.close();
            }
        } catch (IOException e) {
            System.err.println("Error writing stats file");
            e.printStackTrace();
        }
    }

    /**
     * Main routine creates a benchmark instance and kicks off the run method.
     *
     * @param args Command line arguments.
     * @throws Exception if anything goes wrong.
     */
    public static void main(String[] args) {
        ExportBenchConfig config = new ExportBenchConfig();
        config.parse(ExportBenchmark.class.getName(), args);

        try {
            ExportBenchmark bench = new ExportBenchmark(config);
            bench.runTest();
        } catch (InterruptedException e) {
            e.printStackTrace();
        }
    }
}

File: tests/test_apps/exportbenchmark2/client/exportbenchmark/Connect2Server.java
/* This file is part of VoltDB.
 * Copyright (C) 2008-2015 VoltDB Inc.
 *
 * Permission is hereby granted, free of charge, to any person obtaining
 * a copy of this software and associated documentation files (the
 * "Software"), to deal in the Software without restriction, including
 * without limitation the rights to use, copy, modify, merge, publish,
 * distribute, sublicense, and/or sell copies of the Software, and to
 * permit persons to whom the Software is furnished to do so, subject to
 * the following conditions:
 *
 * The above copyright notice and this permission notice shall be
 * included in all copies or substantial portions of the Software.
 *
 * THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,
 * EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF
 * MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT.
 * IN NO EVENT SHALL THE AUTHORS BE LIABLE FOR ANY CLAIM, DAMAGES OR
 * OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE,
 * ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR
 * OTHER DEALINGS IN THE SOFTWARE.
 */

package exportbenchmark;

import java.io.IOException;
import java.util.concurrent.CountDownLatch;

import org.voltdb.client.Client;

public class Connect2Server {
    final static Client client = null;
    /**
     * Connect to a single server with retry. Limited exponential backoff.
     * No timeout. This will run until the process is killed if it's not
     * able to connect.
     *
     * @param server hostname:port or just hostname (hostname can be ip).
     * @return
     */

    static void connectToOneServerWithRetry(String server) {
        int sleep = 1000;
        while (true) {
            try {
                client.createConnection(server);
                break;
            }
            catch (IOException e) {
                System.err.printf("Connection failed - retrying in %d second(s).\n", sleep / 1000);
                try { Thread.sleep(sleep); } catch (InterruptedException interruted) {}
                if (sleep < 8000) sleep += sleep;
            }
        }
        System.out.printf("Connected to VoltDB node at: %s.\n", server);
    }

    /**
     * Connect to a set of servers in parallel. Each will retry until
     * connection. This call will block until all have connected.
     *
     * @param servers A comma separated list of servers using the hostname:port
     * syntax (where :port is optional).
     * @throws InterruptedException if anything bad happens with the threads.
     */
    static Client connect(String servers) throws InterruptedException {
        System.out.println("Connecting to VoltDB...");

        String[] serverArray = servers.split(",");
        final CountDownLatch connections = new CountDownLatch(serverArray.length);

        // use a new thread to connect to each server
        for (final String server : serverArray) {
            new Thread(new Runnable() {
                @Override
                public void run() {
                    connectToOneServerWithRetry(server);
                    connections.countDown();
                }
            }).start();
        }
        // block until all have connected
        connections.await();
        return client;
    }
}



File: tests/test_apps/exportbenchmark2/client/exportbenchmark/ExportBenchmark.java
/* This file is part of VoltDB.
 * Copyright (C) 2008-2015 VoltDB Inc.
 *
 * Permission is hereby granted, free of charge, to any person obtaining
 * a copy of this software and associated documentation files (the
 * "Software"), to deal in the Software without restriction, including
 * without limitation the rights to use, copy, modify, merge, publish,
 * distribute, sublicense, and/or sell copies of the Software, and to
 * permit persons to whom the Software is furnished to do so, subject to
 * the following conditions:
 *
 * The above copyright notice and this permission notice shall be
 * included in all copies or substantial portions of the Software.
 *
 * THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,
 * EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF
 * MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT.
 * IN NO EVENT SHALL THE AUTHORS BE LIABLE FOR ANY CLAIM, DAMAGES OR
 * OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE,
 * ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR
 * OTHER DEALINGS IN THE SOFTWARE.
 */
/*
 * Bogus comment, probably inherited from someplace -- replace!
 *
 * This samples uses multiple threads to post synchronous requests to the
 * VoltDB server, simulating multiple client application posting
 * synchronous requests to the database, using the native VoltDB client
 * library.
 *
 * While synchronous processing can cause performance bottlenecks (each
 * caller waits for a transaction answer before calling another
 * transaction), the VoltDB cluster at large is still able to perform at
 * blazing speeds when many clients are connected to it.
 */

package exportbenchmark;

import java.io.IOException;
import java.nio.ByteBuffer;
import java.nio.channels.Selector;
import java.text.SimpleDateFormat;
import java.util.Timer;
import java.util.TimerTask;
import java.util.concurrent.CountDownLatch;
import java.util.concurrent.atomic.AtomicBoolean;
import java.util.concurrent.atomic.AtomicLong;

import org.voltdb.CLIConfig;
import org.voltdb.client.Client;
import org.voltdb.client.ClientConfig;
import org.voltdb.client.ClientFactory;
import org.voltdb.client.ClientResponse;
import org.voltdb.client.ClientStats;
import org.voltdb.client.ClientStatsContext;
import org.voltdb.client.NoConnectionsException;
import org.voltdb.client.NullCallback;
import org.voltdb.client.ProcCallException;
import org.voltdb.client.ProcedureCallback;

/**
 * Asynchronously sends data to an export table to test VoltDB export performance.
 */
public class ExportBenchmark {

    // handy, rather than typing this out several times
    static final String HORIZONTAL_RULE =
            "----------" + "----------" + "----------" + "----------" +
            "----------" + "----------" + "----------" + "----------" + "\n";

    // Client connection to the server
    static Client client;
    // Validated CLI config
    final ExportBenchConfig config;
    // Ratio of DB inserts to export inserts
    int ratio;
    // Network variables
    Selector statsSocketSelector;
    Thread statsThread;
    ByteBuffer buffer = ByteBuffer.allocate(1024);
    // Statistics manager objects from the client
    static ClientStatsContext periodicStatsContext;
    static ClientStatsContext fullStatsContext;
    // Timer for periodic stats
    Timer periodicStatsTimer;
    // Test stats variables
    long totalInserts = 0;
    AtomicLong successfulInserts = new AtomicLong(0);
    AtomicLong failedInserts = new AtomicLong(0);
    AtomicBoolean testFinished = new AtomicBoolean(false);

    // collectors for min/max/start/stop statistics
    double min = -1;
    double max = 0;
    double start = 0;
    double end = 0;

    int dbInserts;
    int exportInserts;

    // Test timestamp markers
    long benchmarkStartTS, benchmarkWarmupEndTS, benchmarkEndTS, serverStartTS, serverEndTS, decodeTime, partCount;

    static long samples = 0;
    static long sampleSum = 0;

    static final SimpleDateFormat LOG_DF = new SimpleDateFormat("yyyy-MM-dd HH:mm:ss,SSS");

    /**
     * Uses included {@link CLIConfig} class to
     * declaratively state command line options with defaults
     * and validation.
     */
    static class ExportBenchConfig extends CLIConfig {
        @Option(desc = "Interval for performance feedback, in seconds.")
        long displayinterval = 1;

        @Option(desc = "Benchmark duration, in seconds.")
        int duration = 30;

        @Option(desc = "Warmup duration in seconds.")
        int warmup = 10;

        @Option(desc = "Comma separated list of the form server[:port] to connect to.")
        String servers = "localhost";

        @Option (desc = "Port on which to listen for statistics info from export clients")
        int statsPort = 5001;

        @Option(desc = "Filename to write raw summary statistics to.")
        String statsfile = "";

        @Option(desc = "Filename to write periodic stat infomation in CSV format")
        String csvfile = "";

        @Override
        public void validate() {
            if (duration <= 0) exitWithMessageAndUsage("duration must be > 0");
            if (warmup < 0) exitWithMessageAndUsage("warmup must be >= 0");
            if (displayinterval <= 0) exitWithMessageAndUsage("displayinterval must be > 0");
        }
    }

    /**
     * Callback for export insert method. Tracks successes & failures
     */
    class ExportCallback implements ProcedureCallback {
        @Override
        public void clientCallback(ClientResponse response) {
            if (response.getStatus() == ClientResponse.SUCCESS) {
                successfulInserts.incrementAndGet();
            } else {
                failedInserts.incrementAndGet();
            }
        }
    }

    /**
     * Clean way of exiting from an exception
     * @param message   Message to accompany the exception
     * @param e         The exception thrown
     */
    private void exitWithException(String message, Exception e) {
        System.err.println(message);
        System.err.println(e.getLocalizedMessage());
        System.exit(1);
    }

    /**
     * Creates a new instance of the test to be run.
     * Establishes a client connection to a voltdb server, which should already be running
     * @param args The arguments passed to the program
     */
    public ExportBenchmark(ExportBenchConfig config, int dbInserts, int exportInserts) {
        this.config = config;
        this.dbInserts = dbInserts;
        this.exportInserts = exportInserts;
        samples = 0;
        sampleSum = 0;
        serverStartTS = serverEndTS = decodeTime = partCount = 0;
    }

    /**
     * Prints a one line update on performance
     * periodically during benchmark.
     */
    public synchronized void printStatistics() {
        ClientStats stats = periodicStatsContext.fetchAndResetBaseline().getStats();
        long time = Math.round((stats.getEndTimestamp() - benchmarkStartTS) / 1000.0);
        long thrup;

        System.out.printf("%02d:%02d:%02d ", time / 3600, (time / 60) % 60, time % 60);
        thrup = stats.getTxnThroughput();
        System.out.printf("Throughput %d/s, ", thrup);
        System.out.printf("Aborts/Failures %d/%d, ",
                stats.getInvocationAborts(), stats.getInvocationErrors());
        System.out.printf("Avg/95%% Latency %.2f/%.2fms\n", stats.getAverageLatency(),
                stats.kPercentileLatencyAsDouble(0.95));
        samples++;
        if (samples > 3) {
            sampleSum += thrup;
        }

        // collect run statistics -- TPS min, max, start, end
        if (min == -1 || thrup < min) min = thrup;
        if (start == 0) start = thrup;
        if (thrup > max) max = thrup;
        end = thrup;
    }

    /**
    * Create a Timer task to display performance data.
    * It calls printStatistics() every displayInterval seconds
    */
    public void schedulePeriodicStats() {
        periodicStatsTimer = new Timer();
        TimerTask statsPrinting = new TimerTask() {
            @Override
            public void run() { printStatistics(); }
        };
        periodicStatsTimer.scheduleAtFixedRate(statsPrinting,
                                    config.displayinterval * 1000,
                                    config.displayinterval * 1000);
    }

    /**
     * Inserts values into the export table for the test. First it does warmup
     * inserts, then tracked inserts.
     * @param ratio
     * @throws InterruptedException
     * @throws NoConnectionsException
     */
    public void doInserts(Client client, int ratio) {

        // Make sure DB tables are empty
        System.out.println("Truncating DB tables");
        try {
            client.callProcedure("TruncateTables");
        } catch (IOException | ProcCallException e1) {
            // TODO Auto-generated catch block
            e1.printStackTrace();
        }

        // Don't track warmup inserts
        System.out.println("Warming up...");
        long now = System.currentTimeMillis();
        AtomicLong rowId = new AtomicLong(0);
        while (benchmarkWarmupEndTS > now) {
            try {
                client.callProcedure(
                        new NullCallback(),
                        "InsertExport",
                        rowId.getAndIncrement(),
                        dbInserts,
                        exportInserts,
                        0);
                // Check the time every 50 transactions to avoid invoking System.currentTimeMillis() too much
                if (++totalInserts % 50 == 0) {
                    now = System.currentTimeMillis();
                }
            } catch (Exception ignore) {}
        }
        System.out.println("Warmup complete");
        rowId.set(0);

        // reset the stats after warmup is done
        fullStatsContext.fetchAndResetBaseline();
        periodicStatsContext.fetchAndResetBaseline();

        schedulePeriodicStats();

        // Insert objects until we've run for long enough
        System.out.println("Running benchmark...");
        System.out.println("Calling SP " + "InsertExport");
        now = System.currentTimeMillis();
        while (benchmarkEndTS > now) {
            try {

                client.callProcedure(
                        new ExportCallback(),
                        "InsertExport",
                        rowId.getAndIncrement(),
                        dbInserts,
                        exportInserts,
                        0);
                // Check the time every 50 transactions to avoid invoking System.currentTimeMillis() too much
                if (++totalInserts % 50 == 0) {
                    now = System.currentTimeMillis();
                }
            } catch (Exception e) {
                System.err.println("Couldn't insert into VoltDB\n");
                e.printStackTrace();
                System.exit(1);
            }
        }

        try {
            client.drain();
        } catch (Exception e) {
            e.printStackTrace();
        }

        System.out.println("Benchmark complete: wrote " + successfulInserts.get() + " objects");
        System.out.println("Failed to insert " + failedInserts.get() + " objects");

        testFinished.set(true);
        //statsSocketSelector.wakeup();
    }

    /**
     * Runs the export benchmark test
     * @throws InterruptedException
     * @throws NoConnectionsException
     */
    private void runTest() throws InterruptedException {
        // Figure out how long to run for
        benchmarkStartTS = System.currentTimeMillis();
        benchmarkWarmupEndTS = benchmarkStartTS + (config.warmup * 1000);
        benchmarkEndTS = benchmarkWarmupEndTS + (config.duration * 1000);

        // Do the inserts in a separate thread
        Thread writes = new Thread(new Runnable() {
            @Override
            public void run() {
                doInserts(client, ratio);
            }
        });
        writes.start();

        // Listen for stats until we stop
        Thread.sleep(config.warmup * 1000);
        // setupSocketListener();
        // listenForStats();

        writes.join();
        periodicStatsTimer.cancel();
        System.out.println("Client flushed; waiting for export to finish");

        boolean success = false;
        /***
         * Wait until export is done

        try {
            success = Stats.waitForStreamedAllocatedMemoryZero();
        } catch (IOException e) {
            System.err.println("Error while waiting for export: ");
            e.getLocalizedMessage();
        } catch (ProcCallException e) {
            System.err.println("Error while calling procedures: ");S
            e.getLocalizedMessage();
        }
        ***/
        // Print results & close
        System.out.println("Finished benchmark");
        System.out.println("Throughput");
        System.out.format("Start %6.0f, End %6.0f. Delta %6.2f%%%n" , start, end, (end-start)/start*100.0);
        System.out.format("Min %6.0f, Max %6.0f. Delta %6.2f%%%n", min, max, (max-min)/min*100.0);

        try {
            client.drain();
        } catch (NoConnectionsException e) {
            // TODO Auto-generated catch block
            e.printStackTrace();
        }
    }

    static void connectToOneServerWithRetry(String server) {
        int sleep = 1000;
        while (true) {
            try {
                client.createConnection(server);
                break;
            }
            catch (IOException e) {
                System.err.printf("Connection failed - retrying in %d second(s).\n", sleep / 1000);
                try { Thread.sleep(sleep); } catch (InterruptedException interruted) {}
                if (sleep < 8000) sleep += sleep;
            }
        }
        System.out.printf("Connected to VoltDB node at: %s.\n", server);
    }

    /**
     * Connect to a set of servers in parallel. Each will retry until
     * connection. This call will block until all have connected.
     *
     * @param servers A comma separated list of servers using the hostname:port
     * syntax (where :port is optional).
     * @throws InterruptedException if anything bad happens with the threads.
     */
    static void connect(String servers) throws InterruptedException {
        ClientConfig clientConfig = new ClientConfig();
        clientConfig.setReconnectOnConnectionLoss(true);
        clientConfig.setClientAffinity(true);
        client = ClientFactory.createClient(clientConfig);
        fullStatsContext = client.createStatsContext();
        periodicStatsContext = client.createStatsContext();

        System.out.println("Connecting to VoltDB...");

        String[] serverArray = servers.split(",");
        final CountDownLatch connections = new CountDownLatch(serverArray.length);

        // use a new thread to connect to each server
        for (final String server : serverArray) {
            new Thread(new Runnable() {
                @Override
                public void run() {
                    connectToOneServerWithRetry(server);
                    connections.countDown();
                }
            }).start();
        }
        // block until all have connected
        connections.await();
    }
    /* Main routine creates a benchmark instance and kicks off the
     * run method for each configuration variant.
     *
     * We write to a DB table AND a export table in various ratios
     * so for test 1, there's one write to the DB table, none to the export table
     * and for test 2, again there's one write the DB table and one to the export table
     * and so on...
     * @param args Command line arguments.
     * @throws Exception if anything goes wrong.
     */

    public static void main(String[] args) {
        ExportBenchConfig config = new ExportBenchConfig();
        config.parse(ExportBenchmark.class.getName(), args);
        // set up the distinct tests -- (dbInserts, exportInserts) pairs
        final int DBINSERTS = 0;
        final int EXPORTINSERTS = 1;
        int[][] tests = {{5,5}};

     // Connect to servers
        try {
            System.out.println("Test initialization. Servers: " + config.servers);
            connect(config.servers);
        } catch (InterruptedException e) {
            System.err.println("Error connecting to VoltDB");
            e.printStackTrace();
            System.exit(1);
        }

        for (int test = 0; test < tests.length; test++) {
            try {
                 ExportBenchmark bench = new ExportBenchmark(config,tests[test][DBINSERTS], tests[test][EXPORTINSERTS]);
                 System.out.println("Running trial " + test + " -- DB Inserts: " + tests[test][DBINSERTS] + ", Export Inserts: " + tests[test][EXPORTINSERTS]);
                 bench.runTest();
            } catch (InterruptedException e) {
                 e.printStackTrace();
            }

        }
    }
}


File: tests/test_apps/exportbenchmark2/db/exportbenchmark/procedures/InsertExport.java
/* This file is part of VoltDB.
 * Copyright (C) 2008-2015 VoltDB Inc.
 *
 * Permission is hereby granted, free of charge, to any person obtaining
 * a copy of this software and associated documentation files (the
 * "Software"), to deal in the Software without restriction, including
 * without limitation the rights to use, copy, modify, merge, publish,
 * distribute, sublicense, and/or sell copies of the Software, and to
 * permit persons to whom the Software is furnished to do so, subject to
 * the following conditions:
 *
 * The above copyright notice and this permission notice shall be
 * included in all copies or substantial portions of the Software.
 *
 * THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,
 * EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF
 * MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT.
 * IN NO EVENT SHALL THE AUTHORS BE LIABLE FOR ANY CLAIM, DAMAGES OR
 * OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE,
 * ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR
 * OTHER DEALINGS IN THE SOFTWARE.
 */
package exportbenchmark.procedures;

import java.util.Random;

import org.voltdb.ProcInfo;
import org.voltdb.SQLStmt;
import org.voltdb.VoltProcedure;

@ProcInfo(
        partitionInfo = "ALL_VALUES1.rowid:0",
        singlePartition = true
    )

public class InsertExport extends VoltProcedure {
    public final String sqlBase = "(txnid, rowid, rowid_group, type_null_tinyint, type_not_null_tinyint, type_null_smallint, type_not_null_smallint, "
            + "type_null_integer, type_not_null_integer, type_null_bigint, type_not_null_bigint, type_null_timestamp, type_not_null_timestamp, type_null_float, type_not_null_float, "
            + "type_null_decimal, type_not_null_decimal, type_null_varchar25, type_not_null_varchar25, type_null_varchar128, type_not_null_varchar128, type_null_varchar1024, "
            + "type_not_null_varchar1024) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)";
    public final SQLStmt exportInsert1 = new SQLStmt("INSERT INTO ALL_VALUES_EXPORT1 " + sqlBase);
    public final SQLStmt exportInsert2 = new SQLStmt("INSERT INTO ALL_VALUES_EXPORT2 " + sqlBase);
    public final SQLStmt dbInsert1 = new SQLStmt("INSERT INTO ALL_VALUES1 " + sqlBase);
    public final SQLStmt dbInsert2 = new SQLStmt("INSERT INTO ALL_VALUES2 " + sqlBase);

    public long run(long rowid, int dbInserts, int exportInserts, int reversed)
    {
        @SuppressWarnings("deprecation")
        long txid = getVoltPrivateRealTransactionIdDontUseMe();
        //int[] iterations = {1, 5};
        //int dbInserts = 5;
        //int exportInserts = 5;

        // Critical for proper determinism: get a cluster-wide consistent Random instance
        Random rand = new Random(txid);

        // Insert into DB
       for (int row = 0; row < dbInserts; row++) {
            SampleRecord record = new SampleRecord(rowid, rand);
            voltQueueSQL(dbInsert1, txid, rowid, record.rowid_group,
                record.type_null_tinyint, record.type_not_null_tinyint,
                record.type_null_smallint, record.type_not_null_smallint,
                record.type_null_integer, record.type_not_null_integer,
                record.type_null_bigint, record.type_not_null_bigint,
                record.type_null_timestamp, record.type_not_null_timestamp,
                record.type_null_float, record.type_not_null_float,
                record.type_null_decimal, record.type_not_null_decimal,
                record.type_null_varchar25, record.type_not_null_varchar25,
                record.type_null_varchar128, record.type_not_null_varchar128,
                record.type_null_varchar1024, record.type_not_null_varchar1024);

            record = new SampleRecord(rowid, rand);
            voltQueueSQL(dbInsert2, txid, rowid, record.rowid_group,
                record.type_null_tinyint, record.type_not_null_tinyint,
                record.type_null_smallint, record.type_not_null_smallint,
                record.type_null_integer, record.type_not_null_integer,
                record.type_null_bigint, record.type_not_null_bigint,
                record.type_null_timestamp, record.type_not_null_timestamp,
                record.type_null_float, record.type_not_null_float,
                record.type_null_decimal, record.type_not_null_decimal,
                record.type_null_varchar25, record.type_not_null_varchar25,
                record.type_null_varchar128, record.type_not_null_varchar128,
                record.type_null_varchar1024, record.type_not_null_varchar1024);
            }

        // Insert in export table
        for (int row = 0; row < exportInserts; row++) {
            SampleRecord record = new SampleRecord(rowid, rand);
            voltQueueSQL(exportInsert1, txid, rowid, record.rowid_group,
                record.type_null_tinyint, record.type_not_null_tinyint,
                record.type_null_smallint, record.type_not_null_smallint,
                record.type_null_integer, record.type_not_null_integer,
                record.type_null_bigint, record.type_not_null_bigint,
                record.type_null_timestamp, record.type_not_null_timestamp,
                record.type_null_float, record.type_not_null_float,
                record.type_null_decimal, record.type_not_null_decimal,
                record.type_null_varchar25, record.type_not_null_varchar25,
                record.type_null_varchar128,
                record.type_not_null_varchar128,
                record.type_null_varchar1024,
                record.type_not_null_varchar1024);

            record = new SampleRecord(rowid, rand);
            voltQueueSQL(exportInsert2, txid, rowid, record.rowid_group,
                record.type_null_tinyint, record.type_not_null_tinyint,
                record.type_null_smallint, record.type_not_null_smallint,
                record.type_null_integer, record.type_not_null_integer,
                record.type_null_bigint, record.type_not_null_bigint,
                record.type_null_timestamp, record.type_not_null_timestamp,
                record.type_null_float, record.type_not_null_float,
                record.type_null_decimal, record.type_not_null_decimal,
                record.type_null_varchar25, record.type_not_null_varchar25,
                record.type_null_varchar128,
                record.type_not_null_varchar128,
                record.type_null_varchar1024,
                record.type_not_null_varchar1024);
        }

        // Execute queued statements
        voltExecuteSQL(true);

        // Return to caller
        return txid;
    }
}


File: tests/test_apps/exportbenchmark2/db/exportbenchmark/procedures/InsertExport0.java
/* This file is part of VoltDB.
 * Copyright (C) 2008-2015 VoltDB Inc.
 *
 * Permission is hereby granted, free of charge, to any person obtaining
 * a copy of this software and associated documentation files (the
 * "Software"), to deal in the Software without restriction, including
 * without limitation the rights to use, copy, modify, merge, publish,
 * distribute, sublicense, and/or sell copies of the Software, and to
 * permit persons to whom the Software is furnished to do so, subject to
 * the following conditions:
 *
 * The above copyright notice and this permission notice shall be
 * included in all copies or substantial portions of the Software.
 *
 * THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,
 * EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF
 * MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT.
 * IN NO EVENT SHALL THE AUTHORS BE LIABLE FOR ANY CLAIM, DAMAGES OR
 * OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE,
 * ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR
 * OTHER DEALINGS IN THE SOFTWARE.
 */
package exportbenchmark.procedures;

import java.util.Random;

import org.voltdb.ProcInfo;
import org.voltdb.SQLStmt;
import org.voltdb.VoltProcedure;

@ProcInfo(
        partitionInfo = "ALL_VALUES.rowid:0",
        singlePartition = true
    )

public class InsertExport0 extends VoltProcedure {
    public final String sqlBase = "(txnid, rowid, rowid_group, type_null_tinyint, type_not_null_tinyint, type_null_smallint, type_not_null_smallint, "
            + "type_null_integer, type_not_null_integer, type_null_bigint, type_not_null_bigint, type_null_timestamp, type_not_null_timestamp, type_null_float, type_not_null_float, "
            + "type_null_decimal, type_not_null_decimal, type_null_varchar25, type_not_null_varchar25, type_null_varchar128, type_not_null_varchar128, type_null_varchar1024, "
            + "type_not_null_varchar1024) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)";
    public final SQLStmt exportInsert = new SQLStmt("INSERT INTO ALL_VALUES_EXPORT " + sqlBase);
    public final SQLStmt dbInsert = new SQLStmt("INSERT INTO ALL_VALUES " + sqlBase);

    public long run(long rowid, int reversed)
    {
        @SuppressWarnings("deprecation")
        long txid = getVoltPrivateRealTransactionIdDontUseMe();
        //int[] iterations = {1, 5};
        int dbInserts = 1;
        int exportInserts = 0;

        // Critical for proper determinism: get a cluster-wide consistent Random instance
        Random rand = new Random(txid);

        // Insert into DB
        for (int row = 0; row < dbInserts; row++) {
            SampleRecord record = new SampleRecord(rowid, rand);
            voltQueueSQL(
                    dbInsert
                    , txid
                    , rowid
                    , record.rowid_group
                    , record.type_null_tinyint
                    , record.type_not_null_tinyint
                    , record.type_null_smallint
                    , record.type_not_null_smallint
                    , record.type_null_integer
                    , record.type_not_null_integer
                    , record.type_null_bigint
                    , record.type_not_null_bigint
                    , record.type_null_timestamp
                    , record.type_not_null_timestamp
                    , record.type_null_float
                    , record.type_not_null_float
                    , record.type_null_decimal
                    , record.type_not_null_decimal
                    , record.type_null_varchar25
                    , record.type_not_null_varchar25
                    , record.type_null_varchar128
                    , record.type_not_null_varchar128
                    , record.type_null_varchar1024
                    , record.type_not_null_varchar1024
                    );
            }

        // Insert in export table
        for (int row = 0; row < exportInserts; row++) {
            SampleRecord record = new SampleRecord(rowid, rand);
            voltQueueSQL(
                    exportInsert
                    , txid
                    , rowid
                    , record.rowid_group
                    , record.type_null_tinyint
                    , record.type_not_null_tinyint
                    , record.type_null_smallint
                    , record.type_not_null_smallint
                    , record.type_null_integer
                    , record.type_not_null_integer
                    , record.type_null_bigint
                    , record.type_not_null_bigint
                    , record.type_null_timestamp
                    , record.type_not_null_timestamp
                    , record.type_null_float
                    , record.type_not_null_float
                    , record.type_null_decimal
                    , record.type_not_null_decimal
                    , record.type_null_varchar25
                    , record.type_not_null_varchar25
                    , record.type_null_varchar128
                    , record.type_not_null_varchar128
                    , record.type_null_varchar1024
                    , record.type_not_null_varchar1024
                    );
        }

        // Execute queued statements
        voltExecuteSQL(true);

        // Return to caller
        return txid;
    }
}


File: tests/test_apps/exportbenchmark2/db/exportbenchmark/procedures/InsertExport1.java
/* This file is part of VoltDB.
 * Copyright (C) 2008-2015 VoltDB Inc.
 *
 * Permission is hereby granted, free of charge, to any person obtaining
 * a copy of this software and associated documentation files (the
 * "Software"), to deal in the Software without restriction, including
 * without limitation the rights to use, copy, modify, merge, publish,
 * distribute, sublicense, and/or sell copies of the Software, and to
 * permit persons to whom the Software is furnished to do so, subject to
 * the following conditions:
 *
 * The above copyright notice and this permission notice shall be
 * included in all copies or substantial portions of the Software.
 *
 * THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,
 * EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF
 * MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT.
 * IN NO EVENT SHALL THE AUTHORS BE LIABLE FOR ANY CLAIM, DAMAGES OR
 * OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE,
 * ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR
 * OTHER DEALINGS IN THE SOFTWARE.
 */
package exportbenchmark.procedures;

import java.util.Random;

import org.voltdb.ProcInfo;
import org.voltdb.SQLStmt;
import org.voltdb.VoltProcedure;

@ProcInfo(
        partitionInfo = "ALL_VALUES.rowid:0",
        singlePartition = true
    )

public class InsertExport1 extends VoltProcedure {
    public final String sqlBase = "(txnid, rowid, rowid_group, type_null_tinyint, type_not_null_tinyint, type_null_smallint, type_not_null_smallint, "
            + "type_null_integer, type_not_null_integer, type_null_bigint, type_not_null_bigint, type_null_timestamp, type_not_null_timestamp, type_null_float, type_not_null_float, "
            + "type_null_decimal, type_not_null_decimal, type_null_varchar25, type_not_null_varchar25, type_null_varchar128, type_not_null_varchar128, type_null_varchar1024, "
            + "type_not_null_varchar1024) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)";
    public final SQLStmt exportInsert = new SQLStmt("INSERT INTO ALL_VALUES_EXPORT " + sqlBase);
    public final SQLStmt dbInsert = new SQLStmt("INSERT INTO ALL_VALUES " + sqlBase);

    public long run(long rowid, int reversed)
    {
        @SuppressWarnings("deprecation")
        long txid = getVoltPrivateRealTransactionIdDontUseMe();
        //int[] iterations = {1, 5};
        int dbInserts = 1;
        int exportInserts = 1;

        // Critical for proper determinism: get a cluster-wide consistent Random instance
        Random rand = new Random(txid);

        // Insert into DB
        for (int row = 0; row < dbInserts; row++) {
            SampleRecord record = new SampleRecord(rowid, rand);
            voltQueueSQL(
                    dbInsert
                    , txid
                    , rowid
                    , record.rowid_group
                    , record.type_null_tinyint
                    , record.type_not_null_tinyint
                    , record.type_null_smallint
                    , record.type_not_null_smallint
                    , record.type_null_integer
                    , record.type_not_null_integer
                    , record.type_null_bigint
                    , record.type_not_null_bigint
                    , record.type_null_timestamp
                    , record.type_not_null_timestamp
                    , record.type_null_float
                    , record.type_not_null_float
                    , record.type_null_decimal
                    , record.type_not_null_decimal
                    , record.type_null_varchar25
                    , record.type_not_null_varchar25
                    , record.type_null_varchar128
                    , record.type_not_null_varchar128
                    , record.type_null_varchar1024
                    , record.type_not_null_varchar1024
                    );
            }

        // Insert in export table
        for (int row = 0; row < exportInserts; row++) {
            SampleRecord record = new SampleRecord(rowid, rand);
            voltQueueSQL(
                    exportInsert
                    , txid
                    , rowid
                    , record.rowid_group
                    , record.type_null_tinyint
                    , record.type_not_null_tinyint
                    , record.type_null_smallint
                    , record.type_not_null_smallint
                    , record.type_null_integer
                    , record.type_not_null_integer
                    , record.type_null_bigint
                    , record.type_not_null_bigint
                    , record.type_null_timestamp
                    , record.type_not_null_timestamp
                    , record.type_null_float
                    , record.type_not_null_float
                    , record.type_null_decimal
                    , record.type_not_null_decimal
                    , record.type_null_varchar25
                    , record.type_not_null_varchar25
                    , record.type_null_varchar128
                    , record.type_not_null_varchar128
                    , record.type_null_varchar1024
                    , record.type_not_null_varchar1024
                    );
        }

        // Execute queued statements
        voltExecuteSQL(true);

        // Return to caller
        return txid;
    }
}


File: tests/test_apps/exportbenchmark2/db/exportbenchmark/procedures/InsertExport10.java
/* This file is part of VoltDB.
 * Copyright (C) 2008-2015 VoltDB Inc.
 *
 * Permission is hereby granted, free of charge, to any person obtaining
 * a copy of this software and associated documentation files (the
 * "Software"), to deal in the Software without restriction, including
 * without limitation the rights to use, copy, modify, merge, publish,
 * distribute, sublicense, and/or sell copies of the Software, and to
 * permit persons to whom the Software is furnished to do so, subject to
 * the following conditions:
 *
 * The above copyright notice and this permission notice shall be
 * included in all copies or substantial portions of the Software.
 *
 * THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,
 * EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF
 * MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT.
 * IN NO EVENT SHALL THE AUTHORS BE LIABLE FOR ANY CLAIM, DAMAGES OR
 * OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE,
 * ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR
 * OTHER DEALINGS IN THE SOFTWARE.
 */
package exportbenchmark.procedures;

import java.util.Random;

import org.voltdb.ProcInfo;
import org.voltdb.SQLStmt;
import org.voltdb.VoltProcedure;

@ProcInfo(
        partitionInfo = "ALL_VALUES.rowid:0",
        singlePartition = true
    )

public class InsertExport10 extends VoltProcedure {
    public final String sqlBase = "(txnid, rowid, rowid_group, type_null_tinyint, type_not_null_tinyint, type_null_smallint, type_not_null_smallint, "
            + "type_null_integer, type_not_null_integer, type_null_bigint, type_not_null_bigint, type_null_timestamp, type_not_null_timestamp, type_null_float, type_not_null_float, "
            + "type_null_decimal, type_not_null_decimal, type_null_varchar25, type_not_null_varchar25, type_null_varchar128, type_not_null_varchar128, type_null_varchar1024, "
            + "type_not_null_varchar1024) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)";
    public final SQLStmt exportInsert = new SQLStmt("INSERT INTO ALL_VALUES_EXPORT " + sqlBase);
    public final SQLStmt dbInsert = new SQLStmt("INSERT INTO ALL_VALUES " + sqlBase);

    public long run(long rowid, int reversed)
    {
        @SuppressWarnings("deprecation")
        long txid = getVoltPrivateRealTransactionIdDontUseMe();
        int dbInserts = 1;
        int exportInserts = 10;

        // Critical for proper determinism: get a cluster-wide consistent Random instance
        Random rand = new Random(txid);

        // Insert into DB
        for (int row = 0; row < dbInserts; row++) {
            SampleRecord record = new SampleRecord(rowid, rand);
            voltQueueSQL(
                    dbInsert
                    , txid
                    , rowid
                    , record.rowid_group
                    , record.type_null_tinyint
                    , record.type_not_null_tinyint
                    , record.type_null_smallint
                    , record.type_not_null_smallint
                    , record.type_null_integer
                    , record.type_not_null_integer
                    , record.type_null_bigint
                    , record.type_not_null_bigint
                    , record.type_null_timestamp
                    , record.type_not_null_timestamp
                    , record.type_null_float
                    , record.type_not_null_float
                    , record.type_null_decimal
                    , record.type_not_null_decimal
                    , record.type_null_varchar25
                    , record.type_not_null_varchar25
                    , record.type_null_varchar128
                    , record.type_not_null_varchar128
                    , record.type_null_varchar1024
                    , record.type_not_null_varchar1024
                    );
            }

        // Insert in export table
        for (int row = 0; row < exportInserts; row++) {
            SampleRecord record = new SampleRecord(rowid, rand);
            voltQueueSQL(
                    exportInsert
                    , txid
                    , rowid
                    , record.rowid_group
                    , record.type_null_tinyint
                    , record.type_not_null_tinyint
                    , record.type_null_smallint
                    , record.type_not_null_smallint
                    , record.type_null_integer
                    , record.type_not_null_integer
                    , record.type_null_bigint
                    , record.type_not_null_bigint
                    , record.type_null_timestamp
                    , record.type_not_null_timestamp
                    , record.type_null_float
                    , record.type_not_null_float
                    , record.type_null_decimal
                    , record.type_not_null_decimal
                    , record.type_null_varchar25
                    , record.type_not_null_varchar25
                    , record.type_null_varchar128
                    , record.type_not_null_varchar128
                    , record.type_null_varchar1024
                    , record.type_not_null_varchar1024
                    );
        }

        // Execute queued statements
        voltExecuteSQL(true);

        // Return to caller
        return txid;
    }
}


File: tests/test_apps/exportbenchmark2/db/exportbenchmark/procedures/InsertExport5.java
/* This file is part of VoltDB.
 * Copyright (C) 2008-2015 VoltDB Inc.
 *
 * Permission is hereby granted, free of charge, to any person obtaining
 * a copy of this software and associated documentation files (the
 * "Software"), to deal in the Software without restriction, including
 * without limitation the rights to use, copy, modify, merge, publish,
 * distribute, sublicense, and/or sell copies of the Software, and to
 * permit persons to whom the Software is furnished to do so, subject to
 * the following conditions:
 *
 * The above copyright notice and this permission notice shall be
 * included in all copies or substantial portions of the Software.
 *
 * THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,
 * EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF
 * MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT.
 * IN NO EVENT SHALL THE AUTHORS BE LIABLE FOR ANY CLAIM, DAMAGES OR
 * OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE,
 * ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR
 * OTHER DEALINGS IN THE SOFTWARE.
 */
package exportbenchmark.procedures;

import java.util.Random;

import org.voltdb.ProcInfo;
import org.voltdb.SQLStmt;
import org.voltdb.VoltProcedure;

@ProcInfo(
        partitionInfo = "ALL_VALUES1.rowid:0",
        singlePartition = true
    )

public class InsertExport5 extends VoltProcedure {
    public final String sqlBase = "(txnid, rowid, rowid_group, type_null_tinyint, type_not_null_tinyint, type_null_smallint, type_not_null_smallint, "
            + "type_null_integer, type_not_null_integer, type_null_bigint, type_not_null_bigint, type_null_timestamp, type_not_null_timestamp, type_null_float, type_not_null_float, "
            + "type_null_decimal, type_not_null_decimal, type_null_varchar25, type_not_null_varchar25, type_null_varchar128, type_not_null_varchar128, type_null_varchar1024, "
            + "type_not_null_varchar1024) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)";
    public final SQLStmt exportInsert1 = new SQLStmt("INSERT INTO ALL_VALUES_EXPORT1 " + sqlBase);
    public final SQLStmt exportInsert2 = new SQLStmt("INSERT INTO ALL_VALUES_EXPORT2 " + sqlBase);
    public final SQLStmt dbInsert1 = new SQLStmt("INSERT INTO ALL_VALUES1 " + sqlBase);
    public final SQLStmt dbInsert2 = new SQLStmt("INSERT INTO ALL_VALUES2 " + sqlBase);

    public long run(long rowid, int reversed)
    {
        @SuppressWarnings("deprecation")
        long txid = getVoltPrivateRealTransactionIdDontUseMe();
        //int[] iterations = {1, 5};
        int dbInserts = 5;
        int exportInserts = 5;

        // Critical for proper determinism: get a cluster-wide consistent Random instance
        Random rand = new Random(txid);

        // Insert into DB
        for (int row = 0; row < dbInserts; row++) {
            SampleRecord record = new SampleRecord(rowid, rand);
            voltQueueSQL(dbInsert1, txid, rowid, record.rowid_group,
                record.type_null_tinyint, record.type_not_null_tinyint,
                record.type_null_smallint, record.type_not_null_smallint,
                record.type_null_integer, record.type_not_null_integer,
                record.type_null_bigint, record.type_not_null_bigint,
                record.type_null_timestamp, record.type_not_null_timestamp,
                record.type_null_float, record.type_not_null_float,
                record.type_null_decimal, record.type_not_null_decimal,
                record.type_null_varchar25, record.type_not_null_varchar25,
                record.type_null_varchar128, record.type_not_null_varchar128,
                record.type_null_varchar1024, record.type_not_null_varchar1024);

            record = new SampleRecord(rowid, rand);
            voltQueueSQL(dbInsert2, txid, rowid, record.rowid_group,
                record.type_null_tinyint, record.type_not_null_tinyint,
                record.type_null_smallint, record.type_not_null_smallint,
                record.type_null_integer, record.type_not_null_integer,
                record.type_null_bigint, record.type_not_null_bigint,
                record.type_null_timestamp, record.type_not_null_timestamp,
                record.type_null_float, record.type_not_null_float,
                record.type_null_decimal, record.type_not_null_decimal,
                record.type_null_varchar25, record.type_not_null_varchar25,
                record.type_null_varchar128, record.type_not_null_varchar128,
                record.type_null_varchar1024, record.type_not_null_varchar1024);
            }

        // Insert in export table
        for (int row = 0; row < exportInserts; row++) {
            SampleRecord record = new SampleRecord(rowid, rand);
            voltQueueSQL(exportInsert1, txid, rowid, record.rowid_group,
                record.type_null_tinyint, record.type_not_null_tinyint,
                record.type_null_smallint, record.type_not_null_smallint,
                record.type_null_integer, record.type_not_null_integer,
                record.type_null_bigint, record.type_not_null_bigint,
                record.type_null_timestamp, record.type_not_null_timestamp,
                record.type_null_float, record.type_not_null_float,
                record.type_null_decimal, record.type_not_null_decimal,
                record.type_null_varchar25, record.type_not_null_varchar25,
                record.type_null_varchar128,
                record.type_not_null_varchar128,
                record.type_null_varchar1024,
                record.type_not_null_varchar1024);

            record = new SampleRecord(rowid, rand);
            voltQueueSQL(exportInsert2, txid, rowid, record.rowid_group,
                record.type_null_tinyint, record.type_not_null_tinyint,
                record.type_null_smallint, record.type_not_null_smallint,
                record.type_null_integer, record.type_not_null_integer,
                record.type_null_bigint, record.type_not_null_bigint,
                record.type_null_timestamp, record.type_not_null_timestamp,
                record.type_null_float, record.type_not_null_float,
                record.type_null_decimal, record.type_not_null_decimal,
                record.type_null_varchar25, record.type_not_null_varchar25,
                record.type_null_varchar128,
                record.type_not_null_varchar128,
                record.type_null_varchar1024,
                record.type_not_null_varchar1024);
        }

        // Execute queued statements
        voltExecuteSQL(true);

        // Return to caller
        return txid;
    }
}


File: tests/test_apps/exportbenchmark2/db/exportbenchmark/procedures/SampleRecord.java
/* This file is part of VoltDB.
 * Copyright (C) 2008-2015 VoltDB Inc.
 *
 * Permission is hereby granted, free of charge, to any person obtaining
 * a copy of this software and associated documentation files (the
 * "Software"), to deal in the Software without restriction, including
 * without limitation the rights to use, copy, modify, merge, publish,
 * distribute, sublicense, and/or sell copies of the Software, and to
 * permit persons to whom the Software is furnished to do so, subject to
 * the following conditions:
 *
 * The above copyright notice and this permission notice shall be
 * included in all copies or substantial portions of the Software.
 *
 * THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,
 * EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF
 * MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT.
 * IN NO EVENT SHALL THE AUTHORS BE LIABLE FOR ANY CLAIM, DAMAGES OR
 * OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE,
 * ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR
 * OTHER DEALINGS IN THE SOFTWARE.
 */
package exportbenchmark.procedures;

import java.math.BigDecimal;
import java.math.RoundingMode;
import java.util.Random;

import org.voltdb.VoltType;
import org.voltdb.types.TimestampType;

public class SampleRecord
{
    public final long rowid;
    public final Object rowid_group;
    public final Object type_null_tinyint;
    public final Object type_not_null_tinyint;
    public final Object type_null_smallint;
    public final Object type_not_null_smallint;
    public final Object type_null_integer;
    public final Object type_not_null_integer;
    public final Object type_null_bigint;
    public final Object type_not_null_bigint;
    public final Object type_null_timestamp;
    public final Object type_not_null_timestamp;
    public final Object type_null_float;
    public final Object type_not_null_float;
    public final Object type_null_decimal;
    public final Object type_not_null_decimal;
    public final Object type_null_varchar25;
    public final Object type_not_null_varchar25;
    public final Object type_null_varchar128;
    public final Object type_not_null_varchar128;
    public final Object type_null_varchar1024;
    public final Object type_not_null_varchar1024;
    public SampleRecord(long rowid, Random rand)
    {
        this.rowid = rowid;
        this.rowid_group = (byte)((rowid % 255) - 127);
        this.type_null_tinyint          = nextTinyint(rand, true);
        this.type_not_null_tinyint      = nextTinyint(rand);
        this.type_null_smallint         = nextSmallint(rand, true);
        this.type_not_null_smallint     = nextSmallint(rand);
        this.type_null_integer          = nextInteger(rand, true);
        this.type_not_null_integer      = nextInteger(rand);
        this.type_null_bigint           = nextBigint(rand, true);
        this.type_not_null_bigint       = nextBigint(rand);
        this.type_null_timestamp        = nextTimestamp(rand, true);
        this.type_not_null_timestamp    = nextTimestamp(rand);
        this.type_null_float            = nextFloat(rand, true);
        this.type_not_null_float        = nextFloat(rand);
        this.type_null_decimal          = nextDecimal(rand, true);
        this.type_not_null_decimal      = nextDecimal(rand);
        this.type_null_varchar25        = nextVarchar(rand, true, 1, 25);
        this.type_not_null_varchar25    = nextVarchar(rand, 1, 25);
        this.type_null_varchar128       = nextVarchar(rand, true, 25, 128);
        this.type_not_null_varchar128   = nextVarchar(rand, 25, 128);
        this.type_null_varchar1024      = nextVarchar(rand, true, 128, 1024);
        this.type_not_null_varchar1024  = nextVarchar(rand, 128, 1024);
    }

    @Override
    public String toString() {
        String s = "\"" + rowid + "\",\"" + rowid_group + "\",\"" + type_null_tinyint + "\",\"" + type_not_null_tinyint +
                "\",\"" + type_null_smallint + "\",\"" + type_not_null_smallint + "\",\"" + type_null_integer +
                "\",\"" + type_not_null_integer + "\",\"" + type_null_bigint + "\",\"" + type_not_null_bigint +
                "\",\"" + type_null_timestamp + "\",\"" + type_not_null_timestamp + "\",\"" + type_null_float +
                "\",\"" + type_not_null_float + "\",\"" + type_null_decimal + "\",\"" + type_not_null_decimal +
                "\",\"" + type_null_varchar25 + "\",\"" + type_not_null_varchar25 + "\",\"" + type_null_varchar128 +
                "\",\"" + type_not_null_varchar128 + "\",\"" + type_null_varchar1024 + "\",\"" + type_not_null_varchar1024 + "\"";
        return s.replace("\"null\"", "null");   // remove the quotes around NULL's so value is NULL, not a string "null"
    }

    private static Object nextTinyint(Random rand)
    {
        return nextTinyint(rand, false);
    }
    private static Object nextTinyint(Random rand, boolean isNullable)
    {
        if (isNullable && rand.nextBoolean()) return null;
        byte result;
        do { result = (new Integer(rand.nextInt())).byteValue(); } while(result == VoltType.NULL_TINYINT);
        return result;
    }

    private static Object nextSmallint(Random rand)
    {
        return nextSmallint(rand, false);
    }
    private static Object nextSmallint(Random rand, boolean isNullable)
    {
        if (isNullable && rand.nextBoolean()) return null;
        short result;
        do { result = (new Integer(rand.nextInt())).shortValue(); } while(result == VoltType.NULL_SMALLINT);
        return result;
    }

    private static Object nextInteger(Random rand)
    {
        return nextInteger(rand, false);
    }
    private static Object nextInteger(Random rand, boolean isNullable)
    {
        if (isNullable && rand.nextBoolean()) return null;
        int result;
        do { result = rand.nextInt(); } while(result == VoltType.NULL_INTEGER);
        return result;
    }

    private static Object nextBigint(Random rand)
    {
        return nextBigint(rand, false);
    }
    private static Object nextBigint(Random rand, boolean isNullable)
    {
        if (isNullable && rand.nextBoolean()) return null;
        long result;
        do { result = rand.nextLong(); } while(result == VoltType.NULL_BIGINT);
        return result;
    }

    private static Object nextTimestamp(Random rand)
    {
        return nextTimestamp(rand, false);
    }
    private static Object nextTimestamp(Random rand, boolean isNullable)
    {
        if (isNullable && rand.nextBoolean()) return null;
        return new TimestampType(Math.abs(rand.nextInt())*1000l);
    }

    private static Object nextFloat(Random rand)
    {
        return nextFloat(rand, false);
    }
    private static Object nextFloat(Random rand, boolean isNullable)
    {
        if (isNullable && rand.nextBoolean()) return null;
        double result; // Inconsistent naming (!)  Underlying database type is Double
        do { result = rand.nextDouble(); } while(result == VoltType.NULL_FLOAT);
        return result;
    }

    private static Object nextDecimal(Random rand)
    {
        return nextDecimal(rand, false);
    }
    private static Object nextDecimal(Random rand, boolean isNullable)
    {
        if (isNullable && rand.nextBoolean()) return null;
        return (new BigDecimal(rand.nextDouble()*rand.nextLong())).setScale(12, RoundingMode.HALF_EVEN);
    }

    private static Object nextVarchar(Random rand, int minLength, int maxLength)
    {
        return nextVarchar(rand, false, minLength, maxLength);
    }
    private static Object nextVarchar(Random rand, boolean isNullable, int minLength, int maxLength)
    {
        if (isNullable && rand.nextBoolean()) return null;
        int length = (maxLength==minLength)?maxLength:rand.nextInt(maxLength-minLength)+minLength;
        StringBuilder result = new StringBuilder(length);
        while(result.length() < length)
            result.append(Long.toBinaryString(rand.nextLong()));
        return result.toString().substring(0,Math.min(result.length(), length)-1);
    }
}


File: tests/test_apps/exportbenchmark2/db/exportbenchmark/procedures/TruncateTables.java
/* This file is part of VoltDB.
 * Copyright (C) 2008-2015 VoltDB Inc.
 *
 * Permission is hereby granted, free of charge, to any person obtaining
 * a copy of this software and associated documentation files (the
 * "Software"), to deal in the Software without restriction, including
 * without limitation the rights to use, copy, modify, merge, publish,
 * distribute, sublicense, and/or sell copies of the Software, and to
 * permit persons to whom the Software is furnished to do so, subject to
 * the following conditions:
 *
 * The above copyright notice and this permission notice shall be
 * included in all copies or substantial portions of the Software.
 *
 * THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,
 * EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF
 * MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT.
 * IN NO EVENT SHALL THE AUTHORS BE LIABLE FOR ANY CLAIM, DAMAGES OR
 * OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE,
 * ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR
 * OTHER DEALINGS IN THE SOFTWARE.
 */
package exportbenchmark.procedures;

import java.util.Random;

import org.voltdb.ProcInfo;
import org.voltdb.SQLStmt;
import org.voltdb.VoltProcedure;

public class TruncateTables extends VoltProcedure {
    public final SQLStmt truncTable1 = new SQLStmt("TRUNCATE TABLE ALL_VALUES1");
    public final SQLStmt truncTable2 = new SQLStmt("TRUNCATE TABLE ALL_VALUES2");

    public long run()
    {
            voltQueueSQL(truncTable1);
            voltQueueSQL(truncTable2);

        // Execute queued statements
        voltExecuteSQL(true);
        return 0;
    }
}


File: tests/test_apps/exportbenchmark2/exporter/exportbenchmark/NoOpExporter.java
/* This file is part of VoltDB.
 * Copyright (C) 2008-2015 VoltDB Inc.
 *
 * Permission is hereby granted, free of charge, to any person obtaining
 * a copy of this software and associated documentation files (the
 * "Software"), to deal in the Software without restriction, including
 * without limitation the rights to use, copy, modify, merge, publish,
 * distribute, sublicense, and/or sell copies of the Software, and to
 * permit persons to whom the Software is furnished to do so, subject to
 * the following conditions:
 *
 * The above copyright notice and this permission notice shall be
 * included in all copies or substantial portions of the Software.
 *
 * THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,
 * EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF
 * MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT.
 * IN NO EVENT SHALL THE AUTHORS BE LIABLE FOR ANY CLAIM, DAMAGES OR
 * OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE,
 * ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR
 * OTHER DEALINGS IN THE SOFTWARE.
 */
/*
 * Bogus comment -- fix this
 * This samples uses multiple threads to post synchronous requests to the
 * VoltDB server, simulating multiple client application posting
 * synchronous requests to the database, using the native VoltDB client
 * library.
 *
 * While synchronous processing can cause performance bottlenecks (each
 * caller waits for a transaction answer before calling another
 * transaction), the VoltDB cluster at large is still able to perform at
 * blazing speeds when many clients are connected to it.
 */

package exportbenchmark;

import java.util.Properties;

import org.voltdb.export.AdvertisedDataSource;
import org.voltdb.exportclient.ExportClientBase;
import org.voltdb.exportclient.ExportDecoderBase;

public class NoOpExporter extends ExportClientBase {

    @Override
    public void configure(Properties config) throws Exception {
        // We have no properties to configure at this point
    }

    static class NoOpExportDecoder extends ExportDecoderBase {
        NoOpExportDecoder(AdvertisedDataSource source) {
            super(source);
        }

        @Override
        public void sourceNoLongerAdvertised(AdvertisedDataSource source) {
            // The AdvertiseDataSource is no longer available. If file descriptors
            // or threads were allocated to handle the source, free them here.
        }

        @Override
        public boolean processRow(int rowSize, byte[] rowData) throws RestartBlockException {
            // We don't want to do anything yet
            return true;
        }
    }

    @Override
    public ExportDecoderBase constructExportDecoder(AdvertisedDataSource source) {
        return new NoOpExportDecoder(source);
    }
}


File: tests/test_apps/exportbenchmark2/exporter/exportbenchmark/SocketExporter.java
/* This file is part of VoltDB.
 * Copyright (C) 2008-2015 VoltDB Inc.
 *
 * Permission is hereby granted, free of charge, to any person obtaining
 * a copy of this software and associated documentation files (the
 * "Software"), to deal in the Software without restriction, including
 * without limitation the rights to use, copy, modify, merge, publish,
 * distribute, sublicense, and/or sell copies of the Software, and to
 * permit persons to whom the Software is furnished to do so, subject to
 * the following conditions:
 *
 * The above copyright notice and this permission notice shall be
 * included in all copies or substantial portions of the Software.
 *
 * THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,
 * EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF
 * MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT.
 * IN NO EVENT SHALL THE AUTHORS BE LIABLE FOR ANY CLAIM, DAMAGES OR
 * OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE,
 * ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR
 * OTHER DEALINGS IN THE SOFTWARE.
 */
/*
 * This samples uses multiple threads to post synchronous requests to the
 * VoltDB server, simulating multiple client application posting
 * synchronous requests to the database, using the native VoltDB client
 * library.
 *
 * While synchronous processing can cause performance bottlenecks (each
 * caller waits for a transaction answer before calling another
 * transaction), the VoltDB cluster at large is still able to perform at
 * blazing speeds when many clients are connected to it.
 */

package exportbenchmark;

import java.io.IOException;
import java.net.InetSocketAddress;
import java.nio.ByteBuffer;
import java.nio.channels.DatagramChannel;
import java.util.Properties;
import java.util.Timer;
import java.util.TimerTask;
import java.util.concurrent.atomic.AtomicLong;

import org.json_voltpatches.JSONException;
import org.json_voltpatches.JSONObject;
import org.voltcore.logging.VoltLogger;
import org.voltcore.utils.CoreUtils;
import org.voltdb.export.AdvertisedDataSource;
import org.voltdb.exportclient.ExportClientBase;
import org.voltdb.exportclient.ExportDecoderBase;

/**
 * Export class for performance measuring.
 * Export statistics are checked for timestamps, and performance metrics are
 * periodically pushed to a UDP socket for collection.
 */
public class SocketExporter extends ExportClientBase {

    private static final VoltLogger m_logger = new VoltLogger("ExportClient");

    String host;
    int port;
    int statsDuration;
    InetSocketAddress address;
    DatagramChannel channel;

    @Override
    public void configure(Properties config) throws Exception {
        host = config.getProperty("socket.dest", "localhost");
        port = Integer.parseInt(config.getProperty("socket.port", "5001"));
        statsDuration = Integer.parseInt(config.getProperty("stats.duration", "5"));

        if ("localhost".equals(host)) {
            address = new InetSocketAddress(CoreUtils.getLocalAddress(), port);
        } else {
            address = new InetSocketAddress(host, port);
        }
        channel = DatagramChannel.open();
    }

    class SocketExportDecoder extends ExportDecoderBase {
        long transactions = 0;
        long totalDecodeTime = 0;
        long timerStart = 0;

        SocketExportDecoder(AdvertisedDataSource source) {
            super(source);
        }

        /**
         * Prints performance statistics to a socket. Stats are:
         *   -Transactions per second
         *   -Average time for decodeRow() to run
         *   -Partition ID
         */
        public void sendStatistics() {
            if (timerStart > 0) {
                ByteBuffer buffer = ByteBuffer.allocate(1024);
                Long endTime = System.currentTimeMillis();

                // Create message
                JSONObject message = new JSONObject();
                try {
                    message.put("transactions", transactions);
                    message.put("decodeTime", totalDecodeTime);
                    message.put("startTime", timerStart);
                    message.put("endTime", endTime);
                    message.put("partitionId", m_source.partitionId);
                } catch (JSONException e) {
                    m_logger.error("Couldn't create JSON object: " + e.getLocalizedMessage());
                }

                String messageString = message.toString();
                buffer.clear();
                buffer.put((byte)messageString.length());
                buffer.put(messageString.getBytes());
                buffer.flip();

                // Send message over socket
                try {
                    int sent = channel.send(buffer, address);
                    if (sent != messageString.getBytes().length+1) {
                        // Should always send the whole packet.
                        m_logger.error("Error sending entire stats message");
                    }
                } catch (IOException e) {
                    m_logger.error("Couldn't send stats to socket");
                }
                transactions = 0;
                totalDecodeTime = 0;
            }
            timerStart = System.currentTimeMillis();
        }

        @Override
        public void sourceNoLongerAdvertised(AdvertisedDataSource source) {
            try {
                channel.close();
            } catch (IOException ignore) {}
        }

        @Override
        /**
         * Logs the transactions, and determines how long it take to decode
         * the row.
         */
        public boolean processRow(int rowSize, byte[] rowData) throws RestartBlockException {
            // Transaction count
            transactions++;

            // Time decodeRow
            try {
                long startTime = System.nanoTime();
                decodeRow(rowData);
                long endTime = System.nanoTime();

                totalDecodeTime += endTime - startTime;
            } catch (IOException e) {
                m_logger.error(e.getLocalizedMessage());
            }

            return true;
        }

        @Override
        public void onBlockCompletion() {
            if (transactions > 0)
                sendStatistics();
        }
    }

    @Override
    public ExportDecoderBase constructExportDecoder(AdvertisedDataSource source) {
        return new SocketExportDecoder(source);
    }
}