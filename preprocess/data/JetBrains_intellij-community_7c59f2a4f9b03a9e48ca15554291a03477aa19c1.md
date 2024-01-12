Refactoring Types: ['Extract Method']
j/codeInsight/daemon/impl/quickfix/OrderEntryFix.java
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
package com.intellij.codeInsight.daemon.impl.quickfix;

import com.intellij.codeInsight.AnnotationUtil;
import com.intellij.codeInsight.daemon.QuickFixActionRegistrar;
import com.intellij.codeInsight.daemon.QuickFixBundle;
import com.intellij.codeInsight.daemon.impl.actions.AddImportAction;
import com.intellij.codeInsight.intention.IntentionAction;
import com.intellij.codeInspection.LocalQuickFix;
import com.intellij.codeInspection.ProblemDescriptor;
import com.intellij.openapi.application.ApplicationManager;
import com.intellij.openapi.application.PathManager;
import com.intellij.openapi.application.Result;
import com.intellij.openapi.command.WriteCommandAction;
import com.intellij.openapi.editor.Editor;
import com.intellij.openapi.module.EffectiveLanguageLevelUtil;
import com.intellij.openapi.module.Module;
import com.intellij.openapi.project.DumbService;
import com.intellij.openapi.project.Project;
import com.intellij.openapi.projectRoots.ex.JavaSdkUtil;
import com.intellij.openapi.roots.*;
import com.intellij.openapi.roots.impl.OrderEntryUtil;
import com.intellij.openapi.roots.libraries.Library;
import com.intellij.openapi.vfs.LocalFileSystem;
import com.intellij.openapi.vfs.VfsUtil;
import com.intellij.openapi.vfs.VirtualFile;
import com.intellij.openapi.vfs.VirtualFileManager;
import com.intellij.packageDependencies.DependencyValidationManager;
import com.intellij.pom.java.LanguageLevel;
import com.intellij.psi.*;
import com.intellij.psi.search.GlobalSearchScope;
import com.intellij.psi.search.PsiShortNamesCache;
import com.intellij.psi.util.PsiTreeUtil;
import com.intellij.psi.util.PsiUtil;
import com.intellij.psi.util.PsiUtilCore;
import com.intellij.util.Function;
import com.intellij.util.PathUtil;
import com.intellij.util.containers.ContainerUtil;
import gnu.trove.THashSet;
import org.jetbrains.annotations.NonNls;
import org.jetbrains.annotations.NotNull;
import org.jetbrains.annotations.Nullable;

import java.io.File;
import java.util.*;

/**
 * @author cdr
 */
public abstract class OrderEntryFix implements IntentionAction, LocalQuickFix {
  OrderEntryFix() {
  }

  @Override
  public boolean startInWriteAction() {
    return true;
  }

  @Override
  @NotNull
  public String getName() {
    return getText();
  }

  @Override
  public void applyFix(@NotNull final Project project, @NotNull final ProblemDescriptor descriptor) {
    invoke(project, null, descriptor.getPsiElement().getContainingFile());
  }

