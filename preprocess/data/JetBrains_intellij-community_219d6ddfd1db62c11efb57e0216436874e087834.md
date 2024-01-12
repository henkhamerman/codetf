Refactoring Types: ['Extract Superclass', 'Extract Method']
moteServer/agent/util/CloudAgentLoggingHandler.java
/*
 * Copyright 2000-2013 JetBrains s.r.o.
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
package com.intellij.remoteServer.agent.util;

import com.intellij.remoteServer.agent.util.log.LogListener;

import java.io.OutputStream;

/**
 * @author michael.golubev
 */
public interface CloudAgentLoggingHandler {

  void println(String message);

  LogListener getOrCreateLogListener(String pipeName);

  LogListener getOrCreateEmptyLogListener(String pipeName);

  LogListener createConsole(String pipeName, OutputStream consoleInput);
}


File: platform/remote-servers/agent-rt/src/com/intellij/remoteServer/agent/util/log/LogAgentManager.java
/*
 * Copyright 2000-2013 JetBrains s.r.o.
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
package com.intellij.remoteServer.agent.util.log;

import java.util.ArrayList;
import java.util.HashMap;
import java.util.List;
import java.util.Map;

/**
 * @author michael.golubev
 */
public class LogAgentManager {

  private Map<String, List<LogPipe>> myDeploymentName2ActiveLogPipes = new HashMap<String, List<LogPipe>>();

  public void startListeningLog(String deploymentName, LogPipeProvider provider) {
    stopListeningLog(deploymentName);
    doStartListeningLog(deploymentName, provider);
  }

  public void startOrContinueListeningLog(String deploymentName, LogPipeProvider provider) {
    if (!myDeploymentName2ActiveLogPipes.containsKey(deploymentName)) {
      doStartListeningLog(deploymentName, provider);
    }
  }

  private void doStartListeningLog(String deploymentName, LogPipeProvider provider) {
    ArrayList<LogPipe> pipes = new ArrayList<LogPipe>(provider.createLogPipes(deploymentName));
    myDeploymentName2ActiveLogPipes.put(deploymentName, pipes);
    for (LogPipe pipe : pipes) {
      pipe.open();
    }
  }

  public void stopListeningAllLogs() {
    for (String deploymentName : new ArrayList<String>(myDeploymentName2ActiveLogPipes.keySet())) {
      stopListeningLog(deploymentName);
    }
  }

  public void stopListeningLog(String deploymentName) {
    List<LogPipe> pipes = myDeploymentName2ActiveLogPipes.remove(deploymentName);
    if (pipes != null) {
      for (LogPipe pipe : pipes) {
        pipe.close();
      }
    }
  }
}


File: platform/remote-servers/agent-rt/src/com/intellij/remoteServer/agent/util/log/LogPipe.java
/*
 * Copyright 2000-2015 JetBrains s.r.o.
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
package com.intellij.remoteServer.agent.util.log;

import com.intellij.remoteServer.agent.util.CloudAgentLogger;
import com.intellij.remoteServer.agent.util.CloudAgentLoggingHandler;

import java.io.BufferedReader;
import java.io.IOException;
import java.io.InputStream;
import java.io.InputStreamReader;

/**
 * @author michael.golubev
 */
public abstract class LogPipe {

  private final String myDeploymentName;
  private final String myLogPipeName;
  private final CloudAgentLogger myLogger;
  private final CloudAgentLoggingHandler myLoggingHandler;

  private boolean myClosed;

  private int myTotalLines;
  private int myLines2Skip;

  public LogPipe(String deploymentName, String logPipeName, CloudAgentLogger logger, CloudAgentLoggingHandler loggingHandler) {
    myDeploymentName = deploymentName;
    myLogPipeName = logPipeName;
    myLogger = logger;
    myLoggingHandler = loggingHandler;
    myClosed = false;
  }

  public void open() {
    InputStream inputStream = createInputStream(myDeploymentName);
    if (inputStream == null) {
      return;
    }

    InputStreamReader streamReader = new InputStreamReader(inputStream);
    final BufferedReader bufferedReader = new BufferedReader(streamReader);

    myTotalLines = 0;
    myLines2Skip = 0;

    new Thread("log pipe") {

      @Override
      public void run() {
        try {
          while (true) {
            String line = bufferedReader.readLine();
            if (myClosed) {
              myLogger.debug("log pipe closed for: " + myDeploymentName);
              break;
            }
            if (line == null) {
              myLogger.debug("end of log stream for: " + myDeploymentName);
              break;
            }

            if (myLines2Skip == 0) {
              getLogListener().lineLogged(line);
              myTotalLines++;
            }
            else {
              myLines2Skip--;
            }
          }
        }
        catch (IOException e) {
          myLoggingHandler.println(e.toString());
        }
      }
    }.start();
  }

  public void close() {
    myClosed = true;
  }

  protected final void cutTail() {
    myLines2Skip = myTotalLines;
  }

  protected final boolean isClosed() {
    return myClosed;
  }

  protected abstract InputStream createInputStream(String deploymentName);

  protected LogListener getLogListener() {
    return myLoggingHandler.getOrCreateLogListener(myLogPipeName);
  }
}


File: platform/remote-servers/agent-rt/src/com/intellij/remoteServer/agent/util/log/LogPipeProvider.java
/*
 * Copyright 2000-2013 JetBrains s.r.o.
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
package com.intellij.remoteServer.agent.util.log;

import java.util.List;

/**
 * @author michael.golubev
 */
public interface LogPipeProvider {

  List<? extends LogPipe> createLogPipes(String deploymentName);
}


