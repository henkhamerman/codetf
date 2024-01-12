Refactoring Types: ['Extract Method']
oogle/devtools/j2objc/translate/Autoboxer.java
/*
 * Copyright 2011 Google Inc. All Rights Reserved.
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

package com.google.devtools.j2objc.translate;

import com.google.devtools.j2objc.ast.ArrayAccess;
import com.google.devtools.j2objc.ast.ArrayInitializer;
import com.google.devtools.j2objc.ast.AssertStatement;
import com.google.devtools.j2objc.ast.Assignment;
import com.google.devtools.j2objc.ast.CastExpression;
import com.google.devtools.j2objc.ast.ClassInstanceCreation;
import com.google.devtools.j2objc.ast.ConditionalExpression;
import com.google.devtools.j2objc.ast.ConstructorInvocation;
import com.google.devtools.j2objc.ast.DoStatement;
import com.google.devtools.j2objc.ast.EnumConstantDeclaration;
import com.google.devtools.j2objc.ast.Expression;
import com.google.devtools.j2objc.ast.FunctionInvocation;
import com.google.devtools.j2objc.ast.IfStatement;
import com.google.devtools.j2objc.ast.InfixExpression;
import com.google.devtools.j2objc.ast.MethodInvocation;
import com.google.devtools.j2objc.ast.ParenthesizedExpression;
import com.google.devtools.j2objc.ast.PostfixExpression;
import com.google.devtools.j2objc.ast.PrefixExpression;
import com.google.devtools.j2objc.ast.ReturnStatement;
import com.google.devtools.j2objc.ast.SimpleName;
import com.google.devtools.j2objc.ast.SuperConstructorInvocation;
import com.google.devtools.j2objc.ast.SuperMethodInvocation;
import com.google.devtools.j2objc.ast.SwitchStatement;
import com.google.devtools.j2objc.ast.TreeNode;
import com.google.devtools.j2objc.ast.TreeUtil;
import com.google.devtools.j2objc.ast.TreeVisitor;
import com.google.devtools.j2objc.ast.Type;
import com.google.devtools.j2objc.ast.VariableDeclarationFragment;
import com.google.devtools.j2objc.ast.WhileStatement;
import com.google.devtools.j2objc.types.IOSMethodBinding;
import com.google.devtools.j2objc.util.BindingUtil;
import com.google.devtools.j2objc.util.NameTable;

import org.eclipse.jdt.core.dom.IMethodBinding;
import org.eclipse.jdt.core.dom.ITypeBinding;
import org.eclipse.jdt.core.dom.IVariableBinding;

import java.util.List;

/**
 * Adds support for boxing and unboxing numeric primitive values.
 *
 * @author Tom Ball
 */
public class Autoboxer extends TreeVisitor {

  private static final String VALUE_METHOD = "Value";
  private static final String VALUEOF_METHOD = "valueOf";

  /**
   * Convert a primitive type expression into a wrapped instance.  Each
   * wrapper class has a static valueOf factory method, so "expr" gets
   * translated to "Wrapper.valueOf(expr)".
   */
  private Expression box(Expression expr) {
    ITypeBinding wrapperBinding = typeEnv.getWrapperType(expr.getTypeBinding());
    if (wrapperBinding != null) {
      return newBoxExpression(expr, wrapperBinding);
    } else {
      return expr.copy();
    }
  }

  private Expression boxWithType(Expression expr, ITypeBinding wrapperType) {
    if (typeEnv.isBoxedPrimitive(wrapperType)) {
      return newBoxExpression(expr, wrapperType);
    }
    return box(expr);
  }

  private Expression newBoxExpression(Expression expr, ITypeBinding wrapperType) {
    ITypeBinding primitiveType = typeEnv.getPrimitiveType(wrapperType);
    assert primitiveType != null;
    IMethodBinding wrapperMethod = BindingUtil.findDeclaredMethod(
        wrapperType, VALUEOF_METHOD, primitiveType.getName());
    assert wrapperMethod != null : "could not find valueOf method for " + wrapperType;
    MethodInvocation invocation = new MethodInvocation(wrapperMethod, new SimpleName(wrapperType));
    invocation.getArguments().add(expr.copy());
    return invocation;
  }

  private ITypeBinding findWrapperSuperclass(ITypeBinding type) {
    while (type != null) {
      if (typeEnv.isBoxedPrimitive(type)) {
        return type;
      }
      type = type.getSuperclass();
    }
    return null;
  }

  /**
   * Convert a wrapper class instance to its primitive equivalent.  Each
   * wrapper class has a "classValue()" method, such as intValue() or
   * booleanValue().  This method therefore converts "expr" to
   * "expr.classValue()".
   */
  private Expression unbox(Expression expr) {
    ITypeBinding wrapperType = findWrapperSuperclass(expr.getTypeBinding());
    ITypeBinding primitiveType = typeEnv.getPrimitiveType(wrapperType);
    if (primitiveType != null) {
      IMethodBinding valueMethod = BindingUtil.findDeclaredMethod(
          wrapperType, primitiveType.getName() + VALUE_METHOD);
      assert valueMethod != null : "could not find value method for " + wrapperType;
      return new MethodInvocation(valueMethod, expr.copy());
    } else {
      return expr.copy();
    }
  }