  @Nullable
  public static List<LocalQuickFix> registerFixes(@NotNull QuickFixActionRegistrar registrar, @NotNull final PsiReference reference) {
    final PsiElement psiElement = reference.getElement();
    @NonNls final String referenceName = reference.getRangeInElement().substring(psiElement.getText());

    Project project = psiElement.getProject();
    PsiFile containingFile = psiElement.getContainingFile();
    if (containingFile == null) return null;

    final VirtualFile classVFile = containingFile.getVirtualFile();
    if (classVFile == null) return null;

    final ProjectFileIndex fileIndex = ProjectRootManager.getInstance(project).getFileIndex();
    final Module currentModule = fileIndex.getModuleForFile(classVFile);
    if (currentModule == null) return null;

    if ("TestCase".equals(referenceName) || isAnnotation(psiElement) && isJunitAnnotationName(referenceName, psiElement)) {
      final boolean isJunit4 = !referenceName.equals("TestCase");
      @NonNls final String className = isJunit4 ? "org.junit." + referenceName : "junit.framework.TestCase";
      PsiClass found =
        JavaPsiFacade.getInstance(project).findClass(className, currentModule.getModuleWithDependenciesAndLibrariesScope(true));
      if (found != null) return null; //no need to add junit to classpath
      final OrderEntryFix fix = new OrderEntryFix() {
        @Override
        @NotNull
        public String getText() {
          return QuickFixBundle.message("orderEntry.fix.add.junit.jar.to.classpath");
        }

        @Override
        @NotNull
        public String getFamilyName() {
          return getText();
        }

        @Override
        public boolean isAvailable(@NotNull Project project, Editor editor, PsiFile file) {
          return !project.isDisposed() && !currentModule.isDisposed();
        }

        @Override
        public void invoke(@NotNull Project project, @Nullable Editor editor, PsiFile file) {
          if (isJunit4) {
            final VirtualFile location = PsiUtilCore.getVirtualFile(reference.getElement());
            boolean inTests = location != null && ModuleRootManager.getInstance(currentModule).getFileIndex().isInTestSourceContent(location);
            DumbService.getInstance(project).setAlternativeResolveEnabled(true);
            try {
              addJUnit4Library(inTests, currentModule);
              final GlobalSearchScope scope = GlobalSearchScope.moduleWithLibrariesScope(currentModule);
              final PsiClass aClass = JavaPsiFacade.getInstance(project).findClass(className, scope);
              if (aClass != null && editor != null) {
                new AddImportAction(project, reference, editor, aClass).execute();
              }
            }
            catch (ClassNotFoundException e) {
              throw new RuntimeException(e);
            }
            finally {
              DumbService.getInstance(project).setAlternativeResolveEnabled(false);
            }
          } else {
            addBundledJarToRoots(project, editor, currentModule, reference, className, JavaSdkUtil.getJunit3JarPath());
          }
        }
      };
      registrar.register(fix);
      return Collections.singletonList((LocalQuickFix)fix);
    }

    if (isAnnotation(psiElement) && AnnotationUtil.isJetbrainsAnnotation(referenceName)) {
      @NonNls final String className = "org.jetbrains.annotations." + referenceName;
      PsiClass found =
        JavaPsiFacade.getInstance(project).findClass(className, currentModule.getModuleWithDependenciesAndLibrariesScope(true));
      if (found != null) return null; //no need to add junit to classpath
      final OrderEntryFix fix = new OrderEntryFix() {
        @Override
        @NotNull
        public String getText() {
          return QuickFixBundle.message("orderEntry.fix.add.annotations.jar.to.classpath");
        }

        @Override
        @NotNull
        public String getFamilyName() {
          return getText();
        }

        @Override
        public boolean isAvailable(@NotNull Project project, Editor editor, PsiFile file) {
          return !project.isDisposed() && !currentModule.isDisposed();
        }

        @Override
        public void invoke(@NotNull final Project project, final Editor editor, PsiFile file) {
          ApplicationManager.getApplication().invokeLater(new Runnable() {
            @Override
            public void run() {
              final String libraryPath = locateAnnotationsJar(currentModule);
              if (libraryPath != null) {
                new WriteCommandAction(project) {
                  @Override
                  protected void run(final Result result) throws Throwable {
                    addBundledJarToRoots(project, editor, currentModule, reference, "org.jetbrains.annotations." + referenceName, libraryPath);
                  }
                }.execute();
              }
            }
          });
        }
      };
      registrar.register(fix);
      return Collections.singletonList((LocalQuickFix)fix);
    }

    List<LocalQuickFix> result = new ArrayList<LocalQuickFix>();
    Set<Object> librariesToAdd = new THashSet<Object>();
    final JavaPsiFacade facade = JavaPsiFacade.getInstance(psiElement.getProject());
    PsiClass[] classes = PsiShortNamesCache.getInstance(project).getClassesByName(referenceName, GlobalSearchScope.allScope(project));
    List<PsiClass> allowedDependencies = filterAllowedDependencies(psiElement, classes);
    if (allowedDependencies.isEmpty()) {
      return result;
    }
    classes = allowedDependencies.toArray(new PsiClass[allowedDependencies.size()]);
    final OrderEntryFix moduleDependencyFix = new AddModuleDependencyFix(currentModule, classVFile, classes, reference);
    registrar.register(moduleDependencyFix);
    result.add(moduleDependencyFix);
    for (final PsiClass aClass : classes) {
      if (!facade.getResolveHelper().isAccessible(aClass, psiElement, aClass)) continue;
      PsiFile psiFile = aClass.getContainingFile();
      if (psiFile == null) continue;
      VirtualFile virtualFile = psiFile.getVirtualFile();
      if (virtualFile == null) continue;
      ModuleFileIndex moduleFileIndex = ModuleRootManager.getInstance(currentModule).getFileIndex();
      for (OrderEntry orderEntry : fileIndex.getOrderEntriesForFile(virtualFile)) {
        if (orderEntry instanceof LibraryOrderEntry) {
          final LibraryOrderEntry libraryEntry = (LibraryOrderEntry)orderEntry;
          final Library library = libraryEntry.getLibrary();
          if (library == null) continue;
          VirtualFile[] files = library.getFiles(OrderRootType.CLASSES);
          if (files.length == 0) continue;
          final VirtualFile jar = files[0];

          if (jar == null || libraryEntry.isModuleLevel() && !librariesToAdd.add(jar) || !librariesToAdd.add(library)) continue;
          OrderEntry entryForFile = moduleFileIndex.getOrderEntryForFile(virtualFile);
          if (entryForFile != null &&
              !(entryForFile instanceof ExportableOrderEntry &&
                ((ExportableOrderEntry)entryForFile).getScope() == DependencyScope.TEST &&
                !ModuleRootManager.getInstance(currentModule).getFileIndex().isInTestSourceContent(classVFile))) {
            continue;
          }
          final OrderEntryFix fix = new OrderEntryFix() {
            @Override
            @NotNull
            public String getText() {
              return QuickFixBundle.message("orderEntry.fix.add.library.to.classpath", libraryEntry.getPresentableName());
            }

            @Override
            @NotNull
            public String getFamilyName() {
              return QuickFixBundle.message("orderEntry.fix.family.add.library.to.classpath");
            }

            @Override
            public boolean isAvailable(@NotNull Project project, Editor editor, PsiFile file) {
              return !project.isDisposed() && !currentModule.isDisposed() && libraryEntry.isValid();
            }

            @Override
            public void invoke(@NotNull final Project project, @Nullable final Editor editor, PsiFile file) {
              OrderEntryUtil.addLibraryToRoots(libraryEntry, currentModule);
              if (editor != null) {
                DumbService.getInstance(project).withAlternativeResolveEnabled(new Runnable() {
                  @Override
                  public void run() {
                    new AddImportAction(project, reference, editor, aClass).execute();
                  }
                });
              }
            }
          };
          registrar.register(fix);
          result.add(fix);
        }
      }
    }
    return result;
  }

