Refactoring Types: ['Move Class']
etbrains/jps/cmdline/BuildMain.java
/*
 * Copyright 2000-2012 JetBrains s.r.o.
 *
 * Licensed under the Apache License, Version 2.0 (the "License");
 * you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at
 *
 * http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 */
package org.jetbrains.jps.cmdline;

import com.intellij.openapi.diagnostic.Logger;
import com.intellij.openapi.util.io.FileSystemUtil;
import com.intellij.openapi.util.io.FileUtil;
import com.intellij.openapi.util.text.StringUtil;
import io.netty.bootstrap.Bootstrap;
import io.netty.channel.*;
import io.netty.channel.nio.NioEventLoopGroup;
import io.netty.channel.socket.nio.NioSocketChannel;
import io.netty.handler.codec.protobuf.ProtobufDecoder;
import io.netty.handler.codec.protobuf.ProtobufEncoder;
import io.netty.handler.codec.protobuf.ProtobufVarint32FrameDecoder;
import io.netty.handler.codec.protobuf.ProtobufVarint32LengthFieldPrepender;
import org.apache.log4j.Level;
import org.apache.log4j.PropertyConfigurator;
import org.jetbrains.annotations.NonNls;
import org.jetbrains.annotations.NotNull;
import org.jetbrains.annotations.Nullable;
import org.jetbrains.jps.api.CmdlineProtoUtil;
import org.jetbrains.jps.api.CmdlineRemoteProto;
import org.jetbrains.jps.api.GlobalOptions;
import org.jetbrains.jps.builders.BuildTarget;
import org.jetbrains.jps.incremental.BuilderRegistry;
import org.jetbrains.jps.incremental.MessageHandler;
import org.jetbrains.jps.incremental.Utils;
import org.jetbrains.jps.incremental.fs.BuildFSState;
import org.jetbrains.jps.incremental.messages.BuildMessage;
import org.jetbrains.jps.incremental.storage.BuildTargetsState;
import org.jetbrains.jps.service.SharedThreadPool;

import java.io.*;
import java.net.InetSocketAddress;
import java.util.UUID;
import java.util.concurrent.TimeUnit;

/**
 * @author Eugene Zhuravlev
 *         Date: 4/16/12
 */
@SuppressWarnings("UseOfSystemOutOrSystemErr")
public class BuildMain {
  private static final String PRELOAD_PROJECT_PATH = "preload.project.path";
  private static final String PRELOAD_CONFIG_PATH = "preload.config.path";
  
  private static final String LOG_CONFIG_FILE_NAME = "build-log.properties";
  private static final String LOG_FILE_NAME = "build.log";
  private static final String DEFAULT_LOGGER_CONFIG = "defaultLogConfig.properties";
  private static final String LOG_FILE_MACRO = "$LOG_FILE_PATH$";
  private static final Logger LOG;
  static {
    initLoggers();
    LOG = Logger.getInstance("#org.jetbrains.jps.cmdline.BuildMain");
  }

  private static final int HOST_ARG = 0;
  private static final int PORT_ARG = HOST_ARG + 1;
  private static final int SESSION_ID_ARG = PORT_ARG + 1;
  private static final int SYSTEM_DIR_ARG = SESSION_ID_ARG + 1;

  private static NioEventLoopGroup ourEventLoopGroup;
  @Nullable 
  private static PreloadedData ourPreloadedData;

