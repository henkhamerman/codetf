Refactoring Types: ['Rename Package', 'Move Class', 'Extract Interface']
ol.java
/**
 * This file is part of Graylog.
 *
 * Graylog is free software: you can redistribute it and/or modify
 * it under the terms of the GNU General Public License as published by
 * the Free Software Foundation, either version 3 of the License, or
 * (at your option) any later version.
 *
 * Graylog is distributed in the hope that it will be useful,
 * but WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
 * GNU General Public License for more details.
 *
 * You should have received a copy of the GNU General Public License
 * along with Graylog.  If not, see <http://www.gnu.org/licenses/>.
 */
package org.graylog2.bootstrap;

import com.codahale.metrics.JmxReporter;
import com.codahale.metrics.MetricRegistry;
import com.codahale.metrics.log4j.InstrumentedAppender;
import com.github.joschi.jadconfig.JadConfig;
import com.github.joschi.jadconfig.ParameterException;
import com.github.joschi.jadconfig.Repository;
import com.github.joschi.jadconfig.RepositoryException;
import com.github.joschi.jadconfig.ValidationException;
import com.github.joschi.jadconfig.guava.GuavaConverterFactory;
import com.github.joschi.jadconfig.guice.NamedConfigParametersModule;
import com.github.joschi.jadconfig.jodatime.JodaTimeConverterFactory;
import com.github.joschi.jadconfig.repositories.EnvironmentRepository;
import com.github.joschi.jadconfig.repositories.PropertiesRepository;
import com.github.joschi.jadconfig.repositories.SystemPropertiesRepository;
import com.google.common.base.Joiner;
import com.google.common.collect.ImmutableList;
import com.google.common.collect.Lists;
import com.google.common.collect.Sets;
import com.google.inject.Binder;
import com.google.inject.CreationException;
import com.google.inject.Injector;
import com.google.inject.Module;
import com.google.inject.name.Names;
import com.google.inject.spi.Message;
import io.airlift.airline.Command;
import io.airlift.airline.Option;
import org.apache.log4j.Level;
import org.graylog2.UI;
import org.graylog2.plugin.BaseConfiguration;
import org.graylog2.plugin.Plugin;
import org.graylog2.plugin.PluginConfigBean;
import org.graylog2.plugin.PluginLoaderConfig;
import org.graylog2.plugin.PluginMetaData;
import org.graylog2.plugin.PluginModule;
import org.graylog2.plugin.ServerStatus;
import org.graylog2.plugin.Tools;
import org.graylog2.plugin.Version;
import org.graylog2.plugin.system.NodeIdPersistenceException;
import org.graylog2.shared.bindings.GuiceInjectorHolder;
import org.graylog2.shared.bindings.GuiceInstantiationService;
import org.graylog2.shared.bindings.InstantiationService;
import org.graylog2.shared.bindings.PluginBindings;
import org.graylog2.shared.plugins.PluginLoader;
import org.graylog2.shared.utilities.ExceptionUtils;
import org.jboss.netty.logging.InternalLoggerFactory;
import org.jboss.netty.logging.Slf4JLoggerFactory;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.slf4j.bridge.SLF4JBridgeHandler;

import java.io.File;
import java.lang.management.ManagementFactory;
import java.nio.file.AccessDeniedException;
import java.util.Arrays;
import java.util.Collection;
import java.util.Collections;
import java.util.HashSet;
import java.util.List;
import java.util.Map;
import java.util.Set;

import static com.google.common.base.Strings.nullToEmpty;

public abstract class CmdLineTool implements Runnable {
    private static final Logger LOG = LoggerFactory.getLogger(CmdLineTool.class);

    protected static final String ENVIRONMENT_PREFIX = "GRAYLOG2_";
    protected static final String PROPERTIES_PREFIX = "graylog2.";
    protected static final Version version = Version.CURRENT_CLASSPATH;
    protected static final String FILE_SEPARATOR = System.getProperty("file.separator");
    protected static final String TMPDIR = System.getProperty("java.io.tmpdir", "/tmp");

