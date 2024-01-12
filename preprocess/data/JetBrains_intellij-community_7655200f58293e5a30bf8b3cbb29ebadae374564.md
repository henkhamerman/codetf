Refactoring Types: ['Extract Method']
ellij/debugger/engine/DebugProcessImpl.java
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
package com.intellij.debugger.engine;

import com.intellij.Patches;
import com.intellij.debugger.*;
import com.intellij.debugger.actions.DebuggerAction;
import com.intellij.debugger.actions.DebuggerActions;
import com.intellij.debugger.apiAdapters.ConnectionServiceWrapper;
import com.intellij.debugger.engine.evaluation.*;
import com.intellij.debugger.engine.events.DebuggerCommandImpl;
import com.intellij.debugger.engine.events.SuspendContextCommandImpl;
import com.intellij.debugger.engine.jdi.ThreadReferenceProxy;
import com.intellij.debugger.engine.requests.MethodReturnValueWatcher;
import com.intellij.debugger.engine.requests.RequestManagerImpl;
import com.intellij.debugger.impl.DebuggerContextImpl;
import com.intellij.debugger.impl.DebuggerSession;
import com.intellij.debugger.impl.DebuggerUtilsEx;
import com.intellij.debugger.impl.PrioritizedTask;
import com.intellij.debugger.jdi.StackFrameProxyImpl;
import com.intellij.debugger.jdi.ThreadReferenceProxyImpl;
import com.intellij.debugger.jdi.VirtualMachineProxyImpl;
import com.intellij.debugger.settings.DebuggerSettings;
import com.intellij.debugger.settings.NodeRendererSettings;
import com.intellij.debugger.ui.breakpoints.BreakpointManager;
import com.intellij.debugger.ui.breakpoints.RunToCursorBreakpoint;
import com.intellij.debugger.ui.breakpoints.StepIntoBreakpoint;
import com.intellij.debugger.ui.tree.ValueDescriptor;
import com.intellij.debugger.ui.tree.render.*;
import com.intellij.execution.CantRunException;
import com.intellij.execution.ExecutionException;
import com.intellij.execution.ExecutionResult;
import com.intellij.execution.configurations.RemoteConnection;
import com.intellij.execution.process.*;
import com.intellij.execution.runners.ExecutionUtil;
import com.intellij.idea.ActionsBundle;
import com.intellij.openapi.Disposable;
import com.intellij.openapi.application.ApplicationManager;
import com.intellij.openapi.diagnostic.Logger;
import com.intellij.openapi.editor.Document;
import com.intellij.openapi.extensions.Extensions;
import com.intellij.openapi.project.Project;
import com.intellij.openapi.ui.Messages;
import com.intellij.openapi.util.Disposer;
import com.intellij.openapi.util.Pair;
import com.intellij.openapi.util.UserDataHolderBase;
import com.intellij.openapi.util.text.StringUtil;
import com.intellij.openapi.wm.ToolWindowId;
import com.intellij.openapi.wm.impl.status.StatusBarUtil;
import com.intellij.psi.CommonClassNames;
import com.intellij.psi.PsiDocumentManager;
import com.intellij.psi.PsiFile;
import com.intellij.psi.search.GlobalSearchScope;
import com.intellij.ui.classFilter.ClassFilter;
import com.intellij.ui.classFilter.DebuggerClassFilterProvider;
import com.intellij.util.Alarm;
import com.intellij.util.EventDispatcher;
import com.intellij.util.StringBuilderSpinAllocator;
import com.intellij.util.concurrency.Semaphore;
import com.intellij.util.containers.ContainerUtil;
import com.intellij.util.containers.HashMap;
import com.intellij.util.ui.UIUtil;
import com.intellij.xdebugger.XDebugSession;
import com.intellij.xdebugger.impl.XDebugSessionImpl;
import com.intellij.xdebugger.impl.actions.XDebuggerActions;
import com.sun.jdi.*;
import com.sun.jdi.connect.*;
import com.sun.jdi.request.EventRequest;
import com.sun.jdi.request.EventRequestManager;
import com.sun.jdi.request.StepRequest;
import org.jetbrains.annotations.NonNls;
import org.jetbrains.annotations.NotNull;
import org.jetbrains.annotations.Nullable;

import javax.swing.*;
import java.io.IOException;
import java.net.UnknownHostException;
import java.util.*;
import java.util.concurrent.atomic.AtomicBoolean;
import java.util.concurrent.atomic.AtomicInteger;

public abstract class DebugProcessImpl extends UserDataHolderBase implements DebugProcess {
  private static final Logger LOG = Logger.getInstance("#com.intellij.debugger.engine.DebugProcessImpl");

  @NonNls private static final String SOCKET_ATTACHING_CONNECTOR_NAME = "com.sun.jdi.SocketAttach";
  @NonNls private static final String SHMEM_ATTACHING_CONNECTOR_NAME = "com.sun.jdi.SharedMemoryAttach";
  @NonNls private static final String SOCKET_LISTENING_CONNECTOR_NAME = "com.sun.jdi.SocketListen";
  @NonNls private static final String SHMEM_LISTENING_CONNECTOR_NAME = "com.sun.jdi.SharedMemoryListen";

  private final Project myProject;
  private final RequestManagerImpl myRequestManager;

  private volatile VirtualMachineProxyImpl myVirtualMachineProxy = null;
  protected EventDispatcher<DebugProcessListener> myDebugProcessDispatcher = EventDispatcher.create(DebugProcessListener.class);
  protected EventDispatcher<EvaluationListener> myEvaluationDispatcher = EventDispatcher.create(EvaluationListener.class);

  private final List<ProcessListener> myProcessListeners = ContainerUtil.createLockFreeCopyOnWriteList();

  protected static final int STATE_INITIAL   = 0;
  protected static final int STATE_ATTACHED  = 1;
  protected static final int STATE_DETACHING = 2;
  protected static final int STATE_DETACHED  = 3;
  protected final AtomicInteger myState = new AtomicInteger(STATE_INITIAL);

  private volatile ExecutionResult myExecutionResult;
  private RemoteConnection myConnection;
  private JavaDebugProcess myXDebugProcess;

  private ConnectionServiceWrapper myConnectionService;
  private Map<String, Connector.Argument> myArguments;

  private final List<NodeRenderer> myRenderers = new ArrayList<NodeRenderer>();

  // we use null key here
  private final Map<Type, NodeRenderer> myNodeRenderersMap = new HashMap<Type, NodeRenderer>();

  private final NodeRendererSettingsListener mySettingsListener = new NodeRendererSettingsListener() {
    @Override
    public void renderersChanged() {
      myNodeRenderersMap.clear();
      myRenderers.clear();
      loadRenderers();
    }
  };

  private final SuspendManagerImpl mySuspendManager = new SuspendManagerImpl(this);
  protected CompoundPositionManager myPositionManager = null;
  private final DebuggerManagerThreadImpl myDebuggerManagerThread;
  private static final int LOCAL_START_TIMEOUT = 30000;

  private final Semaphore myWaitFor = new Semaphore();
  private final AtomicBoolean myIsFailed = new AtomicBoolean(false);
  protected DebuggerSession mySession;
  @Nullable protected MethodReturnValueWatcher myReturnValueWatcher;
  private final Disposable myDisposable = Disposer.newDisposable();
  private final Alarm myStatusUpdateAlarm = new Alarm(Alarm.ThreadToUse.SHARED_THREAD, myDisposable);

  protected DebugProcessImpl(Project project) {
    myProject = project;
    myDebuggerManagerThread = new DebuggerManagerThreadImpl(myDisposable, myProject);
    myRequestManager = new RequestManagerImpl(this);
    NodeRendererSettings.getInstance().addListener(mySettingsListener);
    loadRenderers();
  }

  private void loadRenderers() {
    getManagerThread().invoke(new DebuggerCommandImpl() {
      @Override
      protected void action() throws Exception {
        try {
          final NodeRendererSettings rendererSettings = NodeRendererSettings.getInstance();
          for (final NodeRenderer renderer : rendererSettings.getAllRenderers()) {
            if (renderer.isEnabled()) {
              myRenderers.add(renderer);
            }
          }
        }
        finally {
          DebuggerInvocationUtil.swingInvokeLater(myProject, new Runnable() {
            @Override
            public void run() {
              final DebuggerSession session = mySession;
              if (session != null && session.isAttached()) {
                session.refresh(true);
                DebuggerAction.refreshViews(mySession.getXDebugSession());
              }
            }
          });
        }
      }
    });
  }

  @Nullable
  public Pair<Method, Value> getLastExecutedMethod() {
    final MethodReturnValueWatcher watcher = myReturnValueWatcher;
    if (watcher == null) {
      return null;
    }
    final Method method = watcher.getLastExecutedMethod();
    if (method == null) {
      return null;
    }
    return Pair.create(method, watcher.getLastMethodReturnValue());
  }

  public void setWatchMethodReturnValuesEnabled(boolean enabled) {
    final MethodReturnValueWatcher watcher = myReturnValueWatcher;
    if (watcher != null) {
      watcher.setFeatureEnabled(enabled);
    }
  }

  public boolean isWatchMethodReturnValuesEnabled() {
    final MethodReturnValueWatcher watcher = myReturnValueWatcher;
    return watcher != null && watcher.isFeatureEnabled();
  }

  public boolean canGetMethodReturnValue() {
    return myReturnValueWatcher != null;
  }

  public NodeRenderer getAutoRenderer(ValueDescriptor descriptor) {
    DebuggerManagerThreadImpl.assertIsManagerThread();
    final Value value = descriptor.getValue();
    Type type = value != null ? value.type() : null;

    // in case evaluation is not possible, force default renderer
    if (!DebuggerManagerEx.getInstanceEx(getProject()).getContext().isEvaluationPossible()) {
      return getDefaultRenderer(type);
    }

    NodeRenderer renderer = myNodeRenderersMap.get(type);
    if(renderer == null) {
      for (final NodeRenderer nodeRenderer : myRenderers) {
        if (nodeRenderer.isApplicable(type)) {
          renderer = nodeRenderer;
          break;
        }
      }
      if (renderer == null) {
        renderer = getDefaultRenderer(type);
      }
      myNodeRenderersMap.put(type, renderer);
    }

    return renderer;
  }

  public static NodeRenderer getDefaultRenderer(Value value) {
    return getDefaultRenderer(value != null ? value.type() : null);
  }

  public static NodeRenderer getDefaultRenderer(Type type) {
    final NodeRendererSettings settings = NodeRendererSettings.getInstance();

    final PrimitiveRenderer primitiveRenderer = settings.getPrimitiveRenderer();
    if(primitiveRenderer.isApplicable(type)) {
      return primitiveRenderer;
    }

    final ArrayRenderer arrayRenderer = settings.getArrayRenderer();
    if(arrayRenderer.isApplicable(type)) {
      return arrayRenderer;
    }

    final ClassRenderer classRenderer = settings.getClassRenderer();
    LOG.assertTrue(classRenderer.isApplicable(type), type.name());
    return classRenderer;
  }

  private static final String ourTrace = System.getProperty("idea.debugger.trace");

  @SuppressWarnings({"HardCodedStringLiteral"})
  protected void commitVM(VirtualMachine vm) {
    if (!isInInitialState()) {
      LOG.error("State is invalid " + myState.get());
    }
    DebuggerManagerThreadImpl.assertIsManagerThread();
    myPositionManager = createPositionManager();
    if (LOG.isDebugEnabled()) {
      LOG.debug("*******************VM attached******************");
    }
    checkVirtualMachineVersion(vm);

    myVirtualMachineProxy = new VirtualMachineProxyImpl(this, vm);

    if (!StringUtil.isEmpty(ourTrace)) {
      int mask = 0;
      StringTokenizer tokenizer = new StringTokenizer(ourTrace);
      while (tokenizer.hasMoreTokens()) {
        String token = tokenizer.nextToken();
        if ("SENDS".compareToIgnoreCase(token) == 0) {
          mask |= VirtualMachine.TRACE_SENDS;
        }
        else if ("RAW_SENDS".compareToIgnoreCase(token) == 0) {
          mask |= 0x01000000;
        }
        else if ("RECEIVES".compareToIgnoreCase(token) == 0) {
          mask |= VirtualMachine.TRACE_RECEIVES;
        }
        else if ("RAW_RECEIVES".compareToIgnoreCase(token) == 0) {
          mask |= 0x02000000;
        }
        else if ("EVENTS".compareToIgnoreCase(token) == 0) {
          mask |= VirtualMachine.TRACE_EVENTS;
        }
        else if ("REFTYPES".compareToIgnoreCase(token) == 0) {
          mask |= VirtualMachine.TRACE_REFTYPES;
        }
        else if ("OBJREFS".compareToIgnoreCase(token) == 0) {
          mask |= VirtualMachine.TRACE_OBJREFS;
        }
        else if ("ALL".compareToIgnoreCase(token) == 0) {
          mask |= VirtualMachine.TRACE_ALL;
        }
      }

      vm.setDebugTraceMode(mask);
    }
  }

  private void stopConnecting() {
    DebuggerManagerThreadImpl.assertIsManagerThread();

    Map<String, Connector.Argument> arguments = myArguments;
    try {
      if (arguments == null) {
        return;
      }
      if(myConnection.isServerMode()) {
        ListeningConnector connector = (ListeningConnector)findConnector(SOCKET_LISTENING_CONNECTOR_NAME);
        if (connector == null) {
          LOG.error("Cannot find connector: " + SOCKET_LISTENING_CONNECTOR_NAME);
        }
        else {
          connector.stopListening(arguments);
        }
      }
      else {
        if(myConnectionService != null) {
          myConnectionService.close();
        }
      }
    }
    catch (IOException e) {
      if (LOG.isDebugEnabled()) {
        LOG.debug(e);
      }
    }
    catch (IllegalConnectorArgumentsException e) {
      if (LOG.isDebugEnabled()) {
        LOG.debug(e);
      }
    }
    catch (ExecutionException e) {
      LOG.error(e);
    }
    finally {
      closeProcess(true);
    }
  }

  protected CompoundPositionManager createPositionManager() {
    return new CompoundPositionManager(new PositionManagerImpl(this));
  }

  @Override
  public void printToConsole(final String text) {
    myExecutionResult.getProcessHandler().notifyTextAvailable(text, ProcessOutputTypes.SYSTEM);
  }

  @Override
  public ProcessHandler getProcessHandler() {
    return myExecutionResult != null ? myExecutionResult.getProcessHandler() : null;
  }

  /**
   *
   * @param suspendContext
   * @param stepThread
   * @param size the step size. One of {@link StepRequest#STEP_LINE} or {@link StepRequest#STEP_MIN}
   * @param depth
   * @param hint may be null
   */
  protected void doStep(final SuspendContextImpl suspendContext, final ThreadReferenceProxyImpl stepThread, int size, int depth,
                        RequestHint hint) {
    if (stepThread == null) {
      return;
    }
    try {
      final ThreadReference stepThreadReference = stepThread.getThreadReference();
      if (LOG.isDebugEnabled()) {
        LOG.debug("DO_STEP: creating step request for " + stepThreadReference);
      }
      deleteStepRequests(stepThreadReference);
      EventRequestManager requestManager = getVirtualMachineProxy().eventRequestManager();
      StepRequest stepRequest = requestManager.createStepRequest(stepThreadReference, size, depth);
      if (!(hint != null && hint.isIgnoreFilters()) /*&& depth == StepRequest.STEP_INTO*/) {
        final List<ClassFilter> activeFilters = new ArrayList<ClassFilter>();
        DebuggerSettings settings = DebuggerSettings.getInstance();
        if (settings.TRACING_FILTERS_ENABLED) {
          for (ClassFilter filter : settings.getSteppingFilters()) {
            if (filter.isEnabled()) {
              activeFilters.add(filter);
            }
          }
        }
        for (DebuggerClassFilterProvider provider : Extensions.getExtensions(DebuggerClassFilterProvider.EP_NAME)) {
          for (ClassFilter filter : provider.getFilters()) {
            if (filter.isEnabled()) {
              activeFilters.add(filter);
            }
          }
        }

        if (!activeFilters.isEmpty()) {
          final String currentClassName = getCurrentClassName(stepThread);
          if (currentClassName == null || !DebuggerUtilsEx.isFiltered(currentClassName, activeFilters)) {
            // add class filters
            for (ClassFilter filter : activeFilters) {
              stepRequest.addClassExclusionFilter(filter.getPattern());
            }
          }
        }
      }

      // suspend policy to match the suspend policy of the context:
      // if all threads were suspended, then during stepping all the threads must be suspended
      // if only event thread were suspended, then only this particular thread must be suspended during stepping
      stepRequest.setSuspendPolicy(suspendContext.getSuspendPolicy() == EventRequest.SUSPEND_EVENT_THREAD? EventRequest.SUSPEND_EVENT_THREAD : EventRequest.SUSPEND_ALL);

      if (hint != null) {
        //noinspection HardCodedStringLiteral
        stepRequest.putProperty("hint", hint);
      }
      stepRequest.enable();
    }
    catch (ObjectCollectedException ignored) {

    }
  }

  void deleteStepRequests(@Nullable final ThreadReference stepThread) {
    EventRequestManager requestManager = getVirtualMachineProxy().eventRequestManager();
    List<StepRequest> stepRequests = requestManager.stepRequests();
    if (!stepRequests.isEmpty()) {
      final List<StepRequest> toDelete = new ArrayList<StepRequest>(stepRequests.size());
      for (final StepRequest request : stepRequests) {
        ThreadReference threadReference = request.thread();
        // [jeka] on attempt to delete a request assigned to a thread with unknown status, a JDWP error occurs
        try {
          if (threadReference.status() != ThreadReference.THREAD_STATUS_UNKNOWN && (stepThread == null || stepThread.equals(threadReference))) {
            toDelete.add(request);
          }
        }
        catch (IllegalThreadStateException e) {
          LOG.info(e); // undocumented by JDI: may be thrown when querying thread status
        }
      }
      requestManager.deleteEventRequests(toDelete);
    }
  }

  @Nullable
  private static String getCurrentClassName(ThreadReferenceProxyImpl thread) {
    try {
      if (thread != null && thread.frameCount() > 0) {
        StackFrameProxyImpl stackFrame = thread.frame(0);
        if (stackFrame != null) {
          Location location = stackFrame.location();
          ReferenceType referenceType = location == null ? null : location.declaringType();
          if (referenceType != null) {
            return referenceType.name();
          }
        }
      }
    }
    catch (EvaluateException ignored) {
    }
    return null;
  }

  private VirtualMachine createVirtualMachineInt() throws ExecutionException {
    try {
      if (myArguments != null) {
        throw new IOException(DebuggerBundle.message("error.debugger.already.listening"));
      }

      final String address = myConnection.getAddress();
      if (myConnection.isServerMode()) {
        ListeningConnector connector = (ListeningConnector)findConnector(
          myConnection.isUseSockets() ? SOCKET_LISTENING_CONNECTOR_NAME : SHMEM_LISTENING_CONNECTOR_NAME);
        if (connector == null) {
          throw new CantRunException(DebuggerBundle.message("error.debug.connector.not.found", DebuggerBundle.getTransportName(myConnection)));
        }
        myArguments = connector.defaultArguments();
        if (myArguments == null) {
          throw new CantRunException(DebuggerBundle.message("error.no.debug.listen.port"));
        }

        if (address == null) {
          throw new CantRunException(DebuggerBundle.message("error.no.debug.listen.port"));
        }
        // negative port number means the caller leaves to debugger to decide at which port to listen
        //noinspection HardCodedStringLiteral
        final Connector.Argument portArg = myConnection.isUseSockets() ? myArguments.get("port") : myArguments.get("name");
        if (portArg != null) {
          portArg.setValue(address);
        }
        //noinspection HardCodedStringLiteral
        final Connector.Argument timeoutArg = myArguments.get("timeout");
        if (timeoutArg != null) {
          timeoutArg.setValue("0"); // wait forever
        }
        connector.startListening(myArguments);
        myDebugProcessDispatcher.getMulticaster().connectorIsReady();
        try {
          return connector.accept(myArguments);
        }
        finally {
          if(myArguments != null) {
            try {
              connector.stopListening(myArguments);
            }
            catch (IllegalArgumentException ignored) {
              // ignored
            }
            catch (IllegalConnectorArgumentsException ignored) {
              // ignored
            }
          }
        }
      }
      else { // is client mode, should attach to already running process
        AttachingConnector connector = (AttachingConnector)findConnector(
          myConnection.isUseSockets() ? SOCKET_ATTACHING_CONNECTOR_NAME : SHMEM_ATTACHING_CONNECTOR_NAME
        );

        if (connector == null) {
          throw new CantRunException( DebuggerBundle.message("error.debug.connector.not.found", DebuggerBundle.getTransportName(myConnection)));
        }
        myArguments = connector.defaultArguments();
        if (myConnection.isUseSockets()) {
          //noinspection HardCodedStringLiteral
          final Connector.Argument hostnameArg = myArguments.get("hostname");
          if (hostnameArg != null && myConnection.getHostName() != null) {
            hostnameArg.setValue(myConnection.getHostName());
          }
          if (address == null) {
            throw new CantRunException(DebuggerBundle.message("error.no.debug.attach.port"));
          }
          //noinspection HardCodedStringLiteral
          final Connector.Argument portArg = myArguments.get("port");
          if (portArg != null) {
            portArg.setValue(address);
          }
        }
        else {
          if (address == null) {
            throw new CantRunException(DebuggerBundle.message("error.no.shmem.address"));
          }
          //noinspection HardCodedStringLiteral
          final Connector.Argument nameArg = myArguments.get("name");
          if (nameArg != null) {
            nameArg.setValue(address);
          }
        }
        //noinspection HardCodedStringLiteral
        final Connector.Argument timeoutArg = myArguments.get("timeout");
        if (timeoutArg != null) {
          timeoutArg.setValue("0"); // wait forever
        }

        myDebugProcessDispatcher.getMulticaster().connectorIsReady();
        try {
          return connector.attach(myArguments);
        }
        catch (IllegalArgumentException e) {
          throw new CantRunException(e.getLocalizedMessage());
        }
      }
    }
    catch (IOException e) {
      throw new ExecutionException(processIOException(e, DebuggerBundle.getAddressDisplayName(myConnection)), e);
    }
    catch (IllegalConnectorArgumentsException e) {
      throw new ExecutionException(processError(e), e);
    }
    finally {
      myArguments = null;
      myConnectionService = null;
    }
  }

  public void showStatusText(final String text) {
    if (!myStatusUpdateAlarm.isDisposed()) {
      myStatusUpdateAlarm.cancelAllRequests();
      myStatusUpdateAlarm.addRequest(new Runnable() {
        @Override
        public void run() {
          StatusBarUtil.setStatusBarInfo(myProject, text);
        }
      }, 50);
    }
  }

  static Connector findConnector(String connectorName) throws ExecutionException {
    VirtualMachineManager virtualMachineManager;
    try {
      virtualMachineManager = Bootstrap.virtualMachineManager();
    }
    catch (Error e) {
      final String error = e.getClass().getName() + " : " + e.getLocalizedMessage();
      throw new ExecutionException(DebuggerBundle.message("debugger.jdi.bootstrap.error", error));
    }
    List connectors;
    if (SOCKET_ATTACHING_CONNECTOR_NAME.equals(connectorName) || SHMEM_ATTACHING_CONNECTOR_NAME.equals(connectorName)) {
      connectors = virtualMachineManager.attachingConnectors();
    }
    else if (SOCKET_LISTENING_CONNECTOR_NAME.equals(connectorName) || SHMEM_LISTENING_CONNECTOR_NAME.equals(connectorName)) {
      connectors = virtualMachineManager.listeningConnectors();
    }
    else {
      return null;
    }
    for (Object connector1 : connectors) {
      Connector connector = (Connector)connector1;
      if (connectorName.equals(connector.name())) {
        return connector;
      }
    }
    return null;
  }

  private void checkVirtualMachineVersion(VirtualMachine vm) {
    final String version = vm.version();
    if ("1.4.0".equals(version)) {
      SwingUtilities.invokeLater(new Runnable() {
        @Override
        public void run() {
          Messages.showMessageDialog(
            getProject(),
            DebuggerBundle.message("warning.jdk140.unstable"), DebuggerBundle.message("title.jdk140.unstable"), Messages.getWarningIcon()
          );
        }
      });
    }
  }

  /*Event dispatching*/
  public void addEvaluationListener(EvaluationListener evaluationListener) {
    myEvaluationDispatcher.addListener(evaluationListener);
  }

  public void removeEvaluationListener(EvaluationListener evaluationListener) {
    myEvaluationDispatcher.removeListener(evaluationListener);
  }

  @Override
  public void addDebugProcessListener(DebugProcessListener listener) {
    myDebugProcessDispatcher.addListener(listener);
  }

  @Override
  public void removeDebugProcessListener(DebugProcessListener listener) {
    myDebugProcessDispatcher.removeListener(listener);
  }

  public void addProcessListener(ProcessListener processListener) {
    synchronized(myProcessListeners) {
      if(getProcessHandler() != null) {
        getProcessHandler().addProcessListener(processListener);
      }
      else {
        myProcessListeners.add(processListener);
      }
    }
  }

  public void removeProcessListener(ProcessListener processListener) {
    synchronized (myProcessListeners) {
      if(getProcessHandler() != null) {
        getProcessHandler().removeProcessListener(processListener);
      }
      else {
        myProcessListeners.remove(processListener);
      }
    }
  }

