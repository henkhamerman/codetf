Refactoring Types: ['Move Method']
/intellij/codeInsight/daemon/HighlightStressTest.java
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

/*
 * Created by IntelliJ IDEA.
 * User: cdr
 * Date: Jul 31, 2007
 * Time: 2:39:56 PM
 */
package com.intellij.codeInsight.daemon;

import com.intellij.codeInsight.daemon.impl.HighlightInfo;
import com.intellij.codeInspection.LocalInspectionTool;
import com.intellij.codeInspection.deadCode.UnusedDeclarationInspection;
import com.intellij.codeInspection.ex.InspectionToolRegistrar;
import com.intellij.codeInspection.ex.InspectionToolWrapper;
import com.intellij.codeInspection.ex.LocalInspectionToolWrapper;
import com.intellij.codeInspection.unusedImport.UnusedImportLocalInspection;
import com.intellij.lang.annotation.HighlightSeverity;
import com.intellij.openapi.command.WriteCommandAction;
import com.intellij.openapi.fileEditor.ex.FileEditorManagerEx;
import com.intellij.psi.*;
import com.intellij.psi.impl.PsiManagerEx;
import com.intellij.psi.search.GlobalSearchScope;
import com.intellij.psi.search.PsiShortNamesCache;
import com.intellij.testFramework.PlatformTestUtil;
import com.intellij.testFramework.SkipSlowTestLocally;
import com.intellij.util.text.CharArrayUtil;
import com.intellij.util.ui.UIUtil;
import org.jetbrains.annotations.NonNls;
import org.jetbrains.annotations.NotNull;

import java.util.*;

@SkipSlowTestLocally
public class HighlightStressTest extends LightDaemonAnalyzerTestCase {
  @Override
  protected void setUp() throws Exception {
    super.setUp();
    if ("RandomEditingForUnused".equals(getTestName(false))) {
      enableInspectionTool(new UnusedDeclarationInspection());
    }
  }

  @NotNull
  @Override
  protected LocalInspectionTool[] configureLocalInspectionTools() {
    if ("RandomEditingForUnused".equals(getTestName(false))) {
      return new LocalInspectionTool[]{new UnusedImportLocalInspection(),};
    }
    List<InspectionToolWrapper> all = InspectionToolRegistrar.getInstance().createTools();
    List<LocalInspectionTool> locals = new ArrayList<LocalInspectionTool>();
    for (InspectionToolWrapper tool : all) {
      if (tool instanceof LocalInspectionToolWrapper) {
        LocalInspectionTool e = ((LocalInspectionToolWrapper)tool).getTool();
        locals.add(e);
      }
    }
    return locals.toArray(new LocalInspectionTool[locals.size()]);
  }

  @NonNls private static final String text = "import java.util.*; class X { void f ( ) { "
  + "List < String > ls = new ArrayList < String > ( 1 ) ; ls . toString ( ) ; \n"
  + "List < Integer > is = new ArrayList < Integer > ( 1 ) ; is . toString ( ) ; \n"
  + "List i = new ArrayList ( 1 ) ; i . toString ( ) ; \n"
  + "Collection < Number > l2 = new ArrayList < Number > ( 10 ) ; l2 . toString ( ) ; \n"
  + "Collection < Number > l22 = new ArrayList < Number > ( ) ; l22 . toString ( ) ; \n"
  + "Map < Number , String > l3 = new HashMap < Number , String > ( 10 ) ; l3 . toString ( ) ; \n"
  + "Map < String , String > m = new HashMap < String , String > ( ) ; m . toString ( ) ; \n"
  + "Map < String , String > m1 = new HashMap < String , String > ( ) ; m1 . toString ( ) ; \n"
  + "Map < String , String > m2 = new HashMap < String , String > ( ) ; m2 . toString ( ) ; \n"
  + "Map < String , String > m3 = new HashMap < String , String > ( ) ; m3 . toString ( ) ; \n"
  + "Map < String , String > mi = new HashMap < String , String > ( 1 ) ; mi . toString ( ) ; \n"
  + "Map < String , String > mi1 = new HashMap < String , String > ( 1 ) ; mi1 . toString ( ) ; \n"
  + "Map < String , String > mi2 = new HashMap < String , String > ( 1 ) ; mi2 . toString ( ) ; \n"
  + "Map < String , String > mi3 = new HashMap < String , String > ( 1 ) ; mi3 . toString ( ) ; \n"
  + "Map < Number , String > l4 = new HashMap < Number , String > ( ) ; l4 . toString ( ) ; \n"
  + "Map < Number , String > l5 = new HashMap < Number , String > ( l4 ) ; l5 . toString ( ) ; \n"
  + "HashMap < Number , String > l6 = new HashMap < Number , String > ( ) ; l6 . toString ( ) ; \n"
  + "Map < List < Integer > , Map < String , List < String > > > l7 = new HashMap ( 1 ) ; l7 . toString ( ) ; \n"
  + "java . util . Map < java . util . List < Integer > , java . util . Map < String , java . util . List < String > > > l77 = new java . util . HashMap ( 1 ) ; l77 . toString ( ) ; \n"
  + " } } ";

  public void testAllTheseConcurrentThreadsDoNotCrashAnything() throws Exception {
    long time = System.currentTimeMillis();
    for (int i = 0; i < 20/*00000*/; i++) {
      //System.out.println("i = " + i);
      getPsiManager().dropResolveCaches();
      ((PsiManagerEx)getPsiManager()).getFileManager().cleanupForNextTest();
      DaemonCodeAnalyzer.getInstance(getProject()).restart();

      configureFromFileText("Stress.java", text);
      List<HighlightInfo> infos = doHighlighting();
      assertEmpty(DaemonAnalyzerTestCase.filter(infos, HighlightSeverity.ERROR));
      UIUtil.dispatchAllInvocationEvents();
      FileEditorManagerEx.getInstanceEx(getProject()).closeAllFiles();
    }
    System.out.println(System.currentTimeMillis() - time+"ms");
  }

  public void _testHugeFile() throws Exception {
    @NonNls String filePath =  "/psi/resolve/Thinlet.java";
    configureByFile(filePath);
    doHighlighting();

    int N = 42;
    long[] time = new long[N];
    for (int i = 0; i < N; i++) {
      DaemonCodeAnalyzer.getInstance(getProject()).restart();

      long start = System.currentTimeMillis();
      doHighlighting();
      long end = System.currentTimeMillis();
      time[i] = end - start;
      System.out.println("i = " + i + "; time= "+(end-start));

      UIUtil.dispatchAllInvocationEvents();
    }
    System.out.println("Average among the N/3 median times: " + PlatformTestUtil.averageAmongMedians(time, 3) + "ms");

    //System.out.println("JobLauncher.COUNT   = " + JobLauncher.COUNT);
    //System.out.println("JobLauncher.TINY    = " + JobLauncher.TINY_COUNT);
    //System.out.println("JobLauncher.LENGTH  = " + JobLauncher.LENGTH);
    //System.out.println("JobLauncher.ELAPSED = " + JobLauncher.ELAPSED);
    //System.out.println("Ave length : "+(JobLauncher.LENGTH.get()/1.0/JobLauncher.COUNT.get()));
    //System.out.println("Ave elapsed: "+(JobLauncher.ELAPSED.get()/1.0/JobLauncher.COUNT.get()));
    //
    //JobLauncher.lengths.sort();
    //System.out.println("Lengths: "+JobLauncher.lengths);
  }

  public void testRandomEditingPerformance() throws Exception {
    configureFromFileText("Stress.java", text);
    List<HighlightInfo> list = doHighlighting();
    int warnings = list.size();
    Random random = new Random();

    DaemonCodeAnalyzer.getInstance(getProject()).restart();
    int N = 20;
    long[] time = new long[N];

    for (int i = 0; i < N; i++) {
      long start = System.currentTimeMillis();

      System.out.println("i = " + i);
      String s = myFile.getText();
      int offset;
      while (true) {
        offset = random.nextInt(s.length());
        if (s.charAt(offset) == ' ') break;
      }
      myEditor.getCaretModel().moveToOffset(offset);
      type("/*--*/");
      Collection<HighlightInfo> infos = doHighlighting();
      if (warnings != infos.size()) {
        list = new ArrayList<HighlightInfo>(list);
        Collections.sort(list, new Comparator<HighlightInfo>() {
          @Override
          public int compare(HighlightInfo o1, HighlightInfo o2) {
            if (o1.equals(o2)) return 0;
            if (o1.getActualStartOffset() != o2.getActualStartOffset()) return o1.getActualStartOffset() - o2.getActualStartOffset();
            return (o1.getText() + o1.getDescription()).compareTo(o2.getText() + o2.getDescription());
          }
        });
        infos = new ArrayList<HighlightInfo>(infos);
        Collections.sort((ArrayList<HighlightInfo>)infos, new Comparator<HighlightInfo>() {
          @Override
          public int compare(HighlightInfo o1, HighlightInfo o2) {
            if (o1.equals(o2)) return 0;
            if (o1.getActualStartOffset() != o2.getActualStartOffset()) return o1.getActualStartOffset() - o2.getActualStartOffset();
            return (o1.getText() + o1.getDescription()).compareTo(o2.getText() + o2.getDescription());
          }
        });
        System.out.println(">--------------------");
        for (HighlightInfo info : list) {
          System.out.println(info);
        }
        System.out.println("---------------------");
        for (HighlightInfo info : infos) {
          System.out.println(info);
        }
        System.out.println("<--------------------");
      }
      assertEquals(infos.toString(), warnings, infos.size());
      for (HighlightInfo info : infos) {
        assertNotSame(info + "", HighlightSeverity.ERROR, info.getSeverity());
      }
      UIUtil.dispatchAllInvocationEvents();

      long end = System.currentTimeMillis();
      time[i] = end - start;
    }
    FileEditorManagerEx.getInstanceEx(getProject()).closeAllFiles();

    System.out.println("Average among the N/3 median times: " + PlatformTestUtil.averageAmongMedians(time, 3) + "ms");
  }

  public void testRandomEditingForUnused() throws Exception {
    configureFromFileText("Stress.java", "class X {<caret>}");

    PsiShortNamesCache cache = PsiShortNamesCache.getInstance(getProject());
    String[] names = cache.getAllClassNames();

    final StringBuilder imports = new StringBuilder();
    final StringBuilder usages = new StringBuilder();
    int v = 0;
    List<PsiClass> aclasses = new ArrayList<PsiClass>();
    for (String name : names) {
      PsiClass[] classes = cache.getClassesByName(name, GlobalSearchScope.allScope(getProject()));
      if (classes.length == 0) continue;
      PsiClass aClass = classes[0];
      if (!aClass.hasModifierProperty(PsiModifier.PUBLIC)) continue;
      if (aClass.getSuperClass() == null) continue;
      PsiClassType[] superTypes = aClass.getSuperTypes();
      if (superTypes.length == 0 || superTypes[0].resolve() == null) continue;
      String qualifiedName = aClass.getQualifiedName();
      if (qualifiedName.startsWith("java.lang.invoke")) continue; // java.lang.invoke.MethodHandle has weird access attributes in recent rt.jar which causes spurious highlighting errors
      imports.append("import " + qualifiedName + ";\n");
      usages.append("/**/ "+aClass.getName() + " var" + v + " = null; var" + v + ".toString();\n");
      aclasses.add(aClass);
      v++;
      if (v>100) break;
    }
    final String text = imports + "\n class X {{\n" + usages + "}}";
    WriteCommandAction.runWriteCommandAction(null, new Runnable() {
      @Override
      public void run() {
        getEditor().getDocument().setText(text);
      }
    });

    List<HighlightInfo> errors = DaemonAnalyzerTestCase.filter(doHighlighting(), HighlightSeverity.WARNING);
    assertEmpty(errors);
    Random random = new Random();
    int unused = 0;
    for (int i = 0; i < 100; i++) {
      String s = myFile.getText();

      int offset;
      while (true) {
        offset = random.nextInt(s.length());
        if (CharArrayUtil.regionMatches(s, offset, "/**/") || CharArrayUtil.regionMatches(s, offset, "//")) break;
      }

      char next = offset < s.length()-1 ? s.charAt(offset+1) : 0;
      if (next == '/') {
        myEditor.getCaretModel().moveToOffset(offset + 1);
        type("**");
        unused--;
      }
      else if (next == '*') {
        myEditor.getCaretModel().moveToOffset(offset + 1);
        delete();
        delete();
        unused++;
      }
      else {
        continue;
      }
      PsiDocumentManager.getInstance(getProject()).commitAllDocuments();
      getFile().accept(new PsiRecursiveElementVisitor() {
        @Override
        public void visitElement(PsiElement element) {
          assertTrue(element.toString(), element.isValid());
          super.visitElement(element);
        }
      });

      System.out.println("i = " + i + " " + next + " at "+offset);

      List<HighlightInfo> infos = doHighlighting();
      errors = DaemonAnalyzerTestCase.filter(infos, HighlightSeverity.ERROR);
      assertEmpty(errors);
      List<HighlightInfo> warns = DaemonAnalyzerTestCase.filter(infos, HighlightSeverity.WARNING);
      if (unused != warns.size()) {
        assertEquals(warns.toString(), unused, warns.size());
      }
    }
    FileEditorManagerEx.getInstanceEx(getProject()).closeAllFiles();
  }


}