  public static void addJUnit4Library(boolean inTests, Module currentModule) throws ClassNotFoundException {
    final String[] junit4Paths = {JavaSdkUtil.getJunit4JarPath(), 
                                  PathUtil.getJarPathForClass(Class.forName("org.hamcrest.Matcher")), 
                                  PathUtil.getJarPathForClass(Class.forName("org.hamcrest.Matchers"))};
    ModuleRootModificationUtil.addModuleLibrary(currentModule,
                                                "JUnit4",
                                                ContainerUtil.map(junit4Paths,
                                                                  new Function<String, String>() {
                                                                    @Override
                                                                    public String fun(String libPath) {
                                                                      return convertToLibraryRoot(libPath).getUrl();
                                                                    }
                                                                  }),
                                                Collections.<String>emptyList(), inTests ? DependencyScope.TEST : DependencyScope.COMPILE);
  }

  private static List<PsiClass> filterAllowedDependencies(PsiElement element, PsiClass[] classes) {
    DependencyValidationManager dependencyValidationManager = DependencyValidationManager.getInstance(element.getProject());
    PsiFile fromFile = element.getContainingFile();
    List<PsiClass> result = new ArrayList<PsiClass>();
    for (PsiClass psiClass : classes) {
      if (dependencyValidationManager.getViolatorDependencyRule(fromFile, psiClass.getContainingFile()) == null) {
        result.add(psiClass);
      }
    }
    return result;
  }

  private static boolean isAnnotation(final PsiElement psiElement) {
    return PsiTreeUtil.getParentOfType(psiElement, PsiAnnotation.class) != null && PsiUtil.isLanguageLevel5OrHigher(psiElement);
  }

  private static boolean isJunitAnnotationName(@NonNls final String referenceName, @NotNull final PsiElement psiElement) {
    if ("Test".equals(referenceName) || "Ignore".equals(referenceName) || "RunWith".equals(referenceName) ||
        "Before".equals(referenceName) || "BeforeClass".equals(referenceName) ||
        "After".equals(referenceName) || "AfterClass".equals(referenceName)) {
      return true;
    }
    final PsiElement parent = psiElement.getParent();
    if (parent != null && !(parent instanceof PsiAnnotation)) {
      final PsiReference reference = parent.getReference();
      if (reference != null) {
        final String referenceText = parent.getText();
        if (isJunitAnnotationName(reference.getRangeInElement().substring(referenceText), parent)) {
          final int lastDot = referenceText.lastIndexOf('.');
          return lastDot > -1 && referenceText.substring(0, lastDot).equals("org.junit");
        }
      }
    }
    return false;
  }

  public static void addBundledJarToRoots(final Project project,
                                          @Nullable final Editor editor,
                                          final Module currentModule,
                                          @Nullable final PsiReference reference,
                                          @NonNls final String className,
                                          @NonNls final String libVirtFile) {
    addJarToRoots(libVirtFile, currentModule, reference != null ? reference.getElement() : null);

    DumbService.getInstance(project).withAlternativeResolveEnabled(new Runnable() {
      @Override
      public void run() {
        GlobalSearchScope scope = GlobalSearchScope.moduleWithLibrariesScope(currentModule);
        PsiClass aClass = JavaPsiFacade.getInstance(project).findClass(className, scope);
        if (aClass != null && editor != null && reference != null) {
          new AddImportAction(project, reference, editor, aClass).execute();
        }
      }
    });
  }

  public static void addJarToRoots(String libPath, final Module module, @Nullable PsiElement location) {
    VirtualFile libVirtFile = convertToLibraryRoot(libPath);

    boolean inTests = false;
    if (location != null) {
      final VirtualFile vFile = location.getContainingFile().getVirtualFile();
      if (vFile != null && ModuleRootManager.getInstance(module).getFileIndex().isInTestSourceContent(vFile)) {
        inTests = true;
      }
    }
    ModuleRootModificationUtil.addModuleLibrary(module, null, Collections.singletonList(libVirtFile.getUrl()),
                                                Collections.<String>emptyList(), inTests ? DependencyScope.TEST : DependencyScope.COMPILE);
  }

