Refactoring Types: ['Extract Method']
pletionContributor.java
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

package com.goide.completion;

import com.goide.GoConstants;
import com.goide.GoParserDefinition;
import com.goide.GoTypes;
import com.goide.psi.GoImportString;
import com.goide.psi.GoPackageClause;
import com.goide.psi.GoReferenceExpressionBase;
import com.goide.util.GoUtil;
import com.intellij.codeInsight.completion.CompletionContributor;
import com.intellij.codeInsight.completion.CompletionParameters;
import com.intellij.codeInsight.completion.CompletionResultSet;
import com.intellij.codeInsight.completion.CompletionType;
import com.intellij.codeInsight.lookup.LookupElementBuilder;
import com.intellij.openapi.util.io.FileUtil;
import com.intellij.openapi.util.text.StringUtil;
import com.intellij.patterns.PlatformPatterns;
import com.intellij.patterns.PsiElementPattern;
import com.intellij.psi.PsiDirectory;
import com.intellij.psi.PsiElement;
import org.jetbrains.annotations.NotNull;

import java.util.Collection;

public class GoCompletionContributor extends CompletionContributor {
  public GoCompletionContributor() {
    extend(CompletionType.BASIC, importString(), new GoImportPathsCompletionProvider());
    extend(CompletionType.BASIC, referenceExpression(), new GoReferenceCompletionProvider());
  }

  @Override
  public void fillCompletionVariants(@NotNull CompletionParameters parameters, @NotNull CompletionResultSet result) {
    PsiElement position = parameters.getPosition();
    if (position.getParent() instanceof GoPackageClause && position.getNode().getElementType() == GoTypes.IDENTIFIER) {
      PsiDirectory directory = parameters.getOriginalFile().getParent();
      Collection<String> packagesInDirectory = GoUtil.getAllPackagesInDirectory(directory);
      for (String packageName : packagesInDirectory) {
        result.addElement(LookupElementBuilder.create(packageName));
        if (packageName.endsWith(GoConstants.TEST_SUFFIX)) {
          result.addElement(LookupElementBuilder.create(StringUtil.trimEnd(packageName, GoConstants.TEST_SUFFIX)));
        }
      }

      if (packagesInDirectory.isEmpty() && directory != null) {
        String packageFromDirectory = FileUtil.sanitizeFileName(directory.getName());
        if (!packageFromDirectory.isEmpty()) {
          result.addElement(LookupElementBuilder.create(packageFromDirectory));
        }
      }
      result.addElement(LookupElementBuilder.create(GoConstants.MAIN));
    }
    super.fillCompletionVariants(parameters, result);
  }

  private static PsiElementPattern.Capture<PsiElement> importString() {
    return PlatformPatterns.psiElement().withElementType(GoParserDefinition.STRING_LITERALS).withParent(GoImportString.class);
  }
  
  private static PsiElementPattern.Capture<PsiElement> referenceExpression() {
    return PlatformPatterns.psiElement().withParent(GoReferenceExpressionBase.class);
  }
}


File: src/com/goide/completion/GoCompletionUtil.java
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

package com.goide.completion;

import com.goide.GoIcons;
import com.goide.psi.*;
import com.goide.psi.impl.GoPsiImplUtil;
import com.goide.sdk.GoSdkUtil;
import com.goide.stubs.GoFieldDefinitionStub;
import com.intellij.codeInsight.completion.InsertHandler;
import com.intellij.codeInsight.completion.InsertionContext;
import com.intellij.codeInsight.completion.PrefixMatcher;
import com.intellij.codeInsight.completion.PrioritizedLookupElement;
import com.intellij.codeInsight.completion.impl.CamelHumpMatcher;
import com.intellij.codeInsight.completion.util.ParenthesesInsertHandler;
import com.intellij.codeInsight.lookup.LookupElement;
import com.intellij.codeInsight.lookup.LookupElementBuilder;
import com.intellij.codeInsight.lookup.LookupElementPresentation;
import com.intellij.codeInsight.lookup.LookupElementRenderer;
import com.intellij.openapi.util.text.StringUtil;
import com.intellij.psi.PsiDirectory;
import com.intellij.psi.PsiElement;
import com.intellij.psi.PsiFile;
import com.intellij.psi.util.PsiTreeUtil;
import com.intellij.util.ObjectUtils;
import com.intellij.util.ui.UIUtil;
import org.jetbrains.annotations.NotNull;
import org.jetbrains.annotations.Nullable;

import javax.swing.*;

