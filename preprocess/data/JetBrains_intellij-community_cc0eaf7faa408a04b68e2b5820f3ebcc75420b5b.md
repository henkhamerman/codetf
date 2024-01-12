Refactoring Types: ['Extract Method']
ectionGadgetsAnalysis/src/com/siyeh/ig/migration/UnnecessaryBoxingInspection.java
/*
 * Copyright 2003-2014 Dave Griffith, Bas Leijdekkers
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
package com.siyeh.ig.migration;

import com.intellij.codeInspection.ProblemDescriptor;
import com.intellij.codeInspection.ui.SingleCheckboxOptionsPanel;
import com.intellij.openapi.project.Project;
import com.intellij.psi.*;
import com.intellij.psi.util.PsiTreeUtil;
import com.intellij.psi.util.PsiUtil;
import com.intellij.util.IncorrectOperationException;
import com.siyeh.InspectionGadgetsBundle;
import com.siyeh.ig.BaseInspection;
import com.siyeh.ig.BaseInspectionVisitor;
import com.siyeh.ig.InspectionGadgetsFix;
import com.siyeh.ig.PsiReplacementUtil;
import com.siyeh.ig.psiutils.ExpectedTypeUtils;
import com.siyeh.ig.psiutils.MethodCallUtils;
import com.siyeh.ig.psiutils.ParenthesesUtils;
import org.jetbrains.annotations.NonNls;
import org.jetbrains.annotations.NotNull;
import org.jetbrains.annotations.Nullable;

import javax.swing.*;
import java.util.HashMap;
import java.util.Map;

public class UnnecessaryBoxingInspection extends BaseInspection {

  @SuppressWarnings("PublicField")
  public boolean onlyReportSuperfluouslyBoxed = false;

  @NonNls static final Map<String, String> boxedPrimitiveMap = new HashMap<String, String>(8);

  static {
    boxedPrimitiveMap.put(CommonClassNames.JAVA_LANG_INTEGER, "int");
    boxedPrimitiveMap.put(CommonClassNames.JAVA_LANG_SHORT, "short");
    boxedPrimitiveMap.put(CommonClassNames.JAVA_LANG_BOOLEAN, "boolean");
    boxedPrimitiveMap.put(CommonClassNames.JAVA_LANG_LONG, "long");
    boxedPrimitiveMap.put(CommonClassNames.JAVA_LANG_BYTE, "byte");
    boxedPrimitiveMap.put(CommonClassNames.JAVA_LANG_FLOAT, "float");
    boxedPrimitiveMap.put(CommonClassNames.JAVA_LANG_DOUBLE, "double");
    boxedPrimitiveMap.put(CommonClassNames.JAVA_LANG_CHARACTER, "char");
  }

  @Override
  @NotNull
  public String getDisplayName() {
    return InspectionGadgetsBundle.message("unnecessary.boxing.display.name");
  }

  @Override
  public boolean isEnabledByDefault() {
    return true;
  }

  @Nullable
  @Override
  public JComponent createOptionsPanel() {
    return new SingleCheckboxOptionsPanel(InspectionGadgetsBundle.message("unnecessary.boxing.superfluous.option"),
                                          this, "onlyReportSuperfluouslyBoxed");
  }

  @Override
  @NotNull
  protected String buildErrorString(Object... infos) {
    return InspectionGadgetsBundle.message("unnecessary.boxing.problem.descriptor");
  }

  @Override
  public InspectionGadgetsFix buildFix(Object... infos) {
    return new UnnecessaryBoxingFix();
  }

  private static class UnnecessaryBoxingFix extends InspectionGadgetsFix {
    @Override
    @NotNull
    public String getFamilyName() {
      return getName();
    }

    @Override
    @NotNull
    public String getName() {
      return InspectionGadgetsBundle.message("unnecessary.boxing.remove.quickfix");
    }

    @Override
    public void doFix(@NotNull Project project, ProblemDescriptor descriptor) throws IncorrectOperationException {
      final PsiCallExpression expression = (PsiCallExpression)descriptor.getPsiElement();
      final PsiType boxedType = expression.getType();
      if (boxedType == null) {
        return;
      }
      final PsiExpressionList argumentList = expression.getArgumentList();
      if (argumentList == null) {
        return;
      }
      final PsiExpression[] arguments = argumentList.getExpressions();
      if (arguments.length != 1) {
        return;
      }
      final PsiExpression unboxedExpression = arguments[0];
      final PsiType unboxedType = unboxedExpression.getType();
      if (unboxedType == null) {
        return;
      }
      final String cast = getCastString(unboxedType, boxedType);
      if (cast == null) {
        return;
      }
      final int precedence = ParenthesesUtils.getPrecedence(unboxedExpression);
      if (!cast.isEmpty() && precedence > ParenthesesUtils.TYPE_CAST_PRECEDENCE) {
        PsiReplacementUtil.replaceExpression(expression, cast + '(' + unboxedExpression.getText() + ')');
      }
      else {
        PsiReplacementUtil.replaceExpression(expression, cast + unboxedExpression.getText());
      }
    }

    @Nullable
    private static String getCastString(@NotNull PsiType fromType, @NotNull PsiType toType) {
      final String toTypeText = toType.getCanonicalText();
      final String fromTypeText = fromType.getCanonicalText();
      final String unboxedType = boxedPrimitiveMap.get(toTypeText);
      if (unboxedType == null) {
        return null;
      }
      if (fromTypeText.equals(unboxedType)) {
        return "";
      }
      else {
        return '(' + unboxedType + ')';
      }
    }
  }

  @Override
  public boolean shouldInspect(PsiFile file) {
    return PsiUtil.isLanguageLevel5OrHigher(file);
  }

  @Override
  public BaseInspectionVisitor buildVisitor() {
    return new UnnecessaryBoxingVisitor();
  }

  private class UnnecessaryBoxingVisitor extends BaseInspectionVisitor {

    @Override
    public void visitNewExpression(@NotNull PsiNewExpression expression) {
      super.visitNewExpression(expression);
      final PsiType constructorType = expression.getType();
      if (constructorType == null) {
        return;
      }
      final String constructorTypeText = constructorType.getCanonicalText();
      if (!boxedPrimitiveMap.containsKey(constructorTypeText)) {
        return;
      }
      final PsiMethod constructor = expression.resolveConstructor();
      if (constructor == null) {
        return;
      }
      final PsiParameterList parameterList = constructor.getParameterList();
      if (parameterList.getParametersCount() != 1) {
        return;
      }
      final PsiParameter[] parameters = parameterList.getParameters();
      final PsiParameter parameter = parameters[0];
      final PsiType parameterType = parameter.getType();
      final String parameterTypeText = parameterType.getCanonicalText();
      final String boxableConstructorType = boxedPrimitiveMap.get(constructorTypeText);
      if (!boxableConstructorType.equals(parameterTypeText)) {
        return;
      }
      if (!canBeUnboxed(expression)) {
        return;
      }
      if (onlyReportSuperfluouslyBoxed) {
        final PsiType expectedType = ExpectedTypeUtils.findExpectedType(expression, false, true);
        if (!(expectedType instanceof PsiPrimitiveType)) {
          return;
        }
      }
      registerError(expression);
    }

    @Override
    public void visitMethodCallExpression(PsiMethodCallExpression expression) {
      super.visitMethodCallExpression(expression);
      final PsiExpressionList argumentList = expression.getArgumentList();
      final PsiExpression[] arguments = argumentList.getExpressions();
      if (arguments.length != 1) {
        return;
      }
      if (!(arguments[0].getType() instanceof PsiPrimitiveType)) {
        return;
      }
      final PsiReferenceExpression methodExpression = expression.getMethodExpression();
      @NonNls
      final String referenceName = methodExpression.getReferenceName();
      if (!"valueOf".equals(referenceName)) {
        return;
      }
      final PsiExpression qualifierExpression = methodExpression.getQualifierExpression();
      if (!(qualifierExpression instanceof PsiReferenceExpression)) {
        return;
      }
      final PsiReferenceExpression referenceExpression = (PsiReferenceExpression)qualifierExpression;
      final String canonicalText = referenceExpression.getCanonicalText();
      if (!boxedPrimitiveMap.containsKey(canonicalText)) {
        return;
      }
      if (!canBeUnboxed(expression)) {
        return;
      }
      registerError(expression);
    }

    private boolean canBeUnboxed(PsiExpression expression) {
      PsiElement parent = expression.getParent();
      while (parent instanceof PsiParenthesizedExpression) {
        parent = parent.getParent();
      }
      if (parent instanceof PsiExpressionStatement || parent instanceof PsiReferenceExpression) {
        return false;
      }
      else if (parent instanceof PsiTypeCastExpression) {
        final PsiTypeCastExpression castExpression = (PsiTypeCastExpression)parent;
        final PsiType castType = castExpression.getType();
        if (castType instanceof PsiClassType) {
          final PsiClassType classType = (PsiClassType)castType;
          final PsiClass aClass = classType.resolve();
          if (aClass instanceof PsiTypeParameter) {
            return false;
          }
        }
      }
      else if (parent instanceof PsiConditionalExpression) {
        final PsiConditionalExpression conditionalExpression = (PsiConditionalExpression)parent;
        final PsiExpression thenExpression = conditionalExpression.getThenExpression();
        final PsiExpression elseExpression = conditionalExpression.getElseExpression();
        if (elseExpression == null || thenExpression == null) {
          return false;
        }
        if (PsiTreeUtil.isAncestor(thenExpression, expression, false)) {
          final PsiType type = elseExpression.getType();
          return type instanceof PsiPrimitiveType;
        }
        else if (PsiTreeUtil.isAncestor(elseExpression, expression, false)) {
          final PsiType type = thenExpression.getType();
          return type instanceof PsiPrimitiveType;
        }
        else {
          return true;
        }
      }
      else if (parent instanceof PsiBinaryExpression) {
        final PsiBinaryExpression binaryExpression = (PsiBinaryExpression)parent;
        final PsiExpression lhs = binaryExpression.getLOperand();
        final PsiExpression rhs = binaryExpression.getROperand();
        if (rhs == null) {
          return false;
        }
        final PsiType rhsType = rhs.getType();
        if (rhsType == null) {
          return false;
        }
        final PsiType lhsType = lhs.getType();
        if (lhsType == null) {
          return false;
        }
        if (PsiTreeUtil.isAncestor(rhs, expression, false)) {
          final PsiPrimitiveType unboxedType = PsiPrimitiveType.getUnboxedType(rhsType);
          return unboxedType != null && unboxedType.isAssignableFrom(lhsType);
        }
        else {
          final PsiPrimitiveType unboxedType = PsiPrimitiveType.getUnboxedType(lhsType);
          return unboxedType != null && unboxedType.isAssignableFrom(rhsType);
        }
      }
      final PsiCallExpression containingMethodCallExpression = getParentMethodCallExpression(expression);
      return containingMethodCallExpression == null || isSameMethodCalledWithoutBoxing(containingMethodCallExpression, expression);
    }

    @Nullable
    private PsiCallExpression getParentMethodCallExpression(@NotNull PsiElement expression) {
      final PsiElement parent = expression.getParent();
      if (parent instanceof PsiParenthesizedExpression || parent instanceof PsiExpressionList) {
        return getParentMethodCallExpression(parent);
      }
      else if (parent instanceof PsiCallExpression) {
        return (PsiCallExpression)parent;
      }
      else {
        return null;
      }
    }

    private boolean isSameMethodCalledWithoutBoxing(@NotNull PsiCallExpression methodCallExpression,
                                                    @NotNull PsiExpression boxingExpression) {
      final PsiExpressionList argumentList = methodCallExpression.getArgumentList();
      if (argumentList == null) {
        return false;
      }
      final PsiExpression[] expressions = argumentList.getExpressions();
      final PsiMethod originalMethod = methodCallExpression.resolveMethod();
      if (originalMethod == null) {
        return false;
      }
      final String name = originalMethod.getName();
      final PsiClass containingClass = originalMethod.getContainingClass();
      if (containingClass == null) {
        return false;
      }
      final PsiType[] types = PsiType.createArray(expressions.length);

      for (int i = 0; i < expressions.length; i++) {
        final PsiExpression expression = expressions[i];
        final PsiType type = expression.getType();
        if (boxingExpression.equals(expression)) {
          final PsiPrimitiveType unboxedType = PsiPrimitiveType.getUnboxedType(type);
          if (unboxedType == null) {
            return false;
          }
          types[i] = unboxedType;
        }
        else {
          types[i] = type;
        }
      }
      final PsiMethod[] methods = containingClass.findMethodsByName(name, true);
      for (final PsiMethod method : methods) {
        if (!originalMethod.equals(method)) {
          if (MethodCallUtils.isApplicable(method, PsiSubstitutor.EMPTY, types)) {
            return false;
          }
        }
      }
      return true;
    }
  }
}

File: plugins/InspectionGadgets/InspectionGadgetsAnalysis/src/com/siyeh/ig/psiutils/ExpressionUtils.java
/*
 * Copyright 2005-2015 Bas Leijdekkers
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
package com.siyeh.ig.psiutils;

import com.intellij.openapi.project.Project;
import com.intellij.psi.*;
import com.intellij.psi.tree.IElementType;
import com.intellij.psi.util.ConstantExpressionUtil;
import com.intellij.psi.util.PsiTreeUtil;
import com.intellij.util.ArrayUtil;
import org.jetbrains.annotations.NonNls;
import org.jetbrains.annotations.NotNull;
import org.jetbrains.annotations.Nullable;

public class ExpressionUtils {

  private ExpressionUtils() {}

  @Nullable
  public static Object computeConstantExpression(
    @Nullable PsiExpression expression) {
    return computeConstantExpression(expression, false);
  }

  @Nullable
  public static Object computeConstantExpression(
    @Nullable PsiExpression expression,
    boolean throwConstantEvaluationOverflowException) {
    if (expression == null) {
      return null;
    }
    final Project project = expression.getProject();
    final JavaPsiFacade psiFacade = JavaPsiFacade.getInstance(project);
    final PsiConstantEvaluationHelper constantEvaluationHelper =
      psiFacade.getConstantEvaluationHelper();
    return constantEvaluationHelper.computeConstantExpression(expression,
                                                              throwConstantEvaluationOverflowException);
  }

  public static boolean isConstant(PsiField field) {
    if (!field.hasModifierProperty(PsiModifier.FINAL) ||
        !field.hasModifierProperty(PsiModifier.STATIC)) {
      return false;
    }
    if (CollectionUtils.isEmptyArray(field)) {
      return true;
    }
    final PsiType type = field.getType();
    return ClassUtils.isImmutable(type);
  }

  public static boolean isDeclaredConstant(PsiExpression expression) {
    PsiField field =
      PsiTreeUtil.getParentOfType(expression, PsiField.class);
    if (field == null) {
      final PsiAssignmentExpression assignmentExpression =
        PsiTreeUtil.getParentOfType(expression,
                                    PsiAssignmentExpression.class);
      if (assignmentExpression == null) {
        return false;
      }
      final PsiExpression lhs = assignmentExpression.getLExpression();
      if (!(lhs instanceof PsiReferenceExpression)) {
        return false;
      }
      final PsiReferenceExpression referenceExpression =
        (PsiReferenceExpression)lhs;
      final PsiElement target = referenceExpression.resolve();
      if (!(target instanceof PsiField)) {
        return false;
      }
      field = (PsiField)target;
    }
    return field.hasModifierProperty(PsiModifier.STATIC) &&
           field.hasModifierProperty(PsiModifier.FINAL);
  }

  public static boolean isEvaluatedAtCompileTime(@Nullable PsiExpression expression) {
    if (expression instanceof PsiLiteralExpression) {
      return true;
    }
    if (expression instanceof PsiPolyadicExpression) {
      final PsiPolyadicExpression polyadicExpression = (PsiPolyadicExpression)expression;
      final PsiExpression[] operands = polyadicExpression.getOperands();
      for (PsiExpression operand : operands) {
        if (!isEvaluatedAtCompileTime(operand)) {
          return false;
        }
      }
      return true;
    }
    if (expression instanceof PsiPrefixExpression) {
      final PsiPrefixExpression prefixExpression = (PsiPrefixExpression)expression;
      final PsiExpression operand = prefixExpression.getOperand();
      return isEvaluatedAtCompileTime(operand);
    }
    if (expression instanceof PsiReferenceExpression) {
      final PsiReferenceExpression referenceExpression = (PsiReferenceExpression)expression;
      final PsiElement qualifier = referenceExpression.getQualifier();
      if (qualifier instanceof PsiThisExpression) {
        return false;
      }
      final PsiElement element = referenceExpression.resolve();
      if (element instanceof PsiField) {
        final PsiField field = (PsiField)element;
        final PsiExpression initializer = field.getInitializer();
        return field.hasModifierProperty(PsiModifier.FINAL) && isEvaluatedAtCompileTime(initializer);
      }
      if (element instanceof PsiVariable) {
        final PsiVariable variable = (PsiVariable)element;
        if (PsiTreeUtil.isAncestor(variable, expression, true)) {
          return false;
        }
        final PsiExpression initializer = variable.getInitializer();
        return variable.hasModifierProperty(PsiModifier.FINAL) && isEvaluatedAtCompileTime(initializer);
      }
    }
    if (expression instanceof PsiParenthesizedExpression) {
      final PsiParenthesizedExpression parenthesizedExpression = (PsiParenthesizedExpression)expression;
      final PsiExpression deparenthesizedExpression = parenthesizedExpression.getExpression();
      return isEvaluatedAtCompileTime(deparenthesizedExpression);
    }
    if (expression instanceof PsiConditionalExpression) {
      final PsiConditionalExpression conditionalExpression = (PsiConditionalExpression)expression;
      final PsiExpression condition = conditionalExpression.getCondition();
      final PsiExpression thenExpression = conditionalExpression.getThenExpression();
      final PsiExpression elseExpression = conditionalExpression.getElseExpression();
      return isEvaluatedAtCompileTime(condition) &&
             isEvaluatedAtCompileTime(thenExpression) &&
             isEvaluatedAtCompileTime(elseExpression);
    }
    if (expression instanceof PsiTypeCastExpression) {
      final PsiTypeCastExpression typeCastExpression = (PsiTypeCastExpression)expression;
      final PsiTypeElement castType = typeCastExpression.getCastType();
      if (castType == null) {
        return false;
      }
      final PsiType type = castType.getType();
      return TypeUtils.typeEquals(CommonClassNames.JAVA_LANG_STRING, type);
    }
    return false;
  }

  @Nullable
  public static String getLiteralString(@Nullable PsiExpression expression) {
    final PsiLiteralExpression literal = getLiteral(expression);
    if (literal == null) {
      return null;
    }
    final Object value = literal.getValue();
    if (value == null) {
      return null;
    }
    return value.toString();
  }

  @Nullable
  public static PsiLiteralExpression getLiteral(@Nullable PsiExpression expression) {
    expression = ParenthesesUtils.stripParentheses(expression);
    if (expression instanceof PsiLiteralExpression) {
      return (PsiLiteralExpression)expression;
    }
    if (!(expression instanceof PsiTypeCastExpression)) {
      return null;
    }
    final PsiTypeCastExpression typeCastExpression = (PsiTypeCastExpression)expression;
    final PsiExpression operand = ParenthesesUtils.stripParentheses(typeCastExpression.getOperand());
    if (!(operand instanceof PsiLiteralExpression)) {
      return null;
    }
    return (PsiLiteralExpression)operand;
  }

  public static boolean isLiteral(@Nullable PsiExpression expression) {
    return getLiteral(expression) != null;
  }

  public static boolean isEmptyStringLiteral(@Nullable PsiExpression expression) {
    expression = ParenthesesUtils.stripParentheses(expression);
    if (!(expression instanceof PsiLiteralExpression)) {
      return false;
    }
    final String text = expression.getText();
    return "\"\"".equals(text);
  }

  public static boolean isNullLiteral(@Nullable PsiExpression expression) {
    expression = ParenthesesUtils.stripParentheses(expression);
    return expression != null && PsiType.NULL.equals(expression.getType());
  }

  public static boolean isZero(@Nullable PsiExpression expression) {
    if (expression == null) {
      return false;
    }
    final PsiType expressionType = expression.getType();
    final Object value = ConstantExpressionUtil.computeCastTo(expression,
                                                              expressionType);
    if (value == null) {
      return false;
    }
    if (value instanceof Double && ((Double)value).doubleValue() == 0.0) {
      return true;
    }
    if (value instanceof Float && ((Float)value).floatValue() == 0.0f) {
      return true;
    }
    if (value instanceof Integer && ((Integer)value).intValue() == 0) {
      return true;
    }
    if (value instanceof Long && ((Long)value).longValue() == 0L) {
      return true;
    }
    if (value instanceof Short && ((Short)value).shortValue() == 0) {
      return true;
    }
    if (value instanceof Character && ((Character)value).charValue() == 0) {
      return true;
    }
    return value instanceof Byte && ((Byte)value).byteValue() == 0;
  }

  public static boolean isOne(@Nullable PsiExpression expression) {
    if (expression == null) {
      return false;
    }
    final Object value = computeConstantExpression(expression);
    if (value == null) {
      return false;
    }
    //noinspection FloatingPointEquality
    if (value instanceof Double && ((Double)value).doubleValue() == 1.0) {
      return true;
    }
    if (value instanceof Float && ((Float)value).floatValue() == 1.0f) {
      return true;
    }
    if (value instanceof Integer && ((Integer)value).intValue() == 1) {
      return true;
    }
    if (value instanceof Long && ((Long)value).longValue() == 1L) {
      return true;
    }
    if (value instanceof Short && ((Short)value).shortValue() == 1) {
      return true;
    }
    if (value instanceof Character && ((Character)value).charValue() == 1) {
      return true;
    }
    return value instanceof Byte && ((Byte)value).byteValue() == 1;
  }

  public static boolean isNegation(@Nullable PsiExpression condition,
                                   boolean ignoreNegatedNullComparison, boolean ignoreNegatedZeroComparison) {
    condition = ParenthesesUtils.stripParentheses(condition);
    if (condition instanceof PsiPrefixExpression) {
      final PsiPrefixExpression prefixExpression = (PsiPrefixExpression)condition;
      final IElementType tokenType = prefixExpression.getOperationTokenType();
      return tokenType.equals(JavaTokenType.EXCL);
    }
    else if (condition instanceof PsiBinaryExpression) {
      final PsiBinaryExpression binaryExpression = (PsiBinaryExpression)condition;
      final PsiExpression lhs = ParenthesesUtils.stripParentheses(binaryExpression.getLOperand());
      final PsiExpression rhs = ParenthesesUtils.stripParentheses(binaryExpression.getROperand());
      if (lhs == null || rhs == null) {
        return false;
      }
      final IElementType tokenType = binaryExpression.getOperationTokenType();
      if (tokenType.equals(JavaTokenType.NE)) {
        if (ignoreNegatedNullComparison) {
          final String lhsText = lhs.getText();
          final String rhsText = rhs.getText();
          if (PsiKeyword.NULL.equals(lhsText) || PsiKeyword.NULL.equals(rhsText)) {
            return false;
          }
        }
        return !(ignoreNegatedZeroComparison && (isZeroLiteral(lhs) || isZeroLiteral(rhs)));
      }
    }
    return false;
  }

  private static boolean isZeroLiteral(PsiExpression expression) {
    if (!(expression instanceof PsiLiteralExpression)) {
      return false;
    }
    final PsiLiteralExpression literalExpression = (PsiLiteralExpression)expression;
    final Object value = literalExpression.getValue();
    if (value instanceof Integer) {
      if (((Integer)value).intValue() == 0) {
        return true;
      }
    } else if (value instanceof Long) {
      if (((Long)value).longValue() == 0L) {
        return true;
      }
    }
    return false;
  }

  public static boolean isOffsetArrayAccess(
    @Nullable PsiExpression expression, @NotNull PsiVariable variable) {
    final PsiExpression strippedExpression =
      ParenthesesUtils.stripParentheses(expression);
    if (!(strippedExpression instanceof PsiArrayAccessExpression)) {
      return false;
    }
    final PsiArrayAccessExpression arrayAccessExpression =
      (PsiArrayAccessExpression)strippedExpression;
    final PsiExpression arrayExpression =
      arrayAccessExpression.getArrayExpression();
    if (isOffsetArrayAccess(arrayExpression, variable)) {
      return false;
    }
    final PsiExpression index = arrayAccessExpression.getIndexExpression();
    if (index == null) {
      return false;
    }
    return expressionIsOffsetVariableLookup(index, variable);
  }

  private static boolean expressionIsOffsetVariableLookup(
    @Nullable PsiExpression expression, @NotNull PsiVariable variable) {
    if (VariableAccessUtils.evaluatesToVariable(expression,
                                                variable)) {
      return true;
    }
    final PsiExpression strippedExpression =
      ParenthesesUtils.stripParentheses(expression);
    if (!(strippedExpression instanceof PsiBinaryExpression)) {
      return false;
    }
    final PsiBinaryExpression binaryExpression =
      (PsiBinaryExpression)strippedExpression;
    final IElementType tokenType = binaryExpression.getOperationTokenType();
    if (!JavaTokenType.PLUS.equals(tokenType) &&
        !JavaTokenType.MINUS.equals(tokenType)) {
      return false;
    }
    final PsiExpression lhs = binaryExpression.getLOperand();
    if (expressionIsOffsetVariableLookup(lhs, variable)) {
      return true;
    }
    final PsiExpression rhs = binaryExpression.getROperand();
    return expressionIsOffsetVariableLookup(rhs, variable) &&
           !JavaTokenType.MINUS.equals(tokenType);
  }

  public static boolean isVariableLessThanComparison(
    @Nullable PsiExpression expression,
    @NotNull PsiVariable variable) {
    expression = ParenthesesUtils.stripParentheses(expression);
    if (!(expression instanceof PsiBinaryExpression)) {
      return false;
    }
    final PsiBinaryExpression binaryExpression =
      (PsiBinaryExpression)expression;
    final IElementType tokenType = binaryExpression.getOperationTokenType();
    if (tokenType.equals(JavaTokenType.LT) ||
        tokenType.equals(JavaTokenType.LE)) {
      final PsiExpression lhs = binaryExpression.getLOperand();
      return VariableAccessUtils.evaluatesToVariable(lhs, variable);
    }
    else if (tokenType.equals(JavaTokenType.GT) ||
             tokenType.equals(JavaTokenType.GE)) {
      final PsiExpression rhs = binaryExpression.getROperand();
      return VariableAccessUtils.evaluatesToVariable(rhs, variable);
    }
    return false;
  }

  public static boolean isVariableGreaterThanComparison(
    @Nullable PsiExpression expression,
    @NotNull PsiVariable variable) {
    expression = ParenthesesUtils.stripParentheses(expression);
    if (!(expression instanceof PsiBinaryExpression)) {
      return false;
    }
    final PsiBinaryExpression binaryExpression =
      (PsiBinaryExpression)expression;
    final IElementType tokenType = binaryExpression.getOperationTokenType();
    if (tokenType.equals(JavaTokenType.GT) ||
        tokenType.equals(JavaTokenType.GE)) {
      final PsiExpression lhs = binaryExpression.getLOperand();
      return VariableAccessUtils.evaluatesToVariable(lhs, variable);
    }
    else if (tokenType.equals(JavaTokenType.LT) ||
             tokenType.equals(JavaTokenType.LE)) {
      final PsiExpression rhs = binaryExpression.getROperand();
      return VariableAccessUtils.evaluatesToVariable(rhs, variable);
    }
    return false;
  }

  public static boolean isZeroLengthArrayConstruction(
    @Nullable PsiExpression expression) {
    if (!(expression instanceof PsiNewExpression)) {
      return false;
    }
    final PsiNewExpression newExpression = (PsiNewExpression)expression;
    final PsiExpression[] dimensions = newExpression.getArrayDimensions();
    if (dimensions.length == 0) {
      final PsiArrayInitializerExpression arrayInitializer =
        newExpression.getArrayInitializer();
      if (arrayInitializer == null) {
        return false;
      }
      final PsiExpression[] initializers =
        arrayInitializer.getInitializers();
      return initializers.length == 0;
    }
    for (PsiExpression dimension : dimensions) {
      final String dimensionText = dimension.getText();
      if (!"0".equals(dimensionText)) {
        return false;
      }
    }
    return true;
  }

  public static boolean isStringConcatenationOperand(PsiExpression expression) {
    final PsiElement parent = expression.getParent();
    if (!(parent instanceof PsiPolyadicExpression)) {
      return false;
    }
    final PsiPolyadicExpression polyadicExpression =
      (PsiPolyadicExpression)parent;
    if (!JavaTokenType.PLUS.equals(
      polyadicExpression.getOperationTokenType())) {
      return false;
    }
    final PsiExpression[] operands = polyadicExpression.getOperands();
    if (operands.length < 2) {
      return false;
    }
    final int index = ArrayUtil.indexOf(operands, expression);
    for (int i = 0; i < index; i++) {
      final PsiType type = operands[i].getType();
      if (TypeUtils.isJavaLangString(type)) {
        return true;
      }
    }
    if (index == 0) {
      final PsiType type = operands[index + 1].getType();
      return TypeUtils.isJavaLangString(type);
    }
    return false;
  }


  public static boolean isConstructorInvocation(PsiElement element) {
    if (!(element instanceof PsiMethodCallExpression)) {
      return false;
    }
    final PsiMethodCallExpression methodCallExpression =
      (PsiMethodCallExpression)element;
    final PsiReferenceExpression methodExpression =
      methodCallExpression.getMethodExpression();
    final String callName = methodExpression.getReferenceName();
    return PsiKeyword.THIS.equals(callName) ||
           PsiKeyword.SUPER.equals(callName);
  }

  public static boolean hasType(@Nullable PsiExpression expression, @NonNls @NotNull String typeName) {
    if (expression == null) {
      return false;
    }
    final PsiType type = expression.getType();
    return TypeUtils.typeEquals(typeName, type);
  }

  public static boolean hasStringType(@Nullable PsiExpression expression) {
    return hasType(expression, CommonClassNames.JAVA_LANG_STRING);
  }

  public static boolean isConversionToStringNecessary(PsiExpression expression, boolean throwable) {
    final PsiElement parent = ParenthesesUtils.getParentSkipParentheses(expression);
    if (parent instanceof PsiPolyadicExpression) {
      final PsiPolyadicExpression polyadicExpression = (PsiPolyadicExpression)parent;
      final PsiType type = polyadicExpression.getType();
      if (!TypeUtils.typeEquals(CommonClassNames.JAVA_LANG_STRING, type)) {
        return true;
      }
      final PsiExpression[] operands = polyadicExpression.getOperands();
      int index = -1;
      for (int i = 0, length = operands.length; i < length; i++) {
        final PsiExpression operand = operands[i];
        if (PsiTreeUtil.isAncestor(operand, expression, false)) {
          index = i;
          break;
        }
      }
      if (index > 0) {
        if (!TypeUtils.typeEquals(CommonClassNames.JAVA_LANG_STRING, operands[index - 1].getType())) {
          return true;
        }
      } else if (operands.length > 1) {
        if (!TypeUtils.typeEquals(CommonClassNames.JAVA_LANG_STRING, operands[index + 1].getType())) {
          return true;
        }
      } else {
        return true;
      }
    } else if (parent instanceof PsiExpressionList) {
      final PsiExpressionList expressionList = (PsiExpressionList)parent;
      final PsiElement grandParent = expressionList.getParent();
      if (!(grandParent instanceof PsiMethodCallExpression)) {
        return true;
      }
      final PsiMethodCallExpression methodCallExpression = (PsiMethodCallExpression)grandParent;
      final PsiReferenceExpression methodExpression1 = methodCallExpression.getMethodExpression();
      @NonNls final String name = methodExpression1.getReferenceName();
      final PsiExpression[] expressions = expressionList.getExpressions();
      if ("insert".equals(name)) {
        if (expressions.length < 2 || !expression.equals(ParenthesesUtils.stripParentheses(expressions[1]))) {
          return true;
        }
        if (!isCallToMethodIn(methodCallExpression, "java.lang.StringBuilder", "java.lang.StringBuffer")) {
          return true;
        }
      } else if ("append".equals(name)) {
        if (expressions.length < 1 || !expression.equals(ParenthesesUtils.stripParentheses(expressions[0]))) {
          return true;
        }
        if (!isCallToMethodIn(methodCallExpression, "java.lang.StringBuilder", "java.lang.StringBuffer")) {
          return true;
        }
      } else if ("print".equals(name) || "println".equals(name)) {
        if (!isCallToMethodIn(methodCallExpression, "java.io.PrintStream", "java.io.PrintWriter")) {
          return true;
        }
      } else if ("trace".equals(name) || "debug".equals(name) || "info".equals(name) || "warn".equals(name) || "error".equals(name)) {
        if (!isCallToMethodIn(methodCallExpression, "org.slf4j.Logger")) {
          return true;
        }
        int l = 1;
        for (int i = 0; i < expressions.length; i++) {
          final PsiExpression expression1 = expressions[i];
          if (i == 0 && TypeUtils.expressionHasTypeOrSubtype(expression1, "org.slf4j.Marker")) {
            l = 2;
          }
          if (expression1 == expression) {
            if (i < l || (throwable && i == expressions.length - 1)) {
              return true;
            }
          }
        }
      } else {
        return true;
      }
    } else {
      return true;
    }
    return false;
  }

  private static boolean isCallToMethodIn(PsiMethodCallExpression methodCallExpression, String... classNames) {
    final PsiMethod method = methodCallExpression.resolveMethod();
    if (method == null) {
      return false;
    }
    final PsiClass containingClass = method.getContainingClass();
    if (containingClass == null) {
      return false;
    }
    final String qualifiedName = containingClass.getQualifiedName();
    for (String className : classNames) {
      if (className.equals(qualifiedName)) {
        return true;
      }
    }
    return false;
  }

  public static boolean isNegative(@NotNull PsiExpression expression) {
    final PsiElement parent = expression.getParent();
    if (!(parent instanceof PsiPrefixExpression)) {
      return false;
    }
    final PsiPrefixExpression prefixExpression = (PsiPrefixExpression)parent;
    final IElementType tokenType = prefixExpression.getOperationTokenType();
    return JavaTokenType.MINUS.equals(tokenType);
  }

  @Nullable
  public static PsiVariable getVariableFromNullComparison(PsiExpression expression, boolean equals) {
    expression = ParenthesesUtils.stripParentheses(expression);
    if (!(expression instanceof PsiPolyadicExpression)) {
      return null;
    }
    final PsiPolyadicExpression polyadicExpression = (PsiPolyadicExpression)expression;
    final IElementType tokenType = polyadicExpression.getOperationTokenType();
    if (equals) {
      if (!JavaTokenType.EQEQ.equals(tokenType)) {
        return null;
      }
    }
    else {
      if (!JavaTokenType.NE.equals(tokenType)) {
        return null;
      }
    }
    final PsiExpression[] operands = polyadicExpression.getOperands();
    if (operands.length != 2) {
      return null;
    }
    if (PsiType.NULL.equals(operands[0].getType())) {
      return getVariable(operands[1]);
    }
    else if (PsiType.NULL.equals(operands[1].getType())) {
      return getVariable(operands[0]);
    }
    return null;
  }

  public static PsiVariable getVariable(PsiExpression expression) {
    expression = ParenthesesUtils.stripParentheses(expression);
    if (!(expression instanceof PsiReferenceExpression)) {
      return null;
    }
    final PsiReferenceExpression referenceExpression = (PsiReferenceExpression)expression;
    final PsiElement target = referenceExpression.resolve();
    if (!(target instanceof PsiVariable)) {
      return null;
    }
    return (PsiVariable)target;
  }

  public static boolean isConcatenation(PsiElement element) {
    if (!(element instanceof PsiPolyadicExpression)) {
      return false;
    }
    final PsiPolyadicExpression expression = (PsiPolyadicExpression)element;
    final PsiType type = expression.getType();
    return type != null && type.equalsToText(CommonClassNames.JAVA_LANG_STRING);
  }
}

File: plugins/InspectionGadgets/InspectionGadgetsAnalysis/src/com/siyeh/ig/psiutils/SwitchUtils.java
/*
 * Copyright 2003-2014 Dave Griffith, Bas Leijdekkers
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
package com.siyeh.ig.psiutils;

import com.intellij.codeInsight.NullableNotNullManager;
import com.intellij.pom.java.LanguageLevel;
import com.intellij.psi.*;
import com.intellij.psi.tree.IElementType;
import com.intellij.psi.util.PsiTreeUtil;
import com.intellij.psi.util.PsiUtil;
import org.jetbrains.annotations.NonNls;
import org.jetbrains.annotations.NotNull;
import org.jetbrains.annotations.Nullable;

import java.util.*;

public class SwitchUtils {

  private SwitchUtils() {}

  public static int calculateBranchCount(@NotNull PsiSwitchStatement statement) {
    final PsiCodeBlock body = statement.getBody();
    if (body == null) {
      return 0;
    }
    final PsiStatement[] statements = body.getStatements();
    int branches = 0;
    for (final PsiStatement child : statements) {
      if (child instanceof PsiSwitchLabelStatement) {
        branches++;
      }
    }
    return branches;
  }

  @Nullable
  public static PsiExpression getSwitchExpression(PsiIfStatement statement, int minimumBranches) {
    return getSwitchExpression(statement, minimumBranches, false);
  }

  @Nullable
  public static PsiExpression getSwitchExpression(PsiIfStatement statement, int minimumBranches, boolean nullSafe) {
    final PsiExpression condition = statement.getCondition();
    final LanguageLevel languageLevel = PsiUtil.getLanguageLevel(statement);
    final PsiExpression possibleSwitchExpression = determinePossibleSwitchExpressions(condition, languageLevel, nullSafe);
    if (!canBeSwitchExpression(possibleSwitchExpression, languageLevel)) {
      return null;
    }
    int branchCount = 0;
    while (true) {
      branchCount++;
      if (!canBeMadeIntoCase(statement.getCondition(), possibleSwitchExpression, languageLevel, false)) {
        break;
      }
      final PsiStatement elseBranch = statement.getElseBranch();
      if (!(elseBranch instanceof PsiIfStatement)) {
        if (elseBranch != null) {
          branchCount++;
        }
        if (branchCount < minimumBranches) {
          return null;
        }
        return possibleSwitchExpression;
      }
      statement = (PsiIfStatement)elseBranch;
    }
    return null;
  }

  private static boolean canBeMadeIntoCase(PsiExpression expression, PsiExpression switchExpression, LanguageLevel languageLevel,
                                           boolean nullSafe) {
    expression = ParenthesesUtils.stripParentheses(expression);
    if (languageLevel.isAtLeast(LanguageLevel.JDK_1_7)) {
      final PsiExpression stringSwitchExpression = determinePossibleStringSwitchExpression(expression, nullSafe);
      if (EquivalenceChecker.expressionsAreEquivalent(switchExpression, stringSwitchExpression)) {
        return true;
      }
    }
    if (!(expression instanceof PsiPolyadicExpression)) {
      return false;
    }
    final PsiPolyadicExpression polyadicExpression = (PsiPolyadicExpression)expression;
    final IElementType operation = polyadicExpression.getOperationTokenType();
    final PsiExpression[] operands = polyadicExpression.getOperands();
    if (operation.equals(JavaTokenType.OROR)) {
      for (PsiExpression operand : operands) {
        if (!canBeMadeIntoCase(operand, switchExpression, languageLevel, nullSafe)) {
          return false;
        }
      }
      return true;
    }
    else if (operation.equals(JavaTokenType.EQEQ) && operands.length == 2) {
      return (canBeCaseLabel(operands[0], languageLevel) && EquivalenceChecker.expressionsAreEquivalent(switchExpression, operands[1])) ||
             (canBeCaseLabel(operands[1], languageLevel) && EquivalenceChecker.expressionsAreEquivalent(switchExpression, operands[0]));
    }
    else {
      return false;
    }
  }

  private static boolean canBeSwitchExpression(PsiExpression expression, LanguageLevel languageLevel) {
    if (expression == null || SideEffectChecker.mayHaveSideEffects(expression)) {
      return false;
    }
    final PsiType type = expression.getType();
    if (PsiType.CHAR.equals(type) || PsiType.BYTE.equals(type) || PsiType.SHORT.equals(type) || PsiType.INT.equals(type)) {
      return true;
    }
    else if (type instanceof PsiClassType) {
      if (isAnnotatedNullable(expression)) {
        return false;
      }
      if (type.equalsToText(CommonClassNames.JAVA_LANG_CHARACTER) || type.equalsToText(CommonClassNames.JAVA_LANG_BYTE) ||
          type.equalsToText(CommonClassNames.JAVA_LANG_SHORT) || type.equalsToText(CommonClassNames.JAVA_LANG_INTEGER)) {
        return true;
      }
      if (languageLevel.isAtLeast(LanguageLevel.JDK_1_5)) {
        final PsiClassType classType = (PsiClassType)type;
        final PsiClass aClass = classType.resolve();
        if (aClass != null && aClass.isEnum()) {
          return true;
        }
      }
      if (languageLevel.isAtLeast(LanguageLevel.JDK_1_7) && type.equalsToText(CommonClassNames.JAVA_LANG_STRING)) {
        return true;
      }
    }
    return false;
  }

  private static PsiExpression determinePossibleSwitchExpressions(PsiExpression expression, LanguageLevel languageLevel, boolean nullSafe) {
    expression = ParenthesesUtils.stripParentheses(expression);
    if (expression == null) {
      return null;
    }
    if (languageLevel.isAtLeast(LanguageLevel.JDK_1_7)) {
      final PsiExpression jdk17Expression = determinePossibleStringSwitchExpression(expression, nullSafe);
      if (jdk17Expression != null) {
        return jdk17Expression;
      }
    }
    if (!(expression instanceof PsiPolyadicExpression)) {
      return null;
    }
    final PsiPolyadicExpression polyadicExpression = (PsiPolyadicExpression)expression;
    final IElementType operation = polyadicExpression.getOperationTokenType();
    final PsiExpression[] operands = polyadicExpression.getOperands();
    if (operation.equals(JavaTokenType.OROR) && operands.length > 0) {
      return determinePossibleSwitchExpressions(operands[0], languageLevel, nullSafe);
    }
    else if (operation.equals(JavaTokenType.EQEQ) && operands.length == 2) {
      final PsiExpression lhs = operands[0];
      final PsiExpression rhs = operands[1];
      if (canBeCaseLabel(lhs, languageLevel)) {
        return rhs;
      }
      else if (canBeCaseLabel(rhs, languageLevel)) {
        return lhs;
      }
    }
    return null;
  }

  private static PsiExpression determinePossibleStringSwitchExpression(PsiExpression expression, boolean nullSafe) {
    if (!(expression instanceof PsiMethodCallExpression)) {
      return null;
    }
    final PsiMethodCallExpression methodCallExpression = (PsiMethodCallExpression)expression;
    final PsiReferenceExpression methodExpression = methodCallExpression.getMethodExpression();
    @NonNls final String referenceName = methodExpression.getReferenceName();
    if (!"equals".equals(referenceName)) {
      return null;
    }
    final PsiExpression qualifierExpression = methodExpression.getQualifierExpression();
    if (qualifierExpression == null) {
      return null;
    }
    final PsiType type = qualifierExpression.getType();
    if (type == null || !type.equalsToText(CommonClassNames.JAVA_LANG_STRING)) {
      return null;
    }
    final PsiExpressionList argumentList = methodCallExpression.getArgumentList();
    final PsiExpression[] arguments = argumentList.getExpressions();
    if (arguments.length != 1) {
      return null;
    }
    final PsiExpression argument = arguments[0];
    final PsiType argumentType = argument.getType();
    if (argumentType == null || !argumentType.equalsToText(CommonClassNames.JAVA_LANG_STRING)) {
      return null;
    }
    if (PsiUtil.isConstantExpression(qualifierExpression)) {
      if (nullSafe && !isAnnotatedNotNull(argument)) {
        return null;
      }
      return argument;
    }
    else if (PsiUtil.isConstantExpression(argument)) {
      return qualifierExpression;
    }
    return null;
  }

  private static boolean isAnnotatedNotNull(PsiExpression expression) {
    expression = ParenthesesUtils.stripParentheses(expression);
    if (!(expression instanceof PsiReferenceExpression)) {
      return false;
    }
    final PsiReferenceExpression referenceExpression = (PsiReferenceExpression)expression;
    final PsiElement target = referenceExpression.resolve();
    if (!(target instanceof PsiModifierListOwner)) {
      return false;
    }
    final PsiModifierListOwner modifierListOwner = (PsiModifierListOwner)target;
    return NullableNotNullManager.isNotNull(modifierListOwner);
  }

  private static boolean isAnnotatedNullable(PsiExpression expression) {
    expression = ParenthesesUtils.stripParentheses(expression);
    if (!(expression instanceof PsiReferenceExpression)) {
      return false;
    }
    final PsiReferenceExpression referenceExpression = (PsiReferenceExpression)expression;
    final PsiElement target = referenceExpression.resolve();
    if (!(target instanceof PsiModifierListOwner)) {
      return false;
    }
    final PsiModifierListOwner modifierListOwner = (PsiModifierListOwner)target;
    return NullableNotNullManager.isNullable(modifierListOwner);
  }

  private static boolean canBeCaseLabel(PsiExpression expression, LanguageLevel languageLevel) {
    if (expression == null) {
      return false;
    }
    if (languageLevel.isAtLeast(LanguageLevel.JDK_1_5) && expression instanceof PsiReferenceExpression) {
      final PsiElement referent = ((PsiReference)expression).resolve();
      if (referent instanceof PsiEnumConstant) {
        return true;
      }
    }
    final PsiType type = expression.getType();
    return (PsiType.INT.equals(type) || PsiType.SHORT.equals(type) || PsiType.BYTE.equals(type) || PsiType.CHAR.equals(type)) &&
           PsiUtil.isConstantExpression(expression);
  }

  public static String findUniqueLabelName(PsiStatement statement, @NonNls String baseName) {
    final PsiElement ancestor = PsiTreeUtil.getParentOfType(statement, PsiMember.class);
    if (!checkForLabel(baseName, ancestor)) {
      return baseName;
    }
    int val = 1;
    while (true) {
      final String name = baseName + val;
      if (!checkForLabel(name, ancestor)) {
        return name;
      }
      val++;
    }
  }

  private static boolean checkForLabel(String name, PsiElement ancestor) {
    final LabelSearchVisitor visitor = new LabelSearchVisitor(name);
    ancestor.accept(visitor);
    return visitor.isUsed();
  }

  private static class LabelSearchVisitor extends JavaRecursiveElementWalkingVisitor {

    private final String m_labelName;
    private boolean m_used = false;

    LabelSearchVisitor(String name) {
      m_labelName = name;
    }

    @Override
    public void visitElement(PsiElement element) {
      if (m_used) {
        return;
      }
      super.visitElement(element);
    }

    @Override
    public void visitLabeledStatement(PsiLabeledStatement statement) {
      final PsiIdentifier labelIdentifier = statement.getLabelIdentifier();
      final String labelText = labelIdentifier.getText();
      if (labelText.equals(m_labelName)) {
        m_used = true;
      }
    }

    public boolean isUsed() {
      return m_used;
    }
  }

  public static class IfStatementBranch {

    private final Set<String> topLevelVariables = new HashSet<String>(3);
    private final LinkedList<String> comments = new LinkedList<String>();
    private final LinkedList<String> statementComments = new LinkedList<String>();
    private final List<PsiExpression> caseExpressions = new ArrayList<PsiExpression>(3);
    private final PsiStatement statement;
    private final boolean elseBranch;

    public IfStatementBranch(PsiStatement branch, boolean elseBranch) {
      statement = branch;
      this.elseBranch = elseBranch;
      calculateVariablesDeclared(statement);
    }

    public void addComment(String comment) {
      comments.addFirst(comment);
    }

    public void addStatementComment(String comment) {
      statementComments.addFirst(comment);
    }

    public void addCaseExpression(PsiExpression expression) {
      caseExpressions.add(expression);
    }

    public PsiStatement getStatement() {
      return statement;
    }

    public List<PsiExpression> getCaseExpressions() {
      return Collections.unmodifiableList(caseExpressions);
    }

    public boolean isElse() {
      return elseBranch;
    }

    public boolean topLevelDeclarationsConflictWith(IfStatementBranch testBranch) {
      final Set<String> topLevel = testBranch.topLevelVariables;
      return intersects(topLevelVariables, topLevel);
    }

    private static boolean intersects(Set<String> set1, Set<String> set2) {
      for (final String s : set1) {
        if (set2.contains(s)) {
          return true;
        }
      }
      return false;
    }

    public List<String> getComments() {
      return comments;
    }

    public List<String> getStatementComments() {
      return statementComments;
    }

    public void calculateVariablesDeclared(PsiStatement statement) {
      if (statement == null) {
        return;
      }
      if (statement instanceof PsiDeclarationStatement) {
        final PsiDeclarationStatement declarationStatement = (PsiDeclarationStatement)statement;
        final PsiElement[] elements = declarationStatement.getDeclaredElements();
        for (PsiElement element : elements) {
          final PsiVariable variable = (PsiVariable)element;
          final String varName = variable.getName();
          topLevelVariables.add(varName);
        }
      }
      else if (statement instanceof PsiBlockStatement) {
        final PsiBlockStatement block = (PsiBlockStatement)statement;
        final PsiCodeBlock codeBlock = block.getCodeBlock();
        final PsiStatement[] statements = codeBlock.getStatements();
        for (PsiStatement statement1 : statements) {
          calculateVariablesDeclared(statement1);
        }
      }
    }
  }
}


File: plugins/InspectionGadgets/test/com/siyeh/igtest/migration/unnecessary_boxing/UnnecessaryBoxing.java
package com.siyeh.igtest.migration.unnecessary_boxing;




public class UnnecessaryBoxing {

    Integer foo(String foo, Integer bar) {
        return foo == null ? Integer.valueOf(0) : bar;
    }

    public static void main(String[] args)
    {
        final Integer intValue = <warning descr="Unnecessary boxing 'new Integer(3)'">new Integer(3)</warning>;
        final Long longValue = <warning descr="Unnecessary boxing 'new Long(3L)'">new Long(3L)</warning>;
        final Long longValue2 = <warning descr="Unnecessary boxing 'new Long(3)'">new Long(3)</warning>;
        final Short shortValue = <warning descr="Unnecessary boxing 'new Short((short)3)'">new Short((short)3)</warning>;
        final Double doubleValue = <warning descr="Unnecessary boxing 'new Double(3.0)'">new Double(3.0)</warning>;
        final Float floatValue = <warning descr="Unnecessary boxing 'new Float(3.0F)'">new Float(3.0F)</warning>;
        final Byte byteValue = <warning descr="Unnecessary boxing 'new Byte((byte)3)'">new Byte((byte)3)</warning>;
        final Boolean booleanValue = <warning descr="Unnecessary boxing 'new Boolean(true)'">new Boolean(true)</warning>;
        final Character character = <warning descr="Unnecessary boxing 'new Character('c')'">new Character('c')</warning>;
    }

    Integer foo2(String foo, int bar) {
        return foo == null ? <warning descr="Unnecessary boxing 'Integer.valueOf(0)'">Integer.valueOf(0)</warning> : bar;
    }

    void noUnboxing(Object val) {
        if (val == Integer.valueOf(0)) {

        } else if (Integer.valueOf(1) == val) {}
        boolean b = true;
        Boolean.valueOf(b).toString();
    }

    public Integer getBar() {
        return null;
    }

    void doItNow(UnnecessaryBoxing foo) {
        Integer bla = foo == null ? Integer.valueOf(0) : foo.getBar();
    }

    private int i;

    private String s;

    public <T>T get(Class<T> type) {
        if (type == Integer.class) {
            return (T) new Integer(i);
        } else if (type == String.class) {
            return (T) s;
        }
        return null;
    }
}
class IntIntegerTest {
  public IntIntegerTest(Integer val) {
    System.out.println("behavoiur 1");
  }

  public IntIntegerTest(int val) {
    System.out.println("behavoiur 2");
  }

  public static void f(Integer val) {
    System.out.println("behavoiur 1");
  }

  public static void f(int val) {
    System.out.println("behavoiur 2");
  }

  public IntIntegerTest() {
  }

  public void test() {
    new IntIntegerTest(new Integer(1)); // <-- incorrectly triggered
    f(new Integer(1)); // <-- not triggered
  }
}