    protected final JadConfig jadConfig;
    protected final BaseConfiguration configuration;

    @Option(name = "--dump-config", description = "Show the effective Graylog configuration and exit")
    protected boolean dumpConfig = false;

    @Option(name = "--dump-default-config", description = "Show the default configuration and exit")
    protected boolean dumpDefaultConfig = false;

    @Option(name = {"-d", "--debug"}, description = "Run Graylog in debug mode")
    private boolean debug = false;

    @Option(name = {"-f", "--configfile"}, description = "Configuration file for Graylog")
    private String configFile = "/etc/graylog/server/server.conf";

    protected String commandName = "command";

    protected Injector injector;

    protected CmdLineTool(BaseConfiguration configuration) {
        this(null, configuration);
    }

    protected CmdLineTool(String commandName, BaseConfiguration configuration) {
        jadConfig = new JadConfig();
        jadConfig.addConverterFactory(new GuavaConverterFactory());
        jadConfig.addConverterFactory(new JodaTimeConverterFactory());

        if (commandName == null) {
            if (this.getClass().isAnnotationPresent(Command.class)) {
                this.commandName = this.getClass().getAnnotation(Command.class).name();
            } else {
                this.commandName = "tool";
            }
        } else {
            this.commandName = commandName;
        }
        this.configuration = configuration;
    }


    protected abstract boolean validateConfiguration();

    public boolean isDumpConfig() {
        return dumpConfig;
    }

    public boolean isDumpDefaultConfig() {
        return dumpDefaultConfig;
    }

    public boolean isDebug() {
        return debug;
    }

    protected abstract List<Module> getCommandBindings();

    protected abstract List<Object> getCommandConfigurationBeans();


    @Override
    public void run() {
        setupLogger();

        final PluginBindings pluginBindings = installPluginConfigAndBindings(getPluginPath(configFile));

        if (isDumpDefaultConfig()) {
            dumpDefaultConfigAndExit();
        }

        final NamedConfigParametersModule configModule = readConfiguration(configFile);

        if (isDumpConfig()) {
            dumpCurrentConfigAndExit();
        }

        if (!validateConfiguration()) {
            LOG.error("Validating configuration file failed - exiting.");
            System.exit(1);
        }

        final List<String> arguments = ManagementFactory.getRuntimeMXBean().getInputArguments();
        LOG.info("Running with JVM arguments: {}", Joiner.on(' ').join(arguments));

        injector = setupInjector(configModule, pluginBindings);

        if (injector == null) {
            LOG.error("Injector could not be created, exiting! (Please include the previous error messages in bug reports.)");
            System.exit(1);
        }

        // This is holding all our metrics.
        final MetricRegistry metrics = injector.getInstance(MetricRegistry.class);

        // Report metrics via JMX.
        final JmxReporter reporter = JmxReporter.forRegistry(metrics).build();
        reporter.start();

        InstrumentedAppender logMetrics = new InstrumentedAppender(metrics);
        logMetrics.activateOptions();
        org.apache.log4j.Logger.getRootLogger().addAppender(logMetrics);

        SLF4JBridgeHandler.removeHandlersForRootLogger();
        SLF4JBridgeHandler.install();

        startCommand();
    }

    protected abstract void startCommand();

    protected void setupLogger() {
        // Are we in debug mode?
        Level logLevel = Level.INFO;
        if (isDebug()) {
            LOG.info("Running in Debug mode");
            logLevel = Level.DEBUG;

            // Enable logging for Netty when running in debug mode.
            InternalLoggerFactory.setDefaultFactory(new Slf4JLoggerFactory());
        } else if (onlyLogErrors()) {
            logLevel = Level.ERROR;
        }
        org.apache.log4j.Logger.getRootLogger().setLevel(logLevel);
        org.apache.log4j.Logger.getLogger("org.graylog2").setLevel(logLevel);
    }

    protected boolean onlyLogErrors() {
        return false;
    }