File: platform/platform-tests/testSrc/com/intellij/openapi/progress/impl/ProgressIndicatorTest.java
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
package com.intellij.openapi.progress.impl;

import com.intellij.ide.util.DelegatingProgressIndicator;
import com.intellij.openapi.application.ApplicationManager;
import com.intellij.openapi.application.ModalityState;
import com.intellij.openapi.application.ex.ApplicationManagerEx;
import com.intellij.openapi.progress.*;
import com.intellij.openapi.progress.util.ProgressIndicatorBase;
import com.intellij.openapi.progress.util.ProgressIndicatorUtils;
import com.intellij.openapi.progress.util.ProgressWrapper;
import com.intellij.openapi.progress.util.ReadTask;
import com.intellij.openapi.util.EmptyRunnable;
import com.intellij.openapi.wm.ex.ProgressIndicatorEx;
import com.intellij.testFramework.BombedProgressIndicator;
import com.intellij.testFramework.LightPlatformTestCase;
import com.intellij.testFramework.PlatformTestCase;
import com.intellij.testFramework.PlatformTestUtil;
import com.intellij.util.*;
import com.intellij.util.containers.ContainerUtil;
import com.intellij.util.containers.DoubleArrayList;
import com.intellij.util.containers.Stack;
import com.intellij.util.ui.UIUtil;
import gnu.trove.TLongArrayList;
import org.jetbrains.annotations.NotNull;

import java.util.Collections;
import java.util.List;
import java.util.Random;
import java.util.concurrent.Future;
import java.util.concurrent.atomic.AtomicBoolean;

/**
 * @author yole
 */
public class ProgressIndicatorTest extends LightPlatformTestCase {
  public ProgressIndicatorTest() {
    PlatformTestCase.autodetectPlatformPrefix();
  }

  public void testCheckCanceledHasStackFrame() {
    ProgressIndicator pib = new ProgressIndicatorBase();
    pib.cancel();
    try {
      pib.checkCanceled();
      fail("Please restore ProgressIndicatorBase.checkCanceled() check!");
    }
    catch(ProcessCanceledException ex) {
      boolean hasStackFrame = ex.getStackTrace().length != 0;
      assertTrue("Should have stackframe", hasStackFrame);
    }
  }

  public void testProgressManagerCheckCanceledWorksRightAfterIndicatorBeenCanceled() {
    for (int i=0; i<1000;i++) {
      final ProgressIndicatorBase indicator = new ProgressIndicatorBase();
      ProgressManager.getInstance().runProcess(new Runnable() {
        @Override
        public void run() {
          ProgressManager.checkCanceled();
          try {
            indicator.cancel();
            ProgressManager.checkCanceled();
            fail("checkCanceled() must have caught just canceled indicator");
          }
          catch (ProcessCanceledException ignored) {
          }
        }
      }, indicator);
    }
  }

  private volatile long prevTime;
  private volatile long now;
  public void testCheckCanceledGranularity() throws InterruptedException {
    prevTime = now = 0;
    final long warmupEnd = System.currentTimeMillis() + 1000;
    final TLongArrayList times = new TLongArrayList();
    final long end = warmupEnd + 1000;

    ApplicationManagerEx.getApplicationEx().runProcessWithProgressSynchronously(new Runnable() {
      @Override
      public void run() {
        final Alarm alarm = new Alarm(Alarm.ThreadToUse.OWN_THREAD, getTestRootDisposable());
        ProgressIndicatorEx indicator = (ProgressIndicatorEx)ProgressIndicatorProvider.getGlobalProgressIndicator();
        prevTime = System.currentTimeMillis();
        assert indicator != null;
        indicator.addStateDelegate(new ProgressIndicatorStub() {
          @Override
          public void checkCanceled() throws ProcessCanceledException {
            now = System.currentTimeMillis();
            if (now > warmupEnd) {
              int delta = (int)(now - prevTime);
              times.add(delta);
            }
            prevTime = now;
          }
        });
        while (System.currentTimeMillis() < end) {
          ProgressManager.checkCanceled();
        }
        alarm.cancelAllRequests();
      }
    }, "", false, getProject(), null, "");
    long averageDelay = PlatformTestUtil.averageAmongMedians(times.toNativeArray(), 5);
    System.out.println("averageDelay = " + averageDelay);
    assertTrue(averageDelay < CoreProgressManager.CHECK_CANCELED_DELAY_MILLIS *3);
  }

  public void testProgressIndicatorUtilsScheduleWithWriteActionPriority() throws Throwable {
    final AtomicBoolean insideReadAction = new AtomicBoolean();
    final ProgressIndicatorBase indicator = new ProgressIndicatorBase();
    ProgressIndicatorUtils.scheduleWithWriteActionPriority(indicator, new ReadTask() {
      @Override
      public void computeInReadAction(@NotNull ProgressIndicator indicator) {
        insideReadAction.set(true);
        while (true) {
          ProgressManager.checkCanceled();
        }
      }

      @Override
      public void onCanceled(@NotNull ProgressIndicator indicator) {
      }
    });
    UIUtil.dispatchAllInvocationEvents();
    while (!insideReadAction.get()) {

    }
    ApplicationManager.getApplication().runWriteAction(new Runnable() {
      @Override
      public void run() {
        assertTrue(indicator.isCanceled());
      }
    });
    assertTrue(indicator.isCanceled());
  }

  public void testThereIsNoDelayBetweenIndicatorCancelAndProgressManagerCheckCanceled() throws Throwable {
    for (int i=0; i<100;i++) {
      final ProgressIndicatorBase indicator = new ProgressIndicatorBase();
      List<Thread> threads = ContainerUtil.map(Collections.nCopies(10, ""), new Function<String, Thread>() {
        @Override
        public Thread fun(String s) {
          return new Thread(new Runnable() {
            @Override
            public void run() {
              ProgressManager.getInstance().executeProcessUnderProgress(new Runnable() {
                @Override
                public void run() {
                  try {
                    Thread.sleep(new Random().nextInt(100));
                    indicator.cancel();
                    ProgressManager.checkCanceled();
                    fail("checkCanceled() must know about canceled indicator even from different thread");
                  }
                  catch (ProcessCanceledException ignored) {
                  }
                  catch (Throwable e) {
                    exception = e;
                  }
                }
              }, indicator);
            }
          },"indicator test"){{start();}};
        }
      });
      ContainerUtil.process(threads, new Processor<Thread>() {
        @Override
        public boolean process(Thread thread) {
          try {
            thread.join();
          }
          catch (InterruptedException e) {
            throw new RuntimeException(e);
          }
          return true;
        }
      });
    }
    if (exception != null) throw exception;
  }

  private volatile boolean checkCanceledCalled;
  private volatile boolean taskCanceled;
  private volatile boolean taskSucceeded;
  private volatile Throwable exception;
  public void testProgressManagerCheckCanceledDoesNotDelegateToProgressIndicatorIfThereAreNoCanceledIndicators() throws Throwable {
    final long warmupEnd = System.currentTimeMillis() + 1000;
    final long end = warmupEnd + 10000;
    checkCanceledCalled = false;
    final ProgressIndicatorBase myIndicator = new ProgressIndicatorBase();
    taskCanceled = taskSucceeded = false;
    exception = null;
    Future<?> future = ((ProgressManagerImpl)ProgressManager.getInstance()).runProcessWithProgressAsynchronously(
      new Task.Backgroundable(getProject(), "xxx") {
        @Override
        public void run(@NotNull ProgressIndicator indicator) {
          try {
            assertFalse(ApplicationManager.getApplication().isDispatchThread());
            assertSame(indicator, myIndicator);
            while (System.currentTimeMillis() < end) {
              ProgressManager.checkCanceled();
            }
          }
          catch (ProcessCanceledException e) {
            exception = e;
            checkCanceledCalled = true;
            throw e;
          }
          catch (RuntimeException e) {
            exception = e;
            throw e;
          }
          catch (Error e) {
            exception = e;
            throw e;
          }
        }

        @Override
        public void onCancel() {
          taskCanceled = true;
        }

        @Override
        public void onSuccess() {
          taskSucceeded = true;
        }
      }, myIndicator, null);

    ApplicationManager.getApplication().assertIsDispatchThread();

    while (!future.isDone()) {
      if (System.currentTimeMillis() < warmupEnd) {
        assertFalse(checkCanceledCalled);
      }
      else {
        myIndicator.cancel();
      }
    }
    // invokeLater in runProcessWithProgressAsynchronously
    UIUtil.dispatchAllInvocationEvents();

    assertTrue(checkCanceledCalled);
    assertFalse(taskSucceeded);
    assertTrue(taskCanceled);
    assertTrue(String.valueOf(exception), exception instanceof ProcessCanceledException);
  }

  private volatile boolean myFlag;
  public void testPerverseIndicator() {
    checkCanceledCalled = false;
    ProgressIndicator indicator = new ProgressIndicatorStub() {
      @Override
      public void checkCanceled() throws ProcessCanceledException {
        checkCanceledCalled = true;
        if (myFlag) throw new ProcessCanceledException();
      }
    };
    ensureCheckCanceledCalled(indicator);
  }

  private void ensureCheckCanceledCalled(@NotNull ProgressIndicator indicator) {
    myFlag = false;
    Alarm alarm = new Alarm(Alarm.ThreadToUse.POOLED_THREAD, myTestRootDisposable);
    alarm.addRequest(new Runnable() {
      @Override
      public void run() {
        myFlag = true;
      }
    }, 100);
    final long start = System.currentTimeMillis();
    try {
      ProgressManager.getInstance().executeProcessUnderProgress(new Runnable() {
        @Override
        public void run() {
          while (System.currentTimeMillis() - start < 10000) {
            ProgressManager.checkCanceled();
          }
        }
      }, indicator);
      fail("must have thrown PCE");
    }
    catch (ProcessCanceledException e) {
      assertTrue(checkCanceledCalled);
    }
  }

  public void testExtremelyPerverseIndicatorWhichCancelMethodIsNoop() {
    checkCanceledCalled = false;
    ProgressIndicator indicator = new ProgressIndicatorStub() {
      @Override
      public void checkCanceled() throws ProcessCanceledException {
        checkCanceledCalled = true;
        if (myFlag) throw new ProcessCanceledException();
      }

      @Override
      public void cancel() {
      }
    };
    ensureCheckCanceledCalled(indicator);
  }