public class GoCompletionUtil {
  public static final int KEYWORD_PRIORITY = 20;
  public static final int CONTEXT_KEYWORD_PRIORITY = 25;
  public static final int NOT_IMPORTED_FUNCTION_PRIORITY = 3;
  public static final int FUNCTION_PRIORITY = NOT_IMPORTED_FUNCTION_PRIORITY + 10;
  public static final int NOT_IMPORTED_TYPE_PRIORITY = 5;
  public static final int TYPE_PRIORITY = NOT_IMPORTED_TYPE_PRIORITY + 10;
  public static final int NOT_IMPORTED_TYPE_CONVERSION = 1;
  public static final int TYPE_CONVERSION = NOT_IMPORTED_TYPE_CONVERSION + 10;
  public static final int VAR_PRIORITY = 15;
  public static final int LABEL_PRIORITY = 15;
  public static final int PACKAGE_PRIORITY = 5;
  public static final InsertHandler<LookupElement> FUNCTION_INSERT_HANDLER = new InsertHandler<LookupElement>() {
    @Override
    public void handleInsert(InsertionContext context, LookupElement item) {
      PsiElement element = item.getPsiElement();
      if (!(element instanceof GoSignatureOwner)) return;
      GoSignatureOwner f = (GoSignatureOwner)element;
      GoSignature signature = f.getSignature();
      int paramsCount = signature != null ? signature.getParameters().getParameterDeclarationList().size() : 0;
      InsertHandler<LookupElement> handler =
        paramsCount == 0 ? ParenthesesInsertHandler.NO_PARAMETERS : ParenthesesInsertHandler.WITH_PARAMETERS;
      handler.handleInsert(context, item);
    }
  };
  public static final LookupElementRenderer<LookupElement> FUNCTION_RENDERER = new LookupElementRenderer<LookupElement>() {
    @Override
    public void renderElement(LookupElement element, LookupElementPresentation p) {
      PsiElement o = element.getPsiElement();
      if (!(o instanceof GoNamedSignatureOwner)) return;
      GoNamedSignatureOwner f = (GoNamedSignatureOwner)o;
      Icon icon = f instanceof GoMethodDeclaration || f instanceof GoMethodSpec ? GoIcons.METHOD : GoIcons.FUNCTION;
      String typeText = "";
      GoSignature signature = f.getSignature();
      String paramText = "";
      if (signature != null) {
        GoResult result = signature.getResult();
        paramText = signature.getParameters().getText();
        if (result != null) typeText = result.getText();
      }

      p.setIcon(icon);
      p.setTypeText(typeText);
      p.setTypeGrayed(true);
      p.setTailText(calcTailText(f), true);
      p.setItemText(element.getLookupString() + paramText);
    }
  };
  public static final LookupElementRenderer<LookupElement> VARIABLE_RENDERER = new LookupElementRenderer<LookupElement>() {
    @Override
    public void renderElement(LookupElement element, LookupElementPresentation p) {
      PsiElement o = element.getPsiElement();
      if (!(o instanceof GoNamedElement)) return;
      GoNamedElement v = (GoNamedElement)o;
      GoType type = v.getGoType(null);
      String text = GoPsiImplUtil.getText(type);
      Icon icon = v instanceof GoVarDefinition ? GoIcons.VARIABLE :
                  v instanceof GoParamDefinition ? GoIcons.PARAMETER :
                  v instanceof GoFieldDefinition ? GoIcons.FIELD :
                  v instanceof GoReceiver ? GoIcons.RECEIVER :
                  v instanceof GoConstDefinition ? GoIcons.CONSTANT :
                  v instanceof GoAnonymousFieldDefinition ? GoIcons.FIELD :
                  null;

      p.setIcon(icon);
      p.setTailText(calcTailTextForFields(v), true);
      p.setTypeText(text);
      p.setTypeGrayed(true);
    }
  };

  private static class Lazy {
    private static final SingleCharInsertHandler DIR_INSERT_HANDLER = new SingleCharInsertHandler('/');
    private static final SingleCharInsertHandler PACKAGE_INSERT_HANDLER = new SingleCharInsertHandler('.');
  }

  private GoCompletionUtil() {

  }

  @NotNull
  public static CamelHumpMatcher createPrefixMatcher(@NotNull PrefixMatcher original) {
    return createPrefixMatcher(original.getPrefix());
  }

  @NotNull
  public static CamelHumpMatcher createPrefixMatcher(@NotNull String prefix) {
    return new CamelHumpMatcher(prefix, false);
  }