  @Override
  public void endVisit(Assignment node) {
    Expression lhs = node.getLeftHandSide();
    ITypeBinding lhType = lhs.getTypeBinding();
    Expression rhs = node.getRightHandSide();
    ITypeBinding rhType = rhs.getTypeBinding();
    Assignment.Operator op = node.getOperator();
    if (op != Assignment.Operator.ASSIGN && !lhType.isPrimitive()) {
      rewriteBoxedAssignment(node);
    } else if (lhType.isPrimitive() && !rhType.isPrimitive()) {
      node.setRightHandSide(unbox(rhs));
    } else if (!lhType.isPrimitive() && rhType.isPrimitive()) {
      node.setRightHandSide(boxWithType(rhs, lhType));
    }
  }

  private void rewriteBoxedAssignment(Assignment node) {
    Expression lhs = node.getLeftHandSide();
    Expression rhs = node.getRightHandSide();
    ITypeBinding type = lhs.getTypeBinding();
    if (!typeEnv.isBoxedPrimitive(type)) {
      return;
    }
    ITypeBinding primitiveType = typeEnv.getPrimitiveType(type);
    IVariableBinding var = TreeUtil.getVariableBinding(lhs);
    assert var != null : "No variable binding for lhs of assignment.";
    String funcName = "Boxed" + getAssignFunctionName(node.getOperator());
    if (var.isField() && !BindingUtil.isWeakReference(var)) {
      funcName += "Strong";
    }
    funcName += NameTable.capitalize(primitiveType.getName());
    FunctionInvocation invocation = new FunctionInvocation(funcName, type, type, type);
    invocation.getArguments().add(new PrefixExpression(
        typeEnv.getPointerType(type), PrefixExpression.Operator.ADDRESS_OF, TreeUtil.remove(lhs)));
    invocation.getArguments().add(unbox(rhs));
    node.replaceWith(invocation);
  }

  private static String getAssignFunctionName(Assignment.Operator op) {
    switch (op) {
      case PLUS_ASSIGN:
        return "PlusAssign";
      case MINUS_ASSIGN:
        return "MinusAssign";
      case TIMES_ASSIGN:
        return "TimesAssign";
      case DIVIDE_ASSIGN:
        return "DivideAssign";
      case BIT_AND_ASSIGN:
        return "BitAndAssign";
      case BIT_OR_ASSIGN:
        return "BitOrAssign";
      case BIT_XOR_ASSIGN:
        return "BitXorAssign";
      case REMAINDER_ASSIGN:
        return "ModAssign";
      case LEFT_SHIFT_ASSIGN:
        return "LShiftAssign";
      case RIGHT_SHIFT_SIGNED_ASSIGN:
        return "RShiftAssign";
      case RIGHT_SHIFT_UNSIGNED_ASSIGN:
        return "URShiftAssign";
      default:
        throw new IllegalArgumentException();
    }
  }

  @Override
  public void endVisit(ArrayAccess node) {
    Expression index = node.getIndex();
    if (!index.getTypeBinding().isPrimitive()) {
      node.setIndex(unbox(index));
    }
  }

  @Override
  public void endVisit(ArrayInitializer node) {
    ITypeBinding type = node.getTypeBinding().getElementType();
    List<Expression> expressions = node.getExpressions();
    for (int i = 0; i < expressions.size(); i++) {
      Expression expr = expressions.get(i);
      Expression result = boxOrUnboxExpression(expr, type);
      if (expr != result) {
        expressions.set(i, result);
      }
    }
  }

  @Override
  public void endVisit(AssertStatement node) {
    Expression expression = node.getMessage();
    if (expression != null) {
      ITypeBinding exprType = expression.getTypeBinding();
      if (exprType.isPrimitive()) {
        node.setMessage(box(expression));
      }
    }
  }

  @Override
  public void endVisit(CastExpression node) {
    ITypeBinding type = node.getTypeBinding();
    Expression expr = node.getExpression();
    ITypeBinding exprType = expr.getTypeBinding();
    if (type.isPrimitive() && !exprType.isPrimitive()) {
      // Casting an object to a primitive. Convert the cast type to the wrapper
      // so that we do a proper cast check, as Java would.
      type = typeEnv.getWrapperType(type);
      node.setType(Type.newType(type));
    }
    Expression newExpr = boxOrUnboxExpression(expr, type);
    if (newExpr != expr) {
      TreeNode parent = node.getParent();
      if (parent instanceof ParenthesizedExpression) {
        parent.replaceWith(newExpr);
      } else {
        node.replaceWith(newExpr);
      }
    }
  }

  @Override
  public void endVisit(ClassInstanceCreation node) {
    convertArguments(node.getMethodBinding(), node.getArguments());
  }

