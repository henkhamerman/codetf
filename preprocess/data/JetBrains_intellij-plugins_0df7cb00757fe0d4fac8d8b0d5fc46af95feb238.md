Refactoring Types: ['Extract Method']
rt/analyzer/DartAnalysisServerService.java
package com.jetbrains.lang.dart.analyzer;

import com.google.common.collect.Lists;
import com.google.common.collect.Maps;
import com.google.common.collect.Sets;
import com.google.dart.server.*;
import com.google.dart.server.generated.AnalysisServer;
import com.google.dart.server.internal.remote.DebugPrintStream;
import com.google.dart.server.internal.remote.FileReadMode;
import com.google.dart.server.internal.remote.RemoteAnalysisServerImpl;
import com.google.dart.server.internal.remote.StdioServerSocket;
import com.google.dart.server.utilities.logging.Logging;
import com.intellij.codeInsight.daemon.DaemonCodeAnalyzer;
import com.intellij.openapi.Disposable;
import com.intellij.openapi.application.ApplicationInfo;
import com.intellij.openapi.application.ApplicationManager;
import com.intellij.openapi.application.ApplicationNamesInfo;
import com.intellij.openapi.application.ModalityState;
import com.intellij.openapi.components.ServiceManager;
import com.intellij.openapi.diagnostic.Logger;
import com.intellij.openapi.editor.Document;
import com.intellij.openapi.editor.EditorFactory;
import com.intellij.openapi.editor.event.DocumentAdapter;
import com.intellij.openapi.editor.event.DocumentEvent;
import com.intellij.openapi.fileEditor.*;
import com.intellij.openapi.progress.ProgressIndicator;
import com.intellij.openapi.progress.ProgressManager;
import com.intellij.openapi.progress.Task;
import com.intellij.openapi.project.Project;
import com.intellij.openapi.roots.ProjectRootManager;
import com.intellij.openapi.util.Comparing;
import com.intellij.openapi.util.Disposer;
import com.intellij.openapi.util.Ref;
import com.intellij.openapi.util.io.FileUtil;
import com.intellij.openapi.util.registry.Registry;
import com.intellij.openapi.util.text.StringUtil;
import com.intellij.openapi.vfs.LocalFileSystem;
import com.intellij.openapi.vfs.VirtualFile;
import com.intellij.psi.PsiFile;
import com.intellij.psi.PsiManager;
import com.intellij.psi.impl.source.resolve.ResolveCache;
import com.intellij.util.Alarm;
import com.intellij.util.ArrayUtil;
import com.intellij.util.concurrency.Semaphore;
import com.intellij.util.net.NetUtils;
import com.intellij.xml.util.HtmlUtil;
import com.jetbrains.lang.dart.DartBundle;
import com.jetbrains.lang.dart.DartFileType;
import com.jetbrains.lang.dart.ide.errorTreeView.DartProblemsViewImpl;
import com.jetbrains.lang.dart.resolve.DartResolver;
import com.jetbrains.lang.dart.sdk.DartSdk;
import com.jetbrains.lang.dart.sdk.DartSdkUpdateChecker;
import com.jetbrains.lang.dart.util.PubspecYamlUtil;
import gnu.trove.THashMap;
import gnu.trove.THashSet;
import org.dartlang.analysis.server.protocol.*;
import org.jetbrains.annotations.Contract;
import org.jetbrains.annotations.NotNull;
import org.jetbrains.annotations.Nullable;

import java.util.*;
import java.util.concurrent.TimeUnit;
import java.util.concurrent.atomic.AtomicBoolean;

public class DartAnalysisServerService {

  public static final String MIN_SDK_VERSION = "1.12";

  private static final long CHECK_CANCELLED_PERIOD = 100;
  private static final long SEND_REQUEST_TIMEOUT = TimeUnit.SECONDS.toMillis(1);
  private static final long EDIT_FORMAT_TIMEOUT = TimeUnit.SECONDS.toMillis(3);
  private static final long EDIT_SORT_MEMBERS_TIMEOUT = TimeUnit.SECONDS.toMillis(3);
  private static final long GET_ERRORS_TIMEOUT = TimeUnit.SECONDS.toMillis(5);
  private static final long GET_ERRORS_LONGER_TIMEOUT = TimeUnit.SECONDS.toMillis(60);
  private static final long GET_FIXES_TIMEOUT = TimeUnit.SECONDS.toMillis(10);
  private static final long GET_SUGGESTIONS_TIMEOUT = TimeUnit.SECONDS.toMillis(1);
  private static final long GET_LIBRARY_DEPENDENCIES_TIMEOUT = TimeUnit.MINUTES.toMillis(5);
  private static final List<String> SERVER_SUBSCRIPTIONS = Collections.singletonList(ServerService.STATUS);
  private static final Logger LOG = Logger.getInstance("#com.jetbrains.lang.dart.analyzer.DartAnalysisServerService");

  private final Object myLock = new Object(); // Access all fields under this lock. Do not wait for server response under lock.
  @Nullable private AnalysisServer myServer;
  @Nullable private StdioServerSocket myServerSocket;

  @NotNull private String myServerVersion = "";
  @NotNull private String mySdkVersion = "";
  @Nullable private String mySdkHome = null;
  private final DartServerRootsHandler myRootsHandler = new DartServerRootsHandler();
  private final Map<String, Long> myFilePathWithOverlaidContentToTimestamp = new THashMap<String, Long>();
  private final List<String> myVisibleFiles = new ArrayList<String>();
  private final Set<String> myFilePathsWithUnsentChanges = Sets.newConcurrentHashSet();

  @NotNull private final Queue<CompletionInfo> myCompletionInfos = new LinkedList<CompletionInfo>();
  @NotNull private final Map<String, List<PluginHighlightRegion>> myHighlightData = Maps.newHashMap();
  @NotNull private final Map<String, List<PluginNavigationRegion>> myNavigationData = Maps.newHashMap();

  @NotNull final AtomicBoolean myServerBusy = new AtomicBoolean(false);
  @NotNull final Alarm myShowServerProgressAlarm = new Alarm();