  /* getters */
  public RemoteConnection getConnection() {
    return myConnection;
  }

  @Override
  public ExecutionResult getExecutionResult() {
    return myExecutionResult;
  }

  @Override
  public Project getProject() {
    return myProject;
  }

  public boolean canRedefineClasses() {
    final VirtualMachineProxyImpl vm = myVirtualMachineProxy;
    return vm != null && vm.canRedefineClasses();
  }

  public boolean canWatchFieldModification() {
    final VirtualMachineProxyImpl vm = myVirtualMachineProxy;
    return vm != null && vm.canWatchFieldModification();
  }

  public boolean isInInitialState() {
    return myState.get() == STATE_INITIAL;
  }

  @Override
  public boolean isAttached() {
    return myState.get() == STATE_ATTACHED;
  }

  @Override
  public boolean isDetached() {
    return myState.get() == STATE_DETACHED;
  }

  @Override
  public boolean isDetaching() {
    return myState.get() == STATE_DETACHING;
  }

  @Override
  public RequestManagerImpl getRequestsManager() {
    return myRequestManager;
  }

  @Override
  public VirtualMachineProxyImpl getVirtualMachineProxy() {
    DebuggerManagerThreadImpl.assertIsManagerThread();
    final VirtualMachineProxyImpl vm = myVirtualMachineProxy;
    if (vm == null) {
      throw new VMDisconnectedException();
    }
    return vm;
  }

  @Override
  public void appendPositionManager(final PositionManager positionManager) {
    DebuggerManagerThreadImpl.assertIsManagerThread();
    myPositionManager.appendPositionManager(positionManager);
  }

  private volatile RunToCursorBreakpoint myRunToCursorBreakpoint;

  public void cancelRunToCursorBreakpoint() {
    DebuggerManagerThreadImpl.assertIsManagerThread();
    final RunToCursorBreakpoint runToCursorBreakpoint = myRunToCursorBreakpoint;
    if (runToCursorBreakpoint != null) {
      myRunToCursorBreakpoint = null;
      getRequestsManager().deleteRequest(runToCursorBreakpoint);
      if (runToCursorBreakpoint.isRestoreBreakpoints()) {
        final BreakpointManager breakpointManager = DebuggerManagerEx.getInstanceEx(getProject()).getBreakpointManager();
        breakpointManager.enableBreakpoints(this);
      }
    }
  }

  protected void closeProcess(boolean closedByUser) {
    DebuggerManagerThreadImpl.assertIsManagerThread();

    if (myState.compareAndSet(STATE_INITIAL, STATE_DETACHING) || myState.compareAndSet(STATE_ATTACHED, STATE_DETACHING)) {
      try {
        getManagerThread().close();
      }
      finally {
        final VirtualMachineProxyImpl vm = myVirtualMachineProxy;
        myVirtualMachineProxy = null;
        myPositionManager = null;
        myReturnValueWatcher = null;
        myNodeRenderersMap.clear();
        myRenderers.clear();
        DebuggerUtils.cleanupAfterProcessFinish(this);
        myState.set(STATE_DETACHED);
        try {
          myDebugProcessDispatcher.getMulticaster().processDetached(this, closedByUser);
        }
        finally {
          //if (DebuggerSettings.getInstance().UNMUTE_ON_STOP) {
          //  XDebugSession session = mySession.getXDebugSession();
          //  if (session != null) {
          //    session.setBreakpointMuted(false);
          //  }
          //}
          if (vm != null) {
            try {
              vm.dispose(); // to be on the safe side ensure that VM mirror, if present, is disposed and invalidated
            }
            catch (Throwable ignored) {
            }
          }
          myWaitFor.up();
        }
      }

    }
  }

  private static String formatMessage(String message) {
    final int lineLength = 90;
    StringBuilder buf = new StringBuilder(message.length());
    int index = 0;
    while (index < message.length()) {
      buf.append(message.substring(index, Math.min(index + lineLength, message.length()))).append('\n');
      index += lineLength;
    }
    return buf.toString();
  }

  public static String processError(Exception e) {
    String message;

    if (e instanceof VMStartException) {
      VMStartException e1 = (VMStartException)e;
      message = e1.getLocalizedMessage();
    }
    else if (e instanceof IllegalConnectorArgumentsException) {
      IllegalConnectorArgumentsException e1 = (IllegalConnectorArgumentsException)e;
      final List<String> invalidArgumentNames = e1.argumentNames();
      message = formatMessage(DebuggerBundle.message("error.invalid.argument", invalidArgumentNames.size()) + ": "+ e1.getLocalizedMessage()) + invalidArgumentNames;
      if (LOG.isDebugEnabled()) {
        LOG.debug(e1);
      }
    }
    else if (e instanceof CantRunException) {
      message = e.getLocalizedMessage();
    }
    else if (e instanceof VMDisconnectedException) {
      message = DebuggerBundle.message("error.vm.disconnected");
    }
    else if (e instanceof IOException) {
      message = processIOException((IOException)e, null);
    }
    else if (e instanceof ExecutionException) {
      message = e.getLocalizedMessage();
    }
    else  {
      message = DebuggerBundle.message("error.exception.while.connecting", e.getClass().getName(), e.getLocalizedMessage());
      if (LOG.isDebugEnabled()) {
        LOG.debug(e);
      }
    }
    return message;
  }

  @NotNull
  public static String processIOException(@NotNull IOException e, @Nullable String address) {
    if (e instanceof UnknownHostException) {
      return DebuggerBundle.message("error.unknown.host") + (address != null ? " (" + address + ")" : "") + ":\n" + e.getLocalizedMessage();
    }

    String message;
    final StringBuilder buf = StringBuilderSpinAllocator.alloc();
    try {
      buf.append(DebuggerBundle.message("error.cannot.open.debugger.port"));
      if (address != null) {
        buf.append(" (").append(address).append(")");
      }
      buf.append(": ");
      buf.append(e.getClass().getName()).append(" ");
      final String localizedMessage = e.getLocalizedMessage();
      if (!StringUtil.isEmpty(localizedMessage)) {
        buf.append('"');
        buf.append(localizedMessage);
        buf.append('"');
      }
      if (LOG.isDebugEnabled()) {
        LOG.debug(e);
      }
      message = buf.toString();
    }
    finally {
      StringBuilderSpinAllocator.dispose(buf);
    }
    return message;
  }

  public void dispose() {
    NodeRendererSettings.getInstance().removeListener(mySettingsListener);
    Disposer.dispose(myDisposable);
    myRequestManager.setFilterThread(null);
  }

  @Override
  public DebuggerManagerThreadImpl getManagerThread() {
    return myDebuggerManagerThread;
  }

  private static int getInvokePolicy(SuspendContext suspendContext) {
    //return ThreadReference.INVOKE_SINGLE_THREADED;
    return suspendContext.getSuspendPolicy() == EventRequest.SUSPEND_EVENT_THREAD ? ObjectReference.INVOKE_SINGLE_THREADED : 0;
  }

  @Override
  public void waitFor() {
    LOG.assertTrue(!DebuggerManagerThreadImpl.isManagerThread());
    myWaitFor.waitFor();
  }

  @Override
  public void waitFor(long timeout) {
    LOG.assertTrue(!DebuggerManagerThreadImpl.isManagerThread());
    myWaitFor.waitFor(timeout);
  }

  private abstract class InvokeCommand <E extends Value> {
    private final Method myMethod;
    private final List myArgs;

    protected InvokeCommand(@NotNull Method method, @NotNull List args) {
      myMethod = method;
      if (!args.isEmpty()) {
        myArgs = new ArrayList(args);
      }
      else {
        myArgs = args;
      }
    }

    public String toString() {
      return "INVOKE: " + super.toString();
    }

    protected abstract E invokeMethod(int invokePolicy, Method method, final List args) throws InvocationException,
                                                                                ClassNotLoadedException,
                                                                                IncompatibleThreadStateException,
                                                                                InvalidTypeException;


    E start(EvaluationContextImpl evaluationContext, boolean internalEvaluate) throws EvaluateException {
      while (true) {
        try {
          return startInternal(evaluationContext, internalEvaluate);
        }
        catch (ClassNotLoadedException e) {
          ReferenceType loadedClass = null;
          try {
            if (evaluationContext.isAutoLoadClasses()) {
              loadedClass = loadClass(evaluationContext, e.className(), evaluationContext.getClassLoader());
            }
          }
          catch (Exception ignored) {
            loadedClass = null;
          }
          if (loadedClass == null) {
            throw EvaluateExceptionUtil.createEvaluateException(e);
          }
        }
      }
    }

    E startInternal(EvaluationContextImpl evaluationContext, boolean internalEvaluate)
      throws EvaluateException, ClassNotLoadedException {
      DebuggerManagerThreadImpl.assertIsManagerThread();
      SuspendContextImpl suspendContext = evaluationContext.getSuspendContext();
      SuspendManagerUtil.assertSuspendContext(suspendContext);

      ThreadReferenceProxyImpl invokeThread = suspendContext.getThread();

      if (SuspendManagerUtil.isEvaluating(getSuspendManager(), invokeThread)) {
        throw EvaluateExceptionUtil.NESTED_EVALUATION_ERROR;
      }

      Set<SuspendContextImpl> suspendingContexts = SuspendManagerUtil.getSuspendingContexts(getSuspendManager(), invokeThread);
      final ThreadReference invokeThreadRef = invokeThread.getThreadReference();

      myEvaluationDispatcher.getMulticaster().evaluationStarted(suspendContext);
      beforeMethodInvocation(suspendContext, myMethod, internalEvaluate);

      Object resumeData = null;
      try {
        for (SuspendContextImpl suspendingContext : suspendingContexts) {
          final ThreadReferenceProxyImpl suspendContextThread = suspendingContext.getThread();
          if (suspendContextThread != invokeThread) {
            if (LOG.isDebugEnabled()) {
              LOG.debug("Resuming " + invokeThread + " that is paused by " + suspendContextThread);
            }
            LOG.assertTrue(suspendContextThread == null || !invokeThreadRef.equals(suspendContextThread.getThreadReference()));
            getSuspendManager().resumeThread(suspendingContext, invokeThread);
          }
        }

        resumeData = SuspendManagerUtil.prepareForResume(suspendContext);
        suspendContext.setIsEvaluating(evaluationContext);

        getVirtualMachineProxy().clearCaches();

        return invokeMethodAndFork(suspendContext);
      }
      catch (InvocationException e) {
        throw EvaluateExceptionUtil.createEvaluateException(e);
      }
      catch (IncompatibleThreadStateException e) {
        throw EvaluateExceptionUtil.createEvaluateException(e);
      }
      catch (InvalidTypeException e) {
        throw EvaluateExceptionUtil.createEvaluateException(e);
      }
      catch (ObjectCollectedException e) {
        throw EvaluateExceptionUtil.createEvaluateException(e);
      }
      catch (UnsupportedOperationException e) {
        throw EvaluateExceptionUtil.createEvaluateException(e);
      }
      catch (InternalException e) {
        throw EvaluateExceptionUtil.createEvaluateException(e);
      }
      finally {
        suspendContext.setIsEvaluating(null);
        if (resumeData != null) {
          SuspendManagerUtil.restoreAfterResume(suspendContext, resumeData);
        }
        for (SuspendContextImpl suspendingContext : mySuspendManager.getEventContexts()) {
          if (suspendingContexts.contains(suspendingContext) && !suspendingContext.isEvaluating() && !suspendingContext.suspends(invokeThread)) {
            mySuspendManager.suspendThread(suspendingContext, invokeThread);
          }
        }

        if (LOG.isDebugEnabled()) {
          LOG.debug("getVirtualMachine().clearCaches()");
        }
        getVirtualMachineProxy().clearCaches();
        afterMethodInvocation(suspendContext, internalEvaluate);

        myEvaluationDispatcher.getMulticaster().evaluationFinished(suspendContext);
      }
    }

    private E invokeMethodAndFork(final SuspendContextImpl context) throws InvocationException,
                                                                           ClassNotLoadedException,
                                                                           IncompatibleThreadStateException,
                                                                           InvalidTypeException {
      final int invokePolicy = getInvokePolicy(context);
      final Exception[] exception = new Exception[1];
      final Value[] result = new Value[1];
      getManagerThread().startLongProcessAndFork(new Runnable() {
        @Override
        public void run() {
          ThreadReferenceProxyImpl thread = context.getThread();
          try {
            try {
              if (LOG.isDebugEnabled()) {
                final VirtualMachineProxyImpl virtualMachineProxy = getVirtualMachineProxy();
                virtualMachineProxy.logThreads();
                LOG.debug("Invoke in " + thread.name());
                assertThreadSuspended(thread, context);
              }

              if (myMethod.isVarArgs()) {
                // See IDEA-63581
                // if vararg parameter array is of interface type and Object[] is expected, JDI wrap it into another array,
                // in this case we have to unroll the array manually and pass its elements to the method instead of array object
                int lastIndex = myArgs.size() - 1;
                if (lastIndex >= 0) {
                  final Object lastArg = myArgs.get(lastIndex);
                  if (lastArg instanceof ArrayReference) {
                    final ArrayReference arrayRef = (ArrayReference)lastArg;
                    if (((ArrayType)arrayRef.referenceType()).componentType() instanceof InterfaceType) {
                      List<String> argTypes = myMethod.argumentTypeNames();
                      if (argTypes.size() > lastIndex && argTypes.get(lastIndex).startsWith(CommonClassNames.JAVA_LANG_OBJECT)) {
                        // unwrap array of interfaces for vararg param
                        myArgs.remove(lastIndex);
                        myArgs.addAll(arrayRef.getValues());
                      }
                    }
                  }
                }
              }

              if (!Patches.IBM_JDK_DISABLE_COLLECTION_BUG) {
                // ensure args are not collected
                for (Object arg : myArgs) {
                  if (arg instanceof ObjectReference) {
                    ((ObjectReference)arg).disableCollection();
                  }
                }
              }

              // workaround for jdi hang in trace mode
              if (!StringUtil.isEmpty(ourTrace)) {
                for (Object arg : myArgs) {
                  //noinspection ResultOfMethodCallIgnored
                  arg.toString();
                }
              }

              result[0] = invokeMethod(invokePolicy, myMethod, myArgs);
            }
            finally {
              //  assertThreadSuspended(thread, context);
              if (!Patches.IBM_JDK_DISABLE_COLLECTION_BUG) {
                // ensure args are not collected
                for (Object arg : myArgs) {
                  if (arg instanceof ObjectReference) {
                    ((ObjectReference)arg).enableCollection();
                  }
                }
              }
            }
          }
          catch (Exception e) {
            exception[0] = e;
          }
        }
      });

      if (exception[0] != null) {
        if (exception[0] instanceof InvocationException) {
          throw (InvocationException)exception[0];
        }
        else if (exception[0] instanceof ClassNotLoadedException) {
          throw (ClassNotLoadedException)exception[0];
        }
        else if (exception[0] instanceof IncompatibleThreadStateException) {
          throw (IncompatibleThreadStateException)exception[0];
        }
        else if (exception[0] instanceof InvalidTypeException) {
          throw (InvalidTypeException)exception[0];
        }
        else if (exception[0] instanceof RuntimeException) {
          throw (RuntimeException)exception[0];
        }
        else {
          LOG.error("Unexpected exception", new Throwable().initCause(exception[0]));
        }
      }

      return (E)result[0];
    }

    private void assertThreadSuspended(final ThreadReferenceProxyImpl thread, final SuspendContextImpl context) {
      LOG.assertTrue(context.isEvaluating());
      try {
        final boolean isSuspended = thread.isSuspended();
        LOG.assertTrue(isSuspended, thread);
      }
      catch (ObjectCollectedException ignored) {
      }
    }
  }

  @Override
  public Value invokeMethod(@NotNull EvaluationContext evaluationContext, @NotNull ObjectReference objRef, @NotNull Method method, final List args) throws EvaluateException {
    return invokeInstanceMethod(evaluationContext, objRef, method, args, 0);
  }

  @Override
  public Value invokeInstanceMethod(@NotNull EvaluationContext evaluationContext,
                                    @NotNull final ObjectReference objRef,
                                    @NotNull Method method,
                                    @NotNull List args,
                                    final int invocationOptions) throws EvaluateException {
    final ThreadReference thread = getEvaluationThread(evaluationContext);
    return new InvokeCommand<Value>(method, args) {
      @Override
      protected Value invokeMethod(int invokePolicy, Method method, final List args) throws InvocationException, ClassNotLoadedException, IncompatibleThreadStateException, InvalidTypeException {
        if (LOG.isDebugEnabled()) {
          LOG.debug("Invoke " + method.name());
        }
        return objRef.invokeMethod(thread, method, args, invokePolicy | invocationOptions);
      }
    }.start((EvaluationContextImpl)evaluationContext, false);
  }

  private static ThreadReference getEvaluationThread(final EvaluationContext evaluationContext) throws EvaluateException {
    ThreadReferenceProxy evaluationThread = evaluationContext.getSuspendContext().getThread();
    if(evaluationThread == null) {
      throw EvaluateExceptionUtil.NULL_STACK_FRAME;
    }
    return evaluationThread.getThreadReference();
  }

  @Override
  public Value invokeMethod(final EvaluationContext evaluationContext, final ClassType classType,
                            final Method method,
                            final List args) throws EvaluateException {
    return invokeMethod(evaluationContext, classType, method, args, false);
  }

  public Value invokeMethod(@NotNull EvaluationContext evaluationContext,
                            @NotNull final ClassType classType,
                            @NotNull Method method,
                            @NotNull List args,
                            boolean internalEvaluate) throws EvaluateException {
    final ThreadReference thread = getEvaluationThread(evaluationContext);
    return new InvokeCommand<Value>(method, args) {
      @Override
      protected Value invokeMethod(int invokePolicy, Method method, List args) throws InvocationException,
                                                                             ClassNotLoadedException,
                                                                             IncompatibleThreadStateException,
                                                                             InvalidTypeException {
        if (LOG.isDebugEnabled()) {
          LOG.debug("Invoke " + method.name());
        }
        return classType.invokeMethod(thread, method, args, invokePolicy);
      }
    }.start((EvaluationContextImpl)evaluationContext, internalEvaluate);
  }

  @Override
  public ArrayReference newInstance(final ArrayType arrayType,
                                    final int dimension)
    throws EvaluateException {
    try {
      return arrayType.newInstance(dimension);
    }
    catch (Exception e) {
      throw EvaluateExceptionUtil.createEvaluateException(e);
    }
  }

  @Override
  public ObjectReference newInstance(@NotNull final EvaluationContext evaluationContext,
                                     @NotNull final ClassType classType,
                                     @NotNull Method method,
                                     @NotNull List args) throws EvaluateException {
    final ThreadReference thread = getEvaluationThread(evaluationContext);
    InvokeCommand<ObjectReference> invokeCommand = new InvokeCommand<ObjectReference>(method, args) {
      @Override
      protected ObjectReference invokeMethod(int invokePolicy, Method method, List args) throws InvocationException,
                                                                                       ClassNotLoadedException,
                                                                                       IncompatibleThreadStateException,
                                                                                       InvalidTypeException {
        if (LOG.isDebugEnabled()) {
          LOG.debug("New instance " + method.name());
        }
        return classType.newInstance(thread, method, args, invokePolicy);
      }
    };
    return invokeCommand.start((EvaluationContextImpl)evaluationContext, false);
  }

  public void clearCashes(int suspendPolicy) {
    if (!isAttached()) return;
    switch (suspendPolicy) {
      case EventRequest.SUSPEND_ALL:
        getVirtualMachineProxy().clearCaches();
        break;
      case EventRequest.SUSPEND_EVENT_THREAD:
        getVirtualMachineProxy().clearCaches();
        //suspendContext.getThread().clearAll();
        break;
    }
  }

  protected void beforeSuspend(SuspendContextImpl suspendContext) {
    clearCashes(suspendContext.getSuspendPolicy());
  }

  private void beforeMethodInvocation(SuspendContextImpl suspendContext, Method method, boolean internalEvaluate) {
    if (LOG.isDebugEnabled()) {
      LOG.debug(
        "before invocation in  thread " + suspendContext.getThread().name() + " method " + (method == null ? "null" : method.name()));
    }

    if (!internalEvaluate) {
      if (method != null) {
        showStatusText(DebuggerBundle.message("progress.evaluating", DebuggerUtilsEx.methodName(method)));
      }
      else {
        showStatusText(DebuggerBundle.message("title.evaluating"));
      }
    }
  }

  private void afterMethodInvocation(SuspendContextImpl suspendContext, boolean internalEvaluate) {
    if (LOG.isDebugEnabled()) {
      LOG.debug("after invocation in  thread " + suspendContext.getThread().name());
    }
    if (!internalEvaluate) {
      showStatusText("");
    }
  }

  @Override
  public ReferenceType findClass(EvaluationContext evaluationContext, String className,
                                 ClassLoaderReference classLoader) throws EvaluateException {
    try {
      DebuggerManagerThreadImpl.assertIsManagerThread();
      final VirtualMachineProxyImpl vmProxy = getVirtualMachineProxy();
      if (vmProxy == null) {
        throw new VMDisconnectedException();
      }
      ReferenceType result = null;
      for (final ReferenceType refType : vmProxy.classesByName(className)) {
        if (refType.isPrepared() && isVisibleFromClassLoader(classLoader, refType)) {
          result = refType;
          break;
        }
      }
      final EvaluationContextImpl evalContext = (EvaluationContextImpl)evaluationContext;
      if (result == null && evalContext.isAutoLoadClasses()) {
        return loadClass(evalContext, className, classLoader);
      }
      return result;
    }
    catch (InvocationException e) {
      throw EvaluateExceptionUtil.createEvaluateException(e);
    }
    catch (ClassNotLoadedException e) {
      throw EvaluateExceptionUtil.createEvaluateException(e);
    }
    catch (IncompatibleThreadStateException e) {
      throw EvaluateExceptionUtil.createEvaluateException(e);
    }
    catch (InvalidTypeException e) {
      throw EvaluateExceptionUtil.createEvaluateException(e);
    }
  }

  private static boolean isVisibleFromClassLoader(final ClassLoaderReference fromLoader, final ReferenceType refType) {
    // IMPORTANT! Even if the refType is already loaded by some parent or bootstrap loader, it may not be visible from the given loader.
    // For example because there were no accesses yet from this loader to this class. So the loader is not in the list of "initialing" loaders
    // for this refType and the refType is not visible to the loader.
    // Attempt to evaluate method with this refType will yield ClassNotLoadedException.
    // The only way to say for sure whether the class is _visible_ to the given loader, is to use the following API call
    return fromLoader == null || fromLoader.equals(refType.classLoader()) || fromLoader.visibleClasses().contains(refType);
  }

  private static String reformatArrayName(String className) {
    if (className.indexOf('[') == -1) return className;

    int dims = 0;
    while (className.endsWith("[]")) {
      className = className.substring(0, className.length() - 2);
      dims++;
    }

    StringBuilder buffer = StringBuilderSpinAllocator.alloc();
    try {
      for (int i = 0; i < dims; i++) {
        buffer.append('[');
      }
      String primitiveSignature = JVMNameUtil.getPrimitiveSignature(className);
      if(primitiveSignature != null) {
        buffer.append(primitiveSignature);
      }
      else {
        buffer.append('L');
        buffer.append(className);
        buffer.append(';');
      }
      return buffer.toString();
    }
    finally {
      StringBuilderSpinAllocator.dispose(buffer);
    }
  }

  @SuppressWarnings({"HardCodedStringLiteral", "SpellCheckingInspection"})
  public ReferenceType loadClass(EvaluationContextImpl evaluationContext, String qName, ClassLoaderReference classLoader)
    throws InvocationException, ClassNotLoadedException, IncompatibleThreadStateException, InvalidTypeException, EvaluateException {

    DebuggerManagerThreadImpl.assertIsManagerThread();
    qName = reformatArrayName(qName);
    ReferenceType refType = null;
    VirtualMachineProxyImpl virtualMachine = getVirtualMachineProxy();
    final List classClasses = virtualMachine.classesByName("java.lang.Class");
    if (!classClasses.isEmpty()) {
      ClassType classClassType = (ClassType)classClasses.get(0);
      final Method forNameMethod;
      if (classLoader != null) {
        //forNameMethod = classClassType.concreteMethodByName("forName", "(Ljava/lang/String;ZLjava/lang/ClassLoader;)Ljava/lang/Class;");
        forNameMethod = DebuggerUtils.findMethod(classClassType, "forName", "(Ljava/lang/String;ZLjava/lang/ClassLoader;)Ljava/lang/Class;");
      }
      else {
        //forNameMethod = classClassType.concreteMethodByName("forName", "(Ljava/lang/String;)Ljava/lang/Class;");
        forNameMethod = DebuggerUtils.findMethod(classClassType, "forName", "(Ljava/lang/String;)Ljava/lang/Class;");
      }
      final List<Mirror> args = new ArrayList<Mirror>(); // do not use unmodifiable lists because the list is modified by JPDA
      final StringReference qNameMirror = virtualMachine.mirrorOf(qName);
      args.add(qNameMirror);
      if (classLoader != null) {
        args.add(virtualMachine.mirrorOf(true));
        args.add(classLoader);
      }
      final Value value = invokeMethod(evaluationContext, classClassType, forNameMethod, args);
      if (value instanceof ClassObjectReference) {
        refType = ((ClassObjectReference)value).reflectedType();
      }
    }
    return refType;
  }