  @Override
  public void endVisit(ConditionalExpression node) {
    Expression expr = node.getExpression();
    ITypeBinding exprType = expr.getTypeBinding();
    if (!exprType.isPrimitive()) {
      node.setExpression(unbox(expr));
    }

    ITypeBinding nodeType = node.getTypeBinding();
    Expression thenExpr = node.getThenExpression();
    ITypeBinding thenType = thenExpr.getTypeBinding();
    Expression elseExpr = node.getElseExpression();
    ITypeBinding elseType = elseExpr.getTypeBinding();

    if (thenType.isPrimitive() && !nodeType.isPrimitive()) {
      node.setThenExpression(box(thenExpr));
    } else if (!thenType.isPrimitive() && nodeType.isPrimitive()) {
      node.setThenExpression(unbox(thenExpr));
    }

    if (elseType.isPrimitive() && !nodeType.isPrimitive()) {
      node.setElseExpression(box(elseExpr));
    } else if (!elseType.isPrimitive() && nodeType.isPrimitive()) {
      node.setElseExpression(unbox(elseExpr));
    }
  }

  @Override
  public void endVisit(ConstructorInvocation node) {
    convertArguments(node.getMethodBinding(), node.getArguments());
  }

  @Override
  public void endVisit(DoStatement node) {
    Expression expression = node.getExpression();
    ITypeBinding exprType = expression.getTypeBinding();
    if (!exprType.isPrimitive()) {
      node.setExpression(unbox(expression));
    }
  }

  @Override
  public void endVisit(EnumConstantDeclaration node) {
    convertArguments(node.getMethodBinding(), node.getArguments());
  }

  @Override
  public void endVisit(IfStatement node) {
    Expression expr = node.getExpression();
    ITypeBinding binding = expr.getTypeBinding();

    if (!binding.isPrimitive()) {
      node.setExpression(unbox(expr));
    }
  }

  @Override
  public void endVisit(InfixExpression node) {
    ITypeBinding type = node.getTypeBinding();
    InfixExpression.Operator op = node.getOperator();
    List<Expression> operands = node.getOperands();

    // Don't unbox for equality tests where both operands are boxed types.
    if ((op == InfixExpression.Operator.EQUALS || op == InfixExpression.Operator.NOT_EQUALS)
        && !operands.get(0).getTypeBinding().isPrimitive()
        && !operands.get(1).getTypeBinding().isPrimitive()) {
      return;
    }
    // Don't unbox for string concatenation.
    if (op == InfixExpression.Operator.PLUS && typeEnv.isJavaStringType(type)) {
      return;
    }

    for (int i = 0; i < operands.size(); i++) {
      Expression expr = operands.get(i);
      if (!expr.getTypeBinding().isPrimitive()) {
        operands.set(i, unbox(expr));
      }
    }
  }

  @Override
  public void endVisit(MethodInvocation node) {
    convertArguments(node.getMethodBinding(), node.getArguments());
  }

  @Override
  public void endVisit(PrefixExpression node) {
    PrefixExpression.Operator op = node.getOperator();
    Expression operand = node.getOperand();
    if (op == PrefixExpression.Operator.INCREMENT) {
      rewriteBoxedPrefixOrPostfix(node, operand, "BoxedPreIncr");
    } else if (op == PrefixExpression.Operator.DECREMENT) {
      rewriteBoxedPrefixOrPostfix(node, operand, "BoxedPreDecr");
    } else if (!operand.getTypeBinding().isPrimitive()) {
      node.setOperand(unbox(operand));
    }
  }

  @Override
  public void endVisit(PostfixExpression node) {
    PostfixExpression.Operator op = node.getOperator();
    if (op == PostfixExpression.Operator.INCREMENT) {
      rewriteBoxedPrefixOrPostfix(node, node.getOperand(), "BoxedPostIncr");
    } else if (op == PostfixExpression.Operator.DECREMENT) {
      rewriteBoxedPrefixOrPostfix(node, node.getOperand(), "BoxedPostDecr");
    }
  }

  private void rewriteBoxedPrefixOrPostfix(TreeNode node, Expression operand, String funcName) {
    ITypeBinding type = operand.getTypeBinding();
    if (!typeEnv.isBoxedPrimitive(type)) {
      return;
    }
    IVariableBinding var = TreeUtil.getVariableBinding(operand);
    if (var != null) {
      if (var.isField() && !BindingUtil.isWeakReference(var)) {
        funcName += "Strong";
      }
    } else {
      assert TreeUtil.trimParentheses(operand) instanceof ArrayAccess
          : "Operand cannot be resolved to a variable or array access.";
      funcName += "Array";
    }
    funcName += NameTable.capitalize(typeEnv.getPrimitiveType(type).getName());
    FunctionInvocation invocation = new FunctionInvocation(funcName, type, type, type);
    invocation.getArguments().add(new PrefixExpression(
        typeEnv.getPointerType(type), PrefixExpression.Operator.ADDRESS_OF,
        TreeUtil.remove(operand)));
    node.replaceWith(invocation);
  }

  @Override
  public void endVisit(ReturnStatement node) {
    Expression expr = node.getExpression();
    if (expr != null) {
      IMethodBinding methodBinding = TreeUtil.getOwningMethodBinding(node);
      ITypeBinding returnType = methodBinding.getReturnType();
      ITypeBinding exprType = expr.getTypeBinding();
      if (returnType.isPrimitive() && !exprType.isPrimitive()) {
        node.setExpression(unbox(expr));
      }
      if (!returnType.isPrimitive() && exprType.isPrimitive()) {
        node.setExpression(box(expr));
      }
    }
  }