File: platform/remote-servers/api/src/com/intellij/remoteServer/runtime/deployment/DeploymentLogManager.java
/*
 * Copyright 2000-2013 JetBrains s.r.o.
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
package com.intellij.remoteServer.runtime.deployment;

import com.intellij.remoteServer.runtime.log.LoggingHandler;
import org.jetbrains.annotations.NotNull;

/**
 * @author nik
 */
public interface DeploymentLogManager {
  @NotNull
  LoggingHandler getMainLoggingHandler();

  @NotNull
  LoggingHandler addAdditionalLog(@NotNull String presentableName);
}


File: platform/remote-servers/impl/src/com/intellij/remoteServer/impl/runtime/log/DeploymentLogManagerImpl.java
/*
 * Copyright 2000-2013 JetBrains s.r.o.
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
package com.intellij.remoteServer.impl.runtime.log;

import com.intellij.openapi.Disposable;
import com.intellij.openapi.project.Project;
import com.intellij.openapi.util.Disposer;
import com.intellij.remoteServer.runtime.deployment.DeploymentLogManager;
import com.intellij.remoteServer.runtime.log.LoggingHandler;
import org.jetbrains.annotations.NotNull;

import java.util.HashMap;
import java.util.Map;
import java.util.concurrent.atomic.AtomicBoolean;

/**
 * @author nik
 */
public class DeploymentLogManagerImpl implements DeploymentLogManager {
  private final LoggingHandlerImpl myMainLoggingHandler;
  private final Project myProject;
  private final Map<String, LoggingHandlerImpl> myAdditionalLoggingHandlers = new HashMap<String, LoggingHandlerImpl>();
  private final Runnable myChangeListener;

  private final AtomicBoolean myLogsDisposed = new AtomicBoolean(false);
  private final Disposable myLogsDisposable;
  private boolean myMainHandlerVisible = false;

  public DeploymentLogManagerImpl(@NotNull Project project, @NotNull Runnable changeListener) {
    myProject = project;
    myChangeListener = changeListener;
    myMainLoggingHandler = new LoggingHandlerImpl(project);
    myLogsDisposable = Disposer.newDisposable();
    Disposer.register(myLogsDisposable, myMainLoggingHandler);
    Disposer.register(project, new Disposable() {
      @Override
      public void dispose() {
        disposeLogs();
      }
    });
  }

  public DeploymentLogManagerImpl withMainHandlerVisible(boolean mainHandlerVisible) {
    myMainHandlerVisible = mainHandlerVisible;
    return this;
  }

  public boolean isMainHandlerVisible() {
    return myMainHandlerVisible;
  }

  @NotNull
  @Override
  public LoggingHandlerImpl getMainLoggingHandler() {
    return myMainLoggingHandler;
  }

  @NotNull
  @Override
  public LoggingHandler addAdditionalLog(@NotNull String presentableName) {
    LoggingHandlerImpl handler = new LoggingHandlerImpl(myProject);
    Disposer.register(myLogsDisposable, handler);
    synchronized (myAdditionalLoggingHandlers) {
      myAdditionalLoggingHandlers.put(presentableName, handler);
    }
    myChangeListener.run();
    return handler;
  }

  @NotNull
  public Map<String, LoggingHandlerImpl> getAdditionalLoggingHandlers() {
    HashMap<String, LoggingHandlerImpl> result;
    synchronized (myAdditionalLoggingHandlers) {
      result = new HashMap<String, LoggingHandlerImpl>(myAdditionalLoggingHandlers);
    }
    return result;
  }

  public void disposeLogs() {
    if (!myLogsDisposed.getAndSet(true)) {
      Disposer.dispose(myLogsDisposable);
    }
  }
}


File: platform/remote-servers/impl/src/com/intellij/remoteServer/impl/runtime/log/LoggingHandlerImpl.java
package com.intellij.remoteServer.impl.runtime.log;

import com.intellij.execution.filters.BrowserHyperlinkInfo;
import com.intellij.execution.filters.HyperlinkInfo;
import com.intellij.execution.filters.TextConsoleBuilderFactory;
import com.intellij.execution.process.ProcessHandler;
import com.intellij.execution.ui.ConsoleView;
import com.intellij.execution.ui.ConsoleViewContentType;
import com.intellij.openapi.Disposable;
import com.intellij.openapi.project.Project;
import com.intellij.openapi.util.Disposer;
import com.intellij.remoteServer.runtime.log.LoggingHandler;
import org.jetbrains.annotations.NotNull;

/**
 * @author nik
 */
public class LoggingHandlerImpl implements LoggingHandler, Disposable {
  private final ConsoleView myConsole;

  public LoggingHandlerImpl(@NotNull Project project) {
    myConsole = TextConsoleBuilderFactory.getInstance().createBuilder(project).getConsole();
    Disposer.register(this, myConsole);
  }

  @NotNull
  public ConsoleView getConsole() {
    return myConsole;
  }

  @Override
  public void print(@NotNull String s) {
    myConsole.print(s, ConsoleViewContentType.NORMAL_OUTPUT);
  }

  @Override
  public void printHyperlink(@NotNull String url) {
    printHyperlink(url, new BrowserHyperlinkInfo(url));
  }

  @Override
  public void printHyperlink(@NotNull String text, HyperlinkInfo info) {
    myConsole.printHyperlink(text, info);
  }

  public void printlnSystemMessage(@NotNull String s) {
    myConsole.print(s + "\n", ConsoleViewContentType.SYSTEM_OUTPUT);
  }

  @Override
  public void attachToProcess(@NotNull ProcessHandler handler) {
    myConsole.attachToProcess(handler);
  }

  @Override
  public void clear() {
    myConsole.clear();
  }

  @Override
  public void dispose() {

  }
}


File: platform/remote-servers/impl/src/com/intellij/remoteServer/impl/runtime/ui/ServersToolWindowContent.java
package com.intellij.remoteServer.impl.runtime.ui;