    private void dumpCurrentConfigAndExit() {
        System.out.println(dumpConfiguration(jadConfig.dump()));
        System.exit(0);
    }

    private void dumpDefaultConfigAndExit() {
        for (Object bean : getCommandConfigurationBeans())
            jadConfig.addConfigurationBean(bean);
        dumpCurrentConfigAndExit();
    }

    private PluginBindings installPluginConfigAndBindings(String pluginPath) {
        final Set<Plugin> plugins = loadPlugins(pluginPath);
        final PluginBindings pluginBindings = new PluginBindings(plugins);
        for (final Plugin plugin : plugins) {
            for (final PluginModule pluginModule : plugin.modules()) {
                for (final PluginConfigBean configBean : pluginModule.getConfigBeans()) {
                    jadConfig.addConfigurationBean(configBean);
                }
            }

        }
        return pluginBindings;
    }

    private String getPluginPath(String configFile) {
        PluginLoaderConfig pluginLoaderConfig = new PluginLoaderConfig();
        JadConfig jadConfig = new JadConfig(getConfigRepositories(configFile), pluginLoaderConfig);

        try {
            jadConfig.process();
        } catch (RepositoryException e) {
            LOG.error("Couldn't load configuration: {}", e.getMessage());
            System.exit(1);
        } catch (ParameterException | ValidationException e) {
            LOG.error("Invalid configuration", e);
            System.exit(1);
        }

        return pluginLoaderConfig.getPluginDir();
    }

    protected Set<Plugin> loadPlugins(String pluginPath) {
        final File pluginDir = new File(pluginPath);
        final Set<Plugin> plugins = new HashSet<>();

        final PluginLoader pluginLoader = new PluginLoader(pluginDir);
        for (Plugin plugin : pluginLoader.loadPlugins()) {
            final PluginMetaData metadata = plugin.metadata();
            if (capabilities().containsAll(metadata.getRequiredCapabilities())) {
                if (version.sameOrHigher(metadata.getRequiredVersion())) {
                    plugins.add(plugin);
                } else {
                    LOG.error("Plugin \"" + metadata.getName() + "\" requires version " + metadata.getRequiredVersion() + " - not loading!");
                }
            } else {
                LOG.debug("Skipping plugin \"{}\" because some capabilities are missing ({}).",
                        metadata.getName(),
                        Sets.difference(plugin.metadata().getRequiredCapabilities(), capabilities()));
            }
        }

        LOG.info("Loaded plugins: " + plugins);
        return plugins;
    }

    protected Collection<Repository> getConfigRepositories(String configFile) {
        return Arrays.asList(
                new EnvironmentRepository(ENVIRONMENT_PREFIX),
                new SystemPropertiesRepository(PROPERTIES_PREFIX),
                new PropertiesRepository(configFile)
        );
    }

    private String dumpConfiguration(final Map<String, String> configMap) {
        final StringBuilder sb = new StringBuilder();
        sb.append("# Configuration of graylog2-").append(commandName).append(" ").append(version).append(System.lineSeparator());
        sb.append("# Generated on ").append(Tools.iso8601()).append(System.lineSeparator());

        for (Map.Entry<String, String> entry : configMap.entrySet()) {
            sb.append(entry.getKey()).append('=').append(nullToEmpty(entry.getValue())).append(System.lineSeparator());
        }

        return sb.toString();
    }

    protected NamedConfigParametersModule readConfiguration(final String configFile) {
        final List<Object> beans = getCommandConfigurationBeans();
        for (Object bean : beans) {
            jadConfig.addConfigurationBean(bean);
        }
        jadConfig.setRepositories(getConfigRepositories(configFile));

        LOG.debug("Loading configuration from config file: {}", configFile);
        try {
            jadConfig.process();
        } catch (RepositoryException e) {
            LOG.error("Couldn't load configuration: {}", e.getMessage());
            System.exit(1);
        } catch (ParameterException | ValidationException e) {
            LOG.error("Invalid configuration", e);
            System.exit(1);
        }

        if (configuration.getRestTransportUri() == null) {
            configuration.setRestTransportUri(configuration.getDefaultRestTransportUri());
            LOG.debug("No rest_transport_uri set. Using default [{}].", configuration.getRestTransportUri());
        }

        return new NamedConfigParametersModule(jadConfig.getConfigurationBeans());
    }