  @NotNull
  public static LookupElement createFunctionOrMethodLookupElement(@NotNull final GoNamedSignatureOwner f,
                                                                  @NotNull final String lookupString,
                                                                  @Nullable final InsertHandler<LookupElement> h,
                                                                  final double priority) {
    return PrioritizedLookupElement.withPriority(LookupElementBuilder
                                                   .createWithSmartPointer(lookupString, f)
                                                   .withRenderer(FUNCTION_RENDERER)
                                                   .withInsertHandler(h != null ? h : FUNCTION_INSERT_HANDLER), priority);
  }

  @Nullable
  private static String calcTailText(GoSignatureOwner m) {
    String text = "";
    if (m instanceof GoMethodDeclaration) {
      text = GoPsiImplUtil.getText(((GoMethodDeclaration)m).getReceiver().getType());
    }
    else if (m instanceof GoMethodSpec) {
      PsiElement parent = m.getParent();
      if (parent instanceof GoInterfaceType) {
        text = GoPsiImplUtil.getText((GoInterfaceType)parent);
      }
    }
    return StringUtil.isNotEmpty(text) ? " " + UIUtil.rightArrow() + " " + text : null;
  }

  @NotNull
  public static LookupElement createTypeLookupElement(@NotNull GoTypeSpec t) {
    return createTypeLookupElement(t, StringUtil.notNullize(t.getName()), null, null, TYPE_PRIORITY);
  }

  @NotNull
  public static LookupElement createTypeLookupElement(@NotNull GoTypeSpec t,
                                                      @NotNull String lookupString,
                                                      @Nullable InsertHandler<LookupElement> handler,
                                                      @Nullable String importPath,
                                                      double priority) {
    LookupElementBuilder builder = LookupElementBuilder.createWithSmartPointer(lookupString, t)
      .withInsertHandler(handler).withIcon(GoIcons.TYPE);
    if (importPath != null) builder = builder.withTailText(" " + importPath, true);
    return PrioritizedLookupElement.withPriority(builder, priority);
  }

  @NotNull
  public static LookupElement createLabelLookupElement(@NotNull GoLabelDefinition l, @NotNull String lookupString) {
    return PrioritizedLookupElement.withPriority(LookupElementBuilder.createWithSmartPointer(lookupString, l)
                                                   .withIcon(GoIcons.LABEL), LABEL_PRIORITY);
  }

  @NotNull
  public static LookupElement createTypeConversionLookupElement(@NotNull GoTypeSpec t) {
    return createTypeConversionLookupElement(t, StringUtil.notNullize(t.getName()), null, null, TYPE_CONVERSION);
  }

  @NotNull
  public static LookupElement createTypeConversionLookupElement(@NotNull GoTypeSpec t,
                                                                @NotNull String lookupString,
                                                                @Nullable InsertHandler<LookupElement> insertHandler,
                                                                @Nullable String importPath,
                                                                double priority) {
    // todo: check context and place caret in or outside {}
    InsertHandler<LookupElement> handler = ObjectUtils.notNull(insertHandler, getTypeConversionInsertHandler(t));
    return createTypeLookupElement(t, lookupString, handler, importPath, priority);
  }

  @NotNull
  public static InsertHandler<LookupElement> getTypeConversionInsertHandler(@NotNull GoTypeSpec t) {
    GoType type = t.getType();
    return type instanceof GoStructType || type instanceof GoArrayOrSliceType || type instanceof GoMapType
           ? BracesInsertHandler.ONE_LINER
           : ParenthesesInsertHandler.WITH_PARAMETERS;
  }

  @NotNull
  public static LookupElement createVariableLikeLookupElement(@NotNull GoNamedElement v) {
    String name = StringUtil.notNullize(v.getName());
    SingleCharInsertHandler handler =
      v instanceof GoFieldDefinition ?
      new SingleCharInsertHandler(':') {
        @Override
        public void handleInsert(@NotNull InsertionContext context, LookupElement item) {
          PsiFile file = context.getFile();
          if (!(file instanceof GoFile)) return;
          context.commitDocument();
          int offset = context.getStartOffset();
          PsiElement at = file.findElementAt(offset);
          GoCompositeElement ref = PsiTreeUtil.getParentOfType(at, GoValue.class, GoReferenceExpression.class);
          if (ref instanceof GoReferenceExpression && (((GoReferenceExpression)ref).getQualifier() != null || GoPsiImplUtil.prevDot(ref))) {
            return;
          }
          GoValue value = PsiTreeUtil.getParentOfType(at, GoValue.class);
          if (value == null || PsiTreeUtil.getPrevSiblingOfType(value, GoKey.class) != null) return;
          super.handleInsert(context, item);
        }
      } : null;
    return PrioritizedLookupElement.withPriority(
      LookupElementBuilder.createWithSmartPointer(name, v)
        .withLookupString(name.toLowerCase()).withRenderer(VARIABLE_RENDERER)
        .withInsertHandler(handler)
      , VAR_PRIORITY);
  }