  private final AnalysisServerListener myAnalysisServerListener = new AnalysisServerListenerAdapter() {

    @Override
    public void computedErrors(@NotNull final String file, @NotNull final List<AnalysisError> errors) {
      updateProblemsView(DartProblemsViewImpl.createGroupName(file), errors);
    }

    @Override
    public void computedHighlights(String file, List<HighlightRegion> regions) {
      if (DartResolver.isServerDrivenResolution()) {
        file = FileUtil.toSystemIndependentName(file);
        // Ignore notifications for files that has been changed, but server does not know about them yet.
        if (myFilePathsWithUnsentChanges.contains(file)) {
          return;
        }
        // Convert HighlightRegion(s) into PluginHighlightRegion(s).
        List<PluginHighlightRegion> pluginRegions = Lists.newArrayList();
        for (HighlightRegion region : regions) {
          pluginRegions.add(new PluginHighlightRegion(region));
        }
        // Put PluginHighlightRegion(s).
        synchronized (myHighlightData) {
          myHighlightData.put(file, pluginRegions);
        }
        // Force (re)highlighting.
        forceFileAnnotation(file);
      }
    }

    @Override
    public void computedNavigation(String file, List<NavigationRegion> regions) {
      if (DartResolver.isServerDrivenResolution()) {
        file = FileUtil.toSystemIndependentName(file);
        // Ignore notifications for files that has been changed, but server does not know about them yet.
        if (myFilePathsWithUnsentChanges.contains(file)) {
          return;
        }
        // Convert NavigationRegion(s) into PluginNavigationRegion(s).
        List<PluginNavigationRegion> pluginRegions = new ArrayList<PluginNavigationRegion>(regions.size());
        for (NavigationRegion region : regions) {
          pluginRegions.add(new PluginNavigationRegion(region));
        }
        // Put PluginNavigationRegion(s).
        synchronized (myNavigationData) {
          myNavigationData.put(file, pluginRegions);
        }
        // Force (re)highlighting.
        forceFileAnnotation(file);
      }
    }

    @Override
    public void flushedResults(List<String> files) {
      for (String file : files) {
        updateProblemsView(DartProblemsViewImpl.createGroupName(file), AnalysisError.EMPTY_LIST);
      }
    }

    @Override
    public void computedCompletion(@NotNull final String completionId,
                                   final int replacementOffset,
                                   final int replacementLength,
                                   @NotNull final List<CompletionSuggestion> completions,
                                   final boolean isLast) {
      synchronized (myCompletionInfos) {
        myCompletionInfos.add(new CompletionInfo(completionId, replacementOffset, replacementLength, completions, isLast));
        myCompletionInfos.notifyAll();
      }
    }

    @Override
    public void serverConnected(@Nullable String version) {
      myServerVersion = version != null ? version : "";
    }

    @Override
    public void serverError(boolean isFatal, @Nullable String message, @Nullable String stackTrace) {
      if (message == null) message = "<no error message>";
      if (stackTrace == null) stackTrace = "<no stack trace>";
      LOG.error("Dart analysis server, SDK version " + mySdkVersion +
                ", server version " + myServerVersion +
                ", " + (isFatal ? "FATAL " : "") + "error: " + message + "\n" + stackTrace);

      if (isFatal) {
        onServerStopped();
      }
    }

    @Override
    public void serverStatus(@Nullable final AnalysisStatus analysisStatus, @Nullable final PubStatus pubStatus) {
      if (analysisStatus != null && analysisStatus.isAnalyzing() || pubStatus != null && pubStatus.isListingPackageDirs()) {
        if (myServerBusy.compareAndSet(false, true)) {
          for (final Project project : myRootsHandler.getTrackedProjects()) {
            final Runnable delayedRunnable = new Runnable() {
              public void run() {
                if (project.isDisposed() || !myServerBusy.get()) return;

                final Task.Backgroundable task =
                  new Task.Backgroundable(project, DartBundle.message("dart.analysis.progress.title"), false) {
                    @Override
                    public void run(@NotNull ProgressIndicator indicator) {
                      if (myServerBusy.get()) {
                        try {
                          synchronized (myServerBusy) {
                            //noinspection WaitNotInLoop
                            myServerBusy.wait();
                          }
                        }
                        catch (InterruptedException e) {/* unlucky */}
                      }
                    }
                  };

                ProgressManager.getInstance().run(task);
              }
            };

            // 50ms delay to minimize blinking in case of consequent start-stop-start-stop-... events that happen with pubStatus events
            // 300ms delay to avoid showing progress for very fast analysis start-stop cycle that happens with analysisStatus events
            final int delay = pubStatus != null && pubStatus.isListingPackageDirs() ? 50 : 300;
            myShowServerProgressAlarm.addRequest(delayedRunnable, delay, ModalityState.any());
          }
        }
      }
      else {
        stopShowingServerProgress();
      }
    }
  };

  public static boolean isDartSdkVersionSufficient(@NotNull final DartSdk sdk) {
    return StringUtil.compareVersionNumbers(sdk.getVersion(), MIN_SDK_VERSION) >= 0;
  }

  private void forceFileAnnotation(String file) {
    final VirtualFile virtualFile = LocalFileSystem.getInstance().findFileByPath(file);
    if (virtualFile != null) {
      Set<Project> projects = myRootsHandler.getTrackedProjects();
      for (final Project project : projects) {
        ResolveCache.getInstance(project).clearCache(true);
        DaemonCodeAnalyzer.getInstance(project).restart();
      }
    }
  }

  public void addCompletions(@NotNull final String completionId,
                             @NotNull final CompletionSuggestionProcessor processor) {
    while (true) {
      ProgressManager.checkCanceled();

      synchronized (myCompletionInfos) {
        // todo in case of several AnalysisServerListenerAdapter.computedCompletion() invocations for one completion (only the last
        // invocation has isLast==true) it looks like each next List<CompletionSuggestion> also contains all items that were already
        // given in previous invocations. If it is by design we should optimize cycle and handle only the last in queue.

        CompletionInfo completionInfo;
        while ((completionInfo = myCompletionInfos.poll()) != null) {
          if (!completionInfo.myCompletionId.equals(completionId)) continue;

          for (final CompletionSuggestion completion : completionInfo.myCompletions) {
            processor.process(completion);
          }

          if (completionInfo.isLast) return;
        }

        try {
          myCompletionInfos.wait(CHECK_CANCELLED_PERIOD);
        }
        catch (InterruptedException e) {
          return;
        }
      }
    }
  }

  public static class FormatResult {
    @Nullable private final List<SourceEdit> myEdits;
    private final int myOffset;
    private final int myLength;

    public FormatResult(@Nullable final List<SourceEdit> edits, final int selectionOffset, final int selectionLength) {
      myEdits = edits;
      myOffset = selectionOffset;
      myLength = selectionLength;
    }

    public int getLength() {
      return myLength;
    }

    public int getOffset() {
      return myOffset;
    }

    @Nullable
    public List<SourceEdit> getEdits() {
      return myEdits;
    }
  }

  public static class LibraryDependenciesResult {
    @Nullable final String[] libraries;

    @Nullable final Map<String, Map<String, List<String>>> packageMap;

    public LibraryDependenciesResult(@Nullable final String[] libraries,
                                     @Nullable final Map<String, Map<String, List<String>>> packageMap) {
      this.libraries = libraries;
      this.packageMap = packageMap;
    }

    @Nullable
    public String[] getLibraries() {
      return libraries;
    }

    @Nullable
    public Map<String, Map<String, List<String>>> getPackageMap() {
      return packageMap;
    }
  }