  public void logThreads() {
    if (LOG.isDebugEnabled()) {
      try {
        Collection<ThreadReferenceProxyImpl> allThreads = getVirtualMachineProxy().allThreads();
        for (ThreadReferenceProxyImpl threadReferenceProxy : allThreads) {
          LOG.debug("Thread name=" + threadReferenceProxy.name() + " suspendCount()=" + threadReferenceProxy.getSuspendCount());
        }
      }
      catch (Exception e) {
        LOG.debug(e);
      }
    }
  }

  public SuspendManager getSuspendManager() {
    return mySuspendManager;
  }

  @Override
  public CompoundPositionManager getPositionManager() {
    return myPositionManager;
  }
  //ManagerCommands

  @Override
  public void stop(boolean forceTerminate) {
    getManagerThread().terminateAndInvoke(createStopCommand(forceTerminate), DebuggerManagerThreadImpl.COMMAND_TIMEOUT);
  }

  public StopCommand createStopCommand(boolean forceTerminate) {
    return new StopCommand(forceTerminate);
  }

  protected class StopCommand extends DebuggerCommandImpl {
    private final boolean myIsTerminateTargetVM;

    public StopCommand(boolean isTerminateTargetVM) {
      myIsTerminateTargetVM = isTerminateTargetVM;
    }

    @Override
    public Priority getPriority() {
      return Priority.HIGH;
    }

    @Override
    protected void action() throws Exception {
      if (isAttached()) {
        final VirtualMachineProxyImpl virtualMachineProxy = getVirtualMachineProxy();
        if (myIsTerminateTargetVM) {
          virtualMachineProxy.exit(-1);
        }
        else {
          // some VMs (like IBM VM 1.4.2 bundled with WebSphere) does not resume threads on dispose() like it should
          try {
            virtualMachineProxy.resume();
          }
          finally {
            virtualMachineProxy.dispose();
          }
        }
      }
      else {
        stopConnecting();
      }
    }
  }

  private class StepOutCommand extends ResumeCommand {
    private final int myStepSize;

    public StepOutCommand(SuspendContextImpl suspendContext, int stepSize) {
      super(suspendContext);
      myStepSize = stepSize;
    }

    @Override
    public void contextAction() {
      showStatusText(DebuggerBundle.message("status.step.out"));
      final SuspendContextImpl suspendContext = getSuspendContext();
      final ThreadReferenceProxyImpl thread = getContextThread();
      RequestHint hint = new RequestHint(thread, suspendContext, StepRequest.STEP_OUT);
      hint.setIgnoreFilters(mySession.shouldIgnoreSteppingFilters());
      applyThreadFilter(thread);
      final MethodReturnValueWatcher rvWatcher = myReturnValueWatcher;
      if (rvWatcher != null) {
        rvWatcher.enable(thread.getThreadReference());
      }
      doStep(suspendContext, thread, myStepSize, StepRequest.STEP_OUT, hint);
      super.contextAction();
    }
  }

  private class StepIntoCommand extends ResumeCommand {
    private final boolean myForcedIgnoreFilters;
    private final MethodFilter mySmartStepFilter;
    @Nullable
    private final StepIntoBreakpoint myBreakpoint;
    private final int myStepSize;

    public StepIntoCommand(SuspendContextImpl suspendContext, boolean ignoreFilters, @Nullable final MethodFilter methodFilter,
                           int stepSize) {
      super(suspendContext);
      myForcedIgnoreFilters = ignoreFilters || methodFilter != null;
      mySmartStepFilter = methodFilter;
      myBreakpoint = methodFilter instanceof BreakpointStepMethodFilter ?
        DebuggerManagerEx.getInstanceEx(myProject).getBreakpointManager().addStepIntoBreakpoint(((BreakpointStepMethodFilter)methodFilter)) :
        null;
      myStepSize = stepSize;
    }

    @Override
    public void contextAction() {
      showStatusText(DebuggerBundle.message("status.step.into"));
      final SuspendContextImpl suspendContext = getSuspendContext();
      final ThreadReferenceProxyImpl stepThread = getContextThread();
      final RequestHint hint = mySmartStepFilter != null?
                               new RequestHint(stepThread, suspendContext, mySmartStepFilter) :
                               new RequestHint(stepThread, suspendContext, StepRequest.STEP_INTO);
      if (myForcedIgnoreFilters) {
        try {
          mySession.setIgnoreStepFiltersFlag(stepThread.frameCount());
        }
        catch (EvaluateException e) {
          LOG.info(e);
        }
      }
      hint.setIgnoreFilters(myForcedIgnoreFilters || mySession.shouldIgnoreSteppingFilters());
      applyThreadFilter(stepThread);
      if (myBreakpoint != null) {
        myBreakpoint.setSuspendPolicy(suspendContext.getSuspendPolicy() == EventRequest.SUSPEND_EVENT_THREAD? DebuggerSettings.SUSPEND_THREAD : DebuggerSettings.SUSPEND_ALL);
        myBreakpoint.createRequest(suspendContext.getDebugProcess());
        myRunToCursorBreakpoint = myBreakpoint;
      }
      doStep(suspendContext, stepThread, myStepSize, StepRequest.STEP_INTO, hint);
      super.contextAction();
    }
  }

  private class StepOverCommand extends ResumeCommand {
    private final boolean myIsIgnoreBreakpoints;
    private final int myStepSize;

    public StepOverCommand(SuspendContextImpl suspendContext, boolean ignoreBreakpoints, int stepSize) {
      super(suspendContext);
      myIsIgnoreBreakpoints = ignoreBreakpoints;
      myStepSize = stepSize;
    }

    @Override
    public void contextAction() {
      showStatusText(DebuggerBundle.message("status.step.over"));
      final SuspendContextImpl suspendContext = getSuspendContext();
      final ThreadReferenceProxyImpl stepThread = getContextThread();
      // need this hint while stepping over for JSR45 support:
      // several lines of generated java code may correspond to a single line in the source file,
      // from which the java code was generated
      RequestHint hint = new RequestHint(stepThread, suspendContext, StepRequest.STEP_OVER);
      hint.setRestoreBreakpoints(myIsIgnoreBreakpoints);
      hint.setIgnoreFilters(myIsIgnoreBreakpoints || mySession.shouldIgnoreSteppingFilters());

      applyThreadFilter(stepThread);

      final MethodReturnValueWatcher rvWatcher = myReturnValueWatcher;
      if (rvWatcher != null) {
        rvWatcher.enable(stepThread.getThreadReference());
      }

      doStep(suspendContext, stepThread, myStepSize, StepRequest.STEP_OVER, hint);

      if (myIsIgnoreBreakpoints) {
        DebuggerManagerEx.getInstanceEx(myProject).getBreakpointManager().disableBreakpoints(DebugProcessImpl.this);
      }
      super.contextAction();
    }
  }

  private class RunToCursorCommand extends ResumeCommand {
    private final RunToCursorBreakpoint myRunToCursorBreakpoint;
    private final boolean myIgnoreBreakpoints;

    private RunToCursorCommand(SuspendContextImpl suspendContext, Document document, int lineIndex, final boolean ignoreBreakpoints) {
      super(suspendContext);
      myIgnoreBreakpoints = ignoreBreakpoints;
      final BreakpointManager breakpointManager = DebuggerManagerEx.getInstanceEx(myProject).getBreakpointManager();
      myRunToCursorBreakpoint = breakpointManager.addRunToCursorBreakpoint(document, lineIndex, ignoreBreakpoints);
    }

    @Override
    public void contextAction() {
      showStatusText(DebuggerBundle.message("status.run.to.cursor"));
      cancelRunToCursorBreakpoint();
      if (myRunToCursorBreakpoint == null) {
        return;
      }
      if (myIgnoreBreakpoints) {
        final BreakpointManager breakpointManager = DebuggerManagerEx.getInstanceEx(myProject).getBreakpointManager();
        breakpointManager.disableBreakpoints(DebugProcessImpl.this);
      }
      applyThreadFilter(getContextThread());
      final SuspendContextImpl context = getSuspendContext();
      myRunToCursorBreakpoint.setSuspendPolicy(context.getSuspendPolicy() == EventRequest.SUSPEND_EVENT_THREAD? DebuggerSettings.SUSPEND_THREAD : DebuggerSettings.SUSPEND_ALL);
      DebugProcessImpl debugProcess = context.getDebugProcess();
      myRunToCursorBreakpoint.createRequest(debugProcess);
      DebugProcessImpl.this.myRunToCursorBreakpoint = myRunToCursorBreakpoint;

      if (debugProcess.getRequestsManager().getWarning(myRunToCursorBreakpoint) == null) {
        super.contextAction();
      }
      else {
        myDebugProcessDispatcher.getMulticaster().resumed(getSuspendContext());
        DebuggerInvocationUtil.swingInvokeLater(myProject, new Runnable() {
          @Override
          public void run() {
            SourcePosition position = myRunToCursorBreakpoint.getSourcePosition();
            String name = position != null ? position.getFile().getName() : "<No File>";
            Messages.showErrorDialog(
              DebuggerBundle.message("error.running.to.cursor.no.executable.code", name, myRunToCursorBreakpoint.getLineIndex()+1),
              UIUtil.removeMnemonic(ActionsBundle.actionText(XDebuggerActions.RUN_TO_CURSOR)));
          }
        });
      }
    }
  }

  public abstract class ResumeCommand extends SuspendContextCommandImpl {

    private final ThreadReferenceProxyImpl myContextThread;

    public ResumeCommand(SuspendContextImpl suspendContext) {
      super(suspendContext);
      final ThreadReferenceProxyImpl contextThread = getDebuggerContext().getThreadProxy();
      myContextThread = contextThread != null ? contextThread : (suspendContext != null? suspendContext.getThread() : null);
    }

    @Override
    public Priority getPriority() {
      return Priority.HIGH;
    }

    @Override
    public void contextAction() {
      showStatusText(DebuggerBundle.message("status.process.resumed"));
      getSuspendManager().resume(getSuspendContext());
      myDebugProcessDispatcher.getMulticaster().resumed(getSuspendContext());
    }

    public ThreadReferenceProxyImpl getContextThread() {
      return myContextThread;
    }

    protected void applyThreadFilter(ThreadReferenceProxy thread) {
      if (getSuspendContext().getSuspendPolicy() == EventRequest.SUSPEND_ALL) {
        // there could be explicit resume as a result of call to voteSuspend()
        // e.g. when breakpoint was considered invalid, in that case the filter will be applied _after_
        // resuming and all breakpoints in other threads will be ignored.
        // As resume() implicitly cleares the filter, the filter must be always applied _before_ any resume() action happens
        final BreakpointManager breakpointManager = DebuggerManagerEx.getInstanceEx(getProject()).getBreakpointManager();
        breakpointManager.applyThreadFilter(DebugProcessImpl.this, thread.getThreadReference());
      }
    }
  }

  private class PauseCommand extends DebuggerCommandImpl {
    public PauseCommand() {
    }

    @Override
    public void action() {
      if (!isAttached() || getVirtualMachineProxy().isPausePressed()) {
        return;
      }
      logThreads();
      getVirtualMachineProxy().suspend();
      logThreads();
      SuspendContextImpl suspendContext = mySuspendManager.pushSuspendContext(EventRequest.SUSPEND_ALL, 0);
      myDebugProcessDispatcher.getMulticaster().paused(suspendContext);
    }
  }

  private class ResumeThreadCommand extends SuspendContextCommandImpl {
    private final ThreadReferenceProxyImpl myThread;

    public ResumeThreadCommand(SuspendContextImpl suspendContext, ThreadReferenceProxyImpl thread) {
      super(suspendContext);
      myThread = thread;
    }

    @Override
    public void contextAction() {
      if (getSuspendManager().isFrozen(myThread)) {
        getSuspendManager().unfreezeThread(myThread);
        return;
      }

      final Set<SuspendContextImpl> suspendingContexts = SuspendManagerUtil.getSuspendingContexts(getSuspendManager(), myThread);
      for (SuspendContextImpl suspendContext : suspendingContexts) {
        if (suspendContext.getThread() == myThread) {
          getManagerThread().invoke(createResumeCommand(suspendContext));
        }
        else {
          getSuspendManager().resumeThread(suspendContext, myThread);
        }
      }
    }
  }

  private class FreezeThreadCommand extends DebuggerCommandImpl {
    private final ThreadReferenceProxyImpl myThread;

    public FreezeThreadCommand(ThreadReferenceProxyImpl thread) {
      myThread = thread;
    }

    @Override
    protected void action() throws Exception {
      SuspendManager suspendManager = getSuspendManager();
      if (!suspendManager.isFrozen(myThread)) {
        suspendManager.freezeThread(myThread);
      }
    }
  }

  private class PopFrameCommand extends SuspendContextCommandImpl {
    private final StackFrameProxyImpl myStackFrame;

    public PopFrameCommand(SuspendContextImpl context, StackFrameProxyImpl frameProxy) {
      super(context);
      myStackFrame = frameProxy;
    }

    @Override
    public void contextAction() {
      final ThreadReferenceProxyImpl thread = myStackFrame.threadProxy();
      try {
        if (!getSuspendManager().isSuspended(thread)) {
          notifyCancelled();
          return;
        }
      }
      catch (ObjectCollectedException ignored) {
        notifyCancelled();
        return;
      }

      final SuspendContextImpl suspendContext = getSuspendContext();
      if (!suspendContext.suspends(thread)) {
        suspendContext.postponeCommand(this);
        return;
      }

      if (myStackFrame.isBottom()) {
        DebuggerInvocationUtil.swingInvokeLater(myProject, new Runnable() {
          @Override
          public void run() {
            Messages.showMessageDialog(myProject, DebuggerBundle.message("error.pop.bottom.stackframe"), ActionsBundle.actionText(DebuggerActions.POP_FRAME), Messages.getErrorIcon());
          }
        });
        return;
      }

      try {
        thread.popFrames(myStackFrame);
      }
      catch (final EvaluateException e) {
        DebuggerInvocationUtil.swingInvokeLater(myProject, new Runnable() {
          @Override
          public void run() {
            Messages.showMessageDialog(myProject, DebuggerBundle.message("error.pop.stackframe", e.getLocalizedMessage()), ActionsBundle.actionText(DebuggerActions.POP_FRAME), Messages.getErrorIcon());
          }
        });
        LOG.info(e);
      }
      finally {
        getSuspendManager().popFrame(suspendContext);
      }
    }
  }

  @Override
  @NotNull
  public GlobalSearchScope getSearchScope() {
    LOG.assertTrue(mySession != null, "Accessing debug session before its initialization");
    return mySession.getSearchScope();
  }

  public void reattach(final DebugEnvironment environment) throws ExecutionException {
    ApplicationManager.getApplication().assertIsDispatchThread(); //TODO: remove this requirement
    ((XDebugSessionImpl)getXdebugProcess().getSession()).reset();
    myState.set(STATE_INITIAL);
    getManagerThread().schedule(new DebuggerCommandImpl() {
      @Override
      protected void action() throws Exception {
        myRequestManager.processDetached(DebugProcessImpl.this, false);
      }
    });
    myConnection = environment.getRemoteConnection();
    getManagerThread().restartIfNeeded();
    createVirtualMachine(environment.getSessionName(), environment.isPollConnection());
  }

  @Nullable
  public ExecutionResult attachVirtualMachine(final DebugEnvironment environment,
                                              final DebuggerSession session) throws ExecutionException {
    mySession = session;
    myWaitFor.down();

    ApplicationManager.getApplication().assertIsDispatchThread();
    LOG.assertTrue(isInInitialState());

    myConnection = environment.getRemoteConnection();

    createVirtualMachine(environment.getSessionName(), environment.isPollConnection());

    ExecutionResult executionResult;
    try {
      synchronized (myProcessListeners) {
        executionResult = environment.createExecutionResult();
        myExecutionResult = executionResult;
        if (executionResult == null) {
          fail();
          return null;
        }
        for (ProcessListener processListener : myProcessListeners) {
          executionResult.getProcessHandler().addProcessListener(processListener);
        }
        myProcessListeners.clear();
      }
    }
    catch (ExecutionException e) {
      fail();
      throw e;
    }

    // writing to volatile field ensures the other threads will see the right values in non-volatile fields

    if (ApplicationManager.getApplication().isUnitTestMode()) {
      return executionResult;
    }

    /*
    final Alarm debugPortTimeout = new Alarm(Alarm.ThreadToUse.SHARED_THREAD);

    myExecutionResult.getProcessHandler().addProcessListener(new ProcessAdapter() {
      public void processTerminated(ProcessEvent event) {
        debugPortTimeout.cancelAllRequests();
      }

      public void startNotified(ProcessEvent event) {
        debugPortTimeout.addRequest(new Runnable() {
          public void run() {
            if(isInInitialState()) {
              ApplicationManager.getApplication().schedule(new Runnable() {
                public void run() {
                  String message = DebuggerBundle.message("status.connect.failed", DebuggerBundle.getAddressDisplayName(remoteConnection), DebuggerBundle.getTransportName(remoteConnection));
                  Messages.showErrorDialog(myProject, message, DebuggerBundle.message("title.generic.debug.dialog"));
                }
              });
            }
          }
        }, LOCAL_START_TIMEOUT);
      }
    });
    */

    return executionResult;
  }

  private void fail() {
    // need this in order to prevent calling stop() twice
    if (myIsFailed.compareAndSet(false, true)) {
      stop(false);
    }
  }

  private void createVirtualMachine(final String sessionName, final boolean pollConnection) {
    final Semaphore semaphore = new Semaphore();
    semaphore.down();

    final AtomicBoolean connectorIsReady = new AtomicBoolean(false);
    myDebugProcessDispatcher.addListener(new DebugProcessAdapter() {
      @Override
      public void connectorIsReady() {
        connectorIsReady.set(true);
        semaphore.up();
        myDebugProcessDispatcher.removeListener(this);
      }
    });

    // reload to make sure that source positions are initialized
    DebuggerManagerEx.getInstanceEx(myProject).getBreakpointManager().reloadBreakpoints();

    getManagerThread().schedule(new DebuggerCommandImpl() {
      @Override
      protected void action() {
        VirtualMachine vm = null;

        try {
          final long time = System.currentTimeMillis();
          while (System.currentTimeMillis() - time < LOCAL_START_TIMEOUT) {
            try {
              vm = createVirtualMachineInt();
              break;
            }
            catch (final ExecutionException e) {
              if (pollConnection && !myConnection.isServerMode() && e.getCause() instanceof IOException) {
                synchronized (this) {
                  try {
                    wait(500);
                  }
                  catch (InterruptedException ignored) {
                    break;
                  }
                }
              }
              else {
                fail();
                DebuggerInvocationUtil.swingInvokeLater(myProject, new Runnable() {
                  @Override
                  public void run() {
                    // propagate exception only in case we succeeded to obtain execution result,
                    // otherwise if the error is induced by the fact that there is nothing to debug, and there is no need to show
                    // this problem to the user
                    if (myExecutionResult != null || !connectorIsReady.get()) {
                      ExecutionUtil.handleExecutionError(myProject, ToolWindowId.DEBUG, sessionName, e);
                    }
                  }
                });
                break;
              }
            }
          }
        }
        finally {
          semaphore.up();
        }

        if (vm != null) {
          final VirtualMachine vm1 = vm;
          afterProcessStarted(new Runnable() {
            @Override
            public void run() {
              getManagerThread().schedule(new DebuggerCommandImpl() {
                @Override
                protected void action() throws Exception {
                  commitVM(vm1);
                }
              });
            }
          });
        }
      }

      @Override
      protected void commandCancelled() {
        try {
          super.commandCancelled();
        }
        finally {
          semaphore.up();
        }
      }
    });

    semaphore.waitFor();
  }

  private void afterProcessStarted(final Runnable run) {
    class MyProcessAdapter extends ProcessAdapter {
      private boolean alreadyRun = false;

      public synchronized void run() {
        if(!alreadyRun) {
          alreadyRun = true;
          run.run();
        }
        removeProcessListener(this);
      }

      @Override
      public void startNotified(ProcessEvent event) {
        run();
      }
    }
    MyProcessAdapter processListener = new MyProcessAdapter();
    addProcessListener(processListener);
    if (myExecutionResult != null) {
      if (myExecutionResult.getProcessHandler().isStartNotified()) {
        processListener.run();
      }
    }
  }

  public boolean isPausePressed() {
    final VirtualMachineProxyImpl vm = myVirtualMachineProxy;
    return vm != null && vm.isPausePressed();
  }

  public DebuggerCommandImpl createPauseCommand() {
    return new PauseCommand();
  }

  public ResumeCommand createResumeCommand(SuspendContextImpl suspendContext) {
    return createResumeCommand(suspendContext, PrioritizedTask.Priority.HIGH);
  }

  public ResumeCommand createResumeCommand(SuspendContextImpl suspendContext, final PrioritizedTask.Priority priority) {
    final BreakpointManager breakpointManager = DebuggerManagerEx.getInstanceEx(getProject()).getBreakpointManager();
    return new ResumeCommand(suspendContext) {
      @Override
      public void contextAction() {
        breakpointManager.applyThreadFilter(DebugProcessImpl.this, null); // clear the filter on resume
        super.contextAction();
      }

      @Override
      public Priority getPriority() {
        return priority;
      }
    };
  }

  public ResumeCommand createStepOverCommand(SuspendContextImpl suspendContext, boolean ignoreBreakpoints) {
    return createStepOverCommand(suspendContext, ignoreBreakpoints, StepRequest.STEP_LINE);
  }

  public ResumeCommand createStepOverCommand(SuspendContextImpl suspendContext, boolean ignoreBreakpoints, int stepSize) {
    return new StepOverCommand(suspendContext, ignoreBreakpoints, stepSize);
  }

  public ResumeCommand createStepOutCommand(SuspendContextImpl suspendContext) {
    return createStepOutCommand(suspendContext, StepRequest.STEP_LINE);
  }

  public ResumeCommand createStepOutCommand(SuspendContextImpl suspendContext, int stepSize) {
    return new StepOutCommand(suspendContext, stepSize);
  }

  public ResumeCommand createStepIntoCommand(SuspendContextImpl suspendContext, boolean ignoreFilters, final MethodFilter smartStepFilter) {
    return createStepIntoCommand(suspendContext, ignoreFilters, smartStepFilter, StepRequest.STEP_LINE);
  }

  public ResumeCommand createStepIntoCommand(SuspendContextImpl suspendContext, boolean ignoreFilters, final MethodFilter smartStepFilter,
                                             int stepSize) {
    return new StepIntoCommand(suspendContext, ignoreFilters, smartStepFilter, stepSize);
  }

  public ResumeCommand createRunToCursorCommand(SuspendContextImpl suspendContext, Document document, int lineIndex,
                                                            final boolean ignoreBreakpoints)
    throws EvaluateException {
    RunToCursorCommand runToCursorCommand = new RunToCursorCommand(suspendContext, document, lineIndex, ignoreBreakpoints);
    if(runToCursorCommand.myRunToCursorBreakpoint == null) {
      final PsiFile psiFile = PsiDocumentManager.getInstance(getProject()).getPsiFile(document);
      throw new EvaluateException(DebuggerBundle.message("error.running.to.cursor.no.executable.code", psiFile != null? psiFile.getName() : "<No File>", lineIndex), null);
    }
    return runToCursorCommand;
  }

  public DebuggerCommandImpl createFreezeThreadCommand(ThreadReferenceProxyImpl thread) {
    return new FreezeThreadCommand(thread);
  }

  public SuspendContextCommandImpl createResumeThreadCommand(SuspendContextImpl suspendContext, ThreadReferenceProxyImpl thread) {
    return new ResumeThreadCommand(suspendContext, thread);
  }

  public SuspendContextCommandImpl createPopFrameCommand(DebuggerContextImpl context, StackFrameProxyImpl stackFrame) {
    final SuspendContextImpl contextByThread =
      SuspendManagerUtil.findContextByThread(context.getDebugProcess().getSuspendManager(), stackFrame.threadProxy());
    return new PopFrameCommand(contextByThread, stackFrame);
  }

  //public void setBreakpointsMuted(final boolean muted) {
  //  XDebugSession session = mySession.getXDebugSession();
  //  if (isAttached()) {
  //    getManagerThread().schedule(new DebuggerCommandImpl() {
  //      @Override
  //      protected void action() throws Exception {
  //        // set the flag before enabling/disabling cause it affects if breakpoints will create requests
  //        if (myBreakpointsMuted.getAndSet(muted) != muted) {
  //          final BreakpointManager breakpointManager = DebuggerManagerEx.getInstanceEx(myProject).getBreakpointManager();
  //          if (muted) {
  //            breakpointManager.disableBreakpoints(DebugProcessImpl.this);
  //          }
  //          else {
  //            breakpointManager.enableBreakpoints(DebugProcessImpl.this);
  //          }
  //        }
  //      }
  //    });
  //  }
  //  else {
  //    session.setBreakpointMuted(muted);
  //  }
  //}

  public DebuggerContextImpl getDebuggerContext() {
    return mySession.getContextManager().getContext();
  }

  public void setXDebugProcess(JavaDebugProcess XDebugProcess) {
    myXDebugProcess = XDebugProcess;
  }

  @Nullable
  public JavaDebugProcess getXdebugProcess() {
    return myXDebugProcess;
  }

  public boolean areBreakpointsMuted() {
    XDebugSession session = mySession.getXDebugSession();
    return session != null && session.areBreakpointsMuted();
  }

