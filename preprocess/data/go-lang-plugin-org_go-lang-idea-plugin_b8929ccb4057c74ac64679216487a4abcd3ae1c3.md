Refactoring Types: ['Extract Method', 'Move Attribute']
yright 2013-2015 Sergey Ignatov, Alexander Zolotov, Mihai Toader, Florin Patan
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

package com.goide.runconfig;

import com.goide.GoConstants;
import com.goide.GoFileType;
import com.goide.psi.GoFile;
import com.goide.psi.GoPackageClause;
import com.intellij.execution.actions.ConfigurationContext;
import com.intellij.openapi.fileChooser.FileChooserDescriptor;
import com.intellij.openapi.fileChooser.FileChooserDescriptorFactory;
import com.intellij.openapi.project.Project;
import com.intellij.openapi.ui.TextBrowseFolderListener;
import com.intellij.openapi.ui.TextFieldWithBrowseButton;
import com.intellij.openapi.util.Condition;
import com.intellij.openapi.vfs.VirtualFile;
import com.intellij.psi.PsiElement;
import com.intellij.psi.PsiFile;
import com.intellij.psi.PsiManager;
import com.intellij.psi.util.PsiTreeUtil;
import org.jetbrains.annotations.Contract;
import org.jetbrains.annotations.NotNull;
import org.jetbrains.annotations.Nullable;

public class GoRunUtil {
  private GoRunUtil() {
    
  }

  @Contract("null -> false")
  public static boolean isPackageContext(@Nullable PsiElement contextElement) {
    return PsiTreeUtil.getNonStrictParentOfType(contextElement, GoPackageClause.class) != null;
  }

  @Nullable
  public static PsiFile findMainFileInDirectory(@NotNull VirtualFile packageDirectory, @NotNull Project project) {
    for (VirtualFile file : packageDirectory.getChildren()) {
      if (file == null) {
        continue;
      }
      PsiFile psiFile = PsiManager.getInstance(project).findFile(file);
      if (isMainGoFile(psiFile)) {
        return psiFile;
      }
    }
    return null;
  }

  @Nullable
  public static PsiElement getContextElement(@Nullable ConfigurationContext context) {
    if (context == null) {
      return null;
    }
    PsiElement psiElement = context.getPsiLocation();
    if (psiElement == null || !psiElement.isValid()) {
      return null;
    }
    return psiElement;
  }

  public static void installGoWithMainFileChooser(final Project project, @NotNull TextFieldWithBrowseButton fileField) {
    installFileChooser(project, fileField, false, new Condition<VirtualFile>() {
      @Override
      public boolean value(VirtualFile file) {
        if (file.getFileType() != GoFileType.INSTANCE) {
          return false;
        }
        final PsiFile psiFile = PsiManager.getInstance(project).findFile(file);
        return isMainGoFile(psiFile);
      }
    });
  }
  
  public static boolean isMainGoFile(@Nullable PsiFile psiFile) {
    if (psiFile != null && psiFile instanceof GoFile) {
      return GoConstants.MAIN.equals(((GoFile)psiFile).getPackageName()) && ((GoFile)psiFile).hasMainFunction();
    }
    return false;
  }

  public static void installFileChooser(@NotNull Project project,
                                        @NotNull TextFieldWithBrowseButton field,
                                        boolean directory) {
    installFileChooser(project, field, directory, null);
  }

  public static void installFileChooser(@NotNull Project project,
                                        @NotNull TextFieldWithBrowseButton field,
                                        boolean directory,
                                        @Nullable Condition<VirtualFile> fileFilter) {
    FileChooserDescriptor chooseDirectoryDescriptor = directory
                                                      ? FileChooserDescriptorFactory.createSingleFolderDescriptor()
                                                      : FileChooserDescriptorFactory.createSingleLocalFileDescriptor();
    chooseDirectoryDescriptor.setRoots(project.getBaseDir());
    chooseDirectoryDescriptor.setShowFileSystemRoots(false);
    chooseDirectoryDescriptor.withFileFilter(fileFilter);
    field.addBrowseFolderListener(new TextBrowseFolderListener(chooseDirectoryDescriptor));
  }
}


