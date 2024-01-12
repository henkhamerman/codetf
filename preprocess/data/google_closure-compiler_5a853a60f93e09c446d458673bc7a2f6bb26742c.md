Refactoring Types: ['Move Class']
jscomp/JsdocToEs6TypedConverter.java
/*
 * Copyright 2015 The Closure Compiler Authors.
 *
 * Licensed under the Apache License, Version 2.0 (the "License");
 * you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at
 *
 *     http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 */

package com.google.javascript.jscomp;

import static com.google.javascript.jscomp.parsing.TypeDeclarationsIRFactory.convert;

import com.google.javascript.jscomp.NodeTraversal.AbstractPostOrderCallback;
import com.google.javascript.rhino.JSDocInfo;
import com.google.javascript.rhino.JSTypeExpression;
import com.google.javascript.rhino.Node;
import com.google.javascript.rhino.Node.TypeDeclarationNode;
import com.google.javascript.rhino.Token;

/**
 * Converts JS with types in jsdocs to an extended JS syntax that includes types.
 * (Still keeps the jsdocs intact.)
 *
 * @author alexeagle@google.com (Alex Eagle)
 *
 * TODO(alexeagle): handle inline-style JSDoc annotations as well.
 */
public final class JsdocToEs6TypedConverter
    extends AbstractPostOrderCallback implements CompilerPass {

  private final AbstractCompiler compiler;

  public JsdocToEs6TypedConverter(AbstractCompiler compiler) {
    this.compiler = compiler;
  }

  @Override
  public void process(Node externs, Node root) {
    NodeTraversal.traverse(compiler, root, this);
  }

  @Override
  public void visit(NodeTraversal t, Node n, Node parent) {
    JSDocInfo bestJSDocInfo = NodeUtil.getBestJSDocInfo(n);
    switch (n.getType()) {
      case Token.FUNCTION:
        if (bestJSDocInfo != null) {
          setTypeExpression(n, bestJSDocInfo.getReturnType());
        }
        break;
      case Token.NAME:
      case Token.GETPROP:
        if (parent == null) {
          break;
        }
        if (parent.isVar() || parent.isAssign() || parent.isExprResult()) {
          if (bestJSDocInfo != null) {
            setTypeExpression(n, bestJSDocInfo.getType());
          }
        } else if (parent.isParamList()) {
          JSDocInfo parentDocInfo = NodeUtil.getBestJSDocInfo(parent);
          if (parentDocInfo == null) {
            break;
          }
          JSTypeExpression parameterType =
              parentDocInfo.getParameterType(n.getString());
          if (parameterType != null) {
            Node attachTypeExpr = n;
            // Modify the primary AST to represent a function parameter as a
            // REST node, if the type indicates it is a rest parameter.
            if (parameterType.getRoot().getType() == Token.ELLIPSIS) {
              attachTypeExpr = Node.newString(Token.REST, n.getString());
              n.getParent().replaceChild(n, attachTypeExpr);
              compiler.reportCodeChange();
            }
            setTypeExpression(attachTypeExpr, parameterType);
          }
        }
        break;
      default:
        break;
    }
  }

  private void setTypeExpression(Node n, JSTypeExpression type) {
    TypeDeclarationNode node = convert(type);
    if (node != null) {
      n.setDeclaredTypeExpression(node);
      compiler.reportCodeChange();
    }
  }
}


File: src/com/google/javascript/jscomp/parsing/TypeDeclarationsIRFactory.java
/*
 * Copyright 2015 The Closure Compiler Authors.
 *
 * Licensed under the Apache License, Version 2.0 (the "License");
 * you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at
 *
 *     http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 */

package com.google.javascript.jscomp.parsing;