  public void testNestedIndicatorsAreCanceledRight() {
    checkCanceledCalled = false;
    ProgressManager.getInstance().executeProcessUnderProgress(new Runnable() {
      @Override
      public void run() {
        assertFalse(CoreProgressManager.threadsUnderCanceledIndicator.contains(Thread.currentThread()));
        ProgressIndicator indicator = ProgressIndicatorProvider.getGlobalProgressIndicator();
        assertTrue(indicator != null && !indicator.isCanceled());
        indicator.cancel();
        assertTrue(CoreProgressManager.threadsUnderCanceledIndicator.contains(Thread.currentThread()));
        assertTrue(indicator.isCanceled());
        final ProgressIndicatorEx nested = new ProgressIndicatorBase();
        nested.addStateDelegate(new ProgressIndicatorStub() {
          @Override
          public void checkCanceled() throws ProcessCanceledException {
            checkCanceledCalled = true;
          }
        });
        ProgressManager.getInstance().executeProcessUnderProgress(new Runnable() {
          @Override
          public void run() {
            assertFalse(CoreProgressManager.threadsUnderCanceledIndicator.contains(Thread.currentThread()));
            ProgressIndicator indicator2 = ProgressIndicatorProvider.getGlobalProgressIndicator();
            assertTrue(indicator2 != null && !indicator2.isCanceled());
            assertSame(indicator2, nested);
            ProgressManager.checkCanceled();
          }
        }, nested);

        ProgressIndicator indicator3 = ProgressIndicatorProvider.getGlobalProgressIndicator();
        assertSame(indicator, indicator3);

        assertTrue(CoreProgressManager.threadsUnderCanceledIndicator.contains(Thread.currentThread()));
      }
    }, new EmptyProgressIndicator());
    assertFalse(checkCanceledCalled);
  }

  public void testWrappedIndicatorsAreSortedRight() {
    EmptyProgressIndicator indicator1 = new EmptyProgressIndicator();
    DelegatingProgressIndicator indicator2 = new DelegatingProgressIndicator(indicator1);
    final DelegatingProgressIndicator indicator3 = new DelegatingProgressIndicator(indicator2);
    ProgressManager.getInstance().executeProcessUnderProgress(new Runnable() {
      @Override
      public void run() {
        ProgressIndicator current = ProgressIndicatorProvider.getGlobalProgressIndicator();
        assertSame(indicator3, current);
      }
    }, indicator3);
    assertFalse(checkCanceledCalled);
  }

  public void testProgressPerformance() {
    PlatformTestUtil.startPerformanceTest("progress", 100, new ThrowableRunnable() {
      @Override
      public void run() throws Throwable {
        EmptyProgressIndicator indicator = new EmptyProgressIndicator();
        for (int i=0;i<100000;i++) {
          ProgressManager.getInstance().executeProcessUnderProgress(EmptyRunnable.getInstance(), indicator);
        }
      }
    }).assertTiming();
  }

  public void testWrapperIndicatorGotCanceledTooWhenInnerIndicatorHas() {
    final ProgressIndicator progress = new ProgressIndicatorBase(){
      @Override
      protected boolean isCancelable() {
        return true;
      }
    };
    try {
      ProgressManager.getInstance().executeProcessUnderProgress(new Runnable() {
        @Override
        public void run() {
          assertFalse(CoreProgressManager.threadsUnderCanceledIndicator.contains(Thread.currentThread()));
          assertTrue(!progress.isCanceled());
          progress.cancel();
          assertTrue(CoreProgressManager.threadsUnderCanceledIndicator.contains(Thread.currentThread()));
          assertTrue(progress.isCanceled());
          while (true) { // wait for PCE
            ProgressManager.checkCanceled();
          }
        }
      }, ProgressWrapper.wrap(progress));
      fail("PCE must have been thrown");
    }
    catch (ProcessCanceledException ignored) {

    }
  }

  public void testBombedIndicator() {
    final int count = 10;
    new BombedProgressIndicator(count).runBombed(new Runnable() {
      @Override
      public void run() {
        for (int i = 0; i < count * 2; i++) {
          TimeoutUtil.sleep(10);
          try {
            ProgressManager.checkCanceled();
            if (i >= count) {
              ProgressManager.checkCanceled();
              fail("PCE expected on " + i + "th check");
            }
          }
          catch (ProcessCanceledException e) {
            if (i < count) {
              fail("Too early PCE");
            }
          }
        }
      }
    });
  }

  private static class ProgressIndicatorStub implements ProgressIndicatorEx {
    private volatile boolean myCanceled;

    @Override
    public void addStateDelegate(@NotNull ProgressIndicatorEx delegate) {
      throw new RuntimeException();
    }

    @Override
    public boolean isModalityEntered() {
      throw new RuntimeException();
    }

    @Override
    public void finish(@NotNull TaskInfo task) {
    }

    @Override
    public boolean isFinished(@NotNull TaskInfo task) {
      throw new RuntimeException();
    }

    @Override
    public boolean wasStarted() {
      throw new RuntimeException();
    }

    @Override
    public void processFinish() {
      throw new RuntimeException();
    }

    @Override
    public void initStateFrom(@NotNull ProgressIndicator indicator) {
    }

    @NotNull
    @Override
    public Stack<String> getTextStack() {
      throw new RuntimeException();
    }

    @NotNull
    @Override
    public DoubleArrayList getFractionStack() {
      throw new RuntimeException();
    }

    @NotNull
    @Override
    public Stack<String> getText2Stack() {
      throw new RuntimeException();
    }

    @Override
    public int getNonCancelableCount() {
      throw new RuntimeException();
    }

    @Override
    public void start() {

    }

    @Override
    public void stop() {

    }

    @Override
    public void setText(String text) {
      throw new RuntimeException();
    }

    @Override
    public String getText() {
      throw new RuntimeException();
    }

    @Override
    public String getText2() {
      throw new RuntimeException();
    }

    @Override
    public void setText2(String text) {
      throw new RuntimeException();
    }

    @Override
    public double getFraction() {
      throw new RuntimeException();
    }

    @Override
    public void setFraction(double fraction) {
      throw new RuntimeException();
    }

    @Override
    public void pushState() {
      throw new RuntimeException();
    }

    @Override
    public void popState() {
      throw new RuntimeException();
    }

    @Override
    public void startNonCancelableSection() {
      throw new RuntimeException();
    }

    @Override
    public void finishNonCancelableSection() {
      throw new RuntimeException();
    }

    @Override
    public boolean isModal() {
      return false;
    }

    @NotNull
    @Override
    public ModalityState getModalityState() {
      throw new RuntimeException();
    }

    @Override
    public void setModalityProgress(ProgressIndicator modalityProgress) {
      throw new RuntimeException();
    }

    @Override
    public boolean isIndeterminate() {
      throw new RuntimeException();
    }

    @Override
    public void setIndeterminate(boolean indeterminate) {
      throw new RuntimeException();
    }

    @Override
    public boolean isPopupWasShown() {
      throw new RuntimeException();
    }

    @Override
    public boolean isShowing() {
      throw new RuntimeException();
    }

    @Override
    public boolean isRunning() {
      return true;
    }

    @Override
    public void cancel() {
      myCanceled = true;
      ProgressManager.canceled(this);
    }

    @Override
    public boolean isCanceled() {
      return myCanceled;
    }

    @Override
    public void checkCanceled() throws ProcessCanceledException {
       if (myCanceled) throw new ProcessCanceledException();
    }
  }
}


File: platform/testFramework/src/com/intellij/testFramework/PlatformTestUtil.java
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
package com.intellij.testFramework;

import com.intellij.concurrency.JobSchedulerImpl;
import com.intellij.ide.DataManager;
import com.intellij.ide.IdeEventQueue;
import com.intellij.ide.util.treeView.AbstractTreeNode;
import com.intellij.ide.util.treeView.AbstractTreeStructure;
import com.intellij.idea.Bombed;
import com.intellij.openapi.Disposable;
import com.intellij.openapi.actionSystem.*;
import com.intellij.openapi.application.ApplicationManager;
import com.intellij.openapi.application.PathManager;
import com.intellij.openapi.application.ex.ApplicationEx;
import com.intellij.openapi.application.ex.ApplicationManagerEx;
import com.intellij.openapi.editor.Document;
import com.intellij.openapi.extensions.ExtensionPoint;
import com.intellij.openapi.extensions.ExtensionPointName;
import com.intellij.openapi.extensions.Extensions;
import com.intellij.openapi.extensions.ExtensionsArea;
import com.intellij.openapi.fileEditor.FileDocumentManager;
import com.intellij.openapi.fileEditor.impl.LoadTextUtil;
import com.intellij.openapi.fileTypes.FileTypes;
import com.intellij.openapi.project.Project;
import com.intellij.openapi.ui.Queryable;
import com.intellij.openapi.util.*;
import com.intellij.openapi.util.io.FileUtil;
import com.intellij.openapi.util.text.StringUtil;
import com.intellij.openapi.vfs.LocalFileSystem;
import com.intellij.openapi.vfs.VfsUtilCore;
import com.intellij.openapi.vfs.VirtualFile;
import com.intellij.openapi.vfs.VirtualFileFilter;
import com.intellij.openapi.vfs.ex.temp.TempFileSystem;
import com.intellij.util.*;
import com.intellij.util.containers.HashMap;
import com.intellij.util.io.ZipUtil;
import com.intellij.util.ui.UIUtil;
import junit.framework.AssertionFailedError;
import org.jdom.Element;
import org.jdom.JDOMException;
import org.jetbrains.annotations.NonNls;
import org.jetbrains.annotations.NotNull;
import org.jetbrains.annotations.Nullable;
import org.jetbrains.annotations.TestOnly;
import org.junit.Assert;

import javax.swing.*;
import javax.swing.tree.DefaultMutableTreeNode;
import javax.swing.tree.TreePath;
import java.awt.*;
import java.awt.event.InvocationEvent;
import java.io.*;
import java.nio.charset.Charset;
import java.text.DecimalFormat;
import java.text.DecimalFormatSymbols;
import java.util.*;
import java.util.List;
import java.util.concurrent.atomic.AtomicBoolean;
import java.util.jar.JarFile;

import static org.junit.Assert.assertEquals;
import static org.junit.Assert.assertNotNull;

/**
 * @author yole
 */
@SuppressWarnings("UseOfSystemOutOrSystemErr")
public class PlatformTestUtil {
  public static final boolean COVERAGE_ENABLED_BUILD = "true".equals(System.getProperty("idea.coverage.enabled.build"));

  private static final boolean SKIP_HEADLESS = GraphicsEnvironment.isHeadless();
  private static final boolean SKIP_SLOW = Boolean.getBoolean("skip.slow.tests.locally");

  public static <T> void registerExtension(@NotNull ExtensionPointName<T> name, @NotNull T t, @NotNull Disposable parentDisposable) {
    registerExtension(Extensions.getRootArea(), name, t, parentDisposable);
  }

  public static <T> void registerExtension(@NotNull ExtensionsArea area, @NotNull ExtensionPointName<T> name, @NotNull final T t, @NotNull Disposable parentDisposable) {
    final ExtensionPoint<T> extensionPoint = area.getExtensionPoint(name.getName());
    extensionPoint.registerExtension(t);
    Disposer.register(parentDisposable, new Disposable() {
      @Override
      public void dispose() {
        extensionPoint.unregisterExtension(t);
      }
    });
  }

  @Nullable
  protected static String toString(@Nullable Object node, @Nullable Queryable.PrintInfo printInfo) {
    if (node instanceof AbstractTreeNode) {
      if (printInfo != null) {
        return ((AbstractTreeNode)node).toTestString(printInfo);
      }
      else {
        @SuppressWarnings({"deprecation", "UnnecessaryLocalVariable"})
        final String presentation = ((AbstractTreeNode)node).getTestPresentation();
        return presentation;
      }
    }
    if (node == null) {
      return "NULL";
    }
    return node.toString();
  }

  public static String print(JTree tree, boolean withSelection) {
    return print(tree, tree.getModel().getRoot(), withSelection, null, null);
  }

