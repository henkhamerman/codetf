Refactoring Types: ['Extract Method']
m/intellij/codeInsight/daemon/impl/analysis/GenericsHighlightUtil.java
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
package com.intellij.codeInsight.daemon.impl.analysis;

import com.intellij.codeInsight.daemon.JavaErrorMessages;
import com.intellij.codeInsight.daemon.impl.HighlightInfo;
import com.intellij.codeInsight.daemon.impl.HighlightInfoType;
import com.intellij.codeInsight.daemon.impl.quickfix.QuickFixAction;
import com.intellij.codeInsight.daemon.impl.quickfix.QuickFixActionRegistrarImpl;
import com.intellij.codeInsight.intention.QuickFixFactory;
import com.intellij.openapi.diagnostic.Logger;
import com.intellij.openapi.project.DumbService;
import com.intellij.openapi.project.IndexNotReadyException;
import com.intellij.openapi.project.Project;
import com.intellij.openapi.projectRoots.JavaSdkVersion;
import com.intellij.openapi.projectRoots.JavaVersionService;
import com.intellij.openapi.util.Comparing;
import com.intellij.openapi.util.Pair;
import com.intellij.openapi.util.TextRange;
import com.intellij.pom.java.LanguageLevel;
import com.intellij.psi.*;
import com.intellij.psi.impl.PsiClassImplUtil;
import com.intellij.psi.search.GlobalSearchScope;
import com.intellij.psi.search.PsiShortNamesCache;
import com.intellij.psi.search.searches.ReferencesSearch;
import com.intellij.psi.search.searches.SuperMethodsSearch;
import com.intellij.psi.util.*;
import com.intellij.util.ArrayUtilRt;
import com.intellij.util.containers.ContainerUtil;
import com.intellij.util.containers.HashMap;
import com.intellij.util.containers.HashSet;
import gnu.trove.THashMap;
import gnu.trove.THashSet;
import org.jetbrains.annotations.NonNls;
import org.jetbrains.annotations.NotNull;
import org.jetbrains.annotations.Nullable;

import java.util.*;

/**
 * @author cdr
 */
public class GenericsHighlightUtil {
  private static final Logger LOG = Logger.getInstance("#com.intellij.codeInsight.daemon.impl.analysis.GenericsHighlightUtil");

  private static final QuickFixFactory QUICK_FIX_FACTORY = QuickFixFactory.getInstance();

  private GenericsHighlightUtil() { }

  @Nullable
  public static HighlightInfo checkInferredTypeArguments(PsiTypeParameterListOwner listOwner,
                                                         PsiElement call,
                                                         PsiSubstitutor substitutor) {
    return checkInferredTypeArguments(listOwner.getTypeParameters(), call, substitutor);
  }

  @Nullable
  public static HighlightInfo checkInferredTypeArguments(PsiTypeParameter[] typeParameters,
                                                         PsiElement call,
                                                         PsiSubstitutor substitutor) {
    final Pair<PsiTypeParameter, PsiType> inferredTypeArgument = GenericsUtil.findTypeParameterWithBoundError(typeParameters, substitutor, call, false);
    if (inferredTypeArgument != null) {
      final PsiType extendsType = inferredTypeArgument.second;
      final PsiTypeParameter typeParameter = inferredTypeArgument.first;
      PsiClass boundClass = extendsType instanceof PsiClassType ? ((PsiClassType)extendsType).resolve() : null;

      @NonNls String messageKey = boundClass == null || typeParameter.isInterface() == boundClass.isInterface()
                                  ? "generics.inferred.type.for.type.parameter.is.not.within.its.bound.extend"
                                  : "generics.inferred.type.for.type.parameter.is.not.within.its.bound.implement";

      String description = JavaErrorMessages.message(
        messageKey,
        HighlightUtil.formatClass(typeParameter),
        JavaHighlightUtil.formatType(extendsType),
        JavaHighlightUtil.formatType(substitutor.substitute(typeParameter))
      );
      return HighlightInfo.newHighlightInfo(HighlightInfoType.ERROR).range(call).descriptionAndTooltip(description).create();
    }

    return null;
  }

  @Nullable
  public static HighlightInfo checkParameterizedReferenceTypeArguments(final PsiElement resolved,
                                                                       final PsiJavaCodeReferenceElement referenceElement,
                                                                       final PsiSubstitutor substitutor,
                                                                       @NotNull JavaSdkVersion javaSdkVersion) {
    if (!(resolved instanceof PsiTypeParameterListOwner)) return null;
    final PsiTypeParameterListOwner typeParameterListOwner = (PsiTypeParameterListOwner)resolved;
    return checkReferenceTypeArgumentList(typeParameterListOwner, referenceElement.getParameterList(), substitutor, true, javaSdkVersion);
  }

  @Nullable
  public static HighlightInfo checkReferenceTypeArgumentList(final PsiTypeParameterListOwner typeParameterListOwner,
                                                             final PsiReferenceParameterList referenceParameterList,
                                                             final PsiSubstitutor substitutor,
                                                             boolean registerIntentions,
                                                             @NotNull JavaSdkVersion javaSdkVersion) {
    PsiDiamondType.DiamondInferenceResult inferenceResult = null;
    PsiTypeElement[] referenceElements = null;
    if (referenceParameterList != null) {
      referenceElements = referenceParameterList.getTypeParameterElements();
      if (referenceElements.length == 1 && referenceElements[0].getType() instanceof PsiDiamondType) {
        if (!typeParameterListOwner.hasTypeParameters()) {
          final String description = JavaErrorMessages.message("generics.diamond.not.applicable");
          return HighlightInfo.newHighlightInfo(HighlightInfoType.ERROR).range(referenceElements[0]).descriptionAndTooltip(description).create();
        }
        inferenceResult = ((PsiDiamondType)referenceElements[0].getType()).resolveInferredTypes();
        final String errorMessage = inferenceResult.getErrorMessage();
        if (errorMessage != null) {
          final PsiType expectedType = detectExpectedType(referenceParameterList);
          if (!(inferenceResult.failedToInfer() && expectedType instanceof PsiClassType && ((PsiClassType)expectedType).isRaw())) {
            return HighlightInfo
              .newHighlightInfo(HighlightInfoType.ERROR).range(referenceElements[0]).descriptionAndTooltip(errorMessage).create();
          }
        }
      }
    }

    final PsiTypeParameter[] typeParameters = typeParameterListOwner.getTypeParameters();
    final int targetParametersNum = typeParameters.length;
    final int refParametersNum = referenceParameterList == null ? 0 : referenceParameterList.getTypeArguments().length;
    if (targetParametersNum != refParametersNum && refParametersNum != 0) {
      final String description;
      if (targetParametersNum == 0) {
        if (PsiTreeUtil.getParentOfType(referenceParameterList, PsiCall.class) != null &&
            typeParameterListOwner instanceof PsiMethod &&
            (javaSdkVersion.isAtLeast(JavaSdkVersion.JDK_1_7) || hasSuperMethodsWithTypeParams((PsiMethod)typeParameterListOwner))) {
          description = null;
        }
        else {
          description = JavaErrorMessages.message(
            "generics.type.or.method.does.not.have.type.parameters",
            typeParameterListOwnerCategoryDescription(typeParameterListOwner),
            typeParameterListOwnerDescription(typeParameterListOwner)
          );
        }
      }
      else {
        description = JavaErrorMessages.message("generics.wrong.number.of.type.arguments", refParametersNum, targetParametersNum);
      }

      if (description != null) {
        final HighlightInfo highlightInfo =
          HighlightInfo.newHighlightInfo(HighlightInfoType.ERROR).range(referenceParameterList).descriptionAndTooltip(description).create();
        if (registerIntentions) {
          if (typeParameterListOwner instanceof PsiClass) {
            QuickFixAction.registerQuickFixAction(highlightInfo, QUICK_FIX_FACTORY.createChangeClassSignatureFromUsageFix((PsiClass)typeParameterListOwner, referenceParameterList));
          }

          PsiElement grandParent = referenceParameterList.getParent().getParent();
          if (grandParent instanceof PsiTypeElement) {
            PsiElement variable = grandParent.getParent();
            if (variable instanceof PsiVariable) {
              if (targetParametersNum == 0) {
                QuickFixAction.registerQuickFixAction(highlightInfo, QUICK_FIX_FACTORY.createRemoveTypeArgumentsFix(variable));
              }
              registerVariableParameterizedTypeFixes(highlightInfo, (PsiVariable)variable, referenceParameterList, javaSdkVersion);
            }
          }
        }
        return highlightInfo;
      }
    }

    // bounds check
    if (targetParametersNum > 0 && refParametersNum != 0) {
      if (inferenceResult != null) {
        final PsiType[] types = inferenceResult.getTypes();
        for (int i = 0; i < typeParameters.length; i++) {
          final PsiType type = types[i];
          final HighlightInfo highlightInfo = checkTypeParameterWithinItsBound(typeParameters[i], substitutor, type, referenceElements[0], referenceParameterList);
          if (highlightInfo != null) return highlightInfo;
        }
      }
      else {
        for (int i = 0; i < typeParameters.length; i++) {
          final PsiTypeElement typeElement = referenceElements[i];
          final HighlightInfo highlightInfo = checkTypeParameterWithinItsBound(typeParameters[i], substitutor, typeElement.getType(), typeElement, referenceParameterList);
          if (highlightInfo != null) return highlightInfo;
        }
      }
    }

    return null;
  }

  private static boolean hasSuperMethodsWithTypeParams(PsiMethod method) {
    for (PsiMethod superMethod : method.findDeepestSuperMethods()) {
      if (superMethod.hasTypeParameters()) return true;
    }
    return false;
  }

  private static PsiType detectExpectedType(PsiReferenceParameterList referenceParameterList) {
    final PsiNewExpression newExpression = PsiTreeUtil.getParentOfType(referenceParameterList, PsiNewExpression.class);
    LOG.assertTrue(newExpression != null);
    final PsiElement parent = newExpression.getParent();
    PsiType expectedType = null;
    if (parent instanceof PsiVariable && newExpression.equals(((PsiVariable)parent).getInitializer())) {
      expectedType = ((PsiVariable)parent).getType();
    }
    else if (parent instanceof PsiAssignmentExpression && newExpression.equals(((PsiAssignmentExpression)parent).getRExpression())) {
      expectedType = ((PsiAssignmentExpression)parent).getLExpression().getType();
    }
    else if (parent instanceof PsiReturnStatement) {
      PsiElement method = PsiTreeUtil.getParentOfType(parent, PsiMethod.class, PsiLambdaExpression.class);
      if (method instanceof PsiMethod) {
        expectedType = ((PsiMethod)method).getReturnType();
      }
    }
    else if (parent instanceof PsiExpressionList) {
      final PsiElement pParent = parent.getParent();
      if (pParent instanceof PsiCallExpression && parent.equals(((PsiCallExpression)pParent).getArgumentList())) {
        final PsiMethod method = ((PsiCallExpression)pParent).resolveMethod();
        if (method != null) {
          final PsiExpression[] expressions = ((PsiCallExpression)pParent).getArgumentList().getExpressions();
          final int idx = ArrayUtilRt.find(expressions, newExpression);
          if (idx > -1) {
            final PsiParameterList parameterList = method.getParameterList();
            if (idx < parameterList.getParametersCount()) {
              expectedType = parameterList.getParameters()[idx].getType();
            }
          }
        }
      }
    }
    return expectedType;
  }

  @Nullable
  private static HighlightInfo checkTypeParameterWithinItsBound(PsiTypeParameter classParameter,
                                                                final PsiSubstitutor substitutor,
                                                                final PsiType type,
                                                                final PsiElement typeElement2Highlight,
                                                                PsiReferenceParameterList referenceParameterList) {
    final PsiClass referenceClass = type instanceof PsiClassType ? ((PsiClassType)type).resolve() : null;
    final PsiType psiType = substitutor.substitute(classParameter);
    if (psiType instanceof PsiClassType && !(PsiUtil.resolveClassInType(psiType) instanceof PsiTypeParameter)) {
      if (GenericsUtil.checkNotInBounds(type, psiType, referenceParameterList)) {
        final String description = "Actual type argument and inferred type contradict each other";
        return HighlightInfo.newHighlightInfo(HighlightInfoType.ERROR).range(typeElement2Highlight).descriptionAndTooltip(description).create();
      }
    }

    final PsiClassType[] bounds = classParameter.getSuperTypes();
    for (PsiClassType type1 : bounds) {
      PsiType bound = substitutor.substitute(type1);
      if (!bound.equalsToText(CommonClassNames.JAVA_LANG_OBJECT) && GenericsUtil.checkNotInBounds(type, bound, referenceParameterList)) {
        PsiClass boundClass = bound instanceof PsiClassType ? ((PsiClassType)bound).resolve() : null;

        @NonNls final String messageKey = boundClass == null || referenceClass == null || referenceClass.isInterface() == boundClass.isInterface()
                                          ? "generics.type.parameter.is.not.within.its.bound.extend"
                                          : "generics.type.parameter.is.not.within.its.bound.implement";

        String description = JavaErrorMessages.message(messageKey,
                                                       referenceClass != null ? HighlightUtil.formatClass(referenceClass) : type.getPresentableText(),
                                                       JavaHighlightUtil.formatType(bound));

        final HighlightInfo info =
          HighlightInfo.newHighlightInfo(HighlightInfoType.ERROR).range(typeElement2Highlight).descriptionAndTooltip(description).create();
        if (bound instanceof PsiClassType && referenceClass != null && info != null) {
          QuickFixAction
            .registerQuickFixAction(info, QUICK_FIX_FACTORY.createExtendsListFix(referenceClass, (PsiClassType)bound, true),
                                    null);
        }
        return info;
      }
    }
    return null;
  }

  private static String typeParameterListOwnerDescription(final PsiTypeParameterListOwner typeParameterListOwner) {
    if (typeParameterListOwner instanceof PsiClass) {
      return HighlightUtil.formatClass((PsiClass)typeParameterListOwner);
    }
    else if (typeParameterListOwner instanceof PsiMethod) {
      return JavaHighlightUtil.formatMethod((PsiMethod)typeParameterListOwner);
    }
    else {
      LOG.error("Unknown " + typeParameterListOwner);
      return "?";
    }
  }

  private static String typeParameterListOwnerCategoryDescription(final PsiTypeParameterListOwner typeParameterListOwner) {
    if (typeParameterListOwner instanceof PsiClass) {
      return JavaErrorMessages.message("generics.holder.type");
    }
    else if (typeParameterListOwner instanceof PsiMethod) {
      return JavaErrorMessages.message("generics.holder.method");
    }
    else {
      LOG.error("Unknown " + typeParameterListOwner);
      return "?";
    }
  }

  @Nullable
  public static HighlightInfo checkElementInTypeParameterExtendsList(@NotNull PsiReferenceList referenceList,
                                                                     @NotNull PsiClass aClass,
                                                                     @NotNull JavaResolveResult resolveResult,
                                                                     @NotNull PsiElement element,
                                                                     @NotNull LanguageLevel languageLevel) {
    final PsiJavaCodeReferenceElement[] referenceElements = referenceList.getReferenceElements();
    PsiClass extendFrom = (PsiClass)resolveResult.getElement();
    if (extendFrom == null) return null;
    HighlightInfo errorResult = null;
    if (!extendFrom.isInterface() && referenceElements.length != 0 && element != referenceElements[0]) {
      String description = JavaErrorMessages.message("interface.expected");
      errorResult = HighlightInfo.newHighlightInfo(HighlightInfoType.ERROR).range(element).descriptionAndTooltip(description).create();
      PsiClassType type =
        JavaPsiFacade.getInstance(aClass.getProject()).getElementFactory().createType(extendFrom, resolveResult.getSubstitutor());
      QuickFixAction.registerQuickFixAction(errorResult, QUICK_FIX_FACTORY.createMoveBoundClassToFrontFix(aClass, type), null);
    }
    else if (referenceElements.length != 0 && element != referenceElements[0] && referenceElements[0].resolve() instanceof PsiTypeParameter) {
      final String description = JavaErrorMessages.message("type.parameter.cannot.be.followed.by.other.bounds");
      errorResult = HighlightInfo.newHighlightInfo(HighlightInfoType.ERROR).range(element).descriptionAndTooltip(description).create();
      PsiClassType type =
        JavaPsiFacade.getInstance(aClass.getProject()).getElementFactory().createType(extendFrom, resolveResult.getSubstitutor());
      QuickFixAction.registerQuickFixAction(errorResult, QUICK_FIX_FACTORY.createExtendsListFix(aClass, type, false), null);
    }
    if (errorResult == null && languageLevel.isAtLeast(LanguageLevel.JDK_1_7) &&
        referenceElements.length > 1) {
      //todo suppress erased methods which come from the same class
      final Collection<HighlightInfo> result = checkOverrideEquivalentMethods(languageLevel, aClass);
      return result != null && result.size() > 0 ? result.iterator().next() : null;
    }
    return errorResult;
  }

  public static HighlightInfo checkInterfaceMultipleInheritance(PsiClass aClass) {
    final PsiClassType[] types = aClass.getSuperTypes();
    if (types.length < 2) return null;
    Map<PsiClass, PsiSubstitutor> inheritedClasses = new HashMap<PsiClass, PsiSubstitutor>();
    final TextRange textRange = HighlightNamesUtil.getClassDeclarationTextRange(aClass);
    return checkInterfaceMultipleInheritance(aClass,
                                             aClass,
                                             PsiSubstitutor.EMPTY, inheritedClasses,
                                             new HashSet<PsiClass>(), textRange);
  }

  private static HighlightInfo checkInterfaceMultipleInheritance(PsiClass aClass,
                                                                 PsiElement place, 
                                                                 PsiSubstitutor derivedSubstitutor,
                                                                 Map<PsiClass, PsiSubstitutor> inheritedClasses,
                                                                 Set<PsiClass> visited,
                                                                 TextRange textRange) {
    final PsiClassType[] superTypes = aClass.getSuperTypes();
    for (PsiClassType superType : superTypes) {
      superType = PsiClassImplUtil.correctType(superType, place.getResolveScope());
      if (superType == null) continue;
      final PsiClassType.ClassResolveResult result = superType.resolveGenerics();
      final PsiClass superClass = result.getElement();
      if (superClass == null || visited.contains(superClass)) continue;
      PsiSubstitutor superTypeSubstitutor = result.getSubstitutor();
      superTypeSubstitutor = MethodSignatureUtil.combineSubstitutors(superTypeSubstitutor, derivedSubstitutor);

      final PsiSubstitutor inheritedSubstitutor = inheritedClasses.get(superClass);
      if (inheritedSubstitutor != null) {
        final PsiTypeParameter[] typeParameters = superClass.getTypeParameters();
        for (PsiTypeParameter typeParameter : typeParameters) {
          PsiType type1 = inheritedSubstitutor.substitute(typeParameter);
          PsiType type2 = superTypeSubstitutor.substitute(typeParameter);

          if (!Comparing.equal(type1, type2)) {
            String description = JavaErrorMessages.message("generics.cannot.be.inherited.with.different.type.arguments",
                                                           HighlightUtil.formatClass(superClass),
                                                           JavaHighlightUtil.formatType(type1),
                                                           JavaHighlightUtil.formatType(type2));
            return HighlightInfo.newHighlightInfo(HighlightInfoType.ERROR).range(textRange).descriptionAndTooltip(description).create();
          }
        }
      }
      inheritedClasses.put(superClass, superTypeSubstitutor);
      visited.add(superClass);
      final HighlightInfo highlightInfo = checkInterfaceMultipleInheritance(superClass, place, superTypeSubstitutor, inheritedClasses, visited, textRange);
      visited.remove(superClass);

      if (highlightInfo != null) return highlightInfo;
    }
    return null;
  }

  public static Collection<HighlightInfo> checkOverrideEquivalentMethods(@NotNull LanguageLevel languageLevel,
                                                                         @NotNull PsiClass aClass) {
    List<HighlightInfo> result = new ArrayList<HighlightInfo>();
    final Collection<HierarchicalMethodSignature> signaturesWithSupers = aClass.getVisibleSignatures();
    PsiManager manager = aClass.getManager();
    Map<MethodSignature, MethodSignatureBackedByPsiMethod> sameErasureMethods =
      new THashMap<MethodSignature, MethodSignatureBackedByPsiMethod>(MethodSignatureUtil.METHOD_PARAMETERS_ERASURE_EQUALITY);

    final Set<MethodSignature> foundProblems = new THashSet<MethodSignature>(MethodSignatureUtil.METHOD_PARAMETERS_ERASURE_EQUALITY);
    for (HierarchicalMethodSignature signature : signaturesWithSupers) {
      HighlightInfo info = checkSameErasureNotSubSignatureInner(signature, manager, aClass, sameErasureMethods);
      if (info != null && foundProblems.add(signature)) {
        result.add(info);
      }
      if (aClass instanceof PsiTypeParameter) {
        info = HighlightMethodUtil.checkMethodIncompatibleReturnType(signature, signature.getSuperSignatures(), true, HighlightNamesUtil.getClassDeclarationTextRange(aClass), languageLevel);
        if (info != null) {
          result.add(info);
        }
      }
    }

    return result.isEmpty() ? null : result;
  }

  static HighlightInfo checkDefaultMethodOverrideEquivalentToObjectNonPrivate(@NotNull LanguageLevel languageLevel,
                                                                              @NotNull PsiClass aClass,
                                                                              @NotNull PsiMethod method,
                                                                              @NotNull PsiElement methodIdentifier) {
    if (languageLevel.isAtLeast(LanguageLevel.JDK_1_8) && aClass.isInterface() && method.hasModifierProperty(PsiModifier.DEFAULT)) {
      HierarchicalMethodSignature sig = method.getHierarchicalMethodSignature();
      for (HierarchicalMethodSignature methodSignature : sig.getSuperSignatures()) {
        final PsiMethod objectMethod = methodSignature.getMethod();
        final PsiClass containingClass = objectMethod.getContainingClass();
        if (containingClass != null && CommonClassNames.JAVA_LANG_OBJECT.equals(containingClass.getQualifiedName()) && objectMethod.hasModifierProperty(PsiModifier.PUBLIC)) {
          return HighlightInfo.newHighlightInfo(HighlightInfoType.ERROR)
            .descriptionAndTooltip("Default method '" + sig.getName() + "' overrides a member of 'java.lang.Object'")
            .range(methodIdentifier)
            .create();
        }
      }
    }
    return null;
  }

  static HighlightInfo checkUnrelatedDefaultMethods(@NotNull PsiClass aClass,
                                                            @NotNull Collection<HierarchicalMethodSignature> signaturesWithSupers,
                                                            @NotNull PsiIdentifier classIdentifier) {
    for (HierarchicalMethodSignature methodSignature : signaturesWithSupers) {
      final PsiMethod method = methodSignature.getMethod();
      final boolean isAbstract = method.hasModifierProperty(PsiModifier.ABSTRACT);
      if (method.hasModifierProperty(PsiModifier.DEFAULT) || isAbstract) {
        final PsiClass containingClass = method.getContainingClass();
        List<HierarchicalMethodSignature> superSignatures = methodSignature.getSuperSignatures();
        if (!superSignatures.isEmpty()) {
          for (HierarchicalMethodSignature signature : superSignatures) {
            final PsiMethod superMethod = signature.getMethod();
            final PsiClass superContainingClass = superMethod.getContainingClass();
            if (containingClass != null && superContainingClass != null && !InheritanceUtil.isInheritorOrSelf(containingClass, superContainingClass, true)) {
              final boolean isDefault = superMethod.hasModifierProperty(PsiModifier.DEFAULT);
              if (!aClass.hasModifierProperty(PsiModifier.ABSTRACT) && !isDefault && !isAbstract) {
                final String message = JavaErrorMessages.message(
                  aClass instanceof PsiEnumConstantInitializer ? "enum.constant.should.implement.method" : "class.must.be.abstract",
                  HighlightUtil.formatClass(superContainingClass),
                  JavaHighlightUtil.formatMethod(superMethod),
                  HighlightUtil.formatClass(superContainingClass, false));
                final HighlightInfo info = HighlightInfo.newHighlightInfo(HighlightInfoType.ERROR)
                  .range(classIdentifier).descriptionAndTooltip(message)
                  .create();
                QuickFixAction.registerQuickFixAction(info, QUICK_FIX_FACTORY.createImplementMethodsFix(aClass));
                return info;
              }

              if (isDefault || !isAbstract && superMethod.hasModifierProperty(PsiModifier.ABSTRACT)) {
                final String message = isDefault
                                       ? " inherits unrelated defaults for "
                                       : " inherits abstract and default for ";
                final String inheritUnrelatedDefaultsMessage = HighlightUtil.formatClass(aClass) +
                                                               message +
                                                               JavaHighlightUtil.formatMethod(method) +
                                                               " from types " +
                                                               HighlightUtil.formatClass(containingClass) +
                                                               " and " +
                                                               HighlightUtil.formatClass(superContainingClass);
                final HighlightInfo info = HighlightInfo
                  .newHighlightInfo(HighlightInfoType.ERROR).range(classIdentifier).descriptionAndTooltip(inheritUnrelatedDefaultsMessage)
                  .create();
                QuickFixAction.registerQuickFixAction(info, QUICK_FIX_FACTORY.createImplementMethodsFix(aClass));
                return info;
              }
            }
          }
        }
      }
    }
    return null;
  }

