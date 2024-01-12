Refactoring Types: ['Move Attribute']
client/KafkaStreamImporter.java
/* This file is part of VoltDB.
 * Copyright (C) 2008-2015 VoltDB Inc.
 *
 * This program is free software: you can redistribute it and/or modify
 * it under the terms of the GNU Affero General Public License as
 * published by the Free Software Foundation, either version 3 of the
 * License, or (at your option) any later version.
 *
 * This program is distributed in the hope that it will be useful,
 * but WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
 * GNU Affero General Public License for more details.
 *
 * You should have received a copy of the GNU Affero General Public License
 * along with VoltDB.  If not, see <http://www.gnu.org/licenses/>.
 */

package org.voltdb.importclient;

import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.Properties;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;
import java.util.concurrent.TimeUnit;
import kafka.consumer.ConsumerConfig;
import kafka.consumer.ConsumerIterator;
import kafka.consumer.KafkaStream;
import kafka.javaapi.consumer.ConsumerConnector;
import kafka.message.MessageAndMetadata;
import org.osgi.framework.BundleActivator;
import org.osgi.framework.BundleContext;
import org.voltdb.importer.CSVInvocation;
import org.voltdb.importer.ImportHandlerProxy;

/**
 * Implement a BundleActivator interface and extend ImportHandlerProxy.
 * @author akhanzode
 */
public class KafkaStreamImporter extends ImportHandlerProxy implements BundleActivator {

    private Properties m_properties;
    private String m_procedure;
    private String[] m_topic;
    private String m_zookeeper;

    private KafkaStreamConsumerConnector m_connector;
    private ExecutorService m_es;

    // Register ImportHandlerProxy service.
    @Override
    public void start(BundleContext context) throws Exception {
        context.registerService(ImportHandlerProxy.class.getName(), this, null);
    }

    @Override
    public void stop(BundleContext context) throws Exception {
        //Do any bundle related cleanup.
    }

    @Override
    public synchronized void stop() {
        synchronized (this) {
            try {
                if (m_connector != null) {
                    info("Stopping Kafka connector.");
                    m_connector.stop();
                    info("Stopped Kafka connector.");
                }
            } catch (Exception ex) {
                ex.printStackTrace();
            } finally {
                m_connector = null;
            }
            try {
                if (m_es != null) {
                    info("Stopping Kafka consumer executor.");
                    m_es.shutdown();
                    m_es.awaitTermination(1, TimeUnit.DAYS);
                    info("Stopped Kafka consumer executor.");
                }
            } catch (Exception ex) {
                ex.printStackTrace();
            } finally {
                m_es = null;
            }
        }
    }

    /**
     * Return a name for VoltDB to log with friendly name.
     * @return name of the importer.
     */
    @Override
    public String getName() {
        return "KafkaImporter";
    }

    /**
     * This is called with the properties that are supplied in the deployment.xml
     * Do any initialization here.
     * @param p
     */
    @Override
    public void configure(Properties p) {
        m_properties = (Properties) p.clone();
        m_procedure = (String )m_properties.get("procedure");
        if (m_procedure == null || m_procedure.trim().length() == 0) {
            throw new RuntimeException("Missing procedure.");
        }
        String topics = (String )m_properties.getProperty("topic");
        if (topics == null || topics.trim().length() == 0) {
            throw new RuntimeException("Missing topic(s).");
        }
        m_topic = topics.split(",");
        if (m_topic == null || m_topic.length == 0) {
            throw new RuntimeException("Missing topic(s).");
        }
        m_zookeeper = (String )m_properties.getProperty("zookeeper");
        if (m_zookeeper == null || m_zookeeper.trim().length() == 0) {
            throw new RuntimeException("Missing kafka zookeeper");
        }
    }

    private class KafkaStreamConsumerConnector {

        private ConsumerConnector m_consumer;

        public KafkaStreamConsumerConnector(String zk, String groupName) {
            //Get group id which should be unique for table so as to keep offsets clean for multiple runs.
            String groupId = "voltdbimporter-" + groupName;
            //TODO: Should get this from properties file or something as override?
            Properties props = new Properties();
            props.put("zookeeper.connect", zk);
            props.put("group.id", groupId);
            props.put("zookeeper.session.timeout.ms", "400");
            props.put("zookeeper.sync.time.ms", "200");
            props.put("auto.commit.interval.ms", "1000");
            props.put("auto.commit.enable", "true");
            props.put("auto.offset.reset", "smallest");
            props.put("rebalance.backoff.ms", "10000");

            m_consumer = kafka.consumer.Consumer.createJavaConsumerConnector(new ConsumerConfig(props));
        }

        public void stop() {
            try {
                m_consumer.commitOffsets();
            } catch (Exception ex) {
                ex.printStackTrace();
            }
            try {
                m_consumer.shutdown();
            } catch (Exception ex) {
                ex.printStackTrace();
            } finally {
                m_consumer = null;
            }
        }
    }