  public static String print(JTree tree, Object root, @Nullable Queryable.PrintInfo printInfo, boolean withSelection) {
    return print(tree, root,  withSelection, printInfo, null);
  }

  public static String print(JTree tree, boolean withSelection, @Nullable Condition<String> nodePrintCondition) {
    return print(tree, tree.getModel().getRoot(), withSelection, null, nodePrintCondition);
  }
  
  public static String print(JTree tree, Object root, 
                             boolean withSelection,
                             @Nullable Queryable.PrintInfo printInfo,
                             @Nullable Condition<String> nodePrintCondition) {
    StringBuilder buffer = new StringBuilder();
    final Collection<String> strings = printAsList(tree, root, withSelection, printInfo, nodePrintCondition);
    for (String string : strings) {
      buffer.append(string).append("\n");
    }
    return buffer.toString();
  }

  public static Collection<String> printAsList(JTree tree, boolean withSelection, @Nullable Condition<String> nodePrintCondition) {
    return printAsList(tree, tree.getModel().getRoot(), withSelection, null, nodePrintCondition);
  }

  private static Collection<String> printAsList(JTree tree, Object root, 
                                                boolean withSelection,
                                                @Nullable Queryable.PrintInfo printInfo,
                                                Condition<String> nodePrintCondition) {
    Collection<String> strings = new ArrayList<String>();
    printImpl(tree, root, strings, 0, withSelection, printInfo, nodePrintCondition);
    return strings;
  }

  private static void printImpl(JTree tree,
                                Object root,
                                Collection<String> strings,
                                int level,
                                boolean withSelection,
                                @Nullable Queryable.PrintInfo printInfo,
                                @Nullable Condition<String> nodePrintCondition) {
    DefaultMutableTreeNode defaultMutableTreeNode = (DefaultMutableTreeNode)root;

    final Object userObject = defaultMutableTreeNode.getUserObject();
    String nodeText;
    if (userObject != null) {
      nodeText = toString(userObject, printInfo);
    }
    else {
      nodeText = "null";
    }

    if (nodePrintCondition != null && !nodePrintCondition.value(nodeText)) return;

    final StringBuilder buff = new StringBuilder();
    StringUtil.repeatSymbol(buff, ' ', level);

    final boolean expanded = tree.isExpanded(new TreePath(defaultMutableTreeNode.getPath()));
    if (!defaultMutableTreeNode.isLeaf()) {
      buff.append(expanded ? "-" : "+");
    }

    final boolean selected = tree.getSelectionModel().isPathSelected(new TreePath(defaultMutableTreeNode.getPath()));
    if (withSelection && selected) {
      buff.append("[");
    }

    buff.append(nodeText);

    if (withSelection && selected) {
      buff.append("]");
    }

    strings.add(buff.toString());

    int childCount = tree.getModel().getChildCount(root);
    if (expanded) {
      for (int i = 0; i < childCount; i++) {
        printImpl(tree, tree.getModel().getChild(root, i), strings, level + 1, withSelection, printInfo, nodePrintCondition);
      }
    }
  }

  public static void assertTreeEqual(JTree tree, @NonNls String expected) {
    assertTreeEqual(tree, expected, false);
  }

  public static void assertTreeEqualIgnoringNodesOrder(JTree tree, @NonNls String expected) {
    assertTreeEqualIgnoringNodesOrder(tree, expected, false);
  }

  public static void assertTreeEqual(JTree tree, String expected, boolean checkSelected) {
    String treeStringPresentation = print(tree, checkSelected);
    assertEquals(expected, treeStringPresentation);
  }

  public static void assertTreeEqualIgnoringNodesOrder(JTree tree, String expected, boolean checkSelected) {
    final Collection<String> actualNodesPresentation = printAsList(tree, checkSelected, null);
    final List<String> expectedNodes = StringUtil.split(expected, "\n");
    UsefulTestCase.assertSameElements(actualNodesPresentation, expectedNodes);
  }

  @TestOnly
  public static void waitForAlarm(final int delay) throws InterruptedException {
    assert !ApplicationManager.getApplication().isWriteAccessAllowed(): "It's a bad idea to wait for an alarm under the write action. Somebody creates an alarm which requires read action and you are deadlocked.";
    assert ApplicationManager.getApplication().isDispatchThread();

    final AtomicBoolean invoked = new AtomicBoolean();
    final Alarm alarm = new Alarm(Alarm.ThreadToUse.SWING_THREAD);
    alarm.addRequest(new Runnable() {
      @Override
      public void run() {
        ApplicationManager.getApplication().invokeLater(new Runnable() {
          @Override
          public void run() {
            alarm.addRequest(new Runnable() {
              @Override
              public void run() {
                invoked.set(true);
              }
            }, delay);
          }
        });
      }
    }, delay);

    UIUtil.dispatchAllInvocationEvents();

    boolean sleptAlready = false;
    while (!invoked.get()) {
      UIUtil.dispatchAllInvocationEvents();
      //noinspection BusyWait
      Thread.sleep(sleptAlready ? 10 : delay);
      sleptAlready = true;
    }
    UIUtil.dispatchAllInvocationEvents();
  }

  @TestOnly
  public static void dispatchAllInvocationEventsInIdeEventQueue() throws InterruptedException {
    assert SwingUtilities.isEventDispatchThread() : Thread.currentThread();
    final EventQueue eventQueue = Toolkit.getDefaultToolkit().getSystemEventQueue();
    while (true) {
      AWTEvent event = eventQueue.peekEvent();
      if (event == null) break;
        AWTEvent event1 = eventQueue.getNextEvent();
        if (event1 instanceof InvocationEvent) {
          IdeEventQueue.getInstance().dispatchEvent(event1);
        }
    }
  }

  private static Date raidDate(Bombed bombed) {
    final Calendar instance = Calendar.getInstance();
    instance.set(Calendar.YEAR, bombed.year());
    instance.set(Calendar.MONTH, bombed.month());
    instance.set(Calendar.DAY_OF_MONTH, bombed.day());
    instance.set(Calendar.HOUR_OF_DAY, bombed.time());
    instance.set(Calendar.MINUTE, 0);

    return instance.getTime();
  }

  public static boolean bombExplodes(Bombed bombedAnnotation) {
    Date now = new Date();
    return now.after(raidDate(bombedAnnotation));
  }

  public static StringBuilder print(AbstractTreeStructure structure,
                                    Object node,
                                    int currentLevel,
                                    @Nullable Comparator comparator,
                                    int maxRowCount,
                                    char paddingChar,
                                    @Nullable Queryable.PrintInfo printInfo) {
    StringBuilder buffer = new StringBuilder();
    doPrint(buffer, currentLevel, node, structure, comparator, maxRowCount, 0, paddingChar, printInfo);
    return buffer;
  }

  private static int doPrint(StringBuilder buffer,
                             int currentLevel,
                             Object node,
                             AbstractTreeStructure structure,
                             @Nullable Comparator comparator,
                             int maxRowCount,
                             int currentLine,
                             char paddingChar,
                             @Nullable Queryable.PrintInfo printInfo) {
    if (currentLine >= maxRowCount && maxRowCount != -1) return currentLine;

    StringUtil.repeatSymbol(buffer, paddingChar, currentLevel);
    buffer.append(toString(node, printInfo)).append("\n");
    currentLine++;
    Object[] children = structure.getChildElements(node);

    if (comparator != null) {
      ArrayList<?> list = new ArrayList<Object>(Arrays.asList(children));
      @SuppressWarnings({"UnnecessaryLocalVariable", "unchecked"}) Comparator<Object> c = comparator;
      Collections.sort(list, c);
      children = ArrayUtil.toObjectArray(list);
    }
    for (Object child : children) {
      currentLine = doPrint(buffer, currentLevel + 1, child, structure, comparator, maxRowCount, currentLine, paddingChar, printInfo);
    }

    return currentLine;
  }

  public static String print(Object[] objects) {
    return print(Arrays.asList(objects));
  }

  public static String print(Collection c) {
    StringBuilder result = new StringBuilder();
    for (Iterator iterator = c.iterator(); iterator.hasNext();) {
      Object each = iterator.next();
      result.append(toString(each, null));
      if (iterator.hasNext()) {
        result.append("\n");
      }
    }

    return result.toString();
  }

  public static String print(ListModel model) {
    StringBuilder result = new StringBuilder();
    for (int i = 0; i < model.getSize(); i++) {
      result.append(toString(model.getElementAt(i), null));
      result.append("\n");
    }
    return result.toString();
  }

  public static String print(JTree tree) {
    return print(tree, false);
  }

  public static void assertTreeStructureEquals(final AbstractTreeStructure treeStructure, final String expected) {
    assertEquals(expected, print(treeStructure, treeStructure.getRootElement(), 0, null, -1, ' ', null).toString());
  }

  public static void invokeNamedAction(final String actionId) {
    final AnAction action = ActionManager.getInstance().getAction(actionId);
    assertNotNull(action);
    final Presentation presentation = new Presentation();
    @SuppressWarnings("deprecation") final DataContext context = DataManager.getInstance().getDataContext();
    final AnActionEvent event = new AnActionEvent(null, context, "", presentation, ActionManager.getInstance(), 0);
    action.update(event);
    Assert.assertTrue(presentation.isEnabled());
    action.actionPerformed(event);
  }

  public static void assertTiming(final String message, final long expectedMs, final long actual) {
    if (COVERAGE_ENABLED_BUILD) return;

    final long expectedOnMyMachine = Math.max(1, expectedMs * Timings.MACHINE_TIMING / Timings.ETALON_TIMING);

    // Allow 10% more in case of test machine is busy.
    String logMessage = message;
    if (actual > expectedOnMyMachine) {
      int percentage = (int)(100.0 * (actual - expectedOnMyMachine) / expectedOnMyMachine);
      logMessage += ". Operation took " + percentage + "% longer than expected";
    }
    logMessage += ". Expected on my machine: " + expectedOnMyMachine + "." +
                  " Actual: " + actual + "." +
                  " Expected on Standard machine: " + expectedMs + ";" +
                  " Actual on Standard: " + actual * Timings.ETALON_TIMING / Timings.MACHINE_TIMING + ";" +
                  " Timings: CPU=" + Timings.CPU_TIMING +
                  ", I/O=" + Timings.IO_TIMING + "." +
                  " (" + (int)(Timings.MACHINE_TIMING*1.0/Timings.ETALON_TIMING*100) + "% of the Standard)" +
                  ".";
    final double acceptableChangeFactor = 1.1;
    if (actual < expectedOnMyMachine) {
      System.out.println(logMessage);
      TeamCityLogger.info(logMessage);
    }
    else if (actual < expectedOnMyMachine * acceptableChangeFactor) {
      TeamCityLogger.warning(logMessage, null);
    }
    else {
      // throw AssertionFailedError to try one more time
      throw new AssertionFailedError(logMessage);
    }
  }

  /**
   * example usage: startPerformanceTest("calculating pi",100, testRunnable).cpuBound().assertTiming();
   */
  public static TestInfo startPerformanceTest(@NonNls @NotNull String message, int expectedMs, @NotNull ThrowableRunnable test) {
    return new TestInfo(test, expectedMs,message);
  }

  // calculates average of the median values in the selected part of the array. E.g. for part=3 returns average in the middle third.
  public static long averageAmongMedians(@NotNull long[] time, int part) {
    assert part >= 1;
    int n = time.length;
    Arrays.sort(time);
    long total = 0;
    for (int i= n /2- n / part /2; i< n /2+ n / part /2; i++) {
      total += time[i];
    }
    int middlePartLength = n / part;
    return middlePartLength == 0 ? 0 : total / middlePartLength;
  }