    protected List<Module> getSharedBindingsModules(InstantiationService instantiationService) {
        return Lists.newArrayList();
    }

    protected Injector setupInjector(NamedConfigParametersModule configModule, Module... otherModules) {
        try {
            final GuiceInstantiationService instantiationService = new GuiceInstantiationService();

            final ImmutableList.Builder<Module> modules = ImmutableList.builder();
            modules.add(configModule);
            modules.addAll(getSharedBindingsModules(instantiationService));
            modules.addAll(getCommandBindings());
            modules.addAll(Arrays.asList(otherModules));
            modules.add(new Module() {
                @Override
                public void configure(Binder binder) {
                    binder.bind(String.class).annotatedWith(Names.named("BootstrapCommand")).toInstance(commandName);
                }
            });

            final Injector injector = GuiceInjectorHolder.createInjector(modules.build());
            instantiationService.setInjector(injector);

            return injector;
        } catch (CreationException e) {
            annotateInjectorCreationException(e);
            return null;
        } catch (Exception e) {
            LOG.error("Injector creation failed!", e);
            return null;
        }
    }

    protected void annotateInjectorCreationException(CreationException e) {
        annotateInjectorExceptions(e.getErrorMessages());
        throw e;
    }

    protected void annotateInjectorExceptions(Collection<Message> messages) {
        for (Message message : messages) {
            //noinspection ThrowableResultOfMethodCallIgnored
            final Throwable rootCause = ExceptionUtils.getRootCause(message.getCause());
            if (rootCause instanceof NodeIdPersistenceException) {
                LOG.error(UI.wallString(
                        "Unable to read or persist your NodeId file. This means your node id file (" + configuration.getNodeIdFile() + ") is not readable or writable by the current user. The following exception might give more information: " + message));
                System.exit(-1);
            } else if (rootCause instanceof AccessDeniedException) {
                LOG.error(UI.wallString("Unable to access file " + rootCause.getMessage()));
                System.exit(-2);
            } else {
                // other guice error, still print the raw messages
                // TODO this could potentially print duplicate messages depending on what a subclass does...
                LOG.error("Guice error (more detail on log level debug): {}", message.getMessage());
                if (rootCause != null) {
                    LOG.debug("Stacktrace:", rootCause);
                }
            }
        }
    }

    protected Set<ServerStatus.Capability> capabilities() {
        return Collections.emptySet();
    }
}


File: graylog2-bootstrap/src/main/java/org/graylog2/bootstrap/Main.java
/**
 * This file is part of Graylog.
 *
 * Graylog is free software: you can redistribute it and/or modify
 * it under the terms of the GNU General Public License as published by
 * the Free Software Foundation, either version 3 of the License, or
 * (at your option) any later version.
 *
 * Graylog is distributed in the hope that it will be useful,
 * but WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
 * GNU General Public License for more details.
 *
 * You should have received a copy of the GNU General Public License
 * along with Graylog.  If not, see <http://www.gnu.org/licenses/>.
 */
package org.graylog2.bootstrap;

import com.google.common.collect.ImmutableSet;
import io.airlift.airline.Cli;
import io.airlift.airline.Cli.CliBuilder;
import io.airlift.airline.Help;
import org.graylog2.bootstrap.commands.Radio;
import org.graylog2.bootstrap.commands.Server;
import org.graylog2.bootstrap.commands.ShowVersion;
import org.graylog2.bootstrap.commands.journal.JournalDecode;
import org.graylog2.bootstrap.commands.journal.JournalShow;
import org.graylog2.bootstrap.commands.journal.JournalTruncate;

import java.util.Set;