    private class KafkaConsumer implements Runnable {

        private final KafkaStream m_stream;
        private final String m_procedure;

        public KafkaConsumer(KafkaStream a_stream, String proc) {
            m_stream = a_stream;
            m_procedure = proc;
        }

        @Override
        public void run() {
            try {
                ConsumerIterator<byte[], byte[]> it = m_stream.iterator();
                while (it.hasNext()) {
                    MessageAndMetadata<byte[], byte[]> md = it.next();
                    byte msg[] = md.message();
                    String line = new String(msg);
                    CSVInvocation invocation = new CSVInvocation(m_procedure, line);
                    callProcedure(invocation);
                }
            } catch (Exception ex) {
                ex.printStackTrace();
            }
        }

    }

    private ExecutorService getConsumerExecutor(KafkaStreamConsumerConnector consumer) throws Exception {

        Map<String, Integer> topicCountMap = new HashMap<>();
        //Get this from config or arg. Use 3 threads default.
        ExecutorService executor = Executors.newFixedThreadPool(3 * m_topic.length);
        for (int i = 0; i < m_topic.length; i++) {
            topicCountMap.put(m_topic[i], 1);
        }
        Map<String, List<KafkaStream<byte[], byte[]>>> consumerMap = consumer.m_consumer.createMessageStreams(topicCountMap);

        for (int i = 0; i < m_topic.length; i++) {
            List<KafkaStream<byte[], byte[]>> streams = consumerMap.get(m_topic[i]);

            // now launch all the threads for partitions.
            for (final KafkaStream stream : streams) {
                KafkaConsumer bconsumer = new KafkaConsumer(stream, m_procedure);
                executor.submit(bconsumer);
            }
        }

        return executor;
    }

    /**
     * This is called when server is ready to accept any transactions.
     */
    @Override
    public void readyForData() {
        try {
            info("Configured and ready with properties: " + m_properties);
            synchronized (this) {
                //TODO: Make group id specific to node.
                m_connector = new KafkaStreamConsumerConnector(m_zookeeper, "voltdb-importer");
                m_es = getConsumerExecutor(m_connector);
            }
            //Now we dont need lock as stop can come along.
            m_es.awaitTermination(365, TimeUnit.DAYS);
        } catch (Exception ex) {
            ex.printStackTrace();
        }
    }

}


File: src/frontend/org/voltdb/importclient/Log4jSocketHandlerImporter.java
/* This file is part of VoltDB.
 * Copyright (C) 2008-2015 VoltDB Inc.
 *
 * This program is free software: you can redistribute it and/or modify
 * it under the terms of the GNU Affero General Public License as
 * published by the Free Software Foundation, either version 3 of the
 * License, or (at your option) any later version.
 *
 * This program is distributed in the hope that it will be useful,
 * but WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
 * GNU Affero General Public License for more details.
 *
 * You should have received a copy of the GNU Affero General Public License
 * along with VoltDB.  If not, see <http://www.gnu.org/licenses/>.
 */

package org.voltdb.importclient;

import java.io.BufferedInputStream;
import java.io.EOFException;
import java.io.IOException;
import java.io.ObjectInputStream;
import java.net.ServerSocket;
import java.net.Socket;
import java.util.ArrayList;
import java.util.Properties;

import org.apache.log4j.spi.LoggingEvent;
import org.osgi.framework.BundleActivator;
import org.osgi.framework.BundleContext;
import org.voltcore.network.ReverseDNSCache;
import org.voltdb.importer.ImportHandlerProxy;
import org.voltdb.importer.Invocation;

/**
 * ImportHandlerProxy implementation for importer that picks up log4j socket appender events.
 */
public class Log4jSocketHandlerImporter extends ImportHandlerProxy implements BundleActivator
{

    private static final String PORT_CONFIG = "port";
    private static final String EVENT_TABLE_CONFIG = "log-event-table";

    private int m_port;
    private String m_tableName;
    private ServerSocket m_serverSocket;
    private final ArrayList<SocketReader> m_connections = new ArrayList<SocketReader>();

    @Override
    public void start(BundleContext context)
    {
        context.registerService(ImportHandlerProxy.class.getName(), this, null);
    }

    @Override
    public void stop(BundleContext context)
    {
        stop();
    }

    @Override
    public void stop()
    {
        closeServerSocket();

        for (SocketReader conn : m_connections) {
            conn.stop();
        }
        m_connections.clear();
    }

    private void closeServerSocket()
    {
        try {
            if (m_serverSocket!=null) {
                m_serverSocket.close();
            }
        } catch(IOException e) { // nothing to do other than log
            info("Unexpected error closing log4j socket appender listener on " + m_port);
        }
    }