  public static void main(String[] args){
    final long processStart = System.currentTimeMillis();
    final String startMessage = "Build process started. Classpath: " + System.getProperty("java.class.path");
    System.out.println(startMessage);
    LOG.info(startMessage);
    
    final String host = args[HOST_ARG];
    final int port = Integer.parseInt(args[PORT_ARG]);
    final UUID sessionId = UUID.fromString(args[SESSION_ID_ARG]);
    @SuppressWarnings("ConstantConditions")
    final File systemDir = new File(FileUtil.toCanonicalPath(args[SYSTEM_DIR_ARG]));
    Utils.setSystemRoot(systemDir);

    final long connectStart = System.currentTimeMillis();
    // IDEA-123132, let's try again
    for (int attempt = 0; attempt < 3; attempt++) {
      try {
        ourEventLoopGroup = new NioEventLoopGroup(1, SharedThreadPool.getInstance());
        break;
      }
      catch (IllegalStateException e) {
        if (attempt == 2) {
          printErrorAndExit(host, port, e);
          return;
        }
        else {
          LOG.warn("Cannot create event loop, attempt #" + attempt, e);
          try {
            //noinspection BusyWait
            Thread.sleep(10 * (attempt + 1));
          }
          catch (InterruptedException ignored) {
          }
        }
      }
    }

    final Bootstrap bootstrap = new Bootstrap().group(ourEventLoopGroup).channel(NioSocketChannel.class).handler(new ChannelInitializer() {
      @Override
      protected void initChannel(Channel channel) throws Exception {
        channel.pipeline().addLast(new ProtobufVarint32FrameDecoder(),
                                   new ProtobufDecoder(CmdlineRemoteProto.Message.getDefaultInstance()),
                                   new ProtobufVarint32LengthFieldPrepender(),
                                   new ProtobufEncoder(),
                                   new MyMessageHandler(sessionId));
      }
    }).option(ChannelOption.TCP_NODELAY, true).option(ChannelOption.SO_KEEPALIVE, true);

    final ChannelFuture future = bootstrap.connect(new InetSocketAddress(host, port)).awaitUninterruptibly();

    
    final boolean success = future.isSuccess();
    if (success) {
      LOG.info("Connection to IDE established in " + (System.currentTimeMillis() - connectStart) + " ms");

      final String projectPathToPreload = System.getProperty(PRELOAD_PROJECT_PATH, null);
      final String globalsPathToPreload = System.getProperty(PRELOAD_CONFIG_PATH, null); 
      if (projectPathToPreload != null && globalsPathToPreload != null) {
        final PreloadedData data = new PreloadedData();
        ourPreloadedData = data;
        try {
          FileSystemUtil.getAttributes(projectPathToPreload); // this will pre-load all FS optimizations

          final BuildRunner runner = new BuildRunner(new JpsModelLoaderImpl(projectPathToPreload, globalsPathToPreload, null));
          data.setRunner(runner);

          final File dataStorageRoot = Utils.getDataStorageRoot(projectPathToPreload);
          final BuildFSState fsState = new BuildFSState(false);
          final ProjectDescriptor pd = runner.load(new MessageHandler() {
            @Override
            public void processMessage(BuildMessage msg) {
              data.addMessage(msg);
            }
          }, dataStorageRoot, fsState);
          data.setProjectDescriptor(pd);
          
          try {
            final File fsStateFile = new File(dataStorageRoot, BuildSession.FS_STATE_FILE);
            final DataInputStream in = new DataInputStream(new BufferedInputStream(new FileInputStream(fsStateFile)));
            try {
              final int version = in.readInt();
              if (version == BuildFSState.VERSION) {
                final long savedOrdinal = in.readLong();
                final boolean hasWorkToDo = in.readBoolean();// must skip "has-work-to-do" flag
                fsState.load(in, pd.getModel(), pd.getBuildRootIndex());
                data.setFsEventOrdinal(savedOrdinal);
                data.setHasHasWorkToDo(hasWorkToDo);
              }
            }
            finally {
              in.close();
            }
          }
          catch (FileNotFoundException ignored) {
          }
          catch (IOException e) {
            LOG.info("Error pre-loading FS state", e);
            fsState.clearAll();
          }

          // preloading target configurations
          final BuildTargetsState targetsState = pd.getTargetsState();
          for (BuildTarget<?> target : pd.getBuildTargetIndex().getAllTargets()) {
            targetsState.getTargetConfiguration(target);
          }

          BuilderRegistry.getInstance();

          LOG.info("Pre-loaded process ready in " + (System.currentTimeMillis() - processStart) + " ms");
        }
        catch (Throwable e) {
          LOG.info("Failed to pre-load project " + projectPathToPreload, e);
          // just failed to preload the project, the situation will be handled later, when real build starts
        }
      }
      else if (projectPathToPreload != null || globalsPathToPreload != null){
        LOG.info("Skipping project pre-loading step: both paths to project configuration files and path to global settings must be specified");
      }
      future.channel().writeAndFlush(CmdlineProtoUtil.toMessage(sessionId, CmdlineProtoUtil.createParamRequest()));
    }
    else {
      printErrorAndExit(host, port, future.cause());
    }
  }