  @Nullable
  private static HighlightInfo checkSameErasureNotSubSignatureInner(@NotNull HierarchicalMethodSignature signature,
                                                                    @NotNull PsiManager manager,
                                                                    @NotNull PsiClass aClass,
                                                                    @NotNull Map<MethodSignature, MethodSignatureBackedByPsiMethod> sameErasureMethods) {
    PsiMethod method = signature.getMethod();
    JavaPsiFacade facade = JavaPsiFacade.getInstance(manager.getProject());
    if (!facade.getResolveHelper().isAccessible(method, aClass, null)) return null;
    MethodSignature signatureToErase = method.getSignature(PsiSubstitutor.EMPTY);
    MethodSignatureBackedByPsiMethod sameErasure = sameErasureMethods.get(signatureToErase);
    HighlightInfo info;
    if (sameErasure != null) {
      if (aClass instanceof PsiTypeParameter ||
          MethodSignatureUtil.findMethodBySuperMethod(aClass, sameErasure.getMethod(), false) != null ||
          !(InheritanceUtil.isInheritorOrSelf(sameErasure.getMethod().getContainingClass(), method.getContainingClass(), true) ||
            InheritanceUtil.isInheritorOrSelf(method.getContainingClass(), sameErasure.getMethod().getContainingClass(), true))) {
        info = checkSameErasureNotSubSignatureOrSameClass(sameErasure, signature, aClass, method);
        if (info != null) return info;
      }
    }
    else {
      sameErasureMethods.put(signatureToErase, signature);
    }
    List<HierarchicalMethodSignature> supers = signature.getSuperSignatures();
    for (HierarchicalMethodSignature superSignature : supers) {
      info = checkSameErasureNotSubSignatureInner(superSignature, manager, aClass, sameErasureMethods);
      if (info != null) return info;

      if (superSignature.isRaw() && !signature.isRaw()) {
        final PsiType[] parameterTypes = signature.getParameterTypes();
        PsiType[] erasedTypes = superSignature.getErasedParameterTypes();
        for (int i = 0; i < erasedTypes.length; i++) {
          if (!Comparing.equal(parameterTypes[i], erasedTypes[i])) {
            return getSameErasureMessage(false, method, superSignature.getMethod(),
                                         HighlightNamesUtil.getClassDeclarationTextRange(aClass));
          }
        }
      }

    }
    return null;
  }

  @Nullable
  private static HighlightInfo checkSameErasureNotSubSignatureOrSameClass(final MethodSignatureBackedByPsiMethod signatureToCheck,
                                                                          final HierarchicalMethodSignature superSignature,
                                                                          final PsiClass aClass,
                                                                          final PsiMethod superMethod) {
    final PsiMethod checkMethod = signatureToCheck.getMethod();
    if (superMethod.equals(checkMethod)) return null;
    PsiClass checkContainingClass = checkMethod.getContainingClass();
    LOG.assertTrue(checkContainingClass != null);
    PsiClass superContainingClass = superMethod.getContainingClass();
    boolean checkEqualsSuper = checkContainingClass.equals(superContainingClass);
    if (checkMethod.isConstructor()) {
      if (!superMethod.isConstructor() || !checkEqualsSuper) return null;
    }
    else if (superMethod.isConstructor()) return null;

    final boolean atLeast17 = JavaVersionService.getInstance().isAtLeast(aClass, JavaSdkVersion.JDK_1_7);
    if (checkMethod.hasModifierProperty(PsiModifier.STATIC) && !checkEqualsSuper && !atLeast17) {
      return null;
    }

    if (superMethod.hasModifierProperty(PsiModifier.STATIC) && superContainingClass != null &&
        superContainingClass.isInterface() && PsiUtil.isLanguageLevel8OrHigher(superContainingClass)) {
      return null;
    }

    final PsiType retErasure1 = TypeConversionUtil.erasure(checkMethod.getReturnType());
    final PsiType retErasure2 = TypeConversionUtil.erasure(superMethod.getReturnType());

    boolean differentReturnTypeErasure = !Comparing.equal(retErasure1, retErasure2);
    if (checkEqualsSuper && atLeast17) {
      if (retErasure1 != null && retErasure2 != null) {
        differentReturnTypeErasure = !TypeConversionUtil.isAssignable(retErasure1, retErasure2);
      }
      else {
        differentReturnTypeErasure = !(retErasure1 == null && retErasure2 == null);
      }
    }

    if (differentReturnTypeErasure &&
        !TypeConversionUtil.isVoidType(retErasure1) &&
        !TypeConversionUtil.isVoidType(retErasure2) &&
        !(checkEqualsSuper && Arrays.equals(superSignature.getParameterTypes(), signatureToCheck.getParameterTypes())) &&
        !atLeast17) {
      int idx = 0;
      final PsiType[] erasedTypes = signatureToCheck.getErasedParameterTypes();
      boolean erasure = erasedTypes.length > 0;
      for (PsiType type : superSignature.getParameterTypes()) {
        erasure &= Comparing.equal(type, erasedTypes[idx]);
        idx++;
      }

      if (!erasure) return null;
    }

    if (!checkEqualsSuper && MethodSignatureUtil.isSubsignature(superSignature, signatureToCheck)) {
      return null;
    }
    if (superContainingClass != null && !superContainingClass.isInterface() && checkContainingClass.isInterface() && !aClass.equals(superContainingClass)) return null;
    if (aClass.equals(checkContainingClass)) {
      boolean sameClass = aClass.equals(superContainingClass);
      return getSameErasureMessage(sameClass, checkMethod, superMethod, HighlightNamesUtil.getMethodDeclarationTextRange(checkMethod));
    }
    else {
      return getSameErasureMessage(false, checkMethod, superMethod, HighlightNamesUtil.getClassDeclarationTextRange(aClass));
    }
  }

  private static HighlightInfo getSameErasureMessage(final boolean sameClass, @NotNull PsiMethod method, @NotNull PsiMethod superMethod,
                                                     TextRange textRange) {
     @NonNls final String key = sameClass ? "generics.methods.have.same.erasure" :
                               method.hasModifierProperty(PsiModifier.STATIC) ?
                               "generics.methods.have.same.erasure.hide" :
                               "generics.methods.have.same.erasure.override";
    String description = JavaErrorMessages.message(key, HighlightMethodUtil.createClashMethodMessage(method, superMethod, !sameClass));
    return HighlightInfo.newHighlightInfo(HighlightInfoType.ERROR).range(textRange).descriptionAndTooltip(description).create();
  }

  public static HighlightInfo checkTypeParameterInstantiation(PsiNewExpression expression) {
    PsiJavaCodeReferenceElement classReference = expression.getClassOrAnonymousClassReference();
    if (classReference == null) return null;
    final JavaResolveResult result = classReference.advancedResolve(false);
    final PsiElement element = result.getElement();
    if (element instanceof PsiTypeParameter) {
      String description = JavaErrorMessages.message("generics.type.parameter.cannot.be.instantiated",
                                                     HighlightUtil.formatClass((PsiTypeParameter)element));
      return HighlightInfo.newHighlightInfo(HighlightInfoType.ERROR).range(classReference).descriptionAndTooltip(description).create();
    }
    return null;
  }

  public static HighlightInfo checkWildcardUsage(PsiTypeElement typeElement) {
    PsiType type = typeElement.getType();
    if (type instanceof PsiWildcardType) {
      if (typeElement.getParent() instanceof PsiReferenceParameterList) {
        PsiElement parent = typeElement.getParent().getParent();
        LOG.assertTrue(parent instanceof PsiJavaCodeReferenceElement, parent);
        PsiElement refParent = parent.getParent();
        if (refParent instanceof PsiAnonymousClass) refParent = refParent.getParent();
        if (refParent instanceof PsiNewExpression) {
          PsiNewExpression newExpression = (PsiNewExpression)refParent;
          if (!(newExpression.getType() instanceof PsiArrayType)) {
            String description = JavaErrorMessages.message("wildcard.type.cannot.be.instantiated", JavaHighlightUtil.formatType(type));
            return HighlightInfo.newHighlightInfo(HighlightInfoType.ERROR).range(typeElement).descriptionAndTooltip(description).create();
          }
        }
        else if (refParent instanceof PsiReferenceList) {
          PsiElement refPParent = refParent.getParent();
          if (!(refPParent instanceof PsiTypeParameter) || refParent != ((PsiTypeParameter)refPParent).getExtendsList()) {
            String description = JavaErrorMessages.message("generics.wildcard.not.expected");
            return HighlightInfo.newHighlightInfo(HighlightInfoType.ERROR).range(typeElement).descriptionAndTooltip(description).create();
          }
        }
      }
      else {
        String description = JavaErrorMessages.message("generics.wildcards.may.be.used.only.as.reference.parameters");
        return HighlightInfo.newHighlightInfo(HighlightInfoType.ERROR).range(typeElement).descriptionAndTooltip(description).create();
      }
    }

    return null;
  }

  public static HighlightInfo checkReferenceTypeUsedAsTypeArgument(final PsiTypeElement typeElement) {
    final PsiType type = typeElement.getType();
    if (type != PsiType.NULL && type instanceof PsiPrimitiveType ||
        type instanceof PsiWildcardType && ((PsiWildcardType)type).getBound() instanceof PsiPrimitiveType) {
      final PsiElement element = new PsiMatcherImpl(typeElement)
        .parent(PsiMatchers.hasClass(PsiReferenceParameterList.class))
        .parent(PsiMatchers.hasClass(PsiJavaCodeReferenceElement.class, PsiNewExpression.class))
        .getElement();
      if (element == null) return null;

      String description = JavaErrorMessages.message("generics.type.argument.cannot.be.of.primitive.type");
      final HighlightInfo highlightInfo =
        HighlightInfo.newHighlightInfo(HighlightInfoType.ERROR).range(typeElement).descriptionAndTooltip(description).create();
      PsiType toConvert = type;
      if (type instanceof PsiWildcardType) {
        toConvert = ((PsiWildcardType)type).getBound();
      }
      if (toConvert instanceof PsiPrimitiveType) {
        final PsiClassType boxedType = ((PsiPrimitiveType)toConvert).getBoxedType(typeElement);
        if (boxedType != null) {
          QuickFixAction.registerQuickFixAction(highlightInfo,
                                                QUICK_FIX_FACTORY.createReplacePrimitiveWithBoxedTypeAction(typeElement, toConvert.getPresentableText(), ((PsiPrimitiveType)toConvert).getBoxedTypeName()));
        }
      }
      return highlightInfo;
    }

    return null;
  }

  @Nullable
  public static HighlightInfo checkForeachLoopParameterType(PsiForeachStatement statement) {
    final PsiParameter parameter = statement.getIterationParameter();
    final PsiExpression expression = statement.getIteratedValue();
    if (expression == null || expression.getType() == null) return null;
    final PsiType itemType = JavaGenericsUtil.getCollectionItemType(expression);
    if (itemType == null) {
      String description = JavaErrorMessages.message("foreach.not.applicable",
                                                     JavaHighlightUtil.formatType(expression.getType()));
      return HighlightInfo.newHighlightInfo(HighlightInfoType.ERROR).range(expression).descriptionAndTooltip(description).create();
    }
    final int start = parameter.getTextRange().getStartOffset();
    final int end = expression.getTextRange().getEndOffset();
    final PsiType parameterType = parameter.getType();
    HighlightInfo highlightInfo = HighlightUtil.checkAssignability(parameterType, itemType, null, new TextRange(start, end), 0);
    if (highlightInfo != null) {
      HighlightUtil.registerChangeVariableTypeFixes(parameter, itemType, expression, highlightInfo);
    }
    return highlightInfo;
  }

  //http://docs.oracle.com/javase/specs/jls/se7/html/jls-8.html#jls-8.9.2
  @Nullable
  public static HighlightInfo checkAccessStaticFieldFromEnumConstructor(@NotNull PsiReferenceExpression expr, @NotNull JavaResolveResult result) {
    final PsiElement resolved = result.getElement();

    if (!(resolved instanceof PsiField)) return null;
    if (!((PsiModifierListOwner)resolved).hasModifierProperty(PsiModifier.STATIC)) return null;
    if (expr.getParent() instanceof PsiSwitchLabelStatement) return null;
    final PsiMember constructorOrInitializer = PsiUtil.findEnclosingConstructorOrInitializer(expr);
    if (constructorOrInitializer == null) return null;
    if (constructorOrInitializer.hasModifierProperty(PsiModifier.STATIC)) return null;
    final PsiClass aClass = constructorOrInitializer instanceof PsiEnumConstantInitializer ? 
                            (PsiClass)constructorOrInitializer : constructorOrInitializer.getContainingClass();
    if (aClass == null || !(aClass.isEnum() || aClass instanceof PsiEnumConstantInitializer)) return null;
    final PsiField field = (PsiField)resolved;
    if (aClass instanceof PsiEnumConstantInitializer) {
      if (field.getContainingClass() != aClass.getSuperClass()) return null;
    } else if (field.getContainingClass() != aClass) return null;


    if (!JavaVersionService.getInstance().isAtLeast(field, JavaSdkVersion.JDK_1_6)) {
      final PsiType type = field.getType();
      if (type instanceof PsiClassType && ((PsiClassType)type).resolve() == aClass) return null;
    }

    if (PsiUtil.isCompileTimeConstant(field)) return null;

    String description = JavaErrorMessages.message(
      "illegal.to.access.static.member.from.enum.constructor.or.instance.initializer",
      HighlightMessageUtil.getSymbolName(resolved, result.getSubstitutor())
    );

    return HighlightInfo.newHighlightInfo(HighlightInfoType.ERROR).range(expr).descriptionAndTooltip(description).create();
  }

  @Nullable
  public static HighlightInfo checkEnumInstantiation(PsiElement expression, PsiClass aClass) {
    if (aClass != null && aClass.isEnum() && 
        (!(expression instanceof PsiNewExpression) ||
         ((PsiNewExpression)expression).getArrayDimensions().length == 0 && ((PsiNewExpression)expression).getArrayInitializer() == null)) {
      String description = JavaErrorMessages.message("enum.types.cannot.be.instantiated");
      return HighlightInfo.newHighlightInfo(HighlightInfoType.ERROR).range(expression).descriptionAndTooltip(description).create();
    }
    return null;
  }

  @Nullable
  public static HighlightInfo checkGenericArrayCreation(PsiElement element, PsiType type) {
    if (type instanceof PsiArrayType) {
      if (!JavaGenericsUtil.isReifiableType(((PsiArrayType)type).getComponentType())) {
        String description = JavaErrorMessages.message("generic.array.creation");
        return HighlightInfo.newHighlightInfo(HighlightInfoType.ERROR).range(element).descriptionAndTooltip(description).create();
      }
    }

    return null;
  }

  private static final MethodSignature ourValuesEnumSyntheticMethod = MethodSignatureUtil.createMethodSignature("values",
                                                                                                                PsiType.EMPTY_ARRAY,
                                                                                                                PsiTypeParameter.EMPTY_ARRAY,
                                                                                                                PsiSubstitutor.EMPTY);

  public static boolean isEnumSyntheticMethod(MethodSignature methodSignature, Project project) {
    if (methodSignature.equals(ourValuesEnumSyntheticMethod)) return true;
    final PsiType javaLangString = PsiType.getJavaLangString(PsiManager.getInstance(project), GlobalSearchScope.allScope(project));
    final MethodSignature valueOfMethod = MethodSignatureUtil.createMethodSignature("valueOf", new PsiType[]{javaLangString}, PsiTypeParameter.EMPTY_ARRAY,
                                                                                    PsiSubstitutor.EMPTY);
    return valueOfMethod.equals(methodSignature);
  }

  @Nullable
  public static HighlightInfo checkTypeParametersList(PsiTypeParameterList list, PsiTypeParameter[] parameters, @NotNull LanguageLevel level) {
    final PsiElement parent = list.getParent();
    if (parent instanceof PsiClass && ((PsiClass)parent).isEnum()) {
      String description = JavaErrorMessages.message("generics.enum.may.not.have.type.parameters");
      return HighlightInfo.newHighlightInfo(HighlightInfoType.ERROR).range(list).descriptionAndTooltip(description).create();
    }
    if (PsiUtil.isAnnotationMethod(parent)) {
      String description = JavaErrorMessages.message("generics.annotation.members.may.not.have.type.parameters");
      return HighlightInfo.newHighlightInfo(HighlightInfoType.ERROR).range(list).descriptionAndTooltip(description).create();
    }
    if (parent instanceof PsiClass && ((PsiClass)parent).isAnnotationType()) {
      String description = JavaErrorMessages.message("annotation.may.not.have.type.parameters");
      return HighlightInfo.newHighlightInfo(HighlightInfoType.ERROR).range(list).descriptionAndTooltip(description).create();
    }

    for (int i = 0; i < parameters.length; i++) {
      final PsiTypeParameter typeParameter1 = parameters[i];
      final HighlightInfo cyclicInheritance = HighlightClassUtil.checkCyclicInheritance(typeParameter1);
      if (cyclicInheritance != null) return cyclicInheritance;
      String name1 = typeParameter1.getName();
      for (int j = i + 1; j < parameters.length; j++) {
        final PsiTypeParameter typeParameter2 = parameters[j];
        String name2 = typeParameter2.getName();
        if (Comparing.strEqual(name1, name2)) {
          String message = JavaErrorMessages.message("generics.duplicate.type.parameter", name1);
          return HighlightInfo.newHighlightInfo(HighlightInfoType.ERROR).range(typeParameter2).descriptionAndTooltip(message).create();
        }
      }
      if (!level.isAtLeast(LanguageLevel.JDK_1_7)) {
        for (PsiJavaCodeReferenceElement referenceElement : typeParameter1.getExtendsList().getReferenceElements()) {
          final PsiElement resolve = referenceElement.resolve();
          if (resolve instanceof PsiTypeParameter && ArrayUtilRt.find(parameters, resolve) > i) {
            return HighlightInfo.newHighlightInfo(HighlightInfoType.ERROR).range(referenceElement.getTextRange()).descriptionAndTooltip("Illegal forward reference").create();
          }
        }
      }
    }
    return null;
  }

  @Nullable
  public static Collection<HighlightInfo> checkCatchParameterIsClass(PsiParameter parameter) {
    if (!(parameter.getDeclarationScope() instanceof PsiCatchSection)) return null;
    final Collection<HighlightInfo> result = ContainerUtil.newArrayList();

    final List<PsiTypeElement> typeElements = PsiUtil.getParameterTypeElements(parameter);
    for (PsiTypeElement typeElement : typeElements) {
      final PsiClass aClass = PsiUtil.resolveClassInClassTypeOnly(typeElement.getType());
      if (aClass instanceof PsiTypeParameter) {
        final String message = JavaErrorMessages.message("generics.cannot.catch.type.parameters");
        result.add(HighlightInfo.newHighlightInfo(HighlightInfoType.ERROR).range(typeElement).descriptionAndTooltip(message).create());
      }
    }

    return result;
  }

  public static HighlightInfo checkInstanceOfGenericType(PsiInstanceOfExpression expression) {
    final PsiTypeElement checkTypeElement = expression.getCheckType();
    if (checkTypeElement == null) return null;
    PsiElement ref = checkTypeElement.getInnermostComponentReferenceElement();
    while (ref instanceof PsiJavaCodeReferenceElement) {
      final HighlightInfo result = isIllegalForInstanceOf((PsiJavaCodeReferenceElement)ref, checkTypeElement);
      if (result != null) return result;
      ref = ((PsiQualifiedReference)ref).getQualifier();
    }
    return null;
  }

  private static HighlightInfo isIllegalForInstanceOf(PsiJavaCodeReferenceElement ref, final PsiTypeElement typeElement) {
    final PsiElement resolved = ref.resolve();
    if (resolved instanceof PsiTypeParameter) {
      String description = JavaErrorMessages.message("generics.cannot.instanceof.type.parameters");
      return HighlightInfo.newHighlightInfo(HighlightInfoType.ERROR).range(ref).descriptionAndTooltip(description).create();
    }

    if (resolved instanceof PsiClass) {
      final PsiClass containingClass = ((PsiClass)resolved).getContainingClass();
      if (containingClass != null &&
          ref.getQualifier() == null &&
          containingClass.getTypeParameters().length > 0 &&
          !((PsiClass)resolved).hasModifierProperty(PsiModifier.STATIC) &&
          ((PsiClass)resolved).getTypeParameters().length == 0) {
        String description = JavaErrorMessages.message("illegal.generic.type.for.instanceof");
        return HighlightInfo.newHighlightInfo(HighlightInfoType.ERROR).range(typeElement).descriptionAndTooltip(description).create();
      }
    }

    final PsiType[] parameters = ref.getTypeParameters();
    for (PsiType parameterType : parameters) {
      if (parameterType != null &&
          !(parameterType instanceof PsiWildcardType && ((PsiWildcardType)parameterType).getBound() == null)) {
        String description = JavaErrorMessages.message("illegal.generic.type.for.instanceof");
        return HighlightInfo.newHighlightInfo(HighlightInfoType.ERROR).range(typeElement).descriptionAndTooltip(description).create();
      }
    }

    return null;
  }

  public static HighlightInfo checkClassObjectAccessExpression(PsiClassObjectAccessExpression expression) {
    PsiType type = expression.getOperand().getType();
    if (type instanceof PsiClassType) {
      return canSelectFrom((PsiClassType)type, expression.getOperand());
    }
    if (type instanceof PsiArrayType) {
      final PsiType arrayComponentType = type.getDeepComponentType();
      if (arrayComponentType instanceof PsiClassType) {
        return canSelectFrom((PsiClassType)arrayComponentType, expression.getOperand());
      }
    }

    return null;
  }

  @Nullable
  private static HighlightInfo canSelectFrom(PsiClassType type, PsiTypeElement operand) {
    PsiClass aClass = type.resolve();
    if (aClass instanceof PsiTypeParameter) {
      String description = JavaErrorMessages.message("cannot.select.dot.class.from.type.variable");
      return HighlightInfo.newHighlightInfo(HighlightInfoType.ERROR).range(operand).descriptionAndTooltip(description).create();
    }
    if (type.getParameters().length > 0) {
      return HighlightInfo
        .newHighlightInfo(HighlightInfoType.ERROR).range(operand).descriptionAndTooltip("Cannot select from parameterized type").create();
    }
    return null;
  }

  @Nullable
  public static HighlightInfo checkOverrideAnnotation(PsiMethod method, final LanguageLevel languageLevel) {
    PsiModifierList list = method.getModifierList();
    final PsiAnnotation overrideAnnotation = list.findAnnotation("java.lang.Override");
    if (overrideAnnotation == null) {
      return null;
    }
    try {
      MethodSignatureBackedByPsiMethod superMethod = SuperMethodsSearch.search(method, null, true, false).findFirst();
      if (superMethod != null && method.getContainingClass().isInterface() && "clone".equals(superMethod.getName())) {
        final PsiClass containingClass = superMethod.getMethod().getContainingClass();
        if (containingClass != null && CommonClassNames.JAVA_LANG_OBJECT.equals(containingClass.getQualifiedName())) {
          superMethod = null;
        }
      }
      if (superMethod == null) {
        String description = JavaErrorMessages.message("method.does.not.override.super");
        HighlightInfo highlightInfo =
          HighlightInfo.newHighlightInfo(HighlightInfoType.ERROR).range(overrideAnnotation).descriptionAndTooltip(description).create();
        QUICK_FIX_FACTORY.registerPullAsAbstractUpFixes(method, new QuickFixActionRegistrarImpl(highlightInfo));
        return highlightInfo;
      }
      PsiClass superClass = superMethod.getMethod().getContainingClass();
      if (languageLevel.equals(LanguageLevel.JDK_1_5) &&
          superClass != null &&
          superClass.isInterface()) {
        String description = JavaErrorMessages.message("override.not.allowed.in.interfaces");
        HighlightInfo info =
          HighlightInfo.newHighlightInfo(HighlightInfoType.ERROR).range(overrideAnnotation).descriptionAndTooltip(description).create();
        QuickFixAction.registerQuickFixAction(info, QUICK_FIX_FACTORY.createIncreaseLanguageLevelFix(LanguageLevel.JDK_1_6));
        return info;
      }
      return null;
    }
    catch (IndexNotReadyException e) {
      return null;
    }
  }