  public DebuggerSession getSession() {
    return mySession;
  }
}


File: java/debugger/impl/src/com/intellij/debugger/engine/JavaDebugProcess.java
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
package com.intellij.debugger.engine;

import com.intellij.debugger.DebuggerBundle;
import com.intellij.debugger.actions.DebuggerActions;
import com.intellij.debugger.engine.evaluation.EvaluationContext;
import com.intellij.debugger.engine.events.DebuggerCommandImpl;
import com.intellij.debugger.engine.events.DebuggerContextCommandImpl;
import com.intellij.debugger.impl.*;
import com.intellij.debugger.jdi.StackFrameProxyImpl;
import com.intellij.debugger.settings.DebuggerSettings;
import com.intellij.debugger.ui.AlternativeSourceNotificationProvider;
import com.intellij.debugger.ui.DebuggerContentInfo;
import com.intellij.debugger.ui.breakpoints.Breakpoint;
import com.intellij.debugger.ui.impl.ThreadsPanel;
import com.intellij.debugger.ui.impl.watch.DebuggerTreeNodeImpl;
import com.intellij.debugger.ui.impl.watch.MessageDescriptor;
import com.intellij.debugger.ui.impl.watch.NodeManagerImpl;
import com.intellij.debugger.ui.tree.NodeDescriptor;
import com.intellij.execution.process.ProcessHandler;
import com.intellij.execution.ui.ExecutionConsole;
import com.intellij.execution.ui.ExecutionConsoleEx;
import com.intellij.execution.ui.RunnerLayoutUi;
import com.intellij.execution.ui.layout.PlaceInGrid;
import com.intellij.icons.AllIcons;
import com.intellij.openapi.actionSystem.*;
import com.intellij.openapi.editor.Document;
import com.intellij.openapi.extensions.Extensions;
import com.intellij.openapi.fileEditor.FileDocumentManager;
import com.intellij.openapi.project.Project;
import com.intellij.openapi.util.Disposer;
import com.intellij.openapi.util.Pair;
import com.intellij.openapi.vfs.VirtualFile;
import com.intellij.ui.EditorNotifications;
import com.intellij.ui.content.Content;
import com.intellij.ui.content.ContentManagerAdapter;
import com.intellij.ui.content.ContentManagerEvent;
import com.intellij.xdebugger.*;
import com.intellij.xdebugger.breakpoints.XBreakpoint;
import com.intellij.xdebugger.breakpoints.XBreakpointHandler;
import com.intellij.xdebugger.evaluation.XDebuggerEditorsProvider;
import com.intellij.xdebugger.frame.XStackFrame;
import com.intellij.xdebugger.frame.XValueMarkerProvider;
import com.intellij.xdebugger.impl.XDebugSessionImpl;
import com.intellij.xdebugger.impl.XDebuggerUtilImpl;
import com.intellij.xdebugger.ui.XDebugTabLayouter;
import com.sun.jdi.event.Event;
import org.jetbrains.annotations.NotNull;
import org.jetbrains.annotations.Nullable;
import org.jetbrains.java.debugger.JavaDebuggerEditorsProvider;

import java.util.ArrayList;
import java.util.List;

/**
 * @author egor
 */
public class JavaDebugProcess extends XDebugProcess {
  private final DebuggerSession myJavaSession;
  private final JavaDebuggerEditorsProvider myEditorsProvider;
  private final XBreakpointHandler<?>[] myBreakpointHandlers;
  private final NodeManagerImpl myNodeManager;

  public static JavaDebugProcess create(@NotNull final XDebugSession session, final DebuggerSession javaSession) {
    JavaDebugProcess res = new JavaDebugProcess(session, javaSession);
    javaSession.getProcess().setXDebugProcess(res);
    return res;
  }

  protected JavaDebugProcess(@NotNull final XDebugSession session, final DebuggerSession javaSession) {
    super(session);
    myJavaSession = javaSession;
    myEditorsProvider = new JavaDebuggerEditorsProvider();
    final DebugProcessImpl process = javaSession.getProcess();

    List<XBreakpointHandler> handlers = new ArrayList<XBreakpointHandler>();
    handlers.add(new JavaBreakpointHandler.JavaLineBreakpointHandler(process));
    handlers.add(new JavaBreakpointHandler.JavaExceptionBreakpointHandler(process));
    handlers.add(new JavaBreakpointHandler.JavaFieldBreakpointHandler(process));
    handlers.add(new JavaBreakpointHandler.JavaMethodBreakpointHandler(process));
    handlers.add(new JavaBreakpointHandler.JavaWildcardBreakpointHandler(process));

    for (JavaBreakpointHandlerFactory factory : Extensions.getExtensions(JavaBreakpointHandlerFactory.EP_NAME)) {
      handlers.add(factory.createHandler(process));
    }

    myBreakpointHandlers = handlers.toArray(new XBreakpointHandler[handlers.size()]);

    myJavaSession.getContextManager().addListener(new DebuggerContextListener() {
      @Override
      public void changeEvent(final DebuggerContextImpl newContext, int event) {
        if (event == DebuggerSession.EVENT_PAUSE
            || event == DebuggerSession.EVENT_CONTEXT
            || event == DebuggerSession.EVENT_REFRESH
               && myJavaSession.isPaused()) {
          if (getSession().getSuspendContext() != newContext.getSuspendContext()) {
            process.getManagerThread().schedule(new DebuggerContextCommandImpl(newContext) {
              @Override
              public void threadAction() {
                SuspendContextImpl context = newContext.getSuspendContext();
                if (context != null) {
                  context.initExecutionStacks(newContext.getThreadProxy());

                  List<Pair<Breakpoint, Event>> descriptors =
                    DebuggerUtilsEx.getEventDescriptors(context);
                  if (!descriptors.isEmpty()) {
                    Breakpoint breakpoint = descriptors.get(0).getFirst();
                    XBreakpoint xBreakpoint = breakpoint.getXBreakpoint();
                    if (xBreakpoint != null) {
                      ((XDebugSessionImpl)getSession()).breakpointReachedNoProcessing(xBreakpoint, context);
                      return;
                    }
                  }
                  getSession().positionReached(context);
                }
              }
            });
          }
        }
        else if (event == DebuggerSession.EVENT_ATTACHED) {
          getSession().rebuildViews(); // to refresh variables views message
        }
      }
    });

    myNodeManager = new NodeManagerImpl(session.getProject(), null) {
      @Override
      public DebuggerTreeNodeImpl createNode(final NodeDescriptor descriptor, EvaluationContext evaluationContext) {
        return new DebuggerTreeNodeImpl(null, descriptor);
      }

      @Override
      public DebuggerTreeNodeImpl createMessageNode(MessageDescriptor descriptor) {
        return new DebuggerTreeNodeImpl(null, descriptor);
      }

      @Override
      public DebuggerTreeNodeImpl createMessageNode(String message) {
        return new DebuggerTreeNodeImpl(null, new MessageDescriptor(message));
      }
    };
    session.addSessionListener(new XDebugSessionAdapter() {
      @Override
      public void sessionPaused() {
        saveNodeHistory();
        showAlternativeNotification(session.getCurrentStackFrame());
      }

      @Override
      public void stackFrameChanged() {
        XStackFrame frame = session.getCurrentStackFrame();
        if (frame instanceof JavaStackFrame) {
          showAlternativeNotification(frame);
          StackFrameProxyImpl frameProxy = ((JavaStackFrame)frame).getStackFrameProxy();
          DebuggerContextUtil.setStackFrame(javaSession.getContextManager(), frameProxy);
          saveNodeHistory(frameProxy);
        }
      }

      private void showAlternativeNotification(XStackFrame frame) {
        XSourcePosition position = frame.getSourcePosition();
        if (position != null) {
          VirtualFile file = position.getFile();
          if (!AlternativeSourceNotificationProvider.fileProcessed(file)) {
            EditorNotifications.getInstance(session.getProject()).updateNotifications(file);
          }
        }
      }
    });
  }

  public void saveNodeHistory() {
    saveNodeHistory(getDebuggerStateManager().getContext().getFrameProxy());
  }

  private void saveNodeHistory(final StackFrameProxyImpl frameProxy) {
    myJavaSession.getProcess().getManagerThread().invoke(new DebuggerCommandImpl() {
      @Override
      protected void action() throws Exception {
        myNodeManager.setHistoryByContext(frameProxy);
      }

      @Override
      public Priority getPriority() {
        return Priority.NORMAL;
      }
    });
  }

  private DebuggerStateManager getDebuggerStateManager() {
    return myJavaSession.getContextManager();
  }

  public DebuggerSession getDebuggerSession() {
    return myJavaSession;
  }

  @NotNull
  @Override
  public XDebuggerEditorsProvider getEditorsProvider() {
    return myEditorsProvider;
  }

  @Override
  public void startStepOver() {
    myJavaSession.stepOver(false);
  }

  @Override
  public void startStepInto() {
    myJavaSession.stepInto(false, null);
  }

  @Override
  public void startForceStepInto() {
    myJavaSession.stepInto(true, null);
  }

  @Override
  public void startStepOut() {
    myJavaSession.stepOut();
  }

  @Override
  public void stop() {
    myJavaSession.dispose();
    myNodeManager.dispose();
  }

  @Override
  public void startPausing() {
    myJavaSession.pause();
  }

  @Override
  public void resume() {
    myJavaSession.resume();
  }

  @Override
  public void runToPosition(@NotNull XSourcePosition position) {
    Document document = FileDocumentManager.getInstance().getDocument(position.getFile());
    myJavaSession.runToCursor(document, position.getLine(), false);
  }

  @NotNull
  @Override
  public XBreakpointHandler<?>[] getBreakpointHandlers() {
    return myBreakpointHandlers;
  }

  @Override
  public boolean checkCanInitBreakpoints() {
    return false;
  }

  @Nullable
  @Override
  protected ProcessHandler doGetProcessHandler() {
    return myJavaSession.getProcess().getProcessHandler();
  }

  @NotNull
  @Override
  public ExecutionConsole createConsole() {
    ExecutionConsole console = myJavaSession.getProcess().getExecutionResult().getExecutionConsole();
    if (console != null) return console;
    return super.createConsole();
  }

  @NotNull
  @Override
  public XDebugTabLayouter createTabLayouter() {
    return new XDebugTabLayouter() {
      @Override
      public void registerAdditionalContent(@NotNull RunnerLayoutUi ui) {
        final ThreadsPanel panel = new ThreadsPanel(myJavaSession.getProject(), getDebuggerStateManager());
        final Content threadsContent = ui.createContent(
          DebuggerContentInfo.THREADS_CONTENT, panel, XDebuggerBundle.message("debugger.session.tab.threads.title"),
          AllIcons.Debugger.Threads, null);
        Disposer.register(threadsContent, panel);
        threadsContent.setCloseable(false);
        ui.addContent(threadsContent, 0, PlaceInGrid.left, true);
        ui.addListener(new ContentManagerAdapter() {
          @Override
          public void selectionChanged(ContentManagerEvent event) {
            if (event.getContent() == threadsContent) {
              if (threadsContent.isSelected()) {
                panel.setUpdateEnabled(true);
                if (panel.isRefreshNeeded()) {
                  panel.rebuildIfVisible(DebuggerSession.EVENT_CONTEXT);
                }
              }
              else {
                panel.setUpdateEnabled(false);
              }
            }
          }
        }, threadsContent);
      }

      @NotNull
      @Override
      public Content registerConsoleContent(@NotNull RunnerLayoutUi ui, @NotNull ExecutionConsole console) {
        Content content = null;
        if (console instanceof ExecutionConsoleEx) {
          ((ExecutionConsoleEx)console).buildUi(ui);
          content = ui.findContent(DebuggerContentInfo.CONSOLE_CONTENT);
        }
        if (content == null) {
          content = super.registerConsoleContent(ui, console);
        }
        return content;
      }
    };
  }

  @Override
  public void registerAdditionalActions(@NotNull DefaultActionGroup leftToolbar, @NotNull DefaultActionGroup topToolbar, @NotNull DefaultActionGroup settings) {
    Constraints beforeRunner = new Constraints(Anchor.BEFORE, "Runner.Layout");
    leftToolbar.add(Separator.getInstance(), beforeRunner);
    leftToolbar.add(ActionManager.getInstance().getAction(DebuggerActions.DUMP_THREADS), beforeRunner);
    leftToolbar.add(Separator.getInstance(), beforeRunner);

    Constraints beforeSort = new Constraints(Anchor.BEFORE, "XDebugger.ToggleSortValues");
    settings.addAction(new WatchLastMethodReturnValueAction(), beforeSort);
    settings.addAction(new AutoVarsSwitchAction(), beforeSort);
  }

  private static class AutoVarsSwitchAction extends ToggleAction {
    private volatile boolean myAutoModeEnabled;

    public AutoVarsSwitchAction() {
      super(DebuggerBundle.message("action.auto.variables.mode"), DebuggerBundle.message("action.auto.variables.mode.description"), null);
      myAutoModeEnabled = DebuggerSettings.getInstance().AUTO_VARIABLES_MODE;
    }

    @Override
    public boolean isSelected(AnActionEvent e) {
      return myAutoModeEnabled;
    }

    @Override
    public void setSelected(AnActionEvent e, boolean enabled) {
      myAutoModeEnabled = enabled;
      DebuggerSettings.getInstance().AUTO_VARIABLES_MODE = enabled;
      XDebuggerUtilImpl.rebuildAllSessionsViews(e.getProject());
    }
  }

  private static class WatchLastMethodReturnValueAction extends ToggleAction {
    private volatile boolean myWatchesReturnValues;
    private final String myText;
    private final String myTextUnavailable;

    public WatchLastMethodReturnValueAction() {
      super("", DebuggerBundle.message("action.watch.method.return.value.description"), null);
      myWatchesReturnValues = DebuggerSettings.getInstance().WATCH_RETURN_VALUES;
      myText = DebuggerBundle.message("action.watches.method.return.value.enable");
      myTextUnavailable = DebuggerBundle.message("action.watches.method.return.value.unavailable.reason");
    }

    @Override
    public void update(@NotNull final AnActionEvent e) {
      super.update(e);
      final Presentation presentation = e.getPresentation();
      DebugProcessImpl process = getCurrentDebugProcess(e.getProject());
      if (process == null || process.canGetMethodReturnValue()) {
        presentation.setEnabled(true);
        presentation.setText(myText);
      }
      else {
        presentation.setEnabled(false);
        presentation.setText(myTextUnavailable);
      }
    }

    @Override
    public boolean isSelected(AnActionEvent e) {
      return myWatchesReturnValues;
    }

    @Override
    public void setSelected(AnActionEvent e, boolean watch) {
      myWatchesReturnValues = watch;
      DebuggerSettings.getInstance().WATCH_RETURN_VALUES = watch;
      DebugProcessImpl process = getCurrentDebugProcess(e.getProject());
      if (process != null) {
        process.setWatchMethodReturnValuesEnabled(watch);
      }
    }
  }

  @Nullable
  private static DebugProcessImpl getCurrentDebugProcess(@Nullable Project project) {
    if (project != null) {
      XDebugSession session = XDebuggerManager.getInstance(project).getCurrentSession();
      if (session != null) {
        XDebugProcess process = session.getDebugProcess();
        if (process instanceof JavaDebugProcess) {
          return ((JavaDebugProcess)process).getDebuggerSession().getProcess();
        }
      }
    }
    return null;
  }

  public NodeManagerImpl getNodeManager() {
    return myNodeManager;
  }

  @Override
  public String getCurrentStateMessage() {
    String description = myJavaSession.getStateDescription();
    return description != null ? description : super.getCurrentStateMessage();
  }

  @Nullable
  @Override
  public XValueMarkerProvider<?, ?> createValueMarkerProvider() {
    return new JavaValueMarker();
  }
}


File: java/debugger/impl/src/com/intellij/debugger/engine/PositionManagerImpl.java
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
package com.intellij.debugger.engine;

import com.intellij.debugger.MultiRequestPositionManager;
import com.intellij.debugger.NoDataException;
import com.intellij.debugger.PositionManager;
import com.intellij.debugger.SourcePosition;
import com.intellij.debugger.engine.evaluation.EvaluateException;
import com.intellij.debugger.jdi.VirtualMachineProxyImpl;
import com.intellij.debugger.requests.ClassPrepareRequestor;
import com.intellij.execution.filters.LineNumbersMapping;
import com.intellij.openapi.application.ApplicationManager;
import com.intellij.openapi.diagnostic.Logger;
import com.intellij.openapi.editor.Document;
import com.intellij.openapi.editor.impl.DocumentMarkupModel;
import com.intellij.openapi.editor.markup.HighlighterTargetArea;
import com.intellij.openapi.editor.markup.RangeHighlighter;
import com.intellij.openapi.editor.markup.TextAttributes;
import com.intellij.openapi.project.Project;
import com.intellij.openapi.util.*;
import com.intellij.openapi.util.text.StringUtil;
import com.intellij.openapi.vfs.VirtualFile;
import com.intellij.psi.*;
import com.intellij.psi.search.FilenameIndex;
import com.intellij.psi.search.GlobalSearchScope;
import com.intellij.psi.util.PsiTreeUtil;
import com.intellij.util.containers.ContainerUtil;
import com.intellij.util.containers.EmptyIterable;
import com.intellij.xdebugger.impl.ui.ExecutionPointHighlighter;
import com.intellij.xdebugger.ui.DebuggerColors;
import com.sun.jdi.AbsentInformationException;
import com.sun.jdi.Location;
import com.sun.jdi.Method;
import com.sun.jdi.ReferenceType;
import com.sun.jdi.request.ClassPrepareRequest;
import org.jetbrains.annotations.NotNull;
import org.jetbrains.annotations.Nullable;

import java.util.*;

/**
 * @author lex
 */
public class PositionManagerImpl implements PositionManager, MultiRequestPositionManager {
  private static final Logger LOG = Logger.getInstance("#com.intellij.debugger.engine.PositionManagerImpl");

  private final DebugProcessImpl myDebugProcess;

  public PositionManagerImpl(DebugProcessImpl debugProcess) {
    myDebugProcess = debugProcess;
  }

  public DebugProcess getDebugProcess() {
    return myDebugProcess;
  }

  @NotNull
  public List<Location> locationsOfLine(@NotNull ReferenceType type, @NotNull SourcePosition position) throws NoDataException {
    try {
      final int line = position.getLine() + 1;
      return type.locationsOfLine(DebugProcess.JAVA_STRATUM, null, line);
    }
    catch (AbsentInformationException ignored) {
    }
    return Collections.emptyList();
  }

  public ClassPrepareRequest createPrepareRequest(@NotNull final ClassPrepareRequestor requestor, @NotNull final SourcePosition position)
    throws NoDataException {
    throw new IllegalStateException("This class implements MultiRequestPositionManager, corresponding createPrepareRequests version should be used");
  }

  @NotNull
  @Override
  public List<ClassPrepareRequest> createPrepareRequests(@NotNull final ClassPrepareRequestor requestor, @NotNull final SourcePosition position)
    throws NoDataException {
    return ApplicationManager.getApplication().runReadAction(new Computable<List<ClassPrepareRequest>>() {
      @Override
      public List<ClassPrepareRequest> compute() {
        List<ClassPrepareRequest> res = new ArrayList<ClassPrepareRequest>();
        for (PsiClass psiClass : getLineClasses(position.getFile(), position.getLine())) {
          ClassPrepareRequestor prepareRequestor = requestor;
          String classPattern = JVMNameUtil.getNonAnonymousClassName(psiClass);
          if (classPattern == null) {
            final PsiClass parent = JVMNameUtil.getTopLevelParentClass(psiClass);
            if (parent == null) {
              continue;
            }
            final String parentQName = JVMNameUtil.getNonAnonymousClassName(parent);
            if (parentQName == null) {
              continue;
            }
            classPattern = parentQName + "*";
            prepareRequestor = new ClassPrepareRequestor() {
              public void processClassPrepare(DebugProcess debuggerProcess, ReferenceType referenceType) {
                final CompoundPositionManager positionManager = ((DebugProcessImpl)debuggerProcess).getPositionManager();
                final List<ReferenceType> positionClasses = positionManager.getAllClasses(position);
                if (positionClasses.contains(referenceType)) {
                  requestor.processClassPrepare(debuggerProcess, referenceType);
                }
              }
            };
          }
          res.add(myDebugProcess.getRequestsManager().createClassPrepareRequest(prepareRequestor, classPattern));
        }
        return res;
      }
    });
  }

  public SourcePosition getSourcePosition(final Location location) throws NoDataException {
    DebuggerManagerThreadImpl.assertIsManagerThread();
    if(location == null) {
      return null;
    }

    PsiFile psiFile = getPsiFileByLocation(getDebugProcess().getProject(), location);
    if(psiFile == null ) {
      return null;
    }

    LOG.assertTrue(myDebugProcess != null);

    int lineNumber;
    try {
      lineNumber = location.lineNumber() - 1;
    }
    catch (InternalError e) {
      lineNumber = -1;
    }

    if (lineNumber > -1) {
      SourcePosition position = calcLineMappedSourcePosition(psiFile, lineNumber);
      if (position != null) {
        return position;
      }
    }

    Method method = location.method();

    if (psiFile instanceof PsiCompiledElement || lineNumber < 0) {
      final String methodSignature = method.signature();
      if (methodSignature == null) {
        return SourcePosition.createFromLine(psiFile, -1);
      }
      final String methodName = method.name();
      if (methodName == null) {
        return SourcePosition.createFromLine(psiFile, -1);
      }
      if (location.declaringType() == null) {
        return SourcePosition.createFromLine(psiFile, -1);
      }

      final MethodFinder finder = new MethodFinder(location.declaringType().name(), methodName, methodSignature);
      psiFile.accept(finder);

      final PsiMethod compiledMethod = finder.getCompiledMethod();
      if (compiledMethod == null) {
        return SourcePosition.createFromLine(psiFile, -1);
      }
      SourcePosition sourcePosition = SourcePosition.createFromElement(compiledMethod);
      if (lineNumber >= 0) {
        sourcePosition = new ClsSourcePosition(sourcePosition, lineNumber);
      }
      return sourcePosition;
    }

    SourcePosition sourcePosition = SourcePosition.createFromLine(psiFile, lineNumber);
    int lambdaOrdinal = -1;
    if (LambdaMethodFilter.isLambdaName(method.name())) {
      List<Location> lambdas = ContainerUtil.filter(locationsOfLine(location.declaringType(), sourcePosition), new Condition<Location>() {
        @Override
        public boolean value(Location location) {
          return LambdaMethodFilter.isLambdaName(location.method().name());
        }
      });
      if (lambdas.size() > 1) {
        Collections.sort(lambdas, new Comparator<Location>() {
          @Override
          public int compare(Location o1, Location o2) {
            return LambdaMethodFilter.getLambdaOrdinal(o1.method().name()) - LambdaMethodFilter.getLambdaOrdinal(o2.method().name());
          }
        });
        lambdaOrdinal = lambdas.indexOf(location);
      }
    }
    return new JavaSourcePosition(sourcePosition, location.declaringType(), method, lambdaOrdinal);
  }

  private static class JavaSourcePosition extends RemappedSourcePosition implements ExecutionPointHighlighter.HighlighterProvider {
    private final String myExpectedClassName;
    private final String myExpectedMethodName;
    private final int myLambdaOrdinal;

    public JavaSourcePosition(SourcePosition delegate, ReferenceType declaringType, Method method, int lambdaOrdinal) {
      super(delegate);
      myExpectedClassName = declaringType != null ? declaringType.name() : null;
      myExpectedMethodName = method != null ? method.name() : null;
      myLambdaOrdinal = lambdaOrdinal;
    }

    private PsiElement remapElement(PsiElement element) {
      PsiClass aClass = getEnclosingClass(element);
      if (!Comparing.equal(myExpectedClassName, JVMNameUtil.getClassVMName(aClass))) {
        return null;
      }
      NavigatablePsiElement method = PsiTreeUtil.getParentOfType(element, PsiMethod.class, PsiLambdaExpression.class);
      if (!StringUtil.isEmpty(myExpectedMethodName)) {
        if (method == null) {
          return null;
        }
        else if ((method instanceof PsiMethod && myExpectedMethodName.equals(((PsiMethod)method).getName()))) {
          if (insideBody(element, ((PsiMethod)method).getBody())) return element;
        }
        //else if (method instanceof PsiLambdaExpression && (myLambdaOrdinal < 0 || myLambdaOrdinal == lambdaOrdinal)
        //         && LambdaMethodFilter.isLambdaName(myExpectedMethodName)) {
        //  if (insideBody(element, ((PsiLambdaExpression)method).getBody())) return element;
        //}
      }
      return null;
    }

    private static boolean insideBody(@NotNull PsiElement element, @Nullable PsiElement body) {
      if (!PsiTreeUtil.isAncestor(body, element, false)) return false;
      if (body instanceof PsiCodeBlock) {
        return !element.equals(((PsiCodeBlock)body).getRBrace()) && !element.equals(((PsiCodeBlock)body).getLBrace());
      }
      return true;
    }