  public DartAnalysisServerService() {
    Disposer.register(ApplicationManager.getApplication(), new Disposable() {
      public void dispose() {
        stopServer();
      }
    });

    Logging.setLogger(new com.google.dart.server.utilities.logging.Logger() {
      @Override
      public void logError(String message) {
        LOG.error(message);
      }

      @Override
      public void logError(String message, Throwable exception) {
        LOG.error(message, exception);
      }

      @Override
      public void logInformation(String message) {
        LOG.debug(message);
      }

      @Override
      public void logInformation(String message, Throwable exception) {
        LOG.debug(message, exception);
      }
    });

    ApplicationManager.getApplication().getMessageBus().connect()
      .subscribe(FileEditorManagerListener.FILE_EDITOR_MANAGER, new FileEditorManagerAdapter() {
        @Override
        public void fileOpened(@NotNull final FileEditorManager source, @NotNull final VirtualFile file) {
          if (PubspecYamlUtil.PUBSPEC_YAML.equals(file.getName()) || file.getFileType() == DartFileType.INSTANCE) {
            DartSdkUpdateChecker.mayBeCheckForSdkUpdate(source.getProject());
          }

          if (isDartOrHtmlFile(file)) {
            updateVisibleFiles();
          }
        }

        @Override
        public void selectionChanged(@NotNull FileEditorManagerEvent event) {
          if (isDartOrHtmlFile(event.getOldFile()) || isDartOrHtmlFile(event.getNewFile())) {
            updateVisibleFiles();
          }
        }

        @Override
        public void fileClosed(@NotNull final FileEditorManager source, @NotNull final VirtualFile file) {
          if (isDartOrHtmlFile(file)) {
            updateVisibleFiles();
          }
        }
      });

    EditorFactory.getInstance().getEventMulticaster().addDocumentListener(new DocumentAdapter() {
      @Override
      public void beforeDocumentChange(DocumentEvent e) {
        updateInformationFromServer(e);
      }
    });
  }

  @NotNull
  public static DartAnalysisServerService getInstance() {
    return ServiceManager.getService(DartAnalysisServerService.class);
  }

  /**
   * Returns {@link PluginHighlightRegion}s for the given file.
   * Empty if no regions.
   */
  @NotNull
  public List<PluginHighlightRegion> getHighlight(@NotNull final VirtualFile file) {
    synchronized (myHighlightData) {
      List<PluginHighlightRegion> regions = myHighlightData.get(file.getPath());
      if (regions == null) {
        return PluginHighlightRegion.EMPTY_LIST;
      }
      return regions;
    }
  }

  /**
   * Returns {@link PluginNavigationRegion}s for the given file.
   * Empty if no regions.
   */
  @NotNull
  public List<PluginNavigationRegion> getNavigation(@NotNull final VirtualFile file) {
    synchronized (myNavigationData) {
      List<PluginNavigationRegion> regions = myNavigationData.get(file.getPath());
      if (regions == null) {
        return PluginNavigationRegion.EMPTY_LIST;
      }
      return regions;
    }
  }

  void updateVisibleFiles() {
    synchronized (myLock) {
      final List<String> newVisibleFiles = new ArrayList<String>();

      for (Project project : myRootsHandler.getTrackedProjects()) {
        for (VirtualFile file : FileEditorManager.getInstance(project).getSelectedFiles()) {
          if (file.isInLocalFileSystem() && isDartOrHtmlFile(file)) {
            newVisibleFiles.add(FileUtil.toSystemDependentName(file.getPath()));
          }
        }
      }

      if (!Comparing.haveEqualElements(myVisibleFiles, newVisibleFiles)) {
        myVisibleFiles.clear();
        myVisibleFiles.addAll(newVisibleFiles);
        analysis_setPriorityFiles();
        analysis_setSubscriptions();
      }
    }
  }

  @Contract("null->false")
  private static boolean isDartOrHtmlFile(@Nullable final VirtualFile file) {
    return file != null && (file.getFileType() == DartFileType.INSTANCE || HtmlUtil.isHtmlFile(file));
  }

  public void updateFilesContent() {
    //TODO: consider using DocumentListener to collect deltas instead of sending the whole Document.getText() each time
    final Set<String> oldTrackedFiles = new THashSet<String>(myFilePathWithOverlaidContentToTimestamp.keySet());
    final Map<String, Object> filesToUpdate = new THashMap<String, Object>();

    synchronized (myLock) {
      if (myServer == null) return;

      final FileDocumentManager fileDocumentManager = FileDocumentManager.getInstance();
      for (Document document : fileDocumentManager.getUnsavedDocuments()) {
        final VirtualFile file = fileDocumentManager.getFile(document);
        if (isDartOrHtmlFile(file)) {
          oldTrackedFiles.remove(file.getPath());

          final Long oldTimestamp = myFilePathWithOverlaidContentToTimestamp.get(file.getPath());
          if (oldTimestamp == null || document.getModificationStamp() != oldTimestamp) {
            filesToUpdate.put(FileUtil.toSystemDependentName(file.getPath()), new AddContentOverlay(document.getText()));
            myFilePathWithOverlaidContentToTimestamp.put(file.getPath(), document.getModificationStamp());
          }
        }
      }

      // oldTrackedFiles at this point contains only those files that are not in FileDocumentManager.getUnsavedDocuments() any more
      for (String oldPath : oldTrackedFiles) {
        final Long removed = myFilePathWithOverlaidContentToTimestamp.remove(oldPath);
        LOG.assertTrue(removed != null, oldPath);
        filesToUpdate.put(FileUtil.toSystemDependentName(oldPath), new RemoveContentOverlay());
      }

      if (LOG.isDebugEnabled()) {
        if (!filesToUpdate.isEmpty()) {
          LOG.debug("Sending overlaid content of the following files:\n" + StringUtil.join(filesToUpdate.keySet(), ",\n"));
        }

        if (!oldTrackedFiles.isEmpty()) {
          LOG.debug("Removing overlaid content of the following files:\n" + StringUtil.join(oldTrackedFiles, ",\n"));
        }
      }

      if (!filesToUpdate.isEmpty()) {
        final UpdateContentConsumer consumer = new UpdateContentConsumer() {
          @Override
          public void onResponse() {
            myFilePathsWithUnsentChanges.clear();
          }
        };

        final AnalysisServer server = myServer;
        final boolean ok = runInPooledThreadAndWait(new Runnable() {
          @Override
          public void run() {
            server.analysis_updateContent(filesToUpdate, consumer);
          }
        }, "analysis_updateContent(" + StringUtil.join(filesToUpdate.keySet(), ", ") + ")", SEND_REQUEST_TIMEOUT);

        if (!ok) {
          stopServer();
          //noinspection UnnecessaryReturnStatement
          return;
        }
      }
    }
  }