import static com.google.javascript.rhino.TypeDeclarationsIR.anyType;
import static com.google.javascript.rhino.TypeDeclarationsIR.arrayType;
import static com.google.javascript.rhino.TypeDeclarationsIR.booleanType;
import static com.google.javascript.rhino.TypeDeclarationsIR.functionType;
import static com.google.javascript.rhino.TypeDeclarationsIR.namedType;
import static com.google.javascript.rhino.TypeDeclarationsIR.numberType;
import static com.google.javascript.rhino.TypeDeclarationsIR.optionalParameter;
import static com.google.javascript.rhino.TypeDeclarationsIR.parameterizedType;
import static com.google.javascript.rhino.TypeDeclarationsIR.recordType;
import static com.google.javascript.rhino.TypeDeclarationsIR.stringType;
import static com.google.javascript.rhino.TypeDeclarationsIR.undefinedType;
import static com.google.javascript.rhino.TypeDeclarationsIR.unionType;

import com.google.common.base.Function;
import com.google.common.base.Predicates;
import com.google.common.collect.FluentIterable;
import com.google.common.collect.ImmutableList;
import com.google.common.collect.Iterables;
import com.google.javascript.rhino.JSTypeExpression;
import com.google.javascript.rhino.Node;
import com.google.javascript.rhino.Node.TypeDeclarationNode;
import com.google.javascript.rhino.Token;

import java.util.LinkedHashMap;

import javax.annotation.Nullable;

/**
 * Converts root nodes of JSTypeExpressions into TypeDeclaration ASTs.
 *
 * @author alexeagle@google.com (Alex Eagle)
 */
public final class TypeDeclarationsIRFactory {

  // Allow functional-style Iterables.transform over collections of nodes.
  private static final Function<Node, TypeDeclarationNode> CONVERT_TYPE_NODE =
      new Function<Node, TypeDeclarationNode>() {
        @Override
        public TypeDeclarationNode apply(Node node) {
          return convertTypeNodeAST(node);
        }
      };

  @Nullable
  public static TypeDeclarationNode convert(@Nullable JSTypeExpression typeExpr) {
    if (typeExpr == null) {
      return null;
    }
    return convertTypeNodeAST(typeExpr.getRoot());
  }