    @Override
    public SourcePosition mapDelegate(final SourcePosition original) {
      return ApplicationManager.getApplication().runReadAction(new Computable<SourcePosition>() {
        @Override
        public SourcePosition compute() {
          PsiFile file = original.getFile();
          int line = original.getLine();
          if (LambdaMethodFilter.isLambdaName(myExpectedMethodName) && myLambdaOrdinal > -1) {
            Document document = PsiDocumentManager.getInstance(file.getProject()).getDocument(file);
            if (document == null || line >= document.getLineCount()) {
              return original;
            }
            PsiElement element = original.getElementAt();
            TextRange lineRange = new TextRange(document.getLineStartOffset(line), document.getLineEndOffset(line));
            do {
              PsiElement parent = element.getParent();
              if (parent == null || (parent.getTextOffset() < lineRange.getStartOffset())) {
                break;
              }
              element = parent;
            }
            while(true);
            final List<PsiLambdaExpression> lambdas = new ArrayList<PsiLambdaExpression>(3);
            // add initial lambda if we're inside already
            NavigatablePsiElement method = PsiTreeUtil.getParentOfType(element, PsiMethod.class, PsiLambdaExpression.class);
            if (method instanceof PsiLambdaExpression) {
              lambdas.add((PsiLambdaExpression)method);
            }
            final PsiElementVisitor lambdaCollector = new JavaRecursiveElementVisitor() {
              @Override
              public void visitLambdaExpression(PsiLambdaExpression expression) {
                super.visitLambdaExpression(expression);
                lambdas.add(expression);
              }
            };
            element.accept(lambdaCollector);
            for (PsiElement sibling = getNextElement(element); sibling != null; sibling = getNextElement(sibling)) {
              if (!lineRange.intersects(sibling.getTextRange())) {
                break;
              }
              sibling.accept(lambdaCollector);
            }
            if (myLambdaOrdinal < lambdas.size()) {
              PsiElement body = lambdas.get(myLambdaOrdinal).getBody();
              if (body instanceof PsiCodeBlock) {
                for (PsiStatement statement : ((PsiCodeBlock)body).getStatements()) {
                  if (lineRange.intersects(statement.getTextRange())) {
                    body = statement;
                    break;
                  }
                }
              }
              return SourcePosition.createFromElement(body);
            }
          }
          else {
            // There may be more than one class/method code on the line, so we need to find out the correct place
            for (PsiElement elem : getLineElements(file, line)) {
              PsiElement remappedElement = remapElement(elem);
              if (remappedElement != null) {
                if (remappedElement.getTextOffset() <= original.getOffset()) break;
                return SourcePosition.createFromElement(remappedElement);
              }
            }
          }
          return original;
        }
      });
    }

    private static PsiElement getNextElement(PsiElement element) {
      PsiElement sibling = element.getNextSibling();
      if (sibling != null) return sibling;
      element = element.getParent();
      if (element != null) return getNextElement(element);
      return null;
    }

    @Nullable
    @Override
    public RangeHighlighter createHighlighter(Document document, Project project, TextAttributes attributes) {
      PsiElement element = getElementAt();
      NavigatablePsiElement method = PsiTreeUtil.getParentOfType(element, PsiMethod.class, PsiLambdaExpression.class);
      if (method instanceof PsiLambdaExpression) {
        TextRange range = method.getTextRange();
        int startOffset = document.getLineStartOffset(getLine());
        int endOffset = document.getLineEndOffset(getLine());
        int hlStart = Math.max(startOffset, range.getStartOffset());
        int hlEnd = Math.min(endOffset, range.getEndOffset());
        if (hlStart != startOffset || hlEnd != endOffset) {
          return DocumentMarkupModel.forDocument(document, project, true).
            addRangeHighlighter(hlStart, hlEnd, DebuggerColors.EXECUTION_LINE_HIGHLIGHTERLAYER, attributes,
                                HighlighterTargetArea.EXACT_RANGE);
        }
      }
      return null;
    }
  }

  private static Iterable<PsiElement> getLineElements(final PsiFile file, int lineNumber) {
    ApplicationManager.getApplication().assertReadAccessAllowed();
    Document document = PsiDocumentManager.getInstance(file.getProject()).getDocument(file);
    if (document == null || lineNumber >= document.getLineCount()) {
      return EmptyIterable.getInstance();
    }
    final int startOffset = document.getLineStartOffset(lineNumber);
    final int endOffset = document.getLineEndOffset(lineNumber);
    return new Iterable<PsiElement>() {
      @Override
      public Iterator<PsiElement> iterator() {
        return new Iterator<PsiElement>() {
          PsiElement myElement = file.findElementAt(startOffset);

          @Override
          public boolean hasNext() {
            return myElement != null;
          }

          @Override
          public PsiElement next() {
            PsiElement res = myElement;
            do {
              myElement = PsiTreeUtil.nextLeaf(myElement);
              if (myElement == null || myElement.getTextOffset() > endOffset) {
                myElement = null;
                break;
              }
            } while (myElement.getTextLength() == 0);
            return res;
          }

          @Override
          public void remove() {}
        };
      }
    };
  }

  private static Set<PsiClass> getLineClasses(final PsiFile file, int lineNumber) {
    ApplicationManager.getApplication().assertReadAccessAllowed();
    Set<PsiClass> res = new HashSet<PsiClass>();
    for (PsiElement element : getLineElements(file, lineNumber)) {
      PsiClass aClass = getEnclosingClass(element);
      if (aClass != null) {
        res.add(aClass);
      }
    }
    return res;
  }

  @Nullable
  private PsiFile getPsiFileByLocation(final Project project, final Location location) {
    if (location == null) {
      return null;
    }
    final ReferenceType refType = location.declaringType();
    if (refType == null) {
      return null;
    }

    // We should find a class no matter what
    // setAlternativeResolveEnabled is turned on here
    //if (DumbService.getInstance(project).isDumb()) {
    //  return null;
    //}

    final String originalQName = refType.name();
    final GlobalSearchScope searchScope = myDebugProcess.getSearchScope();
    PsiClass psiClass = DebuggerUtils.findClass(originalQName, project, searchScope); // try to lookup original name first
    if (psiClass == null) {
      int dollar = originalQName.indexOf('$');
      if (dollar > 0) {
        final String qName = originalQName.substring(0, dollar);
        psiClass = DebuggerUtils.findClass(qName, project, searchScope);
      }
    }

    if (psiClass != null) {
      PsiElement element = psiClass.getNavigationElement();
      // see IDEA-137167, prefer not compiled elements
      if (element instanceof PsiCompiledElement) {
        PsiElement fileElement = psiClass.getContainingFile().getNavigationElement();
        if (!(fileElement instanceof PsiCompiledElement)) {
          element = fileElement;
        }
      }
      return element.getContainingFile();
    }
    else {
      // try to search by filename
      try {
        PsiFile[] files = FilenameIndex.getFilesByName(project, refType.sourceName(), GlobalSearchScope.allScope(project));
        for (PsiFile file : files) {
          if (file instanceof PsiJavaFile) {
            for (PsiClass cls : ((PsiJavaFile)file).getClasses()) {
              if (StringUtil.equals(originalQName, cls.getQualifiedName())) {
                return file;
              }
            }
          }
        }
      }
      catch (AbsentInformationException ignore) {
      }
    }

    return null;
  }

  @NotNull
  public List<ReferenceType> getAllClasses(@NotNull final SourcePosition position) throws NoDataException {
    return ApplicationManager.getApplication().runReadAction(new Computable<List<ReferenceType>>() {
      @Override
      public List<ReferenceType> compute() {
        List<ReferenceType> res = new ArrayList<ReferenceType>();
        for (PsiClass aClass : getLineClasses(position.getFile(), position.getLine())) {
          res.addAll(getClassReferences(aClass, position));
        }
        return res;
      }
    });
  }

  private List<ReferenceType> getClassReferences(@NotNull final PsiClass psiClass, SourcePosition position) {
    final Ref<String> baseClassNameRef = new Ref<String>(null);
    final Ref<PsiClass> classAtPositionRef = new Ref<PsiClass>(null);
    final Ref<Boolean> isLocalOrAnonymous = new Ref<Boolean>(Boolean.FALSE);
    final Ref<Integer> requiredDepth = new Ref<Integer>(0);
    ApplicationManager.getApplication().runReadAction(new Runnable() {
      public void run() {
        classAtPositionRef.set(psiClass);
        String className = JVMNameUtil.getNonAnonymousClassName(psiClass);
        if (className == null) {
          isLocalOrAnonymous.set(Boolean.TRUE);
          final PsiClass topLevelClass = JVMNameUtil.getTopLevelParentClass(psiClass);
          if (topLevelClass != null) {
            final String parentClassName = JVMNameUtil.getNonAnonymousClassName(topLevelClass);
            if (parentClassName != null) {
              requiredDepth.set(getNestingDepth(psiClass));
              baseClassNameRef.set(parentClassName);
            }
          }
          else {
            LOG.error("Local or anonymous class has no non-local parent");
          }
        }
        else {
          baseClassNameRef.set(className);
        }
      }
    });

    final String className = baseClassNameRef.get();
    if (className == null) {
      return Collections.emptyList();
    }

    if (!isLocalOrAnonymous.get()) {
      return myDebugProcess.getVirtualMachineProxy().classesByName(className);
    }
    
    // the name is a parent class for a local or anonymous class
    final List<ReferenceType> outers = myDebugProcess.getVirtualMachineProxy().classesByName(className);
    final List<ReferenceType> result = new ArrayList<ReferenceType>(outers.size());
    for (ReferenceType outer : outers) {
      final ReferenceType nested = findNested(outer, 0, classAtPositionRef.get(), requiredDepth.get(), position);
      if (nested != null) {
        result.add(nested);
      }
    }
    return result;
  }

  private static int getNestingDepth(PsiClass aClass) {
    int depth = 0;
    PsiClass enclosing = getEnclosingClass(aClass);
    while (enclosing != null) {
      depth++;
      enclosing = getEnclosingClass(enclosing);
    }
    return depth;
  }

  /**
   * See IDEA-121739
   * Anonymous classes inside other anonymous class parameters list should belong to parent class
   * Inner in = new Inner(new Inner2(){}) {};
   * Parent of Inner2 sub class here is not Inner sub class
   */
  @Nullable
  private static PsiClass getEnclosingClass(@Nullable PsiElement element) {
    if (element == null) {
      return null;
    }

    element = element.getParent();
    PsiElement previous = null;

    while (element != null) {
      if (PsiClass.class.isInstance(element) && !(previous instanceof PsiExpressionList)) {
        //noinspection unchecked
        return (PsiClass)element;
      }
      if (element instanceof PsiFile) {
        return null;
      }
      previous = element;
      element = element.getParent();
    }

    return null;
  }

  @Nullable
  private ReferenceType findNested(final ReferenceType fromClass, final int currentDepth, final PsiClass classToFind, final int requiredDepth, final SourcePosition position) {
    final VirtualMachineProxyImpl vmProxy = myDebugProcess.getVirtualMachineProxy();
    if (fromClass.isPrepared()) {
      try {
        if (currentDepth < requiredDepth) {
          final List<ReferenceType> nestedTypes = vmProxy.nestedTypes(fromClass);
          for (ReferenceType nested : nestedTypes) {
            final ReferenceType found = findNested(nested, currentDepth + 1, classToFind, requiredDepth, position);
            if (found != null) {
              return found;
            }
          }
          return null;
        }

        int rangeBegin = Integer.MAX_VALUE;
        int rangeEnd = Integer.MIN_VALUE;
        for (Location location : fromClass.allLineLocations()) {
          final int lnumber = location.lineNumber();
          if (lnumber <= 1) {
            // should be a native method, skipping
            // sometimes compiler generates location where line number is exactly 1 (e.g. GWT)
            // such locations are hardly correspond to real lines in code, so skipping them too
            continue;
          }
          final Method method = location.method();
          if (method == null || DebuggerUtils.isSynthetic(method) || method.isBridge()) {
            // do not take into account synthetic stuff
            continue;
          }
          int locationLine = lnumber - 1;
          PsiFile psiFile = position.getFile().getOriginalFile();
          if (psiFile instanceof PsiCompiledFile) {
            locationLine = bytecodeToSourceLine(psiFile, locationLine);
            if (locationLine < 0) continue;
          }
          rangeBegin = Math.min(rangeBegin,  locationLine);
          rangeEnd = Math.max(rangeEnd,  locationLine);
        }

        final int positionLine = position.getLine();
        if (positionLine >= rangeBegin && positionLine <= rangeEnd) {
          // choose the second line to make sure that only this class' code exists on the line chosen
          // Otherwise the line (depending on the offset in it) can contain code that belongs to different classes
          // and JVMNameUtil.getClassAt(candidatePosition) will return the wrong class.
          // Example of such line:
          // list.add(new Runnable(){......
          // First offsets belong to parent class, and offsets inside te substring "new Runnable(){" belong to anonymous runnable.
          final int finalRangeBegin = rangeBegin;
          final int finalRangeEnd = rangeEnd;
          return ApplicationManager.getApplication().runReadAction(new NullableComputable<ReferenceType>() {
            public ReferenceType compute() {
              if (!classToFind.isValid()) {
                return null;
              }
              final int line = Math.min(finalRangeBegin + 1, finalRangeEnd);
              Set<PsiClass> lineClasses = getLineClasses(position.getFile(), line);
              if (lineClasses.size() > 1) {
                // if there's more than one class on the line - try to match by name
                for (PsiClass aClass : lineClasses) {
                  if (classToFind.equals(aClass)) {
                    return fromClass;
                  }
                }
              }
              else if (!lineClasses.isEmpty()){
                return classToFind.equals(lineClasses.iterator().next())? fromClass : null;
              }
              return null;
            }
          });
        }
      }
      catch (AbsentInformationException ignored) {
      }
    }
    return null;
  }

  //don't use JavaRecursiveElementWalkingVisitor because getNextSibling() works slowly for compiled elements 
  private class MethodFinder extends JavaRecursiveElementVisitor {
    private final String myClassName;
    private PsiClass myCompiledClass;
    private final String myMethodName;
    private final String myMethodSignature;
    private PsiMethod myCompiledMethod;

    public MethodFinder(final String className, final String methodName, final String methodSignature) {
      myClassName = className;
      myMethodName = methodName;
      myMethodSignature = methodSignature;
    }

    @Override public void visitClass(PsiClass aClass) {
      final List<ReferenceType> allClasses = myDebugProcess.getPositionManager().getAllClasses(SourcePosition.createFromElement(aClass));
      for (ReferenceType referenceType : allClasses) {
        if (referenceType.name().equals(myClassName)) {
          myCompiledClass = aClass;
        }
      }

      aClass.acceptChildren(this);
    }

    @Override public void visitMethod(PsiMethod method) {
      try {
        //noinspection HardCodedStringLiteral
        String methodName = method.isConstructor() ? "<init>" : method.getName();
        PsiClass containingClass = method.getContainingClass();

        if(containingClass != null &&
           containingClass.equals(myCompiledClass) &&
           methodName.equals(myMethodName) &&
           JVMNameUtil.getJVMSignature(method).getName(myDebugProcess).equals(myMethodSignature)) {
          myCompiledMethod = method;
        }
      }
      catch (EvaluateException e) {
        LOG.debug(e);
      }
    }

    public PsiClass getCompiledClass() {
      return myCompiledClass;
    }

    public PsiMethod getCompiledMethod() {
      return myCompiledMethod;
    }
  }

  private static class ClsSourcePosition extends RemappedSourcePosition {
    private final int myOriginalLine;

    public ClsSourcePosition(SourcePosition delegate, int originalLine) {
      super(delegate);
      myOriginalLine = originalLine;
    }

    @Override
    public SourcePosition mapDelegate(SourcePosition original) {
      if (myOriginalLine < 0) return original;
      SourcePosition position = calcLineMappedSourcePosition(getFile(), myOriginalLine);
      return position != null ? position : original;
    }
  }

  @Nullable
  private static SourcePosition calcLineMappedSourcePosition(PsiFile psiFile, int originalLine) {
    int line = bytecodeToSourceLine(psiFile, originalLine);
    if (line > -1) {
      return SourcePosition.createFromLine(psiFile, line - 1);
    }
    return null;
  }

  private static int bytecodeToSourceLine(PsiFile psiFile, int originalLine) {
    VirtualFile file = psiFile.getVirtualFile();
    if (file != null) {
      LineNumbersMapping mapping = file.getUserData(LineNumbersMapping.LINE_NUMBERS_MAPPING_KEY);
      if (mapping != null) {
        int line = mapping.bytecodeToSource(originalLine + 1);
        if (line > -1) {
          return line;
        }
      }
    }
    return -1;
  }
}


File: java/debugger/impl/src/com/intellij/debugger/engine/RemappedSourcePosition.java
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
package com.intellij.debugger.engine;

import com.intellij.debugger.SourcePosition;
import com.intellij.openapi.editor.Editor;
import com.intellij.psi.PsiElement;
import com.intellij.psi.PsiFile;
import org.jetbrains.annotations.NotNull;

/**
 * @author egor
 */
abstract class RemappedSourcePosition extends SourcePosition {
  private SourcePosition myDelegate;
  private boolean myMapped = false;

  public RemappedSourcePosition(SourcePosition delegate) {
    myDelegate = delegate;
  }

  @Override
  @NotNull
  public PsiFile getFile() {
    return myDelegate.getFile();
  }

  @Override
  public PsiElement getElementAt() {
    return myDelegate.getElementAt();
  }

  @Override
  public int getLine() {
    int line = myDelegate.getLine();
    if (!myMapped) {
      myMapped = true;
      myDelegate = mapDelegate(myDelegate);
      return myDelegate.getLine();
    }
    return line;
  }

  @Override
  public int getOffset() {
    int offset = myDelegate.getOffset(); //document loaded here
    if (!myMapped) {
      myMapped = true;
      myDelegate = mapDelegate(myDelegate);
      return myDelegate.getOffset();
    }
    return offset;
  }

  public abstract SourcePosition mapDelegate(SourcePosition original);

  @Override
  public Editor openEditor(boolean requestFocus) {
    return myDelegate.openEditor(requestFocus);
  }

  @Override
  public boolean equals(Object o) {
    return myDelegate.equals(o);
  }

  @Override
  public void navigate(boolean requestFocus) {
    myDelegate.navigate(requestFocus);
  }

  @Override
  public boolean canNavigate() {
    return myDelegate.canNavigate();
  }

  @Override
  public boolean canNavigateToSource() {
    return myDelegate.canNavigateToSource();
  }
}