  public boolean updateRoots(@NotNull final List<String> includedRoots,
                             @NotNull final List<String> excludedRoots,
                             @Nullable final Map<String, String> packageRoots) {
    synchronized (myLock) {
      if (myServer == null) return false;

      if (LOG.isDebugEnabled()) {
        LOG.debug("analysis_setAnalysisRoots, included:\n" + StringUtil.join(includedRoots, ",\n") +
                  "\nexcluded:\n" + StringUtil.join(excludedRoots, ",\n"));
      }

      final AnalysisServer server = myServer;
      final String runnableInfo = "analysis_setAnalysisRoots(" + StringUtil.join(includedRoots, ", ") + "; " +
                                  StringUtil.join(excludedRoots, ", ") + ")";
      final boolean ok = runInPooledThreadAndWait(new Runnable() {
        @Override
        public void run() {
          server.analysis_setAnalysisRoots(includedRoots, excludedRoots, packageRoots);
        }
      }, runnableInfo, SEND_REQUEST_TIMEOUT);

      if (!ok) {
        stopServer();
        return false;
      }

      return true;
    }
  }

  private void updateProblemsView(@NotNull final String filePath, @NotNull final List<AnalysisError> errors) {
    ApplicationManager.getApplication().runReadAction(new Runnable() {
      @Override
      public void run() {
        final VirtualFile vFile = LocalFileSystem.getInstance().findFileByPath(filePath);

        for (final Project project : myRootsHandler.getTrackedProjects()) {
          if (project.isDisposed()) continue;

          if (vFile != null && ProjectRootManager.getInstance(project).getFileIndex().isInContent(vFile)) {
            DartProblemsViewImpl.getInstance(project).updateErrorsForFile(vFile, errors);
          }
          else {
            DartProblemsViewImpl.getInstance(project).removeErrorsForFile(filePath);
          }
        }
      }
    });
  }

  @Nullable
  public AnalysisError[] analysis_getErrors(@NotNull final DartAnalysisServerAnnotator.AnnotatorInfo info) {
    final Ref<AnalysisError[]> resultRef = new Ref<AnalysisError[]>();
    final Semaphore semaphore = new Semaphore();

    try {
      synchronized (myLock) {
        if (myServer == null) return null;

        semaphore.down();

        final String filePath = FileUtil.toSystemDependentName(info.myFilePath);

        LOG.debug("analysis_getErrors(" + filePath + ")");

        final GetErrorsConsumer consumer = new GetErrorsConsumer() {
          @Override
          public void computedErrors(final AnalysisError[] errors) {
            if (semaphore.tryUp()) {
              resultRef.set(errors);
            }
            else {
              // semaphore unlocked by timeout, schedule to highlight the file again
              LOG.info("analysis_getErrors() took too long for file " + filePath + ", restarting daemon");

              ApplicationManager.getApplication().runReadAction(new Runnable() {
                @Override
                public void run() {
                  final VirtualFile vFile =
                    info.myProject.isDisposed() ? null : LocalFileSystem.getInstance().findFileByPath(info.myFilePath);
                  final PsiFile psiFile = vFile == null ? null : PsiManager.getInstance(info.myProject).findFile(vFile);
                  if (psiFile != null) {
                    DaemonCodeAnalyzer.getInstance(info.myProject).restart(psiFile);
                  }
                }
              });
            }
          }

          @Override
          public void onError(final RequestError error) {
            logError("analysis_getErrors()", filePath, error);
            semaphore.up();
          }
        };

        final AnalysisServer server = myServer;
        final boolean ok = runInPooledThreadAndWait(new Runnable() {
          @Override
          public void run() {
            server.analysis_getErrors(filePath, consumer);
          }
        }, "analysis_getErrors(" + filePath + ")", SEND_REQUEST_TIMEOUT);

        if (!ok) {
          stopServer();
          return null;
        }
      }

      final long timeout = info.isLongerAnalysisTimeout() || ApplicationManager.getApplication().isUnitTestMode()
                           ? GET_ERRORS_LONGER_TIMEOUT
                           : GET_ERRORS_TIMEOUT;
      semaphore.waitFor(timeout);
    }
    finally {
      semaphore.up(); // make sure to unlock semaphore so that computedErrors() can understand when it was unlocked by timeout
    }

    return resultRef.get();
  }

  @Nullable
  public LibraryDependenciesResult analysis_getLibraryDependencies() {
    final Ref<LibraryDependenciesResult> resultRef = new Ref<LibraryDependenciesResult>();
    final Semaphore semaphore = new Semaphore();

    try {
      synchronized (myLock) {
        if (myServer == null) return null;

        semaphore.down();

        LOG.debug("analysis_getLibraryDependencies()");

        final GetLibraryDependenciesConsumer consumer = new GetLibraryDependenciesConsumer() {
          @Override
          public void computedDependencies(@Nullable final String[] libraries,
                                           @Nullable final Map<String, Map<String, List<String>>> packageMap) {
            resultRef.set(new LibraryDependenciesResult(libraries, packageMap));
            semaphore.up();
          }

          @Override
          public void onError(final RequestError error) {
            logError("analysis_getLibraryDependencies()", null, error);
            semaphore.up();
          }
        };

        final AnalysisServer server = myServer;
        final boolean ok = runInPooledThreadAndWait(new Runnable() {
          @Override
          public void run() {
            server.analysis_getLibraryDependencies(consumer);
          }
        }, "analysis_getLibraryDependencies()", SEND_REQUEST_TIMEOUT);

        if (!ok) {
          stopServer();
          return null;
        }
      }

      semaphore.waitFor(GET_LIBRARY_DEPENDENCIES_TIMEOUT);
    }
    finally {
      semaphore.up(); // make sure to unlock semaphore so that computedDependencies() can understand when it was unlocked by timeout
    }

    return resultRef.get();
  }

  @Nullable
  public List<AnalysisErrorFixes> edit_getFixes(@NotNull final String _filePath, final int offset) {
    final Ref<List<AnalysisErrorFixes>> resultRef = new Ref<List<AnalysisErrorFixes>>();
    final Semaphore semaphore = new Semaphore();
    final String filePath = FileUtil.toSystemDependentName(_filePath);

    synchronized (myLock) {
      if (myServer == null) return null;

      semaphore.down();

      final GetFixesConsumer consumer = new GetFixesConsumer() {
        @Override
        public void computedFixes(final List<AnalysisErrorFixes> fixes) {
          resultRef.set(fixes);
          semaphore.up();
        }

        @Override
        public void onError(final RequestError error) {
          logError("edit_getFixes()", filePath, error);
          semaphore.up();
        }
      };

      final AnalysisServer server = myServer;
      final boolean ok = runInPooledThreadAndWait(new Runnable() {
        @Override
        public void run() {
          server.edit_getFixes(filePath, offset, consumer);
        }
      }, "edit_getFixes(" + filePath + ", " + offset + ")", SEND_REQUEST_TIMEOUT);

      if (!ok) {
        stopServer();
        return null;
      }
    }

    final long t0 = System.currentTimeMillis();
    semaphore.waitFor(GET_FIXES_TIMEOUT);

    if (semaphore.tryUp()) {
      LOG.info("edit_getFixes() took too long for file " + filePath + ": " + (System.currentTimeMillis() - t0) + "ms");
      return null;
    }

    return resultRef.get();
  }