  @Override
  public void endVisit(SuperConstructorInvocation node) {
    convertArguments(node.getMethodBinding(), node.getArguments());
  }

  @Override
  public void endVisit(SuperMethodInvocation node) {
    convertArguments(node.getMethodBinding(), node.getArguments());
  }

  @Override
  public void endVisit(VariableDeclarationFragment node) {
    Expression initializer = node.getInitializer();
    if (initializer != null) {
      ITypeBinding nodeType = node.getVariableBinding().getType();
      ITypeBinding initType = initializer.getTypeBinding();
      if (nodeType.isPrimitive() && !initType.isPrimitive()) {
        node.setInitializer(unbox(initializer));
      } else if (!nodeType.isPrimitive() && initType.isPrimitive()) {
        node.setInitializer(boxWithType(initializer, nodeType));
      }
    }
  }

  @Override
  public void endVisit(WhileStatement node) {
    Expression expression = node.getExpression();
    ITypeBinding exprType = expression.getTypeBinding();
    if (!exprType.isPrimitive()) {
      node.setExpression(unbox(expression));
    }
  }

  @Override
  public void endVisit(SwitchStatement node) {
    Expression expression = node.getExpression();
    ITypeBinding exprType = expression.getTypeBinding();
    if (!exprType.isPrimitive()) {
      node.setExpression(unbox(expression));
    }
  }

  private void convertArguments(IMethodBinding methodBinding, List<Expression> args) {
    if (methodBinding instanceof IOSMethodBinding) {
      return; // already converted
    }
    ITypeBinding[] paramTypes = methodBinding.getParameterTypes();
    for (int i = 0; i < args.size(); i++) {
      ITypeBinding paramType;
      if (methodBinding.isVarargs() && i >= paramTypes.length - 1) {
        paramType = paramTypes[paramTypes.length - 1].getComponentType();
      } else {
        paramType = paramTypes[i];
      }
      Expression arg = args.get(i);
      Expression replacementArg = boxOrUnboxExpression(arg, paramType);
      if (replacementArg != arg) {
        args.set(i, replacementArg);
      }
    }
  }

  private Expression boxOrUnboxExpression(Expression arg, ITypeBinding argType) {
    ITypeBinding argBinding = arg.getTypeBinding();
    if (argType.isPrimitive() && !argBinding.isPrimitive()) {
      return unbox(arg);
    } else if (!argType.isPrimitive() && argBinding.isPrimitive()) {
      return box(arg);
    } else {
      return arg;
    }
  }
}


File: translator/src/test/java/com/google/devtools/j2objc/translate/AutoboxerTest.java
/*
 * Copyright 2011 Google Inc. All Rights Reserved.
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

package com.google.devtools.j2objc.translate;

import com.google.devtools.j2objc.GenerationTest;
import com.google.devtools.j2objc.ast.Statement;

import java.io.IOException;
import java.util.List;

/**
 * Unit tests for {@link Autoboxer} class.
 *
 * @author Tom Ball
 */
public class AutoboxerTest extends GenerationTest {

  public void testDoNotBoxIntInVarargMethod() throws IOException {
    String source = "public class Test { Test(String s) {} "
        + "int one(String s, int i) { return two(new Test(s), i, 1, 2); }"
        + "int two(Test t, int i, Integer ... args) { return 0; } }";
    String translation = translateSourceFile(source, "Test", "Test.m");

    // i should not be boxed since its argument is explicitly declared,
    // but 1 and 2 should be because they are passed as varargs.
    assertTranslation(translation, "twoWithTest:[new_Test_initWithNSString_(s) autorelease] "
        + "withInt:i withJavaLangIntegerArray:"
        + "[IOSObjectArray arrayWithObjects:(id[]){ JavaLangInteger_valueOfWithInt_(1), "
        + "JavaLangInteger_valueOfWithInt_(2) } count:2 type:JavaLangInteger_class_()]];");
  }

  public void testUnboxReturn() throws IOException {
    String source = "public class Test { Integer value; int intValue() { return value; }}";
    String translation = translateSourceFile(source, "Test", "Test.m");
    assertTranslation(translation, "return [((JavaLangInteger *) nil_chk(value_)) intValue];");
  }

  public void testBooleanAssignment() throws IOException {
    String source = "boolean b = true; Boolean foo = Boolean.FALSE; b = foo;";
    List<Statement> stmts = translateStatements(source);
    String result = generateStatement(stmts.get(2));
    assertEquals("b = [((JavaLangBoolean *) nil_chk(foo)) booleanValue];", result);

    source = "boolean b = true; Boolean foo = Boolean.FALSE; foo = b;";
    stmts = translateStatements(source);
    result = generateStatement(stmts.get(2));
    assertEquals("foo = JavaLangBoolean_valueOfWithBoolean_(b);", result);
  }