File: java/debugger/impl/src/com/intellij/debugger/impl/DebuggerSession.java
/*
 * Copyright 2000-2014 JetBrains s.r.o.
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
package com.intellij.debugger.impl;

import com.intellij.debugger.DebugEnvironment;
import com.intellij.debugger.DebuggerBundle;
import com.intellij.debugger.DebuggerInvocationUtil;
import com.intellij.debugger.SourcePosition;
import com.intellij.debugger.engine.*;
import com.intellij.debugger.engine.evaluation.EvaluateException;
import com.intellij.debugger.engine.evaluation.EvaluationListener;
import com.intellij.debugger.engine.events.SuspendContextCommandImpl;
import com.intellij.debugger.engine.jdi.StackFrameProxy;
import com.intellij.debugger.engine.requests.RequestManagerImpl;
import com.intellij.debugger.jdi.StackFrameProxyImpl;
import com.intellij.debugger.jdi.ThreadReferenceProxyImpl;
import com.intellij.debugger.ui.breakpoints.Breakpoint;
import com.intellij.debugger.ui.breakpoints.BreakpointWithHighlighter;
import com.intellij.debugger.ui.breakpoints.LineBreakpoint;
import com.intellij.execution.ExecutionException;
import com.intellij.execution.ExecutionResult;
import com.intellij.execution.configurations.RemoteConnection;
import com.intellij.execution.configurations.RemoteState;
import com.intellij.execution.configurations.RunProfileState;
import com.intellij.execution.process.ProcessHandler;
import com.intellij.execution.process.ProcessOutputTypes;
import com.intellij.idea.ActionsBundle;
import com.intellij.openapi.application.ApplicationManager;
import com.intellij.openapi.application.ModalityState;
import com.intellij.openapi.diagnostic.Logger;
import com.intellij.openapi.editor.Document;
import com.intellij.openapi.project.Project;
import com.intellij.openapi.ui.Messages;
import com.intellij.openapi.util.Comparing;
import com.intellij.openapi.util.Computable;
import com.intellij.openapi.util.Disposer;
import com.intellij.openapi.util.Pair;
import com.intellij.openapi.util.registry.Registry;
import com.intellij.psi.PsiCompiledElement;
import com.intellij.psi.PsiDocumentManager;
import com.intellij.psi.PsiFile;
import com.intellij.psi.search.GlobalSearchScope;
import com.intellij.unscramble.ThreadState;
import com.intellij.util.Alarm;
import com.intellij.util.TimeoutUtil;
import com.intellij.util.ui.UIUtil;
import com.intellij.xdebugger.AbstractDebuggerSession;
import com.intellij.xdebugger.XDebugSession;
import com.intellij.xdebugger.impl.actions.XDebuggerActions;
import com.intellij.xdebugger.impl.evaluate.quick.common.ValueLookupManager;
import com.sun.jdi.ObjectCollectedException;
import com.sun.jdi.ThreadReference;
import com.sun.jdi.event.Event;
import com.sun.jdi.request.EventRequest;
import com.sun.jdi.request.StepRequest;
import org.jetbrains.annotations.NotNull;
import org.jetbrains.annotations.Nullable;

import java.util.Collection;
import java.util.HashSet;
import java.util.List;
import java.util.Set;

public class DebuggerSession implements AbstractDebuggerSession {
  private static final Logger LOG = Logger.getInstance("#com.intellij.debugger.impl.DebuggerSession");
  // flags
  private final MyDebuggerStateManager myContextManager;

  public static final int STATE_STOPPED = 0;
  public static final int STATE_RUNNING = 1;
  public static final int STATE_WAITING_ATTACH = 2;
  public static final int STATE_PAUSED = 3;
  public static final int STATE_WAIT_EVALUATION = 5;
  public static final int STATE_DISPOSED = 6;

  public static final int EVENT_ATTACHED = 0;
  public static final int EVENT_DETACHED = 1;
  public static final int EVENT_RESUME = 4;
  public static final int EVENT_STEP = 5;
  public static final int EVENT_PAUSE = 6;
  public static final int EVENT_REFRESH = 7;
  public static final int EVENT_CONTEXT = 8;
  public static final int EVENT_START_WAIT_ATTACH = 9;
  public static final int EVENT_DISPOSE = 10;
  public static final int EVENT_REFRESH_VIEWS_ONLY = 11;
  public static final int EVENT_THREADS_REFRESH = 12;

  private volatile boolean myIsEvaluating;
  private volatile int myIgnoreFiltersFrameCountThreshold = 0;

  private DebuggerSessionState myState = null;

  private final String mySessionName;
  private final DebugProcessImpl myDebugProcess;
  private @NotNull GlobalSearchScope mySearchScope;

  private final DebuggerContextImpl SESSION_EMPTY_CONTEXT;
  //Thread, user is currently stepping through
  private final Set<ThreadReferenceProxyImpl> mySteppingThroughThreads = new HashSet<ThreadReferenceProxyImpl>();
  protected final Alarm myUpdateAlarm = new Alarm(Alarm.ThreadToUse.SWING_THREAD);

  private boolean myModifiedClassesScanRequired = false;

  public boolean isSteppingThrough(ThreadReferenceProxyImpl threadProxy) {
    return mySteppingThroughThreads.contains(threadProxy);
  }

  @NotNull
  public GlobalSearchScope getSearchScope() {
    //noinspection ConstantConditions
    LOG.assertTrue(mySearchScope != null, "Accessing Session's search scope before its initialization");
    return mySearchScope;
  }

  public boolean isModifiedClassesScanRequired() {
    return myModifiedClassesScanRequired;
  }

  public void setModifiedClassesScanRequired(boolean modifiedClassesScanRequired) {
    myModifiedClassesScanRequired = modifiedClassesScanRequired;
  }

  private class MyDebuggerStateManager extends DebuggerStateManager {
    private DebuggerContextImpl myDebuggerContext;

    MyDebuggerStateManager() {
      myDebuggerContext = SESSION_EMPTY_CONTEXT;
    }

    @Override
    public DebuggerContextImpl getContext() {
      return myDebuggerContext;
    }

    /**
     * actually state changes not in the same sequence as you call setState
     * the 'resuming' setState with context.getSuspendContext() == null may be set prior to
     * the setState for the context with context.getSuspendContext()
     *
     * in this case we assume that the latter setState is ignored
     * since the thread was resumed
     */
    @Override
    public void setState(final DebuggerContextImpl context, final int state, final int event, final String description) {
      ApplicationManager.getApplication().assertIsDispatchThread();
      final DebuggerSession session = context.getDebuggerSession();
      LOG.assertTrue(session == DebuggerSession.this || session == null);
      final Runnable setStateRunnable = new Runnable() {
        @Override
        public void run() {
          LOG.assertTrue(myDebuggerContext.isInitialised());
          myDebuggerContext = context;
          if (LOG.isDebugEnabled()) {
            LOG.debug("DebuggerSession state = " + state + ", event = " + event);
          }

          myIsEvaluating = false;

          myState = new DebuggerSessionState(state, description);
          fireStateChanged(context, event);
        }
      };

      if(context.getSuspendContext() == null) {
        setStateRunnable.run();
      }
      else {
        getProcess().getManagerThread().schedule(new SuspendContextCommandImpl(context.getSuspendContext()) {
          @Override
          public void contextAction() throws Exception {
            context.initCaches();
            DebuggerInvocationUtil.swingInvokeLater(getProject(), setStateRunnable);
          }
        });
      }
    }
  }

  protected DebuggerSession(String sessionName, final DebugProcessImpl debugProcess) {
    mySessionName  = sessionName;
    myDebugProcess = debugProcess;
    SESSION_EMPTY_CONTEXT = DebuggerContextImpl.createDebuggerContext(this, null, null, null);
    myContextManager = new MyDebuggerStateManager();
    myState = new DebuggerSessionState(STATE_STOPPED, null);
    myDebugProcess.addDebugProcessListener(new MyDebugProcessListener(debugProcess));
    myDebugProcess.addEvaluationListener(new MyEvaluationListener());
    ValueLookupManager.getInstance(getProject()).startListening();
  }

  @NotNull
  public DebuggerStateManager getContextManager() {
    return myContextManager;
  }

  public Project getProject() {
    return getProcess().getProject();
  }

  public String getSessionName() {
    return mySessionName;
  }

  public DebugProcessImpl getProcess() {
    return myDebugProcess;
  }

  private static class DebuggerSessionState {
    final int myState;
    final String myDescription;

    public DebuggerSessionState(int state, String description) {
      myState = state;
      myDescription = description;
    }
  }

  public int getState() {
    return myState.myState;
  }

  public String getStateDescription() {
    if (myState.myDescription != null) {
      return myState.myDescription;
    }

    switch (myState.myState) {
      case STATE_STOPPED:
        return DebuggerBundle.message("status.debug.stopped");
      case STATE_RUNNING:
        return DebuggerBundle.message("status.app.running");
      case STATE_WAITING_ATTACH:
        RemoteConnection connection = getProcess().getConnection();
        final String addressDisplayName = DebuggerBundle.getAddressDisplayName(connection);
        final String transportName = DebuggerBundle.getTransportName(connection);
        return connection.isServerMode() ? DebuggerBundle.message("status.listening", addressDisplayName, transportName) : DebuggerBundle.message("status.connecting", addressDisplayName, transportName);
      case STATE_PAUSED:
        return DebuggerBundle.message("status.paused");
      case STATE_WAIT_EVALUATION:
        return DebuggerBundle.message("status.waiting.evaluation.result");
      case STATE_DISPOSED:
        return DebuggerBundle.message("status.debug.stopped");
    }
    return null;
  }

  /* Stepping */
  private void resumeAction(final DebugProcessImpl.ResumeCommand command, int event) {
    getContextManager().setState(SESSION_EMPTY_CONTEXT, STATE_WAIT_EVALUATION, event, null);
    myDebugProcess.getManagerThread().schedule(command);
  }

  public void stepOut(int stepSize) {
    final SuspendContextImpl suspendContext = getSuspendContext();
    final DebugProcessImpl.ResumeCommand cmd = myDebugProcess.createStepOutCommand(suspendContext, stepSize);
    mySteppingThroughThreads.add(cmd.getContextThread());
    resumeAction(cmd, EVENT_STEP);
  }

  public void stepOut() {
    stepOut(StepRequest.STEP_LINE);
  }

  public void stepOver(boolean ignoreBreakpoints, int stepSize) {
    final SuspendContextImpl suspendContext = getSuspendContext();
    final DebugProcessImpl.ResumeCommand cmd = myDebugProcess.createStepOverCommand(suspendContext, ignoreBreakpoints, stepSize);
    mySteppingThroughThreads.add(cmd.getContextThread());
    resumeAction(cmd, EVENT_STEP);
  }

  public void stepOver(boolean ignoreBreakpoints) {
    stepOver(ignoreBreakpoints, StepRequest.STEP_LINE);
  }

  public void stepInto(final boolean ignoreFilters, final @Nullable MethodFilter smartStepFilter, int stepSize) {
    final SuspendContextImpl suspendContext = getSuspendContext();
    final DebugProcessImpl.ResumeCommand cmd = myDebugProcess.createStepIntoCommand(suspendContext, ignoreFilters, smartStepFilter, stepSize);
    mySteppingThroughThreads.add(cmd.getContextThread());
    resumeAction(cmd, EVENT_STEP);
  }

  public void stepInto(final boolean ignoreFilters, final @Nullable MethodFilter smartStepFilter) {
    stepInto(ignoreFilters, smartStepFilter, StepRequest.STEP_LINE);
  }

  public void runToCursor(Document document, int line, final boolean ignoreBreakpoints) {
    try {
      DebugProcessImpl.ResumeCommand runToCursorCommand = myDebugProcess.createRunToCursorCommand(getSuspendContext(), document, line, ignoreBreakpoints);
      mySteppingThroughThreads.add(runToCursorCommand.getContextThread());
      resumeAction(runToCursorCommand, EVENT_STEP);
    }
    catch (EvaluateException e) {
      Messages.showErrorDialog(e.getMessage(), UIUtil.removeMnemonic(ActionsBundle.actionText(XDebuggerActions.RUN_TO_CURSOR)));
    }
  }


  public void resume() {
    final SuspendContextImpl suspendContext = getSuspendContext();
    if(suspendContext != null) {
      if (suspendContext.getSuspendPolicy() == EventRequest.SUSPEND_ALL) {
        mySteppingThroughThreads.clear();
      }
      else {
        mySteppingThroughThreads.remove(suspendContext.getThread());
      }
      resetIgnoreStepFiltersFlag();
      resumeAction(myDebugProcess.createResumeCommand(suspendContext), EVENT_RESUME);
    }
  }

  private void resetIgnoreStepFiltersFlag() {
    myIgnoreFiltersFrameCountThreshold = 0;
  }

  public void setIgnoreStepFiltersFlag(int currentStackFrameCount) {
    myIgnoreFiltersFrameCountThreshold = currentStackFrameCount;
  }

  public boolean shouldIgnoreSteppingFilters() {
    return myIgnoreFiltersFrameCountThreshold > 0;
  }

  public void pause() {
    myDebugProcess.getManagerThread().schedule(myDebugProcess.createPauseCommand());
  }

  /*Presentation*/

  public void showExecutionPoint() {
    getContextManager().setState(DebuggerContextUtil.createDebuggerContext(this, getSuspendContext()), STATE_PAUSED, EVENT_REFRESH, null);
  }

  public void refresh(final boolean refreshViewsOnly) {
    final int state = getState();
    DebuggerContextImpl context = myContextManager.getContext();
    DebuggerContextImpl newContext = DebuggerContextImpl.createDebuggerContext(this, context.getSuspendContext(), context.getThreadProxy(), context.getFrameProxy());
    myContextManager.setState(newContext, state, refreshViewsOnly? EVENT_REFRESH_VIEWS_ONLY : EVENT_REFRESH, null);
  }

  public void dispose() {
    getProcess().dispose();
    Disposer.dispose(myUpdateAlarm);
    DebuggerInvocationUtil.invokeLater(getProject(), new Runnable() {
      @Override
      public void run() {
        getContextManager().setState(SESSION_EMPTY_CONTEXT, STATE_DISPOSED, EVENT_DISPOSE, null);
      }
    });
  }

  // ManagerCommands
  @Override
  public boolean isStopped() {
    return getState() == STATE_STOPPED;
  }

  public boolean isAttached() {
    return !isStopped() && getState() != STATE_WAITING_ATTACH;
  }

  @Override
  public boolean isPaused() {
    return getState() == STATE_PAUSED;
  }

  public boolean isConnecting() {
    return getState() == STATE_WAITING_ATTACH;
  }

  public boolean isEvaluating() {
    return myIsEvaluating;
  }

  public boolean isRunning() {
    return getState() == STATE_RUNNING && !getProcess().getProcessHandler().isProcessTerminated();
  }

  private SuspendContextImpl getSuspendContext() {
    ApplicationManager.getApplication().assertIsDispatchThread();
    return getContextManager().getContext().getSuspendContext();
  }

  @Nullable
  protected ExecutionResult attach(DebugEnvironment environment) throws ExecutionException {
    RemoteConnection remoteConnection = environment.getRemoteConnection();
    final String addressDisplayName = DebuggerBundle.getAddressDisplayName(remoteConnection);
    final String transportName = DebuggerBundle.getTransportName(remoteConnection);
    mySearchScope = environment.getSearchScope();
    final ExecutionResult executionResult = myDebugProcess.attachVirtualMachine(environment, this);
    getContextManager().setState(SESSION_EMPTY_CONTEXT, STATE_WAITING_ATTACH, EVENT_START_WAIT_ATTACH, DebuggerBundle.message("status.waiting.attach", addressDisplayName, transportName));
    return executionResult;
  }

  private class MyDebugProcessListener extends DebugProcessAdapterImpl {
    private final DebugProcessImpl myDebugProcess;

    public MyDebugProcessListener(final DebugProcessImpl debugProcess) {
      myDebugProcess = debugProcess;
    }

    //executed in manager thread
    @Override
    public void connectorIsReady() {
      DebuggerInvocationUtil.invokeLater(getProject(), new Runnable() {
        @Override
        public void run() {
          RemoteConnection connection = myDebugProcess.getConnection();
          final String addressDisplayName = DebuggerBundle.getAddressDisplayName(connection);
          final String transportName = DebuggerBundle.getTransportName(connection);
          final String connectionStatusMessage = connection.isServerMode() ? DebuggerBundle.message("status.listening", addressDisplayName, transportName) : DebuggerBundle.message("status.connecting", addressDisplayName, transportName);
          getContextManager().setState(SESSION_EMPTY_CONTEXT, STATE_WAITING_ATTACH, EVENT_START_WAIT_ATTACH, connectionStatusMessage);
        }
      });
    }

    @Override
    public void paused(final SuspendContextImpl suspendContext) {
      if (LOG.isDebugEnabled()) {
        LOG.debug("paused");
      }

      if (!shouldSetAsActiveContext(suspendContext)) {
        DebuggerInvocationUtil.invokeLater(getProject(), new Runnable() {
          @Override
          public void run() {
            getContextManager().fireStateChanged(getContextManager().getContext(), EVENT_THREADS_REFRESH);
          }
        });
        return;
      }

      ThreadReferenceProxyImpl currentThread   = suspendContext.getThread();
      final StackFrameContext positionContext;

      if (currentThread == null) {
        //Pause pressed
        LOG.assertTrue(suspendContext.getSuspendPolicy() == EventRequest.SUSPEND_ALL);
        SuspendContextImpl oldContext = getProcess().getSuspendManager().getPausedContext();

        if (oldContext != null) {
          currentThread = oldContext.getThread();
        }

        if(currentThread == null) {
          final Collection<ThreadReferenceProxyImpl> allThreads = getProcess().getVirtualMachineProxy().allThreads();
          // heuristics: try to pre-select EventDispatchThread
          for (final ThreadReferenceProxyImpl thread : allThreads) {
            if (ThreadState.isEDT(thread.name())) {
              currentThread = thread;
              break;
            }
          }
          if (currentThread == null) {
            // heuristics: display the first thread with RUNNABLE status
            for (final ThreadReferenceProxyImpl thread : allThreads) {
              currentThread = thread;
              if (currentThread.status() == ThreadReference.THREAD_STATUS_RUNNING) {
                break;
              }
            }
          }
        }

        StackFrameProxyImpl proxy = null;
        if (currentThread != null) {
          try {
            while (!currentThread.isSuspended()) {
              // wait until thread is considered suspended. Querying data from a thread immediately after VM.suspend()
              // may result in IncompatibleThreadStateException, most likely some time after suspend() VM erroneously thinks that thread is still running
              TimeoutUtil.sleep(10);
            }
            proxy = (currentThread.frameCount() > 0) ? currentThread.frame(0) : null;
          }
          catch (ObjectCollectedException ignored) {
            proxy = null;
          }
          catch (EvaluateException e) {
            proxy = null;
            LOG.error(e);
          }
        }
        positionContext = new SimpleStackFrameContext(proxy, myDebugProcess);
      }
      else {
        positionContext = suspendContext;
      }

      if (currentThread != null) {
        try {
          final int frameCount = currentThread.frameCount();
          if (frameCount == 0 || (frameCount <= myIgnoreFiltersFrameCountThreshold)) {
            resetIgnoreStepFiltersFlag();
          }
        }
        catch (EvaluateException e) {
          LOG.info(e);
          resetIgnoreStepFiltersFlag();
        }
      }

      SourcePosition position = PsiDocumentManager.getInstance(getProject()).commitAndRunReadAction(new Computable<SourcePosition>() {
        @Override
        public @Nullable SourcePosition compute() {
          return ContextUtil.getSourcePosition(positionContext);
        }
      });

      if (position != null) {
        final List<Pair<Breakpoint, Event>> eventDescriptors = DebuggerUtilsEx.getEventDescriptors(suspendContext);
        final RequestManagerImpl requestsManager = suspendContext.getDebugProcess().getRequestsManager();
        final PsiFile foundFile = position.getFile();
        final boolean sourceMissing = foundFile instanceof PsiCompiledElement;
        for (Pair<Breakpoint, Event> eventDescriptor : eventDescriptors) {
          Breakpoint breakpoint = eventDescriptor.getFirst();
          if (breakpoint instanceof LineBreakpoint) {
            final SourcePosition breakpointPosition = ((BreakpointWithHighlighter)breakpoint).getSourcePosition();
            if (breakpointPosition == null || (!sourceMissing && breakpointPosition.getLine() != position.getLine())) {
              requestsManager.deleteRequest(breakpoint);
              requestsManager.setInvalid(breakpoint, DebuggerBundle.message("error.invalid.breakpoint.source.changed"));
              breakpoint.updateUI();
            }
            else if (sourceMissing) {
              // adjust position to be position of the breakpoint in order to show the real originator of the event
              position = breakpointPosition;
              final StackFrameProxy frameProxy = positionContext.getFrameProxy();
              String className;
              try {
                className = frameProxy != null? frameProxy.location().declaringType().name() : "";
              }
              catch (EvaluateException ignored) {
                className = "";
              }
              requestsManager.setInvalid(breakpoint, DebuggerBundle.message("error.invalid.breakpoint.source.not.found", className));
              breakpoint.updateUI();
            }
          }
        }
      }

      final DebuggerContextImpl debuggerContext = DebuggerContextImpl.createDebuggerContext(DebuggerSession.this, suspendContext, currentThread, null);
      debuggerContext.setPositionCache(position);

      DebuggerInvocationUtil.invokeLater(getProject(), new Runnable() {
        @Override
        public void run() {
          getContextManager().setState(debuggerContext, STATE_PAUSED, EVENT_PAUSE, null);
        }
      });
    }

    private boolean shouldSetAsActiveContext(final SuspendContextImpl suspendContext) {
      // always switch context if it is not a breakpoint stop
      if (DebuggerUtilsEx.getEventDescriptors(suspendContext).isEmpty()) {
        return true;
      }
      final ThreadReferenceProxyImpl newThread = suspendContext.getThread();
      if (newThread == null || suspendContext.getSuspendPolicy() == EventRequest.SUSPEND_ALL || isSteppingThrough(newThread)) {
        return true;
      }
      final SuspendContextImpl currentSuspendContext = getContextManager().getContext().getSuspendContext();
      if (currentSuspendContext == null) {
        return true;
      }
      if (enableBreakpointsDuringEvaluation()) {
        final ThreadReferenceProxyImpl currentThread = currentSuspendContext.getThread();
        return currentThread == null || Comparing.equal(currentThread.getThreadReference(), newThread.getThreadReference());
      }
      return false;
    }


    @Override
    public void resumed(final SuspendContextImpl suspendContext) {
      final SuspendContextImpl currentContext = getProcess().getSuspendManager().getPausedContext();
      DebuggerInvocationUtil.invokeLater(getProject(), new Runnable() {
        @Override
        public void run() {
          if (currentContext != null) {
            getContextManager().setState(DebuggerContextUtil.createDebuggerContext(DebuggerSession.this, currentContext), STATE_PAUSED, EVENT_CONTEXT, null);
          }
          else {
            getContextManager().setState(SESSION_EMPTY_CONTEXT, STATE_RUNNING, EVENT_CONTEXT, null);
          }
        }
      });
    }

    @Override
    public void processAttached(final DebugProcessImpl process) {
      final RemoteConnection connection = getProcess().getConnection();
      final String addressDisplayName = DebuggerBundle.getAddressDisplayName(connection);
      final String transportName = DebuggerBundle.getTransportName(connection);
      final String message = DebuggerBundle.message("status.connected", addressDisplayName, transportName);

      process.printToConsole(message + "\n");
      DebuggerInvocationUtil.invokeLater(getProject(), new Runnable() {
        @Override
        public void run() {
          getContextManager().setState(SESSION_EMPTY_CONTEXT, STATE_RUNNING, EVENT_ATTACHED, message);
        }
      });
    }

    @Override
    public void attachException(final RunProfileState state, final ExecutionException exception, final RemoteConnection remoteConnection) {
      DebuggerInvocationUtil.invokeLater(getProject(), new Runnable() {
        @Override
        public void run() {
          String message = "";
          if (state instanceof RemoteState) {
            message = DebuggerBundle.message("status.connect.failed", DebuggerBundle.getAddressDisplayName(remoteConnection), DebuggerBundle.getTransportName(remoteConnection));
          }
          message += exception.getMessage();
          getContextManager().setState(SESSION_EMPTY_CONTEXT, STATE_STOPPED, EVENT_DETACHED, message);
        }
      });
    }

    @Override
    public void processDetached(final DebugProcessImpl debugProcess, boolean closedByUser) {
      if (!closedByUser) {
        ProcessHandler processHandler = debugProcess.getProcessHandler();
        if(processHandler != null) {
          final RemoteConnection connection = getProcess().getConnection();
          final String addressDisplayName = DebuggerBundle.getAddressDisplayName(connection);
          final String transportName = DebuggerBundle.getTransportName(connection);
          processHandler.notifyTextAvailable(DebuggerBundle.message("status.disconnected", addressDisplayName, transportName) + "\n", ProcessOutputTypes.SYSTEM);
        }
      }
      DebuggerInvocationUtil.invokeLater(getProject(), new Runnable() {
        @Override
        public void run() {
          final RemoteConnection connection = getProcess().getConnection();
          final String addressDisplayName = DebuggerBundle.getAddressDisplayName(connection);
          final String transportName = DebuggerBundle.getTransportName(connection);
          getContextManager().setState(SESSION_EMPTY_CONTEXT, STATE_STOPPED, EVENT_DETACHED, DebuggerBundle.message("status.disconnected", addressDisplayName, transportName));
        }
      });
      mySteppingThroughThreads.clear();
    }

    @Override
    public void threadStarted(DebugProcess proc, ThreadReference thread) {
      notifyThreadsRefresh();
    }

    @Override
    public void threadStopped(DebugProcess proc, ThreadReference thread) {
      notifyThreadsRefresh();
    }

    private void notifyThreadsRefresh() {
      if (!myUpdateAlarm.isDisposed()) {
        myUpdateAlarm.cancelAllRequests();
        myUpdateAlarm.addRequest(new Runnable() {
          @Override
          public void run() {
            final DebuggerStateManager contextManager = getContextManager();
            contextManager.fireStateChanged(contextManager.getContext(), EVENT_THREADS_REFRESH);
          }
        }, 100, ModalityState.NON_MODAL);
      }
    }
  }

  private class MyEvaluationListener implements EvaluationListener {
    @Override
    public void evaluationStarted(SuspendContextImpl context) {
      myIsEvaluating = true;
    }

    @Override
    public void evaluationFinished(final SuspendContextImpl context) {
      myIsEvaluating = false;
      // seems to be not required after move to xdebugger
      //DebuggerInvocationUtil.invokeLater(getProject(), new Runnable() {
      //  @Override
      //  public void run() {
      //    if (context != getSuspendContext()) {
      //      getContextManager().setState(DebuggerContextUtil.createDebuggerContext(DebuggerSession.this, context), STATE_PAUSED, EVENT_REFRESH, null);
      //    }
      //  }
      //});
    }
  }

  public static boolean enableBreakpointsDuringEvaluation() {
    return Registry.is("debugger.enable.breakpoints.during.evaluation");
  }

  @Nullable
  public XDebugSession getXDebugSession() {
    JavaDebugProcess process = myDebugProcess.getXdebugProcess();
    return process != null ? process.getSession() : null;
  }
}


File: java/debugger/impl/src/com/intellij/debugger/ui/breakpoints/BreakpointManager.java
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

/*
 * Class BreakpointManager
 * @author Jeka
 */
package com.intellij.debugger.ui.breakpoints;

import com.intellij.debugger.DebuggerBundle;
import com.intellij.debugger.DebuggerInvocationUtil;
import com.intellij.debugger.engine.BreakpointStepMethodFilter;
import com.intellij.debugger.engine.DebugProcessImpl;
import com.intellij.debugger.engine.requests.RequestManagerImpl;
import com.intellij.debugger.impl.DebuggerContextImpl;
import com.intellij.debugger.impl.DebuggerContextListener;
import com.intellij.debugger.impl.DebuggerManagerImpl;
import com.intellij.debugger.impl.DebuggerSession;
import com.intellij.debugger.ui.JavaDebuggerSupport;
import com.intellij.openapi.application.ApplicationManager;
import com.intellij.openapi.diagnostic.Logger;
import com.intellij.openapi.editor.Document;
import com.intellij.openapi.editor.Editor;
import com.intellij.openapi.editor.markup.GutterIconRenderer;
import com.intellij.openapi.editor.markup.RangeHighlighter;
import com.intellij.openapi.fileEditor.FileDocumentManager;
import com.intellij.openapi.project.Project;
import com.intellij.openapi.startup.StartupManager;
import com.intellij.openapi.ui.MessageType;
import com.intellij.openapi.util.Comparing;
import com.intellij.openapi.util.Computable;
import com.intellij.openapi.util.InvalidDataException;
import com.intellij.openapi.util.Key;
import com.intellij.openapi.vfs.VirtualFile;
import com.intellij.openapi.vfs.VirtualFileManager;
import com.intellij.psi.PsiField;
import com.intellij.util.Function;
import com.intellij.util.containers.ContainerUtil;
import com.intellij.xdebugger.XDebuggerManager;
import com.intellij.xdebugger.XDebuggerUtil;
import com.intellij.xdebugger.breakpoints.*;
import com.intellij.xdebugger.impl.DebuggerSupport;
import com.intellij.xdebugger.impl.XDebugSessionImpl;
import com.intellij.xdebugger.impl.breakpoints.XBreakpointBase;
import com.intellij.xdebugger.impl.breakpoints.XBreakpointManagerImpl;
import com.intellij.xdebugger.impl.breakpoints.XDependentBreakpointManager;
import com.intellij.xdebugger.impl.breakpoints.XLineBreakpointImpl;
import com.sun.jdi.InternalException;
import com.sun.jdi.ThreadReference;
import com.sun.jdi.request.*;
import gnu.trove.THashMap;
import org.jdom.Element;
import org.jetbrains.annotations.NonNls;
import org.jetbrains.annotations.NotNull;
import org.jetbrains.annotations.Nullable;
import org.jetbrains.java.debugger.breakpoints.properties.JavaExceptionBreakpointProperties;

import javax.swing.*;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;

public class BreakpointManager {
  private static final Logger LOG = Logger.getInstance("#com.intellij.debugger.ui.breakpoints.BreakpointManager");

  @NonNls private static final String MASTER_BREAKPOINT_TAGNAME = "master_breakpoint";
  @NonNls private static final String SLAVE_BREAKPOINT_TAGNAME = "slave_breakpoint";
  @NonNls private static final String DEFAULT_SUSPEND_POLICY_ATTRIBUTE_NAME = "default_suspend_policy";
  @NonNls private static final String DEFAULT_CONDITION_STATE_ATTRIBUTE_NAME = "default_condition_enabled";

  @NonNls private static final String RULES_GROUP_NAME = "breakpoint_rules";
  private static final String CONVERTED_PARAM = "converted";

  private final Project myProject;
  private final Map<String, String> myUIProperties = new LinkedHashMap<String, String>();

  private final StartupManager myStartupManager;

  public BreakpointManager(@NotNull Project project, @NotNull StartupManager startupManager, @NotNull DebuggerManagerImpl debuggerManager) {
    myProject = project;
    myStartupManager = startupManager;
    debuggerManager.getContextManager().addListener(new DebuggerContextListener() {
      private DebuggerSession myPreviousSession;

      @Override
      public void changeEvent(@NotNull DebuggerContextImpl newContext, int event) {
        if (event == DebuggerSession.EVENT_ATTACHED) {
          for (XBreakpoint breakpoint : getXBreakpointManager().getAllBreakpoints()) {
            if (checkAndNotifyPossiblySlowBreakpoint(breakpoint)) break;
          }
        }
        if (newContext.getDebuggerSession() != myPreviousSession || event == DebuggerSession.EVENT_DETACHED) {
          updateBreakpointsUI();
          myPreviousSession = newContext.getDebuggerSession();
        }
      }
    });
  }

  private static boolean checkAndNotifyPossiblySlowBreakpoint(XBreakpoint breakpoint) {
    if (breakpoint.isEnabled() &&
        (breakpoint.getType() instanceof JavaMethodBreakpointType || breakpoint.getType() instanceof JavaWildcardMethodBreakpointType)) {
      XDebugSessionImpl.NOTIFICATION_GROUP.createNotification("Method breakpoints may dramatically slow down debugging", MessageType.WARNING)
        .notify(((XBreakpointBase)breakpoint).getProject());
      return true;
    }
    return false;
  }