  public static boolean canRunTest(@NotNull Class testCaseClass) {
    if (!SKIP_SLOW && !SKIP_HEADLESS) {
      return true;
    }

    for (Class<?> clazz = testCaseClass; clazz != null; clazz = clazz.getSuperclass()) {
      if (SKIP_HEADLESS && clazz.getAnnotation(SkipInHeadlessEnvironment.class) != null) {
        System.out.println("Class '" + testCaseClass.getName() + "' is skipped because it requires working UI environment");
        return false;
      }
      if (SKIP_SLOW && clazz.getAnnotation(SkipSlowTestLocally.class) != null) {
        System.out.println("Class '" + testCaseClass.getName() + "' is skipped because it is dog slow");
        return false;
      }
    }

    return true;
  }

  public static void assertPathsEqual(@Nullable String expected, @Nullable String actual) {
    if (expected != null) expected = FileUtil.toSystemIndependentName(expected);
    if (actual != null) actual = FileUtil.toSystemIndependentName(actual);
    assertEquals(expected, actual);
  }

  @NotNull
  public static String getRtJarPath() {
    String home = System.getProperty("java.home");
    return SystemInfo.isAppleJvm ? FileUtil.toCanonicalPath(home + "/../Classes/classes.jar") : home + "/lib/rt.jar";
  }

  public static void saveProject(Project project) {
    ApplicationEx application = ApplicationManagerEx.getApplicationEx();
    boolean oldValue = application.isDoNotSave();
    try {
      application.doNotSave(false);
      project.save();
    }
    finally {
      application.doNotSave(oldValue);
    }
  }

  public static class TestInfo {
    private final ThrowableRunnable test; // runnable to measure
    private final int expectedMs;           // millis the test is expected to run
    private ThrowableRunnable setup;      // to run before each test
    private boolean usesAllCPUCores;      // true if the test runs faster on multi-core
    private int attempts = 4;             // number of retries if performance failed
    private final String message;         // to print on fail
    private boolean adjustForIO = true;   // true if test uses IO, timings need to be re-calibrated according to this agent disk performance
    private boolean adjustForCPU = true;  // true if test uses CPU, timings need to be re-calibrated according to this agent CPU speed

    private TestInfo(@NotNull ThrowableRunnable test, int expectedMs, String message) {
      this.test = test;
      this.expectedMs = expectedMs;
      assert expectedMs > 0 : "Expected must be > 0. Was: "+ expectedMs;
      this.message = message;
    }

    public TestInfo setup(@NotNull ThrowableRunnable setup) { assert this.setup==null; this.setup = setup; return this; }
    public TestInfo usesAllCPUCores() { assert adjustForCPU : "This test configured to be io-bound, it cannot use all cores"; usesAllCPUCores = true; return this; }
    public TestInfo cpuBound() { adjustForIO = false; adjustForCPU = true; return this; }
    public TestInfo ioBound() { adjustForIO = true; adjustForCPU = false; return this; }
    public TestInfo attempts(int attempts) { this.attempts = attempts; return this; }

    public void assertTiming() {
      assert expectedMs != 0 : "Must call .expect() before run test";
      if (COVERAGE_ENABLED_BUILD) return;
      Timings.getStatistics(); // warm-up, measure

      while (true) {
        attempts--;
        long start;
        try {
          if (setup != null) setup.run();
          start = System.currentTimeMillis();
          test.run();
        }
        catch (Throwable throwable) {
          throw new RuntimeException(throwable);
        }
        long finish = System.currentTimeMillis();
        long duration = finish - start;

        int expectedOnMyMachine = expectedMs;
        if (adjustForCPU) {
          expectedOnMyMachine = adjust(expectedOnMyMachine, Timings.CPU_TIMING, Timings.ETALON_CPU_TIMING);

          expectedOnMyMachine = usesAllCPUCores ? expectedOnMyMachine * 8 / JobSchedulerImpl.CORES_COUNT : expectedOnMyMachine;
        }
        if (adjustForIO) {
          expectedOnMyMachine = adjust(expectedOnMyMachine, Timings.IO_TIMING, Timings.ETALON_IO_TIMING);
        }

        // Allow 10% more in case of test machine is busy.
        String logMessage = message;
        if (duration > expectedOnMyMachine) {
          int percentage = (int)(100.0 * (duration - expectedOnMyMachine) / expectedOnMyMachine);
          logMessage += ": " + percentage + "% longer";
        }
        logMessage +=
          ". Expected: " + formatTime(expectedOnMyMachine) + ". Actual: " + formatTime(duration) + "." + Timings.getStatistics();
        final double acceptableChangeFactor = 1.1;
        if (duration < expectedOnMyMachine) {
          int percentage = (int)(100.0 * (expectedOnMyMachine - duration) / expectedOnMyMachine);
          logMessage = percentage + "% faster. " + logMessage;

          TeamCityLogger.info(logMessage);
          System.out.println("SUCCESS: " + logMessage);
        }
        else if (duration < expectedOnMyMachine * acceptableChangeFactor) {
          TeamCityLogger.warning(logMessage, null);
          System.out.println("WARNING: " + logMessage);
        }
        else {
          // try one more time
          if (attempts == 0) {
            //try {
            //  Object result = Class.forName("com.intellij.util.ProfilingUtil").getMethod("captureCPUSnapshot").invoke(null);
            //  System.err.println("CPU snapshot captured in '"+result+"'");
            //}
            //catch (Exception e) {
            //}

            throw new AssertionFailedError(logMessage);
          }
          System.gc();
          System.gc();
          System.gc();
          String s = "Another epic fail (remaining attempts: " + attempts + "): " + logMessage;
          TeamCityLogger.warning(s, null);
          System.err.println(s);
          //if (attempts == 1) {
          //  try {
          //    Class.forName("com.intellij.util.ProfilingUtil").getMethod("startCPUProfiling").invoke(null);
          //  }
          //  catch (Exception e) {
          //  }
          //}
          continue;
        }
        break;
      }
    }

    private static String formatTime(long millis) {
      String hint = "";
      DecimalFormat format = new DecimalFormat("#.0", DecimalFormatSymbols.getInstance(Locale.US));
      if (millis >= 60 * 1000) hint = format.format(millis / 60 / 1000.f) + "m";
      if (millis >= 1000) hint += (hint.isEmpty() ? "" : " ") + format.format(millis / 1000.f) + "s";
      String result = millis + "ms";
      if (!hint.isEmpty()) {
        result = result + " (" + hint + ")";
      }
      return result;
    }

    private static int adjust(int expectedOnMyMachine, long thisTiming, long ethanolTiming) {
      // most of our algorithms are quadratic. sad but true.
      double speed = 1.0 * thisTiming / ethanolTiming;
      double delta = speed < 1
                 ? 0.9 + Math.pow(speed - 0.7, 2)
                 : 0.45 + Math.pow(speed - 0.25, 2);
      expectedOnMyMachine *= delta;
      return expectedOnMyMachine;
    }
  }


  public static void assertTiming(String message, long expected, @NotNull Runnable actionToMeasure) {
    assertTiming(message, expected, 4, actionToMeasure);
  }

  public static long measure(@NotNull Runnable actionToMeasure) {
    long start = System.currentTimeMillis();
    actionToMeasure.run();
    long finish = System.currentTimeMillis();
    return finish - start;
  }

  public static void assertTiming(String message, long expected, int attempts, @NotNull Runnable actionToMeasure) {
    while (true) {
      attempts--;
      long duration = measure(actionToMeasure);
      try {
        assertTiming(message, expected, duration);
        break;
      }
      catch (AssertionFailedError e) {
        if (attempts == 0) throw e;
        System.gc();
        System.gc();
        System.gc();
        String s = "Another epic fail (remaining attempts: " + attempts + "): " + e.getMessage();
        TeamCityLogger.warning(s, null);
        System.err.println(s);
      }
    }
  }

  private static HashMap<String, VirtualFile> buildNameToFileMap(VirtualFile[] files, @Nullable VirtualFileFilter filter) {
    HashMap<String, VirtualFile> map = new HashMap<String, VirtualFile>();
    for (VirtualFile file : files) {
      if (filter != null && !filter.accept(file)) continue;
      map.put(file.getName(), file);
    }
    return map;
  }

  public static void assertDirectoriesEqual(VirtualFile dirAfter, VirtualFile dirBefore) throws IOException {
    assertDirectoriesEqual(dirAfter, dirBefore, null);
  }

  @SuppressWarnings("UnsafeVfsRecursion")
  public static void assertDirectoriesEqual(VirtualFile dirAfter, VirtualFile dirBefore, @Nullable VirtualFileFilter fileFilter) throws IOException {
    FileDocumentManager.getInstance().saveAllDocuments();

    VirtualFile[] childrenAfter = dirAfter.getChildren();

    if (dirAfter.isInLocalFileSystem() && dirAfter.getFileSystem() != TempFileSystem.getInstance()) {
      File[] ioAfter = new File(dirAfter.getPath()).listFiles();
      shallowCompare(childrenAfter, ioAfter);
    }

    VirtualFile[] childrenBefore = dirBefore.getChildren();
    if (dirBefore.isInLocalFileSystem() && dirBefore.getFileSystem() != TempFileSystem.getInstance()) {
      File[] ioBefore = new File(dirBefore.getPath()).listFiles();
      shallowCompare(childrenBefore, ioBefore);
    }

    HashMap<String, VirtualFile> mapAfter = buildNameToFileMap(childrenAfter, fileFilter);
    HashMap<String, VirtualFile> mapBefore = buildNameToFileMap(childrenBefore, fileFilter);

    Set<String> keySetAfter = mapAfter.keySet();
    Set<String> keySetBefore = mapBefore.keySet();
    assertEquals(dirAfter.getPath(), keySetAfter, keySetBefore);

    for (String name : keySetAfter) {
      VirtualFile fileAfter = mapAfter.get(name);
      VirtualFile fileBefore = mapBefore.get(name);
      if (fileAfter.isDirectory()) {
        assertDirectoriesEqual(fileAfter, fileBefore, fileFilter);
      }
      else {
        assertFilesEqual(fileAfter, fileBefore);
      }
    }
  }

  private static void shallowCompare(VirtualFile[] vfs, @Nullable File[] io) {
    List<String> vfsPaths = new ArrayList<String>();
    for (VirtualFile file : vfs) {
      vfsPaths.add(file.getPath());
    }

    List<String> ioPaths = new ArrayList<String>();
    if (io != null) {
      for (File file : io) {
        ioPaths.add(file.getPath().replace(File.separatorChar, '/'));
      }
    }

    assertEquals(sortAndJoin(vfsPaths), sortAndJoin(ioPaths));
  }

  private static String sortAndJoin(List<String> strings) {
    Collections.sort(strings);
    StringBuilder buf = new StringBuilder();
    for (String string : strings) {
      buf.append(string);
      buf.append('\n');
    }
    return buf.toString();
  }

  public static void assertFilesEqual(VirtualFile fileAfter, VirtualFile fileBefore) throws IOException {
    try {
      assertJarFilesEqual(VfsUtilCore.virtualToIoFile(fileAfter), VfsUtilCore.virtualToIoFile(fileBefore));
    }
    catch (IOException e) {
      FileDocumentManager manager = FileDocumentManager.getInstance();

      Document docBefore = manager.getDocument(fileBefore);
      boolean canLoadBeforeText = !fileBefore.getFileType().isBinary() || fileBefore.getFileType() == FileTypes.UNKNOWN;
      String textB = docBefore != null
                     ? docBefore.getText()
                     : !canLoadBeforeText
                       ? null
                       : LoadTextUtil.getTextByBinaryPresentation(fileBefore.contentsToByteArray(false), fileBefore).toString();

      Document docAfter = manager.getDocument(fileAfter);
      boolean canLoadAfterText = !fileBefore.getFileType().isBinary() || fileBefore.getFileType() == FileTypes.UNKNOWN;
      String textA = docAfter != null
                     ? docAfter.getText()
                     : !canLoadAfterText
                       ? null
                       : LoadTextUtil.getTextByBinaryPresentation(fileAfter.contentsToByteArray(false), fileAfter).toString();

      if (textA != null && textB != null) {
        assertEquals(fileAfter.getPath(), textA, textB);
      }
      else {
        Assert.assertArrayEquals(fileAfter.getPath(), fileAfter.contentsToByteArray(), fileBefore.contentsToByteArray());
      }
    }
  }

