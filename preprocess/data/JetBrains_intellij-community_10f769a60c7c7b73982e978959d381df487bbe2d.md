Refactoring Types: ['Move Method', 'Extract Method']
aemon/impl/quickfix/OrderEntryFix.java
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
import com.intellij.packageDependencies.DependencyValidationManager;
import com.intellij.pom.java.LanguageLevel;
import com.intellij.psi.*;
import com.intellij.psi.search.GlobalSearchScope;
import com.intellij.psi.search.PsiShortNamesCache;
import com.intellij.psi.util.PsiTreeUtil;
import com.intellij.psi.util.PsiUtil;
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
  private static final String JUNIT4_LIBRARY_NAME = "JUnit4";

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
          List<String> jarPaths;
          String libraryName;
          if (isJunit4) {
            jarPaths = getJUnit4JarPaths();
            libraryName = JUNIT4_LIBRARY_NAME;
          }
          else {
            jarPaths = Collections.singletonList(JavaSdkUtil.getJunit3JarPath());
            libraryName = null;
          }
          addJarsToRootsAndImportClass(jarPaths, libraryName, currentModule, editor, reference, className);
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
                    addJarsToRootsAndImportClass(Collections.singletonList(libraryPath), null, currentModule, editor, reference,
                                                 "org.jetbrains.annotations." + referenceName);
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
    final List<String> junit4Paths = getJUnit4JarPaths();
    addJarsToRoots(junit4Paths, JUNIT4_LIBRARY_NAME, currentModule, null);
  }

  @NotNull
  private static List<String> getJUnit4JarPaths() {
    try {
      return Arrays.asList(JavaSdkUtil.getJunit4JarPath(),
                           PathUtil.getJarPathForClass(Class.forName("org.hamcrest.Matcher")),
                           PathUtil.getJarPathForClass(Class.forName("org.hamcrest.Matchers")));
    }
    catch (ClassNotFoundException e) {
      throw new RuntimeException(e);
    }
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

  /**
   * @deprecated use {@link #addJarsToRootsAndImportClass} instead
   */
  public static void addBundledJarToRoots(final Project project, @Nullable final Editor editor, final Module currentModule,
                                          @Nullable final PsiReference reference,
                                          @NonNls final String className,
                                          @NonNls final String libVirtFile) {
    addJarsToRootsAndImportClass(Collections.singletonList(libVirtFile), null, currentModule, editor, reference, className);
  }

  public static void addJarsToRootsAndImportClass(@NotNull List<String> jarPaths,
                                                  final String libraryName,
                                                  @NotNull final Module currentModule, @Nullable final Editor editor,
                                                  @Nullable final PsiReference reference,
                                                  @NonNls final String className) {
    addJarsToRoots(jarPaths, libraryName, currentModule, reference != null ? reference.getElement() : null);

    final Project project = currentModule.getProject();
    if (editor != null && reference != null && className != null) {
      DumbService.getInstance(project).withAlternativeResolveEnabled(new Runnable() {
        @Override
        public void run() {
          GlobalSearchScope scope = GlobalSearchScope.moduleWithLibrariesScope(currentModule);
          PsiClass aClass = JavaPsiFacade.getInstance(project).findClass(className, scope);
          if (aClass != null) {
            new AddImportAction(project, reference, editor, aClass).execute();
          }
        }
      });
    }
  }

  public static void addJarToRoots(@NotNull String jarPath, final @NotNull Module module, @Nullable PsiElement location) {
    addJarsToRoots(Collections.singletonList(jarPath), null, module, location);
  }

  public static void addJarsToRoots(@NotNull List<String> jarPaths, @Nullable String libraryName,
                                    @NotNull Module module, @Nullable PsiElement location) {
    List<String> urls = ContainerUtil.map(jarPaths, new Function<String, String>() {
      @Override
      public String fun(String path) {
        return refreshAndConvertToUrl(path);
      }
    });
    boolean inTests = false;
    if (location != null) {
      final VirtualFile vFile = location.getContainingFile().getVirtualFile();
      if (vFile != null && ModuleRootManager.getInstance(module).getFileIndex().isInTestSourceContent(vFile)) {
        inTests = true;
      }
    }
    ModuleRootModificationUtil.addModuleLibrary(module, libraryName, urls, Collections.<String>emptyList(),
                                                inTests ? DependencyScope.TEST : DependencyScope.COMPILE);
  }

  @NotNull
  private static String refreshAndConvertToUrl(String jarPath) {
    final File libraryRoot = new File(jarPath);
    LocalFileSystem.getInstance().refreshAndFindFileByIoFile(libraryRoot);
    return VfsUtil.getUrlForLibraryRoot(libraryRoot);
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


File: java/java-impl/src/com/intellij/openapi/projectRoots/ex/JavaSdkUtil.java
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
package com.intellij.openapi.projectRoots.ex;

import com.intellij.rt.compiler.JavacRunner;
import com.intellij.util.PathUtil;
import com.intellij.util.PathsList;
import org.jetbrains.annotations.NonNls;

public class JavaSdkUtil {
  @NonNls public static final String IDEA_PREPEND_RTJAR = "idea.prepend.rtjar";

  public static void addRtJar(PathsList pathsList) {
    final String ideaRtJarPath = getIdeaRtJarPath();
    if (Boolean.getBoolean(IDEA_PREPEND_RTJAR)) {
      pathsList.addFirst(ideaRtJarPath);
    }
    else {
      pathsList.addTail(ideaRtJarPath);
    }
  }


  public static String getJunit4JarPath() {
    try {
      return PathUtil.getJarPathForClass(Class.forName("org.junit.Test"));
    }
    catch (ClassNotFoundException e) {
      throw new RuntimeException(e);
    }
  }

  public static String getJunit3JarPath() {
    try {
      return PathUtil.getJarPathForClass(Class.forName("junit.runner.TestSuiteLoader")); //junit3 specific class
    }
    catch (ClassNotFoundException e) {
      throw new RuntimeException(e);
    }
  }

  public static String getIdeaRtJarPath() {
    return PathUtil.getJarPathForClass(JavacRunner.class);
  }
}


File: java/java-impl/src/com/intellij/testIntegration/JavaTestFramework.java
/*
 * Copyright 2000-2011 JetBrains s.r.o.
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
package com.intellij.testIntegration;

import com.intellij.codeInsight.daemon.impl.quickfix.OrderEntryFix;
import com.intellij.ide.fileTemplates.FileTemplate;
import com.intellij.ide.fileTemplates.FileTemplateDescriptor;
import com.intellij.ide.fileTemplates.FileTemplateManager;
import com.intellij.lang.Language;
import com.intellij.lang.java.JavaLanguage;
import com.intellij.openapi.module.Module;
import com.intellij.openapi.roots.ProjectRootManager;
import com.intellij.openapi.util.text.StringUtil;
import com.intellij.openapi.vfs.VirtualFile;
import com.intellij.psi.*;
import com.intellij.psi.search.GlobalSearchScope;
import com.intellij.util.IncorrectOperationException;
import org.jetbrains.annotations.NotNull;
import org.jetbrains.annotations.Nullable;

public abstract class JavaTestFramework implements TestFramework {
  public boolean isLibraryAttached(@NotNull Module module) {
    GlobalSearchScope scope = GlobalSearchScope.moduleWithDependenciesAndLibrariesScope(module);
    PsiClass c = JavaPsiFacade.getInstance(module.getProject()).findClass(getMarkerClassFQName(), scope);
    return c != null;
  }

  protected abstract String getMarkerClassFQName();

  public boolean isTestClass(@NotNull PsiElement clazz) {
    return clazz instanceof PsiClass && isTestClass((PsiClass)clazz, false);
  }

  @Override
  public boolean isPotentialTestClass(@NotNull PsiElement clazz) {
    return clazz instanceof PsiClass && isTestClass((PsiClass)clazz, true);
  }

  protected abstract boolean isTestClass(PsiClass clazz, boolean canBePotential);

  protected boolean isUnderTestSources(PsiClass clazz) {
    PsiFile psiFile = clazz.getContainingFile();
    VirtualFile vFile = psiFile.getVirtualFile();
    if (vFile == null) return false;
    return ProjectRootManager.getInstance(clazz.getProject()).getFileIndex().isInTestSourceContent(vFile);
  }

  @Override
  @Nullable
  public PsiElement findSetUpMethod(@NotNull PsiElement clazz) {
    return clazz instanceof PsiClass ? findSetUpMethod((PsiClass)clazz) : null;
  }

  @Nullable
  protected abstract PsiMethod findSetUpMethod(@NotNull PsiClass clazz);

  @Override
  @Nullable
  public PsiElement findTearDownMethod(@NotNull PsiElement clazz) {
    return clazz instanceof PsiClass ? findTearDownMethod((PsiClass)clazz) : null;
  }

  @Nullable
  protected abstract PsiMethod findTearDownMethod(@NotNull PsiClass clazz);

  @Override
  public PsiElement findOrCreateSetUpMethod(@NotNull PsiElement clazz) throws IncorrectOperationException {
    return clazz instanceof PsiClass ? findOrCreateSetUpMethod((PsiClass)clazz) : null;
  }

  @Override
  public boolean isIgnoredMethod(PsiElement element) {
    return false;
  }

  @Override
  @NotNull
  public Language getLanguage() {
    return JavaLanguage.INSTANCE;
  }

  @Nullable
  protected abstract PsiMethod findOrCreateSetUpMethod(PsiClass clazz) throws IncorrectOperationException;
  
  public boolean isParameterized(PsiClass clazz) {
    return false;
  }

  @Nullable
  public PsiMethod findParametersMethod(PsiClass clazz) {
    return null;
  }

  @Nullable
  public FileTemplateDescriptor getParametersMethodFileTemplateDescriptor() {
    return null;
  }
  
  public abstract char getMnemonic();

  public PsiMethod createSetUpPatternMethod(JVMElementFactory factory) {
    final FileTemplate template = FileTemplateManager.getDefaultInstance().getCodeTemplate(getSetUpMethodFileTemplateDescriptor().getFileName());
    final String templateText = StringUtil.replace(StringUtil.replace(template.getText(), "${BODY}\n", ""), "${NAME}", "setUp");
    return factory.createMethodFromText(templateText, null);
  }

  public FileTemplateDescriptor getTestClassFileTemplateDescriptor() {
    return null;
  }
  
  public void setupLibrary(Module module) {
    OrderEntryFix.addJarToRoots(getLibraryPath(), module, null);
  }

  public boolean isSingleConfig() {
    return false;
  }
}


File: java/java-impl/src/com/intellij/testIntegration/createTest/CreateTestDialog.java
/*
 * Copyright 2000-2011 JetBrains s.r.o.
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
package com.intellij.testIntegration.createTest;

import com.intellij.CommonBundle;
import com.intellij.codeInsight.CodeInsightBundle;
import com.intellij.codeInsight.daemon.impl.quickfix.OrderEntryFix;
import com.intellij.icons.AllIcons;
import com.intellij.ide.util.PackageUtil;
import com.intellij.ide.util.PropertiesComponent;
import com.intellij.ide.util.TreeClassChooser;
import com.intellij.ide.util.TreeClassChooserFactory;
import com.intellij.openapi.actionSystem.AnAction;
import com.intellij.openapi.actionSystem.AnActionEvent;
import com.intellij.openapi.actionSystem.CustomShortcutSet;
import com.intellij.openapi.application.ApplicationManager;
import com.intellij.openapi.application.ReadAction;
import com.intellij.openapi.application.Result;
import com.intellij.openapi.command.WriteCommandAction;
import com.intellij.openapi.editor.event.DocumentAdapter;
import com.intellij.openapi.editor.event.DocumentEvent;
import com.intellij.openapi.extensions.Extensions;
import com.intellij.openapi.help.HelpManager;
import com.intellij.openapi.module.Module;
import com.intellij.openapi.project.Project;
import com.intellij.openapi.roots.ModuleRootManager;
import com.intellij.openapi.ui.ComboBox;
import com.intellij.openapi.ui.DialogWrapper;
import com.intellij.openapi.ui.Messages;
import com.intellij.openapi.util.Comparing;
import com.intellij.openapi.util.text.StringUtil;
import com.intellij.openapi.vfs.VirtualFile;
import com.intellij.psi.*;
import com.intellij.refactoring.PackageWrapper;
import com.intellij.refactoring.move.moveClassesOrPackages.MoveClassesOrPackagesUtil;
import com.intellij.refactoring.ui.MemberSelectionTable;
import com.intellij.refactoring.ui.PackageNameReferenceEditorCombo;
import com.intellij.refactoring.util.RefactoringMessageUtil;
import com.intellij.refactoring.util.RefactoringUtil;
import com.intellij.refactoring.util.classMembers.MemberInfo;
import com.intellij.testIntegration.JavaTestFramework;
import com.intellij.testIntegration.TestFramework;
import com.intellij.testIntegration.TestIntegrationUtils;
import com.intellij.ui.*;
import com.intellij.util.IncorrectOperationException;
import org.jetbrains.annotations.NotNull;
import org.jetbrains.annotations.Nullable;
import org.jetbrains.jps.model.java.JavaModuleSourceRootTypes;
import org.jetbrains.jps.model.java.JavaSourceRootType;

import javax.swing.*;
import java.awt.*;
import java.awt.event.ActionEvent;
import java.awt.event.ActionListener;
import java.awt.event.InputEvent;
import java.awt.event.KeyEvent;
import java.util.*;
import java.util.List;

public class CreateTestDialog extends DialogWrapper {
  private static final String RECENTS_KEY = "CreateTestDialog.RecentsKey";
  private static final String RECENT_SUPERS_KEY = "CreateTestDialog.Recents.Supers";
  private static final String DEFAULT_LIBRARY_NAME_PROPERTY = CreateTestDialog.class.getName() + ".defaultLibrary";
  private static final String SHOW_INHERITED_MEMBERS_PROPERTY = CreateTestDialog.class.getName() + ".includeInheritedMembers";

  private final Project myProject;
  private final PsiClass myTargetClass;
  private final PsiPackage myTargetPackage;
  private final Module myTargetModule;

  private PsiDirectory myTargetDirectory;
  private TestFramework mySelectedFramework;

  private final ComboBox myLibrariesCombo = new ComboBox(new DefaultComboBoxModel());
  private EditorTextField myTargetClassNameField;
  private ReferenceEditorComboWithBrowseButton mySuperClassField;
  private ReferenceEditorComboWithBrowseButton myTargetPackageField;
  private JCheckBox myGenerateBeforeBox = new JCheckBox(CodeInsightBundle.message("intention.create.test.dialog.setUp"));
  private JCheckBox myGenerateAfterBox = new JCheckBox(CodeInsightBundle.message("intention.create.test.dialog.tearDown"));
  private JCheckBox myShowInheritedMethodsBox = new JCheckBox(CodeInsightBundle.message("intention.create.test.dialog.show.inherited"));
  private MemberSelectionTable myMethodsTable = new MemberSelectionTable(Collections.<MemberInfo>emptyList(), null);
  private JButton myFixLibraryButton = new JButton(CodeInsightBundle.message("intention.create.test.dialog.fix.library"));
  private JPanel myFixLibraryPanel;
  private JLabel myFixLibraryLabel;

  public CreateTestDialog(@NotNull Project project,
                          @NotNull String title,
                          PsiClass targetClass,
                          PsiPackage targetPackage,
                          Module targetModule) {
    super(project, true);
    myProject = project;

    myTargetClass = targetClass;
    myTargetPackage = targetPackage;
    myTargetModule = targetModule;

    setTitle(title);
    init();
  }

  protected String suggestTestClassName(PsiClass targetClass) {
    return targetClass.getName() + "Test";
  }

  private boolean isSuperclassSelectedManually() {
    String superClass = mySuperClassField.getText();
    if (StringUtil.isEmptyOrSpaces(superClass)) {
      return false;
    }

    for (TestFramework framework : TestFramework.EXTENSION_NAME.getExtensions()) {
      if (superClass.equals(framework.getDefaultSuperClass())) {
        return false;
      }
    }

    return true;
  }

  private void onLibrarySelected(TestFramework descriptor) {
    if (descriptor.isLibraryAttached(myTargetModule)) {
      myFixLibraryPanel.setVisible(false);
    }
    else {
      myFixLibraryPanel.setVisible(true);
      String text = CodeInsightBundle.message("intention.create.test.dialog.library.not.found", descriptor.getName());
      myFixLibraryLabel.setText(text);

      myFixLibraryButton.setVisible(descriptor.getLibraryPath() != null);
    }

    String superClass = descriptor.getDefaultSuperClass();

    if (isSuperclassSelectedManually()) {
      if (superClass != null) {
        String currentSuperClass = mySuperClassField.getText();
        mySuperClassField.appendItem(superClass);
        mySuperClassField.setText(currentSuperClass);
      }
    }
    else {
      mySuperClassField.appendItem(StringUtil.notNullize(superClass));
      mySuperClassField.getChildComponent().setSelectedItem(StringUtil.notNullize(superClass));
    }

    mySelectedFramework = descriptor;
  }

  private void updateMethodsTable() {
    List<MemberInfo> methods = TestIntegrationUtils.extractClassMethods(
      myTargetClass, myShowInheritedMethodsBox.isSelected());

    Set<PsiMember> selectedMethods = new HashSet<PsiMember>();
    for (MemberInfo each : myMethodsTable.getSelectedMemberInfos()) {
      selectedMethods.add(each.getMember());
    }
    for (MemberInfo each : methods) {
      each.setChecked(selectedMethods.contains(each.getMember()));
    }

    myMethodsTable.setMemberInfos(methods);
  }

  private String getDefaultLibraryName() {
    return getProperties().getValue(DEFAULT_LIBRARY_NAME_PROPERTY);
  }

  private void saveDefaultLibraryName() {
    getProperties().setValue(DEFAULT_LIBRARY_NAME_PROPERTY, mySelectedFramework.getName());
  }

  private void restoreShowInheritedMembersStatus() {
    String v = getProperties().getValue(SHOW_INHERITED_MEMBERS_PROPERTY);
    myShowInheritedMethodsBox.setSelected(v != null && v.equals("true"));
  }

  private void saveShowInheritedMembersStatus() {
    boolean v = myShowInheritedMethodsBox.isSelected();
    getProperties().setValue(SHOW_INHERITED_MEMBERS_PROPERTY, Boolean.toString(v));
  }

  private PropertiesComponent getProperties() {
    return PropertiesComponent.getInstance(myProject);
  }

  @Override
  protected String getDimensionServiceKey() {
    return getClass().getName();
  }

  @NotNull
  protected Action[] createActions() {
    return new Action[]{getOKAction(), getCancelAction(), getHelpAction()};
  }

  public JComponent getPreferredFocusedComponent() {
    return myTargetClassNameField;
  }

  protected JComponent createCenterPanel() {
    JPanel panel = new JPanel(new GridBagLayout());

    GridBagConstraints constr = new GridBagConstraints();

    constr.fill = GridBagConstraints.HORIZONTAL;
    constr.anchor = GridBagConstraints.WEST;
    
    int gridy = 1;
    
    constr.insets = insets(4);
    constr.gridy = gridy++;
    constr.gridx = 0;
    constr.weightx = 0;
    final JLabel libLabel = new JLabel(CodeInsightBundle.message("intention.create.test.dialog.testing.library"));
    libLabel.setLabelFor(myLibrariesCombo);
    panel.add(libLabel, constr);

    constr.gridx = 1;
    constr.weightx = 1;
    constr.gridwidth = GridBagConstraints.REMAINDER;
    panel.add(myLibrariesCombo, constr);

    myFixLibraryPanel = new JPanel(new BorderLayout());
    myFixLibraryLabel = new JLabel();
    myFixLibraryLabel.setIcon(AllIcons.Actions.IntentionBulb);
    myFixLibraryPanel.add(myFixLibraryLabel, BorderLayout.CENTER);
    myFixLibraryPanel.add(myFixLibraryButton, BorderLayout.EAST);

    constr.insets = insets(1);
    constr.gridy = gridy++;
    constr.gridx = 0;
    panel.add(myFixLibraryPanel, constr);

    constr.gridheight = 1;

    constr.insets = insets(6);
    constr.gridy = gridy++;
    constr.gridx = 0;
    constr.weightx = 0;
    constr.gridwidth = 1;
    panel.add(new JLabel(CodeInsightBundle.message("intention.create.test.dialog.class.name")), constr);

    myTargetClassNameField = new EditorTextField(suggestTestClassName(myTargetClass));
    myTargetClassNameField.getDocument().addDocumentListener(new DocumentAdapter() {
      @Override
      public void documentChanged(DocumentEvent e) {
        getOKAction().setEnabled(PsiNameHelper.getInstance(myProject).isIdentifier(getClassName()));
      }
    });

    constr.gridx = 1;
    constr.weightx = 1;
    panel.add(myTargetClassNameField, constr);

    constr.insets = insets(1);
    constr.gridy = gridy++;
    constr.gridx = 0;
    constr.weightx = 0;
    panel.add(new JLabel(CodeInsightBundle.message("intention.create.test.dialog.super.class")), constr);

    mySuperClassField = new ReferenceEditorComboWithBrowseButton(new MyChooseSuperClassAction(), null, myProject, true,
                                                                 JavaCodeFragment.VisibilityChecker.EVERYTHING_VISIBLE, RECENT_SUPERS_KEY);
    mySuperClassField.setMinimumSize(mySuperClassField.getPreferredSize());
    constr.gridx = 1;
    constr.weightx = 1;
    panel.add(mySuperClassField, constr);

    constr.insets = insets(1);
    constr.gridy = gridy++;
    constr.gridx = 0;
    constr.weightx = 0;
    panel.add(new JLabel(CodeInsightBundle.message("dialog.create.class.destination.package.label")), constr);

    constr.gridx = 1;
    constr.weightx = 1;


    String targetPackageName = myTargetPackage != null ? myTargetPackage.getQualifiedName() : "";
    myTargetPackageField = new PackageNameReferenceEditorCombo(targetPackageName, myProject, RECENTS_KEY, CodeInsightBundle.message("dialog.create.class.package.chooser.title"));

    new AnAction() {
      public void actionPerformed(AnActionEvent e) {
        myTargetPackageField.getButton().doClick();
      }
    }.registerCustomShortcutSet(new CustomShortcutSet(KeyStroke.getKeyStroke(KeyEvent.VK_ENTER, InputEvent.SHIFT_DOWN_MASK)),
                                myTargetPackageField.getChildComponent());
    JPanel targetPackagePanel = new JPanel(new BorderLayout());
    targetPackagePanel.add(myTargetPackageField, BorderLayout.CENTER);
    panel.add(targetPackagePanel, constr);

    constr.insets = insets(6);
    constr.gridy = gridy++;
    constr.gridx = 0;
    constr.weightx = 0;
    panel.add(new JLabel(CodeInsightBundle.message("intention.create.test.dialog.generate")), constr);

    constr.gridx = 1;
    constr.weightx = 1;
    panel.add(myGenerateBeforeBox, constr);

    constr.insets = insets(1);
    constr.gridy = gridy++;
    panel.add(myGenerateAfterBox, constr);

    constr.insets = insets(6);
    constr.gridy = gridy++;
    constr.gridx = 0;
    constr.weightx = 0;
    final JLabel membersLabel = new JLabel(CodeInsightBundle.message("intention.create.test.dialog.select.methods"));
    membersLabel.setLabelFor(myMethodsTable);
    panel.add(membersLabel, constr);

    constr.gridx = 1;
    constr.weightx = 1;
    panel.add(myShowInheritedMethodsBox, constr);

    constr.insets = insets(1, 8);
    constr.gridy = gridy++;
    constr.gridx = 0;
    constr.gridwidth = GridBagConstraints.REMAINDER;
    constr.fill = GridBagConstraints.BOTH;
    constr.weighty = 1;
    panel.add(ScrollPaneFactory.createScrollPane(myMethodsTable), constr);

    myLibrariesCombo.setRenderer(new ListCellRendererWrapper<TestFramework>() {
      @Override
      public void customize(JList list, TestFramework value, int index, boolean selected, boolean hasFocus) {
        if (value != null) {
          setText(value.getName());
        }
      }
    });
    final List<TestFramework> attachedLibraries = new ArrayList<TestFramework>();
    final String defaultLibrary = getDefaultLibraryName();
    TestFramework defaultDescriptor = null;
    final DefaultComboBoxModel model = (DefaultComboBoxModel)myLibrariesCombo.getModel();
    for (final TestFramework descriptor : Extensions.getExtensions(TestFramework.EXTENSION_NAME)) {
      model.addElement(descriptor);
      if (descriptor.isLibraryAttached(myTargetModule)) {
        attachedLibraries.add(descriptor);
      }

      if (Comparing.equal(defaultLibrary, descriptor.getName())) {
        defaultDescriptor = descriptor;
      }
    }

    myLibrariesCombo.addActionListener(new ActionListener() {
      public void actionPerformed(ActionEvent e) {
        final Object selectedItem = myLibrariesCombo.getSelectedItem();
        if (selectedItem != null) {
          onLibrarySelected((TestFramework)selectedItem);
        }
      }
    });

    if (defaultDescriptor != null && (attachedLibraries.contains(defaultDescriptor) || attachedLibraries.isEmpty())) {
      myLibrariesCombo.setSelectedItem(defaultDescriptor);
    }
    else {
      myLibrariesCombo.setSelectedIndex(0);
    }

    myFixLibraryButton.addActionListener(new ActionListener() {
      public void actionPerformed(ActionEvent e) {
        ApplicationManager.getApplication().runWriteAction(new Runnable() {
          public void run() {
            if (mySelectedFramework instanceof JavaTestFramework) {
              ((JavaTestFramework)mySelectedFramework).setupLibrary(myTargetModule);
            } else {
              OrderEntryFix.addJarToRoots(mySelectedFramework.getLibraryPath(), myTargetModule, null);
            }
          }
        });
        myFixLibraryPanel.setVisible(false);
      }
    });



    myShowInheritedMethodsBox.addActionListener(new ActionListener() {
      public void actionPerformed(ActionEvent e) {
        updateMethodsTable();
      }
    });
    restoreShowInheritedMembersStatus();
    updateMethodsTable();
    return panel;
  }

  private static Insets insets(int top) {
    return insets(top, 0);
  }

  private static Insets insets(int top, int bottom) {
    return new Insets(top, 8, bottom, 8);
  }

  public String getClassName() {
    return myTargetClassNameField.getText();
  }

  public PsiClass getTargetClass() {
    return myTargetClass;
  }

  @Nullable
  public String getSuperClassName() {
    String result = mySuperClassField.getText().trim();
    if (result.length() == 0) return null;
    return result;
  }

  public PsiDirectory getTargetDirectory() {
    return myTargetDirectory;
  }

  public Collection<MemberInfo> getSelectedMethods() {
    return myMethodsTable.getSelectedMemberInfos();
  }

  public boolean shouldGeneratedAfter() {
    return myGenerateAfterBox.isSelected();
  }

  public boolean shouldGeneratedBefore() {
    return myGenerateBeforeBox.isSelected();
  }

  public TestFramework getSelectedTestFrameworkDescriptor() {
    return mySelectedFramework;
  }

  protected void doOKAction() {
    RecentsManager.getInstance(myProject).registerRecentEntry(RECENTS_KEY, myTargetPackageField.getText());
    RecentsManager.getInstance(myProject).registerRecentEntry(RECENT_SUPERS_KEY, mySuperClassField.getText());

    String errorMessage;
    try {
      myTargetDirectory = selectTargetDirectory();
      if (myTargetDirectory == null) return;
      errorMessage = RefactoringMessageUtil.checkCanCreateClass(myTargetDirectory, getClassName());
    }
    catch (IncorrectOperationException e) {
      errorMessage = e.getMessage();
    }

    if (errorMessage != null) {
      final int result = Messages
        .showOkCancelDialog(myProject, errorMessage + ". Update existing class?", CommonBundle.getErrorTitle(), Messages.getErrorIcon());
      if (result == Messages.CANCEL) {
        super.close(CANCEL_EXIT_CODE);
        return;
      }
    }

    saveDefaultLibraryName();
    saveShowInheritedMembersStatus();
    super.doOKAction();
  }

  @Nullable
  private PsiDirectory selectTargetDirectory() throws IncorrectOperationException {
    final String packageName = getPackageName();
    final PackageWrapper targetPackage = new PackageWrapper(PsiManager.getInstance(myProject), packageName);

    final VirtualFile selectedRoot = new ReadAction<VirtualFile>() {
      protected void run(Result<VirtualFile> result) throws Throwable {
        final HashSet<VirtualFile> testFolders = new HashSet<VirtualFile>();
        CreateTestAction.checkForTestRoots(myTargetModule, testFolders);
        List<VirtualFile> roots;
        if (testFolders.isEmpty()) {
          roots = ModuleRootManager.getInstance(myTargetModule).getSourceRoots(JavaModuleSourceRootTypes.SOURCES);
          if (roots.isEmpty()) return;
        } else {
          roots = new ArrayList<VirtualFile>(testFolders);
        }

        if (roots.size() == 1) {
          result.setResult(roots.get(0));
        }
        else {
          PsiDirectory defaultDir = chooseDefaultDirectory(packageName);
          result.setResult(MoveClassesOrPackagesUtil.chooseSourceRoot(targetPackage, roots, defaultDir));
        }
      }
    }.execute().getResultObject();

    if (selectedRoot == null) return null;

    return new WriteCommandAction<PsiDirectory>(myProject, CodeInsightBundle.message("create.directory.command")) {
      protected void run(Result<PsiDirectory> result) throws Throwable {
        result.setResult(RefactoringUtil.createPackageDirectoryInSourceRoot(targetPackage, selectedRoot));
      }
    }.execute().getResultObject();
  }

  @Nullable
  private PsiDirectory chooseDefaultDirectory(String packageName) {
    List<PsiDirectory> dirs = new ArrayList<PsiDirectory>();
    for (VirtualFile file : ModuleRootManager.getInstance(myTargetModule).getSourceRoots(JavaSourceRootType.TEST_SOURCE)) {
      final PsiDirectory dir = PsiManager.getInstance(myProject).findDirectory(file);
      if (dir != null) {
        dirs.add(dir);
      }
    }
    if (!dirs.isEmpty()) {
      for (PsiDirectory dir : dirs) {
        final String dirName = dir.getVirtualFile().getPath();
        if (dirName.contains("generated")) continue;
        return dir;
      }
      return dirs.get(0);
    }
    return PackageUtil.findPossiblePackageDirectoryInModule(myTargetModule, packageName);
  }

  private String getPackageName() {
    String name = myTargetPackageField.getText();
    return name != null ? name.trim() : "";
  }

  @Override
  protected void doHelpAction() {
    HelpManager.getInstance().invokeHelp("reference.dialogs.createTest");
  }

  private class MyChooseSuperClassAction implements ActionListener {
    public void actionPerformed(ActionEvent e) {
      TreeClassChooserFactory f = TreeClassChooserFactory.getInstance(myProject);
      TreeClassChooser dialog =
        f.createAllProjectScopeChooser(CodeInsightBundle.message("intention.create.test.dialog.choose.super.class"));
      dialog.showDialog();
      PsiClass aClass = dialog.getSelected();
      if (aClass != null) {
        String superClass = aClass.getQualifiedName();

        mySuperClassField.appendItem(superClass);
        mySuperClassField.getChildComponent().setSelectedItem(superClass);
      }
    }
  }
}


File: plugins/junit/src/com/intellij/execution/junit/JUnit4Framework.java
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
package com.intellij.execution.junit;

import com.intellij.CommonBundle;
import com.intellij.codeInsight.AnnotationUtil;
import com.intellij.codeInsight.daemon.impl.quickfix.OrderEntryFix;
import com.intellij.codeInsight.intention.AddAnnotationFix;
import com.intellij.icons.AllIcons;
import com.intellij.ide.fileTemplates.FileTemplateDescriptor;
import com.intellij.openapi.application.ApplicationManager;
import com.intellij.openapi.diagnostic.Logger;
import com.intellij.openapi.module.Module;
import com.intellij.openapi.projectRoots.ex.JavaSdkUtil;
import com.intellij.openapi.ui.Messages;
import com.intellij.psi.*;
import com.intellij.psi.codeStyle.JavaCodeStyleManager;
import com.intellij.psi.util.PsiUtil;
import com.intellij.testIntegration.JavaTestFramework;
import com.intellij.util.IncorrectOperationException;
import org.jetbrains.annotations.NotNull;
import org.jetbrains.annotations.Nullable;

import javax.swing.*;

public class JUnit4Framework extends JavaTestFramework {
  private static final Logger LOG = Logger.getInstance("#" + JUnit4Framework.class.getName());

  @NotNull
  public String getName() {
    return "JUnit4";
  }

  @NotNull
  @Override
  public Icon getIcon() {
    return AllIcons.RunConfigurations.Junit;
  }

  protected String getMarkerClassFQName() {
    return JUnitUtil.TEST_ANNOTATION;
  }

  @NotNull
  public String getLibraryPath() {
    return JavaSdkUtil.getJunit4JarPath();
  }

  @Nullable
  public String getDefaultSuperClass() {
    return null;
  }

  public boolean isTestClass(PsiClass clazz, boolean canBePotential) {
    if (canBePotential) return isUnderTestSources(clazz);
    return JUnitUtil.isJUnit4TestClass(clazz);
  }

  @Nullable
  @Override
  protected PsiMethod findSetUpMethod(@NotNull PsiClass clazz) {
    for (PsiMethod each : clazz.getMethods()) {
      if (AnnotationUtil.isAnnotated(each, JUnitUtil.BEFORE_ANNOTATION_NAME, false)) return each;
    }
    return null;
  }

  @Nullable
  @Override
  protected PsiMethod findTearDownMethod(@NotNull PsiClass clazz) {
    for (PsiMethod each : clazz.getMethods()) {
      if (AnnotationUtil.isAnnotated(each, JUnitUtil.AFTER_ANNOTATION_NAME, false)) return each;
    }
    return null;
  }

  @Override
  @Nullable
  protected PsiMethod findOrCreateSetUpMethod(PsiClass clazz) throws IncorrectOperationException {
    PsiMethod method = findSetUpMethod(clazz);
    if (method != null) return method;

    PsiManager manager = clazz.getManager();
    PsiElementFactory factory = JavaPsiFacade.getInstance(manager.getProject()).getElementFactory();

    method = createSetUpPatternMethod(factory);
    PsiMethod existingMethod = clazz.findMethodBySignature(method, false);
    if (existingMethod != null) {
      int exit = ApplicationManager.getApplication().isUnitTestMode() ?
                 Messages.OK :
                       Messages.showOkCancelDialog("Method setUp already exist but is not annotated as @Before. Annotate?",
                                                   CommonBundle.getWarningTitle(),
                                                   Messages.getWarningIcon());
      if (exit == Messages.OK) {
        new AddAnnotationFix(JUnitUtil.BEFORE_ANNOTATION_NAME, existingMethod).invoke(existingMethod.getProject(), null, existingMethod.getContainingFile());
        return existingMethod;
      }
    }
    final PsiMethod testMethod = JUnitUtil.findFirstTestMethod(clazz);
    if (testMethod != null) {
      method = (PsiMethod)clazz.addBefore(method, testMethod);
    } else {
      method = (PsiMethod)clazz.add(method);
    }
    JavaCodeStyleManager.getInstance(manager.getProject()).shortenClassReferences(method);

    return method;
  }

  @Override
  public boolean isIgnoredMethod(PsiElement element) {
    final PsiMethod testMethod = element instanceof PsiMethod ? JUnitUtil.getTestMethod(element) : null;
    return testMethod != null && AnnotationUtil.isAnnotated(testMethod, JUnitUtil.IGNORE_ANNOTATION, false);
  }

  @Override
  public boolean isTestMethod(PsiElement element) {
    return element instanceof PsiMethod && JUnitUtil.getTestMethod(element) != null;
  }

  public FileTemplateDescriptor getSetUpMethodFileTemplateDescriptor() {
    return new FileTemplateDescriptor("JUnit4 SetUp Method.java");
  }

  public FileTemplateDescriptor getTearDownMethodFileTemplateDescriptor() {
    return new FileTemplateDescriptor("JUnit4 TearDown Method.java");
  }

  public FileTemplateDescriptor getTestMethodFileTemplateDescriptor() {
    return new FileTemplateDescriptor("JUnit4 Test Method.java");
  }

  @Override
  public FileTemplateDescriptor getParametersMethodFileTemplateDescriptor() {
    return new FileTemplateDescriptor("JUnit4 Parameters Method.java");
  }

  @Override
  public char getMnemonic() {
    return '4';
  }

  @Override
  public FileTemplateDescriptor getTestClassFileTemplateDescriptor() {
    return new FileTemplateDescriptor("JUnit4 Test Class.java");
  }

  @Override
  public void setupLibrary(Module module) {
    try {
      OrderEntryFix.addJUnit4Library(false, module);
    }
    catch (ClassNotFoundException e) {
      LOG.info(e);
    }
  }

  @Override
  public boolean isParameterized(PsiClass clazz) {
    final PsiAnnotation annotation = AnnotationUtil.findAnnotation(clazz, JUnitUtil.RUN_WITH);
    if (annotation != null) {
      final PsiAnnotationMemberValue value = annotation.findAttributeValue(PsiAnnotation.DEFAULT_REFERENCED_METHOD_NAME);
      if (value instanceof PsiClassObjectAccessExpression) {
        final PsiTypeElement operand = ((PsiClassObjectAccessExpression)value).getOperand();
        final PsiClass psiClass = PsiUtil.resolveClassInClassTypeOnly(operand.getType());
        return psiClass != null && "org.junit.runners.Parameterized".equals(psiClass.getQualifiedName());
      }
    }
    return false;
  }

  @Override
  public PsiMethod findParametersMethod(PsiClass clazz) {
    final PsiMethod[] methods = clazz.getAllMethods();
    for (PsiMethod method : methods) {
      if (method.hasModifierProperty(PsiModifier.PUBLIC) && 
          method.hasModifierProperty(PsiModifier.STATIC) &&
          AnnotationUtil.isAnnotated(method, "org.junit.runners.Parameterized.Parameters", false)) {
        //todo check return value
        return method;
      }
    }
    return null;
  }
}