  public void init() {
    XBreakpointManager manager = XDebuggerManager.getInstance(myProject).getBreakpointManager();
    manager.addBreakpointListener(new XBreakpointAdapter<XBreakpoint<?>>() {
      @Override
      public void breakpointAdded(@NotNull XBreakpoint<?> xBreakpoint) {
        Breakpoint breakpoint = getJavaBreakpoint(xBreakpoint);
        if (breakpoint != null) {
          addBreakpoint(breakpoint);
        }
      }

      @Override
      public void breakpointChanged(@NotNull XBreakpoint xBreakpoint) {
        Breakpoint breakpoint = getJavaBreakpoint(xBreakpoint);
        if (breakpoint != null) {
          fireBreakpointChanged(breakpoint);
        }
      }
    });
  }

  private XBreakpointManager getXBreakpointManager() {
    return XDebuggerManager.getInstance(myProject).getBreakpointManager();
  }

  public void editBreakpoint(final Breakpoint breakpoint, final Editor editor) {
    DebuggerInvocationUtil.swingInvokeLater(myProject, new Runnable() {
      @Override
      public void run() {
        XBreakpoint xBreakpoint = breakpoint.myXBreakpoint;
        if (xBreakpoint instanceof XLineBreakpointImpl) {
          RangeHighlighter highlighter = ((XLineBreakpointImpl)xBreakpoint).getHighlighter();
          if (highlighter != null) {
            GutterIconRenderer renderer = highlighter.getGutterIconRenderer();
            if (renderer != null) {
              DebuggerSupport.getDebuggerSupport(JavaDebuggerSupport.class).getEditBreakpointAction().editBreakpoint(
                myProject, editor, breakpoint.myXBreakpoint, renderer
              );
            }
          }
        }
      }
    });
  }

  public void setBreakpointDefaults(Key<? extends Breakpoint> category, BreakpointDefaults defaults) {
    Class typeCls = null;
    if (LineBreakpoint.CATEGORY.toString().equals(category.toString())) {
      typeCls = JavaLineBreakpointType.class;
    }
    else if (MethodBreakpoint.CATEGORY.toString().equals(category.toString())) {
      typeCls = JavaMethodBreakpointType.class;
    }
    else if (FieldBreakpoint.CATEGORY.toString().equals(category.toString())) {
      typeCls = JavaFieldBreakpointType.class;
    }
    else if (ExceptionBreakpoint.CATEGORY.toString().equals(category.toString())) {
      typeCls = JavaExceptionBreakpointType.class;
    }
    if (typeCls != null) {
      XBreakpointType<XBreakpoint<?>, ?> type = XDebuggerUtil.getInstance().findBreakpointType(typeCls);
      ((XBreakpointManagerImpl)getXBreakpointManager()).getBreakpointDefaults(type).setSuspendPolicy(Breakpoint.transformSuspendPolicy(defaults.getSuspendPolicy()));
    }
  }

  @Nullable
  public RunToCursorBreakpoint addRunToCursorBreakpoint(Document document, int lineIndex, final boolean ignoreBreakpoints) {
    return RunToCursorBreakpoint.create(myProject, document, lineIndex, ignoreBreakpoints);
  }

  @Nullable
  public StepIntoBreakpoint addStepIntoBreakpoint(@NotNull BreakpointStepMethodFilter filter) {
    return StepIntoBreakpoint.create(myProject, filter);
  }

  @Nullable
  public LineBreakpoint addLineBreakpoint(Document document, int lineIndex) {
    ApplicationManager.getApplication().assertIsDispatchThread();
    if (!LineBreakpoint.canAddLineBreakpoint(myProject, document, lineIndex)) {
      return null;
    }
    XLineBreakpoint xLineBreakpoint = addXLineBreakpoint(JavaLineBreakpointType.class, document, lineIndex);
    Breakpoint breakpoint = getJavaBreakpoint(xLineBreakpoint);
    if (breakpoint instanceof LineBreakpoint) {
      addBreakpoint(breakpoint);
      return ((LineBreakpoint)breakpoint);
    }
    return null;
  }

  @Nullable
  public FieldBreakpoint addFieldBreakpoint(@NotNull Document document, int offset) {
    PsiField field = FieldBreakpoint.findField(myProject, document, offset);
    if (field == null) {
      return null;
    }

    int line = document.getLineNumber(offset);

    if (document.getLineNumber(field.getNameIdentifier().getTextOffset()) < line) {
      return null;
    }

    return addFieldBreakpoint(document, line, field.getName());
  }

  @Nullable
  public FieldBreakpoint addFieldBreakpoint(Document document, int lineIndex, String fieldName) {
    ApplicationManager.getApplication().assertIsDispatchThread();
    XLineBreakpoint xBreakpoint = addXLineBreakpoint(JavaFieldBreakpointType.class, document, lineIndex);
    Breakpoint javaBreakpoint = getJavaBreakpoint(xBreakpoint);
    if (javaBreakpoint instanceof FieldBreakpoint) {
      FieldBreakpoint fieldBreakpoint = (FieldBreakpoint)javaBreakpoint;
      fieldBreakpoint.setFieldName(fieldName);
      addBreakpoint(javaBreakpoint);
      return fieldBreakpoint;
    }
    return null;
  }

  @NotNull
  public ExceptionBreakpoint addExceptionBreakpoint(@NotNull final String exceptionClassName, final String packageName) {
    ApplicationManager.getApplication().assertIsDispatchThread();
    final JavaExceptionBreakpointType type = (JavaExceptionBreakpointType)XDebuggerUtil.getInstance().findBreakpointType(JavaExceptionBreakpointType.class);
    return ApplicationManager.getApplication().runWriteAction(new Computable<ExceptionBreakpoint>() {
      @Override
      public ExceptionBreakpoint compute() {
        XBreakpoint<JavaExceptionBreakpointProperties> xBreakpoint = XDebuggerManager.getInstance(myProject).getBreakpointManager()
          .addBreakpoint(type, new JavaExceptionBreakpointProperties(exceptionClassName, packageName));
        Breakpoint javaBreakpoint = getJavaBreakpoint(xBreakpoint);
        if (javaBreakpoint instanceof ExceptionBreakpoint) {
          ExceptionBreakpoint exceptionBreakpoint = (ExceptionBreakpoint)javaBreakpoint;
          exceptionBreakpoint.setQualifiedName(exceptionClassName);
          exceptionBreakpoint.setPackageName(packageName);
          addBreakpoint(exceptionBreakpoint);
          if (LOG.isDebugEnabled()) {
            LOG.debug("ExceptionBreakpoint Added");
          }
          return exceptionBreakpoint;
        }
        return null;
      }
    });
  }

  @Nullable
  public MethodBreakpoint addMethodBreakpoint(Document document, int lineIndex) {
    ApplicationManager.getApplication().assertIsDispatchThread();

    XLineBreakpoint xBreakpoint = addXLineBreakpoint(JavaMethodBreakpointType.class, document, lineIndex);
    Breakpoint javaBreakpoint = getJavaBreakpoint(xBreakpoint);
    if (javaBreakpoint instanceof MethodBreakpoint) {
      addBreakpoint(javaBreakpoint);
      return (MethodBreakpoint)javaBreakpoint;
    }
    return null;
  }

  private <B extends XBreakpoint<?>> XLineBreakpoint addXLineBreakpoint(Class<? extends XBreakpointType<B,?>> typeCls, Document document, final int lineIndex) {
    final XBreakpointType<B, ?> type = XDebuggerUtil.getInstance().findBreakpointType(typeCls);
    final VirtualFile file = FileDocumentManager.getInstance().getFile(document);
    return ApplicationManager.getApplication().runWriteAction(new Computable<XLineBreakpoint>() {
      @Override
      public XLineBreakpoint compute() {
        return XDebuggerManager.getInstance(myProject).getBreakpointManager()
          .addLineBreakpoint((XLineBreakpointType)type, file.getUrl(), lineIndex,
                             ((XLineBreakpointType)type).createBreakpointProperties(file, lineIndex));
      }
    });
  }

  /**
   * @param category breakpoint category, null if the category does not matter
   */
  @Nullable
  public <T extends BreakpointWithHighlighter> T findBreakpoint(final Document document, final int offset, @Nullable final Key<T> category) {
    for (final Breakpoint breakpoint : getBreakpoints()) {
      if (breakpoint instanceof BreakpointWithHighlighter && ((BreakpointWithHighlighter)breakpoint).isAt(document, offset)) {
        if (category == null || category.equals(breakpoint.getCategory())) {
          //noinspection CastConflictsWithInstanceof,unchecked
          return (T)breakpoint;
        }
      }
    }
    return null;
  }

  private final Map<String, Element> myOriginalBreakpointsNodes = new LinkedHashMap<String, Element>();

  public void readExternal(@NotNull final Element parentNode) {
    myOriginalBreakpointsNodes.clear();
    // save old breakpoints
    for (Element element : parentNode.getChildren()) {
      myOriginalBreakpointsNodes.put(element.getName(), element.clone());
    }
    if (myProject.isOpen()) {
      doRead(parentNode);
    }
    else {
      myStartupManager.registerPostStartupActivity(new Runnable() {
        @Override
        public void run() {
          doRead(parentNode);
        }
      });
    }
  }

  private void doRead(@NotNull final Element parentNode) {
    ApplicationManager.getApplication().runReadAction(new Runnable() {
      @Override
      @SuppressWarnings({"HardCodedStringLiteral"})
      public void run() {
        final Map<String, Breakpoint> nameToBreakpointMap = new THashMap<String, Breakpoint>();
        try {
          final List groups = parentNode.getChildren();
          for (final Object group1 : groups) {
            final Element group = (Element)group1;
            if (group.getName().equals(RULES_GROUP_NAME)) {
              continue;
            }
            // skip already converted
            if (group.getAttribute(CONVERTED_PARAM) != null) {
              continue;
            }
            final String categoryName = group.getName();
            final Key<Breakpoint> breakpointCategory = BreakpointCategory.lookup(categoryName);
            final String defaultPolicy = group.getAttributeValue(DEFAULT_SUSPEND_POLICY_ATTRIBUTE_NAME);
            final boolean conditionEnabled = Boolean.parseBoolean(group.getAttributeValue(DEFAULT_CONDITION_STATE_ATTRIBUTE_NAME, "true"));
            setBreakpointDefaults(breakpointCategory, new BreakpointDefaults(defaultPolicy, conditionEnabled));
            Element anyExceptionBreakpointGroup;
            if (!AnyExceptionBreakpoint.ANY_EXCEPTION_BREAKPOINT.equals(breakpointCategory)) {
              // for compatibility with previous format
              anyExceptionBreakpointGroup = group.getChild(AnyExceptionBreakpoint.ANY_EXCEPTION_BREAKPOINT.toString());
              //final BreakpointFactory factory = BreakpointFactory.getInstance(breakpointCategory);
              //if (factory != null) {
                for (Element breakpointNode : group.getChildren("breakpoint")) {
                  //Breakpoint breakpoint = factory.createBreakpoint(myProject, breakpointNode);
                  Breakpoint breakpoint = createBreakpoint(categoryName, breakpointNode);
                  breakpoint.readExternal(breakpointNode);
                  nameToBreakpointMap.put(breakpoint.getDisplayName(), breakpoint);
                }
              //}
            }
            else {
              anyExceptionBreakpointGroup = group;
            }

            if (anyExceptionBreakpointGroup != null) {
              final Element breakpointElement = group.getChild("breakpoint");
              if (breakpointElement != null) {
                XBreakpointManager manager = XDebuggerManager.getInstance(myProject).getBreakpointManager();
                JavaExceptionBreakpointType type = (JavaExceptionBreakpointType)XDebuggerUtil.getInstance().findBreakpointType(JavaExceptionBreakpointType.class);
                XBreakpoint<JavaExceptionBreakpointProperties> xBreakpoint = manager.getDefaultBreakpoint(type);
                Breakpoint breakpoint = getJavaBreakpoint(xBreakpoint);
                if (breakpoint != null) {
                  breakpoint.readExternal(breakpointElement);
                  addBreakpoint(breakpoint);
                }
              }
            }
          }
        }
        catch (InvalidDataException ignored) {
        }

        final Element rulesGroup = parentNode.getChild(RULES_GROUP_NAME);
        if (rulesGroup != null) {
          final List<Element> rules = rulesGroup.getChildren("rule");
          for (Element rule : rules) {
            // skip already converted
            if (rule.getAttribute(CONVERTED_PARAM) != null) {
              continue;
            }
            final Element master = rule.getChild(MASTER_BREAKPOINT_TAGNAME);
            if (master == null) {
              continue;
            }
            final Element slave = rule.getChild(SLAVE_BREAKPOINT_TAGNAME);
            if (slave == null) {
              continue;
            }
            final Breakpoint masterBreakpoint = nameToBreakpointMap.get(master.getAttributeValue("name"));
            if (masterBreakpoint == null) {
              continue;
            }
            final Breakpoint slaveBreakpoint = nameToBreakpointMap.get(slave.getAttributeValue("name"));
            if (slaveBreakpoint == null) {
              continue;
            }

            boolean leaveEnabled = "true".equalsIgnoreCase(rule.getAttributeValue("leaveEnabled"));
            XDependentBreakpointManager dependentBreakpointManager = ((XBreakpointManagerImpl)getXBreakpointManager()).getDependentBreakpointManager();
            dependentBreakpointManager.setMasterBreakpoint(slaveBreakpoint.myXBreakpoint, masterBreakpoint.myXBreakpoint, leaveEnabled);
            //addBreakpointRule(new EnableBreakpointRule(BreakpointManager.this, masterBreakpoint, slaveBreakpoint, leaveEnabled));
          }
        }

        DebuggerInvocationUtil.invokeLater(myProject, new Runnable() {
          @Override
          public void run() {
            updateBreakpointsUI();
          }
        });
      }
    });

    myUIProperties.clear();
    final Element props = parentNode.getChild("ui_properties");
    if (props != null) {
      final List children = props.getChildren("property");
      for (Object child : children) {
        Element property = (Element)child;
        final String name = property.getAttributeValue("name");
        final String value = property.getAttributeValue("value");
        if (name != null && value != null) {
          myUIProperties.put(name, value);
        }
      }
    }
  }

  private Breakpoint createBreakpoint(String category, Element breakpointNode) throws InvalidDataException {
    XBreakpoint xBreakpoint = null;
    if (category.equals(LineBreakpoint.CATEGORY.toString())) {
      xBreakpoint = createXLineBreakpoint(JavaLineBreakpointType.class, breakpointNode);
    }
    else if (category.equals(MethodBreakpoint.CATEGORY.toString())) {
      if (breakpointNode.getAttribute("url") != null) {
        xBreakpoint = createXLineBreakpoint(JavaMethodBreakpointType.class, breakpointNode);
      }
      else {
        xBreakpoint = createXBreakpoint(JavaWildcardMethodBreakpointType.class, breakpointNode);
      }
    }
    else if (category.equals(FieldBreakpoint.CATEGORY.toString())) {
      xBreakpoint = createXLineBreakpoint(JavaFieldBreakpointType.class, breakpointNode);
    }
    else if (category.equals(ExceptionBreakpoint.CATEGORY.toString())) {
      xBreakpoint = createXBreakpoint(JavaExceptionBreakpointType.class, breakpointNode);
    }
    if (xBreakpoint == null) {
      throw new IllegalStateException("Unknown breakpoint category " + category);
    }
    return getJavaBreakpoint(xBreakpoint);
  }

  private <B extends XBreakpoint<?>> XBreakpoint createXBreakpoint(Class<? extends XBreakpointType<B, ?>> typeCls,
                                                                           Element breakpointNode) throws InvalidDataException {
    final XBreakpointType<B, ?> type = XDebuggerUtil.getInstance().findBreakpointType(typeCls);
    return ApplicationManager.getApplication().runWriteAction(new Computable<XBreakpoint>() {
      @Override
      public XBreakpoint compute() {
        return XDebuggerManager.getInstance(myProject).getBreakpointManager()
          .addBreakpoint((XBreakpointType)type, type.createProperties());
      }
    });
  }

  private <B extends XBreakpoint<?>> XLineBreakpoint createXLineBreakpoint(Class<? extends XBreakpointType<B, ?>> typeCls,
                                                                           Element breakpointNode) throws InvalidDataException {
    final String url = breakpointNode.getAttributeValue("url");
    VirtualFile vFile = VirtualFileManager.getInstance().findFileByUrl(url);
    if (vFile == null) {
      throw new InvalidDataException(DebuggerBundle.message("error.breakpoint.file.not.found", url));
    }
    final Document doc = FileDocumentManager.getInstance().getDocument(vFile);
    if (doc == null) {
      throw new InvalidDataException(DebuggerBundle.message("error.cannot.load.breakpoint.file", url));
    }

    final int line;
    try {
      //noinspection HardCodedStringLiteral
      line = Integer.parseInt(breakpointNode.getAttributeValue("line"));
    }
    catch (Exception e) {
      throw new InvalidDataException("Line number is invalid for breakpoint");
    }
    return addXLineBreakpoint(typeCls, doc, line);
  }

  public static void addBreakpoint(@NotNull Breakpoint breakpoint) {
    assert breakpoint.myXBreakpoint.getUserData(Breakpoint.DATA_KEY) == breakpoint;
    breakpoint.updateUI();
    checkAndNotifyPossiblySlowBreakpoint(breakpoint.myXBreakpoint);
  }

  public void removeBreakpoint(@Nullable final Breakpoint breakpoint) {
    if (breakpoint == null) {
      return;
    }
    ApplicationManager.getApplication().runWriteAction(new Runnable() {
      @Override
      public void run() {
        getXBreakpointManager().removeBreakpoint(breakpoint.myXBreakpoint);
      }
    });
  }

  public void writeExternal(@NotNull final Element parentNode) {
    // restore old breakpoints
    for (Element group : myOriginalBreakpointsNodes.values()) {
      if (group.getAttribute(CONVERTED_PARAM) == null) {
        group.setAttribute(CONVERTED_PARAM, "true");
      }
      parentNode.addContent(group.clone());
    }
  }

  @NotNull
  public List<Breakpoint> getBreakpoints() {
    return ApplicationManager.getApplication().runReadAction(new Computable<List<Breakpoint>>() {
      @Override
      public List<Breakpoint> compute() {
        return ContainerUtil.mapNotNull(getXBreakpointManager().getAllBreakpoints(), new Function<XBreakpoint<?>, Breakpoint>() {
          @Override
          public Breakpoint fun(XBreakpoint<?> xBreakpoint) {
            return getJavaBreakpoint(xBreakpoint);
          }
        });
      }
    });
  }

  @Nullable
  public static Breakpoint getJavaBreakpoint(@Nullable final XBreakpoint xBreakpoint) {
    if (xBreakpoint == null) {
      return null;
    }
    Breakpoint breakpoint = xBreakpoint.getUserData(Breakpoint.DATA_KEY);
    if (breakpoint == null && xBreakpoint.getType() instanceof JavaBreakpointType) {
      Project project = ((XBreakpointBase)xBreakpoint).getProject();
      breakpoint = ((JavaBreakpointType)xBreakpoint.getType()).createJavaBreakpoint(project, xBreakpoint);
      xBreakpoint.putUserData(Breakpoint.DATA_KEY, breakpoint);
    }
    return breakpoint;
  }

  //interaction with RequestManagerImpl
  public void disableBreakpoints(@NotNull final DebugProcessImpl debugProcess) {
    final List<Breakpoint> breakpoints = getBreakpoints();
    if (!breakpoints.isEmpty()) {
      final RequestManagerImpl requestManager = debugProcess.getRequestsManager();
      for (Breakpoint breakpoint : breakpoints) {
        breakpoint.markVerified(requestManager.isVerified(breakpoint));
        requestManager.deleteRequest(breakpoint);
      }
      SwingUtilities.invokeLater(new Runnable() {
        @Override
        public void run() {
          updateBreakpointsUI();
        }
      });
    }
  }

  public void enableBreakpoints(final DebugProcessImpl debugProcess) {
    final List<Breakpoint> breakpoints = getBreakpoints();
    if (!breakpoints.isEmpty()) {
      for (Breakpoint breakpoint : breakpoints) {
        breakpoint.markVerified(false); // clean cached state
        breakpoint.createRequest(debugProcess);
      }
      SwingUtilities.invokeLater(new Runnable() {
        @Override
        public void run() {
          updateBreakpointsUI();
        }
      });
    }
  }

  public void applyThreadFilter(@NotNull final DebugProcessImpl debugProcess, @Nullable ThreadReference newFilterThread) {
    final RequestManagerImpl requestManager = debugProcess.getRequestsManager();
    final ThreadReference oldFilterThread = requestManager.getFilterThread();
    if (Comparing.equal(newFilterThread, oldFilterThread)) {
      // the filter already added
      return;
    }
    requestManager.setFilterThread(newFilterThread);
    if (newFilterThread == null || oldFilterThread != null) {
      final List<Breakpoint> breakpoints = getBreakpoints();
      for (Breakpoint breakpoint : breakpoints) {
        if (LineBreakpoint.CATEGORY.equals(breakpoint.getCategory()) || MethodBreakpoint.CATEGORY.equals(breakpoint.getCategory())) {
          requestManager.deleteRequest(breakpoint);
          breakpoint.createRequest(debugProcess);
        }
      }
    }
    else {
      // important! need to add filter to _existing_ requests, otherwise Requestor->Request mapping will be lost
      // and debugger trees will not be restored to original state
      abstract class FilterSetter <T extends EventRequest> {
         void applyFilter(@NotNull final List<T> requests, final ThreadReference thread) {
          for (T request : requests) {
            try {
              final boolean wasEnabled = request.isEnabled();
              if (wasEnabled) {
                request.disable();
              }
              addFilter(request, thread);
              if (wasEnabled) {
                request.enable();
              }
            }
            catch (InternalException e) {
              LOG.info(e);
            }
            catch (InvalidRequestStateException e) {
              LOG.info(e);
            }
          }
        }
        protected abstract void addFilter(final T request, final ThreadReference thread);
      }

      final EventRequestManager eventRequestManager = requestManager.getVMRequestManager();
      if (eventRequestManager != null) {
        new FilterSetter<BreakpointRequest>() {
          @Override
          protected void addFilter(@NotNull final BreakpointRequest request, final ThreadReference thread) {
            request.addThreadFilter(thread);
          }
        }.applyFilter(eventRequestManager.breakpointRequests(), newFilterThread);

        new FilterSetter<MethodEntryRequest>() {
          @Override
          protected void addFilter(@NotNull final MethodEntryRequest request, final ThreadReference thread) {
            request.addThreadFilter(thread);
          }
        }.applyFilter(eventRequestManager.methodEntryRequests(), newFilterThread);

        new FilterSetter<MethodExitRequest>() {
          @Override
          protected void addFilter(@NotNull final MethodExitRequest request, final ThreadReference thread) {
            request.addThreadFilter(thread);
          }
        }.applyFilter(eventRequestManager.methodExitRequests(), newFilterThread);
      }
    }
  }

  public void updateBreakpointsUI() {
    ApplicationManager.getApplication().assertIsDispatchThread();
    for (Breakpoint breakpoint : getBreakpoints()) {
      breakpoint.updateUI();
    }
  }

  public void reloadBreakpoints() {
    ApplicationManager.getApplication().assertIsDispatchThread();

    for (Breakpoint breakpoint : getBreakpoints()) {
      breakpoint.reload();
    }
  }

  public void fireBreakpointChanged(Breakpoint breakpoint) {
    breakpoint.reload();
    breakpoint.updateUI();
  }

  public void setBreakpointEnabled(@NotNull final Breakpoint breakpoint, final boolean enabled) {
    if (breakpoint.isEnabled() != enabled) {
      breakpoint.setEnabled(enabled);
    }
  }

  @Nullable
  public Breakpoint findMasterBreakpoint(@NotNull Breakpoint dependentBreakpoint) {
    XDependentBreakpointManager dependentBreakpointManager = ((XBreakpointManagerImpl)getXBreakpointManager()).getDependentBreakpointManager();
    return getJavaBreakpoint(dependentBreakpointManager.getMasterBreakpoint(dependentBreakpoint.myXBreakpoint));
  }

  public String getProperty(String name) {
    return myUIProperties.get(name);
  }
  
  public String setProperty(String name, String value) {
    return myUIProperties.put(name, value);
  }
}


File: java/debugger/impl/src/com/intellij/debugger/ui/breakpoints/RunToCursorBreakpoint.java
/*
 * Copyright 2000-2014 JetBrains s.r.o.
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
package com.intellij.debugger.ui.breakpoints;

import com.intellij.debugger.SourcePosition;
import com.intellij.debugger.engine.DebugProcessImpl;
import com.intellij.openapi.editor.Document;
import com.intellij.openapi.fileEditor.FileDocumentManager;
import com.intellij.openapi.project.Project;
import com.intellij.openapi.vfs.VirtualFile;
import com.intellij.psi.PsiFile;
import com.intellij.psi.PsiManager;
import org.jetbrains.annotations.NotNull;
import org.jetbrains.annotations.Nullable;

/**
 * @author Eugene Zhuravlev
 *         Date: Sep 13, 2006
 */
public class RunToCursorBreakpoint extends LineBreakpoint {
  private final boolean myRestoreBreakpoints;
  @NotNull
  protected final SourcePosition myCustomPosition;
  private String mySuspendPolicy;