    /**
     * Return a name for VoltDB to log with friendly name.
     * @return name of the importer.
     */
    @Override
    public String getName()
    {
        return "Log4jSocketHandlerImporter";
    }

    /**
     * This is called with the properties that are supplied in the deployment.xml
     * Do any initialization here.
     * @param p
     */
    @Override
    public void configure(Properties p)
    {
        Properties properties = (Properties) p.clone();
        String str = properties.getProperty(PORT_CONFIG);
        if (str == null || str.trim().length() == 0) {
            throw new RuntimeException(PORT_CONFIG + " must be specified as a log4j socket importer property");
        }
        m_port = Integer.parseInt(str);

        closeServerSocket(); // just in case something was not cleaned up properly
        try {
            m_serverSocket = new ServerSocket(m_port);
            info("Log4j socket appender listener listening on port: " + m_port);
        } catch(IOException e) {
            error("IOException opening server socket on port " + m_port + " - " + e.getMessage());
            throw new RuntimeException(e);
        }

        m_tableName = properties.getProperty(EVENT_TABLE_CONFIG);
        if (m_tableName==null || m_tableName.trim().length()==0) {
            throw new RuntimeException(EVENT_TABLE_CONFIG + " must be specified as a log4j socket importer property");
        }

        //TODO:
        // - Config for Anish's idea of deleting old events
        // May be use a configuration that says "keep 'n' hrs data" or "keep 'n' rows", whichever is larger.
    }


    /**
     * This is called when server is ready to accept any transactions.
     */
    @Override
    public void readyForData()
    {
        if (!hasTable(m_tableName)) {
            printCreateTableError();
            return;
        }

        try {
            while (true) {
                Socket socket = m_serverSocket.accept();
                SocketReader reader = new SocketReader(socket);
                m_connections.add(reader);
                new Thread(reader).start();
            }
        } catch (IOException e) {
            //TODO: Could check if this was stopped and log info level message to avoid erroneous error log
            error(String.format("Unexpected error [%s] accepting connections on port [%d]", e.getMessage(), m_serverSocket.getLocalPort()));
        } finally {
            closeServerSocket();
        }
    }

    private void printCreateTableError()
    {
            System.err.println("Log event table must exist before Log4j socket importer can be used");
            System.err.println("Please create the table using the following ddl and use appropriate partition:");
            System.err.println("CREATE TABLE " + m_tableName + "\n" +
            "(\n" +
            "  log_event_host    varchar(256) NOT NULL\n" +
            ", logger_name       varchar(256) NOT NULL\n" +
            ", log_level         varchar(25)  NOT NULL\n" +
            ", logging_thread    varchar(25)  NOT NULL\n" +
            ", log_timestamp     timestamp    NOT NULL\n" +
            ", log_message       varchar(1024)\n" +
            ", throwable_str_rep varchar(4096)\n" +
            ");\n" +
            "PARTITION TABLE " + m_tableName + " ON COLUMN log_event_host;");
    }

    /**
     * Read log4j events from socket and persist into volt
     */
    private class SocketReader implements Runnable
    {
        private final Socket m_socket;

        public SocketReader(Socket socket)
        {
            m_socket = socket;
            Log4jSocketHandlerImporter.this.info("Connected to socket appender at " + socket.getRemoteSocketAddress());
        }

        @Override
        public void run()
        {
            try {
                String hostname = ReverseDNSCache.hostnameOrAddress(m_socket.getInetAddress());
                ObjectInputStream ois = new ObjectInputStream(new BufferedInputStream(m_socket.getInputStream()));
                while (true) {
                    LoggingEvent event = (LoggingEvent) ois.readObject();
                    if (!Log4jSocketHandlerImporter.this.callProcedure(new SaveLog4jEventInvocation(hostname, event, m_tableName))) {
                        Log4jSocketHandlerImporter.this.error("Failed to insert log4j event");
                    }
                }
            } catch(EOFException e) { // normal exit condition
                Log4jSocketHandlerImporter.this.info("Client disconnected from " + m_socket.getRemoteSocketAddress());
            } catch (ClassNotFoundException | IOException e) { // assume that these are unrecoverable
                                                               // errors and exit from thread
                Log4jSocketHandlerImporter.this.error(String.format("Unexpected error [%s] reading from %s", e.getMessage(), m_socket.getRemoteSocketAddress()));
                e.printStackTrace();
            } finally {
                closeSocket();
            }
        }

        public void stop()
        {
            closeSocket();
        }

        private void closeSocket()
        {
            try {
                m_socket.close();
            } catch(IOException e) {
                Log4jSocketHandlerImporter.this.error("Could not close log4j event reader socket on " + m_socket.getLocalPort());
                e.printStackTrace();
            }
        }
    }

    /**
     * Class with invocation details for the stored procedure to insert a logging event into voltdb.
     */
    private class SaveLog4jEventInvocation implements Invocation {