  public static void assertJarFilesEqual(File file1, File file2) throws IOException {
    final File tempDirectory1;
    final File tempDirectory2;

    final JarFile jarFile1 = new JarFile(file1);
    try {
      final JarFile jarFile2 = new JarFile(file2);
      try {
        tempDirectory1 = PlatformTestCase.createTempDir("tmp1");
        tempDirectory2 = PlatformTestCase.createTempDir("tmp2");
        ZipUtil.extract(jarFile1, tempDirectory1, null);
        ZipUtil.extract(jarFile2, tempDirectory2, null);
      }
      finally {
        jarFile2.close();
      }
    }
    finally {
      jarFile1.close();
    }

    final VirtualFile dirAfter = LocalFileSystem.getInstance().refreshAndFindFileByIoFile(tempDirectory1);
    assertNotNull(tempDirectory1.toString(), dirAfter);
    final VirtualFile dirBefore = LocalFileSystem.getInstance().refreshAndFindFileByIoFile(tempDirectory2);
    assertNotNull(tempDirectory2.toString(), dirBefore);
    ApplicationManager.getApplication().runWriteAction(new Runnable() {
      @Override
      public void run() {
        dirAfter.refresh(false, true);
        dirBefore.refresh(false, true);
      }
    });
    assertDirectoriesEqual(dirAfter, dirBefore);
  }

  public static void assertElementsEqual(final Element expected, final Element actual) throws IOException {
    if (!JDOMUtil.areElementsEqual(expected, actual)) {
      assertEquals(printElement(expected), printElement(actual));
    }
  }

  public static void assertElementEquals(final String expected, final Element actual) {
    try {
      assertElementsEqual(JDOMUtil.loadDocument(expected).getRootElement(), actual);
    }
    catch (IOException e) {
      throw new AssertionError(e);
    }
    catch (JDOMException e) {
      throw new AssertionError(e);
    }
  }

  public static String printElement(final Element element) throws IOException {
    final StringWriter writer = new StringWriter();
    JDOMUtil.writeElement(element, writer, "\n");
    return writer.getBuffer().toString();
  }

  public static String getCommunityPath() {
    final String homePath = PathManager.getHomePath();
    if (new File(homePath, "community/.idea").isDirectory()) {
      return homePath + File.separatorChar + "community";
    }
    return homePath;
  }

  public static String getPlatformTestDataPath() {
    return getCommunityPath().replace(File.separatorChar, '/') + "/platform/platform-tests/testData/";
  }


  public static Comparator<AbstractTreeNode> createComparator(final Queryable.PrintInfo printInfo) {
    return new Comparator<AbstractTreeNode>() {
      @Override
      public int compare(final AbstractTreeNode o1, final AbstractTreeNode o2) {
        String displayText1 = o1.toTestString(printInfo);
        String displayText2 = o2.toTestString(printInfo);
        return Comparing.compare(displayText1, displayText2);
      }
    };
  }

  @NotNull
  public static <T> T notNull(@Nullable T t) {
    assertNotNull(t);
    return t;
  }

  @NotNull
  public static String loadFileText(@NotNull String fileName) throws IOException {
    return StringUtil.convertLineSeparators(FileUtil.loadFile(new File(fileName)));
  }

  public static void tryGcSoftlyReachableObjects() {
    GCUtil.tryGcSoftlyReachableObjects();
  }

  public static void withEncoding(@NotNull String encoding, @NotNull final Runnable r) {
    withEncoding(encoding, new ThrowableRunnable() {
      @Override
      public void run() throws Throwable {
        r.run();
      }
    });
  }

  public static void withEncoding(@NotNull String encoding, @NotNull ThrowableRunnable r) {
    Charset oldCharset = Charset.defaultCharset();
    try {
      try {
        patchSystemFileEncoding(encoding);
        r.run();
      }
      finally {
        patchSystemFileEncoding(oldCharset.name());
      }
    }
    catch (Throwable t) {
      throw new RuntimeException(t);
    }
  }

  private static void patchSystemFileEncoding(String encoding) {
    ReflectionUtil.resetField(Charset.class, Charset.class, "defaultCharset");
    System.setProperty("file.encoding", encoding);
  }

  public static void withStdErrSuppressed(@NotNull Runnable r) {
    PrintStream std = System.err;
    System.setErr(new PrintStream(NULL));
    try {
      r.run();
    }
    finally {
      System.setErr(std);
    }
  }

  @SuppressWarnings("IOResourceOpenedButNotSafelyClosed")
  private static final OutputStream NULL = new OutputStream() {
    @Override
    public void write(int b) throws IOException { }
  };
}


File: platform/testFramework/src/com/intellij/testFramework/Timings.java
/*
 * Copyright 2000-2009 JetBrains s.r.o.
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
package com.intellij.testFramework;

import com.intellij.concurrency.JobSchedulerImpl;
import com.intellij.openapi.util.io.FileUtil;

import java.io.*;
import java.math.BigInteger;

/**
 * @author peter
 */
@SuppressWarnings({"UtilityClassWithoutPrivateConstructor"})
public class Timings {
  private static final int IO_PROBES = 42;

  public static final long CPU_TIMING;
  public static final long IO_TIMING;
  public static final long MACHINE_TIMING;

  /**
   * Measured on dual core p4 3HZ 1gig ram
   */
  public static final long ETALON_TIMING = 438;
  public static final long ETALON_CPU_TIMING = 200;
  public static final long ETALON_IO_TIMING = 100;


  static {
    int N = 20;
    for (int i=0; i<N; i++) {
      measureCPU(); //warmup
    }
    long[] elapsed=new long[N];
    for (int i=0; i< N; i++) {
      elapsed[i] = measureCPU();
    }
    CPU_TIMING = PlatformTestUtil.averageAmongMedians(elapsed, 2);

    long start = System.currentTimeMillis();
    for (int i = 0; i < IO_PROBES; i++) {
      try {
        final File tempFile = FileUtil.createTempFile("test", "test" + i);

        final FileWriter writer = new FileWriter(tempFile);
        try {
          for (int j = 0; j < 15; j++) {
            writer.write("test" + j);
            writer.flush();
          }
        }
        finally {
          writer.close();
        }

        final FileReader reader = new FileReader(tempFile);
        try {
          while (reader.read() >= 0) {}
        }
        finally {
          reader.close();
        }

        if (i == IO_PROBES - 1) {
          final FileOutputStream stream = new FileOutputStream(tempFile);
          try {
            stream.getFD().sync();
          }
          finally {
            stream.close();
          }
        }

        if (!tempFile.delete()) {
          throw new IOException("Unable to delete: " + tempFile);
        }
      }
      catch (IOException e) {
        throw new RuntimeException(e);
      }
    }
    IO_TIMING = System.currentTimeMillis() - start;

    MACHINE_TIMING = CPU_TIMING + IO_TIMING;
  }

  private static long measureCPU() {
    long start = System.currentTimeMillis();

    BigInteger k = new BigInteger("1");
    for (int i = 0; i < 1000000; i++) {
      k = k.add(new BigInteger("1"));
    }

    return System.currentTimeMillis() - start;
  }

  /**
   * @param value the value (e.g. number of iterations) which needs to be adjusted according to my machine speed
   * @param isParallelizable true if the test load is scalable with the CPU cores
   * @return value calibrated according to this machine speed. For slower machine, lesser value will be returned
   */
  public static int adjustAccordingToMySpeed(int value, boolean isParallelizable) {
    return Math.max(1, (int)(1.0 * value * ETALON_TIMING / MACHINE_TIMING) / 8 * (isParallelizable ? JobSchedulerImpl.CORES_COUNT : 1));
  }

  public static String getStatistics() {
    return
      " Timings: CPU=" + CPU_TIMING + " (" + (int)(CPU_TIMING*1.0/ ETALON_CPU_TIMING*100) + "% of the etalon)" +
      ", I/O=" + IO_TIMING + " (" + (int)(IO_TIMING*1.0/ ETALON_IO_TIMING*100) + "% of the etalon)" +
      ", total=" + MACHINE_TIMING + " ("+(int)(MACHINE_TIMING*1.0/ ETALON_TIMING*100) + "% of the etalon) " +
      Runtime.getRuntime().availableProcessors() + " cores.";
  }
}


File: platform/util/src/com/intellij/util/ArrayUtil.java
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
package com.intellij.util;

import com.intellij.openapi.util.Comparing;
import com.intellij.util.text.CharArrayCharSequence;
import gnu.trove.Equality;
import org.jetbrains.annotations.Contract;
import org.jetbrains.annotations.NotNull;
import org.jetbrains.annotations.Nullable;

import java.io.File;
import java.lang.reflect.Array;
import java.util.Arrays;
import java.util.Collection;
import java.util.Comparator;
import java.util.List;

/**
 * Author: msk
 */
@SuppressWarnings("MethodOverridesStaticMethodOfSuperclass")
public class ArrayUtil extends ArrayUtilRt {
  public static final short[] EMPTY_SHORT_ARRAY = ArrayUtilRt.EMPTY_SHORT_ARRAY;
  public static final char[] EMPTY_CHAR_ARRAY = ArrayUtilRt.EMPTY_CHAR_ARRAY;
  public static final byte[] EMPTY_BYTE_ARRAY = ArrayUtilRt.EMPTY_BYTE_ARRAY;
  public static final int[] EMPTY_INT_ARRAY = ArrayUtilRt.EMPTY_INT_ARRAY;
  public static final boolean[] EMPTY_BOOLEAN_ARRAY = ArrayUtilRt.EMPTY_BOOLEAN_ARRAY;
  public static final Object[] EMPTY_OBJECT_ARRAY = ArrayUtilRt.EMPTY_OBJECT_ARRAY;
  public static final String[] EMPTY_STRING_ARRAY = ArrayUtilRt.EMPTY_STRING_ARRAY;
  public static final Class[] EMPTY_CLASS_ARRAY = ArrayUtilRt.EMPTY_CLASS_ARRAY;
  public static final long[] EMPTY_LONG_ARRAY = ArrayUtilRt.EMPTY_LONG_ARRAY;
  public static final Collection[] EMPTY_COLLECTION_ARRAY = ArrayUtilRt.EMPTY_COLLECTION_ARRAY;
  public static final File[] EMPTY_FILE_ARRAY = ArrayUtilRt.EMPTY_FILE_ARRAY;
  public static final Runnable[] EMPTY_RUNNABLE_ARRAY = ArrayUtilRt.EMPTY_RUNNABLE_ARRAY;
  public static final CharSequence EMPTY_CHAR_SEQUENCE = new CharArrayCharSequence(EMPTY_CHAR_ARRAY);

  public static final ArrayFactory<String> STRING_ARRAY_FACTORY = new ArrayFactory<String>() {
    @NotNull
    @Override
    public String[] create(int count) {
      return newStringArray(count);
    }
  };
  public static final ArrayFactory<Object> OBJECT_ARRAY_FACTORY = new ArrayFactory<Object>() {
    @NotNull
    @Override
    public Object[] create(int count) {
      return newObjectArray(count);
    }
  };

  private ArrayUtil() { }

  @NotNull
  @Contract(pure=true)
  public static byte[] realloc(@NotNull byte[] array, final int newSize) {
    if (newSize == 0) {
      return EMPTY_BYTE_ARRAY;
    }

    final int oldSize = array.length;
    if (oldSize == newSize) {
      return array;
    }

    final byte[] result = new byte[newSize];
    System.arraycopy(array, 0, result, 0, Math.min(oldSize, newSize));
    return result;
  }
  @NotNull
  @Contract(pure=true)
  public static boolean[] realloc(@NotNull boolean[] array, final int newSize) {
    if (newSize == 0) {
      return EMPTY_BOOLEAN_ARRAY;
    }

    final int oldSize = array.length;
    if (oldSize == newSize) {
      return array;
    }

    boolean[] result = new boolean[newSize];
    System.arraycopy(array, 0, result, 0, Math.min(oldSize, newSize));
    return result;
  }