  @NotNull
  private static VirtualFile convertToLibraryRoot(String libPath) {
    final File libraryRoot = new File(libPath);
    LocalFileSystem.getInstance().refreshAndFindFileByIoFile(libraryRoot);
    String url = VfsUtil.getUrlForLibraryRoot(libraryRoot);
    VirtualFile libVirtFile = VirtualFileManager.getInstance().findFileByUrl(url);
    assert libVirtFile != null : libPath;
    return libVirtFile;
  }

  public static boolean ensureAnnotationsJarInPath(final Module module) {
    if (isAnnotationsJarInPath(module)) return true;
    if (module == null) return false;
    final String libraryPath = locateAnnotationsJar(module);
    if (libraryPath != null) {
      new WriteCommandAction(module.getProject()) {
        @Override
        protected void run(final Result result) throws Throwable {
          addJarToRoots(libraryPath, module, null);
        }
      }.execute();
      return true;
    }
    return false;
  }

  @Nullable
  public static String locateAnnotationsJar(@NotNull Module module) {
    String jarName;
    String libPath;
    if (EffectiveLanguageLevelUtil.getEffectiveLanguageLevel(module).isAtLeast(LanguageLevel.JDK_1_8)) {
      jarName = "annotations-java8.jar";
      libPath = new File(PathManager.getHomePath(), "redist").getAbsolutePath();
    }
    else {
      jarName = "annotations.jar";
      libPath = PathManager.getLibPath();
    }
    final LocateLibraryDialog dialog = new LocateLibraryDialog(module, libPath, jarName, QuickFixBundle.message("add.library.annotations.description"));
    return dialog.showAndGet() ? dialog.getResultingLibraryPath() : null;
  }

  public static boolean isAnnotationsJarInPath(Module module) {
    if (module == null) return false;
    return JavaPsiFacade.getInstance(module.getProject())
             .findClass(AnnotationUtil.LANGUAGE, GlobalSearchScope.moduleWithDependenciesAndLibrariesScope(module)) != null;
  }
}


File: java/java-impl/src/com/intellij/codeInspection/concurrencyAnnotations/JCiPOrderEntryFix.java
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

/*
 * User: anna
 * Date: 30-Jul-2007
 */
package com.intellij.codeInspection.concurrencyAnnotations;

import com.intellij.codeInsight.TargetElementUtil;
import com.intellij.codeInsight.daemon.impl.quickfix.OrderEntryFix;
import com.intellij.codeInsight.intention.IntentionAction;
import com.intellij.openapi.diagnostic.Logger;
import com.intellij.openapi.editor.Editor;
import com.intellij.openapi.module.ModuleUtil;
import com.intellij.openapi.project.Project;
import com.intellij.openapi.roots.ProjectFileIndex;
import com.intellij.openapi.roots.ProjectRootManager;
import com.intellij.openapi.vfs.VirtualFile;
import com.intellij.psi.*;
import com.intellij.psi.util.PsiUtil;
import com.intellij.util.IncorrectOperationException;
import com.intellij.util.PathUtil;
import net.jcip.annotations.GuardedBy;
import org.jetbrains.annotations.NonNls;
import org.jetbrains.annotations.NotNull;

public class JCiPOrderEntryFix implements IntentionAction {
  private static final Logger LOG = Logger.getInstance("#" + JCiPOrderEntryFix.class.getName());

  @Override
  @NotNull
  public String getText() {
    return "Add jcip-annotations.jar to classpath";
  }

  @Override
  @NotNull
  public String getFamilyName() {
    return getText();
  }

  @Override
  public boolean isAvailable(@NotNull final Project project, final Editor editor, final PsiFile file) {
    if (!(file instanceof PsiJavaFile)) return false;

    final PsiReference reference = TargetElementUtil.findReference(editor);
    if (!(reference instanceof PsiJavaCodeReferenceElement)) return false;
    if (reference.resolve() != null) return false;
    @NonNls final String referenceName = ((PsiJavaCodeReferenceElement)reference).getReferenceName();
    if (referenceName == null) return false;
    final ProjectFileIndex fileIndex = ProjectRootManager.getInstance(project).getFileIndex();
    final VirtualFile virtualFile = file.getVirtualFile();
    if (virtualFile == null) return false;
    if (fileIndex.getModuleForFile(virtualFile) == null) return false;
    if (!(((PsiJavaCodeReferenceElement)reference).getParent() instanceof PsiAnnotation &&
          PsiUtil.isLanguageLevel5OrHigher(((PsiJavaCodeReferenceElement)reference)))) return false;
    if (!JCiPUtil.isJCiPAnnotation(referenceName)) return false;
    return true;
  }