  private static void printErrorAndExit(String host, int port, Throwable reason) {
    System.err.println("Error connecting to " + host + ":" + port + "; reason: " + (reason != null ? reason.getMessage() : "unknown"));
    if (reason != null) {
      reason.printStackTrace(System.err);
    }
    System.err.println("Exiting.");
    System.exit(-1);
  }

  private static class MyMessageHandler extends SimpleChannelInboundHandler<CmdlineRemoteProto.Message> {
    private final UUID mySessionId;
    private volatile BuildSession mySession;

    private MyMessageHandler(UUID sessionId) {
      mySessionId = sessionId;
    }

    @Override
    public void channelRead0(final ChannelHandlerContext context, CmdlineRemoteProto.Message message) throws Exception {
      final CmdlineRemoteProto.Message.Type type = message.getType();
      final Channel channel = context.channel();

      if (type == CmdlineRemoteProto.Message.Type.CONTROLLER_MESSAGE) {
        final CmdlineRemoteProto.Message.ControllerMessage controllerMessage = message.getControllerMessage();
        switch (controllerMessage.getType()) {

          case BUILD_PARAMETERS: {
            if (mySession == null) {
              final CmdlineRemoteProto.Message.ControllerMessage.FSEvent delta = controllerMessage.hasFsEvent()? controllerMessage.getFsEvent() : null;
              final BuildSession session = new BuildSession(mySessionId, channel, controllerMessage.getParamsMessage(), delta, ourPreloadedData);
              mySession = session;
              SharedThreadPool.getInstance().executeOnPooledThread(new Runnable() {
                @Override
                public void run() {
                  //noinspection finally
                  try {
                    try {
                      session.run();
                    }
                    finally {
                      channel.close();
                    }
                  }
                  finally {
                    System.exit(0);
                  }
                }
              });
            }
            else {
              LOG.info("Cannot start another build session because one is already running");
            }
            return;
          }

          case FS_EVENT: {
            final BuildSession session = mySession;
            if (session != null) {
              session.processFSEvent(controllerMessage.getFsEvent());
            }
            return;
          }

          case CONSTANT_SEARCH_RESULT: {
            final BuildSession session = mySession;
            if (session != null) {
              session.processConstantSearchResult(controllerMessage.getConstantSearchResult());
            }
            return;
          }

          case CANCEL_BUILD_COMMAND: {
            final BuildSession session = mySession;
            if (session != null) {
              session.cancel();
            }
            else {
              LOG.info("Build canceled, but no build session is running. Exiting.");
              try {
                final CmdlineRemoteProto.Message.BuilderMessage canceledEvent = CmdlineProtoUtil
                  .createBuildCompletedEvent("build completed", CmdlineRemoteProto.Message.BuilderMessage.BuildEvent.Status.CANCELED);
                channel.writeAndFlush(CmdlineProtoUtil.toMessage(mySessionId, canceledEvent)).await();
                channel.close();
              }
              catch (Throwable e) {
                LOG.info(e);
              }
              Thread.interrupted(); // to clear 'interrupted' flag
              final PreloadedData preloaded = ourPreloadedData;
              final ProjectDescriptor pd = preloaded != null? preloaded.getProjectDescriptor() : null;
              if (pd != null) {
                pd.release();
              }
              System.exit(0);
            }
            return;
          }
        }
      }

      channel.writeAndFlush(
        CmdlineProtoUtil.toMessage(mySessionId, CmdlineProtoUtil.createFailure("Unsupported message type: " + type.name(), null)));
    }