  @Nullable
  public String completion_getSuggestions(@NotNull final String filePath, final int offset) {
    final Ref<String> resultRef = new Ref<String>();
    final Semaphore semaphore = new Semaphore();

    synchronized (myLock) {
      if (myServer == null) return null;

      semaphore.down();

      final GetSuggestionsConsumer consumer = new GetSuggestionsConsumer() {
        @Override
        public void computedCompletionId(@NotNull final String completionId) {
          resultRef.set(completionId);
          semaphore.up();
        }

        @Override
        public void onError(@NotNull final RequestError error) {
          // Not a problem. Happens if a file is outside of the project, or server is just not ready yet.
          semaphore.up();
        }
      };

      final AnalysisServer server = myServer;
      final boolean ok = runInPooledThreadAndWait(new Runnable() {
        @Override
        public void run() {
          server.completion_getSuggestions(filePath, offset, consumer);
        }
      }, "completion_getSuggestions(" + filePath + ", " + offset + ")", SEND_REQUEST_TIMEOUT);

      if (!ok) {
        stopServer();
        return null;
      }
    }

    final long t0 = System.currentTimeMillis();
    semaphore.waitFor(GET_SUGGESTIONS_TIMEOUT);

    if (semaphore.tryUp()) {
      LOG.info("completion_getSuggestions() took too long for file " + filePath + ": " + (System.currentTimeMillis() - t0) + "ms");
      return null;
    }

    return resultRef.get();
  }

  @Nullable
  public FormatResult edit_format(@NotNull final String filePath,
                                  final int selectionOffset,
                                  final int selectionLength,
                                  final int lineLength) {
    final Ref<FormatResult> resultRef = new Ref<FormatResult>();
    final Semaphore semaphore = new Semaphore();

    synchronized (myLock) {
      if (myServer == null) return null;

      semaphore.down();

      final FormatConsumer consumer = new FormatConsumer() {
        @Override
        public void computedFormat(final List<SourceEdit> edits, final int selectionOffset, final int selectionLength) {
          resultRef.set(new FormatResult(edits, selectionOffset, selectionLength));
          semaphore.up();
        }

        @Override
        public void onError(final RequestError error) {
          if (!"FORMAT_WITH_ERRORS".equals(error.getCode())) {
            logError("edit_format()", filePath, error);
          }
          semaphore.up();
        }
      };

      final AnalysisServer server = myServer;
      final boolean ok = runInPooledThreadAndWait(new Runnable() {
        @Override
        public void run() {
          server.edit_format(filePath, selectionOffset, selectionLength, lineLength, consumer);
        }
      }, "edit_format(" + filePath + ", " + selectionOffset + ", " + selectionLength + ")", SEND_REQUEST_TIMEOUT);

      if (!ok) {
        stopServer();
        return null;
      }
    }

    final long t0 = System.currentTimeMillis();
    semaphore.waitFor(EDIT_FORMAT_TIMEOUT);

    if (semaphore.tryUp()) {
      LOG.info("edit_format() took too long for file " + filePath + ": " + (System.currentTimeMillis() - t0) + "ms");
      return null;
    }

    return resultRef.get();
  }

  @Nullable
  public SourceFileEdit edit_sortMembers(@NotNull final String filePath) {
    final Ref<SourceFileEdit> resultRef = new Ref<SourceFileEdit>();
    final Semaphore semaphore = new Semaphore();

    synchronized (myLock) {
      if (myServer == null) return null;

      semaphore.down();

      final SortMembersConsumer consumer = new SortMembersConsumer() {
        @Override
        public void computedEdit(final SourceFileEdit edit) {
          resultRef.set(edit);
          semaphore.up();
        }

        @Override
        public void onError(final RequestError error) {
          logError("edit_sortMembers()", filePath, error);
          semaphore.up();
        }
      };

      final AnalysisServer server = myServer;
      final boolean ok = runInPooledThreadAndWait(new Runnable() {
        @Override
        public void run() {
          server.edit_sortMembers(filePath, consumer);
        }
      }, "edit_sortMembers(" + filePath + ")", SEND_REQUEST_TIMEOUT);

      if (!ok) {
        stopServer();
        return null;
      }
    }

    final long t0 = System.currentTimeMillis();
    semaphore.waitFor(EDIT_SORT_MEMBERS_TIMEOUT);

    if (semaphore.tryUp()) {
      LOG.info("edit_sortMembers() took too long for file " + filePath + ": " + (System.currentTimeMillis() - t0) + "ms");
      return null;
    }

    return resultRef.get();
  }

  public boolean analysis_reanalyze(@Nullable final List<String> roots) {
    synchronized (myLock) {
      if (myServer == null) return false;

      String rootsStr = roots != null ? StringUtil.join(roots, ",\n") : "all roots";
      LOG.debug("analysis_reanalyze, roots: " + rootsStr);

      final AnalysisServer server = myServer;
      final boolean ok = runInPooledThreadAndWait(new Runnable() {
        @Override
        public void run() {
          server.analysis_reanalyze(roots);
        }
      }, "analysis_reanalyze(" + rootsStr + ")", SEND_REQUEST_TIMEOUT);

      if (!ok) {
        stopServer();
        return false;
      }

      return true;
    }
  }

  private boolean analysis_setPriorityFiles() {
    synchronized (myLock) {
      if (myServer == null) return false;

      if (LOG.isDebugEnabled()) {
        LOG.debug("analysis_setPriorityFiles, files:\n" + StringUtil.join(myVisibleFiles, ",\n"));
      }

      final AnalysisServer server = myServer;
      final boolean ok = runInPooledThreadAndWait(new Runnable() {
        @Override
        public void run() {
          server.analysis_setPriorityFiles(myVisibleFiles);
        }
      }, "analysis_setPriorityFiles(" + StringUtil.join(myVisibleFiles, ", ") + ")", SEND_REQUEST_TIMEOUT);

      if (!ok) {
        stopServer();
        return false;
      }

      return true;
    }
  }

  private boolean analysis_setSubscriptions() {
    synchronized (myLock) {
      if (myServer == null) return false;

      final Map<String, List<String>> subscriptions = new THashMap<String, List<String>>();
      subscriptions.put(AnalysisService.NAVIGATION, myVisibleFiles);
      subscriptions.put(AnalysisService.HIGHLIGHTS, myVisibleFiles);

      if (LOG.isDebugEnabled()) {
        LOG.debug("analysis_setSubscriptions, subscriptions:\n" + subscriptions);
      }

      final AnalysisServer server = myServer;
      final boolean ok = runInPooledThreadAndWait(new Runnable() {
        @Override
        public void run() {
          server.analysis_setSubscriptions(subscriptions);
        }
      }, "analysis_setSubscriptions(" + subscriptions + ")", SEND_REQUEST_TIMEOUT);

      if (!ok) {
        stopServer();
        return false;
      }

      return true;
    }
  }