  protected RunToCursorBreakpoint(@NotNull Project project, @NotNull SourcePosition pos, boolean restoreBreakpoints) {
    super(project, null);
    myCustomPosition = pos;
    setVisible(false);
    myRestoreBreakpoints = restoreBreakpoints;
  }

  @Override
  public SourcePosition getSourcePosition() {
    return myCustomPosition;
  }

  @Override
  public int getLineIndex() {
    return myCustomPosition.getLine();
  }

  @Override
  public void reload() {
  }

  @Override
  public String getSuspendPolicy() {
    return mySuspendPolicy;
  }

  public void setSuspendPolicy(String policy) {
    mySuspendPolicy = policy;
  }

  protected boolean isLogEnabled() {
    return false;
  }

  @Override
  protected boolean isLogExpressionEnabled() {
    return false;
  }

  @Override
  public boolean isEnabled() {
    return true;
  }

  public boolean isCountFilterEnabled() {
    return false;
  }

  public boolean isClassFiltersEnabled() {
    return false;
  }

  public boolean isInstanceFiltersEnabled() {
    return false;
  }

  @Override
  protected boolean isConditionEnabled() {
    return false;
  }

  public boolean isRestoreBreakpoints() {
    return myRestoreBreakpoints;
  }

  @Override
  public boolean isVisible() {
    return false;
  }

  @Override
  public boolean isValid() {
    return true;
  }

  @Override
  protected boolean isMuted(@NotNull final DebugProcessImpl debugProcess) {
    return false;  // always enabled
  }

  @Nullable
  protected static RunToCursorBreakpoint create(@NotNull Project project, @NotNull Document document, int lineIndex, boolean restoreBreakpoints) {
    VirtualFile virtualFile = FileDocumentManager.getInstance().getFile(document);
    if (virtualFile == null) {
      return null;
    }

    PsiFile psiFile = PsiManager.getInstance(project).findFile(virtualFile);
    SourcePosition pos = SourcePosition.createFromLine(psiFile, lineIndex);

    return new RunToCursorBreakpoint(project, pos, restoreBreakpoints);
  }

  @Override
  protected boolean shouldCreateRequest(DebugProcessImpl debugProcess) {
    return debugProcess.isAttached() && debugProcess.getRequestsManager().findRequests(this).isEmpty();
  }
}


File: java/debugger/openapi/src/com/intellij/debugger/SourcePosition.java
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
package com.intellij.debugger;

import com.intellij.openapi.application.ApplicationManager;
import com.intellij.openapi.diagnostic.Logger;
import com.intellij.openapi.editor.Document;
import com.intellij.openapi.editor.Editor;
import com.intellij.openapi.fileEditor.FileEditorManager;
import com.intellij.openapi.fileEditor.OpenFileDescriptor;
import com.intellij.openapi.progress.ProcessCanceledException;
import com.intellij.openapi.project.Project;
import com.intellij.openapi.util.Comparing;
import com.intellij.openapi.util.Computable;
import com.intellij.openapi.vfs.VirtualFile;
import com.intellij.pom.Navigatable;
import com.intellij.psi.*;
import com.intellij.util.containers.ContainerUtil;
import org.jetbrains.annotations.NotNull;
import org.jetbrains.annotations.Nullable;

import java.lang.ref.WeakReference;
import java.util.List;

/**
 * User: lex
 * Date: Oct 24, 2003
 * Time: 8:23:06 PM
 */
public abstract class SourcePosition implements Navigatable{
  private static final Logger LOG = Logger.getInstance("#com.intellij.debugger.SourcePosition");
  @NotNull
  public abstract PsiFile getFile();

  public abstract PsiElement getElementAt();

  /**
   * @return a zero-based line number
   */
  public abstract int getLine();

  public abstract int getOffset();

  public abstract Editor openEditor(boolean requestFocus);

  private abstract static class SourcePositionCache extends SourcePosition {
    @NotNull private final PsiFile myFile;
    private long myModificationStamp = -1L;

    private WeakReference<PsiElement> myPsiElementRef;
    private Integer myLine;
    private Integer myOffset;

    public SourcePositionCache(@NotNull PsiFile file) {
      myFile = file;
      updateData();
    }

    @Override
    @NotNull
    public PsiFile getFile() {
      return myFile;
    }

    @Override
    public boolean canNavigate() {
      return getFile().isValid();
    }

    @Override
    public boolean canNavigateToSource() {
      return canNavigate();
    }

    @Override
    public void navigate(final boolean requestFocus) {
      ApplicationManager.getApplication().invokeLater(new Runnable() {
        @Override
        public void run() {
          if (!canNavigate()) {
            return;
          }
          openEditor(requestFocus);
        }
      });
    }

    @Override
    public Editor openEditor(final boolean requestFocus) {
      final PsiFile psiFile = getFile();
      final Project project = psiFile.getProject();
      if (project.isDisposed()) {
        return null;
      }
      final VirtualFile virtualFile = psiFile.getVirtualFile();
      if (virtualFile == null || !virtualFile.isValid()) {
        return null;
      }
      final int offset = getOffset();
      if (offset < 0) {
        return null;
      }
      return FileEditorManager.getInstance(project).openTextEditor(new OpenFileDescriptor(project, virtualFile, offset), requestFocus);
    }

    private void updateData() {
      if(dataUpdateNeeded()) {
        myModificationStamp = myFile.getModificationStamp();
        myLine = null;
        myOffset = null;
        myPsiElementRef = null;
      }
    }

    private boolean dataUpdateNeeded() {
      if (myModificationStamp != myFile.getModificationStamp()) {
        return true;
      }
      final PsiElement psiElement = myPsiElementRef != null ? myPsiElementRef.get() : null;
      return psiElement != null && !ApplicationManager.getApplication().runReadAction(new Computable<Boolean>() {
        @Override
        public Boolean compute() {
          return psiElement.isValid();
        }
      });
    }

    @Override
    public int getLine() {
      updateData();
      if (myLine == null) {
        myLine = calcLine();
      }
      return myLine.intValue();
    }

    @Override
    public int getOffset() {
      updateData();
      if (myOffset == null) {
        myOffset = calcOffset();
      }
      return myOffset.intValue();
    }

    @Override
    public PsiElement getElementAt() {
      updateData();
      PsiElement element = myPsiElementRef != null ? myPsiElementRef.get() : null;
      if (element == null) {
        element = calcPsiElement();
        myPsiElementRef = new WeakReference<PsiElement>(element);
        return element;
      }
      return element;
    }

    protected int calcLine() {
      final PsiFile file = getFile();
      Document document = null;
      try {
        document = PsiDocumentManager.getInstance(file.getProject()).getDocument(file);
        if (document == null) { // may be decompiled psi - try to get document for the original file
          document = PsiDocumentManager.getInstance(file.getProject()).getDocument(file.getOriginalFile());
        }
      }
      catch (ProcessCanceledException ignored) {}
      catch (Throwable e) {
        LOG.error(e);
      }
      if (document != null) {
        try {
          return document.getLineNumber(calcOffset());
        }
        catch (IndexOutOfBoundsException e) {
          // may happen if document has been changed since the this SourcePosition was created
        }
      }
      return -1;
    }

    protected int calcOffset() {
      final PsiFile file = getFile();
      final Document document = PsiDocumentManager.getInstance(file.getProject()).getDocument(file);
      if (document != null) {
        try {
          return document.getLineStartOffset(calcLine());
        }
        catch (IndexOutOfBoundsException e) {
          // may happen if document has been changed since the this SourcePosition was created
        }
      }
      return -1;
    }

    @Nullable
    protected PsiElement calcPsiElement() {
      // currently PsiDocumentManager does not store documents for mirror file, so we store original file
      PsiFile origPsiFile = getFile();
      final PsiFile psiFile = origPsiFile instanceof PsiCompiledFile ? ((PsiCompiledFile)origPsiFile).getDecompiledPsiFile() : origPsiFile;
      int lineNumber = getLine();
      if(lineNumber < 0) {
        return psiFile;
      }

      final Document document = PsiDocumentManager.getInstance(origPsiFile.getProject()).getDocument(origPsiFile);
      if (document == null) {
        return null;
      }
      if (lineNumber >= document.getLineCount()) {
        return psiFile;
      }
      final int startOffset = document.getLineStartOffset(lineNumber);
      if(startOffset == -1) {
        return null;
      }

      return ApplicationManager.getApplication().runReadAction(new Computable<PsiElement>() {
        @Override
        public PsiElement compute() {
          PsiElement rootElement = psiFile;

          List<PsiFile> allFiles = psiFile.getViewProvider().getAllFiles();
          if (allFiles.size() > 1) { // jsp & gsp
            PsiClassOwner owner = ContainerUtil.findInstance(allFiles, PsiClassOwner.class);
            if (owner != null) {
              PsiClass[] classes = owner.getClasses();
              if (classes.length == 1 && classes[0] instanceof SyntheticElement) {
                rootElement = classes[0];
              }
            }
          }

          PsiElement element = null;
          int offset = startOffset;
          while (true) {
            final CharSequence charsSequence = document.getCharsSequence();
            for (; offset < charsSequence.length(); offset++) {
              char c = charsSequence.charAt(offset);
              if (c != ' ' && c != '\t') {
                break;
              }
            }
            if (offset >= charsSequence.length()) break;

            element = rootElement.findElementAt(offset);

            if (element instanceof PsiComment) {
              offset = element.getTextRange().getEndOffset() + 1;
            }
            else {
              break;
            }
          }
          if (element != null && element.getParent() instanceof PsiForStatement) {
            return ((PsiForStatement)element.getParent()).getInitialization();
          }
          return element;
        }
      });
    }
  }

  public static SourcePosition createFromLineComputable(final PsiFile file, final Computable<Integer> line) {
    return new SourcePositionCache(file) {
      @Override
      protected int calcLine() {
        return line.compute();
      }
    };
  }

  public static SourcePosition createFromLine(final PsiFile file, final int line) {
    return new SourcePositionCache(file) {
      @Override
      protected int calcLine() {
        return line;
      }

      @Override
      public String toString() {
        return getFile().getName() + ":" + line;
      }
    };
  }

  public static SourcePosition createFromOffset(final PsiFile file, final int offset) {
    return new SourcePositionCache(file) {

      @Override
      protected int calcOffset() {
        return offset;
      }

      @Override
      public String toString() {
        return getFile().getName() + " offset " + offset;
      }
    };
  }
     
  public static SourcePosition createFromElement(PsiElement element) {
    ApplicationManager.getApplication().assertReadAccessAllowed();
    PsiElement navigationElement = element.getNavigationElement();
    final SmartPsiElementPointer<PsiElement> pointer =
      SmartPointerManager.getInstance(navigationElement.getProject()).createSmartPsiElementPointer(navigationElement);
    final PsiFile psiFile;
    if (JspPsiUtil.isInJspFile(navigationElement)) {
      psiFile = JspPsiUtil.getJspFile(navigationElement);
    }
    else {
      psiFile = navigationElement.getContainingFile();
    }
    return new SourcePositionCache(psiFile) {
      @Override
      protected PsiElement calcPsiElement() {
        ApplicationManager.getApplication().assertReadAccessAllowed();
        return pointer.getElement();
      }

      @Override
      protected int calcOffset() {
        return ApplicationManager.getApplication().runReadAction(new Computable<Integer>() {
          @Override
          public Integer compute() {
            PsiElement elem = pointer.getElement();
            return elem != null ? elem.getTextOffset() : -1;
          }
        });
      }
    };
  }

  public boolean equals(Object o) {
    if(o instanceof SourcePosition) {
      SourcePosition sourcePosition = (SourcePosition)o;
      return Comparing.equal(sourcePosition.getFile(), getFile()) && sourcePosition.getOffset() == getOffset();
    }

    return false;
  }
}


File: platform/xdebugger-impl/src/com/intellij/xdebugger/impl/XDebuggerUtilImpl.java
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
package com.intellij.xdebugger.impl;

import com.intellij.lang.Language;
import com.intellij.openapi.actionSystem.CommonDataKeys;
import com.intellij.openapi.actionSystem.DataContext;
import com.intellij.openapi.application.Result;
import com.intellij.openapi.application.WriteAction;
import com.intellij.openapi.editor.Caret;
import com.intellij.openapi.editor.Document;
import com.intellij.openapi.editor.Editor;
import com.intellij.openapi.fileEditor.FileDocumentManager;
import com.intellij.openapi.fileEditor.FileEditorManager;
import com.intellij.openapi.fileEditor.OpenFileDescriptor;
import com.intellij.openapi.fileTypes.StdFileTypes;
import com.intellij.openapi.project.Project;
import com.intellij.openapi.util.text.StringUtil;
import com.intellij.openapi.vfs.VirtualFile;
import com.intellij.psi.*;
import com.intellij.psi.impl.source.tree.injected.InjectedLanguageUtil;
import com.intellij.psi.util.PsiTreeUtil;
import com.intellij.util.Processor;
import com.intellij.xdebugger.*;
import com.intellij.xdebugger.breakpoints.*;
import com.intellij.xdebugger.breakpoints.ui.XBreakpointGroupingRule;
import com.intellij.xdebugger.evaluation.EvaluationMode;
import com.intellij.xdebugger.evaluation.XDebuggerEvaluator;
import com.intellij.xdebugger.frame.XExecutionStack;
import com.intellij.xdebugger.frame.XStackFrame;
import com.intellij.xdebugger.frame.XSuspendContext;
import com.intellij.xdebugger.frame.XValueContainer;
import com.intellij.xdebugger.impl.breakpoints.XBreakpointUtil;
import com.intellij.xdebugger.impl.breakpoints.XExpressionImpl;
import com.intellij.xdebugger.impl.breakpoints.ui.grouping.XBreakpointFileGroupingRule;
import com.intellij.xdebugger.impl.evaluate.quick.common.ValueLookupManager;
import com.intellij.xdebugger.impl.settings.XDebuggerSettingsManager;
import com.intellij.xdebugger.impl.ui.tree.actions.XDebuggerTreeActionBase;
import com.intellij.xdebugger.settings.XDebuggerSettings;
import gnu.trove.THashMap;
import org.jetbrains.annotations.NotNull;
import org.jetbrains.annotations.Nullable;

import java.util.*;

/**
 * @author nik
 */
public class XDebuggerUtilImpl extends XDebuggerUtil {
  private XLineBreakpointType<?>[] myLineBreakpointTypes;
  private Map<Class<? extends XBreakpointType>, XBreakpointType<?,?>> myBreakpointTypeByClass;

  @Override
  public XLineBreakpointType<?>[] getLineBreakpointTypes() {
    if (myLineBreakpointTypes == null) {
      XBreakpointType[] types = XBreakpointUtil.getBreakpointTypes();
      List<XLineBreakpointType<?>> lineBreakpointTypes = new ArrayList<XLineBreakpointType<?>>();
      for (XBreakpointType type : types) {
        if (type instanceof XLineBreakpointType<?>) {
          lineBreakpointTypes.add((XLineBreakpointType<?>)type);
        }
      }
      myLineBreakpointTypes = lineBreakpointTypes.toArray(new XLineBreakpointType<?>[lineBreakpointTypes.size()]);
    }
    return myLineBreakpointTypes;
  }

  @Override
  public void toggleLineBreakpoint(@NotNull final Project project, @NotNull final VirtualFile file, final int line, boolean temporary) {
    XLineBreakpointType<?> typeWinner = null;
    for (XLineBreakpointType<?> type : getLineBreakpointTypes()) {
      if (type.canPutAt(file, line, project) && (typeWinner == null || type.getPriority() > typeWinner.getPriority())) {
        typeWinner = type;
      }
    }
    if (typeWinner != null) {
      toggleLineBreakpoint(project, typeWinner, file, line, temporary);
    }
  }

  @Override
  public boolean canPutBreakpointAt(@NotNull Project project, @NotNull VirtualFile file, int line) {
    for (XLineBreakpointType<?> type : getLineBreakpointTypes()) {
      if (type.canPutAt(file, line, project)) {
        return true;
      }
    }
    return false;
  }

  @Override
  public <P extends XBreakpointProperties> void toggleLineBreakpoint(@NotNull final Project project,
                                                                     @NotNull final XLineBreakpointType<P> type,
                                                                     @NotNull final VirtualFile file,
                                                                     final int line,
                                                                     final boolean temporary) {
    toggleAndReturnLineBreakpoint(project, type, file, line, temporary);
  }

  public static <P extends XBreakpointProperties> XLineBreakpoint toggleAndReturnLineBreakpoint(@NotNull final Project project,
                                                                                                @NotNull final XLineBreakpointType<P> type,
                                                                                                @NotNull final VirtualFile file,
                                                                                                final int line,
                                                                                                final boolean temporary) {
    return new WriteAction<XLineBreakpoint>() {
      @Override
      protected void run(@NotNull final Result<XLineBreakpoint> result) {
        XBreakpointManager breakpointManager = XDebuggerManager.getInstance(project).getBreakpointManager();
        XLineBreakpoint<P> breakpoint = breakpointManager.findBreakpointAtLine(type, file, line);
        if (breakpoint != null) {
          breakpointManager.removeBreakpoint(breakpoint);
        }
        else {
          P properties = type.createBreakpointProperties(file, line);
          result.setResult(breakpointManager.addLineBreakpoint(type, file.getUrl(), line, properties, temporary));
        }
      }
    }.execute().getResultObject();
  }

  @Override
  public void removeBreakpoint(final Project project, final XBreakpoint<?> breakpoint) {
    new WriteAction() {
      @Override
      protected void run(@NotNull final Result result) {
        XDebuggerManager.getInstance(project).getBreakpointManager().removeBreakpoint(breakpoint);
      }
    }.execute();
  }

  @Override
  public <B extends XBreakpoint<?>> XBreakpointType<B, ?> findBreakpointType(@NotNull Class<? extends XBreakpointType<B, ?>> typeClass) {
    if (myBreakpointTypeByClass == null) {
      myBreakpointTypeByClass = new THashMap<Class<? extends XBreakpointType>, XBreakpointType<?,?>>();
      for (XBreakpointType<?, ?> breakpointType : XBreakpointUtil.getBreakpointTypes()) {
        myBreakpointTypeByClass.put(breakpointType.getClass(), breakpointType);
      }
    }
    XBreakpointType<?, ?> type = myBreakpointTypeByClass.get(typeClass);
    //noinspection unchecked
    return (XBreakpointType<B, ?>)type;
  }

  @Override
  public <T extends XDebuggerSettings<?>> T getDebuggerSettings(Class<T> aClass) {
    return XDebuggerSettingsManager.getInstanceImpl().getSettings(aClass);
  }

  @Override
  public XValueContainer getValueContainer(DataContext dataContext) {
    return XDebuggerTreeActionBase.getSelectedValue(dataContext);
  }

  @Override
  @Nullable
  public XSourcePosition createPosition(final VirtualFile file, final int line) {
    return XSourcePositionImpl.create(file, line);
  }

  @Override
  @Nullable
  public XSourcePosition createPositionByOffset(final VirtualFile file, final int offset) {
    return XSourcePositionImpl.createByOffset(file, offset);
  }

  @Override
  public <B extends XLineBreakpoint<?>> XBreakpointGroupingRule<B, ?> getGroupingByFileRule() {
    return new XBreakpointFileGroupingRule<B>();
  }

  @Nullable
  public static XSourcePosition getCaretPosition(@NotNull Project project, DataContext context) {
    Editor editor = getEditor(project, context);
    if (editor == null) return null;

    final Document document = editor.getDocument();
    final int line = editor.getCaretModel().getLogicalPosition().line;
    VirtualFile file = FileDocumentManager.getInstance().getFile(document);
    return XSourcePositionImpl.create(file, line);
  }

  @NotNull
  public static Collection<XSourcePosition> getAllCaretsPositions(@NotNull Project project, DataContext context) {
    Editor editor = getEditor(project, context);
    if (editor == null) {
      return Collections.emptyList();
    }

    final Document document = editor.getDocument();
    VirtualFile file = FileDocumentManager.getInstance().getFile(document);
    Collection<XSourcePosition> res = new ArrayList<XSourcePosition>();
    List<Caret> carets = editor.getCaretModel().getAllCarets();
    for (Caret caret : carets) {
      int line = caret.getLogicalPosition().line;
      XSourcePositionImpl position = XSourcePositionImpl.create(file, line);
      if (position != null) {
        res.add(position);
      }
    }
    return res;
  }

  @Nullable
  private static Editor getEditor(@NotNull Project project, DataContext context) {
    Editor editor = CommonDataKeys.EDITOR.getData(context);
    if(editor == null) {
      return FileEditorManager.getInstance(project).getSelectedTextEditor();
    }
    return editor;
  }

  @Override
  public <B extends XBreakpoint<?>> Comparator<B> getDefaultBreakpointComparator(final XBreakpointType<B, ?> type) {
    return new Comparator<B>() {
      @Override
      public int compare(final B o1, final B o2) {
        return type.getDisplayText(o1).compareTo(type.getDisplayText(o2));
      }
    };
  }

  @Override
  public <P extends XBreakpointProperties> Comparator<XLineBreakpoint<P>> getDefaultLineBreakpointComparator() {
    return new Comparator<XLineBreakpoint<P>>() {
      @Override
      public int compare(final XLineBreakpoint<P> o1, final XLineBreakpoint<P> o2) {
        int fileCompare = o1.getFileUrl().compareTo(o2.getFileUrl());
        if (fileCompare != 0) return fileCompare;
        return o1.getLine() - o2.getLine();
      }
    };
  }

  @Nullable
  public static XDebuggerEvaluator getEvaluator(final XSuspendContext suspendContext) {
    XExecutionStack executionStack = suspendContext.getActiveExecutionStack();
    if (executionStack != null) {
      XStackFrame stackFrame = executionStack.getTopFrame();
      if (stackFrame != null) {
        return stackFrame.getEvaluator();
      }
    }
    return null;
  }

  @Override
  public void iterateLine(@NotNull Project project, @NotNull Document document, int line, @NotNull Processor<PsiElement> processor) {
    PsiFile file = PsiDocumentManager.getInstance(project).getPsiFile(document);
    if (file == null) {
      return;
    }

    int lineStart;
    int lineEnd;
    try {
      lineStart = document.getLineStartOffset(line);
      lineEnd = document.getLineEndOffset(line);
    }
    catch (IndexOutOfBoundsException ignored) {
      return;
    }

    PsiElement element;
    int offset = lineStart;

    if (file instanceof PsiCompiledFile) {
      file = ((PsiCompiledFile)file).getDecompiledPsiFile();
    }

    while (offset < lineEnd) {
      element = file.findElementAt(offset);
      if (element != null) {
        if (!processor.process(element)) {
          return;
        }
        else {
          offset = element.getTextRange().getEndOffset();
        }
      }
      else {
        offset++;
      }
    }
  }

  @Override
  public <B extends XLineBreakpoint<?>> List<XBreakpointGroupingRule<B, ?>> getGroupingByFileRuleAsList() {
    return Collections.<XBreakpointGroupingRule<B, ?>>singletonList(this.<B>getGroupingByFileRule());
  }

  @Override
  @Nullable
  public PsiElement findContextElement(@NotNull VirtualFile virtualFile, int offset, @NotNull Project project, boolean checkXml) {
    if (!virtualFile.isValid()) {
      return null;
    }

    Document document = FileDocumentManager.getInstance().getDocument(virtualFile);
    PsiFile file = document == null ? null : PsiManager.getInstance(project).findFile(virtualFile);
    if (file == null) {
      return null;
    }

    if (offset < 0) {
      offset = 0;
    }
    if (offset > document.getTextLength()) {
      offset = document.getTextLength();
    }
    int startOffset = offset;

    int lineEndOffset = document.getLineEndOffset(document.getLineNumber(offset));
    PsiElement result = null;
    do {
      PsiElement element = file.findElementAt(offset);
      if (!(element instanceof PsiWhiteSpace) && !(element instanceof PsiComment)) {
        result = element;
        break;
      }

      offset = element.getTextRange().getEndOffset() + 1;
    }
    while (offset < lineEndOffset);

    if (result == null) {
      result = file.findElementAt(startOffset);
    }

    if (checkXml && result != null && StdFileTypes.XML.getLanguage().equals(result.getLanguage())) {
      PsiLanguageInjectionHost parent = PsiTreeUtil.getParentOfType(result, PsiLanguageInjectionHost.class);
      if (parent != null) {
        result = InjectedLanguageUtil.findElementInInjected(parent, offset);
      }
    }
    return result;
  }

  @Override
  public void disableValueLookup(@NotNull Editor editor) {
    ValueLookupManager.DISABLE_VALUE_LOOKUP.set(editor, Boolean.TRUE);
  }

  @Nullable
  public static Editor createEditor(@NotNull OpenFileDescriptor descriptor) {
    return descriptor.canNavigate() ? FileEditorManager.getInstance(descriptor.getProject()).openTextEditor(descriptor, false) : null;
  }

  public static void rebuildAllSessionsViews(@Nullable Project project) {
    if (project == null) return;
    for (XDebugSession session : XDebuggerManager.getInstance(project).getDebugSessions()) {
      if (session.isSuspended()) {
        session.rebuildViews();
      }
    }
  }

  @NotNull
  @Override
  public XExpression createExpression(@NotNull String text, Language language, String custom, EvaluationMode mode) {
    return new XExpressionImpl(text, language, custom, mode);
  }

  public static boolean isEmptyExpression(@Nullable XExpression expression) {
    return expression == null || StringUtil.isEmptyOrSpaces(expression.getExpression());
  }
}