    @Override
    public void channelInactive(ChannelHandlerContext context) throws Exception {
      try {
        super.channelInactive(context);
      }
      finally {
        new Thread("Shutdown thread") {
          @Override
          public void run() {
            //noinspection finally
            try {
              ourEventLoopGroup.shutdownGracefully(0, 15, TimeUnit.SECONDS);
            }
            finally {
              System.exit(0);
            }
          }
        }.start();
      }
    }
  }

  private static void initLoggers() {
    try {
      final String logDir = System.getProperty(GlobalOptions.LOG_DIR_OPTION, null);
      final File configFile = logDir != null? new File(logDir, LOG_CONFIG_FILE_NAME) : new File(LOG_CONFIG_FILE_NAME);
      ensureLogConfigExists(configFile);
      String text = FileUtil.loadFile(configFile);
      final String logFile = logDir != null? new File(logDir, LOG_FILE_NAME).getAbsolutePath() : LOG_FILE_NAME;
      text = StringUtil.replace(text, LOG_FILE_MACRO, StringUtil.replace(logFile, "\\", "\\\\"));
      PropertyConfigurator.configure(new ByteArrayInputStream(text.getBytes("UTF-8")));
    }
    catch (IOException e) {
      System.err.println("Failed to configure logging: ");
      //noinspection UseOfSystemOutOrSystemErr
      e.printStackTrace(System.err);
    }

    Logger.setFactory(MyLoggerFactory.class);
  }

  private static void ensureLogConfigExists(final File logConfig) throws IOException {
    if (!logConfig.exists()) {
      FileUtil.createIfDoesntExist(logConfig);
      @SuppressWarnings("IOResourceOpenedButNotSafelyClosed")
      final InputStream in = BuildMain.class.getResourceAsStream("/" + DEFAULT_LOGGER_CONFIG);
      if (in != null) {
        try {
          final FileOutputStream out = new FileOutputStream(logConfig);
          try {
            FileUtil.copy(in, out);
          }
          finally {
            out.close();
          }
        }
        finally {
          in.close();
        }
      }
    }
  }

  private static class MyLoggerFactory implements Logger.Factory {
    @Override
    public Logger getLoggerInstance(String category) {
      final org.apache.log4j.Logger logger = org.apache.log4j.Logger.getLogger(category);

      return new Logger() {
        @Override
        public boolean isDebugEnabled() {
          return logger.isDebugEnabled();
        }

        @Override
        public void debug(@NonNls String message) {
          logger.debug(message);
        }

        @Override
        public void debug(@Nullable Throwable t) {
          logger.debug("", t);
        }

        @Override
        public void debug(@NonNls String message, @Nullable Throwable t) {
          logger.debug(message, t);
        }

        @Override
        public void error(@NonNls String message, @Nullable Throwable t, @NotNull @NonNls String... details) {
          logger.error(message, t);
        }

        @Override
        public void info(@NonNls String message) {
          logger.info(message);
        }

        @Override
        public void info(@NonNls String message, @Nullable Throwable t) {
          logger.info(message, t);
        }

        @Override
        public void warn(@NonNls String message, @Nullable Throwable t) {
          logger.warn(message, t);
        }

        @Override
        public void setLevel(Level level) {
          logger.setLevel(level);
        }
      };
    }
  }
}


File: jps/standalone-builder/src/org/jetbrains/jps/build/Standalone.java
/*
 * Copyright 2000-2012 JetBrains s.r.o.
 *
 * Licensed under the Apache License, Version 2.0 (the "License");
 * you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at
 *
 * http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 */
package org.jetbrains.jps.build;

import com.intellij.util.ArrayUtil;
import com.intellij.util.ParameterizedRunnable;
import com.sampullara.cli.Args;
import com.sampullara.cli.Argument;
import org.jetbrains.jps.api.BuildType;
import org.jetbrains.jps.api.CanceledStatus;
import org.jetbrains.jps.builders.java.JavaModuleBuildTargetType;
import org.jetbrains.jps.cmdline.BuildRunner;
import org.jetbrains.jps.cmdline.JpsModelLoader;
import org.jetbrains.jps.cmdline.JpsModelLoaderImpl;
import org.jetbrains.jps.cmdline.ProjectDescriptor;
import org.jetbrains.jps.incremental.MessageHandler;
import org.jetbrains.jps.incremental.Utils;
import org.jetbrains.jps.incremental.artifacts.ArtifactBuildTargetType;
import org.jetbrains.jps.incremental.fs.BuildFSState;
import org.jetbrains.jps.incremental.messages.BuildMessage;
import org.jetbrains.jps.model.JpsModel;