File: src/com/goide/runconfig/testing/GoTestRunConfigurationProducerBase.java
/*
 * Copyright 2013-2015 Sergey Ignatov, Alexander Zolotov, Mihai Toader, Florin Patan
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

package com.goide.runconfig.testing;

import com.goide.psi.GoFile;
import com.goide.psi.GoFunctionDeclaration;
import com.goide.runconfig.GoRunUtil;
import com.goide.sdk.GoSdkService;
import com.intellij.execution.actions.ConfigurationContext;
import com.intellij.execution.actions.RunConfigurationProducer;
import com.intellij.execution.configurations.ConfigurationType;
import com.intellij.openapi.module.Module;
import com.intellij.openapi.module.ModuleUtilCore;
import com.intellij.openapi.util.Comparing;
import com.intellij.openapi.util.Ref;
import com.intellij.openapi.util.io.FileUtil;
import com.intellij.openapi.util.text.StringUtil;
import com.intellij.psi.PsiDirectory;
import com.intellij.psi.PsiElement;
import com.intellij.psi.PsiFile;
import com.intellij.psi.util.PsiTreeUtil;
import org.jetbrains.annotations.NotNull;
import org.jetbrains.annotations.Nullable;

public abstract class GoTestRunConfigurationProducerBase extends RunConfigurationProducer<GoTestRunConfigurationBase> {

  protected GoTestRunConfigurationProducerBase(@NotNull ConfigurationType configurationType) {
    super(configurationType);
  }

  @Override
  protected boolean setupConfigurationFromContext(@NotNull GoTestRunConfigurationBase configuration, ConfigurationContext context, Ref sourceElement) {
    PsiElement contextElement = GoRunUtil.getContextElement(context);
    if (contextElement == null) {
      return false;
    }

    Module module = ModuleUtilCore.findModuleForPsiElement(contextElement);
    if (module == null || !GoSdkService.getInstance(configuration.getProject()).isGoModule(module)) {
      return false;
    }
    
    configuration.setModule(module);
    if (contextElement instanceof PsiDirectory) {
      configuration.setName("All in '" + ((PsiDirectory)contextElement).getName() + "'");
      configuration.setKind(GoTestRunConfigurationBase.Kind.DIRECTORY);
      String directoryPath = ((PsiDirectory)contextElement).getVirtualFile().getPath();
      configuration.setDirectoryPath(directoryPath);
      configuration.setWorkingDirectory(directoryPath);
      return true;
    }
    else {
      PsiFile file = contextElement.getContainingFile();
      if (GoTestFinder.isTestFile(file)) {
        if (GoRunUtil.isPackageContext(contextElement)) {
          String packageName = StringUtil.notNullize(((GoFile)file).getImportPath());
          configuration.setKind(GoTestRunConfigurationBase.Kind.PACKAGE);
          configuration.setPackage(packageName);
          configuration.setName("All in '" + packageName + "'");
        }
        else {
          String functionNameFromContext = findFunctionNameFromContext(contextElement);
          if (functionNameFromContext != null) {
            configuration.setName(functionNameFromContext + " in " + file.getName());
            configuration.setPattern("^" + functionNameFromContext + "$");

            configuration.setKind(GoTestRunConfigurationBase.Kind.PACKAGE);
            configuration.setPackage(StringUtil.notNullize(((GoFile)file).getImportPath()));
          }
          else {
            configuration.setName(file.getName());
            configuration.setKind(GoTestRunConfigurationBase.Kind.FILE);
            configuration.setFilePath(file.getVirtualFile().getPath());
          }
        }
        return true;
      }
    }

    return false;
  }

  @Override
  public boolean isConfigurationFromContext(@NotNull GoTestRunConfigurationBase configuration, ConfigurationContext context) {
    PsiElement contextElement = GoRunUtil.getContextElement(context);
    if (contextElement == null) return false;

    Module module = ModuleUtilCore.findModuleForPsiElement(contextElement);
    if (!Comparing.equal(module, configuration.getConfigurationModule().getModule())) return false;

    PsiFile file = contextElement.getContainingFile();
    switch (configuration.getKind()) {
      case DIRECTORY:
        if (contextElement instanceof PsiDirectory) {
          String directoryPath = ((PsiDirectory)contextElement).getVirtualFile().getPath();
          return FileUtil.pathsEqual(configuration.getDirectoryPath(), directoryPath) &&
                 FileUtil.pathsEqual(configuration.getWorkingDirectory(), directoryPath);
        }
      case PACKAGE:
        if (!GoTestFinder.isTestFile(file)) return false;
        if (!Comparing.equal(((GoFile)file).getImportPath(), configuration.getPackage())) return false;
        if (GoRunUtil.isPackageContext(contextElement) && configuration.getPattern().isEmpty()) return true;
        
        String functionNameFromContext = findFunctionNameFromContext(contextElement);
        return functionNameFromContext != null 
               ? configuration.getPattern().equals("^" + functionNameFromContext + "$") 
               : configuration.getPattern().isEmpty();
      case FILE:
        return GoTestFinder.isTestFile(file) && FileUtil.pathsEqual(configuration.getFilePath(), file.getVirtualFile().getPath()) &&
          findFunctionNameFromContext(contextElement) == null;
    }
    return false;
  }

  @Nullable
  private static String findFunctionNameFromContext(PsiElement contextElement) {
    GoFunctionDeclaration function = PsiTreeUtil.getNonStrictParentOfType(contextElement, GoFunctionDeclaration.class);
    return function != null ? GoTestFinder.getTestFunctionName(function) : null;
  }
}


File: src/com/goide/runconfig/testing/frameworks/gocheck/GocheckRunConfiguration.java
/*
 * Copyright 2013-2015 Sergey Ignatov, Alexander Zolotov, Mihai Toader, Florin Patan
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

package com.goide.runconfig.testing.frameworks.gocheck;

import com.goide.psi.GoFile;
import com.goide.runconfig.GoModuleBasedConfiguration;
import com.goide.runconfig.testing.GoTestRunConfigurationBase;
import com.goide.runconfig.testing.GoTestRunningState;
import com.goide.runconfig.testing.ui.GoTestRunConfigurationEditorForm;
import com.goide.stubs.index.GoPackagesIndex;
import com.goide.util.GoUtil;
import com.intellij.execution.configurations.ConfigurationType;
import com.intellij.execution.configurations.ModuleBasedConfiguration;
import com.intellij.execution.configurations.RunConfiguration;
import com.intellij.execution.configurations.RuntimeConfigurationException;
import com.intellij.execution.runners.ExecutionEnvironment;
import com.intellij.execution.testframework.TestConsoleProperties;
import com.intellij.execution.testframework.sm.runner.OutputToGeneralTestEventsConverter;
import com.intellij.openapi.module.Module;
import com.intellij.openapi.options.SettingsEditor;
import com.intellij.openapi.project.Project;
import com.intellij.psi.stubs.StubIndex;
import org.jetbrains.annotations.NotNull;

import java.util.regex.Pattern;

public class GocheckRunConfiguration extends GoTestRunConfigurationBase {
  private static final Pattern GO_CHECK_IMPORT_PATH = Pattern.compile("gopkg\\.in/check\\.v\\d+");
  private static final Pattern GO_CHECK_GITHUB_IMPORT_PATH = Pattern.compile("github\\.com/go-check/check\\.v\\d+");

  public GocheckRunConfiguration(@NotNull Project project, String name, @NotNull ConfigurationType configurationType) {
    super(project, name, configurationType);
  }

  @Override
  public OutputToGeneralTestEventsConverter createTestEventsConverter(@NotNull TestConsoleProperties consoleProperties) {
    return new GocheckEventsConverter(consoleProperties);
  }

  @Override
  public String getFrameworkName() {
    return "gocheck";
  }

  @Override
  public void checkConfiguration() throws RuntimeConfigurationException {
    super.checkConfiguration();
    GoModuleBasedConfiguration configurationModule = getConfigurationModule();
    Module module = configurationModule.getModule();
    assert module != null;
    for (GoFile file : StubIndex.getElements(GoPackagesIndex.KEY, "check", getProject(), GoUtil.moduleScope(module), GoFile.class)) {
      String importPath = file.getImportPath();
      if (importPath != null && (GO_CHECK_IMPORT_PATH.matcher(importPath).matches() ||
                                 GO_CHECK_GITHUB_IMPORT_PATH.matcher(importPath).matches())) {
        return;
      }
    }
    throw new RuntimeConfigurationException("Cannot find gocheck package in GOPATH");
  }

  @NotNull
  @Override
  public SettingsEditor<? extends RunConfiguration> getConfigurationEditor() {
    return new GoTestRunConfigurationEditorForm(getProject());
  }

  @NotNull
  @Override
  protected GoTestRunningState newRunningState(@NotNull ExecutionEnvironment env, @NotNull Module module) {
    return new GocheckRunningState(env, module, this);
  }

  @NotNull
  @Override
  protected ModuleBasedConfiguration createInstance() {
    return new GocheckRunConfiguration(getProject(), getName(), GocheckRunConfigurationType.getInstance());
  }
}


File: src/com/goide/runconfig/testing/frameworks/gocheck/GocheckRunConfigurationProducer.java
/*
 * Copyright 2013-2015 Sergey Ignatov, Alexander Zolotov, Mihai Toader, Florin Patan
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

package com.goide.runconfig.testing.frameworks.gocheck;

import com.goide.runconfig.testing.GoTestRunConfigurationProducerBase;


public class GocheckRunConfigurationProducer extends GoTestRunConfigurationProducerBase implements Cloneable {
  public GocheckRunConfigurationProducer() {
    super(GocheckRunConfigurationType.getInstance());
  }
}