        private final String m_hostName;
        private final LoggingEvent m_event;
        private final String m_procName;

        public SaveLog4jEventInvocation(String hostName, LoggingEvent loggingEvent, String tableName) {
            m_hostName = hostName;
            m_event = loggingEvent;
            m_procName = tableName + ".insert";
        }
        @Override
        public String getProcedure()
        {
            return m_procName;
        }

        @Override
        public Object[] getParams() throws IOException
        {
            return new Object[] {
                    m_hostName,
                    m_event.getLoggerName(),
                    m_event.getLevel().toString(),
                    m_event.getThreadName(),
                    m_event.getTimeStamp()*1000,
                    m_event.getRenderedMessage(),
                    getThrowableRep(m_event)
           };
        }

        // Gets the throwable representation from LoggingEvent as a single string
        // with newline chars between lines.
        // Returns null if there is no throwable information in the logging event.
        private String getThrowableRep(LoggingEvent event)
        {
            if (event.getThrowableStrRep() == null || event.getThrowableStrRep().length==0) {
                return null;
            }

            StringBuffer sb = new StringBuffer();
            for (String line : event.getThrowableStrRep()) {
                sb.append(line + "\n");
            }

            // remove the last newline and return the string
            return sb.deleteCharAt(sb.length() - 1).toString();
        }
    }
}


File: src/frontend/org/voltdb/importclient/SocketStreamImporter.java
/* This file is part of VoltDB.
 * Copyright (C) 2008-2015 VoltDB Inc.
 *
 * This program is free software: you can redistribute it and/or modify
 * it under the terms of the GNU Affero General Public License as
 * published by the Free Software Foundation, either version 3 of the
 * License, or (at your option) any later version.
 *
 * This program is distributed in the hope that it will be useful,
 * but WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
 * GNU Affero General Public License for more details.
 *
 * You should have received a copy of the GNU Affero General Public License
 * along with VoltDB.  If not, see <http://www.gnu.org/licenses/>.
 */

package org.voltdb.importclient;

import java.io.BufferedReader;
import java.io.IOException;
import java.io.InputStreamReader;
import java.net.ServerSocket;
import java.net.Socket;
import java.util.ArrayList;
import java.util.Properties;

import org.osgi.framework.BundleActivator;
import org.osgi.framework.BundleContext;
import org.voltdb.importer.CSVInvocation;
import org.voltdb.importer.ImportHandlerProxy;

/**
 * Implement a BundleActivator interface and extend ImportHandlerProxy.
 * @author akhanzode
 */
public class SocketStreamImporter extends ImportHandlerProxy implements BundleActivator {

    private Properties m_properties;
    private ServerSocket m_serverSocket;
    private String m_procedure;
    private final ArrayList<ClientConnectionHandler> m_clients = new ArrayList<ClientConnectionHandler>();

    // Register ImportHandlerProxy service.
    @Override
    public void start(BundleContext context) throws Exception {
        context.registerService(ImportHandlerProxy.class.getName(), this, null);
    }

    @Override
    public void stop(BundleContext context) throws Exception {
        //Do any bundle related cleanup.
    }

    @Override
    public void stop() {
        try {
            for (ClientConnectionHandler s : m_clients) {
                s.stopClient();
            }
            m_clients.clear();
            m_serverSocket.close();
            m_serverSocket = null;
        } catch (IOException ex) {
            ex.printStackTrace();
        }
    }

    /**
     * Return a name for VoltDB to log with friendly name.
     * @return name of the importer.
     */
    @Override
    public String getName() {
        return "SocketImporter";
    }

    /**
     * This is called with the properties that are supplied in the deployment.xml
     * Do any initialization here.
     * @param p
     */
    @Override
    public void configure(Properties p) {
        m_properties = (Properties) p.clone();
        String s = (String )m_properties.get("port");
        m_procedure = (String )m_properties.get("procedure");
        if (m_procedure == null || m_procedure.trim().length() == 0) {
            throw new RuntimeException("Missing procedure.");
        }
        try {
            if (m_serverSocket != null) {
                m_serverSocket.close();
            }
            m_serverSocket = new ServerSocket(Integer.parseInt(s));
        } catch (IOException ex) {
           ex.printStackTrace();
           throw new RuntimeException(ex.getCause());
        }
    }

    //This is ClientConnection handler to read and dispatch data to stored procedure.
    private class ClientConnectionHandler extends Thread {
        private final Socket m_clientSocket;
        private final String m_procedure;
        private final ImportHandlerProxy m_importHandlerProxy;

        public ClientConnectionHandler(ImportHandlerProxy ic, Socket clientSocket, String procedure) {
            m_importHandlerProxy = ic;
            m_clientSocket = clientSocket;
            m_procedure = procedure;
        }