  /**
   * The root of a JSTypeExpression is very different from an AST node, even
   * though we use the same Java class to represent them.
   * This function converts root nodes of JSTypeExpressions into TypeDeclaration ASTs,
   * to make them more similar to ordinary AST nodes.
   *
   * @return the root node of a TypeDeclaration AST, or null if no type is
   *         available for the node.
   */
  // TODO(dimvar): Eventually, we want to just parse types to the new
  // representation directly, and delete this function.
  @Nullable
  public static TypeDeclarationNode convertTypeNodeAST(Node n) {
    int token = n.getType();
    switch (token) {
      case Token.STAR:
      case Token.EMPTY: // for function types that don't declare a return type
        return anyType();
      case Token.VOID:
        return undefinedType();
      case Token.BANG:
        // TODO(alexeagle): non-nullable is assumed to be the default
        return convertTypeNodeAST(n.getFirstChild());
      case Token.STRING:
        String typeName = n.getString();
        switch (typeName) {
          case "boolean":
            return booleanType();
          case "number":
            return numberType();
          case "string":
            return stringType();
          case "null":
          case "undefined":
          case "void":
            return null;
          default:
            TypeDeclarationNode root = namedType(typeName);
            if (n.getChildCount() > 0 && n.getFirstChild().isBlock()) {
              Node block = n.getFirstChild();
              if ("Array".equals(typeName)) {
                return arrayType(convertTypeNodeAST(block.getFirstChild()));
              }
              return parameterizedType(root,
                  Iterables.filter(
                      Iterables.transform(block.children(), CONVERT_TYPE_NODE),
                      Predicates.notNull()));
            }
            return root;
        }
      case Token.QMARK:
        Node child = n.getFirstChild();
        return child == null
            ? anyType()
            // For now, our ES6_TYPED language doesn't support nullable
            // so we drop it before building the tree.
            // : nullable(convertTypeNodeAST(child));
            : convertTypeNodeAST(child);
      case Token.LC:
        LinkedHashMap<String, TypeDeclarationNode> properties = new LinkedHashMap<>();
        for (Node field : n.getFirstChild().children()) {
          boolean isFieldTypeDeclared = field.getType() == Token.COLON;
          Node fieldNameNode = isFieldTypeDeclared ? field.getFirstChild() : field;
          String fieldName = fieldNameNode.getString();
          if (fieldName.startsWith("'") || fieldName.startsWith("\"")) {
            fieldName = fieldName.substring(1, fieldName.length() - 1);
          }
          TypeDeclarationNode fieldType = isFieldTypeDeclared
              ? convertTypeNodeAST(field.getLastChild()) : null;
          properties.put(fieldName, fieldType);
        }
        return recordType(properties);
      case Token.ELLIPSIS:
        return arrayType(convertTypeNodeAST(n.getFirstChild()));
      case Token.PIPE:
        ImmutableList<TypeDeclarationNode> types = FluentIterable
            .from(n.children()).transform(CONVERT_TYPE_NODE)
            .filter(Predicates.notNull()).toList();
        switch (types.size()) {
          case 0:
            return null;
          case 1:
            return types.get(0);
          default:
            return unionType(types);
        }
      case Token.FUNCTION:
        Node returnType = anyType();
        LinkedHashMap<String, TypeDeclarationNode> requiredParams = new LinkedHashMap<>();
        LinkedHashMap<String, TypeDeclarationNode> optionalParams = new LinkedHashMap<>();
        String restName = null;
        TypeDeclarationNode restType = null;
        for (Node child2 : n.children()) {
          if (child2.isParamList()) {
            int paramIdx = 1;
            for (Node param : child2.children()) {
              String paramName = "p" + paramIdx++;
              if (param.getType() == Token.ELLIPSIS) {
                if (param.getFirstChild() != null) {
                  restType = arrayType(convertTypeNodeAST(param.getFirstChild()));
                }
                restName = paramName;
              } else {
                TypeDeclarationNode paramNode = convertTypeNodeAST(param);
                if (paramNode.getType() == Token.OPTIONAL_PARAMETER) {
                  optionalParams.put(paramName,
                      (TypeDeclarationNode) paramNode.removeFirstChild());
                } else {
                  requiredParams.put(paramName, convertTypeNodeAST(param));
                }
              }
            }
          } else if (child2.isNew()) {
            // TODO(alexeagle): keep the constructor signatures on the tree, and emit them following
            // the syntax in TypeScript 1.4 spec, section 3.7.8 Constructor Type Literals
          } else if (child2.isThis()) {
            // Not expressible in TypeScript syntax, so we omit them from the tree.
            // They could be added as properties on the result node.
          } else {
            returnType = convertTypeNodeAST(child2);
          }
        }
        return functionType(returnType, requiredParams, optionalParams, restName, restType);
      case Token.EQUALS:
        TypeDeclarationNode optionalParam = convertTypeNodeAST(n.getFirstChild());
        return optionalParam == null ? null : optionalParameter(optionalParam);
      default:
        throw new IllegalArgumentException(
            "Unsupported node type: " + Token.name(n.getType())
                + " " + n.toStringTree());
    }
  }
}


File: test/com/google/javascript/jscomp/JsdocToEs6TypedConverterTest.java
/*
 * Copyright 2015 The Closure Compiler Authors.
 *
 * Licensed under the Apache License, Version 2.0 (the "License");
 * you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at
 *
 *     http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 */

package com.google.javascript.jscomp;

import com.google.javascript.jscomp.CompilerOptions.LanguageMode;

/**
 * Tests the conversion of closure-style type declarations in JSDoc
 * to inline type declarations, by running both syntaxes through the parser
 * and verifying the resulting AST is the same.
 */
public final class JsdocToEs6TypedConverterTest extends CompilerTestCase {

  @Override
  public void setUp() {
    setAcceptedLanguage(LanguageMode.ECMASCRIPT6_TYPED);
    enableAstValidation(true);
    compareJsDoc = false;
  }

  @Override
  protected CompilerOptions getOptions() {
    CompilerOptions options = super.getOptions();
    options.setLanguageOut(LanguageMode.ECMASCRIPT6_TYPED);
    return options;
  }