  @Nullable
  public static HighlightInfo checkSafeVarargsAnnotation(PsiMethod method, LanguageLevel languageLevel) {
    PsiModifierList list = method.getModifierList();
    final PsiAnnotation safeVarargsAnnotation = list.findAnnotation("java.lang.SafeVarargs");
    if (safeVarargsAnnotation == null) {
      return null;
    }
    try {
      if (!method.isVarArgs()) {
        return HighlightInfo.newHighlightInfo(HighlightInfoType.ERROR).range(safeVarargsAnnotation).descriptionAndTooltip(
          "@SafeVarargs is not allowed on methods with fixed arity").create();
      }
      if (!isSafeVarargsNoOverridingCondition(method, languageLevel)) {
        return HighlightInfo.newHighlightInfo(HighlightInfoType.ERROR).range(safeVarargsAnnotation).descriptionAndTooltip(
          "@SafeVarargs is not allowed on non-final instance methods").create();
      }

      final PsiParameter varParameter = method.getParameterList().getParameters()[method.getParameterList().getParametersCount() - 1];

      for (PsiReference reference : ReferencesSearch.search(varParameter)) {
        final PsiElement element = reference.getElement();
        if (element instanceof PsiExpression && !PsiUtil.isAccessedForReading((PsiExpression)element)) {
          return HighlightInfo.newHighlightInfo(HighlightInfoType.WARNING).range(element).descriptionAndTooltip(
            "@SafeVarargs do not suppress potentially unsafe operations").create();
        }
      }


      LOG.assertTrue(varParameter.isVarArgs());
      final PsiEllipsisType ellipsisType = (PsiEllipsisType)varParameter.getType();
      final PsiType componentType = ellipsisType.getComponentType();
      if (JavaGenericsUtil.isReifiableType(componentType)) {
        PsiElement element = varParameter.getTypeElement();
        return HighlightInfo.newHighlightInfo(HighlightInfoType.WARNING).range(element).descriptionAndTooltip(
          "@SafeVarargs is not applicable for reifiable types").create();
      }
      return null;
    }
    catch (IndexNotReadyException e) {
      return null;
    }
  }

  public static boolean isSafeVarargsNoOverridingCondition(PsiMethod method, LanguageLevel languageLevel) {
    return method.hasModifierProperty(PsiModifier.FINAL) ||
           method.hasModifierProperty(PsiModifier.STATIC) ||
           method.isConstructor() ||
           method.hasModifierProperty(PsiModifier.PRIVATE) && languageLevel.isAtLeast(LanguageLevel.JDK_1_9);
  }

  static void checkEnumConstantForConstructorProblems(@NotNull PsiEnumConstant enumConstant,
                                                      @NotNull HighlightInfoHolder holder,
                                                      @NotNull JavaSdkVersion javaSdkVersion) {
    PsiClass containingClass = enumConstant.getContainingClass();
    if (enumConstant.getInitializingClass() == null) {
      HighlightInfo highlightInfo = HighlightClassUtil.checkInstantiationOfAbstractClass(containingClass, enumConstant.getNameIdentifier());
      if (highlightInfo != null) {
        QuickFixAction.registerQuickFixAction(highlightInfo, QUICK_FIX_FACTORY.createImplementMethodsFix(enumConstant));
        holder.add(highlightInfo);
        return;
      }
      highlightInfo = HighlightClassUtil.checkClassWithAbstractMethods(enumConstant.getContainingClass(), enumConstant, enumConstant.getNameIdentifier().getTextRange());
      if (highlightInfo != null) {
        holder.add(highlightInfo);
        return;
      }
    }
    PsiClassType type = JavaPsiFacade.getInstance(holder.getProject()).getElementFactory().createType(containingClass);

    HighlightMethodUtil.checkConstructorCall(type.resolveGenerics(), enumConstant, type, null, holder, javaSdkVersion);
  }

  @Nullable
  public static HighlightInfo checkEnumSuperConstructorCall(PsiMethodCallExpression expr) {
    PsiReferenceExpression methodExpression = expr.getMethodExpression();
    final PsiElement refNameElement = methodExpression.getReferenceNameElement();
    if (refNameElement != null && PsiKeyword.SUPER.equals(refNameElement.getText())) {
      final PsiMember constructor = PsiUtil.findEnclosingConstructorOrInitializer(expr);
      if (constructor instanceof PsiMethod) {
        final PsiClass aClass = constructor.getContainingClass();
        if (aClass != null && aClass.isEnum()) {
          final String message = JavaErrorMessages.message("call.to.super.is.not.allowed.in.enum.constructor");
          return HighlightInfo.newHighlightInfo(HighlightInfoType.ERROR).range(expr).descriptionAndTooltip(message).create();
        }
      }
    }
    return null;
  }

  @Nullable
  public static HighlightInfo checkVarArgParameterIsLast(@NotNull PsiParameter parameter) {
    PsiElement declarationScope = parameter.getDeclarationScope();
    if (declarationScope instanceof PsiMethod) {
      PsiParameter[] params = ((PsiMethod)declarationScope).getParameterList().getParameters();
      if (params[params.length - 1] != parameter) {
        String description = JavaErrorMessages.message("vararg.not.last.parameter");
        HighlightInfo info = HighlightInfo.newHighlightInfo(HighlightInfoType.ERROR).range(parameter).descriptionAndTooltip(description).create();
        QuickFixAction.registerQuickFixAction(info, QUICK_FIX_FACTORY.createMakeVarargParameterLastFix(parameter));
        return info;
      }
    }
    return null;
  }

  @Nullable
  public static List<HighlightInfo> checkEnumConstantModifierList(PsiModifierList modifierList) {
    List<HighlightInfo> list = null;
    PsiElement[] children = modifierList.getChildren();
    for (PsiElement child : children) {
      if (child instanceof PsiKeyword) {
        if (list == null) {
          list = new ArrayList<HighlightInfo>();
        }
        String description = JavaErrorMessages.message("modifiers.for.enum.constants");
        list.add(HighlightInfo.newHighlightInfo(HighlightInfoType.ERROR).range(child).descriptionAndTooltip(description).create());
      }
    }
    return list;
  }

  @Nullable
  public static HighlightInfo checkParametersAllowed(PsiReferenceParameterList refParamList) {
    final PsiElement parent = refParamList.getParent();
    if (parent instanceof PsiReferenceExpression) {
      final PsiElement grandParent = parent.getParent();
      if (!(grandParent instanceof PsiMethodCallExpression) && !(parent instanceof PsiMethodReferenceExpression)) {
        final String message = JavaErrorMessages.message("generics.reference.parameters.not.allowed");
        return HighlightInfo.newHighlightInfo(HighlightInfoType.ERROR).range(refParamList).descriptionAndTooltip(message).create();
      }
    }

    return null;
  }

  @Nullable
  public static HighlightInfo checkParametersOnRaw(PsiReferenceParameterList refParamList) {
    JavaResolveResult resolveResult = null;
    PsiElement parent = refParamList.getParent();
    PsiElement qualifier = null;
    if (parent instanceof PsiJavaCodeReferenceElement) {
      resolveResult = ((PsiJavaCodeReferenceElement)parent).advancedResolve(false);
      qualifier = ((PsiJavaCodeReferenceElement)parent).getQualifier();
    }
    else if (parent instanceof PsiCallExpression) {
      resolveResult = ((PsiCallExpression)parent).resolveMethodGenerics();
      if (parent instanceof PsiMethodCallExpression) {
        final PsiReferenceExpression methodExpression = ((PsiMethodCallExpression)parent).getMethodExpression();
        qualifier = methodExpression.getQualifier();
      }
    }
    if (resolveResult != null) {
      PsiElement element = resolveResult.getElement();
      if (!(element instanceof PsiTypeParameterListOwner)) return null;
      if (((PsiModifierListOwner)element).hasModifierProperty(PsiModifier.STATIC)) return null;
      if (qualifier instanceof PsiJavaCodeReferenceElement && ((PsiJavaCodeReferenceElement)qualifier).resolve() instanceof PsiTypeParameter) return null;
      PsiClass containingClass = ((PsiMember)element).getContainingClass();
      if (containingClass != null && PsiUtil.isRawSubstitutor(containingClass, resolveResult.getSubstitutor())) {
        if ((parent instanceof PsiCallExpression || parent instanceof PsiMethodReferenceExpression) && PsiUtil.isLanguageLevel7OrHigher(parent)) {
          return null;
        }

        if (element instanceof PsiMethod) {
          if (((PsiMethod)element).findSuperMethods().length > 0) return null;
          if (qualifier instanceof PsiReferenceExpression){
            final PsiType type = ((PsiReferenceExpression)qualifier).getType();
            final boolean isJavac7 = JavaVersionService.getInstance().isAtLeast(containingClass, JavaSdkVersion.JDK_1_7);
            if (type instanceof PsiClassType && isJavac7 && ((PsiClassType)type).isRaw()) return null;
            final PsiClass typeParameter = PsiUtil.resolveClassInType(type);
            if (typeParameter instanceof PsiTypeParameter) {
              if (isJavac7) return null;
              for (PsiClassType classType : typeParameter.getExtendsListTypes()) {
                final PsiClass resolve = classType.resolve();
                if (resolve != null) {
                  final PsiMethod[] superMethods = resolve.findMethodsBySignature((PsiMethod)element, true);
                  for (PsiMethod superMethod : superMethods) {
                    if (!PsiUtil.isRawSubstitutor(superMethod, resolveResult.getSubstitutor())) {
                      return null;
                    }
                  }
                }
              }
            }
          }
        }
        final String message = element instanceof PsiClass
                               ? JavaErrorMessages.message("generics.type.arguments.on.raw.type")
                               : JavaErrorMessages.message("generics.type.arguments.on.raw.method");

        return HighlightInfo.newHighlightInfo(HighlightInfoType.ERROR).range(refParamList).descriptionAndTooltip(message).create();
      }
    }
    return null;
  }

  public static HighlightInfo checkCannotInheritFromEnum(PsiClass superClass, PsiElement elementToHighlight) {
    HighlightInfo errorResult = null;
    if (Comparing.strEqual("java.lang.Enum", superClass.getQualifiedName())) {
      String message = JavaErrorMessages.message("classes.extends.enum");
      errorResult =
        HighlightInfo.newHighlightInfo(HighlightInfoType.ERROR).range(elementToHighlight).descriptionAndTooltip(message).create();
    }
    return errorResult;
  }

  public static HighlightInfo checkGenericCannotExtendException(PsiReferenceList list) {
    PsiElement parent = list.getParent();
    if (!(parent instanceof PsiClass)) return null;
    PsiClass aClass = (PsiClass)parent;

    if (!aClass.hasTypeParameters() || aClass.getExtendsList() != list) return null;
    PsiJavaCodeReferenceElement[] referenceElements = list.getReferenceElements();
    PsiClass throwableClass = null;
    for (PsiJavaCodeReferenceElement referenceElement : referenceElements) {
      PsiElement resolved = referenceElement.resolve();
      if (!(resolved instanceof PsiClass)) continue;
      if (throwableClass == null) {
        throwableClass = JavaPsiFacade.getInstance(aClass.getProject()).findClass("java.lang.Throwable", aClass.getResolveScope());
      }
      if (InheritanceUtil.isInheritorOrSelf((PsiClass)resolved, throwableClass, true)) {
        String message = JavaErrorMessages.message("generic.extend.exception");
        HighlightInfo highlightInfo =
          HighlightInfo.newHighlightInfo(HighlightInfoType.ERROR).range(referenceElement).descriptionAndTooltip(message).create();
        PsiClassType classType = JavaPsiFacade.getInstance(aClass.getProject()).getElementFactory().createType((PsiClass)resolved);
        QuickFixAction.registerQuickFixAction(highlightInfo, QUICK_FIX_FACTORY.createExtendsListFix(aClass, classType, false));
        return highlightInfo;
      }
    }
    return null;
  }

  public static HighlightInfo checkEnumMustNotBeLocal(final PsiClass aClass) {
    if (!aClass.isEnum()) return null;
    PsiElement parent = aClass.getParent();
    if (!(parent instanceof PsiClass || parent instanceof PsiFile || parent instanceof PsiClassLevelDeclarationStatement)) {
      String description = JavaErrorMessages.message("local.enum");
      TextRange textRange = HighlightNamesUtil.getClassDeclarationTextRange(aClass);
      return HighlightInfo.newHighlightInfo(HighlightInfoType.ERROR).range(textRange).descriptionAndTooltip(description).create();
    }
    return null;
  }

  public static HighlightInfo checkEnumWithoutConstantsCantHaveAbstractMethods(final PsiClass aClass) {
    if (!aClass.isEnum()) return null;
    for (PsiField field : aClass.getFields()) {
      if (field instanceof PsiEnumConstant) {
        return null;
      }
    }
    for (PsiMethod method : aClass.getMethods()) {
      if (method.hasModifierProperty(PsiModifier.ABSTRACT)) {
        final String description = "Enum declaration without enum constants cannot have abstract methods";
        final TextRange textRange = HighlightNamesUtil.getClassDeclarationTextRange(aClass);
        return HighlightInfo.newHighlightInfo(HighlightInfoType.ERROR).range(textRange).descriptionAndTooltip(description).create();
      }
    }
    return null;
  }

  public static HighlightInfo checkSelectStaticClassFromParameterizedType(final PsiElement resolved, final PsiJavaCodeReferenceElement ref) {
    if (resolved instanceof PsiClass && ((PsiClass)resolved).hasModifierProperty(PsiModifier.STATIC)) {
      final PsiElement qualifier = ref.getQualifier();
      if (qualifier instanceof PsiJavaCodeReferenceElement) {
        final PsiReferenceParameterList parameterList = ((PsiJavaCodeReferenceElement)qualifier).getParameterList();
        if (parameterList != null && parameterList.getTypeArguments().length > 0) {
          final String message = JavaErrorMessages.message("generics.select.static.class.from.parameterized.type",
                                                           HighlightUtil.formatClass((PsiClass)resolved));
          return HighlightInfo.newHighlightInfo(HighlightInfoType.ERROR).range(parameterList).descriptionAndTooltip(message).create();
        }
      }
    }
    return null;
  }

  public static HighlightInfo checkCannotInheritFromTypeParameter(final PsiClass superClass, final PsiJavaCodeReferenceElement toHighlight) {
    if (superClass instanceof PsiTypeParameter) {
      String description = JavaErrorMessages.message("class.cannot.inherit.from.its.type.parameter");
      return HighlightInfo.newHighlightInfo(HighlightInfoType.ERROR).range(toHighlight).descriptionAndTooltip(description).create();
    }
    return null;
  }

  /**
   * http://docs.oracle.com/javase/specs/jls/se7/html/jls-4.html#jls-4.8
   */
  static HighlightInfo checkRawOnParameterizedType(@NotNull PsiJavaCodeReferenceElement parent, PsiElement resolved) {
    PsiReferenceParameterList list = parent.getParameterList();
    if (list == null || list.getTypeArguments().length > 0) return null;
    final PsiElement qualifier = parent.getQualifier();
    if (qualifier instanceof PsiJavaCodeReferenceElement &&
        ((PsiJavaCodeReferenceElement)qualifier).getTypeParameters().length > 0 &&
        resolved instanceof PsiTypeParameterListOwner &&
        ((PsiTypeParameterListOwner)resolved).hasTypeParameters() &&
        !((PsiTypeParameterListOwner)resolved).hasModifierProperty(PsiModifier.STATIC)) {
      return HighlightInfo.newHighlightInfo(HighlightInfoType.ERROR).range(parent).descriptionAndTooltip(
        "Improper formed type; some type parameters are missing").create();
    }
    return null;
  }

  public static HighlightInfo checkCannotPassInner(PsiJavaCodeReferenceElement ref) {
    if (ref.getParent() instanceof PsiTypeElement) {
      final PsiClass psiClass = PsiTreeUtil.getParentOfType(ref, PsiClass.class);
      if (psiClass == null) return null;
      if (PsiTreeUtil.isAncestor(psiClass.getExtendsList(), ref, false) ||
          PsiTreeUtil.isAncestor(psiClass.getImplementsList(), ref, false)) {
        final PsiElement qualifier = ref.getQualifier();
        if (qualifier instanceof PsiJavaCodeReferenceElement && ((PsiJavaCodeReferenceElement)qualifier).resolve() == psiClass) {
          final PsiJavaCodeReferenceElement referenceElement = PsiTreeUtil.getParentOfType(ref, PsiJavaCodeReferenceElement.class);
          if (referenceElement == null) return null;
          final PsiElement typeClass = referenceElement.resolve();
          if (!(typeClass instanceof PsiClass)) return null;
          final PsiElement resolve = ref.resolve();
          final PsiClass containingClass = resolve != null ? ((PsiClass)resolve).getContainingClass() : null;
          if (containingClass == null) return null;
          if (psiClass.isInheritor(containingClass, true) ||
              unqualifiedNestedClassReferenceAccessedViaContainingClassInheritance((PsiClass)typeClass, ((PsiClass)resolve).getExtendsList()) ||
              unqualifiedNestedClassReferenceAccessedViaContainingClassInheritance((PsiClass)typeClass, ((PsiClass)resolve).getImplementsList())) {
            return HighlightInfo.newHighlightInfo(HighlightInfoType.ERROR).descriptionAndTooltip(((PsiClass)resolve).getName() + " is not accessible in current context").range(ref).create();
          }
        }
      }
    }
    return null;
  }

  private static boolean unqualifiedNestedClassReferenceAccessedViaContainingClassInheritance(PsiClass containingClass,
                                                                                              PsiReferenceList referenceList) {
    if (referenceList != null) {
      for (PsiJavaCodeReferenceElement referenceElement : referenceList.getReferenceElements()) {
        if (!referenceElement.isQualified()) {
          final PsiElement superClass = referenceElement.resolve();
          if (superClass instanceof PsiClass) {
            final PsiClass superContainingClass = ((PsiClass)superClass).getContainingClass();
            if (superContainingClass != null && 
                InheritanceUtil.isInheritorOrSelf(containingClass, superContainingClass, true) && 
                !PsiTreeUtil.isAncestor(superContainingClass, containingClass, true)) {
              return true;
            }
          }
        }
      }
    }
    return false;
  }

  public static void registerVariableParameterizedTypeFixes(HighlightInfo highlightInfo,
                                                            @NotNull PsiVariable variable,
                                                            @NotNull PsiReferenceParameterList parameterList, 
                                                            @NotNull JavaSdkVersion version) {
    PsiType type = variable.getType();
    if (!(type instanceof PsiClassType)) return;

    if (DumbService.getInstance(variable.getProject()).isDumb()) return;

    String shortName = ((PsiClassType)type).getClassName();
    PsiManager manager = parameterList.getManager();
    final JavaPsiFacade facade = JavaPsiFacade.getInstance(manager.getProject());
    PsiShortNamesCache shortNamesCache = PsiShortNamesCache.getInstance(parameterList.getProject());
    PsiClass[] classes = shortNamesCache.getClassesByName(shortName, GlobalSearchScope.allScope(manager.getProject()));
    PsiElementFactory factory = facade.getElementFactory();
    for (PsiClass aClass : classes) {
      if (checkReferenceTypeArgumentList(aClass, parameterList, PsiSubstitutor.EMPTY, false, version) == null) {
        PsiType[] actualTypeParameters = parameterList.getTypeArguments();
        PsiTypeParameter[] classTypeParameters = aClass.getTypeParameters();
        Map<PsiTypeParameter, PsiType> map = new java.util.HashMap<PsiTypeParameter, PsiType>();
        for (int j = 0; j < classTypeParameters.length; j++) {
          PsiTypeParameter classTypeParameter = classTypeParameters[j];
          PsiType actualTypeParameter = actualTypeParameters[j];
          map.put(classTypeParameter, actualTypeParameter);
        }
        PsiSubstitutor substitutor = factory.createSubstitutor(map);
        PsiType suggestedType = factory.createType(aClass, substitutor);
        HighlightUtil.registerChangeVariableTypeFixes(variable, suggestedType, variable.getInitializer(), highlightInfo);
      }
    }
  }

  public static HighlightInfo checkInferredIntersections(PsiSubstitutor substitutor, TextRange ref) {
    for (Map.Entry<PsiTypeParameter, PsiType> typeEntry : substitutor.getSubstitutionMap().entrySet()) {
      final PsiType type = typeEntry.getValue();
      if (type instanceof PsiIntersectionType) {
        final PsiType[] conjuncts = ((PsiIntersectionType)type).getConjuncts();
        for (int i = 0; i < conjuncts.length; i++) {
          PsiClass conjunct = PsiUtil.resolveClassInClassTypeOnly(conjuncts[i]);
          if (conjunct != null && !conjunct.isInterface()) {
            for (int i1 = i + 1; i1 < conjuncts.length; i1++) {
              PsiClass oppositeConjunct = PsiUtil.resolveClassInClassTypeOnly(conjuncts[i1]);
              if (oppositeConjunct != null && !oppositeConjunct.isInterface()) {
                if (!conjunct.isInheritor(oppositeConjunct, true) && !oppositeConjunct.isInheritor(conjunct, true)) {
                  return HighlightInfo.newHighlightInfo(HighlightInfoType.ERROR)
                    .descriptionAndTooltip("Type parameter " + typeEntry.getKey().getName() + " has incompatible upper bounds: " +
                                           conjunct.getName() + " and " + oppositeConjunct.getName())
                    .range(ref).create();
                }
              }
            }
          }
        }
      }
    }
    return null;
  }

  public static HighlightInfo areSupersAccessible(@NotNull PsiClass aClass) {
    return areSupersAccessible(aClass, aClass.getResolveScope(), HighlightNamesUtil.getClassDeclarationTextRange(aClass));
  }

  public static HighlightInfo areSupersAccessible(@NotNull PsiClass aClass, PsiElement ref) {
    return areSupersAccessible(aClass, ref.getResolveScope(), ref.getTextRange());
  }

  private static HighlightInfo areSupersAccessible(@NotNull PsiClass aClass,
                                                   GlobalSearchScope resolveScope,
                                                   TextRange range) {
    final JavaPsiFacade factory = JavaPsiFacade.getInstance(aClass.getProject());
    for (PsiClassType superType : aClass.getSuperTypes()) {
      final String notAccessibleErrorMessage = isSuperTypeAccessible(superType, new HashSet<PsiClass>(), resolveScope, factory);
      if (notAccessibleErrorMessage != null) {
        return HighlightInfo.newHighlightInfo(HighlightInfoType.ERROR)
          .descriptionAndTooltip(notAccessibleErrorMessage)
          .range(range)
          .create();
      }
    }
    return null;
  }

  @Nullable
  private static String isSuperTypeAccessible(PsiType superType,
                                              HashSet<PsiClass> classes,
                                              GlobalSearchScope resolveScope,
                                              JavaPsiFacade factory) {
    final PsiClass aClass = PsiUtil.resolveClassInType(superType);
    if (aClass != null && classes.add(aClass)) {
      final String qualifiedName = aClass.getQualifiedName();
      if (qualifiedName != null && factory.findClass(qualifiedName, resolveScope) == null) {
        return "Cannot access " + HighlightUtil.formatClass(aClass);
      }

      if (superType instanceof PsiClassType) {
        for (PsiType psiType : ((PsiClassType)superType).getParameters()) {
          final String notAccessibleMessage = isSuperTypeAccessible(psiType, classes, resolveScope, factory);
          if (notAccessibleMessage != null) {
            return notAccessibleMessage;
          }
        }
      }

      for (PsiClassType type : aClass.getSuperTypes()) {
        final String notAccessibleMessage = isSuperTypeAccessible(type, classes, resolveScope, factory);
        if (notAccessibleMessage != null) {
          return notAccessibleMessage;
        }
      }
    }
    return null;
  }
}



File: java/java-analysis-impl/src/com/intellij/codeInsight/daemon/impl/analysis/HighlightVisitorImpl.java
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
package com.intellij.codeInsight.daemon.impl.analysis;

import com.intellij.codeHighlighting.Pass;
import com.intellij.codeInsight.daemon.JavaErrorMessages;
import com.intellij.codeInsight.daemon.impl.*;
import com.intellij.codeInsight.daemon.impl.analysis.HighlightUtil.Feature;
import com.intellij.codeInsight.daemon.impl.quickfix.QuickFixAction;
import com.intellij.codeInsight.intention.QuickFixFactory;
import com.intellij.lang.injection.InjectedLanguageManager;
import com.intellij.openapi.application.ApplicationManager;
import com.intellij.openapi.editor.Document;
import com.intellij.openapi.editor.colors.TextAttributesScheme;
import com.intellij.openapi.progress.ProgressIndicator;
import com.intellij.openapi.progress.ProgressManager;
import com.intellij.openapi.project.IndexNotReadyException;
import com.intellij.openapi.project.Project;
import com.intellij.openapi.projectRoots.JavaSdkVersion;
import com.intellij.openapi.projectRoots.JavaVersionService;
import com.intellij.openapi.util.Pair;
import com.intellij.openapi.util.TextRange;
import com.intellij.pom.java.LanguageLevel;
import com.intellij.psi.*;
import com.intellij.psi.controlFlow.ControlFlowUtil;
import com.intellij.psi.impl.source.javadoc.PsiDocMethodOrFieldRef;
import com.intellij.psi.impl.source.resolve.JavaResolveUtil;
import com.intellij.psi.impl.source.resolve.graphInference.InferenceSession;
import com.intellij.psi.impl.source.resolve.graphInference.PsiPolyExpressionUtil;
import com.intellij.psi.impl.source.tree.java.PsiReferenceExpressionImpl;
import com.intellij.psi.javadoc.PsiDocComment;
import com.intellij.psi.javadoc.PsiDocTagValue;
import com.intellij.psi.util.*;
import com.intellij.util.ArrayUtil;
import com.intellij.util.ObjectUtils;
import com.intellij.util.containers.MostlySingularMultiMap;
import gnu.trove.THashMap;
import gnu.trove.TObjectIntHashMap;
import org.jetbrains.annotations.NotNull;
import org.jetbrains.annotations.Nullable;