  public void testByteAssignment() throws IOException {
    String source = "byte b = 5; Byte foo = Byte.valueOf((byte) 3); b = foo;";
    List<Statement> stmts = translateStatements(source);
    String result = generateStatement(stmts.get(2));
    assertEquals("b = [foo charValue];", result);

    source = "byte b = 5; Byte foo = Byte.valueOf((byte) 3); foo = b;";
    stmts = translateStatements(source);
    result = generateStatement(stmts.get(2));
    assertEquals("foo = JavaLangByte_valueOfWithByte_(b);", result);
  }

  public void testCharAssignment() throws IOException {
    String source = "char c = 'a'; Character foo = Character.valueOf('b'); c = foo;";
    List<Statement> stmts = translateStatements(source);
    String result = generateStatement(stmts.get(2));
    assertEquals("c = [foo charValue];", result);

    source = "char c = 'a'; Character foo = Character.valueOf('b'); foo = c;";
    stmts = translateStatements(source);
    result = generateStatement(stmts.get(2));
    assertEquals("foo = JavaLangCharacter_valueOfWithChar_(c);", result);
  }

  public void testShortAssignment() throws IOException {
    String source = "short s = 5; Short foo = Short.valueOf((short) 3); s = foo;";
    List<Statement> stmts = translateStatements(source);
    String result = generateStatement(stmts.get(2));
    assertEquals("s = [foo shortValue];", result);

    source = "short s = 5; Short foo = Short.valueOf((short) 3); foo = s;";
    stmts = translateStatements(source);
    result = generateStatement(stmts.get(2));
    assertEquals("foo = JavaLangShort_valueOfWithShort_(s);", result);
  }

  public void testIntAssignment() throws IOException {
    String source = "int i = 5; Integer foo = Integer.valueOf(3); i = foo;";
    List<Statement> stmts = translateStatements(source);
    String result = generateStatement(stmts.get(2));
    assertEquals("i = [foo intValue];", result);

    source = "int i = 5; Integer foo = Integer.valueOf(3); foo = i;";
    stmts = translateStatements(source);
    result = generateStatement(stmts.get(2));
    assertEquals("foo = JavaLangInteger_valueOfWithInt_(i);", result);
  }

  public void testLongAssignment() throws IOException {
    String source = "long l = 5; Long foo = Long.valueOf(3L); l = foo;";
    List<Statement> stmts = translateStatements(source);
    String result = generateStatement(stmts.get(2));
    assertEquals("l = [foo longLongValue];", result);

    source = "long l = 5; Long foo = Long.valueOf(3L); foo = l;";
    stmts = translateStatements(source);
    result = generateStatement(stmts.get(2));
    assertEquals("foo = JavaLangLong_valueOfWithLong_(l);", result);
  }

  public void testFloatAssignment() throws IOException {
    String source = "float f = 5.0f; Float foo = Float.valueOf(3.0f); f = foo;";
    List<Statement> stmts = translateStatements(source);
    String result = generateStatement(stmts.get(2));
    assertEquals("f = [foo floatValue];", result);

    source = "float f = 5.0f; Float foo = Float.valueOf(3.0f); foo = f;";
    stmts = translateStatements(source);
    result = generateStatement(stmts.get(2));
    assertEquals("foo = JavaLangFloat_valueOfWithFloat_(f);", result);
  }

  public void testDoubleAssignment() throws IOException {
    String source = "double d = 5.0; Double foo = Double.valueOf(3.0); d = foo;";
    List<Statement> stmts = translateStatements(source);
    String result = generateStatement(stmts.get(2));
    assertEquals("d = [foo doubleValue];", result);

    source = "double d = 5.0; Double foo = Double.valueOf(3.0); foo = d;";
    stmts = translateStatements(source);
    result = generateStatement(stmts.get(2));
    assertEquals("foo = JavaLangDouble_valueOfWithDouble_(d);", result);
  }

  public void testInfixLeftOperand() throws IOException {
    String source = "Integer test = new Integer(5); int result = test + 3;";
    List<Statement> stmts = translateStatements(source);
    String result = generateStatement(stmts.get(1));
    assertEquals("jint result = [test intValue] + 3;", result);
  }

  public void testInfixRightOperand() throws IOException {
    String source = "Integer test = new Integer(5); int result = 3 + test;";
    List<Statement> stmts = translateStatements(source);
    String result = generateStatement(stmts.get(1));
    assertEquals("jint result = 3 + [test intValue];", result);
  }

  public void testInfixBothOperands() throws IOException {
    String source = "Integer foo = new Integer(5); Integer bar = new Integer(3);"
        + "int result = foo + bar;";
    List<Statement> stmts = translateStatements(source);
    String result = generateStatement(stmts.get(2));
    assertEquals("jint result = [foo intValue] + [bar intValue];", result);
  }

  public void testInfixNeitherOperand() throws IOException {
    // Make sure primitive expressions aren't modified.
    String source = "int result = 3 + 5;";
    List<Statement> stmts = translateStatements(source);
    String result = generateStatement(stmts.get(0));
    assertEquals("jint result = 3 + 5;", result);
  }

  public void testVariableDeclaration() throws IOException {
    String source = "Integer test = 3;";
    List<Statement> stmts = translateStatements(source);
    String result = generateStatement(stmts.get(0));
    assertEquals("JavaLangInteger *test = JavaLangInteger_valueOfWithInt_(3);", result);
  }