  @Nullable
  private static String calcTailTextForFields(@NotNull GoNamedElement v) {
    String name = null;
    if (v instanceof GoFieldDefinition) {
      GoFieldDefinitionStub stub = ((GoFieldDefinition)v).getStub();
      GoTypeSpec spec = stub != null ? stub.getParentStubOfType(GoTypeSpec.class) : PsiTreeUtil.getParentOfType(v, GoTypeSpec.class);
      name = spec != null ? spec.getName() : null;
    }
    return StringUtil.isNotEmpty(name) ? " " + UIUtil.rightArrow() + " " + name : null;
  }

  @Nullable
  public static LookupElement createPackageLookupElement(@NotNull GoImportSpec spec, @Nullable String name) {
    name = name != null ? name : ObjectUtils.notNull(spec.getAlias(), spec.getLocalPackageName());
    return createPackageLookupElement(name, spec, true);
  }

  @NotNull
  public static LookupElement createPackageLookupElement(@NotNull String importPath,
                                                         @Nullable PsiElement context,
                                                         boolean forType) {
    return createPackageLookupElement(importPath, getContextImportPath(context), forType);
  }

  @NotNull
  public static LookupElement createPackageLookupElement(@NotNull String importPath, @Nullable String contextImportPath, boolean forType) {
    return PrioritizedLookupElement.withPriority(
      LookupElementBuilder.create(importPath)
        .withLookupString(importPath.substring(Math.max(0, importPath.lastIndexOf('/'))))
        .withIcon(GoIcons.PACKAGE).withInsertHandler(forType ? Lazy.PACKAGE_INSERT_HANDLER : null),
      calculatePackagePriority(importPath, contextImportPath));
  }

  public static int calculatePackagePriority(@NotNull String importPath, @Nullable String currentPath) {
    int priority = PACKAGE_PRIORITY;
    if (StringUtil.isNotEmpty(currentPath)) {
      String[] givenSplit = importPath.split("/");
      String[] contextSplit = currentPath.split("/");
      for (int i = 0; i < contextSplit.length && i < givenSplit.length; i++) {
        if (contextSplit[i].equals(givenSplit[i])) {
          priority++;
        }
        else {
          break;
        }
      }
    }
    return priority - StringUtil.countChars(importPath, '/') - StringUtil.countChars(importPath, '.');
  }

  @Nullable
  public static String getContextImportPath(@Nullable PsiElement context) {
    if (context == null) return null;
    String currentPath = null;
    if (context instanceof PsiDirectory) {
      currentPath = GoSdkUtil.getImportPath((PsiDirectory)context);
    }
    else {
      PsiFile file = context.getContainingFile();
      if (file instanceof GoFile) {
        currentPath = ((GoFile)file).getImportPath();
      }
    }
    return currentPath;
  }

  @NotNull
  public static LookupElementBuilder createDirectoryLookupElement(@NotNull PsiDirectory dir) {
    int files = dir.getFiles().length;
    return LookupElementBuilder.createWithSmartPointer(dir.getName(), dir).withIcon(GoIcons.DIRECTORY)
      .withInsertHandler(files == 0 ? Lazy.DIR_INSERT_HANDLER : null);
  }
}


File: src/com/goide/completion/GoReferenceCompletionProvider.java
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

package com.goide.completion;

import com.goide.psi.*;
import com.goide.psi.impl.GoFieldNameReference;
import com.goide.psi.impl.GoReference;
import com.goide.psi.impl.GoScopeProcessor;
import com.goide.psi.impl.GoTypeReference;
import com.intellij.codeInsight.completion.CompletionParameters;
import com.intellij.codeInsight.completion.CompletionProvider;
import com.intellij.codeInsight.completion.CompletionResultSet;
import com.intellij.codeInsight.lookup.LookupElement;
import com.intellij.psi.PsiDirectory;
import com.intellij.psi.PsiElement;
import com.intellij.psi.PsiReference;
import com.intellij.psi.ResolveState;
import com.intellij.psi.impl.source.resolve.reference.impl.PsiMultiReference;
import com.intellij.psi.util.PsiTreeUtil;
import com.intellij.util.ArrayUtil;
import com.intellij.util.ProcessingContext;
import com.intellij.util.containers.ContainerUtil;
import org.jetbrains.annotations.NotNull;
import org.jetbrains.annotations.Nullable;