  @Override
  public CompilerPass getProcessor(Compiler compiler) {
    return new JsdocToEs6TypedConverter(compiler);
  }

  @Override
  protected int getNumRepetitions() {
    return 1;
  }

  public void testVariableDeclaration() {
    test("/** @type {string} */ var print;", "var print: string;");
  }

  public void testVariableDeclarationWithoutDeclaredType() throws Exception {
    test("var print;", "var print;");
  }

  public void testFunctionReturnType() throws Exception {
    test("/** @return {boolean} */ function b(){}", "function b(): boolean {}");
  }

  public void testFunctionParameterTypes() throws Exception {
    test("/** @param {number} n @param {string} s */ function t(n,s){}",
        "function t(n: number, s: string) {}");
  }

  public void testFunctionInsideAssignment() throws Exception {
    test("/** @param {boolean} b @return {boolean} */ "
            + "var f = function(b){return !b};",
        "var f = function(b: boolean): boolean { return !b; };");
  }

  public void testNestedFunctions() throws Exception {
    test("/**@param {boolean} b*/ "
            + "var f = function(b){var t = function(l) {}; t();};",
            "var f = function(b: boolean) {"
            + "  var t = function(l) {"
            + "  };"
            + "  t();"
            + "};");
  }

  public void testUnknownType() throws Exception {
    test("/** @type {?} */ var n;", "var n: any;");
  }

  // TypeScript doesn't have a representation for the Undefined type,
  // so our transpilation is lossy here.
  public void testUndefinedType() throws Exception {
    test("/** @type {undefined} */ var n;", "var n;");
  }
}


File: test/com/google/javascript/jscomp/parsing/TypeDeclarationsIRFactoryTest.java
/*
 * Copyright 2015 The Closure Compiler Authors.
 *
 * Licensed under the Apache License, Version 2.0 (the "License");
 * you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at
 *
 *     http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 */

package com.google.javascript.jscomp.parsing;

import static com.google.common.truth.Truth.THROW_ASSERTION_ERROR;
import static com.google.javascript.jscomp.testing.NodeSubject.assertNode;
import static com.google.javascript.rhino.Token.ANY_TYPE;
import static com.google.javascript.rhino.Token.ARRAY_TYPE;
import static com.google.javascript.rhino.Token.BOOLEAN_TYPE;
import static com.google.javascript.rhino.Token.FUNCTION_TYPE;
import static com.google.javascript.rhino.Token.NAMED_TYPE;
import static com.google.javascript.rhino.Token.NUMBER_TYPE;
import static com.google.javascript.rhino.Token.PARAMETERIZED_TYPE;
import static com.google.javascript.rhino.Token.RECORD_TYPE;
import static com.google.javascript.rhino.Token.STRING_TYPE;
import static com.google.javascript.rhino.TypeDeclarationsIR.anyType;
import static com.google.javascript.rhino.TypeDeclarationsIR.arrayType;
import static com.google.javascript.rhino.TypeDeclarationsIR.booleanType;
import static com.google.javascript.rhino.TypeDeclarationsIR.functionType;
import static com.google.javascript.rhino.TypeDeclarationsIR.namedType;
import static com.google.javascript.rhino.TypeDeclarationsIR.numberType;
import static com.google.javascript.rhino.TypeDeclarationsIR.parameterizedType;
import static com.google.javascript.rhino.TypeDeclarationsIR.recordType;
import static com.google.javascript.rhino.TypeDeclarationsIR.stringType;
import static com.google.javascript.rhino.TypeDeclarationsIR.unionType;
import static java.util.Arrays.asList;

import com.google.javascript.jscomp.parsing.Config.LanguageMode;
import com.google.javascript.jscomp.testing.NodeSubject;
import com.google.javascript.rhino.IR;
import com.google.javascript.rhino.JSTypeExpression;
import com.google.javascript.rhino.Node;
import com.google.javascript.rhino.Node.TypeDeclarationNode;

import junit.framework.TestCase;