  public void testMethodArgs() throws IOException {
    String source = "public class Test { void foo(Integer i) {} "
        + "void test() { int i = 3; foo(i); }}";
    String translation = translateSourceFile(source, "Test", "Test.m");
    assertTranslation(translation,
        "[self fooWithJavaLangInteger:JavaLangInteger_valueOfWithInt_(i)];");
  }

  public void testConditionalExpression() throws IOException {
    String translation = translateSourceFile(
        "public class Test { "
        + "void test() { Boolean b = true ? false : null; } }",
        "Test", "Test.m");
    assertTranslation(translation, "JavaLangBoolean_valueOfWithBoolean_(NO)");
  }

  public void testReturnWithConditional() throws IOException {
    String translation = translateSourceFile(
        "public class Test { "
        + "boolean test() { Boolean b = null; return b != null ? b : false; } }",
        "Test", "Test.m");
    assertTranslation(translation, "b != nil ? [b booleanValue] : NO");
  }

  public void testConditionalOnBoxedValue() throws IOException {
    String translation = translateSourceFile(
        "public class Test { int test(Boolean b) { return b ? 1 : 2; } }", "Test", "Test.m");
    assertTranslation(translation,
        "return [((JavaLangBoolean *) nil_chk(b)) booleanValue] ? 1 : 2;");
  }

  public void testArrayInitializerNotBoxed() throws IOException {
    // Verify that an array with an initializer that has elements of the same
    // type isn't boxed.
    String translation = translateSourceFile(
        "public class Test { public int values[] = new int[] { 1, 2, 3 }; }",
        "Test", "Test.m");
    assertTranslation(translation, "[IOSIntArray newArrayWithInts:(jint[]){ 1, 2, 3 } count:3]");
    translation = translateSourceFile(
        "public class Test { private Integer i = 1; private Integer j = 2; private Integer k = 3;"
        + "  public Integer values[] = new Integer[] { i, j, k }; }",
        "Test", "Test.m");
    assertTranslation(translation,
        "[IOSObjectArray newArrayWithObjects:(id[]){ self->i_, self->j_, self->k_ } count:3 "
        + "type:JavaLangInteger_class_()]");
  }

  public void testArrayInitializerBoxed() throws IOException {
    // Verify that an Integer array with an initializer that has int elements
    // is boxed.
    String translation = translateSourceFile(
        "public class Test { private Integer i = 1; "
        + "  public void test() { Integer values[] = new Integer[] { 1, 2, i }; }}",
        "Test", "Test.m");
    assertTranslation(translation,
        "[IOSObjectArray arrayWithObjects:(id[]){ JavaLangInteger_valueOfWithInt_(1), "
        + "JavaLangInteger_valueOfWithInt_(2), i_ } count:3 type:JavaLangInteger_class_()]");
  }

  public void testArrayInitializerUnboxed() throws IOException {
    // Verify that an int array with an initializer that has Integer elements
    // is unboxed.
    String translation = translateSourceFile(
        "public class Test { private Integer i = 1; private Integer j = 2;"
        + "  public void test() { int values[] = new int[] { i, j, 3 }; }}",
        "Test", "Test.m");
    assertTranslation(translation,
        "[IOSIntArray arrayWithInts:(jint[]){ [((JavaLangInteger *) nil_chk(i_)) intValue], "
        + "[((JavaLangInteger *) nil_chk(j_)) intValue], 3 } count:3]");
  }

  public void testFieldArrayInitializerBoxed() throws IOException {
    // Verify that an Integer array with an initializer that has int elements
    // is boxed.
    String translation = translateSourceFile(
        "public class Test { private Integer i = 1; "
        + "  public Integer values[] = new Integer[] { 1, 2, i }; }",
        "Test", "Test.m");
    assertTranslation(translation,
        "[IOSObjectArray newArrayWithObjects:(id[]){ JavaLangInteger_valueOfWithInt_(1), "
        + "JavaLangInteger_valueOfWithInt_(2), self->i_ } count:3 type:JavaLangInteger_class_()]");
  }

  public void testFieldArrayInitializerUnboxed() throws IOException {
    // Verify that an int array with an initializer that has Integer elements
    // is unboxed.
    String translation = translateSourceFile(
        "public class Test { private Integer i = 1; private Integer j = 2;"
        + "  public int values[] = new int[] { i, j, 3 }; }",
        "Test", "Test.m");
    assertTranslation(translation,
        "[IOSIntArray newArrayWithInts:(jint[]){ "
        + "[self->i_ intValue], [self->j_ intValue], 3 } count:3]");
  }

  public void testBoxedTypeLiteral() throws IOException {
    String source = "public class Test { Class c = int.class; }";
    String translation = translateSourceFile(source, "Test", "Test.m");
    assertTranslation(translation, "Test_set_c_(self, [IOSClass intClass]);");
  }

  public void testBoxedLhsOperatorAssignment() throws IOException {
    String source = "public class Test { Integer i = 1; void foo() { i *= 2; } }";
    String translation = translateSourceFile(source, "Test", "Test.m");
    assertTranslation(translation, "BoxedTimesAssignStrongInt(&i_, 2);");
  }