        @Override
        public void run() {
            try {
                while (true) {
                    BufferedReader in = new BufferedReader(
                            new InputStreamReader(m_clientSocket.getInputStream()));
                    while (true) {
                        String line = in.readLine();
                        //You should convert your data to params here.
                        if (line == null) break;
                        CSVInvocation invocation = new CSVInvocation(m_procedure, line);
                        if (!callProcedure(invocation)) {
                            System.out.println("Inserted failed: " + line);
                        }
                    }
                    m_clientSocket.close();
                    System.out.println("Client Closed.");
                }
            } catch (IOException ioe) {
                ioe.printStackTrace();
            }
        }

        public void stopClient() {
            try {
                m_clientSocket.close();
            } catch (IOException ex) {
                ex.printStackTrace();
            }
        }
    }

    /**
     * This is called when server is ready to accept any transactions.
     */
    @Override
    public void readyForData() {
        try {
            info("Configured and ready with properties: " + m_properties);
            String procedure = m_properties.getProperty("procedure");
            while (true) {
                Socket clientSocket = m_serverSocket.accept();
                ClientConnectionHandler ch = new ClientConnectionHandler(this, clientSocket, procedure);
                m_clients.add(ch);
                ch.start();
            }
        } catch (Exception ex) {
            ex.printStackTrace();
        }
    }

}


File: src/frontend/org/voltdb/importer/ImportProcessor.java
/* This file is part of VoltDB.
 * Copyright (C) 2008-2015 VoltDB Inc.
 *
 * This program is free software: you can redistribute it and/or modify
 * it under the terms of the GNU Affero General Public License as
 * published by the Free Software Foundation, either version 3 of the
 * License, or (at your option) any later version.
 *
 * This program is distributed in the hope that it will be useful,
 * but WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
 * GNU Affero General Public License for more details.
 *
 * You should have received a copy of the GNU Affero General Public License
 * along with VoltDB.  If not, see <http://www.gnu.org/licenses/>.
 */

package org.voltdb.importer;

import java.util.HashMap;
import java.util.Map;
import java.util.Properties;
import java.util.ServiceLoader;

import org.apache.zookeeper_voltpatches.ZooKeeper;
import org.osgi.framework.Bundle;
import org.osgi.framework.Constants;
import org.osgi.framework.ServiceReference;
import org.osgi.framework.launch.Framework;
import org.osgi.framework.launch.FrameworkFactory;
import org.voltcore.logging.VoltLogger;
import org.voltcore.messaging.HostMessenger;
import org.voltdb.CatalogContext;
import org.voltdb.ImportHandler;
import org.voltdb.VoltDB;

import com.google_voltpatches.common.base.Preconditions;
import com.google_voltpatches.common.base.Throwables;

public class ImportProcessor implements ImportDataProcessor {

    private static final VoltLogger m_logger = new VoltLogger("IMPORT");
    private final FrameworkFactory m_frameworkFactory;
    private final Map<String, String> m_frameworkProps;
    private final Map<String, BundleWrapper> m_bundles = new HashMap<String, BundleWrapper>();
    private final Map<String, BundleWrapper> m_bundlesByName = new HashMap<String, BundleWrapper>();

    public ImportProcessor() {
        //create properties for osgi
        m_frameworkProps = new HashMap<String, String>();
        //Need this so that ImportContext is available.
        m_frameworkProps.put(Constants.FRAMEWORK_SYSTEMPACKAGES_EXTRA, "org.voltcore.network;version=1.0.0"
                + ",org.voltdb.importer;version=1.0.0,org.apache.log4j;version=1.0.0,org.voltdb.client;version=1.0.0,org.slf4j;version=1.0.0");
        // more properties available at: http://felix.apache.org/documentation/subprojects/apache-felix-service-component-runtime.html
        //m_frameworkProps.put("felix.cache.rootdir", "/tmp"); ?? Should this be under voltdbroot?
        m_frameworkFactory = ServiceLoader.load(FrameworkFactory.class).iterator().next();
    }

    //This abstracts OSGi based and class based importers.
    public class BundleWrapper {
        public final Bundle m_bundle;
        public final Framework m_framework;
        public final Properties m_properties;
        public final ImportHandlerProxy m_handlerProxy;
        private ImportHandler m_handler;

        public BundleWrapper(Bundle bundle, Framework framework, ImportHandlerProxy handler, Properties properties) {
            m_bundle = bundle;
            m_framework = framework;
            m_handlerProxy = handler;
            m_properties = properties;
        }

        public void setHandler(ImportHandler handler) throws Exception {
            Preconditions.checkState((m_handler == null), "ImportHandler can only be set once.");
            m_handler = handler;
            m_handlerProxy.setHandler(handler);
        }

        public ImportHandler getHandler() {
            return m_handler;
        }

        public void stop() {
            try {
                m_handler.stop();
                if (m_bundle != null) {
                    m_bundle.stop();
                }
                if (m_framework != null) {
                    m_framework.stop();
                }
            } catch (Exception ex) {
                m_logger.error("Failed to stop the import bundles.", ex);
            }
        }
    }