import java.util.HashSet;
import java.util.LinkedHashMap;

/**
 * Tests the conversion of type ASTs from the awkward format inside a
 * jstypeexpression to the better format of native type declarations.
 *
 * @author alexeagle@google.com (Alex Eagle)
 */
public final class TypeDeclarationsIRFactoryTest extends TestCase {

  public void testConvertSimpleTypes() {
    assertParseTypeAndConvert("?").hasType(ANY_TYPE);
    assertParseTypeAndConvert("*").hasType(ANY_TYPE);
    assertParseTypeAndConvert("boolean").hasType(BOOLEAN_TYPE);
    assertParseTypeAndConvert("number").hasType(NUMBER_TYPE);
    assertParseTypeAndConvert("string").hasType(STRING_TYPE);
  }

  public void testConvertNamedTypes() throws Exception {
    assertParseTypeAndConvert("Window")
        .isEqualTo(namedType("Window"));
    assertParseTypeAndConvert("goog.ui.Menu")
        .isEqualTo(namedType("goog.ui.Menu"));

    assertNode(namedType("goog.ui.Menu"))
        .isEqualTo(new TypeDeclarationNode(NAMED_TYPE,
            IR.getprop(IR.getprop(IR.name("goog"), IR.string("ui")), IR.string("Menu"))));
  }

  public void testConvertTypeApplication() throws Exception {
    assertParseTypeAndConvert("Array.<string>")
        .isEqualTo(arrayType(stringType()));
    assertParseTypeAndConvert("Object.<string, number>")
        .isEqualTo(parameterizedType(namedType("Object"), asList(stringType(), numberType())));

    assertNode(parameterizedType(namedType("Array"), asList(stringType())))
        .isEqualTo(new TypeDeclarationNode(PARAMETERIZED_TYPE,
            new TypeDeclarationNode(NAMED_TYPE, IR.name("Array")),
            new TypeDeclarationNode(STRING_TYPE)));
  }

  public void testConvertTypeUnion() throws Exception {
    assertParseTypeAndConvert("(number|boolean)")
        .isEqualTo(unionType(numberType(), booleanType()));
  }

  public void testConvertRecordType() throws Exception {
    LinkedHashMap<String, TypeDeclarationNode> properties = new LinkedHashMap<>();
    properties.put("myNum", numberType());
    properties.put("myObject", null);

    assertParseTypeAndConvert("{myNum: number, myObject}")
        .isEqualTo(recordType(properties));
  }

  public void testCreateRecordType() throws Exception {
    LinkedHashMap<String, TypeDeclarationNode> properties = new LinkedHashMap<>();
    properties.put("myNum", numberType());
    properties.put("myObject", null);
    TypeDeclarationNode node = recordType(properties);

    Node prop1 = IR.stringKey("myNum");
    prop1.addChildToFront(new TypeDeclarationNode(NUMBER_TYPE));
    Node prop2 = IR.stringKey("myObject");

    assertNode(node)
        .isEqualTo(new TypeDeclarationNode(RECORD_TYPE, prop1, prop2));
  }

  public void testConvertRecordTypeWithTypeApplication() throws Exception {
    Node prop1 = IR.stringKey("length");
    assertParseTypeAndConvert("Array.<{length}>")
        .isEqualTo(new TypeDeclarationNode(ARRAY_TYPE,
            new TypeDeclarationNode(RECORD_TYPE, prop1)));
  }

  public void testConvertNullableType() throws Exception {
    assertParseTypeAndConvert("?number")
        .isEqualTo(numberType());
  }

  // TODO(alexeagle): change this test once we can capture nullability constraints in TypeScript
  public void testConvertNonNullableType() throws Exception {
    assertParseTypeAndConvert("!Object")
        .isEqualTo(namedType("Object"));
  }

  public void testConvertFunctionType() throws Exception {
    Node p1 = IR.name("p1");
    p1.setDeclaredTypeExpression(stringType());
    Node p2 = IR.name("p2");
    p2.setDeclaredTypeExpression(booleanType());
    assertParseTypeAndConvert("function(string, boolean)")
        .isEqualTo(new TypeDeclarationNode(FUNCTION_TYPE, anyType(), p1, p2));
  }