  @NotNull
  @Contract(pure=true)
  public static long[] realloc(@NotNull long[] array, int newSize) {
    if (newSize == 0) {
      return EMPTY_LONG_ARRAY;
    }

    final int oldSize = array.length;
    if (oldSize == newSize) {
      return array;
    }

    long[] result = new long[newSize];
    System.arraycopy(array, 0, result, 0, Math.min(oldSize, newSize));
    return result;
  }
  @NotNull
  @Contract(pure=true)
  public static int[] realloc(@NotNull int[] array, final int newSize) {
    if (newSize == 0) {
      return EMPTY_INT_ARRAY;
    }

    final int oldSize = array.length;
    if (oldSize == newSize) {
      return array;
    }

    final int[] result = new int[newSize];
    System.arraycopy(array, 0, result, 0, Math.min(oldSize, newSize));
    return result;
  }
  @NotNull
  @Contract(pure=true)
  public static <T> T[] realloc(@NotNull T[] array, final int newSize, @NotNull ArrayFactory<T> factory) {
    final int oldSize = array.length;
    if (oldSize == newSize) {
      return array;
    }

    T[] result = factory.create(newSize);
    if (newSize == 0) {
      return result;
    }

    System.arraycopy(array, 0, result, 0, Math.min(oldSize, newSize));
    return result;
  }

  @NotNull
  @Contract(pure=true)
  public static long[] append(@NotNull long[] array, long value) {
    array = realloc(array, array.length + 1);
    array[array.length - 1] = value;
    return array;
  }
  @NotNull
  @Contract(pure=true)
  public static int[] append(@NotNull int[] array, int value) {
    array = realloc(array, array.length + 1);
    array[array.length - 1] = value;
    return array;
  }

  @NotNull
  @Contract(pure=true)
  public static <T> T[] insert(@NotNull T[] array, int index, T value) {
    @SuppressWarnings("unchecked")
    T[] result = (T[])Array.newInstance(array.getClass().getComponentType(), array.length + 1);
    System.arraycopy(array, 0, result, 0, index);
    result[index] = value;
    System.arraycopy(array, index, result, index + 1, array.length - index);
    return result;
  }

  @NotNull
  @Contract(pure=true)
  public static int[] insert(@NotNull int[] array, int index, int value) {
    int[] result = new int[array.length + 1];
    System.arraycopy(array, 0, result, 0, index);
    result[index] = value;
    System.arraycopy(array, index, result, index+1, array.length - index);
    return result;
  }

  @NotNull
  @Contract(pure=true)
  public static byte[] append(@NotNull byte[] array, byte value) {
    array = realloc(array, array.length + 1);
    array[array.length - 1] = value;
    return array;
  }
  @NotNull
  @Contract(pure=true)
  public static boolean[] append(@NotNull boolean[] array, boolean value) {
    array = realloc(array, array.length + 1);
    array[array.length - 1] = value;
    return array;
  }

  @NotNull
  @Contract(pure=true)
  public static char[] realloc(@NotNull char[] array, final int newSize) {
    if (newSize == 0) {
      return EMPTY_CHAR_ARRAY;
    }

    final int oldSize = array.length;
    if (oldSize == newSize) {
      return array;
    }

    final char[] result = new char[newSize];
    System.arraycopy(array, 0, result, 0, Math.min(oldSize, newSize));
    return result;
  }

  @NotNull
  @Contract(pure=true)
  public static <T> T[] toObjectArray(@NotNull Collection<T> collection, @NotNull Class<T> aClass) {
    @SuppressWarnings("unchecked") T[] array = (T[])Array.newInstance(aClass, collection.size());
    return collection.toArray(array);
  }

  @NotNull
  @Contract(pure=true)
  public static <T> T[] toObjectArray(@NotNull Class<T> aClass, @NotNull Object... source) {
    @SuppressWarnings("unchecked") T[] array = (T[])Array.newInstance(aClass, source.length);
    System.arraycopy(source, 0, array, 0, array.length);
    return array;
  }

  @NotNull
  @Contract(pure=true)
  public static Object[] toObjectArray(@NotNull Collection<?> collection) {
    if (collection.isEmpty()) return EMPTY_OBJECT_ARRAY;
    //noinspection SSBasedInspection
    return collection.toArray(new Object[collection.size()]);
  }

  @NotNull
  @Contract(pure=true)
  public static int[] toIntArray(@NotNull Collection<Integer> list) {
    int[] ret = newIntArray(list.size());
    int i = 0;
    for (Integer e : list) {
      ret[i++] = e.intValue();
    }
    return ret;
  }

  @NotNull
  @Contract(pure=true)
  public static <T> T[] mergeArrays(@NotNull T[] a1, @NotNull T[] a2) {
    if (a1.length == 0) {
      return a2;
    }
    if (a2.length == 0) {
      return a1;
    }

    final Class<?> class1 = a1.getClass().getComponentType();
    final Class<?> class2 = a2.getClass().getComponentType();
    final Class<?> aClass = class1.isAssignableFrom(class2) ? class1 : class2;

    @SuppressWarnings("unchecked") T[] result = (T[])Array.newInstance(aClass, a1.length + a2.length);
    System.arraycopy(a1, 0, result, 0, a1.length);
    System.arraycopy(a2, 0, result, a1.length, a2.length);
    return result;
  }

  @NotNull
  @Contract(pure=true)
  public static <T> T[] mergeCollections(@NotNull Collection<? extends T> c1, @NotNull Collection<? extends T> c2, @NotNull ArrayFactory<T> factory) {
    T[] res = factory.create(c1.size() + c2.size());

    int i = 0;

    for (T t : c1) {
      res[i++] = t;
    }

    for (T t : c2) {
      res[i++] = t;
    }

    return res;
  }

  @NotNull
  @Contract(pure=true)
  public static <T> T[] mergeArrays(@NotNull T[] a1, @NotNull T[] a2, @NotNull ArrayFactory<T> factory) {
    if (a1.length == 0) {
      return a2;
    }
    if (a2.length == 0) {
      return a1;
    }
    T[] result = factory.create(a1.length + a2.length);
    System.arraycopy(a1, 0, result, 0, a1.length);
    System.arraycopy(a2, 0, result, a1.length, a2.length);
    return result;
  }

  @NotNull
  @Contract(pure=true)
  public static String[] mergeArrays(@NotNull String[] a1, @NotNull String... a2) {
    return mergeArrays(a1, a2, STRING_ARRAY_FACTORY);
  }

  @NotNull
  @Contract(pure=true)
  public static int[] mergeArrays(@NotNull int[] a1, @NotNull int[] a2) {
    if (a1.length == 0) {
      return a2;
    }
    if (a2.length == 0) {
      return a1;
    }
    int[] result = new int[a1.length + a2.length];
    System.arraycopy(a1, 0, result, 0, a1.length);
    System.arraycopy(a2, 0, result, a1.length, a2.length);
    return result;
  }

  @NotNull
  @Contract(pure=true)
  public static byte[] mergeArrays(@NotNull byte[] a1, @NotNull byte[] a2) {
    if (a1.length == 0) {
      return a2;
    }
    if (a2.length == 0) {
      return a1;
    }
    byte[] result = new byte[a1.length + a2.length];
    System.arraycopy(a1, 0, result, 0, a1.length);
    System.arraycopy(a2, 0, result, a1.length, a2.length);
    return result;
  }

  /**
   * Allocates new array of size <code>array.length + collection.size()</code> and copies elements of <code>array</code> and
   * <code>collection</code> to it.
   *
   * @param array      source array
   * @param collection source collection
   * @param factory    array factory used to create destination array of type <code>T</code>
   * @return destination array
   */
  @NotNull
  @Contract(pure=true)
  public static <T> T[] mergeArrayAndCollection(@NotNull T[] array,
                                                @NotNull Collection<T> collection,
                                                @NotNull final ArrayFactory<T> factory) {
    if (collection.isEmpty()) {
      return array;
    }

    final T[] array2;
    try {
      array2 = collection.toArray(factory.create(collection.size()));
    }
    catch (ArrayStoreException e) {
      throw new RuntimeException("Bad elements in collection: " + collection, e);
    }

    if (array.length == 0) {
      return array2;
    }

    final T[] result = factory.create(array.length + collection.size());
    System.arraycopy(array, 0, result, 0, array.length);
    System.arraycopy(array2, 0, result, array.length, array2.length);
    return result;
  }

  /**
   * Appends <code>element</code> to the <code>src</code> array. As you can
   * imagine the appended element will be the last one in the returned result.
   *
   * @param src     array to which the <code>element</code> should be appended.
   * @param element object to be appended to the end of <code>src</code> array.
   * @return new array
   */
  @NotNull
  @Contract(pure=true)
  public static <T> T[] append(@NotNull final T[] src, @Nullable final T element) {
    return append(src, element, (Class<T>)src.getClass().getComponentType());
  }

  @NotNull
  @Contract(pure=true)
  public static <T> T[] prepend(final T element, @NotNull final T[] array) {
    return prepend(element, array, (Class<T>)array.getClass().getComponentType());
  }

  @NotNull
  @Contract(pure=true)
  public static <T> T[] prepend(T element, @NotNull T[] array, @NotNull Class<T> type) {
    int length = array.length;
    T[] result = (T[])Array.newInstance(type, length + 1);
    System.arraycopy(array, 0, result, 1, length);
    result[0] = element;
    return result;
  }

  @NotNull
  @Contract(pure=true)
  public static byte[] prepend(byte element, @NotNull byte[] array) {
    int length = array.length;
    final byte[] result = new byte[length + 1];
    result[0] = element;
    System.arraycopy(array, 0, result, 1, length);
    return result;
  }

  @NotNull
  @Contract(pure=true)
  public static <T> T[] append(@NotNull final T[] src, final T element, @NotNull ArrayFactory<T> factory) {
    int length = src.length;
    T[] result = factory.create(length + 1);
    System.arraycopy(src, 0, result, 0, length);
    result[length] = element;
    return result;
  }

  @NotNull
  @Contract(pure=true)
  public static <T> T[] append(@NotNull T[] src, @Nullable final T element, @NotNull Class<T> componentType) {
    int length = src.length;
    T[] result = (T[])Array.newInstance(componentType, length + 1);
    System.arraycopy(src, 0, result, 0, length);
    result[length] = element;
    return result;
  }

  /**
   * Removes element with index <code>idx</code> from array <code>src</code>.
   *
   * @param src array.
   * @param idx index of element to be removed.
   * @return modified array.
   */
  @NotNull
  @Contract(pure=true)
  public static <T> T[] remove(@NotNull final T[] src, int idx) {
    int length = src.length;
    if (idx < 0 || idx >= length) {
      throw new IllegalArgumentException("invalid index: " + idx);
    }
    T[] result = (T[])Array.newInstance(src.getClass().getComponentType(), length - 1);
    System.arraycopy(src, 0, result, 0, idx);
    System.arraycopy(src, idx + 1, result, idx, length - idx - 1);
    return result;
  }

  @NotNull
  @Contract(pure=true)
  public static <T> T[] remove(@NotNull final T[] src, int idx, @NotNull ArrayFactory<T> factory) {
    int length = src.length;
    if (idx < 0 || idx >= length) {
      throw new IllegalArgumentException("invalid index: " + idx);
    }
    T[] result = factory.create(length - 1);
    System.arraycopy(src, 0, result, 0, idx);
    System.arraycopy(src, idx + 1, result, idx, length - idx - 1);
    return result;
  }

  @NotNull
  @Contract(pure=true)
  public static <T> T[] remove(@NotNull final T[] src, T element) {
    final int idx = find(src, element);
    if (idx == -1) return src;

    return remove(src, idx);
  }