  @Override
  public void invoke(@NotNull final Project project, final Editor editor, final PsiFile file) throws IncorrectOperationException {
    final PsiJavaCodeReferenceElement reference = (PsiJavaCodeReferenceElement)TargetElementUtil.findReference(editor);
    LOG.assertTrue(reference != null);
    String jarPath = PathUtil.getJarPathForClass(GuardedBy.class);
    final VirtualFile virtualFile = file.getVirtualFile();
    LOG.assertTrue(virtualFile != null);
    OrderEntryFix.addBundledJarToRoots(project, editor, ModuleUtil.findModuleForFile(virtualFile, project), reference,
                                       "net.jcip.annotations." + reference.getReferenceName(), jarPath);
  }

  @Override
  public boolean startInWriteAction() {
    return true;
  }

}

File: java/java-impl/src/com/intellij/codeInspection/inferNullity/InferNullityAnnotationsAction.java
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
package com.intellij.codeInspection.inferNullity;

import com.intellij.analysis.AnalysisScope;
import com.intellij.analysis.AnalysisScopeBundle;
import com.intellij.analysis.BaseAnalysisAction;
import com.intellij.analysis.BaseAnalysisActionDialog;
import com.intellij.codeInsight.AnnotationUtil;
import com.intellij.codeInsight.FileModificationService;
import com.intellij.codeInsight.NullableNotNullManager;
import com.intellij.codeInsight.daemon.impl.quickfix.OrderEntryFix;
import com.intellij.history.LocalHistory;
import com.intellij.history.LocalHistoryAction;
import com.intellij.ide.util.PropertiesComponent;
import com.intellij.openapi.application.ApplicationManager;
import com.intellij.openapi.application.Result;
import com.intellij.openapi.command.WriteCommandAction;
import com.intellij.openapi.editor.Document;
import com.intellij.openapi.module.Module;
import com.intellij.openapi.module.ModuleUtilCore;
import com.intellij.openapi.progress.ProgressIndicator;
import com.intellij.openapi.progress.ProgressManager;
import com.intellij.openapi.project.Project;
import com.intellij.openapi.project.ProjectUtil;
import com.intellij.openapi.roots.ModuleRootModificationUtil;
import com.intellij.openapi.roots.libraries.Library;
import com.intellij.openapi.roots.libraries.LibraryUtil;
import com.intellij.openapi.ui.Messages;
import com.intellij.openapi.ui.VerticalFlowLayout;
import com.intellij.openapi.util.Computable;
import com.intellij.openapi.util.Factory;
import com.intellij.openapi.util.Ref;
import com.intellij.openapi.util.text.StringUtil;
import com.intellij.openapi.vfs.VirtualFile;
import com.intellij.pom.java.LanguageLevel;
import com.intellij.psi.*;
import com.intellij.psi.search.GlobalSearchScope;
import com.intellij.psi.util.PsiUtil;
import com.intellij.refactoring.RefactoringBundle;
import com.intellij.ui.TitledSeparator;
import com.intellij.usageView.UsageInfo;
import com.intellij.usageView.UsageViewUtil;
import com.intellij.usages.*;
import com.intellij.util.Function;
import com.intellij.util.Processor;
import com.intellij.util.SequentialModalProgressTask;
import com.intellij.util.containers.ContainerUtil;
import org.jetbrains.annotations.NonNls;
import org.jetbrains.annotations.NotNull;

import javax.swing.*;
import java.util.*;

public class InferNullityAnnotationsAction extends BaseAnalysisAction {
  @NonNls private static final String INFER_NULLITY_ANNOTATIONS = "Infer Nullity Annotations";
  @NonNls private static final String ANNOTATE_LOCAL_VARIABLES = "annotate.local.variables";
  private JCheckBox myAnnotateLocalVariablesCb;

  public InferNullityAnnotationsAction() {
    super("Infer Nullity", INFER_NULLITY_ANNOTATIONS);
  }