import java.util.Collection;
import java.util.List;
import java.util.Map;
import java.util.Set;

public class HighlightVisitorImpl extends JavaElementVisitor implements HighlightVisitor {
  @NotNull
  private final PsiResolveHelper myResolveHelper;

  private HighlightInfoHolder myHolder;

  private RefCountHolder myRefCountHolder;

  // map codeBlock->List of PsiReferenceExpression of uninitialized final variables
  private final Map<PsiElement, Collection<PsiReferenceExpression>> myUninitializedVarProblems = new THashMap<PsiElement, Collection<PsiReferenceExpression>>();
  // map codeBlock->List of PsiReferenceExpression of extra initialization of final variable
  private final Map<PsiElement, Collection<ControlFlowUtil.VariableInfo>> myFinalVarProblems = new THashMap<PsiElement, Collection<ControlFlowUtil.VariableInfo>>();

  // value==1: no info if the parameter was reassigned (but the parameter is present in current file), value==2: parameter was reassigned
  private final TObjectIntHashMap<PsiParameter> myReassignedParameters = new TObjectIntHashMap<PsiParameter>();

  private final Map<String, Pair<PsiImportStaticReferenceElement, PsiClass>> mySingleImportedClasses = new THashMap<String, Pair<PsiImportStaticReferenceElement, PsiClass>>();
  private final Map<String, Pair<PsiImportStaticReferenceElement, PsiField>> mySingleImportedFields = new THashMap<String, Pair<PsiImportStaticReferenceElement, PsiField>>();
  private PsiFile myFile;
  private final PsiElementVisitor REGISTER_REFERENCES_VISITOR = new PsiRecursiveElementWalkingVisitor() {
    @Override public void visitElement(PsiElement element) {
      super.visitElement(element);
      for (PsiReference reference : element.getReferences()) {
        PsiElement resolved = reference.resolve();
        if (resolved instanceof PsiNamedElement) {
          myRefCountHolder.registerLocallyReferenced((PsiNamedElement)resolved);
        }
      }
    }
  };
  private final Map<PsiClass, MostlySingularMultiMap<MethodSignature, PsiMethod>> myDuplicateMethods = new THashMap<PsiClass, MostlySingularMultiMap<MethodSignature, PsiMethod>>();
  private LanguageLevel myLanguageLevel;
  private JavaSdkVersion myJavaSdkVersion;
  private static final boolean CHECK_ELEMENT_LEVEL = ApplicationManager.getApplication().isUnitTestMode() || ApplicationManager.getApplication().isInternal();

  public HighlightVisitorImpl(@NotNull PsiResolveHelper resolveHelper) {
    myResolveHelper = resolveHelper;
  }

  @NotNull
  private MostlySingularMultiMap<MethodSignature, PsiMethod> getDuplicateMethods(@NotNull PsiClass aClass) {
    MostlySingularMultiMap<MethodSignature, PsiMethod> signatures = myDuplicateMethods.get(aClass);
    if (signatures == null) {
      signatures = new MostlySingularMultiMap<MethodSignature, PsiMethod>();
      for (PsiMethod method : aClass.getMethods()) {
        if (method instanceof ExternallyDefinedPsiElement) continue; // ignore aspectj-weaved methods; they are checked elsewhere
        MethodSignature signature = method.getSignature(PsiSubstitutor.EMPTY);
        signatures.add(signature, method);
      }

      myDuplicateMethods.put(aClass, signatures);
    }
    return signatures;
  }

  @Override
  @NotNull
  public HighlightVisitorImpl clone() {
    return new HighlightVisitorImpl(myResolveHelper);
  }

  @Override
  public int order() {
    return 0;
  }

  @Override
  public boolean suitableForFile(@NotNull PsiFile file) {
    // both PsiJavaFile and PsiCodeFragment
    return file instanceof PsiImportHolder && !InjectedLanguageManager.getInstance(file.getProject()).isInjectedFragment(file);
  }

  @Override
  public void visit(@NotNull PsiElement element) {
    if (CHECK_ELEMENT_LEVEL) {
      ((CheckLevelHighlightInfoHolder)myHolder).enterLevel(element);
      element.accept(this);
      ((CheckLevelHighlightInfoHolder)myHolder).enterLevel(null);
    }
    else {
      element.accept(this);
    }
  }

  private void registerReferencesFromInjectedFragments(@NotNull PsiElement element) {
    InjectedLanguageManager.getInstance(myFile.getProject()).enumerateEx(element, myFile, false,
                                                                         new PsiLanguageInjectionHost.InjectedPsiVisitor() {
                                                                           @Override
                                                                           public void visit(@NotNull final PsiFile injectedPsi,
                                                                                             @NotNull final List<PsiLanguageInjectionHost.Shred> places) {
                                                                             injectedPsi.accept(REGISTER_REFERENCES_VISITOR);
                                                                           }
                                                                         }
    );
  }

  @Override
  public boolean analyze(@NotNull final PsiFile file,
                         final boolean updateWholeFile,
                         @NotNull final HighlightInfoHolder holder,
                         @NotNull final Runnable highlight) {
    myFile = file;
    myHolder = CHECK_ELEMENT_LEVEL ? new CheckLevelHighlightInfoHolder(file, holder) : holder;
    boolean success = true;
    try {
      myLanguageLevel = PsiUtil.getLanguageLevel(file);
      myJavaSdkVersion = ObjectUtils.notNull(JavaVersionService.getInstance().getJavaSdkVersion(file), JavaSdkVersion.fromLanguageLevel(myLanguageLevel));
      if (updateWholeFile) {
        final Project project = file.getProject();
        DaemonCodeAnalyzerEx daemonCodeAnalyzer = DaemonCodeAnalyzerEx.getInstanceEx(project);
        final FileStatusMap fileStatusMap = daemonCodeAnalyzer.getFileStatusMap();
        final ProgressIndicator progress = ProgressManager.getInstance().getProgressIndicator();
        if (progress == null) throw new IllegalStateException("Must be run under progress");
        final RefCountHolder refCountHolder = RefCountHolder.get(file);
        myRefCountHolder = refCountHolder;
        final Document document = PsiDocumentManager.getInstance(project).getDocument(file);
        TextRange dirtyScope = document == null ? file.getTextRange() : fileStatusMap.getFileDirtyScope(document, Pass.UPDATE_ALL);
        success = refCountHolder.analyze(file, dirtyScope, progress, new Runnable(){
          @Override
          public void run() {
            highlight.run();
            progress.checkCanceled();
            HighlightingSession highlightingSession = ProgressableTextEditorHighlightingPass.getHighlightingSession(progress);
            PostHighlightingVisitor highlightingVisitor = new PostHighlightingVisitor(file, document, refCountHolder, highlightingSession);
            highlightingVisitor.collectHighlights(file, holder, progress);
          }
        });
      }
      else {
        myRefCountHolder = null;
        highlight.run();
      }
    }
    finally {
      myUninitializedVarProblems.clear();
      myFinalVarProblems.clear();
      mySingleImportedClasses.clear();
      mySingleImportedFields.clear();
      myReassignedParameters.clear();

      myRefCountHolder = null;
      myFile = null;
      myHolder = null;
      myDuplicateMethods.clear();
    }

    return success;
  }

  @Override
  public void visitElement(final PsiElement element) {
    if (myRefCountHolder != null && myFile instanceof ServerPageFile) {
      // in jsp XmlAttributeValue may contain java references
      try {
        for (PsiReference reference : element.getReferences()) {
          if(reference instanceof PsiJavaReference){
            final PsiJavaReference psiJavaReference = (PsiJavaReference)reference;
            myRefCountHolder.registerReference(psiJavaReference, psiJavaReference.advancedResolve(false));
          }
        }
      }
      catch (IndexNotReadyException ignored) {
      }
    }
  }

  @Override
  public void visitAnnotation(PsiAnnotation annotation) {
    super.visitAnnotation(annotation);
    if (!myHolder.hasErrorResults()) myHolder.add(checkFeature(annotation, Feature.ANNOTATIONS));
    if (!myHolder.hasErrorResults()) myHolder.add(AnnotationsHighlightUtil.checkApplicability(annotation, myLanguageLevel, myFile));
    if (!myHolder.hasErrorResults()) myHolder.add(AnnotationsHighlightUtil.checkAnnotationType(annotation));
    if (!myHolder.hasErrorResults()) myHolder.add(AnnotationsHighlightUtil.checkMissingAttributes(annotation));
    if (!myHolder.hasErrorResults()) myHolder.add(AnnotationsHighlightUtil.checkTargetAnnotationDuplicates(annotation));
    if (!myHolder.hasErrorResults()) myHolder.add(AnnotationsHighlightUtil.checkDuplicateAnnotations(annotation, myLanguageLevel));
    if (!myHolder.hasErrorResults()) myHolder.add(AnnotationsHighlightUtil.checkForeignInnerClassesUsed(annotation));
    if (!myHolder.hasErrorResults()) myHolder.add(AnnotationsHighlightUtil.checkFunctionalInterface(annotation, myLanguageLevel));
    if (!myHolder.hasErrorResults()) myHolder.add(AnnotationsHighlightUtil.checkRepeatableAnnotation(annotation));
  }

  @Override
  public void visitAnnotationArrayInitializer(PsiArrayInitializerMemberValue initializer) {
    PsiMethod method = null;
    PsiElement parent = initializer.getParent();
    if (parent instanceof PsiNameValuePair) {
      method = (PsiMethod)parent.getReference().resolve();
    }
    else if (PsiUtil.isAnnotationMethod(parent)) {
      method = (PsiMethod)parent;
    }
    if (method != null) {
      PsiType type = method.getReturnType();
      if (type instanceof PsiArrayType) {
        type = ((PsiArrayType)type).getComponentType();
        PsiAnnotationMemberValue[] initializers = initializer.getInitializers();
        for (PsiAnnotationMemberValue initializer1 : initializers) {
          myHolder.add(AnnotationsHighlightUtil.checkMemberValueType(initializer1, type));
        }
      }
    }
  }

  @Override
  public void visitAnnotationMethod(PsiAnnotationMethod method) {
    PsiType returnType = method.getReturnType();
    PsiAnnotationMemberValue value = method.getDefaultValue();
    if (returnType != null && value != null) {
      myHolder.add(AnnotationsHighlightUtil.checkMemberValueType(value, returnType));
    }

    myHolder.add(AnnotationsHighlightUtil.checkValidAnnotationType(method.getReturnTypeElement()));
    final PsiClass aClass = method.getContainingClass();
    myHolder.add(AnnotationsHighlightUtil.checkCyclicMemberType(method.getReturnTypeElement(), aClass));
    myHolder.add(AnnotationsHighlightUtil.checkClashesWithSuperMethods(method));

    if (!myHolder.hasErrorResults() && aClass != null) {
      myHolder.add(HighlightMethodUtil.checkDuplicateMethod(aClass, method, getDuplicateMethods(aClass)));
    }
  }

  @Override
  public void visitArrayInitializerExpression(PsiArrayInitializerExpression expression) {
    super.visitArrayInitializerExpression(expression);
    if (!myHolder.hasErrorResults()) myHolder.add(HighlightUtil.checkArrayInitializerApplicable(expression));
    if (!(expression.getParent() instanceof PsiNewExpression)) {
      if (!myHolder.hasErrorResults()) myHolder.add(GenericsHighlightUtil.checkGenericArrayCreation(expression, expression.getType()));
    }
  }

  @Override
  public void visitAssignmentExpression(PsiAssignmentExpression assignment) {
    if (!myHolder.hasErrorResults()) myHolder.add(HighlightUtil.checkAssignmentCompatibleTypes(assignment));
    if (!myHolder.hasErrorResults()) myHolder.add(HighlightUtil.checkAssignmentOperatorApplicable(assignment, myFile));
    if (!myHolder.hasErrorResults()) visitExpression(assignment);
  }

  @Override
  public void visitPolyadicExpression(PsiPolyadicExpression expression) {
    super.visitPolyadicExpression(expression);
    if (!myHolder.hasErrorResults()) myHolder.add(HighlightUtil.checkPolyadicOperatorApplicable(expression));
  }

  @Override
  public void visitLambdaExpression(PsiLambdaExpression expression) {
    myHolder.add(checkFeature(expression, Feature.LAMBDA_EXPRESSIONS));
    if (!myHolder.hasErrorResults()) {
      if (LambdaUtil.isValidLambdaContext(expression.getParent())) {
        final PsiType functionalInterfaceType = expression.getFunctionalInterfaceType();
        if (functionalInterfaceType != null) {
          final String notFunctionalMessage = LambdaHighlightingUtil.checkInterfaceFunctional(functionalInterfaceType);
          if (notFunctionalMessage != null) {
            HighlightInfo result =
              HighlightInfo.newHighlightInfo(HighlightInfoType.ERROR).range(expression).descriptionAndTooltip(notFunctionalMessage)
                .create();
            myHolder.add(result);
          }
          else {
            if (!LambdaUtil.isLambdaFullyInferred(expression, functionalInterfaceType) && !expression.hasFormalParameterTypes()) {
              String description = InferenceSession.getInferenceErrorMessage(PsiTreeUtil.getParentOfType(expression, PsiCallExpression.class));
              if (description == null) {
                description = "Cyclic inference";
              }
              HighlightInfo result =
                HighlightInfo.newHighlightInfo(HighlightInfoType.ERROR).range(expression).descriptionAndTooltip(description).create();
              myHolder.add(result);
            }
            else {
              final String incompatibleReturnTypesMessage = LambdaUtil
                .checkReturnTypeCompatible(expression, LambdaUtil.getFunctionalInterfaceReturnType(functionalInterfaceType));
              if (incompatibleReturnTypesMessage != null) {
                final List<PsiExpression> returnExpressions = LambdaUtil.getReturnExpressions(expression);
                final PsiElement returnStatementToHighlight = returnExpressions.size() == 1 ? returnExpressions.get(0) : expression.getBody();
                HighlightInfo result = HighlightInfo.newHighlightInfo(HighlightInfoType.ERROR).range(returnStatementToHighlight != null ? returnStatementToHighlight : expression)
                  .descriptionAndTooltip(incompatibleReturnTypesMessage).create();
                myHolder.add(result);
              }
              else {
                final PsiClassType.ClassResolveResult resolveResult = PsiUtil.resolveGenericsClassInType(functionalInterfaceType);
                final PsiMethod interfaceMethod = LambdaUtil.getFunctionalInterfaceMethod(resolveResult);
                if (interfaceMethod != null) {
                  final PsiParameter[] parameters = interfaceMethod.getParameterList().getParameters();
                  HighlightInfo result = LambdaHighlightingUtil
                    .checkParametersCompatible(expression, parameters, LambdaUtil.getSubstitutor(interfaceMethod, resolveResult));
                  if (result != null) {
                    myHolder.add(result);
                  } else {
                    final PsiClass samClass = resolveResult.getElement();
                    if (!PsiUtil.isAccessible(myFile.getProject(), samClass, expression, null)) {
                      myHolder.add(HighlightInfo.newHighlightInfo(HighlightInfoType.ERROR).range(expression)
                                     .descriptionAndTooltip(HighlightUtil.buildProblemWithAccessDescription(expression, resolveResult)).create());
                    }
                  }
                }
              }
            }
          }
        } else if (LambdaUtil.getFunctionalInterfaceType(expression, true) != null) {
          myHolder.add(HighlightInfo.newHighlightInfo(HighlightInfoType.ERROR).range(expression).descriptionAndTooltip("Cannot infer functional interface type").create());
        }
      }
      else {
        HighlightInfo result = HighlightInfo.newHighlightInfo(HighlightInfoType.ERROR).range(expression)
          .descriptionAndTooltip("Lambda expression not expected here").create();
        myHolder.add(result);
      }
      if (!myHolder.hasErrorResults()) {
        final PsiElement body = expression.getBody();
        if (body instanceof PsiCodeBlock) {
          myHolder.add(HighlightControlFlowUtil.checkUnreachableStatement((PsiCodeBlock)body));
        }
      }
    }
  }

  @Override
  public void visitBreakStatement(PsiBreakStatement statement) {
    super.visitBreakStatement(statement);
    if (!myHolder.hasErrorResults()) {
      myHolder.add(HighlightUtil.checkLabelDefined(statement.getLabelIdentifier(), statement.findExitedStatement()));
    }
    if (!myHolder.hasErrorResults()) myHolder.add(HighlightUtil.checkBreakOutsideLoop(statement));
  }

  @Override
  public void visitClass(PsiClass aClass) {
    super.visitClass(aClass);
    if (aClass instanceof PsiSyntheticClass) return;
    if (!myHolder.hasErrorResults()) myHolder.add(GenericsHighlightUtil.checkInterfaceMultipleInheritance(aClass));
    if (!myHolder.hasErrorResults()) myHolder.add(GenericsHighlightUtil.areSupersAccessible(aClass));
    if (!myHolder.hasErrorResults()) myHolder.add(HighlightClassUtil.checkDuplicateTopLevelClass(aClass));
    if (!myHolder.hasErrorResults()) myHolder.add(GenericsHighlightUtil.checkEnumMustNotBeLocal(aClass));
    if (!myHolder.hasErrorResults()) myHolder.add(GenericsHighlightUtil.checkEnumWithoutConstantsCantHaveAbstractMethods(aClass));
    if (!myHolder.hasErrorResults()) myHolder.add(HighlightUtil.checkImplicitThisReferenceBeforeSuper(aClass, myJavaSdkVersion));
    if (!myHolder.hasErrorResults()) myHolder.add(HighlightClassUtil.checkClassAndPackageConflict(aClass));
    if (!myHolder.hasErrorResults()) myHolder.add(HighlightClassUtil.checkPublicClassInRightFile(aClass));
  }

  @Override
  public void visitClassInitializer(PsiClassInitializer initializer) {
    super.visitClassInitializer(initializer);
    if (!myHolder.hasErrorResults()) myHolder.add(HighlightControlFlowUtil.checkInitializerCompleteNormally(initializer));
    if (!myHolder.hasErrorResults()) myHolder.add(HighlightControlFlowUtil.checkUnreachableStatement(initializer.getBody()));
    if (!myHolder.hasErrorResults()) {
      myHolder.add(HighlightClassUtil.checkThingNotAllowedInInterface(initializer, initializer.getContainingClass()));
    }
  }

  @Override
  public void visitClassObjectAccessExpression(PsiClassObjectAccessExpression expression) {
    super.visitClassObjectAccessExpression(expression);
    if (!myHolder.hasErrorResults()) myHolder.add(GenericsHighlightUtil.checkClassObjectAccessExpression(expression));
  }

  @Override
  public void visitComment(PsiComment comment) {
    super.visitComment(comment);
    if (!myHolder.hasErrorResults()) myHolder.add(HighlightUtil.checkUnclosedComment(comment));
    if (myRefCountHolder != null && !myHolder.hasErrorResults()) registerReferencesFromInjectedFragments(comment);
  }

  @Override
  public void visitContinueStatement(PsiContinueStatement statement) {
    super.visitContinueStatement(statement);
    if (!myHolder.hasErrorResults()) {
      myHolder.add(HighlightUtil.checkLabelDefined(statement.getLabelIdentifier(), statement.findContinuedStatement()));
    }
    if (!myHolder.hasErrorResults()) myHolder.add(HighlightUtil.checkContinueOutsideLoop(statement));
  }

  @Override
  public void visitJavaToken(PsiJavaToken token) {
    super.visitJavaToken(token);
    if (!myHolder.hasErrorResults()
        && token.getTokenType() == JavaTokenType.RBRACE
        && token.getParent() instanceof PsiCodeBlock) {

      final PsiElement gParent = token.getParent().getParent();
      final PsiCodeBlock codeBlock;
      final PsiType returnType;
      if (gParent instanceof PsiMethod) {
        PsiMethod method = (PsiMethod)gParent;
        codeBlock = method.getBody();
        returnType = method.getReturnType();
      }
      else if (gParent instanceof PsiLambdaExpression) {
        final PsiElement body = ((PsiLambdaExpression)gParent).getBody();
        if (!(body instanceof PsiCodeBlock)) return;
        codeBlock = (PsiCodeBlock)body;
        returnType = LambdaUtil.getFunctionalInterfaceReturnType((PsiLambdaExpression)gParent);
      }
      else {
        return;
      }
      myHolder.add(HighlightControlFlowUtil.checkMissingReturnStatement(codeBlock, returnType));
    }
  }

  @Override
  public void visitDocComment(PsiDocComment comment) {
    if (!myHolder.hasErrorResults()) myHolder.add(HighlightUtil.checkUnclosedComment(comment));
  }

  @Override
  public void visitDocTagValue(PsiDocTagValue value) {
    PsiReference reference = value.getReference();
    if (reference != null) {
      PsiElement element = reference.resolve();
      final TextAttributesScheme colorsScheme = myHolder.getColorsScheme();
      if (element instanceof PsiMethod) {
        myHolder.add(HighlightNamesUtil.highlightMethodName((PsiMethod)element, ((PsiDocMethodOrFieldRef)value).getNameElement(), false,
                                                            colorsScheme));
      }
      else if (element instanceof PsiParameter) {
        myHolder.add(HighlightNamesUtil.highlightVariableName((PsiVariable)element, value.getNavigationElement(), colorsScheme));
      }
    }
  }

  @Override
  public void visitEnumConstant(PsiEnumConstant enumConstant) {
    super.visitEnumConstant(enumConstant);
    if (!myHolder.hasErrorResults()) GenericsHighlightUtil.checkEnumConstantForConstructorProblems(enumConstant, myHolder, myJavaSdkVersion);
    if (!myHolder.hasErrorResults()) registerConstructorCall(enumConstant);
  }

  @Override
  public void visitEnumConstantInitializer(PsiEnumConstantInitializer enumConstantInitializer) {
    super.visitEnumConstantInitializer(enumConstantInitializer);
    if (!myHolder.hasErrorResults()) {
      TextRange textRange = HighlightNamesUtil.getClassDeclarationTextRange(enumConstantInitializer);
      myHolder.add(HighlightClassUtil.checkClassMustBeAbstract(enumConstantInitializer, textRange));
    }
  }

  @Override
  public void visitExpression(PsiExpression expression) {
    ProgressManager.checkCanceled(); // visitLiteralExpression is invoked very often in array initializers

    super.visitExpression(expression);
    PsiType type = expression.getType();
    if (myHolder.add(HighlightUtil.checkMustBeBoolean(expression, type))) return;

    if (expression instanceof PsiArrayAccessExpression) {
      myHolder.add(HighlightUtil.checkValidArrayAccessExpression((PsiArrayAccessExpression)expression));
    }

    if (expression.getParent() instanceof PsiNewExpression
        && ((PsiNewExpression)expression.getParent()).getQualifier() != expression
        && ((PsiNewExpression)expression.getParent()).getArrayInitializer() != expression) {
      // like in 'new String["s"]'
      myHolder.add(HighlightUtil.checkAssignability(PsiType.INT, expression.getType(), expression, expression));
    }
    if (!myHolder.hasErrorResults()) myHolder.add(HighlightControlFlowUtil.checkCannotWriteToFinal(expression,myFile));
    if (!myHolder.hasErrorResults()) myHolder.add(HighlightUtil.checkVariableExpected(expression));
    if (!myHolder.hasErrorResults()) myHolder.addAll(HighlightUtil.checkArrayInitializer(expression, type));
    if (!myHolder.hasErrorResults()) myHolder.add(HighlightUtil.checkTernaryOperatorConditionIsBoolean(expression, type));
    if (!myHolder.hasErrorResults()) myHolder.add(HighlightUtil.checkAssertOperatorTypes(expression, type));
    if (!myHolder.hasErrorResults()) myHolder.add(HighlightUtil.checkSynchronizedExpressionType(expression, type,myFile));
    if (!myHolder.hasErrorResults()) myHolder.add(HighlightUtil.checkConditionalExpressionBranchTypesMatch(expression, type));
    if (!myHolder.hasErrorResults()
        && expression.getParent() instanceof PsiThrowStatement
        && ((PsiThrowStatement)expression.getParent()).getException() == expression) {
      myHolder.add(HighlightUtil.checkMustBeThrowable(type, expression, true));
    }

    if (!myHolder.hasErrorResults()) {
      myHolder.add(AnnotationsHighlightUtil.checkConstantExpression(expression));
    }
  }