  public void testBoxedEnumConstructorArgs() throws IOException {
    String source = "public enum Test { INT(0), BOOLEAN(false); Test(Object o) {}}";
    String translation = translateSourceFile(source, "Test", "Test.m");

    assertTranslation(translation,
        "new_TestEnum_initWithId_withNSString_withInt_("
        + "JavaLangInteger_valueOfWithInt_(0), @\"INT\", 0)");
    assertTranslation(translation,
        "new_TestEnum_initWithId_withNSString_withInt_("
        + "JavaLangBoolean_valueOfWithBoolean_(NO), @\"BOOLEAN\", 1)");
  }

  public void testBoxedBoolInIf() throws IOException {
    String source = "public class Test { Boolean b = false; void foo() { if (b) foo(); } }";
    String translation = translateSourceFile(source, "Test", "Test.m");

    assertTranslation(translation, "if ([((JavaLangBoolean *) nil_chk(b_)) booleanValue])");
  }

  public void testBoxedBoolInWhile() throws IOException {
    String source = "public class Test { Boolean b = false; void foo() { while (b) foo(); } }";
    String translation = translateSourceFile(source, "Test", "Test.m");

    assertTranslation(translation, "while ([((JavaLangBoolean *) nil_chk(b_)) booleanValue])");
  }

  public void testBoxedBoolInDoWhile() throws IOException {
    String source = "public class Test { "
        + "  Boolean b = false; void foo() { do { foo(); } while (b); } }";
    String translation = translateSourceFile(source, "Test", "Test.m");

    assertTranslation(translation, "while ([((JavaLangBoolean *) nil_chk(b_)) booleanValue])");
  }

  public void testBoxedBoolNegatedInWhile() throws IOException {
    String source = "public class Test { Boolean b = false; void foo() { while (!b) foo(); } }";
    String translation = translateSourceFile(source, "Test", "Test.m");

    assertTranslation(translation, "while (![((JavaLangBoolean *) nil_chk(b_)) booleanValue])");
  }

  public void testAutoboxCast() throws IOException {
    String source = "public class Test { double doubleValue; "
        + "public int hashCode() { return ((Double) doubleValue).hashCode(); } }";
    String translation = translateSourceFile(source, "Test", "Test.m");

    assertTranslation(translation, "[JavaLangDouble_valueOfWithDouble_(doubleValue_) hash]");
  }

  public void testAutoboxArrayIndex() throws IOException {
    String source =
        "public class Test { "
        + "  Integer index() { return 1; }"
        + "  void test() {"
        + "    int[] array = new int[3];"
        + "    array[index()] = 2; }}";
    String translation = translateSourceFile(source, "Test", "Test.m");
    assertTranslation(translation,
        "*IOSIntArray_GetRef(array, [((JavaLangInteger *) nil_chk([self index])) intValue]) = 2;");
  }

  public void testPrefixExpression() throws IOException {
    String source =
        "public class Test { void test() { "
        + "  Integer iMinutes = new Integer(1); "
        + "  Double iSeconds = new Double(0);"
        + "  iMinutes = -iMinutes; iSeconds = -iSeconds; }}";
    String translation = translateSourceFile(source, "Test", "Test.m");
    assertTranslation(translation,
        "iMinutes = JavaLangInteger_valueOfWithInt_(-[iMinutes intValue]);");
    assertTranslation(translation,
        "iSeconds = JavaLangDouble_valueOfWithDouble_(-[iSeconds doubleValue]);");
  }

  public void testStringConcatenation() throws IOException {
    String translation = translateSourceFile(
        "class Test { void test() { Boolean b = Boolean.TRUE; Integer i = new Integer(3); "
        + "String s = b + \"foo\" + i; } }", "Test", "Test.m");
    assertTranslation(translation, "NSString *s = JreStrcat(\"@$@\", b, @\"foo\", i)");
  }

  public void testExtendedOperandsAreUnboxed() throws IOException {
    String translation = translateSourceFile(
        "class Test { void test() { Integer i1 = new Integer(2); Integer i2 = new Integer(3); "
        + "int i3 = 1 + 2 + i1 + i2; } }", "Test", "Test.m");
    assertTranslation(translation, "int i3 = 1 + 2 + [i1 intValue] + [i2 intValue]");
  }

  public void testUnboxOfSwitchStatementExpression() throws IOException {
    String translation = translateSourceFile(
        "class Test { void test() {"
        + " Integer i = 3;"
        + " switch (i) { case 1: case 2: case 3: } } }", "Test", "Test.m");
    assertTranslation(translation, "switch ([i intValue]) {");
  }

  public void testInvokeSuperMethodAutoboxing() throws IOException {
    String translation = translateSourceFile("class Base { "
        + "public void print(Object o) { System.out.println(o); }}"
        + "public class Test extends Base {"
        + "@Override public void print(Object o) { super.print(123.456f); }}", "Test", "Test.m");
    assertTranslation(translation,
        "[super printWithId:JavaLangFloat_valueOfWithFloat_(123.456f)];");
  }