import java.io.File;
import java.util.*;

import static org.jetbrains.jps.api.CmdlineRemoteProto.Message.ControllerMessage.ParametersMessage.TargetTypeBuildScope;

/**
 * @author nik
 */
@SuppressWarnings({"UseOfSystemOutOrSystemErr", "CallToPrintStackTrace"})
public class Standalone {
  @Argument(value = "config", prefix = "--", description = "Path to directory containing global options (idea.config.path)")
  public String configPath;

  @Argument(value = "script", prefix = "--", description = "Path to Groovy script which will be used to initialize global options")
  public String initializationScriptPath;

  @Argument(value = "cache-dir", prefix = "--", description = "Path to directory to store build caches")
  public String cacheDirPath;

  @Argument(value = "modules", prefix = "--", delimiter = ",", description = "Comma-separated list of modules to compile")
  public String[] modules = ArrayUtil.EMPTY_STRING_ARRAY;

  @Argument(value = "all-modules", prefix = "--", description = "Compile all modules")
  public boolean allModules;

  @Argument(value = "artifacts", prefix = "--", delimiter = ",", description = "Comma-separated list of artifacts to build")
  public String[] artifacts = ArrayUtil.EMPTY_STRING_ARRAY;

  @Argument(value = "all-artifacts", prefix = "--", description = "Build all artifacts")
  public boolean allArtifacts;

  @Argument(value = "i", description = "Build incrementally")
  public boolean incremental;

  public static void main(String[] args) {
    Standalone instance = new Standalone();
    List<String> projectPaths;
    try {
      projectPaths = Args.parse(instance, args);
    }
    catch (Exception e) {
      printUsageAndExit();
      return;
    }

    if (projectPaths.isEmpty()) {
      System.out.println("Path to project is not specified");
      printUsageAndExit();
    }
    if (projectPaths.size() > 1) {
      System.out.println("Only one project can be specified");
      printUsageAndExit();
    }

    instance.loadAndRunBuild(projectPaths.get(0));
    System.exit(0);
  }

  private static void printUsageAndExit() {
    Args.usage(System.err, new Standalone());
    System.exit(0);
  }

  public void loadAndRunBuild(final String projectPath) {
    String globalOptionsPath = null;
    if (configPath != null) {
      File optionsDir = new File(configPath, "options");
      if (!optionsDir.isDirectory()) {
        System.err.println("'" + configPath + "' is not valid config path: " + optionsDir.getAbsolutePath() + " not found");
        return;
      }
      globalOptionsPath = optionsDir.getAbsolutePath();
    }

    ParameterizedRunnable<JpsModel> initializer = null;
    String scriptPath = initializationScriptPath;
    if (scriptPath != null) {
      File scriptFile = new File(scriptPath);
      if (!scriptFile.isFile()) {
        System.err.println("Script '" + scriptPath + "' not found");
        return;
      }
      initializer = new GroovyModelInitializer(scriptFile);
    }

    if (modules.length == 0 && artifacts.length == 0 && !allModules && !allArtifacts) {
      System.err.println("Nothing to compile: at least one of --modules, --artifacts, --all-modules or --all-artifacts parameters must be specified");
      return;
    }

    JpsModelLoaderImpl loader = new JpsModelLoaderImpl(projectPath, globalOptionsPath, initializer);
    Set<String> modulesSet = new HashSet<String>(Arrays.asList(modules));
    List<String> artifactsList = Arrays.asList(artifacts);
    File dataStorageRoot;
    if (cacheDirPath != null) {
      dataStorageRoot = new File(cacheDirPath);
    }
    else {
      dataStorageRoot = Utils.getDataStorageRoot(projectPath);
    }
    if (dataStorageRoot == null) {
      System.err.println("Error: Cannot determine build data storage root for project " + projectPath);
      return;
    }

    long start = System.currentTimeMillis();
    try {
      runBuild(loader, dataStorageRoot, !incremental, modulesSet, allModules, artifactsList, allArtifacts, true, new ConsoleMessageHandler());
    }
    catch (Throwable t) {
      System.err.println("Internal error: " + t.getMessage());
      t.printStackTrace();
    }
    System.out.println("Build finished in " + Utils.formatDuration(System.currentTimeMillis() - start));
  }