import com.intellij.ide.DataManager;
import com.intellij.ide.actions.ContextHelpAction;
import com.intellij.ide.util.treeView.AbstractTreeNode;
import com.intellij.ide.util.treeView.NodeDescriptor;
import com.intellij.ide.util.treeView.NodeRenderer;
import com.intellij.ide.util.treeView.TreeVisitor;
import com.intellij.openapi.Disposable;
import com.intellij.openapi.actionSystem.*;
import com.intellij.openapi.application.ModalityState;
import com.intellij.openapi.project.Project;
import com.intellij.openapi.ui.Splitter;
import com.intellij.openapi.util.Comparing;
import com.intellij.openapi.util.Disposer;
import com.intellij.remoteServer.configuration.RemoteServer;
import com.intellij.remoteServer.impl.runtime.log.LoggingHandlerImpl;
import com.intellij.remoteServer.impl.runtime.ui.tree.ServersTreeStructure;
import com.intellij.remoteServer.impl.runtime.ui.tree.TreeBuilderBase;
import com.intellij.remoteServer.runtime.ConnectionStatus;
import com.intellij.remoteServer.runtime.ServerConnection;
import com.intellij.remoteServer.runtime.ServerConnectionListener;
import com.intellij.remoteServer.runtime.ServerConnectionManager;
import com.intellij.ui.*;
import com.intellij.ui.components.panels.Wrapper;
import com.intellij.ui.treeStructure.Tree;
import com.intellij.util.Alarm;
import com.intellij.util.ui.UIUtil;
import org.jetbrains.annotations.NonNls;
import org.jetbrains.annotations.NotNull;

import javax.swing.*;
import javax.swing.event.TreeSelectionEvent;
import javax.swing.event.TreeSelectionListener;
import javax.swing.tree.DefaultMutableTreeNode;
import javax.swing.tree.DefaultTreeModel;
import java.awt.*;
import java.awt.event.MouseEvent;
import java.util.HashMap;
import java.util.Map;
import java.util.Set;

/**
 * @author michael.golubev
 */
public class ServersToolWindowContent extends JPanel implements Disposable {
  public static final DataKey<ServersToolWindowContent> KEY = DataKey.create("serversToolWindowContent");
  @NonNls private static final String PLACE_TOOLBAR = "ServersToolWindowContent#Toolbar";
  @NonNls private static final String SERVERS_TOOL_WINDOW_TOOLBAR = "RemoteServersViewToolbar";
  @NonNls private static final String SERVERS_TOOL_WINDOW_POPUP = "RemoteServersViewPopup";

  @NonNls
  private static final String HELP_ID = "Application_Servers_tool_window";
  private static final String MESSAGE_CARD = "message";
  private static final String EMPTY_SELECTION_MESSAGE = "Select a server or deployment in the tree to view details";

  private static final int POLL_DEPLOYMENTS_DELAY = 2000;

  private final Tree myTree;
  private final CardLayout myPropertiesPanelLayout;
  private final JPanel myPropertiesPanel;
  private final JLabel myMessageLabel;
  private final Map<String, JComponent> myLogComponents = new HashMap<String, JComponent>();

  private final DefaultTreeModel myTreeModel;
  private TreeBuilderBase myBuilder;
  private AbstractTreeNode<?> myLastSelection;

  private final Project myProject;

  public ServersToolWindowContent(@NotNull Project project) {
    super(new BorderLayout());
    myProject = project;

    myTreeModel = new DefaultTreeModel(new DefaultMutableTreeNode());
    myTree = new Tree(myTreeModel);
    myTree.setRootVisible(false);

    myTree.setShowsRootHandles(true);
    myTree.setCellRenderer(new NodeRenderer());
    myTree.setLineStyleAngled();

    getMainPanel().add(createToolbar(), BorderLayout.WEST);
    Splitter splitter = new Splitter(false, 0.3f);
    splitter.setFirstComponent(ScrollPaneFactory.createScrollPane(myTree, SideBorder.LEFT));
    myPropertiesPanelLayout = new CardLayout();
    myPropertiesPanel = new JPanel(myPropertiesPanelLayout);
    myMessageLabel = new JLabel(EMPTY_SELECTION_MESSAGE, SwingConstants.CENTER);
    myPropertiesPanel.add(MESSAGE_CARD, new Wrapper(myMessageLabel));
    splitter.setSecondComponent(myPropertiesPanel);
    getMainPanel().add(splitter, BorderLayout.CENTER);

    setupBuilder(project);

    for (RemoteServersViewContributor contributor : RemoteServersViewContributor.EP_NAME.getExtensions()) {
      contributor.setupTree(myProject, myTree, myBuilder);
    }

    myTree.addTreeSelectionListener(new TreeSelectionListener() {
      @Override
      public void valueChanged(TreeSelectionEvent e) {
        onSelectionChanged();
      }
    });
    new DoubleClickListener() {
      @Override
      protected boolean onDoubleClick(MouseEvent event) {
        AnAction connectAction = ActionManager.getInstance().getAction("RemoteServers.ConnectServer");
        AnActionEvent actionEvent = AnActionEvent.createFromInputEvent(connectAction, event, ActionPlaces.UNKNOWN);
        connectAction.actionPerformed(actionEvent);
        return true;
      }
    }.installOn(myTree);

    DefaultActionGroup popupActionGroup = new DefaultActionGroup();
    popupActionGroup.add(ActionManager.getInstance().getAction(SERVERS_TOOL_WINDOW_TOOLBAR));
    popupActionGroup.add(ActionManager.getInstance().getAction(SERVERS_TOOL_WINDOW_POPUP));
    PopupHandler.installPopupHandler(myTree, popupActionGroup, ActionPlaces.UNKNOWN, ActionManager.getInstance());

    new TreeSpeedSearch(myTree, TreeSpeedSearch.NODE_DESCRIPTOR_TOSTRING, true);
  }