  public void testAssignIntLiteralToNonIntBoxedType() throws Exception {
    String translation = translateSourceFile(
        "class Test { void test() { Byte b = 3; Short s; s = 4; } }", "Test", "Test.m");
    assertTranslation(translation, "JavaLangByte *b = JavaLangByte_valueOfWithByte_(3);");
    assertTranslation(translation, "s = JavaLangShort_valueOfWithShort_(4);");
  }

  public void testBoxedIncrementAndDecrement() throws Exception {
    String translation = translateSourceFile(
        "class Test { void test() { Integer i = 1; i++; Byte b = 2; b--; Character c = 'a'; ++c; "
        + "Double d = 3.0; --d; } }", "Test", "Test.m");
    assertTranslation(translation, "PostIncrInt(&i);");
    assertTranslation(translation, "PostDecrByte(&b);");
    assertTranslation(translation, "PreIncrChar(&c);");
    assertTranslation(translation, "PreDecrDouble(&d);");
  }

  // Verify that passing a new Double to a method that takes a double is unboxed.
  public void testUnboxedDoubleParameter() throws Exception {
    String translation = translateSourceFile(
        "class Test { void takesDouble(double d) {} void test() { takesDouble(new Double(1.2)); }}",
        "Test", "Test.m");
    assertTranslation(translation,
        "[self takesDoubleWithDouble:[((JavaLangDouble *) [new_JavaLangDouble_initWithDouble_(1.2) "
        + "autorelease]) doubleValue]];");
  }

  public void testWildcardBoxType() throws IOException {
    String translation = translateSourceFile(
        "class Test { interface Entry<T> { T getValue(); } "
        + "void test(Entry<? extends Long> entry) { long l = entry.getValue(); } }",
        "Test", "Test.m");
    assertTranslation(translation,
        "jlong l = [((JavaLangLong *) nil_chk([((id<Test_Entry>) nil_chk(entry_)) "
        + "getValue])) longLongValue];");
  }

  public void testAssignmentWithCase() throws IOException {
    String translation = translateSourceFile(
        "class Test { void test() { Integer i; i = (Integer) 12; } }", "Test", "Test.m");
    assertTranslation(translation, "i = JavaLangInteger_valueOfWithInt_(12);");
  }

  public void testAssertMessage() throws IOException {
    String translation = translateSourceFile(
        "class Test { void test(int i) { assert i == 0 : i; }}", "Test", "Test.m");
    assertTranslation(translation,
        "NSAssert(i == 0, [JavaLangInteger_valueOfWithInt_(i) description]);");
  }

  public void testNonWrapperObjectTypeCastToPrimitive() throws IOException {
    String translation = translateSourceFile(
        "class Test { int test(Object o) { return (int) o; } "
        + "int test2(Integer i) { return (int) i; } }", "Test", "Test.m");
    assertTranslation(translation,
        "return [((JavaLangInteger *) nil_chk((JavaLangInteger *) "
        + "check_class_cast(o, [JavaLangInteger class]))) intValue];");
    // Make sure we don't unnecessarily add a cast check if the object type
    // matches the primitive cast type.
    assertTranslation(translation,
        "return [((JavaLangInteger *) nil_chk(i)) intValue];");
  }

  public void testBoxedOperators() throws IOException {
    // TODO(kstanger): Fix compound assign on array access.
    String translation = translateSourceFile(
        "class Test { Integer si; Long sl; Float sf; Double sd;"
        + " Integer[] ai; Long[] al; Float[] af; Double ad;"
        + " void test(Integer wi, Long wl, Float wf, Double wd) {"
        + " si++; wi++; ++sl; ++wl; sf--; wf--; --sd; --wd;"
        + " si += 5; wi += 5; sl &= 6l; wl &= 6l;"
        + " si <<= 2; wi <<= 2; sl >>>= 3; wl >>>= 3;"
        + " ai[0]++; --al[1]; } }", "Test", "Test.m");
    assertTranslatedLines(translation,
        "BoxedPostIncrStrongInt(&si_);",
        "BoxedPostIncrInt(&wi);",
        "BoxedPreIncrStrongLong(&sl_);",
        "BoxedPreIncrLong(&wl);",
        "BoxedPostDecrStrongFloat(&sf_);",
        "BoxedPostDecrFloat(&wf);",
        "BoxedPreDecrStrongDouble(&sd_);",
        "BoxedPreDecrDouble(&wd);",
        "BoxedPlusAssignStrongInt(&si_, 5);",
        "BoxedPlusAssignInt(&wi, 5);",
        "BoxedBitAndAssignStrongLong(&sl_, 6l);",
        "BoxedBitAndAssignLong(&wl, 6l);",
        "BoxedLShiftAssignStrongInt(&si_, 2);",
        "BoxedLShiftAssignInt(&wi, 2);",
        "BoxedURShiftAssignStrongLong(&sl_, 3);",
        "BoxedURShiftAssignLong(&wl, 3);",
        "BoxedPostIncrArrayInt(IOSObjectArray_GetRef(nil_chk(ai_), 0));",
        "BoxedPreDecrArrayLong(IOSObjectArray_GetRef(nil_chk(al_), 1));");
  }
}