  private void startServer(@NotNull final DartSdk sdk) {
    synchronized (myLock) {
      mySdkHome = sdk.getHomePath();

      final String testSdkHome = System.getProperty("dart.sdk");
      if (ApplicationManager.getApplication().isUnitTestMode() && testSdkHome == null) return;

      final String runtimePath =
        FileUtil.toSystemDependentName((ApplicationManager.getApplication().isUnitTestMode() ? testSdkHome : mySdkHome) + "/bin/dart");
      final String analysisServerPath = FileUtil.toSystemDependentName(
        (ApplicationManager.getApplication().isUnitTestMode() ? testSdkHome : mySdkHome) + "/bin/snapshots/analysis_server.dart.snapshot");

      final DebugPrintStream debugStream = new DebugPrintStream() {
        @Override
        public void println(String str) {
          //System.out.println("debugStream: " + str);
        }
      };

      final int port = NetUtils.tryToFindAvailableSocketPort(10000);

      String argsRaw;
      try {
        argsRaw = Registry.stringValue("dart.server.additional.arguments");
      }
      catch (MissingResourceException e) {
        argsRaw = "";
      }
      argsRaw += " --useAnalysisHighlight2";

      myServerSocket =
        new StdioServerSocket(runtimePath, analysisServerPath, null, debugStream, ArrayUtil.toStringArray(StringUtil.split(argsRaw, " ")),
                              false, false, port, false, FileReadMode.NORMALIZE_EOL_ALWAYS);
      myServerSocket.setClientId(ApplicationNamesInfo.getInstance().getFullProductName().replace(' ', '_'));
      myServerSocket.setClientVersion(ApplicationInfo.getInstance().getApiVersion());
      myServer = new RemoteAnalysisServerImpl(myServerSocket);

      try {
        myServer.start();
        myServer.server_setSubscriptions(SERVER_SUBSCRIPTIONS);
        myServer.addAnalysisServerListener(myAnalysisServerListener);
        mySdkVersion = sdk.getVersion();

        final AnalysisServer server = myServer;
        final boolean ok = runInPooledThreadAndWait(new Runnable() {
          @Override
          public void run() {
            server.analysis_updateOptions(new AnalysisOptions(true, true, true, true, false, true, false));
          }
        }, "analysis_updateOptions(true, true, true, true, false, true, false)", SEND_REQUEST_TIMEOUT);

        if (!ok) {
          stopServer();
          return;
        }

        LOG.info("Server started, see status at http://localhost:" + port + "/status");
      }
      catch (Exception e) {
        LOG.warn("Failed to start Dart analysis server, port=" + port, e);
        stopServer();
      }
    }
  }

  public boolean serverReadyForRequest(@NotNull final Project project, @NotNull final DartSdk sdk) {
    synchronized (myLock) {
      if (myServer == null || !sdk.getHomePath().equals(mySdkHome) || !sdk.getVersion().equals(mySdkVersion) || !myServer.isSocketOpen()) {
        stopServer();

        if (isDartSdkVersionSufficient(sdk)) {
          startServer(sdk);
        }
      }

      if (myServer != null) {
        myRootsHandler.ensureProjectServed(project);
        return true;
      }

      return false;
    }
  }

  private void stopServer() {
    synchronized (myLock) {
      if (myServer != null) {
        LOG.debug("stopping server");
        myServer.removeAnalysisServerListener(myAnalysisServerListener);

        final AnalysisServer server = myServer;
        final boolean ok = runInPooledThreadAndWait(new Runnable() {
          @Override
          public void run() {
            server.server_shutdown();
          }
        }, "server_shutdown()", SEND_REQUEST_TIMEOUT);

        if (!ok) {
          if (myServerSocket != null) {
            myServerSocket.stop();
          }
        }
      }

      onServerStopped();
    }
  }

  private void onServerStopped() {
    stopShowingServerProgress();

    synchronized (myLock) {
      myServerSocket = null;
      myServer = null;
      mySdkHome = null;
      myFilePathWithOverlaidContentToTimestamp.clear();
      myVisibleFiles.clear();

      ApplicationManager.getApplication().runReadAction(new Runnable() {
        @Override
        public void run() {
          for (final Project project : myRootsHandler.getTrackedProjects()) {
            if (!project.isDisposed()) {
              DartProblemsViewImpl.getInstance(project).clearAll();
            }
          }
        }
      });

      myRootsHandler.reset();
    }
  }

  private void stopShowingServerProgress() {
    myShowServerProgressAlarm.cancelAllRequests();
    myServerBusy.set(false);
    synchronized (myServerBusy) {
      myServerBusy.notifyAll();
    }
  }

  private void logError(@NotNull final String methodName, @Nullable final String filePath, @NotNull final RequestError error) {
    final String trace = error.getStackTrace();
    final String partialTrace = trace == null || trace.isEmpty() ? "" : trace.substring(0, Math.min(trace.length(), 1000));
    final String message = "Error from " + methodName +
                           (filePath == null ? "" : (", file = " + filePath)) +
                           ", SDK version = " + mySdkVersion +
                           ", server version = " + myServerVersion +
                           ", error code = " + error.getCode() + ": " + error.getMessage() +
                           "\n" + partialTrace + "...";
    if (RequestErrorCode.GET_ERRORS_INVALID_FILE.equals(error.getCode())) {
      LOG.warn(message);
    }
    else {
      LOG.error(message);
    }
  }

  private static boolean runInPooledThreadAndWait(@NotNull final Runnable runnable,
                                                  @NotNull final String runnableInfo,
                                                  final long timeout) {
    final Ref<RuntimeException> exceptionRef = new Ref<RuntimeException>();

    final Semaphore semaphore = new Semaphore();
    semaphore.down();

    ApplicationManager.getApplication().executeOnPooledThread(new Runnable() {
      @Override
      public void run() {
        try {
          runnable.run();
        }
        catch (RuntimeException e) {
          exceptionRef.set(e);
        }

        semaphore.up();
      }
    });

    semaphore.waitFor(timeout);

    if (!exceptionRef.isNull()) {
      LOG.error(runnableInfo, exceptionRef.get());
      return false;
    }

    if (semaphore.tryUp()) {
      // runnable is still not complete
      LOG.error("Operation didn't finish in " + timeout + " ms: " + runnableInfo);
      return false;
    }

    return true;
  }