public class Main {
    public static void main(String[] args) {
        final Set<Class<? extends Runnable>> commands = ImmutableSet.of(
                Server.class,
                Radio.class,
                ShowVersion.class,
                Help.class);

        final Set<Class<? extends Runnable>> journalCommands = ImmutableSet.<Class<? extends Runnable>>of(
                JournalShow.class,
                JournalTruncate.class,
                JournalDecode.class
        );

        final CliBuilder<Runnable> builder = Cli.<Runnable>builder("graylog")
                .withDescription("Open source, centralized log management")
                .withDefaultCommand(Help.class)
                .withCommands(commands);

        builder.withGroup("journal")
                .withDescription("Manage the persisted message journal")
                .withDefaultCommand(JournalShow.class)
                .withCommands(journalCommands);

        final Cli<Runnable> cli = builder.build();
        final Runnable command = cli.parse(args);
        command.run();
    }
}


File: graylog2-bootstrap/src/main/java/org/graylog2/bootstrap/commands/ShowVersion.java
/**
 * This file is part of Graylog.
 *
 * Graylog is free software: you can redistribute it and/or modify
 * it under the terms of the GNU General Public License as published by
 * the Free Software Foundation, either version 3 of the License, or
 * (at your option) any later version.
 *
 * Graylog is distributed in the hope that it will be useful,
 * but WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
 * GNU General Public License for more details.
 *
 * You should have received a copy of the GNU General Public License
 * along with Graylog.  If not, see <http://www.gnu.org/licenses/>.
 */
package org.graylog2.bootstrap.commands;

import io.airlift.airline.Command;
import org.graylog2.plugin.Tools;
import org.graylog2.plugin.Version;

/**
 * @author Dennis Oelkers <dennis@torch.sh>
 */
@Command(name = "version", description = "Show the Graylog and JVM versions")
public class ShowVersion implements Runnable {
    private final Version version = Version.CURRENT_CLASSPATH;

    @Override
    public void run() {
        System.out.println("Graylog " + version);
        System.out.println("JRE: " + Tools.getSystemInformation());
    }
}


File: graylog2-server/src/main/java/org/graylog2/StartupException.java
/**
 * This file is part of Graylog.
 *
 * Graylog is free software: you can redistribute it and/or modify
 * it under the terms of the GNU General Public License as published by
 * the Free Software Foundation, either version 3 of the License, or
 * (at your option) any later version.
 *
 * Graylog is distributed in the hope that it will be useful,
 * but WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
 * GNU General Public License for more details.
 *
 * You should have received a copy of the GNU General Public License
 * along with Graylog.  If not, see <http://www.gnu.org/licenses/>.
 */
package org.graylog2;

public class StartupException extends RuntimeException {
    private final String description;
    private final String[] docLinks;

    public StartupException(String description, String[] docLinks) {
        this.description = description;
        this.docLinks = docLinks;
    }

    @Override
    public String getMessage() {
        return UI.wallString(description, docLinks);
    }
}


File: graylog2-server/src/main/java/org/graylog2/initializers/IndexerSetupService.java
/**
 * This file is part of Graylog.
 *
 * Graylog is free software: you can redistribute it and/or modify
 * it under the terms of the GNU General Public License as published by
 * the Free Software Foundation, either version 3 of the License, or
 * (at your option) any later version.
 *
 * Graylog is distributed in the hope that it will be useful,
 * but WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
 * GNU General Public License for more details.
 *
 * You should have received a copy of the GNU General Public License
 * along with Graylog.  If not, see <http://www.gnu.org/licenses/>.
 */
package org.graylog2.initializers;