    public void addProcessorConfig(Properties properties) {
        String module = properties.getProperty(ImportDataProcessor.IMPORT_MODULE);
        String moduleAttrs[] = module.split("\\|");
        String bundleJar = moduleAttrs[1];
        String moduleType = moduleAttrs[0];

        Preconditions.checkState(!m_bundles.containsKey(bundleJar), "Import to source is already defined.");
        try {
            ImportHandlerProxy importHandlerProxy = null;
            BundleWrapper wrapper = null;
            if (moduleType.equalsIgnoreCase("osgi")) {
                Framework framework = m_frameworkFactory.newFramework(m_frameworkProps);
                framework.start();

                Bundle bundle = framework.getBundleContext().installBundle(bundleJar);
                bundle.start();

                ServiceReference reference = framework.getBundleContext().getServiceReference(ImportDataProcessor.IMPORTER_SERVICE_CLASS);
                if (reference == null) {
                    m_logger.error("Failed to initialize importer from: " + bundleJar);
                    bundle.stop();
                    framework.stop();
                    return;
                }
                Object o = framework.getBundleContext().getService(reference);
                importHandlerProxy = (ImportHandlerProxy )o;
                //Save bundle and properties
                wrapper = new BundleWrapper(bundle, framework, importHandlerProxy, properties);
            } else {
                //Class based importer.
                Class reference = this.getClass().getClassLoader().loadClass(bundleJar);
                if (reference == null) {
                    m_logger.error("Failed to initialize importer from: " + bundleJar);
                    return;
                }

                Object o = reference.newInstance();
                importHandlerProxy = (ImportHandlerProxy )o;
                //Save bundle and properties - no bundle and framework.
                 wrapper = new BundleWrapper(null, null, importHandlerProxy, properties);
            }
            importHandlerProxy.configure(properties);
            String name = importHandlerProxy.getName();
            if (name == null || name.trim().length() == 0) {
                throw new RuntimeException("Importer must implement and return a valid unique name.");
            }
            Preconditions.checkState(!m_bundlesByName.containsKey(name), "Importer must implement and return a valid unique name.");
            m_bundlesByName.put(name, wrapper);
            m_bundles.put(bundleJar, wrapper);
        } catch(Throwable t) {
            m_logger.error("Failed to configure import handler for " + bundleJar, t);
            Throwables.propagate(t);
        }
    }

    private void registerImporterMetaData(CatalogContext catContext, HostMessenger messenger) {
        ZooKeeper zk = messenger.getZK();
        //TODO: Do resource allocation.
    }

    @Override
    public void readyForData(CatalogContext catContext, HostMessenger messenger) {
        //Register and launch watchers. - See if UAC path needs this. TODO.
        registerImporterMetaData(catContext, messenger);

        //Clean any pending and invoked stuff.
        synchronized (this) {
            for (BundleWrapper bw : m_bundles.values()) {
                try {
                    ImportHandler importHandler = new ImportHandler(bw.m_handlerProxy, catContext);
                    //Set the internal handler
                    bw.setHandler(importHandler);
                    importHandler.readyForData();
                    m_logger.info("Importer started: " + bw.m_handlerProxy.getName());
                } catch (Exception ex) {
                    //Should never fail. crash.
                    VoltDB.crashLocalVoltDB("Import failed to set Handler", true, ex);
                    m_logger.error("Failed to start the import handler: " + bw.m_handlerProxy.getName(), ex);
                }
            }
        }
    }

    @Override
    public void shutdown() {
        synchronized (this) {
            try {
                //Stop all the bundle wrappers.
                for (BundleWrapper bw : m_bundles.values()) {
                    try {
                        bw.stop();
                    } catch (Exception ex) {
                        m_logger.error("Failed to stop the import handler: " + bw.m_handlerProxy.getName(), ex);
                    }
                }
                m_bundles.clear();
            } catch (Exception ex) {
                m_logger.error("Failed to stop the import bundles.", ex);
            }
        }
    }

    @Override
    public void setProcessorConfig(Map<String, Properties> config) {
        for (String cname : config.keySet()) {
            Properties properties = config.get(cname);

            String importBundleJar = properties.getProperty(IMPORT_MODULE);
            Preconditions.checkNotNull(importBundleJar, "Import source is undefined or custom export plugin class missing.");
            addProcessorConfig(properties);
        }
    }

}


File: tests/frontend/org/voltdb/TestImportSuite.java
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


package org.voltdb;

import java.io.File;
import java.io.IOException;
import java.io.OutputStream;
import java.net.Socket;
import java.util.HashMap;
import java.util.Map;
import java.util.Properties;
import java.util.Random;
import java.util.concurrent.CountDownLatch;