  @Override
  public void visitExpressionList(PsiExpressionList list) {
    super.visitExpressionList(list);
    PsiElement parent = list.getParent();
    if (parent instanceof PsiMethodCallExpression) {
      PsiMethodCallExpression expression = (PsiMethodCallExpression)parent;
      if (expression.getArgumentList() == list) {
        PsiReferenceExpression referenceExpression = expression.getMethodExpression();
        JavaResolveResult result;
        JavaResolveResult[] results;
        try {
          results = resolveOptimised(referenceExpression);
          result = results.length == 1 ? results[0] : JavaResolveResult.EMPTY;
        }
        catch (IndexNotReadyException e) {
          return;
        }
        PsiElement resolved = result.getElement();

        if ((!result.isAccessible() || !result.isStaticsScopeCorrect()) &&
            !HighlightMethodUtil.isDummyConstructorCall(expression, myResolveHelper, list, referenceExpression) &&
            // this check is for fake expression from JspMethodCallImpl
            referenceExpression.getParent() == expression) {
          try {
            myHolder.add(HighlightMethodUtil.checkAmbiguousMethodCallArguments(referenceExpression, results, list, resolved, result, expression, myResolveHelper));
          }
          catch (IndexNotReadyException ignored) {
          }
        }
      }
    }
  }

  @Override
  public void visitField(PsiField field) {
    super.visitField(field);
    if (!myHolder.hasErrorResults()) myHolder.add(HighlightControlFlowUtil.checkFinalFieldInitialized(field));
  }

  @Override
  public void visitForStatement(PsiForStatement statement) {
    myHolder.add(HighlightUtil.checkForStatement(statement));
  }

  @Override
  public void visitForeachStatement(PsiForeachStatement statement) {
    myHolder.add(checkFeature(statement, Feature.FOR_EACH));
    if (!myHolder.hasErrorResults()) myHolder.add(GenericsHighlightUtil.checkForeachLoopParameterType(statement));
  }

  @Override
  public void visitImportStaticStatement(PsiImportStaticStatement statement) {
    myHolder.add(checkFeature(statement, Feature.STATIC_IMPORTS));
  }

  @Override
  public void visitIdentifier(final PsiIdentifier identifier) {
    TextAttributesScheme colorsScheme = myHolder.getColorsScheme();

    PsiElement parent = identifier.getParent();
    if (parent instanceof PsiVariable) {
      PsiVariable variable = (PsiVariable)parent;
      myHolder.add(HighlightUtil.checkVariableAlreadyDefined(variable));

      if (variable.getInitializer() == null) {
        final PsiElement child = variable.getLastChild();
        if (child instanceof PsiErrorElement && child.getPrevSibling() == identifier) return;
      }

      boolean isMethodParameter = variable instanceof PsiParameter && ((PsiParameter)variable).getDeclarationScope() instanceof PsiMethod;
      if (isMethodParameter) {
        myReassignedParameters.put((PsiParameter)variable, 1); // mark param as present in current file
      }
      else {
        // method params are highlighted in visitMethod since we should make sure the method body was visited before
        if (HighlightControlFlowUtil.isReassigned(variable, myFinalVarProblems)) {
          myHolder.add(HighlightNamesUtil.highlightReassignedVariable(variable, identifier));
        }
        else {
          myHolder.add(HighlightNamesUtil.highlightVariableName(variable, identifier, colorsScheme));
        }
      }

      myHolder.add(HighlightUtil.checkUnderscore(identifier, variable, myLanguageLevel));
    }
    else if (parent instanceof PsiClass) {
      PsiClass aClass = (PsiClass)parent;
      if (aClass.isAnnotationType()) {
        myHolder.add(checkFeature(identifier, Feature.ANNOTATIONS));
      }

      myHolder.add(HighlightClassUtil.checkClassAlreadyImported(aClass, identifier));
      if (!(parent instanceof PsiAnonymousClass) && aClass.getNameIdentifier() == identifier) {
        myHolder.add(HighlightNamesUtil.highlightClassName(aClass, identifier, colorsScheme));
      }
      if (!myHolder.hasErrorResults() && myLanguageLevel.isAtLeast(LanguageLevel.JDK_1_8)) {
        myHolder.add(GenericsHighlightUtil.checkUnrelatedDefaultMethods(aClass, aClass.getVisibleSignatures(), identifier));
      }
    }
    else if (parent instanceof PsiMethod) {
      PsiMethod method = (PsiMethod)parent;
      if (method.isConstructor()) {
        myHolder.add(HighlightMethodUtil.checkConstructorName(method));
      }
      myHolder.add(HighlightNamesUtil.highlightMethodName(method, identifier, true, colorsScheme));
      final PsiClass aClass = method.getContainingClass();
      if (aClass != null) {
        myHolder.add(GenericsHighlightUtil.checkDefaultMethodOverrideEquivalentToObjectNonPrivate(myLanguageLevel, aClass, method, identifier));
      }
    }

    super.visitIdentifier(identifier);
  }

  @Override
  public void visitImportStatement(final PsiImportStatement statement) {
    if (!myHolder.hasErrorResults()) {
      myHolder.add(HighlightUtil.checkSingleImportClassConflict(statement, mySingleImportedClasses,myFile));
    }
  }

  @Override
  public void visitImportStaticReferenceElement(final PsiImportStaticReferenceElement ref) {
    final String refName = ref.getReferenceName();
    final JavaResolveResult[] results = ref.multiResolve(false);

    final PsiElement referenceNameElement = ref.getReferenceNameElement();
    if (results.length == 0) {
      final String description = JavaErrorMessages.message("cannot.resolve.symbol", refName);
      assert referenceNameElement != null : ref;
      final HighlightInfo info =
        HighlightInfo.newHighlightInfo(HighlightInfoType.WRONG_REF).range(referenceNameElement).descriptionAndTooltip(description).create();
      QuickFixAction.registerQuickFixAction(info, QuickFixFactory.getInstance().createSetupJDKFix());
      myHolder.add(info);
    }
    else {
      final PsiManager manager = ref.getManager();
      for (JavaResolveResult result : results) {
        final PsiElement element = result.getElement();

        String description = null;
        if (element instanceof PsiClass) {
          final Pair<PsiImportStaticReferenceElement, PsiClass> imported = mySingleImportedClasses.get(refName);
          final PsiClass aClass = imported == null ? null : imported.getSecond();
          if (aClass != null && !manager.areElementsEquivalent(aClass, element)) {
            description = imported.first == null
                          ? JavaErrorMessages.message("single.import.class.conflict", refName)
                          : imported.first.equals(ref)
                            ? JavaErrorMessages.message("class.is.ambiguous.in.single.static.import", refName)
                            : JavaErrorMessages.message("class.is.already.defined.in.single.static.import", refName);
          }
          mySingleImportedClasses.put(refName, Pair.create(ref, (PsiClass)element));
        }
        else if (element instanceof PsiField) {
          final Pair<PsiImportStaticReferenceElement, PsiField> imported = mySingleImportedFields.get(refName);
          final PsiField field = imported == null ? null : imported.getSecond();
          if (field != null && !manager.areElementsEquivalent(field, element)) {
            description = imported.first.equals(ref)
                          ? JavaErrorMessages.message("field.is.ambiguous.in.single.static.import", refName)
                          : JavaErrorMessages.message("field.is.already.defined.in.single.static.import", refName);
          }
          mySingleImportedFields.put(refName, Pair.create(ref, (PsiField)element));
        }

        if (description != null) {
          myHolder.add(HighlightInfo.newHighlightInfo(HighlightInfoType.ERROR).range(ref).descriptionAndTooltip(description).create());
        }
      }
    }
    if (!myHolder.hasErrorResults()) {
      final PsiElement resolved = results.length == 1 ? results[0].getElement() : null;
      final TextAttributesScheme colorsScheme = myHolder.getColorsScheme();
      if (resolved instanceof PsiClass) {
        myHolder.add(HighlightNamesUtil.highlightClassName((PsiClass)resolved, ref, colorsScheme));
      }
      else{
        myHolder.add(HighlightNamesUtil.highlightClassNameInQualifier(ref, colorsScheme));
        if (resolved instanceof PsiVariable) {
          myHolder.add(HighlightNamesUtil.highlightVariableName((PsiVariable)resolved, referenceNameElement, colorsScheme));
        }
        else if (resolved instanceof PsiMethod) {
          myHolder.add(HighlightNamesUtil.highlightMethodName((PsiMethod)resolved, referenceNameElement, false, colorsScheme));
        }
      }
    }
  }

  @Override
  public void visitInstanceOfExpression(PsiInstanceOfExpression expression) {
    super.visitInstanceOfExpression(expression);
    if (!myHolder.hasErrorResults()) myHolder.add(HighlightUtil.checkInstanceOfApplicable(expression));
    if (!myHolder.hasErrorResults()) myHolder.add(GenericsHighlightUtil.checkInstanceOfGenericType(expression));
  }

  @Override
  public void visitKeyword(PsiKeyword keyword) {
    super.visitKeyword(keyword);
    PsiElement parent = keyword.getParent();
    String text = keyword.getText();
    if (parent instanceof PsiModifierList) {
      PsiModifierList psiModifierList = (PsiModifierList)parent;
      if (!myHolder.hasErrorResults()) myHolder.add(HighlightUtil.checkNotAllowedModifier(keyword, psiModifierList));
      if (!myHolder.hasErrorResults()) myHolder.add(HighlightUtil.checkIllegalModifierCombination(keyword, psiModifierList));
      if (PsiModifier.ABSTRACT.equals(text) && psiModifierList.getParent() instanceof PsiMethod) {
        if (!myHolder.hasErrorResults()) {
          myHolder.add(HighlightMethodUtil.checkAbstractMethodInConcreteClass((PsiMethod)psiModifierList.getParent(), keyword));
        }
      }
    }
    else if (PsiKeyword.INTERFACE.equals(text) && parent instanceof PsiClass) {
      if (!myHolder.hasErrorResults()) myHolder.add(HighlightClassUtil.checkInterfaceCannotBeLocal((PsiClass)parent));
    }
    if (!myHolder.hasErrorResults()) myHolder.add(HighlightClassUtil.checkStaticDeclarationInInnerClass(keyword));
    if (!myHolder.hasErrorResults()) myHolder.add(HighlightUtil.checkIllegalVoidType(keyword));

    if (PsiTreeUtil.getParentOfType(keyword, PsiDocTagValue.class) != null) {
      HighlightInfo result = HighlightInfo.newHighlightInfo(JavaHighlightInfoTypes.JAVA_KEYWORD).range(keyword).create();
      myHolder.add(result);
    }
  }

  @Override
  public void visitLabeledStatement(PsiLabeledStatement statement) {
    super.visitLabeledStatement(statement);
    if (!myHolder.hasErrorResults()) myHolder.add(HighlightUtil.checkLabelWithoutStatement(statement));
    if (!myHolder.hasErrorResults()) myHolder.add(HighlightUtil.checkLabelAlreadyInUse(statement));
  }

  @Override
  public void visitLiteralExpression(PsiLiteralExpression expression) {
    super.visitLiteralExpression(expression);
    if (myHolder.hasErrorResults()) return;
    myHolder.add(HighlightUtil.checkLiteralExpressionParsingError(expression, myLanguageLevel,myFile));
    if (myRefCountHolder != null && !myHolder.hasErrorResults()) registerReferencesFromInjectedFragments(expression);
  }

  @Override
  public void visitMethod(PsiMethod method) {
    super.visitMethod(method);
    if (!myHolder.hasErrorResults()) myHolder.add(HighlightControlFlowUtil.checkUnreachableStatement(method.getBody()));
    if (!myHolder.hasErrorResults()) myHolder.add(HighlightMethodUtil.checkConstructorHandleSuperClassExceptions(method));
    if (!myHolder.hasErrorResults()) myHolder.add(HighlightMethodUtil.checkRecursiveConstructorInvocation(method));
    if (!myHolder.hasErrorResults()) myHolder.add(GenericsHighlightUtil.checkOverrideAnnotation(method, myLanguageLevel));
    if (!myHolder.hasErrorResults()) myHolder.add(GenericsHighlightUtil.checkSafeVarargsAnnotation(method, myLanguageLevel));

    PsiClass aClass = method.getContainingClass();
    if (!myHolder.hasErrorResults() && method.isConstructor()) {
      myHolder.add(HighlightClassUtil.checkThingNotAllowedInInterface(method, aClass));
    }
    if (!myHolder.hasErrorResults() && method.hasModifierProperty(PsiModifier.DEFAULT)) {
      myHolder.add(checkFeature(method, Feature.EXTENSION_METHODS));
    }
    if (!myHolder.hasErrorResults() && aClass != null && aClass.isInterface() && method.hasModifierProperty(PsiModifier.STATIC)) {
      myHolder.add(checkFeature(method, Feature.EXTENSION_METHODS));
    }
    if (!myHolder.hasErrorResults() && aClass != null) {
      myHolder.add(HighlightMethodUtil.checkDuplicateMethod(aClass, method, getDuplicateMethods(aClass)));
    }

    // method params are highlighted in visitMethod since we should make sure the method body was visited before
    PsiParameter[] parameters = method.getParameterList().getParameters();
    final TextAttributesScheme colorsScheme = myHolder.getColorsScheme();

    for (PsiParameter parameter : parameters) {
      int info = myReassignedParameters.get(parameter);
      if (info == 0) continue; // out of this file
      if (info == 2) {// reassigned
        myHolder.add(HighlightNamesUtil.highlightReassignedVariable(parameter, parameter.getNameIdentifier()));
      }
      else {
        myHolder.add(HighlightNamesUtil.highlightVariableName(parameter, parameter.getNameIdentifier(), colorsScheme));
      }
    }
  }

  private void highlightReferencedMethodOrClassName(PsiJavaCodeReferenceElement element, PsiElement resolved) {
    PsiElement parent = element.getParent();
    if (parent instanceof PsiReferenceExpression || parent instanceof PsiJavaCodeReferenceElement) {
      return;
    }
    final TextAttributesScheme colorsScheme = myHolder.getColorsScheme();
    if (parent instanceof PsiMethodCallExpression) {
      PsiMethod method = ((PsiMethodCallExpression)parent).resolveMethod();
      PsiElement methodNameElement = element.getReferenceNameElement();
      if (method != null && methodNameElement != null&& !(methodNameElement instanceof PsiKeyword)) {
        myHolder.add(HighlightNamesUtil.highlightMethodName(method, methodNameElement, false, colorsScheme));
        myHolder.add(HighlightNamesUtil.highlightClassNameInQualifier(element, colorsScheme));
      }
    }
    else if (parent instanceof PsiConstructorCall) {
      try {
        PsiMethod method = ((PsiConstructorCall)parent).resolveConstructor();
        if (method == null) {
          if (resolved instanceof PsiClass) {
            myHolder.add(HighlightNamesUtil.highlightClassName((PsiClass)resolved, element, colorsScheme));
          }
        }
        else {
          final PsiElement referenceNameElement = element.getReferenceNameElement();
          if(referenceNameElement != null) {
            // exclude type parameters from the highlighted text range
            TextRange range = new TextRange(element.getTextRange().getStartOffset(), referenceNameElement.getTextRange().getEndOffset());
            myHolder.add(HighlightNamesUtil.highlightMethodName(method, referenceNameElement, range, colorsScheme, false));
          }
        }
      }
      catch (IndexNotReadyException ignored) {
      }
    }
    else if (parent instanceof PsiImportStatement && ((PsiImportStatement)parent).isOnDemand()) {
      // highlight on demand import as class
      myHolder.add(HighlightNamesUtil.highlightClassName(null, element, colorsScheme));
    }
    else if (resolved instanceof PsiClass) {
      myHolder.add(HighlightNamesUtil.highlightClassName((PsiClass)resolved, element, colorsScheme));
    }
  }

  @Override
  public void visitMethodCallExpression(PsiMethodCallExpression expression) {
    if (!myHolder.hasErrorResults()) myHolder.add(GenericsHighlightUtil.checkEnumSuperConstructorCall(expression));
    if (!myHolder.hasErrorResults()) myHolder.add(HighlightClassUtil.checkSuperQualifierType(myFile.getProject(), expression));
    // in case of JSP synthetic method call, do not check
    if (myFile.isPhysical() && !myHolder.hasErrorResults()) {
      try {
        myHolder.add(HighlightMethodUtil.checkMethodCall(expression, myResolveHelper, myLanguageLevel,myJavaSdkVersion));
      }
      catch (IndexNotReadyException ignored) {
      }
    }

    if (!myHolder.hasErrorResults()) myHolder.add(HighlightMethodUtil.checkConstructorCallMustBeFirstStatement(expression));
    if (!myHolder.hasErrorResults()) myHolder.add(HighlightMethodUtil.checkSuperAbstractMethodDirectCall(expression));

    if (!myHolder.hasErrorResults()) visitExpression(expression);
  }

  @Override
  public void visitModifierList(PsiModifierList list) {
    super.visitModifierList(list);
    PsiElement parent = list.getParent();
    if (parent instanceof PsiMethod) {
      PsiMethod method = (PsiMethod)parent;
      if (!myHolder.hasErrorResults()) myHolder.add(HighlightMethodUtil.checkMethodCanHaveBody(method, myLanguageLevel));
      MethodSignatureBackedByPsiMethod methodSignature = MethodSignatureBackedByPsiMethod.create(method, PsiSubstitutor.EMPTY);
      if (!method.isConstructor()) {
        try {
          List<HierarchicalMethodSignature> superMethodSignatures = method.getHierarchicalMethodSignature().getSuperSignatures();
          if (!superMethodSignatures.isEmpty()) {
            if (!myHolder.hasErrorResults()) myHolder.add(HighlightMethodUtil.checkMethodIncompatibleReturnType(methodSignature, superMethodSignatures, true, myLanguageLevel));
            if (!myHolder.hasErrorResults()) myHolder.add(HighlightMethodUtil.checkMethodIncompatibleThrows(methodSignature, superMethodSignatures, true, method.getContainingClass()));
            if (!method.hasModifierProperty(PsiModifier.STATIC)) {
              if (!myHolder.hasErrorResults()) myHolder.add(HighlightMethodUtil.checkMethodWeakerPrivileges(methodSignature, superMethodSignatures, true, myFile));
              if (!myHolder.hasErrorResults()) myHolder.add(HighlightMethodUtil.checkMethodOverridesFinal(methodSignature, superMethodSignatures));
            }
          }
        }
        catch (IndexNotReadyException ignored) {
        }
      }
      PsiClass aClass = method.getContainingClass();
      if (!myHolder.hasErrorResults()) myHolder.add(HighlightMethodUtil.checkMethodMustHaveBody(method, aClass));
      if (!myHolder.hasErrorResults()) myHolder.add(HighlightMethodUtil.checkConstructorCallsBaseClassConstructor(method, myRefCountHolder, myResolveHelper));
      if (!myHolder.hasErrorResults()) myHolder.add(HighlightMethodUtil.checkStaticMethodOverride(method,myFile));
    }
    else if (parent instanceof PsiClass) {
      PsiClass aClass = (PsiClass)parent;
      try {
        if (!myHolder.hasErrorResults()) myHolder.add(HighlightClassUtil.checkDuplicateNestedClass(aClass));
        if (!myHolder.hasErrorResults()) {
          TextRange textRange = HighlightNamesUtil.getClassDeclarationTextRange(aClass);
          myHolder.add(HighlightClassUtil.checkClassMustBeAbstract(aClass, textRange));
        }
        if (!myHolder.hasErrorResults()) {
          myHolder.add(HighlightClassUtil.checkClassDoesNotCallSuperConstructorOrHandleExceptions(aClass, myRefCountHolder, myResolveHelper));
        }
        if (!myHolder.hasErrorResults()) myHolder.add(HighlightMethodUtil.checkOverrideEquivalentInheritedMethods(aClass, myFile, myLanguageLevel));
        if (!myHolder.hasErrorResults()) myHolder.addAll(GenericsHighlightUtil.checkOverrideEquivalentMethods(myLanguageLevel, aClass));
        if (!myHolder.hasErrorResults()) myHolder.add(HighlightClassUtil.checkCyclicInheritance(aClass));
      }
      catch (IndexNotReadyException ignored) {
      }
    }
    else if (parent instanceof PsiEnumConstant) {
      if (!myHolder.hasErrorResults()) myHolder.addAll(GenericsHighlightUtil.checkEnumConstantModifierList(list));
    }
  }

  @Override
  public void visitNameValuePair(PsiNameValuePair pair) {
    myHolder.add(AnnotationsHighlightUtil.checkNameValuePair(pair));
    if (!myHolder.hasErrorResults()) {
      PsiIdentifier nameId = pair.getNameIdentifier();
      if (nameId != null) {
        HighlightInfo result = HighlightInfo.newHighlightInfo(HighlightInfoType.ANNOTATION_ATTRIBUTE_NAME).range(nameId).create();
        myHolder.add(result);
      }
    }
  }

  @Override
  public void visitNewExpression(PsiNewExpression expression) {
    final PsiType type = expression.getType();
    final PsiClass aClass = PsiUtil.resolveClassInType(type);
    myHolder.add(HighlightUtil.checkUnhandledExceptions(expression, null));
    if (!myHolder.hasErrorResults()) myHolder.add(HighlightClassUtil.checkAnonymousInheritFinal(expression));
    if (!myHolder.hasErrorResults()) myHolder.add(HighlightClassUtil.checkQualifiedNew(expression, type, aClass));
    if (!myHolder.hasErrorResults()) myHolder.add(HighlightClassUtil.checkCreateInnerClassFromStaticContext(expression, type, aClass));
    if (!myHolder.hasErrorResults()) myHolder.add(GenericsHighlightUtil.checkTypeParameterInstantiation(expression));
    if (!myHolder.hasErrorResults()) myHolder.add(HighlightClassUtil.checkInstantiationOfAbstractClass(aClass, expression));
    try {
      if (!myHolder.hasErrorResults()) HighlightMethodUtil.checkNewExpression(expression, type, myHolder, myJavaSdkVersion);
    }
    catch (IndexNotReadyException ignored) {
    }
    if (!myHolder.hasErrorResults()) myHolder.add(GenericsHighlightUtil.checkEnumInstantiation(expression, aClass));
    if (!myHolder.hasErrorResults()) myHolder.add(GenericsHighlightUtil.checkGenericArrayCreation(expression, type));
    if (!myHolder.hasErrorResults()) registerConstructorCall(expression);

    if (!myHolder.hasErrorResults()) visitExpression(expression);
  }

  @Override
  public void visitPackageStatement(PsiPackageStatement statement) {
    super.visitPackageStatement(statement);
    myHolder.add(AnnotationsHighlightUtil.checkPackageAnnotationContainingFile(statement));
  }

  @Override
  public void visitParameter(PsiParameter parameter) {
    super.visitParameter(parameter);

    final PsiElement parent = parameter.getParent();
    if (parent instanceof PsiParameterList && parameter.isVarArgs()) {
      if (!myHolder.hasErrorResults()) myHolder.add(checkFeature(parameter, Feature.VARARGS));
      if (!myHolder.hasErrorResults()) myHolder.add(GenericsHighlightUtil.checkVarArgParameterIsLast(parameter));
    }
    else if (parent instanceof PsiCatchSection) {
      if (!myHolder.hasErrorResults() && parameter.getType() instanceof PsiDisjunctionType) {
        myHolder.add(checkFeature(parameter, Feature.MULTI_CATCH));
      }
      if (!myHolder.hasErrorResults()) myHolder.add(HighlightUtil.checkCatchParameterIsThrowable(parameter));
      if (!myHolder.hasErrorResults()) myHolder.addAll(GenericsHighlightUtil.checkCatchParameterIsClass(parameter));
      if (!myHolder.hasErrorResults()) myHolder.addAll(HighlightUtil.checkCatchTypeIsDisjoint(parameter));
    }
  }

  @Override
  public void visitParameterList(PsiParameterList list) {
    super.visitParameterList(list);
    if (!myHolder.hasErrorResults()) myHolder.add(HighlightUtil.checkAnnotationMethodParameters(list));
  }

  @Override
  public void visitPostfixExpression(PsiPostfixExpression expression) {
    super.visitPostfixExpression(expression);
    if (!myHolder.hasErrorResults()) {
      myHolder.add(HighlightUtil.checkUnaryOperatorApplicable(expression.getOperationSign(), expression.getOperand()));
    }
  }

  @Override
  public void visitPrefixExpression(PsiPrefixExpression expression) {
    super.visitPrefixExpression(expression);
    if (!myHolder.hasErrorResults()) {
      myHolder.add(HighlightUtil.checkUnaryOperatorApplicable(expression.getOperationSign(), expression.getOperand()));
    }
  }

  private void registerConstructorCall(@NotNull PsiConstructorCall constructorCall) {
    if (myRefCountHolder != null) {
      JavaResolveResult resolveResult = constructorCall.resolveMethodGenerics();
      final PsiElement resolved = resolveResult.getElement();
      if (resolved instanceof PsiNamedElement) {
        myRefCountHolder.registerLocallyReferenced((PsiNamedElement)resolved);
      }
    }
  }

  @Override
  public void visitReferenceElement(PsiJavaCodeReferenceElement ref) {
    JavaResolveResult resolveResult = doVisitReferenceElement(ref);
    if (resolveResult != null && !myHolder.hasErrorResults()) myHolder.add(GenericsHighlightUtil.checkRawOnParameterizedType(ref, resolveResult.getElement()));
  }