import com.codahale.metrics.InstrumentedExecutorService;
import com.codahale.metrics.MetricRegistry;
import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.google.common.annotations.VisibleForTesting;
import com.google.common.base.Splitter;
import com.google.common.net.HostAndPort;
import com.google.common.util.concurrent.AbstractIdleService;
import com.google.common.util.concurrent.ThreadFactoryBuilder;
import com.squareup.okhttp.OkHttpClient;
import com.squareup.okhttp.Request;
import com.squareup.okhttp.Response;
import org.elasticsearch.ElasticsearchTimeoutException;
import org.elasticsearch.Version;
import org.elasticsearch.action.admin.cluster.health.ClusterHealthRequest;
import org.elasticsearch.action.admin.cluster.health.ClusterHealthResponse;
import org.elasticsearch.action.admin.cluster.health.ClusterHealthStatus;
import org.elasticsearch.client.Client;
import org.elasticsearch.node.Node;
import org.graylog2.plugin.DocsHelper;
import org.graylog2.UI;
import org.graylog2.configuration.ElasticsearchConfiguration;
import org.graylog2.plugin.Tools;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import javax.inject.Inject;
import javax.inject.Named;
import javax.inject.Singleton;
import java.io.IOException;
import java.net.URI;
import java.util.Iterator;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;
import java.util.concurrent.ThreadFactory;

import static com.codahale.metrics.MetricRegistry.name;
import static com.google.common.base.Strings.isNullOrEmpty;
import static java.util.concurrent.TimeUnit.MILLISECONDS;

@Singleton
public class IndexerSetupService extends AbstractIdleService {
    private static final Logger LOG = LoggerFactory.getLogger(IndexerSetupService.class);
    private static final Version MINIMUM_ES_VERSION = Version.V_1_3_4;
    private static final Version MAXIMUM_ES_VERSION = Version.fromString("1.5.99");

    private final Node node;
    private final ElasticsearchConfiguration configuration;
    private final BufferSynchronizerService bufferSynchronizerService;
    private final OkHttpClient httpClient;
    private final ObjectMapper objectMapper;

    @Inject
    public IndexerSetupService(final Node node,
                               final ElasticsearchConfiguration configuration,
                               final BufferSynchronizerService bufferSynchronizerService,
                               @Named("systemHttpClient") final OkHttpClient httpClient,
                               final MetricRegistry metricRegistry) {
        this(node, configuration, bufferSynchronizerService, httpClient, new ObjectMapper(), metricRegistry);
    }

    @VisibleForTesting
    IndexerSetupService(final Node node,
                        final ElasticsearchConfiguration configuration,
                        final BufferSynchronizerService bufferSynchronizerService,
                        final OkHttpClient httpClient,
                        final ObjectMapper objectMapper,
                        final MetricRegistry metricRegistry) {
        this.node = node;
        this.configuration = configuration;
        this.bufferSynchronizerService = bufferSynchronizerService;
        this.httpClient = httpClient;
        this.objectMapper = objectMapper;

        // Shutdown after the BufferSynchronizerServer has stopped to avoid shutting down ES too early.
        bufferSynchronizerService.addListener(new Listener() {
            @Override
            public void terminated(State from) {
                LOG.debug("Shutting down ES client after buffer synchronizer has terminated.");
                // Properly close ElasticSearch node.
                IndexerSetupService.this.node.close();
            }
        }, executorService(metricRegistry));
    }

    private ExecutorService executorService(MetricRegistry metricRegistry) {
        final ThreadFactory threadFactory = new ThreadFactoryBuilder().setNameFormat("indexer-setup-service-%d").build();
        return new InstrumentedExecutorService(
                Executors.newSingleThreadExecutor(threadFactory),
                metricRegistry,
                name(this.getClass(), "executor-service"));
    }