import org.apache.log4j.Level;
import org.apache.log4j.Logger;
import org.apache.log4j.net.SocketAppender;
import org.voltdb.client.Client;
import org.voltdb.client.ClientImpl;
import org.voltdb.client.ClientResponse;
import org.voltdb.compiler.VoltProjectBuilder;
import org.voltdb.regressionsuites.LocalCluster;
import org.voltdb.regressionsuites.MultiConfigSuiteBuilder;
import org.voltdb.regressionsuites.RegressionSuite;
import org.voltdb.regressionsuites.TestSQLTypesSuite;
import org.voltdb.utils.VoltFile;

import com.google_voltpatches.common.collect.ImmutableMap;

/**
 * End to end Import tests using the injected socket importer.
 *
 */

public class TestImportSuite extends RegressionSuite {
    private static final Logger s_testSocketLogger = Logger.getLogger("testSocketLogger");
    private static final Level[] s_levels =
        { Level.DEBUG, Level.ERROR, Level.FATAL, Level.INFO, Level.TRACE, Level.WARN };

    private Boolean m_socketHandlerInitialized = false;

    @Override
    public void setUp() throws Exception
    {
        VoltFile.recursivelyDelete(new File("/tmp/" + System.getProperty("user.name")));
        File f = new File("/tmp/" + System.getProperty("user.name"));
        f.mkdirs();

        super.setUp();
    }

    private void setupLog4jSocketHandler() {
        synchronized(m_socketHandlerInitialized) {
            if (m_socketHandlerInitialized) return;

            SocketAppender appender = new SocketAppender("localhost", 6060);
            appender.setReconnectionDelay(50);
            s_testSocketLogger.setAdditivity(false);
            s_testSocketLogger.removeAllAppenders();
            s_testSocketLogger.setLevel(Level.ALL);
            s_testSocketLogger.addAppender(appender);
            m_socketHandlerInitialized = true;
        }
    }

    @Override
    public void tearDown() throws Exception {
        super.tearDown();
    }

    abstract class DataPusher extends Thread {
        private final int m_count;
        private final CountDownLatch m_latch;

        public DataPusher(int count, CountDownLatch latch) {
            m_count = count;
            m_latch = latch;
        }

        protected abstract void initialize();
        protected abstract void close();
        protected abstract void pushData(String str) throws Exception;

        @Override
        public void run() {
            initialize();

            try {
                for (int icnt = 0; icnt < m_count; icnt++) {
                    String s = String.valueOf(System.nanoTime() + icnt) + "," + System.currentTimeMillis() + "\n";
                    pushData(s);
                    Thread.sleep(0, 1);
                }
            } catch (Exception ex) {
                ex.printStackTrace();
            } finally {
                close();
                m_latch.countDown();
            }
        }

    }

    class SocketDataPusher extends DataPusher {
        private final String m_server;
        private final int m_port;
        private OutputStream m_sout;

        public SocketDataPusher(String server, int port, int count, CountDownLatch latch) {
            super(count, latch);
            m_server = server;
            m_port = port;
        }

        @Override
        protected void initialize() {
            m_sout = connectToOneServerWithRetry(m_server, m_port);
            System.out.printf("Connected to VoltDB socket importer at: %s.\n", m_server + ":" + m_port);
        }

        @Override
        protected void pushData(String str) throws Exception {
            m_sout.write(str.getBytes());
        }

        @Override
        protected void close() {
            try {
                m_sout.flush();
                m_sout.close();
            } catch (IOException ex) {
            }
        }
    }

    class Log4jDataPusher extends DataPusher {

        private final Random random = new Random();

        public Log4jDataPusher(int count, CountDownLatch latch) {
            super(count, latch);
        }

        @Override
        protected void initialize() {
            TestImportSuite.this.setupLog4jSocketHandler();
        }

        @Override
        protected void pushData(String str) throws Exception {
            s_testSocketLogger.log(s_levels[random.nextInt(s_levels.length)], str);
        }

        @Override
        protected void close() {
        }
    }

    private void pushDataToImporters(int count, int loops) throws Exception {
        CountDownLatch latch = new CountDownLatch(2*loops);
        for (int i=0; i<loops; i++) {
            (new SocketDataPusher("localhost", 7001, count, latch)).start();
            (new Log4jDataPusher(count, latch)).start();
        }
        latch.await();
    }

    private void verifyData(Client client, int count) throws Exception {
        verifyData(client, count, -1);
    }

    private void verifyData(Client client, int count, int min) throws Exception {
        ClientResponse response = client.callProcedure("@AdHoc", "select count(*) from importTable");
        assertEquals(ClientResponse.SUCCESS, response.getStatus());
            assertEquals(count, response.getResults()[0].asScalarLong());

        response = client.callProcedure("@AdHoc", "select count(*) from log_events");
        assertEquals(ClientResponse.SUCCESS, response.getStatus());
        if (min<0) {
            assertEquals(count, response.getResults()[0].asScalarLong());
        } else {
            long result = response.getResults()[0].asScalarLong();
            assertTrue(result + " not between " + min + " and " + count, result>=min && result<=count);
        }
    }