  @Override
  protected void analyze(@NotNull final Project project, @NotNull final AnalysisScope scope) {
    PropertiesComponent.getInstance().setValue(ANNOTATE_LOCAL_VARIABLES, String.valueOf(myAnnotateLocalVariablesCb.isSelected()));

    final ProgressManager progressManager = ProgressManager.getInstance();
    final Set<Module> modulesWithoutAnnotations = new HashSet<Module>();
    final Set<Module> modulesWithLL = new HashSet<Module>();
    final JavaPsiFacade javaPsiFacade = JavaPsiFacade.getInstance(project);
    final String defaultNullable = NullableNotNullManager.getInstance(project).getDefaultNullable();
    final int[] fileCount = new int[] {0};
    if (!progressManager.runProcessWithProgressSynchronously(new Runnable() {
      @Override
      public void run() {
        scope.accept(new PsiElementVisitor() {
          final private Set<Module> processed = new HashSet<Module>();

          @Override
          public void visitFile(PsiFile file) {
            fileCount[0]++;
            final ProgressIndicator progressIndicator = ProgressManager.getInstance().getProgressIndicator();
            if (progressIndicator != null) {
              final VirtualFile virtualFile = file.getVirtualFile();
              if (virtualFile != null) {
                progressIndicator.setText2(ProjectUtil.calcRelativeToProjectPath(virtualFile, project));
              }
              progressIndicator.setText(AnalysisScopeBundle.message("scanning.scope.progress.title"));
            }
            final Module module = ModuleUtilCore.findModuleForPsiElement(file);
            if (module != null && processed.add(module)) {
              if (PsiUtil.getLanguageLevel(file).compareTo(LanguageLevel.JDK_1_5) < 0) {
                modulesWithLL.add(module);
              }
              else if (javaPsiFacade.findClass(defaultNullable, GlobalSearchScope.moduleWithDependenciesAndLibrariesScope(module)) == null) {
                modulesWithoutAnnotations.add(module);
              }
            }
          }
        });
      }
    }, "Check Applicability...", true, project)) {
      return;
    }
    if (!modulesWithLL.isEmpty()) {
      Messages.showErrorDialog(project, "Infer Nullity Annotations requires the project language level be set to 1.5 or greater.",
                               INFER_NULLITY_ANNOTATIONS);
      return;
    }
    if (!modulesWithoutAnnotations.isEmpty()) {
      final Library annotationsLib = LibraryUtil.findLibraryByClass(defaultNullable, project);
      if (annotationsLib != null) {
        String message = "Module" + (modulesWithoutAnnotations.size() == 1 ? " " : "s ");
        message += StringUtil.join(modulesWithoutAnnotations, new Function<Module, String>() {
          @Override
          public String fun(Module module) {
            return module.getName();
          }
        }, ", ");
        message += (modulesWithoutAnnotations.size() == 1 ? " doesn't" : " don't");
        message += " refer to the existing '" +
                   annotationsLib.getName() +
                   "' library with IDEA nullity annotations. Would you like to add the dependenc";
        message += (modulesWithoutAnnotations.size() == 1 ? "y" : "ies") + " now?";
        if (Messages.showOkCancelDialog(project, message, INFER_NULLITY_ANNOTATIONS, Messages.getErrorIcon()) ==
            Messages.OK) {
          ApplicationManager.getApplication().runWriteAction(new Runnable() {
            @Override
            public void run() {
              for (Module module : modulesWithoutAnnotations) {
                ModuleRootModificationUtil.addDependency(module, annotationsLib);
              }
            }
          });
          restartAnalysis(project, scope);
        }
      }
      else if (Messages.showOkCancelDialog(project, "Infer Nullity Annotations requires that the nullity annotations" +
                                                    " be available in all your project sources.\n\nYou will need to add annotations.jar as a library. " +
                                                    "It is possible to configure custom JAR in e.g. Constant Conditions & Exceptions inspection or use JetBrains annotations available in installation. " +
                                                    " IntelliJ IDEA nullity annotations are freely usable and redistributable under the Apache 2.0 license. Would you like to do it now?",
                                           INFER_NULLITY_ANNOTATIONS, Messages.getErrorIcon()) == Messages.OK) {
        ApplicationManager.getApplication().invokeLater(new Runnable() {
          @Override
          public void run() {
            final String path = OrderEntryFix.locateAnnotationsJar(modulesWithoutAnnotations.iterator().next());
            if (path != null) {
              new WriteCommandAction(project) {
                @Override
                protected void run(@NotNull final Result result) throws Throwable {
                  for (Module module : modulesWithoutAnnotations) {
                    OrderEntryFix.addBundledJarToRoots(project, null, module, null, AnnotationUtil.NOT_NULL, path);
                  }
                }
              }.execute();
              restartAnalysis(project, scope);
            }
          }
        });
      }
      return;
    }
    PsiDocumentManager.getInstance(project).commitAllDocuments();
    final UsageInfo[] usageInfos = findUsages(project, scope, fileCount[0]);
    if (usageInfos == null) return;

    if (usageInfos.length < 5) {
      SwingUtilities.invokeLater(applyRunnable(project, new Computable<UsageInfo[]>() {
        @Override
        public UsageInfo[] compute() {
          return usageInfos;
        }
      }));
    }
    else {
      showUsageView(project, usageInfos, scope);
    }
  }