  @Deprecated
  public static void runBuild(JpsModelLoader loader, final File dataStorageRoot, boolean forceBuild, Set<String> modulesSet,
                              List<String> artifactsList, final boolean includeTests, final MessageHandler messageHandler) throws Exception {
    runBuild(loader, dataStorageRoot, forceBuild, modulesSet, modulesSet.isEmpty(), artifactsList, includeTests, messageHandler);
  }

  public static void runBuild(JpsModelLoader loader, final File dataStorageRoot, boolean forceBuild, Set<String> modulesSet,
                              final boolean allModules, List<String> artifactsList, final boolean includeTests,
                              final MessageHandler messageHandler) throws Exception {
    runBuild(loader, dataStorageRoot, forceBuild, modulesSet, allModules, artifactsList, false, includeTests, messageHandler);
  }

  public static void runBuild(JpsModelLoader loader, final File dataStorageRoot, boolean forceBuild, Set<String> modulesSet,
                              final boolean allModules, List<String> artifactsList, boolean allArtifacts, final boolean includeTests,
                              final MessageHandler messageHandler) throws Exception {
    List<TargetTypeBuildScope> scopes = new ArrayList<TargetTypeBuildScope>();
    for (JavaModuleBuildTargetType type : JavaModuleBuildTargetType.ALL_TYPES) {
      if (includeTests || !type.isTests()) {
        TargetTypeBuildScope.Builder builder = TargetTypeBuildScope.newBuilder().setTypeId(type.getTypeId()).setForceBuild(forceBuild);
        if (allModules) {
          scopes.add(builder.setAllTargets(true).build());
        }
        else if (!modulesSet.isEmpty()) {
          scopes.add(builder.addAllTargetId(modulesSet).build());
        }
      }
    }

    TargetTypeBuildScope.Builder builder = TargetTypeBuildScope.newBuilder()
      .setTypeId(ArtifactBuildTargetType.INSTANCE.getTypeId())
      .setForceBuild(forceBuild);

    if (allArtifacts) {
      scopes.add(builder.setAllTargets(true).build());
    }
    else if (!artifactsList.isEmpty()) {
      scopes.add(builder.addAllTargetId(artifactsList).build());
    }

    runBuild(loader, dataStorageRoot, messageHandler, scopes, true);
  }

  public static void runBuild(JpsModelLoader loader, File dataStorageRoot, MessageHandler messageHandler, List<TargetTypeBuildScope> scopes,
                              boolean includeDependenciesToScope) throws Exception {
    final BuildRunner buildRunner = new BuildRunner(loader);
    ProjectDescriptor descriptor = buildRunner.load(messageHandler, dataStorageRoot, new BuildFSState(true));
    try {
      buildRunner.runBuild(descriptor, CanceledStatus.NULL, null, messageHandler, BuildType.BUILD, scopes, includeDependenciesToScope);
    }
    finally {
      descriptor.release();
    }
  }

  private static class ConsoleMessageHandler implements MessageHandler {
    @Override
    public void processMessage(BuildMessage msg) {
      String messageText = msg.getMessageText();
      if (messageText.isEmpty()) return;
      if (msg.getKind() == BuildMessage.Kind.ERROR) {
        System.err.println("Error: " + messageText);
      }
      else if (msg.getKind() != BuildMessage.Kind.PROGRESS || !messageText.startsWith("Compiled") && !messageText.startsWith("Copying")) {
        System.out.println(messageText);
      }
    }
  }
}