  private void onSelectionChanged() {
    Set<AbstractTreeNode> nodes = myBuilder.getSelectedElements(AbstractTreeNode.class);
    if (nodes.size() != 1) {
      showMessageLabel(EMPTY_SELECTION_MESSAGE);
      myLastSelection = null;
      return;
    }

    AbstractTreeNode<?> node = nodes.iterator().next();
    if (Comparing.equal(node, myLastSelection)) {
      return;
    }

    myLastSelection = node;
    if (node instanceof ServersTreeStructure.LogProvidingNode) {
      ServersTreeStructure.LogProvidingNode logNode = (ServersTreeStructure.LogProvidingNode)node;
      LoggingHandlerImpl loggingHandler = logNode.getLoggingHandler();
      if (loggingHandler != null) {
        String cardName = logNode.getLogId();
        JComponent oldComponent = myLogComponents.get(cardName);
        JComponent logComponent = loggingHandler.getConsole().getComponent();
        if (!logComponent.equals(oldComponent)) {
          myLogComponents.put(cardName, logComponent);
          if (oldComponent != null) {
            myPropertiesPanel.remove(oldComponent);
          }
          myPropertiesPanel.add(cardName, logComponent);
        }
        myPropertiesPanelLayout.show(myPropertiesPanel, cardName);
      }
      else {
        showMessageLabel("");
      }
    }
    else if (node instanceof ServersTreeStructure.RemoteServerNode) {
      updateServerDetails((ServersTreeStructure.RemoteServerNode)node);
    }
    else {
      showMessageLabel("");
    }
  }

  private void updateServerDetails(ServersTreeStructure.RemoteServerNode node) {
    RemoteServer<?> server = ((ServersTreeStructure.RemoteServerNode)node).getValue();
    ServerConnection connection = ServerConnectionManager.getInstance().getConnection(server);
    if (connection == null) {
      showMessageLabel("Double-click on the server node to connect");
    }
    else {
      showMessageLabel(connection.getStatusText());
    }
  }

  private void showMessageLabel(final String text) {
    myMessageLabel.setText(UIUtil.toHtml(text));
    myPropertiesPanelLayout.show(myPropertiesPanel, MESSAGE_CARD);
  }

  private void setupBuilder(final @NotNull Project project) {
    ServersTreeStructure structure = new ServersTreeStructure(project);
    myBuilder = new TreeBuilderBase(myTree, structure, myTreeModel) {
      @Override
      protected boolean isAutoExpandNode(NodeDescriptor nodeDescriptor) {
        return nodeDescriptor instanceof ServersTreeStructure.RemoteServerNode || nodeDescriptor instanceof ServersTreeStructure.DeploymentNodeImpl;
      }
    };
    Disposer.register(this, myBuilder);

    project.getMessageBus().connect().subscribe(ServerConnectionListener.TOPIC, new ServerConnectionListener() {
      @Override
      public void onConnectionCreated(@NotNull ServerConnection<?> connection) {
        getBuilder().queueUpdate();
      }

      @Override
      public void onConnectionStatusChanged(@NotNull ServerConnection<?> connection) {
        getBuilder().queueUpdate();
        updateSelectedServerDetails();
        if (connection.getStatus() == ConnectionStatus.CONNECTED) {
          pollDeployments(connection);
        }
      }

      @Override
      public void onDeploymentsChanged(@NotNull ServerConnection<?> connection) {
        getBuilder().queueUpdate();
        updateSelectedServerDetails();
      }
    });
  }

  private void updateSelectedServerDetails() {
    if (myLastSelection instanceof ServersTreeStructure.RemoteServerNode) {
      updateServerDetails((ServersTreeStructure.RemoteServerNode)myLastSelection);
    }
  }

  private static void pollDeployments(final ServerConnection connection) {
    connection.computeDeployments(new Runnable() {

      @Override
      public void run() {
        new Alarm().addRequest(new Runnable() {

          @Override
          public void run() {
            if (connection == ServerConnectionManager.getInstance().getConnection(connection.getServer())) {
              pollDeployments(connection);
            }
          }
        }, POLL_DEPLOYMENTS_DELAY, ModalityState.any());
      }
    });
  }

  private JComponent createToolbar() {
    DefaultActionGroup group = new DefaultActionGroup();
    group.add(ActionManager.getInstance().getAction(SERVERS_TOOL_WINDOW_TOOLBAR));
    group.add(new Separator());
    group.add(new ContextHelpAction(HELP_ID));

    ActionToolbar actionToolBar = ActionManager.getInstance().createActionToolbar(PLACE_TOOLBAR, group, false);


    myTree.putClientProperty(DataManager.CLIENT_PROPERTY_DATA_PROVIDER, new DataProvider() {

      @Override
      public Object getData(@NonNls String dataId) {
        if (KEY.getName().equals(dataId)) {
          return ServersToolWindowContent.this;
        }
        for (RemoteServersViewContributor contributor : RemoteServersViewContributor.EP_NAME.getExtensions()) {
          Object data = contributor.getData(dataId, ServersToolWindowContent.this);
          if (data != null) {
            return data;
          }
        }
        return null;
      }
    });
    actionToolBar.setTargetComponent(myTree);
    return actionToolBar.getComponent();
  }

  public JPanel getMainPanel() {
    return this;
  }

  @Override
  public void dispose() {
  }

  public TreeBuilderBase getBuilder() {
    return myBuilder;
  }