import static com.goide.completion.GoCompletionUtil.createPrefixMatcher;

public class GoReferenceCompletionProvider extends CompletionProvider<CompletionParameters> {
  @Override
  protected void addCompletions(@NotNull CompletionParameters parameters, ProcessingContext context, @NotNull CompletionResultSet set) {
    final GoReferenceExpressionBase expression = PsiTreeUtil.getParentOfType(parameters.getPosition(), GoReferenceExpressionBase.class);
    if (expression != null) {
      fillVariantsByReference(expression.getReference(), set.withPrefixMatcher(createPrefixMatcher(set.getPrefixMatcher())));
    }
  }

  private static void fillVariantsByReference(@Nullable PsiReference reference, @NotNull final CompletionResultSet result) {
    if (reference == null) return;
    if (reference instanceof PsiMultiReference) {
      PsiReference[] references = ((PsiMultiReference)reference).getReferences();
      ContainerUtil.sort(references, PsiMultiReference.COMPARATOR);
      fillVariantsByReference(ArrayUtil.getFirstElement(references), result);
    }
    else if (reference instanceof GoReference) {
      ((GoReference)reference).processResolveVariants(new MyGoScopeProcessor(result, false));

      PsiElement element = reference.getElement();
      if (element instanceof GoReferenceExpression && PsiTreeUtil.getParentOfType(element, GoCompositeLit.class) != null) {
        for (Object o : new GoFieldNameReference(((GoReferenceExpression)element)).getVariants()) {
          if (o instanceof LookupElement) result.addElement(((LookupElement)o));
        }
      }
    }
    else if (reference instanceof GoTypeReference) {
      PsiElement element = reference.getElement();
      final PsiElement spec = PsiTreeUtil.getParentOfType(element, GoFieldDeclaration.class, GoTypeSpec.class);
      final boolean insideParameter = PsiTreeUtil.getParentOfType(element, GoParameterDeclaration.class) != null;
      ((GoTypeReference)reference).processResolveVariants(new MyGoScopeProcessor(result, true) {
        @Override
        protected boolean accept(@NotNull PsiElement e) {
          return e != spec &&
                 !(insideParameter &&
                   (e instanceof GoNamedSignatureOwner || e instanceof GoVarDefinition || e instanceof GoConstDefinition));
        }
      });
      if (element instanceof GoReferenceExpressionBase && element.getParent() instanceof GoReceiverType) {
        fillVariantsByReference(new GoReference((GoReferenceExpressionBase)element), result);
      }
    }
  }

  private static void addElement(@NotNull PsiElement o, @NotNull ResolveState state, boolean forTypes, @NotNull CompletionResultSet set) {
    LookupElement lookup = createLookupElement(o, state, forTypes);
    if (lookup != null) {
      set.addElement(lookup);
    }
  }

  @Nullable
  private static LookupElement createLookupElement(@NotNull PsiElement o, @NotNull ResolveState state, boolean forTypes) {
    if (o instanceof GoNamedElement && !((GoNamedElement)o).isBlank() || o instanceof GoImportSpec && !((GoImportSpec)o).isDot()) {
      if (o instanceof GoImportSpec) {
        return GoCompletionUtil.createPackageLookupElement(((GoImportSpec)o), state.get(GoReference.ACTUAL_NAME));
      }
      else if (o instanceof GoNamedSignatureOwner && ((GoNamedSignatureOwner)o).getName() != null) {
        String name = ((GoNamedSignatureOwner)o).getName();
        if (name != null) {
          return GoCompletionUtil.createFunctionOrMethodLookupElement((GoNamedSignatureOwner)o, name, null,
                                                                        GoCompletionUtil.FUNCTION_PRIORITY);
        }
      }
      else if (o instanceof GoTypeSpec) {
        return forTypes
                 ? GoCompletionUtil.createTypeLookupElement((GoTypeSpec)o)
                 : GoCompletionUtil.createTypeConversionLookupElement((GoTypeSpec)o);
      }
      else if (o instanceof PsiDirectory) {
        return GoCompletionUtil.createPackageLookupElement(((PsiDirectory)o).getName(), o, true);
      }
      else {
        return GoCompletionUtil.createVariableLikeLookupElement((GoNamedElement)o);
      }
    }
    return null;
  }

  private static class MyGoScopeProcessor extends GoScopeProcessor {
    private final CompletionResultSet myResult;
    private final boolean myForTypes;

    public MyGoScopeProcessor(@NotNull CompletionResultSet result, boolean forTypes) {
      myResult = result;
      myForTypes = forTypes;
    }