  public void testConvertFunctionReturnType() throws Exception {
    assertParseTypeAndConvert("function(): number")
        .isEqualTo(new TypeDeclarationNode(FUNCTION_TYPE, numberType()));
  }

  public void testConvertFunctionThisType() throws Exception {
    Node p1 = IR.name("p1");
    p1.setDeclaredTypeExpression(stringType());
    assertParseTypeAndConvert("function(this:goog.ui.Menu, string)")
        .isEqualTo(new TypeDeclarationNode(FUNCTION_TYPE, anyType(), p1));
  }

  public void testConvertFunctionNewType() throws Exception {
    Node p1 = IR.name("p1");
    p1.setDeclaredTypeExpression(stringType());
    assertParseTypeAndConvert("function(new:goog.ui.Menu, string)")
        .isEqualTo(new TypeDeclarationNode(FUNCTION_TYPE, anyType(), p1));
  }

  public void testConvertVariableParameters() throws Exception {
    Node p1 = IR.name("p1");
    p1.setDeclaredTypeExpression(stringType());
    Node p2 = IR.rest("p2");
    p2.setDeclaredTypeExpression(arrayType(numberType()));
    assertParseTypeAndConvert("function(string, ...number): number")
        .isEqualTo(new TypeDeclarationNode(FUNCTION_TYPE, numberType(), p1, p2));
  }

  public void testConvertOptionalFunctionParameters() throws Exception {
    LinkedHashMap<String, TypeDeclarationNode> requiredParams = new LinkedHashMap<>();
    LinkedHashMap<String, TypeDeclarationNode> optionalParams = new LinkedHashMap<>();
    optionalParams.put("p1", stringType());
    optionalParams.put("p2", numberType());
    assertParseTypeAndConvert("function(?string=, number=)")
        .isEqualTo(functionType(anyType(), requiredParams, optionalParams, null, null));
  }

  public void testConvertVarArgs() throws Exception {
    assertParseJsDocAndConvert("@param {...*} p", "p")
        .isEqualTo(arrayType(anyType()));
  }

  // the JsDocInfoParser.parseTypeString helper doesn't understand an ELLIPSIS
  // as the root token, so we need a whole separate fixture just for that case.
  // This is basically inlining that helper and changing the entry point into
  // the parser.
  // TODO(alexeagle): perhaps we should fix the parseTypeString helper since
  // this seems like a bug, but it's not easy.
  private NodeSubject assertParseJsDocAndConvert(String jsDoc,
      String parameter) {
    // We need to tack a closing comment token on the end so the parser doesn't
    // think it reached premature EOL
    jsDoc = jsDoc + " */";
    Config config = new Config(
        new HashSet<String>(),
         new HashSet<String>(),
        false,
        LanguageMode.ECMASCRIPT3,
        false);
    JsDocInfoParser parser = new JsDocInfoParser(
        new JsDocTokenStream(jsDoc),
        jsDoc,
        0,
        null,
        config,
        NullErrorReporter.forOldRhino());
    assertTrue(parser.parse());
    JSTypeExpression parameterType = parser.retrieveAndResetParsedJSDocInfo()
        .getParameterType(parameter);
    assertNotNull(parameterType);
    Node oldAST = parameterType.getRoot();
    assertNotNull(jsDoc + " did not produce a parsed AST", oldAST);
    return new NodeSubject(THROW_ASSERTION_ERROR,
        TypeDeclarationsIRFactory.convertTypeNodeAST(oldAST));
  }

  private NodeSubject assertParseTypeAndConvert(final String typeExpr) {
    Node oldAST = JsDocInfoParser.parseTypeString(typeExpr);
    assertNotNull(typeExpr + " did not produce a parsed AST", oldAST);
    return new NodeSubject(THROW_ASSERTION_ERROR,
        TypeDeclarationsIRFactory.convertTypeNodeAST(oldAST));
  }
}