  @NotNull
  public Project getProject() {
    return myProject;
  }

  public void select(@NotNull final ServerConnection<?> connection) {
    myBuilder.select(ServersTreeStructure.RemoteServerNode.class, new TreeVisitor<ServersTreeStructure.RemoteServerNode>() {
      @Override
      public boolean visit(@NotNull ServersTreeStructure.RemoteServerNode node) {
        return isServerNodeMatch(node, connection);
      }
    }, null, false);
  }

  public void select(@NotNull final ServerConnection<?> connection, @NotNull final String deploymentName) {
    myBuilder.getUi().queueUpdate(connection).doWhenDone(new Runnable() {
      @Override
      public void run() {
        myBuilder.select(ServersTreeStructure.DeploymentNodeImpl.class, new TreeVisitor<ServersTreeStructure.DeploymentNodeImpl>() {
          @Override
          public boolean visit(@NotNull ServersTreeStructure.DeploymentNodeImpl node) {
            return isDeploymentNodeMatch(node, connection, deploymentName);
          }
        }, null, false);
      }
    });
  }

  public void select(@NotNull final ServerConnection<?> connection,
                     @NotNull final String deploymentName,
                     @NotNull final String logName) {
    myBuilder.getUi().queueUpdate(connection).doWhenDone(new Runnable() {
      @Override
      public void run() {
        myBuilder.select(ServersTreeStructure.DeploymentLogNode.class, new TreeVisitor<ServersTreeStructure.DeploymentLogNode>() {
          @Override
          public boolean visit(@NotNull ServersTreeStructure.DeploymentLogNode node) {
            AbstractTreeNode parent = node.getParent();
            return parent instanceof ServersTreeStructure.DeploymentNodeImpl
                   && isDeploymentNodeMatch((ServersTreeStructure.DeploymentNodeImpl)parent, connection, deploymentName)
                   && node.getValue().second.equals(logName);
          }
        }, null, false);
      }
    });
  }

  private static boolean isServerNodeMatch(@NotNull final ServersTreeStructure.RemoteServerNode node,
                                           @NotNull final ServerConnection<?> connection) {
    return node.getValue().equals(connection.getServer());
  }

  private static boolean isDeploymentNodeMatch(@NotNull ServersTreeStructure.DeploymentNodeImpl node,
                                               @NotNull final ServerConnection<?> connection, @NotNull final String deploymentName) {
    AbstractTreeNode parent = node.getParent();
    return parent instanceof ServersTreeStructure.RemoteServerNode &&
           isServerNodeMatch((ServersTreeStructure.RemoteServerNode)parent, connection)
           && node.getValue().getName().equals(deploymentName);
  }
}


File: platform/remote-servers/impl/src/com/intellij/remoteServer/impl/runtime/ui/tree/ServersTreeStructure.java
package com.intellij.remoteServer.impl.runtime.ui.tree;

import com.intellij.execution.Executor;
import com.intellij.execution.ProgramRunnerUtil;
import com.intellij.execution.RunnerAndConfigurationSettings;
import com.intellij.execution.executors.DefaultDebugExecutor;
import com.intellij.execution.executors.DefaultRunExecutor;
import com.intellij.execution.impl.RunDialog;
import com.intellij.execution.runners.ExecutionEnvironment;
import com.intellij.icons.AllIcons;
import com.intellij.ide.projectView.PresentationData;
import com.intellij.ide.projectView.TreeStructureProvider;
import com.intellij.ide.util.treeView.AbstractTreeNode;
import com.intellij.ide.util.treeView.AbstractTreeStructureBase;
import com.intellij.openapi.actionSystem.AnActionEvent;
import com.intellij.openapi.options.ShowSettingsUtil;
import com.intellij.openapi.project.Project;
import com.intellij.openapi.ui.popup.JBPopupFactory;
import com.intellij.openapi.ui.popup.ListPopup;
import com.intellij.openapi.ui.popup.PopupStep;
import com.intellij.openapi.ui.popup.util.BaseListPopupStep;
import com.intellij.openapi.util.Condition;
import com.intellij.openapi.util.Pair;
import com.intellij.openapi.util.text.StringUtil;
import com.intellij.remoteServer.ServerType;
import com.intellij.remoteServer.configuration.RemoteServer;
import com.intellij.remoteServer.configuration.RemoteServersManager;
import com.intellij.remoteServer.configuration.ServerConfiguration;
import com.intellij.remoteServer.configuration.deployment.DeploymentConfigurationManager;
import com.intellij.remoteServer.impl.configuration.SingleRemoteServerConfigurable;
import com.intellij.remoteServer.impl.configuration.deployment.DeployToServerRunConfiguration;
import com.intellij.remoteServer.impl.runtime.deployment.DeploymentTaskImpl;
import com.intellij.remoteServer.impl.runtime.log.DeploymentLogManagerImpl;
import com.intellij.remoteServer.impl.runtime.log.LoggingHandlerImpl;
import com.intellij.remoteServer.impl.runtime.ui.RemoteServersViewContributor;
import com.intellij.remoteServer.runtime.ConnectionStatus;
import com.intellij.remoteServer.runtime.Deployment;
import com.intellij.remoteServer.runtime.ServerConnection;
import com.intellij.remoteServer.runtime.ServerConnectionManager;
import com.intellij.remoteServer.runtime.deployment.DeploymentRuntime;
import com.intellij.remoteServer.runtime.deployment.DeploymentStatus;
import com.intellij.remoteServer.runtime.deployment.DeploymentTask;
import com.intellij.ui.LayeredIcon;
import com.intellij.ui.awt.RelativePoint;
import com.intellij.util.containers.ContainerUtil;
import icons.RemoteServersIcons;
import org.jetbrains.annotations.NotNull;
import org.jetbrains.annotations.Nullable;