    @Override
    public boolean execute(@NotNull PsiElement o, @NotNull ResolveState state) {
      if (accept(o)) {
        addElement(o, state, myForTypes, myResult);
      }
      return true;
    }

    protected boolean accept(@NotNull PsiElement e) {
      return true;
    }

    @Override
    public boolean isCompletion() {
      return true;
    }
  }
}
                                                      

File: src/com/goide/psi/impl/GoCachedReference.java
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

package com.goide.psi.impl;

import com.goide.util.GoUtil;
import com.intellij.openapi.util.TextRange;
import com.intellij.psi.PsiElement;
import com.intellij.psi.PsiReferenceBase;
import com.intellij.psi.impl.source.resolve.ResolveCache;
import com.intellij.util.IncorrectOperationException;
import org.jetbrains.annotations.NotNull;
import org.jetbrains.annotations.Nullable;

public abstract class GoCachedReference<T extends PsiElement> extends PsiReferenceBase<T> {
  protected GoCachedReference(@NotNull T element) {
    super(element, TextRange.from(0, element.getTextLength()));
  }

  private static final ResolveCache.AbstractResolver<PsiReferenceBase, PsiElement> MY_RESOLVER =
    new ResolveCache.AbstractResolver<PsiReferenceBase, PsiElement>() {
      @Override
      public PsiElement resolve(@NotNull PsiReferenceBase base, boolean b) {
        return ((GoCachedReference)base).resolveInner();
      }
    };

  @Nullable
  protected abstract PsiElement resolveInner();

  @Nullable
  @Override
  public final PsiElement resolve() {
    return myElement.isValid()
           ? ResolveCache.getInstance(myElement.getProject()).resolveWithCaching(this, MY_RESOLVER, false, false)
           : null;
  }

  @Override
  public PsiElement handleElementRename(String newElementName) throws IncorrectOperationException {
    myElement.replace(GoElementFactory.createIdentifierFromText(myElement.getProject(), newElementName));
    return myElement;
  }

  @Override
  public boolean isReferenceTo(PsiElement element) {
    return GoUtil.couldBeReferenceTo(element, myElement) && super.isReferenceTo(element);
  }
}