  private JavaResolveResult doVisitReferenceElement(@NotNull PsiJavaCodeReferenceElement ref) {
    JavaResolveResult result;
    try {
      result = resolveOptimised(ref);
    }
    catch (IndexNotReadyException e) {
      return null;
    }
    PsiElement resolved = result.getElement();
    PsiElement parent = ref.getParent();

    if (myRefCountHolder != null) {
      myRefCountHolder.registerReference(ref, result);
    }
    myHolder.add(HighlightUtil.checkReference(ref, result, myFile, myLanguageLevel));
    if (parent instanceof PsiJavaCodeReferenceElement || ref.isQualified()) {
      if (!myHolder.hasErrorResults() && resolved instanceof PsiTypeParameter) {
        boolean cannotSelectFromTypeParameter = !myJavaSdkVersion.isAtLeast(JavaSdkVersion.JDK_1_7);
        if (!cannotSelectFromTypeParameter) {
          final PsiClass containingClass = PsiTreeUtil.getParentOfType(ref, PsiClass.class);
          if (containingClass != null) {
            if (PsiTreeUtil.isAncestor(containingClass.getExtendsList(), ref, false) ||
                PsiTreeUtil.isAncestor(containingClass.getImplementsList(), ref, false)) {
              cannotSelectFromTypeParameter = true;
            }
          }
        }
        if (cannotSelectFromTypeParameter) {
          myHolder.add(HighlightInfo.newHighlightInfo(HighlightInfoType.ERROR).descriptionAndTooltip("Cannot select from a type parameter").range(ref).create());
        }
      }
    }
    if (!myHolder.hasErrorResults()) myHolder.add(HighlightClassUtil.checkAbstractInstantiation(ref, resolved));
    if (!myHolder.hasErrorResults()) myHolder.add(HighlightClassUtil.checkExtendsDuplicate(ref, resolved,myFile));
    if (!myHolder.hasErrorResults()) myHolder.add(HighlightClassUtil.checkClassExtendsForeignInnerClass(ref, resolved));
    if (!myHolder.hasErrorResults()) myHolder.add(GenericsHighlightUtil.checkSelectStaticClassFromParameterizedType(resolved, ref));
    if (!myHolder.hasErrorResults()) myHolder.add(GenericsHighlightUtil.checkParameterizedReferenceTypeArguments(resolved, ref,
                                                                                                                 result.getSubstitutor(),
                                                                                                                 myJavaSdkVersion));
    if (!myHolder.hasErrorResults()) myHolder.add(GenericsHighlightUtil.checkCannotPassInner(ref));

    if (resolved != null && parent instanceof PsiReferenceList) {
      if (!myHolder.hasErrorResults()) {
        PsiReferenceList referenceList = (PsiReferenceList)parent;
        myHolder.add(HighlightUtil.checkElementInReferenceList(ref, referenceList, result, myLanguageLevel));
      }
    }

    if (parent instanceof PsiAnonymousClass && ref.equals(((PsiAnonymousClass)parent).getBaseClassReference())) {
      PsiClass aClass = (PsiClass)parent;
      myHolder.addAll(GenericsHighlightUtil.checkOverrideEquivalentMethods(myLanguageLevel, aClass));
    }

    if (resolved instanceof PsiVariable) {
      PsiVariable variable = (PsiVariable)resolved;

      final PsiClass containingClass = PsiTreeUtil.getParentOfType(ref, PsiClass.class);
      if (containingClass instanceof PsiAnonymousClass &&
          !PsiTreeUtil.isAncestor(containingClass, variable, false) &&
          !(variable instanceof PsiField)) {
        if (!PsiTreeUtil.isAncestor(((PsiAnonymousClass) containingClass).getArgumentList(), ref, false)) {
          myHolder.add(HighlightInfo.newHighlightInfo(HighlightInfoType.IMPLICIT_ANONYMOUS_CLASS_PARAMETER).range(ref).create());
        }
      }

      if (variable instanceof PsiParameter && ref instanceof PsiExpression && PsiUtil.isAccessedForWriting((PsiExpression)ref)) {
        myReassignedParameters.put((PsiParameter)variable, 2);
      }

      final TextAttributesScheme colorsScheme = myHolder.getColorsScheme();
      if (!variable.hasModifierProperty(PsiModifier.FINAL) && isReassigned(variable)) {
        myHolder.add(HighlightNamesUtil.highlightReassignedVariable(variable, ref));
      }
      else {
        myHolder.add(HighlightNamesUtil.highlightVariableName(variable, ref.getReferenceNameElement(), colorsScheme));
      }
      myHolder.add(HighlightNamesUtil.highlightClassNameInQualifier(ref, colorsScheme));
    }
    else {
      highlightReferencedMethodOrClassName(ref, resolved);
    }

    if (parent instanceof PsiNewExpression && !(resolved instanceof PsiClass) && resolved instanceof PsiNamedElement && ((PsiNewExpression)parent).getClassOrAnonymousClassReference() == ref) {
       myHolder.add(HighlightInfo.newHighlightInfo(HighlightInfoType.ERROR).range(ref)
                      .descriptionAndTooltip("Cannot find symbol " + ((PsiNamedElement)resolved).getName()).create());
    }
    if (!myHolder.hasErrorResults() && resolved instanceof PsiClass) {
      final PsiClass aClass = ((PsiClass)resolved).getContainingClass();
      if (aClass != null) {
        final PsiElement qualifier = ref.getQualifier();
        final PsiElement place;
        if (qualifier instanceof PsiJavaCodeReferenceElement) {
          place = ((PsiJavaCodeReferenceElement)qualifier).resolve();
        }
        else {
          if (parent instanceof PsiNewExpression) {
            final PsiExpression newQualifier = ((PsiNewExpression)parent).getQualifier();
            place = newQualifier == null ? ref : PsiUtil.resolveClassInType(newQualifier.getType());
          }
          else {
            place = ref;
          }
        }
        if (place != null && PsiTreeUtil.isAncestor(aClass, place, false) && aClass.hasTypeParameters()) {
          myHolder.add(HighlightClassUtil.checkCreateInnerClassFromStaticContext(ref, place, (PsiClass)resolved));
        }
      }
      else if (resolved instanceof PsiTypeParameter) {
        final PsiTypeParameterListOwner owner = ((PsiTypeParameter)resolved).getOwner();
        if (owner instanceof PsiClass) {
          final PsiClass outerClass = (PsiClass)owner;
          if (!InheritanceUtil.hasEnclosingInstanceInScope(outerClass, ref, false, false)) {
            myHolder.add(HighlightClassUtil.reportIllegalEnclosingUsage(ref, aClass, (PsiClass)owner, ref));
          }
        }
      }
    }

    if (!myHolder.hasErrorResults()) myHolder.add(HighlightUtil.checkPackageAndClassConflict(ref, myFile));

    return result;
  }

  @NotNull
  private JavaResolveResult resolveOptimised(@NotNull PsiJavaCodeReferenceElement ref) {
    JavaResolveResult result;
    if (ref instanceof PsiReferenceExpressionImpl) {
      PsiReferenceExpressionImpl referenceExpression = (PsiReferenceExpressionImpl)ref;
      JavaResolveResult[] results = JavaResolveUtil.resolveWithContainingFile(referenceExpression,
                                                                              PsiReferenceExpressionImpl.OurGenericsResolver.INSTANCE,
                                                                              true, true,
                                                                              myFile);
      result = results.length == 1 ? results[0] : JavaResolveResult.EMPTY;
    }
    else {
      result = ref.advancedResolve(true);
    }
    return result;
  }

  @NotNull
  private JavaResolveResult[] resolveOptimised(@NotNull PsiReferenceExpression expression) {
    JavaResolveResult[] results;
    if (expression instanceof PsiReferenceExpressionImpl) {
      PsiReferenceExpressionImpl referenceExpression = (PsiReferenceExpressionImpl)expression;
      results = JavaResolveUtil.resolveWithContainingFile(referenceExpression,
                                                          PsiReferenceExpressionImpl.OurGenericsResolver.INSTANCE, true, true,
                                                          myFile);
    }
    else {
      results = expression.multiResolve(true);
    }
    return results;
  }

  @Override
  public void visitReferenceExpression(PsiReferenceExpression expression) {
    JavaResolveResult resultForIncompleteCode = doVisitReferenceElement(expression);
    if (!myHolder.hasErrorResults()) {
      visitExpression(expression);
      if (myHolder.hasErrorResults()) return;
    }
    JavaResolveResult result;
    JavaResolveResult[] results;
    try {
      results = resolveOptimised(expression);
      result = results.length == 1 ? results[0] : JavaResolveResult.EMPTY;
    }
    catch (IndexNotReadyException e) {
      return;
    }
    PsiElement resolved = result.getElement();
    if (resolved instanceof PsiVariable && resolved.getContainingFile() == expression.getContainingFile()) {
      if (!myHolder.hasErrorResults()) {
        try {
          myHolder.add(HighlightControlFlowUtil.checkVariableInitializedBeforeUsage(expression, (PsiVariable)resolved, myUninitializedVarProblems,myFile));
        }
        catch (IndexNotReadyException ignored) {
        }
      }
      PsiVariable variable = (PsiVariable)resolved;
      boolean isFinal = variable.hasModifierProperty(PsiModifier.FINAL);
      if (isFinal && !variable.hasInitializer()) {
        if (!myHolder.hasErrorResults()) {
          myHolder.add(HighlightControlFlowUtil.checkFinalVariableMightAlreadyHaveBeenAssignedTo(variable, expression, myFinalVarProblems));
        }
        if (!myHolder.hasErrorResults()) myHolder.add(HighlightControlFlowUtil.checkFinalVariableInitializedInLoop(expression, resolved));
      }
    }

    PsiElement parent = expression.getParent();
    if (parent instanceof PsiMethodCallExpression && ((PsiMethodCallExpression)parent).getMethodExpression() == expression && (!result.isAccessible() || !result.isStaticsScopeCorrect())) {
      PsiMethodCallExpression methodCallExpression = (PsiMethodCallExpression)parent;
      PsiExpressionList list = methodCallExpression.getArgumentList();
      if (!HighlightMethodUtil.isDummyConstructorCall(methodCallExpression, myResolveHelper, list, expression)) {
        try {
          myHolder.add(HighlightMethodUtil.checkAmbiguousMethodCallIdentifier(expression, results, list, resolved, result,
                                                                              methodCallExpression, myResolveHelper));
        }
        catch (IndexNotReadyException ignored) {
        }
      }
    }

    if (!myHolder.hasErrorResults()) myHolder.add(HighlightUtil.checkExpressionRequired(expression, resultForIncompleteCode));
    if (!myHolder.hasErrorResults() && resolved instanceof PsiField) {
      try {
        myHolder.add(HighlightUtil.checkIllegalForwardReferenceToField(expression, (PsiField)resolved));
      }
      catch (IndexNotReadyException ignored) {
      }
    }
    if (!myHolder.hasErrorResults()) myHolder.add(GenericsHighlightUtil.checkAccessStaticFieldFromEnumConstructor(expression, result));
    if (!myHolder.hasErrorResults()) myHolder.add(HighlightUtil.checkClassReferenceAfterQualifier(expression, resolved));
    final PsiExpression qualifierExpression = expression.getQualifierExpression();
    myHolder.add(HighlightUtil.checkUnqualifiedSuperInDefaultMethod(myLanguageLevel, expression, qualifierExpression));
    if (!myHolder.hasErrorResults() && qualifierExpression != null) {
      final PsiClass psiClass = PsiUtil.resolveClassInType(qualifierExpression.getType());
      if (psiClass != null) {
        myHolder.add(GenericsHighlightUtil.areSupersAccessible(psiClass, qualifierExpression));
      }
    }
  }

  @Override
  public void visitMethodReferenceExpression(PsiMethodReferenceExpression expression) {
    myHolder.add(checkFeature(expression, Feature.METHOD_REFERENCES));

    final JavaResolveResult result;
    final JavaResolveResult[] results;
    try {
      results = expression.multiResolve(true);
      result = results.length == 1 ? results[0] : JavaResolveResult.EMPTY;
    }
    catch (IndexNotReadyException e) {
      return;
    }
    if (myRefCountHolder != null) {
      myRefCountHolder.registerReference(expression, result);
    }
    final PsiElement method = result.getElement();
    if (method != null && !result.isAccessible()) {
      final String accessProblem = HighlightUtil.buildProblemWithAccessDescription(expression, result);
      HighlightInfo info = HighlightInfo.newHighlightInfo(HighlightInfoType.ERROR).range(expression).descriptionAndTooltip(accessProblem).create();
      myHolder.add(info);
    } else {
      final TextAttributesScheme colorsScheme = myHolder.getColorsScheme();
      if (method instanceof PsiMethod) {
        final PsiElement methodNameElement = expression.getReferenceNameElement();
        myHolder.add(HighlightNamesUtil.highlightMethodName((PsiMethod)method, methodNameElement, false, colorsScheme));
      }
      myHolder.add(HighlightNamesUtil.highlightClassNameInQualifier(expression, colorsScheme));
    }
    if (!myHolder.hasErrorResults()) {
      final PsiType functionalInterfaceType = expression.getFunctionalInterfaceType();
      if (functionalInterfaceType != null) {
        final boolean notFunctional = !LambdaUtil.isFunctionalType(functionalInterfaceType);
        if (notFunctional) {
          myHolder.add(HighlightInfo.newHighlightInfo(HighlightInfoType.ERROR).range(expression)
                         .descriptionAndTooltip(functionalInterfaceType.getPresentableText() + " is not a functional interface").create());
        }
      }
      if (!myHolder.hasErrorResults()) {
        final PsiElement referenceNameElement = expression.getReferenceNameElement();
        if (referenceNameElement instanceof PsiKeyword) {
          if (!PsiMethodReferenceUtil.isValidQualifier(expression)) {
            final PsiElement qualifier = expression.getQualifier();
            String description = "Cannot find class " + qualifier.getText();
            HighlightInfo result1 =
              HighlightInfo.newHighlightInfo(HighlightInfoType.ERROR).range(qualifier).descriptionAndTooltip(description).create();
            myHolder.add(result1);
          }
        }
      }
      if (!myHolder.hasErrorResults()) {
        final PsiClassType.ClassResolveResult resolveResult = PsiUtil.resolveGenericsClassInType(functionalInterfaceType);
        final PsiClass psiClass = resolveResult.getElement();
        if (psiClass != null && !PsiUtil.isAccessible(myFile.getProject(), psiClass, expression, null)) {
          myHolder.add(HighlightInfo.newHighlightInfo(HighlightInfoType.ERROR).range(expression)
                         .descriptionAndTooltip(HighlightUtil.buildProblemWithAccessDescription(expression, resolveResult)).create());
        }

        final PsiMethod interfaceMethod = LambdaUtil.getFunctionalInterfaceMethod(resolveResult);
        if (interfaceMethod != null) {
          if (!myHolder.hasErrorResults()) {
            final String errorMessage = PsiMethodReferenceUtil.checkMethodReferenceContext(expression);
            if (errorMessage != null) {
              myHolder.add(HighlightInfo.newHighlightInfo(HighlightInfoType.ERROR).range(expression).descriptionAndTooltip(errorMessage).create());
            }
          }

          if (!myHolder.hasErrorResults()) {
            final String badReturnTypeMessage = PsiMethodReferenceUtil.checkReturnType(expression, result, functionalInterfaceType);
            if (badReturnTypeMessage != null) {
              myHolder.add(HighlightInfo.newHighlightInfo(HighlightInfoType.ERROR).range(expression).descriptionAndTooltip(badReturnTypeMessage).create());
            }
          }
        }
      }
    }

    if (!myHolder.hasErrorResults()) {
      PsiElement qualifier = expression.getQualifier();
      if (qualifier instanceof PsiTypeElement) {
        final PsiType psiType = ((PsiTypeElement)qualifier).getType();
        final HighlightInfo genericArrayCreationInfo = GenericsHighlightUtil.checkGenericArrayCreation(qualifier, psiType);
        if (genericArrayCreationInfo != null) {
          myHolder.add(genericArrayCreationInfo);
        } else {
          final String wildcardMessage = PsiMethodReferenceUtil.checkTypeArguments((PsiTypeElement)qualifier, psiType);
          if (wildcardMessage != null) {
            myHolder.add(HighlightInfo.newHighlightInfo(HighlightInfoType.ERROR).range(qualifier).descriptionAndTooltip(wildcardMessage).create());
          }
        }
      }
    }

    if (!myHolder.hasErrorResults()) {
      myHolder.add(PsiMethodReferenceHighlightingUtil.checkRawConstructorReference(expression));
    }

    if (!myHolder.hasErrorResults()) {
      myHolder.add(HighlightUtil.checkUnhandledExceptions(expression, expression.getTextRange()));
    }

    if (!myHolder.hasErrorResults() && method instanceof PsiTypeParameterListOwner) {
      PsiTypeParameter[] typeParameters = ((PsiTypeParameterListOwner)method).getTypeParameters();
      if (method instanceof PsiMethod) {
        final PsiClass containingClass = ((PsiMethod)method).getContainingClass();
        assert containingClass != null : method;
        typeParameters = ArrayUtil.mergeArrays(typeParameters, containingClass.getTypeParameters());
      }
      myHolder.add(GenericsHighlightUtil.checkInferredTypeArguments(typeParameters, expression, result.getSubstitutor()));
    }

    if (!myHolder.hasErrorResults()) {
      if (results.length == 0) {
        String description = null;
        if (expression.isConstructor()) {
          final PsiClass containingClass = PsiMethodReferenceUtil.getQualifierResolveResult(expression).getContainingClass();

          if (containingClass != null) {
            if (!myHolder.add(HighlightClassUtil.checkInstantiationOfAbstractClass(containingClass, expression)) &&
                !myHolder.add(GenericsHighlightUtil.checkEnumInstantiation(expression, containingClass)) &&
                containingClass.isPhysical()) {
              description = JavaErrorMessages.message("cannot.resolve.constructor", containingClass.getName());
            }
          }
        }
        else {
          description = JavaErrorMessages.message("cannot.resolve.method", expression.getReferenceName());
        }

        if (description != null) {
          final PsiElement referenceNameElement = expression.getReferenceNameElement();
          final HighlightInfo highlightInfo =
            HighlightInfo.newHighlightInfo(HighlightInfoType.WRONG_REF).descriptionAndTooltip(description).range(referenceNameElement).create();
          myHolder.add(highlightInfo);
          final TextRange fixRange = HighlightMethodUtil.getFixRange(referenceNameElement);
          QuickFixAction.registerQuickFixAction(highlightInfo, fixRange, QuickFixFactory.getInstance().createCreateMethodFromUsageFix(expression));
        }
      }
    }
  }

  @Override
  public void visitReferenceList(PsiReferenceList list) {
    if (list.getFirstChild() == null) return;
    PsiElement parent = list.getParent();
    if (!(parent instanceof PsiTypeParameter)) {
      myHolder.add(AnnotationsHighlightUtil.checkAnnotationDeclaration(parent, list));
      if (!myHolder.hasErrorResults()) myHolder.add(HighlightClassUtil.checkExtendsAllowed(list));
      if (!myHolder.hasErrorResults()) myHolder.add(HighlightClassUtil.checkImplementsAllowed(list));
      if (!myHolder.hasErrorResults()) myHolder.add(HighlightClassUtil.checkClassExtendsOnlyOneClass(list));
      if (!myHolder.hasErrorResults()) myHolder.add(GenericsHighlightUtil.checkGenericCannotExtendException(list));
    }
  }

  @Override
  public void visitReferenceParameterList(PsiReferenceParameterList list) {
    if (list.getTextLength() == 0) return;

    myHolder.add(checkFeature(list, Feature.GENERICS));
    if (!myHolder.hasErrorResults()) myHolder.add(GenericsHighlightUtil.checkParametersAllowed(list));
    if (!myHolder.hasErrorResults()) myHolder.add(GenericsHighlightUtil.checkParametersOnRaw(list));
    if (!myHolder.hasErrorResults()) {
      for (PsiTypeElement typeElement : list.getTypeParameterElements()) {
        if (typeElement.getType() instanceof PsiDiamondType) {
          myHolder.add(checkFeature(list, Feature.DIAMOND_TYPES));
        }
      }
    }
  }

  @Override
  public void visitReturnStatement(PsiReturnStatement statement) {
    try {
      myHolder.add(HighlightUtil.checkReturnStatementType(statement));
    }
    catch (IndexNotReadyException ignore) {
    }
  }

  @Override
  public void visitStatement(PsiStatement statement) {
    super.visitStatement(statement);
    if (!myHolder.hasErrorResults()) myHolder.add(HighlightUtil.checkNotAStatement(statement));
    if (!myHolder.hasErrorResults()) myHolder.add(HighlightUtil.checkStatementPrependedWithCaseInsideSwitch(statement));
  }

  @Override
  public void visitSuperExpression(PsiSuperExpression expr) {
    myHolder.add(HighlightUtil.checkThisOrSuperExpressionInIllegalContext(expr, expr.getQualifier(), myLanguageLevel));
    if (!myHolder.hasErrorResults()) visitExpression(expr);
  }

  @Override
  public void visitSwitchLabelStatement(PsiSwitchLabelStatement statement) {
    super.visitSwitchLabelStatement(statement);
    if (!myHolder.hasErrorResults()) myHolder.add(HighlightUtil.checkCaseStatement(statement));
  }

  @Override
  public void visitSwitchStatement(PsiSwitchStatement statement) {
    super.visitSwitchStatement(statement);
    if (!myHolder.hasErrorResults()) myHolder.add(HighlightUtil.checkSwitchSelectorType(statement, myLanguageLevel));
  }

  @Override
  public void visitThisExpression(PsiThisExpression expr) {
    myHolder.add(HighlightUtil.checkThisOrSuperExpressionInIllegalContext(expr, expr.getQualifier(), myLanguageLevel));
    if (!myHolder.hasErrorResults()) {
      myHolder.add(HighlightUtil.checkMemberReferencedBeforeConstructorCalled(expr, null, myFile));
    }
    if (!myHolder.hasErrorResults()) {
      visitExpression(expr);
    }
  }

  @Override
  public void visitThrowStatement(PsiThrowStatement statement) {
    myHolder.add(HighlightUtil.checkUnhandledExceptions(statement, null));
    if (!myHolder.hasErrorResults()) visitStatement(statement);
  }

  @Override
  public void visitTryStatement(PsiTryStatement statement) {
    super.visitTryStatement(statement);
    if (!myHolder.hasErrorResults()) {
      final Set<PsiClassType> thrownTypes = HighlightUtil.collectUnhandledExceptions(statement);
      for (PsiParameter parameter : statement.getCatchBlockParameters()) {
        boolean added = myHolder.addAll(HighlightUtil.checkExceptionAlreadyCaught(parameter));
        if (!added) {
          added = myHolder.addAll(HighlightUtil.checkExceptionThrownInTry(parameter, thrownTypes));
        }
        if (!added) {
          myHolder.addAll(HighlightUtil.checkWithImprovedCatchAnalysis(parameter, thrownTypes, myFile));
        }
      }
    }
  }

  @Override
  public void visitResourceVariable(final PsiResourceVariable resourceVariable) {
    visitVariable(resourceVariable);
    if (!myHolder.hasErrorResults()) myHolder.add(HighlightUtil.checkTryResourceIsAutoCloseable(resourceVariable));
    if (!myHolder.hasErrorResults()) myHolder.add(HighlightUtil.checkUnhandledCloserExceptions(resourceVariable));
  }

  @Override
  public void visitResourceList(PsiResourceList resourceList) {
    super.visitResourceList(resourceList);
    if (!myHolder.hasErrorResults()) myHolder.add(checkFeature(resourceList, Feature.TRY_WITH_RESOURCES));
  }

  @Override
  public void visitTypeElement(final PsiTypeElement type) {
    if (!myHolder.hasErrorResults()) myHolder.add(HighlightUtil.checkIllegalType(type));
    if (!myHolder.hasErrorResults()) myHolder.add(GenericsHighlightUtil.checkReferenceTypeUsedAsTypeArgument(type));
    if (!myHolder.hasErrorResults()) myHolder.add(GenericsHighlightUtil.checkWildcardUsage(type));
  }

  @Override
  public void visitTypeCastExpression(PsiTypeCastExpression typeCast) {
    super.visitTypeCastExpression(typeCast);
    try {
      if (!myHolder.hasErrorResults()) myHolder.add(HighlightUtil.checkIntersectionInTypeCast(typeCast, myLanguageLevel));
      if (!myHolder.hasErrorResults()) myHolder.add(HighlightUtil.checkInconvertibleTypeCast(typeCast));
    }
    catch (IndexNotReadyException ignore) {
    }
  }

  @Override
  public void visitTypeParameterList(PsiTypeParameterList list) {
    PsiTypeParameter[] typeParameters = list.getTypeParameters();
    if (typeParameters.length > 0) {
      myHolder.add(checkFeature(list, Feature.GENERICS));
      if (!myHolder.hasErrorResults()) myHolder.add(GenericsHighlightUtil.checkTypeParametersList(list, typeParameters, myLanguageLevel));
    }
  }

  @Override
  public void visitVariable(PsiVariable variable) {
    super.visitVariable(variable);
    try {
      if (!myHolder.hasErrorResults()) myHolder.add(HighlightUtil.checkVariableInitializerType(variable));
    }
    catch (IndexNotReadyException ignored) {
    }
  }