import javax.swing.*;
import java.awt.event.MouseEvent;
import java.util.*;

/**
 * @author michael.golubev
 */
public class ServersTreeStructure extends AbstractTreeStructureBase {
  // 1st level: servers (RunnerAndConfigurationSettings (has CommonStrategy (extends RunConfiguration)) or RemoteServer)
  // 2nd level: deployments (DeploymentModel or Deployment)

  private final ServersTreeRootNode myRootElement;
  private final Project myProject;

  public ServersTreeStructure(@NotNull Project project) {
    super(project);
    myProject = project;
    myRootElement = new ServersTreeRootNode();
  }

  public static Icon getServerNodeIcon(@NotNull Icon itemIcon, @Nullable Icon statusIcon) {
    if (statusIcon == null) {
      return itemIcon;
    }

    LayeredIcon icon = new LayeredIcon(2);
    icon.setIcon(itemIcon, 0);
    icon.setIcon(statusIcon, 1, itemIcon.getIconWidth() - statusIcon.getIconWidth(), itemIcon.getIconHeight() - statusIcon.getIconHeight());
    return icon;
  }

  @Override
  public List<TreeStructureProvider> getProviders() {
    return Collections.emptyList();
  }

  @NotNull
  Project doGetProject() {
    return myProject;
  }

  @Override
  public Object getRootElement() {
    return myRootElement;
  }

  @Override
  public void commit() {
  }

  @Override
  public boolean hasSomethingToCommit() {
    return false;
  }

  public interface LogProvidingNode {
    @Nullable
    LoggingHandlerImpl getLoggingHandler();

    @NotNull String getLogId();
  }

  public class ServersTreeRootNode extends AbstractTreeNode<Object> {
    public ServersTreeRootNode() {
      super(doGetProject(), new Object());
    }

    @NotNull
    @Override
    public Collection<? extends AbstractTreeNode> getChildren() {
      List<AbstractTreeNode<?>> result = new ArrayList<AbstractTreeNode<?>>();
      for (RemoteServersViewContributor contributor : RemoteServersViewContributor.EP_NAME.getExtensions()) {
        result.addAll(contributor.createServerNodes(doGetProject()));
      }
      for (RemoteServer<?> server : RemoteServersManager.getInstance().getServers()) {
        result.add(new RemoteServerNode(server));
      }
      return result;
    }

    @Override
    protected void update(PresentationData presentation) {
    }
  }

  public class RemoteServerNode extends AbstractTreeNode<RemoteServer<?>> implements ServerNode {
    public RemoteServerNode(RemoteServer<?> server) {
      super(doGetProject(), server);
    }

    @NotNull
    @Override
    public Collection<? extends AbstractTreeNode> getChildren() {
      ServerConnection<?> connection = getConnection();
      if (connection == null) {
        return Collections.emptyList();
      }
      List<AbstractTreeNode> children = new ArrayList<AbstractTreeNode>();
      for (Deployment deployment : connection.getDeployments()) {
        children.add(new DeploymentNodeImpl(connection, this, deployment));
      }
      return children;
    }

    @Override
    protected void update(PresentationData presentation) {
      RemoteServer<?> server = getValue();
      ServerConnection connection = getConnection();
      presentation.setPresentableText(server.getName());
      presentation.setIcon(getServerNodeIcon(server.getType().getIcon(), connection != null ? getStatusIcon(connection.getStatus()) : null));
      presentation.setTooltip(connection != null ? connection.getStatusText() : null);
    }

    @Nullable
    private ServerConnection<?> getConnection() {
      return ServerConnectionManager.getInstance().getConnection(getValue());
    }

    public boolean isConnected() {
      ServerConnection<?> connection = getConnection();
      return connection != null && connection.getStatus() == ConnectionStatus.CONNECTED;
    }

    public void deploy(AnActionEvent e) {
      doDeploy(e, DefaultRunExecutor.getRunExecutorInstance(), "Deploy Configuration", true);
    }

    public void deployWithDebug(AnActionEvent e) {
      doDeploy(e, DefaultDebugExecutor.getDebugExecutorInstance(), "Deploy and Debug Configuration", false);
    }

    public void doDeploy(AnActionEvent e, final Executor executor, String popupTitle, boolean canCreate) {
      final RemoteServer<?> server = getValue();
      final ServerType<? extends ServerConfiguration> serverType = server.getType();
      final DeploymentConfigurationManager configurationManager = DeploymentConfigurationManager.getInstance(doGetProject());
      final List<RunnerAndConfigurationSettings> list = new ArrayList<RunnerAndConfigurationSettings>(ContainerUtil.filter(
        configurationManager.getDeploymentConfigurations(serverType),
        new Condition<RunnerAndConfigurationSettings>() {
          @Override
          public boolean value(RunnerAndConfigurationSettings settings) {
            DeployToServerRunConfiguration configuration =
              (DeployToServerRunConfiguration)settings.getConfiguration();
            return StringUtil.equals(server.getName(), configuration.getServerName());
          }
        }
      ));
      if (canCreate) {
        list.add(null);
      }
      ListPopup popup =
        JBPopupFactory.getInstance().createListPopup(new BaseListPopupStep<RunnerAndConfigurationSettings>(popupTitle, list) {
          @Override
          public Icon getIconFor(RunnerAndConfigurationSettings value) {
            return value != null ? serverType.getIcon() : null;
          }

          @NotNull
          @Override
          public String getTextFor(RunnerAndConfigurationSettings value) {
            return value != null ? value.getName() : "Create...";
          }

          @Override
          public PopupStep onChosen(final RunnerAndConfigurationSettings selectedValue, boolean finalChoice) {
            return doFinalStep(new Runnable() {
              @Override
              public void run() {
                if (selectedValue != null) {
                  ProgramRunnerUtil.executeConfiguration(doGetProject(), selectedValue, executor);
                }
                else {
                  configurationManager.createAndRunConfiguration(serverType, RemoteServerNode.this.getValue());
                }
              }
            });
          }
        });
      if (e.getInputEvent() instanceof MouseEvent) {
        popup.show(new RelativePoint((MouseEvent)e.getInputEvent()));
      }
      else {
        popup.showInBestPositionFor(e.getDataContext());
      }
    }