    public void testImportSimpleData() throws Exception {
        System.out.println("testImportSimpleData");
        Client client = getClient();
        while (!((ClientImpl) client).isHashinatorInitialized()) {
            Thread.sleep(1000);
            System.out.println("Waiting for hashinator to be initialized...");
        }

        pushDataToImporters(100, 1);
        verifyData(client, 100);
        client.close();
    }

    public void testImportMultipleTimes() throws Exception {
        System.out.println("testImportUpdateApplicationCatalog");
        Client client = getClient();
        while (!((ClientImpl) client).isHashinatorInitialized()) {
            Thread.sleep(1000);
            System.out.println("Waiting for hashinator to be initialized...");
        }

        pushDataToImporters(100, 1);
        verifyData(client, 100);

        Thread.sleep(0, 1);

        pushDataToImporters(100, 1);
        verifyData(client, 200);

        client.close();
    }

    public void testImportMultipleClientsInParallel() throws Exception {
        System.out.println("testImportMultipleClientsInParallel");
        Client client = getClient();
        while (!((ClientImpl) client).isHashinatorInitialized()) {
            Thread.sleep(1000);
            System.out.println("Waiting for hashinator to be initialized...");
        }

        pushDataToImporters(100, 2);
        verifyData(client, 100*2);
        client.close();
    }

    public void testImportMultipleClientsUpdateApplicationCatalogWhenNotPushing() throws Exception {
        System.out.println("testImportMultipleClientsUpdateApplicationCatalogWhenNotPushing");
        Client client = getClient();
        while (!((ClientImpl) client).isHashinatorInitialized()) {
            Thread.sleep(1000);
            System.out.println("Waiting for hashinator to be initialized...");
        }

        pushDataToImporters(1000, 3);
        verifyData(client, 3000);

        ClientResponse response = client.callProcedure("@AdHoc", "create table nudge(id integer);");
        assertEquals(ClientResponse.SUCCESS, response.getStatus());

        pushDataToImporters(1000, 4);
        // log4j will lose some events because of reconnection delay
        verifyData(client, 7000, 3001);

        client.close();
    }

    /**
     * Connect to a single server with retry. Limited exponential backoff.
     * No timeout. This will run until the process is killed if it's not
     * able to connect.
     *
     * @param server hostname:port or just hostname (hostname can be ip).
     */
    static OutputStream connectToOneServerWithRetry(String server, int port) {
        int sleep = 1000;
        while (true) {
            try {
                Socket pushSocket = new Socket(server, port);
                OutputStream out = pushSocket.getOutputStream();
                System.out.printf("Connected to VoltDB node at: %s.\n", server);
                return out;
            }
            catch (Exception e) {
                System.err.printf("Connection failed - retrying in %d second(s).\n", sleep / 1000);
                try { Thread.sleep(sleep); } catch (Exception interruted) {}
                if (sleep < 8000) sleep += sleep;
            }
        }
    }

    public TestImportSuite(final String name) {
        super(name);
    }

    static public junit.framework.Test suite() throws Exception
    {

        LocalCluster config;
        Map<String, String> additionalEnv = new HashMap<String, String>();

        final MultiConfigSuiteBuilder builder =
            new MultiConfigSuiteBuilder(TestImportSuite.class);

        VoltProjectBuilder project = new VoltProjectBuilder();
        project.setUseDDLSchema(true);
        project.addSchema(TestSQLTypesSuite.class.getResource("sqltypessuite-import-ddl.sql"));

        // configure socket importer
        Properties props = new Properties();
        props.putAll(ImmutableMap.<String, String>of(
                "port", "7001",
                "decode", "true",
                "procedure", "importTable.insert"));
        project.addImport(true, "custom", "csv", "org.voltdb.importclient.SocketStreamImporter", props);
        project.addPartitionInfo("importTable", "PKEY");

        // configure log4j socket handler importer
        props = new Properties();
        props.putAll(ImmutableMap.<String, String>of(
                "port", "6060",
                "log-event-table", "log_events"));
        project.addImport(true, "custom", null, "org.voltdb.importclient.Log4jSocketHandlerImporter", props);

        /*
         * compile the catalog all tests start with
         */

        config = new LocalCluster("import-ddl-cluster-rep.jar", 4, 1, 0,
                BackendTarget.NATIVE_EE_JNI, LocalCluster.FailureState.ALL_RUNNING, true, false, additionalEnv);
        config.setHasLocalServer(false);
        boolean compile = config.compile(project);
        assertTrue(compile);
        builder.addServerConfig(config);

        return builder;
    }
}