  private boolean isReassigned(@NotNull PsiVariable variable) {
    try {
      boolean reassigned;
      if (variable instanceof PsiParameter) {
        reassigned = myReassignedParameters.get((PsiParameter)variable) == 2;
      }
      else  {
        reassigned = HighlightControlFlowUtil.isReassigned(variable, myFinalVarProblems);
      }

      return reassigned;
    }
    catch (IndexNotReadyException e) {
      return false;
    }
  }

  @Override
  public void visitConditionalExpression(PsiConditionalExpression expression) {
    super.visitConditionalExpression(expression);
    if (myLanguageLevel.isAtLeast(LanguageLevel.JDK_1_8) && PsiPolyExpressionUtil.isPolyExpression(expression)) {
      final PsiExpression thenExpression = expression.getThenExpression();
      final PsiExpression elseExpression = expression.getElseExpression();
      if (thenExpression != null && elseExpression != null) {
        final PsiType conditionalType = expression.getType();
        if (conditionalType != null) {
          final PsiExpression[] sides = new PsiExpression[] {thenExpression, elseExpression};
          for (PsiExpression side : sides) {
            final PsiType sideType = side.getType();
            if (sideType != null && !TypeConversionUtil.isAssignable(conditionalType, sideType)) {
              myHolder.add(HighlightUtil.checkAssignability(conditionalType, sideType, side, side));
            }
          }
        }
      }
    }
  }

  @Nullable
  private HighlightInfo checkFeature(@NotNull PsiElement element, @NotNull Feature feature) {
    return HighlightUtil.checkFeature(element, feature, myLanguageLevel, myFile);
  }
}


File: java/java-psi-api/src/com/intellij/openapi/projectRoots/JavaSdkVersion.java
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
package com.intellij.openapi.projectRoots;

import com.intellij.pom.java.LanguageLevel;
import org.jetbrains.annotations.NotNull;

import java.util.Arrays;

/**
 * Represents version of Java SDK. Use {@link JavaSdk#getVersion(Sdk)} method to obtain version of an {@link Sdk}
 *
 * @author nik
 */
public enum JavaSdkVersion {
  JDK_1_0(LanguageLevel.JDK_1_3, "1.0"), JDK_1_1(LanguageLevel.JDK_1_3, "1.1"), JDK_1_2(LanguageLevel.JDK_1_3, "1.2"), JDK_1_3(LanguageLevel.JDK_1_3, "1.3"),
  JDK_1_4(LanguageLevel.JDK_1_4, "1.4"),
  JDK_1_5(LanguageLevel.JDK_1_5, "1.5"),
  JDK_1_6(LanguageLevel.JDK_1_6, "1.6"),
  JDK_1_7(LanguageLevel.JDK_1_7, "1.7"),
  JDK_1_8(LanguageLevel.JDK_1_8, "1.8"),
  JDK_1_9(LanguageLevel.JDK_1_9, "1.9");
  
  private final LanguageLevel myMaxLanguageLevel;
  private final String myDescription;

  JavaSdkVersion(@NotNull LanguageLevel maxLanguageLevel, @NotNull String description) {
    myMaxLanguageLevel = maxLanguageLevel;
    myDescription = description;
  }

  @NotNull
  public LanguageLevel getMaxLanguageLevel() {
    return myMaxLanguageLevel;
  }

  @NotNull
  public String getDescription() {
    return myDescription;
  }

  public boolean isAtLeast(@NotNull JavaSdkVersion version) {
    return compareTo(version) >= 0;
  }

  @Override
  public String toString() {
    return super.toString() + ", description: " + myDescription;
  }

  @NotNull
  public static JavaSdkVersion byDescription(@NotNull String description) throws IllegalArgumentException {
    for (JavaSdkVersion version : values()) {
      if (version.getDescription().equals(description)) {
        return version;
      }
    }
    throw new IllegalArgumentException(
      String.format("Can't map Java SDK by description (%s). Available values: %s", description, Arrays.toString(values()))
    );
  }

  @NotNull
  public static JavaSdkVersion fromLanguageLevel(@NotNull LanguageLevel languageLevel) throws IllegalArgumentException {
    JavaSdkVersion[] values = values();
    for (int i = values.length - 1; i >= 0; i--) {
      JavaSdkVersion version = values[i];
      if (version.getMaxLanguageLevel().isAtLeast(languageLevel)) {
        return version;
      }
    }
    throw new IllegalArgumentException(
      "Can't map Java SDK by language level "+languageLevel+". Available values: "+ Arrays.toString(values())
    );
  }
}


File: java/java-psi-api/src/com/intellij/pom/java/LanguageLevel.java
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
package com.intellij.pom.java;

import com.intellij.core.JavaCoreBundle;
import com.intellij.openapi.roots.LanguageLevelModuleExtension;
import com.intellij.openapi.roots.LanguageLevelProjectExtension;
import com.intellij.openapi.util.Key;
import org.jetbrains.annotations.Nls;
import org.jetbrains.annotations.NonNls;
import org.jetbrains.annotations.NotNull;
import org.jetbrains.annotations.Nullable;

/**
 * @author dsl
 * @see LanguageLevelProjectExtension
 * @see LanguageLevelModuleExtension
 */
public enum LanguageLevel {
  JDK_1_3("Java 1.3", JavaCoreBundle.message("jdk.1.3.language.level.description")),
  JDK_1_4("Java 1.4", JavaCoreBundle.message("jdk.1.4.language.level.description")),
  JDK_1_5("Java 5.0", JavaCoreBundle.message("jdk.1.5.language.level.description")),
  JDK_1_6("Java 6", JavaCoreBundle.message("jdk.1.6.language.level.description")),
  JDK_1_7("Java 7", JavaCoreBundle.message("jdk.1.7.language.level.description")),
  JDK_1_8("Java 8", JavaCoreBundle.message("jdk.1.8.language.level.description")),
  JDK_1_9("Java 9", JavaCoreBundle.message("jdk.1.9.language.level.description"));

  public static final LanguageLevel HIGHEST = JDK_1_8; // TODO! when language level 9 is really supported, update this field
  public static final Key<LanguageLevel> KEY = Key.create("LANGUAGE_LEVEL");

  private final String myName;
  private final String myPresentableText;

  LanguageLevel(@NotNull @NonNls String name, @NotNull @Nls String presentableText) {
    myName = name;
    myPresentableText = presentableText;
  }

  @NotNull
  @NonNls
  public String getName() {
    return myName;
  }

  @NotNull
  @Nls
  public String getPresentableText() {
    return myPresentableText;
  }

  public boolean isAtLeast(@NotNull LanguageLevel level) {
    return compareTo(level) >= 0;
  }

  @Nullable
  public static LanguageLevel parse(@Nullable String value) {
    if ("1.3".equals(value)) return JDK_1_3;
    if ("1.4".equals(value)) return JDK_1_4;
    if ("1.5".equals(value)) return JDK_1_5;
    if ("1.6".equals(value)) return JDK_1_6;
    if ("1.7".equals(value)) return JDK_1_7;
    if ("1.8".equals(value)) return JDK_1_8;
    if ("1.9".equals(value)) return JDK_1_9;

    return null;
  }
}


File: java/java-psi-impl/src/com/intellij/lang/java/parser/JavaParserUtil.java
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
package com.intellij.lang.java.parser;

import com.intellij.codeInsight.daemon.JavaErrorMessages;
import com.intellij.lang.*;
import com.intellij.lang.impl.PsiBuilderAdapter;
import com.intellij.lang.java.JavaLanguage;
import com.intellij.lang.java.JavaParserDefinition;
import com.intellij.lexer.Lexer;
import com.intellij.openapi.application.Application;
import com.intellij.openapi.application.ApplicationManager;
import com.intellij.openapi.project.Project;
import com.intellij.openapi.util.Condition;
import com.intellij.openapi.util.Key;
import com.intellij.openapi.util.Pair;
import com.intellij.openapi.util.text.StringUtil;
import com.intellij.pom.java.LanguageLevel;
import com.intellij.psi.JavaTokenType;
import com.intellij.psi.PsiElement;
import com.intellij.psi.impl.source.tree.ElementType;
import com.intellij.psi.impl.source.tree.JavaDocElementType;
import com.intellij.psi.impl.source.tree.JavaElementType;
import com.intellij.psi.impl.source.tree.TreeUtil;
import com.intellij.psi.tree.IElementType;
import com.intellij.psi.tree.TokenSet;
import com.intellij.psi.util.PsiUtil;
import com.intellij.util.SystemProperties;
import com.intellij.util.indexing.IndexingDataKeys;
import org.jetbrains.annotations.NotNull;
import org.jetbrains.annotations.Nullable;
import org.jetbrains.annotations.PropertyKey;

import java.util.List;

public class JavaParserUtil {
  private static final Key<LanguageLevel> LANG_LEVEL_KEY = Key.create("JavaParserUtil.LanguageLevel");
  private static final Key<Boolean> DEEP_PARSE_BLOCKS_IN_STATEMENTS = Key.create("JavaParserUtil.ParserExtender");

  public interface ParserWrapper {
    void parse(PsiBuilder builder);
  }

  private static class PrecedingWhitespacesAndCommentsBinder implements WhitespacesAndCommentsBinder {
    private final boolean myAfterEmptyImport;

    public PrecedingWhitespacesAndCommentsBinder(final boolean afterImport) {
      this.myAfterEmptyImport = afterImport;
    }

    @Override
    public int getEdgePosition(final List<IElementType> tokens, final boolean atStreamEdge, final TokenTextGetter
      getter) {
      if (tokens.size() == 0) return 0;

      // 1. bind doc comment
      for (int idx = tokens.size() - 1; idx >= 0; idx--) {
        if (tokens.get(idx) == JavaDocElementType.DOC_COMMENT) return idx;
      }

      // 2. bind plain comments
      int result = tokens.size();
      for (int idx = tokens.size() - 1; idx >= 0; idx--) {
        final IElementType tokenType = tokens.get(idx);
        if (ElementType.JAVA_WHITESPACE_BIT_SET.contains(tokenType)) {
          if (StringUtil.getLineBreakCount(getter.get(idx)) > 1) break;
        }
        else if (ElementType.JAVA_PLAIN_COMMENT_BIT_SET.contains(tokenType)) {
          if (atStreamEdge ||
              (idx == 0 && myAfterEmptyImport) ||
              (idx > 0 && ElementType.JAVA_WHITESPACE_BIT_SET.contains(tokens.get(idx - 1)) && StringUtil.containsLineBreak(getter.get(idx - 1)))) {
            result = idx;
          }
        }
        else break;
      }

      return result;
    }
  }

  private static class TrailingWhitespacesAndCommentsBinder implements WhitespacesAndCommentsBinder {
    @Override
    public int getEdgePosition(final List<IElementType> tokens, final boolean atStreamEdge, final TokenTextGetter getter) {
      if (tokens.size() == 0) return 0;

      int result = 0;
      for (int idx = 0; idx < tokens.size(); idx++) {
        final IElementType tokenType = tokens.get(idx);
        if (ElementType.JAVA_WHITESPACE_BIT_SET.contains(tokenType)) {
          if (StringUtil.containsLineBreak(getter.get(idx))) break;
        }
        else if (ElementType.JAVA_PLAIN_COMMENT_BIT_SET.contains(tokenType)) {
          result = idx + 1;
        }
        else break;
      }

      return result;
    }
  }

  private static final TokenSet PRECEDING_COMMENT_SET = ElementType.FULL_MEMBER_BIT_SET;
  private static final TokenSet TRAILING_COMMENT_SET = TokenSet.orSet(
    TokenSet.create(JavaElementType.PACKAGE_STATEMENT),
    ElementType.IMPORT_STATEMENT_BASE_BIT_SET, ElementType.FULL_MEMBER_BIT_SET, ElementType.JAVA_STATEMENT_BIT_SET);

  public static final WhitespacesAndCommentsBinder PRECEDING_COMMENT_BINDER = new PrecedingWhitespacesAndCommentsBinder(false);
  public static final WhitespacesAndCommentsBinder SPECIAL_PRECEDING_COMMENT_BINDER = new PrecedingWhitespacesAndCommentsBinder(true);
  public static final WhitespacesAndCommentsBinder TRAILING_COMMENT_BINDER = new TrailingWhitespacesAndCommentsBinder();

  public static final boolean EXPERIMENTAL_FEATURES;
  static {
    Application app = ApplicationManager.getApplication();
    EXPERIMENTAL_FEATURES = SystemProperties.getBooleanProperty("idea.experimental.java.features", app != null && app.isUnitTestMode());
  }

  private JavaParserUtil() { }

  public static void setLanguageLevel(final PsiBuilder builder, final LanguageLevel level) {
    builder.putUserDataUnprotected(LANG_LEVEL_KEY, level);
  }

  @NotNull
  public static LanguageLevel getLanguageLevel(final PsiBuilder builder) {
    final LanguageLevel level = builder.getUserDataUnprotected(LANG_LEVEL_KEY);
    assert level != null : builder;
    return level;
  }

  public static void setParseStatementCodeBlocksDeep(final PsiBuilder builder, final boolean deep) {
    builder.putUserDataUnprotected(DEEP_PARSE_BLOCKS_IN_STATEMENTS, deep);
  }

  public static boolean isParseStatementCodeBlocksDeep(final PsiBuilder builder) {
    return Boolean.TRUE.equals(builder.getUserDataUnprotected(DEEP_PARSE_BLOCKS_IN_STATEMENTS));
  }

  @NotNull
  public static PsiBuilder createBuilder(final ASTNode chameleon) {
    final PsiElement psi = chameleon.getPsi();
    assert psi != null : chameleon;
    final Project project = psi.getProject();

    CharSequence text;
    if (TreeUtil.isCollapsedChameleon(chameleon)) {
      text = chameleon.getChars();
    }
    else {
      text = psi.getUserData(IndexingDataKeys.FILE_TEXT_CONTENT_KEY);
      if (text == null) text = chameleon.getChars();
    }

    final PsiBuilderFactory factory = PsiBuilderFactory.getInstance();
    final LanguageLevel level = PsiUtil.getLanguageLevel(psi);
    final Lexer lexer = JavaParserDefinition.createLexer(level);
    Language language = psi.getLanguage();
    if (!language.isKindOf(JavaLanguage.INSTANCE)) language = JavaLanguage.INSTANCE;
    final PsiBuilder builder = factory.createBuilder(project, chameleon, lexer, language, text);
    setLanguageLevel(builder, level);

    return builder;
  }

  @NotNull
  public static PsiBuilder createBuilder(final LighterLazyParseableNode chameleon) {
    final PsiElement psi = chameleon.getContainingFile();
    assert psi != null : chameleon;
    final Project project = psi.getProject();

    final PsiBuilderFactory factory = PsiBuilderFactory.getInstance();
    final LanguageLevel level = PsiUtil.getLanguageLevel(psi);
    final Lexer lexer = JavaParserDefinition.createLexer(level);
    final PsiBuilder builder = factory.createBuilder(project, chameleon, lexer, chameleon.getTokenType().getLanguage(), chameleon.getText());
    setLanguageLevel(builder, level);

    return builder;
  }

  @Nullable
  public static ASTNode parseFragment(final ASTNode chameleon, final ParserWrapper wrapper) {
    return parseFragment(chameleon, wrapper, true, LanguageLevel.HIGHEST);
  }

  @Nullable
  public static ASTNode parseFragment(final ASTNode chameleon, final ParserWrapper wrapper, final boolean eatAll, final LanguageLevel level) {
    final PsiElement psi = (chameleon.getTreeParent() != null ? chameleon.getTreeParent().getPsi() : chameleon.getPsi());
    assert psi != null : chameleon;
    final Project project = psi.getProject();

    final PsiBuilderFactory factory = PsiBuilderFactory.getInstance();
    final Lexer lexer = chameleon.getElementType() == JavaDocElementType.DOC_COMMENT
                        ? JavaParserDefinition.createDocLexer(level) : JavaParserDefinition.createLexer(level);
    final PsiBuilder builder = factory.createBuilder(project, chameleon, lexer, chameleon.getElementType().getLanguage(), chameleon.getChars());
    setLanguageLevel(builder, level);

    final PsiBuilder.Marker root = builder.mark();
    wrapper.parse(builder);
    if (!builder.eof()) {
      if (!eatAll) throw new AssertionError("Unexpected tokens");
      final PsiBuilder.Marker extras = builder.mark();
      while (!builder.eof()) builder.advanceLexer();
      extras.error(JavaErrorMessages.message("unexpected.tokens"));
    }
    root.done(chameleon.getElementType());

    return builder.getTreeBuilt().getFirstChildNode();
  }

  public static void done(final PsiBuilder.Marker marker, final IElementType type) {
    marker.done(type);
    final WhitespacesAndCommentsBinder left = PRECEDING_COMMENT_SET.contains(type) ? PRECEDING_COMMENT_BINDER : null;
    final WhitespacesAndCommentsBinder right = TRAILING_COMMENT_SET.contains(type) ? TRAILING_COMMENT_BINDER : null;
    marker.setCustomEdgeTokenBinders(left, right);
  }

  @Nullable
  public static IElementType exprType(@Nullable final PsiBuilder.Marker marker) {
    return marker != null ? ((LighterASTNode)marker).getTokenType() : null;
  }

  // used instead of PsiBuilder.error() as it keeps all subsequent error messages
  public static void error(final PsiBuilder builder, final String message) {
    builder.mark().error(message);
  }

  public static void error(final PsiBuilder builder, final String message, @Nullable final PsiBuilder.Marker before) {
    if (before == null) {
      error(builder, message);
    }
    else {
      before.precede().errorBefore(message, before);
    }
  }

  public static boolean expectOrError(PsiBuilder builder, TokenSet expected, @PropertyKey(resourceBundle = JavaErrorMessages.BUNDLE) String key) {
    if (!PsiBuilderUtil.expect(builder, expected)) {
      error(builder, JavaErrorMessages.message(key));
      return false;
    }
    return true;
  }

  public static boolean expectOrError(PsiBuilder builder, IElementType expected, @PropertyKey(resourceBundle = JavaErrorMessages.BUNDLE) String key) {
    if (!PsiBuilderUtil.expect(builder, expected)) {
      error(builder, JavaErrorMessages.message(key));
      return false;
    }
    return true;
  }

  public static void emptyElement(final PsiBuilder builder, final IElementType type) {
    builder.mark().done(type);
  }

  public static void emptyElement(final PsiBuilder.Marker before, final IElementType type) {
    before.precede().doneBefore(type, before);
  }

  public static void semicolon(final PsiBuilder builder) {
    expectOrError(builder, JavaTokenType.SEMICOLON, "expected.semicolon");
  }

  public static PsiBuilder braceMatchingBuilder(final PsiBuilder builder) {
    final PsiBuilder.Marker pos = builder.mark();

    int braceCount = 1;
    while (!builder.eof()) {
      final IElementType tokenType = builder.getTokenType();
      if (tokenType == JavaTokenType.LBRACE) braceCount++;
      else if (tokenType == JavaTokenType.RBRACE) braceCount--;
      if (braceCount == 0) break;
      builder.advanceLexer();
    }
    final int stopAt = builder.getCurrentOffset();

    pos.rollbackTo();

    return stoppingBuilder(builder, stopAt);
  }

  public static PsiBuilder stoppingBuilder(final PsiBuilder builder, final int stopAt) {
    return new PsiBuilderAdapter(builder) {
      @Override
      public IElementType getTokenType() {
        return getCurrentOffset() < stopAt ? super.getTokenType() : null;
      }

      @Override
      public boolean eof() {
        return getCurrentOffset() >= stopAt || super.eof();
      }
    };
  }

  public static PsiBuilder stoppingBuilder(final PsiBuilder builder, final Condition<Pair<IElementType, String>> condition) {
    return new PsiBuilderAdapter(builder) {
      @Override
      public IElementType getTokenType() {
        final Pair<IElementType, String> input = Pair.create(builder.getTokenType(), builder.getTokenText());
        return condition.value(input) ? null : super.getTokenType();
      }

      @Override
      public boolean eof() {
        final Pair<IElementType, String> input = Pair.create(builder.getTokenType(), builder.getTokenText());
        return condition.value(input) || super.eof();
      }
    };
  }
}


File: java/java-psi-impl/src/com/intellij/lang/java/parser/ReferenceParser.java
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
package com.intellij.lang.java.parser;

import com.intellij.codeInsight.daemon.JavaErrorMessages;
import com.intellij.lang.PsiBuilder;
import com.intellij.pom.java.LanguageLevel;
import com.intellij.psi.JavaTokenType;
import com.intellij.psi.impl.source.tree.ElementType;
import com.intellij.psi.impl.source.tree.JavaElementType;
import com.intellij.psi.tree.IElementType;
import com.intellij.psi.tree.TokenSet;
import org.jetbrains.annotations.NotNull;
import org.jetbrains.annotations.Nullable;

import static com.intellij.lang.PsiBuilderUtil.expect;
import static com.intellij.lang.java.parser.JavaParserUtil.*;
import static com.intellij.util.BitUtil.*;

public class ReferenceParser {
  public static final int EAT_LAST_DOT = 0x01;
  public static final int ELLIPSIS = 0x02;
  public static final int WILDCARD = 0x04;
  public static final int DIAMONDS = 0x08;
  public static final int DISJUNCTIONS = 0x10;
  public static final int CONJUNCTIONS = 0x20;
  public static final int INCOMPLETE_ANNO = 0x40;

  public static class TypeInfo {
    public boolean isPrimitive = false;
    public boolean isParameterized = false;
    public boolean isArray = false;
    public boolean isVarArg = false;
    public boolean hasErrors = false;
    public PsiBuilder.Marker marker = null;
  }

  private static final TokenSet WILDCARD_KEYWORD_SET = TokenSet.create(JavaTokenType.EXTENDS_KEYWORD, JavaTokenType.SUPER_KEYWORD);

  private final JavaParser myParser;

  public ReferenceParser(@NotNull final JavaParser javaParser) {
    myParser = javaParser;
  }

  @Nullable
  public PsiBuilder.Marker parseType(final PsiBuilder builder, final int flags) {
    final TypeInfo typeInfo = parseTypeInfo(builder, flags);
    return typeInfo != null ? typeInfo.marker : null;
  }

  @Nullable
  public TypeInfo parseTypeInfo(final PsiBuilder builder, final int flags) {
    final TypeInfo typeInfo = parseTypeInfo(builder, flags, false);

    if (typeInfo != null) {
      assert notSet(flags, DISJUNCTIONS|CONJUNCTIONS) : "don't set both flags simultaneously";
      final IElementType operator = isSet(flags, DISJUNCTIONS) ? JavaTokenType.OR : isSet(flags, CONJUNCTIONS) ? JavaTokenType.AND : null;

      if (operator != null && builder.getTokenType() == operator) {
        typeInfo.marker = typeInfo.marker.precede();

        while (builder.getTokenType() == operator) {
          builder.advanceLexer();
          IElementType tokenType = builder.getTokenType();
          if (tokenType != JavaTokenType.IDENTIFIER && tokenType != JavaTokenType.AT) {
            error(builder, JavaErrorMessages.message("expected.identifier"));
          }
          parseTypeInfo(builder, flags, false);
        }

        typeInfo.marker.done(JavaElementType.TYPE);
      }
    }

    return typeInfo;
  }

  @Nullable
  private TypeInfo parseTypeInfo(PsiBuilder builder, int flags, boolean badWildcard) {
    if (builder.getTokenType() == null) return null;

    final TypeInfo typeInfo = new TypeInfo();

    PsiBuilder.Marker type = builder.mark();
    PsiBuilder.Marker anno = myParser.getDeclarationParser().parseAnnotations(builder);

    final IElementType tokenType = builder.getTokenType();
    if (expect(builder, ElementType.PRIMITIVE_TYPE_BIT_SET)) {
      typeInfo.isPrimitive = true;
    }
    else if (tokenType == JavaTokenType.IDENTIFIER) {
      parseJavaCodeReference(builder, isSet(flags, EAT_LAST_DOT), true, false, false, false, isSet(flags, DIAMONDS), typeInfo);
    }
    else if ((isSet(flags, WILDCARD) || badWildcard) && tokenType == JavaTokenType.QUEST) {
      builder.advanceLexer();
      completeWildcardType(builder, isSet(flags, WILDCARD), type);
      typeInfo.marker = type;
      return typeInfo;
    }
    else if (isSet(flags, DIAMONDS) && tokenType == JavaTokenType.GT) {
      emptyElement(builder, JavaElementType.DIAMOND_TYPE);
      type.done(JavaElementType.TYPE);
      typeInfo.marker = type;
      return typeInfo;
    }
    else {
      type.drop();
      if (anno != null && isSet(flags, INCOMPLETE_ANNO)) {
        error(builder, JavaErrorMessages.message("expected.type"));
        typeInfo.hasErrors = true;
        return typeInfo;
      }
      return null;
    }

    while (true) {
      type.done(JavaElementType.TYPE);
      myParser.getDeclarationParser().parseAnnotations(builder);

      final PsiBuilder.Marker bracket = builder.mark();
      if (!expect(builder, JavaTokenType.LBRACKET)) {
        bracket.drop();
        break;
      }
      if (!expect(builder, JavaTokenType.RBRACKET)) {
        bracket.rollbackTo();
        break;
      }
      bracket.drop();
      typeInfo.isArray = true;

      type = type.precede();
    }

    if (isSet(flags, ELLIPSIS) && builder.getTokenType() == JavaTokenType.ELLIPSIS) {
      type = type.precede();
      builder.advanceLexer();
      type.done(JavaElementType.TYPE);
      typeInfo.isVarArg = true;
    }

    typeInfo.marker = type;
    return typeInfo;
  }