    public void editConfiguration() {
      ShowSettingsUtil.getInstance().editConfigurable(doGetProject(), new SingleRemoteServerConfigurable(getValue(), null, false));
    }

    @Nullable
    private Icon getStatusIcon(final ConnectionStatus status) {
      switch (status) {
        case CONNECTED: return RemoteServersIcons.ResumeScaled;
        case DISCONNECTED: return RemoteServersIcons.SuspendScaled;
        default: return null;
      }
    }
  }

  public class DeploymentNodeImpl extends AbstractTreeNode<Deployment> implements LogProvidingNode, DeploymentNode {
    private final ServerConnection<?> myConnection;
    private final RemoteServerNode myParentNode;

    private DeploymentNodeImpl(@NotNull ServerConnection<?> connection, @NotNull RemoteServerNode parentNode, Deployment value) {
      super(doGetProject(), value);
      myConnection = connection;
      myParentNode = parentNode;
    }

    @NotNull
    @Override
    public ServerNode getServerNode() {
      return myParentNode;
    }

    @Override
    public boolean isDeployActionVisible() {
      DeploymentTask<?> deploymentTask = getValue().getDeploymentTask();
      return deploymentTask instanceof DeploymentTaskImpl<?> && ((DeploymentTaskImpl)deploymentTask).getExecutionEnvironment().getRunnerAndConfigurationSettings() != null;
    }

    @Override
    public boolean isDeployActionEnabled() {
      return true;
    }

    @Override
    public void deploy() {
      doDeploy(DefaultRunExecutor.getRunExecutorInstance());
    }

    public void doDeploy(Executor executor) {
      DeploymentTask<?> deploymentTask = getValue().getDeploymentTask();
      if (deploymentTask != null) {
        ExecutionEnvironment environment = ((DeploymentTaskImpl)deploymentTask).getExecutionEnvironment();
        RunnerAndConfigurationSettings settings = environment.getRunnerAndConfigurationSettings();
        if (settings != null) {
          ProgramRunnerUtil.executeConfiguration(doGetProject(), settings, executor);
        }
      }
    }

    @Override
    public boolean isDebugActionVisible() {
      return myParentNode.getValue().getType().createDebugConnector() != null;
    }

    @Override
    public void deployWithDebug() {
      doDeploy(DefaultDebugExecutor.getDebugExecutorInstance());
    }

    @Override
    public boolean isUndeployActionEnabled() {
      DeploymentRuntime runtime = getValue().getRuntime();
      return runtime != null && runtime.isUndeploySupported();
    }

    @Override
    public void undeploy() {
      DeploymentRuntime runtime = getValue().getRuntime();
      if (runtime != null) {
        getConnection().undeploy(getValue(), runtime);
      }
    }

    public boolean isEditConfigurationActionVisible() {
      return getValue().getDeploymentTask() != null;
    }

    public void editConfiguration() {
      DeploymentTask<?> task = getValue().getDeploymentTask();
      if (task != null) {
        RunnerAndConfigurationSettings settings = ((DeploymentTaskImpl)task).getExecutionEnvironment().getRunnerAndConfigurationSettings();
        if (settings != null) {
          RunDialog.editConfiguration(doGetProject(), settings, "Edit Deployment Configuration");
        }
      }
    }

    @Override
    public boolean isDeployed() {
      return getValue().getStatus() == DeploymentStatus.DEPLOYED;
    }

    @Override
    public String getDeploymentName() {
      return getValue().getName();
    }

    public ServerConnection<?> getConnection() {
      return myConnection;
    }

    @Nullable
    @Override
    public LoggingHandlerImpl getLoggingHandler() {
      DeploymentLogManagerImpl logManager = getLogManager();
      return logManager != null && logManager.isMainHandlerVisible() ? logManager.getMainLoggingHandler() : null;
    }

    @Nullable
    private DeploymentLogManagerImpl getLogManager() {
      return (DeploymentLogManagerImpl)myConnection.getLogManager(getValue());
    }

    public String getId() {
      return myParentNode.getName() + ";deployment" + getValue().getName();
    }

    @NotNull
    @Override
    public String getLogId() {
      return getId() + ";main-log";
    }

    @NotNull
    @Override
    public Collection<? extends AbstractTreeNode> getChildren() {
      DeploymentLogManagerImpl logManager = (DeploymentLogManagerImpl)getConnection().getLogManager(getValue());
      if (logManager != null) {
        Map<String,LoggingHandlerImpl> handlers = logManager.getAdditionalLoggingHandlers();
        List<AbstractTreeNode> nodes = new ArrayList<AbstractTreeNode>();
        for (Map.Entry<String, LoggingHandlerImpl> entry : handlers.entrySet()) {
          nodes.add(new DeploymentLogNode(Pair.create(entry.getValue(), entry.getKey()), this));
        }
        return nodes;
      }
      return Collections.emptyList();
    }

    @Override
    protected void update(PresentationData presentation) {
      Deployment deployment = getValue();
      presentation.setIcon(getStatusIcon(deployment.getStatus()));
      presentation.setPresentableText(deployment.getName());
      presentation.setTooltip(deployment.getStatusText());
    }