  @NotNull
  @Contract(pure=true)
  public static <T> T[] remove(@NotNull final T[] src, T element, @NotNull ArrayFactory<T> factory) {
    final int idx = find(src, element);
    if (idx == -1) return src;

    return remove(src, idx, factory);
  }

  @NotNull
  @Contract(pure=true)
  public static int[] remove(@NotNull final int[] src, int idx) {
    int length = src.length;
    if (idx < 0 || idx >= length) {
      throw new IllegalArgumentException("invalid index: " + idx);
    }
    int[] result = newIntArray(src.length - 1);
    System.arraycopy(src, 0, result, 0, idx);
    System.arraycopy(src, idx + 1, result, idx, length - idx - 1);
    return result;
  }
  @NotNull
  @Contract(pure=true)
  public static short[] remove(@NotNull final short[] src, int idx) {
    int length = src.length;
    if (idx < 0 || idx >= length) {
      throw new IllegalArgumentException("invalid index: " + idx);
    }
    short[] result = src.length == 1 ? EMPTY_SHORT_ARRAY : new short[src.length - 1];
    System.arraycopy(src, 0, result, 0, idx);
    System.arraycopy(src, idx + 1, result, idx, length - idx - 1);
    return result;
  }

  @Contract(pure=true)
  public static int find(@NotNull int[] src, int obj) {
    return indexOf(src, obj);
  }

  @Contract(pure=true)
  public static <T> int find(@NotNull final T[] src, final T obj) {
    return ArrayUtilRt.find(src, obj);
  }

  @Contract(pure=true)
  public static boolean startsWith(@NotNull byte[] array, @NotNull byte[] prefix) {
    if (array == prefix) {
      return true;
    }
    int length = prefix.length;
    if (array.length < length) {
      return false;
    }

    for (int i = 0; i < length; i++) {
      if (array[i] != prefix[i]) {
        return false;
      }
    }

    return true;
  }

  @Contract(pure=true)
  public static <E> boolean startsWith(@NotNull E[] array, @NotNull E[] subArray) {
    if (array == subArray) {
      return true;
    }
    int length = subArray.length;
    if (array.length < length) {
      return false;
    }

    for (int i = 0; i < length; i++) {
      if (!Comparing.equal(array[i], subArray[i])) {
        return false;
      }
    }

    return true;
  }

  @Contract(pure=true)
  public static boolean startsWith(@NotNull byte[] array, int start, @NotNull byte[] subArray) {
    int length = subArray.length;
    if (array.length - start < length) {
      return false;
    }

    for (int i = 0; i < length; i++) {
      if (array[start + i] != subArray[i]) {
        return false;
      }
    }

    return true;
  }

  @Contract(pure=true)
  public static <T> boolean equals(@NotNull T[] a1, @NotNull T[] a2, @NotNull Equality<? super T> comparator) {
    if (a1 == a2) {
      return true;
    }

    int length = a2.length;
    if (a1.length != length) {
      return false;
    }

    for (int i = 0; i < length; i++) {
      if (!comparator.equals(a1[i], a2[i])) {
        return false;
      }
    }
    return true;
  }

  @Contract(pure=true)
  public static <T> boolean equals(@NotNull T[] a1, @NotNull T[] a2, @NotNull Comparator<? super T> comparator) {
    if (a1 == a2) {
      return true;
    }
    int length = a2.length;
    if (a1.length != length) {
      return false;
    }

    for (int i = 0; i < length; i++) {
      if (comparator.compare(a1[i], a2[i]) != 0) {
        return false;
      }
    }
    return true;
  }

  @NotNull
  @Contract(pure=true)
  public static <T> T[] reverseArray(@NotNull T[] array) {
    T[] newArray = array.clone();
    for (int i = 0; i < array.length; i++) {
      newArray[array.length - i - 1] = array[i];
    }
    return newArray;
  }

  @NotNull
  @Contract(pure=true)
  public static int[] reverseArray(@NotNull int[] array) {
    int[] newArray = array.clone();
    for (int i = 0; i < array.length; i++) {
      newArray[array.length - i - 1] = array[i];
    }
    return newArray;
  }

  public static void reverse(@NotNull char[] array) {
    for (int i = 0; i < array.length; i++) {
      swap(array, array.length - i - 1, i);
    }
  }

  @Contract(pure=true)
  public static int lexicographicCompare(@NotNull String[] obj1, @NotNull String[] obj2) {
    for (int i = 0; i < Math.max(obj1.length, obj2.length); i++) {
      String o1 = i < obj1.length ? obj1[i] : null;
      String o2 = i < obj2.length ? obj2[i] : null;
      if (o1 == null) return -1;
      if (o2 == null) return 1;
      int res = o1.compareToIgnoreCase(o2);
      if (res != 0) return res;
    }
    return 0;
  }

  //must be Comparables
  @Contract(pure=true)
  public static <T> int lexicographicCompare(@NotNull T[] obj1, @NotNull T[] obj2) {
    for (int i = 0; i < Math.max(obj1.length, obj2.length); i++) {
      T o1 = i < obj1.length ? obj1[i] : null;
      T o2 = i < obj2.length ? obj2[i] : null;
      if (o1 == null) return -1;
      if (o2 == null) return 1;
      int res = ((Comparable)o1).compareTo(o2);
      if (res != 0) return res;
    }
    return 0;
  }

  public static <T> void swap(@NotNull T[] array, int i1, int i2) {
    final T t = array[i1];
    array[i1] = array[i2];
    array[i2] = t;
  }

  public static void swap(@NotNull int[] array, int i1, int i2) {
    final int t = array[i1];
    array[i1] = array[i2];
    array[i2] = t;
  }

  public static void swap(@NotNull boolean[] array, int i1, int i2) {
    final boolean t = array[i1];
    array[i1] = array[i2];
    array[i2] = t;
  }

  public static void swap(@NotNull char[] array, int i1, int i2) {
    final char t = array[i1];
    array[i1] = array[i2];
    array[i2] = t;
  }

  public static <T> void rotateLeft(@NotNull T[] array, int i1, int i2) {
    final T t = array[i1];
    System.arraycopy(array, i1 + 1, array, i1, i2 - i1);
    array[i2] = t;
  }

  public static <T> void rotateRight(@NotNull T[] array, int i1, int i2) {
    final T t = array[i2];
    System.arraycopy(array, i1, array, i1 + 1, i2 - i1);
    array[i1] = t;
  }

  @Contract(pure=true)
  public static int indexOf(@NotNull Object[] objects, @Nullable Object object) {
    return indexOf(objects, object, 0, objects.length);
  }

  @Contract(pure=true)
  public static int indexOf(@NotNull Object[] objects, Object object, int start, int end) {
    if (object == null) {
      for (int i = start; i < end; i++) {
        if (objects[i] == null) return i;
      }
    }
    else {
      for (int i = start; i < end; i++) {
        if (object.equals(objects[i])) return i;
      }
    }
    return -1;
  }

  @Contract(pure=true)
  public static <T> int indexOf(@NotNull List<T> objects, T object, @NotNull Equality<T> comparator) {
    for (int i = 0; i < objects.size(); i++) {
      if (comparator.equals(objects.get(i), object)) return i;
    }
    return -1;
  }

  @Contract(pure=true)
  public static <T> int indexOf(@NotNull List<T> objects, T object, @NotNull Comparator<T> comparator) {
    for (int i = 0; i < objects.size(); i++) {
      if (comparator.compare(objects.get(i), object) == 0) return i;
    }
    return -1;
  }

  @Contract(pure=true)
  public static <T> int indexOf(@NotNull T[] objects, T object, @NotNull Equality<T> comparator) {
    for (int i = 0; i < objects.length; i++) {
      if (comparator.equals(objects[i], object)) return i;
    }
    return -1;
  }

  @Contract(pure=true)
  public static int indexOf(@NotNull long[] ints, long value) {
    for (int i = 0; i < ints.length; i++) {
      if (ints[i] == value) return i;
    }

    return -1;
  }
  @Contract(pure=true)
  public static int indexOf(@NotNull int[] ints, int value) {
    for (int i = 0; i < ints.length; i++) {
      if (ints[i] == value) return i;
    }

    return -1;
  }
  @Contract(pure=true)
  public static int indexOf(@NotNull short[] ints, short value) {
    for (int i = 0; i < ints.length; i++) {
      if (ints[i] == value) return i;
    }

    return -1;
  }

  @Contract(pure=true)
  public static <T> int lastIndexOf(@NotNull final T[] src, final T obj) {
    for (int i = src.length - 1; i >= 0; i--) {
      final T o = src[i];
      if (o == null) {
        if (obj == null) {
          return i;
        }
      }
      else {
        if (o.equals(obj)) {
          return i;
        }
      }
    }
    return -1;
  }

  @Contract(pure=true)
  public static <T> int lastIndexOf(@NotNull final T[] src, final T obj, @NotNull Equality<? super T> comparator) {
    for (int i = src.length - 1; i >= 0; i--) {
      final T o = src[i];
      if (comparator.equals(obj, o)) {
        return i;
      }
    }
    return -1;
  }

  @Contract(pure=true)
  public static <T> int lastIndexOf(@NotNull List<T> src, final T obj, @NotNull Equality<? super T> comparator) {
    for (int i = src.size() - 1; i >= 0; i--) {
      final T o = src.get(i);
      if (comparator.equals(obj, o)) {
        return i;
      }
    }
    return -1;
  }

  @Contract(pure=true)
  public static boolean contains(@Nullable final Object o, @NotNull Object... objects) {
    return indexOf(objects, o) >= 0;
  }

  @Contract(pure=true)
  public static boolean contains(@Nullable final String s, @NotNull String... strings) {
    if (s == null) {
      for (String str : strings) {
        if (str == null) return true;
      }
    }
    else {
      for (String str : strings) {
        if (s.equals(str)) return true;
      }
    }

    return false;
  }

  @NotNull
  @Contract(pure=true)
  public static int[] newIntArray(int count) {
    return count == 0 ? EMPTY_INT_ARRAY : new int[count];
  }

  @NotNull
  @Contract(pure=true)
  public static long[] newLongArray(int count) {
    return count == 0 ? EMPTY_LONG_ARRAY : new long[count];
  }

  @NotNull
  @Contract(pure=true)
  public static String[] newStringArray(int count) {
    return count == 0 ? EMPTY_STRING_ARRAY : new String[count];
  }

  @NotNull
  @Contract(pure=true)
  public static Object[] newObjectArray(int count) {
    return count == 0 ? EMPTY_OBJECT_ARRAY : new Object[count];
  }

  @NotNull
  @Contract(pure=true)
  public static <E> E[] ensureExactSize(int count, @NotNull E[] sample) {
    if (count == sample.length) return sample;
    @SuppressWarnings({"unchecked"}) final E[] array = (E[])Array.newInstance(sample.getClass().getComponentType(), count);
    return array;
  }

  @Nullable
  @Contract(pure=true)
  public static <T> T getFirstElement(@Nullable T[] array) {
    return array != null && array.length > 0 ? array[0] : null;
  }

  @Nullable
  @Contract(pure=true)
  public static <T> T getLastElement(@Nullable T[] array) {
    return array != null && array.length > 0 ? array[array.length - 1] : null;
  }

  @NotNull
  @Contract(pure=true)
  public static String[] toStringArray(@Nullable Collection<String> collection) {
    return ArrayUtilRt.toStringArray(collection);
  }

  public static <T> void copy(@NotNull final Collection<? extends T> src, @NotNull final T[] dst, final int dstOffset) {
    int i = dstOffset;
    for (T t : src) {
      dst[i++] = t;
    }
  }

  @NotNull
  public static <T> T[] stripTrailingNulls(@NotNull T[] array) {
    return array.length != 0 && array[array.length-1] == null ? Arrays.copyOf(array, trailingNullsIndex(array)) : array;
  }

  private static <T> int trailingNullsIndex(@NotNull T[] array) {
    for (int i = array.length - 1; i >= 0; i--) {
      if (array[i] != null) {
        return i + 1;
      }
    }
    return 0;
  }
}