  private UsageInfo[] findUsages(@NotNull final Project project,
                                 @NotNull final AnalysisScope scope, 
                                          final int fileCount) {
    final NullityInferrer inferrer = new NullityInferrer(myAnnotateLocalVariablesCb.isSelected(), project);
    final PsiManager psiManager = PsiManager.getInstance(project);
    final Runnable searchForUsages = new Runnable() {
      @Override
      public void run() {
        scope.accept(new PsiElementVisitor() {
          int myFileCount = 0;

          @Override
          public void visitFile(final PsiFile file) {
            myFileCount++;
            final VirtualFile virtualFile = file.getVirtualFile();
            final FileViewProvider viewProvider = psiManager.findViewProvider(virtualFile);
            final Document document = viewProvider == null ? null : viewProvider.getDocument();
            if (document == null || virtualFile.getFileType().isBinary()) return; //do not inspect binary files
            final ProgressIndicator progressIndicator = ProgressManager.getInstance().getProgressIndicator();
            if (progressIndicator != null) {
              progressIndicator.setText2(ProjectUtil.calcRelativeToProjectPath(virtualFile, project));
              progressIndicator.setFraction(((double)myFileCount) / fileCount);
            }
            if (file instanceof PsiJavaFile) {
              inferrer.collect(file);
            }
          }
        });
      }
    };
    if (ApplicationManager.getApplication().isDispatchThread()) {
      if (!ProgressManager.getInstance().runProcessWithProgressSynchronously(searchForUsages, INFER_NULLITY_ANNOTATIONS, true, project)) {
        return null;
      }
    } else {
      searchForUsages.run();
    }

    final List<UsageInfo> usages = new ArrayList<UsageInfo>();
    inferrer.collect(usages);
    return usages.toArray(new UsageInfo[usages.size()]);
  }

  private static Runnable applyRunnable(final Project project, final Computable<UsageInfo[]> computable) {
    return new Runnable() {
      @Override
      public void run() {
        final LocalHistoryAction action = LocalHistory.getInstance().startAction(INFER_NULLITY_ANNOTATIONS);
        try {
          new WriteCommandAction(project, INFER_NULLITY_ANNOTATIONS) {
            @Override
            protected void run(@NotNull Result result) throws Throwable {
              final UsageInfo[] infos = computable.compute();
              if (infos.length > 0) {

                final Set<PsiElement> elements = new LinkedHashSet<PsiElement>();
                for (UsageInfo info : infos) {
                  final PsiElement element = info.getElement();
                  if (element != null) {
                    ContainerUtil.addIfNotNull(elements, element.getContainingFile());
                  }
                }
                if (!FileModificationService.getInstance().preparePsiElementsForWrite(elements)) return;

                final SequentialModalProgressTask progressTask = new SequentialModalProgressTask(project, INFER_NULLITY_ANNOTATIONS, false);
                progressTask.setMinIterationTime(200);
                progressTask.setTask(new AnnotateTask(project, progressTask, infos));
                ProgressManager.getInstance().run(progressTask);
              } else {
                NullityInferrer.nothingFoundMessage(project);
              }
            }
          }.execute();
        }
        finally {
          action.finish();
        }
      }
    };
  }

  private void restartAnalysis(final Project project, final AnalysisScope scope) {
    ApplicationManager.getApplication().invokeLater(new Runnable() {
      @Override
      public void run() {
        analyze(project, scope);
      }
    });
  }


  private void showUsageView(@NotNull Project project, final UsageInfo[] usageInfos, @NotNull AnalysisScope scope) {
    final UsageTarget[] targets = UsageTarget.EMPTY_ARRAY;
    final Ref<Usage[]> convertUsagesRef = new Ref<Usage[]>();
    if (!ProgressManager.getInstance().runProcessWithProgressSynchronously(new Runnable() {
      @Override
      public void run() {
        ApplicationManager.getApplication().runReadAction(new Runnable() {
          @Override
          public void run() {
            convertUsagesRef.set(UsageInfo2UsageAdapter.convert(usageInfos));
          }
        });
      }
    }, "Preprocess Usages", true, project)) return;

    if (convertUsagesRef.isNull()) return;
    final Usage[] usages = convertUsagesRef.get();

    final UsageViewPresentation presentation = new UsageViewPresentation();
    presentation.setTabText("Infer Nullity Preview");
    presentation.setShowReadOnlyStatusAsRed(true);
    presentation.setShowCancelButton(true);
    presentation.setUsagesString(RefactoringBundle.message("usageView.usagesText"));

    final UsageView usageView = UsageViewManager.getInstance(project).showUsages(targets, usages, presentation, rerunFactory(project, scope));

    final Runnable refactoringRunnable = applyRunnable(project, new Computable<UsageInfo[]>() {
      @Override
      public UsageInfo[] compute() {
        final Set<UsageInfo> infos = UsageViewUtil.getNotExcludedUsageInfos(usageView);
        return infos.toArray(new UsageInfo[infos.size()]);
      }
    });

    String canNotMakeString = "Cannot perform operation.\nThere were changes in code after usages have been found.\nPlease perform operation search again.";

    usageView.addPerformOperationAction(refactoringRunnable, INFER_NULLITY_ANNOTATIONS, canNotMakeString, INFER_NULLITY_ANNOTATIONS, false);
  }

  @NotNull
  private Factory<UsageSearcher> rerunFactory(@NotNull final Project project, @NotNull final AnalysisScope scope) {
    return new Factory<UsageSearcher>() {
      @Override
      public UsageSearcher create() {
        return new UsageInfoSearcherAdapter() {
          @Override
          protected UsageInfo[] findUsages() {
            return InferNullityAnnotationsAction.this.findUsages(project, scope, scope.getFileCount());
          }

          @Override
          public void generate(@NotNull Processor<Usage> processor) {
            processUsages(processor, project);
          }
        };
      }
    };
  }