    @Nullable
    private Icon getStatusIcon(DeploymentStatus status) {
      switch (status) {
        case DEPLOYED: return AllIcons.RunConfigurations.TestPassed;
        case NOT_DEPLOYED: return AllIcons.RunConfigurations.TestIgnored;
        case DEPLOYING: return AllIcons.RunConfigurations.TestInProgress4;
        case UNDEPLOYING: return AllIcons.RunConfigurations.TestInProgress4;
      }
      return null;
    }
  }

  public class DeploymentLogNode extends AbstractTreeNode<Pair<LoggingHandlerImpl, String>> implements ServersTreeNode, LogProvidingNode {
    @NotNull private final DeploymentNodeImpl myDeploymentNode;

    public DeploymentLogNode(@NotNull Pair<LoggingHandlerImpl, String> value, @NotNull DeploymentNodeImpl deploymentNode) {
      super(doGetProject(), value);
      myDeploymentNode = deploymentNode;
    }

    @NotNull
    @Override
    public Collection<? extends AbstractTreeNode> getChildren() {
      return Collections.emptyList();
    }

    @Override
    protected void update(PresentationData presentation) {
      presentation.setIcon(AllIcons.Debugger.Console);
      presentation.setPresentableText(getLogName());
    }

    private String getLogName() {
      return getValue().getSecond();
    }

    @Nullable
    @Override
    public LoggingHandlerImpl getLoggingHandler() {
      return getValue().getFirst();
    }

    @NotNull
    @Override
    public String getLogId() {
      return myDeploymentNode.getId() + ";log:" + getLogName();
    }
  }
}


File: platform/remote-servers/impl/src/com/intellij/remoteServer/util/CloudLoggingHandlerImpl.java
/*
 * Copyright 2000-2013 JetBrains s.r.o.
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
package com.intellij.remoteServer.util;

import com.intellij.execution.process.ProcessHandler;
import com.intellij.remoteServer.agent.util.CloudAgentLoggingHandler;
import com.intellij.remoteServer.agent.util.log.LogListener;
import com.intellij.remoteServer.runtime.deployment.DeploymentLogManager;
import com.intellij.remoteServer.runtime.log.LoggingHandler;
import org.jetbrains.annotations.Nullable;

import java.io.OutputStream;
import java.util.HashMap;

/**
 * @author michael.golubev
 */
public class CloudLoggingHandlerImpl implements CloudAgentLoggingHandler {

  private final HashMap<String, LogListener> myPipeName2LogListener;

  private final LoggingHandler myMainLoggingHandler;

  private final DeploymentLogManager myLogManager;

  public CloudLoggingHandlerImpl(DeploymentLogManager logManager) {
    myMainLoggingHandler = logManager.getMainLoggingHandler();
    myPipeName2LogListener = new HashMap<String, LogListener>();
    myLogManager = logManager;
  }

  @Override
  public void println(String message) {
    myMainLoggingHandler.print(message + "\n");
  }

  @Override
  public LogListener getOrCreateLogListener(String pipeName) {
    LogListener logListener = myPipeName2LogListener.get(pipeName);
    if (logListener == null) {
      final LoggingHandler loggingHandler = myLogManager.addAdditionalLog(pipeName);
      logListener = new LogListenerImpl(loggingHandler);
      myPipeName2LogListener.put(pipeName, logListener);
    }
    return logListener;
  }

  @Override
  public LogListener getOrCreateEmptyLogListener(String pipeName) {
    LogListenerImpl result = (LogListenerImpl)getOrCreateLogListener(pipeName);
    result.clear();
    return result;
  }

  @Override
  public LogListener createConsole(String pipeName, final OutputStream consoleInput) {
    final LoggingHandler loggingHandler = myLogManager.addAdditionalLog(pipeName);
    loggingHandler.attachToProcess(new ProcessHandler() {

      @Override
      protected void destroyProcessImpl() {

      }

      @Override
      protected void detachProcessImpl() {

      }

      @Override
      public boolean detachIsDefault() {
        return false;
      }

      @Nullable
      @Override
      public OutputStream getProcessInput() {
        return consoleInput;
      }
    });

    return new LogListener() {

      @Override
      public void lineLogged(String line) {
        loggingHandler.print(line);
      }
    };
  }

  private static class LogListenerImpl implements LogListener {

    private final LoggingHandler myLoggingHandler;

    public LogListenerImpl(LoggingHandler loggingHandler) {
      myLoggingHandler = loggingHandler;
    }

    @Override
    public void lineLogged(String line) {
      myLoggingHandler.print(line + "\n");
    }

    public void clear() {
      myLoggingHandler.clear();
    }
  }
}


File: platform/remote-servers/impl/src/com/intellij/remoteServer/util/CloudSilentLoggingHandlerImpl.java
package com.intellij.remoteServer.util;

import com.intellij.openapi.diagnostic.Logger;
import com.intellij.remoteServer.agent.util.CloudAgentLoggingHandler;
import com.intellij.remoteServer.agent.util.log.LogListener;

import java.io.OutputStream;

/**
 * @author michael.golubev
 */
public class CloudSilentLoggingHandlerImpl implements CloudAgentLoggingHandler {

  private static final Logger LOG = Logger.getInstance("#" + CloudSilentLoggingHandlerImpl.class.getName());

  @Override
  public void println(String message) {
    LOG.info(message);
  }

  @Override
  public LogListener getOrCreateLogListener(String pipeName) {
    return LogListener.NULL;
  }

  @Override
  public LogListener getOrCreateEmptyLogListener(String pipeName) {
    return LogListener.NULL;
  }

  @Override
  public LogListener createConsole(String pipeName, OutputStream consoleInput) {
    return LogListener.NULL;
  }
}