File: src/com/goide/psi/impl/GoFieldNameReference.java
/*
 * Copyright 2013-2014 Sergey Ignatov, Alexander Zolotov, Mihai Toader, Florin Patan
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

package com.goide.psi.impl;

import com.goide.completion.GoCompletionUtil;
import com.goide.psi.*;
import com.intellij.codeInsight.lookup.LookupElement;
import com.intellij.psi.PsiElement;
import com.intellij.psi.PsiReference;
import com.intellij.psi.ResolveState;
import com.intellij.psi.util.PsiTreeUtil;
import com.intellij.util.ArrayUtil;
import com.intellij.util.containers.ContainerUtil;
import org.jetbrains.annotations.NotNull;
import org.jetbrains.annotations.Nullable;

import java.util.Collection;
import java.util.List;

public class GoFieldNameReference extends GoCachedReference<GoReferenceExpressionBase> {
  private GoCompositeElement myValue;

  @NotNull
  private GoScopeProcessorBase getProcessor(final boolean completion) {
    return new GoScopeProcessorBase(myElement.getText(), myElement, completion) {
      @Override
      protected boolean condition(@NotNull PsiElement element) {
        return !(element instanceof GoFieldDefinition) && !(element instanceof GoAnonymousFieldDefinition);
      }
    };
  }

  public GoFieldNameReference(@NotNull GoReferenceExpressionBase element) {
    super(element);
    GoCompositeElement place = myElement;
    while ((place = PsiTreeUtil.getParentOfType(place, GoLiteralValue.class)) != null) {
      if (place.getParent() instanceof GoValue) {
        myValue = (GoValue)place.getParent();
        break;
      }
    }
  }

  private boolean processFields(@NotNull GoScopeProcessorBase processor) {
    GoKey key = PsiTreeUtil.getParentOfType(myElement, GoKey.class);
    GoValue value = PsiTreeUtil.getParentOfType(myElement, GoValue.class);
    if (key == null && (value == null || PsiTreeUtil.getPrevSiblingOfType(value, GoKey.class) != null)) return false;

    GoCompositeLit lit = PsiTreeUtil.getParentOfType(myElement, GoCompositeLit.class);

    GoType type = lit != null ? lit.getType() : null;
    if (type == null && lit != null) {
      type = GoPsiImplUtil.getType(lit.getTypeReferenceExpression());
    }

    type = getType(type);

    if (type instanceof GoStructType && !type.processDeclarations(processor, ResolveState.initial(), null, myElement)) return true;

    return false;
  }

  @Nullable
  private GoType getType(GoType type) { // todo: rethink and unify this algorithm
    boolean inValue = myValue != null;
    
    if (inValue && type instanceof GoArrayOrSliceType) type = ((GoArrayOrSliceType)type).getType();
    else if (type instanceof GoMapType) type = inValue ? ((GoMapType)type).getValueType() : ((GoMapType)type).getKeyType();
    else if (inValue && type instanceof GoStructType) {
      GoKey key = PsiTreeUtil.getPrevSiblingOfType(myValue, GoKey.class);
      GoFieldName field = key != null ? key.getFieldName() : null;
      PsiReference reference = field != null ? field.getReference() : null;
      PsiElement resolve = reference != null ? reference.resolve() : null;
      if (resolve instanceof GoFieldDefinition) {
        type = PsiTreeUtil.getNextSiblingOfType(resolve, GoType.class);
      }
    }

    if (type != null && type.getTypeReferenceExpression() != null) {
      type = GoPsiImplUtil.getType(type.getTypeReferenceExpression());
    }

    if (type instanceof GoPointerType) {
      GoType inner = ((GoPointerType)type).getType();
      if (inner != null && inner.getTypeReferenceExpression() != null) {
        type = GoPsiImplUtil.getType(inner.getTypeReferenceExpression());
      }
    }

    return type;
  }

  @Nullable
  @Override
  public PsiElement resolveInner() {
    GoScopeProcessorBase p = getProcessor(false);
    processFields(p);
    return p.getResult();
  }

  @NotNull
  @Override
  public Object[] getVariants() {
    GoScopeProcessorBase p = getProcessor(true);
    processFields(p);
    List<GoNamedElement> variants = p.getVariants();
    if (variants.isEmpty()) return EMPTY_ARRAY;
    Collection<LookupElement> result = ContainerUtil.newArrayList();
    for (GoNamedElement element : variants) {
      result.add(GoCompletionUtil.createVariableLikeLookupElement(element));
    }
    return ArrayUtil.toObjectArray(result);
  }
}


File: src/com/goide/psi/impl/GoLabelReference.java
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

package com.goide.psi.impl;

import com.goide.completion.GoCompletionUtil;
import com.goide.psi.GoBlock;
import com.goide.psi.GoLabelDefinition;
import com.goide.psi.GoLabelRef;
import com.intellij.codeInsight.lookup.LookupElement;
import com.intellij.psi.PsiElement;
import com.intellij.psi.ResolveState;
import com.intellij.psi.util.PsiTreeUtil;
import com.intellij.util.ArrayUtil;
import com.intellij.util.containers.ContainerUtil;
import org.jetbrains.annotations.NotNull;
import org.jetbrains.annotations.Nullable;

import java.util.Collection;

public class GoLabelReference extends GoCachedReference<GoLabelRef> {
  private final GoScopeProcessorBase myProcessor = new GoScopeProcessorBase(myElement.getText(), myElement, false) {
    @Override
    protected boolean condition(@NotNull PsiElement element) {
      return !(element instanceof GoLabelDefinition);
    }
  };

  public GoLabelReference(@NotNull GoLabelRef element) {
    super(element);
  }

  @NotNull
  private Collection<GoLabelDefinition> getLabelDefinitions() {
    GoBlock block = PsiTreeUtil.getTopmostParentOfType(myElement, GoBlock.class);
    return PsiTreeUtil.findChildrenOfType(block, GoLabelDefinition.class);
  }

  @Nullable
  @Override
  protected PsiElement resolveInner() {
    Collection<GoLabelDefinition> defs = getLabelDefinitions();
    for (GoLabelDefinition def : defs) {
      if (!myProcessor.execute(def, ResolveState.initial())) return def;
    }
    return null;
  }

  @NotNull
  @Override
  public Object[] getVariants() {
    Collection<LookupElement> result = ContainerUtil.newArrayList();
    for (GoLabelDefinition element : getLabelDefinitions()) {
      String name = element.getName();
      if (name != null) {
        result.add(GoCompletionUtil.createLabelLookupElement(element, name));
      }
    }
    return ArrayUtil.toObjectArray(result);
  }
}


File: src/com/goide/psi/impl/GoScopeProcessorBase.java
/*
 * Copyright 2013-2014 Sergey Ignatov, Alexander Zolotov
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

package com.goide.psi.impl;

import com.goide.psi.GoFunctionOrMethodDeclaration;
import com.goide.psi.GoNamedElement;
import com.intellij.psi.PsiElement;
import com.intellij.psi.ResolveState;
import com.intellij.psi.scope.BaseScopeProcessor;
import com.intellij.util.containers.ContainerUtil;
import com.intellij.util.containers.OrderedSet;
import org.jetbrains.annotations.NotNull;
import org.jetbrains.annotations.Nullable;

import java.util.List;

public abstract class GoScopeProcessorBase extends BaseScopeProcessor {
  @NotNull protected final OrderedSet<GoNamedElement> myResult = new OrderedSet<GoNamedElement>();

  @NotNull protected final PsiElement myOrigin;
  @NotNull private final String myRequestedName;
  protected final boolean myIsCompletion;

  public GoScopeProcessorBase(@NotNull String requestedName, @NotNull PsiElement origin, boolean completion) {
    myRequestedName = requestedName;
    myOrigin = origin;
    myIsCompletion = completion;
  }

  @Override
  public boolean execute(@NotNull PsiElement psiElement, @NotNull ResolveState resolveState) {
    if (psiElement instanceof GoFunctionOrMethodDeclaration) return false;
    if (!(psiElement instanceof GoNamedElement)) return true;
    if (!myIsCompletion && !myRequestedName.equals(((GoNamedElement)psiElement).getName())) return true;
    if (condition(psiElement)) return true;
    if (psiElement.equals(myOrigin)) return true;
    return add((GoNamedElement)psiElement) || myIsCompletion;
  }

  protected boolean add(@NotNull GoNamedElement psiElement) {
    return !myResult.add(psiElement);
  }

  @Nullable
  public GoNamedElement getResult() {
    return ContainerUtil.getFirstItem(myResult);
  }

  @NotNull
  public List<GoNamedElement> getVariants() {
    return myResult;
  }

  protected abstract boolean condition(@NotNull PsiElement element);
}


File: src/com/goide/psi/impl/GoVarReference.java
/*
 * Copyright 2013-2014 Sergey Ignatov, Alexander Zolotov
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

package com.goide.psi.impl;

import com.goide.psi.GoBlock;
import com.goide.psi.GoFunctionOrMethodDeclaration;
import com.goide.psi.GoStatement;
import com.goide.psi.GoVarDefinition;
import com.goide.util.GoUtil;
import com.intellij.psi.PsiElement;
import com.intellij.psi.ResolveState;
import com.intellij.psi.util.PsiTreeUtil;
import com.intellij.util.ArrayUtil;
import com.intellij.util.IncorrectOperationException;
import org.jetbrains.annotations.NotNull;
import org.jetbrains.annotations.Nullable;

public class GoVarReference extends GoCachedReference<GoVarDefinition> {
  private final GoBlock myPotentialStopBlock;

  public GoVarReference(@NotNull GoVarDefinition element) {
    super(element);
    myPotentialStopBlock = PsiTreeUtil.getParentOfType(element, GoBlock.class);
  }

  @Nullable
  @Override
  public PsiElement resolveInner() {
    GoVarProcessor p = new GoVarProcessor(myElement.getText(), myElement, false);
    if (myPotentialStopBlock != null) {
      if (myPotentialStopBlock.getParent() instanceof GoFunctionOrMethodDeclaration) {
        GoReference.processFunctionParameters(myElement, p);
        if (p.getResult() != null) return p.getResult();
      }
      myPotentialStopBlock.processDeclarations(p, ResolveState.initial(), PsiTreeUtil.getParentOfType(myElement, GoStatement.class),
                                               myElement);
    }
    return p.getResult();
  }

  @NotNull
  @Override
  public Object[] getVariants() {
    GoVarProcessor p = new GoVarProcessor(myElement.getText(), myElement, true);
    if (myPotentialStopBlock != null) {
      if (myPotentialStopBlock.getParent() instanceof GoFunctionOrMethodDeclaration) {
        GoReference.processFunctionParameters(myElement, p);
      }
      myPotentialStopBlock.processDeclarations(p, ResolveState.initial(), PsiTreeUtil.getParentOfType(myElement, GoStatement.class),
                                               myElement);
    }
    return ArrayUtil.toObjectArray(p.getVariants());
  }

  @Override
  public PsiElement handleElementRename(String newElementName) throws IncorrectOperationException {
    myElement.replace(GoElementFactory.createVarDefinitionFromText(myElement.getProject(), newElementName));
    return myElement;
  }

  @Override
  public boolean isReferenceTo(PsiElement element) {
    return GoUtil.couldBeReferenceTo(element, myElement) && super.isReferenceTo(element);
  }
}