  private void completeWildcardType(PsiBuilder builder, boolean wildcard, PsiBuilder.Marker type) {
    if (expect(builder, WILDCARD_KEYWORD_SET)) {
      if (parseTypeInfo(builder, EAT_LAST_DOT) == null) {
        error(builder, JavaErrorMessages.message("expected.type"));
      }
    }

    if (wildcard) {
      type.done(JavaElementType.TYPE);
    }
    else {
      type.error(JavaErrorMessages.message("wildcard.not.expected"));
    }
  }

  @Nullable
  public PsiBuilder.Marker parseJavaCodeReference(PsiBuilder builder, boolean eatLastDot, boolean parameterList, boolean isNew, boolean diamonds) {
    return parseJavaCodeReference(builder, eatLastDot, parameterList, false, false, isNew, diamonds, new TypeInfo());
  }

  public boolean parseImportCodeReference(final PsiBuilder builder, final boolean isStatic) {
    final TypeInfo typeInfo = new TypeInfo();
    parseJavaCodeReference(builder, true, false, true, isStatic, false, false, typeInfo);
    return !typeInfo.hasErrors;
  }

  @Nullable
  private PsiBuilder.Marker parseJavaCodeReference(PsiBuilder builder, boolean eatLastDot, boolean parameterList, boolean isImport,
                                                   boolean isStaticImport, boolean isNew, boolean diamonds, TypeInfo typeInfo) {
    PsiBuilder.Marker refElement = builder.mark();

    myParser.getDeclarationParser().parseAnnotations(builder);

    if (!expect(builder, JavaTokenType.IDENTIFIER)) {
      refElement.rollbackTo();
      if (isImport) {
        error(builder, JavaErrorMessages.message("expected.identifier"));
      }
      typeInfo.hasErrors = true;
      return null;
    }

    if (parameterList) {
      typeInfo.isParameterized = parseReferenceParameterList(builder, true, diamonds);
    }
    else {
      emptyElement(builder, JavaElementType.REFERENCE_PARAMETER_LIST);
    }

    boolean hasIdentifier;
    while (builder.getTokenType() == JavaTokenType.DOT) {
      refElement.done(JavaElementType.JAVA_CODE_REFERENCE);

      if (isNew && !diamonds && typeInfo.isParameterized) {
        return refElement;
      }

      final PsiBuilder.Marker dotPos = builder.mark();
      builder.advanceLexer();

      myParser.getDeclarationParser().parseAnnotations(builder);

      if (expect(builder, JavaTokenType.IDENTIFIER)) {
        hasIdentifier = true;
      }
      else if (isImport && expect(builder, JavaTokenType.ASTERISK)) {
        dotPos.drop();
        return refElement;
      }
      else {
        if (!eatLastDot) {
          dotPos.rollbackTo();
          return refElement;
        }
        hasIdentifier = false;
      }
      dotPos.drop();

      final PsiBuilder.Marker prevElement = refElement;
      refElement = refElement.precede();

      if (!hasIdentifier) {
        typeInfo.hasErrors = true;
        if (isImport) {
          error(builder, JavaErrorMessages.message("import.statement.identifier.or.asterisk.expected."));
          refElement.drop();
          return prevElement;
        }
        else {
          error(builder, JavaErrorMessages.message("expected.identifier"));
          emptyElement(builder, JavaElementType.REFERENCE_PARAMETER_LIST);
          break;
        }
      }

      if (parameterList) {
        typeInfo.isParameterized = parseReferenceParameterList(builder, true, diamonds);
      }
      else {
        emptyElement(builder, JavaElementType.REFERENCE_PARAMETER_LIST);
      }
    }

    refElement.done(isStaticImport ? JavaElementType.IMPORT_STATIC_REFERENCE : JavaElementType.JAVA_CODE_REFERENCE);
    return refElement;
  }

  public boolean parseReferenceParameterList(final PsiBuilder builder, final boolean wildcard, final boolean diamonds) {
    final PsiBuilder.Marker list = builder.mark();
    if (!expect(builder, JavaTokenType.LT)) {
      list.done(JavaElementType.REFERENCE_PARAMETER_LIST);
      return false;
    }

    int flags = set(set(EAT_LAST_DOT, WILDCARD, wildcard), DIAMONDS, diamonds);
    boolean isOk = true;
    while (true) {
      if (parseTypeInfo(builder, flags, true) == null) {
        error(builder, JavaErrorMessages.message("expected.identifier"));
      }
      else {
        IElementType tokenType = builder.getTokenType();
        if (WILDCARD_KEYWORD_SET.contains(tokenType)) {
          parseReferenceList(builder, tokenType, null, JavaTokenType.AND);
        }
      }

      if (expect(builder, JavaTokenType.GT)) {
        break;
      }
      else if (!expectOrError(builder, JavaTokenType.COMMA, "expected.gt.or.comma")) {
        isOk = false;
        break;
      }
      flags = set(flags, DIAMONDS, false);
    }

    list.done(JavaElementType.REFERENCE_PARAMETER_LIST);
    return isOk;
  }

  @NotNull
  public PsiBuilder.Marker parseTypeParameters(final PsiBuilder builder) {
    final PsiBuilder.Marker list = builder.mark();
    if (!expect(builder, JavaTokenType.LT)) {
      list.done(JavaElementType.TYPE_PARAMETER_LIST);
      return list;
    }

    while (true) {
      final PsiBuilder.Marker param = parseTypeParameter(builder);
      if (param == null) {
        error(builder, JavaErrorMessages.message("expected.type.parameter"));
      }
      if (!expect(builder, JavaTokenType.COMMA)) {
        break;
      }
    }

    if (!expect(builder, JavaTokenType.GT)) {
      // hack for completion
      if (builder.getTokenType() == JavaTokenType.IDENTIFIER) {
        if (builder.lookAhead(1) == JavaTokenType.GT) {
          final PsiBuilder.Marker errorElement = builder.mark();
          builder.advanceLexer();
          errorElement.error(JavaErrorMessages.message("unexpected.identifier"));
          builder.advanceLexer();
        }
        else {
          error(builder, JavaErrorMessages.message("expected.gt"));
        }
      }
      else {
        error(builder, JavaErrorMessages.message("expected.gt"));
      }
    }

    list.done(JavaElementType.TYPE_PARAMETER_LIST);
    return list;
  }

  @Nullable
  public PsiBuilder.Marker parseTypeParameter(final PsiBuilder builder) {
    final PsiBuilder.Marker param = builder.mark();

    myParser.getDeclarationParser().parseAnnotations(builder);

    if (EXPERIMENTAL_FEATURES && "any".equals(builder.getTokenText()) && getLanguageLevel(builder).isAtLeast(LanguageLevel.JDK_1_9)) {
      PsiBuilder.Marker mark = builder.mark();
      builder.advanceLexer();
      mark.done(JavaElementType.DUMMY_ELEMENT);
    }

    final boolean wild = expect(builder, JavaTokenType.QUEST);
    if (!wild && !expect(builder, JavaTokenType.IDENTIFIER)) {
      param.rollbackTo();
      return null;
    }

    parseReferenceList(builder, JavaTokenType.EXTENDS_KEYWORD, JavaElementType.EXTENDS_BOUND_LIST, JavaTokenType.AND);

    if (!wild) {
      param.done(JavaElementType.TYPE_PARAMETER);
    }
    else {
      param.error(JavaErrorMessages.message("wildcard.not.expected"));
    }
    return param;
  }

  @NotNull
  public PsiBuilder.Marker parseReferenceList(final PsiBuilder builder, final IElementType start,
                                              @Nullable final IElementType type, final IElementType delimiter) {
    final PsiBuilder.Marker element = builder.mark();

    if (expect(builder, start)) {
      while (true) {
        final PsiBuilder.Marker classReference = parseJavaCodeReference(builder, true, true, false, false);
        if (classReference == null) {
          error(builder, JavaErrorMessages.message("expected.identifier"));
        }
        if (!expect(builder, delimiter)) {
          break;
        }
      }
    }

    if (type != null) {
      element.done(type);
    }
    else {
      element.error(JavaErrorMessages.message("bound.not.expected"));
    }
    return element;
  }
}


File: java/java-psi-impl/src/com/intellij/psi/impl/source/PsiTypeElementImpl.java
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
package com.intellij.psi.impl.source;

import com.intellij.lang.ASTNode;
import com.intellij.psi.*;
import com.intellij.psi.augment.PsiAugmentProvider;
import com.intellij.psi.impl.PsiImplUtil;
import com.intellij.psi.impl.source.codeStyle.CodeEditUtil;
import com.intellij.psi.impl.source.tree.CompositePsiElement;
import com.intellij.psi.impl.source.tree.ElementType;
import com.intellij.psi.impl.source.tree.JavaElementType;
import com.intellij.psi.impl.source.tree.TreeElement;
import com.intellij.psi.scope.PsiScopeProcessor;
import com.intellij.psi.tree.IElementType;
import com.intellij.psi.util.PsiTreeUtil;
import com.intellij.psi.util.PsiUtil;
import com.intellij.util.Function;
import com.intellij.util.IncorrectOperationException;
import com.intellij.util.SmartList;
import com.intellij.util.containers.ContainerUtil;
import org.jetbrains.annotations.NonNls;
import org.jetbrains.annotations.NotNull;
import org.jetbrains.annotations.Nullable;

import java.util.List;

public class PsiTypeElementImpl extends CompositePsiElement implements PsiTypeElement {
  private volatile PsiType myCachedType = null;

  @SuppressWarnings({"UnusedDeclaration"})
  public PsiTypeElementImpl() {
    this(JavaElementType.TYPE);
  }

  protected PsiTypeElementImpl(IElementType type) {
    super(type);
  }

  @Override
  public void clearCaches() {
    super.clearCaches();
    myCachedType = null;
  }

  @Override
  public void accept(@NotNull PsiElementVisitor visitor) {
    if (visitor instanceof JavaElementVisitor) {
      ((JavaElementVisitor)visitor).visitTypeElement(this);
    }
    else {
      visitor.visitElement(this);
    }
  }

  @Override
  @NotNull
  public PsiType getType() {
    PsiType cachedType = myCachedType;
    if (cachedType != null) return cachedType;
    cachedType = calculateType();
    myCachedType = cachedType;
    return cachedType;
  }

  private PsiType calculateType() {
    final PsiType inferredType = PsiAugmentProvider.getInferredType(this);
    if (inferredType != null) {
      return inferredType;
    }

    PsiType type = null;
    SmartList<PsiAnnotation> annotations = new SmartList<PsiAnnotation>();

    for (PsiElement child = getFirstChild(); child != null; child = child.getNextSibling()) {
      if (child instanceof PsiComment || child instanceof PsiWhiteSpace) continue;

      if (child instanceof PsiAnnotation) {
        annotations.add((PsiAnnotation)child);
      }
      else if (child instanceof PsiTypeElement) {
        assert type == null : this;
        if (child instanceof PsiDiamondTypeElementImpl) {
          type = new PsiDiamondTypeImpl(getManager(), this);
          break;
        }
        else {
          type = ((PsiTypeElement)child).getType();
        }
      }
      else if (PsiUtil.isJavaToken(child, ElementType.PRIMITIVE_TYPE_BIT_SET)) {
        assert type == null : this;
        addTypeUseAnnotations(annotations);
        PsiAnnotation[] array = ContainerUtil.copyAndClear(annotations, PsiAnnotation.ARRAY_FACTORY, true);
        type = JavaPsiFacade.getInstance(getProject()).getElementFactory().createPrimitiveType(child.getText(), array);
      }
      else if (child instanceof PsiJavaCodeReferenceElement) {
        assert type == null : this;
        addTypeUseAnnotations(annotations);
        PsiAnnotation[] array = ContainerUtil.copyAndClear(annotations, PsiAnnotation.ARRAY_FACTORY, true);
        type = new PsiClassReferenceType((PsiJavaCodeReferenceElement)child, null, array);
      }
      else if (PsiUtil.isJavaToken(child, JavaTokenType.LBRACKET)) {
        assert type != null : this;
        PsiAnnotation[] array = ContainerUtil.copyAndClear(annotations, PsiAnnotation.ARRAY_FACTORY, true);
        type = type.createArrayType(array);
      }
      else if (PsiUtil.isJavaToken(child, JavaTokenType.ELLIPSIS)) {
        assert type != null : this;
        PsiAnnotation[] array = ContainerUtil.copyAndClear(annotations, PsiAnnotation.ARRAY_FACTORY, true);
        type = PsiEllipsisType.createEllipsis(type, array);
      }

      if (PsiUtil.isJavaToken(child, JavaTokenType.QUEST)) {
        assert type == null : this;
        PsiElement boundKind = PsiTreeUtil.skipSiblingsForward(child, PsiComment.class, PsiWhiteSpace.class);
        PsiElement boundType = PsiTreeUtil.skipSiblingsForward(boundKind, PsiComment.class, PsiWhiteSpace.class);
        if (PsiUtil.isJavaToken(boundKind, JavaTokenType.EXTENDS_KEYWORD) && boundType instanceof PsiTypeElement) {
          type = PsiWildcardType.createExtends(getManager(), ((PsiTypeElement)boundType).getType());
        }
        else if (PsiUtil.isJavaToken(boundKind, JavaTokenType.SUPER_KEYWORD) && boundType instanceof PsiTypeElement) {
          type = PsiWildcardType.createSuper(getManager(), ((PsiTypeElement)boundType).getType());
        }
        else {
          type = PsiWildcardType.createUnbounded(getManager());
        }
        PsiAnnotation[] array = ContainerUtil.copyAndClear(annotations, PsiAnnotation.ARRAY_FACTORY, true);
        type = ((PsiWildcardType)type).annotate(array);
        break;
      }

      if (PsiUtil.isJavaToken(child, JavaTokenType.AND)) {
        List<PsiType> types = collectTypes();
        assert !types.isEmpty() : this;
        type = PsiIntersectionType.createIntersection(false, types.toArray(PsiType.createArray(types.size())));
        break;
      }

      if (PsiUtil.isJavaToken(child, JavaTokenType.OR)) {
        List<PsiType> types = collectTypes();
        assert !types.isEmpty() : this;
        type = PsiDisjunctionType.createDisjunction(types, getManager());
        break;
      }
    }

    return type == null ? PsiType.NULL : type;
  }

  private void addTypeUseAnnotations(List<PsiAnnotation> list) {
    PsiElement parent = this;
    while (parent instanceof PsiTypeElement) {
      PsiElement left = PsiTreeUtil.skipSiblingsBackward(parent, PsiComment.class, PsiWhiteSpace.class, PsiAnnotation.class);

      if (left instanceof PsiModifierList) {
        List<PsiAnnotation> annotations = PsiImplUtil.getTypeUseAnnotations((PsiModifierList)left);
        if (annotations != null && !annotations.isEmpty()) {
          list.addAll(annotations);
        }
        break;
      }

      if (left != null) break;

      parent = parent.getParent();
    }
  }

  private List<PsiType> collectTypes() {
    List<PsiTypeElement> typeElements = PsiTreeUtil.getChildrenOfTypeAsList(this, PsiTypeElement.class);
    return ContainerUtil.map(typeElements, new Function<PsiTypeElement, PsiType>() {
      @Override
      public PsiType fun(PsiTypeElement typeElement) {
        return typeElement.getType();
      }
    });
  }

  @Override
  public PsiJavaCodeReferenceElement getInnermostComponentReferenceElement() {
    TreeElement firstChildNode = getFirstChildNode();
    if (firstChildNode == null) return null;
    if (firstChildNode.getElementType() == JavaElementType.TYPE) {
      return SourceTreeToPsiMap.<PsiTypeElement>treeToPsiNotNull(firstChildNode).getInnermostComponentReferenceElement();
    }
    else {
      return getReferenceElement();
    }
  }

  @Nullable
  private PsiJavaCodeReferenceElement getReferenceElement() {
    ASTNode ref = findChildByType(JavaElementType.JAVA_CODE_REFERENCE);
    if (ref == null) return null;
    return (PsiJavaCodeReferenceElement)SourceTreeToPsiMap.treeElementToPsi(ref);
  }

  @Override
  public boolean processDeclarations(@NotNull PsiScopeProcessor processor,
                                     @NotNull ResolveState state,
                                     PsiElement lastParent,
                                     @NotNull PsiElement place) {
    processor.handleEvent(PsiScopeProcessor.Event.SET_DECLARATION_HOLDER, this);
    return true;
  }

  @Override
  @NotNull
  public PsiAnnotation[] getAnnotations() {
    PsiAnnotation[] annotations = PsiTreeUtil.getChildrenOfType(this, PsiAnnotation.class);
    return annotations != null ? annotations : PsiAnnotation.EMPTY_ARRAY;
  }

  @Override
  @NotNull
  public PsiAnnotation[] getApplicableAnnotations() {
    List<PsiAnnotation> annotations = PsiTreeUtil.getChildrenOfTypeAsList(this, PsiAnnotation.class);
    addTypeUseAnnotations(annotations);
    return annotations.toArray(PsiAnnotation.ARRAY_FACTORY.create(annotations.size()));
  }

  @Override
  public PsiAnnotation findAnnotation(@NotNull @NonNls String qualifiedName) {
    return PsiImplUtil.findAnnotation(this, qualifiedName);
  }

  @Override
  @NotNull
  public PsiAnnotation addAnnotation(@NotNull @NonNls String qualifiedName) {
    throw new UnsupportedOperationException();//todo
  }

  @Override
  public PsiElement replace(@NotNull PsiElement newElement) throws IncorrectOperationException {
    // neighbouring type annotations are logical part of this type element and should be dropped
    PsiImplUtil.markTypeAnnotations(this);
    PsiElement result = super.replace(newElement);
    PsiImplUtil.deleteTypeAnnotations((PsiTypeElement)result);

    // We want to reformat method call arguments on method return type change because there is a possible situation that they are aligned
    // and the change breaks the alignment.
    // Example:
    //     Object test(1,
    //                 2) {}
    // Suppose we're changing return type to 'MyCustomClass'. We get the following if parameter list is not reformatted:
    //     MyCustomClass test(1,
    //                 2) {}
    PsiElement parent = result.getParent();
    if (parent instanceof PsiMethod) {
      PsiMethod method = (PsiMethod)parent;
      CodeEditUtil.markToReformat(method.getParameterList().getNode(), true);
    }

    // We cover situation like below here:
    //     int test(int i, int j) {}
    //     ...
    //     int i = test(1,
    //                  2);
    // I.e. the point is to avoid code like below during changing 'test()' return type from 'int' to 'long':
    //     long i = test(1,
    //                  2);
    else if (parent instanceof PsiVariable) {
      PsiVariable variable = (PsiVariable)parent;
      if (variable.hasInitializer()) {
        PsiExpression methodCallCandidate = variable.getInitializer();
        if (methodCallCandidate instanceof PsiMethodCallExpression) {
          PsiMethodCallExpression methodCallExpression = (PsiMethodCallExpression)methodCallCandidate;
          CodeEditUtil.markToReformat(methodCallExpression.getArgumentList().getNode(), true);
        }
      }
    }

    return result;
  }

  @Override
  public String toString() {
    return "PsiTypeElement:" + getText();
  }
}


File: java/java-tests/testSrc/com/intellij/codeInsight/daemon/LightAdvHighlightingJdk9Test.java
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
package com.intellij.codeInsight.daemon;

import com.intellij.codeInspection.InspectionProfileEntry;
import com.intellij.codeInspection.LocalInspectionTool;
import com.intellij.codeInspection.compiler.JavacQuirksInspection;
import com.intellij.codeInspection.deadCode.UnusedDeclarationInspection;
import com.intellij.codeInspection.redundantCast.RedundantCastInspection;
import com.intellij.codeInspection.uncheckedWarnings.UncheckedWarningLocalInspection;
import com.intellij.openapi.projectRoots.JavaSdkVersion;
import com.intellij.pom.java.LanguageLevel;
import com.intellij.testFramework.IdeaTestUtil;
import org.jetbrains.annotations.NotNull;


public class LightAdvHighlightingJdk9Test extends LightDaemonAnalyzerTestCase {
  private static final String BASE_PATH = "/codeInsight/daemonCodeAnalyzer/advHighlighting9";
  @Override
  protected void setUp() throws Exception {
    super.setUp();
    enableInspectionTool(new UnusedDeclarationInspection());
  }

  private void doTest(boolean checkWarnings, boolean checkInfos, InspectionProfileEntry... classes) {
    setLanguageLevel(LanguageLevel.JDK_1_9);
    IdeaTestUtil.setTestVersion(JavaSdkVersion.JDK_1_9, getModule(), myTestRootDisposable);
    enableInspectionTools(classes);
    doTest(BASE_PATH + "/" + getTestName(false) + ".java", checkWarnings, checkInfos);
  }

  @NotNull
  @Override
  protected LocalInspectionTool[] configureLocalInspectionTools() {
    return new LocalInspectionTool[]{
      new UncheckedWarningLocalInspection(),
      new JavacQuirksInspection(),
      new RedundantCastInspection()
    };
  }

  public void testSafeVarargsApplicability() { doTest(true, false); }
  public void testPrivateInInterfaces() { doTest(false, false); }
}


File: java/java-tests/testSrc/com/intellij/lang/java/parser/partial/ReferenceParserTest.java
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
package com.intellij.lang.java.parser.partial;

import com.intellij.lang.PsiBuilder;
import com.intellij.lang.java.parser.JavaParser;
import com.intellij.lang.java.parser.JavaParsingTestCase;
import com.intellij.lang.java.parser.ReferenceParser;
import com.intellij.pom.java.LanguageLevel;

public class ReferenceParserTest extends JavaParsingTestCase {
  public ReferenceParserTest() {
    super("parser-partial/references");
  }

  public void testReference0() { doRefParserTest("a", false); }
  public void testReference1() { doRefParserTest("a.", true); }
  public void testReference2() { doRefParserTest("a.b", false); }

  public void testType0() { doTypeParserTest("int"); }
  public void testType1() { doTypeParserTest("a.b"); }
  public void testType2() { doTypeParserTest("int[]"); }
  public void testType3() { doTypeParserTest("int[]["); }
  public void testType4() { doTypeParserTest("Map<String,List<String>>"); }
  public void testType5() { doTypeParserTest("Object[]..."); }
  public void testType6() { doTypeParserTest("@English String @NonEmpty []"); }
  public void testType7() { doTypeParserTest("Diamond<>"); }
  public void testType8() { doTypeParserTest("A|"); }
  public void testType9() { doTypeParserTest("A|B"); }

  public void testTypeParams0() { doTypeParamsParserTest("<T>"); }
  public void testTypeParams1() { doTypeParamsParserTest("<T, U>"); }
  public void testTypeParams2() { doTypeParamsParserTest("<T"); }
  public void testTypeParams3() { doTypeParamsParserTest("<T hack>"); }
  public void testTypeParams4() { doTypeParamsParserTest("<T hack"); }
  public void testTypeParams5() { doTypeParamsParserTest("<T extends X & Y<Z>>"); }
  public void testTypeParams6() { doTypeParamsParserTest("<T supers X>"); }
  public void testTypeParams7() { doTypeParamsParserTest("<T extends X, Y>"); }
  public void testTypeParams8() { doTypeParamsParserTest("<?>"); }

  public void testAnyType() {
    setLanguageLevel(LanguageLevel.JDK_1_9);
    doTypeParamsParserTest("<any T>");
  }

  private void doRefParserTest(final String text, final boolean incomplete) {
    doParserTest(text, new MyTestParser(incomplete));
  }
  private static class MyTestParser implements TestParser {
    private final boolean myIncomplete;

    public MyTestParser(boolean incomplete) {
      myIncomplete = incomplete;
    }

    @Override
    public void parse(final PsiBuilder builder) {
      JavaParser.INSTANCE.getReferenceParser().parseJavaCodeReference(builder, myIncomplete, false, false, false);
    }
  }

  private void doTypeParserTest(final String text) {
    doParserTest(text, new MyTestParser2());
  }
  private static class MyTestParser2 implements TestParser {
    @Override
    public void parse(final PsiBuilder builder) {
      JavaParser.INSTANCE.getReferenceParser().parseType(builder, ReferenceParser.ELLIPSIS | ReferenceParser.DIAMONDS | ReferenceParser.DISJUNCTIONS);
    }
  }

  private void doTypeParamsParserTest(final String text) {
    doParserTest(text, new MyTestParser3());
  }
  private static class MyTestParser3 implements TestParser {
    @Override
    public void parse(final PsiBuilder builder) {
      JavaParser.INSTANCE.getReferenceParser().parseTypeParameters(builder);
    }
  }
}