  private void updateInformationFromServer(DocumentEvent e) {
    final Document document = e.getDocument();
    final VirtualFile file = FileDocumentManager.getInstance().getFile(document);
    if (!isDartOrHtmlFile(file)) return;

    final String filePath = file.getPath();
    synchronized (myNavigationData) {
      myFilePathsWithUnsentChanges.add(filePath);
      final List<PluginNavigationRegion> regions = myNavigationData.get(filePath);
      if (regions != null) {
        final int eventOffset = e.getOffset();
        final int deltaLength = e.getNewLength() - e.getOldLength();
        for (PluginNavigationRegion region : regions) {
          if (region.offset <= eventOffset && eventOffset <= region.offset + region.length) {
            region.length += deltaLength;
          }
          else if (region.offset >= eventOffset) {
            region.offset += deltaLength;
          }
          for (PluginNavigationTarget target : region.getTargets()) {
            if (target.file.equals(filePath) && target.offset >= eventOffset) {
              target.offset += deltaLength;
            }
          }
        }
      }
    }
  }

  private static class CompletionInfo {
    @NotNull final String myCompletionId;
    final int myReplacementOffset;
    final int myReplacementLength;
    @NotNull final List<CompletionSuggestion> myCompletions;
    final boolean isLast;

    public CompletionInfo(@NotNull final String completionId,
                          final int replacementOffset,
                          final int replacementLength,
                          @NotNull final List<CompletionSuggestion> completions,
                          boolean isLast) {
      this.myCompletionId = completionId;
      this.myReplacementOffset = replacementOffset;
      this.myReplacementLength = replacementLength;
      this.myCompletions = completions;
      this.isLast = isLast;
    }
  }

  public static class PluginHighlightRegion {
    public static final List<PluginHighlightRegion> EMPTY_LIST = Lists.newArrayList();

    private int offset;
    private int length;
    private final String type;

    private PluginHighlightRegion(HighlightRegion region) {
      offset = region.getOffset();
      length = region.getLength();
      type = region.getType();
    }

    public int getOffset() {
      return offset;
    }

    public int getLength() {
      return length;
    }

    public String getType() {
      return type;
    }
  }


  public static class PluginNavigationRegion {
    public static final List<PluginNavigationRegion> EMPTY_LIST = Lists.newArrayList();

    private int offset;
    private int length;
    private final List<PluginNavigationTarget> targets = Lists.newArrayList();

    private PluginNavigationRegion(NavigationRegion region) {
      offset = region.getOffset();
      length = region.getLength();
      for (NavigationTarget target : region.getTargetObjects()) {
        targets.add(new PluginNavigationTarget(target));
      }
    }

    public int getOffset() {
      return offset;
    }

    public int getLength() {
      return length;
    }

    public List<PluginNavigationTarget> getTargets() {
      return targets;
    }
  }

  public static class PluginNavigationTarget {
    private final String file;
    private int offset;

    private PluginNavigationTarget(NavigationTarget target) {
      file = FileUtil.toSystemIndependentName(target.getFile());
      offset = target.getOffset();
    }

    public String getFile() {
      return file;
    }

    public int getOffset() {
      return offset;
    }
  }

  public interface CompletionSuggestionProcessor {
    void process(CompletionSuggestion suggestion);
  }
}


File: Dart/src/com/jetbrains/lang/dart/resolve/DartResolver.java
package com.jetbrains.lang.dart.resolve;

import com.intellij.openapi.project.Project;
import com.intellij.openapi.util.Condition;
import com.intellij.openapi.util.registry.Registry;
import com.intellij.openapi.vfs.LocalFileSystem;
import com.intellij.openapi.vfs.VirtualFile;
import com.intellij.psi.PsiElement;
import com.intellij.psi.PsiFile;
import com.intellij.psi.PsiManager;
import com.intellij.psi.ResolveState;
import com.intellij.psi.impl.source.resolve.ResolveCache;
import com.intellij.psi.util.PsiTreeUtil;
import com.intellij.util.SmartList;
import com.intellij.util.containers.ContainerUtil;
import com.jetbrains.lang.dart.DartComponentType;
import com.jetbrains.lang.dart.analyzer.DartAnalysisServerService;
import com.jetbrains.lang.dart.analyzer.DartAnalysisServerService.PluginNavigationRegion;
import com.jetbrains.lang.dart.analyzer.DartAnalysisServerService.PluginNavigationTarget;
import com.jetbrains.lang.dart.psi.*;
import com.jetbrains.lang.dart.util.DartClassResolveResult;
import com.jetbrains.lang.dart.util.DartResolveUtil;
import org.jetbrains.annotations.NotNull;
import org.jetbrains.annotations.Nullable;

import java.util.ArrayList;
import java.util.Collections;
import java.util.List;

public class DartResolver implements ResolveCache.AbstractResolver<DartReference, List<? extends PsiElement>> {
  public static final DartResolver INSTANCE = new DartResolver();

  public static boolean isServerDrivenResolution() {
    return Registry.is("dart.server.driven.resolution", false);
  }

  @Nullable
  @Override
  public List<? extends PsiElement> resolve(@NotNull DartReference reference, boolean incompleteCode) {
    if (isServerDrivenResolution()) {
      final PsiFile refPsiFile = reference.getContainingFile();
      final int refOffset = reference.getTextOffset();
      final int refLength = reference.getTextLength();
      final PluginNavigationRegion region = findRegion(refPsiFile, refOffset, refLength);
      if (region != null) {
        final Project project = reference.getProject();
        final List<PsiElement> result = new SmartList<PsiElement>();
        for (PluginNavigationTarget target : region.getTargets()) {
          final PsiElement targetElement = getElementForNavigationTarget(project, target);
          if (targetElement != null) {
            result.add(targetElement);
          }
        }
        return result;
      }
      return null;
    }

    if (reference instanceof DartThisExpression) {
      return toResult(PsiTreeUtil.getParentOfType(reference, DartClass.class));
    }
    if (reference instanceof DartParameterNameReferenceExpression) {
      PsiElement target;
      {
        final DartCallExpression callExpression = PsiTreeUtil.getParentOfType(reference, DartCallExpression.class);
        final DartExpression expression = callExpression != null ? callExpression.getExpression() : null;
        target = expression instanceof DartReference ? ((DartReference)expression).resolve() : null;
        target = target != null ? target.getParent() : null;
      }
      if (target == null) {
        final DartNewExpression newExpression = PsiTreeUtil.getParentOfType(reference, DartNewExpression.class);
        if (newExpression != null) {
          target = DartResolveUtil.findConstructorDeclaration(newExpression);
        }
      }
      final DartFormalParameterList parameters = PsiTreeUtil.getChildOfType(target, DartFormalParameterList.class);
      return toResult(DartResolveUtil.findParameterByName(parameters, reference.getText()));
    }
    if (DartResolveUtil.aloneOrFirstInChain(reference)) {
      return resolveSimpleReference(reference);
    }
    final DartReference leftReference = DartResolveUtil.getLeftReference(reference);
    // reference [node, node]
    final DartReference[] references = PsiTreeUtil.getChildrenOfType(reference, DartReference.class);
    if (references != null && references.length == 2) {
      // import prefix
      final List<DartComponentName> result = new SmartList<DartComponentName>();
      final String importPrefix = references[0].getCanonicalText();
      final String componentName = references[1].getCanonicalText();
      DartResolveUtil
        .processDeclarationsInImportedFileByImportPrefix(reference, importPrefix, new DartResolveProcessor(result, componentName),
                                                         componentName);
      if (!result.isEmpty()) {
        return result;
      }

      return toResult(references[1].resolve());
    }
    else if (leftReference != null) {
      final DartClassResolveResult classResolveResult = leftReference.resolveDartClass();
      final DartClass dartClass = classResolveResult.getDartClass();
      if (dartClass != null) {
        final String name = reference.getCanonicalText();
        final DartComponent subComponent = leftReference instanceof DartType
                                           ? dartClass.findNamedConstructor(name)
                                           : filterAccess(reference, dartClass.findMembersByName(name));
        return toResult(subComponent == null ? null : subComponent.getComponentName());
      }

      // import prefix
      final List<DartComponentName> result = new SmartList<DartComponentName>();
      final String importPrefix = leftReference.getCanonicalText();
      final String componentName = reference.getCanonicalText();
      DartResolveUtil
        .processDeclarationsInImportedFileByImportPrefix(reference, importPrefix, new DartResolveProcessor(result, componentName),
                                                         componentName);
      if (!result.isEmpty()) {
        return result;
      }
    }

    return null;
  }