  @Override
  protected JComponent getAdditionalActionSettings(Project project, BaseAnalysisActionDialog dialog) {
    final JPanel panel = new JPanel(new VerticalFlowLayout());
    panel.add(new TitledSeparator());
    myAnnotateLocalVariablesCb = new JCheckBox("Annotate local variables", PropertiesComponent.getInstance().getBoolean(ANNOTATE_LOCAL_VARIABLES, false));
    panel.add(myAnnotateLocalVariablesCb);
    return panel;
  }

  @Override
  protected void canceled() {
    super.canceled();
    myAnnotateLocalVariablesCb = null;
  }
}


File: plugins/testng/src/com/theoryinpractice/testng/intention/TestNGOrderEntryFix.java
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

/*
 * User: anna
 * Date: 30-Jul-2007
 */
package com.theoryinpractice.testng.intention;

import com.intellij.codeInsight.TargetElementUtil;
import com.intellij.codeInsight.daemon.impl.quickfix.OrderEntryFix;
import com.intellij.codeInsight.intention.IntentionAction;
import com.intellij.lang.java.JavaLanguage;
import com.intellij.openapi.diagnostic.Logger;
import com.intellij.openapi.editor.Editor;
import com.intellij.openapi.module.ModuleUtilCore;
import com.intellij.openapi.project.Project;
import com.intellij.openapi.roots.ProjectFileIndex;
import com.intellij.openapi.roots.ProjectRootManager;
import com.intellij.openapi.vfs.VirtualFile;
import com.intellij.psi.*;
import com.intellij.psi.util.PsiUtil;
import com.intellij.util.IncorrectOperationException;
import com.intellij.util.PathUtil;
import org.jetbrains.annotations.NonNls;
import org.jetbrains.annotations.NotNull;
import org.testng.annotations.Test;

public class TestNGOrderEntryFix implements IntentionAction {
  private static final Logger LOG = Logger.getInstance("#" + TestNGOrderEntryFix.class.getName());

  @NotNull
  public String getText() {
    return "Add testng.jar to classpath";
  }

  @NotNull
  public String getFamilyName() {
    return getText();
  }

  public boolean isAvailable(@NotNull final Project project, final Editor editor, final PsiFile file) {
    if (!(file instanceof PsiJavaFile)) return false;
    if (!file.getLanguage().isKindOf(JavaLanguage.INSTANCE)) return false;

    final PsiReference reference = TargetElementUtil.findReference(editor);
    if (!(reference instanceof PsiJavaCodeReferenceElement)) return false;
    if (reference.resolve() != null) return false;
    @NonNls final String referenceName = ((PsiJavaCodeReferenceElement)reference).getReferenceName();
    if (referenceName == null) return false;
    final ProjectFileIndex fileIndex = ProjectRootManager.getInstance(project).getFileIndex();
    final VirtualFile virtualFile = file.getVirtualFile();
    if (virtualFile == null) return false;
    if (fileIndex.getModuleForFile(virtualFile) == null) return false;
    if (!(((PsiJavaCodeReferenceElement)reference).getParent() instanceof PsiAnnotation &&
          PsiUtil.isLanguageLevel5OrHigher(((PsiJavaCodeReferenceElement)reference)))) return false;
    if (!isTestNGAnnotationName(referenceName)) return false;
    return true;
  }

  public void invoke(@NotNull final Project project, final Editor editor, final PsiFile file) throws IncorrectOperationException {
    final PsiJavaCodeReferenceElement reference = (PsiJavaCodeReferenceElement)TargetElementUtil.findReference(editor);
    LOG.assertTrue(reference != null);
    String jarPath = PathUtil.getJarPathForClass(Test.class);
    final VirtualFile virtualFile = file.getVirtualFile();
    LOG.assertTrue(virtualFile != null);
    OrderEntryFix.addBundledJarToRoots(project, editor, ModuleUtilCore.findModuleForFile(virtualFile, project), reference,
                                       "org.testng.annotations." + reference.getReferenceName(), jarPath);
  }

  public boolean startInWriteAction() {
    return true;
  }

  private static boolean isTestNGAnnotationName(@NonNls final String referenceName) {
    return "Test".equals(referenceName) ||
           "BeforeClass".equals(referenceName) ||
           "BeforeGroups".equals(referenceName) ||
           "BeforeMethod".equals(referenceName) ||
           "BeforeSuite".equals(referenceName) ||
           "BeforeTest".equals(referenceName) ||
           "AfterClass".equals(referenceName) ||
           "AfterGroups".equals(referenceName) ||
           "AfterMethod".equals(referenceName) ||
           "AfterSuite".equals(referenceName) ||
           "AfterTest".equals(referenceName) ||
           "Configuration".equals(referenceName);

  }
}