    @Override
    protected void startUp() throws Exception {
        Tools.silenceUncaughtExceptionsInThisThread();

        LOG.debug("Starting indexer");
        try {
            node.start();

            final Client client = node.client();
            try {
                /* try to determine the cluster health. if this times out we could not connect and try to determine if there's
                   anything listening at all. if that happens this usually has these reasons:
                    1. cluster.name is different
                    2. network.publish_host is not reachable
                    3. wrong address configured
                    4. multicast in use but broken in this environment
                   we handle a red cluster state differently because if we can get that result it means the cluster itself
                   is reachable, which is a completely different problem from not being able to join at all.
                 */
                final ClusterHealthRequest atLeastRed = new ClusterHealthRequest().waitForStatus(ClusterHealthStatus.RED);
                final ClusterHealthResponse health = client.admin()
                        .cluster()
                        .health(atLeastRed)
                        .actionGet(configuration.getClusterDiscoveryTimeout(), MILLISECONDS);
                // we don't get here if we couldn't join the cluster. just check for red cluster state
                if (ClusterHealthStatus.RED.equals(health.getStatus())) {
                    UI.exitHardWithWall("The Elasticsearch cluster state is RED which means shards are unassigned. "
                                    + "This usually indicates a crashed and corrupt cluster and needs to be investigated. Graylog will shut down.",
                            DocsHelper.PAGE_ES_CONFIGURATION.toString());

                }
            } catch (ElasticsearchTimeoutException e) {
                final String hosts = node.settings().get("discovery.zen.ping.unicast.hosts");

                if (!isNullOrEmpty(hosts)) {
                    final Iterable<String> hostList = Splitter.on(',').omitEmptyStrings().trimResults().split(hosts);

                    for (String host : hostList) {
                        final URI esUri = URI.create("http://" + HostAndPort.fromString(host).getHostText() + ":9200/");

                        LOG.info("Checking Elasticsearch HTTP API at {}", esUri);
                        try {
                            // Try the HTTP API endpoint
                            final Request request = new Request.Builder()
                                    .get()
                                    .url(esUri.resolve("/_nodes").toString())
                                    .build();
                            final Response response = httpClient.newCall(request).execute();

                            if (response.isSuccessful()) {
                                final JsonNode resultTree = objectMapper.readTree(response.body().byteStream());
                                final JsonNode nodesList = resultTree.get("nodes");

                                if (!configuration.isDisableVersionCheck()) {
                                    final Iterator<String> nodes = nodesList.fieldNames();
                                    while (nodes.hasNext()) {
                                        final String id = nodes.next();
                                        final Version clusterVersion = Version.fromString(nodesList.get(id).get("version").textValue());

                                        checkClusterVersion(clusterVersion);
                                    }
                                }

                                final String clusterName = resultTree.get("cluster_name").textValue();
                                checkClusterName(clusterName);
                            } else {
                                LOG.error("Could not connect to Elasticsearch at " + esUri + ". Is it running?");
                            }
                        } catch (IOException ioException) {
                            LOG.error("Could not connect to Elasticsearch.", ioException);
                        }
                    }
                }

                UI.exitHardWithWall(
                        "Could not successfully connect to Elasticsearch, if you use multicast check that it is working in your network" +
                                " and that Elasticsearch is running properly and is reachable. Also check that the cluster.name setting is correct.",
                        DocsHelper.PAGE_ES_CONFIGURATION.toString());
            }
        } catch (Exception e) {
            bufferSynchronizerService.setIndexerUnavailable();
            throw e;
        }
    }

    private void checkClusterVersion(Version clusterVersion) {
        if (!clusterVersion.onOrAfter(MINIMUM_ES_VERSION) && !clusterVersion.onOrBefore(MAXIMUM_ES_VERSION)) {
            LOG.error("Elasticsearch node is of the wrong version {}, it must be between {} and {}! "
                            + "Please make sure you are running the correct version of Elasticsearch.",
                    clusterVersion, MINIMUM_ES_VERSION, MAXIMUM_ES_VERSION);
        }
    }

    private void checkClusterName(String clusterName) {
        if (!node.settings().get("cluster.name").equals(clusterName)) {
            LOG.error("Elasticsearch cluster name is different, Graylog uses `{}`, Elasticsearch cluster uses `{}`. "
                            + "Please check the `cluster.name` setting of both Graylog and Elasticsearch.",
                    node.settings().get("cluster.name"),
                    clusterName);
        }
    }

    @Override
    protected void shutDown() throws Exception {
        // See constructor. Actual shutdown happens after BufferSynchronizerServer has stopped.
    }
}