  @Nullable
  public static PluginNavigationRegion findRegion(final PsiFile refPsiFile, final int refOffset, final int refLength) {
    final VirtualFile refVirtualFile = DartResolveUtil.getRealVirtualFile(refPsiFile);
    if (refVirtualFile != null) {
      final List<PluginNavigationRegion> regions = DartAnalysisServerService.getInstance().getNavigation(refVirtualFile);
      return findRegion(regions, refOffset, refLength);
    }
    return null;
  }

  @Nullable
  private static PsiElement getElementForNavigationTarget(Project project, PluginNavigationTarget target) {
    String targetPath = target.getFile();
    VirtualFile virtualFile = LocalFileSystem.getInstance().findFileByPath(targetPath);
    if (virtualFile != null) {
      PsiFile file = PsiManager.getInstance(project).findFile(virtualFile);
      if (file != null) {
        int targetOffset = target.getOffset();
        for (int i = 0; i < 2; i++) {
          Class<? extends PsiElement> clazz = DartComponentName.class;
          if (i == 1) {
            clazz = DartReferenceExpression.class;
          }
          PsiElement elementAt = PsiTreeUtil.findElementOfClassAtOffset(file, targetOffset, clazz, false);
          if (elementAt != null) {
            return elementAt;
          }
        }
      }
    }
    return null;
  }

  @NotNull
  private static List<PsiElement> toResult(@Nullable PsiElement element) {
    if (element == null) {
      return Collections.emptyList();
    }
    return new SmartList<PsiElement>(element);
  }

  @Nullable
  private static DartComponent filterAccess(PsiElement element, List<DartComponent> components) {
    final boolean lValue = DartResolveUtil.isLValue(element);
    return ContainerUtil.find(components, new Condition<DartComponent>() {
      @Override
      public boolean value(DartComponent component) {
        if (lValue && component.isSetter()) {
          return true;
        }
        else if (!lValue && component.isGetter()) {
          return true;
        }
        boolean isGetterOrSetter = component.isSetter() || component.isGetter();
        return !isGetterOrSetter;
      }
    });
  }

  /**
   * Find the region with the given offset in the given list of sorted regions.
   * Returns the found region or null.
   */
  @Nullable
  private static PluginNavigationRegion findRegion(List<PluginNavigationRegion> regions, int offset, int length) {
    int low = 0;
    int high = regions.size() - 1;

    while (low <= high) {
      int mid = (low + high) >>> 1;
      PluginNavigationRegion midVal = regions.get(mid);
      int cmp = midVal.getOffset() - offset;

      if (cmp < 0) {
        low = mid + 1;
      }
      else if (cmp > 0) {
        high = mid - 1;
      }
      else {
        if (midVal.getLength() == length) {
          return midVal;
        }
        return null;
      }
    }
    return null;
  }

  private static List<? extends PsiElement> resolveSimpleReference(@NotNull DartReference reference) {
    final List<? extends PsiElement> result = resolveSimpleReference(reference, reference.getCanonicalText());
    final PsiElement parent = reference.getParent();
    final PsiElement superParent = parent.getParent();
    final boolean isSimpleConstructor = parent instanceof DartType &&
                                        superParent instanceof DartNewExpression &&
                                        ((DartNewExpression)superParent).getReferenceExpression() == null;
    if (!isSimpleConstructor || result.isEmpty()) {
      return result;
    }
    final List<PsiElement> filteredResult = new ArrayList<PsiElement>(result.size());
    for (PsiElement element : result) {
      final PsiElement elementParent = element.getParent();
      if (element instanceof DartComponentName && elementParent instanceof DartClass) {
        final DartComponent component = ((DartClass)elementParent).findNamedConstructor(reference.getCanonicalText());
        if (component != null && DartComponentType.typeOf(component) == DartComponentType.CONSTRUCTOR) {
          filteredResult.add(component.getComponentName());
          continue;
        }
      }
      filteredResult.add(element);
    }
    return filteredResult;
  }

  @NotNull
  public static List<? extends PsiElement> resolveSimpleReference(@NotNull final PsiElement scopeElement, @NotNull final String name) {
    final List<DartComponentName> result = new ArrayList<DartComponentName>();
    // local
    final DartResolveProcessor dartResolveProcessor = new DartResolveProcessor(result, name, DartResolveUtil.isLValue(scopeElement));
    PsiTreeUtil.treeWalkUp(dartResolveProcessor, scopeElement, null, ResolveState.initial());

    // supers
    final DartClass dartClass = PsiTreeUtil.getParentOfType(scopeElement, DartClass.class);
    final boolean inClass = PsiTreeUtil.getParentOfType(scopeElement, DartClassBody.class, false) != null;
    if (result.isEmpty() && dartClass != null && inClass) {
      final DartComponent field = filterAccess(scopeElement, dartClass.findMembersByName(name));
      if (field != null) {
        return toResult(field.getComponentName());
      }
    }

    // global
    if (result.isEmpty()) {
      final List<VirtualFile> libraryFiles = DartResolveUtil.findLibrary(scopeElement.getContainingFile());
      DartResolveUtil.processTopLevelDeclarations(scopeElement, dartResolveProcessor, libraryFiles, name);
    }

    return result;
  }
}